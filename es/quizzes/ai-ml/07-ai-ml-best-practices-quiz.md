# AI/ML Best Practices Quiz

Este cuestionario evalúa tu comprensión de las mejores prácticas de AI/ML en Amazon EKS, incluidos benchmarking, optimización de contenedores, selección de GPU, redes, almacenamiento, observabilidad y optimización de costos.

## Quiz Questions

### 1. What does TTFT (Time to First Token) measure in LLM inference benchmarking?

A) El tiempo total para generar todos los tokens en una respuesta
B) El tiempo desde el envío de la solicitud hasta que se genera el primer token
C) El tiempo promedio entre tokens consecutivos
D) El número de tokens generados por segundo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El tiempo desde el envío de la solicitud hasta que se genera el primer token**

**Explicación:**
TTFT (Time to First Token) mide la latencia desde que se envía una solicitud hasta que se genera el primer token de la respuesta. Esta métrica es fundamental para la experiencia del usuario, ya que determina qué tan rápido los usuarios ven el inicio de una respuesta.

La fórmula es: `TTFT = t_first_token - t_request`

Puntos clave sobre TTFT:
- Impacta directamente la capacidad de respuesta percibida de la aplicación
- Debe ser < 500ms para aplicaciones interactivas
- Se ve afectado por la carga del modelo, el procesamiento del prompt (prefill) y la profundidad de la cola
- Un TTFT más alto indica posibles problemas con la memoria de GPU, el tamaño de batch o la carga del sistema

Otras métricas:
- ITL (Inter-Token Latency): Tiempo entre tokens consecutivos
- TPS (Tokens Per Second): Velocidad de generación
- Latencia E2E: Tiempo total desde la solicitud hasta la respuesta completa

</details>

### 2. Which container startup optimization technique provides the highest reduction in cold start time?

A) Solo builds de Docker de varias etapas
B) Solo desacoplamiento de artefactos del modelo
C) Enfoque combinado (desacoplamiento + varias etapas + prefetching + SOCI)
D) Usar únicamente imágenes base más pequeñas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Enfoque combinado (desacoplamiento + varias etapas + prefetching + SOCI)**

**Explicación:**
El enfoque combinado proporciona la mayor reducción en el tiempo de cold start, logrando una mejora del 80-95% en comparación con implementaciones ingenuas.

Comparación de optimización de cold start:

| Technique | Startup Reduction |
|-----------|-------------------|
| Model decoupling | 50-70% |
| Multi-stage builds | 30-50% |
| SOCI snapshotter | 60-80% |
| Image prefetching | 70-90% |
| **Combined approach** | **80-95%** |

El enfoque combinado funciona mediante:
1. **Desacoplamiento del modelo**: Separa los grandes pesos del modelo de las imágenes de contenedor
2. **Builds de varias etapas**: Reduce el tamaño de la imagen al excluir dependencias de build
3. **SOCI snapshotter**: Permite lazy pulling para que los contenedores se inicien antes de descargar la imagen completa
4. **Prefetching de imágenes**: Descarga previamente las imágenes durante el bootstrap del nodo

Para imágenes de AI/ML que pueden tener 10-50GB, esta combinación puede reducir el inicio de 5-15 minutos a menos de 1 minuto.

</details>

### 3. Which GPU instance family is best suited for large-scale distributed training requiring high-bandwidth inter-node communication?

A) G5 (NVIDIA A10G)
B) G6 (NVIDIA L4)
C) P5 (NVIDIA H100)
D) Inf2 (AWS Inferentia2)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) P5 (NVIDIA H100)**

**Explicación:**
Las instancias P5 con GPUs NVIDIA H100 son las más adecuadas para entrenamiento distribuido a gran escala porque ofrecen:

- **8 GPUs NVIDIA H100** con 80GB de memoria HBM3 cada una
- **Redes EFA de 3200 Gbps**: esenciales para entrenamiento distribuido
- **NVLink 4.0** para comunicación GPU a GPU de alto ancho de banda dentro del nodo
- **192 vCPUs y 2048GB de memoria** para preprocesamiento de datos

Comparación para entrenamiento distribuido:

