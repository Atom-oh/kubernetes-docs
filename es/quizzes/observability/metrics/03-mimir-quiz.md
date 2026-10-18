# Cuestionario de Grafana Mimir

Referencia: Mimir 3.2.1 / chart 6.2.0. Repasa la arquitectura, la identidad, el almacenamiento y los límites de validación actuales.

## 1. ¿Qué backend está previsto para el almacenamiento de bloques de Mimir en producción?

- A. Solo SSD local
- B. Almacenamiento de objetos, como S3, GCS, Azure Blob o Swift
- C. Solo NFS
- D. Solo una caché en memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Almacenamiento de objetos, como S3, GCS, Azure Blob o Swift**

Los despliegues de producción usan el almacenamiento de objetos externo que corresponda. Existe un backend de sistema de archivos para desarrollo local; eso no lo convierte en un almacén de objetos compartido para producción. La TSDB/WAL local de los ingesters y el almacenamiento de Kafka tienen requisitos de persistencia y recuperación independientes.

</details>

## 2. ¿Qué hace el distributor en la arquitectura de almacenamiento de ingesta?

- A. Almacena por sí solo todos los bloques de largo plazo
- B. Valida las escrituras y agrega registros a Kafka
- C. Devuelve cada consulta desde una caché de resultados
- D. Compacta bloques de TSDB

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Valida las escrituras y agrega registros a Kafka**

Los distributors validan y limitan las escrituras, y luego las distribuyen entre particiones de Kafka. La confirmación de escritura depende de que la escritura en Kafka tenga éxito con las condiciones de durabilidad configuradas. No espera a que un bloque se cargue en S3. Las escrituras directas a un quórum de ingesters corresponden a la arquitectura clásica.

</details>

## 3. ¿Cómo se debe proteger la selección de tenants para clientes que no son de confianza?

- A. Permitir que los clientes elijan cualquier valor para X-Scope-OrgID
- B. Autenticar y autorizar en una pasarela de confianza que establezca el encabezado del tenant
- C. Usar solo un prefijo de clave de objetos
- D. Tratar el nombre de un namespace como autenticación HTTP automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Autenticar y autorizar en una pasarela de confianza que establezca el encabezado del tenant**

X-Scope-OrgID identifica un tenant; no es una credencial. La pasarela de confianza debe reemplazar los encabezados que no sean de confianza y aplicar la correspondencia entre el cliente y su tenant. Un nombre de usuario de autenticación básica solo se asigna a un tenant si el proxy aplica esa política. También hay que restringir el acceso directo que evite la pasarela.

</details>

## 4. ¿Por qué los ingesters cargan bloques de TSDB al almacenamiento de objetos?

- A. Para evitar toda persistencia local
- B. Para proporcionar almacenamiento de bloques a largo plazo y acceso a consultas sobre ellos
- C. Para respaldar los dashboards de Grafana
- D. Para garantizar que todas las muestras confirmadas sobrevivan a cualquier fallo posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Para proporcionar almacenamiento de bloques a largo plazo y acceso a consultas sobre ellos**

Los ingesters mantienen una TSDB/WAL local y cargan bloques periódicamente. La retención local se solapa con la transferencia de datos a los store-gateways. La confirmación de Kafka, el consumo por los ingesters y la carga de objetos son etapas distintas; la recuperación sigue dependiendo de la persistencia, la retención y las condiciones del fallo.

</details>

## 5. ¿Qué responsabilidades corresponden al compactor?

- A. Recopilar métricas de cada endpoint de las aplicaciones
- B. Combinar bloques, deduplicar muestras replicadas y limpiar datos según la retención
- C. Autenticar todos los tenants
- D. Reducir automáticamente todas las series sin procesar con downsampling_enabled

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Combinar bloques, deduplicar muestras replicadas y limpiar datos según la retención**

La compactación combina bloques y elimina muestras duplicadas de las réplicas. La limpieza por retención es asíncrona. La opción inventada compactor.downsampling_enabled no es válida; las reglas de registro crean series derivadas, pero no eliminan automáticamente los datos sin procesar.

