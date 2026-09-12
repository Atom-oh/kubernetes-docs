# Running Blockchain Nodes on EKS

> **Supported Versions**: Kubernetes 1.33+ (Amazon EKS), Hyperledger Fabric 2.5 / 3.x
> **Last Updated**: September 12, 2026

## What This Document Covers

- Translating the operational characteristics from [Fundamentals](./01-fundamentals.md) into actual Kubernetes configuration — StatefulSets, storage, P2P exposure
- How to put sync state into health checks, and why ordinary health checks do not work
- The operational differences between Ethereum nodes and Hyperledger Fabric, and how to manage hard fork schedules

## Opening Question — Should You Run This on EKS?

Before discussing configuration, this question comes first. **Blockchain nodes fit poorly with some of Kubernetes' strengths.**

| What Kubernetes does well | For a blockchain node |
|---|---|
| Fast scheduling and rescheduling | State rebuild cost makes rescheduling expensive |
| Horizontal scaling for throughput | Throughput does not increase |
| Declarative rolling updates | Hard forks switch simultaneously |
| Moving Pods between nodes | Bound to local disk |

There are still reasons to use EKS.

| Reason | Content |
|---|---|
| **Operational standardization** | If you already run everything on EKS, not adding a separate stack is better |
| **Multiple chains/environments** | Mainnet, testnets, and several protocols managed the same way |
| **Integration with surrounding components** | Indexers, API gateways, and monitoring are already in the cluster |
| **Official direction for Fabric** | Hyperledger Fabric has a mature Kubernetes operator ecosystem |

**Conversely, plain EC2 is better when** you have only a few nodes (1–3) and no other cluster workloads. Then EKS's abstraction adds complexity without benefit. Running a single validator does not require EKS.

**The decision criterion**: **is there other workload around the blockchain node?** If indexers, APIs, and monitoring are in the cluster, keeping the node with them is sensible; if the node stands alone, EC2 is simpler.

## Base Configuration — StatefulSet and Headless Service

### Why not a Deployment

| Requirement | Deployment | StatefulSet |
|---|---|---|
| Stable name (P2P identity) | ✗ random suffix | ✓ `node-0`, `node-1` |
| Per-Pod fixed volume | ✗ shared or random | ✓ per-Pod PVC via `volumeClaimTemplates` |
| Stable DNS | ✗ | ✓ with a headless Service, `node-0.svc...` |
| Ordered startup/shutdown | ✗ | ✓ |

The "stable peer identity" and "per-Pod state" requirements from [Fundamentals](./01-fundamentals.md) are exactly what StatefulSets provide.

### Minimal skeleton

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: eth-node
spec:
  serviceName: eth-node          # headless Service name
  replicas: 2
  template:
    spec:
      terminationGracePeriodSeconds: 300   # graceful shutdown needs time
      containers:
        - name: execution
          # ... execution client
          ports:
            - { name: p2p-tcp, containerPort: 30303, protocol: TCP }
            - { name: p2p-udp, containerPort: 30303, protocol: UDP }
            - { name: rpc,     containerPort: 8545 }
          volumeMounts:
            - { name: data, mountPath: /data }
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: gp3-high-iops
        resources: { requests: { storage: 2Ti } }
