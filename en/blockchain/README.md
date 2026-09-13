# Blockchain Overview

> **Last Updated**: September 12, 2026

## What This Section Covers

- What kind of workload a blockchain is **from an infrastructure engineer's perspective** — why its operational characteristics differ from ordinary stateful services
- What you actually hit running blockchain nodes on Kubernetes (EKS) — storage, P2P networking, synchronization, upgrades
- The boundary between managed (Amazon Managed Blockchain) and self-operated, and how that choice shifts in financial services

## Why This Section Is in This Repository

This repository is Kubernetes and EKS training material. Blockchain is here because **a blockchain node is an unusual workload for a Kubernetes operator.**

Most Kubernetes workloads are one of two kinds — stateless, so you can kill and restart freely, or stateful but pushable onto a managed service (RDS, ElastiCache). A blockchain node is **neither.**

| Common assumption | For a blockchain node |
|---|---|
| "Pods are replaceable at any time" | Rebuilding hundreds of GB to several TB of local state can take **days** |
| "Scaling out increases throughput" | Replicas can scale RPC reads and availability, but do not automatically raise the base chain’s write/consensus capacity |
| "If the health check passes, it can serve" | A node behind on sync passes the health check while **returning wrong data** |
| "Rolling updates give zero-downtime deploys" | Fork-compatible releases can be canaried/rolled out before activation; the protocol deadline and post-fork rollback compatibility are separate constraints |
| "Restore data from backups" | State is replayable from the chain, but **lose the keys and it is over** |

These differences drive real operational decisions. Covering them is the purpose of this section.

## Audience and Assumptions

- Infrastructure engineers and architects with EKS/Kubernetes operations experience
- **We assume blockchain is new to you** — document 1 explains the concepts from scratch
- Smart contract development, token economics, and investment judgment are out of scope. This is **an infrastructure operations perspective**

## Document Structure

| # | Document | Question it answers |
|---|----------|---------------------|
| 1 | [Blockchain Fundamentals](./01-fundamentals.md) | What are consensus, Merkle trees, P2P, and finality — and why do these operational characteristics follow from that design? |
| 2 | [Running Blockchain Nodes on EKS](./02-nodes-on-eks.md) | How do you actually handle StatefulSets, storage, P2P, sync, and upgrades? |
| 3 | [Amazon Managed Blockchain](./03-managed-blockchain.md) | What does managed take off your hands, and what can it not do? What does the shift in AWS's ledger services imply? |
| 4 | [Financial Services Perspective](./04-financial-services.md) | What are the real issues in consortium governance, privacy, regulation, and integration with existing infrastructure? |

Document 1 is prerequisite for 2–4. If blockchain is familiar you can start at 2, but **the "where the operational characteristics come from" section in document 1** is needed to follow document 2.

## A Note on Accuracy

This section has two kinds of uncertainty, handled differently.

**① Fast-moving protocol specifications** — use announced activation dates rather than assuming a fixed upgrade cadence. Hardware, staking and blob handling can change; figures below are dated guidance, not guaranteed current requirements.

**② Figures that are not primary sources** — values like node hardware requirements are often community or vendor estimates rather than official specifications. Such values are marked with the nature of their source and given as ranges.

Anything not confirmed against official documentation is left in a `Needs verification` block. **Before a production design, check current values directly in the protocol's official documentation and client release notes.**

## Related Documents

- [Cluster Architecture](../core/01-cluster-architecture.md) — etcd and consensus (Raft), a reference point for comparing with blockchain consensus
- [Pods and Workloads](../core/02-pods-and-workloads.md) — StatefulSets
- [Storage](../core/04-storage.md) / [EKS Storage](../eks/04-eks-storage-part1.md) — PV/PVC and EBS
- [EBS gp2 vs gp3 Benchmark](../storage/01-ebs-gp2-gp3-benchmark.md) — what IOPS actually means
- [EKS Node Kernel Tuning](../kernel/03-eks-node-tuning.md) — file descriptors, socket buffers
- [Data on EKS Overview](../data-on-eks/README.md) — stateful data workloads generally
- [EKS Resiliency](../eks/10-eks-resiliency.md) — failure domain design