| Instance | GPUs | GPU Memory | Network | Training Suitability |
|----------|------|------------|---------|---------------------|
| G5 | 1-8 A10G | 24GB | 100 Gbps | Small/medium models |
| G6 | 1-8 L4 | 24GB | 100 Gbps | Inference focus |
| P4d | 8 A100 | 40-80GB | 400 Gbps EFA | Large-scale training |
| **P5** | **8 H100** | **80GB** | **3200 Gbps EFA** | **Frontier models** |
| Inf2 | 1-12 Inferentia2 | 32GB | 100 Gbps | Inference only |

El ancho de banda EFA de 3200 Gbps de P5 es 8 veces el de P4d, lo que lo hace ideal para trabajos de entrenamiento donde la sincronización de gradientes entre nodos es el cuello de botella.

</details>

### 4. What is the primary purpose of EFA (Elastic Fabric Adapter) in distributed AI/ML training?

A) Aumentar la capacidad de memoria de la GPU
B) Proporcionar comunicación entre nodos de baja latencia y alto ancho de banda
C) Habilitar el uso compartido de tiempo de GPU
D) Acelerar la inferencia del modelo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar comunicación entre nodos de baja latencia y alto ancho de banda**

**Explicación:**
EFA (Elastic Fabric Adapter) es una interfaz de red para instancias Amazon EC2 que permite que aplicaciones de computación de alto rendimiento (HPC) y machine learning alcancen el rendimiento de comunicación entre nodos de clústeres HPC on-premises.

Beneficios clave de EFA para entrenamiento distribuido:
1. **Capacidad OS-bypass**: Permite que las aplicaciones se comuniquen directamente con el adaptador de red, reduciendo la latencia
2. **Alto ancho de banda**: Hasta 3200 Gbps en instancias P5
3. **Baja latencia**: Latencias de menos de un microsegundo para operaciones colectivas
4. **Optimización de NCCL**: Funciona con el plugin AWS OFI NCCL para comunicación GPU a GPU optimizada

Requisitos de configuración de EFA:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request EFA devices
```

Variables de entorno de NCCL para EFA:
```bash
export FI_PROVIDER=efa
export FI_EFA_USE_DEVICE_RDMA=1
export NCCL_ALGO=Ring,Tree
```

EFA es esencial para:
- Entrenamiento distribuido multinodo con frameworks como PyTorch DDP, Horovod
- Entrenamiento de modelos grandes con paralelismo de tensor/pipeline
- Cualquier carga de trabajo donde la sincronización de gradientes sea un cuello de botella

</details>

### 5. When should you use FSx for Lustre instead of EFS for AI/ML workloads?

A) Cuando necesitas acceso compartido desde múltiples pods
B) Cuando los datasets de entrenamiento superan los 10TB y requieren alto throughput
C) Cuando almacenas checkpoints del modelo temporalmente
D) Cuando ejecutas cargas de trabajo de inferencia con modelos pequeños

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando los datasets de entrenamiento superan los 10TB y requieren alto throughput**

**Explicación:**
FSx for Lustre es la opción óptima para datasets de entrenamiento grandes (>10TB) que requieren alto throughput, mientras que EFS es mejor para datasets más pequeños y almacenamiento compartido de modelos.

Guía de selección de almacenamiento:

| Use Case | Recommended Storage | Reasoning |
|----------|---------------------|-----------|
| Training datasets <500GB | EBS gp3 | Single node, cost-effective |
| Training datasets 500GB-10TB | EFS | Multi-node read, moderate throughput |
| **Training datasets >10TB** | **FSx Lustre** | **Parallel filesystem, TB/s throughput** |
| Shared model weights | EFS | ReadWriteMany, caching |
| Temporary checkpoints | Instance store | Lowest latency, ephemeral |
| Long-term model storage | S3 | Cost-effective, durable |

Ventajas de FSx for Lustre:
- Throughput de hasta 1+ TB/s (frente a ~1-3 GB/s de EFS)
- Latencias de menos de un milisegundo
- Integración directa con S3 mediante `s3ImportPath`
- Sistema de archivos paralelo diseñado para cargas de trabajo HPC

```yaml
# FSx Lustre for large datasets
storageClassName: fsx-lustre-sc
parameters:
  perUnitStorageThroughput: "250"  # MB/s per TiB
  s3ImportPath: s3://training-data  # Transparent S3 access
