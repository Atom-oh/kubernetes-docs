# EKS ネットワーキングクイズ - パート 3

> **最終更新**: 2026年10月16日

このクイズでは、[パート 3 のトラブルシューティングの概念](../../eks/03-eks-networking-part3.md)、プライベート接続、マルチクラスター設計、メッシュ運用を扱います。現在の例では EKS Kubernetes 1.36 と VPC CNI 1.23.2 を使用しています。歴史的な App Mesh 設定は明示的に識別されています。リソース作成例には、レビュー済みの IAM、ネットワーク、および所有権の前提条件が必要です。この監査ではローカルチェックを実行し、EKS のデプロイは行いません。

### 1. アプリケーションがサイドカー型サービスメッシュに参加すると、何が変わりますか？

- A. すべての Pod トラフィックが VPC を離れる
- B. プロキシが参加済みサービスのトラフィックを処理する
- C. Service ディスカバリが削除される
- D. すべてのトラフィックに Transit Gateway が必要になる

<details>
<summary>回答を表示</summary>

**回答: B. 注入されたプロキシが、参加済みサービスのトラフィックを処理します。**

サイドカーモードでは、アプリケーションとプロキシは 1 つの Pod ネットワーク名前空間および IP を共有します。プロキシはデータプレーンの一部であり、コントロールプレーンはルーティング、セキュリティ、およびアイデンティティ設定を配布します。NetworkPolicy、VPC ルーティング、Service ディスカバリは引き続き重要です。論理パスは次のとおりです。
```text
Application → client proxy → Pod network → destination proxy → application
```
インターセプトは参加状況、除外ポート、プロトコル、およびモードに依存します。すべてのパケットが Service VIP を通過する必要はありません。アンビエントメッシュは異なるノードプロキシ/waypoint 設計を使用するため、この質問は明示的にサイドカーモードについてのものです。メッシュはメインのサービス実装を書き換えることなく、リトライ、ルーティング、mTLS、テレメトリを提供できますが、アプリケーションにはトレースコンテキストの伝播、互換性のあるプロトコル、タイムアウト処理が引き続き必要になる場合があります。

手動で追加した古い Envoy イメージや同時に使用する injector ではなく、選択したメッシュでサポートされる injector/revision を使用してください。AWS App Mesh は歴史的な例です。サポートおよびアクセスは 2026 年 9 月 30 日に終了しました。既存のデプロイは移行する必要があり、新規インストールのデフォルト例ではありません。維持されている実装パスについては、[Istio のインストール](../../service-mesh/istio/01-installation.md)を参照してください。

</details>

### 2. VPC エンドポイントはプライベート EKS ワークロードに何を提供しますか？

- A. 無制限の帯域幅
- B. サポートされるサービスへのプライベート接続
- C. 自動的な 50% 割引
- D. 自動的な AWS 認証

<details>
<summary>回答を表示</summary>

**回答: B. それらのリクエストについて、インターネット/NAT を介さずにサポートされる AWS サービスエンドポイントへのプライベートパスを提供します。**

Interface エンドポイントは選択したサブネット/AZ に ENI を作成し、通常は時間単位およびデータ処理の料金がかかります。S3/DynamoDB 用の Gateway エンドポイントはルートテーブルエントリを追加し、エンドポイント料金はかかりません。ただし、サービス/ストレージ/リクエスト料金は引き続き適用されます。エンドポイントは IAM 権限を付与せず、コスト/レイテンシの低下を保証せず、コンプライアンスを自動的に満たすこともありません。

プライベート ECR イメージプルでは、`ecr.api`、`ecr.dkr`、S3 レイヤーダウンロードパス、エンドポイント SG の HTTPS ルール、DNS サポート/プライベート DNS、ルートテーブル、エンドポイント/IAM ポリシーを計画してください。その他に必要なサービスはワークロードに依存します。IRSA 用のリージョナル STS、Pod Identity 用の `eks-auth`、CNI 用の EC2 API、Logs/モニタリングなど、使用するものが対象です。EKS サービスエンドポイントはプライベート Kubernetes API エンドポイントを置き換えません。ECR Public、最初の pull-through-cache リクエスト、Windows の外部レイヤーには、追加の外部接続または準備済みのイメージミラーが必要になることがあります。

