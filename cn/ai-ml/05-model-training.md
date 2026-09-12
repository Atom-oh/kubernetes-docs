# EKS 上的模型训练

> **审核日期**: September 12, 2026
> **基线版本**: Slinky1.2.2, MPI Operator0.8.2, Volcano1.15.2, PyTorch2.14.0, Neuron SDK2.32.0

分布式训练需要兼容的模型代码、数据分片、启动器、设备分配、通信和检查点。有效的 manifest 或处于 Running 状态的 Pod 并不能证明训练或恢复能够正常工作。

有关单 GPU QLoRA 以及 SageMaker AI/EKS 的比较，请参阅 [Qwen 指南](sagemaker-ai/README.md)，其中包括其镜像支持生命周期和执行限制。

## 训练流水线

![从已版本化的数据/代码开始，验证完整检查点，然后评估并注册。参数服务器和集合通信路径取决于算法。](../.gitbook/assets/en-ai-ml-05-model-training-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-0.html)

## 分布式训练策略

![DP、TP、PP 和专家并行的分区及通信模式比较。](../.gitbook/assets/en-ai-ml-05-model-training-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-1.html)

| 策略 | 分区单元 | 要验证的约束 |
| --- | --- | --- |
| DDP | 不同的数据批次；模型副本 | 训练状态/激活值内存和梯度同步 |
| FSDP / ZeRO | 参数、梯度和优化器状态 | 特定 Stage 的通信和检查点格式 |
| TP | 层内的张量操作 | Head/hidden 维度、后端和拓扑 |
| PP | 层阶段 | Microbatch、流水线气泡和激活值传输 |
| Expert parallel | MoE 专家和 token 分发 | 不均衡、all-to-all 和路由容量 |
| Combinations | DP/TP/PP/context/expert 组 | 支持的设备 mesh 和总 rank 数 |

不要认为参数超过100B 时3D 总是最佳选择。除权重之外，还要考虑优化器、梯度、激活值和通信内存，然后比较吞吐量和恢复成本。DDP all-reduce 不需要参数服务器。

TP8×PP4×DP2 表示64个 rank。全局 batch 是 **microbatch × accumulation × DP 副本**：1×32×2=64，而不是再次乘以所有 TP/PP rank 得出的2048。使用可变长度 packing 时，请分别跟踪样本和 token。

## Slurm 和 Slinky

官方仓库是 SlinkyProject/slurm-operator。已验证 Tag1.2.2 及其 OCI chart；GitHub releases/latest 返回404，因此未将其描述为最新 GitHub release。1.2 文档列出了最低 Kubernetes1.29 和 Slurm25.11(data parser0.0.44) 要求。最低兼容性并不保证运行支持生命周期。

![Slinky Controller、NodeSet、Accounting 和 RestApi/LoginSet 的角色，以及外部存储和节点预置。](../.gitbook/assets/en-ai-ml-05-model-training-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-2.html)

### 实际 API 和生命周期

Version1.2.2 在 `slinky.slurm.net/v1beta1` 中定义了 Controller、NodeSet、Accounting、LoginSet、RestApi 和 Token。此前的 SlurmCluster/SlurmNodeSet 示例并非此 API。NodeSet 使用 controllerRef 和 Pod 模板。其默认 scalingMode 的行为类似 StatefulSet；DaemonSet 模式会为每个匹配的 Kubernetes 节点创建一个 Pod，并忽略 replicas。这些是 NodeSet-controller 模式，并不能证明 slurmd 始终以 Kubernetes DaemonSet 资源运行。

slurmctld 管理 job/node/partition 状态和调度；请保留其 StateSaveLocation。slurmdbd 负责 accounting 数据库访问和记录，而非 controller 状态的替代品。请一并设计 login/REST/job 身份、文件系统权限、Slurm 密钥/JWT 以及 DB 凭据的交付/轮换。公开 NLB SSH 暴露不是默认的先决条件。

先渲染实际的 chart。这些命令仅生成本地文件。运行部署还需要分别处理 cert-manager/CRD/operator/Slurm 顺序、持久化/数据库、用户身份和兼容的 Slurm 镜像。

```bash
helm template slurm-api oci://ghcr.io/slinkyproject/charts/slurm-operator-crds   --version 1.2.2 > slurm-crds.yaml
helm template slurm-control oci://ghcr.io/slinkyproject/charts/slurm-operator   --version 1.2.2 --namespace slinky > slurm-operator.yaml
helm template slurm-example oci://ghcr.io/slinkyproject/charts/slurm   --version 1.2.2 --namespace slurm   --set-json 'nodesets={"cpu-example":{}}'   --set partitions.all.enabled=true > slurm-example.yaml
```

