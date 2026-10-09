"""Prueba de equivalencia: el motor en JavaScript (gui/motor.js) debe reproducir al de Python.

Se construye el modelo de Python a partir del mismo JSON exportado (valores redondeados)
y se corre un escenario idéntico en ambos. Usa el intérprete JavaScript de macOS (JXA);
con Node bastaría `node` sobre el mismo archivo de prueba.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from microsim import config as C  # noqa: E402
from microsim.simular import NOLAB, Modelo  # noqa: E402

D = json.load(open(C.GUI / "datos.json"))
P, H = D["personas"], D["hogares"]
h = pd.DataFrame({"hhid": np.arange(len(H["w"])), "peso": H["w"], "mieperho": H["n"], "urbano": H["urb"], "dominio": H["dom"],
                  "dpto": H["dpto"], "gasto_pc": H["g"], "linea": H["lin"], "linpe": H["linpe"], "lab_500": H["lab0"],
                  **{k: H["nolab"][k] for k in NOLAB}})
q = pd.DataFrame({"hhid": P["ih"], "estado": P["e"], "sector": P["s"], "sector_pot": P["sp"], "ing_lab": P["y"],
                  "y_pot_informal": P["yi"], "y_pot_formal": P["yf"], "p_ocupado": P["po"], "p_desocupado_c": P["pd"],
                  "p_formal_c": P["pf"], "afp": P["afp"], "u": P["u"], "urbano": P["urb"],
                  **{f"p_sector_{s+1}": P["ps"][s] for s in range(6)}})
m = Modelo(q, h, D["params"]["coef_sector"])

esc = {**D["escenario_base"], **D["presets"]["2022"], "passthrough": 0.25, "elasticidad_gasto": 0.8,
       "ing_lab_real_factor_sector": None, "ing_lab_real_factor_sector_area": None,
       "bono": {"monto_anual": 600.0, "deciles": 4, "mpc": 0.9}, "afp": {"cobertura": 0.3, "monto": 8000.0, "mpc": 0.7}}
rp = m.simular(esc)

js = (C.GUI / "motor.js").read_text()
prueba = f"""
ObjC.import('Foundation');
const txt = $.NSString.stringWithContentsOfFileEncodingError('{C.GUI / "datos.json"}', $.NSUTF8StringEncoding, null).js;
const D = JSON.parse(txt);
{js}
const m = new MicroSim.Modelo(D);
const r = m.simular({json.dumps(esc)});
JSON.stringify(r);
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
    f.write(prueba)
out = subprocess.run(["osascript", "-l", "JavaScript", f.name], capture_output=True, text=True, timeout=600)
if out.returncode != 0:
    print(out.stderr)
    sys.exit(1)
rj = json.loads(out.stdout.strip())
claves = ["pobreza", "pobreza_extrema", "brecha", "gini_gasto", "gini_ingreso", "n_pobres", "gasto_pc_medio"]
ok = True
for k in claves:
    d = abs(rp[k] - rj[k]) / max(abs(rp[k]), 1e-12)
    ok &= d < 1e-3
    print(f"{k:16s} python {rp[k]:.6f}  js {rj[k]:.6f}  dif rel {d:.1e}")
for k in ["tasa_ocupacion", "informalidad", "ing_lab_medio"]:
    d = abs(rp["laboral"][k] - rj["laboral"][k]) / abs(rp["laboral"][k]); ok &= d < 1e-3
    print(f"{k:16s} python {rp['laboral'][k]:.6f}  js {rj['laboral'][k]:.6f}  dif rel {d:.1e}")
print("GIC python", np.round(rp["gic"], 4)); print("GIC js    ", np.round(rj["gic"], 4))
print("EQUIVALENTES (diferencias relativas < 1e-3, atribuibles al orden de las sumas en punto flotante)" if ok else "DIFIEREN")
sys.exit(0 if ok else 1)
