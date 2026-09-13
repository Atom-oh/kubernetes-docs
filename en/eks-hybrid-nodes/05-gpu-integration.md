# GPU Server Integration

< [Previous: Node Bootstrap](./04-node-bootstrap.md) | [Table of Contents](./README.md) | [Next: Workload Placement](./06-workload-placement.md) >

> **Supported Versions**: DRA GPU examples require Kubernetes 1.34.2+ on a supported EKS version. Reviewed interfaces: GPU Operator 26.7.0, DRA driver 0.5.0, device plugin 0.20.0.
> **Last Updated**: September 12, 2026

This chapter integrates prepared NVIDIA GPU hosts with EKS Hybrid Nodes. It covers allocation, GPU Operator ownership, MIG and time-slicing. **No GPU, driver installation, model download or inference benchmark was executed for this audit.** The examples require an approved OS/kernel/driver/toolkit/runtime/image combination and testing on the actual hardware.

## Choose one allocation owner per GPU

| Path | Prerequisites and allocation |
|---|---|
| Standalone NVIDIA device plugin | Prepared host driver, NVIDIA Container Toolkit and runtime; advertises extended resources such as `nvidia.com/gpu` |
| Standalone DRA driver | Prepared driver and CDI runtime; publishes ResourceSlices and allocates through DeviceClass/ResourceClaim |
| GPU Operator with `ClusterPolicy` | Operator-managed device-plugin workflow; ownership of driver/toolkit/MIG components must match what is already installed |
| GPU Operator 26.7 with `GPUCluster` | Operator-managed DRA workflow for a new installation; mutually exclusive with `ClusterPolicy` in the cluster |

AWS recommends DRA for new EKS 1.34+ deployments with supported static-capacity provisioning. **EKS Auto Mode does not currently support DRA** and already manages its GPU device plugin. The standalone examples below target only the identified Hybrid GPU nodes; do not install duplicate allocation managers on Auto Mode or other GPU nodes.

Use disjoint, owner-managed labels such as `workload.example.com/gpu-allocation=device-plugin` or `dra`. Those labels are scheduling inputs, not a security boundary or proof of healthy GPU hardware. Verify that there is no other plugin/Operator publishing the same physical devices before enabling either path.

## Prepare and verify the host cohort

- Complete [Node Bootstrap](./04-node-bootstrap.md), including Hybrid identity, CNI and time synchronization.
- Check the GPU model/form factor, firmware, driver branch, OS/kernel and runtime against NVIDIA's matrix and AWS Hybrid OS support. A newer NVIDIA matrix does not mean that EKS offers every Kubernetes version listed there.
- Verify the actual NVIDIA driver and toolkit are installed. Being on premises does not imply that a driver exists.
- For the legacy example, prepare an existing `RuntimeClass` named `nvidia` backed by the configured containerd NVIDIA runtime handler. The class name alone does not configure the handler.
- For DRA 0.5.0 GPU allocation, the released prerequisite guide requires Kubernetes **1.34.2+**, a standalone driver **565+**, Toolkit **1.18+** and CDI-enabled runtime. The GPU Operator DRA workflow requires a driver **580+**. These are compatibility floors, not current patch/branch recommendations.
- Prepare discovery labels through the approved NFD/GFD installation or host inventory process. Do not deploy a second discovery controller simply because an example enables one.

The following operator-run check reads host GPU metadata; it is not a CUDA or LLM benchmark:

```bash
nvidia-smi --query-gpu=name,driver_version,uuid,memory.total --format=csv,noheader
```

An output showing `cpu: 128`, `memory: 1024Gi`, `nvidia.com/gpu: 8` in the earlier example was an **unverified illustration**, not a measurement from this audit. Kubernetes GPU capacity can represent physical GPUs, MIG instances or time-slicing replicas, depending on configuration.

## Standalone device plugin on selected Hybrid nodes

The following values require the preinstalled driver/runtime and an existing compatible discovery setup. The two node-selector labels are combined with the chart's GPU-discovery affinity. If no node matches, fix the inventory/labels; do not remove affinity just to obtain running Pods.

```yaml
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  workload.example.com/gpu-allocation: device-plugin
runtimeClassName: nvidia
migStrategy: none
failOnInitError: true
deviceListStrategy: envvar
gfd:
  enabled: false
nfd:
  enabled: false
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

Save as `device-plugin-values.yaml`. The reviewed chart is **0.20.0**; verify the desired upgrade path and image compatibility before deployment:

```bash
# Cluster write; installs a privileged infrastructure component.
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" get nodes \
  -l 'eks.amazonaws.com/compute-type=hybrid,workload.example.com/gpu-allocation=device-plugin' \
  -o json > plugin-nodes.json
