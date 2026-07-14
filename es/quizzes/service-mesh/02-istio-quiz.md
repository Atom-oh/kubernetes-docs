# Cuestionario de Istio

> **Versión compatible**: Istio 1.28.0
> **Versión de EKS**: 1.34 (Kubernetes 1.28+)
> **Última actualización**: February 19, 2026

Este cuestionario evalúa tu comprensión de la service mesh de Istio.

## Pregunta 1: Conceptos básicos de Service Mesh

<details>
<summary>¿Qué es una service mesh y cuáles son sus principales características?</summary>

**Respuesta:**
Una service mesh es una capa de infraestructura que gestiona la comunicación entre servicios, lo que te permite controlar y observar la comunicación entre servicios sin modificar el código de la aplicación.

**Características principales:**
1. **Gestión de tráfico**: Controla el flujo de tráfico entre servicios
   - Enrutamiento, balanceo de carga, despliegues Canary
   - Timeout, Retry, Circuit Breaker
   - Duplicación de tráfico y pruebas shadow

2. **Seguridad**: Cifrado y autenticación para la comunicación entre servicios
   - mTLS automático (TLS mutuo)
   - Authorization Policy (control de acceso)
   - Request Authentication (JWT)

3. **Observabilidad**: Visibilidad de la comunicación entre servicios
   - Recopilación de métricas (Prometheus)
   - Trazado distribuido (Jaeger/Zipkin)
   - Registro y visualización (Kiali, Grafana)

**Características de Istio:**
- Se superpone de forma transparente a las aplicaciones distribuidas existentes
- Usa el patrón de proxy sidecar (Envoy)
- Admite Ambient Mode (arquitectura sin sidecar)
- Gestión de políticas mediante configuración declarativa
</details>

## Pregunta 2: Arquitectura de Istio

<details>
<summary>¿Cuáles son los componentes y roles principales de Istio 1.28.0?</summary>

**Respuesta:**
**Control Plane:**
- **Istiod**: Control Plane unificado en un único binario
  - **Service Discovery**: Mantiene el registro de servicios de la mesh
  - **Gestión de configuración**: Almacena y distribuye la configuración de Istio
  - **Gestión de certificados**: Genera y rota certificados para mTLS

**Data Plane:**
- **Envoy Proxy**: Desplegado como sidecar, intermedia toda la comunicación de red
  - Enrutamiento de tráfico y balanceo de carga
  - Cifrado y autenticación mTLS
  - Recopilación de métricas, logs y trazas

**Ambient Mode (opcional):**
- **ztunnel**: Proxy a nivel de nodo (L4)
- **waypoint proxy**: Proxy L7 opcional

**Características clave:**
- Control Plane unificado en un único binario (Istiod)
- Arquitectura escalable y de alta disponibilidad
- Configuración basada en CRD nativa de Kubernetes
- Es posible una reducción de recursos de más del 85% con Ambient Mode
</details>

## Pregunta 3: Gestión de tráfico e integración con Argo Rollouts

<details>
<summary>¿Cómo implementas despliegues Canary automatizados mediante Istio y Argo Rollouts?</summary>

**Respuesta:**
Argo Rollouts se integra con Istio para proporcionar despliegues Canary automáticos basados en métricas.

**1. Definición del recurso Rollout:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: reviews
spec:
  replicas: 5
  strategy:
    canary:
      # Istio traffic control
      trafficRouting:
        istio:
          virtualService:
            name: reviews-vsvc
            routes:
            - primary
          destinationRule:
            name: reviews-destrule
            canarySubsetName: canary
            stableSubsetName: stable

      # Staged deployment
      steps:
      - setWeight: 10    # 10% Canary
      - pause: {duration: 2m}
      - setWeight: 25    # 25% Canary
      - pause: {duration: 2m}
      - setWeight: 50    # 50% Canary
      - pause: {duration: 2m}

      # Automatic metrics analysis
      analysis:
        templates:
        - templateName: success-rate
        - templateName: latency
        startingStep: 1
```

**2. AnalysisTemplate - Rollback automático:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    successCondition: result >= 0.95  # 95% or higher
    failureLimit: 2  # Auto-rollback after 2 failures
    provider:
      prometheus:
        query: |
          sum(rate(istio_requests_total{
            response_code!~"5.*"
          }[2m])) / sum(rate(istio_requests_total[2m]))
```

**Características clave:**
- Progresión/rollback automático basado en métricas
- Aumento gradual del tráfico (10% → 25% → 50% → 100%)
- Análisis de métricas de Prometheus en tiempo real
- Rollback automático inmediato ante errores
</details>

## Pregunta 4: Características de seguridad

<details>
<summary>¿Cuáles son las características de mTLS y Authorization Policy en Istio 1.28.0?</summary>

**Respuesta:**
**Beneficios de mTLS:**
- Cifrado automático de la comunicación entre servicios
- Seguridad mejorada mediante autenticación mutua
- Se aplica sin cambios en el código de la aplicación
- Emisión y renovación automáticas de certificados

