# パート 3: Kafka 運用

> **サポート対象バージョン**: Strimzi 0.45+, Kafka 3.9\
> **最終更新**: July 9, 2026

Strimzi Operator で Kafka クラスターをデプロイすると、運用作業はストレージ容量計画、broker のスケーリング、partition の再割り当て、およびダウンタイムなしのアップグレードへと移ります。このドキュメントでは、EKS で Strimzi が管理する Kafka クラスターを実行する際に行う主要な運用タスクを取り上げます。

## ストレージ設計

### EBS ボリュームタイプの選択: gp3 と io2

Kafka のログセグメントは主にシーケンシャルに書き込み・読み取りされますが、consumer lag の増加により古いセグメントに対するランダム読み取りが発生する場合があります。このアクセスパターンを考慮して EBS ボリュームタイプを選択してください。

| 項目 | gp3 | io2 |
|--------|-----|-----|
| **課金** | 容量ベース。IOPS/スループットは個別にプロビジョニング | IOPS ベース（単価がより高い） |
| **スループット** | 125MB/s がベースライン。個別プロビジョニングにより最大 1,000MB/s | ボリュームサイズと IOPS に応じて拡張 |
| **最大 IOPS** | 16,000 | 256,000 |
| **最適な用途** | 多くの Kafka ワークロード — スループットがボトルネックとなるパターン | 急増する consumer lag、大量の小さなランダム I/O を伴うレイテンシー重視のワークロード |
| **耐久性（年間障害率）** | 99.8–99.9% | 99.999% |

一般的なイベントストリーミングのワークロードでは、まず **gp3** を使用し、必要に応じてスループット/IOPS を個別にプロビジョニングしてください。これはより費用対効果の高いデフォルトです。ランダム I/O が支配的な場合（多数の consumer group が分散した offset から同時に読み取る場合）、または厳格な p99 レイテンシー SLA がある場合にのみ **io2** へ移行してください。

### JBOD を使用したマルチボリュームストレージ

Strimzi は、各 broker が 1 つの大きなボリュームではなく複数の独立したボリュームを使用する JBOD（Just a Bunch Of Disks）構成をサポートしています。このようにストレージを分割することで、ボリューム間でスループットを並列化でき、他のボリュームに手を加えることなく個々のボリュームを追加または交換できます。

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
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
  resources:
    requests:
      memory: 8Gi
      cpu: "2"
    limits:
      memory: 8Gi
      cpu: "4"
```

各 `volumes` エントリの `id` は broker 内のログディレクトリを識別し、partition はラウンドロビン方式でボリューム間に分散されます。`deleteClaim: false` は、broker のスケールダウンまたは再作成時に PVC が削除されないよう保護します。

> **注記**: Strimzi では、broker pod の起動時に Operator が `kafka-storage.sh format` と同等の処理を自動的に実行するため、ボリュームをフォーマットするためにこのスクリプトを自分で実行する必要はありません。

### ストレージサイジングのガイダンス

次の式を使用してディスク容量を決定します。

```
Required disk capacity = retention period × peak throughput (bytes/sec) × replication factor × (1 + headroom ratio)
```

たとえば、ピークスループットが 50MB/s、保持期間が 7 日（`604,800 seconds`）、replication factor が 3、headroom が 30% の場合:

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (cluster total)
```

これを 3 台の broker に分散すると、broker あたりおよそ 39TB になります。ディスク使用率が high-water mark を超えると Kafka broker の性能は急激に低下するため（log cleaner および segment rolling の動作に影響します）、headroom は重要です。また、`log.retention.bytes`/`log.retention.hours` による削除が遅れると、ディスクがフルになり broker が完全にオフラインになる可能性があります。常に少なくとも 20～30% の空き容量を確保してください。

## Broker と Controller のスケーリング

### Broker のスケールアウト

`KafkaNodePool` の `replicas` を増やすと、Strimzi は新しい broker pod を作成し、自動的にクラスターへ参加させます。

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# Confirm the new brokers joined the cluster
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

