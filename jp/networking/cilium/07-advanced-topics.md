# 高度なトピックと実運用事例

> **確認基準**: Cilium 1.20.3、Cilium CLI 0.20.1、Hubble CLI 1.20.2。
> **最終確認日**: 2026年10月16日。Cilium 1.20 の Kubernetes 対応バージョンは 1.33～1.36 です。過去の測定値は、測定当時の環境条件を維持して記載しています。

## ラボ環境の準備

[インストール前提条件](README.md)を確認し、スケジュール可能な Linux ノードを2台以上備えた、破棄可能なテストクラスターを用意してください。OS、カーネル、Cilium の設定、トポロジー、MTU、ポリシー、暗号化、テストワークロードを結果とともに記録します。kubectl は、API サーバーとのサポート対象バージョンスキューの範囲内で使用してください。以下のコマンドには Helm、jq、Cilium CLI、Hubble CLI が必要です。`kubectl top` を使う場合は、メトリクス API も必要です。

### パフォーマンステスト環境の準備

変更を加える前に、現在のデプロイ状態を記録します。

```bash
cilium version
cilium status --verbose
kubectl version
kubectl get nodes -o wide
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
helm get values cilium --namespace kube-system -o yaml > cilium-current-values.yaml
```

現在の CLI は、テストに必要なワークロードも作成できます。ネットワーク負荷を発生させ、テスト用リソースを作成してよい場合に限り実行してください。

```bash
cilium connectivity perf --test-namespace cilium-advanced-perf \
  --namespace-labels docs-audit-lab=cilium-advanced-07 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-advanced-perf-results
```

並列度を指定しない既定の実行では、引数に接尾辞がなくても **`cilium-advanced-perf-1`** 名前空間が使われます。テスト前にこの名前空間が未使用であることを確認してください。`--duration` はテスト全体ではなく、各シナリオ／サンプルに適用されます。スケジューリング、セットアップ、複数ケースの組み合わせにも時間がかかります。このコマンドは実際にワークロード負荷をかけるテストであり、読み取り専用の診断ではありません。

同一ノード内とノード間、TCP のリクエスト／応答と UDP を比較し、実際の CPU・メモリ使用量とパケット損失を測定してください。一度に変更する設定は1つにします。テストが成功しても、アプリケーションの SLO、本番環境の容量上限、すべてのポリシーパスが保証されるわけではありません。監査ではこれらのコマンド仕様を確認しましたが、テストの実行やクラスターの作成は行っていません。

## パフォーマンスの調整とトラブルシューティング

### パフォーマンス調査の観点

![Cilium のパフォーマンスを調査する4つの領域として、カーネルの動作、eBPF マップ、リソース割り当て、選択したネットワーク経路を示す図。](../../.gitbook/assets/en-networking-cilium-07-advanced-topics-0.png)

[インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-07-advanced-topics-0.html)

この図は調査対象を分類したもので、すべての設定値を増やしたり、セキュリティ制御を無効にしたりするよう勧めるものではありません。

### 調査する設定領域

| 領域 | 測定する内容と設定の役割 |
| --- | --- |
| ソケットのバックログ | `net.core.somaxconn` はソケットの listen backlog の上限です。`net.ipv4.tcp_max_syn_backlog` はリスナーごとの SYN_RECV 待機リクエスト数に関係します。サーバーの accept 動作と対象のネットワーク名前空間を確認してください。 |
| 近隣テーブルのエントリー | `net.ipv4.neigh.default.gc_thresh1`、`gc_thresh2`、`gc_thresh3` は別々のガベージコレクションしきい値です。`gc_thresh` という単一の設定値はありません。 |
| コネクショントラッキング | Netfilter の `nf_conntrack_max` と Cilium の BPF CT マップは別の仕組みです。前者を増やしても後者のサイズは変わりません。 |
| BPF マップ | マップの逼迫、挿入失敗、エントリーの入れ替わり、メモリ使用量を調べます。CT、NAT、LB、エンドポイント単位のポリシーマップでは、対象範囲もサイズ設定も異なります。 |
| CPU とメモリ | agent、operator、Envoy、Hubble を個別に測定します。requests はスケジューリングに影響し、CPU limits はスロットリングを起こす可能性があり、memory limits は OOM 終了につながることがあります。すべての limit を増やすだけでは原因を特定できません。 |
| ネットワーク経路 | ネイティブルーティング／トンネル、MTU、マスカレード、暗号化、Service 転送方式を特定します。XDP 高速化は対応する経路とドライバーで利用できる機能であり、kube-proxy replacement に必須ではありません。 |