このパラメーター化された CloudFormation の例は、**既存の** VPC に 3 つのエンドポイントのみを追加します。作成前に既存のエンドポイント/プライベート DNS の所有権をレビューしてください。サービス固有のエンドポイントポリシーはセキュリティ所有者が定義するために意図的に残しています。エンドポイントのデフォルトアクセスは IAM をオーバーライドしません。これを完全な分離クラスターのデプロイと想定せず、変更セットを準備してください。
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: ECR API/DKR and S3 endpoints in an existing VPC; not a complete private EKS stack
Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  PrivateSubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Existing subnets in distinct Availability Zones
  PrivateRouteTableIds:
    Type: CommaDelimitedList
    Description: Route tables used by the image-pulling workloads
  EndpointSecurityGroupId:
    Type: AWS::EC2::SecurityGroup::Id
    Description: Existing same-VPC SG permitting HTTPS from the intended nodes/Pods
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VpcId
      RouteTableIds: !Ref PrivateRouteTableIds
      VpcEndpointType: Gateway
  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
  ECRDkrEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.dkr
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```
新しい node group が必要な場合、`eksctl create nodegroup` は **`--subnet-ids`** を使用します。以前の `--vpc-private-subnets` フラグはこのコマンドでは誤りでした。この例はプライベート API/サービスパスの準備後に課金対象の managed node を作成します。eksctl が意図した所有者であり、既存の `private-ng` がない場合にのみ使用してください。インスタンスサイズは説明用であり、サイジングの指針ではありません。
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${PRIVATE_SUBNET_A:?Set an existing private subnet}"
: "${PRIVATE_SUBNET_B:?Set another private subnet}"
eksctl create nodegroup --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name private-ng --managed --version auto --node-type m5.large \
  --nodes 2 --nodes-min 2 --nodes-max 3 --node-private-networking \
  --subnet-ids "$PRIVATE_SUBNET_A,$PRIVATE_SUBNET_B"
```

</details>

### 3. 複数の重複しない VPC 間でハブルーティングを提供する選択肢はどれですか？

- A. パブリックロードバランサーが必須である
- B. 完全なルーティングを備えた Transit Gateway
- C. すべてのクラスターが VPC を共有する必要がある
- D. NAT gateway が Kubernetes ディスカバリを提供する

<details>
<summary>回答を表示</summary>

**回答: B. AWS Transit Gateway**

Transit Gateway は多数の VPC 向けの 1 つの設計であり、常に最も有効なマルチクラスターアーキテクチャとは限りません。信頼境界、スケール、DNS、アドレス重複、コストに照らして、VPC peering、共有 VPC、PrivateLink サービス公開、VPC Lattice、メッシュ gateway を比較してください。NAT にもプライベート接続での用途がありますが、Service ディスカバリは提供しません。

TGW 設計では、重複しないルーティング可能な Pod/VPC CIDR、参加する各 AZ の attachment、TGW ルートテーブルの関連付け/伝播、ワークロードサブネットのルート、戻りルートを計画してください。TGW ルートだけでは不十分です。Kubernetes ClusterIP は仮想サービスアドレスであり、リモートエンドポイントとして自動的にルーティング可能にはなりません。到達可能な Pod エンドポイントまたは gateway/ロードバランサーのサービスアドレスを、明示的なディスカバリ設計を通じて公開してください。変更前に実際のルート状態を読み取ってください。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the transit gateway Region}"
: "${TGW_ROUTE_TABLE_ID:?Set the intended TGW route table}"
: "${VPC_ROUTE_TABLE_ID:?Set a workload-subnet route table}"
aws ec2 search-transit-gateway-routes --region "$AWS_REGION" \
  --transit-gateway-route-table-id "$TGW_ROUTE_TABLE_ID" \
  --filters Name=state,Values=active
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --route-table-ids "$VPC_ROUTE_TABLE_ID"
```
TGW にはアタッチされたファイアウォール SG はありません。必要に応じてエンドポイント/node/Pod SG、NACL、NetworkPolicy、検査済みルーティングを使用してください。VPC 間の SG 参照は、ドキュメント化された attachment/Region の制約下でサポートされる TGW 機能です。これは TGW への SG のアタッチとは異なり、ルーティングを置き換えるものではありません。

Cloud Map には namespace の完了、Service、登録、ヘルス/登録解除の管理が必要です。TGW はプライベート hosted-zone DNS を自動的に共有しません。承認済みのプライベートゾーン関連付け、または Route 53 Resolver のエンドポイント/ルールを使用してください。別の VPC の `base+2` resolver に、それがそのクラスターの CoreDNS であるかのように転送しないでください。この **Corefile フラグメント**は、エクスポートされた `cluster2.example.internal` レコードをすでに解決する、実在し到達可能な 2 つの inbound resolver を前提としています。DNS 設定所有者を通じてマージし、クラスターのローカルゾーンを保持してください。
```text
cluster2.example.internal:53 {
    errors
    cache 30
    forward . 10.1.20.10 10.1.21.10
}
```
次の ingress policy は、NAT/proxy の後に実際に見える送信元アドレスに基づき、リモート送信元 CIDR から 1 つの API ポートを許可します。他に一致する policy が許可範囲を広げることがあります。Egress/DNS 要件は別途設計する必要があります。クラスター間で namespace/Pod ラベルが自動的に共有されることはありません。
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: remote-api-ingress
  namespace: multicluster-demo
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.1.0.0/16
    ports:
    - protocol: TCP
      port: 8080
```
Istio multi-primary と primary-remote は異なるコントロールプレーンレイアウトです。サポートされるモデルを選択し、east-west gateway、アイデンティティ信頼、エンドポイントのヘルスを検証してください。既存の App Mesh マルチクラスター利用では、2026 年 9 月の終了を考慮する必要があります。実際のパスを使用して、時間単位、処理、cross-AZ の料金を比較してください。同一 VPC またはパブリックロードバランサーの設計が本質的に無効なわけではありませんが、それぞれ独自のセキュリティ/コスト分析が必要です。

