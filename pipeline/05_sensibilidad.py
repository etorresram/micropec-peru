"""Grilla de sensibilidad del backcasting: modo de ingresos x passthrough x elasticidad."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tinkuy import config as C  # noqa: E402
from tinkuy.simular import cargar_modelo, escenario_base  # noqa: E402

m = cargar_modelo()
ins = json.load(open(C.MACRO / "insumos_observados.json"))
base = escenario_base(ins["base"]["laboral"])
claves = [k for k in base] + ["poblacion_grupos", "lineas_factor"]
filas = []
for modo in ["solo_pbi", "con_ingresos"]:
    for pt in [0.0, 0.25, 0.5, 0.75, 1.0]:
        for el in [0.8, 1.0, 1.2]:
            for t, e in ins["anios"].items():
                esc = {**base, **{k: v for k, v in e.items() if k in claves}}
                esc["passthrough"] = pt
                esc["elasticidad_gasto"] = el
                if modo == "solo_pbi":
                    esc["ing_lab_real_factor"] = None
                r = m.simular(esc)
                filas.append({"modo": modo, "passthrough": pt, "elasticidad": el, "anio": int(t),
                              "pobreza_sim": r["pobreza"], "pobreza_obs": e["observado"]["pobreza"],
                              "extrema_sim": r["pobreza_extrema"], "extrema_obs": e["observado"]["pobreza_extrema"],
                              "urb_sim": r["por_area"]["urbano"]["pobreza"], "urb_obs": e["observado"]["pobreza_urbana"],
                              "rur_sim": r["por_area"]["rural"]["pobreza"], "rur_obs": e["observado"]["pobreza_rural"]})
df = pd.DataFrame(filas)
df["err"] = (df.pobreza_sim - df.pobreza_obs) * 100
df["err_ext"] = (df.extrema_sim - df.extrema_obs) * 100
g = df.groupby(["modo", "passthrough", "elasticidad"]).agg(EAM=("err", lambda x: x.abs().mean()),
                                                           sesgo=("err", "mean"),
                                                           EAM_ext=("err_ext", lambda x: x.abs().mean())).reset_index()
print(g.round(2).to_string(index=False))
df.to_csv(C.OUT / "tablas" / "sensibilidad_backcast.csv", index=False)
g.to_csv(C.OUT / "tablas" / "sensibilidad_resumen.csv", index=False)
