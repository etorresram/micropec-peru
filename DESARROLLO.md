# Tinkuy — notas de desarrollo

Proyecto de muestra para la consultoría del BID "Desarrollo de un modelo de
micro-simulación". Todo el código y la documentación van en español.

- Pipeline en `pipeline/` (scripts numerados) y paquete `pipeline/tinkuy/`.
- Datos crudos en `data/raw/` (descarga del INEI, no se versionan). No modificarlos.
- El motor de simulación existe dos veces y deben mantenerse idénticos:
  `pipeline/tinkuy/simular.py` (Python) y `gui/motor.js` (JavaScript).
  Cualquier cambio en uno exige el mismo cambio en el otro y correr
  `pipeline/07_verificar_gui.py`.
- Parámetros por defecto: passthrough 0,25, elasticidad gasto-ingreso 0,8
  (justificados en `output/tablas/sensibilidad.csv` y en la nota metodológica).
- Entorno: `.venv` con `requirements.txt`; correr todo con `./run_all.sh`.
