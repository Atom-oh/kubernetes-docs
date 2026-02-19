# Istio Installation and Initial Setup

This document covers how to install and initially configure Istio on an Amazon EKS cluster.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Choosing an Installation Method](#choosing-an-installation-method)
3. [Installation Using istioctl](#installation-using-istioctl)
4. [Installation Using Helm](#installation-using-helm)
5. [Installation Using Istio Operator](#installation-using-istio-operator)
6. [Installation Profiles](#installation-profiles)
7. [Installation Verification](#installation-verification)
8. [Sample Application Deployment](#sample-application-deployment)
9. [Istio Removal](#istio-removal)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

Before installing Istio, the following requirements must be met:

### 1. Amazon EKS Cluster

- **Kubernetes version**: 1.28 or higher (recommended: 1.34)
- **Node type**: Minimum 2 worker nodes (recommended: 3 or more)
- **Node size**: Minimum 2 vCPU, 4GB RAM (recommended: t3.medium or larger)

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
- **Helm**: 3.x or higher (if using Helm installation method)

### 4. Cluster Resources

Minimum resource requirements:
- **Control Plane**: 1 vCPU, 1.5GB RAM
- **Sidecar (per pod)**: 0.1 vCPU, 128MB RAM

## Choosing an Installation Method

Istio provides three main installation methods:

| Method | Advantages | Disadvantages | Recommended Use Case |
|------|------|------|---------------|
| **istioctl** | Simple and fast, provides validation features | Difficult to automate | Development and test environments |
| **Helm** | GitOps friendly, easy version management | Configuration can be complex | Production environments, CI/CD pipelines |
| **Istio Operator** | Declarative management, automatic upgrades | Additional resources needed | Large-scale production environments |

## Installation Using istioctl

istioctl is Istio's official CLI tool and the simplest installation method.

### 1. Install istioctl

```bash
# Download istioctl (latest version)
curl -L https://istio.io/downloadIstio | sh -

# Or download a specific version
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -

# Add istioctl to PATH
cd istio-1.28.0
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

Helm is a Kubernetes package manager suitable for GitOps workflows.

### 1. Add Helm Repository

```bash
# Add Istio Helm repository
helm repo add istio https://istio-release.storage.googleapis.com/charts
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
  --version 1.28.0
```

### 3. Install istiod

istiod is the Istio Control Plane.

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  --wait
```

### 4. Install Istio Ingress Gateway (Optional)

```bash
# Create istio-ingress namespace
kubectl create namespace istio-ingress

# Install Istio Ingress Gateway
helm install istio-ingress istio/gateway \
  -n istio-ingress \
  --version 1.28.0 \
  --wait
```

### 5. Custom Installation Using values.yaml

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.28.0

pilot:
  autoscaleEnabled: true
  autoscaleMin: 2
  autoscaleMax: 5
  resources:
    requests:
      cpu: 500m
      memory: 2048Mi

# AWS EKS specific settings
meshConfig:
  accessLogFile: /dev/stdout
  enableTracing: true
  defaultConfig:
    tracing:
      sampling: 100.0
```

```bash
# Install using values.yaml file
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  -f values.yaml \
  --wait
```

## Installation Using Istio Operator

Istio Operator manages Istio in a declarative manner.

### 1. Install Istio Operator

```bash
# Install Operator
istioctl operator init

# Verify Operator installation
kubectl get pods -n istio-operator
```

### 2. Create IstioOperator Resource

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

### 3. Install Istio via Operator

```bash
# Apply IstioOperator resource
kubectl create ns istio-system
kubectl apply -f istio-operator.yaml

# Check installation progress
kubectl get istiooperator -n istio-system
```

## Installation Profiles

Istio provides various profiles for different use cases.

### Available Profiles

| Profile | Description | Components | Recommended Use |
|-------|------|----------|----------|
| **default** | Default settings for production deployment | istiod, ingress gateway | Most production environments |
| **demo** | All features enabled, for learning | istiod, ingress gateway, egress gateway, high trace sampling | Development and demos |
| **minimal** | Only minimal components installed | istiod only | Resource-constrained environments |
| **remote** | For remote cluster in multi-cluster environment | - | Multi-cluster setup |
| **empty** | No default configuration | - | Complete custom setup |
| **preview** | Includes experimental features | Various experimental features | Test environments |

### Check Profiles

```bash
# List available profiles
istioctl profile list

# Check specific profile configuration
istioctl profile dump default

# Compare two profiles
istioctl profile diff default demo
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
  --set values.pilot.resources.requests.memory=2Gi \
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
istioctl verify-install

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

### 1. Enable Automatic Sidecar Injection for Namespace

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled

# Verify label
kubectl get namespace -L istio-injection
```

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
kubectl apply -f samples/bookinfo/networking/bookinfo-gateway.yaml

# Check Gateway
kubectl get gateway

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

### Removal Using istioctl

```bash
# Remove sample application
kubectl delete -f samples/bookinfo/platform/kube/bookinfo.yaml
kubectl delete -f samples/bookinfo/networking/bookinfo-gateway.yaml

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
helm delete istio-ingress -n istio-ingress

# Remove istiod
helm delete istiod -n istio-system

# Remove istio-base
helm delete istio-base -n istio-system

# Remove namespaces
kubectl delete namespace istio-system
kubectl delete namespace istio-ingress
```

### Removal Using Istio Operator

```bash
# Remove IstioOperator resource
kubectl delete istiooperator istio-control-plane -n istio-system

# Remove Operator
istioctl operator remove

# Remove namespaces
kubectl delete namespace istio-system
kubectl delete namespace istio-operator
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
kubectl label namespace default istio-injection=enabled

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
- [AWS EKS Workshop - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
- [Istio Troubleshooting Guide](https://istio.io/latest/docs/ops/diagnostic-tools/)
