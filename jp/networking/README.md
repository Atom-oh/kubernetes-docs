# Kubernetes Networking

> **最終更新**: September 13, 2026. 機能の参照には Cilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9、AWS VPC CNI 1.23.0 を含みます。インストール前に各製品の Kubernetes/プラットフォーム互換マトリクスを確認してください。これらは共同でテストされたクラスター構成ではありません。

## 概要

Kubernetes networking は、コンテナ化されたアプリケーション間の通信を可能にする中核的なインフラストラクチャレイヤーです。このセクションでは、基本的な Kubernetes networking の概念から、高度な CNI (Container Network Interface) ソリューション、AWS EKS 環境の networking パターンまでを扱います。

## Kubernetes Networking Model

現在の Kubernetes モデルは、アドレス変換やプロキシなしで Pod がノード間を直接通信できる Pod network を提供します。ただし、**意図的なネットワーク分離の対象となります**。kubelet などのノードエージェントは、自身のノード上の Pod に到達できなければなりません。特定の接続が成功するかは、依然として NetworkPolicy、ルーティング、アプリケーションリスナーによって決まります。

通常の Pod は独自の network namespace とクラスター全体で有効なアドレスを持ち、1 つの Pod 内のコンテナはその namespace と localhost を共有します。host-network Pod はノードネットワークを共有し、dual-stack または multi-network 構成では、より厳密なアドレス処理が必要です。Pod を再作成すると別の IP が割り当てられる場合がありますが、同じ Pod 内のコンテナを再起動しても必ずしも network sandbox は再作成されません。

| コンポーネント | 役割 |
|---|---|
| Pod network | ワークロードの network namespace 間のアドレス指定と接続性 |
| Service/discovery | 変更される endpoint に対する安定したサービス名または仮想アドレス |
| Ingress/Gateway implementation | 構成された外部エントリーとアプリケーションルーティング |
| Network policy engine | 選択した implementation がサポートするポリシーを適用 |

これらの役割は、必須の直列パケットパスを形成するものではありません。Service 変換、L7 proxy、ワークロードポリシーにより、特定のリクエストがネットワークを通過する方法が変わることがあります。

### Pod Networking

Pod networking は Pod 通信のためのアドレス指定とルートを提供します。以下の図は通常の IPv4 Pod を示しており、接続は適用されるポリシーとネットワーク制御によって許可されていることを前提としています。

