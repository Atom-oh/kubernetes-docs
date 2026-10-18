# Part 8: eBPF データパスの内部構造

> **レビュー基準**: Cilium 1.20.2（安定版、2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。**[1.21 pre-release]** と記した項目は v1.21.0-pre.3 に基づいており、GA 前に変更される可能性があります。
> **最終更新**: 2026年10月15日

この章では Cilium のデータパスを詳しく見ていきます。どの BPF プログラムが実行され、どこにアタッチされ、相互にどう呼び出し、どのマップを読み、エージェントがどうコンパイルしてロードするのか、さらにパケット1個が各ホップでどう処理されるかを説明します。一般的な eBPF の入門（歴史、検証器、マップの種類）は[Part 2: eBPF](02-ebpf.md)を参照してください。オーバーレイとルーティングの動作は[Part 9](09-overlay-native-routing.md)、IPAM は[Part 10](10-ipam-deep-dive.md)で説明します。

> **古いブログ記事に注意: `cilium_tunnel_map` はもう存在しません。** 古い記事や一部の上流サンプル出力には、Pod CIDR とリモートノード IP を対応づける `cilium_tunnel_map` が掲載されています。Cilium 1.17 では BPF 内に存在し（`bpf/lib/encap.h`）、`cilium-dbg bpf tunnel list` で内容を表示できました。1.18 でデータパスから削除され（1.18.14 の BPF ツリーに参照はなく、エージェントが残存マップの pin を解除するだけです）、Go パッケージも 1.19 で削除されました。Cilium 1.20.2 では BPF プログラムから参照されません。リモートノード（トンネルエンドポイント）は `cilium_ipcache_v2` の**値**に格納されます（フィールド `tunnel_endpoint`、フラグ `flag_has_tunnel_ep`）。1.18 と 1.20 に `cilium-dbg bpf tunnel list` コマンドはありません。オーバーレイルーティングの調査に tunnel map を `bpftool map dump` するよう案内された場合は、代わりに ipcache を表示します（`cilium-dbg bpf ipcache list`）。上流の開発ドキュメントにはサンプル出力にまだこのマップが載っていますが、現在も使われているという意味ではありません。

## 学習目標

- 各 Cilium BPF オブジェクト、そのエントリプログラム、およびアタッチ先のデバイスや cgroup を説明する。
- Cilium が tail call を使う理由と、送信元のプログラムから宛先エンドポイントのポリシーが実行される仕組みを説明する。
- ポリシー、ipcache、conntrack、サービスマップのキーと値の構造を読み取り、適切なフラグでサイズを設定する。
- エージェント側の処理（ELF テンプレートキャッシュ、`.rodata.config` 定数、マップの pin、アタッチ、commit）を説明する。
- Pod -> ClusterIP -> Pod の接続を追跡し、各ホップで参照されるマップを列挙する。
- 稼働中のノードで `cilium-dbg bpf ...` と `bpftool` を使って調査する。

## 1. プログラム構成とアタッチ先

Cilium は `bpf/` 以下の少数の C ソースをコンパイルします。各ソースから1つの ELF オブジェクトが生成され、各オブジェクトには1つ以上の**エントリプログラム**（ELF セクション `tc/entry`、`xdp/entry`、`cgroup/...`）と、多数の**tail プログラム**（セクション `tc/tail`）が含まれます。`bpftool prog show` に表示されるプログラム名には `cil_` という接頭辞が付きます。

### 1.1 1.20.2 のエントリプログラム

| ELF オブジェクト（ソース） | エントリプログラム | アタッチ先 | 用途 |
|---|---|---|---|
| `bpf_lxc.o` | `cil_from_container` | ホスト側 `lxc*` veth の ingress（Pod から出る通信）；netkit では netkit peer のプライマリフック | エンドポイント単位の送信経路：identity、CT、送信ポリシー、サービス LB（パケット単位モード）、転送 |
| `bpf_lxc.o` | `cil_to_container` | ホスト側 `lxc*` の egress（スタック経由で Pod に届く通信） | スタック経由で届く通信の受信ポリシー（エンドポイントルート、L7 プロキシからの戻り）。エンドポイントが egress プログラムを必要とする場合のみアタッチ |
| `bpf_lxc.o` | `cil_lxc_policy`、`cil_lxc_policy_egress` | **デバイスにはアタッチしない**。グローバル prog array `cilium_call_policy` / `cilium_egresscall_policy` に格納 | 他のプログラムから呼び出される宛先受信・送信元送信ポリシー |
| `bpf_host.o` | `cil_from_netdev` | すべてのネイティブ／外部デバイスの ingress | ホスト宛て・転送トラフィック、NodePort、ipcache による identity、ホストファイアウォール |
| `bpf_host.o` | `cil_to_netdev` | ネイティブデバイスの egress（masquerade、NodePort、WireGuard、IPsec で必要な場合のみアタッチ） | BPF masquerade、NodePort SNAT、EDT／帯域幅制御、暗号化マーク |
| `bpf_host.o` | `cil_from_host` | `cilium_host` の egress | ホストスタックから Pod への通信 |
| `bpf_host.o` | `cil_to_host` | `cilium_host` と `cilium_net` の ingress | Pod からホストへの通信、ホストファイアウォール |
| `bpf_host.o` | `cil_host_policy` | prog array のスロット（ホストエンドポイントポリシー） | ホストファイアウォールポリシー |
| `bpf_overlay.o` | `cil_from_overlay`、`cil_to_overlay` | `cilium_vxlan` または `cilium_geneve` の ingress／egress | トンネル ID を送信元 identity として読み取る |
| `bpf_wireguard.o` | `cil_from_wireguard`、`cil_to_wireguard` | `cilium_wg0` の ingress（常時）／egress（必要な場合のみ） | 復号された通信にマークを付ける |
| `bpf_xdp.o` | `cil_xdp_entry` | ネイティブデバイスの XDP | CIDR 事前フィルター、NodePort／DSR の高速化 |
| `bpf_sock.o` | `cil_sock4_connect`、`cil_sock4_sendmsg`、`cil_sock4_recvmsg`、`cil_sock4_getpeername`、`cil_sock4_pre_bind`、`cil_sock4_post_bind`、IPv6 相当の各プログラム、`cil_sock_release` | cgroup ルートの **cgroup v2** sock_addr／sock フック | ソケットレベルのロードバランシング |
| `bpf_sock_term.o` | `cil_sock_{tcp,udp}_destroy_v{4,6}` | `bpf_sock_destroy` kfunc を呼び出す BPF iterator（`iter/tcp`、`iter/udp`） | 削除済みバックエンドに接続しているソケットを終了する。kfunc が使えない場合、エージェントは netlink `sock_diag` にフォールバック |
| `bpf_probes.o`、`bpf_alignchecker.o` | 該当なし | 起動時に `BPF_PROG_RUN` で1回実行 | カーネル機能の検査、C／Go 構造体レイアウトの照合 |

`bpf_network.c`（`cil_from_network`、ネイティブデバイス ingress での IPsec 復号）は1.18.14 と1.19.8に存在し、**1.20で削除**されました。

```
                       node A                                   node B
 pod C eth0 ----veth---- lxc_C           lxc_B ----veth---- pod B eth0
   |  cgroup/connect4          |             ^                     
   |  (bpf_sock.o)             | tcx ingress |  redirect_peer
   |                           v cil_from_container                 
   |                    +-------------------+   (tail calls, maps)
   |                    |   bpf_lxc.o       |-------+
   |                    +-------------------+       | encap / FIB redirect
   |                           |                     v
   |        cilium_host  <-----+          cilium_vxlan (cil_to_overlay)  ==underlay==>
   |        cil_from_host/cil_to_host        eth0 (cil_from_netdev / cil_to_netdev)
   |                                         eth0 XDP (cil_xdp_entry, optional)
```

### 1.2 tcx、従来の tc、netkit

