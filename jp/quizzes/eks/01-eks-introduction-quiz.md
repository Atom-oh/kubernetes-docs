# EKS入門クイズ

> **最終更新日**: 2026年10月12日

このクイズでは、Amazon Elastic Kubernetes Service（EKS）の基本概念と機能について理解を確認します。EKSのアーキテクチャ、コンポーネント、管理方法、料金モデルなどを扱います。

単独で使うAPI例では、`EXAMPLE_CLUSTER`、`EXAMPLE_REGION`、`EXAMPLE_CONTEXT`などの指定変数に、レビュー済みの対象環境の値を設定してください。IRSAの例では、既存の`EXAMPLE_NAMESPACE`、必要なバケット/プレフィックスだけに範囲を絞った`APP_POLICY_ARN`、およびIRSA対応のAWS SDKを使用するアプリケーションが必要です。2つの演習では、それぞれ専用の`EKS_INTRO_*`変数を使用します。

## 多肢選択問題

1. Amazon EKS（Elastic Kubernetes Service）の主な利点は何ですか？
   * A) Kubernetesコントロールプレーンのインフラストラクチャを自分で管理する必要がない
   * B) 他のマネージドKubernetesサービスより必ず低コストである
   * C) AWSサービスのみを利用できる
   * D) 単一のアベイラビリティーゾーンでしか実行できない

<details>

<summary>解答を表示</summary>

**解答: A) Kubernetesコントロールプレーンのインフラストラクチャを自分で管理する必要がない**

**解説:** Amazon EKSの主な利点は、Kubernetesコントロールプレーンのインフラストラクチャを自分で管理しなくてよいことです。AWSがコントロールプレーンの可用性とスケーラビリティを管理するため、利用者はワークロードに集中できます。

EKSの主な利点:

* **マネージドコントロールプレーン**: AWSがコントロールプレーンノード、etcdクラスター、APIサーバーなどを管理します。
* **高可用性**: リージョン単位のコントロールプレーンは複数のアベイラビリティーゾーンにまたがります。ワークロードの可用性には、レプリカ、配置、容量、依存先も影響します。
* **メンテナンスの管理**: AWSがコントロールプレーンにパッチを適用します。運用者はマイナーバージョンのアップグレードを計画しますが、バージョンサポートポリシーに基づく自動アップグレードも行われます。
* **AWSサービスとの統合**: IAM、VPC、ELB、ECRなど、さまざまなAWSサービスと統合できます。
* **標準Kubernetes**: Kubernetes APIへの準拠により移植性が高まりますが、AWS固有のID、ストレージ、統合機能には移行作業が必要です。

他の選択肢が誤りである理由:

* EKSが他のマネージドKubernetesサービスより必ず安いとは限りません。コントロールプレーンには時間単位の料金がかかります。
* EKSではAWSサービスに限らず、Kubernetes互換のアプリケーションやサービスを実行できます。
* リージョン単位のEKSコントロールプレーンは複数のアベイラビリティーゾーンにまたがります。ワーカーノードとアプリケーションのレプリカは、利用者が別途分散させる必要があります。

</details>

2. Amazon EKSクラスターのコントロールプレーンはどこに配置されますか？
   * A) 利用者のVPC内
   * B) AWSが管理するアカウント内の複数のアベイラビリティーゾーンに配置される
   * C) 利用者が選んだ単一のアベイラビリティーゾーン
   * D) 利用者のEC2インスタンス上

<details>

<summary>解答を表示</summary>

**解答: B) AWSが管理するアカウント内の複数のアベイラビリティーゾーンに配置される**

**解説:** Amazon EKSのコントロールプレーンは、AWSが管理するアカウント内の複数のアベイラビリティーゾーンに配置されます。これはEKSをマネージドサービスとして提供するうえでの基本的な仕組みです。

EKSコントロールプレーン配置の主な特徴:

* **AWS管理のインフラストラクチャ**: コントロールプレーンはAWSが所有、管理するアカウント内で実行されます。
* **複数AZへの配置**: リージョン単位のコントロールプレーンコンポーネントは複数のアベイラビリティーゾーンに分散されます。
* **自動復旧**: AWSはコントロールプレーンコンポーネントの状態を監視し、障害が発生したコンポーネントを自動的に置き換えます。
* **エンドポイントへのアクセス**: パブリックアクセス、プライベートアクセス、またはその両方を構成できます。プライベートアクセスには、VPCまたは接続ネットワークからのDNS解決とルーティングも必要です。
* **自動スケーリング**: 標準のコントロールプレーン容量は自動的に調整されます。オプションのProvisioned Control Planeティアは明示的に選択します。

他の選択肢が誤りである理由:

* コントロールプレーンは利用者のVPC内ではなく、AWS管理のVPCと利用者のVPCをENI（Elastic Network Interface）で接続します。
* 高可用性のため、コントロールプレーンは単一ではなく複数のアベイラビリティーゾーンにまたがって配置されます。
* コントロールプレーンは利用者のEC2インスタンスではなく、AWS管理のインフラストラクチャ上で実行されます。

</details>

3. EKSのコンピューティング管理について、誤っている説明はどれですか？
   * A) セルフマネージドEC2ノード
   * B) マネージドノードグループ
   * C) Fargateプロファイル
   * D) Bottlerocketは独立したサーバーレスコンピューティングサービスである

<details>
<summary>解答を表示</summary>

**解答: D) Bottlerocketは独立したサーバーレスコンピューティングサービスである**

