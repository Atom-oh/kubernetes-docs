# Cuestionario sobre entrenamiento de modelos en EKS

Este cuestionario evalúa tu comprensión del entrenamiento de modelos en Amazon EKS, incluidas las estrategias de entrenamiento distribuido, la integración de Slurm/Slinky, el entrenamiento basado en GPU y Trainium, la configuración de almacenamiento y las técnicas de optimización.

## Preguntas del cuestionario

### 1. ¿Qué estrategia de entrenamiento distribuido divide una sola capa entre varias GPU?

A) Paralelismo de datos
B) Paralelismo de tensores
C) Paralelismo de canalización
D) Paralelismo de expertos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Paralelismo de tensores**

**Explicación:**
El paralelismo de tensores divide capas individuales (como capas de atención o redes feed-forward) entre varias GPU. Cada GPU contiene una parte de los pesos de la capa y calcula su parte de la operación.

**Comparación de estrategias de paralelismo:**

| Estrategia | Qué se distribuye | Patrón de comunicación |
|----------|---------------------|----------------------|
| Paralelismo de datos | Lotes de datos de entrenamiento | Sincronización de gradientes |
| Paralelismo de tensores | Capas individuales | Comunicación dentro de la capa |
| Paralelismo de canalización | Grupos de capas (etapas) | Paso de activaciones entre etapas |
| Paralelismo de expertos | Redes expertas en MoE | Enrutamiento de tokens |

El paralelismo de tensores es especialmente útil para capas muy grandes que no caben en la memoria de una sola GPU, como las capas de atención en modelos de lenguaje grandes.

</details>

### 2. ¿Cuál es la estrategia de paralelismo recomendada para entrenar un modelo de 200 mil millones de parámetros?

A) Solo paralelismo de datos
B) Solo paralelismo de tensores
C) Solo paralelismo de canalización
D) Paralelismo 3D (DP + TP + PP)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Paralelismo 3D (DP + TP + PP)**

**Explicación:**
Para modelos que superan los 100 mil millones de parámetros, el paralelismo 3D combina las tres estrategias para lograr la máxima eficiencia:

- **Paralelismo de datos (DP)**: Replica el modelo entre grupos de GPU, cada uno procesando lotes de datos diferentes
- **Paralelismo de tensores (TP)**: Divide capas grandes dentro de un nodo (normalmente 8 GPU con NVLink)
- **Paralelismo de canalización (PP)**: Distribuye grupos de capas entre nodos para reducir la memoria por dispositivo

Ejemplo de configuración para un modelo de 200B en 64 GPU A100:
```
TP=8  (within each node)
PP=4  (across 4 nodes)
DP=2  (2 data parallel replicas)
Total: 8 × 4 × 2 = 64 GPUs
```

Este enfoque proporciona:
- Máxima eficiencia de memoria
- Cómputo y comunicación equilibrados
- Capacidad para entrenar modelos que superan la capacidad de memoria de un solo nodo

</details>

### 3. En la arquitectura de Slinky, ¿qué componente administra la contabilidad de trabajos y el estado del clúster?

A) slurmctld
B) slurmdbd
C) slurmd
D) slurmrestd

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) slurmdbd**

**Explicación:**
Los componentes de Slinky/Slurm cumplen diferentes propósitos:

| Componente | Rol | Recurso de Kubernetes |
|-----------|------|---------------------|
| **slurmctld** | Controlador central: administra trabajos, particiones y asignación de recursos | StatefulSet |
| **slurmdbd** | Daemon de base de datos: maneja la contabilidad de trabajos, el seguimiento de uso y la persistencia del estado del clúster | StatefulSet con MySQL/MariaDB |
| **slurmd** | Daemon de cómputo: se ejecuta en cada nodo trabajador y ejecuta pasos de trabajo | DaemonSet |
| **slurmrestd** | REST API: permite el envío programático de trabajos | Deployment |

