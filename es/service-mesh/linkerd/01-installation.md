# Instalación y configuración de Linkerd

> **Versiones compatibles**: Linkerd 2.16+
> **Última actualización**: February 22, 2026

## Descripción general

Este documento cubre varios métodos para instalar Linkerd en su clúster de Kubernetes. Explica de forma integral la instalación de la herramienta CLI, la instalación del control plane, la configuración de alta disponibilidad (HA) y las instalaciones de extensiones, incluidas Viz, Jaeger y Multicluster.

## Requisitos previos

### Versión de Kubernetes

| Versión de Linkerd | Versión mínima de Kubernetes | Versión recomendada de Kubernetes |
|-----------------|---------------------------|-------------------------------|
| 2.16.x | 1.25+ | 1.28+ |
| 2.15.x | 1.24+ | 1.27+ |
| 2.14.x | 1.22+ | 1.26+ |

### Requisitos del clúster

```yaml
# Minimum Requirements
CPU: 100m (entire control plane)
Memory: 200Mi (entire control plane)
Nodes: 1+ (3+ recommended for production)

# Recommended Requirements (Production)
CPU: 500m - 1000m
Memory: 500Mi - 1Gi
Nodes: 3+ (HA configuration)
```

### Requisitos de red

- Puerto TCP 443: comunicación de Webhook
- Puerto TCP 8443: inyector de Proxy
- Puerto TCP 8089: API de Tap
- Resolución DNS dentro del clúster

### Validación previa

```bash
# Run pre-flight checks if Linkerd CLI is installed
linkerd check --pre

# Expected output:
# kubernetes-api
# --------------
# √ can initialize the client
# √ can query the Kubernetes API
#
# kubernetes-version
# ------------------
# √ is running the minimum Kubernetes API version
#
# pre-kubernetes-setup
# --------------------
# √ control plane namespace does not already exist
# √ can create non-namespaced resources
# √ can create ServiceAccounts
# √ can create Services
# √ can create Deployments
# √ can create CronJobs
# √ can create ConfigMaps
# √ can create Secrets
# √ can read Secrets
# √ can read extension-apiserver-authentication configmap
# √ no clock skew detected
#
# Status check results are √
```

## Instalación de la CLI de Linkerd

### Linux/macOS (curl)

```bash
# Install latest stable version
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh

# Add to PATH
export PATH=$HOME/.linkerd2/bin:$PATH

# Permanently add to PATH (bash)
echo 'export PATH=$HOME/.linkerd2/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Permanently add to PATH (zsh)
echo 'export PATH=$HOME/.linkerd2/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

### Instalación de una versión específica

```bash
# Install specific version (e.g., 2.16.0)
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh -s -- --version stable-2.16.0

# Install edge version
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install-edge | sh
```

### macOS (Homebrew)

```bash
# Install via Homebrew
brew install linkerd

# Upgrade
brew upgrade linkerd
```

### Windows (Chocolatey)

```powershell
# Install via Chocolatey
choco install linkerd2

# Upgrade
choco upgrade linkerd2
```

### Windows (instalación manual)

```powershell
# Download in PowerShell
$version = "stable-2.16.0"
$arch = "windows-amd64"
$url = "https://github.com/linkerd/linkerd2/releases/download/$version/linkerd2-cli-$version-$arch.exe"

Invoke-WebRequest -Uri $url -OutFile linkerd.exe

# Add to PATH or move to desired location
Move-Item linkerd.exe C:\tools\linkerd.exe
```

### Verificar la instalación

```bash
# Check version
linkerd version

# Example output:
# Client version: stable-2.16.0
# Server version: unavailable (when server not installed)
```

## Instalación del control plane

### Instalación básica (CLI)

```bash
# Step 1: Install CRDs
linkerd install --crds | kubectl apply -f -

# Step 2: Install control plane
linkerd install | kubectl apply -f -

# Verify installation
linkerd check

