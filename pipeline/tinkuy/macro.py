"""Series macro del BCRP e insumos observados por año para la validación.

Los insumos de cada año t (2020-2024) se expresan como factores respecto del año
base 2019 y provienen de tres fuentes:

* BCRP (API BCRPData): PBI real por sector, IPC promedio anual, remesas del
  exterior (US$) y tipo de cambio.
* Indicadores laborales agregados: tasa de ocupación, desempleo, informalidad y
  estructura sectorial del empleo. Aquí se calculan de la ENAHO del año t (son
  los que el INEI publica); en operación vendrían de la EPEN o de proyecciones.
* Líneas de pobreza y transferencias públicas: INEI (líneas por dominio) y
  ejecución de los programas (aproximada con el agregado de la ENAHO del año t).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config as C

API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{codigo}/json/{ini}/{fin}/esp"

# Informalidad 2024: el INEI no incluyó `ocupinf` en la ENAHO 2024; la formalidad
# se imputa persona a persona con tinkuy/informalidad.py (logit entrenado en 2023).


def _serie(codigo: str, ini: str, fin: str) -> pd.Series:
    r = requests.get(API.format(codigo=codigo, ini=ini, fin=fin), timeout=60)
    r.raise_for_status()
    d = r.json()
    out = {}
    for p in d["periods"]:
        v = p["values"][0]
        out[p["name"]] = float(v) if v not in ("n.d.", None, "") else np.nan
    s = pd.Series(out, name=d["config"]["series"][0]["name"])
    return s


def descargar_bcrp(anios=C.ANIOS) -> pd.DataFrame:
    """Series anuales 2019-2024 en niveles; guarda data/macro/bcrp_anual.csv."""
    ini, fin = str(min(anios)), str(max(anios))
    cols = {}
    for s, codigos in C.BCRP_PBI_SECTOR.items():
        tot = None
        for cod in codigos:
            x = _serie(cod, ini, fin)
            tot = x if tot is None else tot.add(x, fill_value=0)
        cols[f"pbi_{C.SECTOR_CORTO[s]}"] = tot
    cols["pbi"] = _serie(C.BCRP_OTRAS["pbi"], ini, fin)
    cols["ipc_var"] = _serie(C.BCRP_OTRAS["ipc_prom"], ini, fin)
    cols["remesas_usd"] = _serie(C.BCRP_OTRAS["remesas_usd"], ini, fin)
    # tipo de cambio: promedio anual del TC bancario promedio (serie mensual PN01207PM)
    tc_m = _serie("PN01207PM", f"{ini}-1", f"{fin}-12")
    tc_m.index = [int(re.search(r"(\d{4})", str(i)).group(1)) for i in tc_m.index]
    cols["tc"] = tc_m.groupby(level=0).mean()
    cols = {k: v.rename(index=lambda i: int(str(i)[:4])) for k, v in cols.items()}
    df = pd.DataFrame(cols)
    df.index.name = "anio"
    df["remesas_soles"] = df.remesas_usd * df.tc
    df["ipc"] = (1 + df.ipc_var / 100).cumprod() / (1 + df.ipc_var.iloc[0] / 100)  # nivel, base=1 en el primer año
    C.MACRO.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.MACRO / "bcrp_anual.csv")
    return df


def _wmean(x, w):
    return float(np.average(x, weights=w))


def indicadores_laborales(p: pd.DataFrame, informalidad: float | None = None) -> dict:
    """Tasas agregadas (14 años y más) ponderadas con el factor del hogar."""
    q = p[p.edad >= 14]
    w = q.peso
    ocup = q.estado.isin([3, 4])
    des = q.estado == 2
    e = q[ocup]
    out = {
        "pob14": float(w.sum()),
        "ing_lab_medio": _wmean(e.ing_lab, e.peso),
        "ing_lab_medio_sector": [_wmean(e.ing_lab[e.sector == s], e.peso[e.sector == s]) for s in range(1, 7)],
        "ing_lab_medio_sector_area": {str(u): [_wmean(e.ing_lab[(e.sector == s) & (e.urbano == u)], e.peso[(e.sector == s) & (e.urbano == u)]) for s in range(1, 7)] for u in (1, 0)},
        "tasa_ocupacion": _wmean(ocup, w),
        "tasa_desempleo": float((w * des).sum() / (w * (ocup | des)).sum()),
        "informalidad": _wmean(e.estado == 3, e.peso) if informalidad is None else informalidad,
        "sector_shares": [float((e.peso * (e.sector == s)).sum() / e.peso.sum()) for s in range(1, 7)],
    }
    return out


def estructura_poblacion(p: pd.DataFrame) -> dict:
    """Población por sexo x grupo de edad x área, con el factor del hogar."""
    g = p.groupby(["mujer", "gedad", "urbano"]).peso.sum()
    return {f"{int(a)}_{int(b)}_{int(c)}": float(v) for (a, b, c), v in g.items()}


def lineas_por_grupo(h: pd.DataFrame) -> dict:
    g = h.groupby(["dominio", "urbano"]).apply(
        lambda d: pd.Series({"linea": _wmean(d.linea, d.peso * d.mieperho),
                             "linpe": _wmean(d.linpe, d.peso * d.mieperho)}), include_groups=False)
    return {f"{int(a)}_{int(b)}": {"linea": r.linea, "linpe": r.linpe} for (a, b), r in g.iterrows()}


def agregados_transferencias(h: pd.DataFrame) -> dict:
    return {k: float((h[k] * h.peso).sum()) for k in ["tr_juntos", "tr_p65", "tr_pub_otros", "tr_privadas", "remesas"]}


def construir_insumos(cargar) -> dict:
    """Insumos observados de cada año (factores respecto de 2019). Guarda JSON."""
    bcrp = pd.read_csv(C.MACRO / "bcrp_anual.csv", index_col="anio")
    base_p, base_h = cargar(C.ANIO_BASE)
    lab0 = indicadores_laborales(base_p)
    pob0 = estructura_poblacion(base_p)
    lin0 = lineas_por_grupo(base_h)
    tr0 = agregados_transferencias(base_h)
    insumos = {"anio_base": C.ANIO_BASE, "base": {"laboral": lab0, "lineas": lin0, "transferencias": tr0}, "anios": {}}
    for t in C.ANIOS:
        if t == C.ANIO_BASE:
            continue
        p, h = cargar(t)
        lab = indicadores_laborales(p)
        pob = estructura_poblacion(p)
        lin = lineas_por_grupo(h)
        tr = agregados_transferencias(h)
        ipc = float(bcrp.loc[t, "ipc"] / bcrp.loc[C.ANIO_BASE, "ipc"])
        esc = {
            "anio": t,
            "poblacion_factor": float(sum(pob.values()) / sum(pob0.values())),
            "poblacion_grupos": {k: pob.get(k, 0.0) / v for k, v in pob0.items() if v > 0},
            "tasa_ocupacion": lab["tasa_ocupacion"],
            "tasa_desempleo": lab["tasa_desempleo"],
            "informalidad": lab["informalidad"],
            "sector_shares": lab["sector_shares"],
            "va_factor": [float(bcrp.loc[t, f"pbi_{C.SECTOR_CORTO[s]}"] / bcrp.loc[C.ANIO_BASE, f"pbi_{C.SECTOR_CORTO[s]}"]) for s in range(1, 7)],
            "pbi_factor": float(bcrp.loc[t, "pbi"] / bcrp.loc[C.ANIO_BASE, "pbi"]),
            "ing_lab_real_factor": float(lab["ing_lab_medio"] / lab0["ing_lab_medio"] / ipc),
            "ing_lab_real_factor_sector": [float(a / b / ipc) for a, b in zip(lab["ing_lab_medio_sector"], lab0["ing_lab_medio_sector"])],
            "ing_lab_real_factor_sector_area": {u: [float(a / b / ipc) for a, b in zip(lab["ing_lab_medio_sector_area"][u], lab0["ing_lab_medio_sector_area"][u])] for u in ("1", "0")},
            # bonos extraordinarios de la pandemia (MEF/MIDIS, aproximación): monto por hogar y deciles cubiertos
            "bono": {"2020": {"monto_anual": 1000.0, "deciles": 7, "mpc": 1.0},
                     "2021": {"monto_anual": 1225.0, "deciles": 4, "mpc": 1.0}}.get(str(t), {"monto_anual": 0.0, "deciles": 0, "mpc": 1.0}),
            "ipc": ipc,
            "lineas_factor": {k: {"linea": lin[k]["linea"] / v["linea"], "linpe": lin[k]["linpe"] / v["linpe"]} for k, v in lin0.items() if k in lin},
            "linea_factor_nacional": float(np.average([lin[k]["linea"] / v["linea"] for k, v in lin0.items() if k in lin])),
            "linpe_factor_nacional": float(np.average([lin[k]["linpe"] / v["linpe"] for k, v in lin0.items() if k in lin])),
            "tr_juntos_factor": tr["tr_juntos"] / tr0["tr_juntos"],
            "tr_p65_factor": tr["tr_p65"] / tr0["tr_p65"],
            "tr_pub_otros_factor": tr["tr_pub_otros"] / tr0["tr_pub_otros"],
            "tr_privadas_factor": ipc,                      # supuesto: indexadas a la inflación
            "remesas_factor": float(bcrp.loc[t, "remesas_soles"] / bcrp.loc[C.ANIO_BASE, "remesas_soles"]),
            "rentas_factor": float(bcrp.loc[t, "pbi"] / bcrp.loc[C.ANIO_BASE, "pbi"]) * ipc,   # PBI nominal aprox.
            "alq_factor": ipc,
            "otros_factor": ipc,
            "observado": {
                "pobreza": _wmean(h.pobre, h.peso * h.mieperho),
                "pobreza_extrema": _wmean(h.pobre_ext, h.peso * h.mieperho),
                "pobreza_urbana": _wmean(h.pobre[h.urbano == 1], (h.peso * h.mieperho)[h.urbano == 1]),
                "pobreza_rural": _wmean(h.pobre[h.urbano == 0], (h.peso * h.mieperho)[h.urbano == 0]),
                "tr_privadas_factor_enaho": tr["tr_privadas"] / tr0["tr_privadas"],
            },
        }
        insumos["anios"][str(t)] = esc
    with open(C.MACRO / "insumos_observados.json", "w") as f:
        json.dump(insumos, f, indent=1, ensure_ascii=False)
    return insumos
