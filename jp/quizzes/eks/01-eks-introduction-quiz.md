# EKS入門クイズ

> **最終更新日**: 2026年10月12日

このクイズでは、Amazon Elastic Kubernetes Service (EKS) の基本的な概念と機能についての理解度を確認します。EKSのアーキテクチャ、コンポーネント、管理方法、料金モデルなどのトピックを扱います。

単独で実行するAPIの例では、`EXAMPLE_CLUSTER`、`EXAMPLE_REGION`、`EXAMPLE_CONTEXT`や、ほかに指定されている変数に、レビュー済みの対象を設定してください。IRSAの例では、既存の`EXAMPLE_NAMESPACE`、必要なバケット/プレフィックスに範囲を限定した`APP_POLICY_ARN`、およびIRSAに対応したAWS SDKを使用するアプリケーションが必要です。2つの演習では、それぞれ専用のクラスターに個別の`EKS_INTRO_*`変数を使用します。

## 多肢選択問題

1. Amazon EKS (Elastic Kubernetes Service) の主な利点は何ですか？
   * A) Kubernetesコントロールプレーンのインフラストラクチャを自分で管理する必要がない
   * B) ほかのマネージドKubernetesサービスより低コストである
   * C) AWSサービスのみを使用できる
   * D) 単一のアベイラビリティーゾーンでしか実行できない

<details>

<summary>解答を表示</summary>

**解答: A) Kubernetesコントロールプレーンのインフラストラクチャを自分で管理する必要がない**

**解説:** Amazon EKS (Elastic Kubernetes Service) の主な利点は、Kubernetesコントロールプレーンのインフラストラクチャを自分で管理する必要がないことです。AWSがKubernetesコントロールプレーンの可用性とスケーラビリティを管理するため、ユーザーはワークロードの実行に専念できます。

EKSの主な利点:

* **マネージドコントロールプレーン**: AWSがコントロールプレーンノード、etcdクラスター、APIサーバーなどを管理します。
* **高可用性**: リージョンのコントロールプレーンは複数のアベイラビリティーゾーンにまたがります。ワークロードの可用性は、引き続きレプリカ、配置、キャパシティ、依存関係に左右されます。
* **マネージドメンテナンス**: AWSがコントロールプレーンにパッチを適用します。マイナーバージョンのアップグレードは運用担当者が計画します。バージョンサポートポリシーに基づく自動アップグレードも実施されます。
* **AWSサービスとの統合**: IAM、VPC、ELB、ECRなど、さまざまなAWSサービスとシームレスに統合されます。
* **標準的なKubernetes**: 準拠したKubernetes APIにより移植性が向上します。ただし、AWS固有のID、ストレージ、統合機能の移行には引き続き作業が必要です。

ほかの選択肢が誤りである理由:

* EKSがほかのマネージドKubernetesサービスより必ず安いとは限りません。実際には、コントロールプレーンに時間単位の料金がかかります。
* EKSではAWSサービスだけでなく、Kubernetes互換のアプリケーションやサービスを実行できます。
* リージョンのEKSコントロールプレーンは複数のアベイラビリティーゾーンにまたがります。ワーカーノードとアプリケーションレプリカは、ユーザーが別途分散させる必要があります。

</details>

2. Amazon EKSクラスターのコントロールプレーンはどこにデプロイされますか？
   * A) ユーザーのVPC内
   * B) AWSが管理するアカウント内で複数のアベイラビリティーゾーンにまたがってデプロイされる
   * C) ユーザーが選択した単一のアベイラビリティーゾーン
   * D) ユーザーのEC2インスタンス上

<details>

<summary>解答を表示</summary>

**解答: B) AWSが管理するアカウント内で複数のアベイラビリティーゾーンにまたがってデプロイされる**

**解説:** Amazon EKSクラスターのコントロールプレーンは、AWSが管理するアカウント内で複数のアベイラビリティーゾーンにまたがってデプロイされます。これはマネージドサービスとしてのEKSの中核的な特徴の1つです。

EKSコントロールプレーンのデプロイに関する主な特徴:

* **AWS管理のインフラストラクチャ**: コントロールプレーンは、AWSが所有および管理するアカウント内で実行されます。
* **マルチAZデプロイ**: リージョンのEKSコントロールプレーンコンポーネントは、複数のアベイラビリティーゾーンに分散されます。
* **自動復旧**: AWSはコントロールプレーンコンポーネントの状態を監視し、障害が発生したコンポーネントを自動的に置き換えます。
* **エンドポイントへのアクセス**: パブリックアクセス、プライベートアクセス、またはその両方を設定できます。プライベートアクセスには、VPCまたは接続先ネットワークからのDNSとルーティングも必要です。
* **自動スケーリング**: 標準のコントロールプレーンキャパシティは自動的に調整されます。オプションのProvisioned Control Planeティアは明示的に選択します。

ほかの選択肢が誤りである理由:

* コントロールプレーンはユーザーのVPC内にはデプロイされません。代わりに、ENI (Elastic Network Interface) を介してユーザーのVPCとAWS管理のVPCの間に接続が確立されます。
* 高可用性を確保するため、コントロールプレーンは単一のアベイラビリティーゾーンではなく、複数のアベイラビリティーゾーンにまたがってデプロイされます。
* コントロールプレーンはAWS管理のインフラストラクチャ上で実行され、ユーザーのEC2インスタンス上では実行されません。

</details>

3. EKSのコンピューティング管理について、誤っている説明はどれですか？
   * A) セルフマネージドEC2ノード
   * B) マネージドノードグループ
   * C) Fargateプロファイル
   * D) Bottlerocketは独立したサーバーレスコンピューティングサービスである

<details>
<summary>解答を表示</summary>

**解答: D) Bottlerocketは独立したサーバーレスコンピューティングサービスである**

Bottlerocketはコンテナノード向けのオペレーティングシステムであり、独立したサーバーレス実行オプションではありません。

1. **セルフマネージドノード**: お客様がEC2/Auto Scalingグループ、AMI、更新、ノード構成を管理します。
2. **マネージドノードグループ**: AWSがプロビジョニングと置き換えのワークフローを管理し、運用担当者がAMI/バージョンの更新を開始します。最小サイズと最大サイズを設定するだけでは、需要に応じたスケーリングは有効になりません。
3. **Fargate**: プロファイルで、分離されたコンピューティング環境で実行するPodを選択します。DaemonSet、GPU、EBSなどの制限を確認してください。
4. **EKS Auto Mode**: ノードのプロビジョニング、スケーリング、置き換えを自動化する、実際のEKS機能です。
5. **Hybrid Nodes**: オンプレミス/エッジのマシンをAWS管理のコントロールプレーンに接続します。

従来型のEC2ノードでは、需要に応じたスケーリングのために、Cluster AutoscalerまたはセルフマネージドKarpenterを別途構成できます。

</details>

4. 従来型のEC2ベースのEKSノードにおけるデフォルトのCNIは何ですか？
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>解答を表示</summary>

**解答: C) AWS VPC CNI**

