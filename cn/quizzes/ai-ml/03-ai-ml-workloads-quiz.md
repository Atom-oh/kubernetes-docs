# AI/ML 工作负载测验

本测验测试你对在 Kubernetes 中运行 AI/ML 工作负载的理解。

## 测验问题

### 1. 在 Kubernetes 中调度使用 GPU 的 Pod 时，需要的资源请求字段是什么？

A. resources.requests.gpu
B. resources.requests.nvidia.com/gpu
C. resources.requests.k8s.io/gpu
D. resources.requests.compute/gpu

<details>
<summary>显示答案</summary>

**答案：B. resources.requests.nvidia.com/gpu**

**解释：**
在 Kubernetes 中调度使用 GPU 的 Pod 时，需要的资源请求字段是 `resources.requests.nvidia.com/gpu`。这是请求 NVIDIA GPU 的标准方式，其他 GPU 厂商可能会使用自己的命名空间（例如 `amd.com/gpu`）。

**GPU 资源请求示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: gpu-container
    image: nvidia/cuda:11.0-base
    resources:
      limits:
        nvidia.com/gpu: 1  # Request 1 GPU
      requests:
        nvidia.com/gpu: 1  # Requests and limits must be the same
```

**GPU 资源特性：**
1. **整数分配**：GPU 只能按整数单位分配（例如 1、2、3）。不支持小数值（例如 0.5）。
2. **requests 和 limits 匹配**：对于 GPU 资源，`requests` 和 `limits` 必须相同。
3. **独占使用**：默认情况下，GPU 不会在容器之间共享。每个 GPU 一次只分配给一个容器。
4. **Node 标签**：带有 GPU 的 Node 通常会标记为 `nvidia.com/gpu`。

**使用 GPU 的前提条件：**
1. **Node 上的 GPU 硬件**：必须在 Node 上安装物理 GPU。
2. **GPU 驱动程序**：必须在 Node 上安装合适的 GPU 驱动程序。
3. **NVIDIA Device Plugin**：必须在 Kubernetes 集群中安装 NVIDIA Device Plugin。
4. **容器运行时支持**：容器运行时必须支持 GPU。

**安装 NVIDIA Device Plugin：**
```bash
# Installation using Helm
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
helm install nvidia-device-plugin nvdp/nvidia-device-plugin

# Or direct installation
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.13.0/nvidia-device-plugin.yml
```

**检查 GPU 资源：**
```bash
# Check GPU resources on nodes
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu

# Check pods using GPUs
kubectl get pods -A -o custom-columns=NAME:.metadata.name,GPU:.spec.containers[*].resources.limits.nvidia\\.com/gpu
```

**多 GPU 请求：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-gpu-pod
spec:
  containers:
  - name: multi-gpu-container
    image: nvidia/cuda:11.0-base
    resources:
      limits:
        nvidia.com/gpu: 4  # Request 4 GPUs
      requests:
        nvidia.com/gpu: 4
```

**GPU 内存分区（NVIDIA MPS）：**
NVIDIA Multi-Process Service (MPS) 允许多个进程共享同一个 GPU。Kubernetes 原生不支持这一点，需要自定义配置。

**其他 GPU 厂商：**
其他 GPU 厂商使用自己的命名空间：
- AMD GPU: `amd.com/gpu`
- Intel GPU: `intel.com/gpu`

**其他选项的问题：**
- A. resources.requests.gpu：这不是有效的 Kubernetes 资源字段。GPU 资源必须使用特定厂商的命名空间。
- C. resources.requests.k8s.io/gpu：这不是有效的 Kubernetes 资源字段。`k8s.io` 命名空间通常用于 Kubernetes 核心资源。
- D. resources.requests.compute/gpu：这不是有效的 Kubernetes 资源字段。
</details>

### 2. 在 Kubernetes 中运行分布式 TensorFlow 训练 Job 时，最合适的资源类型是什么？

A. Deployment
B. StatefulSet
C. Job
D. TFJob (Kubeflow)

<details>
<summary>显示答案</summary>

**答案：D. TFJob (Kubeflow)**

**解释：**
在 Kubernetes 中运行分布式 TensorFlow 训练 Job 时，最合适的资源类型是 `TFJob`。TFJob 是 Kubeflow 项目的一部分，是专门为在 Kubernetes 上运行 TensorFlow 训练 Job 而设计的自定义资源。

**TFJob 的主要特性：**
1. **分布式训练支持**：支持 TensorFlow 的分布式训练架构，包括 worker、parameter server 和 evaluator。
2. **自动恢复**：自动重启失败的 worker。
3. **Gang scheduling**：确保所有 worker 同时被调度。
4. **TensorFlow 专用特性**：自动配置 TensorFlow 分布式训练所需的环境变量和设置。
5. **监控和日志记录**：提供监控 TensorFlow Job 状态和日志的功能。

**TFJob 示例：**
```yaml
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: mnist-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 3
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
            resources:
              limits:
                nvidia.com/gpu: 1
    PS:
      replicas: 1
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
    Chief:
      replicas: 1
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0
            command:
            - python
            - /opt/model/train.py
            - --batch_size=64
            - --learning_rate=0.001
            resources:
              limits:
                nvidia.com/gpu: 1
```

**TFJob 组件：**
1. **Chief**：负责保存模型 checkpoint 和写入 summary 的主 worker。
2. **Worker**：执行模型训练的 worker。
3. **PS (Parameter Server)**：存储并更新模型参数。
4. **Evaluator**：执行模型评估。

**安装 TFJob：**
```bash
# Install Kubeflow
kubectl apply -f https://raw.githubusercontent.com/kubeflow/kubeflow/master/kfctl_k8s_istio.yaml

# Or install only the TFJob controller
kubectl apply -f https://raw.githubusercontent.com/kubeflow/tf-operator/master/deploy/v1/tf-operator.yaml
```

**监控 TFJob：**
```bash
# Check TFJob status
kubectl get tfjobs

# Check specific TFJob details
kubectl describe tfjob mnist-training

# Check TFJob pods
kubectl get pods -l tf-job-name=mnist-training
```

**与其他资源类型的比较：**

1. **Deployment**：
   - 适合长期运行的 Service
   - 支持自动恢复和滚动更新
   - 缺少分布式训练 Job 所需的协调功能
   - 没有 TensorFlow 专用特性

