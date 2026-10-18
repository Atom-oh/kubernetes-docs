# Parte 1: Fundamentos de Kafka

> **Última actualización**: 16 de octubre de 2026. Apache Kafka 4.3.1, compatible con Strimzi 1.3.0.
> **Validación**: Diecinueve comprobaciones usaron las clases de configuración reales de Kafka 4.3.1 para validar opciones, valores predeterminados y conflictos. No se inició ningún broker ni clúster de EKS.

## 1. Brokers, temas y particiones

Kafka almacena eventos en registros de particiones, lo que permite que los productores y consumidores avancen de forma independiente. Un broker puede almacenar réplicas de particiones de varios temas; no necesita contener un tema entero.

| Término | Significado |
| --- | --- |
| Broker | Rol de servidor que almacena réplicas de datos y gestiona solicitudes |
| Tema | Categoría lógica de eventos |
| Partición | Registro ordenado al que se agregan elementos; la retención y la compactación pueden eliminar registros |
| Offset | Posición dentro de una partición, no un ID global; las eliminaciones y transacciones pueden dejar huecos visibles |
| Factor de replicación | Número de réplicas de una partición, gestionado mediante metadatos de creación o reasignación |
| Líder / seguidor | Los líderes gestionan las escrituras y los seguidores replican; la obtención de datos por parte de los seguidores, si está configurada, puede servir lecturas de consumidores |
| ISR | Réplicas suficientemente sincronizadas con el líder, incluido el propio líder |

![Ejemplo de un grupo de KafkaConsumer con tres consumidores asignados a tres particiones; por lo general, un consumidor puede ser propietario de varias particiones](../../.gitbook/assets/en-data-on-eks-kafka-01-kafka-fundamentals-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-kafka-01-kafka-fundamentals-0.html)

El diagrama 3:3 es un ejemplo. Con la asignación automática de grupos de `subscribe()` de KafkaConsumer, una partición se asigna a un miembro del grupo a la vez; un miembro puede ser propietario de varias particiones. El uso manual de `assign()` se gestiona por separado. Varios grupos pueden consumir el mismo tema de forma independiente. Los Share Groups/KafkaShareConsumer de Kafka 4.x utilizan un modelo distinto para compartir y confirmar.

## 2. Orden y claves de partición

Kafka define el orden del registro **dentro de una partición**. No establece automáticamente el orden global del tema ni el orden de las marcas de tiempo de los eventos de negocio.

Para que el enrutamiento de la misma clave sea coherente, se requiere una serialización, particionador y cantidad de particiones coherentes. Aumentar la cantidad de particiones puede cambiar la asignación basada en hash. Los particionadores personalizados y las particiones elegidas explícitamente también afectan al enrutamiento. Varios productores, los reintentos y el procesamiento paralelo de la aplicación requieren su propio contrato de orden.

El enrutamiento de claves nulas depende del cliente o del particionador. Una gran cardinalidad de claves por sí sola no garantiza una carga equilibrada; unas pocas claves con frecuencias desproporcionadamente altas aún pueden crear particiones sobrecargadas.

Este comando crea un tema en un **clúster al que ya se puede acceder y que cuenta con al menos tres brokers**. Añade `--command-config client.properties` para los listeners autenticados. No lo apliques sin cambios a la configuración de aprendizaje de un solo nodo que aparece más abajo.

```bash
: "${DOCS_BOOTSTRAP:?Set the existing Kafka bootstrap host:port}"
kafka-topics.sh --create --bootstrap-server "$DOCS_BOOTSTRAP" \
  --topic orders --partitions 6 --replication-factor 3 \
  --config min.insync.replicas=2
```

## 3. Grupos de consumidores y offsets

Los grupos basados en particiones pueden tener miembros inactivos cuando hay más consumidores que particiones. El rendimiento del productor, los discos, la red y el procesamiento de la aplicación también afectan a la concurrencia; la cantidad de particiones por sí sola no permite predecir el rendimiento.

### Diferenciar los protocolos de grupo

El consumidor Java de Kafka 4.3 usa `classic` como valor predeterminado de `group.protocol`.

| Opción | Asignación y tiempos de espera |
| --- | --- |
| `classic` | Asignadores del cliente y `session.timeout.ms` / `heartbeat.interval.ms` |
| `consumer` | Asignadores del servidor y `group.consumer.session.timeout.ms` / `group.consumer.heartbeat.interval.ms` del broker |

