"""Backcasting 2020-2024 con insumos observados: tablas, figuras y sensibilidad.

Parámetros por defecto del modelo (elegidos con la grilla de sensibilidad):
  - ingresos laborales: factores observados por sector x área (modo "sector_area");
  - diferenciales sectoriales del PBI por ocupado con passthrough 0,25 (modo agregado);
  - elasticidad gasto-ingreso 0,8; bonos de la pandemia como política explícita.
"""
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from microsim import config as C  # noqa: E402
from microsim.simular import cargar_modelo, escenario_base  # noqa: E402

matplotlib.use("Agg")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e4df", "grid.linewidth": 0.6, "axes.edgecolor": "#b5b3ad"})
AZUL, NARANJA, AQUA, AMARILLO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"

DEFAULTS = {"passthrough": 0.25, "elasticidad_gasto": 0.8}
MODOS = {
    "solo_pbi": {"ing_lab_real_factor": None, "ing_lab_real_factor_sector": None, "ing_lab_real_factor_sector_area": None},
    "agregado": {"ing_lab_real_factor_sector": None, "ing_lab_real_factor_sector_area": None},
    "sectorial": {"ing_lab_real_factor_sector_area": None},
    "sector_area": {},
}

m = cargar_modelo()
ins = json.load(open(C.MACRO / "insumos_observados.json"))
base = escenario_base(ins["base"]["laboral"])
claves = list(base) + ["poblacion_grupos", "lineas_factor"]


def escenario(t, modo="sector_area", bono=True, **kw):
    e = ins["anios"][str(t)]
    esc = {**base, **{k: v for k, v in e.items() if k in claves}, **DEFAULTS, **MODOS[modo], **kw}
    if not bono:
        esc["bono"] = {"monto_anual": 0.0, "deciles": 0, "mpc": 1.0}
    return esc


r0 = m.simular(base)
assert abs(r0["pobreza"] - 0.2019) < 0.001, r0["pobreza"]
print(f"escenario neutro reproduce 2019: pobreza {r0['pobreza']:.4f}, extrema {r0['pobreza_extrema']:.4f}, Gini {r0['gini_gasto']:.4f}")

# --- 1. backcast con los parámetros por defecto ------------------------------
filas, detalle = [], {}
for t in range(2020, 2025):
    r = m.simular(escenario(t))
    o = ins["anios"][str(t)]["observado"]
    filas.append({"anio": t, "pobreza_sim": r["pobreza"], "pobreza_obs": o["pobreza"],
                  "extrema_sim": r["pobreza_extrema"], "extrema_obs": o["pobreza_extrema"],
                  "urbana_sim": r["por_area"]["urbano"]["pobreza"], "urbana_obs": o["pobreza_urbana"],
                  "rural_sim": r["por_area"]["rural"]["pobreza"], "rural_obs": o["pobreza_rural"],
                  "gini_sim": r["gini_gasto"], "ocupacion_sim": r["laboral"]["tasa_ocupacion"],
                  "informalidad_sim": r["laboral"]["informalidad"]})
    detalle[t] = r
bk = pd.DataFrame(filas)
bk["error_pp"] = (bk.pobreza_sim - bk.pobreza_obs) * 100
bk.to_csv(C.OUT / "tablas" / "backcast.csv", index=False)
print(bk.round(3).to_string(index=False))
print(f"EAM pobreza {bk.error_pp.abs().mean():.2f} pp")

# --- 2. sensibilidad: modos x elasticidad x bonos ------------------------------
sens = []
for modo in MODOS:
    for bono in (True, False):
        for el in (0.6, 0.8, 1.0):
            for pt in (0.0, 0.25, 1.0):
                if modo in ("sectorial", "sector_area") and pt != 0.25:
                    continue
                errs = []
                for t in range(2020, 2025):
                    r = m.simular(escenario(t, modo, bono, elasticidad_gasto=el, passthrough=pt))
                    o = ins["anios"][str(t)]["observado"]
                    errs.append([(r["pobreza"] - o["pobreza"]) * 100, (r["pobreza_extrema"] - o["pobreza_extrema"]) * 100,
                                 (r["por_area"]["urbano"]["pobreza"] - o["pobreza_urbana"]) * 100,
                                 (r["por_area"]["rural"]["pobreza"] - o["pobreza_rural"]) * 100])
                errs = np.array(errs)
                sens.append({"modo": modo, "bonos": bono, "elasticidad": el, "passthrough": pt,
                             "EAM": np.abs(errs[:, 0]).mean(), "sesgo": errs[:, 0].mean(), "EAM_extrema": np.abs(errs[:, 1]).mean(),
                             "EAM_urbana": np.abs(errs[:, 2]).mean(), "EAM_rural": np.abs(errs[:, 3]).mean()})
sens = pd.DataFrame(sens)
sens.to_csv(C.OUT / "tablas" / "sensibilidad.csv", index=False)
print(sens.round(2).to_string(index=False))

