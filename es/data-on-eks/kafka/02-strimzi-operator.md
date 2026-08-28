# Parte 2: Operador Strimzi

> **Versiones compatibles**: Strimzi 0.45+, Kubernetes 1.28+\
> **Última actualización**: July 9, 2026

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitará las siguientes herramientas y entorno:

### Herramientas necesarias

* kubectl v1.28 o posterior
* Helm v3.12 o posterior
* Un clúster de Kubernetes funcional (se recomienda Amazon EKS)
* Un clúster con el controlador CSI de Amazon EBS instalado (para almacenamiento)

## ¿Qué es Strimzi?

Strimzi es un proyecto de CNCF en incubación que ejecuta Apache Kafka en Kubernetes mediante el patrón Operator, y administra de forma declarativa el ciclo de vida completo de un clúster de Kafka. Podría implementar manualmente brokers de Kafka como un StatefulSet simple, pero la operación en el mundo real implica un conjunto de tareas repetitivas y propensas a errores:

* Secuenciar actualizaciones graduales y cambios de configuración entre brokers y controllers
* Emitir, renovar y rotar certificados TLS
* Mover datos de forma segura durante el reequilibrio de particiones y el escalado horizontal o vertical
* Administrar de forma declarativa recursos auxiliares como usuarios (ACL), topics y conectores

Strimzi abstrae todo esto mediante CRD (Custom Resource Definitions): `Kafka`, `KafkaNodePool`, `KafkaTopic`, `KafkaUser` y `KafkaConnect`. Usted declara el estado deseado en YAML, y el Operator reconcilia continuamente el estado real del clúster para que coincida con él: un enfoque mucho más fiable y reproducible que un StatefulSet escrito manualmente junto con un conjunto de scripts de shell.

### Componentes principales

* **Cluster Operator**: Supervisa recursos a nivel de clúster como `Kafka`, `KafkaNodePool` y `KafkaConnect`, y crea o administra los StatefulSets, Pods, Services y ConfigMaps subyacentes
* **Topic Operator**: Sincroniza recursos personalizados `KafkaTopic` con topics reales de Kafka (unidireccional: el CR es la fuente de verdad y se aplica sobre el topic real)
* **User Operator**: Administra credenciales de autenticación SCRAM-SHA-512 o TLS y ACL según los recursos personalizados `KafkaUser`
* **Entity Operator**: Agrupa el Topic Operator y el User Operator en un único Pod, implementado una vez por cada clúster de Kafka

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

### Opción 2: Instalar YAML / OperatorHub

También puede instalar sin Helm o mediante OLM (Operator Lifecycle Manager) a través de OperatorHub.

```bash
# Apply the install YAML targeting a specific namespace
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

De forma predeterminada, el Cluster Operator solo supervisa el namespace en el que está implementado. Para supervisar namespaces adicionales, configure la variable de entorno `STRIMZI_NAMESPACE` en el Deployment del Operator con una lista de namespaces separada por comas, o con `*` para supervisar todo el clúster.

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## CRD principales

### Kafka y KafkaNodePool

A partir de Strimzi 0.45+, el modo KRaft (Kafka sin ZooKeeper) es el predeterminado, y dividir los roles de broker/controller en recursos `KafkaNodePool` independientes es ahora la forma de implementación estándar. El bloque heredado `Kafka.spec.zookeeper` ya no es necesario con KRaft; en su lugar, cada pool de nodos declara de forma independiente su rol (`controller`, `broker` o un `dual-role` combinado), recursos y almacenamiento.

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

Tres brokers y tres controllers forman un quórum porque el quórum de controllers de KRaft requiere un voto mayoritario; las implementaciones de producción suelen usar un número impar de controllers (3 o 5). Los clústeres pequeños pueden ejecutar un único pool `dual-role` (`roles: [controller, broker]`) sin nodos de controller dedicados, pero en producción se recomienda mantener los roles de controller y broker en pools de nodos separados para evitar la contención de recursos y aislar fallos.

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

A diferencia de los topics y los usuarios, `KafkaConnect` define un clúster de workers independiente que ejecuta conectores de origen/destino (por ejemplo, Debezium o un destino S3). Después, los conectores individuales se administran de forma declarativa mediante recursos personalizados `KafkaConnector`.

## Consideraciones de implementación en EKS

### 1. StorageClass basado en EBS gp3

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

Los brokers están dominados por escrituras secuenciales continuas, por lo que, si su carga de trabajo supera el rendimiento base de gp3 (125 MiB/s), aumente `throughput` e `iops` según corresponda. `KafkaNodePool.spec.storage` admite JBOD (Just a Bunch Of Disks), lo que permite adjuntar varios volúmenes `persistent-claim` por broker para distribuir la E/S entre varios volúmenes EBS.

### 2. Distribución de AZ mediante Pod Anti-Affinity / Topology Spread

Si los Pods de broker se ubican en la misma AZ, una interrupción de AZ puede dejar fuera de servicio el quórum o la disponibilidad de las particiones. Agregue `topologySpreadConstraints` en `KafkaNodePool.spec.template.pod` para distribuir los brokers de manera uniforme entre las AZ.

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

Use un listener `internal` (simple o TLS) para el tráfico que permanece dentro del clúster, y agregue un listener independiente de tipo `loadbalancer` o `nodeport` solo cuando los clientes externos necesiten acceso.

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

Con `type: loadbalancer`, Strimzi aprovisiona un Service respaldado por NLB para el endpoint bootstrap y uno por cada broker. Use un esquema `internal` si el acceso debe permanecer dentro de la VPC, y cambie a `internet-facing` solo cuando se requiera acceso público completo. Para reducir el coste y el número de balanceadores de carga, puede cambiar a `nodeport` y exponer los brokers mediante NodePorts de los nodos worker combinados con un balanceador de carga externo o registros de Route 53.

## Procedimiento de implementación

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

Una vez que la condición de estado del recurso `Kafka` informe `Ready: True`, los brokers y controllers habrán formado un quórum saludable y los listeners estarán activos. Use `kubectl get pods -n kafka` para confirmar que los Pods de cada pool de nodos (`my-cluster-broker-0`, `my-cluster-controller-0`, etc.) estén en estado `Running`.

## Próximos pasos

Una vez implementado el clúster, siguen las operaciones del día 2: escalar pools de nodos, reequilibrar particiones con Cruise Control y realizar actualizaciones de versión sin tiempo de inactividad. Estas se tratan en la [Parte 3: Operaciones de Kafka](./03-kafka-operations.md).

[Volver a la página principal](./README.md)

## Cuestionario

Para evaluar lo que ha aprendido en este capítulo, pruebe el [Cuestionario de topics](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md).
