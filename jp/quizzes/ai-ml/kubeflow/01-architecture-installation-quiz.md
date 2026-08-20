# EKS 上の Kubeflow アーキテクチャとインストール クイズ

このクイズでは、Kubeflow のコンポーネントアーキテクチャ、CNCF 卒業、Kubeflow Community Distribution のリリースモデル、EKS 固有のインストールパターン、および Pipelines アーティファクトストレージの IAM アクセスパターンについての理解を確認します。

## 選択問題

1. Kubeflow は 2026 年 8 月 17 日に CNCF でどのようなマイルストーンに到達しましたか？
   - A) CNCF の sandbox プロジェクトとして採択された
   - B) sandbox から incubating ステータスへ移行した
   - C) セキュリティ監査を完了し、steering committee を設立した後、CNCF で最も成熟度の高い階層である graduation に到達した
   - D) 非活動を理由に CNCF によりアーカイブされた

<details>
<summary>回答を表示</summary>

**回答: C) セキュリティ監査を完了し、steering committee を設立した後、CNCF で最も成熟度の高い階層である graduation に到達した**

**解説:**
Kubeflow は 2023 年に incubating プロジェクトとして CNCF に参加し、独立した第三者によるセキュリティ監査を通過し、プロジェクトガバナンスのための正式な steering committee を設置した後、[2026 年 8 月 17 日に graduation に到達しました](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)。graduation は CNCF で最も成熟度の高い階層です。
</details>

2. Kubeflow Community Distribution はどのようなバージョニング方式を使用し、ベースリリースはおおよそどの程度の頻度で出荷されますか？
   - A) セマンティックバージョニング（major.minor.patch）、継続的に出荷
   - B) カレンダーバージョニング（YY.MM.patch）、おおよそ年 2 回
   - C) 個別のリリースを持たない、単一のローリング `latest` タグ
   - D) LTS バージョニング、3 年に 1 回

<details>
<summary>回答を表示</summary>

**回答: B) カレンダーバージョニング（YY.MM.patch）、おおよそ年 2 回**

**解説:**
Kubeflow Community Distribution は YY.MM.patch 形式のカレンダーバージョニングを使用し、年間およそ 2 回のベースリリースを行います。執筆時点で 26.03 リリースが最新のベースリリースです（その後、新しいコンポーネントバージョンを含む 26.03.1 パッチが出荷されています）。
</details>

3. Kubeflow のアーキテクチャにおいて、「Kubeflow Profile」とは何ですか？
   - A) ユーザー個人用 dashboard のテーマおよびレイアウト設定
   - B) Profile Controller により調整される、Kubernetes namespace、RBAC バインディング、リソースクォータ、Istio AuthorizationPolicy オブジェクト
   - C) クラスターにインストールされているコンポーネントを列挙した YAML ファイル
   - D) マネージド Kubeflow ベンダーのみが使用する課金構造

<details>
<summary>回答を表示</summary>

**回答: B) Profile Controller により調整される、Kubernetes namespace、RBAC バインディング、リソースクォータ、Istio AuthorizationPolicy オブジェクト**

**解説:**
Kubeflow Profile はマルチテナンシーの境界です。これは RBAC バインディング、クォータ、Istio authorization policy をまとめた namespace であり、すべてが Profile Controller によって単一の Profile カスタムリソースから調整されます。ほかのコンポーネント（Notebooks、Pipelines、Katib）は、ユーザーの profile namespace 内にリソースを作成します。
</details>

4. `awslabs/kubeflow-manifests` は、Kubeflow のデフォルトの Dex、クラスター内 MySQL、MinIO をどの 3 つの AWS ネイティブサービスに置き換えますか？
   - A) IAM、DynamoDB、EFS
   - B) Cognito、RDS、S3
   - C) Secrets Manager、Aurora Serverless、EBS
   - D) SSO、Redshift、Glacier

<details>
<summary>回答を表示</summary>

**回答: B) Cognito、RDS、S3**

**解説:**
`awslabs/kubeflow-manifests` は、認証用の Dex を Amazon Cognito に、Pipelines/Katib メタデータ用のバンドルされたクラスター内 MySQL を Amazon RDS に、Pipelines アーティファクトストレージ用の MinIO を Amazon S3 に置き換えます。kustomize ベースのマニフェストデプロイと Terraform ベースのデプロイの両方で、このパターンが文書化されています。
</details>

