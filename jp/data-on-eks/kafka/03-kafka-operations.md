# 第3部: Kafkaの運用

> **最終更新**: September 12, 2026、Strimzi 1.2.0 / Kafka 4.3.1。
> **検証**: 現行リリースのドキュメント/ソース、ローカルでのCRD/マージパッチ確認、提案の生成/JSON抽出、Decimalによる計算、CLIオプションを検証しました。Kafkaの再割り当て、アップグレード、AWSボリュームの変更は実行していません。

この章は、[第2部](./02-strimzi-operator.md)の認証付きKafkaデプロイとブローカー専用プールを前提とします。運用コマンドは実際のパーティションを移動し、リソースを変更する可能性があります。実行前に現在の設定、配置、提案を確認してください。ブローカーのスケーリング手順を、そのままコントローラーロールのプールに適用しないでください。

## 1. ストレージ性能と耐久性

コンシューマーラグがあっても、すべての読み取りがランダムになるわけではありません。過去データの順次読み取りでも、コンシューマーが異なる範囲を交互に読んだりページキャッシュを超えたりすると、物理I/Oとテールレイテンシーが増えることがあります。IOPS、スループット、キュー遅延、キャッシュヒット、インスタンスのEBS制限を測定してください。

| 特性 | gp3 | io2 Block Express |
| --- | --- | --- |
| 含まれるベースライン | 3,000 IOPS / 125 MiB/s | 性能はプロビジョニングされたIOPSに応じる |
| ボリュームの最大IOPS | 80,000 | Nitroで256,000 |
| ボリュームの最大スループット | 2,000 MiB/s | 4,000 MiB/s |
| 最大サイズ | 64 TiB | 64 TiB |
| 公表されている設計上の耐久性 | 99.8–99.9% | 99.999% |
| 公表されているAFR上限 | 0.2% | 0.001% |

これらはボリュームの設計値であり、KafkaサービスのSLAでも、あらゆる障害に対する保証でもありません。最大性能にはボリュームサイズ、IOPS比率、インスタンスに関する要件があります。Outpostsのgp3やNitro以外のio2には異なる制限があります。

ストレージ容量も請求対象です。gp3の含有ベースラインを超える性能と、io2のプロビジョニングされたIOPSも評価してください。レイテンシー/耐久性要件、測定結果、現在のリージョン別料金に基づいて選択します。io2はIOPSだけで課金されるわけではなく、大きなコンシューマーラグがあるだけでio2が必須になるわけでもありません。

## 2. 保持と空き容量

**保持される圧縮済みログのバイト数**と実際の保持期間を基に見積もります。短時間のピークを7日間継続するレートとして扱うと、ストレージを過大評価する可能性があります。トピックごとの保持/レプリケーションを別々に計算し、コンパクション、インデックス、内部トピック、再割り当て時の一時コピーも考慮してください。

仮定した持続レート **50 MB/s（10⁶ bytes/s）** がRF=3で7日間続くと、複製後のログは90.72 TBになります。

| 解釈 | 容量 | 実際の空き容量の割合 |
| --- | --- | --- |
| データサイズに30%を加算する | 117.936 TB | 約23.08% |
| 総ディスク容量の30%を空けておく | 129.6 TB、約117.87 TiB | 30% |

以前の約118 TBという計算は、最初の解釈としては正しい値です。2つ目は`data / (1 - 0.30)`を使用します。129.6 TBを3台のブローカーで均等に分けると各43.2 TBですが、実際のパーティションの偏りも重要です。これらは計算例であり、第2部の演習用PVCのサイズに関する推奨ではありません。

**`storage-sizing.py`**

```python
"""Illustrative storage calculation, not measured traffic or a volume recommendation."""
from decimal import Decimal
import json

retained_log_bytes_per_second = Decimal("50000000")  # 50 decimal MB/s, sustained
retention_seconds = Decimal(7 * 24 * 60 * 60)
replication_factor = Decimal(3)
broker_count = Decimal(3)
margin = Decimal("0.30")
replicated_bytes = retained_log_bytes_per_second * retention_seconds * replication_factor
additive_capacity = replicated_bytes * (1 + margin)
free_space_capacity = replicated_bytes / (1 - margin)

print(json.dumps({
    "replicated_log_TB": str(replicated_bytes / Decimal(10**12)),
    "capacity_with_30_percent_added_TB": str(additive_capacity / Decimal(10**12)),
    "free_percent_with_added_margin": str((1 - replicated_bytes / additive_capacity) * 100),
    "capacity_with_30_percent_free_TB": str(free_space_capacity / Decimal(10**12)),
    "capacity_with_30_percent_free_TiB": str(free_space_capacity / Decimal(2**40)),
    "average_per_broker_TB": str(free_space_capacity / broker_count / Decimal(10**12)),
    "assumptions": [
        "Sustained retained-log bytes after compression; not a short traffic peak.",
        "No separate allowance here for indexes, internal topics, compaction or temporary reassignment copies.",
        "Per-broker division assumes equal data placement; measure actual skew."
    ]
}, indent=2))
```

