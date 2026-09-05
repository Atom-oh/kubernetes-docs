# Istio Dashboards

> **Supported Versions**: Istio 1.28
> **Last Updated**: February 19, 2026

Comprehensively visualize and monitor Istio service mesh using Grafana, Kiali, and Prometheus.

## Table of Contents

1. [Dashboard Overview](#dashboard-overview)
2. [Kiali](#kiali)
3. [Grafana Dashboards](#grafana-dashboards)
4. [Prometheus](#prometheus)
5. [Creating Custom Dashboards](#creating-custom-dashboards)
6. [Dashboard Integration](#dashboard-integration)
7. [Best Practices](#best-practices)

## Dashboard Overview

### Observability Stack Architecture

![Architecture diagram showing Envoy sidecars in the Istio data plane sending metrics, logs, and traces to Prometheus, Loki, Jaeger, and Tempo, which in turn feed the Kiali, Grafana, and Jaeger UI dashboards, while istiod pushes configuration to Kiali for validation.](../../../.gitbook/assets/en-service-mesh-istio-observability-04-dashboards-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-observability-04-dashboards-0.html)

### Purpose by Tool

| Tool | Primary Use | Data Source |
|------|-------------|-------------|
| **Kiali** | Service topology, traffic analysis, configuration validation | Prometheus, Istio Config |
| **Grafana** | Metrics visualization, alerting, log analysis | Prometheus, Loki, Tempo |
| **Prometheus** | Metrics collection and querying | Envoy, istiod |
| **Jaeger** | Distributed trace analysis | Envoy spans |

## Kiali

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="900">
</p>

Kiali is an **observability console** for Istio service mesh. It visualizes service topology in real-time, analyzes traffic flow, and validates Istio configurations.

### Kiali's Core Value

1. **Service Graph Visualization**: Intuitively represents relationships and traffic flow between microservices
2. **Real-time Monitoring**: View request rate, error rate, and response time in real-time
3. **Configuration Validation**: Detect errors in Istio CRDs like VirtualService, DestinationRule
4. **mTLS Status Verification**: Visually confirm mTLS application between services
5. **Distributed Tracing Integration**: View traces directly from service graph with Jaeger integration

### Production Deployment

#### 1. Install Kiali Operator

```bash
# Deploy Kiali Operator
kubectl create namespace kiali-operator
kubectl apply -f https://raw.githubusercontent.com/kiali/kiali-operator/v1.79/deploy/kiali-operator.yaml

# Verify installation
kubectl get pods -n kiali-operator
```

#### 2. Create Kiali CR (Production Configuration)

```yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali
  namespace: istio-system
spec:
  # Deployment settings
  deployment:
    accessible_namespaces:
    - "**"  # Access all namespaces
    image_name: quay.io/kiali/kiali
    image_version: v1.79
    replicas: 2
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 1Gi

    # Ingress settings
    ingress:
      enabled: true
      class_name: nginx
      override_yaml:
        metadata:
          annotations:
            cert-manager.io/cluster-issuer: letsencrypt-prod
        spec:
          rules:
          - host: kiali.example.com
            http:
              paths:
              - path: /
                pathType: Prefix
                backend:
                  service:
                    name: kiali
                    port:
                      number: 20001
          tls:
          - hosts:
            - kiali.example.com
            secretName: kiali-tls

  # Authentication settings
  auth:
    strategy: token  # token, openid, openshift, anonymous

  # External service integration
  external_services:
    # Prometheus
    prometheus:
      url: http://prometheus.istio-system:9090

    # Grafana
    grafana:
      enabled: true
      url: http://grafana.observability:3000
      in_cluster_url: http://grafana.observability:3000
      dashboards:
      - name: "Istio Service Dashboard"
        variables:
          namespace: "var-namespace"
          service: "var-service"
      - name: "Istio Workload Dashboard"
        variables:
          namespace: "var-namespace"
          workload: "var-workload"

    # Jaeger
    jaeger:
      enabled: true
      url: http://jaeger-query.observability:16686
      in_cluster_url: http://jaeger-query.observability:16686

    # Custom Dashboards
    custom_dashboards:
    - name: "Loki Istio Logs"
      title: "Istio Access Logs"
      runtime: Grafana
      template: "/dashboards/loki-istio.json"

  # Kiali feature settings
  kiali_feature_flags:
    # Enable validation features
    validations:
      ignore:
      - "KIA1301"  # Ignore specific validation rules

    # UI features
    ui_defaults:
      graph:
        find_options:
        - description: "Find: slow edges (> 1s)"
          expression: "rt > 1000"
        - description: "Find: error edges (>= 5%)"
          expression: "error > 5"
        impl: cy  # cytoscape graph engine

      metrics_per_refresh: "1m"
      namespaces:
      - istio-system
      refresh_interval: "60s"
```

**Deploy**:
```bash
kubectl apply -f kiali-cr.yaml

# Verify installation
kubectl get kiali -n istio-system
kubectl get pods -n istio-system -l app=kiali
```

### Accessing Kiali

#### Development Environment

```bash
# Access via port-forward
kubectl port-forward -n istio-system svc/kiali 20001:20001

# Browser: http://localhost:20001
```

#### Production Environment (Token Authentication)

```bash
# Create ServiceAccount Token
kubectl create token kiali -n istio-system --duration=24h

# Login with Token
# Browser: https://kiali.example.com
# Username: (leave empty)
# Token: (token generated above)
```

### Kiali Key Features

#### 1. Service Graph (Graph)

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph-overview.png" alt="Kiali Graph Overview" width="800">
</p>

**Overview**:
- Visualize service topology by namespace
- Display traffic flow and request rate (RPS)
- Visualize error rate and response time
- Verify traffic distribution by version

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-traffic-animation.png" alt="Kiali Traffic Animation" width="700">
</p>

The image above shows Kiali's **Traffic Animation** feature, which displays real-time traffic flow with animation. The size and frequency of dots intuitively show traffic volume.

**Graph View Types**:

| View Type | Description | Use Scenario |
|-----------|-------------|--------------|
| **App Graph** | Application level | Understanding service dependencies |
| **Versioned App Graph** | Application by version | Canary deployment monitoring |
| **Workload Graph** | Workload level | Deployment/StatefulSet level analysis |
| **Service Graph** | Service level | Kubernetes Service-centric view |

**Graph Filter Options**:

```yaml
# Edge label display
- Request percentage: Traffic distribution rate (%)
- Request rate: Request rate (RPS)
- Response time: P95 response time
- Throughput: Throughput (bytes/sec)

# Display options
- Traffic Animation: Real-time traffic flow
- Service Nodes: Show service nodes
- Traffic Distribution: Version-based traffic distribution
- Security: mTLS lock icon
- Circuit Breakers: Circuit breaker status
- Virtual Services: VirtualService icon
```

**Find/Hide Feature**:
```
# Find slow edges
Find: response time > 1s
Expression: rt > 1000

# Find edges with errors
Find: error rate >= 5%
Expression: error >= 5

# Hide specific services
Hide: kube-system namespace
```

#### 2. Applications View

Detailed information for each application:

- **Overview**: Overall status summary
- **Traffic**: Inbound/outbound traffic metrics
  - Request volume (RPS)
  - Request duration (P50, P95, P99)
  - Request size / Response size
- **Inbound Metrics**: Incoming traffic analysis
  - Source workloads
  - Request protocols (HTTP/gRPC/TCP)
  - Response codes
- **Outbound Metrics**: Outgoing traffic analysis
  - Destination services
  - Response times
  - Error rates

#### 3. Workloads View

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-workload-detail.png" alt="Kiali Workload Detail" width="900">
</p>

Detailed information per workload (Deployment, StatefulSet, etc.):

- **Pods**: Pod list and status
- **Services**: Connected Service list
- **Logs**: Real-time pod logs (Envoy + Application)
- **Metrics**: Workload metrics
  - Request volume
  - Duration (P50/P95/P99)
  - Error rate
- **Traces**: Distributed tracing with Jaeger integration
- **Envoy**: Envoy configuration verification
  - Clusters
  - Listeners
  - Routes
  - Bootstrap config

#### 4. Services View

Detailed information per Kubernetes Service:

- **Overview**: Service metadata
- **Traffic**: Traffic metrics
- **Inbound Metrics**: Request analysis by client
- **Traces**: Service call tracing

#### 5. Istio Configuration Validation (Istio Config)

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-config-validation.png" alt="Kiali Config Validation" width="900">
</p>

Validation and management of all Istio resources:

**Validation Targets**:
- VirtualService
- DestinationRule
- Gateway
- ServiceEntry
- Sidecar
- PeerAuthentication
- RequestAuthentication
- AuthorizationPolicy
- Telemetry

**Validation Levels**:

| Icon | Level | Description |
|------|-------|-------------|
| ✅ | Valid | Configuration is correct |
| ⚠️ | Warning | Potential issue (best practice violation) |
| ❌ | Error | Configuration error (application failure) |

**Common Validation Error Examples**:

```yaml
# KIA0101: DestinationRule and VirtualService don't reference the same host
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews  # ❌ Mismatch with DestinationRule host
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews.default.svc.cluster.local  # ⚠️ Using FQDN
  subsets:
  - name: v1
    labels:
      version: v1
```

**Corrected Version**:
```yaml
# Both resources use FQDN
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews.default.svc.cluster.local  # ✅
  http:
  - route:
    - destination:
        host: reviews.default.svc.cluster.local
        subset: v1
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews.default.svc.cluster.local  # ✅
  subsets:
  - name: v1
    labels:
      version: v1
```

#### 6. Security

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-mtls.png" alt="Kiali mTLS Status" width="800">
</p>

**mTLS Status Verification**:

Visually verify mTLS status in Kiali graph:

- 🔒 **Lock icon**: mTLS enabled
- 🔓 **Unlocked**: mTLS disabled
- ⚠️ **Warning icon**: Partial mTLS (PERMISSIVE)

**Security Dashboard**:
- mTLS status by namespace
- PeerAuthentication policy application status
- AuthorizationPolicy effects

#### 7. Distributed Tracing Integration

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-jaeger-integration.png" alt="Kiali Jaeger Integration" width="800">
</p>

Kiali integrates with Jaeger to view traces directly from the service graph.

**How to use**:
1. Click a service node in the graph
2. Click "View Traces" link
3. Automatically navigate to Jaeger UI to view traces for that service

**Trace Details**:
- Span duration (processing time for each service)
- Request/Response headers
- Error details
- Service dependency map

### Kiali Advanced Features

#### Traffic Shifting Visualization

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-weighted-routing.png" alt="Kiali Weighted Routing" width="700">
</p>

```yaml
# Canary deployment VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-canary
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # Displayed as 90% in Kiali
    - destination:
        host: reviews
        subset: v2
      weight: 10  # Displayed as 10% in Kiali
```

Kiali graph displays real-time traffic distribution rates as edge labels.

**Canary Deployment Monitoring**:
- Request rate by version (v1: 90%, v2: 10%)
- Error rate comparison by version
- Response time by version (P50, P95, P99)
- Verify distribution with real-time traffic animation

#### Namespace Isolation and Access Control

```yaml
# Kiali with access to specific namespaces only
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali-team-a
  namespace: team-a
spec:
  deployment:
    accessible_namespaces:
    - team-a
    - istio-system
  auth:
    strategy: openid
    openid:
      client_id: kiali-team-a
      issuer_uri: https://keycloak.example.com/auth/realms/kubernetes
```

## Grafana Dashboards

### Official Istio Dashboards

Istio provides the following official Grafana dashboards:

#### 1. Istio Mesh Dashboard

**Purpose**: Overall mesh status overview

**Key Panels**:
- Global Request Volume
- Global Success Rate (non-5xx responses)
- 4xx Response Codes
- 5xx Response Codes
- Average Response Time
- P50/P90/P95/P99 Latency

**Access**:
```bash
# In Grafana UI
Dashboards → Istio → Istio Mesh Dashboard
```

#### 2. Istio Service Dashboard

**Purpose**: Detailed metrics analysis per service

**Key Panels**:
- Service Request Volume
- Service Success Rate
- Service Request Duration (Percentiles)
- Incoming Request By Source
- Outgoing Request By Destination
- Service Workloads

**Variables**:
- `$namespace`: Namespace selection
- `$service`: Service selection

#### 3. Istio Workload Dashboard

**Purpose**: Workload (Deployment/StatefulSet) metrics

**Key Panels**:
- Workload Request Volume
- Workload Success Rate
- Workload Request Duration
- Incoming Requests by Source
- Outgoing Requests by Destination
- TCP Sent/Received Bytes

**Variables**:
- `$namespace`: Namespace
- `$workload`: Workload name

#### 4. Istio Performance Dashboard

**Purpose**: Istio component performance monitoring

**Key Panels**:
- Pilot Metrics
  - Proxy Push Time
  - Pilot XDS Pushes
  - Pilot XDS Errors
- Envoy Proxy Metrics
  - Memory Usage
  - CPU Usage
  - Active Connections

#### 5. Istio Control Plane Dashboard

**Purpose**: istiod status monitoring

**Key Panels**:
- Pilot Memory
- Pilot CPU
- Pilot Goroutines
- Configuration Validation Errors
- Push Queue Depth
- XDS Push Time

### Grafana Loki Dashboard for Istio (#14876)

**Dashboard ID**: 14876
**URL**: https://grafana.com/grafana/dashboards/14876

This dashboard uses Grafana Loki to analyze Istio Access Logs.

#### Installation Method

**1. Import via Grafana UI**:

```bash
# Access Grafana
kubectl port-forward -n observability svc/grafana 3000:3000

# Browser: http://localhost:3000
# 1. Dashboards → Import
# 2. Enter Dashboard ID: 14876
# 3. Select Loki datasource
# 4. Click Import
```

**2. Import via JSON File** (Automation):

```bash
# Download Dashboard JSON
curl -o istio-loki-dashboard.json \
  https://grafana.com/api/dashboards/14876/revisions/latest/download

# Deploy as ConfigMap
kubectl create configmap grafana-dashboard-loki-istio \
  --from-file=istio-loki-dashboard.json \
  -n observability \
  --dry-run=client -o yaml | kubectl apply -f -

# Add label for auto-loading in Grafana
kubectl label configmap grafana-dashboard-loki-istio \
  -n observability \
  grafana_dashboard=1
```

#### Key Panels

**1. Overview Panels**:
- **Total Requests**: Total request count
- **Request Rate**: Requests per second (RPS)
- **Error Rate**: 5xx error rate
- **P95 Latency**: 95th percentile latency

**2. Traffic Analysis**:
- **Top Services by Request Volume**: Services with highest request volume
- **Request Rate by Service**: Request trends by service
- **Response Code Distribution**: HTTP status code distribution

**3. Performance Metrics**:
- **Latency Heatmap**: Response time distribution heatmap
- **P50/P95/P99 Latency**: Latency by percentile
- **Slow Requests**: Slow request list (> 1s)

**4. Error Analysis**:
- **4xx Errors**: Client errors (bad requests)
- **5xx Errors**: Server errors (internal errors)
- **Error Logs**: Error log details

**5. Security**:
- **mTLS Usage**: mTLS usage rate
- **Non-mTLS Traffic**: Non-mTLS traffic warning

#### LogQL Query Examples

LogQL queries used in this dashboard:

```logql
# Request rate
sum(rate({container="istio-proxy"} | json [5m]))

# Error rate
sum(rate({container="istio-proxy"} | json | response_code >= "500" [5m]))
/
sum(rate({container="istio-proxy"} | json [5m]))

# P95 latency
quantile_over_time(0.95, {container="istio-proxy"} | json | unwrap duration [5m])

# Request distribution by service
sum(count_over_time({container="istio-proxy"} | json [5m])) by (destination_service_name)

# Find slow requests
{container="istio-proxy"}
| json
| duration > 1000
| line_format "{{.method}} {{.path}} - {{.duration}}ms"
```

### Additional Community Dashboards

#### Istio Workload Dashboard (#7636)

**URL**: https://grafana.com/grafana/dashboards/7636

Workload-focused metrics:
- Request Volume
- Request Duration
- Request Size
- Response Size
- TCP Connections

**Import**:
```bash
# Dashboard ID: 7636
Dashboards → Import → 7636 → Load
```

#### Istio Service Mesh Dashboard (#11829)

**URL**: https://grafana.com/grafana/dashboards/11829

Overall mesh overview:
- Service Graph data
- Golden Signals (Latency, Traffic, Errors, Saturation)
- Control Plane status

#### Istio Gateway Dashboard (#13277)

**URL**: https://grafana.com/grafana/dashboards/13277

Ingress/Egress Gateway monitoring:
- Gateway Request Volume
- Gateway Latency
- TLS Handshake Errors
- Connection Metrics

### Grafana Alerting

#### Alert Rules for Istio

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-alerting
  namespace: observability
data:
  istio-alerts.yaml: |
    groups:
    - name: istio-service-alerts
      interval: 1m
      rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name)
          /
          sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name))
          * 100 > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate for {{ $labels.destination_service_name }}"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))
            by (destination_service_name, le)
          ) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency for {{ $labels.destination_service_name }}"
          description: "P95 latency is {{ $value }}ms"

      # Circuit Breaker triggered
      - alert: CircuitBreakerTriggered
        expr: |
          rate(istio_requests_total{response_flags=~".*UO.*", reporter="destination"}[1m]) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker triggered for {{ $labels.destination_service_name }}"
          description: "Requests are being rejected by circuit breaker"

      # Non-mTLS traffic
      - alert: NonMTLSTraffic
        expr: |
          sum(rate(istio_requests_total{connection_security_policy="none", reporter="destination"}[5m])) by (source_workload, destination_workload) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Non-mTLS traffic detected"
          description: "{{ $labels.source_workload }} → {{ $labels.destination_workload }} is not using mTLS"
```

## Prometheus

### Production Deployment

#### Using Prometheus Operator

```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: istio
  namespace: istio-system
spec:
  replicas: 2
  retention: 15d
  retentionSize: "50GB"

  serviceAccountName: prometheus
  serviceMonitorSelector:
    matchLabels:
      monitoring: istio

  podMonitorSelector:
    matchLabels:
      monitoring: istio-proxies

  resources:
    requests:
      cpu: 1000m
      memory: 4Gi
    limits:
      cpu: 2000m
      memory: 8Gi

  storage:
    volumeClaimTemplate:
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 100Gi
        storageClassName: gp3

  # Remote Write (long-term storage)
  remoteWrite:
  - url: http://victoria-metrics:8428/api/v1/write
    queueConfig:
      capacity: 10000
      maxShards: 5
      minShards: 1
      maxSamplesPerSend: 5000
```

### Prometheus Query Examples

#### Golden Signals

```promql
# 1. Latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    reporter="destination"
  }[5m])) by (destination_service_name, le)
)

