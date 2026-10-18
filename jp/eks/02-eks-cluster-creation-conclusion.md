# EKS クラスター作成 - まとめとベストプラクティス

> **最終更新日**: 2026年9月11日

## EKS クラスター作成方法の比較

これまでに、EKS クラスターを作成するさまざまな方法を確認しました。それぞれの利点と欠点を比較します。

ツールを選ぶときは、再現性、レビューのしやすさ、チームのスキル、ライフサイクルの管理主体を考慮してください。どの方法で作成したクラスターにも、ワークロード、ネットワーク、セキュリティの検証が必要です。各リソースの管理主体を 1 つに定め、plan や change set を確認してください。IaC の state と整合させずに手動変更を混在させないでください。

### eksctl

**利点:**
- EKS に特化した簡潔なワークフローを使えます。速度は要求するリソースに左右されます。
- 1 つのコマンドでクラスターを作成できます。
- YAML ファイルによる宣言的な設定に対応します。
- node group や Fargate profile など、さまざまな機能に対応します。

**欠点:**
- 複雑なインフラストラクチャ要件には対応しきれない場合があります。
- 既存インフラストラクチャとの統合が難しいことがあります。

**適した用途:**
- 迅速なプロトタイピング
- 開発／テスト環境
- 設定、所有権、ライフサイクルをレビューできる本番環境

### AWS Management Console

**利点:**
- 視覚的なインターフェイスで理解しやすい
- 手順に沿ってクラスターを作成できる
- さまざまな選択肢を画面上で確認できる

**欠点:**
- 手作業のため自動化が難しい
- 繰り返し作業に時間がかかる
- 設定管理やバージョン管理が難しい

**適した用途:**
- 学習や調査
- 一度限りのクラスター作成
- 小規模なチームやプロジェクト

### AWS CLI

**利点:**
- スクリプトで自動化できる
- 細かな制御が可能
- AWS サービスと統合しやすい

**欠点:**
- コマンドの構造が複雑
- 複数のコマンドを実行する必要がある
- エラー処理が難しい場合がある

**適した用途:**
- 自動化スクリプトの一部
- CI/CD パイプラインとの統合
- 細かな制御が必要な環境

### Terraform

**利点:**
- Infrastructure as Code (IaC)
- state 管理と変更追跡
- さまざまな AWS サービスとの統合
- モジュール化と再利用

**欠点:**
- 習得に時間がかかる
- 初期設定に時間がかかる
- state には保護された保存先、ロック、復旧手段が必要です。ローカル backend 自体に追加インフラストラクチャが必要なわけではありません。

**適した用途:**
- 大規模な本番環境
- 開発、ステージング、本番など複数環境の管理
- 複雑なインフラストラクチャ要件

### AWS CDK

**利点:**
- TypeScript、Python など、慣れたプログラミング言語を使える
- 高水準の抽象化
- コードの再利用とモジュール化
- AWS サービスとの密接な統合

**欠点:**
- 習得に時間がかかる
- デバッグが複雑になることがある
- construct／version によって対応範囲が異なります。合成された CloudFormation と custom resource の動作を確認してください。

**適した用途:**
- 開発者中心の環境
- 複雑なアプリケーションインフラストラクチャ
- 既存アプリケーションコードとの統合

## EKS クラスター作成のベストプラクティス

### ネットワーク

1. **VPC 設計**
   - 少なくとも 2 つの Availability Zone に subnet を配置します。
   - 実際の ingress／egress 要件に基づいて public／private の配置を選びます。private のみの設計では、サービス endpoint や private connectivity を利用できます。
   - 利用可能なアドレス数、CNI の warm／prefix pool、アップグレード時の余裕を計画します。subnet のアドレス範囲と、node の ENI／maxPods 制限を区別してください。
   - 選択した controller の subnet 検出 tag／設定を使います。tag を付けても route やセキュリティ境界は設定されません。

2. **Security Group の設定**
   - 最小権限の原則を適用します。
   - API、kubelet、DNS、webhook、アプリケーションに必要な実際の通信経路を許可します。kubelet が使うのは TCP 10250 であり、範囲の広い任意の ephemeral port 群ではありません。
   - 送信元 IP を制限します。
   - Security Group reference を活用します。

3. **ネットワークポリシー**
   - サポート対象の policy engine を選びます。native VPC CNI policy、または適切な Calico／Cilium 設計を使い、競合する engine を同時に有効化しないでください。
   - Pod 間通信を制限します。
   - positive／negative test で namespace の ingress／egress 制限と DNS を検証します。一致する Kubernetes NetworkPolicy の allow は加算されます。

### セキュリティ

1. **IAM role と policy**
   - 最小権限の原則を適用します。
   - 実行基盤、agent／SDK、trust 要件に応じて EKS Pod Identity または IRSA を使い、アプリケーション権限の範囲を限定します。
   - きめ細かな権限 policy を設定します。

2. **暗号化**
   - EBS volume の暗号化を有効にします。
   - EKS の API data に対する既定の envelope encryption（1.28 以降は KMSv2）と、customer-managed KMS key が必要かを確認します。base64 は暗号化ではありません。
   - TLS で通信中のデータを暗号化します。

3. **認証と認可**
   - 必要に応じて EKS IAM authentication と access entry／access policy を使います。AWS CLI token を使う場合、別のクライアント用 aws-iam-authenticator binary が必ず必要なわけではありません。
   - Kubernetes RBAC と EKS access policy による許可を合わせて確認します。両方で許可された権限は加算されます。
   - RBAC、Pod Security、ネットワーク制御を使って identity と namespace を分離します。namespace だけでは完全なテナント分離になりません。

