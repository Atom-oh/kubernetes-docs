# Pod Network Benchmark — Same Node, Same AZ, Cross-AZ, and DNS ndots

> **Supported Versions**: Kubernetes 1.36 (Amazon EKS), Amazon VPC CNI v1.21.1, kube-proxy iptables mode
> **Last Updated**: September 2, 2026

What actually changes when two Pods on EKS sit on the same node, on different nodes in the same AZ, or in different AZs? Two misconceptions travel with that question. The first is that crossing an AZ "makes things slower and cuts bandwidth" — in this run the AZ boundary changed **latency and the bill**, and bandwidth not at all. The second is DNS: the `ndots:5` and the four-entry search list that every EKS Pod receives silently turn one external lookup — for any name with fewer than five dots — into 10 DNS queries instead of 2. This page collects the RTT, HTTP/gRPC latency, iperf3 throughput, intra-region data transfer cost and DNS query counts measured on `fsi-demo-cluster` (Seoul) on **September 2, 2026** with the fixture described under "How to reproduce". Every number is Pod IP to Pod IP (no ClusterIP); the reason is in "Caveats".

![Client Pod on node A (ap-northeast-2a) reaching a server Pod on the same node, on node B in the same AZ and on node C in ap-northeast-2b — RTT 0.040 / 0.339 / 0.544 ms, single flow 29.97 / 4.96 / 4.96 Gbps.](../.gitbook/assets/en-networking-06-pod-network-benchmark-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-0.html)

## TL;DR — What we measured

1. **The RTT ladder**: same node **0.040 ms** → same AZ **0.339 ms** → cross-AZ **0.544 ms** (ping, average of 200 probes). One AZ hop costs +0.21 ms, or +0.50 ms relative to the same node.
2. **HTTP p50 / p99** (fortio, 100 qps, 4 connections, keepalive, 60 s): 0.259 / 0.350 ms → 0.461 / 0.667 ms → 0.704 / 0.812 ms — the same ladder seen from the application.
3. **Bandwidth**: one TCP flow tops out at **4.96 Gbps** whether it stays inside the AZ or crosses it (the EC2 5 Gbps single-flow limit). Eight flows reach **9.94 Gbps** = the m5.xlarge 10 Gbps peak. **Crossing the AZ does not reduce throughput.**
4. **Same-node Pod to Pod**: **29.97 Gbps** on a single flow (CPU-bound — the client used 99.8 % of one core), **48.15 Gbps** with 8 flows. The traffic crosses a veth pair and never touches the NIC.
5. **The bill**: 3 minutes at line rate across AZs = **223.4 GB** = about **$4.47** of Regional Data Transfer ($0.01/GB in each direction). No burst-credit step-down toward the 1.25 Gbps baseline was observed within 180 s.
6. **DNS**: with the default `ndots:5`, a glibc Pod resolving `sts.ap-northeast-2.amazonaws.com` once sends **10 queries** (8 answered NXDOMAIN), warm median **3.78 ms**. A trailing dot cuts that to **2 queries** (A+AAAA) / 0.80 ms; `ndots:1` gives 2 queries / 0.54 ms.
7. **A new connection costs one more RTT per request**: with keepalive off, p50 goes 0.259 → 0.664, 0.461 → 1.079 and 0.704 → **1.517 ms**. Across AZs, per-request latency more than doubles.

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

"Up to" means burstable networking: the instance can use its peak bandwidth while it has network I/O credits and is throttled toward the baseline when they run out (AWS EC2 User Guide, "Amazon EC2 instance network bandwidth"). The sustained run in Measurement 2 shows only that this limit did not kick in within 180 s (no step-down toward the baseline was observed, and nothing longer was tested).

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

Only the long English comment header was removed; `nodeSelector`, `affinity`, `requests`, `command` and `annotations` are exactly what ran. There are no Service objects because the fixture uses Pod IPs only (see "Caveats" for why).

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

