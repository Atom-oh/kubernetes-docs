# Part 6: eBPF Dataplane

> **対応バージョン**: Calico v3.29+ / Kubernetes 1.28+ **最終更新**: February 23, 2026

## はじめに

Calico の eBPF dataplane は Kubernetes networking の大きな進化を表しており、従来の iptables ベースのパケット処理を最新の eBPF program に置き換えます。このアプローチにより、大幅なパフォーマンス向上、レイテンシ削減、強化された observability 機能が実現します。

この詳細解説では、networking の観点から eBPF の基礎、Calico の eBPF architecture、移行戦略、パフォーマンス最適化手法を取り上げます。

***

## eBPF の基礎

### eBPF とは？

eBPF（extended Berkeley Packet Filter）は、Linux kernel source code を変更したり kernel module をロードしたりすることなく、sandbox 化された program を Linux kernel 内で実行できる画期的な技術です。

![eBPF program が user space から libbpf loader、kernel verifier、JIT compiler を経て kernel hook に移動し、検証アプリケーションと BPF map を共有する様子を示す図。](../../../assets/diagrams/rendered/en-networking-calico-06-ebpf-dataplane-0.svg)

### Networking 向けの主要な eBPF 概念

| 概念      | 説明                              | Calico での用途                       |
| ------------ | ---------------------------------------- | ----------------------------------- |
| **Program** | kernel hook で実行される bytecode        | パケット filtering、routing           |
| **Map**     | program 間で共有される key-value store | route table、policy rule          |
| **Hook**    | kernel 内の attachment point              | XDP、TC、socket                     |
| **Helper**  | eBPF から呼び出し可能な kernel function      | パケット操作、map 操作 |
| **BTF**      | map/program の type information       | debug info、CO-RE                   |

### eBPF と iptables

| 観点               | iptables                  | eBPF              |
| -------------------- | ------------------------- | ----------------- |
| **Architecture**     | 順次的な rule chain    | 直接実行  |
| **Complexity**       | O(n) rule matching        | O(1) map lookup   |
| **Kernel Crossings** | パケットごとに複数回       | 最小限           |
| **Programmability**  | 固定された rule type          | 柔軟な program |
| **Observability**    | 限定的な counter          | 豊富な metric      |
| **CPU Efficiency**   | より高い interrupt overhead | より低い overhead    |

***

## Calico eBPF Architecture

![2 つの Calico dataplane を比較する図。iptables mode では、NIC からの packet が PREROUTING、FORWARD、kube-proxy rule、POSTROUTING chain を通って宛先 Pod に到達します。eBPF mode では、TC hook の単一 BPF program が O(1) BPF map lookup を実行し、socket-level の connect-time load balancing に渡して、kube-proxy を介さず Pod に到達します。](../../.gitbook/assets/en-networking-calico-06-ebpf-dataplane-9.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-06-ebpf-dataplane-9.html)

### Architecture の比較

![7 個の順次的な iptables chain を通過する packet と、TC ingress および egress hook 間で BPF map を参照する単一 eBPF program を通過する同じ packet を対比する図。](../../../assets/diagrams/rendered/en-networking-calico-06-ebpf-dataplane-1.svg)

### Calico の eBPF Program Type

Calico は、異なる機能のために複数の eBPF program type を使用します。

![XDP と TC ingress hook が socket-level の sockops および sk_msg program に入力され、TC egress hook に渡される様子を示す図。cgroup scope program は、接続されていない socket-level primitive として示されています。](../../../assets/diagrams/rendered/en-networking-calico-06-ebpf-dataplane-2.svg)

### TC（Traffic Control）Program

TC program は Calico の主要な dataplane hook です。

```
Ingress TC Program Functions:
├── Policy enforcement (allow/deny)
├── Connection tracking lookup
├── Service load balancing (DNAT)
├── Tunnel decapsulation
└── Metrics collection

Egress TC Program Functions:
├── Policy enforcement (egress rules)
├── SNAT for masquerade
├── Tunnel encapsulation
└── DSR return path handling
```

### XDP（eXpress Data Path）Program

XDP は最も早いパケット処理 hook を提供します。

![network card から XDP program に到着した packet が、DDoS protection 用の drop、通常の TC 処理へ pass、直接的な TX return、または別 interface への redirect という 4 つの verdict のいずれかを返す flowchart。](../../../assets/diagrams/rendered/en-networking-calico-06-ebpf-dataplane-3.svg)