**解説:** Amazon EKSクラスターでPodネットワーキングにデフォルトで使用されるCNI (Container Network Interface) プラグインはAWS VPC CNIです。このプラグインは、Amazon VPCネットワーキングとKubernetes Podを直接統合します。

AWS VPC CNIの主な機能:

* **VPCネイティブなIPアドレス割り当て**: PodにはVPCから直接IPアドレスが割り当てられ、VPC内のほかのリソースと同じネットワーク空間に配置されます。
* **セカンダリIPアドレスの使用**: 各ノードのElastic Network Interface (ENI) に関連付けられたセカンダリIPアドレスをPodに割り当てます。
* **セキュリティグループとの統合**: Pod用セキュリティグループには、サポート対象インスタンス、VPCリソースコントローラーの権限、CNIの構成、SecurityGroupPolicyが必要です。
* **VPCフローログでの可視性**: PodのトラフィックはVPCフローログで確認できます。
* **AWSネットワーキング機能の活用**: VPCピアリング、Transit Gateway、PrivateLinkなどの機能をPodから直接利用できます。

AWS VPC CNIはオープンソースプロジェクトです。コードはGitHubで確認できます: https://github.com/aws/amazon-vpc-cni-k8s

EC2ノードで代替CNIを使用する場合は、それぞれの互換性とサポート状況を確認する必要があります。FargateとAuto Modeでは任意のCNIへの置き換えはサポートされません。Hybrid Nodesでは互換性のあるオンプレミスCNIが必要です。`hostNetwork`を使用するPodはノードのネットワーキングを共有します。

</details>

5. IAM IDにEKS Kubernetes APIへのアクセスを付与するには、どうすればよいですか？
   * A) すべてのIAMユーザーをServiceAccountだけで認証する
   * B) アクセスエントリを使用したIAM認証と、アクセス用ポリシーおよび/またはKubernetes RBACを使う
   * C) EKS IAMポリシーによって、すべてのKubernetesリソースへの権限が自動的に付与される
   * D) Cognitoをすべてのクラスターに自動的に接続する

<details>
<summary>解答を表示</summary>

**解答: B) アクセスエントリを使用したIAM認証と、アクセス用ポリシーおよび/またはKubernetes RBACを使う**

Kubernetes APIへのIAMアクセスと、PodによるAWS APIへのアクセスは別の経路です。

1. `aws eks get-token`は、IAM認証情報で署名された認証トークンを作成します。
2. EKSがIAM IDを認証します。新しいアクセス構成には**アクセスエントリ**を使用してください。
3. EKSアクセス用ポリシーを関連付けるか、Kubernetesグループを指定してRoleBinding/ClusterRoleBindingを作成します。RBACとEKSオーソライザーは許可を加算します。どちらもリクエストを許可しない場合、そのリクエストは拒否されます。
4. 従来の`aws-auth` ConfigMapは非推奨です。既存のマッピングがすべて自動的に移行されるわけではないため、アクセスエントリへの移行時に各IDと権限を確認してください。

IAMポリシーはEKSサービスAPIへの呼び出しを制御します。EKSアクセス用ポリシーはKubernetes権限のテンプレートであり、IAMポリシーではありません。IRSA/Pod Identityは、ワークロードにAWSの権限を別途付与します。Kubernetes ServiceAccountトークンと構成済みのOIDCプロバイダーを使用して、Kubernetesに認証することもできます。IAMだけが認証方式ではありません。

</details>

6. Kubernetes ServiceAccountに一時的なAWS認証情報を付与するために、OIDCフェデレーション関係を使用するのはどれですか？
   * A) EC2インスタンスプロファイルを使ってノードにIAMロールを付与する
   * B) Podの環境変数に長期有効なAWSアクセスキーを埋め込む
   * C) IAMロールをKubernetes ServiceAccountにリンクする (IRSA)
   * D) AWS認証情報をKubernetes Secretsに保存してマウントする

<details>

<summary>解答を表示</summary>

**解答: C) IAMロールをKubernetes ServiceAccountにリンクする (IRSA)**

IRSAでは、クラスターのOIDCプロバイダーを介してServiceAccountトークンを交換し、一時的なAWS認証情報を取得します。信頼ポリシーの対象をnamespace/ServiceAccountおよび`aud=sts.amazonaws.com`に限定してください。EKS Pod Identityも一時的な認証情報を提供しますが、別途OIDCプロバイダーを必要としません。コンピューティング環境、エージェント、SDKの要件を確認してください。この例ではIRSA方式を示します。

IRSAの主な利点:

* **最小権限の原則**: 各アプリケーションに必要な最小限の権限だけを付与できます。
* **権限の分離**: 同じノード上で実行される別々のPodに、異なるIAM権限を付与できます。
* **認証情報管理の簡素化**: AWS認証情報を直接管理する必要がありません。
* **セキュリティの強化**: 認証情報をコードや構成にハードコードしません。

IRSAの設定方法:

1. EKSクラスターにOpenID Connect (OIDC) プロバイダーを関連付けます。

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" --approve
    ```
2. ServiceAccount用のIAMロールを作成します。

    ```bash
    eksctl create iamserviceaccount \
      --name=app-sa \
      --namespace="${EXAMPLE_NAMESPACE:?}" \
      --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" \
      --attach-policy-arn="${APP_POLICY_ARN:?Use a reviewed policy scoped to the required bucket/prefix}" \
      --approve
    ```
3. 同じnamespace内のPodでServiceAccountを指定します。これはテンプレートです。イメージをIRSA互換SDKを使用するアプリケーションのものに置き換え、`-n "$EXAMPLE_NAMESPACE"`を指定して適用してください。

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: app-sa
      containers:
      - name: my-container
        image: registry.example.com/team/app:reviewed
    ```

ほかの選択肢が誤りである理由:

* IMDSにアクセスできるPodは、ノードロールの認証情報を取得する場合があります。IMDSへのアクセスを制限し、ワークロード固有のロールを使用してください。IRSAだけではそのアクセスをブロックできません。
* Podの環境変数に長期有効なアクセスキーを埋め込むと、漏えいとローテーションのリスクが高まります。IRSA/Pod Identityの認証情報プロバイダー環境変数は、これとは異なる仕組みです。
* AWS認証情報をKubernetes Secretsに保存すると、認証情報管理の負担が増え、ローテーションも複雑になります。

</details>

7. Amazon EKSクラスターのログ機能について、正しい説明はどれですか？
   * A) すべてのログがデフォルトでCloudWatch Logsに送信される
   * B) コントロールプレーンのログは、オプションでCloudWatch Logsに送信できる
   * C) ワーカーノードのログだけをCloudWatch Logsに送信できる
   * D) EKSにはログ機能がない

<details>

<summary>解答を表示</summary>

**解答: B) コントロールプレーンのログは、オプションでCloudWatch Logsに送信できる**

**解説:** Amazon EKSクラスターでは、コントロールプレーンのログをオプションでCloudWatch Logsに送信できます。この機能はデフォルトで無効になっており、必要なログタイプを選んで有効化できます。

EKSコントロールプレーンのログ記録機能:

* **任意で有効化**: クラスター作成時にも、既存のクラスターにも有効化できます。
* **ログタイプの選択**: 次の中から必要なログタイプだけを選択できます。
  * APIサーバー (api)
  * 監査 (audit)
  * 認証機能 (authenticator)
  * コントローラーマネージャー (controllerManager)
  * スケジューラー (scheduler)
* **CloudWatch Logsとの統合**: 選択したログは、保存、分析、監視のためにAWS CloudWatch Logsに送信されます。
* **コストに関する考慮事項**: CloudWatch Logsの取り込み、保持、クエリに料金がかかる場合があります。

ログを有効にする方法:

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region "${EXAMPLE_REGION:?}" \
    --name "${EXAMPLE_CLUSTER:?}" \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
```

ワーカーノードのログ:

* ワーカーノードのログは、EKSコントロールプレーンのログ機能には含まれません。
* ワーカーノードのログをCloudWatch Logsに送信するには、CloudWatchエージェントをインストールするか、Fluentd/Fluent Bitなどのログソリューションを構成する必要があります。

ほかの選択肢が誤りである理由:

* すべてのログがデフォルトでCloudWatch Logsに送信されるわけではありません。ユーザーが明示的に有効化する必要があります。
* CloudWatch Logsに送信できるのがワーカーノードのログだけというわけではありません。コントロールプレーンのログも送信できます。
* EKSにはコントロールプレーンのログ機能があります。

</details>

8. Amazon EKSクラスターのコスト項目ではないものはどれですか？
   * A) EKSコントロールプレーンの時間単位料金
   * B) ワーカーノード用EC2インスタンスの料金
   * C) Fargate Podの実行料金
   * D) Kubernetesのライセンス料

<details>

<summary>解答を表示</summary>

**解答: D) Kubernetesのライセンス料**

**解説:** Kubernetesのライセンス料は、Amazon EKSクラスターのコスト項目ではありません。KubernetesはCloud Native Computing Foundation (CNCF) が管理するオープンソースソフトウェアであり、Apache 2.0ライセンスのもとで無料で使用できます。そのため、EKSを使用してもKubernetesのライセンス料は別途発生しません。

Amazon EKSクラスターの実際のコスト項目:

1. **EKSコントロールプレーンの時間単位料金**:
   * 標準サポートと延長サポートではクラスター料金が異なります。オプションのProvisioned Control Planeティアには追加料金がかかります。
   * EKSクラスターはリージョンリソースです。複数リージョンにデプロイする場合は、クラスターと料金がそれぞれ必要です。
   * Auto Mode、EKS Capabilities、Hybrid Nodes、AWSインフラストラクチャの料金も個別に考慮してください。
2. **ワーカーノード用EC2インスタンスの料金**:
   * セルフマネージドまたはマネージドノードグループで使用するEC2インスタンスには料金が発生します。
   * 料金はインスタンスタイプ、サイズ、数、実行時間によって異なります。
   * リザーブドインスタンス、Savings Plans、Spotインスタンスを活用してコストを最適化できます。
3. **Fargate Podの実行料金**:
   * Fargateを使用する場合、Podに割り当てられたvCPUとメモリのリソースに基づいて料金が発生します。
   * Linux Fargateの課金はイメージのダウンロード開始時に始まり、秒単位に切り上げられ、最低1分が適用されます。要求されたリソースは、サポートされている構成単位に切り上げられます。
   * プロビジョニング済みの総キャパシティ、使用率、運用負荷を比較してください。FargateとEC2のどちらかが常に安いとは限りません。
4. **その他のAWSリソースの料金**:
   * EBSボリューム
   * ロードバランサー (NLB、ALB)
   * CloudWatchのログとメトリクス
   * NAT Gateway
   * データ転送

コスト最適化の方法:

* 適切なインスタンスタイプを選択する
* オートスケーリングを構成する
* Spotインスタンスを使用する
* クラスターの自動化とスケジュールに基づくスケーリング
* リソースのrequestsとlimitsを最適化する
* コストを監視して分析する

</details>

9. Auto Modeを使用しない従来型のEKSクラスターで、ALB/NLBとの宣言的な統合を提供するのはどれですか？
   * A) 組み込みのEKSロードバランサーを使用する
   * B) Kubernetes ServiceリソースをAWS Load Balancer Controllerと統合する
   * C) EC2ロードバランサーを手動で作成して構成する
   * D) EKSはロードバランシングをサポートしていない

<details>

<summary>解答を表示</summary>

**解答: B) Kubernetes ServiceリソースをAWS Load Balancer Controllerと統合する**

**解説:** Amazon EKSクラスターでロードバランシングを実装する正しい方法は、Kubernetes ServiceリソースをAWS Load Balancer Controllerと統合することです。この方法では、Kubernetesの宣言的なリソース管理とAWSのロードバランシング機能を組み合わせます。

EKSでロードバランシングを実装する方法:

1. **デフォルトのLoadBalancerタイプのService**:

   * 選択されるコントローラーによってロードバランサーが決まります。この例では、インストール済みで使用が許可されたAWS LBCを`service.k8s.aws/nlb`で明示的に選択します。従来の統合ではCLBが作成される場合があります。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2. **AWS Load Balancer Controller**:

   * Application Load Balancer (ALB) とNetwork Load Balancer (NLB) を管理する高度な機能を利用するには、AWS Load Balancer Controllerをインストールします。
   * Ingressリソースを通じてALBをプロビジョニングおよび構成できます。
   * アノテーションを通じて、さまざまなロードバランサー属性を構成できます。

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
    spec:
      ingressClassName: alb
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
    ```
3. **Serviceアノテーション**:

   * Serviceにアノテーションを追加して、ロードバランサーのタイプと構成を指定できます。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
        service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      selector:
        app: my-app
      ports:
      - port: 80
        targetPort: 8080
    ```

ほかの選択肢が誤りである理由:

* Auto Modeは`eks.amazonaws.com/nlb`を含む異なるクラスを使って、マネージドロードバランシングを提供します。クラスター内にAWS LBCをインストールする必要はありません。両者のクラスや、サポート対象外のアノテーションを混在させないでください。
* EC2ロードバランサーを手動で作成して構成することもできますが、Kubernetesの宣言的なアプローチに合わず、管理が複雑になります。
* EKSはロードバランシングを全面的にサポートしています。

</details>

10. Amazon EKSクラスターでストレージを管理する有効な方法ではないものはどれですか？
    * A) EBS CSIドライバーを使用してEBSボリュームをプロビジョニングする
    * B) EFS CSIドライバーを使用してEFSファイルシステムをマウントする
    * C) Fargate PodにEBSボリュームをマウントする
    * D) FSx for Lustre CSIドライバーを使用して高性能ファイルシステムに接続する

<details>

<summary>解答を表示</summary>

**解答: C) Fargate PodにEBSボリュームをマウントする**

FargateではEBSボリュームをマウントできません。従来型のEC2ノードでは、インストール済みのEBS CSIドライバーとIAM権限を使用します。Auto Modeでは、マネージドEBSプロビジョニングを`ebs.csi.eks.amazonaws.com`を通じて提供します。これは従来型の`ebs.csi.aws.com`ドライバーとは異なります。

Amazon EKSクラスターでストレージを管理する実際の方法:

1. **EBS CSIドライバー**:

   * Amazon EBS (Elastic Block Store) ボリュームをKubernetes Podに接続できます。
   * ブロックストレージを必要とするアプリケーション (データベースなど) に適しています。
   * StorageClassで許可されている場合、動的プロビジョニング、スナップショットコントローラーを使用したスナップショット、拡張をサポートします。
   * EBSはAZスコープです。ReadWriteOnceは1つのノードからの読み書きマウントを意味し、1つのPodだけを意味するわけではありません。同じノード上の複数のPodがボリュームを使用できる場合があります。アクセスモードによってAZが決まるわけではありません。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
2. **EFS CSIドライバー**:

   * Amazon EFS (Elastic File System) をKubernetes Podにマウントできます。
   * 複数のPodから同時にアクセスする必要がある共有ファイルシステムに適しています。
   * 複数のアベイラビリティーゾーンからアクセスできます (ReadWriteManyアクセスモード)。
   * Webサーバー、CMS、CI/CDパイプラインなどに適しています。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    ```