```

</details>

### 6. Which DCGM metric should you monitor to detect GPU thermal throttling?

A) DCGM_FI_DEV_GPU_UTIL
B) DCGM_FI_DEV_FB_USED
C) DCGM_FI_DEV_GPU_TEMP
D) DCGM_FI_DEV_XID_ERRORS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) DCGM_FI_DEV_GPU_TEMP**

**Explicación:**
DCGM_FI_DEV_GPU_TEMP monitorea la temperatura de la GPU en grados Celsius, que es el indicador principal para detectar condiciones de thermal throttling.

Métricas clave de GPU y sus propósitos:

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| **DCGM_FI_DEV_GPU_TEMP** | **Thermal monitoring** | **>80C warning, >90C critical** |
| DCGM_FI_DEV_GPU_UTIL | Compute utilization | >95% sustained |
| DCGM_FI_DEV_FB_USED | Memory usage | >95% of total |
| DCGM_FI_DEV_SM_CLOCK | Clock frequency (throttling detection) | Below baseline |
| DCGM_FI_DEV_POWER_USAGE | Power consumption | Near TDP limit |
| DCGM_FI_DEV_XID_ERRORS | Hardware errors | Any increase |

Detección de thermal throttling:
```yaml
# Alert rule for thermal issues
- alert: GPUHighTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 80
  for: 5m
  labels:
    severity: warning

- alert: GPUCriticalTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 90
  for: 1m
  labels:
    severity: critical
```

Cuando la temperatura supera los umbrales, las GPUs reducen automáticamente las velocidades de reloj (thermal throttling), lo que impacta el rendimiento de entrenamiento e inferencia.

</details>

### 7. What is the recommended approach for using Spot instances with GPU inference workloads?

A) Nunca usar instancias Spot para inferencia
B) Usar Spot solo para entrenamiento, On-Demand para inferencia
C) Usar Spot con manejo de terminación ordenada y topology spread
D) Usar Spot sin ninguna configuración especial

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar Spot con manejo de terminación ordenada y topology spread**

**Explicación:**
Las instancias Spot pueden proporcionar ahorros de costos del 60-90% para cargas de trabajo de inferencia stateless cuando se configuran correctamente con manejo de terminación ordenada y consideraciones de disponibilidad.

Mejores prácticas para inferencia en Spot:

1. **Manejo de terminación ordenada**:
```yaml
spec:
  terminationGracePeriodSeconds: 120
  containers:
  - lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "curl -X POST localhost:8000/drain; sleep 30"]
```

2. **Topology spread para disponibilidad**:
```yaml
topologySpreadConstraints:
- maxSkew: 2
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
```

3. **Tipos de capacidad mixtos**:
```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
    - weight: 50
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

Spot es adecuado para inferencia porque:
- Los pods de inferencia suelen ser stateless
- Múltiples réplicas proporcionan redundancia
- La advertencia de interrupción de 2 minutos permite drenaje ordenado

</details>

### 8. What is the formula for calculating Inter-Token Latency (ITL)?

A) `t_last_token - t_request`
B) `(t_last_token - t_first_token) / (n_tokens - 1)`
C) `n_tokens / total_generation_time`
D) `t_first_token - t_request`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `(t_last_token - t_first_token) / (n_tokens - 1)`**

**Explicación:**
Inter-Token Latency (ITL) mide el tiempo promedio entre tokens consecutivos durante la generación. La fórmula es:

`ITL = (t_last_token - t_first_token) / (n_tokens - 1)`

Donde:
- `t_last_token`: Marca de tiempo cuando se generó el último token
- `t_first_token`: Marca de tiempo cuando se generó el primer token
- `n_tokens`: Número total de tokens generados
- Dividimos por `(n_tokens - 1)` porque estamos midiendo intervalos entre tokens

Importancia de ITL:
- Determina la calidad de streaming para aplicaciones de chat
- Objetivo: < 50ms para una experiencia de usuario fluida
- Un ITL más alto indica presión de memoria de GPU o cuellos de botella de cómputo

Fórmulas de otras métricas:
- **TTFT**: `t_first_token - t_request` (tiempo hasta el primer token)
- **TPS**: `n_tokens / total_generation_time` (tokens por segundo)
- **Latencia E2E**: `t_complete - t_request` (end-to-end)

Ejemplo de cálculo:
- Primer token a los 500ms, último token a los 2500ms, 50 tokens generados
- ITL = (2500 - 500) / (50 - 1) = 2000 / 49 = ~41ms