### Socket Program

service mesh integration 向けの socket-level eBPF：

```yaml
# sockops: Intercept socket operations
- connect() -> Redirect to local sidecar
- accept() -> Apply connection policies
- close() -> Cleanup connection state

# sk_msg: Process socket data
- sendmsg() -> Apply L7 policy
- recvmsg() -> Inspect response
```

***

## BPF Map Structure

### Calico が使用する Map Type

| Map Type          | 目的              | 使用例         |
| ----------------- | -------------------- | ------------------- |
| **Hash Map**      | Key-value lookup     | connection tracking |
| **LRU Hash**      | 自動退避 cache  | NAT table           |
| **Array**         | 固定サイズの index   | endpoint config     |
| **LPM Trie**      | 最長 prefix match | route lookup        |
| **Per-CPU Array** | 拡張可能な counter    | 統計          |

### Route Map Structure

```c
// Simplified route map entry
struct calico_route_key {
    __be32 prefix;
    __u32 prefix_len;
};

struct calico_route_value {
    __u32 flags;          // LOCAL, REMOTE, HOST, etc.
    __be32 next_hop;      // Next hop IP
    __u32 ifindex;        // Interface index
    __u8 mac[6];          // Destination MAC
};
```

### Connection Tracking Map

```c
// Connection tracking key
struct calico_ct_key {
    __be32 src_ip;
    __be32 dst_ip;
    __be16 src_port;
    __be16 dst_port;
    __u8 protocol;
};

// Connection tracking value
struct calico_ct_value {
    __u64 created;        // Timestamp
    __u64 last_seen;      // Last packet
    __be32 orig_dst;      // Pre-DNAT destination
    __be16 orig_port;     // Pre-DNAT port
    __u32 flags;          // Connection state
};
```

### Policy Map Structure

```c
// Policy rule entry
struct calico_policy_key {
    __u32 policy_id;
    __u32 rule_index;
};

struct calico_policy_value {
    __u32 action;         // ALLOW, DENY, PASS
    __u32 flags;
    __be32 src_net;
    __be32 src_mask;
    __be32 dst_net;
    __be32 dst_mask;
    __be16 port_start;
    __be16 port_end;
};
```

***

## Direct Server Return（DSR）

### DSR の概要

DSR では、response traffic が load balancer を迂回できるため、レイテンシと load balancer のリソース消費を削減できます。

![server response が load balancer を経由して client に戻る通常の load-balanced flow と、response が load balancer を迂回して server から client へ直接送られる Direct Server Return flow を比較する図。](../../../assets/diagrams/rendered/en-networking-calico-06-ebpf-dataplane-4.svg)

### Calico の DSR Mode

| Mode         | 説明              | Use Case                  |
| ------------ | ------------------------ | ------------------------- |
| **Disabled** | すべての traffic が LB を経由   | default、すべての environment |
| **IPIP**     | IPIP tunnel 経由の response | subnet 間              |
| **DSR**      | 直接 response          | 同一 L2 network           |

### DSR の有効化

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  bpfEnabled: true
  bpfExternalServiceMode: DSR
```

### DSR の要件

* Server と client は同じ L2 network 上にある必要があります。または
* subnet 間では IPIP/VXLAN encapsulation を使用します
* external client IP は server から route 可能である必要があります
* ingress path に SNAT がないこと

***

## Connect-Time Load Balancing

### 従来型と Connect-Time LB

![kube-proxy の packet ごとのアプローチ（すべての SYN、data、FIN packet が Pod A に DNAT される）と、eBPF connect-time load balancing（単一の connect() syscall が一度だけ Pod B を選択し、その connection のすべての packet が直接そこに送られる）を対比する図。](../../../assets/diagrams/rendered/en-networking-calico-06-ebpf-dataplane-5.svg)

### Connect-Time LB の利点

| 観点                  | Per-Packet          | Connect-Time          |
| ----------------------- | ------------------- | --------------------- |
| **NAT overhead**        | すべての packet        | connection setup 時のみ |
| **Connection tracking** | 必要            | 最小限               |
| **Latency**             | 高い（NAT lookup） | 低い（direct）        |
| **CPU usage**           | 高い              | 低い                 |

### Connect-Time LB の仕組み

```c
// Simplified connect-time LB logic
int bpf_connect4(struct bpf_sock_addr *ctx) {
    // Check if destination is a Service IP
    struct lb_backend *backend = lookup_service(ctx->user_ip4, ctx->user_port);

    if (backend) {
        // Rewrite destination to backend pod
        ctx->user_ip4 = backend->pod_ip;
        ctx->user_port = backend->pod_port;
    }

    return 1; // Allow connection
}
```

***

## XDP Acceleration

### XDP Processing Level

![NIC に offload された XDP program が最速であり、driver 内で native に実行される program は高速、generic network stack で実行される program は最も低速ですが任意の NIC で動作することを示す図。](../../../assets/diagrams/rendered/en-networking-calico-06-ebpf-dataplane-6.svg)

### XDP Mode

| Mode        | 場所      | Performance | 要件   |
| ----------- | ------------- | ----------- | -------------- |
| **Offload** | NIC hardware  | 最速     | SmartNIC       |
| **Native**  | NIC driver    | 高速        | driver support |
| **Generic** | Network stack | 基準値    | 任意の NIC        |

### Calico で XDP を有効にする

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  bpfEnabled: true

  # XDP mode: Disabled, Enabled, Offload
  xdpEnabled: Enabled

  # Interfaces for XDP
  # Uses same detection as BPF dataplane interface
```

