# Cuestionario sobre fundamentos de Kafka

Este cuestionario evalúa tu comprensión del modelo de broker/topic/partition de Kafka, las garantías de orden, el rebalancing de consumer groups, KRaft y la configuración de replicación/durabilidad.

## Preguntas de opción múltiple

1. ¿Dentro de qué alcance garantiza Kafka el orden de los mensajes?
   - A) En todo el cluster
   - B) En todo un topic (en todas sus partitions)
   - C) Solo dentro de la misma partition
   - D) Solo dentro del mismo consumer group

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Solo dentro de la misma partition**

**Explicación:**
Kafka solo garantiza el orden de los mensajes dentro de una única partition. Si un topic tiene múltiples partitions, no hay un orden relativo garantizado entre los mensajes almacenados en distintas partitions, independientemente del orden en que el producer los haya enviado. Para conservar el orden de los eventos de una entidad específica (por ejemplo, eventos de un ID de pedido determinado), debes usar una key que identifique esa entidad para que todos sus eventos se enruten a la misma partition.
</details>

2. ¿A qué se refiere ISR (In-Sync Replicas)?
   - A) El conjunto de todos los brokers registrados en el cluster
   - B) El conjunto de replicas que están suficientemente sincronizadas con el leader
   - C) El conjunto de replicas que no son elegibles para convertirse en leader
   - D) El conjunto de consumers pertenecientes a un consumer group

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El conjunto de replicas que están suficientemente sincronizadas con el leader**

**Explicación:**
ISR (In-Sync Replicas) es el conjunto de follower replicas (más el leader en sí) cuyos datos están suficientemente sincronizados con la leader replica de la partition. Cuando una escritura se envía con `acks=all`, solo se considera correcta cuando cada replica del ISR ha recibido el mensaje. Un follower que se queda demasiado atrás respecto del leader se elimina del ISR, lo que actúa como salvaguarda para la consistencia de los datos durante fallos.
</details>

3. ¿Cuál es el valor predeterminado de la configuración `enable.auto.commit` de un Kafka consumer?
   - A) `false`
   - B) `true`
   - C) Depende de la configuración del broker
   - D) La configuración se eliminó a partir de Kafka 3.x

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `true`**

**Explicación:**
El valor predeterminado de `enable.auto.commit` es `true`; en ese caso, el consumer confirma automáticamente los offsets cada `auto.commit.interval.ms` (5 segundos de forma predeterminada). Esto es conveniente, pero el offset puede confirmarse antes de que el procesamiento del mensaje termine realmente, con riesgo de pérdida de mensajes en caso de fallo. Para confirmar solo después de que el procesamiento se complete, configura `enable.auto.commit=false` y llama explícitamente a `commitSync()` o `commitAsync()`.
</details>

4. ¿Cuál de las siguientes opciones NO desencadena un consumer group rebalance?
   - A) Un nuevo consumer se une al group
   - B) Un consumer no envía un heartbeat dentro de `session.timeout.ms`
   - C) Cambia el número de partitions del topic
   - D) Un producer envía un mensaje con `acks=all`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Un producer envía un mensaje con `acks=all`**

**Explicación:**
Los rebalances ocurren cuando cambia la membresía del consumer group o cambia el diseño de partitions del topic suscrito: consumers que se unen o salen, timeouts de heartbeat, superar `max.poll.interval.ms` o un cambio en el conteo de partitions son los desencadenantes típicos. `acks`, en cambio, es una configuración del lado del producer que determina cómo el producer confirma que una escritura se completó; no tiene nada que ver con la asignación de partitions ni con el rebalancing de un consumer group.
</details>

5. ¿A partir de qué versión de Kafka KRaft (Kafka Raft metadata mode) pasó a estar listo para producción (GA)?
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Kafka 3.3**

**Explicación:**
KRaft se introdujo por primera vez como una vista previa de acceso anticipado en Kafka 2.8, pero no estuvo listo para producción (General Availability) hasta Kafka 3.3. Continuó estabilizándose en versiones menores posteriores, y Kafka 4.0 eliminó por completo el modo ZooKeeper, convirtiendo a KRaft en el único mecanismo de gestión de metadata compatible.
</details>

6. ¿En qué versión de Kafka se eliminó por completo el modo ZooKeeper, dejando KRaft como el único mecanismo de gestión de metadata?
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Kafka 4.0**

**Explicación:**
Kafka 4.0 (publicado en marzo de 2025) eliminó por completo el modo de gestión de metadata basado en ZooKeeper. A partir de esta versión, los nuevos clusters solo pueden inicializarse en modo KRaft, y los clusters existentes basados en ZooKeeper deben completar una migración a KRaft en Kafka 3.x antes de actualizar a 4.0.
</details>

