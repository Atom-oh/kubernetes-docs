# Kafka Operations クイズ

このクイズでは、EKS 上の Strimzi 管理 Kafka cluster における storage design、broker scaling、Cruise Control rebalancing、rolling upgrades、failure handling の理解を確認します。

## 多肢選択問題

1. 多数の consumer group が散在した offset を読み取ることで heavy random I/O が発生し、厳格な p99 latency SLA がある workload には、どの EBS volume type がより適していますか？
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>解答を表示</summary>

**解答: C) io2**

**解説:**
io2 は IOPS に基づいて課金され、最大 256,000 IOPS と 99.999% の耐久性を提供するため、小さな random I/O が中心の latency-sensitive workload に適しています。ほとんどの event-streaming workload は throughput-bound であるため、gp3 がより cost-effective な出発点です。io2 への切り替えは、spiky consumer lag や厳格な p99 SLA など、random I/O が bottleneck になる場合にのみ価値があります。
</details>

2. `KafkaNodePool` で broker が複数の独立した volume を使用するように設定する storage type はどれですか？
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>解答を表示</summary>

**解答: B) `type: jbod`**

**解説:**
`storage.type: jbod` (Just a Bunch Of Disks) を使用すると、broker ごとに複数の独立した volume を `volumes` list で定義できます。各 volume は `id` で識別され、partition はそれらに round-robin で分散されます。`persistent-claim` は、JBOD configuration 内の個々の volume entry に使用される type です。
</details>

3. retention period が 7 日、peak throughput が 100MB/s、replication factor が 3、headroom が 30% の場合、cluster 全体に必要な disk capacity を求める formula はどれですか？
   - A) 100MB/s × 7 日 (秒) × 3
   - B) 100MB/s × 7 日 (秒) × 3 × 1.3
   - C) 100MB/s × 7 日 (秒) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>解答を表示</summary>

**解答: B) 100MB/s × 7 日 (秒) × 3 × 1.3**

**解説:**
sizing formula は `retention period × peak throughput × replication factor × (1 + headroom ratio)` です。retention を秒に変換し、peak throughput を掛けて raw data volume を求め、replica を考慮するために replication factor を掛け、最後に safety margin を残すため headroom factor（30% headroom = 1.3x）を掛けます。
</details>

4. Strimzi 管理 Kafka cluster で storage volume を format するために、operator が手動で実行しなければならない script はどれですか？
   - A) `kafka-storage.sh format` をすべての broker で手動実行する必要がある
   - B) `kafka-configs.sh` を使用して format settings を適用する必要がある
   - C) なし — Strimzi Operator は broker Pod の起動時にこれを自動的に処理する
   - D) `kafka-reassign-partitions.sh --format` を使用する必要がある

<details>

<summary>解答を表示</summary>

**解答: C) なし — Strimzi Operator は broker Pod が起動するとこれを自動的に処理します**

**解説:**
Strimzi では、broker Pod が起動すると Operator が volume formatting を自動的に処理します。これは、通常の open-source Kafka を手動で実行する場合に自分で `kafka-storage.sh format` を実行する必要があるのと比べて便利です。
</details>

5. `KafkaNodePool` の `replicas` を増やして broker を scale out すると、新しい broker では何が自動的に起こりますか？
   - A) 既存の partition はすぐに新しい broker へ再分散される
   - B) 新しい broker は cluster に参加するが、既存の topic partition は自動的には reassignment されない
   - C) 新しい broker はすべての partition の leader に自動的になる
   - D) 新しい broker は controller としてのみ機能する

<details>

<summary>解答を表示</summary>

**解答: B) 新しい broker は cluster に参加しますが、既存の topic partition は自動的には reassignment されません**

**解説:**
`replicas` を増やすと、Strimzi は新しい broker Pod を作成し cluster に参加させますが、既存の topic partition をそれらへ移動することは自動では行われません。新しい broker の capacity を実際に活用するには、`kafka-reassign-partitions.sh` による手動 reassignment、または `add-brokers` mode の Cruise Control rebalance が必要です。
</details>

6. broker を scale down する前に何を行う必要がありますか？
   - A) 何もしない — Strimzi が自動的に drain する
   - B) 削除される broker 上の partition は、先に残りの broker へ reassignment する必要がある
   - C) cluster を restart する必要がある
   - D) すべての topic を削除する必要がある

