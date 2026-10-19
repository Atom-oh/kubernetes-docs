# 第8部: ベストプラクティス

> **レビュー基準**: Kafka 4.3.1、Strimzi 1.3.0\
> **最終レビュー日**: 2026年10月16日

この章では、これまでの例を運用上の判断に結び付け、検証すべき事項を整理します。
[ベンチマークの章](./09-kafka-benchmark.md)では計測を扱います。チェックリストは、実際のワークロードや障害テストの代わりにはなりません。

## パーティションの設計と計測

一般的なコンシューマーグループでは、1つのパーティションを同時に割り当てられるグループメンバーは最大1つです。独立して読み取るメンバーを20個稼働させるには、少なくとも20パーティションが必要です。また、パーティションごとのスループット、キーの偏り、レコードサイズ、レプリケーション負荷、復旧時間、ブローカー／コントローラーのキャパシティも計測してください。共有グループやアプリケーション内並列処理では意味が異なるため、このルールをすべてのコンシューマーAPIに当てはめないでください。

パーティションを増やすと、メタデータ、レプリカ、バッファー、復旧に必要な作業も増えます。パーティションごとのメモリやファイルディスクリプター数に、すべての環境で使える単一の計算式はありません。かつての「ブローカーあたり4,000、クラスターあたり200,000」という経験則は、現在すべてに適用できる上限ではありません。論理パーティション数だけでなく、ブローカーごとのレプリカ割り当ても考慮し、定常時と障害時の実測に基づいて数を決めてください。

### トピック見出しではなくパーティションを数える

`grep -c "PartitionCount"`で数えられるのは**トピックの概要行**であり、パーティションではありません。次の内容を`partition_summary.py`として保存してください。現在のCLIが出力するパーティション行を読み取り、`Leader: none`も扱いながら、論理パーティション数とレプリカ配置／リーダー数を分けて報告します。

```python
import collections
import json
from pathlib import Path
import re
import sys

def summarize(text):
    pattern = re.compile(
        r"^\s*Topic:\s+(\S+)\s+Partition:\s+(\d+)\s+Leader:\s+(none|-?\d+)"
        r"\s+Replicas:[ \t]*([\d,]*)[ \t]+Isr:[ \t]*([\d,]*)"
    )
    partitions = {}
    topics = collections.Counter()
    leaders = collections.Counter()
    replicas = collections.Counter()
    offline = []
    for line in text.splitlines():
        if not re.search(r"\bPartition:", line):
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError("Unrecognized partition row; check Kafka CLI version/output.")
        topic, partition, leader, replica_text, _ = match.groups()
        key = (topic, int(partition))
        if key in partitions:
            raise ValueError("Duplicate topic/partition row.")
        replica_ids = [int(x) for x in replica_text.split(",") if x]
        if not replica_ids or len(set(replica_ids)) != len(replica_ids):
            raise ValueError("Missing or duplicate replica IDs.")
        partitions[key] = True
        topics[topic] += 1
        replicas.update(replica_ids)
        if leader == "none" or int(leader) < 0:
            offline.append({"topic": topic, "partition": int(partition)})
        else:
            leaders[int(leader)] += 1
    if not partitions:
        raise ValueError("No partition rows; empty visibility is not proof of a healthy cluster.")
    return {
        "visible_topics": len(topics),
        "logical_partitions": len(partitions),
        "replica_assignments": sum(replicas.values()),
        "partitions_by_topic": dict(sorted(topics.items())),
        "leaders_by_broker": dict(sorted(leaders.items())),
        "replicas_by_broker": dict(sorted(replicas.items())),
        "offline_partitions": offline,
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 partition_summary.py topics.txt")
    print(json.dumps(summarize(Path(sys.argv[1]).read_text()), indent=2))
```

```bash
set -euo pipefail
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
# Run from a Kafka 4.3.1 client installation. admin.properties is local to this client.
bin/kafka-topics.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe > topics.txt
python3 partition_summary.py topics.txt
```