2. **StatefulSet**：
   - 提供稳定的网络标识符和持久化存储
   - 有序部署和扩缩容
   - 缺少分布式训练 Job 所需的协调功能
   - 没有 TensorFlow 专用特性

3. **Job**：
   - 适合一次性 Job
   - 保证 Job 完成
   - 缺少分布式训练 Job 所需的协调功能
   - 没有 TensorFlow 专用特性

4. **TFJob**：
   - 针对 TensorFlow 分布式训练优化
   - 定义 worker、parameter server 等角色
   - 自动配置 TensorFlow 专用环境变量和设置
   - 内置 Job 完成和失败处理逻辑

**面向其他 ML 框架的 Kubeflow operator：**
- **PyTorchJob**：用于 PyTorch 训练 Job
- **MPIJob**：用于像 Horovod 这样的基于 MPI 的分布式训练
- **XGBoostJob**：用于 XGBoost 训练 Job

**其他选项的问题：**
- A. Deployment：适合长期运行的 Service，无法处理分布式 TensorFlow 训练 Job 的特定需求。
- B. StatefulSet：适合需要状态持久化的应用程序，但缺少分布式 TensorFlow 训练 Job 的协调功能。
- C. Job：适合一次性 Job，但无法处理分布式 TensorFlow 训练 Job 的特定需求。
</details>
### 3. 为 Kubernetes 中的 AI/ML 工作负载配置持久化存储时，最重要的考虑因素是什么？

A. 存储容量
B. StorageClass 类型
C. 数据访问模式和吞吐量要求
D. Storage provisioner

<details>
<summary>显示答案</summary>

**答案：C. 数据访问模式和吞吐量要求**

**解释：**
为 Kubernetes 中的 AI/ML 工作负载配置持久化存储时，最重要的考虑因素是数据访问模式和吞吐量要求。AI/ML 工作负载会处理大量数据，并且可能具有各种访问模式（顺序读取、随机读取、并行访问等），通常还需要高吞吐量。选择满足这些要求的存储解决方案会显著影响性能和效率。

**AI/ML 工作负载中的常见数据访问模式：**
1. **大型数据集读取**：训练数据集可能从数 GB 到数 TB 不等，需要高效的读取性能。
2. **并行访问**：多个 worker 同时访问数据的分布式训练场景很常见。
3. **顺序读取**：按顺序读取整个数据集的批处理 Job。
4. **随机访问**：访问数据集随机部分的 mini-batch 训练或在线学习。
5. **保存 checkpoint**：在训练期间保存模型 checkpoint 的写入操作。

**适合 AI/ML 工作负载的存储解决方案：**

1. **分布式文件系统**：
   - **Amazon FSx for Lustre**：针对高性能计算和机器学习工作负载优化的高性能文件系统
   - **GlusterFS/Ceph**：支持可扩展性和并行访问的开源分布式文件系统
   - **HDFS**：适合大规模数据集处理的 Hadoop Distributed File System

2. **高性能块存储**：
   - **AWS EBS io2/io2 Block Express**：提供高 IOPS 和吞吐量的基于 SSD 的块存储
   - **GCP Persistent Disk SSD**：提供高 IOPS 和吞吐量的基于 SSD 的块存储
   - **Azure Ultra Disk**：提供极高 IOPS 和吞吐量的基于 SSD 的块存储

3. **对象存储**：
   - **Amazon S3**：高度可扩展的对象存储，适合大规模数据集存储
   - **Google Cloud Storage**：高度可扩展的对象存储，适合大规模数据集存储
   - **Azure Blob Storage**：高度可扩展的对象存储，适合大规模数据集存储

**存储配置示例（FSx for Lustre）：**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: SCRATCH_2
  automaticBackupRetentionDays: "0"
  dailyAutomaticBackupStartTime: "00:00"
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
mountOptions:
  - flock

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-dataset
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi

---
# Using in training job
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: distributed-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            command:
            - python
            - /opt/model/train.py
            volumeMounts:
            - name: dataset
              mountPath: /data
            resources:
              limits:
                nvidia.com/gpu: 1
          volumes:
          - name: dataset
            persistentVolumeClaim:
              claimName: ml-dataset
```

**选择存储时需要考虑的性能指标：**
1. **吞吐量**：每秒可以读取/写入的数据量（MB/s 或 GB/s）
2. **IOPS (Input/Output Operations Per Second)**：每秒可以执行的 I/O 操作数量
3. **延迟**：I/O 请求的响应时间
4. **并行访问支持**：多个客户端同时访问的能力
5. **可扩展性**：随着数据增长保持性能的能力

**按 AI/ML 工作负载类型推荐的存储：**
1. **大规模分布式训练**：FSx for Lustre、HDFS、Ceph
2. **单 Node 训练**：高性能 SSD 块存储
3. **数据预处理**：分布式文件系统或对象存储
4. **模型服务**：高性能 SSD 块存储或内存存储

**存储性能测试：**
```bash
# Storage performance test using FIO
kubectl run fio-test --image=nixery.dev/shell/fio --restart=Never -- \
  fio --name=benchmark --directory=/data --direct=1 --rw=randread --bs=4k \
  --size=1G --numjobs=16 --runtime=60 --group_reporting
```

**其他选项的问题：**
- A. 存储容量：很重要，但仅靠容量无法满足 AI/ML 工作负载的性能要求。
- B. Storage class 类型：Storage class 定义了供应方式，但其本身并不能完全决定性能特征。
- D. Storage provisioner：Provisioner 定义了存储的创建方式，但不直接解决工作负载性能要求。
</details>

### 4. 在 Kubernetes 中为 AI/ML 工作负载分配资源的最有效方法是什么？

A. 为所有 Pod 分配相同资源
B. 基于工作负载特性的资源分析和优化
C. 始终请求最大资源
D. 不配置资源请求直接部署

<details>
<summary>显示答案</summary>

**答案：B. 基于工作负载特性的资源分析和优化**

**解释：**
在 Kubernetes 中为 AI/ML 工作负载分配资源的最有效方法是基于工作负载特性进行资源分析和优化。AI/ML 工作负载在训练、推理和数据预处理等不同阶段有不同的资源需求，理解每个工作负载的特性并相应地分配资源，对于优化性能和成本效率非常重要。

**AI/ML 工作负载资源分析方法：**
1. **基准测试**：使用各种资源配置运行工作负载并测量性能。
2. **监控**：监控实际资源使用情况以识别模式。
3. **逐步调整**：从初始估算开始，逐步调整资源。
4. **Auto-scaling**：根据工作负载需求自动调整资源。

**按 AI/ML 工作负载类型划分的资源特性：**

1. **模型训练**：
   - CPU：对数据预处理和特征工程很重要
   - GPU：对深度学习模型训练至关重要
   - 内存：大型数据集和模型参数存储所需
   - 存储：数据集和 checkpoint 存储所需

2. **模型推理**：
   - CPU：适合简单模型或批量推理
   - GPU：对复杂模型或实时推理有优势
   - 内存：模型加载和输入/输出处理所需
   - 延迟：对实时推理很重要

3. **数据预处理**：
   - CPU：并行处理能力很重要
   - 内存：大规模数据集处理所需
   - 存储 I/O：数据读写性能很重要

**资源优化示例：**
```yaml
# Training job - GPU and high memory requirements
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: training-job
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            resources:
              requests:
                cpu: 4
                memory: 16Gi
                nvidia.com/gpu: 1
              limits:
                cpu: 8
                memory: 32Gi
                nvidia.com/gpu: 1