The two DNS Pods were placed on the same node as `srv-a`. The `app` container is glibc (`python:3.12-slim`, Debian 13, glibc 2.41): this page measures the glibc resolver, and results with other resolvers (musl/alpine) were not measured; `sniffer` (netshoot) shares the Pod's network namespace, so its tcpdump sees every query that `app` sends. The only difference between the two Pods is `dnsConfig`.

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

ICMP first, to measure the bare network path (`ping -c 200 -i 0.05 -q`), then the same three paths as HTTP/1.1 and gRPC requests with fortio. A single cold `curl` request's connect / total time is listed for reference.

| Path | RTT min / **avg** / max / mdev (ms) | Loss | curl, 1 cold request: connect / total |
|---|---|---|---|
| same node → 10.0.2.72 | 0.021 / **0.040** / 0.089 / 0.007 | 0/200 | 0.194 ms / 0.497 ms |
| same AZ → 10.0.2.37 | 0.300 / **0.339** / 0.450 / 0.017 | 0/200 | 0.497 ms / 2.333 ms |
| cross-AZ → 10.0.3.65 | 0.504 / **0.544** / 0.625 / 0.015 | 0/200 | 0.694 ms / 4.038 ms |

Deltas: same AZ − same node = +0.30 ms, cross-AZ − same AZ = **+0.21 ms**, cross-AZ − same node = +0.50 ms. All three paths are very stable — mdev is 0.017 ms or less. curl's "total" is one cold run that includes process start-up, so treat it as indicative only and read latency from the fortio tables below.

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

The response body is about 75 bytes (fortio echo, empty payload) and every run finished with 0 errors (200 / SERVING).

**How to read it.** HTTP p50 is the ping average plus 0.12–0.22 ms (0.259 − 0.040 ≈ 0.22, 0.461 − 0.339 ≈ 0.12, 0.704 − 0.544 ≈ 0.16) — that remainder is the client and server user-space stack. The AZ hop costs **+0.24 ms** at p50 (0.461 → 0.704), the same size as ping's +0.21 ms and close to the node hop (+0.20 ms, 0.259 → 0.461). In other words, "same node → different node" and "same AZ → different AZ" are each a constant step of roughly 0.2 ms. gRPC ping p50 sits about 0.13–0.16 ms above HTTP/1.1 on every path (0.397 / 0.592 / 0.865 vs 0.259 / 0.461 / 0.704) — HTTP/2 framing plus protobuf in the fortio ping. Where the paths separate most is the tail: HTTP p99 goes 0.350 → 0.667 → 0.812 ms, and gRPC p99.9 goes 1.187 → 1.052 → **2.582 ms**, crossing 2 ms only on the cross-AZ path.

> **One point of comparison.** In this repository's [Istio sidecar vs ambient measurements](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md), a single sidecar adds **+1.29 ms** at p50. An AZ hop here costs +0.21–0.24 ms — **one mesh hop costs more than one AZ hop.** Before blaming "the other AZ" for a slow request, count the proxies in its path.

### The cost of a new connection — keepalive=false, 100 qps, 4 connections, 30 s (3,000 requests), ms

What happens to latency when every request opens a fresh TCP connection (fortio `-keepalive=false`)?

| Path | avg | **p50** | p90 | p99 | p99.9 | max | min | vs keepalive p50 |
|---|---|---|---|---|---|---|---|---|
| same node | 0.672 | **0.664** | 0.782 | 0.957 | 1.253 | 1.306 | 0.364 | **+0.405 ms** |
| same AZ | 1.066 | **1.079** | 1.185 | 1.369 | 1.582 | 1.795 | 0.769 | **+0.618 ms** |
| cross-AZ | 1.530 | **1.517** | 1.678 | 1.796 | 1.981 | 2.009 | 1.300 | **+0.813 ms** |

One new connection costs roughly **one RTT (the TCP handshake) plus about 0.3 ms of socket setup and teardown**. The larger the path's RTT, the larger the surcharge: across AZs the p50 of a single request goes from 0.704 to 1.517 ms — **more than double**. Connection pooling (HTTP keepalive, gRPC channel reuse, database connection pools) is not a performance tweak; it is the precondition for any call that crosses an AZ (and, as with any connection-per-request client, each fresh connection also leaves a TIME_WAIT socket behind — not measured here).

