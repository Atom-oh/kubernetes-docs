# vLLM Deployment Quiz

Este cuestionario evalúa tu comprensión sobre el despliegue de vLLM (Vector Language Model) en Kubernetes.

## Quiz Questions

### 1. What is the main purpose of vLLM (Vector Language Model)?

A. Aceleración del procesamiento de imágenes
B. Optimización y aceleración de la inferencia de Large Language Model (LLM)
C. Optimización de consultas de bases de datos
D. Gestión del tráfico de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Optimización y aceleración de la inferencia de Large Language Model (LLM)**

**Explicación:**
El propósito principal de vLLM (Vector Language Model) es optimizar y acelerar la inferencia de Large Language Model (LLM). vLLM utiliza un algoritmo de atención innovador llamado PagedAttention para optimizar la gestión de memoria, lo que permite inferencia de LLM con alto throughput y baja latencia.

**Características clave de vLLM:**
1. **PagedAttention**: Mecanismo de atención eficiente en memoria que optimiza el uso de memoria de GPU.
2. **Continuous batching**: Agrupa dinámicamente las solicitudes en batches para mejorar el throughput.
3. **Inferencia distribuida**: Distribuye modelos grandes entre múltiples GPUs y nodes.
4. **Soporte para varios modelos**: Admite varios LLMs open-source, incluidos Llama, GPT-NeoX, Falcon y MPT.
5. **API compatible con OpenAI**: Proporciona una interfaz compatible con la API de OpenAI.

**Cómo funciona PagedAttention:**
PagedAttention es una técnica inspirada en la gestión de memoria virtual de los sistemas operativos, que administra de forma eficiente la cache KV (Key-Value). Los métodos tradicionales asignan bloques de memoria de tamaño fijo para cada solicitud, pero PagedAttention asigna solo la memoria necesaria y la reutiliza.

**Beneficios de rendimiento de vLLM:**
1. **Alto throughput**: Throughput 2-4 veces mayor en comparación con las soluciones existentes
2. **Eficiencia de memoria**: Puede manejar hasta 8 veces más solicitudes concurrentes
3. **Baja latencia**: Tiempo de respuesta reducido mediante una gestión de memoria eficiente
4. **Mejor utilización de recursos**: Uso más eficiente de los recursos de GPU

**Casos de uso de vLLM:**
1. **Servicios de IA conversacional**: Chatbots, asistentes virtuales, etc.
2. **Servicios de generación de texto**: Generación de contenido, resumen, traducción, etc.
3. **Generación y completado de código**: Herramientas de apoyo a la programación
4. **Procesamiento de texto a gran escala**: Análisis de documentos, extracción de información, etc.

**Problemas con las otras opciones:**
- A. Aceleración del procesamiento de imágenes: vLLM es para modelos de lenguaje basados en texto y no está especializado en procesamiento de imágenes.
- C. Optimización de consultas de bases de datos: vLLM no está relacionado con la optimización de consultas de bases de datos.
- D. Gestión del tráfico de red: vLLM no está relacionado con la gestión del tráfico de red.
</details>

### 2. What is the most important resource requirement when deploying vLLM in Kubernetes?

A. CPU y memoria grandes
B. GPU de alto rendimiento y memoria de GPU suficiente
C. Interfaz de red de alta velocidad
D. Almacenamiento persistente grande

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. GPU de alto rendimiento y memoria de GPU suficiente**

**Explicación:**
El requisito de recursos más importante al desplegar vLLM en Kubernetes es una GPU de alto rendimiento y memoria de GPU suficiente. Los Large Language Models (LLMs) tienen miles de millones o cientos de miles de millones de parámetros, y una capacidad de cómputo de GPU potente y memoria de GPU suficiente para almacenar los parámetros del modelo son esenciales para ejecutar estos modelos de manera eficiente.

**Requisitos de GPU:**
1. **Tipo de GPU**: GPUs de alto rendimiento como NVIDIA A100, H100, V100, RTX A6000
2. **Memoria de GPU**: Varía según el tamaño del modelo, pero generalmente:
   - Modelo de 7B parámetros: Mínimo 16GB de memoria de GPU
   - Modelo de 13B parámetros: Mínimo 24GB de memoria de GPU
   - Modelo de 70B parámetros: Mínimo 80GB de memoria de GPU o distribuido entre múltiples GPUs
3. **Número de GPUs**: Depende de los requisitos de throughput y del tamaño del modelo, pero los modelos grandes deben distribuirse entre múltiples GPUs.

**Ejemplo de solicitud de recursos de GPU para un deployment de vLLM:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            nvidia.com/gpu: 1
            cpu: 4
            memory: 16Gi
```

**Ejemplo de deployment distribuido para modelos grandes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-large
  template:
    metadata:
      labels:
        app: vllm-large
    spec:
      nodeSelector:
        gpu-type: a100-80gb
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
        - --max-model-len=4096
        resources:
          limits:
            nvidia.com/gpu: 8
          requests:
            nvidia.com/gpu: 8
            cpu: 32
            memory: 128Gi
```

**Cálculo del requisito de memoria de GPU:**
Los requisitos de memoria de GPU para LLM están determinados por los siguientes factores:
1. **Parámetros del modelo**: Cada parámetro normalmente ocupa 2 bytes (FP16) o 4 bytes (FP32).
2. **KV cache**: La cache key-value para cada token requiere memoria adicional.
3. **Tamaño de batch**: Los requisitos de memoria aumentan a medida que aumenta el número de solicitudes concurrentes.
4. **Longitud de contexto**: Las longitudes de contexto más largas requieren más memoria de KV cache.

**Fórmula aproximada del requisito de memoria:**
```
Required GPU memory = Model size + (batch size x sequence length x hidden size x layers x 4 bytes)
```

**Otros requisitos de recursos:**
1. **CPU**: Núcleos de CPU suficientes para preprocesamiento y postprocesamiento
2. **Memoria del sistema**: RAM suficiente para la carga y el procesamiento del modelo
3. **Almacenamiento**: Almacenamiento suficiente para los archivos de pesos del modelo
4. **Red**: Conexión de red de alta velocidad para inferencia distribuida

