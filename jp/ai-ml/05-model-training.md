# EKS でのモデル学習

> **対応バージョン**: Kubernetes 1.31, 1.32, 1.33
> **最終更新**: February 25, 2026

モデル学習は、AI/ML ライフサイクルの中でも最もリソースを多く消費するワークロードの 1 つです。この章では、分散学習戦略、Slinky による Slurm 統合、GPU および Trainium ベースの学習、Amazon EKS 上で大規模な学習ジョブを実行するためのベストプラクティスについて説明します。

## 学習パイプラインの概要

Kubernetes 上の典型的なモデル学習パイプラインには、データ準備からモデル評価までの複数のステージが含まれます。

```mermaid
flowchart LR
    subgraph DataPrep [Data Preparation]
        S3Data[(S3 Data Lake)]
        DataLoader[Data Loader Pod]
        Preprocessing[Preprocessing Job]
    end

    subgraph Training [Distributed Training]
        Scheduler[Job Scheduler]
        Workers[Worker Pods]
        PS[Parameter Server]
        AllReduce[AllReduce Communication]
    end

    subgraph Checkpointing [Checkpointing]
        FSxLustre[(FSx for Lustre)]
        CheckpointMgr[Checkpoint Manager]
    end

    subgraph Evaluation [Model Evaluation]
        EvalJob[Evaluation Job]
        Metrics[Metrics Collection]
        ModelRegistry[(Model Registry)]
    end

    S3Data --> DataLoader
    DataLoader --> Preprocessing
    Preprocessing --> Scheduler
    Scheduler --> Workers
    Workers <--> PS
    Workers <--> AllReduce
    Workers --> FSxLustre
    FSxLustre --> CheckpointMgr
    CheckpointMgr --> EvalJob
    EvalJob --> Metrics
    Metrics --> ModelRegistry

    classDef dataComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef trainingComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef storageComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef evalComponent fill:#76B900,stroke:#333,stroke-width:1px,color:white;

    class S3Data,DataLoader,Preprocessing dataComponent;
    class Scheduler,Workers,PS,AllReduce trainingComponent;
    class FSxLustre,CheckpointMgr storageComponent;
    class EvalJob,Metrics,ModelRegistry evalComponent;
```

## 分散学習戦略

大規模モデルの学習では、複数の GPU とノードに計算を分散する必要があります。効率的な学習には、さまざまな並列化戦略を理解することが重要です。

```mermaid
flowchart TD
    subgraph DataParallelism [Data Parallelism]
        DP_Model1[Model Replica 1]
        DP_Model2[Model Replica 2]
        DP_Model3[Model Replica 3]
        DP_Data1[Data Shard 1]
        DP_Data2[Data Shard 2]
        DP_Data3[Data Shard 3]
        DP_Sync[Gradient Sync<br/>AllReduce]

        DP_Data1 --> DP_Model1
        DP_Data2 --> DP_Model2
        DP_Data3 --> DP_Model3
        DP_Model1 --> DP_Sync
        DP_Model2 --> DP_Sync
        DP_Model3 --> DP_Sync
    end

    subgraph TensorParallelism [Tensor Parallelism]
        TP_Layer[Single Layer]
        TP_GPU1[GPU 1: Columns 0-N/2]
        TP_GPU2[GPU 2: Columns N/2-N]
        TP_Combine[Combine Results]

        TP_Layer --> TP_GPU1
        TP_Layer --> TP_GPU2
        TP_GPU1 --> TP_Combine
        TP_GPU2 --> TP_Combine
    end

    subgraph PipelineParallelism [Pipeline Parallelism]
        PP_Stage1[Stage 1: Layers 1-4<br/>GPU 1]
        PP_Stage2[Stage 2: Layers 5-8<br/>GPU 2]
        PP_Stage3[Stage 3: Layers 9-12<br/>GPU 3]
        PP_Micro[Micro-batches]

        PP_Micro --> PP_Stage1
        PP_Stage1 --> PP_Stage2
        PP_Stage2 --> PP_Stage3
    end

    subgraph ExpertParallelism [Expert Parallelism - MoE]
        EP_Router[Router/Gating]
        EP_Expert1[Expert 1<br/>GPU 1]
        EP_Expert2[Expert 2<br/>GPU 2]
        EP_Expert3[Expert 3<br/>GPU 3]
        EP_Expert4[Expert 4<br/>GPU 4]
        EP_Output[Combined Output]

        EP_Router --> EP_Expert1
        EP_Router --> EP_Expert2
        EP_Router --> EP_Expert3
        EP_Router --> EP_Expert4
        EP_Expert1 --> EP_Output
        EP_Expert2 --> EP_Output
        EP_Expert3 --> EP_Output
        EP_Expert4 --> EP_Output
    end

    classDef dpComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef tpComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef ppComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef epComponent fill:#76B900,stroke:#333,stroke-width:1px,color:white;

    class DP_Model1,DP_Model2,DP_Model3,DP_Data1,DP_Data2,DP_Data3,DP_Sync dpComponent;
    class TP_Layer,TP_GPU1,TP_GPU2,TP_Combine tpComponent;
    class PP_Stage1,PP_Stage2,PP_Stage3,PP_Micro ppComponent;
    class EP_Router,EP_Expert1,EP_Expert2,EP_Expert3,EP_Expert4,EP_Output epComponent;
```

### 並列化戦略の比較