7. Si un topic está configurado con `replication.factor=3` y `min.insync.replicas=2`, y el producer usa `acks=all`, ¿cuál es el número máximo de fallos simultáneos de brokers que el topic puede tolerar mientras sigue aceptando escrituras?
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) 1**

**Explicación:**
Con un replication factor de 3, cada partition se almacena en 3 replicas. `min.insync.replicas=2` significa que al menos 2 replicas deben permanecer en el ISR para que una escritura con `acks=all` tenga éxito. Si falla un broker, las 2 replicas restantes permanecen en el ISR, por lo que las escrituras continúan teniendo éxito. Pero si dos brokers fallan simultáneamente, el ISR se reduce a solo 1, ya no satisface `min.insync.replicas`, y el producer recibe una `NotEnoughReplicasException`.
</details>

8. ¿Qué configuración de `acks` del producer tiene la menor durabilidad pero la menor latencia?
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) `acks=0`**

**Explicación:**
`acks=0` significa que el producer no espera ninguna respuesta del broker en absoluto: considera que la escritura tuvo éxito en el instante en que se envía el mensaje. Es la opción más rápida en términos de latencia y throughput, pero si ocurre un problema de red o un fallo del broker, no hay forma de saber si el mensaje se almacenó realmente, por lo que es la opción más riesgosa para la pérdida de datos. Ten en cuenta que `acks=all` y `acks=-1` significan lo mismo: la configuración más segura, que exige que cada replica del ISR confirme la escritura antes de que se considere exitosa.
</details>

9. En la arquitectura KRaft, ¿cómo se llama el único node que realmente procesa los cambios de metadata del cluster (elección del partition leader, creación de topics, etc.)?
   - A) Controller Voter
   - B) Active Controller
   - C) Partition Leader
   - D) Metadata Broker

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Active Controller**

**Explicación:**
En KRaft, varios controller voters (normalmente 3 o 5, un número impar para el quorum de Raft) participan en la replicación del metadata log, y uno de ellos se elige como Active Controller mediante consenso Raft. Solo el Active Controller procesa realmente los cambios de metadata del cluster; si falla, se elige un nuevo Active Controller entre los voters restantes.
</details>

10. ¿Cuál es el propósito principal de usar `CooperativeStickyAssignor`?
    - A) Cambiar cómo el producer aplica hash a las partition keys
    - B) Minimizar el movimiento de partitions durante un rebalance, reduciendo su costo
    - C) Ajustar dinámicamente el número de voters en el controller quorum
    - D) Aumentar el número de replicas incluidas en el ISR

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Minimizar el movimiento de partitions durante un rebalance, reduciendo su costo**

**Explicación:**
El protocolo tradicional de eager rebalancing requiere que cada consumer libere todas las partitions que posee y reciba una nueva asignación desde cero cada vez que comienza un rebalance. `CooperativeStickyAssignor` usa un protocolo de cooperative rebalancing que solo reasigna las partitions que realmente necesitan moverse, permitiendo que los consumers existentes conserven las partitions que ya poseen. Esto reduce el número de partitions cuyo consumo se interrumpe durante un rebalance, mitigando el impacto general en el throughput.
</details>

## Preguntas de respuesta breve

11. ¿Cuál es el nombre del topic interno de Kafka donde se almacena la metadata del cluster en modo KRaft?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `__cluster_metadata`**

**Explicación:**
En modo KRaft, en lugar de depender de un ensemble ZooKeeper separado, Kafka almacena la metadata del cluster (información de topics/partitions, ACLs, historial de cambios de estado del controller, etc.) como un event log en un topic interno llamado `__cluster_metadata`. Los controller quorum voters replican este topic mediante el protocolo Raft, y los brokers se suscriben a él para mantenerse al día con la metadata más reciente. Este diseño permite que Kafka reutilice su propio modelo central de almacenamiento — el partition log — también para la gestión de metadata.
</details>

12. ¿Qué configuración del producer se habilita para evitar escrituras duplicadas de mensajes causadas por reintentos de red?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `enable.idempotence` (el idempotent producer, `enable.idempotence=true`)**

**Explicación:**
Configurar `enable.idempotence=true` hace que el producer adjunte un número de secuencia y un producer ID a cada mensaje, que el broker usa para detectar y descartar escrituras duplicadas causadas por reintentos. Esta configuración es la base para lograr escrituras exactly-once dentro de Kafka (a nivel de topic), y combinarla con `transactional.id` extiende esa garantía a escrituras atómicas que abarcan múltiples partitions o topics.
</details>