Argo CD Application 必须引用真实的 chart 路径/revision 和实际 values。虚构的 compute.partitions/efa.enabled 设置不会对其进行配置。审查 pruning、CRD/PVC 删除、Slurm draining/requeue 以及 job 终止超时。NodeSet scale-in 和 EC2 终止是独立的控制循环。

### 从 Slurm 启动 torchrun

每个节点运行一个 torchrun launcher，让它为每个 GPU 创建进程。此前的八个 Slurm task 各自启动八个进程，导致每节点有64个进程。本示例目标为4个节点×8个进程；本次审查中未运行实际的 Slurm/GPU 分配。

```bash
#!/bin/bash
#SBATCH --job-name=distributed-training
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=16
#SBATCH --time=01:00:00
set -euo pipefail

: "${SLURM_NNODES:?Run within an approved Slurm allocation}"
: "${SLURM_JOB_ID:?}"
: "${SLURM_JOB_NODELIST:?}"
export MASTER_ADDR
MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export MASTER_PORT=29500

# One torchrun launcher per Slurm node, eight training processes per launcher.
# train.py, dependencies, data, credentials and checkpoints must be prepared.
srun --ntasks="$SLURM_NNODES" --ntasks-per-node=1 bash -c '
  exec torchrun \
    --nnodes="$SLURM_NNODES" \
    --nproc-per-node=8 \
    --node-rank="$SLURM_PROCID" \
    --rdzv-id="$SLURM_JOB_ID" \
    --rdzv-backend=c10d \
    --rdzv-endpoint="$MASTER_ADDR:$MASTER_PORT" \
    /workspace/train.py
'
```

如果 Slurm 限制每个 task 的 GPU 可见性，请确保每个 launcher 都能接收到预期的全部八个 GPU。train.py 必须实现 LOCAL_RANK/RANK/WORLD_SIZE、设备绑定、DDP/sampler、已版本化的数据/模型和 resume。shell fixture 验证了四个 launcher、不同的 node rank 以及共同的 rendezvous endpoint。

## GPU 通信和 EFA

FI_PROVIDER=efa 选择 libfabric provider；它不会安装 EFA、附加接口或集成 NCCL。请一并验证支持 EFA 的实例、driver/libfabric、aws-ofi-nccl、device plugin/Pod 分配、安全组和实际传输。RAID0 或 subnet tag 不会启用 EFA。

通信节点必须共享一个 AZ；为获得性能，建议使用 cluster placement group。确保训练 Pod 实际使用受限的 NodePool。带宽和 EFA-device 数量因实例而异；400Gbps 并非通用。盲目强制旧的 Ring/Simple、IB_DISABLE、SOCKET_IFNAME 或 FI_EFA_USE_DEVICE_RDMA 设置可能会干扰当前 plugin。请验证 release 文档、日志和 collective 测试。

Karpenter budgets.nodes=0 会限制自愿中断路径；它无法阻止 Spot 回收、节点故障、强制终止或所有 expiration。检查 do-not-disrupt/PDB 与 terminationGracePeriod/expireAfter 的交互，并保持检查点恢复能力。避免在每次 bootstrap 时获取浮动的 driver installer，或跨设备类型硬编码 GPU 时钟。

## BioNeMo

所检查的3.0.0 是 **BioNeMo Recipes**，为 PyTorch、Accelerate 和 Lightning 提供基于 TransformerEngine 的模型/检查点及 recipes。检查 ESM-2、AMPLIFY、Geneformer 等的 recipe 特定支持。不要像使用3.0 API 一样执行 BioNeMo1.5 MegaMolBART module。生物学评估以及模型/数据权限仍是独立要求；仅分配 GPU 并不会准备好 recipe。

## Trainium 和 Neuron

区分 SDK2.32.0 torch-neuronx、NeuronX Distributed Training/模型实现和 Optimum Neuron 路径。transformers-neuronx inference 支持并不等同于通用 training 支持。请根据所选硬件/SDK 检查 TensorFlow/JAX/PyTorch 版本，而不是向旧的2.18 DLC 添加任意 pip 包。

Optimum Neuron0.4.5 包含 NeuronTrainer/NeuronTrainingArguments 以及专用的 Neuron training-model 实现。加载通用 BertForPreTraining 并传入未定义的 dataset/tokenizer 变量，不构成完整的 TP training。准备受支持的 model/config、labels/collator、tokenizer/revisions、optimizer/checkpoint 格式和 launcher。CPU 示例中的 PyTorch2.14 并不表示与 Neuron SDK 兼容。

### 多节点 Job 和预编译

