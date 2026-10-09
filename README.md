# MicroPEC Perú — microsimulación macro-micro de pobreza

Modelo de microsimulación que combina los microdatos de la ENAHO con series
macroeconómicas y del mercado laboral para proyectar la pobreza y la distribución
del ingreso en el Perú, construir escenarios contrafactuales y evaluar el impacto
distributivo de choques y políticas. Es una **muestra de trabajo** preparada para la
consultoría PEC del BID *Desarrollo de un modelo de micro-simulación* (Grupo de
Pobreza, Sector Social); replica en miniatura, para un país, cada una de las
tareas de los términos de referencia.

| Tarea de los TdR | Dónde está |
|---|---|
| Preparar la base (microdatos + series macro, con documentación) | `pipeline/00_descargar.py`, `01_preparar.py`, `02_macro.py`; `docs/nota_metodologica.pdf` §2 |
| Estimar el modelo base (elección ocupacional, ecuaciones de ingreso) | `pipeline/03_estimar.py`, `micropec/estimar.py` |
| Módulo de simulación (población, estados laborales, ingresos, no laborales) | `micropec/simular.py` (Python) y `gui/motor.js` (JavaScript, idéntico) |
| Módulo de resultados y escenarios (pobreza, desigualdad, curvas de incidencia) | `micropec/indicadores.py`; interfaz |
| Validación: backcasting y sensibilidad | `pipeline/04_validar.py`; `output/tablas/`, `output/figuras/` |
| Interfaz gráfica para usuarios no técnicos | `gui/index.html` (corre en el navegador, sin servidor) |
| Código reproducible y documentado, nota metodológica, manual | `run_all.sh`, `docs/` |

## Resultados en una línea

Estimado en la ENAHO 2019, el modelo reproduce la cifra oficial del año base
(20,2 %) y, alimentado solo con los insumos macro y laborales observados de cada
año, reproduce la pobreza de 2020-2024 con un error absoluto medio de 1,4 puntos
porcentuales (2020: 29,3 % simulado vs. 30,1 % oficial; 2024: 25,5 % vs. 27,6 %).
Las tablas completas de validación y sensibilidad están en `output/tablas/`.

## Cómo correrlo

```bash
./run_all.sh            # crea .venv, descarga la ENAHO 2019-2024 del INEI y corre todo (~10 min)
```

Los pasos, uno por uno (todos en `pipeline/`):

| Paso | Script | Produce |
|---|---|---|
| 0 | `00_descargar.py` | `data/raw/<año>/` módulos 200, 300, 500 y Sumaria (INEI) |
| 0b | `micropec/informalidad.py` | formalidad imputada para 2024 (el INEI no publicó `ocupinf`) |
| 1 | `01_preparar.py` | `data/clean/personas_<año>.parquet`, `hogares_<año>.parquet` |
| 2 | `02_macro.py` | `data/macro/bcrp_anual.csv`, `insumos_observados.json` |
| 3 | `03_estimar.py` | `data/clean/base_modelo_2019.parquet`, `output/resumen_estimacion.json` |
| 4 | `04_validar.py` | `output/tablas/backcast.csv`, `sensibilidad.csv`, `output/figuras/*.png` |
| 6 | `06_exportar_gui.py` | `gui/datos.json.gz` (base del modelo para la interfaz) |
| 7 | `07_verificar_gui.py` | prueba de que el motor en JavaScript reproduce al de Python |

Para usar la interfaz localmente: `cd gui && python3 -m http.server 8000` y abrir
`http://localhost:8000/`. La versión publicada está en
https://etorresram.github.io/micropec-peru/ (GitHub Pages, rama `gh-pages`, que se
regenera con `gui/build_pages.sh`).

## Estructura

```
pipeline/micropec/   paquete: config, preparar, estimar, simular, indicadores, macro, informalidad
pipeline/0X_*.py     scripts del pipeline, numerados en orden de ejecución
gui/                 interfaz (index.html + motor.js + datos.json.gz)
docs/                nota metodológica (LaTeX/PDF) y manual de usuario
output/              tablas, figuras y resúmenes de estimación
data/                raw (INEI, no versionado), clean (parquet), macro (BCRP)
```

## Escalar a otros países

El motor no contiene nada específico del Perú: trabaja sobre dos tablas
(`personas`, `hogares`) con nombres de columna fijos (`micropec/preparar.py` los
documenta) y sobre un diccionario de insumos macro. Para otro país de la base
armonizada del BID basta escribir el equivalente de `preparar.py` y de la tabla de
correspondencia sector-PBI de `config.py`; estimación, simulación, validación e
interfaz se reutilizan sin cambios.

## Autor

Eric Torres Ramírez (etorresram@gmail.com).
