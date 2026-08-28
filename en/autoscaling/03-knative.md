# Knative

> **Supported Versions**: Knative v1.16+, Kourier v1.16+
> **Last Updated**: June 2025

## Table of Contents

- [Overview and Learning Objectives](#overview-and-learning-objectives)
- [Knative Architecture](#knative-architecture)
- [EKS Installation and Configuration](#eks-installation-and-configuration)
- [Knative Serving Deep Dive](#knative-serving-deep-dive)
- [Knative Eventing Deep Dive](#knative-eventing-deep-dive)
- [KEDA vs Knative Comparison](#keda-vs-knative-comparison)
- [Production Operations](#production-operations)
- [Best Practices](#best-practices)
- [References](#references)

---

## Overview and Learning Objectives

### What Is Knative?

Knative is a **CNCF Graduated** project that extends Kubernetes to provide a set of middleware components for building, deploying, and managing modern serverless workloads. Rather than replacing Kubernetes primitives, Knative builds on top of them, offering higher-level abstractions that simplify common patterns such as request-driven autoscaling, event delivery, and traffic management.

Knative consists of two independently installable components:

- **Knative Serving** -- Manages the lifecycle of serverless workloads. It automates deployment, scaling (including scale-to-zero), revision tracking, and traffic routing.
- **Knative Eventing** -- Provides infrastructure for producing, routing, and consuming events following the CloudEvents specification. It decouples event producers from consumers, enabling loosely coupled, event-driven architectures.

### Serverless on Kubernetes

Traditional Kubernetes Deployments require operators to pre-configure replica counts, HPA thresholds, and resource budgets. Knative shifts this burden:

1. Workloads automatically scale from zero to many replicas based on incoming request concurrency or RPS.
2. Revisions capture immutable snapshots of each deployment, allowing instant rollbacks and gradual traffic shifts.
3. Event sources and triggers allow reactive architectures without polling or custom glue code.

The result is a platform that retains the full power of Kubernetes (scheduling, RBAC, networking, storage) while providing a developer experience closer to that of a fully managed serverless platform.

### Knative Serving vs Eventing

| Aspect | Knative Serving | Knative Eventing |
|--------|----------------|-----------------|
| Primary purpose | Request-driven workload lifecycle | Event routing and delivery |
| Scaling trigger | HTTP request concurrency / RPS | Event volume (via Broker/Trigger) |
| Scale-to-zero | Yes (built-in) | Depends on consumer (Serving-backed consumers can) |
| Core resources | Service, Configuration, Revision, Route | Broker, Trigger, Channel, Subscription, Source |
| Typical use case | APIs, web apps, microservices | Async pipelines, webhooks, CDC streams |

### Knative vs AWS Lambda and AWS Fargate

| Feature | Knative on EKS | AWS Lambda | AWS Fargate |
|---------|---------------|------------|-------------|
| Runtime environment | Any OCI container | Lambda runtimes or container images | Any OCI container |
| Maximum execution time | No hard limit | 15 minutes | No hard limit |
| Scale-to-zero | Yes | Yes | No (minimum tasks) |
| Cold start control | Configurable (minScale, initialScale) | Limited (SnapStart, provisioned concurrency) | N/A |
| Custom networking | Full VPC / CNI control | VPC attachment required | VPC native |
| GPU support | Yes (via node selectors) | No | No |
| Event sources | CloudEvents, Kafka, SQS, custom | Native AWS event sources | N/A (pull-based) |
| Vendor lock-in | Low (CNCF standard, portable) | High (AWS proprietary) | Medium (ECS/Fargate API) |
| Kubernetes-native | Yes | No | Partially (EKS on Fargate) |
| Observability | Prometheus, OpenTelemetry, any k8s tooling | CloudWatch, X-Ray | CloudWatch, X-Ray |
| Cost model | Cluster resources consumed | Per-invocation + duration | Per vCPU/memory-second |

### Learning Objectives

By the end of this document you will be able to:

1. Explain Knative's architecture and how Serving and Eventing complement each other.
2. Install and configure Knative on Amazon EKS with Kourier, DNS, and TLS.
3. Deploy serverless workloads with fine-grained concurrency-based autoscaling.
4. Implement traffic splitting strategies (canary, blue-green) using Revisions and Routes.
5. Build event-driven pipelines with Brokers, Triggers, and CloudEvents.
6. Compare KEDA and Knative and decide when to use each (or both).
7. Operate Knative in production with monitoring, high availability, and garbage collection policies.

---

## Knative Architecture

### Serving Architecture

Knative Serving deploys five key components inside the `knative-serving` namespace. Together they manage the full lifecycle of a serverless workload, from receiving an initial request to scaling the application and routing traffic.

![Diagram of a Knative request path: a client request enters through a Kourier/Istio gateway, either flowing directly to a running revision's queue-proxy and container when scaled above zero, or being buffered by the Activator and forwarded once the Autoscaler brings a pod up from zero, with concurrency metrics feeding the Autoscaler's scaling decisions to the Controller.](../.gitbook/assets/en-autoscaling-03-knative-0.png)

**Component responsibilities:**

| Component | Role |
|-----------|------|
| **Activator** | Receives requests when a Revision is scaled to zero. Buffers requests, triggers scale-up, then proxies the buffered requests once pods are ready. Also acts as a load balancer when the system is in "burst capacity" mode. |
| **Autoscaler** | Collects concurrency and RPS metrics from Queue Proxy sidecars. Computes the desired replica count using the Knative Pod Autoscaler (KPA) algorithm or delegates to the Kubernetes HPA. Communicates scaling decisions to the Controller. |
| **Queue Proxy** | Injected as a sidecar into every Knative pod. Enforces `containerConcurrency` limits, reports real-time concurrency to the Autoscaler, performs health checking, and handles graceful shutdown during scale-down. |
| **Controller** | Reconciles Knative CRDs (Service, Configuration, Revision, Route) into underlying Kubernetes resources (Deployments, Services, Ingress objects). Manages revision creation and garbage collection. |
| **Webhook** | Validates and defaults Knative resource specifications on admission. Ensures that invalid configurations are rejected before they reach the Controller. |

### Eventing Architecture

Knative Eventing provides a declarative way to bind event sources to consumers. It supports two delivery patterns: **Broker/Trigger** (content-based routing) and **Channel/Subscription** (direct pub-sub).

![Diagram contrasting Knative's Broker/Trigger eventing pattern (sources feeding a Broker that routes filtered events through Triggers to consumer services, with failed deliveries going to a dead letter sink) against its Channel/Subscription pattern (a source feeding a Channel that fans out to Subscriptions and their consumer services).](../.gitbook/assets/en-autoscaling-03-knative-1.png)

**Eventing core concepts:**

| Concept | Description |
|---------|-------------|
| **Event Source** | A resource that generates or imports events. Knative provides built-in sources (ApiServerSource, PingSource) and the community maintains sources for Kafka, AWS SQS, GitHub, and more. |
| **Broker** | An event mesh that receives events and fans them out to matching Triggers. Backed by an in-memory channel (default) or Kafka for durability. |
| **Trigger** | A filter attached to a Broker. Each Trigger selects events by CloudEvent attributes (type, source, extensions) and routes matches to a subscriber. |
| **Channel** | A durable or in-memory event transport. Unlike Brokers, Channels do not filter -- every Subscription receives every event. |
| **Subscription** | Connects a Channel to a subscriber and optionally a reply destination. |
| **Dead Letter Sink** | A fallback destination for events that cannot be delivered after exhausting retry policies. |
| **CloudEvents** | The CNCF standard envelope format (v1.0) used by all Knative Eventing components. Provides interoperability across sources and consumers. |

---

## EKS Installation and Configuration

### Prerequisites

- An EKS cluster running Kubernetes 1.28 or later.
- `kubectl` configured with cluster admin access.
- (Optional) `helm` v3.12+ for Helm-based installations.

### Step 1: Install Knative Operator

The Knative Operator manages the installation and lifecycle of Knative Serving and Eventing components. Using the Operator simplifies version upgrades and configuration management.

```bash
# Install the Knative Operator v1.16
kubectl apply -f https://github.com/knative/operator/releases/download/knative-v1.16.0/operator.yaml

# Verify the Operator is running
kubectl get deployment knative-operator -n default
```

### Step 2: Install Knative Serving via the Operator

Create a `KnativeServing` custom resource to deploy Serving components:

```yaml
apiVersion: operator.knative.dev/v1beta1
kind: KnativeServing
metadata:
  name: knative-serving
  namespace: knative-serving
spec:
  version: "1.16.0"
  ingress:
    kourier:
      enabled: true
  config:
    network:
      ingress-class: kourier.ingress.networking.knative.dev
    autoscaler:
      # KPA is the default; set to "hpa" to use Kubernetes HPA
      class: kpa.autoscaling.knative.dev
      # Target 70% average concurrency per pod
      target-utilization-percentage: "70"
    defaults:
      # All new Revisions default to these values
      revision-timeout-seconds: "300"
      container-concurrency: "0"
    deployment:
      # Queue proxy resource requests
      queue-sidecar-cpu-request: "25m"
      queue-sidecar-memory-request: "50Mi"
```

```bash
# Create the namespace and apply
kubectl create namespace knative-serving
kubectl apply -f knative-serving.yaml

# Wait for all Serving pods to become ready
kubectl wait --for=condition=Ready pods --all -n knative-serving --timeout=300s
```

### Step 3: Install Kourier (Lightweight Ingress)

Kourier is the recommended lightweight ingress for Knative on EKS. It is simpler than Istio and has a smaller resource footprint.

If you installed Serving via the Operator with the `kourier` section above, Kourier is installed automatically. For manual installation:

```bash
# Install Kourier
kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.16.0/kourier.yaml

# Patch the config-network ConfigMap to use Kourier
kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

# Verify Kourier is running
kubectl get pods -n kourier-system
kubectl get svc kourier -n kourier-system
```

On EKS, the Kourier service is exposed as a `LoadBalancer`, which provisions an AWS Network Load Balancer (NLB) by default. To use an Application Load Balancer (ALB) instead, annotate the service accordingly:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kourier
  namespace: kourier-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
spec:
  type: LoadBalancer
```

### Step 4: DNS Configuration

Knative generates URLs for each Service in the form `<service>.<namespace>.<domain>`. You must configure DNS so that these URLs resolve to the Ingress gateway.

#### Option A: Magic DNS (sslip.io) -- Development Only

Magic DNS uses `sslip.io` to automatically resolve any hostname to the embedded IP address. This is suitable for development and testing only.

```bash
# Configure Knative to use sslip.io
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.16.0/serving-default-domain.yaml

# Verify: a service "my-app" in namespace "default" would get the URL:
# http://my-app.default.<EXTERNAL-IP>.sslip.io
```

#### Option B: Real DNS with Amazon Route 53 -- Production

For production, configure a real domain with Route 53:

```bash
# 1. Get the Kourier external IP / hostname
KOURIER_LB=$(kubectl get svc kourier -n kourier-system \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# 2. Create a wildcard CNAME record in Route 53
#    *.knative.example.com -> $KOURIER_LB
aws route53 change-resource-record-sets \
  --hosted-zone-id Z0123456789ABCDEFGHIJ \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "*.knative.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'$KOURIER_LB'"}]
      }
    }]
  }'

# 3. Configure Knative to use this domain
kubectl patch configmap/config-domain \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"knative.example.com":""}}'
```

### Step 5: TLS with cert-manager

Integrate cert-manager to automatically provision and renew TLS certificates for Knative Services.

```bash
# Install the Knative cert-manager integration
kubectl apply -f https://github.com/knative/net-certmanager/releases/download/knative-v1.16.0/release.yaml
```

Configure Knative to request certificates automatically:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-network
  namespace: knative-serving
data:
  ingress-class: kourier.ingress.networking.knative.dev
  auto-tls: "Enabled"
  http-protocol: "Redirected"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-certmanager
  namespace: knative-serving
data:
  issuerRef: |
    kind: ClusterIssuer
    name: letsencrypt-prod
```

Create the ClusterIssuer (assumes cert-manager is already installed):

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: platform-team@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - dns01:
          route53:
            region: us-west-2
            hostedZoneID: Z0123456789ABCDEFGHIJ
```

### Step 6: HPA vs KPA Autoscaler Selection

Knative supports two autoscaler implementations. The choice affects scaling behavior significantly.

| Feature | KPA (Knative Pod Autoscaler) | HPA (Kubernetes HPA) |
|---------|------------------------------|----------------------|
| Scale-to-zero | Yes | No |
| Metrics | Concurrency, RPS | CPU, Memory, Custom metrics |
| Scaling speed | Fast (panic/stable windows) | Standard HPA intervals |
| Configuration | Knative annotations | Standard HPA spec |
| Best for | HTTP workloads, latency-sensitive | CPU/memory-bound workloads |

Configure the default autoscaler class cluster-wide:

```yaml
# In config-autoscaler ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-autoscaler
  namespace: knative-serving
data:
  # "kpa.autoscaling.knative.dev" or "hpa.autoscaling.knative.dev"
  class: "kpa.autoscaling.knative.dev"

  # KPA-specific settings
  stable-window: "60s"
  panic-window-percentage: "10"
  panic-threshold-percentage: "200"
  scale-to-zero-grace-period: "30s"
  scale-to-zero-pod-retention-period: "0s"

  # Target defaults
  target-burst-capacity: "200"
  requests-per-second-target-default: "200"
  container-concurrency-target-default: "100"
```

Override per-Revision using annotations:

```yaml
metadata:
  annotations:
    autoscaling.knative.dev/class: "hpa.autoscaling.knative.dev"
    autoscaling.knative.dev/metric: "cpu"
    autoscaling.knative.dev/target: "70"
```

### Step 7: Install Knative Eventing

```yaml
apiVersion: operator.knative.dev/v1beta1
kind: KnativeEventing
metadata:
  name: knative-eventing
  namespace: knative-eventing
spec:
  version: "1.16.0"
  config:
    default-ch-webhook:
      default-ch-config: |
        clusterDefault:
          apiVersion: messaging.knative.dev/v1
          kind: InMemoryChannel
```

```bash
kubectl create namespace knative-eventing
kubectl apply -f knative-eventing.yaml
kubectl wait --for=condition=Ready pods --all -n knative-eventing --timeout=300s
```

---

## Knative Serving Deep Dive

### Resource Model

Knative Serving introduces four primary custom resources that work together to manage the complete lifecycle of a serverless workload.

![Diagram of Knative resource ownership: a Knative Service owns a Configuration and a Route; the Configuration creates a new immutable Revision on every change, while the Route sends all live traffic to the latest revision and keeps older revisions available at zero percent for rollback.](../.gitbook/assets/en-autoscaling-03-knative-2.png)

| Resource | Description |
|----------|-------------|
| **Service** (`ksvc`) | The top-level resource. Manages the entire lifecycle by owning a Configuration and a Route. Most users interact only with Services. |
| **Configuration** | Describes the desired state of a workload (container image, environment variables, resource limits). Each update to a Configuration creates a new Revision. |
| **Revision** | An immutable, point-in-time snapshot of a Configuration. Revisions are named automatically (e.g., `my-app-00001`). Old Revisions are retained for traffic splitting and rollback. |
| **Route** | Maps network traffic to one or more Revisions. Enables canary deployments, blue-green releases, and percentage-based traffic splitting. |

### Complete Knative Service YAML

The following example deploys a production-grade Knative Service with explicit autoscaling, resource limits, health checks, and scaling boundaries:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: order-api
  namespace: production
  labels:
    app.kubernetes.io/name: order-api
    app.kubernetes.io/part-of: ecommerce
    app.kubernetes.io/managed-by: knative
spec:
  template:
    metadata:
      annotations:
        # Autoscaling configuration
        autoscaling.knative.dev/class: "kpa.autoscaling.knative.dev"
        autoscaling.knative.dev/metric: "concurrency"
        autoscaling.knative.dev/target: "100"
        autoscaling.knative.dev/target-utilization-percentage: "70"
        autoscaling.knative.dev/min-scale: "2"
        autoscaling.knative.dev/max-scale: "50"
        autoscaling.knative.dev/initial-scale: "3"
        autoscaling.knative.dev/scale-down-delay: "15m"
        autoscaling.knative.dev/window: "60s"
    spec:
      containerConcurrency: 0
      timeoutSeconds: 300
      containers:
        - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/order-api:v1.2.3
          ports:
            - containerPort: 8080
              protocol: TCP
          env:
            - name: DB_HOST
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: host
            - name: LOG_LEVEL
              value: "info"
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
      serviceAccountName: order-api-sa
```

### Traffic Splitting: Canary Deployments

Traffic splitting allows you to gradually shift traffic between Revisions. This is the foundation for canary and blue-green deployment strategies.

#### Canary Deployment

Route a small percentage of traffic to the new Revision and increase it over time:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: order-api
  namespace: production
spec:
  template:
    metadata:
      # The new Revision is created from this template
      annotations:
        autoscaling.knative.dev/min-scale: "2"
    spec:
      containers:
        - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/order-api:v1.3.0
          ports:
            - containerPort: 8080
  traffic:
    # 90% to the current stable Revision
    - revisionName: order-api-00005
      percent: 90
    # 10% canary to the latest Revision
    - latestRevision: true
      percent: 10
      tag: canary
```

Gradually increase canary traffic:

```bash
# Increase canary to 50%
kubectl patch ksvc order-api -n production --type merge --patch '
spec:
  traffic:
    - revisionName: order-api-00005
      percent: 50
    - latestRevision: true
      percent: 50
      tag: canary
'

# Promote canary to 100%
kubectl patch ksvc order-api -n production --type merge --patch '
spec:
  traffic:
    - latestRevision: true
      percent: 100
'
```

Each tagged traffic target gets its own URL: `https://canary-order-api.production.knative.example.com`. This allows direct testing of the canary Revision.

#### Blue-Green Deployment

In a blue-green strategy, both Revisions run at full capacity and traffic is switched atomically:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: order-api
  namespace: production
spec:
  template:
    spec:
      containers:
        - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/order-api:v2.0.0
          ports:
            - containerPort: 8080
  traffic:
    # Blue (current) receives 100% of production traffic
    - revisionName: order-api-00005
      percent: 100
      tag: blue
    # Green (new) is deployed but receives 0% traffic; accessible via tag URL
    - latestRevision: true
      percent: 0
      tag: green
```

After validating the green environment via `https://green-order-api.production.knative.example.com`, switch traffic:

```bash
# Instant switch to green
kubectl patch ksvc order-api -n production --type merge --patch '
spec:
  traffic:
    - revisionName: order-api-00005
      percent: 0
      tag: blue
    - latestRevision: true
      percent: 100
      tag: green
'
```

### Scale-to-Zero Behavior

Scale-to-zero is a defining feature of Knative Serving. When a Revision receives no traffic, its pods are terminated after a configurable grace period. When a new request arrives, the Activator buffers it, triggers a scale-up, and proxies the request once a pod is ready.

![Sequence diagram of Knative's scale-to-zero and cold-start flow: after 60 seconds without traffic the Autoscaler scales the pod to zero and it terminates, then a new client request causes the Activator to request a scale-up, buffer the request while the pod starts, forward it once the pod reports ready, and return the response, after which later requests go directly to the pod.](../.gitbook/assets/en-autoscaling-03-knative-3.png)

Key parameters controlling scale-to-zero:

| Annotation / Config | Default | Description |
|---------------------|---------|-------------|
| `scale-to-zero-grace-period` (global) | 30s | Time the system waits after the last pod in a Revision becomes idle before removing it. |
| `scale-to-zero-pod-retention-period` (global) | 0s | Minimum time a pod is kept after last request, even if already idle. |
| `autoscaling.knative.dev/scale-to-zero-pod-retention-period` (per-Revision) | inherited | Per-Revision override of the global retention period. |
| `enable-scale-to-zero` (global) | true | Master toggle. Set to false to disable scale-to-zero cluster-wide. |

### Concurrency-Based Scaling

Knative's KPA scales based on observed concurrency (in-flight requests) or requests per second (RPS). The algorithm maintains two windows:

- **Stable window** (default 60s): Average concurrency over this period drives the steady-state scale decision.
- **Panic window** (default 6s, i.e., 10% of stable): If average concurrency in this window exceeds the panic threshold (default 200% of target), the system scales up aggressively.

**Key annotations:**

| Annotation | Example | Description |
|------------|---------|-------------|
| `autoscaling.knative.dev/metric` | `"concurrency"` or `"rps"` | Which metric to scale on. |
| `autoscaling.knative.dev/target` | `"100"` | Target value for the metric (e.g., 100 concurrent requests per pod). |
| `autoscaling.knative.dev/target-utilization-percentage` | `"70"` | The Autoscaler aims to keep average utilization at this percentage of the target. Effective target = target * utilization / 100. |
| `spec.containerConcurrency` | `0` (unlimited) | Hard limit on concurrent requests per container. The Queue Proxy enforces this and queues excess requests. Set to 0 for no limit. A value of 1 enables single-threaded processing. |

**Scaling formula:**

```
desiredReplicas = ceil( observedConcurrency / (target * targetUtilization / 100) )
```

For example, with `target=100`, `targetUtilization=70%`, and 350 observed concurrent requests:

```
desiredReplicas = ceil(350 / (100 * 0.70)) = ceil(350 / 70) = ceil(5.0) = 5
```

### Cold Start Optimization

Cold starts -- the latency penalty when scaling from zero -- are a common concern. Knative provides several mechanisms to mitigate them:

| Strategy | Configuration | Trade-off |
|----------|---------------|-----------|
| **minScale** | `autoscaling.knative.dev/min-scale: "2"` | Keeps a minimum number of pods running. Eliminates cold starts but incurs baseline cost. |
| **initialScale** | `autoscaling.knative.dev/initial-scale: "3"` | Number of pods created when a new Revision is first deployed. Does not prevent scale-to-zero later. |
| **scale-down-delay** | `autoscaling.knative.dev/scale-down-delay: "15m"` | Delays scale-down decisions. Useful for bursty workloads to avoid frequent cold starts. |
| **Container image caching** | Use EKS node-level image caching or pre-pull DaemonSets | Reduces container pull time during cold start. |
| **Lightweight base images** | Use distroless or Alpine-based images | Reduces image size and pull time. |
| **Application warmup** | Implement readiness probes that wait for caches/connections | Ensures the pod reports ready only after it can handle traffic at full speed. |

```yaml
# Example: latency-sensitive service with cold start mitigation
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: latency-critical-api
  namespace: production
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/min-scale: "3"
        autoscaling.knative.dev/initial-scale: "5"
        autoscaling.knative.dev/scale-down-delay: "10m"
        autoscaling.knative.dev/target: "50"
        autoscaling.knative.dev/window: "30s"
    spec:
      containerConcurrency: 100
      containers:
        - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/api:v1.0.0
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5
```

### Private and Public Services

By default, Knative Services are exposed externally through the ingress gateway. You can make a Service cluster-internal only:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: internal-processor
  namespace: production
  labels:
    networking.knative.dev/visibility: cluster-local
spec:
  template:
    spec:
      containers:
        - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/processor:v1.0.0
```

The `cluster-local` label causes Knative to generate an internal URL (e.g., `http://internal-processor.production.svc.cluster.local`) instead of a publicly routable one. This is useful for internal microservices that should not be accessible from outside the cluster.

You can also set the default visibility cluster-wide:

```yaml
# config-network ConfigMap
data:
  default-external-scheme: "https"
  visibility: "cluster-local"  # All services are private by default
```

---

## Knative Eventing Deep Dive

### Event Sources

Event Sources are Knative resources that connect external systems to the eventing mesh. Each Source emits CloudEvents to a configured sink (a Broker, Channel, or directly to a Knative Service).

#### ApiServerSource

Watches the Kubernetes API server for resource events and forwards them as CloudEvents:

```yaml
apiVersion: sources.knative.dev/v1
kind: ApiServerSource
metadata:
  name: pod-event-source
  namespace: production
spec:
  serviceAccountName: event-watcher-sa
  mode: Resource
  resources:
    - apiVersion: v1
      kind: Pod
    - apiVersion: apps/v1
      kind: Deployment
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
```

#### SinkBinding

Injects environment variables (specifically `K_SINK`) into any Kubernetes workload so it can send events to a sink without hardcoding the destination:

```yaml
apiVersion: sources.knative.dev/v1
kind: SinkBinding
metadata:
  name: order-producer-binding
  namespace: production
spec:
  subject:
    apiVersion: apps/v1
    kind: Deployment
    name: order-producer
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
  ceOverrides:
    extensions:
      source: order-system
```

Your application reads `K_SINK` and POSTs CloudEvents to it:

```python
import os, requests, json
from datetime import datetime

sink_url = os.environ["K_SINK"]

event = {
    "specversion": "1.0",
    "type": "com.example.order.created",
    "source": "/orders/api",
    "id": "order-12345",
    "time": datetime.utcnow().isoformat() + "Z",
    "datacontenttype": "application/json",
    "data": {"orderId": "12345", "amount": 99.99}
}

headers = {
    "Content-Type": "application/cloudevents+json",
    "ce-specversion": event["specversion"],
    "ce-type": event["type"],
    "ce-source": event["source"],
    "ce-id": event["id"],
}

requests.post(sink_url, json=event["data"], headers=headers)
```

#### KafkaSource

Consumes messages from Apache Kafka topics and delivers them as CloudEvents:

```yaml
apiVersion: sources.knative.dev/v1beta1
kind: KafkaSource
metadata:
  name: payment-events
  namespace: production
spec:
  consumerGroup: knative-payment-consumer
  bootstrapServers:
    - kafka-bootstrap.kafka.svc.cluster.local:9092
  topics:
    - payment-events
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
  # Optional: configure SASL/TLS for MSK
  net:
    sasl:
      enable: true
      type:
        secretKeyRef:
          name: kafka-credentials
          key: sasl-type
      user:
        secretKeyRef:
          name: kafka-credentials
          key: username
      password:
        secretKeyRef:
          name: kafka-credentials
          key: password
    tls:
      enable: true
```

#### SQSSource (AWS)

Consumes messages from Amazon SQS queues. This requires the AWS event source controller:

```bash
# Install AWS event sources
kubectl apply -f https://github.com/triggermesh/aws-event-sources/releases/latest/download/aws-event-sources.yaml
```

```yaml
apiVersion: sources.triggermesh.io/v1alpha1
kind: AWSSQSSource
metadata:
  name: order-queue-source
  namespace: production
spec:
  arn: arn:aws:sqs:us-west-2:123456789012:order-events
  receiveOptions:
    visibilityTimeout: 60s
  auth:
    credentials:
      accessKeyID:
        valueFromSecret:
          name: aws-credentials
          key: access-key-id
      secretAccessKey:
        valueFromSecret:
          name: aws-credentials
          key: secret-access-key
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
```

For production on EKS, prefer IAM Roles for Service Accounts (IRSA) instead of static credentials.

### Broker/Trigger Pattern

The Broker/Trigger pattern provides content-based event routing. A Broker acts as an event hub; Triggers filter events by CloudEvent attributes and route them to subscribers.

#### Complete Broker/Trigger Example

```yaml
# 1. Create the Broker
apiVersion: eventing.knative.dev/v1
kind: Broker
metadata:
  name: default
  namespace: production
  annotations:
    eventing.knative.dev/broker.class: MTChannelBasedBroker
spec:
  config:
    apiVersion: v1
    kind: ConfigMap
    name: config-br-default-channel
    namespace: knative-eventing
  delivery:
    retry: 5
    backoffPolicy: exponential
    backoffDelay: "PT2S"
    deadLetterSink:
      ref:
        apiVersion: serving.knative.dev/v1
        kind: Service
        name: dead-letter-handler
---
# 2. Trigger for order.created events -> Order Service
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: order-created-trigger
  namespace: production
spec:
  broker: default
  filter:
    attributes:
      type: com.example.order.created
      source: /orders/api
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: order-processor
---
# 3. Trigger for payment.processed events -> Payment Service
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: payment-processed-trigger
  namespace: production
spec:
  broker: default
  filter:
    attributes:
      type: com.example.payment.processed
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: payment-reconciler
  delivery:
    retry: 10
    backoffPolicy: exponential
    backoffDelay: "PT5S"
    deadLetterSink:
      ref:
        apiVersion: serving.knative.dev/v1
        kind: Service
        name: payment-dead-letter
---
# 4. Trigger for all events -> Analytics (no filter = catch-all)
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: analytics-trigger
  namespace: production
spec:
  broker: default
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: analytics-collector
```

### CloudEvents Standard

All Knative Eventing components communicate using the [CloudEvents](https://cloudevents.io/) specification (v1.0). CloudEvents defines a common envelope with required and optional attributes:

| Attribute | Required | Example | Description |
|-----------|----------|---------|-------------|
| `specversion` | Yes | `"1.0"` | CloudEvents specification version. |
| `type` | Yes | `"com.example.order.created"` | Event type. Used for routing by Triggers. |
| `source` | Yes | `"/orders/api"` | Event origin. Combined with type for filtering. |
| `id` | Yes | `"evt-abc123"` | Unique event identifier for deduplication. |
| `time` | No | `"2025-06-15T10:30:00Z"` | Timestamp of event occurrence. |
| `datacontenttype` | No | `"application/json"` | Content type of the `data` attribute. |
| `subject` | No | `"order-12345"` | Subject of the event in context of the source. |
| `data` | No | `{"orderId": "12345"}` | Event payload. |

### Channel/Subscription Pattern

The Channel/Subscription pattern provides direct pub-sub without content-based filtering. Every Subscription on a Channel receives every event.

```yaml
# 1. Create a Channel backed by Kafka for durability
apiVersion: messaging.knative.dev/v1beta1
kind: KafkaChannel
metadata:
  name: audit-events
  namespace: production
spec:
  numPartitions: 6
  replicationFactor: 3
  retentionDuration: PT168H  # 7 days
---
# 2. Subscription: forward to audit logging service
apiVersion: messaging.knative.dev/v1
kind: Subscription
metadata:
  name: audit-log-subscription
  namespace: production
spec:
  channel:
    apiVersion: messaging.knative.dev/v1beta1
    kind: KafkaChannel
    name: audit-events
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: audit-logger
  reply:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: audit-response-handler
---
# 3. Subscription: forward to compliance service
apiVersion: messaging.knative.dev/v1
kind: Subscription
metadata:
  name: compliance-subscription
  namespace: production
spec:
  channel:
    apiVersion: messaging.knative.dev/v1beta1
    kind: KafkaChannel
    name: audit-events
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: compliance-checker
  delivery:
    deadLetterSink:
      ref:
        apiVersion: serving.knative.dev/v1
        kind: Service
        name: dead-letter-handler
    retry: 3
    backoffPolicy: linear
    backoffDelay: "PT10S"
```

### Dead Letter Sink

When event delivery fails after exhausting all retries, the event is forwarded to a Dead Letter Sink (DLS). The DLS is typically a Knative Service that persists failed events for later analysis or replay.

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: dead-letter-handler
  namespace: production
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/min-scale: "1"
    spec:
      containers:
        - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/dead-letter:v1.0.0
          env:
            - name: S3_BUCKET
              value: "failed-events-production"
            - name: AWS_REGION
              value: "us-west-2"
```

Configure DLS at the Broker level (applies to all Triggers) or at individual Trigger/Subscription level for fine-grained control.

### Event Filtering

Triggers support filtering on CloudEvent attributes and extensions.

#### Attribute Filtering

```yaml
spec:
  filter:
    attributes:
      type: com.example.order.created
      source: /orders/api
```

This Trigger fires only when both `type` AND `source` match (logical AND).

#### Extension Filtering

You can filter on custom CloudEvent extensions set by producers:

```yaml
spec:
  filter:
    attributes:
      type: com.example.order.created
      myextension: priority-high
```

#### Multiple Triggers for OR Logic

Since a single Trigger filter is AND-only, use multiple Triggers on the same subscriber for OR logic:

```yaml
# Trigger 1: react to order.created
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: order-created
spec:
  broker: default
  filter:
    attributes:
      type: com.example.order.created
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: notification-service
---
# Trigger 2: also react to order.cancelled
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: order-cancelled
spec:
  broker: default
  filter:
    attributes:
      type: com.example.order.cancelled
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: notification-service
```

---

## KEDA vs Knative Comparison

Both KEDA and Knative enable event-driven scaling on Kubernetes, but they operate at different levels of abstraction and serve complementary roles.

### Scaling Model Differences

| Aspect | KEDA | Knative |
|--------|------|---------|
| **Abstraction level** | Extends HPA with custom metric sources | Full serverless platform (deployment, routing, scaling) |
| **Scaling mechanism** | Creates/manages HPA resources | Custom KPA controller or HPA delegation |
| **Primary metric** | External metrics (queue depth, DB rows, custom) | HTTP concurrency / RPS |
| **Workload type** | Any Deployment, StatefulSet, Job | Knative Service (manages its own Deployment) |
| **CRDs** | ScaledObject, ScaledJob, TriggerAuthentication | Service, Configuration, Revision, Route |
| **Built-in routing** | No | Yes (traffic splitting, revisions, canary) |
| **Built-in eventing** | No (focuses on scaling only) | Yes (Broker/Trigger, Channel/Subscription) |

### Scale-to-Zero Behavior Differences

| Behavior | KEDA | Knative (KPA) |
|----------|------|---------------|
| Scale-to-zero trigger | Metric value drops to 0 or below threshold | No HTTP requests for configurable grace period |
| Activation mechanism | KEDA Operator sets replicas from 0 to `minReplicaCount` when metric > 0 | Activator buffers HTTP requests and triggers scale-up |
| Request buffering | No (not HTTP-aware) | Yes (Activator buffers during cold start) |
| Cool-down period | `cooldownPeriod` on ScaledObject | `scale-to-zero-grace-period` + `stable-window` |
| Scale-to-zero for Jobs | Yes (ScaledJob) | No (Serving only handles long-running processes) |

### Roles in Event-Driven Architecture

![Diagram comparing two parallel scaling paths from shared event sources: Amazon SQS queue depth driving a KEDA ScaledObject through the HPA to scale a Worker Deployment, versus Kafka and HTTP CloudEvents flowing into a Knative Broker that routes through a Trigger to a Knative Service.](../.gitbook/assets/en-autoscaling-03-knative-4.png)

### When to Use KEDA vs Knative

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| Scale workers based on SQS queue depth | **KEDA** | KEDA has a native SQS scaler; no HTTP routing needed. |
| Deploy HTTP APIs with auto-scaling and traffic splitting | **Knative** | Serving provides revision management, traffic splitting, and HTTP-aware autoscaling. |
| Scale based on Prometheus metrics | **KEDA** | KEDA's Prometheus scaler is mature and well-tested. |
| Event-driven microservices with CloudEvents | **Knative** | Eventing provides Broker/Trigger, dead letter handling, and CloudEvents support. |
| Scale CronJobs or batch workloads | **KEDA** | ScaledJob is designed for this. Knative Serving is for long-running processes. |
| Scale based on CPU/memory with scale-to-zero | **KEDA** | Knative's KPA focuses on concurrency/RPS, not CPU/memory. |
| Serverless platform for developers | **Knative** | Higher-level abstraction; developers deploy with `kn service create`. |

### Using KEDA and Knative Together

KEDA and Knative are not mutually exclusive. A common architecture uses:

- **Knative Serving** for HTTP-facing services (APIs, web applications) with concurrency-based autoscaling.
- **KEDA** for background workers (queue consumers, batch processors) with external-metric-based autoscaling.
- **Knative Eventing** to route events between services, including KEDA-scaled workers via SinkBinding.

```yaml
# Knative Service: receives HTTP events from Broker
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: event-enricher
spec:
  template:
    spec:
      containers:
        - image: event-enricher:v1
---
# KEDA ScaledObject: scales a Deployment based on SQS queue depth
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-worker-scaler
spec:
  scaleTargetRef:
    name: sqs-worker
  minReplicaCount: 0
  maxReplicaCount: 100
  triggers:
    - type: aws-sqs-queue
      metadata:
        queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/enriched-events
        queueLength: "5"
        awsRegion: us-west-2
      authenticationRef:
        name: keda-aws-credentials
```

---

## Production Operations

### Resource Limits and QoS

In production, always set resource requests and limits for both your application container and the Queue Proxy sidecar. This ensures pods get a `Guaranteed` or `Burstable` QoS class, preventing OOM kills and noisy-neighbor issues.

```yaml
# Global Queue Proxy resources (config-deployment ConfigMap)
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-deployment
  namespace: knative-serving
data:
  queue-sidecar-cpu-request: "50m"
  queue-sidecar-cpu-limit: "500m"
  queue-sidecar-memory-request: "100Mi"
  queue-sidecar-memory-limit: "256Mi"
  # Enforce resource limits on all revisions
  queue-sidecar-token-audiences: ""
```

### Revision Garbage Collection

Over time, old Revisions accumulate. Configure garbage collection to limit the number of retained Revisions:

```yaml
# config-gc ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-gc
  namespace: knative-serving
data:
  # Minimum number of non-active Revisions to retain
  min-non-active-revisions: "2"
  # Maximum number of non-active Revisions to retain
  max-non-active-revisions: "10"
  # Duration to retain non-active Revisions (Go duration format)
  retain-since-create-time: "48h"
  retain-since-last-active-time: "24h"
  # Minimum staleness before a Revision is eligible for GC
  min-stale-revision-create-delay: "24h"
```

### High Availability Configuration

For production workloads, configure Knative Serving components for high availability:

```yaml
apiVersion: operator.knative.dev/v1beta1
kind: KnativeServing
metadata:
  name: knative-serving
  namespace: knative-serving
spec:
  version: "1.16.0"
  high-availability:
    replicas: 3
  ingress:
    kourier:
      enabled: true
  workloads:
    - name: activator
      replicas: 3
      resources:
        requests:
          cpu: "300m"
          memory: "256Mi"
        limits:
          cpu: "1000m"
          memory: "512Mi"
    - name: controller
      replicas: 2
    - name: webhook
      replicas: 2
```

Additionally, configure Pod Disruption Budgets for Knative system components:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: activator-pdb
  namespace: knative-serving
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: activator
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: controller-pdb
  namespace: knative-serving
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: controller
```

Spread system pods across Availability Zones using topology constraints:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: activator
  namespace: knative-serving
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: activator
```

### Monitoring with Prometheus

Knative Serving and Eventing expose Prometheus metrics. Configure a ServiceMonitor (for the Prometheus Operator) or a scrape config to collect them.

```yaml
# ServiceMonitor for Knative Serving components
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: knative-serving
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
      - knative-serving
  selector:
    matchLabels:
      app.kubernetes.io/part-of: knative
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
---
# ServiceMonitor for application-level metrics (Queue Proxy)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: knative-revisions
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    any: true
  selector:
    matchLabels:
      serving.knative.dev/service: ""
  endpoints:
    - port: http-usermetric
      interval: 10s
      path: /metrics
    - port: http-queueadm
      interval: 10s
      path: /metrics
```

**Key metrics to monitor:**

| Metric | Component | Description |
|--------|-----------|-------------|
| `revision_app_request_count` | Queue Proxy | Total request count per Revision. |
| `revision_app_request_latencies` | Queue Proxy | Request latency histogram. |
| `revision_request_concurrency` | Queue Proxy | Current in-flight request count per pod. |
| `activator_request_count` | Activator | Requests handled by the Activator (indicates cold starts). |
| `autoscaler_desired_pods` | Autoscaler | Desired replica count per Revision. |
| `autoscaler_actual_pods` | Autoscaler | Current actual replica count. |
| `autoscaler_panic_mode` | Autoscaler | Whether the Autoscaler is in panic mode (1 = yes). |
| `controller_reconcile_count` | Controller | Reconciliation count by resource type and result. |
| `broker_event_count` | Eventing | Events processed by each Broker. |
| `trigger_filter_event_count` | Eventing | Events that passed/failed Trigger filter. |

### Grafana Dashboard

Import or create a Grafana dashboard that visualizes the Knative metrics above. Below is a JSON model for a basic Knative overview dashboard:

```json
{
  "dashboard": {
    "title": "Knative Overview",
    "panels": [
      {
        "title": "Request Rate by Revision",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(revision_app_request_count[5m])) by (revision_name)",
            "legendFormat": "{{revision_name}}"
          }
        ]
      },
      {
        "title": "Request Latency P99",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, sum(rate(revision_app_request_latencies_bucket[5m])) by (le, revision_name))",
            "legendFormat": "{{revision_name}}"
          }
        ]
      },
      {
        "title": "Concurrency per Pod",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(revision_request_concurrency) by (revision_name)",
            "legendFormat": "{{revision_name}}"
          }
        ]
      },
      {
        "title": "Desired vs Actual Pods",
        "type": "graph",
        "targets": [
          {
            "expr": "autoscaler_desired_pods",
            "legendFormat": "desired - {{revision_name}}"
          },
          {
            "expr": "autoscaler_actual_pods",
            "legendFormat": "actual - {{revision_name}}"
          }
        ]
      },
      {
        "title": "Activator Requests (Cold Starts)",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(activator_request_count[5m])) by (revision_name)",
            "legendFormat": "{{revision_name}}"
          }
        ]
      },
      {
        "title": "Autoscaler Panic Mode",
        "type": "stat",
        "targets": [
          {
            "expr": "autoscaler_panic_mode",
            "legendFormat": "{{revision_name}}"
          }
        ]
      }
    ]
  }
}
```

### Troubleshooting

#### Cold Start Latency Is Too High

**Symptoms:** First request after idle period takes several seconds.

**Diagnosis:**

```bash
# Check if the Revision is scaled to zero
kubectl get ksvc order-api -n production -o jsonpath='{.status.conditions}' | jq .

