# Strimzi Operator クイズ

このクイズでは、Strimzi Operator の基礎、インストール方法、主要な CRD、KRaft node role、EKS へのデプロイ時の考慮事項についての理解を確認します。

## 多肢選択問題

1. Strimzi はどのような CNCF project ですか？
   - A) service mesh
   - B) Kubernetes 上で Apache Kafka を実行するための Operator
   - C) container runtime
   - D) CI/CD pipeline tool

<details>

<summary>解答を表示</summary>

**解答: B) Kubernetes 上で Apache Kafka を実行するための Operator**

**解説:**
Strimzi は CNCF Incubating project であり、Kubernetes Operator pattern を使用して、インストール、アップグレード、スケーリング、certificate 管理を含む Apache Kafka cluster のデプロイとライフサイクル全体を管理します。Kafka broker を StatefulSet として手作業で記述する代わりに、CRD を通じて望ましい状態を宣言し、Operator が実際の cluster 状態をそれに一致するよう調整します。
</details>

2. Strimzi を使わずに Kafka を StatefulSet として直接実行する際の課題として、次のうち最も正確でないものはどれですか？
   - A) sequential rolling upgrade の処理
   - B) TLS certificate の発行とローテーション
   - C) container image のビルドが不可能になる
   - D) partition rebalancing 中の data movement の管理

<details>

<summary>解答を表示</summary>

**解答: C) container image のビルドが不可能になる**

**解説:**
Kafka を StatefulSet として直接実行すること自体は不可能ではありません。本当の問題は、運用上の複雑さと脆さです。sequential upgrade、certificate rotation、rebalancing 中の data movement は、手作業で管理するのが難しく、エラーも起きやすくなります。Strimzi は CRD と Operator logic によって、これらすべてを自動化します。
</details>

3. Cluster Operator をインストールする前に Strimzi Helm repository を追加するコマンドはどれですか？
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>解答を表示</summary>

**解答: A) `helm repo add strimzi https://strimzi.io/charts/`**

**解説:**
Strimzi の公式 Helm repository は `https://strimzi.io/charts/` です。追加後、Cluster Operator は `helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator --namespace kafka --create-namespace` でインストールします。
</details>

4. Strimzi Cluster Operator はデフォルトでどの namespace scope を監視しますか？
   - A) cluster 内のすべての namespace
   - B) すべての `kube-system` namespace
   - C) デプロイされた namespace のみ
   - D) `default` namespace のみ

<details>

<summary>解答を表示</summary>

**解答: C) デプロイされた namespace のみ**

**解説:**
デフォルトでは、Cluster Operator は自身の namespace 内の resource のみを監視します。複数の namespace を監視するには、Operator Deployment の `STRIMZI_NAMESPACE` environment variable に namespace のカンマ区切りリストを設定するか、`*` を指定して監視 scope を cluster 全体に拡張します。
</details>

5. Strimzi 0.45+ で KRaft mode がデフォルトになったことで不要になった field はどれですか？
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>解答を表示</summary>

**解答: B) `Kafka.spec.zookeeper`**

**解説:**
KRaft mode がデフォルトになったことで、controller quorum が ZooKeeper なしで metadata を直接管理するため、以前は必須だった `Kafka.spec.zookeeper` block は不要になりました。代わりに、broker と controller の role は個別の `KafkaNodePool` resource を通じて定義されます。
</details>

6. `KafkaNodePool.spec.roles` の有効な entry ではない値はどれですか？
   - A) `controller`
   - B) `broker`
   - C) `controller` と `broker` を組み合わせた dual-role
   - D) `zookeeper`

<details>

<summary>解答を表示</summary>

**解答: D) `zookeeper`**

**解説:**
KRaft-based の `KafkaNodePool` における `roles` field は、`controller`、`broker`、または dual-role combination（`[controller, broker]`）のみをサポートします。`zookeeper` は有効な role ではありません。KRaft mode では ZooKeeper は一切存在しません。
</details>

7. controller node pool を 3 nodes で実行する主な理由は何ですか？
   - A) broker 数と常に一致させる必要があるため
   - B) controller quorum には majority vote が必要なため、奇数の方が安全である
   - C) Kafka client library は少なくとも 3 controllers を必要とするため
   - D) EBS volume limit のため

