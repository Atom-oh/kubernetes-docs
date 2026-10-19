# EKS クラスター作成クイズ — Part 3

> **最終更新**: 2026年9月11日

このクイズでは、EKS のネットワーキング、ノード容量、マルチテナンシー、自動スケーリング、ノードセキュリティを扱います。コマンドとマニフェストは学習用の例であり、クラウドへのデプロイは実行しておらず、エンドツーエンドの動作もこのレビューではテストしていません。使用する前に、対象アカウント、リージョン、kubeconfig、互換性のあるアドオンバージョン、リソースの所有者を確認してください。

## 基本概念の問題

1. 従来の IPv4 セカンダリ IP 計算では、ENI と ENI ごとのアドレス上限を何が決めますか？
   * A) Namespace 名
   * B) EC2 インスタンスタイプ
   * C) Service 名
   * D) Deployment 名

<details>
<summary>解答を表示</summary>

**解答: B) EC2 インスタンスタイプ**

Linux の IPv4 **セカンダリ IP モード**で、サブネットに十分なアドレスがあり、カスタムネットワークも Pod 用セキュリティグループも使わない場合、ENI と ENI ごとの IP アドレス上限はインスタンスタイプによって決まります。この値から従来方式でノードあたりの Pod 上限を見積もれます。「Pod ごとの IP アドレス数」を示すものではありません。

従来の計算式では、各 ENI のプライマリアドレスを予約します。

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
```
計算に加える 2 は、歴史的に hostNetwork を使う `aws-node` と `kube-proxy` のための予約分です。次の表はセカンダリ IP 計算を示すもので、すべての AMI、CNI モード、マネージドノードグループにおける実効 `maxPods` を示すものではありません。

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

**実際の容量と EC2 上限を確認します。**

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,CAPACITY:.status.capacity.pods,ALLOCATABLE:.status.allocatable.pods
aws ec2 describe-instance-types --region us-west-2 \
  --instance-types m5.large m5.4xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4PerENI:NetworkInfo.Ipv4AddressesPerInterface}'
```
ノード上限に達していなくても、サブネットのアドレス枯渇で Pod を作成できなくなることがあります。CPU/メモリの requests、他の hostNetwork Pod、カスタムネットワーク、Pod 用セキュリティグループ、kubelet 設定も影響します。マネージドノードグループの `maxPods` は、vCPU が30未満のインスタンスでは110、30以上では250が上限です。これは前述の計算結果がさらに大きくても変わりません。

IPv4 prefix delegation は ENI のセカンダリアドレス **スロット** 1つに `/28` を割り当てます。1つの ENI に複数のプレフィックスを割り当てられますが、サブネットのアドレス空間が増えるわけではありません。前提条件と移行手順は問題5を参照してください。

カスタム AL2023 AMI では、適切な値を計算してテストしたうえで、NodeConfig の `spec.kubelet.config.maxPods` を設定してください。カスタム AMI ID を指定しないマネージドノードグループでは、EKS が推奨値を計算します。kubelet の上限だけを引き上げても、IP アドレスや計算資源は増えません。存在しない eksctl の `--kubelet-extra-args` オプションを指定しないでください。

</details>

2. NetworkPolicy が Pod を選択していない場合、その Pod の NetworkPolicy 分離状態はどうなりますか？
   * A) 分離されず、他のネットワーク制御の対象となる
   * B) 同じ namespace 内の通信のみ許可される
   * C) 明示的な許可ルールが必要となる
   * D) すべての通信が拒否される

<details>
<summary>解答を表示</summary>

**解答: A) 分離されず、他のネットワーク制御の対象となる**

ある通信方向について Pod を選択するポリシーがなければ、Kubernetes NetworkPolicy 上、その方向は分離されません。ただし、これはセキュリティグループ、ルートテーブル、NACL、他のポリシー API、アプリケーションのリスナーを迂回することを意味しません。

Amazon VPC CNI は、対応する Linux EC2 ノードで有効にするとネイティブの NetworkPolicy 適用を行えます。現在の標準/管理ポリシーのガイダンスでは、VPC CNI 1.21 以降とカーネル 5.10 以降が必要です。選択したアドオンとの互換性を確認してください。この適用方式は Windows と Fargate を対象としていません。Deployment などのコントローラー管理 Pod を使い、AWS が定めるインターフェイスと Service ポートの制約も確認してください。

AWS VPC ネットワーク上の Calico ポリシーと、AWS-CNI chaining を使う Cilium は、それぞれ異なるインストール要件を持つ代替手段です。設定していない CNI を追加したり、意図せずポリシーエージェントを重ねたりしないでください。AWS Network Firewall はルーティングされた VPC トラフィックをフィルタリングしますが、Kubernetes NetworkPolicy の selector を実装するものではありません。

以下は**新規の専用** `network-policy-lab` namespace を使う例です。最初のポリシーは ingress のみを分離します。続く2つは特定の通信を許可します。`prod` の peer には、組み込み namespace label とバックエンド Pod label の両方が必要です。

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
egress を分離する場合は、実際の DNS 経路とアプリケーションの依存先を別途許可してください。接続拒否を判断する前に、基準となる接続性、DNS、readiness、および許可される positive control が成功することを確認します。手早いテストとして `kube-system` や共有 `default` namespace に全面拒否ポリシーを適用しないでください。

</details>

3. プライベート IPv4 サブネットからインターネットへ egress する一般的な経路はどれですか？
   * A) IGW をサブネットに関連付ける
   * B) パブリック NAT gateway を経由してから VPC IGW にルーティングする
   * C) 各 Pod に Elastic IP を割り当てる
   * D) プライベート NAT gateway から IGW へ直接接続する

<details>
<summary>解答を表示</summary>

**解答: B) パブリック NAT gateway を経由してから VPC IGW にルーティングする**

