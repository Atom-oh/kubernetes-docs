# Workload-Specific Optimization

> **Supported Versions**: EKS Auto Mode GA; examples reviewed for EKS 1.36
> **Last Updated**: September 12, 2026

Match placement and recovery policy to the workload, then validate actual capacity, performance and cost. The web and batch examples are bounded lab configurations. The GPU examples are **inactive configuration templates**, not validated training/inference applications: inference has zero replicas and the legacy training job is suspended. No GPU/model execution, live cluster deployment or benchmark was performed.

Use the account/context guard in [Operations](./05-operations.md). All pools are dynamic; they do not reserve physical capacity. Select only the examples needed, review the `default`/custom NodeClass identity and subnet access, and account for ongoing node/storage costs. Taints and selectors provide placement control, not a tenant-security boundary.

## Web Services: Availability and Recovery

On-Demand avoids Spot reclaim events but does not guarantee capacity or availability. Replicas, topology, readiness, disruption policy, durable state and tested failure recovery are still needed.

This example uses three replicas and a PDB permitting one voluntary eviction when all three are healthy, instead of assuming `N-1` is a literal PDB value. The old ten-replica example was a sizing choice, not a universal requirement. The nginx image/digest and non-root configuration match the reviewed operations example. The probes serve `/` on 8080; an arbitrary application image does not necessarily implement `/health`.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: workload-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '32'
    memory: 128Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 20
          failureThreshold: 3
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: web-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: web-tier
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            app: web-frontend
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-frontend
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-frontend
```

The hard zone spread requires at least two eligible domains; missing capacity can leave Pods Pending. The soft hostname spread is a preference, not one replica per node or a three-AZ guarantee. Check matching labels, subnet coverage and failure policy.

A startup probe protects slow initialization from premature liveness checks. Readiness controls endpoint eligibility; liveness restarts a container. Choose application-specific thresholds and avoid liveness checks that restart every replica because a shared dependency is unavailable. The illustrative probe timing here is not a measured startup SLA.

## Batch: Retry Is Not Checkpoint Recovery

Use Spot only for jobs that can tolerate interruption, missed deadlines and unavailable Spot capacity. There is no On-Demand fallback in this pool. `restartPolicy: OnFailure` can restart a failed container on a surviving Pod; it does not recover lost process memory from a terminated node. `SPOT_AWARE=true` is just an environment variable unless an application implements it.

The following Indexed Job prints a logical shard number as a **smoke example**. It has two-way parallelism, five completions, a deadline and bounded retries instead of the former 20-parallel/100-completion sizing example. It is not a data-processing implementation. The reviewed BusyBox image index includes Linux amd64/arm64; no image was run during this audit.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-smoke
  namespace: workload-lab
spec:
  completionMode: Indexed
  parallelism: 2
  completions: 5
  backoffLimit: 2
  activeDeadlineSeconds: 300
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: indexed-smoke
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: processor
        image: busybox:1.37.0@sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0
        command:
        - /bin/sh
        - -ec
        args:
        - printf 'logical shard=%s; smoke only\n' "$JOB_COMPLETION_INDEX"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: 100m
            memory: 32Mi
          limits:
            cpu: 500m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: batch-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: batch-tier
        effect: NoSchedule
```

Real jobs need idempotent output commits, durable checkpoints and resume logic. Even Indexed Jobs can execute an index more than once in some failure cases; do not assume exactly-once side effects. Export required logs/artifacts before TTL cleanup. Node-local caches and emptyDir are not durable checkpoints.

`WhenEmpty` can clean up a node after eligible application work is gone; a 30-second `consolidateAfter` is a debounce, not a guarantee that a running job completes or that the node disappears after 30 seconds. Drift, expiration and interruption remain separate lifecycle paths.

## GPU Inference: Check the Whole Node Shape

Auto Mode manages NVIDIA drivers/device support and Bottlerocket images. It does not support the former `amiFamily: AL2023` or `blockDeviceMappings` NodeClass fields.

| Instance | GPUs | GPU memory | Host vCPU / RAM |
|----------|------|------------|-----------------|
| g5.xlarge | 1 A10G | 24 GB | 4 / 16 GiB |
| g5.2xlarge | 1 A10G | 24 GB | 8 / 32 GiB |
| g5.4xlarge | 1 A10G | 24 GB | 16 / 64 GiB |
| g5.12xlarge | 4 A10G | 96 GB total, 24 GB each | 48 / 192 GiB |
| p5.48xlarge | 8 H100 | 640 GB total, 80 GB each | 192 / 2 TiB |

These are examples, not a list of the newest or universally available GPU instances. Aggregate GPU memory is not one contiguous device's memory. In particular, the old Pod's 4 CPU/16Gi requests cannot fit a g5.xlarge after node/system reservations and DaemonSet overhead. This inference pool allows larger G5 shapes and avoids selecting an eight-GPU training node for an unreviewed one-GPU service.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: gpu-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 200Gi
    iops: 6000
    throughput: 250
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
  namespace: workload-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: inference
        image: registry.example.invalid/reviewed-inference:replace-me
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
          limits:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: gpu-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

