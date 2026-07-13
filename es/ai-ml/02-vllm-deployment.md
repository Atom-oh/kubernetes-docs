# vLLM Deployment & Optimization

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33  
> **Última actualización**: April 9, 2026

vLLM es el motor de inferencia open-source de alto rendimiento más ampliamente adoptado para modelos de lenguaje de gran tamaño (LLMs). En este capítulo, exploraremos las características y la arquitectura más recientes de vLLM, y aprenderemos cómo desplegarlo y optimizarlo a escala de producción en EKS.

## Lab Environment Setup

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Required Tools and Resources
- kubectl v1.31 o superior
- Helm v3.10 o superior
- Cluster EKS con GPUs NVIDIA (recomendación mínima: instancia g5.2xlarge)
- Drivers NVIDIA y NVIDIA Device Plugin instalados
- Al menos 50 GB de espacio en disco

### GPU Node Setup

```bash
# Install NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU nodes
kubectl get nodes "-o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu"
```

## Introduction to vLLM

vLLM es un motor de inferencia de LLM con las siguientes características:

```mermaid
flowchart TD
    subgraph vLLM [vLLM Architecture]
        subgraph Features [Key Features]
            PagedAttention[PagedAttention]
            ContinuousBatching[Continuous Batching]
            DistributedInference[Distributed Inference]
            Quantization[Quantization]
            OpenAIAPI[OpenAI Compatible API]
        end

        subgraph Components [Core Components]
            Engine[Inference Engine]
            Scheduler[Request Scheduler]
            KVCache[KV Cache Manager]
            ModelLoader[Model Loader]
            APIServer[API Server]
        end

        subgraph Benefits [Key Benefits]
            MemoryEfficiency[Memory Efficiency]
            HighThroughput[High Throughput]
            LowLatency[Low Latency]
            Scalability[Scalability]
        end
    end

    PagedAttention --> MemoryEfficiency
    ContinuousBatching --> HighThroughput
    DistributedInference --> Scalability
    Quantization --> MemoryEfficiency

    Engine --> KVCache
    Scheduler --> Engine
    ModelLoader --> Engine
    Engine --> APIServer

    classDef featureNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef componentNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef benefitNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    class PagedAttention,ContinuousBatching,DistributedInference,Quantization,OpenAIAPI,Features featureNode;
    class Engine,Scheduler,KVCache,ModelLoader,APIServer,Components componentNode;
    class MemoryEfficiency,HighThroughput,LowLatency,Scalability,Benefits benefitNode;
    class vLLM default;
```

### Key Features of vLLM

1. **PagedAttention**:
   - Tecnología de gestión de memoria que administra eficientemente la KV cache
   - Inspirada en la gestión de memoria virtual de los sistemas operativos
   - Permite procesar hasta 10 veces más solicitudes concurrentes

2. **Continuous Batching**:
   - Agrupa solicitudes dinámicamente para maximizar la utilización de GPU
   - Comienza a procesar nuevas solicitudes inmediatamente al llegar
   - Hasta 2 veces de mejora en throughput

3. **Distributed Inference**:
   - Soporta modelos a gran escala mediante paralelización de tensores
   - Sharding del modelo en múltiples GPUs
   - Soporta modelos de más de 175B parámetros

4. **Quantization**:
   - Soporta varias precisiones, incluidas INT8 y FP16
   - Reduce el uso de memoria y mejora la velocidad de inferencia
   - Hasta 2 veces de mejora en eficiencia de memoria con pérdida mínima de precisión

## Supported Models

vLLM soporta los siguientes modelos:

| Model Family | Supported Models | Quantization Options |
|-------------|-----------------|---------------------|
| **LLaMA 3 / 3.1 / 3.2 / 3.3** | 1B, 3B, 8B, 70B, 405B | FP16, BF16, FP8, INT8, INT4, AWQ, GPTQ |
| **DeepSeek V3 / R1** | 7B, 67B, 671B (MoE) | FP16, BF16, FP8, AWQ, GPTQ |
| **Qwen 2 / 2.5 / QwQ** | 0.5B ~ 72B | FP16, BF16, FP8, INT8, AWQ, GPTQ |
| **Mistral / Mixtral** | 7B, 8x7B, 8x22B, Large 2 | FP16, BF16, FP8, AWQ, GPTQ |
| **Gemma 2 / 3** | 2B, 9B, 27B | FP16, BF16, INT8 |
| **Phi-3 / Phi-4** | 3.8B, 7B, 14B | FP16, BF16, INT8, AWQ |
| **Command R / R+** | 35B, 104B | FP16, BF16 |
| **DBRX** | 132B (MoE) | FP16, BF16 |
| **StarCoder 2** | 3B, 7B, 15B | FP16, BF16 |
| **Vision Models (VLM)** | LLaVA, Pixtral, Qwen2-VL, InternVL | FP16, BF16 |

1. **PagedAttention**: Mecanismo de atención eficiente en memoria que optimiza el uso de memoria al procesar secuencias largas.
2. **Continuous Batching**: Agrupa solicitudes dinámicamente para mejorar el throughput.
3. **Distributed Inference**: Distribuye modelos entre múltiples GPUs y nodes para manejar modelos a gran escala.
4. **Quantization**: Soporta quantization INT8/INT4 para reducir el uso de memoria y mejorar el throughput.
5. **OpenAI Compatible API**: Proporciona una interfaz compatible con la API de OpenAI.

### Latest vLLM Features (v0.6+)

vLLM evoluciona rápidamente con nuevas capacidades significativas en versiones recientes:

#### Speculative Decoding

Usa un modelo borrador más pequeño para generar múltiples tokens candidatos, que el modelo más grande verifica en una sola pasada, mejorando la velocidad de inferencia entre 2 y 3 veces:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --speculative-model meta-llama/Llama-3.1-8B-Instruct \
  --num-speculative-tokens 5
