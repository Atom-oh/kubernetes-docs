# EKS上のKafka詳解

## 概要

このガイドでは、EKS上でKafkaを自己管理する選択肢としてStrimzi Operatorを使用します。OperatorはPod、ストレージ、リスナー、証明書、アップグレードを調整しますが、データ、可用性、セキュリティ方針への責任をなくすものではありません。第6部ではAmazon MSKなどのマネージドな代替サービスを比較します。

> **最終更新**: September 12, 2026。Strimzi 1.2.0 / Kafka 4.3.1。
> **アップグレード要件**: Strimzi 1.0以降はCRD API `v1`のみをサポートします。Operatorのアップグレード前に、公式移行手順に従って既存の`v1beta2` / `v1beta1` / `v1alpha1`リソースを変換し、CRDを準備してください。バージョン番号を変更するだけではアップグレード計画になりません。

Strimzi 1.2.0はKafka 4.2.0、4.2.1、4.3.0、4.3.1をサポートし、デフォルトは4.3.1です。このガイドは互換性のある組み合わせに固定しています。インストール前にはディストリビューション、Kubernetesバージョン、アップグレード経路も確認してください。

## アーキテクチャの主要概念

ブローカーはトピックのパーティションレプリカを格納します。KafkaConsumerグループはパーティションを分担し、1つのメンバーが複数パーティションを所有する場合があります。別のコントローラークォーラムがメタデータのRaftログを管理します。

KRaftは2.8で早期アクセスとして登場し、3.3で本番利用可能になりました。Kafka 4.0ではZooKeeperモードが削除されました。コントローラーとブローカーは専用ロールにできます。ZooKeeperを削除しても、コントローラー、ストレージ、復旧の運用がなくなるわけではありません。

ユーザーはKafkaやKafkaNodePoolなどのカスタムリソースを宣言し、StrimziがPod、PVC、Service、Secretを調整します。次の図は関係を簡略化したものであり、HA構成のレプリカ数を定めたデプロイ仕様ではありません。

![StrimziによるKafka/KafkaNodePoolからPod/PVCへの調整を簡略化した図。実際のブローカーとコントローラーのレプリカ数は別途設計が必要](../../.gitbook/assets/en-data-on-eks-kafka-readme-0.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-kafka-readme-0.html)

## 詳解の目次

**[1. Kafkaの基礎](01-kafka-fundamentals.md)**
- ブローカーとトピック/パーティションの構造
- レプリケーションと耐久性の保証
- コンシューマーグループとオフセット管理
- KRaftコントローラークォーラムのアーキテクチャ

**[2. Strimzi Operator](02-strimzi-operator.md)**
- Strimziのインストールと設定
- `Kafka`と`KafkaNodePool` CRDの詳細
- EKSへのKafkaクラスターのデプロイ

**[3. Kafkaの運用](03-kafka-operations.md)**
- EBS/gp3を用いたストレージ設計
- ブローカーのスケーリング戦略
- Cruise Controlによるパーティションのリバランス
- 互換性と可用性の確認を伴うローリングアップグレード

**[4. Schema Registry](04-schema-registry.md)**
- Avro/Protobufスキーマの設計
- KarapaceとApicurio Registryの比較
- 互換性戦略: BACKWARD/FORWARD/FULL

**[5. Kafka ConnectとMirrorMaker](05-kafka-connect-mirrormaker.md)**
- Kafka Connectのデプロイとコネクターの設定
- ソースコネクターとシンクコネクターの運用
- MirrorMaker2による災害復旧とリージョン間レプリケーション

**[6. MSKとの統合](06-msk-integration.md)**
- Amazon MSKと自己管理のStrimziの比較
- MSK Connectの使用
- Kinesis Data Streamsとの統合と比較

**[7. 監視](07-monitoring.md)**
- Prometheus/Grafanaによるブローカーメトリクスの収集
- コンシューマーラグの監視
- KEDAによるコンシューマーの自動スケーリング

**[8. ベストプラクティス](08-best-practices.md)**
- パーティション数とキーの設計戦略
- プロデューサー/コンシューマーの性能チューニング
- mTLS/SASLによるセキュリティ
- ストレージとインスタンスのコスト最適化

**[9. Kafka実測ベンチマーク](09-kafka-benchmark.md)**
- gp3ボリューム上の3ブローカーKRaftクラスターで実測したRF3とRF1の取り込み上限
- acks=0/1/allにおけるスループットとp99レイテンシーのトレードオフ
- 圧縮コーデックとレコードサイズごとのスループットおよびCPUコスト
- コールドコンシューマーと混在ワークロードがプロデューサーのスループットに及ぼす影響

## 参考資料

- [Strimzi 1.2.0のリリース](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.2.0)

- [Strimziドキュメント](https://strimzi.io/docs/operators/1.2.0/overview.html)
- [Apache Kafkaドキュメント](https://kafka.apache.org/43/design/design/)
- [KRaft運用ガイド](https://kafka.apache.org/43/operations/kraft/)
- [AWS Data on EKSプロジェクト](https://awslabs.github.io/data-on-eks/)

## クイズ

このセクションの学習内容を確認するには、[Kafkaの基礎クイズ](../../quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)に挑戦してください。ベンチマークの数値を設計判断に結び付けられるかを確認するには、[Kafka実測ベンチマーククイズ](../../quizzes/data-on-eks/kafka/09-kafka-benchmark-quiz.md)にも挑戦してください。
