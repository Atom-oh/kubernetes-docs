# AI/ML Workloads Quiz

Review allocation, training/serving, storage, networking, security, observability and cost boundaries.

## Quiz Questions

### 1. How should a Pod request GPUs exposed by the NVIDIA device plugin?

- A. Set only requests with nvidia.com/gpu:0.5
- B. Specify integer nvidia.com/gpu limits, with an equal request if also supplied
- C. Add only an nvidia.com/gpu node annotation
- D. Name a RuntimeClass nvidia-mps to enable sharing automatically

<details>
<summary>Show Answer</summary>

**Answer: B. Specify integer nvidia.com/gpu limits, with an equal request if also supplied**

Limits alone imply an equal request. Allocatable GPU capacity is not a node label. GPU Feature Discovery labels, MIG, MPS and time-slicing require separate configuration; a shared slot does not guarantee a fraction of GPU memory.

[Allocation and sharing](../../ai-ml/01-ai-ml-workloads.md#nvidia-gpu-operator-and-device-allocation)
</details>

### 2. Which installed legacy Kubeflow resource understands TensorFlow distributed roles?

- A. Deployment automatically creates all TF_CONFIG values
- B. Job guarantees training success and simultaneous worker placement
- C. TFJob provides framework-specific roles/configuration
- D. TFJob is built into Kubernetes and needs no installation

<details>
<summary>Show Answer</summary>

**Answer: C. TFJob provides framework-specific roles/configuration**

Install its CRD/controller and configure restart policy, framework strategy, checkpoints, storage and networking. Recovery and gang scheduling are not universal guarantees. A regular Job can also train when actual execution code is supplied.

[Trainer and legacy APIs](../../ai-ml/kubeflow/05-training-operator.md)
</details>

### 3. How should an existing FSx for Lustre filesystem be connected through CSI?

- A. Combine a Lustre CR and a StorageClass containing the existing ID
- B. Use a static PV with volumeHandle/dnsname/mountname and a bound PVC
- C. SCRATCH_2 supports every persistent backup/throughput option
- D. FIO against unmounted /data measures FSx

<details>
<summary>Show Answer</summary>

**Answer: B. Use a static PV with volumeHandle/dnsname/mountname and a bound PVC**

Static attachment differs from dynamic filesystem creation. Compare capacity, IOPS/throughput, latency, access patterns, permissions, AZ/network and backups. Benchmark a dedicated test path on the actual mounted volume.

[Static and dynamic storage](../../ai-ml/01-ai-ml-workloads.md#storage-and-caching)
</details>

### 4. What should guide AI/ML resource allocation?

- A. Every training job requires a GPU
- B. Measured CPU/memory/GPU use, model size, I/O, latency and throughput
- C. Always request maximum resources
- D. Omitting requests is always most efficient

<details>
<summary>Show Answer</summary>

**Answer: B. Measured CPU/memory/GPU use, model size, I/O, latency and throughput**

CPU and other accelerators can be appropriate. OMP/MKL thread settings affect supporting libraries, not GPU sharing. CUDA allocator settings differ from Kubernetes GPU allocation/isolation. VPA effects depend on mode, restart behavior and workload compatibility.

[Resource placement](../../ai-ml/01-ai-ml-workloads.md#placement-and-topology)
</details>

### 5. What should be checked when selecting a serving platform such as KServe?

- A. Any model URI immediately works
- B. Runtime image, model format, protocol, storage and deployment mode match requirements
- C. A normal Deployment cannot serve inference
- D. All modes offer identical canary and scale-to-zero behavior

<details>
<summary>Show Answer</summary>

**Answer: B. Runtime image, model format, protocol, storage and deployment mode match requirements**

A Deployment can run an inference server. KServe Knative/Standard and versioned Seldon APIs differ. Explainability, processing, weighted routing and batch inference are not universally enabled defaults. TorchServe is not a maintained default for new use.

[KServe modes and runtimes](../../ai-ml/kubeflow/06-kserve.md)
</details>

### 6. What is required for HPA scaling on GPU utilization or request load?

- A. Allocated nvidia.com/gpu automatically becomes a utilization Resource metric
- B. Exporters and custom/external metrics adapters with correct labels, units and aggregation
- C. Increase replicas to fix low model accuracy
- D. Attach several HPAs to the same Deployment for additive scaling

<details>
<summary>Show Answer</summary>

**Answer: B. Exporters and custom/external metrics adapters with correct labels, units and aggregation**

The standard metrics-server Resource path exposes CPU/memory. GPU/request metrics need separate collection/adapters. Pod metrics must map to namespace/Pod labels; a global average can lose that mapping. Use one scaling owner and validate whether load/queue is a better proportional signal than latency percentiles.

[HPA example](../../ai-ml/01-ai-ml-workloads.md#hpa-and-metrics)
</details>

### 7. Which statement about distributed-training networking is correct?

- A. A zone annotation alone controls placement
- B. GPU hostPath mounts configure EFA/GPUDirect
- C. Validate node-label placement, hardware, drivers/plugins, communication libraries and network policies together
- D. NCCL always transports data through MPI

<details>
<summary>Show Answer</summary>

**Answer: C. Validate node-label placement, hardware, drivers/plugins, communication libraries and network policies together**

NCCL over EFA uses AWS OFI NCCL and libfabric; MPI can launch processes. Multus/SR-IOV, MTU and RDMA configuration are environment-specific. Generic NIC examples are not turnkey EKS settings. NetworkPolicy can affect availability/performance by blocking required traffic.

[Distributed-training boundaries](../../ai-ml/01-ai-ml-workloads.md#kubeflow-and-distributed-training)
</details>

### 8. Which model/data protection statement is correct?

- A. Secret base64 is encryption
- B. Kubernetes RBAC grants S3/KMS permissions
- C. Configure API RBAC, workload IAM, encryption/key management, file credentials and networking separately
- D. Store large models in Secrets and decryption keys in environment variables by default

<details>
<summary>Show Answer</summary>

**Answer: C. Configure API RBAC, workload IAM, encryption/key management, file credentials and networking separately**

Secrets have size limits and base64 is encoding. Use object storage with authorization/integrity checks for large models. A Pod service account does not always need Secret get permission to mount a Secret volume: API reads and kubelet volume delivery differ. PodSecurityPolicy was removed; use current admission/PSS controls.

[Data and model access](../../ai-ml/01-ai-ml-workloads.md#data-and-model-access)
</details>

### 9. What should ML service observability distinguish?

- A. GPU utilization determines accuracy
- B. ServiceMonitor selects Pod labels directly
- C. Service errors/latency/throughput, resource use and ground-truth model quality are separate
- D. All container logs are Docker JSON

<details>
<summary>Show Answer</summary>

**Answer: C. Service errors/latency/throughput, resource use and ground-truth model quality are separate**

ServiceMonitor selects Service labels/named ports. Define whether latency includes failures and avoid counting one request as both success and error. Quality needs labels/ground truth. Validate CRI framing versus app JSON, Grafana datasource/panel schema, labeled alert aggregation and zero-traffic behavior.

[Metrics and logs](../../ai-ml/01-ai-ml-workloads.md#prometheus-and-grafana)
</details>

### 10. How should cost optimization be validated?

- A. Use Spot for every workload
- B. Newest instances are always cheapest
- C. Measure required performance, total cost, interruption recovery/checkpointing and actual Pod/node reclamation
- D. Nighttime automatically lowers On-Demand rates

<details>
<summary>Show Answer</summary>

**Answer: C. Measure required performance, total cost, interruption recovery/checkpointing and actual Pod/node reclamation**

Fewer Pods do not imply EC2 termination. Check availability, quotas, AMI/drivers and NodePool limits. Training taints need matching tolerations; mixed CPU/GPU groups are not EKS Hybrid Nodes. Creating an unused Autoscaler ConfigMap does not change controller flags.

[Spot and node provisioning](../../ai-ml/01-ai-ml-workloads.md#spot-and-node-provisioning)
</details>

---

[Return to Learning Materials](../../ai-ml/01-ai-ml-workloads.md)
