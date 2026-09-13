# Cuestionario sobre el despliegue de vLLM

Este cuestionario evalúa tu comprensión del despliegue de vLLM (Vector Language Model) en Kubernetes.

## Preguntas del cuestionario

### 1. ¿Cuál es el propósito principal de vLLM (Vector Language Model)?

A. Aceleración del procesamiento de imágenes
B. Optimización y aceleración de la inferencia de Large Language Model (LLM)
C. Optimización de consultas de bases de datos
D. Gestión del tráfico de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Optimización y aceleración de la inferencia de Large Language Model (LLM)**

**Explicación:**
El propósito principal de vLLM (Vector Language Model) es optimizar y acelerar la inferencia de Large Language Model (LLM). vLLM usa un algoritmo innovador de atención llamado PagedAttention para optimizar la gestión de memoria, lo que permite la inferencia de LLM con alto rendimiento y baja latencia.

**Características principales de vLLM:**
1. **PagedAttention**: Mecanismo de atención eficiente en memoria que optimiza el uso de la memoria GPU.
2. **Batching continuo**: Agrupa dinámicamente las solicitudes para mejorar el rendimiento.
3. **Inferencia distribuida**: Distribuye modelos grandes entre varias GPU y nodos.
4. **Compatibilidad con diversos modelos**: Admite varios LLM de código abierto, incluidos Llama, GPT-NeoX, Falcon y MPT.
5. **API compatible con OpenAI**: Proporciona una interfaz compatible con la API de OpenAI.

**Cómo funciona PagedAttention:**
PagedAttention es una técnica inspirada en la gestión de memoria virtual de los sistemas operativos que administra eficientemente la caché KV (Key-Value). Los métodos tradicionales asignan bloques de memoria de tamaño fijo para cada solicitud, pero PagedAttention asigna solo la memoria necesaria y la reutiliza.

**Beneficios de rendimiento de vLLM:**
1. **Alto rendimiento**: Rendimiento 2-4 veces superior al de las soluciones existentes
2. **Eficiencia de memoria**: Puede gestionar hasta 8 veces más solicitudes simultáneas
3. **Baja latencia**: Tiempo de respuesta reducido mediante una gestión eficiente de la memoria
4. **Mejor utilización de recursos**: Uso más eficiente de los recursos de GPU

**Casos de uso de vLLM:**
1. **Servicios de IA conversacional**: Chatbots, asistentes virtuales, etc.
2. **Servicios de generación de texto**: Generación de contenido, resumen, traducción, etc.
3. **Generación y finalización de código**: Herramientas de asistencia para programación
4. **Procesamiento de texto a gran escala**: Análisis de documentos, extracción de información, etc.

**Problemas con las otras opciones:**
- A. Aceleración del procesamiento de imágenes: vLLM es para modelos lingüísticos basados en texto y no está especializado en el procesamiento de imágenes.
- C. Optimización de consultas de bases de datos: vLLM no está relacionado con la optimización de consultas de bases de datos.
- D. Gestión del tráfico de red: vLLM no está relacionado con la gestión del tráfico de red.
</details>

### 2. ¿Cuál es el requisito de recursos más importante al desplegar vLLM en Kubernetes?

A. Gran cantidad de CPU y memoria
B. GPU de alto rendimiento y memoria GPU suficiente
C. Interfaz de red de alta velocidad
D. Gran almacenamiento persistente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. GPU de alto rendimiento y memoria GPU suficiente**

**Explicación:**
El requisito de recursos más importante al desplegar vLLM en Kubernetes es una GPU de alto rendimiento y memoria GPU suficiente. Los Large Language Model (LLM) tienen miles de millones o cientos de miles de millones de parámetros, y para ejecutarlos eficientemente son esenciales una potente capacidad de cómputo GPU y memoria GPU suficiente para almacenar sus parámetros.

**Requisitos de GPU:**
1. **Tipo de GPU**: GPU de alto rendimiento como NVIDIA A100, H100, V100 y RTX A6000
2. **Memoria GPU**: Varía según el tamaño del modelo, pero en general:
   - Modelo de 7B parámetros: Mínimo 16GB de memoria GPU
   - Modelo de 13B parámetros: Mínimo 24GB de memoria GPU
   - Modelo de 70B parámetros: Mínimo 80GB de memoria GPU o distribución entre varias GPU
3. **Cantidad de GPU**: Depende de los requisitos de rendimiento y del tamaño del modelo, pero los modelos grandes deben distribuirse entre varias GPU.

**Ejemplo de solicitud de recursos GPU para un despliegue de vLLM:**
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

**Ejemplo de despliegue distribuido para modelos grandes:**
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