<details>

<summary>解答を表示</summary>

**解答: B) 削除される broker 上の partition は、先に残りの broker へ reassignment する必要があります**

**解説:**
Strimzi は broker を scale down するときに partition を自動的に drain しません。`replicas` を減らす前に、削除される broker 上のすべての replica を残りの broker に reassignment する必要があります。そうしないと、under-replicated partition や完全な data loss のリスクがあります。
</details>

7. Cruise Control の主な役割は何ですか？
   - A) topic の作成と削除を自動化する
   - B) broker load metrics を収集し、goal-based partition reassignment plan を自動的に生成/実行する
   - C) consumer group offset commit を管理する
   - D) TLS certificate を自動的に更新する

<details>

<summary>解答を表示</summary>

**解答: B) broker load metric を収集し、goal-based partition reassignment plan を自動的に生成/実行します**

**解説:**
Cruise Control は broker ごとの load metric（disk usage、CPU、network throughput）を継続的に収集し、設定された goal を使用して partition reassignment plan を自動的に生成して実行します。これにより、routine rebalancing のために `kafka-reassign-partitions.sh` を手動で実行する必要がなくなります。
</details>

8. `KafkaRebalance` resource の `mode` field で、新しく追加された broker に partition を移動して load を埋めることに重点を置く mode はどれですか？
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>解答を表示</summary>

**解答: B) `add-brokers`**

**解説:**
`add-brokers` mode は、新しく追加された broker に partition を移動することに重点を置くため、関連のない broker を含むすべての broker 間で reassignment する `full` mode よりも高速で範囲が限定されています。逆に、`remove-brokers` mode は、削除予定の broker から partition を移動することに重点を置き、scale down 前の有用な drain step になります。
</details>

9. KRaft-mode cluster の Kafka version を 3.8 から 3.9 に upgrade する正しい手順はどれですか？
   - A) `version` と `metadataVersion` を一度に 3.9 に変更する
   - B) まず新しい broker/controller software を roll out するために `version` のみを 3.9 に変更し、すべての node が置き換えられた後でのみ `metadataVersion` を 3.9-IV0 に上げる
   - C) まず `metadataVersion` を上げてから、`version` を変更する
   - D) cluster 全体を停止し、すべての値を一度に変更する

<details>

<summary>解答を表示</summary>

**解答: B) まず新しい broker/controller software を roll out するために `version` のみを 3.9 に変更し、すべての node が置き換えられた後でのみ `metadataVersion` を 3.9-IV0 に上げます**

**解説:**
KRaft mode には `inter.broker.protocol.version`/`log.message.format.version` はありません（これらは ZooKeeper 時代の設定です）。代わりに、`spec.kafka.version`（software version）と `spec.kafka.metadataVersion`（controller quorum が metadata を永続化するために使用する format）は 2 つの phase で上げる必要があります。Phase 1 では、`metadataVersion` を古い format に固定したまま software version のみを上げます。これにより、rollout 中に古い node と新しい node の両方が動作している間も、controller quorum 内で相互に compatible な状態を維持できます。Phase 2 では、すべての node が置き換えられたことを確認した後にのみ `metadataVersion` を上げます。この順序を逆にすると、古い binary のままの node が新しい metadata format を理解できず、controller quorum communication error が発生します。
</details>

10. Strimzi が `KafkaNodePool` ごとに自動的に作成し、voluntary eviction を制限する Kubernetes resource はどれですか？
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>解答を表示</summary>

**解答: C) PodDisruptionBudget**

**解説:**
Strimzi はすべての `KafkaNodePool` に対して `PodDisruptionBudget` (PDB) を自動的に作成します。デフォルトでは、一度に 1 つの broker Pod だけが voluntary eviction（node drain、autoscaler node replacement など）を受けられるようにし、複数の broker が同時に停止して availability が損なわれることを防ぎます。
</details>

## 短答問題

11. rolling restart 中に partition の available replica count が必要最小数を下回らないよう、Strimzi が尊重する Kafka config value は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `min.insync.replicas`**