</details>

### 9. Which test scenario is most appropriate for finding the maximum throughput of an LLM inference service?

A) Prueba baseline
B) Prueba de saturación
C) Prueba con dataset real
D) Prueba de contexto largo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prueba de saturación**

**Explicación:**
La prueba de saturación está diseñada específicamente para encontrar el throughput máximo aumentando incrementalmente la concurrencia hasta que la latencia se degrade, revelando los límites de capacidad del sistema.

Comparación de escenarios de prueba:

| Scenario | Purpose | Configuration |
|----------|---------|---------------|
| Baseline | Establish single-request performance | Concurrency=1, 100 requests |
| **Saturation** | **Find throughput limits** | **Concurrency=[1,5,10,20,50,100]** |
| Production | Validate real-world performance | Variable prompts, realistic load |
| Real dataset | Test with actual data patterns | ShareGPT or domain data |
| Long context | Test context window handling | 4K-128K token prompts |

Configuración de prueba de saturación:
```yaml
saturation:
  description: "Find maximum throughput"
  concurrency: [1, 5, 10, 20, 50, 100]  # Incrementally increase
  num_requests: 500
  prompt_length: 256
  max_tokens: 512
```

Lo que revela la prueba de saturación:
- Curva de throughput frente a latencia
- Punto en el que la latencia empieza a degradarse
- Si el sistema está limitado por GPU, memoria o CPU
- Nivel óptimo de concurrencia operativa

El objetivo es encontrar el "codo" de la curva, donde el throughput se estabiliza mientras la latencia permanece aceptable.

</details>

### 10. What is the purpose of SOCI (Seekable OCI) snapshotter for AI/ML containers?

A) Comprimir imágenes de contenedor
B) Habilitar lazy pulling para que los contenedores puedan iniciarse antes de descargar la imagen completa
C) Cifrar imágenes de contenedor
D) Compartir imágenes entre nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Habilitar lazy pulling para que los contenedores puedan iniciarse antes de descargar la imagen completa**

**Explicación:**
SOCI (Seekable OCI) snapshotter permite la carga diferida de imágenes de contenedor, lo que permite que los contenedores se inicien antes de que se descargue toda la imagen. Esto es particularmente valioso para imágenes grandes de AI/ML (10-50GB).

Cómo funciona SOCI:
1. Crea un índice de las capas de la imagen de contenedor
2. Descarga inicialmente solo los metadatos y las capas esenciales
3. Obtiene las capas restantes bajo demanda a medida que la aplicación accede a los archivos
4. El contenedor puede iniciarse con solo ~10-20% de la imagen descargada

Beneficios para AI/ML:
- Reducción del 60-80% en el tiempo de inicio del contenedor
- Particularmente efectivo para imágenes con capas grandes a las que se accede rara vez
- Funciona mejor cuando se accede a los pesos del modelo después del inicio del contenedor

Configuración de SOCI:
```bash
# Create SOCI index for an image
soci create \
  --ref public.ecr.aws/myrepo/vllm:latest \
  --platform linux/amd64

# Push the index to registry
soci push \
  --ref public.ecr.aws/myrepo/vllm:latest
```

Combinado con otras optimizaciones:
- Desacoplamiento del modelo (50-70%)
- Builds de varias etapas (30-50%)
- SOCI snapshotter (60-80%)
- Prefetching de imágenes (70-90%)

SOCI es más efectivo cuando el runtime de contenedores lo soporta (containerd con plugin SOCI) y las imágenes se almacenan en registros compatibles (Amazon ECR).

</details>

### 11. Which Karpenter consolidation policy setting prevents node disruption during business hours?

A) consolidationPolicy: WhenEmpty
B) consolidateAfter: 0
C) budgets with schedule and nodes: "0"
D) weight: 0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) budgets with schedule and nodes: "0"**

**Explicación:**
Los disruption budgets de Karpenter con schedule y `nodes: "0"` evitan cualquier consolidación de nodos durante ventanas de tiempo especificadas, normalmente durante el horario laboral.

Ejemplo de configuración:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m

  budgets:
  # No consolidation during business hours
  - nodes: "0"
    schedule: "0 9-17 * * 1-5"  # 9 AM to 5 PM, Mon-Fri
    duration: 8h

  # Allow 30% consolidation during off-peak
  - nodes: "30%"
