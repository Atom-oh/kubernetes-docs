# AI Infrastructure on EKS

> **Reviewed**: September12,2026
> **Baselines**: GPU Operator26.7.0 / NVIDIA DRA0.5.0 / Argo Workflows4.1.3 / JupyterHub chart4.4.2 / Mountpoint CSI2.8.0

AI infrastructure combines notebooks, pipelines, distributed runtimes, devices/nodes, storage/networking and authorization. A list of tools or successful Helm release does not establish platform security, availability or model execution.

## Layers and Responsibilities

![Layers separating workload, platform, compute and EKS foundation responsibilities.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-0.html)

Workloads own model/data/execution code; platforms own workflows, runtimes and registries; compute owns real devices, Pods and node capacity. IAM, networking and storage identities span these layers. A Spot-enabled NodePool guarantees neither capacity nor recovery/savings.

## JARK Stack

JARK combines JupyterHub, Argo Workflows, Ray and Karpenter. It is an integration pattern, not one automatically connected product. Explicitly connect notebook authorization, workflow submission, Ray jobs, Kubernetes scheduling and node provisioning.

![JupyterHub/Argo/Ray create Kubernetes workloads; the scheduler places Pods and Karpenter provisions nodes.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-1.html)

### JupyterHub Authentication and Notebook Profiles

Chart4.4.2 declares appVersion5.5.2, distinct from the latest inspected PyPI Hub6.0.0. Local API checks used Hub6.0.0/OAuthenticator17.4.0/KubeSpawner7.1.0; verify actual package combinations inside the operational chart image.

Cognito is one OIDC provider option. Match callback URLs, token/userInfo endpoints, scopes and a stable username claim, and configure an explicit allow policy. MFA/corporate federation must be configured in the provider; GenericOAuthenticator does not enable them automatically.

This Hub configuration assumes an existing Secret volume mounted at /run/secrets/oidc. Keep real secrets out of ConfigMaps, source and environment variables. Wire this Python file into the Hub's actual configuration path and replace URIs/approved sub values for your environment.

```python
from pathlib import Path

c.JupyterHub.authenticator_class = "oauthenticator.generic.GenericOAuthenticator"
c.GenericOAuthenticator.client_id = "prepared-client-id"
c.GenericOAuthenticator.client_secret = Path("/run/secrets/oidc/client-secret").read_text().strip()
c.GenericOAuthenticator.oauth_callback_url = "https://jupyter.example.com/hub/oauth_callback"
c.GenericOAuthenticator.authorize_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize"
c.GenericOAuthenticator.token_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/token"
c.GenericOAuthenticator.userdata_url = "https://prepared-domain.auth.us-west-2.amazoncognito.com/oauth2/userInfo"
c.GenericOAuthenticator.scope = ["openid", "profile", "email"]
c.GenericOAuthenticator.username_claim = "sub"
c.GenericOAuthenticator.allow_all = False
c.GenericOAuthenticator.allow_existing_users = False
c.GenericOAuthenticator.allowed_users = {"replace-with-approved-cognito-sub"}
```

The example sets allow_all=False, explicit allowed_users and allow_existing_users=False. Local checks allowed one approved identity and rejected unapproved/previous users. No actual OAuth login/token exchange was executed.

