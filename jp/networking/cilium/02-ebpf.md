# eBPF 技術の詳細解説

> **レビュー基準**: Cilium 1.20.3、Linux 5.10 以降または文書化された同等の backport（例: RHEL 8.10 の kernel 4.18）、検証対象 Kubernetes 1.33–1.36。個々の BPF 機能には別途要件があります。
> **最終レビュー**: 2026年10月16日

## ラボ環境のセットアップ

保守対象のディストリビューションを使う使い捨て Linux 開発 VM を用意し、以下で使う tracepoint と tracing program をロードする権限を確認してください。これは Cilium のインストールとは別です。実験用 program を cluster node にロードしないでください。Linux 6.12 は verifier の説明に使う参照元であり、6.12 の全ディストリビューションですべての機能が有効だという意味ではありません。

必要なツールは、BPF backend を備えた Clang、対象アーキテクチャの UAPI header、libbpf 1.x の開発用 header/library、libelf、zlib、C compiler、bpftool です。BCC と bpftrace は代替ツールとして任意です。Debian/Ubuntu の package 名には通常 `clang`、`libbpf-dev`、`libelf-dev`、`zlib1g-dev`、`build-essential`、`pkg-config` などがあります。bpftool の package はディストリビューション/kernel によって異なります。`linux-tools-generic` がすべての Debian system で利用可能または適切とは限りません。Cilium は AMD64/AArch64 host を文書化しています。Cilium を container image の外でネイティブ実行するには Clang/LLVM 18.1 以降も必要ですが、これはこの小規模な tracing lab とは別の要件です。

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

tracefs が mount 済みでアクセス可能である必要があります。一部の system では `/sys/kernel/debug/tracing` に公開されます。kernel configuration、capability、lockdown/LSM policy、container の制限によっては、container root でも program のロードや attach が拒否される場合があります。`CAP_BPF` だけで tracing 権限が常に得られるわけではありません。必要な権限は kernel、program type、BPF token の委譲によって異なります。

**検証範囲:** これらの例では、libbpf 1.7 に対する host-side C 構文検査、userspace link、決定論的な helper simulation が通過しました。Clang による BPF target compile、実行中 kernel の verifier、live tracepoint への attach は、準備した VM 上で別途検証が必要です。本番での動作確認済み、またはイベントを取りこぼさない tracing recipe ではありません。

## eBPF 技術の概要と歴史的背景

eBPF は、対応する Linux hook で承認された program を実行し、kernel の動作を観測したり影響を与えたりします。verification は memory access と実行を制限しますが、kernel、verifier、JIT、helper の bug がなくなるわけではありません。program が受け入れられたことは、host が crash しないことや、program が意図した policy を実装することの証明ではありません。

### BPF から eBPF へ: 発展の歴史

McCanne と Jacobson の論文 *The BSD Packet Filter: A New Architecture for User-level Packet Capture* は、preprint の日付を1992年12月19日とし、発表を1993年1月25–29日の Winter USENIX としています。年を引用する際はこの違いを保ってください。Classic BPF は、不要な packet copy を userspace に行わずに filter するため、32-bit の A/X register と scratch memory を使用します。命令セットが制限されていることは、最新 CPU 上で実行できないという意味ではありません。

Extended BPF では、11個の register R0–R10（R10 は読み取り専用 frame pointer）、一般に上限512 byte の stack、map、さらに多くの program type を備えた64-bit 命令セットが追加されました。これは汎用 register 数が10個から11個へ変わった歴史ではありません。function call と tail call の組み合わせには、追加の stack 制限が適用される場合があります。

### kernel version ごとの eBPF の主な進化

以下は version 固定の source で確認した、選択した upstream の milestone です。ディストリビューションの対応表ではありません。backport、build option、architecture、helper によって利用可否は異なります。