## 3. JBODの拡張と変更

Kafka 4.3.1は通常、新しいログを配置する際、パーティションログが少ないディレクトリを優先します。単純なラウンドロビンやバイト数で均等化する配置ではありません。ディスクを追加しても、既存データは自動的に再分散されません。

このマージパッチは第2部のボリューム0を100Giから500Giへ拡張し、ボリューム1を追加します。**volumes配列全体を置き換えます**。そのまま適用せず、他の既存ボリュームを保持してください。既存のトポロジー/リソース設定は維持されます。

**`storage-expand.patch.yaml`**

```yaml
# For the Part 2 broker pool with one 100Gi volume (id 0).
# Merge patch replaces the entire volumes array; preserve every existing volume.
spec:
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
        kraftMetadata: shared
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
```

```bash
kubectl -n kafka get kafkanodepool broker -o yaml > broker-before.yaml
kubectl -n kafka patch kafkanodepool broker --type=merge \
  --patch-file storage-expand.patch.yaml
kubectl -n kafka get pvc -l strimzi.io/cluster=my-cluster
```

拡張はStorageClass/CSIとファイルシステムに依存します。PVCの縮小、クラス変更、ボリュームID変更は、この操作には含まれません。kraftMetadata: sharedを2つのボリュームに割り当てないでください。

ディスクを取り外す前に、レプリカとメタデータの配置を調べ、データを退避してください。Strimzi 1.2はremove-disksリバランスモードでブローカー内のJBOD移動をサポートし、専用のフィールドと前提条件があります。deleteClaim: false/Retainはバックアップでも復旧の証明でもありません。Operator管理下のデータに対してkafka-storage.sh formatを手動実行しないでください。

## 4. ブローカーのスケーリング: 手動と自動の方法

これらの手順は**ブローカー専用プール**が対象です。Strimzi 1.2は静的コントローラークォーラムを設定するため、コントローラーロールのプールを同じ方法でスケーリングしないでください。上流Kafkaの動的クォーラム機能とOperatorのサポートは別です。

| 設定 | 既存プールのレプリカ数の変更 |
| --- | --- |
| 一致するautoRebalanceモードなし | ブローカー追加と既存レプリカの移動は別々 |
| `add-brokers` autoRebalance | スケールアウト後に自動再分散 |
| `remove-brokers` autoRebalance | スケールイン時にレプリカ退避を自動調整 |

自動化は**既存プールのreplicas変更**に反応します。プールの作成/削除は同じトリガーではありません。Kafka 4.3+では、自動スケールダウン時にブローカーをcordonし、退避中の新しいレプリカ割り当ても防止します。

### 手動スケールアウト

```bash
kubectl -n kafka get kafka my-cluster -o jsonpath='{.spec.cruiseControl.autoRebalance}'
# Continue with the manual path only when the relevant automatic mode is not enabled.
kubectl -n kafka get kafkanodepool broker -o json > broker-before.json
kubectl -n kafka patch kafkanodepool broker --type=merge -p '{"spec":{"replicas":6}}'
kubectl -n kafka get pods -l strimzi.io/pool-name=broker
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
```

PodがRunningであるだけでは不十分です。Operatorの現在のgeneration、ブローカー登録、ISR、容量を確認してください。ノードIDはクラスター全体にまたがります。IDが0–5であることや、my-cluster-broker-0というPodがあることを想定しないでください。

### 手動スケールダウン

実際に削除するIDを特定し、**内部トピックを含むすべてのレプリカ**を退避します。orders/paymentsだけを移動しても、ブローカーが空である証明にはなりません。replicasを減らす前に、完了、残存RF/ISR、ラック分散、容量を確認してください。

