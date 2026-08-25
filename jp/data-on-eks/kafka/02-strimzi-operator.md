# パート 2: Strimzi Operator

> **サポート対象バージョン**: Strimzi 0.45+, Kubernetes 1.28+\
> **最終更新**: July 9, 2026

## ラボ環境のセットアップ

このドキュメントの例に沿って進めるには、以下のツールと環境が必要です。

### 必要なツール

* kubectl v1.28 以降
* Helm v3.12 以降
* 稼働中の Kubernetes クラスター（Amazon EKS 推奨）
* Amazon EBS CSI driver がインストールされたクラスター（ストレージ用）

## Strimzi とは？

Strimzi は、Operator パターンを使用して Kubernetes 上で Apache Kafka を実行し、Kafka クラスターのライフサイクル全体を宣言的に管理する CNCF Incubating プロジェクトです。Kafka broker を通常の StatefulSet として手作業で構築することもできますが、実運用には、反復的でエラーが発生しやすい一連のタスクが伴います。

* broker と controller 間でローリングアップグレードおよび設定変更の順序を調整すること
* TLS 証明書の発行、更新、ローテーション
* partition のリバランスおよびスケールイン／アウト時にデータを安全に移動すること
* user（ACL）、topic、connector などの補助リソースを宣言的に管理すること

Strimzi は、これらすべてを `Kafka`、`KafkaNodePool`、`KafkaTopic`、`KafkaUser`、`KafkaConnect` という CRD（Custom Resource Definitions）の背後に抽象化します。必要な状態を YAML で宣言すると、Operator がクラスターの実際の状態を継続的に調整し、宣言した状態に一致させます。これは、手書きの StatefulSet と大量の shell script を組み合わせるよりも、はるかに信頼性と再現性の高いアプローチです。

### コアコンポーネント

* **Cluster Operator**: `Kafka`、`KafkaNodePool`、`KafkaConnect` などのクラスターレベルのリソースを監視し、基盤となる StatefulSet、Pod、Service、ConfigMap を作成・管理します
* **Topic Operator**: `KafkaTopic` custom resource と実際の Kafka topic を同期します（一方向。CR が信頼できる情報源となり、実際の topic に適用されます）
* **User Operator**: `KafkaUser` custom resource に基づいて SCRAM-SHA-512 または TLS の認証情報と ACL を管理します
* **Entity Operator**: Topic Operator と User Operator を 1 つの Pod にバンドルし、Kafka クラスターごとに 1 回デプロイします

## インストール

### オプション 1: Helm Chart（推奨）

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

### オプション 2: YAML / OperatorHub のインストール

Helm を使わずに、または OperatorHub 経由で OLM（Operator Lifecycle Manager）を使用してインストールすることもできます。

```bash
# Apply the install YAML targeting a specific namespace
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

デフォルトでは、Cluster Operator はデプロイ先の namespace のみを監視します。追加の namespace を監視するには、Operator Deployment 上の `STRIMZI_NAMESPACE` 環境変数に namespace のカンマ区切りリストを設定するか、クラスター全体を監視する場合は `*` を設定します。

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## コア CRD

### Kafka と KafkaNodePool

Strimzi 0.45+ 以降、KRaft モード（ZooKeeper を使用しない Kafka）がデフォルトとなり、broker と controller の役割を別々の `KafkaNodePool` リソースに分割することが標準的なデプロイ構成になりました。KRaft では、従来の `Kafka.spec.zookeeper` ブロックは不要です。代わりに、各 node pool が role（`controller`、`broker`、または両方を持つ `dual-role`）、リソース、ストレージを個別に宣言します。

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

KRaft controller quorum には過半数の投票が必要なため、3 つの broker と 3 つの controller で quorum を構成します。本番デプロイでは通常、奇数の controller（3 または 5）を使用します。小規模なクラスターでは、専用の controller node を使用せず、単一の `dual-role` pool（`roles: [controller, broker]`）を実行できます。ただし本番環境では、リソース競合を回避して障害を分離するために、controller と broker の role を別々の node pool に維持することを推奨します。

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

`KafkaConnect` は、topic や user とは異なり、source/sink connector（たとえば Debezium や S3 sink）を実行する別個の worker クラスターを定義します。個々の connector は `KafkaConnector` custom resource を通じて宣言的に管理されます。

## EKS デプロイ時の考慮事項

### 1. EBS gp3 ベースの StorageClass

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

broker では連続したシーケンシャル書き込みが主な負荷となるため、ワークロードが gp3 のベースライン throughput（125 MiB/s）を超える場合は、`throughput` と `iops` を適宜引き上げてください。`KafkaNodePool.spec.storage` は JBOD（Just a Bunch Of Disks）をサポートしており、broker ごとに複数の `persistent-claim` volume をアタッチして、複数の EBS volume に I/O を分散できます。

### 2. Pod Anti-Affinity / Topology Spread による AZ 分散

broker Pod が同じ AZ に配置されると、AZ 障害によって quorum または partition の可用性が失われる可能性があります。`KafkaNodePool.spec.template.pod` の下に `topologySpreadConstraints` を追加して、broker を AZ 全体に均等に分散してください。

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

### 3. Listener と外部公開

クラスター内に留まるトラフィックには `internal` listener（plain または TLS）を使用し、外部 client からのアクセスが必要な場合にのみ、別個の `loadbalancer` または `nodeport` type listener を追加してください。

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

`type: loadbalancer` では、Strimzi は bootstrap endpoint 用に 1 つ、broker ごとに 1 つの NLB-backed Service をプロビジョニングします。アクセスを VPC 内に限定する場合は `internal` scheme を使用し、完全なパブリックアクセスが必要な場合にのみ `internet-facing` に切り替えてください。コストと load balancer の数を削減するには、`nodeport` に切り替え、外部 load balancer または Route 53 record と組み合わせた worker node NodePort を介して broker を公開できます。

## デプロイ手順

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

`Kafka` resource の status condition が `Ready: True` を報告すると、broker と controller は正常な quorum を形成し、listener がアクティブになっています。`kubectl get pods -n kafka` を使用して、各 node pool（`my-cluster-broker-0`、`my-cluster-controller-0` など）の Pod が `Running` であることを確認してください。

## 次のステップ

クラスターをデプロイしたら、day-2 operations が続きます。node pool のスケーリング、Cruise Control を使用した partition のリバランス、ダウンタイムなしのバージョンアップグレードです。これらについては、[パート 3: Kafka Operations](./03-kafka-operations.md) で説明します。

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[Topic クイズ](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md) に挑戦してください。