# Check Activator logs for buffering duration
kubectl logs -l app=activator -n knative-serving --tail=50

# Check pod startup time
kubectl get pods -l serving.knative.dev/service=order-api -n production \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions}{"\n"}{end}'
```

**Solutions:**
1. Set `autoscaling.knative.dev/min-scale: "1"` to keep at least one pod warm.
2. Reduce container image size.
3. Use readiness probes with short intervals.
4. Pre-pull images using a DaemonSet.

#### Scaling Is Too Slow or Oscillating

**Symptoms:** Pod count does not keep up with load, or scales up and down repeatedly.

**Diagnosis:**

```bash
# Check Autoscaler metrics
kubectl logs -l app=autoscaler -n knative-serving --tail=100

# View current scale decisions
kubectl get podautoscaler -n production
kubectl describe podautoscaler order-api-00001 -n production
```

**Solutions:**
1. Reduce the `stable-window` for faster reactions (e.g., `30s`).
2. Increase `target-utilization-percentage` to allow more headroom before scaling up.
3. Adjust `panic-window-percentage` and `panic-threshold-percentage` for burst handling.
4. If using HPA class, increase the `--horizontal-pod-autoscaler-sync-period`.

#### Events Not Being Delivered

**Symptoms:** Events are produced but Triggers do not fire.

**Diagnosis:**

```bash
# Verify Broker is ready
kubectl get broker default -n production -o yaml