3. **FSx for Lustre CSIドライバー**:

   * Amazon FSx for LustreをKubernetes Podに接続できます。
   * ハイパフォーマンスコンピューティング、機械学習、ビッグデータ分析など、高性能なワークロードに適しています。
   * 高スループットと低レイテンシーを提供します。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: fsx-sc
    provisioner: fsx.csi.aws.com
    parameters:
      subnetId: subnet-0123456789abcdef0
      securityGroupIds: sg-0123456789abcdef0
      deploymentType: PERSISTENT_1
      automaticBackupRetentionDays: "1"
      dailyAutomaticBackupStartTime: "00:00"
      perUnitStorageThroughput: "200"
    ```
   容量は`storageCapacity` StorageClassパラメーターではなく、PVCの`spec.resources.requests.storage` (例: `1200Gi`) で指定してください。デプロイメント固有の容量単位、サブネット/セキュリティグループ、Lustreクライアントの互換性、ドライバーのIAM権限を確認してください。

4. **その他のストレージオプション**:
   * CSIドライバーまたはS3マウンターを介したAmazon S3 (Simple Storage Service)
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * サードパーティーのストレージソリューション (Portworx、Rookなど)

ストレージ管理のベストプラクティス:

* ワークロードの要件に合ったストレージタイプを選択する
* 動的プロビジョニング用にStorageClassを構成する
* バックアップおよび復旧戦略を策定する
* ストレージのパフォーマンスを監視する
* コスト最適化のために、適切なストレージクラスとサイズを選択する

</details>

## ハンズオン演習

### 演習1: EKSクラスターの作成と構成

**シナリオ:** あなたは勤務先のDevOpsエンジニアで、開発チーム用にAmazon EKSクラスターをセットアップする必要があります。このクラスターは開発環境向けであり、必要な機能をすべて備えつつ、コスト効率のよい構成にします。

**要件:**

1. コスト効率のよいEKSクラスターを作成する
2. 適切なノードグループを構成する
3. 基本的なモニタリングを設定する
4. クラスターへのkubectlアクセスを構成する

**解答:**

<details>
<summary>解答を表示</summary>

これらのデプロイコマンドを実行すると、料金が発生するAWSリソースが作成されます。監査時には実行していません。Bash、最新のAWS CLI v2、kubectl 1.36、Helmを準備し、OS/CPUアーキテクチャとチェックサムを確認するため、[公式のeksctlインストール手順](https://eksctl.io/installation/)を使用してください。この例はeksctl 0.230.0のスキーマとEKS 1.36を基準にレビューしたものであり、本番環境で検証済みの構成ではありません。

1つのシェルで手順を実行し、コマンドが失敗した場合は停止してください。`EKS_INTRO_ADMIN_CIDR`には、通常は`/32`を指定して、承認済みクライアントの実際の外部IPv4 CIDRを設定します。この新しいクラスターは、プライベートノード/プライベートAPIアクセスに加えて、制限付きのパブリックAPIアクセスを使用します。単一のNAT gatewayは開発ラボ向けの選択であり、本番環境の可用性設計ではありません。クラスター作成者への管理者アクセスは、この専用ラボの初期セットアップのみを目的としています。

**1. 専用クラスターを作成する**

```bash
# Use a dedicated nonproduction AWS account/role and an approved region.
eksctl version  # Example tool baseline: 0.230.0
aws --version
kubectl version --client
helm version

EKS_INTRO_DIR=$(mktemp -d /tmp/eks-intro.XXXXXX)
: "${EKS_INTRO_DIR:?}"
EKS_INTRO_CLUSTER=$(basename "$EKS_INTRO_DIR" | tr '[:upper:].' '[:lower:]-')
EKS_INTRO_REGION=us-west-2
: "${EKS_INTRO_ADMIN_CIDR:?Set your approved client egress IPv4 CIDR, normally /32}"
EKS_INTRO_KUBECONFIG="$EKS_INTRO_DIR/kubeconfig"
unset EKS_INTRO_CLUSTER_ARN EKS_INTRO_POLICY_ARN
aws sts get-caller-identity

cat > "$EKS_INTRO_DIR/eks-cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_INTRO_CLUSTER}
  region: ${EKS_INTRO_REGION}
  version: "1.36"
  tags:
    docs-lab: ${EKS_INTRO_CLUSTER}
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: true
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${EKS_INTRO_ADMIN_CIDR}"]
  nat:
    gateway: Single
managedNodeGroups:
- name: ng-1
  amiFamily: AmazonLinux2023
  instanceType: t3.medium
  privateNetworking: true
  disableIMDSv1: true
  disablePodIMDS: true
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

# Inspect the file, account, allowed CIDR and projected costs before provisioning.
cat "$EKS_INTRO_DIR/eks-cluster.yaml"
eksctl create cluster -f "$EKS_INTRO_DIR/eks-cluster.yaml" \
  --kubeconfig "$EKS_INTRO_KUBECONFIG" &&
  EKS_INTRO_CLUSTER_ARN=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
    --region "$EKS_INTRO_REGION" --query cluster.arn --output text)
: "${EKS_INTRO_CLUSTER_ARN:?Cluster creation/verification did not complete}"
```

作成に失敗した場合は、この一意の名前に対応するCloudFormationスタック/リソースを調査して削除してから、同じ名前を再利用してください。`minSize`/`maxSize`は範囲を設定するだけで、需要に応じたノードオートスケーラーはインストールされません。t3.mediumはあくまで一例です。キャパシティ、CPUクレジット、リージョンごとの料金を確認してください。

**2. 専用kubeconfigと接続確認**

```bash
aws eks update-kubeconfig --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --kubeconfig "${EKS_INTRO_KUBECONFIG:?}"
intro_kubectl() {
  kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" "$@"
}
intro_kubectl get nodes
intro_kubectl cluster-info
```

**3. 基本的なリソースメトリクス**

Metrics Server 0.9.xはKubernetes 1.34以降をサポートします。これはリソースメトリクスを提供するものであり、ログ記録や長期モニタリングを提供するものではありません。TLS検証を無効にせずに、kubelet証明書とネットワーク接続を確認してください。

```bash
intro_kubectl get pods -n kube-system

