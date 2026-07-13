# Estrategias de utilización de Spot Instance

> **Versiones compatibles**: EKS 1.29+, EKS Auto Mode GA
> **Última actualización**: February 19, 2026

Esta guía cubre estrategias para usar Spot instances de forma eficaz con EKS Auto Mode, incluidas configuraciones de capacidad mixta, diversificación y manejo de interrupciones.

---

## Estrategia mixta de Spot y On-Demand

Una estrategia mixta logra tanto estabilidad como eficiencia de costos.

```yaml
# spot-ondemand-mixed.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        # Allow both Spot and On-Demand
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Configure Spot preference in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: spot-friendly
  template:
    metadata:
      labels:
        app: spot-friendly
    spec:
      # Prefer Spot instances
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]
      # For critical workloads, require On-Demand
      # requiredDuringSchedulingIgnoredDuringExecution:
      #   nodeSelectorTerms:
      #     - matchExpressions:
      #         - key: karpenter.sh/capacity-type
      #           operator: In
      #           values: ["on-demand"]
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
```

### Pautas de selección del tipo de capacidad

| Tipo de workload | Capacidad recomendada | Justificación |
|---------------|---------------------|-----------|
| Servicios web sin estado | Spot preferido | Puede manejar interrupciones |
| Procesamiento por lotes | Solo Spot | Ahorro de costos, reintentable |
| Bases de datos | Solo On-Demand | Integridad de datos |
| Runners de CI/CD | Spot preferido | Ahorro de costos, reintentable |
| Inferencia de machine learning | Mixta | Equilibra costo y disponibilidad |
| Entrenamiento de machine learning | Mixta con checkpointing | De larga duración, puede crear checkpoints |

---

## Diversificación de Spot Instance

Use tipos de instancia diversos para distribuir el riesgo de interrupción.

```yaml
# diversified-spot.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
      requirements:
        # Various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # Various generations
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # Various sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Various architectures
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        # Use only Spot
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Fast re-provisioning on Spot interrupt
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Mejores prácticas de diversificación

| Estrategia | Beneficio | Configuración |
|----------|---------|---------------|
| Varias familias de instancias | Reduce interrupciones correlacionadas | `["m", "c", "r", "i", "d"]` |
| Varias generaciones | Accede a un pool de capacidad más grande | `["5", "6", "7"]` |
| Varios tamaños | Flexibilidad en el aprovisionamiento | `["large", "xlarge", "2xlarge"]` |
| Varias arquitecturas | Pool de capacidad 2x | `["amd64", "arm64"]` |

---

## Manejo de interrupciones de Spot

### Configuración de Disruption Budget

```yaml
# spot-disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-with-disruption-budget
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    # Limit concurrent node disruptions
    budgets:
      - nodes: "10%"    # Only 10% of total nodes simultaneously
      - nodes: "3"      # Or maximum 3 nodes
      # Minimize disruptions during business hours
      - nodes: "0"
        schedule: "0 9-18 * * mon-fri"  # Weekdays 9-18
        duration: 9h
```

### Configuración de Pod para conciencia de Spot

```yaml
# Configure Spot interrupt handling in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      # Allow time for graceful shutdown
      terminationGracePeriodSeconds: 120
      containers:
        - name: app
          image: my-app:latest
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 90"]
      # Spread across multiple AZs
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: spot-aware
```

### Lista de comprobación para el manejo de interrupciones

| Elemento | Descripción | Implementación |
|------|-------------|----------------|
| Apagado ordenado | Maneje SIGTERM correctamente | `terminationGracePeriodSeconds` |
| Hook PreStop | Retrasa la terminación | `lifecycle.preStop` |
| Distribución multi-AZ | Sobrevive a interrupciones de toda una AZ | `topologySpreadConstraints` |
| Varias réplicas | Sin punto único de falla | `replicas > 1` |
| Externalización del estado | No almacene estado localmente | Use bases de datos/cachés externos |

---

## Ejemplos de ahorro de costos

```
+-----------------------------------------------------------------------------+
|                       Spot Instance Cost Savings Examples                    |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Workload Type          On-Demand Cost   Spot Cost      Savings             |
|  ---------------------------------------------------------------------------  |
|  Batch Processing        $1,000/month    $300/month     70%                 |
|  Dev/Test Environment    $2,000/month    $500/month     75%                 |
|  CI/CD Pipeline          $500/month      $150/month     70%                 |
|  Non-critical API Server $3,000/month    $1,200/month   60%                 |
|                                                                              |
|  * Spot instance prices vary based on supply and demand                      |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Cálculo del ahorro con Spot

Para estimar sus posibles ahorros con Spot:

1. **Identifique workloads aptos para Spot**: Sin estado, tolerantes a fallas, flexibles
2. **Revise el historial de precios de Spot**: Use AWS Spot Instance Advisor
3. **Calcule el costo base On-Demand**: Gasto actual o proyectado
4. **Aplique el descuento promedio de Spot**: Normalmente 60-90% menos que On-Demand
5. **Considere la sobrecarga por interrupciones**: Cómputo adicional para reaprovisionamiento

### Fórmula de ahorro con Spot

```
Estimated Monthly Savings =
    (On-Demand Hours * On-Demand Price) -
    (Spot Hours * Spot Price) -
    (Interrupt Overhead * On-Demand Price)

Where:
- Interrupt Overhead = Estimated interrupts * Recovery time * Instance count
```

---

## Resumen de mejores prácticas de Spot

| Práctica | Descripción |
|----------|-------------|
| Diversificar tipos de instancia | Use más de 10 tipos de instancia para reducir el riesgo de interrupción |
| Usar varias AZs | Distribuya en más de 3 AZs para disponibilidad |
| Establecer períodos de gracia adecuados | Permita más de 120 segundos para el apagado ordenado |
| Implementar health checks | Detecte y reemplace pods no saludables rápidamente |
| Usar distribución topológica | Evite que todas las réplicas estén en el mismo pool de Spot |
| Externalizar el estado | No almacene datos críticos en nodos Spot |
| Establecer disruption budgets | Limite las interrupciones concurrentes |
| Monitorear métricas de Spot | Haga seguimiento de interrupciones y ahorros |

---

< [Anterior: Comportamiento de escalado](./03-scaling-behavior.md) | [Tabla de contenidos](./README.md) | [Siguiente: Operaciones](./05-operations.md) >