Job parallelism=4 仅启动四个 Pod；它不会配置 rank 或 rendezvous。Indexed Job 需要 completionMode/index 和一个共享 master endpoint。将每个 Pod 的 MASTER_ADDR 设置为自己的 status.podIP，会使 worker 指向不同的 master。使用 coordinator/controller 拓扑和受支持的 launcher，并准备 train_lora.py、数据、compile cache 和设备。

neuron_parallel_compile 会提取/编译图；它不能替代实际 training。之后单独运行 training，并验证 cache hit、shape 以及 compiler/SDK revision。有关 core 与 device 的区别，请参阅 [Neuron 单元区别](04-inference-frameworks.md)。

## Ray Train、MPI 和 Volcano

使用经审查的 Ray2.58/KubeRay1.7 [Train 指南](ray/03-ray-train-tune.md)。匹配 worker 之间的 report-call 数量，并报告实际的 Checkpoint 对象。get_checkpoint() 获取先前的恢复状态，而不是新的 save context manager。resources_per_worker GPU8 不会自动在一个 worker 内启动八个 DDP 进程。

MPI Operator0.8.2 使用 kubeflow.org/v2beta1。slotsPerWorker 声明 hostfile slot；它不会独立确定 mpirun -np、mapping 或 GPU binding。准备 Launcher/Worker 代码、MPI/SSH 实现、支持的镜像和 CRD/RBAC。四个 worker×八个 slot 本身并不能保证32个 GPU 进程。

Volcano1.15.2 minAvailable 计数的是 **Pod/member**，而不是 EC2 节点。三个配置充足的节点可能容纳四个 Pod。gang plugin 应用 minimum-member/resource 条件，但不保证 container 同时启动或 training 成功。审查额外 worker、elastic-runtime 支持及 RestartJob/requeue 行为。

JupyterHub GPU profile 必须与实际镜像/device label 和授权匹配。g5.xlarge 是 A10G，而不是 A100 profile。将配置接入正在运行的 Hub，并配置每用户存储、quota、networking 和 idle culling。

## 训练存储和检查点

使用 [GPU/存储指南](01-ai-ml-workloads.md) 中经审查的 CSI 路径。通过 static PV 挂载现有 FSx 文件系统与通过 dynamic provisioning 创建新文件系统不同。不要虚构 FileSystem dataRepositoryAssociations 字段，也不要将 SCRATCH_2 与仅适用于 persistent 的 throughput 设置混用。分别验证 DRA/import/export API、policy 和完成状态。

EFS PVC capacity request 并不是物理存储 quota。验证 access-point UID/GID、目录权限、CSI identity、networking 和 mount target。在 S3 transfer 完成之前，本地 checkpoint 不具备远程持久性。

恢复需要 model、optimizer、scheduler、RNG、scaler（如有使用）、data/sampler cursor 以及所有 sharded state。避免多个 rank 覆盖同一文件；使用 framework-aware 的分布式保存。验证完成 manifest/checksum、远程 transfer 和 restore，然后再删除先前有效的 checkpoint。虚构的 checkpoint-manager 镜像或 auto_resume=true ConfigMap 并不能实现这些功能。

### 可执行的小型 CPU 示例

这个合成的16个样本、单 CPU thread 示例执行四次 optimizer update。它演示 accumulation、有界 cosine schedule、temporary-file replacement 以及 optimizer/RNG 恢复。PyTorch2.14.0+cpu 对未中断 training 和在两步后 resume 的 training 产生了相同结果。这不是 GPU、分布式或远程持久性测试。

```python
from pathlib import Path
import math
import os
import tempfile
import torch


def lr_factor(step, warmup_steps, total_steps, min_ratio=0.1):
    if not 0 <= warmup_steps < total_steps or not 0 <= min_ratio <= 1:
        raise ValueError("Invalid schedule bounds")
    if step < 0:
        raise ValueError("Step must be non-negative")
    if step < warmup_steps:
        return step / max(1, warmup_steps)
    progress = min(1.0, (step - warmup_steps) / (total_steps - warmup_steps))
    return min_ratio + (1 - min_ratio) * (1 + math.cos(math.pi * progress)) / 2


def save_checkpoint(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = output.name
            torch.save(state, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def train_toy(checkpoint_path, stop_after=4, resume=False):
    # Tiny deterministic CPU example; no GPU, dataset or model download.
    torch.set_num_threads(1)
    torch.manual_seed(17)
    model = torch.nn.Linear(2, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05, momentum=0.9)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda step: lr_factor(step, 1, 4)
    )
    inputs = torch.arange(32, dtype=torch.float32).reshape(16, 2) / 32
    targets = inputs.sum(dim=1, keepdim=True)
    start = 0
    if resume:
        saved = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        scheduler.load_state_dict(saved["scheduler"])
        torch.set_rng_state(saved["torch_rng"])
        start = saved["optimizer_step"]
    if not start <= stop_after <= 4:
        raise ValueError("Invalid stopping point")
    for step in range(start, stop_after):
        optimizer.zero_grad(set_to_none=True)
        # Two equal-sized microbatches per optimizer update.
        for microbatch in range(2):
            offset = step * 4 + microbatch * 2
            prediction = model(inputs[offset:offset + 2])
            loss = torch.nn.functional.mse_loss(prediction, targets[offset:offset + 2]) / 2
            loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        save_checkpoint(checkpoint_path, {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "optimizer_step": step + 1,
            "torch_rng": torch.get_rng_state(),
        })
    return {name: value.detach().clone() for name, value in model.state_dict().items()}


if __name__ == "__main__":
    path = Path("toy-training.pt")
    train_toy(path, stop_after=2)
    train_toy(path, stop_after=4, resume=True)
    print("Completed four CPU optimizer updates, including checkpoint resume.")
```