Distinguish notebook CPU/RAM guarantees from limits and match actual GPU images, labels, tolerations and drivers. Do not assume old jupyter/*:gpu tags provide CUDA. PVCs must share the consuming Pod's namespace; a jupyterhub Pod cannot reference an ml-platform PVC by name alone. Review per-user access points, UID/GID, quotas and shared-model write permissions. EFS storage_capacity is not a physical capacity limit.

### Argo Workflows Data Flow

The previous workflow referenced missing templates, artifacts and scripts. This **tiny dataflow fixture** has six stages. It passes parameters through environment variables and JSON instead of injecting values into Python source. It selects between two coefficients; it is not a real image-classification training, Ray-cluster or external-registry pipeline.

Argo4.1.3 offline lint and all six Python script bodies were validated locally. Prepare prepared-workflow-runner with least privilege and configure image digests, quotas and artifact storage separately before operations.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: toy-dataflow-
  namespace: argo
spec:
  entrypoint: pipeline
  serviceAccountName: prepared-workflow-runner
  parallelism: 1
  activeDeadlineSeconds: 600
  arguments:
    parameters:
    - name: data
      value: '[[1,2],[2,4],[3,6],[4,8]]'
  templates:
  - name: pipeline
    dag:
      tasks:
      - name: validate
        template: validate
        arguments:
          parameters:
          - name: data
            value: '{{workflow.parameters.data}}'
      - name: prepare
        template: prepare
        arguments:
          parameters:
          - name: data
            value: '{{tasks.validate.outputs.result}}'
        dependencies:
        - validate
      - name: tune
        template: tune
        arguments:
          parameters:
          - name: data
            value: '{{tasks.prepare.outputs.result}}'
        dependencies:
        - prepare
      - name: train
        template: train
        arguments:
          parameters:
          - name: scale
            value: '{{tasks.tune.outputs.result}}'
        dependencies:
        - tune
      - name: evaluate
        template: evaluate
        arguments:
          parameters:
          - name: model
            value: '{{tasks.train.outputs.result}}'
          - name: data
            value: '{{tasks.prepare.outputs.result}}'
        dependencies:
        - train
      - name: register
        template: register
        arguments:
          parameters:
          - name: model
            value: '{{tasks.train.outputs.result}}'
        dependencies:
        - evaluate
        when: '{{tasks.evaluate.outputs.result}} == 0'
  - name: validate
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        rows = json.loads(os.environ["DATA"])

        assert rows and all(len(row) == 2 for row in rows)

        assert all(isinstance(v, (int, float)) for row in rows for v in row)

        print(json.dumps(rows))

        '
  - name: prepare
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        rows = json.loads(os.environ["DATA"])

        print(json.dumps({"train": rows[:2], "test": rows[2:]}))

        '
  - name: tune
    inputs:
      parameters:
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        data = json.loads(os.environ["DATA"])

        candidates = [1.0, 2.0]

        loss = lambda scale: sum((scale*x-y)**2 for x,y in data["train"]) / len(data["train"])

        print(min(candidates, key=loss))

        '
  - name: train
    inputs:
      parameters:
      - name: scale
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: SCALE
        value: '{{inputs.parameters.scale}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        print(json.dumps({"scale": float(os.environ["SCALE"]), "fixture": True}))

        '
  - name: evaluate
    inputs:
      parameters:
      - name: model
      - name: data
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: MODEL
        value: '{{inputs.parameters.model}}'
      - name: DATA
        value: '{{inputs.parameters.data}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        model = json.loads(os.environ["MODEL"])

        held_out = json.loads(os.environ["DATA"])["test"]

        print(sum((model["scale"]*x-y)**2 for x,y in held_out) / len(held_out))

        '
  - name: register
    inputs:
      parameters:
      - name: model
    script:
      image: python:3.12.14-slim-trixie
      command:
      - python
      env:
      - name: MODEL
        value: '{{inputs.parameters.model}}'
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 500m
          memory: 128Mi
      source: 'import json, os

        model = json.loads(os.environ["MODEL"])

        print(json.dumps({"candidate": model, "note": "fixture output only; no registry write"}))

        '
```

Fixture MSE0 comes from four synthetic samples, not a real model-quality measurement. Production workflows need train/test separation, data/model revisions, failure/retry/idempotency rules and actual artifact handoffs. artifactRepositoryRef does not install boto3 or grant application download permissions.

### Ray and Karpenter

Use the audited Ray2.58/KubeRay1.7 paths in the [Ray guide](ray/README.md). GCS means Global Control Service; scheduling interacts with raylets. The head may run work if it advertises CPU. Avoid unverified Ray/Python combinations across CPU/GPU/Neuron workers; Neuron images also need Ray and compatible frameworks.

Ray autoscaling expresses worker-Pod demand, the Kubernetes scheduler places Pods, and Karpenter supplies supported node capacity. Ray workers do not directly invoke Karpenter APIs. Match memory/GPU product labels to real nodes; do not select40GB p4d A100s with an80GB label.

Do not duplicate drivers on AL2023 NVIDIA AMIs or overwrite the entire containerd configuration. Karpenter limits are not absolute admission/cost caps, and consolidation does not directly use a DCGM20% utilization threshold. Inspect requests, scheduling feasibility, prices and disruption constraints.

## DRA APIs and Support Boundaries

DRA represents device attributes, requests and allocation through DeviceClass, ResourceSlice and ResourceClaim/Template. Drivers publish slices; scheduler/driver components allocate and prepare claims. Handwritten ResourceSlices do not create real GPUs. Kubernetes API maturity and NVIDIA-driver feature maturity are separate.

![Device-plugin extended resources versus DRA DeviceClass/ResourceSlice/ResourceClaim paths; sharing/topology depend on driver, hardware and feature gates.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-2.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-2.html)

### Current Claim Example

The inspected Kubernetes1.36.2 resource.k8s.io/v1 schema uses requests.exactly. NVIDIA driver0.5 prerequisites distinguish GPU allocation(1.34.2+) from ComputeDomains(1.32+). Verify APIs and patch/platform versions actually served by EKS. “All DRA features on1.31+” is inaccurate.

This **schema example** defines one GPU claim and an inventory-command Pod. Prepare the ml-workloads namespace, gpu.nvidia.com DeviceClass, driver/CDI, nodes and permissions separately. No GPU execution was performed in this audit.

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  namespace: ml-workloads
  name: single-gpu
spec:
  spec:
    devices:
      requests:
      - name: gpu
        exactly:
          deviceClassName: gpu.nvidia.com
          count: 1
---
apiVersion: v1
kind: Pod
metadata:
  name: gpu-inventory-demo
  namespace: ml-workloads
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  containers:
  - name: inspect
    image: ubuntu:24.04
    command:
    - nvidia-smi
    - -L
    resources:
      claims:
      - name: gpu
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
  resourceClaims:
  - name: gpu
    resourceClaimTemplateName: single-gpu
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

CEL must use the actual published typed attributes/domain structure. The former device.topology.node==device.topology.node neither expresses same-node placement nor matches the API. matchAttribute needs an actual qualified attribute. A normal single-Pod GPU claim does not automatically allocate72GPUs across an NVL72 rack.

### NVIDIA0.5 and GPU Operator26.7

The0.5 README still describes GPU allocation as experimental/default-disabled, conflicting with installation/chart and Operator26.7 documentation. The actual standalone chart defaults resources.gpus.enabled=true but **rejects rendering** without explicit opt-in to avoid device-plugin collisions. Do not describe default installation as silently disabling GPUs and succeeding.

The Operator26.7 managed path uses the GPUCluster singleton named gpu-cluster, mutually exclusive with ClusterPolicy. Its preinstalled-driver path sets clusterPolicy.deployCR=false, gpuCluster.deployCR=true and driver.enabled=false. GPUCluster does not replace all driver/toolkit preparation; supply driver/CDI prerequisites. Do not install a duplicate standalone DRA release. Local rendering simulated a served DeviceClass API; it did not enable a real cluster feature.

Distinguish full-GPU/existing-MIG and ComputeDomain support from alpha DynamicMIG, MPS and TimeSlicingSettings. The inspected0.5 feature-gate code declares those three false/Alpha. Some documentation GA labels also differ from source Beta labels; record the exact release's support matrix, code and configuration together. GPU Operator25.3 alone does not establish support for everything.

Device plugins also support existing MIG, time-slicing and experimental MPS paths; GPU sharing is not exclusive to DRA.3g.20gb names one instance profile, not three20GB instances. MIG/exclusive allocation does not automatically isolate host, driver, privileges or every side channel; MPS/time-slicing are not security boundaries.

### Multi-Node NVLink and ComputeDomains

GB200 is Grace Blackwell, not Grace Hopper. ComputeDomains coordinate MNNVL/IMEX resources across Pods/nodes. Distinguish racks, EC2 instances, Kubernetes nodes and Pods, and verify actual clique/fabric/device/driver support. Invented nvswitchEnabled/graceHopperMode fields or scheduling gates do not configure topology. A scheduling gate without a controller to remove it leaves the Pod waiting.

## Agent Platforms and MCP

Use current Kagent/LangGraph/Langfuse/Milvus APIs in the [Agentic AI guide](03-agentic-ai-platform.md). GitLab is an optional source/CI platform; privileged runners and public ingress are not baseline requirements. Separate job identity, networking, secrets and image-build permissions, and verify provider credential delivery.

MCP defines protocol operations such as tool listing/calling; it is not a standard Kubernetes auto-discovery controller or a gateway distribution. The former ghcr.io/anthropics/mcp-gateway:latest image and mcp.anthropic.com/tool label/config were unverified implementations and were removed. Select an actual server/gateway release and validate transport, authentication, authorization, timeouts and tool input schemas. A URL environment variable does not implement those operations.

Requesting GPU resources for Milvus does not enable GPU indexing. Match embedding dimensions/model revisions, index parameters, deletion/update lifecycle and tenant filters. Do not use a Langfuse2.x Deployment as current4.x platform installation; check backend dependencies, file credentials, instrumentation APIs and sensitive-data retention.

## Storage and Networking

Verify EFS access-point IAM/UID/GID, directory permissions and same-namespace PVC consumption. The IAM mount option does not configure controller/mount-identity credentials by itself.

Use supported FSx CSI parameters and capacity units. Do not copy invented s3ImportPath/s3ExportPath settings for PERSISTENT_2 or an invalid10Ti capacity. Distinguish existing/static and newly provisioned filesystems, DRA and backup compatibility in the [storage guide](01-ai-ml-workloads.md).

Mountpoint CSI2.8.0 supports **static PVs** for existing S3 buckets. The StorageClass/PVC-only dynamic-bucket example was removed. Mountpoint is not fully POSIX; check rename, random-write, locking and checkpoint behavior. The2.8 support table removes AL2/Ubuntu22.04 and directs installations to EKS add-ons or official charts rather than repository branches.

Do not multiply interface counts by already aggregate instance bandwidth. The former p4d“4×400Gbps” and trn1n“16×1600Gbps” figures were incorrect. Use the [training networking guide](05-model-training.md) for same-AZ placement, real interfaces, driver/libfabric/NCCL, device/Pod allocation and security groups. RAID0 and efa-enabled tags do not enable EFA.

Subnets are one part of isolation. Configure workload ingress/egress and EFA self-reference requirements through actual SG/IAM resources. Terraform-looking YAML stored in a ConfigMap does not apply network rules. Avoid default access from an entire VPC CIDR.

## GPU Observability and Alerts

DCGM Exporter4.6.0-4.8.3 defines XID_ERRORS as the last error **code gauge**. increase(XID_ERRORS) is not an error count and can misread a31→13 code change as a reset. Observe the current code or separately enable the XID_ERRORS_TOTAL counter. Not every XID indicates hardware failure.

FB_USED/FB_FREE are MiB gauges; the ratio below ranges0–1. High reserved VRAM is not necessarily OOM: inspect allocation failures, workload behavior, model cache and available memory together. Fixed85C/20% thresholds are not universal failure/reclamation standards. Check actual metric types/units before applying rate() to PCIe throughput or NVLink bandwidth gauges.

These rules assume one cluster per Prometheus. For combined clusters, include cluster labels in aggregation/joins. Inspect actual node/UUID/MIG labels and kube-state-metrics resource-label normalization.

```yaml
groups:
- name: gpu-observations
  rules:
  - record: gpu:framebuffer_used_ratio
    expr: DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)
  - alert: GPUReportedXIDCode
    expr: DCGM_FI_DEV_XID_ERRORS > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Inspect the reported XID code and workload context"
  - record: namespace:pending_gpu_requesting_pods:count
    expr: |
      count by (namespace) (
        max by (namespace, pod) (kube_pod_status_phase{phase="Pending"} == 1)
        and on (namespace, pod)
        max by (namespace, pod) (kube_pod_container_resource_requests{resource="nvidia_com_gpu"} > 0)
      )
```

The pending rule counts waiting Pods that request GPUs; it does not prove GPU shortage caused the wait. Multiple GPU-requesting containers count once per Pod. Inspect events, PVCs, affinity, taints, quotas, claims and image pulls. Do not assume a node label exists on every alert.

Configure actual Prometheus rule selection and correct Service/port scraping for DCGM, Ray and Karpenter. Grafana file provisioning differs from an HTTP dashboard wrapper; a label alone does not connect datasources. Neuron monitor output and exporter endpoints need separate preparation.

## Verification Scope

All original guide/quiz prose and58unique code blocks were reviewed. Checks cover DRA/Pod schemas, official Helm, OAuthenticator allow policies, Argo offline lint/script bodies and Prometheus fixtures. No actual OAuth/cluster/GPU/DRA allocation, model, S3 mount or MCP server was executed; no cloud resources or paid calls were created.

## References

- [GPU Operator26.7 DRA installation](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)
- [NVIDIA DRA0.5 source](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/tree/v0.5.0)
- [DRA0.5 prerequisites](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [DRA0.5 feature gates](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/pkg/featuregates/featuregates.go)
- [OAuthenticator17.4](https://github.com/jupyterhub/oauthenticator/tree/17.4.0)
- [JupyterHub chart4.4.2](https://github.com/jupyterhub/zero-to-jupyterhub-k8s/releases/tag/4.4.2)
- [Argo Workflows4.1.3](https://github.com/argoproj/argo-workflows/tree/v4.1.3)
- [Mountpoint CSI2.8.0](https://github.com/awslabs/mountpoint-s3-csi-driver/tree/v2.8.0)
- [DCGM Exporter counter definitions](https://github.com/NVIDIA/dcgm-exporter/blob/4.6.0-4.8.3/etc/default-counters.csv)
- [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

## Quiz

[AI Infrastructure Quiz](../quizzes/ai-ml/06-ai-infrastructure-quiz.md)