**Cálculo de requisitos de memoria GPU:**
Los requisitos de memoria GPU de los LLM se determinan mediante los siguientes factores:
1. **Parámetros del modelo**: Cada parámetro suele ocupar 2 bytes (FP16) o 4 bytes (FP32).
2. **Caché KV**: La caché Key-Value para cada token requiere memoria adicional.
3. **Tamaño del batch**: Los requisitos de memoria aumentan a medida que crece el número de solicitudes simultáneas.
4. **Longitud del contexto**: Los contextos más largos requieren más memoria para la caché KV.

**Fórmula aproximada de requisitos de memoria:**
```
Required GPU memory = Model size + (batch size x sequence length x hidden size x layers x 4 bytes)
```

**Otros requisitos de recursos:**
1. **CPU**: Núcleos CPU suficientes para el preprocesamiento y el posprocesamiento
2. **Memoria del sistema**: RAM suficiente para la carga y el procesamiento del modelo
3. **Almacenamiento**: Almacenamiento suficiente para los archivos de pesos del modelo
4. **Red**: Conexión de red de alta velocidad para la inferencia distribuida

**Problemas con las otras opciones:**
- A. Gran cantidad de CPU y memoria: La CPU no es eficiente para la inferencia de LLM, y la memoria del sistema por sí sola no puede sustituir a la memoria GPU.
- C. Interfaz de red de alta velocidad: Es importante para la inferencia distribuida, pero tiene menor prioridad que la GPU y su memoria.
- D. Gran almacenamiento persistente: Es necesario para almacenar los pesos del modelo, pero no afecta directamente al rendimiento de inferencia.
</details>


### 3. ¿Cuál es la solución de almacenamiento óptima para vLLM en Kubernetes?

A. Volumen emptyDir
B. Volumen hostPath
C. Sistema de archivos distribuido de alto rendimiento (p. ej., FSx for Lustre)
D. Sistema de archivos de red habitual (NFS)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Sistema de archivos distribuido de alto rendimiento (p. ej., FSx for Lustre)**

**Explicación:**
La solución de almacenamiento óptima para vLLM en Kubernetes es un sistema de archivos distribuido de alto rendimiento (p. ej., FSx for Lustre). vLLM debe cargar rápidamente los archivos de pesos del modelo para procesar modelos lingüísticos grandes y, en entornos de inferencia distribuida, varios nodos deben acceder simultáneamente a los mismos archivos de modelo. Los sistemas de archivos distribuidos de alto rendimiento cumplen estos requisitos al proporcionar alto rendimiento, baja latencia y capacidades de acceso paralelo.

**Ventajas de los sistemas de archivos distribuidos de alto rendimiento:**
1. **Alto rendimiento**: Pueden cargar rápidamente archivos de modelo grandes.
2. **Acceso paralelo**: Varios nodos pueden acceder simultáneamente a los mismos archivos.
3. **Escalabilidad**: La capacidad y el rendimiento de almacenamiento pueden escalarse según sea necesario.
4. **Consistencia de datos**: Proporcionan una vista de datos coherente entre varios nodos.
5. **Durabilidad**: Reducen el riesgo de pérdida de datos mediante replicación y copia de seguridad.

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
# Azure NetApp Files configuration example
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

| Opción de almacenamiento | Rendimiento | Latencia | Acceso multinodo | Escalabilidad | Persistencia |
|----------------|------------|---------|-------------------|-------------|-------------|
| emptyDir | Alto | Muy baja | No es posible | Limitada | Temporal |
| hostPath | Alto | Muy baja | No es posible | Limitada | Dependiente del nodo |
| NFS | Medio | Media | Posible | Media | Persistente |
| FSx for Lustre | Muy alto | Baja | Posible | Alta | Persistente |
| Google Filestore | Alto | Baja | Posible | Alta | Persistente |
| Azure NetApp Files | Alto | Baja | Posible | Alta | Persistente |

**Estrategias de optimización del rendimiento de carga de modelos:**
1. **Mapeo de memoria**: Reduce el tiempo de carga al mapear directamente los archivos de modelo grandes a memoria.
2. **Fragmentación del modelo**: Divide el modelo en varios fragmentos y los carga en paralelo.
3. **Caché**: Almacena en caché los modelos usados con frecuencia para evitar recargas.
4. **Precarga**: Precarga los modelos al iniciar el servicio para reducir la latencia de la primera solicitud.

