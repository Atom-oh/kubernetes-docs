# 用于 LLM Serving 的推理框架

> **支持版本**: Kubernetes 1.31, 1.32, 1.33
> **最后更新**: April 9, 2026

本章介绍在 Amazon EKS 上部署 Large Language Models (LLMs) 时可用的多样化推理框架生态系统。我们将探讨 NVIDIA NIM、NVIDIA Dynamo、AIBrix、Ray Serve 集成和 AWS Neuron，以及快速增长的开源框架，包括 SGLang、HuggingFace TGI、Ollama 和 LiteLLM。

## 推理框架概览

LLM 推理生态系统发展迅速，多个框架分别解决生产部署中的不同方面。下图展示了这些框架之间的关系：

```mermaid
flowchart TD
    subgraph Ecosystem [LLM Inference Framework Ecosystem]
        subgraph NVIDIAStack [NVIDIA Stack]
            NIM[NVIDIA NIM]
            Dynamo[NVIDIA Dynamo]
            TensorRTLLM[TensorRT-LLM]
            Triton[Triton Inference Server]
        end

        subgraph OpenSource [Open Source Frameworks]
            vLLM[vLLM]
            SGLang[SGLang]
            TGI[HuggingFace TGI]
            AIBrix[AIBrix]
            RayServe[Ray Serve]
        end

        subgraph DevTools [Dev / Gateway Tools]
            Ollama[Ollama]
            LiteLLM[LiteLLM]
            LlamaCpp[llama.cpp]
        end

        subgraph AWSNative [AWS Native]
            Neuron[AWS Neuron SDK]
            Inferentia[Inferentia2]
            SageMaker[SageMaker]
        end

        subgraph Orchestration [Orchestration Layer]
            KubeRay[KubeRay Operator]
            Karpenter[Karpenter]
            KEDA[KEDA]
        end
    end

    NIM --> TensorRTLLM
    Dynamo --> vLLM
    Dynamo --> SGLang
    Dynamo --> TensorRTLLM
    RayServe --> vLLM
    AIBrix --> vLLM
    AIBrix --> SGLang

    Neuron --> Inferentia
    LiteLLM --> vLLM
    LiteLLM --> SGLang
    LiteLLM --> NIM
    Ollama --> LlamaCpp

    KubeRay --> RayServe
    Karpenter --> NVIDIAStack
    Karpenter --> OpenSource
    Karpenter --> AWSNative

    classDef nvidiaNode fill:#76B900,stroke:#333,stroke-width:1px,color:white;
    classDef ossNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef orchNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef devToolNode fill:#9B59B6,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class NIM,Dynamo,TensorRTLLM,Triton,NVIDIAStack nvidiaNode;
    class vLLM,SGLang,TGI,AIBrix,RayServe,OpenSource ossNode;
    class Neuron,Inferentia,SageMaker,AWSNative awsNode;
    class KubeRay,Karpenter,KEDA,Orchestration orchNode;
    class Ollama,LiteLLM,LlamaCpp,DevTools devToolNode;
    class Ecosystem default;
```

### 框架选择指南

| 使用场景 | 推荐框架 | 原因 |
|----------|----------------------|-----|
| 使用 NVIDIA GPU 的企业生产环境 | NVIDIA NIM | 优化容器、支持、监控 |
| 通过 KV cache 优化实现高吞吐 | NVIDIA Dynamo | 解耦 serving、智能路由 |
| 结构化输出、复杂提示流水线 | SGLang | RadixAttention、优化的结构化输出 |
| 使用 LoRA 适配器的多租户场景 | AIBrix | 原生 LoRA 管理、异构 GPU |
| 快速部署 HuggingFace 模型到生产 | HuggingFace TGI | HF 生态系统集成、易于设置 |
| 大规模分布式推理 | Ray Serve + vLLM | 成熟的编排、自动扩缩容 |
| 多 LLM provider 集成（网关） | LiteLLM | 100+ 模型 provider、成本跟踪 |
| 本地开发和边缘部署 | Ollama | 一键设置、GGUF 支持、轻量级 |
| 使用 AWS silicon 优化成本 | AWS Neuron + Inferentia2 | 相比 GPU 降低 40-70% 成本 |
| 研究和实验 | vLLM standalone | 设置简单、社区活跃 |

## NVIDIA NIM

NVIDIA NIM (NVIDIA Inference Microservices) 提供生产就绪、容器化的 LLM 部署，包含优化的推理引擎、内置监控和 OpenAI-compatible API。

### NIM 架构

```mermaid
flowchart TD
    subgraph NIMDeployment [NVIDIA NIM Deployment on EKS]
        subgraph Ingress [Ingress Layer]
            ALB[Application Load Balancer]
            NginxIngress[Nginx Ingress Controller]
        end

        subgraph NIMPods [NIM Pods]
            subgraph Pod1 [NIM Pod 1]
                NIMContainer1[NIM Container]
                TensorRTEngine1[TensorRT-LLM Engine]
                ModelCache1[Model Cache]
            end
            subgraph Pod2 [NIM Pod 2]
                NIMContainer2[NIM Container]
                TensorRTEngine2[TensorRT-LLM Engine]
                ModelCache2[Model Cache]
            end
        end

        subgraph GPUNodes [GPU Node Pool]
            Node1[p4d.24xlarge - 8x A100]
            Node2[g5.48xlarge - 8x A10G]
        end

        subgraph Monitoring [Monitoring Stack]
            Prometheus[(Prometheus)]
            Grafana[Grafana Dashboards]
            NIMMetrics[NIM Metrics Exporter]
        end

        subgraph Storage [Model Storage]
            NGC[NGC Catalog]
            S3[Amazon S3]
            FSx[FSx for Lustre]
        end
    end

    ALB --> NginxIngress
    NginxIngress --> Pod1
    NginxIngress --> Pod2

    Pod1 --> Node1
    Pod2 --> Node2

    NIMContainer1 --> TensorRTEngine1
    NIMContainer2 --> TensorRTEngine2

    TensorRTEngine1 --> ModelCache1
    TensorRTEngine2 --> ModelCache2

    ModelCache1 --> FSx
    ModelCache2 --> FSx
    FSx --> S3
    NGC --> FSx

    NIMMetrics --> Prometheus
    Prometheus --> Grafana

    classDef ingressNode fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef nimNode fill:#76B900,stroke:#333,stroke-width:1px,color:white;
    classDef gpuNode fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef monitorNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef storageNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class ALB,NginxIngress,Ingress ingressNode;
    class NIMContainer1,NIMContainer2,TensorRTEngine1,TensorRTEngine2,ModelCache1,ModelCache2,Pod1,Pod2,NIMPods nimNode;
    class Node1,Node2,GPUNodes gpuNode;
    class Prometheus,Grafana,NIMMetrics,Monitoring monitorNode;
    class NGC,S3,FSx,Storage storageNode;
    class NIMDeployment default;
```

### 前提条件

部署 NIM 之前，请确保你已具备：

```bash
# Verify GPU nodes are available
kubectl get nodes -l nvidia.com/gpu.present=true \
  -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu

# Install NVIDIA GPU Operator (if not already installed)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --set driver.enabled=true \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true

# Create NGC API key secret
kubectl create secret generic ngc-api-key \
  --from-literal=NGC_API_KEY='your-ngc-api-key'
```

### 使用 Karpenter 部署 NIM

首先，为 GPU 工作负载配置 Karpenter NodePool：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: nim-gpu-pool
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p4d.24xlarge
        - p4de.24xlarge
        - p5.48xlarge
        - g5.48xlarge
        - g5.24xlarge
        - g5.12xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: nim-gpu-class
      taints:
      - key: nvidia.com/gpu
        value: "true"
        effect: NoSchedule
  limits:
    nvidia.com/gpu: 64
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: nim-gpu-class
spec:
  amiFamily: AL2
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  instanceStorePolicy: RAID0
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 500Gi
      volumeType: gp3
      iops: 10000
      throughput: 500
      deleteOnTermination: true
  userData: |
    #!/bin/bash
    # Pre-pull NIM container images
    nvidia-container-toolkit --version
