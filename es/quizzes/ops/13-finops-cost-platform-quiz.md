# Cuestionario sobre la plataforma de visibilidad de costos de FinOps

1. ¿Qué describe mejor el ciclo Inform → Optimize → Operate?
   - A) Un recorte de costos de ingeniería que se realiza una sola vez
   - B) Una práctica iterativa de visibilidad, mejora y responsabilidad compartida para generar valor tecnológico
   - C) Una secuencia que toda organización completa en seis meses
   - D) Un proceso financiero que termina automáticamente todos los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una práctica iterativa de visibilidad, mejora y responsabilidad compartida para generar valor tecnológico**

Los equipos de producto, negocio, ingeniería y finanzas colaboran; los niveles de servicio y la economía unitaria importan tanto como el gasto.

</details>

---

2. ¿Qué identifica bucket en la configuración de Athena para costos en la nube de OpenCost?
   - A) Solo el bucket de origen de CUR
   - B) El bucket y el prefijo de los resultados de las consultas de Athena
   - C) El almacenamiento de kubeconfig
   - D) Un bucket público compartido por todas las cuentas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El bucket y el prefijo de los resultados de las consultas de Athena**

Las lecturas de origen y las escrituras de resultados necesitan permisos separados. También hay que verificar la tabla real de Glue y la actualidad de los datos importados.

</details>

---

3. ¿Cuál es la afirmación correcta sobre `ValidatingPolicy validationActions: [Audit]`?
   - A) Elimina todos los Pods existentes
   - B) No bloquea las infracciones; revisa los informes antes de cambiar las políticas seleccionadas a Deny
   - C) Agrega automáticamente las etiquetas que faltan
   - D) Ignora `namespaceSelector`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No bloquea las infracciones; revisa los informes antes de cambiar las políticas seleccionadas a Deny**

Audit y Warn para el usuario son mecanismos distintos. El fallo de una prueba en la CLI local no equivale a que la admisión del clúster haya denegado el recurso.

</details>

---

4. ¿Qué hacen realmente el modo Off de VPA y el script de recomendaciones de este capítulo?
   - A) Reducen de inmediato la cantidad de nodos y la factura
   - B) Observan las recomendaciones y generan propuestas asociadas por nombre de contenedor
   - C) Crean y fusionan PR automáticamente
   - D) Aplican `upperBound` como límite para todos los contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Observan las recomendaciones y generan propuestas asociadas por nombre de contenedor**

La edición de manifiestos, los PR, las pruebas de rendimiento y el despliegue son pasos separados. Reducir las solicitudes no garantiza ahorros, por lo que el ahorro estimado en la factura es nulo.

</details>

---

5. ¿Qué diferencia hay entre showback y chargeback?
   - A) Showback da visibilidad; chargeback asigna los costos y los factura según reglas acordadas
   - B) Showback es en tiempo real y chargeback siempre es anual
   - C) Showback solo es compatible con AWS
   - D) Chargeback puede ignorar los redondeos y los créditos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Showback da visibilidad; chargeback asigna los costos y los factura según reglas acordadas**

Acuerda los períodos, la moneda, los costos compartidos, inactivos o no asignados, los impuestos, los reembolsos y los redondeos. Los valores del modelo no se convierten automáticamente en facturas internas.

</details>

---

6. ¿Qué representa un panel que multiplica por 730 la tasa de costos actual de Prometheus?
   - A) La factura mensual final de AWS
   - B) Una estimación que supone que la tasa actual se mantiene durante 730 horas fijas
   - C) La suma exacta de los costos diarios observados
   - D) El monto contable final que incluye todos los descuentos e impuestos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una estimación que supone que la tasa actual se mantiene durante 730 horas fijas**

Distingue las tasas actuales, el costo calculado para un período y el costo facturado. La estimación lineal al cierre del mes también varía según los datos faltantes y los cambios en la demanda.

</details>

---

7. ¿Una variable de espacio de nombres del equipo en Grafana garantiza el aislamiento de datos?
   - A) Sí, las variables otorgan autorización en el origen de datos
   - B) No; se necesitan permisos del lado del servidor en el origen de datos o aislamiento por inquilino, y pruebas de denegación
   - C) Sí, un ALB interno también elimina la necesidad de autenticación
   - D) Solo si el nombre de la etiqueta es suficientemente largo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; se necesitan permisos del lado del servidor en el origen de datos o aislamiento por inquilino, y pruebas de denegación**

Los filtros de los paneles y las carpetas organizan las vistas. Comprueba si los usuarios pueden enviar consultas diferentes al mismo origen de datos.

</details>

---

8. ¿Cuál es la afirmación correcta sobre `for: 30m` en una alerta de tasa de costos?
   - A) Cambia el intervalo de scraping a 30 minutos
   - B) Exige que la condición persista; reduce el ruido de picos breves, pero no elimina los falsos positivos
   - C) Actualiza de inmediato los datos de facturación de AWS
   - D) Garantiza la entrega de Slack exactamente una vez

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Exige que la condición persista; reduce el ruido de picos breves, pero no elimina los falsos positivos**

La duración de la condición, la actualización de los datos, la precisión del modelo y las garantías de entrega son aspectos distintos. Las métricas ausentes no significan que el gasto sea cero.

</details>
