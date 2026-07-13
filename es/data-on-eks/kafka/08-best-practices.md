# Parte 8: Mejores prácticas

> **Versiones compatibles**: Apache Kafka 3.9, Strimzi 0.45+\
> **Última actualización**: July 9, 2026

A lo largo de esta inmersión profunda cubrimos los fundamentos de Kafka, las operaciones de Strimzi, schema registry, Kafka Connect/MirrorMaker, la integración con MSK y la monitorización. Este documento final consolida las mejores prácticas de preparación para producción por categoría y reúne los elementos clave de las siete partes anteriores en una única checklist para la puesta en marcha.

## 1. Diseño de particiones

### Dimensionamiento del número de particiones

Empieza por el **paralelismo máximo esperado de los consumers** para un topic. Una sola partition solo puede ser consumida por una instancia de consumer dentro de un consumer group determinado a la vez, así que decide hasta dónde esperas escalar un consumer group y provisiona al menos esa cantidad de partitions. Si planeas escalar horizontalmente hasta 20 instancias de consumer en el pico, necesitas al menos 20 partitions.

Crear demasiadas partitions tiene costos reales y debe evitarse:

- **Más manejadores de archivos abiertos**: cada partition mantiene abiertos varios archivos de segmentos de log (`.log`, `.index`, `.timeindex`), por lo que el número de descriptores de archivo abiertos por broker crece linealmente con la cantidad de partitions.
- **Más presión de memoria**: los buffers de batches de producer/consumer y los buffers por hilo de replicación en el broker escalan con la cantidad de partitions.
- **Rebalances y failover más lentos**: la cantidad de trabajo de elección de leader que debe hacer el controller ante un fallo de broker escala con la cantidad de partitions, y los rebalances de consumer group también tardan más.

La regla práctica clásica de Confluent era un límite suave de alrededor de **4,000 partitions por broker y 200,000 por cluster**: orientación de la época en la que el controller basado en ZooKeeper era el cuello de botella de metadatos. Los clusters basados en KRaft (quórum de controllers de Kafka 3.x+) manejan cantidades de partitions mucho mayores gracias a una ruta de metadatos del controller mucho más rápida, pero el principio sigue siendo válido: no crees partitions de más solo porque puedes, y valida el límite real para tu workload con pruebas de carga reales.

```bash
# Check total partition count and distribution per broker
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# Inspect partition/leader distribution for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### Elección de una clave de partición

Elige una clave con **alta cardinalidad y distribución uniforme** para evitar partitions calientes. El partitioner predeterminado aplica hash a la clave con murmur2 y toma el módulo con el número de partitions, por lo que una clave de baja cardinalidad (por ejemplo, `country` o `status` con solo un puñado de valores distintos) sobrecargará las pocas partitions que coincidan con tus valores de tráfico dominantes mientras otras permanecen inactivas. Prefiere un campo con cardinalidad suficientemente alta (por ejemplo, `user_id`) o añade salt a una clave de baja cardinalidad (agrega un sufijo aleatorio o derivado de timestamp) para forzar una distribución más uniforme.

### Manejo cuidadoso de cambios en el número de particiones

Aumentar el número de partitions en un topic **con clave** rompe el mapeo de clave a partition. Como `hash(key) % partition_count` cambia en cuanto cambia `partition_count`, la misma clave puede caer en una partition distinta después del cambio respecto a donde caía antes. Esto causa dos problemas concretos:

- **Orden roto**: Kafka solo garantiza el orden dentro de una partition, por lo que una vez que los mensajes de la misma clave se dividen entre partitions, los consumers ya no pueden confiar en el orden a nivel de clave.
- **Co-particionamiento roto**: los joins en Kafka Streams (y similares) requieren que los topics unidos compartan el mismo número de partitions y el mismo esquema de particionamiento. Cambiar las partitions solo en un lado de un join lo rompe.

Decide el número de partitions con margen durante la planificación de capacidad y, si un topic de producción ya depende del orden basado en clave o de joins, prefiere migrar a un topic nuevo antes que aumentar las partitions del existente.

## 2. Ajuste de producers

| Configuración | Valor recomendado | Propósito |
|---------|--------------------|---------|
| `acks` | `all` (para topics críticos para durabilidad) | Esperar confirmación de todas las réplicas sincronizadas (ISR) para que un fallo de broker no pierda datos |
| `min.insync.replicas` (configuración de topic/broker) | `2` (con replication.factor=3) | Combinado con `acks=all`, requiere que la escritura llegue al menos a 2 réplicas antes de completarse correctamente; se configura en el topic (`kafka-configs.sh --entity-type topics`) o como valor predeterminado del broker, no como propiedad del producer client |
| `linger.ms` | `5`–`20` | Intercambiar una pequeña cantidad de latencia por batches más grandes y mayor throughput |
| `batch.size` | `32768`–`65536` (32–64KB) | Aumentar los bytes máximos por batch para incrementar el throughput por request |
| `enable.idempotence` | `true` | Evitar escrituras duplicadas causadas por reintentos del producer |
| `compression.type` | `lz4` or `zstd` | Reducir costos de red y almacenamiento |

```properties
# Producer settings for durability-critical topics (orders, payments, etc.)
# (min.insync.replicas is a topic/broker setting, not a producer property — shown here for reference only)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