**Problemas con las otras opciones:**
- A. Volumen emptyDir: Almacenamiento temporal cuyos datos se pierden al reiniciar el Pod. No es adecuado para almacenar archivos de modelo grandes.
- B. Volumen hostPath: Depende del almacenamiento local del nodo, lo que dificulta compartir datos en entornos multinodo.
- D. Sistema de archivos de red habitual (NFS): Tiene un rendimiento inferior al de los sistemas de archivos distribuidos de alto rendimiento en rendimiento y latencia.
</details>

### 4. ¿Cuál es el propósito principal de Tensor Parallelism en vLLM?

A. Procesar varias solicitudes de usuarios en paralelo
B. Distribuir modelos grandes entre varias GPU para reducir los requisitos de memoria
C. Acelerar el preprocesamiento de datos
D. Optimizar la comunicación de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Distribuir modelos grandes entre varias GPU para reducir los requisitos de memoria**

**Explicación:**
El propósito principal de Tensor Parallelism en vLLM es distribuir modelos grandes entre varias GPU para reducir los requisitos de memoria. Los Large Language Model (LLM) a menudo tienen miles de millones o cientos de miles de millones de parámetros que superan la capacidad de memoria de una sola GPU. El paralelismo de tensores resuelve este problema al dividir las capas del modelo entre varias GPU, de modo que cada GPU almacena y procesa solo una parte del modelo.

**Cómo funciona Tensor Parallelism:**
1. **División del modelo**: Divide cada capa del modelo (especialmente las capas de atención y MLP) entre varias GPU.
2. **Cálculo paralelo**: Cada GPU realiza cálculos en la parte asignada del modelo.
3. **Sincronización**: Sincroniza los resultados intermedios entre las GPU cuando es necesario.
4. **Agregación de resultados**: Agrega los resultados de cada GPU para generar la salida final.

**Ejemplo de configuración de paralelismo de tensores en vLLM:**
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

**Guía para seleccionar el tamaño de paralelismo de tensores:**
1. **Tamaño del modelo**: El tamaño de paralelismo de tensores requerido depende del número de parámetros del modelo.
   - Modelo de 7B parámetros: 1-2 GPU
   - Modelo de 13B parámetros: 2-4 GPU
   - Modelo de 70B parámetros: 8-16 GPU
   - Modelo de 175B parámetros: más de 16 GPU

2. **Memoria GPU**: El tamaño del paralelismo de tensores debe ajustarse según la memoria GPU disponible.
   - GPU de 24GB: Adecuada para modelos pequeños
   - GPU de 40GB: Adecuada para modelos medianos
   - GPU de 80GB: Adecuada para modelos grandes

3. **Consideraciones de rendimiento**: El paralelismo de tensores crea sobrecarga de comunicación de GPU a GPU.
   - Tamaño de paralelismo de tensores demasiado pequeño: Problemas de falta de memoria
   - Tamaño de paralelismo de tensores demasiado grande: Degradación del rendimiento por sobrecarga de comunicación

**Tensor Parallelism frente a otras técnicas de paralelización:**
1. **Data Parallelism**: Varias copias del mismo modelo procesan distintos batches de datos. Se usa principalmente para entrenamiento.
2. **Pipeline Parallelism**: Distribuye secuencialmente las capas del modelo entre varias GPU.
3. **Tensor Parallelism**: Distribuye los cálculos de capas individuales entre varias GPU.

**Ventajas de Tensor Parallelism:**
1. **Eficiencia de memoria**: Reduce los requisitos de memoria distribuyendo modelos grandes entre varias GPU.
2. **Latencia reducida de una sola solicitud**: Mejora la velocidad de inferencia mediante cálculo paralelo.
3. **Mejor utilización de recursos**: Uso más eficiente de los recursos de GPU.

**Desventajas de Tensor Parallelism:**
1. **Sobrecarga de comunicación**: Sobrecarga por transferencia de datos entre GPU.
2. **Complejidad de implementación**: Lógica compleja de división y sincronización del modelo.
3. **Requisitos de hardware**: Requiere interconexiones GPU de alta velocidad (NVLink, NVSwitch, etc.).

**Problemas con las otras opciones:**
- A. Procesar varias solicitudes de usuarios en paralelo: Este es el propósito del procesamiento por batch o del paralelismo de solicitudes.
- C. Acelerar el preprocesamiento de datos: El paralelismo de tensores se centra en la inferencia del modelo, no en el preprocesamiento de datos.
- D. Optimizar la comunicación de red: El paralelismo de tensores no optimiza la comunicación de red; más bien crea comunicación adicional.
</details>


### 5. ¿Cuál es el método más efectivo para garantizar la alta disponibilidad de los servicios vLLM en Kubernetes?