# Fresh lab cluster only: do not overwrite an existing managed installation.
curl -fL https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml \
  -o "${EKS_INTRO_DIR:?}/metrics-server.yaml" &&
  intro_kubectl apply -f "$EKS_INTRO_DIR/metrics-server.yaml"
intro_kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s
intro_kubectl top nodes
```

**4. AWS Load Balancer Controllerをインストールする**

ポリシー、コントローラー、チャートのバージョンは3.5.0に固定されています。無関係なアドオン権限をすべてのノードに付与する代わりに、専用のIRSAロールを使用してください。IMDSによる検出に依存しないよう、リージョンとVPCを明示的に指定します。サブネットタグ、セキュリティグループ、サービスクォータは別途確認してください。

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use the new lab cluster}"
curl -fL https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json \
  -o "${EKS_INTRO_DIR:?}/lbc-policy.json" || exit 1
# Inspect the pinned policy before creating this lab-owned IAM policy.
EKS_INTRO_POLICY_ARN=$(aws iam create-policy \
  --policy-name "${EKS_INTRO_CLUSTER:?}-lbc" \
  --policy-document "file://$EKS_INTRO_DIR/lbc-policy.json" \
  --query Policy.Arn --output text)
: "${EKS_INTRO_POLICY_ARN:?Policy creation failed}"

# iam.withOIDC created the cluster OIDC provider in step1.
eksctl create iamserviceaccount \
  --cluster="$EKS_INTRO_CLUSTER" --region="${EKS_INTRO_REGION:?}" \
  --namespace=kube-system --name=aws-load-balancer-controller \
  --attach-policy-arn="$EKS_INTRO_POLICY_ARN" --approve

EKS_INTRO_VPC_ID=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query cluster.resourcesVpcConfig.vpcId --output text)
: "${EKS_INTRO_VPC_ID:?}"
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" install aws-load-balancer-controller \
  eks/aws-load-balancer-controller --version 3.5.0 -n kube-system \
  --set clusterName="$EKS_INTRO_CLUSTER" \
  --set region="$EKS_INTRO_REGION" --set vpcId="$EKS_INTRO_VPC_ID" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait --timeout 5m
```

**5. クラスターの状態を確認する**

```bash
intro_kubectl get nodes -o wide
intro_kubectl get pods -n kube-system
intro_kubectl get events --sort-by='.lastTimestamp'
intro_kubectl cluster-info
```

**6. ローカルのポートフォワーディングを使って基本的なアプリを確認する**

```bash
intro_kubectl create namespace intro-smoke
intro_kubectl -n intro-smoke create deployment nginx --image=nginx:1.30.6-alpine
intro_kubectl -n intro-smoke rollout status deployment/nginx --timeout=180s
intro_kubectl -n intro-smoke expose deployment nginx --port=80 --type=ClusterIP
intro_kubectl -n intro-smoke get deployment,service
# Run in a separate terminal using the same dedicated kubeconfig.
kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" -n intro-smoke \
  port-forward --address 127.0.0.1 service/nginx 8080:80
```

ポートフォワーディングの実行中に`http://127.0.0.1:8080`を開きます。停止するにはCtrl-Cを押してください。次の演習では、外部からのALBアクセスを構成します。2つの演習が終わったら、クリーンアップ手順を実行してください。想定される動作やコスト削減効果は、監査で測定した結果ではありません。

</details>

### 演習2: EKSクラスターへのアプリケーションのデプロイとServiceの公開

**シナリオ:** チームはマイクロサービスアーキテクチャに基づくWebアプリケーションを開発しました。このアプリケーションをEKSクラスターにデプロイし、外部からアクセスできるようにする必要があります。

**要件:**

1. フロントエンドとバックエンドのServiceをデプロイする
2. Service間通信を構成する
3. Ingressコントローラーを通じた外部アクセスを構成する
4. 基本的なスケーリングを設定する

**解答:**

<details>
<summary>解答を表示</summary>

演習1で使用した専用クラスターとシェル変数、AWS LBC/IngressClass `alb`、正常に動作しているMetrics Serverを使用してください。このHTTPデモが返すのは公開用のダミーレスポンスのみで、ALBへのアクセスは選択したクライアントCIDRに制限されています。アプリケーション認証、TLS、本番環境での負荷検証は実装していません。

