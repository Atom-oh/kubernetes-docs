# Gestión del ciclo de vida de Node

> **Versiones compatibles**: EKS 1.29+, EKS Auto Mode GA
> **Última actualización**: July 3, 2026

Esta guía cubre la gestión del ciclo de vida de Node en EKS Auto Mode, incluidas las políticas de expiración, la gestión de AMI, la detección de drift y el monitoreo de la actualidad de los Nodes.

---

## Políticas de expiración de Node (expireAfter)

El campo `expireAfter` controla cuánto tiempo puede ejecutarse un Node antes de ser reemplazado automáticamente.

### Cómo funciona expireAfter

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

### Proceso de expiración

1. El Node alcanza la edad definida en `expireAfter`
2. El controller marca el Node para reemplazo
3. Se aprovisiona un nuevo Node con configuración actualizada
4. Los workloads se migran respetando los PDBs
5. El Node anterior se drena y se termina

### Vida útil máxima de Node de 21 días en Auto Mode

EKS Auto Mode usa el valor predeterminado de `expireAfter` basado en Karpenter, y los Nodes se reemplazan automáticamente una vez que alcanzan una edad máxima de **21 días (504h)** después de su creación. Puedes establecer `expireAfter` en un valor menor que 21 días para un reemplazo más frecuente, pero establecerlo en un valor mayor que 21 días no tiene efecto: Auto Mode impone 21 días como límite máximo estricto. A diferencia de los managed node groups o Karpenter autogestionado, los Nodes no se pueden conservar indefinidamente.

Si ejecutas workloads que mantienen estado durante períodos prolongados (services con tiempos largos de calentamiento de caché, workloads con estado que dependen de almacenamiento local, etc.), planifica con anticipación los procedimientos de reprogramación de Pods y rebalanceo de datos alrededor de este límite de 21 días.

### Valores recomendados de expireAfter

| Caso de uso | expireAfter | Justificación |
|----------|-------------|-----------|
| **Crítico para seguridad** | 24h - 72h | Patching frecuente, requisitos de cumplimiento |
| **Producción estándar** | 168h (7 days) | Equilibrio entre actualidad y estabilidad |
| **Sensible al costo** | 336h (14 days) | Minimiza la sobrecarga de reemplazo (dentro del límite de 21 días) |
| **Desarrollo/Prueba** | 504h (21 days, maximum) | Maximiza la reutilización de Node; este es el límite superior impuesto |
| **Cumplimiento (PCI/HIPAA)** | 72h - 168h | Cumple los requisitos de auditoría |

### Ejemplos de configuración de expireAfter

```yaml
# Security-first configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-critical
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days for security compliance
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
---
# Cost-optimized configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days for cost efficiency
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
```

---

## Estrategia de gestión de AMI

### Cómo Auto Mode selecciona AMIs

EKS Auto Mode selecciona y gestiona automáticamente las AMIs según tu configuración de NodeClass.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ami-managed
spec:
  # AMI family selection
  amiFamily: AL2023  # or Bottlerocket
```

### Comparación de familias de AMI

| Característica | AL2023 | Bottlerocket |
|---------|--------|--------------|
| OS base | Amazon Linux 2023 | OS de contenedores diseñado específicamente |
| Tiempo de arranque | ~40-60 seconds | ~20-40 seconds |
| Superficie de ataque | Estándar | Mínima (raíz de solo lectura) |
| Personalización | Completa (userData) | Limitada (settings API) |
| Gestor de paquetes | dnf | Ninguno (inmutable) |
| Actualizaciones de seguridad | Patching estándar | Actualizaciones atómicas |
| Caso de uso | Workloads generales | Workloads enfocados en seguridad |

### Guías para la selección de familia de AMI

| Tipo de workload | AMI recomendada | Justificación |
|---------------|-----------------|-----------|
| Services web generales | AL2023 | Flexibilidad, tooling familiar |
| Crítico para seguridad | Bottlerocket | Superficie de ataque mínima |
| Cumplimiento (PCI/SOC2) | Bottlerocket | Infraestructura inmutable |
| Workloads de GPU | AL2023 | Soporte de drivers NVIDIA |
| Módulos de kernel personalizados | AL2023 | Acceso completo al OS |
| Escalado rápido | Bottlerocket | Tiempos de arranque más rápidos |

### Configuración de AMI personalizada

```yaml
# For specific AMI requirements
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-ami
spec:
  amiFamily: AL2023

  # AMI selection by tags (if using custom AMIs)
  amiSelectorTerms:
    - tags:
        Name: my-custom-eks-ami
        Environment: production
```

---

## Actualizaciones de AMI y detección de drift

### Cómo las actualizaciones de AMI activan drift

Cuando AWS publica nuevas AMIs o actualizas tu NodeClass:

1. **Lanzamiento de AMI**: AWS publica una nueva AMI optimizada para EKS
2. **Detección de drift**: El controller detecta una discrepancia de versión de AMI
3. **Marcado de Node**: Los Nodes existentes se marcan como "drifted"
4. **Reemplazo**: Los Nodes se reemplazan según la configuración de disruption

### Disparadores de detección de drift

| Cambio | Activa drift | Velocidad de reemplazo |
|--------|----------------|-------------------|
| Nueva versión de AMI | Sí | Según el disruption budget |
| Cambio de familia de AMI en NodeClass | Sí | Scheduling inmediato |
| AMI con patch de seguridad | Sí | Según el disruption budget |
| Cambio de requirements de NodePool | Sí | Según la consolidation |
| Cambio de block device en NodeClass | Sí | Solo Nodes nuevos |

### Monitoreo del estado de drift

```bash
# Check for drifted nodes
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
AGE:.metadata.creationTimestamp,\
DRIFT:.metadata.annotations.karpenter\\.sh/drift-hash

