# Parte 8: Cuestionario de mejores prácticas

Este cuestionario evalúa tu comprensión de las mejores prácticas que abarcan toda la serie de profundización en Kafka: diseño de partitions, ajuste de producers/consumers, seguridad (mTLS/SASL) y optimización de costos.

## Preguntas de opción múltiple

1. ¿Qué deberías considerar primero al dimensionar el número de partitions de un topic?
   - A) El número total de brokers en el cluster
   - B) El paralelismo máximo esperado del consumer group
   - C) El número de instancias de producer
   - D) El tamaño disponible del volumen EBS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El paralelismo máximo esperado del consumer group**

**Explicación:**
Una sola partition solo puede ser consumida por una instancia de consumer dentro de un group a la vez, por lo que necesitas decidir hasta qué punto esperas escalar un consumer group y aprovisionar al menos esa cantidad de partitions. Si planeas escalar a 20 instancias de consumer en el pico, necesitas al menos 20 partitions. El número de brokers y el tamaño del volumen EBS son preocupaciones de capacidad sobre qué tan bien el cluster puede alojar un número determinado de partitions, no el factor principal de ese número en sí.
</details>

2. Según la regla práctica clásica de Confluent, ¿cuál era el límite flexible aproximado de partitions por broker?
   - A) 400
   - B) 4,000
   - C) 40,000
   - D) 400,000

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) 4,000**

**Explicación:**
La guía clásica de Confluent sugería un límite flexible de alrededor de 4,000 partitions por broker y 200,000 por cluster. Esto se remonta a cuando el controller basado en ZooKeeper era el cuello de botella de metadata. Los clusters basados en KRaft manejan muchas más partitions gracias a una ruta de metadata del controller mucho más rápida, pero el principio subyacente — no sobreparticionar solo porque puedes — sigue aplicando, y el límite real para una workload determinada debe confirmarse con pruebas de carga.
</details>

3. ¿Cuál de los siguientes NO es un costo real de sobreparticionar un topic?
   - A) Más file handles abiertos por broker
   - B) Mayor uso de memoria en buffers de producer/broker
   - C) Mayor tiempo de leader election y rebalance ante una falla de broker
   - D) El throughput del consumer group siempre disminuye

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) El throughput del consumer group siempre disminuye**

**Explicación:**
Sobreparticionar sí agrega overhead en file handles, memoria y tiempo de recuperación ante fallas, pero no siempre reduce el throughput; si el paralelismo de consumers puede mantenerse al ritmo, el throughput no necesariamente empeora. De hecho, tener muy pocas partitions limita el throughput al restringir cuántos consumers pueden trabajar en paralelo. El número de partitions es un balance entre paralelismo y overhead, no una pregunta simple de "más siempre es peor/mejor".
</details>

4. ¿Qué garantía se rompe de forma más directa cuando aumentas el número de partitions en un topic con keys?
   - A) El replication factor
   - B) El orden de los mensajes para una key determinada
   - C) Los commits de offsets del consumer group
   - D) La lista ISR entre brokers

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El orden de los mensajes para una key determinada**

**Explicación:**
El partitioner predeterminado calcula `hash(key) % partition_count`, por lo que cambiar el número de partitions cambia a qué partition se asigna la misma key. Como Kafka solo garantiza el orden dentro de una sola partition, los mensajes para la misma key pueden terminar divididos entre partitions antiguas y nuevas, y los consumers ya no pueden confiar en el orden a nivel de key. Los joins basados en co-partitioning en Kafka Streams también pueden romperse como resultado.
</details>

5. ¿A partir de qué versión de Kafka `enable.idempotence` tiene el valor predeterminado `true` sin necesidad de configurarlo explícitamente?
   - A) Kafka 1.0
   - B) Kafka 2.0
   - C) Kafka 3.0
   - D) Kafka 4.0

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Kafka 3.0**

**Explicación:**
`enable.idempotence=true` ha sido el valor predeterminado del producer desde Kafka 3.0, salvo que `acks` o `retries` se sobrescriban explícitamente de una forma incompatible. Asigna al producer un producer ID único y números de secuencia por partition para que el broker pueda deduplicar automáticamente los reintentos.
</details>

6. ¿Qué evita la idempotencia del producer?
   - A) Rebalances del consumer group
   - B) Escrituras duplicadas en el broker causadas por reintentos de red
   - C) Fallas del partition leader
   - D) Errores de compatibilidad del schema registry

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Escrituras duplicadas en el broker causadas por reintentos de red**

**Explicación:**
Cuando un producer no recibe un ack y reintenta el mismo record, sin idempotencia el broker podría terminar almacenando el record dos veces. El PID y los números de secuencia de un producer idempotente permiten que el broker detecte y descarte el duplicado. Ten en cuenta que esto solo deduplica el salto de producer a broker; exactamente una vez de extremo a extremo aún requiere la transactional API además de la idempotencia.
</details>