**Problemas con las otras opciones:**
- A. CPU y memoria grandes: La CPU no es eficiente para la inferencia de LLM, y la memoria del sistema por sí sola no puede reemplazar la memoria de GPU.
- C. Interfaz de red de alta velocidad: Es importante para la inferencia distribuida, pero tiene menor prioridad que la GPU y la memoria de GPU.
- D. Almacenamiento persistente grande: Necesario para almacenar pesos del modelo, pero no impacta directamente el rendimiento de inferencia.
</details>
### 3. What is the optimal storage solution for vLLM in Kubernetes?

A. Volumen emptyDir
B. Volumen hostPath
C. Sistema de archivos distribuido de alto rendimiento (por ejemplo, FSx for Lustre)
D. Sistema de archivos de red normal (NFS)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Sistema de archivos distribuido de alto rendimiento (por ejemplo, FSx for Lustre)**

**Explicación:**
La solución de almacenamiento óptima para vLLM en Kubernetes es un sistema de archivos distribuido de alto rendimiento (por ejemplo, FSx for Lustre). vLLM necesita cargar rápidamente archivos de pesos del modelo para procesar large language models, y en entornos de inferencia distribuida, varios nodes necesitan acceder simultáneamente a los mismos archivos de modelo. Los sistemas de archivos distribuidos de alto rendimiento cumplen estos requisitos proporcionando alto throughput, baja latencia y capacidades de acceso paralelo.

**Ventajas de los sistemas de archivos distribuidos de alto rendimiento:**
1. **Alto throughput**: Pueden cargar rápidamente archivos de modelo grandes.
2. **Acceso paralelo**: Varios nodes pueden acceder simultáneamente a los mismos archivos.
3. **Escalabilidad**: La capacidad y el rendimiento de almacenamiento pueden escalarse según sea necesario.
4. **Consistencia de datos**: Proporciona una vista de datos consistente entre múltiples nodes.
5. **Durabilidad**: Reduce el riesgo de pérdida de datos mediante replicación de datos y funciones de backup.

**Ejemplo de configuración de AWS FSx for Lustre:**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: SCRATCH_2
  automaticBackupRetentionDays: "0"
  dailyAutomaticBackupStartTime: "00:00"
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
mountOptions:
  - flock

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi

---
# Use in vLLM deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=/models/llama-2-70b
        - --tensor-parallel-size=8
        volumeMounts:
        - name: model-storage
          mountPath: /models
        resources:
          limits:
            nvidia.com/gpu: 8
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: vllm-models
```

**Ejemplo de configuración de Google Cloud Filestore:**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: filestore-hpc
provisioner: filestore.csi.storage.gke.io
parameters:
  tier: ENTERPRISE
  network: default
  location: us-central1-a

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: filestore-hpc
  resources:
    requests:
      storage: 1200Gi
```

**Ejemplo de configuración de Azure NetApp Files:**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: netapp-files-premium
provisioner: netapp.io/trident
parameters:
  backendType: "azure-netapp-files"
  serviceLevel: "Premium"

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: netapp-files-premium
  resources:
    requests:
      storage: 1200Gi
```

**Comparación con otras opciones de almacenamiento:**

| Storage Option | Throughput | Latency | Multi-node Access | Scalability | Persistence |
|----------------|------------|---------|-------------------|-------------|-------------|
| emptyDir | High | Very low | Not possible | Limited | Temporary |
| hostPath | High | Very low | Not possible | Limited | Node-dependent |
| NFS | Medium | Medium | Possible | Medium | Persistent |
| FSx for Lustre | Very high | Low | Possible | High | Persistent |
| Google Filestore | High | Low | Possible | High | Persistent |
| Azure NetApp Files | High | Low | Possible | High | Persistent |

**Estrategias de optimización del rendimiento de carga de modelos:**
1. **Memory mapping**: Reduce el tiempo de carga al mapear directamente archivos de modelo grandes en memoria
2. **Model sharding**: Divide el modelo en múltiples shards y los carga en paralelo
3. **Caching**: Guarda en cache los modelos usados con frecuencia en memoria para evitar recargas
4. **Pre-loading**: Precarga modelos al iniciar el Service para reducir la latencia de la primera solicitud

**Problemas con las otras opciones:**
- A. Volumen emptyDir: Almacenamiento temporal donde los datos se pierden cuando el Pod se reinicia. No es adecuado para almacenar archivos de modelo grandes.
- B. Volumen hostPath: Depende del almacenamiento local del node, lo que dificulta compartir datos en entornos multi-node.
- D. Sistema de archivos de red normal (NFS): El rendimiento es inferior al de los sistemas de archivos distribuidos de alto rendimiento en términos de throughput y latencia.
</details>

### 4. What is the main purpose of Tensor Parallelism in vLLM?

A. Procesar múltiples solicitudes de usuarios en paralelo
B. Distribuir modelos grandes entre múltiples GPUs para reducir los requisitos de memoria
C. Acelerar el preprocesamiento de datos
D. Optimizar la comunicación de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Distribuir modelos grandes entre múltiples GPUs para reducir los requisitos de memoria**

**Explicación:**
El propósito principal de Tensor Parallelism en vLLM es distribuir modelos grandes entre múltiples GPUs para reducir los requisitos de memoria. Los Large Language Models (LLMs) a menudo tienen miles de millones o cientos de miles de millones de parámetros que exceden la capacidad de memoria de una sola GPU. Tensor parallelism resuelve este problema dividiendo las capas del modelo entre múltiples GPUs, de modo que cada GPU almacene y procese solo una parte del modelo.

**Cómo funciona Tensor Parallelism:**
1. **División del modelo**: Divide cada capa del modelo (especialmente las capas de atención y MLP) entre múltiples GPUs.
2. **Cómputo paralelo**: Cada GPU realiza cálculos sobre la parte del modelo que tiene asignada.
3. **Sincronización**: Sincroniza resultados intermedios entre GPUs cuando es necesario.
4. **Agregación de resultados**: Agrega los resultados de cada GPU para generar la salida final.

**Ejemplo de configuración de tensor parallelism en vLLM:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-tensor-parallel
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      nodeSelector:
        nvidia.com/gpu.product: A100-SXM4-80GB
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8  # Distribute model across 8 GPUs
        - --max-model-len=4096
        - --gpu-memory-utilization=0.9
        resources:
          limits:
            nvidia.com/gpu: 8  # Request 8 GPUs
```

