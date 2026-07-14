# Observability Lab パート 1: Infrastructure Setup クイズ

> **最終更新**: February 22, 2026

Observability End-to-End Lab パート 1 で扱ったインフラストラクチャセットアップの概念についての理解を確認しましょう。

---

1. マルチクラスター EKS アーキテクチャにおいて、Managed Cluster と Service Cluster の主な役割の違いは何ですか？
   - A) Managed Cluster はアプリケーションワークロードを実行し、Service Cluster はネットワーキングのみを処理する
   - B) Managed Cluster は Observability およびプラットフォームツールをホストし、Service Cluster はアプリケーションワークロードを実行する
   - C) Service Cluster はすべてのクラスターを管理し、Managed Cluster はテスト用である
   - D) 機能上の違いはなく、互換的に使用できる

<details>
<summary>回答を表示</summary>

**回答: B) Managed Cluster は Observability およびプラットフォームツールをホストし、Service Cluster はアプリケーションワークロードを実行する**

**解説:**
マルチクラスターアーキテクチャでは、Managed Cluster（多くの場合、management または platform cluster と呼ばれます）が、Observability スタック、GitOps ツール（ArgoCD）、プラットフォームコンポーネントなどの共有サービスをホストします。Service Cluster は実際のアプリケーションワークロードを実行します。この分離により、リソース分離とセキュリティ境界が強化され、プラットフォームサービスとアプリケーションワークロードを独立してスケーリングできます。

</details>

---

2. EKS ワークロードで IAM インスタンスプロファイルを使用するよりも、IRSA（IAM Roles for Service Accounts）が推奨される理由は何ですか？
   - A) IRSA はインスタンスプロファイルよりも設定が速い
   - B) IRSA は最小権限の原則に従った Pod レベルの IAM 権限を提供する
   - C) インスタンスプロファイルは AWS で非推奨となっている
   - D) IRSA は Pod ごとに無制限の IAM ポリシーを許可する

<details>
<summary>回答を表示</summary>

**回答: B) IRSA は最小権限の原則に従った Pod レベルの IAM 権限を提供する**

**解説:**
IRSA（IAM Roles for Service Accounts）は、IAM ロールを Kubernetes service account に関連付けることで、きめ細かな Pod レベルの IAM 権限を可能にします。ノード上のすべての Pod に同じ権限を付与するインスタンスプロファイルとは異なり、IRSA では各ワークロードが必要な特定の権限だけを持てるため、最小権限の原則に従えます。これによりセキュリティ態勢が向上し、権限の監査と管理が容易になります。

</details>

---

3. EKS クラスターのプロビジョニングで eksctl ではなく Terraform を選択する際の重要なトレードオフは何ですか？
   - A) Terraform は EKS クラスターをまったく作成できない
   - B) Terraform はより優れた状態管理と Infrastructure-as-Code のプラクティスを提供する一方で、学習曲線がより急である
   - C) eksctl は本番環境により適している
   - D) Terraform は AWS GovCloud リージョンでのみ動作する

<details>
<summary>回答を表示</summary>

**回答: B) Terraform はより優れた状態管理と Infrastructure-as-Code のプラクティスを提供する一方で、学習曲線がより急である**

**解説:**
Terraform は、堅牢な状態管理、ドリフト検出、依存関係グラフを提供し、宣言型 HCL 構文を使用して複数のクラウドプロバイダーで動作します。ただし、HCL の学習と Terraform の概念の理解が必要です。eksctl はよりシンプルな YAML 設定と迅速なクラスター作成を備えた EKS 専用のツールですが、複雑なインフラストラクチャ管理における柔軟性は低くなります。Infrastructure-as-Code のプラクティスと状態管理が重要となる本番環境では、Terraform がよく選択されます。

</details>

---