```

### NIM Deployment Manifest

使用 Llama 3.1 70B 部署 NVIDIA NIM：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nim-inference
---
apiVersion: v1
kind: Secret
metadata:
  name: ngc-credentials
  namespace: nim-inference
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: <base64-encoded-docker-config>
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nim-config
  namespace: nim-inference
data:
  NIM_MANIFEST_PROFILE: "vllm-bf16-tp8"
  NIM_MAX_MODEL_LEN: "32768"
  NIM_GPU_MEMORY_UTILIZATION: "0.90"
  NIM_ENABLE_CHUNKED_PREFILL: "true"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nim-llama-70b
  namespace: nim-inference
  labels:
    app: nim-inference
    model: llama-3-1-70b
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nim-inference
      model: llama-3-1-70b
  template:
    metadata:
      labels:
        app: nim-inference
        model: llama-3-1-70b
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      imagePullSecrets:
      - name: ngc-credentials
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: nim
        image: nvcr.io/nim/meta/llama-3.1-70b-instruct:1.2.0
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        envFrom:
        - configMapRef:
            name: nim-config
        env:
        - name: NGC_API_KEY
          valueFrom:
            secretKeyRef:
              name: ngc-api-key
              key: NGC_API_KEY
        - name: NIM_CACHE_PATH
          value: "/opt/nim/.cache"
        resources:
          limits:
            nvidia.com/gpu: 8
            memory: 700Gi
          requests:
            nvidia.com/gpu: 8
            memory: 600Gi
            cpu: "32"
        volumeMounts:
        - name: nim-cache
          mountPath: /opt/nim/.cache
        - name: shm
          mountPath: /dev/shm
        readinessProbe:
          httpGet:
            path: /v1/health/ready
            port: 8000
          initialDelaySeconds: 300
          periodSeconds: 10
          timeoutSeconds: 5
        livenessProbe:
          httpGet:
            path: /v1/health/live
            port: 8000
          initialDelaySeconds: 300
          periodSeconds: 30
          timeoutSeconds: 10
        startupProbe:
          httpGet:
            path: /v1/health/ready
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          failureThreshold: 20
      volumes:
      - name: nim-cache
        persistentVolumeClaim:
          claimName: nim-model-cache
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 64Gi
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: nim-inference
              topologyKey: kubernetes.io/hostname
---
apiVersion: v1
kind: Service
metadata:
  name: nim-inference
  namespace: nim-inference
  labels:
    app: nim-inference
spec:
  selector:
    app: nim-inference
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nim-model-cache
  namespace: nim-inference
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: gp3
  resources:
    requests:
      storage: 500Gi
```

### OpenAI-Compatible API 使用

NIM 提供 OpenAI-compatible API：

```bash
# Port forward for local testing
kubectl port-forward -n nim-inference svc/nim-inference 8000:8000

# Chat completion request
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta/llama-3.1-70b-instruct",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is Kubernetes?"}
    ],
    "temperature": 0.7,
    "max_tokens": 500,
    "stream": false
  }'

# Streaming response
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta/llama-3.1-70b-instruct",
    "messages": [
      {"role": "user", "content": "Explain containerization in 3 sentences."}
    ],
    "stream": true
  }'
```

Python 客户端示例：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://nim-inference.nim-inference.svc.cluster.local:8000/v1",
    api_key="not-needed"  # NIM doesn't require API key for internal calls
)

response = client.chat.completions.create(
    model="meta/llama-3.1-70b-instruct",
    messages=[
        {"role": "system", "content": "You are a Kubernetes expert."},
        {"role": "user", "content": "How does HPA work?"}
    ],
    temperature=0.7,
    max_tokens=1000
)

print(response.choices[0].message.content)
```

### 使用 Grafana 监控 NIM

为 NIM 指标部署 Grafana dashboards：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nim-grafana-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  nim-dashboard.json: |
    {
      "annotations": {
        "list": []
      },
      "editable": true,
      "fiscalYearStartMonth": 0,
      "graphTooltip": 0,
      "id": null,
      "links": [],
      "liveNow": false,
      "panels": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "color": {
                "mode": "palette-classic"
              },
              "custom": {
                "axisBorderShow": false,
                "axisCenteredZero": false,
                "axisColorMode": "text",
                "axisLabel": "",
                "axisPlacement": "auto",
                "barAlignment": 0,
                "drawStyle": "line",
                "fillOpacity": 10,
                "gradientMode": "none",
                "hideFrom": {
                  "legend": false,
                  "tooltip": false,
                  "viz": false
                },
                "insertNulls": false,
                "lineInterpolation": "linear",
                "lineWidth": 1,
                "pointSize": 5,
                "scaleDistribution": {
                  "type": "linear"
                },
                "showPoints": "auto",
                "spanNulls": false,
                "stacking": {
                  "group": "A",
                  "mode": "none"
                },
                "thresholdsStyle": {
                  "mode": "off"
                }
              },
              "mappings": [],
              "thresholds": {
                "mode": "absolute",
                "steps": [
                  {
                    "color": "green",
                    "value": null
                  }
                ]
              },
              "unit": "ms"
            },
            "overrides": []
          },
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "id": 1,
          "options": {
            "legend": {
              "calcs": ["mean", "max"],
              "displayMode": "table",
              "placement": "bottom",
              "showLegend": true
            },
            "tooltip": {
              "mode": "single",
              "sort": "none"
            }
          },
          "targets": [
            {
              "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
              },
              "expr": "histogram_quantile(0.99, sum(rate(nim_request_latency_bucket[5m])) by (le))",
              "legendFormat": "P99 Latency",
              "refId": "A"
            },
            {
              "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
              },
              "expr": "histogram_quantile(0.95, sum(rate(nim_request_latency_bucket[5m])) by (le))",
              "legendFormat": "P95 Latency",
              "refId": "B"
            },
            {
              "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
              },
              "expr": "histogram_quantile(0.50, sum(rate(nim_request_latency_bucket[5m])) by (le))",
              "legendFormat": "P50 Latency",
              "refId": "C"
            }
          ],
          "title": "Request Latency (TTFT + Generation)",
          "type": "timeseries"
        },
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "color": {
                "mode": "palette-classic"
              },
              "custom": {
                "axisBorderShow": false,
                "axisCenteredZero": false,
                "axisColorMode": "text",
                "axisLabel": "",
                "axisPlacement": "auto",
                "barAlignment": 0,
                "drawStyle": "line",
                "fillOpacity": 10,
                "gradientMode": "none",
                "hideFrom": {
                  "legend": false,
                  "tooltip": false,
                  "viz": false
                },
                "insertNulls": false,
                "lineInterpolation": "linear",
                "lineWidth": 1,
                "pointSize": 5,
                "scaleDistribution": {
                  "type": "linear"
                },
                "showPoints": "auto",
                "spanNulls": false,
                "stacking": {
                  "group": "A",
                  "mode": "none"
                },
                "thresholdsStyle": {
                  "mode": "off"
                }
              },
              "mappings": [],
              "thresholds": {
                "mode": "absolute",
                "steps": [
                  {
                    "color": "green",
                    "value": null
                  }
                ]
              },
              "unit": "tokens/s"
            },
            "overrides": []
          },
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "id": 2,
          "options": {
            "legend": {
              "calcs": ["mean", "max"],
              "displayMode": "table",
              "placement": "bottom",
              "showLegend": true
            },
            "tooltip": {
              "mode": "single",
              "sort": "none"
            }
          },
          "targets": [
            {
              "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
              },
              "expr": "sum(rate(nim_tokens_generated_total[5m]))",
              "legendFormat": "Output Tokens/s",
              "refId": "A"
            },
            {
              "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
              },
              "expr": "sum(rate(nim_tokens_processed_total[5m]))",
              "legendFormat": "Input Tokens/s",
              "refId": "B"
            }
          ],
          "title": "Token Throughput",
          "type": "timeseries"
        }
      ],
      "refresh": "5s",
      "schemaVersion": 38,
      "tags": ["nim", "llm", "inference"],
      "templating": {
        "list": []
      },
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "timepicker": {},
      "timezone": "",
      "title": "NVIDIA NIM Inference Metrics",
      "uid": "nim-metrics",
      "version": 1,
      "weekStart": ""
    }
```