パフォーマンスを比較するときは、セキュリティ要件とルーティング要件を一定に保ってください。必須の暗号化やポリシーを外して得た高速化は、同等の構成同士の比較ではありません。

### マップサイズの調整

以下は、逼迫を測定した後に**変更候補**としてのみ保存してください。完全なバージョン管理対象リリース値へ統合し、小さな断片で Cilium ConfigMap 全体を置き換えないでください。

```yaml
# map-sizing-values.yaml
bpf:
  mapDynamicSizeRatio: 0.005
```

`0.005` は動的サイズ計算に用いる**ノードメモリの0.5**%という名目値であり、5%ではありません。また、Cilium 全体のメモリ使用量に対するハード上限でもありません。たとえば 32 GiB × 0.005 は、マップ上限、丸め、その他の割り当てを考慮する前で 163.84 MiB です。影響する大規模マップには CT、NAT、neighbor、socket reverse-NAT があります。その他のマップやユーザー空間メモリは別枠です。

`bpf.ctTcpMax`、`bpf.ctAnyMax`、`bpf.natMax` を明示すると、それぞれ該当するマップの動的サイズ計算が上書きされます。NAT 容量と CT 容量の整合性を保ち、起動時に確定したサイズを確認してください。マップを大きくするとメモリ消費が増えることがあります。また、マップを再作成すると既存の接続が切断される可能性があります。

分散 LRU（`bpf.distributedLRU.enabled`）は CPU ごとのプールを使って競合を減らしますが、メモリ使用量や eviction とのトレードオフがあります。動的サイズ計算が必要で、有効化時にマップが再作成されます。公式の高性能プロファイルは、稼働中の環境でいつでも切り替えられる設定ではありません。この種の datapath 変更は準備済みの新規ノードで導入するか、文書化された移行手順に従ってください。

古い `proxy-max-memory-percentage`、`proxy-max-threads`、`enable-xdp`、`tunnel: disabled`、`kube-proxy-replacement: strict` の例は、現在の設定手順として使えません。代わりに、前提条件を確認したうえで `envoy.resources`、`routingMode`、boolean 型の `kubeProxyReplacement`、`loadBalancer.acceleration` など、サポートされる chart 設定を使用してください。

### Hubble の負荷とイベント損失

イベントキューを大きくするとバーストを吸収できますが、メモリを使います。処理能力の不足が継続する問題を解決したり、CPU 消費を抑えたりするものではありません。

```yaml
# hubble-queue-values.yaml
hubble:
  eventQueueSize: 32768
```

トレースイベントの繰り返しが処理の大部分を占める場合は、集約間隔を長くする方法も個別に評価してください。

```yaml
# hubble-aggregation-values.yaml
bpf:
  monitorAggregation: medium
  monitorInterval: 10s
```

実際の chart フィールドは **`bpf.monitorInterval`** であり、`bpf.events.monitorInterval` ではありません。デプロイ前に、レンダリング後の `monitor-aggregation-interval` を確認してください。集約間隔を長くすること、イベント発生率を制限すること、イベント種別を無効にすることは、監視、Hubble メトリクス、エクスポートに利用できる観測データを減らします。Hubble イベントが失われても、それだけでアプリケーションのパケットがドロップしたとは限りません。可観測性データの損失と datapath のドロップをそれぞれ確認してください。

### 高度な datapath 機能の前提条件

