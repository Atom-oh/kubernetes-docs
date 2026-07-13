# Resiliencia y alta disponibilidad de EKS

> **Versiones compatibles**: EKS 1.28+, Istio 1.20+, Karpenter 1.0+ **Última actualización**: February 23, 2026

## Descripción general de la resiliencia

La resiliencia es **la capacidad de minimizar el impacto durante las fallas mientras se recupera un estado normal o se mantiene el servicio**. Va más allá de la simple alta disponibilidad (HA) y representa una filosofía de diseño que anticipa las fallas y se prepara para ellas.

### Modelo de madurez de la resiliencia

| Nivel | Nombre       | Alcance           | Tecnologías clave                   | Objetivo de RTO    |
| ----- | ------------ | ----------------- | ------------------------------------ | ----------------- |
| 1     | Básico       | Pod               | Probes, Resource Limits, PDB         | Minutos           |
| 2     | Multi-AZ     | Availability Zone | Topology Spread, ARC Zonal Shift     | Segundos          |
| 3     | Basado en Cell | Unidad de Service | Shuffle Sharding, Cell Router        | Segundos (parcial) |
| 4     | Multi-Region | Region            | Global Accelerator, Data Replication | Casi cero         |

> No todos los servicios requieren el Nivel 4. Elija el nivel adecuado según los requisitos de SLA, las regulaciones y el presupuesto.

***

## Nivel 1: resiliencia básica (nivel de Pod)

### Liveness/Readiness/Startup Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: app
        image: web-app:1.0
        ports:
        - containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: 8080
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 0
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

### PodDisruptionBudget (PDB)

PDB garantiza una disponibilidad mínima durante interrupciones voluntarias.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  # Method 1: Minimum available Pods
  minAvailable: 2
  # Method 2: Maximum unavailable Pods (use only one)
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

```bash
# Check PDB status
kubectl get pdb web-app-pdb
# NAME          MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
# web-app-pdb   2               N/A               1                     5m
```

### Graceful Shutdown

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 5"]
```

> La razón para esperar 5 segundos en `preStop`: si el Pod termina antes de que se propague la eliminación del endpoint, se produce pérdida de tráfico. La espera garantiza tiempo para la propagación.

***

## Nivel 2: estrategia Multi-AZ

### Pod Topology Spread Constraints

Distribuya los Pods de manera uniforme entre las availability zones.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      topologySpreadConstraints:
      # Hard constraint: Maximum 1 difference between AZs
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
        minDomains: 3
      # Soft constraint: Even distribution across nodes
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-app
      containers:
      - name: app
        image: web-app:1.0
```

| Parámetro           | Descripción                                              |
| ------------------- | -------------------------------------------------------- |
| `maxSkew`           | Diferencia máxima en el recuento de Pods entre dominios de topología |
| `topologyKey`       | Base de distribución (zone, hostname, etc.)              |
| `whenUnsatisfiable` | `DoNotSchedule` (Hard) o `ScheduleAnyway` (Soft)         |
| `minDomains`        | Número mínimo de dominios (3 para 3 AZs)                 |

### Karpenter Multi-AZ NodePool

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m7i.xlarge", "m7i.2xlarge"]
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    budgets:
    - nodes: "20%"    # Maximum 20% disrupted simultaneously
    - nodes: "0"
      schedule: "0 9 * * 1-5"   # No disruption during business hours
      duration: 8h
```

### ARC Zonal Shift

AWS Application Recovery Controller (ARC) Zonal Shift redirige automáticamente el tráfico fuera de una AZ con fallas.

```bash
# Start Zonal Shift (manual)
aws arc-zonal-shift start-zonal-shift \
  --resource-identifier arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/my-alb/abc123 \
  --away-from ap-northeast-2a \
  --expires-in 1h \
  --comment "AZ-a experiencing issues"

# Enable Zonal Autoshift (automatic)
aws arc-zonal-shift create-practice-run-configuration \
  --resource-identifier $ALB_ARN \
  --outcome-alarms '[{"alarmIdentifier": {"alarmName": "my-alarm", "region": "ap-northeast-2"}, "type": "CLOUDWATCH"}]'
```

### Consideraciones de almacenamiento

**Prevención de problemas de bloqueo de AZ con EBS:**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer  # Create volume after Pod scheduling
parameters:
  type: gp3
```