jq -e '.items | length > 0 and
  all(.[]; .metadata.labels["nvidia.com/mps.capable"] != "true")' plugin-nodes.json
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update nvdp
helm install hybrid-gpu-plugin nvdp/nvidia-device-plugin \
  --version 0.20.0 --namespace gpu-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values device-plugin-values.yaml --wait --timeout 10m
```

Use a namespace and release owned by the GPU infrastructure operator. Review rendered RBAC, host paths, privilege, registry access and tolerations. A Helm `--wait` success is not proof of CUDA compatibility or workload performance.

The published 0.20.0 chart also renders an MPS control DaemonSet, restricted by `nvidia.com/mps.capable=true` plus the selected Hybrid cohort. This exclusive-GPU example stops if such a label is already set. Investigate existing MPS ownership instead of clearing the label blindly; do not assume the chart contains only one DaemonSet.

## Standalone DRA on a separate Hybrid GPU cohort

The current driver project is **`kubernetes-sigs/dra-driver-nvidia-gpu`**. DRA API stability, EKS support and individual vendor feature maturity are separate checks. Current NVIDIA 26.7 documentation identifies full-GPU and existing-MIG allocation as GA; dynamic MIG, MPS, some sharing and NVML allocation-health features have separate Alpha gates. Do not enable all feature gates to make a demo start.

The older prose in the tagged repository README describes GPU allocation as unsupported. The released prerequisite/install documentation and current NVIDIA capability table provide the newer, feature-specific guidance. Record the exact version and support contract for a production deployment.

The example disables ComputeDomains because ordinary H100/H200 allocation does not require Multi-Node NVLink orchestration. ComputeDomains have additional Grace Blackwell/MNNVL, IMEX and discovery requirements.

```yaml
gpuResourcesEnabledOverride: true
nvidiaDriverRoot: /
resources:
  gpus:
    enabled: true
  computeDomains:
    enabled: false
featureGates: {}
kubeletPlugin:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
    workload.example.com/gpu-allocation: dra
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  containers:
    gpus:
      resources:
        requests:
          cpu: 50m
          memory: 128Mi
        limits:
          cpu: "1"
          memory: 512Mi
webhook:
  enabled: false
```

Save as `dra-values.yaml`. This path assumes the host driver root is `/` and CDI is configured. An Operator-installed driver typically uses a different root; do not copy this value into that deployment.

```bash
# Alternative cluster write, only for the separately selected DRA cohort.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}"
helm install hybrid-gpu-dra \
  oci://registry.k8s.io/dra-driver-nvidia/charts/dra-driver-nvidia-gpu \
  --version 0.5.0 --namespace gpu-dra-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values dra-values.yaml --wait --timeout 10m
```

`gpuResourcesEnabledOverride=true` is still required by this chart for GPU resources. Its presence is not a claim that every GPU feature is Alpha. The optional admission webhook is disabled in this minimal example; enabling it requires reachable webhook endpoints and validated TLS/cert-manager or existing-secret configuration.

### GPU Operator alternative and ownership

Use the Operator when its managed component lifecycle matches the intended installation. `driver.enabled=false` is appropriate **only if the host driver is already verified**. Similarly, disable toolkit management only after the required runtime configuration is prepared. Operator upgrades can change drivers, validators, resource advertisement and node availability.

For **new Operator-managed DRA**, the documented values include:

```yaml
clusterPolicy:
  deployCR: false
gpuCluster:
  deployCR: true
driver:
  enabled: false
nfd:
  enabled: false
draDriver:
  computeDomains:
    enabled: false
