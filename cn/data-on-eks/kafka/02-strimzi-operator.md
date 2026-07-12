# Part 2: Strimzi Operator

> **Supported Versions**: Strimzi 0.45+, Kubernetes 1.28+\
> **最后更新**：July 9, 2026

## Lab Environment Setup

要跟随本文档中的示例操作，你需要以下工具和环境：

### Required Tools

* kubectl v1.28 或更高版本
* Helm v3.12 或更高版本
* 一个可用的 Kubernetes cluster（推荐 Amazon EKS）
* 一个已安装 Amazon EBS CSI driver 的 cluster（用于存储）

## What is Strimzi?

Strimzi 是一个 CNCF Incubating 项目，它使用 Operator 模式在 Kubernetes 上运行 Apache Kafka，并以声明式方式管理 Kafka cluster 的完整生命周期。你可以把 Kafka brokers 手工部署成普通的 StatefulSet，但真实环境中的运维会涉及一系列重复且容易出错的任务：

* 按顺序在 brokers 和 controllers 之间执行滚动升级与配置变更
* 签发、续期和轮换 TLS certificates
* 在 partition rebalancing 和扩缩容期间安全地移动数据
* 以声明式方式管理 users（ACLs）、topics 和 connectors 等支撑资源

Strimzi 将所有这些都抽象在 CRDs（Custom Resource Definitions，自定义资源定义）之后——`Kafka`、`KafkaNodePool`、`KafkaTopic`、`KafkaUser` 和 `KafkaConnect`。你在 YAML 中声明期望状态，Operator 会持续调谐 cluster 的实际状态以匹配它——相比手写 StatefulSet 加上一堆 shell scripts，这是一种可靠且可复现得多的方法。

### Core Components

* **Cluster Operator**：监视 `Kafka`、`KafkaNodePool` 和 `KafkaConnect` 等 cluster 级资源，并创建/管理底层 StatefulSets、Pods、Services 和 ConfigMaps
* **Topic Operator**：将 `KafkaTopic` custom resources 与实际 Kafka topics 同步（单向——CR 是事实来源，会应用到真实 topic 上）
* **User Operator**：基于 `KafkaUser` custom resources 管理 SCRAM-SHA-512 或 TLS authentication credentials 以及 ACLs
* **Entity Operator**：将 Topic Operator 和 User Operator 打包到单个 Pod 中，每个 Kafka cluster 部署一次

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

你也可以不使用 Helm 进行安装，或者通过 OperatorHub 使用 OLM（Operator Lifecycle Manager）安装。

```bash
# Apply the install YAML targeting a specific namespace
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

默认情况下，Cluster Operator 只监视它所部署到的 namespace。若要监视其他 namespaces，请在 Operator Deployment 上将 `STRIMZI_NAMESPACE` environment variable 设置为以逗号分隔的 namespace 列表，或设置为 `*` 以监视整个 cluster。

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## Core CRDs

### Kafka and KafkaNodePool

从 Strimzi 0.45+ 开始，KRaft mode（不使用 ZooKeeper 的 Kafka）成为默认模式，将 broker/controller roles 拆分到独立的 `KafkaNodePool` resources 现在是标准部署形态。在 KRaft 下不再需要旧的 `Kafka.spec.zookeeper` block；相反，每个 node pool 会独立声明其 role（`controller`、`broker` 或组合的 `dual-role`）、resources 和 storage。

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

三个 brokers 和三个 controllers 会形成 quorum，因为 KRaft controller quorum 需要多数票；生产部署通常使用奇数个 controllers（3 或 5 个）。小型 clusters 可以运行单个 `dual-role` pool（`roles: [controller, broker]`），而不使用专用 controller nodes，但在生产环境中，建议将 controller 和 broker roles 放在不同的 node pools 上，以避免资源争用并隔离故障。

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

与 topics 和 users 不同，`KafkaConnect` 定义的是一个独立的 worker cluster，用于运行 source/sink connectors（例如 Debezium 或 S3 sink）。随后通过 `KafkaConnector` custom resources 以声明式方式管理单个 connectors。

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

Brokers 主要受连续顺序写入影响，因此如果你的 workload 超过 gp3 的基线吞吐量（125 MiB/s），请相应提高 `throughput` 和 `iops`。`KafkaNodePool.spec.storage` 支持 JBOD（Just a Bunch Of Disks），让你可以为每个 broker 挂载多个 `persistent-claim` volumes，以便将 I/O 分散到多个 EBS volumes 上。

### 2. AZ Distribution via Pod Anti-Affinity / Topology Spread

如果 broker Pods 落在同一个 AZ 中，一次 AZ outage 可能会导致 quorum 或 partition availability 中断。在 `KafkaNodePool.spec.template.pod` 下添加 `topologySpreadConstraints`，以便将 brokers 均匀分布到各个 AZ。

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

对于保留在 cluster 内部的流量，使用 `internal` listener（plain 或 TLS）；只有当外部 clients 需要访问时，才添加单独的 `loadbalancer` 或 `nodeport` 类型 listener。

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

使用 `type: loadbalancer` 时，Strimzi 会为 bootstrap endpoint 预置一个由 NLB 支持的 Service，并为每个 broker 各预置一个。如果访问应保持在 VPC 内，请使用 `internal` scheme；只有在需要完全公共访问时才切换到 `internet-facing`。为了降低成本和减少 load balancers 数量，你可以切换到 `nodeport`，并通过 worker node NodePorts 结合外部 load balancer 或 Route 53 records 来暴露 brokers。

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

一旦 `Kafka` resource 的 status condition 报告 `Ready: True`，就表示 brokers 和 controllers 已形成健康的 quorum，listeners 也已激活。使用 `kubectl get pods -n kafka` 确认每个 node pool 的 Pods（`my-cluster-broker-0`、`my-cluster-controller-0` 等）处于 `Running` 状态。

## Next Steps

cluster 部署完成后，接下来就是 day-2 operations：扩缩 node pools、使用 Cruise Control 重新平衡 partitions，以及执行零停机版本升级。这些内容将在 [第 3 部分：Kafka Operations](./03-kafka-operations.md) 中介绍。

[返回主页](./)

## Quiz

要测试你在本章中学到的内容，请尝试 [Topic 测验](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)。
