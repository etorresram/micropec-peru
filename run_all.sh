#!/usr/bin/env bash
# Pipeline completo. --sin-descarga usa las instantáneas locales de INEI/BCRP.
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  ""|--sin-descarga) ;;
  *) echo "Uso: ./run_all.sh [--sin-descarga]" >&2; exit 2 ;;
esac
NODE_BINARY="${NODE_BINARY:-node}"
command -v "$NODE_BINARY" >/dev/null || { echo "Falta Node.js 18+ (o NODE_BINARY)." >&2; exit 1; }
command -v tectonic >/dev/null || { echo "Falta Tectonic para generar la nota PDF." >&2; exit 1; }
export NODE_BINARY
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock.txt
fi
PY=.venv/bin/python
mkdir -p data/clean output/tablas output/figuras
if [ "${1:-}" != --sin-descarga ]; then "$PY" pipeline/00_descargar.py; fi
"$PY" -c "import sys; sys.path.insert(0,'pipeline'); from microsim.informalidad import imputar; imputar()"
"$PY" pipeline/01_preparar.py
if [ "${1:-}" = --sin-descarga ]; then
  "$PY" -c "import sys; sys.path.insert(0,'pipeline'); from microsim.macro import construir_insumos; from microsim.preparar import cargar; construir_insumos(cargar)"
else
  "$PY" pipeline/02_macro.py
fi
"$PY" pipeline/03_estimar.py
"$PY" pipeline/04_validar.py
"$PY" pipeline/05_sensibilidad.py
"$PY" pipeline/06_exportar_gui.py
"$PY" pipeline/07_verificar_gui.py
"$PY" docs/build_nota.py
echo "Pipeline, verificación y documentación completos."