`enable.idempotence=true` ha sido **el valor predeterminado desde Kafka 3.0**, a menos que sobrescribas explícitamente `acks` o `retries` de una forma incompatible con él. Asigna al producer un ID de producer único y números de secuencia por partition para que el broker pueda deduplicar de forma transparente los reintentos causados por errores transitorios de red. Esto es distinto de la semántica exactamente una vez completa: la idempotencia solo elimina duplicados en el salto de producer a broker; la semántica exactamente una vez real de extremo a extremo requiere también la API transaccional (`transactional.id`).

`lz4` ofrece un buen equilibrio entre sobrecarga de CPU y ratio de compresión para la mayoría de workloads. `zstd` comprime mejor — útil para payloads con mucho JSON/texto — a costa de un uso de CPU algo mayor. `gzip` comprime bien, pero consume suficiente CPU como para que generalmente no se recomiende para producers de alto throughput.

## 3. Ajuste de consumers

### Evitar tormentas de rebalance

Si el procesamiento tarda más que `max.poll.interval.ms` (5 minutos por defecto), el consumer es expulsado forzosamente de su group, lo que desencadena un rebalance. Cuando varios consumers se ralentizan a la vez, esto puede convertirse en cascada en una "tormenta de rebalance" con interrupciones repetidas del group.

```properties
# Tune poll-related settings around your actual per-batch processing time
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

Reducir `max.poll.records` disminuye cuántos records devuelve una sola llamada a `poll()`, acortando la ventana de procesamiento entre polls. Aumentar `max.poll.interval.ms` da más margen al procesamiento lento antes de la expulsión. La solución más robusta es arquitectónica: mover el procesamiento pesado fuera del poll loop por completo y llevarlo a un pool separado de worker threads, usando polling solo para obtener y entregar trabajo.

### Commits manuales de offset

Para pipelines donde importa el procesamiento at-least-once (procesamiento de pedidos, pagos), el auto-commit (`enable.auto.commit=true`) puede confirmar un offset antes de que el record correspondiente haya terminado realmente de procesarse; si el consumer falla entre medias, ese record se pierde efectivamente desde la perspectiva del pipeline aunque haya sido "committed".

```properties
enable.auto.commit=false
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);          // business logic
    }
    consumer.commitSync();        // commit only after processing succeeds
}
```

### Membresía estática de group

Los consumer pods en Kubernetes se reinician con frecuencia: rolling deploys, reinicios por OOMKilled, reemplazo de nodes. Por defecto, que un consumer salga y vuelva a unirse a un group desencadena un rebalance completo, así que los reinicios breves y frecuentes causan pausas de procesamiento repetidas e innecesarias en todo el group. Configurar `group.instance.id` habilita la membresía estática: si el consumer se reconecta dentro de `session.timeout.ms`, reanuda con su asignación anterior de partitions intacta, sin ningún rebalance.

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id` debe ser único por pod; normalmente se obtiene del nombre de un pod de StatefulSet o se inyecta mediante la downward API.

