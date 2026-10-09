"""Construye data/clean/personas_<año>.parquet y hogares_<año>.parquet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tinkuy import config as C  # noqa: E402
from tinkuy.preparar import guardar  # noqa: E402

anios = [int(a) for a in sys.argv[1:]] or C.ANIOS
for a in anios:
    guardar(a)