```

This fragment assumes an approved preinstalled driver, CDI runtime and discovery installation. GPUCluster does not automatically provide the toolkit/MIG-management behavior of ClusterPolicy. Review the complete chart values for **26.7.0**, then deploy through the cluster's GPU owner.

`GPUCluster` is a cluster-scoped singleton named `gpu-cluster`. It cannot coexist with `ClusterPolicy`. An in-place migration from ClusterPolicy or a standalone DRA Helm release to GPUCluster is not supported by this workflow; use the documented new-installation path. Do not install an additional standalone DRA release for an Operator-managed deployment.

An Operator controller's `nodeSelector` does **not** restrict every operand. Operand placement uses GPU discovery and `nvidia.com/gpu.deploy.*` labels; review excluded cloud/Auto Mode GPUs and future nodes as well. If that boundary cannot be maintained, use an isolated cluster or the appropriately scoped standalone path.

GPUCluster reconciliation can run GPU validators and allocate claims. Its readiness status and DCGM telemetry are not equivalent to DRA device-allocation health: `NVMLDeviceHealthCheck` is Alpha and disabled by default in this release.

## Current DRA manifests

These examples use **`resource.k8s.io/v1`**. Kubernetes 1.31's former alpha shape is not a drop-in manifest for current clusters. DRA needs a working vendor driver, ResourceSlices, compatible kubelets/runtime and the enabled API; a DeviceClass by itself does not discover GPUs.

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-full-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu"
---
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-large-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu" &&
          device.capacity["gpu.nvidia.com"].memory.isGreaterThan(quantity("40Gi"))
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: single-large-gpu
  namespace: ai-workloads
spec:
  spec:
    devices:
      requests:
        - name: gpu
          exactly:
            deviceClassName: hybrid-large-gpu
            allocationMode: ExactCount
            count: 1
```

The `type == "gpu"` selector excludes MIG and VFIO devices published under the same `gpu.nvidia.com` driver. The second class selects **more than 40 GiB** of advertised memory; it is not an H100/H200-only selector. Inspect the ResourceSlice for the actual capacity and NVML `productName`. A GFD node label such as `NVIDIA-H200` need not equal the DRA product-name attribute.

DeviceClass has no `suitableNodes` field in this API. Constrain workloads with their node selector/affinity and let DRA match devices and node availability. The request uses `requests[].exactly`; Pod claims refer directly to `resourceClaimTemplateName`, without the old `source` wrapper.

## Bounded GPU smoke Jobs

Use an approved namespace (for example `ai-workloads`) and a tested image **pinned by digest** that works with the selected driver/runtime, non-root UID and read-only root filesystem. The placeholder image below is deliberately unusable. Both Jobs are **suspended by default**, so applying them does not start GPU work.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-plugin-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      runtimeClassName: nvidia
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: device-plugin
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              nvidia.com/gpu: 1
            limits:
              cpu: 500m
              memory: 256Mi
              nvidia.com/gpu: 1
---
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-dra-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: dra
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
            claims:
              - name: gpu-resource
      resourceClaims:
        - name: gpu-resource
          resourceClaimTemplateName: single-large-gpu
```

The first Job is for the exclusive legacy-device-plugin example; the second is for the separate DRA cohort. Do not request the same GPU through both mechanisms. A single DRA claim is one allocation even if multiple containers reference it.

After the owner replaces the image, verifies placement/runtime/security and approves the GPU test, unsuspend only the intended Job through the normal deployment process. Capture its result before TTL cleanup. The 120-second deadline bounds the Job after it starts, not the duration of image preparation or an external maintenance operation.

Do not set `CUDA_VISIBLE_DEVICES=0,1,2,3` for a one-device claim. The device manager/runtime supplies the assigned devices; CUDA's process-visible indices may differ from physical GPU indices. A manual override can hide or misidentify the allocation and does not grant extra GPUs.

`nvidia-smi -L` confirms device visibility only. Validate a bounded CUDA operation and the actual application separately on approved hardware; no such execution or performance result is claimed here.

## MIG and time-slicing

MIG partitions supported GPUs into hardware-backed compute/memory instances. It provides stronger resource and memory/fault isolation than time-slicing, but does not turn a shared host/driver into a complete security boundary or guarantee an application's latency SLO. Supported profiles and instance limits depend on GPU SKU and driver.

Common **A100 40 GB** profiles include:

| Profile | Nominal profile memory | Maximum instances of that profile |
|---|---|---|
| `1g.5gb` | 5 GB | 7 |
| `2g.10gb` | 10 GB | 3 |
| `3g.20gb` | 20 GB | 2 |
| `4g.20gb` | 20 GB | 1 |
| `7g.40gb` | 40 GB | 1 |

`4g.40gb` belongs to the **A100 80 GB** profile set; the old quiz mixed these SKU tables. `1g` refers to the profile's GPU compute slice count, not a count of physical GPUs. Nominal memory labels are not an exact usable-memory guarantee. Mixed profile placement has additional geometry constraints.

Enabling/reconfiguring MIG is an owner-controlled maintenance operation and can interrupt GPU workloads. The baseline standalone-plugin values above use `migStrategy: none`; changing a Pod request to `nvidia.com/mig-1g.5gb` does not create the MIG instance. Prepare the actual MIG geometry and the plugin's appropriate strategy first.

Time-slicing advertises multiple **logical access slots**, not physically separated GPUs or memory partitions. For example, a separately reviewed device-plugin configuration could use:

```yaml
# Fragment of device-plugin configuration, not a Kubernetes resource.
version: v1
sharing:
  timeSlicing:
    renameByDefault: true
    failRequestsGreaterThanOne: true
    resources:
      - name: nvidia.com/gpu
        replicas: 4