| 機能 | 確認する前提条件と制約 |
| --- | --- |
| netkit | この基準バージョンでは Beta です。Linux 6.8 以降と BPF host routing が必要です。既存の veth Pod は、agent の再起動だけでデバイスタイプを切り替えられません。 |
| BIG TCP | Family ごとのカーネル／NIC 要件があります。組み合わせた調整プロファイルには Linux 6.8 以降と対応 NIC が必要です。一般的な MTU 引き上げ機能ではありません。 |
| BPF host routing | 対応する kube-proxy replacement と BPF masquerading が必要です。ホストの Netfilter hook を迂回するため、それらの hook に依存する Istio などの連携を確認してください。 |
| XDP Service 高速化 | ネイティブ XDP 対応デバイスと、サポート対象の外部 Service 転送経路が必要です。ドライバー／プラットフォームの手順に従い、実行中の状態を確認してください。 |
| Bandwidth Manager | Pod ごとの egress には EDT、ingress には eBPF token bucket を使用します。帯域幅 annotation の `10M` は 10 Mbit/s であり、10 MB/s ではありません。 |
| Pod の BBR | Bandwidth Manager、Linux 5.18 以降、BPF host routing が必要です。新規作成された Pod に設定が反映されます。ホストのみの BBR は別の選択肢です。 |

帯域幅制御には、egress L7 Cilium ポリシーや kind のようなネストされたネットワーク名前空間との既知の制約があります。これらは通常の Cilium インストール要件とは異なる条件です。1つの調整プロファイルが、すべての Service Mesh、クラウド、カーネルの組み合わせで動作する証拠にはなりません。

### 対象を絞ったトラブルシューティングコマンド

クラスター操作には単独の `cilium` CLI を使います。ローカルのエンドポイント、ポリシー、マップを調べるときは、対象 agent 内で **`cilium-dbg`** を実行します。任意の最初の agent を照会するのではなく、調査対象のノードを選んでください。

```bash
set -euo pipefail
: "${NODE_NAME:?Set NODE_NAME to the node being investigated}"
CILIUM_POD=$(kubectl -n kube-system get pods -l k8s-app=cilium \
  --field-selector "spec.nodeName=$NODE_NAME,status.phase=Running" -o json |
  jq -er 'if (.items | length) == 1
then .items[0].metadata.name
else error("expected exactly one running Cilium Pod on the selected node")
end')
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy selectors
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf metrics list
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --since=10m --tail=200
```

エンドポイント ID は agent ごとに異なります。対象 agent のエンドポイント一覧から ID を取得してください。

```bash
: "${CILIUM_POD:?Select the owning Cilium Pod first}"
: "${ENDPOINT_ID:?Read the endpoint ID from the selected agent endpoint list}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "$ENDPOINT_ID"
# Stream local BPF drop events; stop with Ctrl-C.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type drop
```

`cilium-dbg map list` は、agent の map manager が把握している open map を表示するもので、カーネル内の全 BPF map の一覧ではありません。`cilium-dbg monitor` は出力された BPF イベントと、任意で取得された trace を表示します。すべてのパケットを欠落なく取得する tcpdump ではありません。大規模な CT map のダンプは負荷がかかることがあります。`cilium-dbg bpf ct list global` を実行する前に、メトリクスと対象ノードを確認してください。

Hubble を使う前に、[セキュリティと可視性](06-security-visibility.md)で説明するローカル Relay 接続を確認してください。

```bash
hubble status
hubble observe --protocol tcp --verdict DROPPED --since 1h
hubble observe --protocol dns --from-label k8s:app=frontend --last 100
hubble observe --http-status '5+' --from-namespace production --last 100
```

`--type` はイベント種別を選ぶ引数であり、DNS レコードの A 型を指定するものではありません。クエリ種別を判別する場合は DNS flow のフィールドを使ってください。HTTP status のフィルターは `5xx` ではなく `5+` を使います。`--since 1h` で取得できる範囲は、保持されている履歴とイベントの可用性に制限されます。上書きされた1時間分のイベントを復元することはできません。

### よくあるトラブルと確認事項

