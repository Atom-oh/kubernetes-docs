# Cuestionario sobre infraestructura de AI en EKS

Este cuestionario evalúa tu comprensión de los patrones de infraestructura de AI/ML en Amazon EKS, incluyendo JARK Stack, Dynamic Resource Allocation y plataformas de producción para workloads de AI.

## Preguntas del cuestionario

### 1. ¿Qué significa JARK Stack en el contexto de la infraestructura de AI/ML en EKS?

A) Java, Ansible, Redis, Kafka
B) JupyterHub, Argo Workflows, Ray, Karpenter
C) Jenkins, Airflow, RabbitMQ, Kubernetes
D) JupyterLab, Apache Spark, Ray, Kubeflow

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) JupyterHub, Argo Workflows, Ray, Karpenter**

**Explicación:**
JARK Stack es un entorno completo de desarrollo de AI/ML en EKS que consiste en:

- **JupyterHub**: Entorno de desarrollo interactivo multiusuario con perfiles de notebook habilitados para GPU
- **Argo Workflows**: Orquestación de pipelines de ML con workflows basados en DAG
- **Ray (KubeRay)**: Computación distribuida unificada para entrenamiento, ajuste y servicio
- **Karpenter**: Aprovisionamiento de nodos rápido y rentable con soporte para GPU y Neuron

Este stack proporciona todo lo necesario para que científicos de datos e ingenieros de ML desarrollen, entrenen e implementen modelos de ML en Kubernetes.

</details>

### 2. ¿Qué método de autenticación se usa comúnmente con JupyterHub en EKS para entornos empresariales?

A) Nombre de usuario/contraseña básicos almacenados en ConfigMaps
B) Autenticación basada en claves SSH
C) Amazon Cognito con OAuth
D) Tokens de Kubernetes ServiceAccount

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon Cognito con OAuth**

**Explicación:**
Amazon Cognito con OAuth es el método de autenticación recomendado para JupyterHub en EKS en entornos empresariales porque:

1. **Single Sign-On (SSO)**: Se integra con proveedores de identidad corporativos (SAML, OIDC)
2. **Autenticación multifactor**: Soporta MFA para mejorar la seguridad
3. **Gestión de usuarios**: Gestión centralizada de usuarios y control de acceso
4. **Escalabilidad**: Servicio administrado que escala con tu base de usuarios
5. **Cumplimiento**: Ayuda a cumplir requisitos de cumplimiento de seguridad

Ejemplo de configuración:
```python
c.JupyterHub.authenticator_class = 'oauthenticator.generic.GenericOAuthenticator'
c.GenericOAuthenticator.oauth_callback_url = 'https://jupyter.example.com/hub/oauth_callback'
c.GenericOAuthenticator.authorize_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize'
```

</details>

### 3. En Ray en Kubernetes, ¿cuál es el propósito del nodo Ray Head?

A) Almacenar todos los datos de entrenamiento y los pesos del modelo
B) Coordinar el cluster, ejecutar el dashboard y gestionar la programación de workers
C) Realizar exclusivamente todos los cálculos de GPU
D) Manejar solo solicitudes de API externas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Coordinar el cluster, ejecutar el dashboard y gestionar la programación de workers**

**Explicación:**
El nodo Ray Head actúa como coordinador central del cluster de Ray:

1. **Global Control Store (GCS)**: Gestiona los metadatos y el estado del cluster
2. **Dashboard**: Ejecuta el dashboard de Ray para monitoreo y depuración (puerto 8265)
3. **Conexiones de clientes**: Acepta conexiones desde clientes de Ray (puerto 10001)
4. **Programación**: Coordina la programación de tareas y actores entre workers
5. **Autoscaling**: Trabaja con el autoscaler de KubeRay para escalar grupos de workers

El nodo Head normalmente no ejecuta workloads de cómputo intensivo por sí mismo; estos se distribuyen a los nodos worker según los requisitos de recursos (CPU, GPU, memoria).

```yaml
headGroupSpec:
  rayStartParams:
    dashboard-host: '0.0.0.0'
    block: 'true'
```

</details>

### 4. ¿Cuál es la principal ventaja de Dynamic Resource Allocation (DRA) sobre los device plugins tradicionales de Kubernetes para la programación de GPU?

A) DRA detecta el hardware de GPU más rápido
B) DRA permite compartir GPU con granularidad fina (MIG, MPS, time-slicing) y programación consciente de la topología
C) DRA requiere menos sobrecarga de memoria
D) DRA solo funciona con GPU NVIDIA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) DRA permite compartir GPU con granularidad fina (MIG, MPS, time-slicing) y programación consciente de la topología**