### Maximum qps from a fixed connection pool — latency is throughput (closed loop, 16 connections, 20 s)

With `-qps 0` (unlimited, closed loop), the maximum request rate that 16 connections can sustain turns the latency difference into a throughput difference.

| Path | Requests | **Achieved qps** | avg ms | p50 | p90 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|
| same node | 899,827 | **44,991** | 0.355 | 0.249 | 0.733 | 1.695 | 3.389 | 13.593 |
| same AZ | 770,156 | **38,507** | 0.415 | 0.396 | 0.537 | 0.728 | 1.147 | 4.502 |
| cross-AZ | 512,060 | **25,602** | 0.624 | 0.597 | 0.770 | 0.949 | 1.293 | 4.725 |

Little's law (derived: throughput = concurrency ÷ latency) holds almost exactly — 16 ÷ 0.000355 s = 45,070 (measured 44,991), 16 ÷ 0.000415 = 38,554 (38,507), 16 ÷ 0.000624 = 25,641 (25,602). With a pool of fixed size, the AZ hop's +0.2 ms **cuts achievable throughput by 34 %** (38.5k → 25.6k qps). For a request/response service, what makes the other AZ expensive is this latency, not bandwidth. The same-node p99/max being worse than same-AZ is not the network either: at 45k qps the client and the server share the 4 vCPUs of one node and contend for CPU.

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

1. **Same-node is memory-copy speed.** At 29.97 Gbps on a single flow the client iperf3 was using 99.8 % of one core, and 8 flows pushed it to 48.15 Gbps. Packets over a veth pair never pass the NIC or the ENA shaper, so these are CPU figures for this instance and will differ on another instance family.
2. **A single TCP flow between nodes stops at 4.96 Gbps — identical to the second decimal for same-AZ and cross-AZ.** AWS documents that outside a cluster placement group a single flow is limited to 5 Gbps ("Amazon EC2 instance network bandwidth"), and that limit is what shows up. The flow uses about 20 % of a core, so CPU is not the bottleneck.
3. **Eight flows give 9.94 Gbps = the m5.xlarge 10 Gbps peak**, again identical on both paths. **Crossing the AZ boundary does not reduce bandwidth.** Retransmits appear only when the instance ceiling is hit (5,874 / 5,979 at 8 flows vs 2–13 at 1 flow) — an **indirect signal** consistent with ENA allowance shaping dropping packets at the cap; the ENA `*_allowance_exceeded` counters were not collected in this run (Caveats).
4. **When a flow is saturated, every request riding it waits.** With a single flow pinned at the cap, the sender's TCP RTT grew from an idle ping RTT of 0.34 ms (same AZ) / 0.54 ms (cross-AZ) to **5.6 ms** / **5.4 ms** with a congestion window of about 4.3 MB. That delay is queueing in the shaper, so a request/response exchange multiplexed onto the same TCP connection as a bulk transfer loses about 5 ms.

MSS 8949 follows from the 9001-byte MTU (jumbo frames), and the bytes-sent column is the basis for the cost arithmetic in the next section.

> **So what:** one gRPC stream, one Kafka replica fetcher, one volume copy — "one connection" between two Pods on different nodes never exceeds about 5 Gbps, whatever it carries. To use the instance's 10 Gbps you have to split the work across parallel connections (`num.replica.fetchers`, multipart uploads, parallel rsync and the like); conversely, the expectation that "keeping it in one AZ doubles the bandwidth" has no support in these measurements.

### The 3-minute sustained run and burst credits

The baseline of "Up to 10 Gigabit" is 1.25 Gbps. Once credits run out the instance should drop from peak toward baseline, so a 4-flow cross-AZ run was watched for 180 s at 10 s intervals (`iperf3 -c 10.0.3.65 -p 5201 -t 180 -P 4 -i 10 -J`).

