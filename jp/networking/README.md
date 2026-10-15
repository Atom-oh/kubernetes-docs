# Kubernetes ネットワーキング

> **最終更新**: September 15, 2026. 機能の参照先には Cilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9、および AWS VPC CNI 1.23.0 が含まれます。インストール前に各製品の Kubernetes/プラットフォーム互換性マトリクスを確認してください。これらは共同でテストされたクラスター構成ではありません。

## 概要

Kubernetes ネットワーキングは、コンテナ化されたアプリケーション間の通信を可能にする中核インフラストラクチャレイヤーです。このセクションでは、基本的な Kubernetes ネットワーキングの概念から、高度な CNI (Container Network Interface) ソリューション、AWS EKS 環境でのネットワーキングパターンまでを扱います。

## 学習パス {#learning-path}

Linux またはネットワーキングが初めての場合は、[初級コース](beginner/README.md)から始めてください。その 8 つのレッスンでは、CLI、アドレッシング、DNS、SSH、ファイアウォール、モニタリング、そして総合演習を結び付けます。以下のパスでは、その基礎をプロトコル、カーネル、クラスター実装へと拡張します。

プロトコルの概念から観測へと積み上げ、それをコンテナ、クラスター、クラウドの責任範囲に結び付けます。前提条件を使用して開始地点を選び、続行前に成果で理解を確認してください。

