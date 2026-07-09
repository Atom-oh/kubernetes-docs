# Part 2: Strimzi Operator

> **Supported Versions**: Strimzi 0.45+, Kubernetes 1.28+\
> **Last Updated**: July 9, 2026

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* kubectl v1.28 or later
* Helm v3.12 or later
* A working Kubernetes cluster (Amazon EKS recommended)
* A cluster with the Amazon EBS CSI driver installed (for storage)

## What is Strimzi?

Strimzi is a CNCF Incubating project that runs Apache Kafka on Kubernetes using the Operator pattern, managing the full lifecycle of a Kafka cluster declaratively. You could hand-roll Kafka brokers as a plain StatefulSet, but real-world operation involves a set of repetitive, error-prone tasks:

* Sequencing rolling upgrades and configuration changes across brokers and controllers
* Issuing, renewing, and rotating TLS certificates
* Moving data safely during partition rebalancing and scale in/out
* Declaratively managing supporting resources such as users (ACLs), topics, and connectors

Strimzi abstracts all of this behind CRDs (Custom Resource Definitions) — `Kafka`, `KafkaNodePool`, `KafkaTopic`, `KafkaUser`, and `KafkaConnect`. You declare the desired state in YAML, and the Operator continuously reconciles the cluster's actual state to match it — a far more reliable and reproducible approach than a hand-written StatefulSet plus a pile of shell scripts.

### Core Components

* **Cluster Operator**: Watches cluster-level resources such as `Kafka`, `KafkaNodePool`, and `KafkaConnect`, and creates/manages the underlying StatefulSets, Pods, Services, and ConfigMaps
* **Topic Operator**: Synchronizes `KafkaTopic` custom resources with actual Kafka topics (unidirectional — the CR is the source of truth, applied onto the real topic)
* **User Operator**: Manages SCRAM-SHA-512 or TLS authentication credentials and ACLs based on `KafkaUser` custom resources
* **Entity Operator**: Bundles the Topic Operator and User Operator into a single Pod, deployed once per Kafka cluster

## Installation

### Option 1: Helm Chart (Recommended)

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

### Option 2: Install YAML / OperatorHub

You can also install without Helm, or through OLM (Operator Lifecycle Manager) via OperatorHub.

```bash
# Apply the install YAML targeting a specific namespace
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

By default, the Cluster Operator only watches the namespace it is deployed into. To watch additional namespaces, set the `STRIMZI_NAMESPACE` environment variable on the Operator Deployment to a comma-separated list of namespaces, or `*` to watch the entire cluster.

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## Core CRDs

### Kafka and KafkaNodePool

Starting with Strimzi 0.45+, KRaft mode (Kafka without ZooKeeper) is the default, and splitting broker/controller roles into separate `KafkaNodePool` resources is now the standard deployment shape. The legacy `Kafka.spec.zookeeper` block is no longer needed under KRaft; instead, each node pool independently declares its role (`controller`, `broker`, or a combined `dual-role`), resources, and storage.

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

Three brokers and three controllers form a quorum because the KRaft controller quorum requires a majority vote; production deployments typically use an odd number of controllers (3 or 5). Small clusters can run a single `dual-role` pool (`roles: [controller, broker]`) without dedicated controller nodes, but in production it's recommended to keep controller and broker roles on separate node pools to avoid resource contention and to isolate failures.

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

Unlike topics and users, `KafkaConnect` defines a separate worker cluster that runs source/sink connectors (for example, Debezium or an S3 sink). Individual connectors are then managed declaratively through `KafkaConnector` custom resources.

## EKS Deployment Considerations

### 1. EBS gp3-based StorageClass

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

Brokers are dominated by continuous sequential writes, so if your workload exceeds gp3's baseline throughput (125 MiB/s), raise `throughput` and `iops` accordingly. `KafkaNodePool.spec.storage` supports JBOD (Just a Bunch Of Disks), letting you attach multiple `persistent-claim` volumes per broker to spread I/O across several EBS volumes.

### 2. AZ Distribution via Pod Anti-Affinity / Topology Spread

If broker Pods land on the same AZ, an AZ outage can take down quorum or partition availability. Add `topologySpreadConstraints` under `KafkaNodePool.spec.template.pod` to spread brokers evenly across AZs.

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

### 3. Listeners and External Exposure

Use an `internal` listener (plain or TLS) for traffic that stays inside the cluster, and add a separate `loadbalancer` or `nodeport` type listener only when external clients need access.

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

With `type: loadbalancer`, Strimzi provisions one NLB-backed Service for the bootstrap endpoint and one per broker. Use an `internal` scheme if access should stay within the VPC, and switch to `internet-facing` only when full public access is required. To reduce cost and the number of load balancers, you can switch to `nodeport` and expose brokers through worker node NodePorts combined with an external load balancer or Route 53 records.

## Deployment Procedure

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

Once the `Kafka` resource's status condition reports `Ready: True`, the brokers and controllers have formed a healthy quorum and the listeners are active. Use `kubectl get pods -n kafka` to confirm that the Pods for each node pool (`my-cluster-broker-0`, `my-cluster-controller-0`, etc.) are `Running`.

## Next Steps

Once the cluster is deployed, day-2 operations come next: scaling node pools, rebalancing partitions with Cruise Control, and performing zero-downtime version upgrades. These are covered in [Part 3: Kafka Operations](./03-kafka-operations.md).

[Return to Main Page](./)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md).
