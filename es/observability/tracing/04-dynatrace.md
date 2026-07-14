# Dynatrace

> **Última actualización**: February 20, 2026

## Introducción

Dynatrace es una plataforma de observabilidad full-stack impulsada por IA. A través de la tecnología OneAgent, supervisa automáticamente las aplicaciones, la infraestructura y la experiencia de usuario, mientras que el motor Davis AI analiza automáticamente las causas raíz de los problemas.

## Características principales

| Característica | Descripción |
|---------|-------------|
| **OneAgent** | Supervisión full-stack con un único agente |
| **Auto-instrumentation** | Trazabilidad automática sin cambios en el código |
| **Davis AI** | Análisis de causa raíz impulsado por IA |
| **PurePath** | Tecnología de trazabilidad distribuida |
| **Smartscape** | Mapeo de topología en tiempo real |
| **Full Stack** | Desde la infraestructura hasta la experiencia de usuario |

## Arquitectura

```mermaid
flowchart TD
    subgraph EKS["Amazon EKS Cluster"]
        subgraph Nodes["Worker Nodes"]
            OA1[OneAgent<br/>DaemonSet]
            OA2[OneAgent<br/>DaemonSet]
        end

        subgraph Apps["Applications"]
            APP1[Service A]
            APP2[Service B]
            APP3[Service C]
        end

        subgraph Operator["Dynatrace Operator"]
            DYN_OP[Operator Pod]
            WEBHOOK[Webhook]
        end

        ACTIVEGATE[ActiveGate<br/>StatefulSet]
    end

    subgraph Dynatrace["Dynatrace Platform"]
        SaaS[Dynatrace SaaS]
        DAVIS[Davis AI Engine]
        GRAIL[Grail Data Lakehouse]
    end

    OA1 & OA2 -->|Metrics/Traces/Logs| ACTIVEGATE
    ACTIVEGATE -->|Encrypted Connection| SaaS
    SaaS --> DAVIS
    SaaS --> GRAIL

    APP1 & APP2 & APP3 -.->|Auto-instrumentation| OA1 & OA2

    classDef node fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef dynatrace fill:#6F2DA8,stroke:#333,stroke-width:1px,color:white
    classDef operator fill:#F8B52A,stroke:#333,stroke-width:1px,color:black

    class OA1,OA2,ACTIVEGATE node
    class APP1,APP2,APP3 app
    class SaaS,DAVIS,GRAIL dynatrace
    class DYN_OP,WEBHOOK operator
```

## Despliegue en EKS con Helm

### 1. Instalar Dynatrace Operator

```bash
# Add Helm repository
helm repo add dynatrace https://raw.githubusercontent.com/Dynatrace/dynatrace-operator/main/config/helm/repos/stable
helm repo update

# Create namespace
kubectl create namespace dynatrace
```

### 2. Crear tokens de API

Cree tokens de API en la consola de Dynatrace con estos permisos:

- `Access problem and event feed, metrics, and topology`
- `Read configuration`
- `Write configuration`
- `PaaS integration - Installer download`
- `PaaS integration - Support alert`
- `Read entities`
- `Write entities`
- `Read settings`
- `Write settings`
- `Ingest logs`
- `Ingest metrics`
- `Ingest OpenTelemetry traces`

### 3. Crear Secret

```yaml
# dynatrace-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: dynakube
  namespace: dynatrace
type: Opaque
data:
  # Base64 encoded values
  apiToken: <BASE64_ENCODED_API_TOKEN>
  dataIngestToken: <BASE64_ENCODED_DATA_INGEST_TOKEN>
```

```bash
# Or create via CLI
kubectl create secret generic dynakube \
  --namespace dynatrace \
  --from-literal=apiToken=<API_TOKEN> \
  --from-literal=dataIngestToken=<DATA_INGEST_TOKEN>
```

### 4. Configuración de values.yaml

```yaml
# dynatrace-values.yaml
platform: "kubernetes"

operator:
  image:
    repository: docker.io/dynatrace/dynatrace-operator
    tag: v1.0.0
  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 100m
      memory: 256Mi

webhook:
  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 100m
      memory: 256Mi

csidriver:
  enabled: true
```

### 5. Instalar Operator

```bash
helm upgrade --install dynatrace-operator dynatrace/dynatrace-operator \
  --namespace dynatrace \
  --values dynatrace-values.yaml \
  --wait
```

### 6. Configuración de DynaKube CR