| Item | Value |
|---|---|
| Gbps per 10 s interval (18 intervals) | 9.94, 9.93 ×12, 9.92, 9.93 ×4 — **min 9.92, max 9.94** |
| Total sent | 223,376,179,200 B = **223.4 GB** in 180.0 s (9.93 Gbps) |
| Retransmits | 44,842 (≈ 249/s; 2,273–2,669 per 10 s interval) |
| CPU | client 30.7 % (system 30.1 %), server 54.2 % (system 52.2 %) |

**No drop toward the 1.25 Gbps baseline was observed within 180 s.** That does not mean burst credits do not exist. AWS documents that on "Up to" instances longer sustained transfers may be throttled toward the baseline; nothing beyond 180 s was tested here, so this run cannot say when — or whether, for a fresh node — that point is reached. If you are planning multi-hour backups, rebalances or replays on m5.xlarge, budget for the 1.25 Gbps baseline (other sizes have their own baseline) and treat 10 Gbps as a bonus.

## Measurement 3 — The real cross-AZ cost is the bill

Measurements 1 and 2 showed that the AZ hop adds +0.2 ms of latency and leaves bandwidth untouched. So where is the real difference between AZs? On the invoice.

Within a region, AWS charges $0.01/GB on each side of an AZ crossing — "out" of the sending AZ and "in" to the receiving AZ (EC2 On-Demand pricing page, "Data Transfer within the same AWS Region"). The Pricing API item for this account is `APN2-DataTransfer-Regional-Bytes`, "Regional Data Transfer - in/out/between AZs or when using public IP or Elastic IP addresses", **$0.0100000000 USD/GB**. For a one-way bulk transfer the sending AZ is billed $0.01/GB "out" and the receiving AZ $0.01/GB "in", so within one account it is effectively **$0.02 per GB crossing an AZ boundary** (derived: $0.01 × 2).

| Scenario | Bytes crossing the AZ boundary | Cost (derived: GB × $0.01 × 2) |
|---|---|---|
| The 180 s sustained run on this page (measured) | 223.4 GB | 223.4 × $0.01 = **$2.23 per direction, $4.47 total** |
| All cross-AZ transfer in Measurement 2 (measured: 12.41 + 24.85 + 223.38 GB) | 260.6 GB | ≈ $2.61 per direction, **≈ $5.21 total** (fortio and ping traffic, under 0.2 GB, ignored) |
| An average of 1 Gbps crossing AZs for 30 days (**assumption**) | 0.125 GB/s × 86,400 s × 30 days = 324,000 GB ≈ **324 TB** | 324,000 × $0.02 ≈ **$6,480 / month** |
| An RF3 StatefulSet spread over 3 AZs with 100 MiB/s of leader ingest (**assumption**, replication traffic only) | two followers, each in another AZ → 2 × 100 MiB/s = 209,715,200 B/s × 2,592,000 s ≈ 543,600 GB ≈ **544 TB / month** | 543,600 × $0.02 ≈ **$10,870 / month** |

The bottom two rows are not measurements but **estimates** at this unit price, and they ignore producer/consumer traffic and AZ placement. The point is the magnitude: a three-node benchmark spent $4.47 in three minutes, and sustained around the clock that rate becomes thousands of dollars a month. Bandwidth crosses the boundary undiminished, but every byte carries a price tag.

**What an operator should do.**

- **Keep traffic inside the AZ.** `Service.spec.trafficDistribution: PreferClose` — beta in Kubernetes 1.31, GA in 1.33 (Kubernetes docs, "Traffic Distribution") — makes kube-proxy prefer endpoints in the same zone. **It was not measured in this run** — no Service could be created (Caveats) — so this page has no number for its effect.
- **Zone-align stateful workloads.** StatefulSets with a large replication fan-out (Kafka RF3, distributed databases) send most of their replication bytes across AZs, as in the fourth row above. Zone-level placement and AZ failover design are covered in the [Zonal Cluster Operations guide](../ops/15-zonal-operations-guide.md).
- **Know the direction and volume of bulk transfers.** Record which AZ backups, rebalances and replays flow from and to, and how much, and remember that "in" and "out" are billed as two separate line items in the same account.

