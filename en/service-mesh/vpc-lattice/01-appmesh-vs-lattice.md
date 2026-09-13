# App Mesh vs VPC Lattice Architecture

> **Scope**: VPC Lattice service/resource APIs and AWS Gateway API Controller; verify the selected release and installed CRDs.
> **Last Updated**: September 13, 2026

## What This Document Covers

- What problem each model — sidecar and managed data plane — was designed to solve
- How App Mesh resources map to Lattice resources, and why that mapping is not one-to-one
- The feature gaps that follow from the non-one-to-one parts, and what the AWS Gateway API Controller does in between

## Why the Two Models Were Designed Differently

### The sidecar model — put a proxy next to the application

App Mesh and Istio put an Envoy inside the Pod because **some decisions require the application's context.**

A caller-side proxy can maintain connection pools, observe upstream failures and apply configured retries. The exact controls depend on the product and its API; an Envoy capability is not automatically an App Mesh feature. A managed service can also maintain state, so proxy placement alone does not prove a feature is impossible.

The customer operates the injected Envoy workloads and any separately deployed SPIRE infrastructure. **AWS operates the App Mesh control plane.** Proxy upgrades and resource consumption remain customer workload concerns; do not describe App Mesh as a fully self-operated control plane.

### The managed data plane model — push the proxy into the infrastructure

Lattice went the other direction. It pulls the proxy out of the Pod and places it in **infrastructure that AWS operates.** The client Pod sends an ordinary HTTP request knowing nothing, and when that request is addressed to a Lattice service, the infrastructure intercepts and handles it.

The problems this design solves are scale and heterogeneity. Because there is no sidecar, proxies do not multiply with Pod count, and EKS, ECS, EC2, and Lambda can all participate in the service network **the same way.** You cannot put an Envoy inside a Lambda function, but an infrastructure-layer proxy can serve Lambda too. VPC and account boundaries — even overlapping IP ranges — are absorbed by the infrastructure.

Removing Envoy changes where resilience and telemetry are implemented. Compare the **currently exposed App Mesh and Lattice APIs**, then identify which controls must move into the application or another proxy. Do not infer AWS internal state placement or permanent feature limits from this conceptual topology.

## AS-IS / TO-BE Architecture

```mermaid
graph TB
    subgraph ASIS["AS-IS: App Mesh (sidecar model)"]
        direction TB
        subgraph P1["Pod A (caller)"]
            A1["app<br/>container"]
            A2["Envoy<br/>sidecar"]
            A1 -->|"localhost"| A2
        end
        subgraph P2["Pod B (receiver)"]
            B2["Envoy<br/>sidecar"]
            B1["app<br/>container"]
            B2 -->|"localhost"| B1
        end
        A2 ==>|"mTLS<br/>direct to Pod IP"| B2
        CM["AWS Cloud Map<br/>service discovery"]
        AM["App Mesh<br/>control plane"]
        SP["SPIRE Server/Agent<br/>SVID issuance"]
        AM -.->|"xDS config push"| A2
        AM -.->|"xDS config push"| B2
        SP -.->|"SDS: X.509 SVID"| A2
        SP -.->|"SDS: X.509 SVID"| B2
        CM -.->|"endpoint lookup"| A2
    end
```

```mermaid
graph TB
    subgraph TOBE["TO-BE: VPC Lattice (managed data plane model)"]
        direction TB
        subgraph P3["Pod A (caller)"]
            C1["app container<br/>no Envoy"]
        end
        subgraph LAT["AWS managed infrastructure"]
            L1["Lattice<br/>Listener + Rule"]
            L2["Target Group"]
            L1 --> L2
        end
        subgraph P4["Pod B (receiver)"]
            D1["app container<br/>no Envoy"]
        end
        C1 ==>|"HTTP/HTTPS<br/>addressed to 169.254.171.0/24"| L1
        L2 ==>|"Pod IP"| D1
        GW["AWS Gateway API<br/>Controller"]
        IAM["IAM / STS<br/>+ auth policy"]
        GW -.->|"watches Gateway/HTTPRoute<br/>creates Lattice resources"| L1
        GW -.->|"registers/deregisters Pod IPs"| L2
        IAM -.->|"SigV4 verification<br/>policy evaluation"| L1
    end
```

Three differences stand out.