El daemon slurmdbd es crítico para:
- Almacenar datos históricos de trabajos
- Hacer seguimiento del uso de recursos para la contabilidad
- Mantener el estado del clúster para la recuperación ante fallas
- Admitir la programación fair-share basada en el uso anterior

</details>

### 4. ¿Qué CRD usa Slinky para definir grupos de nodos de cómputo (particiones)?

A) SlurmCluster
B) SlurmNodeSet
C) SlurmPartition
D) SlurmWorker

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) SlurmNodeSet**

**Explicación:**
Slinky introduce dos Custom Resource Definitions principales:

1. **SlurmCluster**: Define la configuración general del clúster, incluida:
   - Configuración del controlador (slurmctld)
   - Configuración de la base de datos (slurmdbd)
   - Configuración de REST API
   - Configuración de almacenamiento compartido

2. **SlurmNodeSet**: Define grupos de nodos de cómputo (particiones), incluidos:
   - Tipos de instancia y configuración de GPU
   - Asignación de recursos (CPU, memoria, memoria de GPU)
   - Características de nodo para GRES (Generic Resource Scheduling)
   - Configuración de autoscaling con integración de Karpenter
   - Configuración de placement group para redes de baja latencia

Ejemplo de SlurmNodeSet:
```yaml
apiVersion: slinky.slurm.net/v1alpha1
kind: SlurmNodeSet
metadata:
  name: gpu-a100-nodes
spec:
  partition: gpu-a100
  nodeCount: 4
  nodeTemplate:
    instanceType: p4d.24xlarge
    gpus:
      type: nvidia-a100
      count: 8
```

</details>

### 5. ¿Qué variable de entorno habilita EFA (Elastic Fabric Adapter) en NCCL para entrenamiento distribuido?

A) NCCL_EFA_ENABLE=1
B) FI_PROVIDER=efa
C) EFA_ENABLED=true
D) NCCL_NET=efa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FI_PROVIDER=efa**

**Explicación:**
Para habilitar redes EFA con NCCL para entrenamiento distribuido, debes establecer varias variables de entorno:

```bash
# Primary EFA configuration
export FI_PROVIDER=efa              # Use EFA as the libfabric provider
export FI_EFA_USE_DEVICE_RDMA=1     # Enable device-level RDMA
export RDMAV_FORK_SAFE=1            # Safe forking with RDMA

# NCCL configuration for EFA
export NCCL_DEBUG=INFO              # Enable debugging output
export NCCL_ALGO=Ring               # Use Ring algorithm (works well with EFA)
export NCCL_PROTO=Simple            # Simple protocol for EFA
```

EFA proporciona hasta 400 Gbps de ancho de banda de red en tipos de instancia compatibles (p4d, p5, trn1) y reduce significativamente la latencia de comunicación para el entrenamiento distribuido.

Además, los pods deben solicitar dispositivos EFA:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request 4 EFA devices
```

</details>

### 6. ¿Cuál es el propósito de NVIDIA BioNeMo en EKS?

A) Monitoreo de GPU y recopilación de métricas
B) Descubrimiento de fármacos y modelado molecular
C) Optimización de redes de contenedores
D) Cuantización y compresión de modelos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Descubrimiento de fármacos y modelado molecular**

**Explicación:**
NVIDIA BioNeMo es un framework especializado para el descubrimiento de fármacos y el modelado molecular impulsados por IA. Proporciona:

**Capacidades clave:**
- **MegaMolBART**: Generación y optimización molecular
- **ESMFold**: Predicción de estructura de proteínas
- **DiffDock**: Acoplamiento molecular
- **NVIDIA Clara**: Pipelines de descubrimiento de fármacos

**Casos de uso en EKS:**
- Generar nuevos candidatos a fármacos
- Predecir interacciones proteína-ligando
- Optimizar propiedades moleculares
- Cribado virtual de alto rendimiento

**Requisitos de Deployment:**
```yaml
resources:
  limits:
    nvidia.com/gpu: 8      # Multiple GPUs for large models
    memory: "500Gi"        # High memory for molecular datasets
