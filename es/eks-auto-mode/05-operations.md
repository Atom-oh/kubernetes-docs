# Operaciones y gestión

> **Versiones compatibles**: EKS 1.29+, EKS Auto Mode GA
> **Última actualización**: February 19, 2026

Esta guía cubre los aspectos operativos de EKS Auto Mode, incluidos disruption budgets, rolling replacement, monitoreo, resolución de problemas y mejores prácticas de seguridad.

---

## Configuración de Disruption Budget

Configura budgets para el reemplazo seguro de nodes.

```yaml
# disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: production-pool
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Default: only 10% of total nodes disrupted simultaneously
      - nodes: "10%"

      # Business hours: minimize disruptions
      - nodes: "1"
        schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
        duration: 9h

      # Weekends: allow more aggressive consolidation
      - nodes: "30%"
        schedule: "0 0 * * sat-sun"
        duration: 48h

      # Emergency maintenance window: no disruptions
      - nodes: "0"
        schedule: "0 0 1 * *"  # 1st of each month
        duration: 24h
```

---

## Estrategia de Rolling Replacement

```yaml
# rolling-replacement-strategy.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: rolling-replacement
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Node expiration time
      expireAfter: 168h  # 7 days
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
      # Limit concurrent disrupted nodes for sequential replacement
      - nodes: "1"
```

### Comparación de estrategias de reemplazo de Node

| Estrategia | Caso de uso | Configuración | Compensaciones |
|----------|----------|---------------|------------|
| **Rolling (Conservadora)** | Producción crítica | `nodes: "1"` | Más lenta, pero más segura |
| **Rolling (Moderada)** | Producción estándar | `nodes: "10%"` | Enfoque equilibrado |
| **Agresiva** | Dev/Test, batch | `nodes: "30%"` | Más rápida, pero más riesgosa |
| **Programada** | Ventanas de mantenimiento | Budgets basados en tiempo | Interrupción predecible |

### Cuándo usar cada estrategia

- **Rolling (Conservadora)**: Workloads con estado, bases de datos, APIs críticas
- **Rolling (Moderada)**: Servicios web estándar, microservices
- **Agresiva**: Runners de CI/CD, procesamiento batch, entornos de desarrollo
- **Programada**: Requisitos de cumplimiento, mantenimiento planificado

---

## Integración con PodDisruptionBudget

```yaml
# pdb-example.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  # Minimum available Pods
  minAvailable: 3
  # Or maximum unavailable Pods
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: web
          image: nginx:latest
          resources:
            requests:
              cpu: 500m
              memory: 256Mi
      # Graceful shutdown during node replacement
      terminationGracePeriodSeconds: 60
```

### Mejores prácticas de PDB

| Tipo de workload | Replicas | Configuración de PDB |
|---------------|----------|-------------------|
| Stateless (3+ replicas) | 3-10 | `minAvailable: N-1` o `maxUnavailable: 1` |
| Stateless (10+ replicas) | 10+ | `maxUnavailable: 10%` |
| Stateful | 3+ | `minAvailable: 2` (mantener quorum) |
| Singleton | 1 | Sin PDB (o aceptar la interrupción) |

---

## Respuesta ante falla de Zone

### Configuración de Deployment Multi-AZ

```yaml
# multi-az-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      # Availability zone distribution
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: ha-app
        # Node distribution
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: ha-app
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
---
# NodePool for guaranteed minimum nodes per zone
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: multi-az-pool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Guarantee minimum capacity per zone
  limits:
    cpu: 1000
```

### Patrones de respuesta ante fallas de Availability Zone

| Patrón | Descripción | Implementación |
|---------|-------------|----------------|
| **Active-Active** | Todas las AZs sirven tráfico | `topologySpreadConstraints` con `DoNotSchedule` |
| **Active-Standby** | Failover a una AZ secundaria | Pod anti-affinity + health checks |
| **Capacity Reservation** | Capacidad preaprovisionada | On-Demand Capacity Reservations |
| **Overflow** | Burst hacia otras AZs | Restricciones `ScheduleAnyway` |

