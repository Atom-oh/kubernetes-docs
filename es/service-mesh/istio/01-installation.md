# Instalación y configuración inicial de Istio

> **Última actualización**: October 12, 2026 · Versión fijada de instalación: Istio 1.31.1

A fecha del 12 de octubre de 2026, Istio 1.31.1 es el parche actual de la versión 1.31; corrige una alternativa de texto sin formato de `BackendTLSPolicy`. Los ejemplos de comandos Helm a continuación se han actualizado desde 1.31.0; la representación de ese chart anterior no valida todos los valores de la versión 1.31.1, por lo que debe generar e inspeccionar el chart seleccionado antes de aplicarlo.

Este documento abarca cómo instalar y configurar inicialmente Istio en un clúster de Amazon EKS.

## Tabla de contenido

1. [Requisitos previos](#prerequisites)
2. [Elegir un método de instalación](#choosing-an-installation-method)
3. [Instalación mediante istioctl](#installation-using-istioctl)
4. [Instalación mediante Helm](#installation-using-helm)
5. [Instalación declarativa con istioctl](#declarative-installation-with-istioctl)
6. [Perfiles de instalación](#installation-profiles)
7. [Verificación de la instalación](#installation-verification)
8. [Implementación de la aplicación de ejemplo](#sample-application-deployment)
9. [Eliminación de Istio](#istio-removal)
10. [Solución de problemas](#troubleshooting)

## Requisitos previos

Antes de instalar Istio, se deben cumplir los siguientes requisitos:

### 1. Clúster de Amazon EKS

- **Versión de Kubernetes**: EKS 1.34–1.37 para este ejemplo de Istio 1.31.1 (revisado el 12 de octubre de 2026). Istio 1.31 admite 1.32–1.37; EKS 1.31–1.33 tienen soporte extendido y 1.34–1.37 tienen soporte estándar. Consulte tanto la [matriz de Istio](https://istio.io/latest/docs/releases/supported-releases/) como el [ciclo de vida de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html).
- **Tipo de nodo**: Como mínimo 2 nodos de trabajo (recomendado: 3 o más)
- **Tamaño de nodo**: Como mínimo 2 vCPU, 4GB de RAM (recomendado: t3.medium o superior)

Estos ejemplos están dirigidos a nodos de trabajo Linux EC2. Fargate no puede ejecutar los DaemonSets/la red con privilegios necesarios para estas rutas de instalación de Istio. EKS Auto Mode tiene un modelo de red y balanceo de carga administrado diferente; valide sus requisitos previos por separado.

### 2. Instalación y configuración de kubectl

```bash
# Verify kubectl installation
kubectl version --client

# Verify EKS cluster connection
kubectl get nodes
```

### 3. Herramientas necesarias

- **AWS CLI**: 2.x o superior
- **eksctl**: (Opcional) Para la gestión de clústeres
- **Helm**: una versión actualmente compatible de Helm 3 o Helm 4 (mínimo 3.6; consulte la guía de instalación oficial)

### 4. Recursos del clúster

Solicitudes de planificación ilustrativas, no mínimos universales; dimensione según la carga medida:
- **Control Plane**: 1 vCPU, 1.5GB de RAM
- **Sidecar (por Pod)**: 0.1 vCPU, 128MB de RAM

## Elegir un método de instalación

Elija una ruta de instalación compatible; no ejecute las instalaciones de istioctl y Helm en el mismo Control Plane:

| Método | Ventajas | Desventajas | Caso de uso recomendado |
|------|------|------|---------------|
| **istioctl** | Simple y rápido, proporciona funciones de validación | Requiere reconciliación explícita en la automatización | Desarrollo y producción |
| **Helm** | Compatible con GitOps, fácil gestión de versiones | La configuración puede ser compleja | Entornos de producción, canalizaciones CI/CD |

## Instalación mediante istioctl

istioctl es la herramienta CLI oficial de Istio y el método de instalación más sencillo.

### 1. Instalar istioctl

```bash
# Download the current 1.31 patch
curl -fsSL https://istio.io/downloadIstio | ISTIO_VERSION=1.31.1 sh -

# Add istioctl to PATH
cd istio-1.31.1
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

## Instalación mediante Helm

Los charts de la versión 1.31.0 generados durante la revisión anterior no contenían un perfil de plataforma `eks`. Los ejemplos de charts a continuación ahora fijan la versión 1.31.1, pero esta revisión no generó el chart de ese parche; inspeccione el chart seleccionado antes de instalarlo. Estos ejemplos omiten `global.platform=eks` en lugar de suponer que existe un perfil, y usan requisitos previos explícitos de EKS y configuraciones de balanceador de carga.

Helm es un administrador de paquetes de Kubernetes adecuado para flujos de trabajo GitOps.

### 1. Agregar el repositorio Helm

```bash
# Add Istio Helm repository
helm repo add istio https://blob.istio.io/istio-release/charts
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
  --set defaultRevision=default \
  --version 1.31.1
```

### 3. Instalar istiod

istiod es el Control Plane de Istio.

```bash
# Install istiod chart
helm install istiod istio/istiod \
  -n istio-system \
  --version 1.31.1 \
  --wait
```

### 4. Instalar Istio Ingress Gateway (opcional)

```bash
# Verify the gateway namespace
kubectl get namespace istio-system

# Install Istio Ingress Gateway
helm install istio-ingressgateway istio/gateway \
  -n istio-system \
  --set labels.istio=ingressgateway \
  --set labels.app=istio-ingressgateway \
  --version 1.31.1 \
  --wait
```

### 5. Instalación personalizada mediante values.yaml

```yaml
# values.yaml
global:
  hub: docker.io/istio
  tag: 1.31.1

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
  --version 1.31.1 \
  -f values.yaml \
  --wait
```

## Instalación declarativa con istioctl

El operador upstream en el clúster quedó obsoleto en la versión 1.23 y se eliminó en la 1.24. `istioctl operator init/remove` y aplicar un objeto IstioOperator al clúster no son métodos de instalación actuales. El [formato de archivo IstioOperator sigue siendo compatible como entrada para istioctl](https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/).

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

## Perfiles de instalación

Istio proporciona diversos perfiles para diferentes casos de uso.

### Perfiles disponibles

| Perfil | Descripción | Componentes | Uso recomendado |
|-------|------|----------|----------|
| **default** | Configuración predeterminada para la implementación de producción | istiod, ingress gateway | La mayoría de los entornos de producción |
| **demo** | Configuración de demostración, no todas las funciones | istiod, ingress gateway, egress gateway, alto muestreo de trazas | Desarrollo y demostraciones |
| **minimal** | Solo se instalan componentes mínimos | Solo istiod | Entornos con recursos limitados |
| **remote** | Para un clúster remoto en un entorno multiclúster | - | Configuración multiclúster |
| **empty** | Sin configuración predeterminada | - | Configuración completamente personalizada |
| **preview** | Incluye funciones experimentales | Diversas funciones experimentales | Entornos de prueba |
| **ambient** | Malla L4 sin Sidecar | istiod, CNI, ztunnel; los waypoints L7 se configuran por separado | Implementaciones Ambient |

La lista de componentes se aplica a istioctl. Helm requiere instalar cada chart por separado; un perfil no instala otros charts.

### Consultar perfiles

```bash
helm show values istio/istiod --version 1.31.1
istioctl manifest generate --set profile=default > default.yaml
istioctl manifest generate --set profile=demo > demo.yaml
diff -u default.yaml demo.yaml
```

### Instalación por perfil

```bash
# Install with demo profile
istioctl install --set profile=demo -y

# Install with minimal profile
istioctl install --set profile=minimal -y
```

### Personalizar perfiles

```bash
# Modify specific settings based on profile
istioctl install --set profile=default \
  --set meshConfig.accessLogFile=/dev/stdout \
  --set components.pilot.k8s.resources.requests.memory=2Gi \
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
kubectl rollout status deployment/istiod -n istio-system
istioctl proxy-status

# Analyze Istio configuration
istioctl analyze -A
```

### 4. Comprobar Webhooks

```bash
# Check MutatingWebhookConfiguration
kubectl get mutatingwebhookconfiguration

# Check ValidatingWebhookConfiguration
kubectl get validatingwebhookconfiguration
```

## Implementación de la aplicación de ejemplo

Istio incluye una aplicación de ejemplo llamada Bookinfo.

Ejecute estos comandos desde el directorio extraído `istio-1.31.1` con el espacio de nombres predeterminado seleccionado (`kubectl config set-context --current --namespace=default`). Para Helm, instale primero el gateway opcional anterior. Los comandos del panel más adelante requieren complementos de telemetría instalados por separado.

### 1. Habilitar la inyección automática de Sidecar para el espacio de nombres

```bash
# Add label to default namespace
kubectl label namespace default istio-injection=enabled --overwrite

# Verify label
kubectl get namespace -L istio-injection
```

Los Pods existentes deben recrearse después de cambiar las etiquetas de inyección. Use un espacio de nombres sin una etiqueta `istio.io/rev` o Ambient en conflicto.

### 2. Implementar la aplicación Bookinfo

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

Estos comandos de limpieza son para un laboratorio desechable. La purga elimina recursos de malla compartidos; elimine las cargas de trabajo inyectadas o reinícielas sin inyección antes de desinstalar una malla en producción. La desinstalación de Helm conserva los CRD.

### Eliminación mediante istioctl

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

### Eliminación mediante Helm

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

## Solución de problemas

### Problemas comunes

#### 1. Error de inyección automática de Sidecar

**Síntoma**: el Sidecar de Envoy no se inyecta en el Pod

**Solución**:
```bash
# Check namespace label
kubectl get namespace -L istio-injection

# Add label if missing
kubectl label namespace default istio-injection=enabled --overwrite

# Check Webhook
kubectl get mutatingwebhookconfiguration
```

#### 2. El Pod de istiod no se inicia

**Síntoma**: el Pod de istiod está en estado Pending o CrashLoopBackOff

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

**Síntoma**: el Service de tipo LoadBalancer está en estado Pending

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

### Recopilación de registros

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

1. **[Conceptos básicos](02-basic-concepts.md)**: Comprenda los conceptos y la arquitectura principales de Istio
2. **[Gestión del tráfico](traffic-management/README.md)**: Aprenda sobre Gateway, VirtualService, DestinationRule
3. **[Seguridad](security/README.md)**: Configure mTLS, autenticación y autorización

## Referencias

- [Guía oficial de instalación de Istio](https://istio.io/latest/docs/setup/install/)
- [Documentación de perfiles de Istio](https://istio.io/latest/docs/setup/additional-setup/config-profiles/)
- [Guía de plataforma EKS de Istio](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Guía de solución de problemas de Istio](https://istio.io/latest/docs/ops/diagnostic-tools/)

- [Restricciones de EKS Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Lanzamiento de Istio 1.31 y migración de artefactos](https://istio.io/latest/news/releases/1.31.x/announcing-1.31/)
