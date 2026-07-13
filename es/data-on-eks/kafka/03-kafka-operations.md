# Part 3: Kafka Operations

> **Supported Versions**: Strimzi 0.45+, Kafka 3.9\
> **Última actualización**: July 9, 2026

Una vez desplegado un cluster de Kafka con el Strimzi Operator, el trabajo operativo pasa a la planificación de capacidad de almacenamiento, el escalado de brokers, la reasignación de particiones y las actualizaciones sin tiempo de inactividad. Este documento cubre las tareas operativas principales que encontrarás al ejecutar un cluster de Kafka gestionado por Strimzi en EKS.

## Storage Design

### Choosing an EBS Volume Type: gp3 vs io2

Los segmentos de log de Kafka se escriben y leen principalmente de forma secuencial, pero el aumento del retraso de los consumers puede provocar lecturas aleatorias contra segmentos más antiguos. Elige tu tipo de volumen de EBS teniendo en cuenta ese patrón de acceso.

| Aspect | gp3 | io2 |
|--------|-----|-----|
| **Billing** | Capacity-based; IOPS/throughput provisioned separately | IOPS-based (higher per-unit cost) |
| **Throughput** | 125MB/s baseline, up to 1,000MB/s with independent provisioning | Scales with volume size and IOPS |
| **Max IOPS** | 16,000 | 256,000 |
| **Best fit** | Most Kafka workloads — throughput-bound patterns | Spiky consumer lag, latency-sensitive workloads with heavy small random I/O |
| **Durability (annual failure rate)** | 99.8–99.9% | 99.999% |

Para workloads típicos de streaming de eventos, empieza con **gp3** y aprovisiona throughput/IOPS de forma independiente según sea necesario: es la opción predeterminada más rentable. Cambia a **io2** solo cuando domine la E/S aleatoria (muchos consumer groups leyendo desde offsets dispersos simultáneamente) o cuando tengas un SLA estricto de latencia p99.

### Multi-Volume Storage with JBOD

Strimzi admite configuraciones JBOD (Just a Bunch Of Disks), donde cada broker usa múltiples volúmenes independientes en lugar de un único volumen grande. Dividir el almacenamiento de esta manera te permite paralelizar el throughput entre volúmenes y añadir o reemplazar volúmenes individuales sin tocar el resto.

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: broker
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
  resources:
    requests:
      memory: 8Gi
      cpu: "2"
    limits:
      memory: 8Gi
      cpu: "4"
```

El `id` de cada entrada de `volumes` identifica un directorio de logs dentro del broker, y las particiones se distribuyen entre los volúmenes en modo round-robin. `deleteClaim: false` protege los PVC de ser eliminados cuando un broker se escala hacia abajo o se recrea.

> **Note**: Con Strimzi, el Operator ejecuta automáticamente el equivalente de `kafka-storage.sh format` cuando se inicia un broker pod, por lo que no necesitas ejecutar ese script tú mismo para formatear los volúmenes.

### Storage Sizing Guidance

Dimensiona tus discos usando esta fórmula:

```
Required disk capacity = retention period × peak throughput (bytes/sec) × replication factor × (1 + headroom ratio)
```

Por ejemplo, con un throughput máximo de 50MB/s, un período de retención de 7 días (`604,800 seconds`), un factor de replicación de 3 y un margen libre del 30%:

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (cluster total)
```

Distribuido entre 3 brokers, eso equivale aproximadamente a 39TB por broker. El margen libre importa porque los brokers de Kafka se degradan con rapidez cuando la utilización del disco supera una marca alta (afecta al comportamiento del log cleaner y del segment rolling), y si la eliminación impulsada por `log.retention.bytes`/`log.retention.hours` se retrasa, un disco lleno puede dejar a un broker completamente fuera de línea. Mantén al menos un 20–30% de espacio libre en todo momento.

## Broker and Controller Scaling

### Scaling Out Brokers

Aumentar `replicas` en un `KafkaNodePool` le indica a Strimzi que cree nuevos broker pods y los una automáticamente al cluster.

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# Confirm the new brokers joined the cluster
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