<details>

<summary>解答を表示</summary>

**解答: B) controller quorum には majority vote が必要なため、奇数の方が安全である**

**解説:**
KRaft controller quorum は、leader election と metadata commit に majority vote を必要とする Raft-like consensus protocol を使用して動作します。controller が偶数の場合、split-vote scenario が発生して可用性を損なう可能性があるため、3 や 5 のような奇数が一般的です。これは broker 数とは独立して決定されます。
</details>

8. Amazon EKS 上の Kafka broker 向けに EBS StorageClass を定義する際に使用される CSI provisioner の名前は何ですか？
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>解答を表示</summary>

**解答: B) `ebs.csi.aws.com`**

**解説:**
Amazon EBS CSI driver は provisioner 名 `ebs.csi.aws.com` を使用します。`kubernetes.io/aws-ebs` は deprecated となった in-tree provisioner です。`KafkaNodePool.spec.storage` 配下の `persistent-claim` volume は、この provisioner によって backed された StorageClass を参照し、EBS gp3 volume を動的に provision します。
</details>

9. broker Pod を AZ 全体に均等に分散するために `KafkaNodePool.spec.template.pod` に追加する field はどれですか？
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>解答を表示</summary>

**解答: B) `topologySpreadConstraints`**

**解説:**
`topologySpreadConstraints` は、`topologyKey`（たとえば `topology.kubernetes.io/zone`）に基づいて Pod を均等に分散する scheduling constraint です。Kafka broker を AZ 全体に分散することで、単一 AZ の障害が cluster 全体の可用性を停止させないようにします。`whenUnsatisfiable: DoNotSchedule` を設定すると、この制約に違反する scheduling をブロックし、制約を厳密に適用します。
</details>

10. 外部 client が cluster 外部から Kafka broker に到達する必要がある場合、`Kafka.spec.kafka.listeners` に追加できる listener type はどれですか？
    - A) `internal` と `clusterip`
    - B) `loadbalancer` または `nodeport`
    - C) `ingress` のみ
    - D) 外部公開はサポートされていない

<details>

<summary>解答を表示</summary>

**解答: B) `loadbalancer` または `nodeport`**

**解説:**
Strimzi listener は `internal`、`route`、`ingress`、`loadbalancer`、`nodeport` type をサポートします。EKS では、外部 access は通常 `loadbalancer`（bootstrap/broker ごとに AWS NLB を自動 provision）または `nodeport`（worker node port と外部 load balancer）を通じて提供されます。`loadbalancer` type は、internal と internet-facing scheme など、AWS Load Balancer Controller の NLB 設定を制御する annotation によって調整できます。
</details>

## 短答問題

11. `KafkaTopic` と `KafkaUser` custom resource を実際の Kafka resource と同期する役割を持つ、Strimzi の 2 つの内部 component の名前を答えてください。

<details>

<summary>解答を表示</summary>

**解答: Topic Operator, User Operator**

**解説:**
Topic Operator は `KafkaTopic` custom resource を実際の Kafka topic に一方向で同期します（CR が source of truth です）。一方、User Operator は `KafkaUser` custom resource に基づいて SCRAM-SHA-512 または TLS authentication credential と ACL を管理します。どちらも Entity Operator の一部として、Kafka cluster ごとに単一の Pod にまとめられています。
</details>

12. Cluster Operator が複数の namespace を監視するように設定する environment variable は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `STRIMZI_NAMESPACE`**

**解説:**
Cluster Operator Deployment に `STRIMZI_NAMESPACE` を設定すると、監視する namespace scope を制御できます。namespace のカンマ区切りリストを指定するか、`*` を指定して監視 scope を cluster 全体に拡張できます。
</details>

13. I/O を分散するために broker ごとに複数の EBS volume をアタッチできる、`KafkaNodePool.spec.storage` の storage type は何ですか？

<details>

<summary>解答を表示</summary>

**解答: JBOD (type: jbod)**

