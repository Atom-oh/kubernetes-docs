# Parte 8: Mejores prácticas

> **Versiones compatibles**: Apache Kafka 3.9, Strimzi 0.45+\
> **Última actualización**: July 9, 2026

En esta profundización cubrimos los fundamentos de Kafka, operaciones de Strimzi, schema registry, Kafka Connect/MirrorMaker, integración de MSK y monitoreo. Este documento final consolida las mejores prácticas de preparación para producción por categoría y reúne los elementos clave de las siete partes anteriores en una única lista de verificación para la puesta en marcha.

## 1. Diseño de particiones

### Dimensionamiento del número de particiones

Comience con el **máximo paralelismo esperado de consumidores** para un topic. Una única partición solo puede ser consumida por una instancia de consumidor dentro de un consumer group determinado a la vez, por lo que debe decidir hasta dónde espera escalar un consumer group y aprovisionar al menos esa cantidad de particiones. Si planea escalar a 20 instancias de consumidor en el pico, necesita al menos 20 particiones.

El exceso de particiones tiene costos reales y debe evitarse:

- **Más descriptores de archivos abiertos**: cada partición mantiene abiertos varios archivos de segmentos de log (`.log`, `.index`, `.timeindex`), por lo que el número de descriptores de archivos abiertos por broker crece linealmente con el número de particiones.
- **Mayor presión de memoria**: los buffers de lotes de productor/consumidor y los buffers por hilo de replicación en el broker escalan con el número de particiones.
- **Rebalances y failover más lentos**: la cantidad de trabajo de elección de líder que el controller debe realizar ante una falla de broker escala con el número de particiones, y los rebalances del consumer group también tardan más.

La regla general clásica de Confluent era un límite flexible de aproximadamente **4,000 particiones por broker y 200,000 por cluster** — orientación de la época en que el controller basado en ZooKeeper era el cuello de botella de metadatos. Los clusters basados en KRaft (quórum de controllers de Kafka 3.x+) manejan cantidades de particiones mucho mayores gracias a una ruta de metadatos de controller mucho más rápida, pero el principio sigue vigente: no cree particiones en exceso solo porque puede hacerlo, y valide el límite real para su carga de trabajo con pruebas de carga reales.