Bottlerocketはコンテナノード向けのオペレーティングシステムであり、独立したサーバーレス実行方式ではありません。

1. **セルフマネージドノード**: 利用者がEC2/Auto Scalingグループ、AMI、更新、ノード構成を管理します。
2. **マネージドノードグループ**: AWSがプロビジョニングと置き換えのワークフローを管理し、運用者がAMIやバージョンの更新を開始します。最小/最大サイズを指定するだけでは、需要に応じたスケーリングは有効になりません。
3. **Fargate**: プロファイルでPodを選択し、分離されたコンピューティング環境で実行します。DaemonSet、GPU、EBSなどの制限を確認してください。
4. **EKS Auto Mode**: ノードのプロビジョニング、スケーリング、置き換えを自動化する実際のEKS機能です。
5. **Hybrid Nodes**: オンプレミスまたはエッジのマシンをAWS管理のコントロールプレーンに接続します。

従来型のEC2ノードでは、需要に応じたスケーリングのためにCluster AutoscalerまたはセルフマネージドKarpenterを別途構成できます。

</details>

4. 従来型EC2ベースのEKSノードで、デフォルトのCNIはどれですか？
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>解答を表示</summary>

**解答: C) AWS VPC CNI**

**解説:** Amazon EKSでPodネットワーキングにデフォルトで使用されるCNI（Container Network Interface）プラグインはAWS VPC CNIです。このプラグインはAmazon VPCのネットワーク機能をKubernetes Podに直接統合します。

AWS VPC CNIの主な機能:

* **VPCネイティブのIPアドレス割り当て**: PodにはVPCのIPアドレスが直接割り当てられ、VPC内の他のリソースと同じネットワーク空間に配置されます。
* **セカンダリIPアドレスの利用**: 各ノードのElastic Network Interface（ENI）に関連付けられたセカンダリIPアドレスをPodに割り当てます。
* **セキュリティグループの統合**: Pod用セキュリティグループには、対応インスタンス、VPCリソースコントローラーの権限、CNI構成、SecurityGroupPolicyが必要です。
* **VPCフローログでの可視性**: PodのトラフィックはVPCフローログで確認できます。
* **AWSネットワーク機能の利用**: PodからVPCピアリング、Transit Gateway、PrivateLinkなどを利用できます。

AWS VPC CNIはオープンソースプロジェクトです。コードはGitHubで確認できます: https://github.com/aws/amazon-vpc-cni-k8s

EC2ノード上で別のCNIを使う場合は、それぞれの互換性とサポートを確認してください。FargateとAuto Modeでは任意のCNIへの置き換えはサポートされません。Hybrid Nodesでは互換性のあるオンプレミスCNIが必要です。`hostNetwork`を使用するPodはノードのネットワークを共有します。

</details>

5. IAM IDにEKS Kubernetes APIへのアクセスを許可するにはどうしますか？
   * A) すべてのIAMユーザーをServiceAccountだけで認証する
   * B) アクセスエントリを使い、アクセスポリシーおよび/またはKubernetes RBACでIAM認証を設定する
   * C) EKS IAMポリシーがすべてのKubernetesリソース権限を自動的に付与する
   * D) Cognitoをすべてのクラスターへ自動接続する

<details>
<summary>解答を表示</summary>

**解答: B) アクセスエントリを使い、アクセスポリシーおよび/またはKubernetes RBACでIAM認証を設定する**

Kubernetes APIへのIAMアクセスと、PodからAWS APIへのアクセスは別の経路です。

1. `aws eks get-token`は、IAM認証情報で署名した認証トークンを作成します。
2. EKSがIAM IDを認証します。新しいアクセス構成には**アクセスエントリ**を使用してください。
3. EKSアクセスポリシーを関連付けるか、Kubernetesグループを指定してRoleBinding/ClusterRoleBindingを作成します。RBACとEKSオーソライザーは権限を加算します。どちらも要求を許可しなければ拒否されます。
4. 従来の`aws-auth` ConfigMapは非推奨です。既存のマッピングがすべて自動移行されるわけではないため、アクセスエントリへ移行する際に各IDと権限を確認してください。

IAMポリシーはEKSサービスAPIへの呼び出しを制御します。EKSアクセスポリシーはKubernetes権限のテンプレートであり、IAMポリシーではありません。IRSA/Pod Identityは、ワークロードにAWS権限を別途付与します。Kubernetes ServiceAccountトークンと構成済みOIDCプロバイダーもKubernetesの認証に使えます。IAMだけが認証方式ではありません。

</details>

6. OIDCフェデレーションを使ってKubernetes ServiceAccountに一時的なAWS認証情報を付与するのはどれですか？
   * A) EC2インスタンスプロファイルでノードにIAMロールを付与する
   * B) 長期AWSアクセスキーをPodの環境変数に埋め込む
   * C) IAMロールをKubernetes ServiceAccountに関連付ける（IRSA）
   * D) AWS認証情報をKubernetes Secretに保存してマウントする

<details>

<summary>解答を表示</summary>

**解答: C) IAMロールをKubernetes ServiceAccountに関連付ける（IRSA）**

IRSAは、クラスターのOIDCプロバイダーを介してServiceAccountトークンを交換し、一時的なAWS認証情報を取得します。信頼ポリシーは名前空間/ServiceAccountと`aud=sts.amazonaws.com`に限定してください。EKS Pod Identityも一時認証情報を提供しますが、個別のOIDCプロバイダーは不要です。対応するコンピューティング環境、エージェント、SDKの要件を確認してください。この例はIRSAの方式を示します。