**Guía de selección del tamaño de tensor parallelism:**
1. **Tamaño del modelo**: El tamaño requerido de tensor parallelism depende del número de parámetros del modelo.
   - Modelo de 7B parámetros: 1-2 GPUs
   - Modelo de 13B parámetros: 2-4 GPUs
   - Modelo de 70B parámetros: 8-16 GPUs
   - Modelo de 175B parámetros: 16+ GPUs

2. **Memoria de GPU**: El tamaño de tensor parallelism debe ajustarse según la memoria de GPU disponible.
   - GPU de 24GB: Adecuada para modelos pequeños
   - GPU de 40GB: Adecuada para modelos medianos
   - GPU de 80GB: Adecuada para modelos grandes

3. **Consideraciones de rendimiento**: Tensor parallelism genera overhead de comunicación GPU a GPU.
   - Tamaño de tensor parallelism demasiado pequeño: Problemas de falta de memoria
   - Tamaño de tensor parallelism demasiado grande: Degradación del rendimiento debido al overhead de comunicación

**Tensor Parallelism frente a otras técnicas de paralelización:**
1. **Data Parallelism**: Múltiples copias del mismo modelo procesan diferentes batches de datos. Se usa principalmente para entrenamiento.
2. **Pipeline Parallelism**: Distribuye las capas del modelo secuencialmente entre múltiples GPUs.
3. **Tensor Parallelism**: Distribuye los cálculos de capas individuales entre múltiples GPUs.

**Ventajas de Tensor Parallelism:**
1. **Eficiencia de memoria**: Reduce los requisitos de memoria al distribuir modelos grandes entre múltiples GPUs
2. **Latencia reducida para solicitudes individuales**: Mejora la velocidad de inferencia mediante cómputo paralelo
3. **Mejor utilización de recursos**: Uso más eficiente de los recursos de GPU

**Desventajas de Tensor Parallelism:**
1. **Overhead de comunicación**: Overhead por transferencia de datos entre GPUs
2. **Complejidad de implementación**: Lógica compleja de división del modelo y sincronización
3. **Requisitos de hardware**: Requiere interconexiones GPU de alta velocidad (NVLink, NVSwitch, etc.)

**Problemas con las otras opciones:**
- A. Procesar múltiples solicitudes de usuarios en paralelo: Este es el propósito del procesamiento por batches o del paralelismo de solicitudes.
- C. Acelerar el preprocesamiento de datos: Tensor parallelism se centra en la inferencia del modelo, no en el preprocesamiento de datos.
- D. Optimizar la comunicación de red: Tensor parallelism no optimiza la comunicación de red; más bien crea comunicación adicional.
</details>
### 5. What is the most effective method to ensure high availability of vLLM services in Kubernetes?

A. Desplegar múltiples containers en un solo Pod
B. Usar Deployment con múltiples replicas y requests/limits de recursos adecuados
C. Desplegar en todos los nodes con DaemonSet
D. Reiniciar periódicamente con CronJob

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar Deployment con múltiples replicas y requests/limits de recursos adecuados**

**Explicación:**
El método más efectivo para garantizar alta disponibilidad de los Services de vLLM en Kubernetes es usar un Deployment con múltiples replicas y requests/limits de recursos adecuados. Este enfoque maneja el tráfico sin interrupciones del Service, proporciona recuperación automática en caso de fallos de node y permite escalar según la carga.

**Ejemplo de configuración de deployment de vLLM con alta disponibilidad:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
  labels:
    app: vllm
spec:
  replicas: 3  # Run multiple replicas
  selector:
    matchLabels:
      app: vllm
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime updates
  template:
    metadata:
      labels:
        app: vllm
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - vllm
              topologyKey: "kubernetes.io/hostname"  # Distribute pods across different nodes
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        resources:
          requests:
            nvidia.com/gpu: 1
            cpu: 4
            memory: 16Gi
          limits:
            nvidia.com/gpu: 1
            cpu: 8
            memory: 32Gi
        readinessProbe:  # Readiness check
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
        livenessProbe:  # Liveness check
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 30
        ports:
        - containerPort: 8000
          name: http
```

**Ejemplo de configuración de Service:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

**Ejemplo de configuración de Horizontal Pod Autoscaling:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-service
  minReplicas: 2
  maxReplicas: 10
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
        name: inference_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

**Configuraciones adicionales para alta disponibilidad:**

1. **Configuración de Pod Disruption Budget (PDB)**:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: vllm-pdb
spec:
  minAvailable: 2  # At least 2 pods must always be running
  selector:
    matchLabels:
      app: vllm
```

2. **Node affinity y tolerations**:
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: nvidia.com/gpu.product
          operator: In
          values:
          - A100-SXM4-40GB
          - A100-SXM4-80GB
tolerations:
- key: nvidia.com/gpu
  operator: Exists
  effect: NoSchedule
```

3. **Restricciones de distribución topológica**:
```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector:
    matchLabels:
      app: vllm
```

**Beneficios clave de la configuración de alta disponibilidad:**
1. **Tolerancia a fallos**: Continúa proporcionando el Service incluso con fallos de node o Pod
2. **Load balancing**: Distribuye el tráfico entre múltiples instancias
3. **Actualizaciones sin downtime**: Deployment sin interrupción mediante rolling updates
4. **Auto-scaling**: Escalado automático basado en la carga
5. **Auto-recuperación**: Reinicio automático de Pods fallidos

**Estrategias de load balancing:**
1. **Load balancing interno del Service**: Load balancing básico mediante Kubernetes Service
2. **Load balancing externo**: Distribución de tráfico externo mediante Ingress o cloud load balancer
3. **Afinidad de sesión**: Enruta solicitudes del mismo cliente al mismo Pod cuando sea necesario

**Monitoreo y alertas:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-monitor
spec:
  selector:
    matchLabels:
      app: vllm
  endpoints:
  - port: http
    interval: 15s
    path: /metrics
```