1. **Number of proxy traversals**: AS-IS passes through **two** proxies — the caller's Envoy and the receiver's Envoy. TO-BE passes through Lattice **once.**
2. **Who owns the control plane**: In AS-IS, the App Mesh control plane pushes configuration to each Envoy via xDS and SPIRE issues certificates. In TO-BE these roles move into the AWS-managed domain, and all that remains in the customer cluster is a single Gateway API Controller Deployment.
3. **Where the connection terminates**: In AS-IS the caller's Envoy connects **directly to the receiver's Pod IP.** In TO-BE it connects to a Lattice address, and it is Lattice that knows the Pod IPs.

## Resource Mapping

| App Mesh | VPC Lattice | Relationship |
|---|---|---|
| **Mesh** | **Service Network** | Both are logical boundaries. An App Mesh mesh is not inherently Kubernetes-only; a Lattice service network associates services and VPCs, with resource connectivity as a separate capability. |
| **VirtualService** | **Lattice Service** | Logical service name. A Lattice Service gets its own DNS name |
| **VirtualRouter** + **Route** | **Listener** + **Listener Rule** | VirtualRouter's per-protocol routing role is absorbed by Listener; Route's match/action by Listener Rule |
| **VirtualNode** | **Target Group** | VirtualNode packed "this workload's identity + backend config + listener config" into one resource; a Target Group expresses only the **set of backend targets** |
| **AWS Cloud Map** | **Not needed** | Lattice has service discovery built in. Cloud Map namespace/service management disappears |
| **Envoy sidecar** | **Removed** | Gone from the Pod. The data plane moves to AWS infrastructure |
| **VirtualGateway** | **Lattice Service + Listener** (or ALB/NLB) | North-South traffic is out of scope for the Gateway API Controller. That is AWS Load Balancer Controller territory |

### Why you must not read this as a one-to-one table

**The VirtualNode row is the problem.** An App Mesh VirtualNode expressed three things at once — who this workload is (identity, including backend TLS settings), where it goes (backends), and where it receives (listeners, health checks, connection pools, outlier detection). In Lattice those three scatter to different places.

- Only **part of "where it receives"** (the target set, health checks) becomes a Target Group
- **"Where it goes"** stops being a resource and becomes a matter of **auth policies and IAM permissions**
- **"Who it is"** becomes an **IAM Role**, not an SVID ([document 05](./05-spiffe-to-iam.md))
- **Connection pools and outlier detection** have **no corresponding resource at all**

In other words, even where the right-hand column is filled in, not every attribute the left-hand resource held moves across. **The table maps resource names, not capabilities.**

## Feature Gaps

These are **migration checks**, not proofs of what a managed data plane can never implement. App Mesh, Istio and raw Envoy expose different configuration surfaces; verify the source feature actually used before choosing its replacement.

| Capability | Migration check |
|---|---|
| Connection limits, retries and outlier handling | Inventory the controls exposed by the actual source product. Lattice health checks do not reproduce every Envoy client-side policy; validate application resilience and retry budgets. |
| Fault injection and traffic mirroring | Do not label all Envoy/Istio capabilities as App Mesh features. Design a separate reviewed test/mirroring path when needed. |
| Health checks | Target-group health checks actively probe targets; they are not passive per-request outlier detection. |
| Client certificate identity | An HTTPS service listener and endpoint mTLS through TLS passthrough are different trust boundaries. See [networking](./04-networking-basics.md). |
| Metrics and traces | Retain application OpenTelemetry spans. Lattice access logs and CloudWatch metrics add request/target timing and correlation, but do not supply a native Lattice trace span. |

### How to read these gaps in practice

An important migration task is **observability**: inventory the metrics, access logs and trace context supplied by each existing component, and verify the replacement path end to end.

Circuit breakers and retries have a clear alternative — "add a library to the application" — with a cost you can estimate. Observability looks like it has a clear alternative too, but it is a different kind of work. In AS-IS, the spans Envoy produced automatically came **without touching application code.** Getting the same level of tracing in TO-BE means adding OpenTelemetry instrumentation to every service, and that becomes a work item for application teams.

