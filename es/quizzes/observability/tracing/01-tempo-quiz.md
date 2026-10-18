# Cuestionario de Grafana Tempo

> **Última actualización**: 13 de septiembre de 2026

Referencia: Tempo 3.0.3 y chart de Helm 3.6.0.

---

1. ¿Qué describe mejor el almacenamiento y la búsqueda de Tempo?

   - A) Cada atributo debe indexarse en Elasticsearch
   - B) Los bloques Parquet del almacenamiento de objetos admiten TraceID/TraceQL; el almacenamiento y las consultas siguen teniendo un costo
   - C) Conocer un ID recupera cada span descartado
   - D) Tempo conserva las trazas para siempre

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los bloques Parquet del almacenamiento de objetos admiten TraceID/TraceQL; el almacenamiento y las consultas siguen teniendo costos**

Las columnas dedicadas, los metadatos y las cachés no eliminan los costos de indexación ni de consulta. Solo están disponibles los datos que se ingirieron y conservaron correctamente.

</details>

---

2. ¿Qué componente recibe y valida los datos de las trazas antes de que la ruta de escritura distribuida de Tempo 3 los confirme en Kafka?

   - A) Block-builder
   - B) Querier
   - C) Distributor
   - D) Backend worker

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Distributor**

El distribuidor escribe en Kafka. Los componentes live-store y block-builder, así como el generador de métricas opcional, consumen los datos por separado; esta no es la ruta del ingestor de Tempo 2.

</details>

---

3. ¿Qué consulta TraceQL selecciona spans con estado de error?

   - A) `{ duration > 1s }`
   - B) `{ status = error }`
   - C) `{ status = ok }`
   - D) `{ span.http.response.status_code = 200 }`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `{ status = error }`**

El estado de error de un span es distinto de un umbral de latencia o de una condición arbitraria sobre la respuesta HTTP.

</details>

---

4. ¿Qué configuración de identidad utiliza este ejemplo de EKS/S3?

   - A) Claves de acceso estáticas en los valores de Helm
   - B) El rol de nodo compartido por todas las cargas de trabajo
   - C) IRSA vinculado a monitoring:tempo con sub/aud exactos de OIDC y permisos de S3 con alcance limitado
   - D) Un ServiceAccount no relacionado sin asociación con Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) IRSA vinculado a monitoring:tempo con valores exactos de sub/aud de OIDC y permisos de S3 de alcance limitado**

La anotación del rol debe coincidir con el ServiceAccount de cada Pod de Tempo. Otros métodos de identidad para cargas de trabajo requieren una comprobación propia de compatibilidad con las imágenes fijadas.

</details>

---

5. ¿Cuál no se genera a partir de trazas mediante los procesadores del generador de métricas ilustrado?

   - A) Métricas del grafo de servicios
   - B) Métricas de spans
   - C) Métricas arbitrarias de registros de aplicaciones
   - D) Métricas de tasa, errores y duración derivadas de spans

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Métricas arbitrarias de logs de aplicaciones**

Los procesadores `span-metrics` y `service-graphs` requieren activación explícita y escritura remota. No convierten registros arbitrarios en métricas.

</details>

---

6. ¿Qué afirmación sobre la durabilidad de Tempo 3 es correcta?

   - A) Tres réplicas de Tempo siempre garantizan cero pérdidas
   - B) Los microservicios usan Kafka; su replicación, ISR, retención y recuperación deben diseñarse de forma independiente
   - C) El modo monolítico siempre requiere Kafka
   - D) Cada StatefulSet tiene automáticamente un PVC persistente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los microservicios usan Kafka; su replicación, ISR, retención y recuperación deben diseñarse por separado**

El chart usa emptyDir para los datos de live-store y block-builder. La durabilidad de Kafka no queda garantizada por la cantidad de réplicas de Tempo; el modo monolítico no requiere Kafka.

</details>

---

7. ¿Qué dirección de correlación de Grafana es correcta?

   - A) El mismo namespace por sí solo crea correlación
   - B) Tempo tracesToLogsV2 proporciona el vínculo de trazas a registros; Loki derivedFields proporciona el vínculo de registros a trazas
   - C) Ambos sistemas deben compartir un bucket de S3
   - D) derivedFields hace que las aplicaciones generen TraceIDs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tempo tracesToLogsV2 proporciona Trace→Logs; Loki derivedFields proporciona Logs→Trace**

Los identificadores, los UID de los orígenes de datos, las etiquetas y el intervalo consultado deben corresponder a datos reales. Un enlace no puede recuperar telemetría ausente.

</details>

---

8. ¿Qué componentes gestionan la compactación y la retención en segundo plano de Tempo 3?

   - A) Pestañas del navegador de Grafana
   - B) Clientes OTLP
   - C) El planificador y los trabajadores del backend
   - D) La configuración del compactor antiguo copiada sin cambios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El planificador y los trabajadores del backend**

Estos componentes reemplazan la arquitectura del compactor anterior. La retención es asíncrona, y una regla general de expiración de S3 puede entrar en conflicto con las operaciones del backend.

</details>

---

9. ¿Qué selecciona `{ resource.service.name = "A" } >> { resource.service.name = "B" }`?

   - A) Cualquier par de spans en traces diferentes
   - B) Descendientes B coincidentes de spans A coincidentes
   - C) Solo padres A, nunca B
   - D) Solo hijos B directos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Descendientes B que coinciden con spans A coincidentes**

El resultado aparece en el lado derecho. Use > para los hijos directos. La coincidencia entre spans hermanos y la pertenencia a una misma traza son conceptos distintos.

</details>

---

10. ¿Cuál es la primera respuesta más segura ante consultas lentas y búsquedas recientes aparentemente vacías?

   - A) Copiar ingester.max_block_duration: 30m desde Tempo 2
   - B) Deshabilitar todas las protecciones contra el retraso y las consultas recientes
   - C) Comprobar el intervalo de tiempo, los datos recibidos, el retraso, el volumen de datos analizados y los límites antes de ajustar
   - D) Convertir la telemetría ausente y el tráfico cero en un valor saludable garantizado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Comprobar el intervalo de tiempo, los datos realmente recibidos, el retraso, el volumen de escaneo y los límites antes de ajustar**

Tempo 3 tiene componentes y valores predeterminados diferentes. Los resultados vacíos, la ausencia de tráfico y los fallos son situaciones distintas; generar la configuración no demuestra por sí solo que el sistema de producción funcione.

</details>

---

[Revisa la guía de Tempo](../../../observability/tracing/01-tempo.md).