| Stage | Role | Prerequisites | Outcome | Read / practice |
|---|---|---|---|---|
| プロトコル、アドレッシング、HTTP | 用語を確立する | 基本的なコマンドラインの使用 | リクエストを追跡し、アドレッシング、トランスポート、アプリケーションの動作を区別する | ネットワークの基礎 [Part 1](../basics/06-network-fundamentals-part1.md)、[Part 2](../basics/06-network-fundamentals-part2.md)、[Part 3](../basics/06-network-fundamentals-part3.md)、[Part 4](../basics/06-network-fundamentals-part4.md) |
| Linux ソケット、VFS、パケットパス | API をカーネルに結び付ける | TCP/IP の基礎 | FD、ソケットバッファ、ウィンドウ、キューを区別する | [カーネルネットワーキングスタック](../kernel/02-network-stack.md) |
| Linux ネットワーク診断 | 根拠を用いて仮説を検証する | ソケットおよびパケットパスの概念 | ソケット、パケット、アプリケーションの観測結果を関連付ける | [診断演習](07-linux-network-diagnostics.md) · [クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker とコンテナネットワーキング | namespace の境界を特定する | Linux パケットパスと基本的な診断 | ブリッジネットワーキング、公開ポート、コンテナ名解決を説明する | [コンテナテクノロジー](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | クラスター抽象化を対応付ける | コンテナネットワーキング | 名前を Service 経由でその endpoint まで追跡し、Ingress の役割を特定する | [Service とネットワーキング](../core/03-services-networking.md) · [ラボ](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、ポリシー | 実装の責任範囲を比較する | Pod と Service のパス | パケット転送、ポリシー適用、可観測性を区別する | [eBPF の基礎](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS ネットワーク境界とパフォーマンス | モデルをクラウドパスに適用する | CNI の概念と測定スキル | VPC、ノード、AZ の境界を特定し、文脈の中で測定値を解釈する | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) · [Pod Network Benchmark](06-pod-network-benchmark.md) |

## Kubernetes ネットワーキングモデル

現在の Kubernetes モデルは、**意図的なネットワーク分離を前提として**、Pod がアドレス変換やプロキシなしでノードをまたいで直接通信できる Pod ネットワークを提供します。kubelet などのノードエージェントは、自身のノード上の Pod に到達できる必要があります。特定の接続が成功するかどうかは、依然として NetworkPolicy、ルーティング、アプリケーションリスナーによって決まります。

通常の Pod には独自のネットワーク namespace とクラスター全体で有効なアドレスがあり、1 つの Pod 内のコンテナはその namespace と localhost を共有します。host-network Pod はノードネットワークを共有し、dual-stack または multi-network 構成では、より正確なアドレス処理が必要です。Pod を再作成すると異なる IP が割り当てられることがあります。同じ Pod 内のコンテナを再起動しても、必ずしもそのネットワークサンドボックスが再作成されるわけではありません。

| Component | Role |
|---|---|
| Pod ネットワーク | workload のネットワーク namespace 間のアドレッシングと接続性 |
| Service/ディスカバリー | 変化する endpoint に対する安定した Service 名または仮想アドレス |
| Ingress/Gateway 実装 | 構成済みの外部エントリーとアプリケーションルーティング |
| NetworkPolicy エンジン | 選択した実装でサポートされるポリシーを適用する |

これらの役割は、必須の直列パケットパスを構成するものではありません。Service 変換、L7 プロキシ、workload ポリシーにより、特定のリクエストがネットワークを通過する方法は変わる可能性があります。

### Pod ネットワーキング

Pod ネットワーキングは、Pod 通信のためのアドレッシングとルートを提供します。以下の図は通常の IPv4 Pod を示しており、その接続は該当するポリシーとネットワーク制御が許可していることを前提とします。

![構成されたポリシーとルーティングに従う、2 つのノードにまたがる直接 IPv4 Pod パスの例。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

アドレスは例示的な通常の Pod アドレスです。意図的な分離、および host-network または multi-network 構成には、それぞれ固有の解釈が必要です。

#### Pod ネットワーキングの実装方式

| Method | Description | Example CNI |
|--------|-------------|-------------|
| **Overlay Network** | 既存のネットワーク上でトラフィックをカプセル化する | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **Native Routing** | overlay カプセル化なしで、基盤ネットワーク内のルートを使用する | AWS VPC CNI、Calico routing/BGP、Cilium native routing |
| **Conditional Encapsulation** | 構成済みトポロジーに応じて直接パスまたはカプセル化を使用する | 前提条件が異なる、サポート対象の Calico/Flannel/Cilium モード |

### Service ネットワーキング

Service は、通常は Pod からなる論理的な endpoint の集合と、その到達方法を記述します。ClusterIP はデフォルトで安定した仮想 IP を提供し、headless Service はその仮想 IP を省略します。ExternalName は DNS CNAME マッピングを使用します。Service は、Pod selector なしで管理される endpoint を持つこともできます。

![ClusterIP、NodePort、LoadBalancer、ExternalName Service の一般的なエントリーメカニズム。DNS マッピングはパケット転送と区別されます。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

これらは一般的な公開メカニズムであり、セキュリティ保証ではありません。NodePort の範囲とアクセス可能なノードアドレスは構成可能であり、LoadBalancer は internal にできます。ExternalName は DNS エイリアスを返すだけで、転送プロキシは作成しません。

#### Service タイプの特性

`default` に、表示された target port で listen する一致する `app: my-app` Pod を作成してください。NodePort のデフォルトの割り当て範囲は 30000–32767 であり、構成できます。外部からの到達可能性は依然としてアドレス、ルート、アクセス制御に依存します。

LoadBalancer の例では、EC2 instance target と割り当てられた NodePort を使用する **AWS Load Balancer Controller** を明示的に選択しています。まず、その controller と IAM/subnet の前提条件をインストールおよび構成してください。EKS Auto Mode は異なる controller/class を使用します。ここで port 443 は TCP port を選択しているだけであり、TLS は backend が 8443 で提供するか、load balancer 上で別途構成する必要があります。

これらのポートマッピングは、一般的な Kubernetes Service API を例示しています。AWS は現在、追加のネイティブ EKS NetworkPolicy 要件を文書化しています。Service port は container port と一致する必要があり、`metadata.ownerReferences` を持つ controller 管理 Pod は信頼性の高い適用を提供します。このポリシー実装をテストする前に、例をそれらの要件に適合させてください。

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

### Ingress ネットワーキング

Ingress resource には controller とその data plane が必要です。この HTTP の例では、`spec.ingressClassName: alb` と IP target を持つ AWS LBC を使用します。参照される `api-v1`、`api-v2`、`web-frontend` Service は `default` に存在し、port 80 を公開し、ready で VPC-routable な Pod endpoint を持つ必要があります。必要な場合は HTTPS/certificate を別途構成してください。インストールと target の前提条件については、[LBC ガイド](03-aws-lb-controller.md)を参照してください。

Ingress は、HTTP/HTTPS トラフィックを内部クラスター Service にルーティングするルールを定義します。

![Service backend と Pod への論理的な Ingress host/path ルーティング。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

ボックスは Ingress の data-plane 機能を表します。AWS LBC は ALB をプログラムします。アプリケーショントラフィックは controller の reconciliation process を通過しません。target mode に応じて、data plane は Pod IP または NodePort に到達できます。これは Service 仮想 IP を文字どおり追加の hop として通過するのとは異なります。

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

CNI は、runtime がコンテナネットワークを構成するためのインターフェイスを標準化します。現在の Kubernetes では、kubelet は CRI 経由で Pod-sandbox 操作を要求し、**container runtime が CNI を管理します**。kubelet の古い直接 CNI 管理フラグは Kubernetes 1.24 で削除されました。

### Runtime と Plugin の責任範囲

| Actor | Responsibility |
|---|---|
| kubelet | container runtime interface を通じて sandbox の作成/削除を要求する |
| Container runtime | ネットワーク構成を選択し、CNI plugin chain を呼び出す |
| CNI plugin | 構成を受け取り、ADD/DEL とその他のサポートされる操作を実行し、結果を返す |
| IPAM 実装 | アドレスを割り当て/解放する。委譲された plugin、または provider 固有 agent の一部の場合がある |
| オプションの node agent | provider 固有のルート、ポリシー、IP pool、または datapath state を維持する |

runtime は CNI interface 経由で plugin に構成を渡します。個別の長時間実行 agent や IPAM binary は、すべての plugin に必須ではありません。interface type も異なり、veth pair は一般的ですが唯一の実装ではありません。

## CNI 比較

| Project / scope | Networking and policy | Features and limits to distinguish |
|---|---|---|
| **Cilium 1.20.1** | eBPF ネットワーキング、該当する L7 機能には Envoy、Cilium NetworkPolicy と Hubble | AMD64/Arm64 要件を持つ Linux worker dataplane。Windows CLI の可用性は Windows CNI のサポートを意味しません。WireGuard/IPsec と Beta ztunnel mTLS は対象範囲が異なります。 |
| **Calico Open Source 3.32** | routing/encapsulation の選択肢、iptables、nftables、eBPF のオプション、順序付き policy tier と host/workload policy | Windows には Linux eBPF または WireGuard dataplane がないことを含む、別個の制限があります。Whisker/Goldmane のフロー可観測性は Tech Preview として利用できます。有償機能については edition matrix を参照してください。 |
| **Flannel 0.28.9** | Host subnet 割り当てと node 間 transport、VXLAN、host-gw、その他の backend | `flanneld` 自体は NetworkPolicy を適用しません。chart のオプション `netpol.enabled` は SIGs policy controller をデプロイします。WireGuard は文書化された backend であり、IPsec は実験的です。Windows VXLAN には固有の設定/制限があります。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPC アドレス割り当てと EC2 ENI/prefix、サポート対象の Linux EC2 node での EKS standard および Admin network policy 機能 | EKS Auto Mode は、追加の DNS policy 機能を備えたマネージドネットワーキング実装です。Windows、Fargate、custom networking、prefix delegation、multi-NIC サポートには個別の条件があります。 |
| **Original Weave Net project** | 歴史的な overlay networking 実装 | 元の `weaveworks/weave` repository はアーカイブされています。新しいクラスターに対するアクティブでサポートされたデフォルトとして説明しないでください。 |

### Policy、Encryption、Observability

- Cilium は、該当する L7 component を通じて HTTP/DNS 対応 policy、および cluster-wide/host policy を提供します。その deny/allow semantics は Calico の順序付き Tier API とは異なります。
- Calico Open Source には、階層的な policy tier と host policy が含まれます。現在の product matrix は application-layer policy、DNS/FQDN policy、Cluster Mesh を Cloud/Enterprise に割り当てています。これらを open-source edition の機能として暗黙に帰属させてはなりません。Calico の文書化された transit 中の encryption は WireGuard を使用します。
- Amazon EKS は、Auto Mode とサポート対象の EC2/VPC-CNI インストール用に `ClusterNetworkPolicy` Admin/Baseline control を提供します。AWS が説明する DNS/FQDN `ApplicationNetworkPolicy` 機能は **Auto Mode** 用です。その名前は、現在の HTTP method/body inspection を意味するものではありません。
- Flannel のオプション policy controller には独自の要件があります。networking backend を選択しただけでは適用は有効になりません。
- node 間 encryption、認証された workload identity、application mTLS は異なる control です。ネットワークフローの可視性も、application tracing や process/file enforcement とは異なります。

### Routing と Performance

Calico と Cilium は BGP を使用して route を advertise できますが、それだけで multi-cluster Service discovery、policy synchronization、または encryption が提供されるわけではありません。Flannel host-gw は直接 route を使用し、適切な layer-2 接続性が必要です。overlay は encapsulation と MTU の考慮事項を追加しますが、CNI 名から普遍的な performance ranking を導くことはできません。

以前の 100/98/95/85/80/75 percent の throughput 数値には、再現可能な workload、version、または measurement source がありませんでした。同等の hardware、kernel、packet/request size、concurrency、encryption/policy 設定、throughput、loss、tail latency を使用してください。個別の [Pod benchmark](06-pod-network-benchmark.md) には、独自の歴史的環境と測定値が残されています。

## CNI 選定ガイド

まず必要な routing、policy、operating-system、support model を選択し、その組み合わせをテストしてください。

| Need | Evaluation path |
|---|---|
| 標準の EKS VPC アドレッシングとサポート対象の NetworkPolicy | 2 つ目の policy engine を追加する前に、AWS VPC CNI/EKS の機能を評価する。 |
| 順序付き policy tier、host policy、または infrastructure BGP | 関連する Calico edition/dataplane と routing の前提条件を評価する。 |
| Cilium policy、Hubble、または選択した mesh 機能 | Linux/kernel/platform の互換性と [Cilium mesh ガイド](../service-mesh/cilium-service-mesh/README.md)を確認する。Envoy は該当する L7 path の一部として残ります。 |
| 機能セットが限定された小規模ネットワーク | Flannel の backend とオプションの policy controller を実際の要件に照らして評価する。 |
| Process、syscall、file enforcement | Tetragon などの runtime-security component を NetworkPolicy とは別に評価する。 |

### EKS Managed Add-on Configuration

以下は **configuration payload** の例であり、同じ workload に Calico と VPC CNI policy engine の両方をインストールする手順ではありません。

```json
{
  "enableNetworkPolicy": "true"
}
```

文字列の `"true"` は、この設定で文書化されている型です。既存の Kubernetes version と互換性がある EKS add-on build を選択し、その build の configuration schema を調べてください。

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

upstream の 1.23.0 release number と EKS の `eksbuild` version は異なる識別子です。変更は意図した managed add-on configuration とマージしてください。`latest` を無条件に選択したり、無関係な値を置き換えたりしないでください。third-party policy 実装からの migration には、既存の enforcement state の削除と、テスト済みの node/workload transition plan も必要です。

## EKS ネットワーキングの基礎

### EKS デフォルトネットワーキングアーキテクチャ

| Location / component | Responsibility |
|---|---|
| EKS 管理 VPC | AWS は Availability Zone をまたいでマネージド Kubernetes control plane を実行します。 |
| Customer cluster VPC | worker ネットワーキング、選択した subnet、および EKS 管理の cross-account ENI が、control plane への構成済みパスを提供します。 |
| 選択した customer VPC subnet 内の ALB/NLB | 選択した public または internal application entry point を提供します。internet gateway/NAT gateway はその routing configuration の代替ではありません。 |
| NAT gateway または private service endpoint | workload design が必要とする特定の outbound path を提供します。 |

以前の図では control plane を customer VPC 内、load balancer をその外部に配置していましたが、これらの所有境界に置き換えられました。

### Compute Mode 別の DNS とネットワーキング

| Compute mode | DNS / component placement |
|---|---|
| Standard EC2 node | 通常、構成済みの CoreDNS Deployment とインストール済みの networking component を使用します。置き換える場合は、独自にサポートされた構成が必要です。 |
| Pure EKS Auto Mode | CoreDNS、VPC CNI、kube-proxy の機能は managed node systemd service として実行されます。これらの node には CoreDNS Deployment/add-on は不要です。 |
| Auto Mode と non-Auto node の混在 | non-Auto node 用に CoreDNS Deployment を維持します。これらの node は別の node の Auto Mode DNS service を使用できません。 |

Auto Mode の最初の DNS resolver は node-local です。upstream forwarding と control-plane 通信には依然として network access が必要なことがあり、すべての DNS 関連 packet が node に留まることを保証するものではありません。AWS は Auto Mode 向けに Admin と DNS の両方の policy を文書化していますが、standard EC2 VPC-CNI Admin policy には独自の version/enabling 要件があります。

### VPC CNI の仕組み

AWS VPC CNI は、選択した IPAM mode を使用して、通常の Pod に VPC-routable なアドレスを提供します。secondary IPv4 address、delegated prefix、branch ENI、multi-NIC 構成は異なり、host-network Pod は node network を共有します。

![オプションの warm interface を含む、EC2 ENI から Pod への secondary-IPv4 割り当ての例。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

これは secondary-IP mode のみを示しています。warm ENI は構成可能な割り当て戦略であり、すべての node が常に 1 つだけ予約しなければならないという要件ではありません。prefix delegation、custom networking、branch ENI には異なる割り当てルールがあります。

#### ENI と IP の制限

| Instance Type | Max ENIs | IPv4 slots per ENI | Legacy secondary-IP bootstrap value |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

これらの値は、VPC CNI 1.23.0 の instance limit と legacy max-Pods table に照らして検証されています。歴史的な計算式は `ENIs × (IPv4 slots per ENI − 1) + 2` です。これは現在の普遍的な推奨ではありません。prefix delegation、custom networking、branch ENI、複数の network card により address capacity は変わります。Kubernetes scheduling は kubelet の `maxPods` と resource によっても制限されます。EKS managed node group は、30 vCPU 未満の instance では `maxPods` を 110、それ以外では 250 に制限します。利用可能な IP 数だけではこの上限を上書きできません。

### EKS ネットワーキングの考慮事項

#### IP Address Management

**Linux VPC CNI** では、選択した add-on/Helm/DaemonSet 管理メカニズムを通じて、文書化された environment variable を構成してください。以下は EKS add-on configuration fragment です。`enable-prefix-delegation` を持つ古い `amazon-vpc-cni` ConfigMap では、この方法で Linux IPAMD は構成されません。変更を適用する際は、他の意図した add-on 値を保持してください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

代わりに、総割り当て下限と free-IP target を調整できます。`MINIMUM_IP_TARGET` または `WARM_IP_TARGET` のいずれかが構成されると、`WARM_PREFIX_TARGET` より優先されます。これらは 4 つの独立した加算 target ではなく、代替の policy です。割り当ては引き続き prefix size 単位で行われます。Nitro のサポート、IPv4 のための連続した `/28` space、適切な kubelet Pod limit は別個の前提条件です。

Windows prefix allocation は別の構成パスです。AWS は `amazon-vpc-cni` ConfigMap 内の `enable-windows-prefix-delegation` とその warm-target key を文書化しています。Linux の environment-variable 手順を変更せずに Windows へコピーしないでください。

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

これらの IPv4 例には、意図した AZ と VPC 内の実際の subnet/security-group ID が必要です。custom networking を有効にし、各 node の ENIConfig をその zone label で選択してください。明示的な ENIConfig node annotation は、その label より優先されます。以下の例の名前は両言語で同じ region を使用しています。実際の node zone に置き換えてください。ENIConfig object をインストールするだけでは custom networking は有効になりません。

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

## 高度なネットワーキングの概念

以下の項目は、この概要の他の箇所で簡単に言及されています。完全なセットアップ手順と測定値はリンク先の詳細ページにあります。このセクションでは、これらの要素が layer ごとにどのように異なり、それぞれがどこに位置付くかを整理します。

### L2–L7 と Router と Load Balancer の違い

「router」と「load balancer」は同じ文でよく登場しますが、答える問いは異なります。router は（一般に）単一の destination への 1 つの path を選び、load balancer は distribution algorithm を使用して複数の同等な candidate から 1 つの target を選びます。

| Layer | Device/function | Decision basis | Kubernetes/AWS mapping |
|---|---|---|---|
| L2 (link) | Switch、bridge | 宛先 MAC address | CNI が作成する veth pair と Linux bridge、ENI が公開する virtual NIC |
| L3 (network) | Router または transparent appliance insertion | routing のための destination IP、appliance 選択のための flow identity | VPC の implicit router、TGW。GWLB は appliance 向けに IP packet を encapsulate する |
| L4 (transport) | L4 load balancer | connection/flow identity、通常は 5-tuple | NLB、kube-proxy (iptables、IPVS、nftables)、個別の eBPF Service 実装 |
| L7 (application) | L7 load balancer/reverse proxy | request ごとの host、path、header、protocol-aware | ALB、Ingress/Gateway API 実装、service-mesh sidecar (Envoy) |

主な違いは **分散の単位** です。L4 load balancer は通常、TCP connection または追跡対象の UDP flow に対して target を選択します。L7 proxy は、connection を共有する request を含め、サポートする application request ごとに target を選択できます。GWLB は application request を解析するのではなく、security appliance 間で encapsulated IP flow を分散します。flow stickiness は構成された timeout、health、failover の動作に依存します。flow が再割り当てまたは中断されないことを保証するものではありません。

> 📎 L2/L3 概念のプロトコルレベルの定義は [Network Fundamentals Part 1](../basics/06-network-fundamentals-part1.md) にあります。ALB/NLB の target type と実際の構成は [AWS Load Balancer Controller](03-aws-lb-controller.md) にあります。

### Cross-Account/VPC Connectivity: TGW、VPC Peering、GWLB、PrivateLink、Lattice

これら 5 つの connectivity option は、layer と traffic model が異なります。TGW RAM sharing、VPC Peering、PrivateLink、TGW Peering、VPC Lattice をまたぐ測定済み latency は [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) にあります。このセクションでは、その比較 table にはない GWLB を追加し、5 つすべてを layer ごとに再構成します。

| Connectivity | Layer/model | Characteristics |
|---|---|---|
| VPC Peering | L3、双方向 IP routing | transitive ではない。overlap する CIDR 間では構成できない |
| Transit Gateway (TGW) | L3、hub-and-spoke IP routing | 1 つ以上の TGW route table 間で attachment association と propagation を使用する。RAM 経由で cross-account 共有する |
| Gateway Load Balancer (GWLB) | L3、transparent appliance insertion | 元の packet を GENEVE (UDP 6081) で encapsulate する。VPC endpoint service model が consumer traffic を provider の appliance fleet に接続する |
| PrivateLink | Private endpoint connectivity | NLB-backed endpoint service は 1 つの model。resource endpoint も存在する。consumer/provider CIDR は overlap 可能 |
| VPC Lattice | Application および resource networking | HTTP/HTTPS Service は L7 routing とオプションの IAM authorization をサポートする。TLS passthrough と resource configuration には異なる機能がある |

GWLB は、Gateway Load Balancer endpoint を介した IP path に firewall や IDS/IPS などの inspection appliance を挿入します。デフォルトの flow stickiness は 5 field を使用します。サポートされる構成では、代わりに 2 または 3 field を使用できます。forward と return の route、appliance health、encapsulation MTU、NACL、および実際の workload/appliance の security group を検証してください。GWLB 自体には ALB のような security group はなく、flow stickiness は failure testing の代替ではありません。

> 📎 完全な EKS/VPC Lattice integration (Gateway API Controller、IAM authorization、routing) は [VPC Lattice](02-vpc-lattice.md) にあります。

### DNS Resolver と Route Table の実際の動作

**DNS resolver:** AmazonProvidedDNS **は Route 53 Resolver です**。その address には、primary VPC IPv4 network address に 2 を加えたもの（`10.0.0.0/16` では `10.0.0.2`）と `169.254.169.253` が含まれます。Resolver rule に従って、関連付けられた private zone と public name を解決します。CoreDNS は通常、構成された Kubernetes cluster domain、多くの場合 `cluster.local` を提供します。`kube-dns` はその Service 名であり、namespace や DNS zone ではありません。external forwarding は Corefile と DNS Pod から見える resolver file に従います。node の resolver file が変更なしで使用されると想定せず、それらの設定を確認してください。Resolver endpoint design では、inbound endpoint が on-premises query を受け入れ、outbound endpoint と関連付けられた rule が選択された VPC query を on-premises DNS に転送します。Auto Mode の node-local resolver によって upstream dependency がなくなるわけではありません。

**Route table:** VPC の route evaluation は通常、longest-prefix matching を使用します。AWS では、`local` route の target の置換や、appliance routing のためのサポート対象のより specific な subnet route の追加が可能です。`local` は無条件に最も specific な route ではありません。同一 destination の場合、static VPC route は virtual private gateway から propagated された route より優先されます。TGW を target とする VPC route は static です。TGW 内部の propagation は、別個の route table に属します。無効な target は traffic を drop する `blackhole` entry を残すことがあるため、destination だけでなく route state も調べてください。明示的な route-table association がない subnet は、VPC の main route table を使用します。

> 📎 TGW/Peering の route priority と static-route configuration の例は、[Cross-Org VPC Connectivity の運用上の知見](05-cross-org-vpc-connectivity.md#operational-findings)にあります。

### Kernel Data Plane: iptables、IPVS、eBPF、Packet Filtering

Linux の Service forwarding と NetworkPolicy enforcement には異なる mechanism を使用できます。Netfilter は、iptables と nftables が使用する packet-path hook を提供します。eBPF 実装は XDP、tc、または socket hook に attach し、そこで Service selection を実行できます。これは、eBPF-enabled cluster 内のすべての packet が Netfilter や connection tracking を bypass することを意味するものではありません。path は CNI、kernel、routing、feature configuration に依存します。

| Implementation | Where it sits | Characteristics |
|---|---|---|
| iptables | netfilter hook 上の順次 rule chain | evaluation time は rule count に比例する (O(n))。kube-proxy の長年の default mode |
| IPVS | kernel-native L4 load balancer、netfilter extension | hash-based lookup (ほぼ O(1))。Kubernetes 1.35 から kube-proxy mode として deprecated |
| nftables | iptables の後継となる netfilter framework | 1.33 以降の kube-proxy stable mode。まず kernel/CNI compatibility を確認する |
| eBPF (例: Cilium) | 構成済みの XDP、tc、socket hook | kube-proxy の Service handling を置き換えられる。これは個別の実装であり、path 固有の Netfilter/conntrack 動作を持つ |

実装を切り替えると、kernel rule と active connection が残る可能性があります。distribution/CNI の migration procedure に従い、必要に応じて workload を drain し、cleanup に必要な node restart を計画してください。kube-proxy を eBPF-based CNI に置き換えるには、実装が同じ Service traffic を競合して処理しないよう、サポートされた cutover order も必要です。

> 📎 IPVS の deprecation timeline と nftables の stable transition は [Introduction to Kubernetes](../basics/04-kubernetes-introduction.md) で扱われています。Cilium の eBPF kube-proxy replacement は [Cilium eBPF](cilium/02-ebpf.md)、Calico の eBPF data plane と migration procedure は [Calico eBPF](calico/06-ebpf-dataplane.md) にあります。

### Compute-Intensive Networking: ENI、EFA、NVLink、Optical Transceiver

ENI、EFA、NVLink は異なる path に使用されます。**ENI** は 1 つの Availability Zone 内の EC2 instance に attach される virtual network interface です。その通常の IP traffic は、routing と policy が許可すれば、他の AZ や接続された VPC に到達できます（[VPC CNI](01-vpc-cni.md)を参照）。**EFA** は、互換性のある MPI/NCCL software が libfabric 経由で使用する OS-bypass device を提供します。**EFA device traffic は routable ではなく、VPC/AZ 境界を越えることはできません**。EFA-with-ENA interface の ENA device を通る通常の IP traffic は routable のままです。EFA-only interface には ENA device も IP addressing もありません。**NVLink** は、サポート対象の rack-scale NVLink domain を含む、サポート対象 system 内の GPU を接続します。EFA に対する固定の speedup を想定するのではなく、選択した hardware、collective operation、placement を測定してください。

**Optical transceiver** は、一般的な data-center networking の概念です。銅製 DAC (Direct Attach Copper) cable は短距離に適しており、optical module と fiber はその他の到達距離および bandwidth 要件をサポートします。QSFP と OSFP は module form factor を示すものであり、optical media を保証するものではありません。これは一般的な背景情報として扱ってください。特定の AWS workload の物理 cabling を確立するものではありません。

> 📎 NVLink/IMEX の topology-aware scheduling と GPU Pod placement の例は [AI/ML Infrastructure](../ai-ml/06-ai-infrastructure.md) にあります。EFA の VPC/AZ 境界制約と測定値は [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) にあります。

### 次世代プロトコルが Kubernetes にとって意味すること: HTTP/3、gRPC、QUIC

HTTP/3 (RFC 9114) とその QUIC transport (RFC 9000) のプロトコルメカニズムは、[Network Fundamentals Part 2](../basics/06-network-fundamentals-part2.md) と [Part 3](../basics/06-network-fundamentals-part3.md) で扱っています。ここでは、Kubernetes traffic distribution に実際に影響することのみを扱います。

- **gRPC と L4 load balancer:** gRPC は HTTP/2 connection 上で request を multiplex します。L4 balancer は通常、確立された TCP connection を選択済み endpoint に維持します。その endpoint が proxy の場合、さらに routing decision を行うことができます。Pod を追加しても既存の connection は再分散されません。RPC ごとの分散には、互換性のある L7 proxy または client-side policy が必要です。streaming RPC は 1 つの call のままです。その個々の message は独立して balance されません。
- **Gateway API の GRPCRoute:** Ingress には gRPC 固有の resource はありませんが、Gateway API は `GRPCRoute` によって Service/method-level routing を標準化します。support は実装によって異なります（header match の数、retry policy など）。controller 自体の documentation を確認してください。
- **HTTP/3/QUIC が実際にクラスター内のどこまで到達するか:** client と edge (CDN、load balancer) 間の HTTP/3 support は、クラスター内または Ingress の backend connection における HTTP/3 support とは別の問題です。多くの Ingress/Gateway 実装は、依然として backend に HTTP/1.1 または HTTP/2 を使用します。end-to-end HTTP/3 がサポートされるかどうかは、実装と version によって異なります。一般化せず、実際に使用する controller の documentation を確認してください。

## ネットワーキングのサブページ

このセクションでは、以下のトピックを詳しく扱います。

### [Linux ネットワーキング入門](beginner/README.md) {#beginner-course}

Linux またはネットワーキングが初めての場合は、[初級コース](beginner/README.md)から始めてください。その 8 つのレッスンでは、CLI、アドレッシング、DNS、SSH、ファイアウォール、モニタリング、そして総合演習を結び付けます。以下のパスでは、その基礎をプロトコル、カーネル、クラスター実装へと拡張します。

### [Linux ネットワーク診断演習](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

CNI 実装を学ぶ前に、[カーネルのソケットとパケットパスの概念](../kernel/02-network-stack.md)を観測結果に結び付けてください。[診断クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md)を使用して、解釈を確認してください。

### [VPC CNI](01-vpc-cni.md)
通常の Pod の VPC address を使用する EKS networking と、mode 固有の IPAM/policy 前提条件。

### [Cilium 詳細](cilium/README.md)
高性能な eBPF-based CNI solution。L7 NetworkPolicy、Service Mesh、observability (Hubble) などの高度な機能を提供します。

### [Calico 詳細](calico/README.md)
最も広く使用されている CNI の 1 つ。強力な NetworkPolicy、BGP support、enterprise feature。intro、architecture、networking mode、BGP 詳細、NetworkPolicy、eBPF、高度なトピック、EKS integration、operations guide を扱います。

### [VPC Lattice](02-vpc-lattice.md)
AWS managed application networking service。cross-VPC、cross-account の service-to-service communication。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Kubernetes Service と Ingress を AWS ELB (ALB/NLB) と統合します。

### [Gateway API](04-gateway-api.md)
次世代 Kubernetes ingress API。標準化された resource model と role-based configuration。

### [Pod Network Benchmark](06-pod-network-benchmark.md)
同一 node、同一 AZ、cross-AZ における EKS 上の Pod-to-pod RTT、HTTP latency、throughput と、DNS `ndots:5` query amplification を測定します。

## ネットワークトラブルシューティング

### 一般的な問題と解決策

#### Pod 間通信の失敗

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

指定した tool を持つ既存の Pod から診断を実行してください。クラスターにインストールされている CNI のみを照会してください。Auto Mode の system service はこれらの DaemonSet ではありません。DNS の成功、TCP reachability、application HTTP response は異なる確認です。ICMP は block されている場合や追加 privilege が必要な場合があるため、ping の失敗だけでは TCP service に到達できないことは証明されません。

#### Service に到達できない

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

現在の endpoint 診断には EndpointSlice を使用してください。Service selector、target port、endpoint readiness、address family、該当する policy を確認してください。Service forwarding を実際にその component が所有している場合にのみ kube-proxy log を調べてください。eBPF replacement または Auto Mode には、それぞれ独自の診断が必要です。

#### NetworkPolicy のデバッグ

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium command は DaemonSet reference で選択された 1 つの Agent を検査します。incident を追跡する場合は、影響を受けた node の Agent を選択してください。Calico native API installation は異なる API group を公開することがあるため、installation が提供する resource を確認してください。Kubernetes、Calico、AWS の extension policy は別個の resource であり、異なる precedence を持つ場合があります。

### ネットワークパフォーマンステスト

この制限付き TCP 演習では、Linux AMD64 および Arm64 image を含む publisher の固定された Netshoot v0.16 image index を使用します。その Dockerfile には `iperf3` が含まれています。TCP 5201 が許可されるテスト環境にこれらの Pod を作成してください。これは例示的な workload であり、測定済みの CNI 比較ではありません。

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

client は 1 時間 sleep し、この command は提供する traffic を 10 秒間 10 Mbit/s に制限します。これは選択した path をテストするものであり、最大 throughput をテストするものではありません。結果を解釈する前に、実際の Pod/node/AZ placement、resource limit、policy を記録してください。Windows node には Windows 固有の tool を選択してください。完了したら、作成した test resource のみを削除してください。

これらの standalone diagnostic Pod は connectivity test 用です。ネイティブ EKS NetworkPolicy enforcement test には、Deployment/Job 管理 Pod と文書化された Service/container-port 要件を使用してください。

## ベストプラクティス

### 1. IP Address Planning

- 十分に大きい CIDR block を設計する
- Pod network と Service network を分離する
- 将来の拡張を考慮して subnet を設計する

### 2. NetworkPolicy の適用

この例を使用する前に、分離された `networking-demo` namespace を作成してください。これはそこにあるすべての Pod を選択し、標準 Kubernetes NetworkPolicy semantics の下で ingress と egress の両方を分離します。必要な DNS と application flow には明示的な allow rule が必要です。enforcement には対応する policy engine が必要です。追加の cluster/admin policy API は precedence を変更でき、この 1 つの manifest は完全な zero-trust architecture ではありません。

- default deny policy を適用する (Zero Trust)
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

- 適切な CNI を選択する (workload に合わせる)
- MTU の最適化
- Kernel parameter のチューニング

### 4. Security Hardening

- サポート対象の transport encryption を選択し、対象となる traffic を検証する。
- 必要に応じて workload/application identity と mTLS を構成し、これらを DNS/IP-based allowlist とは分離する。
- policy、certificate、access-control の変更を定期的にレビューする。

### 5. Observability の確保

- ネットワークメトリクスを収集する
- flow log を有効にする
- distributed tracing を実装する

## 次のステップ

[初級コース](beginner/README.md)の後は、[カーネルネットワーキングスタック](../kernel/02-network-stack.md)、次に [Linux ネットワーク診断演習](07-linux-network-diagnostics.md)とその[クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md)を続けてください。[学習パス](#learning-path)は、以下の CNI と AWS のトピックに進む前に、これらの基礎をコンテナと Service に結び付けます。

1. [VPC CNI](01-vpc-cni.md) - デフォルト EKS CNI
2. [Cilium 詳細](cilium/README.md) - eBPF-based networking
3. [Calico 詳細](calico/README.md) - Routing、policy、dataplane
4. [VPC Lattice](02-vpc-lattice.md) - AWS managed networking
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB integration
6. [Gateway API](04-gateway-api.md) - 次世代 ingress
7. [Cross-Org VPC Connectivity](05-cross-org-vpc-connectivity.md) - AWS Organizations をまたぐ VPC 接続 (field-verified)
8. [Pod Network Benchmark](06-pod-network-benchmark.md) - node/AZ 境界ごとの測定済み latency と throughput

---

## 参考資料

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
