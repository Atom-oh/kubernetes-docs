# eBPF の基礎クイズ

> **対応バージョン**: Linux Kernel 4.18+, Kubernetes 1.25+
> **最終更新**: February 23, 2026

このクイズでは、eBPF (extended Berkeley Packet Filter) の基本概念から Kubernetes 環境での応用まで、全体的な理解を確認します。

## 選択問題

1. eBPF verifier がチェックしないものはどれですか？
   - A) 無限ループがないこと
   - B) 範囲外のメモリアクセスがないこと
   - C) プログラムの実行速度
   - D) 初期化されていない変数を使用していないこと

<details>
<summary>解答を見る</summary>

**解答: C) プログラムの実行速度**

**解説:**
eBPF verifier は、プログラムの安全性を確保するために、無限ループがないこと（DAG 構造の検証）、範囲外のメモリアクセスがないこと、初期化されていない変数を使用していないこと、helper function の呼び出しが正しいこと、プログラムが必ず終了することをチェックします。プログラムの実行速度は verifier の検証項目ではありません。

</details>

2. どの XDP (eXpress Data Path) program の戻り値が、packet を同じ NIC に送り返しますか？
   - A) XDP_DROP
   - B) XDP_PASS
   - C) XDP_TX
   - D) XDP_REDIRECT

<details>
<summary>解答を見る</summary>

**解答: C) XDP_TX**

**解説:**
XDP program の戻り値には、次の意味があります。
- `XDP_DROP`: packet をドロップ
- `XDP_PASS`: kernel stack に渡す
- `XDP_TX`: packet を同じ NIC に戻す
- `XDP_REDIRECT`: 別の interface に転送
- `XDP_ABORTED`: エラー処理

XDP_TX は、packet を受信した network interface に送り返したい場合に使用します。

</details>

3. eBPF Maps の主な役割ではないものはどれですか？
   - A) kernel と user space 間のデータ共有
   - B) state の保存
   - C) eBPF programs のコンパイル
   - D) event data の送信

<details>
<summary>解答を見る</summary>

**解答: C) eBPF programs のコンパイル**

**解説:**
eBPF maps は、kernel と user space の間でデータを共有し、state を保存するために使用されるデータ構造です。Maps は event data の送信（PERF_EVENT_ARRAY、RINGBUF）、key-value storage（HASH）、統計収集（PERCPU_ARRAY）などに使用されます。eBPF programs のコンパイルは Clang/LLVM によって処理され、maps の役割ではありません。

</details>

4. Cilium が kube-proxy を置き換えるときに eBPF が提供する主な利点は何ですか？
   - A) service 数に比例する O(n) performance
   - B) iptables rule evaluation が必要
   - C) map lookup による O(1) performance
   - D) Netfilter を使用する

<details>
<summary>解答を見る</summary>

**解答: C) map lookup による O(1) performance**

**解説:**
従来の kube-proxy（iptables mode）は、service 数が増えるにつれて O(n) の performance 低下が発生します。Cilium は eBPF maps を使用して、一定時間の O(1) lookup performance を提供します。これにより、connection establishment time、CPU 使用率、connections per second など、あらゆる面で大幅な performance 改善が得られます。

</details>

5. bpftrace の主な目的は何ですか？
   - A) eBPF programs を C にコンパイルする
   - B) kernel modules をロードする
   - C) DTrace-style high-level tracing
   - D) container images をビルドする

<details>
<summary>解答を見る</summary>

**解答: C) DTrace-style high-level tracing**

**解説:**
bpftrace は、シンプルな one-liner command で system を trace できる DTrace-style high-level tracing language です。たとえば、system calls のカウント、process ごとの読み取り bytes の追跡、file opens の trace、TCP connections の追跡などを簡単に実行できます。

</details>

6. Tetragon の TracingPolicy で、悪意のある file access が検出されたときに process を即座に終了する action はどれですか？
   - A) action: Block
   - B) action: Sigkill
   - C) action: Deny
   - D) action: Terminate

<details>
<summary>解答を見る</summary>

**解答: B) action: Sigkill**

**解説:**
Tetragon の TracingPolicy では、policy に一致する event が発生したとき、`matchActions` の `action: Sigkill` が SIGKILL signal によって process を即座に終了します。これは sensitive file access や悪意のある network connections をリアルタイムでブロックするために使用されます。

</details>