IRSAの主な利点:

* **最小権限の原則**: アプリケーションごとに必要最低限の権限を付与できます。
* **権限の分離**: 同じノード上で実行する異なるPodに別々のIAM権限を持たせられます。
* **認証情報管理の簡素化**: AWS認証情報を直接管理する必要がありません。
* **セキュリティの向上**: 認証情報をコードや構成にハードコードしません。

IRSAの設定方法:

1.  EKSクラスターにOpenID Connect（OIDC）プロバイダーを関連付けます:

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" --approve
    ```
2.  ServiceAccount用のIAMロールを作成します:

    ```bash
    eksctl create iamserviceaccount \
      --name=app-sa \
      --namespace="${EXAMPLE_NAMESPACE:?}" \
      --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" \
      --attach-policy-arn="${APP_POLICY_ARN:?Use a reviewed policy scoped to the required bucket/prefix}" \
      --approve
    ```
3.  同じ名前空間のPodからServiceAccountを参照します。これはテンプレートです。イメージをIRSA対応SDKを使用するアプリケーションに置き換え、`-n "$EXAMPLE_NAMESPACE"`を指定して適用します:

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

他の選択肢が誤りである理由:

* IMDSに到達できるPodはノードロールの認証情報を取得できる場合があります。IMDSへのアクセスを制限し、ワークロードごとのロールを使ってください。IRSAだけではIMDSアクセスは遮断されません。
* 長期アクセスキーをPodの環境変数に埋め込むと、漏えいとローテーションのリスクが高まります。IRSA/Pod Identityが使う認証プロバイダー環境変数とは別の仕組みです。
* AWS認証情報をKubernetes Secretに保存すると、認証情報の管理負担が増し、ローテーションが複雑になります。

</details>

7. Amazon EKSクラスターのログ機能について正しい説明はどれですか？
   * A) すべてのログがデフォルトでCloudWatch Logsに送信される
   * B) コントロールプレーンログは任意でCloudWatch Logsに送信できる
   * C) ワーカーノードログだけがCloudWatch Logsに送信できる
   * D) EKSにはログ機能がない

<details>

<summary>解答を表示</summary>

**解答: B) コントロールプレーンログは任意でCloudWatch Logsに送信できる**

**解説:** Amazon EKSでは、コントロールプレーンログを任意でCloudWatch Logsに送信できます。この機能はデフォルトでは無効です。必要なログタイプを選択して有効にできます。

EKSコントロールプレーンログの主な特徴:

* **任意で有効化**: クラスター作成時にも、既存クラスターにも設定できます。
* **ログタイプの選択**: 次のログタイプから必要なものだけを選択できます:
  * APIサーバー（api）
  * 監査（audit）
  * 認証器（authenticator）
  * コントローラーマネージャー（controllerManager）
  * スケジューラー（scheduler）
* **CloudWatch Logsとの統合**: 選択したログは、保存、分析、監視のためCloudWatch Logsへ送信されます。
* **コスト**: ログの取り込み、保持、クエリに料金がかかる場合があります。

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

* ワーカーノードのログはEKSコントロールプレーンログ機能には含まれません。
* ワーカーノードのログをCloudWatch Logsへ送るには、CloudWatch Agentをインストールするか、Fluentd/Fluent Bitなどのログソリューションを構成してください。

他の選択肢が誤りである理由:

* すべてのログがデフォルトでCloudWatch Logsへ送信されるわけではありません。明示的に有効にする必要があります。
* CloudWatch Logsへ送信できるログはワーカーノードのものだけではなく、コントロールプレーンログも送信できます。
* EKSにはコントロールプレーンのログ機能があります。

</details>

8. Amazon EKSクラスターのコストに含まれないものはどれですか？
   * A) EKSコントロールプレーンの時間料金
   * B) ワーカーノード用EC2インスタンスの料金
   * C) Fargate Podの実行料金
   * D) Kubernetesのライセンス料

<details>

<summary>解答を表示</summary>

**解答: D) Kubernetesのライセンス料**

**解説:** Kubernetesのライセンス料はAmazon EKSクラスターのコストに含まれません。KubernetesはCloud Native Computing Foundation（CNCF）が管理するオープンソースソフトウェアで、Apache 2.0ライセンスの下で利用できます。そのため、EKSの利用に別途Kubernetesのライセンス料は発生しません。

Amazon EKSで実際に発生する主なコスト:

1. **EKSコントロールプレーンの時間料金**:
   * 標準サポートと延長サポートではクラスター料金が異なります。オプションのProvisioned Control Planeティアには追加料金がかかります。
   * EKSクラスターはリージョン単位のリソースです。複数リージョンに展開する場合はクラスターと料金がそれぞれ発生します。
   * Auto Mode、EKS Capabilities、Hybrid NodesおよびAWSインフラストラクチャの料金も別途考慮してください。
2. **ワーカーノード用EC2インスタンスの料金**:
   * セルフマネージドまたはマネージドノードグループで使うEC2インスタンスに料金がかかります。
   * 料金はインスタンスタイプ、サイズ、数、稼働時間によって異なります。
   * リザーブドインスタンス、Savings Plans、Spotインスタンスで最適化できる場合があります。
3. **Fargate Podの実行料金**:
   * FargateではPodに割り当てたvCPUとメモリリソースに基づいて課金されます。
   * Linux Fargateの課金はイメージのダウンロード開始時から始まり、秒単位に丸められ、最低1分です。要求リソースはサポートされる構成単位に丸められます。
   * プロビジョニングする容量、利用率、運用負荷を含めて比較してください。FargateとEC2のどちらかが常に安いとは限りません。
4. **追加のAWSリソース料金**:
   * EBSボリューム
   * ロードバランサー（NLB、ALB）
   * CloudWatch Logsとメトリクス
   * NAT Gateway
   * データ転送

コスト最適化の方法:

* 適切なインスタンスタイプを選ぶ
* オートスケーリングを構成する
* Spotインスタンスを使う
* クラスターの自動化とスケジュールスケーリングを行う
* リソース要求と上限を最適化する
* コストを監視、分析する

</details>

9. Auto Modeを使わない従来型EKSクラスターで、ALB/NLBと宣言的に統合する方法はどれですか？
   * A) EKS組み込みロードバランサーを使う
   * B) Kubernetes ServiceリソースをAWS Load Balancer Controllerと統合する
   * C) EC2ロードバランサーを手動で作成、構成する
   * D) EKSはロードバランシングをサポートしない

<details>

<summary>解答を表示</summary>

**解答: B) Kubernetes ServiceリソースをAWS Load Balancer Controllerと統合する**

**解説:** 従来型のAmazon EKSクラスターでは、Kubernetes ServiceリソースとAWS Load Balancer Controllerを統合することで、宣言的なロードバランシングを構成できます。Kubernetesのリソース管理とAWSのロードバランサー機能を組み合わせる方法です。

EKSでロードバランシングを実装する方法:

1. **デフォルトのLoadBalancer型Service**:
   * どのコントローラーがロードバランサーを作るかは、選択されたコントローラーによって異なります。この例ではインストールと権限設定が済んだAWS LBCを`service.k8s.aws/nlb`で明示的に選択します。従来の統合ではCLBが作られる場合があります。

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
   * より高度な機能でApplication Load Balancer（ALB）とNetwork Load Balancer（NLB）を管理するには、AWS Load Balancer Controllerをインストールします。
   * ALBはIngressリソースでプロビジョニング、構成できます。
   * ロードバランサーの各種属性はアノテーションで設定できます。

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
   * Serviceにアノテーションを追加して、ロードバランサーのタイプや構成を指定できます。

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

他の選択肢が誤りである理由:

* Auto Modeは`eks.amazonaws.com/nlb`を含む別のクラスを使ってロードバランシングを管理します。インクラスターのAWS LBCをインストールする必要はありません。両者のクラスや、サポートされないアノテーションを混在させないでください。
* EC2ロードバランサーを手動で作成、構成することもできますが、Kubernetesの宣言的な管理方法に沿わず、運用が複雑になります。
* EKSはロードバランシングをサポートしています。

</details>

10. Amazon EKSクラスターでストレージを管理する有効な方法ではないものはどれですか？
    * A) EBS CSIドライバーでEBSボリュームをプロビジョニングする
    * B) EFS CSIドライバーでEFSファイルシステムをマウントする
    * C) Fargate PodにEBSボリュームをマウントする
    * D) FSx for Lustre CSIドライバーで高性能ファイルシステムを接続する

<details>

<summary>解答を表示</summary>

**解答: C) Fargate PodにEBSボリュームをマウントする**

FargateではEBSボリュームをマウントできません。従来型のEC2ノードでは、IAM権限を設定したEBS CSIドライバーをインストールして使用します。Auto Modeでは`ebs.csi.eks.amazonaws.com`によるマネージドEBSプロビジョニングを利用できます。これは従来型の`ebs.csi.aws.com`ドライバーとは別です。

Amazon EKSでストレージを管理する実際の方法:

1. **EBS CSIドライバー**:
   * Amazon EBS（Elastic Block Store）ボリュームをKubernetes Podに接続します。
   * データベースなど、ブロックストレージを必要とするアプリケーションに適しています。
   * StorageClassで許可されている場合、動的プロビジョニング、スナップショットコントローラーによるスナップショット、ボリューム拡張をサポートします。
   * EBSはAZ単位のストレージです。ReadWriteOnceは1つのノードから読み書きしてマウントできることを示し、1つのPodに限るという意味ではありません。同じノード上の複数Podで使える場合があります。アクセスモードでAZが決まるわけではありません。

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
   * Amazon EFS（Elastic File System）をKubernetes Podにマウントします。
   * 複数のPodから同時にアクセスする共有ファイルシステムに適しています。
   * 複数のアベイラビリティーゾーンからアクセスできます（ReadWriteManyアクセスモード）。
   * Webサーバー、CMS、CI/CDパイプラインなどで利用できます。

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
   * Amazon FSx for LustreをKubernetes Podに接続します。
   * HPC、機械学習、ビッグデータ分析など、高性能が必要なワークロードに適しています。
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
   PVCの容量は`spec.resources.requests.storage`（例: `1200Gi`）で指定してください。StorageClassの`storageCapacity`パラメーターではありません。デプロイ先ごとの容量増分、サブネット/セキュリティグループ、Lustreクライアントの互換性、ドライバーのIAM権限を確認してください。

4. **その他のストレージ**:
   * CSIドライバーやS3マウンターを通じたAmazon S3（Simple Storage Service）
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * サードパーティーのストレージソリューション（Portworx、Rookなど）

ストレージ管理のベストプラクティス:

* ワークロードの要件に合うストレージタイプを選ぶ
* 動的プロビジョニング用にStorageClassを構成する
* バックアップと復旧の方法を確立する
* ストレージの性能を監視する
* コスト最適化のため、適切なストレージクラスと容量を選ぶ

</details>

## ハンズオン演習

### 演習1: EKSクラスターの作成と構成

**シナリオ:** あなたは社内のDevOpsエンジニアで、開発チーム向けのAmazon EKSクラスターを用意する必要があります。クラスターは開発環境用で、必要な機能を備えつつ費用を抑えることが求められています。

**要件:**

1. 費用を抑えたEKSクラスターを作成する
2. 適切なノードグループを構成する
3. 基本的な監視を設定する
4. クラスターへのkubectlアクセスを構成する

**手順:**

<details>
<summary>手順を表示</summary>

これらのデプロイコマンドを実行すると課金対象のAWSリソースが作成されます。監査時には実行していません。Bash、最新のAWS CLI v2、kubectl 1.36、Helmを準備し、[eksctlの公式インストール手順](https://eksctl.io/installation/)でOS/CPUアーキテクチャとチェックサムを確認してください。この例はeksctl 0.230.0のスキーマとEKS 1.36に照らしてレビューしたものですが、本番構成として検証済みではありません。

手順は1つのシェルで実行し、コマンドが失敗したら停止してください。`EKS_INTRO_ADMIN_CIDR`には、許可されたクライアントの実際の外部IPv4 CIDR（通常は`/32`）を設定します。新しいクラスターはプライベートノード/プライベートAPIアクセスにし、パブリックAPIアクセスは制限します。NAT Gatewayを1つにするのは開発ラボ向けの選択であり、本番可用性設計ではありません。クラスター作成者への管理者権限付与は、この専用ラボの初期設定に限ります。

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

作成に失敗した場合は、一意なクラスター名に対応するCloudFormationスタック/リソースを調査して削除してから、その名前を再利用してください。`minSize`/`maxSize`はサイズの範囲を設定するだけで、需要に応じたノードオートスケーラーをインストールするものではありません。t3.mediumは例です。キャパシティ、CPUクレジット、リージョンごとの料金を確認してください。

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

Metrics Server 0.9.xはKubernetes 1.34以降をサポートします。これはリソースメトリクスを提供するものであり、ログ収集や長期監視を行うものではありません。TLS検証を無効にせず、kubeletの証明書とネットワーク到達性を確認してください。

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

ポリシー、コントローラー、Chartは3.5.0に固定しています。無関係なアドオン権限をすべてのノードに与えず、コントローラー専用のIRSAロールを使用してください。IMDSによる検出に頼らないよう、リージョン/VPCを明示します。サブネットタグ、セキュリティグループ、サービスクォータは別途確認してください。

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

**6. ローカルのポートフォワードで基本アプリを確認する**

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

ポートフォワードの実行中に`http://127.0.0.1:8080`を開いてください。終了するにはCtrl-Cを押します。次の演習では外部ALBアクセスを構成します。2つの演習が終わったら削除手順を実行してください。期待どおりの動作や費用削減は測定していません。

