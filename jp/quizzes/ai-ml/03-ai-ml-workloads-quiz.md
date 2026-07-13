# AI/ML Workloads クイズ

このクイズでは、Kubernetes で AI/ML workloads を実行することについての理解を確認します。

## クイズ問題

### 1. Kubernetes で GPU を使用する Pod をスケジュールするために必要な resource request フィールドは何ですか?

A. resources.requests.gpu
B. resources.requests.nvidia.com/gpu
C. resources.requests.k8s.io/gpu
D. resources.requests.compute/gpu

<details>
<summary>解答を表示</summary>

**解答: B. resources.requests.nvidia.com/gpu**

**解説:**
Kubernetes で GPU を使用する Pod をスケジュールするために必要な resource request フィールドは `resources.requests.nvidia.com/gpu` です。これは NVIDIA GPU を要求する標準的な方法であり、他の GPU ベンダーは独自の namespace（例: `amd.com/gpu`）を使用する場合があります。

**GPU resource request の例:**
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

**GPU resource の特性:**
1. **整数単位の割り当て**: GPU は整数単位（例: 1、2、3）でのみ割り当てることができます。小数値（例: 0.5）はサポートされていません。
2. **requests と limits の一致**: GPU resources では、`requests` と `limits` は同じである必要があります。
3. **排他的使用**: デフォルトでは、GPU は containers 間で共有されません。各 GPU は一度に 1 つの container にのみ割り当てられます。
4. **Node labels**: GPU を持つ Nodes には通常 `nvidia.com/gpu` の label が付けられます。

**GPU 使用の前提条件:**
1. **Node 上の GPU hardware**: 物理 GPU が Node にインストールされている必要があります。
2. **GPU drivers**: 適切な GPU drivers が Node にインストールされている必要があります。
3. **NVIDIA Device Plugin**: NVIDIA Device Plugin が Kubernetes cluster にインストールされている必要があります。
4. **Container runtime support**: Container runtime が GPU をサポートしている必要があります。

**NVIDIA Device Plugin のインストール:**
```bash
# Installation using Helm
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
helm install nvidia-device-plugin nvdp/nvidia-device-plugin

# Or direct installation
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.13.0/nvidia-device-plugin.yml
```

**GPU resources の確認:**
```bash
# Check GPU resources on nodes
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu

# Check pods using GPUs
kubectl get pods -A -o custom-columns=NAME:.metadata.name,GPU:.spec.containers[*].resources.limits.nvidia\\.com/gpu
```

**Multi-GPU request:**
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

**GPU memory partitioning (NVIDIA MPS):**
NVIDIA Multi-Process Service (MPS) は、複数の processes が同じ GPU を共有できるようにします。これは Kubernetes ではネイティブにサポートされておらず、カスタム設定が必要です。

**その他の GPU ベンダー:**
その他の GPU ベンダーは独自の namespace を使用します:
- AMD GPU: `amd.com/gpu`
- Intel GPU: `intel.com/gpu`

**他の選択肢の問題点:**
- A. resources.requests.gpu: これは有効な Kubernetes resource フィールドではありません。GPU resources は vendor-specific namespace を使用する必要があります。
- C. resources.requests.k8s.io/gpu: これは有効な Kubernetes resource フィールドではありません。`k8s.io` namespace は通常、Kubernetes core resources に使用されます。
- D. resources.requests.compute/gpu: これは有効な Kubernetes resource フィールドではありません。
</details>

### 2. Kubernetes で分散 TensorFlow training jobs を実行するために最も適した resource type は何ですか?

A. Deployment
B. StatefulSet
C. Job
D. TFJob (Kubeflow)

<details>
<summary>解答を表示</summary>

**解答: D. TFJob (Kubeflow)**

**解説:**
Kubernetes で分散 TensorFlow training jobs を実行するために最も適した resource type は `TFJob` です。TFJob は Kubeflow project の一部であり、Kubernetes 上で TensorFlow training jobs を実行するために特別に設計された custom resource です。

