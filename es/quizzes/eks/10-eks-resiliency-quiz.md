# Cuestionario sobre alta disponibilidad y resiliencia de Amazon EKS

Este cuestionario evalúa tu comprensión de la alta disponibilidad (HA) de clústeres de Amazon EKS, la resiliencia, la implementación Multi-AZ, Cell-Based Architecture (arquitectura basada en Cells), Chaos Engineering, PodDisruptionBudget y Topology Spread Constraints.

## Descripción general del cuestionario
- Arquitectura y configuración Multi-AZ
- Patrones de Cell-Based Architecture
- Principios y herramientas de Chaos Engineering
- Configuración de PodDisruptionBudget (PDB)
- Topology Spread Constraints
- Disaster Recovery y Failover

## Preguntas de opción múltiple

### 1. ¿Cuál es el beneficio principal de una implementación Multi-AZ en Amazon EKS?

A. Reducción de costos
B. Mantener la disponibilidad de la aplicación incluso durante una falla de una sola AZ
C. Mayor latencia de red
D. Menor complejidad de administración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Mantener la disponibilidad de la aplicación incluso durante una falla de una sola AZ**

**Explicación:**
El beneficio clave de una implementación Multi-AZ es que, incluso si falla una sola Availability Zone (AZ), las cargas de trabajo pueden continuar ejecutándose en otras AZs, manteniendo la disponibilidad de la aplicación.

**Beneficios clave de la implementación Multi-AZ:**
- Failover automático durante una falla de una sola AZ
- Tolerancia a fallas a nivel de datacenter
- Capacidad para lograr una disponibilidad del 99.99%+
- Capacidad mejorada de disaster recovery regional

```yaml
# Multi-AZ Node Group Configuration Example
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ha-cluster
  region: us-west-2
nodeGroups:
  - name: ng-multi-az
    instanceType: m5.large
    desiredCapacity: 6
    availabilityZones: ["us-west-2a", "us-west-2b", "us-west-2c"]
```

</details>

### 2. ¿Cuál es el propósito principal de PodDisruptionBudget (PDB)?

A. Limitar el uso de CPU de los Pods
B. Asegurar una cantidad mínima de Pods disponibles durante interrupciones voluntarias
C. Controlar el tráfico de red entre Pods
D. Monitorear el uso de memoria de los Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Asegurar una cantidad mínima de Pods disponibles durante interrupciones voluntarias**

**Explicación:**
PodDisruptionBudget (PDB) asegura que una cantidad mínima de Pods permanezca en ejecución durante interrupciones voluntarias, como el drenado de nodos, actualizaciones de clúster y eventos de autoscaling.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  minAvailable: 2  # or maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

**Características clave de PDB:**
- `minAvailable`: cantidad mínima de Pods que deben permanecer disponibles
- `maxUnavailable`: cantidad máxima de Pods que pueden estar no disponibles simultáneamente
- Asegura la continuidad del Service durante actualizaciones rolling y mantenimiento de nodos

</details>

### 3. ¿Qué significa `whenUnsatisfiable: DoNotSchedule` en Topology Spread Constraints?

A. Programar el Pod en cualquier nodo si las restricciones no se pueden satisfacer
B. Rechazar la programación del Pod si las restricciones no se pueden satisfacer
C. Ignorar las restricciones y programar siempre
D. Eliminar los Pods existentes cuando se infringen las restricciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Rechazar la programación del Pod si las restricciones no se pueden satisfacer**

**Explicación:**
`whenUnsatisfiable: DoNotSchedule` rechaza la programación del Pod si no se pueden satisfacer las restricciones de distribución de topología. Se usa al aplicar políticas de distribución estrictas.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
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
            app: web-app
```

**Opciones de whenUnsatisfiable:**
- `DoNotSchedule`: rechaza la programación si no se cumplen las restricciones (restricción fuerte)
- `ScheduleAnyway`: mejor esfuerzo para satisfacer las restricciones; programa en cualquier lugar si no es posible (restricción flexible)

</details>

### 4. ¿Cuál NO es una característica clave de una "Cell" en Cell-Based Architecture?

A. Puede implementarse y escalarse de forma independiente
B. Las fallas se propagan a todo el sistema
C. Unidad funcional autónoma
D. Acoplamiento flexible con otras Cells

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Las fallas se propagan a todo el sistema**

**Explicación:**
El propósito central de Cell-Based Architecture es el aislamiento de fallas. Cada Cell opera de forma independiente, de modo que una falla en una Cell no se propaga a otras Cells.

**Principios centrales de Cell-Based Architecture:**
1. **Aislamiento de fallas**: una falla en una Cell no afecta a las demás
2. **Implementación independiente**: cada Cell puede actualizarse individualmente
3. **Escalado horizontal**: escalar la capacidad a nivel de Cell
4. **Autonomía**: cada Cell contiene todos los componentes necesarios

```yaml
# Cell-based Namespace Configuration Example
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
    region: us-west-2
