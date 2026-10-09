"""Descarga las series del BCRP y construye los insumos observados por año."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from microsim import macro  # noqa: E402
from microsim.preparar import cargar  # noqa: E402

df = macro.descargar_bcrp()
print(df.round(3).to_string())
ins = macro.construir_insumos(cargar)
for t, e in ins["anios"].items():
    print(t, "ocup %.3f des %.3f inf %.3f ipc %.3f pob %.3f linea %.3f | obs pobreza %.3f" % (
        e["tasa_ocupacion"], e["tasa_desempleo"], e["informalidad"], e["ipc"], e["poblacion_factor"],
        e["linea_factor_nacional"], e["observado"]["pobreza"]))
    print("    VA:", [round(x, 3) for x in e["va_factor"]], "sectores:", [round(x, 3) for x in e["sector_shares"]])