7. Hubble の主な機能ではないものはどれですか？
   - A) Network flow の観測
   - B) DNS query の追跡
   - C) eBPF programs のコンパイル
   - D) Policy decision の監視

<details>
<summary>解答を見る</summary>

**解答: C) eBPF programs のコンパイル**

**解説:**
Hubble は Cilium に組み込まれた network observability platform で、network flows、DNS queries、HTTP requests、policy decisions などを収集・監視します。Hubble は observability tool であり、eBPF program のコンパイル機能は提供しません。

</details>

8. CO-RE (Compile Once, Run Everywhere) はどの問題を解決しますか？
   - A) eBPF program の実行速度の向上
   - B) 異なる kernel versions 間の portability
   - C) memory usage の削減
   - D) network latency の削減

<details>
<summary>解答を見る</summary>

**解答: B) 異なる kernel versions 間の portability**

**解説:**
CO-RE は libbpf と BTF (BPF Type Format) を使用し、一度コンパイルした eBPF programs をさまざまな kernel versions で実行できるようにします。これにより kernel header への依存が減り、struct relocation が自動的に処理されるため、kernel version ごとの再コンパイルが不要になります。

</details>

9. Falco は eBPF を使用して何を検出しますか？
   - A) Network bandwidth usage
   - B) Runtime anomalous behavior
   - C) Disk capacity
   - D) CPU temperature

<details>
<summary>解答を見る</summary>

**解答: B) Runtime anomalous behavior**

**解説:**
Falco は eBPF を使用して runtime anomalous behavior を検出する CNCF project です。sensitive files の読み取り、containers 内での shell 実行、privilege escalation attempts などの security threats を rules に基づいて検出し、alert を出します。

</details>

10. eBPF programs の stack size limit はいくつですか？
    - A) 128 bytes
    - B) 256 bytes
    - C) 512 bytes
    - D) 1024 bytes

<details>
<summary>解答を見る</summary>

**解答: C) 512 bytes**

**解説:**
eBPF programs には 512 byte の stack size limit があります。この制限を回避するには、PERCPU_ARRAY のような maps を使用して、より大きな buffers を割り当てる必要があります。この制限は kernel の安全性を確保するために存在します。

</details>

## 短答問題

11. eBPF bytecode を native machine code に変換する compiler の名前は何ですか？

<details>
<summary>解答を見る</summary>

**解答: JIT compiler (Just-In-Time compiler)**

**解説:**
JIT compiler は eBPF bytecode を native machine code に変換します。これにより interpreter と比較して 4〜5 倍の performance 向上が得られ、architecture-specific optimizations が適用されます。`/proc/sys/net/core/bpf_jit_enable` を 1 に設定することで有効化できます。

</details>

12. kernel function calls を動的に trace する eBPF program type の名前は何ですか？

<details>
<summary>解答を見る</summary>

**解答: Kprobes (or Kprobe)**

**解説:**
Kprobes は kernel function calls を動的に trace する eBPF program type です。user space functions を trace する Uprobes とは異なり、Kprobes は kernel 内の functions を trace します。たとえば、`tcp_connect` function を trace して TCP connection information を収集できます。

</details>

13. Cilium に組み込まれている network observability platform の名前は何ですか？

<details>
<summary>解答を見る</summary>

**解答: Hubble**

**解説:**
Hubble は Cilium に組み込まれている network observability platform で、network flows、DNS queries、HTTP requests、policy decisions など、eBPF dataplane からのデータを収集します。Hubble CLI、Hubble UI、Hubble Relay を通じて、cluster の network traffic をリアルタイムで観測できます。

</details>

14. eBPF programs をロードするために必要な Linux capability は何ですか？（kernel 5.8 以降）

<details>
<summary>解答を見る</summary>

**解答: CAP_BPF**

**解説:**
kernel 5.8 以降では、eBPF programs をロードするために `CAP_BPF` capability が必要です。それ以前の version では `CAP_SYS_ADMIN` が必要でした。さらに、performance monitoring events への attach には `CAP_PERFMON`、XDP/TC programs への attach には `CAP_NET_ADMIN` が必要です。

</details>

15. eBPF を使用して container energy consumption を監視する CNCF project の名前は何ですか？

<details>
<summary>解答を見る</summary>

**解答: Kepler (Kubernetes-based Efficient Power Level Exporter)**

**解説:**
Kepler は eBPF を使用して container energy consumption を監視する project です。`kepler_container_joules_total`（container ごとの energy consumption）や `kepler_container_gpu_joules_total`（GPU energy consumption）など、Prometheus format の metrics を提供します。