</details>

## 6. ¿Cuál no es una responsabilidad del query-frontend?

- A. Dividir y fragmentar las consultas compatibles
- B. Usar una caché de resultados de consultas
- C. Persistir los bloques TSDB autoritativos de largo plazo
- D. Combinar las respuestas de las consultas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Persistir los bloques TSDB autoritativos de largo plazo**

El frontend planifica y almacena en caché el trabajo, y devuelve las respuestas combinadas. El scheduler pone el trabajo en cola y los queriers recuperan los datos necesarios. Que haya aciertos en la caché de metadatos o de chunks no significa que se responda automáticamente la consulta completa. La alineación de pasos puede cambiar las marcas de tiempo solicitadas y la conformidad con PromQL.

</details>

## 7. ¿Qué comparación con VictoriaMetrics es precisa?

- A. Mimir nunca tiene un backend de sistema de archivos
- B. El uso de Grafana hace que Mimir sea universalmente más rápido
- C. Compara la arquitectura de almacenamiento, la semántica de consultas, la aplicación de la multitenencia, la recuperación y el costo medido
- D. VictoriaMetrics no admite tenants

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Compara la arquitectura de almacenamiento, la semántica de consultas, la aplicación de la multitenencia, la recuperación y el costo medido**

Ambos productos requieren un límite de autenticación y autorización. El almacenamiento de bloques de producción de Mimir y la arquitectura revisada de VictoriaMetrics basada en almacenamiento local tienen requisitos operativos distintos. Ni las clasificaciones de compresión sin respaldo ni la preferencia por un ecosistema determinan cuál ofrece mejor rendimiento o menor costo.

</details>

## 8. ¿Qué ofrece el store-gateway?

- A. Recopilación de métricas de aplicaciones
- B. Acceso a consultas sobre bloques mediante almacenamiento de objetos, encabezados de índice y cachés configuradas
- C. Autenticación automática de tenants
- D. Replicación de brokers de Kafka

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Acceso a consultas sobre bloques mediante almacenamiento de objetos, encabezados de índice y cachés configuradas**

Los queriers solicitan datos de bloques a los store-gateways y datos recientes a los ingesters; durante la transferencia de bloques, los rangos pueden solaparse. Reutilizar la caché o los metadatos del índice evita parte del trabajo, pero no significa que todas las consultas se respondan sin leer chunks.

</details>

## 9. ¿Qué controla compactor_blocks_retention_period?

- A. Solo la caducidad de la caché en memoria
- B. La política de retención de bloques a largo plazo que aplica el compactor
- C. La retención de topics de Kafka
- D. Una fecha límite exacta para la eliminación física o por cumplimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La política de retención de bloques a largo plazo que aplica el compactor**

Los rangos de tiempo de los bloques, los escaneos, los marcadores de eliminación y deletion_delay afectan a la eliminación real. La retención de la TSDB local y la de Kafka son independientes. El versionado de S3, Object Lock y las copias de seguridad también afectan a la eliminación completa; una configuración de 365d por sí sola no garantiza el cumplimiento normativo.

</details>

## 10. ¿Cuál no es una suposición válida sobre la disponibilidad?

- A. Validar por separado la durabilidad y la recuperación de Kafka
- B. Hacer coincidir los selectores de zona con nodos que realmente puedan programarse
- C. Colocarlo todo en una sola AZ y afirmar que tolera la pérdida de una zona
- D. Revisar la cobertura de particiones de ingesters, las réplicas de store-gateway y las dependencias de los despliegues

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Colocarlo todo en una sola AZ y afirmar que tolera la pérdida de una zona**

Las zonas lógicas no equivalen a la ubicación física. El ejemplo renderiza tres ingesters y store-gateways en tres zonas seleccionadas, pero aún hay que validar la topología de los brokers, los PVC, la capacidad, las colas, los despliegues y otros componentes. La redundancia de la caché y un solo compactor no demuestran alta disponibilidad integral.

</details>

[Volver al capítulo](../../../observability/metrics/03-mimir.md)
