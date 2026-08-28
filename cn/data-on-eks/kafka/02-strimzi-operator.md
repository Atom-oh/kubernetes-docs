# 第 2 部分：Strimzi Operator

> **支持的版本**: Strimzi 0.45+, Kubernetes 1.28+\
> **最后更新**: July 9, 2026

## 实验环境设置

要跟随本文档中的示例操作，您需要以下工具和环境：

### 必需工具

* kubectl v1.28 或更高版本
* Helm v3.12 或更高版本
* 一个可用的 Kubernetes 集群（推荐 Amazon EKS）
* 一个已安装 Amazon EBS CSI driver 的集群（用于存储）

## 什么是 Strimzi？

Strimzi 是一个 CNCF 孵化项目，它使用 Operator 模式在 Kubernetes 上运行 Apache Kafka，以声明式方式管理 Kafka 集群的完整生命周期。您可以将 Kafka broker 手动构建为普通的 StatefulSet，但实际生产运维涉及一系列重复且容易出错的任务：

* 在 broker 和 controller 之间依次执行滚动升级和配置变更
* 签发、续订和轮换 TLS 证书
* 在分区再平衡以及扩缩容期间安全地迁移数据
* 以声明式方式管理用户（ACL）、topic 和 connector 等支持资源

Strimzi 通过 CRD（Custom Resource Definition）抽象了所有这些操作：`Kafka`、`KafkaNodePool`、`KafkaTopic`、`KafkaUser` 和 `KafkaConnect`。您在 YAML 中声明期望状态，Operator 会持续协调集群的实际状态以使其匹配——与手写 StatefulSet 加上一堆 shell 脚本相比，这种方式更可靠、更可复现。

### 核心组件

* **Cluster Operator**：监视 `Kafka`、`KafkaNodePool` 和 `KafkaConnect` 等集群级资源，并创建/管理底层的 StatefulSet、Pod、Service 和 ConfigMap
* **Topic Operator**：将 `KafkaTopic` 自定义资源与实际 Kafka topic 同步（单向同步——CR 是事实来源，并应用到真实 topic）
* **User Operator**：根据 `KafkaUser` 自定义资源管理 SCRAM-SHA-512 或 TLS 身份验证凭证及 ACL
* **Entity Operator**：将 Topic Operator 和 User Operator 打包到单个 Pod 中，每个 Kafka 集群部署一次

## 安装

### 选项 1：Helm Chart（推荐）

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

### 选项 2：安装 YAML / OperatorHub

您也可以不使用 Helm 安装，或通过 OperatorHub 中的 OLM（Operator Lifecycle Manager）安装。

```bash
# Apply the install YAML targeting a specific namespace
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

默认情况下，Cluster Operator 仅监视其部署所在的 namespace。要监视其他 namespace，请将 Operator Deployment 上的 `STRIMZI_NAMESPACE` 环境变量设置为以逗号分隔的 namespace 列表；或设为 `*` 以监视整个集群。

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## 核心 CRD

### Kafka 和 KafkaNodePool

从 Strimzi 0.45+ 开始，KRaft 模式（不使用 ZooKeeper 的 Kafka）为默认模式，将 broker/controller 角色拆分为独立的 `KafkaNodePool` 资源也已成为标准部署形态。在 KRaft 下，不再需要旧版的 `Kafka.spec.zookeeper` 块；每个 node pool 改为独立声明其角色（`controller`、`broker` 或组合的 `dual-role`）、资源和存储。

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

三个 broker 和三个 controller 构成 quorum，因为 KRaft controller quorum 需要多数票；生产部署通常使用奇数个 controller（3 或 5）。小型集群可运行单个 `dual-role` pool（`roles: [controller, broker]`），无需专用 controller 节点；但在生产环境中，建议将 controller 和 broker 角色保留在独立的 node pool 中，以避免资源争用并隔离故障。

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

与 topic 和用户不同，`KafkaConnect` 定义了一个运行 source/sink connector（例如 Debezium 或 S3 sink）的独立 worker 集群。随后可通过 `KafkaConnector` 自定义资源以声明式方式管理各个 connector。

## EKS 部署注意事项

### 1. 基于 EBS gp3 的 StorageClass

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

broker 主要由持续的顺序写入负载构成，因此如果您的工作负载超过 gp3 的基准吞吐量（125 MiB/s），请相应提高 `throughput` 和 `iops`。`KafkaNodePool.spec.storage` 支持 JBOD（Just a Bunch Of Disks），允许您为每个 broker 挂载多个 `persistent-claim` volume，从而将 I/O 分布到多个 EBS volume。

### 2. 通过 Pod Anti-Affinity / Topology Spread 实现 AZ 分布

如果 broker Pod 被调度到相同的 AZ，AZ 故障可能导致 quorum 或分区可用性丧失。在 `KafkaNodePool.spec.template.pod` 下添加 `topologySpreadConstraints`，以便将 broker 均匀分布到各个 AZ。

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

### 3. Listener 和外部暴露

对于保留在集群内部的流量，请使用 `internal` listener（plain 或 TLS）；仅当外部客户端需要访问时，再添加单独的 `loadbalancer` 或 `nodeport` 类型 listener。

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

使用 `type: loadbalancer` 时，Strimzi 会为 bootstrap endpoint 配置一个由 NLB 支持的 Service，并为每个 broker 配置一个 Service。如果访问应保留在 VPC 内部，请使用 `internal` scheme；只有在需要完全公开访问时，才切换为 `internet-facing`。为减少成本和 load balancer 的数量，您可以切换到 `nodeport`，并通过 worker node NodePort 配合外部 load balancer 或 Route 53 record 暴露 broker。

## 部署流程

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

当 `Kafka` 资源的状态条件报告 `Ready: True` 后，broker 和 controller 已形成健康的 quorum，且 listener 已激活。使用 `kubectl get pods -n kafka` 确认每个 node pool 的 Pod（`my-cluster-broker-0`、`my-cluster-controller-0` 等）均为 `Running`。

## 后续步骤

集群部署完成后，接下来是第 2 天运维：扩展 node pool、使用 Cruise Control 再平衡分区，以及执行零停机版本升级。这些内容将在[第 3 部分：Kafka 运维](./03-kafka-operations.md)中介绍。

[返回主页](./README.md)

## 测验

为测试您在本章中学到的内容，请尝试[Topic 测验](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)。
