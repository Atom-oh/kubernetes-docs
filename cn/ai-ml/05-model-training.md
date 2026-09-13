# EKS 上的模型训练

> **最后更新**: September 12, 2026
> **基准**: Slinky1.2.2, MPI Operator0.8.2, Volcano1.15.2, PyTorch2.14.0, Neuron SDK2.32.0

分布式训练需要兼容的模型代码、数据分片、启动器、设备分配、通信和 checkpoint。一个有效的 manifest 或处于 Running 状态的 Pod 并不能证明训练或恢复能够正常工作。

有关单 GPU QLoRA 以及 SageMaker AI/EKS 对比，请参阅 [Qwen 指南](sagemaker-ai/README.md)，其中包括镜像支持生命周期和执行限制。

## 训练流水线

![从已版本化的数据/代码开始，验证完整 checkpoint，随后评估并注册。参数服务器和 collective 路径取决于算法。](../.gitbook/assets/en-ai-ml-05-model-training-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-0.html)

## 分布式训练策略

![DP、TP、PP 和 expert-parallel 的分区与通信模式对比。](../.gitbook/assets/en-ai-ml-05-model-training-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-1.html)

| 策略 | 分区单元 | 需验证的约束 |
| --- | --- | --- |
| DDP | 不同数据批次；模型副本 | 训练状态/activation 内存和梯度同步 |
| FSDP / ZeRO | 参数、梯度和 optimizer 状态 | 特定 Stage 的通信和 checkpoint 格式 |
| TP | 层内的 tensor 运算 | Head/hidden 维度、backend 和拓扑 |
| PP | Layer stage | Microbatch、pipeline bubble 和 activation 传输 |
| Expert parallel | MoE expert 和 token 分发 | 不平衡、all-to-all 和路由容量 |
| 组合 | DP/TP/PP/context/expert group | 支持的 device mesh 和总 rank 数 |

不要假设参数量超过100B时3D 始终最佳。除 weights 外，还应考虑 optimizer、gradient、activation 和 communication 内存，然后比较吞吐量和恢复成本。DDP all-reduce 不需要 parameter server。

TP8×PP4×DP2 表示64个 rank。全局 batch 为 **microbatch × accumulation × DP replicas**：1×32×2=64，而不是再次乘以所有 TP/PP rank 后得到的2048。使用可变长度 packing 时，应分别跟踪 sample 和 token。

## Slurm 和 Slinky

官方仓库是 SlinkyProject/slurm-operator。已验证 Tag1.2.2 及其 OCI chart；GitHub releases/latest 返回404，因此未将其描述为最新 GitHub release。1.2 文档列出的最低要求为 Kubernetes1.29 和 Slurm25.11(data parser0.0.44)。最低兼容性并不保证运行支持生命周期。

![Slinky Controller、NodeSet、Accounting 和 RestApi/LoginSet 的角色，以及外部存储和节点配置。](../.gitbook/assets/en-ai-ml-05-model-training-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-2.html)

### 实际 API 和生命周期

版本1.2.2 在 `slinky.slurm.net/v1beta1` 中定义了 Controller、NodeSet、Accounting、LoginSet、RestApi 和 Token。先前的 SlurmCluster/SlurmNodeSet 示例并非此 API。NodeSet 使用 controllerRef 和 Pod template。其默认 scalingMode 的行为类似 StatefulSet；DaemonSet 模式会在每个匹配的 Kubernetes node 上创建一个 Pod，并忽略 replicas。这些是 NodeSet-controller 模式，并不能证明 slurmd 始终作为 Kubernetes DaemonSet resource 运行。

slurmctld 管理 job/node/partition 状态和调度；请保留其 StateSaveLocation。slurmdbd 处理 accounting database 的访问和记录，并不替代 controller 状态。请一并设计 login/REST/job identity、filesystem permission、Slurm key/JWT 以及 DB credential 的交付/轮换。公共 NLB SSH 暴露并非默认前提条件。

请先 render 实际 chart。以下命令只会生成本地文件。生产部署还需要分别处理 cert-manager/CRD/operator/Slurm 顺序、持久化/database、user identity 和兼容的 Slurm image。

```bash
helm template slurm-api oci://ghcr.io/slinkyproject/charts/slurm-operator-crds   --version 1.2.2 > slurm-crds.yaml
helm template slurm-control oci://ghcr.io/slinkyproject/charts/slurm-operator   --version 1.2.2 --namespace slinky > slurm-operator.yaml
helm template slurm-example oci://ghcr.io/slinkyproject/charts/slurm   --version 1.2.2 --namespace slurm   --set-json 'nodesets={"cpu-example":{}}'   --set partitions.all.enabled=true > slurm-example.yaml
```