パブリック IPv4 インターネットへの egress が必要なプライベート IPv4 ノードおよび Pod では、プライベートサブネットのデフォルトルートを**パブリックサブネット内のパブリック NAT gateway**に向ける構成が一般的です。そのパブリックサブネットは VPC に接続されたインターネット gateway にルーティングし、NAT gateway には Elastic IP を割り当てます。NAT instance も選択肢ですが、追加のルーティング、送信元/送信先チェック、運用要件があります。

既定の IPv4 VPC CNI SNAT 動作では、VPC 外への Pod トラフィックは最初にノードのプライマリ IPv4 アドレスを使います。パブリック IPv4 アドレスを持つパブリックノードは、IGW ルートを通る別の経路を利用できます。ネイティブ IPv6 egress には egress-only internet gateway を使える場合があります。また、VPC endpoint による AWS service access にインターネット NAT が不要な場合もあります。NAT がすべての Pod に普遍的に必要だと考えないでください。

**単一 AZ の CloudFormation ルーティング例:** パブリック/プライベートのルート関連付けを示すもので、完全な EKS VPC ではありません。EKS クラスターのサブネットには少なくとも2つの AZ が必要です。AZ 単位で NAT を設計する場合、AZ 間依存を避けるために各 AZ に NAT gateway とプライベートルートを設けることを検討してください。NAT gateway とパブリック IPv4 アドレスには料金がかかります。クラスターをデプロイする際は、概念ガイドの完全な EKS VPC テンプレートを確認してください。

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
`SubnetRouteTableAssociation` リソースは不可欠です。関連付けられていないルートテーブルにルートを作っても、どちらのサブネットの経路も変わりません。

個別にレビューしたデプロイの後、実際の ID とルートを確認してください。CLI で NAT gateway を作る場合は、返された ID を記録し、ルートを作成する前に `nat-gateway-available` になるまで待ちます。NAT 作成に失敗したら、その後の処理を停止してください。

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
eksctl の `vpc.nat.gateway: Single` は、eksctl が管理する VPC 作成手順では有効ですが、単一 AZ への依存を生みます。`HighlyAvailable` は各 AZ に zonal NAT を作成します。これらの設定で、任意の既存サブネットのルーティングを修復できるわけではありません。ラボ用 stack を削除する場合は、依存する workload/ENI を先に削除し、自分が作成したリソースだけを削除してください。NAT とその EIP が解放されたことも確認します。

</details>

4. Pod の branch ENI を使わず、ノードのネットワークを共有する Pod 設定はどれですか？
   * A) 一致する Pod label
   * B) 一致する ServiceAccount label
   * C) `hostNetwork: true`
   * D) 選択された SecurityGroupPolicy

<details>
<summary>解答を表示</summary>

**解答: C) `hostNetwork: true`**

host-network Pod はノードのネットワーク namespace とセキュリティグループを共有します。Pod 用セキュリティグループは、独自のネットワーク namespace を持つ、選択された Pod に branch ENI を使います。

この Linux EC2 の例の前提条件には、対応する trunking 対応インスタンスタイプ、互換性のある VPC CNI、クラスター role の `AmazonEKSVPCResourceController` 権限、`ENABLE_POD_ENI=true` が含まれます。EC2 `t` ファミリーと EKS Auto Mode はこの機能をサポートしません。DNS、control plane とアプリケーションのルール、branch ENI 容量、`POD_SECURITY_GROUP_ENFORCING_MODE` を確認してください。SNAT とポリシー動作はモードによって異なります。古い CNI マニフェストを直接適用せず、アドオン所有者の設定手順を使ってください。

SecurityGroupPolicy は `podSelector` **または** `serviceAccountSelector` で Pod を選択します。Pod 選択に専用 ServiceAccount を必須とするわけではありません。`ENIConfig` はカスタムネットワーク用のリソースであり、Pod 用セキュリティグループだけを利用するために必要なものではありません。

以下の service-account selector の例では、先に専用の `pod-sg-lab` namespace を作成し、SG placeholder を同じ VPC 内にある既存のレビュー済みグループへ置き換えて、前提条件を満たしてください。この待機クライアントは選択動作を示すだけで、データベースへの接続性を証明しません。一致する ServiceAccount label と Pod の `serviceAccountName` の両方が設定されています。

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
別の方法として、`serviceAccountSelector` を `podSelector: {matchLabels: {app: db-client}}` に置き換えます。ポリシーと選択対象の Pod は同じ namespace に置いてください。新しく作成した Pod の branch ENI と、実際の許可/拒否接続を確認します。ポリシーの作成だけでは実行中 Pod に反映されません。テスト後はこのラボ namespace とポリシーだけを削除し、他のリソースが使っている SG は削除しないでください。

</details>

5. IPv4 prefix delegation の主な容量上の利点は何ですか？
   * A) Pod 間通信が必ず高速になる
   * B) ノードあたりの Pod IP 容量が増える
   * C) すべての Pod にパブリック IPv4 アドレスが付与される
   * D) ネットワーク分離が自動化される

<details>
<summary>解答を表示</summary>

**解答: B) ノードあたりの Pod IP 容量が増える**

Linux の IPv4 prefix mode では、`/28`（16アドレス）が ENI のセカンダリアドレススロット1つを使います。1つの ENI に複数の prefix を割り当てられますが、ENI の最大数は増えません。kubelet とリソース上限、およびサブネット容量の範囲内で、IP に基づく Pod 密度を高め、アドレス割り当て API の処理を減らせます。

`m5.large` の従来のセカンダリ IP 計算では29 Pod です。prefix mode の互換性があるマネージドノードグループでは、推奨 `maxPods` を110にできますが、無制限に「110を超える」わけではありません。理論上のアドレススロット数は、アプリケーション容量の保証ではありません。

**前提条件とトレードオフ:**