### NIM 性能指标

NIM 部署需要监控的关键指标：

| 指标 | 描述 | 目标 |
|--------|-------------|--------|
| TTFT (Time to First Token) | 生成第一个 token 之前的延迟 | < 500ms |
| ITL (Inter-Token Latency) | 连续 token 之间的时间 | < 50ms |
| Throughput | 每秒生成的 token 数 | 取决于模型 |
| GPU Utilization | GPU 计算利用率 | 80-95% |
| KV Cache Utilization | KV cache 内存使用率 | < 90% |
| Queue Depth | 队列中的待处理请求数 | < 100 |

### GenAI-Perf 基准测试

使用 NVIDIA GenAI-Perf 进行基准测试：

```bash
# Install GenAI-Perf
pip install genai-perf

# Run benchmark against NIM endpoint
genai-perf \
  --endpoint-type chat \
  --service-kind openai \
  --url http://nim-inference.nim-inference.svc.cluster.local:8000/v1 \
  --model meta/llama-3.1-70b-instruct \
  --concurrency 16 \
  --input-sequence-length 512 \
  --output-sequence-length 256 \
  --num-prompts 100 \
  --profile-export-file nim-benchmark.json

# View results
genai-perf analyze nim-benchmark.json
```

## NVIDIA Dynamo

NVIDIA Dynamo 是一个推理图编排框架，可实现解耦 serving，将 prefill（提示处理）与 decode（token 生成）阶段分离，以获得最佳资源利用率。

### Dynamo 架构

```mermaid
flowchart TD
    subgraph DynamoCluster [NVIDIA Dynamo Deployment]
        subgraph Router [Dynamo Router]
            RouterPod[Router Pod]
            KVRouter[KV-Aware Router]
            LoadBalancer[Request Load Balancer]
        end

        subgraph PrefillPool [Prefill Workers]
            Prefill1[Prefill Worker 1]
            Prefill2[Prefill Worker 2]
            PrefillGPU1[8x A100 - High Memory BW]
            PrefillGPU2[8x A100 - High Memory BW]
        end

        subgraph DecodePool [Decode Workers]
            Decode1[Decode Worker 1]
            Decode2[Decode Worker 2]
            Decode3[Decode Worker 3]
            DecodeGPU1[4x A10G - Cost Optimized]
            DecodeGPU2[4x A10G - Cost Optimized]
            DecodeGPU3[4x A10G - Cost Optimized]
        end

        subgraph KVCache [Distributed KV Cache]
            KVStore[(KV Cache Store)]
            KVTransfer[KV Transfer Service]
        end

        subgraph Backends [Inference Backends]
            vLLMBackend[vLLM]
            SGLangBackend[SGLang]
            TRTLLMBackend[TensorRT-LLM]
        end
    end

    Client[Client Request] --> RouterPod
    RouterPod --> KVRouter
    KVRouter --> LoadBalancer

    LoadBalancer -->|Prefill Request| Prefill1
    LoadBalancer -->|Prefill Request| Prefill2

    Prefill1 --> PrefillGPU1
    Prefill2 --> PrefillGPU2

    Prefill1 -->|KV Cache| KVStore
    Prefill2 -->|KV Cache| KVStore

    KVStore --> KVTransfer
    KVTransfer --> Decode1
    KVTransfer --> Decode2
    KVTransfer --> Decode3

    Decode1 --> DecodeGPU1
    Decode2 --> DecodeGPU2
    Decode3 --> DecodeGPU3

    Prefill1 --> vLLMBackend
    Decode1 --> SGLangBackend
    Decode2 --> TRTLLMBackend

    classDef routerNode fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef prefillNode fill:#76B900,stroke:#333,stroke-width:1px,color:white;
    classDef decodeNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef kvNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef backendNode fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class RouterPod,KVRouter,LoadBalancer,Router routerNode;
    class Prefill1,Prefill2,PrefillGPU1,PrefillGPU2,PrefillPool prefillNode;
    class Decode1,Decode2,Decode3,DecodeGPU1,DecodeGPU2,DecodeGPU3,DecodePool decodeNode;
    class KVStore,KVTransfer,KVCache kvNode;
    class vLLMBackend,SGLangBackend,TRTLLMBackend,Backends backendNode;
    class DynamoCluster,Client default;
```

### 核心概念

1. **解耦 Serving**: 将 prefill（计算密集型）与 decode（内存带宽密集型）阶段分离
2. **KV Cache 路由**: 基于 KV cache 局部性智能路由请求
3. **多 Runtime 支持**: 可与 vLLM、SGLang 和 TensorRT-LLM backend 配合使用
4. **异构 GPU 支持**: 为 prefill 与 decode 工作负载使用不同的 GPU 类型

### Dynamo 部署

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dynamo
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: dynamo-config
  namespace: dynamo
data:
  config.yaml: |
    router:
      port: 8080
      kv_routing:
        enabled: true
        locality_weight: 0.7
        load_weight: 0.3
      load_balancing:
        algorithm: least_pending

    prefill:
      replicas: 2
      backend: vllm
      model: meta-llama/Llama-3.1-70B-Instruct
      tensor_parallel_size: 8
      max_num_seqs: 256
      max_model_len: 32768
      gpu_memory_utilization: 0.92

    decode:
      replicas: 4
      backend: vllm
      model: meta-llama/Llama-3.1-70B-Instruct
      tensor_parallel_size: 4
      max_num_seqs: 512
      gpu_memory_utilization: 0.88

    kv_cache:
      transfer_protocol: rdma  # or tcp
      compression: lz4
      max_cache_size_gb: 128
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dynamo-router
  namespace: dynamo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dynamo-router
  template:
    metadata:
      labels:
        app: dynamo-router
    spec:
      containers:
      - name: router
        image: nvcr.io/nvidia/dynamo-router:0.4.0
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: DYNAMO_CONFIG_PATH
          value: /config/config.yaml
        - name: PREFILL_SERVICE
          value: "dynamo-prefill.dynamo.svc.cluster.local:8000"
        - name: DECODE_SERVICE
          value: "dynamo-decode.dynamo.svc.cluster.local:8000"
        - name: KV_CACHE_SERVICE
          value: "dynamo-kv-cache.dynamo.svc.cluster.local:6379"
        volumeMounts:
        - name: config
          mountPath: /config
        resources:
          requests:
            cpu: "4"
            memory: 8Gi
          limits:
            cpu: "8"
            memory: 16Gi
      volumes:
      - name: config
        configMap:
          name: dynamo-config
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dynamo-prefill
  namespace: dynamo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dynamo-prefill
  template:
    metadata:
      labels:
        app: dynamo-prefill
        dynamo-role: prefill
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: prefill
        image: nvcr.io/nvidia/dynamo-worker:0.4.0
        args:
        - --role=prefill
        - --backend=vllm
        - --model=meta-llama/Llama-3.1-70B-Instruct
        - --tensor-parallel-size=8
        - --max-num-seqs=256
        - --gpu-memory-utilization=0.92
        - --enable-kv-export
        ports:
        - containerPort: 8000
          name: inference
        - containerPort: 8001
          name: kv-transfer
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        - name: KV_CACHE_HOST
          value: "dynamo-kv-cache.dynamo.svc.cluster.local"
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4,5,6,7"
        resources:
          limits:
            nvidia.com/gpu: 8
            memory: 600Gi
          requests:
            nvidia.com/gpu: 8
            memory: 500Gi
            cpu: "32"
        volumeMounts:
        - name: shm
          mountPath: /dev/shm
        - name: model-cache
          mountPath: /models
      volumes:
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 64Gi
      - name: model-cache
        persistentVolumeClaim:
          claimName: dynamo-model-cache
      nodeSelector:
        node.kubernetes.io/instance-type: p4d.24xlarge
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dynamo-decode
  namespace: dynamo
