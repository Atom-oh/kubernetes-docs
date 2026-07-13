# Cuestionario de operaciones de Kafka

Este cuestionario evalúa tu comprensión del diseño de almacenamiento, el escalado de brokers, el rebalanceo con Cruise Control, las actualizaciones continuas y el manejo de fallos para un clúster Kafka gestionado por Strimzi en EKS.

## Preguntas de opción múltiple

1. ¿Qué tipo de volumen EBS es más adecuado para una carga de trabajo con I/O aleatorio intenso de muchos grupos de consumidores que leen en offsets dispersos y un SLA estricto de latencia p99?
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) io2**

**Explicación:**
io2 se factura por IOPS y ofrece hasta 256,000 IOPS con 99.999% de durabilidad, lo que lo hace muy adecuado para cargas de trabajo sensibles a la latencia dominadas por I/O aleatorio pequeño. La mayoría de las cargas de trabajo de streaming de eventos están limitadas por throughput, por lo que gp3 es el punto de partida más rentable; io2 solo vale la pena cuando el I/O aleatorio se convierte en el cuello de botella, como con lag de consumidores con picos o un SLA estricto de p99.
</details>

2. ¿Qué tipo de almacenamiento en un `KafkaNodePool` configura un broker para usar varios volúmenes independientes?
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `type: jbod`**

**Explicación:**
`storage.type: jbod` (Just a Bunch Of Disks) te permite definir varios volúmenes independientes por broker en una lista `volumes`. Cada volumen se identifica mediante un `id`, y las particiones se distribuyen round-robin entre ellos. `persistent-claim` es el tipo usado para cada entrada de volumen individual dentro de una configuración JBOD.
</details>

3. Con un período de retención de 7 días, throughput máximo de 100MB/s, un factor de replicación de 3 y 30% de margen, ¿qué fórmula da la capacidad de disco requerida para todo el clúster?
   - A) 100MB/s × 7 días (segundos) × 3
   - B) 100MB/s × 7 días (segundos) × 3 × 1.3
   - C) 100MB/s × 7 días (segundos) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) 100MB/s × 7 días (segundos) × 3 × 1.3**

**Explicación:**
La fórmula de dimensionamiento es `retention period × peak throughput × replication factor × (1 + headroom ratio)`. Convierte la retención a segundos y multiplícala por el throughput máximo para obtener el volumen de datos sin procesar, multiplícala por el factor de replicación para tener en cuenta las réplicas y, por último, multiplícala por el factor de margen (30% de margen = 1.3x) para dejar un margen de seguridad.
</details>

4. ¿Qué script debe ejecutar manualmente un operador para formatear volúmenes de almacenamiento en un clúster Kafka gestionado por Strimzi?
   - A) `kafka-storage.sh format` debe ejecutarse manualmente en cada broker
   - B) `kafka-configs.sh` debe usarse para aplicar la configuración de formato
   - C) Ninguno — el Strimzi Operator se encarga de esto automáticamente cuando inicia un pod de broker
   - D) Debe usarse `kafka-reassign-partitions.sh --format`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Ninguno — el Strimzi Operator se encarga de esto automáticamente cuando inicia un pod de broker**

**Explicación:**
Con Strimzi, el Operator se encarga automáticamente del formateo de volúmenes cuando inicia un pod de broker. Esto es una comodidad en comparación con ejecutar Kafka open-source básico manualmente, donde tendrías que ejecutar `kafka-storage.sh format` por tu cuenta.
</details>

5. Cuando escalas horizontalmente los brokers aumentando `replicas` en un `KafkaNodePool`, ¿qué ocurre automáticamente con los nuevos brokers?
   - A) Las particiones existentes se redistribuyen inmediatamente hacia los nuevos brokers
   - B) Los nuevos brokers se unen al clúster, pero las particiones de topics existentes no se reasignan automáticamente
   - C) Los nuevos brokers se convierten automáticamente en líderes de todas las particiones
   - D) Los nuevos brokers solo sirven como controllers

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los nuevos brokers se unen al clúster, pero las particiones de topics existentes no se reasignan automáticamente**

**Explicación:**
Aumentar `replicas` hace que Strimzi cree nuevos pods de broker y los una al clúster, pero mover hacia ellos las particiones de topics existentes no es automático. Para utilizar realmente la capacidad de los nuevos brokers, necesitas una reasignación manual mediante `kafka-reassign-partitions.sh` o un rebalanceo de Cruise Control en modo `add-brokers`.
</details>

