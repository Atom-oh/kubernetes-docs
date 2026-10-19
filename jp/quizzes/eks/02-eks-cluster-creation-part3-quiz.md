# EKS クラスター作成クイズ - パート 3

> **最終更新日**: 2026年9月11日

このクイズでは、EKS のネットワーキング、ノード容量、マルチテナンシー、自動スケーリング、ノードセキュリティを扱います。コマンドとマニフェストは学習用の例です。クラウドへのデプロイは実行されておらず、このレビュー中にエンドツーエンドの動作もテストされていません。使用する前に、対象アカウント、リージョン、kubeconfig、互換性のあるアドオンバージョン、リソースの所有者を確認してください。

## 基本概念に関する質問

1. 従来の IPv4 セカンダリ IP 計算では、ENI と ENI ごとのアドレス上限は何によって決まりますか？
   * A) Namespace 名
   * B) EC2 インスタンスタイプ
   * C) Service 名
   * D) Deployment 名

<details>
<summary>回答を表示</summary>

**回答: B) EC2 インスタンスタイプ**

十分なサブネットアドレスがあり、カスタムネットワーキングも Pod 用セキュリティグループも使用していない Linux IPv4 の**セカンダリ IP モード**では、インスタンスタイプによって ENI と ENI ごとのアドレス上限が決まります。これは従来のノード Pod 上限の推定値であり、「Pod あたりの IP アドレス数」ではありません。

従来の計算式では、**各** ENI のプライマリアドレスを差し引きます。

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
```
追加の 2 は、`aws-node` と `kube-proxy` に対する歴史的な host-network の許容量です。この表はセカンダリ IP の計算を示しています。すべての AMI、CNI モード、マネージドノードグループにおける実効 `maxPods` を示すものでは**ありません**。

| インスタンスタイプ | 最大 ENI 数 | ENI あたりの IP 数 | 最大 Pod 数 |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4           | 11       |
| t3.medium     | 3        | 6           | 17       |
| m5.large      | 3        | 10          | 29       |
| m5.xlarge     | 4        | 15          | 58       |
| m5.2xlarge    | 4        | 15          | 58       |
| m5.4xlarge    | 8        | 30          | 234      |
| c5.large      | 3        | 10          | 29       |
| c5.xlarge     | 4        | 15          | 58       |
| r5.large      | 3        | 10          | 29       |
| r5.xlarge     | 4        | 15          | 58       |

**実際の容量と EC2 の上限を確認する:**

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,CAPACITY:.status.capacity.pods,ALLOCATABLE:.status.allocatable.pods
aws ec2 describe-instance-types --region us-west-2 \
  --instance-types m5.large m5.4xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4PerENI:NetworkInfo.Ipv4AddressesPerInterface}'
```
ノード上限に達していなくても、サブネットの枯渇によって Pod の作成が停止することがあります。CPU/メモリーの requests、その他の host-network Pod、カスタムネットワーキング、Pod 用セキュリティグループ、kubelet の設定も影響します。マネージドノードグループの `maxPods` は、vCPU が 30 未満のインスタンスでは 110、それ以外では 250 が上限となり、上記の計算式でより大きな値が得られても変わりません。

IPv4 プレフィックス委任では、ENI のセカンダリアドレスの**スロット** 1 つに `/28` が割り当てられます。1 つの ENI に複数のプレフィックスを配置できます。サブネットのアドレス空間が増えるわけではありません。前提条件と移行方法については、質問 5 を参照してください。

カスタム AL2023 AMI では、適切な値を計算してテストしたうえで、NodeConfig の `spec.kubelet.config.maxPods` を設定してください。カスタム AMI ID を指定しないマネージドノードグループでは、EKS が推奨値を計算します。kubelet の上限だけを引き上げても、IP アドレスやコンピューティング容量が使えるようになるわけではありません。存在しない eksctl の `--kubelet-extra-args` オプションは渡さないでください。

</details>

2. Pod を選択する NetworkPolicy がない場合、その Pod の NetworkPolicy による分離状態はどうなりますか？
   * A) 分離されない。他のネットワーク制御は適用される
   * B) 同一 Namespace のトラフィックのみ許可される
   * C) 明示的な許可ルールが必要
   * D) すべてのトラフィックが拒否される

<details>
<summary>回答を表示</summary>

**回答: A) 分離されない。他のネットワーク制御は適用される**

ある方向のトラフィックについて Pod を選択するポリシーがない場合、Kubernetes NetworkPolicy はその方向を分離しません。これは、セキュリティグループ、ルートテーブル、NACL、その他のポリシー API、アプリケーションのリスナーを無視できるという意味では**ありません**。

Amazon VPC CNI は、サポートされている Linux EC2 ノードで有効化すると、ネイティブの NetworkPolicy 適用機能を提供します。現在の標準ポリシーおよび管理者ポリシーのガイダンスでは、VPC CNI 1.21 以降、カーネル 5.10 以降が必要です。選択したアドオンとの互換性を確認してください。この適用経路の対象には Windows と Fargate は含まれません。Deployment など、コントローラーが管理する Pod を使い、AWS のインターフェイスと Service ポートに関する制限を確認してください。

AWS VPC ネットワーキングと組み合わせた Calico ポリシー、および Cilium AWS-CNI chaining も選択肢ですが、それぞれ独自のインストール要件があります。設定していない 2 つ目の CNI をインストールしたり、ポリシーエージェントを意図せず重ねて導入したりしないでください。AWS Network Firewall はルーティングされる VPC トラフィックをフィルタリングしますが、Kubernetes NetworkPolicy のセレクターを実装するものではありません。

以下の例は、**新規の専用** `network-policy-lab` Namespace 用です。最初のポリシーは ingress のみを分離します。次の 2 つは特定のトラフィックを許可します。`prod` の peer には、組み込み Namespace ラベルと backend Pod ラベルの両方が必要です。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: network-policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: backend}
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector:
        matchLabels: {app: frontend}
    ports:
    - {protocol: TCP, port: 8080}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prod-to-database
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: database}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: prod
      podSelector:
        matchLabels: {app: backend}
    ports:
    - {protocol: TCP, port: 5432}
```
egress を分離する場合は、実際の DNS 経路とアプリケーションの依存先を個別に許可してください。接続拒否を有意な結果とみなせるのは、基準となる接続、DNS、readiness、許可された正の対照が成功した後だけです。手軽なテストとして `kube-system` や共有の `default` Namespace に包括的な deny ポリシーを適用しないでください。

</details>

3. プライベート IPv4 サブネットで一般的なインターネット egress 経路はどれですか？
   * A) IGW をサブネットにアタッチする
   * B) パブリック NAT gateway を経由して VPC IGW にルーティングする
   * C) 各 Pod に Elastic IP を割り当てる
   * D) プライベート NAT gateway から IGW を直接経由する

<details>
<summary>回答を表示</summary>

**回答: B) パブリック NAT gateway を経由して VPC IGW にルーティングする**

パブリック IPv4 インターネットへの egress が必要なプライベート IPv4 ノードと Pod には、プライベートサブネットのデフォルトルートを、**パブリックサブネット内のパブリック NAT gateway** に向ける設計がよく使われます。そのパブリックサブネットは、**VPC** にアタッチされたインターネットゲートウェイへルーティングし、NAT gateway には Elastic IP を割り当てます。NAT instance も選択肢ですが、追加のルーティング、送信元/送信先チェック、運用上の要件があります。

デフォルトの IPv4 VPC CNI SNAT 動作では、VPC 外への Pod トラフィックは最初にノードのプライマリ IPv4 アドレスを使用します。パブリック IPv4 アドレスを持ち、IGW へのルートがあるパブリックノードでは、異なる経路を使用できます。ネイティブ IPv6 の egress には egress-only internet gateway を使用できます。また、VPC endpoint 経由の AWS サービスアクセスにはインターネット NAT が不要な場合があります。すべての Pod に NAT が必須だと考えないでください。

**1 つの AZ を使用する CloudFormation のルーティング例:** この例はパブリック/プライベートルートの関連付けを示すものであり、完全な EKS VPC ではありません。EKS クラスターのサブネットには少なくとも 2 つの AZ が必要です。AZ ごとに NAT を配置する設計では、AZ 間の依存を避けるため、各 AZ に NAT gateway とプライベートルートを設けることを検討してください。NAT gateway とパブリック IPv4 アドレスには料金が発生します。クラスターをデプロイする場合は、概念ガイドにある EKS VPC の完全なテンプレートを確認してください。

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: One-AZ IPv4 NAT routing demonstration; not a complete EKS VPC
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway

  PublicSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PrivateSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet1
      RouteTableId: !Ref PrivateRouteTable
```
`SubnetRouteTableAssociation` リソースは不可欠です。関連付けられていないテーブルにルートを作成しても、どちらのサブネットのルートも変わりません。