デバイス単位のプログラムについて、ローダー（`pkg/datapath/loader/tc.go`）は次の優先順位で方式を選びます。

1. **tcx**（Helm `bpf.enableTCX: true`、デフォルト）：末尾アンカーに `link.AttachTCX` でアタッチする `bpf_link`。リンクは（エンドポイントの場合）`/sys/fs/bpf/cilium/endpoints/<id>/links/`、（デバイスの場合）`/sys/fs/bpf/cilium/devices/<dev>/links/` の下に pin されます。プログラム更新時はリンクがアトミックに更新されるため、再ロード中にプログラムが存在しない時間帯はありません。カーネル6.6以降が必要です。tcx のアタッチ成功後、古い tc フィルターを削除します。
2. **従来の tc**：カーネルが「未対応」を返すか `enableTCX: false` の場合、ローダーは `cls_bpf` を direct-action モードで使う `clsact` qdisc を設定し、古い tcx リンクをデタッチします。
3. **完全な失敗**：どちらも使えない場合のみです。エージェントは tc-bpf または tcx（Linux 6.6以降）が必要だと報告します。

**netkit**（成熟度：**beta**）：`bpf.datapathMode: veth | netkit | netkit-l2 | auto` で選択します。デフォルトは `veth` です。netkit では Pod 専用プログラムを netkit の **peer** デバイス内にアタッチします。他のデバイスは引き続き tcx を使い、netkit を選択すると tcx も自動的に有効になります。ソースで検査される前提条件（`canUseNetkit`）は、カーネル検査に合格すること（上流ドキュメントは6.8以降、ソースの検査エラーメッセージは6.7と記載）、BPF host routing、BPF masquerade、kube-proxy replacement が有効であること、そして **`bpf.tproxy` を使わないこと**（`bpf_sk_assign` が必要で、tc ingress でのみ有効）です。`auto` は1.20で追加され、検査後、警告を出して veth にフォールバックします。Pod が veth を使い始めた後に、その Pod を netkit または `auto` に切り替えることは拒否されます。代わりに新しいノードグループを段階的に展開してください。

| 方式 | カーネル | pin されるオブジェクト | 再ロード時の動作 | Cilium での成熟度 |
|---|---|---|---|---|
| 従来の tc（`clsact` + `cls_bpf`） | 5.10 が基準 | デバイス上のフィルター | フィルターを置換 | 安定、フォールバック |
| tcx | 6.6以降 | `/sys/fs/bpf/cilium/...` 以下の `bpf_link` | リンクをアトミックに更新 | 安定、利用可能ならデフォルト |
| netkit | 6.8以降（ドキュメント記載） | peer 上の netkit link | リンクをアトミックに更新 | beta |

### 1.3 XDP と cgroup フック

- **XDP**（`cil_xdp_entry`）は `loadBalancer.acceleration` が `native` または `best-effort` の場合にアタッチされます。CIDR 事前フィルター（`cilium_cidr_v4_fix`／`dyn` LPM map）と NodePort／DSR の高速経路を実行します。ドライバーが `EINVAL` を返す場合、ローダーはアタッチ種別と `XDP_HAS_FRAGS` フラグを組み合わせ、最大4通りを再試行します。
- **cgroup フック**は cgroup ルートに一度アタッチされます（エージェントフラグ `--cgroup-root`、デフォルト `/run/cilium/cgroupv2`）。`bpf_link` を使用し、`/sys/fs/bpf/cilium/socketlb/links/cgroup` に pin されます。`socketLB.hostNamespaceOnly=true` でない限り、すべての Pod netns で実行されます。

## 2. Tail call とポリシープログラムの構造

### 2.1 Tail call を使う理由

Tail call は戻り値を返さず、実行中のプログラムを別のプログラムに置き換えます。Cilium が tail call を使う理由は3つあります。1つのプログラムの複雑さに対する検証器の上限（100万命令）、512バイトのスタック制限、そして大きなオプション機能を通常の処理経路から分離できることです。連鎖できる tail call は最大33回です。bpf-to-bpf 呼び出しと tail call の併用にはカーネル5.10が必要で、これも5.10を基準とする理由の1つです。

Tail call をまたいで状態を受け渡す場所は2つあります。`skb->cb[]`（`CB_SRC_LABEL` などの `CB_*` スロット）と、conntrack タプルや CT tail プログラムが計算した結果などを格納する CPU ごとのスクラッチマップ `cilium_tail_call_buffer4/6` です。

### 2.2 エンドポイントごとの call array

各エンドポイントには `cilium_calls_<endpoint-id, 5 digits>`（例：`cilium_calls_00312`）という専用の `PROG_ARRAY` があります。ホストエンドポイントは `cilium_calls_hostns_<id>`、各ネイティブデバイスは `cilium_calls_netdev_<ifindex>` を使います。他のローダーは `cilium_calls_overlay_2`（予約済み identity 2 の `world` という名前を持つ overlay デバイス）、`cilium_calls_wireguard_<ifindex>`、`cilium_calls_xdp_<ifindex>` を使用します。いずれも `CILIUM_CALL_SIZE` 個のエントリと、「ロードごとに pin を置き換え、古い array は再利用しない」というフラグを使って宣言されます。

| バージョン | `CILIUM_CALL_SIZE` |
|---|---|
| 1.18.14 | 48 |
| 1.19.8 | 49 |
| 1.20.2 | 50 |
| 1.21.0-pre.3 | 50 |

スロットは**固定**です。呼び出し箇所はスロット番号を定数とするインラインアセンブリです。ローダーは各 `tc/tail` プログラムの BTF decl-tag（`tail:cilium_calls/<idx>`）を読み取り、array を設定します。定数適用後に到達不能となる tail プログラムは**除去されます**（セクション5）。1.20のスロットグループは次のとおりです。

| スロット | 意味 |
|---|---|
| 1-2、4-5 | drop／エラー通知、ICMPv6 neighbor solicitation、time-exceeded |
| 6 | ARP |
| 3 | 未使用（バックポート時の衝突を避けるために残された番号の空き） |
| 7、10 | IPv4／IPv6 from-LXC（netdev、overlay、WireGuard のエントリでも別名として使用） |
| 8-9 | IPv4 から IPv6、IPv6 から IPv4 への変換（`CILIUM_CALL_IPV46_RFC6052`、`CILIUM_CALL_IPV64_RFC6052`；NAT46／NAT64） |
| 11-14 | to-LXC ポリシーのみ、to-endpoint |
| 15-25、36-39 | NodePort NAT、rev-NAT、DSR、SNAT forward；from-host |
| 26-27 | from-LXC の続き（送信経路の後半。検証器の複雑さを分割） |
| 28-33 | CT ingress／CT ingress policy-only／CT egress、IPv4 と IPv6 |
| 34-35、40 | SRv6、クラスター間 rev-SNAT |
| 41-47 | host／netdev からの続き、「no service」ICMP unreachable、multicast 配信 |
| 48-49 | ポリシー拒否時の ICMP 応答（1.20で追加、`policy_deny_response` 有効時に使用） |

### 2.3 グローバルなポリシープログラム array

ポリシーはエンドポイント別 call array には格納されません。`cil_lxc_policy` と `cil_lxc_policy_egress` は、エンドポイント ID をインデックスとし `ENDPOINTS_MAP_SIZE` のサイズを持つ、2つの**グローバル** prog array に登録されます。

| Array | インデックス | 実行するポリシー |
|---|---|---|
| `cilium_call_policy` | 宛先エンドポイント ID | 宛先の**受信**ポリシー |
| `cilium_egresscall_policy` | 送信元エンドポイント ID | 送信元の**送信**ポリシー |