4. 本番の Observability セットアップにおいて、Aurora PostgreSQL が writer/reader インスタンス構成を使用する理由は何ですか？
   - A) ライセンスコストを削減するため
   - B) 高可用性を実現し、読み取り負荷の高い Observability クエリを書き込み操作から分離するため
   - C) Aurora はこの構成のみをサポートするため
   - D) クロスリージョンレプリケーションのみを有効にするため

<details>
<summary>回答を表示</summary>

**回答: B) 高可用性を実現し、読み取り負荷の高い Observability クエリを書き込み操作から分離するため**

**解説:**
Aurora PostgreSQL の writer/reader 構成では、書き込み操作（メトリクスの取り込み、ログの保存）と読み取り操作（ダッシュボードクエリ、アラートクエリ）を分離します。Observability ワークロードは通常、ダッシュボードの継続的な更新とアラート評価が発生するため、読み取り負荷が高くなります。Reader インスタンスは書き込みパフォーマンスに影響を与えることなく、これらのクエリを処理します。また、この構成は高可用性も提供します。writer に障害が発生した場合、reader を自動的に昇格させることができ、ダウンタイムを最小限に抑えられます。

</details>

---

5. Amazon Managed Service for Prometheus (AMP) ワークスペースを作成する際に設定する必要がある必須コンポーネントは何ですか？
   - A) 必要なのはワークスペース名のみである
   - B) ワークスペース、remote write 権限を持つ IAM ロール、およびセキュアなアクセスのための VPC エンドポイント
   - C) ストレージ用の S3 バケット設定のみ
   - D) ワークスペースと必須の CloudWatch 統合

<details>
<summary>回答を表示</summary>

**回答: B) ワークスペース、remote write 権限を持つ IAM ロール、およびセキュアなアクセスのための VPC エンドポイント**

**解説:**
AMP をセットアップする際は、ワークスペース（Prometheus データ用の論理コンテナ）を作成し、データ取り込み用の `aps:RemoteWrite` 権限を持つ IAM ロールを設定し、必要に応じてプライベートネットワークアクセス用の VPC エンドポイントをセットアップします。IAM ロールは IRSA とともに使用し、collector が認証してメトリクスを書き込めるようにします。VPC エンドポイントにより、トラフィックがパブリックインターネットを通過しないため、セキュリティが向上し、レイテンシーが削減されます。

</details>

---

6. Amazon Managed Grafana (AMG) をデータソースに接続するには、どのような方法を使用できますか？
   - A) Grafana UI による手動設定のみ
   - B) AWS データソース設定、Grafana API プロビジョニング、または Terraform/CloudFormation
   - C) AWS CLI コマンドのみ
   - D) データソースは設定なしで自動的に検出される

<details>
<summary>回答を表示</summary>

**回答: B) AWS データソース設定、Grafana API プロビジョニング、または Terraform/CloudFormation**

**解説:**
AMG はデータソース設定のための複数の方法をサポートしています。AWS ネイティブのデータソース設定（AMP、CloudWatch、X-Ray などの AWS サービスに対する認証を自動処理）、プログラムによるセットアップのための Grafana API ベースのプロビジョニング、および Terraform や CloudFormation などの Infrastructure-as-Code ツールです。この柔軟性により、GitOps 主導の自動化か初期セットアップ時の手動設定かを問わず、チームはワークフローに最適なアプローチを選択できます。

</details>

---

7. マルチクラスターセットアップで Service Cluster を ArgoCD に登録する際に必要な設定は何ですか？
   - A) クラスターエンドポイント URL のみ
   - B) クラスターエンドポイント、認証情報（service account トークンまたは IAM）、およびクラスター名/ラベル
   - C) kubeconfig ファイルパスのみ
   - D) 両方のクラスターが同じ VPC 内にあれば、クラスター登録は自動的に行われる

<details>
<summary>回答を表示</summary>

**回答: B) クラスターエンドポイント、認証情報（service account トークンまたは IAM）、およびクラスター名/ラベル**