独立したレビューを経てデプロイした後、実際の ID とルートを確認してください。代わりに CLI で NAT gateway を作成する場合は、返された ID を記録し、ルートを作成する前に `nat-gateway-available` になるまで待機してください。NAT の作成に失敗した場合は、ワークフローを中止してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region}"
: "${VPC_ID:?Set the deployed VPC ID}"
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
aws ec2 describe-nat-gateways --region "$AWS_REGION" \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[].{Id:NatGatewayId,Subnet:SubnetId,State:State}'
```
eksctl の `vpc.nat.gateway: Single` は、eksctl が管理する VPC 作成ワークフローでは有効ですが、単一 AZ への依存が生じます。`HighlyAvailable` は各 AZ にゾーン単位の NAT を作成します。これらのオプションは、任意の既存サブネットのルーティングを修正するものではありません。ラボ用スタックを削除する場合は、依存するワークロード/ENI を削除した後、自分が作成したリソースだけを削除してください。NAT とその EIP が解放されたことを確認してください。

</details>

4. Pod の設定のうち、Pod 用 branch ENI を使わずにノードネットワーキングを共有するものはどれですか？
   * A) 一致する Pod ラベル
   * B) 一致する ServiceAccount ラベル
   * C) hostNetwork: true
   * D) 選択された SecurityGroupPolicy

<details>
<summary>回答を表示</summary>

**回答: C) hostNetwork: true**

host-network Pod はノードのネットワーク Namespace とセキュリティグループを共有します。Pod 用セキュリティグループでは、独自のネットワーク Namespace を持つ選択対象 Pod に branch ENI を使用します。

この Linux EC2 の例では、サポート対象の trunking インスタンスタイプ、互換性のある VPC CNI、クラスターのロールに付与する `AmazonEKSVPCResourceController` の権限、`ENABLE_POD_ENI=true` が前提条件です。EC2 の `t` ファミリーと EKS Auto Mode はこの機能をサポートしていません。DNS、コントロールプレーンおよびアプリケーションのルール、branch ENI の容量、`POD_SECURITY_GROUP_ENFORCING_MODE` を確認してください。SNAT とポリシーの動作はモードによって異なります。古い CNI マニフェストを適用するのではなく、アドオンの所有者が定める設定手順を使用してください。

SecurityGroupPolicy は `podSelector` または `serviceAccountSelector` の**どちらか**で Pod を選択します。Pod の選択に特別に作成した ServiceAccount は必須ではありません。`ENIConfig` はカスタムネットワーキング用のリソースであり、Pod 用セキュリティグループを使うだけなら必要ありません。

以下の ServiceAccount セレクターの代替例を使う場合は、まず専用の `pod-sg-lab` Namespace を作成し、SG のプレースホルダーを正しい VPC 内にあるレビュー済みの既存グループに置き換え、前提条件を満たしてください。この待機中のクライアントはセレクターによる選択を示すものであり、データベースへの接続を証明するものではありません。一致する ServiceAccount ラベルと Pod の `serviceAccountName` の両方を設定しています。

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: pod-sg-lab
spec:
  serviceAccountSelector:
    matchLabels:
      role: db-client
  securityGroups:
    groupIds:
    - sg-REPLACE_WITH_REVIEWED_GROUP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: db-client
  namespace: pod-sg-lab
  labels:
    role: db-client
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: pod-sg-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: db-client}
  template:
    metadata:
      labels: {app: db-client}
    spec:
      serviceAccountName: db-client
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
代わりに `serviceAccountSelector` を `podSelector: {matchLabels: {app: db-client}}` に置き換えることもできます。ポリシーと選択対象 Pod は同じ Namespace に置いてください。**新しく作成された** Pod の branch ENI と、実際に許可/拒否される接続を確認してください。ポリシーを作成しても、稼働中の Pod に遡って適用されることはありません。テスト後はこのラボ Namespace とそのポリシーだけを削除し、他のリソースで使用中の SG は削除しないでください。

</details>



5. IPv4 プレフィックス委任による容量面での主な利点は何ですか？
   * A) Pod 間通信の高速化が保証される
   * B) ノードあたりの Pod IP 容量が増える
   * C) 各 Pod にパブリック IPv4 アドレスが割り当てられる
   * D) ネットワーク分離が自動的に行われる

<details>
<summary>回答を表示</summary>

**回答: B) ノードあたりの Pod IP 容量が増える**

Linux IPv4 プレフィックスモードでは、`/28`（16 アドレス）1 つで ENI のセカンダリアドレススロットを 1 つ消費します。1 つの ENI に複数のプレフィックスをアタッチできますが、ENI の最大数自体は増えません。kubelet とリソースの上限の範囲内で、IP アドレスに基づく Pod 密度を上げ、アドレス割り当て API の処理を減らせる可能性があります。

`m5.large` の場合、従来のセカンダリ IP 計算では Pod 数は 29 です。プレフィックスモードを使う互換性のあるマネージドノードグループでは、制限のない「110 超」ではなく、推奨 `maxPods` として 110 を使用できます。理論上のアドレススロット数は、アプリケーション容量を保証するものではありません。

**前提条件とトレードオフ:**

* サポートされている Nitro インスタンスと互換性のある CNI を使用してください（Linux IPv4 の歴史的な最低バージョンは 1.9.0 です。現在サポートされているビルドを選んでください）。
* サブネットには連続した `/28` ブロックが必要です。サブネットが断片化していると、個別の空き IP が多くても `InsufficientCidrBlocks` で失敗する場合があります。サブネット CIDR 予約を使ってプレフィックス用の領域を確保できます。
* プレフィックスはブロック単位で実際のサブネットアドレスを消費します。CIDR を拡張するものでも、IP 消費量の削減、利用効率の向上、コストの削減を保証するものでもありません。
* `WARM_PREFIX_TARGET` は余分に確保するプレフィックス数を指定します。`WARM_IP_TARGET` は余分に確保する IP 数を指定します。`MINIMUM_IP_TARGET` は割り当ての最低総数を設定します。後者の 2 つを設定すると、`WARM_PREFIX_TARGET` より優先されます。Pod 起動レイテンシーと未使用アドレスの消費量のバランスを見て調整してください。
* 置き換え用ノードグループを計画し、cordon/drain を使って制御された移行を実施してください。変数を切り替えてすべての Pod を再起動するだけでは不十分です。PDB、ボリューム、予備容量、ロールバックを確認し、旧グループを削除する前に新しいノードを検証してください。

以下は**新しいクラスターの設定例**であり、既存クラスターの更新コマンドではありません。プライベート API アクセスを使用するため、管理者にはルーティングされた管理経路が必要です。バージョンを指定しない場合は互換性のある EKS のデフォルト CNI ビルドが選ばれます。デプロイ前に実際に解決されたバージョンを記録し、確認してください。`withOIDC` は eksctl の CNI IAM 統合に関係します。生成されるロールを確認してください。サイズの上下限を設定しても、オートスケーラーはインストールされません。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: prefix-demo
  region: us-west-2
  version: "1.36"
vpc:
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
iam:
  withOIDC: true
addons:
- name: vpc-cni
  configurationValues: |
    {"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
managedNodeGroups:
- name: prefix-linux
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  privateNetworking: true
  disableIMDSv1: true
```