| Kernel | 主な milestone |
|---|---|
| [3.15](https://github.com/torvalds/linux/blob/v3.15/include/linux/filter.h) | 拡張命令セット、内部での classic-BPF translation |
| [3.16](https://github.com/torvalds/linux/blob/v3.16/arch/x86/net/bpf_jit_comp.c) | x86 extended-BPF JIT |
| [3.18](https://github.com/torvalds/linux/blob/v3.18/include/uapi/linux/bpf.h) | BPF syscall/verification の基盤。利用可能な HASH/ARRAY map type はまだない |
| [3.19](https://github.com/torvalds/linux/blob/v3.19/include/uapi/linux/bpf.h) | HASH/ARRAY map と socket-filter program type |
| [4.1](https://github.com/torvalds/linux/blob/v4.1/include/uapi/linux/bpf.h) | KPROBE と TC SCHED_CLS/SCHED_ACT |
| [4.2](https://github.com/torvalds/linux/blob/v4.2/include/uapi/linux/bpf.h) | PROG_ARRAY と tail call |
| [4.8](https://github.com/torvalds/linux/blob/v4.8/include/uapi/linux/bpf.h) | XDP program type |
| [4.10](https://github.com/torvalds/linux/blob/v4.10/include/uapi/linux/bpf.h) | LRU hash map |
| [4.16](https://github.com/torvalds/linux/blob/v4.16/include/uapi/linux/bpf.h) | BPF-to-BPF function call |
| [4.17](https://github.com/torvalds/linux/blob/v4.17/include/uapi/linux/bpf.h) | raw tracepoint |
| [4.18](https://github.com/torvalds/linux/blob/v4.18/include/uapi/linux/bpf.h) | BTF load API |
| [5.2](https://github.com/torvalds/linux/blob/v5.2/include/uapi/linux/bpf.h) | global data に使われる map value への直接 access |
| [5.7](https://github.com/torvalds/linux/blob/v5.7/include/uapi/linux/bpf.h) | BPF link API と BPF LSM |
| [5.8](https://github.com/torvalds/linux/blob/v5.8/include/uapi/linux/bpf.h) | BPF ring buffer |
| [5.10](https://github.com/torvalds/linux/blob/v5.10/include/uapi/linux/bpf.h) | 対応する attach type 向けの sleepable program |
| [5.15](https://github.com/torvalds/linux/blob/v5.15/include/uapi/linux/bpf.h) | BPF timer helper |
| [5.19](https://github.com/torvalds/linux/blob/v5.19/include/uapi/linux/bpf.h) | dynamic-pointer helper |
| [6.2](https://github.com/torvalds/linux/blob/v6.2/kernel/bpf/helpers.c) | 型付き object allocation kfunc。制限のない malloc ではない |

Bounded loop は Linux 5.3 で導入されました。[upstream verifier change](https://github.com/torvalds/linux/commit/2589726d12a1b12eaaa93c7f1ea64287e383c7a5) は loop analysis と state pruning を説明しています。古い design FAQ に残る「loop は実装されていない」という記述は、現在の機能案内ではありません。bounded loop も verifier の complexity limit を超えることがあります。

### eBPF の利用領域と普及

Cilium の公開 repository は2015年12月に作成されました。「project が2017年に始まった」という説明は正確ではありません。repository 作成日は、厳密な製品 launch 日や「最初の主要 project」である証拠ではありません。

| 領域 | 例と適用範囲 |
|---|---|
| Networking | Cilium/Calico datapath、Katran load balancing、XDP filtering |
| Runtime security | Falco、Tracee、Tetragon は kernel event を利用。enforcement の可否は製品と hook による |
| Tracing | BCC（Python/Lua frontend を含む）、bpftrace、storage と block-I/O tracing |
| Network observability | Hubble flow/proxy event。flow graph は分散 application span tracing ではない |
| Service mesh | Cilium は対応する L7 機能向けに kernel forwarding と userspace proxy を組み合わせる |
| Community | eBPF Foundation は ecosystem を支援する。資金や project の成熟度は互換性の判定基準ではない |

`seccomp-bpf` は system call の判断に classic BPF filter interface を使います。Linux が classic filter を内部変換する場合はありますが、これは一般的な eBPF program/map/helper API ではありません。

### 従来の kernel module と eBPF: 設計上の違い

| 特性 | eBPF | Kernel module |
|---|---|---|
| 安全性 | verifier による制約があるが、実装 bug と運用リスクは残る | より広く native kernel に access でき、bug が host を不安定にする可能性がある |
| 配備 | 対応 program は reboot せずに load/attach できる | 依存関係や使用状況が許せば、多くの module は reboot せずに load/unload できる |
| 互換性 | instruction/helper ABI と feature 要件。CO-RE は対応する type access を relocate できる | kernel/module ABI、configuration、ディストリビューションの対応状況 |
| Performance | 多くは JIT compile される。overhead は hook、program、workload による | native 実行でも workload に応じた cost が発生する |
| 開発 | 制約された context、helper/kfunc、verifier limit | kernel API と通常の kernel 開発上の制約 |
| 権限 | load/attach に適切な privilege または委譲が必要 | privileged load が必要。署名/lockdown で制限される場合がある |

どちらも運用環境での検証が必要です。module は vendor 実装に限られず、eBPF だからといって本番 rollout が自動的に安全になるわけではありません。

## Kernel 内部の eBPF アーキテクチャを詳しく見る

### eBPF アーキテクチャの構成要素

Userspace では Clang が C を BPF ELF に compile します。Rust には独自の compiler/toolchain ecosystem があります。libbpf は ELF section、map、relocation、load、対応する attach API を扱います。BCC は高水準 API を提供し、bpftrace は tracing language を提供します。

CO-RE は BTF と relocation を使用して、対応する type/field access を適応させます。不足している helper、program type、kernel configuration を補ったり、任意の architecture/kernel 間の互換性を保証したりするものではありません。program が BTF を使うからといって、kernel 内部構造、tracepoint format、kfunc が安定 ABI になるわけではありません。

Kernel 内では verifier が program type、context、helper、権限に照らして program を検査します。JIT は受理された BPF を native instruction に変換できます。対応環境では interpreter も実行方式の一つです。JIT 出力の後に必須の第2段階 VM を通るわけではありません。Attach はロード済み program を hook に接続します。load しただけでは tracepoint を購読しません。

### eBPF program の lifecycle

1. **開発:** hook/context を選び、map と license metadata を定義します。すべての program に GPL compatibility が必要なわけではありませんが、GPL-only helper や一部の type/kfunc には制限があります。ここでの tracing sample は使用する helper に合わせて GPL metadata を設定します。
2. **Compile:** target toolchain と header を使い、BPF ELF と必要な debug/BTF information を生成します。
3. **Open/load:** ELF を解析し、map を作成または明示的に再利用し、relocate して BPF load API を呼び出します。verification と任意の JIT は load 時に行われます。
4. **Attach:** 適切な API を使います。`SEC("tracepoint/...")` から libbpf がこれらの tracepoint を推定できます。link/attachment を保持します。
5. **実行/観測:** event により program が呼び出され、userspace が map/buffer を読み取ります。sampling と容量制限によって観測を取りこぼすことがあります。
6. **更新/unload:** 互換性のある map/link/pin を意図した場合だけ保持します。この lab の link を破棄し、object を close して resource を解放します。

Linux 6.12 では、BPF 対応の load path の program 長上限は1,000,000 instruction、unprivileged path では4,096 instruction です。verifier には別途、1,000,000 instruction の**解析 complexity**上限があります。より小さな program でも verification に失敗することがあります。Unprivileged BPF は無効なことが多く、token/capability と program type の確認も引き続き必要です。

### eBPF program type と特性

| Hook / program type | 目的と戻り値の境界 |
|---|---|
| XDP / `BPF_PROG_TYPE_XDP` | Native driver XDP は skb allocation の前に実行される。generic/offloaded mode は動作が異なる。`XDP_DROP`、`PASS`、`TX`、`REDIRECT` は action であり、throughput の保証ではない |
| TC / `SCHED_CLS`, `SCHED_ACT` | ingress/egress packet の分類/action。classifier の `TC_ACT_*` semantics には適切な direct-action 設定が必要 |
| Socket filter / `SOCKET_FILTER` | socket への packet 配信。0 は破棄、正の capture length は切り詰められる場合がある。create/connect policy には別の hook を使う |
| kprobe/uprobe / `KPROBE` | kernel/userspace probe。独立した `BPF_PROG_TYPE_UPROBE` はない。inline 化、blacklist、symbol の利用可否が attach を制約する |
| Tracepoint / `TRACEPOINT` | 静的に宣言された event context。対象の format を確認する。kernel ABI が常に安定しているわけではない |
| Perf event / `PERF_EVENT` | performance sampling。戻り値の動作は perf-event integration に依存する |
| cgroup / `CGROUP_SKB`, `CGROUP_SOCK`, `CGROUP_SOCK_ADDR` など | network/socket control。context と allow/deny の規約は type によって異なる |
| LSM / `LSM` | MAC 型 program は通常、先行する error を保持し、0/error を返す。cgroup-LSM の許可 semantics は異なる |
| Socket operations / `SOCK_OPS` | TCP callback。operation、reply field、helper 対応状況を考慮する |
| fentry/fexit / `TRACING` | 対応時の BTF-based function tracing。target と attach に制約がある |

観測または制御の要件に合わせて hook を選択してください。XDP には後段 stack の一部 context がありません。TC は skb-backed traffic を扱います。tracepoint/probe で観測しても network policy が自動的に enforcement されるわけではありません。別の program type の context struct や戻り値を流用しないでください。

### eBPF map: data 共有と state 保存の中核

FD、load 済み program、明示的な bpffs pin などの参照が残っている間、map は存続します。pin は disk persistence ではなく、reboot 後も map 内容を保持しません。再 load しても旧 map が自動的に再利用されるわけではありません。

| Type | 用途と制約 |
|---|---|
| `HASH` | key/value の上限付き table。満杯では insert に失敗する。平均的な定数時間 lookup は latency の保証ではない |
| `ARRAY` | 有効な index に事前確保し、0 初期化した value を持つ。0 は hash entry が存在しない状態とは異なる |
| `LRU_HASH` | LRU 方式で eviction する容量制限付き cache。欠損のない累積 counter ではない |
| `RINGBUF` | CPU 間で複数 producer/単一 consumer。key/value size は0、byte capacity は2の累乗。予約失敗は producer を block しない |
| `PERF_EVENT_ARRAY` | CPU ごとの perf channel。userspace 側で event の準備/消費を行い、lost record を追跡する必要がある |
| `PROG_ARRAY` | tail-call 用 program reference。対応する target と call 上限が適用される |
| `PERCPU_HASH` / `PERCPU_ARRAY` | CPU 間の競合を減らすが、常に race-free とは限らない。userspace は必要な padding を使って可能な全 CPU slot を読む |
| `SOCKMAP` / `SOCKHASH` | 対応する redirect/program 用の socket reference。任意の socket operation hook ではない |

libbpf 1.x では `struct bpf_map_def SEC("maps")` が削除されました。以下の BTF-style 定義は、実際の type を使って8種類の map category を示します。必要な map を適切な program と組み合わせてください。定義だけで event pipeline ができるわけではありません。

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

共有 counter には atomic increment が必要です。新しい hash key は `BPF_NOEXIST` で insert し、続いて lookup/increment して勝者側の entry を更新してください。`BPF_ANY` による初期化では、別 CPU の count を上書きする可能性があります。有効な index の ARRAY entry はすでに存在します。

## Cilium における eBPF の活用: container networking

### Cilium architecture と eBPF の役割

![Cilium の論理的な役割: Kubernetes state と Operator、node ごとの agent、kernel program/map、Hubble flow の観測。](../../.gitbook/assets/en-networking-cilium-02-ebpf-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-02-ebpf-1.html)

この図は論理上の役割を示しており、必須の配置場所や単一の compile pipeline を示すものではありません。CLI は cluster 外部で実行できます。agent は対象となる managed node 上で実行されます。program の build/load 手順は version/feature によって異なります。Hubble Relay は flow を集約します。Prometheus metric は別の endpoint を使用します。

Agent は endpoint、identity、policy、datapath state を reconcile します。Operator は identity/IPAM lifecycle など、設定された cluster-wide task を処理します。packet-forwarding path ではありません。Hubble は BPF flow 情報と userspace proxy event を組み合わせます。

### Cilium eBPF datapath の詳しい分析

以下は連携する機能であり、すべての packet に対する固定順序ではありません。

1. **入口:** socket hook は packet が生成される前に Service backend を解決できます。TC は packet path を処理します。任意の XDP acceleration は対応する external traffic を処理します。
2. **Identity/policy:** IP/identity と endpoint policy が L3/L4 access を制御します。対応する HTTP/gRPC policy は Envoy を使用し、DNS policy は DNS proxy を使用します。L7 parsing/enforcement のすべてが BPF によるわけではありません。
3. **State/translation:** conntrack、service/backend、reverse-NAT、affinity map はそれぞれ役割が異なります。すべての packet が backend selection を繰り返すわけではありません。
4. **Forwarding:** native routing または設定した overlay が traffic を運びます。DSR の dispatch/return path には、選択した mode に応じた network prerequisite が必要です。
5. **観測:** datapath counter/event と proxy event には、それぞれ設定条件と収集時の loss limit があります。

Backend の readiness は control-plane state と該当する health mechanism で決まります。BPF の汎用 application probe があるわけではありません。Maglev、affinity、DSR、acceleration は選択機能であり、全環境の default ではありません。

### Cilium の主要 eBPF program

| Cilium 1.20.3 の source | 役割 |
|---|---|
| `bpf/bpf_lxc.c` | endpoint packet path、policy、conntrack、forwarding |
| `bpf/bpf_overlay.c` | overlay packet path |
| `bpf/bpf_host.c` | host/device path と対応する host-firewall 処理 |
| `bpf/bpf_xdp.c` | XDP path。設定された load-balancer acceleration を含む |
| `bpf/bpf_sock.c` | cgroup socket-address hook（IPv4/IPv6）: connect、sendmsg、recvmsg、getpeername、bind/post_bind、sock_release。socket-level の Service translation に使用 |
| `bpf/bpf_wireguard.c` | `cilium_wg0` device program（`cil_from_wireguard`/`cil_to_wireguard`）。WireGuard で復号された traffic に mark を付ける |
| `bpf/bpf_sock_term.c` | BPF iterator（TCP/UDP）。削除された Service backend に接続する socket を破棄する |
| `bpf/bpf_probes.c`, `bpf/bpf_alignchecker.c` | datapath program ではない。agent 起動時に kernel feature を調べ、C/Go struct layout を確認する |
| `bpf/lib/lb.h` | load-balancing helper の共有実装 |
| `bpf/lib/policy.h` | policy helper の共有実装 |

loader、attach point、tail call、program ごとの解説は[eBPF datapath の内部解説](08-ebpf-datapath-internals.md)を参照してください。

この release に top-level の `bpf_lb.c` や `bpf_network.c` はありません。function 名と feature gate は変わるため、概念上の名前を source file と見なさず、対象 release を確認してください。

### Cilium の eBPF map の使用

以下は安定した map-layout API ではありません。

| 名前 / family | key と役割 |
|---|---|
| `cilium_lxc` | address/family → endpoint forwarding metadata。単なる endpoint ID ではない |
| `cilium_ipcache_v2` | prefix、address family、cluster context → identity/tunnel metadata |
| `cilium_policy_v3_<endpoint>` | identity、direction、protocol、destination port、prefix → policy entry |
| `cilium_ct4_global`、`cilium_ct6_global`、`cilium_ct_any4_global` など | connection tuple の state。実際の map は protocol/family/configuration による |
| `cilium_lb4_services_v2` / `cilium_lb6_services_v2` | address/port、protocol、scope、backend slot → Service metadata/backend reference。backend record は別 map |
| `cilium_metrics` | reason、direction、source-location key → packet/byte counter |

`cilium-dbg map get` は userspace cache の内容を表示し、最新の kernel dump とは限りません。対応する kernel view は `cilium-dbg bpf ...` decoder または bpftool で確認してください。troubleshooting の近道として Cilium map に raw byte を書き込まないでください。

### eBPF を利用する Cilium 機能と境界

- **Policy:** Kubernetes NetworkPolicy は L3/L4 semantics を持ち、Cilium resource が対応機能を追加します。制限のない L4 allow によって、重複する L7 制限付き allow が迂回される場合があります。組み合わさる policy を確認してください。
- **暗号化:** WireGuard/IPsec mode では、BPF が traffic をそれらの kernel facility に振り分けます。暗号処理のすべてを BPF instruction が担うわけではありません。選択した mode に応じて key、port、MTU、traffic coverage を設定します。IPsec と WireGuard では key 操作が異なります。
- **Service mesh:** 対応する L7 処理には userspace proxy を使用します。Kafka L7 policy は削除されました。Beta workload mTLS/ztunnel には個別の prerequisite があり、node encryption を有効にしただけでは含まれません。
- **Bandwidth:** EDT/bandwidth-manager と congestion control は、end-to-end QoS や throughput を保証しません。
- **Multi-cluster:** Cluster Mesh には connectivity、identity、addressing、互換性のある configuration が必要です。あらゆる policy object を自動同期したり、routing 問題を解決したりするものではありません。

## Lab: eBPF program の開発と debug

### 1. 基本的な eBPF program の開発

指定された file を新しい lab directory に保存してください。この program は後続で失敗するものも含め、`execve` の**試行**を記録します。`execveat` には別の syscall-entry tracepoint があります。debug print は共有でノイズが多く、本番用 event transport ではありません。`SEC()` は想定する type/hook を指定します。ここでは使用する helper に合わせて GPL metadata を設定します。

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

### 2. map を使う eBPF program

参照先の kernel では、`sched_process_exec` は実行への遷移に成功した後に出力されます。最大16 byte（終端を含む）の短い task 名 `comm` ごとに count します。一意な executable path/process identity ではありません。名前が衝突したり変化したりする場合もあります。これは host を観測し、特定の Pod を自動的に観測するものではありません。

この map は最大1,024個の名前を保持します。`lost_events[0]` は name の読み取り失敗を数え、`[1]` は容量超過を含む、利用可能な counter entry がない event を数えます。これらで考えられるすべての collection failure を捕捉するわけではありません。64-bit counter は wrap する場合があります。count 中に lab が entry を削除することはありません。

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

#### Userspace application と attach の有効期間

この loader はいずれか一方の sample object を受け付け、program を1つだけ load/attach し、Ctrl-C/SIGTERM まで link を保持します。pin が存在すると仮定せず、同じ object の counter map FD を読み取ります。NULL から iteration を始め、上限付きで atomic ではない live sample を表示します。

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

#### Compile と実行

Debian/Ubuntu の multiarch installation では、GCC の multiarch directory が UAPI `asm/` header を提供します。他のディストリビューションでは path を調整してください。`.maps` の BTF には `-g` を使用します。準備した VM の terminal A で loader を compile/start してください。

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

Terminal B で `sudo cat /sys/kernel/tracing/trace_pipe` を実行し、terminal C で `/usr/bin/true` など外部 executable を実行します。hello loader を Ctrl-C で止め、次に `sudo ./run_bpf exec_count.bpf.o` を実行してください。別 terminal で command を実行しながら、変化する name/count の組を観測します。observer 自身や host 上の別 activity も event を発生させるため、一定の総数/PID は保証されません。失敗した `execve` の試行は hello の出力に現れる場合がありますが、`sched_process_exec` は出力されないはずです。

`bpftool prog load OBJECT PIN` だけでは、この tracepoint に attach されません。この例では link の所有権を明示しています。明示的な pin/reuse は別の lifecycle 判断です。`pinmaps` と `map ... pinned ...` は置き換え可能な syntax ではありません。この loader を close すると、pin していない resource は解放されます。

### 3. Cilium eBPF program の調査と debug

準備済みの cluster と適切な kubeconfig context を使います。対象 Pod が動作する node の agent を選んでください。endpoint ID は node ごとです。明示的な placeholder を置き換えます。

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

`kubectl get networkpolicy,ciliumnetworkpolicy -n YOUR_NAMESPACE` で希望する policy を確認し、該当する cluster-wide policy は別途調べます。endpoint の realized state と実際の flow を比較してください。削除された `policy trace` や非推奨の `policy get` は代替になりません。

一度に monitor を1つだけ実行し、Ctrl-C で停止します。

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent --   cilium-dbg monitor --related-to "$ENDPOINT_ID" --type drop
```

出力された policy decision には `--type policy-verdict`、利用可能な proxy event には `--type l7` を使います。可視性は configuration によります。HTTP rejection は network の DROPPED verdict ではなく HTTP 403 の場合があります。

Hubble Relay が有効な場合は、`cilium hubble port-forward` を実行したままにしてから、次を使用します。

```bash
hubble status
hubble observe --namespace default --last 20
hubble observe --protocol http --last 20
hubble observe --namespace default --last 20 --output json
```

JSON を `jq` に pipe しても Service dependency graph にはなりません。有効な Hubble UI は Service map（`cilium hubble ui`）を提供します。HTTP 可視性には対応する proxy/L7 path が必要です。暗号化された application content が自動的に decode されることはありません。

### 4. Performance の分析と最適化

profiling 権限と対応がある control 済み node で、実際の program ID を調べます。以下は local kernel state を対象とした command であり、この audit では実行していません。

```bash
sudo bpftool prog show
export PROG_ID=REPLACE-WITH-ACTUAL-ID
sudo bpftool prog show id "$PROG_ID"
sudo bpftool prog dump xlated id "$PROG_ID"
sudo bpftool prog profile id "$PROG_ID" duration 10 cycles instructions
```

Profiling には metric 名と適切な kernel/PMU support が必要です。`bpftool -p map dump ...` は内容を pretty-print しますが、lookup latency は測定しません。`perf`/bpftrace は workload を profile できますが、対象 symbol、probe の利用可否、argument を確認してください。kretprobe だけでは明示的な correlation なしに entry 時点の `arg0` を確実に取得できません。

workload 全体を測定する際は protocol、packet size、concurrency、policy、encryption、proxy、routing を記録してください。XDP/native routing を変更する前に、インストール済み Helm values と `cilium-dbg status --verbose` を確認します。hook が高速であることや synthetic result が得られたことは、application latency が低下する証明ではありません。

### 5. Troubleshooting のヒント

| 症状 | 確認項目 |
|---|---|
| C build が失敗する | 正しい UAPI/libbpf header、BPF compiler target、`__u32`/`__u64`、BTF 用の `-g` |
| Verifier に拒否される | loader stderr/verifier log、bounds、stack initialization、helper、license、complexity |
| load 済みだが event がない | attach/link の有効期間、正確な tracepoint、trigger、権限 |
| map data が欠ける | 同じ map instance か、insert error/capacity、key の意味、reference/pin の有効期間 |
| Cilium flow が想定と異なる | 正しい node/endpoint、希望 state と実現 state の policy、route/backend state、L7 proxy の動作 |
| Hubble record が欠ける | Relay、filter、設定済み visibility、lost-event report |

`trace_pipe` は trace 出力であり、verifier diagnostic ではありません。隔離 VM 内で意図的に load test する場合、bpftool `-d` は loader/verifier diagnostic を表示します。それでも load は attach や動作の証明ではありません。test を通すために policy を無効化したり、本番権限を拡大したり、map を書き換えたりしないでください。

## 参考資料

- [BPF の原著論文](https://www.tcpdump.org/papers/bpf-usenix93.pdf)、[Linux BPF design Q&A](https://docs.kernel.org/bpf/bpf_design_QA.html)、[verifier](https://docs.kernel.org/bpf/verifier.html)、[ring buffer](https://docs.kernel.org/bpf/ringbuf.html)、[license](https://docs.kernel.org/bpf/bpf_licensing.html)、[seccomp](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [Linux 6.12 BPF loading](https://github.com/torvalds/linux/blob/v6.12/kernel/bpf/syscall.c)、[exec event の配置](https://github.com/torvalds/linux/blob/v6.12/fs/exec.c)、[libbpf 1.7](https://github.com/libbpf/libbpf/tree/v1.7.0)、[bpftool 7.7](https://github.com/libbpf/bpftool/releases/tag/v7.7.0)
- [Cilium 1.20.3 BPF source](https://github.com/cilium/cilium/tree/v1.20.3/bpf)、[maps](https://github.com/cilium/cilium/tree/v1.20.3/pkg/maps)、[load-balancer maps](https://github.com/cilium/cilium/tree/v1.20.3/pkg/loadbalancer/maps)、[command reference](https://github.com/cilium/cilium/tree/v1.20.3/Documentation/cmdref)
- [Cilium system requirements](https://docs.cilium.io/en/v1.20/operations/system_requirements/)、[Kubernetes compatibility](https://docs.cilium.io/en/v1.20/network/kubernetes/compatibility/)、[kube-proxy replacement](https://docs.cilium.io/en/v1.20/network/kubernetes/kubeproxy-free/)、[encryption](https://docs.cilium.io/en/v1.20/security/network/encryption/)

## クイズ

[理解度を確認する](../../quizzes/networking/cilium/02-ebpf-quiz.md)。