# 2. Traffic
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name)

# 3. Errors (error rate)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name)
* 100

# 4. Saturation
envoy_cluster_upstream_cx_active / envoy_cluster_circuit_breakers_default_cx_max * 100
```

## Creating Custom Dashboards

### Grafana Dashboard JSON Template

```json
{
  "dashboard": {
    "title": "Custom Istio Service Dashboard",
    "tags": ["istio", "custom"],
    "timezone": "browser",
    "schemaVersion": 38,
    "version": 1,

    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total{destination_service_name=\"$service\"}[5m])) by (response_code)",
            "legendFormat": "{{ response_code }}",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {"mode": "palette-classic"},
            "custom": {
              "drawStyle": "line",
              "lineInterpolation": "linear",
              "fillOpacity": 10
            },
            "unit": "reqps"
          }
        }
      },

      {
        "id": 2,
        "title": "P95 Latency",
        "type": "gauge",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket{destination_service_name=\"$service\"}[5m])) by (le))",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "ms",
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 500, "color": "yellow"},
                {"value": 1000, "color": "red"}
              ]
            },
            "max": 2000
          }
        },
        "options": {
          "showThresholdLabels": true,
          "showThresholdMarkers": true
        }
      },

      {
        "id": 3,
        "title": "Error Rate",
        "type": "stat",
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total{destination_service_name=\"$service\", response_code=~\"5..\"}[5m])) / sum(rate(istio_requests_total{destination_service_name=\"$service\"}[5m])) * 100",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 1, "color": "yellow"},
                {"value": 5, "color": "red"}
              ]
            }
          }
        }
      },

      {
        "id": 4,
        "title": "Request by Source",
        "type": "table",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total{destination_service_name=\"$service\"}[5m])) by (source_workload, response_code)",
            "format": "table",
            "instant": true,
            "refId": "A"
          }
        ],
        "transformations": [
          {
            "id": "organize",
            "options": {
              "excludeByName": {"Time": true},
              "indexByName": {
                "source_workload": 0,
                "response_code": 1,
                "Value": 2
              },
              "renameByName": {
                "source_workload": "Source",
                "response_code": "Code",
                "Value": "RPS"
              }
            }
          }
        ]
      },

      {
        "id": 5,
        "title": "Circuit Breaker Status",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total{destination_service_name=\"$service\", response_flags=~\".*UO.*\"}[5m]))",
            "legendFormat": "Circuit Breaker Open",
            "refId": "A"
          },
          {
            "expr": "sum(rate(istio_requests_total{destination_service_name=\"$service\", response_flags=~\".*URX.*\"}[5m]))",
            "legendFormat": "Rejected by CB",
            "refId": "B"
          }
        ]
      }
    ],

    "templating": {
      "list": [
        {
          "name": "namespace",
          "type": "query",
          "query": "label_values(istio_requests_total, destination_service_namespace)",
          "datasource": "Prometheus",
          "current": {"selected": true, "text": "default", "value": "default"},
          "multi": false
        },
        {
          "name": "service",
          "type": "query",
          "query": "label_values(istio_requests_total{destination_service_namespace=\"$namespace\"}, destination_service_name)",
          "datasource": "Prometheus",
          "current": {},
          "multi": false
        }
      ]
    },

    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### Automatic Dashboard Deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-custom-istio
  namespace: observability
  labels:
    grafana_dashboard: "1"