```yaml
# dynakube.yaml
apiVersion: dynatrace.com/v1beta2
kind: DynaKube
metadata:
  name: dynakube
  namespace: dynatrace
spec:
  # Dynatrace environment URL
  apiUrl: https://<ENVIRONMENT_ID>.live.dynatrace.com/api

  # OneAgent deployment mode
  oneAgent:
    # Classic Full Stack (DaemonSet)
    classicFullStack:
      tolerations:
        - effect: NoSchedule
          operator: Exists
      args:
        - --set-host-group=eks-production
      env:
        - name: ONEAGENT_ENABLE_VOLUME_STORAGE
          value: "true"
      resources:
        requests:
          cpu: 100m
          memory: 512Mi
        limits:
          cpu: 500m
          memory: 1.5Gi
      # Node selector
      nodeSelector:
        kubernetes.io/os: linux

  # ActiveGate configuration
  activeGate:
    capabilities:
      - routing
      - kubernetes-monitoring
      - dynatrace-api
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 1000m
        memory: 1.5Gi
    # Replica count
    replicas: 2
    # Kubernetes API monitoring
    group: eks-production
    # Custom properties
    customProperties:
      value: |
        [kubernetes_monitoring]
        kubernetes_cluster_name=eks-production

  # Metadata enrichment
  metadataEnrichment:
    enabled: true

  # Namespace selector (namespaces to monitor)
  namespaceSelector:
    matchLabels:
      dynatrace: enabled
---
# Add label to namespaces to monitor
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    dynatrace: enabled
```

### 7. Desplegar y verificar

```bash
# Deploy DynaKube
kubectl apply -f dynakube.yaml

# Check status
kubectl get dynakube -n dynatrace
kubectl get pods -n dynatrace

# Check OneAgent status
kubectl logs -n dynatrace -l app.kubernetes.io/name=oneagent --tail=100

# Check ActiveGate status
kubectl logs -n dynatrace -l app.kubernetes.io/name=activegate --tail=100
```

## Modo Cloud Native Full Stack

Supervisión ligera mediante inyección de módulos de código:

```yaml
# dynakube-cloudnative.yaml
apiVersion: dynatrace.com/v1beta2
kind: DynaKube
metadata:
  name: dynakube
  namespace: dynatrace
spec:
  apiUrl: https://<ENVIRONMENT_ID>.live.dynatrace.com/api

  oneAgent:
    # Cloud Native Full Stack (Sidecar approach)
    cloudNativeFullStack:
      # Code modules image
      codeModulesImage: docker.io/dynatrace/dynatrace-codemodules

      # Namespace selector
      namespaceSelector:
        matchLabels:
          dynatrace-injection: enabled

      # Resource limits
      initResources:
        requests:
          cpu: 30m
          memory: 30Mi
        limits:
          cpu: 300m
          memory: 300Mi

      # Node selector
      nodeSelector:
        kubernetes.io/os: linux

      # Tolerations
      tolerations:
        - effect: NoSchedule
          operator: Exists

  # Host monitoring separate configuration
  hostGroup: eks-prod-cloudnative

  activeGate:
    capabilities:
      - routing
      - kubernetes-monitoring
```

## Análisis de causa raíz con Davis AI

### Cómo funciona Davis AI

```mermaid
flowchart TD
    subgraph DataCollection["Data Collection"]
        METRICS[Metrics]
        TRACES[Traces]
        LOGS[Logs]
        EVENTS[Events]
        TOPO[Topology]
    end

    subgraph DavisAI["Davis AI Engine"]
        BASELINE[Baseline Learning]
        ANOMALY[Anomaly Detection]
        CORRELATE[Correlation Analysis]
        ROOT[Root Cause Identification]
    end

    subgraph Output["Analysis Results"]
        PROBLEM[Problem Card]
        IMPACT[Impact Analysis]
        REMEDIATION[Remediation Suggestions]
    end

    METRICS & TRACES & LOGS & EVENTS & TOPO --> BASELINE
    BASELINE --> ANOMALY
    ANOMALY --> CORRELATE
    CORRELATE --> ROOT
    ROOT --> PROBLEM & IMPACT & REMEDIATION

    classDef data fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef ai fill:#6F2DA8,stroke:#333,stroke-width:1px,color:white
    classDef output fill:#34A853,stroke:#333,stroke-width:1px,color:white

    class METRICS,TRACES,LOGS,EVENTS,TOPO data
    class BASELINE,ANOMALY,CORRELATE,ROOT ai
    class PROBLEM,IMPACT,REMEDIATION output
```

### Configuración de alertas de problemas

```yaml
# Dynatrace alerting profile (via API)
# POST /api/config/v1/alertingProfiles
{
  "displayName": "EKS Production Alerts",
  "rules": [
    {
      "severityLevel": "AVAILABILITY",
      "tagFilter": {
        "includeMode": "INCLUDE_ANY",
        "tagFilters": [
          {
            "context": "KUBERNETES_CLUSTER",
            "key": "eks-production"
          }
        ]
      },
      "delayInMinutes": 0
    },
    {
      "severityLevel": "ERROR",
      "tagFilter": {
        "includeMode": "INCLUDE_ANY",
        "tagFilters": [
          {
            "context": "CONTEXTLESS",
            "key": "environment",
            "value": "production"
          }
        ]
      },
      "delayInMinutes": 5
    }
  ],
  "eventTypeFilters": []
}
```

