# EKSノードのカーネルチューニング

> **対象バージョン**: Amazon Linux 2023（カーネル6.1／6.12／6.18）、Kubernetes 1.33以降（Amazon EKS）
> **最終更新日**: 2026年9月13日

## このドキュメントで扱うこと

- EKSノードで何を変更し、何を既定のままにするか、その判断方法
- EKSでカーネルパラメーターを適用する実際の経路と、それぞれの落とし穴
- AL2023のカーネル移行（6.1から6.18）が運用上何を意味するか

## まず、ほとんどの設定は変更しない

これがこのドキュメントでもっとも重要な助言です。

カーネルの既定値は、**幅広いワークロードで妥当に動作するように**選ばれています。またTCPバッファーの自動調整など、多くの機能は負荷に応じてカーネルが調整します。根拠のないチューニングには3つのコストがあります。

| 問題 | 例 |
|---|---|
| **再現できない設定** | ノードごとに値が異なり、障害を再現できない |
| **カーネルアップグレード時の破損** | 6.1で使えた設定が6.18では名前や場所が変わる、または削除される |
| **自動調整を妨げる** | ソケットごとに`SO_RCVBUF`／`SO_SNDBUF`を明示すると、そのソケットの自動サイズ調整が無効になる。sysctlの範囲設定は別の制御 |

**チューニングの前提条件は測定です。** 次の順序で進めてください。

1. 症状を特定する（遅延、破棄、スループットなど）
2. **まず破棄カウンターを確認する**: `conntrack -S`の`insert_failed`、`tc -s qdisc`の`dropped`、`ethtool -S`のNIC破棄数
3. そのカウンターが増加している箇所のパラメーターだけを変更する
4. 同じ条件で変更前と変更後を測定する
5. 変更内容と理由をコードとして記録する（以下の適用経路を参照）

測定方法については、[Podネットワークベンチマーク](../networking/06-pod-network-benchmark.md)のフィクスチャを参照してください。

## 適用経路: EKSでカーネルパラメーターを変更する方法

方法はいくつかあり、**それぞれ適用範囲と落とし穴が異なります。** 実務では違いを理解することが重要です。

| 経路 | 適用範囲 | 永続性 | 注意点 |
|---|---|---|---|
| **ノードのブートストラップ**（User Data／`nodeadm`） | ノード全体 | ノード置換時に再適用 | AL2023では`nodeadm`設定を使う。最も標準的 |
| **Bottlerocket設定**（`settings.kernel.sysctl`） | ノード全体 | ノード設定として管理 | Bottlerocketはイミュータブルなので、この方法だけを使う |
| **Podの`securityContext.sysctls`** | **Podのnet名前空間だけ** | Pod仕様 | **名前空間スコープのsysctlのみ。** 多くの`net.*`が該当する |
| **特権init DaemonSet** | ノード全体 | Pod再起動時に再適用 | よく使われるが、特権が必要（セキュリティレビューの対象） |
| **`kube-proxy-config` ConfigMap** | conntrack関連 | kube-proxyが管理 | **EKSではCLI引数より優先される** |
| **Karpenterの`EC2NodeClass`** | ノードグループ | ノードのプロビジョニング時 | User Dataを宣言的に管理する |

### 見落としやすい2つの点

**1つ目は、名前空間スコープのsysctlと、そうでないsysctlの違いです。** 多くの`net.*`値はnet名前空間単位で設定できるため、Podの`securityContext.sysctls`で変更できます。一方、`vm.*`、`fs.*`、`net.netfilter.nf_conntrack_max`など**一部の値はノード全体に適用**され、Pod仕様からは変更できません。

また、kubeletは既定では「unsafe」sysctlを拒否します。必要な場合は、ノード設定で`--allowed-unsafe-sysctls`を明示的に許可します。