**Problemas con las otras opciones:**
- A. Desplegar múltiples containers en un solo Pod: Todo el Service puede interrumpirse en caso de fallo de node y no proporciona alta disponibilidad real.
- C. Desplegar en todos los nodes con DaemonSet: No se garantiza que todos los nodes tengan GPUs, y puede causar desperdicio de recursos.
- D. Reiniciar periódicamente con CronJob: Esto causa interrupción del Service y no es una solución de alta disponibilidad.
</details>

### 6. What is the main benefit of "Continuous Batching" in vLLM?

A. Mejor precisión del modelo
B. Mayor throughput y mejor utilización de GPU
C. Tamaño reducido del modelo
D. Ahorro de ancho de banda de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mayor throughput y mejor utilización de GPU**

**Explicación:**
El principal beneficio de "Continuous Batching" en vLLM es mayor throughput y mejor utilización de GPU. Continuous batching agrupa dinámicamente solicitudes con distintas longitudes y tiempos de inicio en batches para su procesamiento, lo que permite usar los recursos de GPU de manera más eficiente y mejorar significativamente el throughput general del sistema.

**Batching tradicional frente a Continuous batching:**
1. **Batching tradicional**:
   - Espera solicitudes para formar batches de tamaño fijo
   - Todas las solicitudes comienzan y terminan simultáneamente
   - Requiere padding para igualar la secuencia más larga del batch
   - Las nuevas solicitudes deben esperar hasta que finalice el batch actual

2. **Continuous batching**:
   - Procesa las solicitudes dinámicamente a medida que llegan
   - Procesa simultáneamente solicitudes con diferentes tiempos de inicio y longitudes
   - Uso eficiente de memoria sin padding innecesario
   - Los recursos de las solicitudes completadas se asignan inmediatamente a nuevas solicitudes

**Cómo funciona Continuous Batching:**
1. **Planificación dinámica de solicitudes**: Comienza el procesamiento inmediatamente cuando llegan las solicitudes
2. **Procesamiento token por token**: Cada solicitud se procesa token por token, generando nuevos tokens en cada paso
3. **Reasignación de recursos**: Los recursos de solicitudes completadas se asignan inmediatamente a nuevas solicitudes
4. **Gestión de KV cache**: Gestión eficiente de KV cache mediante PagedAttention

**Beneficios de Continuous Batching:**
1. **Alto throughput**: Aumento del número de solicitudes procesadas por segundo al utilizar los recursos de GPU de manera más eficiente
2. **Baja latencia**: Las solicitudes no necesitan esperar a que se formen batches
3. **Mejor utilización de recursos**: Menor tiempo ocioso de los recursos de cómputo y memoria de GPU
4. **Manejo de solicitudes de longitudes variadas**: Maneja eficientemente solicitudes de diferentes longitudes

**Configuraciones de continuous batching en la configuración de vLLM:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        - --max-num-batched-tokens=8192  # Maximum tokens per batch
        - --max-num-seqs=256  # Maximum sequences to process simultaneously
        - --max-model-len=4096  # Maximum context length
        resources:
          limits:
            nvidia.com/gpu: 1
```

**Optimización del rendimiento de continuous batching:**
1. **Configuración óptima del tamaño de batch**:
   - `max-num-batched-tokens`: Máximo de tokens que pueden procesarse a la vez
   - `max-num-seqs`: Máximo de secuencias que pueden procesarse simultáneamente

2. **Ajuste de utilización de memoria de GPU**:
   - `gpu-memory-utilization`: Establece la proporción de uso de memoria de GPU (0.0-1.0)

3. **Gestión de KV cache**:
   - `max-model-len`: Establece la longitud máxima de contexto
   - `block-size`: Establece el tamaño de bloque de PagedAttention

**Ejemplo de benchmark de rendimiento:**
| Batching Method | Throughput (req/sec) | Average Latency (ms) | GPU Utilization (%) |
|-----------------|----------------------|----------------------|---------------------|
| Static batching | 10 | 500 | 60% |
| Continuous batching | 25 | 300 | 90% |

**Limitaciones de Continuous Batching:**
1. **Complejidad de gestión de memoria**: Mayor complejidad debido a la asignación y liberación dinámicas de memoria
2. **Overhead de planificación**: Overhead adicional por la planificación dinámica de solicitudes
3. **Dificultad de optimización**: Dificultad para establecer parámetros óptimos para diversas cargas de trabajo

**Problemas con las otras opciones:**
- A. Mejor precisión del modelo: Continuous batching no afecta la precisión del modelo.
- C. Tamaño reducido del modelo: Continuous batching no cambia el tamaño del modelo.
- D. Ahorro de ancho de banda de red: Continuous batching no afecta directamente el uso de ancho de banda de red.
</details>
### 7. What is the most important metric for monitoring vLLM services in Kubernetes?

A. Conteo de reinicios de Pod
B. Latencia de inferencia, throughput, uso de memoria de GPU
C. Tasa de pérdida de paquetes de red
D. Rendimiento de I/O de disco

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Latencia de inferencia, throughput, uso de memoria de GPU**

**Explicación:**
Las métricas más importantes para monitorear Services de vLLM en Kubernetes son la latencia de inferencia, el throughput y el uso de memoria de GPU. Estas métricas reflejan directamente el rendimiento, la eficiencia y la utilización de recursos del Service de vLLM, e impactan directamente la calidad del Service (QoS) y la experiencia del usuario.

**Métricas clave de monitoreo:**

1. **Latencia de inferencia**:
   - **Definición**: Tiempo desde la recepción de la solicitud hasta la devolución de la respuesta
   - **Importancia**: Impacta directamente la experiencia del usuario y la capacidad de respuesta del Service
   - **Unidad de medida**: Milisegundos (ms) o segundos (s)
   - **Métricas detalladas**:
     - Time to First Token
     - Time per Token
     - Total Generation Time

2. **Throughput**:
   - **Definición**: Número de solicitudes o tokens que pueden procesarse por unidad de tiempo
   - **Importancia**: Evaluación de capacidad y escalabilidad del sistema
   - **Unidad de medida**: Requests per Second (RPS) o Tokens per Second (TPS)
   - **Métricas detalladas**:
     - Requests per Second
     - Tokens per Second
     - Batch Size

3. **Uso de memoria de GPU**:
   - **Definición**: Cantidad de memoria de GPU usada por el Service de vLLM
   - **Importancia**: Prevención de falta de memoria y optimización de recursos
   - **Unidad de medida**: Gigabytes (GB) o Megabytes (MB)
   - **Métricas detalladas**:
     - Uso de memoria de pesos del modelo
     - Uso de memoria de KV cache
     - Uso de memoria de activaciones
     - Uso total de memoria de GPU

**Ejemplo de configuración de métricas de Prometheus:**
```yaml
# Expose metrics from vLLM service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        - --enable-metrics=true  # Enable metrics
```

**Configuración de Prometheus ServiceMonitor:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: vllm
  endpoints:
  - port: http
    interval: 15s
    path: /metrics
```