```bash
# Check total partition count and distribution per broker
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# Inspect partition/leader distribution for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### Elección de una clave de partición

Elija una clave con **alta cardinalidad y distribución uniforme** para evitar particiones calientes. El particionador predeterminado aplica hash murmur2 a la clave y toma su módulo con el número de particiones, por lo que una clave de baja cardinalidad (por ejemplo, `country` o `status` con solo unos pocos valores distintos) sobrecargará las pocas particiones que coincidan con sus valores de tráfico dominantes mientras las demás permanecen inactivas. Prefiera un campo con una cardinalidad suficientemente alta (por ejemplo, `user_id`), o aplique sal a una clave de baja cardinalidad (añada un sufijo aleatorio o derivado de una marca de tiempo) para forzar una distribución más uniforme.

### Manejo cuidadoso de los cambios en el número de particiones

Aumentar el número de particiones en un topic **con clave** rompe el mapeo de clave a partición. Debido a que `hash(key) % partition_count` cambia tan pronto como cambia `partition_count`, la misma clave puede llegar a una partición diferente después del cambio de la que tenía antes. Esto causa dos problemas concretos:

- **Orden roto**: Kafka solo garantiza el orden dentro de una partición, así que cuando los mensajes de la misma clave se dividen entre particiones, los consumidores ya no pueden depender del orden a nivel de clave.
- **Co-particionamiento roto**: los joins en Kafka Streams (y similares) requieren que los topics unidos compartan el mismo número de particiones y esquema de particionamiento. Cambiar las particiones en solo un lado de un join lo rompe.

Decida el número de particiones con margen durante la planificación de capacidad y, si un topic de producción ya depende del orden basado en claves o de joins, prefiera migrar a un topic nuevo en lugar de aumentar las particiones en el existente.

## 2. Ajuste del productor

| Configuración | Valor recomendado | Propósito |
|---------|--------------------|---------|
| `acks` | `all` (para topics críticos para la durabilidad) | Esperar la confirmación de todas las réplicas sincronizadas (ISR) para que una falla de broker no pierda datos |
| `min.insync.replicas` (configuración de topic/broker) | `2` (con replication.factor=3) | Junto con `acks=all`, requiere que la escritura llegue al menos a 2 réplicas antes de tener éxito — configúrelo en el topic (`kafka-configs.sh --entity-type topics`) o como valor predeterminado del broker, no como propiedad del cliente productor |
| `linger.ms` | `5`–`20` | Intercambiar una pequeña cantidad de latencia por lotes más grandes y mayor throughput |
| `batch.size` | `32768`–`65536` (32–64KB) | Aumentar los bytes máximos por lote para incrementar el throughput por solicitud |
| `enable.idempotence` | `true` | Evitar escrituras duplicadas causadas por reintentos del productor |
| `compression.type` | `lz4` o `zstd` | Reducir los costos de red y almacenamiento |

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

`enable.idempotence=true` ha sido **el valor predeterminado desde Kafka 3.0** a menos que sobrescriba explícitamente `acks` o `retries` de una forma incompatible con ello. Asigna al productor un ID de productor único y números de secuencia por partición para que el broker pueda deduplicar de forma transparente los reintentos causados por errores transitorios de red. Esto es distinto de la semántica completa exactly-once — la idempotencia solo elimina duplicados en el salto de productor a broker; la verdadera semántica exactly-once de extremo a extremo también requiere la API transaccional (`transactional.id`).

`lz4` ofrece un buen equilibrio entre sobrecarga de CPU y ratio de compresión para la mayoría de las cargas de trabajo. `zstd` comprime mejor — útil para payloads con mucho JSON/texto — a costa de un uso de CPU algo mayor. `gzip` comprime bien, pero su alto consumo de CPU hace que en general no se recomiende para productores de alto throughput.

## 3. Ajuste del consumidor

### Cómo evitar tormentas de rebalance

Si el procesamiento tarda más que `max.poll.interval.ms` (5 minutos de forma predeterminada), el consumidor es expulsado forzosamente de su grupo, lo que desencadena un rebalance. Cuando varios consumidores se ralentizan a la vez, esto puede encadenarse en una «tormenta de rebalance» de interrupciones repetidas del grupo.

```properties
# Tune poll-related settings around your actual per-batch processing time
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

Reducir `max.poll.records` disminuye cuántos registros regresan de una sola llamada a `poll()`, acortando la ventana de procesamiento entre polls. Aumentar `max.poll.interval.ms` da más margen al procesamiento lento antes de la expulsión. La solución más robusta es arquitectónica: mover el procesamiento pesado fuera del bucle de poll por completo y llevarlo a un pool de hilos de trabajo separado, usando poll solo para obtener y entregar trabajo.

### Commits manuales de offsets

Para pipelines donde el procesamiento at-least-once es importante (procesamiento de pedidos, pagos), el auto-commit (`enable.auto.commit=true`) puede confirmar un offset antes de que el registro correspondiente haya terminado realmente de procesarse — si el consumidor falla entre ambos, ese registro se pierde efectivamente desde la perspectiva del pipeline aunque se hubiera «confirmado».

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

### Membresía estática del grupo

