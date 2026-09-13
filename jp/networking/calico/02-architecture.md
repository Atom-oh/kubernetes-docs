# 第2部: アーキテクチャ

> **レビュー基準**: Calico Open Source 3.32.2 / operator 1.42.6。Calico 3.32はKubernetes 1.34–1.36でテストされています。
> **最終更新**: September 12, 2026。例は設定の参考であり、実クラスターでの検証ではありません。

## 概要

このセクションはCalicoのアーキテクチャを詳しく説明します。各コンポーネントの動作と相互作用を理解することは、本番環境でCalicoを効果的にデプロイし、トラブルシューティングし、最適化するために不可欠です。

## 全体アーキテクチャ図

![Kubernetes APIとTyphaからFelixへの状態配布、およびBGP設定経路の簡略図。中間コンポーネントは省略。](../../.gitbook/assets/en-networking-calico-02-architecture-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-0.html)

これは制御状態の簡略図です。BIRDへの辺では設定をレンダリングするconfdを省略しており、TyphaはBIRDを直接設定するAPIではありません。BIRD/confdとTyphaはインストールモードに依存し、コントロールプレーンの全コンポーネントを示してはいません。

## Felix: Calicoエージェント

Felixは選択したワークロードノードのCalicoノードエージェント内で動作し、該当する経路、インターフェース設定、ポリシーをカーネルに設定します。Linuxの完全ネットワーキング経路では、コンテナランタイムがCNIチェーンを呼び出し、CNI/IPAMプラグインがインターフェースを作成してアドレスを割り当てます。Felixはエンドポイント変更を非同期に観測し、直接CNI ADD呼び出しを処理するものではありません。具体的なコンポーネントはOperator、プラットフォーム、ネットワークモードで決まります。

### Felixの責務

Linux CNI/IPAMがPodインターフェースとアドレスを作成します。Felixはエンドポイント状態とカーネルポリシーを調整します。HTTPヘルス応答の提供とデータストアへの状態報告は別の機能です。

### 中核機能

1. **経路設定**: 該当するワークロードとトンネルの経路を調整。BGPモードではBIRDのカーネルプロトコルも学習経路を設定
2. **ACL適用**: ネットワークポリシー用のiptables/nftables/eBPFルールを設定
3. **インターフェース管理**: エンドポイントのインターフェース状態と関連カーネル設定を調整。Linux veth作成はCNI経路の担当
4. **ヘルス報告**: ノードとエンドポイントの健全性をデータストアへ報告
5. **エンドポイント調整**: ワークロードエンドポイント状態を監視し、該当ポリシー/経路を設定。アドレス割り当てとLinux Podインターフェース作成はCNI/IPAMプラグインが担当

### Felixのデータプレーン選択肢

Felixは複数のデータプレーンバックエンドをサポートします。

| データプレーン | 説明 | 適した用途 |
| ------------ | -------------------------- | ------------------------------------------- |
| **iptables** | 従来のLinuxファイアウォール | 互換性、成熟したデプロイ |
| **nftables** | ネイティブnftables実装 | 対応カーネル、プラットフォーム、機能群を確認 |
| **eBPF** | カーネル内でプログラム可能 | オプションのService処理。調整された移行と対応機能が必要 |

### FelixConfigurationリソース

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  healthEnabled: true
  healthPort: 9099
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
  reportingInterval: 30s
  reportingTTL: 90s