**Explicación:**
Dynamic Resource Allocation (DRA) proporciona capacidades que los device plugins tradicionales no pueden ofrecer:

| Característica | Device Plugin tradicional | DRA |
|---------|--------------------------|-----|
| Asignación de GPU | Solo GPU completa | Fraccionaria (MIG, MPS, time-slice) |
| Conciencia de topología | Limitada | Consciente de NVLink/IMEX |
| Modos de uso compartido | Time-slicing básico | MIG, MPS, time-slicing, exclusivo |
| Resource Claims | Estáticos | Dinámicos con restricciones |
| Programación multi-GPU | Independiente | Restringida por topología |

DRA usa ResourceClaims y ResourceSlices para proporcionar:
- Particionado de memoria de GPU con granularidad fina (perfiles MIG como 3g.20gb)
- Uso compartido del contexto CUDA mediante MPS
- Time-slicing para workloads de desarrollo
- Programación consciente de la topología para GPU conectadas por NVLink

Esto es esencial para P6e-GB200 UltraServers con 72 GPU interconectadas.

</details>

### 5. ¿Qué estrategia para compartir GPU proporciona el aislamiento más fuerte entre workloads?

A) Time-Slicing
B) MPS (Multi-Process Service)
C) MIG (Multi-Instance GPU)
D) Modo exclusivo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) MIG (Multi-Instance GPU)**

**Explicación:**
Entre las estrategias para compartir GPU, MIG proporciona el aislamiento más fuerte sin dejar de permitir el uso compartido:

| Estrategia | Nivel de aislamiento | Cómo funciona |
|----------|----------------|--------------|
| **Exclusivo** | Completo (sin compartir) | Un workload por GPU |
| **MIG** | Fuerte (hardware) | Instancias de GPU particionadas por hardware |
| **MPS** | Medio | Contexto CUDA compartido con límites de threads |
| **Time-Slicing** | Débil | Cambio de contexto entre workloads |

MIG (disponible en GPU A100/H100) proporciona:
- **Aislamiento de hardware**: Cada instancia MIG tiene unidades SM, memoria y caché dedicadas
- **Aislamiento de fallos**: Los errores en una instancia no afectan a las demás
- **Garantías de QoS**: Rendimiento predecible por instancia
- **Protección de memoria**: Espacios de memoria separados evitan la filtración de datos

Ejemplos de perfiles MIG para A100 80GB:
- `7g.80gb` - GPU completa
- `3g.40gb` - Media GPU (2 instancias)
- `1g.10gb` - 1/7 de GPU (7 instancias)

</details>

### 6. ¿Cuál es la versión mínima de NVIDIA GPU Operator requerida para soporte completo de DRA?

A) v22.9.0
B) v23.6.0
C) v24.3.0
D) v25.3.0

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) v25.3.0**

**Explicación:**
NVIDIA GPU Operator v25.3.0 o posterior es requerido para soporte completo de Dynamic Resource Allocation (DRA). Esta versión incluye:

1. **Driver DRA**: Driver DRA nativo para la gestión de recursos de GPU
2. **Soporte de ResourceSlice**: Expone información de topología de GPU
3. **Configuración de uso compartido**: MIG, MPS y time-slicing mediante DRA
4. **Expresiones CEL**: Selección de dispositivos usando Common Expression Language

Configuración con DRA habilitado:
```yaml
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
```

Las versiones anteriores solo soportan el modo de device plugin tradicional sin el control de granularidad fina que proporciona DRA.

</details>

### 7. En la plataforma Agents on EKS, ¿cuál es el propósito de Langfuse?

A) Base de datos vectorial para almacenar embeddings
B) Control de código fuente y pipelines de CI/CD
C) Observabilidad, tracing y monitoreo de LLM
D) Descubrimiento y registro de tools

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Observabilidad, tracing y monitoreo de LLM**

**Explicación:**
Langfuse es una plataforma open-source de observabilidad de LLM que proporciona:

1. **Tracing**: Trazas end-to-end de interacciones con LLM
2. **Gestión de prompts**: Versiona y gestiona prompts
3. **Evaluación**: Puntúa y evalúa salidas de LLM
4. **Analítica**: Métricas de uso, latencia y seguimiento de costos
5. **Depuración**: Identifica problemas en chains y agents de LLM