</details>

6. CoreDNS が読み込む Corefile を格納している Kubernetes オブジェクトはどれですか？
   * A) ノードのセキュリティグループ
   * B) coredns ConfigMap
   * C) StorageClass
   * D) PodDisruptionBudget

<details>
<summary>回答を表示</summary>

**回答: B) coredns ConfigMap**

`coredns` ConfigMap には `data.Corefile` が格納されています。適切な**設定の管理者**は、CoreDNS が EKS マネージドアドオンかセルフマネージドかによって異なります。

マネージドアドオンでは、AWS コンソールと `aws eks update-addon --configuration-values` のどちらでも、サポートされているフィールドをカスタマイズできます。ConfigMap を直接編集すると、アドオンの更新時に上書きされる場合があります。カスタム Corefile 全体をアドオンの `corefile` 設定キーに保存してください。既存の設定キーを保持し、正確なアドオンバージョンのスキーマを確認してください。

編集前に現在の設定を保存するため、新しいローカル作業ディレクトリを使用してください。

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?Set the cluster}"
: "${EXAMPLE_REGION:?Set the Region}"
: "${EXAMPLE_KUBECONFIG:?Set a private kubeconfig path}"
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --addon-name coredns > coredns-addon-before.json
COREDNS_VERSION=$(jq -er '.addon.addonVersion' coredns-addon-before.json)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --query configurationSchema --output text > coredns-schema.json
jq -e '(.addon.configurationValues // "{}") | fromjson | select(type == "object")' \
  coredns-addon-before.json > coredns-values-before.json
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  get configmap coredns -o json | jq -er '.data.Corefile' > Corefile.reviewed
```
`Corefile.reviewed` を編集し、このインストールで必要な Kubernetes ゾーン、forwarding、`ready`、health、monitoring プラグインを保持してください。以下は個別のカスタマイズ例であり、置き換え用の Corefile ではありません。

* 実際の内部アドレスを使って、既存の server block に静的レコードを追加します。

```text
hosts {
    10.0.0.1 example.com
    10.0.0.2 api.example.com
    fallthrough
}
```
* 条件付き forwarder には別の server block を使います。上流に到達できること、またこの CoreDNS service にループバックしないことを確認してください。

```text
example.org:53 {
    errors
    forward . 10.0.0.53
    cache 30
}
```
* 既存の cache stanza を置き換え、重複して追加しないでください。`prefetch` の期間には単位が必要です。

```text
cache {
    success 10000
    denial 5000
    prefetch 10 10m 10%
}
```
* オプションのエラー分類別クエリログ（ログ量と機密性のある名前を確認してください）:

```text
log {
    class error
}
```
`autopath` はサーバー側で検索パスを補完するための独立したプラグインであり、`kubernetes` のサブディレクティブではありません。Kubernetes block 内の `autopath off` は無効です。既存の `autopath @kubernetes` を無効にするには、そのディレクティブを削除してください。そもそも有効化されていないインストールに追加しないでください。

スキーマと構文を確認した後、**同じ**アドオンバージョンを更新してください。

```bash
# After reviewing the complete Corefile and existing configuration:
jq --rawfile corefile Corefile.reviewed '.corefile = $corefile' \
  coredns-values-before.json > coredns-values-reviewed.json
COREDNS_UPDATE_ID=$(aws eks update-addon \
  --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --resolve-conflicts PRESERVE \
  --configuration-values file://coredns-values-reviewed.json \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --update-id "$COREDNS_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
応答がまだ `InProgress` の場合があります。この更新 ID を再確認し、`Successful` になるまで待ってください。失敗した場合は停止し、別の変更を行う前にエラーを調べてください。その後、Deployment の readiness、ログ、内部 Service の名前解決、カスタム DNS ケースを確認してください。必要に応じて、同じ管理者を通じて保存済みの設定に戻してください。

セルフマネージド CoreDNS では、レビュー済み ConfigMap を GitOps/マニフェストの管理元で編集してください。`reload` を使用している場合、ConfigMap の投影と reload 間隔の後に Corefile の変更が検出されます。常に再起動が必要なわけではありません。reload エラーと DNS の動作を監視してください。Deployment の設定を変更した場合は、ロールアウトが必要な場合があります。

**スケーリングとリソース:** 選択したバージョンが AWS の前提条件を満たす場合、EKS マネージド CoreDNS は `autoScaling` 設定オブジェクトをサポートします。レプリカ数を管理するコントローラーは 1 つだけにしてください。以下の CPU HPA は**セルフマネージド CoreDNS 向けの代替案**であり、Metrics Server と CPU requests が必要です。EKS CoreDNS autoscaling と併用しないでください。

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns-autoscaler
  namespace: kube-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: coredns
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```
レプリカ数 2～10 と目標値 60% は例であり、実測に基づくサイジングではありません。メモリー、CPU スロットリング、キャッシュの増加、トポロジー、DNS レイテンシーを確認してください。コンテナ配列のインデックスでリソースオブジェクト全体を置き換えるのではなく、アドオンのスキーマまたはセルフマネージドワークロードの管理元を通じてリソースを変更してください。

</details>

7. 1 つの EKS クラスターを共有する信頼済みチームの論理的な分離に役立つ組み合わせはどれですか？
   * A) Namespace のみ
   * B) Namespace、RBAC、適用されるポリシー、クォータ
   * C) ノードセレクターのみ
   * D) 共有の cluster-admin ロール

<details>
<summary>回答を表示</summary>

**回答: B) Namespace、RBAC、適用されるポリシー、クォータ**

互いに信頼できるチームがクラスターを共有する場合、Namespace、RBAC、適用されるネットワークポリシー、クォータの組み合わせによって、有用な論理的分離を実現できます。悪意のあるテナントに対する万能な解決策ではありません。

プラットフォーム管理者は、新しい `tenant-a`/`tenant-b` Namespace を作成し、適切な Pod Security Admission ポリシーを適用します（この Linux EKS 1.36 の例では、バージョン `v1.36` の Restricted を使用）。以下は `tenant-a` のポリシー一式です。`tenant-b` にも同等のレビュー済みポリシーを適用してください。また、`tenant-a-users` の認証済みグループマッピングも必要です。

アプリケーションの権限は明示的に設定します。この Role を使って、テナントが ResourceQuota、LimitRange、NetworkPolicy、Role、RoleBinding を直接変更することはできません。クラスター範囲のリソースはプラットフォーム側で管理します。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
**制限と検証:**

* ワークロードの作成時に、アクセス可能な ServiceAccount を使用したり、Namespace 内の Secret をマウントしたりすることは可能です。この Role は、テナント内の Secret の機密性を守る境界ではありません。Admission ポリシーで許可する ID、マウント、セキュリティ設定を適用してください。プラットフォームの認証情報はテナントの Namespace の外に置いてください。
* DNS ルールは、`kube-system` に `k8s-app=kube-dns` ラベルの通常の CoreDNS Pod があることを前提としています。NodeLocal DNSCache や別の DNS 経路を使用する場合は調整してテストしてください。このルールで許可されるのは DNS クエリであり、system Pod への egress 全般ではありません。また、Namespace をまたぐ DNS 名を隠すものでもありません。
* クォータは、受付可能なリソース requests/個数に上限を設けます。物理ノードを予約したり、帯域幅を保証したり、ノイジーネイバーをなくしたりするものではありません。LimitRange の値は説明用のデフォルトです。
* テナントを受け入れる前に、テナント ID で実効権限とポリシー適用を確認してください。許可された接続、テナント間の拒否接続、クォータ違反による拒否のケースもテストします。
* 専用ノードグループは一部の共有を減らしますが、ノードセレクター/taint だけではセキュリティ境界になりません。より強い分離が必要な場合は、サンドボックス化されたランタイム、仮想コントロールプレーン、または別々のクラスター/アカウント/ネットワークを検討し、共有依存関係と運用コストも評価してください。

Namespace の共有は、コントロールプレーンのオーバーヘッドを減らし、運用の集中化を簡素化できます。設計を決めるのは必要な分離レベルであり、普遍的に「最適」だという主張ではありません。

</details>

8. EC2 インスタンスタイプの技術的な容量を、それ自体では変えないものはどれですか？
   * A) vCPU とメモリーのサイズ
   * B) ネットワークとストレージの上限
   * C) 表示専用の名前タグ
   * D) ENI とアドレスの上限

<details>
<summary>回答を表示</summary>

**回答: C) 表示専用の名前タグ**

インスタンスを選択する際は、CPU、メモリー、アクセラレーターの要件、アーキテクチャに対応したイメージ/AMI とドライバー、Pod 密度、ネットワーク帯域幅、EBS/インスタンスストアの性能、AZ での提供状況、中断への許容度、コストを考慮してください。サポート対象の AMI、ドライバー、機能を通じて Kubernetes のバージョンが関係することもあります。無関係ではありません。

以下のファミリーの例はワークロードの傾向を示すものであり、現時点の価格/性能ランキングではありません。`m5` は汎用、`r5` はメモリー最適化、`c5` はコンピューティング最適化です。Graviton の代替インスタンスには、Arm 互換のイメージと依存関係が必要です。GPU ワークロードには、適切なアクセラレーテッド AMI とデバイスプラグインも必要です。インスタンスストアのデータは一時的なものであり、ラベルだけではデータベースの耐久性や配置が保証されません。

以下は、レビュー済みの既存クラスター向けの**代替ノードグループ設定ファイル**です（`eksctl create nodegroup -f ...`）。未使用のグループ名と、必要な egress/endpoint が設定済みのプライベートサブネットを使います。実際のリージョン/AZ での提供状況を確認してください。上下限を設定しても Cluster Autoscaler はインストールされません。バッチグループの初期値を 0 にする場合は、正しく設定されたオートスケーラーか手動スケーリングが必要です。

**Web サーバー**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: web-servers
  instanceType: m5.large
  minSize: 2
  maxSize: 10
  labels:
    role: web
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**データベースのワークロード**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: database-nodes
  instanceType: r5.xlarge
  minSize: 3
  maxSize: 5
  labels:
    role: database
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**バッチ処理**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: batch-processors
  instanceType: c5.2xlarge
  minSize: 0
  maxSize: 20
  labels:
    role: batch
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**中断の可能性がある Spot ワーカー**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: spot-workers
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m5ad.large
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    lifecycle: spot
  amiFamily: AmazonLinux2023
  privateNetworking: true
```
EKS では、標準サポートが 14 か月、その後に延長サポートが 12 か月提供されます。上流の Kubernetes リリースとは別に、EKS のサポートカレンダー、アップグレード要件、アドオンとの互換性を確認してください。これらの例は、コスト削減や容量を実測したと主張するものではありません。

</details>

9. drain 中の自発的な Pod eviction を制約する Kubernetes オブジェクトはどれですか？
   * A) StorageClass
   * B) PodDisruptionBudget
   * C) ConfigMap
   * D) IngressClass