**TFJob の主な機能:**
1. **分散 training support**: workers、parameter servers、evaluators を含む TensorFlow の分散 training architecture をサポートします。
2. **自動復旧**: 失敗した workers を自動的に再起動します。
3. **Gang scheduling**: すべての workers が同時にスケジュールされることを保証します。
4. **TensorFlow-specific features**: TensorFlow 分散 training に必要な environment variables と settings を自動的に設定します。
5. **Monitoring and logging**: TensorFlow job の status と logs を監視する機能を提供します。

**TFJob の例:**
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

**TFJob components:**
1. **Chief**: model checkpoints の保存と summaries の書き込みを担当する main worker です。
2. **Worker**: model training を実行する workers です。
3. **PS (Parameter Server)**: model parameters を保存し更新します。
4. **Evaluator**: model evaluation を実行します。

**TFJob のインストール:**
```bash
# Install Kubeflow
kubectl apply -f https://raw.githubusercontent.com/kubeflow/kubeflow/master/kfctl_k8s_istio.yaml

# Or install only the TFJob controller
kubectl apply -f https://raw.githubusercontent.com/kubeflow/tf-operator/master/deploy/v1/tf-operator.yaml
```

**TFJob の監視:**
```bash
# Check TFJob status
kubectl get tfjobs

# Check specific TFJob details
kubectl describe tfjob mnist-training

# Check TFJob pods
kubectl get pods -l tf-job-name=mnist-training
```

**他の resource types との比較:**

1. **Deployment**:
   - 長時間実行される services に適しています
   - 自動復旧と rolling updates をサポートします
   - 分散 training jobs のための coordination features がありません
   - TensorFlow-specific features がありません

2. **StatefulSet**:
   - 安定した network identifiers と persistent storage を提供します
   - 順序付けられた deployment と scaling
   - 分散 training jobs のための coordination features がありません
   - TensorFlow-specific features がありません

3. **Job**:
   - one-time jobs に適しています
   - job completion を保証します
   - 分散 training jobs のための coordination features がありません
   - TensorFlow-specific features がありません

4. **TFJob**:
   - TensorFlow distributed training に最適化されています
   - workers、parameter servers のような roles を定義します
   - TensorFlow-specific environment variables と settings を自動的に設定します
   - job completion と failure handling logic が組み込まれています

**他の ML frameworks 向け Kubeflow operators:**
- **PyTorchJob**: PyTorch training jobs 用
- **MPIJob**: Horovod のような MPI-based distributed training 用
- **XGBoostJob**: XGBoost training jobs 用

**他の選択肢の問題点:**
- A. Deployment: 長時間実行される services には適していますが、分散 TensorFlow training jobs の特定の要件を処理しません。
- B. StatefulSet: state persistence を必要とする applications には適していますが、分散 TensorFlow training jobs のための coordination features がありません。
- C. Job: one-time jobs には適していますが、分散 TensorFlow training jobs の特定の要件を処理しません。
</details>
### 3. Kubernetes で AI/ML workloads の persistent storage を設定するときに最も重要な考慮事項は何ですか?

A. Storage capacity
B. Storage class type
C. Data access patterns and throughput requirements
D. Storage provisioner

<details>
<summary>解答を表示</summary>

**解答: C. Data access patterns and throughput requirements**

**解説:**
Kubernetes で AI/ML workloads の persistent storage を設定するときに最も重要な考慮事項は、data access patterns と throughput requirements です。AI/ML workloads は大量のデータを処理し、さまざまな access patterns（sequential reads、random reads、parallel access など）を持つことがあり、多くの場合 high throughput が必要です。これらの要件を満たす storage solution を選択することは、performance と efficiency に大きな影響を与えます。