**Acceso entre AZ con EFS:**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-12345
  directoryPerms: "700"
```

### Istio Locality-Aware Routing

Priorizar el tráfico dentro de la misma AZ reduce los costos de transferencia entre AZ en un 60-80%.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-app-dr
spec:
  host: web-app.default.svc.cluster.local
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
    connectionPool:
      tcp:
        maxConnections: 100
  # Locality-aware routing is handled automatically by Istio
  # Based on Pod's topology.kubernetes.io/zone label
```

***

## Nivel 3: arquitectura basada en Cell

### Concepto de Cell

Una Cell es **una unidad de servicio autónoma con su propio almacén de datos, caché y cola**. Aísla el radio de impacto de las fallas a una Cell específica.

### Estrategias de particionamiento de Cell

| Estrategia       | Descripción                       | Adecuado para                    |
| -------------- | --------------------------------- | -------------------------------- |
| Basada en clientes | Asignar Cell por hash de ID de cliente | SaaS multi-tenant                |
| Basada en Region   | Particionar por ubicación geográfica  | Servicios globales               |
| Basada en capacidad | Nueva Cell cuando se alcanza la capacidad | Distribución uniforme de carga   |
| Basada en nivel     | Cell por nivel de servicio              | Diferenciación Premium/Standard  |

### Implementación de Cell basada en Namespace

```yaml
# Cell A Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
    tier: standard
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-a-quota
  namespace: cell-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cell-isolation
  namespace: cell-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          cell: a
    - namespaceSelector:
        matchLabels:
          role: cell-router
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          cell: a
    - namespaceSelector:
        matchLabels:
          role: shared-services
```

### Shuffle Sharding

Asignar cada cliente a una combinación de Cells seleccionada aleatoriamente minimiza los clientes afectados por una falla de una sola Cell.

```
With 2 Cell combinations from a pool of 8 Cells:
- Customer A → Cell 1, Cell 5
- Customer B → Cell 2, Cell 7
- Customer C → Cell 1, Cell 3

When Cell 1 fails:
- Customer A → Automatically switches to Cell 5 ✅
- Customer B → Not affected ✅
- Customer C → Automatically switches to Cell 3 ✅
```

Número de combinaciones: C(8,2) = 28, lo que hace que la probabilidad de que dos clientes compartan la misma combinación sea muy baja.

***

## Nivel 4: Multi-Cluster / Multi-Region

### Comparación de patrones de arquitectura

| Patrón             | RTO        | RPO     | Costo         | Complejidad |
| ------------------ | ---------- | ------- | ------------- | ---------- |
| Active-Active      | \~0        | \~0     | 2x+           | Muy alta   |
| Active-Passive     | Min\~Hours | Minutos | 1.5x          | Alta       |
| Regional Isolation | N/A        | N/A     | 1x por region | Media      |
| Hub-Spoke          | Minutos    | Minutos | 1.3x          | Media      |

### Despliegue Multi-Cluster con ArgoCD ApplicationSet

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: web-app-set
  namespace: argocd
spec:
  generators:
  # Cluster Generator: Based on cluster labels
  - clusters:
      selector:
        matchLabels:
          environment: production
  template:
    metadata:
      name: 'web-app-{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/k8s-manifests.git
        targetRevision: main
        path: 'apps/web-app/overlays/{{metadata.labels.region}}'
      destination:
        server: '{{server}}'
        namespace: web-app
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Integración con Global Accelerator

```bash
# Create Global Accelerator
aws globalaccelerator create-accelerator \
  --name prod-accelerator \
  --ip-address-type IPV4

# Add endpoint groups (each region)
aws globalaccelerator create-endpoint-group \
  --listener-arn $LISTENER_ARN \
  --endpoint-group-region ap-northeast-2 \
  --endpoint-configurations "EndpointId=$NLB_ARN_APNE2,Weight=50" \
  --health-check-path /healthz
```

### Federación Istio Multi-Primary

```yaml
# Cross-cluster service discovery
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: web-app-remote
spec:
  hosts:
  - web-app.default.svc.cluster.local
  location: MESH_INTERNAL
  ports:
  - number: 80
    name: http
    protocol: HTTP
  resolution: DNS
  endpoints:
  - address: web-app.remote-cluster.example.com
    locality: us-west-2/us-west-2a
    ports:
      http: 80
```