strimzi.io/remove-node-idsでIDを選択できますが、無効な範囲を指定するとデフォルトの選択に戻る場合があります。現在のnodeIdsと比較してください。Strimziの空でないブローカーに対するスケールダウンチェックを有効なままにします。このチェックを迂回してデータを持つブローカーを削除することは、標準の運用手順ではありません。

## 5. Cruise Controlの提案と承認

この例はデフォルトで手動承認を使用します。既存のKafka設定を保持してCruise Controlを追加してください。任意のgoalsリストによってデフォルトのハードゴールを除外したり、汎用のデフォルトとしてskipHardGoalCheckを有効にしたりしないでください。

**`cruise-control.patch.yaml`**

```yaml
spec:
  cruiseControl: {}
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file cruise-control.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

**`rebalance-full.yaml`**

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
# Review optimizationResult, movement volume, goals, capacity and expected impact first.
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

メトリクスのサンプル不足や達成不能なゴールにより、ProposalReadyにならない場合があります。承認前に、移動量、ゴール、ラック、容量を確認してください。手動作成のauto-approval=falseリクエストと、自動スケーリングで生成されたリクエストを区別します。以前のリクエストがすでに存在する場合、新しい変更には一意の名前を使用してください。

| モード | 目的 |
| --- | --- |
| `full` | ゴールに基づくクラスター全体の再分散 |
| `add-brokers` | 指定した新しいブローカーへレプリカを移動 |
| `remove-brokers` | 指定したブローカーからレプリカを退避 |
| `remove-disks` | ブローカー内のJBODボリュームからレプリカを退避 |

追加/削除モードにはブローカーIDが必要です。対象範囲を狭めても、実行時間の短縮や影響の軽減は保証されません。このヘルパーはブローカープールのスナップショットに対してIDを検証し、**提案CRのJSONだけ**を作成します。容量やISR/ラックの安全性の評価、APIの呼び出しは行いません。

**`rebalance_request.py`**

```python
"""Generate a manual KafkaRebalance proposal from a broker pool snapshot; no API calls."""
import argparse
import json
from pathlib import Path


def request(pool, mode, broker_ids):
    if pool.get("kind") != "KafkaNodePool" or pool.get("spec", {}).get("roles") != ["broker"]:
        raise ValueError("Use a broker-only KafkaNodePool snapshot")
    metadata = pool.get("metadata", {})
    namespace = metadata.get("namespace")
    cluster = metadata.get("labels", {}).get("strimzi.io/cluster")
    if not namespace or not cluster:
        raise ValueError("The pool must include namespace and cluster label")
    known = pool.get("status", {}).get("nodeIds", [])
    if not known or any(type(value) is not int or value < 0 for value in known):
        raise ValueError("Read a fresh pool snapshot with valid status.nodeIds")
    if mode not in ("add-brokers", "remove-brokers"):
        raise ValueError("Select add-brokers or remove-brokers")
    if not broker_ids or len(broker_ids) != len(set(broker_ids)):
        raise ValueError("Supply distinct broker IDs")
    if any(type(value) is not int or value not in known for value in broker_ids):
        raise ValueError("Every selected broker must belong to the supplied pool")
    return {
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaRebalance",
        "metadata": {
            "name": f"reviewed-{mode}", "namespace": namespace,
            "labels": {"strimzi.io/cluster": cluster},
            "annotations": {"strimzi.io/rebalance-auto-approval": "false"},
        },
        "spec": {"mode": mode, "brokers": sorted(broker_ids)},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--mode", choices=["add-brokers", "remove-brokers"], required=True)
    parser.add_argument("--brokers", nargs="+", type=int, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(request(json.loads(args.pool.read_text()), args.mode, args.brokers), indent=2))
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Cannot create proposal: {error}\n")
```

```bash
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
# Set actual broker IDs from the snapshot, not controller IDs.
DOCS_BROKER_ID="REPLACE_WITH_VERIFIED_BROKER_ID"
python3 rebalance_request.py --pool broker-pool.json \
  --mode remove-brokers --brokers "$DOCS_BROKER_ID" > remove-proposal.json
python3 -m json.tool remove-proposal.json
# Review the generated proposal before creating/approving it.
```

### オプション: 既存プールの自動リバランス

この設定では、**replicasの変更後に別途手動承認することなくデータが移動する場合があります**。定義された運用方針/ゴールの下でのみ有効にしてください。status.autoRebalance.state=Idleは失敗後にも現れる場合があるため、生成されたKafkaRebalanceの結果とKafkaのstatusを併せて確認します。

**`auto-rebalance.patch.yaml`**

```yaml
# Optional: enables automatic partition movement on existing pool replica changes.
spec:
  cruiseControl:
    autoRebalance:
      - mode: add-brokers
      - mode: remove-brokers
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file auto-rebalance.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get kafkarebalances -l strimzi.io/cluster=my-cluster
```

## 6. 手動Kafka CLIによる代替手段

JSONファイルと管理者設定は、CLIを実行する環境と同じ場所に置いてください。ローカルファイルがkubectl exec内で自動的に利用可能になるわけではありません。クライアントには、広告されたすべてのエンドポイントへのアクセスと、管理権限を持つTLS/SASL IDが必要です。第2部のordersアプリケーションユーザーは管理者ではありません。

この例の対象はordersのみです。ブローカー削除に必要な完全な一覧ではありません。

```json
{
  "version": 1,
  "topics": [{"topic": "orders"}]
}
```

```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set a reachable TLS bootstrap endpoint}"
: "${DOCS_ADMIN_CONFIG:?Set the local admin client.properties path}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated target broker IDs}"
# Save the JSON above as topics-to-move.json in this environment.
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "$DOCS_BROKER_IDS" --generate > generate-output.txt
```

--generateはCurrentとProposedの両方のJSONを出力します。元の出力を以前の配置の記録として保持し、Proposedだけを新しいファイルへ抽出してください。このヘルパーは既存出力の上書きを拒否するため、新しい計画には新しいファイル名を使用します。

**`extract_reassignment.py`**

```python
"""Extract Kafka 4.3 --generate's proposal; never execute reassignment."""
import argparse
import json
from pathlib import Path

