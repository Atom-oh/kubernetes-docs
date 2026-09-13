# Strimzi Operatorクイズ

> **最終更新**: September 12, 2026、Strimzi 1.2.0 / Kafka 4.3.1。

このクイズはStrimzi Operatorの基礎、インストール方法、主要CRD、KRaftノードの役割、EKSデプロイの考慮事項の理解を確認します。

## 選択問題

1. StrimziはどのようなCNCFプロジェクトですか？
   - A) サービスメッシュ
   - B) Kubernetes上でApache Kafkaを実行するOperator
   - C) コンテナランタイム
   - D) CI/CDパイプラインツール

<details>

<summary>解答を表示</summary>

**正解: B) Kubernetes上でApache Kafkaを実行するOperator**

**解説:**
Strimzi 1.2はカスタムリソースの期待状態を調整するCNCFインキュベーションプロジェクトです。現在のKafka Pod管理はStrimziPodSetを使います。Operatorがすべての運用方針や可用性保証を自動完成させるわけではありません。
</details>

2. StrimziなしでKafkaをStatefulSetとして直接運用する課題として、最も不正確なのはどれですか？
   - A) 順次ローリングアップグレードへの対応
   - B) TLS証明書の発行とローテーション
   - C) コンテナイメージをビルドできなくなる
   - D) パーティションリバランス時のデータ移動管理

<details>

<summary>解答を表示</summary>

**正解: C) コンテナイメージをビルドできなくなる**

**解説:**
直接運用は可能ですが、アップグレード、証明書、ストレージ、再割り当て手順の実装が必要です。Strimziは反復作業を調整しますが、データ復旧と可用性方針は引き続き検証が必要です。
</details>

3. Cluster Operatorインストール前にStrimzi Helmリポジトリを追加するコマンドはどれですか？
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>解答を表示</summary>

**正解: A) `helm repo add strimzi https://strimzi.io/charts/`**

**解説:**
公式チャートリポジトリを追加し、新規インストールでは1.2.0に固定します。既存ベータAPI/CRDは先に公式移行手順が必要です。新名前空間でもクラスター範囲のCRD競合は避けられません。
</details>

4. Strimzi Cluster Operatorがデフォルトで監視する名前空間範囲はどれですか？
   - A) クラスター内の全名前空間
   - B) 全`kube-system`名前空間
   - C) デプロイ先の名前空間のみ
   - D) `default`名前空間のみ

<details>

<summary>解答を表示</summary>

**正解: C) デプロイ先の名前空間のみ**

**解説:**
デフォルトチャートはリリースの名前空間を監視します。チャート1.2は追加watchNamespacesとともにその名前空間を含めて重複排除し、RoleBindingを作成します。環境変数だけの変更ではRBAC不足が残る場合があります。
</details>

5. 現在のStrimzi 1.2 KRaftデプロイで未対応のブロックはどれですか？
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>解答を表示</summary>

**正解: B) `Kafka.spec.zookeeper`**

**解説:**
現在のStrimzi 1.2はKRaftを使い、ZooKeeperブロックをサポートしません。KafkaNodePoolはcontrollerとbrokerロールを定義し、従来の有効化アノテーションは不要です。
</details>

6. `KafkaNodePool.spec.roles`の有効なエントリではない値はどれですか？
   - A) `controller`
   - B) `broker`
   - C) `controller`と`broker`を組み合わせた二重ロール
   - D) `zookeeper`

<details>

<summary>解答を表示</summary>

**正解: D) `zookeeper`**

**解説:**
実際の列挙値はcontrollerとbrokerです。[controller, broker]として両方を列挙できますが、dual-roleは独立した文字列値ではありません。
</details>

7. コントローラー投票者を3つ選ぶ理由は何ですか？
   - A) 常にブローカー数と一致する必要がある
   - B) 投票者1つの障害後も2つの過半数が残る
   - C) Kafkaクライアントライブラリが最低3コントローラーを要求する
   - D) EBSボリューム制限が要求する

