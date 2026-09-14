# Kubernetes ネットワーキング

> **最終更新**: September 14, 2026. 機能の参照には Cilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9、AWS VPC CNI 1.23.0 が含まれます。インストール前に各製品の Kubernetes/プラットフォーム対応マトリクスを確認してください。これらは共同でテストされたクラスター構成ではありません。

## 概要

Kubernetes ネットワーキングは、コンテナ化されたアプリケーション間の通信を可能にする中核のインフラストラクチャ層です。このセクションでは、基本的な Kubernetes ネットワーキングの概念から、高度な CNI (Container Network Interface) ソリューション、AWS EKS 環境におけるネットワーキングパターンまでを扱います。

## 学習パス {#learning-path}

プロトコルの概念から観測へと積み上げ、それらをコンテナ、クラスター、クラウドの責任範囲に結び付けます。前提条件を使用して開始点を選択し、続行前に到達目標で理解を確認してください。

| 段階 | 役割 | 前提条件 | 到達目標 | 読む / 実践する |
|---|---|---|---|---|
| プロトコル、アドレッシング、HTTP | 用語を確立する | 基本的なコマンドラインの使用 | リクエストを追跡し、アドレッシング、トランスポート、アプリケーションの動作を区別する | ネットワークの基礎 [Part 1](../basics/06-network-fundamentals-part1.md)、[Part 2](../basics/06-network-fundamentals-part2.md)、[Part 3](../basics/06-network-fundamentals-part3.md)、[Part 4](../basics/06-network-fundamentals-part4.md) |
| Linux ソケット、VFS、パケットパス | API をカーネルに結び付ける | TCP/IP の基礎 | FD、ソケットバッファ、ウィンドウ、キューを区別する | [カーネルネットワーキングスタック](../kernel/02-network-stack.md) |
| Linux ネットワーク診断 | 証拠を用いて仮説を検証する | ソケットとパケットパスの概念 | ソケット、パケット、アプリケーションの観測結果を関連付ける | [診断の実践](07-linux-network-diagnostics.md) · [クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker とコンテナネットワーキング | Namespace の境界を特定する | Linux パケットパスと基本診断 | bridge ネットワーキング、公開ポート、コンテナ名解決を説明する | [コンテナ技術](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | クラスター抽象化を対応付ける | コンテナネットワーキング | 名前を Service 経由でそのエンドポイントまで追跡し、Ingress の役割を特定する | [Services とネットワーキング](../core/03-services-networking.md) · [ラボ](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、ポリシー | 実装の責任範囲を比較する | Pod と Service のパス | パケット転送、ポリシー適用、可観測性を区別する | [eBPF の基礎](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS ネットワーク境界とパフォーマンス | モデルをクラウドパスに適用する | CNI の概念と計測スキル | VPC、node、AZ の境界を特定し、計測値を文脈に沿って解釈する | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) · [Pod ネットワークベンチマーク](06-pod-network-benchmark.md) |

## Kubernetes ネットワーキングモデル

現在の Kubernetes モデルは、**意図的なネットワークセグメンテーションを前提として**、Pod がアドレス変換やプロキシなしに node 間で直接通信できる Pod ネットワークを提供します。kubelet などの node Agent は、自身の node 上にある Pod に到達できなければなりません。ネットワークポリシー、ルーティング、アプリケーションリスナーによって、特定の接続が成功するかどうかは引き続き決まります。

通常の Pod には独自の network namespace とクラスター全体で有効なアドレスがあり、1 つの Pod 内のコンテナはその namespace と localhost を共有します。host-network Pod は node ネットワークを共有し、dual-stack または multi-network の構成ではより正確なアドレス処理が必要です。Pod を再作成すると異なる IP が割り当てられる場合がありますが、同じ Pod 内のコンテナを再起動しても、必ずしもそのネットワークサンドボックスは再作成されません。

| コンポーネント | 役割 |
|---|---|
| Pod ネットワーク | ワークロード network namespace 間のアドレッシングと接続性 |
| Service/ディスカバリー | 変動するエンドポイントに対する安定したサービス名または仮想アドレス |
| Ingress/Gateway 実装 | 構成された外部エントリとアプリケーションルーティング |
| ネットワークポリシーエンジン | 選択した実装でサポートされるポリシーを適用する |

これらの役割は必須の直列パケットパスを構成するものではありません。Service の変換、L7 プロキシ、ワークロードポリシーにより、特定のリクエストがネットワークを通過する方法は変わる場合があります。

### Pod ネットワーキング

Pod ネットワーキングは、Pod 通信のためのアドレッシングとルートを提供します。以下の図は通常の IPv4 Pod を示しています。その接続は、適用されるポリシーとネットワーク制御が許可していることを前提としています。

![構成されたポリシーとルーティングに従う接続性を伴う、2 つの node にまたがる例示的な直接 IPv4 Pod パス。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

アドレスは例示的な通常の Pod アドレスです。意図的な分離、host-network、multi-network の構成には、それぞれ固有の解釈が必要です。

#### Pod ネットワーキング実装方式

| 方式 | 説明 | CNI の例 |
|--------|-------------|-------------|
| **Overlay Network** | 既存ネットワーク上でトラフィックをカプセル化する | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **Native Routing** | その Overlay のカプセル化なしに基盤ネットワークのルートを使用する | AWS VPC CNI、Calico routing/BGP、Cilium native routing |
| **Conditional Encapsulation** | 構成されたトポロジーに応じて直接パスまたはカプセル化を使用する | 前提条件が異なる、サポートされる Calico/Flannel/Cilium モード |

### Service ネットワーキング

Service は、通常は Pod である論理的なエンドポイント集合と、その到達方法を記述します。ClusterIP はデフォルトで安定した仮想 IP を提供し、headless Service はその仮想 IP を省略し、ExternalName は DNS CNAME マッピングを使用します。Service は Pod selector を持たずに管理されるエンドポイントを持つこともできます。

![ClusterIP、NodePort、LoadBalancer、ExternalName Service の代表的なエントリメカニズム。DNS マッピングはパケット転送と区別されています。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

これらは代表的な公開メカニズムであり、セキュリティ保証ではありません。NodePort の範囲とアクセス可能な node アドレスは構成可能であり、LoadBalancer は内部向けにできます。ExternalName は DNS エイリアスを返し、転送プロキシを作成しません。

#### Service タイプの特性

表示された target port でリッスンする、`app: my-app` が一致する Pod を `default` に作成してください。NodePort のデフォルト割り当て範囲は 30000–32767 であり、構成可能です。外部からの到達性は引き続きアドレス、ルート、アクセス制御に依存します。

LoadBalancer の例では、EC2 instance target と割り当てられた NodePort を持つ **AWS Load Balancer Controller** を明示的に選択しています。最初にその controller と IAM/subnet の前提条件をインストール・構成してください。EKS Auto Mode は別の controller/class を使用します。ここで port 443 は TCP port を選択するだけです。TLS は backend が 8443 で提供するか、load balancer 上で別途構成する必要があります。

これらの port マッピングは、一般的な Kubernetes Service API を示しています。AWS は現在、追加の native EKS ネットワークポリシー要件を文書化しています。Service port はコンテナ port と一致する必要があり、`metadata.ownerReferences` を持つ controller 管理 Pod は信頼性の高い適用を提供します。そのポリシー実装をテストする前に、例をこれらの要件に合わせてください。

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

Ingress リソースには controller とそのデータプレーンが必要です。この HTTP の例では、`spec.ingressClassName: alb` と IP target を使用する AWS LBC を使用しています。参照されている `api-v1`、`api-v2`、`web-frontend` の Service は `default` に存在し、port 80 を公開し、準備完了状態の VPC ルーティング可能な Pod エンドポイントを持つ必要があります。必要に応じて HTTPS/証明書を別途構成してください。インストールと target の前提条件については [LBC ガイド](03-aws-lb-controller.md) を参照してください。

Ingress は、HTTP/HTTPS トラフィックを内部クラスター Service にルーティングするルールを定義します。

![Service backend と Pod への論理的な Ingress host/path ルーティング。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

このボックスは Ingress データプレーン機能を表しています。AWS LBC は ALB をプログラムします。アプリケーショントラフィックは controller の reconciliation プロセスを通過しません。target モードに応じて、データプレーンは Pod IP または NodePort に到達でき、文字どおりの追加ホップとして Service 仮想 IP を経由するわけではありません。

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

CNI は、runtime がコンテナネットワークを構成するためのインターフェースを標準化します。現在の Kubernetes では、kubelet は CRI を通じて Pod-sandbox 操作を要求し、**container runtime が CNI を管理します**。kubelet による旧来の直接 CNI 管理フラグは Kubernetes 1.24 で削除されました。

### Runtime と Plugin の責任範囲

| 実行主体 | 責任 |
|---|---|
| kubelet | container runtime interface を通じて sandbox の作成/削除を要求する |
| Container runtime | ネットワーク構成を選択し、CNI plugin chain を呼び出す |
| CNI plugin | 構成を受け取り、ADD/DEL およびその他のサポートされる操作を実行し、結果を返す |
| IPAM 実装 | アドレスを割り当て/解放する。委譲された plugin またはプロバイダー固有 Agent の一部である場合がある |
| オプションの node Agent | プロバイダー固有のルート、ポリシー、IP pool、データパス状態を維持する |

runtime は CNI インターフェースを通じて plugin に構成を渡します。すべての plugin に対して、別の長期実行 Agent や IPAM binary が必須ではありません。インターフェースタイプも異なります。veth pair は一般的ですが、唯一の実装ではありません。

## CNI の比較

| プロジェクト / 範囲 | ネットワーキングとポリシー | 区別すべき機能と制限 |
|---|---|---|
| **Cilium 1.20.1** | eBPF ネットワーキング、該当する L7 機能用の Envoy、Cilium ネットワークポリシーと Hubble | AMD64/Arm64 の要件を持つ Linux worker dataplane。Windows CLI の利用可能性は Windows CNI サポートを意味しません。WireGuard/IPsec と Beta ztunnel mTLS には異なる範囲があります。 |
| **Calico Open Source 3.32** | ルーティング/カプセル化の選択肢、iptables、nftables、eBPF のオプション、順序付きポリシー tier と host/workload ポリシー | Windows には Linux eBPF や WireGuard dataplane がないことを含む、別の制限があります。Whisker/Goldmane の flow observability は Tech Preview として利用可能です。有償機能については edition matrix を参照してください。 |
| **Flannel 0.28.9** | Host subnet の割り当てと node 間トランスポート、VXLAN、host-gw、その他の backend | `flanneld` 自体は NetworkPolicy を適用しません。chart のオプション `netpol.enabled` は SIGs policy controller をデプロイします。WireGuard は文書化された backend であり、IPsec は実験的です。Windows VXLAN には固有の設定/制限があります。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPC アドレスの割り当てと EC2 ENI/prefix、サポートされる Linux EC2 node における EKS standard および Admin ネットワークポリシー機能 | EKS Auto Mode は、追加の DNS ポリシー機能を持つマネージドネットワーキング実装です。Windows、Fargate、custom networking、prefix delegation、multi-NIC サポートには別個の条件があります。 |
| **Original Weave Net project** | 歴史的な Overlay ネットワーキング実装 | 元の `weaveworks/weave` repository はアーカイブされています。新規クラスターに対するアクティブでサポートされたデフォルトとして説明しないでください。 |

### ポリシー、暗号化、可観測性

- Cilium は該当する L7 コンポーネントを通じた HTTP/DNS 対応ポリシーと、クラスター全体/host ポリシーを提供します。その deny/allow セマンティクスは Calico の順序付き Tier API とは異なります。
- Calico Open Source には階層型ポリシー tier と host ポリシーが含まれます。現在の製品マトリクスでは、application-layer ポリシー、DNS/FQDN ポリシー、Cluster Mesh は Cloud/Enterprise に割り当てられています。これらを open-source edition に暗黙に帰属させてはなりません。Calico が文書化している転送中の暗号化では WireGuard を使用します。
- Amazon EKS は、Auto Mode およびサポートされる EC2/VPC-CNI インストールに対し、`ClusterNetworkPolicy` Admin/Baseline 制御を提供します。AWS が説明する DNS/FQDN `ApplicationNetworkPolicy` 機能は **Auto Mode** 向けです。その名前は、現在の HTTP method/body 検査を意味するものではありません。
- Flannel のオプション policy controller には独自の要件があります。ネットワーキング backend を選択するだけでは適用は有効になりません。
- node 間暗号化、認証済みワークロードアイデンティティ、アプリケーション mTLS は異なる制御です。ネットワークフローの可視性も、アプリケーショントレーシングやプロセス/ファイルの適用とは異なります。

### ルーティングとパフォーマンス

Calico と Cilium は BGP を使用してルートを広告できますが、それ自体で multi-cluster Service discovery、ポリシー同期、暗号化を提供するわけではありません。Flannel host-gw は直接ルートを使用し、適切な layer-2 接続性を必要とします。Overlay ではカプセル化と MTU を考慮する必要がありますが、CNI 名から普遍的なパフォーマンス順位を推論することはできません。

以前の 100/98/95/85/80/75 パーセントの throughput 指標には、再現可能なワークロード、バージョン、計測ソースがありませんでした。比較可能なハードウェア、kernel、packet/request サイズ、並行性、暗号化/ポリシー設定、throughput、loss、tail latency を使用してください。別の [Pod ベンチマーク](06-pod-network-benchmark.md) には、独自の履歴的な環境と計測値が残されています。

## CNI 選択ガイド

まず必要なルーティング、ポリシー、operating-system、サポートモデルを選択し、その組み合わせをテストしてください。

| ニーズ | 評価パス |
|---|---|
| 標準 EKS VPC アドレッシングとサポートされるネットワークポリシー | 2 つ目のポリシーエンジンを追加する前に、AWS VPC CNI/EKS 機能を評価する。 |
| 順序付きポリシー tier、host ポリシー、またはインフラストラクチャ BGP | 関連する Calico edition/dataplane とルーティングの前提条件を評価する。 |
| Cilium ポリシー、Hubble、または選択した mesh 機能 | Linux/kernel/プラットフォーム互換性と [Cilium mesh ガイド](../service-mesh/cilium-service-mesh/README.md) を確認する。Envoy は該当する L7 パスの一部であり続けます。 |
| 機能セットが限定された小規模ネットワーク | 実際の要件に照らして Flannel の backend とオプション policy controller を評価する。 |
| プロセス、syscall、またはファイルの適用 | ネットワークポリシーとは別に、Tetragon などの runtime-security コンポーネントを評価する。 |

### EKS Managed Add-on 構成

以下は **構成ペイロード**の例であり、同じワークロードに Calico と VPC CNI policy engine の両方をインストールする指示ではありません。

```json
{
  "enableNetworkPolicy": "true"
}
```

文字列の `"true"` は、この設定に対して文書化された型です。既存の Kubernetes バージョンと互換性のある EKS add-on build を選択し、その build の構成 schema を確認してください。

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

upstream の 1.23.0 release number と EKS の `eksbuild` version は異なる識別子です。意図した managed add-on 構成と変更をマージしてください。`latest` を無造作に選択したり、無関係な値を置き換えたりしないでください。サードパーティのポリシー実装からの移行には、既存の適用状態の削除と、テスト済みの node/ワークロード移行計画も必要です。

## EKS ネットワーキングの基礎

### EKS デフォルトネットワーキングアーキテクチャ

| 場所 / コンポーネント | 責任 |
|---|---|
| EKS 管理 VPC | AWS は Availability Zone をまたいでマネージド Kubernetes control plane を実行します。 |
| 顧客クラスター VPC | Worker ネットワーキング、選択された subnet、EKS 管理の cross-account ENI は、control plane への構成済みパスを提供します。 |
| 選択された顧客 VPC subnet 内の ALB/NLB | 選択されたパブリックまたは内部アプリケーションエントリポイントを提供します。internet gateway/NAT gateway は、そのルーティング構成の代替ではありません。 |
| NAT gateway または private service endpoint | ワークロード設計が必要とする特定の outbound パスを提供します。 |

以前の図は control plane を顧客 VPC 内に、load balancer をその外部に配置していました。現在はこれらの所有権境界に置き換えられています。

### Compute Mode ごとの DNS とネットワーキング

| Compute mode | DNS / コンポーネント配置 |
|---|---|
| Standard EC2 node | 通常は構成された CoreDNS Deployment とインストール済みネットワーキングコンポーネントを使用します。置き換える場合は独自のサポートされる構成が必要です。 |
| Pure EKS Auto Mode | CoreDNS、VPC CNI、kube-proxy の機能は、管理された node systemd service として実行されます。これらの node には CoreDNS Deployment/add-on は不要です。 |
| Auto Mode と非 Auto node の混在 | 非 Auto node 向けに CoreDNS Deployment を保持してください。別の node の Auto Mode DNS service は使用できません。 |

Auto Mode の最初の DNS resolver は node-local です。upstream forwarding と control-plane 通信には引き続きネットワークアクセスが必要になる場合があります。これは DNS 関連のすべての packet が node 内に留まることを保証するものではありません。AWS は Auto Mode 向けの Admin と DNS ポリシーの両方を文書化していますが、standard EC2 VPC-CNI の Admin ポリシーには独自のバージョン/有効化要件があります。

### VPC CNI の仕組み

AWS VPC CNI は、選択した IPAM モードを使用して通常の Pod に VPC ルーティング可能なアドレスを与えます。secondary IPv4 address、delegated prefix、branch ENI、multi-NIC の構成はそれぞれ異なります。host-network Pod は node ネットワークを共有します。

![オプションの warm interface を含む、EC2 ENI から Pod への例示的な secondary-IPv4 割り当て。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

これは secondary-IP モードのみを示しています。warm ENI は構成可能な割り当て戦略であり、すべての node が常にちょうど 1 つを予約する必要があるわけではありません。prefix delegation、custom networking、branch ENI には異なる割り当てルールがあります。

#### ENI と IP の上限

| Instance Type | Max ENI | ENI あたりの IPv4 slot | 旧来の secondary-IP bootstrap 値 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

これらの値は、VPC CNI 1.23.0 の instance limit と旧来の max-Pods table に照らして検証されています。履歴的な計算式は `ENIs × (IPv4 slots per ENI − 1) + 2` です。これは現在の普遍的な推奨事項ではありません。prefix delegation、custom networking、branch ENI、複数の network card はアドレス容量を変更します。Kubernetes scheduling は kubelet `maxPods` とリソースによっても制限されます。EKS managed node group は、30 vCPU 未満の instance では `maxPods` を 110、それ以外では 250 に制限します。利用可能な IP 数だけでその上限を超えることはできません。

### EKS ネットワーキングの考慮事項

#### IP アドレス管理

**Linux VPC CNI** では、選択した add-on/Helm/DaemonSet 管理メカニズムを通じて文書化された環境変数を構成してください。以下は EKS add-on の構成フラグメントです。`enable-prefix-delegation` を持つ古い `amazon-vpc-cni` ConfigMap は、この方法で Linux IPAMD を構成しません。変更を適用するときは、他の意図した add-on 値を保持してください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

代わりに、合計割り当て下限と空き IP target を調整できます。`MINIMUM_IP_TARGET` または `WARM_IP_TARGET` のいずれかを構成すると、`WARM_PREFIX_TARGET` より優先されます。これらは 4 つの独立して加算される target ではなく、代替のポリシーです。割り当ては引き続き prefix サイズ単位で行われます。Nitro サポート、IPv4 用の連続した `/28` 空間、適切な kubelet Pod 上限は別の前提条件です。

Windows の prefix 割り当ては別の構成パスです。AWS は `amazon-vpc-cni` ConfigMap で `enable-windows-prefix-delegation` とその warm-target key を文書化しています。Linux の環境変数手順を変更せずに Windows にコピーしないでください。

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

これらの IPv4 の例には、意図した AZ と VPC に存在する実際の subnet/security-group ID が必要です。custom networking を有効にし、各 node の ENIConfig をその zone label を通じて選択します。明示的な ENIConfig node annotation はその label より優先されます。以下の例の名前は両言語で同じ region を使用しています。実際の node zone に置き換えてください。ENIConfig object をインストールするだけでは custom networking は有効になりません。

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

以下の項目は、この概要のほかの場所で簡潔に言及されています。完全なセットアップ手順と計測値はリンク先の詳細ページにあります。このセクションでは、これらの要素が layer ごとにどう異なるか、そして各要素がどこに適合するかを整理します。

### L2–L7 と Router と Load Balancer の違い

「Router」と「load balancer」は同じ文に登場することが多いですが、答える問いは異なります。router は（一般に）単一の宛先への 1 つのパスを選び、load balancer は分散アルゴリズムを使用して複数の同等な候補から 1 つの target を選びます。

| Layer | デバイス/機能 | 判断基準 | Kubernetes/AWS との対応 |
|---|---|---|---|
| L2 (link) | Switch、bridge | 宛先 MAC address | CNI が作成する veth pair と Linux bridge、ENI が公開する virtual NIC |
| L3 (network) | Router または透過的な appliance 挿入 | ルーティングには宛先 IP、appliance 選択には flow identity | VPC の暗黙的な router、TGW、GWLB は appliance 向けに IP packet をカプセル化 |
| L4 (transport) | L4 load balancer | 接続/flow identity、一般的には 5-tuple | NLB、kube-proxy (iptables、IPVS、nftables)、個別の eBPF Service 実装 |
| L7 (application) | L7 load balancer/reverse proxy | リクエストごとの host、path、header、プロトコル認識 | ALB、Ingress/Gateway API 実装、service-mesh sidecar (Envoy) |

重要な違いは **分散の単位**です。L4 load balancer は通常、TCP 接続または追跡された UDP flow に対して target を選択します。L7 proxy は、接続を共有するリクエストを含め、サポートされるアプリケーションリクエストごとに target を選択できます。GWLB はアプリケーションリクエストを解析するのではなく、カプセル化された IP flow を security appliance に分散します。flow stickiness は、構成された timeout、health、failover の動作に依存します。flow が決して再割り当てまたは中断されないことを保証するものではありません。

> 📎 L2/L3 のプロトコルレベルの定義は [ネットワークの基礎 Part 1](../basics/06-network-fundamentals-part1.md) にあります。ALB/NLB target type と実際の構成は [AWS Load Balancer Controller](03-aws-lb-controller.md) にあります。

### Cross-Account/VPC 接続: TGW、VPC Peering、GWLB、PrivateLink、Lattice

これら 5 つの接続オプションは、layer とトラフィックモデルが異なります。TGW RAM 共有、VPC Peering、PrivateLink、TGW Peering、VPC Lattice をまたぐ計測 latency は [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) にあります。このセクションでは、その比較 table にはない GWLB を追加し、5 つすべてを layer 別に再構成します。

| 接続性 | Layer/モデル | 特性 |
|---|---|---|
| VPC Peering | L3、双方向 IP ルーティング | 推移的ではない。重複する CIDR 間では構成できない |
| Transit Gateway (TGW) | L3、hub-and-spoke IP ルーティング | 1 つ以上の TGW route table にまたがる attachment association と propagation を使用。RAM を介して cross-account 共有 |
| Gateway Load Balancer (GWLB) | L3、透過的な appliance 挿入 | 元の packet を GENEVE (UDP 6081) にカプセル化。VPC endpoint service モデルが consumer トラフィックを provider の appliance fleet に接続する |
| PrivateLink | Private endpoint 接続性 | NLB backed endpoint service は 1 つのモデルであり、resource endpoint も存在する。consumer/provider CIDR は重複可能 |
| VPC Lattice | アプリケーションおよびリソースネットワーキング | HTTP/HTTPS Service は L7 ルーティングとオプションの IAM authorization をサポート。TLS passthrough と resource configuration には異なる機能がある |

GWLB は、Gateway Load Balancer endpoint を経由する IP パスに firewall や IDS/IPS などの inspection appliance を挿入します。デフォルトの flow stickiness は 5 つの field を使用します。サポートされる構成では、代わりに 2 つまたは 3 つを使用できます。forward および return route、appliance health、encapsulation MTU、NACL、実際の workload/appliance の security group を検証してください。GWLB 自体には ALB 形式の security group はなく、flow stickiness は障害テストに代わるものではありません。

> 📎 完全な EKS/VPC Lattice 統合 (Gateway API Controller、IAM authorization、ルーティング) は [VPC Lattice](02-vpc-lattice.md) にあります。

### DNS Resolver と Route Table の実際の動作

**DNS resolver:** AmazonProvidedDNS **は Route 53 Resolver です**。そのアドレスには、プライマリ VPC IPv4 network address に 2 を加えたもの (`10.0.0.0/16` では `10.0.0.2`) と `169.254.169.253` が含まれます。Resolver rule に従い、関連付けられた private zone と public name を解決します。CoreDNS は通常、構成された Kubernetes cluster domain、多くの場合 `cluster.local` を提供します。`kube-dns` はその Service 名であり、namespace や DNS zone ではありません。外部 forwarding は Corefile と DNS Pod から見える resolver file に従います。node の resolver file が変更されずに使用されると仮定するのではなく、これらの設定を確認してください。Resolver endpoint 設計では、inbound endpoint がオンプレミス query を受け入れ、outbound endpoint と関連 rule が選択された VPC query をオンプレミス DNS に転送します。Auto Mode の node-local resolver は upstream 依存関係をなくしません。

**Route table:** VPC の route 評価では、通常 longest-prefix matching を使用します。AWS では、`local` route の target の置き換えと、appliance routing 用のサポートされたより具体的な subnet route の追加が可能です。`local` が無条件に最も具体的な route であるわけではありません。同一の宛先では、static VPC route が virtual private gateway から propagated された route より優先されます。TGW を target にする VPC route は static です。TGW 内の propagation は、その個別の route table に属します。無効な target はトラフィックを破棄する `blackhole` entry を残す場合があるため、宛先だけでなく route 状態も確認してください。明示的な route-table association がない subnet は VPC の main route table を使用します。

> 📎 TGW/Peering の route priority と static-route 構成例は、[組織間 VPC 接続の運用上の知見](05-cross-org-vpc-connectivity.md#operational-findings) にあります。

### Kernel Data Plane: iptables、IPVS、eBPF、Packet Filtering

Linux Service forwarding とネットワークポリシー適用は、異なるメカニズムを使用できます。Netfilter は iptables と nftables が使用する packet-path hook を提供します。eBPF 実装は XDP、tc、socket hook に attach し、そこで Service 選択を実行できます。これは、eBPF 有効クラスターのすべての packet が Netfilter や connection tracking を bypass することを意味しません。パスは CNI、kernel、ルーティング、機能構成に依存します。

| 実装 | 配置場所 | 特性 |
|---|---|---|
| iptables | netfilter hook 上の順次 rule chain | 評価時間は rule 数に比例して増加 (O(n))。kube-proxy の長年のデフォルトモード |
| IPVS | Kernel native L4 load balancer、netfilter extension | hash ベースの lookup (ほぼ O(1))。Kubernetes 1.35 から kube-proxy モードとして非推奨 |
| nftables | iptables の後継となる netfilter framework | Kubernetes 1.33 以降で kube-proxy の stable モード。最初に kernel/CNI 互換性を確認 |
| eBPF (例: Cilium) | 構成された XDP、tc、socket hook | kube-proxy の Service 処理を置き換え可能。これは別個の実装であり、パス固有の Netfilter/conntrack 動作を持つ |

実装の切り替えにより、kernel rule と active connection が残る場合があります。distribution/CNI の移行手順に従い、必要に応じて workload を drain し、cleanup に必要な node restart を計画してください。kube-proxy を eBPF ベース CNI に置き換えるには、実装が同じ Service traffic を競合して処理しないよう、サポートされる cutover 順序も必要です。

> 📎 IPVS の非推奨化タイムラインと nftables の stable への移行は [Kubernetes 入門](../basics/04-kubernetes-introduction.md) にあります。Cilium の eBPF kube-proxy 置換は [Cilium eBPF](cilium/02-ebpf.md) に、Calico の eBPF data plane とその移行手順は [Calico eBPF](calico/06-ebpf-dataplane.md) にあります。

### Compute-Intensive Networking: ENI、EFA、NVLink、Optical Transceiver

ENI、EFA、NVLink は異なるパスを提供します。**ENI** は 1 つの Availability Zone 内の EC2 instance にアタッチされる仮想ネットワークインターフェースです。その通常の IP traffic は、ルーティングとポリシーが許可すれば他の AZ や接続された VPC に到達できます ([VPC CNI](01-vpc-cni.md) を参照)。**EFA** は、対応する MPI/NCCL software が libfabric 経由で使用する OS-bypass device を提供します。**EFA device traffic はルーティング不可で、VPC/AZ 境界を越えることはできません**。EFA-with-ENA interface の ENA device を経由する通常の IP traffic はルーティング可能なままです。EFA-only interface には ENA device も IP addressing もありません。**NVLink** は、サポートされる rack-scale NVLink domain を含む、サポート対象 system 内の GPU を接続します。EFA に対する一定の高速化を前提とせず、選択した hardware、collective operation、placement を計測してください。

**Optical transceiver** は一般的な data-center networking の概念です。銅線 DAC (Direct Attach Copper) cable は短距離に適しており、optical module と fiber は別の到達距離と bandwidth 要件をサポートします。QSFP と OSFP は module form factor を表すものであり、optical media を保証するものではありません。これは一般的な背景情報として扱ってください。特定の AWS workload の物理 cabling を立証するものではありません。

> 📎 NVLink/IMEX の topology-aware scheduling と GPU Pod placement の例は [AI/ML インフラストラクチャ](../ai-ml/06-ai-infrastructure.md) にあります。EFA の VPC/AZ 境界制約と計測値は [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) にあります。

### 次世代プロトコルが Kubernetes にもたらす意味: HTTP/3、gRPC、QUIC

HTTP/3 (RFC 9114) とその QUIC transport (RFC 9000) のプロトコルメカニズムは、[ネットワークの基礎 Part 2](../basics/06-network-fundamentals-part2.md) と [Part 3](../basics/06-network-fundamentals-part3.md) で扱います。ここでは、Kubernetes のトラフィック分散に実際に影響する点だけを扱います。

- **gRPC と L4 load balancer:** gRPC は HTTP/2 connection 上でリクエストを多重化します。L4 balancer は通常、確立済み TCP connection を選択した endpoint に保持します。その endpoint が proxy であれば、さらにルーティング判断を行えます。Pod を追加するだけでは既存 connection は再分散されません。RPC 単位の分散には、互換性のある L7 proxy または client-side policy が必要です。streaming RPC は 1 回の call のままです。その個々の message が独立して balance されることはありません。
- **Gateway API の GRPCRoute:** Ingress には gRPC 固有の resource はありませんが、Gateway API は `GRPCRoute` によって service/method レベルのルーティングを標準化します。サポートは実装によって異なります (header match の数、retry policy など)。そのため、controller 自身の documentation を確認してください。
- **HTTP/3/QUIC が実際にクラスター内まで到達する範囲:** client と edge (CDN、load balancer) 間の HTTP/3 サポートは、クラスター内または Ingress の backend connection における HTTP/3 サポートとは別の問題です。多くの Ingress/Gateway 実装は依然として backend に HTTP/1.1 または HTTP/2 を使用しており、end-to-end HTTP/3 がサポートされるかは実装と version によって異なります。一般化せず、実際に使用している controller の documentation を確認してください。

## ネットワーキングのサブページ

このセクションでは、次のトピックを詳しく扱います。

### [Linux ネットワーク診断の実践](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

CNI 実装を学ぶ前に、[kernel の socket と packet-path の概念](../kernel/02-network-stack.md) を観測結果に結び付けてください。[診断クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md) を使用して解釈を確認してください。

### [VPC CNI](01-vpc-cni.md)
通常の Pod 向けの VPC address と、モード固有の IPAM/ポリシー前提条件を備えた EKS ネットワーキング。

### [Cilium 詳細解説](cilium/README.md)
高パフォーマンスな eBPF ベース CNI ソリューション。L7 Network Policy、Service Mesh、可観測性 (Hubble) などの高度な機能を提供します。

### [Calico 詳細解説](calico/README.md)
最も広く使用されている CNI の 1 つです。強力な Network Policy、BGP サポート、enterprise 機能を提供します。導入、アーキテクチャ、ネットワーキングモード、BGP 詳細解説、Network Policy、eBPF、高度なトピック、EKS 統合、運用ガイドを扱います。

### [VPC Lattice](02-vpc-lattice.md)
AWS マネージドアプリケーションネットワーキングサービス。VPC 間、account 間の service-to-service 通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Kubernetes Service と Ingress を AWS ELB (ALB/NLB) と統合します。

### [Gateway API](04-gateway-api.md)
次世代 Kubernetes ingress API。標準化された resource model と role-based configuration。

### [Pod ネットワークベンチマーク](06-pod-network-benchmark.md)
同一 node、同一 AZ、AZ 間における EKS 上の Pod 間 RTT、HTTP latency、throughput と、DNS `ndots:5` query amplification の計測値。

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

指定された tool を持つ既存の Pod から診断を実行してください。クラスターにインストールされている CNI だけを query してください。Auto Mode の system service はこれらの DaemonSet ではありません。DNS の成功、TCP の到達性、アプリケーション HTTP response は異なる確認項目です。ICMP は block されているか追加の権限が必要な場合があるため、ping の失敗だけで TCP Service に到達不能であることは証明されません。

#### Service に到達できない

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

現在の endpoint 診断には EndpointSlice を使用してください。Service selector、target port、endpoint readiness、address family、適用されるポリシーを確認してください。Service forwarding を実際にそのコンポーネントが所有している場合のみ kube-proxy log を確認してください。eBPF 置換または Auto Mode には独自の診断が必要です。

#### ネットワークポリシーのデバッグ

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium command は DaemonSet reference によって選択された 1 つの Agent を検査します。incident を追跡する場合は、影響を受けた node の Agent を選択してください。Calico native API のインストールでは異なる API group を公開する場合があるため、そのインストールで提供されている resource を確認してください。Kubernetes、Calico、AWS extension のポリシーは別個の resource であり、優先順位が異なる場合があります。

### ネットワークパフォーマンステスト

この制限付き TCP 演習では、publisher が固定した Netshoot v0.16 image index を使用します。この index には Linux AMD64 と Arm64 の image が含まれ、Dockerfile には `iperf3` が含まれます。TCP 5201 が許可されたテスト環境でこれらの Pod を作成してください。これは例示的なワークロードであり、計測済みの CNI 比較ではありません。

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

client は 1 時間 sleep し、command は提示トラフィックを 10 秒間 10 Mbit/s に制限します。これは選択されたパスをテストするものであり、最大 throughput をテストするものではありません。結果を解釈する前に、実際の Pod/node/AZ placement、resource limit、ポリシーを記録してください。Windows node には Windows 固有の tool を選択してください。完了時には、自分で作成したテスト resource だけを削除してください。

これらの standalone diagnostic Pod は接続性テスト用です。native EKS ネットワークポリシー適用のテストでは、Deployment/Job 管理 Pod と文書化された Service/container-port 要件を使用してください。

## ベストプラクティス

### 1. IP アドレス計画

- 十分に大きい CIDR block を設計する
- Pod ネットワークと Service ネットワークを分離する
- 将来の拡張を考慮して subnet を設計する

### 2. ネットワークポリシーを適用する

この例を使用する前に、分離された `networking-demo` namespace を作成してください。これはその namespace 内のすべての Pod を選択し、標準の Kubernetes NetworkPolicy セマンティクスに基づき ingress と egress の両方を分離します。必要な DNS とアプリケーションフローには明示的な allow rule が必要です。適用には対応する policy engine が必要です。追加の cluster/admin ポリシー API は優先順位を変更する可能性があり、この 1 つの manifest は完全な zero-trust アーキテクチャではありません。

- デフォルト deny ポリシーを適用する (Zero Trust)
- 必要なトラフィックのみを明示的に許可する
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

### 3. パフォーマンスの最適化

- 適切な CNI を選択する (ワークロードに適合)
- MTU の最適化
- Kernel parameter の調整

### 4. セキュリティ強化

- サポートされる転送時暗号化を選択し、それが対象とするトラフィックを検証する。
- 必要に応じて workload/application identity と mTLS を構成する。これらは DNS/IP ベースの allowlist と分けて扱う。
- ポリシー、証明書、アクセス制御の変更を定期的にレビューする。

### 5. 可観測性を確保する

- ネットワークメトリクスを収集する
- flow log を有効にする
- distributed tracing を実装する

## 次のステップ

[Kernel Networking Stack](../kernel/02-network-stack.md) から始め、次に [Linux ネットワーク診断の実践](07-linux-network-diagnostics.md) とその [クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md) に進んでください。[学習パス](#learning-path) は、以下の CNI および AWS トピックに進む前に、これらの基礎をコンテナと Service に結び付けます。

1. [VPC CNI](01-vpc-cni.md) - デフォルト EKS CNI
2. [Cilium 詳細解説](cilium/README.md) - eBPF ベースのネットワーキング
3. [Calico 詳細解説](calico/README.md) - ルーティング、ポリシー、dataplane
4. [VPC Lattice](02-vpc-lattice.md) - AWS マネージドネットワーキング
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB 統合
6. [Gateway API](04-gateway-api.md) - 次世代 ingress
7. [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) - AWS Organizations をまたぐ VPC 接続 (フィールド検証済み)
8. [Pod ネットワークベンチマーク](06-pod-network-benchmark.md) - node/AZ 境界ごとの計測 latency と throughput

---

## 参考資料

- [Kubernetes ネットワークモデル](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Container runtime と CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI 仕様](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico 製品 edition](https://docs.tigera.io/calico/latest/about)
- [Calico ポリシー tier](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker flow log](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows の制限](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 ネットワーキングとポリシー](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel backend](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Original Weave repository の状態](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [EKS ネットワークポリシー構成](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS standard および Admin ネットワークポリシー](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS prefix delegation と maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin および DNS ポリシーのデプロイメントモデル](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode ネットワーキング](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS add-on 要件](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS control plane アーキテクチャ](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 image metadata](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon runtime security](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB 構成](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress 構成](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer の概念](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE カプセル化 (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS resolver](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver endpoint と rule](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC route table 評価順序](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Local route とより具体的な subnet route](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Static route と propagated route の優先順位](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS のアドレスと動作](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB flow stickiness と failover](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service 仮想 IP と kube-proxy モード](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service 名と forwarding 構成](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink resource endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables プロジェクト文書](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC transport protocol (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [HTTP/2 上の gRPC と load balancing](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