| 戦略 | 最適な用途 | メモリ効率 | 通信オーバーヘッド | 実装の複雑さ |
|----------|----------|-------------------|----------------------|---------------------------|
| **Data Parallelism** | 単一 GPU メモリに収まるモデル | 低（GPU ごとに完全なモデル） | 中（勾配同期） | 低 |
| **Tensor Parallelism** | 大きなレイヤー（attention、FFN） | 高（レイヤー分割） | 高（レイヤー内） | 中 |
| **Pipeline Parallelism** | 非常に深いモデル | 高（ステージを分散） | 低（ステージ境界） | 中 |
| **Expert Parallelism** | MoE モデル（Mixtral、Switch） | 中 | 中（ルーティング） | 高 |
| **3D Parallelism** | 100B+ パラメータモデル | 最高 | 複合 | 非常に高 |

### 適切な戦略の選択

```yaml
# Decision matrix for parallelism selection
# Model Size < 10B parameters, fits in single GPU
strategy: data_parallelism
reason: Simple, efficient gradient synchronization

# Model Size 10B-100B parameters
strategy: data_parallelism + tensor_parallelism
reason: Split attention layers across GPUs within node

# Model Size > 100B parameters
strategy: 3d_parallelism  # DP + TP + PP
reason: Combine all strategies for maximum efficiency
```

## Slinky による EKS 上の Slurm

Slinky は、使い慣れた Slurm ワークロードマネージャーを Kubernetes にもたらし、AI/ML 学習ワークロード向けの HPC スタイルのジョブスケジューリングを可能にします。

### Slinky アーキテクチャ

```mermaid
flowchart TD
    subgraph EKSCluster [Amazon EKS Cluster]
        subgraph SlurmControl [Slurm Control Plane]
            Slurmctld[slurmctld<br/>Controller Daemon]
            Slurmdbd[slurmdbd<br/>Database Daemon]
            SlurmREST[slurmrestd<br/>REST API]
        end

        subgraph ComputeNodes [Compute Nodes]
            Slurmd1[slurmd Pod 1<br/>8x A100 GPU]
            Slurmd2[slurmd Pod 2<br/>8x A100 GPU]
            Slurmd3[slurmd Pod 3<br/>8x A100 GPU]
            Slurmd4[slurmd Pod 4<br/>8x A100 GPU]
        end

        subgraph Access [User Access]
            LoginPod[Login Pod<br/>SSH via NLB]
            JupyterHub[JupyterHub]
        end

        subgraph Storage [Shared Storage]
            FSxLustre[(FSx for Lustre)]
        end

        subgraph Scaling [Auto Scaling]
            Karpenter[Karpenter]
            NodePool[GPU NodePool]
        end
    end

    subgraph External [External Services]
        ArgoCD[ArgoCD<br/>GitOps Deployment]
        ECR[Amazon ECR<br/>AWS DLC Images]
        NLB[Network Load Balancer]
    end

    ArgoCD --> SlurmControl
    ECR --> ComputeNodes
    NLB --> LoginPod

    Slurmctld --> Slurmdbd
    Slurmctld --> SlurmREST
    Slurmctld --> Slurmd1
    Slurmctld --> Slurmd2
    Slurmctld --> Slurmd3
    Slurmctld --> Slurmd4

    LoginPod --> Slurmctld
    JupyterHub --> SlurmREST

    Slurmd1 --> FSxLustre
    Slurmd2 --> FSxLustre
    Slurmd3 --> FSxLustre
    Slurmd4 --> FSxLustre

    Karpenter --> NodePool
    NodePool --> ComputeNodes

    classDef controlComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef computeComponent fill:#76B900,stroke:#333,stroke-width:1px,color:white;
    classDef accessComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef storageComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef externalComponent fill:#E6522C,stroke:#333,stroke-width:1px,color:white;

    class Slurmctld,Slurmdbd,SlurmREST controlComponent;
    class Slurmd1,Slurmd2,Slurmd3,Slurmd4 computeComponent;
    class LoginPod,JupyterHub accessComponent;
    class FSxLustre storageComponent;
    class ArgoCD,ECR,NLB,Karpenter,NodePool externalComponent;
```

### Slinky コンポーネント

| コンポーネント | 説明 | Kubernetes Resource |
|-----------|-------------|---------------------|
| **slurmctld** | ジョブ、パーティション、リソースを管理する中央コントローラー | PVC 付き StatefulSet |
| **slurmdbd** | ジョブアカウンティングとクラスタ状態のためのデータベースデーモン | MySQL/MariaDB 付き StatefulSet |
| **slurmd** | 各ワーカーノードで実行されるコンピュートデーモン | GPU ノード上の DaemonSet |
| **slurmrestd** | プログラムによるジョブ送信用の REST API | Service 付き Deployment |
| **Login Pod** | ユーザーがジョブを送信するための SSH アクセスポイント | NLB で公開される Pod |

### Slinky CRD

Slinky は、Slurm クラスタを管理するための Custom Resource Definitions を導入します。

