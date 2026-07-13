# Cuestionario sobre frameworks de inferencia

Este cuestionario evalúa tu comprensión de los frameworks de inferencia de LLM para despliegues en Kubernetes, incluidos NVIDIA NIM, NVIDIA Dynamo, AIBrix, Ray Serve y AWS Neuron.

## Preguntas del cuestionario

### 1. ¿Cuál es el beneficio principal de NVIDIA NIM para el despliegue de LLM?

A) Solo admite modelos de código abierto
B) Proporciona despliegues de LLM containerizados y listos para producción con motores de inferencia optimizados y APIs compatibles con OpenAI
C) Requiere la compilación manual de todos los modelos
D) Solo funciona con instancias CPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporciona despliegues de LLM containerizados y listos para producción con motores de inferencia optimizados y APIs compatibles con OpenAI**

**Explicación:**
NVIDIA NIM (NVIDIA Inference Microservices) proporciona despliegues de LLM containerizados y listos para producción con varias características clave:

1. **Motores de inferencia optimizados**: Usa TensorRT-LLM para obtener el máximo rendimiento
2. **APIs compatibles con OpenAI**: Reemplazo directo para llamadas a la API de OpenAI
3. **Monitoreo integrado**: Métricas de Prometheus y dashboards de Grafana
4. **Integración con NGC Catalog**: Acceso sencillo a modelos preoptimizados
5. **Soporte empresarial**: SLAs de producción y soporte de NVIDIA

```yaml
# NIM deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nim-llama-70b
spec:
  template:
    spec:
      containers:
      - name: nim
        image: nvcr.io/nim/meta/llama-3.1-70b-instruct:1.2.0
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 8
```

</details>

### 2. ¿Qué es el "disaggregated serving" en NVIDIA Dynamo?

A) Ejecutar varios modelos en una sola GPU
B) Separar las fases de prefill (procesamiento del prompt) y decode (generación de tokens) en diferentes pools de workers
C) Distribuir logs entre varios servidores
D) Ejecutar inferencia sin GPUs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separar las fases de prefill (procesamiento del prompt) y decode (generación de tokens) en diferentes pools de workers**

**Explicación:**
El disaggregated serving es un patrón arquitectónico clave en NVIDIA Dynamo que separa las dos fases principales de la inferencia de LLM:

1. **Fase de prefill**:
   - Procesa el prompt de entrada
   - Intensiva en cómputo (necesita FLOPs altos)
   - Se beneficia de GPUs de gama alta como A100

2. **Fase de decode**:
   - Genera tokens de salida uno a la vez
   - Intensiva en ancho de banda de memoria
   - Puede usar GPUs más rentables como A10G

**Beneficios de la desagregación:**
- Mejor utilización de recursos
- Optimización de costos mediante el uso heterogéneo de GPU
- Mayor throughput general
- Escalado independiente de la capacidad de prefill y decode

```yaml
# Dynamo configuration example
prefill:
  replicas: 2
  backend: vllm
  tensor_parallel_size: 8
  # Uses p4d.24xlarge with A100 GPUs

decode:
  replicas: 4
  backend: vllm
  tensor_parallel_size: 4
  # Uses g5.12xlarge with A10G GPUs
```

</details>

### 3. ¿Qué componente de AIBrix se encarga de la carga y gestión dinámica de adaptadores LoRA?

A) Gateway
B) Autoscaler
C) LoRA Manager
D) Model Registry

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) LoRA Manager**

**Explicación:**
AIBrix consta de varios componentes clave, cada uno con responsabilidades específicas:

1. **Gateway**: Enrutamiento inteligente de solicitudes y balanceo de carga
2. **LoRA Manager**: Carga y gestión dinámica de adaptadores LoRA
3. **Autoscaler**: Autoscaling consciente de la carga de trabajo para pods de inferencia
4. **Model Registry**: Gestión centralizada de modelos y adaptadores

El **LoRA Manager** se encarga específicamente de:
- Carga dinámica de adaptadores LoRA sin reinicio
- Hot-swapping entre diferentes adaptadores
- Gestión de memoria para varios adaptadores
- Versionado y ciclo de vida de adaptadores

```bash
# Register a LoRA adapter
curl -X POST http://aibrix-registry:8081/v1/lora/register \
  -d '{
    "name": "customer-support",
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_path": "s3://aibrix-models/lora/customer-support",
    "rank": 16,
    "alpha": 32
  }'

# Use LoRA in inference request
curl -X POST http://aibrix-gateway:8080/v1/chat/completions \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_adapter": "customer-support",
    "messages": [{"role": "user", "content": "Help me"}]
  }'
```