</details>

## ハンズオン問題

16. bpftool を使用して、system に現在ロードされている eBPF programs を一覧表示し、特定の program の詳細情報を照会する commands を書いてください。

<details>
<summary>解答を見る</summary>

**解答:**
```bash
# List loaded eBPF programs
sudo bpftool prog list

# Query detailed information for a specific program (ID: 123)
sudo bpftool prog show id 123

# Dump program bytecode
sudo bpftool prog dump xlated id 123

# Dump JIT compiled code
sudo bpftool prog dump jited id 123
```

**解説:**
`bpftool prog list` は、現在ロードされているすべての eBPF programs の一覧を表示します。各 program の ID、type、name、attachment location などを確認できます。特定の program の詳細情報を照会するには `bpftool prog show id <ID>` を使用し、bytecode と JIT-compiled native code を表示するには `dump xlated` と `dump jited` を使用します。

</details>

17. system 上のすべての processes から発生する TCP connections をリアルタイムで trace する bpftrace one-liner command を書いてください。

<details>
<summary>解答を見る</summary>

**解答:**
```bash
# TCP connection tracing (Method 1: using kprobe)
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s (PID: %d) connecting...\n", comm, pid); }'

# TCP connection tracing (Method 2: using tracepoint, more detailed info)
sudo bpftrace -e 'tracepoint:tcp:tcp_connect { printf("%s -> %s:%d\n", ntop(args->saddr), ntop(args->daddr), args->dport); }'

# Count TCP connections by process
sudo bpftrace -e 'kprobe:tcp_connect { @[comm] = count(); }'
```

**解説:**
bpftrace は、シンプルな one-liners で system を trace できる DTrace-style high-level tracing language です。`kprobe:tcp_connect` は kernel の `tcp_connect` function が呼び出されたときに trigger されます。`comm` は process name を表し、`pid` は process ID を表します。tracepoints を使用すると、source/destination IP addresses と port information も取得できます。

</details>

18. Hubble CLI を使用して、特定の namespace からの dropped packets のみを観測する command を書いてください。

<details>
<summary>解答を見る</summary>

**解答:**
```bash
# Observe dropped packets in a specific namespace
hubble observe --namespace production --verdict DROPPED

# Observe dropped packets with real-time streaming
hubble observe --namespace production --verdict DROPPED -f

# Output detailed information of dropped packets in JSON format
hubble observe --namespace production --verdict DROPPED -o json

# Observe dropped packets from a specific Pod
hubble observe --from-pod production/frontend --verdict DROPPED
```

**解説:**
Hubble は Cilium に組み込まれた network observability tool です。`--namespace` option は特定の namespace で filter し、`--verdict DROPPED` は dropped packets のみに filter します。`-f` option は real-time streaming を提供し、`-o json` は JSON format output を提供します。dropped packets を分析することで、network policy の問題や configuration errors の診断に役立ちます。

</details>

## 応用問題

19. eBPF が kernel modules に対して持つ 3 つの主な利点を説明し、それぞれが Kubernetes environments で具体的にどのような benefits を提供するかを述べてください。

<details>
<summary>解答を見る</summary>

**解答:**

kernel modules に対する eBPF の主な利点と、Kubernetes environments における benefits:

**1. 安全性（verifier による安全性の保証）**
- **利点**: eBPF verifier は、program をロードする前に無限ループ、memory access violations、uninitialized variables などをチェックし、kernel crashes を防ぎます。
- **Kubernetes における benefit**: CNI plugins（Cilium）や security tools（Tetragon、Falco）を production clusters で安全に実行できます。kernel modules とは異なり、bug があっても system 全体は crash せず、高可用性を維持できます。

**2. Portability（CO-RE による kernel version からの独立性）**
- **利点**: CO-RE (Compile Once, Run Everywhere) と BTF を使用することで、一度コンパイルした eBPF programs をさまざまな kernel versions で実行できます。kernel version ごとの再コンパイルは不要です。
- **Kubernetes における benefit**: 同じ networking/security solutions を、異種混在の node environments（kernel versions が異なる nodes）に展開できます。cluster upgrades や node 追加時の compatibility issues が大幅に減少します。