```yaml
# SlurmCluster CRD - Defines the overall Slurm cluster configuration
apiVersion: slinky.slurm.net/v1alpha1
kind: SlurmCluster
metadata:
  name: ml-training-cluster
  namespace: slurm
spec:
  clusterName: ml-cluster

  # Controller configuration
  controller:
    replicas: 1
    image: schedmd/slurmctld:24.05
    resources:
      requests:
        cpu: "2"
        memory: "4Gi"
      limits:
        cpu: "4"
        memory: "8Gi"
    persistence:
      storageClass: gp3
      size: 50Gi

  # Database configuration
  database:
    type: mariadb
    persistence:
      storageClass: gp3
      size: 100Gi

  # REST API configuration
  restApi:
    enabled: true
    replicas: 2

  # Shared storage configuration
  sharedStorage:
    type: fsx-lustre
    fileSystemId: fs-0123456789abcdef0
    mountPath: /shared
---
# SlurmNodeSet CRD - Defines compute node groups (partitions)
apiVersion: slinky.slurm.net/v1alpha1
kind: SlurmNodeSet
metadata:
  name: gpu-a100-nodes
  namespace: slurm
spec:
  clusterRef:
    name: ml-training-cluster

  partition: gpu-a100
  nodeCount: 4

  nodeTemplate:
    instanceType: p4d.24xlarge
    image: schedmd/slurmd:24.05

    # GPU configuration
    gpus:
      type: nvidia-a100
      count: 8
      mig: false

    # Resource allocation
    resources:
      cpus: 96
      memory: 1152Gi
      gpuMemory: 320Gi  # 8x 40GB A100

    # Node features for Slurm GRES
    features:
      - a100
      - nvlink
      - efa

    # Placement for low-latency communication
    placement:
      groupName: ml-cluster-pg
      strategy: cluster

  # Karpenter integration for auto-scaling
  autoscaling:
    enabled: true
    minNodes: 0
    maxNodes: 16
    scaleDownDelay: 300s
    nodePoolRef:
      name: gpu-a100-nodepool
```

### ArgoCD による Slinky のデプロイ

```yaml
# ArgoCD Application for Slinky deployment
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: slinky-slurm
  namespace: argocd
spec:
  project: ml-infrastructure

  source:
    repoURL: https://github.com/your-org/ml-platform
    targetRevision: main
    path: clusters/production/slurm

    helm:
      values: |
        cluster:
          name: ml-training

        controller:
          nodeSelector:
            node.kubernetes.io/instance-type: m6i.2xlarge

        compute:
          partitions:
            - name: gpu-a100
              nodeType: p4d.24xlarge
              maxNodes: 16
            - name: gpu-h100
              nodeType: p5.48xlarge
              maxNodes: 8
            - name: trainium
              nodeType: trn1.32xlarge
              maxNodes: 32

        storage:
          fsxLustre:
            fileSystemId: fs-0123456789abcdef0
            capacity: 4800Gi

        networking:
          efa:
            enabled: true

  destination:
    server: https://kubernetes.default.svc
    namespace: slurm

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### GPU Auto-scaling 用の Karpenter NodePool

```yaml
# Karpenter NodePool for Slurm GPU nodes
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-a100-nodepool
spec:
  template:
    metadata:
      labels:
        slurm.schedmd.com/partition: gpu-a100
        node-type: gpu-training
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - p4d.24xlarge
            - p4de.24xlarge
        - key: karpenter.sh/capacity-type
          operator: In
          values:
            - on-demand  # Use on-demand for training stability
        - key: topology.kubernetes.io/zone
          operator: In
          values:
            - us-west-2a  # Single AZ for EFA

      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-a100-class

      # Taints to ensure only Slurm workloads run here
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
        - key: slurm.schedmd.com/partition
          value: gpu-a100
          effect: NoSchedule

  limits:
    nvidia.com/gpu: 128  # Max 16 nodes * 8 GPUs

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "0"  # Don't disrupt running training jobs
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-a100-class
spec:
  amiFamily: AL2

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: ml-cluster
        network-type: efa-enabled

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: ml-cluster

  # EFA configuration for high-speed networking
  instanceStorePolicy: RAID0

  # Block device configuration
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 500Gi
        volumeType: gp3
        iops: 10000
        throughput: 500
        encrypted: true

  # User data for GPU and EFA setup
  userData: |
    #!/bin/bash
    set -ex

    # Install EFA driver
    curl -O https://efa-installer.amazonaws.com/aws-efa-installer-latest.tar.gz
    tar -xf aws-efa-installer-latest.tar.gz
    cd aws-efa-installer && ./efa_installer.sh -y

    # Configure NVIDIA persistence mode
    nvidia-smi -pm 1

    # Set GPU clock speeds for consistent performance
    nvidia-smi -ac 1215,1410

  tags:
    Environment: production
    Workload: ml-training
```

### Slurm へのジョブ送信

```bash
#!/bin/bash
# Example Slurm job script for distributed PyTorch training

#SBATCH --job-name=llama3-finetune
#SBATCH --partition=gpu-a100
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=12
#SBATCH --mem=1100G
#SBATCH --time=48:00:00
#SBATCH --output=/shared/logs/%x-%j.out
#SBATCH --error=/shared/logs/%x-%j.err

# Load required modules
module load cuda/12.1
module load nccl/2.18

# Set environment variables
export MASTER_ADDR=$(scontrol show hostname $SLURM_NODELIST | head -n 1)
export MASTER_PORT=29500
export WORLD_SIZE=$((SLURM_NNODES * SLURM_NTASKS_PER_NODE))
export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=1
export NCCL_SOCKET_IFNAME=eth0

