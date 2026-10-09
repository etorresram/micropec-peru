#!/usr/bin/env bash
# Publica la interfaz en GitHub Pages: envuelve index.html (escrito para el visor de
# fragmentos HTML, sin <html>/<head>) en un documento completo y lo sube con
# motor.js y datos.json a la rama gh-pages. Requiere que el repo sea público (o plan
# Pro) y Pages habilitado desde la rama gh-pages: Settings > Pages > Branch: gh-pages.
set -euo pipefail
cd "$(dirname "$0")"
[ -f datos.json ] || { echo "falta gui/datos.json: corre pipeline/06_exportar_gui.py"; exit 1; }
T=$(mktemp -d)
{ printf '<!doctype html>\n<html lang="es">\n<head>\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  sed -n '1,/^<\/style>/p' index.html; printf '</head>\n<body>\n'; sed '1,/^<\/style>/d' index.html; printf '</body>\n</html>\n'; } > "$T/index.html"
cp motor.js datos.json "$T/"
printf 'Tinkuy — interfaz publicada con GitHub Pages. Generada con gui/build_pages.sh desde la rama main.\n' > "$T/README.md"
REMOTO=$(git -C .. remote get-url origin)
( cd "$T" && git init -q -b gh-pages && git add -A && git commit -q -m "Interfaz para GitHub Pages" && git push -q --force "$REMOTO" gh-pages )
rm -rf "$T"
echo "publicado en la rama gh-pages de $REMOTO"