**2つ目は、kube-proxyがconntrack設定を上書きすることです。** [コンテナを支えるカーネル機能](./01-container-primitives.md)で触れましたが、実務でよく遭遇する落とし穴なので繰り返します。EKSでは既定で`kube-proxy-config` ConfigMapが用意され、**コマンドライン引数より優先されます**。ブートストラップでsysctlを引き上げても、kube-proxyが元に戻す場合があります。

::: warning 要確認
Bottlerocketでは、`settings.kernel.sysctl`でconntrackの上限を引き上げても反映されないという報告があります（2024年9月に報告された[bottlerocket-os/bottlerocket#4221](https://github.com/bottlerocket-os/bottlerocket/issues/4221)）。原因は**kube-proxy設定ファイル（`/var/lib/kube-proxy-config/config`）がコマンドライン引数より優先されること**です。

kube-proxyの設定ファイルを使う場合、上限管理をノードのsysctlへ意図的に委ねるには、**設定内の`conntrack.maxPerCore`／`conntrack.min`フィールド**を変更します。両方を0に設定しても、`--config`に無視されるCLIフラグへ依存してよい理由にはなりません。適用前にマネージドアドオンによる再調整とメモリの余裕を確認してください。

**特定のBottlerocketリリースで解決済みかどうかは確認できませんでした。** どの経路を使っても、適用後にノード上の実際の値を確認してください。

```bash
# Check the actually applied values on the node
cat /proc/sys/net/netfilter/nf_conntrack_max
cat /proc/sys/net/netfilter/nf_conntrack_count
conntrack -S | head
```
:::

## カーネルバージョン: AL2023の6.1から6.18への移行

現在、把握しておくべき変更です。

| 日付 | 内容 |
|---|---|
| 2023年3月 | カーネル**6.1**を搭載したAL2023をリリース |
| 2025年4月 | カーネル**6.12**のサポートを追加 |
| **2026年8月17日** | **`al2023-ami-kernel-default` AMIの既定カーネルを6.1から6.18に変更** |

**ここから2つの点が導かれます。**

既定カーネルの**AMIファミリー**は変更されましたが、ノードの置換時には起動テンプレートまたはプロビジョニングポリシーで選択したAMIが使われます。AMI IDを固定している場合、新しいノードを起動しただけではカーネルは変わりません。latest／defaultを再取得する設定では、新しいカーネルが選ばれる可能性があります。EKS最適化AMIには独自のリリース選択があります。

カーネルを固定する必要がある場合は、**バージョンを指定したAMI**（`al2023-ami-kernel-6.1-*`など）を明示的に使ってください。

**カーネル変更時に確認すること:**

| 項目 | 理由 |
|---|---|
| チューナブルの存在と場所 | バージョン間で名前が変わる、sysctlからdebugfsへ移動するなどの変更がある |
| カーネルモジュールに依存するコンポーネント | eBPFプログラム、特定のCNI機能、GPUドライバー、カスタムモジュール |
| スケジューラーの動作 | 6.6以降はEEVDF（後述）。遅延に敏感なワークロードで差が出る場合がある |
| パフォーマンスの退行 | カーネルバージョンごとにベンチマークを再測定する |

**推奨事項**: カーネル移行は**Kubernetesのバージョンアップグレードと同じ重要度**で扱います。同じカーネルを使ったステージングで検証し、性能ベースラインを再測定してから本番へ展開してください。

## CPU: スケジューラーとスロットリング

### EEVDF: 6.6での変更

Linux 6.6では、CFSのタスク選択ロジックが**EEVDF**（Earliest Eligible Virtual Deadline First）に置き換わりました。

正確に理解すべきなのは、**何が変わり、何が変わらなかったか**です。

| 変更された点 | 変更されていない点 |
|---|---|
| **次に実行するタスクの選び方**（仮想デッドラインに基づく） | `vruntime`の仕組み、重みの計算 |
| 起床したタスクのプリエンプション判断: ヒューリスティック（`sched_wakeup_granularity_ns`）ではなく**デッドラインを比較** | グループスケジューリング（cgroupの`cpu.weight`）、負荷分散 |

したがって、これは**CFS全体の置き換えではなく、タスク選択ロジックの進化**と捉えるのが正確です。変更は`fair_sched_class`内にあります。

運用上は、遅延に敏感なワークロードで**起床時の遅延特性が変わる場合があります**。通常は改善しますが、カーネル6.1から6.18へ移行してp99が変化した場合、これも原因候補の1つです。

### チューナブルが実際にある場所

カーネルソース（`kernel/sched/debug.c`）で確認した内容:

| 項目 | 状況 |
|---|---|
| `sched_latency_ns` | **削除済み**。`kernel/sched/fair.c`に参照が残っていない |
| `sched_wakeup_granularity_ns` | **削除済み**（同上） |
| **`/sys/kernel/debug/sched/base_slice_ns`** | **現在の相当値**。内部変数は`sysctl_sched_base_slice`で、debugfsでは`base_slice_ns`として公開 |

そのため、CFS時代の遅延／プリエンプションに関するチューナブルはなくなり、調整対象は基本タイムスライス（`base_slice_ns`）に集約されています。この値は`/sys/kernel/debug/sched/base_slice_ns`で公開され、名前に`sched_`の接頭辞は付きません。

別の方法として、EEVDFではタスク自身が`sched_setattr()`システムコールで**タイムスライスを要求**できます。遅延に敏感なアプリケーションでは、グローバルなチューナブルを変更するより適しています。

**スケジューラーのチューナブルは、現在も推奨される調整対象ではありません。** debugfsはカーネルのデバッグ用インターフェースであり、本番環境でマウントされているとは限りません。多くの場合、アプリケーションのスレッド数またはcgroup上限を調整する方が適切です。

### CPU上限: スロットリングが実際の問題である場合

[コンテナを支えるカーネル機能](./01-container-primitives.md)で説明したとおり、CPU上限は帯域幅の制限であり、使用率が低くても遅延を生じさせます。

**診断:**

```bash
# cgroup v2: from the container's cgroup path
cat cpu.stat
# nr_periods, nr_throttled, throttled_usec
```

`nr_throttled / nr_periods`が無視できない割合なら、上限が原因です。

**対応の優先順位**（設計については[リソース最適化](../ops/10-resource-optimization.md)を参照）:

1. **アプリケーションが認識するCPU数を上限に合わせます**。もっとも見落とされる原因です。コンテナ内のランタイムがノードの全コアを認識し、その数のスレッドを起動すると、クォータをすぐに使い切ります。JVMの`-XX:ActiveProcessorCount`、Goの`GOMAXPROCS`、Node.jsの`UV_THREADPOOL_SIZE`などを上限に合わせてください。
2. **ノード安定性とのトレードオフを考慮して上限を引き上げます。**
3. **遅延に極端に敏感な場合は上限の削除を検討します**が、requestsとノード分離を使ってnoisy neighborのリスクを管理します。
4. `cpu.pressure` PSIで実際の停止時間を確認します。

**CPU Managerのstaticポリシー**（コア専有）は、遅延に敏感なワークロードに使える別の仕組みです。ノード使用率が下がるため、採用理由が必要です。

## メモリ: OOMと圧力

### 変更するものと既定のままにするもの

| パラメーター | 推奨事項 |
|---|---|
| `vm.swappiness` | Kubernetesは従来swap無効を前提としてきました。swapサポートは成熟してきていますが、EKSで有効にする前に**サポート状況を確認してください** |
| `vm.overcommit_memory` | **既定値を維持します**。変更するとコンテナのメモリ確保失敗の挙動が予測しにくくなります |
| `vm.min_free_kbytes` | メモリ回収の余裕に関する値です。低すぎると急な割り当てでOOMになるおそれがあります。**大容量ノードでバーストが激しい場合に限り検討してください** |
| `vm.max_map_count` | Elasticsearch／OpenSearchなどで**実際に必要となる調整**です。既定値が低く、mmap上限に達します |
| `kernel.pid_max` | 高密度ノードでPIDが枯渇した場合に調整します |

`vm.max_map_count`は、実際に必要となる例としてよく挙がります。OpenSearch系のソフトウェアは多くのファイルをmmapし、既定値では起動に失敗します。「正当化されたチューニング」のよい例です。症状が明確で、パラメーターが直接の原因であり、ベンダーが値を文書化しています。

### カーネルパラメーターの前にkubelet予約を確認する

ノードの安定性には、カーネルのチューニングよりも**kubeletのリソース予約**の方が大きな影響があります。

| 設定 | 目的 |
|---|---|
| `--system-reserved` | OSとシステムデーモンのために予約する |
| `--kube-reserved` | kubeletとコンテナランタイムのために予約する |
| `--eviction-hard` | このしきい値に達したらPodをevictする |

予約が足りないと、Podがノードのメモリをすべて消費し、**カーネルまたはkubelet自体がOOMになります**。ノードは`NotReady`になり、そこで動くすべてのPodが影響を受けます。個々のPodでOOMが起きるよりはるかに深刻です。

**OOMよりevictionの方が望ましい結果です。** evictionではKubernetesが制御された方法でPodを移動しますが、OOM killerはカーネルがプロセスを突然終了させます。カーネルOOMより前にKubernetesが介入するよう、`--eviction-hard`を設定してください。

### PSIで圧力を観測する

cgroup v2のPSIは、使用量より適切なシグナルを示します。

```bash
# Whole node
cat /proc/pressure/memory
cat /proc/pressure/cpu
cat /proc/pressure/io

# A specific cgroup
: "${KERNEL_CGROUP_PATH:?Set the inspected cgroup directory}"
cat "$KERNEL_CGROUP_PATH/memory.pressure"
```

`some avg10`は、直近10秒のうち**少なくとも1つのタスクがそのリソースを待って停止していた時間の割合**です。使用量グラフが落ち着いているのにこの値が増加する場合は、回収または競合に時間を使っています。

## ネットワーク: 根拠のある調整

### conntrack

ここまで説明したとおり、**実際の障害原因としてもっとも多い項目**です。

| 項目 | 内容 |
|---|---|
| 症状 | 新規接続が通知なく破棄され、アプリケーションにはタイムアウト／拒否だけが見える |
| 照合する証拠 | `conntrack -S`で`insert_failed`が増加していること。これだけではテーブル枯渇の証明にならない |
| 補助シグナル | `dmesg`の`nf_conntrack: table full`、`nf_conntrack_count`／`nf_conntrack_max`の比率 |
| 調整経路 | **`kube-proxy-config` ConfigMapの`conntrack.maxPerCore`／`conntrack.min`**（EKSでは優先される） |
| コスト | エントリーごとにノードメモリを使用。無制限に引き上げられない |
| 根本対策 | 接続の入れ替わりを減らし、データプレーン／マップの負荷を調べる。headless DNSだけでは追跡は無効にならない |

`maxPerCore`を使う理由も理解しておきましょう。絶対値ではなくコア数に比例するため、同じ設定がノードサイズに応じて変わります。`nf_conntrack_max`のような絶対値を固定すると、小さなノードでは過剰に、大きなノードでは不足する値になります。

タイムアウトも調整できます。既定値が非常に長い`nf_conntrack_tcp_timeout_established`を短くすると、エントリーを早く回収できます。ただし、正当に長時間維持する接続を切断しないよう注意してください。

### ソケットバッファーとキュー

| パラメーター | 使用する状況 |
|---|---|
| `net.core.somaxconn` | **acceptキューがあふれた場合**。接続が集中するサーバーでよく調整する |
| `net.ipv4.tcp_max_syn_backlog` | SYNが集中する場合 |
| `net.core.netdev_max_backlog` | **受信softirqの処理が追い付かない場合** |
| `net.ipv4.tcp_rmem`／`tcp_wmem` | TCPサイズ調整の上限／既定値。これを変更しても自動調整が単独で無効になるわけではない。測定したBDP／メモリの証拠に基づく場合だけ調整する |
| `net.ipv4.ip_local_port_range` | **送信元ポートが枯渇した場合**。アウトバウンド通信が多いノードで実際に起きる |
| `net.ipv4.tcp_tw_reuse` | TIME_WAITが蓄積した場合。動作を理解したうえで適用する |

**`somaxconn`と`ip_local_port_range`は、根拠のある調整の代表例です。前者は証拠となるカウンター**（`nstat`の`TcpExtListenOverflows`）があり、後者は接続失敗として直接確認できます。

測定結果が変更を正当化しない限り、妥当な`tcp_rmem`／`tcp_wmem`の範囲を維持してください。Linuxのドキュメントによると、明示的な**ソケット単位の`SO_RCVBUF`／`SO_SNDBUF`設定**は該当ソケットの自動サイズ調整を無効にします。sysctlでmin／default／max値を設定することとは混同しないでください。

### qdisc

ノード内で破棄が確認された場合（`tc -s qdisc`の`dropped`）、ここを調整対象とします。

- **`fq_codel`**: バッファーブロート対策（遅延が問題の場合）
- **`fq`**: ペーシング（bbr利用時）
- キュー長（`txqueuelen`）を増やすと破棄は減りますが、**遅延が増えます**。トレードオフを理解して決めてください。

### 割り込みの分散

`/proc/interrupts`で1つのコアに偏り、`mpstat -P ALL`でそのコアの`%soft`が急増している場合は、RSS／RPS／RFSを確認します。ただし、**現在のENAドライバーとインスタンスタイプは既定でマルチキューとRSSを使用する**ため、これは問題になることがまれです。

### kube-proxyモード

ノードのカーネルパラメーターではありませんが、データプレーン性能に最も大きく影響します。

| 状況 | 推奨事項 |
|---|---|
| iptablesモードでServiceが多い | **nftablesモードを検討する**。1.33でGA、O(1)検索と差分更新に対応。カーネル5.13以降が必要（AL2023は満たす） |
| **IPVSモードを実行中** | **移行計画が必要**。1.35で非推奨、上流は1.40で既定無効化、1.43で削除を予定。推奨される移行先はnftables |
| 既定のままにする | nftablesがGAでも、**既定は引き続きiptables**です。切り替えは明示的に判断します |

## ストレージ

| パラメーター | 内容 |
|---|---|
| **IOスケジューラー** | NVMeでは`none`（または`mq-deadline`）が一般的です。複雑なスケジューラーを使ってもNVMeではあまり効果がありません |
| `vm.dirty_ratio`／`dirty_background_ratio` | 書き込みバッファー量。書き込みバースト時の遅延挙動に影響する |
| **エフェメラルストレージ** | カーネルパラメーターよりも、実際には**overlayfsのcopy-upコスト**が問題です。書き込みの多いパスはボリュームに移す（[コンテナを支えるカーネル機能](./01-container-primitives.md)） |
| **EBS性能** | カーネルの問題ではなく、ボリュームタイプ、IOPS、スループット設定の問題（[EBS gp2とgp3のベンチマーク](../storage/01-ebs-gp2-gp3-benchmark.md)） |

## ワークロード別

症状から確認するための表です。

| ワークロード | よく必要となる調整 | 証拠となるカウンター |
|---|---|---|
| **多数の接続を扱うゲートウェイ／プロキシ** | conntrack上限、`somaxconn`、`ip_local_port_range` | `insert_failed`、`TcpExtListenOverflows`、ポート枯渇 |
| **遅延に敏感（金融取引、リアルタイム）** | CPU上限の見直し、CPU Manager staticポリシー、`fq_codel` | `cpu.stat`のスロットリング、`cpu.pressure` |
| **高スループット（バッチ、データ処理）** | バッファー上限（長距離通信のみ）、`netdev_max_backlog` | qdiscの`dropped`、softirqの偏り |
| **検索／インデックス（OpenSearchなど）** | **`vm.max_map_count`**、ファイル記述子の上限 | 起動失敗ログ |
| **高密度ノード** | `kernel.pid_max`、kubelet予約、evictionしきい値 | PID枯渇、ノードの`NotReady` |
| **ブロックチェーンノード** | ファイル記述子、ディスクIOPS、ソケットバッファー | [ブロックチェーンノードの運用](../blockchain/02-nodes-on-eks.md) |

## 変更を管理する

長期的にはチューニングそのものより、**どう管理するか**が重要です。

| 原則 | 理由 |
|---|---|
| **コードとして管理する**（Karpenterの`EC2NodeClass`、起動テンプレート、Bottlerocket設定） | ノードごとに値が異なるのを防ぐ |
| **理由をコメントに記録する** | 6か月後に「なぜこの値か」を知る人がいなければ、誰も元に戻せない |
| **ノードグループを分ける** | ワークロードごとに必要なチューニングは異なる。すべてに1つのプロファイルを強制しない |
| **カーネルを固定するか、移行計画を立てる** | `kernel-default` AMIは気付かないうちにカーネルが変わる |
| **適用後に実値を確認する** | 特にconntrack。別のコンポーネントに上書きされる場合がある |
| **同じ条件で変更前後を測定する** | 測定なしのチューニングは迷信になる |

## まとめ

- **大半は既定のままにしてください。** カーネルは負荷に応じて自動調整します。根拠のない調整は再現できない設定や、カーネルアップグレード時の問題を生みます。
- チューニングの前提条件は測定です。**破棄カウンター**（`insert_failed`、qdiscの`dropped`、NICの破棄数）から確認します。
- 選択したAMIと実行中のカーネルを確認してください。既定AMIファミリーは新しいものへ移行する場合がありますが、AMI IDを固定するとノード置換だけでは自動変更されません。
- CPUスロットリングの根本原因は、多くの場合、**アプリケーションが認識するCPU数とクォータの不一致**です。`GOMAXPROCS`／`ActiveProcessorCount`から確認してください。
- ノードの安定性には、カーネル調整よりも**kubeletの予約とevictionしきい値**が有効です。カーネルOOMよりevictionの方が望ましい動作です。
- 根拠があれば調整しやすい代表例は、**conntrack上限、`somaxconn`、`ip_local_port_range`、`vm.max_map_count`です**。いずれも直接的な証拠となるカウンターがあります。
- TCPのsysctl上限と、ソケット単位の自動調整の上書きは別のものです。測定の証拠がある場合だけ調整してください。
- **IPVSモードを実行している場合は移行計画が必要です**（1.35で非推奨、1.40で既定無効化、1.43で削除を予定）。展開前に、以下にリンクした保守中のKEP-5495スケジュールを確認してください。

## 参考資料

- [Amazon Linux 2023: Linuxカーネルの更新](https://docs.aws.amazon.com/linux/al2023/ug/kernel-update.html)
- [Amazon EKSに最適化されたAmazon Linux 2023 AMI](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
- [EKSノードでnf_conntrack_maxの上限を引き上げる](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [nftablesモードでのkube-proxy実行: EKSのベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [KEP-5495: kube-proxyのIPVSモードを非推奨化](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [EEVDFスケジューラー: Linuxカーネルドキュメント](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [kernel/sched/debug.c: debugfsチューナブルの定義](https://github.com/torvalds/linux/blob/master/kernel/sched/debug.c)
- [bottlerocket-os/bottlerocket#4221: conntrack上限が適用されない](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [システムデーモン用のコンピュートリソースを予約する（Kubernetes）](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Kubernetesクラスターでsysctlを使う](https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/)
- [リソース最適化](../ops/10-resource-optimization.md) / [Podネットワークベンチマーク](../networking/06-pod-network-benchmark.md)