</details>

### 4. アドレススロット密度を高めるために、/28 ブロックで IPv4 アドレスを割り当てる VPC CNI 機能はどれですか？

- A. すべての Pod に対する hostNetwork
- B. Prefix delegation
- C. すべての Service に対する NodePort
- D. Pod 間トラフィックに対する Global Accelerator

<details>
<summary>回答を表示</summary>

**回答: B. Prefix delegation**

委任された IPv4 /28 は 1 つの ENI アドレススロットを消費しながら、16 個の Pod アドレスを供給します。アロケーション API の処理を削減し、Pod の起動/密度を改善できます。これは汎用的なパケットスループット最適化でも、サブネット全体の枯渇の解決策でもありません。IPv6 は異なる prefix サイズを使用します。サポートされる Nitro ハードウェア、連続した空き prefix、kubelet maxPods、リソース容量は、引き続き密度を制約します。

スキーマ/所有権のレビュー後に、この JSON フラグメントを正確な EKS add-on 設定にマージするか、対応する Helm の `env` 値を使用してください。古い小文字の `amazon-vpc-cni` ConfigMap キーは Linux CNI を設定しません。
```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
`WARM_PREFIX_TARGET=1` は prefix サイズではなく、予備 prefix を 1 つ意味します。正の `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` は warm-prefix target より優先されます。大きな warm pool はより多くのサブネット空間を予約します。node group の移行と maxPods 設定を計画してください。DaemonSet を切り替えるだけでは、既存 node が任意の密度をサポートできるようにはなりません。

| インスタンス | 従来の secondary-IPv4 maxPods の計算式 | これらの小規模インスタンスでの説明用 prefix-mode 上限 |
|---|---:|---:|
| t3.medium | 17 | 110 |
| m5.large | 29 | 110 |
| c5.xlarge | 58 | 110 |
| r5.2xlarge | 58 | 110 |

これらは設定上の制限であり、ベンチマーク結果やすべての Pod が収まる保証ではありません。c5.xlarge/r5.2xlarge の以前の 250 エントリは誤りでした。EKS 推奨上限は、30 vCPU 未満では 110、30 vCPU 以上では 250 です。Pod SG branch interface には別の制限があります。prefix の割り当てには、汎用的な最小 /24 サブネットではなく、連続した /28 ブロックが必要であり、SG policy を自動的に単純化することはありません。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the node Region}"
kubectl get nodes -o 'custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,PODS:.status.allocatable.pods'
kubectl -n kube-system get daemonset aws-node -o yaml
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
aws ec2 describe-instance-types --region "$AWS_REGION" \
  --instance-types t3.medium m5.large c5.xlarge r5.2xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,vCPUs:VCpuInfo.DefaultVCpus,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4Slots:NetworkInfo.Ipv4AddressesPerInterface}'
```

</details>

### 5. Istio サイドカーモードはどのプロキシを使用し、どのように診断しますか？

<details>
<summary>回答を表示</summary>

**回答: Envoy**

Istio サイドカーモードは Envoy を使用し、istiod がディスカバリ、ルーティング、証明書設定を提供します。古い Pilot/Citadel の機能は istiod に統合され、Mixer は現在必要なコンポーネントではありません。他のメッシュでは異なるプロキシを使用することがあり、Envoy は Kubernetes やすべてのメッシュの要件ではありません。