---
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
    region: us-west-2
```

</details>

### 5. ¿Qué significa "Steady State Hypothesis" en Chaos Engineering?

A. Mantener el sistema siempre en estado detenido
B. Una línea base medible para verificar el comportamiento normal del sistema antes y después de los experimentos
C. Condiciones para detener experimentos de caos
D. Estado de carga máxima del sistema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Una línea base medible para verificar el comportamiento normal del sistema antes y después de los experimentos**

**Explicación:**
Steady State Hypothesis define métricas medibles para el estado "normal" del sistema. Antes de un experimento de caos, verifica que esta hipótesis sea verdadera y, después del experimento, verifica que el sistema vuelva a este estado.

**Ejemplos de métricas de Steady State:**
- Tiempo de respuesta < 200ms (p99)
- Tasa de errores < 0.1%
- Throughput > 1000 req/s
- Disponibilidad de Pods > 99%

```yaml
# Litmus Chaos Experiment Definition Example
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosExperiment
metadata:
  name: pod-delete
spec:
  definition:
    steadyState:
      metrics:
        - name: response_time_p99
          threshold: 200
          comparison: lessThan
        - name: error_rate
          threshold: 0.1
          comparison: lessThan
```

</details>

### 6. ¿Qué anotación de Service se usa para implementar Zone-Aware Routing en EKS?

A. `service.kubernetes.io/topology-aware-hints: auto`
B. `service.kubernetes.io/zone-routing: enabled`
C. `service.kubernetes.io/local-only: true`
D. `service.kubernetes.io/cross-zone: disabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. `service.kubernetes.io/topology-aware-hints: auto`**

**Explicación:**
Topology Aware Hints, introducido en Kubernetes 1.23+, permite que kube-proxy enrute preferentemente el tráfico a endpoints en la misma Zone, lo que reduce los costos de tráfico entre AZs y la latencia.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-service
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

**Beneficios de Zone-Aware Routing:**
- Menores costos de transferencia de datos entre AZs
- Menor latencia de red
- Mayor confiabilidad al mantener el tráfico dentro de la misma Zone

</details>

### 7. Con `maxUnavailable: 25%` en un PDB y 8 réplicas, ¿cuál es la cantidad máxima de Pods que pueden interrumpirse simultáneamente?

A. 1
B. 2
C. 3
D. 4

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. 2**

**Explicación:**
`maxUnavailable: 25%` significa que hasta el 25% del total de réplicas puede interrumpirse simultáneamente. El 25% de 8 es 2 (8 × 0.25 = 2).

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  maxUnavailable: 25%  # 2 out of 8 can be disrupted
  selector:
    matchLabels:
      app: web-app