<details>

<summary>解答を表示</summary>

**正解: B) 投票者1つの障害後も2つの過半数が残る**

**解説:**
3投票者は1障害後も2つの過半数を維持します。偶数のグループにも過半数はありますが、同じ耐障害性なら奇数が効率的です。コントローラー数はブローカー数から独立し、接続性や他条件にも依存します。
</details>

8. 標準Amazon EBS CSIドライバー経路のStorageClassプロビジョナーはどれですか？
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>解答を表示</summary>

**正解: B) `ebs.csi.aws.com`**

**解説:**
標準EBS CSIはebs.csi.aws.com、EKS Auto Modeはebs.csi.eks.amazonaws.comを使います。StorageClassプロビジョナーを変更しても既存PVCは移行されません。
</details>

9. ブローカーPodをAZ間に均等分散するため、`KafkaNodePool.spec.template.pod`に追加するフィールドはどれですか？
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>解答を表示</summary>

**正解: B) `topologySpreadConstraints`**

**解説:**
セレクターは実Podラベルと一致する必要があります。適格な3 AZを要求するにはminDomains: 3などの条件も必要で、maxSkew: 1は3 AZを作成しません。スケジューリングとKafkaレプリカのラック配置を別々に確認します。
</details>

10. 外部クライアントがクラスター外からKafkaブローカーに接続する場合、`Kafka.spec.kafka.listeners`に追加できるリスナータイプはどれですか？
    - A) `internal`と`clusterip`
    - B) `loadbalancer`または`nodeport`
    - C) `ingress`のみ
    - D) 外部公開は未対応

<details>

<summary>解答を表示</summary>

**正解: B) `loadbalancer`または`nodeport`**

**解説:**
StrimziはLoadBalancer ServiceまたはNodePortを作成します。クラウドロードバランサーはコントローラー/クラスに依存します。本文はAWS Load Balancer Controllerクラスを固定し、bootstrapと全ブローカーServiceに内部/IPターゲット設定を適用します。
</details>

## 短答問題

11. `KafkaTopic`と`KafkaUser`カスタムリソースを実Kafkaリソースと同期する2つのStrimzi内部コンポーネントを挙げてください。

<details>

<summary>解答を表示</summary>

**正解: Topic Operator、User Operator**

**解説:**
TopicとUser Operatorは有効なEntity Operator内で動作でき、単独インストールもあります。トピック/ユーザーCRには適切な名前空間とクラスターラベルが必要です。
</details>

12. Cluster Operatorに複数名前空間を監視させる環境変数は何ですか？

<details>

<summary>解答を表示</summary>

**正解: `STRIMZI_NAMESPACE`**

**解説:**
変数はSTRIMZI_NAMESPACEです。Helm管理ではkubectl set envで差異を作らず、watchNamespaces/watchAnyNamespaceのvaluesと対応RBACを使います。
</details>

13. `KafkaNodePool.spec.storage`で、ブローカーごとに複数EBSボリュームを付けてI/Oを分散できるストレージタイプは何ですか？

<details>

<summary>解答を表示</summary>

**正解: JBOD（type: jbod）**

**解説:**
JBODは複数ボリュームIDをサポートします。自動データ均等化を保証せず、インスタンスのEBS/ネットワーク制限を取り除きません。kraftMetadata: sharedを選べるボリュームは最大1つです。
</details>

14. Operatorの最後に成功したKafka調整を示す条件は何ですか？

<details>

<summary>解答を表示</summary>

**正解: `Ready: True`**

**解説:**
Ready=TrueはOperatorの最後の調整観測です。observedGenerationと現在のgenerationを比較し、Pod準備状態、クォーラム、実際の認証付きクライアント接続を確認します。
</details>

15. Debeziumなどのソース/シンクコネクターを実行する独立ワーカークラスターを定義するStrimzi CRDは何ですか？

