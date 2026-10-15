# Kubernetes ネットワーキング

> **最終更新**: September 15, 2026. 機能に関する記述は Cilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9、AWS VPC CNI 1.23.0 を対象としています。インストール前に各製品の Kubernetes / プラットフォーム対応マトリクスを確認してください。これらは共同でテストされたクラスター構成ではありません。

## 概要

Kubernetes ネットワーキングは、コンテナ化されたアプリケーション間の通信を可能にする中核的なインフラストラクチャ層です。このセクションでは、Kubernetes ネットワーキングの基本概念から、高度な CNI (Container Network Interface) ソリューション、そして AWS EKS 環境におけるネットワーキングパターンまでを扱います。

## 学習パス {#learning-path}

初級コースの後は、[エキスパートネットワーキングパス](expert/README.md) を使って、プロトコルのプロジェクト、ルーティングポリシー、EVPN、Linux パフォーマンス、クラウド設計、自動化の評価をつなげてください。まず各ワークブックの環境、証跡、復旧基準を確認してください。

Linux やネットワーキングが初めての方は、[初級コース](beginner/README.md) から始めてください。8 つのレッスンで CLI、アドレッシング、DNS、SSH、ファイアウォール、モニタリング、そして総まとめの課題をつなげます。以下のパスは、その基礎をプロトコル、カーネル、クラスター実装へと広げていきます。

プロトコルの概念から観測へと積み上げ、それをコンテナ、クラスター、クラウドの責務に結び付けてください。前提条件を使って入り口を選び、成果を使って理解度を確認してから次に進んでください。

