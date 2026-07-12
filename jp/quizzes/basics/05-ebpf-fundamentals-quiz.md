# eBPF Fundamentals Quiz

> **サポート対象バージョン**: Linux Kernel 4.18+, Kubernetes 1.25+
> **最終更新**: February 23, 2026

このクイズでは、eBPF (extended Berkeley Packet Filter) の基本概念から Kubernetes 環境での応用まで、全体的な理解を確認します。

## Multiple Choice Questions

1. eBPF verifier がチェックしないものはどれですか？
   - A) 無限ループがないこと
   - B) 範囲外の memory access がないこと
   - C) Program の実行速度
   - D) 未初期化変数の使用がないこと

<details>
<summary>答えを表示</summary>

**答え: C) Program の実行速度**

**解説:**
eBPF verifier は、program の安全性を確保するために、無限ループがないこと (DAG 構造検証)、範囲外の memory access がないこと、未初期化変数の使用がないこと、正しい helper function 呼び出し、program の終了が保証されていることをチェックします。Program の実行速度は verifier の検証項目ではありません。

</details>

2. どの XDP (eXpress Data Path) program の戻り値が、packet を同じ NIC に送り返しますか？
   - A) XDP_DROP
   - B) XDP_PASS
   - C) XDP_TX
   - D) XDP_REDIRECT

<details>
<summary>答えを表示</summary>

**答え: C) XDP_TX**

**解説:**
XDP program の戻り値には、次の意味があります。
- `XDP_DROP`: packet を破棄
- `XDP_PASS`: kernel stack に渡す
- `XDP_TX`: packet を同じ NIC に戻す
- `XDP_REDIRECT`: 別の interface に転送
- `XDP_ABORTED`: error handling

XDP_TX は、受信した network interface に packet を送り返したい場合に使用します。

</details>

3. eBPF Maps の主な役割ではないものはどれですか？
   - A) kernel と user space 間の data 共有
   - B) state の保存
   - C) eBPF programs の compile
   - D) event data の送信

<details>
<summary>答えを表示</summary>

**答え: C) eBPF programs の compile**

**解説:**
eBPF maps は、kernel と user space 間で data を共有し、state を保存するために使われる data structures です。Maps は、event data の送信 (PERF_EVENT_ARRAY, RINGBUF)、key-value storage (HASH)、statistics collection (PERCPU_ARRAY) などに使用されます。eBPF programs の compile は Clang/LLVM が担当するものであり、maps の役割ではありません。

</details>

4. Cilium が kube-proxy を置き換えるときに eBPF が提供する主な利点は何ですか？
   - A) Service 数に比例する O(n) performance
   - B) iptables rule evaluation が必要
   - C) map lookup による O(1) performance
   - D) Netfilter を使用する

<details>
<summary>答えを表示</summary>

**答え: C) map lookup による O(1) performance**

**解説:**
従来の kube-proxy (iptables mode) は、Service 数が増えるにつれて O(n) の performance 低下が発生します。Cilium は eBPF maps を使用して、一定時間の O(1) lookup performance を提供します。これにより、connection establishment time、CPU 使用率、connections per second など、あらゆる面で大幅な performance 改善が得られます。

</details>

5. bpftrace の主な目的は何ですか？
   - A) eBPF programs を C に compile する
   - B) kernel modules を load する
   - C) DTrace-style の high-level tracing
   - D) container images を build する

<details>
<summary>答えを表示</summary>

**答え: C) DTrace-style の high-level tracing**

**解説:**
bpftrace は DTrace-style の high-level tracing language であり、簡単な one-liner command で system を trace できます。たとえば、system calls の count、process ごとの read bytes の tracking、file open の tracing、TCP connections の tracking などの task を簡単に実行できます。

</details>

6. Tetragon の TracingPolicy で、悪意のある file access が検出されたときに process を即座に終了させる action はどれですか？
   - A) action: Block
   - B) action: Sigkill
   - C) action: Deny
   - D) action: Terminate

<details>
<summary>答えを表示</summary>

**答え: B) action: Sigkill**

**解説:**
Tetragon の TracingPolicy では、`matchActions` 内の `action: Sigkill` が、policy に一致する event が発生したときに SIGKILL signal で process を即座に終了させます。これは、sensitive file access や悪意のある network connections を real-time で block するために使用されます。

</details>

7. Hubble の主な feature ではないものはどれですか？
   - A) Network flow の observation
   - B) DNS query の tracking
   - C) eBPF programs の compile
   - D) Policy decision の monitoring

<details>
<summary>答えを表示</summary>

**答え: C) eBPF programs の compile**