---
# Inference service - low latency requirements
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      containers:
      - name: inference
        image: tensorflow/serving:2.6.0-gpu
        resources:
          requests:
            cpu: 2
            memory: 4Gi
            nvidia.com/gpu: 1
          limits:
            cpu: 4
            memory: 8Gi
            nvidia.com/gpu: 1
        env:
        - name: TF_FORCE_GPU_ALLOW_GROWTH
          value: "true"

---
# Data preprocessing job - CPU and memory intensive
apiVersion: batch/v1
kind: Job
metadata:
  name: data-preprocessing
spec:
  template:
    spec:
      containers:
      - name: preprocessing
        image: python:3.9
        resources:
          requests:
            cpu: 8
            memory: 16Gi
          limits:
            cpu: 16
            memory: 32Gi
```

**资源监控和优化工具：**
1. **Prometheus + Grafana**：资源使用监控和可视化
2. **Kubernetes Metrics Server**：基础资源指标收集
3. **NVIDIA DCGM Exporter**：GPU 指标收集
4. **Vertical Pod Autoscaler**：自动调整资源请求
5. **Horizontal Pod Autoscaler**：自动调整 Pod 数量

**资源优化策略：**
1. **GPU 共享**：通过 NVIDIA MPS 或时间切片调度在多个 Job 之间共享 GPU
2. **内存优化**：模型量化、延迟加载、内存高效算法
3. **批处理**：批量处理推理请求以提高吞吐量
4. **Auto-scaling**：根据负载自动调整资源
5. **Node affinity**：将工作负载放置到具有特定硬件特性的 Node 上

**GPU 内存优化示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-memory-optimized
spec:
  containers:
  - name: tensorflow
    image: tensorflow/tensorflow:2.6.0-gpu
    env:
    - name: TF_FORCE_GPU_ALLOW_GROWTH
      value: "true"  # Allocate only as much GPU memory as needed
    - name: TF_GPU_ALLOCATOR
      value: "cuda_malloc_async"  # Use asynchronous memory allocator
    resources:
      limits:
        nvidia.com/gpu: 1
```

**CPU 和内存优化示例：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cpu-memory-optimized
spec:
  containers:
  - name: python
    image: python:3.9
    env:
    - name: OMP_NUM_THREADS
      value: "4"  # Limit OpenMP thread count
    - name: MKL_NUM_THREADS
      value: "4"  # Limit Intel MKL thread count
    resources:
      requests:
        cpu: 4
        memory: 8Gi
      limits:
        cpu: 8
        memory: 16Gi
```

**其他选项的问题：**
- A. 为所有 Pod 分配相同资源：没有考虑不同工作负载特性，可能导致资源浪费或不足。
- C. 始终请求最大资源：成本效率差，集群资源利用率低。
- D. 不配置资源请求直接部署：可能导致调度和资源争用问题，对 GPU 等有限资源尤其重要。
</details>
### 5. 在 Kubernetes 中进行 AI/ML 模型服务的最合适方法是什么？

A. 使用常规 Deployment 资源
B. 使用 KServe（以前称为 KFServing）或 Seldon Core 等专用服务平台
C. 使用 StatefulSet 资源
D. 使用 CronJob 资源

<details>
<summary>显示答案</summary>

**答案：B. 使用 KServe（以前称为 KFServing）或 Seldon Core 等专用服务平台**

**解释：**
在 Kubernetes 中进行 AI/ML 模型服务的最合适方法是使用 KServe（以前称为 KFServing）或 Seldon Core 等专用服务平台。这些平台提供模型服务所需的各种功能（模型版本管理、A/B 测试、canary deployment、auto-scaling、监控等），并支持各种 ML 框架。

**专用模型服务平台的主要特性：**
1. **支持多种 ML 框架**：支持使用 TensorFlow、PyTorch、ONNX、scikit-learn 等多种框架训练的模型
2. **模型版本管理**：管理模型的多个版本并支持回滚
3. **流量拆分**：用于 A/B 测试、canary deployment 等的流量拆分功能
4. **Auto-scaling**：基于请求负载的 auto-scaling
5. **监控和日志记录**：监控模型性能、延迟、吞吐量等
6. **预处理和后处理**：输入数据预处理和输出数据后处理 pipeline
7. **批量推理**：支持对大量数据进行批量推理
8. **模型可解释性**：解释模型预测的功能

**KServe 示例：**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: sklearn-iris
spec:
  predictor:
    sklearn:
      storageUri: "gs://kserve-examples/models/sklearn/iris"
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          cpu: 1
          memory: 1Gi
```

**Seldon Core 示例：**
```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-model
spec:
  name: iris
  predictors:
  - name: default
    replicas: 1
    graph:
      name: classifier
      implementation: SKLEARN_SERVER
      modelUri: "gs://seldon-models/sklearn/iris"
      envSecretRefName: seldon-init-container-secret
    engineResources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 1
        memory: 1Gi
```

**高级服务功能示例：**

1. **Canary deployment（KServe）：**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: sklearn-iris
spec:
  predictor:
    canaryTrafficPercent: 20
    sklearn:
      storageUri: "gs://kserve-examples/models/sklearn/iris-v2"
    containers:
    - name: sklearn-v1
      image: kserve/sklearnserver:latest
      args:
      - --model_dir=/mnt/models
      - --model_name=sklearn-iris
