# AI/ML Workloads

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 23, 2026

Kubernetes is a powerful platform for running AI/ML workloads. In this chapter, we will learn how to run AI/ML workloads on EKS and explore best practices.

## Characteristics of AI/ML Workloads

AI/ML workloads have different characteristics compared to typical application workloads:

```mermaid
flowchart TD
    subgraph AIML [AI/ML Workload Characteristics]
        Resource[Resource Intensive]
        Data[Data Intensive]
        Distributed[Distributed Processing]
        Diversity[Workload Diversity]
        Processing[Batch and Real-time Processing]
    end

    subgraph ResourceDetails [Resource Requirements]
        GPU[GPU Acceleration]
        Memory[Large Memory]
        CPU[High-Performance CPU]
        Network[High-Speed Network]
    end

    subgraph WorkloadTypes [Workload Types]
        Training[Model Training]
        Inference[Model Inference]
        DataPrep[Data Preprocessing]
        HPO[Hyperparameter Optimization]
    end

    Resource --> ResourceDetails
    Diversity --> WorkloadTypes

    classDef aimlFeature fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef resourceDetail fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef workloadType fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Resource,Data,Distributed,Diversity,Processing aimlFeature;
    class GPU,Memory,CPU,Network resourceDetail;
    class Training,Inference,DataPrep,HPO workloadType;
    class AIML,ResourceDetails,WorkloadTypes default;
```

1. **Resource Intensive**: Requires significant computing resources including GPUs, high-performance CPUs, and large memory.
2. **Data Intensive**: Requires fast access to large datasets.
3. **Distributed Processing**: Requires distributed processing across multiple nodes for large-scale model training.
4. **Workload Diversity**: Includes various types of workloads such as training, inference, and data preprocessing.

## Latest AI/ML Trends (2025)

The latest trends for running AI/ML workloads on Kubernetes include:

### 1. Large Language Model (LLM) Deployment

Large Language Models (LLMs) are one of the most prominent technologies in AI recently. Key considerations for efficiently deploying LLMs on Kubernetes:

- **Model Sharding**: Distributing large models across multiple GPUs
- **Quantization**: Reducing memory usage by lowering model precision (INT8, FP16, etc.)
- **Inference Optimization**: Improving inference performance using vLLM, TensorRT, ONNX Runtime, etc.
- **Scaling Strategy**: Increasing throughput through horizontal scaling

### 2. AI Orchestration Frameworks

Specialized orchestration frameworks for managing AI/ML workloads on Kubernetes:

- **Kubeflow**: Comprehensive platform for machine learning workflows
- **Ray on Kubernetes**: Distributed computing framework
- **KServe**: Serverless inference service
- **Seldon Core**: Model serving and monitoring

### 3. GPU Sharing and Optimization

Technologies for efficiently utilizing GPU resources:

- **MIG (Multi-Instance GPU)**: Partitioning of NVIDIA A100/H100 GPUs
- **Time-Sharing Scheduling**: NVIDIA MPS, GPU time slicing
- **Dynamic Allocation**: Dynamic allocation of GPU resources as needed
- **GPU Operator**: Automating GPU management in Kubernetes

### 4. MLOps and GitOps Integration

Applying DevOps principles for AI/ML lifecycle management:

- **Model Version Control**: Model versioning integrated with Git
- **CI/CD Pipelines**: Automating model training and deployment
- **A/B Testing**: Gradual rollout of new model versions
- **Monitoring and Feedback Loops**: Model performance monitoring and retraining

### 5. Vector Database Integration

Vector database integration for embeddings and semantic search:

- **Pinecone**: Managed vector search
- **Milvus**: Open-source vector database
- **Faiss**: Facebook AI's efficient similarity search library
- **OpenSearch**: Search engine with vector search capabilities
5. **Batch and Real-time Processing**: Both batch processing and real-time inference are required.

## AI/ML Infrastructure Configuration in EKS

