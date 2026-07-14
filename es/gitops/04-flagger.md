# Entrega progresiva con Flagger

> **Versiones compatibles**: Flagger v1.38+, Flux v2.4+
> **Última actualización**: June 2025

Flagger es un operador de entrega progresiva para Kubernetes que automatiza la promoción de despliegues Canary mediante enrutamiento de service mesh, controladores de ingress o Gateway API para el desplazamiento de tráfico y métricas de Prometheus para el análisis Canary. Creado originalmente por Weaveworks y ahora un proyecto de CNCF dentro de la familia Flux, Flagger reduce el riesgo de introducir nuevas versiones de software en producción al desplazar gradualmente el tráfico a una versión nueva mientras mide indicadores clave de rendimiento y revierte automáticamente si se detectan anomalías.

## Tabla de contenidos

- [Descripción general y objetivos de aprendizaje](#overview-and-learning-objectives)
- [Arquitectura de Flagger](#flagger-architecture)
- [Instalación y configuración de EKS](#eks-installation-and-configuration)
- [Estrategia de despliegue Canary](#canary-deployment-strategy)
- [Estrategia de despliegue Blue-Green](#blue-green-deployment-strategy)
- [Estrategia de pruebas A/B](#ab-testing-strategy)
- [Métricas personalizadas y webhooks](#custom-metrics-and-webhooks)
- [Integración de GitOps (Flux + Flagger)](#gitops-integration-flux--flagger)
- [Observabilidad y alertas](#observability-and-alerting)
- [Prácticas recomendadas para producción](#production-best-practices)
- [Referencias](#references)

---

## Descripción general y objetivos de aprendizaje

### Objetivos de aprendizaje

Después de completar este documento, podrá:

1. Explicar las estrategias de entrega progresiva (Canary, Blue-Green, pruebas A/B) y cuándo usar cada una
2. Implementar y configurar Flagger en Amazon EKS con varios proveedores de mesh e ingress
3. Definir recursos Canary con análisis de métricas personalizadas y condiciones de reversión automática
4. Implementar despliegues Blue-Green con duplicación de tráfico y aprobación manual
5. Configurar pruebas A/B con enrutamiento basado en encabezados y cookies
6. Integrar Flagger con FluxCD para pipelines de entrega progresiva GitOps totalmente automatizados
7. Configurar paneles de observabilidad y alertas para despliegues de Flagger

### ¿Qué es la entrega progresiva?

La entrega progresiva es un término general para estrategias de despliegue avanzadas que permiten una implementación controlada y gradual de cambios para un subconjunto de usuarios antes de ponerlos a disposición de toda la base de usuarios. A diferencia de las actualizaciones rolling tradicionales que reemplazan todos los pods simultáneamente, la entrega progresiva proporciona control detallado sobre la distribución del tráfico, análisis en tiempo real y reversión automática.

Las tres estrategias principales de entrega progresiva son:

| Estrategia | Control de tráfico | Caso de uso | Complejidad |
|----------|----------------|----------|------------|
| **Canary** | Desplazamiento de peso basado en porcentaje | Implementación gradual de propósito general | Media |
| **Blue-Green** | Cambio completo entre dos entornos | Sin tiempo de inactividad, reversión instantánea | Baja |
| **Pruebas A/B** | Enrutamiento basado en encabezados/cookies | Pruebas de funcionalidades con segmentos de usuarios específicos | Alta |

### Flagger frente a Argo Rollouts

Tanto Flagger como Argo Rollouts resuelven el problema de la entrega progresiva para Kubernetes, pero adoptan enfoques fundamentalmente distintos:

| Característica | Flagger | Argo Rollouts |
|---------|---------|---------------|
| **Ecosistema** | Flux / CNCF | Argo / CNCF |
| **Modelo de recursos** | Envuelve Deployment/DaemonSet nativos | Reemplaza Deployment por Rollout CRD |
| **Proveedores de tráfico** | Istio, Linkerd, Contour, Nginx, Gateway API, AWS App Mesh, Gloo, Traefik | Istio, Nginx, ALB, SMI, Gateway API |
| **Análisis de métricas** | Prometheus, Datadog, CloudWatch y webhooks personalizados integrados | AnalysisTemplate integrado con varios proveedores |
| **Integración de GitOps** | Integración nativa de Flux | Integración nativa de Argo CD |
| **Compatibilidad con webhooks** | Pre/post-rollout, rollout, confirm-rollout, load-test | Análisis pre/post, anti-affinity |
| **Blue-Green** | Compatible mediante Canary CRD | Estrategia Rollout de primera clase |
| **Pruebas A/B** | Compatible mediante Canary CRD con encabezados | Compatible mediante Experiment CRD |
| **Estado de CNCF** | Incubación (familia Flux) | Graduado (familia Argo) |
| **Patrón de adopción** | Aditivo (sin cambios en Deployment) | Sustitución (Rollout reemplaza Deployment) |

**Diferenciador clave**: Flagger no requiere que cambie sus recursos Deployment existentes. Crea automáticamente variantes CloneSet primary y Canary, y administra el desplazamiento de tráfico a través de la capa mesh/ingress. Argo Rollouts requiere reemplazar su tipo `Deployment` por un tipo `Rollout`.

### Flagger en el ecosistema Flux

Flagger está diseñado como el componente de entrega progresiva del conjunto de herramientas GitOps de Flux:

```mermaid
graph TB
    subgraph "Flux GitOps Toolkit"
        SC["Source Controller<br/>(Git, Helm, OCI)"]
        KC["Kustomize Controller"]
        HC["Helm Controller"]
        NC["Notification Controller"]
        IAC["Image Automation<br/>Controller"]
        FL["Flagger<br/>(Progressive Delivery)"]
    end

    subgraph "External Systems"
        GIT[("Git Repository")]
        PROM["Prometheus"]
        MESH["Service Mesh /<br/>Ingress Controller"]
    end

    subgraph "Kubernetes Cluster"
        DEP["Deployments"]
        SVC["Services"]
        VS["VirtualServices /<br/>HTTPRoutes"]
    end

    GIT --> SC
    SC --> KC
    SC --> HC
    KC --> DEP
    HC --> DEP
    IAC --> GIT

    FL -->|"Watches"| DEP
    FL -->|"Queries"| PROM
    FL -->|"Manages"| SVC
    FL -->|"Manages"| VS
    NC -->|"Alerts"| FL

    classDef flux fill:#5468FF,stroke:#333,color:white
    classDef ext fill:#FF9900,stroke:#333,color:white
    classDef k8s fill:#326CE5,stroke:#333,color:white

    class SC,KC,HC,NC,IAC,FL flux
    class GIT,PROM,MESH ext
    class DEP,SVC,VS k8s
```

---

## Arquitectura de Flagger

### Bucle de control

Flagger implementa un bucle de control que avanza progresivamente una nueva versión de una aplicación analizando métricas, ejecutando pruebas de conformidad y administrando el enrutamiento de tráfico. El bucle principal de reconciliación es:

```mermaid
stateDiagram-v2
    [*] --> Initialized: Canary created
    Initialized --> Progressing: Deployment change detected
    Progressing --> WaitingPromotion: All steps passed
    Progressing --> Progressing: Advance step<br/>(increase weight)
    Progressing --> Failed: Metrics check failed<br/>or threshold exceeded
    WaitingPromotion --> Promoting: Auto or manual gate
    WaitingPromotion --> Failed: Timeout exceeded
    Promoting --> Finalising: Traffic shifted to primary
    Finalising --> Succeeded: Primary updated, canary scaled down
    Failed --> Initialized: Rollback complete
    Succeeded --> Initialized: Waiting for next change
```

### Pasos detallados del bucle de control

Cuando se detecta un cambio en la carga de trabajo objetivo (por ejemplo, una nueva imagen de contenedor), Flagger ejecuta la siguiente secuencia:

1. **Detectar cambio**: Flagger observa el Deployment objetivo para detectar cambios de spec (etiqueta de imagen, variables de entorno, recursos, etc.)
2. **Inicializar Canary**: Escala el Deployment Canary con la nueva versión; el primary conserva la versión anterior
3. **Ejecutar webhooks pre-rollout**: Ejecuta pruebas de conformidad, smoke tests u otras precondiciones
4. **Desplazar tráfico**: Aumenta incrementalmente el peso del tráfico Canary según `stepWeight` y `maxWeight`
5. **Analizar métricas**: Consulta Prometheus (u otros proveedores) para obtener tasa de éxito, latencia y métricas personalizadas
6. **Avanzar o revertir**: Si las métricas superan los umbrales, avanza al siguiente paso; de lo contrario inicia la reversión
7. **Confirmar promoción**: Opcionalmente espera la aprobación de aprobación manual mediante webhook
8. **Promover**: Copia el spec Canary al primary, reduce el Canary y enruta todo el tráfico al primary
9. **Enviar notificaciones**: Alerta mediante Slack, Teams u otros proveedores configurados

### Compatibilidad con proveedores de mesh e ingress

Flagger admite una amplia variedad de proveedores de administración de tráfico, cada uno con capacidades diferentes:

| Proveedor | Canary | Blue-Green | Pruebas A/B | Duplicación | Gateway API |
|----------|--------|------------|-------------|-----------|-------------|
| **Istio** | Sí | Sí | Sí | Sí | Sí |
| **Linkerd** | Sí | Sí | No | No | Sí |
| **AWS App Mesh** | Sí | Sí | No | No | No |
| **Contour** | Sí | Sí | Sí | No | Sí |
| **Nginx Ingress** | Sí | Sí | Sí | No | No |
| **Gloo Edge** | Sí | Sí | No | No | No |
| **Traefik** | Sí | Sí | No | No | No |
| **Gateway API** | Sí | Sí | Sí | No | Sí |
| **Kuma** | Sí | Sí | No | No | No |
| **Open Service Mesh** | Sí | Sí | No | No | No |

### Análisis de métricas de Prometheus

El motor de análisis de métricas de Flagger consulta Prometheus para evaluar si una versión Canary es saludable. Las dos métricas integradas son:

- **request-success-rate**: El porcentaje de solicitudes HTTP correctas (no 5xx) durante el intervalo de análisis
- **request-duration**: La latencia P99 de las solicitudes HTTP durante el intervalo de análisis

Ambas métricas se derivan de las métricas de Prometheus del service mesh o controlador de ingress (por ejemplo, `istio_requests_total`, `istio_request_duration_milliseconds_bucket`).

```mermaid
sequenceDiagram
    participant F as Flagger
    participant P as Prometheus
    participant M as Mesh/Ingress
    participant C as Canary Pod

    F->>M: Set canary weight (e.g., 10%)
    M->>C: Route 10% traffic to canary
    Note over C: Handle requests
    C->>M: Return responses
    M->>P: Report metrics<br/>(latency, status codes)
    F->>P: Query: request-success-rate?
    P-->>F: 99.5% (threshold: 99%)
    F->>P: Query: request-duration P99?
    P-->>F: 250ms (threshold: 500ms)
    F->>F: All checks passed
    F->>M: Advance: set weight to 20%
```

---

## Instalación y configuración de EKS

### Requisitos previos

Antes de instalar Flagger en Amazon EKS, asegúrese de que se cumplan los siguientes requisitos previos:

- Un clúster de Amazon EKS que ejecute Kubernetes v1.27+
- Helm v3.12+ instalado
- Un service mesh (Istio) o controlador de ingress (Nginx, Contour) implementado
- Stack de Prometheus implementado (se recomienda kube-prometheus-stack)
- FluxCD v2.4+ inicializado (para la integración de GitOps)

### Instalación con Helm y Prometheus

Instale Flagger usando Helm con el servidor de métricas de Prometheus habilitado:

```bash
# Add Flagger Helm repository
helm repo add flagger https://flagger.app
helm repo update

# Install Flagger with Prometheus metrics server
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --create-namespace \
  --set meshProvider=istio \
  --set metricsServer=http://prometheus-kube-prometheus-prometheus.monitoring:9090 \
  --set prometheus.install=true
```

Para EKS con IRSA (IAM Roles for Service Accounts), configure la service account:

```yaml
# flagger-values.yaml
meshProvider: istio
metricsServer: http://prometheus-kube-prometheus-prometheus.monitoring:9090

serviceAccount:
  create: true
  name: flagger
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/FlaggerRole

prometheus:
  install: true
  retention: 2h

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 1000m
    memory: 512Mi

# Enable leader election for HA
leaderElection:
  enabled: true
  replicaCount: 2
```

```bash
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --create-namespace \
  -f flagger-values.yaml
```

### Instalar Flagger loadtester

El loadtester de Flagger es una herramienta complementaria para ejecutar pruebas de carga y webhooks automatizados durante el análisis Canary:

```bash
helm upgrade -i flagger-loadtester flagger/loadtester \
  --namespace flagger-system \
  --set cmd.timeout=1h \
  --set resources.requests.cpu=100m \
  --set resources.requests.memory=64Mi
```

### Configuración del proveedor Istio

Al utilizar Istio como proveedor de mesh, Flagger administra automáticamente los recursos VirtualService y DestinationRule:

```yaml
# flagger-values-istio.yaml
meshProvider: istio
metricsServer: http://prometheus-kube-prometheus-prometheus.monitoring:9090

# Istio-specific settings
istio:
  # The Istio ingress gateway name
  gateway: istio-system/public-gateway

# Namespace selector for Flagger to watch
namespace: ""  # Empty means all namespaces

# Log level
logLevel: info
```

Verifique que la inyección de sidecar de Istio esté habilitada para el namespace objetivo:

```bash
kubectl label namespace production istio-injection=enabled
kubectl get namespace production --show-labels
```

### Configuración del proveedor Gateway API

Flagger admite Kubernetes Gateway API como proveedor, lo que permite la entrega progresiva sin un service mesh completo:

```yaml
# flagger-values-gatewayapi.yaml
meshProvider: gatewayapi
metricsServer: http://prometheus-kube-prometheus-prometheus.monitoring:9090

# Gateway API specific configuration
gatewayApi:
  # Reference to the Gateway resource
  gateway: istio-system/main-gateway
```

```bash
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --create-namespace \
  -f flagger-values-gatewayapi.yaml
```

Cree el recurso Gateway que Flagger referenciará:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: istio-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    port: 80
    protocol: HTTP
    allowedRoutes:
      namespaces:
        from: All
  - name: https
    port: 443
    protocol: HTTPS
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-secret
    allowedRoutes:
      namespaces:
        from: All
```

### Configuración de notificaciones de Slack y Teams

Flagger puede enviar notificaciones de despliegue a Slack, Microsoft Teams y otros proveedores mediante el AlertProvider CRD:

```yaml
# Slack AlertProvider
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: slack
  namespace: production
spec:
  type: slack
  channel: deployments
  username: flagger
  # Webhook URL stored in a Kubernetes Secret
  secretRef:
    name: slack-webhook
---
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook
  namespace: production
stringData:
  address: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

```yaml
# Microsoft Teams AlertProvider
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: msteams
  namespace: production
spec:
  type: msteams
  secretRef:
    name: msteams-webhook
---
apiVersion: v1
kind: Secret
metadata:
  name: msteams-webhook
  namespace: production
stringData:
  address: https://outlook.office.com/webhook/XXXXXXXX
```

Se pueden referenciar varios proveedores de alertas en un recurso Canary:

```yaml
spec:
  analysis:
    alerts:
    - name: "slack-notification"
      severity: info
      providerRef:
        name: slack
        namespace: production
    - name: "teams-notification"
      severity: error
      providerRef:
        name: msteams
        namespace: production
```

---

## Estrategia de despliegue Canary

### Explicación detallada de Canary CRD

El Canary CRD es el recurso principal de Flagger para definir estrategias de entrega progresiva. Hace referencia a un Deployment objetivo y especifica cómo se debe desplazar el tráfico, qué métricas se deben analizar y cuándo se debe revertir.

**Estructura principal del recurso Canary:**

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: app-name
  namespace: production
spec:
  # ---- Target Reference ----
  targetRef:              # The Deployment to manage
  autoscalerRef:          # Optional HPA/KEDA reference
  ingressRef:             # Optional Ingress reference
  
  # ---- Service Configuration ----
  service:                # Service mesh / ingress settings
  
  # ---- Analysis Configuration ----
  analysis:               # Metrics, webhooks, alerts
  
  # ---- Promotion Policy ----
  progressDeadlineSeconds: 600
  skipAnalysis: false
```

### Desplazamiento de tráfico paso a paso

Flagger administra el desplazamiento del tráfico Canary mediante dos parámetros clave:

- **`stepWeight`**: El porcentaje de tráfico que se agrega al Canary en cada intervalo de análisis
- **`maxWeight`**: El porcentaje máximo de tráfico que recibe el Canary antes de la promoción

Por ejemplo, con `stepWeight: 10` y `maxWeight: 50`:

```
Step 1: Canary 10%, Primary 90%  ->  Analyze metrics
Step 2: Canary 20%, Primary 80%  ->  Analyze metrics
Step 3: Canary 30%, Primary 70%  ->  Analyze metrics
Step 4: Canary 40%, Primary 60%  ->  Analyze metrics
Step 5: Canary 50%, Primary 50%  ->  Analyze metrics
Step 6: Promote -> Canary spec copied to Primary, all traffic to Primary
```

```mermaid
graph LR
    subgraph "Traffic Shifting Progress"
        S1["Step 1<br/>10%"] --> S2["Step 2<br/>20%"]
        S2 --> S3["Step 3<br/>30%"]
        S3 --> S4["Step 4<br/>40%"]
        S4 --> S5["Step 5<br/>50%"]
        S5 --> PROMOTE["Promote<br/>100%"]
    end

    subgraph "At Each Step"
        METRIC1["Check: request-success-rate<br/>>= 99%"]
        METRIC2["Check: request-duration P99<br/><= 500ms"]
        WH["Run: webhooks<br/>(load test, conformance)"]
    end

    S3 -.->|"Analyze"| METRIC1
    S3 -.->|"Analyze"| METRIC2
    S3 -.->|"Execute"| WH

    classDef step fill:#28a745,stroke:#333,color:white
    classDef check fill:#ffc107,stroke:#333,color:black
    classDef promote fill:#5468FF,stroke:#333,color:white

    class S1,S2,S3,S4,S5 step
    class METRIC1,METRIC2,WH check
    class PROMOTE promote
```

También puede definir incrementos de tráfico no lineales con `stepWeights` (un array):

```yaml
analysis:
  stepWeights: [1, 2, 5, 10, 25, 50, 80]
  # Traffic progression: 1% -> 2% -> 5% -> 10% -> 25% -> 50% -> 80% -> promote
```

### Análisis de métricas

Las métricas integradas de Flagger se basan en que el service mesh o controlador de ingress exponga métricas de Prometheus:

```yaml
analysis:
  metrics:
  # Built-in metric: request success rate
  - name: request-success-rate
    # Minimum percentage of successful (non-5xx) requests
    thresholdRange:
      min: 99
    interval: 1m

  # Built-in metric: request duration (latency)
  - name: request-duration
    # Maximum P99 latency in milliseconds
    thresholdRange:
      max: 500
    interval: 1m
```

El campo `interval` determina con qué frecuencia Flagger consulta Prometheus durante cada paso de análisis. `thresholdRange` especifica los límites aceptables:

- `min`: El valor de la métrica debe ser **mayor o igual** que este valor (por ejemplo, tasa de éxito >= 99%)
- `max`: El valor de la métrica debe ser **menor o igual** que este valor (por ejemplo, latencia <= 500ms)

### Condiciones de reversión automática

Flagger revierte automáticamente un despliegue Canary cuando:

1. **Se excede el umbral de fallo de métricas**: Una comprobación de métrica falla más veces que `threshold` dentro de un paso de análisis
2. **Se excede el plazo de progreso**: El Canary no progresa dentro de `progressDeadlineSeconds`
3. **Fallo de webhook**: Un webhook pre-rollout o rollout devuelve un estado distinto de 2xx

```yaml
analysis:
  # Number of consecutive metric check failures before rollback
  threshold: 5
  
  # Maximum number of failed metric checks before rollback
  # (across all steps, not just consecutive)
  maxWeight: 50
  
  # Analysis interval
  interval: 1m
  
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 99
    interval: 1m
  - name: request-duration
    thresholdRange:
      max: 500
    interval: 1m
```

Cuando ocurre una reversión, Flagger:
1. Enruta todo el tráfico de vuelta al primary (versión anterior)
2. Reduce el Canary a cero
3. Establece el estado Canary en `Failed`
4. Envía notificaciones de alerta

### Ejemplo completo de YAML Canary

El siguiente es un recurso Canary listo para producción para una aplicación web implementada en EKS con Istio:

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  # Reference to the target Deployment
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app

  # Reference to the HPA (optional, Flagger will manage scaling)
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: web-app

  # Maximum time in seconds for the canary to progress
  progressDeadlineSeconds: 600

  service:
    # Container port
    port: 8080
    # Port name (must match Istio conventions)
    portName: http
    # Target port on the container
    targetPort: 8080
    # Istio gateway references
    gateways:
    - istio-system/public-gateway
    # Hostnames
    hosts:
    - app.example.com
    # Istio traffic policy
    trafficPolicy:
      tls:
        mode: ISTIO_MUTUAL
    # Retries
    retries:
      attempts: 3
      perTryTimeout: 1s
      retryOn: "gateway-error,connect-failure,refused-stream"

  analysis:
    # Analysis interval
    interval: 1m
    # Number of analysis cycles before promotion
    iterations: 10
    # Max traffic weight shifted to canary
    maxWeight: 50
    # Traffic weight step
    stepWeight: 10
    # Number of failed checks before rollback
    threshold: 5

    # Prometheus metrics
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m

    # Webhooks for load testing and conformance
    webhooks:
    - name: smoke-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: bash
        cmd: "curl -sd 'test' http://web-app-canary.production:8080/healthz | grep ok"

    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"

    # Alert providers
    alerts:
    - name: "slack"
      severity: info
      providerRef:
        name: slack
        namespace: production
```

Este recurso Canary:
1. Observa cambios en el Deployment `web-app`
2. Crea Deployments `web-app-primary` y `web-app-canary`
3. Crea Services ClusterIP `web-app`, `web-app-primary` y `web-app-canary`
4. Crea un VirtualService de Istio para el enrutamiento de tráfico
5. Ejecuta un smoke test antes de iniciar el rollout
6. Desplaza el tráfico un 10% cada vez hasta el 50%
7. Ejecuta pruebas de carga durante cada paso de análisis
8. Comprueba la tasa de éxito de solicitudes (>= 99%) y la latencia P99 (<= 500ms)
9. Revierte si fallan 5 comprobaciones consecutivas de métricas
10. Promueve copiando el spec Canary al primary después de que todos los pasos se superen

**Supervisar un despliegue Canary:**

```bash
# Watch Canary status
kubectl get canaries -n production -w

# Describe the Canary for detailed events
kubectl describe canary web-app -n production

# Check Flagger logs
kubectl logs -n flagger-system deploy/flagger -f | jq

# Trigger a canary deployment by updating the image
kubectl set image deployment/web-app web-app=myregistry/web-app:v2.0.0 -n production
```

---

## Estrategia de despliegue Blue-Green

### Blue-Green Canary CRD

Flagger admite despliegues Blue-Green mediante el mismo Canary CRD al omitir `stepWeight` y `maxWeight` y utilizar `iterations` para definir cuántos ciclos de análisis se ejecutan antes de cambiar el tráfico de la versión antigua (blue) a la nueva (green).

En el modo Blue-Green:
- El Canary no recibe tráfico en vivo durante el análisis (a menos que la duplicación esté habilitada)
- Flagger ejecuta comprobaciones de métricas contra el Canary usando el load tester o tráfico duplicado
- Después de que todas las iteraciones se superen, el tráfico se cambia 100% del primary al Canary en un solo paso
- Si falla alguna iteración, el Canary se reduce sin impacto en el tráfico de producción

```mermaid
sequenceDiagram
    participant U as Users
    participant P as Primary (Blue)
    participant C as Canary (Green)
    participant F as Flagger
    participant LT as Load Tester

    Note over P: Serving 100% traffic
    F->>C: Deploy new version (Green)
    F->>LT: Run pre-rollout tests
    LT->>C: Synthetic traffic
    LT-->>F: Tests passed

    loop Analysis Iterations
        F->>LT: Generate test traffic
        LT->>C: Synthetic requests
        F->>F: Check metrics (success rate, latency)
        Note over F: Iteration passed
    end

    F->>U: Switch: 100% traffic to Green
    F->>P: Update Primary with Green spec
    F->>C: Scale down canary
    Note over P: Now serving new version
```

### Duplicar tráfico

Al utilizar Istio, Flagger puede duplicar el tráfico de producción al Canary durante el análisis Blue-Green. El tráfico duplicado es de envío y olvido; la respuesta del Canary se descarta, lo que garantiza cero impacto en los usuarios:

```yaml
spec:
  analysis:
    # Number of analysis cycles
    iterations: 10
    # Enable traffic mirroring (Istio only)
    mirror: true
    # Percentage of traffic to mirror (default: 100)
    mirrorWeight: 100
```

### Aprobación manual

Para despliegues de alto riesgo, puede requerir aprobación manual antes de que Flagger promueva el Canary. Esto se logra mediante un webhook confirm-rollout que Flagger consulta en cada paso:

```yaml
spec:
  analysis:
    webhooks:
    - name: confirm-promotion
      type: confirm-promotion
      url: http://flagger-loadtester.flagger-system/gate/approve
```

Para aprobar o rechazar manualmente:

```bash
# Approve the promotion
kubectl exec -n flagger-system deploy/flagger-loadtester -- \
  wget --post-data='{}' -q -O- http://localhost:8080/gate/open/web-app.production

# Reject the promotion (close the gate)
kubectl exec -n flagger-system deploy/flagger-loadtester -- \
  wget --post-data='{}' -q -O- http://localhost:8080/gate/close/web-app.production

# Check gate status
kubectl exec -n flagger-system deploy/flagger-loadtester -- \
  wget -q -O- http://localhost:8080/gate/check/web-app.production
```

### Ejemplo completo de YAML Blue-Green

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app

  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: web-app

  progressDeadlineSeconds: 600

  service:
    port: 8080
    portName: http
    targetPort: 8080
    gateways:
    - istio-system/public-gateway
    hosts:
    - app.example.com

  analysis:
    # Blue-Green: use iterations, no stepWeight/maxWeight
    interval: 1m
    iterations: 10
    threshold: 2

    # Mirror production traffic to the canary (Istio only)
    mirror: true
    mirrorWeight: 100

    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m

    webhooks:
    # Pre-rollout conformance test
    - name: conformance-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 120s
      metadata:
        type: bash
        cmd: "curl -sd 'test' http://web-app-canary.production:8080/healthz | grep ok"

    # Load test for generating metrics
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"

    # Manual gate for production approval
    - name: confirm-promotion
      type: confirm-promotion
      url: http://flagger-loadtester.flagger-system/gate/approve

    alerts:
    - name: "slack"
      severity: info
      providerRef:
        name: slack
        namespace: production
```

---

## Estrategia de pruebas A/B

### Enrutamiento basado en encabezados y cookies

Las pruebas A/B en Flagger utilizan encabezados HTTP o cookies para enrutar usuarios específicos a la versión Canary. A diferencia de los despliegues Canary que utilizan enrutamiento ponderado, las pruebas A/B garantizan un enrutamiento determinista basado en atributos de la solicitud.

Esta estrategia es ideal para:
- Pruebas de feature flags con segmentos de usuarios específicos
- Rollouts regionales basados en encabezados de solicitudes
- Pruebas internas antes del lanzamiento público
- Medición de métricas de negocio (tasa de conversión, interacción) para cohortes de usuarios específicas

### Integración con Istio VirtualService

Al utilizar Istio, Flagger genera reglas VirtualService que coinciden con encabezados HTTP o cookies:

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app

  progressDeadlineSeconds: 600

  service:
    port: 8080
    portName: http
    targetPort: 8080
    gateways:
    - istio-system/public-gateway
    hosts:
    - app.example.com

  analysis:
    interval: 1m
    iterations: 20
    threshold: 5

    # A/B testing match conditions
    # Users matching ANY of these conditions see the canary
    match:
    # Route based on a custom header
    - headers:
        x-canary:
          exact: "insider"
    # Route based on a cookie value
    - headers:
        cookie:
          regex: "^(.*?;)?(canary=always)(;.*)?$"

    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m

    webhooks:
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 5 -c 2 -H 'x-canary: insider' http://web-app-canary.production:8080/"

    alerts:
    - name: "slack"
      severity: info
      providerRef:
        name: slack
        namespace: production
```

El Istio VirtualService resultante tendrá este aspecto:

```yaml
# Auto-generated by Flagger
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: web-app
  namespace: production
spec:
  gateways:
  - istio-system/public-gateway
  hosts:
  - app.example.com
  http:
  # A/B test route: matched users go to canary
  - match:
    - headers:
        x-canary:
          exact: "insider"
    - headers:
        cookie:
          regex: "^(.*?;)?(canary=always)(;.*)?$"
    route:
    - destination:
        host: web-app-canary
  # Default route: everyone else goes to primary
  - route:
    - destination:
        host: web-app-primary
```

### Promoción automática basada en métricas

Durante las pruebas A/B, Flagger aún realiza análisis de métricas sobre el tráfico Canary. Después de que el número configurado de `iterations` se supere con todas las métricas dentro de sus umbrales, Flagger promueve automáticamente el Canary:

```bash
# Test A/B routing with header
curl -H "x-canary: insider" http://app.example.com/

# Test A/B routing with cookie
curl -b "canary=always" http://app.example.com/

# Verify routing (should return the canary version)
for i in $(seq 1 10); do
  curl -s -H "x-canary: insider" http://app.example.com/version
done
```

---

## Métricas personalizadas y webhooks

### Consultas de métricas personalizadas de Prometheus

Además de las dos métricas integradas, Flagger admite consultas personalizadas de Prometheus mediante el MetricTemplate CRD. Esto le permite analizar cualquier métrica de Prometheus durante los despliegues Canary:

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: error-rate
  namespace: production
spec:
  provider:
    type: prometheus
    address: http://prometheus-kube-prometheus-prometheus.monitoring:9090
  query: |
    100 - sum(
      rate(
        http_requests_total{
          namespace="{{ namespace }}",
          job="{{ target }}-canary",
          status!~"5.*"
        }[{{ interval }}]
      )
    )
    /
    sum(
      rate(
        http_requests_total{
          namespace="{{ namespace }}",
          job="{{ target }}-canary"
        }[{{ interval }}]
      )
    ) * 100
```

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: latency-p95
  namespace: production
spec:
  provider:
    type: prometheus
    address: http://prometheus-kube-prometheus-prometheus.monitoring:9090
  query: |
    histogram_quantile(0.95,
      sum(
        rate(
          http_request_duration_seconds_bucket{
            namespace="{{ namespace }}",
            job="{{ target }}-canary"
          }[{{ interval }}]
        )
      ) by (le)
    )
```

Haga referencia a las métricas personalizadas en el análisis Canary:

```yaml
analysis:
  metrics:
  - name: error-rate
    templateRef:
      name: error-rate
      namespace: production
    thresholdRange:
      max: 1
    interval: 1m
  - name: latency-p95
    templateRef:
      name: latency-p95
      namespace: production
    thresholdRange:
      max: 0.5
    interval: 1m
```

### Proveedor de métricas Datadog

Flagger admite Datadog como proveedor de métricas externo:

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: dd-request-duration
  namespace: production
spec:
  provider:
    type: datadog
    secretRef:
      name: datadog-api
  query: |
    avg:trace.http.request.duration{
      service:{{ target }}-canary,
      kube_namespace:{{ namespace }}
    }.rollup(avg, 60)
---
apiVersion: v1
kind: Secret
metadata:
  name: datadog-api
  namespace: production
stringData:
  datadog_api_key: YOUR_DATADOG_API_KEY
  datadog_application_key: YOUR_DATADOG_APP_KEY
  datadog_site: datadoghq.com
```

### Proveedor de métricas CloudWatch

Para métricas de Amazon CloudWatch en EKS:

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: cw-error-rate
  namespace: production
spec:
  provider:
    type: cloudwatch
    region: us-west-2
  query: |
    [
      {
        "Id": "e1",
        "Expression": "m1 / m2 * 100",
        "Label": "ErrorRate"
      },
      {
        "Id": "m1",
        "MetricStat": {
          "Metric": {
            "Namespace": "MyApp",
            "MetricName": "5xxErrors",
            "Dimensions": [
              {
                "Name": "Service",
                "Value": "{{ target }}-canary"
              }
            ]
          },
          "Period": 60,
          "Stat": "Sum"
        },
        "ReturnData": false
      },
      {
        "Id": "m2",
        "MetricStat": {
          "Metric": {
            "Namespace": "MyApp",
            "MetricName": "TotalRequests",
            "Dimensions": [
              {
                "Name": "Service",
                "Value": "{{ target }}-canary"
              }
            ]
          },
          "Period": 60,
          "Stat": "Sum"
        },
        "ReturnData": false
      }
    ]
```

Asegúrese de que la service account de Flagger tenga los permisos de IAM adecuados para consultar CloudWatch:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

### Webhooks de rollout pre/post

Flagger admite varios tipos de webhooks que se ejecutan en diferentes fases del rollout:

| Tipo de webhook | Cuándo se ejecuta | Caso de uso |
|-------------|---------------|----------|
| `confirm-rollout` | Antes de iniciar el desplazamiento de tráfico | Puerta: requiere aprobación externa |
| `pre-rollout` | Antes de cada paso de análisis | Smoke tests, pruebas de conformidad |
| `rollout` | Durante cada paso de análisis | Pruebas de carga, tráfico sintético |
| `confirm-promotion` | Antes de la promoción final | Puerta manual, aprobación empresarial |
| `post-rollout` | Después de la promoción o reversión | Limpieza, notificación, auditoría |
| `rollback` | Después de un rollout fallido | Notificación de incidentes, limpieza |
| `event` | En cada evento de Flagger | Registro de auditoría |

### Ejemplos de YAML de webhooks

**Webhook de pruebas de carga con hey:**

```yaml
webhooks:
- name: load-test-hey
  type: rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 60s
  metadata:
    type: cmd
    cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"
    logCmdOutput: "true"
```

**Prueba de conformidad con bash:**

```yaml
webhooks:
- name: smoke-test
  type: pre-rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 120s
  metadata:
    type: bash
    cmd: |
      set -e
      # Check health endpoint
      curl -sf http://web-app-canary.production:8080/healthz

      # Check readiness
      curl -sf http://web-app-canary.production:8080/readyz

      # Verify API response
      response=$(curl -sf http://web-app-canary.production:8080/api/v1/status)
      echo "$response" | jq -e '.status == "ok"'
```

**Pruebas de carga con Grafana k6:**

```yaml
webhooks:
- name: load-test-k6
  type: rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 120s
  metadata:
    type: bash
    cmd: |
      k6 run --vus 5 --duration 1m - <<'EOF'
      import http from 'k6/http';
      import { check, sleep } from 'k6';

      export default function () {
        const res = http.get('http://web-app-canary.production:8080/');
        check(res, {
          'status is 200': (r) => r.status === 200,
          'duration < 500ms': (r) => r.timings.duration < 500,
        });
        sleep(0.5);
      }
      EOF
```

**Webhook de limpieza post-rollout:**

```yaml
webhooks:
- name: post-deploy-cleanup
  type: post-rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 60s
  metadata:
    type: bash
    cmd: |
      # Notify external system of deployment
      curl -X POST https://api.internal.example.com/deployments \
        -H 'Content-Type: application/json' \
        -d '{"service": "web-app", "status": "promoted", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
```

**Webhook externo para aprobación manual:**

```yaml
webhooks:
- name: manual-gate
  type: confirm-promotion
  url: https://deploy-approval.internal.example.com/api/approve
  timeout: 30s
  metadata:
    service: web-app
    environment: production
```

---

## Integración de GitOps (Flux + Flagger)

### Flujo de trabajo de FluxCD HelmRelease + Flagger Canary

El patrón más potente combina Flux HelmRelease para el despliegue de aplicaciones con Flagger Canary para la entrega progresiva. Flux administra el estado deseado desde Git, y Flagger administra cómo se implementan los cambios.

```mermaid
sequenceDiagram
    participant D as Developer
    participant G as Git Repository
    participant FC as Flux Controllers
    participant FL as Flagger
    participant K as Kubernetes

    D->>G: Push new image tag
    G->>FC: Source Controller detects change
    FC->>K: Helm Controller updates HelmRelease
    K->>FL: Deployment spec changed
    FL->>FL: Initialize canary
    FL->>K: Create canary pods
    FL->>FL: Run analysis (metrics + webhooks)

    alt Metrics Pass
        FL->>K: Promote canary to primary
        FL->>D: Notify: deployment succeeded
    else Metrics Fail
        FL->>K: Rollback to primary
        FL->>D: Notify: deployment failed
    end
```

**Estructura de repositorio para Flux + Flagger:**

```
fleet-infra/
├── clusters/
│   └── production/
│       ├── flux-system/         # Flux bootstrap
│       │   ├── gotk-components.yaml
│       │   └── gotk-sync.yaml
│       ├── infrastructure.yaml  # Infrastructure Kustomization
│       └── apps.yaml            # Apps Kustomization
├── infrastructure/
│   ├── flagger/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── helmrepository.yaml
│   │   └── helmrelease.yaml
│   └── istio/
│       └── ...
└── apps/
    └── web-app/
        ├── kustomization.yaml
        ├── deployment.yaml
        ├── hpa.yaml
        ├── canary.yaml          # Flagger Canary resource
        └── alerts.yaml          # Flagger AlertProviders
```

**Flux HelmRelease para la aplicación:**

```yaml
# apps/web-app/helmrelease.yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: web-app
  namespace: production
spec:
  interval: 5m
  chart:
    spec:
      chart: web-app
      version: "1.x"
      sourceRef:
        kind: HelmRepository
        name: internal-charts
        namespace: flux-system
  values:
    image:
      repository: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app
      tag: v2.0.0
    replicaCount: 3
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi
```

**Recurso Flagger Canary junto con HelmRelease:**

```yaml
# apps/web-app/canary.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: web-app
  progressDeadlineSeconds: 600
  service:
    port: 8080
    portName: http
    gateways:
    - istio-system/public-gateway
    hosts:
    - app.example.com
  analysis:
    interval: 1m
    maxWeight: 50
    stepWeight: 10
    threshold: 5
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
    webhooks:
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"
```

### Despliegue basado en Kustomization

Para equipos que usan Flux Kustomizations en lugar de HelmReleases:

```yaml
# clusters/production/apps.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: web-app
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: production
  sourceRef:
    kind: GitRepository
    name: fleet-infra
  path: ./apps/web-app
  prune: true
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: web-app
    namespace: production
  timeout: 5m
```

```yaml
# apps/web-app/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: production
resources:
- deployment.yaml
- service.yaml
- hpa.yaml
- canary.yaml
- alert-providers.yaml

images:
- name: web-app
  newName: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app
  newTag: v2.0.0
```

### Pipeline de automatización de Image Automation + Canary

El pipeline totalmente automatizado usa Flux Image Automation para detectar nuevas imágenes de contenedor, confirmar la etiqueta actualizada en Git y permitir que Flagger gestione el rollout progresivo:

```mermaid
flowchart LR
    subgraph CI["CI Pipeline"]
        BUILD["Build & Push<br/>Image"]
    end

    subgraph ECR["Amazon ECR"]
        IMG["web-app:v2.0.0"]
    end

    subgraph GIT["Git Repository"]
        MANIFEST["deployment.yaml<br/>image: web-app:v2.0.0"]
    end

    subgraph FLUX["Flux Controllers"]
        IR["Image Repository<br/>(scan ECR)"]
        IP["Image Policy<br/>(semver filter)"]
        IU["Image Update<br/>Automation"]
        KC["Kustomize<br/>Controller"]
    end

    subgraph FLAGGER["Flagger"]
        CANARY["Canary<br/>Controller"]
        ANALYSIS["Metrics<br/>Analysis"]
    end

    subgraph K8S["Kubernetes"]
        PRIMARY["Primary<br/>Deployment"]
        CANARY_DEP["Canary<br/>Deployment"]
    end

    BUILD --> IMG
    IMG --> IR
    IR --> IP
    IP --> IU
    IU -->|"git commit"| MANIFEST
    MANIFEST --> KC
    KC --> PRIMARY
    PRIMARY --> CANARY
    CANARY --> CANARY_DEP
    CANARY_DEP --> ANALYSIS
    ANALYSIS -->|"Promote"| PRIMARY

    classDef ci fill:#dc3545,stroke:#333,color:white
    classDef ecr fill:#FF9900,stroke:#333,color:white
    classDef git fill:#f05033,stroke:#333,color:white
    classDef flux fill:#5468FF,stroke:#333,color:white
    classDef flagger fill:#28a745,stroke:#333,color:white
    classDef k8s fill:#326CE5,stroke:#333,color:white

    class BUILD ci
    class IMG ecr
    class MANIFEST git
    class IR,IP,IU,KC flux
    class CANARY,ANALYSIS flagger
    class PRIMARY,CANARY_DEP k8s
```

**Recursos de Flux Image Automation:**

```yaml
# Image repository: scan ECR for new tags
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: web-app
  namespace: flux-system
spec:
  image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app
  interval: 5m
  provider: aws
---
# Image policy: select the latest semver tag
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: web-app
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: web-app
  policy:
    semver:
      range: ">=1.0.0"
---
# Image update automation: commit new tag to Git
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: web-app
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: fleet-infra
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux@example.com
        name: flux
      messageTemplate: |
        Automated image update

        Automation: {{ .AutomationObject }}

        Files:
        {{ range $filename, $_ := .Changed.FileChanges -}}
        - {{ $filename }}
        {{ end -}}

        Objects:
        {{ range $resource, $_ := .Changed.Objects -}}
        - {{ $resource.Kind }} {{ $resource.Name }}
        {{ end -}}
    push:
      branch: main
  update:
    path: ./apps/web-app
    strategy: Setters
```

Marque el campo de imagen en el Deployment con un comentario setter:

```yaml
# apps/web-app/deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: web-app
        image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app:v1.0.0 # {"$imagepolicy": "flux-system:web-app"}
```

Cuando se envía una nueva imagen (por ejemplo, `v2.0.0`) a ECR:
1. Flux Image Repository analiza ECR y detecta la nueva etiqueta
2. Flux Image Policy selecciona `v2.0.0` según el rango semver
3. Flux Image Update Automation confirma la nueva etiqueta en Git
4. Flux Kustomize Controller aplica el Deployment actualizado
5. Flagger detecta el cambio de Deployment e inicia el rollout Canary
6. Flagger desplaza progresivamente el tráfico, analiza métricas y promueve o revierte

---

## Observabilidad y alertas

### Panel de Grafana (métricas de Flagger)

Flagger exporta métricas de Prometheus que se pueden visualizar en Grafana. Las métricas clave son:

| Métrica | Tipo | Descripción |
|--------|------|-------------|
| `flagger_canary_status` | Gauge | Estado Canary (0=Initialized, 1=Progressing, 2=WaitingPromotion, 3=Promoting, 4=Finalising, 5=Succeeded, 6=Failed) |
| `flagger_canary_weight` | Gauge | Peso actual del tráfico Canary |
| `flagger_canary_total` | Counter | Número total de análisis Canary |
| `flagger_canary_duration_seconds` | Histogram | Duración del análisis Canary en segundos |
| `flagger_canary_metric_analysis` | Gauge | Resultado del último análisis de métricas (1=pass, 0=fail) |

**Importe el panel oficial de Flagger para Grafana:**

```bash
# The official Flagger dashboard ID for Grafana is 16527
# Import via Grafana UI: Dashboards > Import > Enter 16527
```

**Modelo JSON de panel personalizado de Grafana (simplificado):**

```json
{
  "title": "Flagger Canary Deployments",
  "panels": [
    {
      "title": "Canary Status",
      "type": "stat",
      "targets": [
        {
          "expr": "flagger_canary_status{namespace=\"production\"}",
          "legendFormat": "{{ name }}"
        }
      ]
    },
    {
      "title": "Canary Traffic Weight",
      "type": "timeseries",
      "targets": [
        {
          "expr": "flagger_canary_weight{namespace=\"production\"}",
          "legendFormat": "{{ name }}"
        }
      ]
    },
    {
      "title": "Request Success Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "flagger_canary_metric_analysis{namespace=\"production\", metric=\"request-success-rate\"}",
          "legendFormat": "{{ name }}"
        }
      ]
    }
  ]
}
```

### Reglas de alerta de Prometheus

Configure reglas de alerta de Prometheus para fallos de Canary de Flagger:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: flagger-alerts
  namespace: monitoring
spec:
  groups:
  - name: flagger
    rules:
    # Alert when a canary deployment fails
    - alert: CanaryDeploymentFailed
      expr: flagger_canary_status == 6
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Canary deployment failed for {{ $labels.name }}"
        description: >
          The canary deployment for {{ $labels.name }} in namespace
          {{ $labels.namespace }} has failed. Flagger has rolled back
          to the previous version.

    # Alert when a canary is stuck progressing
    - alert: CanaryProgressStalled
      expr: flagger_canary_status == 1 and flagger_canary_weight == flagger_canary_weight offset 10m
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "Canary progress stalled for {{ $labels.name }}"
        description: >
          The canary weight for {{ $labels.name }} has not changed in
          the last 15 minutes. Check Flagger logs for analysis failures.

    # Alert when canary metric analysis fails
    - alert: CanaryMetricCheckFailed
      expr: flagger_canary_metric_analysis == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Canary metric check failing for {{ $labels.name }}"
        description: >
          The {{ $labels.metric }} metric check for {{ $labels.name }}
          is failing. If this continues, Flagger will rollback.

    # Alert on high canary analysis duration
    - alert: CanaryAnalysisSlow
      expr: histogram_quantile(0.99, rate(flagger_canary_duration_seconds_bucket[1h])) > 600
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Canary analysis taking too long for {{ $labels.name }}"
        description: >
          The canary analysis P99 duration exceeds 10 minutes.
          Consider tuning the analysis interval or metrics thresholds.
```

### Configuración de notificaciones de Slack y Teams

Configure alertas exhaustivas con enrutamiento basado en gravedad:

```yaml
# Alert provider for informational messages (deployments started, promoted)
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: slack-info
  namespace: production
spec:
  type: slack
  channel: deploy-notifications
  username: flagger
  secretRef:
    name: slack-webhook
---
# Alert provider for critical messages (failures, rollbacks)
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: slack-critical
  namespace: production
spec:
  type: slack
  channel: deploy-incidents
  username: flagger
  secretRef:
    name: slack-webhook
---
# Alert provider for PagerDuty integration
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: pagerduty
  namespace: production
spec:
  type: slack
  # PagerDuty Slack integration or Events API v2
  secretRef:
    name: pagerduty-webhook
```

Haga referencia a varios proveedores con diferentes niveles de gravedad en el Canary:

```yaml
spec:
  analysis:
    alerts:
    - name: "info-slack"
      severity: info
      providerRef:
        name: slack-info
    - name: "error-slack"
      severity: error
      providerRef:
        name: slack-critical
    - name: "critical-pagerduty"
      severity: error
      providerRef:
        name: pagerduty
```

### Seguimiento del historial de despliegues

Realice el seguimiento del historial de despliegues mediante eventos de Flagger y eventos de Kubernetes:

```bash
# View Flagger events for a canary
kubectl describe canary web-app -n production

# Query Flagger events via kubectl
kubectl get events -n production \
  --field-selector involvedObject.kind=Canary,involvedObject.name=web-app \
  --sort-by='.lastTimestamp'

# Export deployment history from Prometheus
# Query: changes(flagger_canary_status{name="web-app"}[7d])
```

Para el historial de despliegues a largo plazo, integre con Flux Notification Controller para reenviar eventos a un sistema externo:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: deployment-tracker
  namespace: flux-system
spec:
  type: generic
  address: https://deploy-tracker.internal.example.com/api/events
---
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: flagger-events
  namespace: flux-system
spec:
  providerRef:
    name: deployment-tracker
  eventSources:
  - kind: Canary
    name: "*"
    namespace: production
  eventSeverity: info
```

---

## Prácticas recomendadas para producción

### Estrategia de adopción incremental

Adopte Flagger progresivamente en toda su organización:

**Fase 1: Servicios no críticos**
- Comience con herramientas internas o entornos de staging
- Utilice configuraciones de análisis conservadoras (umbrales altos, muchas iteraciones)
- Valide la recopilación de métricas y la integración de webhooks

**Fase 2: Servicios de producción de bajo riesgo**
- Aplíquelo a servicios de producción con radio de impacto reducido
- Configure canales de alertas y notificaciones
- Establezca runbooks para la intervención manual

**Fase 3: Servicios de misión crítica**
- Aplíquelo a servicios de alto tráfico orientados al cliente
- Utilice aprobación manual para mayor seguridad
- Implemente métricas personalizadas específicas para los KPI empresariales

**Fase 4: Rollout en toda la organización**
- Estandarice las plantillas Canary entre los equipos
- Cree una plataforma de autoservicio con Flux + Flagger
- Automatice pipelines de extremo a extremo de imagen a producción

### Ajuste de umbrales de métricas

Elegir los umbrales de métricas adecuados es fundamental para equilibrar la velocidad de despliegue con la seguridad:

```yaml
# Conservative (recommended for initial rollout)
analysis:
  interval: 2m
  maxWeight: 30
  stepWeight: 5
  threshold: 3
  iterations: 15
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 99.9
    interval: 2m
  - name: request-duration
    thresholdRange:
      max: 200
    interval: 2m

# Balanced (recommended for most production services)
analysis:
  interval: 1m
  maxWeight: 50
  stepWeight: 10
  threshold: 5
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 99
    interval: 1m
  - name: request-duration
    thresholdRange:
      max: 500
    interval: 1m

# Aggressive (for high-confidence, frequently deployed services)
analysis:
  interval: 30s
  maxWeight: 80
  stepWeight: 20
  threshold: 10
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 95
    interval: 30s
  - name: request-duration
    thresholdRange:
      max: 1000
    interval: 30s
```

**Directrices para el ajuste de umbrales:**

| Parámetro | Conservador | Equilibrado | Agresivo |
|-----------|-------------|----------|------------|
| `interval` | 2m | 1m | 30s |
| `stepWeight` | 5 | 10 | 20 |
| `maxWeight` | 30 | 50 | 80 |
| `threshold` (fallos) | 3 | 5 | 10 |
| Mínimo de tasa de éxito | 99.9% | 99% | 95% |
| Máximo de latencia P99 | 200ms | 500ms | 1000ms |
| Tiempo total de rollout | ~20 min | ~10 min | ~4 min |

### Estrategias de reversión

Comprender el comportamiento de reversión es esencial para las operaciones de producción:

**Reversión automática** (comportamiento predeterminado):
- Flagger detecta fallos de métricas que superan el umbral
- Todo el tráfico se enruta inmediatamente de vuelta al primary
- Los pods Canary se reducen a cero
- El estado se establece en `Failed`

**Reversión manual**:
```bash
# Force a rollback by setting the skipAnalysis annotation
kubectl annotate canary web-app -n production \
  flagger.app/rollback="true"

# Skip analysis for emergency deploys (not recommended for production)
kubectl annotate canary web-app -n production \
  flagger.app/skipAnalysis="true"
```

**Webhook de reversión** para respuesta automatizada a incidentes:

```yaml
webhooks:
- name: rollback-handler
  type: rollback
  url: http://incident-handler.production:8080/api/rollback
  timeout: 30s
  metadata:
    service: web-app
    team: platform
    pagerduty_service: web-app-prod
```

### Flagger multiclúster

Para organizaciones que ejecutan varios clústeres EKS, Flagger se puede implementar en un patrón hub-and-spoke:

```mermaid
graph TB
    subgraph HUB["Management Cluster"]
        FLUX_HUB["Flux Controllers"]
        GIT[("Git Repository")]
    end

    subgraph SPOKE1["Production Cluster - us-east-1"]
        FL1["Flagger"]
        ISTIO1["Istio"]
        APP1["web-app"]
    end

    subgraph SPOKE2["Production Cluster - us-west-2"]
        FL2["Flagger"]
        ISTIO2["Istio"]
        APP2["web-app"]
    end

    subgraph SPOKE3["Production Cluster - eu-west-1"]
        FL3["Flagger"]
        ISTIO3["Istio"]
        APP3["web-app"]
    end

    GIT --> FLUX_HUB
    FLUX_HUB -->|"Kustomization"| SPOKE1
    FLUX_HUB -->|"Kustomization"| SPOKE2
    FLUX_HUB -->|"Kustomization"| SPOKE3

    classDef hub fill:#FF9900,stroke:#333,color:white
    classDef spoke fill:#326CE5,stroke:#333,color:white

    class FLUX_HUB,GIT hub
    class FL1,FL2,FL3,ISTIO1,ISTIO2,ISTIO3,APP1,APP2,APP3 spoke
```

**Consideraciones clave para Flagger multiclúster:**

1. **Instancias de Flagger independientes**: Implemente Flagger en cada clúster; solo administra recursos locales
2. **Definiciones Canary compartidas**: Utilice Flux Kustomizations con overlays para la configuración específica del clúster
3. **Rollouts secuenciales**: Utilice dependencias de Flux para realizar el rollout a staging antes que a los clústeres de producción
4. **Observabilidad centralizada**: Agregue las métricas de Flagger de todos los clústeres a un Prometheus/Thanos/Mimir central

```yaml
# clusters/production-us-east-1/apps.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: web-app
  namespace: flux-system
spec:
  # Deploy to us-east-1 only after staging succeeds
  dependsOn:
  - name: web-app
    namespace: flux-system
  # This refers to the staging cluster Kustomization
  sourceRef:
    kind: GitRepository
    name: fleet-infra
  path: ./apps/web-app/overlays/production-us-east-1
  interval: 10m
  prune: true
```

### Prácticas recomendadas adicionales

1. **Ejecute siempre pruebas de carga durante el análisis Canary.** Sin tráfico al Canary, Prometheus no tiene métricas que analizar. Utilice el loadtester de Flagger o genere tráfico sintético.

2. **Establezca `progressDeadlineSeconds` adecuadamente.** Esta es su red de seguridad. Si el Canary no puede progresar dentro de este tiempo, se revierte automáticamente. Establézcalo al menos en 2 veces el tiempo total de rollout esperado.

3. **Use `skipAnalysis` con moderación.** Aunque permite despliegues de emergencia, omite todas las comprobaciones de seguridad. Prefiera la aprobación manual para cambios urgentes que aún necesiten validación básica.

4. **Fije las versiones de Flagger y del proveedor.** Utilice versiones específicas de Helm chart en su Flux HelmRelease para evitar comportamientos inesperados de actualizaciones automáticas.

5. **Pruebe el comportamiento de reversión regularmente.** Implemente versiones conocidas como defectuosas en staging para verificar que Flagger detecta correctamente los fallos y revierte.

6. **Separe las definiciones Canary de los Deployments en Git.** Esto mantiene sus recursos Deployment limpios y portátiles, con las preocupaciones de entrega progresiva aisladas en recursos Canary.

7. **Utilice AlertProviders con ámbito de namespace.** Esto evita la filtración de credenciales de webhook entre namespaces y admite entornos multiinquilino.

8. **Supervise la salud del controlador Flagger.** Configure alertas para reinicios de pod de Flagger, uso elevado de memoria y errores de reconciliación.

---

## Referencias

### Documentación oficial

- [Documentación oficial de Flagger](https://docs.flagger.app/)
- [Repositorio de GitHub de Flagger](https://github.com/fluxcd/flagger)
- [Helm Chart de Flagger](https://artifacthub.io/packages/helm/flagger/flagger)
- [Documentación oficial de FluxCD](https://fluxcd.io/docs/)
- [Preguntas frecuentes de Flagger](https://docs.flagger.app/faq)

### Documentación interna relacionada

| Tema | Enlace |
|-------|------|
| FluxCD | [GitOps de FluxCD](./02-fluxcd.md) |
| Comparación de herramientas GitOps | [ArgoCD vs FluxCD vs otros](./03-gitops-comparison.md) |
| ArgoCD | [Documentación de ArgoCD](./argocd/README.md) |
| División de tráfico de Istio | [División de tráfico](../service-mesh/istio/traffic-management/04-traffic-splitting.md) |
| Argo Rollouts + Istio | [Integración de Argo Rollouts](../service-mesh/istio/advanced/08-argo-rollouts.md) |
| Prometheus | [Monitoreo con Prometheus](../observability/metrics/01-prometheus.md) |
| Grafana | [Paneles de Grafana](../observability/grafana/README.md) |
| Gateway API | [Gateway API](../networking/04-gateway-api.md) |
| Escalado automático KEDA | [KEDA](../autoscaling/01-keda.md) |

### Recursos externos

- [Entrega progresiva con Flagger (webinar de CNCF)](https://www.cncf.io/online-programs/progressive-delivery-with-flagger/)
- [GitOps y entrega progresiva con Flux y Flagger](https://fluxcd.io/blog/)
- [Despliegues Canary con Flagger e Istio](https://docs.flagger.app/tutorials/istio-progressive-delivery)
- [Flagger en AWS App Mesh](https://docs.flagger.app/tutorials/appmesh-progressive-delivery)
- [Despliegues Canary de Gateway API](https://docs.flagger.app/tutorials/gatewayapi-progressive-delivery)

---

## Navegación

| Anterior | Arriba | Siguiente |
|----------|----|----- |
| [Comparación de herramientas GitOps](./03-gitops-comparison.md) | [Descripción general de GitOps](./README.md) | Ninguno |