ローダーは tc／tcx プログラムをアタッチする**前**にスロットを書き込みます（`PolicyMap.Update(ep id, PolicyProg)`）。ローカル宛先への L3 書き換えを終えた送信元は `tail_call_policy(ep->lxc_id)` を呼びます。BPF host routing では `bpf_redirect_peer` によりパケットが宛先 Pod の netns に移され、**宛先の tc egress フックは通らない**ため、これは重要です。同一ノード内でも受信ポリシーを確実に適用する方法が、送信元から宛先のポリシープログラムを呼ぶことです。スロットが空（エンドポイント終了中）の場合、`DROP_EP_NOT_READY` でパケットを破棄します。

スタック経由の通信には引き続き `cil_to_container` があるため、宛先の受信ポリシーは送信元からの tail call、またはその egress フックから実行されます。

## 3. ポリシー適用経路

### 3.1 ポリシーマップ

各エンドポイントは `cilium_policy_v3_<id>`（1.20。1.18／1.19では `cilium_policy_v2_`）を持ちます。型は `LPM_TRIE`、フラグは `BPF_F_NO_PREALLOC | BPF_F_RDONLY_PROG_COND`、サイズは `--bpf-policy-map-max`（エンドポイントあたりデフォルト16384）です。

```
policy_key  { lpm prefixlen; u32 sec_label;   /* remote identity, 0 = wildcard */
              u8 egress:1;  u8 protocol;      /* 0 = any */
              be16 dport; }                   /* prefix match => port ranges */
policy_entry{ be16 proxy_port;                /* != 0 => redirect to L7 proxy */
              deny:1; lpm_prefix_length:5; auth_type:7; has_explicit_auth_type:1;
              u32 precedence; u32 cookie; }
```

LPM prefix は `sec_label` と `egress` を完全一致で扱い、`protocol` は指定するかしないかの二択、`dport` はビット prefix で扱います。そのため、ポート範囲を少数のエントリで表現できます。

### 3.2 検索アルゴリズム

リモート identity `R`、プロトコル `P`、ポート `D` のフローを考えます。

1. `sec_label = R` で個別検索します。最大優先度（deny）を持つエントリがヒットした場合、ここで終了します。
2. 集約検索を行います。identity の集約（CIDR グループなど）、次に `sec_label = 0`（L3 ワイルドカード）で調べます。
3. `precedence` が高いもの（deny、proxy redirect、allow の順）、次に LPM prefix が長いものを選択します。ヒットしなければ `DROP_POLICY` です。

マッチの種類はイベントに記録されます（L3+L4、L3 のみ、L4 のみ、protocol のみ、すべて）。ICMP ルールが有効な場合、ICMP type は `dport` に格納され、「fragmentation needed」は常に許可されます。

### 3.3 判定と副作用

- Deny の場合は `DROP_POLICY_DENY` と drop event が記録されます。`proxy_port != 0` の allow はプロキシにリダイレクトします（セクション3.5）。`auth_type != 0` の allow は、`cilium_auth_map` に有効なエントリがない場合 `DROP_POLICY_AUTH_REQUIRED` となります。
- **送信ポリシーは送信元エンドポイントで適用**されます（`handle_ipv4_from_lxc`）。対象は `CT_NEW` と `CT_ESTABLISHED` のみで、返信（`CT_REPLY`、`CT_RELATED`）ではポリシーをスキップします。**受信ポリシーは宛先で適用**され（ポリシープログラム内の `ipv4_policy()`）、allow の後に ingress CT エントリを作成します。
- deny と、新たに許可された接続で policy-verdict event が出力されます。hairpin 通信（Pod から自身のサービス IP への通信）はポリシーをスキップします。
- エントリ単位のカウンターを有効にすると `cilium_policystats` に記録されます（`--bpf-policy-stats-map-max` は65536）。

### 3.4 ポリシー変更では再コンパイルしない

ポリシー更新は `cilium_policy_v3_<id>` に対するマップ操作です（`applyPolicyMapChangesLocked`）。オブジェクトの再構築と再ロードが行われるのは、エンドポイントまたはノード構成のハッシュが変わった場合だけです。したがって `CiliumNetworkPolicy` の編集で clang が起動することはありません。

### 3.5 L7 と FQDN のリダイレクト

`proxy_port != 0` のとき、`ctx_redirect_to_proxy4()` はフローを Envoy または DNS proxy に送ります。実装は2種類あります。

| 方式 | 動作 | 成熟度 |
|---|---|---|
| iptables TPROXY（デフォルト） | データパスが `mark = MARK_MAGIC_TO_PROXY \| proxy_port << 16` を設定して OK を返す。`CILIUM_PRE_mangle` ルールの `xt_socket`／`TPROXY` が listener へ送る | 安定 |
| `bpf.tproxy: true` | tc ingress で `bpf_sk_assign` を使って listener socket を割り当てる | beta、デフォルト無効、**netkit と非互換**（エージェントは1.19.8、1.20、1.21.0-pre.3では起動を拒否。1.18.14のソースにはこの検査が見当たらない） |

プロキシポートは `--proxy-portrange-min/max`（10000-20000）から割り当てます。CT エントリに `proxy_redirect` を記録し、返信がプロキシに戻るようにします。L7 event は BPF からは出ず、Envoy と DNS proxy が access log の記録をエージェントに送ります。

相互認証（`auth_type`）は**1.20で非推奨**になりました（ztunnel を使用）。**[1.21 pre-release]** では `--bpf-auth-map-max` と `cilium_auth_map` が削除され、エントリの auth bit は予約済みになります。

## 4. マップ一覧

グローバルマップは `/sys/fs/bpf/tc/globals/` 以下に名前で pin されます。リンクとプラグインオブジェクトは `/sys/fs/bpf/cilium/` 以下です。Helm 設定は `bpf.root`（デフォルト `/sys/fs/bpf`）と `bpf.autoMount.enabled` です。

### 4.1 コアマップ

| Map | 型 | Key -> Value（主要項目） | 備考 |
|---|---|---|---|
| `cilium_lxc` | HASH | endpoint IP（+family、cluster_id） -> `{ifindex, lxc_id, flags, mac, node_mac, sec_id, parent_ifindex}` | ローカルエンドポイントとホスト IP。65535エントリ（`lxcmap.MaxEntries`） |
| `cilium_ipcache_v2` | LPM_TRIE | `{cluster_id, family, ip/prefix}` -> `{sec_identity, tunnel_endpoint, key, flag_skip_tunnel, flag_has_tunnel_ep, flag_ipv6_tunnel_ep, flag_remote_cluster}` | **identity と tunnel endpoint**。512000エントリ（`ipcachemap.MaxEntries`） |
| `cilium_policy_v3_<id>` | LPM_TRIE | 3.1 を参照 | エンドポイントごと |
| `cilium_calls_<id>`、`_hostns_`、`_netdev_` | PROG_ARRAY | slot -> program | プライベート。ロードごとに置換 |
| `cilium_call_policy`、`cilium_egresscall_policy` | PROG_ARRAY | endpoint ID -> policy program | グローバル |
| `cilium_ct4_global`、`cilium_ct6_global` | LRU_HASH | 5-tuple + direction flags -> `ct_entry` | TCP |
| `cilium_ct_any4_global`、`cilium_ct_any6_global` | LRU_HASH | 同上 | TCP 以外 |
| `cilium_snat_v4_external`（+`v6`） | LRU_HASH | CT tuple -> NAT entry（`to_saddr/to_sport` または `to_daddr/to_dport`） | masquerade、NodePort SNAT |
| `cilium_nodeport_neigh4/6` | LRU_HASH | next-hop IP -> MAC | |
| `cilium_node_map_v2` | HASH | `{family, ip}` -> `{node id, spi}` | IPsec／WireGuard／ClusterMesh の node ID（v1 は1.19で削除） |
| `cilium_devices`（1.20で追加） | HASH | ifindex -> `{mac, l3}` | エージェントが同期 |
| `cilium_runtime_config` | ARRAY | index -> u64（時刻オフセット、agent liveness） | `cilium-dbg bpf config list` |
| `cilium_metrics` | PERCPU_HASH | `{reason, direction, line, file}` -> `{count, bytes}` | forward／drop counter の元データ |
| `cilium_events` | PERF_EVENT_ARRAY | CPU -> perf fd | monitor と Hubble のデータソース（セクション8） |
| `cilium_signals` | PERF_EVENT_ARRAY | datapath -> agent signal | 例：CT が上限に達したときに GC を起動 |