新しい broker は、既存の partition の leader または follower に自動的に選出されることはありません。実際に既存の topic partition を新しい broker に分散するには、別途 partition の再割り当て手順が必要です。

### Partition の再割り当て（`kafka-reassign-partitions.sh`）

```bash
# 1) Write the topics-to-move JSON file inside the broker pod
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c 'cat <<EOF > /tmp/topics-to-move.json
{
  "topics": [{"topic": "orders"}, {"topic": "payments"}],
  "version": 1
}
EOF'

# 2) Generate a reassignment plan across the full broker list, saved to a file inside the pod
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c '
  bin/kafka-reassign-partitions.sh \
    --bootstrap-server localhost:9092 \
    --topics-to-move-json-file /tmp/topics-to-move.json \
    --broker-list "0,1,2,3,4,5" \
    --generate > /tmp/generate-output.txt
  # The --generate output contains both the Current and Proposed assignment JSON,
  # so extract just the JSON under "Proposed partition reassignment configuration"
  awk "/^Proposed partition reassignment configuration/{flag=1; next} flag" /tmp/generate-output.txt > /tmp/reassignment.json
'

# 3) Apply the generated plan (reassignment.json)
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --execute

# 4) Check progress
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --verify
```

### スケールダウンが危険な理由

**Strimzi は、スケールダウン時に broker から partition を自動的にドレインしません。** `KafkaNodePool` の `replicas` を減らす前に、削除する broker 上に存在するすべての partition（leader と follower replica の両方）を、残りの broker に再割り当てする必要があります。この手順を省略すると、その broker にのみ存在した replica は単に消失します。最善の場合でも under-replicated partition が残り、最悪の場合はデータ損失が発生します。

安全なスケールダウン手順は次のとおりです。

1. 削除する broker を除外した broker リストに対して、`kafka-reassign-partitions.sh --generate` を実行します。
2. `--execute` でプランを適用し、`--verify` で完了を確認します（under-replicated partition がゼロであることを確認します）。
3. 再割り当てが完全に完了してから、`KafkaNodePool.spec.replicas` を減らして broker pod を削除します。

## Cruise Control による自動リバランシング

Cruise Control は、ディスク使用量、CPU、ネットワークスループットなどの broker レベルの負荷メトリクスを継続的に収集し、それらを使用して partition 再割り当てプランを自動的に生成・実行します。broker を追加または削除するたびに `kafka-reassign-partitions.sh` を手動で実行する代わりに、goal ベースの自動化にリバランシングを委任できます。

### Cruise Control の有効化

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # ... existing kafka config ...
  cruiseControl:
    config:
      # Goals: keep disk/CPU/network usage even across brokers
      goals: >-
        com.linkedin.kafka.cruisecontrol.analyzer.goals.RackAwareGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.DiskCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.CpuCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkInboundCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkOutboundCapacityGoal
```

### `KafkaRebalance` によるリバランスのトリガー

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaRebalance
metadata:
  name: my-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  mode: full
```

```bash
# Generate a rebalance proposal (not executed yet: PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# Approve the proposal to actually execute the rebalance
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# Watch progress
kubectl get kafkarebalance my-rebalance -n kafka -w
```

### リバランスモード

| モード | ユースケース |
|------|----------|
| `full`（デフォルト） | 設定された goal に基づき、クラスター内のすべての broker を対象とする完全なリバランスプランを生成します |
| `add-brokers` | 新たに追加された broker に partition を移動して負荷を満たすことに重点を置きます。完全なリバランスより高速で対象範囲が狭くなります |
| `remove-brokers` | 削除予定の broker から partition を移動することに重点を置きます。スケールダウン前の安全なドレイン手順として使用してください |

スケールアウトまたはスケールインの直後は、リバランスを `add-brokers` または `remove-brokers` に限定することで、移動する必要のない無関係な partition を `full` モードが移動することによるネットワークオーバーヘッドと時間コストを回避できます。

## ローリングアップグレード

### Spec 変更時の自動ローリング再起動

