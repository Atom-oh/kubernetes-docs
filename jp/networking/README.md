# Kubernetesネットワーキング

> **最終更新**: September 13, 2026。機能の参照対象はCilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9、AWS VPC CNI 1.23.0です。インストール前に各製品のKubernetes/プラットフォーム対応表を確認してください。これらを組み合わせたクラスター構成としてテストしたわけではありません。

## 概要

Kubernetesネットワーキングは、コンテナ化されたアプリケーション間の通信を可能にする基盤インフラ層です。このセクションでは、Kubernetesネットワーキングの基本概念から高度なCNI（Container Network Interface）ソリューション、AWS EKS環境のネットワーキングパターンまで扱います。

## Kubernetesネットワーキングモデル

現在のKubernetesモデルは、**意図的なネットワーク分割に従い**、アドレス変換やプロキシなしでPodがノードをまたいで直接通信できるPodネットワークを提供します。kubeletなどのノードエージェントは、自ノードのPodに到達できる必要があります。特定の接続の成否は、ネットワークポリシー、ルーティング、アプリケーションのリスナーにも依存します。

通常のPodは独自のネットワーク名前空間とクラスター全体でのアドレスを持ち、同じPodのコンテナはその名前空間とlocalhostを共有します。ホストネットワークのPodはノードのネットワークを共有し、デュアルスタックや複数ネットワーク構成ではより厳密なアドレス処理が必要です。Podを再作成すると別のIPになる場合がありますが、同じPod内のコンテナ再起動が必ずネットワークサンドボックスを再作成するわけではありません。

| コンポーネント | 役割 |
|---|---|
| Podネットワーク | ワークロードのネットワーク名前空間間のアドレス割り当てと接続 |
| Service/検出 | 変化するエンドポイントに対する安定したサービス名または仮想アドレス |
| Ingress/Gateway実装 | 設定された外部入口とアプリケーションルーティング |
| ネットワークポリシーエンジン | 選択した実装がサポートするポリシーを適用 |

これらの役割が必須の直列パケット経路を形成するわけではありません。Service変換、L7プロキシ、ワークロードポリシーによって、個々のリクエストのネットワーク経路は変わります。

### Podネットワーキング

PodネットワーキングはPod通信のアドレスと経路を提供します。以下の図は通常のIPv4 Podを示し、該当ポリシーとネットワーク制御が接続を許可することを前提とします。

