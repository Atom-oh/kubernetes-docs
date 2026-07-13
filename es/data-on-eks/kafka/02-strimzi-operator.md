# Parte 2: Strimzi Operator

> **Versiones compatibles**: Strimzi 0.45+, Kubernetes 1.28+\
> **Última actualización**: July 9, 2026

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Herramientas requeridas

* kubectl v1.28 o posterior
* Helm v3.12 o posterior
* Un cluster de Kubernetes funcional (se recomienda Amazon EKS)
* Un cluster con el Amazon EBS CSI driver instalado (para storage)

## ¿Qué es Strimzi?

Strimzi es un proyecto CNCF Incubating que ejecuta Apache Kafka en Kubernetes usando el patrón Operator, administrando de forma declarativa todo el ciclo de vida de un cluster de Kafka. Podrías crear manualmente Kafka brokers como un StatefulSet simple, pero la operación en el mundo real implica un conjunto de tareas repetitivas y propensas a errores:

* Secuenciar rolling upgrades y cambios de configuración entre brokers y controllers
* Emitir, renovar y rotar certificados TLS
* Mover datos de forma segura durante el rebalanceo de partitions y el scale in/out
* Administrar de forma declarativa recursos de soporte como users (ACLs), topics y connectors

Strimzi abstrae todo esto detrás de CRDs (Custom Resource Definitions): `Kafka`, `KafkaNodePool`, `KafkaTopic`, `KafkaUser` y `KafkaConnect`. Declaras el estado deseado en YAML, y el Operator reconcilia continuamente el estado real del cluster para que coincida con él: un enfoque mucho más confiable y reproducible que un StatefulSet escrito a mano más una pila de scripts shell.

### Componentes principales

* **Cluster Operator**: Observa recursos a nivel de cluster como `Kafka`, `KafkaNodePool` y `KafkaConnect`, y crea/administra los StatefulSets, Pods, Services y ConfigMaps subyacentes
* **Topic Operator**: Sincroniza recursos personalizados `KafkaTopic` con topics de Kafka reales (unidireccional: el CR es la fuente de verdad, aplicada sobre el topic real)
* **User Operator**: Administra credenciales de autenticación SCRAM-SHA-512 o TLS y ACLs basándose en recursos personalizados `KafkaUser`
* **Entity Operator**: Agrupa el Topic Operator y el User Operator en un único Pod, desplegado una vez por cada cluster de Kafka

## Instalación

### Opción 1: Helm Chart (recomendada)

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

### Opción 2: Install YAML / OperatorHub

También puedes instalar sin Helm, o mediante OLM (Operator Lifecycle Manager) a través de OperatorHub.

```bash
# Apply the install YAML targeting a specific namespace
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

De forma predeterminada, el Cluster Operator solo observa el namespace en el que se despliega. Para observar namespaces adicionales, establece la variable de entorno `STRIMZI_NAMESPACE` en el Operator Deployment con una lista de namespaces separada por comas, o `*` para observar todo el cluster.

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## CRDs principales

### Kafka y KafkaNodePool

A partir de Strimzi 0.45+, el modo KRaft (Kafka sin ZooKeeper) es el valor predeterminado, y dividir los roles de broker/controller en recursos `KafkaNodePool` separados es ahora la forma estándar de deployment. El bloque legacy `Kafka.spec.zookeeper` ya no es necesario con KRaft; en su lugar, cada node pool declara de forma independiente su role (`controller`, `broker` o un `dual-role` combinado), recursos y storage.

```yaml
# Controller-only node pool (3 nodes, forming a quorum)
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: controller
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - controller
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 20Gi
        class: gp3-kafka
        deleteClaim: false
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
---
# Broker-only node pool (3 nodes)
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
---
# The Kafka cluster itself (KRaft, no ZooKeeper)
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
spec:
  kafka:
    version: 3.9.0
    metadataVersion: 3.9-IV0
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

Tres brokers y tres controllers forman un quorum porque el KRaft controller quorum requiere una votación mayoritaria; los deployments de producción normalmente usan un número impar de controllers (3 o 5). Los clusters pequeños pueden ejecutar un único pool `dual-role` (`roles: [controller, broker]`) sin nodes controller dedicados, pero en producción se recomienda mantener los roles de controller y broker en node pools separados para evitar contención de recursos y aislar fallos.

