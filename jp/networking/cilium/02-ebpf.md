# eBPF テクノロジー詳解

> **レビュー基準**: Cilium 1.20.2、Linux 5.10+ または文書化された同等のバックポート（例: RHEL 8.10 の 4.18 カーネル）、検証済み Kubernetes 1.33–1.36。個々の BPF 機能にはそれぞれ別の要件があります。
> **最終更新**: October 15, 2026

## ラボ環境のセットアップ

保守されているディストリビューション、以下で使用する tracepoint、およびトレーシングプログラムをロードする権限を備えた使い捨ての Linux 開発 VM を使用してください。これは Cilium のインストールとは別です。クラスタノードに実験的なプログラムをロードしないでください。Linux 6.12 は verifier の説明におけるソース参照であり、すべての 6.12 ディストリビューションがすべての機能を有効にしているという主張ではありません。

必要なツールは、BPF バックエンドを含む Clang、ターゲットアーキテクチャの UAPI ヘッダー、libbpf 1.x 開発ヘッダー/ライブラリ、libelf、zlib、C コンパイラ、および bpftool です。BCC と bpftrace は任意の代替手段です。Debian/Ubuntu のパッケージ名には通常 `clang`、`libbpf-dev`、`libelf-dev`、`zlib1g-dev`、`build-essential`、`pkg-config` が含まれます。bpftool のパッケージはディストリビューション/カーネルに依存します。すべての Debian システムで `linux-tools-generic` が利用可能または適切であると想定しないでください。Cilium は AMD64/AArch64 ホストを文書化しています。Cilium をコンテナイメージ外でネイティブに実行する場合は、Clang/LLVM 18.1+ も必要であり、これはこの小規模トレーシングラボとは別の要件です。

```bash
uname -r
clang --version
clang --print-targets
pkg-config --modversion libbpf
bpftool version
test -r /sys/kernel/tracing/events/syscalls/sys_enter_execve/format
test -r /sys/kernel/tracing/events/sched/sched_process_exec/format
# Active feature probing: run only on the prepared lab VM.
sudo bpftool feature probe kernel
```

Tracefs はマウントされアクセス可能でなければなりません。一部のシステムでは `/sys/kernel/debug/tracing` 配下に公開されます。カーネル設定、capability、lockdown/LSM ポリシー、コンテナの制限により、コンテナ root であってもロードやアタッチが妨げられる可能性があります。`CAP_BPF` 単独は汎用的なトレーシング権限ではありません。要件はカーネル、プログラムタイプ、BPF-token delegation に依存します。

**検証の境界:** これらの例は、libbpf 1.7 に対するホスト C 構文チェック、userspace リンク、および決定的な helper シミュレーションに合格しました。Clang の BPF ターゲットコンパイル、実行中カーネルの verifier、ライブ tracepoint アタッチには、準備した VM での検証が依然として必要です。これらは本番環境でテスト済みでも、損失のないトレーシングレシピでもありません。

## eBPF テクノロジーの導入と歴史的背景

eBPF により、承認されたプログラムはサポートされた Linux hook で実行され、カーネルの動作を観測または制御できます。検証によりメモリアクセスと実行は制限されますが、カーネル、verifier、JIT、helper のバグは依然として起こり得ます。受理されたからといって、ホストがクラッシュしないことやプログラムが意図したポリシーを実装していることが証明されるわけではありません。

### BPF から eBPF へ: 進化の歴史

McCanne と Jacobson の *The BSD Packet Filter: A New Architecture for User-level Packet Capture* のプレプリント日は 1992 年 12 月 19 日であり、1993 年 1 月 25–29 日の Winter USENIX での発表を明記しています。年を引用する際には、この区別を維持してください。Classic BPF は、userspace への不要なパケットコピーを避けるフィルタリングのために、32 ビットの A/X レジスタと scratch memory を使用します。制限された命令セットであっても、最新の CPU で実行できないことを意味するわけではありません。

Extended BPF は、R0–R10 の 11 個のレジスタ（R10 は読み取り専用の frame pointer）、一般に 512 バイトに制限されるスタック、map、およびより多くのプログラムタイプを備えた 64 ビット命令セットを追加しました。これは、汎用レジスタが 10 個から 11 個へ変わったという歴史的変更ではありません。function/tail-call の組み合わせにより、追加のスタック制限が課されることがあります。

### eBPF の技術的進化: カーネルバージョン別の主な機能

以下の選択した upstream のマイルストーンは、バージョン付きソースに対して確認されています。これらはディストリビューションのサポートマトリクスではありません。バックポート、ビルドオプション、アーキテクチャ、helper は異なります。