この結果に含まれるのは、呼び出し元の認証主体から見えるトピックとコマンドのフィルターに一致するものだけです。出力された場合は内部トピックも含まれます。クエリが失敗したり空だったりしても、クラスターのパーティション数がゼロであることや、クラスターが正常であることの証明にはなりません。管理用の読み取りに適切な認証情報を使い、ブローカーPodのIDや`localhost:9092`の平文リスナーが使えるとは想定しないでください。

### キーの意味を保つ

Java Producerの既定のキー割り当てでは、明示的なパーティション、カスタムpartitioner、またはキーを無視する設定がない限り、**シリアライズ後のキーのバイト列**に`toPositive(murmur2(keyBytes)) % partitionCount`を適用します。同じ割り当てが必要な他のクライアントでも、互換性のあるpartitionerとserializerを使う必要があります。

カーディナリティが高いだけでは、トラフィックが均等になるとは限りません。非常に利用頻度の高い顧客が1社いれば、そのキーが依然として支配的になることがあります。ランダム値や時刻をキーに加えると、キー単位の順序、join、compactionでのキー識別が変わります。データ契約でそれらの変更が許される場合に限って使い、必要なら再結合や順序復元の方法を明示してください。

パーティション数を増やすと、一部のキーの割り当て先が変わる場合がありますが、既存レコードは再配置されません。パーティションをまたぐキーの順序や、同じパーティション構成を前提とするjoinも壊れることがあります。要件はjoinやトポロジーによって異なり、Kafka Streamsのすべてのjoinで同一のco-partitioning条件が使われるわけではありません。順序依存またはstatefulなワークロードでは、多くの場合、新しいトピックを使った再パーティション化／移行を計画してテストしてください。

## Producerのチューニング

これは、既存の認証済みクライアント設定に追加するための、計測に基づく開始プロファイルです。万能な最適値ではありません。

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

- `acks=all`は現在のISRを待ちます。RF=3でトピック／ブローカーの`min.insync.replicas=2`なら、ISRが2未満のときは2つ目のレプリカを無期限に待つのではなく、書き込みを拒否します。単一障害に耐えられるのは、残りのレプリカ／クォーラムと他の依存要件も満たされている間だけです。
- `enable.idempotence=true`は、サポートされるProducerの再試行による重複を抑制します。互換性のある`acks`、`retries`、`max.in.flight.requests.per.connection`の設定が必要です。互換性のある値を明示しても、冪等性が無効になるわけではありません。
- Kafka 4.3の`linger`既定値は5 msです。ここでの10 msと32 KiBは設定例です。`batch.size`はパーティションごとのバッチ処理／割り当て設定であり、レコードやリクエストの厳密な最大サイズではありません。キューイングと配信期限もレイテンシーに影響します。
- 代表的なデータ、CPU、レイテンシーを使ってlz4、zstd、gzip、圧縮なしを比較してください。常に総コストが最小になるコーデックが1つだけだとは限りません。

`min.insync.replicas`はProducerのプロパティではなく、トピック／ブローカーの設定です。`delivery.timeout.ms`が再試行を含む配信の期限を決めるため、再試行回数が多くても無期限に配信されるわけではありません。送信失敗を必ず監視してください。

冪等性は、アプリケーションが任意に再送する処理や外部データベースへの副作用を重複排除しません。Kafkaのconsume-transform-produceでexactly-onceを実現するには、適切なトランザクションの開始／終了、入力オフセットと出力の原子的なコミット、fencing、`read_committed`コンシューマーも必要です。`transactional.id`文字列だけでは不十分です。

## Consumerの処理とメンバーシップ

**このプロファイルでは`group.protocol=classic`を明示しているため**、クライアントのheartbeat／session設定が適用されます。`group.protocol=consumer`では、これらの間隔はブローカーのコンシューマーグループ設定によって制御されます。