</details>

### 演習2: EKSクラスターへのアプリケーション展開とサービス公開

**シナリオ:** チームはマイクロサービスアーキテクチャのWebアプリケーションを開発しました。このアプリケーションをEKSクラスターに展開し、外部からアクセスできるように構成します。

**要件:**

1. フロントエンドとバックエンドのサービスを展開する
2. サービス間通信を構成する
3. Ingress Controllerで外部アクセスを構成する
4. 基本的なスケーリングを設定する

**手順:**

<details>
<summary>手順を表示</summary>

演習1で作成した専用クラスターとシェル変数を使用し、AWS LBC/IngressClass `alb`と正常なMetrics Serverを用意してください。このHTTPデモは公開用のダミー応答だけを返し、ALBへのアクセスを選択したクライアントCIDRに制限します。アプリケーション認証、TLS、本番負荷検証は行いません。

**1. 名前空間を作成する**

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Complete exercise1 first}"
unset EKS_INTRO_WEB_UID
EKS_INTRO_WEB_UID=$(intro_kubectl create namespace web-app -o jsonpath='{.metadata.uid}')
: "${EKS_INTRO_WEB_UID:?Stop if this namespace already exists}"
```

**2. バックエンドを構成する**

NGINXをポート80で待ち受けるように構成し、`/api`などのパスにダミーJSONを返します。

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

**3. フロントエンドとサービス間通信を構成する**

標準のNGINXイメージは`BACKEND_URL`を読み取りません。このNGINX構成では`/proxy-api/`を`backend-service`へプロキシするため、実際のサービス間通信経路になります。

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

**4. AWS LBCのIngressを作成する**

ALBは`/api`を自動的に削除しません。バックエンド側でこのパスを処理します。`/`と`/proxy-api/`はフロントエンドへ送ります。

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

CPU使用率はrequestsに対する割合として測定されます。HPAが変更するのはPodのレプリカ数であり、ノード数ではありません。Metrics Serverと、ノード側の空き容量が必要です。

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

ALBのホスト名があるだけではターゲットが正常である証明にはなりません。要求が失敗した場合は、イベント、ターゲットの健全性、セキュリティグループ、クライアントCIDRを調べてください。

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

このサンプル負荷でCPU目標を超えたりHPAが動作したりするとは限りません。静的なNGINX応答はCPU使用量が少ない場合があり、フロントエンドのルートへの要求はバックエンドに負荷をかけません。実際にスケーリングが起きたかは、メトリクス、HPAの状態、Pending Podを確認してください。

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

### 演習リソースを削除する

専用ラボクラスターであることを、アカウント、ARN、タグで確認してください。コントローラーを削除する前にアプリケーションのロードバランサーを削除し、最終処理が終わるまで待ちます。タイムアウト時はfinalizerを削除するのではなく、コントローラーのエラーを調べてください。

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

所有者を確認し、Ingressと名前空間を削除できた後にだけ続行してください。IAMロールのスタック削除とポリシーのデタッチを確認してから、ポリシーを削除してください。

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

CloudFormationの削除状態と、残っているロードバランサー、セキュリティグループ、NAT、EBS、ログ保持コストを確認してください。CloudWatchロググループを保持するか削除するかは、別途判断します。途中まで作成されたリソースや、これらの手順以外のリソースも自動削除されるとは限りません。ラボ用ディレクトリに保存したマニフェスト、ポリシー、kubeconfigを削除してください。

## 高度なトピック

次の問題はAmazon EKSの高度なトピックを扱います。EKSの高度な機能と統合について理解を確認します。

1. Amazon EKSでFargateプロファイルを構成する場合、正しい説明はどれですか？
   * A) Fargateプロファイルは、名前空間とラベルに基づいてFargateで実行するPodを選択する
   * B) FargateプロファイルはすべてのPodを自動的にFargateで実行する
   * C) FargateプロファイルはPodの実行を特定のEC2インスタンスタイプに制限する
   * D) Fargateプロファイルはクラスター全体のリソースクォータを設定する

<details>

<summary>解答を表示</summary>

**解答: A) Fargateプロファイルは、名前空間とラベルに基づいてFargateで実行するPodを選択する**

**解説:** Amazon EKSのFargateプロファイルは、名前空間とラベルに基づいてFargateで実行するPodを指定します。これにより、Fargateのサーバーレスコンテナ実行環境とEC2ベースのノードを組み合わせられます。

Fargateプロファイルの主な機能:

* **選択的な実行**: プロファイルに定義した条件に一致するPodだけがFargateで実行されます。
* **名前空間とラベルのセレクター**: Podは特定の名前空間とラベルの組み合わせで選択されます。
* **サブネット指定**: Podの実行先となるプライベートサブネットを指定できます。
* **IAMロール**: Pod実行ロールはイメージ取得などFargateインフラストラクチャの処理に使います。アプリケーションコンテナからAWS APIへアクセスするには、別途IRSAロールが必要です。

Fargateプロファイルの作成例:

```bash
eksctl create fargateprofile \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