# Check Trigger status
kubectl get triggers -n production
kubectl describe trigger order-created-trigger -n production

# Inspect Eventing controller logs
kubectl logs -l app=eventing-controller -n knative-eventing --tail=100

# Check dead letter sink for failed events
kubectl logs -l serving.knative.dev/service=dead-letter-handler -n production --tail=50
```

**Solutions:**
1. Verify the Trigger filter attributes match the CloudEvent attributes exactly (case-sensitive).
2. Check that the subscriber Service is ready and reachable.
3. Ensure the Broker's backing channel is healthy.
4. Confirm RBAC allows the event source's ServiceAccount to send events to the Broker.

#### DNS Resolution Failures

**Symptoms:** Knative Service URLs return `NXDOMAIN` or connection timeouts.

**Diagnosis:**

```bash
# Verify Kourier service has an external address
kubectl get svc kourier -n kourier-system

# Check config-domain
kubectl get cm config-domain -n knative-serving -o yaml

# Test DNS resolution
nslookup order-api.production.knative.example.com

# Check the Knative Service URL
kubectl get ksvc order-api -n production -o jsonpath='{.status.url}'
```

**Solutions:**
1. For sslip.io: ensure the external IP is reachable and port 80/443 is not blocked by security groups.
2. For Route 53: verify the wildcard CNAME record resolves to the Kourier load balancer.
3. Check that `config-domain` has the correct domain entry.

---

## Best Practices

### Service Design Patterns

1. **One container per Knative Service.** Knative Services are designed for a single application container plus the Queue Proxy sidecar. Avoid multi-container pods unless absolutely necessary (Knative does support them, but the scaling model assumes a single primary container).

2. **Use `containerConcurrency` deliberately.** Set it to `0` (unlimited) for thread-safe applications that handle many concurrent requests. Set it to `1` for single-threaded processors (e.g., ML inference on a single GPU) where concurrent requests would degrade performance.

3. **Separate read and write paths.** Deploy read-heavy APIs and write-heavy processors as separate Knative Services with different scaling profiles. Read services may have a high `target` (100+ concurrency), while write services may need a low `target` (10-20) to avoid overwhelming the database.

4. **Tag Revisions for rollback.** Always tag the last known-good Revision so you can instantly roll back:

```bash
kn service update order-api --tag order-api-00005=stable --tag @latest=canary
```

5. **Use private services for internal communication.** Apply `networking.knative.dev/visibility: cluster-local` to services that should not be internet-facing. This reduces attack surface and avoids unnecessary load balancer costs.

### Event-Driven Microservices Patterns

1. **Use Brokers for multi-consumer routing.** When multiple services need to react to the same event type, use a single Broker with multiple Triggers rather than duplicating the event source.

2. **Always configure Dead Letter Sinks.** Undeliverable events should never be silently dropped. Configure a DLS at the Broker level as a safety net and at individual Trigger levels for critical paths.

3. **Adopt a CloudEvents naming convention.** Use reverse-DNS notation for event types: `com.<company>.<domain>.<action>` (e.g., `com.example.order.created`). This prevents naming collisions and makes Trigger filters clear.

4. **Idempotent consumers.** Since events may be delivered more than once (at-least-once semantics), design consumers to be idempotent. Use the CloudEvent `id` attribute for deduplication.

5. **Use Kafka-backed Channels for durability.** The default InMemoryChannel loses events on pod restart. For production, install the KafkaChannel and configure it as the default:

```yaml
# config-br-default-channel ConfigMap
data:
  channel-template-spec: |
    apiVersion: messaging.knative.dev/v1beta1
    kind: KafkaChannel
    spec:
      numPartitions: 6
      replicationFactor: 3