```

BioNeMo aprovecha la aceleración de GPU de NVIDIA para acelerar drásticamente los flujos de trabajo de química computacional en comparación con enfoques basados en CPU.

</details>

### 7. ¿Qué paquete de Neuron SDK proporciona API de entrenamiento de alto nivel para modelos HuggingFace en Trainium?

A) torch-neuronx
B) tensorflow-neuronx
C) optimum-neuron
D) transformers-neuronx

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) optimum-neuron**

**Explicación:**
Neuron SDK incluye varios paquetes con diferentes propósitos:

| Paquete | Propósito | Nivel |
|---------|---------|-------|
| **torch-neuronx** | Integración central con PyTorch | Bajo nivel |
| **tensorflow-neuronx** | Integración central con TensorFlow | Bajo nivel |
| **transformers-neuronx** | Inferencia optimizada para transformers | Nivel medio |
| **optimum-neuron** | API de entrenamiento/inferencia de alto nivel | Alto nivel |

**optimum-neuron** forma parte de la biblioteca Optimum de HuggingFace y proporciona:
- `NeuronTrainer`: Reemplazo directo de HuggingFace Trainer
- `NeuronTrainingArguments`: Configuración de entrenamiento con opciones específicas de Neuron
- Configuración automática de paralelismo de tensores
- Integración con entrenamiento distribuido (ZeRO, paralelismo de canalización)
- Compatibilidad de checkpoints con modelos HuggingFace estándar

Ejemplo de uso:
```python
from optimum.neuron import NeuronTrainer, NeuronTrainingArguments

training_args = NeuronTrainingArguments(
    tensor_parallel_size=8,
    bf16=True,
)
trainer = NeuronTrainer(model=model, args=training_args)
trainer.train()
```

</details>

### 8. ¿Cuál es la solución de almacenamiento recomendada para el acceso de alto throughput a datos de entrenamiento distribuido en EKS?

A) Amazon EBS gp3
B) Amazon EFS
C) FSx for Lustre
D) Acceso directo a Amazon S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) FSx for Lustre**

**Explicación:**
FSx for Lustre es el almacenamiento recomendado para entrenamiento de ML distribuido debido a:

**Características de rendimiento:**
- Hasta más de 1 TB/s de throughput agregado
- Latencias inferiores al milisegundo
- Sistema de archivos paralelo optimizado para cargas de trabajo HPC/ML

**Características clave para entrenamiento de ML:**
- **Integración con S3**: Importación/exportación automática de datos con repositorios de datos S3
- **ReadWriteMany**: Varios pods pueden acceder simultáneamente
- **IOPS alto**: Crítico para patrones de acceso aleatorio en el entrenamiento
- **Soporte de checkpoints**: Escrituras rápidas de checkpoints durante el entrenamiento

**Comparación:**

| Almacenamiento | Throughput | Modo de acceso | Ideal para |
|---------|------------|-------------|----------|
| FSx Lustre | Muy alto | ReadWriteMany | Datos de entrenamiento, checkpoints |
| EFS | Medio | ReadWriteMany | Configuraciones compartidas, modelos |
| EBS | Alto | ReadWriteOnce | Cargas de trabajo de un solo nodo |
| S3 | Variable | Objeto | Datos fríos, archivos |

Ejemplo de configuración:
```yaml
lustreConfiguration:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: 250  # MB/s per TiB
  dataRepositoryAssociations:
    - fileSystemPath: /data
      dataRepositoryPath: s3://bucket/training-data
