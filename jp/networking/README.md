# Kubernetes Networking

> **最終更新**: October 12, 2026
>
> **固定された例**: Cilium 1.20.1、Calico Open Source 3.32.2、Flannel 0.28.9、およびアップストリーム AWS VPC CNI/Helm chart 1.23.0。
>
> **現在のリリース情報**: AWS は、Kubernetes 1.31–1.37 向けの EKS 管理 VPC CNI add-on `v1.23.1-eksbuild.1` を掲載しています。Calico 3.33.0 は最新の Open Source リリースであり、Kubernetes 1.35–1.37 でテストされています。固定された例を変更する前に、そのリリースノートを確認してください。
>
> これらのバージョンは、共同でテストされたクラスター構成ではありません。インストール前に各製品の Kubernetes/プラットフォームマトリックスを確認してください。

## 概要

Kubernetes networking は、コンテナ化されたアプリケーション間の通信を可能にする中核インフラストラクチャ層です。このセクションでは、基本的な Kubernetes networking の概念から、高度な CNI (Container Network Interface) ソリューション、AWS EKS 環境における networking パターンまでを扱います。

## 学習パス {#learning-path}

初級コースの後は、[エキスパート networking パス](expert/README.md)を使用して、プロトコルプロジェクト、ルーティングポリシー、EVPN、Linux パフォーマンス、クラウド設計、自動化評価を結び付けてください。最初に各ワークブックの環境、エビデンス、復旧基準を確認してください。

Linux または networking を初めて学ぶ場合は、[初級コース](beginner/README.md)から始めてください。8 つのレッスンで、CLI、アドレッシング、DNS、SSH、firewall、監視、capstone を結び付けます。以下のパスは、この基礎をプロトコル、kernel、cluster 実装へと拡張します。

プロトコルの概念から観測へと積み上げ、その後にコンテナ、cluster、cloud の責務に結び付けます。前提条件を使用して開始点を選択し、結果を使用して続行前に理解を確認してください。

