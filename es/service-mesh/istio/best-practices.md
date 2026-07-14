# Mejores prácticas de Istio

Este documento cubre las mejores prácticas y recomendaciones para operar Istio con éxito en entornos de producción.

## Tabla de contenido

1. [Optimización del rendimiento](#performance-optimization)
2. [Fortalecimiento de la seguridad](#security-hardening)
3. [Guía de operaciones](#operations-guide)
4. [Monitoreo y observabilidad](#monitoring-and-observability)
5. [Lista de verificación para producción](#production-checklist)

## Optimización del rendimiento

### 1. Optimización de recursos del Control Plane

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
          limits:
            cpu: 1000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
          metrics:
          - type: Resource
            resource:
              name: cpu
              target:
                type: Utilization
                averageUtilization: 80
```

**Recomendaciones**:
- Istiod debe tener al menos 2 réplicas
- CPU: Ajustar según el tamaño del clúster
- Memoria: Estimar aproximadamente 10KB por servicio

### 2. Optimización de recursos del Data Plane

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    # Sidecar resource optimization
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

**Recomendaciones**:
- Cargas de trabajo normales: CPU 100m, memoria 128Mi
- Cargas de trabajo con alto tráfico: CPU 500m, memoria 512Mi
- Concurrencia del Sidecar: `concurrency: 2` (predeterminada)

### 3. Optimización del Connection Pool

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: optimized-pool
spec:
  host: myapp
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30ms
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
        idleTimeout: 300s
```

**Recomendaciones**:
- `maxConnections`: Considerar las conexiones simultáneas de la carga de trabajo
- `maxRequestsPerConnection`: 1-2 para HTTP/1.1, mayor para HTTP/2
- `idleTimeout`: Aumentar si se necesitan conexiones de larga duración

### 4. Balanceo de carga por localidad

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: locality-lb
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # Same AZ priority
            "us-east-1/us-east-1b/*": 20
```

**Beneficios**:
- Reducción de costos entre AZ (~85%)
- Menor latencia de red
- Manejo automático de fallas de la zona de disponibilidad

### 5. Limitación del alcance del Sidecar

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "default/*"
    - "istio-system/*"
```

**Beneficios**:
- Menor tamaño de configuración de Envoy
- Menor uso de memoria
- Envío de configuración más rápido

## Fortalecimiento de la seguridad

### 1. Aplicar mTLS estricto

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # STRICT recommended for production
```

**Lista de verificación**:
- Aplicar mTLS STRICT a todos los servicios
- Usar PERMISSIVE solo durante los períodos de migración
- DISABLE para servicios externos (manejar en ServiceEntry)

### 2. Política de autorización

```yaml
# Deny by default
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec: {}  # Deny all requests
---
# Allow specific
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
```

**Mejores prácticas**:
- Usar una política de denegación predeterminada
- Aplicar el principio de privilegio mínimo
- Autenticación basada en Service Account
- Aislamiento de Namespace

### 3. Control del tráfico de salida

```yaml
# Block external traffic
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    outboundTrafficPolicy:
      mode: REGISTRY_ONLY  # Allow only explicit ServiceEntries
---
# Allowed external services
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 4. Autenticación JWT

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  selector:
    matchLabels:
      app: api-service
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  selector:
    matchLabels:
      app: api-service
  action: ALLOW
  rules:
  - when:
    - key: request.auth.claims[iss]
      values: ["https://auth.example.com"]
```

## Guía de operaciones

### 1. Estrategia de Deployment

#### Adopción gradual de Istio

```mermaid
flowchart LR
    Start[Start]
    Phase1[Phase 1<br/>Observability]
    Phase2[Phase 2<br/>mTLS PERMISSIVE]
    Phase3[Phase 3<br/>mTLS STRICT]
    Phase4[Phase 4<br/>Advanced Features]
    End[Full Adoption]

    Start --> Phase1
    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    Phase4 --> End

    %% Style definition
    classDef phase fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Class application
    class Start,Phase1,Phase2,Phase3,Phase4,End phase;
```

**Fase 1: Observabilidad (1-2 semanas)**
```bash
# Enable sidecar injection only
kubectl label namespace default istio-injection=enabled

# Verify metrics, logs, traces
# Evaluate performance impact
```

**Fase 2: mTLS PERMISSIVE (1-2 semanas)**
```yaml
# Enable PERMISSIVE mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: PERMISSIVE
```

**Fase 3: mTLS STRICT (1 semana)**
```yaml
# Switch to STRICT mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**Fase 4: Funcionalidades avanzadas (En curso)**
- Traffic Management (Canary, Circuit Breaker)
- Authorization Policy
- Rate Limiting

### 2. Estrategia de actualización

#### Actualización Canary

```bash
# 1. Install new version Control Plane
istioctl install --set revision=1-28-0 -y

# 2. Move test namespace
kubectl label namespace test istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n test

# 3. Move production after verification
kubectl label namespace prod istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n prod

# 4. Remove previous version
istioctl uninstall --revision=1-27-0 -y
```

### 3. Alta disponibilidad

```yaml
# Control Plane HA
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        replicaCount: 3
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: istiod
            topologyKey: kubernetes.io/hostname
```

**Recomendaciones**:
- Istiod: Mínimo 3 réplicas
- Distribuir uniformemente entre las AZ
- Configurar PodDisruptionBudget

### 4. Copia de seguridad y recuperación

```bash
# Backup Istio configuration
kubectl get istiooperator -A -o yaml > istio-operator-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# Recovery
kubectl apply -f istio-operator-backup.yaml
kubectl apply -f istio-config-backup.yaml
```

## Monitoreo y observabilidad

### 1. Señales doradas

```promql
# 1. Latency (P50, P95, P99)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (Request count)
sum(rate(istio_requests_total[5m]))

# 3. Errors (Error rate)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/
sum(rate(istio_requests_total[5m]))

# 4. Saturation (Resource utilization)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

### 2. Monitoreo del Control Plane

```promql
# Pilot configuration push time
pilot_proxy_convergence_time

# xDS connection count
pilot_xds_pushes

# Memory usage
process_resident_memory_bytes{app="istiod"}
```

### 3. Monitoreo del Data Plane

```promql
# Envoy connection count
envoy_cluster_upstream_cx_active

# Circuit Breaker open
envoy_cluster_circuit_breakers_default_rq_open

# Outlier Detection
envoy_cluster_outlier_detection_ejections_active
```

### 4. Reglas de alerta

```yaml
groups:
- name: istio
  rules:
  # High error rate
  - alert: HighErrorRate
    expr: |
      (sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
      /
      sum(rate(istio_requests_total[5m]))) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  # High latency
  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
      ) > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected (P95 > 1s)"

  # Pilot not ready
  - alert: PilotNotReady
    expr: up{job="pilot"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pilot is not ready"
```

## Lista de verificación para producción

### Antes de la instalación

- [ ] Verificar la compatibilidad de la versión de Kubernetes (1.28+)
- [ ] Seleccionar la versión de Istio (se recomienda una versión estable)
- [ ] Calcular los requisitos de recursos
- [ ] Revisar las políticas de red
- [ ] Establecer un plan de copia de seguridad y recuperación

### Instalación

- [ ] Usar el perfil de producción
- [ ] Configurar HA del Control Plane (réplicas >= 3)
- [ ] Establecer límites de recursos
- [ ] Configurar PodDisruptionBudget
- [ ] Preparar el stack de monitoreo

### Seguridad

- [ ] Habilitar el modo mTLS STRICT
- [ ] Aplicar Authorization Policy
- [ ] Controlar el tráfico de salida
- [ ] Configurar la autenticación JWT (si es necesario)
- [ ] Integrar Network Policy

### Gestión del tráfico

- [ ] Configurar VirtualService
- [ ] Configurar DestinationRule
- [ ] Configurar Circuit Breaker
- [ ] Configurar Retry/Timeout
- [ ] Configurar Rate Limiting

### Observabilidad

- [ ] Integrar Prometheus
- [ ] Configurar paneles de Grafana
- [ ] Configurar trazas de Jaeger/Zipkin
- [ ] Instalar Kiali
- [ ] Configurar reglas de alerta

### Operaciones

- [ ] Establecer un plan de actualización
- [ ] Automatizar las copias de seguridad
- [ ] Documentación
- [ ] Escribir una guía de guardia
- [ ] Preparar runbook

### Rendimiento

- [ ] Optimizar los recursos de Sidecar
- [ ] Ajustar Connection Pool
- [ ] Configurar el balanceo de carga por localidad
- [ ] Limitar el alcance de Sidecar
- [ ] Realizar pruebas de rendimiento

### Pruebas

- [ ] Pruebas funcionales
- [ ] Pruebas de rendimiento
- [ ] Pruebas de recuperación ante desastres
- [ ] Ingeniería del caos
- [ ] Pruebas de escenarios de actualización

## Antipatrones comunes

### Aspectos que se deben evitar

1. **Adoptar todo de una vez**
   ```
   Don't enable all Istio features on Day 1
   Do add features gradually (Observability -> Security -> Traffic Management)
   ```

2. **Sin límites de recursos**
   ```yaml
   Don't leave Sidecar without resource limits
   Do set appropriate requests/limits
   ```

3. **Uso a largo plazo del modo PERMISSIVE**
   ```
   Don't keep using PERMISSIVE
   Do transition to STRICT quickly
   ```

4. **Abuso de coincidencias con comodines**
   ```yaml
   Don't: hosts: ["*"]  # All services
   Do: hosts: ["myapp.default.svc.cluster.local"]  # Explicit
   ```

5. **Desplegar sin monitoreo**
   ```
   Don't deploy to production without checking metrics
   Do require Golden Signals monitoring
   ```

## Optimización de costos

### 1. Considerar Ambient Mode

```yaml
# Resource usage comparison
# Sidecar Mode: 100 pods x 50MB = 5GB
# Ambient Mode: 10 nodes x 50MB = 500MB

# 85%+ reduction possible
```

### 2. Balanceo de carga por localidad

```yaml
# Cross-AZ cost savings
# AWS: $0.01-0.02 per GB
# Significant savings with 80% same AZ routing
```

### 3. Limitación del alcance de Sidecar

```yaml
# Remove unnecessary configuration
# 30-50% memory usage reduction possible
```

## Referencias

### Documentación oficial
- [Mejores prácticas de Istio](https://istio.io/latest/docs/ops/best-practices/)
- [Rendimiento y escalabilidad](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [Mejores prácticas de seguridad](https://istio.io/latest/docs/ops/best-practices/security/)

### Comunidad
- [Istio Discuss](https://discuss.istio.io/)
- [Istio Slack](https://istio.slack.com/)
- [GitHub Issues](https://github.com/istio/istio/issues)

### Recursos adicionales
- [Istio en producción](https://www.tetrate.io/blog/istio-in-production/)
- [Patrones de Service Mesh](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