```

**Método de cálculo:**
- Los porcentajes se redondean hacia abajo
- replicas = 8, maxUnavailable = 25%
- 8 × 0.25 = 2 (decimal truncado)
- Por lo tanto, al menos 6 Pods deben permanecer siempre en ejecución

</details>

### 8. ¿Cuál NO es un tipo de experimento proporcionado por Litmus Chaos?

A. pod-delete
B. node-drain
C. network-loss
D. cluster-delete

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. cluster-delete**

**Explicación:**
Litmus Chaos no proporciona un experimento para eliminar un clúster completo. El propósito de Chaos Engineering es probar la resiliencia del sistema en entornos controlados, no destruir infraestructura completa.

**Tipos principales de experimentos de Litmus Chaos:**
- **Nivel de Pod**: pod-delete, pod-cpu-hog, pod-memory-hog, pod-network-loss
- **Nivel de nodo**: node-drain, node-cpu-hog, node-memory-hog, node-taint
- **Nivel de red**: network-loss, network-latency, network-corruption
- **Específicos de AWS**: ec2-terminate, ebs-loss, az-chaos

```bash
# Litmus Chaos Installation
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml
```

</details>

### 9. ¿Cómo se garantiza la alta disponibilidad del EKS Control Plane?

A. Los usuarios deben configurar Multi-AZ manualmente
B. AWS lo administra automáticamente en múltiples AZs
C. Se ejecuta solo en una sola AZ
D. Se requiere configuración manual de failover

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. AWS lo administra automáticamente en múltiples AZs**

**Explicación:**
Amazon EKS Control Plane es completamente administrado por AWS y se implementa automáticamente con alta disponibilidad en múltiples Availability Zones. Los datos de etcd también se replican en múltiples AZs.

**Características de HA del EKS Control Plane:**
- Implementación Multi-AZ automática (mínimo 2 AZs)
- Escalado automático del API server
- Replicación y backup automáticos de datos de etcd
- Detección y recuperación automáticas de fallas
- Garantía de SLA del 99.95%

**Responsabilidad del usuario:**
- Configuración Multi-AZ del data plane (nodo)
- Distribución de Pods de carga de trabajo
- Configuración de PDB y Topology Spread

</details>

### 10. ¿Qué significa `maxSkew` en Topology Spread Constraints?

A. Cantidad máxima de Pods
B. Diferencia máxima permitida en el conteo de Pods entre dominios de topología
C. Cantidad mínima de nodos
D. Máximo de Pods por nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Diferencia máxima permitida en el conteo de Pods entre dominios de topología**

**Explicación:**
`maxSkew` es la diferencia máxima permitida en el conteo de Pods entre distintos dominios de topología (por ejemplo, AZs, nodos). Por ejemplo, con `maxSkew: 1`, la diferencia en el conteo de Pods entre dos dominios cualesquiera no puede superar 1.

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1  # Maximum 1 Pod difference between domains
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

**Ejemplos de maxSkew (replicas=6, 3 AZs):**
- maxSkew=1: Zone-A(2), Zone-B(2), Zone-C(2) - Distribución uniforme
- maxSkew=2: Zone-A(3), Zone-B(2), Zone-C(1) - Permitido
- Infracción de maxSkew=1: Zone-A(4), Zone-B(1), Zone-C(1) - Programación rechazada

</details>

## Preguntas de respuesta corta

### 1. ¿Qué anotación de Service se usa para reducir los costos de transferencia de datos entre AZs en EKS?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** `service.kubernetes.io/topology-aware-hints: auto`

**Explicación:**
Agregar esta anotación a un Service habilita Kubernetes Topology Aware Hints, que enruta preferentemente el tráfico a endpoints dentro de la misma AZ.

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
```

</details>

### 2. Enumera 3 ejemplos de "Voluntary Disruption" en PodDisruptionBudget.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
1. Node drain (kubectl drain)
2. Actualización de clúster
3. Reducción de nodos por Cluster Autoscaler

**Ejemplos adicionales:**
- Actualizaciones rolling de Deployment/StatefulSet
- Eliminación manual de Pods (kubectl delete pod)
- Node cordon/drain para mantenimiento

**Ejemplos de Involuntary Disruption:**
- Falla de hardware
- Kernel panic
- Eliminación de VM
- OOM Kill

</details>

### 3. Enumera los 4 principios centrales de Chaos Engineering.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**
1. **Construir una Steady State Hypothesis**: definir métricas medibles para el estado normal
2. **Variar eventos del mundo real**: simular escenarios de falla del mundo real
3. **Ejecutar experimentos en producción**: probar en entornos reales cuando sea posible
4. **Minimizar el blast radius**: limitar el impacto del experimento y establecer condiciones automáticas de cancelación

**Principios adicionales:**
- Automatizar experimentos para verificación continua
- Analizar resultados y mejorar el sistema

</details>

### 4. ¿Cuál es la cantidad mínima recomendada de AZs al configurar node groups de EKS para Multi-AZ?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** 3

**Explicación:**
Distribuir nodos en 3 o más AZs proporciona:
- 2/3 de la capacidad mantenida durante una falla de una sola AZ
- Estabilidad para sistemas basados en quórum (por ejemplo, etcd)
- Distribución más uniforme de la carga de trabajo

```yaml
# eksctl Multi-AZ Node Group Configuration
nodeGroups:
  - name: ng-multi-az
    availabilityZones:
      - us-west-2a
      - us-west-2b
      - us-west-2c
    desiredCapacity: 6
```

</details>

### 5. ¿Cómo se enruta el tráfico a una Cell específica en Cell-Based Architecture?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** La capa de enrutamiento (por ejemplo, API Gateway, Service Mesh, Load Balancer) distribuye el tráfico a Cells específicas según el ID de usuario/tenant.

**Métodos de implementación:**
1. **Enrutamiento basado en hash**: aplicar hash al ID de usuario para determinar la Cell
2. **Mapeo explícito**: mantener una tabla de mapeo de usuario a Cell
3. **Basado en región**: asignar la Cell según la ubicación geográfica