```

Parámetros de budget:
- `nodes`: Número/porcentaje máximo de nodos que pueden ser interrumpidos
- `schedule`: Expresión cron para indicar cuándo se aplica el budget
- `duration`: Cuánto tiempo permanece activo el budget después de que se activa el schedule

Por qué esto importa para AI/ML:
- Los nodos GPU son caros y la interrupción provoca cold starts
- La latencia de inferencia aumenta durante el reemplazo de nodos
- Los trabajos de entrenamiento pueden perder progreso si los checkpoints no son frecuentes
- El horario laboral suele tener el mayor tráfico

Otros ajustes de consolidación:
- `consolidationPolicy: WhenEmpty`: Solo consolida nodos completamente vacíos
- `consolidationPolicy: WhenEmptyOrUnderutilized`: También consolida nodos infrautilizados
- `consolidateAfter`: Retraso antes de la consolidación (por ejemplo, 5m)

</details>

### 12. What is the recommended method for managing HuggingFace and NGC API keys in Kubernetes?

A) Incluirlas directamente en el Dockerfile
B) Pasarlas como variables de entorno en la especificación del pod
C) Usar External Secrets Operator con AWS Secrets Manager
D) Almacenarlas en ConfigMap

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar External Secrets Operator con AWS Secrets Manager**

**Explicación:**
External Secrets Operator (ESO) con AWS Secrets Manager proporciona una gestión de secretos segura y centralizada con capacidades de rotación automática y auditoría.

Por qué se recomienda ESO:
1. **Gestión centralizada**: Secretos almacenados en AWS Secrets Manager
2. **Sincronización automática**: ESO actualiza automáticamente los secretos de Kubernetes
3. **Soporte de rotación**: Los secretos pueden rotarse sin redesplegar pods
4. **Registro de auditoría**: AWS CloudTrail registra todo acceso a secretos
5. **Integración con IAM**: Control de acceso detallado con IRSA

Ejemplo de configuración:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: model-registry-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: model-registry-credentials
  data:
  - secretKey: HUGGING_FACE_HUB_TOKEN
    remoteRef:
      key: ai-ml/huggingface-token
      property: token
  - secretKey: NGC_API_KEY
    remoteRef:
      key: ai-ml/ngc-api-key
      property: key
```

Por qué otras opciones son problemáticas:
- **Incluidas directamente en el Dockerfile**: Los secretos quedan expuestos en las capas de la imagen
- **Variables de entorno en la especificación del pod**: Visibles en kubectl describe
- **ConfigMap**: No está cifrado, visible para cualquiera con acceso de lectura

Mejores prácticas de seguridad:
- Usa IRSA para autenticación de service account
- Habilita cifrado en reposo en Secrets Manager
- Implementa políticas de acceso de mínimo privilegio
- Rota los secretos regularmente

</details>

### 13. For a 30B parameter model inference workload with a medium budget, which GPU instance type is most appropriate?

A) g5.xlarge (1x A10G, 24GB)
B) g5.4xlarge (1x A10G, 24GB)
C) g5.12xlarge (4x A10G, 96GB total)
D) p4d.24xlarge (8x A100, 640GB total)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) g5.12xlarge (4x A10G, 96GB total)**

**Explicación:**
Un modelo de 30B parámetros requiere aproximadamente 60GB de memoria GPU para inferencia FP16 (2 bytes por parámetro), por lo que g5.12xlarge con 4 GPUs A10G (96GB en total) es la opción adecuada para un presupuesto medio.

Cálculo de memoria:
- 30B parámetros x 2 bytes (FP16) = 60GB mínimo
- Con sobrecarga de KV cache: se recomiendan ~70-80GB
- g5.12xlarge: 4 x 24GB = 96GB (suficiente con margen)

Guía de selección de instancias:

| Model Size | Memory Needed | Recommended Instance | Budget |
|------------|---------------|---------------------|--------|
| <7B | 14GB | g5.xlarge | Low |
| 7-13B | 26GB | g5.2xlarge | Low-Medium |
| 13-30B | 60GB | g5.4xlarge (quantized) or g5.12xlarge | Medium |
| **30B** | **60GB** | **g5.12xlarge (4x A10G)** | **Medium** |
| 30-70B | 140GB | g5.12xlarge + tensor parallel | Medium-High |
| >70B | 280GB+ | p4d.24xlarge | High |