### Calico における XDP Use Case

1. **DDoS Protection**: NIC で malicious traffic を drop
2. **Blocklist Enforcement**: block された IP を早期に拒否
3. **Rate Limiting**: stack より前で packet rate を制限
4. **Metrics Collection**: wire-speed での packet counting

***

## eBPF Mode の要件

### Kernel の要件

| 要件      | Minimum Version | 注記                     |
| ---------------- | --------------- | ------------------------- |
| **Linux Kernel** | 5.3+            | 5.8+ を推奨          |
| **BTF Support**  | 必須        | `CONFIG_DEBUG_INFO_BTF=y` |
| **BPF Syscall**  | 必須        | `CONFIG_BPF_SYSCALL=y`    |
| **BPF JIT**      | 必須        | `CONFIG_BPF_JIT=y`        |

### Kernel Support の確認

```bash
# Check kernel version
uname -r

# Check BTF support
ls /sys/kernel/btf/vmlinux

# Check BPF support
cat /boot/config-$(uname -r) | grep -E "CONFIG_BPF|CONFIG_DEBUG_INFO_BTF"

# Required output:
# CONFIG_BPF=y
# CONFIG_BPF_SYSCALL=y
# CONFIG_BPF_JIT=y
# CONFIG_DEBUG_INFO_BTF=y
```

### Distribution Support

| Distribution      | eBPF 対応 | 注記                        |
| ----------------- | ---------- | ---------------------------- |
| Ubuntu 20.04+     | はい        | Kernel 5.4+                  |
| Ubuntu 22.04+     | はい        | Kernel 5.15+（推奨）   |
| RHEL/CentOS 8.2+  | はい        | backport 付き Kernel 4.18+  |
| Amazon Linux 2    | 部分的    | kernel upgrade が必要な場合あり      |
| Amazon Linux 2023 | はい        | Kernel 6.1+                  |
| Bottlerocket      | はい        | container 専用に構築 |

### Calico Version の要件

```yaml
# Minimum Calico versions for eBPF features
eBPF dataplane basic:     v3.13.0
Connect-time LB:          v3.16.0
XDP acceleration:         v3.18.0
Dual-stack eBPF:         v3.20.0
Host-networked pods:      v3.13.0 (with limitations)
```

### Node Configuration

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Enable eBPF dataplane
  bpfEnabled: true

  # Data interface detection
  # Auto-detect: first interface with default route
  # Or specify pattern: "eth*"
  bpfDataIfacePattern: "^((en|eth|wl)[opsx].*|(eth|wlan|eno)[0-9].*)"

  # External service mode: Tunnel or DSR
  bpfExternalServiceMode: Tunnel

  # Log level for BPF programs
  bpfLogLevel: Info

  # Kube-proxy replacement
  bpfKubeProxyIptablesCleanupEnabled: true

  # Connection tracking
  bpfConnectTimeLoadBalancingEnabled: true
```

***

## iptables から eBPF への移行

### 移行前チェックリスト

```bash
# 1. Verify kernel requirements
uname -r  # Should be 5.3+
ls /sys/kernel/btf/vmlinux  # BTF must exist