**Métricas clave de vLLM y consultas PromQL:**

1. **Latencia de inferencia**:
   ```
   # 95th percentile inference latency
   histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))

   # Average time per token generation
   avg(rate(vllm_token_generation_time_seconds_sum[5m]) / rate(vllm_token_generation_time_seconds_count[5m]))
   ```

2. **Throughput**:
   ```
   # Requests per second
   sum(rate(vllm_requests_total[5m]))

   # Tokens per second
   sum(rate(vllm_generated_tokens_total[5m]))
   ```

3. **Uso de memoria de GPU**:
   ```
   # GPU memory usage
   vllm_gpu_memory_used_bytes

   # KV cache memory usage
   vllm_kv_cache_memory_bytes
   ```

**Ejemplo de configuración de dashboard de Grafana:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  vllm-dashboard.json: |
    {
      "title": "vLLM Performance Dashboard",
      "panels": [
        {
          "title": "Inference Latency",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))",
              "legendFormat": "p95 Latency"
            },
            {
              "expr": "histogram_quantile(0.50, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))",
              "legendFormat": "p50 Latency"
            }
          ]
        },
        {
          "title": "Throughput",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "sum(rate(vllm_requests_total[5m]))",
              "legendFormat": "Requests/sec"
            },
            {
              "expr": "sum(rate(vllm_generated_tokens_total[5m]))",
              "legendFormat": "Tokens/sec"
            }
          ]
        },
        {
          "title": "GPU Memory Usage",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "vllm_gpu_memory_used_bytes / 1024 / 1024 / 1024",
              "legendFormat": "GPU Memory (GB)"
            },
            {
              "expr": "vllm_kv_cache_memory_bytes / 1024 / 1024 / 1024",
              "legendFormat": "KV Cache (GB)"
            }
          ]
        },
        {
          "title": "GPU Utilization",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "DCGM_FI_DEV_GPU_UTIL",
              "legendFormat": "GPU {{gpu}}"
            }
          ]
        }
      ]
    }
```

**Ejemplo de configuración de regla de alerta:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vllm-alerts
  namespace: monitoring
spec:
  groups:
  - name: vllm.rules
    rules:
    - alert: HighInferenceLatency
      expr: histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le)) > 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High inference latency"
        description: "95th percentile latency is above 2 seconds"

    - alert: LowThroughput
      expr: sum(rate(vllm_requests_total[5m])) < 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Low request throughput"
        description: "Request throughput is below 10 RPS"

    - alert: HighGPUMemoryUsage
      expr: vllm_gpu_memory_used_bytes / vllm_gpu_memory_total_bytes > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High GPU memory usage"
        description: "GPU memory usage is above 95%"
```

**Métricas de monitoreo adicionales:**
1. **Utilización de GPU**: Proporción de utilización de las unidades de cómputo de GPU
2. **Uso de CPU**: Recursos de CPU usados para preprocesamiento y postprocesamiento
3. **Uso de memoria del sistema**: Uso de memoria del host
4. **Tasa de errores**: Proporción de solicitudes fallidas
5. **Longitud de cola**: Número de solicitudes esperando ser procesadas
6. **Eficiencia de batch**: Tamaño medio de batch y utilización

**Integración de herramientas de monitoreo:**
1. **Prometheus + Grafana**: Recolección y visualización de métricas
2. **NVIDIA DCGM Exporter**: Recolección de métricas de GPU
3. **Jaeger/Zipkin**: Distributed tracing
4. **ELK Stack**: Recolección y análisis de logs

**Problemas con las otras opciones:**
- A. Conteo de reinicios de Pod: Es un indicador de estabilidad del sistema, pero no refleja directamente el rendimiento del Service de vLLM.
- C. Tasa de pérdida de paquetes de red: Útil para diagnosticar problemas de red, pero no es una métrica central de rendimiento para el Service de vLLM.
- D. Rendimiento de I/O de disco: Puede ser importante durante la carga del modelo, pero es menos importante para el rendimiento del Service de vLLM en ejecución.
</details>

### 8. What is the optimal network configuration for vLLM services in Kubernetes?

A. Usar el plugin CNI predeterminado
B. Interfaz de red de alto rendimiento y soporte RDMA para tensor parallelism
C. Restringir todo el tráfico con network policies
D. Implementar service mesh

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Interfaz de red de alto rendimiento y soporte RDMA para tensor parallelism**