```

2. **预处理和后处理 pipeline（Seldon Core）：**
```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-pipeline
spec:
  name: iris
  predictors:
  - name: default
    replicas: 1
    graph:
      name: preprocessor
      type: TRANSFORMER
      children:
      - name: model
        type: MODEL
        implementation: SKLEARN_SERVER
        modelUri: "gs://seldon-models/sklearn/iris"
        children:
        - name: postprocessor
          type: TRANSFORMER
          implementation: PYTHON
          modelUri: "gs://seldon-models/postprocessor"
```

3. **多模型服务（KServe）：**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: multi-model-example
spec:
  predictor:
    triton:
      storageUri: "gs://kserve-examples/models/triton/multi-model"
```

**安装专用服务平台：**
```bash
# Install KServe
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve.yaml

# Install Seldon Core (using Helm)
helm install seldon-core seldon-core-operator \
  --repo https://storage.googleapis.com/seldon-charts \
  --namespace seldon-system \
  --create-namespace
```

**模型服务监控：**
```bash
# Check KServe service status
kubectl get inferenceservices

# Check Seldon Core service status
kubectl get seldondeployments
```

**常规 Deployment 与专用服务平台的比较：**

| 功能 | 常规 Deployment | 专用服务平台 |
|---------|-------------------|------------------------------|
| 基础服务 | 支持 | 支持 |
| 模型版本管理 | 需要手动实现 | 内置支持 |
| 流量拆分 | 需要手动实现 | 内置支持 |
| Auto-scaling | 通过 HPA 提供有限支持 | 高级扩缩容支持 |
| 监控 | 需要手动实现 | 内置支持 |
| 预处理/后处理 | 需要手动实现 | 内置支持 |
| 批量推理 | 需要手动实现 | 内置支持 |
| 模型可解释性 | 需要手动实现 | 内置支持 |

**其他选项的问题：**
- A. 使用常规 Deployment 资源：可以实现基础服务，但缺少模型版本管理、流量拆分和高级监控等功能。
- C. 使用 StatefulSet 资源：适合需要状态持久化的应用程序，但缺少面向模型服务的专用功能。
- D. 使用 CronJob 资源：适合周期性批处理 Job，不适合实时模型服务。
</details>

### 6. 为 Kubernetes 中的 AI/ML 工作负载配置 auto-scaling 时，最合适的指标是什么？

A. CPU 利用率
B. 内存利用率
C. GPU 利用率
D. 基于工作负载特性的自定义指标

<details>
<summary>显示答案</summary>

**答案：D. 基于工作负载特性的自定义指标**

**解释：**
为 Kubernetes 中的 AI/ML 工作负载配置 auto-scaling 时，最合适的指标是基于工作负载特性的自定义指标。AI/ML 工作负载可能需要根据 CPU、内存和 GPU 利用率之外的多种因素进行扩缩容，例如请求延迟、队列长度和批大小。选择最能反映工作负载特性的指标非常重要。

**AI/ML 工作负载的 auto-scaling 指标类型：**
1. **基于资源的指标**：
   - CPU 利用率
   - 内存利用率
   - GPU 利用率

2. **自定义指标**：
   - 请求延迟
   - 请求吞吐量
   - 队列长度
   - 批大小
   - 模型准确率
   - 推理时间

3. **外部指标**：
   - 消息队列长度（Kafka、RabbitMQ 等）
   - 数据库查询延迟
   - API gateway 请求数

**按 AI/ML 工作负载类型推荐的指标：**
1. **模型推理 Service**：
   - 请求延迟
   - 每秒请求数（RPS）
   - 排队请求数量

2. **批处理 Job**：
   - Job 队列长度
   - 待处理数据量
   - Job 完成时间

3. **流式处理**：
   - 流处理延迟
   - 事件处理速率
   - 未处理事件数量

**Horizontal Pod Autoscaler (HPA) 示例：**
```yaml
# CPU utilization-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-cpu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

---
# Custom metric-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-custom
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: inference_latency_milliseconds
      target:
        type: AverageValue
        averageValue: 100

---
# External metric-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-external
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: kafka_topic_lag
        selector:
          matchLabels:
            topic: inference-requests
      target:
        type: AverageValue
        averageValue: 100
```

**自定义指标收集与暴露：**
1. **Prometheus Adapter**：将 Prometheus 收集的指标暴露给 Kubernetes API
2. **Custom Metrics API**：将自定义指标暴露给 Kubernetes API
3. **External Metrics API**：将外部系统指标暴露给 Kubernetes API

**Prometheus Adapter 配置示例：**
```yaml
# Prometheus Adapter configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
    - seriesQuery: 'inference_latency_milliseconds{namespace!="",pod!=""}'
      resources:
        overrides:
          namespace: {resource: "namespace"}
          pod: {resource: "pod"}
      name:
        matches: "inference_latency_milliseconds"
      metricsQuery: 'avg(<<.Series>>{<<.LabelMatchers>>})'
```

**KEDA (Kubernetes Event-driven Autoscaling) 示例：**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: inference-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc:9090
      metricName: inference_latency_milliseconds
      threshold: "100"
      query: avg(inference_latency_milliseconds{service="inference-service"})
```

**基于 GPU 利用率的扩缩容：**
可以使用 NVIDIA DCGM Exporter 等工具实现基于 GPU 利用率的扩缩容。

```yaml
# NVIDIA DCGM Exporter deployment
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  template:
    metadata:
      labels:
        app: dcgm-exporter
    spec:
      containers:
      - name: dcgm-exporter
        image: nvidia/dcgm-exporter:2.3.1-2.6.1-ubuntu20.04
        ports:
        - containerPort: 9400
          name: metrics
        securityContext:
          runAsNonRoot: false
          runAsUser: 0
        volumeMounts:
        - name: docker-socket
          mountPath: /var/run/docker.sock
      volumes:
      - name: docker-socket
        hostPath:
          path: /var/run/docker.sock

---
# GPU utilization-based HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa-gpu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: DCGM_FI_DEV_GPU_UTIL
      target:
        type: AverageValue
        averageValue: 70