# 2. Check Calico version
kubectl get deployment -n kube-system calico-kube-controllers -o jsonpath='{.spec.template.spec.containers[0].image}'
# Should be v3.13.0+

# 3. Verify CNI plugin
kubectl get ds -n kube-system calico-node -o jsonpath='{.spec.template.spec.containers[0].env}' | grep -i cni

# 4. Check existing networking mode
calicoctl get felixconfiguration default -o yaml | grep -i bpf

# 5. Verify no conflicting CNI
ls /etc/cni/net.d/
```

### 移行手順

**ステップ 1: FelixConfiguration を更新（dry-run）**

```yaml
# Save current configuration
kubectl get felixconfiguration default -o yaml > felix-backup.yaml

# Create eBPF configuration
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  bpfEnabled: false  # Not enabled yet
  bpfLogLevel: Debug  # For troubleshooting
  bpfDataIfacePattern: "^((en|eth|wl)[opsx].*|(eth|wlan|eno)[0-9].*)"
  bpfExternalServiceMode: Tunnel
  bpfKubeProxyIptablesCleanupEnabled: false  # Don't cleanup yet
```

**ステップ 2: kube-proxy を無効化（Calico を replacement として使用する場合）**

```bash
# Option A: Scale down kube-proxy
kubectl -n kube-system patch daemonset kube-proxy -p '{"spec":{"template":{"spec":{"nodeSelector":{"non-calico":"true"}}}}}'

# Option B: Add calico node selector to skip kube-proxy nodes
# Only if running both temporarily
```

**ステップ 3: test node で eBPF を有効化**

```bash
# Label test node
kubectl label node test-node-1 calico-ebpf=enabled

# Apply node-specific config
calicoctl apply -f - <<EOF
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: node.test-node-1
spec:
  bpfEnabled: true
EOF
```

**ステップ 4: test node を検証**

```bash
# Check BPF programs loaded
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  bpftool prog list

# Verify connectivity
kubectl run test-pod --image=busybox --restart=Never --overrides='{"spec":{"nodeName":"test-node-1"}}' -- sleep 3600
kubectl exec test-pod -- wget -O- http://kubernetes.default.svc

# Check logs
kubectl logs -n kube-system -l k8s-app=calico-node -c calico-node | grep -i bpf
```

**ステップ 5: すべての node に rollout**

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  bpfEnabled: true
  bpfLogLevel: Info
  bpfDataIfacePattern: "^((en|eth|wl)[opsx].*|(eth|wlan|eno)[0-9].*)"
  bpfExternalServiceMode: Tunnel
  bpfKubeProxyIptablesCleanupEnabled: true
  bpfConnectTimeLoadBalancingEnabled: true
```

**ステップ 6: iptables rule を cleanup**

```bash
# After confirming eBPF is working
calicoctl patch felixconfiguration default -p '{"spec":{"bpfKubeProxyIptablesCleanupEnabled":true}}'

# Verify iptables rules are minimal
iptables -L -n | wc -l  # Should be significantly reduced
```

### Rollback 手順

```bash
# Disable eBPF
calicoctl patch felixconfiguration default -p '{"spec":{"bpfEnabled":false}}'

# Restore kube-proxy if disabled
kubectl -n kube-system patch daemonset kube-proxy -p '{"spec":{"template":{"spec":{"nodeSelector":null}}}}'

# Wait for calico-node restart
kubectl rollout status ds/calico-node -n kube-system

# Verify iptables rules restored
iptables -L -n -v
```

***

## Performance Benchmark

### Latency の比較

| Scenario                | iptables | eBPF  | 改善率 |
| ----------------------- | -------- | ----- | ----------- |
| Pod-to-Pod（同じ node）  | 45 μs    | 25 μs | 44%         |
| Pod-to-Pod（node 間） | 120 μs   | 80 μs | 33%         |
| Service（ClusterIP）     | 150 μs   | 60 μs | 60%         |
| Service（NodePort）      | 180 μs   | 70 μs | 61%         |

### Throughput の比較

| Scenario            | iptables | eBPF    | 改善率 |
| ------------------- | -------- | ------- | ----------- |
| TCP single stream   | 15 Gbps  | 23 Gbps | 53%         |
| TCP multi-stream    | 35 Gbps  | 48 Gbps | 37%         |
| UDP single stream   | 8 Gbps   | 18 Gbps | 125%        |
| Small packet（64B） | 2M pps   | 5M pps  | 150%        |

