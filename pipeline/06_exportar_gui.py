"""Exporta la base del modelo y los parámetros para la interfaz (gui/datos.json.gz).

La interfaz corre el mismo motor de simulación en JavaScript (gui/motor.js), de
modo que un escenario produce exactamente el mismo resultado en Python y en el
navegador. Se exportan solo las columnas que el motor necesita, sin redondear.
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from microsim import config as C  # noqa: E402
from microsim.simular import NOLAB, cargar_modelo, escenario_base  # noqa: E402

m = cargar_modelo()
q, h = m.q, m.h
ins = json.load(open(C.MACRO / "insumos_observados.json"))
est = json.load(open(C.OUT / "resumen_estimacion.json"))
bk = pd.read_csv(C.OUT / "tablas" / "backcast.csv")


def r(a, d):
    return [float(x) for x in a]  # precisión completa: conservar rankings y umbrales


personas = {
    "ih": [int(x) for x in m.ih],
    "e": [int(x) for x in q.estado], "s": [int(x) for x in q.sector], "sp": [int(x) for x in q.sector_pot],
    "y": r(q.ing_lab, 0), "yi": r(q.y_pot_informal, 0), "yf": r(q.y_pot_formal, 0),
    "po": r(q.p_ocupado, 4), "pd": r(q.p_desocupado_c, 4), "pf": r(q.p_formal_c, 4),
    "ps": [r(q[f"p_sector_{s}"], 3) for s in range(1, 7)],
    "afp": [int(x) for x in q.afp], "u": r(q.u, 4), "urb": [int(x) for x in q.urbano],
}
hogares = {
    "w": r(h.peso, 3), "n": [int(x) for x in h.mieperho], "urb": [int(x) for x in h.urbano],
    "dom": [int(x) for x in h.dominio], "dpto": [int(x) for x in h.dpto],
    "g": r(h.gasto_pc, 2), "lin": r(h.linea, 2), "linpe": r(h.linpe, 2), "lab0": r(h.lab_500, 1),
    "nolab": {k: r(h[k], 1) for k in NOLAB},
}
base_lab = ins["base"]["laboral"]
datos = {
    "meta": {"version": "0.2.0", "anio_base": C.ANIO_BASE, "fuente": "ENAHO 2019 (INEI), módulos 200, 300, 500 y Sumaria",
             "sectores": C.SECTORES, "nolab": NOLAB, "n_personas": len(q), "n_hogares": len(h)},
    "params": {"coef_sector": est["coef_sector"], "L0": r(m.L0, 1), "omega": r(m.omega, 5),
               "laboral_base": {k: base_lab[k] for k in ("tasa_ocupacion", "tasa_desempleo", "informalidad", "sector_shares")},
               "defaults": {"passthrough": 0.25, "elasticidad_gasto": 0.8}},
    "escenario_base": escenario_base(base_lab),
    "presets": {t: {**escenario_base(base_lab), **e, "passthrough": 0.25, "elasticidad_gasto": 0.8} for t, e in ins["anios"].items()},
    "demografia": {"claves": m.grupos_claves, "conteos": m.grupos_hh.astype(int).tolist()},
    "oficial": {"2019": {"pobreza": 0.2019, "pobreza_extrema": 0.0285}, **{str(int(x.anio)): {"pobreza": x.pobreza_obs, "pobreza_extrema": x.extrema_obs,
                "pobreza_urbana": x.urbana_obs, "pobreza_rural": x.rural_obs} for x in bk.itertuples()}},
    "backcast": {str(int(x.anio)): {"pobreza": x.pobreza_sim, "pobreza_extrema": x.extrema_sim} for x in bk.itertuples()},
    "personas": personas, "hogares": hogares,
}
C.GUI.mkdir(exist_ok=True)
raw = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode()
with gzip.open(C.GUI / "datos.json.gz", "wb", compresslevel=9) as f:
    f.write(raw)
open(C.GUI / "datos.json", "wb").write(raw)   # copia sin comprimir para pruebas locales (no se publica)
print(f"personas {len(q):,} hogares {len(h):,} | json {len(raw)/1e6:.1f} MB | gz {(C.GUI/'datos.json.gz').stat().st_size/1e6:.2f} MB")