```yaml
# Cell Routing Example with Istio VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: cell-router
spec:
  http:
  - match:
    - headers:
        x-cell-id:
          exact: "cell-a"
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: "cell-b"
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## Ejercicios prácticos

### 1. Escribe un YAML de PodDisruptionBudget que satisfaga los siguientes requisitos:
- Nombre: api-server-pdb
- Objetivo: Pods con la etiqueta `app: api-server`
- Deben permanecer siempre en ejecución al menos 3 Pods

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```

**Comandos de verificación:**
```bash
# Create PDB
kubectl apply -f api-server-pdb.yaml

# Check PDB status
kubectl get pdb api-server-pdb

# View detailed information
kubectl describe pdb api-server-pdb
```

**Salida esperada:**
```
NAME              MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
api-server-pdb    3               N/A               2                     10s
```

</details>

### 2. Escribe un Deployment con Topology Spread Constraints para distribuir Pods uniformemente en 3 AZs.
- Nombre de Deployment: web-frontend
- replicas: 6
- maxSkew: 1
- Clave de distribución: topology.kubernetes.io/zone

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
      containers:
      - name: web
        image: nginx:latest
        ports:
        - containerPort: 80
```

**Comandos de verificación:**
```bash
# Create Deployment
kubectl apply -f web-frontend.yaml

# Check Pod distribution
kubectl get pods -l app=web-frontend -o wide

# Check Pod count per Zone
kubectl get pods -l app=web-frontend -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | \
  xargs -I {} kubectl get node {} -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}{"\n"}' | \
  sort | uniq -c
```

**Salida esperada:**
```
2 us-west-2a
2 us-west-2b
2 us-west-2c
```

</details>

### 3. Define un experimento de Chaos usando Litmus Chaos para eliminar Pods específicos.
- Objetivo: Pods en el namespace `production` con la etiqueta `app: payment-service`
- Duración del experimento: 30 segundos
- Cantidad de Pods a eliminar: 1

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: app=payment-service
    appkind: deployment
  engineState: active
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
        - name: PODS_AFFECTED_PERC
          value: "100"
        - name: TARGET_PODS
          value: ""
        - name: FORCE
          value: "false"
```

**Prerrequisitos:**
```bash
# Install Litmus Chaos Operator
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml

# Install ChaosExperiment CRD
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/experiment.yaml

# Create ServiceAccount
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/rbac.yaml -n production
```

**Comandos de verificación:**
```bash
# Run Chaos experiment
kubectl apply -f payment-pod-delete.yaml

# Check experiment status
kubectl get chaosengine payment-pod-delete -n production

# Check experiment results
kubectl get chaosresult payment-pod-delete-pod-delete -n production -o yaml
```

</details>

## Preguntas avanzadas

### 1. Diseña una arquitectura para lograr una disponibilidad del 99.99% para un clúster de EKS en una empresa de servicios financieros. Proporciona una estrategia integral utilizando Multi-AZ, Cell-Based Architecture, PDB y Chaos Engineering.

<details>
<summary>Mostrar respuesta</summary>

**Arquitectura integral para una disponibilidad del 99.99%:**

**1. Configuración Multi-Region + Multi-AZ:**
```yaml
# Primary Region (us-west-2)
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary
  region: us-west-2
nodeGroups:
  - name: ng-critical
    instanceType: m5.xlarge
    desiredCapacity: 9
    availabilityZones: ["us-west-2a", "us-west-2b", "us-west-2c"]
    labels:
      criticality: high
```

**2. Implementación de Cell-Based Architecture:**
```yaml
# Cell-level isolation
apiVersion: v1
kind: Namespace
metadata:
  name: cell-us-1
  labels:
    cell: us-1
    region: us-west-2
---
# Cell-specific resource quotas
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: cell-us-1
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    limits.cpu: "200"
    limits.memory: 400Gi
```

**3. Políticas PDB estrictas:**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
spec:
  minAvailable: 80%  # Always 80%+ available
  selector:
    matchLabels:
      tier: critical
```

**4. Topology Spread + Anti-Affinity:**
```yaml
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: payment-api
        topologyKey: kubernetes.io/hostname
```

**5. Programa de Chaos Engineering:**
```yaml
# Periodic Chaos experiments (GameDay)
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosSchedule
metadata:
  name: weekly-resilience-test
spec:
  schedule:
    type: repeat
    repeat:
      timeRange:
        startTime: "2024-01-01T02:00:00Z"
        endTime: "2024-12-31T04:00:00Z"
      workDays:
        includedDays: "Sun"
  engineSpec:
    experiments:
    - name: pod-delete
    - name: node-drain
    - name: network-loss
