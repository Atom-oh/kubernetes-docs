# Kubernetes 上のデータベースの概要

> **最終更新日**: 2026年9月11日

「データベースを Kubernetes 上で実行すべきか」は、もはや単純な Yes/No の質問ではありません。実際に検討すべきなのは、**どのデータベースを、どの Operator で運用し、どのストレージ上で実行するか**です。このセクションでは、その判断の枠組みを扱い、仕様書の数値ではなく実測データで裏付けます。

## このセクションの内容

| ドキュメント | 内容 |
|----------|----------------|
| [EKS 上の ClickHouse の実測ベンチマーク](./01-clickhouse-on-eks.md) | 1 億件のログ行を読み込んだ EKS 上のシングルノード ClickHouse: 実測した取り込みスループット、圧縮率、クエリレイテンシ、スキップインデックスの効果 |

## Kubernetes のマネージド型とセルフホスト型の比較

| 基準 | マネージド型 (RDS/Aurora/ElastiCache) が有利 | K8s セルフホスト型が有利 |
|-----------|---------------------------------------|----------------------|
| 運用スタッフ | 専任の DBA/プラットフォームチームが不要 | プラットフォームチームがライフサイクルを管理 |
| エンジンの提供状況 | 成熟したマネージドサービスがある PostgreSQL/MySQL/Redis | 利用可能なマネージドサービスでは対応できないリージョン/拡張機能/バージョンが必要な場合。ClickHouse Cloud との比較も必要 |
| コスト構造 | サービス料金と運用コストの削減 | インフラストラクチャ、HA、バックアップ、アップグレード、スタッフのコストを合わせて検討 |
| デプロイ密度 | テナントが少数 | GitOps によってテナントごとのデータベースを数十個デプロイ |
| 制御要件 | 提供リージョン、暗号化、監査機能を確認 | 追加の制御と運用責任の両方を自ら担う |

重要な問いは、**データベースのライフサイクルと復旧の責任を誰が担うか**です。検証済みの Operator はその作業の一部を自動化できますが、インストールしただけでは HA やバックアップは確立しません。サポートされているエンジン/Kubernetes の組み合わせと復旧機能を確認してください。StatefulSet を直接使うチームは、対応する自動化を実装し、運用責任を自ら果たす必要があります。

## Operator の状況 (2026 年)

| データベース | 主な Operator | 成熟度に関する注意点 |
|----------|-------------------|----------------|
| PostgreSQL | CloudNativePG、Crunchy PGO、Zalando | サポートされる PostgreSQL/Kubernetes のバージョンと復旧動作を比較 |
| MySQL | Percona Operator、Vitess (シャーディング)、MySQL Operator (Oracle) | Vitess はシャーディングプラットフォームです。Percona/Oracle のエンジンと機能のサポートを比較 |
| Redis/Valkey | OT-CONTAINER-KIT redis-operator と代替製品。エンジンのサポートを確認 | キャッシュ用途なら、まず必ず ElastiCache の料金と比較 |
| ClickHouse | Altinity clickhouse-operator | 成熟したコミュニティ Operator を持つ Apache-2.0 ライセンスのデータベース。マネージド型の代替は ClickHouse Cloud |
| MongoDB | MongoDB Controllers for Kubernetes、Percona | 従来の Community Operator は非推奨です。現行のリポジトリ/移行ガイドを使用 |
| Kafka | Strimzi | ストリーミングについては [Data Pipeline セクション](../data-on-eks/kafka/README.md)を参照 |

## K8s 上のデータベース運用を支える 4 つの柱

1. **ストレージ**: ボリュームの種類がパフォーマンスの予算になります。[EBS gp2 と gp3 のベンチマーク](../storage/01-ebs-gp2-gp3-benchmark.md)が示すように、容量が同じでも IOPS は 10 倍異なる場合があります。データベースでは gp3 から始め、プロビジョンド IOPS も選択肢に含めます。
2. **トポロジー**: `topologySpreadConstraints` でレプリカを複数の AZ に分散し、AZ 間転送料金とレプリケーションラグも考慮してください。
3. **リソース分離**: Guaranteed QoS が必要な場合、すべてのコンテナで CPU/メモリの requests と limits を等しくする必要があります。これで OOM、CPU スロットリング、ノード障害がなくなるわけではありません。測定したワークロードに合わせ、CPU limits、キャッシュ、バックグラウンド処理、クエリ用メモリの余裕を調整してください。
4. **実際に復元したバックアップ**: Operator のバックアップ機能 (例: CloudNativePG がサポートする Barman Cloud プラグインから S3 へのバックアップ) を有効にするのは最低条件です。定期的に復元訓練を行って初めて、バックアップが実用的になります。

## 関連資料

- [ログバックエンドとしての ClickHouse](../observability/logging/04-clickhouse.md): オブザーバビリティパイプラインの観点から見た ClickHouse
- [Kubernetes ストレージ](../core/04-storage.md) / [ストレージセクション](../storage/README.md)
- [EKS ストレージ パート 1](../eks/04-eks-storage-part1.md)

## 参考資料

- [MongoDB Operator の移行](https://github.com/mongodb/mongodb-kubernetes/blob/master/docs/migration/community-operator-migration.md)
- [CloudNativePG](https://cloudnative-pg.io/docs/)
- [ClickHouse Cloud](https://clickhouse.com/cloud)
- [Altinity ClickHouse Operator](https://github.com/Altinity/clickhouse-operator)