Conntrack のアドレスは、パケットに対して送信元と宛先を入れ替えた形で格納されます。`ct_entry` は有効期間、`rx/tx_closing`、`rev_nat_index`、`proxy_redirect`、`from_l7lb`、`from_tunnel`、`src_sec_id` と、確認済み TCP flag を保持します。1つのマップに送信、受信、サービススコープのエントリが入り、`tuple.flags` で区別します。Cluster Mesh は、IP が重複する場合にクラスターごとの内部マップ（`cilium_per_cluster_ct_*`）を追加します。

タイムアウト（エージェントフラグ、1.20.2）：TCP established は2時間13分20秒、SYN は1分、FIN は10秒、TCP 以外は1分、サービス TCP は2時間13分20秒、サービス猶予期間は1分です。

### 4.2 ロードバランシングマップ

| Map | 型 | Key -> Value | 備考 |
|---|---|---|---|
| `cilium_lb4_services_v2`（+`6`） | HASH | `{address, dport, backend_slot, proto, scope}` -> `{backend_id or affinity/algorithm, count, rev_nat_index, flags, qcount}` | slot 0 は frontend、slot 1..count は backend ID。`scope` で external と internal（externalTrafficPolicy）を区別 |
| `cilium_lb4_backends_v3`（+`6`） | HASH | `backend_id` -> `{address, port, proto, flags, cluster_id, zone}` | |
| `cilium_lb4_reverse_nat`（+`6`） | HASH | `rev_nat_index` -> `{address, port}` | パケット単位の LB 返信アドレス復元 |
| `cilium_lb4_reverse_sk`（+`6`） | LRU_HASH | `{socket cookie, backend addr, port}` -> `{original service addr, port, rev_nat_index}` | socket-LB の逆変換 |
| `cilium_lb4_affinity`、`cilium_lb_affinity_match` | LRU_HASH / HASH | client（IP または netns cookie）+ rev_nat -> backend | `sessionAffinity` |
| `cilium_lb4_source_range` | LPM_TRIE | `{rev_nat_id, cidr}` -> flag | `loadBalancerSourceRanges` |
| `cilium_lb4_maglev` | HASH_OF_MAPS | `rev_nat_id` -> lookup-table array | `--bpf-lb-algorithm maglev`、テーブルサイズは `--bpf-lb-maglev-table-size` |
| `cilium_lb4_health` | LRU_HASH | socket cookie -> peer backend | LB health datapath。カーネル5.12 |

サービスの `affinity_timeout` フィールドの上位8 bit は選択アルゴリズム（random または maglev）を格納します。

### 4.3 機能別マップ（一行ずつ）

`cilium_ipmasq_v4/v6`（masquerade しない CIDR）、`cilium_ipv4_frag_datagrams`（デフォルト8192）、`cilium_vtep_map`、`cilium_srv6_*`、`cilium_egress_gw_policy_v4_v2`（1.20で `_v4` から改名）、`cilium_l2_responder_v4/v6`、`cilium_mcast_*`、`cilium_cidr_v4_fix/dyn`（XDP 事前フィルター）、`cilium_encrypt_state`、`cilium_auth_map`、`cilium_policystats`、`cilium_ratelimit`、`cilium_throttle`、`cilium_lb_act`／`cilium_lb_fct`（アクティブ接続追跡、デフォルト無効）、および CPU ごとのスクラッチマップ（`cilium_tail_call_buffer4/6`、`cilium_nodeport_nat_buffer`、`cilium_xdp_scratch`、`cilium_percpu_trace_id`）。

### 4.4 サイズ設定フラグ

| Flag（Helm） | デフォルト（1.20.2） | 対象 |
|---|---|---|
| `--bpf-map-dynamic-size-ratio`（`bpf.mapDynamicSizeRatio`） | 0.0025（RAM の0.25%）；**デフォルトで動的サイズ設定が有効** | CT TCP／any、NAT、socket reverse-NAT。NodePort neighbor map は NAT のサイズに連動（フラグの説明には「CT、NAT、policy BPF map」とあるが、サイズ設定コードは policy map を変更しない） |
| `--bpf-ct-global-tcp-max`（`bpf.ctTcpMax`） | 524288 | TCP CT |
| `--bpf-ct-global-any-max`（`bpf.ctAnyMax`） | 262144 | TCP 以外の CT |
| `--bpf-nat-global-max`（`bpf.natMax`） | 524288 | NAT。警告を出し、CT 合計の2/3を上限とする |
| `--bpf-neigh-global-max`（`bpf.neighMax`） | 524288 | NodePort neighbor |
| `--bpf-policy-map-max`（`bpf.policyMapMax`） | エンドポイントごとに16384（最大65536） | policy |
| `--bpf-fragments-map-max` | 8192 | fragments |
| `--bpf-node-map-max` | 16384 | node map |
| `--bpf-lb-map-max`（`bpf.lbMapMax`） | 65536 | LB map ごとの6つのフラグ（`--bpf-lb-service-map-max`、`-service-backend-map-max`、`-rev-nat-map-max`、`-affinity-map-max`、`-source-range-map-max`、`-maglev-map-max`）のフォールバック。個々のデフォルトは0で、`lb-map-max` を使用。ソース（`pkg/loadbalancer/config.go`）には存在するが、生成された cmdref にはなく、cmdref には `--bpf-lb-map-max` のみ記載 |
| `--bpf-sock-rev-map-max` | 動的。デフォルトは CT-any のサイズ | socket reverse map |
| `bpf.distributedLRU.enabled` | false | CPU ごとの LRU free list。大きな map と併用 |
| `bpf.preallocateMaps` | false | メモリを使って挿入レイテンシーを低減 |

動的サイズ設定では `entries = default_entries * (ratio * RAM) / total_default_bytes` を計算し、各 map の下限（CT TCP 128Ki、CT any 64Ki、NAT 128Ki、socket reverse 64Ki）と上限16Mi（2^24）の範囲に収めます。**フラグを明示的に設定すると、その map の動的サイズ設定だけが無効になります。** 適用時、エージェントは `option <name> set by dynamic sizing to <N>` をログに出します。上流の調整済み performance profile では ratio 0.08 を使用します。

> map のサイズ変更では map が作り直され、再投入されるまでエントリが失われます。稼働中のノードで LB map または CT map のサイズを変えると、確立済み接続が中断されます。サイズ変更はノードを順番に入れ替える作業として計画してください。

`cilium_bpf_map_pressure{map_name}`（`--bpf-policy-map-pressure-metrics-threshold`、デフォルト0.1を超えると出力）、`cilium_bpf_map_capacity`、`cilium_bpf_map_ops_total` で監視します。

## 5. エージェントからカーネルへ：コンパイル、ロード、アタッチ

### 5.1 フロー

```
agent start
  |  write node headers  (StateDir/globals: node_config.h, netdev_config.h, ...)
  |  hash node config -> if changed, wipe template cache (StateDir/templates)
  v
template config hash (compile-time #defines only)
  |  cache hit?  -> reuse StateDir/templates/<sha>/bpf_lxc.o
  |  miss        -> clang -O2 --target=bpf -mcpu=v3|v2|v1 ... -> new ELF template
  v
LoadCollection (per endpoint / device)
  |  copy spec -> patch maps -> rename maps (cilium_calls -> cilium_calls_<id>, cilium_policy -> cilium_policy_v3_<id>)
  |  write .rodata.config (endpoint ID, IPs, MAC, ifindex, feature switches)
  |  dead-code analysis -> remove unused tail calls and maps
  |  fill tail-call arrays from BTF decl tags
  |  load into kernel (verifier); reuse pinned global maps, replace incompatible ones
  v
attach: policy progs into cilium_call_policy/egresscall_policy
        -> tcx/tc/netkit entry programs -> commit() map pins -> endpoint routes
```

