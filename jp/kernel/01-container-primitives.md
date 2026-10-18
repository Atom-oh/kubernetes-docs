# コンテナを支えるカーネル機能

> **対象バージョン**: Linux 6.1／6.12／6.18（Amazon Linux 2023）、Kubernetes 1.25以降（cgroup v2）
> **最終更新日**: October 16, 2026

## このドキュメントで扱うこと

- コンテナを成立させるカーネル機能の組み合わせと、カーネルに「コンテナ」という単一のオブジェクトがないこと
- cgroup v1からv2への移行で運用上何が変わったか（特にOOMの診断）
- Kubernetesのネットワーキングにおけるnetfilterとconntrackの位置付け

## まず、「コンテナ」はカーネルに存在しない

コンテナを理解する出発点です。カーネルには`struct container`も、コンテナを作る単一のシステムコールもありません。

コンテナとは、**複数の独立したカーネル機能を組み合わせる慣習**です。containerdやruncなどのランタイムがプロセスを起動するときに、これらの機能をまとめて適用します。

| 目的 | カーネル機能 |
|---|---|
| **見えるものを制限する（分離）** | 名前空間 |
| **利用できる量を制限する** | cgroup |
| **実行できる操作を制限する** | capability、seccomp、LSM（AppArmor／SELinux） |
| **ファイルシステムを構成する** | overlayfs（ユニオンマウント） |
| **トラフィックを流す** | veth、ブリッジ／ルーティング、netfilter |

複数機能の組み合わせであることから、運用上2つの結論が導かれます。

**1つ目に、分離はすべてかゼロかではありません。** 一部の名前空間を共有しながら、別のものは分離できます。KubernetesのPodがその例です。同じPodにあるコンテナはネットワークとIPCの名前空間を**共有**しますが、マウントとPIDの名前空間は通常**分離**します。そのため、Pod内のコンテナ同士は`localhost`で通信でき（ネットワークを共有）、互いのファイルシステムは見えません（マウントを分離）。

**2つ目に、設定し忘れた分離は、気付かれない穴になります。** カーネルに「コンテナを作る」操作はないため、ランタイムがseccompプロファイルを適用しなければ、ワークロードは単にプロファイルなしで実行されます。コンテナセキュリティがランタイムとポリシーの設定に関わるのはこのためです。

## 名前空間: 何が見えるか

名前空間は、カーネルリソースの「名前空間」を**分離**します。そのため、名前や番号が同じでも、名前空間が違えば別のものを指します。

| 名前空間 | 分離するもの | Pod内の扱い |
|---|---|---|
| **mnt** | マウントポイント | コンテナごと |
| **pid** | プロセスID | コンテナごと（`shareProcessNamespace: true`の場合はPod内で共有） |
| **net** | インターフェース、ルーティングテーブル、netfilterルール、ソケット、ポート | **Podごとに共有** |
| **ipc** | System V IPC、POSIXメッセージキュー | Pod内で共有 |
| **uts** | ホスト名、ドメイン名 | Pod内で共有 |
| **user** | UID／GIDのマッピング | 既定では使用しない（後述） |
| **cgroup** | cgroupのルートパス | コンテナごと |
| **time** | 起動時刻、単調増加時計（5.6以降） | 使用しない |

### net名前空間がPodの境界になる理由

Podの識別はここで決まります。KubernetesはPodごとに1つのnet名前空間を作り（pauseコンテナが保持）、**そのPodの全コンテナを同じnet名前空間に入れます。**

その結果、次のようになります。

- Pod内のコンテナは**同じIPと同じポート空間を共有**します。そのため、1つのPod内にある2つのコンテナが両方とも8080番ポートをバインドすることはできません。
- `localhost`で通信できます。これがサイドカーパターンの基盤です。
- **netfilterルールもnet名前空間ごとに存在**します。そのため、サイドカーメッシュのinitコンテナはPodのnet名前空間内にiptablesルールを設定でき、そのルールはノード全体には影響しません（[VPC Latticeのカーネルデータパス](../service-mesh/vpc-lattice/07-kernel-datapath.md)を参照）。
- ルーティングテーブルも分離されます。Pod内の`ip route`はノードのルーティングテーブルではありません。

### user名前空間が長い間既定ではなかった理由

user名前空間はコンテナのUID／GIDをホスト側の別の範囲にマッピングします。これにより、権限が昇格した場合の多くの操作権限は小さくなりますが、カーネル脆弱性など別の権限昇格経路による侵害を**防げる保証はありません**。