Los brokers nuevos no se eligen automáticamente como leaders o followers para las particiones existentes. Para distribuir realmente las particiones de topics existentes en los nuevos brokers, necesitas un paso separado de reasignación de particiones.

### Partition Reassignment (`kafka-reassign-partitions.sh`)

```bash
# 1) Write the topics-to-move JSON file inside the broker pod
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c 'cat <<EOF > /tmp/topics-to-move.json
{
  "topics": [{"topic": "orders"}, {"topic": "payments"}],
  "version": 1
}
EOF'

# 2) Generate a reassignment plan across the full broker list, saved to a file inside the pod
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c '
  bin/kafka-reassign-partitions.sh \
    --bootstrap-server localhost:9092 \
    --topics-to-move-json-file /tmp/topics-to-move.json \
    --broker-list "0,1,2,3,4,5" \
    --generate > /tmp/generate-output.txt
  # The --generate output contains both the Current and Proposed assignment JSON,
  # so extract just the JSON under "Proposed partition reassignment configuration"
  awk "/^Proposed partition reassignment configuration/{flag=1; next} flag" /tmp/generate-output.txt > /tmp/reassignment.json
'

# 3) Apply the generated plan (reassignment.json)
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --execute

# 4) Check progress
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --verify
```

### Why Scaling Down Is Dangerous

**Strimzi no drena automáticamente las particiones de un broker cuando escalas hacia abajo.** Antes de reducir `replicas` en un `KafkaNodePool`, primero debes reasignar todas las particiones (tanto leader como follower replicas) que residen en el broker que se va a eliminar hacia los brokers restantes. Si omites este paso, las replicas que solo existían en ese broker simplemente desaparecen, dejándote con particiones subreplicadas en el mejor de los casos y pérdida de datos en el peor.

La secuencia segura para escalar hacia abajo es:

1. Ejecuta `kafka-reassign-partitions.sh --generate` contra una lista de brokers que excluya los brokers que estás eliminando.
2. Aplica el plan con `--execute` y confirma que se completó con `--verify` (verifica que las particiones subreplicadas sean cero).
3. Solo después de que la reasignación esté completamente terminada, reduce `KafkaNodePool.spec.replicas` para eliminar los broker pods.

## Automated Rebalancing with Cruise Control

Cruise Control recopila continuamente métricas de carga a nivel de broker — uso de disco, CPU, throughput de red — y las usa para generar y ejecutar automáticamente planes de reasignación de particiones. En lugar de ejecutar `kafka-reassign-partitions.sh` manualmente cada vez que añades o eliminas un broker, puedes delegar el rebalanceo a una automatización basada en objetivos.

### Enabling Cruise Control

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # ... existing kafka config ...
  cruiseControl:
    config:
      # Goals: keep disk/CPU/network usage even across brokers
      goals: >-
        com.linkedin.kafka.cruisecontrol.analyzer.goals.RackAwareGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.DiskCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.CpuCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkInboundCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkOutboundCapacityGoal
```

### Triggering a Rebalance with `KafkaRebalance`

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaRebalance
metadata:
  name: my-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  mode: full
```

```bash
# Generate a rebalance proposal (not executed yet: PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# Approve the proposal to actually execute the rebalance
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# Watch progress
kubectl get kafkarebalance my-rebalance -n kafka -w
```

### Rebalance Modes

| Mode | Use case |
|------|----------|
| `full` (default) | Generates a full rebalance plan across every broker in the cluster, based on the configured goals |
| `add-brokers` | Focuses on moving partitions onto newly added brokers to fill their load — faster and narrower in scope than a full rebalance |
| `remove-brokers` | Focuses on moving partitions off brokers you're about to remove — use this as the safe drain step before scaling down |

Justo después de escalar hacia afuera o hacia adentro, limitar el alcance del rebalanceo a `add-brokers` o `remove-brokers` evita la sobrecarga de red y el costo de tiempo del modo `full`, que movería particiones no relacionadas que no necesitan moverse.

## Rolling Upgrades

### Automatic Rolling Restarts on Spec Changes