spec:
  replicas: 4
  selector:
    matchLabels:
      app: dynamo-decode
  template:
    metadata:
      labels:
        app: dynamo-decode
        dynamo-role: decode
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: decode
        image: nvcr.io/nvidia/dynamo-worker:0.4.0
        args:
        - --role=decode
        - --backend=vllm
        - --model=meta-llama/Llama-3.1-70B-Instruct
        - --tensor-parallel-size=4
        - --max-num-seqs=512
        - --gpu-memory-utilization=0.88
        - --enable-kv-import
        ports:
        - containerPort: 8000
          name: inference
        - containerPort: 8001
          name: kv-transfer
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        - name: KV_CACHE_HOST
          value: "dynamo-kv-cache.dynamo.svc.cluster.local"
        resources:
          limits:
            nvidia.com/gpu: 4
            memory: 200Gi
          requests:
            nvidia.com/gpu: 4
            memory: 150Gi
            cpu: "16"
        volumeMounts:
        - name: shm
          mountPath: /dev/shm
        - name: model-cache
          mountPath: /models
      volumes:
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 32Gi
      - name: model-cache
        persistentVolumeClaim:
          claimName: dynamo-model-cache
      nodeSelector:
        node.kubernetes.io/instance-type: g5.12xlarge
---
apiVersion: v1
kind: Service
metadata:
  name: dynamo-router
  namespace: dynamo
spec:
  selector:
    app: dynamo-router
  ports:
  - port: 8080
    targetPort: 8080
    name: http
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: dynamo-prefill
  namespace: dynamo
spec:
  selector:
    app: dynamo-prefill
  ports:
  - port: 8000
    targetPort: 8000
    name: inference
  - port: 8001
    targetPort: 8001
    name: kv-transfer
  clusterIP: None
---
apiVersion: v1
kind: Service
metadata:
  name: dynamo-decode
  namespace: dynamo
spec:
  selector:
    app: dynamo-decode
  ports:
  - port: 8000
    targetPort: 8000
    name: inference
  - port: 8001
    targetPort: 8001
    name: kv-transfer
  clusterIP: None
```

### Dynamo KV Cache Service

为 KV cache 元数据部署 Redis：

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: dynamo-kv-cache
  namespace: dynamo
spec:
  serviceName: dynamo-kv-cache
  replicas: 1
  selector:
    matchLabels:
      app: dynamo-kv-cache
  template:
    metadata:
      labels:
        app: dynamo-kv-cache
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        args:
        - --maxmemory
        - 32gb
        - --maxmemory-policy
        - allkeys-lru
        resources:
          requests:
            cpu: "2"
            memory: 34Gi
          limits:
            cpu: "4"
            memory: 36Gi
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: gp3
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: dynamo-kv-cache
  namespace: dynamo
spec:
  selector:
    app: dynamo-kv-cache
  ports:
  - port: 6379
    targetPort: 6379
  clusterIP: None
```

## AIBrix

AIBrix 是一个开源 GenAI 推理基础设施，提供 LLM 网关/路由、LoRA 适配器管理、面向应用的 autoscaling，以及异构 GPU 支持。

### AIBrix 组件

AIBrix 由几个关键组件组成：

1. **Gateway**: 智能请求路由和负载均衡
2. **LoRA Manager**: 动态 LoRA 适配器加载和管理
3. **Autoscaler**: 面向推理 Pod 的工作负载感知 autoscaling
4. **Model Registry**: 集中式模型和适配器管理

### AIBrix 部署

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aibrix
---
# AIBrix Gateway
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aibrix-gateway
  namespace: aibrix
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aibrix-gateway
  template:
    metadata:
      labels:
        app: aibrix-gateway
    spec:
      containers:
      - name: gateway
        image: ghcr.io/aibrix/aibrix-gateway:0.3.0
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: AIBRIX_MODEL_REGISTRY
          value: "aibrix-registry.aibrix.svc.cluster.local:8081"
        - name: AIBRIX_ROUTING_STRATEGY
          value: "least_load"  # Options: round_robin, least_load, hash
        - name: AIBRIX_ENABLE_LORA_ROUTING
          value: "true"
        - name: AIBRIX_MAX_QUEUE_SIZE
          value: "1000"
        resources:
          requests:
            cpu: "2"
            memory: 4Gi
          limits:
            cpu: "4"
            memory: 8Gi
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: aibrix-gateway
  namespace: aibrix
spec:
  selector:
    app: aibrix-gateway
  ports:
  - port: 8080
    targetPort: 8080
    name: http
  type: ClusterIP
---
# AIBrix Model Registry
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aibrix-registry
  namespace: aibrix
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aibrix-registry
  template:
    metadata:
      labels:
        app: aibrix-registry
    spec:
      containers:
      - name: registry
        image: ghcr.io/aibrix/aibrix-registry:0.3.0
        ports:
        - containerPort: 8081
          name: http
        env:
        - name: DATABASE_URL
          value: "postgresql://aibrix:password@aibrix-db.aibrix.svc.cluster.local:5432/aibrix"
        - name: S3_BUCKET
          value: "aibrix-models"
        - name: AWS_REGION
          value: "us-west-2"
        volumeMounts:
        - name: lora-cache
          mountPath: /cache
        resources:
          requests:
            cpu: "1"
            memory: 2Gi
          limits:
            cpu: "2"
            memory: 4Gi
      volumes:
      - name: lora-cache
        emptyDir:
          sizeLimit: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: aibrix-registry
  namespace: aibrix
spec:
  selector:
    app: aibrix-registry
  ports:
  - port: 8081
    targetPort: 8081
    name: http
  type: ClusterIP
---
# AIBrix vLLM Backend with LoRA support
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aibrix-vllm
  namespace: aibrix
spec:
  replicas: 2
  selector:
    matchLabels:
      app: aibrix-vllm
  template:
    metadata:
      labels:
        app: aibrix-vllm
      annotations:
        aibrix.io/gpu-type: "nvidia-a10g"
        aibrix.io/model: "meta-llama/Llama-3.1-8B-Instruct"
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: vllm
        image: vllm/vllm-openai:v0.6.0
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        args:
        - --model=meta-llama/Llama-3.1-8B-Instruct
        - --enable-lora
        - --max-loras=8
        - --max-lora-rank=32
        - --lora-modules
        - customer-support=/lora/customer-support
        - code-review=/lora/code-review
        - translation=/lora/translation
        - --tensor-parallel-size=1
        - --gpu-memory-utilization=0.85
        - --max-model-len=8192
        - --port=8000
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        - name: AIBRIX_REGISTRY_URL
          value: "http://aibrix-registry.aibrix.svc.cluster.local:8081"
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: 48Gi
          requests:
            nvidia.com/gpu: 1
            memory: 40Gi
            cpu: "8"
        volumeMounts:
        - name: shm
          mountPath: /dev/shm
        - name: lora-adapters
          mountPath: /lora
        - name: model-cache
          mountPath: /root/.cache/huggingface
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 10
      volumes:
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 16Gi
      - name: lora-adapters
        persistentVolumeClaim:
          claimName: aibrix-lora-pvc
      - name: model-cache
        persistentVolumeClaim:
          claimName: aibrix-model-cache
---
apiVersion: v1
kind: Service
metadata:
  name: aibrix-vllm
  namespace: aibrix
spec:
  selector:
    app: aibrix-vllm
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP
```

### AIBrix LoRA 管理

注册和管理 LoRA 适配器：

```bash
# Register a new LoRA adapter
curl -X POST http://aibrix-registry.aibrix.svc.cluster.local:8081/v1/lora/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer-support",
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_path": "s3://aibrix-models/lora/customer-support",
    "rank": 16,
    "alpha": 32,
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"]
  }'

# List registered LoRA adapters
curl http://aibrix-registry.aibrix.svc.cluster.local:8081/v1/lora/list

# Use LoRA adapter in inference request
curl -X POST http://aibrix-gateway.aibrix.svc.cluster.local:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_adapter": "customer-support",
    "messages": [
      {"role": "user", "content": "How do I reset my password?"}
    ],
    "max_tokens": 200
  }'