```

この最小例はCalico 3.32.2で受け入れられるフィールドを使います。設定の所有者を通じて変更してください。データプレーン移行や性能調整の手順ではありません。Felixのヘルスホストのデフォルトはlocalhostです。メトリクスの有効化はPrometheusのスクレイプを設定せず、公開を適切にするものでもありません。

| 設定上の観点 | 正しい所有者 / 解釈 |
|---|---|
| Linuxデータプレーン | Operatorの`Installation.spec.calicoNetwork.linuxDataplane`で、対応構成の`Iptables`、`Nftables`、`BPF`を選択 |
| `bpfEnabled` | 低レベルのFelix設定。単独パッチではなくOperator管理の移行、kube-proxy/API到達性を調整 |
| `iptablesBackend: NFT` | iptables-nftツールのバックエンドを選択。Calicoネイティブnftablesデータプレーンではない |
| 接続時負荷分散 | 現在のフィールドは`bpfConnectTimeLoadBalancing: TCP`、`Enabled`、`Disabled`。旧ブール値`bpfConnectTimeLoadBalancingEnabled`も受理されるが非推奨 |
| ノードアドレス検出 | Operatorの`calicoNetwork.nodeAddressAutodetectionV4` / `V6`、またはマニフェスト管理インストールのノード起動環境。`ipAutoDetectionMethod`や`ipv6AutoDetectionMethod`というFelixフィールドではない |
| フロー可視性 | 対応するGoldmane/Whisker設定を使用。Open Sourceは以前の例のEnterpriseファイルログフィールドを受け入れない |
| MTUとトンネルモード | アンダーレイ、カプセル化、暗号化から導出。1440/1410/1420を任意に設定したり全トンネルを有効にしたりせず、Installation/IPPool設定を調整 |
| ホストのフェイルセーフポート | デフォルト一覧の置換前に実際のAPI/BGP/etcd/管理アクセス到達性を確認。旧短縮一覧では必要な例外が消える可能性があった |
| 期間 | `reportingInterval`、`reportingTTL`、`iptablesPostWriteCheckInterval`、`iptablesLockProbeInterval`など現在の名前を使用。機械的に`Secs`/`Millis`を追加しない |

リリースされたスキーマは、旧名の`iptablesLockFilePath`、`iptablesLockTimeoutSecs`、`iptablesLockProbeIntervalMillis`、`iptablesPostWriteCheckIntervalSecs`、`reportingIntervalSecs`、`reportingTTLSecs`を拒否します。[Felixリソースリファレンス](https://docs.tigera.io/calico/latest/reference/resources/felixconfig)と[Operator API](https://docs.tigera.io/calico/latest/reference/installation/api)を参照してください。アドレスやデータプレーンの変更には独自のロールアウト確認が必要です。

### Felixのiptablesルール構造

以下は[リリース済みルール定義](https://github.com/projectcalico/calico/blob/v3.32.2/felix/rules/rule_defs.go)から選んだプレフィックスであり、完全なチェーングラフではありません。iptablesデータプレーンを説明しています。インストールしたモードと設定の実際のルールを確認してください。

| チェーン/プレフィックス | 役割 |
|---|---|
| `cali-FORWARD` | Calico転送フック |
| `cali-from-wl-dispatch` | ワークロードインターフェースからの振り分け |
| `cali-to-wl-dispatch` | ワークロードインターフェースへの振り分け |
| `cali-fw-…` / `cali-tw-…` | ワークロードごとの方向別チェーン |
| `cali-pi-…` / `cali-po-…` | 受信/送信ポリシーチェーン |

### Felixのデータフロー

Pod作成時にランタイムがCNI/IPAMチェーンを呼び出し、ネットワークを設定してエンドポイント状態を記録します。Felixは関連変更を観測してポリシー/経路を設定します。有効な場合、BGP設定は独自のconfd/BIRD経路に従います。PodがRunningでも、ルーティングやポリシーの収束は証明されません。

## BIRD: BGPルーティングデーモン

BIRD（BIRD Internet Routing Daemon）はCalicoのBGPバックエンドが有効な場合にBGP経路を交換します。ポリシー専用やBGP無効のVXLANインストールではBIRD/confdは必須ではありません。以下のトポロジー例には適切に設計されたBGP有効クラスターが必要で、入門のBGP無効kind演習に追加するものではありません。

### CalicoアーキテクチャにおけるBIRD

![3ノードそれぞれのBIRDが完全なiBGPメッシュを形成してPod経路を交換し、さらにトップオブラックスイッチとeBGPでピア接続し、スイッチがコアルーターへ経路を渡す図。](../../.gitbook/assets/en-networking-calico-02-architecture-3.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-3.html)

線はBGPセッションを表し、BIRDを通るアプリケーションパケットの経路ではありません。規模ラベルは目安であり、プロトコル要件やルートリフレクターの固定しきい値ではありません。

### BGPセッションの種類

| セッションタイプ | 用途 | 設定 |
| --------------------- | --------------------------- | ---------------------- |
| **ノード間メッシュ** | 小規模クラスターのデフォルト | 自動、フルメッシュ |
| **ルートリフレクター** | トポロジー要件に応じてメッシュのセッション数を削減 | 代替ピアを先に設定・確認 |
| **外部ピアリング** | オンプレミス統合 | BGPピアを手動設定 |

### BGP設定例

#### ノード間メッシュ（デフォルト）

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
```