Por qué g5.12xlarge para 30B:
- El paralelismo tensorial de 4 vías distribuye el modelo entre GPUs
- Cada GPU contiene ~15GB de pesos del modelo
- La memoria restante queda disponible para KV cache
- Más rentable que P4d para inferencia

p4d.24xlarge funcionaría, pero es excesivo para inferencia de 30B y significativamente más caro.

</details>

### 14. Which vLLM metric indicates that the system may start rejecting requests due to memory pressure?

A) vllm:num_requests_running
B) vllm:time_to_first_token_seconds
C) vllm:gpu_cache_usage_perc
D) vllm:request_success_total

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) vllm:gpu_cache_usage_perc**

**Explicación:**
`vllm:gpu_cache_usage_perc` mide la utilización de la KV (Key-Value) cache. Cuando esta métrica se aproxima al 100%, vLLM no puede aceptar nuevas solicitudes porque no hay memoria disponible para almacenar estados de atención.

Importancia de la KV cache:
- Almacena claves y valores de atención calculados para cada token
- Crece con la longitud de la secuencia y el tamaño del batch
- Cuando está llena, vLLM debe anticipar solicitudes en ejecución o rechazar nuevas solicitudes

Configuración de alerta:
```yaml
- alert: vLLMKVCacheFull
  expr: vllm:gpu_cache_usage_perc > 0.95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "vLLM KV cache nearly full"
    description: "KV cache usage above 95%, requests may be rejected"
```

Qué hacer cuando la KV cache está llena:
1. Reducir `--max-num-seqs` (secuencias concurrentes)
2. Reducir `--max-model-len` (longitud máxima de secuencia)
3. Habilitar chunked prefill
4. Escalar horizontalmente (agregar más réplicas)
5. Usar instancias GPU más grandes

Otras métricas de vLLM:
- `vllm:num_requests_running`: Solicitudes concurrentes actuales
- `vllm:num_requests_waiting`: Profundidad de la cola
- `vllm:time_to_first_token_seconds`: Latencia TTFT
- `vllm:gpu_prefix_cache_hit_rate`: Eficiencia de caché

</details>

### 15. What is the primary benefit of using placement groups with cluster strategy for distributed training?

A) Costos reducidos de instancias EC2
B) Balanceo de carga automático
C) La latencia de red más baja entre nodos
D) Mayor memoria GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La latencia de red más baja entre nodos**

**Explicación:**
Los cluster placement groups colocan las instancias físicamente cerca dentro de una única Availability Zone, minimizando la latencia de red y maximizando el ancho de banda para la comunicación entre nodos.

Beneficios de cluster placement group:
1. **Latencia más baja**: Instancias en la misma estructura de red
2. **Ancho de banda máximo**: Ancho de banda de bisección completo disponible
3. **Rendimiento consistente**: Menor jitter de red
4. **Optimización de EFA**: El mejor rendimiento de EFA requiere colocación en cluster

Configuración:
```bash
# Create cluster placement group
aws ec2 create-placement-group \
  --group-name training-cluster-pg \
  --strategy cluster

# Karpenter configuration
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
spec:
  tags:
    aws:ec2:placement-group: training-cluster-pg
```

Estrategias de placement group:

| Strategy | Use Case | Latency | Availability |
|----------|----------|---------|--------------|
| **Cluster** | **Distributed training** | **Lowest** | **Single AZ** |
| Spread | High availability | Higher | Multi-AZ |
| Partition | Large deployments | Medium | Multi-rack |

Por qué la estrategia cluster para entrenamiento:
- Las operaciones all-reduce de NCCL son sensibles a la latencia
- La sincronización de gradientes ocurre con frecuencia (en cada batch)
- Incluso pequeños aumentos de latencia se acumulan en miles de iteraciones
- Las instancias P4d/P5 logran el mejor rendimiento de EFA en cluster placement

Trade-off: Los cluster placement groups están limitados a una única AZ, lo que reduce la disponibilidad. Para entrenamiento, esto es aceptable porque:
- Los trabajos de entrenamiento pueden hacer checkpoint y reiniciarse
- La menor latencia mejora el tiempo de entrenamiento más de lo que ayuda la redundancia

</details>
