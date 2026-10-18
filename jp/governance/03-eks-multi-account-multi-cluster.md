# マルチアカウント／マルチクラスタ EKS アーキテクチャ

> **最終更新日**: 2026 年 10 月 12 日

## 1. クラスタ統合のアプローチ

複数のチーム／ドメインのワークロードを EKS に配置する方法は、大きく 4 つあります。

| アプローチ | 構成 |
|---|---|
| 単一の中核 EKS | すべてのワークロードを 1 つのクラスタに配置 |
| 環境ごとの中央 EKS | 本番／非本番環境ごとに 1 クラスタ |
| ドメインごとの EKS | ドメインごとに専用クラスタ |
| **共有＋専用** | 一般的なワークロードは共有クラスタに配置し、強いテナント分離／クォータ／SLO 要件を持つワークロードだけを専用クラスタに配置 |

「共有＋専用」は最初に検討できるアプローチです。以下のしきい値は現場での運用例であり、AWS が定める分割基準ではありません。既定値と実際に適用されたクォータを区別し、SLO、成長、運用能力を合わせて評価してください。

| シグナル | 測定方法 | 分割を検討するしきい値 |
|---|---|---|
| Managed node group 数 | EKS API | 25 / 30 |
| Access entry 数 | EKS API | 2,000 / 3,000 |
| コントロールプレーン API のスロットリング | CloudWatch、429 ログ | 429 が継続して発生 |
| etcd サイズ／オブジェクト数 | 対象 EKS バージョンが公開するコントロールプレーンメトリクスとオブジェクトインベントリ | アラートを設定する前に、メトリクスの利用可否と指針を確認 |
| VPC ごとの NAU（Network Address Usage） | VPC コンソール／CloudWatch | 50,000 / 64,000（または 200,000 / 256,000） |
| アップグレード時の障害範囲 | クラスタにデプロイされた CUJ の数 | 2 つ以上の CUJ があれば分割を検討 |
| アドオンのリリース周期の競合 | チームごとのアドオンバージョン要件の違い | 要件の競合が生じた時点で分割 |

しきい値を超えたらレビューを開始します。クォータ引き上げ、クリーンアップ、分割にかかるコストを比較してください。クラスタを分割する場合は、検証済みの計画とロールバック手順を用意してください。

## 2. A/B EKS Runtime: 2 クラスタに障害範囲を分ける

同じ CUJ（critical user journey）を 2 つの独立した EKS クラスタにデプロイし、一方のクラスタで障害が起きても、もう一方がトラフィックを処理できるようにする構成は、一般に「A/B EKS Runtime」と呼ばれます。これは**AWS が公式に推奨するパターンではありません。組織が自ら検証する必要のある作業仮説です。** 可用性を実際に高めるには、まず以下の条件を満たす必要があります。

### まず、何を障害から守るのかを定義する

EKS のマネージドコントロールプレーンはマルチ AZ です。ARC の zonal shift/autoshift が作用するのはデータプレーンです。A/B は次のようなクラスタ固有の障害を分離できる場合があります。一方、共有 VPC、DNS、アカウント、リージョン、データ依存関係は共有の障害ドメインです。クラスタを 2 つにしただけでは、AZ またはリージョンのレジリエンスは保証されません。

- クラスタのアップグレード失敗
- アドオン（CNI/CoreDNS/CSI）のリグレッション
- Admission webhook のエラー
- クラスタ全体に適用するポリシーの不適切なロールアウト
- コントロールプレーン API のスロットリング

この障害リストを明示的に文書化してください。PoC の成功基準は、「A/B に分割すると、この障害は実際に片側に封じ込められるか」とします。「可用性が向上する」という抽象的な主張では検証できません。

<span id="coredns-is-the-most-common-single-point-of-failure"></span>

### DNS の共有障害モードと容量を確認する

DNS は共有依存関係です。レプリカ数、AZ への分散、容量を確認してください。インシデントデータがない限り、CoreDNS が最も一般的な単一障害点だと順位づけしないでください。Auto Mode と混在ノードの場合、まず実際の DNS 経路を特定します。

- `replicaCount` と `topologySpreadConstraints` によって、レプリカが実際に AZ 間で分散されるか
- CoreDNS アドオンの autoscaling（`{"autoScaling":{"enabled":true}}`）または HPA／cluster-proportional-autoscaler が適用されているか
- 1 つの AZ を停止した場合の QPS／レイテンシーの変化

**DNS、IMDS、NTP を含むトラフィックは、EC2 のリンクローカルサービスの上限である 1,024 パケット/秒を共有します。** VPC DNS ENI の上限と、実際の ENA `linklocal_allowance_exceeded` メトリクスを確認してください。キャッシュと DNS レプリカの配置を評価します。Pod 密度だけでは DNS 障害の原因は特定できません。

### 予備容量を事前に確保しないと ARC zonal shift が停止を引き起こすことがある

AWS のドキュメントにも明示的な注意があります。zonal shift が発生すると、次のことが自動的に行われます。

1. 対象 AZ 内のすべてのノードが cordon され、新たなスケジューリングを受け付けなくなる。
2. Managed node group の AZ リバランスが停止する。
3. その AZ の Pod が EndpointSlice から取り除かれる。
4. ノード／Pod 自体は終了または evict されない。shift を解除すると直ちに戻る。
5. ARC に登録された ALB/NLB は、正常な AZ だけにルーティングする。