Argo CD Application 必须引用真实的 chart path/revision 和实际 values。虚构的 compute.partitions/efa.enabled 设置不会配置它。检查 pruning、CRD/PVC 删除、Slurm draining/requeue 以及 job termination timeout。NodeSet scale-in 和 EC2 termination 是独立的控制循环。

### 从 Slurm 启动 torchrun

每个 node 运行一个 torchrun launcher，让它为每个 GPU 创建进程。此前的八个 Slurm task 各自启动八个进程，导致每个 node 产生64个进程。此示例计划使用4个 node×8个进程；本次审计未实际运行 Slurm/GPU allocation。

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

如果 Slurm 按 task 限制 GPU 可见性，请确保每个 launcher 都能获得预期的全部八个 GPU。train.py 必须实现 LOCAL_RANK/RANK/WORLD_SIZE、device binding、DDP/sampler、已版本化的数据/models 以及 resume。该 shell fixture 验证了四个 launcher、不同的 node rank 和一个共同的 rendezvous endpoint。

## GPU 通信和 EFA

FI_PROVIDER=efa 选择 libfabric provider；它不会安装 EFA、附加 interface 或集成 NCCL。请一并验证受支持的已启用 EFA 的 instance、driver/libfabric、aws-ofi-nccl、device plugin/Pod allocation、security group 和实际 transport。RAID0 或 subnet tag 不会启用 EFA。

通信 node 必须共享一个 AZ；建议使用 cluster placement group 以获得性能。确保训练 Pod 确实使用受限的 NodePool。带宽和 EFA-device 数量因 instance 而异；400Gbps 并不通用。盲目强制使用旧的 Ring/Simple、IB_DISABLE、SOCKET_IFNAME 或 FI_EFA_USE_DEVICE_RDMA 设置可能会干扰当前 plugin。请验证 release documentation、log 和 collective test。

Karpenter budgets.nodes=0 限制 voluntary disruption 路径；它不能阻止 Spot 回收、node failure、forced termination 或所有 expiration。检查 do-not-disrupt/PDB 与 terminationGracePeriod/expireAfter 的交互，并保留 checkpoint recovery。避免在每次 bootstrap 中获取浮动的 driver installer，或在不同 device type 上硬编码 GPU clock。

## BioNeMo

经检查的3.0.0 是 **BioNeMo Recipes**，提供基于 TransformerEngine 的 model/checkpoint，以及适用于 PyTorch、Accelerate 和 Lightning 的 recipe。请检查 ESM-2、AMPLIFY、Geneformer 等的 recipe-specific 支持。不要将 BioNeMo1.5 MegaMolBART module 当作3.0 API 执行。生物学评估以及 model/data permission 仍是独立要求；仅分配 GPU 并不能准备好 recipe。

## Trainium 和 Neuron

区分 SDK2.32.0 torch-neuronx、NeuronX Distributed Training/model implementation 和 Optimum Neuron 路径。transformers-neuronx inference 支持并不等于通用 training 支持。应根据所选 hardware/SDK 检查 TensorFlow/JAX/PyTorch version，而不是向旧版2.18 DLC 添加任意 pip package。

Optimum Neuron0.4.5 包括 NeuronTrainer/NeuronTrainingArguments 以及专用 Neuron training-model implementation。加载通用 BertForPreTraining 并传入未定义的 dataset/tokenizer variable 并不构成完整 TP training。准备好支持的 model/config、label/collator、tokenizer/revision、optimizer/checkpoint format 和 launcher。CPU 示例中的 PyTorch2.14 并不表示 Neuron SDK 兼容性。

### Multi-node Job 和预编译

Job parallelism=4 只会启动四个 Pod；它不会配置 rank 或 rendezvous。Indexed Job 需要 completionMode/index 和一个共享 master endpoint。将每个 Pod 的 MASTER_ADDR 设置为各自的 status.podIP 会使 worker 指向不同的 master。请使用 coordinator/controller 拓扑和受支持的 launcher，并准备好 train_lora.py、data、compile cache 和 device。

neuron_parallel_compile 会提取/编译 graph；它不能替代实际 training。之后请单独运行 training，并验证 cache hit、shape 以及 compiler/SDK revision。关于 core 与 device 的区别，请参阅 [Neuron 单元区别](04-inference-frameworks.md)。

## Ray Train、MPI 和 Volcano

使用经过审计的 Ray2.58/KubeRay1.7 [Train 指南](ray/03-ray-train-tune.md)。匹配 worker 间的 report-call count，并报告实际 Checkpoint object。get_checkpoint() 获取的是先前的 recovery state，而非新的 save context manager。resources_per_worker GPU8 不会自动在一个 worker 内启动八个 DDP process。