**解説:**
CR spec の変更によって rolling restart が triggered されると、Strimzi Operator は各 partition の `min.insync.replicas` requirement が引き続き満たされていることを確認しながら、broker を 1 つずつ restart します。これにより、restart によって partition の available in-sync replica count が必要な threshold を下回ることを防ぎます。下回ると write failure や availability loss が発生する可能性があります。
</details>

12. Kafka cluster 自体の version を upgrade する前に、どの component を upgrade すべきですか？

<details>

<summary>解答を表示</summary>

**解答: Strimzi Operator**

**解説:**
各 Strimzi release は特定範囲の Kafka version を support しており、実行中の Operator が認識しない Kafka version に CR を変更すると validation に失敗します。そのため、Kafka software version を上げる前に、Strimzi Operator 自体を最新 version に upgrade する必要があります。
</details>

13. partition reassignment plan を実際に実行する前に、指定した broker list に対して plan を生成するために使用する `kafka-reassign-partitions.sh` の option は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `--generate`**

**解説:**
`--generate` option は、実際には実行せずに、`--topics-to-move-json-file` と `--broker-list` に基づいて reassignment plan（JSON）を生成します。plan を review した後、`--execute` で適用し、`--verify` で進捗と完了を確認します。
</details>

14. `acks=all` で設定された producer が data を失わずに broker rolling restart を乗り切れる理由を、1 文で説明してください。

<details>

<summary>解答を表示</summary>

**解答: restart される broker が partition leader だった場合、controller は restart が進む前に in-sync replica (ISR) set から新しい leader を選出し、`min.insync.replicas` が満たされている限り committed data は保持されます。**

**解説:**
`acks=all` producer は、message を committed と見なす前に、`min.insync.replicas` を満たすのに十分な replica に message が書き込まれるのを待ちます。broker restart の前に leader が変更されると、producer はその変更を検出し、metadata を更新し、新しい leader に対して retry します。短い latency spike は発生する可能性がありますが、すでに committed された data は失われません。`acks=1` 以下を使用する producer にはそのような保証はなく、in-flight message を失うリスクがあります。
</details>

## ハンズオン問題

15. 3 つの volume を持つ JBOD storage を使用し、それぞれ gp3 上で 300Gi の、`broker` という名前の `KafkaNodePool` YAML を書いてください。

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
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 2
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
```

**解説:**
`storage.type: jbod` を設定し、`volumes` list に 3 つの `persistent-claim` volume を定義し、それぞれに一意の `id`（0、1、2）を付けることで、broker に 3 つの独立した volume が与えられます。`deleteClaim: false` は、broker が recreated されたり scaled down されたりしたときに PVC が削除されないよう保護し、その data を safeguard します。
</details>

16. `my-cluster` という名前の cluster に対して `full` mode の `KafkaRebalance` resource を作成し、生成された rebalance proposal を approve する command を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
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
# Check proposal generation status (PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# Approve the proposal to execute it
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# Watch progress
kubectl get kafkarebalance my-rebalance -n kafka -w
```

**解説:**
`KafkaRebalance` CR を作成すると、Cruise Control が rebalance proposal を自動的に生成し、`ProposalReady` state で待機します。partition move を実際に実行するには、`strimzi.io/rebalance=approve` annotation が必要です。`mode: full` は、cluster 内のすべての broker を対象とする goal-based plan を生成します。
</details>

17. broker を 3 台（ID 0,1,2）から 6 台（ID 0-5）に scale した後、新しい broker を含む完全な broker list 全体に `orders` topic の partition を reassignment するための 3-step command（generate → execute → verify）を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```bash
# 1) Define the topic to move
cat <<EOF > topics-to-move.json
{
  "topics": [{"topic": "orders"}],
  "version": 1
}
EOF

# 2) Generate the plan
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "0,1,2,3,4,5" \
  --generate

# 3) Execute the plan (using the generated reassignment.json)
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# 4) Verify completion
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

**解説:**
`--generate` は、指定された `--broker-list`（ここでは新しい broker を含む 0-5）を対象とする partition move plan を生成します。`--execute` は実際の reassignment を開始し、`--verify` は reassignment が完了し under-replicated partition が残っていないことを確認します。この process の後になって初めて、新しく追加された broker が実際に partition leader/follower role を保持します。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/03-kafka-operations.md) | [次のクイズ: Schema Registry](./04-schema-registry-quiz.md)