7. ¿Cuál es el efecto combinado de configurar `acks=all` y `min.insync.replicas=2` en un topic con `replication.factor=3`?
   - A) Las escrituras siempre esperan a las 3 replicas
   - B) Una escritura no se considera completa hasta que al menos 2 replicas (incluido el leader) la tienen
   - C) La compresión se habilita automáticamente
   - D) La partition leader election se deshabilita

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una escritura no se considera completa hasta que al menos 2 replicas (incluido el leader) la tienen**

**Explicación:**
`acks=all` hace que el producer espere confirmación del conjunto actual de in-sync replicas (ISR), y `min.insync.replicas=2` fuerza que las escrituras sean rechazadas directamente si el ISR se reduce por debajo de 2 (leader incluido). Juntas, esta es la configuración estándar de durabilidad que permite que las escrituras continúen de forma segura incluso si falla un solo broker.
</details>

8. ¿Qué sucede cuando un consumer no termina de procesar dentro de `max.poll.interval.ms`?
   - A) El partition leader se reemplaza inmediatamente
   - B) El consumer es expulsado forzosamente del group, lo que dispara un rebalance
   - C) El broker deshabilita automáticamente la compresión para ese topic
   - D) Nada: el consumer simplemente espera el siguiente poll

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El consumer es expulsado forzosamente del group, lo que dispara un rebalance**

**Explicación:**
`max.poll.interval.ms` limita cuánto tiempo puede tardar un consumer entre llamadas sucesivas a `poll()`. Superarlo hace que el broker trate al consumer como muerto, lo expulse del group y dispare un rebalance. Si varios consumers se ralentizan a la vez, esto puede convertirse en cascada en una "tormenta de rebalances".
</details>

9. ¿Cuál es el propósito principal de configurar `group.instance.id` para habilitar static group membership?
   - A) Aumentar automáticamente el throughput del consumer
   - B) Evitar rebalances innecesarios durante reinicios breves de pods
   - C) Mejorar el ratio de compresión del producer
   - D) Acelerar la partition leader election

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Evitar rebalances innecesarios durante reinicios breves de pods**

**Explicación:**
Los consumer pods se reinician con frecuencia en Kubernetes debido a rolling deploys, eventos OOMKilled y situaciones similares. Configurar `group.instance.id` habilita static membership: siempre que el consumer se reconecte dentro de `session.timeout.ms`, reanuda con su asignación de partitions anterior intacta, sin ningún rebalance. Esto evita que los reinicios breves y frecuentes disparen un rebalance completo del group cada vez.
</details>

10. Cuando un `KafkaUser` en Strimzi especifica `authentication.type: tls`, ¿quién firma el certificado de cliente resultante?
    - A) AWS Certificate Manager
    - B) Un certificado autofirmado generado por el propio cliente
    - C) La cluster CA gestionada por Strimzi
    - D) Un cert-manager Issuer desplegado por separado

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) La cluster CA gestionada por Strimzi**

**Explicación:**
Strimzi aprovisiona automáticamente su propia cluster CA cuando se despliega un cluster Kafka y rota los certificados según una programación. Configurar el `authentication.type` de un `KafkaUser` como `tls` hace que Strimzi emita un certificado de cliente firmado por esa cluster CA en un Secret, listo para usarse en conexiones mTLS.
</details>

## Preguntas de respuesta corta

11. ¿Qué término único describe el problema que surge al usar directamente un campo de baja cardinalidad (por ejemplo, `country`) como partition key?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Hot partition**

**Explicación:**
El partitioner predeterminado calcula `hash(key) % partition_count`, por lo que una key de baja cardinalidad con solo un puñado de valores distintos concentrará el tráfico en un pequeño subconjunto de partitions cuando la mayor parte del tráfico comparta el valor dominante, dejando otras partitions inactivas. Esto puede mitigarse eligiendo una key de mayor cardinalidad o agregando salt a una de baja cardinalidad para forzar una distribución más uniforme.
</details>

12. Para pipelines donde importa el procesamiento at-least-once, ¿qué enfoque de commit de offsets (y configuración) debería reemplazar al auto-commit?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Commits manuales con `enable.auto.commit=false`, llamando a `consumer.commitSync()` (o `commitAsync()`) solo después de que termine el procesamiento**

**Explicación:**
Auto-commit puede confirmar un offset antes de que el record correspondiente haya terminado realmente de procesarse, por lo que un crash en medio del procesamiento puede hacer que ese record se pierda efectivamente desde el punto de vista del pipeline, aunque Kafka lo considere "committed". Configurar `enable.auto.commit=false` y hacer commit solo después de que finalice la lógica de negocio garantiza que un crash resulte en que el record se entregue de nuevo y se reprocese, preservando la semántica at-least-once.
</details>

