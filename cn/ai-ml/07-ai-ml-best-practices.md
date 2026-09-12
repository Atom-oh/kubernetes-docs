# EKS 上的 AI/ML 最佳实践

> **审核日期**: September12,2026
> **基线**: inference-perf0.6.1 / SOCI0.15.0 / Karpenter1.14.1 / External Secrets2.10.0

针对相同工作负载，使用延迟、成功率、吞吐量、成本和恢复能力评估改进。GPU、snapshotter 或共享功能并不保证固定的加速或节省百分比。

![通过测量和恢复检查评估基准测试、启动优化、设备、网络/存储、可观测性、成本和安全性。](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-0.html)

## LLM 推理基准测试

![首个输出、token 间隔、端到端延迟和聚合吞吐量的不同测量窗口。](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-1.html)

| 指标 | 定义和注意事项 |
| --- | --- |
| TTFT | 从发送到收到首个**非空输出**的时间；第一个 HTTP/SSE 帧不一定包含 token |
| ITL | token/chunk 间隔；一个网络 chunk 可能包含多个 token |
| TPOT | 工具定义的首个 token 之后的平均值；对于只有一个或更少输出 token 的情况未定义 |
| E2E | 从请求到完成的时间；记录队列、网络和后处理边界 |
| 请求吞吐量 | 成功完成的请求数 / 指定测量窗口 |
| Token 吞吐量 | 窗口内输出 token 总和 / 时间，而非请求 TPS 的非加权平均值 |
| Goodput | 满足成功和延迟 SLO 标准的请求速率 |

使用实际 token 时间戳时，平均 ITL 为(最后一个 token 时间-第一个 token 时间)/(token 数-1)。非流式响应无法测量实际 TTFT/ITL。请明确 tokenizer、空/单 token 输出、失败以及排除的预热数据。500ms/50ms 并非通用 SLO。

### inference-perf 和 GenAI-Perf

inference-perf 是 Kubernetes SIGs/wg-serving 基准测试工具。检查的 PyPI 包为0.6.1，而其 Git tag 的 pyproject 仍显示0.5.0；此元数据差异已记录。实际 CLI 使用 --config_file 或 --server.type 等结构化选项，而不是原先的 benchmark --endpoint --prompt-length 接口。

此**内部 mock**配置不会调用模型服务器。实际0.6.1 CLI 使用一个 worker 完成了三个请求。Mock token 计数为零，TTFT/TPOT 为 null，因此这些并非模型性能结果。

```yaml
api:
  type: chat
  streaming: false
data:
  type: mock
load:
  type: concurrent
  stages:
    - concurrency_level: 1
      num_requests: 3
  num_workers: 1
  worker_max_concurrency: 1
  base_seed: 17
server:
  type: mock
  base_url: http://127.0.0.1:8000
report:
  request_lifecycle:
    summary: true
    per_stage: true
    per_request: true
storage:
  local_storage:
    path: ./benchmark-fixture-results
```

```bash
inference-perf --config_file benchmark-fixture.yaml
```

切换到真实端点前，请验证服务器/API 类型、模型别名、流式传输、tokenizer 和身份验证。配置可能包含 secret header，且合并后的配置会被记录，因此请验证凭证传递/脱敏。保留输出文件、原始请求/响应和失败记录，同时遵守数据集隐私和使用权限。

恒定/Poisson 速率测量每秒到达量；并发负载控制并发数。相同的数值设置并不等价。测试单请求基线、受限的负载爬升、突发流量和真实分布。仅凭饱和曲线无法证明是 CPU/GPU/内存瓶颈；应检查性能分析、队列、网络和客户端容量。

使用 GenAI-Perf0.0.16 已审查的[profile/endpoint/service/token 选项](04-inference-frameworks.md)，不要虚构 --backend vllm 组合。GPU 指标需要单独收集；检查负载生成器的 CPU/网络限制。基准测试 Job 需要经验证的镜像、配置键、PVC、截止时间和考虑重复负载的重试语义。

## 容器启动优化

![分别测量 Pod 调度、镜像获取/解包、容器启动、模型加载和就绪状态。](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-2.html)

分别测量镜像传输、解包、模型下载/加载和就绪状态。无来源的“始终5–15分钟”和“节省80–95%”表格已删除。45GB/1Gbps≈360秒仅是理想化的传输算术，不包括压缩后大小、协议、磁盘和并发开销——并非测得的拉取时间。