```

### AIBrix Autoscaler

配置工作负载感知 autoscaling：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aibrix-autoscaler-config
  namespace: aibrix
data:
  config.yaml: |
    autoscaler:
      enabled: true
      poll_interval: 30s

      scaling_policies:
        - name: default
          min_replicas: 2
          max_replicas: 10
          target_metrics:
            - name: requests_per_second
              target: 50
              window: 60s
            - name: gpu_utilization
              target: 80
              window: 120s
            - name: queue_depth
              target: 20
              window: 30s
          scale_up:
            stabilization_window: 60s
            step_size: 2
          scale_down:
            stabilization_window: 300s
            step_size: 1

        - name: high-priority
          min_replicas: 4
          max_replicas: 20
          target_metrics:
            - name: p99_latency_ms
              target: 1000
              window: 60s
          scale_up:
            stabilization_window: 30s
            step_size: 4
          scale_down:
            stabilization_window: 600s
            step_size: 1
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aibrix-autoscaler
  namespace: aibrix
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aibrix-autoscaler
  template:
    metadata:
      labels:
        app: aibrix-autoscaler
    spec:
      serviceAccountName: aibrix-autoscaler
      containers:
      - name: autoscaler
        image: ghcr.io/aibrix/aibrix-autoscaler:0.3.0
        env:
        - name: AIBRIX_NAMESPACE
          value: "aibrix"
        - name: PROMETHEUS_URL
          value: "http://prometheus.monitoring.svc.cluster.local:9090"
        volumeMounts:
        - name: config
          mountPath: /config
        resources:
          requests:
            cpu: "500m"
            memory: 512Mi
          limits:
            cpu: "1"
            memory: 1Gi
      volumes:
      - name: config
        configMap:
          name: aibrix-autoscaler-config
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: aibrix-autoscaler
  namespace: aibrix
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: aibrix-autoscaler
  namespace: aibrix
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "deployments/scale"]
  verbs: ["get", "list", "watch", "update", "patch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: aibrix-autoscaler
  namespace: aibrix
subjects:
- kind: ServiceAccount
  name: aibrix-autoscaler
  namespace: aibrix
roleRef:
  kind: Role
  name: aibrix-autoscaler
  apiGroup: rbac.authorization.k8s.io
```

## Ray Serve 集成

Ray Serve 通过 KubeRay operator 为 Kubernetes-native 部署提供分布式 serving 能力。

### KubeRay Operator 安装

```bash
# Add KubeRay Helm repository
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update

# Install KubeRay operator
helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace \
  --set image.tag=v1.1.0
```

### 使用 vLLM 的 Ray Serve 部署

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ray-serve
---
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-serve
  namespace: ray-serve
spec:
  serviceUnhealthySecondThreshold: 900
  deploymentUnhealthySecondThreshold: 300
  serveConfigV2: |
    applications:
    - name: vllm-app
      route_prefix: /
      import_path: serve_vllm:deployment
      deployments:
      - name: VLLMDeployment
        num_replicas: 2
        ray_actor_options:
          num_cpus: 8
          num_gpus: 1
        user_config:
          model: meta-llama/Llama-3.1-8B-Instruct
          tensor_parallel_size: 1
          max_model_len: 8192
          gpu_memory_utilization: 0.85
  rayClusterConfig:
    rayVersion: '2.9.0'
    headGroupSpec:
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
            - containerPort: 8000
              name: serve
            env:
            - name: HF_TOKEN
              valueFrom:
                secretKeyRef:
                  name: hf-token
                  key: token
            resources:
              limits:
                cpu: "4"
                memory: 16Gi
              requests:
                cpu: "2"
                memory: 8Gi
            volumeMounts:
            - name: serve-code
              mountPath: /home/ray/serve_vllm.py
              subPath: serve_vllm.py
          volumes:
          - name: serve-code
            configMap:
              name: vllm-serve-code
    workerGroupSpecs:
    - groupName: gpu-workers
      replicas: 2
      minReplicas: 1
      maxReplicas: 8
      rayStartParams:
        block: 'true'
      template:
        spec:
          tolerations:
          - key: nvidia.com/gpu
            operator: Exists
            effect: NoSchedule
          containers:
          - name: ray-worker
            image: rayproject/ray-ml:2.9.0-py310-gpu
            env:
            - name: HF_TOKEN
              valueFrom:
                secretKeyRef:
                  name: hf-token
                  key: token
            resources:
              limits:
                nvidia.com/gpu: 1
                cpu: "16"
                memory: 64Gi
              requests:
                nvidia.com/gpu: 1
                cpu: "8"
                memory: 48Gi
            volumeMounts:
            - name: shm
              mountPath: /dev/shm
            - name: model-cache
              mountPath: /home/ray/.cache/huggingface
          volumes:
          - name: shm
            emptyDir:
              medium: Memory
              sizeLimit: 16Gi
          - name: model-cache
            persistentVolumeClaim:
              claimName: ray-model-cache
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-serve-code
  namespace: ray-serve
data:
  serve_vllm.py: |
    from ray import serve
    from vllm.engine.arg_utils import AsyncEngineArgs
    from vllm.engine.async_llm_engine import AsyncLLMEngine
    from vllm.sampling_params import SamplingParams
    from fastapi import FastAPI
    from pydantic import BaseModel
    from typing import List, Optional
    import asyncio

    app = FastAPI()

    class ChatMessage(BaseModel):
        role: str
        content: str

    class ChatCompletionRequest(BaseModel):
        model: str
        messages: List[ChatMessage]
        temperature: Optional[float] = 0.7
        max_tokens: Optional[int] = 512
        stream: Optional[bool] = False

    @serve.deployment(
        ray_actor_options={"num_gpus": 1, "num_cpus": 8},
        autoscaling_config={
            "min_replicas": 1,
            "max_replicas": 8,
            "target_num_ongoing_requests_per_replica": 10,
            "upscale_delay_s": 30,
            "downscale_delay_s": 300,
        },
    )
    @serve.ingress(app)
    class VLLMDeployment:
        def __init__(self, model: str, tensor_parallel_size: int = 1,
                     max_model_len: int = 8192, gpu_memory_utilization: float = 0.85):
            engine_args = AsyncEngineArgs(
                model=model,
                tensor_parallel_size=tensor_parallel_size,
                max_model_len=max_model_len,
                gpu_memory_utilization=gpu_memory_utilization,
                trust_remote_code=True,
            )
            self.engine = AsyncLLMEngine.from_engine_args(engine_args)

        @app.post("/v1/chat/completions")
        async def chat_completions(self, request: ChatCompletionRequest):
            # Format messages into prompt
            prompt = self._format_chat_prompt(request.messages)

            sampling_params = SamplingParams(
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            request_id = str(id(request))
            results_generator = self.engine.generate(prompt, sampling_params, request_id)

            final_output = None
            async for request_output in results_generator:
                final_output = request_output

            return {
                "id": request_id,
                "object": "chat.completion",
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_output.outputs[0].text
                    },
                    "finish_reason": "stop"
                }]
            }

        def _format_chat_prompt(self, messages: List[ChatMessage]) -> str:
            prompt = ""
            for msg in messages:
                if msg.role == "system":
                    prompt += f"<|system|>\n{msg.content}</s>\n"
                elif msg.role == "user":
                    prompt += f"<|user|>\n{msg.content}</s>\n"
                elif msg.role == "assistant":
                    prompt += f"<|assistant|>\n{msg.content}</s>\n"
            prompt += "<|assistant|>\n"
            return prompt

        @app.get("/health")
        async def health(self):
            return {"status": "healthy"}

    deployment = VLLMDeployment.bind(
        model="meta-llama/Llama-3.1-8B-Instruct",
        tensor_parallel_size=1,
        max_model_len=8192,
        gpu_memory_utilization=0.85
    )
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-serve
  namespace: ray-serve