```mermaid
flowchart TD
    subgraph AWS [AWS Cloud]
        subgraph EKS [Amazon EKS]
            subgraph NodeGroups [Node Groups]
                subgraph Training [Training Node Group]
                    P4d[p4d.24xlarge]
                    P3[p3.16xlarge]
                    G5[g5.48xlarge]
                end

                subgraph Inference [Inference Node Group]
                    G4dn[g4dn.xlarge]
                    Inf1[inf1.24xlarge]
                    Trn1[trn1.32xlarge]
                end

                subgraph CPU [CPU Node Group]
                    C6i[c6i.32xlarge]
                    R6i[r6i.32xlarge]
                end
            end

            subgraph Storage [Storage]
                EBS[Amazon EBS]
                EFS[Amazon EFS]
                FSx[FSx for Lustre]
                S3[Amazon S3]
            end

            subgraph Networking [Networking]
                VPC[VPC CNI]
                ENA[ENA/EFA]
                PlacementGroup[Placement Group]
            end
        end

        subgraph Services [AWS Services]
            SageMaker[Amazon SageMaker]
            ECR[Amazon ECR]
            CloudWatch[CloudWatch]
        end
    end

    Training --> Storage
    Inference --> Storage
    CPU --> Storage

    Training --> Networking
    Inference --> Networking
    CPU --> Networking

    EKS --> Services

    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef trainingNode fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef inferenceNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef cpuNode fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class SageMaker,ECR,CloudWatch,EBS,EFS,FSx,S3 awsService;
    class EKS,NodeGroups,Storage,Networking,VPC,ENA,PlacementGroup k8sComponent;
    class P4d,P3,G5,Training trainingNode;
    class G4dn,Inf1,Trn1,Inference inferenceNode;
    class C6i,R6i,CPU cpuNode;
    class AWS,Services default;
```

### Node Type Selection

EC2 instance types suitable for AI/ML workloads include:

1. **GPU Instances**:
   - p4d.24xlarge: 8x NVIDIA A100 GPU, 320GB GPU memory
   - p3.16xlarge: 8x NVIDIA V100 GPU, 128GB GPU memory
   - g5.xlarge~g5.48xlarge: NVIDIA A10G GPU, up to 8 GPUs
   - g4dn.xlarge~g4dn.16xlarge: NVIDIA T4 GPU, up to 4 GPUs

2. **CPU Optimized Instances**:
   - c6i.32xlarge: 128 vCPU, 256GB memory
   - c7g.16xlarge: 64 vCPU (AWS Graviton3), 128GB memory

3. **Memory Optimized Instances**:
   - r6i.32xlarge: 128 vCPU, 1024GB memory
   - x2gd.16xlarge: 64 vCPU, 1024GB memory

4. **Inferentia Instances**:
   - inf1.24xlarge: 16 AWS Inferentia chips, 96 vCPU, 192GB memory

5. **Trainium Instances**:
   - trn1.32xlarge: 16 AWS Trainium chips, 128 vCPU, 512GB memory

### Storage Configuration

AI/ML workloads require high-performance storage:

1. **Amazon EBS**:
   - gp3: Default general-purpose SSD storage
   - io2: High-performance SSD storage
   - st1: Throughput-optimized HDD storage

2. **Amazon EFS**:
   - Useful when multiple nodes need access to shared data
   - Performance mode: General purpose or Max I/O
   - Throughput mode: Bursting or Provisioned throughput

3. **Amazon FSx for Lustre**:
   - High-performance parallel file system
   - Provides fast access to large datasets
   - Simplifies data import and export through S3 integration

4. **Amazon S3**:
   - Stores large datasets
   - Stores training data and model artifacts

### Networking Configuration

Networking configuration for distributed training:

1. **Cluster Placement Groups**:
   - Minimizes latency between nodes
   - Places nodes within the same availability zone

2. **Enhanced Networking**:
   - Elastic Network Adapter (ENA)
   - ENA Express
   - Elastic Fabric Adapter (EFA)

3. **VPC CNI Configuration**:
   - IP address management for large-scale pod deployments
   - Secondary IP address range configuration

## AI/ML Workload Deployment