data:
  custom-istio-service.json: |
    {
      "dashboard": {
        "title": "Custom Istio Service Dashboard",
        ...
      }
    }
```

**Grafana Configuration**:
```yaml
# Grafana Deployment sidecar configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  template:
    spec:
      containers:
      - name: grafana-sc-dashboard
        image: quay.io/kiwigrid/k8s-sidecar:1.25.2
        env:
        - name: LABEL
          value: "grafana_dashboard"
        - name: FOLDER
          value: "/tmp/dashboards"
        - name: NAMESPACE
          value: "ALL"
        volumeMounts:
        - name: sc-dashboard-volume
          mountPath: /tmp/dashboards
```

## Dashboard Integration

### Kiali → Grafana Link

One-click navigation from Kiali to Grafana dashboards:

```yaml
# Kiali CR configuration
external_services:
  grafana:
    enabled: true
    url: http://grafana.observability:3000
    dashboards:
    - name: "Istio Service Dashboard"
      variables:
        namespace: "var-namespace"
        service: "var-service"
    - name: "Istio Workload Dashboard"
      variables:
        namespace: "var-namespace"
        workload: "var-workload"
```

**How to use**:
1. Click a service in Kiali
2. Click "View in Grafana" link in the "Metrics" tab
3. Automatically navigate to Grafana dashboard (namespace, service variables auto-configured)

### Grafana → Jaeger Link

Navigate from logs/metrics in Grafana to traces:

```yaml
# Prometheus datasource configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      jsonData:
        exemplarTraceIdDestinations:
        - datasourceUid: jaeger
          name: TraceID
          urlDisplayLabel: "View Trace"