该示例演示的是单一文件系统上的已完成文件替换，而不是文件系统崩溃/目录元数据持久性、S3 transaction 或分布式 checkpoint protocol。其固定的数据顺序也没有实现通用 sampler 恢复。请根据保存延迟、故障率、可接受的工作损失和成本来选择 checkpoint interval/retention，而不是采用通用的500 step/五副本规则。

## 数值精度和内存优化

当前 PyTorch API 使用 torch.amp.autocast 和 torch.amp.GradScaler。BF16 与 FP32 具有相同的 exponent-bit 数，而非相同的 mantissa 精度或精确的最大有限值。它通常无需 FP16 式 loss scaling，但仍需验证硬件、操作和收敛性。Autocast 不会将所有 weight/optimizer state 转换为 BF16。

Activation checkpointing 会在 backward 期间重新计算 activation，以计算换取内存。它不同于磁盘 checkpoint，且不保证3–4x 节省或30% slowdown。明确指定 use_reentrant，并验证 gradient、dropout/RNG 和 stateful layer。

Flash Attention/SDPA backend 选择取决于 dtype、head size、device 和 mask。定义 training state，并在 evaluation 期间传入 dropout_p=0。检查 explicit/causal mask 组合的 API 支持；仅使用 use_cache=False 并不会安装 attention backend。

DeepSpeed0.19.6 ZeRO1 对 optimizer state 分区；2 还会分区 gradient；3 还会分区 parameter。CPU/NVMe offload 需单独配置，并不会由 Stage3 自动启用。区分会替换 auto value 的上层 integration 与纯 DeepSpeed 配置。buffer、activation 和最大 layer 会阻止无限制的内存缩减。

按 optimizer update 而非 accumulation microstep 推进 scheduler。限制 progress，以使 cosine 在 training horizon 后不会再次上升，并如示例所示验证 warmup/total-step 边界。

## 验证范围

已审查全部指南/quiz prose 和76个唯一的原始 code block。检查涵盖官方 Slinky Helm/CRD、MPI/Volcano API 和 SDK source、小型 CPU training/resume 以及 shell-launcher fixture。未运行 GPU/Neuron/EFA、Slurm/MPI cluster、实际 pretrained model 或 cloud resource。本地 code/schema 验证不同于生产部署验证。

## 参考资料

- [Slinky 1.2.2](https://github.com/SlinkyProject/slurm-operator/tree/v1.2.2)
- [Slurm controller](https://slurm.schedmd.com/slurmctld.html)
- [Slurm accounting daemon](https://slurm.schedmd.com/slurmdbd.html)
- [MPI Operator 0.8.2](https://github.com/kubeflow/mpi-operator/tree/v0.8.2)
- [Volcano 1.15.2 gang plugin](https://github.com/volcano-sh/volcano/blob/v1.15.2/pkg/scheduler/plugins/gang/gang.go)
- [EKS EFA networking](https://docs.aws.amazon.com/eks/latest/best-practices/aiml-networking.html)
- [BioNeMo 3.0.0 recipes](https://github.com/NVIDIA/bionemo-framework/tree/v3.0.0)
- [Optimum Neuron 0.4.5](https://github.com/huggingface/optimum-neuron/tree/v0.4.5)
- [Neuron SDK 2.32.0](https://github.com/aws-neuron/aws-neuron-sdk/tree/v2.32.0)
- [PyTorch 2.14 launcher](https://github.com/pytorch/pytorch/blob/v2.14.0/torch/distributed/run.py)
- [DeepSpeed 0.19.6 ZeRO configuration](https://github.com/deepspeedai/DeepSpeed/blob/v0.19.6/deepspeed/runtime/zero/config.py)

## 测验

[模型训练测验](../quizzes/ai-ml/05-model-training-quiz.md)