## Measurement 4 — DNS: the query amplification of ndots:5

![One glibc lookup under ndots:5 walks the four search suffixes with A+AAAA pairs (8 NXDOMAIN, 10 queries) before the absolute name answers, versus a trailing-dot lookup that ends in 2 queries.](../.gitbook/assets/en-networking-06-pod-network-benchmark-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-1.html)

An EKS Pod's `/etc/resolv.conf` has four search domains (`bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal`) and `options ndots:5`. The glibc resolver takes any name with fewer than `ndots` dots and **tries it with each search suffix first**, sending A and AAAA in parallel for every candidate (`single-request` is off by default). So `sts.ap-northeast-2.amazonaws.com`, with 3 dots, has to collect NXDOMAIN for all four candidates before it asks for the absolute name. Method: in the `app` container of `dns-default` / `dns-ndots1`, one cold `socket.getaddrinfo(name, 80, AF_UNSPEC, SOCK_STREAM)` call is made while tcpdump (`-i eth0 -nn udp port 53`) in the `sniffer` sidecar captures that single resolution's DNS packets, which are counted; the same name is then resolved 20 more times and timed in-process — that is the warm latency.

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

The cold first resolution (including glibc NSS initialisation; indicative only) was: default / `sts` 6.22 ms, default / `sts.` 2.87 ms, default / `www.amazon.com` 9.58 ms, default / `kubernetes.default.svc.cluster.local` 7.40 ms, ndots1 / `kubernetes.default` 10.52 ms, ndots1 / `sts` 2.84 ms.

**How to read it.** Under the default `ndots:5`, the two external names (`sts.…`, `www.amazon.com`) and — perhaps surprisingly — the **cluster FQDN without a trailing dot** (`kubernetes.default.svc.cluster.local`: 4 dots, fewer than 5) all cost **10 queries, 8 NXDOMAIN, median 3.5–3.8 ms**. Add one dot to the same name (`….com.`) and it is 2 queries / 0.46–0.80 ms — **one fifth of the queries, with the warm median falling from 3.78 to 0.80 ms for `sts` and from 3.63 to 0.46 ms for the cluster FQDN**. The short name `kubernetes.default` matches on the second candidate (`svc.cluster.local`) and stops at 4 queries / 1.71 ms. CoreDNS's `cache 30` caches NXDOMAIN for up to 30 s too, so what is expensive in the warm state is not upstream lookups but **waiting for 5 sequential Pod↔CoreDNS round trips**.

### The walk itself — one cold resolution of `sts.ap-northeast-2.amazonaws.com` (ndots:5, tcpdump, ms from the first packet)

| t (ms) | Candidate sent to 172.20.0.10 (A + AAAA in parallel) | Answer |
|---|---|---|
| 0.00 | `sts.ap-northeast-2.amazonaws.com.bench-net.svc.cluster.local.` | NXDomain (authoritative, CoreDNS kubernetes plugin) at 0.92 / 1.14 |
| 1.21 | `sts.ap-northeast-2.amazonaws.com.svc.cluster.local.` | NXDomain at 2.01 / 2.26 |
| 2.32 | `sts.ap-northeast-2.amazonaws.com.cluster.local.` | NXDomain at 3.15 / 3.41 |
| 3.47 | `sts.ap-northeast-2.amazonaws.com.ap-northeast-2.compute.internal.` | NXDomain (forwarded to the VPC resolver — non-authoritative) at 3.68 / 3.93 |
| 3.99 | `sts.ap-northeast-2.amazonaws.com.` | **A 10.0.3.84, A 10.0.2.129** at 4.37 (AAAA: no data) |

