# Parte 3: Operaciones de Kafka

> **Versiones compatibles**: Strimzi 0.45+, Kafka 3.9\
> **Última actualización**: July 9, 2026

Una vez que un clúster de Kafka se implementa con Strimzi Operator, el trabajo operativo se centra en la planificación de capacidad de almacenamiento, el escalado de brokers, la reasignación de particiones y las actualizaciones sin tiempo de inactividad. Este documento cubre las tareas operativas principales que encontrará al ejecutar un clúster de Kafka administrado por Strimzi en EKS.

## Diseño de almacenamiento

### Elegir un tipo de volumen EBS: gp3 vs io2

Los segmentos de log de Kafka se escriben y leen principalmente de forma secuencial, pero el creciente consumer lag puede activar lecturas aleatorias de segmentos más antiguos. Elija el tipo de volumen EBS teniendo en cuenta ese patrón de acceso.

| Aspecto | gp3 | io2 |
|--------|-----|-----|
| **Facturación** | Basada en la capacidad; IOPS/throughput se aprovisionan por separado | Basada en IOPS (mayor costo por unidad) |
| **Throughput** | Línea base de 125MB/s, hasta 1,000MB/s con aprovisionamiento independiente | Escala con el tamaño del volumen y las IOPS |
| **IOPS máximas** | 16,000 | 256,000 |
| **Mejor opción** | La mayoría de las cargas de trabajo de Kafka — patrones limitados por throughput | Consumer lag con picos, cargas de trabajo sensibles a la latencia con intensa I/O aleatoria pequeña |
| **Durabilidad (tasa anual de fallos)** | 99.8–99.9% | 99.999% |

Para cargas de trabajo típicas de event streaming, comience con **gp3** y aprovisione throughput/IOPS de forma independiente según sea necesario — es la opción predeterminada más rentable. Cambie a **io2** solo cuando predomine la I/O aleatoria (muchos grupos de consumidores leyendo simultáneamente desde offsets dispersos) o cuando tenga un SLA de latencia p99 estricto.

### Almacenamiento de múltiples volúmenes con JBOD

Strimzi admite configuraciones JBOD (Just a Bunch Of Disks), en las que cada broker usa múltiples volúmenes independientes en lugar de un volumen grande. Dividir el almacenamiento de esta forma permite paralelizar el throughput entre volúmenes y agregar o reemplazar volúmenes individuales sin afectar el resto.

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

El `id` de cada entrada de `volumes` identifica un directorio de log dentro del broker, y las particiones se distribuyen entre los volúmenes de forma round-robin. `deleteClaim: false` protege los PVC de ser eliminados cuando un broker se reduce o se vuelve a crear.

> **Nota**: Con Strimzi, el Operator ejecuta automáticamente el equivalente de `kafka-storage.sh format` cuando se inicia un Pod de broker, por lo que no necesita ejecutar ese script usted mismo para formatear volúmenes.

### Guía para dimensionar el almacenamiento

Dimensione sus discos usando esta fórmula:

```
Required disk capacity = retention period × peak throughput (bytes/sec) × replication factor × (1 + headroom ratio)
```