* 対応する Nitro インスタンスと互換性のある CNI を使います（Linux IPv4 の歴史的な最低要件は1.9.0です。現在サポートされるビルドを選んでください）。
* サブネットに連続した `/28` ブロックが必要です。個別の空き IP が多くてもサブネットが断片化していると `InsufficientCidrBlocks` が発生する場合があります。Subnet CIDR reservation で prefix 用領域を確保できます。
* prefix は実際にサブネットアドレスをブロック単位で消費します。CIDR を拡張することも、IP 消費量の削減、高い利用率、低コストを保証することもありません。
* `WARM_PREFIX_TARGET` は予備 prefix 数、`WARM_IP_TARGET` は予備 IP 数を指定します。`MINIMUM_IP_TARGET` は最低割り当て総数を定めます。後の2つが設定されると `WARM_PREFIX_TARGET` を上書きします。起動レイテンシと未使用アドレス消費の両方を考慮して調整します。
* 置き換え用ノードグループを計画し、余力を確保したうえで cordon/drain による移行を行います。変数を切り替えて全 Pod を再起動するだけでは不十分です。PDB、volume、余剰容量、rollback を確認し、新ノードを検証してから旧グループを削除してください。

次は**新規クラスター設定の例**であり、既存クラスターを更新するコマンドではありません。private API access を使うため、管理者がルーティングされた管理経路を持つ必要があります。バージョンを指定しない場合、互換性のある EKS 既定 CNI ビルドが選択されます。デプロイ前に解決された実バージョンを記録して確認してください。`withOIDC` は eksctl の CNI IAM 連携に関わるため、作成された role を確認します。サイズの上下限だけでは autoscaler はインストールされません。

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

6. CoreDNS が読み込む Corefile を含む Kubernetes object はどれですか？
   * A) ノードのセキュリティグループ
   * B) `coredns` ConfigMap
   * C) StorageClass
   * D) PodDisruptionBudget

<details>
<summary>解答を表示</summary>

**解答: B) `coredns` ConfigMap**

`coredns` ConfigMap には `data.Corefile` が含まれています。適切な**設定の所有者**は、CoreDNS が EKS マネージドアドオンか、セルフマネージドかによって異なります。

マネージドアドオンでは、AWS コンソールと `aws eks update-addon --configuration-values` のどちらでも、サポートされる項目をカスタマイズできます。ConfigMap を直接編集するとアドオン更新で上書きされる場合があります。完全なカスタム Corefile はアドオンの `corefile` 設定キーに保存してください。既存の設定キーを保持し、対象アドオンバージョンの schema を確認します。

編集前に、別のローカル作業ディレクトリへ現在の設定を保存します。

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
`Corefile.reviewed` を編集し、この環境に必要な Kubernetes zone、forwarding、`ready`、health、monitoring plugin を保持してください。以下は個別のカスタマイズ例であり、Corefile 全体を置き換えるものではありません。

* 既存の server block に静的レコードを追加します。実際の内部アドレスを指定してください。

```text
hosts {
    10.0.0.1 example.com
    10.0.0.2 api.example.com
    fallthrough
}
```
* 条件付き forwarder は別の server block を使います。upstream に到達可能であり、CoreDNS service へ戻るループがないことを確認します。

```text
example.org:53 {
    errors
    forward . 10.0.0.53
    cache 30
}
```
* 既存の cache stanza を置き換え、重複を追加しないでください。`prefetch` の時間には単位が必要です。

```text
cache {
    success 10000
    denial 5000
    prefetch 10 10m 10%
}
```
* 任意のエラー分類クエリログです（ログ量と機密性のある名前を確認してください）。

```text
log {
    class error
}
```
`autopath` はサーバー側の検索パス補完用の別 plugin であり、`kubernetes` の subdirective ではありません。Kubernetes block 内の `autopath off` は無効です。既存の `autopath @kubernetes` を無効にする場合は、そのディレクティブを削除してください。元から有効でない環境に追加してはいけません。

schema と構文を確認した後、**同じ**アドオンバージョンを更新します。

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
応答が `InProgress` のままの場合があります。該当する update ID を状態が `Successful` になるまで再確認し、失敗したらそのエラーを調べるまで次の変更を行わないでください。その後、Deployment の readiness、ログ、内部 Service の名前解決、カスタム DNS ケースを検証します。必要なら同じ設定所有者を通じて保存した設定を復元します。

セルフマネージド CoreDNS では、GitOps/manifest の所有者を通じてレビュー済み ConfigMap を編集します。`reload` が有効なら、ConfigMap の投影と reload 間隔の後に Corefile の変更が検出されるため、常に再起動が必要とは限りません。reload error と DNS 動作を確認してください。Deployment 設定を変更した場合は rollout が必要になることがあります。

**スケーリングとリソース:** EKS マネージド CoreDNS は、AWS の前提条件を満たすバージョンで `autoScaling` 設定 object をサポートします。replica を管理する controller は1つだけにしてください。次の CPU HPA は Metrics Server と CPU requests が必要な**セルフマネージド CoreDNS 用の代替案**です。EKS CoreDNS autoscaling と同時に使わないでください。

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
2～10 replica と60%の目標値は例示であり、計測に基づくサイズ設定ではありません。memory、CPU throttling、cache 増加、topology、DNS latency を確認してください。アドオン schema またはセルフマネージド workload の所有者を通じてリソースを変更し、container 配列 index を使ってリソース object 全体を置き換えないでください。

</details>

7. 信頼関係にあるチームが1つの EKS クラスターを共有する場合、論理的な分離を実現する組み合わせはどれですか？
   * A) Namespace のみ
   * B) Namespace、RBAC、強制されるポリシー、quota
   * C) Node selector のみ
   * D) 共有 cluster-admin role

<details>
<summary>解答を表示</summary>

**解答: B) Namespace、RBAC、強制されるポリシー、quota**

相互に信頼できるチームがクラスターを共有する場合、namespace に RBAC、強制されるネットワークポリシー、quota を組み合わせることで有効な論理分離を構成できます。信頼できない tenant に対する普遍的な分離策ではありません。

