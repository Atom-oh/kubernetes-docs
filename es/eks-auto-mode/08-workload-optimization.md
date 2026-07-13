# Optimización específica por carga de trabajo

> **Versiones compatibles**: EKS 1.29+, EKS Auto Mode GA
> **Última actualización**: February 19, 2026

Esta guía cubre cómo optimizar las configuraciones de EKS Auto Mode para diferentes tipos de cargas de trabajo, incluidos servicios web, procesamiento por lotes, workloads de GPU y entrenamiento de AI/ML.

---

## Servicios web (disponibilidad primero)

```yaml
# web-service-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    metadata:
      labels:
        tier: web
    spec:
      requirements:
        # General-purpose instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Use only On-Demand (availability first)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: tier
          value: web
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      - nodes: "10%"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 10
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      tolerations:
        - key: tier
          value: web
          effect: NoSchedule
      nodeSelector:
        tier: web
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: web-frontend
                topologyKey: kubernetes.io/hostname
      containers:
        - name: web
          image: my-web-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
```

### Resumen de optimización para servicios web

| Aspecto | Recomendación | Justificación |
|--------|----------------|-----------|
| Tipo de capacidad | On-Demand | Requisito de alta disponibilidad |
| Familia de instancias | Serie M (propósito general) | CPU/memoria equilibradas |
| Anti-affinity | Por hostname | Distribuir entre nodos |
| Health checks | Tanto readiness como liveness | Detección rápida de fallos |
| PDB | minAvailable: N-1 | Mantener el Service durante las actualizaciones |

---

## Procesamiento por lotes (costo primero, Spot)

```yaml
# batch-processing-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    metadata:
      labels:
        tier: batch
    spec:
      requirements:
        # Compute-optimized
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["xlarge", "2xlarge", "4xlarge"]
        # Use only Spot (cost first)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        # Various instance types for better Spot availability
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
      taints:
        - key: tier
          value: batch
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processing
spec:
  parallelism: 20
  completions: 100
  backoffLimit: 10
  template:
    spec:
      tolerations:
        - key: tier
          value: batch
          effect: NoSchedule
      nodeSelector:
        tier: batch
      restartPolicy: OnFailure
      terminationGracePeriodSeconds: 30
      containers:
        - name: processor
          image: my-batch-processor:latest
          resources:
            requests:
              cpu: 2000m
              memory: 4Gi
            limits:
              cpu: 4000m
              memory: 8Gi
          env:
            - name: SPOT_AWARE
              value: "true"
```

### Resumen de optimización para procesamiento por lotes

| Aspecto | Recomendación | Justificación |
|--------|----------------|-----------|
| Tipo de capacidad | Solo Spot | Máximo ahorro de costos |
| Familia de instancias | Serie C (optimizada para cómputo) | Cargas de trabajo intensivas en CPU |
| Diversidad de instancias | Varias generaciones | Mejor disponibilidad de Spot |
| Política de reinicio | OnFailure | Gestionar interrupciones de Spot |
| Consolidación | Agresiva (30s) | Limpieza rápida después de los jobs |

---

## Workloads de GPU (p5, g5)

```yaml
# gpu-workload-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    metadata:
      labels:
        tier: gpu
        accelerator: nvidia
    spec:
      requirements:
        # GPU instances
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g", "p"]
        - key: karpenter.k8s.aws/instance-gpu-manufacturer
          operator: In
          values: ["nvidia"]
        # Specific GPU instance types
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge", "p5.48xlarge"]
        # On-Demand (GPU Spot availability is low)
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
  limits:
    nvidia.com/gpu: 16
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m  # GPU takes longer to start
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: gpu-nodeclass
spec:
  amiFamily: AL2023
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 200Gi  # Large volume for model caching
        volumeType: gp3
        iops: 6000
        throughput: 250
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      tolerations:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
      nodeSelector:
        tier: gpu
      containers:
        - name: inference
          image: my-ml-model:latest
          resources:
            limits:
              nvidia.com/gpu: 1
            requests:
              cpu: 4000m
              memory: 16Gi
```

### Guía de selección de instancias GPU

| Instancia | GPU | Memoria de GPU | Caso de uso |
|----------|------|------------|----------|
| g5.xlarge | 1x A10G | 24GB | Inferencia pequeña |
| g5.2xlarge | 1x A10G | 24GB | Inferencia mediana |
| g5.4xlarge | 1x A10G | 24GB | Inferencia grande |
| g5.12xlarge | 4x A10G | 96GB | Servicio de múltiples modelos |
| p5.48xlarge | 8x H100 | 640GB | Entrenamiento a gran escala |