**AI/ML workloads における一般的な data access patterns:**
1. **Large dataset reads**: Training datasets は数 GB から数 TB に及ぶ場合があり、効率的な read performance が必要です。
2. **Parallel access**: 複数の workers が同時にデータへアクセスする distributed training scenarios は一般的です。
3. **Sequential reads**: データセット全体を順番に読み込む batch processing jobs。
4. **Random access**: データセットのランダムな部分にアクセスする mini-batch training や online learning。
5. **Checkpoint saving**: training 中に model checkpoints を保存するための write operations。

**AI/ML workloads に適した storage solutions:**

1. **Distributed file systems**:
   - **Amazon FSx for Lustre**: high-performance computing と machine learning workloads に最適化された high-performance file system
   - **GlusterFS/Ceph**: scalability と parallel access をサポートする open-source distributed file systems
   - **HDFS**: large-scale dataset processing に適した Hadoop Distributed File System

2. **High-performance block storage**:
   - **AWS EBS io2/io2 Block Express**: high IOPS と throughput を提供する SSD-based block storage
   - **GCP Persistent Disk SSD**: high IOPS と throughput を提供する SSD-based block storage
   - **Azure Ultra Disk**: 非常に高い IOPS と throughput を提供する SSD-based block storage

3. **Object storage**:
   - **Amazon S3**: large-scale dataset storage に適した highly scalable object storage
   - **Google Cloud Storage**: large-scale dataset storage に適した highly scalable object storage
   - **Azure Blob Storage**: large-scale dataset storage に適した highly scalable object storage

**Storage configuration の例 (FSx for Lustre):**
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

**Storage を選択するときに考慮すべき performance metrics:**
1. **Throughput**: 1 秒あたりに読み書きできるデータ量（MB/s または GB/s）
2. **IOPS (Input/Output Operations Per Second)**: 1 秒あたりに実行できる I/O operations の数
3. **Latency**: I/O requests の response time
4. **Parallel access support**: 複数の clients が同時にアクセスできる能力
5. **Scalability**: データが増加しても performance を維持できる能力

**AI/ML workload type ごとの推奨 storage:**
1. **Large-scale distributed training**: FSx for Lustre、HDFS、Ceph
2. **Single-node training**: High-performance SSD block storage
3. **Data preprocessing**: Distributed file systems または object storage
4. **Model serving**: High-performance SSD block storage または in-memory storage

**Storage performance testing:**
```bash
# Storage performance test using FIO
kubectl run fio-test --image=nixery.dev/shell/fio --restart=Never -- \
  fio --name=benchmark --directory=/data --direct=1 --rw=randread --bs=4k \
  --size=1G --numjobs=16 --runtime=60 --group_reporting
```

**他の選択肢の問題点:**
- A. Storage capacity: 重要ですが、capacity だけでは AI/ML workloads の performance requirements を満たすことはできません。
- B. Storage class type: Storage class は provisioning method を定義しますが、それ自体で performance characteristics を完全に決定するわけではありません。
- D. Storage provisioner: Provisioner は storage の作成方法を定義しますが、workload performance requirements に直接対応するものではありません。
</details>

### 4. Kubernetes で AI/ML workloads の resource allocation を行う最も効果的な方法は何ですか?

A. すべての Pods に同じ resources を割り当てる
B. Workload characteristics に基づく resource profiling と optimization
C. 常に最大 resources を要求する
D. Resource requests なしで deploy する

<details>
<summary>解答を表示</summary>

**解答: B. Workload characteristics に基づく resource profiling と optimization**

**解説:**
Kubernetes で AI/ML workloads の resource allocation を行う最も効果的な方法は、workload characteristics に基づく resource profiling と optimization です。AI/ML workloads は training、inference、data preprocessing などのさまざまな段階で異なる resource requirements を持ち、各 workload の characteristics を理解してそれに応じて resources を割り当てることが、performance と cost efficiency の最適化に重要です。

**AI/ML workload resource profiling methods:**
1. **Benchmarking**: さまざまな resource configurations で workloads を実行し、performance を測定します。
2. **Monitoring**: 実際の resource usage を監視して patterns を特定します。
3. **Gradual adjustment**: 初期見積もりから始め、resources を段階的に調整します。
4. **Auto-scaling**: workload demands に基づいて resources を自動的に調整します。