MARKER = "Proposed partition reassignment configuration"


def extract(text):
    if text.count(MARKER) != 1:
        raise ValueError("Expected exactly one proposal marker; inspect the command output")
    proposal, _ = json.JSONDecoder().raw_decode(text.split(MARKER, 1)[1].lstrip())
    if (not isinstance(proposal, dict) or type(proposal.get("version")) is not int
            or proposal["version"] != 1 or not isinstance(proposal.get("partitions"), list)
            or not proposal["partitions"]):
        raise ValueError("Expected a nonempty version-1 reassignment proposal")
    seen = set()
    for entry in proposal["partitions"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid partition entry")
        topic, partition, replicas = entry.get("topic"), entry.get("partition"), entry.get("replicas")
        if not isinstance(topic, str) or not topic or type(partition) is not int or partition < 0:
            raise ValueError("Invalid topic/partition")
        if (topic, partition) in seen:
            raise ValueError("Duplicate topic/partition")
        seen.add((topic, partition))
        if (not isinstance(replicas, list) or not replicas
                or any(type(broker) is not int or broker < 0 for broker in replicas)
                or len(replicas) != len(set(replicas))):
            raise ValueError("Invalid replica list")
        if "log_dirs" in entry:
            if (not isinstance(entry["log_dirs"], list) or len(entry["log_dirs"]) != len(replicas)
                    or not all(isinstance(directory, str) for directory in entry["log_dirs"])):
                raise ValueError("Log directory and replica lists must have equal lengths")
    return proposal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        proposal = extract(args.input.read_text())
        with args.output.open("x") as stream:
            json.dump(proposal, stream, indent=2)
            stream.write("\n")
    except (ValueError, OSError, TypeError, AttributeError) as error:
        parser.exit(1, f"Proposal extraction failed: {error}\n")
```

```bash
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review topic coverage, replica order/count, broker IDs, racks and capacity.
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose the reviewed movement throttle in bytes/second}"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute \
  --throttle "$DOCS_MOVE_BYTES_PER_SEC"

# Status check without removing configured throttles:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

ヘルパーはJSONの形式を検証しますが、ブローカーの存在、RFの維持、ラック間の均衡、パーティション一覧の完全性は検証しません。

--verifyは指定された再割り当て/ログディレクトリ移動を確認します。**--preserve-throttlesなしでは、検証完了時にブローカー/トピックのスロットル設定が解除される場合があり、純粋な読み取り専用操作ではありません。** 同じ制限を共有する他の作業とクリーンアップを調整してください。この検証は、複製不足/オフラインパーティションに対する完全な健全性チェックでもありません。

```bash
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-min-isr-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --unavailable-partitions
```

## 7. バージョンアップグレード