**Explicación:**
La configuración de red óptima para Services de vLLM en Kubernetes es una interfaz de red de alto rendimiento y soporte RDMA (Remote Direct Memory Access) para tensor parallelism. Al ejecutar large language models distribuidos entre múltiples GPUs, el rendimiento de la comunicación GPU a GPU impacta significativamente el rendimiento general del sistema. Las interfaces de red de alto rendimiento y el soporte RDMA minimizan la latencia de transferencia de datos GPU a GPU y maximizan el throughput para mejorar el rendimiento de inferencia distribuida.

**Importancia de redes de alto rendimiento:**
1. **Tensor parallelism**: Se requiere comunicación GPU a GPU frecuente al distribuir capas del modelo entre múltiples GPUs
2. **Model sharding**: El rendimiento de red entre nodes es importante al distribuir modelos grandes entre múltiples nodes
3. **Sensibilidad a la latencia**: La latencia de comunicación GPU a GPU impacta directamente la latencia general de inferencia
4. **Requisitos de ancho de banda**: Se necesita alto ancho de banda para transferencias de datos tensoriales grandes

**Componentes de configuración de red óptima:**

1. **Interfaz de red de alto rendimiento**:
   - **NVIDIA ConnectX-6/7**: Soporta hasta 200Gbps de ancho de banda
   - **InfiniBand**: Red de ultra baja latencia y alto ancho de banda
   - **RDMA over Converged Ethernet (RoCE)**: Capacidad RDMA en redes Ethernet

2. **Soporte RDMA (Remote Direct Memory Access)**:
   - Transferencia directa de datos entre memoria de GPU sin intervención de CPU
   - Latencia minimizada y throughput maximizado
   - GPU Direct RDMA: Transferencia directa de datos entre memoria de GPU

3. **NVLink/NVSwitch**:
   - Conexión de alta velocidad entre GPUs dentro del mismo node
   - Hasta 600GB/s de ancho de banda (NVLink 4.0)
   - Importante para sistemas multi-GPU

**Configuración de redes de alto rendimiento en Kubernetes:**

1. **SR-IOV (Single Root I/O Virtualization) Network Device Plugin**:
```yaml
# SR-IOV network device plugin configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: sriovdp-config
  namespace: kube-system
data:
  config.json: |
    {
      "resourceList": [
        {
          "resourceName": "nvidia_sriov_netdevice",
          "rootDevices": ["0000:03:00.0"],
          "sriovMode": true,
          "deviceType": "netdevice"
        },
        {
          "resourceName": "nvidia_sriov_rdma",
          "rootDevices": ["0000:03:00.0"],
          "sriovMode": true,
          "deviceType": "rdma"
        }
      ]
    }
```

2. **Configuración de NetworkAttachmentDefinition**:
```yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-rdma-network
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "sriov-rdma-network",
    "type": "sriov",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.1.0/24",
      "rangeStart": "192.168.1.10",
      "rangeEnd": "192.168.1.200"
    },
    "capabilities": { "ips": true }
  }'
```

3. **Aplicar configuración de red de alto rendimiento al deployment de vLLM**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-distributed
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
      annotations:
        k8s.v1.cni.cncf.io/networks: sriov-rdma-network
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
        - --max-model-len=4096
        resources:
          limits:
            nvidia.com/gpu: 8
            nvidia.com/sriov_rdma: 8
        env:
        - name: NCCL_DEBUG
          value: "INFO"
        - name: NCCL_IB_DISABLE
          value: "0"
        - name: NCCL_IB_GID_INDEX
          value: "3"
        - name: NCCL_IB_HCA
          value: "mlx5_0:1,mlx5_1:1,mlx5_2:1,mlx5_3:1"
        - name: NCCL_SOCKET_IFNAME
          value: "eth0,ens"
```

**Configuración de NCCL (NVIDIA Collective Communications Library):**
NCCL es una biblioteca que optimiza la comunicación GPU a GPU, configurable mediante las siguientes variables de entorno:

```
# Enable NCCL debug information
NCCL_DEBUG=INFO

# Enable InfiniBand usage
NCCL_IB_DISABLE=0

# Set InfiniBand GID index
NCCL_IB_GID_INDEX=3

# Specify HCA (Host Channel Adapter) to use
NCCL_IB_HCA=mlx5_0:1,mlx5_1:1

# Specify network interface
NCCL_SOCKET_IFNAME=eth0,ens

# Enable RDMA transport
NCCL_IB_ENABLE_RDMA=1

# Enable GPU Direct RDMA
NCCL_IB_GDR_LEVEL=4
```

**Configuración distribuida multi-node:**
Al distribuir vLLM entre múltiples nodes, el rendimiento de red entre nodes se vuelve aún más importante. Se necesita la siguiente configuración:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vllm-distributed-node1
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-rdma-network
spec:
  nodeSelector:
    kubernetes.io/hostname: node1
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model=meta-llama/Llama-2-70b-chat-hf
    - --tensor-parallel-size=16
    - --tensor-parallel-rank=0-7
    - --distributed-init-method=tcp://vllm-init:7777
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_IB_DISABLE
      value: "0"
    resources:
      limits:
        nvidia.com/gpu: 8
        nvidia.com/sriov_rdma: 8

---
apiVersion: v1
kind: Pod
metadata:
  name: vllm-distributed-node2
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-rdma-network
spec:
  nodeSelector:
    kubernetes.io/hostname: node2
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model=meta-llama/Llama-2-70b-chat-hf
    - --tensor-parallel-size=16
    - --tensor-parallel-rank=8-15
    - --distributed-init-method=tcp://vllm-init:7777
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_IB_DISABLE
      value: "0"
    resources:
      limits:
        nvidia.com/gpu: 8
        nvidia.com/sriov_rdma: 8
```