### 5.2 ELF テンプレートと `.rodata.config`

高コストなコンパイルは引き続きエージェントで実行します（コンテナイメージには clang／LLVM が含まれます。エージェントをネイティブ実行する場合は LLVM 18.1 以降が必要です）。Pod ごとに再コンパイルしないよう、Cilium は**テンプレート構成**だけをハッシュ化します。これはコードの形を変える `#define ENABLE_*` フラグです。同じフラグを持つエンドポイントはすべて `StateDir/templates/<sha>/` 以下の同じオブジェクトを共有します。`cilium-dbg bpf sha list` で一覧を表示できます。

エンドポイントごとの値はコンパイル時に埋め込みません。`DECLARE_CONFIG(type, name, desc)` で宣言した `.rodata.config` セクション内の global とし、`CONFIG(name)` で読み取ります。エージェントはロード前に spec のコピーへ値を書き込みます。カーネルが読み取り専用データを固定するため、検証器はその値を定数として扱い、**到達しない分岐を除去**できます。この機能には dead-code elimination（カーネル5.1以降）が必要です。Go 側の構造体は BTF decl-tag から `dpgen` で生成されます（`pkg/datapath/config/*_config.go`）。有効な定数はエンドポイント／デバイスごとに JSON（例：`bpf_lxc.json`）として state directory に出力され、`cilium sysdump` に含まれます。

各リリースで `#define` スイッチの `.rodata.config` への移行が進み、テンプレートの種類と再コンパイル回数が減っています。BPF ツリー内の `DECLARE_CONFIG`／`NODE_CONFIG` 宣言を grep で数えると、1.18.14 では18、1.19.8 では43、1.20.2 では73、**[1.21 pre-release]**（v1.21.0-pre.3）では104です。各タグのチェックアウトで `grep -rE '^\s*(DECLARE_CONFIG|NODE_CONFIG)\(' bpf --include=*.h --include=*.c | wc -l` を実行した結果です。API の数ではなく、おおまかな傾向として捉えてください。

### 5.3 再生成

エンドポイントを再生成するたび、エージェントは endpoint header hash を計算します。前回と一致する場合はマップだけを同期します（ポリシー変更にあたる `RegenerateWithoutDatapath`）。一致しない場合はヘッダーを書き込み、データパスを再ロードします。関連メトリクス：`cilium_endpoint_regenerations_total`、`endpoint_regeneration_time_stats_seconds`（`bpfCompilation`、`bpfLoadProg`、`bpfWaitForELF` などの段階）、`cilium_endpoint_component_status`（1.20で追加）。

順序が重要です。すべてのエントリプログラムがアタッチされてから map pin に対して `commit()` してください。そうしないと新しいプログラムが古い array に tail call し、呼び出しに失敗する可能性があります。

### 5.4 検証器テスト

Cilium はカーネル5.10、6.1、net-next に対して、最大機能を有効にしたビルドをコンパイルテストします（`bpf/complexity-tests/`）。ロード時の検証器エラーは、検証器の出力全体とともにログに記録されます。

## 6. カーネルと機能の対応表

### 6.1 起動時に必須の条件（1.20.2）

次の機能がなければ、エージェントは起動しません。`bpf()` と JIT、tc-bpf または tcx、`bpf_skb_change_tail`、`bpf_get_socket_cookie`、`bpf_get_current_cgroup_id`、`bpf_fib_lookup`、dead-code elimination、書き込み可能な `skb->queue_mapping`、100万命令のプログラム、`BPF_ADJ_ROOM_MAC` を使う `bpf_skb_adjust_room`、`bpf_jiffies64`、`BPF_MAP_LOOKUP_BATCH`、`bpf_get_netns_cookie`、`bpf_sk_assign`、`bpf_get_cgroup_classid`、cgroup sock_addr の `bpf_perf_event_output`、`bpf_csum_level`、`bpf_skb_change_head`、`bpf_redirect_neigh`、`bpf_redirect_peer` です。そのためドキュメント上の最小要件は**カーネル5.10**です（RHEL 8.10 の4.18は Red Hat によるバックポートを理由とする明示的な例外）。以前の helper 単位のヘッダー検査は現在空です。5.10を基準にすべての helper が使えることを前提にしています。

上流に記載されているカーネル設定には、`BPF`、`BPF_SYSCALL`、`BPF_JIT`、`NET_CLS_BPF`、`NET_CLS_ACT`、`NET_SCH_INGRESS`、`CGROUPS`、`CGROUP_BPF`、`DEBUG_INFO_BTF` と、`VXLAN`、`GENEVE`、（bandwidth manager 用の）`NET_SCH_FQ`、`NETKIT` などの追加機能があります。

### 6.2 オプションの高速化機能

| 機能 | 最小カーネル | 成熟度／備考 |
|---|---|---|
| tcx link | 6.6 | 利用可能ならデフォルト。利用できない場合は従来の tc |
| netkit（`bpf.datapathMode`） | 6.8（ドキュメント記載。ソースの probe 表記は6.7） | beta |
| IPv6 BIG TCP | 5.19 | 対応 NIC ドライバーが必要 |
| IPv4 BIG TCP | 6.3 | |
| Bandwidth Manager の BBR | 5.18 | |
| LB health-check datapath | 5.12 | |
| Multicast | AMD64 では5.10、AArch64 では6.0 | |
| `bpf_sock_destroy` kfunc | ソースに記載なし | netlink `sock_diag` に自動フォールバック |

データパスは CO-RE relocation helper を使いません（1.20.2 の `bpf/` ツリーで `preserve_access_index` を検索すると、UAPI ヘッダーのコメントだけが見つかります）。独自のヘッダーと UAPI の `__sk_buff` に対してビルドします。BTF は map 定義、`.rodata.config` データセクション、decl-tag に使われるため、`CONFIG_DEBUG_INFO_BTF=y` が必要です。

EKS では tcx または netkit に依存する設定を有効にする前に、`uname -r` と `cilium-dbg status` で実際のノードカーネルを確認してください。この章では各 AMI のカーネルバージョンを前提としていません。

## 7. 処理例：Pod -> Service -> Pod

以下は説明用の構成例です（数値は例、構造はソースに基づきます）。クライアント Pod `C` は10.0.1.10、identity は4711、endpoint ID は312で、ノード A 上にあります。Service `web` は ClusterIP 10.100.0.20:80/TCP、`rev_nat_index` は42、バックエンドは2つです。B1 は10.0.1.55（ノード A、endpoint 87）、B2 は10.0.2.77（ノード B）で、どちらも identity は9001です。設定は IPv4、veth、tcx、BPF host routing、`kubeProxyReplacement: true`（socket-LB が自動で有効）、`socketLB.hostNamespaceOnly=false` です。

### Hop 0: Pod 内の `connect()`、`cgroup/connect4`（`cil_sock4_connect`）

1. `{10.100.0.20, 80, TCP, slot 0, scope 0}` で `cilium_lb4_services_v2` を検索します。エントリがなければ sockaddr は変更されません。エントリがある場合は `count=2` です。
2. slot を選びます。TCP は random、UDP は socket cookie を使います。その slot のサービスキーから `backend_id` を取得し、続けて `cilium_lb4_backends_v3[backend_id]` から 10.0.2.77:80 を取得します。`sessionAffinity` が設定されていれば、先に `cilium_lb4_affinity` を参照します。
3. `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}] = {10.100.0.20, 80, 42}` を書き込みます。
4. syscall 内の `user_ip4/user_port` を書き換えます。**wire 上で DNAT は行われません。** Pod 内で `tcpdump` を実行すると backend IP が見えるため、驚くことがあります。socket-LB tracing が有効なら `trace_sock_notify` event が出力されます。