```mermaid
flowchart TD
    subgraph EKS [Amazon EKS]
        subgraph Components [Key Components]
            NVIDIA[NVIDIA GPU Operator]
            Kubeflow[Kubeflow]
            MPIOperator[MPI Operator]
            KServe[KServe]
        end

        subgraph GPUOperator [NVIDIA GPU Operator]
            Driver[NVIDIA Driver]
            Toolkit[NVIDIA Container Toolkit]
            DevicePlugin[NVIDIA Device Plugin]
            DCGM[NVIDIA DCGM Exporter]
        end

        subgraph KubeflowComponents [Kubeflow Components]
            Notebooks[Jupyter Notebooks]
            Training[TF/PyTorch Training Jobs]
            Serving[KFServing]
            Pipelines[Pipelines]
            Katib[Katib]
        end

        subgraph ModelServing [Model Serving Options]
            KServeComponent[KServe]
            TorchServe[TorchServe]
            Triton[Triton Inference Server]
        end
    end

    NVIDIA --> GPUOperator
    Kubeflow --> KubeflowComponents
    KServe --> ModelServing

    classDef eksComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef nvidiaComponent fill:#76B900,stroke:#333,stroke-width:1px,color:white;
    classDef kubeflowComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef servingComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class EKS,Components eksComponent;
    class NVIDIA,Driver,Toolkit,DevicePlugin,DCGM,GPUOperator nvidiaComponent;
    class Kubeflow,Notebooks,Training,Serving,Pipelines,Katib,KubeflowComponents kubeflowComponent;
    class KServe,KServeComponent,TorchServe,Triton,ModelServing servingComponent;
```

### NVIDIA GPU Operator

NVIDIA GPU Operator is a tool for managing NVIDIA GPUs in Kubernetes clusters:

```bash
# Installation using Helm
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

helm install --wait --generate-name \
  -n gpu-operator --create-namespace \
  nvidia/gpu-operator
```

The GPU Operator deploys the following components:

1. **NVIDIA Driver**: Automatic GPU driver installation
2. **NVIDIA Container Toolkit**: Enables GPU usage in containers
3. **NVIDIA Device Plugin**: Exposes GPU resources to Kubernetes
4. **NVIDIA DCGM Exporter**: Provides GPU monitoring metrics

### Kubeflow

Kubeflow is a platform for running ML workflows on Kubernetes:

```bash
# Kubeflow installation
kustomize build https://github.com/kubeflow/manifests/tree/master/example | kubectl apply -f -
```

Kubeflow provides the following components:

1. **Jupyter Notebooks**: Interactive development environment
2. **TensorFlow/PyTorch Training Jobs**: Running distributed training jobs
3. **KFServing**: Model serving
4. **Pipelines**: End-to-end ML workflows
5. **Katib**: Hyperparameter tuning

### Distributed Training

Kubernetes resources for distributed training:

```mermaid
flowchart TD
    subgraph DistributedTraining [Distributed Training Architecture]
        subgraph MPIJob [MPI Job]
            Launcher[Launcher Pod]
            Worker1[Worker Pod 1]
            Worker2[Worker Pod 2]
            Worker3[Worker Pod 3]
            Worker4[Worker Pod 4]
        end

        subgraph Communication [Communication Layer]
            NCCL[NVIDIA NCCL]
            MPI[MPI]
            EFA[Elastic Fabric Adapter]
        end

        subgraph Storage [Shared Storage]
            FSxLustre[FSx for Lustre]
            S3[Amazon S3]
            Checkpoints[Checkpoint Storage]
        end
    end

    Launcher --> Worker1
    Launcher --> Worker2
    Launcher --> Worker3
    Launcher --> Worker4

    Worker1 <--> NCCL
    Worker2 <--> NCCL
    Worker3 <--> NCCL
    Worker4 <--> NCCL

    NCCL --> MPI
    MPI --> EFA

    Worker1 --> FSxLustre
    Worker2 --> FSxLustre
    Worker3 --> FSxLustre
    Worker4 --> FSxLustre

    FSxLustre --> S3
    FSxLustre --> Checkpoints

    classDef podComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef communicationComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef storageComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Launcher,Worker1,Worker2,Worker3,Worker4,MPIJob podComponent;
    class NCCL,MPI,EFA,Communication communicationComponent;
    class FSxLustre,S3,Checkpoints,Storage storageComponent;
    class DistributedTraining default;
```