YAML形式のFargateプロファイル定義:

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

Fargateを使用する際の考慮事項:

* DaemonSetはFargateではサポートされません。
* 特権コンテナは実行できません。
* HostNetworkとHostPortはサポートされません。
* GPUワークロードはサポートされません。
* Podごとに料金が発生するため、コスト計画が必要です。

* 永続ストレージは静的にプロビジョニングしたEFSボリュームで利用できます。FargateではEBSボリュームとEFSの動的プロビジョニングはサポートされません。

他の選択肢が誤りである理由:

* FargateプロファイルはすべてのPodを自動的にFargateで実行するのではなく、セレクターに一致するPodだけを選びます。
* FargateプロファイルはEC2インスタンスタイプとは関係ありません。Fargateはサーバーレスのコンテナ実行環境です。
* Fargateプロファイルはクラスター全体のリソースクォータを設定しません。リソースクォータはKubernetesのResourceQuotaで管理します。

</details>

2. EKSのアップグレードはどのように計画すべきですか？
   * A) 互換性を後で確認するため、最初にノードを目標バージョンへ上げる
   * B) 互換性と現行バージョンを確認し、コントロールプレーン → ノードの順で進め、各アドオンの更新を調整する
   * C) 準備としてすべてのアドオンを無条件で最新に更新する
   * D) すべてのコンポーネントを同時に変更する

