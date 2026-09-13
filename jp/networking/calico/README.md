# Calico詳解: Kubernetesネットワーキングとポリシー

> **レビュー基準**: Calico Open Source 3.32.2 · **最終更新**: September 12, 2026
> Calico 3.32はKubernetes 1.34–1.36でテストされています。上限のない`3.29+ / Kubernetes 1.28+`の互換性保証ではありません。

## 概要

CalicoはKubernetesのネットワーキングとネットワークポリシーを提供し、デプロイや製品エディションに応じてホスト/VM機能も提供します。このシリーズはアーキテクチャ、カプセル化とルーティング、BGP、ポリシー、eBPF、EKS統合、運用を扱います。日付のない成熟度やリソース使用量の順位ではなく、[現在の要件](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)に基づいて構成を選んでください。

### 2026年7月: Kubernetes上のVM向けCalico

Tigeraの[公式発表](https://www.tigera.io/news/tigera-launches-ebpf-powered-calico-for-vms-on-kubernetes-vm-migration-that-doesnt-require-rebuilding-the-network/)の日付は**July 23, 2026**です。VMware移行向けのVM/コンテナネットワーク、IP継続性、L2ブリッジ拡張、ポリシー、可観測性を説明しています。製品発表であり、広告された全機能がCalico Open Sourceに含まれる約束ではありません。正確なエディション、トポロジー、機能状態を確認してください。[Enterprise 3.23リリースノート](https://docs.tigera.io/calico-enterprise/latest/release-notes/)ではKubeVirtライブマイグレーションはまだ技術プレビューです。マーケティング上の提供開始は、その機能固有の制限をなくしません。

## 互換性と機能の境界

- Calico 3.32.2はAugust 30, 2026にリリースされました。テスト済みKubernetesマイナーバージョンは1.34、1.35、1.36です。Kubernetes 1.37が利用可能でも互換性は成立しません。
- 一般的なLinux要件はカーネル5.10以降と必要モジュールです。対応アーキテクチャ、ベンダーのバックポート、個別機能のより高い要件はeBPFガイドを確認してください。
- Linuxデータプレーンにはiptables、nftables、eBPFがあります。デフォルトはインストーラー/プラットフォーム次第で、現在の自己管理kubeadm OperatorインストールはeBPFがデフォルトになる場合があります。一律の機能同等性保証はありません。
- [Calico for Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)は指定IPv4 VXLAN/BGP構成をサポートしますが、Linux eBPF、IPIP、IPv6/デュアルスタック、WireGuard、全Linuxポリシー機能はサポートしません。
- Open SourceにはTier付きポリシー、Goldmaneフロー集約、Whisker UIがあります。DNS/FQDNポリシー、アプリケーション層ポリシーなどの高度な機能には、[製品比較](https://docs.tigera.io/calico/latest/about/calico-product-editions)に示すエディション境界があります。

## CalicoとCilium

| 要件 | Calico | Cilium |
|---|---|---|
| Linuxデータプレーン | 設定に応じてiptables / nftables / eBPF | eBPF、該当L7機能にEnvoy |
| Kubernetes NetworkPolicy | サポート。加えてCalicoポリシーとTier | サポート。加えてCiliumポリシー |
| L7 / DNSポリシー | Enterprise/Cloudのライセンスと機能状態を確認 | HTTP/DNSポリシーを提供。プロトコル固有制限あり |
| BGP | 該当ネットワークモードでBIRDベースのルーティング | BGPコントロールプレーン広告。必要経路とトポロジーを評価 |
| 可観測性 | Open SourceのGoldmane/Whiskerとメトリクス。有料機能で追加 | Hubbleとメトリクス |
| Windows | 対応構成に大きな制限あり | Cilium 1.20エージェントはLinux必須。Windowsベータ版データプレーンではない |
| kube-proxy置換 | eBPFデータプレーンで利用可能 | 設定時に利用可能 |
| マルチクラスター / メッシュ | 別の機能や統合。エディション依存 | Cluster Meshとオプションのサービスメッシュ機能。インストールだけで全機能は有効にならない |

両方とも本番の選択肢になります。リソース使用量と運用の複雑さはルール、通信、プラットフォーム、調整に依存します。対象環境で必要機能を検証してください。別環境で動作するからといって1つのクラスターに主要CNIを2つインストールしないでください。Ciliumの[バージョン付き要件](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)と本サイトの[Ciliumサービスメッシュガイド](../../service-mesh/cilium-service-mesh/README.md)が、プラットフォームとメッシュの境界を説明します。

## アーキテクチャ

![Kubernetesデータストア、任意のTypha、Felix、confd、BIRDを持つCalico BGPデプロイの概略。](../../.gitbook/assets/en-networking-calico-readme-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-readme-0.html)

図はBGPデプロイの概略で、必須のコンポーネント配置ではありません。以下のEKSポリシー専用例はKubernetesデータストアを使い、BIRD/confdを省略します。「コントロールプレーン」は論理的役割を示し、EKS管理コントロールプレーンマシンへの配置ではありません。Typhaはノードごとのプロセスでなく、独立Deploymentです。

| コンポーネント | 役割と範囲 |
|---|---|
| Felix | ワークロードノードにポリシーと該当経路を設定 |
| BIRD / confd | バックエンド有効時のBGPとその設定。ポリシー専用モードにはない |
| Typha | 任意のデータストア更新キャッシュ/配布。Operatorがインストールに合わせてレプリカを調整し、必ず3ではない |
| kube-controllers | Kubernetesリソースの調整、同期、クリーンアップ |
| Calico CNI / IPAM | Calicoがネットワークを担当する場合のインターフェースとPodアドレス管理。EKS例ではAmazon VPC CNI/IPAMが担当を維持 |
| Calico APIサーバー | デフォルトモデルで内部CRD上に集約`projectcalico.org/v3` APIを提供。ネイティブv3 CRDは別の技術プレビュー |

[アーキテクチャリファレンス](https://docs.tigera.io/calico/latest/reference/architecture/overview)と実際のレンダリング済みワークロードで、有効なコンポーネントを特定します。このガイドはKubernetes APIデータストアを使い、etcdベース設計には別のインストール/機能制約があります。

## ネットワーキングモードとMTU

| モード | カプセル化とルーティング | 1500バイトIPv4アンダーレイでのPod MTU例 |
|---|---|---|
| IPIP | IPv4-in-IPv4、通常はBGP経路配布と併用 | 1480 |
| VXLAN | デフォルトUDP 4789。VXLAN PodルーティングにBGPは不要 | 1450 |
| 非カプセル化 | アンダーレイにPodアドレスの経路が必要。BGPは配布方法の1つ | 1500 |
| CrossSubnet | ノードサブネット間だけカプセル化するIPIP/VXLAN設定 | 必要な経路向けのトンネルオーバーヘッドを引き続き確保 |

これらのMTUは例で、普遍的な定数ではありません。IPv6 VXLANオーバーヘッド、ジャンボアンダーレイ、WireGuard、クラウド経路制限で計算は変わります。IPIPはIPv4専用で、IPv4 VXLANはIPIPが不適切な場所でも使えます。[MTU設定](https://docs.tigera.io/calico/latest/networking/configuring/mtu)と[オーバーレイ要件](https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip)を確認してください。BGPが利用できるだけでは、全アンダーレイホップがPod CIDRをルーティングできる証明になりません。同一L2隣接は非カプセル化ルーティングファブリックの普遍的前提条件ではありません。モード選択前にアンダーレイ、ポート、アドレスファミリー、プラットフォームを計画します。

## EKS: Amazon VPC CNIを保持してCalicoポリシーを追加

この例は、サポート対象のAmazon VPC CNIがインストール済みのLinux EC2ノード向けです。Podネットワークは置き換えません。Auto ModeやFargateのインストール手順ではありません。[公式EKSガイド](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)は次を要求します。

1. Calicoをポリシーエンジンに選ぶ前にAmazon VPC CNIのネイティブネットワークポリシー適用を無効にします。両方動かすと競合します。保護済みの既存クラスターでは、無保護な移行を生じさせず、ポリシーの引き継ぎを計画・検証します。
2. VPC CNIの`ANNOTATE_POD_IP=true`を設定し、`aws-node` ServiceAccountにPodへの`patch`アクセスを付与します。調整で戻されないよう、インストール済みアドオン/設定所有者を通じて管理します。以下の追加的RBAC例を適用する前に、実際のServiceAccount名を確認します。
3. `ENABLE_V4_EGRESS=true`のIPv6 Podを対象とするとは主張しないでください。Calico EKSガイドはこの組み合わせでの適用を明示的に除外します。
4. 以下のインストール方法を**1つ**選びます。新規インストール例であり、既存Operatorの引き継ぎや稼働中CNIの移行コマンドではありません。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-ip-patch
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-ip-patch
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-ip-patch
subjects:
  - kind: ServiceAccount
    name: aws-node
    namespace: kube-system
```

### 方法A: バージョン固定のOperatorマニフェスト

```bash
set -euo pipefail
CALICO_VERSION=v3.32.2
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/v1_crd_projectcalico_org.yaml"
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml"
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=300s
kubectl apply -f - <<'YAML'
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
    linuxDataplane: Iptables
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
```

### 方法B: バージョン固定のHelmインストール

同じVPC CNI前提条件を完了してください。Calico 3.32はCRDインストールをOperatorチャートから分離しており、小さなOperatorチャートだけでは新規クラスターに不十分です。次のvaluesを`calico-eks-values.yaml`として保存します。

```yaml
installation:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
apiServer:
  enabled: true
```

```bash
set -euo pipefail
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico-crds projectcalico/crd.projectcalico.org.v1 --version v3.32.2   | kubectl apply --server-side -f -
helm install calico projectcalico/tigera-operator --version v3.32.2   --namespace tigera-operator --create-namespace -f calico-eks-values.yaml
```

固定したチャートはGoldmaneとWhiskerもデフォルトで有効にします。レンダリング済みマニフェストでコンポーネントとアクセス制御を確認してください。ネイティブ`projectcalico.org/v3` CRDは別の技術プレビューで、ここでは従来の内部CRDと集約APIサーバーを使います。

### 確認後にポリシー動作をテスト

```bash
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl get felixconfigurations.projectcalico.org
```

degraded/progressing状態を調べ、適用を信頼する前に使い捨てワークロードで許可/拒否両方の通信をテストします。ReadyなDaemonSetはポリシーの証明ではありません。AmazonVPCポリシー専用モードでは、Calico IPPoolが空、BIRDセッションがないという状態は必ずしも障害ではありません。AWSがPod IPAMとネットワークを引き続き提供します。

### 完全Calicoネットワーキングと他のインストール方法

EKSの完全Calicoネットワーキングは別の新規クラスター設計です。公式手順はワークロードノードなしで開始し、ノード追加前にCNIを変更します。稼働中VPC CNIクラスターに`cni.type: Calico`断片を適用しないでください。[EKS統合](08-eks-integration.md)と公式EKS手順を参照してください。既存CNIがない自己管理クラスターには[オンプレミスガイド](https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises)を使います。直接マニフェストも代替手段ですが、名前空間、Typha設定、ライフサイクルがOperatorインストールと異なります。Helm、Operator、`calico.yaml`インストールを重ねず、所有者を1つ選んでください。

## 範囲を明示したポリシー例

専用の`calico-demo`名前空間を使用します。以下のIngress/Egress例はその名前空間だけを選択し、クラスター全体のゼロトラスト導入ではありません。既存Calico Tierや先行ポリシーで結果が変わる場合があります。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: calico-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

ピアの`podSelector`は**同一名前空間**のフロントエンドPodを意味します。ユーザー認証、同一名前空間の全通信許可、Egressポリシー設定はしません。次の独立例は、デモ名前空間のEgressを選択したCoreDNS PodのUDP/TCP 53に制限し、他のEgressを拒否します。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-dns-only
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: all()
  order: 100
  types: [Egress]
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
    - action: Deny
```

先に実DNSエンドポイントとラベルを確認します。このセレクターベース例は通常CoreDNS Podが対象で、NodeLocal DNSCacheやAuto Modeのシステムリゾルバーポリシーではありません。ポート53だけでは認可されたDNSサーバーを識別できません。アプリケーションEgressも必要なら、最後の拒否を有効にする前に明示許可を設計・テストします。後続の別Allowは、一致した先行Calico Denyを上書きできません。

### FQDNポリシーはエディション固有

Calico Enterprise/Cloud DNSポリシーの`destination.domains`フィールドは、**Open Source 3.32.2 NetworkPolicyスキーマにありません**。このOpen Sourceインストールに適用しないでください。利用権のあるデプロイでは[ドメインベースポリシーガイド](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy)に従い、信頼するDNSサーバーを設定しDNS経路を許可します。ドメインは意図的に制限してください。`*.amazonaws.com`は広範な許可で、1つのAWSアカウントやサービスへの認可ではありません。DNSからIPへの認可はHTTP HostやTLS IDの検証と同等ではありません。

## 監視と健全性

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
```

Felixのメトリクスはデフォルトで無効です。このリスナーを有効にしてもPrometheusスクレイプジョブは作られず、公開して安全になるわけでもありません。[メトリクスガイド](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)で非公開の検出とアクセス制御を設定します。`flowLogsFileEnabled`はOpen SourceのFelixConfigurationフィールドではありません。Enterpriseファイルログ設定をコピーせず、対応する[Goldmane/Whiskerフローログ経路](https://docs.tigera.io/calico/latest/observability/view-flow-logs)を使ってください。

| メトリクス | 意味 |
|---|---|
| `felix_active_local_endpoints` | 有効なローカルワークロード/ホストエンドポイント |
| `felix_active_local_policies` | このノードのエンドポイントで有効なポリシー |
| `felix_iptables_rules` | 有効なiptablesルール。データプレーン固有 |
| `felix_int_dataplane_failures` | 再試行されるデータプレーン更新失敗 |
| `felix_cluster_num_hosts` | Felixのクラスター全体ホスト数。全Felixインスタンスで合計しない |
| `typha_connections_accepted` | 累積の受け入れ接続数。現在の接続数ではない |
| `typha_connections_active` | 現在開いているクライアント接続 |

[Felix](https://docs.tigera.io/calico/latest/reference/felix/prometheus)と[Typha](https://docs.tigera.io/calico/latest/reference/typha/prometheus)のメトリクスリファレンスを参照してください。コンポーネントの健全性/設定メトリクスで、汎用の拒否パケットカウンターではありません。Felixヘルスのデフォルトはlocalhost:9099、Typhaヘルスは有効時に通常9098を使います。確認前にデプロイ済みプローブを読んでください。ノートPCの`curl localhost`はノードのヘルスサーバーを調べません。

## トラブルシューティング

```bash
kubectl -n calico-system get pods -o wide
kubectl -n calico-system logs -l k8s-app=calico-node -c calico-node --tail=100
kubectl get installations.operator.tigera.io default -o yaml
kubectl get networkpolicies.networking.k8s.io -A
kubectl get networkpolicies.projectcalico.org -A
kubectl get globalnetworkpolicies.projectcalico.org
kubectl get ippools.projectcalico.org -o wide
```

Operatorインストールは通常`calico-system`、直接マニフェストは`kube-system`を使う場合があります。KubernetesとCalicoのNetworkPolicyを区別するため完全修飾APIリソース名を使います。`kubectl get nodes ...status.conditions`はCalicoルーティング状態コマンドではありません。BIRD状態コマンドはBGP有効時のみ適用され、`calicoctl node status`には任意の管理者ノートPCでなく適切なCalicoノード環境が必要です。

| 症状 | 設定変更前の調査 |
|---|---|
| PodにIPがない | 先にIPAM担当を特定。ポリシー専用EKSならVPC CNIログ/容量、それ以外はCalico IPAM |
| ノード間の障害 | 経路、アンダーレイ/ファイアウォール権限、MTU、選択したカプセル化。無条件なトンネル有効化は障害を悪化させ得る |
| ポリシー不一致 | エンドポイントラベル、名前空間、方向、Tier/順序、既存ポリシー、実データプレーン |
| CPU高負荷 | 通信/ルール規模とメトリクス/プロファイルの証拠。eBPF移行は計画された変更で、即時の汎用修正ではない |

必要時だけ対応バージョンの[calicoctl](https://docs.tigera.io/calico/latest/reference/calicoctl/)を使い、実際のOS/CPUアーキテクチャを選んでリリース成果物を検証します。BGPやCalico IPAM状態がないことだけでポリシー専用モードの障害を推定しないでください。

## 詳解の内容

| 部 | トピック |
|---|---|
| [1](01-introduction.md) | 入門、プロジェクト史、演習環境設定 |
| [2](02-architecture.md) | コンポーネント、データストア、パケットフロー |
| [3](03-networking-modes.md) | カプセル化、直接ルーティング、MTU |
| [4](04-bgp-deep-dive.md) | BGP、ルートリフレクター、外部統合 |
| [5](05-network-policy.md) | NetworkPolicy、Tier、ポリシー設計 |
| [6](06-ebpf-dataplane.md) | eBPF設定、制限、トラブルシューティング |
| [7](07-advanced-topics.md) | 高度なネットワーク/セキュリティトピック |
| [8](08-eks-integration.md) | EKSとVPC CNIの統合 |
| [9](09-operations.md) | 運用と診断 |
| [用語集](glossary.md) | 用語 |

[Calico入門クイズ](../../quizzes/networking/calico/01-introduction-quiz.md) · [公式ドキュメント](https://docs.tigera.io/calico/latest/about/) · [リリース3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2)