A. Desplegar varios contenedores en un único Pod
B. Usar Deployment con varias réplicas y solicitudes/límites de recursos adecuados
C. Desplegar en todos los nodos con DaemonSet
D. Reiniciar periódicamente con CronJob

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar Deployment con varias réplicas y solicitudes/límites de recursos adecuados**

**Explicación:**
El método más efectivo para garantizar la alta disponibilidad de los servicios vLLM en Kubernetes es usar un Deployment con varias réplicas y solicitudes/límites de recursos adecuados. Este enfoque gestiona el tráfico sin interrupciones del servicio, proporciona recuperación automática en caso de fallos de nodo y permite escalar según la carga.

**Ejemplo de configuración de despliegue vLLM de alta disponibilidad:**
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

2. **Afinidad de nodos y tolerations**:
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

3. **Restricciones de distribución de topología**:
```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector:
    matchLabels:
      app: vllm
```

**Beneficios principales de la configuración de alta disponibilidad:**
1. **Tolerancia a fallos**: Continúa proporcionando servicio incluso con fallos de nodo o Pod.
2. **Balanceo de carga**: Distribuye el tráfico entre varias instancias.
3. **Actualizaciones sin tiempo de inactividad**: Despliegue sin interrupciones mediante actualizaciones continuas.
4. **Autoescalado**: Escalado automático según la carga.
5. **Recuperación automática**: Reinicio automático de Pods que fallan.

**Estrategias de balanceo de carga:**
1. **Balanceo de carga interno del servicio**: Balanceo de carga básico mediante Kubernetes Service.
2. **Balanceo de carga externo**: Distribución de tráfico externo mediante Ingress o balanceador de carga en la nube.
3. **Afinidad de sesión**: Enruta las solicitudes del mismo cliente al mismo Pod cuando sea necesario.

**Monitorización y alertas:**
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
- A. Desplegar varios contenedores en un único Pod: Todo el servicio puede interrumpirse ante un fallo de nodo y no proporciona verdadera alta disponibilidad.
- C. Desplegar en todos los nodos con DaemonSet: No se garantiza que todos los nodos tengan GPU y puede causar desperdicio de recursos.
- D. Reiniciar periódicamente con CronJob: Esto causa interrupciones del servicio y no es una solución de alta disponibilidad.
</details>

### 6. ¿Cuál es el principal beneficio de "Continuous Batching" en vLLM?

A. Mayor precisión del modelo
B. Mayor rendimiento y mejor utilización de GPU
C. Tamaño de modelo reducido
D. Ahorro de ancho de banda de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mayor rendimiento y mejor utilización de GPU**

**Explicación:**
El principal beneficio de "Continuous Batching" en vLLM es el aumento del rendimiento y la mejora de la utilización de GPU. El batching continuo agrupa dinámicamente para su procesamiento solicitudes con diferentes longitudes y tiempos de inicio, usa más eficientemente los recursos GPU y mejora de forma significativa el rendimiento global del sistema.

**Batching tradicional frente a batching continuo:**
1. **Batching tradicional**:
   - Espera a que las solicitudes formen batches de tamaño fijo.
   - Todas las solicitudes comienzan y terminan simultáneamente.
   - Requiere padding para coincidir con la secuencia más larga del batch.
   - Las solicitudes nuevas deben esperar a que finalice el batch actual.

2. **Batching continuo**:
   - Procesa las solicitudes dinámicamente a medida que llegan.
   - Procesa simultáneamente solicitudes con distintos tiempos de inicio y longitudes.
   - Uso eficiente de memoria sin padding innecesario.
   - Los recursos de solicitudes completadas se asignan inmediatamente a solicitudes nuevas.

**Cómo funciona Continuous Batching:**
1. **Planificación dinámica de solicitudes**: Comienza a procesar inmediatamente cuando llegan solicitudes.
2. **Procesamiento token por token**: Cada solicitud se procesa token por token y genera nuevos tokens en cada paso.
3. **Reasignación de recursos**: Los recursos de solicitudes completadas se asignan inmediatamente a solicitudes nuevas.
4. **Gestión de caché KV**: Gestión eficiente de caché KV mediante PagedAttention.

**Beneficios de Continuous Batching:**
1. **Alto rendimiento**: Aumenta el número de solicitudes procesadas por segundo mediante un uso más eficiente de los recursos GPU.
2. **Baja latencia**: Las solicitudes no tienen que esperar a que se formen los batches.
3. **Mejor utilización de recursos**: Reduce el tiempo inactivo de los recursos de cómputo y memoria GPU.
4. **Gestión de solicitudes de diversas longitudes**: Gestiona eficientemente solicitudes de diferentes longitudes.

**Configuración de batching continuo en vLLM:**
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