# Run distributed training
srun --ntasks=$WORLD_SIZE \
     --ntasks-per-node=$SLURM_NTASKS_PER_NODE \
     torchrun \
     --nnodes=$SLURM_NNODES \
     --nproc_per_node=$SLURM_NTASKS_PER_NODE \
     --rdzv_id=$SLURM_JOB_ID \
     --rdzv_backend=c10d \
     --rdzv_endpoint=$MASTER_ADDR:$MASTER_PORT \
     train_llama.py \
     --model_name_or_path meta-llama/Llama-3-70B \
     --dataset_path /shared/data/finetune-dataset \
     --output_dir /shared/checkpoints/llama3-finetuned \
     --per_device_train_batch_size 1 \
     --gradient_accumulation_steps 8 \
     --learning_rate 2e-5 \
     --num_train_epochs 3 \
     --bf16 \
     --deepspeed configs/ds_config_zero3.json
```

## NVIDIA GPU での学習

NVIDIA GPU は、AI/ML 学習の主要な選択肢であり続けています。NCCL、EFA、マルチノード通信を適切に設定することは、パフォーマンスに不可欠です。

### マルチノード学習向け NCCL 設定

```yaml
apiVersion: kubeflow.org/v1
kind: MPIJob
metadata:
  name: bert-large-training
  namespace: training
spec:
  slotsPerWorker: 8
  runPolicy:
    cleanPodPolicy: Running
    ttlSecondsAfterFinished: 86400

  mpiReplicaSpecs:
    Launcher:
      replicas: 1
      template:
        spec:
          containers:
            - name: mpi-launcher
              image: 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2
              command:
                - mpirun
                - --allow-run-as-root
                - -np
                - "32"
                - -bind-to
                - none
                - -map-by
                - slot
                - -x
                - NCCL_DEBUG=INFO
                - -x
                - NCCL_ALGO=Ring
                - -x
                - NCCL_PROTO=Simple
                - -x
                - FI_PROVIDER=efa
                - -x
                - FI_EFA_USE_DEVICE_RDMA=1
                - -x
                - RDMAV_FORK_SAFE=1
                - python
                - /workspace/train_bert.py
                - --model_name=bert-large-uncased
                - --batch_size=32
                - --learning_rate=3e-5
              resources:
                limits:
                  cpu: "4"
                  memory: "16Gi"

    Worker:
      replicas: 4
      template:
        spec:
          containers:
            - name: mpi-worker
              image: 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2
              resources:
                limits:
                  nvidia.com/gpu: 8
                  vpc.amazonaws.com/efa: 4
                  memory: "1100Gi"
                  cpu: "96"
              volumeMounts:
                - name: shared-storage
                  mountPath: /shared
                - name: shm
                  mountPath: /dev/shm
          volumes:
            - name: shared-storage
              persistentVolumeClaim:
                claimName: fsx-lustre-pvc
            - name: shm
              emptyDir:
                medium: Memory
                sizeLimit: 64Gi

          # Node placement for EFA
          affinity:
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                  - matchExpressions:
                      - key: node.kubernetes.io/instance-type
                        operator: In
                        values:
                          - p4d.24xlarge
                          - p4de.24xlarge
```

### EFA ネットワーク設定

```yaml
# EFA Device Plugin DaemonSet
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: aws-efa-k8s-device-plugin
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: aws-efa-k8s-device-plugin
  template:
    metadata:
      labels:
        name: aws-efa-k8s-device-plugin
    spec:
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      priorityClassName: system-node-critical
      containers:
        - name: aws-efa-k8s-device-plugin
          image: 602401143452.dkr.ecr.us-west-2.amazonaws.com/eks/aws-efa-k8s-device-plugin:v0.4.4
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: device-plugin
              mountPath: /var/lib/kubelet/device-plugins
      volumes:
        - name: device-plugin
          hostPath:
            path: /var/lib/kubelet/device-plugins
      nodeSelector:
        node.kubernetes.io/instance-type: p4d.24xlarge
```

### EKS 上の NVIDIA BioNeMo

BioNeMo は、創薬と分子モデリングのための NVIDIA のフレームワークです。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: bionemo-molecule-generation
  namespace: ai-research
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: bionemo
          image: nvcr.io/nvidia/clara/bionemo-framework:1.5
          command:
            - python
            - -m
            - bionemo.model.molecule.megamolbart.infer
            - --config-path=/configs
            - --config-name=megamolbart_inference
          env:
            - name: CUDA_VISIBLE_DEVICES
              value: "0,1,2,3,4,5,6,7"
            - name: NVIDIA_VISIBLE_DEVICES
              value: "all"
          resources:
            limits:
              nvidia.com/gpu: 8
              memory: "500Gi"
              cpu: "48"
          volumeMounts:
            - name: model-cache
              mountPath: /models
            - name: data
              mountPath: /data
            - name: configs
              mountPath: /configs
            - name: shm
              mountPath: /dev/shm
      volumes:
        - name: model-cache
          persistentVolumeClaim:
            claimName: bionemo-models-pvc
        - name: data
          persistentVolumeClaim:
            claimName: molecule-data-pvc
        - name: configs
          configMap:
            name: bionemo-inference-config
        - name: shm
          emptyDir:
            medium: Memory
            sizeLimit: 32Gi
      nodeSelector:
        node.kubernetes.io/instance-type: p4d.24xlarge
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
```

## AWS Trainium/Neuron での学習

AWS Trainium チップは、大規模モデルに対してコスト効率の高い学習を提供します。Neuron SDK は、PyTorch および TensorFlow との統合を提供します。

### Neuron SDK コンポーネント

