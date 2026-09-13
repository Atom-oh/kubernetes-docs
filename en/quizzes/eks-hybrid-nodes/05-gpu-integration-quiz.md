# EKS Hybrid Nodes GPU Integration Quiz

> **Related Document**: [GPU Integration](../../eks-hybrid-nodes/05-gpu-integration.md)
> **Last Updated**: September 12, 2026

### 1. Which statement correctly describes MIG?

A. It combines several physical GPUs into one

B. It creates supported hardware-backed compute/memory instances, while host/driver and application SLO considerations remain

C. It guarantees complete isolation for every tenant and every failure

D. It is identical to software time-slicing

<details>
<summary>Show Answer</summary>

**Answer: B. It creates supported hardware-backed compute/memory instances, while host/driver and application SLO considerations remain**

**Explanation:** MIG provides memory/fault and resource isolation at the GPU hardware layer. Supported profiles/limits depend on the GPU SKU and driver. This does not establish complete shared-host security or an application latency guarantee.

</details>

### 2. Which profile belongs in the common A10040GB table?

A. 4g.40gb

B. 4g.20gb

C. 4g.80gb

D. 1g means one entire physical GPU

<details>
<summary>Show Answer</summary>

**Answer: B. 4g.20gb**

**Explanation:** The A10040GB examples include1g.5gb,2g.10gb,3g.20gb,4g.20gb and7g.40gb.4g.40gb belongs to the A10080GB set. The g component counts profile compute slices; nominal memory labels are not exact usable-memory guarantees.

</details>

### 3. What does time-slicing replicas:4 provide?

A. Four physical GPUs and four private memory regions

B. Four logical access slots per configured GPU, sharing its memory/fault domain

C. A guaranteed quarter of compute for each Pod

D. Automatic GPU memory expansion

<details>
<summary>Show Answer</summary>

**Answer: B. Four logical access slots per configured GPU, sharing its memory/fault domain**

**Explanation:** Contention and workload behavior can change latency/throughput. More requested replicas do not guarantee proportional compute. renameByDefault:true advertises nvidia.com/gpu.shared; connect the configuration to the actual plugin rather than creating an unused ConfigMap.

</details>

### 4. What does current DRA add to GPU allocation?

A. GPU support without any vendor driver

B. Only static CPU and memory requests

C. Structured device selection/allocation through DeviceClasses and ResourceClaims

D. Automatic production validation of all GPU applications

<details>
<summary>Show Answer</summary>

**Answer: C. Structured device selection/allocation through DeviceClasses and ResourceClaims**

**Explanation:** A vendor driver, ResourceSlices, compatible kubelets/runtime and enabled APIs are still required. Current v1 claims use requests[].exactly, and Pod resourceClaims refer directly to resourceClaimTemplateName.

</details>

### 5. How should a current ResourceClaim be assessed?

A. Wait for a universal status.phase:Bound enum

B. Claim creation alone proves the GPU is usable

C. Inspect allocation.devices.results, reservations, Pod events and driver preparation

D. Inspect the old resourceHandles field only

<details>
<summary>Show Answer</summary>

**Answer: C. Inspect allocation.devices.results, reservations, Pod events and driver preparation**

**Explanation:** There is no universal stored Pending→Allocated→Bound phase sequence for current ResourceClaims. An allocation/reservation does not prove successful device injection or application execution.

</details>

### 6. Which GPU Operator26.7 ownership statement is correct?

A. GPUCluster and ClusterPolicy should always run together

B. Choose ClusterPolicy for device-plugin management or a new GPUCluster workflow for managed DRA; they cannot coexist

C. Setting driver.enabled:false installs a missing host driver

D. The controller nodeSelector automatically restricts every operand

<details>
<summary>Show Answer</summary>

**Answer: B. Choose ClusterPolicy for device-plugin management or a new GPUCluster workflow for managed DRA; they cannot coexist**

**Explanation:** GPUCluster is a cluster-scoped singleton named gpu-cluster. The managed DRA workflow is not an in-place migration from ClusterPolicy/standalone DRA. Prepare the appropriate driver/CDI/discovery components and review operand labels separately.

</details>

### 7. What does the H100SXM/H200SXM comparison establish?

A. Every H100 variant has identical memory

B. NVIDIA lists80GB/3.35TB/s for H100SXM and141GB/4.8TB/s for H200SXM; application results still require measurement

C. H200 does not support MIG

D. H200 always doubles every application's throughput

<details>
<summary>Show Answer</summary>

**Answer: B. NVIDIA lists80GB/3.35TB/s for H100SXM and141GB/4.8TB/s for H200SXM; application results still require measurement**

**Explanation:** These are vendor SKU specifications, not audit benchmarks. H100NVL/PCIe variants differ. Model size, precision, batching, software, interconnect and contention also affect actual performance.

</details>

### 8. Which EKS GPU deployment boundary is correct?

A. Install an extra NVIDIA device plugin on every Auto Mode node

B. DRA is unsupported on every kind of EKS node

C. Use a scoped Hybrid allocation cohort; current EKS Auto Mode does not support DRA and already manages its device plugin

D. Publish each physical GPU through as many managers as possible

<details>
<summary>Show Answer</summary>

**Answer: C. Use a scoped Hybrid allocation cohort; current EKS Auto Mode does not support DRA and already manages its device plugin**

**Explanation:** AWS recommends DRA for new supported EKS1.34+ static-capacity deployments. Use the documented driver prerequisites and prevent duplicate device ownership. Kubernetes API maturity is separate from individual vendor feature gates.

</details>

### 9. A container requests one DRA GPU. How should it set CUDA_VISIBLE_DEVICES?

A. Always set0,1,2,3

B. Set every physical index discovered on the host

C. Use the variable to request three extra GPUs

D. Let the device manager/runtime expose the assigned devices; do not override it with unrelated physical indices

<details>
<summary>Show Answer</summary>

**Answer: D. Let the device manager/runtime expose the assigned devices; do not override it with unrelated physical indices**

**Explanation:** Process-visible CUDA indices can differ from physical GPU indices. A manual override can hide or misidentify devices and does not grant additional GPUs. Multiple containers referencing one claim still share that one allocation.

</details>

### 10. What do the suspended smoke Jobs and local schema checks prove?

A. The GPU driver and model have been executed successfully

B. All GPU workloads meet their latency SLO

C. The reviewed manifests/configuration pass bounded local checks; real GPU validation requires owner approval and execution

D. No cleanup verification will be needed

<details>
<summary>Show Answer</summary>

**Answer: C. The reviewed manifests/configuration pass bounded local checks; real GPU validation requires owner approval and execution**

**Explanation:** Replace the intentionally unusable image with an approved digest and verify runtime/placement/security before unsuspending one Job. Capture results and verify claim unprepare/release during cleanup. nvidia-smi visibility alone is not a CUDA/LLM benchmark.

</details>

