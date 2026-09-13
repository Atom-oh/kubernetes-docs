# 第1部: Calico入門

> **レビュー基準**: Calico Open Source 3.32.2、kind 0.33.0、Kubernetes 1.36.4
> **最終更新**: September 12, 2026。Calico 3.32はKubernetes 1.34–1.36でテストされています。

## 演習環境

この使い捨てのローカル演習では、iptables、VXLAN、Calico IPAMを明示的に選択します。既存CNIの置換やEKSの設定はしません。監査では公開成果物と設定を確認しましたが、クラスターの作成や実際の通信テストは行っていません。

| ツール/環境 | 要件 |
|---|---|
| kind | 0.33.0。固定されていないデフォルトを使わず、以下の1.36.4イメージに固定 |
| Docker | kindノード3台分の容量がある、サポート対象で動作するランタイム |
| ノードOS | [Calico要件](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)を満たすLinuxカーネル/モジュール。macOSではコンテナVMのカーネル |
| kubectl | APIサーバー1.36から1マイナー以内。対応する1.36クライアントが便利 |
| calicoctl | 任意。実際のCLIホストOS/アーキテクチャに対応する3.32.2クライアント |
| curl / Python 3 | 以下の任意のクライアントダウンロードとSHA-256検証用 |
| Helm | [概要](README.md)の任意の代替手段。この演習では不要 |