Cuando cambias la especificación de un CR `Kafka` o `KafkaNodePool` — requests/limits de recursos, valores de configuración, volúmenes, etc. — el Strimzi Operator detecta el cambio y reinicia los broker pods **uno a la vez**. El Operator coordina cada reinicio para que solo continúe mientras cada partición todavía satisfaga su `min.insync.replicas`, asegurando que un reinicio nunca reduzca el número de replicas disponibles de una partición por debajo del umbral requerido.

### Kafka Version Upgrades — The Two-Phase Pattern

En modo KRaft no existe `inter.broker.protocol.version`/`log.message.format.version` (son configuraciones de la era de ZooKeeper). En su lugar, `spec.kafka.version` (la versión del software) y `spec.kafka.metadataVersion` (la versión del formato del log de metadatos de KRaft) del CR `Kafka` **no** deben incrementarse juntos; esto sigue requiriendo **dos fases separadas**. `metadataVersion` controla el formato que usa el controller quorum para persistir metadatos, por lo que debe mantenerse en el formato anterior mientras se mezclan nodos antiguos y nuevos a mitad del rollout.

**Phase 1 — Upgrade the software version only**

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # Keep metadataVersion pinned to the old format
    metadataVersion: 3.8-IV0
```

Aplicar esto desencadena un reemplazo rolling de los binarios de broker/controller a 3.9.0, mientras el formato de metadatos permanece en 3.8-IV0. Esto mantiene compatibles entre sí a los nodos antiguos y nuevos en el controller quorum durante la ventana en la que ambos están en ejecución.

**Phase 2 — Bump metadataVersion after every node is replaced**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

Incrementa `metadataVersion` solo después de confirmar que cada broker/controller está ejecutando 3.9.0. Este cambio desencadena otra reconciliación para adoptar el nuevo formato de metadatos. Si inviertes el orden — incrementando la versión del software y `metadataVersion` al mismo tiempo — los nodos que aún ejecutan el binario antiguo no entenderán el nuevo formato de metadatos, y obtendrás errores de comunicación del controller quorum.

### Strimzi Operator Version Upgrades

**Actualiza primero el Strimzi Operator antes de incrementar la versión de Kafka.** Cada versión de Strimzi admite un rango específico de versiones de Kafka, y cambiar el CR a una versión de Kafka que el Operator en ejecución no reconoce fallará en la validación. El orden típico es: actualizar el Operator → darle tiempo para completar la reconciliación → actualizar la versión del software de Kafka (Phase 1) → actualizar `metadataVersion` (Phase 2).

## Failure Handling Basics

### PodDisruptionBudget and Broker Pod Eviction

Strimzi crea automáticamente un `PodDisruptionBudget` (PDB) para cada `KafkaNodePool`. Por defecto, permite que solo un broker pod a la vez pase por una eviction voluntaria — drenajes de nodes, reemplazo de nodes por Cluster Autoscaler y similares — lo que evita que múltiples brokers se caigan simultáneamente y rompan el quorum o la disponibilidad.

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### `acks=all` Producers During Rolling Restarts

Con `acks=all`, los producers están protegidos contra la pérdida de datos incluso durante un rolling restart de brokers. Si el broker que se está reiniciando era el leader de una partición, el controller elige un nuevo leader del conjunto de in-sync replicas (ISR) justo antes de que continúe el reinicio. Los producers detectan el cambio de leader, actualizan sus metadatos y reintentan contra el nuevo leader; puede haber un breve pico de latencia, pero mientras `min.insync.replicas` se satisfaga, no se pierden datos confirmados. Los producers que usan `acks=1` o inferior corren el riesgo de perder mensajes que aún no se habían replicado a un follower en el momento del reinicio.

Desde el lado del consumer, un rolling restart puede desencadenar un rebalanceo del consumer group y una caída temporal del throughput, pero mientras los offsets se hayan confirmado normalmente, los consumers continúan justo donde lo dejaron una vez que se completa el reinicio.

---

[Volver a la página principal](./)

## Quiz

Para probar lo que has aprendido en este capítulo, intenta el [cuestionario del tema](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md).

A continuación: Part 4 cubre Schema Registry: gestionar esquemas de mensajes y la estrategia de compatibilidad para Kafka topics.