En la arquitectura de la plataforma Agents on EKS:
- **GitLab**: Control de código fuente y CI/CD
- **Langfuse**: Observabilidad y tracing de LLM
- **Milvus**: Base de datos vectorial para RAG
- **MCP Gateway**: Descubrimiento y registro de tools

Ejemplo de integración:
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-xxx",
    secret_key="sk-xxx",
    host="https://langfuse.agents.example.com"
)

# Trace LLM calls
trace = langfuse.trace(name="customer-support-agent")
```

</details>

### 8. ¿Qué solución de almacenamiento se recomienda para workloads de entrenamiento distribuido de alto throughput en EKS?

A) Volúmenes Amazon EBS gp3
B) Amazon EFS con modo de rendimiento estándar
C) Amazon FSx for Lustre
D) Amazon S3 con Mountpoint

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon FSx for Lustre**

**Explicación:**
Amazon FSx for Lustre es la solución de almacenamiento recomendada para entrenamiento distribuido de alto throughput porque:

1. **Alto throughput**: Hasta 1000+ MB/s por TiB de almacenamiento
2. **Baja latencia**: Latencias inferiores a un milisegundo para operaciones de metadatos
3. **Integración con S3**: Integración nativa de repositorio de datos con S3
4. **Acceso paralelo**: Optimizado para workloads de sistema de archivos paralelo
5. **Cumplimiento POSIX**: Soporte POSIX completo para frameworks de ML

Comparación de almacenamiento para AI/ML:

| Almacenamiento | Throughput | Caso de uso |
|---------|------------|----------|
| EFS | Hasta 10 GB/s | Notebooks compartidos, almacenamiento de modelos |
| FSx Lustre | Hasta 1+ TB/s | Entrenamiento distribuido, HPC |
| S3 + Mountpoint | Variable | Datos fríos, checkpoints |
| EBS gp3 | 1 GB/s máx. | Workloads de un solo nodo |

Configuración de FSx for Lustre:
```yaml
parameters:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: "500"  # MB/s per TiB
  dataCompressionType: LZ4
  s3ImportPath: s3://ml-datasets
```

</details>

### 9. ¿Para qué se usa EFA (Elastic Fabric Adapter) en workloads de AI/ML?

A) Cifrar datos en reposo en nodos GPU
B) Redes de alto bandwidth y baja latencia para entrenamiento distribuido multinodo
C) Gestionar la asignación de memoria de GPU
D) Autenticar workloads ante servicios externos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Redes de alto bandwidth y baja latencia para entrenamiento distribuido multinodo**

**Explicación:**
Elastic Fabric Adapter (EFA) es la interfaz de red de alto rendimiento de AWS para workloads de HPC y ML:

1. **Alto bandwidth**: Hasta 3200 Gbps (trn1n.32xlarge con 16x EFA)
2. **Baja latencia**: Baja latencia constante para operaciones colectivas
3. **OS Bypass**: Acceso directo al hardware evitando el kernel
4. **Integración con NCCL**: Optimizado para NVIDIA Collective Communications Library

Instancias compatibles con EFA para AI/ML:
- `p4d.24xlarge`: 4x 400 Gbps EFA
- `p5.48xlarge`: 32x 400 Gbps EFA
- `trn1.32xlarge`: 8x 800 Gbps EFA
- `trn1n.32xlarge`: 16x 1600 Gbps EFA

Variables de entorno para EFA con NCCL:
```yaml
env:
- name: FI_PROVIDER
  value: "efa"
- name: FI_EFA_USE_DEVICE_RDMA
  value: "1"
- name: NCCL_ALGO
  value: "Ring,Tree"
```

Solicitud de recursos:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4
```

</details>

### 10. ¿Qué métrica de Prometheus indica agotamiento de memoria de GPU que requiere atención inmediata?

A) DCGM_FI_DEV_GPU_UTIL > 80
B) DCGM_FI_DEV_GPU_TEMP > 70
C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95
D) DCGM_FI_DEV_SM_CLOCK < 1000

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95**

**Explicación:**
Esta métrica calcula el porcentaje de utilización del frame buffer (memoria) de la GPU. Cuando supera el 95 %, la GPU está casi sin memoria:

Métricas clave de DCGM para el monitoreo de GPU:

