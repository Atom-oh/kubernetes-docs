# Cuestionario sobre el stack de observabilidad

> **Documento relacionado**: [Stack de observabilidad](../../ops/09-observability-stack.md)

## 1. ¿Qué afirmación debería orientar un nuevo despliegue de Loki?

- A) SimpleScalable es el valor predeterminado permanente para todos los despliegues nuevos
- B) SimpleScalable está obsoleto y está previsto retirarlo en la versión 4.0; evalúe alternativas
- C) Monolithic no puede usar almacenamiento de objetos
- D) Tres réplicas garantizan automáticamente el aislamiento entre AZ

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La separación read/write/backend describe la arquitectura de SSD. Los diseños nuevos también deben evaluar su ciclo de vida y las restricciones operativas y de capacidad de los modos Monolithic y Distributed.

</details>

## 2. ¿En qué se diferencian los modos distribuido y monolítico de Tempo 3?

- A) Ambos conservan el ingester antiguo
- B) Monolithic siempre requiere Kafka
- C) Distributed usa Kafka; Monolithic puede ejecutarse sin Kafka
- D) Aumentar las réplicas del chart monolítico proporciona alta disponibilidad distribuida compatible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La versión 3 usa block-builders/live-stores y backend-scheduler/workers en lugar de la arquitectura distribuida de ingester/compactor. No mezcle sus modos de despliegue.

</details>

## 3. ¿Qué limitación se aplica al tail sampling?

- A) Siempre conserva todas las trazas con errores
- B) Decide a partir de los spans recibidos dentro de `decision_wait` y no puede recuperar los datos descartados por head sampling
- C) El balanceo aleatorio de Service siempre mantiene una traza en un mismo sampler
- D) `num_traces` es la tasa de trazas por segundo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Importan los spans que llegan tarde, los límites del búfer, los reinicios y los fallos de transporte. Si hay varios samplers, se necesita enrutamiento por ID de traza.

</details>

## 4. ¿Qué controla `send_batch_size` del procesador batch?

- A) El tamaño máximo del lote
- B) La duración máxima de una traza
- C) Un umbral por número de elementos que activa el envío
- D) La capacidad del almacenamiento persistente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

`send_batch_max_size` establece el límite superior del tamaño del lote. Coloque el procesamiento por lotes después de limitar memoria y procesar el muestreo/descartes.

</details>

## 5. ¿Qué ocurre si todos los Pods de Alloy DaemonSet recopilan todos los destinos de registros del clúster?

- A) La deduplicación de alta disponibilidad perfecta se activa automáticamente
- B) La recopilación puede duplicarse; particione los destinos o configure el clustering de la fuente
- C) La API de Kubernetes permite automáticamente un solo recopilador
- D) No puede iniciarse porque siempre necesita hostPath

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La fuente de la API de registros de Kubernetes es distinta del seguimiento de archivos. El ejemplo con un único Deployment/Recreate reduce duplicados, pero no proporciona alta disponibilidad ni recopilación ininterrumpida.

</details>

## 6. ¿Qué se necesita para la retención de Loki?

- A) Solo `retention_period`
- B) Un índice TSDB de 24 horas, retención del compactor habilitada, `delete_request_store` y un período de retención
- C) Expirar todos los objetos del bucket a la misma antigüedad
- D) El intervalo de tiempo del dashboard de Grafana

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La eliminación se retrasa y es asíncrona, y el estado/marcadores del compactor deben sobrevivir a los reinicios. La expiración de todo el bucket puede dañar objetos necesarios, como los índices.

</details>

## 7. ¿Qué etiquetas identifican un grupo HA y sus réplicas en AMP?

- A) namespace y pod
- B) cluster y `__replica__`
- C) service y trace_id
- D) solo region

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Las réplicas de los mismos datos de scrape comparten `cluster` y usan valores distintos de `__replica__`. Agrupar coberturas de scrape independientes en un mismo grupo HA puede ocasionar pérdida de datos.

</details>

## 8. ¿Qué afirmación sobre la retención de AMP es correcta?

- A) 150 días es un máximo inmutable
- B) Se puede configurar por espacio de trabajo hasta 1095 días
- C) Siempre es ilimitada
- D) Aumentarla restaura las métricas que ya se eliminaron

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Establezca la retención después de evaluar los requisitos, el costo y los límites del servicio. Los datos vencidos no se restauran retroactivamente.

</details>

## 9. ¿Qué se necesita para enlazar un registro de Loki con una traza de Tempo en Grafana?

- A) Instalar ambos servicios los enlaza automáticamente
- B) Extraer correctamente el ID de traza, especificar los UID de los orígenes de datos y tener acceso a los datos de traza
- C) Añadir los ID de traza como etiquetas ordinarias de Prometheus
- D) Habilitar solo HTTP/2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Haga coincidir las asignaciones `derivedFields`/`tracesToLogsV2`, el intervalo de tiempo, la tenencia y los permisos. Los exemplars también requieren instrumentación, OpenMetrics y configuración de almacenamiento.

</details>

## 10. ¿Qué se debe comprobar después de que el renderizado del chart finalice correctamente?

- A) Nada; se aplican todos los valores desconocidos
- B) Los PVC, Services, la identidad, la configuración del backend y las rutas de escritura/consulta reales
- C) Solo la sangría de YAML
- D) Sustituir todas las imágenes por `latest`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Algunos valores del chart pueden ignorarse silenciosamente. Compruebe las solicitudes de almacenamiento y `accessModes`, así como los puertos de Service, y distinga la validación del analizador nativo de la conectividad con el entorno activo.

</details>