---

## Monitoreo con CloudWatch

EKS Auto Mode envía métricas automáticamente a CloudWatch.

```bash
# CloudWatch metric namespaces
# - AWS/EKS
# - Karpenter

# Key metrics
# - karpenter_nodes_total: Total node count
# - karpenter_pods_pending: Pending Pod count
# - karpenter_nodeclaims_created: Created NodeClaim count
# - karpenter_nodeclaims_terminated: Terminated NodeClaim count
```

### Configuración de CloudWatch Dashboard

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Auto Mode Node Count",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Pending Pods",
        "metrics": [
          ["Karpenter", "karpenter_pods_pending", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Time",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_startup_duration_seconds", "cluster", "my-cluster"]
        ],
        "stat": "p99",
        "period": 300
      }
    }
  ]
}
```

---

## Diagnósticos basados en kubectl

```bash
# Check NodePool status
kubectl get nodepools
kubectl describe nodepool general-purpose

# Check NodeClaim status (nodes being provisioned)
kubectl get nodeclaims
kubectl describe nodeclaim <name>

# Check node status and labels
kubectl get nodes -o wide -L karpenter.sh/nodepool,karpenter.sh/capacity-type

# Check Pending Pods
kubectl get pods -A --field-selector=status.phase=Pending

# Check events
kubectl get events --sort-by='.lastTimestamp' | grep -E "karpenter|nodepool|nodeclaim"

# Node resource usage
kubectl top nodes

# Pod distribution by node
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c | sort -rn
```

---

## Problemas comunes y soluciones

### Problema 1: Pod permanece en estado Pending

```bash
# Analyze cause
kubectl describe pod <pending-pod>

# Common causes:
# 1. Resource requests too large
# 2. NodePool limits exceeded
# 3. nodeSelector/affinity condition mismatch
# 4. taint/toleration mismatch

# Solution: Check NodePool limits
kubectl get nodepool -o yaml | grep -A5 limits

# Solution: Check nodeSelector conditions
kubectl get pod <pending-pod> -o yaml | grep -A10 nodeSelector
```

### Problema 2: Falla en el aprovisionamiento de Node

```bash
# Check NodeClaim status
kubectl describe nodeclaim <name>

# Check error messages in events
kubectl get events --field-selector reason=FailedProvisioning

# Common causes:
# 1. Instance capacity shortage
# 2. Subnet IP exhaustion
# 3. IAM permission issues
# 4. Security group configuration errors

# Solution: Allow more diverse instance types
# Expand NodePool requirements
```

### Problema 3: La consolidación de Node no funciona

```bash
# Check Consolidation status
kubectl get nodeclaims -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
PHASE:.status.phase,\
AGE:.metadata.creationTimestamp

# Check PodDisruptionBudget
kubectl get pdb -A

# Solution: Adjust PDB or check budgets settings
```

### Problema 4: Retraso al reprogramar Pod después de una interrupción de Spot

```bash
# Check Spot interrupt events
kubectl get events --sort-by='.lastTimestamp' | grep -i "spot\|interrupt"

# Solutions for fast re-provisioning:
# 1. Allow diverse instance types
# 2. Reduce consolidateAfter time
# 3. Use mixed Spot and On-Demand
```

---

## Mejores prácticas de seguridad

```yaml
# security-best-practices.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  # IMDSv2 required
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1  # Block Pod IMDS access
    httpTokens: required

  # EBS encryption
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        encrypted: true
        kmsKeyId: arn:aws:kms:ap-northeast-2:123456789:key/xxx

  # Use only private subnets
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"

  # Restrictive security groups
  securityGroupSelectorTerms:
    - tags:
        Type: worker-restricted
---
# Apply Pod Security Standards
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## Checklist de operaciones Day-2

### Tareas diarias