```

Connect this configuration to the plugin through its named ConfigMap/config selection and the intended nodes; an unattached ConfigMap changes nothing. With `renameByDefault: true`, the advertised resource is `nvidia.com/gpu.shared`. Do not use the exclusive-GPU smoke request unchanged against that shared resource.

Four replicas do not reserve four independent memory regions, and requesting more tickets does not guarantee proportional compute. Contention, context switches and workload behavior can affect latency/throughput; measure rather than assume one fixed cause. Time-slicing has no memory/fault isolation between replicas. Inference is not automatically safe to oversubscribe, and training is not universally incompatible with sharing.

## H100/H200 specification context

| NVIDIA specification | H100 **SXM** | H200 **SXM** |
|---|---|---|
| GPU memory | 80 GB HBM3 | 141 GB HBM3e |
| Published memory bandwidth | 3.35 TB/s | 4.8 TB/s |
| MIG | Up to 7, model-specific profiles | Up to 7, model-specific profiles |

These are vendor hardware specifications, not measurements of this Kubernetes environment. H100 NVL/PCIe variants have different capacity/bandwidth; do not generalize the SXM row to every H100. Larger memory can help a workload fit, but actual inference/training performance also depends on model, precision, batching, software, interconnect and contention.

## Inspect allocation and clean up safely

Use the explicit administrator kubeconfig/context and keep hardware/Pod diagnostics private:

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceslices -o json > gpu-slices.json
jq '[.items[] | select(.spec.driver == "gpu.nvidia.com") |
  {name: .metadata.name, node: .spec.nodeName,
   devices: [.spec.devices[] | {name, attributes, capacity}]}]' gpu-slices.json
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceclaims -n ai-workloads -o json > gpu-claims.json
jq '[.items[] | {name: .metadata.name,
  allocation: .status.allocation.devices.results,
  reservedFor: .status.reservedFor}]' gpu-claims.json
```

Current ResourceClaims do not have a universal stored `Pending → Allocated → Bound` phase enum. Check allocation results, reservations, Pod scheduling/events and driver preparation. A reservation is not proof that the container used the GPU successfully. The old `resourceHandles` example is not the current structured-allocation shape.

Use the workload names/labels actually rendered by your chosen driver release when inspecting logs. Operator-managed DRA and a standalone DRA release do not necessarily share the old `app=nvidia-dra-driver` selector.

Delete only the owned test Jobs/Pods after capturing results; verify generated claims are released and devices are unprepared. Retained claims or finalizers can outlive a stopped container. Do not remove the DRA kubelet plugin while workloads still need it to unprepare claims.

For Operator-managed DRA, follow its ordered Helm hook/finalizer teardown. Do not use `helm uninstall --no-hooks` or blindly strip finalizers/force-delete shared claims. Reconcile a failed cleanup with the resource owner before reusing the hardware.

## Primary references

- [AWS NVIDIA device management](https://docs.aws.amazon.com/eks/latest/userguide/device-management-nvidia.html)
- [AWS Hybrid inference: scoped device plugin](https://aws.amazon.com/blogs/containers/run-genai-inference-across-environments-with-amazon-eks-hybrid-nodes/)
- [GPU Operator platform/component matrix](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html)
- [GPU Operator DRA/GPUCluster workflow](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/dra-intro-install.html)
- [DRA driver 0.5.0 prerequisites](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [DRA ResourceSlice attributes](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/reference/resourceslice-attributes.md)
- [Kubernetes DRA](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/)
- [NVIDIA device plugin 0.20.0](https://github.com/NVIDIA/k8s-device-plugin/tree/v0.20.0)
- [MIG profiles](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-mig-profiles.html) and [time-slicing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- [H100 specifications](https://www.nvidia.com/en-us/data-center/h100/) and [H200 specifications](https://www.nvidia.com/en-us/data-center/h200/)

< [Previous: Node Bootstrap](./04-node-bootstrap.md) | [Table of Contents](./README.md) | [Next: Workload Placement](./06-workload-placement.md) >