**Optimización del rendimiento de batching continuo:**
1. **Configuración óptima del tamaño de batch**:
   - `max-num-batched-tokens`: Máximo de tokens que se pueden procesar a la vez
   - `max-num-seqs`: Máximo de secuencias que se pueden procesar simultáneamente

2. **Ajuste de la utilización de memoria GPU**:
   - `gpu-memory-utilization`: Establece la proporción de uso de memoria GPU (0.0-1.0)

3. **Gestión de caché KV**:
   - `max-model-len`: Establece la longitud máxima del contexto
   - `block-size`: Establece el tamaño de bloque de PagedAttention

**Ejemplo de referencia de rendimiento:**
| Método de batching | Rendimiento (req/s) | Latencia media (ms) | Utilización de GPU (%) |
|-----------------|----------------------|----------------------|---------------------|
| Batching estático | 10 | 500 | 60% |
| Batching continuo | 25 | 300 | 90% |

**Limitaciones de Continuous Batching:**
1. **Complejidad de gestión de memoria**: Mayor complejidad por la asignación y desasignación dinámica de memoria.
2. **Sobrecarga de planificación**: Sobrecarga adicional de la planificación dinámica de solicitudes.
3. **Dificultad de optimización**: Dificultad para configurar parámetros óptimos para diversas cargas de trabajo.

**Problemas con las otras opciones:**
- A. Mayor precisión del modelo: El batching continuo no afecta a la precisión del modelo.
- C. Tamaño de modelo reducido: El batching continuo no cambia el tamaño del modelo.
- D. Ahorro de ancho de banda de red: El batching continuo no afecta directamente al uso de ancho de banda de red.
</details>


### 7. ¿Cuál es la métrica más importante para monitorizar los servicios vLLM en Kubernetes?

A. Recuento de reinicios de Pod
B. Latencia de inferencia, rendimiento y uso de memoria GPU
C. Tasa de pérdida de paquetes de red
D. Rendimiento de E/S de disco

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Latencia de inferencia, rendimiento y uso de memoria GPU**

**Explicación:**
Las métricas más importantes para monitorizar los servicios vLLM en Kubernetes son la latencia de inferencia, el rendimiento y el uso de memoria GPU. Estas métricas reflejan directamente el rendimiento, la eficiencia y la utilización de recursos del servicio vLLM, e influyen directamente en la calidad del servicio (QoS) y la experiencia de usuario.

**Métricas de monitorización principales:**

1. **Latencia de inferencia**:
   - **Definición**: Tiempo desde que se recibe una solicitud hasta que se devuelve la respuesta.
   - **Importancia**: Influye directamente en la experiencia de usuario y la capacidad de respuesta del servicio.
   - **Unidad de medida**: Milisegundos (ms) o segundos (s).
   - **Métricas detalladas**:
     - Tiempo hasta el primer token
     - Tiempo por token
     - Tiempo total de generación

2. **Rendimiento**:
   - **Definición**: Número de solicitudes o tokens que pueden procesarse por unidad de tiempo.
   - **Importancia**: Evaluación de la capacidad y escalabilidad del sistema.
   - **Unidad de medida**: Solicitudes por segundo (RPS) o tokens por segundo (TPS).
   - **Métricas detalladas**:
     - Solicitudes por segundo
     - Tokens por segundo
     - Tamaño de batch

3. **Uso de memoria GPU**:
   - **Definición**: Cantidad de memoria GPU utilizada por el servicio vLLM.
   - **Importancia**: Prevención de falta de memoria y optimización de recursos.
   - **Unidad de medida**: Gigabytes (GB) o megabytes (MB).
   - **Métricas detalladas**:
     - Uso de memoria de pesos del modelo
     - Uso de memoria de caché KV
     - Uso de memoria de activaciones
     - Uso total de memoria GPU

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

**Métricas vLLM principales y consultas PromQL:**

1. **Latencia de inferencia**:
   ```
   # 95th percentile inference latency
   histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))

   # Average time per token generation
   avg(rate(vllm_token_generation_time_seconds_sum[5m]) / rate(vllm_token_generation_time_seconds_count[5m]))
   ```

2. **Rendimiento**:
   ```
   # Requests per second
   sum(rate(vllm_requests_total[5m]))

   # Tokens per second
   sum(rate(vllm_generated_tokens_total[5m]))
   ```

3. **Uso de memoria GPU**:
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

**Ejemplo de configuración de reglas de alerta:**
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