# Expected output:
# kubernetes-api
# --------------
# √ can initialize the client
# √ can query the Kubernetes API
#
# linkerd-existence
# -----------------
# √ 'linkerd-config' config map exists
# √ heartbeat ServiceAccount exist
# √ control plane replica sets are ready
# √ no unschedulable pods
# √ control plane pods are ready
# √ cluster networks contains all pods
# √ cluster networks contains all services
#
# linkerd-config
# --------------
# √ control plane Namespace exists
# √ control plane ClusterRoles exist
# √ control plane ClusterRoleBindings exist
# √ control plane ServiceAccounts exist
# √ control plane CustomResourceDefinitions exist
# √ control plane MutatingWebhookConfigurations exist
# √ control plane ValidatingWebhookConfigurations exist
# √ proxy-init container runs as root user if docker container runtime is used
#
# linkerd-identity
# ----------------
# √ certificate config is valid
# √ trust anchors are using supported crypto algorithm
# √ trust anchors are within their validity period
# √ trust anchors are valid for at least 60 days
# √ issuer cert is using supported crypto algorithm
# √ issuer cert is within its validity period
# √ issuer cert is valid for at least 60 days
# √ issuer cert is issued by the trust anchor
#
# linkerd-webhooks-and-apisvc-tls
# -------------------------------
# √ proxy-injector webhook has valid cert
# √ proxy-injector cert is valid for at least 60 days
# √ sp-validator webhook has valid cert
# √ sp-validator cert is valid for at least 60 days
# √ policy-validator webhook has valid cert
# √ policy-validator cert is valid for at least 60 days
#
# linkerd-version
# ---------------
# √ can determine the latest version
# √ cli is up-to-date
#
# control-plane-version
# ---------------------
# √ can retrieve the control plane version
# √ control plane is up-to-date
# √ control plane and cli versions match
#
# Status check results are √
```

### Vista previa de los manifiestos de instalación

```bash
# Preview resources to be installed
linkerd install --crds > linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml

# Review and apply
kubectl apply -f linkerd-crds.yaml
kubectl apply -f linkerd-control-plane.yaml
```

### Instalación mediante Helm

Helm permite una configuración más detallada.

#### Agregar repositorio de Helm

```bash
# Add Linkerd Helm repository
helm repo add linkerd https://helm.linkerd.io/stable
helm repo update

# Repository for edge versions
helm repo add linkerd-edge https://helm.linkerd.io/edge
```

#### Generar certificados

Los certificados deben proporcionarse al instalar con Helm.

```bash
# Install step CLI (for certificate generation)
# macOS
brew install step

# Linux
wget https://dl.step.sm/gh-release/cli/docs-cli-install/v0.25.0/step-cli_0.25.0_amd64.deb
sudo dpkg -i step-cli_0.25.0_amd64.deb

# Generate Trust Anchor (Root CA)
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h  # 10 years

# Generate Issuer certificate
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca \
  --not-after=8760h \  # 1 year
  --no-password \
  --insecure \
  --ca ca.crt \
  --ca-key ca.key
```

#### Instalar CRDs con Helm

```bash
# Install CRDs
helm install linkerd-crds linkerd/linkerd-crds \
  -n linkerd \
  --create-namespace \
  --wait
```

#### Instalar control plane con Helm

```bash
# Install control plane
helm install linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait
```

#### Usar un archivo de valores de Helm

```yaml
# values.yaml
# Proxy resource settings
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi

# Proxy log level
proxyLogLevel: warn,linkerd=info

# Proxy log format
proxyLogFormat: plain

# Identity settings
identity:
  issuer:
    clockSkewAllowance: 20s
    issuanceLifetime: 24h0m0s

# Control plane resources
controllerResources: &controller_resources
  cpu:
    request: 100m
    limit: 1000m
  memory:
    request: 50Mi
    limit: 250Mi

destinationResources: *controller_resources
identityResources: *controller_resources
proxyInjectorResources: *controller_resources

# Pod anti-affinity settings
enablePodAntiAffinity: false

# Namespace metadata
namespace:
  labels:
    linkerd.io/control-plane-ns: linkerd
