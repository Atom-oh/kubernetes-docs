# Model Training on EKS

> **Reviewed**: September 12, 2026
> **Baselines**: Slinky1.2.2, MPI Operator0.8.2, Volcano1.15.2, PyTorch2.14.0, Neuron SDK2.32.0

Distributed training requires compatible model code, data sharding, launchers, device allocation, communication and checkpoints. A valid manifest or Running Pod does not prove training or recovery works.

For single-GPU QLoRA and SageMaker AI/EKS comparison, see the [Qwen guide](sagemaker-ai/README.md), including its image support-lifecycle and execution restrictions.

## Training Pipeline

![Training from versioned data/code, validating complete checkpoints, then evaluating and registering. Parameter-server and collective paths depend on the algorithm.](../.gitbook/assets/en-ai-ml-05-model-training-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-0.html)

## Distributed Training Strategies

![Comparison of DP, TP, PP and expert-parallel partitioning and communication patterns.](../.gitbook/assets/en-ai-ml-05-model-training-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-1.html)

| Strategy | Partitioned unit | Constraints to validate |
| --- | --- | --- |
| DDP | Different data batches; model replicas | Training-state/activation memory and gradient synchronization |
| FSDP / ZeRO | Parameters, gradients and optimizer states | Stage-specific communication and checkpoint formats |
| TP | Tensor operations within layers | Head/hidden dimensions, backend and topology |
| PP | Layer stages | Microbatches, pipeline bubbles and activation transfer |
| Expert parallel | MoE experts and token dispatch | Imbalance, all-to-all and routing capacity |
| Combinations | DP/TP/PP/context/expert groups | Supported device mesh and total rank count |

Do not assume3D is always best above100B parameters. Account for optimizer, gradient, activation and communication memory beyond weights, then compare throughput and recovery cost. DDP all-reduce does not require a parameter server.

TP8×PP4×DP2 means64ranks. Global batch is **microbatch × accumulation × DP replicas**:1×32×2=64, not2048 from multiplying all TP/PP ranks again. With variable-length packing, track samples and tokens separately.

## Slurm and Slinky

The official repository is SlinkyProject/slurm-operator. Tag1.2.2 and its OCI charts were verified; GitHub releases/latest returned404, so it is not described as the latest GitHub release. The1.2 documentation lists minimum Kubernetes1.29 and Slurm25.11(data parser0.0.44). Minimum compatibility is not an operational support-lifecycle guarantee.

![Roles of Slinky Controller, NodeSet, Accounting and RestApi/LoginSet, with external storage and node provisioning.](../.gitbook/assets/en-ai-ml-05-model-training-2.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-2.html)

### Actual APIs and Lifecycle

Version1.2.2 defines Controller, NodeSet, Accounting, LoginSet, RestApi and Token in `slinky.slurm.net/v1beta1`. The former SlurmCluster/SlurmNodeSet examples are not this API. NodeSet uses controllerRef and a Pod template. Its default scalingMode behaves like StatefulSet; DaemonSet mode creates one Pod per matching Kubernetes node and ignores replicas. These are NodeSet-controller modes, not proof that slurmd always runs as a Kubernetes DaemonSet resource.

slurmctld manages job/node/partition state and scheduling; preserve its StateSaveLocation. slurmdbd handles accounting-database access and records, not a replacement for controller state. Design login/REST/job identities, filesystem permissions, Slurm keys/JWT and DB credential delivery/rotation together. Public NLB SSH exposure is not a default prerequisite.

Render the actual charts first. These commands only produce local files. An operational deployment separately requires cert-manager/CRD/operator/Slurm ordering, persistence/database, user identity and compatible Slurm images.

```bash
helm template slurm-api oci://ghcr.io/slinkyproject/charts/slurm-operator-crds   --version 1.2.2 > slurm-crds.yaml
helm template slurm-control oci://ghcr.io/slinkyproject/charts/slurm-operator   --version 1.2.2 --namespace slinky > slurm-operator.yaml
helm template slurm-example oci://ghcr.io/slinkyproject/charts/slurm   --version 1.2.2 --namespace slurm   --set-json 'nodesets={"cpu-example":{}}'   --set partitions.all.enabled=true > slurm-example.yaml
```