Keep `replicas: 0` until replacing the deliberately invalid example registry/image with a reviewed immutable image and supplying its actual entrypoint, model/input paths, probes, storage and scoped workload identity. Validate driver/CUDA/library compatibility and non-root UID 1000/security policy with that image; this audit did not validate an inference runtime.

`ephemeralStorage` is node storage configuration, not persistent model/checkpoint storage or a throughput guarantee. Inspect actual allocatable storage and backing devices. Node root/data EBS encryption does not establish arbitrary PVC encryption. A GPU-count limit constrains pool resources, not total dollars, and may temporarily overshoot during rapid provisioning. The original 16/20-GPU examples were sizing choices; the lab uses a smaller four-GPU ceiling.

`WhenEmpty` with a ten-minute debounce can reduce churn after workloads leave. It does not delay scheduling until GPU initialization is complete or guarantee a warm node. Static NodePools are available when desired pre-provisioned capacity is appropriate, with different limits/consolidation semantics and ongoing cost.

## Distributed Training and EFA

EFA support in Auto Mode is current and real. **A comment beside disk settings does not enable it.** The supported NodeClass field is `advancedNetworking.networkInterfaces`; the device-plugin path advertises `vpc.amazonaws.com/efa`.

Review all of these before activating a training workload:

- Auto Mode currently does **not** support the EFA DRA path. Use the EFA device plugin, not a DRANET ResourceClaim example copied from another compute mode.
- NVIDIA/Neuron host drivers are managed by Auto Mode; EFA host dependencies alone do not prove the separate EFA device plugin is installed and Ready.
- EFA-only interfaces carry RDMA, not Pod IPs. The primary interface is card 0/device 0 with type `interface`. The example adds four `efa-only` devices and one `/28` prefix for Pod IPs.
- Static interface configuration is IPv4-only; no extra IPs/prefixes/ENIs are added after launch. Do not combine the multi-interface configuration with `associatePublicIPAddress`. Plan IP capacity for workload and system Pods.
- Use an existing compatible placement group, matching private AZ/subnets and a reviewed EFA security group permitting the required self-referenced traffic. The example AZ/group names are placeholders, not proof that P5 capacity is available there.
- Check EFA/libfabric/NCCL, process launch/rendezvous, GPU/EFA locality and any required hugepage/memory-lock settings. The four-device interface example is not a claim of maximum P5 network bandwidth or automatic GPU/EFA alignment on Auto Mode's Bottlerocket hosts.

The following homogeneous P5 pool avoids assuming mixed P4d/P5 workers are interchangeable. P4d remains an alternative that needs its own compatible pool/runtime validation. The old 500Gi/16,000 IOPS/1,000 throughput and extra 2,000Gi data-disk values were illustrative; the supported NodeClass does not create that arbitrary extra block device.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ml-training-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: reviewed-efa-security-group
  advancedNetworking:
    networkInterfaces:
    - networkCardIndex: 0
      deviceIndex: 0
      interfaceType: interface
      secondaryIPv4PrefixCount: 1
    - networkCardIndex: 0
      deviceIndex: 1
      interfaceType: efa-only
    - networkCardIndex: 1
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 2
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 3
      deviceIndex: 0
      interfaceType: efa-only
  ephemeralStorage:
    size: 500Gi
    iops: 16000
    throughput: 1000
  placementGroupSelector:
    name: reviewed-ml-training-pg
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - p
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p5.48xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: ml-training-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: ml-training
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: ml-training
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
    budgets:
    - nodes: 10%
  limits:
    cpu: '960'
    memory: 10Ti
    nvidia.com/gpu: '40'
```

### Retained legacy PyTorchJob shape

`kubeflow.org/v1 PyTorchJob` requires **Kubeflow Training Operator V1**; its released v1.9.3 CRD was used for structural validation. Current Kubeflow Trainer's TrainJob/Runtime APIs are different. Auto Mode does not install either operator by creating a NodePool.

This template is suspended and uses a deliberately invalid placeholder image. It illustrates one master plus three workers, eight local GPU processes per node and four EFA devices per Pod: **32 GPUs / four eight-GPU nodes** when activated. The pool's 40-GPU ceiling allows at most five such node shapes as a planning limit, including replacement headroom; it is not a reservation or a strict billing cap.

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training
  namespace: workload-lab
spec:
  nprocPerNode: '8'
  runPolicy:
    suspend: true
    activeDeadlineSeconds: 3600
    backoffLimit: 1
    cleanPodPolicy: None
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
    Worker:
      replicas: 3
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
```

