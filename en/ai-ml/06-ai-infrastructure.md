# AI Infrastructure on EKS

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 25, 2026

This guide covers comprehensive AI/ML infrastructure patterns on Amazon EKS, including the JARK Stack, Dynamic Resource Allocation (DRA), and production-ready platforms for AI agent development.

## AI/ML Infrastructure Architecture Overview

Modern AI/ML infrastructure on EKS follows a layered architecture that separates concerns and enables independent scaling of each layer.

![Layer stack showing the EKS AI/ML platform: ML workloads (training, inference, notebooks, pipelines, agents) run on platform services (Ray, KServe, Kubeflow, MLflow, Vector DB), which schedule onto GPU, Neuron, CPU, and Spot compute pools, all provisioned on the EKS base layer's control plane, storage, and networking.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-0.png)

**Layer responsibilities:**

| Layer | Components | Purpose |
|-------|------------|---------|
| **Workloads** | Training, Inference, Notebooks, Pipelines, Agents | User-facing ML applications |
| **Platform** | Ray, KServe, Kubeflow, MLflow, Vector DBs | ML-specific orchestration and tooling |
| **Compute** | GPU/Neuron/CPU NodePools, Spot instances | Hardware acceleration and cost optimization |
| **Base** | EKS, Karpenter, Storage, Networking | Foundation infrastructure |

---

## JARK Stack: Complete AI/ML Development Environment

The JARK Stack (JupyterHub + Argo Workflows + Ray + Karpenter) provides a complete, production-ready AI/ML development environment on EKS.

### JARK Stack Architecture

![Architecture diagram showing data scientists reaching JupyterHub notebooks that hand off to Argo Workflows and a Ray cluster for training and tuning, with Ray triggering Karpenter to provision GPU/Neuron nodes while JupyterHub and Ray both share EFS/FSx/S3 storage.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-1.png)

### JARK Stack Components

#### 1. JupyterHub - Interactive Development

JupyterHub provides a multi-user interactive development environment with GPU-enabled notebook profiles.

**JupyterHub Configuration with GPU Profiles:**

```yaml
# jupyterhub-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jupyterhub-config
  namespace: jupyterhub
data:
  jupyterhub_config.py: |
    c.JupyterHub.spawner_class = 'kubespawner.KubeSpawner'

    # Authentication with Amazon Cognito
    c.JupyterHub.authenticator_class = 'oauthenticator.generic.GenericOAuthenticator'
    c.GenericOAuthenticator.oauth_callback_url = 'https://jupyter.example.com/hub/oauth_callback'
    c.GenericOAuthenticator.client_id = 'your-cognito-client-id'
    c.GenericOAuthenticator.client_secret = 'your-cognito-client-secret'
    c.GenericOAuthenticator.authorize_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize'
    c.GenericOAuthenticator.token_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/token'
    c.GenericOAuthenticator.userdata_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/userInfo'

    # Notebook profile definitions
    c.KubeSpawner.profile_list = [
        {
            'display_name': 'CPU - Small (2 CPU, 4GB RAM)',
            'slug': 'cpu-small',
            'kubespawner_override': {
                'cpu_limit': 2,
                'cpu_guarantee': 1,
                'mem_limit': '4G',
                'mem_guarantee': '2G',
                'image': 'jupyter/scipy-notebook:latest',
            }
        },
        {
            'display_name': 'CPU - Large (8 CPU, 32GB RAM)',
            'slug': 'cpu-large',
            'kubespawner_override': {
                'cpu_limit': 8,
                'cpu_guarantee': 4,
                'mem_limit': '32G',
                'mem_guarantee': '16G',
                'image': 'jupyter/tensorflow-notebook:latest',
            }
        },
        {
            'display_name': 'GPU - T4 (4 CPU, 16GB RAM, 1x T4)',
            'slug': 'gpu-t4',
            'kubespawner_override': {
                'cpu_limit': 4,
                'cpu_guarantee': 2,
                'mem_limit': '16G',
                'mem_guarantee': '8G',
                'image': 'jupyter/tensorflow-notebook:gpu',
                'extra_resource_limits': {'nvidia.com/gpu': '1'},
                'extra_resource_guarantees': {'nvidia.com/gpu': '1'},
                'node_selector': {'nvidia.com/gpu.product': 'Tesla-T4'},
            }
        },
        {
            'display_name': 'GPU - A10G (8 CPU, 64GB RAM, 1x A10G)',
            'slug': 'gpu-a10g',
            'kubespawner_override': {
                'cpu_limit': 8,
                'cpu_guarantee': 4,
                'mem_limit': '64G',
                'mem_guarantee': '32G',
                'image': 'jupyter/tensorflow-notebook:gpu',
                'extra_resource_limits': {'nvidia.com/gpu': '1'},
                'extra_resource_guarantees': {'nvidia.com/gpu': '1'},
                'node_selector': {'nvidia.com/gpu.product': 'NVIDIA-A10G'},
            }
        },
        {
            'display_name': 'GPU - A100 (16 CPU, 128GB RAM, 1x A100 80GB)',
            'slug': 'gpu-a100',
            'kubespawner_override': {
                'cpu_limit': 16,
                'cpu_guarantee': 8,
                'mem_limit': '128G',
                'mem_guarantee': '64G',
                'image': 'jupyter/tensorflow-notebook:gpu',
                'extra_resource_limits': {'nvidia.com/gpu': '1'},
                'extra_resource_guarantees': {'nvidia.com/gpu': '1'},
                'node_selector': {'nvidia.com/gpu.product': 'NVIDIA-A100-SXM4-80GB'},
            }
        },
    ]

    # Persistent storage for notebooks
    c.KubeSpawner.storage_class = 'efs-sc'
    c.KubeSpawner.storage_pvc_ensure = True
    c.KubeSpawner.pvc_name_template = 'claim-{username}'
    c.KubeSpawner.storage_capacity = '50Gi'

    # Shared read-only datasets mount
    c.KubeSpawner.volumes = [
        {
            'name': 'shared-datasets',
            'persistentVolumeClaim': {'claimName': 'shared-datasets-pvc'}
        },
        {
            'name': 'shared-models',
            'persistentVolumeClaim': {'claimName': 'shared-models-pvc'}
        }
    ]
    c.KubeSpawner.volume_mounts = [
        {'name': 'shared-datasets', 'mountPath': '/home/jovyan/datasets', 'readOnly': True},
        {'name': 'shared-models', 'mountPath': '/home/jovyan/models', 'readOnly': False}
    ]
```

**JupyterHub Helm Installation:**

```bash
# Add JupyterHub Helm repository
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
helm repo update

# Create namespace
kubectl create namespace jupyterhub

# Install JupyterHub
helm upgrade --install jupyterhub jupyterhub/jupyterhub \
  --namespace jupyterhub \
  --version 3.2.1 \
  --values jupyterhub-values.yaml \
  --timeout 10m
```

#### 2. Argo Workflows - ML Pipeline Orchestration

Argo Workflows enables complex ML pipeline orchestration with DAG-based workflows.

**ML Training Pipeline Example:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: ml-training-pipeline-
  namespace: argo
spec:
  entrypoint: ml-pipeline
  serviceAccountName: argo-workflow

  # Artifact repository configuration
  artifactRepositoryRef:
    configMap: artifact-repositories
    key: default-v1

  # Workflow parameters
  arguments:
    parameters:
    - name: model-name
      value: "resnet50"
    - name: dataset-path
      value: "s3://ml-datasets/imagenet"
    - name: epochs
      value: "100"
    - name: batch-size
      value: "64"
    - name: learning-rate
      value: "0.001"

  templates:
  - name: ml-pipeline
    dag:
      tasks:
      # Data validation task
      - name: validate-data
        template: data-validation
        arguments:
          parameters:
          - name: dataset-path
            value: "{{workflow.parameters.dataset-path}}"

      # Data preprocessing task
      - name: preprocess-data
        template: data-preprocessing
        dependencies: [validate-data]
        arguments:
          parameters:
          - name: dataset-path
            value: "{{workflow.parameters.dataset-path}}"

      # Hyperparameter tuning with Ray Tune
      - name: hyperparameter-tuning
        template: ray-tune
        dependencies: [preprocess-data]
        arguments:
          parameters:
          - name: model-name
            value: "{{workflow.parameters.model-name}}"

      # Distributed training with Ray Train
      - name: distributed-training
        template: ray-train
        dependencies: [hyperparameter-tuning]
        arguments:
          parameters:
          - name: model-name
            value: "{{workflow.parameters.model-name}}"
          - name: epochs
            value: "{{workflow.parameters.epochs}}"
          - name: best-params
            value: "{{tasks.hyperparameter-tuning.outputs.parameters.best-params}}"

      # Model evaluation
      - name: evaluate-model
        template: model-evaluation
        dependencies: [distributed-training]
        arguments:
          artifacts:
          - name: model
            from: "{{tasks.distributed-training.outputs.artifacts.model}}"

      # Model registration
      - name: register-model
        template: model-registration
        dependencies: [evaluate-model]
        when: "{{tasks.evaluate-model.outputs.parameters.accuracy}} > 0.95"
        arguments:
          parameters:
          - name: accuracy
            value: "{{tasks.evaluate-model.outputs.parameters.accuracy}}"

  # Data validation template
  - name: data-validation
    inputs:
      parameters:
      - name: dataset-path
    container:
      image: python:3.11-slim
      command: [python]
      args:
      - -c
      - |
        import boto3
        # Validate dataset exists and has expected structure
        print(f"Validating dataset at {{inputs.parameters.dataset-path}}")
        # Add validation logic here
      resources:
        requests:
          cpu: "1"
          memory: "2Gi"

  # Data preprocessing template
  - name: data-preprocessing
    inputs:
      parameters:
      - name: dataset-path
    outputs:
      artifacts:
      - name: processed-data
        path: /tmp/processed
        s3:
          key: processed-data/{{workflow.name}}
    container:
      image: pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime
      command: [python]
      args:
      - /scripts/preprocess.py
      - --input={{inputs.parameters.dataset-path}}
      - --output=/tmp/processed
      resources:
        requests:
          cpu: "4"
          memory: "16Gi"
        limits:
          cpu: "8"
          memory: "32Gi"
      volumeMounts:
      - name: scripts
        mountPath: /scripts

  # Ray Tune hyperparameter optimization template
  - name: ray-tune
    inputs:
      parameters:
      - name: model-name
    outputs:
      parameters:
      - name: best-params
        valueFrom:
          path: /tmp/best_params.json
    container:
      image: rayproject/ray-ml:2.9.0-py310-gpu
      command: [python]
      args:
      - -c
      - |
        import ray
        from ray import tune
        from ray.tune.schedulers import ASHAScheduler
        import json

        ray.init()

        def train_func(config):
            # Training function for hyperparameter search
            accuracy = config["lr"] * 0.5 + config["batch_size"] * 0.001
            return {"accuracy": accuracy}

        scheduler = ASHAScheduler(max_t=100, grace_period=10)

        analysis = tune.run(
            train_func,
            config={
                "lr": tune.loguniform(1e-5, 1e-1),
                "batch_size": tune.choice([16, 32, 64, 128]),
                "hidden_size": tune.choice([64, 128, 256, 512]),
            },
            num_samples=50,
            scheduler=scheduler,
            resources_per_trial={"cpu": 2, "gpu": 0.5},
        )

        best_config = analysis.get_best_config(metric="accuracy", mode="max")
        with open("/tmp/best_params.json", "w") as f:
            json.dump(best_config, f)
      resources:
        requests:
          cpu: "4"
          memory: "16Gi"
          nvidia.com/gpu: "1"
        limits:
          nvidia.com/gpu: "1"

  # Ray Train distributed training template
  - name: ray-train
    inputs:
      parameters:
      - name: model-name
      - name: epochs
      - name: best-params
    outputs:
      artifacts:
      - name: model
        path: /tmp/model
    container:
      image: rayproject/ray-ml:2.9.0-py310-gpu
      command: [python]
      args:
      - -c
      - |
        import ray
        from ray.train.torch import TorchTrainer
        from ray.train import ScalingConfig
        import json

        ray.init()

        params = json.loads('{{inputs.parameters.best-params}}')

        def train_loop_per_worker():
            import torch
            from torch import nn
            # Distributed training logic
            pass

        trainer = TorchTrainer(
            train_loop_per_worker=train_loop_per_worker,
            scaling_config=ScalingConfig(
                num_workers=4,
                use_gpu=True,
                resources_per_worker={"CPU": 4, "GPU": 1}
            ),
        )

        result = trainer.fit()
        # Save model
      resources:
        requests:
          cpu: "8"
          memory: "32Gi"
          nvidia.com/gpu: "4"
        limits:
          nvidia.com/gpu: "4"
      nodeSelector:
        nvidia.com/gpu.product: NVIDIA-A100-SXM4-80GB
```

#### 3. Ray (KubeRay) - Distributed Computing

Ray provides unified distributed computing for ML workloads including training, tuning, and serving.

**RayCluster Configuration:**

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: ml-cluster
  namespace: ray-system
spec:
  rayVersion: '2.9.0'
  enableInTreeAutoscaling: true

  # Head node configuration
  headGroupSpec:
    serviceType: ClusterIP
    rayStartParams:
      dashboard-host: '0.0.0.0'
      block: 'true'
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
          env:
          - name: RAY_GRAFANA_HOST
            value: "http://grafana.monitoring:3000"
          - name: RAY_PROMETHEUS_HOST
            value: "http://prometheus.monitoring:9090"
          volumeMounts:
          - name: ray-logs
            mountPath: /tmp/ray
        volumes:
        - name: ray-logs
          emptyDir: {}
        nodeSelector:
          node-type: cpu

  # Worker group specifications
  workerGroupSpecs:
  # CPU workers for data processing
  - replicas: 2
    minReplicas: 1
    maxReplicas: 10
    groupName: cpu-workers
    rayStartParams:
      block: 'true'
    template:
      spec:
        containers:
        - name: ray-worker
          image: rayproject/ray-ml:2.9.0-py310
          resources:
            limits:
              cpu: "8"
              memory: "32Gi"
            requests:
              cpu: "4"
              memory: "16Gi"
          volumeMounts:
          - name: shared-data
            mountPath: /data
        volumes:
        - name: shared-data
          persistentVolumeClaim:
            claimName: ray-shared-data
        nodeSelector:
          node-type: cpu

  # GPU workers for training (g5 instances - A10G)
  - replicas: 2
    minReplicas: 0
    maxReplicas: 8
    groupName: gpu-a10g-workers
    rayStartParams:
      block: 'true'
      num-gpus: '1'
    template:
      spec:
        containers:
        - name: ray-worker
          image: rayproject/ray-ml:2.9.0-py310-gpu
          resources:
            limits:
              cpu: "8"
              memory: "64Gi"
              nvidia.com/gpu: "1"
            requests:
              cpu: "4"
              memory: "32Gi"
              nvidia.com/gpu: "1"
        nodeSelector:
          nvidia.com/gpu.product: NVIDIA-A10G
        tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule

  # High-performance GPU workers (p4d/p5 instances - A100/H100)
  - replicas: 0
    minReplicas: 0
    maxReplicas: 4
    groupName: gpu-a100-workers
    rayStartParams:
      block: 'true'
      num-gpus: '8'
    template:
      spec:
        containers:
        - name: ray-worker
          image: rayproject/ray-ml:2.9.0-py310-gpu
          resources:
            limits:
              cpu: "96"
              memory: "1024Gi"
              nvidia.com/gpu: "8"
            requests:
              cpu: "48"
              memory: "512Gi"
              nvidia.com/gpu: "8"
        nodeSelector:
          nvidia.com/gpu.product: NVIDIA-A100-SXM4-80GB
        tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule

  # AWS Neuron workers (inf2/trn1 instances)
  - replicas: 0
    minReplicas: 0
    maxReplicas: 4
    groupName: neuron-workers
    rayStartParams:
      block: 'true'
    template:
      spec:
        containers:
        - name: ray-worker
          image: public.ecr.aws/neuron/pytorch-training-neuronx:2.1
          resources:
            limits:
              cpu: "32"
              memory: "128Gi"
              aws.amazon.com/neuron: "16"
            requests:
              cpu: "16"
              memory: "64Gi"
              aws.amazon.com/neuron: "16"
        nodeSelector:
          node.kubernetes.io/instance-type: trn1.32xlarge
        tolerations:
        - key: aws.amazon.com/neuron
          operator: Exists
          effect: NoSchedule
```

#### 4. Karpenter - Intelligent Node Provisioning

Karpenter provides fast, cost-effective node provisioning with GPU and Neuron support.

**GPU and Neuron NodePools:**

```yaml
# GPU NodePool for NVIDIA GPUs
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-nodepool
spec:
  template:
    metadata:
      labels:
        node-type: gpu
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        # g5 instances (A10G GPU)
        - g5.xlarge
        - g5.2xlarge
        - g5.4xlarge
        - g5.8xlarge
        - g5.12xlarge
        - g5.16xlarge
        - g5.24xlarge
        - g5.48xlarge
        # p4d instances (A100 GPU)
        - p4d.24xlarge
        # p5 instances (H100 GPU)
        - p5.48xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-nodeclass
      taints:
      - key: nvidia.com/gpu
        effect: NoSchedule

  limits:
    cpu: 1000
    memory: 4000Gi
    nvidia.com/gpu: 100

  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m

  weight: 10
---
# EC2NodeClass for GPU instances
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-nodeclass
spec:
  amiFamily: AL2
  role: KarpenterNodeRole-ml-cluster

  # Use EKS-optimized AMI with GPU drivers
  amiSelectorTerms:
  - alias: al2@latest

  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: ml-cluster

  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: ml-cluster

  # Install NVIDIA drivers and container toolkit
  userData: |
    #!/bin/bash
    set -e

    # Install NVIDIA driver
    yum install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)

    # Configure containerd for NVIDIA
    cat <<EOF > /etc/containerd/config.toml
    version = 2
    [plugins."io.containerd.grpc.v1.cri".containerd]
      default_runtime_name = "nvidia"
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
        runtime_type = "io.containerd.runc.v2"
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
          BinaryName = "/usr/bin/nvidia-container-runtime"
    EOF

    systemctl restart containerd

  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 200Gi
      volumeType: gp3
      iops: 10000
      throughput: 500
      encrypted: true

  # Instance store for ephemeral data
  instanceStorePolicy: RAID0

  tags:
    Environment: production
    Team: ml-platform
---
# Neuron NodePool for AWS Inferentia/Trainium
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: neuron-nodepool
spec:
  template:
    metadata:
      labels:
        node-type: neuron
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        # inf2 instances (Inferentia2)
        - inf2.xlarge
        - inf2.8xlarge
        - inf2.24xlarge
        - inf2.48xlarge
        # trn1 instances (Trainium)
        - trn1.2xlarge
        - trn1.32xlarge
        - trn1n.32xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: neuron-nodeclass
      taints:
      - key: aws.amazon.com/neuron
        effect: NoSchedule

  limits:
    cpu: 500
    memory: 2000Gi
    aws.amazon.com/neuron: 64

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m

  weight: 5
---
# EC2NodeClass for Neuron instances
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: neuron-nodeclass
spec:
  amiFamily: AL2
  role: KarpenterNodeRole-ml-cluster

  amiSelectorTerms:
  - alias: al2@latest

  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: ml-cluster

  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: ml-cluster

  userData: |
    #!/bin/bash
    set -e

    # Install Neuron driver and tools
    tee /etc/yum.repos.d/neuron.repo > /dev/null <<EOF
    [neuron]
    name=Neuron YUM Repository
    baseurl=https://yum.repos.neuron.amazonaws.com
    enabled=1
    gpgcheck=1
    gpgkey=https://yum.repos.neuron.amazonaws.com/GPG-PUB-KEY-AMAZON-AWS-NEURON.PUB
    EOF

    yum install -y aws-neuronx-dkms aws-neuronx-collectives aws-neuronx-runtime-lib aws-neuronx-tools

    # Configure containerd for Neuron
    systemctl restart containerd

  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 500Gi
      volumeType: gp3
      iops: 16000
      throughput: 1000
      encrypted: true

  tags:
    Environment: production
    Team: ml-platform
```

---

## Dynamic Resource Allocation (DRA) for GPUs

Dynamic Resource Allocation (DRA) is Kubernetes' next-generation approach to GPU scheduling, providing fine-grained control over GPU resources that traditional device plugins cannot achieve.

### DRA vs Traditional GPU Scheduling

![Flowchart comparing the traditional GPU device-plugin allocation path, which yields exclusive whole-GPU access with no sharing, against the Kubernetes 1.31+ Dynamic Resource Allocation path, which evaluates topology-aware ResourceClaims to unlock fine-grained, multi-tenant GPU benefits.](../.gitbook/assets/en-ai-ml-06-ai-infrastructure-2.png)

### GPU Sharing Strategies with DRA

DRA supports multiple GPU sharing strategies for different use cases:

| Strategy | Use Case | GPU Utilization | Isolation | Latency |
|----------|----------|-----------------|-----------|---------|
| **Exclusive** | Training, HPC | 100% dedicated | Full | Lowest |
| **MIG** | Multi-tenant inference | Hardware partitioned | Strong | Low |
| **Time-Slicing** | Development, testing | Time-shared | Weak | Variable |
| **MPS** | Parallel small workloads | CUDA context shared | Medium | Medium |

**DRA ResourceClaim for GPU Sharing:**

```yaml
# GPU ResourceClaimTemplate with MIG partitioning
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaimTemplate
metadata:
  name: gpu-mig-3g20gb
  namespace: ml-workloads
spec:
  spec:
    devices:
      requests:
      - name: gpu
        deviceClassName: gpu.nvidia.com
        selectors:
        - cel:
            expression: device.attributes["gpu.nvidia.com/mig.profile"] == "3g.20gb"
      config:
      - requests: ["gpu"]
        opaque:
          driver: gpu.nvidia.com
          parameters:
            # MIG profile: 3 GPU instances, 20GB each
            migProfile: "3g.20gb"
            # Sharing mode
            sharingMode: "mig"
---
# ResourceClaimTemplate for time-slicing
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaimTemplate
metadata:
  name: gpu-timeslice
  namespace: ml-workloads
spec:
  spec:
    devices:
      requests:
      - name: gpu
        deviceClassName: gpu.nvidia.com
      config:
      - requests: ["gpu"]
        opaque:
          driver: gpu.nvidia.com
          parameters:
            sharingMode: "time-slicing"
            timeSlice: "default"
            replicas: 4  # 4 pods share one GPU
---
# ResourceClaimTemplate for MPS
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaimTemplate
metadata:
  name: gpu-mps
  namespace: ml-workloads
spec:
  spec:
    devices:
      requests:
      - name: gpu
        deviceClassName: gpu.nvidia.com
      config:
      - requests: ["gpu"]
        opaque:
          driver: gpu.nvidia.com
          parameters:
            sharingMode: "mps"
            mpsActiveThreadPercentage: 50
---
# Pod using DRA ResourceClaim
apiVersion: v1
kind: Pod
metadata:
  name: inference-pod
  namespace: ml-workloads
spec:
  containers:
  - name: inference
    image: nvcr.io/nvidia/pytorch:24.01-py3
    command: ["python", "/app/inference.py"]
    resources:
      claims:
      - name: gpu-claim
  resourceClaims:
  - name: gpu-claim
    resourceClaimTemplateName: gpu-mig-3g20gb
```

### NVIDIA GPU Operator with DRA Support

DRA requires NVIDIA GPU Operator v25.3.0 or later for full support.

```yaml
# Install NVIDIA GPU Operator with DRA enabled
apiVersion: v1
kind: Namespace
metadata:
  name: gpu-operator
---
# GPU Operator Helm values for DRA
# helm install gpu-operator nvidia/gpu-operator -n gpu-operator -f values.yaml
# values.yaml content:
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-operator-values
  namespace: gpu-operator
data:
  values.yaml: |
    operator:
      defaultRuntime: containerd

    driver:
      enabled: true
      version: "550.90.07"

    toolkit:
      enabled: true
      version: "v1.15.0"

    devicePlugin:
      enabled: true
      config:
        name: device-plugin-config
        default: any
        data:
          any: |-
            version: v1
            sharing:
              timeSlicing:
                renameByDefault: false
                failRequestsGreaterThanOne: false
                resources:
                - name: nvidia.com/gpu
                  replicas: 4
          mig-mixed: |-
            version: v1
            sharing:
              mig:
                strategy: mixed

    # DRA driver configuration (v25.3.0+)
    draDriver:
      enabled: true
      version: "v0.1.0"
      config:
        sharing:
          mps:
            enabled: true
          timeSlicing:
            enabled: true
          mig:
            enabled: true
            strategy: mixed

    # MIG manager for automatic MIG configuration
    migManager:
      enabled: true
      config:
        default: all-disabled
        data:
          all-disabled: |-
            version: v1
            mig-configs: {}
          all-1g.10gb: |-
            version: v1
            mig-configs:
              all-1g.10gb:
                - devices: all
                  mig-enabled: true
                  mig-devices:
                    1g.10gb: 7
          all-3g.40gb: |-
            version: v1
            mig-configs:
              all-3g.40gb:
                - devices: all
                  mig-enabled: true
                  mig-devices:
                    3g.40gb: 2

    # DCGM exporter for GPU metrics
    dcgmExporter:
      enabled: true
      serviceMonitor:
        enabled: true

    # GPU Feature Discovery
    gfd:
      enabled: true

    # Node Feature Discovery
    nfd:
      enabled: true
```

### Topology-Aware Scheduling for NVLink/IMEX

For multi-GPU training workloads, topology-aware scheduling ensures GPUs connected via NVLink are allocated together.

```yaml
# ResourceClaim for topology-aware multi-GPU allocation
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaim
metadata:
  name: multi-gpu-nvlink
  namespace: ml-training
spec:
  devices:
    requests:
    - name: gpu-group
      deviceClassName: gpu.nvidia.com
      count: 8  # Request 8 GPUs
      selectors:
      # Ensure all GPUs are on the same node
      - cel:
          expression: device.topology.node == device.topology.node
      # Prefer NVLink-connected GPUs
      - cel:
          expression: device.attributes["gpu.nvidia.com/nvlink.capable"] == "true"
    constraints:
    # All GPUs must be from the same NUMA node for best performance
    - requests: ["gpu-group"]
      matchAttribute: device.topology.numa
---
# Pod for distributed training with topology awareness
apiVersion: v1
kind: Pod
metadata:
  name: distributed-training
  namespace: ml-training
spec:
  containers:
  - name: trainer
    image: nvcr.io/nvidia/pytorch:24.01-py3
    command:
    - torchrun
    - --nproc_per_node=8
    - --nnodes=1
    - /app/train.py
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_IB_DISABLE
      value: "0"
    - name: NCCL_NVLS_ENABLE
      value: "1"  # Enable NVLink SHARP
    resources:
      claims:
      - name: gpu-claim
  resourceClaims:
  - name: gpu-claim
    resourceClaimName: multi-gpu-nvlink
  # Ensure pod scheduling respects GPU topology
  schedulingGates:
  - name: gpu-topology
```

### P6e-GB200 UltraServer Support

The NVIDIA GB200 NVL72 (P6e instances) require DRA for proper resource management due to their unique architecture with 72 interconnected GPUs.

```yaml
# ResourceSlice representing GB200 NVL72 topology
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceSlice
metadata:
  name: gb200-nvl72-node-1
spec:
  nodeName: p6e-gb200-node-1
  pool:
    name: gb200-pool
    generation: 1
    resourceSliceCount: 1
  driver: gpu.nvidia.com
  devices:
  - name: gpu-0
    basic:
      attributes:
        gpu.nvidia.com/product: "NVIDIA-GB200"
        gpu.nvidia.com/memory: "192Gi"
        gpu.nvidia.com/nvlink.version: "5.0"
        gpu.nvidia.com/nvswitch.connected: "true"
        gpu.nvidia.com/imex.capable: "true"
      capacity:
        gpu.nvidia.com/gpu: 1
---
# DeviceClass for GB200 GPUs
apiVersion: resource.k8s.io/v1alpha3
kind: DeviceClass
metadata:
  name: gpu.nvidia.com.gb200
spec:
  selectors:
  - cel:
      expression: device.attributes["gpu.nvidia.com/product"] == "NVIDIA-GB200"
  config:
  - opaque:
      driver: gpu.nvidia.com
      parameters:
        # Enable IMEX (In-Memory Exchange) for GB200
        imexEnabled: true
        # NVSwitch-based communication
        nvswitchEnabled: true
        # Grace-Hopper specific optimizations
        graceHopperMode: true
---
# ResourceClaimTemplate for GB200 workloads
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaimTemplate
metadata:
  name: gb200-training
  namespace: ml-training
spec:
  spec:
    devices:
      requests:
      - name: gb200-gpus
        deviceClassName: gpu.nvidia.com.gb200
        count: 72  # Full NVL72 rack
      constraints:
      - requests: ["gb200-gpus"]
        matchAttribute: device.topology.nvswitch
```

---

## Agents on EKS Platform

The Agents on EKS platform provides infrastructure for building and deploying AI agents with integrated tooling for source control, observability, vector storage, and tool discovery.

### Agents Platform Architecture

```yaml
# GitLab for Source Control and CI/CD
apiVersion: v1
kind: Namespace
metadata:
  name: gitlab
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: gitlab
  namespace: gitlab
spec:
  interval: 10m
  chart:
    spec:
      chart: gitlab
      version: "7.8.0"
      sourceRef:
        kind: HelmRepository
        name: gitlab
        namespace: flux-system
  values:
    global:
      hosts:
        domain: agents.example.com
        gitlab:
          name: gitlab.agents.example.com
      ingress:
        configureCertmanager: true
        class: alb
        annotations:
          alb.ingress.kubernetes.io/scheme: internet-facing
          alb.ingress.kubernetes.io/target-type: ip

    # Runner configuration for CI/CD
    gitlab-runner:
      runners:
        privileged: true
        config: |
          [[runners]]
            [runners.kubernetes]
              namespace = "gitlab"
              image = "ubuntu:22.04"
              [[runners.kubernetes.volumes.pvc]]
                name = "runner-cache"
                mount_path = "/cache"
---
# Langfuse for LLM Observability
apiVersion: v1
kind: Namespace
metadata:
  name: langfuse
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langfuse
  namespace: langfuse
spec:
  replicas: 2
  selector:
    matchLabels:
      app: langfuse
  template:
    metadata:
      labels:
        app: langfuse
    spec:
      containers:
      - name: langfuse
        image: langfuse/langfuse:2.50.0
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: database-url
        - name: NEXTAUTH_URL
          value: "https://langfuse.agents.example.com"
        - name: NEXTAUTH_SECRET
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: nextauth-secret
        - name: SALT
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: salt
        - name: ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: encryption-key
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
---
# Milvus Vector Database for RAG
apiVersion: v1
kind: Namespace
metadata:
  name: milvus
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: milvus
  namespace: milvus
spec:
  interval: 10m
  chart:
    spec:
      chart: milvus
      version: "4.1.0"
      sourceRef:
        kind: HelmRepository
        name: milvus
        namespace: flux-system
  values:
    cluster:
      enabled: true

    # Proxy configuration
    proxy:
      replicas: 2
      resources:
        requests:
          cpu: "500m"
          memory: "2Gi"
        limits:
          cpu: "2"
          memory: "8Gi"

    # Query nodes with GPU acceleration
    queryNode:
      replicas: 2
      resources:
        requests:
          cpu: "2"
          memory: "8Gi"
          nvidia.com/gpu: "1"
        limits:
          nvidia.com/gpu: "1"

    # Index nodes for vector indexing
    indexNode:
      replicas: 2
      resources:
        requests:
          cpu: "4"
          memory: "16Gi"
          nvidia.com/gpu: "1"
        limits:
          nvidia.com/gpu: "1"

    # Storage configuration
    minio:
      enabled: false

    externalS3:
      enabled: true
      host: s3.us-west-2.amazonaws.com
      port: 443
      useSSL: true
      bucketName: milvus-storage
      useIAM: true

    # etcd for metadata
    etcd:
      replicaCount: 3
      persistence:
        enabled: true
        storageClass: gp3
        size: 50Gi
---
# MCP Gateway for Tool Discovery
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-gateway
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-gateway
  namespace: mcp-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-gateway
  template:
    metadata:
      labels:
        app: mcp-gateway
    spec:
      containers:
      - name: mcp-gateway
        image: ghcr.io/anthropics/mcp-gateway:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: grpc
        env:
        - name: REGISTRY_BACKEND
          value: "kubernetes"
        - name: DISCOVERY_MODE
          value: "auto"
        - name: LOG_LEVEL
          value: "info"
        volumeMounts:
        - name: config
          mountPath: /etc/mcp-gateway
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "2Gi"
      volumes:
      - name: config
        configMap:
          name: mcp-gateway-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-gateway-config
  namespace: mcp-gateway
data:
  config.yaml: |
    server:
      http_port: 8080
      grpc_port: 9090

    registry:
      type: kubernetes
      kubernetes:
        namespace: mcp-tools
        label_selector: "mcp.anthropic.com/tool=true"

    discovery:
      enabled: true
      interval: 30s
      endpoints:
      - name: kubernetes
        type: kubernetes
        config:
          namespaces: ["mcp-tools", "ai-agents"]

    auth:
      enabled: true
      provider: oidc
      oidc:
        issuer: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_xxxxx
        client_id: mcp-gateway-client

    rate_limiting:
      enabled: true
      requests_per_minute: 1000

    telemetry:
      metrics:
        enabled: true
        port: 9091
      tracing:
        enabled: true
        endpoint: http://otel-collector.monitoring:4317
```

### AI Agent Deployment Example

```yaml
# AI Agent Deployment with RAG capabilities
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent
  namespace: ai-agents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-agent
  template:
    metadata:
      labels:
        app: ai-agent
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
    spec:
      serviceAccountName: ai-agent
      containers:
      - name: agent
        image: ai-agents/customer-support:v1.2.0
        ports:
        - containerPort: 8000
          name: http
        env:
        # LLM configuration
        - name: LLM_PROVIDER
          value: "bedrock"
        - name: LLM_MODEL
          value: "anthropic.claude-3-5-sonnet-20241022-v2:0"
        - name: AWS_REGION
          value: "us-west-2"

        # Vector database for RAG
        - name: MILVUS_HOST
          value: "milvus.milvus.svc.cluster.local"
        - name: MILVUS_PORT
          value: "19530"
        - name: MILVUS_COLLECTION
          value: "knowledge_base"

        # Langfuse for observability
        - name: LANGFUSE_HOST
          value: "https://langfuse.agents.example.com"
        - name: LANGFUSE_PUBLIC_KEY
          valueFrom:
            secretKeyRef:
              name: langfuse-credentials
              key: public-key
        - name: LANGFUSE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: langfuse-credentials
              key: secret-key

        # MCP Gateway for tool discovery
        - name: MCP_GATEWAY_URL
          value: "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"

        resources:
          requests:
            cpu: "1"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "16Gi"

        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

      # Sidecar for embedding model
      - name: embeddings
        image: ai-agents/embeddings:v1.0.0
        ports:
        - containerPort: 8001
          name: grpc
        env:
        - name: MODEL_NAME
          value: "sentence-transformers/all-MiniLM-L6-v2"
        resources:
          requests:
            cpu: "500m"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "8Gi"
```

---

## Storage Solutions for AI/ML

### Amazon EFS for Shared Model Storage

```yaml
# EFS StorageClass for shared notebooks and models
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-xxxxxxxxx
  directoryPerms: "755"
  gidRangeStart: "1000"
  gidRangeEnd: "2000"
  basePath: "/ml-storage"
mountOptions:
  - tls
  - iam
---
# Shared models PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-models-pvc
  namespace: ml-platform
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 500Gi
---
# Shared datasets PVC (read-only for most users)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-datasets-pvc
  namespace: ml-platform
spec:
  accessModes:
    - ReadOnlyMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 2Ti
```

### FSx for Lustre for High-Throughput Training

```yaml
# FSx for Lustre StorageClass for training workloads
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-xxxxxxxxx
  securityGroupIds: sg-xxxxxxxxx
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: "500"  # MB/s per TiB
  dataCompressionType: LZ4
  automaticBackupRetentionDays: "7"
  copyTagsToBackups: "true"
  s3ImportPath: s3://ml-datasets
  s3ExportPath: s3://ml-training-outputs
mountOptions:
  - flock
---
# FSx for Lustre PVC for training data
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: training-data-pvc
  namespace: ml-training
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 10Ti
```

### S3 Integration with Mountpoint

```yaml
# S3 CSI Driver StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: s3-sc
provisioner: s3.csi.aws.com
parameters:
  bucketName: ml-artifacts
mountOptions:
  - allow-delete
  - allow-other
  - uid=1000
  - gid=1000
---
# S3-backed PVC for model artifacts
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-artifacts-pvc
  namespace: ml-platform
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: s3-sc
  resources:
    requests:
      storage: 1Ti  # Logical size, S3 scales automatically
```

---

## Networking for AI Workloads

### Elastic Fabric Adapter (EFA) for Multi-Node Training

EFA provides high-bandwidth, low-latency networking essential for distributed training.

```yaml
# EFA-enabled NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: efa-training-nodepool
spec:
  template:
    metadata:
      labels:
        node-type: efa-training
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        # EFA-supported GPU instances
        - p4d.24xlarge   # 4x 400 Gbps EFA
        - p5.48xlarge    # 32x 400 Gbps EFA
        - trn1.32xlarge  # 8x 800 Gbps EFA
        - trn1n.32xlarge # 16x 1600 Gbps EFA
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: efa-nodeclass
      taints:
      - key: nvidia.com/gpu
        effect: NoSchedule
---
# EC2NodeClass with EFA support
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: efa-nodeclass
spec:
  amiFamily: AL2
  role: KarpenterNodeRole-ml-cluster

  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: ml-cluster
      efa-enabled: "true"

  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: ml-cluster
      efa-enabled: "true"

  # Enable all available EFA interfaces
  instanceStorePolicy: RAID0

  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 500Gi
      volumeType: gp3
      iops: 16000
      throughput: 1000
---
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
        image: public.ecr.aws/eks/aws-efa-k8s-device-plugin:v0.5.0
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        volumeMounts:
        - name: device-plugin
          mountPath: /var/lib/kubelet/device-plugins
      volumes:
      - name: device-plugin
        hostPath:
          path: /var/lib/kubelet/device-plugins
      nodeSelector:
        node-type: efa-training
---
# Distributed training job with EFA
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training-efa
  namespace: ml-training
spec:
  nprocPerNode: "8"
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: pytorch
            image: nvcr.io/nvidia/pytorch:24.01-py3
            command:
            - torchrun
            - --nproc_per_node=8
            - --nnodes=4
            - --node_rank=0
            - --master_addr=$(MASTER_ADDR)
            - --master_port=29500
            - /app/train.py
            env:
            - name: NCCL_DEBUG
              value: "INFO"
            - name: FI_PROVIDER
              value: "efa"
            - name: FI_EFA_USE_DEVICE_RDMA
              value: "1"
            - name: NCCL_ALGO
              value: "Ring,Tree"
            - name: NCCL_PROTO
              value: "Simple"
            resources:
              limits:
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              requests:
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
          nodeSelector:
            node-type: efa-training
    Worker:
      replicas: 3
      restartPolicy: OnFailure
      template:
        spec:
          containers:
          - name: pytorch
            image: nvcr.io/nvidia/pytorch:24.01-py3
            command:
            - torchrun
            - --nproc_per_node=8
            - --nnodes=4
            - --node_rank=$(RANK)
            - --master_addr=$(MASTER_ADDR)
            - --master_port=29500
            - /app/train.py
            env:
            - name: NCCL_DEBUG
              value: "INFO"
            - name: FI_PROVIDER
              value: "efa"
            - name: FI_EFA_USE_DEVICE_RDMA
              value: "1"
            resources:
              limits:
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              requests:
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
          nodeSelector:
            node-type: efa-training
```

### VPC Design for AI Workloads

```yaml
# VPC Configuration for AI/ML workloads (Terraform reference)
# Recommended: 2-4 AZs with large CIDR blocks for IP-intensive GPU instances

# Example subnet layout:
# - Public subnets: NAT gateways, load balancers
# - Private subnets: EKS nodes, GPU instances
# - Isolated subnets: FSx for Lustre, EFA traffic

# Security group for GPU instances
apiVersion: v1
kind: ConfigMap
metadata:
  name: vpc-design-reference
  namespace: kube-system
data:
  security-groups.yaml: |
    # GPU Node Security Group
    - name: gpu-nodes-sg
      description: Security group for GPU nodes
      ingress:
        # Allow all traffic within VPC for NCCL/EFA
        - protocol: -1
          from_port: 0
          to_port: 65535
          cidr_blocks: ["10.0.0.0/16"]
        # EFA requires all traffic between GPU nodes
        - protocol: -1
          from_port: 0
          to_port: 65535
          self: true
      egress:
        - protocol: -1
          from_port: 0
          to_port: 65535
          cidr_blocks: ["0.0.0.0/0"]

    # EFA Security Group (additional rules)
    - name: efa-sg
      description: Security group for EFA traffic
      ingress:
        # All traffic from EFA-enabled instances
        - protocol: -1
          from_port: 0
          to_port: 65535
          self: true
      egress:
        - protocol: -1
          from_port: 0
          to_port: 65535
          self: true
```

---

## Monitoring and Observability

### Prometheus and Grafana Stack

```yaml
# Prometheus configuration for GPU metrics
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-gpu-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
    # DCGM Exporter for NVIDIA GPU metrics
    - job_name: 'dcgm-exporter'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: dcgm-exporter
      - source_labels: [__meta_kubernetes_pod_container_port_number]
        action: keep
        regex: '9400'
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_pod_node_name]
        target_label: node

    # Neuron Monitor for AWS Inferentia/Trainium
    - job_name: 'neuron-monitor'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: neuron-monitor
      - source_labels: [__meta_kubernetes_pod_container_port_number]
        action: keep
        regex: '8000'

    # Ray metrics
    - job_name: 'ray-metrics'
      kubernetes_sd_configs:
      - role: service
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_label_ray_io_cluster]
        action: keep
        regex: .+
      - source_labels: [__meta_kubernetes_service_port_name]
        action: keep
        regex: metrics

    # Karpenter metrics
    - job_name: 'karpenter'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['karpenter']
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_name]
        action: keep
        regex: karpenter
---
# DCGM Exporter DaemonSet
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
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9400"
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04
        ports:
        - containerPort: 9400
          name: metrics
        env:
        - name: DCGM_EXPORTER_LISTEN
          value: ":9400"
        - name: DCGM_EXPORTER_KUBERNETES
          value: "true"
        - name: DCGM_EXPORTER_COLLECTORS
          value: "/etc/dcgm-exporter/dcp-metrics-included.csv"
        securityContext:
          runAsNonRoot: false
          runAsUser: 0
          capabilities:
            add: ["SYS_ADMIN"]
        volumeMounts:
        - name: pod-resources
          mountPath: /var/lib/kubelet/pod-resources
      volumes:
      - name: pod-resources
        hostPath:
          path: /var/lib/kubelet/pod-resources
      nodeSelector:
        nvidia.com/gpu.present: "true"
---
# Grafana Dashboard ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-gpu-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  gpu-dashboard.json: |
    {
      "dashboard": {
        "title": "GPU Cluster Overview",
        "panels": [
          {
            "title": "GPU Utilization",
            "type": "timeseries",
            "targets": [
              {
                "expr": "avg(DCGM_FI_DEV_GPU_UTIL) by (node, gpu)",
                "legendFormat": "{{node}} - GPU {{gpu}}"
              }
            ]
          },
          {
            "title": "GPU Memory Usage",
            "type": "timeseries",
            "targets": [
              {
                "expr": "DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) * 100",
                "legendFormat": "{{node}} - GPU {{gpu}}"
              }
            ]
          },
          {
            "title": "GPU Temperature",
            "type": "gauge",
            "targets": [
              {
                "expr": "avg(DCGM_FI_DEV_GPU_TEMP) by (node)",
                "legendFormat": "{{node}}"
              }
            ]
          },
          {
            "title": "GPU Power Usage",
            "type": "timeseries",
            "targets": [
              {
                "expr": "sum(DCGM_FI_DEV_POWER_USAGE) by (node)",
                "legendFormat": "{{node}}"
              }
            ]
          },
          {
            "title": "GPU SM Clock",
            "type": "stat",
            "targets": [
              {
                "expr": "avg(DCGM_FI_DEV_SM_CLOCK)",
                "legendFormat": "SM Clock (MHz)"
              }
            ]
          },
          {
            "title": "NVLink Bandwidth",
            "type": "timeseries",
            "targets": [
              {
                "expr": "rate(DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL[5m])",
                "legendFormat": "{{node}} - GPU {{gpu}}"
              }
            ]
          },
          {
            "title": "PCIe Bandwidth",
            "type": "timeseries",
            "targets": [
              {
                "expr": "rate(DCGM_FI_DEV_PCIE_TX_THROUGHPUT[5m]) + rate(DCGM_FI_DEV_PCIE_RX_THROUGHPUT[5m])",
                "legendFormat": "{{node}} - GPU {{gpu}}"
              }
            ]
          },
          {
            "title": "Tensor Core Utilization",
            "type": "timeseries",
            "targets": [
              {
                "expr": "avg(DCGM_FI_PROF_PIPE_TENSOR_ACTIVE) by (node, gpu) * 100",
                "legendFormat": "{{node}} - GPU {{gpu}}"
              }
            ]
          }
        ]
      }
    }
```

### GPU Utilization Alerts

```yaml
# PrometheusRule for GPU alerts
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-alerts
  namespace: monitoring
spec:
  groups:
  - name: gpu.rules
    interval: 30s
    rules:
    # GPU utilization alerts
    - alert: GPULowUtilization
      expr: avg_over_time(DCGM_FI_DEV_GPU_UTIL[30m]) < 20
      for: 1h
      labels:
        severity: warning
      annotations:
        summary: "Low GPU utilization on {{ $labels.node }}"
        description: "GPU {{ $labels.gpu }} on node {{ $labels.node }} has been underutilized (<20%) for over 1 hour. Consider consolidating workloads."

    - alert: GPUHighTemperature
      expr: DCGM_FI_DEV_GPU_TEMP > 85
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High GPU temperature on {{ $labels.node }}"
        description: "GPU {{ $labels.gpu }} on node {{ $labels.node }} temperature is {{ $value }}C, which exceeds the safe threshold."

    - alert: GPUMemoryExhausted
      expr: (DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100 > 95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "GPU memory nearly exhausted on {{ $labels.node }}"
        description: "GPU {{ $labels.gpu }} on node {{ $labels.node }} memory usage is at {{ $value }}%."

    - alert: GPUXIDError
      expr: increase(DCGM_FI_DEV_XID_ERRORS[5m]) > 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "GPU XID error detected on {{ $labels.node }}"
        description: "GPU {{ $labels.gpu }} on node {{ $labels.node }} has reported XID errors, indicating potential hardware issues."

    - alert: GPUECCErrors
      expr: increase(DCGM_FI_DEV_ECC_DBE_VOL_TOTAL[1h]) > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: "GPU ECC double-bit errors on {{ $labels.node }}"
        description: "GPU {{ $labels.gpu }} on node {{ $labels.node }} has reported ECC double-bit errors."

    # Karpenter scaling alerts
    - alert: GPUNodePoolExhausted
      expr: karpenter_nodepools_limit{resource="nvidia.com/gpu"} - karpenter_nodepools_usage{resource="nvidia.com/gpu"} < 2
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "GPU NodePool approaching limit"
        description: "GPU NodePool {{ $labels.nodepool }} has only {{ $value }} GPUs remaining before hitting its limit."

    - alert: PendingGPUPods
      expr: sum(kube_pod_status_phase{phase="Pending"} * on(pod, namespace) group_left() kube_pod_container_resource_requests{resource="nvidia.com/gpu"}) > 0
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "Pods pending due to GPU unavailability"
        description: "{{ $value }} pods requesting GPUs have been pending for over 15 minutes."
```

---

## Best Practices Summary

### Infrastructure Best Practices

| Category | Recommendation | Rationale |
|----------|---------------|-----------|
| **Compute** | Use Karpenter with separate NodePools for GPU types | Faster provisioning, cost optimization |
| **Storage** | EFS for shared data, FSx Lustre for training | Match I/O patterns to workload needs |
| **Networking** | Enable EFA for multi-node training | 400+ Gbps bandwidth for NCCL |
| **Scheduling** | Use DRA for GPU sharing in Kubernetes 1.31+ | Fine-grained GPU allocation |
| **Monitoring** | Deploy DCGM exporter on all GPU nodes | GPU-specific metrics and alerting |

### Cost Optimization Strategies

1. **Spot Instances**: Use Spot for fault-tolerant training with checkpointing
2. **Right-sizing**: Match GPU type to workload (T4 for dev, A100 for production training)
3. **Consolidation**: Use Karpenter's consolidation to bin-pack GPU workloads
4. **Time-slicing**: Share GPUs for inference workloads with DRA
5. **Neuron Instances**: Consider inf2/trn1 for inference (up to 50% cost savings)

### Security Considerations

1. **Network Isolation**: Use dedicated subnets for GPU nodes
2. **IAM Roles**: Implement least-privilege IRSA for S3/secrets access
3. **Encryption**: Enable encryption for EBS, EFS, and S3
4. **Secrets Management**: Use External Secrets Operator for API keys
5. **Container Security**: Scan GPU container images for vulnerabilities

---

## References

- [AI on EKS - AWS Labs](https://awslabs.github.io/ai-on-eks/)
- [NVIDIA GPU Operator Documentation](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/)
- [Ray on Kubernetes Documentation](https://docs.ray.io/en/latest/cluster/kubernetes/)
- [Karpenter Documentation](https://karpenter.sh/)
- [Amazon EKS Best Practices Guide - AI/ML](https://aws.github.io/aws-eks-best-practices/ai-ml/)
- [NVIDIA DCGM Documentation](https://docs.nvidia.com/datacenter/dcgm/latest/)
- [Dynamic Resource Allocation KEP](https://github.com/kubernetes/enhancements/tree/master/keps/sig-node/3063-dynamic-resource-allocation)

---

**Quiz**: Test your knowledge with the [AI Infrastructure Quiz](../quizzes/ai-ml/06-ai-infrastructure-quiz.md)