1. **MPI Operator**:

```yaml
apiVersion: kubeflow.org/v1
kind: MPIJob
metadata:
  name: tensorflow-benchmarks
spec:
  slotsPerWorker: 8
  cleanPodPolicy: Running
  mpiReplicaSpecs:
    Launcher:
      replicas: 1
      template:
        spec:
          containers:
          - image: mpioperator/tensorflow-benchmarks:latest
            name: tensorflow-benchmarks
            command:
            - mpirun
            - --allow-run-as-root
            - -np
            - "16"
            - -bind-to
            - none
            - -map-by
            - slot
            - -x
            - NCCL_DEBUG=INFO
            - python
            - scripts/tf_cnn_benchmarks/tf_cnn_benchmarks.py
            - --model=resnet50
            - --batch_size=64
            - --variable_update=horovod
    Worker:
      replicas: 2
      template:
        spec:
          containers:
          - image: mpioperator/tensorflow-benchmarks:latest
            name: tensorflow-benchmarks
            resources:
              limits:
                nvidia.com/gpu: 8
```

2. **PyTorch Elastic**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pytorch-elastic-job
spec:
  completions: 1
  parallelism: 1
  template:
    spec:
      containers:
      - name: pytorch-elastic
        image: pytorch/pytorch:1.9.0-cuda10.2-cudnn7-runtime
        command:
        - torchrun
        - --nnodes=2
        - --nproc_per_node=8
        - --rdzv_id=job1
        - --rdzv_backend=c10d
        - --rdzv_endpoint=$(MASTER_ADDR):$(MASTER_PORT)
        - train.py
        env:
        - name: MASTER_ADDR
          value: pytorch-elastic-job-0
        - name: MASTER_PORT
          value: "29500"
        resources:
          limits:
            nvidia.com/gpu: 8
      restartPolicy: Never
```

### Model Serving

Options for model serving:

```mermaid
flowchart TD
    subgraph ModelServing [Model Serving Architecture]
        subgraph InferenceServices [Inference Services]
            KServe[KServe]
            TorchServe[TorchServe]
            Triton[Triton Inference Server]
        end

        subgraph ScalingOptions [Scaling Options]
            HPA[HorizontalPodAutoscaler]
            KEDA[KEDA]
            VPA[VerticalPodAutoscaler]
        end

        subgraph NetworkingOptions [Networking Options]
            Ingress[Ingress]
            ALB[AWS ALB]
            APIGateway[API Gateway]
        end

        subgraph ModelStorage [Model Storage]
            S3[Amazon S3]
            ECR[Amazon ECR]
            EFS[Amazon EFS]
        end
    end

    Client([Client]) --> NetworkingOptions
    NetworkingOptions --> InferenceServices
    InferenceServices --> ModelStorage
    ScalingOptions --> InferenceServices

    classDef serviceComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef scalingComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef networkingComponent fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef storageComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class KServe,TorchServe,Triton,InferenceServices serviceComponent;
    class HPA,KEDA,VPA,ScalingOptions scalingComponent;
    class Ingress,ALB,APIGateway,NetworkingOptions networkingComponent;
    class S3,ECR,EFS,ModelStorage storageComponent;
    class ModelServing,Client default;
```

1. **KServe**:

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: bert-model
spec:
  predictor:
    model:
      modelFormat:
        name: pytorch
      storageUri: s3://my-bucket/bert-model
      resources:
        limits:
          nvidia.com/gpu: 1
```

2. **TorchServe**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: torchserve
spec:
  replicas: 3
  selector:
    matchLabels:
      app: torchserve
  template:
    metadata:
      labels:
        app: torchserve
    spec:
      containers:
      - name: torchserve
        image: pytorch/torchserve:latest
        ports:
        - containerPort: 8080
        - containerPort: 8081
        volumeMounts:
        - name: model-store
          mountPath: /home/model-server/model-store
        resources:
          limits:
            nvidia.com/gpu: 1
      volumes:
      - name: model-store
        persistentVolumeClaim:
          claimName: model-store-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: torchserve
