# EKS 上的 AI 基础设施

> **最后更新**: September 12, 2026
> **基线**: GPU Operator26.7.0 / NVIDIA DRA0.5.0 / Argo Workflows4.1.3 / JupyterHub chart4.4.2 / Mountpoint CSI2.8.0

AI 基础设施将 notebook、pipeline、分布式 runtime、device/node、storage/networking 和 authorization 结合在一起。工具清单或成功的 Helm release 并不能建立平台安全性、可用性或模型执行能力。

## 层次与职责

![分隔工作负载、平台、计算和 EKS 基础层职责的层次。](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-0.html)

工作负载负责模型/数据/执行代码；平台负责 workflow、runtime 和 registry；计算层负责真实 device、Pod 和 node 容量。IAM、networking 和 storage identity 跨越这些层次。启用了 Spot 的 NodePool 并不保证容量、恢复或节省成本。

## JARK Stack

JARK 将 JupyterHub、Argo Workflows、Ray 和 Karpenter 结合起来。它是一种集成模式，而不是自动连接的单一产品。请显式连接 notebook authorization、workflow submission、Ray job、Kubernetes scheduling 和 node provisioning。

![JupyterHub/Argo/Ray 创建 Kubernetes 工作负载；scheduler 放置 Pod，Karpenter 提供 node。](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-1.html)

### JupyterHub Authentication 和 Notebook Profile

Chart4.4.2 声明的 appVersion 为 5.5.2，与检查到的最新 PyPI Hub6.0.0 不同。本地 API 检查使用 Hub6.0.0/OAuthenticator17.4.0/KubeSpawner7.1.0；请验证运行中 chart image 内实际的 package 组合。

Cognito 是一种 OIDC provider 选项。匹配 callback URL、token/userInfo endpoint、scope 和稳定的 username claim，并配置显式 allow policy。必须在 provider 中配置 MFA/corporate federation；GenericOAuthenticator 不会自动启用它们。

此 Hub 配置假定已有一个 Secret volume 挂载在 /run/secrets/oidc。不要将真实 secret 放入 ConfigMap、源代码或环境变量。将此 Python 文件接入 Hub 实际的配置路径，并替换为适用于你的环境的 URI/已批准 sub 值。

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

该示例设置 allow_all=False、显式 allowed_users 和 allow_existing_users=False。本地检查允许一个已批准 identity，并拒绝未批准/先前的 user。未执行实际 OAuth login/token exchange。