**AI/ML workload type ごとの resource characteristics:**

1. **Model training**:
   - CPU: data preprocessing と feature engineering に重要
   - GPU: deep learning model training に不可欠
   - Memory: large datasets と model parameter storage に必要
   - Storage: dataset と checkpoint storage に必要

2. **Model inference**:
   - CPU: simple models または batch inference に適しています
   - GPU: complex models または real-time inference に有利です
   - Memory: model loading と input/output processing に必要
   - Latency: real-time inference に重要

3. **Data preprocessing**:
   - CPU: parallel processing capability が重要
   - Memory: large-scale dataset processing に必要
   - Storage I/O: data read/write performance が重要

**Resource optimization の例:**
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

**Resource monitoring and optimization tools:**
1. **Prometheus + Grafana**: Resource usage の monitoring と visualization
2. **Kubernetes Metrics Server**: 基本的な resource metric collection
3. **NVIDIA DCGM Exporter**: GPU metric collection
4. **Vertical Pod Autoscaler**: Resource request の自動調整
5. **Horizontal Pod Autoscaler**: Pod 数の自動調整

**Resource optimization strategies:**
1. **GPU sharing**: NVIDIA MPS または time-sliced scheduling によって複数の jobs 間で GPU を共有します
2. **Memory optimization**: Model quantization、lazy loading、memory-efficient algorithms
3. **Batch processing**: Throughput を向上させるため inference requests を batch で処理します
4. **Auto-scaling**: load に基づいて resources を自動的に調整します
5. **Node affinity**: 特定の hardware characteristics を持つ Nodes に workloads を配置します

**GPU memory optimization の例:**
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

**CPU and memory optimization の例:**
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

**他の選択肢の問題点:**
- A. すべての Pods に同じ resources を割り当てる: 異なる workload characteristics を考慮しないため、resource waste や不足が発生する可能性があります。
- C. 常に最大 resources を要求する: cost efficiency が低く、cluster resource utilization が低くなります。
- D. Resource requests なしで deploy する: scheduling と resource contention の問題を引き起こす可能性があり、GPU のような limited resources では特に重要です。
</details>
### 5. Kubernetes で AI/ML model serving を行う最も適した方法は何ですか?

A. 通常の Deployment resources を使用する
B. KServe（旧 KFServing）や Seldon Core のような specialized serving platforms を使用する
C. StatefulSet resources を使用する
D. CronJob resources を使用する

<details>
<summary>解答を表示</summary>

**解答: B. KServe（旧 KFServing）や Seldon Core のような specialized serving platforms を使用する**

**解説:**
Kubernetes で AI/ML model serving を行う最も適した方法は、KServe（旧 KFServing）や Seldon Core のような specialized serving platforms を使用することです。これらの platforms は model serving に必要なさまざまな機能（model version management、A/B testing、canary deployment、auto-scaling、monitoring など）を提供し、さまざまな ML frameworks をサポートします。

**Specialized model serving platforms の主な機能:**
1. **Various ML framework support**: TensorFlow、PyTorch、ONNX、scikit-learn などのさまざまな frameworks で trained された models をサポートします
2. **Model version management**: models の複数 versions を管理し、rollback を可能にします
3. **Traffic splitting**: A/B testing、canary deployment などのための traffic splitting features
4. **Auto-scaling**: request load に基づく auto-scaling
5. **Monitoring and logging**: model performance、latency、throughput などの monitoring
6. **Pre and post-processing**: input data preprocessing と output data post-processing pipelines
7. **Batch inference**: 大量データに対する batch inference のサポート
8. **Model explainability**: model predictions を説明する機能

**KServe の例:**
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

**Seldon Core の例:**
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

**Advanced serving feature の例:**

1. **Canary deployment (KServe):**
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

2. **Pre and post-processing pipeline (Seldon Core):**
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

3. **Multi-model serving (KServe):**
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