# --- 3. figuras -----------------------------------------------------------------
obs2019 = {"pobreza": r0["pobreza"], "extrema": r0["pobreza_extrema"], "urbana": r0["por_area"]["urbano"]["pobreza"],
           "rural": r0["por_area"]["rural"]["pobreza"]}
anios = [2019] + list(bk.anio)
fig, axes = plt.subplots(1, 4, figsize=(11, 3.1))
for ax, (k, titulo) in zip(axes, [("pobreza", "Pobreza total"), ("extrema", "Pobreza extrema"),
                                  ("urbana", "Pobreza urbana"), ("rural", "Pobreza rural")]):
    sim = [obs2019[k]] + list(bk[f"{k}_sim"] * 100 / 100)
    obs = [obs2019[k]] + list(bk[f"{k}_obs"])
    ax.plot(anios, np.array(obs) * 100, color=AZUL, lw=2, marker="o", ms=5, label="Observado (INEI)")
    ax.plot(anios, np.array(sim) * 100, color=NARANJA, lw=2, marker="o", ms=5, label="Simulado")
    ax.set_title(titulo, fontsize=10, loc="left")
    ax.set_xticks(anios)
    ax.set_ylabel("% de la población")
    ax.set_ylim(0, None)
    alto, bajo = (sim[-1], obs[-1]) if sim[-1] >= obs[-1] else (obs[-1], sim[-1])
    ax.annotate(f"{alto*100:.1f}", (anios[-1], alto * 100), textcoords="offset points", xytext=(5, 3), color="#52514e", fontsize=8)
    ax.annotate(f"{bajo*100:.1f}", (anios[-1], bajo * 100), textcoords="offset points", xytext=(5, -9), color="#52514e", fontsize=8)
axes[0].legend(frameon=False, loc="upper left", fontsize=8)
fig.suptitle("Backcasting 2020-2024: pobreza simulada con insumos macro observados vs. cifra oficial", x=0.01, ha="left", fontsize=10)
fig.tight_layout()
fig.savefig(C.OUT / "figuras" / "backcast.png", dpi=200)
fig.savefig(C.OUT / "figuras" / "backcast.pdf")

# GIC 2019-2024
from microsim.preparar import cargar  # noqa: E402
from microsim.indicadores import medias_por_decil  # noqa: E402
r24 = m.simular(escenario(2024), detalle=True)
p24, h24 = cargar(2024)
ipc24 = ins["anios"]["2024"]["ipc"]
d0 = medias_por_decil(m.h.gasto_pc.values, m.w0 * m.h.mieperho.values)
ds = medias_por_decil(r24["_hogares"]["gasto_pc"] / ipc24, r24["_hogares"]["w"] * m.h.mieperho.values)
do = medias_por_decil(h24.gasto_pc.values / ipc24, (h24.peso * h24.mieperho).values)
fig, ax = plt.subplots(figsize=(5.2, 3.1))
x = np.arange(1, 11)
ax.bar(x - 0.2, (do / d0 - 1) * 100, width=0.38, color=AZUL, label="Observado (ENAHO 2024)")
ax.bar(x + 0.2, (ds / d0 - 1) * 100, width=0.38, color=NARANJA, label="Simulado")
ax.axhline(0, color="#b5b3ad", lw=0.8)
ax.set_xticks(x)
ax.set_xlabel("Decil de gasto per cápita")
ax.set_ylabel("Variación real 2019-2024 (%)")
ax.set_title("Curva de incidencia del crecimiento, 2019-2024", fontsize=10, loc="left")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(C.OUT / "figuras" / "gic_2024.png", dpi=200)
fig.savefig(C.OUT / "figuras" / "gic_2024.pdf")

# sensibilidad: elasticidad vs modo (EAM nacional)
piv = sens[(sens.bonos) & (sens.passthrough == 0.25)].pivot(index="elasticidad", columns="modo", values="EAM")
fig, ax = plt.subplots(figsize=(5.2, 3.0))
for col, color in zip(["solo_pbi", "agregado", "sectorial", "sector_area"], [AZUL, NARANJA, AQUA, AMARILLO]):
    ax.plot(piv.index, piv[col], marker="o", lw=2, ms=5, color=color, label={"solo_pbi": "Solo PBI sectorial", "agregado": "Ingreso medio + PBI sectorial",
                                                                               "sectorial": "Ingreso por sector", "sector_area": "Ingreso por sector y área"}[col])
ax.set_xlabel("Elasticidad gasto-ingreso")
ax.set_ylabel("Error absoluto medio (pp)")
ax.set_title("Sensibilidad del backcasting", fontsize=10, loc="left")
ax.set_ylim(0, None)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(C.OUT / "figuras" / "sensibilidad.png", dpi=200)
fig.savefig(C.OUT / "figuras" / "sensibilidad.pdf")
json.dump({str(k): {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in detalle.items()},
          open(C.OUT / "backcast_detalle.json", "w"), indent=1)
print("figuras en output/figuras/")