Los Pods de consumidor en Kubernetes se reinician a menudo: despliegues graduales, reinicios OOMKilled, reemplazo de nodos. De forma predeterminada, que un consumidor salga y vuelva a unirse a un grupo desencadena un rebalance completo, de modo que los reinicios breves frecuentes provocan pausas de procesamiento repetidas e innecesarias en todo el grupo. Configurar `group.instance.id` habilita la membresía estática: si el consumidor se vuelve a conectar dentro de `session.timeout.ms`, reanuda su asignación de particiones anterior intacta, sin ningún rebalance.

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id` debe ser único por Pod — normalmente se obtiene de un nombre de Pod de StatefulSet o se inyecta mediante la downward API.

## 4. Seguridad

### mTLS (cifrado de transporte + autenticación mutua)

Strimzi aprovisiona y rota automáticamente su propia CA de cluster cuando se despliega un cluster Kafka. Establecer el tipo de un listener en `tls` cifra el tráfico entre cliente y broker, y asignar a un `KafkaUser` el tipo de autenticación `tls` hace que Strimzi emita un certificado de cliente firmado por esa CA de cluster.

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

Para entornos donde distribuir y rotar certificados de cliente no es práctico (aplicaciones heredadas, herramientas de terceros), SASL/SCRAM basado en nombre de usuario/contraseña (`scram-sha-512`) es una alternativa sólida. Establezca el tipo de autenticación del listener en `scram-sha-512` y asigne al `KafkaUser` correspondiente el mismo `authentication.type`; Strimzi genera automáticamente las credenciales en un Secret.

### Gestión declarativa de ACL

Como se muestra en el ejemplo de `KafkaUser` anterior, `authorization.type: simple` junto con una lista `acls` permite gestionar ACL como código mediante GitOps, en lugar de ejecutar manualmente `kafka-acls.sh` contra los brokers. Incorporar un servicio nuevo a un topic consiste simplemente en confirmar un recurso `KafkaUser` nuevo.

### Políticas de red

Los listeners de Strimzi admiten `networkPolicyPeers`, que restringe qué Pods pueden alcanzar un puerto de listener determinado (por ejemplo, 9092/9093/9094).

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

Strimzi transforma esto en una `NetworkPolicy` estándar de Kubernetes internamente, por lo que solo los Pods que coincidan con los selectores especificados podrán alcanzar el puerto de listener.

### Cifrado en reposo

El cifrado de volúmenes EBS **no** es algo que el controlador EBS CSI aplique automáticamente — debe habilitarlo explícitamente mediante una de estas opciones:

- Habilitar la configuración de nivel de cuenta/región **"EBS encryption by default"**, de modo que cada volumen creado posteriormente se cifre automáticamente.
- Configurar `encrypted: "true"` (y opcionalmente `kmsKeyId`) en la `StorageClass`.

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

Dado que los clusters Kafka suelen contener datos sensibles para cumplimiento, trate una `StorageClass` explícitamente cifrada para PVC de brokers como el valor predeterminado, no como una ocurrencia tardía.

## 5. Optimización de costos

### Dimensionamiento adecuado de tipos de instancia

La mayoría de las cargas de trabajo de Kafka son mucho más sensibles a la **memoria — específicamente, la caché de páginas del SO — que a la CPU**. Kafka está diseñado para atender la mayoría de las lecturas desde la caché de páginas, por lo que, en el caso habitual donde los consumidores leen datos recientes, la RAM que queda tras el heap del broker (normalmente 4–8GB son suficientes) determina directamente el throughput. Por esta razón, las instancias optimizadas para memoria (la familia Graviton `r6g`/`r7g`, por ejemplo) con frecuencia ofrecen una mejor relación precio/rendimiento que las optimizadas para cómputo.

### Almacenamiento por niveles

El almacenamiento por niveles, definido por KIP-405, descarga segmentos de log antiguos del disco local a almacenamiento remoto como S3, reduciendo la capacidad local de EBS que necesita cada broker. Se incorporó como acceso anticipado en Apache Kafka 3.6 y **pasó a estar listo para producción (GA) en Kafka 3.9**, pero no está habilitado de forma predeterminada — sigue siendo una característica opcional que debe activar explícitamente (`remote.log.storage.system.enable=true`). Antes de usarlo con Strimzi, consulte las notas de soporte y madurez de esa versión de Strimzi para el almacenamiento por niveles, y valídelo exhaustivamente primero en un cluster que no sea de producción.

### Ajuste de la retención de logs

Configure `retention.ms`/`retention.bytes` por topic según los requisitos reales del negocio en lugar de dejar los valores predeterminados, ya que retener datos en exceso en EBS es un costo directo y continuo. Los topics que solo necesitan el valor más reciente por clave (snapshots de estado, datos tipo caché) deben usar `cleanup.policy=compact` para que el almacenamiento no crezca sin límite.

```bash
# Example: tighten retention for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### Uso de instancias Spot