| コンポーネント | 説明 | 目的 |
|-----------|-------------|---------|
| **Neuron Compiler** | XLA ベースのコンパイラ | Neuron ハードウェア向けにモデルを最適化 |
| **Neuron Runtime** | 実行ランタイム | Neuron デバイスと実行を管理 |
| **Neuron Tools** | プロファイリングとデバッグ | neuron-top, neuron-monitor, neuron-profile |
| **torch-neuronx** | PyTorch 統合 | Trainium 向けのネイティブ PyTorch API |
| **transformers-neuronx** | HuggingFace 統合 | Neuron 向けに最適化された transformers |
| **optimum-neuron** | HuggingFace Optimum | 高レベルの学習および推論 API |

### 対応フレームワークとモデル

```yaml
# Neuron-supported frameworks and versions
frameworks:
  pytorch:
    versions: ["2.1", "2.0", "1.13"]
    package: torch-neuronx
    models:
      - BERT, RoBERTa, DistilBERT
      - GPT-2, GPT-NeoX, GPT-J
      - Llama 2, Llama 3
      - T5, FLAN-T5
      - Stable Diffusion, SDXL

  tensorflow:
    versions: ["2.10"]
    package: tensorflow-neuronx
    models:
      - BERT, DistilBERT
      - ResNet, EfficientNet
      - Custom models via SavedModel

  jax:
    versions: ["0.4"]
    package: jax-neuronx
    models:
      - Custom JAX models
      - Flax-based models
```

### Trainium での Llama 3 LoRA ファインチューニング

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: llama3-lora-finetune
  namespace: training
spec:
  parallelism: 4
  completions: 4
  template:
    metadata:
      labels:
        app: llama3-training
        training-type: lora
    spec:
      restartPolicy: OnFailure

      initContainers:
        # Download model and dataset
        - name: setup
          image: amazon/aws-cli:latest
          command:
            - /bin/bash
            - -c
            - |
              aws s3 sync s3://my-bucket/llama3-70b /shared/models/llama3-70b
              aws s3 sync s3://my-bucket/training-data /shared/data
          volumeMounts:
            - name: shared-storage
              mountPath: /shared

      containers:
        - name: trainer
          image: 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training-neuronx:2.1.0-neuronx-py310-sdk2.18.0-ubuntu20.04
          command:
            - neuron_parallel_compile
            - torchrun
            - --nproc_per_node=32
            - --nnodes=4
            - --node_rank=$(JOB_COMPLETION_INDEX)
            - --master_addr=$(MASTER_ADDR)
            - --master_port=29500
            - train_lora.py
          args:
            - --model_id=/shared/models/llama3-70b
            - --dataset_path=/shared/data/instruct-dataset
            - --output_dir=/shared/checkpoints/llama3-lora
            - --lora_rank=16
            - --lora_alpha=32
            - --lora_dropout=0.1
            - --target_modules=q_proj,k_proj,v_proj,o_proj
            - --per_device_train_batch_size=1
            - --gradient_accumulation_steps=16
            - --learning_rate=2e-4
            - --num_train_epochs=3
            - --warmup_ratio=0.03
            - --bf16
            - --gradient_checkpointing
            - --save_strategy=steps
            - --save_steps=500
          env:
            - name: NEURON_RT_NUM_CORES
              value: "32"
            - name: NEURON_CC_FLAGS
              value: "--model-type transformer --distribution-strategy llm-training"
            - name: XLA_USE_BF16
              value: "1"
            - name: MASTER_ADDR
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
            - name: JOB_COMPLETION_INDEX
              valueFrom:
                fieldRef:
                  fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
          resources:
            limits:
              aws.amazon.com/neuron: 16  # 16 Trainium chips = trn1.32xlarge
              memory: "500Gi"
              cpu: "128"
            requests:
              aws.amazon.com/neuron: 16
              memory: "450Gi"
              cpu: "120"
          volumeMounts:
            - name: shared-storage
              mountPath: /shared
            - name: neuron-cache
              mountPath: /var/tmp/neuron-compile-cache

      volumes:
        - name: shared-storage
          persistentVolumeClaim:
            claimName: fsx-lustre-pvc
        - name: neuron-cache
          emptyDir:
            sizeLimit: 100Gi

      nodeSelector:
        node.kubernetes.io/instance-type: trn1.32xlarge

      tolerations:
        - key: aws.amazon.com/neuron
          operator: Exists
          effect: NoSchedule
```

### NeuronX Distributed による Trainium 上の BERT-Large 学習

```python
# train_bert_neuronx.py - Example training script
import os
import torch
import torch_neuronx
from torch.utils.data import DataLoader
from transformers import BertForPreTraining, BertTokenizer
from optimum.neuron import NeuronTrainer, NeuronTrainingArguments
from optimum.neuron.distributed import lazy_load_for_parallelism

# Initialize distributed training
torch.distributed.init_process_group(backend='xla')
world_size = torch.distributed.get_world_size()
rank = torch.distributed.get_rank()

# Load model with tensor parallelism
with lazy_load_for_parallelism(tensor_parallel_size=8):
    model = BertForPreTraining.from_pretrained(
        "bert-large-uncased",
        torch_dtype=torch.bfloat16
    )

# Configure training arguments
training_args = NeuronTrainingArguments(
    output_dir="/shared/checkpoints/bert-large",
    per_device_train_batch_size=16,
    gradient_accumulation_steps=4,
    learning_rate=1e-4,
    num_train_epochs=3,
    warmup_steps=1000,
    weight_decay=0.01,
    logging_steps=100,
    save_steps=1000,
    bf16=True,
    tensor_parallel_size=8,
    pipeline_parallel_size=1,
    zero_1=True,
)

# Create trainer
trainer = NeuronTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    tokenizer=tokenizer,
)

