# VPC Lattice Deep Dive Overview

> **Supported Versions**: Amazon VPC Lattice (GA), AWS Gateway API Controller v1.1+, Kubernetes 1.28+ (Amazon EKS)
> **Last Updated**: September 3, 2026

## What This Section Covers

- What actually changes when you move from a sidecar-proxy service mesh (App Mesh, Istio) to a **managed data plane** (VPC Lattice)
- How Lattice works internally — intercepting traffic via link-local addresses, SigV4 request signature verification, and triple auth policy evaluation
- The structural differences you hit when moving workload identity from SPIFFE/SPIRE to IAM, and why those become review board issues

## Why This Section Exists Separately

This section is about **understanding concepts**. How to create Lattice resources and install the AWS Gateway API Controller is already covered in [VPC Lattice](../../networking/02-vpc-lattice.md), and the feature-by-feature comparison with Istio lives in [Istio vs VPC Lattice](../istio/comparison/02-istio-vs-lattice.md). What those two documents do not cover is what this section addresses: **"why was it designed this way" and "what follows from that design."**

There is urgency behind it. **AWS App Mesh reaches end of support on September 30, 2026**, and after that date you can no longer access the App Mesh console or App Mesh resources. New customer onboarding has already been closed since September 24, 2024. For any organization running App Mesh, this migration is not a choice — it is a task with a deadline.

But App Mesh and Lattice are **not two implementations of the same thing.** The data plane sits in a different place (inside the Pod vs. AWS infrastructure), identity is proven at a different granularity (connection vs. request), and the root of trust is owned by a different party (customer CA vs. AWS IAM/STS). If you approach it by swapping resource names one at a time, you will discover functional gaps and failed security reviews late in the migration. The purpose of this section is to surface those gaps **first**.

## Audience and Assumptions

- AWS architects and customer infrastructure engineers
- We assume you already know EKS and Kubernetes
- We assume VPC Lattice and service mesh internals are new to you
- Code and manifest examples are kept to a minimum. This is not a hands-on lab guide

## Document Structure

| # | Document | Question it answers |
|---|----------|---------------------|
| 1 | [App Mesh vs VPC Lattice Architecture](./01-appmesh-vs-lattice.md) | When the data plane moves from the Pod into the infrastructure, what survives and what disappears? |
| 2 | [Latency Impact Analysis](./02-latency.md) | Both degrading and improving factors exist. Which one wins in our environment? |
| 3 | [IAM Authentication Flow in Detail](./03-auth-flow.md) | What happens across the four stages from signing a request to authorizing it? |
| 4 | [Foundations — Link-Local and SNI](./04-networking-basics.md) | How is traffic intercepted without a sidecar? What do you lose by not terminating TLS? |
| 5 | [Workload Identity Migration — SPIFFE to IAM](./05-spiffe-to-iam.md) | Can IAM do what SPIRE was doing? What is not replaced? |
| 6 | [Constraints and Decision Points](./06-constraints.md) | What must you answer before finalizing the design? |

Reading in order from 1 is recommended. Document 4 (link-local, SNI) is prerequisite knowledge for the constraints in 3 and 6 — it is placed later, but if network fundamentals are unfamiliar, read 4 first.

## A Note on Accuracy

The factual claims in this section are based on AWS official documentation, the AWS Gateway API Controller documentation, the `aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice` reference implementation, and the SPIFFE/SPIRE documentation.

Anything not confirmed against official documentation is not stated as fact — it is marked with a `Needs verification` block. Lattice is a service that keeps gaining features, and in particular **quotas and pricing vary by region and over time.** Before finalizing a design, check current values directly in the Service Quotas console and on the [VPC Lattice pricing page](https://aws.amazon.com/vpc/lattice/pricing/).

## Related Documents

- [VPC Lattice](../../networking/02-vpc-lattice.md) — Lattice resource configuration and Gateway API Controller installation
- [Gateway API](../../networking/04-gateway-api.md) — the Kubernetes Gateway API standard
- [Istio vs VPC Lattice](../istio/comparison/02-istio-vs-lattice.md) — feature, cost, and operational complexity comparison
- [Istio Security — mTLS](../istio/security/01-mtls.md) — how sidecar-based mutual authentication works
- [Pod Network Benchmark](../../networking/06-pod-network-benchmark.md) — measured same-AZ and cross-AZ latency baselines
