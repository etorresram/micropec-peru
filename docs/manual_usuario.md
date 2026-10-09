# MicroPEC Perú — manual de usuario de la interfaz

La interfaz corre íntegramente en el navegador: carga una vez la base del modelo
(12 MB) y cada escenario se calcula en alrededor de un segundo. No envía datos a
ningún servidor.

## 1. Qué muestra

- **Indicadores principales**: pobreza monetaria, pobreza extrema, personas en
  pobreza, Gini del gasto, brecha e ingreso laboral medio real, con la diferencia
  respecto del año base 2019. En los escenarios "observado" aparece además la
  cifra oficial del INEI para comparar.
- **Curva de incidencia del crecimiento**: variación real del gasto per cápita medio
  de cada decil respecto de 2019. Dice quién gana y quién pierde con el escenario.
- **Pobreza por dominio geográfico y por departamento**: 2019 vs. escenario.
- **Resumen de indicadores**: tabla con base, referencia y escenario; se copia como
  CSV con un botón.

## 2. Cómo construir un escenario

1. Elija un punto de partida en el desplegable y pulse **Cargar**: el año base sin
   cambios, un año observado (2020-2024, con los insumos reales del BCRP y el INEI),
   un choque ilustrativo o la política de retiro de AFP.
2. Modifique los controles. Todas las variaciones son **acumuladas respecto de
   2019** (por ejemplo, "inflación acumulada 25 %" significa precios 25 % por encima
   de los de 2019). Los grupos:
   - *Economía*: PBI real por sector, ingreso laboral medio real, traslado del PBI
     sectorial a los ingresos (0 = todos los sectores crecen igual; 1 = cada sector
     crece con su PBI por ocupado), población.
   - *Mercado laboral*: tasa de ocupación, desempleo, informalidad y estructura
     sectorial del empleo (las participaciones se normalizan a 100).
   - *Precios y líneas de pobreza*: IPC y crecimiento de las líneas (la canasta de
     pobreza suele encarecerse más que el IPC cuando sube el precio de los alimentos).
   - *Ingresos no laborales*: Juntos, Pensión 65, otras transferencias públicas,
     pensiones y transferencias privadas, remesas y rentas.
   - *Políticas*: bono extraordinario (monto anual por hogar, deciles cubiertos y
     proporción que se consume) y retiro extraordinario de fondos de AFP (porcentaje
     de afiliados que retira, monto medio y proporción que se consume).
   - *Supuestos del modelo*: elasticidad del gasto al ingreso del hogar.
3. Pulse **Simular**. Para comparar dos escenarios, simule el primero, pulse
   **Fijar como referencia** y luego simule el segundo: la curva de incidencia y la
   tabla muestran ambos.

## 3. Lectura de los resultados

- Los resultados son de un **modelo de muestra** estimado en la ENAHO 2019; sirven
  para comparar escenarios entre sí más que como pronóstico puntual.
- El error de backcasting 2020-2024 es de 1,4 puntos porcentuales en promedio para
  la pobreza nacional (ver `docs/nota_metodologica.pdf`, §5). La pobreza rural es la
  que peor se reproduce (hasta 7 pp en 2023).
- Las variaciones de las transferencias se aplican a los hogares que ya las
  recibían en 2019; un programa nuevo se modela con el bono (monto y deciles).

## 4. Requisitos

Navegador moderno (Chrome, Edge, Firefox o Safari de 2023 en adelante). Funciona en
pantalla de teléfono. Para correrla localmente: `cd gui && python3 -m http.server`.