spec:
  selector:
    ray.io/serve: vllm-serve
  ports:
  - port: 8000
    targetPort: 8000
    name: serve
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ray-model-cache
  namespace: ray-serve
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: gp3
  resources:
    requests:
      storage: 200Gi
```

### Ray Serve Auto-Scaling

为 Ray Serve 配置 auto-scaling：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ray-worker-hpa
  namespace: ray-serve
spec:
  scaleTargetRef:
    apiVersion: ray.io/v1
    kind: RayCluster
    name: vllm-serve-raycluster
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: ray_serve_num_pending_requests
      target:
        type: AverageValue
        averageValue: "20"
  - type: External
    external:
      metric:
        name: ray_serve_deployment_replica_healthy
      target:
        type: Value
        value: "1"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 120
```

## SGLang

SGLang (Structured Generation Language) 是由 UC Berkeley 开发的高性能 LLM serving 框架，针对结构化输出生成和复杂提示流水线进行了优化。它是与 vLLM 并列增长最快的开源推理引擎之一。

### SGLang 核心技术

```mermaid
flowchart TD
    subgraph SGLangArch [SGLang Architecture]
        subgraph Frontend [Frontend]
            SGLangDSL[SGLang DSL]
            OpenAICompat[OpenAI Compatible API]
            NativeAPI[Native API]
        end

        subgraph Runtime [Runtime Engine]
            RadixAttention[RadixAttention]
            CompressedFSM[Compressed FSM Structured Output]
            ChunkedPrefill[Chunked Prefill]
            FlashInfer[FlashInfer Kernels]
        end

        subgraph Optimization [Optimization]
            KVCacheReuse[KV Cache Reuse]
            OverlapSchedule[Schedule Overlapping]
            DataParallel[Data Parallelism]
        end
    end

    SGLangDSL --> Runtime
    OpenAICompat --> Runtime
    RadixAttention --> KVCacheReuse
    CompressedFSM --> OverlapSchedule

    classDef featureNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef runtimeNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef optNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class SGLangDSL,OpenAICompat,NativeAPI,Frontend featureNode;
    class RadixAttention,CompressedFSM,ChunkedPrefill,FlashInfer,Runtime runtimeNode;
    class KVCacheReuse,OverlapSchedule,DataParallel,Optimization optNode;
    class SGLangArch default;
```

1. **RadixAttention**: 基于 radix tree 的 KV cache 复用，超越 prefix caching，可在部分重叠的 prompts 之间高效共享 cache。
2. **Compressed FSM Structured Output**: 压缩用于结构化输出（JSON Schema、regex 等）的有限状态机，与 vLLM 相比可带来最高 10 倍更快的结构化解码。
3. **FlashInfer Kernels**: 优化的 attention kernels，可在多种 GPU 架构上提供峰值性能。

### 在 EKS 上部署 SGLang

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sglang-server
  namespace: ai-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sglang-server
  template:
    metadata:
      labels:
        app: sglang-server
    spec:
      containers:
      - name: sglang
        image: lmsysorg/sglang:latest
        command:
        - python3
        - -m
        - sglang.launch_server
        - --model-path=meta-llama/Llama-3.1-8B-Instruct
        - --host=0.0.0.0
        - --port=30000
        - --tp=1
        - --mem-fraction-static=0.85
        ports:
        - containerPort: 30000
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: 48Gi
          requests:
            nvidia.com/gpu: 1
            memory: 32Gi
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: model-cache-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: sglang-server
  namespace: ai-inference
spec:
  selector:
    app: sglang-server
  ports:
  - port: 30000
    targetPort: 30000
  type: ClusterIP
```

### SGLang DSL 编程

SGLang 的关键差异化能力是其 DSL，可用于以编程方式组合复杂的 LLM 流水线：

```python
import sglang as sgl

@sgl.function
def multi_turn_qa(s, question_1, question_2):
    s += sgl.system("You are a helpful AI assistant.")
    s += sgl.user(question_1)
    s += sgl.assistant(sgl.gen("answer_1", max_tokens=256))
    s += sgl.user(question_2)
    s += sgl.assistant(sgl.gen("answer_2", max_tokens=256))

@sgl.function
def json_extraction(s, text):
    s += sgl.user(f"Extract information from the following text: {text}")
    s += sgl.assistant(
        sgl.gen("result", max_tokens=512,
                regex=r'\{"name": "[^"]+", "age": \d+, "city": "[^"]+"\}')
    )
```

### vLLM 与 SGLang 选择标准

| 标准 | vLLM | SGLang |
|----------|------|--------|
| **结构化输出速度** | 良好 | 优秀（最高 10 倍） |
| **社区/生态系统** | 非常大 | 快速增长 |
| **多轮流水线** | API 层级 | DSL 层级优化 |
| **Prefix caching** | 支持 | RadixAttention（更高效） |
| **生产稳定性** | 非常高 | 高 |
| **VLM 支持** | 广泛 | 广泛 |
| **Kubernetes 集成** | Helm chart | Docker image |

## HuggingFace TGI (Text Generation Inference)

HuggingFace TGI 是 HuggingFace 开发的生产就绪 LLM serving 框架，其关键优势是与 HuggingFace model hub 的原生集成。

### TGI 关键特性

- **Flash Attention 2 集成**: 面向高吞吐的优化 attention 操作
- **Continuous Batching**: 动态请求 batching，以最大化 GPU 利用率
- **Quantization 支持**: GPTQ、AWQ、bitsandbytes、EETQ、Marlin 等
- **Guidance 集成**: 基于 JSON schema 的结构化输出支持
- **HuggingFace Hub 集成**: 只需模型 ID 即可直接下载和 serving
- **基于 Rust 的高性能 Server**: 低内存开销和高并发

### 在 EKS 上部署 TGI

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tgi-server
  namespace: ai-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tgi-server
  template:
    metadata:
      labels:
        app: tgi-server
    spec:
      containers:
      - name: tgi
        image: ghcr.io/huggingface/text-generation-inference:latest
        args:
        - --model-id=meta-llama/Llama-3.1-8B-Instruct
        - --max-input-tokens=4096
        - --max-total-tokens=8192
        - --max-batch-prefill-tokens=16384
        - --quantize=awq
        - --port=8080
        ports:
        - containerPort: 8080
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: 48Gi
          requests:
            nvidia.com/gpu: 1
            memory: 32Gi
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 120
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 180
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: tgi-server
  namespace: ai-inference
spec:
  selector:
    app: tgi-server
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
```

### TGI API 使用示例

```bash
# Text generation
curl http://tgi-server:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "inputs": "The advantages of running AI workloads on Kubernetes are",
    "parameters": {
      "max_new_tokens": 200,
      "temperature": 0.7,
      "do_sample": true
    }
  }'

# OpenAI-compatible API (TGI v2+)
curl http://tgi-server:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "tgi",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

## Ollama

Ollama 是一个便于在本地运行 LLMs 的工具，非常适合开发/测试环境和边缘部署。借助 GGUF 格式的 quantized models，它甚至可以在消费级硬件上运行 LLMs。

### Ollama 特性

- **一键模型执行**: 使用单条命令下载并运行：`ollama run llama3.1`
- **GGUF Quantized Models**: 可在 CPU 和消费级 GPU 上高效运行
- **Modelfile**: 使用类似 Dockerfile 的语法定义自定义模型
- **OpenAI Compatible API**: 以最小改动与现有代码集成
- **轻量级 Container**: 易于在 Docker/Kubernetes 上部署

### 在 EKS 上部署 Ollama

在 EKS 上为开发/staging 环境或轻量级推理部署 Ollama：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: ai-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: 32Gi
          requests:
            nvidia.com/gpu: 1
            memory: 16Gi
        volumeMounts:
        - name: ollama-data
          mountPath: /root/.ollama
        lifecycle:
          postStart:
            exec:
              command:
              - /bin/sh
              - -c
              - |
                sleep 10 && ollama pull llama3.1:8b
      volumes:
      - name: ollama-data
        persistentVolumeClaim:
          claimName: ollama-data-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ollama
  namespace: ai-dev
spec:
  selector:
    app: ollama
  ports:
  - port: 11434
    targetPort: 11434
  type: ClusterIP
```