An Argo CD Application must reference a real chart path/revision and actual values. Invented compute.partitions/efa.enabled settings do not configure it. Review pruning, CRD/PVC deletion, Slurm draining/requeue and job termination timeouts. NodeSet scale-in and EC2 termination are separate control loops.

### Launching torchrun from Slurm

Run one torchrun launcher per node, letting it create processes per GPU. The previous eight Slurm tasks each launched eight processes, producing64processes per node. This example intends4nodes×8processes; no actual Slurm/GPU allocation was run in this audit.

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

If Slurm restricts GPU visibility per task, ensure each launcher receives all eight intended GPUs. train.py must implement LOCAL_RANK/RANK/WORLD_SIZE, device binding, DDP/sampler, versioned data/models and resume. The shell fixture verified four launchers, distinct node ranks and a common rendezvous endpoint.

## GPU Communication and EFA

FI_PROVIDER=efa selects a libfabric provider; it does not install EFA, attach interfaces or integrate NCCL. Validate supported EFA-enabled instances, driver/libfabric, aws-ofi-nccl, device plugin/Pod allocation, security groups and actual transport together. RAID0 or a subnet tag does not enable EFA.

Communicating nodes must share an AZ; a cluster placement group is recommended for performance. Ensure training Pods actually use the restricted NodePool. Bandwidth and EFA-device counts vary by instance;400Gbps is not universal. Blindly forcing old Ring/Simple, IB_DISABLE, SOCKET_IFNAME or FI_EFA_USE_DEVICE_RDMA settings can interfere with current plugins. Verify release documentation, logs and collective tests.

Karpenter budgets.nodes=0 restricts voluntary disruption paths; it does not prevent Spot reclamation, node failure, forced termination or every expiration. Check do-not-disrupt/PDB interaction with terminationGracePeriod/expireAfter and preserve checkpoint recovery. Avoid fetching floating driver installers in every bootstrap or hardcoding GPU clocks across device types.

## BioNeMo

The inspected3.0.0 is **BioNeMo Recipes**, providing TransformerEngine-based models/checkpoints and recipes for PyTorch, Accelerate and Lightning. Check recipe-specific support for ESM-2, AMPLIFY, Geneformer and others. Do not execute a BioNeMo1.5 MegaMolBART module as if it were the3.0 API. Biological evaluation and model/data permissions remain separate requirements; GPU allocation alone does not prepare the recipe.

## Trainium and Neuron

Distinguish SDK2.32.0 torch-neuronx, NeuronX Distributed Training/model implementations and Optimum Neuron paths. transformers-neuronx inference support is not general training support. Check TensorFlow/JAX/PyTorch versions against the selected hardware/SDK rather than adding arbitrary pip packages to an old2.18 DLC.

Optimum Neuron0.4.5 includes NeuronTrainer/NeuronTrainingArguments and dedicated Neuron training-model implementations. Loading a generic BertForPreTraining and passing undefined dataset/tokenizer variables is not complete TP training. Prepare supported model/config, labels/collator, tokenizer/revisions, optimizer/checkpoint formats and launcher. The CPU example's PyTorch2.14 is not a claim of Neuron SDK compatibility.

### Multi-node Jobs and Precompilation

Job parallelism=4 only starts four Pods; it does not configure ranks or rendezvous. Indexed Jobs need completionMode/index and one shared master endpoint. Setting each Pod's MASTER_ADDR to its own status.podIP points workers at different masters. Use coordinator/controller topology and supported launchers, and prepare train_lora.py, data, compile cache and devices.

neuron_parallel_compile extracts/compiles graphs; it is not a replacement for actual training. Run training separately afterward and verify cache hits, shapes and compiler/SDK revisions. See the [Neuron unit distinctions](04-inference-frameworks.md) for cores versus devices.

## Ray Train, MPI and Volcano

Use the audited Ray2.58/KubeRay1.7 [Train guide](ray/03-ray-train-tune.md). Match report-call counts across workers and report actual Checkpoint objects. get_checkpoint() retrieves prior recovery state, not a new-save context manager. resources_per_worker GPU8 does not automatically launch eight DDP processes inside one worker.