```

```bash
# Install with values file
helm install linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  -f values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait
```

## Instalación de alta disponibilidad (HA)

Se recomienda la configuración de alta disponibilidad para entornos de producción.

### Instalación de HA mediante CLI

```bash
# Install with HA profile
linkerd install --crds | kubectl apply -f -
linkerd install --ha | kubectl apply -f -
```

### Instalación de HA mediante Helm

```yaml
# ha-values.yaml
# HA base settings
enablePodAntiAffinity: true

# Control plane replicas
controllerReplicas: 3

# Destination controller settings
destination:
  replicas: 3
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi

# Identity controller settings
identity:
  replicas: 3
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 10Mi
      limit: 250Mi

# Proxy Injector settings
proxyInjector:
  replicas: 3
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi

# PodDisruptionBudget settings
podDisruptionBudget:
  maxUnavailable: 1

# Proxy resources (increased for HA)
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi

# Pod anti-affinity
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 100
    podAffinityTerm:
      labelSelector:
        matchLabels:
          linkerd.io/control-plane-component: destination
      topologyKey: kubernetes.io/hostname

# Topology spread constraints
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        linkerd.io/control-plane-ns: linkerd
```

```bash
# Install with HA values
helm install linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  -f ha-values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait
```

### Verificar la configuración de HA

```bash
# Check control plane Pod distribution
kubectl get pods -n linkerd -o wide

# Check PodDisruptionBudget
kubectl get pdb -n linkerd

# Verify anti-affinity (deployed on different nodes)
kubectl get pods -n linkerd -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
```

## Instalación de extensiones

### Extensión Viz (Dashboard y métricas)

La extensión Viz proporciona las funcionalidades de observabilidad de Linkerd.

#### Instalar con CLI

```bash
# Install Viz extension
linkerd viz install | kubectl apply -f -

# Verify installation
linkerd viz check

# Open dashboard
linkerd viz dashboard &
```

#### Instalar con Helm

```bash
# Viz extension Helm installation
helm install linkerd-viz linkerd/linkerd-viz \
  -n linkerd-viz \
  --create-namespace \
  --wait
```

#### Personalizar valores de Viz

```yaml
# viz-values.yaml
# Prometheus settings
prometheus:
  enabled: true
  resources:
    cpu:
      request: 300m
      limit: 1000m
    memory:
      request: 300Mi
      limit: 1Gi
  persistence:
    enabled: true
    storageClass: gp3
    size: 10Gi

# Disable Grafana (when using external Grafana)
grafana:
  enabled: false

# Dashboard settings
dashboard:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
  # Disable authentication (development only)
  # enforcedHostRegexp: ""

# Tap settings
tap:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi

# Metrics API settings
metricsAPI:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
```

```bash
# Install with custom values
helm install linkerd-viz linkerd/linkerd-viz \
  -n linkerd-viz \
  --create-namespace \
  -f viz-values.yaml \
  --wait
```

### Extensión Jaeger (trazado distribuido)

#### Instalar con CLI

```bash
# Install Jaeger extension
linkerd jaeger install | kubectl apply -f -

# Verify installation
linkerd jaeger check
```

#### Instalar con Helm

```bash
# Jaeger extension Helm installation
helm install linkerd-jaeger linkerd/linkerd-jaeger \
  -n linkerd-jaeger \
  --create-namespace \
  --wait
```

#### Personalizar valores de Jaeger

```yaml
# jaeger-values.yaml
# Collector settings
collector:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi

# Jaeger UI/Query settings
jaeger:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi

# Sampling settings
webhook:
  collectorSvcAddr: collector.linkerd-jaeger:55678
  collectorSvcAccount: collector
```

### Extensión Multicluster

#### Instalar con CLI

```bash
# Install Multicluster extension
linkerd multicluster install | kubectl apply -f -

# Verify installation
linkerd multicluster check
```

#### Instalar con Helm

```bash
# Multicluster extension Helm installation
helm install linkerd-multicluster linkerd/linkerd-multicluster \
  -n linkerd-multicluster \
  --create-namespace \
  --wait