| Tarea | Comando/Acción | Propósito |
|------|----------------|---------|
| Revisar Pods pendientes | `kubectl get pods -A --field-selector=status.phase=Pending` | Identificar problemas de scheduling |
| Revisar la salud de nodes | `kubectl get nodes` | Detectar nodes NotReady |
| Revisar la capacidad de nodes | `kubectl top nodes` | Monitorear presión de recursos |
| Revisar eventos | `kubectl get events --sort-by='.lastTimestamp'` | Detectar advertencias/errores |

### Tareas semanales

| Tarea | Comando/Acción | Propósito |
|------|----------------|---------|
| Revisar la antigüedad de nodes | `kubectl get nodes --sort-by='.metadata.creationTimestamp'` | Rastrear la frescura de nodes |
| Auditar límites de NodePool | `kubectl get nodepools -o yaml` | Garantizar límites adecuados |
| Revisar la consolidación | Revisar métricas de CloudWatch | Verificar la optimización de costos |
| Revisar uso de Spot | Revisar la distribución de capacity type | Optimizar costo/disponibilidad |

### Tareas mensuales

| Tarea | Comando/Acción | Propósito |
|------|----------------|---------|
| Revisar versiones de AMI | Revisar IDs de AMI de nodes | Aplicación de parches de seguridad |
| Auditar security groups | Revisar configuración de NodeClass | Cumplimiento de seguridad |
| Análisis de costos | AWS Cost Explorer | Seguimiento del presupuesto |
| Planificación de capacidad | Revisar tendencias de uso | Escalar adecuadamente |

---

## Automatización de operaciones

### Alertas de rotación automatizadas

```yaml
# CloudWatch Alarm for old nodes
# Create alarm when nodes exceed age threshold
```

```bash
# Script to check node ages
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_days=$(( ($(date +%s) - $(date -d "$created" +%s)) / 86400 ))
  if [ $age_days -gt 7 ]; then
    echo "WARNING: Node $name is $age_days days old"
  fi
done
```

### Monitoreo de cumplimiento de PDB

```bash
# Check PDB status across all namespaces
kubectl get pdb -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
MIN-AVAILABLE:.spec.minAvailable,\
MAX-UNAVAILABLE:.spec.maxUnavailable,\
CURRENT:.status.currentHealthy,\
DESIRED:.status.desiredHealthy,\
DISRUPTIONS-ALLOWED:.status.disruptionsAllowed
```

### Consultas de Capacity Dashboard

Consultas clave de Prometheus para monitoreo de capacity:

```promql
# Total nodes by NodePool
count(kube_node_labels) by (label_karpenter_sh_nodepool)

# Node CPU utilization by pool
avg(1 - rate(node_cpu_seconds_total{mode="idle"}[5m])) by (node) * on(node) group_left(label_karpenter_sh_nodepool) kube_node_labels

# Pending pods over time
sum(kube_pod_status_phase{phase="Pending"})

# Node age distribution
(time() - kube_node_created) / 86400
```

---

## Checklist de resumen de operaciones

| Área | Elemento de checklist | Estado |
|------|----------------|--------|
| **Configuración** | Límites de NodePool configurados | |
| | Disruption Budget configurado | |
| | Configuración de seguridad de NodeClass revisada | |
| **Monitoreo** | CloudWatch dashboard creado | |
| | Alarmas configuradas (Pod Pending, fallas de provisioning) | |
| | Monitoreo de costos configurado | |
| **Disponibilidad** | PodDisruptionBudget configurado | |
| | Distribución Multi-AZ verificada | |
| | Relación de mezcla Spot/On-Demand revisada | |
| **Costo** | Relación de Spot instances optimizada | |
| | Política de consolidación revisada | |
| | Idoneidad de resource requests/limits revisada | |

---

< [Anterior: Estrategias de Spot](./04-spot-strategies.md) | [Tabla de contenidos](./README.md) | [Siguiente: Gestión de costos](./06-cost-management.md) >