#### ルートリフレクターの設定

[公式BGP移行手順](https://docs.tigera.io/calico/latest/networking/configuring/bgp)を使います。ルートリフレクターのクラスターIDを割り当てると、そのノードは即座に既存ノードメッシュから外れ、ワークロードを中断する可能性があります。アプリケーションワークロードのない専用ノードを準備するか、明示的な保守移行を計画してください。他の設定を省略した部分オブジェクトで既存Calico Nodeを置き換えないでください。

Kubernetes APIデータストアでは、文書化されたノードアノテーションが既存Nodeフィールドを保持します。例の名前を準備したノードに置き換えてください。

```bash
# Existing, prepared RR nodes with no application workloads.
kubectl get nodes rr-1 rr-2 -o yaml > rr-nodes-before.yaml
kubectl get bgpconfiguration.projectcalico.org default -o yaml > bgp-before.yaml
kubectl annotate node rr-1 projectcalico.org/RouteReflectorClusterID=244.0.0.1 --overwrite
kubectl annotate node rr-2 projectcalico.org/RouteReflectorClusterID=244.0.0.2 --overwrite
kubectl label nodes rr-1 rr-2 route-reflector=true --overwrite
kubectl apply -f - <<'YAML'
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: nodes-to-route-reflectors
spec:
  nodeSelector: all()
  peerSelector: route-reflector == 'true'
YAML
```

RRセレクターへの`all()`はクライアントとRR間のピアリングをカバーします。両リフレクターとクライアント経路を確認してください。セッションの確立を待ち、実際の到達性を確認してから旧ノードメッシュを無効にします。Establishedセッションだけでは、必要な経路が受理された証明にはなりません。

```bash
# Only after replacement sessions, routes and test traffic have been verified.
kubectl patch bgpconfiguration.projectcalico.org default --type merge \
  -p '{"spec":{"nodeToNodeMeshEnabled":false}}'
```

これは順序のある移行で、全ブロックの同時適用指示でも無中断保証でもありません。保存した設定と検証済み復旧経路を保持してください。外部ファブリック例のアドレス、ASN、再利用AS番号には、意図的な経路ポリシーとASループ処理が必要です。

#### 外部BGPピアリング

例のピアアドレス、ASN、ラックセレクターを計画したトポロジーに置き換えます。パスワード参照には、Calicoノードコンポーネントの名前空間内の一致するSecret/キーと、対応ルーター設定が必要です。BGPセッションを認証し、ワークロードのペイロードは認証しません。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-switch-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  nodeSelector: rack == 'rack-1'
  password:
    secretKeyRef:
      name: bgp-passwords
      key: tor-password
  sourceAddress: UseNodeIP
  keepOriginalNextHop: false
```

### 経路伝播の処理

![Felixがカーネルルーティングテーブルに経路を追加し、BIRDがBGPセッション管理を通じて経路情報を取得して、BGP UPDATEでPod CIDRを他ノードや外部ルーターへ広告する図。大規模クラスター向けルートリフレクターと、エクスポートフィルターによる経路フィルタリングもBIRDの機能として示す。](../../.gitbook/assets/en-networking-calico-02-architecture-4.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-4.html)

これは経路情報の1つの流れを示します。BIRDのカーネルプロトコルも学習経路を設定でき、confd/IPAMデータはルーティング設定の生成に寄与します。BGP経路フィルターはルーティングポリシーであり、Kubernetes NetworkPolicyの適用ではありません。

### BIRD状態確認コマンド

BIRDが動作するノードを選びます。リリース済みの[起動スクリプト](https://github.com/projectcalico/calico/blob/v3.32.2/node/filesystem/etc/service/available/bird/run)は、以下のIPv4制御ソケットを設定します。マニフェスト管理インストールでは別の名前空間を使う場合があります。

```bash
CALICO_NODE=worker-node-name
CALICO_POD=$(kubectl -n calico-system get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')
: "${CALICO_POD:?No Calico Pod on the selected node}"
kubectl -n calico-system exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols
kubectl -n calico-system exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
```

詳細な照会には、出力の実際のプロトコル名とプレフィックスを使用します。コマンドとコンソール出力例は別です。以前の`birdcl>`プロンプトはBashコマンドではありませんでした。これらの読み取り専用確認はルーティングを設定しません。

## confd: 設定管理

confdはCalicoデータストアを監視してBIRD設定ファイルを生成する軽量な設定管理ツールです。

### confdのワークフロー

confdは関連BGP設定を監視し、テンプレートをレンダリングして候補を検査し、BIRDに再読み込みを通知します。

### confdのテンプレート処理

架空の`.NodeIP` / `.BGPPeers`データ構造でなく、[リリース済みテンプレート](https://github.com/projectcalico/calico/blob/v3.32.2/confd/etc/calico/confd/templates/bird.cfg.template)を使います。この抜粋はカーネル同期を示します。フィルターと周囲の設定は別の場所で定義されるため、完全な`bird.cfg`ではありません。

```text
protocol kernel {
  learn;
  persist;
  scan time 2;
  import all;
  export filter calico_kernel_programming;
  graceful restart;
  merge paths on;
}
```

[confdテンプレート定義](https://github.com/projectcalico/calico/blob/v3.32.2/confd/etc/calico/confd/conf.d/bird.toml)は`/etc/calico/confd/config/bird.cfg`を書き込み、`bird -p -c {{.src}}`で候補を検証し、再読み込みアクションとして`sv hup bird || true`を使います。これはBIRDが選択した学習経路をカーネルへエクスポートできることを示し、単に全経路をFelixから受け取るわけではありません。再読み込みとグレースフルリスタートの動作には状態と通信の確認が依然必要です。生成ファイルを編集せず、API所有者を通じてBGP設定を管理してください。

## Typha: スケーリングコンポーネント

TyphaはKubernetes APIサーバーとFelixエージェントの間に置かれる配布プロキシです。データストア更新をキャッシュ・配布し、APIサーバーの負荷を減らします。

### Typhaを使う理由

Typhaは状態をキャッシュし、複数クライアントへ変更をストリーミングすることで、繰り返しのデータストア更新処理を削減します。ノード数だけでなく、インストールの所有権、TLS、実際のスケーリングロジックも重要です。

### operator 1.42.6のTyphaスケーリング

OperatorはTyphaをデプロイしてスケーリングします。「50ノード超だけ」という普遍的なルールはありません。固定バージョンの[オートスケーラー実装](https://github.com/tigera/operator/blob/v1.42.6/pkg/controller/installation/typha_autoscaler.go)は、スケジュール不可とされていないノードを数え、AKS仮想ノードを除外し、希望レプリカを配置する十分なLinuxノードがあるかを別に確認します。Taintや他の配置制約も重要です。

短縮されたコメントではなく、実際の[スケール関数](https://github.com/tigera/operator/blob/v1.42.6/pkg/common/autoscale.go)は次を返します。

- カウント対象ノードが1–2台なら1レプリカ。
- カウント対象ノードが3–4台なら2レプリカ。
- カウント対象ノードが5台以上なら`max(3, floor(N / 200) + 2)`。

| カウント対象ノード数 | このバージョンでの希望レプリカ数 |
|---|---|
| 50 | 3 |
| 200 | 3 |
| 500 | 4 |
| 1,000 | 7 |
| 2,000 | 12 |

これはバージョン固有の希望数であり、レプリカあたり容量の保証や全インストールへの推奨ではありません。非クラスターホストモードは別の適格HostEndpoint数を使います。以前の`max(3, ceil(N / 200))`表はこのOperatorを説明していませんでした。

### Operator管理のTypha設定

OperatorのDeployment、ServiceAccount/RBAC、Service、Disruption Budget、TLS設定をまとめて保持します。以前の手書きDeploymentは必須依存関係を欠き、Operator管理設定を上書きする可能性がありました。FelixからTyphaへのTLSは、信頼するCA、Typhaサーバー証明書/キー、期待されるFelixクライアントIDを使います。5473はデフォルト同期ポートで、ユーザートラフィックのプロキシではありません。

```bash
# Change the operator's supported setting through its API.
kubectl patch installation.operator.tigera.io default --type merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl -n calico-system get deployment calico-typha -o yaml
kubectl -n calico-system get service calico-typha -o yaml
kubectl -n calico-system get pdb
```

Typhaのヘルスエンドポイントのデフォルトはlocalhost:9098です。このOperatorは設定したFelixヘルスポートから1を引いてヘルスポートを決定し、プローブも対応して設定します。PodネットワークのDeploymentでPod IPを対象とするプローブは、localhostだけで待ち受けるリスナーに届きません。ネットワーク/バインド設定なしでプローブをコピーするのは安全ではありません。Operatorソースは、旧単独例にはなかったTLSマウントとクライアントID設定を提供します。

### Typhaの配布アーキテクチャ

各Typhaはクライアントストリーム用のキャッシュ状態を維持します。図のクライアントグループ分けは、インスタンスあたりの固定容量仕様ではありません。

## kube-controllers: Kubernetes統合

calico-kube-controllersは選択された調整機能を実行します。実行されるコントローラーはデータストア、エディション、インストール設定に依存します。etcdデータストアへのポリシー/名前空間/サービスアカウントの投影は、Kubernetes APIデータストアの処理とは異なります。

### 利用可能なコントローラーの役割

| コントローラー | 目的 |
| ------------------------------- | ------------------------------------------------- |
| **Node Controller** | KubernetesノードとCalicoノードリソースを同期 |
| **Policy Controller** | Kubernetes NetworkPolicyとCalicoポリシーを同期 |
| **Namespace Controller** | プロファイル管理用に名前空間ラベルを同期 |
| **ServiceAccount Controller** | サービスアカウントラベルをCalicoプロファイルに投影。Kubernetes RBACは付与しない |
| **WorkloadEndpoint Controller** | 該当データストア経路でPodラベルなどのワークロードエンドポイントメタデータを更新 |

### コントローラーの調整ループ

![kube-controllersがKubernetesとCalicoリソースの一覧を繰り返し取得し、差分を比較してCalicoデータストアへ変更を書き込むか、同期済みなら何もしないシーケンス図。](../../.gitbook/assets/en-networking-calico-02-architecture-8.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-8.html)

これは期待状態と観測状態の論理的な調整の概略であり、毎周期2つのリモートLIST呼び出しがあると証明するトレースではありません。実際のコントローラーはwatch/キャッシュを使い、有効な役割はデータストアとインストールに依存します。

### kube-controllersの設定

Operatorインストールでは、実際の[KubeControllersConfiguration API](https://docs.tigera.io/calico/latest/reference/resources/kubecontrollersconfig)を設定します。このガイドのDeploymentは`calico-kube-controllers-config`という任意のConfigMapを読みません。

```bash
kubectl get kubecontrollersconfiguration.projectcalico.org default -o yaml
kubectl patch kubecontrollersconfiguration.projectcalico.org default --type merge \
  -p '{"spec":{"logSeverityScreen":"Info","healthChecks":"Enabled","prometheusMetricsPort":9094}}'
```

このマージパッチは既存の`controllers`設定を保持します。GitOps管理なら、代わりに期待状態で同等の変更を行ってください。空のコントローラーオブジェクトを持つ置換マニフェストは、既存の調整や割り当て設定を変える場合があります。

Operator 1.42.6は標準Open Sourceデプロイで`ENABLED_CONTROLLERS=node,loadbalancer`を選択します。上の広い一覧は利用可能な役割を説明し、全データストアで必ず5コントローラーが動作する意味ではありません。[レンダラー](https://github.com/tigera/operator/blob/v1.42.6/pkg/render/kubecontrollers/kube-controllers.go)は1レプリカと`Recreate`戦略を指定し、以前のリーダー選出の主張はその設定で裏付けられていませんでした。置換や手動スケーリングをせず、インストール所有者の管理下に置いてください。

## データストアの選択肢

このOperator例はKubernetes APIデータストアを使います。Calico状態にはCalico CRDとネイティブKubernetesオブジェクトが関与し、論理的な全Calicoリソースが個別CRDになるわけではありません。通常の集約APIサーバーは内部表現の上に`projectcalico.org/v3`を公開します。ネイティブv3 CRDは別のCalico 3.32技術プレビューで、独自の移行手順があります。

Typhaは読み取り/watch更新を配布し、Felixの汎用書き込みプロキシではありません。状態やリソースを更新するコンポーネントは独自のデータストアアクセスを使います。Kubernetesは背後のストアにAPI状態を永続化しますが、このモードで利用者が別のCalico etcdクラスターを必要とするわけではありません。

etcdv3への直接アクセスは、明示的なサポートと機能制約がある別のインストール選択肢です。高速、無制限、5,000ノード超で必須だと推測しないでください。eBPFデータプレーンにはKubernetesデータストアが必要です。直接etcdデプロイには、独自のTLS信頼、認証情報、可用性、整合性のあるバックアップ/復元設計も必要です。

| 観点 | Kubernetes APIデータストア | 直接etcdv3 |
|---|---|---|
| アクセス制御 | Kubernetes認証/RBACと適切なCalico API経路 | etcd認証/TLSとアクセス制御 |
| 運用 | クラスターAPIを再利用し、プロバイダー固有のバックアップ手順に従う | 選択したetcdデプロイを運用・バックアップ |
| ホスト/VM対応 | 具体的なインストールとエディションを確認 | 具体的なインストールとエディションを確認 |
| 選択 | このOperatorガイドで使用 | 別途検証した設計。ノード数に基づく近道ではない |

マネージドKubernetesの「Kubernetesバックアップ」は、利用者が直接コントロールプレーンのetcdスナップショットを取得できる意味ではありません。プラットフォーム手順で対応リソースをバックアップしてください。

## コンポーネント間の連携シーケンス

kubeletはコンテナランタイムを通じてサンドボックス作成を要求し、ランタイムがCNI/IPAMを呼び出します。エンドポイントとポリシーデータは、選択したデータストア/watch経路でFelixへ届きます。BGPモードではconfdとBIRDがルーティング設定を別に処理します。これらは非同期に収束するため、実際の接続性と適用を確認してください。

## パケットフローの分析

### Ingressパケットフロー（同一ノードのPod間）

![同一ノードのPodから別のPodへ、それぞれのvethインターフェースとホストのiptables/eBPFポリシーチェックを通過するパケットの図。](../../.gitbook/assets/en-networking-calico-02-architecture-12.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-12.html)

ポリシーのボックスは、該当する送信元Egressと宛先Ingressのカーネルチェックをまとめています。vethインターフェースは両Podのネットワーク経路に属し、パケットはFelixプロセスを通りません。

### Egressパケットフロー（IPIPを使う異なるノードのPod間）

![Pod Aのパケットがノード1のFelix/iptables Egressポリシーチェックを通り、IPIP/VXLANでカプセル化されるかBGP経路で直接転送されてノード2へ到達し、Ingressポリシーチェック後にPod Bへ届くシーケンス図。](../../.gitbook/assets/en-networking-calico-02-architecture-13.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-13.html)

2つの経路は選択肢として読んでください。「Felix/iptables」はFelixが設定するカーネルルールを意味し、デーモンによるパケット転送ではありません。BIRDはBGPモードで経路制御情報を提供し、アプリケーションパケットは運びません。

### パケット構造の比較

```
Original Pod-to-Pod Packet:
┌─────────────────────────────────────────────────────────────┐
│ Ethernet │   IP Header    │   TCP/UDP   │     Payload      │
│  Header  │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 192.168.2.10 │             │                  │
└─────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet:
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │   Outer IP     │   Inner IP     │   TCP/UDP   │     Payload      │
│  Header  │ Src: 10.0.1.10 │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 10.0.1.11 │ Dst: 192.168.2.10 │             │                  │
│          │ Proto: 4 (IPIP)│                │             │                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## まとめ

Calicoのアーキテクチャは拡張性、性能、運用の簡素さを重視して設計されています。

1. **Felix**: 各ノードで経路とACLを設定する主力エージェント
2. **BIRD**: BGPで経路を配布し、ネイティブルーティング統合を可能にする
3. **confd**: データストアとBIRD設定を橋渡し
4. **Typha**: APIサーバー負荷を減らしてシステムを拡張
5. **kube-controllers**: KubernetesとCalicoを同期状態に保つ
6. **データストア**: 設定保存にKubernetes API（推奨）またはetcdを使用

これらのコンポーネントと相互作用の理解は、次に不可欠です。

* 接続問題のトラブルシューティング
* 大規模環境での性能最適化
* 容量とアーキテクチャの計画
* 既存ネットワークインフラとの統合

[前: 第1部 - Calico入門](01-introduction.md)

[次: 第3部 - ネットワーキングモード](03-networking-modes.md)

[Calicoの概要に戻る](./README.md)

## クイズ

この章の学習内容を確認するには、[アーキテクチャクイズ](../../quizzes/networking/calico/02-architecture-quiz.md)に挑戦してください。