**1. PeerAuthentication - Política de mTLS:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # STRICT recommended for production
```

**2. AuthorizationPolicy - Control de acceso detallado:**
```yaml
# Deny by default
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec: {}  # Deny all requests

---
# Allow specific
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]
```

**3. RequestAuthentication - Validación de JWT:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
```

**Buenas prácticas:**
- Usa políticas de denegación predeterminada
- Aplica el principio de privilegio mínimo
- Autenticación basada en Service Account
- Aislamiento de Namespace
</details>

## Pregunta 5: Gateway e Ingress

<details>
<summary>¿Cuál es el rol de Istio Gateway y cómo configuras TLS?</summary>

**Respuesta:**
**Rol de Gateway:**
- Punto de entrada para el tráfico externo hacia los servicios internos del cluster
- Control de tráfico Ingress/Egress
- Terminación TLS y gestión de certificados
- Integración con balanceadores de carga

**Ejemplo de configuración:**
```yaml
# Gateway Definition
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTPS (443)
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com

  # HTTP (80) - Redirect to HTTPS
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
    tls:
      httpsRedirect: true

---
# VirtualService - Connect to Gateway
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: bookinfo-vs
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - bookinfo-gateway
  http:
  - match:
    - uri:
        prefix: /productpage
    route:
    - destination:
        host: productpage
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
```

**Creación del certificado TLS:**
```bash
# Create TLS certificate as Kubernetes Secret
kubectl create -n istio-system secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo.crt
```
</details>

## Pregunta 6: Herramientas de observabilidad

<details>
<summary>¿Qué herramientas de observabilidad proporciona Istio 1.28.0 y cuáles son sus roles?</summary>

**Respuesta:**
**1. Prometheus - Recopilación de métricas:**
```promql
# Golden Signals Monitoring
# 1. Latency (P95)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (Request count)
sum(rate(istio_requests_total[5m]))

# 3. Errors (Error rate)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/ sum(rate(istio_requests_total[5m]))

# 4. Saturation (CPU usage)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

**2. Jaeger - Trazado distribuido:**
```yaml
# Enable Tracing
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% sampling
```

**3. Kiali - Visualización de Service Mesh:**
- Visualización de topología en tiempo real
- Análisis del flujo de tráfico
- Validación de configuración
- Visualización de métricas de rendimiento

**4. Grafana - Dashboards:**
- Istio Service Dashboard
- Istio Workload Dashboard
- Istio Performance Dashboard
- Creación de dashboards personalizados

**Método de acceso:**
```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```
</details>

## Pregunta 7: Ambient Mode

<details>
<summary>¿Qué es Ambient Mode en Istio 1.28.0 y en qué se diferencia de Sidecar Mode?</summary>

**Respuesta:**
**Concepto de Ambient Mode:**
- Arquitectura de service mesh sin sidecar
- ztunnel (proxy L4 a nivel de nodo) + waypoint (proxy L7 opcional)
- Reducción de recursos de más del 85%

**Comparación de arquitectura:**

| Característica | Sidecar Mode | Ambient Mode |
|---------|-------------|--------------|
| Despliegue | Inyección de Envoy por Pod | 1 ztunnel por nodo |
| Uso de recursos | Alto (50-100MB por Pod) | Bajo (50MB por nodo) |
| Complejidad de despliegue | Alta (se necesita redespliegue) | Baja (aplicación transparente) |
| Características L4 | Compatible | Compatible mediante ztunnel |
| Características L7 | Compatibilidad completa | Requiere waypoint |
| Rendimiento | Ligeramente más lento | Rápido (solo L4) |

**Activación de Ambient Mode:**
```bash
# Install Ambient Mode
istioctl install --set profile=ambient -y

# Enable Ambient Mode on Namespace
kubectl label namespace default istio.io/dataplane-mode=ambient
```

**Casos de uso:**
- Entornos con recursos limitados
- Clusters a gran escala (más de 1000 Pods)
- Cuando solo se necesitan características L4
- Adopción gradual de Istio
</details>

## Pregunta 8: Patrones de resiliencia

<details>
<summary>¿Cuáles son las diferencias entre Outlier Detection, Circuit Breaker y Rate Limiting en Istio?</summary>

**Respuesta:**
**1. Outlier Detection - Excluir instancias no saludables:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5       # 5 consecutive failures
      interval: 30s              # Evaluate every 30s
      baseEjectionTime: 30s      # 30s ejection
      maxEjectionPercent: 50     # Max 50% ejection
```

**2. Circuit Breaker - Evitar sobrecargas:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
```

**3. Rate Limiting - Control de tasa de solicitudes:**
```yaml
# Local Rate Limiting
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-rate-limit
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
```

**Diferencias:**
- **Outlier Detection**: Reactivo (excluye tras un error)
- **Circuit Breaker**: Preventivo (limita conexiones)
- **Rate Limiting**: Control de tasa de solicitudes (token bucket)

**Uso combinado:**
```yaml
trafficPolicy:
  connectionPool:     # Circuit Breaker
    tcp:
      maxConnections: 100
  outlierDetection:   # Outlier Detection
    consecutiveErrors: 5