**解説:**
Hubble は Cilium に組み込まれた network observability platform であり、network flows、DNS queries、HTTP requests、policy decisions などを収集・監視します。Hubble は observability tool であり、eBPF program の compile 機能は提供しません。

</details>

8. CO-RE (Compile Once, Run Everywhere) はどの問題を解決しますか？
   - A) eBPF program の実行速度の向上
   - B) 異なる kernel versions 間での portability
   - C) memory usage の削減
   - D) network latency の削減

<details>
<summary>答えを表示</summary>

**答え: B) 異なる kernel versions 間での portability**

**解説:**
CO-RE は libbpf と BTF (BPF Type Format) を使用して、一度 compile した eBPF programs をさまざまな kernel versions で実行できるようにします。これにより、kernel header dependencies が減り、struct relocation が自動的に処理されるため、kernel version ごとに再 compile する必要がなくなります。

</details>

9. Falco は eBPF を使用して何を検出しますか？
   - A) Network bandwidth usage
   - B) runtime anomalous behavior
   - C) Disk capacity
   - D) CPU temperature

<details>
<summary>答えを表示</summary>

**答え: B) runtime anomalous behavior**

**解説:**
Falco は、eBPF を使用して runtime anomalous behavior を検出する CNCF project です。rules に基づいて、sensitive files の読み取り、containers 内での shell 実行、privilege escalation attempts などの security threats を検出し、alert を出します。

</details>

10. eBPF programs の stack size limit は何ですか？
    - A) 128 bytes
    - B) 256 bytes
    - C) 512 bytes
    - D) 1024 bytes

<details>
<summary>答えを表示</summary>

**答え: C) 512 bytes**

**解説:**
eBPF programs には 512 byte の stack size limit があります。この制限を回避するには、PERCPU_ARRAY のような maps を使用して、より大きな buffers を allocate する必要があります。この制限は kernel の安全性を確保するために存在します。

</details>

## Short Answer Questions

11. eBPF bytecode を native machine code に変換する compiler の名前は何ですか？

<details>
<summary>答えを表示</summary>

**答え: JIT compiler (Just-In-Time compiler)**

**解説:**
JIT compiler は eBPF bytecode を native machine code に変換します。これにより interpreter と比較して 4〜5 倍の performance improvement が得られ、architecture-specific optimizations が適用されます。`/proc/sys/net/core/bpf_jit_enable` を 1 に設定することで有効化できます。

</details>

12. kernel function calls を動的に trace する eBPF program type の名前は何ですか？

<details>
<summary>答えを表示</summary>

**答え: Kprobes (or Kprobe)**

**解説:**
Kprobes は、kernel function calls を動的に trace する eBPF program type です。user space functions を trace する Uprobes とは異なり、Kprobes は kernel 内の functions を trace します。たとえば、`tcp_connect` function を trace して TCP connection information を収集できます。

</details>

13. Cilium に組み込まれている network observability platform の名前は何ですか？

<details>
<summary>答えを表示</summary>

**答え: Hubble**

**解説:**
Hubble は Cilium に組み込まれた network observability platform であり、network flows、DNS queries、HTTP requests、policy decisions など、eBPF dataplane からの data を収集します。Hubble CLI、Hubble UI、Hubble Relay を通じて、cluster の network traffic を real-time で観測できます。

</details>

14. eBPF programs を load するために必要な Linux capability は何ですか？ (kernel 5.8 以上)

<details>
<summary>答えを表示</summary>

**答え: CAP_BPF**

**解説:**
kernel 5.8 以上では、eBPF programs を load するために `CAP_BPF` capability が必要です。以前の versions では `CAP_SYS_ADMIN` が必要でした。さらに、performance monitoring events への attach には `CAP_PERFMON` が必要で、XDP/TC programs への attach には `CAP_NET_ADMIN` が必要です。

</details>

15. eBPF を使用して container の energy consumption を monitor する CNCF project の名前は何ですか？

<details>
<summary>答えを表示</summary>

**答え: Kepler (Kubernetes-based Efficient Power Level Exporter)**

**解説:**
Kepler は、eBPF を使用して container の energy consumption を monitor する project です。`kepler_container_joules_total` (container ごとの energy consumption) や `kepler_container_gpu_joules_total` (GPU energy consumption) などの metrics を Prometheus format で提供します。

</details>

## Hands-on Questions

16. bpftool を使用して system に現在 load されている eBPF programs を一覧表示し、特定の program に関する詳細情報を query する commands を書いてください。

<details>
<summary>答えを表示</summary>