| 症状 | 収集する証拠 | 次の判断 |
| --- | --- | --- |
| CT/NAT の逼迫 | マップの逼迫、挿入／ドロップ理由、接続の入れ替わり、実際に設定されたサイズ | サイズを増やす前に、接続の入れ替わり、タイムアウト、メモリの余裕を調査します。 |
| OOM または CPU 飽和 | コンテナの終了理由、メモリ／CPU の推移、スロットリング、proxy と Hubble の負荷 | 原因となるコンポーネントを特定し、その予算またはワークロードを調整します。 |
| 予期しないポリシー結果 | 正しい名前空間／ラベル、エンドポイントのポリシー revision、proxy エラー、Hubble verdict | 通信方向、加算される allow ルール、deny の優先順位を確認します。通常の allow ルールは、優先度順に評価するファイアウォールリストではありません。 |
| ノード間通信の失敗 | DNS、ノード／Pod の経路、MTU、トンネル／暗号化ポート、プラットフォームのファイアウォール | 往路と復路を確認します。BGP セッションが確立しても datapath の到達性は証明されません。 |
| アップグレード後の問題 | 変更前後の値、バージョン情報、全コンポーネントのバージョン、proxy の再接続 | 準備済みでサポートされるロールバック手順を使い、機能の互換性を調査します。 |

## 大規模デプロイの戦略

容量計画では、ノード／Pod 密度、Service とバックエンド、identity、ポリシー展開、API watch の通信量、IPAM 割り当て、flow 件数を考慮してください。ポリシーオブジェクトの数だけでは、エンドポイントごとのマップ消費量は決まりません。

### 大規模デプロイの構成

```text
Management / GitOps / shared monitoring
          | config and collected telemetry
          +-----------------------+
          v                       v
  Workload cluster A       Workload cluster B
  - Cilium Operator        - Cilium Operator
  - agent on each node     - agent on each node
  - local Hubble servers   - local Hubble servers
  - Relay/export setup     - Relay/export setup
          |                       |
          +--- optional ClusterMesh metadata/data paths
```

中央管理クラスターを設けても、管理対象の各クラスターで operator が不要になるわけではありません。各クラスターの operator と agent のサイズを計画してください。chart の operator replica 数や anti-affinity を満たすには、条件を満たすノードが十分に必要です。設定済みの collector を通じてメトリクスやログを集約します。ClusterMesh には、独自のアドレス設計、identity、trust、到達性の設計が必要です。すべてのポリシーリソースが自動的に複製されるわけではありません。

`ciliumEndpointSlice.enabled` は明示的に有効化する Cilium 機能であり、Kubernetes の EndpointSlice とは異なります。古い ConfigMap の `enable-endpoint-slice` フラグでもありません。有効化する前にバージョンと機能の互換性を評価してください。現時点で Egress Gateway は CiliumEndpointSlice または ClusterMesh と併用できません。

Egress Gateway は対象トラフィックの送信元 IP を予測可能な Gateway アドレスに **SNAT** します。元の Pod の送信元アドレスは維持しません。AWS 固有の要件を含め、Gateway のインターフェイス／IP とルーティングは事前に構成してください。BPF masquerading、kube-proxy replacement、CRD identity allocation が必要です。新しく起動した Pod は egress ポリシーが適用されるまでの短い間にトラフィックを送信することがあります。送信元 IP を即時に fail-closed で保証する機能として扱わないでください。

### 段階的な更新と復旧

期待する設定値、ポリシー、アドレスプール定義、必要な trust／鍵素材は、適切なバージョン管理とバックアップ制御のもとで保持してください。復旧訓練を行ってください。ConfigMap のバックアップだけでは、IPAM や暗号鍵を含む完全な復旧計画になりません。

マイナーバージョンを更新する前に、まず現在のマイナーバージョンの最新パッチへ更新し、必要な事前チェックを行ってから、**一度に1つのマイナーバージョンだけ**進めてください。アップグレードガイドの指示どおり、初期の `upgradeCompatibility` を維持し、名前が変わった設定や削除された設定を移行してください。マイナーバージョンをまたいで `--reuse-values` を使わないでください。agent、operator、その他の Cilium コンポーネントのバージョンを揃えてください。

更新中はユーザー空間 proxy 経由の通信が再接続されることがあり、バッファーされた監視イベントが失われる可能性もあります。ロールバックを有効にするには、新機能やリソースの削除または移行が必要な場合があります。一般的なアプリケーションの Blue/Green デプロイや Helm rollback だけでは、CNI 移行を可逆かつ無停止で行える保証になりません。