```

#### Prefix Caching

Reutiliza automáticamente la KV cache entre solicitudes que comparten el mismo system prompt o contexto, reduciendo drásticamente el TTFT (Time to First Token):

```bash
--enable-prefix-caching
```

#### Chunked Prefill

Divide el prefill de prompts largos en chunks más pequeños intercalados con pasos de decodificación, reduciendo el impacto de las solicitudes de contexto largo sobre la latencia de otras solicitudes:

```bash
--enable-chunked-prefill --max-num-batched-tokens 2048
```

#### Dynamic LoRA Adapter Loading

Carga y descarga dinámicamente múltiples adaptadores LoRA en tiempo de ejecución, sirviendo muchos modelos personalizados desde un único modelo base:

```bash
--enable-lora --max-loras 4 --max-lora-rank 64
```

```python
# Specify LoRA model in API request
response = client.chat.completions.create(
    model="my-custom-lora-adapter",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

#### Structured Output

Soporta generación de salida restringida mediante JSON Schema, patrones regex y CFG (Context-Free Grammar) para generar datos estructurados de forma confiable:

```python
from openai import OpenAI
client = OpenAI(base_url="http://vllm-service:8000/v1")

response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "Return user information as JSON"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "user_info",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "email": {"type": "string"}
                },
                "required": ["name", "age", "email"]
            }
        }
    }
)
```

#### Tool Calling

Soporta Tool/Function Calling compatible con OpenAI para integrarse con flujos de trabajo de agentes:

```python
response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "What's the weather in Seoul?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a specified location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"]
            }
        }
    }]
)
```

#### FP8 Quantization

Soporta FP8 quantization en GPUs Hopper (H100) y Ada Lovelace (L4, L40S), reduciendo a la mitad el uso de memoria mientras mantiene una precisión casi idéntica:

```bash
--quantization fp8 --kv-cache-dtype fp8
```

#### Vision-Language Model (VLM) Serving

Soporta modelos multimodales que procesan imágenes y texto simultáneamente:

```python
response = client.chat.completions.create(
    model="llava-hf/llava-v1.6-mistral-7b-hf",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
    }]
)
```

## System Requirements

Requisitos del sistema para desplegar vLLM en EKS:

```mermaid
flowchart TD
    subgraph Requirements [System Requirements]
        subgraph Hardware [Hardware]
            GPU[NVIDIA GPU]
            Memory[GPU Memory]
            CPU[CPU Cores]
        end

        subgraph Software [Software]
            CUDA[CUDA 12.1+]
            Python[Python 3.9+]
            PyTorch[PyTorch 2.4.0+]
        end

        subgraph ModelSize [Requirements by Model Size]
            Model7B[7B Model: 16GB+ GPU Memory]
            Model13B[13B Model: 24GB+ GPU Memory]
            Model70B[70B Model: 80GB+ GPU Memory]
        end
    end

    GPU --> Memory
    Memory --> ModelSize

    classDef hardwareNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef softwareNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef modelNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class GPU,Memory,CPU,Hardware hardwareNode;
    class CUDA,Python,PyTorch,Software softwareNode;
    class Model7B,Model13B,Model70B,ModelSize modelNode;
    class Requirements default;
```

1. **Hardware**:
   - NVIDIA GPU (arquitectura Volta, Turing, Ampere, Hopper)
   - Memoria GPU mínima: varía según el tamaño del modelo
     - Modelo 7B: mínimo 16 GB de memoria GPU
     - Modelo 13B: mínimo 24 GB de memoria GPU
     - Modelo 70B: mínimo 80 GB de memoria GPU (o distribuida entre múltiples GPUs)

2. **Software**:
   - CUDA 12.1 o superior (se recomienda CUDA 12.4 para FP8)
   - Python 3.9 o superior
   - PyTorch 2.4.0 o superior

3. **EKS Node Types**:
   - p5.48xlarge: 8x NVIDIA H100 GPU, 80 GB cada una (máximo rendimiento)
   - p4d.24xlarge: 8x NVIDIA A100 GPU, 40 GB u 80 GB cada una
   - g6.12xlarge: 4x NVIDIA L4 GPU, 24 GB cada una (rentable)
   - g5.12xlarge: 4x NVIDIA A10G GPU, 24 GB cada una
   - g6e.12xlarge: 4x NVIDIA L40S GPU, 48 GB cada una
   - trn1.32xlarge: 16x AWS Trainium, 32 GB cada una (silicio de AWS)

## EKS Infrastructure Configuration

```mermaid
flowchart TD
    subgraph AWS [AWS Cloud]
        subgraph EKS [Amazon EKS]
            subgraph ControlPlane [Control Plane]
                APIServer[API Server]
                Scheduler[Scheduler]
                ControllerManager[Controller Manager]
            end

            subgraph NodeGroups [Node Groups]
                subgraph GPUNodes [GPU Nodes]
                    P4d[p4d.24xlarge]
                    P3[p3.16xlarge]
                    G5[g5.12xlarge]
                end

                subgraph CPUNodes [CPU Nodes]
                    C5[c5.4xlarge]
                    M5[m5.4xlarge]
                end
            end

            subgraph Storage [Storage]
                FSx[FSx for Lustre]
                EBS[Amazon EBS]
                S3[Amazon S3]
            end

            subgraph Networking [Networking]
                VPC[VPC]
                Subnet[Subnet]
                SecurityGroup[Security Group]
                EFA[Elastic Fabric Adapter]
            end
        end

        subgraph Services [AWS Services]
            ECR[Amazon ECR]
            CloudWatch[CloudWatch]
            IAM[IAM]
        end
    end

    GPUNodes --> Storage
    GPUNodes --> Networking
    CPUNodes --> Storage
    CPUNodes --> Networking

    EKS --> Services

    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef gpuNode fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef cpuNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class ECR,CloudWatch,IAM,FSx,EBS,S3 awsService;
    class APIServer,Scheduler,ControllerManager,ControlPlane,Networking,VPC,Subnet,SecurityGroup,EFA k8sComponent;
    class P4d,P3,G5,GPUNodes gpuNode;
    class C5,M5,CPUNodes cpuNode;
    class AWS,EKS,NodeGroups,Storage default;
```

## Storage Configuration

vLLM requiere almacenamiento de alto rendimiento, ya que necesita cargar pesos de modelo grandes:

### FSx for Lustre Setup

FSx for Lustre es un sistema de archivos paralelo de alto rendimiento adecuado para cargar rápidamente pesos de modelo grandes:

```yaml
apiVersion: fsx.aws.k8s.io/v1beta1
kind: Lustre
metadata:
  name: vllm-models
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
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
parameters:
  fileSystemId: fs-0123456789abcdef0
  mountName: vllm-models
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

### Downloading Models from S3

Job para almacenar modelos de Hugging Face en S3 y descargarlos a FSx for Lustre:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: model-download
spec:
  template:
    spec:
      containers:
      - name: model-download
        image: huggingface/transformers:latest
        command:
        - python
        - -c
        - |
          from huggingface_hub import snapshot_download
          import os

          model_id = "meta-llama/Llama-3.1-70B-Instruct"
          dest_dir = "/models/llama-3.1-70b"

          os.makedirs(dest_dir, exist_ok=True)
          snapshot_download(repo_id=model_id, local_dir=dest_dir, token=os.environ["HF_TOKEN"])
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: huggingface-token
              key: token
        volumeMounts:
        - name: models-volume
          mountPath: /models
      restartPolicy: Never
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
```

## vLLM Deployment

### Deployment Architecture

El siguiente diagrama muestra dos arquitecturas principales para desplegar vLLM en EKS:

```mermaid
flowchart TD
    subgraph Deployment [vLLM Deployment Architecture]
        subgraph SingleNode [Single Node Deployment]
            Pod1[vLLM Pod]

            subgraph Pod1Components [Pod Components]
                Container1[vLLM Container]
                Volume1[Model Volume]
            end

            subgraph GPUs1 [GPU]
                GPU1[GPU 0]
                GPU2[GPU 1]
                GPU3["..."]
                GPU4[GPU 7]
            end
        end

        subgraph MultiNode [Multi-Node Deployment]
            Pod2[vLLM Pod 0]
            Pod3[vLLM Pod 1]

            subgraph Pod2Components [Pod 0 Components]
                Container2[vLLM Container]
                Volume2[Model Volume]
            end

            subgraph Pod3Components [Pod 1 Components]
                Container3[vLLM Container]
                Volume3[Model Volume]
            end

            subgraph GPUs2 [Node 0 GPU]
                GPU5[GPU 0]
                GPU6[GPU 1]
                GPU7["..."]
                GPU8[GPU 7]
            end

            subgraph GPUs3 [Node 1 GPU]
                GPU9[GPU 0]
                GPU10[GPU 1]
                GPU11["..."]
                GPU12[GPU 7]
            end

            NCCL[NCCL Communication]
        end

        subgraph Storage [Shared Storage]
            FSx[FSx for Lustre]
            S3[Amazon S3]
        end

        subgraph Networking [Networking]
            Service[Kubernetes Service]
            LoadBalancer[Load Balancer]
            Client[Client]
        end
    end

    Pod1 --> Pod1Components
    Pod1Components --> GPUs1
    Container1 --> Volume1

    Pod2 --> Pod2Components
    Pod3 --> Pod3Components
    Pod2Components --> GPUs2
    Pod3Components --> GPUs3
    Container2 --> Volume2
    Container3 --> Volume3

    Pod2 <--> NCCL
    Pod3 <--> NCCL

    Volume1 --> FSx
    Volume2 --> FSx
    Volume3 --> FSx
    FSx --> S3

    Client --> LoadBalancer
    LoadBalancer --> Service
    Service --> Pod1
    Service --> Pod2

    classDef podComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef containerComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef gpuComponent fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef storageComponent fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef networkComponent fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Pod1,Pod2,Pod3,Pod1Components,Pod2Components,Pod3Components podComponent;
    class Container1,Container2,Container3,Volume1,Volume2,Volume3,NCCL containerComponent;
    class GPU1,GPU2,GPU3,GPU4,GPU5,GPU6,GPU7,GPU8,GPU9,GPU10,GPU11,GPU12,GPUs1,GPUs2,GPUs3 gpuComponent;
    class FSx,S3,Storage storageComponent;
    class Service,LoadBalancer,Client,Networking networkComponent;
    class Deployment,SingleNode,MultiNode default;
```

### Single Node Deployment

Deployment que ejecuta vLLM en una sola GPU o en múltiples GPUs en un único node:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      containers:
      - name: vllm-server
        image: vllm/vllm-openai:latest
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        - --model=/models/llama-3.1-70b
        - --tensor-parallel-size=8
        - --gpu-memory-utilization=0.95
        - --max-num-batched-tokens=16384
        - --enable-prefix-caching
        - --enable-chunked-prefill
        - --port=8000
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 8
        volumeMounts:
        - name: models-volume
          mountPath: /models
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4,5,6,7"
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### Multi-Node Distributed Deployment

Método para distribuir modelos grandes entre múltiples nodes:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-config
data:
  hostfile: |
    vllm-inference-0 slots=8
    vllm-inference-1 slots=8
  run_server.sh: |
    #!/bin/bash

    RANK=$HOSTNAME
    if [[ $HOSTNAME == "vllm-inference-0" ]]; then
      RANK=0
    elif [[ $HOSTNAME == "vllm-inference-1" ]]; then
      RANK=1
    fi

    python -m vllm.entrypoints.openai.api_server \
      --model=/models/llama-3.1-70b \
      --tensor-parallel-size=16 \
      --pipeline-parallel-size=1 \
      --max-num-batched-tokens=8192 \
      --port=8000 \
      --host=0.0.0.0 \
      --master-addr=vllm-inference-0 \
      --master-port=29500 \
      --rank=$RANK
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vllm-inference
spec:
  serviceName: "vllm-inference"
  replicas: 2
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - vllm-inference
            topologyKey: kubernetes.io/hostname
      containers:
      - name: vllm-server
        image: vllm/vllm-openai:latest
        command:
        - bash
        - /config/run_server.sh
        ports:
        - containerPort: 8000
        - containerPort: 29500
        resources:
          limits:
            nvidia.com/gpu: 8
        volumeMounts:
        - name: models-volume
          mountPath: /models
        - name: config-volume
          mountPath: /config
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4,5,6,7"
        - name: NCCL_DEBUG
          value: "INFO"
        - name: NCCL_IB_DISABLE
          value: "0"
        - name: NCCL_IB_GID_INDEX
          value: "3"
        - name: NCCL_NET_GDR_LEVEL
          value: "5"
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
      - name: config-volume
        configMap:
          name: vllm-config
          defaultMode: 0755
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8000
    targetPort: 8000
    name: api
  - port: 29500
    targetPort: 29500
    name: nccl
  clusterIP: None
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference-lb
spec:
  selector:
    app: vllm-inference
    statefulset.kubernetes.io/pod-name: vllm-inference-0
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

## Performance Optimization

```mermaid
flowchart TD
    subgraph Optimization [Performance Optimization]
        subgraph GPUMemory [GPU Memory Optimization]
            MemoryUtil[GPU Memory Utilization Adjustment]
            Quantization[Quantization Application]
            SwapSpace[Swap Space Utilization]
        end

        subgraph Throughput [Throughput Optimization]
            BatchSize[Batch Size Adjustment]
            KVCache[KV Cache Optimization]
            TensorParallel[Tensor Parallel Processing]
        end

        subgraph NetworkOpt [Network Optimization]
            EFA[EFA Utilization]
            NCCLSettings[NCCL Settings Optimization]
            NodePlacement[Node Placement Optimization]
        end
    end

    MemoryUtil -->|--gpu-memory-utilization=0.9| Performance([Performance Improvement])
    Quantization -->|--quantization awq| Performance
    SwapSpace -->|--swap-space=16| Performance

    BatchSize -->|--max-num-batched-tokens=8192| Performance
    KVCache -->|--block-size=16| Performance
    TensorParallel -->|--tensor-parallel-size=8| Performance

    EFA -->|vpc.amazonaws.com/efa: 1| Performance
    NCCLSettings -->|NCCL_DEBUG=INFO| Performance
    NodePlacement -->|topology.kubernetes.io/zone| Performance

    classDef gpuMemNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef throughputNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef networkNode fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef performanceNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class MemoryUtil,Quantization,SwapSpace,GPUMemory gpuMemNode;
    class BatchSize,KVCache,TensorParallel,Throughput throughputNode;
    class EFA,NCCLSettings,NodePlacement,NetworkOpt networkNode;
    class Performance performanceNode;
    class Optimization default;
```

### GPU Memory Optimization

Métodos para optimizar el uso de memoria GPU de vLLM:

1. **GPU Memory Utilization Adjustment**:

```bash
--gpu-memory-utilization=0.9
```

2. **Quantization Application**:

```bash
--quantization awq
```

3. **Swap Space Utilization**:

```bash
--swap-space=16
```

### Throughput Optimization

Métodos para optimizar el throughput de vLLM:

1. **Batch Size Adjustment**:

```bash
--max-num-batched-tokens=8192
```

2. **KV Cache Optimization**:

```bash
--block-size=16
```

3. **Tensor Parallel Processing Adjustment**:

```bash
--tensor-parallel-size=8
```

### Network Optimization

Métodos para optimizar el rendimiento de red en deployments distribuidos:

1. **EFA (Elastic Fabric Adapter) Utilization**:

```yaml
resources:
  limits:
    nvidia.com/gpu: 8
    vpc.amazonaws.com/efa: 1
```

2. **NCCL Settings Optimization**:

```yaml
env:
- name: NCCL_DEBUG
  value: "INFO"
- name: NCCL_MIN_NCHANNELS
  value: "4"
- name: NCCL_SOCKET_IFNAME
  value: "^lo,docker"
- name: NCCL_ASYNC_ERROR_HANDLING
  value: "1"
```

3. **Node Placement Optimization**:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-west-2a
```

## Monitoring and Logging

```mermaid
flowchart TD
    subgraph Monitoring [Monitoring and Logging]
        subgraph MetricsCollection [Metrics Collection]
            vLLMMetrics[vLLM Metrics]
            GPUMetrics[GPU Metrics]
            KubeMetrics[Kubernetes Metrics]
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
            GPUUtilization[GPU Utilization]
            Throughput[Throughput]
            Latency[Latency]
            ErrorRate[Error Rate]
        end

        subgraph Alerts [Alerts]
            HighLatency[High Latency]
            LowThroughput[Low Throughput]
            GPUError[GPU Error]
            OOMError[Out of Memory Error]
        end
    end

    vLLMMetrics --> Prometheus
    GPUMetrics --> Prometheus
    KubeMetrics --> Prometheus

    Prometheus --> AlertManager
    Prometheus --> Grafana

    AlertManager --> Alerts
    Grafana --> Dashboards

    vLLMMetrics --> Fluentd
    Fluentd --> CloudWatch
    Fluentd --> ElasticSearch
    ElasticSearch --> Kibana

    classDef metricsNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef monitoringNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef loggingNode fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef dashboardNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef alertNode fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class vLLMMetrics,GPUMetrics,KubeMetrics,MetricsCollection metricsNode;
    class Prometheus,AlertManager,Grafana,MonitoringStack monitoringNode;
    class Fluentd,CloudWatch,ElasticSearch,Kibana,LoggingStack loggingNode;
    class GPUUtilization,Throughput,Latency,ErrorRate,Dashboards dashboardNode;
    class HighLatency,LowThroughput,GPUError,OOMError,Alerts alertNode;
    class Monitoring default;
```

### Prometheus Metrics

Método para recopilar métricas de Prometheus desde el servidor vLLM:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-metrics
  labels:
    app: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8001
    targetPort: 8001
    name: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: vllm-inference
  endpoints:
  - port: metrics
    interval: 15s
```

### Log Collection

Método para recopilar logs del servidor vLLM en CloudWatch:

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
      path /var/log/containers/vllm-*.log
      pos_file /var/log/fluentd-vllm.log.pos
      tag kubernetes.vllm.*
      read_from_head true
      <parse>
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.vllm.**>
      @type kubernetes_metadata
      @id filter_kube_metadata
    </filter>

    <match kubernetes.vllm.**>
      @type cloudwatch_logs
      log_group_name /eks/vllm/logs
      log_stream_name_key $.kubernetes.pod_name
      remove_log_stream_name_key true
      auto_create_stream true
      region us-west-2
    </match>
```

## Autoscaling

```mermaid
flowchart TD
    subgraph Autoscaling [Autoscaling]
        subgraph PodScaling [Pod Scaling]
            HPA[HorizontalPodAutoscaler]
            KEDA[KEDA]
            CustomMetrics[Custom Metrics]
        end

        subgraph NodeScaling [Node Scaling]
            Karpenter[Karpenter]
            ClusterAutoscaler[Cluster Autoscaler]
            SpotInstances[Spot Instances]
        end

        subgraph ScalingTriggers [Scaling Triggers]
            CPUUtilization[CPU Utilization]
            GPUUtilization[GPU Utilization]
            RequestsPerSecond[Requests Per Second]
            QueueLength[Queue Length]
        end
    end

    CPUUtilization --> HPA
    GPUUtilization --> CustomMetrics
    RequestsPerSecond --> KEDA
    QueueLength --> KEDA

    HPA --> Karpenter
    KEDA --> Karpenter
    CustomMetrics --> ClusterAutoscaler

    Karpenter --> SpotInstances

    classDef podScalingNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef nodeScalingNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef triggerNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class HPA,KEDA,CustomMetrics,PodScaling podScalingNode;
    class Karpenter,ClusterAutoscaler,SpotInstances,NodeScaling nodeScalingNode;
    class CPUUtilization,GPUUtilization,RequestsPerSecond,QueueLength,ScalingTriggers triggerNode;
    class Autoscaling default;
```

### HPA (Horizontal Pod Autoscaler)

Método para escalar automáticamente servidores vLLM según el volumen de solicitudes:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-inference
  minReplicas: 1
  maxReplicas: 5
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
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

### Node Autoscaling with Karpenter

Método para aprovisionar automáticamente GPU nodes:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: vllm-gpu
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.16xlarge
        - g5.12xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: vpc.amazonaws.com/efa
        operator: In
        values:
        - "true"
      nodeClassRef:
        name: vllm-gpu-class
  limits:
    nvidia.com/gpu: 32
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: vllm-gpu-class
spec:
  subnetSelector:
    karpenter.sh/discovery: vllm-cluster
  securityGroupSelector:
    karpenter.sh/discovery: vllm-cluster
  ttlSecondsAfterEmpty: 30
```

## Security Configuration

### Network Policy

Método para restringir el acceso de red a los servidores vLLM:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
spec:
  podSelector:
    matchLabels:
      app: vllm-inference
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  - from:
    - podSelector:
        matchLabels:
          app: vllm-inference
    ports:
    - protocol: TCP
      port: 29500
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: vllm-inference
    ports:
    - protocol: TCP
      port: 29500
  - to:
    ports:
    - protocol: TCP
      port: 443
```

### Security Context

Método para configurar el security context del container:

```yaml
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

## Client Integration

```mermaid
flowchart TD
    subgraph ClientIntegration [Client Integration]
        subgraph Gateway [API Gateway]
            Nginx[Nginx]
            APIGateway[API Gateway]
            Envoy[Envoy Proxy]
        end

        subgraph Clients [Clients]
            PythonClient[Python Client]
            JavaScriptClient[JavaScript Client]
            CurlClient[Curl Client]
        end

        subgraph Security [Security]
            Auth[Authentication]
            RateLimit[Rate Limiting]
            CORS[CORS]
        end

        subgraph Backend [Backend]
            vLLMService[vLLM Service]
            LoadBalancer[Load Balancer]
        end
    end

    Clients --> Gateway
    Gateway --> Security
    Security --> Backend

    PythonClient -->|HTTP Request| Nginx
    JavaScriptClient -->|HTTP Request| APIGateway
    CurlClient -->|HTTP Request| Envoy

    Nginx --> Auth
    APIGateway --> RateLimit
    Envoy --> CORS

    Auth --> LoadBalancer
    RateLimit --> LoadBalancer
    CORS --> LoadBalancer

    LoadBalancer --> vLLMService

    classDef gatewayNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef clientNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef securityNode fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef backendNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Nginx,APIGateway,Envoy,Gateway gatewayNode;
    class PythonClient,JavaScriptClient,CurlClient,Clients clientNode;
    class Auth,RateLimit,CORS,Security securityNode;
    class vLLMService,LoadBalancer,Backend backendNode;
    class ClientIntegration default;
```

### API Gateway

Método para desplegar un API gateway delante de los servidores vLLM:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: nginx:latest
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-config
          mountPath: /etc/nginx/conf.d
      volumes:
      - name: nginx-config
        configMap:
          name: nginx-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
data:
  default.conf: |
    server {
      listen 80;

      location /v1/ {
        proxy_pass http://vllm-inference:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
      }
    }
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Client Example

Método para enviar solicitudes al servidor vLLM usando un cliente Python:

```python
import requests
import json

url = "http://api-gateway/v1/completions"

payload = {
    "model": "llama-3.1-70b",
    "prompt": "Once upon a time",
    "max_tokens": 100,
    "temperature": 0.7
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))

print(response.json())
```

## Best Practices

### Resource Management

1. **Consider Memory Overhead**:
   - Asigna suficiente memoria CPU además de memoria GPU.
   - Se recomienda asignar aproximadamente el doble del tamaño del modelo en memoria CPU.

2. **CPU Core Allocation**:
   - Asigna al menos 4 CPU cores por GPU.
   - Es posible que se necesiten más CPU cores al usar paralelización de tensores.

3. **Node Selection**:
   - Selecciona los tipos de node adecuados según el tamaño del modelo.
   - Elige nodes con alto ancho de banda de memoria.

### High Availability

1. **Multi-Availability Zone Deployment**:
   - Despliega servidores vLLM en múltiples availability zones.
   - Asegura capacidad suficiente en cada availability zone.

2. **Load Balancing**:
   - Distribuye solicitudes entre múltiples instancias de servidor vLLM.
   - Configura session affinity para que las solicitudes del mismo usuario se enruten al mismo servidor.

3. **Failure Recovery**:
   - Configura health checks para detectar servidores fallidos.
   - Implementa mecanismos de recuperación automática.

### Cost Optimization

1. **Utilize Spot Instances**:
   - Usa Spot instances para reducir costos.
   - Adecuado para workloads tolerantes a interrupciones.

2. **Model Quantization**:
   - Aplica quantization INT8 o INT4 para reducir el uso de memoria.
   - Considera el equilibrio entre precisión y rendimiento.

3. **Autoscaling**:
   - Escala automáticamente los servidores según el volumen de solicitudes.
   - Reduce costos escalando los servidores hacia abajo durante períodos de inactividad.

## Conclusion

vLLM es el motor de inferencia LLM open-source con desarrollo más activo, y soporta de forma integral características esenciales para producción, incluidas Speculative Decoding, Prefix Caching, carga dinámica de LoRA, Structured Output y Tool Calling. Combinado con una selección adecuada de instancias GPU, almacenamiento de alto rendimiento, optimización de red y auto-scaling en EKS, puedes construir una plataforma de serving de LLM rentable y escalable. Para comparaciones con otros frameworks como SGLang y TGI, consulta el capítulo [Inference Frameworks](./04-inference-frameworks.md).

## References

- [Documentación oficial de vLLM](https://docs.vllm.ai/) - Documentación oficial de vLLM y guías de las características más recientes
- [AI on EKS](https://awslabs.github.io/ai-on-eks/) - Guía y ejemplos de AWS para desplegar workloads de AI/ML en EKS

## Quiz

Para comprobar lo que has aprendido en este capítulo, prueba el [cuestionario del tema](../quizzes/ai-ml/04-vllm-deployment-quiz.md).