![2つのノードをまたぐ直接IPv4 Pod経路の例。接続性は設定済みのポリシーとルーティングに従う。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

アドレスは通常のPodアドレスの例です。意図的な分離、ホストネットワーク、複数ネットワーク構成は、それぞれに応じて解釈する必要があります。

#### Podネットワーキングの実装方法

| 方法 | 説明 | CNIの例 |
|--------|-------------|-------------|
| **オーバーレイネットワーク** | 既存ネットワーク上でトラフィックをカプセル化 | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **ネイティブルーティング** | オーバーレイのカプセル化なしに基盤ネットワークの経路を使用 | AWS VPC CNI、Calicoルーティング/BGP、Ciliumネイティブルーティング |
| **条件付きカプセル化** | 設定したトポロジーに応じて直接経路またはカプセル化を使用 | 対応するCalico/Flannel/Ciliumモード。前提条件は異なる |

### Serviceネットワーキング

Serviceは通常Podであるエンドポイントの論理集合と、その到達方法を記述します。ClusterIPはデフォルトで安定した仮想IPを提供し、ヘッドレスServiceは仮想IPを持たず、ExternalNameはDNS CNAMEマッピングを使います。Podセレクターを使わずに管理されるエンドポイントも持てます。

![ClusterIP、NodePort、LoadBalancer、ExternalName Serviceの典型的な入口の仕組み。DNSマッピングとパケット転送を区別している。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

これらは典型的な公開方法であり、セキュリティ保証ではありません。NodePort範囲とアクセス可能なノードアドレスは設定でき、LoadBalancerは内部向けにもできます。ExternalNameはDNS別名を返し、転送プロキシを作成しません。

#### Serviceタイプの特性

表示したターゲットポートで待ち受ける、一致する`app: my-app` Podを`default`に作成します。NodePortのデフォルト割り当て範囲は30000–32767で、設定可能です。外部到達性はアドレス、経路、アクセス制御にも依存します。

LoadBalancerの例は**AWS Load Balancer Controller**を明示的に選択し、EC2インスタンスターゲットと割り当て済みNodePortを使用します。先にコントローラーとIAM/サブネットの前提条件をインストール・設定してください。EKS Auto Modeは別のコントローラー/クラスを使います。ここでの443はTCPポートを選ぶだけです。TLSはバックエンドの8443で提供するか、ロードバランサーに別途設定する必要があります。

これらのポート対応は一般的なKubernetes Service APIを示します。AWSは現在、ネイティブEKSネットワークポリシーの追加要件を文書化しています。Serviceポートはコンテナポートと一致する必要があり、`metadata.ownerReferences`を持つコントローラー管理Podが確実な適用を可能にします。そのポリシー実装をテストする前に、例を要件に合わせてください。

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

### Ingressネットワーキング

Ingressリソースにはコントローラーとデータプレーンが必要です。このHTTP例は`spec.ingressClassName: alb`とIPターゲットを設定したAWS LBCを使います。参照する`api-v1`、`api-v2`、`web-frontend` Serviceは`default`に存在し、ポート80を公開して、準備済みかつVPCでルーティング可能なPodエンドポイントを持つ必要があります。必要ならHTTPS/証明書を別途設定します。インストールとターゲットの前提条件は[LBCガイド](03-aws-lb-controller.md)を参照してください。

IngressはHTTP/HTTPSトラフィックをクラスター内部のServiceへルーティングするルールを定義します。

![Ingressのホスト/パスからServiceバックエンドとPodへの論理的なルーティング。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

ボックスはIngressのデータプレーン機能を表します。AWS LBCはALBを設定し、アプリケーショントラフィックはコントローラーの調整処理を通りません。ターゲットモードにより、Service仮想IPを文字どおり追加ホップとして通るのではなく、Pod IPまたはNodePortに到達できます。

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

## CNI（Container Network Interface）

CNIは、ランタイムがコンテナネットワークを設定するインターフェースを標準化します。現在のKubernetesでは、kubeletがCRIを通じてPodサンドボックス操作を要求し、**コンテナランタイムがCNIを管理します**。kubeletの旧来の直接CNI管理フラグはKubernetes 1.24で削除されました。

### ランタイムとプラグインの責務

| 主体 | 責務 |
|---|---|
| kubelet | コンテナランタイムインターフェース経由でサンドボックスの作成/削除を要求 |
| コンテナランタイム | ネットワーク設定を選択しCNIプラグインチェーンを呼び出す |
| CNIプラグイン | 設定を受け取り、ADD/DELや他の対応操作を実行して結果を返す |
| IPAM実装 | アドレスを割り当て/解放。委任プラグインまたはプロバイダー固有エージェントの一部の場合がある |
| オプションのノードエージェント | プロバイダー固有の経路、ポリシー、IPプール、データパス状態を維持 |

ランタイムはCNIインターフェースを通じてプラグインに設定を渡します。すべてのプラグインに独立した常駐エージェントやIPAMバイナリが必須ではありません。インターフェースタイプも異なり、vethペアが一般的ですが唯一の実装ではありません。

## CNIの比較

| プロジェクト / 範囲 | ネットワーキングとポリシー | 区別すべき機能と制限 |
|---|---|---|
| **Cilium 1.20.1** | eBPFネットワーキング。該当L7機能にEnvoy。CiliumネットワークポリシーとHubble | LinuxワーカーデータプレーンでAMD64/Arm64要件がある。Windows CLIの提供はWindows CNIサポートではない。WireGuard/IPsecとベータ版ztunnel mTLSの範囲は異なる。 |
| **Calico Open Source 3.32** | ルーティング/カプセル化の選択肢。iptables、nftables、eBPF。順序付きポリシーTierとホスト/ワークロードポリシー | WindowsにはLinux eBPFやWireGuardデータプレーンがないなど、別の制限がある。Whisker/Goldmaneのフロー可観測性は技術プレビュー。有料機能はエディション表を参照。 |
| **Flannel 0.28.9** | ホストサブネットの割り当てとノード間転送。VXLAN、host-gwなどのバックエンド | `flanneld`自体はNetworkPolicyを適用しない。チャートのオプション`netpol.enabled`がSIGsポリシーコントローラーをデプロイ。WireGuardは文書化されたバックエンドで、IPsecは実験的。Windows VXLANには固有の設定/制限がある。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPCアドレス割り当てとEC2 ENI/プレフィックス。対応Linux EC2ノードでEKS標準およびAdminネットワークポリシー | EKS Auto Modeは追加DNSポリシー機能を持つマネージドネットワーク実装。Windows、Fargate、カスタムネットワーキング、プレフィックス委任、複数NICサポートには別々の条件がある。 |
| **元のWeave Netプロジェクト** | 過去のオーバーレイネットワーク実装 | 元の`weaveworks/weave`リポジトリはアーカイブ済み。新規クラスター向けの活発でサポートされたデフォルトと説明しない。 |

### ポリシー、暗号化、可観測性

- Ciliumは該当L7コンポーネントを通じてHTTP/DNS対応ポリシーと、クラスター全体/ホストポリシーを提供します。deny/allowの意味はCalicoの順序付きTier APIとは異なります。
- Calico Open Sourceには階層的ポリシーTierとホストポリシーがあります。現在の製品表では、アプリケーション層ポリシー、DNS/FQDNポリシー、Cluster MeshはCloud/Enterpriseに割り当てられています。これらを暗黙にオープンソース版の機能としてはいけません。Calicoの文書化された転送時暗号化はWireGuardを使用します。
- Amazon EKSは、Auto Modeと対応EC2/VPC-CNIインストールに`ClusterNetworkPolicy`のAdmin/Baseline制御を提供します。AWSが説明するDNS/FQDNの`ApplicationNetworkPolicy`機能は**Auto Mode**向けです。その名前は、現在HTTPメソッド/本文を検査することを意味しません。
- Flannelのオプションのポリシーコントローラーには独自要件があり、ネットワークバックエンドを選ぶだけでは適用は有効になりません。
- ノード間暗号化、認証済みワークロードID、アプリケーションmTLSは別々の制御です。ネットワークフローの可視性も、アプリケーショントレースやプロセス/ファイルの制御とは異なります。

### ルーティングと性能

CalicoとCiliumはBGPで経路を広告できますが、それだけでマルチクラスターのサービス検出、ポリシー同期、暗号化を提供するわけではありません。Flannel host-gwは直接経路を使い、適切なレイヤー2接続が必要です。オーバーレイではカプセル化とMTUの考慮が増えますが、CNI名から普遍的な性能順位は導けません。

以前の100/98/95/85/80/75パーセントというスループット値には、再現可能なワークロード、バージョン、測定元がありませんでした。比較可能なハードウェア、カーネル、パケット/リクエストサイズ、同時実行数、暗号化/ポリシー設定、スループット、損失、テールレイテンシーを使います。別の[Podベンチマーク](06-pod-network-benchmark.md)は、独自の過去の環境と測定を保持します。

## CNI選択ガイド

必要なルーティング、ポリシー、OS、サポートモデルを先に選び、その組み合わせをテストしてください。

| 要件 | 評価方法 |
|---|---|
| 標準EKS VPCアドレスと対応ネットワークポリシー | 第2のポリシーエンジンを追加する前にAWS VPC CNI/EKSの機能を評価。 |
| 順序付きポリシーTier、ホストポリシー、インフラBGP | 該当Calicoエディション/データプレーンとルーティング前提条件を評価。 |
| Ciliumポリシー、Hubble、選択したメッシュ機能 | Linux/カーネル/プラットフォーム互換性と[Ciliumメッシュガイド](../service-mesh/cilium-service-mesh/README.md)を確認。Envoyは該当L7経路に引き続き含まれる。 |
| 機能を絞った小規模ネットワーク | 実際の要件に対してFlannelのバックエンドとオプションのポリシーコントローラーを評価。 |
| プロセス、システムコール、ファイルの制御 | ネットワークポリシーとは別にTetragonなどのランタイムセキュリティコンポーネントを評価。 |

### EKSマネージドアドオン設定

以下は**設定ペイロード**の例であり、CalicoとVPC CNIポリシーエンジンを同じワークロードに両方インストールする指示ではありません。

```json
{
  "enableNetworkPolicy": "true"
}
```

文字列`"true"`はこの設定で文書化された型です。既存Kubernetesバージョンに互換性のあるEKSアドオンビルドを選び、その設定スキーマを調べます。

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

上流の1.23.0リリース番号とEKSの`eksbuild`バージョンは異なる識別子です。意図したマネージドアドオン設定に変更をマージし、無条件に`latest`を選んだり無関係な値を置き換えたりしないでください。第三者ポリシー実装からの移行には、その既存の適用状態の削除と、テスト済みノード/ワークロード移行計画も必要です。

## EKSネットワーキングの基礎

### EKSのデフォルトネットワーク構成

| 場所 / コンポーネント | 責務 |
|---|---|
| EKS管理VPC | AWSがマネージドKubernetesコントロールプレーンを複数AZにまたがって実行。 |
| 顧客のクラスターVPC | ワーカーネットワーク、選択したサブネット、EKS管理のクロスアカウントENIが、設定されたコントロールプレーンへの経路を提供。 |
| 選択した顧客VPCサブネットのALB/NLB | 選択した公開/内部アプリケーション入口を提供。インターネットゲートウェイ/NATゲートウェイはそのルーティング設定の代わりにならない。 |
| NATゲートウェイまたはプライベートサービスエンドポイント | ワークロード設計に必要な個別の送信経路を提供。 |

以前の図はコントロールプレーンを顧客VPC内、ロードバランサーをその外に置いていました。この所有権の境界に置き換えました。

### コンピュートモードごとのDNSとネットワーク

| コンピュートモード | DNS / コンポーネントの配置 |
|---|---|
| 標準EC2ノード | 通常は設定済みCoreDNS Deploymentとインストール済みネットワークコンポーネントを使用。置き換えには対応する独自設定が必要。 |
| EKS Auto Modeのみ | CoreDNS、VPC CNI、kube-proxyの機能は、マネージドノードのsystemdサービスとして動作。これらのノードにCoreDNS Deployment/アドオンは不要。 |
| Auto Modeと非Autoノードの混在 | 非Autoノード用のCoreDNS Deploymentを保持。非Autoノードは別ノードのAuto Mode DNSサービスを使えない。 |

Auto Modeの最初のDNSリゾルバーはノードローカルです。上流への転送やコントロールプレーン通信では引き続きネットワークアクセスが必要な場合があり、すべてのDNS関連パケットがノード内に留まる保証ではありません。AWSはAuto ModeのAdminとDNS両方のポリシーを文書化し、標準EC2 VPC-CNIのAdminポリシーには独自のバージョン/有効化要件があります。

### VPC CNIの動作

AWS VPC CNIは、選択したIPAMモードで通常のPodにVPCでルーティング可能なアドレスを与えます。セカンダリIPv4アドレス、委任プレフィックス、ブランチENI、複数NIC構成は異なります。ホストネットワークPodはノードネットワークを共有します。

![オプションのウォームインターフェースを含む、EC2 ENIからPodへのセカンダリIPv4割り当ての例。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

これはセカンダリIPモードだけを示します。ウォームENIは設定可能な割り当て戦略であり、全ノードが常にちょうど1つ予約する要件ではありません。プレフィックス委任、カスタムネットワーキング、ブランチENIは割り当て規則が異なります。

#### ENIとIPの制限

| インスタンスタイプ | 最大ENI数 | ENIあたりIPv4スロット数 | 従来のセカンダリIPブートストラップ値 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

これらの値はVPC CNI 1.23.0のインスタンス制限と従来のmax-Pods表で確認しました。過去の計算は`ENIs × (IPv4 slots per ENI − 1) + 2`であり、現在の普遍的な推奨ではありません。プレフィックス委任、カスタムネットワーキング、ブランチENI、複数ネットワークカードはアドレス容量を変えます。Kubernetesのスケジューリングはkubeletの`maxPods`とリソースにも制限されます。EKSマネージドノードグループは、30 vCPU未満のインスタンスで`maxPods`を110、それ以外で250に制限します。使用可能IP数だけでこの上限は変わりません。

### EKSネットワーキングの考慮事項

#### IPアドレス管理

**Linux VPC CNI**では、選択したアドオン/Helm/DaemonSet管理の仕組みで文書化された環境変数を設定します。以下はEKSアドオン設定の断片です。`enable-prefix-delegation`を持つ旧`amazon-vpc-cni` ConfigMapでは、この方法でLinux IPAMDを設定できません。変更時は他の意図したアドオン値を保持してください。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

別の方法として、総割り当て下限と空きIP目標を調整できます。`MINIMUM_IP_TARGET`または`WARM_IP_TARGET`を設定すると`WARM_PREFIX_TARGET`より優先されます。これらは代替方針であり、4つの独立して加算される目標ではありません。割り当ては引き続きプレフィックス単位で行われます。Nitro対応、IPv4の連続した`/28`空間、適切なkubelet Pod上限は別の前提条件です。

Windowsのプレフィックス割り当ては別の設定方法です。AWSは`amazon-vpc-cni` ConfigMapの`enable-windows-prefix-delegation`とウォーム目標キーを文書化しています。Linuxの環境変数手順をWindowsにそのままコピーしないでください。

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

これらのIPv4例には、対象AZとVPCの実際のサブネット/セキュリティグループIDが必要です。カスタムネットワーキングを有効にし、各ノードのゾーンラベルでENIConfigを選択します。明示的なENIConfigノードアノテーションはそのラベルより優先されます。以下の例の名前は両言語で同じリージョンを使っています。実際のノードゾーンに置き換えてください。ENIConfigオブジェクトのインストールだけではカスタムネットワーキングは有効になりません。

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

## 高度なネットワーキング概念

以下の項目はこの概要の他の場所でも簡単に触れています。完全な設定手順と実測値はリンク先の詳細ページにあります。このセクションは、各要素がレイヤーによってどう異なり、どこに位置するかを整理します。

### L2–L7とルーターとロードバランサーの違い

「ルーター」と「ロードバランサー」は同じ文に登場しがちですが、判断する内容は異なります。ルーターは単一の宛先への経路を通常1つ選び、ロードバランサーは分散アルゴリズムで同等の候補から1つのターゲットを選びます。

| レイヤー | 機器/機能 | 判断基準 | Kubernetes/AWSでの対応 |
|---|---|---|---|
| L2（リンク） | スイッチ、ブリッジ | 宛先MACアドレス | CNIが作成するvethペアとLinuxブリッジ、ENIが公開する仮想NIC |
| L3（ネットワーク） | ルーターまたは透過的アプライアンス挿入 | ルーティングには宛先IP、アプライアンス選択にはフロー識別情報 | VPCの暗黙ルーター、TGW。GWLBはアプライアンス向けにIPパケットをカプセル化 |
| L4（トランスポート） | L4ロードバランサー | 接続/フロー識別情報、一般に5タプル | NLB、kube-proxy（iptables、IPVS、nftables）、別個のeBPF Service実装 |
| L7（アプリケーション） | L7ロードバランサー/リバースプロキシ | リクエストごとのホスト、パス、ヘッダー。プロトコルを認識 | ALB、Ingress/Gateway API実装、サービスメッシュのサイドカー（Envoy） |

重要な違いは**分散の単位**です。L4ロードバランサーは通常、TCP接続や追跡中のUDPフローごとにターゲットを選びます。L7プロキシは接続を共有するリクエストも含め、対応するアプリケーションリクエストごとに選択できます。GWLBはアプリケーションリクエストを解析せず、カプセル化されたIPフローをセキュリティアプライアンスに分散します。フローのスティッキネスは設定したタイムアウト、健全性、フェイルオーバー動作に依存し、フローが再割り当てや中断されない保証ではありません。

> 📎 L2/L3概念のプロトコルレベルの定義は[ネットワーク基礎 第1部](../basics/06-network-fundamentals-part1.md)、ALB/NLBのターゲットタイプと実際の設定は[AWS Load Balancer Controller](03-aws-lb-controller.md)を参照してください。

### アカウント間/VPC間接続: TGW、VPC Peering、GWLB、PrivateLink、Lattice

これら5つの接続方法は、レイヤーとトラフィックモデルが異なります。TGW RAM共有、VPC Peering、PrivateLink、TGW Peering、VPC Latticeの実測レイテンシーは[組織間VPC接続](05-cross-org-vpc-connectivity.md)にあります。このセクションはその比較表にないGWLBを追加し、5つをレイヤー別に整理し直します。

| 接続方式 | レイヤー/モデル | 特性 |
|---|---|---|
| VPC Peering | L3、双方向IPルーティング | 推移的ではなく、CIDRが重複する間では設定できない |
| Transit Gateway（TGW） | L3、ハブアンドスポークIPルーティング | 1つ以上のTGWルートテーブルでアタッチメントの関連付けと伝播を使用。RAMでアカウント間共有 |
| Gateway Load Balancer（GWLB） | L3、透過的なアプライアンス挿入 | 元パケットをGENEVE（UDP 6081）でカプセル化。VPCエンドポイントサービスモデルで利用者トラフィックを提供者のアプライアンス群へ接続 |
| PrivateLink | プライベートエンドポイント接続 | NLBをバックエンドとするエンドポイントサービスは1つのモデル。リソースエンドポイントも存在。利用者/提供者CIDRは重複可能 |
| VPC Lattice | アプリケーションとリソースのネットワーキング | HTTP/HTTPSサービスはL7ルーティングとオプションのIAM認可をサポート。TLSパススルーとリソース設定は機能が異なる |

GWLBはGateway Load Balancerエンドポイントを通じて、ファイアウォールやIDS/IPSなどの検査アプライアンスをIP経路に挿入します。デフォルトのフロースティッキネスは5フィールドを使い、対応設定では2つまたは3つにもできます。往路と復路、アプライアンスの健全性、カプセル化MTU、NACL、実際のワークロード/アプライアンスのセキュリティグループを検証します。GWLB自体にはALB型セキュリティグループがなく、フロースティッキネスは障害テストを代替しません。

> 📎 EKS/VPC Latticeの完全な統合（Gateway API Controller、IAM認可、ルーティング）は[VPC Lattice](02-vpc-lattice.md)を参照してください。

### DNSリゾルバーとルートテーブルの実際の動作

**DNSリゾルバー:** AmazonProvidedDNSは**Route 53 Resolverです**。アドレスにはプライマリVPC IPv4ネットワークアドレスに2を加えたもの（`10.0.0.0/16`なら`10.0.0.2`）と`169.254.169.253`が含まれ、Resolverルールに従って関連付けられたプライベートゾーンとパブリック名を解決します。CoreDNSは通常、設定されたKubernetesクラスタードメイン（多くは`cluster.local`）を提供します。`kube-dns`はService名であり、名前空間やDNSゾーンではありません。外部転送はCorefileとDNS Podから見えるリゾルバーファイルに従います。ノードのリゾルバーファイルがそのまま使われると想定せず、設定を確認してください。Resolverエンドポイント設計では、インバウンドエンドポイントがオンプレミスのクエリを受け入れ、アウトバウンドエンドポイントと関連ルールが選択したVPCクエリをオンプレミスDNSへ転送します。Auto Modeのノードローカルリゾルバーは上流依存をなくしません。

**ルートテーブル:** VPCの経路評価は通常、最長プレフィックス一致を使用します。AWSはアプライアンスルーティングのために`local`経路のターゲット置き換えと、サポートされるより具体的なサブネット経路の追加を許可します。`local`が無条件で最も具体的とは限りません。同じ宛先では、静的VPC経路が仮想プライベートゲートウェイから伝播した経路に優先します。TGWを対象とするVPC経路は静的です。TGW内の伝播は別のTGWルートテーブルに属します。無効ターゲットにより、トラフィックを破棄する`blackhole`エントリが残ることがあるため、宛先だけでなく経路状態も確認します。明示的なルートテーブル関連付けがないサブネットは、VPCのメインルートテーブルを使用します。

> 📎 TGW/Peeringの経路優先順位と静的経路設定例は[組織間VPC接続の運用上の知見](05-cross-org-vpc-connectivity.md#operational-findings)を参照してください。

### カーネルデータプレーン: iptables、IPVS、eBPF、パケットフィルタリング

LinuxのService転送とネットワークポリシー適用は、異なる仕組みを使う場合があります。Netfilterはiptablesとnftablesが使うパケット経路のフックを提供します。eBPF実装はXDP、tc、ソケットのフックに接続してService選択を行えます。これはeBPF有効クラスターの全パケットがNetfilterや接続追跡を迂回する意味ではありません。経路はCNI、カーネル、ルーティング、機能設定に依存します。

| 実装 | 位置 | 特性 |
|---|---|---|
| iptables | netfilterフック上の順次ルールチェーン | 評価時間はルール数に比例（O(n)）。kube-proxyの長年のデフォルトモード |
| IPVS | カーネルネイティブL4ロードバランサー、netfilter拡張 | ハッシュベース検索（ほぼO(1)）。Kubernetes 1.35からkube-proxyモードとして非推奨 |
| nftables | iptablesの後継となるnetfilterフレームワーク | 1.33からkube-proxyの安定モード。先にカーネル/CNI互換性を確認 |
| eBPF（例: Cilium） | 設定されたXDP、tc、ソケットフック | kube-proxyのService処理を置換可能。別実装で、Netfilter/conntrackの動作は経路固有 |

実装を切り替えると、カーネルルールや有効な接続が残る場合があります。ディストリビューション/CNIの移行手順に従い、必要に応じてワークロードをドレインし、クリーンアップに必要ならノード再起動を計画します。kube-proxyをeBPFベースCNIで置き換える場合も、同じServiceトラフィックを奪い合わないよう、サポートされる切り替え順序が必要です。

> 📎 IPVSの非推奨化時期とnftablesの安定版への移行は[Kubernetes入門](../basics/04-kubernetes-introduction.md)、CiliumのeBPF kube-proxy置換は[Cilium eBPF](cilium/02-ebpf.md)、CalicoのeBPFデータプレーンと移行手順は[Calico eBPF](calico/06-ebpf-dataplane.md)を参照してください。

### 計算集約型ネットワーキング: ENI、EFA、NVLink、光トランシーバー

ENI、EFA、NVLinkは異なる経路を担います。**ENI**は1つのAZのEC2インスタンスに接続する仮想ネットワークインターフェースです。通常のIP通信は、ルーティングとポリシーが許せば他AZや接続済みVPCに到達できます（[VPC CNI](01-vpc-cni.md)参照）。**EFA**は対応MPI/NCCLソフトウェアがlibfabric経由で使うOSバイパスデバイスを提供します。**EFAデバイストラフィックはルーティングできず、VPC/AZ境界を越えられません**。EFA-with-ENAインターフェースのENAデバイスによる通常のIP通信は引き続きルーティング可能です。EFA-onlyインターフェースにはENAデバイスもIPアドレスもありません。**NVLink**は対応するラック規模のNVLinkドメインを含む対応システム内でGPUを接続します。EFAより一定倍率速いと想定せず、選択したハードウェア、集合通信操作、配置を測定してください。

**光トランシーバー**は一般的なデータセンターネットワークの概念です。銅線DAC（Direct Attach Copper）ケーブルは短距離に適し、光モジュールとファイバーは他の距離/帯域要件を支えます。QSFPとOSFPはモジュール形状を表し、光媒体である保証ではありません。一般的な背景情報として扱ってください。特定AWSワークロードの物理配線を示すものではありません。

> 📎 NVLink/IMEXのトポロジーを考慮したスケジューリングとGPU Pod配置例は[AI/MLインフラ](../ai-ml/06-ai-infrastructure.md)、EFAのVPC/AZ境界制約と測定は[組織間VPC接続](05-cross-org-vpc-connectivity.md)を参照してください。

### 次世代プロトコルがKubernetesに意味すること: HTTP/3、gRPC、QUIC

HTTP/3（RFC 9114）とそのQUICトランスポート（RFC 9000）のプロトコルの仕組みは、[ネットワーク基礎 第2部](../basics/06-network-fundamentals-part2.md)と[第3部](../basics/06-network-fundamentals-part3.md)で扱います。ここではKubernetesのトラフィック分散に実際に影響する点だけを扱います。

- **gRPCとL4ロードバランサー:** gRPCはHTTP/2接続上でリクエストを多重化します。L4バランサーは通常、確立済みTCP接続を選択済みエンドポイントに保ちます。そのエンドポイントがプロキシなら、さらにルーティング判断できます。Podを追加するだけでは既存接続は再分散されません。RPCごとの分散には互換L7プロキシまたはクライアント側ポリシーが必要です。ストリーミングRPCは1回の呼び出しであり、個々のメッセージは独立に負荷分散されません。
- **Gateway APIのGRPCRoute:** IngressにはgRPC専用リソースがありませんが、Gateway APIは`GRPCRoute`でサービス/メソッド単位のルーティングを標準化します。ヘッダー一致数や再試行ポリシーなどのサポートは実装によるため、コントローラー自身の文書を確認してください。
- **HTTP/3/QUICがクラスター内のどこまで届くか:** クライアントとエッジ（CDN、ロードバランサー）間のHTTP/3対応は、クラスター内部やIngressのバックエンド接続のHTTP/3対応とは別問題です。多くのIngress/Gateway実装はバックエンドと引き続きHTTP/1.1またはHTTP/2で通信し、エンドツーエンドHTTP/3対応は実装とバージョンに依存します。一般化せず、実際に使うコントローラーの文書を確認してください。

## ネットワーキングのサブページ

このセクションでは以下のトピックを詳しく扱います。

### [VPC CNI](01-vpc-cni.md)
通常PodへのVPCアドレス付与と、モード固有のIPAM/ポリシー前提条件を持つEKSネットワーキング。

### [Cilium詳解](cilium/README.md)
高性能なeBPFベースCNIソリューション。L7ネットワークポリシー、サービスメッシュ、可観測性（Hubble）などの高度な機能を提供します。

### [Calico詳解](calico/README.md)
最も広く使用されるCNIの1つ。強力なネットワークポリシー、BGPサポート、エンタープライズ機能を備えます。入門、アーキテクチャ、ネットワークモード、BGP詳解、ネットワークポリシー、eBPF、高度なトピック、EKS統合、運用ガイドを扱います。

### [VPC Lattice](02-vpc-lattice.md)
AWSマネージドのアプリケーションネットワークサービス。VPC間、アカウント間のサービス間通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
Kubernetes ServiceとIngressをAWS ELB（ALB/NLB）と統合します。

### [Gateway API](04-gateway-api.md)
次世代Kubernetes Ingress API。標準化されたリソースモデルとロールベース設定。

### [Podネットワークベンチマーク](06-pod-network-benchmark.md)
EKSで同一ノード、同一AZ、AZ間のPod間RTT、HTTPレイテンシー、スループットと、DNSの`ndots:5`によるクエリ増幅を測定。

## ネットワークのトラブルシューティング

### よくある問題と解決方法

#### Pod間の通信失敗

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

指定ツールを備えた既存Podから診断を実行します。クラスターにインストールされたCNIだけを照会してください。Auto ModeシステムサービスはこれらのDaemonSetではありません。DNS成功、TCP到達性、アプリケーションHTTP応答は別の確認です。ICMPは遮断されるか追加権限が必要な場合があるため、ping失敗だけでTCPサービスが到達不能とは証明できません。

#### Serviceに到達できない

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

現在のエンドポイント診断にはEndpointSliceを使用します。Serviceセレクター、ターゲットポート、エンドポイントの準備状態、アドレスファミリー、該当ポリシーを確認します。kube-proxyログは、そのコンポーネントが実際にService転送を担当する場合だけ調べます。eBPFによる置換やAuto Modeでは独自の診断が必要です。

#### ネットワークポリシーのデバッグ

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

CiliumコマンドはDaemonSet参照で選択された1つのAgentを調べます。障害追跡では影響ノードのAgentを選んでください。CalicoネイティブAPIのインストールでは異なるAPIグループが公開されることがあるため、そのインストールが提供するリソースを確認します。Kubernetes、Calico、AWS拡張ポリシーは別リソースで、優先順位も異なる場合があります。

### ネットワーク性能テスト

この制限付きTCP演習は、配布元が固定したNetshoot v0.16イメージインデックスを使用します。Linux AMD64とArm64イメージを含み、Dockerfileには`iperf3`があります。TCP 5201が許可されたテスト環境にPodを作成してください。説明用ワークロードであり、実測CNI比較ではありません。

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

クライアントは1時間スリープし、コマンドは送信トラフィックを10 Mbit/s、10秒間に制限します。選択した経路のテストであり、最大スループットの測定ではありません。結果を解釈する前に、実際のPod/ノード/AZ配置、リソース制限、ポリシーを記録します。WindowsノードにはWindows専用ツールを選択してください。終了時は作成したテストリソースだけを削除します。

これらの単独診断Podは接続テスト用です。ネイティブEKSネットワークポリシーの適用テストにはDeployment/Job管理Podを使い、文書化されたService/コンテナポート要件に従ってください。

## ベストプラクティス

### 1. IPアドレス計画

- 十分に大きなCIDRブロックを設計
- PodネットワークとServiceネットワークを分離
- 将来の拡張を考慮してサブネットを設計

### 2. ネットワークポリシーの適用

例を使用する前に、隔離された`networking-demo`名前空間を作成します。標準Kubernetes NetworkPolicyの意味に従って、その中の全Podを選択し、IngressとEgress両方を分離します。必要なDNSとアプリケーションの通信には明示的な許可ルールが必要です。適用には対応ポリシーエンジンが必要です。追加のクラスター/AdminポリシーAPIは優先順位を変える場合があり、この1つのマニフェストは完全なゼロトラスト構成ではありません。

- デフォルト拒否ポリシーを適用（ゼロトラスト）
- 必要なトラフィックだけを明示的に許可
- 名前空間を分離

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

### 3. 性能最適化

- 適切なCNIを選択（ワークロードに合わせる）
- MTUの最適化
- カーネルパラメーターの調整

### 4. セキュリティ強化

- サポートされる転送暗号化を選び、対象トラフィックを確認する。
- 必要に応じてワークロード/アプリケーションIDとmTLSを設定し、DNS/IPベースの許可リストとは分けて扱う。
- ポリシー、証明書、アクセス制御の変更を定期的に確認する。

### 5. 可観測性の確保

- ネットワークメトリクスを収集
- フローログを有効化
- 分散トレーシングを実装

## 次のステップ

1. [VPC CNI](01-vpc-cni.md) - EKSのデフォルトCNI
2. [Cilium詳解](cilium/README.md) - eBPFベースのネットワーキング
3. [Calico詳解](calico/README.md) - ルーティング、ポリシー、データプレーン
4. [VPC Lattice](02-vpc-lattice.md) - AWSマネージドネットワーキング
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB統合
6. [Gateway API](04-gateway-api.md) - 次世代Ingress
7. [組織間VPC接続](05-cross-org-vpc-connectivity.md) - AWS Organizations間のVPC接続（現場検証済み）
8. [Podネットワークベンチマーク](06-pod-network-benchmark.md) - ノード/AZ境界ごとの実測レイテンシーとスループット

---

## 参考資料

- [Kubernetesネットワークモデル](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Service](https://kubernetes.io/docs/concepts/services-networking/service/)
- [コンテナランタイムとCNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI仕様](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calicoの製品エディション](https://docs.tigera.io/calico/latest/about)
- [CalicoのポリシーTier](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whiskerフローログ](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [CalicoのWindows制限](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9のネットワーキングとポリシー](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannelバックエンド](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [元のWeaveリポジトリの状態](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [EKSネットワークポリシー設定](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS標準およびAdminネットワークポリシー](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKSプレフィックス委任とmaxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS AdminおよびDNSポリシーのデプロイモデル](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Modeネットワーキング](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKSアドオン要件](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKSコントロールプレーンのアーキテクチャ](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16イメージメタデータ](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragonランタイムセキュリティ](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB設定](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress設定](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancerの概念](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVEカプセル化（RFC 8926）](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNSリゾルバー](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolverのエンドポイントとルール](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPCルートテーブルの評価順序](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [ローカル経路とより具体的なサブネット経路](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [静的経路と伝播経路の優先順位](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNSのアドレスと動作](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLBフロースティッキネスとフェイルオーバー](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service仮想IPとkube-proxyモード](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service名と転送設定](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLinkリソースエンドポイント](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptablesプロジェクトのドキュメント](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUICトランスポートプロトコル（RFC 9000）](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3（RFC 9114）](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC over HTTP/2と負荷分散](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