プラットフォーム管理者は `tenant-a` と `tenant-b` の新しい namespace を作成し、適切な Pod Security Admission ポリシーを強制します（この Linux EKS 1.36 の例では `v1.36` の Restricted）。以下は `tenant-a` に適用するポリシー一式です。`tenant-b` にも同等のレビュー済みポリシーを適用してください。また、`tenant-a-users` に対応する認証済みグループ mapping が必要です。

アプリケーション権限は明示的に定義します。この Role を使う tenant は、ResourceQuota、LimitRange、NetworkPolicy、Role、RoleBinding を直接変更できません。cluster-scoped resource はプラットフォームの所有者が管理します。

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
**制約と検証:**

* workload の作成者は、namespace 内で利用可能な ServiceAccount を使ったり Secret を mount したりできます。この Role は tenant 内の Secret の機密性を保証する境界ではありません。許可する identity、mount、security 設定は admission policy で強制し、プラットフォーム資格情報を tenant namespace の外に置いてください。
* DNS ルールは `kube-system` に `k8s-app=kube-dns` label を持つ一般的な CoreDNS Pod があることを前提とします。NodeLocal DNSCache など別の DNS 経路では、ルールを調整してテストします。このルールが許可するのは DNS query であり、system Pod へのすべての egress ではありません。また、namespace 間の DNS 名を隠すものでもありません。
* quota は受け入れられる resource request と数を制限しますが、物理 node を予約したり、帯域を保証したり、noisy neighbor を解消したりはしません。LimitRange の値は例示です。
* tenant identity を使い、許可される接続、tenant 間の拒否接続、quota による拒否を確認して、onboarding 前に権限の実効値とポリシー適用を検証してください。
* 専用 node group は共有の一部を減らせますが、node selector/taint だけではセキュリティ境界になりません。より強い分離には、sandboxed runtime、virtual control plane、別クラスター/アカウント/ネットワークを、それらの共有依存関係と運用コストも含めて検討してください。

namespace の共有は control plane の負荷を減らし、集中運用を簡素化できます。普遍的に「最適」と決めつけず、必要な分離レベルに基づいて設計してください。

</details>

8. EC2 インスタンスタイプの技術的な容量自体を変えないものはどれですか？
   * A) vCPU 数とメモリ容量
   * B) ネットワークとストレージの上限
   * C) 表示用の name tag
   * D) ENI とアドレスの上限

<details>
<summary>解答を表示</summary>

**解答: C) 表示用の name tag**

インスタンスを選ぶ際は、CPU、メモリ、accelerator、architecture に適合する image/AMI と driver、Pod 密度、ネットワーク帯域、EBS/instance-store の性能、AZ での可用性、中断許容度、コストを考慮します。Kubernetes バージョンは、対応 AMI、driver、機能を通じて関係する場合があり、無関係ではありません。

以下の従来型ファミリーの例は workload の傾向を示すもので、現在の価格/性能ランキングではありません。`m5` は汎用、`r5` はメモリ最適化、`c5` はコンピューティング最適化です。Graviton へ移行する場合は Arm 対応 image と依存関係が必要です。GPU workload には適切な高速化 AMI と device plugin も必要です。instance-store のデータは一時的なもので、label だけではデータベースの耐久性や配置を保証できません。

以下は、既存のレビュー済みクラスターに対する**代替の node-group 設定ファイル**です（`eksctl create nodegroup -f ...`）。未使用の group 名と、必要な egress/endpoint がある private subnet を使ってください。実際のリージョン/AZ で提供されるかを確認します。設定範囲は Cluster Autoscaler をインストールしません。batch group を0台から開始する場合は、適切に設定された autoscaler または手動スケーリングが必要です。

**Web server**

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

**データベース workload**

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

**Batch 処理**

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

**中断可能な Spot worker**

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
EKS の標準バージョンサポートは14か月で、その後12か月の延長サポートがあります。EKS のサポートカレンダー、アップグレード要件、アドオン互換性は、アップストリーム Kubernetes のリリースとは別に確認してください。これらの例は、コスト削減や容量を計測した結果を示すものではありません。

</details>

9. drain 中の voluntary Pod eviction を制約する Kubernetes object はどれですか？
   * A) StorageClass
   * B) PodDisruptionBudget
   * C) ConfigMap
   * D) IngressClass

<details>
<summary>解答を表示</summary>

**解答: B) PodDisruptionBudget**

PDB は Eviction API を通じて voluntary eviction を制約します。更新戦略の一部ではありますが、可用性を保証するものではありません。node 障害、Pod の直接削除、Deployment 自体の rolling update は PDB によって防止されません。

`app=my-app` label が付く3 replica のレビュー済み `update-lab` Deployment に対して、この例は選択された healthy Pod が少なくとも2つ残る場合のみ eviction を許可します。

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
別の指定方法は `maxUnavailable: "50%"` です。PDB の値はどちらか一方だけ指定してください。割合は**切り上げ**られるため、この例では3 Pod のうち2 Pod、または1 Pod 中1 Pod が停止可能です。「半分以上を必ず残す」という保証ではありません。quorum、readiness、workload の動作、スケジュール可能な余剰容量を基準に値を選んでください。

マネージドノードグループの `DEFAULT` 更新では、選択された古い node を drain する前に置換容量を起動します。`MINIMAL` は古い node を先に終了し、一時的に必要な容量を減らします。`maxUnavailable` は同時に利用できなくなる node 数を制御し、PDB は Pod eviction を別途制約します。drain が止まった際に `--force` を常用しないでください。Pod eviction の保護を迂回する可能性があります。

node update policy を設定し、**version update を始める前に**その update の成功を待ちます。

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
返された ID の `describe-update` を状態が `Successful` になるまで確認し、`Failed`/`Cancelled` を明示的に処理します。元の eksctl `update nodegroup --max-unavailable` コマンドはサポートされている代替手段ではありません。実際の PDB `disruptionsAllowed`、readiness、アプリケーション状態、volume 移動を確認してください。3 replica の構成は一例であり、普遍的な最小数ではありません。