### CPU Efficiency

```
Connection rate test (connections/sec):

iptables dataplane:
├── 1000 rules: 50,000 conn/s
├── 5000 rules: 35,000 conn/s
└── 10000 rules: 20,000 conn/s

eBPF dataplane:
├── 1000 rules: 120,000 conn/s
├── 5000 rules: 115,000 conn/s
└── 10000 rules: 110,000 conn/s

Note: eBPF performance remains nearly constant regardless of rule count
```

### 独自 Benchmark の実行

```bash
# Install netperf
apt-get install netperf

# Pod-to-Pod latency (TCP_RR)
kubectl exec client-pod -- netperf -H server-pod-ip -t TCP_RR -l 30

# Throughput (TCP_STREAM)
kubectl exec client-pod -- netperf -H server-pod-ip -t TCP_STREAM -l 30

# Service latency
kubectl exec client-pod -- netperf -H service-cluster-ip -t TCP_RR -l 30

# Compare with iperf3
kubectl exec client-pod -- iperf3 -c server-pod-ip -t 30
```

***

## eBPF Debugging

### bpftool Command

```bash
# List loaded BPF programs
bpftool prog list

# Show program details
bpftool prog show id 123

# Dump program instructions
bpftool prog dump xlated id 123

# List BPF maps
bpftool map list

# Dump map contents
bpftool map dump id 456

# Show map entries
bpftool map lookup id 456 key 0x0a 0x00 0x01 0x0a
```

### TC Filter Inspection

```bash
# Show TC filters on interface
tc filter show dev eth0 ingress
tc filter show dev eth0 egress

# Show BPF program attached to TC
tc filter show dev eth0 ingress | grep bpf

# Detailed filter info
tc -s filter show dev eth0 ingress
```

### Calico BPF Debugging

```bash
# Enable debug logging
calicoctl patch felixconfiguration default -p '{"spec":{"bpfLogLevel":"Debug"}}'

# View BPF debug logs
kubectl logs -n kube-system -l k8s-app=calico-node -c calico-node | grep -i "bpf\|ebpf"

# Check BPF map contents via calico-node
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf conntrack dump

# Show routes in BPF map
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf routes dump

# Show NAT entries
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf nat dump
```

### 一般的な Debug Scenario

**Connectivity Issue：**

```bash
# Check if BPF programs are loaded
bpftool prog list | grep calico

# Verify route is in BPF map
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf routes dump | grep "10.244.1.5"

# Check conntrack entries
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf conntrack dump | grep "10.244.1.5"

# Verify policy is allowing traffic
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf policy dump
```

**Service Load Balancing Issue：**

```bash
# Check service backends in NAT map
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf nat dump | grep "10.96.0.1"

# Verify frontend entry exists
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf nat frontend list
```

***

## 制限事項と既知の問題

### 現在の制限事項

| 制限事項              | 説明            | Workaround                      |
| ----------------------- | ---------------------- | ------------------------------- |
| **Host-networked pod** | 限定的な policy support | host pod には iptables を使用      |
| **IPv6**                | 部分的な support        | dual-stack mode を使用             |
| **Wireguard**           | eBPF とは併用不可          | IPsec を使用するか encryption を無効化 |
| **Service topology**    | 限定的な support        | 標準の kube-proxy を使用         |
| **Windows node**       | 未対応          | iptables dataplane を使用          |

### 既知の問題

```yaml
# Issue: BPF program fails to load
# Cause: Kernel too old or BTF missing
# Solution: Upgrade kernel or enable BTF

# Issue: Services not accessible
# Cause: kube-proxy and Calico BPF conflict
# Solution: Fully disable kube-proxy

# Issue: NodePort not working
# Cause: DSR mode with non-routable client IPs
# Solution: Use Tunnel mode instead of DSR

# Issue: High memory usage
# Cause: Large conntrack table
# Solution: Tune conntrack limits
```

### 問題の確認

```bash
# Check for BPF verifier errors
dmesg | grep -i "bpf\|verifier"

# Check Felix logs for BPF errors
kubectl logs -n kube-system -l k8s-app=calico-node -c calico-node | grep -i error

# Verify BPF map limits
cat /proc/sys/kernel/bpf_map_max_entries
```

***

## Kube-proxy Replacement

### Kube-proxy の完全な Replacement