| Kernel | 選択したマイルストーン |
|---|---|
| [3.15](https://github.com/torvalds/linux/blob/v3.15/include/linux/filter.h) | 拡張命令セット、内部 classic-BPF 変換 |
| [3.16](https://github.com/torvalds/linux/blob/v3.16/arch/x86/net/bpf_jit_comp.c) | x86 extended-BPF JIT |
| [3.18](https://github.com/torvalds/linux/blob/v3.18/include/uapi/linux/bpf.h) | BPF syscall/verification infrastructure。まだ利用可能な HASH/ARRAY map type はありません |
| [3.19](https://github.com/torvalds/linux/blob/v3.19/include/uapi/linux/bpf.h) | HASH/ARRAY map と socket-filter program type |
| [4.1](https://github.com/torvalds/linux/blob/v4.1/include/uapi/linux/bpf.h) | KPROBE および TC SCHED_CLS/SCHED_ACT |
| [4.2](https://github.com/torvalds/linux/blob/v4.2/include/uapi/linux/bpf.h) | PROG_ARRAY と tail call |
| [4.8](https://github.com/torvalds/linux/blob/v4.8/include/uapi/linux/bpf.h) | XDP program type |
| [4.10](https://github.com/torvalds/linux/blob/v4.10/include/uapi/linux/bpf.h) | LRU hash map |
| [4.16](https://github.com/torvalds/linux/blob/v4.16/include/uapi/linux/bpf.h) | BPF-to-BPF function call |
| [4.17](https://github.com/torvalds/linux/blob/v4.17/include/uapi/linux/bpf.h) | Raw tracepoint |
| [4.18](https://github.com/torvalds/linux/blob/v4.18/include/uapi/linux/bpf.h) | BTF load API |
| [5.2](https://github.com/torvalds/linux/blob/v5.2/include/uapi/linux/bpf.h) | global data に使用する直接 map-value access |
| [5.7](https://github.com/torvalds/linux/blob/v5.7/include/uapi/linux/bpf.h) | BPF link API と BPF LSM |
| [5.8](https://github.com/torvalds/linux/blob/v5.8/include/uapi/linux/bpf.h) | BPF ring buffer |
| [5.10](https://github.com/torvalds/linux/blob/v5.10/include/uapi/linux/bpf.h) | サポートされる attachment type 用の sleepable program |
| [5.15](https://github.com/torvalds/linux/blob/v5.15/include/uapi/linux/bpf.h) | BPF timer helper |
| [5.19](https://github.com/torvalds/linux/blob/v5.19/include/uapi/linux/bpf.h) | Dynamic-pointer helper |
| [6.2](https://github.com/torvalds/linux/blob/v6.2/kernel/bpf/helpers.c) | 型付き object-allocation kfunc。制限のない malloc ではありません |

Bounded loop は Linux 5.3 で導入されました。[upstream verifier change](https://github.com/torvalds/linux/commit/2589726d12a1b12eaaa93c7f1ea64287e383c7a5) は loop analysis と state pruning を説明しています。設計 FAQ に残っている古い「loops are not implemented」の段落は、現在の機能ガイダンスではありません。Bounded loop も verifier の複雑性制限を超える場合があります。

### 成長と適用分野

Cilium の公開リポジトリは 2015 年 12 月に作成されました。「プロジェクトは 2017 年に開始した」は不正確です。リポジトリの作成は、正確な製品ローンチ日でも「最初の主要プロジェクト」ステータスの証明でもありません。

| 分野 | 例と境界 |
|---|---|
| ネットワーキング | Cilium/Calico datapaths, Katran load balancing and XDP filtering |
| ランタイムセキュリティ | Falco、Tracee、Tetragon はカーネルイベントを使用します。enforcement は製品と hook に依存します |
| トレーシング | BCC（Python/Lua frontend を含む）、bpftrace、storage および block-I/O tracing |
| ネットワーク可観測性 | Hubble の flow/proxy event。flow graph は分散アプリケーション span tracing ではありません |
| Service mesh | Cilium はカーネル forwarding と userspace proxy を組み合わせ、サポートされる L7 機能を提供します |
| コミュニティ | eBPF Foundation はエコシステムを支援します。資金提供とプロジェクト成熟度は互換性の基準ではありません |

`seccomp-bpf` は、system-call の決定に classic BPF filter interface を使用します。Linux は内部で classic filter を変換することがありますが、これは汎用的な eBPF program/map/helper API ではありません。

### eBPF と従来のカーネルモジュール: パラダイムシフト

| 特性 | eBPF | カーネルモジュール |
|---|---|---|
| 安全性 | Verifier による制約。実装バグと運用リスクは依然として残ります | より広いネイティブカーネルアクセス。バグはホストを不安定にする可能性があります |
| デプロイ | サポートされるプログラムは再起動なしでロード/アタッチできます | 多くのモジュールも、依存関係と使用状況が許せば再起動なしでロード/アンロードできます |
| 互換性 | Instruction/helper ABI および機能要件。CO-RE はサポートされる type access を relocate できます | Kernel/module ABI、設定、ディストリビューションのサポート |
| パフォーマンス | 多くは JIT コンパイルされます。overhead は hook、program、workload により決まります | ネイティブ実行にも workload 依存のコストがあります |
| 開発 | 制限された context、helper/kfunc、verifier の制限 | Kernel API と通常のカーネル開発上の制約 |
| 権限 | ロード/アタッチに必要な適切な権限または delegation | 特権ロード。signing/lockdown により制限されることがあります |

どちらも運用テストが必要です。モジュールはベンダー実装に限定されず、eBPF も本番ロールアウトを本質的に安全にするわけではありません。

## カーネル内部における eBPF アーキテクチャの詳細分析

### eBPF アーキテクチャコンポーネントの詳細説明

userspace では、Clang は C を BPF ELF にコンパイルします。Rust は独自のコンパイラ/toolchain エコシステムを使用します。libbpf は ELF section、map、relocation、ロード、サポートされるアタッチ API を処理します。BCC はより高水準の API を提供し、bpftrace はトレーシング言語を提供します。

CO-RE は BTF と relocation を使用して、サポートされる type/field access を適応させます。不足している helper、プログラムタイプ、カーネル設定を提供するものではなく、任意の cross-architecture/kernel 互換性を保証するものでもありません。カーネル内部構造、tracepoint format、kfunc は、プログラムが BTF を使用しているというだけで安定した ABI にはなりません。

カーネルでは、verifier が program type、context、helper、権限に対してプログラムを検査します。JIT は受理された BPF をネイティブ命令に変換できます。サポートされる場合、interpreter は別の実行メカニズムです。JIT 出力がその後に必須の第 2 VM stage を通過することはありません。アタッチはロードされたプログラムを hook に接続します。ロードだけでは tracepoint を subscribe しません。

### eBPF プログラムライフサイクルの詳細分析

1. **開発:** hook/context を選択し、map/license metadata を定義します。すべてのプログラムが GPL 互換性を必要とするわけではありませんが、GPL 専用 helper と特定の type/kfunc には制約があります。これらのトレーシングサンプルは helper に合わせ GPL metadata を使用します。
2. **コンパイル:** ターゲット toolchain と header を使用して、BPF ELF および必要な debug/BTF 情報を作成します。
3. **Open/load:** ELF を parse し、map を作成または明示的に再利用し、relocate して BPF load API を呼び出します。検証と任意の JIT はロード中に発生します。
4. **アタッチ:** 適切な API を使用します。libbpf は `SEC("tracepoint/...")` からこれらの tracepoint を推論できます。link/attachment を維持してください。
5. **実行/観測:** event がプログラムを呼び出し、userspace が map/buffer を読み取ります。sampling と容量制限により観測が失われる場合があります。
6. **更新/アンロード:** 互換性のある map/link/pin は意図的にのみ維持してください。このラボの link を破棄し、object を close してリソースを解放します。

Linux 6.12 では、プログラム長は BPF 対応のロードパスで最大 1,000,000 命令、unprivileged path で 4,096 命令に制限されます。verifier には別途 1,000,000 命令の **analysis complexity** 制限があります。より小さなプログラムでも検証に失敗する場合があります。Unprivileged BPF はしばしば無効化されています。token/capability と program-type の検査は引き続き適用されます。

### eBPF プログラムタイプと特性

| Hook / program type | 目的と return-value の境界 |
|---|---|
| XDP / `BPF_PROG_TYPE_XDP` | Native driver XDP は skb allocation 前に実行されます。generic/offloaded mode は異なります。`XDP_DROP`、`PASS`、`TX`、`REDIRECT` は action であり、throughput 保証ではありません |
| TC / `SCHED_CLS`, `SCHED_ACT` | Ingress/egress packet classification/actions。classifier の `TC_ACT_*` semantics には適切な direct-action setup が必要です |
| Socket filter / `SOCKET_FILTER` | Socket packet delivery: zero は drop、正の capture length は truncate する場合があります。作成/connect policy には他の hook を使用します |
| kprobe/uprobe / `KPROBE` | Kernel/userspace probe。個別の `BPF_PROG_TYPE_UPROBE` はありません。inlining、blacklist、symbol availability がアタッチを制約します |
| Tracepoint / `TRACEPOINT` | 静的に宣言された event context。ターゲット format を検査してください。安定したカーネル ABI は保証されません |
| Perf event / `PERF_EVENT` | Performance sampling。return behavior は perf-event integration に依存します |
| cgroup / `CGROUP_SKB`, `CGROUP_SOCK`, `CGROUP_SOCK_ADDR`, etc. | Network/socket control。context と allow/deny convention は異なります |
| LSM / `LSM` | MAC-style program は通常、先行する error を保持し zero/error を返します。cgroup-LSM には異なる grant semantics があります |
| Socket operations / `SOCK_OPS` | TCP callback。operation、reply field、helper support が重要です |
| fentry/fexit / `TRACING` | サポートされる場合の BTF ベースの function tracing。target と attachment の制約は残ります |

可視性/制御のニーズに応じて hook を選択してください。XDP には後段 stack の context が一部ありません。TC は skb-backed traffic を処理します。tracepoint/probe の観測は自動的に network policy を enforcement するものではありません。context struct や return code を program type 間でコピーしないでください。

### eBPF Map: データ共有と状態保存の中核

FD、ロード済み program、明示的な bpffs pin などの参照が残っている間、map は存続します。pin はディスク永続化ではなく、再起動後に map content を保持しません。再ロードしても古い map を自動的に再利用しません。

| Type | 用途と制約 |
|---|---|
| `HASH` | 境界付き key/value table。満杯時に挿入が失敗することがあります。期待される定数時間 lookup は latency を保証しません |
| `ARRAY` | 有効な index にある preallocated、zero-initialized value。zero は存在しない hash entry ではありません |
| `LRU_HASH` | LRU-style eviction を備えた境界付き cache。損失のない累積 counter ではありません |
| `RINGBUF` | CPU をまたぐ multiple producer/single consumer。key/value size は zero、power-of-two byte capacity。予約失敗は block しません |
| `PERF_EVENT_ARRAY` | Per-CPU perf channel。userspace は event を provision/consume し、lost record を追跡する必要があります |
| `PROG_ARRAY` | Tail-call program reference。互換性のある target と call limit が適用されます |
| `PERCPU_HASH` / `PERCPU_ARRAY` | Cross-CPU contention は少なくなりますが、普遍的に race-free ではありません。userspace は必要な padding を含め、すべての possible-CPU slot を読み取ります |
| `SOCKMAP` / `SOCKHASH` | サポートされる redirection/program 用の socket reference。任意の socket-operation hook 用ではありません |

libbpf 1.x では `struct bpf_map_def SEC("maps")` が削除されました。これらの BTF-style definition は、実際の type を使用して 8 つの map category を示しています。必要な map を適切な program と組み合わせてください。宣言だけでは event pipeline になりません。

**`map_types.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

/* Definitions only; combine the needed maps with a suitable program. */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} hash_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} total SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} cache SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __type(key, __u32);
    __type(value, __u32);
    /* libbpf determines max_entries from the number of possible CPUs. */
} perf_events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PROG_ARRAY);
    __uint(max_entries, 10);
    __type(key, __u32);
    __type(value, __u32);
} jump_table SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} cpu_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_SOCKMAP);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u32);
} sockets SEC(".maps");
```

共有 counter には atomic increment が必要です。新しい hash key には `BPF_NOEXIST` insertion を行い、その後 winning entry を lookup/increment します。`BPF_ANY` initialization は別の CPU の count を上書きする可能性があります。Array entry は有効な index にすでに存在します。

## Cilium における eBPF の活用: コンテナネットワーキングの革新

### Cilium アーキテクチャと eBPF の役割

![Cilium の論理的役割: Kubernetes state と Operator、ノードごとの agent、kernel program/map、および Hubble flow observation。](../../.gitbook/assets/en-networking-cilium-02-ebpf-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-02-ebpf-1.html)

この図は論理的な責務を示しており、必須の配置や単一の compilation pipeline を示すものではありません。CLI はクラスタ外で実行できます。agent は対象となる管理ノードで実行されます。Program build/load の詳細はバージョン/機能によって異なります。Hubble Relay は flow を集約します。Prometheus metric は別の endpoint を使用します。

agent は endpoint、identity、policy、datapath state を reconcile します。Operator は identity/IPAM lifecycle など、設定されたクラスタ全体の task を処理します。これは packet-forwarding path ではありません。Hubble は BPF flow information と userspace proxy event を組み合わせます。

### Cilium の eBPF Datapath の詳細分析

これらは協調する機能であり、すべての packet に対する固定された順序ではありません。

1. **エントリ:** packet が存在する前に socket hook が Service backend を解決できます。TC は packet path を処理します。任意の XDP acceleration はサポートされる external traffic を処理します。
2. **Identity/policy:** IP/identity と endpoint policy が L3/L4 access を制御します。サポートされる HTTP/gRPC policy は Envoy を使用し、DNS policy は DNS proxy を使用します。L7 parsing/enforcement は完全に BPF で行われるわけではありません。
3. **状態/変換:** conntrack、service/backend、reverse-NAT、affinity map には異なる役割があります。すべての packet が backend selection を繰り返すわけではありません。
4. **Forwarding:** native routing または設定済み overlay が traffic を運びます。DSR dispatch/return path には、選択した mode のネットワーク前提条件が必要です。
5. **観測:** datapath counter/event と proxy event には設定と collection-loss の制限があります。

Backend readiness は control-plane state と適用可能な health mechanism から得られるものであり、汎用的な BPF application probe から得られるものではありません。Maglev、affinity、DSR、acceleration は機能の選択肢であり、普遍的なデフォルトではありません。

### Cilium の主要 eBPF プログラムの詳細説明

| Cilium 1.20.2 source | 役割 |
|---|---|
| `bpf/bpf_lxc.c` | Endpoint packet path、policy、conntrack、forwarding |
| `bpf/bpf_overlay.c` | Overlay packet path |
| `bpf/bpf_host.c` | Host/device path とサポートされる host-firewall processing |
| `bpf/bpf_xdp.c` | XDP path。設定済み load-balancer acceleration を含む |
| `bpf/bpf_sock.c` | cgroup socket-address hook（IPv4 と IPv6）: connect、sendmsg、recvmsg、getpeername、bind/post_bind、sock_release。socket-level service translation に使用されます |
| `bpf/bpf_wireguard.c` | WireGuard により復号された traffic を mark する `cilium_wg0` device program（`cil_from_wireguard`/`cil_to_wireguard`） |
| `bpf/bpf_sock_term.c` | 削除された Service backend に接続する socket を破棄する BPF iterator（TCP/UDP） |
| `bpf/bpf_probes.c`, `bpf/bpf_alignchecker.c` | Datapath program ではありません。kernel-feature probe は agent startup 時に実行され、C/Go struct-layout check です |
| `bpf/lib/lb.h` | 共有 load-balancing helper |
| `bpf/lib/policy.h` | 共有 policy helper |

loader、attach point、tail call、program ごとの walkthrough については、[eBPF datapath internals](08-ebpf-datapath-internals.md) を参照してください。

このリリースには最上位の `bpf_lb.c` または `bpf_network.c` ファイルはありません。function name と feature gate は変わります。概念的な名前を source file として扱うのではなく、正確なリリースを確認してください。

### Cilium の eBPF Map 使用法

これらの例は安定した map-layout API ではありません。

| 名前 / family | Key と役割 |
|---|---|
| `cilium_lxc` | Address/family → endpoint forwarding metadata。単なる endpoint ID ではありません |
| `cilium_ipcache_v2` | Prefix、address family、cluster context → identity/tunnel metadata |
| `cilium_policy_v3_<endpoint>` | Identity、direction、protocol、destination port、prefix → policy entry |
| `cilium_ct4_global`, `cilium_ct6_global`, `cilium_ct_any4_global`, etc. | Connection-tuple state。実際の map は protocol/family/configuration に依存します |
| `cilium_lb4_services_v2` / `cilium_lb6_services_v2` | Address/port、protocol、scope、backend slot → service metadata/backend reference。backend record は別の map です |
| `cilium_metrics` | Reason、direction、source-location key → packet/byte counter |

`cilium-dbg map get` は userspace-cached content を表示するものであり、必ずしも新しい kernel dump ではありません。サポートされる kernel view には、対応する `cilium-dbg bpf ...` decoder または bpftool を使用してください。トラブルシューティングの近道として Cilium map に raw byte を書き込まないでください。

### eBPF ベース機能とその境界

- **Policy:** Kubernetes NetworkPolicy には L3/L4 semantics があります。Cilium resource はサポートされる capability を追加します。制限のない L4 allow は、重複する L7-restricted allow を bypass する場合があります。combined policy を検査してください。
- **Encryption:** WireGuard/IPsec mode では、BPF は traffic をそれらの kernel facility に誘導します。cryptography は BPF instruction のみで行われるものではありません。選択した mode に対し、key、port、MTU、traffic coverage を設定してください。IPsec と WireGuard の key operation は異なります。
- **Service mesh:** Userspace proxy がサポートされる L7 processing を提供します。Kafka L7 policy は削除されました。Beta workload mTLS/ztunnel には別の前提条件があり、node encryption から暗黙に得られるものではありません。
- **Bandwidth:** EDT/bandwidth-manager と congestion control は end-to-end QoS や throughput を保証しません。
- **Multi-cluster:** Cluster Mesh には connectivity、identity、addressing、互換性のある configuration が必要です。すべての policy object を自動的に同期したり routing を解決したりするものではありません。

## ラボ: eBPF プログラム開発とデバッグ

### 1. 基本的な eBPF プログラム開発

名前付きファイルを新しい lab directory に保存してください。この program は、後で失敗する場合を含め、`execve` **attempt** を記録します。`execveat` には異なる syscall-entry tracepoint があります。Debug print は共有されノイジーであり、本番用 event transport ではありません。`SEC()` は意図する type/hook を提供します。GPL metadata はここで使用する helper に適しています。

**`hello.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("tracepoint/syscalls/sys_enter_execve")
int hello_execve(void *ctx)
{
    (void)ctx;
    char message[] = "execve attempt\n";
    bpf_trace_printk(message, sizeof(message));
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

### 2. Map を使用する高度な eBPF プログラム

`sched_process_exec` は、参照対象のカーネルでは成功した execution transition 後に発行されます。`comm` ごとにカウントします。これは終端を含め最大 16 byte の短い task name であり、一意の executable path/process identity ではありません。名前は衝突/変更する可能性があります。これは host を観測するものであり、自動的に 1 つの Pod を観測するわけではありません。

map は最大 1,024 個の名前を保持します。`lost_events[0]` は name-read failure を、`[1]` は capacity exhaustion を含む使用可能な counter entry のない event をカウントします。これらは起こり得るすべての collection failure を網羅するものではありません。64-bit counter は wrap する場合があります。この lab ではカウント中に entry を削除しません。

**`exec_shared.h`**

```c
#ifndef EXEC_SHARED_H
#define EXEC_SHARED_H
#define COMM_BYTES 16
#define MAX_COMMANDS 1024
struct comm_key {
    char comm[COMM_BYTES];
};
#endif
```

**`exec_count.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include "exec_shared.h"

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_COMMANDS);
    __type(key, struct comm_key);
    __type(value, __u64);
} exec_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 2);
    __type(key, __u32);
    __type(value, __u64);
} lost_events SEC(".maps");

static __always_inline void record_loss(__u32 reason)
{
    __u64 *lost = bpf_map_lookup_elem(&lost_events, &reason);
    if (lost)
        __sync_fetch_and_add(lost, 1);
}

SEC("tracepoint/sched/sched_process_exec")
int count_exec(void *ctx)
{
    (void)ctx;
    struct comm_key key = {};
    __u64 zero = 0;
    if (bpf_get_current_comm(key.comm, sizeof(key.comm)) != 0) {
        record_loss(0);
        return 0;
    }

    __u64 *count = bpf_map_lookup_elem(&exec_counts, &key);
    if (!count) {
        /* A competing CPU may insert first; never overwrite its count. */
        bpf_map_update_elem(&exec_counts, &key, &zero, BPF_NOEXIST);
        count = bpf_map_lookup_elem(&exec_counts, &key);
    }
    if (count)
        __sync_fetch_and_add(count, 1);
    else
        record_loss(1);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

#### Userspace アプリケーションとアタッチメントの存続期間

この loader はいずれかの sample object を受け取り、プログラムをちょうど 1 つロードしてアタッチし、Ctrl-C/SIGTERM まで link を保持します。pin が存在することを仮定せず、同じ object から counter map FD を読み取ります。iteration は NULL から開始し、境界付きで atomic ではない live sample を生成します。

**`run_bpf.c`**

```c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <bpf/bpf.h>
#include <bpf/libbpf.h>
#include "exec_shared.h"

static volatile sig_atomic_t stopping;

static void stop(int signal_number)
{
    (void)signal_number;
    stopping = 1;
}

static int dump_counts(int map_fd, int lost_fd)
{
    struct comm_key current, next;
    const struct comm_key *previous = NULL;
    unsigned int seen = 0;

    while (seen < MAX_COMMANDS) {
        if (bpf_map_get_next_key(map_fd, previous, &next) != 0) {
            if (errno == ENOENT)
                break;
            perror("get next key");
            return -1;
        }
        __u64 value;
        if (bpf_map_lookup_elem(map_fd, &next, &value) == 0)
            printf("%.*s: %" PRIu64 "\n", COMM_BYTES, next.comm,
                   (uint64_t)value);
        else if (errno != ENOENT) {
            perror("lookup count");
            return -1;
        }
        current = next;
        previous = &current;
        seen++;
    }
    for (__u32 reason = 0; reason < 2; reason++) {
        __u64 value;
        if (bpf_map_lookup_elem(lost_fd, &reason, &value) != 0) {
            perror("lookup loss");
            return -1;
        }
        printf("lost[%u]: %" PRIu64 "\n", reason, (uint64_t)value);
    }
    if (fflush(stdout) != 0) {
        perror("flush output");
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    struct bpf_object *object = NULL;
    struct bpf_link *link = NULL;
    int result = 1;
    if (argc != 2) {
        fprintf(stderr, "usage: %s OBJECT.bpf.o\n", argv[0]);
        return 2;
    }
    struct sigaction action = {.sa_handler = stop};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, NULL) || sigaction(SIGTERM, &action, NULL)) {
        perror("sigaction");
        return 1;
    }
    object = bpf_object__open_file(argv[1], NULL);
    if (!object) {
        perror("open BPF object");
        return 1;
    }
    struct bpf_program *program = bpf_object__next_program(object, NULL);
    if (!program || bpf_object__next_program(object, program)) {
        fprintf(stderr, "expected exactly one program\n");
        goto cleanup;
    }
    if (bpf_object__load(object) != 0) {
        fprintf(stderr, "load failed; inspect libbpf/verifier diagnostics\n");
        goto cleanup;
    }
    int counts = bpf_object__find_map_fd_by_name(object, "exec_counts");
    int losses = bpf_object__find_map_fd_by_name(object, "lost_events");
    if (counts >= 0 && losses < 0) {
        fprintf(stderr, "counter object is missing lost_events\n");
        goto cleanup;
    }
    link = bpf_program__attach(program);
    if (!link) {
        perror("attach tracepoint");
        goto cleanup;
    }
    fprintf(stderr, "Attached; Ctrl-C detaches. Counts are live samples.\n");
    result = 0;
    while (!stopping) {
        if (counts >= 0 && dump_counts(counts, losses) != 0) {
            result = 1;
            break;
        }
        sleep(2);
    }
cleanup:
    bpf_link__destroy(link);
    bpf_object__close(object);
    return result;
}
```

#### コンパイルと実行

Debian/Ubuntu の multiarch installation では、GCC の multiarch directory が UAPI `asm/` header を提供します。他のディストリビューションでは path を調整してください。`-g` は `.maps` 用の BTF を提供します。準備した VM の terminal A で loader をコンパイルして開始します。

```bash
MULTIARCH=$(gcc -print-multiarch)
test -n "$MULTIARCH"
clang -O2 -g -target bpf -I"/usr/include/$MULTIARCH" \
  -c hello.bpf.c -o hello.bpf.o
clang -O2 -g -target bpf -I"/usr/include/$MULTIARCH" \
  -c exec_count.bpf.c -o exec_count.bpf.o
cc -O2 -Wall -Wextra run_bpf.c -o run_bpf \
  $(pkg-config --cflags --libs libbpf)
sudo ./run_bpf hello.bpf.o
```

terminal B で `sudo cat /sys/kernel/tracing/trace_pipe` を読み取り、terminal C で `/usr/bin/true` などの外部 executable を実行します。Ctrl-C で hello loader を停止し、次に `sudo ./run_bpf exec_count.bpf.o` を実行します。別の terminal で command を実行すると、name/count pair が変化することを観測します。observer やその他の host activity も event を生成するため、固定された total/PID は保証されません。失敗した `execve` attempt は hello output に現れる場合がありますが、`sched_process_exec` を発行すべきではありません。

`bpftool prog load OBJECT PIN` 単独では、この tracepoint にアタッチしません。この例は意図的に link を所有します。明示的な pinning/reuse は別の lifecycle decision です。`pinmaps` と `map ... pinned ...` は互換性のある構文ではありません。この loader を閉じると、pin されていない resource は解放されます。

### 3. Cilium eBPF プログラムの探索とデバッグ

すでに準備された cluster と正しい kubeconfig context を使用してください。影響を受ける Pod の node 上にある agent を選択してください。endpoint ID は node-local です。明示的な placeholder を置き換えてください。

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-ACTUAL-POD
export ENDPOINT_ID=REPLACE-WITH-NODE-LOCAL-ID
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint get "$ENDPOINT_ID"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg service list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --frontends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
```

必要な policy を `kubectl get networkpolicy,ciliumnetworkpolicy -n YOUR_NAMESPACE` で検査し、適用可能な cluster-wide policy は個別に確認します。endpoint realized state を実際の flow と比較してください。削除された `policy trace` と非推奨の `policy get` は代替になりません。

Ctrl-C で停止しながら、一度に 1 つの monitor を実行してください。

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent --   cilium-dbg monitor --related-to "$ENDPOINT_ID" --type drop
```

発行された policy decision には `--type policy-verdict` を、利用可能な proxy event には `--type l7` を使用してください。可視性は設定に依存します。HTTP rejection は network DROPPED verdict ではなく HTTP 403 となる場合があります。

有効な Hubble Relay では、`cilium hubble port-forward` を実行したままにしてから、以下を使用します。

```bash
hubble status
hubble observe --namespace default --last 20
hubble observe --protocol http --last 20
hubble observe --namespace default --last 20 --output json
```

`jq` に pipe した JSON は service-dependency graph ではありません。有効な Hubble UI は service map（`cilium hubble ui`）を提供します。HTTP visibility にはサポートされる proxy/L7 path が必要です。暗号化された application content は自動的に decode されません。

### 4. パフォーマンス分析と最適化

profiling permission/support を備えた制御された node で、実際の program ID を検査してください。これらの command はローカル kernel state を対象としており、この監査では実行されていません。

```bash
sudo bpftool prog show
export PROG_ID=REPLACE-WITH-ACTUAL-ID
sudo bpftool prog show id "$PROG_ID"
sudo bpftool prog dump xlated id "$PROG_ID"
sudo bpftool prog profile id "$PROG_ID" duration 10 cycles instructions
```

Profiling には metric name と適切な kernel/PMU support が必要です。`bpftool -p map dump ...` は content を pretty-print するものであり、lookup latency ではありません。`perf`/bpftrace は workload を profile できますが、target symbol、probe availability、argument を確認してください。kretprobe は明示的な correlation なしに entry `arg0` を確実に公開しません。

完全な workload を測定するときは、protocol、packet size、concurrency、policy、encryption、proxy、routing を記録してください。XDP/native routing を変更する前に、インストール済み Helm value と `cilium-dbg status --verbose` を検査してください。より高速な hook や synthetic result は application latency の低下を証明するものではありません。

### 5. トラブルシューティングのヒント

| 症状 | 確認事項 |
|---|---|
| C build が失敗する | 正しい UAPI/libbpf header、BPF compiler target、`__u32`/`__u64`、BTF 用の `-g` |
| Verifier rejection | Loader stderr/verifier log、bound、stack initialization、helper、license、complexity |
| ロード済みだが event がない | Attachment/link lifetime、正確な tracepoint、trigger、権限 |
| Map data がない | 同じ map instance、insertion error/capacity、key の意味、reference/pin lifetime |
| 誤った Cilium flow | 正しい node/endpoint、combined desired/realized policy、route/backend state、L7 proxy behavior |
| Hubble record がない | Relay、filter、設定済み visibility、lost-event reporting |

`trace_pipe` には trace output があり、verifier diagnostic はありません。隔離した VM で意図的に load test を行うには、bpftool `-d` が loader/verifier diagnostic を提供します。ロードしても attachment や動作が証明されるわけではありません。test を成功させるために policy を無効化したり、本番の privilege を拡大したり、map を書き換えたりしないでください。

## ソース

- [Original BPF paper](https://www.tcpdump.org/papers/bpf-usenix93.pdf), [Linux BPF design Q&A](https://docs.kernel.org/bpf/bpf_design_QA.html), [verifier](https://docs.kernel.org/bpf/verifier.html), [ring buffer](https://docs.kernel.org/bpf/ringbuf.html), [licensing](https://docs.kernel.org/bpf/bpf_licensing.html), [seccomp](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [Linux 6.12 BPF loading](https://github.com/torvalds/linux/blob/v6.12/kernel/bpf/syscall.c), [exec event placement](https://github.com/torvalds/linux/blob/v6.12/fs/exec.c), [libbpf 1.7](https://github.com/libbpf/libbpf/tree/v1.7.0), [bpftool 7.7](https://github.com/libbpf/bpftool/releases/tag/v7.7.0)
- [Cilium 1.20.2 BPF source](https://github.com/cilium/cilium/tree/v1.20.2/bpf), [maps](https://github.com/cilium/cilium/tree/v1.20.2/pkg/maps), [load-balancer maps](https://github.com/cilium/cilium/tree/v1.20.2/pkg/loadbalancer/maps), [command reference](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/cmdref)
- [Cilium system requirements](https://docs.cilium.io/en/v1.20/operations/system_requirements/), [Kubernetes compatibility](https://docs.cilium.io/en/v1.20/network/kubernetes/compatibility/), [kube-proxy replacement](https://docs.cilium.io/en/v1.20/network/kubernetes/kubeproxy-free/), [encryption](https://docs.cilium.io/en/v1.20/security/network/encryption/)

## クイズ

[理解度を確認する](../../quizzes/networking/cilium/02-ebpf-quiz.md).
