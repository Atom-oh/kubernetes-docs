# AI Infrastructure on EKS Quiz

15questions on current APIs and operational boundaries.

## 1. What is JARK, and is it automatically complete?

<details>
<summary>Answer and explanation</summary>

An integration pattern of JupyterHub/Argo Workflows/Ray/Karpenter. Explicitly connect identities, submissions, execution, Pod placement, node supply, storage and authorization.
</details>

## 2. What must be configured for JupyterHub with Cognito?

<details>
<summary>Answer and explanation</summary>

Callback/token/userInfo URLs, scopes, stable username claims and allow policies. Read the client secret from a prepared file; configure MFA/federation in the provider separately. Successful authentication does not imply universal access.
</details>

## 3. What are the roles of the Ray head and Karpenter?

<details>
<summary>Answer and explanation</summary>

GCS is Global Control Service; scheduling interacts with raylets. A head advertising CPUs may run work. Karpenter provisions nodes based on worker-Pod demand and Kubernetes scheduling state.
</details>

## 4. How should DRA and device plugins be compared?

<details>
<summary>Answer and explanation</summary>

DRA provides structured requests, attributes and allocation through DeviceClass/ResourceSlice/ResourceClaim. Device plugins also support MIG/time-slicing; they are not universally exclusive-only. Features depend on drivers, hardware and gates.
</details>

## 5. What matters about MIG profiles and isolation?

<details>
<summary>Answer and explanation</summary>

3g.20gb describes one profile, not three20GB devices. MIG partitions hardware but does not replace host/driver/authorization isolation. MPS/time-slicing are not security boundaries.
</details>

## 6. Can one GPU Operator version establish all DRA support?

<details>
<summary>Answer and explanation</summary>

No. Check Kubernetes APIs, drivers/hardware/CDI and individual gates. Operator26.7 GPUCluster is mutually exclusive with ClusterPolicy; standalone0.5 has an opt-in guard against device-plugin collisions.
</details>

## 7. What should be checked when integrating Langfuse?

<details>
<summary>Answer and explanation</summary>

Verify current SDK/backend dependencies, DB/ClickHouse/object storage, file credentials, tracing and sensitive-data retention. Old2.x Deployments or trace() calls are not current4.x APIs.
</details>

## 8. How should EFS, FSx and Mountpoint be selected?

<details>
<summary>Answer and explanation</summary>

Compare I/O, authorization, namespace/PVC scope, capacity and filesystem semantics. EFS requests are not quotas; Mountpoint CSI2.8 uses static PVs for existing buckets and is not fully POSIX.
</details>

## 9. How should EFA bandwidth and interface counts be interpreted?

<details>
<summary>Answer and explanation</summary>

Distinguish aggregate instance bandwidth from per-interface values; do not multiply an already aggregate figure. Verify same-AZ placement, interfaces, drivers/libfabric/NCCL, security groups and Pod resources. RAID0 does not enable EFA.
</details>

## 10. How should GPU memory and XID metrics be interpreted?

<details>
<summary>Answer and explanation</summary>

FB_USED/FREE are MiB gauges; a high ratio is not necessarily OOM. XID_ERRORS is the last code gauge, not a counter for increase(). Investigate actual errors, caches, allocation failures and device-specific limits.
</details>

## 11. Does Karpenter consolidation directly use GPU utilization metrics?

<details>
<summary>Answer and explanation</summary>

It uses workload requests, scheduling feasibility, prices and disruption constraints rather than a DCGM20% threshold. Limits/budgets are not absolute cost/failure guarantees; verify termination and recovery.
</details>

## 12. Who publishes ResourceSlices, and what do they represent?

<details>
<summary>Answer and explanation</summary>

Drivers publish real device inventory with typed attributes/capacity. Creating an arbitrary slice does not create GPUs. CEL and matchAttribute must follow the actual published schema.
</details>

## 13. Does requesting a GPU for Milvus complete RAG?

<details>
<summary>Answer and explanation</summary>

No. Match supported images/indexes, embedding dimensions/revisions, metrics/parameters, tenant filtering and update/deletion lifecycle. Validate result authorization and handle absent evidence.
</details>

## 14. How should pending GPU Pods and node failures be investigated?

<details>
<summary>Answer and explanation</summary>

Counting pending GPU-requesting Pods does not diagnose the cause. Inspect events, PVCs, affinity, taints, quotas, claims and images, and test checkpoint/resume. Multiple requesting containers count once per Pod.
</details>

## 15. Does MCP provide a standard Kubernetes auto-discovery gateway?

<details>
<summary>Answer and explanation</summary>

No. It defines operations such as tool listing/calling. Choose an actual server/gateway release, transport and authorization design. Invented images/labels/config or a URL environment variable do not implement discovery/execution.
</details>

[Return to guide](../../ai-ml/06-ai-infrastructure.md)