<details>

<summary>解答を表示</summary>

**正解: `KafkaConnect`**

**解説:**
KafkaConnectはConnectワーカー、KafkaConnectorは個々のコネクターを表します。コネクターリソース管理とワーカーの認証/認可を別々に設定します。
</details>

## 実践問題

16. 本文のoperator-values.yamlを使い、新しいkafka名前空間にStrimzi 1.2.0をインストールしてください。

<details>

<summary>解答を表示</summary>

**解答:**
```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.2.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io
```

**解説:**
コマンドは新規インストール用です。チャートを固定し、Operator可用性/CRDを確認します。既存インストールには、先にv1変換とCRD所有権/更新レビューが必要です。
</details>

17. 本文の名前空間、ストレージ、3 AZ制約を使って、3ブローカーのKafkaNodePoolを書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: broker
  namespace: kafka
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
      kraftMetadata: shared
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      memory: 4Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: broker
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 3
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            strimzi.io/cluster: my-cluster
            docs.example.com/kafka-role: broker
```

**解説:**
本文の標準gp3-kafka StorageClassと3 AZ要件を使います。名前空間/クラスターラベルを合わせ、deleteClaim: falseでPVCを保持します。Auto Modeは別StorageClassを使い、プールは物理ノード分離を保証しません。
</details>

18. 認証付きkafka-client Podが準備済みとして、ordersを作成し、TLS/SCRAMのプロデューサー/コンシューマーコマンドでテストしてください。

<details>

<summary>解答を表示</summary>

**解答:**
```yaml
apiVersion: kafka.strimzi.io/v1
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

```bash
kubectl apply -f orders-topic.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
printf 'strimzi-auth-smoke-test\n' |
  kubectl -n kafka exec -i kafka-client -- \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
    --producer.config /client/client.properties --topic orders
kubectl -n kafka exec kafka-client -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
  --consumer.config /client/client.properties --group order-processor \
  --topic orders --from-beginning --max-messages 1 --timeout-ms 10000
```

**解説:**
本文のKafkaUser、CA Secret、認証付きkafka-client Podが存在する必要があります。平文エンドポイントでなくTLS/SCRAMクライアントプロパティを使います。既存トピックの最初のレコードが実際に直前に送ったものか確認します。
</details>

19. ordersの生成/消費、order-processorグループ、冪等プロデューサー操作用のSCRAMユーザーを定義してください。

<details>

<summary>解答を表示</summary>

**解答:**
```yaml
apiVersion: kafka.strimzi.io/v1
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
          patternType: literal
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: order-processor
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

**解説:**
リスナー認証とクラスターオーソライザーも有効にします。トピックACLに加え、order-processorグループのReadと冪等プロデューサー機能を付与します。実サービスでは別々のプロデューサー/コンシューマーIDを検討します。
</details>

20. ブローカーKafkaNodePoolのspec内に、実ラベルと一致し、適格な3 AZを要求するテンプレート抜粋を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```yaml
# Merge under KafkaNodePool.spec
template:
  pod:
    metadata:
      labels:
        docs.example.com/kafka-role: broker
    topologySpreadConstraints:
    - maxSkew: 1
      minDomains: 3
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      nodeAffinityPolicy: Honor
      nodeTaintsPolicy: Honor
      labelSelector:
        matchLabels:
          strimzi.io/cluster: my-cluster
          docs.example.com/kafka-role: broker
```

**解説:**
抜粋をブローカーKafkaNodePoolのspec下へマージします。メタデータラベルをセレクターに一致させます。minDomains=3では適格な3 AZがなければPodがPendingのままになり得ます。厳格な制約はAZ喪失後の代替Podを阻み得ます。Kafkaのラック認識は別です。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/02-strimzi-operator.md) | [次のクイズ: Kafkaの運用](./03-kafka-operations-quiz.md)