```properties
group.id=order-processor
group.protocol=classic
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

レコード数だけでなく、実際の処理時間に上限を設けてください。処理の遅いレコードが1つあるだけでも`max.poll.interval.ms`を超えることがあります。動的メンバーと静的メンバーでは、割り当ての再調整タイミングが同じではありません。静的メンバーはpollタイムアウト後にheartbeatを止めても、sessionが期限切れになるまで再割り当てが保留されることがあります。

### 永続処理の完了後にコミットする

auto-commitは、非同期の外部処理がいつ完了したかを認識しません。正しい順序で動く同期ループならauto-commitを使えますが、ワーカープールの進捗まで追跡すると考えないでください。以下のヘルパーは、auto-commitを無効にし、同期処理が完了してから明示的にコミットする例です。

```java
import java.time.Duration;
import java.util.Properties;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;

public final class ConsumerExamples {
    public static void setStaticIdentity(Properties props, String instanceId) {
        if (instanceId == null || instanceId.isBlank() || instanceId.contains("${")) {
            throw new IllegalArgumentException("Supply a resolved, stable, unique consumer instance ID.");
        }
        props.setProperty(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, instanceId);
    }

    public static int processOneBatch(
            Consumer<String, String> consumer,
            java.util.function.Consumer<ConsumerRecord<String, String>> processDurably) {
        var records = consumer.poll(Duration.ofMillis(500));
        for (var record : records) {
            processDurably.accept(record);
        }
        if (!records.isEmpty()) {
            consumer.commitSync();
        }
        return records.count();
    }
}
```

```java
// props already includes bootstrap, TLS/SCRAM, deserializers and the profile below.
try (var consumer = new KafkaConsumer<String, String>(props)) {
    consumer.subscribe(List.of("orders"));
    while (!Thread.currentThread().isInterrupted()) {
        ConsumerExamples.processOneBatch(consumer, application::processDurably);
    }
}
```

`application.processDurably`はアプリケーション側の処理であり、必要な副作用が成功した後に限って戻るよう実装する必要があります。処理またはコミットに失敗した場合は停止して復旧するか、正しい位置へ明示的にseekしてください。**エラーを捕捉したまま失敗レコードを越えてpollを続けてはいけません。** 再起動時には処理済みレコードが再生されることがあるため、外部副作用には適切な冪等性／トランザクション戦略が必要です。終了処理は、KafkaConsumerがサポートするwakeup／closeパターンを使ってください。

KafkaConsumerは一般にスレッドセーフではありません。処理を別スレッドへ移す場合は、上限付きキュー、パーティション順序、コンシューマースレッド上でのpause／resume、連続して完了したオフセットの追跡、リバランス処理が必要です。スレッドプールへ移すだけでは信頼性の問題は解決しません。

### 安定した静的メンバーIDを解決する

Javaの`Properties`は`group.instance.id=${POD_NAME}`を展開しません。コンシューマーを生成する前に、アプリケーション／設定コードで環境変数の値を解決してください。

```java
// One consumer instance per stable logical member in this example.
ConsumerExamples.setStaticIdentity(props, System.getenv("KAFKA_GROUP_INSTANCE_ID"));
```

StatefulSet Podごとにコンシューマーを1つ動かす場合、Downward APIから取得した`metadata.name`を安定した論理IDに使えます。DeploymentのPod名は多くのロールアウトで変わります。同じPod内に複数のコンシューマーがあるなら、それぞれ異なるIDが必要です。稼働中の各コンシューマーには一意のIDを割り当て、置き換え後に意図して再利用する場合だけ同じIDを使います。同じIDを持つコンシューマーが同時に動くと、メンバーがfenceされることがあります。

静的メンバーシップは、互換性のある短時間の再起動で不要なリバランスを避けられますが、Podがタイマー前に戻れば割り当てが変わらないと保証するわけではありません。トポロジー、メンバーシップ、サブスクリプションも影響します。session timeoutを長くすると、本当に失敗したメンバーの復旧も遅れます。

## 認証、認可、ネットワーク

### 2種類のCAとリスナー設定を分ける

Strimzi管理の既定CAを使う場合:

- **クラスターCA**はブローカー／内部コンポーネントの証明書を署名します。クライアントは適切なサーバー証明書チェーンを信頼します。
- **クライアントCA**はmTLS用のKafkaUserクライアント証明書を署名します。
- `user.crt`／`user.key`はクライアント認証情報です。ユーザーSecret内のクライアントCA証明書は、ブローカーを信頼するための証明書チェーンの代わりにはなりません。

リスナーのネットワーク公開方式には`type: internal`、`loadbalancer`などを指定します。暗号化は`tls: true`、クライアント認証は`authentication.type: tls`です。`tls`という名前のリスナー公開方式はありません。

以下は既存の`spec.kafka.listeners`配列に追加する**1つのリスナーエントリー**であり、第2部のTLS／SCRAMリスナーを置き換えるものではありません。追加前にKafkaリソース全体を確認してください。

```yaml
name: mtls
port: 9094
type: internal
tls: true
authentication:
  type: tls