### Hop 1: Pod から SYN を送信、ホスト側 veth の `cil_from_container`（tcx ingress）

| 手順 | 処理 | アクセスするマップ |
|---|---|---|
| 1 | metadata をクリアし、`send_trace_notify(TRACE_FROM_LXC)`（集約設定に従う） | `cilium_events` |
| 2 | slot 7（IPv4 from-LXC）に tail call | `cilium_calls_00312` |
| 3 | per-packet LB をスキップ（socket-LB が変換済み） | なし |
| 4 | slot 30（CT egress）に tail call：`CT_NEW` を検索し、tuple を CPU ごとの buffer に保存 | `cilium_ct4_global`、`cilium_tail_call_buffer4` |
| 5 | slot 26（`handle_ipv4_from_lxc`）に tail call | `cilium_calls_00312` |
| 6 | 宛先 identity を解決：10.0.2.77 を LPM lookup し、identity 9001 と（overlay の場合）ノード B の tunnel endpoint を取得。見つからない場合は `world` | `cilium_ipcache_v2` |
| 7 | 送信ポリシー：`{egress=1, sec_label=9001, TCP, 80}` を2段階で検索し、許可または破棄。新しい通信を許可すると policy-verdict event を出力 | `cilium_policy_v3_00312`、drop 時は `cilium_events`、`cilium_metrics` |
| 8 | `proxy_port != 0` の場合、proxy 用の mark と CT の `proxy_redirect` flag を設定し、stack に渡す（セクション3.5） | |
| 9 | `ct_create4(CT_EGRESS)`：エントリを追加。SYN の有効期間は1分、ACK 後は2時間13分20秒 | `cilium_ct4_global`（関連 ICMP では CT-any も使用） |
| 10 | 以下のいずれかの転送経路を選ぶ | |

手順10で選ばれる転送経路：

- **宛先が同一ノード上（B1）**：`cilium_lxc[dst]` から `{ifindex, lxc_id=87, mac, node_mac}` を取得し、L2 header を書き換えます。metadata（`CB_SRC_LABEL=4711`、配信 flag）を設定した後、`cilium_call_policy` の B1 の `cil_lxc_policy` を使う `tail_call_policy(87)` を実行します（Hop 3）。
- **リモート、overlay**：ipcache の値に `flag_has_tunnel_ep` が設定されているため、`bpf_skb_set_tunnel_key` が `tunnel_id` に送信元 identity 4711、`remote_ipv4` にノード B を設定します。パケットは `cilium_vxlan`／`cilium_geneve` に redirect され、カーネルが encapsulation する前に `cil_to_overlay` が実行されます。Pod 間通信は masquerade されません。
- **リモート、BPF host routing を使う native routing**：`bpf_fib_lookup` の後、NIC に redirect します。`bpf.hostLegacyRouting=true` の場合は代わりに OK を返し、カーネルスタックと netfilter に処理させます。VNI はありません。受信側は IPsec／WireGuard を使う場合を除き、送信元 IP から ipcache を検索して送信元 identity を再取得します（または mark から取得）。

### Hop 2（リモートのみ）：ノード B が受信

- Overlay：`cil_from_netdev` は UDP 8472（VXLAN）／6081（Geneve）を stack に渡します。カーネルが `cilium_vxlan` 上で decapsulate し、`cil_from_overlay` が `bpf_skb_get_tunnel_key` から `tunnel_id` を読み取り、**送信元 identity** に対応づけます（host identity は `DROP_INVALID_IDENTITY` で拒否）。`CB_SRC_LABEL` を設定し、`TRACE_FROM_OVERLAY` を出力した後、`cilium_lxc[10.0.2.77]` を検索して `tail_call_policy(ep)` を呼びます。
- Native routing：`cil_from_netdev` が同じ処理を行い、送信元 IP に対応する `cilium_ipcache_v2` から送信元 identity を取得します。

### Hop 3: 宛先での受信ポリシー適用と配信

1. `cil_lxc_policy` が CT ingress tail call を実行し、`cilium_ct4_global` から `CT_NEW` を検索します。
2. ingress policy：`{egress=0, sec_label=4711, TCP, 80}` を使って `cilium_policy_v3_00087` を検索します。判定 event を出力します。
3. `ct_create4(CT_INGRESS)` は `src_sec_id=4711`、`from_tunnel`、`proxy_redirect` を記録します。
4. 配信：veth では `bpf_redirect_peer`、netkit では `redirect` で Pod の netns に転送し、`TRACE_TO_LXC` event を出力します。backend の stack は送信元を10.0.2.77として応答し、ClusterIP は認識しません。

### Hop 4: 返信と接続終了

- B の `cil_from_container` は ingress CT エントリを `CT_REPLY` として検出するため、**ポリシーをスキップ**します。パケットを VNI 9001 で encapsulate（または native routing）します。ノード A では `tail_call_policy(312)` が C の policy program を実行します。`CT_REPLY` なのでここでもポリシーをスキップし、`redirect_peer` で C に届けます。
- socket-LB の逆変換：アプリケーションは 10.100.0.20 と通信していると認識します。`getpeername` と `recvmsg` の hook は `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}]` を検索し、サービスアドレスを返します。
- socket-LB を使わない場合（host-namespace-only モード、L7 LB、SCTP）、Hop 1 の `bpf_lxc` で DNAT を行い、CT エントリに `rev_nat_index` を保存します。返信時には `cilium_lb4_reverse_nat[rev_nat_index]` で送信元を復元します。
- FIN／RST で `tx/rx_closing` を設定し、有効期間を FIN timeout（10秒）に短縮します。エージェントの CT GC が期限切れのエントリを削除します。`cilium_lb4_reverse_sk` エントリは LRU eviction または `cil_sock_release` まで残ります。

### ホップごとの参照一覧

| Hop | Program | 検索／書き込み |
|---|---|---|
| 0 | `cil_sock4_connect` | `lb4_services_v2` x2、`lb4_backends_v3`、`lb4_affinity`（任意）、`lb4_reverse_sk` への書き込み |
| 1 | `cil_from_container` + tail call 群 | `calls_<id>` x3、`tail_call_buffer4`、`ct4_global`（検索、作成）、`ipcache_v2`、`policy_v3_<src>`（送信）、`cilium_lxc`、`call_policy`、`events`、`metrics` |
| 2 | `cil_from_overlay`／`cil_from_netdev` | tunnel key または `ipcache_v2`、`cilium_lxc`、`call_policy` |
| 3 | `cil_lxc_policy`（宛先） | `ct4_global`、`policy_v3_<dst>`（受信）、`ct4_global` への作成、`events` |
| 4 | 返信経路、`recvmsg` | `ct4_global`（返信）、`lb4_reverse_sk` または `lb4_reverse_nat` |

### この trace に影響する1.20の動作変更

kube-proxy replacement を使い、`socketLB.enabled=false` または `socketLB.hostNamespaceOnly=true` にすると、クラスター内の Pod から NodePort への接続は、クライアント Pod の tc hook でロードバランスされます。クライアントの送信ポリシーと backend の受信 NetworkPolicy の両方で、この通信を許可する必要があります。

## 8. Hubble event の経路

```
BPF program --ctx_event_output--> cilium_events (PERF_EVENT_ARRAY, per CPU)
      |   trace_notify / drop_notify / policy_verdict_notify / debug / capture / trace_sock_notify
      v
agent monitor (pkg/monitor/agent): perf reader, 64 pages per CPU, opened only if a consumer exists
      |-- lost samples (kernel buffer overrun) -> MonitorStatus.Lost
      |-- unix-socket listeners (cilium-dbg monitor), queue --monitor-queue-size
      v
Hubble consumer -> observer queue (--hubble-event-queue-size)
      |   full => LostEvent source=OBSERVER_EVENTS_QUEUE, hubble_lost_events_total
      v
Hubble parser (identity/endpoint/service enrichment) -> ring buffer (--hubble-event-buffer-capacity)
      v
gRPC: hubble observe / Relay / UI
```

