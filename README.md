# Microsimulación de Pobreza

Prototipo macro-micro para explorar pobreza y distribución del bienestar en Perú.
ENAHO 2019 como base; reconstrucción histórica 2020–2024 con agregados contemporáneos.
**Versión 0.2.0: correcciones contables, nominales y de equivalencia entre motores.**

- [Interfaz pública](https://etorresram.github.io/microsim-pobreza/)
- [Nota metodológica](docs/nota_metodologica.pdf)
- [Manual de usuario](docs/manual_usuario.md)
- [Resultados históricos](output/tablas/backcast.csv)
- [Sensibilidad](output/tablas/sensibilidad.csv)
- [Verificación automática](output/verificacion.json)

Es una muestra de trabajo de Eric Torres Ramírez. No es una herramienta oficial del
BID ni una proyección oficial del INEI. El ejercicio histórico usa ingresos, empleo,
demografía, transferencias y líneas de las encuestas de los años evaluados: **no
constituye una validación de pronóstico fuera de muestra**. Los parámetros son
supuestos de trabajo; las limitaciones están documentadas en la nota.

## Reproducir

Requisitos: Python 3.11+, Node.js 18+ y Tectonic en PATH. También puede indicarse
la ruta de Node en `NODE_BINARY`. Las dependencias Python están fijadas en
`requirements.lock.txt`; `requirements.txt` enumera las dependencias directas.

```bash
./run_all.sh                  # descarga INEI/BCRP y genera todos los productos
./run_all.sh --sin-descarga   # requiere las instantáneas locales ya descargadas
```

El script crea las carpetas necesarias y, si no existe, el entorno `.venv`.
Si se reutiliza otro entorno, instalar primero con
`.venv/bin/python -m pip install -r requirements.lock.txt`.
Las descargas pueden tardar y las fuentes pueden revisar sus series: conservar los
archivos de entrada permite reproducir una versión. No se promete un tiempo fijo.

Para ejecutar solo las pruebas, después de generar los datos de la interfaz:

```bash
.venv/bin/python pipeline/07_verificar_gui.py
```

Esta prueba compara todos los indicadores, territorios, curvas y diagnósticos de
Python y JavaScript para los cinco años y cuatro modos de ingreso, el año base y
escenarios de políticas. También verifica neutralidad nominal, cierre contable,
metas agregadas y entradas inválidas. Node ejecuta el mismo `gui/motor.js` que la web.

Para servir localmente la interfaz:

```bash
cd gui
python3 -m http.server 8000
```

Abrir `http://localhost:8000/`. Generar una carpeta autocontenida con
`./gui/build_pages.sh /ruta/de/salida`; este script **no publica**. La publicación se
realiza separadamente desde una revisión verificada.

## Qué hace el modelo

1. Prepara personas y hogares; conserva el ingreso individual y explicita un ajuste
   contable firmado para cerrar el ingreso total de la Sumaria.
2. Estima estados laborales y sectores (logits no ponderados) e ingresos por
   segmento (mínimos cuadrados ponderados); documenta supuestos y limitaciones.
3. Calibra composición demográfica y reasigna estados laborales por probabilidades.
4. Ofrece cuatro modos: solo PBI, ingreso agregado, ingreso por sector, e ingreso
   por sector y área. Las metas de ingreso se ajustan después de las transiciones.
5. Actualiza componentes no laborales; distingue ingreso corriente, consumo de
   bonos y retiro de activos previsionales. No suma bonos de pandemia a flujos
   históricos que ya pueden incluirlos.
6. Aplica la elasticidad al ingreso **real**, actualiza líneas regionales y calcula
   pobreza, desigualdad, curvas reordenadas, costo y cobertura de las políticas.

## Estructura

- `pipeline/microsim/`: preparación, estimación, escenarios, indicadores y fuentes.
- `pipeline/00_...07_*.py`: etapas y pruebas; `verificar_motor.cjs`: ejecutor Node.
- `gui/`: motor JS, interfaz y datos generados (sin pérdida de precisión).
- `docs/`: plantilla, generador de nota, PDF y manual.
- `output/`: tablas, figuras, estimación y verificación.
- `data/raw`, `data/clean`: archivos locales no versionados; `data/macro`: instantánea.

## Extensión y limitaciones

Las convenciones actuales incluyen seis sectores, edad laboral 14+, programas
peruanos y pobreza por gasto. Adaptar otro país exige revisar bienestar, líneas,
programas, demografía, sectores, fuentes y estimación, además de preparación.
La reponderación no crea hogares nuevos. La asignación laboral es discreta. Los
logits no usan pesos; los residuos se sortean sin corrección de selección. Los
adultos sin estado laboral observado se asumen inactivos. La informalidad imputada
2024 no tiene validación temporal propia. No hay intervalos de confianza ni efectos
de equilibrio general. La selección de receptores históricos se mantiene fija.

## Autor

Eric Torres Ramírez (etorresram@gmail.com).