```

**选择 auto-scaling 策略时的注意事项：**
1. **工作负载特性**：批处理、实时推理、流式处理等
2. **性能要求**：延迟、吞吐量、准确率等
3. **资源效率**：成本优化、资源利用率等
4. **可扩展性**：响应负载变化的能力
5. **稳定性**：防止快速扩缩容导致 Service 中断

**其他选项的问题：**
- A. CPU 利用率：AI/ML 工作负载通常受 GPU 或内存约束，因此仅靠 CPU 利用率可能无法做出合适的扩缩容决策。
- B. 内存利用率：内存利用率通常不会随工作负载增加而成比例增长，尤其是在模型加载后会保持相对稳定。
- C. GPU 利用率：GPU 利用率是重要指标，但并非所有 AI/ML 工作负载都使用 GPU；即使使用 GPU，仅靠 GPU 利用率也可能无法充分反映 Service 质量。
</details>
### 7. 为 Kubernetes 中的 AI/ML 工作负载配置网络时，最重要的考虑因素是什么？

A. NetworkPolicy 配置
B. Service mesh 实现
C. 面向分布式训练的高性能网络和拓扑感知
D. 外部可访问性配置

<details>
<summary>显示答案</summary>

**答案：C. 面向分布式训练的高性能网络和拓扑感知**

**解释：**
为 Kubernetes 中的 AI/ML 工作负载配置网络时，最重要的考虑因素是面向分布式训练的高性能网络和拓扑感知。分布式 AI/ML 工作负载需要在 Node 之间交换大量数据和模型参数，因此网络性能会显著影响整体训练和推理性能。识别网络拓扑以确保临近 Node 之间通信，对于最小化延迟非常重要。

**分布式 AI/ML 工作负载的网络要求：**
1. **高带宽**：用于交换大量数据和模型参数的高网络带宽
2. **低延迟**：用于 Node 间快速通信的低网络延迟
3. **RDMA (Remote Direct Memory Access) 支持**：通过内存之间的直接数据传输降低 CPU 开销
4. **拓扑感知**：考虑网络拓扑的 Pod 放置
5. **GPU 直接通信**：支持 NVIDIA GPUDirect RDMA 等直接 GPU 到 GPU 通信技术

**高性能网络配置示例：**
```yaml
# Node selector and affinity settings for high-performance networking
apiVersion: kubeflow.org/v1
kind: TFJob
metadata:
  name: distributed-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4
      template:
        spec:
          nodeSelector:
            network-type: high-performance
          affinity:
            podAntiAffinity:
              preferredDuringSchedulingIgnoredDuringExecution:
              - weight: 100
                podAffinityTerm:
                  labelSelector:
                    matchExpressions:
                    - key: tf-job-name
                      operator: In
                      values:
                      - distributed-training
                  topologyKey: kubernetes.io/hostname
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                - matchExpressions:
                  - key: topology.kubernetes.io/zone
                    operator: In
                    values:
                    - us-west-2a
          containers:
          - name: tensorflow
            image: tensorflow/tensorflow:2.6.0-gpu
            env:
            - name: TF_CONFIG
              valueFrom:
                configMapKeyRef:
                  name: tf-config
                  key: tf-config.json
            resources:
              limits:
                nvidia.com/gpu: 1
```

**网络拓扑感知配置：**
```yaml
# Topology spread constraints setting
apiVersion: v1
kind: Pod
metadata:
  name: ml-worker
  labels:
    app: distributed-training
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: distributed-training
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: distributed-training
  containers:
  - name: ml-container
    image: ml-training:latest
```

**高性能网络接口配置：**
```yaml
# High-performance network interface configuration using Multus CNI
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-net
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "sriov-net",
    "type": "sriov",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.1.0/24",
      "rangeStart": "192.168.1.10",
      "rangeEnd": "192.168.1.200"
    }
  }'

---
apiVersion: v1
kind: Pod
metadata:
  name: ml-worker
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-net
spec:
  containers:
  - name: ml-container
    image: ml-training:latest
    resources:
      limits:
        intel.com/sriov: 1
```

**RDMA 支持配置：**
```yaml
# Configuration for RDMA support
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: rdma-net
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "rdma-net",
    "type": "rdma",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.2.0/24"
    },
    "deviceID": "0000:03:00.0"
  }'

---
apiVersion: v1
kind: Pod
metadata:
  name: rdma-pod
  annotations:
    k8s.v1.cni.cncf.io/networks: rdma-net
spec:
  containers:
  - name: rdma-container
    image: rdma-app:latest
    securityContext:
      capabilities:
        add: ["IPC_LOCK"]
    volumeMounts:
    - name: rdma-devices
      mountPath: /dev/infiniband
  volumes:
  - name: rdma-devices
    hostPath:
      path: /dev/infiniband
```

**NVIDIA GPUDirect RDMA 配置：**
```yaml
# Configuration for NVIDIA GPUDirect RDMA support
apiVersion: v1
kind: Pod
metadata:
  name: gpudirect-pod
spec:
  containers:
  - name: gpudirect-container
    image: nvidia/cuda:11.0-base
    command: ["sleep", "infinity"]
    resources:
      limits:
        nvidia.com/gpu: 1
    securityContext:
      capabilities:
        add: ["IPC_LOCK"]
    volumeMounts:
    - name: nvidia-dev
      mountPath: /dev/nvidia0
    - name: nvidia-uvm
      mountPath: /dev/nvidia-uvm
    - name: nvidia-uvm-tools
      mountPath: /dev/nvidia-uvm-tools
    - name: nvidia-modeset
      mountPath: /dev/nvidia-modeset
  volumes:
  - name: nvidia-dev
    hostPath:
      path: /dev/nvidia0
  - name: nvidia-uvm
    hostPath:
      path: /dev/nvidia-uvm
  - name: nvidia-uvm-tools
    hostPath:
      path: /dev/nvidia-uvm-tools
  - name: nvidia-modeset
    hostPath:
      path: /dev/nvidia-modeset
```

**网络性能优化策略：**
1. **Node 放置优化**：将相关 Pod 放置在同一机架或临近 Node 上
2. **网络接口优化**：使用 SR-IOV、DPDK 等技术提升网络性能
3. **网络拓扑感知**：使用 topology spread constraints，根据网络拓扑放置 Pod
4. **使用专用网络**：为 AI/ML 工作负载配置专用网络接口
5. **MTU 优化**：针对大包传输优化 MTU (Maximum Transmission Unit)

**网络性能测试：**
```bash
# Network performance test using iperf3
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201

kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**其他选项的问题：**
- A. NetworkPolicy 配置：对安全很重要，但不会直接影响 AI/ML 工作负载性能。
- B. Service mesh 实现：对微服务架构有用，但无法满足 AI/ML 工作负载的高性能网络需求。
- D. 外部可访问性配置：对模型服务很重要，但不会直接影响分布式训练性能。
</details>

### 8. 为 Kubernetes 中的 AI/ML 工作负载配置安全性时，最重要的考虑因素是什么？

A. NetworkPolicy 配置
B. 模型和数据的访问控制与加密
C. 容器镜像扫描
D. Pod security policy 配置

<details>
<summary>显示答案</summary>

**答案：B. 模型和数据的访问控制与加密**

**解释：**
为 Kubernetes 中的 AI/ML 工作负载配置安全性时，最重要的考虑因素是模型和数据的访问控制与加密。AI/ML 工作负载通常处理敏感数据和作为知识产权的模型，因此保护这些资产最为重要。数据泄露或模型盗窃可能带来严重的业务和合规影响。

**AI/ML 工作负载的主要安全风险：**
1. **数据泄露**：训练数据、推理数据等敏感信息泄露
2. **模型盗窃**：作为知识产权的模型文件被盗
3. **模型投毒**：通过对抗性攻击降低模型性能或注入偏差
4. **推理操纵**：通过操纵输入数据诱导错误预测
5. **权限提升**：通过过高权限获得系统访问权限

**模型和数据安全的主要策略：**
1. **访问控制**：
   - 通过 RBAC (Role-Based Access Control) 进行细粒度权限管理
   - 应用最小权限原则
   - 分离 Service account

2. **加密**：
   - Encryption at Rest
   - Encryption in Transit
   - 模型文件加密

3. **Secret 管理**：
   - 使用 Kubernetes Secrets 或外部 secret 管理系统
   - 安全管理 API key、认证 token 等

4. **容器安全**：
   - 以最小权限运行容器
   - 使用只读文件系统
   - 以非 root 用户运行

**RBAC 配置示例：**
```yaml
# Role definition for model access
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: model-reader
  namespace: ml-models
rules:
- apiGroups: [""]
  resources: ["secrets", "configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["model-weights", "model-config"]

---
# Model access role binding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: model-reader-binding
  namespace: ml-models
subjects:
- kind: ServiceAccount
  name: inference-service
  namespace: ml-models
roleRef:
  kind: Role
  name: model-reader
  apiGroup: rbac.authorization.k8s.io
```

**加密模型存储示例：**
```yaml
# Secret for encrypted model storage
apiVersion: v1
kind: Secret
metadata:
  name: model-weights
  namespace: ml-models
type: Opaque
data:
  model.h5: <base64-encoded-encrypted-model>

---
# Pod using encrypted model
apiVersion: v1
kind: Pod
metadata:
  name: inference-pod
  namespace: ml-models
spec:
  serviceAccountName: inference-service
  containers:
  - name: inference
    image: ml-inference:latest
    volumeMounts:
    - name: model-volume
      mountPath: /models
      readOnly: true
    env:
    - name: MODEL_ENCRYPTION_KEY
      valueFrom:
        secretKeyRef:
          name: model-encryption-keys
          key: key1
  volumes:
  - name: model-volume
    secret:
      secretName: model-weights
```

**外部 secret 管理系统集成示例（HashiCorp Vault）：**
```yaml
# Secret injection using Vault Agent Injector
apiVersion: v1
kind: Pod
metadata:
  name: ml-training
  namespace: ml-workloads
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-secret-db-creds: "database/creds/ml-training-role"
    vault.hashicorp.com/role: "ml-training-role"
spec:
  serviceAccountName: ml-training
  containers:
  - name: training
    image: ml-training:latest
```

**数据加密配置示例：**
```yaml
# PersistentVolume with EBS encryption
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: encrypted-data
  namespace: ml-workloads
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: encrypted-storage
  resources:
    requests:
      storage: 100Gi

---
# Encrypted storage class
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

**容器安全加固示例：**
```yaml
# Security-hardened pod configuration
apiVersion: v1
kind: Pod
metadata:
  name: secure-ml-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  containers:
  - name: ml-container
    image: ml-image:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: model-output
      mountPath: /output
  volumes:
  - name: tmp
    emptyDir: {}
  - name: model-output
    persistentVolumeClaim:
      claimName: model-output-pvc
```

**NetworkPolicy 示例：**
```yaml
# Network policy for ML workloads
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ml-network-policy
  namespace: ml-workloads
spec:
  podSelector:
    matchLabels:
      app: ml-inference
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          name: logging
    ports:
    - protocol: TCP
      port: 8125
```

**模型和数据安全的其他策略：**
1. **模型签名和验证**：对模型文件应用数字签名，并在使用前验证
2. **模型版本管理**：跟踪模型版本和变更
3. **审计日志**：维护模型和数据访问的审计日志
4. **数据掩码**：对敏感数据字段进行掩码处理
5. **差分隐私**：应用差分隐私技术保护个人信息

**其他选项的问题：**
- A. NetworkPolicy 配置：很重要，但其本身并不能直接保证模型和数据安全。
- C. 容器镜像扫描：对漏洞管理很重要，但不能直接解决模型和数据安全问题。
- D. Pod security policy 配置：增强容器执行环境安全性，但其本身并不能直接保证模型和数据安全。
</details>
### 9. 为 Kubernetes 中的 AI/ML 工作负载配置日志记录和监控时，最重要的指标是什么？

A. Pod 和 Node 状态
B. 模型性能指标（准确率、延迟等）和资源使用情况
C. API 调用次数
D. 网络流量

<details>
<summary>显示答案</summary>

**答案：B. 模型性能指标（准确率、延迟等）和资源使用情况**

**解释：**
为 Kubernetes 中的 AI/ML 工作负载配置日志记录和监控时，最重要的指标是模型性能指标（准确率、延迟等）和资源使用情况。这些指标直接反映模型质量、SLO (Service Level Objective) 合规性和资源效率，并有助于及早发现模型性能下降或资源瓶颈。

**关键监控指标：**

1. **模型性能指标**：
   - **Accuracy**：模型预测的准确率
   - **Precision**：预测为正的样本中实际为正的比例
   - **Recall**：实际为正的样本中被预测为正的比例
   - **F1 Score**：Precision 和 Recall 的调和平均数
   - **AUC-ROC**：二分类模型的性能度量
   - **Mean Squared Error (MSE)**：回归模型的误差度量

2. **Service 级别指标**：
   - **延迟**：从请求到响应的时间
   - **吞吐量**：单位时间内处理的请求数量
   - **错误率**：失败请求的比例
   - **可用性**：Service 正常响应的时间比例

3. **资源使用情况**：
   - **CPU 利用率**：容器和 Node 的 CPU 利用率
   - **内存利用率**：容器和 Node 的内存利用率
   - **GPU 利用率**：GPU 计算和内存利用率
   - **磁盘 I/O**：存储读写性能
   - **网络 I/O**：网络发送/接收性能

**监控栈配置示例：**
```yaml
# Prometheus configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
    - job_name: 'ml-metrics'
      kubernetes_sd_configs:
      - role: pod
        selectors:
        - role: pod
          label: "app=ml-inference"
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__