spec:
  selector:
    app: torchserve
  ports:
  - port: 8080
    targetPort: 8080
    name: inference
  - port: 8081
    targetPort: 8081
    name: management
  type: LoadBalancer
```

3. **Triton Inference Server**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: triton-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: triton-server
  template:
    metadata:
      labels:
        app: triton-server
    spec:
      containers:
      - name: triton-server
        image: nvcr.io/nvidia/tritonserver:21.08-py3
        command:
        - tritonserver
        - --model-repository=/models
        ports:
        - containerPort: 8000
        - containerPort: 8001
        - containerPort: 8002
        volumeMounts:
        - name: model-repository
          mountPath: /models
        resources:
          limits:
            nvidia.com/gpu: 1
      volumes:
      - name: model-repository
        persistentVolumeClaim:
          claimName: model-repository-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: triton-server
spec:
  selector:
    app: triton-server
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  - port: 8001
    targetPort: 8001
    name: grpc
  - port: 8002
    targetPort: 8002
    name: metrics
  type: LoadBalancer
```

## AI/ML Workload Optimization

```mermaid
flowchart TD
    subgraph Optimization [AI/ML Workload Optimization]
        subgraph GPUOptimization [GPU Optimization]
            MemoryOvercommit[GPU Memory Overcommit]
            GPUSharing[GPU Sharing]
            MPS[NVIDIA MPS]
        end

        subgraph TrainingOptimization [Training Optimization]
            NodeAffinity[Node Affinity]
            TopologyAware[Topology-Aware Scheduling]
            PlacementGroups[Placement Groups]
        end

        subgraph StorageOptimization [Storage Optimization]
            LustreConfig[FSx for Lustre Configuration]
            DataCaching[Data Caching]
            S3Integration[S3 Integration]
        end

        subgraph CostOptimization [Cost Optimization]
            SpotInstances[Spot Instances]
            AutoScaling[Auto Scaling]
            HybridNodes[Hybrid Nodes]
        end
    end

    GPUOptimization --> Performance([Performance Improvement])
    TrainingOptimization --> Performance
    StorageOptimization --> Performance
    CostOptimization --> CostReduction([Cost Reduction])

    classDef gpuOptComponent fill:#76B900,stroke:#333,stroke-width:1px,color:white;
    classDef trainingOptComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef storageOptComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef costOptComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef resultComponent fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class MemoryOvercommit,GPUSharing,MPS,GPUOptimization gpuOptComponent;
    class NodeAffinity,TopologyAware,PlacementGroups,TrainingOptimization trainingOptComponent;
    class LustreConfig,DataCaching,S3Integration,StorageOptimization storageOptComponent;
    class SpotInstances,AutoScaling,HybridNodes,CostOptimization costOptComponent;
    class Performance,CostReduction resultComponent;
    class Optimization default;
```

### GPU Memory Optimization

1. **GPU Memory Overcommit**:

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia-mps
handler: nvidia-container-runtime
---
apiVersion: v1
kind: Pod
metadata:
  name: cuda-mps
spec:
  runtimeClassName: nvidia-mps
  containers:
  - name: cuda-mps
    image: nvidia/cuda:11.6.0-base-ubuntu20.04
    command: ["nvidia-cuda-mps-control", "-d"]
    securityContext:
      privileged: true
    resources:
      limits:
        nvidia.com/gpu: 1
```

2. **GPU Sharing**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod-1
spec:
  containers:
  - name: gpu-container
    image: nvidia/cuda:11.6.0-base-ubuntu20.04
    resources:
      limits:
        nvidia.com/gpu: 0.5
```

### Distributed Training Optimization

1. **Node Affinity**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: node.kubernetes.io/instance-type
            operator: In
            values:
            - p3.16xlarge
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - gpu-intensive
        topologyKey: kubernetes.io/hostname
  containers:
  - name: gpu-container
    image: nvidia/cuda:11.6.0-base-ubuntu20.04
    resources:
      limits:
        nvidia.com/gpu: 8
```

2. **Topology-Aware Scheduling**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
  annotations:
    topology.kubernetes.io/region: us-west-2
    topology.kubernetes.io/zone: us-west-2a
spec:
  containers:
  - name: gpu-container
    image: nvidia/cuda:11.6.0-base-ubuntu20.04
    resources:
      limits:
        nvidia.com/gpu: 8
```

