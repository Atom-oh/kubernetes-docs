# Pod Network Benchmark — Same Node, Same AZ, Cross-AZ, and DNS ndots

> **Recorded test environment**: Kubernetes 1.36 (Amazon EKS), Amazon VPC CNI v1.21.1, kube-proxy iptables mode
> **Measurement date**: September 2, 2026 · **Content review**: September 12, 2026

This page preserves the September 2, 2026 benchmark report from `fsi-demo-cluster` (Seoul): Pod-to-Pod RTT, HTTP/gRPC latency, iperf3 throughput and DNS query counts. In these runs, crossing an AZ increased latency while the two inter-node paths reached similar throughput. That does not establish an AZ-independent bandwidth guarantee. Application traffic in Measurements 1–2 used Pod IPs directly; Measurement 3 models its cost, while Measurement 4 used the existing `kube-dns` ClusterIP. The reported 10-query DNS walk depends on this resolver, search list and response sequence, rather than applying to every EKS Pod. Historical versions and measurements are retained; the audit did not rerun the EKS benchmark or verify a billing invoice.

![Client Pod on node A (ap-northeast-2a) reaching a server Pod on the same node, on node B in the same AZ and on node C in ap-northeast-2b — RTT 0.040 / 0.339 / 0.544 ms, single flow 29.97 / 4.96 / 4.96 Gbps.](../.gitbook/assets/en-networking-06-pod-network-benchmark-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-0.html)

The diagram records this test topology. Its +0.21 ms is a difference between these runs, and its $4.47 is the historical decimal-GB cost model explained below, not a verified charge or a universal per-AZ cost.

## TL;DR — What we measured

1. **Reported RTT**: same node **0.040 ms** → same AZ **0.339 ms** → cross-AZ **0.544 ms** (ping, average of 200 probes). The observed differences are +0.21 ms between the two inter-node paths and +0.50 ms relative to the same node.
2. **HTTP p50 / p99** (fortio, 100 qps, 4 connections, keepalive, 60 s): 0.259 / 0.350 ms → 0.461 / 0.667 ms → 0.704 / 0.812 ms — the same ladder seen from the application.
3. **Reported bandwidth**: one TCP flow reached **4.96 Gbps** on both inter-node paths; eight flows reached **9.94 Gbps**, near the m5.xlarge 10 Gbps burst peak. This is consistent with the ordinary 5 Gbps single-flow limit outside a cluster placement group; other instance features and paths can have different limits.
4. **Same-node Pod to Pod**: **29.97 Gbps** with one flow (client process CPU 99.8 %, consistent with CPU pressure) and **48.15 Gbps** with eight. In this VPC CNI configuration, traffic traverses the Pods’ veth pairs and host network stack without using the physical NIC.
5. **Cost model**: the 180 s cross-AZ run sent **223.4 decimal GB**. The original payload-based model estimates **$4.47** at $0.01/GB at each end; it is not an invoice. No step-down toward the 1.25 Gbps baseline was observed within 180 s.
6. **Reported DNS**: this glibc Pod resolving `sts.ap-northeast-2.amazonaws.com` under `ndots:5` sent **10 queries** (8 NXDOMAIN), warm median **3.78 ms**. A trailing dot gave **2 queries** / 0.80 ms; `ndots:1` gave 2 / 0.54 ms. These timings are samples, not guarantees.
7. **New connections**: disabling keepalive changed p50 from 0.259 → 0.664, 0.461 → 1.079 and 0.704 → **1.517 ms**. TCP establishment contributes to this increase, but the test did not isolate handshake, socket and application costs.

## Test environment

| Item | Value |
|---|---|
| Cluster | Amazon EKS `fsi-demo-cluster`, ap-northeast-2 (Seoul), control plane `v1.36.2-eks-bca9cf6`, two AZs used (2a, 2b) |
| Nodes | **3 × m5.xlarge** launched fresh by the Karpenter `system` NodePool for this test — a client node in 2a, a server node in 2a, a server node in 2b. 4 vCPU, Intel Xeon Platinum 8175M @ 2.50GHz |
| Node OS | Amazon Linux 2023.12.20260817, kernel `6.18.41-94.142.amzn2023.x86_64`, containerd 2.2.5, kubelet v1.36.3-eks-cb19647 |
| CNI | Amazon VPC CNI `v1.21.1-eksbuild.8` (+ network-policy-agent v1.3.4); `ENABLE_PREFIX_DELEGATION=false`, `ENABLE_POD_ENI=false`, `AWS_VPC_K8S_CNI_EXTERNALSNAT=false`, `NETWORK_POLICY_ENFORCING_MODE=standard`, `WARM_ENI_TARGET=1`, `WARM_IP_TARGET=3` |
| kube-proxy | `v1.35.3-eksbuild.5`, `mode: "iptables"` |
| CoreDNS | `v1.14.2-eksbuild.4`, 2 replicas — one per AZ (`10.0.2.106` / 2a, `10.0.3.14` / 2b); Service `kube-dns` ClusterIP `172.20.0.10`; Corefile `kubernetes cluster.local … { pods insecure }`, `forward . /etc/resolv.conf`, `cache 30`, `loadbalance`; **no NodeLocal DNSCache**, no `autopath` plugin |
| Pod resolv.conf (default) | `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` / `nameserver 172.20.0.10` / `options ndots:5` |
| Pod NIC | eth0 MTU **9001** (jumbo frames), TCP congestion control `cubic`, iperf3 `tcp_mss_default: 8949` |
| EC2 network spec | m5.xlarge "Up to 10 Gigabit" — baseline **1.25 Gbps**, peak **10 Gbps**, 4 vCPU (for comparison: m5.large baseline 0.75 Gbps, peak 10 Gbps, 2 vCPU). Verified with `aws ec2 describe-instance-types`; ENA required |
| Pricing | usagetype `APN2-DataTransfer-Regional-Bytes`, "Regional Data Transfer - in/out/between AZs or when using public IP or Elastic IP addresses", **$0.01/GB** (`aws pricing get-products --region us-east-1`, queried 2026-09) |
| Tools | `nicolaka/netshoot:v0.14` — iperf **3.19**, fortio **1.69.5**, iputils ping 20250605, tcpdump 4.99.5; DNS client `python:3.12-slim` (Debian 13, **glibc 2.41**, Python 3.12.14) |
| Test window | 2026-09-02 07:58–08:40 UTC (first Pod at 07:58:22Z, DNS Pods at 08:16:24Z) |

