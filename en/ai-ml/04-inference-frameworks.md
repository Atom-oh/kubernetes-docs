# Inference Frameworks for LLM Serving

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: April 9, 2026

This chapter covers the diverse inference framework ecosystem for deploying Large Language Models (LLMs) on Amazon EKS. We explore NVIDIA NIM, NVIDIA Dynamo, AIBrix, Ray Serve integration, and AWS Neuron, as well as rapidly growing open-source frameworks including SGLang, HuggingFace TGI, Ollama, and LiteLLM.

## Inference Framework Landscape

The LLM inference ecosystem has evolved rapidly, with multiple frameworks addressing different aspects of production deployment. The following diagram shows the relationship between these frameworks:

![Landscape of LLM inference frameworks: LiteLLM routes requests to NIM, vLLM and SGLang, NVIDIA Dynamo orchestrates vLLM, SGLang and TensorRT-LLM, and Karpenter provisions nodes for the NVIDIA stack, open-source frameworks and Neuron/Inferentia2.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-0.html)

### Framework Selection Guide

| Use Case | Recommended Framework | Why |
|----------|----------------------|-----|
| Enterprise production with NVIDIA GPUs | NVIDIA NIM | Optimized containers, support, monitoring |
| High-throughput with KV cache optimization | NVIDIA Dynamo | Disaggregated serving, intelligent routing |
| Structured output, complex prompting pipelines | SGLang | RadixAttention, optimized structured output |
| Multi-tenant with LoRA adapters | AIBrix | Native LoRA management, heterogeneous GPUs |
| Quick HuggingFace model production deployment | HuggingFace TGI | HF ecosystem integration, easy setup |
| Distributed inference at scale | Ray Serve + vLLM | Mature orchestration, auto-scaling |
| Multi-LLM provider integration (gateway) | LiteLLM | 100+ model providers, cost tracking |
| Local development and edge deployment | Ollama | One-click setup, GGUF support, lightweight |
| Cost optimization with AWS silicon | AWS Neuron + Inferentia2 | 40-70% cost reduction vs GPUs |
| Research and experimentation | vLLM standalone | Simple setup, active community |

## NVIDIA NIM

NVIDIA NIM (NVIDIA Inference Microservices) provides production-ready, containerized LLM deployments with optimized inference engines, built-in monitoring, and OpenAI-compatible APIs.

### NIM Architecture

![NVIDIA NIM on EKS: requests pass through an ALB and Nginx Ingress to replicated NIM pods running a TensorRT-LLM engine on a GPU node pool, with a model cache backed by FSx for Lustre, S3 and NGC, and metrics flowing through Prometheus to Grafana.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-1.html)

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

