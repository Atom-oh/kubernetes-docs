# Strimzi Operator Quiz

Este cuestionario evalúa tu comprensión de los fundamentos de Strimzi Operator, los métodos de instalación, los CRDs principales, los roles de nodos KRaft y las consideraciones de despliegue en EKS.

## Multiple Choice Questions

1. ¿Qué tipo de proyecto de CNCF es Strimzi?
   - A) Un service mesh
   - B) Un Operator para ejecutar Apache Kafka en Kubernetes
   - C) Un container runtime
   - D) Una herramienta de pipeline de CI/CD

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un Operator para ejecutar Apache Kafka en Kubernetes**

**Explicación:**
Strimzi es un proyecto CNCF Incubating que usa el patrón Kubernetes Operator para gestionar el despliegue y el ciclo de vida completo de clusters de Apache Kafka, incluida la instalación, las actualizaciones, el escalado y la gestión de certificados. En lugar de escribir manualmente brokers de Kafka como un StatefulSet, declaras el estado deseado mediante CRDs y el Operator reconcilia el estado real del cluster para que coincida.
</details>

2. ¿Cuál de las siguientes opciones es la MENOS precisa como desafío de ejecutar Kafka directamente como un StatefulSet sin Strimzi?
   - A) Gestionar actualizaciones rolling secuenciales
   - B) Emitir y rotar certificados TLS
   - C) Construir imágenes de container se vuelve imposible
   - D) Gestionar el movimiento de datos durante el rebalanceo de particiones

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Construir imágenes de container se vuelve imposible**

**Explicación:**
Ejecutar Kafka directamente como un StatefulSet no es imposible en sí mismo. El problema real es la complejidad operativa y la fragilidad: las actualizaciones secuenciales, la rotación de certificados y el movimiento de datos durante el rebalanceo son difíciles de gestionar manualmente y propensos a errores. Strimzi automatiza todo esto mediante CRDs y lógica de Operator.
</details>

3. ¿Qué comando agrega el repositorio Helm de Strimzi antes de instalar el Cluster Operator?
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) `helm repo add strimzi https://strimzi.io/charts/`**

**Explicación:**
El repositorio Helm oficial de Strimzi es `https://strimzi.io/charts/`. Después de agregarlo, el Cluster Operator se instala con `helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator --namespace kafka --create-namespace`.
</details>

4. ¿Qué scope de namespace observa por defecto el Strimzi Cluster Operator?
   - A) Todos los namespace del cluster
   - B) Todos los namespace `kube-system`
   - C) Solo el namespace en el que está desplegado
   - D) Solo el namespace `default`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Solo el namespace en el que está desplegado**

**Explicación:**
Por defecto, el Cluster Operator solo observa recursos en su propio namespace. Para observar varios namespaces, establece la variable de entorno `STRIMZI_NAMESPACE` en el Operator Deployment con una lista de namespaces separada por comas, o `*` para ampliar el scope de observación a todo el cluster.
</details>

5. ¿Qué campo dejó de ser necesario una vez que Strimzi 0.45+ hizo que el modo KRaft fuera el predeterminado?
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `Kafka.spec.zookeeper`**

**Explicación:**
Con el modo KRaft como predeterminado, el quorum de controllers gestiona los metadatos directamente sin ZooKeeper, por lo que el bloque anteriormente requerido `Kafka.spec.zookeeper` ya no es necesario. Los roles de broker y controller se definen en su lugar mediante recursos `KafkaNodePool` separados.
</details>

6. ¿Qué valor NO es una entrada válida para `KafkaNodePool.spec.roles`?
   - A) `controller`
   - B) `broker`
   - C) Un rol dual que combina `controller` y `broker`
   - D) `zookeeper`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) `zookeeper`**

**Explicación:**
El campo `roles` en un `KafkaNodePool` basado en KRaft solo admite `controller`, `broker` o una combinación de roles dual (`[controller, broker]`). `zookeeper` no es un rol válido: ZooKeeper no existe en absoluto en modo KRaft.
</details>

7. ¿Cuál es la razón principal para ejecutar el pool de nodos controller con 3 nodos?
   - A) Siempre debe coincidir con la cantidad de brokers
   - B) El quorum de controllers requiere un voto mayoritario, por lo que un número impar es más seguro
   - C) Las bibliotecas cliente de Kafka requieren al menos 3 controllers
   - D) Los límites de volumen de EBS lo requieren

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El quorum de controllers requiere un voto mayoritario, por lo que un número impar es más seguro**

