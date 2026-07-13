# Frameworks de inferencia para servir LLMs

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33
> **Última actualización**: April 9, 2026

Este capítulo cubre el diverso ecosistema de frameworks de inferencia para desplegar Large Language Models (LLMs) en Amazon EKS. Exploramos NVIDIA NIM, NVIDIA Dynamo, AIBrix, la integración con Ray Serve y AWS Neuron, así como frameworks de código abierto en rápido crecimiento, incluidos SGLang, HuggingFace TGI, Ollama y LiteLLM.

## Panorama de frameworks de inferencia

El ecosistema de inferencia de LLM ha evolucionado rápidamente, con múltiples frameworks que abordan diferentes aspectos del despliegue en producción. El siguiente diagrama muestra la relación entre estos frameworks:

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

### Guía de selección de frameworks

| Caso de uso | Framework recomendado | Por qué |
|----------|----------------------|-----|
| Producción empresarial con GPUs NVIDIA | NVIDIA NIM | Contenedores optimizados, soporte, monitoreo |
| Alto rendimiento con optimización de KV cache | NVIDIA Dynamo | Servicio desagregado, enrutamiento inteligente |
| Salida estructurada, pipelines de prompting complejos | SGLang | RadixAttention, salida estructurada optimizada |
| Multi-tenant con adaptadores LoRA | AIBrix | Gestión nativa de LoRA, GPUs heterogéneas |
| Despliegue rápido en producción de modelos HuggingFace | HuggingFace TGI | Integración con el ecosistema HF, configuración sencilla |
| Inferencia distribuida a escala | Ray Serve + vLLM | Orquestación madura, auto-scaling |
| Integración de múltiples proveedores de LLM (gateway) | LiteLLM | Más de 100 proveedores de modelos, seguimiento de costos |
| Desarrollo local y despliegue en edge | Ollama | Configuración con un clic, soporte GGUF, ligero |
| Optimización de costos con silicio de AWS | AWS Neuron + Inferentia2 | Reducción de costos del 40-70% frente a GPUs |
| Investigación y experimentación | vLLM standalone | Configuración simple, comunidad activa |

## NVIDIA NIM

NVIDIA NIM (NVIDIA Inference Microservices) proporciona despliegues de LLM en contenedores y listos para producción, con motores de inferencia optimizados, monitoreo integrado y APIs compatibles con OpenAI.

### Arquitectura de NIM

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

### Prerrequisitos

Antes de desplegar NIM, asegúrate de tener:

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

### Despliegue de NIM con Karpenter

Primero, configura un NodePool de Karpenter para cargas de trabajo de GPU:

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

### Manifiesto de despliegue de NIM

Despliega NVIDIA NIM con Llama 3.1 70B:

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

### Uso de API compatible con OpenAI

NIM proporciona una API compatible con OpenAI:

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

Ejemplo de cliente Python:

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

### Monitoreo de NIM con Grafana

Despliega dashboards de Grafana para métricas de NIM:

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

### Métricas de rendimiento de NIM

Métricas clave para monitorear despliegues de NIM:

| Métrica | Descripción | Objetivo |
|--------|-------------|--------|
| TTFT (Time to First Token) | Latencia hasta que se genera el primer token | < 500ms |
| ITL (Inter-Token Latency) | Tiempo entre tokens consecutivos | < 50ms |
| Throughput | Tokens generados por segundo | Depende del modelo |
| GPU Utilization | Utilización de cómputo de GPU | 80-95% |
| KV Cache Utilization | Uso de memoria de KV cache | < 90% |
| Queue Depth | Solicitudes pendientes en la cola | < 100 |

### Benchmarking con GenAI-Perf

Usa NVIDIA GenAI-Perf para benchmarking:

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

NVIDIA Dynamo es un framework de orquestación de grafos de inferencia que habilita el servicio desagregado, separando las fases de prefill (procesamiento de prompts) y decode (generación de tokens) para una utilización óptima de recursos.

### Arquitectura de Dynamo

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

### Conceptos clave

1. **Servicio desagregado**: Separa las fases de prefill (intensiva en cómputo) y decode (intensiva en ancho de banda de memoria)
2. **Enrutamiento de KV Cache**: Enruta solicitudes de forma inteligente según la localidad de KV cache
3. **Soporte multi-runtime**: Funciona con backends vLLM, SGLang y TensorRT-LLM
4. **Soporte de GPUs heterogéneas**: Diferentes tipos de GPU para cargas de trabajo de prefill frente a decode

### Despliegue de Dynamo

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

### Servicio de KV Cache de Dynamo

Despliega Redis para metadatos de KV cache:

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