| Métrica | Descripción | Umbral crítico |
|--------|-------------|-------------------|
| `DCGM_FI_DEV_FB_USED` | Memoria de frame buffer usada | - |
| `DCGM_FI_DEV_FB_FREE` | Memoria de frame buffer libre | - |
| `DCGM_FI_DEV_GPU_UTIL` | Utilización de cómputo de GPU | <20% (infrautilizada) |
| `DCGM_FI_DEV_GPU_TEMP` | Temperatura de GPU | >85C (sobrecalentamiento) |
| `DCGM_FI_DEV_XID_ERRORS` | Conteo de errores de hardware | >0 (problema de hardware) |

Regla de alerta para agotamiento de memoria:
```yaml
- alert: GPUMemoryExhausted
  expr: (DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100 > 95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "GPU memory nearly exhausted"
```

Causas del agotamiento de memoria:
- Errores OOM (Out of Memory)
- Fallos en trabajos de entrenamiento
- Rechazos de solicitudes de inferencia

</details>

### 11. ¿Cuál es el propósito de la característica de consolidación de Karpenter para workloads de GPU?

A) Fusionar varias GPU en una sola GPU virtual
B) Combinar checkpoints de entrenamiento en un solo archivo
C) Hacer bin-packing de workloads y eliminar nodos infrautilizados para ahorrar costos
D) Consolidar logs de varios pods GPU

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Hacer bin-packing de workloads y eliminar nodos infrautilizados para ahorrar costos**

**Explicación:**
La característica de consolidación de Karpenter optimiza los costos del cluster mediante:

1. **Bin-Packing**: Mover workloads a menos nodos y más utilizados
2. **Eliminación de nodos**: Terminar nodos vacíos o infrautilizados
3. **Right-Sizing**: Reemplazar nodos por tipos de instancia más adecuados
4. **Reducción de costos**: Minimizar recursos de GPU inactivos

Políticas de consolidación:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

- **WhenEmpty**: Consolidar solo nodos completamente vacíos
- **WhenEmptyOrUnderutilized**: Consolidar nodos vacíos o infrautilizados

Para workloads de GPU, la consolidación es crítica porque:
- Las instancias GPU son caras ($3-30+/hora)
- Las GPU infrautilizadas desperdician costos significativos
- Los trabajos de entrenamiento a menudo finalizan y dejan nodos inactivos

Buenas prácticas:
- Usa `consolidateAfter` más corto para desarrollo (5m)
- Usa periodos más largos para entrenamiento de producción (30m)
- Establece `limits` adecuados para evitar escalado descontrolado

</details>

### 12. En DRA, ¿para qué se usa un ResourceSlice?

A) Dividir recursos de CPU entre contenedores
B) Representar los recursos de GPU disponibles y su topología en un nodo
C) Dividir el bandwidth de red para diferentes workloads
D) Particionar volúmenes de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Representar los recursos de GPU disponibles y su topología en un nodo**

**Explicación:**
ResourceSlice es un recurso de DRA que representa los dispositivos disponibles y su topología:

```yaml
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
```

ResourceSlice proporciona:
1. **Inventario de dispositivos**: Lista todos los dispositivos disponibles en un nodo
2. **Atributos**: Modelo de GPU, memoria, capacidades
3. **Información de topología**: Conexiones NVLink, nodo NUMA, NVSwitch
4. **Capacidad**: Recursos disponibles para la programación

El scheduler usa ResourceSlices para:
- Encontrar nodos con los tipos de GPU requeridos
- Programar workloads multi-GPU conscientes de la topología
- Asegurar que las GPU conectadas por NVLink se asignen juntas

</details>

### 13. ¿Qué componente en la plataforma Agents on EKS proporciona almacenamiento vectorial para RAG (Retrieval-Augmented Generation)?

A) GitLab
B) Langfuse
C) Milvus
D) MCP Gateway

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Milvus**

**Explicación:**
Milvus es una base de datos vectorial open-source optimizada para aplicaciones de AI:

1. **Almacenamiento vectorial**: Almacena vectores de embeddings de alta dimensionalidad
2. **Búsqueda por similitud**: Búsqueda aproximada rápida de vecinos más cercanos (ANN)
3. **Aceleración con GPU**: Los nodos de consulta e índice pueden usar GPU
4. **Escalabilidad**: Arquitectura distribuida para implementaciones a gran escala

Arquitectura RAG con Milvus:
```
User Query → Embedding Model → Milvus (vector search) → Retrieved Context → LLM → Response
```

Configuración de Milvus en EKS:
```yaml
queryNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU-accelerated search

indexNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU-accelerated indexing
```