networkPolicyPeers:
- namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: kafka-clients
  podSelector:
    matchLabels:
      app: order-service
```

2つのセレクターは**1つのpeer内**にあるため、Podは`app=order-service`に一致し、**かつ**`kafka-clients`名前空間に属する必要があります。peerを2つに分けるとOR条件になり、NetworkPolicyの名前空間内でラベルに一致するPod、または選択した名前空間のすべてのPodが対象になります。NetworkPolicyは加算的に評価され、CNIによる適用が必要です。また、別の許可ポリシーを上書きしません。egressと、実際の外部／ノード通信経路も考慮してください。

次のmTLSユーザーは、既存のSCRAMユーザーとIDを分けます。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

User Operatorにこのユーザーを調整させ、ブローカーのsimple authorizerも有効にしてください。ユーザー認証情報とブローカー信頼情報を、管理されたローテーション手順でアプリケーション名前空間へ配布します。Kubernetesでは、別の名前空間にあるSecretを直接マウントできません。現在のgeneration、TLS／認証の成功、許可／拒否される操作を確認してください。YAMLをコミットしただけでは、アクセスが正しく動くことの証明になりません。

既存のSCRAM経路でも、暗号化とパスワードローテーションのためにTLSが必要です。Kafka ACLとNetworkPolicyは互いの代わりにはなりません。

### 新規プロビジョニングする永続ストレージを明示的に暗号化する

標準のEBS CSIドライバーでは、暗号化されたStorageClass、またはアカウント／リージョンのEBS暗号化既定設定を使ってください。この例では、ボリュームを保持し、スケジューリングを待ってからAZを選択します。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
parameters:
  type: gp3
  encrypted: 'true'
```

Auto Modeでは、`ebs.csi.eks.amazonaws.com`プロビジョナーと第2部のトポロジー制約を使い、`encrypted: "true"`も指定してください。Auto Modeのノード／エフェメラルディスク暗号化に関する説明から、動的PVCも暗号化されると推測しないでください。Auto ModeのStorageClassパラメーターでは`encrypted`の既定値はfalseです。作成後のEBSボリュームで暗号化状態とKMSキーを確認してください。

カスタマーマネージドキーを使う場合は、`key/xxxxxxxx`のような例ではなく実際のARNと、適切なロール／キーの権限設定が必要です。StorageClassの変更やアカウントの既定値有効化によって、既存ボリュームが遡って暗号化されることはありません。サポートされるデータ／スナップショット移行を計画し、永続ストレージを置き換える前に復元権限を確認してください。

## キャパシティ、階層化、保持

Kafkaではページキャッシュが有効ですが、CPU（TLS／圧縮を含む）、ネットワーク、ストレージのスループット／IOPS、cgroupのメモリ上限もボトルネックになります。計測ではheap、off-heap、ページキャッシュ、他のワークロードも含めてください。「heapは4～8 GBで十分」や、メモリ最適化インスタンスが常に最安という普遍的なルールはありません。

Kafkaのtiered storageは3.9以降本番利用可能で、Strimzi 1.3でもサポートされます。それでも互換性のある**RemoteStorageManagerプラグイン**、イメージ内の依存関係、リモートアクセス認証情報／権限、保持、クリーンアップ、復旧の設定が必要です。Strimziのカスタム統合では`spec.kafka.tieredStorage`にプラグインのクラス／パス／設定を指定します。`remote.log.storage.system.enable`を有効にするだけでは、KafkaはS3に接続しません。該当バージョンの機能制限を読み、リモートストレージが利用できない場合の動作と復元手順もテストしてください。