区分 notebook CPU/RAM guarantee 与 limit，并匹配实际 GPU image、label、toleration 和 driver。不要假定旧的 jupyter/*:gpu tag 提供 CUDA。PVC 必须与使用它的 Pod 共享 namespace；jupyterhub Pod 不能仅通过名称引用 ml-platform PVC。检查 per-user access point、UID/GID、quota 和 shared-model write permission。EFS storage_capacity 不是物理容量限制。

### Argo Workflows 数据流

此前的 workflow 引用了缺失的 template、artifact 和 script。这个**微型数据流 fixture**有六个 stage。它通过环境变量和 JSON 传递 parameter，而非将值注入 Python 源代码。它在两个 coefficient 之间选择；它不是真实的 image-classification training、Ray-cluster 或 external-registry pipeline。

Argo4.1.3 offline lint 和全部六个 Python script body 均已在本地验证。在运行前，为 prepared-workflow-runner 配置 least privilege，并单独配置 image digest、quota 和 artifact storage。

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

Fixture MSE0 来自四个合成样本，并非真实的模型质量测量。生产 workflow 需要 train/test separation、data/model revision、failure/retry/idempotency rule 以及真实的 artifact handoff。artifactRepositoryRef 不会安装 boto3 或授予 application download permission。

### Ray 和 Karpenter

请使用 [Ray 指南](ray/README.md)中经过审计的 Ray2.58/KubeRay1.7 路径。GCS 指 Global Control Service；scheduling 与 raylet 交互。如果 head 宣告了 CPU，它可能运行工作负载。避免在 CPU/GPU/Neuron worker 之间使用未经验证的 Ray/Python 组合；Neuron image 也需要 Ray 和兼容的 framework。

Ray autoscaling 表达 worker-Pod demand，Kubernetes scheduler 放置 Pod，而 Karpenter 提供受支持的 node capacity。Ray worker 不会直接调用 Karpenter API。将 memory/GPU product label 与真实 node 匹配；不要用 80GB label 选择 40GB p4d A100。

不要在 AL2023 NVIDIA AMI 上重复安装 driver，也不要覆盖整个 containerd configuration。Karpenter limit 不是绝对的 admission/cost cap，consolidation 也不会直接使用 DCGM20% utilization threshold。检查 request、scheduling feasibility、price 和 disruption constraint。

## DRA API 与支持边界

DRA 通过 DeviceClass、ResourceSlice 和 ResourceClaim/Template 表示 device attribute、request 和 allocation。driver 发布 slice；scheduler/driver component 分配并准备 claim。手写的 ResourceSlice 不会创建真实 GPU。Kubernetes API maturity 与 NVIDIA-driver feature maturity 是彼此独立的。

![device-plugin extended resource 与 DRA DeviceClass/ResourceSlice/ResourceClaim 路径；共享/topology 取决于 driver、hardware 和 feature gate。](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-06-ai-infrastructure-2.html)

### 当前 Claim 示例

检查到的 Kubernetes1.36.2 resource.k8s.io/v1 schema 使用 requests.exactly。NVIDIA driver0.5 prerequisite 将 GPU allocation(1.34.2+) 与 ComputeDomains(1.32+) 区分开来。请验证 EKS 实际提供的 API 及 patch/platform version。“1.31+ 上全部 DRA feature”是不准确的。

此**schema 示例**定义了一个 GPU claim 和一个 inventory-command Pod。请分别准备 ml-workloads namespace、gpu.nvidia.com DeviceClass、driver/CDI、node 和 permission。本次审计未执行 GPU。

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

CEL 必须使用实际发布的 typed attribute/domain structure。此前的 device.topology.node==device.topology.node 既未表达 same-node placement，也不匹配 API。matchAttribute 需要实际的 qualified attribute。普通的 single-Pod GPU claim 不会自动在 NVL72 rack 中分配 72 个 GPU。

### NVIDIA0.5 和 GPU Operator26.7

0.5 README 仍将 GPU allocation 描述为 experimental/default-disabled，这与 installation/chart 和 Operator26.7 文档冲突。实际 standalone chart 的默认值为 resources.gpus.enabled=true，但为避免 device-plugin collision，在没有显式 opt-in 时会**拒绝 render**。不要将默认 installation 描述为静默禁用 GPU 并成功。

Operator26.7 managed path 使用名为 gpu-cluster 的 GPUCluster singleton，且与 ClusterPolicy 互斥。其 preinstalled-driver path 设置 clusterPolicy.deployCR=false、gpuCluster.deployCR=true 和 driver.enabled=false。GPUCluster 不会替代所有 driver/toolkit preparation；请提供 driver/CDI prerequisite。不要安装重复的 standalone DRA release。本地 rendering 模拟了一个被提供的 DeviceClass API；它没有启用真实的 cluster feature。

区分 full-GPU/existing-MIG 和 ComputeDomain support 与 alpha DynamicMIG、MPS 和 TimeSlicingSettings。检查到的 0.5 feature-gate code 将后三者声明为 false/Alpha。一些文档中的 GA label 也与 source 中的 Beta label 不同；请一并记录确切 release 的 support matrix、code 和 configuration。仅 GPU Operator25.3 并不能建立对所有功能的支持。

Device plugin 也支持 existing MIG、time-slicing 和 experimental MPS path；GPU sharing 并非 DRA 独有。3g.20gb 指的是一个 instance profile，而非三个 20GB instance。MIG/exclusive allocation 不会自动隔离 host、driver、privilege 或每个 side channel；MPS/time-slicing 不是 security boundary。

### Multi-Node NVLink 和 ComputeDomains

GB200 是 Grace Blackwell，而不是 Grace Hopper。ComputeDomains 跨 Pod/node 协调 MNNVL/IMEX resource。区分 rack、EC2 instance、Kubernetes node 和 Pod，并验证实际 clique/fabric/device/driver support。虚构的 nvswitchEnabled/graceHopperMode field 或 scheduling gate 不会配置 topology。没有 controller 移除的 scheduling gate 会让 Pod 持续等待。

## Agent 平台和 MCP

请在 [Agentic AI 指南](03-agentic-ai-platform.md)中使用当前的 Kagent/LangGraph/Langfuse/Milvus API。GitLab 是可选的 source/CI platform；privileged runner 和 public ingress 不是基线要求。分离 job identity、networking、secret 和 image-build permission，并验证 provider credential delivery。

MCP 定义 tool listing/calling 等 protocol operation；它不是标准 Kubernetes auto-discovery controller 或 gateway distribution。此前的 ghcr.io/anthropics/mcp-gateway:latest image 以及 mcp.anthropic.com/tool label/config 是未经验证的 implementation，已被移除。选择实际的 server/gateway release，并验证 transport、authentication、authorization、timeout 和 tool input schema。一个 URL environment variable 并不能实现这些 operation。

为 Milvus 请求 GPU resource 不会启用 GPU indexing。匹配 embedding dimension/model revision、index parameter、deletion/update lifecycle 和 tenant filter。不要将 Langfuse2.x Deployment 用作当前 4.x platform installation；检查 backend dependency、file credential、instrumentation API 和 sensitive-data retention。

## Storage 和 Networking

验证 EFS access-point IAM/UID/GID、directory permission 及同 namespace 的 PVC consumption。IAM mount option 本身不会配置 controller/mount-identity credential。

使用受支持的 FSx CSI parameter 和 capacity unit。不要复制为 PERSISTENT_2 虚构的 s3ImportPath/s3ExportPath setting 或无效的 10Ti capacity。在 [storage 指南](01-ai-ml-workloads.md)中区分 existing/static 与 newly provisioned filesystem、DRA 和 backup compatibility。

Mountpoint CSI2.8.0 支持现有 S3 bucket 的**static PV**。StorageClass/PVC-only dynamic-bucket 示例已被移除。Mountpoint 并非完全 POSIX；请检查 rename、random-write、locking 和 checkpoint behavior。2.8 support table 移除了 AL2/Ubuntu22.04，并引导通过 EKS add-on 或 official chart 而不是 repository branch 安装。

不要将 interface count 乘以已是 aggregate 的 instance bandwidth。此前 p4d“4×400Gbps”和 trn1n“16×1600Gbps”的数值不正确。请使用 [training networking 指南](05-model-training.md)了解 same-AZ placement、real interface、driver/libfabric/NCCL、device/Pod allocation 和 security group。RAID0 和 efa-enabled tag 不会启用 EFA。

Subnet 只是 isolation 的一部分。通过实际的 SG/IAM resource 配置 workload ingress/egress 和 EFA self-reference requirement。存储在 ConfigMap 中看似 Terraform 的 YAML 不会应用 network rule。避免默认允许来自整个 VPC CIDR 的访问。

## GPU Observability 和 Alert

DCGM Exporter4.6.0-4.8.3 将 XID_ERRORS 定义为最后一个 error **code gauge**。increase(XID_ERRORS) 不是 error count，并可能将 31→13 的 code change 误读为 reset。观察当前 code，或单独启用 XID_ERRORS_TOTAL counter。并非每个 XID 都表示 hardware failure。

FB_USED/FB_FREE 是 MiB gauge；下方 ratio 的范围为 0–1。较高的 reserved VRAM 不一定是 OOM：请一并检查 allocation failure、workload behavior、model cache 和 available memory。固定的 85C/20% threshold 并非通用的 failure/reclamation standard。在对 PCIe throughput 或 NVLink bandwidth gauge 应用 rate() 前，请检查实际 metric type/unit。

这些 rule 假定每个 Prometheus 只有一个 cluster。对于 combined cluster，请在 aggregation/join 中包含 cluster label。检查实际的 node/UUID/MIG label 以及 kube-state-metrics resource-label normalization。

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

pending rule 统计请求 GPU 的等待 Pod；它不能证明 GPU 短缺导致了等待。多个请求 GPU 的 container 在每个 Pod 中只计一次。检查 event、PVC、affinity、taint、quota、claim 和 image pull。不要假定每个 alert 上都存在 node label。

为 DCGM、Ray 和 Karpenter 配置实际的 Prometheus rule selection 以及正确的 Service/port scraping。Grafana file provisioning 与 HTTP dashboard wrapper 不同；一个 label 本身不会连接 datasource。Neuron monitor output 和 exporter endpoint 需要单独准备。

## 验证范围

已审查全部原始指南/quiz prose 和 58 个唯一 code block。检查涵盖 DRA/Pod schema、official Helm、OAuthenticator allow policy、Argo offline lint/script body 和 Prometheus fixture。未执行实际 OAuth/cluster/GPU/DRA allocation、model、S3 mount 或 MCP server；未创建 cloud resource 或 paid call。

## 参考资料

- [GPU Operator26.7 DRA 安装](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)
- [NVIDIA DRA0.5 源代码](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/tree/v0.5.0)
- [DRA0.5 前提条件](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [DRA0.5 feature gate](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/pkg/featuregates/featuregates.go)
- [OAuthenticator17.4](https://github.com/jupyterhub/oauthenticator/tree/17.4.0)
- [JupyterHub chart4.4.2](https://github.com/jupyterhub/zero-to-jupyterhub-k8s/releases/tag/4.4.2)
- [Argo Workflows4.1.3](https://github.com/argoproj/argo-workflows/tree/v4.1.3)
- [Mountpoint CSI2.8.0](https://github.com/awslabs/mountpoint-s3-csi-driver/tree/v2.8.0)
- [DCGM Exporter counter 定义](https://github.com/NVIDIA/dcgm-exporter/blob/4.6.0-4.8.3/etc/default-counters.csv)
- [MCP tool 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

## 测验

[AI Infrastructure 测验](../quizzes/ai-ml/06-ai-infrastructure-quiz.md)