```

</details>

### 9. En un Volcano Job con `minAvailable: 4`, ¿qué sucede si solo hay 3 nodos disponibles?

A) El trabajo comienza con 3 workers
B) El trabajo espera hasta que haya 4 nodos disponibles
C) El trabajo falla de inmediato
D) El trabajo solicita nodos adicionales a Karpenter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El trabajo espera hasta que haya 4 nodos disponibles**

**Explicación:**
El campo `minAvailable` en Volcano implementa **Gang Scheduling**, que garantiza que todos los pods requeridos se programen juntos o ninguno se programe.

**Comportamiento de Gang Scheduling:**
- Si se establece `minAvailable: 4`, los 4 pods deben ser programables simultáneamente
- El trabajo permanece en estado pendiente hasta que los recursos estén disponibles
- Evita situaciones de deadlock en el entrenamiento distribuido
- Garantiza un entorno de entrenamiento consistente

**Por qué esto importa para el entrenamiento de ML:**
1. **El entrenamiento distribuido requiere todos los workers**: El entrenamiento no puede continuar con workers parciales
2. **Eficiencia de recursos**: Evita asignaciones parciales que desperdician recursos
3. **Comportamiento determinista**: El entrenamiento comienza con el paralelismo esperado

Ejemplo:
```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
spec:
  minAvailable: 4  # Gang scheduling requirement
  tasks:
    - name: worker
      replicas: 4
```

Sin gang scheduling, algunos workers podrían iniciarse mientras otros permanecen pendientes, lo que provocaría timeouts y trabajos de entrenamiento fallidos.

</details>

### 10. ¿Cuál es el beneficio de usar BF16 (bfloat16) en lugar de FP16 para el entrenamiento?

A) Mayor precisión
B) No se requiere loss scaling
C) Menor huella de memoria
D) Cómputo más rápido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No se requiere loss scaling**

**Explicación:**
BF16 (Brain Floating Point 16) tiene el mismo rango de exponentes que FP32, pero con menor precisión de mantisa:

| Formato | Bits de exponente | Bits de mantisa | Rango |
|--------|--------------|---------------|-------|
| FP32 | 8 | 23 | Grande |
| FP16 | 5 | 10 | Limitado |
| BF16 | 8 | 7 | Grande (igual que FP32) |

**Por qué BF16 no necesita loss scaling:**
- Los 8 bits de exponente de BF16 proporcionan el mismo rango dinámico que FP32
- El rango limitado de FP16 causa underflow/overflow durante el entrenamiento
- Loss scaling aumenta artificialmente los gradientes para evitar underflow en FP16

**Ventajas de BF16:**
```python
# FP16 requires loss scaling
scaler = GradScaler()
with autocast(dtype=torch.float16):
    loss = model(inputs)
scaler.scale(loss).backward()
scaler.step(optimizer)

# BF16 is simpler - no scaling needed
with autocast(dtype=torch.bfloat16):
    loss = model(inputs)
loss.backward()
optimizer.step()
```

BF16 es compatible con:
- GPU NVIDIA A100, H100 (Ampere y posteriores)
- Chips AWS Trainium
- CPU Intel Sapphire Rapids

</details>

### 11. ¿Qué logra el gradient checkpointing durante el entrenamiento?

A) Forward pass más rápido
B) Menor overhead de comunicación
C) Ahorro de memoria al recalcular activaciones
D) Mayor precisión del modelo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ahorro de memoria al recalcular activaciones**

**Explicación:**
Gradient checkpointing (también llamado activation checkpointing) intercambia cómputo por memoria al almacenar selectivamente activaciones durante el forward pass y recalcularlas durante la backpropagation.

**Cómo funciona:**
1. **Sin checkpointing**: Todas las activaciones se almacenan en memoria
2. **Con checkpointing**: Solo se almacenan las activaciones de checkpoint; las activaciones intermedias se recalculan durante el backward pass

**Ahorro de memoria:**
- Reduce la memoria de activaciones de O(n) a O(sqrt(n)), donde n es el número de capas
- Permite entrenar tamaños de batch 3-4 veces mayores
- Es crítico para entrenar modelos grandes con memoria de GPU limitada

**Configuración en PyTorch:**
```python
from torch.utils.checkpoint import checkpoint

class Model(nn.Module):
    def forward(self, x):
        # Checkpoint specific layers
        x = checkpoint(self.layer1, x)
        x = checkpoint(self.layer2, x)
        return x