Envoy は、設定された場合にコネクションプール、HTTP/TCP ルーティング、リトライ、outlier detection、TLS、テレメトリをサポートします。単に Envoy コンテナを追加しても、透過的なトラフィックインターセプト、ワークロードアイデンティティ、xDS、mTLS は構成されません。実際のメッシュでは、サポートされる injector とプロキシビルドを使用してください。古いスタンドアロンの Envoy 1.20 イメージと不完全な Deployment は、有効な現在のインストールではありません。

次の **スタンドアロンリバースプロキシ bootstrap** は、元となる listener/route/cluster の概念を示しています。アップストリーム Envoy 1.39.1 でローカル検証されています。別の HTTP アプリケーションが、同じネットワーク名前空間で `127.0.0.1:8080` をリッスンする必要があります。プロキシと admin listener は loopback にのみ bind します。これは本番または Kubernetes メッシュのデプロイではありません。
```yaml
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
static_resources:
  listeners:
  - name: local-proxy
    address:
      socket_address:
        address: 127.0.0.1
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: demo_http
          route_config:
            name: local-route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: /
                route:
                  cluster: local-app
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: local-app
    connect_timeout: 0.25s
    type: STATIC
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: local-app
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8080
```
これを `envoy-config.yaml` として保存し、一致するアップストリームバイナリで検証してください。検証では設定を解析しますが、backend またはワークロードアイデンティティが機能することは証明しません。
```bash
envoy --mode validate --concurrency 1 --config-path envoy-config.yaml
```
既存の Kubernetes メッシュプロキシでは、19000 を仮定するのではなく、設定済みの admin port とコンテナ名を検出してください。App Mesh のデフォルト admin port は 9901 です。Istio では一般に 15000 を使用しますが、デプロイ設定は異なる場合があります。この port-forward を 1 つのターミナルで実行してください。
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the existing mesh workload namespace}"
: "${MESH_POD:?Set the existing proxy Pod}"
: "${ENVOY_ADMIN_PORT:?Use the admin port actually configured by that mesh}"
kubectl -n "$MESH_NAMESPACE" port-forward --address 127.0.0.1 \
  "pod/$MESH_POD" "19000:$ENVOY_ADMIN_PORT"
```
次に、別のターミナルから境界付きの読み取り専用クエリを実行します。設定ダンプには内部トポロジーまたは機密設定が含まれることがあります。公開したり、admin listener を外部に公開したりしないでください。
```bash
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/config_dump
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/stats
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/clusters
```
アップストリームヘルス、コネクションプール制限、リトライ、filter コスト、メモリ、リクエストレイテンシを併せて調査してください。測定したワークロードの挙動に基づいて調整してください。オーバーヘッドを削減するためだけにセキュリティ filter を削除すると、セキュリティモデルが変わります。

</details>

### 6. 従来の EKS node で DNS を提供するものは何で、どのように設定すべきですか？

<details>
<summary>回答を表示</summary>

**回答: CoreDNS（最初に実際の DNS/add-on 所有者を特定します）。**

CoreDNS は従来の EKS compute における通常の DNS add-on です。作成方法/add-on の所有権は異なる場合があります。EKS Auto Mode には管理されたクラスター DNS が含まれ、従来の CoreDNS Deployment が本質的に必要なわけではありません。次の従来型 add-on チェックを適用する前に、compute/DNS 所有者を特定してください。ResourceNotFound の応答では、所有権の調査が必要であり、自動的な再インストールは行いません。
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name coredns
kubectl -n kube-system get deployment coredns -o yaml
kubectl -n kube-system get configmap coredns -o yaml
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
```
Service DNS は通常、`<service>.<namespace>.svc.<cluster-domain>` に従います。`cluster.local` は一般的なドメインであり、不変のものではありません。Headless/ExternalName レコードは通常の ClusterIP レコードとは異なります。任意の Pod IP すべてに有用な逆引き DNS レコードがあると仮定しないでください。