AIBrix es una infraestructura de inferencia GenAI de código abierto que proporciona gateway/enrutamiento de LLM, gestión de adaptadores LoRA, autoscaling adaptado a aplicaciones y soporte para GPUs heterogéneas.

### Componentes de AIBrix

AIBrix consta de varios componentes clave:

1. **Gateway**: Enrutamiento inteligente de solicitudes y balanceo de carga
2. **LoRA Manager**: Carga y gestión dinámica de adaptadores LoRA
3. **Autoscaler**: Autoscaling consciente de la carga de trabajo para pods de inferencia
4. **Model Registry**: Gestión centralizada de modelos y adaptadores

### Despliegue de AIBrix

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

### Gestión de LoRA en AIBrix

Registra y gestiona adaptadores LoRA:

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

### Autoscaler de AIBrix

Configura autoscaling consciente de la carga de trabajo:

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

## Integración de Ray Serve

Ray Serve proporciona capacidades de servicio distribuido con el operador KubeRay para despliegue nativo de Kubernetes.

### Instalación del operador KubeRay

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

### Ray Serve con despliegue de vLLM

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

### Auto-scaling de Ray Serve

Configura auto-scaling para Ray Serve:

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

SGLang (Structured Generation Language) es un framework de alto rendimiento para servir LLM desarrollado en UC Berkeley, optimizado para la generación de salida estructurada y pipelines de prompting complejos. Es uno de los motores de inferencia de código abierto de más rápido crecimiento junto con vLLM.

### Tecnología central de SGLang

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

1. **RadixAttention**: Reutilización de KV cache basada en árboles radix que va más allá del caching de prefijos, compartiendo cache de forma eficiente entre prompts parcialmente superpuestos.
2. **Compressed FSM Structured Output**: Comprime máquinas de estados finitos para salida estructurada (JSON Schema, regex, etc.), ofreciendo decodificación estructurada hasta 10 veces más rápida frente a vLLM.
3. **FlashInfer Kernels**: Kernels de atención optimizados que ofrecen rendimiento máximo en arquitecturas de GPU.

### Despliegue de SGLang en EKS

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

### Programación con DSL de SGLang

El diferenciador clave de SGLang es su DSL para componer programáticamente pipelines de LLM complejos:

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

### Criterios de selección entre vLLM y SGLang

| Criterio | vLLM | SGLang |
|----------|------|--------|
| **Velocidad de salida estructurada** | Buena | Excelente (hasta 10x) |
| **Comunidad/ecosistema** | Muy grande | En rápido crecimiento |
| **Pipelines multi-turn** | Nivel de API | Optimización a nivel de DSL |
| **Prefix caching** | Compatible | RadixAttention (más eficiente) |
| **Estabilidad en producción** | Muy alta | Alta |
| **Soporte VLM** | Amplio | Amplio |
| **Integración con Kubernetes** | Helm chart | Imagen Docker |

## HuggingFace TGI (Text Generation Inference)

HuggingFace TGI es un framework de servicio de LLM listo para producción desarrollado por HuggingFace, con integración nativa con el hub de modelos de HuggingFace como su fortaleza principal.

### Características clave de TGI

- **Integración con Flash Attention 2**: Operaciones de atención optimizadas para alto throughput
- **Continuous Batching**: Batching dinámico de solicitudes para maximizar la utilización de GPU
- **Soporte de cuantización**: GPTQ, AWQ, bitsandbytes, EETQ, Marlin y más
- **Integración con Guidance**: Soporte de salida estructurada basada en JSON schema
- **Integración con HuggingFace Hub**: Descarga y servicio directos solo con un ID de modelo
- **Servidor de alto rendimiento basado en Rust**: Baja sobrecarga de memoria y alta concurrencia

### Despliegue de TGI en EKS

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

### Ejemplos de uso de la API de TGI

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

Ollama es una herramienta para ejecutar LLMs localmente con facilidad, ideal para entornos de desarrollo/pruebas y despliegues en edge. Con modelos cuantizados en formato GGUF, puede ejecutar LLMs incluso en hardware de consumo.

### Características de Ollama

- **Ejecución de modelos con un clic**: Descarga y ejecuta con un solo comando: `ollama run llama3.1`
- **Modelos cuantizados GGUF**: Ejecución eficiente en CPU y GPUs de consumo
- **Modelfile**: Define modelos personalizados con sintaxis similar a Dockerfile
- **API compatible con OpenAI**: Integra con código existente con cambios mínimos
- **Contenedor ligero**: Despliegue sencillo en Docker/Kubernetes

### Despliegue de Ollama en EKS

Despliega Ollama en EKS para entornos de desarrollo/staging o inferencia ligera:

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

### Ejemplos de uso de Ollama

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