<details>
<summary>回答を表示</summary>

**回答: B) PodDisruptionBudget**

PDB は Eviction API を通じて自発的な eviction を制約します。更新戦略の一部ではありますが、可用性を保証するものではありません。ノード障害、Pod の直接削除、Deployment 自身のローリングアップデートは、PDB では防げません。

レビュー済みの `update-lab` Deployment が `app=my-app` ラベルの 3 つのレプリカを持つ場合、この例では、選択された正常な Pod が 2 つ以上残るときに限り eviction を許可します。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
代替案として `maxUnavailable: "50%"` を使うこともできます。予算フィールドはいずれか 1 つだけ指定してください。割合は**切り上げ**られるため、この設定では 3 つ中 2 つ、または 1 つ中 1 つの Pod が利用不可になることを許します。少なくとも半数が残るという約束ではありません。quorum、readiness、ワークロードの動作、スケジュール可能な予備容量に基づいて予算を選択してください。

マネージドノードグループの `DEFAULT` 更新では、選択した旧ノードを drain する前に置き換え用容量を起動します。`MINIMAL` は、選択した旧ノードを先に終了させることで、一時的に必要となる容量を減らします。`maxUnavailable` は同時に利用不可となるノード数を制御します。PDB は Pod の eviction を別途制約します。drain がブロックされた際の定型的な対応として `--force` を使わないでください。Pod の eviction 保護を上書きする可能性があります。

ノードのバージョン更新を開始する**前に**、ノード更新ポリシーを設定し、この特定の更新が成功するまで待ってください。

```bash
set -euo pipefail
NODEGROUP_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":1,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODEGROUP_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
その ID の `describe-update` を確認し、`Successful` になるまで待ちます。`Failed`/`Cancelled` の場合は明示的に処理してください。元の eksctl コマンド `update nodegroup --max-unavailable` は、サポートされている代替手段ではありません。実際の PDB の `disruptionsAllowed`、readiness、アプリケーションの健全性、ボリュームの再配置を確認してください。レプリカ 3 つの構成は一例であり、普遍的な最小数ではありません。

</details>

10. Pod の CPU とメモリーの requests を推奨または変更するコントローラーはどれですか？
   * A) Cluster Autoscaler
   * B) Karpenter
   * C) Horizontal Pod Autoscaler
   * D) Vertical Pod Autoscaler

<details>
<summary>回答を表示</summary>

**回答: D) Vertical Pod Autoscaler**

VPA は Pod のリソース requests を推奨または更新します。HPA はレプリカ数を変更します。**どちらも**、間接的にノード需要を変化させる可能性があります。どちらもマネージドノードグループの ASG を直接管理するものではありません。

| コンポーネント | 制御対象 |
| --- | --- |
| Cluster Autoscaler | スケジュール可能性と安全な削除に基づく、検出済みの既存ノードグループ/ASG の desired capacity |
| Karpenter | NodePool と EC2NodeClass を通じて選択する独自の NodeClaims/EC2 容量。マネージドノードグループの ASG は対象外 |
| HPA / KEDA | リソース/カスタム/外部メトリクスまたはイベントに基づくワークロードのレプリカ数 |
| VPA | 更新モードに応じた Pod リソースの推奨値/requests |

**Cluster Autoscaler:** クラスターと同じ Kubernetes マイナーバージョンを使用してください。EKS 1.36 の例では、Chart 9.59.0 にイメージ `v1.36.1` を明示的に指定する必要があります（デフォルトのイメージは 1.35.0 です）。まず、レビュー済みのタグ範囲付き IAM 権限と ASG 検出タグを持つ専用 `cluster-autoscaler` ServiceAccount を設定します。インストール前に、RBAC、イメージ、引数をレンダリングして確認してください。

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
ローカルストレージの保護を安易に無効化したり、同じ desired capacity に対して ASG の target-tracking/predictive ポリシーと Cluster Autoscaler を競合させたりしないでください。

**Karpenter を使う場合:** 互換性のあるコントローラーを別途インストールし、認可してください。AMI ID、ノードロール、検出タグの値を、このクラスター用にレビュー済みのリソースに置き換えてください。AMI は AL2023、Kubernetes バージョン、アーキテクチャに適合している必要があります。`al2023@latest` を暗黙に選択するのではなく、AMI ID またはテスト済みのバージョン付きエイリアスを固定してください。以下の上限と集約までの時間は例であり、実測に基づくサイジングやプロビジョニング速度の保証ではありません。

```yaml
# Karpenter NodePool (karpenter.sh/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
# Karpenter EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_VERIFIED_AL2023_AMI
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
**HPA:** この例では、`autoscaling-lab` に既存の `my-app` Deployment があり、Metrics Server と CPU requests が設定されている必要があります。

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
**VPA:** まず VPA の CRD/コントローラーをインストールしてください。推奨値のみのモードから始め、明示的にサポートされている更新モードを選ぶ前に推奨値を確認してください。

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: autoscaling-lab
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```
`Off` では Pod リソースは変更されません。推奨値の適用に Pod の再作成またはサポート対象のインプレースリサイズが必要となるかどうかは、VPA/Kubernetes のバージョンと設定によって異なります。どのモードでも再起動が必ず起きるとは限りません。CPU utilization によって HPA が同じワークロードを制御しているときに CPU requests を更新すると、utilization の分母を介してフィードバックが発生します。推奨値のみの例では、連携を考慮した設計をレビューするまで、この競合を避けられます。

</details>

## 実践演習

### 演習 1: EKS クラスターでの NetworkPolicy の実装

**シナリオ:** AWS VPC CNI による IP 割り当てを使いつつ、frontend → backend と backend → database を許可し、frontend → database を拒否します。AWS VPC CNI を使いながら Calico を学ぶという当初の目的を維持してください。

**対象範囲:** 既存の破棄可能な Linux IPv4 EKS クラスター、競合するグローバル/階層ポリシーがないこと、標準の CoreDNS、管理者がレビューした Calico のインストール。本演習は接続性を確認するものであり、本番向けのマイクロサービス/データベース構成例ではありません。この監査ではクラウドへのインストールとトラフィックテストは実行されていません。


<details>
<summary>解決策を表示</summary>

**1. ポリシーエンジンを準備する。** Calico EKS の公式な **Amazon VPC networking** 手順に従ってください。Calico の適用機能と競合するため、ネイティブ AWS VPC CNI NetworkPolicy はその設定管理元を通じて無効にします。`aws-node` のネットワーキング設定は維持してください。`ANNOTATE_POD_IP=true` 設定を有効にし、ServiceAccount に Pod を patch する権限を付与します。この専用 RBAC の例は、不正な YAML をアドオンの ClusterRole に追記せずに、その権限を追加します。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-annotation
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-annotation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-annotation
subjects:
- kind: ServiceAccount
  name: aws-node
  namespace: kube-system
```
RBAC を保存して確認した後、対象の `aws-node` ServiceAccount にのみ適用してください。環境変数は、マネージドアドオンまたはセルフマネージドマニフェストの管理元を通じて設定します。ロールアウトとアノテーションの動作が正常になるまで次に進まないでください。すでに Calico がインストールされている場合は、以下の新規インストール用コマンドを実行するのではなく、既存のものを確認して再利用してください。