**1. namespaceを作成する**

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Complete exercise1 first}"
unset EKS_INTRO_WEB_UID
EKS_INTRO_WEB_UID=$(intro_kubectl create namespace web-app -o jsonpath='{.metadata.uid}')
: "${EKS_INTRO_WEB_UID:?Stop if this namespace already exists}"
```

**2. バックエンドを構成する**

ポート80でリッスンし、`/api`を含むパスに対してダミーJSONを返すようにNGINXを構成します。

```bash
cat > "${EKS_INTRO_DIR:?}/backend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location / {
            default_type application/json;
            return 200 '{"service":"backend","example":true}\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: backend
        image: nginx:1.30.6-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: backend-config
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: web-app
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/backend-deployment.yaml"
```

**3. フロントエンドとService間通信を構成する**

標準のNGINXイメージは`BACKEND_URL`を使用しません。この明示的なNGINX構成では、`/proxy-api/`を`backend-service`にプロキシし、実際のService間通信経路を作成します。

```bash
cat > "${EKS_INTRO_DIR:?}/frontend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location /proxy-api/ {
            proxy_pass http://backend-service/;
        }
        location / {
            default_type text/plain;
            return 200 'frontend demo\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: frontend
        image: nginx:1.30.6-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: frontend-config
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: web-app
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/frontend-deployment.yaml"
```

**4. AWS LBC Ingressを作成する**

ALBが`/api`を自動的に取り除くことはありません。このバックエンドはパスを直接処理します。`/`と`/proxy-api/`はフロントエンドに転送されます。

```bash
cat > "${EKS_INTRO_DIR:?}/ingress.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
    alb.ingress.kubernetes.io/inbound-cidrs: ${EKS_INTRO_ADMIN_CIDR:?}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/ingress.yaml"
```

**5. HPAを構成する**

CPU使用率はrequestsを基準に測定されます。HPAが変更するのはPodのレプリカ数であり、ノード数ではありません。また、Metrics Serverとノードの余剰キャパシティが必要です。

```bash
cat > "${EKS_INTRO_DIR:?}/hpa.yaml" << 'EOF'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/hpa.yaml"
```

**6. ルーティングと状態を確認する**

ALBホスト名が存在しても、ターゲットが正常であることの証明にはなりません。リクエストに失敗した場合は、イベント、ターゲットのヘルス状態、セキュリティグループ、クライアントCIDRを調べてください。

```bash
intro_kubectl -n web-app rollout status deployment/backend --timeout=180s
intro_kubectl -n web-app rollout status deployment/frontend --timeout=180s
intro_kubectl -n web-app get deployments,services,ingress,hpa
intro_kubectl -n web-app describe ingress web-app-ingress
ALB_ADDRESS=$(intro_kubectl -n web-app get ingress web-app-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
: "${ALB_ADDRESS:?Wait for ALB provisioning and inspect events}"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/api"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/proxy-api/"
```

**7. 上限を設けた負荷を観察する**

この負荷サンプルでは、CPUターゲットを超えることやHPAが起動することは保証されません。静的なNGINXレスポンスではCPU使用率が低い可能性があり、フロントエンドのルートへのリクエストはバックエンドに負荷をかけません。実際にスケーリングが行われるかどうかは、メトリクス、HPAの状態、Pending Podを確認してください。

```bash
# Only target the lab ALB whose ownership and health you checked above.
: "${ALB_ADDRESS:?}"
ab -n 1000 -c 10 -s 10 "http://$ALB_ADDRESS/"
intro_kubectl -n web-app get hpa
intro_kubectl -n web-app top pods
intro_kubectl -n web-app get events --sort-by='.lastTimestamp'
# Optional observation; Ctrl-C stops watching, not the HPA.
intro_kubectl -n web-app get hpa -w
```

</details>

### 演習リソースをクリーンアップする

アカウント、ARN、タグが専用ラボクラスターを示していることを確認してください。コントローラーを削除する前にアプリケーションロードバランサーを削除し、finalizerの処理完了を待ちます。タイムアウトした場合は、finalizerを削除するのではなく、コントローラーのエラーを調査してください。

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use only the dedicated cluster created in exercise1}"
EKS_INTRO_CLEANUP_READY=false
current_arn=$(aws eks describe-cluster --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --query cluster.arn --output text)
current_tag=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query 'cluster.tags."docs-lab"' --output text)
if [[ "$current_arn" = "$EKS_INTRO_CLUSTER_ARN" && "$current_tag" = "$EKS_INTRO_CLUSTER" ]]; then
  # Keep the controller running until it removes ALB resources/finalizers.
  intro_kubectl -n web-app delete ingress web-app-ingress --ignore-not-found --wait=true --timeout=180s &&
    intro_kubectl delete namespace web-app intro-smoke --ignore-not-found --wait=true --timeout=180s &&
    EKS_INTRO_CLEANUP_READY=true
else
  printf 'Ownership check failed; stop cleanup and inspect the selected account/cluster\n' >&2
fi
```

所有権の確認とIngress/namespaceの削除が成功した後にのみ続行してください。IAMロールスタックの削除とポリシーのデタッチが完了したことを確認してから、ポリシーを削除します。

```bash
if [[ ${EKS_INTRO_CLEANUP_READY:-false} = true ]]; then
  helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" uninstall aws-load-balancer-controller -n kube-system
  eksctl delete iamserviceaccount --cluster="${EKS_INTRO_CLUSTER:?}" \
    --region="${EKS_INTRO_REGION:?}" --namespace=kube-system --name=aws-load-balancer-controller --approve --wait
  # Wait for the related IAM-role stack deletion to finish before deleting its policy.
  aws iam list-entities-for-policy --policy-arn "${EKS_INTRO_POLICY_ARN:?}"
  # Continue only when no attachment remains.
  aws iam delete-policy --policy-arn "$EKS_INTRO_POLICY_ARN" &&
    eksctl delete cluster --config-file="${EKS_INTRO_DIR:?}/eks-cluster.yaml" --wait
else
  printf 'Complete ownership and load balancer cleanup checks first\n' >&2
fi
```

CloudFormationの削除と、残存するロードバランサー、セキュリティグループ、NAT、EBS、ログ保持コストを確認してください。CloudWatchロググループは、保持するか削除するかを別途判断してください。一部の作成処理が失敗した場合や、これらの手順以外で作成されたリソースまで自動的にクリーンアップされたと考えないでください。ラボ終了後は、専用ディレクトリにあるマニフェスト、ポリシー、kubeconfigを削除してください。

## 高度なトピック

以下はAmazon EKSの高度なトピックに関する問題です。このセクションでは、高度なEKS機能と統合についての理解度を確認します。

1. Amazon EKSでFargateプロファイルを構成する際の正しい説明はどれですか？
   * A) Fargateプロファイルは、特定のnamespaceとラベルに基づいてFargateで実行するPodを指定する
   * B) Fargateプロファイルは、すべてのPodを自動的にFargateで実行する
   * C) Fargateプロファイルは、Podの実行を特定のEC2インスタンスタイプに制限する
   * D) Fargateプロファイルは、クラスター全体のリソースクォータを設定する

<details>

<summary>解答を表示</summary>

**解答: A) Fargateプロファイルは、特定のnamespaceとラベルに基づいてFargateで実行するPodを指定する**

**解説:** Amazon EKSのFargateプロファイルは、特定のnamespaceとラベルに基づいてFargateで実行するPodを指定する構成です。これにより、サーバーレスコンテナ実行環境とEC2ベースのノードを併用するハイブリッドアーキテクチャを構成できます。

Fargateプロファイルの主な機能:

* **選択的な実行**: プロファイルで定義された条件に一致するPodだけがFargateで実行され、すべてのPodが対象になるわけではありません。
* **namespaceとラベルセレクター**: 特定のnamespaceとラベルの組み合わせに基づいてPodが選択されます。
* **サブネットの指定**: Podの実行先となるプライベートサブネットを指定できます。
* **IAMロール**: Pod実行ロールは、イメージの取得などのためにFargateインフラストラクチャによって使用されます。アプリケーションコンテナがAWS APIにアクセスするには、独自のIRSAロールが必要です。

Fargateプロファイルの作成例:

```bash
eksctl create fargateprofile \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

YAMLによるFargateプロファイルの定義:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: my-fargate-profile
    selectors:
      - namespace: my-namespace
        labels:
          app: my-app
      - namespace: another-namespace
```

Fargateを使用する際の注意点:

* FargateではDaemonSetはサポートされません。
* 特権コンテナは実行できません。
* HostNetworkとHostPortはサポートされません。
* GPUワークロードはサポートされません。
* Pod単位で料金が発生するため、コスト計画が必要です。
* 静的にプロビジョニングされたEFSボリュームを通じて永続ストレージを利用できます。FargateではEBSボリュームとEFSの動的プロビジョニングはサポートされません。

ほかの選択肢が誤りである理由:

* FargateプロファイルはすべてのPodを自動的にFargateで実行するわけではありません。Fargateで実行されるのはセレクターに一致するPodだけです。
* FargateプロファイルはEC2インスタンスタイプとは関係ありません。Fargateはサーバーレスのコンテナ実行環境です。
* Fargateプロファイルはクラスター全体のリソースクォータを設定しません。リソースクォータはKubernetes ResourceQuotaで管理します。

</details>

2. EKSのアップグレードはどのように計画すべきですか？
   * A) 先にノードを目標バージョンにアップグレードし、後から互換性を確認する
   * B) 互換性と現行バージョンを事前に確認し、各アドオンの更新を調整しながら、コントロールプレーン → ノードの順に進める
   * C) 準備として、すべてのアドオンを確認せずに最新バージョンへアップグレードする
   * D) すべてのコンポーネントを同時に変更する

<details>
<summary>解答を表示</summary>

