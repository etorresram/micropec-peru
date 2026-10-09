"""Estima el modelo base (año 2019) y guarda la base de personas con predicciones."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from micropec import config as C  # noqa: E402
from micropec.estimar import guardar  # noqa: E402
from micropec.preparar import cargar  # noqa: E402

t0 = time.time()
p, h = cargar(C.ANIO_BASE)
q, r = guardar(p)
print(f"{len(q):,} personas de 14+ | {time.time()-t0:.0f}s")
print("MNL estado: acierto %.3f pseudo-R2 %.3f" % (r["mnl_estado"]["acierto"], r["mnl_estado"]["pseudo_r2"]))
print("MNL sector: acierto %.3f pseudo-R2 %.3f" % (r["mnl_sector"]["acierto"], r["mnl_sector"]["pseudo_r2"]))
for s in ["informal", "formal"]:
    print(f"Mincer {s}: n={r['mincer_'+s]['n']:,} R2={r['mincer_'+s]['r2']:.3f} sigma={r['mincer_'+s]['sigma']:.3f}")
print("coef sector:", {k: [round(x, 2) for x in v] for k, v in r["coef_sector"].items()})