LiteLLM es un proxy/gateway que unifica más de 100 proveedores de LLM en una única interfaz compatible con OpenAI. Es útil al gestionar múltiples backends de modelos (vLLM, SGLang, NIM, APIs en la nube, etc.) en EKS.

### Características clave de LiteLLM

- **API unificada**: Una única interfaz para OpenAI, Anthropic, Google, vLLM, Ollama y más de 100 proveedores
- **Balanceo de carga**: Enrutamiento inteligente entre múltiples instancias de modelos
- **Seguimiento de costos**: Seguimiento de uso y costos por modelo, equipo y proyecto
- **Limitación de tasa**: Gestión de límites de tasa por clave de API y por usuario
- **Estrategia de fallback**: Fallback automático ante fallos de modelos

### Despliegue del proxy LiteLLM en EKS

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

### Ejemplos de uso de LiteLLM

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

## AWS Neuron e Inferentia2

AWS Neuron SDK permite ejecutar LLMs en instancias Inferentia2 (inf2) rentables, ofreciendo ahorros de costo significativos en comparación con instancias GPU.

### Descripción general de Neuron SDK

AWS Inferentia2 proporciona:
- Hasta un 70% menos de costo en comparación con instancias GPU
- Alto throughput para cargas de trabajo de inferencia
- Soporte para modelos populares: Llama 2/3, Mistral, Stable Diffusion

### Tipos de instancias compatibles

| Tipo de instancia | Neuron Cores | Memoria | Caso de uso |
|--------------|--------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | Modelos pequeños (7B) |
| inf2.8xlarge | 2 | 32 GB | Modelos medianos (7B con batching) |
| inf2.24xlarge | 6 | 96 GB | Modelos grandes (13B-70B) |
| inf2.48xlarge | 12 | 192 GB | Modelos muy grandes (70B+) |

### Instalación del Neuron Device Plugin