**Métricas adicionales de monitorización:**
1. **Utilización de GPU**: Proporción de utilización de las unidades de cómputo GPU.
2. **Uso de CPU**: Recursos CPU usados para preprocesamiento y posprocesamiento.
3. **Uso de memoria del sistema**: Uso de memoria del host.
4. **Tasa de errores**: Proporción de solicitudes fallidas.
5. **Longitud de cola**: Número de solicitudes que esperan ser procesadas.
6. **Eficiencia de batch**: Tamaño y utilización medios del batch.

**Integración de herramientas de monitorización:**
1. **Prometheus + Grafana**: Recopilación y visualización de métricas.
2. **NVIDIA DCGM Exporter**: Recopilación de métricas GPU.
3. **Jaeger/Zipkin**: Trazado distribuido.
4. **ELK Stack**: Recopilación y análisis de logs.

**Problemas con las otras opciones:**
- A. Recuento de reinicios de Pod: Es un indicador de estabilidad del sistema, pero no refleja directamente el rendimiento del servicio vLLM.
- C. Tasa de pérdida de paquetes de red: Es útil para diagnosticar problemas de red, pero no es una métrica de rendimiento principal de vLLM.
- D. Rendimiento de E/S de disco: Puede ser importante durante la carga del modelo, pero es menos importante para el rendimiento del servicio vLLM en ejecución.
</details>


### 8. ¿Cuál es la configuración de red óptima para los servicios vLLM en Kubernetes?

A. Usar el plugin CNI predeterminado
B. Interfaz de red de alto rendimiento y compatibilidad con RDMA para el paralelismo de tensores
C. Restringir todo el tráfico con políticas de red
D. Implementar service mesh

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Interfaz de red de alto rendimiento y compatibilidad con RDMA para el paralelismo de tensores**

**Explicación:**
La configuración de red óptima para los servicios vLLM en Kubernetes es una interfaz de red de alto rendimiento y compatibilidad con RDMA (Remote Direct Memory Access) para el paralelismo de tensores. Al ejecutar modelos lingüísticos grandes distribuidos entre varias GPU, el rendimiento de la comunicación de GPU a GPU influye significativamente en el rendimiento global. Las interfaces de red de alto rendimiento y RDMA minimizan la latencia de transferencia de datos entre GPU y maximizan el rendimiento para mejorar la inferencia distribuida.

**Importancia de las redes de alto rendimiento:**
1. **Paralelismo de tensores**: Se requiere comunicación frecuente de GPU a GPU al distribuir capas de modelo entre varias GPU.
2. **Fragmentación del modelo**: El rendimiento de red entre nodos es importante al distribuir modelos grandes entre varios nodos.
3. **Sensibilidad a la latencia**: La latencia de comunicación de GPU a GPU afecta directamente a la latencia global de inferencia.
4. **Requisitos de ancho de banda**: Se requiere gran ancho de banda para transferencias de datos de tensores grandes.

**Componentes de una configuración de red óptima:**

1. **Interfaz de red de alto rendimiento**:
   - **NVIDIA ConnectX-6/7**: Admite hasta 200Gbps de ancho de banda.
   - **InfiniBand**: Red de ancho de banda alto y latencia ultrabaja.
   - **RDMA over Converged Ethernet (RoCE)**: Capacidad RDMA en redes Ethernet.

2. **Compatibilidad con RDMA (Remote Direct Memory Access)**:
   - Transferencia directa de datos entre memoria GPU sin intervención de CPU.
   - Latencia minimizada y rendimiento maximizado.
   - GPU Direct RDMA: Transferencia directa de datos entre memoria GPU.

3. **NVLink/NVSwitch**:
   - Conexión de alta velocidad entre GPU dentro del mismo nodo.
   - Hasta 600GB/s de ancho de banda (NVLink 4.0).
   - Importante para sistemas con varias GPU.

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

3. **Aplicar la configuración de red de alto rendimiento al despliegue de vLLM**:
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
NCCL es una biblioteca que optimiza la comunicación de GPU a GPU y puede configurarse con las siguientes variables de entorno:

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

**Configuración distribuida multinodo:**
Al distribuir vLLM entre varios nodos, el rendimiento de red entre nodos es aún más importante. Se requiere la siguiente configuración:

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
- A. Usar el plugin CNI predeterminado: Los plugins CNI predeterminados normalmente no admiten características de redes de alto rendimiento como RDMA ni proporcionan el rendimiento requerido para el paralelismo de tensores.
- C. Restringir todo el tráfico con políticas de red: Esto puede mejorar la seguridad, pero no mejora el rendimiento y puede añadir sobrecarga adicional.
- D. Implementar service mesh: Service mesh es útil para la arquitectura de microservicios, pero añade sobrecarga innecesaria en cargas de trabajo de cómputo de alto rendimiento como vLLM.
</details>