Before unsuspending, supply a vetted image/entrypoint implementing the operator's distributed launch contract, actual dataset paths and durable checkpoint/artifact export. Validate the operator, queue/gang-scheduling behavior, four-node capacity, DNS/rendezvous, network rules, runtime permissions and deadline. This is not a complete production training recipe. The Restricted namespace template may need a separately reviewed workload policy if the vetted accelerator runtime requires permissions it cannot satisfy; do not simply disable cluster-wide admission security.

Suspending an already-running legacy PyTorchJob deletes its active Pods/PodGroups; it is not a checkpoint operation. `cleanPodPolicy: None` preserves completed Pods for inspection but does not export artifacts. Review cleanup after durable export, including PVCs, nodes and separately owned reservations.

### Observe real device capacity

This read-only snapshot reports actual allocatable values and Ready conditions. A missing GPU/EFA value or API failure must not be interpreted as successful device setup:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[]|{name:.metadata.name,
  instanceType:.metadata.labels["node.kubernetes.io/instance-type"],
  pool:.metadata.labels["karpenter.sh/nodepool"],
  allocatable:{cpu:.status.allocatable.cpu,memory:.status.allocatable.memory,
    gpu:.status.allocatable["nvidia.com/gpu"],efa:.status.allocatable["vpc.amazonaws.com/efa"]},
  conditions:[.status.conditions[]?|select(.type=="Ready")|{type,status,reason}]}]'
```

## Resource and Architecture Decisions

| Workload | Candidate policy | Validation still needed |
|----------|------------------|-------------------------|
| Web / API | On-Demand or carefully mixed capacity; moderate consolidation | Availability budget, replicas, runtime architecture and measured latency |
| Batch / CI | Spot where restart and deadline behavior permit | Idempotency, durable progress, retries and unavailable capacity |
| Database / streaming | State-aware placement and disruption policy | Quorum, volume topology, recovery and partition behavior |
| GPU inference | Model-sized GPU/CPU/RAM and possible warm capacity | Image/driver compatibility, probes, cold start and cost |
| Distributed training | Homogeneous accelerator pool and validated network/runtime | Gang capacity, checkpoint/export, EFA devices and placement |

The former 24h/72h/168h/336h expiry and 30s/1m/5m/10m/15m/30m consolidation values are policy examples, not workload-type defaults. Auto Mode's maximum lifetime and separate termination grace still apply.

For CPU-bound workloads, the old 2 CPU/2Gi request and 4 CPU/4Gi limit illustrate a possible burst policy, not universal sizing. For memory-bound workloads, an 8Gi request/limit does not itself provide Guaranteed QoS when CPU request and limit differ. Guaranteed QoS also depends on all relevant containers/resources, and memory limits can still lead to OOM. The earlier 1.2–1.5× usage and 2× request formulas have no verified general performance basis.

With the device-plugin API, GPU resources are integer extended resources: specify limits, optionally matching requests; requests-only is not the GPU pattern. A CPU/memory request must leave enough node allocatable capacity for required system work. Lowering only limits does not ordinarily improve request-based bin-packing.

### Multi-architecture verification

Check a pinned image index instead of grepping `nginx:latest`. An index containing both platforms is a necessary packaging check, not proof that native dependencies and application behavior work on both:

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```

For your own reviewed Dockerfile, the following writes a local OCI archive rather than publishing an unspecified image:

```bash
: "${BUILD_CONTEXT:?Set the reviewed Dockerfile directory}"
test -f "$BUILD_CONTEXT/Dockerfile"
docker buildx build --platform linux/amd64,linux/arm64 \
  --output "type=oci,dest=$WORK_DIR/app-multiarch.tar" "$BUILD_CONTEXT"
```

The build requires a suitable Buildx builder, native workers or correctly configured emulation/cross-compilation. Run architecture-specific application tests before publishing through your normal registry workflow. The former ~40% mixed Spot/Graviton saving remains an unverified estimate; compare actual useful-work cost as described in [Cost Management](./06-cost-management.md).

## References

- [Auto Mode AI/ML compute](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [NodeClass storage and static network interfaces](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EFA device management, including Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/device-management-efa.html)
- [G5 instance specifications](https://aws.amazon.com/ec2/instance-types/g5/)
- [P5 instance specifications](https://aws.amazon.com/ec2/instance-types/p5/)
- [Kubernetes Jobs and Indexed Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [Resource requests, limits and quantities](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Startup, readiness and liveness probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
- [Training Operator v1.9.3 PyTorchJob CRD](https://github.com/kubeflow/training-operator/blob/v1.9.3/manifests/base/crds/kubeflow.org_pytorchjobs.yaml)
- [Kubeflow Trainer and legacy-v1 migration](https://github.com/kubeflow/trainer)
- [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)

< [Previous: Node Lifecycle](./07-node-lifecycle.md) | [Table of Contents](./README.md) | [Next: Migration Guide](./09-migration-guide.md) >