<details>
<summary>解答を表示</summary>

**解答: B) 互換性と現行バージョンを確認し、コントロールプレーン → ノードの順で進め、各アドオンの更新を調整する**

まず、現在のクラスター/ノードのバージョン、Upgrade Insights、削除済みAPI、Webhook/CRD/アドオンの互換性、サブネットの空きIP、復旧計画を確認します。次のマイナーバージョンへ進む前に、遅れているノードを現在のコントロールプレーンと同じバージョンまで更新します。

**1. コントロールプレーン**

一度に1つのマイナーバージョンずつ更新してください。現在のkubeletはAPIサーバーより新しいバージョンにはできず、最大3つ前のマイナーバージョンまで許容されます。ただし、EKSはアップグレード前後にバージョンを一致させることを推奨しています。許容される最大のバージョン差を通常運用の目標にしないでください。

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

コントロールプレーンの更新が成功した後、マネージドノードグループの更新を開始し、更新状態、ノードのReady状態、kubeletバージョンを確認します。従来型のノードグループはコントロールプレーンと同時には自動更新されません。セルフマネージドノード/Hybrid Nodesは運用者が更新します。Fargate Podは新しいバージョンで使うために再作成します。Auto ModeのノードはAWSが段階的に更新します。

```bash
aws eks update-nodegroup-version --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
# Alternative:
# eksctl upgrade nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --name "$EXAMPLE_NODEGROUP" --kubernetes-version "$NEXT_MINOR_VERSION"
```

**3. アドオンとクライアント**

現在と目標のKubernetesバージョン両方との互換性を事前に確認してください。CNI、Webhook、コントローラーによってはコントロールプレーンより先に更新が必要なものもあり、アドオン更新を常に最後にするとは限りません。コントロールプレーン更新後に、残りのアドオン、Cluster Autoscaler、kubectlをサポート対象バージョンにし、それぞれ動作確認してください。

