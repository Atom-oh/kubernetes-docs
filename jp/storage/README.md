# ストレージ概要

> **最終更新日**: 2026年9月11日

Kubernetes で stateful workload を実行すると、ストレージは単に「後から接続するもの」ではなくなり、性能、コスト、可用性を左右する領域になります。このセクションでは、実務上重要な順序でクラウドストレージを扱います。**選び方 → 実際に測定されるもの → 運用方法**です。

## このセクションの内容

| ドキュメント | 内容 |
|----------|----------------|
| [EBS gp2 と gp3 の実測ベンチマーク](./01-ebs-gp2-gp3-benchmark.md) | 同じ 100 GiB のボリュームでも性能に10倍の差が生じる理由: fio で測定した IOPS／レイテンシー／スループットと gp2 のバーストクレジット枯渇 |

Kubernetes ストレージの基礎と実践的な EKS 設定については、本書の別の箇所で詳しく扱っています。このセクションは、次の資料と併せてお読みください。

- [Kubernetes Storage](../core/04-storage.md): PV／PVC、StorageClass、動的プロビジョニング、アクセスモード
- [EKS Storage Part 1: EBS, EFS](../eks/04-eks-storage-part1.md): CSI driver のインストールと基本的な使用方法
- [EKS Storage Part 2: FSx for Lustre, S3, snapshots, performance](../eks/04-eks-storage-part2.md)
- [EKS Storage Part 3: monitoring, troubleshooting, cost](../eks/04-eks-storage-part3.md)

## ストレージスタックの概要

アプリケーションの書き込みから物理ボリュームまでの経路を理解すると、性能が期待に届かないときに、どのレイヤーを調査すべきかが分かります。

```text
application write()
  → mounted volume filesystem (ext4/xfs)
    → guest kernel and block device
      → EC2 EBS path (IOPS/bandwidth shared by all volumes)
        → EBS service and volume (per-volume IOPS/throughput limits)
```

ボリューム自体の上限と、**インスタンス単位の EBS 帯域幅／IOPS 上限**は別々の予算です。m5.xlarge のベースラインはおよそ 6,000 IOPS です。3 つの gp3 ボリュームを同時に 3,000 IOPS で動かすと、合計 9,000 IOPS を要求するため、持続可能なベースラインを超えます。インスタンスのバースト容量と、他のすべてのボリュームのトラフィックも確認してください。

## AWS ストレージの選択

| サービス | アクセスモード | 特性 | 適した用途 |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO（単一ノード） | ブロックストレージ。レイテンシーは種類、負荷、キュー深度に依存 | データベース、単一 Pod の状態データ |
| **EFS** | RWX（複数ノード） | NFS、ミリ秒単位のレイテンシー、伸縮する容量 | 共有設定／コンテンツ、共有 ML 学習データ |
| **FSx for Lustre** | RWX | 高スループットの並列ファイルシステム | HPC、大規模 ML 学習 |
| **S3 (Mountpoint CSI)** | RWX（読み取り中心） | オブジェクトストレージ。POSIX／NFS とは操作の意味が異なる | データレイク、モデル、成果物 |
| **インスタンスストア** | ノードローカル | NVMe、最も低いレイテンシー、**一時的** | キャッシュ、shuffle データ、一時領域 |

RWO は同一ノード上の複数 Pod による利用を許可します。単一 Pod だけが使えるという保証ではありません。io2 Multi-Attach などの例外には、個別のサポートとファイルシステム／アプリケーション側の並行アクセス設計が必要です。Mountpoint for S3 は汎用の POSIX 共有ファイルシステムではありません。ワークロードに必要な更新、rename、ロックの各機能がサポートされるか確認してください。インスタンスストアのデータは再起動後も残ることがありますが、停止または終了時に失われる可能性があります。

## 仕様書を読むだけでなく測定する理由

ストレージは、データシート上の性能と実際の使用感の差が最も大きい領域です。よくある注意点は次のとおりです。

1. **gp2 のバーストクレジット:** ベースラインが 3,000 IOPS 未満のボリュームは、利用可能なクレジットを使ってバーストできます。継続時間は初期クレジット量、容量、負荷によって変わります。容量 100 GiB のボリュームを 3,000 IOPS で使う場合、計算上は約33分です。短時間のテストでは、クレジット消費後の性能を見落とすことがあります。
2. **ボリューム上限とインスタンス上限:** 上のスタック図を参照してください。
3. **iodepth によって結論が変わる:** queue-depth-1 のレイテンシーテストと queue-depth-32 の IOPS テストは、同じボリュームのまったく異なる特性を表します。

[実測 EBS gp2 と gp3 のベンチマーク](./01-ebs-gp2-gp3-benchmark.md)では、fio を使ってこれらの注意点を実証します。

## 参考資料

- [EBS performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EC2 EBS limits](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)
- [Mountpoint S3 semantics](https://github.com/awslabs/mountpoint-s3/blob/main/doc/SEMANTICS.md)
