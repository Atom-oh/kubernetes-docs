# Kafka運用クイズ

> **最終更新**: September 12, 2026、Strimzi 1.2.0 / Kafka 4.3.1。

このクイズはEKS上のStrimzi管理Kafkaクラスターのストレージ設計、ブローカースケーリング、Cruise Controlリバランス、ローリングアップグレード、障害処理の理解を確認します。

## 選択問題

1. AWSが低レイテンシー、高IOPS、高耐久性向けに設計したSSDはどれですか？
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>解答を表示</summary>

**正解: C) io2**

**解説:**
io2 Block Expressは低レイテンシー、高IOPS、耐久性を目指します。最大256,000 IOPSにはNitroなど適切な条件が必要です。設計耐久性99.999%とAFR 0.001%を区別します。容量とIOPSが費用に寄与するため、測定、要件、料金で選びます。
</details>

2. `KafkaNodePool`でブローカーに複数の独立ボリュームを使用させるストレージタイプはどれですか？
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>解答を表示</summary>

**正解: B) `type: jbod`**

**解説:**
JBODは独立したボリュームIDを提供します。Kafka 4.3.1は新ログで通常パーティションログの少ないディレクトリを優先し、ラウンドロビンやバイト均等配置は保証されません。既存データ移動は別です。
</details>

3. 持続100MB/sの保持ログ、7日保持、RF=3の場合、総容量の30%を空ける式はどれですか？
   - A) 100MB/s × 7日（秒換算） × 3
   - B) 100MB/s × 7日（秒換算） × 3 ÷ 0.70
   - C) 100MB/s × 7日（秒換算） ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>解答を表示</summary>

**正解: B) 100MB/s × 7日（秒換算） × 3 ÷ 0.70**

**解説:**
データサイズに30%加えても総容量の空きは約23.08%です。30%空けるには複製済みデータを0.70で割ります。持続した保持/圧縮ログバイト数、実保持期間、別の運用オーバーヘッドを使います。
</details>

4. Strimzi管理Kafkaクラスターのストレージをフォーマットするため、運用者が手動実行すべきスクリプトは何ですか？
   - A) 全ブローカーで`kafka-storage.sh format`を手動実行する必要がある
   - B) `kafka-configs.sh`でフォーマット設定を適用する必要がある
   - C) なし。ブローカーPod起動時にStrimzi Operatorが自動処理する
   - D) `kafka-reassign-partitions.sh --format`を使う必要がある

<details>

<summary>解答を表示</summary>

**正解: C) なし。ブローカーPod起動時にStrimzi Operatorが自動処理する**

**解説:**
Strimzi/起動スクリプトが新ストレージメタデータの必要初期化を管理します。起動ごとに既存データが消去されるわけではありません。Operator管理ボリュームを任意に手動フォーマットしないでください。
</details>

5. 一致するautoRebalanceモードがない場合、ブローカープールのreplicasを増やすとどうなりますか？
   - A) 既存パーティションが即座に新ブローカーへ再分散される
   - B) 新ブローカーは参加するが、既存トピックパーティションは自動再割り当てされない
   - C) 新ブローカーが全パーティションのリーダーになる
   - D) 新ブローカーはコントローラーとしてのみ動作する

<details>

<summary>解答を表示</summary>

**正解: B) 新ブローカーは参加するが、既存トピックパーティションは自動再割り当てされない**

**解説:**
一致するautoRebalanceモードがない場合の説明です。Strimzi 1.2はadd-brokers自動化を設定すれば、既存プールのreplicas増加後に自動リバランスできます。プール作成/削除は別イベントです。
</details>

6. ブローカー削除前に満たすべきデータ状態の要件は何ですか？
   - A) なし。Strimziが自動で退避する
   - B) 削除ブローカーのパーティションを先に残るブローカーへ再割り当てする
   - C) クラスターを再起動する
   - D) 全トピックを削除する

<details>

<summary>解答を表示</summary>

**正解: B) 削除ブローカーのパーティションを先に残るブローカーへ再割り当てする**

**解説:**
削除前に全レプリカを安全に退避する必要があります。手動手順には内部トピックも含めます。設定済みremove-brokers autoRebalanceは自動で退避を調整できます。空でないブローカーのチェックを維持し、削除IDを確認します。
</details>

7. Cruise Controlの主な役割は何ですか？
   - A) トピック作成/削除を自動化
   - B) ブローカー負荷メトリクスを収集し、ゴールに基づくパーティション再割り当て計画を自動生成/実行
   - C) コンシューマーグループのオフセットコミットを管理
   - D) TLS証明書を自動更新

<details>

<summary>解答を表示</summary>

**正解: B) ブローカー負荷メトリクスを収集し、ゴールに基づくパーティション再割り当て計画を自動生成/実行**

**解説:**
Cruise Controlは負荷/ゴールから提案を計算し、承認/自動化方針に従って実行します。提案生成と移動は別です。メトリクス不足やハードゴール失敗を安易に迂回しないでください。
</details>

8. `KafkaRebalance`の`mode`で、新規ブローカーへパーティションを移し負荷を配分するモードはどれですか？
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>解答を表示</summary>

**正解: B) `add-brokers`**

**解説:**
add-brokersは指定新ブローカーを対象とし、実IDが必要です。ゴール、データ量、ラック制約が時間/影響を決め、常にfullより速いわけではありません。remove-brokersは削除前にブローカーを退避します。
</details>