```bash
# Install Neuron device plugin
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml

# Verify Neuron device plugin
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# Check Neuron devices on nodes
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

### NodePool de Karpenter para Inferentia2

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

### Despliegue de vLLM en Neuron

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

### Compilación de modelos para Neuron

Antes de desplegar, compila los modelos para Neuron:

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

Job de Kubernetes para compilación:

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

## Comparación de frameworks

### Matriz de comparación de características

| Característica | NIM | Dynamo | SGLang | vLLM | TGI | AIBrix | Ollama |
|---------|-----|--------|--------|------|-----|--------|--------|
| **API de OpenAI** | Sí | Sí | Sí | Sí | Sí (v2+) | Sí | Sí |
| **Tensor Parallelism** | Sí | Sí | Sí | Sí | Sí | Sí | No |
| **Servicio desagregado** | No | Sí | No | No | No | No | No |
| **Salida estructurada** | Limitada | Sí | Muy rápida | Sí | Sí | Sí | Sí |
| **Soporte LoRA** | Limitado | Sí | Sí | Sí | Sí | Nativo | Sí |
| **VLM (Vision)** | Sí | Sí | Sí | Sí | Sí | Sí | Sí |
| **Speculative Decoding** | Sí | Sí | Sí | Sí | Sí | No | No |
| **Cuantización FP8** | Sí | Sí | Sí | Sí | No | Sí | No |
| **Modelos GGUF** | No | No | No | No | No | No | Sí |
| **Inferencia en CPU** | No | No | No | Limitada | No | No | Sí |
| **Auto-scaling** | Manual | Manual | Manual | Manual | Manual | Integrado | Manual |
| **Soporte empresarial** | Sí | Sí | Comunidad | Comunidad | HuggingFace | Comunidad | Comunidad |

### Comparación de rendimiento (Llama 3.1 70B, 8x A100)

| Framework | TTFT (P99) | ITL (P99) | Throughput (tok/s) | Concurrencia máxima |
|-----------|------------|-----------|-------------------|-----------------|
| NIM | 450ms | 35ms | 2,800 | 128 |
| Dynamo | 380ms | 30ms | 3,200 | 256 |
| SGLang | 480ms | 36ms | 2,700 | 128 |
| vLLM | 520ms | 40ms | 2,400 | 96 |
| TGI | 540ms | 38ms | 2,200 | 96 |
| Ray+vLLM | 550ms | 42ms | 2,300 | 128 |
| Triton+TRT-LLM | 400ms | 32ms | 3,000 | 128 |

> **Nota**: SGLang ofrece un rendimiento hasta 5-10 veces más rápido que vLLM en escenarios de salida estructurada. Las cifras anteriores son para generación de texto general.

### Comparación de costos (mensual, 1 millón de solicitudes/día)

| Framework | Tipo de instancia | Cantidad | Costo mensual | Costo/1K solicitudes |
|-----------|--------------|-------|--------------|------------------|
| NIM | p4d.24xlarge | 2 | $48,000 | $0.80 |
| vLLM | p4d.24xlarge | 3 | $72,000 | $1.20 |
| Dynamo | combinación p4d + g5 | 2+4 | $52,000 | $0.87 |
| Neuron | inf2.48xlarge | 4 | $28,000 | $0.47 |
| Ray+vLLM | g5.48xlarge | 4 | $38,000 | $0.63 |

## Buenas prácticas

### Directrices de selección de frameworks

1. **Elige NIM cuando**:
   - Necesites soporte empresarial y SLAs
   - Uses GPUs NVIDIA exclusivamente
   - Requieras contenedores preoptimizados con ajuste mínimo
   - Se prefiera monitoreo basado en Grafana

2. **Elige Dynamo cuando**:
   - El alto throughput sea crítico
   - Puedas beneficiarte del servicio desagregado
   - Uses tipos de GPU heterogéneos
   - La localidad de KV cache sea importante para tu carga de trabajo

3. **Elige AIBrix cuando**:
   - Despliegue multi-tenant con adaptadores LoRA
   - Necesites autoscaling integrado
   - Uses tipos de GPU mixtos en el mismo cluster
   - Requieras estrategias de enrutamiento flexibles

4. **Elige Ray Serve cuando**:
   - Ya uses el ecosistema Ray
   - Necesites pipelines de servicio complejos
   - Requieras despliegue nativo de Python
   - Se necesite servicio multi-modelo

5. **Elige SGLang cuando**:
   - La salida estructurada (JSON, regex) sea un requisito central
   - Se necesiten pipelines de prompting multi-turn complejos
   - La eficiencia de prefix caching sea crítica
   - Necesites capacidades similares a vLLM pero con mejor rendimiento de salida estructurada

6. **Elige TGI cuando**:
   - Despliegue rápido en producción de modelos HuggingFace
   - Necesites un servidor estable basado en Rust
   - Uses HuggingFace Enterprise Hub

7. **Elige Ollama cuando**:
   - Configuración rápida de LLM para desarrollo/pruebas
   - Necesites ejecutar LLMs en CPU sin GPU
   - Despliegue en dispositivo edge o entorno ligero

8. **Elige LiteLLM cuando**:
   - Gestiones múltiples backends de LLM de forma unificada
   - Necesites seguimiento de costos por equipo/proyecto
   - Requieras estrategias de fallback y balanceo de carga

9. **Elige Neuron cuando**:
   - La optimización de costos sea el objetivo principal
   - La carga de trabajo encaje con las restricciones de inf2
   - Puedas aceptar la sobrecarga de compilación
   - Ejecutes modelos compatibles (Llama, Mistral)

### Checklist de despliegue en producción

- [ ] Configurar requests y limits de recursos apropiados
- [ ] Configurar health checks (readiness, liveness, startup probes)
- [ ] Implementar auto-scaling (HPA, Karpenter o nativo del framework)
- [ ] Configurar monitoreo y alertas
- [ ] Configurar agregación de logs
- [ ] Implementar limitación de tasa de solicitudes
- [ ] Configurar network policies
- [ ] Configurar caching de modelos (FSx, EBS o S3)
- [ ] Probar failover y recuperación
- [ ] Documentar runbooks para problemas comunes

## Referencias

- [AI on EKS](https://awslabs.github.io/ai-on-eks/) - Guía y ejemplos de AWS para desplegar cargas de trabajo AI/ML en EKS
- [Documentación de NVIDIA NIM](https://docs.nvidia.com/nim/)
- [GitHub de NVIDIA Dynamo](https://github.com/ai-dynamo/dynamo)
- [Documentación oficial de SGLang](https://sgl-project.github.io/) - Documentación y benchmarks del proyecto SGLang
- [GitHub de HuggingFace TGI](https://github.com/huggingface/text-generation-inference)
- [Sitio oficial de Ollama](https://ollama.com/) - Descargas de Ollama y biblioteca de modelos
- [Documentación de LiteLLM](https://docs.litellm.ai/) - Guía de configuración e integración del proxy LiteLLM
- [GitHub de AIBrix](https://github.com/aibrix/aibrix)
- [Documentación de KubeRay](https://docs.ray.io/en/latest/cluster/kubernetes/)
- [Documentación de AWS Neuron](https://awsdocs-neuron.readthedocs-hosted.com/)

## Quiz

Para comprobar lo que has aprendido en este capítulo, intenta el [quiz de frameworks de inferencia](../quizzes/ai-ml/04-inference-frameworks-quiz.md).