**解説:**
JBOD (Just a Bunch Of Disks) storage により、単一の broker が複数の `persistent-claim` volume を使用できます。各 volume は異なる `id` で識別されます。これにより、単一の EBS volume の throughput ceiling に制限されるのではなく、複数の volume に I/O を分散できます。
</details>

14. broker/controller が健全な quorum を形成し、listener が有効であることを示す `Kafka` resource の status condition は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `Ready: True`**

**解説:**
`kubectl get kafka -n kafka` で `Kafka` resource の status を確認したとき、`Ready` condition が `True` に設定されていれば、すべての cluster component（broker、controller、listener、Entity Operator）が正しく機能していることを意味します。
</details>

15. Debezium などの source/sink connector を実行するための個別 worker cluster を定義する Strimzi CRD の名前は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `KafkaConnect`**

**解説:**
`KafkaConnect` は Kafka Connect worker cluster を定義する CRD です。個々の connector instance は `KafkaConnector` custom resource を通じて宣言的に管理され、`KafkaConnect` cluster 上にデプロイされます。
</details>

## ハンズオン問題

16. Helm を使用して Strimzi Cluster Operator を `kafka` namespace にインストールする完全なコマンド列を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
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

**解説:**
`helm repo add` は Strimzi repository を登録し、`helm repo update` は最新の chart metadata を取得します。`helm install` に `--create-namespace` を追加すると、`kafka` namespace がまだ存在しない場合に自動的に作成されます。インストール後は、`kubectl get pods -n kafka` を使用して Cluster Operator Pod が `Running` であることを確認し、`kubectl get crd | grep strimzi` を使用して `Kafka` や `KafkaNodePool` などの CRD が登録されていることを確認します。
</details>

17. 3 つの broker-only node で構成され、それぞれが 100Gi の gp3-based `persistent-claim` volume を使用する `KafkaNodePool` を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
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

**解説:**
`strimzi.io/cluster` label は、この node pool が属する `Kafka` resource の名前と一致している必要があります。`roles: [broker]` は broker-only node を指定し、`storage.type: jbod` 配下の `persistent-claim` volume は EBS-backed の 100Gi persistent volume を provision します。`class` は `ebs.csi.aws.com` provisioner によって backed された StorageClass を参照します。
</details>

18. 12 partition と 3 replica を持つ `orders` という名前の `KafkaTopic` を作成し、その後 console producer と consumer でテストするコマンドを書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
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

**解説:**
`strimzi.io/cluster` label は、この `KafkaTopic` がどの `Kafka` cluster に属するかを Topic Operator に伝えます。apply 後、`kubectl get kafkatopic -n kafka` で topic が実際に作成されたことを確認します。producer/consumer test は、bootstrap Service（`my-cluster-kafka-bootstrap:9092`）に接続する使い捨て Pod として Strimzi の Kafka image を実行します。
</details>

19. SCRAM-SHA-512 authentication を使用し、`orders` topic に対して Read、Write、Describe のみが許可された `KafkaUser` を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
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

**解説:**
`authentication.type: scram-sha-512` は、SCRAM credential を生成して Secret に保存するよう User Operator に指示します。`authorization.type: simple` は Kafka built-in の ACL-based authorization を使用し、`acls` list はこの user を `orders` topic に対する `Read`、`Write`、`Describe` operation のみに制限します。これにより、CR level で least privilege を宣言的に実装します。
</details>

20. broker Pod を AZ 全体に均等に分散するために、`KafkaNodePool` の `spec.template.pod` に `topologySpreadConstraints` を追加してください。

<details>

<summary>解答を表示</summary>

**解答:**
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

**解説:**
`topologyKey: topology.kubernetes.io/zone` は、EKS worker node 上の AZ label に基づいて Pod を分散します。`maxSkew: 1` は AZ 間の Pod 数の差を最大 1 Pod まで許可し、`whenUnsatisfiable: DoNotSchedule` は制約を満たせない場合に scheduling を完全にブロックして、均等な分散を保証します。`labelSelector` は、skew の計算対象となる Pod の集合（同じ broker node pool）を決定します。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/02-strimzi-operator.md) | [次のクイズ: Kafka Operations](./03-kafka-operations-quiz.md)
