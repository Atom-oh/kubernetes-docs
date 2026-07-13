# Gestión y optimización de costos

> **Versiones compatibles**: EKS 1.29+, EKS Auto Mode GA
> **Última actualización**: July 11, 2026

Esta guía cubre estrategias de optimización de costos para EKS Auto Mode, incluidos análisis de costos, medición de ahorros con Spot, right-sizing de recursos e integración con Savings Plans.

### Actualización de julio de 2026: las tarifas de gestión de GPU se redujeron hasta un 60%

A partir del 1 de julio de 2026, se redujeron las tarifas de gestión de EKS Auto Mode para GPU y tipos de instancia acelerados:

- **G-series**: tarifas de gestión reducidas en un 35%
- **P-series y AWS Trainium**: tarifas de gestión reducidas en un 60%

Las reducciones se aplican automáticamente a todos los clusters de Auto Mode en cada AWS Region donde EKS Auto Mode está disponible; no se requiere ninguna acción. Auto Mode incluye capacidades creadas para workloads acelerados, como la extracción y descompresión paralelas de imágenes en instancias GPU con almacenamiento NVMe local (para que los contenedores grandes y las imágenes de modelos se inicien más rápido) y reparación de nodes con conocimiento de aceleradores, que detecta fallos de hardware GPU y reemplaza automáticamente los nodes no saludables. Consulta [precios de Amazon EKS](https://aws.amazon.com/eks/pricing/) para ver la tabla de tarifas actualizada. ([Anuncio](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price))

---

## Mejores prácticas de optimización de costos

```yaml
# cost-optimization-best-practices.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
        # 1. Allow various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]

        # 2. Include Graviton (ARM) instances (20% cheaper)
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]

        # 3. Prioritize Spot instances
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  # 4. Aggressive Consolidation
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Pod settings for cost optimization
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
spec:
  replicas: 5
  template:
    spec:
      # Prefer Spot
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]

      # Appropriate resource requests (prevent overprovisioning)
      containers:
        - name: app
          resources:
            requests:
              cpu: 250m      # Based on actual usage
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

## Panel de análisis de costos

### Métricas de costo de CloudWatch

Configura un panel de CloudWatch para hacer seguimiento de los costos de Auto Mode:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Node Hours by Capacity Type",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "spot"],
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "on-demand"]
        ],
        "period": 3600,
        "stat": "Average"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Rate",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_created"],
          ["Karpenter", "karpenter_nodeclaims_terminated"]
        ],
        "period": 3600,
        "stat": "Sum"
      }
    }
  ]
}
```

### Integración con Kubecost

Para una asignación detallada de costos, integra Kubecost:

```bash
# Install Kubecost
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace \
  --set kubecostToken="<your-token>"
```

Métricas clave de Kubecost para Auto Mode:

| Métrica | Descripción | Caso de uso |
|--------|-------------|----------|
| Costo del cluster | Gasto total de cómputo | Seguimiento de presupuesto |
| Costo de namespace | Costo por namespace | Chargeback |
| Costo de Pod | Costo por workload | Objetivos de optimización |
| Costo inactivo | Recursos no utilizados | Oportunidades de right-sizing |
| Ahorros de Spot | Diferencia entre Spot y On-Demand | Validar la estrategia de Spot |

---

## Medición de ahorros con Spot Instance

### Calcular ahorros reales con Spot

```bash
# Get current node distribution
kubectl get nodes -L karpenter.sh/capacity-type -L node.kubernetes.io/instance-type | \
  awk 'NR>1 {print $6, $7}' | sort | uniq -c
```

### Script de análisis de ahorros con Spot

```bash
#!/bin/bash
# spot-savings-analysis.sh

# Get Spot and On-Demand node counts
SPOT_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=spot --no-headers | wc -l)
OD_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=on-demand --no-headers | wc -l)

echo "Current Node Distribution:"
echo "  Spot nodes: $SPOT_NODES"
echo "  On-Demand nodes: $OD_NODES"
echo "  Spot percentage: $(echo "scale=2; $SPOT_NODES * 100 / ($SPOT_NODES + $OD_NODES)" | bc)%"

# Estimate savings (assuming average 70% Spot discount)
echo ""
echo "Estimated Monthly Savings:"
echo "  If all were On-Demand: \$X,XXX"
echo "  With current Spot mix: \$X,XXX"
echo "  Monthly savings: \$X,XXX (XX%)"
```

### Consultas de AWS Cost Explorer

Usa Cost Explorer para analizar los costos de Auto Mode:

1. **Filtrar por tag**: `eks:cluster-name` = your-cluster
2. **Agrupar por**: `Instance Type` o `Purchase Option`
3. **Intervalo de tiempo**: Últimos 30 días
4. **Comparar**: gasto de Spot vs On-Demand

---

## Análisis de right-sizing de recursos

### Recomendaciones de VPA

Instala Vertical Pod Autoscaler para obtener recomendaciones de right-sizing:

```bash
# Install VPA
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v1-crd-gen.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-rbac.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/recommender-deployment.yaml
```

Configura VPA en modo de recomendación:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Recommendation only
  resourcePolicy:
    containerPolicies:
      - containerName: '*'
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 4
          memory: 8Gi
```

### Análisis de patrones de uso

```bash
# Get VPA recommendations
kubectl get vpa my-app-vpa -o jsonpath='{.status.recommendation.containerRecommendations[0]}' | jq

# Compare with current requests
kubectl get deployment my-app -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

### Matriz de decisión de right-sizing

| Actual vs recomendado | Acción | Ahorros esperados |
|------------------------|--------|------------------|
| Request > 2x uso | Reducir request | 20-50% |
| Request dentro de 2x | Óptimo | - |
| Request < uso | Aumentar request | Evitar OOM |
| Limit >> request | Reducir limit | Mejor bin-packing |

---

## Estrategia de Savings Plans y Reserved Instances

### Cómo interactúan Savings Plans con Auto Mode

EKS Auto Mode con Savings Plans:

| Escenario | Savings Plans se aplican | Recomendación |
|----------|---------------------|----------------|
| Nodes On-Demand | Sí | Comprar Compute Savings Plans |
| Nodes Spot | No (ya tienen descuento) | No incluir en la cobertura |
| Instancias Graviton | Sí (tarifa separada) | Considerar ARM Savings Plans |
| Workloads mixtos | Parcial | Calcular la línea base On-Demand |

### Dimensionamiento de Savings Plans

```
Recommended Savings Plans Coverage =
    Baseline On-Demand Hours *
    (1 - Expected Spot Percentage) *
    Average Instance Cost

Where:
- Baseline = Minimum sustained usage
- Expected Spot = Target Spot percentage (e.g., 60%)
- Don't over-commit (leave room for Spot)
```

### Mejores prácticas de Savings Plans

| Práctica | Justificación |
|----------|-----------|
| Cubrir el 60-70% de la línea base On-Demand | Dejar margen para la optimización con Spot |
| Usar Compute Savings Plans | Flexibilidad entre tipos de instancia |
| Revisar trimestralmente | Ajustar a medida que evoluciona el workload |
| Excluir instancias GPU | Planes específicos de GPU separados |

### Reserved Instances vs Savings Plans

| Factor | Reserved Instances | Savings Plans |
|--------|-------------------|---------------|
| Flexibilidad | Específica de la instancia | Cualquier instancia |
| Ajuste con Auto Mode | Deficiente (las instancias varían) | Bueno |
| Compromiso | 1 o 3 años | 1 o 3 años |
| Recomendación | No recomendado | Recomendado |

---

## Checklist de optimización de costos

### Victorias rápidas

| Acción | Ahorros estimados | Esfuerzo |
|--------|-------------------|--------|
| Habilitar Spot instances | 60-90% en nodes Spot | Bajo |
| Agregar soporte para ARM/Graviton | 20% en instancias ARM | Bajo |
| Ajustar requests con right-sizing | 10-30% | Medio |
| Habilitar consolidación | 10-20% | Bajo |

### Optimizaciones de mediano plazo

| Acción | Ahorros estimados | Esfuerzo |
|--------|-------------------|--------|
| Implementar VPA | 15-30% | Medio |
| Comprar Savings Plans | 20-40% en On-Demand | Bajo |
| Optimización Multi-AZ | 5-10% | Medio |
| Programación de workloads | 10-20% | Alto |

### Alertas de monitoreo de costos

Configura alertas para anomalías de costos:

```yaml
# CloudWatch Alarm for unexpected node growth
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  NodeCountAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: EKS-Auto-Mode-Node-Count-High
      MetricName: karpenter_nodes_total
      Namespace: Karpenter
      Statistic: Average
      Period: 300
      EvaluationPeriods: 3
      Threshold: 100  # Adjust based on expected max
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic
```

---

## Atribución de costos

### Estrategia de etiquetado para asignación de costos

```yaml
# NodeClass with cost allocation tags
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: "12345"
    Application: my-app
    ManagedBy: eks-auto-mode
```

### Seguimiento de costos a nivel de namespace

```yaml
# Namespace with cost labels
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: "team-a"
    environment: production
```

---

< [Anterior: Operaciones](./05-operations.md) | [Tabla de contenidos](./README.md) | [Siguiente: Ciclo de vida de Node](./07-node-lifecycle.md) >
