"""Genera docs/nota_metodologica.tex con las tablas tomadas de output/ y lo compila con tectonic."""
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
bk = pd.read_csv(OUT / "tablas" / "backcast.csv")
sens = pd.read_csv(OUT / "tablas" / "sensibilidad.csv")
est = json.load(open(OUT / "resumen_estimacion.json"))
inf = json.load(open(OUT / "resumen_informalidad.json"))
ins = json.load(open(ROOT / "data" / "macro" / "insumos_observados.json"))
bcrp = pd.read_csv(ROOT / "data" / "macro" / "bcrp_anual.csv", index_col="anio")

def f(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")

# tabla de backcast
filas = []
for r in bk.itertuples():
    filas.append(f"{int(r.anio)} & {f(r.pobreza_obs*100)} & {f(r.pobreza_sim*100)} & {f(r.error_pp, 1)} & "
                 f"{f(r.extrema_obs*100)} & {f(r.extrema_sim*100)} & {f(r.urbana_obs*100)} & {f(r.urbana_sim*100)} & "
                 f"{f(r.rural_obs*100)} & {f(r.rural_sim*100)} \\\\")
TAB_BK = "\n".join(filas)
EAM = f(bk.error_pp.abs().mean(), 1)

# tabla de sensibilidad (sin bonos adicionales, passthrough 0,25)
s = sens[(~sens.bonos) & (sens.passthrough == 0.25)].copy()
nombres = {"solo_pbi": "Solo PBI sectorial", "agregado": "Ingreso medio + PBI sectorial", "sectorial": "Ingreso por sector",
           "sector_area": "Ingreso por sector y área"}
filas = []
for modo in ["solo_pbi", "agregado", "sectorial", "sector_area"]:
    for el in (0.6, 0.8, 1.0):
        r = s[(s.modo == modo) & (s.elasticidad == el)].iloc[0]
        filas.append(f"{nombres[modo]} & {f(el,1)} & {f(r.EAM,2)} & {f(r.sesgo,2)} & {f(r.EAM_extrema,2)} & {f(r.EAM_urbana,2)} & {f(r.EAM_rural,2)} \\\\")
TAB_SENS = "\n".join(filas)
sb = sens[(~sens.bonos) & (sens.passthrough == 0.25) & (sens.modo == "sector_area") & (sens.elasticidad == 0.8)].iloc[0]
EAM_SIN_BONO = f(sb.EAM, 2)
sp = sens[(~sens.bonos) & (sens.modo == "solo_pbi") & (sens.elasticidad == 0.8) & (sens.passthrough == 1.0)].iloc[0]
SESGO_PBI = f(sp.sesgo, 1)

# insumos macro
filas = []
for t in range(2020, 2025):
    e = ins["anios"][str(t)]
    filas.append(f"{t} & {f((bcrp.loc[t,'pbi']/bcrp.loc[2019,'pbi']-1)*100)} & {f((e['ipc']-1)*100)} & {f((e['linea_factor_nacional']-1)*100)} & "
                 f"{f(e['tasa_ocupacion']*100)} & {f(e['informalidad']*100)} & {f((e['ing_lab_real_factor']-1)*100)} & {f((e['remesas_factor']-1)*100)} \\\\")
TAB_INS = "\n".join(filas)
b = ins["base"]["laboral"]

tex = open(ROOT / "docs" / "nota_metodologica_plantilla.tex", encoding="utf-8").read()
for k, v in {"TAB_BK": TAB_BK, "EAM": EAM, "TAB_SENS": TAB_SENS, "TAB_INS": TAB_INS, "EAM_SIN_BONO": EAM_SIN_BONO, "SESGO_PBI": SESGO_PBI,
             "ACC_ESTADO": f(est["mnl_estado"]["acierto"]*100), "R2_ESTADO": f(est["mnl_estado"]["pseudo_r2"], 2),
             "ACC_SECTOR": f(est["mnl_sector"]["acierto"]*100), "R2_SECTOR": f(est["mnl_sector"]["pseudo_r2"], 2),
             "N_INF": f"{est['mincer_informal']['n']:,}".replace(",", "\\,"), "R2_INF": f(est["mincer_informal"]["r2"], 2), "SIG_INF": f(est["mincer_informal"]["sigma"], 2),
             "N_FOR": f"{est['mincer_formal']['n']:,}".replace(",", "\\,"), "R2_FOR": f(est["mincer_formal"]["r2"], 2), "SIG_FOR": f(est["mincer_formal"]["sigma"], 2),
             "N14": f"{est['n_14mas']:,}".replace(",", "\\,"),
             "ACC_INFORM": f(inf["acierto_validacion"]*100), "INF24": f(inf["informalidad_2024_imputada"]*100),
             "OCUP0": f(b["tasa_ocupacion"]*100), "DES0": f(b["tasa_desempleo"]*100), "INF0": f(b["informalidad"]*100),
             "POB2020": f(bk.pobreza_sim.iloc[0]*100), "POB2024": f(bk.pobreza_sim.iloc[-1]*100),
             "MUJER_INF": f(est["mincer_informal"]["coef"]["mujer"], 2), "MUJER_FOR": f(est["mincer_formal"]["coef"]["mujer"], 2),
             "EDUC4_INF": f(est["mincer_informal"]["coef"]["educ4"], 2), "EDUC4_FOR": f(est["mincer_formal"]["coef"]["educ4"], 2),
             }.items():
    tex = tex.replace("@@" + k + "@@", v)
open(ROOT / "docs" / "nota_metodologica.tex", "w", encoding="utf-8").write(tex)
r = subprocess.run(["tectonic", "-o", str(ROOT / "docs"), str(ROOT / "docs" / "nota_metodologica.tex")], capture_output=True, text=True)
print(r.stdout[-1500:], r.stderr[-3000:])
r.check_returncode()