Para entornos de desarrollo/staging o clusters Strimzi de menor criticidad, ejecutar el pool de nodos de brokers en instancias Spot puede reducir los costos considerablemente. Sin embargo, **el pool de nodos de controllers KRaft debe permanecer en On-Demand**. Perder una mayoría del quórum de controllers detiene la gestión de metadatos de todo el cluster, un riesgo que no vale la pena asumir por los ahorros de Spot. Distribuya el pool de nodos de brokers entre AZ/nodos con restricciones de distribución de topología de Pods para que un evento de recuperación de Spot no elimine varias réplicas de la misma partición a la vez.

## 6. Lista de verificación para la puesta en marcha

Reuniendo los elementos clave de las partes 1 a 8 de esta profundización en una única lista de verificación previa a producción:

- [ ] **Arquitectura**: en ejecución en modo KRaft, con pools de nodos de controllers y brokers separados (Partes 1, 2)
- [ ] **Replicación**: los topics de producción usan `replication.factor=3` y `min.insync.replicas=2`, tolerando una sola falla de broker (Parte 1)
- [ ] **Diseño de particiones**: los números de particiones se dimensionan para el paralelismo máximo esperado de consumidores, sin dividir en exceso (Parte 8)
- [ ] **Fijación de versión de Strimzi**: las versiones de Operator y Kafka se fijan explícitamente, no se dejan variar mediante actualización automática (Parte 2)
- [ ] **Almacenamiento**: la `StorageClass` de broker usa gp3 (o io2) con cifrado (`encrypted: "true"`) (Partes 3, 8)
- [ ] **PodDisruptionBudget**: un PDB garantiza la disponibilidad de quórum/mayoría durante reinicios graduales y reemplazo de nodos (Parte 3)
- [ ] **Ensayo de actualización gradual**: el procedimiento de actualización gradual se ha ejercitado realmente en staging (Parte 3)
- [ ] **Compatibilidad de schemas**: el modo de compatibilidad de schema registry (BACKWARD/FORWARD/FULL) se establece deliberadamente según las necesidades de cada topic (Parte 4)
- [ ] **DR/replicación**: se documenta la recuperación ante desastres o replicación entre regiones basada en Kafka Connect/MirrorMaker2 y se ha probado el failover (Parte 5)
- [ ] **Decisión MSK frente a autogestionado**: la elección entre MSK gestionado y Strimzi autogestionado está documentada junto con su justificación operativa y de costos (Parte 6)
- [ ] **Monitoreo/alertas**: existen dashboards y reglas de alerta para métricas de brokers y consumer lag (Parte 7)
- [ ] **Autoscaling**: las cargas de trabajo de consumidores escalan según el lag mediante KEDA o un mecanismo equivalente (Parte 7)
- [ ] **Revisión de configuración de productor/consumidor**: `acks`, `enable.idempotence`, la estrategia de commit de offsets y la membresía estática del grupo se han revisado según las necesidades de la carga de trabajo (Parte 8)
- [ ] **Seguridad**: mTLS o SASL/SCRAM, ACL basadas en `KafkaUser` y `NetworkPolicy` de listener están implementados (Parte 8)
- [ ] **Revisión de costos**: los tipos de instancia, la política de retención y el uso de Spot se reevalúan periódicamente (Parte 8)
- [ ] **Pruebas de carga**: la escala de brokers y consumidores se ha probado realmente con carga al throughput pico esperado

Cumplir esta lista de verificación es un umbral razonable para afirmar que el cluster está listo para ejecutarse en producción en EKS.

---

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, pruebe el [Cuestionario de topics](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md).