13. ¿Qué recurso importa más que la CPU para la mayoría de las workloads de Kafka broker, y por qué?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Memoria — específicamente, OS page cache**

**Explicación:**
Kafka está diseñado para servir la mayoría de las lecturas desde la page cache, por lo que, en el caso común de consumers que leen datos recientes, la RAM que queda después del heap del broker determina directamente el throughput de lectura. Por eso las instancias optimizadas para memoria (`r6g`/`r7g`, por ejemplo) suelen ofrecer mejor precio/rendimiento para Kafka brokers que las optimizadas para cómputo.
</details>

14. ¿Qué campo de listener de Strimzi restringe qué pods/namespaces pueden llegar al puerto del broker?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `networkPolicyPeers`**

**Explicación:**
Configurar `networkPolicyPeers` en un listener de Strimzi hace que Strimzi genere una `NetworkPolicy` estándar de Kubernetes que solo permite tráfico a ese puerto de listener desde pods/namespaces que coincidan con el `podSelector`/`namespaceSelector` especificado. Esto te permite controlar declarativamente qué workloads pueden siquiera llegar al listener de Kafka.
</details>

15. ¿El cifrado de volúmenes EBS ocurre automáticamente solo porque estás usando el EBS CSI driver? Nombra dos formas de activarlo explícitamente.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: No, no ocurre automáticamente. (1) Habilita la configuración "EBS encryption by default" a nivel de cuenta/región, o (2) configura `encrypted: "true"` (y opcionalmente `kmsKeyId`) en los parámetros de `StorageClass`**

**Explicación:**
El EBS CSI driver no fuerza el cifrado por sí solo: una `StorageClass` sin cifrado produce volúmenes sin cifrar. Necesitas habilitar la configuración "EBS encryption by default" a nivel de cuenta/región para que cada volumen nuevo se cifre automáticamente, o configurar explícitamente `encrypted: "true"` en la `StorageClass` usada para los PVCs de brokers. Como los clusters Kafka con frecuencia transportan datos sensibles para cumplimiento, tratar esto como el valor predeterminado en lugar de una idea tardía es la opción más segura.
</details>

## Preguntas prácticas

16. Escribe configuraciones de producer para un topic crítico para la durabilidad (por ejemplo, procesamiento de pedidos), cubriendo `acks`, la consideración de `min.insync.replicas`, idempotencia y compresión.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```properties
# Producer settings (assuming the topic has replication.factor=3, min.insync.replicas=2)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

**Explicación:**
`acks=all` espera confirmación de todo el ISR, garantizando durabilidad, y combinado con el `min.insync.replicas=2` del topic (asumiendo `replication.factor=3`), el pipeline tolera una falla de un solo broker sin pérdida de datos. `enable.idempotence=true` (el valor predeterminado de Kafka 3.0+) evita escrituras duplicadas por reintentos, y `compression.type=lz4` ofrece un buen equilibrio entre overhead de CPU y ratio de compresión para la mayoría de las workloads. `linger.ms`/`batch.size` intercambian un poco de latencia por batches más grandes y eficientes.
</details>

17. Escribe un recurso `KafkaUser` usando autenticación TLS para una aplicación llamada `order-service` que necesita acceso de lectura/escritura al topic `orders` y acceso de lectura al consumer group `order-service-group`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
          patternType: literal
        operations: ["Read", "Write", "Describe"]
      - resource:
          type: group
          name: order-service-group
        operations: ["Read"]
```

**Explicación:**
Configurar `authentication.type: tls` hace que Strimzi emita automáticamente un certificado de cliente firmado por la cluster CA en un Secret. `authorization.type: simple` con una lista `acls` otorga declarativamente Read/Write/Describe en el topic `orders` y Read en el consumer group `order-service-group`. La label `strimzi.io/cluster` indica al Strimzi Operator a qué cluster `Kafka` pertenece este `KafkaUser`.
</details>

18. Escribe configuraciones de consumer para que los reinicios breves de pods no disparen un rebalance y los offsets solo se confirmen después de que termine el procesamiento.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
heartbeat.interval.ms=15000
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);
    }
    consumer.commitSync();
}
```

**Explicación:**
`group.instance.id` (configurado de forma única, por ejemplo a partir del nombre del pod) habilita static group membership, por lo que el consumer conserva su asignación de partitions existente sin rebalance siempre que se reconecte dentro de `session.timeout.ms`. `enable.auto.commit=false` combinado con `commitSync()` llamado solo después de que termina el procesamiento garantiza que solo los records completamente procesados tengan sus offsets confirmados, preservando la semántica at-least-once. `max.poll.records`/`max.poll.interval.ms` se ajustan al tiempo real de procesamiento por batch para evitar aún más rebalances innecesarios.
</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/kafka/08-best-practices.md) | [Volver al inicio de la profundización en Kafka](../../../data-on-eks/kafka/README.md)