```

### Loki → Tempo Integration

Jump from logs to traces:

```yaml
# Loki datasource configuration
apiVersion: 1
datasources:
- name: Loki
  type: loki
  jsonData:
    derivedFields:
    - datasourceUid: tempo
      matcherRegex: '"request_id":"([^"]+)"'
      name: TraceID
      url: '$${__value.raw}'
      urlDisplayLabel: 'View Trace'
```

## Best Practices

### 1. Dashboard Organization

```
Grafana Folder Structure:
├── Istio/
│   ├── Overview/
│   │   ├── Istio Mesh Dashboard
│   │   └── Istio Control Plane Dashboard
│   ├── Services/
│   │   ├── Istio Service Dashboard
│   │   └── Custom Service Dashboards
│   ├── Workloads/
│   │   └── Istio Workload Dashboard
│   ├── Gateways/
│   │   └── Istio Gateway Dashboard
│   └── Logs/
│       ├── Loki Istio Dashboard (#14876)
│       └── Access Log Analysis
```

### 2. Variable Usage

Use consistent variables across all dashboards:

```json
{
  "templating": {
    "list": [
      {"name": "datasource", "type": "datasource"},
      {"name": "namespace", "type": "query"},
      {"name": "service", "type": "query"},
      {"name": "workload", "type": "query"},
      {"name": "interval", "type": "interval", "auto": true}
    ]
  }
}
```

### 3. Alert Management

- **Tiered Alerting**: Critical (PagerDuty) → Warning (Slack) → Info (Email)
- **Alert Grouping**: Group by service, namespace
- **Silencing Rules**: Mute alerts during maintenance

### 4. Performance Optimization

```yaml
# Grafana configuration
[dashboards]
min_refresh_interval = 10s

[panels]
disable_sanitize_html = false

[dataproxy]
timeout = 30
```

**Query Optimization**:
- Use Recording Rules to pre-compute frequently used queries
- Use `$__interval` variable for dynamic time range adjustment
- Use `increase()` instead of `rate()` (when counter doesn't reset)

### 5. Access Control

```yaml
# Grafana RBAC
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
data:
  grafana.ini: |
    [auth]
    disable_login_form = false

    [auth.anonymous]
    enabled = false

    [auth.basic]
    enabled = true

    [users]
    allow_sign_up = false
    auto_assign_org = true
    auto_assign_org_role = Viewer

    [security]
    admin_user = admin
    admin_password = ${GF_SECURITY_ADMIN_PASSWORD}
```

### 6. Backup and Recovery

```bash
# Grafana dashboard backup
kubectl exec -n observability grafana-xxx -- \
  grafana-cli admin export-dashboard > dashboards-backup.json

# Prometheus data backup
kubectl exec -n istio-system prometheus-xxx -- \
  promtool tsdb snapshot /prometheus
```

## References

### Official Documentation
- [Kiali Documentation](https://kiali.io/docs/)
- [Istio Observability](https://istio.io/latest/docs/tasks/observability/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [Prometheus Operator](https://prometheus-operator.dev/)

### Community Dashboards
- [Grafana Loki Dashboard for Istio (#14876)](https://grafana.com/grafana/dashboards/14876)
- [Istio Workload Dashboard (#7636)](https://grafana.com/grafana/dashboards/7636)
- [Istio Service Mesh Dashboard (#11829)](https://grafana.com/grafana/dashboards/11829)
- [Istio Gateway Dashboard (#13277)](https://grafana.com/grafana/dashboards/13277)

### Reference Materials
- [Kiali Architecture](https://kiali.io/docs/architecture/architecture/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
