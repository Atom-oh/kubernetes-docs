# Cuestionario de gestión de costos de EKS Auto Mode

> **Documento relacionado**: [Gestión de costos](../../eks-auto-mode/06-cost-management.md)

## Preguntas de opción múltiple

### 1. ¿Aproximadamente qué porcentaje de ahorro de costos se puede lograr al incluir instancias Graviton (ARM) para la optimización de costos?

- A) 5%
- B) 10%
- C) 20%
- D) 50%

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 20%**

**Explicación:**
Las instancias basadas en procesadores AWS Graviton (arm64) son aproximadamente un 20% más baratas que las instancias x86 comparables, a la vez que ofrecen un rendimiento excelente.

```yaml
spec:
  template:
    spec:
      requirements:
        # Include Graviton (ARM) instances
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

**Estrategias de optimización de costos:**
- Usar instancias Graviton (ARM): ~20% de ahorro
- Usar instancias Spot: hasta 70-90% de ahorro
- Consolidation agresiva: consolidar nodes infrautilizados
- Resource requests adecuados: prevenir el sobreaprovisionamiento

</details>

### 2. ¿Qué significa que el CPU limit esté establecido en 500 en la configuración `limits` de NodePool?

- A) El CPU máximo por node es de 500 cores
- B) NodePool puede aprovisionar hasta 500 vCPU en total
- C) Máximo de 500m CPU por Pod
- D) CPU limit para todo el cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) NodePool puede aprovisionar hasta 500 vCPU en total**

**Explicación:**
`limits` de NodePool restringe la cantidad total de resources que NodePool puede aprovisionar.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  limits:
    cpu: 500      # Maximum 500 vCPU
    memory: 1Ti   # Maximum 1TB memory
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
```

Esto ayuda a prevenir sobrecostos y a gestionar presupuestos.

</details>

### 3. ¿Qué política de Consolidation limpia automáticamente los nodes infrautilizados para optimizar los costos?

- A) `consolidationPolicy: WhenEmpty`
- B) `consolidationPolicy: WhenEmptyOrUnderutilized`
- C) `consolidationPolicy: Always`
- D) `consolidationPolicy: Aggressive`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `consolidationPolicy: WhenEmptyOrUnderutilized`**

**Explicación:**
La política `WhenEmptyOrUnderutilized` apunta tanto a los nodes vacíos como a los infrautilizados para consolidation.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

**Comparación de políticas:**
- `WhenEmpty`: solo elimina nodes vacíos (conservadora, prioriza la estabilidad)
- `WhenEmptyOrUnderutilized`: optimización de costos agresiva

Efecto de ahorro de costos: consolidar nodes infrautilizados para reducir el recuento total de nodes y los costos de infraestructura

</details>

### 4. ¿Cuál es el enfoque recomendado al usar Savings Plans con EKS Auto Mode?

- A) Compute Savings Plans para flexibilidad de familia de instancias
- B) EC2 Instance Savings Plans para tipos de instancia específicos
- C) Usar solo Reserved Instances
- D) No usar Savings Plans

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Compute Savings Plans para flexibilidad de familia de instancias**

**Explicación:**
Auto Mode usa varios tipos de instancia según los workloads, por lo que Compute Savings Plans son los más adecuados.

**Comparación de Savings Plans:**
| Tipo | Flexibilidad | Descuento |
|------|-------------|----------|
| Compute Savings Plans | Familia de instancias, tamaño, región y OS flexibles | Hasta 66% |
| EC2 Instance Savings Plans | Familia de instancias específica fija | Hasta 72% |

```
Recommended Strategy:
1. Analyze baseline workload volume (3-month baseline)
2. Cover 70% of minimum usage with Compute Savings Plans
3. Run remainder flexibly with Spot/On-Demand
```

</details>

### 5. ¿Qué se requiere para la asignación de costos a nivel de Pod en el análisis de costos usando Kubecost?

- A) Se admite automáticamente sin configuración
- B) Agregar la etiqueta cost-center a los Pods
- C) Instalar el agente de Kubecost e integrar el cluster
- D) AWS Cost Explorer es suficiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Instalar el agente de Kubecost e integrar el cluster**

**Explicación:**
Kubecost es una herramienta de monitoreo de costos nativa de Kubernetes que proporciona análisis de costos detallados.

```bash
# Kubecost installation (Helm)
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
    --namespace kubecost \
    --create-namespace
```

Características de Kubecost:
- Análisis de costos por namespace/workload
- Recomendaciones de eficiencia de resources
- Configuración de alertas de presupuesto
- Integración con AWS para precisión de costos reales

</details>

### 6. ¿Cuál es la mejor práctica para prevenir el sobreaprovisionamiento al configurar resource requests?

- A) Establecer siempre limits y requests iguales
- B) Consultar recomendaciones de VPA basadas en el uso real
- C) Establecer requests lo más altos posible
- D) Omitir la configuración de requests

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Consultar recomendaciones de VPA basadas en el uso real**

**Explicación:**
Use Vertical Pod Autoscaler (VPA) para analizar el uso real de resources y establecer valores de requests adecuados.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Only provide recommendations, no auto-apply
```

Consultar recomendaciones:
```bash
kubectl describe vpa my-app-vpa
```

Esto permite:
- Prevenir el sobreaprovisionamiento (ahorro de costos)
- Prevenir el subaprovisionamiento (garantía de rendimiento)

</details>

### 7. ¿Cuál es la estrategia de separación de NodePool eficiente en costos para workloads multi-tier?

- A) Colocar todos los workloads en un único NodePool
- B) Separar NodePool por tier (frontend/API/batch/ML)
- C) Separar NodePool por tamaño de instancia
- D) Separar NodePool por availability zone

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Separar NodePool por tier (frontend/API/batch/ML)**

**Explicación:**
Separar NodePools según las características del workload logra un equilibrio óptimo entre costo y rendimiento.

| Tier | Estrategia | Ahorro esperado |
|------|----------|-----------------|
| Frontend | On-Demand + Graviton | ~20% |
| API | Spot mixto + Graviton | ~40% |
| Batch | Solo Spot + diversificación | ~70% |
| ML | Selección de tamaño de instancia adecuado | ~30% |

```yaml
# Batch tier example - Maximum cost savings
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
```

</details>

### 8. ¿Qué se necesita para categorizar los costos de EKS Auto Mode por tag en AWS Cost Explorer?

- A) Todos los tags se aplican automáticamente
- B) Es necesario establecer el campo tags en NodeClass
- C) Configurar en AWS Organizations
- D) La categorización basada en tags no es posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es necesario establecer el campo tags en NodeClass**

**Explicación:**
Aplique tags de asignación de costos a los nodes aprovisionados mediante el campo tags en NodeClass.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: production-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: engineering-001
    Project: kubernetes-platform
```

Configuración de AWS Cost Explorer:
1. Habilitar Cost Allocation Tags en Billing Console
2. Seleccionar las claves de tag deseadas
3. Disponible en Cost Explorer después de 24 horas

</details>