**Explicación:**
El quorum de controllers KRaft opera usando un protocolo de consenso similar a Raft que requiere un voto mayoritario para la elección de líder y los commits de metadatos. Un número par de controllers puede provocar escenarios de empate de votos que perjudican la disponibilidad, por lo que son típicas cantidades impares como 3 o 5. Esto se decide independientemente de la cantidad de brokers.
</details>

8. ¿Cuál es el nombre del provisioner CSI usado al definir una StorageClass de EBS para brokers de Kafka en Amazon EKS?
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `ebs.csi.aws.com`**

**Explicación:**
El driver Amazon EBS CSI usa el nombre de provisioner `ebs.csi.aws.com`. `kubernetes.io/aws-ebs` es el provisioner in-tree obsoleto. Los volúmenes `persistent-claim` bajo `KafkaNodePool.spec.storage` referencian una StorageClass respaldada por este provisioner para aprovisionar dinámicamente volúmenes EBS gp3.
</details>

9. ¿Qué campo se agrega a `KafkaNodePool.spec.template.pod` para distribuir los broker Pods de manera uniforme entre AZs?
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `topologySpreadConstraints`**

**Explicación:**
`topologySpreadConstraints` es una restricción de scheduling que distribuye Pods de manera uniforme según una `topologyKey` (por ejemplo, `topology.kubernetes.io/zone`). Distribuir brokers de Kafka entre AZs significa que una interrupción de una sola AZ no derriba la disponibilidad de todo el cluster. Establecer `whenUnsatisfiable: DoNotSchedule` aplica la restricción de forma estricta al bloquear cualquier scheduling que la incumpla.
</details>

10. ¿Qué tipos de listener pueden agregarse a `Kafka.spec.kafka.listeners` cuando clientes externos necesitan alcanzar los brokers de Kafka desde fuera del cluster?
    - A) `internal` y `clusterip`
    - B) `loadbalancer` o `nodeport`
    - C) Solo `ingress`
    - D) La exposición externa no es compatible

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `loadbalancer` o `nodeport`**

**Explicación:**
Los listeners de Strimzi admiten los tipos `internal`, `route`, `ingress`, `loadbalancer` y `nodeport`. En EKS, el acceso externo normalmente se proporciona mediante `loadbalancer` (aprovisiona automáticamente un AWS NLB por bootstrap/broker) o `nodeport` (puertos de nodos worker más un load balancer externo). El tipo `loadbalancer` puede ajustarse mediante annotations que controlan la configuración del NLB del AWS Load Balancer Controller, como el esquema interno frente a internet-facing.
</details>

## Short Answer Questions

11. Nombra los dos componentes internos de Strimzi responsables de sincronizar los recursos personalizados `KafkaTopic` y `KafkaUser` con los recursos reales de Kafka.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Topic Operator, User Operator**

**Explicación:**
El Topic Operator sincroniza unidireccionalmente los recursos personalizados `KafkaTopic` con topics reales de Kafka (el CR es la fuente de verdad), mientras que el User Operator gestiona credenciales de autenticación SCRAM-SHA-512 o TLS y ACLs basándose en recursos personalizados `KafkaUser`. Ambos se agrupan en un único Pod por cluster de Kafka como parte del Entity Operator.
</details>

12. ¿Qué variable de entorno configura el Cluster Operator para observar varios namespaces?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `STRIMZI_NAMESPACE`**

**Explicación:**
Establecer `STRIMZI_NAMESPACE` en el Cluster Operator Deployment controla el scope de namespaces que observa. Puedes especificar una lista de namespaces separada por comas, o `*` para ampliar el scope de observación a todo el cluster.
</details>

13. ¿Qué tipo de storage en `KafkaNodePool.spec.storage` permite adjuntar varios volúmenes EBS por broker para distribuir la E/S?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: JBOD (type: jbod)**

**Explicación:**
El storage JBOD (Just a Bunch Of Disks) permite que un solo broker use varios volúmenes `persistent-claim`, cada uno identificado por un `id` distinto. Esto distribuye la E/S entre varios volúmenes en lugar de quedar limitado por el techo de throughput de un único volumen EBS.
</details>

14. ¿Qué condición de status en el recurso `Kafka` indica que brokers/controllers han formado un quorum saludable y que los listeners están activos?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `Ready: True`**

**Explicación:**
Cuando verificas el status del recurso `Kafka` con `kubectl get kafka -n kafka`, una condición `Ready` establecida en `True` significa que todos los componentes del cluster (brokers, controllers, listeners, Entity Operator) funcionan correctamente.
</details>

15. ¿Cuál es el nombre del CRD de Strimzi que define un cluster worker separado para ejecutar connectors source/sink, como Debezium?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: `KafkaConnect`**

