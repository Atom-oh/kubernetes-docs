# Cuestionario de ubicación de workloads de EKS Hybrid Nodes

> **Documento relacionado**: [Workload Placement](../../eks-hybrid-nodes/06-workload-placement.md)

## Preguntas de opción múltiple

### 1. ¿Cuál NO es un método usado para ubicar Pods en nodos específicos en Kubernetes?

A. nodeSelector
B. Node Affinity
C. Taints/Tolerations
D. PodDisruptionBudget

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. PodDisruptionBudget**

**Explicación:**
PodDisruptionBudget (PDB) se usa para garantizar una disponibilidad mínima durante interrupciones voluntarias, no para la ubicación de Pods.

**Métodos de ubicación de Pods:**
- **nodeSelector**: Selección simple de nodos basada en labels
- **Node Affinity**: Selección compleja de nodos basada en reglas
- **Taints/Tolerations**: Restringen los nodos para aceptar solo Pods específicos
- **Pod Affinity/Anti-Affinity**: Definen relaciones de ubicación entre Pods

```yaml
# nodeSelector example
spec:
  nodeSelector:
    location: onprem

# Node Affinity example
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: gpu
            operator: In
            values: ["nvidia-a100"]
```

</details>

### 2. ¿Cuál es el comando correcto para establecer un Taint en Hybrid Nodes de modo que solo se ubiquen allí workloads de GPU?

A. kubectl label node hybrid-node-1 gpu=true
B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule
C. kubectl annotate node hybrid-node-1 gpu=nvidia
D. kubectl cordon hybrid-node-1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule**

**Explicación:**
Los Taints restringen la programación solo a Pods que toleran el taint.

```bash
# Set Taint
kubectl taint node hybrid-node-1 dedicated=gpu:NoSchedule

# Verify Taint
kubectl describe node hybrid-node-1 | grep Taints
```

```yaml
# Toleration that allows the Taint
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/gpu: 1
```

**Tipos de efecto de Taint:**
- **NoSchedule**: Impide la programación de nuevos Pods
- **PreferNoSchedule**: Evita la programación si es posible
- **NoExecute**: También desaloja Pods existentes

</details>

### 3. En una estrategia de cloud bursting, ¿qué método se usa para mover workloads a nodos de cloud cuando los recursos on-premises son insuficientes?

A. Eliminar y volver a crear Pods manualmente
B. Usar preferredDuringSchedulingIgnoredDuringExecution de Node Affinity
C. Ubicar todos los Pods en cloud
D. Eliminar y volver a crear el cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar preferredDuringSchedulingIgnoredDuringExecution de Node Affinity**

**Explicación:**
Cloud bursting implementa una estrategia de preferencia on-premises y respaldo en cloud.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst-workload
spec:
  replicas: 10
  template:
    spec:
      affinity:
        nodeAffinity:
          # Prefer on-premises (not required)
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["onprem"]
          - weight: 50
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["cloud"]
      containers:
      - name: app
        image: myapp:v1
```

**Patrón de cloud bursting:**
```
[On-premises capacity: 8 nodes]    [Cloud capacity: Unlimited]
      | Preferred                       | Fallback
  Pods 1-8 placed -----------------> Pods 9+ overflow
```

</details>

### 4. ¿Qué significa maxSkew al usar TopologySpreadConstraints para distribuir Pods uniformemente entre zonas?

A. Conteo mínimo de Pods
B. Diferencia máxima en el conteo de Pods entre zonas
C. Conteo total de Pods
D. Máximo de Pods por nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Diferencia máxima en el conteo de Pods entre zonas**

**Explicación:**
`maxSkew` define el desequilibrio máximo en el conteo de Pods entre dominios de topología (por ejemplo, zonas).

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: distributed-app
spec:
  replicas: 6
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: distributed-app
```

**Ejemplo de maxSkew=1:**
```
Zone A: 2 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Balanced)
Zone A: 3 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=1, Allowed)
Zone A: 4 Pods  |  Zone B: 2 Pods  |  Zone C: 2 Pods  (Skew=2, Not Allowed)
```

**Opciones de whenUnsatisfiable:**
- **DoNotSchedule**: Rechaza la programación si se infringe la restricción
- **ScheduleAnyway**: Programa incluso si se infringe la restricción (mejor esfuerzo)

</details>

### 5. ¿Cómo ubicas Pods en nodos donde residen los datos por consideraciones de localidad de datos?

A. Programación aleatoria
B. Usar labels de nodo y nodeSelector para ubicación por proximidad a los datos
C. Seleccionar siempre nodos de cloud
D. Orden alfabético del nombre del Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar labels de nodo y nodeSelector para ubicación por proximidad a los datos**

**Explicación:**
Para la localidad de datos, etiqueta los nodos donde se almacenan los datos y ubica los Pods usando esos labels.

```bash
# Label nodes with data location
kubectl label node storage-node-1 data-location=primary-storage
kubectl label node storage-node-2 data-location=replica-storage
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
spec:
  template:
    spec:
      nodeSelector:
        data-location: primary-storage
      containers:
      - name: processor
        image: data-processor:v1
        volumeMounts:
        - name: local-data
          mountPath: /data
      volumes:
      - name: local-data
        hostPath:
          path: /mnt/data
```

**Beneficios de la localidad de datos:**
- Minimiza la latencia de red
- Reduce los costos de transferencia de datos
- Mejora el rendimiento de procesamiento

</details>

### 6. ¿Por qué usar Pod Anti-Affinity para evitar que los Pods de la misma aplicación se ubiquen en el mismo nodo?

A. Ahorro de costos
B. Alta disponibilidad y aislamiento de fallas
C. Mejora de la velocidad de red
D. Ahorro de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Alta disponibilidad y aislamiento de fallas**

**Explicación:**
Pod Anti-Affinity distribuye Pods de la misma aplicación entre distintos nodos para mantener la disponibilidad del servicio incluso durante fallas de un solo nodo.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ha-webapp
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: ha-webapp
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values: ["ha-webapp"]
            topologyKey: kubernetes.io/hostname
      containers:
      - name: web
        image: nginx:1.25
```

**Resultado:**
```
Node 1: ha-webapp-pod-1
Node 2: ha-webapp-pod-2
Node 3: ha-webapp-pod-3
(Only 1 placed per node)
```

Si un nodo falla, solo se ve afectado 1 Pod, y los 2 restantes continúan proporcionando servicio.

</details>