外部模型工件可能减少镜像变更/拉取，但会增加下载和缓存管理成本。预制镜像在某些环境中可能合适。初始化必须传播失败，并验证 revision、校验和及完成状态。先前 S3 sync 后接成功 echo 的做法可能掩盖下载失败，已删除。

多阶段构建必须对齐 Python 解释器/ABI 及 CUDA/runtime 库，包括可执行文件/共享库。不要假设 Ubuntu22.04 的 python3.11 和 pip3 使用同一解释器，也不要只复制 site-packages。使用受支持的发行版包/wheel，并在镜像内测试 import/entrypoint。优先使用只读 root filesystem，并显式配置可写的 cache/tmp/model mount。

### SOCI0.15

SOCI 支持延迟镜像加载，但当启动时立即读取全部 weights/libraries 时，收益可能缩小。拥有 index 并不会配置 CRI 使用 SOCI snapshotter。验证 containerd/CRI 集成、镜像/index digest 和 registry 兼容性。未经验证的、暴露 host containerd socket 的 privileged DaemonSet 已删除。

版本0.15 的 create/push 接受位置 image reference，而不是 --ref。当前入门指南使用 convert 创建启用 SOCI 的镜像。独立模式无需 containerd 或 sudo，即可处理本地 OCI layout。

```bash
soci convert --standalone --format oci-dir input-oci-layout output-soci-layout
```

输入必须是 OCI layout，而非普通 docker-save tarball。如果每个 layer 都小于 min-layer-size，转换可能失败。本次审查使用显式 min-layer-size=0 转换了一个合成 layer，并验证了八个 blob digest。未运行容器启动基准测试。发布时请将转换后的镜像/index 一并保留。

### Bottlerocket Bootstrap

在1.64 中，`bootstrap-containers.<name>.user-data` 是 **base64 数据**，由 bootstrap container 作为文件使用。settings 中的纯 shell 文本不会自动执行。源镜像必须真实存在，并正确使用 host image store/namespace。静态的 images-prefetched=true label 并非成功的证据。

mode=once 会在执行后变为 off。essential=true 失败会停止启动；false 允许失败，因此应使该设置与就绪需求一致。allowed-unsafe-sysctls 不是 privileged-container 开关。请在测量中纳入 prefetch 对节点准备时间的影响。

## GPU、Neuron 和存储选择

参数×字节数只是 weights 的下限。还应包括与架构相关的 KV cache、activation、workspace、通信 buffer、fragmentation 和 sharding 约束。13B FP16 weights≈26GB 无法放入24GB；70B FP16≈140GB 超过四个24GB GPU 的总容量。更多 host CPU 不会扩大未变化的 GPU VRAM。

区分 p4d.24xlarge 的8×40GB 与 p4de 的8×80GB A100。G5g 使用 Arm/T4G；验证镜像/kernel 架构。有关 inf2.48xlarge 的192vCPU/768GiB host RAM、12chips/24NeuronCores/384GiB HBM，请参阅已审查的[Inf2 表](04-inference-frameworks.md)。P5 等系列名称并不固定所有规格的 GPU 数量。选择时请重新检查可用的代际、区域、quota 和价格。

LoRA 减少可训练 adapter state，但仍保留 base weights/activation，且与 QLoRA 不同。不要使用假定大多数 LoRA 模型能放入24GB 的函数。测量峰值内存、延迟、吞吐量和重启。

不要仅凭10TB 数据集阈值选择存储。比较访问模式、并发、metadata、延迟、语义、耐久性和成本。当前通用 gp3 文档列出的基线为3000IOPS/125MiB/s，最大为80000IOPS/2000MiB/s，受大小/IOPS/instance 约束；Outposts 有所不同。历史的16000IOPS/1GB/s 限制并非普遍适用的当前限制。

有关 EFS Elastic 吞吐量、FSx/CSI/S3 关联和 Mountpoint POSIX 限制，请使用[基础设施指南](06-ai-infrastructure.md)。S3 既没有无限吞吐量，也没有固定延迟；EFS 并不总是比 FSx 慢。instance store/tmpfs 是临时存储。GPU KV cache 通常位于 GPU 内存中，而不会自动位于 SSD/tmpfs。

### 模型缓存验证

config.json 文件并不能证明 weights 已下载完成。在公开不可变只读存储之前，请根据受信任的 release manifest/revision 验证**所有文件**。防止并发 downloader 竞争和部分写入的文件。

此本地验证器不执行下载/删除。测试涵盖完整文件、错误 revision、部分/缺失 weights、路径遍历和外部 symlink。Manifest 信任和验证后的不可变性仍是独立要求。