El rebalanceo eager clásico revoca un conjunto amplio de asignaciones. CooperativeStickyAssignor mueve de forma incremental las particiones que necesitan reasignarse. El nuevo protocolo de consumidor también realiza una conciliación incremental en el servidor. No todos los rebalances necesariamente pausan a todo el grupo. No traslades al nuevo protocolo las suposiciones sobre los tiempos de espera y los asignadores del cliente clásico.

`max.poll.interval.ms` tiene un valor predeterminado de 300000 ms. Con la pertenencia estática (`group.instance.id`), superar ese valor no reasigna las particiones de inmediato: el consumidor deja de enviar heartbeats, y el tiempo de espera de sesión aplicable también afecta a la reasignación.

### Offsets y finalización del trabajo de negocio

Un offset confirmado suele identificar la siguiente posición que se leerá. La posición de obtención del cliente y el trabajo externo completado son hechos distintos. Con procesamiento asíncrono o paralelo, no confirmes offsets que superen registros cuyo trabajo aún no haya terminado.

| Método | Significado y consideración |
| --- | --- |
| Confirmación automática | `enable.auto.commit=true`, intervalo predeterminado de 5000 ms; no determina cuándo se completa el trabajo de negocio |
| `commitSync()` | Espera a que termine la llamada; el impacto en la latencia depende del procesamiento por lotes y la frecuencia |
| `commitAsync()` | Haz seguimiento de los errores y el progreso mediante callbacks; no vuelvas a intentar offsets obsoletos a ciegas ni hagas retroceder el progreso confirmado |

Confirmar antes del procesamiento puede provocar la pérdida de trabajo tras un fallo; confirmar después del procesamiento puede repetir efectos durante la recuperación. Prueba los fallos, reinicios y rebalances junto con la salida de la aplicación.

## 4. Alcance de la semántica exactamente una vez

`enable.idempotence` evita las escrituras duplicadas en el registro de una misma transmisión del productor durante los reintentos. No es una clave general de deduplicación para una aplicación que envía el mismo evento de negocio como un nuevo envío.

Para el procesamiento de Kafka a Kafka, confirma los registros de salida y los **siguientes offsets de entrada** en la misma transacción, y haz que los consumidores lean con `read_committed`. Establecer una cadena `transactional.id` no implementa esa lógica de procesamiento. Las bases de datos y API externas requieren contratos independientes de transacción del sink, idempotencia y recuperación.

**`producer.properties`**

```properties
bootstrap.servers=127.0.0.1:19092
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
acks=all
enable.idempotence=true
transactional.id=orders-writer-1
max.in.flight.requests.per.connection=5
delivery.timeout.ms=120000
```

**`consumer.properties`**

```properties
bootstrap.servers=127.0.0.1:19092
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=org.apache.kafka.common.serialization.StringDeserializer
group.id=order-processor
group.protocol=consumer
enable.auto.commit=false
isolation.level=read_committed
max.poll.interval.ms=300000
```

El procesamiento transaccional incluye `initTransactions()`, `beginTransaction()`, los envíos de salida, `sendOffsetsToTransaction(...)`, `commitTransaction()` y la gestión de abortos y recuperación. Los productores simultáneos necesitan IDs transaccionales distintos; diseña un comportamiento estable de reinicio y fencing para los escritores lógicos.

La idempotencia explícita requiere `acks=all`, `retries>0` y `max.in.flight.requests.per.connection<=5`. Los conflictos generan ConfigException. La idempotencia predeterminada implícita puede desactivarse por opciones en conflicto. Un valor alto de retries no anula límites de tiempo como `delivery.timeout.ms`.

## 5. Metadatos de KRaft

KRaft llegó como función de acceso anticipado en Kafka 2.8, pasó a estar listo para producción en la versión 3.3 y es el único modo disponible desde la eliminación de ZooKeeper en Kafka 4.0. Los procesos de controlador dedicados no tienen que atender el tráfico de datos de los brokers, por lo que los controladores no son necesariamente un subconjunto de los brokers de datos.

Los votantes del controlador replican el registro Raft de metadatos, con un controlador activo. En producción suelen implementarse tres o cinco votantes. Los grupos de tamaño par también tienen una mayoría calculable; los tamaños impares usan los recursos de forma eficiente para la misma tolerancia a fallos.

`__cluster_metadata` es el nombre del registro interno de metadatos, no un tema de aplicación ordinario gestionado mediante KafkaProducer/KafkaConsumer. Eliminar ZooKeeper no elimina la responsabilidad de gestionar el cuórum de controladores, el almacenamiento, las actualizaciones y la monitorización.

### Cuórums dinámicos y estáticos