MPI Operator0.8.2 uses kubeflow.org/v2beta1. slotsPerWorker declares hostfile slots; it does not independently determine mpirun -np, mapping or GPU binding. Prepare Launcher/Worker code, MPI/SSH implementation, supported images and CRD/RBAC. Four workers×eight slots does not by itself guarantee32GPU processes.

Volcano1.15.2 minAvailable counts **Pods/members**, not EC2 nodes. Three sufficiently provisioned nodes may fit four Pods. The gang plugin applies minimum-member/resource conditions but does not guarantee simultaneous container startup or training success. Review extra workers, elastic-runtime support and RestartJob/requeue behavior.

JupyterHub GPU profiles must match actual images/device labels and authorization. g5.xlarge is A10G, not an A100 profile. Wire the configuration into the running Hub and configure per-user storage, quotas, networking and idle culling.

## Training Storage and Checkpoints

Use the audited CSI paths in the [GPU/storage guide](01-ai-ml-workloads.md). Mounting an existing FSx filesystem via static PV differs from creating a new one through dynamic provisioning. Do not invent FileSystem dataRepositoryAssociations fields or mix SCRATCH_2 with persistent-only throughput settings. Verify DRA/import/export APIs, policies and completion separately.

An EFS PVC capacity request is not a physical-storage quota. Validate access-point UID/GID, directory permissions, CSI identity, networking and mount targets. A local checkpoint is not remotely durable before S3 transfer completes.

Recovery needs model, optimizer, scheduler, RNG, scaler when used, data/sampler cursor and all sharded states. Avoid multiple ranks overwriting one file; use framework-aware distributed saving. Validate completion manifests/checksums, remote transfer and restore before deleting prior valid checkpoints. An invented checkpoint-manager image or auto_resume=true ConfigMap does not implement these functions.

### Executable Tiny CPU Example

This synthetic16sample, one-CPU-thread example performs four optimizer updates. It demonstrates accumulation, a bounded cosine schedule, temporary-file replacement and optimizer/RNG restoration. PyTorch2.14.0+cpu produced identical results for uninterrupted training and resuming after two steps. This is not GPU, distributed or remote-durability testing.

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

The example demonstrates completed-file replacement on one filesystem, not filesystem-crash/directory-metadata durability, S3 transactions or distributed checkpoint protocols. Its fixed data order also does not implement general sampler recovery. Choose checkpoint intervals/retention using save latency, failure rate, acceptable lost work and cost rather than a universal500step/five-copy rule.

## Numerical Precision and Memory Optimization

Current PyTorch APIs use torch.amp.autocast and torch.amp.GradScaler. BF16 shares FP32's exponent-bit count, not its mantissa precision or exact maximum finite value. It commonly avoids FP16-style loss scaling, but verify hardware, operations and convergence. Autocast does not convert all weights/optimizer state to BF16.

Activation checkpointing recomputes activations during backward, trading compute for memory. It differs from disk checkpoints and guarantees neither3–4x savings nor30% slowdown. Specify use_reentrant explicitly and validate gradients, dropout/RNG and stateful layers.

Flash Attention/SDPA backend selection depends on dtype, head size, device and masks. Define training state and pass dropout_p=0 during evaluation. Check API support for explicit/causal mask combinations; use_cache=False alone does not install an attention backend.

DeepSpeed0.19.6 ZeRO1 partitions optimizer state;2 adds gradients;3 adds parameters. CPU/NVMe offload is separately configured, not automatically enabled by Stage3. Distinguish upper-level integrations that replace auto values from pure DeepSpeed configuration. Buffers, activations and the largest layer prevent unlimited memory reduction.

Advance schedulers by optimizer updates rather than accumulation microsteps. Clamp progress so cosine does not rise again after the training horizon, and validate warmup/total-step bounds as in the example.

## Verification Scope

All guide/quiz prose and76unique original code blocks were reviewed. Checks cover official Slinky Helm/CRDs, MPI/Volcano APIs and SDK sources, tiny CPU training/resume and a shell-launcher fixture. No GPU/Neuron/EFA, Slurm/MPI cluster, actual pretrained model or cloud resource was run. Local code/schema verification differs from production deployment validation.

## References

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

## Quiz

[Model Training Quiz](../quizzes/ai-ml/05-model-training-quiz.md)