# Start training
trainer.train()
```

### Trainium ノード設定

```yaml
# Karpenter NodePool for Trainium instances
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: trainium-nodepool
spec:
  template:
    metadata:
      labels:
        accelerator-type: trainium
        node-type: ml-training
    spec:
      requirements:
        - key: node.kubernetes.io/instance-type
          operator: In
          values:
            - trn1.32xlarge
            - trn1n.32xlarge  # Enhanced networking
        - key: karpenter.sh/capacity-type
          operator: In
          values:
            - on-demand
        - key: topology.kubernetes.io/zone
          operator: In
          values:
            - us-east-1a

      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: trainium-class

      taints:
        - key: aws.amazon.com/neuron
          value: "true"
          effect: NoSchedule

  limits:
    aws.amazon.com/neuron: 256  # Max 16 nodes * 16 chips

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: trainium-class
spec:
  amiFamily: AL2
  amiSelectorTerms:
    - id: ami-0123456789abcdef0  # Neuron-optimized AMI

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: ml-cluster

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: ml-cluster

  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 500Gi
        volumeType: gp3
        iops: 10000
        encrypted: true

  userData: |
    #!/bin/bash
    # Install Neuron drivers and tools
    . /etc/os-release
    sudo tee /etc/yum.repos.d/neuron.repo > /dev/null <<EOF
    [neuron]
    name=Neuron YUM Repository
    baseurl=https://yum.repos.neuron.amazonaws.com
    enabled=1
    metadata_expire=0
    EOF
    sudo rpm --import https://yum.repos.neuron.amazonaws.com/GPG-PUB-KEY-AMAZON-AWS-NEURON.PUB
    sudo yum install -y aws-neuronx-runtime-lib aws-neuronx-collectives

    # Increase ulimits for Neuron
    echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
    echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf
```

## 学習インフラストラクチャコンポーネント

### 分散学習向け KubeRay と RayTrain

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: raytrain-cluster
  namespace: training
spec:
  rayVersion: '2.9.0'

  headGroupSpec:
    rayStartParams:
      dashboard-host: '0.0.0.0'
      num-cpus: '0'
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray-ml:2.9.0-py310-gpu
            ports:
              - containerPort: 6379
                name: gcs
              - containerPort: 8265
                name: dashboard
              - containerPort: 10001
                name: client
            resources:
              limits:
                cpu: "8"
                memory: "32Gi"
              requests:
                cpu: "4"
                memory: "16Gi"

  workerGroupSpecs:
    - groupName: gpu-workers
      replicas: 4
      minReplicas: 1
      maxReplicas: 16
      rayStartParams:
        num-gpus: '8'
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray-ml:2.9.0-py310-gpu
              resources:
                limits:
                  nvidia.com/gpu: 8
                  memory: "500Gi"
                  cpu: "96"
              volumeMounts:
                - name: shared-storage
                  mountPath: /shared
          volumes:
            - name: shared-storage
              persistentVolumeClaim:
                claimName: fsx-lustre-pvc
          nodeSelector:
            node.kubernetes.io/instance-type: p4d.24xlarge
          tolerations:
            - key: nvidia.com/gpu
              operator: Exists
              effect: NoSchedule
```

```python
# ray_train_example.py - RayTrain distributed training
import ray
from ray import train
from ray.train.torch import TorchTrainer
from ray.train import ScalingConfig, RunConfig, CheckpointConfig

def train_loop_per_worker(config):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    # Get distributed context
    world_size = train.get_context().get_world_size()
    rank = train.get_context().get_world_rank()

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name"],
        torch_dtype=torch.bfloat16
    )

    # Training loop
    for epoch in range(config["epochs"]):
        # ... training logic ...

        # Report metrics to Ray
        train.report({"loss": loss, "epoch": epoch})

        # Save checkpoint
        if rank == 0:
            with train.get_checkpoint() as checkpoint:
                torch.save(model.state_dict(), checkpoint.path / "model.pt")

# Configure trainer
trainer = TorchTrainer(
    train_loop_per_worker,
    train_loop_config={
        "model_name": "meta-llama/Llama-3-8B",
        "epochs": 3,
        "learning_rate": 2e-5,
    },
    scaling_config=ScalingConfig(
        num_workers=4,
        use_gpu=True,
        resources_per_worker={"GPU": 8, "CPU": 24},
    ),
    run_config=RunConfig(
        name="llama3-training",
        storage_path="/shared/ray-results",
        checkpoint_config=CheckpointConfig(
            num_to_keep=3,
            checkpoint_frequency=100,
        ),
    ),
)

result = trainer.fit()
```

### 従来の HPC ワークロード向け MPI Operator

```yaml
# Install MPI Operator
apiVersion: v1
kind: Namespace
metadata:
  name: mpi-operator
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mpi-operator
  namespace: mpi-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mpi-operator
  template:
    metadata:
      labels:
        app: mpi-operator
    spec:
      serviceAccountName: mpi-operator
      containers:
        - name: mpi-operator
          image: mpioperator/mpi-operator:v0.4.0
          args:
            - --gpus-per-node=8
            - --kubectl-delivery-image=mpioperator/kubectl-delivery:v0.4.0
          imagePullPolicy: Always
```

### Gang Scheduling 向け Volcano Scheduler