```
</details>

## Pregunta 9: Locality Load Balancing (enrutamiento consciente de zona)

<details>
<summary>¿Qué es la característica Locality Load Balancing de Istio y cómo se utiliza con AWS EKS?</summary>

**Respuesta:**
**Concepto de Locality Load Balancing:**
- Enrutamiento prioritario a servicios en la misma Availability Zone (AZ)
- Latencia de red reducida
- Ahorro en costes de transferencia de datos entre AZ (~85%)

**Configuración:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Same AZ priority, other AZ for failover
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # Same AZ 80%
            "us-east-1/us-east-1b/*": 20  # Other AZ 20%

        # Failover policy
        failover:
        - from: us-east-1
          to: us-west-2
```

**Uso con AWS EKS:**
1. **Ahorro de costes:**
   - Tráfico entre AZ: $0.01/GB
   - Tráfico en la misma AZ: Gratis
   - Ahorro significativo de costes con un enrutamiento del 80% dentro de la misma AZ

2. **Mejora de rendimiento:**
   - Latencia dentro de una AZ: ~1ms
   - Latencia entre AZ: ~2-3ms

3. **Failover automático:**
   - Failover automático a otra AZ ante un fallo de AZ
   - Combinado con Outlier Detection

**Configuración de topología de Pod:**
```yaml
# EKS nodes automatically set topology labels
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```
</details>

## Pregunta 10: Integración con Amazon EKS y buenas prácticas

<details>
<summary>¿Cuáles son las consideraciones y buenas prácticas al integrar Istio 1.28.0 con Amazon EKS 1.34?</summary>

**Respuesta:**
**1. Instalación y configuración:**
```bash
# Install Istioctl
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Install with production profile
istioctl install --set profile=production -y
```

**2. Integración con AWS Load Balancer:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    # Network Load Balancer
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

    # TLS termination (ACM certificate)
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/id"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
```

**3. Optimización de recursos:**
```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5

  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 1024Mi
```

**4. Configuración de seguridad:**
```yaml
# VPC Security Group settings
# - Istiod: 15010, 15012, 8080
# - Envoy: 15001, 15006, 15021, 15090
# - Gateway: 80, 443

# IAM Role (IRSA)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::account:role/istio-gateway
```

**5. Integración de monitorización:**
```yaml
# CloudWatch Container Insights
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match *
        region us-east-1
        log_group_name /aws/eks/cluster/istio
```

**6. Buenas prácticas:**
- Usa el perfil de producción
- HA de Control Plane (replicas >= 3)
- Modo mTLS STRICT
- Configuración de PodDisruptionBudget
- Habilita Locality Load Balancing
- Monitorización con Prometheus + Grafana
- Actualizaciones de versión regulares (enfoque Canary)

**7. Optimización de costes:**
- Considera Ambient Mode (reducción de recursos del 85%)
- Locality Load Balancing (ahorro de costes entre AZ)
- Limitación de Sidecar Scope (reducción de memoria del 30-50%)
</details>

## Pregunta adicional: Progressive Delivery

<details>
<summary>¿Cómo implementas Progressive Delivery totalmente automatizado con Istio + Argo Rollouts?</summary>

**Respuesta:**
Progressive Delivery es un enfoque que avanza o revierte automáticamente los despliegues según las métricas.

**Ejemplo de automatización completa:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary

      steps:
      # Stage 1: 10% Canary
      - setWeight: 10
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 2: 25% Canary (auto-progress)
      - setWeight: 25
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 3: 50% Canary (auto-progress)
      - setWeight: 50
      - pause: {duration: 2m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 4: 100% Canary (auto-complete)
```

**Condiciones de rollback automático:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    interval: 30s
    count: 4
    successCondition: result >= 0.95
    failureLimit: 2  # Immediate rollback after 2 failures
    provider:
      prometheus:
        query: |
          # Success rate < 95% or
          # Latency > 500ms or
          # Error rate > 5%
          # → Auto rollback
```

**Beneficios clave:**
- Automatización completa (sin intervención humana)
- Rollback inmediato (en segundos tras detectar un error)
- Despliegues seguros (verificación basada en métricas)
- Proceso consistente (estandarizado)
</details>

---

**Puntuación:**
- 10-11 correctas: Excelente (nivel experto en Istio)
- 8-9 correctas: Bueno (capaz de operar en producción)
- 6-7 correctas: Regular (se recomienda aprendizaje adicional)
- 4-5 correctas: Insuficiente (se requiere repasar los conceptos básicos)
- 0-3 correctas: Se necesita volver a estudiar

**Recursos de aprendizaje:**
- [Documentación oficial de Istio](https://istio.io/latest/docs/)
- [Documentación de Argo Rollouts](https://argo-rollouts.readthedocs.io/)
- [EKS Workshop - Istio](https://www.eksworkshop.com/docs/security/servicemesh/)
- [Documentación detallada en esta guía](../../service-mesh/istio/)
