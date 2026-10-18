# Cuestionario de Kafka Connect y MirrorMaker

Revisa la configuración v1 de Strimzi del capítulo, los complementos reales, la replicación y las condiciones de recuperación.

## 1. ¿En qué dirección mueven los datos Debezium PostgreSQL y un sink de S3?

<details>
<summary>Mostrar respuesta</summary>

Debezium es un conector de origen que envía a Kafka los cambios de la instantánea y del WAL; un sink de S3 envía los registros de Kafka a S3. Comprueba los formatos y el comportamiento de entrega de cada complemento.

</details>

## 2. ¿Archivar los registros de Debezium con el sink de S3 de Aiven reconstruye automáticamente la tabla actual de la base de datos?

<details>
<summary>Mostrar respuesta</summary>

No. El ejemplo archiva eventos CDC con la operación y los datos anteriores y posteriores al cambio. Para materializar el estado actual hay que manejar las claves, las eliminaciones y tombstones, el orden y la reproducción de eventos.

</details>

## 3. ¿En qué se diferencian el coordinador del grupo distribuido de Connect y el líder de los workers?

<details>
<summary>Mostrar respuesta</summary>

Un broker de Kafka coordina el grupo; el líder elegido entre los workers calcula las asignaciones. Un fallo de worker puede retrasar la reasignación y provocar la reproducción de registros, y es distinto de un fallo de tarea.

</details>

## 4. ¿Es imposible ejecutar Connect en modo standalone en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

No; se puede ejecutar allí, pero no dispone de conmutación por error entre workers distribuidos. Strimzi KafkaConnect administra el modo distribuido. Agregar workers no paraleliza automáticamente un conector que tiene una sola tarea.

</details>

## 5. ¿Qué puede ocurrir si se edita un conector directamente mediante REST mientras los recursos KafkaConnector lo administran?

<details>
<summary>Mostrar respuesta</summary>

El operador puede reconciliarlo y devolverlo al estado deseado del recurso personalizado (CR). Usa el CR como vía para modificarlo y restringe tanto las actualizaciones de Kubernetes como el acceso a Connect REST.

</details>

## 6. ¿Qué anotación habilita la reconciliación de KafkaConnector y qué versión de API se usa aquí?

<details>
<summary>Mostrar respuesta</summary>

`strimzi.io/use-connector-resources: "true"` y `kafka.strimzi.io/v1`. La migración a v1 incluye campos como `groupId` y los nombres de los topics internos; cambiar solo `apiVersion` no basta.

</details>

## 7. ¿Qué se debe fijar y comprobar en `spec.build`, y cómo se autentica con ECR?

<details>
<summary>Mostrar respuesta</summary>

Especifica las versiones de los complementos, las URL, las sumas de comprobación y una etiqueta para la imagen de salida. Mantén un Secret válido para publicar la imagen y los permisos para extraerla; los tokens de ECR caducan a las 12 horas. La identidad de S3 en tiempo de ejecución y la autenticación para compilar y publicar la imagen son independientes.

</details>

## 8. ¿Para qué sirven las asignaciones de offsets y los checkpoints de MM2?

<details>
<summary>Mostrar respuesta</summary>

`MirrorSourceConnector` emite asignaciones de offsets de origen a destino; `MirrorCheckpointConnector` las usa para traducir los commits de grupos del origen. No se debe suponer que los offsets de origen y destino sean iguales.

</details>

## 9. ¿Cómo nombra los topics remotos `DefaultReplicationPolicy` y cómo detecta ciclos?

<details>
<summary>Mostrar respuesta</summary>

Usa `<source-alias>.<topic>` y detecta un ciclo de vuelta a un alias de destino que ya esté en la cadena de origen. No excluye todos los topics con prefijo: la replicación de varios saltos a un tercer clúster puede ser legítima.

</details>

## 10. ¿Qué hay que preparar, además de MM2, para una conmutación por error activo-pasivo?

<details>
<summary>Mostrar respuesta</summary>

Aísla a los escritores anteriores, mide la actualidad de la replicación y los checkpoints, verifica los permisos y esquemas del destino, cambia los endpoints y las suscripciones, y valida las posiciones al reanudar. Si el origen no se puede recuperar, se pueden perder datos que no alcanzaron a replicarse; mide también la reproducción duplicada.