## 実運用のユースケース

### 公開済みの過去のスケーラビリティ実験

公式のスケーラビリティレポートには、Google Cloud 上の **worker ノード1,000台**、controller ノード3台、カーネル **5.4.0-1009-gcp** の実験が記載されています。環境設定には Cilium のバージョンが書かれていないため、この結果を Cilium 1.20.3 のベンチマークとして扱ってはいけません。このレポートは、独自のワークロードにおけるリソース消費と収束を説明するものです。現在のサポートマトリクスでも、容量の保証でもありません。

ヘルスチェックの変更や大きな rollout 並列度は、実験時に選択された条件です。引用するときは実際のテスト条件を保ち、運用構成は別途検証してください。

### 設計シナリオ1: 大規模な EC サイト

Service 数が多くリクエスト量が大きい場合は、eBPF Service 転送、identity／L7 ポリシー、Hubble、任意の ClusterMesh を評価します。同一のトポロジーと保護要件のもとで、p95／p99 レイテンシー、スループット、エラー、リクエストあたりの CPU 使用量、ポリシー収束を測定してください。ここでは、特定の実装や再現可能な測定値に基づく一律の改善率は示せません。

### 設計シナリオ2: 金融サービス

最小権限ポリシー、適切な範囲を持つトランスポート／アプリケーション暗号化、制御された flow export を、アプリケーション／API の監査記録と組み合わせます。鍵のローテーション、イベント損失、保持期間、クラスター間の trust をテストしてください。Hubble flow だけでは、規制対応に必要な完全な監査証跡にならず、監査時間の短縮も保証しません。

### 設計シナリオ3: 通信とエッジ

実環境に近い通信量で、NIC／ドライバー対応、CPU スケジューリング、Service 転送経路、パケットサイズ、損失、遅延を評価してください。条件を満たす転送経路では XDP が有効な場合がありますが、それだけで 5G user-plane function が実装されるわけでも、任意のハードウェアで固定の packets-per-second 性能が得られるわけでもありません。遠隔拠点にも underlay が必要であり、障害と復旧を明示的にテストしてください。

## 今後のロードマップと開発方針

コミュニティのロードマップには、**日程の確約はありません**。希望する連携機能の一覧を提供時期の約束とみなさず、個々の機能についてリリースノート、承認済み設計、issue を確認してください。

| 領域 | 調査する内容 |
| --- | --- |
| eBPF とカーネル | 提案された経路に必要なカーネル機能、バックポート、NIC、アーキテクチャは何か。CO-RE は不足しているカーネル機能を補いません。 |
| ネットワークと IPv6 | 選択したリリースでサポートされる IPAM、ルーティング、ポリシー、外部連携の組み合わせは何か。 |
| セキュリティと可観測性 | これは Cilium のネットワークポリシーか、Beta のワークロード認証／暗号化か、Tetragon の実行時強制か、それとも外部の検知／保存システムか。 |
| クラウド、Service Mesh、サーバーレス | マネージドプラットフォームは意図する CNI／ホスト hook を許可するか。Service Mesh の interception と認証は維持されるか。 |
| エッジ、IoT、5G、AI/ML | どの追加デバイス、転送方式、実行環境、アクセラレーター連携が必要か。Kubernetes CNI だけでアプリケーション固有の能力すべてが実現するわけではありません。 |

プロジェクトの issue、設計提案、ドキュメント、コミュニティの議論を通じて参加できます。商用サポートやマネージドディストリビューションには、それぞれ独自の機能／サポート契約があります。

## 現在の BGP 設定

以前の `CiliumBGPPeeringPolicy` の例は、この基準バージョンでは古くなっています。現在の設定では、クラスター／ノードの選択、peer 設定、広告する prefix を3つの **`cilium.io/v2`** リソースに分けます。BGP Control Plane、LoadBalancer IP の広告、Egress Gateway、エッジ構成の詳細は[BGP、LB、egress、エッジ](11-bgp-lb-egress-edge.md)を、マルチクラスターの詳細は[ClusterMesh の導入と更新](13-clustermesh-install-upgrade.md)を参照してください。