```bash
# Download pinned manifests for inspection; do not overwrite an existing installation.
curl --fail --location --output calico-crds.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
curl --fail --location --output tigera-operator.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
# After review, on the intended new lab installation:
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" create -f calico-crds.yaml
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create -f tigera-operator.yaml
```
Operator の CRD が確立された後、レビュー済みの次の `Installation` と `APIServer` リソースを作成します。Operator をインストールしただけでは、AWS VPC ネットワーキングは設定されません。`projectcalico.org/v3` ポリシーの例には API server が必要です。

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
```

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get tigerastatus
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get apiservice v3.projectcalico.org
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n calico-system get pods
```
Calico コンポーネントと集約 API が利用可能であることを確認してから、以下の実際の適用確認に進んでください。ノードが `Ready` であるだけでは不十分です。オプションの Goldmane/Whisker UI はこの演習には不要です。

**2. 所有する Namespace と一時的なデータベース認証情報を作成する。** 以降のスニペットは同じ Bash セッションで実行してください。Namespace 名と UID を記録することで、別の Namespace を対象として誤ってクリーンアップすることを防ぎます。

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed lab cluster kubeconfig}"
NETWORK_LAB_DIR=$(mktemp -d /tmp/eks-calico-lab.XXXXXX)
NETWORK_NAMESPACE="calico-quiz-$(date +%s)-$$"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$NETWORK_NAMESPACE"
NETWORK_NAMESPACE_UID=$(kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
  get namespace "$NETWORK_NAMESPACE" -o jsonpath='{.metadata.uid}')
: "${NETWORK_NAMESPACE_UID:?}"
jq -n --arg name "$NETWORK_NAMESPACE" --arg uid "$NETWORK_NAMESPACE_UID" \
  '{namespace:$name,namespaceUID:$uid}' > "$NETWORK_LAB_DIR/ownership.json"
openssl rand -hex 32 > "$NETWORK_LAB_DIR/db-password"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
  create secret generic database-auth \
  --from-file=password="$NETWORK_LAB_DIR/db-password"
```
**3. 3 つの層をデプロイする。** frontend/backend の代わりに Python HTTP server を使い、診断用 TCP クライアントを両方のコンテナで利用できるようにします。PostgreSQL 17 イメージは `POSTGRES_PASSWORD_FILE` と Namespace 内の Secret を使います。外部データベース操作は行いません。DB の `emptyDir` は Pod が置き換わると**失われます**。ここに価値のあるデータを保存しないでください。DB イメージの初期化動作はそのまま使用しています。これは Restricted profile に対応した本番用データベースマニフェストではありません。メジャーバージョンのイメージタグは変更可能です。再現可能な実行のため、解決された digest を記録してください。

```bash
# The HTTP layers are diagnostic stand-ins, not business applications.
for tier in frontend backend; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $tier
spec:
  replicas: 1
  selector:
    matchLabels: {app: $tier}
  template:
    metadata:
      labels: {app: $tier}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: diagnostic
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: $tier
spec:
  selector: {app: $tier}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
done

kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 1
  selector:
    matchLabels: {app: database}
  template:
    metadata:
      labels: {app: database}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      containers:
      - name: database
        image: postgres:17-alpine
        env:
        - name: POSTGRES_PASSWORD_FILE
          value: /run/secrets/postgres/password
        ports:
        - containerPort: 5432
        readinessProbe:
          exec:
            command: [pg_isready, -U, postgres]
          initialDelaySeconds: 5
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
        volumeMounts:
        - {name: data, mountPath: /var/lib/postgresql/data}
        - {name: auth, mountPath: /run/secrets/postgres, readOnly: true}
      volumes:
      - name: data
        emptyDir: {}
      - name: auth
        secret: {secretName: database-auth}
---
apiVersion: v1
kind: Service
metadata:
  name: database
spec:
  selector: {app: database}
  ports:
  - {port: 5432, targetPort: 5432, protocol: TCP}
EOF

for tier in frontend backend database; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    rollout status "deployment/$tier" --timeout=180s
done
```
**4. 基準となる接続性を確立する。** ポリシーを適用する前に、3 つすべての TCP 経路と DNS が動作している必要があります。ポート 5432 への接続成功が証明するのは TCP 接続だけであり、SQL 認証やアプリケーションの正しさではありません。

```bash
# Distinguish DNS failure from TCP denial. Status 42 means a TCP failure.
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    exec "deployment/$1" -c diagnostic -- python -c '
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
try:
    address = socket.gethostbyname(host)
except OSError as error:
    print("DNS failure:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, port), timeout=3)
    connection.close()
except OSError as error:
    print("TCP connection failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP connection succeeded")
' "$2" "$3"
}