```yaml
# Volcano configuration for ML training
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: ml-training-queue
spec:
  weight: 100
  capability:
    nvidia.com/gpu: 128
    cpu: "1000"
    memory: "8000Gi"
---
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: distributed-training
  namespace: training
spec:
  minAvailable: 4  # Gang scheduling: all 4 pods must be scheduled together
  schedulerName: volcano
  queue: ml-training-queue

  policies:
    - event: PodEvicted
      action: RestartJob
    - event: PodFailed
      action: RestartJob

  tasks:
    - name: worker
      replicas: 4
      template:
        spec:
          containers:
            - name: pytorch
              image: pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
              command:
                - torchrun
                - --nproc_per_node=8
                - --nnodes=4
                - train.py
              resources:
                limits:
                  nvidia.com/gpu: 8
```

### インタラクティブな学習開発向け JupyterHub

```yaml
# JupyterHub with GPU support
apiVersion: v1
kind: ConfigMap
metadata:
  name: jupyterhub-config
  namespace: jupyter
data:
  jupyterhub_config.py: |
    c.JupyterHub.spawner_class = 'kubespawner.KubeSpawner'

    # GPU profile
    c.KubeSpawner.profile_list = [
        {
            'display_name': 'GPU Development (1x A100)',
            'kubespawner_override': {
                'image': 'jupyter/tensorflow-notebook:latest',
                'extra_resource_limits': {'nvidia.com/gpu': '1'},
                'node_selector': {'node.kubernetes.io/instance-type': 'g5.xlarge'},
            }
        },
        {
            'display_name': 'Multi-GPU Development (8x A100)',
            'kubespawner_override': {
                'image': 'jupyter/tensorflow-notebook:latest',
                'extra_resource_limits': {'nvidia.com/gpu': '8'},
                'node_selector': {'node.kubernetes.io/instance-type': 'p4d.24xlarge'},
                'volumes': [
                    {
                        'name': 'shared-storage',
                        'persistentVolumeClaim': {'claimName': 'fsx-lustre-pvc'}
                    }
                ],
                'volume_mounts': [
                    {'name': 'shared-storage', 'mountPath': '/shared'}
                ]
            }
        },
        {
            'display_name': 'Trainium Development (16x Trainium)',
            'kubespawner_override': {
                'image': '763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training-neuronx:2.1.0',
                'extra_resource_limits': {'aws.amazon.com/neuron': '16'},
                'node_selector': {'node.kubernetes.io/instance-type': 'trn1.32xlarge'},
            }
        },
    ]
```

## 学習用ストレージ

### FSx for Lustre 設定

```yaml
# FSx for Lustre file system with S3 data repository
apiVersion: fsx.services.k8s.aws/v1alpha1
kind: FileSystem
metadata:
  name: ml-training-lustre
  namespace: storage
spec:
  fileSystemType: LUSTRE
  storageCapacity: 4800
  subnetIDs:
    - subnet-0123456789abcdef0
  securityGroupIDs:
    - sg-0123456789abcdef0

  lustreConfiguration:
    deploymentType: PERSISTENT_2
    perUnitStorageThroughput: 250  # MB/s per TiB

    # S3 data repository association
    dataRepositoryAssociations:
      - fileSystemPath: /data
        dataRepositoryPath: s3://my-ml-data-bucket/training-data
        batchImportMetaDataOnCreate: true
        s3:
          autoImportPolicy:
            events:
              - NEW
              - CHANGED
          autoExportPolicy:
            events:
              - NEW
              - CHANGED
              - DELETED

      - fileSystemPath: /checkpoints
        dataRepositoryPath: s3://my-ml-data-bucket/checkpoints
        s3:
          autoExportPolicy:
            events:
              - NEW
              - CHANGED

  tags:
    - key: Environment
      value: production
    - key: Workload
      value: ml-training
---
# StorageClass for dynamic FSx provisioning
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  perUnitStorageThroughput: "200"
volumeBindingMode: WaitForFirstConsumer
---
# PVC for FSx Lustre
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fsx-lustre-pvc
  namespace: training
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 4800Gi
```

### 共有モデルストレージ用 Amazon EFS

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "755"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
  basePath: "/ml-models"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-storage-pvc
  namespace: training
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 1Ti
```

### チェックポイント管理

```yaml
# Checkpoint manager sidecar
apiVersion: v1
kind: ConfigMap
metadata:
  name: checkpoint-manager-config
  namespace: training
data:
  config.yaml: |
    checkpoint:
      # Local path where training writes checkpoints
      local_path: /checkpoints

      # Remote path for durable storage
      remote_path: s3://my-bucket/checkpoints

      # Sync settings
      sync_interval: 300  # seconds
      max_checkpoints: 5  # keep last N checkpoints

      # Compression
      compression: true
      compression_level: 6

      # Resumption
      auto_resume: true
      resume_from_latest: true
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: training-with-checkpoint-manager
spec:
  template:
    spec:
      containers:
        - name: trainer
          # ... training container ...
          volumeMounts:
            - name: checkpoints
              mountPath: /checkpoints

        - name: checkpoint-manager
          image: my-registry/checkpoint-manager:v1
          args:
            - --config=/config/config.yaml
            - --watch
          volumeMounts:
            - name: checkpoints
              mountPath: /checkpoints
            - name: config
              mountPath: /config

      volumes:
        - name: checkpoints
          emptyDir:
            sizeLimit: 500Gi
        - name: config
          configMap:
            name: checkpoint-manager-config
```

## 学習最適化のヒント

### 混合精度学習

```python
# PyTorch mixed precision with torch.cuda.amp
import torch
from torch.cuda.amp import autocast, GradScaler

model = MyModel().cuda()
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
scaler = GradScaler()

