# Inference Frameworks for LLM Serving

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 25, 2026

This chapter covers advanced inference frameworks beyond vLLM for deploying Large Language Models (LLMs) on Amazon EKS. We explore NVIDIA NIM, NVIDIA Dynamo, AIBrix, Ray Serve integration, and AWS Neuron for Inferentia2.

## Inference Framework Landscape

The LLM inference ecosystem has evolved rapidly, with multiple frameworks addressing different aspects of production deployment. The following diagram shows the relationship between these frameworks:

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
            AIBrix[AIBrix]
            RayServe[Ray Serve]
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

    KubeRay --> RayServe
    Karpenter --> NVIDIAStack
    Karpenter --> OpenSource
    Karpenter --> AWSNative

    classDef nvidiaNode fill:#76B900,stroke:#333,stroke-width:1px,color:white;
    classDef ossNode fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsNode fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef orchNode fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class NIM,Dynamo,TensorRTLLM,Triton,NVIDIAStack nvidiaNode;
    class vLLM,SGLang,AIBrix,RayServe,OpenSource ossNode;
    class Neuron,Inferentia,SageMaker,AWSNative awsNode;
    class KubeRay,Karpenter,KEDA,Orchestration orchNode;
    class Ecosystem default;
```

### Framework Selection Guide

| Use Case | Recommended Framework | Why |
|----------|----------------------|-----|
| Enterprise production with NVIDIA GPUs | NVIDIA NIM | Optimized containers, support, monitoring |
| High-throughput with KV cache optimization | NVIDIA Dynamo | Disaggregated serving, intelligent routing |
| Multi-tenant with LoRA adapters | AIBrix | Native LoRA management, heterogeneous GPUs |
| Distributed inference at scale | Ray Serve + vLLM | Mature orchestration, auto-scaling |
| Cost optimization with AWS silicon | AWS Neuron + Inferentia2 | 40-70% cost reduction vs GPUs |
| Research and experimentation | vLLM standalone | Simple setup, active community |

## NVIDIA NIM

NVIDIA NIM (NVIDIA Inference Microservices) provides production-ready, containerized LLM deployments with optimized inference engines, built-in monitoring, and OpenAI-compatible APIs.

### NIM Architecture

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

### Prerequisites

Before deploying NIM, ensure you have:

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

### NIM Deployment with Karpenter

First, configure a Karpenter NodePool for GPU workloads:

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

Deploy NVIDIA NIM with Llama 3.1 70B:

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

### OpenAI-Compatible API Usage

NIM provides an OpenAI-compatible API:

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

Python client example:

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

### NIM Monitoring with Grafana

Deploy Grafana dashboards for NIM metrics:

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

### NIM Performance Metrics

Key metrics to monitor for NIM deployments:

| Metric | Description | Target |
|--------|-------------|--------|
| TTFT (Time to First Token) | Latency until first token is generated | < 500ms |
| ITL (Inter-Token Latency) | Time between consecutive tokens | < 50ms |
| Throughput | Tokens generated per second | Model-dependent |
| GPU Utilization | GPU compute utilization | 80-95% |
| KV Cache Utilization | KV cache memory usage | < 90% |
| Queue Depth | Pending requests in queue | < 100 |

### GenAI-Perf Benchmarking

Use NVIDIA GenAI-Perf for benchmarking:

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

NVIDIA Dynamo is an inference graph orchestration framework that enables disaggregated serving, separating prefill (prompt processing) from decode (token generation) phases for optimal resource utilization.

### Dynamo Architecture

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

### Key Concepts

1. **Disaggregated Serving**: Separates prefill (compute-intensive) from decode (memory-bandwidth-intensive) phases
2. **KV Cache Routing**: Intelligently routes requests based on KV cache locality
3. **Multi-Runtime Support**: Works with vLLM, SGLang, and TensorRT-LLM backends
4. **Heterogeneous GPU Support**: Different GPU types for prefill vs decode workloads

### Dynamo Deployment

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

Deploy Redis for KV cache metadata:

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

AIBrix is an open-source GenAI inference infrastructure that provides LLM gateway/routing, LoRA adapter management, application-tailored autoscaling, and heterogeneous GPU support.

### AIBrix Components

AIBrix consists of several key components:

1. **Gateway**: Intelligent request routing and load balancing
2. **LoRA Manager**: Dynamic LoRA adapter loading and management
3. **Autoscaler**: Workload-aware autoscaling for inference pods
4. **Model Registry**: Centralized model and adapter management

### AIBrix Deployment

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

### AIBrix LoRA Management

Register and manage LoRA adapters:

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

Configure workload-aware autoscaling:

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

## Ray Serve Integration

Ray Serve provides distributed serving capabilities with the KubeRay operator for Kubernetes-native deployment.

### KubeRay Operator Installation

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

### Ray Serve with vLLM Deployment

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

Configure auto-scaling for Ray Serve:

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

## AWS Neuron and Inferentia2

AWS Neuron SDK enables running LLMs on cost-effective Inferentia2 (inf2) instances, offering significant cost savings compared to GPU instances.

### Neuron SDK Overview

AWS Inferentia2 provides:
- Up to 70% lower cost compared to GPU instances
- High throughput for inference workloads
- Support for popular models: Llama 2/3, Mistral, Stable Diffusion

### Supported Instance Types

| Instance Type | Neuron Cores | Memory | Use Case |
|--------------|--------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | Small models (7B) |
| inf2.8xlarge | 2 | 32 GB | Medium models (7B with batching) |
| inf2.24xlarge | 6 | 96 GB | Large models (13B-70B) |
| inf2.48xlarge | 12 | 192 GB | Very large models (70B+) |

### Neuron Device Plugin Installation

```bash
# Install Neuron device plugin
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml

# Verify Neuron device plugin
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# Check Neuron devices on nodes
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

### Karpenter NodePool for Inferentia2

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

### vLLM on Neuron Deployment

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

### Model Compilation for Neuron

Before deploying, compile models for Neuron:

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

Kubernetes Job for compilation:

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

## Framework Comparison

### Feature Comparison Matrix

| Feature | NIM | Dynamo | AIBrix | vLLM | Ray+vLLM | Triton |
|---------|-----|--------|--------|------|----------|--------|
| **OpenAI API** | Yes | Yes | Yes | Yes | Yes | Via backend |
| **Tensor Parallelism** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Pipeline Parallelism** | Yes | Yes | No | Yes | Yes | Yes |
| **Disaggregated Serving** | No | Yes | No | No | No | No |
| **KV Cache Routing** | No | Yes | No | No | No | No |
| **LoRA Support** | Limited | Yes | Yes | Yes | Yes | Yes |
| **Multi-Model** | Yes | Yes | Yes | No | Yes | Yes |
| **Auto-Scaling** | Manual | Manual | Built-in | Manual | Built-in | Manual |
| **GPU Memory Opt** | High | High | Medium | High | High | High |
| **Multi-Backend** | TRT-LLM | vLLM/SGLang/TRT | vLLM/SGLang | - | - | Multiple |
| **Enterprise Support** | Yes | Yes | Community | Community | Community | Yes |
| **Neuron Support** | No | No | No | Yes | Yes | Yes |

### Performance Comparison (Llama 3.1 70B, 8x A100)

| Framework | TTFT (P99) | ITL (P99) | Throughput (tok/s) | Max Concurrency |
|-----------|------------|-----------|-------------------|-----------------|
| NIM | 450ms | 35ms | 2,800 | 128 |
| Dynamo | 380ms | 30ms | 3,200 | 256 |
| vLLM | 520ms | 40ms | 2,400 | 96 |
| Ray+vLLM | 550ms | 42ms | 2,300 | 128 |
| Triton+TRT-LLM | 400ms | 32ms | 3,000 | 128 |

### Cost Comparison (Monthly, 1M requests/day)

| Framework | Instance Type | Count | Monthly Cost | Cost/1K requests |
|-----------|--------------|-------|--------------|------------------|
| NIM | p4d.24xlarge | 2 | $48,000 | $0.80 |
| vLLM | p4d.24xlarge | 3 | $72,000 | $1.20 |
| Dynamo | p4d + g5 mix | 2+4 | $52,000 | $0.87 |
| Neuron | inf2.48xlarge | 4 | $28,000 | $0.47 |
| Ray+vLLM | g5.48xlarge | 4 | $38,000 | $0.63 |

## Best Practices

### Framework Selection Guidelines

1. **Choose NIM when**:
   - You need enterprise support and SLAs
   - Using NVIDIA GPUs exclusively
   - Require pre-optimized containers with minimal tuning
   - Grafana-based monitoring is preferred

2. **Choose Dynamo when**:
   - High throughput is critical
   - You can benefit from disaggregated serving
   - Using heterogeneous GPU types
   - KV cache locality matters for your workload

3. **Choose AIBrix when**:
   - Multi-tenant deployment with LoRA adapters
   - Need built-in autoscaling
   - Using mixed GPU types in the same cluster
   - Require flexible routing strategies

4. **Choose Ray Serve when**:
   - Already using Ray ecosystem
   - Need complex serving pipelines
   - Require Python-native deployment
   - Multi-model serving is needed

5. **Choose Neuron when**:
   - Cost optimization is primary goal
   - Workload fits inf2 constraints
   - Can accept compilation overhead
   - Running supported models (Llama, Mistral)

### Production Deployment Checklist

- [ ] Configure appropriate resource requests and limits
- [ ] Set up health checks (readiness, liveness, startup probes)
- [ ] Implement auto-scaling (HPA, Karpenter, or framework-native)
- [ ] Configure monitoring and alerting
- [ ] Set up log aggregation
- [ ] Implement request rate limiting
- [ ] Configure network policies
- [ ] Set up model caching (FSx, EBS, or S3)
- [ ] Test failover and recovery
- [ ] Document runbooks for common issues

## References

- [AI on EKS](https://awslabs.github.io/ai-on-eks/) - AWS guide and examples for deploying AI/ML workloads on EKS
- [NVIDIA NIM Documentation](https://docs.nvidia.com/nim/)
- [NVIDIA Dynamo GitHub](https://github.com/ai-dynamo/dynamo)
- [AIBrix GitHub](https://github.com/aibrix/aibrix)
- [KubeRay Documentation](https://docs.ray.io/en/latest/cluster/kubernetes/)
- [AWS Neuron Documentation](https://awsdocs-neuron.readthedocs-hosted.com/)

## Quiz

To test what you've learned in this chapter, try the [Inference Frameworks Quiz](../quizzes/ai-ml/04-inference-frameworks-quiz.md).