# Baseline: all three must succeed BEFORE the policy is applied.
check_tcp frontend backend 8080
check_tcp backend database 5432
check_tcp frontend database 5432
```
**5. ポリシーを適用してテストする。** 選択された Pod は ingress と egress の両方で分離され、一致しないトラフィックは拒否されます。明示的なルールで、2 つのアプリケーション経路と UDP/TCP の DNS を許可します。ラボの Namespace 外にある CoreDNS に到達するには、Namespace セレクターが必要です。NodeLocal DNSCache または異なるラベルを使用している場合は、テスト前に DNS ルールを調整してください。

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: tier-boundaries
spec:
  selector: all()
  types: [Ingress, Egress]
  ingress:
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
  egress:
  - action: Allow
    protocol: UDP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
EOF

# Allow policy propagation, then verify positive controls and the denied path.
POLICY_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp frontend backend 8080
  check_tcp backend database 5432
  if check_tcp frontend database 5432; then
    sleep 2
  else
    result=$?
    if [ "$result" -ne 42 ]; then
      printf '%s\n' 'DNS/exec failure is not proof of policy denial.' >&2
      exit 1
    fi
    # Database availability must still hold after the negative observation.
    check_tcp backend database 5432
    POLICY_VERIFIED=true
    break
  fi
done
[ "$POLICY_VERIFIED" = true ] || {
  printf '%s\n' 'Expected denial was not observed; inspect policy enforcement.' >&2
  exit 1
}
```
ポリシーの反映は非同期です。タイムアウト、DNS エラー、診断用バイナリの不在、データベースの利用不可だけでは、分離が成功した証拠になりません。この手順では、動作する基準接続と正の対照を使用します。観測結果が異なる場合は、他のポリシーやルートを調査してください。

**6. クリーンアップする。** UID を確認してから、所有する Namespace だけを削除してください。これにより、クラスターワイドの Calico インストールではなく、テスト用ワークロード、ポリシー、Secret、一時データが削除されます。演習の後でローカルのパスワードファイルを削除してください。別途レビュー済みのロールバックで管理されていない限り、共有 CNI/RBAC 設定はそのまま残してください。

```bash
CURRENT_NETWORK_UID=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get namespace "${NETWORK_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_NETWORK_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_NETWORK_UID" = "${NETWORK_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
    delete namespace "$NETWORK_NAMESPACE" --wait=true || exit 1
else
  printf '%s\n' 'Namespace UID changed; no deletion attempted.' >&2
  exit 1
fi
```

</details>

### 演習 2: EKS クラスターでの IRSA と S3 アクセスの設定

**シナリオ:** ノードロールではなく IRSA を使い、既存の S3 バケット内の承認済み `training/` プレフィックスに対する読み取り専用アクセスを、1 つのワークロードに付与します。実際に引き受けたロールの ID を確認し、認証情報を意図的に与えていない Pod と比較します。

**前提条件:** Bash、jq、AWS CLI、eksctl、kubectl、既存の認可済み EKS クラスター、新しい Namespace と IAM ロールへの管理者アクセス、承認済みの機密性のない既存 S3 オブジェクト。本商用パーティションの例では、追加のカスタマー KMS 要件がないオブジェクトを想定します。バケット/KMS ポリシー、SCP、DNS、STS、S3 ネットワーク経路に追加要件がある場合があります。S3 オブジェクトの作成、変更、削除は行いません。


<details>
<summary>解決策を表示</summary>

**1. ラボの対象範囲を決め、OIDC を確認する。** `EXAMPLE_CLUSTER`、`EXAMPLE_REGION`、`S3_BUCKET`、`S3_TEST_KEY`（`training/` 配下）を設定します。OIDC provider はクラスター共有インフラストラクチャです。クリーンアップ時に削除しないでください。Namespace の作成または provider の確認に失敗した場合は中止してください。

```bash
set -euo pipefail
umask 077
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```
**2. 範囲を限定した一意のロールを作成する。** 信頼ポリシーでは `aud=sts.amazonaws.com` と正確な Namespace/ServiceAccount の `sub` の両方を必須とします。ロールの作成に失敗した場合は、ポリシーをアタッチせずに停止してください。クリーンアップ用に不変の RoleId を記録します。

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```
**3. デプロイして検証する。** テストが失敗した場合は、再試行する前に IAM の伝播を待ってください。3 つのコンテナで、ID、プレフィックスの一覧数、オブジェクトの長さを確認します。オブジェクトの内容や認証情報はログに出しません。S3 にアクセスできただけでは、より広い権限を持つノードロールが使われた可能性を排除できないため、ID が新しく作成したロールと一致する必要があります。

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```
**4. 制御された否定比較。** 新しい Namespace のデフォルト ServiceAccount に IRSA アノテーションがなく、EKS Pod Identity の関連付けもなく、他の認証情報も注入されていないことが必要です。このテストクライアントでは IMDS へのフォールバックを無効にし、特定の認証情報不足エラーを必須にします。任意のネットワークエラーや認可エラーでは、適切な否定結果になりません。

```bash
# Controlled comparison: no IRSA, no Pod Identity association, no IMDS fallback.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg region "${EXAMPLE_REGION:?}" '
{
  apiVersion:"v1",kind:"Pod",
  metadata:{name:"no-role-check",namespace:$ns},
  spec:{
    automountServiceAccountToken:false,
    serviceAccountName:"default",
    nodeSelector:{"kubernetes.io/os":"linux"},
    restartPolicy:"Never",
    containers:[{
      name:"identity",image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",
      command:["aws"],args:["--region",$region,"sts","get-caller-identity"],
      env:[{name:"AWS_EC2_METADATA_DISABLED",value:"true"}],
      resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
    }]
  }
}' > "${IRSA_LAB_DIR:?}/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create -f "$IRSA_LAB_DIR/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Failed pod/no-role-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get pod no-role-check -o json > "$IRSA_LAB_DIR/negative-status.json" || exit 1
jq -e '.status.containerStatuses[] | select(.name=="identity") |
  .state.terminated.exitCode == 255' "$IRSA_LAB_DIR/negative-status.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs no-role-check -c identity > "$IRSA_LAB_DIR/negative-log.txt" || exit 1
grep -F 'Unable to locate credentials' "$IRSA_LAB_DIR/negative-log.txt" >/dev/null || {
  printf '%s\n' 'Unexpected failure: inspect the saved log; do not claim isolation.' >&2
  exit 1
}
```
これは認証情報プロバイダーの比較であり、任意の Pod が IMDS にアクセスできないことや、コンテナがセキュリティ境界になることを証明するものではありません。ノードの認証情報は別途制限してください。IRSA は投影された web-identity token と STS の一時認証情報を使用します。互換性のある SDK ではそれらが更新されます。`AWS_*` 環境変数や token ファイルをすべて出力しないでください。

**5. 所有するリソースだけをクリーンアップする。** 記録した Namespace UID と IAM RoleId を保持してください。保護されたクリーンアップ処理では、ラボ Namespace、そのインラインポリシー、一意のロールを削除します。S3 バケット/オブジェクト、共有 OIDC provider、クラスターは保持します。セットアップが部分的にしか成功しなかった場合は `ownership.json` を調べ、そこに実際に記録されているリソースだけをクリーンアップしてください。

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

</details>

## 発展的なトピック

以下の質問は、Amazon EKS クラスター作成に関する発展的なトピックを扱います。このセクションでは、EKS クラスター作成に関する高度な概念とベストプラクティスの理解度を確認します。

1. IPv4 プレフィックス委任で保証されないことはどれですか？
   * A) プレフィックスは ENI のアドレススロットを使用する
   * B) 1 つのノードでより多くの IP 容量を確保できる
   * C) すべてのアプリケーションがより速く Ready になる
   * D) サブネット内に連続したブロックが必要

<details>
<summary>回答を表示</summary>

**回答: C) すべてのアプリケーションがより速く Ready になる**

プレフィックス委任は、アドレス割り当てのレイテンシーを短縮する可能性があります。既存の ENI に別のプレフィックスをアタッチすることで、ENI の作成/アタッチに関する一部の処理を避けられるためです。この利点は AWS が説明しているため、プレフィックス委任では起動時間を短縮できず、必ずルーティングのオーバーヘッドが増えるという当初の説明は誤りでした。

Pod のエンドツーエンドの readiness は、スケジューリング、ノードの起動、イメージ取得、ボリュームのアタッチ、初期化、probe、アプリケーションの起動にも依存します。ここでは導入前後のベンチマークは示されておらず、この監査でも実行していません。固定のレイテンシー改善を推測したり、速度低下の原因を作り上げたりしないでください。