</details>

10. Pod の CPU とメモリ requests を推奨、または変更する controller はどれですか？
    * A) Cluster Autoscaler
    * B) Karpenter
    * C) Horizontal Pod Autoscaler
    * D) Vertical Pod Autoscaler

<details>
<summary>解答を表示</summary>

**解答: D) Vertical Pod Autoscaler**

VPA は Pod の resource request を推奨または更新します。HPA は replica 数を変更します。**どちらも**間接的に node 需要を変える可能性はありますが、managed node group の ASG を直接管理しません。

| コンポーネント | 制御する object |
| --- | --- |
| Cluster Autoscaler | 検出した既存 node group/ASG の desired capacity。スケジュール可能性と安全な削除に基づく |
| Karpenter | NodePool と EC2NodeClass で選択する独自の NodeClaim/EC2 capacity。managed node group ASG は対象外 |
| HPA / KEDA | resource/custom/external metric または event に基づく workload replica 数 |
| VPA | update mode に応じた Pod resource の推奨/request |

**Cluster Autoscaler:** クラスターと同じ Kubernetes minor version を使います。EKS 1.36 の例では、chart 9.59.0 に既定 image 1.35.0 ではなく `v1.36.1` image を明示する必要があります。まず、レビュー済みの tag-scoped IAM 権限と ASG discovery tag を持つ専用 `cluster-autoscaler` ServiceAccount を設定します。インストール前に RBAC、image、引数を render して確認します。

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
local storage の保護設定を安易に無効化したり、同じ desired capacity をめぐって ASG の target-tracking/predictive policy と Cluster Autoscaler を競合させたりしないでください。

**Karpenter の代替案:** 互換性のある controller を別途インストールして認可します。AMI ID、node role、discovery tag をこのクラスターでレビュー済みの値に置き換えてください。AMI は AL2023、Kubernetes バージョン、architecture に適合する必要があります。`al2023@latest` を暗黙に選ぶのではなく、AMI ID またはテスト済みの versioned alias を固定します。以下の limit と consolidation timing は例であり、計測済みの容量設定や provisioning 速度の保証ではありません。

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
**HPA:** この例には、`autoscaling-lab` namespace 内の既存 `my-app` Deployment、Metrics Server、CPU requests が必要です。

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
**VPA:** 先に VPA CRD/controller をインストールしてください。recommendation-only mode から始め、明示的にサポートされる update mode を選ぶ前に推奨値を確認します。

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
`Off` は Pod resource を変更しません。推奨値を適用すると、VPA/Kubernetes のバージョンと設定によって Pod の再作成や、サポートされる in-place resize が必要になる場合があります。どの mode でも再起動が保証されるわけではありません。CPU-utilization HPA が同じ workload を制御する状態で CPU request を変更すると、使用率の分母を通じた feedback が発生します。この recommendation-only の例では、連携した設計をレビューするまでその競合を避けます。

</details>

## ハンズオン演習

### 演習1: EKS クラスターで NetworkPolicy を実装する

**シナリオ:** frontend → backend、backend → database の通信を許可し、frontend → database は拒否します。IP 割り当てには AWS VPC CNI を使い、元の学習目標である Calico を維持します。

**範囲:** 使い捨ての既存 Linux IPv4 EKS クラスターで、競合する global/tier policy がなく、標準 CoreDNS と管理者がレビューした Calico があることを前提とします。これは接続性を学ぶ演習であり、本番向けの microservice/database 手順ではありません。クラウドへのインストールと通信テストはこの監査では実行していません。

<details>
<summary>解答例を表示</summary>

**1. policy engine を準備します。** 公式の Calico EKS **Amazon VPC networking** 手順に従います。AWS VPC CNI のネイティブ NetworkPolicy は設定所有者を通じて無効にしてください。Calico の適用と競合します。`aws-node` のネットワーク設定は保持します。`ANNOTATE_POD_IP=true` を有効にし、ServiceAccount に Pod の patch 権限を与えます。以下の専用 RBAC 例は、アドオンの ClusterRole に不正な YAML を追記せずにその権限を追加します。

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
RBAC を保存してレビューし、対象 `aws-node` ServiceAccount にのみ適用します。環境変数は managed add-on または self-managed manifest の所有者を通じて設定します。rollout と annotation 動作が正常になるまで先へ進まないでください。Calico が既にある場合は新規インストールコマンドを再実行せず、既存構成をレビューして再利用します。

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
operator CRD が利用可能になった後、以下のレビュー済み `Installation` と `APIServer` resource を作成します。operator をインストールしただけでは AWS VPC networking は設定されません。API server は `projectcalico.org/v3` policy の例で必要です。

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
以下の実際の適用を確認する前に、Calico component と aggregated API が利用可能であることを確認します。node が `Ready` であるだけでは不十分です。任意の Goldmane/Whisker UI はこの演習では必要ありません。

