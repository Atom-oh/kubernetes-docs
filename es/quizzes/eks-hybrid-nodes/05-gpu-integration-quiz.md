# Cuestionario sobre integración de GPU en EKS Hybrid Nodes

> **Documento relacionado**: [Integración de GPU](../../eks-hybrid-nodes/05-gpu-integration.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la característica clave de la tecnología Multi-Instance GPU (MIG) de NVIDIA GPU?

A. Combina varias GPUs en una sola
B. Divide una sola GPU en varias instancias físicamente aisladas
C. Solo comparte memoria de GPU
D. Time-Slicing a nivel de software

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Divide una sola GPU en varias instancias físicamente aisladas**

**Explicación:**
MIG (Multi-Instance GPU) particiona GPUs como NVIDIA A100 y H100 en hasta 7 instancias físicamente aisladas. Cada instancia tiene recursos independientes de memoria, caché y cómputo.

**Comparación entre MIG y Time-Slicing:**

| Característica | MIG | Time-Slicing |
|---------|-----|--------------|
| Nivel de aislamiento | Físico (aislamiento completo) | Basado en tiempo (software) |
| Aislamiento de memoria | Aislamiento completo | Compartida |
| GPUs compatibles | A100, H100 | Todas las GPUs NVIDIA |
| Garantía de QoS | Sí | No |

```yaml
# MIG Resource Request
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/mig-1g.5gb: 1
```

</details>

### 2. ¿Qué significa "1g.5gb" en la configuración MIG de NVIDIA GPU?

A. 1 GB de memoria, 5 núcleos de GPU
B. 1 GPU Instance (1 segmento de cómputo), 5 GB de memoria de GPU
C. 1 GPU, 5 GB de memoria del sistema
D. 1 segundo por cada 5 GB de throughput

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 1 GPU Instance (1 segmento de cómputo), 5 GB de memoria de GPU**

**Explicación:**
Formato de nombre de instancia MIG: `<compute-slices>g.<memory-size>gb`

- **1g**: 1 segmento de cómputo
- **5gb**: 5 GB de memoria de GPU

**Ejemplos de perfiles MIG de A100:**
- `1g.5gb`: 1 segmento de cómputo, 5 GB de memoria (máx. 7)
- `2g.10gb`: 2 segmentos de cómputo, 10 GB de memoria (máx. 3)
- `3g.20gb`: 3 segmentos de cómputo, 20 GB de memoria (máx. 2)
- `4g.40gb`: 4 segmentos de cómputo, 40 GB de memoria (máx. 1)
- `7g.40gb`: 7 segmentos de cómputo, 40 GB de memoria (GPU completa)

```bash
# Check MIG instances
nvidia-smi mig -lgi
```

</details>

### 3. ¿Cuál es el comportamiento esperado cuando ocurre sobresuscripción en GPU Time-Slicing?

A. Fallo completo de la tarea de GPU
B. Degradación del rendimiento debido al cambio de contexto
C. Adición automática de GPU
D. Expansión automática de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Degradación del rendimiento debido al cambio de contexto**

**Explicación:**
Time-Slicing permite que varias cargas de trabajo compartan una sola GPU mediante división por tiempo. Cuando ocurre sobresuscripción, el cambio de contexto frecuente causa degradación del rendimiento.

```yaml
# GPU Time-Slicing Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    sharing:
      timeSlicing:
        resources:
        - name: nvidia.com/gpu
          replicas: 4  # Split 1 GPU into 4
```

**Consideraciones de Time-Slicing:**
- La memoria se comparte, por lo que puede ocurrir OOM
- Adecuado para cargas de trabajo de inferencia
- Se recomiendan MIG o GPUs dedicadas para entrenamiento
- Es importante configurar correctamente el número de réplicas

</details>

### 4. ¿Cuál es la principal ventaja de Dynamic Resource Allocation (DRA)?

A. Solo admite asignación estática de recursos
B. Admite todos los dispositivos sin plugins específicos del proveedor
C. Mecanismo flexible de solicitud/asignación para recursos personalizados
D. Solo gestiona CPU y memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Mecanismo flexible de solicitud/asignación para recursos personalizados**

**Explicación:**
DRA (Dynamic Resource Allocation), introducido en Kubernetes 1.26, proporciona un mecanismo más flexible de solicitud y asignación para recursos personalizados como GPUs, FPGAs y dispositivos de red.

**Componentes principales de DRA:**
- **ResourceClass**: Define los tipos de recursos proporcionados por drivers
- **ResourceClaim**: Solicitud de recursos
- **ResourceClaimTemplate**: Plantilla de claim reutilizable

```yaml
# Using DRA in Pod
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
  - name: cuda-app
    resources:
      claims:
      - name: gpu
  resourceClaims:
  - name: gpu
    source:
      resourceClaimTemplateName: gpu-claim-template
```

</details>

### 5. ¿Qué condición debe cumplirse para que el estado de ResourceClaim pase a ser "Bound" en DRA (Dynamic Resource Allocation)?

A. Solo la creación del claim
B. El driver asigna recursos y el Pod se programa
C. El Pod termina
D. El claim se elimina

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El driver asigna recursos y el Pod se programa**

**Explicación:**
Flujo de estado de ResourceClaim:

1. **Pending**: Claim creado, aún no asignado
2. **Allocated**: El driver completó la asignación de recursos
3. **Bound**: Vinculado al Pod y en uso

```yaml
# Check ResourceClaim Status
kubectl get resourceclaim gpu-claim -o yaml

# Expected output
status:
  allocation:
    resourceHandles:
    - driverName: gpu.nvidia.com
      data: '{"gpu":"GPU-abc123"}'
  reservedFor:
  - name: gpu-workload
    uid: xxx-xxx-xxx
```

</details>

### 6. ¿Cuál es el rol principal de NVIDIA GPU Operator?

A. Fabricación de hardware de GPU
B. Gestión automática de drivers, runtimes y plugins de GPU en Kubernetes
C. Solo pruebas de rendimiento de GPU
D. Gestión de compra y entrega de GPUs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Gestión automática de drivers, runtimes y plugins de GPU en Kubernetes**

**Explicación:**
NVIDIA GPU Operator gestiona automáticamente la infraestructura de GPU en Kubernetes:

- Instalación/actualizaciones del driver de NVIDIA
- Instalación de NVIDIA Container Toolkit
- Despliegue de NVIDIA Device Plugin
- Monitoreo de GPU (DCGM Exporter)
- Gestión de MIG

```bash
# Install GPU Operator (Helm)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

```yaml
# GPU Operator Custom Configuration
apiVersion: nvidia.com/v1
kind: ClusterPolicy
metadata:
  name: cluster-policy
spec:
  driver:
    enabled: true
    version: "535.104.12"
  toolkit:
    enabled: true
  devicePlugin:
    enabled: true
  mig:
    strategy: mixed
```

</details>

### 7. ¿Cuál es la principal diferencia entre las GPUs H100 y H200?

A. H200 tiene menor capacidad de memoria que H100
B. H200 proporciona memoria HBM3e con mayor ancho de banda que H100
C. H200 no admite MIG
D. H200 no es para centros de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. H200 proporciona memoria HBM3e con mayor ancho de banda que H100**

**Explicación:**
H200 es el sucesor de H100 y proporciona un sistema de memoria mejorado:

| Característica | H100 | H200 |
|---------|------|------|
| Tipo de memoria | HBM3 | HBM3e |
| Capacidad de memoria | 80 GB | 141 GB |
| Ancho de banda de memoria | 3,35 TB/s | 4,8 TB/s |
| Soporte de MIG | Sí (hasta 7) | Sí (hasta 7) |
| Inferencia de LLM | Excelente | Optimizada |

```yaml
# H200 Node Selection
apiVersion: v1
kind: Pod
spec:
  nodeSelector:
    nvidia.com/gpu.product: "NVIDIA-H200"
  containers:
  - name: llm
    resources:
      limits:
        nvidia.com/gpu: 1
```

H200 muestra un rendimiento excelente, especialmente en inferencia de modelos de lenguaje grandes (LLM), gracias a su capacidad de memoria y ancho de banda.

</details>