```python
from pathlib import Path
import hashlib
import re


def verify_model_cache(root, manifest, expected_revision):
    """Verify files against a separately trusted release manifest; no downloads/deletion."""
    root = Path(root).resolve(strict=True)
    if manifest.get("revision") != expected_revision:
        raise ValueError("Model revision mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Empty or invalid release manifest")
    for relative, expected_hash in files.items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError("Unsafe manifest path")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Invalid SHA256")
        target = (root / name).resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("File escapes the cache or is not a regular file")
        digest = hashlib.sha256()
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_hash:
            raise ValueError("Incomplete or corrupt model file: " + relative)
    return root
```

Checkpoint 需要 optimizer/RNG/data-cursor 和 shard state，如[训练/恢复示例](05-model-training.md)所示。在传输、校验和和完成 manifest 成功之前，不要删除之前的有效副本。旧的 ls/xargs rm -rf 循环混淆了目录内容与 checkpoint 路径，并尝试通过只读 mount 删除；已删除。将首次同步延迟30分钟或省略终止时的 flush 会增加工作丢失风险。

## 网络和调度

EFA 可改善适合的工作负载的通信；并非每个 DDP 执行都需要它。验证 interface、同一 AZ 放置、driver/libfabric/aws-ofi-nccl、Pod resource、security group 和实际 transport。RAID0/subnet tag 不会启用它。避免未经验证的 NCCL_TIMEOUT 和盲目复制的 Ring/Simple/IB_DISABLE 设置。torchrun --nnodes 统计的是节点数，而非总进程 WORLD_SIZE。

使用 Karpenter1.14.1 实际的 placementGroupSelector。aws:ec2:placement-group tag 不是 placement API，且 aws: 不是 user-tag namespace。此**schema 示例**需要批准的 AMI/subnet/SG/role identifier 以及已有的 placement group。该示例指定 amiFamily AL2023，因此替换值必须是经过验证的 EKS AL2023 AMI，而不是其他 OS 的 AMI。它未完成 EFA networkInterfaces 配置。

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: prepared-gpu-class
spec:
  role: REPLACE_WITH_APPROVED_NODE_ROLE
  amiSelectorTerms:
  - id: ami-0123456789abcdef0
  subnetSelectorTerms:
  - id: subnet-0123456789abcdef0
  securityGroupSelectorTerms:
  - id: sg-0123456789abcdef0
  placementGroupSelector:
    name: prepared-training-placement-group
  amiFamily: AL2023
```

### 中断预算和 Spot

此预算适用于周一至周五 **09:00–17:00UTC**。旧的0 9-17 * * 1-5 会在直至17:00的每小时启动一个八小时窗口，使保护延续到次日01:00。并发预算使用更严格的限制，且不会自动遵循本地时区。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-gpu-pool
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: prepared-gpu-class
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: '0'
      schedule: 0 9 * * 1-5
      duration: 8h
    - nodes: 30%
```

budgets.nodes=0 限制自愿中断，不限制 Spot interruption、节点故障或强制过期。仅 Spot requirement 是强制条件，不是可回退至 on-demand 的偏好。ScheduleAnyway topology spread 是软约束；请验证实际 replica、容量和 AZ 分布。

terminationGracePeriodSeconds=120 并不保证 EC2 会授予120秒。通过真实终止测试 gateway readiness/draining、endpoint propagation、SIGTERM、活跃 stream、重试和重复请求。不要虚构 vLLM /drain API。推理 cache、session 和 TP group 带有状态/重启成本。

## 可观测性和成本

使用[当前 vLLM metrics](02-vllm-deployment.md)和[DCGM rules](06-ai-infrastructure.md)。KV 占用率是 vllm:kv_cache_usage_perc，而非旧的 gpu_cache_usage_perc。观察 queue/preemption 和 backend 行为，而不是假定满 cache 会立即拒绝请求。从当前 hit/query counter 推导 prefix-hit ratio，并处理零分母。

DCGM FB_USED/FREE 是 MiB gauge；XID_ERRORS 是最后一个代码。避免使用不存在的 FB_TOTAL 或对 gauge 使用 increase()。仅凭温度不能证明 thermal throttling；应比较 clock、power、throttle reason 和工作负载。匹配 Prometheus label/histogram aggregation，并对表达式上的 avg_over_time 使用有效的 subquery 语法。