---
# Expose metrics from ML service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: inference
        image: ml-inference:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
```

**自定义指标暴露示例（Python）：**
```python
from prometheus_client import start_http_server, Summary, Counter, Gauge, Histogram
import time
import random

# Metric definitions
INFERENCE_LATENCY = Histogram('inference_latency_seconds', 'Inference latency in seconds',
                             ['model', 'version'])
INFERENCE_REQUESTS = Counter('inference_requests_total', 'Total number of inference requests',
                            ['model', 'version', 'status'])
MODEL_ACCURACY = Gauge('model_accuracy', 'Model accuracy',
                      ['model', 'version', 'dataset'])
GPU_MEMORY_USAGE = Gauge('gpu_memory_usage_bytes', 'GPU memory usage in bytes',
                        ['device'])

# Start metrics server
start_http_server(9090)

# Metric update example
def process_request(model_name, model_version, input_data):
    start_time = time.time()

    try:
        # Perform model inference
        result = model.predict(input_data)

        # Record latency
        latency = time.time() - start_time
        INFERENCE_LATENCY.labels(model=model_name, version=model_version).observe(latency)

        # Increment request count
        INFERENCE_REQUESTS.labels(model=model_name, version=model_version, status="success").inc()

        # Update GPU memory usage
        GPU_MEMORY_USAGE.labels(device="gpu0").set(get_gpu_memory_usage())

        return result
    except Exception as e:
        # Increment error request count
        INFERENCE_REQUESTS.labels(model=model_name, version=model_version, status="error").inc()
        raise e

# Periodically update model accuracy
def update_model_accuracy():
    while True:
        accuracy = evaluate_model_accuracy()
        MODEL_ACCURACY.labels(model="image_classifier", version="v1", dataset="validation").set(accuracy)
        time.sleep(3600)  # Update every hour
```

**Grafana dashboard 配置示例：**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ml-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  ml-dashboard.json: |
    {
      "title": "ML Model Monitoring",
      "panels": [
        {
          "title": "Inference Latency",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version))",
              "legendFormat": "p95 - {{model}} - {{version}}"
            },
            {
              "expr": "histogram_quantile(0.50, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version))",
              "legendFormat": "p50 - {{model}} - {{version}}"
            }
          ]
        },
        {
          "title": "Request Rate",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "sum(rate(inference_requests_total[5m])) by (model, version, status)",
              "legendFormat": "{{model}} - {{version}} - {{status}}"
            }
          ]
        },
        {
          "title": "Model Accuracy",
          "type": "gauge",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "model_accuracy",
              "legendFormat": "{{model}} - {{version}} - {{dataset}}"
            }
          ],
          "options": {
            "min": 0,
            "max": 1,
            "thresholds": [
              { "color": "red", "value": 0 },
              { "color": "yellow", "value": 0.7 },
              { "color": "green", "value": 0.9 }
            ]
          }
        },
        {
          "title": "GPU Memory Usage",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "gpu_memory_usage_bytes",
              "legendFormat": "{{device}}"
            }
          ]
        }
      ]
    }
```

**日志记录配置示例：**
```yaml
# Fluent Bit configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush        5
        Daemon       Off
        Log_Level    info

    [INPUT]
        Name             tail
        Tag              kube.*
        Path             /var/log/containers/*.log
        Parser           docker
        DB               /var/log/flb_kube.db
        Mem_Buf_Limit    5MB
        Skip_Long_Lines  On
        Refresh_Interval 10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       log_processed
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [FILTER]
        Name         grep
        Match        kube.var.log.containers.ml-*
        Regex        log ERROR|WARN|INFO

    [OUTPUT]
        Name            es
        Match           kube.var.log.containers.ml-*
        Host            elasticsearch
        Port            9200
        Index           ml-logs
        Type            _doc
        Logstash_Format On
        Logstash_Prefix ml-logs
        Time_Key        @timestamp
        Replace_Dots    On
        Retry_Limit     False
```

**用于模型性能监控的其他工具：**
1. **MLflow**：实验跟踪、模型版本管理、模型注册表
2. **TensorBoard**：TensorFlow 模型训练过程和性能可视化
3. **Weights & Biases**：实验跟踪、模型性能比较、超参数优化
4. **Seldon Core Metrics**：Seldon Core 提供的模型服务指标
5. **KServe Metrics**：KServe 提供的模型服务指标

**监控告警配置示例：**
```yaml
# Prometheus alert rules
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ml-alerts
  namespace: monitoring
spec:
  groups:
  - name: ml.rules
    rules:
    - alert: HighInferenceLatency
      expr: histogram_quantile(0.95, sum(rate(inference_latency_seconds_bucket[5m])) by (le, model, version)) > 0.5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High inference latency"
        description: "Model {{ $labels.model }} version {{ $labels.version }} has p95 latency above 500ms"

    - alert: LowModelAccuracy
      expr: model_accuracy < 0.8
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "Low model accuracy"
        description: "Model {{ $labels.model }} version {{ $labels.version }} has accuracy below 80%"

    - alert: HighErrorRate
      expr: sum(rate(inference_requests_total{status="error"}[5m])) / sum(rate(inference_requests_total[5m])) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate"
        description: "Error rate is above 5%"
```