Integración con Agent:
```python
from pymilvus import connections, Collection

connections.connect(host="milvus.milvus.svc.cluster.local", port="19530")
collection = Collection("knowledge_base")

# Search for similar documents
results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param={"metric_type": "IP", "params": {"nprobe": 10}},
    limit=5
)
```

</details>

### 14. ¿Cuál es el enfoque recomendado para manejar fallos de nodos GPU durante el entrenamiento distribuido?

A) Reiniciar manualmente el entrenamiento desde cero
B) Usar checkpointing con frameworks de entrenamiento tolerantes a fallos como Ray Train
C) Aumentar el número de réplicas GPU para prevenir fallos
D) Usar solo instancias on-demand para evitar interrupciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar checkpointing con frameworks de entrenamiento tolerantes a fallos como Ray Train**

**Explicación:**
Checkpointing con frameworks tolerantes a fallos es el enfoque recomendado porque:

1. **Recuperación automática**: El entrenamiento se reanuda desde el último checkpoint
2. **Eficiencia de costos**: Permite usar instancias Spot más económicas
3. **Escalabilidad**: Maneja cambios dinámicos en el tamaño del cluster
4. **Preservación del progreso**: Minimiza el tiempo de cómputo perdido

Ray Train con checkpointing:
```python
from ray.train.torch import TorchTrainer
from ray.train import Checkpoint, ScalingConfig

def train_loop_per_worker():
    # Load from checkpoint if available
    checkpoint = ray.train.get_checkpoint()
    if checkpoint:
        with checkpoint.as_directory() as checkpoint_dir:
            model.load_state_dict(torch.load(f"{checkpoint_dir}/model.pt"))

    for epoch in range(epochs):
        # Training logic
        train_epoch()

        # Save checkpoint
        with tempfile.TemporaryDirectory() as temp_dir:
            torch.save(model.state_dict(), f"{temp_dir}/model.pt")
            ray.train.report(
                {"loss": loss},
                checkpoint=Checkpoint.from_directory(temp_dir)
            )

trainer = TorchTrainer(
    train_loop_per_worker,
    scaling_config=ScalingConfig(
        num_workers=4,
        use_gpu=True,
    ),
    run_config=ray.train.RunConfig(
        checkpoint_config=ray.train.CheckpointConfig(
            num_to_keep=3,
            checkpoint_frequency=10,
        )
    )
)
```

</details>

### 15. ¿Cuál es el propósito de MCP Gateway en la plataforma Agents on EKS?

A) Enrutar tráfico entre microservicios
B) Gestionar registros de imágenes de contenedor
C) Proporcionar descubrimiento y registro de tools para AI agents
D) Cifrar la comunicación entre pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Proporcionar descubrimiento y registro de tools para AI agents**

**Explicación:**
MCP (Model Context Protocol) Gateway proporciona descubrimiento y gestión de tools para AI agents:

1. **Registro de tools**: Registro central de tools/funciones disponibles
2. **Descubrimiento**: Descubrimiento automático de tools en Kubernetes
3. **Enrutamiento**: Enruta llamadas de tools a los backends adecuados
4. **Autenticación**: Control de acceso basado en OIDC
5. **Rate Limiting**: Previene el abuso de tools

Configuración de MCP Gateway:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-gateway-config
data:
  config.yaml: |
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
```

Integración con Agent:
```python
# Agent discovers and uses tools via MCP Gateway
env:
- name: MCP_GATEWAY_URL
  value: "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"
```

MCP permite a los agents:
- Descubrir tools disponibles dinámicamente
- Llamar APIs y servicios externos
- Acceder a bases de datos y sistemas de archivos
- Ejecutar código y comandos

</details>

---

## Resumen

Este cuestionario cubrió conceptos clave de infraestructura de AI en EKS:

- **JARK Stack**: JupyterHub + Argo Workflows + Ray + Karpenter para entornos de ML completos
- **Dynamic Resource Allocation**: Programación de GPU con granularidad fina mediante MIG, MPS y time-slicing
- **Agents Platform**: GitLab + Langfuse + Milvus + MCP Gateway para el desarrollo de AI agents
- **Almacenamiento**: EFS para compartir, FSx Lustre para entrenamiento de alto throughput
- **Redes**: EFA para entrenamiento distribuido multinodo
- **Monitoreo**: Métricas DCGM y alertas Prometheus para observabilidad de GPU

Para más detalles, consulta la documentación de [AI Infrastructure on EKS](../../ai-ml/06-ai-infrastructure.md).
