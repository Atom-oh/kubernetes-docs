# Cuestionario de optimización de workloads de EKS Auto Mode

> **Documento relacionado**: [Optimización específica por carga de trabajo](../../eks-auto-mode/08-workload-optimization.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es la configuración recomendada de NodePool para workloads frontend en una plataforma de comercio electrónico a gran escala?

- A) Solo Spot, Consolidation agresiva
- B) Prioridad On-Demand, Disruption Budget centrado en la disponibilidad
- C) Instancias GPU, configuración de alto rendimiento
- D) Solo instancias optimizadas para memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prioridad On-Demand, Disruption Budget centrado en la disponibilidad**

**Explicación:**
Los workloads frontend están orientados al usuario, por lo que la disponibilidad es la máxima prioridad.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend-tier
spec:
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]  # Availability first
      taints:
        - key: tier
          value: frontend
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
      - nodes: "1"
        schedule: "0 9-23 * * *"  # Peak hours
        duration: 14h
```

</details>

### 2. ¿Cuál es la configuración de NodePool más adecuada para workloads de procesamiento por lotes?

- A) Solo On-Demand, Consolidation conservadora
- B) Solo Spot, familias de instancias diversas, limpieza rápida
- C) Usar solo instancias GPU
- D) Colocar en el NodePool del sistema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo Spot, familias de instancias diversas, limpieza rápida**

**Explicación:**
Los batch jobs son tolerantes a interrupciones, lo que los hace adecuados para instancias Spot.

```yaml
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
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r", "i", "d"]  # Diverse families
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      taints:
        - key: tier
          value: batch
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s  # Quick cleanup
```

</details>

### 3. ¿Cuál es la configuración recomendada de Consolidation para workloads de inferencia ML con GPU?

- A) `consolidateAfter: 0s`
- B) `consolidateAfter: 15m` (considerando el tiempo de inicio de GPU)
- C) `consolidationPolicy: WhenEmptyOrUnderutilized`
- D) Deshabilitar Consolidation

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `consolidateAfter: 15m` (considerando el tiempo de inicio de GPU)**

**Explicación:**
Las instancias GPU tardan más en iniciar, por lo que requieren un valor de consolidateAfter suficiente.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-inference
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
  limits:
    nvidia.com/gpu: 20
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m  # Consider GPU startup time
```

</details>

### 4. ¿Qué estrategia equilibra estabilidad y costo para workloads de API server?

- A) Solo On-Demand
- B) Solo Spot
- C) Spot/On-Demand mixto + incluir Graviton
- D) Solo Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Spot/On-Demand mixto + incluir Graviton**

**Explicación:**
Los API servers necesitan disponibilidad adecuada mientras permiten la optimización de costos.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    metadata:
      labels:
        tier: api
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]  # Mixed
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
      taints:
        - key: tier
          value: api
          effect: NoSchedule
  weight: 10
```

**Ahorro de costos esperado:** ~40%

</details>

### 5. ¿Qué debe verificarse en las aplicaciones para la compatibilidad multi-arquitectura (amd64/arm64)?

- A) No se necesita ninguna verificación especial
- B) Verificar que las container images sean compatibles con multi-arch
- C) Solo comprobar la versión de Kubernetes
- D) Solo comprobar la región de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Verificar que las container images sean compatibles con multi-arch**

**Explicación:**
Para utilizar instancias Graviton (arm64), las container images deben ser compatibles con esa arquitectura.

```bash
# Check image supported architectures
docker manifest inspect nginx:latest | grep architecture

# Multi-arch image build example
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t myapp:latest \
    --push .
```

**Lista de verificación:**
- Verificar la compatibilidad multi-arch de la base image
- Compilar binarios nativos para ambas arquitecturas
- Configurar el build multi-arch en el pipeline de CI/CD

</details>

### 6. ¿Cuál es el método para garantizar que los Pods se programen en el NodePool correcto al separar NodePools por workload?

- A) Coincidencia automática por nombre de Pod
- B) Usar Taint/Toleration y NodeSelector o Affinity
- C) Separación automática por namespace
- D) Separación solo por tags de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar Taint/Toleration y NodeSelector o Affinity**

**Explicación:**
Establece taints en NodePool y agrega tolerations y affinity a los Pods.

```yaml
# Set taint on NodePool
spec:
  template:
    spec:
      taints:
        - key: tier
          value: batch
          effect: NoSchedule

---
# Set toleration and affinity on Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-job
spec:
  template:
    spec:
      tolerations:
        - key: tier
          value: batch
          effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: tier
                    operator: In
                    values: ["batch"]
```

</details>