```bash
aws eks describe-addon-versions --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}" \
  --query 'addons[].addonVersions[].addonVersion' --output table

# Select a compatible EKS add-on build after reviewing configuration changes.
aws eks update-addon --cluster-name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_ADDON_VERSION:?}" \
  --resolve-conflicts PRESERVE
```

`PRESERVE`は利用者の構成を維持しますが、互換性は保証しません。PDB、予備容量、正常な終了処理を確認し、forceフラグで失敗を隠さないでください。各段階を検証し、復元可能なアプリケーション/データのバックアップを準備します。AWSのコントロールプレーンバックアップは、利用者側のデータ復旧計画の代わりにはなりません。

EKSでは、条件を満たすアップグレードの完了後7日以内に、前のマイナーバージョンへロールバックできるようになりました。ノード、アドオン、API変更、サポートポリシーなどの条件があり、アプリケーションデータは自動で復元されません。[アップグレード手順](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)と[ロールバック条件](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)に従ってください。

</details>

3. Amazon EKSのVPC CNIプラグインの主要機能ではないものはどれですか？
   * A) PodにVPC IPアドレスを割り当てる
   * B) Pod単位でセキュリティグループを適用する
   * C) Pod間のネットワークトラフィックを暗号化する
   * D) Prefix DelegationでIPアドレス数を増やす

<details>

<summary>解答を表示</summary>

**解答: C) Pod間のネットワークトラフィックを暗号化する**

Amazon VPC CNIは、Pod間のトラフィックを一律に暗号化する機能を提供しません。アプリケーションTLS/mTLS、または明示的にサポートされたメッシュ/CNIの暗号化機能を構成してください。NetworkPolicyは通信をフィルタリングしますが、暗号化はしません。

Amazon VPC CNIプラグインの主な機能:

1. **PodへのVPC IPアドレス割り当て**:
   * 通常のPodにはVPCのIPアドレスが割り当てられます。`hostNetwork` Podはノードのネットワークを共有します。
   * これにより、PodはVPC内の他のリソースと直接通信できます。
   * Pod IPはVPC内でルーティングでき、複雑なオーバーレイネットワークは不要です。
2. **Pod単位のセキュリティグループ適用**:
   * SecurityGroupsForPods機能で、AWSセキュリティグループをPodに適用できます。
   * これにより、Pod単位できめ細かいネットワークセキュリティポリシーを実装できます。
   * 構成例:

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
3. **Prefix DelegationによるIPアドレスの拡張**:
   * デフォルトでは、ノードあたりにPodへ割り当てられるIPアドレス数に上限があります（インスタンスタイプによって異なります）。
   * Prefix Delegationでは、ノードに`/28` CIDRブロック（16 IP）を割り当て、ENIあたりのアドレス容量を増やせます。既存サブネットのIPを消費し、空きの連続したプレフィックスが必要です。サブネットの総容量が増えるわけではありません。
4. **カスタムネットワーキング**:
   * Podを特定のサブネットに配置できます。
   * 複数のネットワークインターフェイスを使うようPodネットワーキングを構成できます。
5. **Kubernetesのホストネットワーキング**:
   * `hostNetwork`はノードのネットワークを使います。これはKubernetes Podの設定であり、CNIによる暗号化や分離の機能ではありません。
   * ネットワーク性能が重要なワークロードで役立ちます。

前提条件を確認してから、VPC CNIの各機能を個別に適用してください。

| 設定 | 必要な確認事項 |
| --- | --- |
| `ENABLE_PREFIX_DELEGATION` | 対応するインスタンス/CNIバージョン、空きの連続した`/28`ブロック、kubeletのmax-pods、新規ノードへの移行計画 |
| `ENABLE_POD_ENI` | 対応するtrunk/branch ENIインスタンス、VPCリソースコントローラーの権限、SecurityGroupPolicy、DNS/セキュリティグループルール |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | IPv4、同じVPC/AZ内のPodサブネットとセキュリティグループ、ノードのENIConfig選択、空きIP |

フラグを有効にするだけで、既存Podと新規Podの動作が変わったり、IP割り当てに失敗したりする場合があります。EKSマネージドアドオン構成と競合しない公式の移行手順に従ってください。この従来型のEC2 DaemonSet方式をAuto Mode、Fargate、Hybrid Nodesにそのまま適用しないでください。

```bash
# Inspect current non-secret CNI flags; this does not enable any feature.
kubectl --context "${EXAMPLE_CONTEXT:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="aws-node")].env}{"\n"}'
```

Pod間通信を暗号化するには、次の方法を検討してください:

* App Meshのサポートは2026年9月30日に終了しました。既存ユーザーは移行が必要です。
* Istioサービスメッシュを導入する
* Ciliumの透過的暗号化機能を使う
* アプリケーションレベルでTLS/mTLSを実装する

</details>

4. 開発者用IAMロールに、名前空間を限定したKubernetes読み取りアクセスを付与する方法はどれですか？
   * A) IAMユーザーにKubernetes Roleを直接関連付ける
   * B) EKSアクセスエントリでIAMロールをKubernetesグループに対応付け、RBACバインディングを構成する
   * C) クラスターIAMロールにS3ポリシーだけを付与する
   * D) アプリケーションServiceAccountのIRSA設定だけで開発者のkubectlアクセスを許可する

<details>
<summary>解答を表示</summary>