# Or enable for entire model
model.gradient_checkpointing_enable()
```

**Trade-offs:**
- Aumento de aproximadamente 30% en el tiempo de cómputo
- Reducción de 3-4 veces en la memoria de activaciones
- Permite entrenar modelos/batches más grandes

</details>

### 12. ¿Qué etapa de DeepSpeed ZeRO descarga tanto los estados del optimizador COMO los parámetros del modelo a memoria de CPU?

A) ZeRO Stage 1
B) ZeRO Stage 2
C) ZeRO Stage 3
D) ZeRO Stage 0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ZeRO Stage 3**

**Explicación:**
DeepSpeed ZeRO (Zero Redundancy Optimizer) reduce progresivamente la redundancia de memoria entre etapas:

| Etapa | Particiona | CPU Offload disponible |
|-------|------------|----------------------|
| Stage 0 | Nada (baseline) | No |
| Stage 1 | Estados del optimizador | Estados del optimizador |
| Stage 2 | Estados del optimizador + Gradientes | Estados del optimizador |
| Stage 3 | Estados del optimizador + Gradientes + Parámetros | Tanto optimizador como parámetros |

**Configuración de ZeRO Stage 3:**
```json
{
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {
      "device": "cpu",
      "pin_memory": true
    },
    "offload_param": {
      "device": "cpu",
      "pin_memory": true
    }
  }
}
```

**Cuándo usar ZeRO-3:**
- Entrenar modelos más grandes que la memoria de GPU
- Cuando necesitas la máxima eficiencia de memoria
- Cuando es aceptable intercambiar algo de velocidad por memoria

**Reducción de memoria (aproximada):**
- Stage 1: reducción de 4 veces
- Stage 2: reducción de 8 veces
- Stage 3: escalado lineal con el número de GPU (teóricamente ilimitado)

</details>

### 13. ¿Cuál es el propósito del campo `slotsPerWorker` en una especificación de MPIJob?

A) Número de núcleos de CPU por worker
B) Número de dispositivos GPU por worker
C) Número de procesos MPI por worker
D) Número de interfaces de red por worker

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Número de procesos MPI por worker**

**Explicación:**
En un MPIJob, `slotsPerWorker` define cuántos rangos MPI (procesos) ejecutará cada worker pod:

```yaml
apiVersion: kubeflow.org/v1
kind: MPIJob
spec:
  slotsPerWorker: 8  # 8 MPI processes per worker
  mpiReplicaSpecs:
    Worker:
      replicas: 4  # 4 worker pods
```

**Procesos MPI totales = slotsPerWorker × réplicas Worker**
En este ejemplo: 8 × 4 = 32 procesos MPI

**Configuración común:**
- Establecer `slotsPerWorker` igual al número de GPU por nodo
- Cada rango MPI normalmente maneja una GPU
- Para nodos de 8 GPU: `slotsPerWorker: 8`

**Ejemplo de comando del launcher:**
```yaml
command:
  - mpirun
  - -np
  - "32"  # Total processes (must match slots × workers)
  - -bind-to
  - none
  - -map-by
  - slot
```

Esto garantiza que cada GPU se asigne exactamente a un proceso MPI, maximizando el paralelismo y evitando la contención de GPU.

</details>

### 14. ¿Cuál es la estrategia de frecuencia de checkpoints recomendada para trabajos de entrenamiento de larga duración?

A) Hacer checkpoint solo en cada época
B) Hacer checkpoint en cada paso para máxima seguridad
C) Hacer checkpoint cada N pasos, conservando los últimos 3-5 checkpoints
D) No hacer checkpointing para maximizar la velocidad de entrenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Hacer checkpoint cada N pasos, conservando los últimos 3-5 checkpoints**

**Explicación:**
La estrategia óptima de checkpoints equilibra la capacidad de recuperación con los costos de almacenamiento y el overhead de entrenamiento:

**Enfoque recomendado:**
```yaml
checkpoint:
  save_steps: 500           # Save every 500 steps
  save_total_limit: 5       # Keep only last 5 checkpoints
  save_on_each_node: false  # Save from rank 0 only
