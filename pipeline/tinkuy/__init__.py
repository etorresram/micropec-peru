"""tinkuy: modelo de microsimulación macro-micro de pobreza para el Perú (ENAHO).

Módulos:
- config:      rutas, mapeos de sectores, educación y grupos de edad.
- preparar:    construye las bases persona/hogar a partir de los módulos de la ENAHO.
- estimar:     elección ocupacional (logit multinomial) y ecuaciones de ingreso (Mincer).
- simular:     motor de simulación (reponderación, reasignación laboral, ingresos, gasto).
- indicadores: pobreza, desigualdad y curvas de incidencia del crecimiento.
- macro:       series del BCRP y construcción de los insumos observados por año.
"""
__version__ = "0.1.0"
