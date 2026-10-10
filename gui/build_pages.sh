#!/usr/bin/env bash
# Construye una carpeta revisable. No hace push ni modifica ramas remotas.
set -euo pipefail
cd "$(dirname "$0")"
DESTINO="${1:?Uso: ./gui/build_pages.sh /ruta/de/salida}"
[ -f datos.json.gz ] || { echo "Faltan datos: ejecutar pipeline/06_exportar_gui.py" >&2; exit 1; }
[ -f ../output/verificacion.json ] || { echo "Falta ejecutar pipeline/07_verificar_gui.py" >&2; exit 1; }
mkdir -p "$DESTINO"
{
  printf '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<title>Microsimulación de Pobreza</title>\n'
  sed -n '1,/^<\/style>/p' index.html
  printf '</head>\n<body>\n'
  sed '1,/^<\/style>/d' index.html
  printf '</body>\n</html>\n'
} > "$DESTINO/index.html"
cp motor.js datos.json.gz "$DESTINO/"
cp ../docs/nota_metodologica.pdf "$DESTINO/"
cp ../docs/nota_metodologica.pdf "$DESTINO/nota_metodologica_20261010_2aa4127.pdf"
cp ../output/verificacion.json "$DESTINO/"
printf 'Interfaz de microsimulación, versión 0.2.0. Construida desde una revisión verificada.\n' > "$DESTINO/README.md"
echo "Interfaz construida en $DESTINO"