**3. Dynamic loading（reboot なしでの program の load/unload）**
- **利点**: eBPF programs は system reboot なしで動的に load/unload できます。runtime に機能を追加または変更できます。
- **Kubernetes における benefit**: node restarts なしで network policies、security rules、observability settings を即座に適用できます。Cilium NetworkPolicy や Tetragon TracingPolicy への変更はリアルタイムに反映され、運用を中断せずに security enhancements を実現できます。

**追加の利点:**
- **Performance**: JIT compilation により native code-level performance が提供され、kube-proxy を置き換える際に O(1) service lookup が可能になります。
- **開発難易度**: kernel module development よりも比較的容易で、迅速な feature development と deployment が可能になります。

</details>

20. Kubernetes cluster で eBPF-based security solution（Tetragon または Falco）を使用して containers 内の sensitive file access を検出し、ブロックする approach を設計してください。説明には TracingPolicy または Falco rule の examples を含めてください。

<details>
<summary>解答を見る</summary>

**解答:**

**eBPF-based Sensitive File Access Security Design**

**1. Security Requirements Definition**
- Detection targets: `/etc/shadow`, `/etc/passwd`, `/etc/sudoers`, `/var/run/secrets/` (Kubernetes secrets)
- Response approach: Alert on detection, process termination for severe cases

**2. Tetragon TracingPolicy Implementation**

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: sensitive-file-protection
spec:
  kprobes:
    # Monitor sensitive file opens
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        # Detect and log Kubernetes secret access
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /var/run/secrets/kubernetes.io/
          matchActions:
            - action: Post  # Event logging

        # Block system authentication file access
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/shadow
                - /etc/sudoers
          matchNamespaces:
            - namespace: default
              operator: In
          matchActions:
            - action: Sigkill  # Immediately terminate process
```

**3. Falco Rules Implementation**

```yaml
# /etc/falco/rules.d/sensitive-files.yaml
- rule: Read Kubernetes Secrets
  desc: Detect reading of Kubernetes secret files in containers
  condition: >
    open_read and
    container and
    (fd.name startswith /var/run/secrets/kubernetes.io/ or
     fd.name startswith /etc/shadow or
     fd.name startswith /etc/sudoers) and
    not proc.name in (kubelet, containerd)
  output: >
    Sensitive file access detected
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name namespace=%k8s.ns.name
     pod=%k8s.pod.name)
  priority: WARNING
  tags: [security, filesystem]

- rule: Write to Sensitive System Files
  desc: Detect writing to sensitive system files
  condition: >
    open_write and
    container and
    fd.name in (/etc/passwd, /etc/shadow, /etc/sudoers)
  output: >
    Attempt to modify sensitive file
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name)
  priority: CRITICAL
  tags: [security, filesystem]
```

**4. Deployment and Monitoring**

```bash
# Install Tetragon and apply policy
helm install tetragon cilium/tetragon -n kube-system
kubectl apply -f sensitive-file-protection.yaml

# Monitor events
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon \
  -c export-stdout -f | tetra getevents -o compact

# Install Falco (eBPF driver)
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf

# Check Falco alerts
kubectl logs -n falco -l app.kubernetes.io/name=falco -f
```

**5. Architecture Explanation**

```
┌─────────────────────────────────────────────────┐
│              Kubernetes Cluster                 │
│  ┌─────────────────┐    ┌─────────────────┐    │
│  │   Application   │    │   Application   │    │
│  │      Pod        │    │      Pod        │    │
│  └────────┬────────┘    └────────┬────────┘    │
│           │                      │             │
│  ┌────────▼──────────────────────▼────────┐   │
│  │              eBPF Layer                 │   │
│  │  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ Tetragon    │  │  Falco      │     │   │
│  │  │ TracingPol. │  │  Rules      │     │   │
│  │  └──────┬──────┘  └──────┬──────┘     │   │
│  │         │                 │            │   │
│  │         ▼                 ▼            │   │
│  │   [File Access Event Capture]          │   │
│  └────────────────────────────────────────┘   │
│                      │                         │
│  ┌───────────────────▼───────────────────┐   │
│  │           Security Response            │   │
│  │  • Event logging (Post)               │   │
│  │  • Process termination (Sigkill)      │   │
│  │  • SIEM alert forwarding              │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

この設計では、eBPF の kernel-level visibility を活用し、applications を変更することなく sensitive file access をリアルタイムで検出して対応します。

</details>

---

[学習資料に戻る](../../basics/05-ebpf-fundamentals.md) | [次のクイズ: Container Technology](./03-container-technology-quiz.md)