**解答: B) 互換性と現行バージョンを事前に確認し、各アドオンの更新を調整しながら、コントロールプレーン → ノードの順に進める**

最初に、クラスター/ノードの現行バージョン、アップグレードインサイト、削除予定のAPI、Webhook/CRD/アドオンの互換性、サブネットの余剰IP、復旧計画を確認してください。次のマイナーバージョンに進む前に、バージョンが遅れているノードを現行コントロールプレーンのバージョンまで更新します。

**1. コントロールプレーン**

一度に1つのマイナーバージョンずつ進めます。現在のkubeletをAPIサーバーより新しいバージョンにすることはできず、最大で3つ前のマイナーバージョンまで許容されます。ただし、EKSはアップグレードの前後でバージョンを一致させることを推奨しています。許可される最大のバージョンスキューは、定常状態での目標ではありません。

```bash
# Inspect the current version and node versions before choosing the next minor.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status}' --output table
kubectl --context "${EXAMPLE_CONTEXT:?}" get nodes

# Choose one interface, after prerequisite checks and workload testing.
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?Select the next supported minor}"
# Alternative:
# eksctl upgrade cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --version "$NEXT_MINOR_VERSION" --approve

# Use the update ID returned above. Proceed only after status is Successful.
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "${CONTROL_PLANE_UPDATE_ID:?}" --query update.status
```

**2. ノード**

コントロールプレーンの更新が成功した後に、マネージドノードグループの更新を開始し、更新状態、ノードの準備状態、kubeletバージョンを確認します。従来型のノードグループは、コントロールプレーンと同時には自動更新されません。セルフマネージドノード/Hybrid Nodesは運用担当者が更新します。新しいバージョンを使用するには、Fargate Podを再作成してください。Auto Modeのノードは段階的に更新されます。

```bash
aws eks update-nodegroup-version --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
# Alternative:
# eksctl upgrade nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --name "$EXAMPLE_NODEGROUP" --kubernetes-version "$NEXT_MINOR_VERSION"
```

**3. アドオンとクライアント**

現行バージョンと目標バージョンの両方との互換性を事前に確認してください。一部のCNI、Webhook、コントローラーコンポーネントは、コントロールプレーンより先に互換性のあるバージョンへ更新する必要があります。そのため、アドオンの更新を常に最後に行えるとは限りません。コントロールプレーンの更新後、残りのアドオン、Cluster Autoscaler、kubectlをサポート対象のバージョンにし、それぞれを検証してください。

```bash
aws eks describe-addon-versions --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}" \
  --query 'addons[].addonVersions[].addonVersion' --output table

# Select a compatible EKS add-on build after reviewing configuration changes.
aws eks update-addon --cluster-name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_ADDON_VERSION:?}" \
  --resolve-conflicts PRESERVE
```

`PRESERVE`はユーザー構成を保持しますが、互換性を保証するものではありません。PDB、余剰キャパシティ、正常な終了処理を確認し、forceフラグで失敗を覆い隠さないでください。各段階を検証し、復元可能なアプリケーション/データのバックアップを準備します。AWSによるコントロールプレーンのバックアップは、お客様のデータ復旧計画の代わりにはなりません。

EKSでは、条件を満たすアップグレードの完了から7日以内であれば、1つ前のマイナーバージョンへのロールバックをサポートするようになりました。ノード、アドオン、API変更、サポートポリシーに関する制約があり、アプリケーションデータは自動的には復元されません。[アップグレード手順](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)と[ロールバック条件](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)に従ってください。

</details>

3. Amazon EKSのVPC CNIプラグインの主要な機能ではないものはどれですか？
   * A) PodへのVPC IPアドレスの割り当て
   * B) Pod単位でのセキュリティグループの適用
   * C) Pod間のネットワークトラフィックの暗号化
   * D) プレフィックス委任によるIPアドレスの拡張

<details>

<summary>解答を表示</summary>

**解答: C) Pod間のネットワークトラフィックの暗号化**

Amazon VPC CNIは、Pod間トラフィックを一律に暗号化する機能を提供しません。アプリケーションTLS/mTLS、または明示的にサポートされているメッシュ/CNI暗号化機能を構成してください。NetworkPolicyはトラフィックをフィルタリングしますが、暗号化は行いません。

Amazon VPC CNIプラグインの実際の主な機能:

1. **PodへのVPC IPアドレスの割り当て**:
   * 通常のPodにはVPC IPが割り当てられます。`hostNetwork` Podはノードのネットワークを共有します。
   * これにより、PodはVPC内のほかのリソースと直接通信できます。
   * PodのIPはVPC内でルーティングできるため、複雑なオーバーレイネットワークは不要です。
2. **Pod単位でのセキュリティグループの適用**:
   * SecurityGroupsForPods機能を通じて、個々のPodにAWSセキュリティグループを適用できます。
   * これにより、Pod単位で細かなネットワークセキュリティポリシーを実装できます。
   *   構成例:

       ```yaml
       apiVersion: vpcresources.k8s.aws/v1beta1
       kind: SecurityGroupPolicy
       metadata:
         name: my-security-group-policy
         namespace: default
       spec:
         podSelector:
           matchLabels:
             app: my-app
         securityGroups:
           groupIds:
             - sg-0123456789abcdef0
       ```
3. **プレフィックス委任によるIPアドレスの拡張**:
   * デフォルトでは、各ノードがPodに割り当てられるIPアドレスの数に制限があります (インスタンスタイプによって異なります)。
   * プレフィックス委任機能を使用すると、各ノードに/28 CIDRブロック (16個のIP) を割り当てて、利用可能なIPアドレス数を増やせます。
   * これによりENIあたりのアドレス数が増えますが、サブネット内の既存のアドレスを消費します。空きプレフィックスが連続している必要があり、サブネットの新たなキャパシティが作られるわけではありません。
4. **カスタムネットワーキング**:
   * Podを特定のサブネットに配置できます。
   * 複数のネットワークインターフェイスを使用してPodのネットワーキングを構成できます。
5. **Kubernetesのホストネットワーキング**:
   * `hostNetwork`はノードのネットワークを使用します。これはKubernetes Podの設定であり、CNIの暗号化機能や分離機能ではありません。
   * ネットワークパフォーマンスが重要なワークロードに役立ちます。

前提条件を確認したうえで、VPC CNIの機能を個別に適用してください。

| 設定 | 確認事項 |
| --- | --- |
| `ENABLE_PREFIX_DELEGATION` | サポート対象のインスタンス/CNIバージョン、連続した空き`/28`ブロック、kubeletのmax-pods、新しいノードへの移行計画 |
| `ENABLE_POD_ENI` | サポート対象のtrunk/branch ENIインスタンス、VPCリソースコントローラーの権限、SecurityGroupPolicy、DNS/セキュリティグループのルール |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | IPv4、同一VPC/AZ内のPodサブネット/セキュリティグループ、ノードのENIConfig選択、空きIP |

フラグを有効にするだけでは、新旧のPodで動作が異なったり、IP割り当てに失敗したりする場合があります。EKSマネージドアドオンの構成と競合しないよう、公式の移行手順に従ってください。この従来型EC2 DaemonSet方式をAuto Mode、Fargate、Hybrid Nodesに直接適用しないでください。