```

#### Valores de Multicluster

```yaml
# multicluster-values.yaml
# Gateway settings
gateway:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
  # LoadBalancer settings (for EKS)
  serviceType: LoadBalancer
  loadBalancerIP: ""
  # When using NLB
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

# Service Account settings
remoteMirrorServiceAccountName: linkerd-service-mirror-remote-access
```

## Configuración específica para Amazon EKS

### Preparación del clúster de EKS

```bash
# Create EKS cluster (using eksctl)
eksctl create cluster \
  --name linkerd-cluster \
  --version 1.28 \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Update kubeconfig
aws eks update-kubeconfig --name linkerd-cluster --region us-west-2
```

### Compatibilidad con CNI de EKS

Linkerd es compatible con la mayoría de los CNI.

```bash
# Check Amazon VPC CNI version
kubectl describe daemonset aws-node -n kube-system | grep Image

# Install Linkerd CNI plugin (optional, for use with Amazon VPC CNI)
linkerd install-cni | kubectl apply -f -
```

### Configuración de IAM de EKS

```yaml
# linkerd-service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: linkerd-destination
  namespace: linkerd
  annotations:
    # When using IRSA (if needed)
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/LinkerdDestinationRole
```

### Configuración de Ingress de EKS (AWS Load Balancer Controller)

```yaml
# linkerd-viz-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: linkerd-viz
  namespace: linkerd-viz
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:ACCOUNT_ID:certificate/CERT_ID
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/healthcheck-path: /ready
spec:
  rules:
  - host: linkerd.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web
            port:
              number: 8084
```

### Configuración de gateway NLB de EKS (Multicluster)

```yaml
# multicluster-gateway-nlb.yaml
# Helm values
gateway:
  serviceType: LoadBalancer
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
```

### Configuración del Security Group de EKS

```bash
# Allow required ports in cluster security group
# - TCP 4143: Linkerd proxy
# - TCP 4191: Linkerd proxy metrics
# - TCP 8443: Proxy injector webhook
# - TCP 8089: Tap API

# Add security group rules with eksctl (example)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 4143 \
  --source-group sg-xxxxxxxxx
```

## Verificación y validación de la instalación

### Comprobación completa del estado

```bash
# Comprehensive status check
linkerd check

# Status check including extensions
linkerd check --proxy

# Viz extension status check
linkerd viz check

# Multicluster extension status check
linkerd multicluster check

# Jaeger extension status check
linkerd jaeger check
```

### Comprobación del estado de los componentes

```bash
# Control plane Pod status
kubectl get pods -n linkerd

# Extension Pod status
kubectl get pods -n linkerd-viz
kubectl get pods -n linkerd-jaeger
kubectl get pods -n linkerd-multicluster

# Service status
kubectl get svc -n linkerd
kubectl get svc -n linkerd-viz

# Check CRDs
kubectl get crds | grep linkerd
```

### Prueba con una aplicación de ejemplo

```bash
# Install emojivoto sample app
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/emojivoto.yml | kubectl apply -f -

# Inject proxy
kubectl get -n emojivoto deploy -o yaml | linkerd inject - | kubectl apply -f -

# Verify deployment
kubectl get pods -n emojivoto

# Check statistics
linkerd viz stat deploy -n emojivoto

# Check real-time traffic
linkerd viz top deploy -n emojivoto
```

## Actualización de Linkerd

### Actualización del canal estable

```bash
# Upgrade CLI
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh

# Check new version
linkerd version

# Pre-upgrade check
linkerd check --pre

# Upgrade CRDs
linkerd upgrade --crds | kubectl apply -f -

# Upgrade control plane
linkerd upgrade | kubectl apply -f -

# Verify upgrade
linkerd check

# Upgrade extensions
linkerd viz upgrade | kubectl apply -f -
linkerd viz check
```

### Actualización con Helm

```bash
# Update Helm repository
helm repo update

# Backup current values
helm get values linkerd-control-plane -n linkerd > current-values.yaml

# Upgrade CRDs
helm upgrade linkerd-crds linkerd/linkerd-crds -n linkerd --wait