## Auto-instrumentation

### Tecnologías compatibles

| Lenguaje/plataforma | Frameworks compatibles |
|-------------------|---------------------|
| **Java** | Spring, Spring Boot, Micronaut, Quarkus, Jakarta EE |
| **Node.js** | Express, Fastify, NestJS, Koa |
| **Python** | Django, Flask, FastAPI |
| **.NET** | ASP.NET Core, .NET Framework |
| **Go** | net/http, Gin, Echo, Fiber |
| **PHP** | Laravel, Symfony |

### Verificar Auto-instrumentation

```bash
# Check Pod environment variables
kubectl exec -it <pod-name> -- env | grep -i dynatrace

# Expected output:
# LD_PRELOAD=/opt/dynatrace/oneagent/agent/lib64/liboneagentproc.so
# DT_TENANT=abc12345
# DT_TENANTTOKEN=xxxxx
# DT_CONNECTION_POINT=https://abc12345.live.dynatrace.com/communication

# Check OneAgent logs
kubectl exec -it <pod-name> -- cat /var/log/dynatrace/oneagent/oneagent.log
```

## Estructura de costos

### Modelo de licencia

| Tipo | Unidad | Incluye |
|------|------|----------|
| **Full-Stack** | Unidad de host | Infraestructura + APM + Logs |
| **Infrastructure** | Unidad de host | Solo supervisión de infraestructura |
| **Application Security** | Unidad de host | RASP + Análisis de vulnerabilidades |
| **DEM (Digital Experience)** | Sesión | RUM + Synthetic |
| **Log Monitoring** | GiB | Recopilación y análisis de logs |

### Estrategias de optimización de costos

```yaml
# 1. Selective namespace monitoring
spec:
  oneAgent:
    cloudNativeFullStack:
      namespaceSelector:
        matchLabels:
          dynatrace-injection: enabled  # Only necessary namespaces

# 2. Resource limits
      resources:
        limits:
          cpu: 500m
          memory: 1Gi

# 3. Data retention adjustment (Dynatrace console)
# Settings > Monitoring > Data privacy > Data retention

# 4. Disable session replay if needed
# Applications > [App] > Session Replay > Disable
```

### Cálculo de unidades de host

```
Host Units = max(memory_GB / 16, vCPU / 1.5)

Examples:
- 4 vCPU, 16GB RAM = max(1, 2.67) = 2.67 Host Units
- 8 vCPU, 32GB RAM = max(2, 5.33) = 5.33 Host Units
- 2 vCPU, 8GB RAM  = max(0.5, 1.33) = 1.33 Host Units
```

## Integración con OpenTelemetry

Dynatrace recopila datos de OpenTelemetry de forma nativa:

```yaml
# Send from OTEL Collector to Dynatrace
exporters:
  otlphttp/dynatrace:
    endpoint: https://<ENVIRONMENT_ID>.live.dynatrace.com/api/v2/otlp
    headers:
      Authorization: "Api-Token <DYNATRACE_API_TOKEN>"

service:
  pipelines:
    traces:
      exporters: [otlphttp/dynatrace]
    metrics:
      exporters: [otlphttp/dynatrace]
    logs:
      exporters: [otlphttp/dynatrace]
```

## Solución de problemas

### Problemas comunes

```bash
# 1. OneAgent connection issues
kubectl logs -n dynatrace -l app.kubernetes.io/name=oneagent | grep -i error

# 2. ActiveGate status check
kubectl exec -n dynatrace -it $(kubectl get pod -n dynatrace -l app.kubernetes.io/name=activegate -o jsonpath='{.items[0].metadata.name}') -- \
  /opt/dynatrace/gateway/jre/bin/java -jar /opt/dynatrace/gateway/lib/cli.jar status

# 3. Code module injection verification
kubectl describe pod <pod-name> | grep -A5 "Init Containers"

# 4. Network connectivity test
kubectl exec -n dynatrace -it <oneagent-pod> -- \
  curl -v https://<ENVIRONMENT_ID>.live.dynatrace.com/api/v1/deployment/installer/agent/connectioninfo

# 5. Token permission verification
curl -X GET "https://<ENVIRONMENT_ID>.live.dynatrace.com/api/v2/apiTokens/<TOKEN_ID>" \
  -H "Authorization: Api-Token <API_TOKEN>"
```

### Verificación de recopilación de logs

```bash
# ActiveGate logs
kubectl logs -n dynatrace -l app.kubernetes.io/name=activegate --tail=200

# OneAgent logs
kubectl exec -n dynatrace -it <oneagent-pod> -- \
  tail -100 /var/log/dynatrace/oneagent/oneagent.log

# Operator logs
kubectl logs -n dynatrace -l app.kubernetes.io/name=dynatrace-operator --tail=100
```

## Cuestionario

Ponga a prueba sus conocimientos con el [cuestionario de Dynatrace](../../quizzes/observability/tracing/04-dynatrace-quiz.md).
