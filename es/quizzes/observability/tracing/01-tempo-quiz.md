# Cuestionario de Grafana Tempo

> **Última actualización**: September 13, 2026

Referencia: Tempo 3.0.3 y chart 3.6.0.

---

1. ¿Qué describe mejor el almacenamiento y la búsqueda de Tempo?

   - A) Cada atributo debe indexarse en Elasticsearch
   - B) Los bloques Parquet del almacenamiento de objetos admiten TraceID/TraceQL; el almacenamiento y las consultas siguen teniendo costos
   - C) Conocer un ID recupera cada span descartado
   - D) Tempo retiene traces para siempre

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los bloques Parquet del almacenamiento de objetos admiten TraceID/TraceQL; el almacenamiento y las consultas siguen teniendo costos**

Las columnas dedicadas, los metadatos y las cachés no implican un costo de indexación o consulta cero. Solo están disponibles los datos ingeridos y retenidos correctamente.

</details>

---

2. ¿Qué componente recibe y valida los datos de trace antes de que la ruta de escritura distribuida de Tempo 3 los confirme en Kafka?

   - A) Block-builder
   - B) Querier
   - C) Distributor
   - D) Backend worker

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Distributor**

El distributor escribe en Kafka. Los live-stores, block-builders y metrics-generators opcionales consumen por separado; esta no es la ruta de ingester de Tempo 2.

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

El error de estado del span es distinto de un umbral de latencia o de una condición de respuesta HTTP arbitraria.

</details>

---

4. ¿Qué configuración de identidad utiliza este ejemplo de EKS/S3?

   - A) Claves de acceso estáticas en los values de Helm
   - B) El rol de nodo compartido por cada workload
   - C) IRSA vinculado a monitoring:tempo con sub/aud exactos de OIDC y permisos de S3 con alcance limitado
   - D) Un ServiceAccount no relacionado sin asociación con Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) IRSA vinculado a monitoring:tempo con sub/aud exactos de OIDC y permisos de S3 con alcance limitado**

La anotación de rol y el ServiceAccount de cada Pod de Tempo deben coincidir. Otros enfoques de identidad de workload necesitan su propia comprobación de compatibilidad con imágenes fijadas.

</details>

---

5. ¿Cuál no se genera a partir de traces mediante los processors de metrics-generator ilustrados?

   - A) Métricas de grafo de servicios
   - B) Métricas de span
   - C) Métricas arbitrarias de logs de aplicaciones
   - D) Métricas de tasa/error/duración derivadas de spans

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Métricas arbitrarias de logs de aplicaciones**

Span-metrics y service-graphs requieren la activación explícita del processor y remote write. No convierten logs arbitrarios en métricas.

</details>

---

6. ¿Qué afirmación sobre la durabilidad de Tempo 3 es correcta?

   - A) Tres réplicas de Tempo siempre garantizan cero pérdidas
   - B) Los microservicios usan Kafka; su replicación, ISR, retención y recuperación deben diseñarse por separado
   - C) El modo monolítico siempre requiere Kafka
   - D) Cada StatefulSet tiene automáticamente un PVC persistente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los microservicios usan Kafka; su replicación, ISR, retención y recuperación deben diseñarse por separado**

El chart usa emptyDir para los datos de live-store/block-builder. La durabilidad de Kafka no queda establecida por un número de réplicas de Tempo; el modo monolítico no requiere Kafka.

</details>

---

7. ¿Qué dirección de correlación de Grafana es correcta?

   - A) El mismo namespace por sí solo crea correlación
   - B) Tempo tracesToLogsV2 proporciona Trace→Logs; Loki derivedFields proporciona Logs→Trace
   - C) Ambos sistemas deben compartir un bucket de S3
   - D) derivedFields hace que las aplicaciones generen TraceIDs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tempo tracesToLogsV2 proporciona Trace→Logs; Loki derivedFields proporciona Logs→Trace**

Los identificadores, los UID de data sources, las labels y el intervalo de tiempo consultado deben coincidir con datos reales. Un enlace no puede recuperar telemetría ausente.

</details>

---

8. ¿Qué componentes gestionan el trabajo de compactación y retención en segundo plano de Tempo 3?

   - A) Pestañas del navegador de Grafana
   - B) Clientes OTLP
   - C) Backend scheduler y backend workers
   - D) La configuración del compactor antiguo copiada sin cambios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Backend scheduler y backend workers**

Estos reemplazan la arquitectura del compactor antiguo. La retención es asíncrona, y una regla general e independiente de expiración de S3 puede entrar en conflicto con las operaciones del backend.

</details>

---

9. ¿Qué selecciona `{ resource.service.name = "A" } >> { resource.service.name = "B" }`?

   - A) Cualquier par de spans en traces diferentes
   - B) Descendientes B coincidentes de spans A coincidentes
   - C) Solo padres A, nunca B
   - D) Solo hijos B directos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Descendientes B coincidentes de spans A coincidentes**

El resultado está en el lado derecho. Usa > para hijos directos. Ni la coincidencia entre siblings ni una prueba de pertenencia al mismo trace significan lo mismo.

</details>

---

10. ¿Cuál es la primera respuesta más segura ante consultas lentas y búsquedas recientes aparentemente vacías?

   - A) Copiar ingester.max_block_duration: 30m desde Tempo 2
   - B) Deshabilitar todas las protecciones contra el retraso y las consultas recientes
   - C) Comprobar el intervalo de tiempo, los datos realmente recibidos, el retraso, el volumen de escaneo y los límites antes de ajustar
   - D) Convertir la telemetría ausente y el tráfico cero en un valor saludable garantizado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Comprobar el intervalo de tiempo, los datos realmente recibidos, el retraso, el volumen de escaneo y los límites antes de ajustar**

Tempo 3 tiene componentes y valores predeterminados diferentes. Los resultados vacíos, el tráfico cero y los fallos son distintos; solo renderizar la configuración no demuestra que un sistema de producción funcione.

</details>

---

[Revisa la guía de Tempo](../../../observability/tracing/01-tempo.md).