**2. 所有する namespace と一時的なデータベース資格情報を作成します。** 続く断片は1つの Bash session で実行してください。namespace 名と UID を記録し、cleanup が別の namespace を誤って対象にしないようにします。

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
**3. 3層の workload をデプロイします。** 診断用 TCP client を両方の container で利用できるよう、frontend/backend の代わりに Python HTTP server を使います。PostgreSQL 17 image は `POSTGRES_PASSWORD_FILE` と namespace 内 Secret を利用し、外部データベース操作は行いません。DB の `emptyDir` は**Pod の置換時に失われます**。重要なデータを保存しないでください。DB image の初期化動作は残してあります。この manifest は Restricted profile の本番データベース向けではありません。major version tag は変更可能です。再現可能な実行にするには解決済み digest を記録してください。

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
**4. 基準となる接続性を確立します。** ポリシーを適用する前に、3つの TCP 経路と DNS がすべて動作する必要があります。port 5432 の成功が示すのは TCP 接続だけであり、SQL 認証やアプリケーションの正常性ではありません。

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
**5. ポリシーを適用してテストします。** 選択された Pod は ingress と egress の両方で分離され、一致しない通信は拒否されます。明示的なルールで2つのアプリケーション経路と UDP/TCP DNS を許可します。ラボ namespace の外にある CoreDNS に到達するには namespace selector が必要です。テスト前に NodeLocal DNSCache や異なる label に合わせて DNS rule を調整します。

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
ポリシーの反映は非同期です。timeout、DNS failure、診断 binary の欠如、データベースの利用不可だけでは分離に成功した証拠になりません。この手順では動作する baseline と positive control を使います。観測結果が異なる場合は、他の policy や route も調べてください。

**6. cleanup します。** UID を確認してから、自分が所有する namespace だけを削除してください。これによりテスト workload、policy、Secret、一時データは消えますが、クラスター全体の Calico installation は削除されません。演習後はローカルの password file を削除します。共有 CNI/RBAC 設定は、別途管理者がレビューした rollback の対象でない限り、そのまま残してください。

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

### 演習2: EKS クラスターで IRSA と S3 access を設定する

**シナリオ:** 既存 S3 bucket の承認済み `training/` prefix を読み取り専用で使う workload に対し、node role の代わりに IRSA を使って権限を付与します。実際に引き受けた role identity を確認し、資格情報を持たない Pod と比較します。

**前提条件:** Bash、jq、AWS CLI、eksctl、kubectl、既存の認可済み EKS クラスター、新しい namespace と IAM role に対する管理権限、機密ではない承認済みの既存 S3 object が必要です。この commercial partition の例は、追加の customer KMS 要件がない object を想定します。bucket/KMS policy、SCP、DNS、STS、S3 ネットワーク経路に別の要件がある場合があります。S3 object の作成、変更、削除は行いません。

<details>
<summary>解答例を表示</summary>

**1. 演習の範囲を定め、OIDC を確認します。** `EXAMPLE_CLUSTER`、`EXAMPLE_REGION`、`S3_BUCKET`、`S3_TEST_KEY`（`training/` 配下）を設定します。OIDC provider はクラスター共有基盤のため、cleanup 時に削除しないでください。namespace 作成または provider の確認に失敗した場合は停止します。

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
**2. 一意で範囲を限定した role を作成します。** 信頼条件には `aud=sts.amazonaws.com` と、正確な namespace/ServiceAccount に対応する `sub` の両方が必要です。role 作成に失敗したら policy の関連付けを停止し、cleanup に備えて不変の RoleId を記録します。

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
**3. デプロイして確認します。** IAM の反映には時間がかかる場合があります。テストが失敗したら、再試行前に伝播を待ちます。3つの container は identity、prefix の list 数、object の長さを確認しますが、object 内容や資格情報はログに出しません。S3 操作の成功だけでは node role など広い権限による可能性があるため、identity が新しく作成した role と一致することを確認します。

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
**4. 制御された negative comparison を行います。** 新しい namespace の default ServiceAccount に IRSA annotation や EKS Pod Identity association がなく、他の資格情報も注入されていないことが必要です。このテスト用 client では IMDS fallback を無効にし、特定の資格情報不足 error を確認します。無関係なネットワーク error や認可 error は、有効な negative result ではありません。

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
これは credential provider の比較であり、任意の Pod が IMDS にアクセスできないことや、container がセキュリティ境界になることを証明するものではありません。node の資格情報は別途制限してください。IRSA は projected web-identity token と STS の一時資格情報を使い、互換性のある SDK がそれらを更新します。すべての `AWS_*` environment variable や token file を出力しないでください。

**5. 自分が所有するリソースだけを cleanup します。** 記録した namespace UID と IAM RoleId を使います。保護された cleanup はラボ namespace、その inline policy、一意の role を削除します。S3 bucket/object、共有 OIDC provider、クラスターは残します。セットアップが途中で失敗した場合は `ownership.json` を確認し、実際に記録されたリソースだけをcleanupしてください。

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

## 応用トピック

次の問題では、Amazon EKS クラスター作成に関する高度なトピックを扱います。概念とベストプラクティスの理解を確認してください。

1. IPv4 prefix delegation が保証しない内容はどれですか？
   * A) prefix は ENI address slot を1つ使う
   * B) 1 node に収容できる IP 容量が増える場合がある
   * C) すべてのアプリケーションの readiness が速くなる
   * D) 連続した subnet block が必要

<details>
<summary>解答を表示</summary>

**解答: C) すべてのアプリケーションの readiness が速くなる**

prefix delegation により、既存 ENI に prefix を追加することで ENI 作成/attachment の一部処理を避け、アドレス割り当て latency を減らせる場合があります。AWS はこの利点を説明しているため、prefix delegation は起動時間を短縮せず routing overhead を増やすだけ、という以前の説明は誤りでした。

Pod 全体の readiness は、scheduling、node 起動、image pull、volume attachment、初期化、probe、アプリケーション起動にも左右されます。前後比較の benchmark は提示されておらず、この監査でも実行していません。固定の latency 改善を推定したり、遅延の原因を作り上げたりしないでください。

IPv4 `/28` はそれぞれ ENI の secondary-address slot 1つと16個の subnet address を消費します。`maxPods`、計算資源、subnet 空き容量に応じて、node あたりの IP 容量が増えます。CIDR を拡張したり、割り当て IP 数の減少を保証したりはしません。warm-pool 設定は予備アドレス消費と割り当て readiness のトレードオフを調整します。

基本問題5の前提条件と新しい node group への移行手順を使います。subnet の断片化を調べ、互換 CNI を設定し、計算した node 容量を確認し、余剰容量と PDB に配慮した drain で移行してください。稼働中 Pod を一律に再起動するだけでは移行計画として不十分です。