**解答: B) EKSアクセスエントリでIAMロールをKubernetesグループに対応付け、RBACバインディングを構成する**

新しいIAMアクセス構成には**EKSアクセスエントリ**を使用してください。クラスターの認証モードは`API`または`API_AND_CONFIG_MAP`である必要があります。既存クラスターのモードを変更する前に、マッピング移行と管理者の復旧手段を準備してください。`aws-auth`は非推奨ですが、IAMマッピングの唯一の方法ではありません。

この例では、既存の開発者IAMロールを`dev-readers`に対応付けます。IAM IDとアクセスエントリだけではKubernetes RBACオブジェクトは作成されません。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.accessConfig.authenticationMode

aws eks create-access-entry --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --principal-arn "${DEV_ROLE_ARN:?Existing developer IAM role}" \
  --type STANDARD --kubernetes-groups dev-readers
```

管理者が既存の`dev`名前空間にこのRoleとRoleBindingを適用します。Secretや変更権限を含まず、Pod/Deploymentの読み取りを許可します。ワークロード作成権限から名前空間内のSecretを使用できる可能性があるため、別途検討が必要です。

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

ロールを引き受ける権限を持つIDを使用して、専用kubeconfigを作成し、実際の権限を確認します。別のRBAC許可またはEKSアクセスポリシーで追加の権限が付いていない限り、最初の確認は許可され、次は拒否されるはずです。

```bash
aws eks update-kubeconfig --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --role-arn "${DEV_ROLE_ARN:?}" --kubeconfig "${DEV_KUBECONFIG:?Use a dedicated file}"
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get pods -n dev
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get secrets -n dev
```

代替として、アクセスエントリに名前空間を限定したEKSアクセスポリシーを関連付けることもできます。アクセスポリシーとRBAC許可は加算されます。IAMポリシーだけではKubernetes権限は付与されません。IRSA/Pod IdentityはPodがAWS APIを呼び出すための別経路です。通常の開発者に`system:masters`を付与したり、`aws-auth` ConfigMap全体を上書きしたりしないでください。

</details>

5. EKSのバージョンサポートについて正しい説明はどれですか？
   * A) すべてのバージョンが無期限にサポートされる
   * B) すべてのバージョンが12か月でサポート終了する
   * C) 常に最新バージョンと直前3バージョンだけがサポートされる
   * D) EKSリリース後14か月の標準サポートと、有料延長サポートが12か月ある

<details>
<summary>解答を表示</summary>

**解答: D) EKSリリース後14か月の標準サポートと、有料延長サポートが12か月ある**

EKSのマイナーバージョンは**EKSでのリリース日から14か月間、標準サポート**され、その後12か月間は有料の延長サポートを受けられます。起算日は上流Kubernetesのリリース日ではありません。

* 2026年10月12日時点の公式一覧では、標準サポートは**1.34–1.37**、延長サポートは**1.31–1.33**です。EKS 1.37は上流の2026年8月26日リリース後、2026年10月1日に利用可能になりました。
* 延長サポートはデフォルトで有効です。`STANDARD`アップグレードポリシーを選ぶと延長サポートを使わず、標準サポート終了後に自動アップグレードの対象になります。
* 延長サポート終了後、AWSはコントロールプレーンをサポート対象バージョンに自動アップグレードします。正確な実行時刻は保証されないため、計画的にアップグレードしてください。
* コントロールプレーンの自動アップグレードだけで、マネージド/セルフマネージド/Hybrid Nodesが更新されるわけではありません。Fargate Podの再作成やアドオン更新も別途計画してください。Auto Modeノードはマネージド更新に従います。
* サポート中のバージョンにはセキュリティパッチが提供されます。すべてのバージョンを無期限に使い続けることはできません。サポート終了後のバージョンでは新しいクラスターを作成できません。

実際のリージョンのリリースカレンダーとバージョン情報を確認してください。アドオンのメタデータを検索しても、クラスターのバージョンサポート一覧の代わりにはなりません。

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,upgradePolicy:upgradePolicy}' --output json
```

アップグレードの予定を立て、削除済みAPI/互換性を調べ、本番以外の環境でテストし、アプリケーション/データ復旧の準備をして、1回に1つのマイナーバージョンずつ進めます。EKSは少なくとも3つのバージョンを標準サポートしていますが、「常に最新とその前3つだけ」という固定ルールではありません。

</details>

## 公式リファレンスと検証範囲

- [EKSのバージョンライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKSアクセスエントリ](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Pod IdentityとIRSA](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)
- [Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Auto Modeのロードバランシング](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [FSx CSI構成とPVC容量](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)
- [Fargateの制限](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Prefix Delegation](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [カスタムネットワーキング](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)
- [EKSの料金](https://aws.amazon.com/eks/pricing/)
- [Fargateの料金](https://aws.amazon.com/fargate/pricing/)
- [eksctl 0.230.0のスキーマ](https://github.com/eksctl-io/eksctl/blob/v0.230.0/pkg/apis/eksctl.io/v1alpha5/assets/schema.json)
- [LBC 3.5.0のインストール](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/installation.md)
- [Metrics Server 0.9.0の互換性](https://github.com/kubernetes-sigs/metrics-server/blob/v0.9.0/README.md)

これは公式ドキュメントとリリーススキーマに基づく静的なレビューです。クラスター/IAM/ロードバランサーの作成、アプリケーションの展開、アップグレード/ロールバック、NGINXの実行、負荷テスト、コスト測定は実施していません。例で期待される動作は、測定結果ではありません。