10 queries, 8 NXDOMAIN, 5 sequential round trips, 4.37 ms end to end — the useful answer arrives in the last 0.38 ms. Each candidate's Pod→CoreDNS→Pod round trip took 0.8–1.1 ms, which contains CoreDNS processing time plus the RTT ladder from Measurement 1. `172.20.0.10` is spread across the two CoreDNS Pods by iptables random selection, and one of them is in the other AZ, so **roughly half of all DNS queries cross the AZ boundary.** `sts.ap-northeast-2.amazonaws.com` resolves to two private IPs (10.0.2.x / 10.0.3.x) because this VPC has an STS interface endpoint with one ENI per AZ. `kubernetes.default.svc.cluster.local` without a trailing dot walks the same path; its `.ap-northeast-2.compute.internal` candidate took 2.2 ms because CoreDNS forwarded it upstream, and the whole walk took 5.6 ms cold versus 0.4–0.5 ms with the trailing dot.

### What `ndots:1` does — and its side effect

- **External names**: 10 → **2 queries**, median 3.5–3.8 → **0.5–0.9 ms** (about 4–8× faster, one fifth of the queries).
- **Short cluster names get worse.** `kubernetes.default` (1 dot, which is ≥ ndots 1) is first tried as the absolute name `kubernetes.default.`; CoreDNS has no zone for it and **forwards it to the VPC resolver** (NXDomain after 1.6 ms), then walks `bench-net.svc.cluster.local` (NXDOMAIN) and finally gets `172.20.0.1` from `svc.cluster.local` — 6 queries, 4 NXDOMAIN, median 2.04 ms, slower than the 1.71 ms under ndots:5. Cluster-internal names also leak to the upstream resolver. If you use `ndots:1`, address in-cluster services by FQDN (`name.namespace.svc.cluster.local`).
- **The trailing dot works regardless of ndots** — 2 queries, 0.4–0.8 ms in every case.

### Amplification arithmetic (derived)

An application that resolves one external name per request sends 10 DNS queries instead of 2 under `ndots:5` and spends **about +3 ms** per resolution (derived: 3.78 − 0.80 = 2.98 ms for `sts`, 3.63 − 0.46 = 3.17 ms for the FQDN without a trailing dot). Assume 1,000 resolutions/s cluster-wide and CoreDNS receives **10,000** queries/s instead of 2,000, 8,000 of them answered NXDOMAIN. Four fifths of the load on the two CoreDNS replicas goes into producing "does not exist", and about half of those packets also cross the AZ boundary at the Regional Data Transfer rate (small in volume, but not zero).

> **So what — four ways to fix it.** (1) Put a **trailing dot** on external endpoints in configuration (`sts.ap-northeast-2.amazonaws.com.`) — 2 queries immediately, no code change. (2) Give Pods that make many external calls `dnsConfig: {options: [{name: ndots, value: "1"}]}` — but then address cluster names by FQDN. (3) **NodeLocal DNSCache** — absent from this cluster; with it, the Pod↔CoreDNS round trips (half of them cross-AZ) become node-local cache hits (not measured). (4) The CoreDNS `autopath` plugin walks the search path server-side on the Pod's behalf; it was not in this Corefile (not measured).

## How to reproduce

1. Save the manifest above as `bench-net.yaml`, apply it, and check that the placement came out as intended. Pod IPs differ on every run, so read them from `-o wide` and substitute them into the commands below.

   ```bash
   kubectl apply -f bench-net.yaml
   kubectl -n bench-net get pods -o wide   # cli and srv-same on one node (2a), srv-a on another 2a node, srv-b in 2b
   kubectl -n bench-net exec -it cli -- bash
   ```

2. **RTT** — 200 probes per path at 50 ms intervals:

   ```bash
   ping -c 200 -i 0.05 -q 10.0.2.72   # same-node
   ping -c 200 -i 0.05 -q 10.0.2.37   # same-AZ
   ping -c 200 -i 0.05 -q 10.0.3.65   # cross-AZ
   curl -s -o /dev/null -w 'connect=%{time_connect} total=%{time_total}\n' http://10.0.3.65:8080/   # one cold request, for reference
   ```