```

Three things differ from ordinary workloads.

**① `terminationGracePeriodSeconds` is long.** Blockchain clients must flush in-memory state to disk on shutdown. A forced kill can **corrupt the database and require a resync.** The default 30 seconds is usually not enough.

**② P2P ports are both TCP and UDP.** Many protocols separate discovery (UDP) from actual connections (TCP). Open only one and you either cannot find peers or cannot connect.

**③ The volume is large.** Covered in the storage section below.

## Storage — The Most Important Design Decision

### What the bottleneck is

A blockchain node's disk pattern is characterized by **heavy random reads and writes**, because traversing and updating the state trie (Merkle Patricia Trie and similar) touches scattered keys.

So **IOPS becomes the bottleneck before capacity.** With capacity to spare but insufficient IOPS, sync falls behind — and a node that is behind cannot serve.

| Requirement | Why |
|---|---|
| **High IOPS** | Random access pattern |
| **Low latency** | State lookups sit on the block-processing path |
| **Sustained throughput** | Continuous load, not bursts |

### Choosing an EBS volume

| Volume type | Suitability |
|---|---|
| **gp3** | Default choice. The key advantage is **setting IOPS and throughput independently of capacity** |
| **io2 / io2 Block Express** | When you need higher IOPS and more consistent latency |
| **gp2** | Not recommended — IOPS is tied to capacity and cannot be adjusted |
| **Instance store (NVMe)** | Fastest but **lost when the instance stops** — only if you can accept a resync |

**Why gp3's independent settings matter**: gp2 fixes IOPS per unit of capacity, so raising IOPS meant buying capacity you did not need. gp3 sets capacity and IOPS separately, so **you can match actual needs.** See the [EBS gp2 vs gp3 Benchmark](../storage/01-ebs-gp2-gp3-benchmark.md) for concrete differences.

**The instance store trade-off** is clear — best performance but state can vanish. Choose it if you can accept the resync time (you have a snapshot-restore process) and you run multiple nodes so one resyncing does not break service.

### Capacity planning — growth is the point

Chain data grows **monotonically.** That changes the nature of capacity planning.

| Item | Implication |
|---|---|
| Continuous growth | **A volume expansion plan is mandatory** — you will need it eventually |
| Growth rate depends on protocol activity | Leave headroom and set alarms |
| Pruning options | Clients offer modes that discard old data — use them if you do not need archive |

**EBS volumes support online expansion** (followed by a filesystem grow), so the standard response is a StorageClass with `allowVolumeExpansion: true` plus disk-utilization alarms.

::: warning Needs verification
Commonly cited estimates for Ethereum node disk requirements are roughly **0.9–1.3 TB for the execution client, 80–200 GB for the consensus client, and an additional 100–150 GB for blob data** (community and vendor estimates as of early 2026).

**These figures are not official AWS or Ethereum Foundation specifications — they come from third-party blogs and vendor material, and they vary considerably by client, pruning configuration, and fork.** Size against the official documentation and release notes for the client you will use, and measure the growth rate yourself in a PoC.
:::

### Snapshot strategy

As seen in [Fundamentals](./01-fundamentals.md), **chain data is re-obtainable from the network but takes time.** So the purpose of a backup is not "preserving data" but **"shortening recovery time."**

| Method | Characteristics |
|---|---|
| **EBS snapshots** | Whole volume. Consider initialization latency (lazy loading) on restore |
| **Client snapshot export** | Client-provided export. Consistency guarantees are explicit |
| **Resync** | No backup, start over — a time cost |

**A caution**: snapshotting a running node's volume directly can capture **a database mid-write.** For a consistent snapshot you must stop the client or use a consistency mechanism the client provides.

## Health Checks — Why the Ordinary Approach Fails

This is **the most frequently misconfigured part** of blockchain node operations.

### The problem

An ordinary health check asks "is the process responding." For a blockchain node that is **insufficient and dangerous.**

A node behind on sync:

- Has its RPC port open and responds → liveness passes
- But **answers based on a stale chain state** → returns wrong data
- The Service sends it traffic → the application sees wrong balances and state

### The correct split

| Probe | What it should check |
|---|---|
| **startup** | Initial sync is in progress — it takes a long time, so **a generous `failureThreshold`** |
| **liveness** | The process is alive and responding — **do not check sync here** (killing a lagging node means it can never catch up) |
| **readiness** | **Within N blocks of the chain head** — whether it can serve |

**The liveness/readiness split is decisive.**

- Put sync in liveness → a lagging node gets restarted → falls further behind → an infinite loop
- Leave it out of readiness → a lagging node takes traffic and returns wrong answers

### Implementation direction

Sync state is checked via the client's RPC. The method differs per protocol and client, so judging it with a wrapper script or sidecar is the usual approach.

```yaml
# Conceptual form — the actual judgment logic differs per client
readinessProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-sync.sh"]   # block delta vs head
  periodSeconds: 15
  failureThreshold: 3

livenessProbe:
  httpGet: { path: /, port: rpc }     # responsiveness only
  periodSeconds: 30
  failureThreshold: 5

