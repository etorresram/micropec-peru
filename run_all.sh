#!/usr/bin/env bash
# Corre el pipeline completo de principio a fin (descarga, preparación, estimación,
# validación, exportación y prueba de equivalencia). Tiempo total: ~10 minutos.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; fi
PY=.venv/bin/python
$PY pipeline/00_descargar.py
$PY -c "import sys; sys.path.insert(0,'pipeline'); from micropec.informalidad import imputar; imputar()"
$PY pipeline/01_preparar.py
$PY pipeline/02_macro.py
$PY pipeline/03_estimar.py
$PY pipeline/04_validar.py
$PY pipeline/06_exportar_gui.py
$PY pipeline/07_verificar_gui.py
echo "pipeline completo"