![Architecture of NVIDIA Dynamo's disaggregated serving: a client request passes through the KV-aware Dynamo router to the prefill workers, whose KV cache flows through the distributed KV cache and KV transfer service to the decode workers, with both worker pools running on vLLM, SGLang, and TensorRT-LLM backends.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-2.html)

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

## SGLang

SGLang (Structured Generation Language) is a high-performance LLM serving framework developed at UC Berkeley, optimized for structured output generation and complex prompting pipelines. It is one of the fastest-growing open-source inference engines alongside vLLM.

### SGLang Core Technology

![Three-tier view of SGLang showing its frontend APIs feeding a RadixAttention runtime engine, which drives KV-cache reuse and schedule-overlap optimizations.](../.gitbook/assets/en-ai-ml-04-inference-frameworks-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-3.html)

1. **RadixAttention**: Radix tree-based KV cache reuse that goes beyond prefix caching, efficiently sharing cache across partially overlapping prompts.
2. **Compressed FSM Structured Output**: Compresses finite state machines for structured output (JSON Schema, regex, etc.), delivering up to 10x faster structured decoding vs vLLM.
3. **FlashInfer Kernels**: Optimized attention kernels delivering peak performance across GPU architectures.

### SGLang Deployment on EKS

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

### SGLang DSL Programming

SGLang's key differentiator is its DSL for programmatically composing complex LLM pipelines:

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

### vLLM vs SGLang Selection Criteria

| Criteria | vLLM | SGLang |
|----------|------|--------|
| **Structured output speed** | Good | Excellent (up to 10x) |
| **Community/ecosystem** | Very large | Rapidly growing |
| **Multi-turn pipelines** | API-level | DSL-level optimization |
| **Prefix caching** | Supported | RadixAttention (more efficient) |
| **Production stability** | Very high | High |
| **VLM support** | Broad | Broad |
| **Kubernetes integration** | Helm chart | Docker image |

## HuggingFace TGI (Text Generation Inference)

HuggingFace TGI is a production-ready LLM serving framework developed by HuggingFace, with native integration with the HuggingFace model hub as its key strength.

### TGI Key Features

- **Flash Attention 2 Integration**: Optimized attention operations for high throughput
- **Continuous Batching**: Dynamic request batching to maximize GPU utilization
- **Quantization Support**: GPTQ, AWQ, bitsandbytes, EETQ, Marlin and more
- **Guidance Integration**: JSON schema-based structured output support
- **HuggingFace Hub Integration**: Direct download and serving with just a model ID
- **Rust-Based High-Performance Server**: Low memory overhead and high concurrency

### TGI Deployment on EKS

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

### TGI API Usage Examples

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

Ollama is a tool for running LLMs locally with ease, ideal for development/testing environments and edge deployments. Using quantized models in GGUF format, it can run LLMs even on consumer-grade hardware.

### Ollama Features

- **One-Click Model Execution**: Download and run with a single command: `ollama run llama3.1`
- **GGUF Quantized Models**: Efficient execution on CPU and consumer GPUs
- **Modelfile**: Define custom models with Dockerfile-like syntax
- **OpenAI Compatible API**: Integrate with existing code with minimal changes
- **Lightweight Container**: Easy deployment on Docker/Kubernetes

### Ollama Deployment on EKS

Deploy Ollama on EKS for development/staging environments or lightweight inference:

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

### Ollama Usage Examples

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

LiteLLM is a proxy/gateway that unifies 100+ LLM providers into a single OpenAI-compatible interface. It is useful when managing multiple model backends (vLLM, SGLang, NIM, cloud APIs, etc.) on EKS.

### LiteLLM Key Features

- **Unified API**: Single interface for OpenAI, Anthropic, Google, vLLM, Ollama, and 100+ providers
- **Load Balancing**: Intelligent routing across multiple model instances
- **Cost Tracking**: Usage and cost tracking per model, team, and project
- **Rate Limiting**: Per API key and per user rate limit management
- **Fallback Strategy**: Automatic fallback on model failures

### LiteLLM Proxy Deployment on EKS

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

### LiteLLM Usage Examples

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

| Feature | NIM | Dynamo | SGLang | vLLM | TGI | AIBrix | Ollama |
|---------|-----|--------|--------|------|-----|--------|--------|
| **OpenAI API** | Yes | Yes | Yes | Yes | Yes (v2+) | Yes | Yes |
| **Tensor Parallelism** | Yes | Yes | Yes | Yes | Yes | Yes | No |
| **Disaggregated Serving** | No | Yes | No | No | No | No | No |
| **Structured Output** | Limited | Yes | Very fast | Yes | Yes | Yes | Yes |
| **LoRA Support** | Limited | Yes | Yes | Yes | Yes | Native | Yes |
| **VLM (Vision)** | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **Speculative Decoding** | Yes | Yes | Yes | Yes | Yes | No | No |
| **FP8 Quantization** | Yes | Yes | Yes | Yes | No | Yes | No |
| **GGUF Models** | No | No | No | No | No | No | Yes |
| **CPU Inference** | No | No | No | Limited | No | No | Yes |
| **Auto-Scaling** | Manual | Manual | Manual | Manual | Manual | Built-in | Manual |
| **Enterprise Support** | Yes | Yes | Community | Community | HuggingFace | Community | Community |

### Performance Comparison (Llama 3.1 70B, 8x A100)

| Framework | TTFT (P99) | ITL (P99) | Throughput (tok/s) | Max Concurrency |
|-----------|------------|-----------|-------------------|-----------------|
| NIM | 450ms | 35ms | 2,800 | 128 |
| Dynamo | 380ms | 30ms | 3,200 | 256 |
| SGLang | 480ms | 36ms | 2,700 | 128 |
| vLLM | 520ms | 40ms | 2,400 | 96 |
| TGI | 540ms | 38ms | 2,200 | 96 |
| Ray+vLLM | 550ms | 42ms | 2,300 | 128 |
| Triton+TRT-LLM | 400ms | 32ms | 3,000 | 128 |

> **Note**: SGLang delivers up to 5-10x faster performance than vLLM in structured output scenarios. The numbers above are for general text generation.

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

5. **Choose SGLang when**:
   - Structured output (JSON, regex) is a core requirement
   - Complex multi-turn prompting pipelines are needed
   - Prefix caching efficiency is critical
   - You need vLLM-like capabilities but better structured output performance

6. **Choose TGI when**:
   - Quick production deployment of HuggingFace models
   - Need a stable Rust-based server
   - Using HuggingFace Enterprise Hub

7. **Choose Ollama when**:
   - Quick LLM setup for development/testing
   - Need to run LLMs on CPU without GPU
   - Edge device or lightweight environment deployment

8. **Choose LiteLLM when**:
   - Managing multiple LLM backends in a unified way
   - Need per-team/project cost tracking
   - Require fallback strategies and load balancing

9. **Choose Neuron when**:
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
- [SGLang Official Documentation](https://sgl-project.github.io/) - SGLang project docs and benchmarks
- [HuggingFace TGI GitHub](https://github.com/huggingface/text-generation-inference)
- [Ollama Official Site](https://ollama.com/) - Ollama downloads and model library
- [LiteLLM Documentation](https://docs.litellm.ai/) - LiteLLM proxy setup and integration guide
- [AIBrix GitHub](https://github.com/aibrix/aibrix)
- [KubeRay Documentation](https://docs.ray.io/en/latest/cluster/kubernetes/)
- [AWS Neuron Documentation](https://awsdocs-neuron.readthedocs-hosted.com/)

## Quiz

To test what you've learned in this chapter, try the [Inference Frameworks Quiz](../quizzes/ai-ml/04-inference-frameworks-quiz.md).