</details>

### 4. ¿Qué operator de Kubernetes se usa para desplegar Ray Serve para inferencia distribuida?

A) NVIDIA GPU Operator
B) KubeRay Operator
C) Prometheus Operator
D) Flux Operator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) KubeRay Operator**

**Explicación:**
El KubeRay Operator es la forma nativa de Kubernetes para desplegar y gestionar clusters de Ray, incluido Ray Serve para inferencia distribuida.

**Características de KubeRay Operator:**
- Gestiona el ciclo de vida del cluster de Ray
- Admite CRDs RayCluster, RayJob y RayService
- Maneja el auto-scaling de workers de Ray
- Se integra con RBAC y redes de Kubernetes

**Instalación:**
```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace
```

**Ejemplo de RayService:**
```yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-serve
spec:
  serveConfigV2: |
    applications:
    - name: vllm-app
      import_path: serve_vllm:deployment
      deployments:
      - name: VLLMDeployment
        num_replicas: 2
        ray_actor_options:
          num_gpus: 1
  rayClusterConfig:
    workerGroupSpecs:
    - groupName: gpu-workers
      replicas: 2
      maxReplicas: 8
```

</details>

### 5. ¿Cuál es la ventaja principal de usar instancias AWS Inferentia2 (inf2) para inferencia de LLM?

A) Más memoria GPU que A100
B) Hasta un 70% menos de costo en comparación con instancias GPU
C) Tiempos de compilación de modelos más rápidos
D) Mejor soporte para cargas de trabajo de entrenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hasta un 70% menos de costo en comparación con instancias GPU**

**Explicación:**
AWS Inferentia2 proporciona ventajas de costo significativas para cargas de trabajo de inferencia:

**Beneficios de costo:**
- Hasta un 70% menos de costo frente a instancias GPU comparables
- Alto throughput por dólar
- Eficiente para cargas de trabajo solo de inferencia

**Modelos compatibles:**
- Llama 2/3
- Mistral
- Stable Diffusion
- Varios modelos encoder

**Instance Types:**
| Instance | Neuron Cores | Memory | Use Case |
|----------|--------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | 7B models |
| inf2.24xlarge | 6 | 96 GB | 13B-70B models |
| inf2.48xlarge | 12 | 192 GB | 70B+ models |

**Trade-offs:**
- Requiere compilación de modelos para Neuron
- Soporte de modelos limitado en comparación con GPUs
- Tiempo de configuración inicial más largo

```yaml
# Neuron resource request
resources:
  limits:
    aws.amazon.com/neuron: 2
    memory: 32Gi
  requests:
    aws.amazon.com/neuron: 2
```

</details>

### 6. ¿Qué métrica mide el tiempo hasta que se genera el primer token en la inferencia de LLM?

A) ITL (Inter-Token Latency)
B) TTFT (Time to First Token)
C) TPS (Tokens Per Second)
D) QPS (Queries Per Second)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) TTFT (Time to First Token)**

**Explicación:**
TTFT (Time to First Token) es una métrica de latencia crítica para la inferencia de LLM que mide cuánto espera un usuario antes de ver cualquier salida.

**Métricas clave de inferencia de LLM:**

1. **TTFT (Time to First Token)**:
   - Tiempo desde el envío de la solicitud hasta el primer token
   - Incluye el tiempo de procesamiento del prompt (prefill)
   - Objetivo: < 500 ms para una buena UX

2. **ITL (Inter-Token Latency)**:
   - Tiempo entre tokens generados consecutivos
   - Afecta la velocidad de streaming percibida
   - Objetivo: < 50 ms

3. **Throughput**:
   - Tokens generados por segundo
   - Mide la capacidad del sistema

4. **Latencia E2E**:
   - Tiempo total para la respuesta completa
   - TTFT + (ITL * output_tokens)

**Ejemplo de monitoreo:**
```promql
# TTFT P99
histogram_quantile(0.99, sum(rate(nim_time_to_first_token_bucket[5m])) by (le))

# ITL P99
histogram_quantile(0.99, sum(rate(nim_inter_token_latency_bucket[5m])) by (le))

# Throughput
sum(rate(nim_tokens_generated_total[5m]))
```

</details>

### 7. En NVIDIA Dynamo, ¿cuál es el propósito del enrutamiento consciente de KV?