3. **Throughput** — iperf3, 20 s, 1 flow and 8 flows, JSON output. The sustained run is cross-AZ for 180 s / 4 flows / 10 s intervals:

   ```bash
   for SRV in 10.0.2.72 10.0.2.37 10.0.3.65; do
     iperf3 -c $SRV -p 5201 -t 20 -P 1 -J > t1-$SRV-P1.json
     iperf3 -c $SRV -p 5201 -t 20 -P 8 -J > t1-$SRV-P8.json
   done
   iperf3 -c 10.0.3.65 -p 5201 -t 180 -P 4 -i 10 -J > t1-b-sustained180-P4.json
   ```

   The table columns come from the JSON: `end.sum_sent.bits_per_second`, `retransmits`, `end.cpu_utilization_percent.host_total` / `remote_total`, and per stream `sender.mean_rtt` and `max_snd_cwnd`.

4. **Request latency** — fortio. Every run gets `-quiet -r 0.00001 -json -`:

   ```bash
   SRV=10.0.3.65   # repeat per path
   fortio load -quiet -r 0.00001 -json - -qps 100 -c 4 -t 60s http://$SRV:8080/                    # HTTP keepalive
   fortio load -quiet -r 0.00001 -json - -qps 100 -c 4 -t 30s -keepalive=false http://$SRV:8080/   # new connection per request
   fortio load -quiet -r 0.00001 -json - -qps 0 -c 16 -t 20s http://$SRV:8080/                     # qps 0 = unlimited, closed loop
   fortio load -quiet -r 0.00001 -json - -grpc -ping -qps 100 -c 4 -t 30s $SRV:8079                # gRPC ping
   ```

   **Do not drop `-r 0.00001`.** fortio's default histogram resolution is `-r 0.001`, i.e. 1 ms buckets. Every latency on this page is below 1 ms, so with the default every request lands in the first bucket and p50/p99 become linear interpolations inside that one bucket — p50 = 0.5 ms for anything under 1 ms. That is exactly what the first T2 run produced; its percentiles were discarded (the averages were valid) and the tables above are the rerun at 10 µs resolution. Anyone measuring sub-millisecond latency with fortio walks into this once.

5. **DNS** — deploy the two Pods from `bench-dns.yaml`; capture with the `sniffer` sidecar in one terminal while the `app` container resolves the name once cold and 20 times warm in another:

   ```bash
   kubectl apply -f bench-dns.yaml
   kubectl -n bench-net exec dns-default -c app -- cat /etc/resolv.conf        # confirm 4 search domains + ndots:5
   kubectl -n bench-net exec dns-ndots1  -c app -- grep ndots /etc/resolv.conf  # options ndots:1
   # terminal 1 — every DNS packet this Pod sends or receives
   kubectl -n bench-net exec dns-default -c sniffer -- tcpdump -i eth0 -nn udp port 53
   # terminal 2 — one cold resolution (count queries and NXDOMAIN in the capture above) + 20 warm timings
   kubectl -n bench-net exec dns-default -c app -- python3 - <<'PY'
   import socket, statistics, time
   name = "sts.ap-northeast-2.amazonaws.com"       # trailing-dot variant: name + "."
   def one():
       t = time.perf_counter()
       socket.getaddrinfo(name, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
       return (time.perf_counter() - t) * 1000
   print("cold ms", round(one(), 2))
   xs = sorted(one() for _ in range(20))
   print("warm min/median/p90/max", round(xs[0], 2), round(statistics.median(xs), 2), round(xs[int(len(xs)*0.9)-1], 2), round(xs[-1], 2))
   PY
   ```

   Repeat the same procedure against `dns-ndots1` for the bottom six rows of the table. The table measures the glibc resolver (`python:3.12-slim`); results with other resolvers (musl/alpine) were not measured, so use a glibc image to reproduce these numbers.

6. When finished, delete the namespace — `kubectl delete ns bench-net`. Karpenter removes the empty nodes.

## Caveats