**Specialized serving platforms のインストール:**
```bash
# Install KServe
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve.yaml

# Install Seldon Core (using Helm)
helm install seldon-core seldon-core-operator \
  --repo https://storage.googleapis.com/seldon-charts \
  --namespace seldon-system \
  --create-namespace
```

**Model serving monitoring:**
```bash
# Check KServe service status
kubectl get inferenceservices

# Check Seldon Core service status
kubectl get seldondeployments
```

**通常の Deployment と specialized serving platforms の比較:**

| Feature | Regular Deployment | Specialized Serving Platform |
|---------|-------------------|------------------------------|
| Basic serving | Supported | Supported |
| Model version management | Manual implementation required | Built-in support |
| Traffic splitting | Manual implementation required | Built-in support |
| Auto-scaling | Limited support with HPA | Advanced scaling support |
| Monitoring | Manual implementation required | Built-in support |
| Pre/post-processing | Manual implementation required | Built-in support |
| Batch inference | Manual implementation required | Built-in support |
| Model explainability | Manual implementation required | Built-in support |

**他の選択肢の問題点:**
- A. 通常の Deployment resources を使用する: basic serving は可能ですが、model version management、traffic splitting、advanced monitoring のような機能がありません。
- C. StatefulSet resources を使用する: state persistence を必要とする applications には適していますが、model serving のための specialized features がありません。
- D. CronJob resources を使用する: periodic batch jobs には適しており、real-time model serving には適していません。
</details>

### 6. Kubernetes で AI/ML workloads の auto-scaling を設定するために最も適した metric は何ですか?

A. CPU utilization
B. Memory utilization
C. GPU utilization
D. Custom metrics based on workload characteristics

<details>
<summary>解答を表示</summary>

**解答: D. Custom metrics based on workload characteristics**

**解説:**
Kubernetes で AI/ML workloads の auto-scaling を設定するために最も適した metric は、workload characteristics に基づく custom metrics です。AI/ML workloads は、CPU、memory、GPU utilization だけでなく、request latency、queue length、batch size などのさまざまな要因に基づいて scaling が必要になる場合があります。workload characteristics を最もよく反映する metrics を選択することが重要です。

**AI/ML workloads の auto-scaling metrics の種類:**
1. **Resource-based metrics**:
   - CPU utilization
   - Memory utilization
   - GPU utilization

2. **Custom metrics**:
   - Request latency
   - Request throughput
   - Queue length
   - Batch size
   - Model accuracy
   - Inference time

3. **External metrics**:
   - Message queue length (Kafka、RabbitMQ など)
   - Database query latency
   - API gateway request count

**AI/ML workload type ごとの推奨 metrics:**
1. **Model inference service**:
   - Request latency
   - Requests per second (RPS)
   - Queued requests の数

2. **Batch processing jobs**:
   - Job queue length
   - 処理待ちデータ量
   - Job completion time

3. **Streaming processing**:
   - Stream processing latency
   - Event processing rate
   - Unprocessed events の数

**Horizontal Pod Autoscaler (HPA) の例:**
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

**Custom metric collection and exposure:**
1. **Prometheus Adapter**: Prometheus によって収集された metrics を Kubernetes API に公開します
2. **Custom Metrics API**: custom metrics を Kubernetes API に公開します
3. **External Metrics API**: external system metrics を Kubernetes API に公開します

**Prometheus Adapter configuration の例:**
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

**KEDA (Kubernetes Event-driven Autoscaling) の例:**
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

**GPU utilization-based scaling:**
GPU utilization-based scaling は NVIDIA DCGM Exporter のような tools を使用して実装できます。

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

**Auto-scaling strategy を選択するときの考慮事項:**
1. **Workload characteristics**: Batch processing、real-time inference、streaming processing など
2. **Performance requirements**: Latency、throughput、accuracy など
3. **Resource efficiency**: Cost optimization、resource utilization など
4. **Scalability**: load variations に対応できる能力
5. **Stability**: rapid scaling による service disruption の防止