| 段階 | 役割 | 前提条件 | 成果 | 読む / 練習する |
|---|---|---|---|---|
| プロトコル、アドレッシング、HTTP | 語彙を確立する | 基本的なコマンドライン操作 | リクエストを追跡し、アドレッシング、トランスポート、アプリケーションの挙動を区別する | ネットワーク基礎 [Part 1](../basics/06-network-fundamentals-part1.md), [Part 2](../basics/06-network-fundamentals-part2.md), [Part 3](../basics/06-network-fundamentals-part3.md), [Part 4](../basics/06-network-fundamentals-part4.md) |
| Linux ソケット、VFS、パケットパス | API をカーネルに結び付ける | TCP/IP の基礎 | FD、ソケットバッファ、ウィンドウ、キューを区別する | [カーネルネットワークスタック](../kernel/02-network-stack.md) |
| Linux ネットワーク診断 | 証跡で仮説を検証する | ソケットとパケットパスの概念 | ソケット、パケット、アプリケーションの観測結果を相関付ける | [診断の実践](07-linux-network-diagnostics.md) · [クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker とコンテナネットワーキング | Namespace の境界を特定する | Linux パケットパスと基本的な診断 | ブリッジネットワーキング、公開ポート、コンテナ名前解決を説明する | [コンテナ技術](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | クラスターの抽象化を対応付ける | コンテナネットワーキング | 名前を Service 経由でそのエンドポイントまで追跡し、Ingress の役割を特定する | [Service とネットワーキング](../core/03-services-networking.md) · [ラボ](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、ポリシー | 実装の責務を比較する | Pod と Service のパス | パケット転送、ポリシー適用、可観測性を区別する | [eBPF の基礎](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS のネットワーク境界とパフォーマンス | モデルをクラウドのパスに適用する | CNI の概念と測定スキル | VPC、ノード、AZ の境界を特定し、測定結果を文脈の中で解釈する | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) · [Pod ネットワークベンチマーク](06-pod-network-benchmark.md) |

## Kubernetes ネットワーキングモデル

現在の Kubernetes モデルは、**意図的なネットワークセグメンテーションが適用される場合を除き**、Pod がアドレス変換やプロキシーなしでノードを越えて直接通信できる Pod ネットワークを提供します。kubelet などのノードエージェントは、自ノード上の Pod に到達できる必要があります。特定の接続が成功するかどうかは、Network Policy、ルーティング、アプリケーションのリスナーによって決まります。

通常の Pod は独自のネットワーク Namespace とクラスター全体で有効なアドレスを持ち、1 つの Pod 内のコンテナはその Namespace と localhost を共有します。ホストネットワークの Pod はノードのネットワークを共有し、デュアルスタックやマルチネットワーク構成ではより厳密なアドレスの取り扱いが必要になります。Pod を再作成すると別の IP が割り当てられることがありますが、同じ Pod 内のコンテナを再起動しても、そのネットワークサンドボックスが必ず再作成されるわけではありません。

| コンポーネント | 役割 |
|---|---|
| Pod ネットワーク | ワークロードのネットワーク Namespace 間のアドレッシングと接続性 |
| Service / ディスカバリー | 変化するエンドポイントの上に安定したサービス名または仮想アドレスを提供 |
| Ingress / Gateway 実装 | 設定された外部エントリーポイントとアプリケーションルーティング |
| Network Policy エンジン | 選択した実装がサポートするポリシーを適用 |

これらの役割は、必ず直列につながるパケットパスを形成するわけではありません。Service の変換、L7 プロキシー、ワークロードポリシーによって、特定のリクエストがネットワークをどう通過するかは変わり得ます。

### Pod ネットワーキング

Pod ネットワーキングは、Pod 間通信のためのアドレッシングとルートを提供します。以下の図は通常の IPv4 Pod を示しており、その接続は該当するポリシーとネットワーク制御が許可していることを前提としています。

![2 つのノードにまたがる直接的な IPv4 Pod パスの例。接続性は設定されたポリシーとルーティングに依存します。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

図中のアドレスは、通常の Pod アドレスの例です。意図的な分離や、ホストネットワーク・マルチネットワーク構成については、それぞれ別の解釈が必要です。

#### Pod ネットワーキングの実装方式

| 方式 | 説明 | CNI の例 |
|--------|-------------|-------------|
| **オーバーレイネットワーク** | 既存のネットワーク上でトラフィックをカプセル化する | Flannel VXLAN, Calico VXLAN/IPIP, Cilium VXLAN/Geneve |
| **ネイティブルーティング** | オーバーレイのカプセル化を行わず、下位ネットワークのルートを使用する | AWS VPC CNI, Calico routing/BGP, Cilium native routing |
| **条件付きカプセル化** | 設定されたトポロジーに応じて直接パスまたはカプセル化を使用する | 対応する Calico/Flannel/Cilium のモード。前提条件はそれぞれ異なる |

### Service ネットワーキング

Service は、通常は Pod である論理的なエンドポイントの集合と、そこへの到達方法を記述します。ClusterIP はデフォルトで安定した仮想 IP を提供します。headless Service はその仮想 IP を持たず、ExternalName は DNS CNAME マッピングを使用します。Service は Pod セレクターなしで管理されるエンドポイントを持つこともできます。

![ClusterIP、NodePort、LoadBalancer、ExternalName Service の代表的なエントリー機構。DNS マッピングはパケット転送とは区別されます。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

これらは代表的な公開機構であり、セキュリティの保証ではありません。NodePort の範囲やアクセス可能なノードアドレスは設定可能で、LoadBalancer は内部向けにもできます。ExternalName は DNS エイリアスを返すだけで、転送プロキシーを作成しません。

#### Service タイプの特性

`default` に `app: my-app` が一致する Pod を作成し、図示された targetPort でリッスンさせてください。NodePort のデフォルト割り当て範囲は 30000〜32767 で、設定可能です。外部からの到達性は、アドレス、ルート、アクセス制御に依存します。

LoadBalancer の例では **AWS Load Balancer Controller** を明示的に選択し、EC2 インスタンスターゲットと割り当て済み NodePort を使用しています。事前にそのコントローラーと IAM / サブネットの前提条件をインストール・設定してください。EKS Auto Mode は別のコントローラー / クラスを使用します。ここでのポート 443 は単に TCP ポートを選んでいるだけであり、TLS はバックエンドが 8443 で提供するか、ロードバランサー側で別途設定する必要があります。

これらのポートマッピングは、一般的な Kubernetes Service API を示しています。AWS は現在、EKS ネイティブの Network Policy に関する追加要件を文書化しています。Service のポートはコンテナポートと一致する必要があり、`metadata.ownerReferences` を持つコントローラー管理下の Pod が確実な適用を提供します。そのポリシー実装をテストする前に、例をこれらの要件に合わせて調整してください。

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

Ingress リソースには、コントローラーとそのデータプレーンが必要です。この HTTP の例では、`spec.ingressClassName: alb` と IP ターゲットを使用した AWS LBC を用いています。参照している `api-v1`、`api-v2`、`web-frontend` Service は `default` に存在し、ポート 80 を公開し、VPC でルーティング可能な Ready 状態の Pod エンドポイントを持っている必要があります。必要に応じて HTTPS / 証明書は別途設定してください。インストールとターゲットの前提条件は [LBC ガイド](03-aws-lb-controller.md) を参照してください。

Ingress は、HTTP/HTTPS トラフィックをクラスター内部の Service にルーティングするルールを定義します。

![Ingress のホスト / パスによる Service バックエンドと Pod への論理的なルーティング。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

図のボックスは Ingress のデータプレーン機能を表します。AWS LBC は ALB を設定するもので、アプリケーショントラフィックがコントローラーの調整 (reconciliation) プロセスを通過することはありません。ターゲットモードによっては、データプレーンは Service の仮想 IP を実際の追加ホップとして経由するのではなく、Pod IP または NodePort に到達できます。

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

CNI は、ランタイムがコンテナネットワークを設定するためのインターフェイスを標準化します。現在の Kubernetes では、kubelet は CRI を通じて Pod サンドボックスの操作を要求し、**コンテナランタイムが CNI を管理します**。kubelet が CNI を直接管理していた古いフラグは Kubernetes 1.24 で削除されました。

### ランタイムとプラグインの責務

| 主体 | 責務 |
|---|---|
| kubelet | コンテナランタイムインターフェイス経由でサンドボックスの作成 / 削除を要求する |
| コンテナランタイム | ネットワーク設定を選択し、CNI プラグインチェーンを呼び出す |
| CNI プラグイン | 設定を受け取り、ADD/DEL などのサポートされる操作を実行し、結果を返す |
| IPAM 実装 | アドレスを割り当て / 解放する。委譲プラグインの場合もあれば、プロバイダー固有のエージェントの一部の場合もある |
| 任意のノードエージェント | プロバイダー固有のルート、ポリシー、IP プール、データパスの状態を維持する |

ランタイムは CNI インターフェイスを通じてプラグインに設定を渡します。常駐する別のエージェントや IPAM バイナリーは、すべてのプラグインに必須というわけではありません。インターフェイスの種類も異なります。veth ペアは一般的ですが、唯一の実装ではありません。

## CNI の比較

| プロジェクト / 範囲 | ネットワーキングとポリシー | 区別すべき機能と制限 |
|---|---|---|
| **Cilium 1.20.1** | eBPF ネットワーキング。該当する L7 機能には Envoy を使用。Cilium Network Policy と Hubble | Linux ワーカーのデータプレーンで、AMD64/Arm64 の要件がある。Windows CLI が利用できることは Windows CNI サポートを意味しない。WireGuard/IPsec と Beta の ztunnel mTLS は適用範囲が異なる。 |
| **Calico Open Source 3.32** | ルーティング / カプセル化の選択肢。iptables、nftables、eBPF のオプション。順序付きポリシー Tier とホスト / ワークロードポリシー | Windows には Linux の eBPF や WireGuard データプレーンが使えないなど、別の制限がある。Whisker/Goldmane のフロー可観測性は Tech Preview として提供。有償機能についてはエディションマトリクスを参照。 |
| **Flannel 0.28.9** | ホストサブネットの割り当てとノード間トランスポート。VXLAN、host-gw などのバックエンド | `flanneld` 自体は NetworkPolicy を適用しない。Chart の任意設定 `netpol.enabled` が SIGs のポリシーコントローラーをデプロイする。WireGuard は文書化されたバックエンドで、IPsec は実験的。Windows VXLAN には固有の設定 / 制限がある。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPC アドレスの割り当てと EC2 の ENI / プレフィックス。サポート対象の Linux EC2 ノードで EKS 標準および Admin Network Policy 機能 | EKS Auto Mode はマネージドなネットワーキング実装で、追加の DNS ポリシー機能を持つ。Windows、Fargate、カスタムネットワーキング、プレフィックス委譲、マルチ NIC のサポートにはそれぞれ別の条件がある。 |
| **オリジナルの Weave Net プロジェクト** | 歴史的なオーバーレイネットワーキング実装 | オリジナルの `weaveworks/weave` リポジトリはアーカイブされている。新しいクラスターにおいてアクティブでサポートされたデフォルトとして説明してはならない。 |

### ポリシー、暗号化、可観測性

- Cilium は該当する L7 コンポーネントを通じて HTTP/DNS を認識したポリシーと、クラスター全体 / ホストのポリシーを提供します。その deny/allow のセマンティクスは、Calico の順序付き Tier API とは異なります。
- Calico Open Source には階層的なポリシー Tier とホストポリシーが含まれます。現在の製品マトリクスでは、アプリケーション層ポリシー、DNS/FQDN ポリシー、Cluster Mesh は Cloud/Enterprise に割り当てられており、これらを暗黙にオープンソース版の機能として扱ってはいけません。Calico が文書化している通信経路の暗号化は WireGuard を使用します。
- Amazon EKS は、Auto Mode およびサポート対象の EC2/VPC-CNI インストールに対して `ClusterNetworkPolicy` の Admin/Baseline 制御を提供します。AWS が説明している DNS/FQDN の `ApplicationNetworkPolicy` 機能は **Auto Mode** 向けです。その名称は、現時点で HTTP メソッド / ボディの検査を行うことを意味しません。
- Flannel の任意のポリシーコントローラーには独自の要件があり、ネットワーキングバックエンドを選ぶだけでは適用は有効になりません。
- ノード間の暗号化、認証されたワークロード ID、アプリケーションの mTLS は、それぞれ異なる制御です。ネットワークフローの可視性も、アプリケーションのトレーシングやプロセス / ファイルの適用とは異なります。

### ルーティングとパフォーマンス

Calico と Cilium は BGP を使ってルートをアドバタイズできますが、それ自体でマルチクラスターのサービスディスカバリー、ポリシー同期、暗号化が提供されるわけではありません。Flannel の host-gw は直接ルートを使用し、適切なレイヤー 2 の接続性が必要です。オーバーレイはカプセル化と MTU の考慮事項を追加しますが、CNI の名前から普遍的なパフォーマンス順位を推論することはできません。

かつて記載されていた 100/98/95/85/80/75 パーセントというスループットの数値には、再現可能なワークロード、バージョン、測定元がありませんでした。同等のハードウェア、カーネル、パケット / リクエストサイズ、並列度、暗号化 / ポリシー設定、スループット、損失、テールレイテンシーを用いてください。別ページの [Pod ベンチマーク](06-pod-network-benchmark.md) は、独自の当時の環境と測定値をそのまま保持しています。

## CNI 選択ガイド

まず必要なルーティング、ポリシー、オペレーティングシステム、サポートモデルを決め、その組み合わせをテストしてください。

| ニーズ | 評価の進め方 |
|---|---|
| 標準的な EKS の VPC アドレッシングとサポート対象の Network Policy | 2 つ目のポリシーエンジンを追加する前に、AWS VPC CNI / EKS の機能を評価する。 |
| 順序付きポリシー Tier、ホストポリシー、インフラの BGP | 該当する Calico のエディション / データプレーンとルーティングの前提条件を評価する。 |
| Cilium のポリシー、Hubble、選択したメッシュ機能 | Linux / カーネル / プラットフォームの互換性と [Cilium メッシュガイド](../service-mesh/cilium-service-mesh/README.md) を確認する。Envoy は該当する L7 パスの一部であり続ける。 |
| 限られた機能セットの小規模ネットワーク | Flannel のバックエンドと任意のポリシーコントローラーを、実際の要件に照らして評価する。 |
| プロセス、syscall、ファイルの適用 | Tetragon などのランタイムセキュリティコンポーネントを、Network Policy とは切り離して評価する。 |

### EKS マネージドアドオンの設定

以下は**設定ペイロード**の例であり、同一のワークロードに Calico と VPC CNI のポリシーエンジンの両方をインストールするよう指示するものではありません。

```json
{
  "enableNetworkPolicy": "true"
}
```

この設定において文書化されている型は文字列 `"true"` です。既存の Kubernetes バージョンに対応する EKS アドオンビルドを選択し、そのビルドの設定スキーマを確認してください。

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

アップストリームの 1.23.0 というリリース番号と、EKS の `eksbuild` バージョンは異なる識別子です。変更は意図したマネージドアドオン設定にマージしてください。`latest` を無条件に選んだり、無関係な値を置き換えたりしないでください。サードパーティーのポリシー実装からの移行では、既存の適用状態の削除と、テスト済みのノード / ワークロード移行計画も必要です。

## EKS ネットワーキングの基礎

### EKS のデフォルトネットワーキングアーキテクチャ

| 場所 / コンポーネント | 責務 |
|---|---|
| EKS 管理の VPC | AWS がマネージドな Kubernetes コントロールプレーンを複数のアベイラビリティーゾーンにまたがって運用する。 |
| 顧客のクラスター VPC | ワーカーのネットワーキング、選択したサブネット、EKS 管理のクロスアカウント ENI が、コントロールプレーンへの設定済みパスを提供する。 |
| 顧客 VPC の選択したサブネット内の ALB/NLB | 選択したパブリックまたは内部のアプリケーションエントリーポイントを提供する。インターネットゲートウェイ / NAT ゲートウェイはそのルーティング設定の代替にはならない。 |
| NAT ゲートウェイまたはプライベートサービスエンドポイント | ワークロード設計が必要とする特定のアウトバウンドパスを提供する。 |

かつての図はコントロールプレーンを顧客 VPC の内側に、ロードバランサーをその外側に描いていました。この所有境界の記述に置き換えられています。

### コンピュートモード別の DNS とネットワーキング

| コンピュートモード | DNS / コンポーネントの配置 |
|---|---|
| 標準的な EC2 ノード | 通常は設定済みの CoreDNS Deployment とインストール済みのネットワーキングコンポーネントを使用する。置き換える場合はそれ自体のサポートされた設定が必要。 |
| 純粋な EKS Auto Mode | CoreDNS、VPC CNI、kube-proxy の機能がマネージドなノードの systemd サービスとして動作する。これらのノードには CoreDNS の Deployment / アドオンは不要。 |
| Auto Mode と非 Auto ノードの混在 | 非 Auto ノード向けに CoreDNS Deployment を維持する。これらは他ノードの Auto Mode DNS サービスを利用できない。 |

Auto Mode の最初の DNS リゾルバーはノードローカルです。上位への転送やコントロールプレーンとの通信ではネットワークアクセスが必要になる場合があり、DNS 関連のすべてのパケットがノード内に留まることを保証するものではありません。AWS は Auto Mode について Admin と DNS の両方のポリシーを文書化しており、標準的な EC2 の VPC-CNI Admin ポリシーには独自のバージョン / 有効化要件があります。

### VPC CNI の仕組み

AWS VPC CNI は、選択した IPAM モードを使って通常の Pod に VPC でルーティング可能なアドレスを付与します。セカンダリー IPv4 アドレス、委譲プレフィックス、ブランチ ENI、マルチ NIC 構成はそれぞれ異なります。ホストネットワークの Pod はノードのネットワークを共有します。

![EC2 ENI から Pod へのセカンダリー IPv4 割り当ての例。任意のウォームインターフェイスを含む。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

これはセカンダリー IP モードのみを描いたものです。ウォーム ENI は設定可能な割り当て戦略であり、すべてのノードが常にちょうど 1 つを予約するという要件ではありません。プレフィックス委譲、カスタムネットワーキング、ブランチ ENI では割り当てルールが異なります。

#### ENI と IP の上限

| インスタンスタイプ | 最大 ENI 数 | ENI あたりの IPv4 スロット数 | 従来のセカンダリー IP ブートストラップ値 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

これらの値は VPC CNI 1.23.0 のインスタンス上限と従来の max-Pods 表に照らして検証済みです。当時の計算式は `ENIs × (IPv4 slots per ENI − 1) + 2` ですが、現在の普遍的な推奨ではありません。プレフィックス委譲、カスタムネットワーキング、ブランチ ENI、複数のネットワークカードはアドレス容量を変えます。Kubernetes のスケジューリングも kubelet の `maxPods` とリソースによって制限されます。EKS マネージドノードグループは、vCPU が 30 未満のインスタンスでは `maxPods` を 110、それ以外では 250 に制限します。利用可能な IP 数だけでこの上限を超えることはできません。

### EKS ネットワーキングの考慮事項

#### IP アドレス管理

**Linux VPC CNI** では、選択したアドオン / Helm / DaemonSet の管理機構を通じて、文書化された環境変数を設定してください。以下は EKS アドオンの設定の断片です。`enable-prefix-delegation` を含む旧来の `amazon-vpc-cni` ConfigMap は、この方法で Linux の IPAMD を設定するものではありません。変更を適用する際は、意図した他のアドオン値を保持してください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

あるいは、割り当ての下限合計と空き IP のターゲットを調整します。`MINIMUM_IP_TARGET` または `WARM_IP_TARGET` のいずれかが設定されている場合、それが `WARM_PREFIX_TARGET` より優先されます。これらは 4 つの独立した加算的ターゲットではなく、代替的なポリシーです。割り当ては依然としてプレフィックス単位で行われます。Nitro のサポート、IPv4 用の連続した `/28` の空間、適切な kubelet の Pod 上限は、それぞれ別の前提条件です。

Windows のプレフィックス割り当ては別の設定経路です。AWS は `amazon-vpc-cni` ConfigMap における `enable-windows-prefix-delegation` とそのウォームターゲットのキーを文書化しています。Linux の環境変数の手順をそのまま Windows にコピーしないでください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "MINIMUM_IP_TARGET": "5",
    "WARM_IP_TARGET": "2"
  }
}
```

#### カスタムネットワーキング

これらの IPv4 の例では、意図した AZ と VPC における実際のサブネット / セキュリティグループ ID が必要です。カスタムネットワーキングを有効にし、各ノードの ENIConfig をゾーンラベルで選択してください。明示的な ENIConfig のノードアノテーションは、そのラベルより優先されます。以下の例の名前はどの言語版でも同じリージョンを使用しています。実際のノードのゾーンに置き換えてください。ENIConfig オブジェクトをインストールするだけでは、カスタムネットワーキングは有効になりません。

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

以下の項目は、この概要の他の箇所で名前だけ触れられているものです。完全なセットアップ手順と測定値はリンク先の詳細ページにあります。このセクションでは、これらの要素が層ごとにどう異なり、それぞれがどこに位置づけられるかを整理します。

### L2〜L7 と、ルーターとロードバランサーの違い

「ルーター」と「ロードバランサー」は同じ文の中に登場しがちですが、答えている問いが異なります。ルーターは 1 つの宛先に対して (一般的には) 1 つの経路を選びます。ロードバランサーは、同等な複数の候補の中から分散アルゴリズムを使って 1 つのターゲットを選びます。

| 層 | デバイス / 機能 | 判断の基準 | Kubernetes/AWS への対応 |
|---|---|---|---|
| L2 (リンク) | スイッチ、ブリッジ | 宛先 MAC アドレス | CNI が作成する veth ペアと Linux ブリッジ、ENI が公開する仮想 NIC |
| L3 (ネットワーク) | ルーター、または透過的なアプライアンス挿入 | ルーティングは宛先 IP、アプライアンス選択はフロー識別 | VPC の暗黙のルーター、TGW。GWLB はアプライアンス向けに IP パケットをカプセル化する |
| L4 (トランスポート) | L4 ロードバランサー | コネクション / フローの識別。一般的には 5 タプル | NLB、kube-proxy (iptables, IPVS, nftables)、独立した eBPF の Service 実装 |
| L7 (アプリケーション) | L7 ロードバランサー / リバースプロキシー | リクエストごとのホスト、パス、ヘッダー。プロトコルを認識する | ALB、Ingress/Gateway API の実装、サービスメッシュのサイドカー (Envoy) |

決定的な違いは**分散の単位**です。L4 ロードバランサーは通常、TCP コネクションまたは追跡された UDP フローに対してターゲットを選択します。L7 プロキシーは、サポートされるアプリケーションリクエストごとに、コネクションを共有するリクエストであってもターゲットを選択できます。GWLB はアプリケーションリクエストを解析するのではなく、カプセル化された IP フローをセキュリティアプライアンス群に分散します。フローの固定 (stickiness) は、設定されたタイムアウト、ヘルス、フェイルオーバーの挙動に依存し、フローが再割り当てされたり中断されたりすることが絶対にないという保証ではありません。

> 📎 L2/L3 の概念のプロトコルレベルの定義は [ネットワーク基礎 Part 1](../basics/06-network-fundamentals-part1.md) にあります。ALB/NLB のターゲットタイプと実際の設定は [AWS Load Balancer Controller](03-aws-lb-controller.md) にあります。

### アカウント / VPC をまたぐ接続: TGW、VPC Peering、GWLB、PrivateLink、Lattice

これら 5 つの接続オプションは、層とトラフィックモデルが異なります。TGW の RAM 共有、VPC Peering、PrivateLink、TGW Peering、VPC Lattice にまたがる実測レイテンシーは [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) にあります。このセクションでは、その比較表にない GWLB を追加し、5 つすべてを層の観点から捉え直します。

| 接続方式 | 層 / モデル | 特性 |
|---|---|---|
| VPC Peering | L3、双方向の IP ルーティング | 推移的ではない。CIDR が重複している場合は設定できない |
| Transit Gateway (TGW) | L3、ハブアンドスポークの IP ルーティング | 1 つ以上の TGW ルートテーブルにまたがるアタッチメントの関連付けと伝播を使用する。RAM 経由でアカウント間で共有される |
| Gateway Load Balancer (GWLB) | L3、透過的なアプライアンス挿入 | 元のパケットを GENEVE (UDP 6081) でカプセル化する。VPC エンドポイントサービスモデルが、コンシューマーのトラフィックをプロバイダーのアプライアンス群に接続する |
| PrivateLink | プライベートエンドポイント接続 | NLB をバックエンドとするエンドポイントサービスは 1 つのモデルであり、リソースエンドポイントも存在する。コンシューマー / プロバイダーの CIDR は重複してもよい |
| VPC Lattice | アプリケーションとリソースのネットワーキング | HTTP/HTTPS サービスは L7 ルーティングと任意の IAM 認可をサポートする。TLS パススルーとリソース設定では機能が異なる |

GWLB は、ファイアウォールや IDS/IPS といった検査アプライアンスを、Gateway Load Balancer エンドポイント経由で IP パスに挿入します。デフォルトのフロー固定は 5 つのフィールドを使用し、サポートされる設定では代わりに 2 つまたは 3 つを使用できます。往復のルート、アプライアンスのヘルス、カプセル化の MTU、NACL、そして実際のワークロード / アプライアンスのセキュリティグループを検証してください。GWLB 自体は ALB のようなセキュリティグループを持たず、フロー固定は障害試験の代わりにはなりません。

> 📎 EKS と VPC Lattice の完全な統合 (Gateway API Controller、IAM 認可、ルーティング) は [VPC Lattice](02-vpc-lattice.md) にあります。

### DNS リゾルバーとルートテーブルの実際の挙動

**DNS リゾルバー:** AmazonProvidedDNS は **Route 53 Resolver そのもの**です。そのアドレスには、VPC のプライマリー IPv4 ネットワークアドレスに 2 を足したもの (`10.0.0.0/16` なら `10.0.0.2`) と `169.254.169.253` が含まれます。Resolver のルールに従って、関連付けられたプライベートゾーンとパブリックな名前を解決します。CoreDNS は通常、設定された Kubernetes クラスタードメイン (多くの場合 `cluster.local`) を提供します。`kube-dns` はその Service 名であり、Namespace や DNS ゾーンではありません。外部への転送は Corefile と、DNS Pod から見えるリゾルバーファイルに従います。ノードのリゾルバーファイルがそのまま使われると仮定せず、これらの設定を確認してください。Resolver エンドポイントを用いた設計では、インバウンドエンドポイントがオンプレミスからのクエリーを受け付け、アウトバウンドエンドポイントと関連ルールが選択された VPC のクエリーをオンプレミスの DNS に転送します。Auto Mode のノードローカルリゾルバーは、上位への依存をなくすものではありません。

**ルートテーブル:** VPC のルート評価は一般に最長プレフィックス一致を使用します。AWS では、アプライアンスルーティングのために `local` ルートのターゲットを置き換えたり、サポートされるより具体的なサブネットルートを追加したりできます。`local` が無条件に最も具体的なルートであるとは限りません。宛先が同一の場合、静的な VPC ルートは仮想プライベートゲートウェイから伝播されたルートより優先されます。TGW をターゲットとする VPC ルートは静的であり、TGW 内部での伝播はその別のルートテーブルに属します。無効なターゲットは `blackhole` エントリーを残してトラフィックを破棄することがあるため、宛先だけでなくルートの状態も確認してください。明示的なルートテーブルの関連付けがないサブネットは、VPC のメインルートテーブルを使用します。

> 📎 TGW/Peering のルート優先順位と静的ルートの設定例は [組織間 VPC 接続の運用上の知見](05-cross-org-vpc-connectivity.md#operational-findings) にあります。

### カーネルのデータプレーン: iptables、IPVS、eBPF、パケットフィルタリング

Linux における Service 転送と Network Policy の適用は、異なる機構を使用できます。Netfilter は、iptables と nftables が使用するパケットパスのフックを提供します。eBPF の実装は XDP、tc、ソケットのフックにアタッチし、そこで Service の選択を行えます。これは、eBPF を有効にしたクラスターのすべてのパケットが Netfilter やコネクション追跡をバイパスすることを意味しません。経路は CNI、カーネル、ルーティング、機能設定に依存します。

| 実装 | 位置 | 特性 |
|---|---|---|
| iptables | netfilter フック上の逐次的なルールチェーン | 評価時間がルール数に比例する (O(n))。kube-proxy の長年のデフォルトモード |
| IPVS | カーネルネイティブの L4 ロードバランサー。netfilter の拡張 | ハッシュベースの参照 (ほぼ O(1))。Kubernetes 1.35 以降、kube-proxy のモードとして非推奨 |
| nftables | iptables の後継となる netfilter のフレームワーク | 1.33 以降、kube-proxy の安定モード。まずカーネル / CNI の互換性を確認する |
| eBPF (例: Cilium) | 設定された XDP、tc、ソケットのフック | kube-proxy の Service 処理を置き換えられる。これは別個の実装であり、Netfilter/conntrack の挙動は経路ごとに異なる |

実装を切り替えると、カーネルのルールやアクティブなコネクションが残る場合があります。ディストリビューション / CNI の移行手順に従い、必要に応じてワークロードを drain し、クリーンアップにノード再起動が必要な場合はそれも計画してください。kube-proxy を eBPF ベースの CNI で置き換える場合も、両実装が同じ Service トラフィックを競合して扱わないよう、サポートされた切り替え順序が必要です。

> 📎 IPVS の非推奨のタイムラインと nftables の安定版への移行は [Kubernetes 入門](../basics/04-kubernetes-introduction.md) で扱っています。Cilium の eBPF による kube-proxy 置き換えは [Cilium eBPF](cilium/02-ebpf.md)、Calico の eBPF データプレーンとその移行手順は [Calico eBPF](calico/06-ebpf-dataplane.md) にあります。

### 計算集約型ワークロードのネットワーキング: ENI、EFA、NVLink、光トランシーバー

ENI、EFA、NVLink はそれぞれ異なる経路を担います。**ENI** は 1 つのアベイラビリティーゾーン内の EC2 インスタンスにアタッチされる仮想ネットワークインターフェイスで、その通常の IP トラフィックはルーティングとポリシーが許可すれば他の AZ や接続された VPC に到達できます ([VPC CNI](01-vpc-cni.md) を参照)。**EFA** は、互換性のある MPI/NCCL ソフトウェアが libfabric 経由で使用する OS バイパスデバイスを提供します。**EFA デバイスのトラフィックはルーティング不可であり、VPC/AZ の境界を越えられません**。EFA-with-ENA インターフェイスの ENA デバイスを通る通常の IP トラフィックはルーティング可能なままです。EFA 専用インターフェイスには ENA デバイスも IP アドレッシングもありません。**NVLink** は、サポートされるラックスケールの NVLink ドメインを含む、サポート対象システム内の GPU 同士を接続します。EFA に対して一定の高速化が得られると仮定せず、選択したハードウェア、集団通信、配置を実測してください。

**光トランシーバー**は、データセンターネットワーキング一般の概念です。銅の DAC (Direct Attach Copper) ケーブルは短距離に適し、光モジュールと光ファイバーはそれ以外の距離と帯域幅の要件に対応します。QSFP と OSFP はモジュールの形状 (フォームファクター) を表すもので、光媒体であることの保証ではありません。これは一般的な背景知識として扱ってください。特定の AWS ワークロードの物理配線を規定するものではありません。

> 📎 NVLink/IMEX のトポロジーを考慮したスケジューリングと GPU Pod 配置の例は [AI/ML インフラストラクチャ](../ai-ml/06-ai-infrastructure.md) にあります。EFA の VPC/AZ 境界の制約と測定値は [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) にあります。

### 次世代プロトコルが Kubernetes にもたらす意味: HTTP/3、gRPC、QUIC

HTTP/3 (RFC 9114) とそのトランスポートである QUIC (RFC 9000) のプロトコル的な仕組みは、[ネットワーク基礎 Part 2](../basics/06-network-fundamentals-part2.md) と [Part 3](../basics/06-network-fundamentals-part3.md) で扱っています。ここでは、Kubernetes のトラフィック分散に実際に影響する点だけを扱います。

- **gRPC と L4 ロードバランサー:** gRPC はリクエストを HTTP/2 コネクション上で多重化します。L4 バランサーは通常、確立済みの TCP コネクションを選択したエンドポイントに保ち続けます。そのエンドポイントがプロキシーであれば、さらにルーティングの判断を行えます。Pod を追加するだけでは既存のコネクションは再分散されません。RPC ごとの分散には、互換性のある L7 プロキシーかクライアント側のポリシーが必要です。ストリーミング RPC は 1 つの呼び出しのままであり、その個々のメッセージが独立に分散されることはありません。
- **Gateway API の GRPCRoute:** Ingress には gRPC 固有のリソースはありませんが、Gateway API は `GRPCRoute` によってサービス / メソッドレベルのルーティングを標準化します。サポート状況 (ヘッダー一致の数、リトライポリシーなど) は実装ごとに異なるため、コントローラー自身のドキュメントを確認してください。
- **HTTP/3/QUIC が実際にクラスターのどこまで届くか:** クライアントとエッジ (CDN やロードバランサー) の間で HTTP/3 がサポートされるかどうかは、クラスター内部や Ingress のバックエンド接続で HTTP/3 がサポートされるかどうかとは別の問題です。多くの Ingress/Gateway 実装は、バックエンドに対しては依然として HTTP/1.1 または HTTP/2 で通信し、エンドツーエンドの HTTP/3 がサポートされるかは実装とバージョンによって異なります。一般化せず、実際に使用しているコントローラーのドキュメントを確認してください。

## ネットワーキングのサブページ

このセクションでは、以下のトピックを詳しく扱います。

### [はじめての Linux ネットワーキング](beginner/README.md) {#beginner-course}

Linux やネットワーキングが初めての方は、[初級コース](beginner/README.md) から始めてください。8 つのレッスンで CLI、アドレッシング、DNS、SSH、ファイアウォール、モニタリング、そして総まとめの課題をつなげます。以下のパスは、その基礎をプロトコル、カーネル、クラスター実装へと広げていきます。

### [エキスパートネットワーキングパス](expert/README.md) {#expert-course}

初級コースの後は、[エキスパートネットワーキングパス](expert/README.md) を使って、プロトコルのプロジェクト、ルーティングポリシー、EVPN、Linux パフォーマンス、クラウド設計、自動化の評価をつなげてください。まず各ワークブックの環境、証跡、復旧基準を確認してください。

### [Linux ネットワーク診断の実践](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

CNI の実装を学ぶ前に、[カーネルのソケットとパケットパスの概念](../kernel/02-network-stack.md) を観測結果に結び付けてください。[診断クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md) で自分の解釈を確認しましょう。

### [VPC CNI](01-vpc-cni.md)
通常の Pod に VPC アドレスを割り当てる EKS ネットワーキングと、モード別の IPAM / ポリシーの前提条件。

### [Cilium 詳解](cilium/README.md)
高性能な eBPF ベースの CNI ソリューション。L7 Network Policy、Service Mesh、可観測性 (Hubble) といった高度な機能を提供します。

### [Calico 詳解](calico/README.md)
最も広く使われている CNI の 1 つ。強力な Network Policy、BGP サポート、エンタープライズ機能を備えます。導入、アーキテクチャ、ネットワーキングモード、BGP 詳解、Network Policy、eBPF、高度なトピック、EKS 統合、運用ガイドを扱います。

### [VPC Lattice](02-vpc-lattice.md)
AWS マネージドのアプリケーションネットワーキングサービス。VPC 間、アカウント間のサービス間通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Kubernetes の Service と Ingress を AWS ELB (ALB/NLB) と統合します。

### [Gateway API](04-gateway-api.md)
次世代の Kubernetes Ingress API。標準化されたリソースモデルとロールベースの設定。

### [Pod ネットワークベンチマーク](06-pod-network-benchmark.md)
同一ノード、同一 AZ、AZ 間について EKS 上で測定した Pod 間 RTT、HTTP レイテンシー、スループット。加えて DNS の `ndots:5` によるクエリー増幅。

## ネットワークのトラブルシューティング

### よくある問題と解決策

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

診断は、上記のツールを備えた既存の Pod から実行してください。クラスターにインストールされている CNI だけを対象にクエリーしてください。Auto Mode のシステムサービスはこれらの DaemonSet ではありません。DNS の成功、TCP の到達性、アプリケーションの HTTP レスポンスは、それぞれ別のチェックです。ICMP はブロックされていたり追加の権限を必要とする場合があるため、ping の失敗だけで TCP サービスに到達できないと結論付けることはできません。

#### Service に到達できない

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

現在のエンドポイントの診断には EndpointSlice を使用してください。Service のセレクター、targetPort、エンドポイントの Ready 状態、アドレスファミリー、該当するポリシーを確認します。kube-proxy のログを調べるのは、そのコンポーネントが実際に Service 転送を担っている場合に限ってください。eBPF による置き換えや Auto Mode では独自の診断が必要です。

#### Network Policy のデバッグ

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium のコマンドは、DaemonSet 参照によって選択された 1 つの Agent を調べます。インシデントを追跡する際は、影響を受けたノードの Agent を選んでください。Calico のネイティブ API を使うインストールでは異なる API グループが公開されることがあるため、そのインストールで提供されているリソースを確認してください。Kubernetes、Calico、AWS の拡張ポリシーはそれぞれ別のリソースであり、優先順位も異なる場合があります。

### ネットワークパフォーマンステスト

この範囲を限定した TCP の演習では、publisher がピン留めした Netshoot v0.16 のイメージインデックスを使用します。これには Linux の AMD64 と Arm64 イメージが含まれ、その Dockerfile には `iperf3` が含まれています。これらの Pod は、TCP 5201 が許可されているテスト環境に作成してください。これは例示的なワークロードであり、測定に基づく CNI の比較ではありません。

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

クライアントは 1 時間スリープし、コマンドは 10 秒間、送出トラフィックを 10 Mbit/s に制限します。これは選択した経路をテストするもので、最大スループットを測るものではありません。結果を解釈する前に、実際の Pod / ノード / AZ の配置、リソース制限、ポリシーを記録してください。Windows ノードには Windows 向けのツールを選んでください。終了時は、自分が作成したテストリソースのみを削除してください。

これらの単体の診断用 Pod は接続性テスト用です。EKS ネイティブの Network Policy 適用テストには、Deployment/Job が管理する Pod と、文書化された Service / コンテナポートの要件を使用してください。

## ベストプラクティス

### 1. IP アドレス設計

- 十分に大きな CIDR ブロックを設計する
- Pod ネットワークと Service ネットワークを分離する
- 将来の拡張を見込んでサブネットを設計する

### 2. Network Policy の適用

この例を使う前に、分離された `networking-demo` Namespace を作成してください。この例はその Namespace のすべての Pod を選択し、標準的な Kubernetes NetworkPolicy のセマンティクスの下で Ingress と Egress の両方を分離します。必要な DNS とアプリケーションの通信には、明示的な許可ルールが必要です。適用にはそれをサポートするポリシーエンジンが必要です。追加のクラスター / 管理者向けポリシー API は優先順位を変えることがあり、このマニフェスト 1 つで完全なゼロトラストアーキテクチャになるわけではありません。

- デフォルト拒否ポリシーを適用する (ゼロトラスト)
- 必要なトラフィックのみを明示的に許可する
- Namespace を分離する

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

### 3. パフォーマンス最適化

- 適切な CNI を選ぶ (ワークロードに合ったもの)
- MTU の最適化
- カーネルパラメーターのチューニング

### 4. セキュリティ強化

- サポートされているトランスポート暗号化を選択し、どのトラフィックが対象になるかを検証する。
- 必要に応じてワークロード / アプリケーションの ID と mTLS を設定する。これらは DNS/IP ベースの許可リストとは切り離して扱う。
- ポリシー、証明書、アクセス制御の変更を定期的にレビューする。

### 5. 可観測性の確保

- ネットワークメトリクスを収集する
- フローログを有効にする
- 分散トレーシングを実装する

## 次のステップ

[初級コース](beginner/README.md) の後は、[カーネルネットワークスタック](../kernel/02-network-stack.md)、続いて [Linux ネットワーク診断の実践](07-linux-network-diagnostics.md) とその [クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md) に進んでください。[学習パス](#learning-path) は、これらの基礎を以下の CNI と AWS のトピックの前にコンテナと Service へと結び付けます。

1. [VPC CNI](01-vpc-cni.md) - EKS のデフォルト CNI
2. [Cilium 詳解](cilium/README.md) - eBPF ベースのネットワーキング
3. [Calico 詳解](calico/README.md) - ルーティング、ポリシー、データプレーン
4. [VPC Lattice](02-vpc-lattice.md) - AWS マネージドネットワーキング
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB 統合
6. [Gateway API](04-gateway-api.md) - 次世代の Ingress
7. [組織間 VPC 接続](05-cross-org-vpc-connectivity.md) - AWS Organizations をまたぐ VPC の接続 (実地検証済み)
8. [Pod ネットワークベンチマーク](06-pod-network-benchmark.md) - ノード / AZ 境界ごとの実測レイテンシーとスループット

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
