# Instalación y configuración inicial de Istio

Este documento explica cómo instalar y configurar inicialmente Istio en un clúster de Amazon EKS.

## Tabla de contenido

1. [Requisitos previos](#prerequisites)
2. [Elección de un método de instalación](#choosing-an-installation-method)
3. [Instalación con istioctl](#installation-using-istioctl)
4. [Instalación con Helm](#installation-using-helm)
5. [Instalación con Istio Operator](#installation-using-istio-operator)
6. [Perfiles de instalación](#installation-profiles)
7. [Verificación de la instalación](#installation-verification)
8. [Despliegue de aplicación de ejemplo](#sample-application-deployment)
9. [Eliminación de Istio](#istio-removal)
10. [Solución de problemas](#troubleshooting)

## Requisitos previos

Antes de instalar Istio, se deben cumplir los siguientes requisitos:

### 1. Clúster de Amazon EKS

- **Versión de Kubernetes**: 1.28 o superior (recomendado: 1.34)
- **Tipo de nodo**: Mínimo 2 nodos de trabajo (recomendado: 3 o más)
- **Tamaño de nodo**: Mínimo 2 vCPU, 4GB de RAM (recomendado: t3.medium o superior)

### 2. Instalación y configuración de kubectl

```bash
# Verify kubectl installation
kubectl version --client

# Verify EKS cluster connection
kubectl get nodes
```

### 3. Herramientas necesarias

- **AWS CLI**: 2.x o superior
- **eksctl**: (Opcional) Para la administración de clústeres
- **Helm**: 3.x o superior (si se utiliza el método de instalación con Helm)

### 4. Recursos del clúster

Requisitos mínimos de recursos:
- **Control Plane**: 1 vCPU, 1.5GB de RAM
- **Sidecar (por Pod)**: 0.1 vCPU, 128MB de RAM

## Elección de un método de instalación

Istio proporciona tres métodos principales de instalación:

| Método | Ventajas | Desventajas | Caso de uso recomendado |
|------|------|------|---------------|
| **istioctl** | Simple y rápido, proporciona funciones de validación | Difícil de automatizar | Entornos de desarrollo y prueba |
| **Helm** | Compatible con GitOps, gestión de versiones sencilla | La configuración puede ser compleja | Entornos de producción, pipelines de CI/CD |
| **Istio Operator** | Gestión declarativa, actualizaciones automáticas | Se necesitan recursos adicionales | Entornos de producción a gran escala |

## Instalación con istioctl

istioctl es la herramienta CLI oficial de Istio y el método de instalación más sencillo.

### 1. Instalar istioctl

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

### 2. Validación del clúster previa a la instalación

```bash
# Verify cluster meets Istio installation requirements
istioctl x precheck
```

### 3. Instalar Istio

```bash
# Install with default profile
istioctl install --set profile=default -y

# Check installation progress
kubectl get pods -n istio-system
```

### 4. Verificar la instalación

```bash
# Check Istio components
kubectl get all -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod
```

## Instalación con Helm

Helm es un administrador de paquetes de Kubernetes adecuado para flujos de trabajo de GitOps.

### 1. Agregar el repositorio de Helm

```bash
# Add Istio Helm repository
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update
```

### 2. Instalar istio-base

istio-base instala los CRD (Custom Resource Definitions) de Istio.

```bash
# Create istio-system namespace
kubectl create namespace istio-system

# Install istio-base chart
helm install istio-base istio/base \
  -n istio-system \
  --version 1.28.0
```

### 3. Instalar istiod

istiod es el Control Plane de Istio.

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.28.0 \
  --wait
```

### 4. Instalar Istio Ingress Gateway (opcional)

```bash
# Create istio-ingress namespace
kubectl create namespace istio-ingress

# Install Istio Ingress Gateway
helm install istio-ingress istio/gateway \
  -n istio-ingress \
  --version 1.28.0 \
  --wait
```

### 5. Instalación personalizada con values.yaml

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

## Instalación con Istio Operator

Istio Operator administra Istio de manera declarativa.

### 1. Instalar Istio Operator

```bash
# Install Operator
istioctl operator init

# Verify Operator installation
kubectl get pods -n istio-operator
```

### 2. Crear el recurso IstioOperator

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

### 3. Instalar Istio mediante Operator

```bash
# Apply IstioOperator resource
kubectl create ns istio-system
kubectl apply -f istio-operator.yaml

# Check installation progress
kubectl get istiooperator -n istio-system
```

## Perfiles de instalación

Istio proporciona varios perfiles para distintos casos de uso.

### Perfiles disponibles

| Perfil | Descripción | Componentes | Uso recomendado |
|-------|------|----------|----------|
| **default** | Configuración predeterminada para despliegues de producción | istiod, ingress gateway | La mayoría de los entornos de producción |
| **demo** | Todas las funciones habilitadas, para aprendizaje | istiod, ingress gateway, egress gateway, muestreo de trazas alto | Desarrollo y demostraciones |
| **minimal** | Solo se instalan los componentes mínimos | solo istiod | Entornos con recursos limitados |
| **remote** | Para clúster remoto en un entorno multiclúster | - | Configuración multiclúster |
| **empty** | Sin configuración predeterminada | - | Configuración totalmente personalizada |
| **preview** | Incluye funciones experimentales | Diversas funciones experimentales | Entornos de prueba |

### Consultar perfiles

```bash
# List available profiles
istioctl profile list

# Check specific profile configuration
istioctl profile dump default

# Compare two profiles
istioctl profile diff default demo
```

### Instalación por perfil

```bash
# Install with demo profile
istioctl install --set profile=demo -y

# Install with minimal profile
istioctl install --set profile=minimal -y
```

### Personalización de perfiles

```bash
# Modify specific settings based on profile
istioctl install --set profile=default \
  --set meshConfig.accessLogFile=/dev/stdout \
  --set values.pilot.resources.requests.memory=2Gi \
  -y
```

## Verificación de la instalación

### 1. Comprobar el Control Plane

```bash
# Check all resources in istio-system namespace
kubectl get all -n istio-system

# Check istiod status
kubectl get deployment istiod -n istio-system

# Check istiod logs
kubectl logs -n istio-system -l app=istiod --tail=100
```

### 2. Comprobar la versión de Istio

```bash
# Control Plane version
istioctl version

# Or
kubectl get pods -n istio-system -o yaml | grep image:
```

### 3. Validar la configuración de Istio

```bash
# Check Istio installation status
istioctl verify-install

# Analyze Istio configuration
istioctl analyze -A
```

### 4. Comprobar los Webhooks

```bash
# Check MutatingWebhookConfiguration
kubectl get mutatingwebhookconfiguration

# Check ValidatingWebhookConfiguration
kubectl get validatingwebhookconfiguration
```

## Despliegue de aplicación de ejemplo

Istio incluye una aplicación de ejemplo llamada Bookinfo.

### 1. Habilitar la inyección automática de Sidecar para el Namespace

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled

# Verify label
kubectl get namespace -L istio-injection
```

### 2. Desplegar la aplicación Bookinfo

```bash
# Deploy Bookinfo application
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Check pods (each pod should have 2 containers)
kubectl get pods

# Check services
kubectl get services
```

### 3. Verificar el acceso a la aplicación

```bash
# Test productpage service
kubectl exec "$(kubectl get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" \
  -c ratings -- curl -sS productpage:9080/productpage | grep -o "<title>.*</title>"
```

### 4. Configurar Ingress Gateway

```bash
# Create Bookinfo Gateway
kubectl apply -f samples/bookinfo/networking/bookinfo-gateway.yaml

# Check Gateway
kubectl get gateway

# Check VirtualService
kubectl get virtualservice
```

### 5. Configurar el acceso externo

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

## Eliminación de Istio

### Eliminación con istioctl

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

### Eliminación con Helm

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

### Eliminación con Istio Operator

```bash
# Remove IstioOperator resource
kubectl delete istiooperator istio-control-plane -n istio-system

# Remove Operator
istioctl operator remove

# Remove namespaces
kubectl delete namespace istio-system
kubectl delete namespace istio-operator
```

## Solución de problemas

### Problemas comunes

#### 1. Error en la inyección automática de Sidecar

**Síntoma**: El sidecar de Envoy no se inyecta en el Pod

**Solución**:
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled

# Check Webhook
kubectl get mutatingwebhookconfiguration
```

#### 2. El Pod de istiod no se inicia

**Síntoma**: El Pod de istiod está en estado Pending o CrashLoopBackOff

**Solución**:
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

#### 3. Ingress Gateway no recibe una IP externa

**Síntoma**: El Service de tipo LoadBalancer está en estado Pending

**Solución**:
```bash
# Check service status
kubectl get svc -n istio-system istio-ingressgateway

# Check AWS Load Balancer Controller
kubectl get deployment -n kube-system aws-load-balancer-controller

# Check events
kubectl describe svc -n istio-system istio-ingressgateway
```

### Herramientas de depuración

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

### Recopilación de logs

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

## Próximos pasos

¡La instalación de Istio está completa! Ahora consulte los siguientes documentos para empezar a usar Istio:

1. **[Conceptos básicos](02-basic-concepts.md)**: Comprenda los conceptos fundamentales y la arquitectura de Istio
2. **[Gestión del tráfico](traffic-management/README.md)**: Aprenda sobre Gateway, VirtualService, DestinationRule
3. **[Seguridad](security/README.md)**: Configure mTLS, autenticación y autorización

## Referencias

- [Guía oficial de instalación de Istio](https://istio.io/latest/docs/setup/install/)
- [Documentación de perfiles de Istio](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [AWS EKS Workshop - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
- [Guía de solución de problemas de Istio](https://istio.io/latest/docs/ops/diagnostic-tools/)