**他の選択肢の問題点:**
- A. CPU utilization: AI/ML workloads は GPU-bound または memory-bound であることが多いため、CPU utilization だけでは適切な scaling decisions につながらない可能性があります。
- B. Memory utilization: Memory utilization は通常 workload increase に比例して増加せず、特に model loading 後は比較的一定のままです。
- C. GPU utilization: GPU utilization は重要な metric ですが、すべての AI/ML workloads が GPU を使用するわけではなく、使用する場合でも GPU utilization だけでは service quality を完全には反映できない場合があります。
</details>
### 7. Kubernetes で AI/ML workloads の networking を設定するときに最も重要な考慮事項は何ですか?

A. Network policy configuration
B. Service mesh implementation
C. High-performance networking and topology awareness for distributed training
D. External accessibility configuration

<details>
<summary>解答を表示</summary>

**解答: C. High-performance networking and topology awareness for distributed training**

**解説:**
Kubernetes で AI/ML workloads の networking を設定するときに最も重要な考慮事項は、distributed training のための high-performance networking と topology awareness です。Distributed AI/ML workloads は Nodes 間で大量のデータと model parameters を交換する必要があるため、network performance は全体的な training と inference performance に大きな影響を与えます。network topology を認識して近接 Nodes 間の communication を確保することは、latency を最小化するうえで重要です。

**Distributed AI/ML workloads の network requirements:**
1. **High bandwidth**: 大量のデータと model parameters を交換するための高い network bandwidth
2. **Low latency**: Nodes 間の高速 communication のための低い network latency
3. **RDMA (Remote Direct Memory Access) support**: memory 間の direct data transfer により CPU overhead を削減します
4. **Topology awareness**: network topology を考慮した Pod placement
5. **GPU direct communication**: NVIDIA GPUDirect RDMA のような direct GPU-to-GPU communication の technology support

**High-performance networking configuration の例:**
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

**Network topology awareness configuration:**
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

**High-performance network interface configuration:**
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

**RDMA support configuration:**
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

**NVIDIA GPUDirect RDMA configuration:**
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

**Network performance optimization strategies:**
1. **Node placement optimization**: 関連する Pods を同じ rack または近接 Nodes に配置します
2. **Network interface optimization**: SR-IOV、DPDK のような technologies を使用して network performance を向上させます
3. **Network topology awareness**: network topology を考慮した Pod placement のために topology spread constraints を使用します
4. **Dedicated network use**: AI/ML workloads のために dedicated network interfaces を設定します
5. **MTU optimization**: large packet transmission のための MTU (Maximum Transmission Unit) optimization