### 保持期間はデータに関わる判断

以下の例は既存トピックを変更し、3日または**パーティションあたり50 GiB**のうち先に到達した上限を適用します。削除はセグメント単位で非同期に行われるため、指定バイト数で瞬時に厳密上限へ到達するわけではありません。

```bash
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe \
  --entity-type topics --entity-name application-logs
# After reviewing retention/recovery requirements: shortening retention can delete data.
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --alter \
  --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

保持期間を短くすると、再生や復旧に必要なレコードが不可逆に削除される場合があります。`cleanup.policy=compact`ではクリーンアップは非同期で、tombstone／cleanerの動作に従いキーごとの最新値を保持します。キーのカーディナリティが高い場合や、未処理のセグメントがある場合は、ストレージが増え続けることがあります。compactionはストレージの厳密な上限ではありません。`compact,delete`では削除保持も適用され、古いキーの最後の値が削除されることもあります。state再構築とtombstone保持の要件を明示的に設計してください。

### Spotと中断への対応

この本番基準では、コントローラーのクォーラムを適切で信頼性の高いキャパシティ上に維持してください。リスクを許容できるワークロードならブローカーにSpotを検討できますが、Podを分散するだけでは同時に発生する回収を防げません。ブローカーのラック認識レプリカ配置、ノード／AZ分散、EBSボリュームと同じAZ内の代替キャパシティ、テスト済みの復旧と余裕容量を組み合わせてください。

Strimzi 1.3のPDBはKafkaクラスターのPodを対象とし、自発的なevictionを制限します。強制削除、ノード障害、Spot回収、またはすべてのOperatorローリング操作時のクォーラムを保証するものではありません。RF=3／minISR=2、PDB、On-Demandコントローラーはいずれも設計要素であり、データ損失やダウンタイムがゼロである証明ではありません。

## 本番利用前に残す証拠

- バージョン／API互換性、アップグレード／ロールバック、証明書ローテーションのリハーサル結果
- 障害時に計測したパーティション、レプリカ、CPU／メモリ／ネットワーク／ストレージ上限
- 検証した認可境界、クライアントID、Secret／信頼情報のローテーション
- スキーマ／履歴の互換性、処理／コミット動作、重複の扱い
- 復元／フェイルオーバーの証拠と、計測したRPO／RTO、必要なスキーマ／キー
- メトリクス収集／アラート／通知の網羅状況、コンシューマーキャパシティ、アプリケーションSLO
- 保持、ストレージ暗号化、コストの前提、明確な運用責任者

ワークロードに必要な制御を適用し、残る制約を記録してください。一般的なチェックリストを完了しても、本番利用可能と証明されたことにはなりません。

## 参考資料と検証

例はKafka 4.3.1の設定クラス、実際のキーpartitioner、MockConsumerの処理／コミットテスト、リリース済みリソーススキーマ、トピック出力のfixtureを使って確認しました。実際のTLS／CNI適用、暗号化ボリュームの検査、障害復旧、アプリケーションの正しさを確認するテストの代わりにはなりません。

- [Kafka 4.3 Producer設定](https://kafka.apache.org/43/configuration/producer-configs/)
- [Kafka 4.3 Consumer設定](https://kafka.apache.org/43/configuration/consumer-configs/)
- [Kafka 4.3 tiered storage](https://kafka.apache.org/43/operations/tiered-storage/)
- [Kafka 4.3.1のキーpartitioner](https://github.com/apache/kafka/blob/4.3.1/clients/src/main/java/org/apache/kafka/clients/producer/internals/BuiltInPartitioner.java)
- [Kafka 4.3.1のトピック説明出力](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/TopicCommand.java)
- [Strimzi 1.3.0のデプロイ、TLS、tiered storageガイド](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Kubernetes NetworkPolicyのセレクター意味論](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EBSの既定暗号化](https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html)
- [EKS Auto ModeのStorageClassパラメーター](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)

## 次のステップ

[第9部: Kafkaベンチマーク](./09-kafka-benchmark.md)

[メインページに戻る](./README.md)

## クイズ

[トピッククイズ](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
