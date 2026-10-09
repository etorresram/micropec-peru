"""Equivalencia completa Python/JavaScript e invariantes económicos.

Compara el modelo Python de producción con el JSON de la interfaz, sin redondear.
Node.js 18+ debe estar en PATH o indicado en NODE_BINARY. No depende de macOS.
"""
import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from microsim import config as C
from microsim.simular import cargar_modelo, escenario_base, FACTORES_NOLAB

node = os.environ.get("NODE_BINARY") or shutil.which("node")
if not node:
    raise SystemExit("Falta Node.js 18+ (node en PATH o NODE_BINARY).")
D = json.loads((C.GUI / "datos.json").read_text())
m = cargar_modelo()
base = escenario_base(D["params"]["laboral_base"])
escenarios = {"base": base}
for anio, preset in D["presets"].items():
    for modo in ("sector_area", "sectorial", "agregado", "solo_pbi"):
        e = copy.deepcopy(preset)
        if modo != "sector_area": e["ing_lab_real_factor_sector_area"] = None
        if modo in ("agregado", "solo_pbi"): e["ing_lab_real_factor_sector"] = None
        if modo == "solo_pbi": e["ing_lab_real_factor"] = None
        escenarios[f"{anio}_{modo}"] = e
nominal = {**copy.deepcopy(base), "ipc": 1.2, "ing_lab_real_factor": 1.0, "elasticidad_gasto": .8,
           "linea_factor_nacional": 1.2, "linpe_factor_nacional": 1.2}
for k in set(FACTORES_NOLAB.values()): nominal[k] = 1.2
escenarios["neutralidad_nominal"] = nominal
for mpc in (0.0, 1.0):
    escenarios[f"bono_mpc{mpc}"] = {**copy.deepcopy(base), "bono": {"monto_anual":1200., "deciles":4, "mpc":mpc}}
    escenarios[f"afp_mpc{mpc}"] = {**copy.deepcopy(base), "afp": {"monto":8000., "cobertura":.3, "mpc":mpc}}
invalidos = {
    "ipc_booleano": {**base, "ipc": True},
    "bono_nulo": {**base, "bono": None},
    "mpc_nula": {**base, "bono": {"mpc": None}},
    "monto_nulo": {**base, "bono": {"monto_anual": None}},
    "sectores_cero": {**base, "sector_shares": [0.0]*6},
    "ipc_cero": {**base, "ipc": 0.0},
    "empleo_imposible": {**base, "tasa_ocupacion": .9, "tasa_desempleo": .2},
    "demografia_incompleta": {**base, "poblacion_grupos": {"0_0_0":1.0}},
    "lineas_incompletas": {**base, "lineas_factor": {}},
    "bono_negativo": {**base, "bono": {"monto_anual":-1.0,"deciles":4,"mpc":1.0}},
}
todos = {**escenarios, **invalidos}
proc = subprocess.run([node, str(C.ROOT / "pipeline/verificar_motor.cjs"), str(C.GUI / "datos.json")],
                      input=json.dumps(list(todos.values())), capture_output=True, text=True, check=True, timeout=300)
js = dict(zip(todos, json.loads(proc.stdout)))
py = {}
def comparar(a, b, ruta=""):
    if isinstance(a, dict):
        assert set(map(str,a)) == set(b), ruta
        for k,v in a.items(): comparar(v, b[str(k)], ruta+"/"+str(k))
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b), ruta
        for i,(x,y) in enumerate(zip(a,b)): comparar(x,y,ruta+f"/{i}")
    else:
        assert np.isfinite(a) and b is not None and np.isfinite(b), ruta
        assert np.isclose(a,b,rtol=1e-8,atol=1e-8), f"{ruta}: Python={a} JS={b}"
for nombre,e in escenarios.items():
    r = m.simular(e)
    assert "resultado" in js[nombre], (nombre, js[nombre])
    comparar(r, js[nombre]["resultado"], nombre)
    py[nombre] = r
    d = r["diagnostico"]
    assert np.isclose(r["poblacion"],d["poblacion_meta"],rtol=1e-8), nombre
    assert d["demografia"]["error_max_rel"] < 1e-8, nombre
    for grupo in ("ingresos","no_laborales"):
        for v in d[grupo].values(): assert np.isclose(v["meta"],v["resultado"],rtol=1e-10,atol=1e-7), (nombre,v)
    # Personas indivisibles: las metas de empleo admiten hasta un peso de encuesta.
    w = m._reponderar(e)[m.ih]
    tolerancia = 2*w.max()/w.sum()
    for k in ("tasa_ocupacion","tasa_desempleo","informalidad"):
        assert abs(r["laboral"][k]-e[k]) < tolerancia, (nombre,k)
    print(f"OK {nombre}: pobreza {100*r['pobreza']:.6f}%")
for nombre,e in invalidos.items():
    try: m.simular(e)
    except (ValueError,KeyError,TypeError): pass
    else: raise AssertionError("Python aceptó " + nombre)
    assert "error" in js[nombre], "JavaScript aceptó " + nombre
r0 = py["base"]
assert np.allclose(m.Y0, m.h.ing_pc*m.h.mieperho, rtol=1e-12,atol=1e-8), "Cuenta del hogar no cierra"
for r in (py["neutralidad_nominal"],):
    for k in ("pobreza","pobreza_extrema","gini_gasto","gini_ingreso"):
        assert abs(r[k]-r0[k]) < 1e-10, k
    assert np.max(np.abs(r["gic"])) < 1e-10
assert np.isclose(py["bono_mpc0.0"]["gasto_pc_medio"],r0["gasto_pc_medio"])
assert py["bono_mpc0.0"]["ingreso_hogar_total"] > r0["ingreso_hogar_total"]
assert py["bono_mpc1.0"]["pobreza"] <= r0["pobreza"]
assert np.isclose(py["afp_mpc1.0"]["ingreso_hogar_total"],r0["ingreso_hogar_total"])
assert py["afp_mpc1.0"]["gasto_pc_medio"] > r0["gasto_pc_medio"]
assert np.isclose(py["afp_mpc0.0"]["gasto_pc_medio"],r0["gasto_pc_medio"])
# El experimento de sensibilidad realmente cambia el canal de ingresos.
assert abs(py["2024_solo_pbi"]["gasto_pc_medio"] - py["2024_agregado"]["gasto_pc_medio"]) > 1
resumen = {"version":D["meta"]["version"],"escenarios_equivalentes":len(escenarios),"entradas_invalidas_rechazadas":len(invalidos),
           "neutralidad_nominal":True,"cierre_contable":True,"metas_verificadas":True,
           "tolerancia_relativa_equivalencia":1e-8,"tolerancia_absoluta_equivalencia":1e-8}
(C.OUT/"verificacion.json").write_text(json.dumps(resumen,indent=2)+"\n")
print(json.dumps(resumen,indent=2))