![設定されたポリシーとルーティングの対象となる、2 つのノードをまたぐ例示的な直接 IPv4 Pod パス。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

アドレスは例示的な通常の Pod アドレスです。意図的な分離と host-network または multi-network 構成は、それぞれ固有の解釈が必要です。

#### Pod Networking Implementation Methods

| 方法 | 説明 | CNI の例 |
|--------|-------------|-------------|
| **Overlay Network** | 既存のネットワーク上でトラフィックをカプセル化 | Flannel VXLAN, Calico VXLAN/IPIP, Cilium VXLAN/Geneve |
| **Native Routing** | その overlay カプセル化なしで基盤ネットワークのルートを使用 | AWS VPC CNI, Calico routing/BGP, Cilium native routing |
| **Conditional Encapsulation** | 構成されたトポロジーに応じて直接パスまたはカプセル化を使用 | 異なる前提条件を持つ、サポート対象の Calico/Flannel/Cilium モード |

### Service Networking

Service は、通常は Pod である論理的な endpoint セットと、その到達方法を記述します。ClusterIP はデフォルトで安定した仮想 IP を提供します。headless Service はその仮想 IP を省略し、ExternalName は DNS CNAME マッピングを使用します。Service は、Pod selector なしで管理される endpoint を持つこともできます。

![ClusterIP、NodePort、LoadBalancer、ExternalName Service の一般的なエントリー機構。DNS マッピングはパケット転送と区別されています。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

これらは一般的な公開機構であり、セキュリティ保証ではありません。NodePort の範囲と到達可能なノードアドレスは構成可能であり、LoadBalancer は内部向けにできます。ExternalName は DNS エイリアスを返し、転送 proxy を作成しません。

#### Service Type Characteristics

`default` に、表示された target port でリッスンする一致した `app: my-app` Pod を作成します。NodePort のデフォルト割り当て範囲は 30000–32767 であり、構成できます。外部到達性は依然としてアドレス、ルート、アクセス制御に依存します。

LoadBalancer の例は、EC2 instance target と割り当て済み NodePort を使用して **AWS Load Balancer Controller** を明示的に選択します。事前に、その controller と IAM/subnet の前提条件をインストールおよび構成してください。EKS Auto Mode は別の controller/class を使用します。ここで port 443 は TCP port を選択するだけです。TLS は backend が 8443 で提供するか、load balancer で別途構成する必要があります。

これらの port マッピングは、一般的な Kubernetes Service API を例示します。AWS は現在、追加のネイティブ EKS network-policy 要件を文書化しています。Service port は container port と一致する必要があり、`metadata.ownerReferences` を持つ controller 管理 Pod は信頼性の高い適用を実現します。その policy implementation をテストする前に、例をこれらの要件に適合させてください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-nodeport-service
  namespace: default
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
    nodePort: 30080
---
apiVersion: v1
kind: Service
metadata:
  name: my-loadbalancer-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
  namespace: default
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 443
    targetPort: 8443
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: true
```

### Ingress Networking

Ingress resource には controller とその data plane が必要です。この HTTP の例では、`spec.ingressClassName: alb` と IP target を伴う AWS LBC を使用します。参照される `api-v1`、`api-v2`、`web-frontend` Service は `default` に存在し、port 80 を公開して、ready で VPC からルーティング可能な Pod endpoint を持っている必要があります。必要に応じて HTTPS/certificate を別途構成してください。インストールと target の前提条件については、[LBC guide](03-aws-lb-controller.md) を参照してください。

Ingress は、HTTP/HTTPS トラフィックを内部クラスター Service にルーティングするためのルールを定義します。

![Service backend と Pod への論理的な Ingress host/path ルーティング。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

このボックスは Ingress data-plane 機能を表します。AWS LBC は ALB をプログラムします。アプリケーショントラフィックは controller の reconciliation process を通過しません。target mode に応じて、data plane は文字どおり追加の hop として Service 仮想 IP を通過するのではなく、Pod IP または NodePort に到達できます。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
  namespace: default
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: api-v1
            port:
              number: 80
      - path: /v2
        pathType: Prefix
        backend:
          service:
            name: api-v2
            port:
              number: 80
  - host: web.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-frontend
            port:
              number: 80
  ingressClassName: alb
```

## CNI (Container Network Interface)

CNI は、runtime が container network を構成するインターフェイスを標準化します。現在の Kubernetes では、kubelet は CRI を通じて Pod-sandbox 操作を要求し、**container runtime が CNI を管理します**。kubelet の旧来の直接 CNI 管理フラグは Kubernetes 1.24 で削除されました。

### Runtime and Plugin Responsibilities

| アクター | 責任 |
|---|---|
| kubelet | container runtime interface を通じて sandbox の作成/削除を要求 |
| Container runtime | network configuration を選択し、CNI plugin chain を呼び出す |
| CNI plugin | configuration を受け取り、ADD/DEL およびその他のサポート対象操作を実行し、結果を返す |
| IPAM implementation | アドレスを割り当て/解放する。委譲された plugin または provider 固有 agent の一部の場合がある |
| Optional node agent | provider 固有の route、policy、IP pool、data path state を維持 |

runtime は CNI interface を通じて plugin に configuration を渡します。すべての plugin で、別個の長時間稼働 agent または IPAM binary が必須というわけではありません。interface type も異なります。veth pair は一般的ですが、唯一の implementation ではありません。

## CNI Comparison

| プロジェクト / 範囲 | Networking と policy | 区別すべき機能と制限 |
|---|---|---|
| **Cilium 1.20.1** | eBPF networking、関連する L7 機能用の Envoy、Cilium network policy、Hubble | AMD64/Arm64 要件を伴う Linux worker dataplane。Windows CLI の可用性は Windows CNI のサポートを意味しません。WireGuard/IPsec と Beta ztunnel mTLS は対象範囲が異なります。 |
| **Calico Open Source 3.32** | routing/encapsulation の選択肢、iptables・nftables・eBPF のオプション、順序付き policy tier、host/workload policy | Windows には Linux eBPF や WireGuard dataplane がないことを含む別の制限があります。Whisker/Goldmane の flow observability は Tech Preview として利用可能です。有償機能については edition matrix を確認してください。 |
| **Flannel 0.28.9** | host subnet 割り当てとノード間 transport、VXLAN、host-gw、その他の backend | `flanneld` 自体は NetworkPolicy を適用しません。chart のオプション `netpol.enabled` は SIGs policy controller をデプロイします。WireGuard は文書化された backend で、IPsec は experimental です。Windows VXLAN には固有の設定/制限があります。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPC address の割り当てと EC2 ENI/prefix、サポート対象 Linux EC2 node での EKS standard および Admin network policy 機能 | EKS Auto Mode は、追加の DNS policy 機能を備えた managed networking implementation です。Windows、Fargate、custom networking、prefix delegation、multi-NIC のサポートにはそれぞれ条件があります。 |
| **Original Weave Net project** | 歴史的な overlay networking implementation | 元の `weaveworks/weave` repository は archive 済みです。新規クラスター向けのアクティブでサポートされたデフォルトとして説明しないでください。 |

### Policy, Encryption and Observability

- Cilium は、適用される L7 component を通じて HTTP/DNS を認識する policy と、cluster-wide/host policy を提供します。その deny/allow semantics は Calico の順序付き Tier API とは異なります。
- Calico Open Source には階層型 policy tier と host policy が含まれます。現在の製品 matrix は application-layer policy、DNS/FQDN policy、Cluster Mesh を Cloud/Enterprise に割り当てており、これらを open-source edition に暗黙的に帰属させてはなりません。Calico で文書化されている転送中の encryption は WireGuard を使用します。
- Amazon EKS は、Auto Mode およびサポート対象の EC2/VPC-CNI installation に `ClusterNetworkPolicy` Admin/Baseline control を提供します。AWS が説明する DNS/FQDN `ApplicationNetworkPolicy` 機能は **Auto Mode** 向けです。その名称は、現在の HTTP method/body inspection を意味するものではありません。
- Flannel のオプション policy controller には独自の要件があります。networking backend を選択するだけでは enforcement は有効になりません。
- node-to-node encryption、authenticated workload identity、application mTLS は異なる control です。network flow visibility も application tracing や process/file enforcement とは異なります。

### Routing and Performance

Calico と Cilium は BGP を使用して route を広告できますが、それだけで multi-cluster Service discovery、policy synchronization、encryption を提供するものではありません。Flannel host-gw は直接 route を使用し、適切な layer-2 接続性が必要です。overlay はカプセル化と MTU の考慮事項を追加しますが、CNI 名から普遍的な performance ranking を推測することはできません。

以前の 100/98/95/85/80/75 percent throughput 値には、再現可能な workload、version、測定 source がありませんでした。比較可能な hardware、kernel、packet/request size、concurrency、encryption/policy setting、throughput、loss、tail latency を使用してください。別の [Pod benchmark](06-pod-network-benchmark.md) には、独自の過去の環境と測定値が保持されています。

## CNI Selection Guide

必要な routing、policy、operating-system、support model を最初に選択し、その組み合わせをテストしてください。

| ニーズ | 評価パス |
|---|---|
| 標準 EKS VPC addressing とサポート対象 network policy | 2 番目の policy engine を追加する前に、AWS VPC CNI/EKS の機能を評価します。 |
| 順序付き policy tier、host policy、infrastructure BGP | 関連する Calico edition/dataplane と routing の前提条件を評価します。 |
| Cilium policy、Hubble、または選択した mesh 機能 | Linux/kernel/platform の互換性と [Cilium mesh guide](../service-mesh/cilium-service-mesh/README.md) を確認します。Envoy は適用される L7 path の一部であり続けます。 |
| 機能セットが限定された小規模ネットワーク | 実際の要件に対して Flannel の backend とオプション policy controller を評価します。 |
| process、syscall、file enforcement | network policy とは別に、Tetragon などの runtime-security component を評価します。 |

### EKS Managed Add-on Configuration

以下は **configuration payload** の例であり、Calico と VPC CNI policy engine の両方を同じ workload にインストールする指示ではありません。

```json
{
  "enableNetworkPolicy": "true"
}
```

文字列の `"true"` はこの設定で文書化されている型です。既存の Kubernetes version と互換性のある EKS add-on build を選択し、その build の configuration schema を確認してください。

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

upstream の 1.23.0 release number と EKS の `eksbuild` version は異なる識別子です。意図した managed add-on configuration と変更をマージしてください。`latest` を盲目的に選択したり、無関係な値を置き換えたりしないでください。third-party policy implementation からの migration には、既存 enforcement state の削除と、テスト済みの node/workload transition plan も必要です。

## EKS Networking Fundamentals

### EKS Default Networking Architecture

| 場所 / コンポーネント | 責任 |
|---|---|
| EKS-managed VPC | AWS は Availability Zone 全体にわたって managed Kubernetes control plane を実行します。 |
| Customer cluster VPC | worker networking、選択した subnet、EKS 管理の cross-account ENI が、control plane への構成済み path を提供します。 |
| ALB/NLB in selected customer VPC subnets | 選択されたパブリックまたは内部アプリケーション entry point を提供します。internet gateway/NAT gateway はその routing configuration の代替ではありません。 |
| NAT gateway or private service endpoints | workload design で必要となる特定の outbound path を提供します。 |

以前の図は control plane を customer VPC 内に、load balancer をその外部に配置していましたが、これらの所有権境界に置き換えられました。

### DNS and Networking by Compute Mode

| Compute mode | DNS / component placement |
|---|---|
| Standard EC2 nodes | 通常は構成された CoreDNS Deployment とインストール済み networking component を使用します。置き換える場合は、独自のサポート対象 configuration が必要です。 |
| Pure EKS Auto Mode | CoreDNS、VPC CNI、kube-proxy 機能は managed node の systemd service として実行されます。これらの node には CoreDNS Deployment/add-on は不要です。 |
| Auto Mode mixed with non-Auto nodes | non-Auto node のために CoreDNS Deployment を維持します。これらは別の node の Auto Mode DNS service を使用できません。 |

Auto Mode の最初の DNS resolver は node-local です。upstream forwarding と control-plane communication には依然として network access が必要な場合があります。これは DNS 関連のすべての packet が node 内に留まる保証ではありません。AWS は Auto Mode 向けに Admin と DNS の両方の policy を文書化していますが、standard EC2 VPC-CNI Admin policy には独自の version/enabling 要件があります。

### How VPC CNI Works

AWS VPC CNI は、選択した IPAM mode を使用して通常の Pod に VPC からルーティング可能なアドレスを付与します。secondary IPv4 address、delegated prefix、branch ENI、multi-NIC 構成は異なり、host-network Pod は node network を共有します。

![EC2 ENI から Pod への secondary-IPv4 割り当て（オプションの warm interface を含む）の例示。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

これは secondary-IP mode のみを示します。warm ENI は構成可能な allocation strategy であり、すべての node が常に正確に 1 つを予約する要件ではありません。prefix delegation、custom networking、branch ENI には異なる allocation rule があります。

#### ENI and IP Limits

| Instance Type | Max ENIs | IPv4 slots per ENI | Legacy secondary-IP bootstrap value |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

これらの値は、VPC CNI 1.23.0 の instance limit と legacy max-Pods table に照らして検証されています。過去の計算式は `ENIs × (IPv4 slots per ENI − 1) + 2` であり、現在の普遍的な推奨ではありません。prefix delegation、custom networking、branch ENI、複数の network card は address capacity を変化させます。Kubernetes scheduling は kubelet の `maxPods` と resource によっても制限されます。EKS managed node group は、30 vCPU 未満の instance では `maxPods` を 110、それ以外では 250 に制限します。利用可能な IP 数だけでこの上限を超えることはできません。

### EKS Networking Considerations

#### IP Address Management

**Linux VPC CNI** では、選択した add-on/Helm/DaemonSet 管理機構を通じて文書化された environment variable を構成します。以下は EKS add-on configuration fragment です。古い `amazon-vpc-cni` ConfigMap の `enable-prefix-delegation` は、この方法で Linux IPAMD を構成しません。変更を適用する際は、意図したその他の add-on 値を保持してください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

代わりに、合計 allocation floor と free-IP target を調整します。`MINIMUM_IP_TARGET` または `WARM_IP_TARGET` のいずれかを構成すると、`WARM_PREFIX_TARGET` より優先されます。これらは独立して加算される 4 つの target ではなく、代替 policy です。allocation は依然として prefix-size 単位で行われます。Nitro support、IPv4 用の連続した `/28` space、適切な kubelet Pod limit は別の前提条件です。

Windows prefix allocation は別の configuration path です。AWS は `amazon-vpc-cni` ConfigMap の `enable-windows-prefix-delegation` とその warm-target key を文書化しています。Linux の environment-variable 手順を変更せずに Windows へコピーしないでください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "MINIMUM_IP_TARGET": "5",
    "WARM_IP_TARGET": "2"
  }
}
```

#### Custom Networking

これらの IPv4 の例には、意図した AZ と VPC の実在する subnet/security-group ID が必要です。custom networking を有効にし、各 node の ENIConfig を zone label で選択します。明示的な ENIConfig node annotation はその label より優先されます。以下の例の名前は両方の言語で同じ region を使用しています。実際の node zone に置き換えてください。ENIConfig object をインストールするだけでは custom networking は有効になりません。

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-fedcba9876543210f
```

## Advanced Networking Concepts

以下の項目は、この概要の他の箇所で簡単に名前が挙げられています。完全なセットアップ手順と測定値はリンク先の詳細ページにあります。このセクションでは、これらが layer ごとにどのように異なるか、またそれぞれがどこに当てはまるかを整理します。

### L2–L7 and the Difference Between Routers and Load Balancers

「router」と「load balancer」は同じ文に現れることが多いですが、異なる問いに答えます。router は（通常）単一の宛先への 1 つの path を選択し、load balancer は distribution algorithm を使用して複数の同等な candidate から 1 つの target を選択します。

| Layer | デバイス/機能 | 判断基準 | Kubernetes/AWS の対応 |
|---|---|---|---|
| L2 (link) | Switch, bridge | 宛先 MAC address | CNI が作成する veth pair と Linux bridge、ENI が公開する virtual NIC |
| L3 (network) | Router または transparent appliance insertion | routing では宛先 IP、appliance 選択では flow identity | VPC の implicit router、TGW、GWLB は appliance 向けに IP packet をカプセル化 |
| L4 (transport) | L4 load balancer | connection/flow identity、一般に 5-tuple | NLB、kube-proxy (iptables、IPVS、nftables)、独立した eBPF Service implementation |
| L7 (application) | L7 load balancer/reverse proxy | request ごとの host、path、header、protocol-aware | ALB、Ingress/Gateway API implementation、service-mesh sidecar (Envoy) |

主な違いは **distribution の単位** です。L4 load balancer は通常、TCP connection または追跡対象 UDP flow に対して target を選択します。L7 proxy は、connection を共有する request を含め、サポート対象の各 application request に対して target を選択できます。GWLB は application request を解析するのではなく、security appliance 間でカプセル化された IP flow を分散します。flow stickiness は構成された timeout、health、failover の動作に依存します。flow が再割り当てまたは中断されない保証ではありません。

> 📎 L2/L3 概念の protocol-level 定義は [Network Fundamentals Part 1](../basics/06-network-fundamentals-part1.md) にあり、ALB/NLB target type と実際の configuration は [AWS Load Balancer Controller](03-aws-lb-controller.md) にあります。

### Cross-Account/VPC Connectivity: TGW, VPC Peering, GWLB, PrivateLink, Lattice

これら 5 つの connectivity option は、layer と traffic model が異なります。TGW RAM sharing、VPC Peering、PrivateLink、TGW Peering、VPC Lattice をまたぐ測定 latency は [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) にあります。このセクションでは、その比較 table にはない GWLB を追加し、5 つすべてを layer 別に捉え直します。

| Connectivity | Layer/model | 特性 |
|---|---|---|
| VPC Peering | L3、双方向 IP routing | transitive ではなく、overlap する CIDR 間では構成できません |
| Transit Gateway (TGW) | L3、hub-and-spoke IP routing | 1 つ以上の TGW route table にまたがる attachment association と propagation を使用し、RAM によって cross-account 共有します |
| Gateway Load Balancer (GWLB) | L3、transparent appliance insertion | 元の packet を GENEVE (UDP 6081) でカプセル化し、VPC endpoint service model が consumer traffic を provider の appliance fleet に接続します |
| PrivateLink | Private endpoint connectivity | NLB-backed endpoint service は 1 つの model で、resource endpoint も存在します。consumer/provider CIDR は overlap できます |
| VPC Lattice | Application and resource networking | HTTP/HTTPS Service は L7 routing と任意の IAM authorization をサポートします。TLS passthrough と resource configuration には異なる機能があります |

GWLB は、Gateway Load Balancer endpoint を通る IP path に firewall や IDS/IPS などの inspection appliance を挿入します。デフォルトの flow stickiness は 5 field を使用しますが、サポート対象の構成では代わりに 2 または 3 field を使用できます。forward/return route、appliance health、encapsulation MTU、NACL、実際の workload/appliance の security group を検証してください。GWLB 自体には ALB 形式の security group はなく、flow stickiness は failure testing の代替ではありません。

> 📎 完全な EKS/VPC Lattice integration (Gateway API Controller、IAM authorization、routing) は [VPC Lattice](02-vpc-lattice.md) にあります。

### How DNS Resolver and Route Tables Actually Behave

**DNS resolver:** AmazonProvidedDNS **は Route 53 Resolver です**。そのアドレスには、primary VPC IPv4 network address に 2 を加えたもの（`10.0.0.0/16` の場合は `10.0.0.2`）と `169.254.169.253` が含まれ、Resolver rule に従って関連付けられた private zone と public name を解決します。CoreDNS は通常、構成された Kubernetes cluster domain（多くは `cluster.local`）を提供します。`kube-dns` は Service 名であり、namespace や DNS zone ではありません。external forwarding は Corefile と DNS Pod から見える resolver file に従います。node の resolver file が変更なしに使用されると想定するのではなく、これらの設定を確認してください。Resolver endpoint design では、inbound endpoint が on-premises query を受け入れ、outbound endpoint と関連付けられた rule が選択した VPC query を on-premises DNS に転送します。Auto Mode の node-local resolver は upstream dependency をなくすものではありません。

**Route tables:** VPC route evaluation は通常、longest-prefix matching を使用します。AWS は appliance routing 向けに `local` route の target を置き換え、サポート対象のより具体的な subnet route を追加することを許可します。`local` が無条件に最も具体的な route というわけではありません。同一の宛先では、static VPC route が virtual private gateway から propagated された route より優先されます。TGW を target とする VPC route は static です。TGW 内の propagation は、その独立した route table に属します。invalid target は traffic を drop する `blackhole` entry を残す可能性があるため、宛先だけでなく route state も確認してください。明示的な route-table association がない subnet は VPC の main route table を使用します。

> 📎 TGW/Peering の route priority と static-route configuration の例は、[Cross-Org VPC Connectivity's operational findings](05-cross-org-vpc-connectivity.md#operational-findings) にあります。

### The Kernel Data Plane: iptables, IPVS, eBPF and Packet Filtering

Linux の Service forwarding と network-policy enforcement は異なる mechanism を使用できます。Netfilter は iptables と nftables が使用する packet-path hook を提供します。eBPF implementation は XDP、tc、socket hook に attach し、そこで Service selection を実行できます。これは、eBPF 有効クラスターのすべての packet が Netfilter または connection tracking を迂回することを意味するものではありません。path は CNI、kernel、routing、feature configuration に依存します。

| Implementation | 配置場所 | 特性 |
|---|---|---|
| iptables | netfilter hook 上の連続した rule chain | evaluation time は rule count (O(n)) に比例。kube-proxy の長年の default mode |
| IPVS | kernel-native L4 load balancer、netfilter extension | hash-based lookup (ほぼ O(1))。Kubernetes 1.35 から kube-proxy mode として deprecated |
| nftables | iptables の後継となる netfilter framework | Kubernetes 1.33 以降の kube-proxy stable mode。最初に kernel/CNI 互換性を確認 |
| eBPF (e.g., Cilium) | 構成された XDP、tc、socket hook | kube-proxy Service handling を置き換え可能。独立した implementation で、path 固有の Netfilter/conntrack 動作を持つ |

implementation を切り替えると、kernel rule と active connection が残る場合があります。distribution/CNI の migration procedure に従い、必要に応じて workload を drain し、cleanup に必要な node restart を計画してください。kube-proxy を eBPF-based CNI に置き換えるには、implementation が同じ Service traffic を競合して処理しないよう、サポート対象の cutover order も必要です。

> 📎 IPVS deprecation timeline と nftables の stable transition は [Introduction to Kubernetes](../basics/04-kubernetes-introduction.md) で扱っています。Cilium の eBPF kube-proxy replacement は [Cilium eBPF](cilium/02-ebpf.md) に、Calico の eBPF data plane と migration procedure は [Calico eBPF](calico/06-ebpf-dataplane.md) にあります。

### Compute-Intensive Networking: ENI, EFA, NVLink and Optical Transceivers

ENI、EFA、NVLink は異なる path を担います。**ENI** は 1 つの Availability Zone 内で EC2 instance にアタッチされる virtual network interface です。その通常の IP traffic は、routing と policy が許可する場合、他の AZ と接続済み VPC に到達できます（[VPC CNI](01-vpc-cni.md) を参照）。**EFA** は、互換性のある MPI/NCCL software が libfabric を通じて使用する OS-bypass device を提供します。**EFA device traffic は routable ではなく、VPC/AZ 境界を越えることはできません**。EFA-with-ENA interface の ENA device を通る通常の IP traffic は routable のままです。EFA-only interface には ENA device も IP addressing もありません。**NVLink** は、サポート対象の rack-scale NVLink domain を含む、サポート対象 system 内の GPU を接続します。EFA に対する固定の speedup を想定するのではなく、選択した hardware、collective operation、placement を測定してください。

**Optical transceiver** は一般的な data-center networking の概念です。銅製 DAC (Direct Attach Copper) cable は短距離に適し、optical module と fiber は他の到達距離と bandwidth 要件に対応します。QSFP と OSFP は module form factor を表すものであり、optical media を保証するものではありません。これは一般的な背景情報として扱ってください。特定の AWS workload の物理 cabling を確立するものではありません。

> 📎 NVLink/IMEX topology-aware scheduling と GPU Pod placement の例は [AI/ML Infrastructure](../ai-ml/06-ai-infrastructure.md) にあります。EFA の VPC/AZ boundary constraint と測定値は [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) にあります。

### What Next-Generation Protocols Mean for Kubernetes: HTTP/3, gRPC, QUIC

HTTP/3 (RFC 9114) とその QUIC transport (RFC 9000) の protocol mechanics は、[Network Fundamentals Part 2](../basics/06-network-fundamentals-part2.md) と [Part 3](../basics/06-network-fundamentals-part3.md) で扱っています。ここでは Kubernetes traffic distribution に実際に影響することのみを扱います。

- **gRPC and L4 load balancers:** gRPC は HTTP/2 connection 上で request を multiplex します。L4 balancer は通常、確立済み TCP connection を選択済み endpoint に維持します。その endpoint が proxy である場合、さらに routing decision を行えます。Pod を追加するだけでは既存 connection は再分散されません。RPC ごとの distribution には、互換性のある L7 proxy または client-side policy が必要です。streaming RPC は 1 つの call のままであり、その個々の message は独立して balance されません。
- **Gateway API's GRPCRoute:** Ingress には gRPC 固有の resource はありませんが、Gateway API は `GRPCRoute` によって service/method-level routing を標準化します。support は implementation ごとに異なります（header match の数、retry policy など）。controller 自身の document を確認してください。
- **How far HTTP/3/QUIC actually reaches into the cluster:** client と edge（CDN、load balancer）間の HTTP/3 support は、cluster 内または Ingress の backend connection における HTTP/3 support とは別の問題です。多くの Ingress/Gateway implementation は依然として backend と HTTP/1.1 または HTTP/2 で通信します。end-to-end HTTP/3 がサポートされるかは implementation と version によって異なります。一般化せず、実際に使用している controller の document を確認してください。

## Networking Sub-pages

このセクションでは、以下の topic を詳しく扱います。

### [VPC CNI](01-vpc-cni.md)
通常の Pod 向け VPC address と、mode 固有の IPAM/policy 前提条件を備えた EKS networking。

### [Cilium Deep Dive](cilium/README.md)
high-performance eBPF-based CNI solution。L7 Network Policy、Service Mesh、observability (Hubble) などの高度な機能を提供します。

### [Calico Deep Dive](calico/README.md)
最も広く使用されている CNI の 1 つです。強力な Network Policy、BGP support、enterprise feature を提供します。introduction、architecture、networking mode、BGP deep dive、Network Policy、eBPF、advanced topic、EKS integration、operations guide を扱います。

### [VPC Lattice](02-vpc-lattice.md)
AWS managed application networking service。cross-VPC、cross-account の service-to-service communication。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Kubernetes Service と Ingress を AWS ELB (ALB/NLB) と統合します。

### [Gateway API](04-gateway-api.md)
next-generation Kubernetes ingress API。標準化された resource model と role-based configuration。

### [Pod Network Benchmark](06-pod-network-benchmark.md)
同一 node、同一 AZ、cross-AZ における EKS 上で測定した Pod-to-pod RTT、HTTP latency、throughput、および DNS `ndots:5` query amplification。

## Network Troubleshooting

### Common Issues and Solutions

#### Pod-to-Pod Communication Failure

```bash
NAMESPACE=default
POD_NAME=iperf-client  # An existing diagnostic Pod with nslookup/curl
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get pods -o wide
kubectl -n "$NAMESPACE" exec "$POD_NAME" -- nslookup "$SERVICE_NAME"
kubectl -n "$NAMESPACE" exec "$POD_NAME" -- \
  curl --connect-timeout 3 --max-time 5 -v "http://$SERVICE_NAME:80/"
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=100
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --tail=100
```

指定した tool を持つ既存の Pod から diagnostics を実行します。cluster にインストールされている CNI のみを query してください。Auto Mode system service はそれらの DaemonSet ではありません。DNS success、TCP reachability、application HTTP response は異なる check です。ICMP は block されているか追加の privilege が必要な場合があるため、ping の失敗だけでは TCP Service に到達できない証明にはなりません。

#### Service Unreachable

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

現在の endpoint diagnosis には EndpointSlice を使用します。Service selector、target port、endpoint readiness、address family、適用される policy を確認してください。kube-proxy log は、その component が実際に Service forwarding を所有している場合のみ調べます。eBPF replacement または Auto Mode には独自の diagnostics が必要です。

#### Network Policy Debugging

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium command は DaemonSet reference によって選択された 1 つの Agent を調べます。incident を追跡する際は、影響を受けた node の Agent を選択してください。Calico native API installation は異なる API group を公開する場合があるため、installation が提供している resource を確認してください。Kubernetes、Calico、AWS extension policy は別々の resource であり、異なる precedence を持つ場合があります。

### Network Performance Testing

この制限された TCP exercise は、Linux AMD64 と Arm64 image を含み、Dockerfile に `iperf3` を含む、publisher が pin した Netshoot v0.16 image index を使用します。TCP 5201 が許可される test environment にこれらの Pod を作成してください。これは例示的な workload であり、測定済み CNI comparison ではありません。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: iperf-server
  namespace: default
  labels:
    app: iperf-server
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  containers:
  - name: netshoot
    image: nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
    command:
    - iperf3
    - -s
    workingDir: /tmp
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
    ports:
    - containerPort: 5201
      protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: iperf-client
  namespace: default
  labels:
    app: iperf-client
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  containers:
  - name: netshoot
    image: nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
    command:
    - sleep
    - '3600'
    workingDir: /tmp
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
```

```bash
kubectl -n default wait --for=condition=Ready pod/iperf-server pod/iperf-client --timeout=120s
IPERF_SERVER_IP="$(kubectl -n default get pod iperf-server -o jsonpath='{.status.podIP}')"
test -n "$IPERF_SERVER_IP"
kubectl -n default exec iperf-client -- iperf3 -c "$IPERF_SERVER_IP" -t 10 -b 10M
```

client は 1 時間 sleep し、この command は提供する traffic を 10 秒間 10 Mbit/s に制限します。これは選択された path をテストするものであり、maximum throughput をテストするものではありません。結果を解釈する前に、実際の Pod/node/AZ placement、resource limit、policy を記録してください。Windows node には Windows 固有の tool を選択してください。完了時には、作成した test resource のみを削除してください。

これらの standalone diagnostic Pod は connectivity test 用です。native EKS network-policy enforcement test には、Deployment/Job 管理 Pod と文書化された Service/container-port 要件を使用してください。

## Best Practices

### 1. IP Address Planning

- 十分に大きな CIDR block を設計する
- Pod network と Service network を分離する
- 将来の拡張を考慮して subnet を設計する

### 2. Apply Network Policies

この例を使用する前に、分離された `networking-demo` namespace を作成します。これはそこにあるすべての Pod を選択し、標準 Kubernetes NetworkPolicy semantics のもとで ingress と egress の両方を分離します。必要な DNS と application flow には明示的な allow rule が必要です。enforcement にはサポートする policy engine が必要です。追加の cluster/admin policy API により precedence が変わる場合があり、この 1 つの manifest は完全な zero-trust architecture ではありません。

- default deny policy (Zero Trust) を適用する
- 必要な traffic のみを明示的に許可する
- namespace を分離する

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: networking-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### 3. Performance Optimization

- 適切な CNI を選択する（workload に適合させる）
- MTU optimization
- kernel parameter tuning

### 4. Security Hardening

- サポート対象の transport encryption を選択し、対象となる traffic を確認する。
- 必要に応じて workload/application identity と mTLS を構成し、これらを DNS/IP-based allowlist と区別する。
- policy、certificate、access-control の変更を定期的にレビューする。

### 5. Ensure Observability

- network metric を収集する
- flow log を有効にする
- distributed tracing を実装する

## Next Steps

1. [VPC CNI](01-vpc-cni.md) - デフォルト EKS CNI
2. [Cilium Deep Dive](cilium/README.md) - eBPF-based networking
3. [Calico Deep Dive](calico/README.md) - routing、policy、dataplane
4. [VPC Lattice](02-vpc-lattice.md) - AWS managed networking
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB integration
6. [Gateway API](04-gateway-api.md) - next-generation ingress
7. [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) - AWS Organizations をまたぐ VPC 接続（field-verified）
8. [Pod Network Benchmark](06-pod-network-benchmark.md) - node/AZ 境界ごとに測定された latency と throughput

---

## References

- [Kubernetes network model](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Container runtime and CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI specification](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico product editions](https://docs.tigera.io/calico/latest/about)
- [Calico policy tiers](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker flow logs](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows limitations](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 networking and policy](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel backends](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Original Weave repository status](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [EKS network policy configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS standard and Admin network policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS prefix delegation and maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin and DNS policy deployment models](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS add-on requirements](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS control plane architecture](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 image metadata](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon runtime security](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB configuration](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress configuration](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer concepts](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE encapsulation (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS resolver](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver endpoints and rules](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC route table evaluation order](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Local routes and more-specific subnet routes](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Static and propagated route priority](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS addresses and behavior](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB flow stickiness and failover](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service virtual IPs and kube-proxy modes](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service names and forwarding configuration](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink resource endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables project documentation](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC transport protocol (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC over HTTP/2 and load balancing](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