### KafkaTopic

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
    retention.ms: 604800000
    min.insync.replicas: 2
```

### KafkaUser

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

### KafkaConnect

A diferencia de topics y users, `KafkaConnect` define un worker cluster separado que ejecuta source/sink connectors (por ejemplo, Debezium o un S3 sink). Luego, los connectors individuales se administran de forma declarativa mediante recursos personalizados `KafkaConnector`.

## Consideraciones para deployment en EKS

### 1. StorageClass basada en EBS gp3

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "250"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

Los brokers están dominados por escrituras secuenciales continuas, por lo que si tu workload supera el throughput baseline de gp3 (125 MiB/s), aumenta `throughput` e `iops` según corresponda. `KafkaNodePool.spec.storage` admite JBOD (Just a Bunch Of Disks), lo que te permite adjuntar varios volúmenes `persistent-claim` por broker para distribuir I/O entre varios volúmenes EBS.

### 2. Distribución entre AZ mediante Pod Anti-Affinity / Topology Spread

Si los broker Pods aterrizan en la misma AZ, una caída de AZ puede afectar el quorum o la disponibilidad de partitions. Agrega `topologySpreadConstraints` bajo `KafkaNodePool.spec.template.pod` para distribuir los brokers de manera uniforme entre AZs.

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

### 3. Listeners y exposición externa

Usa un listener `internal` (plain o TLS) para el tráfico que permanece dentro del cluster, y agrega un listener separado de tipo `loadbalancer` o `nodeport` solo cuando los clientes externos necesiten acceso.

```yaml
listeners:
  - name: plain
    port: 9092
    type: internal
    tls: false
  - name: tls
    port: 9093
    type: internal
    tls: true
  - name: external
    port: 9094
    type: loadbalancer
    tls: true
    configuration:
      bootstrap:
        annotations:
          service.beta.kubernetes.io/aws-load-balancer-type: nlb
          service.beta.kubernetes.io/aws-load-balancer-scheme: internal
```

Con `type: loadbalancer`, Strimzi aprovisiona un Service respaldado por NLB para el endpoint bootstrap y uno por cada broker. Usa un scheme `internal` si el acceso debe permanecer dentro de la VPC, y cambia a `internet-facing` solo cuando se requiera acceso público completo. Para reducir el costo y la cantidad de load balancers, puedes cambiar a `nodeport` y exponer brokers mediante NodePorts de worker nodes combinados con un load balancer externo o registros de Route 53.

## Procedimiento de deployment

```bash
# 1. Verify the Cluster Operator is running
kubectl get pods -n kafka

# 2. Apply the KafkaNodePool and Kafka custom resources
kubectl apply -f controller-pool.yaml -n kafka
kubectl apply -f broker-pool.yaml -n kafka
kubectl apply -f kafka-cluster.yaml -n kafka

# 3. Check cluster status (wait until the Ready condition is True)
kubectl get kafka -n kafka -w
kubectl get pods -n kafka

# 4. Create a topic
kubectl apply -f orders-topic.yaml -n kafka
kubectl get kafkatopic -n kafka

# 5. Produce/consume test
kubectl run kafka-producer -n kafka -ti --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders

kubectl run kafka-consumer -n kafka -ti --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders --from-beginning
```

Una vez que la condition de status del recurso `Kafka` informa `Ready: True`, los brokers y controllers han formado un quorum saludable y los listeners están activos. Usa `kubectl get pods -n kafka` para confirmar que los Pods de cada node pool (`my-cluster-broker-0`, `my-cluster-controller-0`, etc.) están `Running`.

## Próximos pasos

Una vez que el cluster está desplegado, siguen las operaciones day-2: escalar node pools, rebalancear partitions con Cruise Control y realizar upgrades de versión sin downtime. Estas se cubren en [Parte 3: Operaciones de Kafka](./03-kafka-operations.md).

[Volver a la página principal](./)

## Cuestionario

Para poner a prueba lo que aprendiste en este capítulo, prueba el [Cuestionario del topic](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md).