**答え:**
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
`bpftool prog list` は、現在 load されているすべての eBPF programs の一覧を表示します。各 program の ID、type、name、attachment location などを確認できます。`bpftool prog show id <ID>` を使用すると、特定の program に関する詳細情報を query でき、`dump xlated` と `dump jited` を使用すると、bytecode と JIT-compiled native code を表示できます。

</details>

17. system 上のすべての process から発生する TCP connections を real-time で trace する bpftrace one-liner command を書いてください。

<details>
<summary>答えを表示</summary>

**答え:**
```bash
# TCP connection tracing (Method 1: using kprobe)
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s (PID: %d) connecting...\n", comm, pid); }'

# TCP connection tracing (Method 2: using tracepoint, more detailed info)
sudo bpftrace -e 'tracepoint:tcp:tcp_connect { printf("%s -> %s:%d\n", ntop(args->saddr), ntop(args->daddr), args->dport); }'

# Count TCP connections by process
sudo bpftrace -e 'kprobe:tcp_connect { @[comm] = count(); }'
```

**解説:**
bpftrace は DTrace-style の high-level tracing language であり、簡単な one-liner で system を trace できます。`kprobe:tcp_connect` は、kernel の `tcp_connect` function が呼び出されたときに trigger されます。`comm` は process name を表し、`pid` は process ID を表します。tracepoints を使用すると、source/destination IP addresses と port information も取得できます。

</details>

18. Hubble CLI を使用して、特定の namespace からの dropped packets だけを観測する command を書いてください。

<details>
<summary>答えを表示</summary>

**答え:**
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
Hubble は Cilium に組み込まれた network observability tool です。`--namespace` option は特定の namespace で filter し、`--verdict DROPPED` は dropped packets のみに filter します。`-f` option は real-time streaming を提供し、`-o json` は JSON format output を提供します。dropped packets を分析することで、network policy issues や configuration errors の診断に役立ちます。

</details>

## Advanced Questions

19. eBPF が kernel modules に対して持つ 3 つの主な利点を説明し、それぞれが Kubernetes 環境で具体的にどのような benefit を提供するかを述べてください。

<details>
<summary>答えを表示</summary>

**答え:**

eBPF が kernel modules に対して持つ主な利点と、Kubernetes 環境での benefits は次のとおりです。

**1. Safety (verifier によって保証される安全性)**
- **利点**: eBPF verifier は、program を load する前に無限ループ、memory access violation、未初期化変数などをチェックし、kernel crash を防ぎます。
- **Kubernetes benefit**: CNI plugins (Cilium) や security tools (Tetragon, Falco) を production clusters で安全に実行できます。kernel modules とは異なり、bug があっても system 全体が crash せず、high availability を維持できます。

**2. Portability (CO-RE による kernel version independence)**
- **利点**: CO-RE (Compile Once, Run Everywhere) と BTF を使用することで、一度 compile した eBPF programs をさまざまな kernel versions で実行できます。kernel version ごとに再 compile する必要はありません。
- **Kubernetes benefit**: 同じ networking and security solutions を、異種 node environments (異なる kernel versions を持つ nodes) 全体に deploy できます。cluster upgrade や node addition の際の compatibility issues が大幅に減ります。

**3. Dynamic loading (reboot なしでの program load/unload)**
- **利点**: eBPF programs は system reboot なしで動的に load/unload できます。runtime に functionality を追加または変更できます。
- **Kubernetes benefit**: node restart なしで network policies、security rules、observability settings を即座に適用できます。Cilium NetworkPolicy や Tetragon TracingPolicy への変更が real-time で反映され、operational interruption なしに security enhancements を実現できます。

**Additional advantages:**
- **Performance**: JIT compilation により native code-level performance が得られ、kube-proxy を置き換える際に O(1) service lookup が可能になります。
- **Development difficulty**: kernel module development より比較的容易で、迅速な feature development と deployment が可能です。

</details>

20. Kubernetes cluster で eBPF-based security solution (Tetragon または Falco) を使用して、containers 内の sensitive file access を検出して block する approach を設計してください。説明には TracingPolicy または Falco rule の例を含めてください。

<details>
<summary>答えを表示</summary>

**答え:**

**eBPF-based Sensitive File Access Security Design**

**1. Security Requirements Definition**
- Detection targets: `/etc/shadow`, `/etc/passwd`, `/etc/sudoers`, `/var/run/secrets/` (Kubernetes secrets)
- Response approach: 検出時に alert、深刻な case では process termination

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

この設計では、eBPF の kernel-level visibility を活用して、applications を変更することなく、sensitive file access を real-time で検出し対応します。

</details>

---

[学習資料に戻る](../../basics/05-ebpf-fundamentals.md) | [次のクイズ: Container Technology](./03-container-technology-quiz.md)
