# Cuestionario de Amazon OpenSearch Service

Pon a prueba tus conocimientos sobre Amazon OpenSearch Service.

---

1. ¿En qué proyecto de código abierto se basa Amazon OpenSearch Service?

   - A) Apache Solr
   - B) bifurcación de Elasticsearch 7.10
   - C) Apache Lucene por sí solo
   - D) versión de código abierto de Splunk

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) bifurcación de Elasticsearch 7.10**

**Explicación:**
OpenSearch es un proyecto de código abierto creado por AWS en 2021 mediante una bifurcación de Elasticsearch 7.10 bajo la licencia Apache 2.0. Se inició como respuesta al cambio de licencia de Elastic (SSPL).

</details>

---

2. ¿Qué tipo de Node en un clúster de OpenSearch es responsable de la gestión de los metadatos de los índices y del estado del clúster?

   - A) Data Node
   - B) Master Node
   - C) UltraWarm Node
   - D) Coordinating Node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Master Node**

**Explicación:**
Los Master Nodes gestionan tareas de administración del clúster, como la gestión del estado del clúster, la creación/eliminación de índices y las decisiones de asignación de shards. En entornos de producción, se recomiendan 3 Master Nodes dedicados.

</details>

---

3. ¿Cuál es el nivel de almacenamiento de solo lectura rentable de OpenSearch?

   - A) Hot Storage
   - B) Warm Storage
   - C) UltraWarm
   - D) Standard Storage

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) UltraWarm**

**Explicación:**
UltraWarm es un nivel de almacenamiento de solo lectura basado en S3 que es aproximadamente un 75 % más económico que Hot storage (EBS). Es adecuado para almacenar datos históricos de logs que no se consultan con frecuencia.

</details>

---

4. ¿Cuál es el propósito principal de las políticas de ISM (Index State Management)?

   - A) Gestionar la configuración de seguridad de los índices
   - B) Automatizar el ciclo de vida de los índices (rollover, eliminación, etc.)
   - C) Optimizar las consultas de índices
   - D) Configurar la replicación de índices

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Automatizar el ciclo de vida de los índices (rollover, eliminación, etc.)**

**Explicación:**
Las políticas de ISM gestionan automáticamente los ciclos de vida de los índices. Pueden automatizar el rollover de índices, las transiciones Hot→UltraWarm→Cold y la eliminación después de períodos de retención.

</details>

---

5. ¿Qué método de recopilación de logs para OpenSearch es el más rentable y fácil de gestionar?

   - A) Logstash en EC2
   - B) FluentBit DaemonSet + transmisión directa
   - C) Kinesis Data Firehose
   - D) funciones Lambda

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Kinesis Data Firehose**

**Explicación:**
Kinesis Data Firehose es un servicio completamente administrado que realiza automáticamente el almacenamiento en búfer, la compresión y el procesamiento por lotes. Con copias de seguridad integradas en S3 y gestión de errores, tiene una baja sobrecarga operativa y es rentable para la recopilación de logs a gran escala.

</details>

---

6. En el Fine-Grained Access Control (FGAC) de OpenSearch, ¿qué característica restringe el acceso a los logs de namespaces específicos?

   - A) Field-Level Security (FLS)
   - B) Document-Level Security (DLS)
   - C) Index-Level Security
   - D) Cluster-Level Security

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Document-Level Security (DLS)**

**Explicación:**
Document-Level Security (DLS) restringe el acceso únicamente a los documentos que coinciden con condiciones específicas. Por ejemplo, puedes configurar el acceso únicamente a los logs de un equipo específico mediante la condición `kubernetes.namespace: "team-a"`.

</details>

---

7. En las plantillas de índices de OpenSearch, ¿cuál es el tipo de optimización de strings de Elasticsearch/OpenSearch utilizado en lugar de `LowCardinality`?

   - A) text
   - B) keyword
   - C) analyzed_string
   - D) compact_string

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) keyword**

**Explicación:**
En OpenSearch, los campos de strings de baja cardinalidad (namespace, level, etc.) utilizan el tipo `keyword`. El tipo `text` se tokeniza para la búsqueda de texto completo, mientras que `keyword` está optimizado para coincidencias exactas y agregaciones.

</details>

---

8. ¿Cuál es el orden correcto de niveles de almacenamiento para la optimización de costos de OpenSearch?

   - A) Cold → UltraWarm → Hot
   - B) Hot → Cold → UltraWarm
   - C) Hot → UltraWarm → Cold
   - D) UltraWarm → Hot → Cold

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Hot → UltraWarm → Cold**

**Explicación:**
Los datos se almacenan primero en Hot storage (EBS) para realizar consultas rápidas, luego pasan a UltraWarm (solo lectura) con el tiempo y, por último, a Cold Storage (S3) para los datos más antiguos. Los costos disminuyen en este orden.

</details>

---

9. ¿Cuál es el Query DSL correcto para buscar logs de error dentro de un intervalo de tiempo específico en OpenSearch?

   - A) `{"query": {"match": {"level": "error", "time": "1h"}}}`
   - B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`
   - C) `{"filter": {"level": "error", "time": "> now-1h"}}`
   - D) `{"search": {"level": "error", "since": "1h"}}`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`**

**Explicación:**
En OpenSearch Query DSL, las consultas `bool` se utilizan para combinar múltiples condiciones. El array `must` incluye especificaciones tanto de `match` (coincidencia de texto) como de `range` (intervalo de tiempo).

</details>

---

10. Al comparar OpenSearch y Loki, ¿para qué caso de uso es más adecuado OpenSearch?

    - A) Startups en las que la optimización de costos es la máxima prioridad
    - B) Casos que requieren búsqueda de texto completo y consultas analíticas complejas
    - C) Integración con una pila de Grafana existente
    - D) Casos que requieren únicamente filtrado simple de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Casos que requieren búsqueda de texto completo y consultas analíticas complejas**

**Explicación:**
OpenSearch admite potentes capacidades de búsqueda de texto completo basadas en Lucene y consultas de agregación complejas. Es adecuado para el análisis de seguridad (SIEM), el cumplimiento y el análisis complejo de logs. Para la optimización de costos o el filtrado simple, Loki es más apropiado.

</details>