for epoch in range(num_epochs):
    for batch in dataloader:
        optimizer.zero_grad()

        # Forward pass with automatic mixed precision
        with autocast(dtype=torch.bfloat16):
            outputs = model(batch['input_ids'])
            loss = loss_fn(outputs, batch['labels'])

        # Backward pass with gradient scaling
        scaler.scale(loss).backward()

        # Gradient clipping
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        # Optimizer step
        scaler.step(optimizer)
        scaler.update()
```

### 勾配累積

```yaml
# Training configuration with gradient accumulation
apiVersion: v1
kind: ConfigMap
metadata:
  name: training-config
data:
  config.yaml: |
    training:
      # Effective batch size = micro_batch * gradient_accumulation * num_gpus
      # 1 * 32 * 64 = 2048 effective batch size
      micro_batch_size: 1
      gradient_accumulation_steps: 32

      # Memory optimization
      gradient_checkpointing: true
      activation_checkpointing_granularity: selective

      # Precision
      precision: bf16

      # Learning rate
      learning_rate: 2e-5
      lr_scheduler: cosine
      warmup_ratio: 0.03

      # Optimizer
      optimizer: adamw_torch_fused
      weight_decay: 0.01
```

### Flash Attention 設定

```python
# Enable Flash Attention 2 in transformers
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3-70B",
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",  # Enable Flash Attention
    use_cache=False,  # Disable KV cache during training
)

# For custom models, use torch.nn.functional.scaled_dot_product_attention
import torch.nn.functional as F

def attention_forward(q, k, v, mask=None):
    # Uses Flash Attention automatically when available
    return F.scaled_dot_product_attention(
        q, k, v,
        attn_mask=mask,
        dropout_p=0.0 if not training else 0.1,
        is_causal=True,  # Enable causal masking optimization
    )
```

### Learning Rate Scheduling のベストプラクティス

```python
# Cosine annealing with warmup
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts, LambdaLR

def get_cosine_schedule_with_warmup(optimizer, num_warmup_steps, num_training_steps, min_lr_ratio=0.1):
    def lr_lambda(current_step):
        if current_step < num_warmup_steps:
            # Linear warmup
            return float(current_step) / float(max(1, num_warmup_steps))

        # Cosine annealing
        progress = float(current_step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        return max(min_lr_ratio, 0.5 * (1.0 + math.cos(math.pi * progress)))

    return LambdaLR(optimizer, lr_lambda)

# Usage
scheduler = get_cosine_schedule_with_warmup(
    optimizer,
    num_warmup_steps=1000,
    num_training_steps=100000,
    min_lr_ratio=0.1
)
```

### DeepSpeed ZeRO 設定

```json
{
  "bf16": {
    "enabled": true
  },
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {
      "device": "cpu",
      "pin_memory": true
    },
    "offload_param": {
      "device": "cpu",
      "pin_memory": true
    },
    "overlap_comm": true,
    "contiguous_gradients": true,
    "sub_group_size": 1e9,
    "reduce_bucket_size": "auto",
    "stage3_prefetch_bucket_size": "auto",
    "stage3_param_persistence_threshold": "auto",
    "stage3_max_live_parameters": 1e9,
    "stage3_max_reuse_distance": 1e9,
    "stage3_gather_16bit_weights_on_model_save": true
  },
  "gradient_accumulation_steps": 32,
  "gradient_clipping": 1.0,
  "train_micro_batch_size_per_gpu": 1,
  "wall_clock_breakdown": false,
  "communication_data_type": "bf16"
}
```

## ベストプラクティスのまとめ

| カテゴリ | ベストプラクティス | 利点 |
|----------|--------------|---------|
| **Parallelism** | 100B+ モデルには 3D parallelism を使用 | 最大限のメモリ効率 |
| **Communication** | マルチノード学習に EFA を有効化 | 400 Gbps ネットワーク |
| **Storage** | S3 データリポジトリ付き FSx Lustre を使用 | 高スループット + 耐久性 |
| **Checkpointing** | N ステップごとに保存し、直近 3〜5 個を保持 | ストレージと復旧のバランス |
| **Precision** | 安定性のため FP16 より BF16 を使用 | 損失スケーリングが不要 |
| **Memory** | gradient checkpointing を有効化 | 3〜4 倍のメモリ節約 |
| **Scheduling** | Gang Scheduling に Volcano を使用 | オールオアナッシングの Pod 配置 |
| **Scaling** | GPU NodePools と Karpenter を使用 | GPU の自動プロビジョニング |

## 参考資料

- [AI on EKS](https://awslabs.github.io/ai-on-eks/) - EKS 上に AI/ML ワークロードをデプロイするための AWS ガイドと例
- [Slinky - Slurm on Kubernetes](https://github.com/SchedMD/slurm-operator) - Kubernetes 向け SchedMD の Slurm operator
- [AWS Neuron Documentation](https://awsdocs.github.io/aws-neuron-documentation/) - Trainium と Inferentia 向け Neuron SDK
- [NVIDIA NCCL Documentation](https://docs.nvidia.com/deeplearning/nccl/) - Collective communication ライブラリ
- [DeepSpeed Documentation](https://www.deepspeed.ai/) - Microsoft の分散学習ライブラリ
- [KubeRay Documentation](https://ray-project.github.io/kuberay/) - Kubernetes 上の Ray

## クイズ

この章で学んだ内容を確認するには、[モデル学習クイズ](../quizzes/ai-ml/05-model-training-quiz.md) に挑戦してください。