リソース requests/limits、config 値、ボリュームなど、`Kafka` または `KafkaNodePool` CR の spec を変更すると、Strimzi Operator はその変更を検出し、broker pod を**一度に 1 つずつ**再起動します。Operator は、すべての partition が `min.insync.replicas` を満たしている場合にのみ再起動を続行するよう各再起動を調整し、再起動によって partition の利用可能な replica 数が必要なしきい値を下回らないようにします。

### Kafka バージョンアップグレード — 2 フェーズパターン

KRaft モードには `inter.broker.protocol.version`/`log.message.format.version` はありません（これらは ZooKeeper 時代の設定です）。代わりに、`Kafka` CR の `spec.kafka.version`（ソフトウェアバージョン）と `spec.kafka.metadataVersion`（KRaft metadata log format バージョン）を同時に上げてはなりません。この場合も**2 つの別々のフェーズ**が必要です。`metadataVersion` は controller quorum が metadata を永続化するために使用する形式を制御するため、ロールアウト途中で古い node と新しい node が混在している間は古い形式のままにする必要があります。

**フェーズ 1 — ソフトウェアバージョンのみをアップグレードする**

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # Keep metadataVersion pinned to the old format
    metadataVersion: 3.8-IV0
```

これを適用すると、broker/controller バイナリが 3.9.0 にローリング置換される一方で、metadata format は 3.8-IV0 のままになります。これにより、両方が稼働する期間中、controller quorum の古い node と新しい node の互換性が維持されます。

**フェーズ 2 — すべての node が置換された後に metadataVersion を上げる**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

すべての broker/controller が 3.9.0 を実行していることを確認してから、`metadataVersion` を上げてください。この変更により、新しい metadata format を採用するための別の reconciliation がトリガーされます。順序を逆にして、ソフトウェアバージョンと `metadataVersion` を同時に上げると、古いバイナリをまだ実行している node は新しい metadata format を理解できず、controller quorum の通信エラーが発生します。

### Strimzi Operator バージョンのアップグレード

**Kafka バージョンを上げる前に、Strimzi Operator 自体をアップグレードしてください。** 各 Strimzi リリースは特定の範囲の Kafka バージョンをサポートしており、稼働中の Operator が認識しない Kafka バージョンに CR を変更すると、validation に失敗します。通常の順序は、Operator をアップグレード → reconciliation の完了を待つ → Kafka ソフトウェアバージョンをアップグレード（フェーズ 1）→ `metadataVersion` をアップグレード（フェーズ 2）です。

## 障害対応の基本

### PodDisruptionBudget と Broker Pod の退避

Strimzi は、すべての `KafkaNodePool` に対して `PodDisruptionBudget`（PDB）を自動的に作成します。デフォルトでは、一度に voluntary eviction の対象になれる broker pod は 1 つだけです。これには node drain、Cluster Autoscaler による node の置換などが含まれ、複数の broker が同時に停止して quorum または可用性が損なわれることを防ぎます。

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### ローリング再起動中の `acks=all` Producer

`acks=all` を使用すると、broker のローリング再起動中でも producer はデータ損失から保護されます。再起動する broker が partition の leader だった場合、再起動の直前に controller が in-sync replica（ISR）セットから新しい leader を選出します。producer は leader の変更を検出し、metadata を更新して新しい leader に対して再試行します。一時的なレイテンシーのスパイクが発生する可能性はありますが、`min.insync.replicas` が満たされている限り、commit 済みのデータが失われることはありません。`acks=1` 以下を使用する producer は、再起動時にまだ follower へ複製されていないメッセージを失うリスクがあります。

consumer 側では、ローリング再起動により consumer group のリバランスと一時的なスループット低下が発生する可能性がありますが、offset が通常どおり commit されていれば、再起動の完了後に consumer は中断した位置から再開します。

---

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[Topic クイズ](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)に挑戦してください。

次は、パート 4 で Kafka topic のメッセージ schema と互換性戦略を管理する Schema Registry を取り上げます。