```

**6. Monitoreo y Auto-Recovery:**
```yaml
# HPA + Auto-recovery
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
spec:
  minReplicas: 6
  maxReplicas: 30
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

**Cálculo del SLA:**
- 99.99% = aproximadamente 52 minutos de downtime por año
- Multi-AZ: maneja fallas de una sola AZ
- Multi-Region: maneja fallas a nivel de región
- Aislamiento de Cells: limita el blast radius
- Auto-recovery: minimiza MTTR

</details>

### 2. Desarrolla una estrategia de resiliencia de EKS para una gran plataforma de e-commerce que se prepara para un aumento de tráfico de Black Friday (10x). Incluye pre-scaling, validación con Chaos Engineering y planes de respuesta ante escenarios de falla.

<details>
<summary>Mostrar respuesta</summary>

**Estrategia de preparación para el aumento de tráfico de Black Friday:**

**1. Planificación de capacidad de pre-scaling:**
```yaml
# Karpenter Provisioner - Surge Configuration
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: blackfriday
spec:
  requirements:
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["m5.2xlarge", "m5.4xlarge", "c5.2xlarge", "c5.4xlarge"]
  - key: topology.kubernetes.io/zone
    operator: In
    values: ["us-west-2a", "us-west-2b", "us-west-2c"]
  limits:
    resources:
      cpu: 2000
      memory: 4000Gi
  ttlSecondsAfterEmpty: 30
---
# HPA Pre-scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50  # Normal 10 -> Black Friday 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60  # Conservative 60%
```

**2. Validación previa al tráfico con Chaos Engineering:**
```yaml
# Load Test + Chaos Combination
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: blackfriday-prep-test
spec:
  experiments:
  # Scenario 1: 10x traffic + 30% Pod failure
  - name: pod-delete
    spec:
      components:
        env:
        - name: PODS_AFFECTED_PERC
          value: "30"
        - name: TOTAL_CHAOS_DURATION
          value: "300"
  # Scenario 2: 10x traffic + AZ failure
  - name: node-drain
    spec:
      components:
        env:
        - name: TARGET_NODE_LABEL
          value: "topology.kubernetes.io/zone=us-west-2a"
  # Scenario 3: 10x traffic + DB latency
  - name: pod-network-latency
    spec:
      components:
        env:
        - name: TARGET_PODS
          value: "app=mysql"
        - name: NETWORK_LATENCY
          value: "500"
```

**3. Planes de respuesta ante escenarios de falla:**

| Escenario | Detección | Respuesta automática | Respuesta manual |
|---------|------|----------|----------|
| Falla de AZ | CloudWatch Alarm | Redistribución automática mediante Topology Spread | Route53 Failover |
| Latencia de DB | Alerta de latencia | Activación de Circuit Breaker | Cambiar a Read Replica |
| Agotamiento de memoria | Alerta OOM | Scale-out de HPA | Agregar nodos |
| Pico de tráfico | Alerta TPS | Rate Limiting | Ampliar caché de CDN |

**4. Patrón Circuit Breaker:**
```yaml
# Istio DestinationRule - Circuit Breaker
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: product-catalog-cb
spec:
  host: product-catalog
  trafficPolicy:
    connectionPool:
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**5. Dashboard de monitoreo en tiempo real:**
```promql
# Grafana Dashboard Queries
# 1. Total TPS
sum(rate(http_requests_total[1m]))

# 2. Error Rate
sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m])) * 100

# 3. P99 Response Time
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))

# 4. Pod Availability Rate
sum(kube_pod_status_ready{condition="true"}) / sum(kube_pod_status_ready) * 100
```

**6. Plan de rollback:**
```bash
#!/bin/bash
# Emergency Rollback Script
NAMESPACE="production"
DEPLOYMENT="product-catalog"

# 1. Rollback to previous version
kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE

# 2. Pause HPA
kubectl patch hpa $DEPLOYMENT-hpa -n $NAMESPACE -p '{"spec":{"minReplicas":100}}'

# 3. Disable Feature Flags
curl -X POST "https://feature-flags.internal/api/v1/flags/blackfriday-features/disable"

# 4. Extend CDN Cache
aws cloudfront update-distribution --id $CF_DIST_ID --default-cache-behavior "DefaultTTL=86400"
```

**Cronograma de pruebas:**
- D-14: pruebas básicas de Chaos
- D-7: GameDay de escenario completo
- D-3: verificación final y pre-scaling
- D-Day: monitoreo y respuesta en tiempo real

</details>
