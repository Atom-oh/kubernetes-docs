# Flagger Progressive Delivery

> **Supported Versions**: Flagger v1.38+, Flux v2.4+
> **Last Updated**: June 2025

Flagger is a progressive delivery operator for Kubernetes that automates the promotion of canary deployments using service mesh routing, ingress controllers, or Gateway API for traffic shifting and Prometheus metrics for canary analysis. Originally created by Weaveworks and now a CNCF project under the Flux family, Flagger reduces the risk of introducing new software versions in production by gradually shifting traffic to a new version while measuring key performance indicators and automatically rolling back if anomalies are detected.

## Table of Contents

- [Overview and Learning Objectives](#overview-and-learning-objectives)
- [Flagger Architecture](#flagger-architecture)
- [EKS Installation and Configuration](#eks-installation-and-configuration)
- [Canary Deployment Strategy](#canary-deployment-strategy)
- [Blue-Green Deployment Strategy](#blue-green-deployment-strategy)
- [A/B Testing Strategy](#ab-testing-strategy)
- [Custom Metrics and Webhooks](#custom-metrics-and-webhooks)
- [GitOps Integration (Flux + Flagger)](#gitops-integration-flux--flagger)
- [Observability and Alerting](#observability-and-alerting)
- [Production Best Practices](#production-best-practices)
- [References](#references)

---

## Overview and Learning Objectives

### Learning Objectives

After completing this document, you will be able to:

1. Explain progressive delivery strategies (Canary, Blue-Green, A/B Testing) and when to use each
2. Deploy and configure Flagger on Amazon EKS with various mesh and ingress providers
3. Define Canary resources with custom metrics analysis and automated rollback conditions
4. Implement Blue-Green deployments with traffic mirroring and manual gating
5. Configure A/B testing with header-based and cookie-based routing
6. Integrate Flagger with FluxCD for fully automated GitOps progressive delivery pipelines
7. Set up observability dashboards and alerting for Flagger deployments

### What is Progressive Delivery?

Progressive delivery is an umbrella term for advanced deployment strategies that enable controlled, gradual rollout of changes to a subset of users before making them available to the entire user base. Unlike traditional rolling updates that replace all pods simultaneously, progressive delivery provides fine-grained control over traffic distribution, real-time analysis, and automated rollback.

The three primary progressive delivery strategies are:

| Strategy | Traffic Control | Use Case | Complexity |
|----------|----------------|----------|------------|
| **Canary** | Percentage-based weight shifting | General-purpose, gradual rollout | Medium |
| **Blue-Green** | Full switch between two environments | Zero-downtime, instant rollback | Low |
| **A/B Testing** | Header/cookie-based routing | Feature testing with specific user segments | High |

### Flagger vs Argo Rollouts

Both Flagger and Argo Rollouts solve the progressive delivery problem for Kubernetes, but they take fundamentally different approaches:

| Feature | Flagger | Argo Rollouts |
|---------|---------|---------------|
| **Ecosystem** | Flux / CNCF | Argo / CNCF |
| **Resource Model** | Wraps native Deployment/DaemonSet | Replaces Deployment with Rollout CRD |
| **Traffic Providers** | Istio, Linkerd, Contour, Nginx, Gateway API, AWS App Mesh, Gloo, Traefik | Istio, Nginx, ALB, SMI, Gateway API |
| **Metrics Analysis** | Built-in Prometheus, Datadog, CloudWatch, custom webhooks | Built-in AnalysisTemplate with multiple providers |
| **GitOps Integration** | Native Flux integration | Native Argo CD integration |
| **Webhook Support** | Pre/post-rollout, rollout, confirm-rollout, load-test | Pre/post analysis, anti-affinity |
| **Blue-Green** | Supported via Canary CRD | First-class Rollout strategy |
| **A/B Testing** | Supported via Canary CRD with headers | Supported via Experiment CRD |
| **CNCF Status** | Incubating (Flux family) | Graduated (Argo family) |
| **Adoption Pattern** | Additive (no Deployment changes) | Replacement (Rollout replaces Deployment) |

**Key Differentiator**: Flagger does not require you to change your existing Deployment resources. It creates primary and canary CloneSet variants automatically and manages traffic shifting through the mesh/ingress layer. Argo Rollouts requires replacing your `Deployment` kind with a `Rollout` kind.

### Flagger in the Flux Ecosystem

Flagger is designed as the progressive delivery component of the Flux GitOps toolkit:

![Flux's source, kustomize, helm, notification and image-automation controllers reconcile Kubernetes deployments from a Git repository, while Flagger watches those deployments, queries Prometheus, and manages the Services and routes used for progressive delivery.](../../assets/diagrams/rendered/en-gitops-04-flagger-0.svg)

---

## Flagger Architecture

### Control Loop

Flagger implements a control loop that progressively advances a new version of an application by analyzing metrics, running conformance tests, and managing traffic routing. The core reconciliation loop is:

![A canary progresses from initialized through step-wise traffic increases to waiting for promotion, promoting, and finalising into a successful rollout, or diverts to a failed state and rolls back to initialized if metrics or a timeout fail along the way.](../../assets/diagrams/rendered/en-gitops-04-flagger-1.svg)

### Detailed Control Loop Steps

When a change is detected in the target workload (e.g., a new container image), Flagger executes the following sequence:

1. **Detect Change**: Flagger watches the target Deployment for spec changes (image tag, environment variables, resources, etc.)
2. **Initialize Canary**: Scale up the canary Deployment with the new version; the primary retains the old version
3. **Run Pre-Rollout Webhooks**: Execute conformance tests, smoke tests, or other pre-conditions
4. **Shift Traffic**: Incrementally increase the canary traffic weight according to `stepWeight` and `maxWeight`
5. **Analyze Metrics**: Query Prometheus (or other providers) for success rate, latency, and custom metrics
6. **Advance or Rollback**: If metrics pass thresholds, advance to the next step; otherwise initiate rollback
7. **Confirm Promotion**: Optionally wait for manual gate approval via webhook
8. **Promote**: Copy canary spec to primary, scale down canary, route all traffic to primary
9. **Send Notifications**: Alert via Slack, Teams, or other configured providers

### Mesh and Ingress Provider Support

Flagger supports a wide range of traffic management providers, each with different capabilities:

| Provider | Canary | Blue-Green | A/B Testing | Mirroring | Gateway API |
|----------|--------|------------|-------------|-----------|-------------|
| **Istio** | Yes | Yes | Yes | Yes | Yes |
| **Linkerd** | Yes | Yes | No | No | Yes |
| **AWS App Mesh** | Yes | Yes | No | No | No |
| **Contour** | Yes | Yes | Yes | No | Yes |
| **Nginx Ingress** | Yes | Yes | Yes | No | No |
| **Gloo Edge** | Yes | Yes | No | No | No |
| **Traefik** | Yes | Yes | No | No | No |
| **Gateway API** | Yes | Yes | Yes | No | Yes |
| **Kuma** | Yes | Yes | No | No | No |
| **Open Service Mesh** | Yes | Yes | No | No | No |

### Prometheus Metrics Analysis

Flagger's metrics analysis engine queries Prometheus to evaluate whether a canary release is healthy. The two built-in metrics are:

- **request-success-rate**: The percentage of successful HTTP requests (non-5xx) over the analysis interval
- **request-duration**: The P99 latency of HTTP requests over the analysis interval

Both metrics are derived from the service mesh or ingress controller's Prometheus metrics (e.g., `istio_requests_total`, `istio_request_duration_milliseconds_bucket`).

![Flagger shifts a slice of traffic to the canary pod through the mesh, then queries Prometheus for success rate and latency against thresholds before advancing the traffic weight.](../../assets/diagrams/rendered/en-gitops-04-flagger-2.svg)

---

## EKS Installation and Configuration

### Prerequisites

Before installing Flagger on Amazon EKS, ensure the following prerequisites are met:

- An Amazon EKS cluster running Kubernetes v1.27+
- Helm v3.12+ installed
- A service mesh (Istio) or ingress controller (Nginx, Contour) deployed
- Prometheus stack deployed (kube-prometheus-stack recommended)
- FluxCD v2.4+ bootstrapped (for GitOps integration)

### Helm Installation with Prometheus

Install Flagger using Helm with Prometheus metrics server enabled:

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

For EKS with IRSA (IAM Roles for Service Accounts), configure the service account:

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

### Install Flagger Loadtester

The Flagger loadtester is a companion tool for running automated load tests and webhooks during canary analysis:

```bash
helm upgrade -i flagger-loadtester flagger/loadtester \
  --namespace flagger-system \
  --set cmd.timeout=1h \
  --set resources.requests.cpu=100m \
  --set resources.requests.memory=64Mi
```

### Istio Provider Configuration

When using Istio as the mesh provider, Flagger automatically manages VirtualService and DestinationRule resources:

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

Verify that Istio sidecar injection is enabled for the target namespace:

```bash
kubectl label namespace production istio-injection=enabled
kubectl get namespace production --show-labels
```

### Gateway API Provider Configuration

Flagger supports Kubernetes Gateway API as a provider, enabling progressive delivery without a full service mesh:

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

Create the Gateway resource that Flagger will reference:

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

### Slack and Teams Notification Setup

Flagger can send deployment notifications to Slack, Microsoft Teams, and other providers using the AlertProvider CRD:

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

Multiple alert providers can be referenced in a Canary resource:

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

## Canary Deployment Strategy

### Canary CRD Detailed Explanation

The Canary CRD is Flagger's primary resource for defining progressive delivery strategies. It references a target Deployment and specifies how traffic should be shifted, what metrics to analyze, and when to rollback.

**Core structure of the Canary resource:**

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

### Step-by-Step Traffic Shifting

Flagger manages canary traffic shifting through two key parameters:

- **`stepWeight`**: The percentage of traffic to add to the canary at each analysis interval
- **`maxWeight`**: The maximum percentage of traffic the canary receives before promotion

For example, with `stepWeight: 10` and `maxWeight: 50`:

```
Step 1: Canary 10%, Primary 90%  ->  Analyze metrics
Step 2: Canary 20%, Primary 80%  ->  Analyze metrics
Step 3: Canary 30%, Primary 70%  ->  Analyze metrics
Step 4: Canary 40%, Primary 60%  ->  Analyze metrics
Step 5: Canary 50%, Primary 50%  ->  Analyze metrics
Step 6: Promote -> Canary spec copied to Primary, all traffic to Primary
```

![Canary traffic weight climbs in five steps from 10% to 50% before promotion to 100%, and at each step Flagger analyzes the request success rate and P99 duration and runs any configured webhooks.](../../assets/diagrams/rendered/en-gitops-04-flagger-3.svg)

You can also define non-linear traffic stepping with `stepWeights` (an array):

```yaml
analysis:
  stepWeights: [1, 2, 5, 10, 25, 50, 80]
  # Traffic progression: 1% -> 2% -> 5% -> 10% -> 25% -> 50% -> 80% -> promote
```

### Metrics Analysis

Flagger's built-in metrics rely on the service mesh or ingress controller to expose Prometheus metrics:

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

The `interval` field determines how often Flagger queries Prometheus during each analysis step. The `thresholdRange` specifies the acceptable boundaries:

- `min`: The metric value must be **greater than or equal** to this value (e.g., success rate >= 99%)
- `max`: The metric value must be **less than or equal** to this value (e.g., latency <= 500ms)

### Automatic Rollback Conditions

Flagger automatically rolls back a canary deployment when:

1. **Metric failure threshold exceeded**: A metric check fails more times than `threshold` within an analysis step
2. **Progress deadline exceeded**: The canary does not progress within `progressDeadlineSeconds`
3. **Webhook failure**: A pre-rollout or rollout webhook returns a non-2xx status

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

When a rollback occurs, Flagger:
1. Routes all traffic back to the primary (old version)
2. Scales the canary to zero
3. Sets the Canary status to `Failed`
4. Sends alert notifications

### Complete Canary YAML Example

The following is a production-ready Canary resource for a web application deployed on EKS with Istio:

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

This Canary resource will:
1. Watch the `web-app` Deployment for changes
2. Create `web-app-primary` and `web-app-canary` Deployments
3. Create `web-app`, `web-app-primary`, and `web-app-canary` ClusterIP Services
4. Create an Istio VirtualService for traffic routing
5. Run a smoke test before starting the rollout
6. Shift traffic 10% at a time up to 50%
7. Run load tests during each analysis step
8. Check request success rate (>= 99%) and P99 latency (<= 500ms)
9. Rollback if 5 consecutive metric checks fail
10. Promote by copying canary spec to primary after all steps pass

**Monitoring a canary deployment:**

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

## Blue-Green Deployment Strategy

### Blue-Green Canary CRD

Flagger supports Blue-Green deployments through the same Canary CRD by omitting `stepWeight` and `maxWeight` and using `iterations` to define how many analysis cycles to run before switching traffic from the old (blue) version to the new (green) version.

In Blue-Green mode:
- The canary receives no live traffic during analysis (unless mirroring is enabled)
- Flagger runs metric checks against the canary using the load tester or mirrored traffic
- After all iterations pass, traffic is switched 100% from primary to canary in a single step
- If any iteration fails, the canary is scaled down with no impact on production traffic

![Flagger deploys a green canary, drives synthetic load through it in repeated analysis iterations, then switches all user traffic to green, updates the primary spec, and scales the old canary down.](../../assets/diagrams/rendered/en-gitops-04-flagger-4.svg)

### Mirror Traffic

When using Istio, Flagger can mirror production traffic to the canary during Blue-Green analysis. Mirrored traffic is fire-and-forget; the response from the canary is discarded, ensuring zero impact on users:

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

### Manual Gating

For high-risk deployments, you can require manual approval before Flagger promotes the canary. This is achieved via a confirm-rollout webhook that Flagger queries at each step:

```yaml
spec:
  analysis:
    webhooks:
    - name: confirm-promotion
      type: confirm-promotion
      url: http://flagger-loadtester.flagger-system/gate/approve
```

To manually approve or reject:

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

### Complete Blue-Green YAML Example

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

## A/B Testing Strategy

### Header and Cookie-Based Routing

A/B testing in Flagger uses HTTP headers or cookies to route specific users to the canary version. Unlike canary deployments that use weighted routing, A/B testing ensures deterministic routing based on request attributes.

This strategy is ideal for:
- Feature flag testing with specific user segments
- Regional rollouts based on request headers
- Internal testing before public release
- Measuring business metrics (conversion rate, engagement) for specific user cohorts

### Istio VirtualService Integration

When using Istio, Flagger generates VirtualService rules that match on HTTP headers or cookies:

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

The resulting Istio VirtualService will look like:

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

### Metrics-Based Automatic Promotion

During A/B testing, Flagger still performs metrics analysis on the canary traffic. After the configured number of `iterations` pass with all metrics within their thresholds, Flagger automatically promotes the canary:

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

## Custom Metrics and Webhooks

### Prometheus Custom Metric Queries

Beyond the two built-in metrics, Flagger supports custom Prometheus queries through the MetricTemplate CRD. This allows you to analyze any Prometheus metric during canary deployments:

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

Reference custom metrics in the Canary analysis:

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

### Datadog Metrics Provider

Flagger supports Datadog as an external metrics provider:

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

### CloudWatch Metrics Provider

For Amazon CloudWatch metrics on EKS:

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

Ensure the Flagger service account has the appropriate IAM permissions to query CloudWatch:

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

### Pre/Post Rollout Webhooks

Flagger supports several webhook types that execute at different phases of the rollout:

| Webhook Type | When Executed | Use Case |
|-------------|---------------|----------|
| `confirm-rollout` | Before traffic shifting starts | Gate: require external approval |
| `pre-rollout` | Before each analysis step | Smoke tests, conformance tests |
| `rollout` | During each analysis step | Load testing, synthetic traffic |
| `confirm-promotion` | Before final promotion | Manual gate, business approval |
| `post-rollout` | After promotion or rollback | Cleanup, notification, audit |
| `rollback` | After a failed rollout | Incident notification, cleanup |
| `event` | On every Flagger event | Audit logging |

### Webhook YAML Examples

**Load testing webhook with hey:**

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

**Conformance test with bash:**

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

**Load testing with Grafana k6:**

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

**Post-rollout cleanup webhook:**

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

**External webhook for manual gating:**

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

## GitOps Integration (Flux + Flagger)

### FluxCD HelmRelease + Flagger Canary Workflow

The most powerful pattern is combining Flux HelmRelease for application deployment with Flagger Canary for progressive delivery. Flux manages the desired state from Git, and Flagger manages how changes are rolled out.

![A developer's image push flows through Flux's controllers into a HelmRelease change that Flagger picks up, runs a canary analysis against, and then either promotes to primary or rolls back, notifying the developer either way.](../../assets/diagrams/rendered/en-gitops-04-flagger-5.svg)

**Repository structure for Flux + Flagger:**

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

**Flux HelmRelease for the application:**

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

**Flagger Canary resource alongside the HelmRelease:**

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

### Kustomization-Based Deployment

For teams using Flux Kustomizations instead of HelmReleases:

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

### Image Automation + Canary Automation Pipeline

The fully automated pipeline uses Flux Image Automation to detect new container images, commit the updated tag to Git, and let Flagger handle the progressive rollout:

![A new image built and pushed to ECR is picked up by Flux's image automation controllers, which commit an updated manifest that Kustomize applies, and Flagger's metrics analysis then promotes the resulting canary to primary or leaves it in place.](../../assets/diagrams/rendered/en-gitops-04-flagger-6.svg)

**Flux Image Automation resources:**

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

Mark the image field in the Deployment with a setter comment:

```yaml
# apps/web-app/deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: web-app
        image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app:v1.0.0 # {"$imagepolicy": "flux-system:web-app"}
```

When a new image (e.g., `v2.0.0`) is pushed to ECR:
1. Flux Image Repository scans ECR and detects the new tag
2. Flux Image Policy selects `v2.0.0` based on the semver range
3. Flux Image Update Automation commits the new tag to Git
4. Flux Kustomize Controller applies the updated Deployment
5. Flagger detects the Deployment change and begins the canary rollout
6. Flagger progressively shifts traffic, analyzes metrics, and promotes or rolls back

---

## Observability and Alerting

### Grafana Dashboard (Flagger Metrics)

Flagger exports Prometheus metrics that can be visualized in Grafana. The key metrics are:

| Metric | Type | Description |
|--------|------|-------------|
| `flagger_canary_status` | Gauge | Canary status (0=Initialized, 1=Progressing, 2=WaitingPromotion, 3=Promoting, 4=Finalising, 5=Succeeded, 6=Failed) |
| `flagger_canary_weight` | Gauge | Current canary traffic weight |
| `flagger_canary_total` | Counter | Total number of canary analyses |
| `flagger_canary_duration_seconds` | Histogram | Duration of canary analysis in seconds |
| `flagger_canary_metric_analysis` | Gauge | Result of the last metric analysis (1=pass, 0=fail) |

**Import the official Flagger Grafana dashboard:**

```bash
# The official Flagger dashboard ID for Grafana is 16527
# Import via Grafana UI: Dashboards > Import > Enter 16527
```

**Custom Grafana dashboard JSON model (simplified):**

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

### Prometheus Alert Rules

Configure Prometheus alerting rules for Flagger canary failures:

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

### Slack and Teams Notification Configuration

Configure comprehensive alerting with severity-based routing:

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

Reference multiple providers with different severities in the Canary:

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

### Deployment History Tracking

Track deployment history through Flagger events and Kubernetes events:

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

For long-term deployment history, integrate with Flux Notification Controller to forward events to an external system:

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

## Production Best Practices

### Incremental Adoption Strategy

Adopt Flagger progressively across your organization:

**Phase 1: Non-Critical Services**
- Start with internal tools or staging environments
- Use conservative analysis settings (high thresholds, many iterations)
- Validate metrics collection and webhook integration

**Phase 2: Low-Risk Production Services**
- Apply to production services with low blast radius
- Configure alerting and notification channels
- Establish runbooks for manual intervention

**Phase 3: Mission-Critical Services**
- Apply to high-traffic, customer-facing services
- Use manual gating for additional safety
- Implement custom metrics specific to business KPIs

**Phase 4: Organization-Wide Rollout**
- Standardize Canary templates across teams
- Build self-service platform with Flux + Flagger
- Automate end-to-end image-to-production pipelines

### Metrics Threshold Tuning

Choosing the right metric thresholds is critical for balancing deployment speed against safety:

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

**Guidelines for threshold tuning:**

| Parameter | Conservative | Balanced | Aggressive |
|-----------|-------------|----------|------------|
| `interval` | 2m | 1m | 30s |
| `stepWeight` | 5 | 10 | 20 |
| `maxWeight` | 30 | 50 | 80 |
| `threshold` (failures) | 3 | 5 | 10 |
| Success Rate Min | 99.9% | 99% | 95% |
| Latency P99 Max | 200ms | 500ms | 1000ms |
| Total Rollout Time | ~20 min | ~10 min | ~4 min |

### Rollback Strategies

Understanding rollback behavior is essential for production operations:

**Automatic Rollback** (default behavior):
- Flagger detects metric failures exceeding the threshold
- All traffic is immediately routed back to the primary
- Canary pods are scaled to zero
- Status is set to `Failed`

**Manual Rollback**:
```bash
# Force a rollback by setting the skipAnalysis annotation
kubectl annotate canary web-app -n production \
  flagger.app/rollback="true"

# Skip analysis for emergency deploys (not recommended for production)
kubectl annotate canary web-app -n production \
  flagger.app/skipAnalysis="true"
```

**Rollback Webhook** for automated incident response:

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

### Multi-Cluster Flagger

For organizations running multiple EKS clusters, Flagger can be deployed in a hub-and-spoke pattern:

![A single management cluster's Flux controllers read one Git repository and apply the same Kustomization to three production clusters in different regions, each running its own Flagger, Istio, and web-app canary.](../../assets/diagrams/rendered/en-gitops-04-flagger-7.svg)

**Key considerations for multi-cluster Flagger:**

1. **Independent Flagger instances**: Deploy Flagger in each cluster; it only manages local resources
2. **Shared Canary definitions**: Use Flux Kustomizations with overlays for cluster-specific configuration
3. **Sequential rollouts**: Use Flux dependencies to roll out to staging before production clusters
4. **Centralized observability**: Aggregate Flagger metrics from all clusters to a central Prometheus/Thanos/Mimir

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

### Additional Best Practices

1. **Always run load tests during canary analysis.** Without traffic to the canary, Prometheus has no metrics to analyze. Use the Flagger loadtester or generate synthetic traffic.

2. **Set `progressDeadlineSeconds` appropriately.** This is your safety net. If the canary cannot progress within this time, it is automatically rolled back. Set it to at least 2x your expected total rollout time.

3. **Use `skipAnalysis` sparingly.** While it allows emergency deploys, it bypasses all safety checks. Prefer manual gating for urgent changes that still need basic validation.

4. **Pin Flagger and provider versions.** Use specific Helm chart versions in your Flux HelmRelease to avoid unexpected behavior from auto-upgrades.

5. **Test rollback behavior regularly.** Deploy known-bad versions in staging to verify that Flagger correctly detects failures and rolls back.

6. **Separate Canary definitions from Deployments in Git.** This keeps your Deployment resources clean and portable, with progressive delivery concerns isolated in Canary resources.

7. **Use namespace-scoped AlertProviders.** This prevents webhook credential leakage across namespaces and supports multi-tenant environments.

8. **Monitor Flagger controller health.** Set up alerts for Flagger pod restarts, high memory usage, and reconciliation errors.

---

## References

### Official Documentation

- [Flagger Official Documentation](https://docs.flagger.app/)
- [Flagger GitHub Repository](https://github.com/fluxcd/flagger)
- [Flagger Helm Chart](https://artifacthub.io/packages/helm/flagger/flagger)
- [FluxCD Official Documentation](https://fluxcd.io/docs/)
- [Flagger FAQ](https://docs.flagger.app/faq)

### Related Internal Documentation

| Topic | Link |
|-------|------|
| FluxCD | [FluxCD GitOps](./02-fluxcd.md) |
| GitOps Tools Comparison | [ArgoCD vs FluxCD vs Others](./03-gitops-comparison.md) |
| ArgoCD | [ArgoCD Documentation](./argocd/README.md) |
| Istio Traffic Splitting | [Traffic Splitting](../service-mesh/istio/traffic-management/04-traffic-splitting.md) |
| Argo Rollouts + Istio | [Argo Rollouts Integration](../service-mesh/istio/advanced/08-argo-rollouts.md) |
| Prometheus | [Prometheus Monitoring](../observability/metrics/01-prometheus.md) |
| Grafana | [Grafana Dashboards](../observability/grafana/README.md) |
| Gateway API | [Gateway API](../networking/04-gateway-api.md) |
| KEDA Autoscaling | [KEDA](../autoscaling/01-keda.md) |

### External Resources

- [Progressive Delivery with Flagger (CNCF Webinar)](https://www.cncf.io/online-programs/progressive-delivery-with-flagger/)
- [GitOps and Progressive Delivery with Flux and Flagger](https://fluxcd.io/blog/)
- [Canary Deployments with Flagger and Istio](https://docs.flagger.app/tutorials/istio-progressive-delivery)
- [Flagger on AWS App Mesh](https://docs.flagger.app/tutorials/appmesh-progressive-delivery)
- [Gateway API Canary Deployments](https://docs.flagger.app/tutorials/gatewayapi-progressive-delivery)

---

## Navigation

| Previous | Up | Next |
|----------|----|----- |
| [GitOps Tools Comparison](./03-gitops-comparison.md) | [GitOps Overview](./README.md) | None |