13. ¿Cuál es el término para la situación en la que el tráfico se concentra en un pequeño número de partitions porque la partition key elegida tiene baja cardinalidad (pocos valores distintos)?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Hot Partition**

**Explicación:**
Una hot partition ocurre cuando los valores elegidos como partition key no tienen suficiente cardinalidad (valores distintos), o cuando un valor en particular aparece con una frecuencia desproporcionada. Por ejemplo, si la mayor parte del tráfico se concentra en un puñado de IDs de clientes grandes, solo las partitions a las que esas keys aplican hash reciben carga excesiva mientras el resto permanece inactivo. Esto anula el beneficio del procesamiento paralelo por consumers, por lo que la distribución del tráfico debe revisarse cuidadosamente al diseñar la key.
</details>

14. ¿Qué configuración controla el tiempo máximo que un consumer puede dedicar a procesar mensajes entre llamadas a `poll()`, y desencadena un rebalance si se excede porque se considera que el consumer ha abandonado el group?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `max.poll.interval.ms`**

**Explicación:**
`max.poll.interval.ms` especifica el tiempo máximo permitido entre llamadas consecutivas a `poll()` (5 minutos de forma predeterminada). Si el procesamiento de los records devueltos por una sola llamada a `poll()` tarda más que esto, el broker considera que el consumer ya no está vivo, lo elimina del group y desencadena un rebalance. Este es un mecanismo separado de `session.timeout.ms`, que se rige por un heartbeat thread separado; si la lógica de procesamiento es lenta, debes aumentar este valor o reducir `max.poll.records` para disminuir el tamaño del batch.
</details>

## Preguntas prácticas

15. Escribe el comando `kafka-topics.sh` para crear un topic llamado `events` con 8 partitions, un replication factor de 3 y `min.insync.replicas=2`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**Explicación:**
`--partitions 8` divide el topic en 8 partitions, lo que permite que hasta 8 consumers lo consuman en paralelo. `--replication-factor 3` copia cada partition en 3 brokers, preservando los datos ante hasta 2 fallos de brokers. `--config min.insync.replicas=2` exige que al menos 2 replicas permanezcan en el ISR para que una escritura con `acks=all` tenga éxito, lo que combinado con el replication factor mantiene las escrituras disponibles ante el fallo de un solo broker.
</details>

16. Escribe una configuración de ejemplo de `server.properties` para un quorum de controllers KRaft dedicado de 3 nodes (solo rol de controller, sin rol de broker). Usa los node IDs 90, 91 y 92.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```properties
# server.properties for one dedicated controller node (e.g., node.id=90)
process.roles=controller
node.id=90

controller.quorum.voters=90@kraft-controller-0:9093,91@kraft-controller-1:9093,92@kraft-controller-2:9093

listeners=CONTROLLER://:9093
controller.listener.names=CONTROLLER

log.dirs=/var/lib/kafka/controller-data
```

**Explicación:**
Configurar `process.roles=controller` significa que este node solo actúa como controller quorum voter y no sirve tráfico de broker. En clusters más grandes, separar el rol de controller del rol de broker de esta manera evita que la carga de procesamiento de metadata compita con la carga de procesamiento de datos, mejorando la estabilidad. `controller.quorum.voters` debe listar cada node que participa en el controller quorum como `node.id@host:port`, y usar un conteo impar (3 o 5) permite que el cluster calcule una mayoría clara de quorum Raft.
</details>

17. Escribe una configuración de producer (formato de propiedades Java) que combine `acks=all`, escrituras idempotentes y un transactional ID para lograr escrituras exactly-once.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```properties
bootstrap.servers=broker1:9092,broker2:9092,broker3:9092
acks=all
enable.idempotence=true
transactional.id=order-producer-1
max.in.flight.requests.per.connection=5
retries=2147483647
```

**Explicación:**
`acks=all` exige que cada replica del ISR reciba el mensaje antes de que la escritura se considere exitosa, y `enable.idempotence=true` elimina las escrituras duplicadas causadas por reintentos. Configurar `transactional.id` convierte al producer en un transactional producer, lo que le permite usar las APIs `initTransactions()`, `beginTransaction()` y `commitTransaction()` para escribir atómicamente en múltiples partitions. Configurar `retries` con un valor muy alto es seguro una vez que se configura `enable.idempotence=true`, ya que el orden y los duplicados se gestionan automáticamente; `max.in.flight.requests.per.connection` debe mantenerse en 5 o menos para evitar romper las garantías de orden.
</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [Siguiente cuestionario: Strimzi Operator](./02-strimzi-operator-quiz.md)