VPA Off 提供 CPU/内存建议，而非自动选择 GPU instance。之前的 rightsizing script 只检查第一个 series，并将0–1 ratio 与50/90 比较；已删除。应在移除后检查各工作负载的峰值、queue、SLO 和恢复情况。

使用实际的区域/OS/购买条款、利用率、空闲/故障时间、存储、传输和运维记录节省。Spot/Savings Plans/RI 在折扣和容量保证方面不同。避免固定的60–90%表格或叠加优化节省百分比。使用测得的基线和波动性，单独作出 commitment-purchase 决策。

## 模型访问和 Secret 管理

S3 ListBucket 和 GetObject 分别使用 bucket/object ARN 和受支持的 condition key。通用 bucket 在显式启用 ABAC 后可使用 aws:ResourceTag/Environment 等 bucket-tag condition。ABAC 默认禁用：请验证 bucket 状态、受信任的 tag-administration permission、identity/bucket policy 以及 action/resource 配对，而非仅复制 tag condition。启用不会创建所需的 Allow，也不会覆盖其他 Deny policy。验证受信任的 ServiceAccount namespace/name、SDK credential chain 和实际请求 identity。vLLM 不会自动下载每个 S3 model URI。

检查的 ESO2.10.0 CRD **提供 v1**，其中 v1beta1 served=false。此示例引用一个已批准的、同一 namespace 的 SecretStore。请分别准备 remote key、permission、rotation 和 target lifecycle。

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: model-download-token
  namespace: ai-ml
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: approved-secrets-manager
    kind: SecretStore
  target:
    name: model-download-credential
    creationPolicy: Owner
  data:
  - secretKey: token
    remoteRef:
      key: approved/model-download
      property: token
```

将 Kubernetes Secret 作为 volume 挂载，并让应用在需要时重新读取文件。subPath mount 不会接收自动更新；environment variable 或仅在启动时读取的值不会自动重新加载。ESO refresh 本身不是上游 credential issuance/rotation。请分别验证 provider rotation、Secret access 和应用重新加载。

CloudTrail Secrets Manager API 记录不会捕获应用读取本地 Secret 文件的每一次操作。不要声称 kubectl describe 通常会打印 SecretKeyRef 值，但 environment 传递仍会暴露 process/debugging surface，且不同于 file-credential policy。绝不要在示例/log 中打印真实 secret。

NetworkPolicy 需要 CNI 执行。验证 selector AND/OR 语义、默认 namespace-name label 和 TCP/UDP DNS。10.0.0.0/8 health-check 开放规则和“internet443 意味着仅 S3”规则已删除。对于预置模型，将运行时 egress 限制为必要路径，并在 gateway 区分 inference/management API。

审计日志应捕获 user/workload identity、模型 revision、action、outcome 和 request ID，并酌情脱敏 prompt/secret。将 containerd CRI log 按 Docker 格式解析，或仅保留包含 request 的行，可能丢失审计事件。验证实际的 collector、parser、IAM、buffer、retention 和交付失败情况——而不只是 ConfigMap。

## 验证范围

已审查原指南/quiz 的全部 prose 和87个唯一 code block。验证包括三个原生 inference-perf mock 请求、SOCI 本地 OCI 转换、六个 cache case、三个 Karpenter/ESO schema 和 cron 算术。未执行 GPU/真实模型基准测试、容器启动测量、host SOCI 安装、cloud resource 或 secret provider。

## 参考资料

- [inference-perf0.6.1](https://github.com/kubernetes-sigs/inference-perf/tree/v0.6.1)
- [SOCI0.15 CLI](https://github.com/awslabs/soci-snapshotter/blob/v0.15.0/docs/cli-usage.md)
- [Bottlerocket1.64 bootstrap 设置](https://bottlerocket.dev/en/os/1.64.x/api/settings/bootstrap-containers/)
- [Karpenter1.14.1 CRD](https://github.com/aws/karpenter-provider-aws/tree/v1.14.1/pkg/apis/crds)
- [Karpenter 中断](https://karpenter.sh/docs/concepts/disruption/)
- [ESO2.10 ExternalSecret CRD](https://github.com/external-secrets/external-secrets/blob/helm-chart-2.10.0/config/crds/bases/external-secrets.io_externalsecrets.yaml)
- [Kubernetes Secret 更新](https://kubernetes.io/docs/concepts/configuration/secret/)
- [S3 通用 bucket ABAC 启用](https://docs.aws.amazon.com/AmazonS3/latest/userguide/buckets-tagging-enable-abac.html)
- [EBS gp3 性能](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)

## 测验

[AI/ML 最佳实践测验](../quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