### スケーラビリティと可用性

1. **Node group の設定**
   - 複数の Availability Zone に node を配置します。
   - 実行基盤の管理主体を明確にします。managed／self-managed node group、Karpenter、Auto Mode、Fargate などがあります。すべての方式が operator 管理の ASG を使うわけではありません。
   - Spot instance を含む、さまざまな instance type を利用します。

2. **Cluster Autoscaler**
   - 必要に応じて互換性のある Cluster Autoscaler／Karpenter release を使います。Auto Mode は独自に capacity を管理します。同じ pool に複数の管理主体を競合させないでください。
   - workload の replica 数によるスケーリングと node のプロビジョニングを区別し、request、schedule できない Pod、capacity 制約を検証します。
   - 選択した controller で disruption／consolidation budget とタイミングを調整します。アプリケーションの drain と復旧をテストしてください。

3. **高可用性の設定**
   - 複数の Availability Zone を利用します。
   - 該当する自発的 eviction には PodDisruptionBudget を使います。node 障害や、強制的な disruption のすべてを防ぐものではありません。
   - 想定する障害シナリオに合わせて replica 数、topology spread、readiness、capacity を設定します。

### 監視とログ

1. **コントロールプレーンのログ**
   - 5 種類の control plane log（api、audit、authenticator、controllerManager、scheduler）について、保持期間、アクセス、コストを考慮します。
   - CloudWatch Logs と統合します。

2. **Node と Pod の監視**
   - 必要な CloudWatch Container Insights／add-on の信号と、サポート対象の実行基盤設定を選びます。
   - Prometheus/Grafana または既存の監視基盤を意図的に利用し、重複収集や未レビューの自動 instrumentation を避けます。
   - custom metric を設定します。

3. **alarm と通知**
   - CloudWatch alarm を設定します。
   - 承認済みの通知先を設定し、配信と管理主体を確認します。subscription が確認済みとは限りません。
   - 重要イベントの通知を設定します。

### コスト最適化

1. **Instance type の選択**
   - workload に適した instance type を選びます。
   - 中断への耐性がある workload では、capacity／障害対応をテストしたうえで Spot を使います。
   - アプリケーション、image、agent、add-on の architecture との互換性を検証してから Graviton を検討します。

2. **Auto Scaling**
   - 需要に応じた自動スケーリングを設定します。
   - scale-down policy を最適化します。
   - スケジュールによるスケーリングを検討します。

3. **リソース request と limit**
   - CPU と memory の適切な request を設定します。
   - workload の動作に合わせて limit を設定します。すべての limit を無償の保護とみなさず、memory OOM と CPU throttling を考慮してください。
   - ResourceQuota と LimitRange を設定します。

4. **Fargate の利用**
   - workload の scheduling、networking、storage、権限制約が合う場合にのみ Fargate を使います。
   - Fargate profile を最適化します。
   - コストと性能を評価します。

## 次のステップ

EKS クラスターを作成したら、次の項目を検討してください。

1. **クラスターのアップグレード戦略を策定する**
   - upstream Kubernetes release だけでなく、EKS のサポートカタログと、使用する add-on／client／node の互換性に基づいて計画します。
   - in-place と replacement cluster の方式を比較します。現在の EKS control plane rollback は条件付きであり、アプリケーションデータは復元しません。
   - アップグレードテストを自動化します。

2. **Disaster Recovery を計画する**
   - RPO／RTO を定義し、アプリケーションデータ、設定、必要な key を backup します。snapshot を作るだけでなく、整合性と restore をテストしてください。
   - replication、DNS／failover、IAM/KMS、コストの前提を明確にした場合に限り、multi-Region 復旧を選びます。
   - 障害シナリオをテストします。

3. **CI/CD pipeline と統合する**
   - GitOps workflow を導入します。
   - deployment pipeline を自動化します。
   - テストと検証を自動化します。

4. **追加サービスを統合する**
   - 選択した実行基盤／ingress 経路で必要な場合は AWS Load Balancer Controller を使います。Auto Mode 管理下の controller と重複させないでください。
   - DNS の管理範囲と IAM 権限を限定して ExternalDNS を使います。
   - Kubernetes 上で証明書発行が必要な場合は cert-manager を使います。ALB の ACM 証明書管理は別の経路です。
   - 実行基盤と provisioning の管理主体に応じて EBS/EFS storage を選びます。Auto Mode の EBS と Fargate の storage 経路は、通常の EC2 add-on とは異なります。

5. **セキュリティを強化する**
   - 脆弱性スキャンを導入します。
   - compliance を監視します。
   - security policy を自動化します。

EKS クラスターの作成は Kubernetes の取り組みの始まりにすぎません。継続的な管理、監視、最適化により、安定して効率的な環境を維持してください。

## 検証に使用した資料

- [EKS のネットワーク要件](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [Private EKS cluster](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [API data の envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)
- [Access policy の権限](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [条件付きクラスター rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

実装の詳細とローカルで確認した例は、[クラスター作成パート 4](02-eks-cluster-creation-part4.md)、[パート 5](02-eks-cluster-creation-part5.md)、[ネットワークパート 2](03-eks-networking-part2.md)を参照してください。本番利用に必要な準備状況は、該当環境での検証と障害／復旧テストを行って確認してください。