</details>

## 11. ¿Un heartbeat de Apache MirrorHeartbeatTask demuestra que la replicación de los datos de origen está sana?

<details>
<summary>Mostrar respuesta</summary>

No. La tarea puede emitir un heartbeat sin leer datos del origen. Comprueba también el avance de las particiones, los errores y la actualidad de los checkpoints. Distingue esta clase de Apache de los campos que admite el CRD v1 de Strimzi 1.3.

</details>

## 12. ¿Cuáles son los campos de topics internos de Connect v1 y qué requisitos de particiones y retención tienen?

<details>
<summary>Mostrar respuesta</summary>

`spec.configStorageTopic`, `spec.offsetStorageTopic` y `spec.statusStorageTopic`. Usa compactación y una partición para el topic de configuración. Establece el grupo de workers con `spec.groupId`; los offsets de los grupos de los sinks son independientes.

</details>

## 13. ¿`sync.topic.acls.enabled=true` copia sin cambios toda la política de seguridad del clúster de origen?

<details>
<summary>Mostrar respuesta</summary>

No. Kafka 4.3.1 procesa ACL de topics literales seleccionados, excluye `ALLOW WRITE` y reduce `ALLOW ALL` a `READ`. No migra todos los usuarios, las políticas del clúster ni las políticas externas de IAM. El ejemplo administra por separado las políticas del destino.

</details>

## 14. ¿Qué hay que tener en cuenta al interpretar `replication-latency-ms` y la compresión entre regiones?

<details>
<summary>Mostrar respuesta</summary>

Mide el tiempo de confirmación del destino menos la marca de tiempo del registro; le afectan la diferencia entre relojes, el modo de marcas de tiempo y la reproducción. La compresión del productor de destino en un worker de la región de destino no reduce el tráfico de lectura del origen que ya cruzó regiones.

</details>

## 15. ¿Dónde se definen el destino y el origen en KafkaMirrorMaker2 v1?

<details>
<summary>Mostrar respuesta</summary>

En `spec.target` y `spec.mirrors[].source`. El destino requiere un alias, `bootstrapServers`, `groupId` y los nombres de los tres topics internos. No uses la estructura anterior `connectCluster`/`clusters`/`heartbeatConnector`.

</details>

## 16. Escribe el KafkaConnector de Debezium PostgreSQL del capítulo y describe sus requisitos previos.

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnector
metadata:
  name: orders-db-source
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: orders-db.REPLACE.ap-northeast-2.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${dir:/mnt/debezium:password}"
    database.dbname: orders
    database.sslmode: verify-full
    database.sslrootcert: /mnt/rds-ca/ca.crt
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    publication.name: debezium_orders_pub
    publication.autocreate.mode: disabled
    table.include.list: 'public[.]orders,public[.]order_items'
    snapshot.mode: initial
```

Prepara la replicación lógica, los privilegios, la publicación y una identidad de réplica adecuada. Lee la contraseña mediante el proveedor permitido del directorio de Secrets y verifica el nombre de host TLS de la base de datos. Usa una sola tarea y supervisa el WAL retenido por una ranura que se haya quedado atascada.

</details>

## 17. ¿Qué condiciones clave permiten sincronizar los offsets de grupo en el ejemplo MM2 v1 del capítulo?

<details>
<summary>Mostrar respuesta</summary>

Haz coincidir la política de replicación del origen y de los checkpoints, así como la ubicación de `offset-syncs`, y habilita `sync.group.offsets.enabled=true`. Se necesitan asignaciones/checkpoints válidos y permisos; el grupo de destino debe estar inactivo o no existir. Los consumidores activos no se sobrescriben. Usa la estructura de origen/destino de `mm2.yaml` del capítulo.

</details>

## 18. ¿`IdentityReplicationPolicy` y `topicsPattern` hacen seguras las escrituras bidireccionales arbitrarias?

<details>
<summary>Mostrar respuesta</summary>

No. Identity pierde la información del prefijo de origen y no tiene una detección de ciclos equivalente a la política predeterminada. Diseña la propiedad direccional de los topics, los filtros, las políticas de escritura y el cambio de tráfico. Los filtros de topics no resuelven automáticamente los conflictos de datos ni los duplicados.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Siguiente cuestionario](./06-msk-integration-quiz.md)
