# Latency Impact Analysis

> **Scope**: VPC Lattice service/resource APIs and AWS Gateway API Controller; verify the selected release and installed CRDs.
> **Last Updated**: September 13, 2026

## What This Document Covers

- Why migrating to Lattice introduces degrading and improving latency factors **at the same time**
- Why which side wins depends on your environment and cannot be predicted in advance
- What to measure, and how, so that you get an answer — a PoC measurement matrix

## First: this document does not give you numbers

The latency impact can differ by workload. Proxy processing, network paths, connection reuse, signing, credential refresh and policy evaluation can all change. **No Lattice latency measurements are supplied in this chapter**, so neither a magnitude nor a guaranteed direction is asserted.

Which one wins depends on things like: how much node CPU your Envoy sidecars currently consume, how short your requests are (the relative weight of fixed overhead), whether you use keepalive, whether you enable IAM Auth, and what fraction of your calls cross an AZ. These values differ per organization.

So the conclusion of this document is **"measure it," and the body of this document is "what to measure so that you get an answer."** Below, the factors are organized by sign and magnitude, followed by a measurement matrix that isolates them.

## Degrading Factors

### 1. A VPC network traversal is added

In AS-IS the caller's Envoy connected **directly to the receiver's Pod IP.** For a Pod on the same node, it never left the veth pair and never touched the NIC. In TO-BE the destination is a Lattice link-local address, and that traffic **goes through a Lattice ingress endpoint inside the VPC** before reaching the final target.

This difference is largest for **Pod-to-Pod communication that used to be on the same node.** A path that finished inside the kernel in AS-IS now leaves the node, traverses Lattice, and comes back. As a reference baseline, the [Pod Network Benchmark](../../networking/06-pod-network-benchmark.md) measured same-node RTT at 0.040 ms, same-AZ different-node at 0.339 ms, and cross-AZ at 0.544 ms. If any call path depended on same-node locality, that path is affected most.

### 2. SigV4 signing and verification overhead

Enabling IAM Auth adds two computations per request.

- Caller-side signing adds canonicalization and signature computation. Lattice requires `UNSIGNED-PAYLOAD`; do not benchmark generic payload hashing as required Lattice signing work.
- Lattice-side verification and enabled-policy evaluation add work. Measure the complete path rather than assuming a per-operation duration.

The real cost here may be less the crypto itself and more the **credential acquisition path.** SigV4 signing needs STS temporary credentials; those are cached, but a refresh happens at expiry. If the refresh is implemented so that it blocks the request path, the request at that moment absorbs the STS call latency in full. This barely shows up in p50 and **appears in the p99 tail** (see [document 03](./03-auth-flow.md)).

If you sign via an egress proxy, add the cost of one more proxy hop.

### 3. Possible cross-AZ traversal

Do not assume Lattice picks a Target in the caller's own AZ. If you were pinning traffic within an AZ using zone-aware routing or topology-aware hints in AS-IS, you must separately confirm whether that optimization survives.

::: note Documented AZ behavior
AWS describes AZ affinity for the service/resource address returned to the client, with alternatives if the AZ is unavailable. Backend targets may still span AZs; the target-group documentation describes round-robin routing. This does not guarantee a same-AZ backend. Measure the actual target placement in the PoC.

Separately, **on the billing side there is no additional inter-AZ charge for traffic through Lattice.** It is included in the data processing charge. So cross-AZ is **a latency factor but not an additional billing factor** in this migration.
:::

### 4. Change in TLS handshake pattern

In AS-IS, the mTLS connection between Envoys was a **long-lived connection.** You paid the handshake cost once and many requests flowed over it.

In TO-BE, where and how often the handshake happens changes. If the client opens a new connection per request, the handshake cost attaches to every request. In the benchmark above, disabling keepalive raised p50 from 0.461 → 1.079 ms same-AZ and 0.704 → 1.517 ms cross-AZ. **Whether connections are reused matters more than one proxy hop.**

This is why you must audit your applications' HTTP client settings (connection pool size, keepalive, idle timeout) during migration. It is not a Lattice characteristic — it is a client configuration issue that surfaces once the proxy that used to manage connections for you is gone.

## Improving Factors

### 1. Proxy traversals drop from two to one

A single request in AS-IS passes through a proxy **twice**: once at the caller's Envoy (routing decision, mTLS initiation, metrics) and once at the receiver's Envoy (mTLS termination, authorization, metrics). Each traversal is a full userspace receive-process-send cycle.

This removes the two **customer-managed sidecar traversals** in the illustrated path. Lattice internal implementation, signing proxies and changed network routes prevent treating this as a guaranteed reduction in end-to-end latency.

### 2. Envoy sidecar CPU contention goes away

This is the factor most often underestimated in practice.

There is one Envoy sidecar per Pod, and each consumes node CPU. When a node is under CPU pressure, the Envoy process waits to be scheduled, and that wait time is added directly to request latency. The characteristic of this phenomenon is that **it barely shows in the average and shows heavily in the tail.** Most requests are scheduled immediately; some wait milliseconds to tens of milliseconds.

Removing the sidecar removes the contention itself. So **on clusters with high Pod density and tight CPU, p99 may improve.** At the same time, more CPU and memory become available per node, creating room to increase Pod density.

### 3. Configuration convergence changes