それでも長い間、既定ではありませんでした。理由は**ファイル所有権**です。ボリューム上のファイルはホストUIDで記録されます。コンテナから別のUIDに見えると、権限が一致しません。解決にはマウント時のUID変換（idmapped mount、カーネル5.12以降）が必要であり、ストレージドライバーやCSIも対応していなければなりません。

### Kubernetesのuser名前空間サポート状況

[機能ゲートのリファレンス](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)と[v1.36のGA告知](https://kubernetes.io/blog/2026/04/23/kubernetes-v1-36-userns-ga/)によると、成熟度は次のとおりです（設計文書: [KEP-127](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/kep.yaml)）。

| 段階 | バージョン |
|---|---|
| alpha | v1.25 |
| beta | v1.30（v1.33から既定で有効） |
| **安定版（GA）** | **v1.36** |

機能ゲートは`UserNamespacesSupport`で、kubeletとkube-apiserverに適用されます。**v1.36ではGAになったため、機能ゲートを有効にしなくても`hostUsers: false`が機能します。**

::: warning 要確認
ここに記載した成熟度は上流Kubernetesのものです。**EKSがそのバージョンを提供しているか、コンテナランタイムやCSIドライバーがidmapped mountをサポートしているかは別の問題です**。採用前に、EKSの対応バージョンとランタイム／ストレージの組み合わせを確認してください。
:::

## cgroup: 利用できる量を制御する

cgroup（control group）は、プロセスのグループが使うリソースを**測定し、制限します**。Kubernetesの`requests`／`limits`が最終的に適用される場所です。

### v1とv2の構造的な違い

| 項目 | cgroup v1 | cgroup v2 |
|---|---|---|
| **階層** | コントローラー（cpu、memory、blkioなど）ごとに**別のツリー** | **統合された単一ツリー** |
| **プロセスの所属** | コントローラーごとに別々のグループに所属可能 | 1つのグループだけに所属 |
| **メモリとIOの連携** | 難しい（別ツリー間では連携できない） | 可能（同一ツリー内） |
| **圧力情報** | なし | **PSI**（`cpu.pressure`、`memory.pressure`、`io.pressure`） |
| **CPU上限の表現** | `cpu.cfs_quota_us`／`cpu.cfs_period_us` | `cpu.max`（1つのファイルに「quota period」） |
| **メモリ上限の表現** | `memory.limit_in_bytes` | `memory.max`と、ソフトな圧力上限の`memory.high` |
| **AL2023 EKS AMI** | - | **既定** |

v1の「コントローラーごとに別のツリー」が実際に問題となったのは、**メモリ回収とIOの連携**です。メモリが不足してページキャッシュを破棄しなければならない場合、その回収処理自体がディスクIOを発生させます。しかしv1では2つのコントローラーが互いを認識しませんでした。v2では統合された同じ階層で両方を扱います。

### 2026年10月の更新: cgroup v1の非推奨化が進む

Kubernetesブログにcgroup v1からv2への移行状況がまとめられています（[Kubernetesにおけるcgroup v2への移行](https://kubernetes.io/blog/2026/10/06/kubernetes-cgroups-v2-shift/)、2026-10-06）。cgroup v2の管理はv1.25から安定版で、cgroup v1のサポートはv1.31から保守モードです。**v1.35以降、kubeletの`failCgroupV1`は既定で`true`となり、通常はcgroup v1ノード上でkubeletが起動しなくなります。** kubelet設定で`failCgroupV1: false`にするのは一時的な上書きであり、完全削除はKEP-5573で追跡されています。kubeadmクラスターでは、kubelet v1.35以降のSystemVerification事前確認でcgroup v1はエラーとなり、それより古いkubeletでは警告になります。v1.35より前のリリースを利用している場合は、アップグレード前にすべてのLinuxノードをcgroup v2へ移行してください。

### 運用上もっとも大きな変更: OOMの診断

cgroup v2について必ず知っておくべきことがあります。

> **`memory.current`にはページキャッシュが含まれます。**

そのため、アプリケーションが実際に保持するメモリ（anon／RSS）が上限を大きく下回っていても、多くのファイルを読み込むとページキャッシュが積み上がり、`memory.current`が上限に達する場合があります。

ここで重要な違いがあります。**ページキャッシュは回収可能です。** 通常はカーネルが上限に達すると、領域を確保するためにページキャッシュを破棄し、OOMは起きません。問題になるのは**割り当てに回収が追い付かない場合**です。このときOOM killerが動作します。

運用上は次の点に注意してください。

| 誤解 | 実際のところ |
|---|---|
| 「`memory.current`が上限に近いので、OOMが差し迫っている」 | 回収可能なファイルキャッシュが含まれる場合があります。内訳を決めつけず、anon／file／kernelの使用量と圧力を確認してください |
| 「RSSだけ見ればよい」 | RSSが低くても、回収が追い付かないとOOMになる場合があります |
| 「上限を増やせば直る」 | 原因が回収の遅れであれば、再発します |

**診断時に確認する値:**

| ファイル／値 | 意味 |
|---|---|
| `memory.current` | 現在の使用量（ページキャッシュを含む） |
| `memory.stat` → `anon` | 匿名メモリ（アプリケーションが実際に保持するもの） |
| `memory.stat` → `file` | ページキャッシュ |
| `memory.events` → `oom`／`oom_kill` | OOM発生回数／killの回数 |
| `memory.events` → `high`／`max` | ソフト／ハード上限に達した回数 |
| `memory.pressure`（PSI） | メモリ圧力により停止した**時間の割合** |

**PSIは特に有用です。** 使用量（どれだけ使ったか）ではなく、圧力（その結果どれだけ待ったか）を示します。`memory.pressure`の`some avg10`が上昇している場合は、メモリ回収に時間を使っていることを示します。使用量のグラフだけでは分からない情報です。

### CPU上限とスロットリング: 使用率が低くても遅くなる理由

CPU上限は**帯域幅の制限**です。`cpu.max`が`20000 100000`なら、「100 msの期間ごとに最大20 msまで」という意味です。

直感に反する結果が生じます。複数スレッドで短時間にまとめて処理するアプリケーションは、期間の早い段階でクォータを**使い切り、期間の終わりまで強制停止されます**。平均使用率は20%程度と低く見えるのに、遅延が急増します。

複数スレッドではさらに顕著です。4スレッドを同時に動かすと、20 msのクォータは実時間5 msで使い切られます。残りの95 msは待ち時間です。

**診断:** `cpu.stat`の`nr_throttled`（スロットリングされた期間数）と`throttled_usec`（合計スロットリング時間）を確認します。`nr_throttled`が`nr_periods`に対して無視できない割合なら、上限が原因です。

**対応の方向性**（requests／limitsの設計は[リソース最適化](../ops/10-resource-optimization.md)を参照）:

- 上限を引き上げるか削除する（ノードの安定性とのトレードオフがある）
- アプリケーションのスレッド数を上限に合わせる（JVMの`-XX:ActiveProcessorCount`、Goの`GOMAXPROCS`など）。**コンテナが認識するCPU数と実際のクォータが一致していないことが、根本原因である場合がよくあります**
- `cpu.pressure` PSIで実際の停止時間を確認する

## 権限: 何ができるか

分離（名前空間）と上限（cgroup）を設定しても、プロセスが実行できる**操作**を減らすことは別の層です。

| 機能 | 役割 | Kubernetesでの設定 |
|---|---|---|
| **capability** | root権限を細かな単位（`CAP_NET_ADMIN`、`CAP_SYS_ADMIN`など）で付与／削除する | `securityContext.capabilities.add/drop` |
| **seccomp** | 許可する**システムコール**を制限する | `securityContext.seccompProfile`（`RuntimeDefault`を推奨） |
| **LSM**（AppArmor／SELinux） | ポリシーでファイルとネットワークへのアクセスを制御する | `securityContext.appArmorProfile`など |
| **no_new_privs** | setuidバイナリによる権限昇格を防ぐ | `allowPrivilegeEscalation: false` |

この3層は異なる問いに答えます。capabilityは「この権限を持っているか」、seccompは「このシステムコールを呼べるか」、LSMは「この対象にアクセスできるか」を判断します。**どれか1つだけでは不十分であり、重ねて適用するのが一般的です。**

`CAP_NET_ADMIN`についても触れておきます。サイドカーメッシュのinitコンテナはiptablesルールの設定にこれを必要とします。そのため、メッシュを採用すると「なぜこのPodにNET_ADMIN権限があるのか」というセキュリティレビュー上の問いが生じます。

## netfilterとconntrack: Kubernetesネットワーキングの実態

### netfilter

netfilterは、カーネルのネットワークスタック内に定義された地点で**フック**を提供するフレームワークです。`iptables`、`nftables`、`ipvs`は、これらのフックを使うユーザー空間ツール、またはその上に構築された実装です。

主なフック:

| フック | タイミング |
|---|---|
| `PREROUTING` | パケット到着時、ルーティング判断の**前**（DNATの地点） |
| `INPUT` | ローカルプロセス宛てのパケット |
| `FORWARD` | 通過中のパケット |
| `OUTPUT` | ローカルから送信されるパケット |
| `POSTROUTING` | ルーティング後、送出直前（SNAT／MASQUERADEの地点） |

Kubernetesでは、これらのフックが次のように使われます。

- **Service ClusterIPからPod IPへの変換**: `PREROUTING`／`OUTPUT`でDNAT
- **Podから外部への通信における送信元変換**: `POSTROUTING`でMASQUERADE
- **NetworkPolicy**: CNIが`FORWARD`などにルールを挿入（Calicoのiptablesデータプレーン）
- **サイドカーメッシュの通信横取り**: Podのnet名前空間内の`OUTPUT`／`PREROUTING`でREDIRECT

### kube-proxyのモード: iptables、IPVS、nftables

Serviceの実装には3つの方式があり、**2025～2026年に状況が変わりました。**

| モード | ルール評価 | 状況 |
|---|---|---|
| **iptables** | ルールチェーンの検索コストはルール配置によって異なる。現在のkube-proxyは更新を最適化 | 明示的に変更しなければ既定。インストール済み実装を確認する |
| **IPVS** | カーネル内のL4ロードバランサー。ハッシュ方式でO(1) | **Kubernetes 1.35（2025年12月）で非推奨**。1.40で既定無効化、1.43で削除を予定 |
| **nftables** | O(1)検索と**差分ルール更新** | **Kubernetes 1.33でGA**（1.29でalpha、1.31でbeta）。ワーカーノードには**カーネル5.13以降**が必要 |

次のように読み取ってください。

- **大規模クラスターでiptablesモードのボトルネックになるのは、ルール数と更新コストです。** ServiceとEndpointが増えるほどkube-proxyの同期に時間がかかり、その間ルールは最新の状態ではありません。
- **IPVSを使っている場合は、移行計画が必要です。** 上流では1.40で既定無効化、1.43で削除を予定しています。計画時に保守されている[KEP-5495のスケジュール](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)を確認してください。推奨される移行先はnftablesモードです。
- AL2023ノードはカーネル6.xを使うため、nftablesモードのカーネル要件を満たします。
- nftablesがGAになっても、**既定は引き続きiptables**です。明示的に切り替えてください。

### conntrack: 障害原因としてもっともよく見られるもの

netfilterがNATを行うには、**接続状態を記憶する**必要があります。送信時にアドレスを書き換えたなら、戻りの通信では元に戻さなければなりません。その状態を保持するカーネルテーブルが`nf_conntrack`です。

kube-proxyのnetfilterモードでは、Service NATにコネクショントラッキングを使います。ただし、**NATを行わないトラフィックも追跡される場合があります**。headless Service、外部エンドポイント、eBPF実装では経路が異なります。Kubernetes Serviceはすべて必ず1つのDNAT経路を通る、と考えないでください。

**枯渇時に何が起きるかが問題の核心です。** 明確なエラーは出ません。新しい接続が**通知なく破棄され**、アプリケーションにはタイムアウトまたは接続拒否が見えます。アプリケーション側から理由を知る方法はありません。

| 観測場所 | 意味 |
|---|---|
| `/proc/sys/net/netfilter/nf_conntrack_count` | 現在のエントリー数 |
| `/proc/sys/net/netfilter/nf_conntrack_max` | 上限 |
| `conntrack -S` → `insert_failed` | 挿入失敗数。これだけで枯渇の証拠とせず、count／max、drop、カーネルログと照合する |
| `conntrack -S` → `drop` | 破棄されたパケット数 |
| `dmesg` → `nf_conntrack: table full, dropping packet` | カーネル警告 |

**EKS固有の注意点が1つあります。** kube-proxyもconntrack値を管理します。また、**EKSでは既定で`kube-proxy-config` ConfigMapが用意され、コマンドライン引数より優先されます。そのため**、ノードでsysctlを引き上げてもkube-proxyが元に戻す場合があります。適切な方法はConfigMapの`conntrack.maxPerCore`／`conntrack.min`を変更し、kube-proxy DaemonSetを再起動することです。

`nf_conntrack_max`を引き上げると**ノードのメモリ使用量が増えます**。エントリーごとにメモリが必要なため、無制限には増やせません。ノードサイズに合った値にする必要があります。具体的な設定は[EKSノードのカーネルチューニング](./03-eks-node-tuning.md)を参照してください。

::: warning 有効なkube-proxy設定を確認する
Bottlerocketでノードのsysctl値がkube-proxyに上書きされた過去の報告があります。`--config`を使う場合は、それが上書きするCLIフラグではなく、**有効な設定**（`conntrack.maxPerCore`、`conntrack.min`）を編集してください。両方を0に設定すると、上限の管理を意図的にノードのsysctlへ委ねます。デプロイ済みのアドオン／バージョンで動作を確認し、適用後のノード値を検証してください。ノードのメモリ予算も維持します。
:::

過去の問題があるからといって、現在のBottlerocketリリースがすべて同じ動作をするとは限りません。有効な設定と、適用後のsysctlの実際の値を確認してください。

### conntrackの負荷を減らす

負荷そのものを減らす方法もあります。

- headless ServiceではService VIPへのDNATを避けられますが、**本質的にconntrackを回避するわけではありません**。
- Ciliumはkube-proxy／netfilterの機能をeBPFマップで置き換えられます。Cilium独自の追跡／マップ負荷と、残存するnetfilter経路を測定してください。
- 接続の再利用は、接続の頻繁な生成を減らします。確立済み接続の容量とタイムアウト動作を確認してください。

## overlayfs: イメージのレイヤーを構成する方法

コンテナイメージのレイヤーを1つのファイルシステムとして見せる仕組みは、特に`overlayfs`と呼ばれる**ユニオンマウント**です。

主な部分は3つです。

| レイヤー | 役割 |
|---|---|
| **lowerdir** | 読み取り専用。イメージのレイヤー（複数を重ねられる） |
| **upperdir** | 書き込み可能。コンテナによる変更 |
| **merged** | コンテナから見える統合ビュー |

運用上重要な性質は**copy-up**です。lowerdirにあるファイルを変更すると、まず**ファイル全体がupperdirへコピー**され、その後に変更されます。そのため、次の点に注意してください。

- **大きなファイルを少し変更するだけでも、全体をコピーするコストがかかります。** 1 GBのファイルの1 byteを書き換える場合でも1 GBがコピーされます。
- コンテナ内で大量に書き込むと、ノードディスク（エフェメラルストレージ）が消費されます。
- **書き込み量の多いパスにはボリューム**（emptyDir、PVCなど）を使ってください。

## まとめ

- カーネルに「コンテナ」はありません。名前空間（分離）＋cgroup（上限）＋capability／seccomp／LSM（権限）＋overlayfs（ファイルシステム）＋netfilter（ネットワーク）の**組み合わせ**です。そのため分離は選択的であり、忘れた分離は気付かれない穴になります。
- **net名前空間がPodの境界です。** IP／ポート空間の共有、`localhost`通信、Pod単位のnetfilterルールはすべてそこから生じます。
- cgroup v2では、**`memory.current`にページキャッシュが含まれます。** OOMを診断するには、`memory.stat`の`anon`、`memory.events`、**PSI（`memory.pressure`）を合わせて確認します**。
- CPU上限は**帯域幅の制限**であり、使用率が低くてもスロットリングで遅延が急増します。証拠として`cpu.stat`の`nr_throttled`を確認します。
- kube-proxyでは、**nftablesが1.33でGAになり、IPVSは1.35で非推奨**となりました。上流は1.40での既定無効化と1.43での削除を予定しています。既定は引き続きiptablesです。
- conntrackが枯渇すると新しい接続が破棄される場合があります。count／max、drop／insertカウンター、ログで診断し、上限を変更する前に有効なkube-proxy設定を確認してください。

次は[カーネルのネットワーキングスタック](./02-network-stack.md)で、パケットが通る経路全体を確認します。

## 参考資料

- [Control Group v2: Linuxカーネルドキュメント](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [namespaces(7): Linuxマニュアル](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [KEP-127: user namespaceのサポート](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/README.md)
- [bottlerocket-os/bottlerocket#4221: conntrack上限が適用されない](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [kube-proxyのnftablesモード（Kubernetesブログ）](https://kubernetes.io/blog/2025/02/28/nftables-kube-proxy/)
- [KEP-5495: kube-proxyのIPVSモードを非推奨化](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [nftablesモードでのkube-proxy実行: EKSのベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [EKSノードでnf_conntrack_maxの上限を引き上げる](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [Amazon EKSに最適化されたAmazon Linux 2023 AMI](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