9. 検証期間に旧メタデータ形式を保持し、Kafka 4.2.1を4.3.1へ更新するパターンはどれですか？
   - A) versionとmetadataVersionを即座に両方上げる
   - B) versionを4.3.1に上げ、metadataVersion 4.2-IV1を維持し、検証後に4.3-IV0へ変更する
   - C) バイナリ互換性確認前にmetadataVersionを上げる
   - D) 全データを削除して再起動する

<details>

<summary>解答を表示</summary>

**正解: B) versionを4.3.1に上げ、metadataVersion 4.2-IV1を維持し、検証後に4.3-IV0へ変更する**

**解説:**
検証用に旧metadataVersionを明示維持する運用パターンです。省略するとStrimziはバイナリ更新後にメタデータを更新する場合があります。Operatorは現/対象Kafkaをサポートする必要があり、後の形式変更はダウングレードを妨げることがあります。
</details>

10. Strimzi Kafkaクラスターの自発的退避を制限するKubernetesリソースはどれですか？
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>解答を表示</summary>

**正解: C) PodDisruptionBudget**

**解説:**
Strimzi 1.2は通常クラスターごとにKafka PDBを1つ作り、全プールのKafka Podを対象とします。自発的退避を制約し、ノード/AZ障害や強制削除は制約しません。
</details>

## 短答問題

11. Kafkaのローリング可用性確認で考慮する最小ISR設定は何ですか？

<details>

<summary>解答を表示</summary>

**正解: `min.insync.replicas`**

**解説:**
min.insync.replicasは重要な可用性入力で、あらゆるローリング処理中の無条件保証ではありません。実ISR、コントローラークォーラム、ストレージ/ネットワーク、クライアントタイムアウト/再試行を確認します。
</details>

12. アップグレード前に、現Kafkaと対象Kafkaの両方をサポート表に含む必要があるコンポーネントは何ですか？

<details>

<summary>解答を表示</summary>

**正解: Strimzi Operator**

**解説:**
現/対象Kafka両方をサポートするStrimzi版を確認します。すでに対応するならOperator更新は必須ではありません。最新Operatorが現Kafkaのサポートを外す場合、中間版とAPI/CRD移行を計画します。
</details>

13. パーティション再割り当てを実行する前に、指定ブローカー一覧への計画を生成する`kafka-reassign-partitions.sh`オプションは何ですか？

<details>

<summary>解答を表示</summary>

**正解: `--generate`**

**解説:**
--generateは移動を実行せず、現在と提案の割り当てを表示します。Proposedを別に抽出し、RF、ID、ラック、容量を確認します。preserve-throttlesなしでは、完了した--verifyがスロットル設定を解除する場合があります。
</details>

14. acks=allの耐久性前提と、ローリング処理中のリクエスト成功保証を区別してください。

<details>

<summary>解答を表示</summary>

**解答: 同期済みコピーと機能するクォーラム/リーダーが残る間は耐久性が高まりますが、リクエストはタイムアウトしたり再試行が必要になったりします。**

**解説:**
acks=allは最小ISRを満たしつつ、現在の全ISRを待ちます。同期済みコピーと利用可能なリーダー/クォーラム/ストレージ条件の維持が必要です。タイムアウト、再試行、繰り返し処理を別途扱います。
</details>

## 実践問題

15. 300Giのgp3ボリューム3つを持つ、新環境用ブローカープールの例を定義してください。

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
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
    - id: 1
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
    - id: 2
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
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
新環境の定義で、500Giへ拡張済みのボリュームを縮小する指示ではありません。第2部のgp3-kafkaを使い、メタデータボリュームを1つ選びます。Retain/deleteClaim設定はバックアップではありません。
</details>

16. `my-cluster`クラスター用に`full`モードの`KafkaRebalance`を作成し、生成提案を承認するコマンドを書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaRebalance
metadata:
  name: reviewed-full-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
  annotations:
    strimzi.io/rebalance-auto-approval: "false"
spec:
  mode: full
```

```bash
kubectl create -f rebalance-full.yaml
kubectl -n kafka wait kafkarebalance/reviewed-full-rebalance \
  --for=condition=ProposalReady --timeout=30m
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -o yaml
# Review the proposal before executing:
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

**解説:**
有効なメトリクス/ゴールでCruise Controlを有効にする必要があります。自動承認はfalseです。ProposalReadyを確認してから承認します。手動要求と自動スケーリング要求を区別します。
</details>

17. ブローカー拡張後、実IDとTLS管理者設定を使い、orders再割り当てを生成、抽出、実行、確認してください。

<details>

<summary>解答を表示</summary>

**解答:**
```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set reachable TLS bootstrap}"
: "${DOCS_ADMIN_CONFIG:?Set local admin properties file}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated broker IDs}"
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose reviewed throttle bytes/second}"
cat > topics-to-move.json <<'JSON'
{"version":1,"topics":[{"topic":"orders"}]}
JSON
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json --broker-list "$DOCS_BROKER_IDS" \
  --generate > generate-output.txt
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review the exact proposal before movement:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute --throttle "$DOCS_MOVE_BYTES_PER_SEC"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

**解説:**
CLI実行環境にファイルを置きます。実ブローカーIDとTLS管理者設定を使い、CurrentでなくProposedを抽出します。移動状態に--verify --preserve-throttlesを使い、URP/min-ISR/オフライン状態を別途確認します。1トピックの移動ではブローカーの完全退避は証明されません。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/03-kafka-operations.md) | [次のクイズ: Schema Registry](./04-schema-registry-quiz.md)