| 段階 | 役割 | 前提条件 | 到達点 | 読む / 練習する |
|---|---|---|---|---|
| プロトコル、アドレッシング、HTTP | 用語を確立する | 基本的なコマンドライン操作 | リクエストを追跡し、アドレッシング、transport、application の動作を区別する | Network fundamentals [Part 1](../basics/06-network-fundamentals-part1.md)、[Part 2](../basics/06-network-fundamentals-part2.md)、[Part 3](../basics/06-network-fundamentals-part3.md)、[Part 4](../basics/06-network-fundamentals-part4.md) |
| Linux socket、VFS、packet path | API を kernel に結び付ける | TCP/IP の基礎 | FD、socket buffer、window、queue を区別する | [Kernel Networking Stack](../kernel/02-network-stack.md) |
| Linux network diagnostics | エビデンスで仮説を検証する | Socket と packet-path の概念 | socket、packet、application の観測結果を関連付ける | [Diagnostics practice](07-linux-network-diagnostics.md) · [Quiz](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker と container networking | namespace 境界を特定する | Linux packet path と基本診断 | bridge networking、公開 port、container 名解決を説明する | [Container Technology](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | cluster 抽象化を対応付ける | Container networking | 名前を Service 経由で endpoint まで追跡し、ingress の役割を特定する | [Services and Networking](../core/03-services-networking.md) · [Lab](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、policy | 実装の責務を比較する | Pod と Service の path | packet forwarding、policy enforcement、observability を区別する | [eBPF Fundamentals](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS network 境界と performance | model を cloud path に適用する | CNI の概念と測定スキル | VPC、node、AZ の境界を特定し、文脈の中で測定値を解釈する | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) · [Pod Network Benchmark](06-pod-network-benchmark.md) |

## Kubernetes Networking Model

現在の Kubernetes model は、アドレス変換や proxy を使わずに Pod が node 間で直接通信できる Pod network を提供します。ただし、**意図的な network segmentation の対象となります**。kubelet などの node agent は自身の node 上の Pod に到達できなければなりません。Network policy、routing、application listener は、特定の接続が成功するかどうかを引き続き決定します。

通常の Pod には独自の network namespace と cluster 全体で有効なアドレスがあり、1 つの Pod 内の container はその namespace と localhost を共有します。host-network Pod は node network を共有し、dual-stack または multi-network 構成ではより正確なアドレス処理が必要です。Pod を再作成すると別の IP が割り当てられる可能性があります。同じ Pod 内の container を再起動しても、その network sandbox が必ず再作成されるわけではありません。

| コンポーネント | 役割 |
|---|---|
| Pod network | workload network namespace 間のアドレッシングと接続性 |
| Service/discovery | 変化する endpoint に対する安定した service 名または virtual address |
| Ingress/Gateway implementation | 構成された外部 entry と application routing |
| Network policy engine | 選択した implementation でサポートされる policy を強制する |

これらの役割は、必須の直列 packet path を形成しません。Service translation、L7 proxy、workload policy によって、特定のリクエストが network を通過する方法は変わり得ます。

### Pod Networking

Pod networking は Pod 通信のためのアドレッシングと route を提供します。以下の図は通常の IPv4 Pod を示しており、その接続は適用可能な policy と network control により許可されることを前提としています。

![構成された policy と routing の対象となる、2 つの node 間の例示的な直接 IPv4 Pod path。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

アドレスは例示的な通常の Pod address です。意図的な隔離、host-network、multi-network 構成には、それぞれ固有の解釈が必要です。

#### Pod Networking Implementation Methods

| 手法 | 説明 | 例となる CNI |
|--------|-------------|-------------|
| **Overlay Network** | 既存の network 上で traffic を encapsulate する | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **Native Routing** | その overlay encapsulation なしで基盤 network 内の route を使用する | AWS VPC CNI、Calico routing/BGP、Cilium native routing |
| **Conditional Encapsulation** | 構成された topology に応じて direct path または encapsulation を使用する | サポートされる Calico/Flannel/Cilium mode。前提条件はそれぞれ異なる |

### Service Networking

Service は、通常は Pod である論理的な endpoint の集合と、その到達方法を記述します。ClusterIP はデフォルトで安定した virtual IP を提供します。headless Service はその virtual IP を省略し、ExternalName は DNS CNAME mapping を使用します。Service では、Pod selector なしで管理された endpoint を使用することもできます。

![ClusterIP、NodePort、LoadBalancer、ExternalName Service の典型的な entry mechanism。DNS mapping は packet forwarding と区別される。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

これらは典型的な公開 mechanism であり、security guarantee ではありません。NodePort range とアクセス可能な node address は構成可能で、LoadBalancer は内部向けにできます。ExternalName は DNS alias を返すだけで、forwarding proxy は作成しません。

#### Service Type Characteristics

表示された target port で listen する、対応する `app: my-app` Pod を `default` に作成します。NodePort のデフォルト割り当て range は 30000–32767 で、構成できます。外部からの到達可能性は、依然として address、route、access control に依存します。

LoadBalancer の例では、EC2 instance target と割り当てられた NodePort を備えた **AWS Load Balancer Controller** を明示的に選択しています。最初にその controller と IAM/subnet の前提条件をインストール/構成してください。EKS Auto Mode は別の controller/class を使用します。port 443 はここでは TCP port を選択するだけです。TLS は backend で 8443 に提供するか、load balancer で別途構成する必要があります。

これらの port mapping は、一般的な Kubernetes Service API を例示しています。AWS は現在、追加の native EKS network-policy 要件を文書化しています。Service port は container port と一致し、`metadata.ownerReferences` を持つ controller 管理 Pod は信頼性のある enforcement を提供する必要があります。その policy implementation をテストする前に、例をこれらの要件に適合させてください。

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

Ingress resource には controller とその data plane が必要です。この HTTP の例では、`spec.ingressClassName: alb` と IP target を使用する AWS LBC を利用します。参照される `api-v1`、`api-v2`、`web-frontend` Service は `default` に存在し、port 80 を公開し、ready 状態で VPC-routable な Pod endpoint を持つ必要があります。必要な場合は HTTPS/certificate を別途構成してください。インストールと target の前提条件については、[LBC guide](03-aws-lb-controller.md)を参照してください。

Ingress は HTTP/HTTPS traffic を内部 cluster Service に routing する rule を定義します。

![Service backend と Pod への論理的な Ingress host/path routing。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

box は Ingress data-plane function を表します。AWS LBC は ALB を program します。application traffic は controller の reconciliation process を通過しません。target mode に応じて、data plane は literal な追加 hop として Service virtual IP を通過するのではなく、Pod IP または NodePort に到達できます。

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

CNI は、runtime が container network を構成する interface を標準化します。現在の Kubernetes では、kubelet は CRI を通じて Pod-sandbox operation を要求し、**container runtime が CNI を管理します**。kubelet の旧来の直接 CNI 管理 flag は Kubernetes 1.24 で削除されました。

### Runtime and Plugin Responsibilities

| 担当 | 責務 |
|---|---|
| kubelet | container runtime interface を通じて sandbox の作成/削除を要求する |
| Container runtime | network configuration を選択し、CNI plugin chain を呼び出す |
| CNI plugin | configuration を受け取り、ADD/DEL およびその他のサポートされた operation を実行し、result を返す |
| IPAM implementation | address を割り当て/解放する。delegated plugin または provider 固有 agent の一部の場合がある |
| Optional node agent | provider 固有の route、policy、IP pool、datapath state を維持する |

runtime は CNI interface を通じて plugin に configuration を渡します。個別の長期稼働 agent または IPAM binary は、すべての plugin で必須ではありません。interface type もさまざまです。veth pair は一般的ですが、唯一の実装ではありません。

## CNI 比較

| Project / 範囲 | Networking と policy | 区別すべき feature と制限 |
|---|---|---|
| **Cilium 1.20.1** | eBPF networking、該当する L7 function 向けの Envoy、Cilium network policy と Hubble | AMD64/Arm64 要件を持つ Linux worker dataplane。Windows CLI が利用可能であっても Windows CNI support を意味しません。WireGuard/IPsec と Beta ztunnel mTLS は適用範囲が異なります。 |
| **Calico Open Source 3.32.2 examples; 3.33.0 current** | Routing/encapsulation の選択肢、iptables、nftables、eBPF option、順序付き policy tier と host/workload policy | Calico 3.33.0 は Kubernetes 1.35–1.37 でテストされています。upgrade 前に release note を確認してください。Windows には Linux eBPF または WireGuard dataplane がないことを含む個別の制限があります。Whisker/Goldmane flow observability は Tech Preview として利用できます。有償 capability については edition matrix を確認してください。 |
| **Flannel 0.28.9** | Host subnet allocation と inter-node transport、VXLAN、host-gw、その他の backend | `flanneld` 自体は NetworkPolicy を強制しません。chart の optional `netpol.enabled` は SIGs policy controller を deploy します。WireGuard は文書化された backend で、IPsec は experimental です。Windows VXLAN には固有の設定/制限があります。 |
| **AWS VPC CNI 1.23.0 upstream/Helm examples; EKS add-on `v1.23.1-eksbuild.1`** | VPC address allocation と EC2 ENI/prefix、サポート対象 Linux EC2 node での EKS standard および Admin network policy capability | AWS は Kubernetes 1.31–1.37 向けにこの managed add-on build を掲載しています。region availability と cluster の実際の version を確認してください。EKS Auto Mode は、追加の DNS policy capability を備えた managed networking implementation です。Windows、Fargate、custom networking、prefix delegation、multi-NIC support には個別の条件があります。 |
| **Original Weave Net project** | 歴史的な overlay networking implementation | 元の `weaveworks/weave` repository は archive されています。新しい cluster の active でサポートされる default として記述しないでください。 |

### Policy、Encryption、Observability

- Cilium は該当する L7 component を通じた HTTP/DNS-aware policy と、cluster-wide/host policy を提供します。その deny/allow semantics は Calico の順序付き Tier API ではありません。
- Calico Open Source には hierarchical policy tier と host policy が含まれます。現在の product matrix では application-layer policy、DNS/FQDN policy、Cluster Mesh は Cloud/Enterprise に割り当てられています。これらを open-source edition に暗黙に帰属させてはいけません。Calico が文書化している in-transit encryption には WireGuard を使用します。
- Amazon EKS は、Auto Mode とサポート対象 EC2/VPC-CNI installation 向けに `ClusterNetworkPolicy` Admin/Baseline control を提供します。AWS が説明する DNS/FQDN `ApplicationNetworkPolicy` feature は **Auto Mode** 向けです。その名前は、現在の HTTP method/body inspection を意味しません。
- Flannel の optional policy controller には独自の要件があります。networking backend を選択するだけでは enforcement は有効になりません。
- node-to-node encryption、authenticated workload identity、application mTLS は異なる control です。network flow visibility も application tracing や process/file enforcement とは異なります。

### Routing and Performance

Calico と Cilium は BGP を使用して route を advertise できます。それだけでは multi-cluster Service discovery、policy synchronization、encryption は提供されません。Flannel host-gw は direct route を使用し、適切な layer-2 connectivity が必要です。overlay には encapsulation と MTU の考慮事項が追加されますが、CNI 名から普遍的な performance ranking を推測することはできません。

以前の 100/98/95/85/80/75 percent throughput の数値には、再現可能な workload、version、measurement source がありませんでした。同等の hardware、kernel、packet/request size、concurrency、encryption/policy setting、throughput、loss、tail latency を使用してください。個別の [Pod benchmark](06-pod-network-benchmark.md)には、独自の歴史的環境と測定値が残されています。

## CNI Selection Guide

まず必要な routing、policy、operating-system、support model を選択し、次にその組み合わせをテストしてください。

| ニーズ | 評価パス |
|---|---|
| Standard EKS VPC addressing とサポートされる network policy | 2 つ目の policy engine を追加する前に、AWS VPC CNI/EKS capability を評価する。 |
| 順序付き policy tier、host policy、infrastructure BGP | 該当する Calico edition/dataplane と routing の前提条件を評価する。 |
| Cilium policy、Hubble、または選択した mesh feature | Linux/kernel/platform compatibility と [Cilium mesh guide](../service-mesh/cilium-service-mesh/README.md)を確認する。Envoy は該当する L7 path の一部であり続けます。 |
| feature set が限定された小規模 network | Flannel の backend と optional policy controller を実際の要件に照らして評価する。 |
| process、syscall、file enforcement | Tetragon などの runtime-security component を network policy とは別に評価する。 |

### EKS Managed Add-on Configuration

以下は **configuration payload** の例であり、同じ workload で Calico と VPC CNI policy engine の両方をインストールする指示ではありません。

```json
{
  "enableNetworkPolicy": "true"
}
```

文字列の `"true"` はこの設定で文書化された type です。既存の Kubernetes version に適合する EKS add-on build を選択し、その build の configuration schema を確認してください。

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

upstream の 1.23.0 release number と EKS の `eksbuild` version は異なる identifier です。AWS の現在の add-on table は Kubernetes 1.31–1.37 向けに `v1.23.1-eksbuild.1` を掲載しています。対象 Region で `describe-addon-versions` を使用し、互換性のある build を選択してください。変更は意図した managed add-on configuration と merge してください。`latest` を無条件に選択したり、無関係な value を置き換えたりしないでください。third-party policy implementation からの migration には、既存 enforcement state の削除と、テスト済みの node/workload transition plan も必要です。

## EKS Networking Fundamentals

### EKS Default Networking Architecture

| 場所 / コンポーネント | 責務 |
|---|---|
| EKS-managed VPC | AWS は Availability Zone 全体にわたって managed Kubernetes control plane を実行します。 |
| Customer cluster VPC | Worker networking、選択した subnet、EKS 管理 cross-account ENI が control plane への構成済み path を提供します。 |
| 選択した customer VPC subnet の ALB/NLB | 選択した public または internal application entry point を提供します。internet gateway/NAT gateway はその routing configuration の代替ではありません。 |
| NAT gateway または private service endpoint | workload design が必要とする特定の outbound path を提供します。 |

以前の図では control plane を customer VPC 内、load balancer をその外部に配置していましたが、これらの ownership boundary に置き換えられました。

### Compute Mode ごとの DNS と Networking

| Compute mode | DNS / component 配置 |
|---|---|
| Standard EC2 node | 通常、構成済みの CoreDNS Deployment とインストール済み networking component を使用します。置き換える場合は、独自のサポート対象 configuration が必要です。 |
| Pure EKS Auto Mode | CoreDNS、VPC CNI、kube-proxy function は managed node systemd service として実行されます。これらの node に CoreDNS Deployment/add-on は不要です。 |
| Auto Mode と non-Auto node の混在 | non-Auto node 向けに CoreDNS Deployment を維持します。他の node の Auto Mode DNS service は使用できません。 |

Auto Mode の最初の DNS resolver は node-local です。upstream forwarding と control-plane communication には引き続き network access が必要な場合があります。これは DNS 関連 packet のすべてが node 上に留まる保証ではありません。AWS は Auto Mode 向けに Admin と DNS policy の両方を文書化しています。一方、standard EC2 VPC-CNI Admin policy には独自の version/enabling 要件があります。

### How VPC CNI Works

AWS VPC CNI は、選択した IPAM mode を使用して通常の Pod に VPC-routable address を与えます。secondary IPv4 address、delegated prefix、branch ENI、multi-NIC 構成は異なります。host-network Pod は node network を共有します。

![EC2 ENI から Pod への secondary-IPv4 割り当てと、optional warm interface の例。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

これは secondary-IP mode のみを示しています。warm ENI は構成可能な allocation strategy であり、すべての node が常に 1 つだけ予約する要件ではありません。prefix delegation、custom networking、branch ENI には異なる allocation rule があります。

#### ENI and IP Limits

| Instance Type | Max ENIs | ENI あたりの IPv4 slot | 旧式の secondary-IP bootstrap 値 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

これらの値は、VPC CNI 1.23.0 の instance limit と旧来の max-Pods table に照らして検証されています。歴史的な計算式は `ENIs × (IPv4 slots per ENI − 1) + 2` です。これは現在の普遍的な推奨事項ではありません。prefix delegation、custom networking、branch ENI、複数の network card は address capacity を変更します。Kubernetes scheduling は kubelet `maxPods` と resource によっても制限されます。EKS managed node group は、30 vCPU 未満の instance では `maxPods` を 110、それ以外では 250 に制限します。利用可能な IP count だけでその cap を上書きすることはできません。

### EKS Networking Considerations

#### IP Address Management

**Linux VPC CNI** では、選択した add-on/Helm/DaemonSet 管理 mechanism を通じて、文書化された environment variable を構成します。以下は EKS add-on configuration fragment です。古い `amazon-vpc-cni` ConfigMap の `enable-prefix-delegation` は、この方法で Linux IPAMD を構成しません。変更を適用する際は、他の意図した add-on value を保持してください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

または、total allocation floor と free-IP target を調整します。`MINIMUM_IP_TARGET` または `WARM_IP_TARGET` のいずれかを構成すると、`WARM_PREFIX_TARGET` より優先されます。これらは 4 つの独立した加算 target ではなく、代替 policy です。allocation は引き続き prefix-sized unit で行われます。Nitro support、IPv4 用の連続した `/28` space、適切な kubelet Pod limit は別個の前提条件です。

Windows prefix allocation は異なる configuration path です。AWS は `amazon-vpc-cni` ConfigMap 内の `enable-windows-prefix-delegation` とその warm-target key を文書化しています。Linux の environment-variable 手順を変更せずに Windows へコピーしないでください。

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

これらの IPv4 の例には、対象の AZ と VPC 内の実際の subnet/security-group ID が必要です。custom networking を有効にし、各 node の ENIConfig を zone label により選択してください。明示的な ENIConfig node annotation はその label より優先されます。以下の例の name は両方の言語で同じ region を使用しています。実際の node zone に置き換えてください。ENIConfig object をインストールするだけでは custom networking は有効になりません。

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

以下の項目は、この概要の他の箇所で簡単に言及されています。完全な setup procedure と測定値はリンク先の deep-dive page にあります。このセクションでは、これらの要素が layer ごとにどう異なるか、そして各々がどこに適合するかを整理します。

### L2–L7 と Router と Load Balancer の違い

「Router」と「load balancer」は同じ文でよく使われますが、答える問いは異なります。router は（通常）単一 destination への 1 つの path を選び、load balancer は distribution algorithm を使用して、複数の等価な candidate から 1 つの target を選びます。

| Layer | Device/function | 判断基準 | Kubernetes/AWS の対応 |
|---|---|---|---|
| L2 (link) | Switch、bridge | Destination MAC address | CNI が作成する veth pair と Linux bridge、ENI が公開する virtual NIC |
| L3 (network) | Router または transparent appliance insertion | routing は destination IP、appliance selection は flow identity | VPC の implicit router、TGW、GWLB は appliance 向けに IP packet を encapsulate |
| L4 (transport) | L4 load balancer | connection/flow identity。一般に 5-tuple | NLB、kube-proxy (iptables、IPVS、nftables)、個別の eBPF Service implementation |
| L7 (application) | L7 load balancer/reverse proxy | request ごとの host、path、header、protocol-aware | ALB、Ingress/Gateway API implementation、service-mesh sidecar (Envoy) |

重要な違いは **distribution の単位** です。L4 load balancer は通常、TCP connection または追跡された UDP flow に対して target を選択します。L7 proxy は、connection を共有する request を含め、サポートする各 application request に target を選択できます。GWLB は application request を解析するのではなく、encapsulate された IP flow を security appliance 間に分配します。flow stickiness は構成された timeout、health、failover の動作に依存します。flow が再割り当てまたは中断されないという保証ではありません。

> 📎 L2/L3 の protocol-level 定義は [Network Fundamentals Part 1](../basics/06-network-fundamentals-part1.md)、ALB/NLB target type と実際の configuration は [AWS Load Balancer Controller](03-aws-lb-controller.md)にあります。

### Cross-Account/VPC Connectivity: TGW、VPC Peering、GWLB、PrivateLink、Lattice

これら 5 つの connectivity option は layer と traffic model が異なります。TGW RAM sharing、VPC Peering、PrivateLink、TGW Peering、VPC Lattice にわたる測定 latency は [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md)にあります。このセクションでは、その比較 table にはない GWLB を追加し、5 つすべてを layer ごとに再構成します。

| Connectivity | Layer/model | 特性 |
|---|---|---|
| VPC Peering | L3、bidirectional IP routing | transitive ではない。overlap する CIDR 間には構成できない |
| Transit Gateway (TGW) | L3、hub-and-spoke IP routing | 1 つ以上の TGW route table にわたる attachment association と propagation を使用。RAM による cross-account 共有 |
| Gateway Load Balancer (GWLB) | L3、transparent appliance insertion | 元の packet を GENEVE (UDP 6081) で encapsulate。VPC endpoint service model が consumer traffic を provider の appliance fleet に接続 |
| PrivateLink | Private endpoint connectivity | NLB-backed endpoint service は 1 つの model。resource endpoint も存在。consumer/provider CIDR は overlap 可能 |
| VPC Lattice | Application と resource networking | HTTP/HTTPS Service は L7 routing と optional IAM authorization を support。TLS passthrough と resource configuration には異なる capability がある |

GWLB は Gateway Load Balancer endpoint を通じて firewall や IDS/IPS などの inspection appliance を IP path に挿入します。default の flow stickiness は 5 field を使用します。サポートされる構成では、代わりに 2 または 3 field を使用できます。forward/return route、appliance health、encapsulation MTU、NACL、実際の workload/appliance の security group を検証してください。GWLB 自体には ALB 形式の security group はありません。また flow stickiness は failure test の代替にはなりません。

> 📎 完全な EKS/VPC Lattice integration (Gateway API Controller、IAM authorization、routing) は [VPC Lattice](02-vpc-lattice.md)にあります。

### DNS Resolver と Route Table の実際の動作

**DNS resolver:** AmazonProvidedDNS **は Route 53 Resolver です**。address には、primary VPC IPv4 network address に 2 を足したもの（`10.0.0.0/16` では `10.0.0.2`）と `169.254.169.253` が含まれます。Resolver rule に従って、関連付けられた private zone と public name を解決します。CoreDNS は通常、構成済み Kubernetes cluster domain（多くの場合 `cluster.local`）を提供します。`kube-dns` は Service name であり、namespace や DNS zone ではありません。external forwarding は Corefile と DNS Pod から見える resolver file に従います。node の resolver file がそのまま使用されると仮定せず、これらの設定を調べてください。Resolver endpoint design では、inbound endpoint が on-premises query を受け取り、outbound endpoint と関連付けられた rule が選択した VPC query を on-premises DNS に forward します。Auto Mode の node-local resolver でも upstream dependency はなくなりません。

**Route table:** VPC の route evaluation は一般に longest-prefix matching を使用します。AWS では、`local` route の target の置き換えと、appliance routing 用にサポートされるより specific な subnet route の追加が可能です。`local` が無条件に最も specific な route となるわけではありません。同一 destination では、static VPC route が virtual private gateway から propagated された route より優先されます。TGW を target とする VPC route は static です。TGW 内の propagation は、別個の route table に属します。invalid target により traffic を drop する `blackhole` entry が残る可能性があるため、destination だけでなく route state も調べてください。明示的な route-table association がない subnet は VPC の main route table を使用します。

> 📎 TGW/Peering route priority と static-route configuration の例は、[Cross-Org VPC Connectivity の operational findings](05-cross-org-vpc-connectivity.md#operational-findings)にあります。

### Kernel Data Plane: iptables、IPVS、eBPF、Packet Filtering

Linux Service forwarding と network-policy enforcement は異なる mechanism を使用できます。Netfilter は iptables と nftables が使用する packet-path hook を提供します。eBPF implementation は XDP、tc、socket hook に attach し、そこで Service selection を実行できます。これは eBPF-enabled cluster のすべての packet が Netfilter または connection tracking を bypass することを意味しません。path は CNI、kernel、routing、feature configuration に依存します。

| Implementation | 配置場所 | 特性 |
|---|---|---|
| iptables | netfilter hook 上の順次 rule chain | evaluation time は rule count に比例 (O(n))。kube-proxy の長年の default mode |
| IPVS | kernel-native L4 load balancer、netfilter extension | hash-based lookup (ほぼ O(1))。Kubernetes 1.35 以降、kube-proxy mode として deprecated |
| nftables | iptables に対する netfilter の後継 framework | Kubernetes 1.33 以降 kube-proxy の stable mode。最初に kernel/CNI compatibility を確認 |
| eBPF (例: Cilium) | 構成された XDP、tc、socket hook | kube-proxy Service handling を置き換え可能。個別の implementation であり、path 固有の Netfilter/conntrack 動作を持つ |

implementation を切り替えると、kernel rule と active connection が残る可能性があります。distribution/CNI migration procedure に従い、必要に応じて workload を drain し、cleanup に必要な場合は node restart を計画してください。kube-proxy を eBPF-based CNI に置き換える場合も、implementation が同じ Service traffic を競合して処理しないよう、サポートされる cutover order が必要です。

> 📎 IPVS deprecation timeline と nftables stable transition は [Introduction to Kubernetes](../basics/04-kubernetes-introduction.md)、Cilium の eBPF kube-proxy replacement は [Cilium eBPF](cilium/02-ebpf.md)、Calico の eBPF data plane と migration procedure は [Calico eBPF](calico/06-ebpf-dataplane.md)で扱っています。

### Compute-Intensive Networking: ENI、EFA、NVLink、Optical Transceiver

ENI、EFA、NVLink は異なる path を扱います。**ENI** は 1 つの Availability Zone 内で EC2 instance にアタッチされる virtual network interface です。routing と policy が許可する場合、その通常の IP traffic は他の AZ や接続された VPC に到達できます（[VPC CNI](01-vpc-cni.md)を参照）。**EFA** は互換性のある MPI/NCCL software が libfabric 経由で使用する OS-bypass device を提供します。**EFA device traffic は routable ではなく、VPC/AZ boundary を越えられません**。EFA-with-ENA interface の ENA device を通る通常の IP traffic は routable のままです。EFA-only interface には ENA device も IP addressing もありません。**NVLink** は、サポートされる rack-scale NVLink domain を含む、サポート対象 system 内の GPU を接続します。EFA に対する固定 speedup を想定するのではなく、選択した hardware、collective operation、placement を測定してください。

**Optical transceiver** は一般的な data-center networking の概念です。Copper DAC (Direct Attach Copper) cable は短距離に適し、optical module と fiber は他の到達距離および bandwidth 要件をサポートします。QSFP と OSFP は module form factor を記述するものであり、optical media を保証するものではありません。これは一般的な背景情報として扱ってください。特定の AWS workload の physical cabling を示すものではありません。

> 📎 NVLink/IMEX topology-aware scheduling と GPU Pod placement の例は [AI/ML Infrastructure](../ai-ml/06-ai-infrastructure.md)、EFA の VPC/AZ boundary constraint と測定値は [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md)にあります。

### Kubernetes における次世代 Protocol の意味: HTTP/3、gRPC、QUIC

HTTP/3 (RFC 9114) とその QUIC transport (RFC 9000) の protocol mechanics は、[Network Fundamentals Part 2](../basics/06-network-fundamentals-part2.md)および [Part 3](../basics/06-network-fundamentals-part3.md)で扱っています。ここでは、Kubernetes traffic distribution に実際に影響することだけを扱います。

- **gRPC と L4 load balancer:** gRPC は HTTP/2 connection 上で request を multiplex します。L4 balancer は通常、established TCP connection を選択した endpoint に維持します。その endpoint が proxy であれば、さらに routing decision を行えます。Pod を追加しただけでは既存 connection は再分配されません。RPC ごとの distribution には、互換性のある L7 proxy または client-side policy が必要です。streaming RPC は 1 つの call のままであり、個々の message が独立して balance されることはありません。
- **Gateway API の GRPCRoute:** Ingress には gRPC 固有 resource はありませんが、Gateway API は `GRPCRoute` により service/method-level routing を標準化します。support は implementation により異なります（header match の数、retry policy など）。そのため controller 独自の documentation を確認してください。
- **HTTP/3/QUIC が実際に cluster 内へ到達する範囲:** client と edge（CDN、load balancer）間の HTTP/3 support は、cluster 内または Ingress の backend connection での HTTP/3 support とは別の問題です。多くの Ingress/Gateway implementation は backend と HTTP/1.1 または HTTP/2 で通信します。end-to-end HTTP/3 がサポートされるかは implementation と version により異なります。一般化せず、実際に使用する controller の documentation を確認してください。

## Networking Sub-pages

このセクションでは、以下の topic を詳しく扱います。

### [Linux Networking from the Beginning](beginner/README.md) {#beginner-course}

Linux または networking を初めて学ぶ場合は、[初級コース](beginner/README.md)から始めてください。8 つのレッスンで、CLI、アドレッシング、DNS、SSH、firewall、監視、capstone を結び付けます。以下のパスは、この基礎をプロトコル、kernel、cluster 実装へと拡張します。

### [Expert Networking Path](expert/README.md) {#expert-course}

初級コースの後は、[エキスパート networking パス](expert/README.md)を使用して、プロトコルプロジェクト、routing policy、EVPN、Linux performance、cloud design、自動化評価を結び付けてください。最初に各ワークブックの環境、エビデンス、復旧基準を確認してください。

### [Linux Network Diagnostics Practice](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

CNI implementation を学ぶ前に、[kernel socket と packet-path の概念](../kernel/02-network-stack.md)を観測に結び付けてください。解釈を確認するには、[diagnostics quiz](../quizzes/networking/07-linux-network-diagnostics-quiz.md)を使用してください。

### [VPC CNI](01-vpc-cni.md)
通常の Pod 向けの VPC address と、mode 固有の IPAM/policy 前提条件を使用する EKS networking。

### [Cilium Deep Dive](cilium/README.md)
高 performance の eBPF-based CNI solution。L7 Network Policy、Service Mesh、observability (Hubble) などの高度な feature を提供します。

### [Calico Deep Dive](calico/README.md)
最も広く使用される CNI の 1 つ。強力な Network Policy、BGP support、enterprise feature。intro、architecture、networking mode、BGP deep dive、Network Policy、eBPF、advanced topic、EKS integration、operations guide を扱います。

### [VPC Lattice](02-vpc-lattice.md)
AWS managed application networking service。cross-VPC、cross-account の service-to-service communication。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Kubernetes Service と Ingress を AWS ELB (ALB/NLB) に統合します。

### [Gateway API](04-gateway-api.md)
次世代の Kubernetes ingress API。標準化された resource model と role-based configuration。

### [Pod Network Benchmark](06-pod-network-benchmark.md)
同じ node、同じ AZ、cross-AZ における EKS 上の Pod-to-pod RTT、HTTP latency、throughput、および DNS `ndots:5` query amplification を測定します。

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

必要な tool がある既存の Pod から diagnostics を実行してください。cluster にインストールされた CNI のみを query してください。Auto Mode system service はこれらの DaemonSet ではありません。DNS success、TCP reachability、application HTTP response は異なる確認です。ICMP は block されるか追加 privilege を必要とする場合があるため、ping の失敗だけでは TCP Service に到達できないことの証明にはなりません。

#### Service Unreachable

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

現在の endpoint diagnosis には EndpointSlice を使用してください。Service selector、target port、endpoint readiness、address family、適用される policy を確認します。kube-proxy log は、その component が実際に Service forwarding を所有する場合にのみ調べてください。eBPF replacement または Auto Mode には独自の diagnostics が必要です。

#### Network Policy Debugging

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium command は DaemonSet reference により選択した 1 つの Agent を調べます。incident を追跡する際は、影響を受けた node の Agent を選択してください。Calico native API installation は別の API group を公開する可能性があるため、installation が提供する resource を調べてください。Kubernetes、Calico、AWS extension policy は別個の resource であり、precedence が異なる可能性があります。

### Network Performance Testing

この制限付き TCP exercise では、Linux AMD64 と Arm64 image を含み、Dockerfile に `iperf3` を含む、publisher が固定した Netshoot v0.16 image index を使用します。TCP 5201 が許可された test environment でこれらの Pod を作成してください。これは例示的な workload であり、測定済み CNI comparison ではありません。

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

client は 1 時間 sleep し、この command は 10 秒間、offered traffic を 10 Mbit/s に制限します。これは選択した path をテストするものであり、maximum throughput をテストするものではありません。result を解釈する前に、実際の Pod/node/AZ placement、resource limit、policy を記録してください。Windows node には Windows 固有の tool を選択してください。完了したら、自分で作成した test resource だけを削除してください。

これらの standalone diagnostic Pod は connectivity test 用です。native EKS network-policy enforcement test には、Deployment/Job-managed Pod と、文書化された Service/container-port 要件を使用してください。

## Best Practices

### 1. IP Address Planning

- 十分に大きな CIDR block を設計する
- Pod network を Service network から分離する
- 将来の拡張を考慮して subnet を設計する

### 2. Network Policy を適用する

この例を使用する前に、隔離された `networking-demo` namespace を作成してください。これはそこにあるすべての Pod を選択し、standard Kubernetes NetworkPolicy semantics により ingress と egress の両方を隔離します。必要な DNS と application flow には明示的な allow rule が必要です。enforcement にはサポートする policy engine が必要です。追加の cluster/admin policy API は precedence を変更する可能性があり、この 1 つの manifest は完全な zero-trust architecture ではありません。

- default deny policy (Zero Trust) を適用する
- 必要な traffic のみを明示的に許可する
- namespace を隔離する

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

- 適切な CNI を選択する（workload に合わせる）
- MTU optimization
- Kernel parameter tuning

### 4. Security Hardening

- サポートされる transport encryption を選択し、それが対象とする traffic を確認する。
- 必要に応じて workload/application identity と mTLS を構成する。これらは DNS/IP-based allowlist とは別に扱う。
- policy、certificate、access-control の変更を定期的に見直す。

### 5. Observability を確保する

- network metric を収集する
- flow log を有効にする
- distributed tracing を実装する

## Next Steps

[初級コース](beginner/README.md)の後、[Kernel Networking Stack](../kernel/02-network-stack.md)、次に [Linux Network Diagnostics Practice](07-linux-network-diagnostics.md)とその[quiz](../quizzes/networking/07-linux-network-diagnostics-quiz.md)へ進んでください。[学習パス](#learning-path)は、以下の CNI と AWS topic の前に、これらの基礎を container と Service に結び付けます。

1. [VPC CNI](01-vpc-cni.md) - Default EKS CNI
2. [Cilium Deep Dive](cilium/README.md) - eBPF-based networking
3. [Calico Deep Dive](calico/README.md) - Routing、policy、dataplane
4. [VPC Lattice](02-vpc-lattice.md) - AWS managed networking
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB integration
6. [Gateway API](04-gateway-api.md) - 次世代 ingress
7. [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) - AWS Organizations をまたぐ VPC の接続（field-verified）
8. [Pod Network Benchmark](06-pod-network-benchmark.md) - node/AZ boundary ごとの測定済み latency と throughput

---

## 参考資料

- [Kubernetes network model](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Container runtime and CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI specification](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico product editions](https://docs.tigera.io/calico/latest/about)
- [Calico Open Source 3.33.0 release](https://github.com/projectcalico/calico/releases/tag/v3.33.0)
- [Calico policy tiers](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker flow logs](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows limitations](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 networking and policy](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel backends](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Original Weave repository status](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [Amazon EKS latest VPC CNI add-on versions](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
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