これは説明用の **Corefile** であり、無条件に上書きする ConfigMap ではありません。管理対象の設定、実際のクラスター domain、probe、DNS Service を保持してください。`pods insecure` は Pod 検証なしで構文上の Pod-IP DNS 応答を許可します。意図した Kubernetes plugin モードを選択してください。
```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf
    cache 30
    loop
    reload
    loadbalance
}
```
`errors` は失敗を記録します。`health` と `ready` は異なる probe の役割を果たします。`kubernetes` はクラスター レコードに応答し、`forward` はその他の domain を解決し、`prometheus` はメトリクスを公開します。`cache`、`reload`、`loadbalance` はキャッシュ/設定再読み込み/レコード順序に影響します。`loop` plugin は、起動時に特定の単純な forwarding loop を検出しますが、すべての動的 DNS loop を永続的に検出するわけではありません。`loadbalance` は DNS 応答順序を変更しますが、Service のパケット転送は変更しません。

条件付き転送には、承認済みで到達可能な DNS server を使用し、UDP/TCP53 を許可してください。10.0.0.1 のような VPC サブネットの最初のアドレスは、サンプルの社内 DNS server ではありません。`file` plugin は、有効な SOA/records とともに作成、mount、保守する必要がある権威ゾーンファイルを提供します。これは stub-domain forward の代替ではありません。パブリック resolver には意図的な egress と情報開示ポリシーが必要であり、プライベート hosted zone を魔法のように解決することはできません。

この cache フラグメントは、元の引数順序を修正します: `prefetch AMOUNT DURATION PERCENTAGE`。2 つ目を追加するのではなく、既存の cache directive を置き換えてください。
```text
cache 30 {
    success 10000
    denial 1024
    prefetch 10 2m 10%
}
```
アップストリーム CoreDNS 1.14.7 では、`denial1000` は受け入れられますが 1024 に正規化され、`success10000` は 9984 に正規化されます。明示的な 1024 は元の実効 denial 容量を維持します。これらの容量は実装上の挙動であり、測定された DNS サイジング推奨ではありません。

**単一のスケーリング所有者**を選択してください。正確な add-on バージョン/スキーマでサポートされる場合は EKS 管理の CoreDNS autoscaling を使用するか、別途所有される HPA/cluster-proportional autoscaler を使用します。次の HPA は、metrics-server と CPU request を備えた、意図的に自己管理される Deployment 専用です。別の replica manager と組み合わせないでください。
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns
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
元のリソース例（100m CPU request、70Mi memory request、170Mi memory limit）は説明用であり、ワークロードで検証されたものではありません。クエリレート、エラー、cache hit/miss の挙動、memory/OOM、応答レイテンシを監視してからサイズを決めてください。診断には、DNS ツールを備えた既存の承認済み診断ワークロードを使用してください。dnsPolicy/dnsConfig/resolv.conf、kube-dns EndpointSlice、policy/SG/upstream パスを確認します。クラスター Service と、承認済みの外部/プライベート name を別々にテストしてください。以前の廃止された dnsutils イメージと所有者のない bare Pod は、DNS 診断の前提条件ではありません。

</details>

### 7. 既存の App Mesh デプロイをどのように保護、監視、移行すべきですか？

<details>
<summary>回答を表示</summary>

**回答: 既存の graph、アイデンティティ、テレメトリをレビューし、サポートされる代替を検証します。**