**Pruebas de rendimiento de red:**
```bash
# Run NCCL test
kubectl run nccl-test --image=nvidia/cuda:11.8.0-devel-ubuntu22.04 --overrides='{"spec": {"containers": [{"name": "nccl-test", "image": "nvidia/cuda:11.8.0-devel-ubuntu22.04", "command": ["/bin/bash", "-c"], "args": ["apt-get update && apt-get install -y git && git clone https://github.com/NVIDIA/nccl-tests.git && cd nccl-tests && make && ./build/all_reduce_perf -b 8 -e 128M -f 2 -g 8"], "resources": {"limits": {"nvidia.com/gpu": 8}}}]}}' --restart=Never

# Network bandwidth test
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201
kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**Problemas con las otras opciones:**
- A. Usar el plugin CNI predeterminado: Los plugins CNI predeterminados normalmente no admiten funciones de red de alto rendimiento como RDMA y no proporcionan el rendimiento necesario para tensor parallelism.
- C. Restringir todo el tráfico con network policies: Esto puede mejorar la seguridad, pero no mejora el rendimiento y puede añadir overhead adicional.
- D. Implementar service mesh: Service mesh es útil para arquitectura de microservicios, pero añade overhead innecesario para cargas de trabajo de cómputo de alto rendimiento como vLLM.
</details>
### 9. What is the most effective method to improve scalability of vLLM services in Kubernetes?

A. Asignar más núcleos de CPU
B. Combinación de escalado horizontal (múltiples replicas) con load balancing y escalado vertical (GPUs más grandes)
C. Asignar más memoria
D. Aprovisionar volúmenes persistentes más grandes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Combinación de escalado horizontal (múltiples replicas) con load balancing y escalado vertical (GPUs más grandes)**

**Explicación:**
El método más efectivo para mejorar la escalabilidad de Services de vLLM en Kubernetes es una combinación de escalado horizontal (múltiples replicas) con load balancing y escalado vertical (GPUs más grandes). Este enfoque puede responder con flexibilidad a diversos requisitos de carga de trabajo y restricciones de recursos, y equilibrar eficiencia de costos y rendimiento.

**Beneficios del escalado horizontal:**
1. **Mayor throughput**: Se pueden manejar más solicitudes concurrentes con más replicas
2. **Alta disponibilidad**: El Service continúa aunque algunas instancias fallen
3. **Distribución geográfica**: Deployment en múltiples regiones para reducir la latencia
4. **Eficiencia de costos**: Puede ajustar el número de instancias según sea necesario

**Beneficios del escalado vertical:**
1. **Soporte para modelos más grandes**: Una memoria de GPU más grande puede cargar modelos más grandes
2. **Latencia reducida para solicitudes individuales**: Mayor velocidad de inferencia con GPUs más potentes
3. **Manejo de contextos más largos**: Más memoria puede manejar contextos más largos
4. **Overhead de comunicación reducido**: Overhead de comunicación reducido al usar una sola GPU o múltiples GPUs dentro de un solo node

**Ejemplo de configuración de escalado horizontal:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 5  # Run multiple replicas
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        resources:
          limits:
            nvidia.com/gpu: 1
```

**Configuración de auto-scaling horizontal:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-service
  minReplicas: 2
  maxReplicas: 10
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
        name: inference_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

**Ejemplo de configuración de escalado vertical:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-large
  template:
    metadata:
      labels:
        app: vllm-large
    spec:
      nodeSelector:
        gpu-type: a100-80gb  # Select larger GPU
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8  # Distribute model across multiple GPUs
        resources:
          limits:
            nvidia.com/gpu: 8  # Allocate more GPUs
```

**Configuración de load balancing:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vllm-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "route"
    nginx.ingress.kubernetes.io/session-cookie-expires: "172800"
    nginx.ingress.kubernetes.io/session-cookie-max-age: "172800"
spec:
  rules:
  - host: vllm.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: vllm-service
            port:
              number: 80
```

**Model sharding y enrutamiento:**
Se pueden combinar múltiples deployments y enrutar para admitir varios tamaños y tipos de modelo:

```yaml
# Small model deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-small
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
---
# Medium model deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-medium
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-13b-chat-hf
---
# Large model deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
```

**Configuración de API gateway:**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: vllm-routing
spec:
  hosts:
  - "api.example.com"
  gateways:
  - api-gateway
  http:
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-7b"
    route:
    - destination:
        host: vllm-small
        port:
          number: 8000
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-13b"
    route:
    - destination:
        host: vllm-medium
        port:
          number: 8000
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-70b"
    route:
    - destination:
        host: vllm-large
        port:
          number: 8000
```

**Estrategias de optimización de escalabilidad:**
1. **Optimización del enrutamiento de solicitudes**:
   - Enrutar solicitudes a instancias adecuadas según el tamaño y la complejidad del modelo
   - Optimizar la reutilización de KV cache mediante afinidad de sesión

2. **Optimización de asignación de recursos**:
   - Seleccionar el tipo de GPU adecuado para las características de la carga de trabajo
   - Establecer un tamaño adecuado de tensor parallelism

3. **Estrategia de caching**:
   - Guardar en cache prompts y respuestas usados con frecuencia
   - Caching de pesos del modelo

4. **Escalado de cloud híbrida**:
   - Combinar recursos on-premises y de cloud
   - Escalado en cloud para tráfico burst

**Pruebas de escalabilidad y benchmarking:**
```bash
# Run load test
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**Problemas con las otras opciones:**
- A. Asignar más núcleos de CPU: vLLM está limitado principalmente por GPU, y el rendimiento no mejora significativamente solo agregando núcleos de CPU.
- C. Asignar más memoria: La memoria del sistema es importante, pero la memoria de GPU es la restricción principal.
- D. Aprovisionar volúmenes persistentes más grandes: La capacidad de almacenamiento es importante para almacenar modelos, pero no impacta directamente el rendimiento ni la escalabilidad de inferencia.
</details>

### 10. What is the most important security consideration when deploying vLLM in Kubernetes?

A. Configuración de network policy
B. Proteger pesos del modelo y API keys, hardening de seguridad de containers
C. Configuración de Pod security policy
D. Habilitar audit logging

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Proteger pesos del modelo y API keys, hardening de seguridad de containers**