### Storage Optimization

1. **FSx for Lustre Configuration**:

```yaml
apiVersion: fsx.aws.k8s.io/v1beta1
kind: Lustre
metadata:
  name: lustre-fs
spec:
  deploymentType: SCRATCH_2
  storageCapacity: 1200
  subnetIds:
    - subnet-0123456789abcdef0
  securityGroupIds:
    - sg-0123456789abcdef0
  perUnitStorageThroughput: 200
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  fileSystemId: fs-0123456789abcdef0
  mountName: lustre-fs
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lustre-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi
```

2. **Data Caching**:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: alluxio-worker
spec:
  selector:
    matchLabels:
      app: alluxio-worker
  template:
    metadata:
      labels:
        app: alluxio-worker
    spec:
      containers:
      - name: alluxio-worker
        image: alluxio/alluxio:2.7.3
        resources:
          limits:
            memory: 8Gi
        volumeMounts:
        - name: alluxio-domain
          mountPath: /opt/domain
      volumes:
      - name: alluxio-domain
        hostPath:
          path: /mnt/alluxio
          type: DirectoryOrCreate
```

## Monitoring and Logging

```mermaid
flowchart TD
    subgraph Monitoring [Monitoring and Logging Architecture]
        subgraph MetricsCollection [Metrics Collection]
            DCGMExporter[NVIDIA DCGM Exporter]
            NodeExporter[Node Exporter]
            KubeStateMetrics[Kube State Metrics]
        end

        subgraph MonitoringStack [Monitoring Stack]
            Prometheus[(Prometheus)]
            AlertManager[Alert Manager]
            Grafana[Grafana]
        end

        subgraph LoggingStack [Logging Stack]
            Fluentd[Fluentd]
            CloudWatch[CloudWatch Logs]
            ElasticSearch[(ElasticSearch)]
            Kibana[Kibana]
        end

        subgraph Dashboards [Dashboards]
            GPUDashboard[GPU Dashboard]
            TrainingDashboard[Training Dashboard]
            InferenceDashboard[Inference Dashboard]
            CostDashboard[Cost Dashboard]
        end

        subgraph Alerts [Alerts]
            GPUAlerts[GPU Alerts]
            PerformanceAlerts[Performance Alerts]
            CostAlerts[Cost Alerts]
        end
    end

    DCGMExporter --> Prometheus
    NodeExporter --> Prometheus
    KubeStateMetrics --> Prometheus

    Prometheus --> AlertManager
    Prometheus --> Grafana

    Fluentd --> CloudWatch
    Fluentd --> ElasticSearch
    ElasticSearch --> Kibana

    Grafana --> Dashboards
    AlertManager --> Alerts

    classDef metricsComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef monitoringComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef loggingComponent fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef dashboardComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef alertComponent fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class DCGMExporter,NodeExporter,KubeStateMetrics,MetricsCollection metricsComponent;
    class Prometheus,AlertManager,Grafana,MonitoringStack monitoringComponent;
    class Fluentd,CloudWatch,ElasticSearch,Kibana,LoggingStack loggingComponent;
    class GPUDashboard,TrainingDashboard,InferenceDashboard,CostDashboard,Dashboards dashboardComponent;
    class GPUAlerts,PerformanceAlerts,CostAlerts,Alerts alertComponent;
    class Monitoring default;