Los cuórums dinámicos usan `controller.quorum.bootstrap.servers` como direcciones iniciales de descubrimiento, no como pertenencia de votantes. El formato inicial del almacenamiento y el arranque del cuórum deben coincidir en el ID del clúster, los ID de directorio y los votantes iniciales. Para realizar cambios, usa los procedimientos compatibles de adición o eliminación de controladores.

`controller.quorum.voters` estático sigue siendo compatible con Kafka 4.3.1. No lo establezcas para un cuórum dinámico. Cambiar solo las direcciones iniciales no migra automáticamente un cuórum estático.

Este archivo es para **aprendizaje local en un solo nodo**, no para alta disponibilidad. Usa listeners PLAINTEXT de loopback. Antes del inicio, un directorio de datos nuevo necesita el procedimiento adecuado de formato del almacenamiento y arranque del cuórum. Nunca formatees de forma arbitraria datos de Kafka existentes.

**`combined-lab.properties`**

```properties
# Local, single-node configuration for learning; not an HA deployment.
process.roles=broker,controller
node.id=1
controller.quorum.bootstrap.servers=127.0.0.1:19093
listeners=BROKER://127.0.0.1:19092,CONTROLLER://127.0.0.1:19093
advertised.listeners=BROKER://127.0.0.1:19092,CONTROLLER://127.0.0.1:19093
listener.security.protocol.map=BROKER:PLAINTEXT,CONTROLLER:PLAINTEXT
controller.listener.names=CONTROLLER
inter.broker.listener.name=BROKER
log.dirs=./kafka-lab-data
# Single-node internal-topic settings are for this lab only.
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
share.coordinator.state.topic.replication.factor=1
share.coordinator.state.topic.min.isr=1
```

Un listener personalizado `BROKER` necesita una asignación explícita de protocolo. Kafka 4.3.1 puede proporcionar una asignación PLAINTEXT para el listener `CONTROLLER` predeterminado, exclusivo de controladores, en las configuraciones pertinentes; la ausencia de una línea de asignación no invalida todas las configuraciones de controlador.

En EKS, usa la configuración, los certificados y el almacenamiento generados por Strimzi en la Parte 2. No edites directamente el archivo server.properties de un Pod gestionado por el Operator. Configura TLS, autenticación y autorización según sea necesario para los listeners de producción.

## 6. Replicación, disponibilidad de escritura y durabilidad

RF=3 por sí solo no garantiza que todos los datos sobrevivan a cualquier fallo de dos brokers. Ten en cuenta el progreso real de la replicación, el ISR en el momento de la confirmación, la elección de líder elegible, los fallos de almacenamiento o de red y el cuórum de controladores.

Si las tres réplicas pertenecen inicialmente a un ISR en buen estado, una partición que usa `min.insync.replicas=2` y `acks=all` puede continuar con dos miembros del ISR tras el fallo de un broker, si se mantienen las demás condiciones. La transición de líder aún puede causar errores o reintentos. Las escrituras fallan o se rechazan cuando el ISR queda por debajo del mínimo; los detalles del error dependen del momento.

| acks | Confirmación | Interpretación |
| --- | --- | --- |
| `0` | No se espera respuesta del broker | No se confirma el almacenamiento; el offset devuelto es -1 |
| `1` | El líder responde después de registrar los datos | Riesgo de perder al líder antes de la replicación a los seguidores |
| `all` / `-1` | Espera al ISR completo actual | Evalúalo junto con el ISR mínimo, la replicación y la política de elección de líder |

`acks=all` no significa que todos los discos hayan completado fsync para cada registro. Tampoco basta con acks para garantizar el rendimiento o las clasificaciones de p99. Mide el costo de la confirmación con una carga, procesamiento por lotes y redes comparables.

Puedes cambiar el ISR mínimo de la siguiente manera. Cambiar el propio factor de replicación requiere reasignar réplicas; no se hace añadiendo `replication.factor` como una configuración ordinaria del tema.

```bash
kafka-configs.sh --bootstrap-server "$DOCS_BOOTSTRAP" \
  --alter --entity-type topics --entity-name orders \
  --add-config min.insync.replicas=2
```


## Próximos pasos y referencias

- [Operator de Strimzi](./02-strimzi-operator.md)
- [Descripción general de Kafka](./README.md)
- [Cuestionario](../../quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
- [Diseño de Kafka](https://kafka.apache.org/43/design/design/)
- [Configuraciones de consumidores](https://kafka.apache.org/43/configuration/consumer-configs/)
- [Configuraciones de productores](https://kafka.apache.org/43/configuration/producer-configs/)
- [Operaciones de KRaft](https://kafka.apache.org/43/operations/kraft/)
- [Aviso de migración y versión 1.3.0 de Strimzi](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.3.0)