</details>

2. Cluster Autoscaler を使う複数インスタンスタイプのマネージドノードグループで、誤った運用はどれですか？
   * A) CPU/memory/GPU 構成が近いタイプを使う
   * B) image と AZ の互換性を確認する
   * C) Spot と On-Demand の group を分ける
   * D) autoscaler は全タイプをシミュレートするため、任意の構成を混在させる

<details>
<summary>解答を表示</summary>

**解答: D) autoscaler は全タイプをシミュレートするため、任意の構成を混在させる**

インスタンスの選択肢を増やすと、特に Spot で容量確保を改善できますが、autoscaler のスケジューリングモデルに従う必要があります。Cluster Autoscaler は混在 group を先頭のインスタンスタイプでシミュレートするため、候補は CPU、memory、GPU の構成をそろえてください。より小さい代替を指定すると Pod が Pending のままになり、大きい代替では容量を無駄にすることがあります。名前が似ていても構成が一致するとは限りません。たとえば `c5n.large` は `c5.large` と memory 容量が異なります。

マネージドノードグループは1つの capacity type を使います。On-Demand の基準容量と Spot の拡張容量には**別々の group**を使ってください。1つの managed group に `instanceTypes` を複数指定しても購入方式は混在しません。EKS が managed Spot allocation strategy を選ぶため、`spotAllocationStrategy` は eksctl の `managedNodeGroups` でサポートされる field ではありません。

以下は、レビュー済み既存クラスターの node-group 設定例です。未使用 group 名を使い、価格/性能や容量の保証を示すものではありません。各 AZ の提供状況と image/driver/storage の互換性を確認してください。

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
異なる workload の形状を、memory/compute/general-purpose の instance を1つの autoscaled group にまとめず、別々に扱います。

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
専用 pool で workload を実行するには、対応する toleration **と** selector/affinity が必要です。label だけでは配置されず、taint も tenant のセキュリティ境界ではありません。scale-from-zero 検出、daemon overhead、中断への対応、storage の永続性、すべての候補タイプでのテストを考慮します。選択肢が多いと監視とトラブルシューティングの負荷が増える場合があります。管理の簡素化やコスト削減が自動的に得られるわけではありません。

</details>

3. 古い node group を退役させる前に、置換用 node group を別に作成する戦略はどれですか？
   * A) 追跡されない host package の更新
   * B) Blue/green 移行
   * C) 全 node を一度に削除
   * D) クラスターの表示名だけを変更

<details>
<summary>解答を表示</summary>

**解答: B) Blue/green 移行**

Blue/green 方式では置換用 node group を別に作成し、検証後に workload を移行します。古い group と互換性のあるアプリケーション/データ状態を保持する間は rollback の選択肢になります。同じクラスター内の2つの group は control plane と他の依存先を共有するため、完全分離でも無停止の保証でもありません。

| 戦略 | 利点 | 主な制約 |
| --- | --- | --- |
| Blue/green | 最終退役前に置換容量を検証できる | 追加コスト/容量が必要。rollback は旧 node と互換性のある状態が残ることが条件 |
| Managed rolling update | EKS が段階的な node 置換を調整する | `DEFAULT` は一時的に追加 node を使う。PDB/容量の問題で停止する場合がある |
| Canary | 小さな workload/group で先行テストできる | workload/traffic の範囲を実際に限定する必要があり、検証と routing 作業が増える |
| 手動 host package 変更 | 個別 host を変更する | AMI との drift が発生する。曖昧な SSH/yum 手順ではなく、レビュー済みの replacement-image lifecycle を使う |

**置換 group の例:** 既存クラスターで未使用の group 名を使い、このファイルをレビューして `eksctl create nodegroup -f green-nodegroup.yaml` を実行します。最初に AL2023/architecture 互換性、アドオン、egress、IP 空間、quota、storage topology を確認してください。

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
**実際の canary では別の Deployment を使います。** 次は専用 `update-lab` namespace に置く最小限の HTTP probe workload で、既存 Service に誤って参加しない一意の label を使います。アプリケーション互換性を主張する前に、実際のアプリケーションをレビュー済み canary に置き換えてください。main Deployment の node selector を patch すると全 replica が rollout され、限定的な canary にはなりません。

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
レビューした観測期間を通じて readiness、API/CNI/DNS、アプリケーション error、resource pressure、persistent volume、代表的な traffic を検証します。traffic routing を明示してください。node label だけでは traffic は切り替わりません。置換容量と workload/data の動作を確認した後、旧 node を1台ずつ確実に選んで drain します。

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
drain が止まったら原因を調査してください。`--force` や emptyDir の自動削除を使わないでください。別途行う最終削除の前に、すべての移行済み workload と状態を確認します。

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```
managed rolling update の代替手順では、基本問題9の `update-nodegroup-config` が完了した後に `update-nodegroup-version` を送信し、返された update ID を追跡します。managed group はリソースとしての identity を保持したまま EC2 node を置き換えられます。古い容量を削除したり互換性のないデータ変更を加えたりした後は、「即時 rollback」はできません。

</details>

4. managed ASG の所有権について Cluster Autoscaler と競合する可能性がある操作はどれですか？
   * A) discovery tag を確認する
   * B) 観測に基づき scan interval を調整する
   * C) Pod の resource request を適切に設定する
   * D) 同じ desired capacity を独立して変更する別の policy を追加する

<details>
<summary>解答を表示</summary>

**解答: D) 同じ desired capacity を独立して変更する別の policy を追加する**

Cluster Autoscaler は、平均 EC2 CPU だけでなく、スケジューリング要求に基づいて node-group 容量を管理します。同じ desired capacity を target-tracking または predictive ASG policy が変更すると、この制御 loop と競合し、想定された Kubernetes drain 手順を迂回する場合があります。「最適化」として desired capacity を直接2に設定しないでください。

**有用な制御:**

* 反応時間と API 負荷を基準に scan interval を調整します。文書化された既定値は10秒です。30秒は試験する値の例であり、計測済みの最適値ではありません。provisioning timeout も実際の node 起動動作に合わせます。
* レビュー済み ASG discovery tag と tag-scoped IAM を使います。tag は対象 group を示しますが、権限を付与したり scaling algorithm を定義したりはしません。
* request、label、taint を実際の容量に合わせます。単一のインスタンスタイプも適切な場合があります。可用性/Spot 要件があれば、同等構成を持つ複数タイプも有用です（応用問題2）。
* priority を意図的に使います。preemption は可用性を保証せず、優先度の低い workload に影響する場合があります。次の class を `priorityClassName` で指定するのは、admission と workload policy を評価した後にしてください。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-high-priority
value: 1000000
globalDefault: false
description: Reviewed priority for critical application Pods
```
**Overprovisioning:** 低優先度で preemptible な Pod を使い、request 分の容量を予約します。この例では、Cluster Autoscaler の expendable-Pod cutoff を `-5` より小さく（例: `-10`）設定し、アプリケーション Pod の priority をそれより高くします。そうしないと予約 Pod が意図どおり補充を起動しない場合があります。専用 namespace と未使用の PriorityClass 名を使ってください。

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
これは request 上の CPU 1個と memory 1000Mi を確保するだけで、起動済みのアプリケーション状態ではなく node cost がかかります。image pull、volume attachment、アプリケーション初期化は省略できません。観測した需要に合わせてサイズを決め、テスト後は自分が所有する予約 Deployment と PriorityClass を削除してください。