# Upgrade control plane
helm upgrade linkerd-control-plane linkerd/linkerd-control-plane \
  -n linkerd \
  -f current-values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set-file identity.issuer.tls.crtPEM=issuer.crt \
  --set-file identity.issuer.tls.keyPEM=issuer.key \
  --wait

# Upgrade Viz extension
helm upgrade linkerd-viz linkerd/linkerd-viz -n linkerd-viz --wait
```

### Canal Edge

```bash
# Install edge version (latest features, more frequent updates)
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install-edge | sh

# Edge Helm repository
helm repo add linkerd-edge https://helm.linkerd.io/edge
```

### Actualización del data plane (reinicio progresivo del Proxy)

```bash
# Restart all meshed workloads to apply new proxy
kubectl rollout restart deploy -n my-namespace

# Or specific Deployment only
kubectl rollout restart deploy/my-app -n my-namespace

# Check proxy version
linkerd viz stat deploy -n my-namespace -o wide
```

## Solución de problemas

### Problemas comunes de instalación

#### Fallo de conexión de Webhook

```bash
# Symptom: Proxy injection not working
# Cause: Cannot connect to webhook service

# Solution 1: Check webhook service
kubectl get svc -n linkerd linkerd-proxy-injector

# Solution 2: Check webhook configuration
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml

# Solution 3: Check network policies
kubectl get networkpolicy -n linkerd
```

#### Problemas de certificados

```bash
# Symptom: Identity-related errors
# Certificate errors when running linkerd check

# Solution: Check certificate status
linkerd check --proxy

# Check trust anchor expiration
kubectl get secret linkerd-identity-trust-roots -n linkerd -o json | \
  jq -r '.data["ca-bundle.crt"]' | base64 -d | \
  openssl x509 -noout -dates

# Check issuer certificate
kubectl get secret linkerd-identity-issuer -n linkerd -o json | \
  jq -r '.data["crt.pem"]' | base64 -d | \
  openssl x509 -noout -dates
```

#### Falta de recursos

```bash
# Symptom: Pods stuck in Pending state
# Cause: Insufficient node resources

# Solution: Check resource requests
kubectl describe pod -n linkerd <pod-name>

# Check node resources
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### Comandos de depuración

```bash
# Check control plane logs
kubectl logs -n linkerd deploy/linkerd-destination -c destination
kubectl logs -n linkerd deploy/linkerd-identity
kubectl logs -n linkerd deploy/linkerd-proxy-injector

# Check proxy logs
kubectl logs <pod-name> -c linkerd-proxy

# Check events
kubectl get events -n linkerd --sort-by='.lastTimestamp'

# Check proxy status
linkerd diagnostics proxy-metrics <pod-name>
```

## Desinstalación

### Desinstalar con CLI

```bash
# Remove extensions first
linkerd viz uninstall | kubectl delete -f -
linkerd jaeger uninstall | kubectl delete -f -
linkerd multicluster uninstall | kubectl delete -f -

# Remove control plane
linkerd uninstall | kubectl delete -f -
```

### Desinstalar con Helm

```bash
# Remove extensions
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-jaeger -n linkerd-jaeger
helm uninstall linkerd-multicluster -n linkerd-multicluster

# Remove control plane
helm uninstall linkerd-control-plane -n linkerd

# Remove CRDs
helm uninstall linkerd-crds -n linkerd

# Remove namespaces
kubectl delete namespace linkerd linkerd-viz linkerd-jaeger linkerd-multicluster
```

## Próximos pasos

- [Arquitectura](./02-architecture.md): Comprensión detallada de los componentes internos de Linkerd
- [Gestión de tráfico](./03-traffic-management.md): Configuración de ServiceProfile y división de tráfico
- [Seguridad](./04-security.md): Configuración de mTLS y políticas de autorización

## Referencias

- [Guía de instalación de Linkerd](https://linkerd.io/2/getting-started/)
- [Documentación de Helm Chart](https://linkerd.io/2/tasks/install-helm/)
- [Guía de instalación de HA](https://linkerd.io/2/features/ha/)
- [Guía de EKS](https://linkerd.io/2/reference/cluster-configuration/)