Por ejemplo, con un throughput máximo de 50MB/s, un período de retención de 7 días (`604,800 seconds`), un factor de replicación de 3 y un margen del 30%:

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (cluster total)
```

Distribuido entre 3 brokers, equivale aproximadamente a 39TB por broker. El margen es importante porque los brokers de Kafka se degradan considerablemente una vez que la utilización del disco supera una marca de agua alta (afecta el comportamiento del log cleaner y la rotación de segmentos), y si la eliminación impulsada por `log.retention.bytes`/`log.retention.hours` se retrasa, un disco lleno puede dejar un broker completamente fuera de línea. Mantenga al menos un 20–30% de espacio libre en todo momento.

## Escalado de brokers y controllers

### Escalar horizontalmente los brokers

Aumentar `replicas` en un `KafkaNodePool` indica a Strimzi que cree nuevos Pods de broker y los una al clúster automáticamente.

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# Confirm the new brokers joined the cluster
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

Los nuevos brokers no se eligen automáticamente como leaders o followers para las particiones existentes. Para distribuir realmente las particiones de topics existentes en los nuevos brokers, necesita un paso independiente de reasignación de particiones.

### Reasignación de particiones (`kafka-reassign-partitions.sh`)

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

### Por qué reducir horizontalmente es peligroso

**Strimzi no drena automáticamente las particiones de un broker cuando reduce horizontalmente.** Antes de reducir `replicas` en un `KafkaNodePool`, primero debe reasignar todas las particiones (tanto réplicas leader como follower) que residen en el broker que se eliminará a los brokers restantes. Omita este paso y las réplicas que solo existían en ese broker simplemente desaparecen — lo que, en el mejor de los casos, deja particiones con replicación insuficiente y, en el peor, provoca pérdida de datos.

La secuencia segura para reducir horizontalmente es:

1. Ejecute `kafka-reassign-partitions.sh --generate` sobre una lista de brokers que excluya los brokers que va a eliminar.
2. Aplique el plan con `--execute` y confirme su finalización con `--verify` (compruebe que las particiones con replicación insuficiente sean cero).
3. Solo después de que la reasignación esté completamente terminada, reduzca `KafkaNodePool.spec.replicas` para eliminar los Pods de broker.

## Rebalanceo automatizado con Cruise Control

Cruise Control recopila continuamente métricas de carga a nivel de broker — uso de disco, CPU, throughput de red — y las utiliza para generar y ejecutar automáticamente planes de reasignación de particiones. En lugar de ejecutar `kafka-reassign-partitions.sh` manualmente cada vez que agrega o elimina un broker, puede delegar el rebalanceo a la automatización basada en objetivos.

### Habilitar Cruise Control

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

### Activar un rebalanceo con `KafkaRebalance`

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

### Modos de rebalanceo

| Modo | Caso de uso |
|------|----------|
| `full` (predeterminado) | Genera un plan de rebalanceo completo en todos los brokers del clúster, según los objetivos configurados |
| `add-brokers` | Se centra en mover particiones a brokers recién agregados para completar su carga — más rápido y de alcance más limitado que un rebalanceo completo |
| `remove-brokers` | Se centra en mover particiones fuera de los brokers que está a punto de eliminar — úselo como paso de drenaje seguro antes de reducir horizontalmente |

Inmediatamente después de un escalado horizontal hacia afuera o hacia adentro, limitar el rebalanceo a `add-brokers` o `remove-brokers` evita la sobrecarga de red y el costo de tiempo del modo `full`, que mueve particiones no relacionadas que no necesitan moverse.

## Actualizaciones progresivas

### Reinicios progresivos automáticos ante cambios en la especificación

Cuando cambia la especificación de un CR de `Kafka` o `KafkaNodePool` — solicitudes/límites de recursos, valores de configuración, volúmenes, etc. — Strimzi Operator detecta el cambio y reinicia los Pods de broker **uno a la vez**. El Operator coordina cada reinicio para que solo continúe mientras cada partición siga cumpliendo su `min.insync.replicas`, lo que garantiza que un reinicio nunca reduzca el recuento de réplicas disponibles de una partición por debajo del umbral requerido.

### Actualizaciones de versión de Kafka — El patrón de dos fases

En el modo KRaft no existen `inter.broker.protocol.version`/`log.message.format.version` (son configuraciones de la era ZooKeeper). En su lugar, `spec.kafka.version` del CR de `Kafka` (la versión de software) y `spec.kafka.metadataVersion` (la versión de formato del log de metadatos KRaft) **no** deben incrementarse juntas — esto sigue requiriendo **dos fases separadas**. `metadataVersion` controla el formato que usa el quorum de controllers para persistir metadatos, por lo que debe mantenerse en el formato anterior mientras se mezclan nodos antiguos y nuevos durante la implementación progresiva.

**Fase 1 — Actualice solo la versión de software**

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

Aplicar esto activa un reemplazo progresivo de los binarios de broker/controller a 3.9.0, mientras el formato de metadatos permanece en 3.8-IV0. Esto mantiene los nodos antiguos y nuevos compatibles entre sí en el quorum de controllers durante la ventana en que ambos están en ejecución.

**Fase 2 — Incremente metadataVersion después de reemplazar todos los nodos**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

Incremente `metadataVersion` solo después de confirmar que cada broker/controller ejecuta 3.9.0. Este cambio activa otra reconciliación para adoptar el nuevo formato de metadatos. Si invierte el orden — incrementando la versión de software y `metadataVersion` al mismo tiempo — los nodos que aún ejecutan el binario anterior no entenderán el nuevo formato de metadatos y obtendrá errores de comunicación del quorum de controllers.

### Actualizaciones de la versión de Strimzi Operator

**Actualice Strimzi Operator antes de incrementar la versión de Kafka.** Cada versión de Strimzi admite un rango específico de versiones de Kafka, y cambiar el CR a una versión de Kafka que el Operator en ejecución no reconoce fallará la validación. El orden habitual es: actualizar el Operator → darle tiempo para completar la reconciliación → actualizar la versión de software de Kafka (Fase 1) → actualizar `metadataVersion` (Fase 2).

## Conceptos básicos de manejo de fallos

### PodDisruptionBudget y la expulsión de Pods de broker

Strimzi crea automáticamente un `PodDisruptionBudget` (PDB) para cada `KafkaNodePool`. De forma predeterminada, permite que solo un Pod de broker a la vez se someta a expulsión voluntaria — drenajes de nodos, reemplazo de nodos por Cluster Autoscaler y casos similares — lo que evita que varios brokers se apaguen simultáneamente y rompan el quorum o la disponibilidad.

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### Producers con `acks=all` durante reinicios progresivos

Con `acks=all`, los producers están protegidos contra la pérdida de datos incluso durante un reinicio progresivo de broker. Si el broker que se reinicia era el leader de una partición, el controller elige un nuevo leader del conjunto de réplicas sincronizadas (ISR) justo antes de que proceda el reinicio. Los producers detectan el cambio de leader, actualizan sus metadatos y reintentan con el nuevo leader — puede haber un breve pico de latencia, pero mientras se cumpla `min.insync.replicas`, no se pierden datos confirmados. Los producers que usan `acks=1` o un valor inferior corren el riesgo de perder mensajes que aún no se habían replicado a un follower en el momento del reinicio.

Desde el lado del consumidor, un reinicio progresivo puede activar un rebalanceo del grupo de consumidores y una caída temporal del throughput, pero mientras los offsets se hayan confirmado normalmente, los consumidores continúan exactamente donde lo dejaron una vez que se completa el reinicio.

---

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, pruebe el [Cuestionario de topics](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md).

A continuación: la Parte 4 cubre Schema Registry — la administración de esquemas de mensajes y la estrategia de compatibilidad para los topics de Kafka.