Calico eBPF は、Service load balancing で kube-proxy を完全に置き換えられます。

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  bpfEnabled: true
  bpfKubeProxyIptablesCleanupEnabled: true
  bpfKubeProxyMinSyncPeriod: 1s

  # Disable kube-proxy IPVS/iptables cleanup
  # (Calico will manage service rules)
```

### kube-proxy を無効化する

```bash
# Method 1: Scale to zero
kubectl -n kube-system scale deployment kube-proxy --replicas=0

# Method 2: Delete DaemonSet
kubectl -n kube-system delete ds kube-proxy

# Method 3: Prevent scheduling (reversible)
kubectl -n kube-system patch ds kube-proxy -p '{"spec":{"template":{"spec":{"nodeSelector":{"non-calico":"true"}}}}}'
```

### Replacement の検証

```bash
# Check no kube-proxy rules in iptables
iptables -t nat -L KUBE-SERVICES 2>/dev/null | wc -l
# Should be 0 or minimal

# Verify Calico is handling services
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-bpf nat frontend list

# Test service connectivity
kubectl run test --image=busybox --rm -it -- wget -O- http://kubernetes.default.svc
```

### Service Feature の比較

| Feature         | kube-proxy (iptables) | kube-proxy (IPVS) | Calico eBPF |
| --------------- | --------------------- | ----------------- | ----------- |
| ClusterIP       | はい                   | はい               | はい         |
| NodePort        | はい                   | はい               | はい         |
| LoadBalancer    | はい                   | はい               | はい         |
| ExternalIPs     | はい                   | はい               | はい         |
| SessionAffinity | はい                   | はい               | はい         |
| Topology        | はい                   | はい               | 限定的     |
| ProxyMode       | iptables              | IPVS              | eBPF        |

***

## ベストプラクティス

### Deployment の推奨事項

1. eBPF を有効化する前に **kernel の要件を確認** する
2. 最初に **non-production** cluster でテストする
3. node selector を使用して **段階的に有効化** する
4. rollout 中に **パフォーマンスを monitor** する
5. **rollback plan** を準備しておく

### Configuration のベストプラクティス

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Production settings
  bpfEnabled: true
  bpfLogLevel: Warn  # Reduce logging in production

  # Interface detection
  bpfDataIfacePattern: "^((en|eth)[0-9]+)"

  # Service mode based on topology
  bpfExternalServiceMode: Tunnel  # Safe default

  # Connection tracking
  bpfConnectTimeLoadBalancingEnabled: true

  # Cleanup legacy rules
  bpfKubeProxyIptablesCleanupEnabled: true
```

### eBPF Dataplane の Monitoring

```yaml
# Prometheus metrics to monitor
calico_bpf_num_maps                    # Number of BPF maps
calico_bpf_map_size_bytes              # Size of each map
calico_bpf_conntrack_entries           # Active connections
calico_bpf_nat_frontend_entries        # Service frontends
calico_bpf_nat_backend_entries         # Service backends
felix_bpf_dataplane_apply_time_seconds # Dataplane sync time
```

***

## まとめ

Calico の eBPF dataplane は、Kubernetes networking における大きな進歩です。

| 利点           | 影響                      |
| ----------------- | --------------------------- |
| **Performance**   | レイテンシを最大 60% 削減 |
| **Scalability**   | O(n) ではなく O(1) の rule lookup    |
| **Efficiency**    | より低い CPU usage             |
| **Observability** | 豊富な BPF ベースの metric      |
| **Simplicity**    | kube-proxy を置き換え         |

### eBPF Dataplane を使用する場合

* 高 throughput の workload
* latency-sensitive application
* 多数の Service を持つ大規模 cluster
* 詳細な observability が必要な environment
* Linux kernel 5.3+ が利用可能

### iptables を継続して使用する場合

* Windows node support が必要
* 古い kernel version
* Wireguard encryption が必要
* 複雑な Service topology の要件
* 実績のある技術を必要とする risk-averse な environment

***

## 参考資料

* [Calico eBPF Documentation](https://docs.tigera.io/calico/latest/operations/ebpf/)
* [Linux eBPF Documentation](https://ebpf.io/what-is-ebpf/)
* [BPF and XDP Reference Guide](https://docs.cilium.io/en/stable/bpf/)
* [Calico eBPF Migration Guide](https://docs.tigera.io/calico/latest/operations/ebpf/enabling-ebpf)
* [bpftool Manual](https://man7.org/linux/man-pages/man8/bpftool.8.html)