古い不完全な v1.23 Deployment ではなく、基本問題10の Cluster Autoscaler 設定全体を使ってください。Karpenter は別管理容量向けの代替手段であり、NodePool は有効で認可された EC2NodeClass を参照する必要があります。KEDA/HPA は workload replica を変更し、どちらの node autoscaler にも需要を作る可能性があります。同じ resource にすべての scaling mechanism を有効にするのではなく、相互作用する各 loop を検証してください。

</details>

5. EKS node group に関する一般的なセキュリティのベストプラクティスではないものはどれですか？
   * A) IMDSv2 を必須にし、metadata access を確認する
   * B) IAM を最小権限にする
   * C) すべての node にパブリック IP を付与する
   * D) security group rule を確認する

<details>
<summary>解答を表示</summary>

**解答: C) すべての node にパブリック IP を付与する**

すべての node にパブリック IP を付与することは、一般的なセキュリティのベストプラクティスではありません。private subnet は直接のインターネット露出を抑えますが、route、security group、IAM、ソフトウェア保守、workload 制御も重要です。

**Node identity と metadata:** eksctl がサポートする `disableIMDSv1` field で IMDSv2 を必須にします。ネストした `metadataOptions` object は eksctl managed node group の field ではありません。独自の EC2 MetadataOptions は、レビュー済み launch template で設定してください。IMDSv2 は一部の SSRF 経路を緩和しますが、特に host-network Pod など、すべての Pod による node 資格情報へのアクセスを防ぐものではありません。workload identity と host 依存関係とは別に metadata access を確認します。

**最小権限と暗号化 root volume:** この既存クラスター用 node-group の例では、CNI が独自の IRSA/Pod Identity 権限を既に持つものとします。EBS CSI、log collector、アプリケーションも個別のレビュー済み role が必要です。それらの広い権限をすべての node に付与するのは最小権限に反します。

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
EBS 暗号化と Kubernetes API data は別の層です。EKS 1.28 以降は default envelope encryption によりすべての Kubernetes API data を保存時に暗号化します。customer-managed KMS key は任意ですが、追加の grant/permission と key lifecycle の管理が必要です。クラスターの key を通常の cleanup として無効化または削除しないでください。

**Network design:** private API endpoint では、管理者/node が到達できる route が必要です。public API の制限には `publicAccessCidrs` を使います。クラスター SG の inbound rule で制限するのではありません。AWS が定める完全な cluster/node SG 要件を確認してください。TCP 443、TCP 10250、TCP/UDP 53、workload 固有の経路を、正しい方向と peer group で設定します。inbound port rule を2つ設定しただけでは、node network design として不十分です。

private IPv4 のインターネット egress には NAT を使う場合があります。VPC endpoint と native IPv6 では別の経路があります。load balancer や認可済み接続ネットワークから inbound traffic が来る場合もあります。private subnet だからといって完全な分離や規制遵守が証明されるわけではありません。

**Container 制御:** non-root と read-only 実行に対応する workload を使います。以下の controller-managed diagnostic Pod は**新しい専用** `security-lab` namespace に置き、ネットワークも writable root も必要としません。

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
専用 namespace で deny policy を強制できます。実際の workload で使う前に、DNS/アプリケーション通信の許可を追加してください。

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
**Logging と detection:** control-plane CloudWatch log には、設定可能な5種類があります。

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
返された update が成功するまで待ち、実際の log delivery と retention を確認します。これはすべての container のアプリケーション log を収集するものではありません。GuardDuty EKS audit-log protection と Runtime Monitoring は別々の機能であり、設定/対象範囲も異なります。control-plane log を有効にしただけでは runtime threat detection になりません。

</details>

## 参考資料

* [EKS prefix mode](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
* [EKS maxPods と prefix 手順](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
* [EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [NAT gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
* [Subnet route table association](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-subnetroutetableassociation.html)
* [Pod 用セキュリティグループ](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
* [CoreDNS managed add-on](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)
* [CoreDNS cache](https://coredns.io/plugins/cache/)
* [CoreDNS reload](https://coredns.io/plugins/reload/)
* [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
* [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
* [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
* [EKS managed node update](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)
* [Calico on EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
* [Calico NetworkPolicy](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
* [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