### 9. ¿Cuál es el método más efectivo para mejorar la escalabilidad de los servicios vLLM en Kubernetes?

A. Asignar más núcleos CPU
B. Combinar escalado horizontal (varias réplicas) con balanceo de carga y escalado vertical (GPU más grandes)
C. Asignar más memoria
D. Aprovisionar volúmenes persistentes más grandes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Combinar escalado horizontal (varias réplicas) con balanceo de carga y escalado vertical (GPU más grandes)**

**Explicación:**
El método más efectivo para mejorar la escalabilidad de los servicios vLLM en Kubernetes es combinar escalado horizontal (varias réplicas) con balanceo de carga y escalado vertical (GPU más grandes). Este enfoque puede responder con flexibilidad a diversos requisitos de carga de trabajo y restricciones de recursos, y equilibrar la eficiencia de costes y el rendimiento.

**Beneficios del escalado horizontal:**
1. **Mayor rendimiento**: Se pueden atender más solicitudes simultáneas con más réplicas.
2. **Alta disponibilidad**: El servicio continúa aunque fallen algunas instancias.
3. **Distribución geográfica**: Despliegue en varias regiones para reducir la latencia.
4. **Eficiencia de costes**: Permite ajustar el número de instancias según sea necesario.

**Beneficios del escalado vertical:**
1. **Compatibilidad con modelos más grandes**: Una memoria GPU mayor puede cargar modelos más grandes.
2. **Latencia reducida de una sola solicitud**: Inferencia más rápida con GPU más potentes.
3. **Gestión de contextos más largos**: Más memoria permite gestionar contextos más largos.
4. **Menor sobrecarga de comunicación**: Menor sobrecarga al usar una sola GPU o varias GPU dentro de un nodo.

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

**Configuración de autoescalado horizontal:**
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

**Configuración de balanceo de carga:**
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

**Fragmentación y enrutamiento de modelos:**
Se pueden combinar varios despliegues y enrutarlos para admitir distintos tamaños y tipos de modelos:

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
   - Enrutar las solicitudes a instancias adecuadas según el tamaño y la complejidad del modelo.
   - Optimizar la reutilización de caché KV mediante afinidad de sesión.
2. **Optimización de la asignación de recursos**:
   - Seleccionar el tipo de GPU adecuado para las características de la carga de trabajo.
   - Establecer un tamaño de paralelismo de tensores adecuado.
3. **Estrategia de caché**:
   - Almacenar en caché prompts y respuestas usados con frecuencia.
   - Caché de pesos de modelo.
4. **Escalado de nube híbrida**:
   - Combinar recursos locales y de nube.
   - Escalado en nube para picos de tráfico.