# Check NodeClaim drift status
kubectl get nodeclaims -o wide

# Watch for drift events
kubectl get events --sort-by='.lastTimestamp' | grep -i drift
```

### Control del reemplazo por drift

```yaml
# Slow drift replacement for stability
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
spec:
  template:
    spec:
      expireAfter: 168h
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      # Slow, controlled replacement
      - nodes: "1"
      # No replacement during business hours
      - nodes: "0"
        schedule: "0 9-17 * * mon-fri"
        duration: 8h
```

---

## Políticas de actualidad de Node y patching de seguridad

### Por qué importa la actualidad de Node

| Preocupación | Impacto | Mitigación |
|---------|--------|------------|
| **Patches de seguridad** | Vulnerabilidades sin patch | `expireAfter` corto |
| **Actualizaciones de AMI** | Funcionalidades/correcciones faltantes | Habilita el reemplazo por drift |
| **Drift de configuración** | Comportamiento inconsistente | Rotación regular de Nodes |
| **Cumplimiento** | Hallazgos de auditoría | Política de rotación documentada |

### Estrategia de patching de seguridad

```yaml
# Security-focused NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-patched
spec:
  template:
    spec:
      # Maximum node age for security compliance
      expireAfter: 72h  # 3 days
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Allow faster replacement for security patches
      - nodes: "20%"
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  metadataOptions:
    httpTokens: required  # IMDSv2 only
    httpPutResponseHopLimit: 1

  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        encrypted: true
        volumeType: gp3
```

---

## Compensaciones entre consolidation y expiración

### Cuándo se aplica cada una

| Mecanismo | Disparador | Propósito | Prioridad |
|-----------|---------|---------|----------|
| **Consolidation** | Subutilización | Optimización de costos | Más baja |
| **Expiración** | Umbral de edad | Seguridad/actualidad | Más alta |
| **Drift** | Cambio de configuración | Consistencia | Máxima |

### Interacción entre mecanismos

```
Node Lifecycle Priority:
1. Drift (immediate) - Configuration mismatch
2. Expiration (scheduled) - Age threshold reached
3. Consolidation (opportunistic) - Underutilization detected
```

### Configuración para diferentes prioridades

```yaml
# Cost-priority (consolidation aggressive, expiration relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days - relaxed
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m  # Aggressive consolidation
---
# Security-priority (expiration aggressive, consolidation relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days - aggressive
  disruption:
    consolidationPolicy: WhenEmpty  # Relaxed consolidation
    consolidateAfter: 10m
```

---

## Monitoreo de la distribución de edades de Node

### Monitoreo basado en kubectl

```bash
# List nodes with age
kubectl get nodes --sort-by='.metadata.creationTimestamp' \
  -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type,\
CREATED:.metadata.creationTimestamp,\
AGE:.metadata.creationTimestamp

# Calculate node ages in days
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_seconds=$(($(date +%s) - $(date -d "$created" +%s)))
  age_days=$((age_seconds / 86400))
  age_hours=$(((age_seconds % 86400) / 3600))
  echo "$name: ${age_days}d ${age_hours}h"
done
```

### Monitoreo con Prometheus/Grafana

Consultas clave de Prometheus para la edad de Node:

```promql
# Node age in days
(time() - kube_node_created) / 86400

# Nodes older than 7 days
count(((time() - kube_node_created) / 86400) > 7)

# Average node age by NodePool
avg((time() - kube_node_created) / 86400) by (label_karpenter_sh_nodepool)

# Node age distribution histogram
histogram_quantile(0.50,
  sum(rate(kube_node_created_bucket[24h])) by (le)
)
```

### Reglas de alerting

```yaml
# Prometheus alerting rules for node age
groups:
  - name: node-lifecycle
    rules:
      - alert: NodeTooOld
        expr: (time() - kube_node_created) / 86400 > 10
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Node {{ $labels.node }} is older than 10 days"

      - alert: NodeAgeDistributionSkewed
        expr: stddev((time() - kube_node_created) / 86400) > 3
        for: 4h
        labels:
          severity: info
        annotations:
          summary: "Node ages are highly variable, check rotation"
```

### Dashboard de edad de Node

Crea un dashboard de Grafana con:

| Panel | Consulta | Visualización |
|-------|-------|---------------|
| Conteo de Nodes por bucket de edad | Histograma de edades de Node | Gráfico de barras |
| Edad promedio por NodePool | `avg by (nodepool)` | Panel Stat |
| Nodes más antiguos | Top N por edad | Tabla |
| Nodes próximos a expirar | Edad cercana a `expireAfter` | Lista de alertas |
| Tasa de reemplazo | NodeClaims creados/terminados | Serie temporal |

---

## Mejores prácticas para el ciclo de vida de Node

| Práctica | Recomendación |
|----------|----------------|
| Configurar expireAfter | Configúralo siempre, predeterminado 7 días |
| Usar Bottlerocket para seguridad | Superficie de ataque mínima |
| Monitorear edades de Node | Alerta sobre Nodes > edad esperada |
| Respetar PDBs | Asegura una migración gradual de workloads |
| Escalonar reemplazos | Usa disruption budgets |
| Rastrear versiones de AMI | Monitorea patches de seguridad |

---

< [Anterior: Gestión de costos](./06-cost-management.md) | [Tabla de contenidos](./README.md) | [Siguiente: Optimización de workloads](./08-workload-optimization.md) >