```

### Prometheus and Grafana

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: gpu-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: dcgm-exporter
  endpoints:
  - port: metrics
    interval: 15s
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  gpu-dashboard.json: |
    {
      "annotations": {
        "list": [
          {
            "builtIn": 1,
            "datasource": "-- Grafana --",
            "enable": true,
            "hide": true,
            "iconColor": "rgba(0, 211, 255, 1)",
            "name": "Annotations & Alerts",
            "type": "dashboard"
          }
        ]
      },
      "editable": true,
      "gnetId": null,
      "graphTooltip": 0,
      "id": 1,
      "links": [],
      "panels": [
        {
          "aliasColors": {},
          "bars": false,
          "dashLength": 10,
          "dashes": false,
          "datasource": null,
          "fieldConfig": {
            "defaults": {
              "custom": {}
            },
            "overrides": []
          },
          "fill": 1,
          "fillGradient": 0,
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "hiddenSeries": false,
          "id": 2,
          "legend": {
            "avg": false,
            "current": false,
            "max": false,
            "min": false,
            "show": true,
            "total": false,
            "values": false
          },
          "lines": true,
          "linewidth": 1,
          "nullPointMode": "null",
          "options": {
            "alertThreshold": true
          },
          "percentage": false,
          "pluginVersion": "7.2.0",
          "pointradius": 2,
          "points": false,
          "renderer": "flot",
          "seriesOverrides": [],
          "spaceLength": 10,
          "stack": false,
          "steppedLine": false,
          "targets": [
            {
              "expr": "DCGM_FI_DEV_GPU_UTIL",
              "interval": "",
              "legendFormat": "GPU {{gpu}}",
              "refId": "A"
            }
          ],
          "thresholds": [],
          "timeFrom": null,
          "timeRegions": [],
          "timeShift": null,
          "title": "GPU Utilization",
          "tooltip": {
            "shared": true,
            "sort": 0,
            "value_type": "individual"
          },
          "type": "graph",
          "xaxis": {
            "buckets": null,
            "mode": "time",
            "name": null,
            "show": true,
            "values": []
          },
          "yaxes": [
            {
              "format": "percent",
              "label": null,
              "logBase": 1,
              "max": null,
              "min": null,
              "show": true
            },
            {
              "format": "short",
              "label": null,
              "logBase": 1,
              "max": null,
              "min": null,
              "show": true
            }
          ],
          "yaxis": {
            "align": false,
            "alignLevel": null
          }
        }
      ],
      "schemaVersion": 26,
      "style": "dark",
      "tags": [],
      "templating": {
        "list": []
      },
      "time": {
        "from": "now-6h",
        "to": "now"
      },
      "timepicker": {},
      "timezone": "",
      "title": "GPU Dashboard",
      "uid": "gpu-dashboard",
      "version": 1
    }
```

### Log Collection

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: logging
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
      @id filter_kube_metadata
    </filter>

    <match kubernetes.var.log.containers.**>
      @type cloudwatch_logs
      log_group_name /eks/ml-cluster/pods
      log_stream_name_key $.kubernetes.pod_name
      remove_log_stream_name_key true
      auto_create_stream true
      region us-west-2
    </match>
```

## Cost Optimization

### Utilizing Spot Instances

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-spot
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g4dn.xlarge
        - g4dn.2xlarge
        - g4dn.4xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      nodeClassRef:
        name: gpu-spot-class
  limits:
    nvidia.com/gpu: 10
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-spot-class
spec:
  subnetSelector:
    karpenter.sh/discovery: gpu-cluster
  securityGroupSelector:
    karpenter.sh/discovery: gpu-cluster
```

### Auto Scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-service
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
  - type: Resource
    resource:
      name: nvidia.com/gpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: inference_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

### Utilizing Hybrid Nodes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: training-pod
spec:
  nodeSelector:
    node.kubernetes.io/instance-type: p3.16xlarge
  containers:
  - name: training-container
    image: tensorflow/tensorflow:latest-gpu
    resources:
      limits:
        nvidia.com/gpu: 8
---
apiVersion: v1
kind: Pod
metadata:
  name: inference-pod
spec:
  nodeSelector:
    node.kubernetes.io/instance-type: g4dn.xlarge
  containers:
  - name: inference-container
    image: tensorflow/tensorflow:latest-gpu
    resources:
      limits:
        nvidia.com/gpu: 1
```

## Conclusion

Running AI/ML workloads on EKS provides robust infrastructure, flexible scaling, and various optimization options. It is important to select appropriate node types, storage configurations, and networking settings, leverage tools like Kubeflow to manage ML workflows, and optimize GPU memory and distributed training. Additionally, you can track workload performance through monitoring and logging, and optimize costs by utilizing Spot instances and auto scaling.

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../quizzes/ai-ml/03-ai-ml-workloads-quiz.md).