```bash
# Inspect current non-secret CNI flags; this does not enable any feature.
kubectl --context "${EXAMPLE_CONTEXT:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="aws-node")].env}{"\n"}'
```


Pod間のネットワークトラフィックを暗号化するには、次の代替手段を検討してください。

* App Meshのサポートは2026年9月30日に終了しました。既存ユーザーは移行する必要があります。
* Istioサービスメッシュを実装する
* Ciliumの透過的な暗号化機能を使用する
* アプリケーションレベルでTLS/mTLSを実装する

</details>

4. 開発者用IAMロールに、namespaceスコープのKubernetes読み取りアクセスを付与するにはどうすればよいですか？
   * A) IAMユーザーにKubernetes Roleを直接アタッチする
   * B) EKSアクセスエントリでIAMロールをKubernetesグループにマッピングし、RBACバインディングを構成する
   * C) クラスターIAMロールにS3ポリシーだけをアタッチする
   * D) アプリケーションServiceAccountのIRSA設定だけで、開発者にkubectlアクセスを付与する

<details>
<summary>解答を表示</summary>

**解答: B) EKSアクセスエントリでIAMロールをKubernetesグループにマッピングし、RBACバインディングを構成する**

新しいIAMアクセスには**EKSアクセスエントリ**を使用してください。クラスターの認証モードは`API`または`API_AND_CONFIG_MAP`である必要があります。既存クラスターのモードを変更する前に、マッピングの移行と管理者の復旧経路を準備してください。`aws-auth`は非推奨ですが、唯一のマッピング方式ではありません。

この例では、既存の開発者用IAMロールを`dev-readers`に関連付けます。IAM IDとアクセスエントリだけでは、Kubernetes RBACオブジェクトは自動的に作成されません。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.accessConfig.authenticationMode

aws eks create-access-entry --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --principal-arn "${DEV_ROLE_ARN:?Existing developer IAM role}" \
  --type STANDARD --kubernetes-groups dev-readers
```

管理者は、既存の`dev` namespaceにこのRoleとRoleBindingを適用します。これにより、Secretへのアクセス権限や変更権限を付与せずに、Pod/Deploymentの読み取りアクセスを付与できます。ワークロード作成権限はnamespace内のSecretの使用を可能にする場合があるため、別途検討が必要です。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: dev-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-readers
  namespace: dev
subjects:
- kind: Group
  name: dev-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: dev-reader
  apiGroup: rbac.authorization.k8s.io
```

ロールの引き受けが許可されたIDを使用して、専用のkubeconfigを作成し、実際の権限を確認してください。別のRBAC付与またはEKSアクセス用ポリシーによって権限が追加されていない限り、最初のチェックは許可され、2番目のチェックは拒否されます。

```bash
aws eks update-kubeconfig --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --role-arn "${DEV_ROLE_ARN:?}" --kubeconfig "${DEV_KUBECONFIG:?Use a dedicated file}"
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get pods -n dev
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get secrets -n dev
```

代わりに、namespaceスコープのEKSアクセス用ポリシーをエントリに関連付けることもできます。アクセス用ポリシーとRBACによる許可は加算されます。IAMポリシーをアタッチするだけでは、Kubernetes権限は付与されません。IRSA/Pod Identityは、PodがAWS APIを呼び出すための別の経路です。通常の開発者に`system:masters`を付与したり、`aws-auth` ConfigMap全体を上書きしたりしないでください。

</details>

5. EKSのバージョンサポートについて、正しい説明はどれですか？
   * A) すべてのバージョンが無期限にサポートされる
   * B) すべてのバージョンが12か月後にサポート終了となる
   * C) 常に最新バージョンと、その前の3バージョンちょうどがサポートされる
   * D) EKSリリース後、標準サポートが14か月、その後、有料の延長サポートが12か月提供される

<details>
<summary>解答を表示</summary>

**解答: D) EKSリリース後、標準サポートが14か月、その後、有料の延長サポートが12か月提供される**

EKSのマイナーバージョンは、EKSでのリリース日から**14か月間の標準サポート**を受け、その後**12か月間の有料延長サポート**を受けます。期間の起算日は上流のリリース日ではありません。

* 2026年10月12日時点の公式リスト: 標準サポートは**1.34～1.37**、延長サポートは**1.31～1.33**です。EKS 1.37は上流リリースの8月26日より後、2026年10月1日に利用可能になりました。
* 延長サポートはデフォルトで有効です。`STANDARD`のアップグレードポリシーを選択するとオプトアウトされ、標準サポート終了後に自動アップグレードの対象になります。
* 延長サポートが終了すると、AWSはコントロールプレーンをサポート対象のバージョンに自動アップグレードします。実施の正確な時期は保証されないため、運用担当者は先を見越してアップグレードを計画してください。
* コントロールプレーンが自動アップグレードされても、マネージド/セルフマネージド/Hybrid Nodesは更新されません。Fargate Podの置き換えとアドオンの更新は別途計画してください。Auto Modeのノードはマネージド更新に従います。
* サポート対象バージョンにはセキュリティパッチが適用されますが、すべてのバージョンを無期限に保持することはできません。サポート終了後のバージョンでは新しいクラスターを作成できません。

実際に使用するリージョンのリリースカレンダーとバージョン情報を確認してください。アドオンのメタデータをgrepしても、クラスターのバージョンサポート一覧の代わりにはなりません。

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,upgradePolicy:upgradePolicy}' --output json
```

アップグレードスケジュールを維持し、削除予定のAPI/互換性を確認し、本番環境以外でテストを実施して、アプリケーション/データの復旧を準備したうえで、一度に1つのマイナーバージョンずつ進めてください。EKSでは少なくとも3つのバージョンが標準サポートされますが、「常に最新とその前の3バージョンのみ」という固定ルールはありません。

</details>


## 公式リファレンスと検証範囲

- [EKSのバージンライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKSアクセスエントリ](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Pod IdentityとIRSA](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)
- [Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Auto Modeのロードバランシング](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [FSx CSIの構成とPVC容量](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)
- [Fargateの制限](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [プレフィックス委任](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [カスタムネットワーキング](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)
- [EKSの料金](https://aws.amazon.com/eks/pricing/)
- [Fargateの料金](https://aws.amazon.com/fargate/pricing/)
- [eksctl 0.230.0のスキーマ](https://github.com/eksctl-io/eksctl/blob/v0.230.0/pkg/apis/eksctl.io/v1alpha5/assets/schema.json)
- [LBC 3.5.0のインストール](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/installation.md)
- [Metrics Server 0.9.0の互換性](https://github.com/kubernetes-sigs/metrics-server/blob/v0.9.0/README.md)

これは公式ドキュメントとリリーススキーマに照らして行った静的レビューです。クラスター/IAM/ロードバランサーのプロビジョニング、アプリケーションのデプロイ、アップグレード/ロールバック、NGINXの実行、負荷テスト、コスト測定は実施していません。例で想定される動作は、測定結果ではありません。