覚えておくべき点：

- 1.20 と1.21-pre.3 の event map は **perf event array** であり、BPF ring buffer ではありません。
- データパス内での event 量の制御には `bpf.monitorAggregation`（Helm のデフォルト `medium`、agent flag のデフォルト `None`）を使います。`medium` 以上ではノード内の受信 trace を抑制します。また確立済みフローは `bpf.monitorInterval`（5秒）の経過時、または `bpf.monitorFlags` の flag が検出されたときだけ報告します。クラス別設定は `bpf.events.drop.enabled`、`bpf.events.policyVerdict.enabled`、`bpf.events.trace.enabled`（すべてデフォルト true）です。実験的な rate limit `bpf.events.default.rateLimit`／`burstLimit` は、両方を設定するか、両方を0にします。
- `hubble observe` の flow はメモリ内 ring（`hubble.eventBufferCapacity`、2^n - 1 である必要があり、デフォルト4095、最大65535）に保存されます。best-effort のため、perf-buffer overrun と observer queue overflow のどちらでも event が失われます。カウンターは異なる `source` label（`perf_event_ring_buffer`、`observer_events_queue`）で記録されます。
- L7 event は BPF から発生するのではなく、proxy から agent event として届きます。

## 9. 調査ツール

### 9.1 cilium-dbg

```bash
CILIUM_POD=$(kubectl -n kube-system get pod -l k8s-app=cilium -o jsonpath='{.items[0].metadata.name}')
kc() { kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- "$@"; }

kc cilium-dbg status --verbose         # KPR, datapath mode (configured vs operational), BPF map pressure
kc cilium-dbg bpf fs show              # bpffs mount
kc cilium-dbg map list -v              # pinned maps and sizes
kc cilium-dbg bpf endpoint list        # cilium_lxc
kc cilium-dbg bpf ipcache list         # identity + tunnel endpoint per IP/CIDR
kc cilium-dbg bpf ct list global       # conntrack
kc cilium-dbg bpf nat list             # SNAT maps
kc cilium-dbg bpf lb list --frontends  # also --backends, --revnat, --source-ranges
kc cilium-dbg bpf lb maglev list       # only with Maglev
kc cilium-dbg bpf policy get --all -n  # every cilium_policy_v3_*, numeric identities
kc cilium-dbg bpf metrics list         # cilium_metrics
kc cilium-dbg bpf config list          # cilium_runtime_config
kc cilium-dbg bpf sha list             # compiled ELF templates
kc cilium-dbg monitor -t drop -t policy-verdict --related-to <ENDPOINT_ID>
```

`cilium-dbg map get <name>` はエージェントがキャッシュした状態を表示し、必ずしもカーネル上の状態とは一致しません。`cilium-dbg map events <name>` は更新ログを表示します。`bpf tunnel` と `bpf calls` サブコマンドはありません。

### 9.2 bpftool（ノード上で実行）

```bash
sudo bpftool net show                                     # tcx/tc/xdp/netkit attachments per device
sudo bpftool prog show | grep -E 'cil_|tail_'             # entry and tail programs
sudo bpftool map show pinned /sys/fs/bpf/tc/globals/cilium_ct4_global
sudo bpftool cgroup tree /run/cilium/cgroupv2             # socket-LB hooks
sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links
```

pin されたマップは読み取り専用として扱ってください。Cilium のマップに raw byte を書き込まないでください。エージェントのキャッシュ状態と食い違います。エージェントイメージに `bpftool` が含まれるとは限りません（このレビューでは確認していません）。存在しない場合はノード上、または debug Pod から実行します。

**[1.21 pre-release]** `--enable-bpf-stats`（Helm `bpf.stats.enabled`、デフォルト false）を有効にすると、カーネルの実行時統計と hive command `bpf/stats/report` が追加され、`cilium-dbg bpf stats report` から利用できます（`--sort avg|total|runs`、`--pod`、`--device`、`--json`）。プログラムごとの実行回数と平均実行時間を表示します。

## 10. データパスプラグイン（beta、1.20で追加）

Datapath Plugin を使うと、外部コンポーネントがデータパスを fork せずに Cilium のエントリポイントの前後で独自の BPF プログラムを実行できます。

- Helm `datapathPlugins.enabled=true`（デフォルト false）、または agent の `--enable-datapath-plugins` で有効にします。state directory は `datapathPlugins.stateDir`（デフォルト `/var/run/cilium/plugins`）です。
- `CiliumDatapathPlugin` CRD（`cilium.io/v2alpha1`）でプラグインを登録します。`spec.attachmentPolicy: Always | BestEffort` と `spec.version` を指定します。
- エージェントは `<stateDir>/<name>/plugin.sock` 上の gRPC を使い、各 plugin と `PrepareCollection` および `InstrumentCollection` を呼び出します。Cilium は dispatcher を生成し、tc、XDP、cgroup sock hook の Cilium エントリプログラムの前または後に、plugin の `BPF_PROG_TYPE_EXT`（freplace）プログラムを実行します。
- plugin Pod には `SYS_ADMIN` が必要です。plugin CR の作成、更新、削除のたびに、データパス全体が再初期化されます。バージョンをまたいだ互換性の保証はありません。1.18 と1.19にはありません。

現時点では実験やベンダー統合に使い、本番変更の一般的な拡張ポイントとして使うのは避けてください。

## 11. 演習

すべての演習の前提条件：Cilium 1.20.2、kube-proxy replacement を実行する使い捨て Linux クラスター、ノードのシェルアクセス（SSM など）、`kubectl`。この演習でクラスター外に公開されるものはありません。

### Lab 1: ノード上の Cilium プログラムをすべて確認する

1. ノード上で `sudo bpftool net show` と `sudo bpftool prog show | grep cil_` を実行します。
2. pin されたリンクを `sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links` で一覧表示します。
3. `kc cilium-dbg bpf sha list` を実行します。

期待される結果：各 native device に `cil_from_netdev`、各 `lxc*` device に `cil_from_container`、`cilium_host` に `cil_to_host`／`cil_from_host`、overlay の場合は `cilium_vxlan` または `cilium_geneve` に `cil_from_overlay`／`cil_to_overlay` が表示されます。カーネル6.6以降ではエンドポイント単位の link pin が存在します。それより古いカーネルでは、代わりに `tc filter show dev <lxc> ingress` で従来の filter を一覧表示できます。後片付け：不要（読み取り専用）。

### Lab 2: ポリシー変更では再コンパイルされないことを確認する

1. `kc cilium-dbg bpf sha list` と、エンドポイントの map を表示する `kc cilium-dbg bpf policy get <ENDPOINT_ID>` の結果を記録します。
2. client label を持つクライアントからテスト用 backend の TCP/80 への通信を許可する `CiliumNetworkPolicy` を適用します。
3. 2つのコマンドを再実行します。

期待される結果：client の数値 identity を持つ新しい ingress entry が backend endpoint の policy map に現れます。テンプレート一覧は変わりません。明示的な deny rule を追加し、deny flag を持つ entry を確認します。後片付け：policy object を削除します。クラスター全体の default-deny と干渉するため、他のポリシーがない namespace で事前に試してください。

### Lab 3: マップを使って1つの接続を追跡する

1. テスト用 namespace に2つの replica を持つ Deployment と ClusterIP Service、および client Pod を作成します。
2. client から ClusterIP に `curl` します。別の terminal で、client のノード上にて `cilium-dbg monitor -t trace -t policy-verdict --related-to <CLIENT_ENDPOINT_ID>` を実行します。
3. `bpf lb list --frontends`、`--backends`、`bpf ct list global | grep <backend ip>` を実行します。
4. client の netns 内で取得した `tcpdump -ni eth0 port 80` の結果と Service IP を比較します。