### Resumen de optimización para GPU

| Aspecto | Recomendación | Justificación |
|--------|----------------|-----------|
| Tipo de capacidad | On-Demand | La disponibilidad de GPU Spot es limitada |
| Almacenamiento | 200GB+ gp3 | Caché de modelos, checkpoints |
| Consolidación | Relajada (10m) | El arranque de GPU es más lento |
| Límites | Establecer límite de nvidia.com/gpu | Evitar costos descontrolados de GPU |

---

## Workloads de entrenamiento de AI/ML

```yaml
# ml-training-optimized.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    metadata:
      labels:
        tier: ml-training
    spec:
      requirements:
        # Large-scale GPU instances
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["p5.48xlarge", "p4d.24xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: ml-training
          value: "true"
          effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: ml-training-nodeclass
  limits:
    nvidia.com/gpu: 64
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ml-training-nodeclass
spec:
  amiFamily: AL2023
  # Enable EFA networking
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 500Gi
        volumeType: gp3
        iops: 16000
        throughput: 1000
    # Additional volume for training data
    - deviceName: /dev/xvdb
      ebs:
        volumeSize: 2000Gi
        volumeType: gp3
---
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training
spec:
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      template:
        spec:
          tolerations:
            - key: ml-training
              value: "true"
              effect: NoSchedule
          nodeSelector:
            tier: ml-training
          containers:
            - name: pytorch
              image: my-training-image:latest
              resources:
                limits:
                  nvidia.com/gpu: 8
    Worker:
      replicas: 3
      template:
        spec:
          tolerations:
            - key: ml-training
              value: "true"
              effect: NoSchedule
          nodeSelector:
            tier: ml-training
          containers:
            - name: pytorch
              image: my-training-image:latest
              resources:
                limits:
                  nvidia.com/gpu: 8
```

### Resumen de optimización para entrenamiento de ML

| Aspecto | Recomendación | Justificación |
|--------|----------------|-----------|
| Tipo de instancia | p5.48xlarge, p4d.24xlarge | Capacidad máxima de GPU |
| Almacenamiento | Raíz de 500GB+, datos de 2TB+ | Conjuntos de datos grandes, checkpoints |
| IOPS | 16000+ | Escrituras rápidas de checkpoints |
| Redes | Con EFA habilitado | Entrenamiento distribuido |
| Framework | PyTorchJob, TFJob | Soporte distribuido nativo |

---

## Referencia rápida de tipos de workload

| Workload | Estrategia de NodePool | Tipos de instancia | Capacidad | Consolidación |
|----------|-------------------|----------------|----------|---------------|
| Servicios web | Disponibilidad primero | Serie m | On-Demand | Moderada (5m) |
| Backend de API | Mixta | Series m/c | Mixta | Moderada (5m) |
| Procesamiento por lotes | Costo primero | Serie c | Solo Spot | Agresiva (30s) |
| CI/CD | Costo primero | Series c/m | Spot preferido | Agresiva (1m) |
| Bases de datos | Estabilidad primero | Serie r | On-Demand | Conservadora (10m) |
| Inferencia de GPU | Disponibilidad primero | Serie g5 | On-Demand | Relajada (10m) |
| Entrenamiento de ML | Rendimiento primero | p5/p4d | On-Demand | Relajada (15m) |
| Procesamiento de streams | Equilibrada | Series m/c | Mixta | Moderada (5m) |

---

## Directrices de recursos de Pod

### Workloads limitados por CPU

```yaml
resources:
  requests:
    cpu: 2000m      # Request what you need
    memory: 2Gi
  limits:
    cpu: 4000m      # Allow some burst
    memory: 4Gi
```

### Workloads limitados por memoria

```yaml
resources:
  requests:
    cpu: 500m
    memory: 8Gi     # Request what you need
  limits:
    cpu: 1000m
    memory: 8Gi     # Limit = request (no overcommit)
```

### Workloads de GPU

```yaml
resources:
  requests:
    cpu: 4000m
    memory: 16Gi
  limits:
    nvidia.com/gpu: 1   # GPU limits are always required
    cpu: 8000m
    memory: 32Gi
```

---

< [Anterior: Ciclo de vida de Node](./07-node-lifecycle.md) | [Tabla de contenidos](./README.md) | [Siguiente: Guía de migración](./09-migration-guide.md) >