- **The nodes were fresh, but not entirely alone.** Soon after Karpenter launched the three m5.xlarge nodes for this test, consolidation moved a few small Pods from other namespaces onto them (one onto the `cli` node, three onto the `srv-b` node — small internal services and controllers unrelated to the benchmark traffic). They were idle or low-traffic during the runs, and load was limited to bursts of at most 180 s. The `cli` node showed 3901m / 3920m (99 %) of CPU *requested*, which says nothing about actual utilisation.
- **Single run (n = 1 per cell, one day).** No repeats were made to estimate variance. Read the numbers as order-of-magnitude anchors, not SLAs, and rest conclusions on the ratios and patterns (the RTT ladder, the 5 Gbps flow cap, the 10 Gbps instance cap, 10 vs 2 queries).
- **ClusterIP (the kube-proxy iptables hop) and `trafficDistribution: PreferClose` could not be measured.** Every `kubectl apply` of a Service in the cluster was rejected with `Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`. The read-only diagnosis: `aws-load-balancer-controller` had been in CrashLoopBackOff for weeks, so the `failurePolicy: Fail` webhook behind it had zero ready endpoints — and until the controller recovers, no Service can be created anywhere in the cluster. The webhook was not bypassed for this benchmark; the fixture uses Pod IPs only. Symptom → diagnosis → fix is written up in the [Troubleshooting Playbook, entry 11 "No Service can be created: failed calling webhook"](../ops/16-troubleshooting-playbook.md#11-no-service-can-be-created-failed-calling-webhook).
- **ENA allowance counters were not collected.** `ethtool -S eth0 | grep allowance_exceeded` (`bw_in_allowance_exceeded`, `bw_out_allowance_exceeded`, `pps_allowance_exceeded`, `conntrack_allowance_exceeded`, `linklocal_allowance_exceeded`) needs a hostNetwork Pod on the node and was not run here. Retransmit counts are the indirect signal.
- **Burst-credit exhaustion was merely not observed within 180 s.** On "Up to" instances, longer sustained transfers may be throttled toward the baseline (1.25 Gbps). Nothing beyond 180 s was tested.
- **DNS latency includes CoreDNS cache effects.** The cold first resolution and the 20 warm repeats differ (`cache 30` caches NXDOMAIN as well), and external names traverse the VPC resolver. Comparisons between warm values are valid; the absolute values depend on cache state.
- **Same-node iperf3 is bound by one client core (99.8 %).** 29.97 / 48.15 Gbps are CPU figures for this instance family and will differ on others.
- **Other CNI modes were not compared.** Prefix delegation off, Security Groups for Pods off, network policy enforcing mode `standard` (the eBPF agent is present but the namespace has no policies). What changes when those settings change is not on this page.

## Related reading

- [Amazon VPC CNI](./01-vpc-cni.md) — the data plane under these measurements: Pods receiving VPC IPs directly, prefix delegation, ENI/IP warming
- [Zonal Cluster Operations](../ops/15-zonal-operations-guide.md) — zone-aligned placement and AZ failover design that reduce the bill in Measurement 3
- [Troubleshooting Playbook, entry 11 — No Service can be created: failed calling webhook](../ops/16-troubleshooting-playbook.md#11-no-service-can-be-created-failed-calling-webhook) — the outage that kept ClusterIP out of this benchmark
- [Sidecar vs Ambient Mode Selection Guide](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) — put the sidecar hop's +1.29 ms p50 next to the +0.21 ms AZ hop measured here
- [EBS gp2 vs gp3 Measured Benchmark](../storage/01-ebs-gp2-gp3-benchmark.md) — the storage path of the same cluster, measured
- [Kafka on EKS Measured Benchmark](../data-on-eks/kafka/09-kafka-benchmark.md) — how RF3 replication traffic meets this page's 5 Gbps flow cap and cross-AZ pricing
- [Guidebook Roadmap — the measured-benchmark series](../roadmap.md)
- [Quiz: Pod Network Benchmark](../quizzes/networking/06-pod-network-benchmark-quiz.md)