A) Enrutar solicitudes según la ubicación del usuario
B) Enrutar solicitudes según la localidad de la KV cache para un rendimiento óptimo
C) Enrutar solicitudes a la instancia más barata
D) Enrutar solicitudes según la versión del modelo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Enrutar solicitudes según la localidad de la KV cache para un rendimiento óptimo**

**Explicación:**
El enrutamiento consciente de KV en NVIDIA Dynamo optimiza el enrutamiento de solicitudes en función de dónde se encuentran los datos de la KV cache, mejorando el rendimiento al reducir la transferencia de datos.

**Cómo funciona el enrutamiento consciente de KV:**

1. **Seguimiento de KV Cache**: El router rastrea qué workers de decode tienen datos KV en cache para solicitudes anteriores
2. **Optimización de localidad**: Enruta solicitudes de seguimiento (en conversaciones multi-turno) a workers que ya tienen la KV cache relevante
3. **Balanceo de carga**: Equilibra los beneficios de localidad frente a la carga del worker

**Configuración:**
```yaml
router:
  kv_routing:
    enabled: true
    locality_weight: 0.7  # Prefer cache locality
    load_weight: 0.3      # Consider worker load
```

**Beneficios:**
- TTFT reducido para conversaciones multi-turno
- Menor presión de memoria (evita KV cache duplicada)
- Mejor utilización de memoria GPU
- Mayor throughput efectivo

**Fórmula de decisión de enrutamiento:**
```
score = locality_weight * cache_hit_score + load_weight * (1 - worker_load)
```

</details>

### 8. ¿Qué comando se usa para instalar el plugin de dispositivo Neuron para Kubernetes?

A) `kubectl apply -f nvidia-device-plugin.yml`
B) `helm install neuron-plugin aws/neuron`
C) `kubectl apply -f k8s-neuron-device-plugin.yml`
D) `eksctl create addon --name neuron-device-plugin`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `kubectl apply -f k8s-neuron-device-plugin.yml`**

**Explicación:**
El plugin de dispositivo Neuron se instala usando kubectl apply con el manifiesto oficial del repositorio AWS Neuron SDK.

**Comando de instalación:**
```bash
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml
```

**Verificación:**
```bash
# Check DaemonSet
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# Check Neuron devices on nodes
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

**Formato de solicitud de recursos:**
```yaml
resources:
  limits:
    aws.amazon.com/neuron: 2  # Request 2 Neuron cores
```

El plugin de dispositivo NVIDIA usa `nvidia.com/gpu`, mientras que Neuron usa `aws.amazon.com/neuron`.

</details>

### 9. ¿Qué framework de inferencia proporciona autoscaling integrado como característica principal?

A) vLLM standalone
B) NVIDIA NIM
C) AIBrix
D) Triton Inference Server

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) AIBrix**

**Explicación:**
AIBrix proporciona autoscaling integrado y consciente de la carga de trabajo como característica principal, a diferencia de otros frameworks que requieren soluciones externas como HPA o KEDA.

**Características de AIBrix Autoscaler:**
- Políticas de escalado conscientes de la carga de trabajo
- Soporte de múltiples métricas (RPS, latencia, utilización de GPU, profundidad de cola)
- Comportamiento configurable de scale-up/scale-down
- Políticas de escalado por despliegue

**Configuración de AIBrix Autoscaler:**
```yaml
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
        - name: gpu_utilization
          target: 80
        - name: queue_depth
          target: 20
      scale_up:
        stabilization_window: 60s
        step_size: 2
      scale_down:
        stabilization_window: 300s
        step_size: 1
```

**Comparison:**
| Framework | Auto-scaling |
|-----------|--------------|
| NIM | Manual (external HPA/KEDA) |
| Dynamo | Manual (external) |
| AIBrix | Built-in |
| vLLM | Manual (external) |
| Ray Serve | Built-in |
| Triton | Manual (external) |

</details>

### 10. ¿Cuál es el propósito de NGC Catalog en los despliegues de NVIDIA NIM?

A) Almacenar manifiestos de Kubernetes
B) Proporcionar contenedores y configuraciones de modelos preoptimizados
C) Gestionar redes de cluster
D) Manejar autenticación de usuarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar contenedores y configuraciones de modelos preoptimizados**

**Explicación:**
El NGC (NVIDIA GPU Cloud) Catalog es el repositorio de NVIDIA para software optimizado para GPU, incluidos contenedores NIM preconstruidos con modelos optimizados.

**Características de NGC Catalog:**
- Contenedores de modelos preoptimizados
- Múltiples perfiles de modelo (diferentes tamaños de batch y precisiones)
- Gestión de versiones
- Escaneo de seguridad
- Soporte empresarial

**Acceso a NGC:**
```bash
# Create NGC API key secret
kubectl create secret generic ngc-api-key \
  --from-literal=NGC_API_KEY='your-ngc-api-key'