```

### Cost Optimization with Scale-to-Zero

1. **Enable scale-to-zero for non-critical services.** Development, staging, and low-traffic production services should scale to zero when idle. This can reduce compute costs by 60-80% for environments with sporadic traffic.

2. **Use `scale-down-delay` for bursty workloads.** If traffic comes in bursts separated by short idle periods, setting a scale-down delay (e.g., 5-15 minutes) avoids repeated cold starts without keeping pods running indefinitely.

3. **Combine with Karpenter for node-level efficiency.** When Knative scales pods to zero, the freed capacity allows Karpenter to consolidate or terminate underutilized nodes:

| Layer | Tool | Action |
|-------|------|--------|
| Application (Pods) | Knative Serving | Scale pods to zero on idle |
| Infrastructure (Nodes) | Karpenter | Consolidate and terminate empty nodes |
| Cost visibility | AWS Cost Explorer / Kubecost | Track savings from scale-to-zero |

4. **Set `minScale` only where needed.** Reserve `minScale > 0` for latency-critical paths. For everything else, let pods scale to zero.

### Knative with GPU Workloads

Knative can serve GPU-accelerated workloads (e.g., ML inference) by scheduling pods on GPU nodes. Key considerations:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: llm-inference
  namespace: ai
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/class: "kpa.autoscaling.knative.dev"
        autoscaling.knative.dev/metric: "concurrency"
        autoscaling.knative.dev/target: "1"
        autoscaling.knative.dev/min-scale: "1"
        autoscaling.knative.dev/max-scale: "4"
    spec:
      # Single-request processing for GPU workloads
      containerConcurrency: 1
      timeoutSeconds: 600
      containers:
        - image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/llm-server:v1
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "4"
              memory: "16Gi"
              nvidia.com/gpu: "1"
            limits:
              cpu: "8"
              memory: "32Gi"
              nvidia.com/gpu: "1"
      nodeSelector:
        node.kubernetes.io/instance-type: g5.xlarge
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
```