MPI Operator0.8.2 使用 kubeflow.org/v2beta1。slotsPerWorker 声明 hostfile slot；它并不独立决定 mpirun -np、mapping 或 GPU binding。准备 Launcher/Worker code、MPI/SSH implementation、支持的 image 和 CRD/RBAC。四个 worker×八个 slot 本身并不能保证32个 GPU process。

Volcano1.15.2 minAvailable 统计的是 **Pod/member**，而非 EC2 node。三个资源充足的 node 可能容纳四个 Pod。gang plugin 应用 minimum-member/resource 条件，但不保证 container 同时启动或 training 成功。检查 extra worker、elastic-runtime 支持和 RestartJob/requeue 行为。

JupyterHub GPU profile 必须匹配实际 image/device label 和 authorization。g5.xlarge 是 A10G，而不是 A100 profile。将配置接入正在运行的 Hub，并配置 per-user storage、quota、networking 和 idle culling。

## 训练存储和 Checkpoint

使用 [GPU/storage 指南](01-ai-ml-workloads.md) 中经过审计的 CSI path。通过 static PV 挂载现有 FSx filesystem 与通过 dynamic provisioning 创建新的 filesystem 不同。不要虚构 FileSystem dataRepositoryAssociations field，或将 SCRATCH_2 与仅适用于 persistent 的 throughput setting 混用。请分别验证 DRA/import/export API、policy 和完成情况。

EFS PVC capacity request 不是物理 storage quota。验证 access-point UID/GID、directory permission、CSI identity、networking 和 mount target。S3 transfer 完成前，本地 checkpoint 并非远程持久。

恢复需要 model、optimizer、scheduler、RNG、scaler（如使用）、data/sampler cursor 以及所有 sharded state。避免多个 rank 覆盖同一 file；应使用 framework-aware distributed saving。在删除先前有效的 checkpoint 前，验证 completion manifest/checksum、remote transfer 和 restore。虚构的 checkpoint-manager image 或 auto_resume=true ConfigMap 不会实现这些功能。

### 可执行的微型 CPU 示例

这个合成的16个 sample、单 CPU thread 示例执行四次 optimizer update。它演示 accumulation、有界 cosine schedule、temporary-file replacement 和 optimizer/RNG restoration。PyTorch2.14.0+cpu 对不中断训练和两步后 resume 的训练产生了相同结果。这不是 GPU、distributed 或 remote-durability 测试。

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

该示例演示了单个 filesystem 上已完成文件的替换，而非 filesystem-crash/directory-metadata durability、S3 transaction 或 distributed checkpoint protocol。其固定 data order 也未实现通用 sampler recovery。应根据 save latency、failure rate、可接受的工作损失和成本选择 checkpoint interval/retention，而不是采用通用的500 step/五副本规则。

## 数值精度和内存优化

当前 PyTorch API 使用 torch.amp.autocast 和 torch.amp.GradScaler。BF16 与 FP32 具有相同的 exponent-bit 数量，但不具有相同的 mantissa precision 或精确的最大有限值。它通常避免类似 FP16 的 loss scaling，但应验证 hardware、operation 和收敛性。Autocast 不会将所有 weight/optimizer state 转换为 BF16。

Activation checkpointing 会在 backward 期间重新计算 activation，以计算换取内存。它不同于 disk checkpoint，且不保证节省3–4倍内存或增加30% slowdown。请显式指定 use_reentrant，并验证 gradient、dropout/RNG 和 stateful layer。

Flash Attention/SDPA backend 选择取决于 dtype、head size、device 和 mask。定义 training state，并在 evaluation 期间传入 dropout_p=0。检查 explicit/causal mask 组合的 API 支持；仅 use_cache=False 不会安装 attention backend。

DeepSpeed0.19.6 ZeRO1 对 optimizer state 分区；2增加 gradient；3增加 parameter。CPU/NVMe offload 需单独配置，并不会由 Stage3 自动启用。区分替换 auto value 的上层 integration 与纯 DeepSpeed configuration。buffer、activation 和最大 layer 会阻止无限的内存缩减。

按 optimizer update 而非 accumulation microstep 推进 scheduler。限制 progress，避免 cosine 在训练周期结束后再次上升，并如示例所示验证 warmup/total-step bound。

## 验证范围

已审阅所有指南/quiz prose 和76个唯一的原始 code block。检查涵盖官方 Slinky Helm/CRD、MPI/Volcano API 和 SDK source、微型 CPU training/resume 以及 shell-launcher fixture。未运行 GPU/Neuron/EFA、Slurm/MPI cluster、实际 pretrained model 或 cloud resource。本地 code/schema verification 与 production deployment validation 不同。

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