各 IPv4 `/28` は 1 つのセカンダリアドレススロットを消費し、連続したサブネットブロックから 16 個のアドレスを使用します。`maxPods`、コンピューティングリソース、サブネットの空き容量に応じて、ノードあたりの IP 容量を増やします。CIDR を拡張したり、割り当てアドレス数の削減を保証したりするものではありません。Warm-pool の設定は、予備アドレスの消費量と割り当て準備のバランスを取ります。

前提条件と新しいノードグループへの移行方法については、基本概念の質問 5 を参照してください。断片化を調べ、互換性のある CNI を設定し、計算したノード容量を検証したうえで、余裕のある容量と PDB に配慮した drain により移行してください。既存 Pod を一律に再起動しても、完全な移行計画にはなりません。

</details>

2. Cluster Autoscaler を使用する混在インスタンスタイプのマネージドノードグループで、不適切な方法はどれですか？
   * A) CPU/メモリー/GPU の形状が近いものを使う
   * B) イメージと AZ の互換性を確認する
   * C) Spot グループと On-Demand グループを分ける
   * D) オートスケーラーがすべてのタイプをシミュレーションするため、任意の形状を混在させる

<details>
<summary>回答を表示</summary>

**回答: D) オートスケーラーがすべてのタイプをシミュレーションするため、任意の形状を混在させる**

選択肢の多様性は、特に Spot で容量の選択肢を増やせますが、オートスケーラーのスケジューリングモデルに従う必要があります。Cluster Autoscaler は、混在グループの最初のインスタンスタイプを使ってシミュレーションします。候補は CPU、メモリー、GPU の形状が同じである必要があります。より小さな代替タイプでは Pod が Pending のままになることがあり、より大きなタイプでは容量が無駄になる可能性があります。名前が似ていても形状が一致するとは限りません。たとえば、`c5n.large` は `c5.large` とメモリー量が異なります。

マネージドノードグループに設定できるキャパシティタイプは 1 つです。On-Demand のベースラインと Spot の拡張には**別々のグループ**を使用してください。複数の `instanceTypes` を指定しても、1 つのマネージドグループ内で購入オプションが混在するわけではありません。EKS がマネージド Spot の割り当て戦略を選択します。`spotAllocationStrategy` は、eksctl の `managedNodeGroups` でサポートされるフィールドではありません。

この例では、形状の近い `m5` ファミリーを使用しています。これはレビュー済みの既存クラスター向けノードグループ設定です。未使用のグループ名を使用します。価格/性能や容量の保証を示すものではありません。AZ ごとの提供状況、イメージ/ドライバー/ストレージの互換性を確認してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: on-demand-base
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  spot: false
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
- name: spot-scaling
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large, m5n.large]
  privateNetworking: true
  spot: true
  desiredCapacity: 0
  minSize: 0
  maxSize: 20
```
メモリー最適化、コンピューティング最適化、汎用インスタンスを 1 つの自動スケーリンググループに混在させるのではなく、ワークロードの形状ごとにグループを分けてください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: compute-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [c5.2xlarge, c5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: compute}
  taints:
  - {key: workload-type, value: compute, effect: NoSchedule}
- name: memory-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [r5.2xlarge, r5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: memory}
  taints:
  - {key: workload-type, value: memory, effect: NoSchedule}
```
ワークロードを専用プールに配置する必要がある場合は、一致する toleration **と** selector/affinity の両方が必要です。ラベルだけではスケジュールされず、taint もテナントのセキュリティ境界にはなりません。ゼロからのスケールに関する検出、daemon のオーバーヘッド、中断への対処、ストレージの永続性、すべての候補タイプでのテストを考慮してください。選択肢を増やすと監視やトラブルシューティングの作業も増える可能性があります。管理の簡素化も低コストも自動的には実現しません。

</details>

3. 古いノードグループを廃止する前に、置き換え用ノードグループを別に作成する戦略はどれですか？
   * A) 追跡されないホストパッケージの更新
   * B) Blue/green 移行
   * C) すべてのノードを一度に削除する
   * D) クラスターの表示名だけを変更する

<details>
<summary>回答を表示</summary>

**回答: B) Blue/green 移行**

Blue/green では、別の置き換え用ノードグループを作成し、検証後にワークロードを移行します。古いグループと互換性のあるアプリケーション/データ状態を維持している間は、ロールバックの選択肢を残せる可能性があります。同じクラスター内の 2 つのグループは、コントロールプレーンや他の依存関係を共有します。完全な分離でも、ダウンタイムゼロの保証でもありません。

| 戦略 | 利点 | 重要な制限 |
| --- | --- | --- |
| Blue/green | 最終的に旧グループを廃止する前に、置き換え用容量を検証できる | 追加のコスト/容量が必要。ロールバックにはノードと互換性のある状態の維持が必要 |
| マネージドのローリングアップデート | EKS が段階的なノード置き換えを調整する | `DEFAULT` は一時的な追加ノードを使用する。PDB/容量の問題で進行がブロックされる場合がある |
| Canary | 別の小規模なワークロード/グループで先に試せる | ワークロード/トラフィックの範囲を実際に限定する必要がある。検証とルーティングの作業も増える |
| ホスト上での手動パッケージ変更 | 個別のホストを変更できる | AMI とのドリフトが生じる。レビュー済みの置き換えイメージの運用を使い、根拠のない SSH/yum 手順には頼らない |

**置き換え用グループの例:** 既存クラスターで未使用のグループ名を使う場合は、このファイルを確認して `eksctl create nodegroup -f green-nodegroup.yaml` を実行してください。事前に AL2023/アーキテクチャとの互換性、アドオン、egress、IP 空間、クォータ、ストレージトポロジーを確認します。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: green-nodegroup
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 3
  maxSize: 5
  labels:
    audit.example.com/pool: green