**歴史的な運用および移行演習:** AWS App Mesh のサポートおよびリソースアクセスは、**2026 年 9 月 30 日**に終了しました。新しい mesh、Private CA、パブリック Grafana をプロビジョニングするために元のレシピに従わないでください。以前の App Mesh デプロイでは、その graph をインベントリ化し、サポートされる mesh/gateway に移行してください。ECS Service Connect は EKS のインストール対象ではありません。実際に使用する機能に対応する、サポートされた Kubernetes mesh/gateway アーキテクチャを評価してください。
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the namespace of the existing mesh workloads}"
kubectl get meshes.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get virtualnodes.appmesh.k8s.aws,virtualservices.appmesh.k8s.aws,virtualrouters.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get deployments,services
```
**1. 既存の graph をマッピングする。** Mesh namespace selector は参加する namespace を選択し、VirtualNode Pod selector はワークロード、listener、Service ディスカバリを選択します。VirtualService name は VirtualNode または VirtualRouter にルーティングし、router route は重み付けされた VirtualNode を選択します。backend 参照、endpoint DNS、health check、IAM/IRSA、injector 設定、アプリケーションの listening port をインベントリ化してください。元の `service-a:latest` プレースホルダーと欠落した service-b ワークロードは、機能するアプリケーションではありません。既存の ServiceAccount を上書きしたり、トラブルシューティングの手順としてフルアクセス policy をアタッチしたりしないでください。

**2. TLS と相互認証を区別する。** サーバー証明書のみを持つ STRICT モードの listener は、暗号化された接続を必要としますが、それ自体で client を認証するわけではありません。App Mesh mTLS には client 証明書と server 側の client 信頼に加え、client 側の server 信頼/SAN チェックが必要です。client 証明書および listener validation trust は、ACM client-certificate reference ではなく、file または SDS を使用します。ワークロード内の app-to-Envoy トラフィックは、proxy-to-proxy mTLS によって自動的に暗号化されません。

次は **レガシー設定レビュー例**であり、新規インストールではありません。ファイルはすでに proxy に安全に mount されている必要があり、証明書には必要な identity/usage が必要で、service-b が存在し、一致する namespace が意図した Mesh に属している必要があります。信頼設計で必要に応じて承認済み client SAN 制限を追加してください。CA のみを信頼すると、その適格な client 証明書を受け入れます。
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
  - portMapping:
      port: 8080
      protocol: http
    tls:
      mode: STRICT
      certificate:
        file:
          certificateChain: /certs/server.crt
          privateKey: /certs/server.key
      validation:
        trust:
          file:
            certificateChain: /certs/trusted-client-ca.pem
    outlierDetection:
      baseEjectionDuration:
        unit: s
        value: 30
      interval:
        unit: s
        value: 10
      maxEjectionPercent: 50
      maxServerErrors: 5
  backends:
  - virtualService:
      virtualServiceRef:
        name: service-b
      clientPolicy:
        tls:
          enforce: true
          ports: [8080]
          certificate:
            file:
              certificateChain: /certs/client.crt
              privateKey: /certs/client.key
          validation:
            trust:
              file:
                certificateChain: /certs/trusted-server-ca.pem
            subjectAlternativeNames:
              match:
                exact: [service-b.app-namespace.svc.cluster.local]
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
  logging:
    accessLog:
      file:
        path: /dev/stdout
```
アカウント内のすべての ACTIVE CA を 1 つの変数に選択しないでください。root CA の作成には明示的な設定とアクティベーション/証明書の手順が必要で、料金が発生します。直ちに使用可能な証明書を生成するわけではありません。意図した正確な ARN を保持してください。App Mesh Kubernetes CRD フィールドは大文字小文字を区別します（`certificateARN`、`certificateAuthorityARNs`）。プレーン YAML ファイル内の `${CA_ARN}` は shell interpolation ではありません。表示した file-based の例は、存在しない CA ワークフローが実行済みであるふりを避けます。

既存の plaintext peer では、文書化された PERMISSIVE 移行を段階的に実施し、client/server identity と trust をプロビジョニングし、受け入れられる peer と拒否される peer の両方をテストしてから、STRICT を要求してください。`ssl.handshake`、`ssl.no_certificate`、`ssl.fail_verify_no_cert`、`ssl.fail_verify_san` と実際のリクエスト結果を調査します。server-TLS handshake の成功だけでは、mTLS の十分な証明になりません。

**3. 移行中もオブザーバビリティを保持する。** 元のレシピの `Mesh.spec.tracing`、`Mesh.spec.logging`、`Mesh.spec.serviceDiscovery` は、レビュー対象の controller 1.13.1 CRD のフィールドではありません。access logging は VirtualNode（上記のとおり）に属します。App Mesh Envoy image の tracing 設定は別のもので、たとえばこの **コンテナ環境フラグメント**には、2000 上の動作するローカル X-Ray daemon/collector、権限、エンドポイントアクセス、トレースコンテキストの伝播が必要です。
```yaml
env:
- name: ENABLE_ENVOY_XRAY_TRACING
  value: "1"
- name: XRAY_DAEMON_PORT
  value: "2000"
```
承認済み collector を使用して proxy の実際の `/stats` または Prometheus endpoint を収集してください。CloudWatch には設定済みの scraping/export/EMF が必要です。`AWS/AppMesh` RequestCount/Latency メトリクスが自動的に表示されると仮定しないでください。dashboard を構築する前に、実際の namespace、metric name、dimension、unit をインベントリ化してください。既存の CloudWatch/Prometheus/Grafana の所有者、認証情報、サポートされる StorageClass を保持してください。浮動する manifest、ハードコードされた Grafana admin password、未レビューのパブリック LoadBalancer を避けてください。この任意の Grafana provisioning フラグメントは、既存の Prometheus datasource を識別するだけで、いずれのシステムもインストールまたは保護しません。
```yaml
apiVersion: 1
datasources:
- name: Prometheus
  type: prometheus
  url: http://prometheus-server.prometheus.svc.cluster.local
  access: proxy
  isDefault: true
```
**4. トラフィックの挙動を明示的にマッピングする。** このレガシー router の例では、両方のバージョン付き VirtualNode がすでに存在し、健全な endpoint を持つことを前提としています。weight は正確なリクエスト数を保証しません。outlier detection は endpoint ejection であり、コネクションプールの circuit-breaking 制限とは異なります。元の 4 つの HTTP retry event 文字列は有効です。`client-error` は 409 を意味し、`stream-error` は拒否された stream を意味します。全体の timeout budget 内で、idempotent operation に対する retry を選択してください。retry は障害負荷を増幅する可能性があります。
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
  - portMapping:
      port: 8080
      protocol: http
  routes:
  - name: service-a-route
    httpRoute:
      match:
        prefix: /
      action:
        weightedTargets:
        - virtualNodeRef:
            name: service-a-v1
          weight: 90
        - virtualNodeRef:
            name: service-a-v2
          weight: 10
      retryPolicy:
        maxRetries: 3
        perRetryTimeout:
          unit: ms
          value: 2000
        httpRetryEvents:
        - gateway-error