**Network performance testing:**
```bash
# Network performance test using iperf3
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201

kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**他の選択肢の問題点:**
- A. Network policy configuration: security には重要ですが、AI/ML workload performance には直接影響しません。
- B. Service mesh implementation: microservices architecture には有用ですが、AI/ML workloads の high-performance networking requirements は満たしません。
- D. External accessibility configuration: model serving には重要ですが、distributed training performance には直接影響しません。
</details>

### 8. Kubernetes で AI/ML workloads の security を設定するときに最も重要な考慮事項は何ですか?

A. Network policy configuration
B. Access control and encryption for models and data
C. Container image scanning
D. Pod security policy configuration

<details>
<summary>解答を表示</summary>

**解答: B. Access control and encryption for models and data**

**解説:**
Kubernetes で AI/ML workloads の security を設定するときに最も重要な考慮事項は、models と data の access control と encryption です。AI/ML workloads は sensitive data や intellectual property models を扱うことが多いため、これらの assets を保護することが最も重要です。Data leaks や model theft は、business と regulatory の面で深刻な影響を及ぼす可能性があります。

**AI/ML workloads の主な security risks:**
1. **Data leakage**: training data、inference data などの sensitive information の漏えい
2. **Model theft**: intellectual property である model files の盗難
3. **Model poisoning**: adversarial attacks による model performance の低下または bias injection
4. **Inference manipulation**: input data manipulation によって誤った predictions を誘導すること
5. **Privilege escalation**: excessive privileges を通じた system access

**Model と data security の主な strategies:**
1. **Access control**:
   - RBAC (Role-Based Access Control) による fine-grained permission management
   - principle of least privilege の適用
   - Service account separation

2. **Encryption**:
   - Encryption at Rest
   - Encryption in Transit
   - Model file encryption

3. **Secret management**:
   - Kubernetes Secrets または external secret management systems の使用
   - API keys、authentication tokens などの secure management

4. **Container security**:
   - 最小権限で containers を実行
   - read-only file system の使用
   - non-root user として実行

**RBAC configuration の例:**
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

**Encrypted model storage の例:**
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

**External secret management system integration の例 (HashiCorp Vault):**
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

**Data encryption configuration の例:**
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

**Container security hardening の例:**
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

**Network policy の例:**
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

**Model と data security の追加 strategies:**
1. **Model signing and verification**: model files に digital signatures を適用し、使用前に検証します
2. **Model version management**: model versions と changes を追跡します
3. **Audit logging**: model と data access の audit logs を保持します
4. **Data masking**: sensitive data fields をマスクします
5. **Differential privacy**: personal information protection のために differential privacy techniques を適用します

**他の選択肢の問題点:**
- A. Network policy configuration: 重要ですが、それ自体では model と data security を直接保証しません。
- C. Container image scanning: vulnerability management には重要ですが、model と data security に直接対応するものではありません。
- D. Pod security policy configuration: container execution environment の security を強化しますが、それ自体では model と data security を直接保証しません。
</details>
### 9. Kubernetes で AI/ML workloads の logging and monitoring configuration において最も重要な metric は何ですか?

A. Pod and node status
B. Model performance metrics (accuracy, latency, etc.) and resource usage
C. API call count
D. Network traffic

<details>
<summary>解答を表示</summary>

**解答: B. Model performance metrics (accuracy, latency, etc.) and resource usage**

**解説:**
Kubernetes で AI/ML workloads の logging and monitoring configuration において最も重要な metrics は、model performance metrics（accuracy、latency など）と resource usage です。これらの metrics は model quality、SLO (Service Level Objective) compliance、resource efficiency を直接反映し、model performance degradation や resource bottlenecks を早期に検出するのに役立ちます。

**主な monitoring metrics:**

1. **Model performance metrics**:
   - **Accuracy**: model predictions の正確性
   - **Precision**: positive と予測されたもののうち、実際に positive である割合
   - **Recall**: 実際の positives のうち、positive と予測された割合
   - **F1 Score**: precision と recall の harmonic mean
   - **AUC-ROC**: binary classification models の performance measurement
   - **Mean Squared Error (MSE)**: regression models の error measurement

2. **Service level metrics**:
   - **Latency**: request から response までの時間
   - **Throughput**: 単位時間あたりに処理される requests 数
   - **Error Rate**: failed requests の割合
   - **Availability**: service が正常に応答した時間の割合

3. **Resource usage**:
   - **CPU utilization**: containers と nodes の CPU utilization
   - **Memory utilization**: containers と nodes の memory utilization
   - **GPU utilization**: GPU computation と memory utilization
   - **Disk I/O**: storage read/write performance
   - **Network I/O**: network send/receive performance

**Monitoring stack configuration の例:**
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

**Custom metric exposure の例 (Python):**
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

**Grafana dashboard configuration の例:**
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

**Logging configuration の例:**
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

**Model performance monitoring のための追加 tools:**
1. **MLflow**: experiment tracking、model version management、model registry
2. **TensorBoard**: TensorFlow model training process と performance visualization
3. **Weights & Biases**: experiment tracking、model performance comparison、hyperparameter optimization
4. **Seldon Core Metrics**: Seldon Core が提供する model serving metrics
5. **KServe Metrics**: KServe が提供する model serving metrics

**Monitoring alert configuration の例:**
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

**他の選択肢の問題点:**
- A. Pod and node status: basic system status monitoring には重要ですが、AI/ML workload performance と quality を直接反映しません。
- C. API call count: system usage の測定には有用ですが、model performance や resource efficiency を直接示すものではありません。
- D. Network traffic: distributed training や large-scale data transfers には重要ですが、model performance や quality を直接反映しません。
</details>

### 10. Kubernetes で AI/ML workloads の最も効果的な cost optimization strategy は何ですか?

A. 常に最新の instance types を使用する
B. すべての workloads に Spot instances を使用する
C. Workload characteristics に基づく適切な instance type selection と auto-scaling
D. すべての resources の requests と limits を最小化する

<details>
<summary>解答を表示</summary>

**解答: C. Workload characteristics に基づく適切な instance type selection と auto-scaling**

**解説:**
Kubernetes で AI/ML workloads の最も効果的な cost optimization strategy は、workload characteristics に基づく適切な instance type selection と auto-scaling です。AI/ML workloads は training、inference、data preprocessing などのさまざまな段階で異なる resource requirements を持ち、各 workload の characteristics に合った instance types を選択し、必要に応じて auto-scaling することが cost efficiency の最適化に重要です。

**Workload characteristics ごとの instance type selection:**

1. **Model training**:
   - **GPU instances**: deep learning model training に適しています
   - **Memory-optimized instances**: large-scale dataset processing に適しています
   - **Compute-optimized instances**: compute-intensive algorithms に適しています

2. **Model inference**:
   - **GPU instances**: complex models または real-time inference に適しています
   - **CPU instances**: simple models または batch inference に適しています
   - **Inference-optimized instances (AWS Inferentia、Google TPU など)**: inference に特化した specialized instances

3. **Data preprocessing**:
   - **Compute-optimized instances**: parallel processing に適しています
   - **Memory-optimized instances**: large-scale dataset processing に適しています
   - **Storage-optimized instances**: I/O-intensive jobs に適しています

**Node group configuration の例:**
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

**Workload placement の例:**
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

**Auto-scaling configuration の例:**
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

**Cost optimization strategies:**

1. **Appropriate instance type selection**:
   - workload characteristics に合った instance types を選択します
   - cost vs performance analysis により optimal instances を選択します
   - specialized instances（GPU、TPU など）を活用します

2. **Spot instance utilization**:
   - fault-tolerant workloads に Spot instances を使用します
   - さまざまな instance types を指定して availability を向上させます
   - interruption tolerance strategies を実装します

3. **Auto-scaling**:
   - Cluster Autoscaler により Node count を自動的に調整します
   - HPA により Pod count を自動的に調整します
   - Custom metric-based scaling

4. **Resource request and limit optimization**:
   - actual usage に基づいて resource requests を設定します
   - Vertical Pod Autoscaler により resource requests を自動的に調整します
   - Resource usage monitoring and optimization

5. **Job schedule optimization**:
   - より低コストな時間帯に batch jobs を実行します
   - lower priority jobs を low-cost resources に配置します
   - Job queue and priority settings

**Cost monitoring and optimization tools:**
1. **Kubecost**: Kubernetes clusters の cost monitoring and optimization
2. **AWS Cost Explorer**: AWS resource cost analysis
3. **Google Cloud Cost Management**: GCP resource cost analysis
4. **Azure Cost Management**: Azure resource cost analysis
5. **Prometheus + Grafana**: Custom cost dashboard configuration

**他の選択肢の問題点:**
- A. 常に最新の instance types を使用する: 最新の instances が常に最も cost-effective であるとは限らず、workload characteristics に合った instances を選択することの方が重要です。
- B. すべての workloads に Spot instances を使用する: Spot instances は中断される可能性があるため、中断に敏感な critical workloads には適していません。
- D. すべての resources の requests と limits を最小化する: resource requests を過度に最小化すると performance issues を引き起こす可能性があり、workload characteristics に合った適切な resource allocation が重要です。
</details>
