# Manual de usuario — versión 0.2.0

[Interfaz pública](https://etorresram.github.io/microsim-pobreza/).
La simulación se ejecuta en el navegador después de descargar la base. Los
escenarios introducidos no se envían a un servidor. La primera carga y la
calibración demográfica pueden tardar más que los escenarios sencillos.

## Cargar y modificar un escenario

1. Seleccionar el año o escenario y pulsar **Cargar**. Cambiar el desplegable por
   sí solo no modifica los resultados existentes.
2. Elegir el modo de ingresos laborales. Los años históricos se cargan con
   **ingresos por sector y área**, líneas regionales y composición demográfica.
3. Editar los controles habilitados y pulsar **Simular**. Aparece la indicación de
   cambios pendientes hasta ejecutar. El resultado se identifica como personalizado.
4. **Fijar como referencia** conserva resultados y supuestos para comparar. Las
   cifras principales siguen comparándose con 2019; el CSV añade diferencias
   respecto de la referencia.
5. **Volver a 2019** carga el escenario sin cambios. La referencia fijada se conserva.

Todas las variaciones son acumuladas respecto de 2019. Los montos de políticas
son anuales; el motor los mensualiza para compararlos con ingresos y gastos.

## Modos de ingreso

- **Solo PBI sectorial:** el PBI real por ocupado determina el crecimiento del
  ingreso; no usa una meta agregada independiente de ingreso laboral.
- **Ingreso medio + PBI sectorial:** la meta de ingreso real medio fija el nivel;
  el PBI por ocupado y el passthrough definen diferencias entre sectores.
- **Ingresos por sector:** usa las metas sectoriales del escenario cargado.
- **Ingresos por sector y área:** usa las metas por sector y urbano/rural.

Los dos últimos modos desactivan los controles de PBI, passthrough e ingreso
agregado, porque no intervienen en esos cálculos. Para editar esas hipótesis,
cambiar de modo. En el año base las metas por celda son factores unitarios.
Cambiar población mantiene la composición relativa cargada; modificar la inflación
de las líneas escala los factores regionales conservando sus diferencias relativas.

## Políticas y unidades

Juntos, Pensión 65, otras transferencias públicas y remesas representan cambios en
**totales nominales**. Se conserva la distribución de receptores del año base y se
ajusta por los pesos demográficos del escenario. Las demás variaciones no laborales
son factores sobre componentes del hogar. La renta imputada y el ajuste contable
se indexan según los supuestos documentados en la nota.

El **bono nuevo** es adicional a las transferencias cargadas. Se focaliza en
hogares de los deciles de gasto de 2019 indicados. Su monto íntegro incrementa el
ingreso corriente; la proporción consumida añade gasto. No se aplica otra vez la
elasticidad ingreso-gasto a esa porción. Los escenarios históricos no incluyen
un segundo bono extraordinario de pandemia.

El **retiro de AFP** es una reducción de activos: no aumenta ingreso corriente.
Solo la proporción consumida aumenta gasto. Se reportan el volumen retirado y las
personas que retiran, separados del costo fiscal del bono. No se verifica saldo
individual ni se estima el costo previsional futuro; es un ejemplo ilustrativo.

## Resultados y exportaciones

La pobreza usa gasto y líneas actualizadas. Se muestran pobreza extrema, Gini,
resultados urbanos/rurales, dominios y departamentos. La curva de incidencia compara
**deciles reordenados en cada distribución**, no los mismos hogares a través del tiempo.
La cifra INEI es un punto de comparación observado, no un resultado del modelo.

- **Descargar CSV:** indicadores, cifras observadas disponibles, resultados
  territoriales, curvas, diferencias frente a referencia, supuestos, versión y
  diagnóstico de metas. Separador punto y coma; valores sin formato local.
- **Copiar tabla como CSV / Mostrar CSV:** mismo contenido disponible como texto.
- **Descargar gráfico SVG:** exporta cada gráfico vectorial con sus colores y tipografía.
- **Guardar escenario:** descarga el escenario efectivamente simulado en JSON.
- **Cargar escenario JSON:** restaura supuestos de la misma versión; valida
  estructura, valores, grupos y líneas antes de simular. No carga código ejecutable.

Los cambios pendientes en controles no alteran el escenario que se guarda ni los
resultados que se exportan hasta pulsar Simular.

## Interpretación y límites

La reconstrucción histórica usa agregados contemporáneos ENAHO/BCRP, incluyendo
los ingresos del año evaluado. No es una prueba fuera de muestra ni un pronóstico
oficial. Consultar la nota y las tablas para los errores nacionales y territoriales
actualizados; no utilizar cifras de la versión 0.1.0. No hay intervalos de confianza.
Los costos y efectos de las políticas dependen de supuestos explícitos y no son
estimaciones causales. Los programas existentes no incorporan receptores nuevos.

La suma sectorial se normaliza si es positiva. Campos vacíos, factores no válidos,
participaciones todas cero o una combinación imposible de ocupación/desempleo
se rechazan con un mensaje; los resultados previos permanecen visibles.

## Ejecución local

Ejecutar primero el pipeline descrito en el README. Después: `cd gui` y
`python3 -m http.server 8000`; abrir `http://localhost:8000/`. Usar un navegador
actual con JavaScript habilitado. Si falla la carga, verificar que existe
`datos.json` o `datos.json.gz`, que se sirve por HTTP y que su versión corresponde
al motor.