期待される結果：service frontend に backend が表示され、選択された backend の CT entry が存在します。socket-LB が有効なら、capture には ClusterIP ではなく backend IP が表示されます。任意：`socketLB.hostNamespaceOnly=true` では capture に ClusterIP が表示されます（パケット単位の LB）。この設定はクラスター全体のロードバランシング方法を変えるため、テストクラスターでのみ適用し、以前の Helm 値に戻してください。

### Lab 4: Hubble の event loss を集計する

1. テストクラスターで `hubble.eventQueueSize` を意図的に小さい値に設定します（ロールバック時は以前の値に戻します。agent が再起動します）。
2. テスト用 namespace で traffic tool を使って負荷を発生させます。
3. `source` 別に agent の `hubble_lost_events_total` metric を取得します。

期待される結果：queue overflow 時に `observer_events_queue` が増加し、agent log に「hubble events queue is full」と記録されます。perf-buffer overrun の場合は、代わりに `perf_event_ring_buffer` に現れます。

### Lab 5（応用）: 新しいノードグループで netkit を試す

netkit 対応カーネルのノードのみで実施します。新しいノードグループを作成またはアップグレードし、`bpf.datapathMode=auto` にします。次に `cilium-dbg status` で設定済み／稼働中モードを、`ip -d link show` でデバイス種別を、`bpftool net show` で netkit attachment を確認します。netkit と同時に `bpf.tproxy=true` を設定すると、1.19以降は agent が netkit を拒否します（`auto` は veth にフォールバック）。ロールバック：既存 veth Pod をその場で切り替えず、ノードを drain して交換してください。

## バージョン差分

| 項目 | 1.18.14 | 1.19.8 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|---|---|
| 最小カーネル（ドキュメント） | 5.10（RHEL 8.10 では4.18） | 5.10 | 5.10 | 5.10 |
| `bpf_network.c` | あり | あり | **削除** | 削除 |
| `CILIUM_CALL_SIZE` | 48 | 49 | 50 | 50 |
| 設定変数（grep の数） | 18 | 43 | 73 | 104 |
| Policy map 名 | `cilium_policy_v2_` | `cilium_policy_v2_` | `cilium_policy_v3_` | `cilium_policy_v3_`（auth bit は予約済み） |
| Node map | v1 + v2 | v2 のみ | v2 | v2 |
| Egress gateway map | `..._v4` | `..._v4` | `..._v4_v2` | `..._v4_v2` |
| `cilium_devices` map | なし | なし | あり | あり |
| `--datapath-mode` の値 | veth、netkit、netkit-l2 | 同左 | + `auto` | + `auto` |
| `bpf.tproxy` | beta（netkit 検査なし） | beta、netkit を拒否 | beta、netkit を拒否 | beta、netkit を拒否 |
| Datapath Plugin | なし | なし | あり（beta） | あり |
| Mutual auth map（`--bpf-auth-map-max`） | あり | あり | あり、mutual auth は非推奨 | 削除 |
| `--enable-bpf-stats` | なし | なし | なし | あり |
| `--node-port-mode`、`--node-port-algorithm` | あり | あり | 削除（`--bpf-lb-mode`、`--bpf-lb-algorithm` を使用） | 削除 |
| Policy deny 時の ICMP 応答 | なし | なし | あり（tail slot 48-49） | あり |

1.21 の pre-release tree にある upgrade note はまだ1.20の文面のままなので、現時点で信頼できる1.21の差分情報はありません。

## トラブルシューティング

| 症状 | 考えられる原因 | 確認方法 |
|---|---|---|
| `DROP_EP_NOT_READY`（code -203）で drop される | endpoint 作成中または削除中に policy slot が空 | `cilium-dbg endpoint list`。入れ替え中の一時的な状態です。続く場合は再生成に失敗しています |
| 「Missed tail call」による drop | array が未設定、または reload 失敗後に commit の順序が崩れた | agent log の load error、`cilium-dbg endpoint log <id>` を確認し、agent Pod を再起動 |
| 新しい接続が失敗し、CT map の `cilium_bpf_map_pressure` が1に近い | CT／NAT map が満杯 | `cilium-dbg map list -v`。`bpf.mapDynamicSizeRatio` または明示的な上限を増やし、NAT は CT の最大2/3とする。resize で entry が消える点にも注意 |
| map の使用量増加後に Service が一致しなくなる | LB map の上限に到達 | `bpf.lbMapMax`（6つの map に適用）を確認。resize は通信に影響します |
| agent が起動せず、「Require support for tcx links」または helper error が出る | カーネルが基準より古い | `uname -r`、`cilium-dbg status` を確認し、対応 AMI に移行 |
| tcx ではなく従来の tc にプログラムがある | カーネルが6.6より古い、または `enableTCX: false` | `bpftool net show`、`tc filter show` |
| netkit が拒否される | 前提条件が不足（host routing、BPF masquerade、KPR、tproxy、カーネル） | agent log の理由、`cilium-dbg status` の設定済み／稼働中モード |
| load 時に検証器が拒否する | 珍しい機能の組み合わせ、またはカーネル上限 | agent stderr の検証器ログ全体を確認し、5.10／6.1／net-next のテスト済みビルドと比較 |
| `hubble observe` に flow が表示されない | perf-buffer または observer queue の loss、aggregation が高すぎる、ring が小さすぎる | `source` 別の `hubble_lost_events_total`、`bpf.monitorAggregation`、`hubble.eventBufferCapacity` |
| 古いガイドが `cilium_tunnel_map` の dump を案内している | map は削除済み | `cilium-dbg bpf ipcache list` を使用 |
| 1.20へのアップグレード後、socket-LB 無効または host-namespace-only で Pod -> NodePort が失敗する | LB がクライアント Pod の tc hook で処理されるようになった | client の送信ポリシーと backend の受信ポリシーで許可 |

## 検証範囲と情報源

このレビューでは live cluster に対して演習を実行していません。コマンドと flag は上流のソースおよびドキュメントに照らして確認しました。trace にある ID、IP、identity は説明用です。ソースの事実は Cilium v1.20.2 tree（例：`bpf/bpf_lxc.c`、`bpf/lib/tailcall.h`、`bpf/lib/policy.h`、`bpf/lib/eps.h`、`pkg/datapath/loader/tc.go`、`pkg/bpf/collection.go`、`Documentation/cmdref/cilium-agent.md`）を確認しました。行番号はリリースごとに移動するため、使用する正確な tag を確認してください。未検証事項：agent image に `bpftool` が含まれるか、`bpf_sock_destroy` kfunc が導入された正確なカーネルバージョン、**[1.21 pre-release]** の stats report（ソース `cilium-dbg/cmd/bpf_stats_report.go` は読んだものの実行していません）。

- Cilium v1.20.2 のシステム要件: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst
- Maps reference: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/ebpf/maps.rst（`cilium_ct_{4,6}_global` と記載されていますが、実際の名前は `cilium_ct4_global` と `cilium_ct6_global` です）
- BPF source: https://github.com/cilium/cilium/tree/v1.20.2/bpf
- Datapath loader: https://github.com/cilium/cilium/tree/v1.20.2/pkg/datapath/loader
- Agent flags: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/cmdref/cilium-agent.md
- Datapath Plugin: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/contributing/development/plugins.rst
- Upgrade note: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc
- Performance tuning（netkit、BIG TCP）: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst
- **[1.21 pre-release]** BPF stats: https://github.com/cilium/cilium/tree/v1.21.0-pre.3/pkg/bpf/stats

## クイズ

[Part 8 のクイズ](../../quizzes/networking/cilium/08-ebpf-datapath-internals-quiz.md)で理解度を確認してください。