***

## Chaos Engineering

Chaos Engineering es **una metodología para inyectar fallas intencionalmente en entornos de producción con el fin de descubrir de forma proactiva las debilidades del sistema**.

### AWS Fault Injection Service (FIS)

```json
{
  "description": "AZ Failure Simulation",
  "targets": {
    "eks-pods": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "ALL",
      "parameters": {
        "clusterIdentifier": "production-cluster",
        "namespace": "default",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app"
      }
    }
  },
  "actions": {
    "delete-pods": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {},
      "targets": { "Pods": "eks-pods" }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:error-rate-high"
    }
  ]
}
```

### Litmus Chaos (CNCF Incubating)

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-chaos
  namespace: default
spec:
  appinfo:
    appns: default
    applabel: app=web-app
    appkind: deployment
  chaosServiceAccount: litmus-admin
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: "30"
        - name: CHAOS_INTERVAL
          value: "10"
        - name: FORCE
          value: "false"
```

### Chaos Mesh

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay
  mode: all
  selector:
    namespaces:
    - default
    labelSelectors:
      app: web-app
  delay:
    latency: "100ms"
    jitter: "50ms"
    correlation: "25"
  duration: "5m"
```

### Marco de Game Day

| Fase                   | Actividad                           | Entregable                |
| ---------------------- | ----------------------------------- | ------------------------- |
| 1. Registrar estado estable | Recopilar líneas base de métricas | Captura del dashboard     |
| 2. Inyectar falla      | Ejecutar experimentos FIS/Litmus    | Logs del experimento      |
| 3. Observar recuperación | Monitorear el proceso de recuperación automática | Medición del tiempo de recuperación |
| 4. Analizar impacto    | Analizar tasa de errores y cambios de latencia | Informe de impacto        |
| 5. Revisión post-mortem | Identificar mejoras, Action Items  | Plan de mejora            |

***

## Checklist de implementación

### Nivel 1 básico

* [ ] Configurar Liveness/Readiness Probe para todos los contenedores
* [ ] Configurar requests/limits de recursos
* [ ] Configurar PodDisruptionBudget
* [ ] Implementar Graceful shutdown (hook preStop)
* [ ] Configurar terminationGracePeriodSeconds adecuado

### Nivel 2 Multi-AZ

* [ ] Aplicar Pod Topology Spread Constraints
* [ ] Configurar distribución en 3 AZ en Karpenter NodePool
* [ ] Configurar `WaitForFirstConsumer` en StorageClass
* [ ] Habilitar ARC Zonal Shift
* [ ] Monitorear costos de tráfico Cross-AZ

### Nivel 3 basado en Cell

* [ ] Definir límites de Cell (Namespace o Cluster)
* [ ] Implementar Cell Router
* [ ] Aislar Cells con NetworkPolicy
* [ ] Implementar Shuffle Sharding
* [ ] Configurar ResourceQuota por Cell

### Nivel 4 Multi-Region

* [ ] Decidir el patrón de arquitectura Multi-Region
* [ ] Configurar Global Accelerator
* [ ] Desplegar multi-cluster con ArgoCD ApplicationSet
* [ ] Establecer estrategia de replicación de datos
* [ ] Mantener coherencia con GitOps

***

## Consideraciones de costo

| Elemento                   | Impacto en costo                    | Estrategia de reducción de costos            |
| -------------------------- | ------------------------------------ | -------------------------------------------- |
| Multi-Region Active-Active | 2x+ comparado con una sola region    | Reducir Passive en 50-70% con Active-Passive |
| Tráfico Cross-AZ           | $0.01/GB (dentro de la misma region) | Reducir 60-80% con Locality-aware routing    |
| Spot Instance              | 60-90% de ahorro comparado con On-Demand | Aplicar a workloads sin estado             |
| Chaos Engineering          | Costos de experimentos FIS           | ROI mediante prevención de fallas            |

***

## Próximos pasos

* [Depuración avanzada de EKS y respuesta a incidentes](11-eks-advanced-debugging.md)
* [Cuestionario sobre alta disponibilidad de EKS](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Istio Service Mesh](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md) - Análisis profundo de Circuit Breaker y Retry