6. ¿Qué debe hacerse antes de reducir la escala de un broker?
   - A) Nada — Strimzi lo drena automáticamente
   - B) Las particiones en el broker que se eliminará primero deben reasignarse a los brokers restantes
   - C) El clúster debe reiniciarse
   - D) Deben eliminarse todos los topics

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Las particiones en el broker que se eliminará primero deben reasignarse a los brokers restantes**

**Explicación:**
Strimzi no drena automáticamente las particiones al reducir la escala de un broker. Antes de reducir `replicas`, todas las réplicas en el broker que se eliminará deben reasignarse a los brokers restantes; de lo contrario, corres el riesgo de tener particiones subreplicadas o incluso pérdida de datos directa.
</details>

7. ¿Cuál es el rol principal de Cruise Control?
   - A) Automatiza la creación y eliminación de topics
   - B) Recopila métricas de carga de brokers y genera/ejecuta automáticamente planes de reasignación de particiones basados en objetivos
   - C) Gestiona los commits de offsets de grupos de consumidores
   - D) Renueva automáticamente certificados TLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Recopila métricas de carga de brokers y genera/ejecuta automáticamente planes de reasignación de particiones basados en objetivos**

**Explicación:**
Cruise Control recopila continuamente métricas de carga por broker — uso de disco, CPU, throughput de red — y usa objetivos configurados para generar y ejecutar automáticamente planes de reasignación de particiones. Esto elimina la necesidad de ejecutar manualmente `kafka-reassign-partitions.sh` para rebalanceos rutinarios.
</details>

8. En el campo `mode` de un recurso `KafkaRebalance`, ¿qué modo se enfoca en mover particiones hacia brokers recién agregados para llenar su carga?
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `add-brokers`**

**Explicación:**
El modo `add-brokers` se enfoca en mover particiones hacia brokers recién agregados, por lo que es más rápido y tiene un alcance más limitado que el modo `full`, que reasigna entre todos los brokers, incluidos los no relacionados. El modo `remove-brokers`, por el contrario, se enfoca en mover particiones fuera de brokers que están por eliminarse: un paso de drenaje útil antes de reducir la escala.
</details>

9. ¿Cuál es el procedimiento correcto para actualizar la versión de Kafka de un clúster en modo KRaft de 3.8 a 3.9?
   - A) Cambiar `version` y `metadataVersion` a 3.9 todo de una vez
   - B) Primero cambiar solo `version` a 3.9 para desplegar el nuevo software de broker/controller, y solo después de que cada nodo haya sido reemplazado, aumentar `metadataVersion` a 3.9-IV0
   - C) Primero aumentar `metadataVersion`, luego cambiar `version`
   - D) Detener todo el clúster y cambiar todos los valores de una vez

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Primero cambiar solo `version` a 3.9 para desplegar el nuevo software de broker/controller, y solo después de que cada nodo haya sido reemplazado, aumentar `metadataVersion` a 3.9-IV0**

**Explicación:**
En modo KRaft no existe `inter.broker.protocol.version`/`log.message.format.version` (esas son configuraciones de la era ZooKeeper). En su lugar, `spec.kafka.version` (la versión del software) y `spec.kafka.metadataVersion` (el formato que el quorum de controllers usa para persistir metadatos) deben aumentarse en dos fases. La fase 1 aumenta solo la versión del software mientras mantiene `metadataVersion` fijado al formato anterior, de modo que los nodos antiguos y nuevos sigan siendo compatibles entre sí en el quorum de controllers mientras ambos se ejecutan durante el rollout. La fase 2 aumenta `metadataVersion` solo después de confirmar que todos los nodos han sido reemplazados. Invertir este orden significa que los nodos que aún tienen el binario anterior no entenderán el nuevo formato de metadatos, lo que causará errores de comunicación del quorum de controllers.
</details>

10. ¿Qué recurso de Kubernetes crea Strimzi automáticamente por cada `KafkaNodePool` para limitar las expulsiones voluntarias?
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) PodDisruptionBudget**

**Explicación:**
Strimzi crea automáticamente un `PodDisruptionBudget` (PDB) para cada `KafkaNodePool`. De forma predeterminada, permite que solo un pod de broker a la vez sufra una expulsión voluntaria (drenajes de nodos, reemplazo de nodos por autoscaler, etc.), lo que evita que varios brokers caigan simultáneamente y rompan la disponibilidad.
</details>

## Preguntas de respuesta corta

11. ¿Qué valor de configuración de Kafka respeta Strimzi durante un reinicio continuo para garantizar que el recuento de réplicas disponibles de una partición nunca caiga por debajo del mínimo requerido?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `min.insync.replicas`**