**其他选项的问题：**
- A. Pod 和 Node 状态：对基础系统状态监控很重要，但不能直接反映 AI/ML 工作负载的性能和质量。
- C. API 调用次数：对衡量系统使用情况有用，但不能直接表示模型性能或资源效率。
- D. 网络流量：对分布式训练或大规模数据传输很重要，但不能直接反映模型性能或质量。
</details>

### 10. Kubernetes 中 AI/ML 工作负载最有效的成本优化策略是什么？

A. 始终使用最新实例类型
B. 对所有工作负载使用 Spot 实例
C. 基于工作负载特性选择合适的实例类型并进行 auto-scaling
D. 最小化所有资源的 requests 和 limits

<details>
<summary>显示答案</summary>

**答案：C. 基于工作负载特性选择合适的实例类型并进行 auto-scaling**

**解释：**
Kubernetes 中 AI/ML 工作负载最有效的成本优化策略是基于工作负载特性选择合适的实例类型并进行 auto-scaling。AI/ML 工作负载在训练、推理和数据预处理等不同阶段有不同的资源需求，选择匹配每个工作负载特性的实例类型，并按需进行 auto-scaling，对于优化成本效率非常重要。

**按工作负载特性选择实例类型：**

1. **模型训练**：
   - **GPU 实例**：适合深度学习模型训练
   - **内存优化实例**：适合大规模数据集处理
   - **计算优化实例**：适合计算密集型算法

2. **模型推理**：
   - **GPU 实例**：适合复杂模型或实时推理
   - **CPU 实例**：适合简单模型或批量推理
   - **推理优化实例（AWS Inferentia、Google TPU 等）**：面向推理的专用实例

3. **数据预处理**：
   - **计算优化实例**：适合并行处理
   - **内存优化实例**：适合大规模数据集处理
   - **存储优化实例**：适合 I/O 密集型 Job

**Node group 配置示例：**
```yaml
# Training node group (GPU instances)
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ml-cluster
  region: us-west-2
nodeGroups:
  - name: training-ng
    instanceType: p3.2xlarge  # GPU instance
    minSize: 0
    maxSize: 10
    labels:
      workload-type: training
    taints:
      - key: workload-type
        value: training
        effect: NoSchedule
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # Inference node group (CPU instances)
  - name: inference-ng
    instanceType: c5.2xlarge  # Compute-optimized instance
    minSize: 1
    maxSize: 20
    labels:
      workload-type: inference
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # Data preprocessing node group (Memory-optimized instances)
  - name: preprocessing-ng
    instanceType: r5.2xlarge  # Memory-optimized instance
    minSize: 0
    maxSize: 10
    labels:
      workload-type: preprocessing
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"

  # Spot instance node group (Cost-effective batch jobs)
  - name: spot-ng
    instanceTypes: ["m5.xlarge", "m5a.xlarge", "m5n.xlarge"]
    minSize: 0
    maxSize: 20
    spot: true
    labels:
      workload-type: batch
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
      k8s.io/cluster-autoscaler/ml-cluster: "owned"
```

**工作负载放置示例：**
```yaml
# Training job (Place on GPU nodes)
apiVersion: batch/v1
kind: Job
metadata:
  name: training-job
spec:
  template:
    spec:
      nodeSelector:
        workload-type: training
      containers:
      - name: training
        image: training:latest
        resources:
          limits:
            nvidia.com/gpu: 1

# Inference service (Place on CPU nodes)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      nodeSelector:
        workload-type: inference
      containers:
      - name: inference
        image: inference:latest
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi

# Data preprocessing job (Place on memory-optimized nodes)
apiVersion: batch/v1
kind: Job
metadata:
  name: preprocessing-job
spec:
  template:
    spec:
      nodeSelector:
        workload-type: preprocessing
      containers:
      - name: preprocessing
        image: preprocessing:latest
        resources:
          requests:
            memory: 16Gi
          limits:
            memory: 32Gi

# Batch inference job (Place on Spot instances)
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-inference
spec:
  template:
    spec:
      nodeSelector:
        workload-type: batch
      tolerations:
      - key: spot
        operator: Exists
      containers:
      - name: batch-inference
        image: batch-inference:latest
```

**Auto-scaling 配置示例：**
```yaml
# Cluster Autoscaler configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-config
  namespace: kube-system
data:
  config.yaml: |
    expendablePodsPriorityCutoff: -10
    scaleDownUtilizationThreshold: 0.5
    scaleDownUnneededTime: 5m
    scaleDownDelayAfterAdd: 5m
    scaleDownDelayAfterDelete: 0s
    scaleDownDelayAfterFailure: 3m
    maxNodeProvisionTime: 15m

# HPA configuration (Inference service)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: inference_latency_milliseconds
      target:
        type: AverageValue
        averageValue: 100
```

**成本优化策略：**

1. **选择合适的实例类型**：
   - 选择匹配工作负载特性的实例类型
   - 通过成本与性能分析选择最优实例
   - 利用专用实例（GPU、TPU 等）

2. **Spot 实例利用**：
   - 将 Spot 实例用于容错工作负载
   - 通过指定多种实例类型提高可用性
   - 实现中断容忍策略

3. **Auto-scaling**：
   - 通过 Cluster Autoscaler 自动调整 Node 数量
   - 通过 HPA 自动调整 Pod 数量
   - 基于自定义指标的扩缩容

4. **资源 request 和 limit 优化**：
   - 基于实际使用情况设置资源 request
   - 通过 Vertical Pod Autoscaler 自动调整资源 request
   - 资源使用监控和优化

5. **Job 调度优化**：
   - 在成本较低的时间段运行批处理 Job
   - 将低优先级 Job 放置在低成本资源上
   - Job 队列和优先级设置

**成本监控和优化工具：**
1. **Kubecost**：Kubernetes 集群的成本监控和优化
2. **AWS Cost Explorer**：AWS 资源成本分析
3. **Google Cloud Cost Management**：GCP 资源成本分析
4. **Azure Cost Management**：Azure 资源成本分析
5. **Prometheus + Grafana**：自定义成本 dashboard 配置

**其他选项的问题：**
- A. 始终使用最新实例类型：最新实例并不总是最具成本效益，选择匹配工作负载特性的实例更重要。
- B. 对所有工作负载使用 Spot 实例：Spot 实例可能被中断，因此不适合对中断敏感的关键工作负载。
- D. 最小化所有资源的 requests 和 limits：过度最小化资源 request 可能导致性能问题，匹配工作负载特性的适当资源分配很重要。
</details>