以下は、独立したルーティングラボ向けの設定モデルであり、完全なクラウドルーター構成ではありません。`PodCIDR` を広告するには cluster-pool または Kubernetes host-scope IPAM を前提とし、接続可能な peer ルーター、そのルーター側の設定、`cilium-bgp=lab` と意図的にラベル付けされたノードが必要です。`192.0.2.1` はドキュメント用アドレスです。実際の peer IP に置き換え、`/32` は付けないでください。Multi-pool IPAM では別の広告タイプと pool 選択が必要です。

```yaml
# bgp-values.yaml
bgpControlPlane:
  enabled: true
```
```yaml
# bgp-lab.yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata:
  name: lab-bgp
spec:
  nodeSelector:
    matchLabels:
      cilium-bgp: lab
  bgpInstances:
  - name: asn-64512
    localASN: 64512
    peers:
    - name: router-64513
      peerASN: 64513
      peerAddress: 192.0.2.1
      peerConfigRef:
        name: lab-peer
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata:
  name: lab-peer
spec:
  timers:
    connectRetryTimeSeconds: 120
    holdTimeSeconds: 90
    keepAliveTimeSeconds: 30
  gracefulRestart:
    enabled: true
    restartTimeSeconds: 120
  families:
  - afi: ipv4
    safi: unicast
    advertisements:
      matchLabels:
        advertise: lab
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: lab-pod-cidrs
  labels:
    advertise: lab
spec:
  advertisements:
  - advertisementType: PodCIDR
```

peer の広告 selector は `advertise: lab` に一致し、`peerConfigRef` は `lab-peer` を参照します。Graceful Restart には互換性のある peer の動作と適切な timer が必要です。停止した datapath を保持したり、アプリケーションの可用性を保証したりはできません。BGP は到達可能性を広告しますが、**ローカルの datapath route を設定したり**、DNS レコードを作成したりはしません。

ルーティングラボ用に適切な設定を準備して適用した後、Cilium の状態と外部ルーターが受信した route の両方を確認してください。

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
cilium bgp peers
cilium bgp routes advertised ipv4 unicast
```

往路と復路の実際の通信は別にテストしてください。以前から存在する HTTP ポリシーや根拠のない改善率を、古いリリースの新機能として説明しないでください。Cilium 1.18 またはそれ以前のマイナーバージョンから移行する場合は、該当するリリースノートを確認してください。

## 次のステップ

個々の経路を検証するには、[IPAM とポリシー](04-ipam-policy.md)、[L2～L7 ネットワーク](05-l2-l7-networking.md)、[セキュリティ／可視性](06-security-visibility.md)の各章を参照してください。測定結果にはベンチマーク条件と制約を添え、段階的な更新と復旧をリハーサルしてください。

パフォーマンステストで作成した正確な名前空間を確認してから、そのリソースを削除してください。

```bash
set -eu
PERF_NS=cilium-advanced-perf-1
LAB_OWNER=$(kubectl get namespace "$PERF_NS" -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-advanced-07
kubectl delete namespace "$PERF_NS"
```

## 主な参考資料

- [パフォーマンス調整ガイド](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/performance/tuning.rst)
- [Chart の値](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Chart の ConfigMap テンプレート](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/templates/cilium-configmap.yaml)
- [マップサイズ](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/ebpf/maps.rst)
- [マップサイズの実装](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/pkg/option/config.go)
- [アップグレードガイド](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/upgrade.rst)
- [アップグレードの制約](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/upgrade-warning.rst)
- [BGP の設定](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)
- [BGP の運用](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [Bandwidth Manager](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/bandwidth-manager.rst)
- [Egress Gateway](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/egress-gateway/egress-gateway.rst)
- [過去のスケーラビリティレポート](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/performance/scalability/report.rst)
- [コミュニティのロードマップ](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/community/roadmap.rst)
- [Linux IP sysctl](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html)

[メインページに戻る](README.md)

## クイズ

運用上の制約と診断コマンドは、[このトピックのクイズ](../../quizzes/networking/cilium/07-advanced-topics-quiz.md)で確認してください。