**Explicación:**
Durante los reinicios continuos desencadenados por cambios en la especificación del CR, el Strimzi Operator reinicia los brokers de uno en uno mientras garantiza que el requisito `min.insync.replicas` de cada partición siga satisfecho. Esto evita que un reinicio reduzca el recuento de réplicas in-sync disponibles de una partición por debajo del umbral requerido, lo que de otro modo causaría fallos de escritura o pérdida de disponibilidad.
</details>

12. ¿Qué componente debe actualizarse antes de actualizar la versión del propio clúster Kafka?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: El Strimzi Operator**

**Explicación:**
Cada versión de Strimzi admite un rango específico de versiones de Kafka, y cambiar el CR a una versión de Kafka que el Operator en ejecución no reconoce fallará en la validación. Por lo tanto, el propio Strimzi Operator debe actualizarse a la versión más reciente antes de aumentar la versión del software Kafka.
</details>

13. Antes de ejecutar realmente un plan de reasignación de particiones, ¿qué opción de `kafka-reassign-partitions.sh` se usa para generar un plan contra una lista de brokers especificada?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `--generate`**

**Explicación:**
La opción `--generate` produce un plan de reasignación (JSON) basado en `--topics-to-move-json-file` y `--broker-list`, sin ejecutarlo realmente. Después de revisar el plan, lo aplicas con `--execute` y verificas el progreso y la finalización con `--verify`.
</details>

14. En una oración, explica por qué un producer configurado con `acks=all` puede sobrevivir a un reinicio continuo de brokers sin perder datos.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Si el broker que se reinicia era líder de una partición, el controller elige un nuevo líder del conjunto de réplicas in-sync (ISR) antes de que el reinicio continúe, y mientras `min.insync.replicas` esté satisfecho, los datos confirmados se preservan.**

**Explicación:**
Un producer con `acks=all` espera a que su mensaje sea escrito por suficientes réplicas para satisfacer `min.insync.replicas` antes de tratarlo como confirmado. Si el líder cambia antes del reinicio de un broker, el producer detecta el cambio, actualiza sus metadatos y reintenta contra el nuevo líder; puede haber un breve pico de latencia, pero los datos ya confirmados no se pierden. Los producers que usan `acks=1` o menor no tienen tal garantía y corren el riesgo de perder mensajes en tránsito.
</details>

## Preguntas prácticas

15. Escribe un YAML de `KafkaNodePool` llamado `broker` usando almacenamiento JBOD con 3 volúmenes, cada uno de 300Gi en gp3.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
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
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 2
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
```

**Explicación:**
Configurar `storage.type: jbod` y definir tres volúmenes `persistent-claim` en la lista `volumes`, cada uno con un `id` único (0, 1, 2), le da al broker tres volúmenes independientes. `deleteClaim: false` protege los PVCs contra eliminación cuando el broker se recrea o se reduce la escala, salvaguardando los datos que contienen.
</details>

16. Crea un recurso `KafkaRebalance` en modo `full` para un clúster llamado `my-cluster`, y escribe el comando para aprobar la propuesta de rebalanceo generada.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
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
# Check proposal generation status (PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# Approve the proposal to execute it
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# Watch progress
kubectl get kafkarebalance my-rebalance -n kafka -w
```

**Explicación:**
Crear el CR `KafkaRebalance` hace que Cruise Control genere automáticamente una propuesta de rebalanceo y espere en estado `ProposalReady`. La anotación `strimzi.io/rebalance=approve` es necesaria para ejecutar realmente los movimientos de particiones. `mode: full` genera un plan basado en objetivos que cubre todos los brokers del clúster.
</details>

17. Después de escalar los brokers de 3 (IDs 0,1,2) a 6 (IDs 0-5), escribe los comandos de tres pasos (generar → ejecutar → verificar) para reasignar las particiones del topic `orders` en toda la lista de brokers, incluidos los nuevos brokers.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# 1) Define the topic to move
cat <<EOF > topics-to-move.json
{
  "topics": [{"topic": "orders"}],
  "version": 1
}
EOF

# 2) Generate the plan
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "0,1,2,3,4,5" \
  --generate

# 3) Execute the plan (using the generated reassignment.json)
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# 4) Verify completion
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

**Explicación:**
`--generate` produce un plan de movimiento de particiones dirigido a la `--broker-list` dada (aquí, 0-5, incluidos los nuevos brokers). `--execute` inicia la reasignación real, y `--verify` confirma que la reasignación se completó sin particiones subreplicadas restantes. Solo después de este proceso los brokers recién agregados realmente tienen roles de líder/follower de particiones.
</details>

---

[Volver a los materiales de aprendizaje](../../../data-on-eks/kafka/03-kafka-operations.md) | [Siguiente cuestionario: Schema Registry](./04-schema-registry-quiz.md)