### Ollama 使用示例

```bash
# Download and run models
ollama pull llama3.1:8b
ollama pull deepseek-r1:8b
ollama pull qwen2.5:7b

# Chat API (OpenAI compatible)
curl http://ollama:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:8b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Create custom model with Modelfile
cat <<EOF > Modelfile
FROM llama3.1:8b
SYSTEM "You are a Kubernetes expert assistant."
PARAMETER temperature 0.3
PARAMETER num_ctx 4096
EOF
ollama create k8s-expert -f Modelfile
```

## LiteLLM

LiteLLM 是一个 proxy/gateway，可将 100+ LLM providers 统一到单个 OpenAI-compatible interface 中。当你需要在 EKS 上管理多个模型后端（vLLM、SGLang、NIM、cloud APIs 等）时，它非常有用。

### LiteLLM 关键特性

- **统一 API**: 面向 OpenAI、Anthropic、Google、vLLM、Ollama 和 100+ providers 的单一 interface
- **负载均衡**: 在多个模型实例之间进行智能路由
- **成本跟踪**: 按模型、团队和项目跟踪使用量和成本
- **速率限制**: 按 API key 和按用户管理速率限制
- **Fallback 策略**: 模型故障时自动 fallback

### 在 EKS 上部署 LiteLLM Proxy

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: litellm-config
  namespace: ai-gateway
data:
  config.yaml: |
    model_list:
      - model_name: gpt-4-equivalent
        litellm_params:
          model: openai/meta-llama/Llama-3.1-70B-Instruct
          api_base: http://vllm-inference.ai-inference:8000/v1
          api_key: dummy
      - model_name: gpt-4-equivalent
        litellm_params:
          model: openai/meta-llama/Llama-3.1-70B-Instruct
          api_base: http://sglang-server.ai-inference:30000/v1
          api_key: dummy
      - model_name: fast-model
        litellm_params:
          model: openai/meta-llama/Llama-3.1-8B-Instruct
          api_base: http://vllm-small.ai-inference:8000/v1
          api_key: dummy
      - model_name: dev-model
        litellm_params:
          model: ollama/llama3.1:8b
          api_base: http://ollama.ai-dev:11434
    
    litellm_settings:
      drop_params: true
      set_verbose: false
    
    router_settings:
      routing_strategy: least-busy
      num_retries: 3
      retry_after: 5
      allowed_fails: 2
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: litellm-proxy
  namespace: ai-gateway
spec:
  replicas: 2
  selector:
    matchLabels:
      app: litellm-proxy
  template:
    metadata:
      labels:
        app: litellm-proxy
    spec:
      containers:
      - name: litellm
        image: ghcr.io/berriai/litellm:main-latest
        args:
        - --config=/app/config.yaml
        - --port=4000
        ports:
        - containerPort: 4000
        resources:
          requests:
            cpu: "500m"
            memory: 512Mi
          limits:
            cpu: "2"
            memory: 2Gi
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
        readinessProbe:
          httpGet:
            path: /health
            port: 4000
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: litellm-config
---
apiVersion: v1
kind: Service
metadata:
  name: litellm-proxy
  namespace: ai-gateway
spec:
  selector:
    app: litellm-proxy
  ports:
  - port: 4000
    targetPort: 4000
  type: ClusterIP
```

### LiteLLM 使用示例

```python
from openai import OpenAI

# Access various backends through LiteLLM proxy
client = OpenAI(
    base_url="http://litellm-proxy.ai-gateway:4000/v1",
    api_key="sk-your-litellm-key"
)