AWS manages the Lattice data plane, but controller reconciliation, endpoint registration, health checks and policy propagation still take time. AWS documents that auth-policy updates can take a few minutes. Measure convergence and rollout behavior rather than assuming propagation delay disappears.

## Factor Summary — Sign and Where It Shows

| Factor | Sign | Metric where it appears | Conditions that amplify it |
|---|---|---|---|
| Added VPC network traversal | Degrades | Both p50 and p99 | High share of same-node/same-AZ traffic |
| SigV4 signing/verification | Degrades | p50 slightly, **p99** (credential refresh) | IAM Auth enabled, short requests |
| Cross-AZ traversal | Degrades | p50, p99 | You relied on AZ-aware routing |
| TLS handshake pattern change | Degrades | p50, p99 | No keepalive, no connection pool tuning |
| Sidecar removal | Potential improvement | p50, p99 | Depends on removed work, signing path and network topology |
| Envoy CPU contention removed | **Improves** | **p99** | Node CPU pressure exists |
| Configuration convergence | Must measure | Availability/latency during changes | Controller, target health and policy propagation |

The key point of this table is that **p50 and p99 have different factor compositions.** Degrading factors (added path) likely dominate p50; improving factors (removed CPU contention) may dominate p99. **Looking at the average alone hides this structure.**

## PoC Measurement Matrix

To observe these factors separately, split your measurements along axes.

### Measurement axes

| Axis | Values | Factor it isolates |
|---|---|---|
| **Percentile** | p50, p99 | Separates the added-path effect from the CPU-contention effect |
| **AZ placement** | Same AZ / Cross-AZ | Cross-AZ traversal cost, whether Lattice is AZ-aware |
| **IAM Auth** | on / off in an isolated approved test | Combined signing, credential and policy-evaluation effect |

AZ placement and auth mode are configuration axes; p50/p99 are two outputs from each run, not independent trials. Use repeated matched runs, randomize ordering where practical, and report errors/throughput as well as latency.

### Measurement table template

| Configuration | Same-AZ p50 | Same-AZ p99 | Cross-AZ p50 | Cross-AZ p99 |
|---|---|---|---|---|
| AS-IS: App Mesh (baseline) | | | | |
| TO-BE: Lattice, IAM Auth **off** | | | | |
| TO-BE: Lattice, IAM Auth **on** | | | | |

The auth-on/off delta is the **combined effect of signing, credential handling and enabled-policy evaluation under those conditions**. The App Mesh/Lattice delta includes proxy, routing, TLS and other configuration changes. Neither difference identifies a pure causal component without additional controls.

### Conditions you must record alongside

Recording only the numbers makes later interpretation impossible. Record these too.

| Item | Why |
|---|---|
| **keepalive usage and connection pool settings** | As shown, this can matter more than a proxy hop. If it differs between cells, the cells are not comparable |
| **Request/response payload sizes** | Changes the relative weight of fixed overhead. Overhead looks large on short requests |
| **Load level (RPS) and concurrency** | Behavior may change near quotas |
| **Node instance type and node CPU utilization during the run** | The basis for interpreting the CPU-contention effect. For AS-IS runs, record **the Envoy container's CPU usage separately** |
| **AS-IS sidecar resource requests/limits** | To determine whether throttling was occurring |
| **Measurement tool and settings** | `fortio`, `wrk2`, `k6`, etc. Percentile computation differs by tool |
| **Timestamp, region, and AZ** | Reproducibility |

### Commonly missed aspects of measurement design

**First, measuring without a warm-up mixes in credential acquisition and connection setup.** The first request includes both an STS call and a TLS handshake, so it does not represent steady state. Measure steady state after adequate warm-up and **record first-request latency as a separate item.** For workloads with frequent cold starts (Lambda, services that scale out often), that first-request number is actually the important one.

**Second, gather enough samples for p99 to be meaningful.** With few requests, p99 is noise. Use values taken after tens of thousands of requests under stable load.

**Third, account for call chain depth.** Single-hop measurements are useful for isolating factors, but real user latency is the sum across the chain. Overhead accumulates with each added Lattice hop, so **pick your deepest real call path and measure it end-to-end as well.** This perspective also ties directly to billing ([document 06](./06-constraints.md)).

**Fourth, your ability to observe the Lattice hop directly is limited.** Lattice does not create trace spans, so you will be correlating client-side measurements with Lattice access logs. Make sure **enabling access logs** is part of your measurement plan.

## Conclusion

- This chapter supplies a measurement design, not measured Lattice latency or a guaranteed improvement.
- p50 may degrade while p99 may improve. Judging from a single average hides this structure.
- keepalive and connection pool settings can matter more than the proxy hop change. Auditing client configuration is mandatory during migration.
- Compare AZ/auth configurations with repeated matched runs; report p50/p99, failures and throughput for each run.

Next: [IAM Authentication Flow in Detail](./03-auth-flow.md) covers what SigV4 overhead actually consists of and the credential dependency behind it.

## References

- [Pod Network Benchmark](../../networking/06-pod-network-benchmark.md) — measured same-node/same-AZ/cross-AZ RTT and keepalive impact
- [Amazon VPC Lattice pricing](https://aws.amazon.com/vpc/lattice/pricing/) — inter-AZ included in data processing
- [Access logs for Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [Monitoring Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-overview.html)


The linked Pod benchmark is a separate workload baseline. Its HTTP keepalive numbers are not measurements of TLS handshakes or Lattice itself.