```
**実際の Canary では別の Deployment を使う:** 次は、専用の `update-lab` Namespace にデプロイする最小構成の HTTP probe ワークロードです。既存の Service に誤って加わらないよう、専用ラベルを使います。アプリケーション互換性を主張する前に、実際のアプリケーションのレビュー済み Canary に置き換えてください。メイン Deployment のノードセレクターを patch すると、レプリカが**すべて**ロールアウトされ、範囲を限定した Canary にはなりません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-canary
  namespace: update-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: my-app-canary}
  template:
    metadata:
      labels: {app: my-app-canary}
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        audit.example.com/pool: green
      containers:
      - name: web
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet: {path: /, port: 80}
        resources:
          requests: {cpu: 100m, memory: 64Mi}
          limits: {cpu: 500m, memory: 128Mi}
```
レビュー済みの観測期間にわたり、readiness、API/CNI/DNS、アプリケーションエラー、リソース圧迫、永続ボリューム、代表的なトラフィックを検証してください。トラフィックのルーティングは明示的に設定してください。ノードラベルだけではトラフィックは切り替わりません。置き換え用容量とワークロード/データの動作を確認したら、旧ノードを 1 台ずつ、対象を確認して drain します。

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
drain がブロックされた場合は、自動的に `--force` を付けたり emptyDir の削除を許可したりせず、原因を調査してください。移行したすべてのワークロードと状態を確認してから、別の最終削除手順に進んでください。

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```
マネージドのローリング更新を使う場合は、basic question 9 の `update-nodegroup-config` 操作を完了してから `update-nodegroup-version` を送信し、返された更新 ID を追跡してください。マネージドグループは、EC2 ノードを置き換えてもリソースとしての ID を維持できます。古い容量を削除したり、互換性のないデータ変更を行ったりすると、「即時ロールバック」はできなくなります。

</details>

4. マネージド ASG の desired capacity に対する Cluster Autoscaler の制御と競合する可能性がある操作はどれですか？
   * A) 検出タグを確認する
   * B) 観測結果に基づいてスキャン頻度を調整する
   * C) 正確な Pod リソース requests を設定する
   * D) 同じ desired capacity を独立して変更する別のポリシーを追加する

<details>
<summary>回答を表示</summary>

**回答: D) 同じ desired capacity を独立して変更する別のポリシーを追加する**

Cluster Autoscaler は、単なる EC2 CPU の平均値ではなく、スケジューリングに関する requests に基づいてノードグループの容量を制御します。同じ desired capacity を変更する target-tracking または predictive ASG ポリシーは、その制御ループと競合し、想定される Kubernetes drain の手順を回避する可能性があります。「最適化」として desired capacity を直接 2 に戻さないでください。

**有用な制御方法:**

* 応答時間と API 負荷のバランスを見てスキャン頻度を調整します。ドキュメントに記載されたデフォルトは 10 秒です。30 秒はテスト用の例であり、実測に基づく最適値ではありません。同様に、プロビジョニングのタイムアウトは実際のノード起動動作に合わせる必要があります。
* レビュー済みの ASG 検出タグと、タグ範囲を限定した IAM を使用してください。タグは対象となるグループを特定しますが、権限を付与したりスケーリングアルゴリズムを定めたりするものではありません。
* requests、ラベル、taint を実際の容量に合わせます。インスタンスタイプを 1 つにするのが適切な場合もあります。可用性/Spot の要件が正当化される場合は、形状が近いタイプを複数使うのが有効です（発展的な質問 2）。
* 優先度を意図的に使用します。Preemption は可用性を保証せず、優先度の低いワークロードに影響を及ぼす可能性があります。Admission とワークロードのポリシーを評価したうえで、`priorityClassName` を使って以下のクラスを割り当ててください。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-high-priority
value: 1000000
globalDefault: false
description: Reviewed priority for critical application Pods
```
**過剰プロビジョニング:** 中断可能な低優先度 Pod で requests を予約します。この例では、Cluster Autoscaler の設定済み expendable-Pod cutoff を `-5` より小さく（たとえば `-10` に）し、アプリケーション Pod の優先度はそれより高くする必要があります。そうしないと、想定どおりの容量補充が行われるきっかけとして予約 Pod が使われない場合があります。専用 Namespace と未使用の PriorityClass 名を使用してください。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-overprovisioning
value: -5
globalDefault: false
description: Temporary spare capacity for an autoscaling lab
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: overprovisioning
  namespace: autoscaling-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: overprovisioning}
  template:
    metadata:
      labels: {app: overprovisioning}
    spec:
      priorityClassName: audit-overprovisioning
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: reserve
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '86400']
        resources:
          requests: {cpu: 1000m, memory: 1000Mi}
          limits: {cpu: 1000m, memory: 1000Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
これは CPU 1 個と 1000Mi の request を持つ容量を確保するものであり、事前起動したアプリケーション状態ではありません。ノードのコストも発生します。イメージ取得、ボリュームのアタッチ、アプリケーション初期化を省略できるものではありません。観測された需要に基づいてサイズを決め、テスト後は所有する予約 Deployment と PriorityClass を削除してください。

古く不完全な v1.23 Deployment ではなく、基本概念の質問 10 にある Cluster Autoscaler の完全なレンダリング設定を使用してください。Karpenter は別途管理する容量の代替案です。有効で認可された EC2NodeClass を NodePool が参照する必要があります。KEDA/HPA はワークロードのレプリカ数を増やし、いずれかのノードオートスケーラーに対する需要を生み出す可能性があります。同じリソースにすべてのスケーリング機構を有効にするのではなく、これらの制御ループが相互作用することを検証してください。

</details>

5. EKS ノードグループの一般的なセキュリティベストプラクティスではないものはどれですか？
   * A) IMDSv2 を必須にし、メタデータアクセスを確認する
   * B) 最小権限の IAM を使う
   * C) すべてのノードにパブリック IP を付与する
   * D) セキュリティグループルールを確認する

<details>
<summary>回答を表示</summary>

**回答: C) すべてのノードにパブリック IP を付与する**

すべてのノードにパブリック IP を付与することは、一般的なセキュリティベストプラクティスではありません。プライベートサブネットはインターネットからの直接的な露出を減らしますが、ルート、セキュリティグループ、IAM、ソフトウェア保守、ワークロード制御も引き続き重要です。

**ノード ID とメタデータ:** eksctl がサポートする `disableIMDSv1` フィールドを使い、IMDSv2 を必須にします。ネストされた `metadataOptions` オブジェクトは、eksctl のマネージドノードグループで使えるフィールドではありません。カスタム EC2 MetadataOptions は、レビュー済みの launch template で設定してください。IMDSv2 は一部の SSRF 経路を軽減しますが、特に host-network Pod では、すべての Pod からノード認証情報に到達できなくなるわけではありません。ワークロード ID とホストの依存関係とは別に、メタデータアクセスを確認してください。

**最小権限と暗号化されたルートボリューム:** 既存クラスター向けの次のノードグループ例は、CNI がすでに独自の IRSA/Pod Identity 権限を持っていることを前提とします。EBS CSI、ログ収集ツール、アプリケーションにも、個別にレビューされたロールが必要です。これらの広範な権限をすべてのノードに付与することは、最小権限の原則に反します。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: secure-nodes
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  disableIMDSv1: true
  volumeEncrypted: true
  iam:
    attachPolicyARNs:
    - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
    - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
```
EBS 暗号化が保護するのは Kubernetes API データとは別の層です。EKS 1.28 以降では、デフォルトのエンベロープ暗号化により、すべての Kubernetes API データが保存時に暗号化されます。カスタマーマネージド KMS キーは任意ですが、追加の grant/権限とキーのライフサイクル管理が必要です。通常のクリーンアップとして、クラスターのキーを無効化したり削除したりしないでください。

**ネットワーク設計:** プライベート API endpoint を使う場合は、ルーティングされた管理者/ノードアクセス経路が必要です。パブリック API の制限には `publicAccessCidrs` を使用し、クラスター SG の inbound ルールを使うものではありません。AWS が示すクラスター/ノードの SG 要件全体を確認してください。TCP 443、TCP 10250、TCP/UDP 53、ワークロード固有の経路について、方向と peer group を正しく設定する必要があります。2 つの inbound ポートルールだけでは、ノードネットワーキングの設計として不十分です。

プライベート IPv4 のインターネット egress には NAT を使う場合があります。VPC endpoint とネイティブ IPv6 では経路が異なります。inbound トラフィックはロードバランサーや、認可済みの接続ネットワークから届く場合があります。プライベートサブネットを使っているだけでは、完全な分離も規制準拠も証明できません。

**コンテナの制御:** 非 root と読み取り専用での実行に対応するワークロードを使います。このコントローラー管理の診断用 Pod は、**新しい専用** `security-lab` Namespace で稼働し、ネットワークや書き込み可能な root を必要としません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-pod
  namespace: security-lab
spec:
  replicas: 1
  selector:
    matchLabels: &id001
      app: secure-pod
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: secure-container
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sh
        - -c
        - echo read-only-lab; sleep 3600
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 32Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```
適用される deny ポリシーをこの専用 Namespace で実証できます。実際のワークロードで使用する前に、DNS/アプリケーションの許可ルールを追加してください。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```
**ログ記録と検出:** CloudWatch のコントロールプレーンログには、設定可能な次の 5 種類があります。

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```
返された更新が成功するまで待ち、ログの実際の配信と保持を確認してください。すべてのコンテナのアプリケーションログが収集されるわけではありません。GuardDuty の EKS audit-log 保護と Runtime Monitoring はそれぞれ別の機能であり、設定方法/対象範囲も異なります。コントロールプレーンログを有効にしただけでは、ランタイムの脅威検出にはなりません。

</details>


## 参考資料

* [EKS prefix mode](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
* [EKS maxPods and prefix procedure](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
* [EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
* [Subnet route table association](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-subnetroutetableassociation.html)
* [Security groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
* [CoreDNS managed add-on](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)
* [CoreDNS cache](https://coredns.io/plugins/cache/)
* [CoreDNS reload](https://coredns.io/plugins/reload/)
* [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
* [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
* [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
* [EKS managed node updates](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)
* [Calico on EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
* [Calico NetworkPolicy](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
* [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
