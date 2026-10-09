"""Descarga los módulos de la ENAHO (INEI) necesarios para el modelo.

Fuente: portal de microdatos del INEI, https://proyectos.inei.gob.pe/microdatos/
Los archivos zip se guardan en data/raw/<año>/ y se descomprimen allí mismo.
Solo se descargan los que no existen todavía (descarga idempotente).
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE_URL = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{codigo}-Modulo{modulo}.zip"

# Código interno del INEI para cada ENAHO anual (verificado con el diccionario
# incluido en cada zip).
CODIGOS = {2019: 687, 2020: 737, 2021: 759, 2022: 784, 2023: 906, 2024: 966}

# Módulos: 02 = características de los miembros, 03 = educación,
# 05 = empleo e ingresos, 34 = sumaria (ingresos, gastos y pobreza del hogar).
MODULOS = ["02", "03", "05", "34"]


def descargar(anio: int, modulo: str) -> Path:
    destino = RAW / str(anio)
    destino.mkdir(parents=True, exist_ok=True)
    zip_path = destino / f"{CODIGOS[anio]}-Modulo{modulo}.zip"
    if not zip_path.exists():
        url = BASE_URL.format(codigo=CODIGOS[anio], modulo=modulo)
        print(f"  descargando {url}")
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
    marca = destino / f".extraido_{modulo}"
    if not marca.exists():
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                if info.filename.lower().endswith(".dta"):
                    info.filename = Path(info.filename).name
                    z.extract(info, destino)
        marca.touch()
    return destino


if __name__ == "__main__":
    anios = [int(a) for a in sys.argv[1:]] or sorted(CODIGOS)
    for anio in anios:
        print(f"ENAHO {anio}")
        for modulo in MODULOS:
            descargar(anio, modulo)
    print("listo")