```

**Por qué esta estrategia:**
1. **Granularidad de recuperación**: Limita la pérdida de datos a aproximadamente 500 pasos como máximo
2. **Eficiencia de almacenamiento**: Conservar 3-5 checkpoints evita el crecimiento excesivo del almacenamiento
3. **Overhead de entrenamiento**: Hacer checkpoint en cada paso es demasiado lento
4. **Solo por época es riesgoso**: Las épocas largas significan una pérdida significativa de datos ante una falla

**Consideraciones sobre el tamaño del checkpoint:**
- Modelos grandes (70B+): Cada checkpoint puede ocupar 100-200 GB
- 5 checkpoints = 500 GB-1 TB de almacenamiento
- Usa políticas de ciclo de vida de S3 para checkpoints antiguos

**Buenas prácticas:**
```python
training_args = TrainingArguments(
    save_strategy="steps",
    save_steps=500,
    save_total_limit=5,
    save_safetensors=True,  # Faster, safer format
)
```

Para entrenamiento en producción, sincroniza también los checkpoints con almacenamiento duradero (S3) mediante un sidecar administrador de checkpoints.

</details>

### 15. ¿Qué configuración de Karpenter garantiza que los pods de entrenamiento con GPU se programen en una sola Availability Zone para un rendimiento óptimo de EFA?

A) `consolidationPolicy: WhenEmpty`
B) Requisito `topology.kubernetes.io/zone` con un solo valor
C) `karpenter.sh/capacity-type: spot`
D) `disruption.budgets.nodes: "0"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Requisito `topology.kubernetes.io/zone` con un solo valor**

**Explicación:**
EFA (Elastic Fabric Adapter) requiere que todas las instancias que se comunican estén en la misma Availability Zone. El requisito de zona de Karpenter garantiza esto:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
            - us-west-2a  # Single AZ for EFA
```

**Por qué una sola AZ importa para EFA:**
- EFA usa la interfaz de red personalizada de AWS para comunicación de alto ancho de banda y baja latencia
- La comunicación entre AZ no puede usar las capacidades RDMA de EFA
- La latencia de red aumenta significativamente entre AZ

**Otras opciones explicadas:**
- A) `consolidationPolicy`: Controla la consolidación de nodos, no la ubicación
- C) `capacity-type: spot`: Determina el modelo de precios, no la zona
- D) `disruption.budgets`: Evita la interrupción de nodos, no la selección de zona

**Configuración completa para entrenamiento con GPU:**
```yaml
requirements:
  - key: node.kubernetes.io/instance-type
    operator: In
    values: [p4d.24xlarge]
  - key: topology.kubernetes.io/zone
    operator: In
    values: [us-west-2a]  # Single zone
  - key: karpenter.sh/capacity-type
    operator: In
    values: [on-demand]   # Stability for training
```

</details>

## Resumen

Este cuestionario cubrió conceptos esenciales para el entrenamiento de modelos en EKS:

1. **Estrategias de entrenamiento distribuido**: Paralelismo de datos, tensores, canalización y expertos
2. **Integración de Slinky/Slurm**: Componentes (slurmctld, slurmdbd, slurmd) y CRD
3. **Entrenamiento con GPU**: Configuración de NCCL, redes EFA, BioNeMo
4. **Entrenamiento con Trainium**: Paquetes de Neuron SDK, optimum-neuron
5. **Almacenamiento**: FSx for Lustre para entrenamiento de alto throughput
6. **Scheduling**: Gang scheduling de Volcano
7. **Optimización**: Precisión mixta (BF16), gradient checkpointing, DeepSpeed ZeRO
8. **Infraestructura**: Karpenter NodePools, administración de checkpoints

Para obtener más información, consulta la documentación de [entrenamiento de modelos en EKS](../../ai-ml/05-model-training.md).