startupProbe:
  exec:
    command: ["/bin/sh", "-c", "/scripts/check-alive.sh"]
  periodSeconds: 30
  failureThreshold: 240               # allow a long initial sync
```

**The threshold (N blocks) must be set from application requirements.** Decide it together with the confirmation depth from [Fundamentals](./01-fundamentals.md).

## P2P Exposure — Accepting Inbound Connections

### Why inbound matters

Sync works with outbound only. But accepting inbound:

- Increases peer count, making **propagation faster and more stable**
- Contributes to the network (mutually beneficial on public chains)

It matters especially for validators — block propagation delay directly affects performance (rewards).

### Methods and trade-offs

| Method | Characteristics |
|---|---|
| **`hostNetwork: true`** | Simplest. The Pod uses the node IP and ports directly. **One per node** constraint, a security-review item |
| **`hostPort`** | Maps only specific ports to the node. Requires managing port conflicts per node |
| **NodePort Service** | Kubernetes standard. Port-range constraints, node-IP advertisement issues |
| **Per-Pod LoadBalancer (NLB)** | Stable address. **LB cost per Pod** |
| **Skip inbound** | Outbound only. Simple configuration, degraded peer quality |

### A common pitfall — the advertised address

P2P protocols **advertise** their own address to other peers. If the address seen inside the container (the Pod IP) differs from the externally reachable address (node public IP, LB address), **other peers cannot connect.**

Most clients offer an option to specify the advertised address (`--nat extip:<addr>` and similar). **Without it, opening inbound brings no peers** — the classic cause of "I opened it and nothing happened."

Since each Pod must advertise a different address, you need initialization logic where each Pod discovers its own address via the StatefulSet ordinal or the downward API.

## Resources — Sustained Load, Not Bursts

Blockchain nodes **use CPU and IOPS steadily.** Blocks keep arriving, verification keeps happening, state keeps updating.

| Item | Recommendation |
|---|---|
| **CPU limit** | **Be careful.** Throttling turns into block-processing delay, and for validators performance ties to rewards. See the throttling diagnosis in [Kernel Tuning](../kernel/03-eks-node-tuning.md) |
| **Memory** | Clients use a lot of memory for state caches. **Be generous with limits** — OOM risks DB corruption |
| **request = limit** | Guaranteed QoS lowers eviction priority |
| **Dedicated nodes** | Separate from other workloads with taints/tolerations — prevents noisy neighbors |
| **File descriptors** | A socket per peer connection. Consider raising the limit ([Kernel Tuning](../kernel/03-eks-node-tuning.md)) |

**The CPU limit judgment matters most.** As seen in the [kernel documents](../kernel/01-container-primitives.md), a CPU limit is a bandwidth limit, so exhausting the quota within a period forces a stop. If block processing lands in that window, latency appears — and for a validator, a missed opportunity.

At the same time, without a limit a node can consume the whole machine. **The resolution is dedicating nodes and giving generous requests** — on a dedicated node, no limit still harms no other workload.

## Ethereum Nodes — A Two-Client Structure

After Ethereum's move to PoS, a node is **two processes.**

| Client | Role | Examples |
|---|---|---|
| **Execution client** (EL) | Transaction execution, state management, EVM | Geth, Nethermind, Besu, Erigon, Reth |
| **Consensus client** (CL) | PoS consensus, block proposal and attestation | Prysm, Lighthouse, Teku, Nimbus, Lodestar |

They communicate over the **Engine API** and share a JWT secret.

### Placement decision

| Approach | Pros and cons |
|---|---|
| **Two containers in one Pod** | Simple `localhost` communication, scheduled and restarted together. Resources requested together |
| **Separate StatefulSets** | Independent scaling and upgrades. Requires managing the Engine API connection |

**One Pod is the default choice** — the two clients operate as a 1:1 pair and Engine API latency affects performance, so `localhost` within a Pod is natural.

**Client diversity** is also worth mentioning. So that a bug in one client does not affect the whole network, the community recommends distributing clients. If you run several nodes, using **different client combinations** is defensive.

### Recent protocol changes with operational impact

::: warning Needs verification
The following are **facts as of their stated dates.** Ethereum moved to a twice-yearly hard fork schedule in 2025, so **there may be further changes since.** Before designing, check the current state in the [ethereum.org roadmap](https://ethereum.org/roadmap/) and your client's release notes.

| Date | Upgrade | Operational significance |
|---|---|---|
| **May 7, 2025** | **Pectra** mainnet | **EIP-7251** raised the validator max effective balance (MaxEB) from **32 ETH to 2,048 ETH**. Multiple validators can be consolidated into one → **fewer validator instances to operate** |
| **December 3, 2025** | **Fusaka** mainnet (epoch 411392) | The headline is **PeerDAS** (Peer Data Availability Sampling) — verifying blob data by sampling rather than in full. Expands blob throughput |
:::

**The MaxEB change has large operational significance.** Previously, increasing stake meant adding validators in 32 ETH units, each a separate key and process. Consolidation means **fewer keys and instances to manage** — operational burden and infrastructure cost drop together.

**PeerDAS affects storage and bandwidth planning.** A change in blob handling changes how much data a node retains and transfers, so existing sizing baselines should be revisited.

## Hyperledger Fabric — Operating a Permissioned Chain

Fabric is different in character. Being **a consortium chain with known participants**, its consensus and operational characteristics differ, as seen in [Fundamentals](./01-fundamentals.md).

### Components

| Component | Role | Kubernetes placement |
|---|---|---|
| **Peer** | Holds the ledger, runs chaincode, validates transactions | StatefulSet + persistent volume |
| **Orderer** | Orders transactions (Raft consensus) | **StatefulSet + persistent volume mandatory** |
| **CA** (Fabric CA) | Issues member certificates | Deployment + persistent volume |
| **Chaincode** | Smart contracts | External builder or separate Pods |

### Operational points

**① The orderer's persistent volume is non-negotiable.** Losing the Raft log breaks consensus state. Pods restart on updates, so **operating without a persistent volume loses data.**

**② Certificate management is the core task.** Fabric manages organizations and identities via MSP (Membership Service Provider), and all communication is TLS. What you must manage:

- MSP signing certificates and keys
- TLS certificates (for peers, orderers, and the CA each)
- **Expiry management** — certificate expiry causes real outages

**Certificate expiry is cited as the most common cause of Fabric outages.** Automating renewal and setting expiry alarms is mandatory. Integrating with external PKI such as HashiCorp Vault is also used in practice.

**③ Use an operator.** Fabric has a Kubernetes operator ecosystem.

| Operator | Characteristics |
|---|---|
| [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) | CNCF operator pattern. CA, Peer, Orderer, and Console declared as CRs |
| [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric) | From the Hyperledger Bevel project. Supports Fabric 2.3–3.x |

An operator turns repetitive configuration into applying declarative resources. **Starting with an operator is recommended over assembling YAML by hand** — Fabric's configuration complexity makes manual management error-prone.

### Ethereum vs Fabric

| Item | Ethereum node | Hyperledger Fabric |
|---|---|---|
| **Participation** | Permissionless | Permissioned (MSP) |
| **Consensus** | PoS | Raft (orderer) |
| **Finality** | Checkpoint-based | Immediate (orderer settles) |
| **Main operational burden** | Sync, disk growth, hard forks | **Certificate expiry**, channel and policy management |
| **P2P exposure** | Inbound recommended | Inter-organization connections (known endpoints) |
| **Storage growth** | Large, monotonic | Relatively small (depends on transaction volume) |
| **Upgrades** | External schedule (hard forks) | Decided by consortium consensus |

**The biggest operational difference**: Ethereum must meet **an externally set schedule** (hard forks), while Fabric lets **the consortium set the schedule.** In exchange, Fabric requires an agreement process among members.

## Managing Hard Fork Schedules

[Fundamentals](./01-fundamentals.md) called a hard fork "a migration with a deadline." As a practical procedure:

| Step | Content |
|---|---|
| **1. Subscribe** | Protocol official blog, client release notes, operator communities |
| **2. Register the date** | Put the fork block/time on the team calendar. **Set a target date with margin** |
| **3. Validate on testnet** | Testnets fork before mainnet — validate there |
| **4. Prepare images** | Build and scan images on a fork-supporting version |
| **5. Upgrade sequentially** | **Complete before** the fork point. With several nodes, one at a time |
| **6. Monitor at the fork** | Chain height, peer count, whether the fork was recognized |
| **7. Verify afterward** | That all nodes are on the same chain |

**Easily missed**: a node left on a version that does not support the fork **silently splits onto a different chain.** The process is healthy and it keeps processing blocks, but it sees a different reality from the rest of the network. That is why steps 6 and 7 matter — **compare block hashes against other nodes and a public explorer right after the fork.**

## Monitoring

| Category | Metric | Why |
|---|---|---|
| **Sync** | Block delta vs chain head | The core of whether it can serve |
| **Sync** | Block processing latency | An early signal of starting to fall behind |
| **P2P** | Peer count | A sharp drop means a network or configuration problem |
| **P2P** | Inbound/outbound ratio | Zero inbound means exposure configuration failed |
| **Storage** | Disk utilization and growth rate | Predicting when to expand |
| **Storage** | IOPS, queue depth, latency | Confirming the bottleneck |
| **Consensus** | Reorg occurrences | Must be surfaced to the application |
| **Validator** | Participation rate, missed duties | Directly tied to rewards |
| **Fabric** | **Time remaining until certificate expiry** | Outage prevention |
| **Resources** | CPU throttling (`nr_throttled`) | [Kernel documents](../kernel/01-container-primitives.md) |

**"Block delta vs chain head" is the single most important metric.** When it starts growing you must find the cause (IOPS, CPU, peers, network), and past a threshold the node should drop out of readiness.

## Summary

- **First decide whether to run this on EKS.** The criterion is whether other workload surrounds the node. A node standing alone is simpler on EC2.
- **StatefulSet + headless Service + persistent volume** is the base skeleton, and `terminationGracePeriodSeconds` must be generous (a forced kill risks DB corruption).
- For storage, **IOPS bottlenecks before capacity.** gp3's independent capacity/IOPS settings are the key advantage, and a volume expansion plan is mandatory.
- **Health checks are the most frequently misconfigured part.** Sync in liveness causes a restart loop; leaving it out of readiness returns wrong data. The split is decisive.
- When opening inbound P2P, **forgetting the advertised address means no peers arrive.**
- Resources are sustained load, not bursts. **Dedicate nodes and decide CPU limits carefully.**
- Ethereum has an **EL + CL two-client** structure, and Pectra's MaxEB increase (32 → 2,048 ETH) means **fewer validators to operate.**
- Fabric's main operational burden is **certificate expiry.** Start with an operator and automate renewal.
- After a hard fork, **compare block hashes with other nodes and explorers** to confirm you are on the same chain.

Next: [Amazon Managed Blockchain](./03-managed-blockchain.md) examines how much of this burden managed services can take.

## References

- [Ethereum — Run a node](https://ethereum.org/developers/docs/nodes-and-clients/run-a-node/)
- [Ethereum roadmap](https://ethereum.org/roadmap/) / [Pectra](https://ethereum.org/roadmap/pectra/) / [Fusaka](https://ethereum.org/roadmap/fusaka/)
- [Pectra Mainnet Announcement (Ethereum Foundation)](https://blog.ethereum.org/2025/04/23/pectra-mainnet)
- [Fusaka Mainnet Announcement (Ethereum Foundation)](https://blog.ethereum.org/2025/11/06/fusaka-mainnet-announcement)
- [Hyperledger Fabric — Deploying a production network](https://hyperledger-fabric.readthedocs.io/en/latest/deployment_guide_overview.html)
- [hyperledger-labs/fabric-operator](https://github.com/hyperledger-labs/fabric-operator) / [bevel-operator-fabric](https://github.com/hyperledger-bevel/bevel-operator-fabric)
- [EBS gp2 vs gp3 Benchmark](../storage/01-ebs-gp2-gp3-benchmark.md) / [EKS Node Kernel Tuning](../kernel/03-eks-node-tuning.md)