**フェイルセーフ動作**: ワークロードのエンドポイントが障害のある AZ にしか存在しない場合、EKS は引き続きその AZ にトラフィックを送ります。つまり、**単一 AZ にだけデプロイされたワークロードは zonal shift で保護されません。**

以下の技術的制約も確認してください。

- **EKS Fargate では機能しません。**
- セルフマネージド Karpenter では **1.12 以降**が必要です。
- EKS Auto Mode では、クラスタで zonal shift を有効にする以外に追加構成は不要です。有効にすると、障害のある AZ で新しいノードのプロビジョニングが停止し、その AZ に影響する consolidation などの自発的な中断も止まり、厳格なスケジューリング要件がその AZ を対象とする Pod のための容量確保も避けます。
- ステートフルワークロードはストレージバックエンドごとに評価してください。EBS PV は AZ に紐付いており、別の AZ に直接アタッチできません。すべての PVC が EBS を使うわけではありません。EFS などのバックエンドでは可用性と復旧の動作が異なります。

> **設計提案**: autoshift の前に、各サービス、DNS、ストレージの N-1 動作を検証してください。フェイルセーフにより単一 AZ のエンドポイントが残る場合があるため、練習で必ず停止するとは限りません。また、そのフェイルセーフは障害のある AZ からサービスを提供できることを保証するものでもありません。

### 予備容量倍率の計算で陥りやすい点

「2 AZ ではおよそ 2 倍、3 AZ（N-1 基準）ではおよそ 1.5 倍の容量を事前に確保する」という計算は、算術としては正しいものの、次の 3 点で誤解しやすいです。

1. **ノード追加の遅延**: placeholder Pod と priority で既存容量を予約できますが、ノードのプロビジョニング、イメージ取得、アプリケーションの起動時間はなくなりません。
2. **正常な AZ の新しい容量が、他の顧客の需要によって制約されるリスク**: これは憶測ではありません。AWS のドキュメントは「AZ が障害状態にある間、正常な AZ に新しいノードを追加できないコンピューティング容量制約のリスク」を明示しています。
3. **依存関係と AZ 配置**: すべての必須 CUJ の各ホップについて、生き残った AZ から到達可能で十分な容量がある必要があります。必要に応じて topology spread、affinity、AZ 間のフォールバックを組み合わせ、厳格な affinity が復旧を妨げないかテストしてください。

### AZ 間コストの最適化

次の順に進めます: 測定 → 最適化 → 残存コストの比較。

1. Flow Logs と ENI/AZ の対応関係を使って、コストが大きい経路を特定する。CUR だけでは送信元／宛先の AZ の組み合わせは分からない。
2. 同一ゾーン内のルーティング、Service の `spec.trafficDistribution`、topology spread、ALB IP ターゲット、NAT／エンドポイントのローカリティ、データのローカリティを評価する。このフィールド名は変更されていません。対象の Kubernetes/EKS バージョンで `PreferClose`、`PreferSameZone`、`PreferSameNode` がサポートされ、feature gate が有効か確認してください。
3. これらを適用した後の残存する AZ 間コストを比較する。

ALB の AZ 間リージョナルデータ転送には追加の転送料金がないため、無効にしてもコスト削減になるとは限りません。ターゲットグループ単位で無効にすると、ターゲットスティッキネスと Lambda ターゲットのサポートがなくなります。AZ が空なら 503 を返すことがあります。エンドポイントはあるが正常ではない AZ では、DNS／ルーティングのフェイルオーバー条件に従います。これらの状態を区別し、AZ ごとの容量を保証できない場合は、有効化された既定値を維持してください。

### アップグレード戦略は A/B を導入する理由に直結する

A/B EKS Runtime を使う本当の理由がアップグレードの分離なら、次の事項を正式に定める必要があります。

- A/B クラスタ間で許容するバージョン差
- 常に片側を先にアップグレードするルール
- Extended support を利用するかどうか

これらがなければ、A/B は単なる「クラスタが 2 つある状態」にすぎず、冗長化の意味を失います。

### Worker の AZ 数とコントロールプレーンのサブネットは別の概念

クラスタの作成には、少なくとも 2 つの異なる AZ 内にサブネットが必要です。ただし、worker ノードを 1 つの AZ にだけ配置することはできます。つまり、EKS 自体は「単一 AZ の worker 構成」を禁止していません。前述の zonal shift の例外ルールとは別に評価してください。

## 3. 完全なワークロード Cell: より強い分離の代替案

A/B EKS Runtime より強い分離が必要な場合は、受信、コンピューティング、データ、必要な依存関係をまとめて「Cell」という単位で分割／複製し、障害範囲をその Cell 内に抑えられます。分割、整合性、容量、運用コストは大幅に増えるため、これは独立したデータ分割と複製に対応できるワークロードに**限って**現実的です。

## 次へ

EKS の可用性設計は、その基盤となる VPC 構成と切り離して考えることはできません → [共有 VPC と接続性](./04-shared-vpc-and-connectivity.md)

## 参考資料

- [EKS クォータ](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
- [EKS のサブネットとマルチ AZ](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
- [EKS ネットワークのコスト最適化](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [EKS zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html)
- [EKS のテナント分離](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html)
- [Availability Zone を使った静的安定性](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [Well-Architected: マルチ AZ](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_fault_isolation_multiaz_region_system.html)
- [ALB ターゲットグループの属性](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB ターゲットグループのヘルス](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [ALB の AZ 間データ転送](https://aws.amazon.com/elasticloadbalancing/faqs/)
- [Amazon DNS クォータ](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Kubernetes Service のトラフィック分散](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution)