**Explicación:**
La consideración de seguridad más importante al desplegar vLLM en Kubernetes es proteger los pesos del modelo y las API keys, y aplicar hardening de seguridad a los containers. Los Services de vLLM manejan pesos de modelos que son propiedad intelectual, API keys sensibles y datos de usuarios, por lo que proteger estos activos y reforzar la seguridad del entorno de containers es lo más importante.

**Consideraciones clave de seguridad:**

1. **Protección de pesos del modelo**:
   - Los pesos del modelo son activos valiosos con derechos de propiedad intelectual.
   - Deben protegerse contra acceso no autorizado, copia y filtración.
   - Se requiere almacenamiento cifrado y cifrado en tránsito.

2. **Protección de API keys e información de autenticación**:
   - La información de autenticación como API keys, tokens y contraseñas debe gestionarse de forma segura.
   - Debe usar Kubernetes Secrets o sistemas externos de gestión de secretos.
   - Debe proporcionar secrets mediante volúmenes montados en lugar de variables de entorno.

3. **Hardening de seguridad de containers**:
   - Aplicar el principio de mínimo privilegio
   - Ejecutar containers como usuario no root
   - Usar sistema de archivos de solo lectura
   - Eliminar capacidades y privilegios innecesarios

4. **Validación de entrada y filtrado de salida**:
   - Prevenir ataques de prompt injection
   - Prevenir filtración de información sensible
   - Filtrar contenido dañino

**Ejemplo de configuración de protección de pesos del modelo:**
```yaml
# Encrypted persistent volume claim
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-storage
spec:
  accessModes:
    - ReadOnlyMany
  storageClassName: encrypted-storage
  resources:
    requests:
      storage: 100Gi

---
# Restrict access to model weights
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      securityContext:
        fsGroup: 1000
        runAsUser: 1000
        runAsGroup: 1000
      containers:
      - name: vllm
        volumeMounts:
        - name: model-volume
          mountPath: /models
          readOnly: true
      volumes:
      - name: model-volume
        persistentVolumeClaim:
          claimName: model-storage
```

**Protección de API keys e información de autenticación:**
```yaml
# Use Kubernetes Secrets
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
type: Opaque
data:
  openai-api-key: base64EncodedApiKey
  huggingface-token: base64EncodedToken

---
# External secret management system integration (HashiCorp Vault)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vllm-service
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-secret-api-keys: "secret/data/api-keys"
    vault.hashicorp.com/role: "vllm-role"

---
# Mount secrets as volume
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      containers:
      - name: vllm
        volumeMounts:
        - name: api-keys
          mountPath: /app/secrets
          readOnly: true
      volumes:
      - name: api-keys
        secret:
          secretName: api-keys
```

**Hardening de seguridad de containers:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      # Pod level security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        # Container level security context
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
```

**Network policy:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
spec:
  podSelector:
    matchLabels:
      app: vllm
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          name: huggingface
    ports:
    - protocol: TCP
      port: 443
```

**Validación de entrada y filtrado de salida:**
```python
# Prompt validation and filtering example
def validate_prompt(prompt):
    # Check prompt injection patterns
    if re.search(r"(ignore|forget|disregard).*instructions", prompt, re.IGNORECASE):
        return False, "Potential prompt injection detected"

    # Check sensitive commands
    if re.search(r"(system|sudo|exec|eval)", prompt, re.IGNORECASE):
        return False, "Potentially harmful commands detected"

    return True, prompt

# Output filtering example
def filter_output(response):
    # PII filtering
    response = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED SSN]", response)
    response = re.sub(r"\b\d{16}\b", "[REDACTED CREDIT CARD]", response)

    # Harmful content filtering
    for harmful_pattern in HARMFUL_PATTERNS:
        if re.search(harmful_pattern, response, re.IGNORECASE):
            response = "[Content removed due to policy violation]"
            break

    return response
```

**Configuración de RBAC (Role-Based Access Control):**
```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vllm-service
  namespace: ml-services

---
# Role definition
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: vllm-role
  namespace: ml-services
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
  resourceNames: ["model-access-keys"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get"]
  resourceNames: ["vllm-config"]

---
# Role binding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: vllm-role-binding
  namespace: ml-services
subjects:
- kind: ServiceAccount
  name: vllm-service
  namespace: ml-services
roleRef:
  kind: Role
  name: vllm-role
  apiGroup: rbac.authorization.k8s.io
```

**Configuración de audit logging:**
```yaml
# ConfigMap for audit logging
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-audit-config
data:
  audit.yaml: |
    apiVersion: audit.k8s.io/v1
    kind: Policy
    rules:
    - level: RequestResponse
      resources:
      - group: ""
        resources: ["secrets"]
    - level: Metadata
      resources:
      - group: ""
        resources: ["pods"]

# Enable audit logging
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    metadata:
      annotations:
        audit-log-path: "/var/log/vllm/audit.log"
        audit-log-maxage: "30"
        audit-log-maxbackup: "10"
        audit-log-maxsize: "100"
    spec:
      containers:
      - name: vllm
        volumeMounts:
        - name: audit-logs
          mountPath: /var/log/vllm
      volumes:
      - name: audit-logs
        emptyDir: {}
```

**Buenas prácticas de seguridad adicionales:**
1. **Escaneo de seguridad regular**: Escanear imágenes de containers y dependencias en busca de vulnerabilidades
2. **Principio de mínimo privilegio**: Conceder solo los privilegios mínimos requeridos
3. **Infraestructura inmutable**: Desplegar containers nuevos cuando se necesiten cambios
4. **Monitoreo de seguridad**: Detectar comportamiento anómalo y enviar alertas
5. **Plan de respuesta ante emergencias**: Preparar procedimientos de respuesta para incidentes de seguridad

**Problemas con las otras opciones:**
- A. Configuración de network policy: Importante, pero de menor prioridad que proteger pesos del modelo y API keys, y el hardening de seguridad de containers.
- C. Configuración de Pod security policy: Parte de la seguridad de containers, pero no incluye protección de pesos del modelo ni API keys.
- D. Habilitar audit logging: Importante para el monitoreo de seguridad, pero de menor prioridad que las medidas preventivas de seguridad.
</details>