## 4. Seguridad

### mTLS (cifrado de transporte + autenticación mutua)

Strimzi aprovisiona y rota automáticamente su propia CA de cluster cuando se despliega un cluster de Kafka. Configurar el tipo de un listener como `tls` cifra el tráfico client-broker, y dar a un `KafkaUser` el tipo de autenticación `tls` hace que Strimzi emita un certificado de cliente firmado por esa CA de cluster.

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

### SASL/SCRAM

Para entornos donde distribuir y rotar certificados de cliente no es práctico (apps heredadas, herramientas de terceros), SASL/SCRAM basado en username/password (`scram-sha-512`) es una alternativa sólida. Configura el tipo de autenticación del listener como `scram-sha-512` y da al `KafkaUser` correspondiente el mismo `authentication.type`; Strimzi genera las credenciales automáticamente en un Secret.

### Gestión declarativa de ACL

Como se muestra en el ejemplo de `KafkaUser` anterior, `authorization.type: simple` más una lista `acls` te permite gestionar ACLs como código mediante GitOps en lugar de ejecutar `kafka-acls.sh` contra los brokers manualmente. Incorporar un nuevo service a un topic es simplemente confirmar un nuevo recurso `KafkaUser`.

### Network policies

Los listeners de Strimzi admiten `networkPolicyPeers`, restringiendo qué pods pueden alcanzar un puerto de listener determinado (por ejemplo, 9092/9093/9094).

```yaml
listeners:
  - name: tls
    port: 9093
    type: internal
    tls: true
    networkPolicyPeers:
      - podSelector:
          matchLabels:
            app: order-service
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: kafka-clients
```

Strimzi convierte esto en una `NetworkPolicy` estándar de Kubernetes entre bastidores, por lo que solo los pods que coinciden con los selectors especificados pueden alcanzar el puerto del listener.

### Cifrado en reposo

El cifrado de volúmenes EBS **no** es algo que el EBS CSI driver aplique automáticamente: debes optar por él explícitamente mediante una de estas opciones:

- Habilitar la configuración **"EBS encryption by default"** a nivel de account/region, para que cada volumen creado posteriormente se cifre automáticamente.
- Configurar `encrypted: "true"` (y opcionalmente `kmsKeyId`) en el `StorageClass`.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/xxxxxxxx
```

Como los clusters de Kafka suelen transportar datos sensibles para compliance, trata un `StorageClass` cifrado explícitamente para los PVCs de brokers como el valor predeterminado, no como una consideración posterior.

## 5. Optimización de costos

### Dimensionamiento correcto de tipos de instancia

La mayoría de workloads de Kafka son mucho más sensibles a la **memoria — específicamente a la page cache del OS — que a la CPU**. Kafka está diseñado para servir la mayoría de las lecturas desde la page cache, por lo que, en el caso común donde los consumers leen datos recientes, la RAM restante después del heap del broker (normalmente 4–8GB es más que suficiente) determina directamente el throughput. Las instancias optimizadas para memoria (familia Graviton `r6g`/`r7g`, por ejemplo) suelen ofrecer mejor precio/rendimiento que las optimizadas para cómputo por este motivo.

### Tiered storage

Tiered storage, definido por KIP-405, descarga segmentos de log antiguos desde el disco local hacia almacenamiento remoto como S3, reduciendo cuánta capacidad EBS local necesita cada broker. Llegó como early access en Apache Kafka 3.6 y **pasó a estar listo para producción (GA) en Kafka 3.9**, pero no está habilitado por defecto: sigue siendo una función opt-in que debes activar explícitamente (`remote.log.storage.system.enable=true`). Antes de depender de ella con Strimzi, revisa las notas de soporte y madurez de tiered storage de esa versión de Strimzi, y valídala exhaustivamente primero en un cluster que no sea de producción.

### Ajuste de retención de logs

Configura `retention.ms`/`retention.bytes` por topic según los requisitos reales del negocio en lugar de dejar los valores predeterminados, ya que retener datos de más en EBS es un costo directo y continuo. Los topics que solo necesitan el último valor por clave (snapshots de estado, datos similares a cache) deben usar `cleanup.policy=compact` para que el almacenamiento no crezca sin límite.

```bash
# Example: tighten retention for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### Uso de Spot instances