A client span normally encloses the downstream server span, so subtracting the caller span end from the receiver span start is not a network-latency measurement. Correlate application spans with Lattice log fields such as `requestId`, `duration`, and `requestToTargetDuration` and `responseFromTargetDuration`; clock skew, instrumentation boundaries and network time limit causal attribution. Lattice adds `x-amzn-requestid` for HTTP correlation; that is not an OpenTelemetry span.

## The Role of the AWS Gateway API Controller

You can create Lattice resources directly with the CLI or console, but on EKS you normally use the **AWS Gateway API Controller.** It watches Kubernetes Gateway API resources inside the cluster and creates and deletes the corresponding Lattice resources.

| Kubernetes resource | Lattice resource created |
|---|---|
| `GatewayClass` (`amazon-vpc-lattice`) | — (declares Lattice as the data plane) |
| `Gateway` | Points to a **Service Network**. The Gateway name (without namespace) corresponds to the Service Network name; multiple Gateways sharing a name all point to the same Service Network |
| `HTTPRoute` / `GRPCRoute` | **Lattice Service** + **Listener Rule**. Each Route **gets its own domain name** |
| `TLSRoute` | A Lattice Service for TLS Passthrough (see [document 04](./04-networking-basics.md)) |
| The Service referenced by `backendRefs` | **Target Group** and the **Targets** in it |
| `TargetGroupPolicy` | Target Group protocol and health check settings |
| `IAMAuthPolicy` | Service network auth policy or service auth policy, depending on the attachment target ([document 03](./03-auth-flow.md)) |

### Why this controller is central to closing the gap

In App Mesh, Cloud Map and Envoy were what tracked Pod IPs. In Lattice, this controller plays that role.

The controller watches **endpoint changes** on the Kubernetes Services referenced by `backendRefs`. When a Deployment scales out and adds Pods, or a rolling update changes Pod IPs, the controller detects the change and **registers and deregisters** Targets in the Lattice Target Group. Keeping Kubernetes' declared state and Lattice's actual target list in sync is this controller's core job.

Two practical points follow.

**First, if the controller stops, the routing targets go stale.** Lattice keeps forwarding traffic, but newly started Pods are never registered as Targets and dead Pods are never deregistered. The availability and IAM permissions of the controller Deployment are directly tied to the reliability of the data path.

**Second, you can use Pod readiness gates.** You can make a Pod not be marked Ready until its Lattice Target Group health is `Healthy`, which makes a rolling update **not terminate old Pods until new Pods are healthy from Lattice's point of view.** This is an important mechanism for zero-downtime during migration.

### Scope limits of the controller

The Gateway API was designed to cover both North-South (Ingress) and East-West (Mesh) traffic, but **the AWS Gateway API Controller currently focuses only on East-West traffic through Lattice.** Do not expect ALB/NLB-style North-South features — those belong to the AWS Load Balancer Controller.

This matters especially in environments that also run ingress-nginx. The North-South traffic ingress-nginx handles is not in scope for this migration; only East-West traffic moves to Lattice. A configuration where both paths coexist is the normal outcome.

## Summary

- Compare product APIs and configured capabilities; moving the proxy changes responsibilities but does not prove immutable feature gaps.
- The resource mapping table maps names. The attributes VirtualNode held either scatter across several places or vanish.
- The most underestimated gap is observability. Spans that Envoy gave you for free become an instrumentation project.
- The AWS Gateway API Controller is what reflects Kubernetes endpoint changes into Lattice Targets, and its availability is tied to data path reliability.

Next: [Latency Impact Analysis](./02-latency.md) examines how fewer proxy hops and an added VPC traversal work against each other.

## References

- [Migrating from AWS App Mesh to Amazon VPC Lattice (AWS Containers Blog)](https://aws.amazon.com/blogs/containers/migrating-from-aws-app-mesh-to-amazon-vpc-lattice/)
- [aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice](https://github.com/aws-samples/migrating-from-aws-app-mesh-to-amazon-vpc-lattice)
- [AWS Gateway API Controller — Understanding the Gateway API Controller](https://www.gateway-api-controller.eks.aws.dev/latest/concepts/overview/)
- [AWS Gateway API Controller — Gateway API Reference](https://www.gateway-api-controller.eks.aws.dev/latest/api-types/gateway/)
- [Amazon VPC Lattice User Guide](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [App Mesh Document history](https://docs.aws.amazon.com/app-mesh/latest/userguide/doc-history.html)