[Kubernetesのバージョンスキューポリシー](https://kubernetes.io/releases/version-skew-policy/)は、任意の`kubectl 1.28+`とすべての後続サーバーの組み合わせをサポートしません。作成前にPod/Service CIDRがコンテナネットワーク、ホストLAN、VPNと重複しないか確認してください。

### オプション: 対応するcalicoctl

プラットフォームを1つ選び、該当リリースアセットの公開ダイジェストを確認し、バイナリを演習ディレクトリに置きます。これらのコマンドはグローバルインストールやホームディレクトリの設定を必要としません。

```bash
set -euo pipefail
CALICO_VERSION=v3.32.2
case "$(uname -s)" in
  Linux) CALICO_OS=linux ;;
  Darwin) CALICO_OS=darwin ;;
  *) echo "Select a supported calicoctl OS" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) CALICO_ARCH=amd64 ;;
  aarch64|arm64) CALICO_ARCH=arm64 ;;
  *) echo "Select a supported calicoctl architecture" >&2; exit 1 ;;
esac
CALICO_ASSET="calicoctl-$CALICO_OS-$CALICO_ARCH"
curl --fail --location --retry 3 \
  "https://api.github.com/repos/projectcalico/calico/releases/tags/$CALICO_VERSION" \
  --output calico-release.json
curl --fail --location --retry 3 \
  "https://github.com/projectcalico/calico/releases/download/$CALICO_VERSION/$CALICO_ASSET" \
  --output calicoctl
python3 - "$CALICO_ASSET" <<'PY'
import hashlib
import json
import pathlib
import sys

release = json.loads(pathlib.Path("calico-release.json").read_text())
if release["tag_name"] != "v3.32.2":
    raise SystemExit("Unexpected release")
asset = next(a for a in release["assets"] if a["name"] == sys.argv[1])
expected = asset.get("digest") or ""
actual = "sha256:" + hashlib.sha256(pathlib.Path("calicoctl").read_bytes()).hexdigest()
if not expected.startswith("sha256:") or actual != expected:
    raise SystemExit("Digest mismatch or missing published digest")
print("Verified", asset["name"], actual)
PY
chmod +x calicoctl
./calicoctl --help
```

演習のデータストア設定後に`./calicoctl version`を実行し、クライアントとクラスター情報を確認します。文書化された`version`コマンドに`--client`フラグはありません。集約APIサーバーの準備ができれば`kubectl`でもCalicoリソースを管理でき、すべての操作でcalicoctlが必須ではありません。

### 独立したkindクラスターの作成

未使用のクラスター名と新しいローカルkubeconfigを使用します。[kind 0.33.0リリース](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0)は、Calicoのテスト済みマイナー範囲内にあるこの1.36.4イメージを公開しています。レジストリのダイジェストとamd64/arm64マニフェストは確認しましたが、監査でノードイメージのレイヤーはダウンロードしていません。

```bash
set -euo pipefail
CALICO_LAB_KUBECONFIG="$PWD/calico-lab.kubeconfig"
test ! -e "$CALICO_LAB_KUBECONFIG"
cat > kind-calico.yaml <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  disableDefaultCNI: true
  kubeProxyMode: iptables
  podSubnet: 10.244.0.0/16
nodes:
  - role: control-plane
  - role: worker
  - role: worker
YAML
kind create cluster --name calico-lab --config kind-calico.yaml \
  --kubeconfig "$CALICO_LAB_KUBECONFIG" \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed
export KUBECONFIG="$CALICO_LAB_KUBECONFIG"
export DATASTORE_TYPE=kubernetes
kubectl config current-context
kubectl cluster-info
```

CNIインストールまではノードと通常のPodが準備未完了のままになる場合があります。解消のために第2のCNIをインストールしないでください。Pod CIDRが競合する場合、クラスター作成前にkindとInstallationの両方で変更します。

```bash
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
  kubernetesProvider: Kind
  cni:
    type: Calico
  calicoNetwork:
    linuxDataplane: Iptables
    bgp: Disabled
    ipPools:
      - cidr: 10.244.0.0/16
        blockSize: 26
        encapsulation: VXLAN
        natOutgoing: Enabled
        nodeSelector: all()
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
```

Operatorが作成するワークロードが現れるまで待ち、ロールアウトと条件を確認します。ラベル選択結果が空であることや、1つのコントローラーの可用性だけでは、全ノードのネットワークが動作する証明になりません。

```bash
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl -n calico-system rollout status deployment/calico-kube-controllers --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl wait --for=condition=Ready nodes --all --timeout=300s
kubectl get ippools.projectcalico.org -o wide
kubectl get installations.operator.tigera.io default -o yaml
# Optional, if the matching local client was downloaded:
./calicoctl version
./calicoctl get nodes
```

ここではBGPを無効にしているため、BIRDセッションと`calicoctl node status`は準備完了の基準ではありません。このコマンドには、ノートPCのkubeconfigだけでなく適切なノード環境も必要です。実際のコンポーネント数を観察してください。CSI/Typhaのレプリカ数は固定ではありません。使い捨てワークロードでPod、Service、DNS接続と、ポリシーで許可/拒否される両方の通信を確認します。

## Calicoが提供するもの

CalicoはKubernetesネットワーキング、IPAM、ポリシー適用を組み合わせます。ポリシー専用の統合では、別のCNIがネットワーキングとIPAMを担当します。機能はOS、データプレーン、製品エディションによって異なり、プラットフォーム一覧への掲載は同一動作を保証しません。

## プロジェクトの歴史とガバナンス

Project Calicoは2014年にMetaswitchで始まり、2016年設立のTigeraが主なメンテナーです。以下のリリース記録は以前の3.0/3.29の日付を訂正し、最初のeBPFプレビューと後の機能提供を区別します。

| 日付 | 一次リリース記録 |
|---|---|
| December 21, 2017 | [Calico 3.0.0](https://github.com/projectcalico/calico/releases/tag/v3.0.0)。過去のリリースでありインストール推奨ではない |
| February 25, 2020 | [eBPFの導入](https://www.tigera.io/blog/introducing-the-calico-ebpf-dataplane/)。GAではなく**3.13の技術プレビュー**として発表 |
| October 29, 2024 | [Calico 3.29.0](https://github.com/projectcalico/calico/releases/tag/v3.29.0) |
| August 30, 2026 | [Calico 3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2)。このレビューの基準 |

旧年表の「eBPFの完全な機能同等性」と「Windows eBPF」という主張は誤りでした。現在の[Windowsの制限](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)でも、Linux eBPF、IPIP、IPv6/デュアルスタック、WireGuardは対象外です。

CalicoはApache-2.0ライセンスを採用し、Tigeraとコミュニティが保守します。CNCF Landscapeへの掲載は、CNCFの所有、インキュベーション、卒業を意味しません。Enterpriseは商用の自己管理製品、CloudはSaaSです。Open Sourceは小規模や非本番クラスターに限定されません。

![Calicoのエコシステムと商用製品の関係。](../../.gitbook/assets/en-networking-calico-01-introduction-4.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-01-introduction-4.html)

CNCFのボックスはLandscape/エコシステムへの参加のみを表します。Tigeraは製品に加えてオープンソースプロジェクトも保守します。図のグループ化がCNCFにガバナンス権限を与えるわけではありません。

## 主な機能

### 1. ネットワーキングとデータプレーン

カプセル化と実装は別の選択です。CalicoはIPIP、VXLAN、ルーティングされたアンダーレイを使えます。CrossSubnetは条件付きIPIP/VXLAN設定で、WAN接続サービスではありません。Linuxデータプレーンにはiptables、nftables、eBPFがあります。eBPFは**カーネル内部**で動作し、従来のパケット処理経路の一部を迂回できますが、カーネルを迂回するわけではありません。非カプセル化ルーティングでトンネルヘッダーを避けられるのは、アンダーレイに必要なPod経路がある場合だけで、全ワークロードの最小レイテンシーを保証しません。

### 2. KubernetesとCalicoのポリシー

Kubernetes NetworkPolicyは名前空間単位で、加算的です。Calicoは明示的アクション、順序付きポリシー、Tierを追加し、TierはOpen Sourceにも含まれます。GlobalNetworkPolicyはクラスターリソースのスコープを持ちますが、1つの名前空間を選択できます。HostEndpointは保護するホストエンドポイントを記述し、固定階層でNetworkPolicyの下にある第3のポリシータイプではありません。

これらは専用名前空間での**独立した例**です。既存Tierと高優先度ポリシーを考慮してください。どちらも完全なセキュリティ基準ではありません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: calico-demo
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress: []
```

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-trusted-ingress
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'backend'
  order: 100
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
        selector: trusted == 'true'
      destination:
        ports: [8080]
    - action: Deny
```

Calicoの例は、デモ名前空間内の一致するエンドポイントから選択したバックエンドへのTCP 8080を許可し、他のIngressを拒否します。ラベル書き込み権限を保護してください。`trusted`は暗号学的なIDではありません。これらの例はEgressやDNSを設定しません。CIDR/ポートルールは使えますが、大きなプライベートCIDRはID境界ではありません。DNS/FQDNとアプリケーション層のポリシーには適切なEnterprise/Cloud機能が必要です。[エディション表](https://docs.tigera.io/calico/latest/about/calico-product-editions)を参照してください。

### 3. IPアドレス管理

CalicoがIPAMを担当する場合、プールとブロックが割り当てを制御します。IPv4 /26ブロックは64アドレスを含みますが、どのプラットフォームでも64個のPodアドレスを使用できる保証ではありません。Windowsはアドレスを予約し、IPv6はデフォルトが異なります。VPC CNIのポリシー専用モードではAWSがIPAMを担当します。

これは[IPPool API](https://docs.tigera.io/calico/latest/reference/resources/ippool)の例です。**重複するOperator管理プールと並行して作成しないでください。** kind演習にはすでにプールがあります。カプセル化/IPAM変更は別の計画された演習です。

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: example-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
```

重複しない複数プールとノードセレクターで割り当てを分離できます。`natOutgoing`は通常、Calicoプールを出る通信に適用され、ファイアウォールや暗号化設定ではありません。直接ルーティングもCrossSubnetも、アンダーレイ設計なしに拠点間を接続しません。

### 4. BGPルーティング

BGPは経路を配布します。アプリケーションパケットはBIRDプロセスを通らず、BGPは暗号化もしません。BGPは直接ルーティングを支援し、IPIPとも共存できます。フルメッシュ、ルートリフレクター、外部ピアはトポロジーの選択肢です。

以下は**別のルーティング演習**用で、BGP無効のkind例には属しません。文書用アドレス、ASN、ノードラベルを、設計したトポロジーと対応ルーター設定に置き換えます。代替の経路配布が動作する前にノードメッシュを無効にしないでください。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: example-rack-tor
spec:
  peerIP: 192.0.2.1
  asNumber: 64513
  nodeSelector: rack == 'rack-1'
```

BGPPeerはセッション認証に`password.secretKeyRef`をサポートします。SecretはCalicoノードコンポーネントの名前空間に置き、ルーターも一致する認証情報を使用する必要があります。ワークロードトラフィックは暗号化されません。Service-CIDR広告とメッシュ削除には追加テストが必要です。[BGP詳解](04-bgp-deep-dive.md)を参照してください。

### 5. プラットフォームと規模の境界

| 環境 | 境界 |
|---|---|
| EKS | VPC CNI + Calicoポリシーは1つの統合。完全なCalico CNIは別の新規クラスター設計 |
| AKS | プロバイダーがサポートするCNI/ポリシーの組み合わせと現在のインストール手順を確認 |
| GKE | Dataplane V2は**Cilium**を使用。Calicoは該当する従来設定に適用し、V2の上にインストールしない |
| 自己管理Kubernetes | ディストリビューション、カーネル、CNI所有権、経路、権限を確認 |
| Windows | 指定のIPv4構成。Linux eBPF、IPIP、IPv6/デュアルスタック、WireGuardとの機能同等性はない |
| ホスト / VM | インストールと機能要件が別。KubeVirt/Enterpriseの対応状況は基本的なホスト保護と異なる |

[GKEの文書](https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2)は、V2のCiliumと従来のCalico方式を明確に区別しています。

Typhaは独立したPod群で更新をキャッシュ・配布し、Felixの直接のデータストア監視を減らします。3レプリカは例で、普遍的な最小数ではありません。容量はポリシー、エンドポイント、Serviceの変更頻度、ハードウェア、データストア、データプレーンに依存します。この入門には、「5,000ノード / 100,000 Pod / 数百万ルール」という固定上限を裏付ける再現可能な証拠はありません。

## Calico、kube-proxy、性能

kube-proxyはService転送を実装し、CNIネットワーキングやNetworkPolicyは実装しません。Calicoの標準データプレーンはこの演習のように共存でき、eBPFデータプレーンは設定すればService処理を置き換えられます。

| 観点 | 比較対象 |
|---|---|
| Podネットワーキング/IPAM | 同一トポロジーのCNI/IPAM実装 |
| Service転送 | 選択したkube-proxyバックエンドまたはeBPF置換 |
| ポリシー | 同等のルールと適用範囲 |
| 規模 | Service/エンドポイント、セレクター、変更頻度、接続再利用 |
| CPU/メモリ/レイテンシー | ハードウェア、カーネル、バージョン、ワークロード、ウォームアップ、反復、エラー |

kube-proxyはiptables専用ではなく、現在のKubernetesはnftablesとバージョン依存の旧バックエンドも提供します。IPセット検索がCalicoの全パケット経路をO(1)にするわけではありません。初回のiptables Service NAT選択も、後続パケットのconntrack高速経路とは異なります。以前の出典のない1,000ノード/50,000 Podのルール数、レイテンシー、メモリ例は再現可能なベンチマークではなく、サイジングに使うべきではありません。

従来のVMネットワークも自動化・分散化できます。Calicoの宣言的ポリシーは、無限のIP容量や秒単位の収束保証を意味しません。

## デプロイシナリオ

- **オンプレミス**: Pod経路、BGPピア/フィルター、復路、ホスト保護を調整します。カプセル化を無効にするだけではアンダーレイ経路は作成されません。
- **EKS**: AWSネットワークを保持するには`cni.type: AmazonVPC`を選び、ポリシーエンジンの所有権とPod IPアノテーションを含む[レビュー済み概要](README.md)に従います。このKind演習にEKS Installationを適用したり、2つのポリシーエンジンを動かしたりしないでください。
- **ハイブリッド/マルチクラスター**: 接続、検出、ポリシー管理は別の機能です。CrossSubnet IPPoolはVPN、共有ID、クラスター間検出を確立しません。該当するクラスター・メッシュ/マルチクラスター製品機能とアンダーレイを別々に評価してください。「Calico Federation」は普遍的な組み込みリンクではありません。
- **規制対象ワークロード**: Enterprise/Cloudはレポート、ログ、セキュリティ機能を追加できますが、インストールでコンプライアンスが成立するわけではありません。API監査ログはAPI変更を、フローログはネットワークの観測を記録し、あらゆる適用判断を自動記録するものではありません。WireGuardは対応するOpen Source Linux構成でも利用できます。

## コミュニティとソース開発

現在のSlack/ミーティングリンクは[コミュニティページ](https://www.tigera.io/project-calico/community/)、再現可能な報告は[課題トラッカー](https://github.com/projectcalico/calico/issues)、開発参加には[貢献者ガイド](https://github.com/projectcalico/calico/blob/v3.32.2/CONTRIBUTING.md)を使います。日付のない隔週予定や古いフォーラムURLが現在も有効だと想定しないでください。

ソース学習向けの[開発者ガイド](https://github.com/projectcalico/calico/blob/v3.32.2/DEVELOPER_GUIDE.md)は、Linux/Docker/git/make環境とコンポーネント固有テストを説明します。ルートに`make dev-environment`ターゲットはありません。この任意のソース作業手順はネットワーキング演習とは別で、監査中に実行していません。

```bash
git clone --depth 1 --branch v3.32.2 https://github.com/projectcalico/calico.git calico-source-study
cd calico-source-study
# Read prerequisites and the selected component's Makefile before running tests.
cat DEVELOPER_GUIDE.md
make -C calicoctl test
```

Open Sourceは、演習だけでなく本番にもコミュニティサポートのネットワーキングとポリシーを提供します。Enterpriseは商用機能/サポートを追加し、CloudはSaaS管理を提供します。「小規模か大規模か」という一律の基準でなく、[機能表](https://docs.tigera.io/calico/latest/about/calico-product-editions)で選んでください。

## 使い捨て演習環境のクリーンアップ

結果の保存後、`kind delete cluster --name calico-lab`でこの演習用に作成した`calico-lab`クラスターだけを削除します。無関係なクラスターとkubeconfigは保持してください。このローカルクリーンアップはEKS削除手順ではありません。

[次: Calicoアーキテクチャ](02-architecture.md) · [Calicoの概要](README.md) · [入門クイズ](../../quizzes/networking/calico/01-introduction-quiz.md)
