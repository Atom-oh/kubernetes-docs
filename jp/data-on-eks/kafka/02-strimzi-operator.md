# パート 2: Strimzi Operator

> **サポート対象バージョン**: Strimzi 0.45+, Kubernetes 1.28+\
> **最終更新**: July 9, 2026

## Lab 環境のセットアップ

このドキュメントの例に沿って進めるには、以下のツールと環境が必要です。

### 必要なツール

* kubectl v1.28 以降
* Helm v3.12 以降
* 稼働中の Kubernetes cluster (Amazon EKS 推奨)
* Amazon EBS CSI driver がインストールされた cluster (ストレージ用)

## Strimzi とは?

Strimzi は、Operator pattern を使用して Apache Kafka を Kubernetes 上で実行する CNCF Incubating project であり、Kafka cluster のライフサイクル全体を宣言的に管理します。Kafka broker を通常の StatefulSet として手作業で構築することもできますが、実運用では反復的でエラーが起きやすい作業が数多く発生します。

* broker と controller 全体にわたる rolling upgrade と設定変更の順序制御
* TLS 証明書の発行、更新、ローテーション
* partition rebalancing と scale in/out の際のデータの安全な移動
* user (ACL)、topic、connector などの補助リソースの宣言的管理

Strimzi は、これらすべてを CRD (Custom Resource Definitions) — `Kafka`、`KafkaNodePool`、`KafkaTopic`、`KafkaUser`、`KafkaConnect` — の背後に抽象化します。目的の状態を YAML で宣言すると、Operator が cluster の実際の状態を継続的に reconcile して一致させます。これは、手書きの StatefulSet と大量の shell script を組み合わせるよりも、はるかに信頼性と再現性の高いアプローチです。

### 主要コンポーネント

* **Cluster Operator**: `Kafka`、`KafkaNodePool`、`KafkaConnect` などの cluster level resource を監視し、基盤となる StatefulSet、Pod、Service、ConfigMap を作成および管理します
* **Topic Operator**: `KafkaTopic` custom resource を実際の Kafka topic と同期します (単方向 — CR が信頼できる情報源であり、実際の topic に適用されます)
* **User Operator**: `KafkaUser` custom resource に基づいて、SCRAM-SHA-512 または TLS authentication credential と ACL を管理します
* **Entity Operator**: Topic Operator と User Operator を 1 つの Pod にまとめ、Kafka cluster ごとに 1 回 deploy します

## インストール

### オプション 1: Helm Chart (推奨)

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

### オプション 2: YAML / OperatorHub によるインストール

Helm を使わずにインストールすることも、OperatorHub 経由で OLM (Operator Lifecycle Manager) を通じてインストールすることもできます。

```bash
# Apply the install YAML targeting a specific namespace
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

デフォルトでは、Cluster Operator は deploy された namespace のみを監視します。追加の namespace を監視するには、Operator Deployment の `STRIMZI_NAMESPACE` environment variable にカンマ区切りの namespace list を設定するか、cluster 全体を監視する場合は `*` を設定します。

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## 主要 CRD

### Kafka と KafkaNodePool

Strimzi 0.45+ 以降では、KRaft mode (ZooKeeper なしの Kafka) がデフォルトであり、broker/controller role を別々の `KafkaNodePool` resource に分割することが標準的な deployment 形態になっています。従来の `Kafka.spec.zookeeper` block は KRaft では不要です。代わりに、各 node pool がそれぞれ role (`controller`、`broker`、または combined `dual-role`)、resource、storage を独立して宣言します。

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

3 つの broker と 3 つの controller が quorum を形成します。これは、KRaft controller quorum が majority vote を必要とするためです。本番 deployment では、通常 controller の数を奇数 (3 または 5) にします。小規模 cluster では、専用の controller node を使わずに単一の `dual-role` pool (`roles: [controller, broker]`) を実行できますが、本番では resource contention を避け、障害を分離するために、controller と broker の role を別々の node pool に分けることが推奨されます。

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

topic や user とは異なり、`KafkaConnect` は source/sink connector (たとえば Debezium や S3 sink) を実行する別個の worker cluster を定義します。個々の connector は、`KafkaConnector` custom resource を通じて宣言的に管理されます。

## EKS Deployment の考慮事項

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

broker は継続的な sequential write が中心となるため、workload が gp3 の baseline throughput (125 MiB/s) を超える場合は、それに応じて `throughput` と `iops` を引き上げてください。`KafkaNodePool.spec.storage` は JBOD (Just a Bunch Of Disks) をサポートしており、broker ごとに複数の `persistent-claim` volume を attach して、I/O を複数の EBS volume に分散できます。

### 2. Pod Anti-Affinity / Topology Spread による AZ 分散

broker Pod が同じ AZ に配置されると、AZ outage によって quorum や partition availability が失われる可能性があります。`KafkaNodePool.spec.template.pod` の下に `topologySpreadConstraints` を追加し、broker を AZ 全体に均等に分散させます。

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

### 3. Listener と External Exposure

cluster 内に留まる traffic には `internal` listener (plain または TLS) を使用し、external client が access する必要がある場合にのみ、別の `loadbalancer` または `nodeport` type listener を追加します。

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

`type: loadbalancer` では、Strimzi は bootstrap endpoint 用に NLB-backed Service を 1 つ、broker ごとに 1 つずつ provision します。access を VPC 内に留める必要がある場合は `internal` scheme を使用し、完全な public access が必要な場合にのみ `internet-facing` に切り替えます。cost と load balancer の数を減らすには、`nodeport` に切り替え、worker node NodePort を external load balancer または Route 53 record と組み合わせて broker を expose できます。

## Deployment 手順

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

`Kafka` resource の status condition が `Ready: True` を報告すると、broker と controller は健全な quorum を形成し、listener が active になっています。`kubectl get pods -n kafka` を使用して、各 node pool の Pod (`my-cluster-broker-0`、`my-cluster-controller-0` など) が `Running` であることを確認します。

## 次のステップ

cluster が deploy されたら、次は day-2 operation です。node pool の scaling、Cruise Control を使った partition rebalancing、zero-downtime version upgrade の実行が含まれます。これらは [パート 3: Kafka Operations](./03-kafka-operations.md) で説明します。

[メインページに戻る](./)

## Quiz

この章で学んだ内容を確認するには、[Topic Quiz](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md) に挑戦してください。