5. 特に KFPv2 において、Kubeflow Pipelines Pod に S3 へのアクセスを付与する IRSA サポートには、どのような文書化された経緯がありますか？
   - A) IRSA は常に、注意事項なしで KFPv2 を完全にサポートしてきた
   - B) IRSA はどの Kubeflow Pipelines バージョンにおいても EKS で利用可能になったことはない
   - C) KFPv2 に対する IRSA サポートは歴史的に遅れており、その間は IAM user ベースの回避策が文書化されていた。一方、IAM-to-pod バインディングのより広い方向性は EKS Pod Identity である
   - D) KFPv2 では IAM を完全に無効化し、匿名の S3 アクセスを使用する必要がある

<details>
<summary>回答を表示</summary>

**回答: C) KFPv2 に対する IRSA サポートは歴史的に遅れており、その間は IAM user ベースの回避策が文書化されていた。一方、IAM-to-pod バインディングのより広い方向性は EKS Pod Identity である**

**解説:**
`kubeflow-manifests` のガイダンスでは、IRSA は KFPv1 ではサポートされているものの、KFPv2 ではまだサポートされていないことが歴史的に注記されており、暫定的な回避策として static credentials を持つ専用 IAM user が推奨されていました。これとは別に、EKS Pod Identity は、一般に EKS 上の新しい IAM-to-pod バインディングでますます推奨されるデフォルトメカニズムとなっています。ただし、KFPv2 固有の Pod Identity サポートの現状は、想定するのではなく最新のドキュメントで確認すべきです。
</details>

6. このドキュメントで説明されている「マネージド代替サービスではなく EKS 上で実行する理由」のトレードオフによると、完全マネージドプラットフォームである SageMaker ではなく EKS 上で Kubeflow を実行することを最も強く支持する条件はどれですか？
   - A) チームが Kubernetes controller や CRD に一切触れずに済ませたい
   - B) チームがすでに EKS 上で混在ワークロードを実行しており、ML でも同じ node pool、autoscaling、observability スタックを共有したい
   - C) チームに Kubernetes の運用経験がまったくない
   - D) チームがポータビリティにかかわらず運用オーバーヘッドを絶対的に最小化したい

<details>
<summary>回答を表示</summary>

**回答: B) チームがすでに EKS 上で混在ワークロードを実行しており、ML でも同じ node pool、autoscaling、observability スタックを共有したい**

**解説:**
EKS 上の Kubeflow が最も正当化されるのは、チームがすでに EKS 上で他のワークロードを運用しており、トレーニング/サービング内部のポータビリティ、ロックイン回避、きめ細かな制御を必要とするとともに、ML のために第 2 の並行した運用モデルを維持することを避けられる場合です。既存の Kubernetes 運用能力を持たないチーム、または最小限の運用オーバーヘッドを優先するチームには、通常、完全マネージドプラットフォームの方が適しています。
</details>

## 短答問題

7. CNCF graduation（2026 年 8 月 17 日発表）が Kubeflow のプロジェクト成熟度について何を示すかを 1 文で説明し、到達のためにプロジェクトが満たす必要のあった具体的な要件を 1 つ挙げてください。

<details>
<summary>回答を表示</summary>

**回答:**
graduation は、CNCF プロジェクトがプロダクションレベルの成熟度、幅広い採用、健全なガバナンスを実証したことを示します。Kubeflow はその到達のため、独立した第三者のセキュリティ監査を受け、プロジェクトガバナンスのための正式な steering committee を設立しました。詳細は [CNCF の発表](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/)を参照してください。
</details>

8. EKS に Kubeflow をデプロイする際、`awslabs/kubeflow-manifests` のデプロイパターンが、クラスター内の MinIO アーティファクトストアとバンドルされた Dex 認証を、それぞれ S3 と Cognito に置き換えるのはなぜですか？

<details>
<summary>回答を表示</summary>

**回答:**
EKS には両方に対応するマネージドで永続性があり IAM 統合されたサービス、すなわちオブジェクトストレージ用の S3 と ID 用の Cognito がすでにあるためです。代わりにバンドルされたクラスター内のサービスを実行すると、AWS がすでに提供している機能を重複させる追加のステートフルサービスを運用することになり、Kubeflow がセルフホスト版から特に必要とする利点は得られません。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/01-architecture-installation.md) | [次のクイズ: Pipelines](./02-pipelines-quiz.md)