AWS describes burst bandwidth as best effort even while network I/O credits remain; incoming and outgoing traffic have separate credit buckets. A new instance starts with maximum credits, but peak availability and burst duration vary. This 180 s run establishes only that no baseline step-down was observed during its window. The recorded m5.xlarge 1.25 Gbps baseline / 10 Gbps peak also appear in the official [M5 network specifications](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html); current credit behavior is described in the [EC2 bandwidth guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html).

Fixture placement during the run:

| Pod | IP | Node | Zone | Role / requests |
|---|---|---|---|---|
| `cli` | 10.0.2.109 | ip-10-0-2-128 (nodeclaim `system-76r87`) | ap-northeast-2a | client; 2500m / 1Gi |
| `srv-same` | 10.0.2.72 | ip-10-0-2-128 — same node as `cli` (required podAffinity) | ap-northeast-2a | server; 200m / 256Mi |
| `srv-a` | 10.0.2.37 | ip-10-0-2-20 (nodeclaim `system-ksrbg`, podAntiAffinity to `cli`) | ap-northeast-2a | server; 2800m / 1Gi |
| `srv-b` | 10.0.3.65 | ip-10-0-3-32 (nodeclaim `system-svdvk`) | ap-northeast-2b | server; 2500m / 1Gi |
| `dns-default` | 10.0.2.5 | ip-10-0-2-20 (podAffinity to `srv-a`) | ap-northeast-2a | glibc resolver, default `ndots:5` |
| `dns-ndots1` | 10.0.2.143 | ip-10-0-2-20 | ap-northeast-2a | glibc resolver, `dnsConfig.options ndots=1` |

The server Pods run `sh -c "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"`, and every bench Pod carries `karpenter.sh/do-not-disrupt: "true"`. `srv-a` was first requested as m5.large / 1500m, but Karpenter reported `no instance type has enough resources` — DaemonSet overhead takes 821m of an m5.large's 1930m allocatable — so it was changed to m5.xlarge / 2800m.

### Fixture manifest

The following is the recorded fixture, with its historical selectors, requests, images, commands and annotations preserved. It contains no application Service objects. Its selectors do not themselves guarantee new or isolated nodes. Before a new run, adapt a copy to an approved test NodePool, available AZs and resource budget; do not deploy it blindly to a shared `system` pool. Record image digests and tool versions: mutable image tags and netshoot’s build-time tool downloads do not guarantee the original binaries. The revised procedure below is separate from this historical artifact.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-net
  labels:
    bench: net
---
# client — fresh m5.xlarge in ap-northeast-2a
apiVersion: v1
kind: Pod
metadata:
  name: cli
  namespace: bench-net
  labels: { app: cli, role: client }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
---
# same-node — co-located with cli through required podAffinity
apiVersion: v1
kind: Pod
metadata:
  name: srv-same
  namespace: bench-net
  labels: { app: srv-same, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "200m", memory: "256Mi" }