**Explicación:**
`KafkaConnect` es el CRD que define un cluster worker de Kafka Connect. Las instancias individuales de connectors se gestionan declarativamente mediante recursos personalizados `KafkaConnector`, que se despliegan en un cluster `KafkaConnect`.
</details>

## Hands-on Questions

16. Escribe la secuencia completa de comandos para instalar el Strimzi Cluster Operator mediante Helm en el namespace `kafka`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Add the Strimzi Helm repository
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# Install the Cluster Operator into the kafka namespace
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --namespace kafka \
  --create-namespace \
  --version 0.45.0

# Verify the installation
kubectl get pods -n kafka
kubectl get crd | grep strimzi
```

**Explicación:**
`helm repo add` registra el repositorio de Strimzi, y `helm repo update` obtiene los metadatos más recientes del chart. Agregar `--create-namespace` a `helm install` crea automáticamente el namespace `kafka` si aún no existe. Después de instalar, usa `kubectl get pods -n kafka` para confirmar que el Pod del Cluster Operator está `Running`, y `kubectl get crd | grep strimzi` para confirmar que CRDs como `Kafka` y `KafkaNodePool` están registrados.
</details>

17. Escribe un `KafkaNodePool` compuesto por 3 nodos solo broker, cada uno usando un volumen `persistent-claim` de 100Gi basado en gp3.

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
        size: 100Gi
        class: gp3-kafka
        deleteClaim: false
  resources:
    requests:
      cpu: "2"
      memory: 4Gi
    limits:
      cpu: "4"
      memory: 4Gi
```

**Explicación:**
La label `strimzi.io/cluster` debe coincidir con el nombre del recurso `Kafka` al que pertenece este node pool. `roles: [broker]` designa nodos solo broker, y el volumen `persistent-claim` bajo `storage.type: jbod` aprovisiona un persistent volume de 100Gi respaldado por EBS. `class` referencia una StorageClass respaldada por el provisioner `ebs.csi.aws.com`.
</details>

18. Crea un `KafkaTopic` llamado `orders` con 12 particiones y 3 réplicas, luego escribe los comandos para probarlo con el console producer y consumer.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: orders
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 12
  replicas: 3
  config:
    min.insync.replicas: 2
```

```bash
# Apply the topic
kubectl apply -f orders-topic.yaml -n kafka
kubectl get kafkatopic -n kafka

# Producer test
kubectl run kafka-producer -n kafka -ti \
  --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders

# Consumer test
kubectl run kafka-consumer -n kafka -ti \
  --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders --from-beginning
```

**Explicación:**
La label `strimzi.io/cluster` le indica al Topic Operator a qué cluster `Kafka` pertenece este `KafkaTopic`. Después de aplicarlo, `kubectl get kafkatopic -n kafka` confirma que el topic se creó realmente. La prueba de producer/consumer ejecuta la imagen Kafka de Strimzi como un Pod desechable que se conecta al bootstrap Service (`my-cluster-kafka-bootstrap:9092`).
</details>

19. Escribe un `KafkaUser` con autenticación SCRAM-SHA-512 que solo esté autorizado a Read, Write y Describe el topic `orders`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
        operations: [Read, Write, Describe]
```

**Explicación:**
`authentication.type: scram-sha-512` indica al User Operator que genere credenciales SCRAM y las almacene en un Secret. `authorization.type: simple` usa la autorización basada en ACL integrada de Kafka, y la lista `acls` restringe a este usuario únicamente a las operaciones `Read`, `Write` y `Describe` sobre el topic `orders`: implementando el principio de privilegio mínimo declarativamente a nivel de CR.
</details>

20. Agrega `topologySpreadConstraints` al `spec.template.pod` de un `KafkaNodePool` para distribuir los broker Pods de manera uniforme entre AZs.

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
  roles: [broker]
  template:
    pod:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              strimzi.io/cluster: my-cluster
              strimzi.io/name: my-cluster-broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 100Gi
        class: gp3-kafka
```

**Explicación:**
`topologyKey: topology.kubernetes.io/zone` distribuye Pods según la label de AZ en los nodos worker de EKS. `maxSkew: 1` permite como máximo una diferencia de 1 Pod en la cantidad entre AZs, y `whenUnsatisfiable: DoNotSchedule` bloquea directamente el scheduling cuando la restricción no puede satisfacerse, garantizando una distribución uniforme. `labelSelector` determina contra qué conjunto de Pods (el mismo broker node pool) se calcula el skew.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/02-strimzi-operator.md) | [Next Quiz: Kafka Operations](./03-kafka-operations-quiz.md)