**GPU-specific tips:**
- Set `containerConcurrency: 1` if the model cannot batch concurrent requests. Increase it if the serving framework supports dynamic batching (e.g., vLLM, Triton Inference Server).
- Set `min-scale: 1` or higher to avoid cold starts, as GPU container images are large and model loading is slow.
- Use Karpenter with GPU NodePools to dynamically provision GPU nodes as Knative scales up.
- Monitor GPU utilization with DCGM Exporter and NVIDIA GPU Operator metrics.

---

## References

### Official Documentation

- [Knative Official Documentation](https://knative.dev/docs/)
- [Knative GitHub Organization](https://github.com/knative)
- [Knative Serving API Reference](https://knative.dev/docs/reference/api/serving-api/)
- [Knative Eventing API Reference](https://knative.dev/docs/reference/api/eventing-api/)
- [Kourier GitHub Repository](https://github.com/knative-extensions/net-kourier)
- [CloudEvents Specification](https://cloudevents.io/)
- [CNCF Knative Project Page](https://www.cncf.io/projects/knative/)

### AWS and EKS Resources

- [AWS Blog: Serverless Containers with Knative and EKS](https://aws.amazon.com/blogs/containers/)
- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [Amazon Route 53 Developer Guide](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/)
- [cert-manager on EKS](https://cert-manager.io/docs/installation/compatibility/)

### Related Internal Documentation

- [KEDA -- Kubernetes Event-driven Autoscaling](./01-keda.md)
- [Karpenter -- Cluster Autoscaler](./02-karpenter.md)
- [EKS Cost Optimization](../eks/07-eks-cost-optimization.md)

---

**Previous:** [Karpenter](./02-karpenter.md) | **Next:** None