Para entornos dev/staging o clusters de Strimzi de menor criticidad, ejecutar el pool de broker nodes en Spot instances puede reducir costos sustancialmente. Sin embargo, **el pool de KRaft controller nodes debe permanecer en On-Demand**. Perder una mayoría del controller quorum detiene la gestión de metadatos de todo el cluster, lo cual no es un riesgo que valga la pena asumir por ahorros de Spot. Distribuye el pool de broker nodes entre AZs/nodes con restricciones de distribución de topología de pods para que un evento de reclamación de Spot no elimine varias réplicas de la misma partition a la vez.

## 6. Checklist de puesta en marcha

Reuniendo los elementos clave de las Partes 1 a 8 de esta inmersión profunda en una única checklist previa a producción:

- [ ] **Arquitectura**: se ejecuta en modo KRaft, con pools de controller y broker nodes separados (Partes 1, 2)
- [ ] **Replicación**: los topics de producción usan `replication.factor=3` y `min.insync.replicas=2`, tolerando el fallo de un solo broker (Parte 1)
- [ ] **Diseño de particiones**: el número de partitions está dimensionado según el paralelismo máximo esperado de consumers, no dividido en exceso (Parte 8)
- [ ] **Fijación de versión de Strimzi**: las versiones de Operator y Kafka están fijadas explícitamente, no se dejan derivar con auto-upgrade (Parte 2)
- [ ] **Almacenamiento**: el `StorageClass` del broker usa gp3 (o io2) con cifrado (`encrypted: "true"`) (Partes 3, 8)
- [ ] **PodDisruptionBudget**: un PDB garantiza disponibilidad de quorum/mayoría durante rolling restarts y reemplazo de nodes (Parte 3)
- [ ] **Ensayo de rolling upgrade**: el procedimiento de rolling upgrade se ha ejercitado realmente en staging (Parte 3)
- [ ] **Compatibilidad de esquemas**: el modo de compatibilidad de schema registry (BACKWARD/FORWARD/FULL) se configura deliberadamente según las necesidades de cada topic (Parte 4)
- [ ] **DR/replicación**: la recuperación ante desastres basada en Kafka Connect/MirrorMaker2 o la replicación cross-region está documentada y se ha probado el failover (Parte 5)
- [ ] **Decisión MSK vs. self-managed**: la elección entre MSK gestionado y Strimzi self-managed está documentada con su justificación operativa y de costos (Parte 6)
- [ ] **Monitorización/alertas**: existen dashboards y reglas de alerta para métricas de brokers y consumer lag (Parte 7)
- [ ] **Autoscaling**: los workloads de consumers escalan según lag mediante KEDA o un mecanismo equivalente (Parte 7)
- [ ] **Revisión de configuración de producer/consumer**: `acks`, `enable.idempotence`, la estrategia de commit de offsets y la membresía estática de group se han revisado frente a las necesidades del workload (Parte 8)
- [ ] **Seguridad**: mTLS o SASL/SCRAM, ACLs basadas en `KafkaUser` y `NetworkPolicy` de listener están todas implementadas (Parte 8)
- [ ] **Revisión de costos**: los tipos de instancia, la política de retención y el uso de Spot se reevalúan periódicamente (Parte 8)
- [ ] **Pruebas de carga**: la escala de brokers y consumers se ha probado realmente con carga al throughput máximo esperado

Cumplir esta checklist es un umbral razonable para decir que el cluster está listo para ejecutarse en producción sobre EKS.

---

[Volver a la página principal](./)

## Quiz

Para comprobar lo que aprendiste en este capítulo, intenta el [quiz del topic](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md).