# Create docker config secret for image pull
kubectl create secret docker-registry ngc-credentials \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password='your-ngc-api-key'
```

**Uso de imágenes NGC:**
```yaml
spec:
  imagePullSecrets:
  - name: ngc-credentials
  containers:
  - name: nim
    image: nvcr.io/nim/meta/llama-3.1-70b-instruct:1.2.0
    env:
    - name: NGC_API_KEY
      valueFrom:
        secretKeyRef:
          name: ngc-api-key
          key: NGC_API_KEY
```

**Perfiles NIM disponibles:**
- `vllm-bf16-tp8`: paralelo tensorial de 8 GPU, precisión BF16
- `vllm-fp8-tp4`: paralelo tensorial de 4 GPU, precisión FP8
- `tensorrt-llm-fp16-tp8`: backend TensorRT-LLM

</details>

### 11. ¿Qué backends admite NVIDIA Dynamo para inferencia?

A) Solo TensorRT-LLM
B) vLLM, SGLang y TensorRT-LLM
C) Solo vLLM
D) Solo PyTorch

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) vLLM, SGLang y TensorRT-LLM**

**Explicación:**
NVIDIA Dynamo está diseñado para ser agnóstico al backend y admite múltiples motores de inferencia:

1. **vLLM**:
   - Código abierto, alto rendimiento
   - PagedAttention para eficiencia de memoria
   - Amplio soporte de modelos

2. **SGLang**:
   - Optimizado para generación estructurada
   - Decodificación restringida por JSON/regex rápida
   - Cache de prefijos eficiente

3. **TensorRT-LLM**:
   - Máximo rendimiento en GPU NVIDIA
   - Kernels optimizados
   - Cuantización INT8/FP8

**Ejemplo de configuración:**
```yaml
# Using vLLM backend for prefill
prefill:
  backend: vllm
  model: meta-llama/Llama-3.1-70B-Instruct
  tensor_parallel_size: 8

# Using SGLang backend for decode
decode:
  backend: sglang
  model: meta-llama/Llama-3.1-70B-Instruct
  tensor_parallel_size: 4

# Or using TensorRT-LLM
prefill:
  backend: tensorrt-llm
  engine_path: /models/llama-70b-trt
```

Esta flexibilidad permite:
- Mezclar backends para un rendimiento óptimo
- Probar diferentes motores
- Usar backends especializados para tareas específicas

</details>

### 12. ¿Cuál es la forma recomendada de manejar el almacenamiento de modelos para despliegues de vLLM en EKS?

A) Almacenar modelos en ConfigMaps
B) Descargar modelos al iniciar el contenedor cada vez
C) Usar FSx for Lustre o persistent volumes con modelos descargados previamente
D) Incrustar modelos en la imagen del contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar FSx for Lustre o persistent volumes con modelos descargados previamente**

**Explicación:**
Para despliegues de LLM en producción, usar almacenamiento persistente de alto rendimiento es crítico:

**Opciones de almacenamiento recomendadas:**

1. **FSx for Lustre**:
   - Sistema de archivos paralelo de alto throughput
   - Ideal para archivos de modelos grandes
   - Integración con S3 para actualizaciones de modelos
   - Hasta 1000+ MB/s de throughput

2. **Volúmenes EBS gp3**:
   - Buenos para despliegues de un solo node
   - Rentables
   - Hasta 16,000 IOPS

3. **EFS**:
   - Acceso compartido entre pods
   - Menor throughput que FSx
   - Bueno para modelos más pequeños

**Configuración de FSx for Lustre:**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

**Por qué NO otras opciones:**
- **ConfigMaps**: Límite de tamaño de 1 MB, no son para archivos grandes
- **Descarga al inicio**: Inicio lento, costos de ancho de banda, problemas de confiabilidad
- **Incrustado en la imagen**: Imágenes enormes, pulls lentos, poca flexibilidad de versiones

</details>

### 13. ¿Cuál es la función de GenAI-Perf en los despliegues de NIM?

A) Generar imágenes de IA
B) Hacer benchmarking y perfilar el rendimiento de inferencia de LLM
C) Gestionar memoria GPU
D) Configurar políticas de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Hacer benchmarking y perfilar el rendimiento de inferencia de LLM**

**Explicación:**
GenAI-Perf es la herramienta de NVIDIA para benchmarking y profiling del rendimiento de inferencia de IA generativa.

**Características:**
- Mide TTFT, ITL y throughput
- Admite pruebas de solicitudes concurrentes
- Múltiples tipos de endpoint (chat, completion)
- Exporta resultados para análisis

**Instalación:**
```bash
pip install genai-perf
```

**Ejemplo de uso:**
```bash
genai-perf \
  --endpoint-type chat \
  --service-kind openai \
  --url http://nim-inference:8000/v1 \
  --model meta/llama-3.1-70b-instruct \
  --concurrency 16 \
  --input-sequence-length 512 \
  --output-sequence-length 256 \
  --num-prompts 100 \
  --profile-export-file nim-benchmark.json