**Pruebas de escalabilidad y benchmarking:**
```bash
# Run load test
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**Problemas con las otras opciones:**
- A. Asignar más núcleos CPU: vLLM está limitado principalmente por GPU y el rendimiento no mejora significativamente solo añadiendo núcleos CPU.
- C. Asignar más memoria: La memoria del sistema es importante, pero la memoria GPU es la restricción principal.
- D. Aprovisionar volúmenes persistentes más grandes: La capacidad de almacenamiento es importante para los modelos, pero no afecta directamente al rendimiento ni a la escalabilidad de la inferencia.
</details>


### 10. ¿Cuál es la consideración de seguridad más importante al desplegar vLLM en Kubernetes?

A. Configuración de políticas de red
B. Protección de pesos de modelo y claves de API, refuerzo de la seguridad de contenedores
C. Configuración de políticas de seguridad de Pod
D. Habilitación del registro de auditoría

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Protección de pesos de modelo y claves de API, refuerzo de la seguridad de contenedores**

**Explicación:**
La consideración de seguridad más importante al desplegar vLLM en Kubernetes es proteger los pesos de modelo y las claves de API, y reforzar la seguridad de los contenedores. Los servicios vLLM gestionan pesos de modelo que constituyen propiedad intelectual, claves de API confidenciales y datos de usuarios; por ello, proteger estos activos y fortalecer la seguridad del entorno de contenedores es lo más importante.

**Consideraciones de seguridad principales:**

1. **Protección de los pesos de modelo**:
   - Los pesos de modelo son activos valiosos con derechos de propiedad intelectual.
   - Deben protegerse contra accesos, copias y filtraciones no autorizados.
   - Se requiere almacenamiento cifrado y cifrado en tránsito.

2. **Protección de claves de API e información de autenticación**:
   - La información de autenticación, como claves de API, tokens y contraseñas, debe gestionarse de forma segura.
   - Deben usarse Kubernetes Secrets o sistemas externos de gestión de secretos.
   - Los secretos deben proporcionarse mediante volúmenes montados en lugar de variables de entorno.

3. **Refuerzo de la seguridad de contenedores**:
   - Aplicar el principio de mínimo privilegio.
   - Ejecutar contenedores como usuario no root.
   - Usar un sistema de archivos de solo lectura.
   - Eliminar capacidades y privilegios innecesarios.

4. **Validación de entradas y filtrado de salidas**:
   - Prevenir ataques de prompt injection.
   - Prevenir filtraciones de información confidencial.
   - Filtrar contenido dañino.

**Ejemplo de configuración de protección de pesos de modelo:**
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

**Protección de claves de API e información de autenticación:**
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

**Refuerzo de la seguridad de contenedores:**
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

**Política de red:**
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

**Validación de entradas y filtrado de salidas:**
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

**Configuración de registro de auditoría:**
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

**Prácticas recomendadas de seguridad adicionales:**
1. **Análisis de seguridad periódico**: Analizar imágenes de contenedor y dependencias para detectar vulnerabilidades.
2. **Principio de mínimo privilegio**: Conceder únicamente los privilegios mínimos necesarios.
3. **Infraestructura inmutable**: Desplegar contenedores nuevos cuando se requieran cambios.
4. **Monitorización de seguridad**: Detectar comportamientos anómalos y enviar alertas.
5. **Plan de respuesta ante emergencias**: Preparar procedimientos de respuesta para incidentes de seguridad.

**Problemas con las otras opciones:**
- A. Configuración de políticas de red: Es importante, pero tiene menor prioridad que proteger los pesos de modelo y las claves de API, y reforzar la seguridad de los contenedores.
- C. Configuración de políticas de seguridad de Pod: Es parte de la seguridad de contenedores, pero no incluye la protección de pesos de modelo y claves de API.
- D. Habilitación del registro de auditoría: Es importante para la monitorización de seguridad, pero tiene menor prioridad que las medidas preventivas.
</details>

### 11. En el benchmark medido de Qwen2.5-7B-Instruct en una sola GPU NVIDIA L4 de esta página, ¿qué ocurrió con la latencia por solicitud cuando la concurrencia pasó de 1 a 16?

A. Creció casi 16 veces, en proporción a la carga añadida
B. Se mantuvo casi plana (+33 %, de p50 5.65s a 7.52s), mientras el rendimiento agregado escaló casi linealmente
C. Disminuyó, porque más solicitudes permitieron a vLLM omitir la fase de prefill
D. No pudo medirse porque la GPU agotó la memoria de caché KV antes de alcanzar la concurrencia 16

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se mantuvo casi plana (+33 %, de p50 5.65s a 7.52s), mientras el rendimiento agregado escaló casi linealmente**

**Explicación:**
Esta es la lección principal del batching continuo: vLLM no pone una solicitud nueva en cola detrás de las que ya se están ejecutando. Se une al batch en el siguiente paso del planificador, por lo que la GPU procesa muchas secuencias en paralelo en lugar de en serie. En esta ejecución medida, la latencia p50 para una respuesta completa de aproximadamente 100-128 tokens solo aumentó de 5.65s con concurrencia 1 a 7.52s con concurrencia 16 (+33 %), mientras que el rendimiento agregado de finalización escaló de aproximadamente 17 tokens/s a 208 tokens/s (medido por el cliente). Ese escalado es la señal de una decodificación limitada por ancho de banda: con concurrencia 1, transmitir aproximadamente 15.2 GB de pesos bf16 desde la memoria GDDR6 para cada token limita la decodificación de una sola solicitud a los aproximadamente 17-18 tokens/s medidos en los cerca de 300 GB/s de ancho de banda de memoria de esta L4, mientras el cómputo permanece en solo un par de puntos porcentuales del límite de aproximadamente 121 TFLOPS bf16 de la GPU incluso en el punto medido de mayor actividad. El batching permite que muchas solicitudes compartan esa misma lectura de pesos casi sin coste, razón por la que el rendimiento escala casi linealmente mientras la latencia apenas varía.

**Por qué las otras opciones son incorrectas:**
- A. Esto describe lo que ocurriría con la gestión serial (sin batching) de solicitudes, no con el batching continuo.
- C. El batching continuo no omite el prefill; cada solicitud nueva todavía pasa por prefill antes de decode, solo que ocurre junto con los pasos de decode de otras solicitudes.
- D. El uso de caché KV de la GPU alcanzó solo el 2.6 % con concurrencia 16 en esta L4 de 24GB, muy lejos de agotarse. El benchmark no llevó la concurrencia lo bastante alto como para encontrar ese límite.
</details>
