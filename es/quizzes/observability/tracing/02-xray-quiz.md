# Cuestionario de AWS X-Ray

> **Última actualización**: September 13, 2026

[AWS X-Ray](../../../observability/tracing/02-xray.md)

---

1. ¿Qué comportamiento NO proporciona automáticamente un pipeline de trazas de X-Ray?
   - A) Visualización de dependencias de Service a partir de las trazas recopiladas
   - B) Trazado distribuido de solicitudes
   - C) Recopilación de los archivos de logs habituales de todas las aplicaciones
   - D) Análisis de los tiempos de los spans recopilados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilación de los archivos de logs habituales de todas las aplicaciones**

**Explicación:**

Tracing no configura un recopilador general de logs de aplicaciones. CloudWatch Transaction Search puede almacenar spans estructurados en aws/spans, pero esto es distinto de recopilar todos los logs habituales de aplicaciones. Metrics/logs necesitan sus propios pipelines configurados y controles de acceso.

</details>

---

2. Para la ruta del daemon heredado, ¿qué workload de Kubernetes puede ejecutar un daemon en cada worker de EC2 elegible?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) DaemonSet**

**Explicación:**

DaemonSet selecciona nodes elegibles; no es compatible con EKS Fargate. Un Service ClusterIP puede seleccionar un daemon en otro node, por lo que la ubicación del DaemonSet por sí sola no garantiza la entrega UDP local al node ni sin pérdidas. Los SDK/daemon de X-Ray están en modo de mantenimiento; la guía utiliza un Deployment de OpenTelemetry collector independiente para la instrumentación nueva.

</details>

---

3. ¿Cuál NO es un campo de una regla de sampling centralizada de X-Ray?
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) RetentionDays**

**Explicación:**

FixedRate, ReservoirSize y Priority son campos de sampling. RetentionDays no es un parámetro de regla de sampling. Un reservoir no garantiza un número mínimo de trazas cuando no hay tráfico. Las reglas requieren un remote sampler compatible; el head sampling no puede seleccionar un error de respuesta que aún no ha ocurrido.

</details>

---

4. ¿Qué afirmación distingue correctamente entre annotations y metadata de X-Ray?
   - A) Cada segment recibe de forma independiente 100 annotations indexadas
   - B) Las annotations se indexan para el filtrado de X-Ray; la metadata no indexada permanece almacenada y accesible
   - C) Las annotations solo aceptan strings
   - D) La metadata se enmascara automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las annotations se indexan para el filtrado de X-Ray; la metadata no indexada permanece almacenada y accesible**

**Explicación:**

X-Ray indexa hasta50annotations por trace. La metadata no se indexa como annotations, pero no indexada no significa secreta ni inaccesible. Usa campos delimitados deliberadamente y elimina payloads sensibles, identificadores, tokens y parámetros SQL antes de la recopilación. index_all_attributes=false no es un procesador de enmascaramiento.

</details>

---

5. ¿Qué afirmación sobre ADOT Collector es falsa?
   - A) Acepta protocolos de OpenTelemetry compatibles
   - B) Puede conectar pipelines compatibles a múltiples backends
   - C) Declarar un exporter de CloudWatch Logs sin usar convierte automáticamente las trazas en logs
   - D) Debe comprobarse el inventario de componentes de su versión publicada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Declarar un exporter de CloudWatch Logs sin usar convierte automáticamente las trazas en logs**

**Explicación:**

Los receivers, processors y exporters deben conectarse en el pipeline correspondiente de logs/metrics/traces. ADOT incluye integraciones de AWS como awsxray, por lo que el comportamiento específico de AWS no es exclusivo del daemon heredado. No asumas que todos los exporters upstream de Contrib existen en la versión de ADOT seleccionada.

</details>

---

6. ¿Qué representa la categoría de tráfico roja en el trace map de X-Ray/CloudWatch?
   - A) Cada solicitud lenta
   - B) Volumen alto de tráfico
   - C) Fallos de servidor, como HTTP5xx
   - D) Services descubiertos recientemente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Fallos de servidor, como HTTP5xx**

**Explicación:**

El rojo representa fallos de servidor, el amarillo errores de cliente, el púrpura throttling como HTTP429 y el verde tráfico exitoso. Estas categorías no son umbrales de latencia arbitrarios ni afirman que cada Service rojo haya superado una alarma de tasa de errores alta definida por el usuario.

</details>

---

7. ¿Qué se requiere para enviar spans de OpenTelemetry a través de la ruta de recopilación de X-Ray de la guía?
   - A) Cada productor debe usar el SDK de X-Ray heredado
   - B) Un pipeline de collector/export de OTLP compatible y autenticado con la identidad de AWS correcta
   - C) Cada aplicación debe instalar un CloudWatch Agent
   - D) Cada Pod de EKS debe instalar una Lambda Layer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un pipeline de collector/export de OTLP compatible y autenticado con la identidad de AWS correcta**

**Explicación:**

La guía envía OTLP con mTLS a ADOT, cuyo exporter awsxray invoca la API clásica firmada de X-Ray. X-Ray admite IDs W3C de 128 bits; un generador/propagador de ID de X-Ray especial no es obligatorio universalmente. El endpoint alternativo nativo de HTTPS de OTLP requiere SigV4 y Transaction Search. Configura la propagación para la integración real.

</details>

---

8. ¿Qué filtro de tiempo de respuesta de X-Ray selecciona valores estrictamente mayores que dos segundos?
   - A) `responsetime > 2000`
   - B) `responsetime > 2`
   - C) `responsetime >= 2`
   - D) `time > 2s`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `responsetime > 2`**

**Explicación:**

Los valores de tiempo de respuesta están en segundos. >2 excluye exactamente 2 segundos; >=2 los incluye. Estas son expresiones de filtro de X-Ray, no comandos de shell ni Logs Insights QL. duration también es una keyword documentada de X-Ray y no debe presentarse como una keyword inválida inventada.

</details>

---

9. ¿Qué NO demuestra el simple hecho de abrir el trace map de CloudWatch?
   - A) Una vista de dependencias de trazas ya recopiladas
   - B) Correlación con metrics/alarms configuradas
   - C) Instrumentación automática y recopilación exitosa de cada aplicación
   - D) Enlaces a logs correlacionados adecuadamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Instrumentación automática y recopilación exitosa de cada aplicación**

**Explicación:**

La instrumentación, la recopilación, la identidad y la correlación deben configurarse por separado. El antiguo mapa de ServiceLens y X-Ray se combinan en el trace map de CloudWatch. La telemetría existente puede correlacionarse allí, pero un ConfigMap sin montar o una vista vacía no son evidencia de que los agents y las aplicaciones estén configurados.

</details>

---

10. ¿Cuál es el propósito de los Groups de X-Ray?
   - A) Reemplazar la autorización de IAM
   - B) Agrupar trazas coincidentes para análisis y metrics/alarms asociadas
   - C) Asignar automáticamente la propiedad de facturación de AWS
   - D) Establecer la retención mediante una regla de sampling

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar trazas coincidentes para análisis y metrics/alarms asociadas**

**Explicación:**

Los Groups seleccionan trazas con expresiones de filtro. Revisa las metrics resultantes y configura las alarms de CloudWatch por separado. Crear un group no instrumenta a los productores, no anula el sampling, no define el aislamiento de IAM ni prueba que se haya activado una alerta de extremo a extremo.

</details>

---