# Analyze results
genai-perf analyze nim-benchmark.json
```

**Métricas clave reportadas:**
- Time to First Token (P50, P90, P99)
- Inter-Token Latency (P50, P90, P99)
- Throughput de solicitudes
- Throughput de tokens
- Utilización de GPU durante el benchmark

</details>

### 14. ¿Qué tipo de recurso de Kubernetes es más apropiado para desplegar vLLM distribuido con paralelismo tensorial entre varios pods?

A) Deployment
B) StatefulSet
C) DaemonSet
D) ReplicaSet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) StatefulSet**

**Explicación:**
StatefulSet es el recurso apropiado para despliegues distribuidos de vLLM que requieren:

1. **Identidad de red estable**: Cada pod obtiene un hostname predecible (vllm-0, vllm-1, etc.)
2. **Despliegue ordenado**: Los pods se crean en secuencia, importante para la coordinación master/worker
3. **Almacenamiento estable**: Cada pod puede tener su propio persistent volume
4. **Headless Service**: Comunicación directa pod-to-pod para NCCL

**Configuración de StatefulSet:**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vllm-distributed
spec:
  serviceName: "vllm-distributed"
  replicas: 2
  selector:
    matchLabels:
      app: vllm-distributed
  template:
    metadata:
      labels:
        app: vllm-distributed
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        env:
        - name: MASTER_ADDR
          value: "vllm-distributed-0.vllm-distributed"
        - name: MASTER_PORT
          value: "29500"
        ports:
        - containerPort: 8000
        - containerPort: 29500  # NCCL communication
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-distributed
spec:
  clusterIP: None  # Headless service
  selector:
    app: vllm-distributed
```

**Por qué StatefulSet en lugar de Deployment:**
- Deployments no garantiza hostnames estables
- NCCL requiere direccionamiento predecible
- La elección de master necesita una identidad de pod consistente

</details>

### 15. ¿Qué variable de entorno controla el número de cores Neuron visibles para un contenedor?

A) CUDA_VISIBLE_DEVICES
B) NEURON_RT_VISIBLE_CORES
C) AWS_NEURON_CORES
D) NEURON_DEVICE_COUNT

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) NEURON_RT_VISIBLE_CORES**

**Explicación:**
`NEURON_RT_VISIBLE_CORES` controla qué cores Neuron son visibles para el runtime de Neuron dentro de un contenedor.

**Variables de entorno clave de Neuron:**

1. **NEURON_RT_VISIBLE_CORES**:
   - Especifica qué cores usar
   - Formato: "0,1" o "0-3"
   ```yaml
   env:
   - name: NEURON_RT_VISIBLE_CORES
     value: "0,1"
   ```

2. **NEURON_RT_NUM_CORES**:
   - Número total de cores a usar
   ```yaml
   env:
   - name: NEURON_RT_NUM_CORES
     value: "2"
   ```

3. **NEURON_CC_FLAGS**:
   - Flags del compilador para la compilación del modelo
   ```yaml
   env:
   - name: NEURON_CC_FLAGS
     value: "--model-type transformer"
   ```

**Ejemplo completo:**
```yaml
containers:
- name: vllm-neuron
  image: public.ecr.aws/neuron/pytorch-inference-neuronx:latest
  env:
  - name: NEURON_RT_NUM_CORES
    value: "2"
  - name: NEURON_RT_VISIBLE_CORES
    value: "0,1"
  - name: NEURON_CC_FLAGS
    value: "--model-type transformer"
  resources:
    limits:
      aws.amazon.com/neuron: 2
```

Nota: `CUDA_VISIBLE_DEVICES` es para GPUs NVIDIA, no para Neuron.

</details>