```
**5. 段階的に検証して切り替える。** トラフィックを移動する前に、ルーティング、許可済み/未許可 peer、DNS、TLS rotation、retry、障害復旧、trace、metric の継続性を比較してください。残りの製品サポート期間内で rollback path を保持してください。元の 100–200m CPU および 128–256Mi proxy memory 値は、**未検証の例の見積もり**であり、測定値や保証されたサイジングではありません。実際の saturation、memory、latency、error rate を測定してください。この監査では、mesh、CA、collector、cloud dashboard はプロビジョニングされていません。

</details>

### 8. VPC CNI 1.23.2 でアタッチ済み ENI MTU を設定する変数はどれですか？

- A. `ENI_MTU`
- B. `AWS_VPC_ENI_MTU`
- C. `VPC_MTU_SIZE`
- D. `MAX_ENI`

<details>
<summary>回答を表示</summary>

**回答: B. `AWS_VPC_ENI_MTU`**

`POD_MTU` は Pod virtual interface を設定し、未設定の場合は ENI MTU から導出されます。`ENI_MTU` は誤った名前でした。実際の path MTU と計画済み node/Pod rollout に合わせてください。数値が受け入れられても、gateway/tunnel/remote endpoint がそのパケットサイズを受け入れる保証はありません。SG は MTU 設定デバイスではありません。

</details>

### 9. strict Pod-SG TCP early-demux の回避策はどこに置くべきですか？

- A. アプリケーション Deployment
- B. CoreDNS ConfigMap
- C. CNI init container
- D. LoadBalancer annotation

<details>
<summary>回答を表示</summary>

**回答: C. `aws-vpc-cni-init`**

ドキュメント化された `DISABLE_TCP_EARLY_DEMUX=true` 設定は、Helm `init.env` で表される init container に属します。メインの `aws-node` container に設定しても、その init-time 変更は適用されません。strict-mode の kubelet-probe 問題を確認してください。標準 Pod-SG モードでは、この回避策は必要ありません。

</details>

### 10. Kubernetes NetworkPolicy が保証するルール順序の最適化はどれですか？

- A. 最も頻繁に使用されるルールを最初に置く
- B. name をアルファベット順に並べる
- C. 制限的な policy を最後に作成する
- D. 順序の保証はない

<details>
<summary>回答を表示</summary>

**回答: D. ありません。一致する許可は加算されます。**

ポータブルな「最初に一致したものが勝つ」または最新 policy の優先順位はありません。selector/direction と許可の和集合が分離を決定します。vendor の tier/order API は別のものです。必要な制限を維持し、ルール数だけを理由に削除するのではなく、policy のプログラミング/ランタイムコストを測定してください。

</details>

### 11. サブネットが枯渇しています。WARM_IP_TARGET を増やすとアドレス容量は追加されますか？

- A. はい、サブネットを拡張します
- B. いいえ、予備アドレスの需要を増やします
- C. はい、ENI 制限を回避します
- D. はい、すべての ContainerCreating Pod を修復します

<details>
<summary>回答を表示</summary>

**回答: B. いいえ。より多くの予備アドレスを要求します。**

より大きな warm target は容量が存在する場合にアロケーションレイテンシを低減できますが、アドレスを予約するため、枯渇を悪化させる可能性もあります。サブネット空間、ENI slot、maxPods、API throttling、prefix fragmentation を独立して特定してください。Prefix delegation は IPv4 アドレスの総数を増やしません。

</details>

### 12. 現在の Service backend アドレスと condition を確認するには、どの API を調べるべきですか？

- A. Node event のみ
- B. Ingress annotation
- C. EndpointSlice
- D. Service ClusterIP のみ

<details>
<summary>回答を表示</summary>

**回答: C. EndpointSlice**

Service namespace で、`kubernetes.io/service-name=<service>` を使用して EndpointSlice をクエリしてください。Service selector と targetPort と合わせて、address、port、ready/serving/terminating condition を確認します。レガシー Endpoints object は大規模な endpoint set を切り詰めることがあります。空の結果は、ロードバランサーの障害ではなく、selector/readiness の問題を示すことがあります。

</details>

### 13. trafficDistribution: PreferSameZone は何を意味しますか？

- A. AZ 境界を決してまたがない
- B. 同じ zone を優先し、フォールバックする
- C. 既存の Pod を 1 つの AZ に移動する
- D. すべての Local traffic policy をオーバーライドする

<details>
<summary>回答を表示</summary>

**回答: B. 利用可能な同じ zone の endpoint を優先し、フォールバックします。**

これは互換性のある Service proxy のルーティング優先設定であり、AZ 分離 policy ではありません。十分なローカル容量を確保してください。既存の topology-mode Auto annotation が優先されます。Local internal/external traffic policy は、それぞれのトラフィックにより厳しい node-local 要件を課し、ローカル endpoint が存在しない場合はトラフィックをドロップする可能性があります。

</details>

### 14. RTT が 20 ms の仮想的な 10 Gbps フローの帯域幅遅延積を計算してください。

<details>
<summary>回答を表示</summary>

**回答: 25,000,000 バイト、約 23.84 MiB。**

```text
10,000,000,000 bits/s × 0.020 s / 8 = 25,000,000 bytes
```
これは算術例であり、EKS ベンチマークや、すべての socket buffer をその値に設定する推奨ではありません。実際の EC2 の単一フロー/burst 制限、TCP auto-tuning、window scaling、同時接続、memory pressure を考慮してください。以前の 16 MiB maxima は、測定なしに最適とは言えません。keepalive は有効な idle socket で動作し、HTTP pooling および buffer sizing とは別のものです。

</details>

### 15. DNS、Service 選択、アプリケーション接続の障害をどのように切り分けますか？

<details>
<summary>回答を表示</summary>

**回答: エビデンスを収集してから、ポジティブコントロールを用いて実際のプロトコルをテストします。**

ContainerCreating をネットワーキングと分類する前に、影響を受けた Pod の event を確認してください。既知のクラスター Service と意図した hostname を解決し、Service/EndpointSlice の selector-port-readiness の一貫性を調査してから、同じ送信元から Pod-IP と Service-URL へのアクセスを比較します。許可されることが既知のパスをテストし、ツールの欠落、DNS の失敗、または停止した backend を policy 拒否と誤認しないようにしてください。前掲のパート 3 の章にある、範囲を限定した診断方法を使用してください。
```bash
set -euo pipefail
: "${APP_NAMESPACE:?Set the affected namespace}"
: "${APP_POD:?Set the affected Pod}"
: "${APP_SERVICE:?Set the affected Service}"
kubectl -n "$APP_NAMESPACE" describe pod "$APP_POD"
kubectl -n "$APP_NAMESPACE" get events --field-selector "involvedObject.name=$APP_POD" --sort-by=.metadata.creationTimestamp
kubectl -n "$APP_NAMESPACE" get service "$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get networkpolicy
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
```
ロードバランサーでは、controller/class、scheme、target type、target-health reason を特定してください。実際の application/health port、SG と route path、TLS/SNI、Host routing を検証します。ICMP の挙動だけでは、TCP/UDP NetworkPolicy の適用を証明できません。確認された原因を 1 つ変更し、所有者の rollback path を保持して、同じチェックを繰り返してください。これらの例では、本番ネットワークテストを実施したとは主張していません。

</details>

公式リファレンス: [Private EKS](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [VPC CNI 1.23.2](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.2/README.md), [CoreDNS cache](https://coredns.io/plugins/cache/), [App Mesh mTLS](https://docs.aws.amazon.com/app-mesh/latest/userguide/mutual-tls.html), [App Mesh metrics](https://docs.aws.amazon.com/app-mesh/latest/userguide/metrics.html), [Envoy 1.39.1](https://github.com/envoyproxy/envoy/releases/tag/v1.39.1).
