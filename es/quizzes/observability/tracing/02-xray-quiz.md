# Cuestionario de AWS X-Ray

> **Última actualización**: 13 de septiembre de 2026

[AWS X-Ray](../../../observability/tracing/02-xray.md)

---

1. ¿Qué comportamiento NO proporciona automáticamente un pipeline de trazas de X-Ray?
   - A) Visualización de dependencias de servicios a partir de las trazas recopiladas
   - B) Trazado distribuido de solicitudes
   - C) Recopilación de los archivos de registro habituales de todas las aplicaciones
   - D) Análisis de los tiempos de los spans recopilados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilación de los archivos de registro habituales de todas las aplicaciones**

**Explicación:**

El trazado no configura un recopilador general de registros de aplicaciones. CloudWatch Transaction Search puede almacenar spans estructurados en aws/spans, pero eso no equivale a recopilar todos los registros habituales de las aplicaciones. Las métricas y los registros requieren pipelines propios y controles de acceso.

</details>

---

2. Para la ruta del daemon heredado, ¿qué carga de trabajo de Kubernetes puede ejecutar un daemon en cada nodo de trabajo EC2 elegible?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) DaemonSet**

**Explicación:**

DaemonSet selecciona los nodos elegibles; no se admite en EKS Fargate. Un Service de tipo ClusterIP puede seleccionar un daemon que esté en otro nodo, así que la ubicación del DaemonSet por sí sola no garantiza que los datagramas UDP lleguen al agente del mismo nodo ni que lo hagan sin pérdidas. Los SDK y el daemon de X-Ray están en modo de mantenimiento; para instrumentación nueva, la guía usa un Deployment independiente del collector de OpenTelemetry.

</details>

---

3. ¿Cuál NO es un campo de una regla de muestreo centralizada de X-Ray?
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) RetentionDays**

**Explicación:**

FixedRate, ReservoirSize y Priority son campos de muestreo. RetentionDays no es un parámetro de las reglas de muestreo. La cuota reservada no garantiza una cantidad mínima de trazas si no hay tráfico. Las reglas requieren un muestreador remoto compatible; el muestreo en cabecera no puede seleccionar un error de respuesta que todavía no se ha producido.

</details>

---

4. ¿Qué afirmación distingue correctamente las anotaciones de los metadatos de X-Ray?
   - A) Cada segmento recibe de forma independiente 100 anotaciones indexadas
   - B) Las anotaciones se indexan para filtrar en X-Ray; los metadatos no indexados permanecen almacenados y accesibles
   - C) Las anotaciones solo aceptan cadenas
   - D) Los metadatos se enmascaran automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las anotaciones se indexan para filtrar en X-Ray; los metadatos no indexados permanecen almacenados y accesibles**

**Explicación:**

X-Ray indexa hasta 50 anotaciones por traza. Los metadatos no se indexan como anotaciones, pero eso no significa que sean secretos o inaccesibles. Define campos acotados y bien elegidos, y elimina cargas útiles sensibles, identificadores, tokens y parámetros SQL antes de recopilarlos. `index_all_attributes=false` no es un procesador de enmascaramiento.

</details>

---

5. ¿Qué afirmación sobre ADOT Collector es falsa?
   - A) Acepta protocolos de OpenTelemetry compatibles
   - B) Puede conectar pipelines compatibles a múltiples backends
   - C) Declarar un exportador de CloudWatch Logs sin usar convierte automáticamente las trazas en registros
   - D) Debe comprobarse el inventario de componentes de su versión publicada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Declarar un exportador de CloudWatch Logs sin usar convierte automáticamente las trazas en registros**

**Explicación:**

Los receptores, procesadores y exportadores deben conectarse en el pipeline correspondiente de registros, métricas o trazas. ADOT incluye integraciones de AWS como awsxray, por lo que el comportamiento específico de AWS no es exclusivo del daemon heredado. No des por hecho que todos los exportadores upstream de Contrib están disponibles en la versión de ADOT seleccionada.

</details>

---

6. ¿Qué representa la categoría roja de tráfico en el mapa de trazas de X-Ray/CloudWatch?
   - A) Cada solicitud lenta
   - B) Volumen alto de tráfico
   - C) Fallos de servidor, como HTTP 5xx
   - D) Servicios descubiertos recientemente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Fallos de servidor, como HTTP 5xx**

**Explicación:**

El rojo representa fallos de servidor; el amarillo, errores de cliente; el púrpura, limitación de tasa como HTTP 429; y el verde, tráfico correcto. Estas categorías no son umbrales de latencia arbitrarios ni significan que cada servicio rojo haya superado una alarma de tasa de errores elevada definida por el usuario.

</details>

---

7. ¿Qué se requiere para enviar spans de OpenTelemetry a través de la ruta de recopilación de X-Ray de la guía?
   - A) Cada productor debe usar el SDK de X-Ray heredado
   - B) Un pipeline compatible y autenticado de recepción y exportación de OTLP, con la identidad de AWS correcta
   - C) Cada aplicación debe instalar un CloudWatch Agent
   - D) Cada Pod de EKS debe instalar una Lambda Layer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un pipeline compatible y autenticado de recepción y exportación de OTLP, con la identidad de AWS correcta**

**Explicación:**

La guía envía OTLP con mTLS a ADOT, cuyo exportador awsxray llama a la API clásica de X-Ray firmada. X-Ray admite ID W3C de 128 bits; un generador o propagador especial de ID de X-Ray no es obligatorio en todos los casos. El endpoint nativo alternativo de OTLP por HTTPS requiere SigV4 y Transaction Search. Configura la propagación según la integración real.

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

Los valores de tiempo de respuesta se expresan en segundos. El filtro >2 excluye exactamente 2 segundos; >=2 los incluye. Son expresiones de filtro de X-Ray, no comandos de shell ni consultas de Logs Insights QL. duration también es una palabra clave documentada de X-Ray y no debe presentarse como una palabra clave inválida inventada.

</details>

---

9. ¿Qué NO demuestra el simple hecho de abrir el mapa de trazas de CloudWatch?
   - A) Una vista de dependencias de trazas ya recopiladas
   - B) Correlación con métricas y alarmas configuradas
   - C) Instrumentación automática y recopilación exitosa de cada aplicación
   - D) Enlaces a registros correlacionados correctamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Instrumentación automática y recopilación exitosa de cada aplicación**

**Explicación:**

La instrumentación, la recopilación, la identidad y la correlación deben configurarse por separado. El antiguo mapa de ServiceLens y el mapa de X-Ray se combinaron en el mapa de trazas de CloudWatch. La telemetría existente puede correlacionarse allí, pero un ConfigMap sin montar o una vista vacía no demuestra que los agentes y las aplicaciones estén configurados.

</details>

---

10. ¿Para qué sirven los grupos de X-Ray?
   - A) Reemplazar la autorización de IAM
   - B) Agrupar trazas coincidentes para analizarlas y asociarles métricas y alarmas
   - C) Asignar automáticamente la propiedad de facturación de AWS
   - D) Establecer la retención mediante una regla de muestreo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar trazas coincidentes para analizarlas y asociarles métricas y alarmas**

**Explicación:**

Los grupos seleccionan trazas mediante expresiones de filtro. Revisa las métricas resultantes y configura las alarmas de CloudWatch por separado. Crear un grupo no instrumenta a los productores, no anula el muestreo, no establece aislamiento de IAM ni demuestra que se haya activado una alerta de extremo a extremo.

</details>

---