**解説:**
ArgoCD に外部クラスターを登録するには、クラスターの API server エンドポイント、認証情報（適切な RBAC 権限を持つ service account トークン、または EKS 用の IAM ベース認証）、およびクラスター名やラベルなどのメタデータが必要です。クラスター名とラベルは、デプロイメントの対象を指定するために ApplicationSets で使用されます。EKS では、長期間有効なトークンの管理を避けられるため、IRSA による IAM ベース認証が推奨されます。

</details>

---

8. ログストレージのために、Amazon OpenSearch Service ドメインを EKS とどのように統合すべきですか？
   - A) OpenSearch は EKS とともに使用できない
   - B) VPC エンドポイント、きめ細かなアクセス制御、およびログシッパー用の IRSA ベース認証を使用する
   - C) IP ホワイトリストを備えたパブリックエンドポイント経由のみで使用する
   - D) OpenSearch 統合には仲介として CloudWatch が必要である

<details>
<summary>回答を表示</summary>

**回答: B) VPC エンドポイント、きめ細かなアクセス制御、およびログシッパー用の IRSA ベース認証を使用する**

**解説:**
EKS と OpenSearch をセキュアに統合するには、プライベートアクセス用の VPC エンドポイントを備えた VPC モードで OpenSearch をデプロイします。インデックスレベルの権限を管理するために、きめ細かなアクセス制御を有効にします。FluentBit や Grafana Alloy などのログシッパーを IRSA で設定し、IAM ロールを使用して認証します。このセットアップにより、ログは VPC 内でセキュアに送信され、アクセスはインデックスレベルで制御され、認証は AWS のセキュリティベストプラクティスに従います。

</details>

---

9. Amazon MWAA (Managed Workflows for Apache Airflow) 環境における S3 DAG バケットの役割は何ですか？
   - A) Airflow の実行ログのみを保存する
   - B) MWAA がワークフローを定義・実行するために読み込む DAG ファイル、プラグイン、requirements を保存する
   - C) MWAA データベースのバックアップとして機能する
   - D) タスク出力の一時ストレージを提供する

<details>
<summary>回答を表示</summary>

**回答: B) MWAA がワークフローを定義・実行するために読み込む DAG ファイル、プラグイン、requirements を保存する**

**解説:**
S3 DAG バケットは、MWAA ワークフロー定義の信頼できる唯一の情報源です。ワークフローを定義する DAG（Directed Acyclic Graph）Python ファイル、Airflow 機能を拡張するカスタムプラグイン、および追加の Python 依存関係用の requirements.txt を保存します。MWAA はこのバケットを継続的に同期し、新規または更新された DAG を自動的に検出して読み込みます。この S3 ベースのアプローチにより、DAG の変更を CI/CD パイプラインを通じてデプロイする GitOps ワークフローが可能になります。

</details>

---

10. Argo Rollouts が Managed Cluster ではなく Service Cluster にインストールされる理由は何ですか？
    - A) Argo Rollouts はクラスター間で通信できない
    - B) Rollouts controller は canary/blue-green デプロイメントのために、管理対象ワークロードへ直接アクセスする必要がある
    - C) より少ないクラスターにインストールすることでライセンスコストを削減できる
    - D) Managed Cluster は CRD のインストールをサポートしていない

<details>
<summary>回答を表示</summary>

**回答: B) Rollouts controller は canary/blue-green デプロイメントのために、管理対象ワークロードへ直接アクセスする必要がある**

**解説:**
Argo Rollouts controller は、canary、blue-green、またはその他のデプロイメント戦略を通じて、アプリケーションの段階的デリバリーを管理します。ワークロードが実行されているクラスター内の ReplicaSets、Services、およびその他のリソースを変更するため、直接アクセスが必要です。ArgoCD は中央の場所からデプロイできますが、Rollouts controller はデプロイメント中にトラフィックシフトと Pod スケーリングをアクティブに管理するため、制御するワークロードと同じ場所で実行する必要があります。これが、Rollouts が各 Service Cluster にインストールされる理由です。

</details>
