# Istio Installation and Initial Setup

This document covers how to install and initially configure Istio on an Amazon EKS cluster.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Choosing an Installation Method](#choosing-an-installation-method)
3. [Installation Using istioctl](#installation-using-istioctl)
4. [Installation Using Helm](#installation-using-helm)
5. [Declarative Installation with istioctl](#declarative-installation-with-istioctl)
6. [Installation Profiles](#installation-profiles)
7. [Installation Verification](#installation-verification)
8. [Sample Application Deployment](#sample-application-deployment)
9. [Istio Removal](#istio-removal)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

Before installing Istio, the following requirements must be met:

### 1. Amazon EKS Cluster

- **Kubernetes version**: EKS 1.34–1.36 for this Istio 1.31.0 example (reviewed September 11, 2026). Istio 1.31 supports 1.32–1.36; EKS 1.32/1.33 are in extended support. Check both the [Istio matrix](https://istio.io/latest/docs/releases/supported-releases/) and [EKS lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html).
- **Node type**: Minimum 2 worker nodes (recommended: 3 or more)
- **Node size**: Minimum 2 vCPU, 4GB RAM (recommended: t3.medium or larger)

These examples target Linux EC2 worker nodes. Fargate cannot run the DaemonSets/privileged networking needed by these Istio installation paths. EKS Auto Mode has a different managed networking/load-balancing model; validate its prerequisites separately.

### 2. kubectl Installation and Configuration

```bash
# Verify kubectl installation
kubectl version --client

# Verify EKS cluster connection
kubectl get nodes
```

### 3. Required Tools

- **AWS CLI**: 2.x or higher
- **eksctl**: (Optional) For cluster management
- **Helm**: a currently supported Helm 3 or Helm 4 release (minimum 3.6; see the official installation guide)

### 4. Cluster Resources

Illustrative planning requests, not universal minimums; size from measured load:
- **Control Plane**: 1 vCPU, 1.5GB RAM
- **Sidecar (per pod)**: 0.1 vCPU, 128MB RAM

## Choosing an Installation Method

Choose one supported installation path; do not run the istioctl and Helm installations on the same control plane:

| Method | Advantages | Disadvantages | Recommended Use Case |
|------|------|------|---------------|
| **istioctl** | Simple and fast, provides validation features | Requires explicit reconciliation in automation | Development and production |
| **Helm** | GitOps friendly, easy version management | Configuration can be complex | Production environments, CI/CD pipelines |

## Installation Using istioctl

istioctl is Istio's official CLI tool and the simplest installation method.

### 1. Install istioctl

```bash
# Download the reviewed release
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.0 sh -

# Add istioctl to PATH
cd istio-1.31.0
export PATH=$PWD/bin:$PATH

# Verify installation
istioctl version
```

### 2. Pre-installation Cluster Validation

```bash
# Verify cluster meets Istio installation requirements
istioctl x precheck
```

### 3. Install Istio

```bash
# Install with default profile
istioctl install --set profile=default -y

# Check installation progress
kubectl get pods -n istio-system
```

### 4. Verify Installation

```bash
# Check Istio components
kubectl get all -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod
```

## Installation Using Helm

The pinned 1.31.0 release charts were rendered during this audit. They do not contain an `eks` platform profile, although the current overview lists one. These examples therefore omit `global.platform=eks`; apply the explicit EKS prerequisites and load-balancer settings instead.

Helm is a Kubernetes package manager suitable for GitOps workflows.

### 1. Add Helm Repository

```bash
# Add Istio Helm repository
helm repo add istio https://blob.istio.io/istio-release/charts
helm repo update
```

### 2. Install istio-base

istio-base installs Istio's CRDs (Custom Resource Definitions).

```bash
# Create istio-system namespace
kubectl create namespace istio-system

# Install istio-base chart
helm install istio-base istio/base \
  -n istio-system \
  --set defaultRevision=default \
  --version 1.31.0
```

### 3. Install istiod

istiod is the Istio Control Plane.

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.31.0 \
  --wait
```

### 4. Install Istio Ingress Gateway (Optional)

```bash
# Verify the gateway namespace
kubectl get namespace istio-system

# Install Istio Ingress Gateway
helm install istio-ingressgateway istio/gateway \
  -n istio-system \
  --set labels.istio=ingressgateway \
  --set labels.app=istio-ingressgateway \
  --version 1.31.0 \
  --wait
```

### 5. Custom Installation Using values.yaml

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.31.0

autoscaleEnabled: true
autoscaleMin: 2
autoscaleMax: 5
resources:
  requests:
    cpu: 500m
    memory: 2048Mi

meshConfig:
  accessLogFile: /dev/stdout
```

```bash
# Install using values.yaml file
helm upgrade --install istiod istio/istiod \
  -n istio-system \
  --version 1.31.0 \
  -f values.yaml \
  --wait
```

## Declarative Installation with istioctl

The upstream in-cluster operator was deprecated in 1.23 and removed in 1.24. `istioctl operator init/remove` and applying an IstioOperator object to the cluster are not current installation methods. The [IstioOperator file format remains supported as input to istioctl](https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/).

```yaml
# istio-operator.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-control-plane
  namespace: istio-system
spec:
  profile: default
  meshConfig:
    accessLogFile: /dev/stdout
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 1000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
```

```bash
istioctl install -f istio-operator.yaml
kubectl rollout status deployment/istiod -n istio-system
```

## Installation Profiles

Istio provides various profiles for different use cases.

### Available Profiles

| Profile | Description | Components | Recommended Use |
|-------|------|----------|----------|
| **default** | Default settings for production deployment | istiod, ingress gateway | Most production environments |
| **demo** | Demonstration settings, not all features | istiod, ingress gateway, egress gateway, high trace sampling | Development and demos |
| **minimal** | Only minimal components installed | istiod only | Resource-constrained environments |
| **remote** | For remote cluster in multi-cluster environment | - | Multi-cluster setup |
| **empty** | No default configuration | - | Complete custom setup |
| **preview** | Includes experimental features | Various experimental features | Test environments |
| **ambient** | Sidecarless L4 mesh | istiod, CNI, ztunnel; L7 waypoints configured separately | Ambient deployments |

The component list applies to istioctl. Helm requires installing each chart separately; a profile does not install other charts.

### Check Profiles

```bash
helm show values istio/istiod --version 1.31.0
istioctl manifest generate --set profile=default > default.yaml
istioctl manifest generate --set profile=demo > demo.yaml
diff -u default.yaml demo.yaml
```

### Installation by Profile

```bash
# Install with demo profile
istioctl install --set profile=demo -y

# Install with minimal profile
istioctl install --set profile=minimal -y
```

### Customizing Profiles

```bash
# Modify specific settings based on profile
istioctl install --set profile=default \
  --set meshConfig.accessLogFile=/dev/stdout \
  --set components.pilot.k8s.resources.requests.memory=2Gi \
  -y
```

## Installation Verification

### 1. Check Control Plane

```bash
# Check all resources in istio-system namespace
kubectl get all -n istio-system

# Check istiod status
kubectl get deployment istiod -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod --tail=100
```

### 2. Check Istio Version

```bash
# Control Plane version
istioctl version

# Or
kubectl get pods -n istio-system -o yaml | grep image:
```

### 3. Validate Istio Configuration

```bash
# Check Istio installation status
kubectl rollout status deployment/istiod -n istio-system
istioctl proxy-status

# Analyze Istio configuration
istioctl analyze -A
```

### 4. Check Webhooks

```bash
# Check MutatingWebhookConfiguration
kubectl get mutatingwebhookconfiguration

# Check ValidatingWebhookConfiguration
kubectl get validatingwebhookconfiguration
```

## Sample Application Deployment

Istio includes a sample application called Bookinfo.

Run these commands from the extracted `istio-1.31.0` directory with the default namespace selected (`kubectl config set-context --current --namespace=default`). For Helm, install the optional gateway above first. The dashboard commands later require separately installed telemetry addons.

### 1. Enable Automatic Sidecar Injection for Namespace

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled --overwrite

# Verify label
kubectl get namespace -L istio-injection
```

Existing pods need recreation after changing injection labels. Use a namespace without a conflicting `istio.io/rev` or ambient label.

### 2. Deploy Bookinfo Application

```bash
# Deploy Bookinfo application
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Check pods (each pod should have 2 containers)
kubectl get pods

# Check services
kubectl get services
```

### 3. Verify Application Access

```bash
# Test productpage service
kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" \
  -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"
```

### 4. Configure Ingress Gateway

```bash
# Create Bookinfo Gateway
cat <<'EOF' > bookinfo-gateway.yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: default
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: default
spec:
  hosts:
  - "*"
  gateways:
  - bookinfo-gateway
  http:
  - route:
    - destination:
        host: productpage
        port:
          number: 9080
EOF
kubectl apply -f bookinfo-gateway.yaml

# Check Gateway
kubectl get gateway.networking.istio.io

# Check VirtualService
kubectl get virtualservice
```

### 5. Configure External Access

```bash
# Get Ingress Gateway External IP
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway \
  -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')

export GATEWAY_URL=$INGRESS_HOST:$INGRESS_PORT

# Access application
echo "http://$GATEWAY_URL/productpage"

# Access in browser or verify with curl
curl -s "http://$GATEWAY_URL/productpage" | grep -o "<title>.*</title>"
```

## Istio Removal

These cleanup commands are for a disposable lab. Purging removes shared mesh resources; remove injected workloads or restart them without injection before uninstalling a live mesh. Helm uninstall retains CRDs.

### Removal Using istioctl

```bash
# Remove sample application
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f bookinfo-gateway.yaml

# Remove Istio
istioctl uninstall --purge -y

# Remove istio-system namespace
kubectl delete namespace istio-system

# Remove Istio label
kubectl label namespace default istio-injection-
```

### Removal Using Helm

```bash
# Remove Ingress Gateway
helm delete istio-ingressgateway -n istio-system

# Remove istiod
helm delete istiod -n istio-system

# Remove istio-base
helm delete istio-base -n istio-system

# Remove namespaces
kubectl delete namespace istio-system
```

## Troubleshooting

### Common Issues

#### 1. Sidecar Auto-Injection Failure

**Symptom**: Envoy sidecar is not injected into pod

**Solution**:
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled --overwrite

# Check Webhook
kubectl get mutatingwebhookconfiguration
```

#### 2. istiod Pod Not Starting

**Symptom**: istiod pod is in Pending or CrashLoopBackOff state

**Solution**:
```bash
# Check pod status
kubectl get pods -n istio-system

# Check pod events
kubectl describe pod -n istio-system -l app=istiod

# Check logs
kubectl logs -n istio-system -l app=istiod

# Check resources
kubectl top nodes
kubectl describe nodes
```

#### 3. Ingress Gateway Not Receiving External IP

**Symptom**: LoadBalancer type service is in Pending state

**Solution**:
```bash
# Check service status
kubectl get svc -n istio-system istio-ingressgateway

# Check AWS Load Balancer Controller
kubectl get deployment -n kube-system aws-load-balancer-controller

# Check events
kubectl describe svc -n istio-system istio-ingressgateway
```

### Debugging Tools

#### istioctl analyze

```bash
# Analyze entire cluster
istioctl analyze -A

# Analyze specific namespace
istioctl analyze -n default
```

#### istioctl proxy-status

```bash
# Check all proxy status
istioctl proxy-status

# Check specific pod proxy status
istioctl proxy-status <POD_NAME>.<NAMESPACE>
```

#### istioctl dashboard

```bash
# Launch Kiali dashboard
istioctl dashboard kiali

# Launch Grafana dashboard
istioctl dashboard grafana

# Launch Prometheus dashboard
istioctl dashboard prometheus

# Envoy admin interface
istioctl dashboard envoy <POD_NAME>.<NAMESPACE>
```

### Log Collection

```bash
# Control Plane logs
kubectl logs -n istio-system -l app=istiod

# Ingress Gateway logs
kubectl logs -n istio-system -l app=istio-ingressgateway

# Envoy logs for specific pod
kubectl logs <POD_NAME> -c istio-proxy

# Save all Istio-related logs to file
istioctl bug-report
```

## Next Steps

Istio installation is complete! Now refer to the following documents to start using Istio:

1. **[Basic Concepts](02-basic-concepts.md)**: Understand Istio core concepts and architecture
2. **[Traffic Management](traffic-management/README.md)**: Learn Gateway, VirtualService, DestinationRule
3. **[Security](security/README.md)**: Configure mTLS, authentication, authorization

## References

- [Istio Official Installation Guide](https://istio.io/latest/docs/setup/install/)
- [Istio Profile Documentation](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [Istio EKS platform guidance](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Istio Troubleshooting Guide](https://istio.io/latest/docs/ops/diagnostic-tools/)

- [EKS Fargate restrictions](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Istio 1.31 release and artifact migration](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)