# Auto load-balancing - distributes between vLLM and SGLang
response = client.chat.completions.create(
    model="gpt-4-equivalent",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Route to lightweight model
response = client.chat.completions.create(
    model="fast-model",
    messages=[{"role": "user", "content": "Simple question"}]
)
```

## AWS Neuron 和 Inferentia2

AWS Neuron SDK 支持在高性价比的 Inferentia2 (inf2) 实例上运行 LLMs，与 GPU 实例相比可显著节省成本。

### Neuron SDK 概述

AWS Inferentia2 提供：
- 与 GPU 实例相比成本最高降低 70%
- 面向推理工作负载的高吞吐
- 支持常用模型：Llama 2/3、Mistral、Stable Diffusion

### 支持的实例类型

| 实例类型 | Neuron Cores | 内存 | 使用场景 |
|--------------|--------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | 小模型（7B） |
| inf2.8xlarge | 2 | 32 GB | 中等模型（带 batching 的 7B） |
| inf2.24xlarge | 6 | 96 GB | 大模型（13B-70B） |
| inf2.48xlarge | 12 | 192 GB | 超大模型（70B+） |

### Neuron Device Plugin 安装

```bash
# Install Neuron device plugin
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml

# Verify Neuron device plugin
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# Check Neuron devices on nodes
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

### 面向 Inferentia2 的 Karpenter NodePool

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: neuron-pool
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - inf2.xlarge
        - inf2.8xlarge
        - inf2.24xlarge
        - inf2.48xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: neuron-class
      taints:
      - key: aws.amazon.com/neuron
        value: "true"
        effect: NoSchedule
  limits:
    aws.amazon.com/neuron: 24
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: neuron-class
spec:
  amiFamily: AL2
  amiSelectorTerms:
  - id: ami-xxxxxxxxxxxxxxxxx  # Neuron DLAMI
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 500Gi
      volumeType: gp3
      deleteOnTermination: true
  userData: |
    #!/bin/bash
    # Configure Neuron runtime
    source /opt/aws_neuron_venv_pytorch/bin/activate
```

### 在 Neuron 上部署 vLLM

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: neuron-inference
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-neuron
  namespace: neuron-inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vllm-neuron
  template:
    metadata:
      labels:
        app: vllm-neuron
    spec:
      tolerations:
      - key: aws.amazon.com/neuron
        operator: Exists
        effect: NoSchedule
      containers:
      - name: vllm-neuron
        image: public.ecr.aws/neuron/pytorch-inference-neuronx:2.1.2-neuronx-py310-sdk2.18.0
        command:
        - /bin/bash
        - -c
        - |
          source /opt/aws_neuron_venv_pytorch/bin/activate
          pip install vllm-neuron
          python -m vllm.entrypoints.openai.api_server \
            --model /models/llama-3-8b-neuron \
            --device neuron \
            --tensor-parallel-size 2 \
            --max-num-seqs 8 \
            --max-model-len 4096 \
            --port 8000
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: NEURON_RT_NUM_CORES
          value: "2"
        - name: NEURON_RT_VISIBLE_CORES
          value: "0,1"
        - name: NEURON_CC_FLAGS
          value: "--model-type transformer"
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        resources:
          limits:
            aws.amazon.com/neuron: 2
            memory: 32Gi
          requests:
            aws.amazon.com/neuron: 2
            memory: 24Gi
            cpu: "8"
        volumeMounts:
        - name: model-cache
          mountPath: /models
        - name: shm
          mountPath: /dev/shm
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 600
          periodSeconds: 30
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: neuron-model-cache
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 8Gi
      nodeSelector:
        node.kubernetes.io/instance-type: inf2.xlarge
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-neuron
  namespace: neuron-inference
spec:
  selector:
    app: vllm-neuron
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: neuron-model-cache
  namespace: neuron-inference
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: gp3
  resources:
    requests:
      storage: 200Gi
```

### 面向 Neuron 的模型编译

部署前，请为 Neuron 编译模型：

```python
# compile_model.py
import torch
import torch_neuronx
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "meta-llama/Llama-3.1-8B-Instruct"
output_dir = "/models/llama-3-8b-neuron"

# Load model
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True
)

# Compile for Neuron
# Configure for tensor parallelism
neuron_config = {
    "sequence_length": 4096,
    "batch_size": 1,
    "tp_degree": 2,  # Number of Neuron cores
    "amp": "bf16",
}

# Trace and compile
compiled_model = torch_neuronx.trace(
    model,
    example_inputs=torch.zeros((1, 4096), dtype=torch.long),
    compiler_args=["--model-type", "transformer"]
)

# Save compiled model
compiled_model.save(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"Model compiled and saved to {output_dir}")
```

用于编译的 Kubernetes Job：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: neuron-compile-llama
  namespace: neuron-inference
spec:
  template:
    spec:
      tolerations:
      - key: aws.amazon.com/neuron
        operator: Exists
        effect: NoSchedule
      containers:
      - name: compiler
        image: public.ecr.aws/neuron/pytorch-inference-neuronx:2.1.2-neuronx-py310-sdk2.18.0
        command:
        - /bin/bash
        - -c
        - |
          source /opt/aws_neuron_venv_pytorch/bin/activate
          pip install transformers accelerate
          python /scripts/compile_model.py
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        - name: NEURON_RT_NUM_CORES
          value: "2"
        resources:
          limits:
            aws.amazon.com/neuron: 2
            memory: 64Gi
            cpu: "16"
          requests:
            aws.amazon.com/neuron: 2
            memory: 48Gi
            cpu: "8"
        volumeMounts:
        - name: model-cache
          mountPath: /models
        - name: compile-script
          mountPath: /scripts
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: neuron-model-cache
      - name: compile-script
        configMap:
          name: neuron-compile-script
      restartPolicy: Never
      nodeSelector:
        node.kubernetes.io/instance-type: inf2.xlarge
  backoffLimit: 2
```

## 框架对比

### 特性对比矩阵

| 特性 | NIM | Dynamo | SGLang | vLLM | TGI | AIBrix | Ollama |
|---------|-----|--------|--------|------|-----|--------|--------|
| **OpenAI API** | 是 | 是 | 是 | 是 | 是 (v2+) | 是 | 是 |
| **Tensor Parallelism** | 是 | 是 | 是 | 是 | 是 | 是 | 否 |
| **Disaggregated Serving** | 否 | 是 | 否 | 否 | 否 | 否 | 否 |
| **Structured Output** | 有限 | 是 | 非常快 | 是 | 是 | 是 | 是 |
| **LoRA Support** | 有限 | 是 | 是 | 是 | 是 | 原生 | 是 |
| **VLM (Vision)** | 是 | 是 | 是 | 是 | 是 | 是 | 是 |
| **Speculative Decoding** | 是 | 是 | 是 | 是 | 是 | 否 | 否 |
| **FP8 Quantization** | 是 | 是 | 是 | 是 | 否 | 是 | 否 |
| **GGUF Models** | 否 | 否 | 否 | 否 | 否 | 否 | 是 |
| **CPU Inference** | 否 | 否 | 否 | 有限 | 否 | 否 | 是 |
| **Auto-Scaling** | 手动 | 手动 | 手动 | 手动 | 手动 | 内置 | 手动 |
| **Enterprise Support** | 是 | 是 | 社区 | 社区 | HuggingFace | 社区 | 社区 |

### 性能对比（Llama 3.1 70B，8x A100）

| 框架 | TTFT (P99) | ITL (P99) | 吞吐量 (tok/s) | 最大并发 |
|-----------|------------|-----------|-------------------|-----------------|
| NIM | 450ms | 35ms | 2,800 | 128 |
| Dynamo | 380ms | 30ms | 3,200 | 256 |
| SGLang | 480ms | 36ms | 2,700 | 128 |
| vLLM | 520ms | 40ms | 2,400 | 96 |
| TGI | 540ms | 38ms | 2,200 | 96 |
| Ray+vLLM | 550ms | 42ms | 2,300 | 128 |
| Triton+TRT-LLM | 400ms | 32ms | 3,000 | 128 |

> **注意**: 在结构化输出场景中，SGLang 的性能最高可比 vLLM 快 5-10 倍。上述数字适用于通用文本生成。

### 成本对比（每月，100 万请求/天）

| 框架 | 实例类型 | 数量 | 月度成本 | 每 1K 请求成本 |
|-----------|--------------|-------|--------------|------------------|
| NIM | p4d.24xlarge | 2 | $48,000 | $0.80 |
| vLLM | p4d.24xlarge | 3 | $72,000 | $1.20 |
| Dynamo | p4d + g5 mix | 2+4 | $52,000 | $0.87 |
| Neuron | inf2.48xlarge | 4 | $28,000 | $0.47 |
| Ray+vLLM | g5.48xlarge | 4 | $38,000 | $0.63 |

## 最佳实践

### 框架选择指南

1. **在以下情况选择 NIM**:
   - 你需要企业支持和 SLA
   - 仅使用 NVIDIA GPU
   - 需要预优化容器并尽量减少调优
   - 偏好基于 Grafana 的监控

2. **在以下情况选择 Dynamo**:
   - 高吞吐至关重要
   - 你可以从解耦 serving 中受益
   - 使用异构 GPU 类型
   - KV cache 局部性对你的工作负载很重要

3. **在以下情况选择 AIBrix**:
   - 使用 LoRA 适配器的多租户部署
   - 需要内置 autoscaling
   - 在同一 cluster 中使用混合 GPU 类型
   - 需要灵活的路由策略

4. **在以下情况选择 Ray Serve**:
   - 已在使用 Ray 生态系统
   - 需要复杂的 serving 流水线
   - 需要 Python-native 部署
   - 需要多模型 serving

5. **在以下情况选择 SGLang**:
   - 结构化输出（JSON、regex）是核心需求
   - 需要复杂的多轮提示流水线
   - Prefix caching 效率至关重要
   - 你需要类似 vLLM 的能力，但希望获得更好的结构化输出性能

6. **在以下情况选择 TGI**:
   - 快速生产部署 HuggingFace 模型
   - 需要稳定的基于 Rust 的 server
   - 使用 HuggingFace Enterprise Hub

7. **在以下情况选择 Ollama**:
   - 为开发/测试快速设置 LLM
   - 需要在没有 GPU 的 CPU 上运行 LLMs
   - 边缘设备或轻量级环境部署

8. **在以下情况选择 LiteLLM**:
   - 以统一方式管理多个 LLM backend
   - 需要按团队/项目进行成本跟踪
   - 需要 fallback 策略和负载均衡

9. **在以下情况选择 Neuron**:
   - 成本优化是首要目标
   - 工作负载符合 inf2 限制
   - 可以接受编译开销
   - 运行受支持的模型（Llama、Mistral）

### 生产部署检查清单

- [ ] 配置合适的 resource requests 和 limits
- [ ] 设置健康检查（readiness、liveness、startup probes）
- [ ] 实现 auto-scaling（HPA、Karpenter 或 framework-native）
- [ ] 配置监控和告警
- [ ] 设置日志聚合
- [ ] 实现请求速率限制
- [ ] 配置 network policies
- [ ] 设置模型缓存（FSx、EBS 或 S3）
- [ ] 测试 failover 和恢复
- [ ] 为常见问题编写 runbooks

## 参考资料

- [AI on EKS](https://awslabs.github.io/ai-on-eks/) - 用于在 EKS 上部署 AI/ML 工作负载的 AWS 指南和示例
- [NVIDIA NIM Documentation](https://docs.nvidia.com/nim/)
- [NVIDIA Dynamo GitHub](https://github.com/ai-dynamo/dynamo)
- [SGLang Official Documentation](https://sgl-project.github.io/) - SGLang 项目文档和基准测试
- [HuggingFace TGI GitHub](https://github.com/huggingface/text-generation-inference)
- [Ollama Official Site](https://ollama.com/) - Ollama 下载和模型库
- [LiteLLM Documentation](https://docs.litellm.ai/) - LiteLLM proxy 设置和集成指南
- [AIBrix GitHub](https://github.com/aibrix/aibrix)
- [KubeRay Documentation](https://docs.ray.io/en/latest/cluster/kubernetes/)
- [AWS Neuron Documentation](https://awsdocs-neuron.readthedocs-hosted.com/)

## 测验

要测试你在本章中学到的内容，请尝试[推理框架测验](../quizzes/ai-ml/04-inference-frameworks-quiz.md)。