---
# same-AZ — same AZ as cli, different node (podAntiAffinity). m5.large did not fit because of DaemonSet overhead, hence m5.xlarge
apiVersion: v1
kind: Pod
metadata:
  name: srv-a
  namespace: bench-net
  labels: { app: srv-a, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2800m", memory: "1Gi" }
---
# cross-AZ — fresh m5.xlarge in ap-northeast-2b
apiVersion: v1
kind: Pod
metadata:
  name: srv-b
  namespace: bench-net
  labels: { app: srv-b, role: server, zone: b }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2b
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
```

The two DNS Pods were reported on the same node as `srv-a`. The `app` image was reported as Debian 13 / glibc 2.41; musl and other resolvers were not measured. `sniffer` shares its Pod network namespace, so it can capture matching application DNS packets if the cluster permits packet capture. To produce both DNS objects from the example below, duplicate it: change the second name and `app` label to `dns-ndots1` and uncomment `dnsConfig` only in that second object. Keep both images identical and pin their recorded digests in a new run.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-default          # the second Pod is name: dns-ndots1 plus the dnsConfig block below
  namespace: bench-net
  labels: { app: dns-default, role: dns }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: srv-a } }
          topologyKey: kubernetes.io/hostname
  # present only in dns-ndots1:
  # dnsConfig:
  #   options:
  #     - name: ndots
  #       value: "1"
  terminationGracePeriodSeconds: 5
  containers:
    - name: app
      image: python:3.12-slim
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
    - name: sniffer
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
```

## Measurement 1 — RTT and HTTP latency: same node → same AZ → cross-AZ

ICMP probes (`ping -c 200 -i 0.05 -q`) characterize the idle path, including endpoint kernel processing and scheduling. The same paths were then exercised with HTTP/1.1 and gRPC. A single fresh-connection `curl` connect / total time is listed for reference.

| Path | RTT min / **avg** / max / mdev (ms) | Loss | curl, 1 cold request: connect / total |
|---|---|---|---|
| same node → 10.0.2.72 | 0.021 / **0.040** / 0.089 / 0.007 | 0/200 | 0.194 ms / 0.497 ms |
| same AZ → 10.0.2.37 | 0.300 / **0.339** / 0.450 / 0.017 | 0/200 | 0.497 ms / 2.333 ms |
| cross-AZ → 10.0.3.65 | 0.504 / **0.544** / 0.625 / 0.015 | 0/200 | 0.694 ms / 4.038 ms |

Observed differences: same AZ − same node = +0.30 ms, cross-AZ − same AZ = **+0.21 ms**, cross-AZ − same node = +0.50 ms. The reported mdev values are at most 0.017 ms in this sample. curl’s `time_total` measures the transfer operation, not process startup; a single observation is insufficient to characterize its distribution. See the [curl timing definitions](https://curl.se/docs/manpage.html).

### HTTP/1.1 — 100 qps, 4 connections, keepalive, 60 s (6,000 requests), ms

| Path | avg | **p50** | p90 | p99 | p99.9 | max | min |
|---|---|---|---|---|---|---|---|
| same node | 0.260 | **0.259** | 0.299 | 0.350 | 1.267 | 2.080 | 0.111 |
| same AZ | 0.468 | **0.461** | 0.560 | 0.667 | 0.783 | 2.823 | 0.336 |
| cross-AZ | 0.706 | **0.704** | 0.782 | 0.812 | 1.150 | 4.581 | 0.551 |

### gRPC ping — 100 qps, 4 connections, 30 s (3,000 requests), ms

| Path | avg | **p50** | p90 | p99 | p99.9 | max | min |
|---|---|---|---|---|---|---|---|
| same node | 0.410 | **0.397** | 0.449 | 0.869 | 1.187 | 1.314 | 0.241 |
| same AZ | 0.601 | **0.592** | 0.687 | 0.889 | 1.052 | 1.105 | 0.448 |
| cross-AZ | 0.878 | **0.865** | 0.967 | 1.209 | 2.582 | 2.826 | 0.692 |

The report describes an approximately 75-byte HTTP echo body with an empty request payload and zero errors in all runs. Check each protocol’s result counters separately: HTTP status 200, gRPC Ping results and gRPC health-check `SERVING` are different responses; `-grpc -ping` selects Ping rather than the default health-check workload.

**How to read it.** HTTP p50 exceeds the ping mean by roughly 0.22 / 0.12 / 0.16 ms, but subtracting different statistics from different protocols does not isolate user-space overhead. The observed HTTP p50 steps are +0.202 ms and +0.243 ms; they are not constant per-node or per-AZ costs. gRPC p50 exceeds HTTP p50 by 0.138 / 0.131 / 0.161 ms in these implementations, without proving how much comes from HTTP/2, serialization, scheduling or client/server code. HTTP p99 is 0.350 → 0.667 → 0.812 ms; gRPC p99.9 is 1.187 → 1.052 → **2.582 ms**. These are reported distributions for one run per cell.

> **Comparison with the mesh benchmark.** The [Istio sidecar vs ambient report](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) records a **+1.29 ms** p50 difference (2.11 − 0.82 ms) for its whole sidecar scenario, not an isolated single proxy. Its Graviton hardware, 200 qps, 16 connections and Fortio 1.69.4 differ from this M5 / 100 qps / four-connection test. The numbers cannot be added or ranked as universal “mesh hop” versus “AZ hop” costs.

### The cost of a new connection — keepalive=false, 100 qps, 4 connections, 30 s (3,000 requests), ms

What happens to latency when every request opens a fresh TCP connection (fortio `-keepalive=false`)?

| Path | avg | **p50** | p90 | p99 | p99.9 | max | min | vs keepalive p50 |
|---|---|---|---|---|---|---|---|---|
| same node | 0.672 | **0.664** | 0.782 | 0.957 | 1.253 | 1.306 | 0.364 | **+0.405 ms** |
| same AZ | 1.066 | **1.079** | 1.185 | 1.369 | 1.582 | 1.795 | 0.769 | **+0.618 ms** |
| cross-AZ | 1.530 | **1.517** | 1.678 | 1.796 | 1.981 | 2.009 | 1.300 | **+0.813 ms** |

The observed increases are **+0.405 / +0.618 / +0.813 ms**. A new TCP connection adds establishment work, but these measurements do not prove a fixed “one RTT + 0.3 ms” decomposition. Connection reuse is a useful optimization to measure with the real workload; it is not a prerequisite for correctness across AZs. Connection churn can also increase TIME_WAIT state on the active-closing endpoint, depending on how connections close; sockets and TIME_WAIT were not measured here.

### Maximum qps from a fixed connection pool — latency is throughput (closed loop, 16 connections, 20 s)

With `-qps 0` (unlimited, closed loop), the maximum request rate that 16 connections can sustain turns the latency difference into a throughput difference.

| Path | Requests | **Achieved qps** | avg ms | p50 | p90 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|
| same node | 899,827 | **44,991** | 0.355 | 0.249 | 0.733 | 1.695 | 3.389 | 13.593 |
| same AZ | 770,156 | **38,507** | 0.415 | 0.396 | 0.537 | 0.728 | 1.147 | 4.502 |
| cross-AZ | 512,060 | **25,602** | 0.624 | 0.597 | 0.770 | 0.949 | 1.293 | 4.725 |

For a steady closed loop with about 16 requests in flight and little client think time, Little’s law gives throughput ≈ concurrency / mean latency: 16 / 0.000355 = 45,070 (reported 44,991), 16 / 0.000415 = 38,554 (38,507), and 16 / 0.000624 = 25,641 (25,602). The reported cross-AZ rate is **33.5 % lower** than same-AZ in this test. This relationship does not identify the exclusive cause of latency or predict a universal AZ penalty. Shared CPU contention is a plausible explanation for the worse same-node tail, but no profiling here establishes that cause.

## Measurement 2 — Throughput: the 5 Gbps single-flow cap and the 10 Gbps instance cap

iperf3 3.19, TCP, 20 s per run, `-J`, client `cli`. The CPU columns are iperf3's own per-process figures, where 100 % = one vCPU.

| Path | Flows (-P) | Send Gbps | Recv Gbps | Retransmits | Bytes sent | Client CPU | Server CPU | Sender TCP mean RTT (stream 1) | max snd_cwnd |
|---|---|---|---|---|---|---|---|---|---|
| same node (cli→srv-same) | 1 | **29.97** | 29.97 | 13 | 74,921,541,632 | **99.8 %** | 80.9 % | 34 µs | 1,861,392 B |
| same node | 8 | **48.15** | 48.08 | 14,567 | 120,375,083,008 | 179.0 % | 186.9 % | 201 µs / 767 µs (streams 1, 2) | 5,888,442 B |
| same AZ (cli→srv-a, 2a→2a) | 1 | **4.96** | 4.96 | 4 | 12,411,731,968 | 19.5 % | 15.4 % | **5,641 µs** | 4,349,214 B |
| same AZ | 8 | **9.94** | 9.93 | 5,874 | 24,846,139,392 | 36.3 % | 159.3 % | 2,720 µs / 1,626 µs | 1,163,370 B |
| cross-AZ (cli→srv-b, 2a→2b) | 1 | **4.96** | 4.96 | 2 | 12,411,994,112 | 20.0 % | 22.5 % | **5,420 µs** | 4,304,469 B |
| cross-AZ | 8 | **9.94** | 9.93 | 5,979 | 24,845,090,816 | 36.7 % | 138.2 % | 3,671 µs / 3,237 µs | 1,226,013 B |

Four things to read here.

1. **Same-node traffic bypassed the physical NIC.** The single-flow result was 29.97 Gbps with 99.8 % client process CPU; eight flows reached 48.15 Gbps. Host routing, both Pods’ veth paths, kernel processing and CPU scheduling still matter. This is a network benchmark with evidence of CPU pressure, not a measurement of pure memory-copy speed.
2. **Both inter-node single-flow runs reached 4.96 Gbps.** This is consistent with the ordinary 5 Gbps limit outside a cluster placement group. AWS also documents up to 10 Gbps for flows within a cluster placement group, and up to 25 Gbps with eligible ENA Express paths in the same AZ. Low iperf3 process CPU alone does not rule out all host/network processing limits.
3. **Both eight-flow runs reached 9.94 Gbps.** This supports similar observed throughput for these paths during this window. Retransmits existed even at one flow (4 / 2 for inter-node paths) and increased at eight flows (5,874 / 5,979); retransmission counts alone do not identify ENA shaping or the location of loss. The ENA allowance counters were not collected.
4. **Loaded TCP RTT was higher than idle ICMP RTT.** The single-flow sender reported about **5.6 / 5.4 ms** and a roughly 4.3 MB congestion window, compared with idle ping means of 0.34 / 0.54 ms. Queueing is a candidate explanation, but protocol, sampling and load differ. Neither the queue location nor a guaranteed extra 5 ms for every multiplexed RPC was measured.

The reported MSS 8949 is consistent with a 9001-byte MTU and the observed IPv4/TCP overhead; effective MSS also depends on headers and path MTU. The bytes-sent column below is application transfer volume, not independently verified billable usage.

> For this ordinary EC2 path, parallel flows used more of the instance’s available burst bandwidth than one flow. Increasing parallelism also changes CPU load, congestion and cost. Check the actual instance/path limits before changing Kafka fetchers or transfer concurrency; the measurements do not support either “every connection is capped at 5 Gbps” or “one AZ always doubles bandwidth.”

### The 3-minute sustained run and burst credits

The reported m5.xlarge baseline is 1.25 Gbps, with a best-effort peak up to 10 Gbps. The historical four-flow cross-AZ test ran for 180 s at 10 s intervals (`iperf3 -c 10.0.3.65 -p 5201 -t 180 -P 4 -i 10 -J`). That IP belongs to the recorded fixture; obtain current Pod IPs before any new test.

| Item | Value |
|---|---|
| Gbps per 10 s interval (18 intervals) | 9.94, 9.93 ×12, 9.92, 9.93 ×4 — **min 9.92, max 9.94** |
| Total sent | 223,376,179,200 B = **223.4 GB** in 180.0 s (9.93 Gbps) |
| Retransmits | 44,842 (≈ 249/s; 2,273–2,669 per 10 s interval) |
| CPU | client 30.7 % (system 30.1 %), server 54.2 % (system 52.2 %) |

**No drop toward 1.25 Gbps was observed within 180 s.** This is not evidence of unlimited credits or guaranteed sustained peak bandwidth. AWS documents variable, best-effort bursts and throttling toward baseline when credits run out. Size long backups and rebalances using the applicable baseline and measured workload requirements, rather than extrapolating this short run.

## Measurement 3 — A model of cross-AZ data-transfer cost

This section preserves the report’s cost arithmetic as an estimate. The benchmark supplied payload-byte counts and a public list price, not a Cost and Usage Report (CUR) or invoice.

For direct EC2 private-IP transfers between AZs in the same Region, the [EC2 pricing page](https://aws.amazon.com/ec2/pricing/on-demand/) documents $0.01/GB at each end. The reported public Pricing API item was `APN2-DataTransfer-Regional-Bytes`, **$0.0100000000 USD/GB**. `get-products` returns catalog pricing, not an account-specific paid rate. One payload direction can incur both sending-end “out” and receiving-end “in” charges; it does not require an equally large reverse transfer. Other AWS service paths can have different charging rules.

| Scenario | Payload volume in the historical decimal-GB model | Estimated cost (model GB × $0.01 × 2) |
|---|---|---|
| The 180 s run (measured payload; estimated cost) | 223.4 GB | 223.4 × $0.01 ≈ **$2.23 at each end, $4.47 total** |
| Cross-AZ iperf3 transfers in Measurement 2 (12.41 + 24.85 + 223.38 GB) | 260.6 GB | ≈ $2.61 at each end, **≈ $5.21 total** (other traffic excluded) |
| An average of 1 Gbps crossing AZs for 30 days (**assumption**) | 0.125 GB/s × 86,400 s × 30 days = 324,000 GB ≈ **324 TB** | 324,000 × $0.02 ≈ **$6,480 / month** |
| An RF3 StatefulSet spread over 3 AZs with 100 MiB/s of leader ingest (**assumption**, replication traffic only) | two followers, each in another AZ → 2 × 100 MiB/s = 209,715,200 B/s × 2,592,000 s ≈ 543,600 GB ≈ **544 TB / month** | 543,600 × $0.02 ≈ **$10,870 / month** |

All four cost rows use the original **decimal conversion, 1 GB = 10⁹ payload bytes**, as a modeling assumption. This audit did not establish that EC2’s billed usage quantity equals that conversion. The exact raw totals are 223,376,179,200 B for the sustained run and 260,633,264,128 B for all three cross-AZ iperf3 runs. Reconcile actual metered units, rates, both charged endpoints, protocol overhead/retransmissions and applicable credits or discounts with the [CUR data-transfer records](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html). The last two rows additionally assume continuous traffic for 30 days; replication volume excludes producer/consumer traffic. **$4.47 and $5.21 are estimates, not amounts proven to have been spent.**

**What an operator should do.**

- **Prefer suitable local endpoints where supported.** Current Kubernetes documentation uses `Service.spec.trafficDistribution: PreferSameZone`; `PreferClose` is its deprecated alias. This is a preference with fallback, not a strict zone restriction. Check the API server, kube-proxy version and feature support; this recorded cluster used a 1.35 kube-proxy with a 1.36 control plane. Neither this preference nor an application Service path was measured, and it does not affect direct Pod-IP traffic.
- **Balance locality with fault tolerance.** Zone-aware reads or clients can reduce avoidable transfer, but moving all RF3 replicas into one AZ sacrifices AZ failure protection. Retain the required replica/failover design; see [Zonal Cluster Operations](../ops/15-zonal-operations-guide.md).
- **Measure both billed endpoints.** Track source/destination AZs and metered volume for backups, rebalances and replays. Sum the relevant “in” and “out” usage records, which can belong to different accounts; do not infer a final bill from payload bytes alone.

## Measurement 4 — DNS: the query amplification of ndots:5

![One glibc lookup under ndots:5 walks the four search suffixes with A+AAAA pairs (8 NXDOMAIN, 10 queries) before the absolute name answers, versus a trailing-dot lookup that ends in 2 queries.](../.gitbook/assets/en-networking-06-pod-network-benchmark-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-1.html)

This diagram illustrates the recorded glibc search sequence. Its 4.37 ms ends at the reported A response, not the full `getaddrinfo` call; the upstream arrows are explanatory, since the Pod capture did not observe that leg. “cache 30” is a TTL ceiling, not a guaranteed 30-second hit.

The recorded Pod had four search domains and `ndots:5`; that configuration is not universal across EKS, DNS policies, operating systems or node settings. For this glibc `AF_UNSPEC` lookup, A and AAAA were requested for each candidate, and the four search candidates returned NXDOMAIN before the absolute STS name succeeded. A/AAAA concurrency and query counts can change with resolver options, address family, early success, retries and TCP fallback. The historical capture used `tcpdump -i eth0 -nn udp port 53`, which observes UDP DNS only. The report describes one first-process lookup followed by 20 timed repeats; a first-process call does not prove that CoreDNS or upstream caches were cold. See [Kubernetes Pod DNS configuration](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/).

### Queries sent for one resolution and warm latency (20 repeats), ms

| Pod / ndots | Name (dots) | Queries sent | NXDOMAIN answers | warm min | **median** | p90 | max |
|---|---|---|---|---|---|---|---|
| default / 5 | `kubernetes.default` (1) | 4 | 2 | 0.87 | **1.71** | 1.97 | 2.61 |
| default / 5 | `kubernetes.default.svc.cluster.local` (4) | **10** | 8 | 1.53 | **3.63** | 4.45 | 6.41 |
| default / 5 | `kubernetes.default.svc.cluster.local.` (trailing dot) | 2 | 0 | 0.33 | **0.46** | 1.09 | 1.58 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com` (3) | **10** | 8 | 3.08 | **3.78** | 4.66 | 4.84 |
| default / 5 | `sts.ap-northeast-2.amazonaws.com.` (trailing dot) | 2 | 0 | 0.42 | **0.80** | 1.25 | 2.17 |
| default / 5 | `www.amazon.com` (2) | **10** | 8 | 2.51 | **3.46** | 3.74 | 5.86 |
| ndots1 / 1 | `kubernetes.default` (1) | **6** | 4 | 1.16 | **2.04** | 2.80 | 4.54 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local` (4) | 2 | 0 | 0.35 | **0.97** | 1.08 | 1.35 |
| ndots1 / 1 | `kubernetes.default.svc.cluster.local.` | 2 | 0 | 0.34 | **0.40** | 0.97 | 1.17 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com` (3) | 2 | 0 | 0.45 | **0.54** | 1.22 | 1.42 |
| ndots1 / 1 | `sts.ap-northeast-2.amazonaws.com.` | 2 | 0 | 0.47 | **0.75** | 1.20 | 1.30 |
| ndots1 / 1 | `www.amazon.com` (2) | 2 | 0 | 0.63 | **0.90** | 1.27 | 2.74 |

The reported first-process times were: default / `sts` 6.22 ms, default / `sts.` 2.87 ms, default / `www.amazon.com` 9.58 ms, default / `kubernetes.default.svc.cluster.local` 7.40 ms, ndots1 / `kubernetes.default` 10.52 ms, and ndots1 / `sts` 2.84 ms. These include resolver initialization work and are distinct from the wire timelines below.

**How to read it.** In these samples, the external names and the cluster FQDN without a trailing dot produced **10 queries / 8 NXDOMAIN**. The trailing-dot STS median fell 3.78 → 0.80 ms, and the cluster FQDN median 3.63 → 0.46 ms. `kubernetes.default` succeeded on the second search candidate, so it needed only four queries: search expansion does not invariably consume the whole list. [CoreDNS cache](https://coredns.io/plugins/cache/) can cache negative answers, but `cache 30` sets a maximum TTL; response TTLs and minimums still apply, and each replica has its own cache. The Kubernetes plugin’s default TTL is 5 s unless configured otherwise. Sequential queries remain even on cache hits, but this capture does not prove that all warm lookups avoided upstream traffic.

### The walk itself — one cold resolution of `sts.ap-northeast-2.amazonaws.com` (ndots:5, tcpdump, ms from the first packet)

| t (ms) | Candidate sent to 172.20.0.10 (A + AAAA in parallel) | Answer |
|---|---|---|
| 0.00 | `sts.ap-northeast-2.amazonaws.com.bench-net.svc.cluster.local.` | NXDomain (authoritative, CoreDNS kubernetes plugin) at 0.92 / 1.14 |
| 1.21 | `sts.ap-northeast-2.amazonaws.com.svc.cluster.local.` | NXDomain at 2.01 / 2.26 |
| 2.32 | `sts.ap-northeast-2.amazonaws.com.cluster.local.` | NXDomain at 3.15 / 3.41 |
| 3.47 | `sts.ap-northeast-2.amazonaws.com.ap-northeast-2.compute.internal.` | NXDomain (forwarded to the VPC resolver — non-authoritative) at 3.68 / 3.93 |
| 3.99 | `sts.ap-northeast-2.amazonaws.com.` | **A 10.0.3.84, A 10.0.2.129** at 4.37 (AAAA: no data) |

The table records 10 queries and 8 NXDOMAIN. Its **4.37 ms** runs from the first query to the reported A answer; the AAAA completion time is not listed, so this is not the full 6.22 ms first-process call. Candidate RTTs are not uniformly 0.8–1.1 ms: the fourth pair took 0.21 / 0.46 ms and the final A took 0.38 ms. kube-proxy iptables chooses an endpoint for a new conntrack flow, rather than independently for every packet; A/AAAA requests can share that flow. With two equally selected endpoints, half of new flows would be an illustrative expectation, **not a measured fraction of cross-AZ DNS queries**. The Pod capture showing Service VIP `172.20.0.10` cannot identify the selected backend AZ. The original report attributes the two STS private addresses to interface endpoint ENIs, and records a 2.2 ms forwarded candidate / 5.6 ms wire walk for the cluster FQDN versus 0.4–0.5 ms with its trailing dot; these are separate observations.

### What `ndots:1` does — and its side effect

- **External names in these samples**: 10 → **2 queries**, medians about 3.5–3.8 → **0.5–0.9 ms**. This gain depends on the names and resolver behavior.
- **Short names can incur an extra failed attempt.** Here `kubernetes.default` has one dot, meeting `ndots:1`, so glibc first tried `kubernetes.default.`. CoreDNS forwarded it and received NXDOMAIN after a reported 1.6 ms, then tried the namespace suffix and finally succeeded with `svc.cluster.local` at `172.20.0.1`: six queries, four NXDOMAIN and a 2.04 ms median versus 1.71 ms. This can disclose internal-looking names upstream. Test every application’s service naming before changing `ndots`; full Service names reduce this ambiguity.
- **A trailing dot makes the resolver name absolute**, avoiding search expansion in this resolver. It does not guarantee two wire queries or a fixed latency under retries, different address-family settings or caching.

### Amplification arithmetic (derived)

Under the **same response pattern**, with no application DNS cache and one lookup per request, 1,000 resolutions/s × 10 queries gives 10,000 queries/s, versus 2,000 for the two-query form. Of those 10,000, 8,000 (80 %) would receive NXDOMAIN. This is a query-count model, not a measurement of CoreDNS CPU or the cross-AZ fraction. The observed median differences are 3.78 − 0.80 = 2.98 ms for STS and 3.63 − 0.46 = 3.17 ms for the cluster FQDN; they are not fixed per-request penalties.

**Options to test with the actual application:**

- Use absolute DNS names where the client supports them. Do not blindly append a dot to HTTPS or AWS SDK endpoint URLs: Host handling, SNI, certificate verification and request signing must still work.
- Evaluate `dnsConfig: {options: [{name: ndots, value: "1"}]}` together with short-name behavior and application DNS caching.
- Evaluate [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) where appropriate. Cache hits stay local; misses can still go upstream. Current [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) already runs node-local CoreDNS as a system service; a pure Auto Mode cluster does not need a CoreDNS Deployment, while non-Auto nodes in a mixed cluster still do.
- [CoreDNS autopath](https://coredns.io/plugins/autopath/) can do search completion server-side, but its Kubernetes integration requires `pods verified`, visibility of the originating Pod IP and the associated Pod watches/RBAC/memory. The recorded `pods insecure` configuration does not meet those requirements. This optimization was not tested here.

## How to reproduce — revised procedure

Use an approved, isolated lab and an unused namespace dedicated to this test. Save an adapted copy of the first fixture as `bench-net.yaml` and both DNS objects as `bench-dns.yaml`; keep the namespace names consistent. Check NodePool capacity, AZs, scheduling and packet-capture permissions before applying. Do not weaken production admission or security controls to run the test. These bounded commands can still saturate nodes and incur charges.

Run all commands from the **operator’s Bash shell**, without entering an interactive shell in `cli`. The audit checked syntax and selected local tool behavior; it did not deploy this fixture or run these network loads on EKS.

**1. Deploy the adapted fixture and verify placement.**

```bash
set -euo pipefail
BENCH_NS=bench-net
kubectl apply -f bench-net.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready \
  pod/cli pod/srv-same pod/srv-a pod/srv-b --timeout=300s
kubectl -n "$BENCH_NS" get pods -o wide
kubectl get nodes -L topology.kubernetes.io/zone,node.kubernetes.io/instance-type,karpenter.sh/nodepool

SAME_IP=$(kubectl -n "$BENCH_NS" get pod srv-same -o jsonpath='{.status.podIP}')
AZ_IP=$(kubectl -n "$BENCH_NS" get pod srv-a -o jsonpath='{.status.podIP}')
CROSS_IP=$(kubectl -n "$BENCH_NS" get pod srv-b -o jsonpath='{.status.podIP}')
: "${SAME_IP:?missing srv-same IP}" "${AZ_IP:?missing srv-a IP}" "${CROSS_IP:?missing srv-b IP}"
for bench_pod in srv-same srv-a srv-b; do
  kubectl -n "$BENCH_NS" logs "$bench_pod" --tail=30
  kubectl -n "$BENCH_NS" exec "$bench_pod" -- ss -lnt
done
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- \
    curl --fail --silent --show-error --max-time 5 "http://$bench_ip:8080/" >/dev/null
done
```

Before continuing, verify `cli` and `srv-same` share a node, `srv-a` uses a different node in the same AZ, and `srv-b` uses another AZ. Check server listeners on 5201/8080/8079 and startup errors: Pod Ready alone does not prove these processes are listening, because the historical fixture has no readiness probes. Record node IDs, IPs, image IDs and actual `iperf3 --version` / `fortio version`. Stop and refresh addresses if a Pod is recreated.

**2. RTT and one reference HTTP request.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- ping -c 200 -i 0.05 -q "$bench_ip"
done
kubectl -n "$BENCH_NS" exec cli -- curl --fail --silent --show-error --max-time 5 \
  -o /dev/null -w 'connect=%{time_connect} total=%{time_total}\n' "http://$CROSS_IP:8080/"
```

**3. Throughput, with bounded duration and operator-local output files.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 1 -J > "t1-$bench_ip-P1.json"
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 8 -J > "t1-$bench_ip-P8.json"
done
kubectl -n "$BENCH_NS" exec cli -- \
  iperf3 -c "$CROSS_IP" -p 5201 -t 180 -P 4 -i 10 -J > t1-cross-sustained180-P4.json
```

Check JSON errors as well as exit status. Read `end.sum_sent.bits_per_second`, `end.sum_sent.retransmits`, `end.cpu_utilization_percent.host_total` / `remote_total` and `end.streams[].sender.mean_rtt` / `max_snd_cwnd`. iperf3 3.19 process CPU uses 100 % for one CPU’s time over elapsed wall time; multiple threads can exceed 100 %. TCP RTT fields are in microseconds.

**4. Request latency. Repeat for each verified server address.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 60s "http://$bench_ip:8080/" > "http-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 30s -keepalive=false "http://$bench_ip:8080/" > "new-connection-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 0 -c 16 -t 20s "http://$bench_ip:8080/" > "closed-loop-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -grpc -ping -qps 100 -c 4 -t 30s "$bench_ip:8079" > "grpc-$bench_ip.json"
done
```

In Fortio 1.69.5, `-r` is the histogram’s lowest-bucket resolution in seconds: the default `0.001` is 1 ms, and `0.00001` is 10 µs; larger buckets can widen. Percentiles interpolate within bucket bounds, including the observed minimum/maximum at the edges. A single populated bucket therefore **does not imply p50 = 0.5 ms**. The report discarded its first coarse-resolution percentiles and reran with 10 µs resolution; retain that history without calling all interpolated percentiles fake. Several tail values and new-connection medians in the tables exceed 1 ms. Save the full histogram and error counters alongside averages.

**5. DNS: separate the capture of one lookup from the timed repeats.**

```bash
kubectl apply -f bench-dns.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready pod/dns-default pod/dns-ndots1 --timeout=300s
for bench_pod in dns-default dns-ndots1; do
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- cat /etc/resolv.conf
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- ldd --version
done
```

In terminal 1, start capture before the single lookup. This filter includes ordinary UDP and TCP DNS on port 53; it does not cover encrypted DNS or CoreDNS’s upstream leg. Stop capture with Ctrl-C after that lookup before doing warm repeats.

```bash
kubectl -n bench-net exec -it dns-default -c sniffer -- \
  tcpdump -l -i eth0 -nn '(udp or tcp) and port 53'
```

In terminal 2, create this local helper and forward it with **`kubectl exec -i`**. The first mode makes exactly one resolver call. Warm mode makes one unmeasured warm-up followed by 20 calls in the same process; this revised procedure makes the capture boundary explicit.

```bash
cat > dns-probe.py <<'PY'
import json
import socket
import statistics
import sys
import time

name, mode = sys.argv[1:3]
if mode not in ("first", "warm"):
    raise SystemExit("mode must be first or warm")

def one():
    started = time.perf_counter()
    socket.getaddrinfo(name, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return (time.perf_counter() - started) * 1000

first = one()
if mode == "first":
    print(json.dumps({"name": name, "first_process_ms": first}))
else:
    samples = [one() for _ in range(20)]
    ordered = sorted(samples)
    print(json.dumps({
        "name": name, "warmup_ms": first, "samples_ms": samples,
        "min_ms": ordered[0], "median_ms": statistics.median(ordered),
        "p90_ms": ordered[17], "max_ms": ordered[-1],
    }))
PY
BENCH_NS=bench-net
DNS_POD=dns-default
DNS_NAME=sts.ap-northeast-2.amazonaws.com
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" first < dns-probe.py
```

After stopping capture:

```bash
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" warm < dns-probe.py
```

Repeat with the names in the table and `DNS_POD=dns-ndots1`, changing the capture target too. Count query/response pairs from the first-only window; do not count 21 lookups as one. Use matching digests, resolver versions and configuration, but expect timings and cache state to differ. The original image digests and complete packet/JSON artifacts are not supplied on this page, so exact reproduction is not guaranteed.

**6. Clean up only this test’s resources.** If `bench-net` was created exclusively for this run, remove it with `kubectl delete namespace bench-net` after saving results. Verify the remaining nodes and cost separately. Karpenter consolidation depends on its policy, budgets and other workloads; deleting the namespace does not guarantee immediate node removal. `do-not-disrupt` is not protection against every forceful disruption method.

## Caveats

- **The nodes were fresh, but not entirely alone.** Soon after Karpenter launched the three m5.xlarge nodes for this test, consolidation moved a few small Pods from other namespaces onto them (one onto the `cli` node, three onto the `srv-b` node — small internal services and controllers unrelated to the benchmark traffic). They were idle or low-traffic during the runs, and load was limited to bursts of at most 180 s. The `cli` node showed 3901m / 3920m (99 %) of CPU *requested*, which says nothing about actual utilisation.
- **Single run (n = 1 per cell, one day).** There were no independent repetitions to estimate variance. Rankings, ratios and causal explanations are also limited by that sample size; none is an SLA.
- **Application ClusterIP and traffic distribution were not measured.** The report says Service creation in the benchmark namespace failed with `failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`. A failing `failurePolicy: Fail` webhook rejects matching requests; its rules, namespace/object selectors and match conditions determine scope. This historical incident is not a statement that today’s cluster cannot create any Service. The benchmark did not bypass the webhook. DNS still used the pre-existing `kube-dns` Service. See the [Troubleshooting Playbook](../ops/16-troubleshooting-playbook.md).
- **ENA allowance counters were not collected.** `ethtool -S` must target the host’s actual ENA interface with appropriate access; a Pod’s own `eth0` is generally a veth, and `hostNetwork` alone does not prove the right device or permissions. Relevant counters include `bw_in_allowance_exceeded`, `bw_out_allowance_exceeded`, `pps_allowance_exceeded`, `conntrack_allowance_exceeded` and `linklocal_allowance_exceeded`. Retransmits do not substitute for these measurements.
- **Burst-credit exhaustion was merely not observed within 180 s.** On "Up to" instances, longer sustained transfers may be throttled toward the baseline (1.25 Gbps). Nothing beyond 180 s was tested.
- **DNS cache state was not controlled.** First-process and repeated lookups differ, but `cache 30` does not ensure a hit for 30 s. Replica selection and upstream state can affect both sets of timings; the reported comparison is observational.
- **Same-node CPU pressure is plausible.** The client’s 99.8 % process CPU supports that interpretation of the 29.97 Gbps result; it does not establish every bottleneck or make 29.97 / 48.15 Gbps portable to other instances.
- **Other CNI modes and policy enforcement were not compared.** Prefix delegation and Security Groups for Pods were off; the namespace had no NetworkPolicies. These bare Pods also do not constitute a validation of VPC CNI NetworkPolicy enforcement for supported controller-owned workloads.

## Related reading

- [Amazon VPC CNI](./01-vpc-cni.md) — the data plane under these measurements: Pods receiving VPC IPs directly, prefix delegation, ENI/IP warming
- [Zonal Cluster Operations](../ops/15-zonal-operations-guide.md) — zone-aligned placement and AZ failover design that reduce the bill in Measurement 3
- [Troubleshooting Playbook](../ops/16-troubleshooting-playbook.md) — diagnosis of webhook failures; the incident here is historical
- [Sidecar vs Ambient Mode Selection Guide](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) — separate hardware/workload experiment; its +1.29 ms is a whole-scenario difference
- [EBS gp2 vs gp3 Measured Benchmark](../storage/01-ebs-gp2-gp3-benchmark.md) — the storage path of the same cluster, measured
- [Kafka on EKS Measured Benchmark](../data-on-eks/kafka/09-kafka-benchmark.md) — replication traffic, flow limits and availability tradeoffs
- [Guidebook Roadmap — the measured-benchmark series](../roadmap.md)
- [Quiz: Pod Network Benchmark](../quizzes/networking/06-pod-network-benchmark-quiz.md)


### Primary references used in the review

- [Fortio 1.69.5 histogram implementation](https://github.com/fortio/fortio/blob/v1.69.5/stats/stats.go) · [CLI flags](https://github.com/fortio/fortio/blob/v1.69.5/cli/fortio_main.go)
- [glibc 2.41 search ordering](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_query.c) · [A/AAAA transport](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_send.c)
- [CoreDNS Kubernetes / autopath requirements](https://coredns.io/plugins/kubernetes/)
- [Kubernetes Service traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/) · [virtual IP handling](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [EC2 ENA network metrics](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html)
- [Karpenter disruption and cleanup conditions](https://karpenter.sh/docs/concepts/disruption/)
