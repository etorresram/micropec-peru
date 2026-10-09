"""Rutas y mapeos compartidos por todo el pipeline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
MACRO = ROOT / "data" / "macro"
OUT = ROOT / "output"
GUI = ROOT / "gui"

ANIO_BASE = 2019
ANIOS = [2019, 2020, 2021, 2022, 2023, 2024]

# Códigos internos del INEI por año (portal de microdatos).
CODIGOS_INEI = {2019: 687, 2020: 737, 2021: 759, 2022: 784, 2023: 906, 2024: 966}

# Sectores de actividad del modelo (ocupación principal, CIIU Rev. 4 a 2 dígitos)
# y su correspondencia con el PBI sectorial del BCRP.
SECTORES = {
    1: "Agropecuario y pesca",
    2: "Minería e hidrocarburos",
    3: "Manufactura",
    4: "Construcción",
    5: "Comercio",
    6: "Servicios",
}
SECTOR_CORTO = {1: "agro", 2: "mineria", 3: "manufactura", 4: "construccion", 5: "comercio", 6: "servicios"}

# Series anuales del BCRP (millones de S/ de 2007) por sector del modelo.
# Electricidad y agua se agrega a servicios por su escaso peso en el empleo.
BCRP_PBI_SECTOR = {
    1: ["PM04986AA", "PM04989AA"],   # agropecuario + pesca
    2: ["PM04990AA"],                # minería e hidrocarburos
    3: ["PM04993AA"],                # manufactura
    4: ["PM04997AA"],                # construcción
    5: ["PM04998AA"],                # comercio
    6: ["PM04999AA", "PM04996AA"],   # servicios + electricidad y agua
}
BCRP_OTRAS = {
    "pbi": "PM05000AA",              # PBI real (millones S/ 2007)
    "ipc_prom": "PM05217PA",         # IPC Lima, variación % promedio anual
    "remesas_usd": "PM39983BA",      # remesas del exterior, millones US$
}

ESTADOS = {0: "Menor de 14", 1: "Inactivo", 2: "Desocupado", 3: "Ocupado informal", 4: "Ocupado formal"}

# Niveles educativos (p301a de la ENAHO) agrupados en 4 categorías.
EDUC = {1: "Hasta primaria", 2: "Secundaria", 3: "Superior no universitaria", 4: "Superior universitaria"}

GRUPOS_EDAD = [(0, 13), (14, 24), (25, 44), (45, 64), (65, 120)]


def ciiu_a_sector(codigo: float) -> int:
    """CIIU Rev. 4 (4 dígitos) -> sector del modelo."""
    if codigo != codigo:  # NaN
        return 0
    div = int(codigo) // 100
    if div <= 3:
        return 1
    if div <= 9:
        return 2
    if div <= 33:
        return 3
    if div in (41, 42, 43):
        return 4
    if div in (45, 46, 47):
        return 5
    return 6


def educ_a_grupo(p301a: float) -> int:
    if p301a != p301a:
        return 1
    p = int(p301a)
    if p <= 4 or p == 12:
        return 1
    if p <= 6:
        return 2
    if p <= 8:
        return 3
    return 4


def grupo_edad(edad: float) -> int:
    for i, (a, b) in enumerate(GRUPOS_EDAD):
        if a <= edad <= b:
            return i
    return len(GRUPOS_EDAD) - 1