**現在と移行先の両方のKafkaバージョン**をサポートするOperatorの組み合わせを選択してください。すでに両方をサポートしているなら、順序のためだけにOperatorをアップグレードする必要はありません。最新Operatorが現在のKafkaバージョンのサポートを削除している場合、直接インストールせず、中間のサポート対象バージョンとAPI変換を計画します。

### ソフトウェアとmetadataVersion

metadataVersionを省略すると、StrimziはKafkaバイナリのアップグレード後にデフォルト値へ自動更新する場合があります。両方のフィールドを1回の更新で変更すること自体が、クォーラムを破損させるわけではありません。

以前のmetadataVersionを明示的に維持すると、引き上げる前に検証/復旧を判断する期間を確保できます。この例は、Strimzi 1.2の下で**既存のKafka 4.2.1 / メタデータ4.2-IV1**クラスターを4.3.1へアップグレードします。すでに4.3.1である第2部の演習環境でメタデータを下げる指示ではありません。

**`upgrade-binaries.patch.yaml`**

```yaml
# Only for an existing Kafka 4.2.1 cluster currently using metadata 4.2-IV1.
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.2-IV1
```

```bash
kubectl -n kafka get kafka my-cluster -o yaml > kafka-before-upgrade.yaml
# Check current version, metadataVersion and any custom image override first.
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-binaries.patch.yaml
kubectl -n kafka get pods -l 'strimzi.io/cluster=my-cluster,strimzi.io/pool-name' \
  -o 'custom-columns=NAME:.metadata.name,IMAGES:.spec.containers[*].image'
kubectl -n kafka get kafka my-cluster -o yaml
```

status.kafkaVersion、status.kafkaMetadataVersion、status.operatorLastSuccessfulVersion、generation、実際のPodイメージを併せて確認してください。カスタムのKafka、Connect、MirrorMakerイメージも、互換性のあるバージョンで準備する必要があります。

クライアントと復旧計画を検証した後、適切であればメタデータを引き上げます。新しいメタデータ/機能によりダウングレードできなくなる場合があります。Gitで元に戻しても復旧は保証されません。

**`upgrade-metadata.patch.yaml`**

```yaml
# Apply only after validating the completed binary upgrade and recovery plan.
spec:
  kafka:
    metadataVersion: 4.3-IV0
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-metadata.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

すべてのspec変更がPodを再起動するわけではありません。動的なKafka設定やサポートされたボリューム拡張では、別の方法で処理される場合があります。再起動が必要な場合でも、Operatorの可用性チェックは無停止や損失ゼロを絶対的に保証するものではありません。データ状態、ISR、コントローラークォーラム、クライアントのタイムアウトと再試行を観察してください。

## 8. PDBと障害処理

Strimzi 1.2のデフォルトKafka PDBは、**Kafkaクラスターごとに1つで、そのノードプール全体のKafka Podを対象とします**。プールごとに1つではありません。生成設定やカスタムPDBが異なる場合は、実際のセレクターとminAvailable/maxUnavailableを調べてください。

PDBは自発的な退避を制限します。ノード/AZ障害、Podの直接削除、Operatorのあらゆる操作を防ぐものではありません。min.insync.replicasは、あらゆる形態のデータ損失を防止する単一のスイッチではありません。

```bash
kubectl -n kafka get pdb -l strimzi.io/cluster=my-cluster -o yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

acks=allは同期済みレプリカに関する前提の下で耐久性を高めますが、すべてのアプリケーションリクエストの成功を保証しません。再起動中のリーダー/コーディネーターの変更、タイムアウト、再試行、繰り返し処理を計画に含めてください。ブローカーの再起動が必ずすべてのコンシューマーグループ全体を停止させるわけではありません。

Strimzi Drain Cleanerなどの追加コンポーネントには、独自のサポートモード/PDB動作があります。操作が失敗したという理由だけでfinalizerやスケールダウンチェックを削除しないでください。まず原因と、残っているデータ/メタデータのレプリカを確認します。

## 次のステップと参考資料

- [Schema Registry](./04-schema-registry.md)
- [Kafkaの概要](./README.md)
- [クイズ](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
- [Strimzi 1.2の運用](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Kafka 4.3の設計](https://kafka.apache.org/43/design/design/)
- [Kafka 4.3.1のログディレクトリ選択](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/log/LogManager.scala)
- [Kafka再割り当てコマンドの実装](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/reassign/ReassignPartitionsCommand.java)
- [EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EBS io2 Block Express](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)
- [EBSの料金](https://aws.amazon.com/ebs/pricing/)
