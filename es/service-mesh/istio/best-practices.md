# Mejores prácticas de Istio

Este documento cubre las mejores prácticas y recomendaciones para operar Istio correctamente en entornos de producción.

## Tabla de contenidos

1. [Optimización del rendimiento](#performance-optimization)
2. [Fortalecimiento de la seguridad](#security-hardening)
3. [Guía de operaciones](#operations-guide)
4. [Monitoreo y observabilidad](#monitoring-and-observability)
5. [Lista de verificación para producción](#production-checklist)

Revisado para Istio 1.31 el 11 de septiembre de 2026. Los fragmentos de `IstioOperator` son entradas para `istioctl install -f`, no recursos de Kubernetes que se aplican con kubectl. Intégrelos en la configuración de instalación existente; use valores de chart equivalentes para Helm. La mayoría de los ejemplos describen sidecars; use políticas waypoint/Gateway API para ambient. Los ajustes de recursos y las duraciones de rollout son puntos de partida que se deben validar bajo carga.

## Optimización del rendimiento {#performance-optimization}

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
- CPU: Ajuste según el tamaño del clúster
- Memoria: Mida el número de servicios/proxies, el tamaño de la configuración y la tasa de actualización; no existe una fórmula fija por servicio

### 2. Optimización de recursos del Data Plane

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  labels:
    sidecar.istio.io/inject: "true"
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
- Workloads normales: CPU 100m, memoria 128Mi
- Workloads de alto tráfico: CPU 500m, memoria 512Mi
- Concurrencia del sidecar: normalmente déjela sin configurar para que Istio derive los hilos de trabajo de las solicitudes/límites de CPU

### 3. Optimización del grupo de conexiones

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
        maxRequestsPerConnection: 0
        idleTimeout: 300s
```

**Recomendaciones**:
- `maxConnections`: Considere las conexiones concurrentes del workload
- `maxRequestsPerConnection`: 0 significa ilimitado; los valores pequeños aumentan la rotación de conexiones y los handshakes de TLS
- `idleTimeout`: Auméntelo si se necesitan conexiones de larga duración

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
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 5s
      baseEjectionTime: 30s
```

**Beneficios**:
- Posible reducción del tráfico entre AZ; el ahorro depende de la distribución del tráfico y de la facturación
- Menor latencia de red
- Valide el failover con detección de valores atípicos y capacidad saludable en otras zonas

### 5. Limitación del alcance del sidecar

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
- Tamaño reducido de la configuración de Envoy
- Menor uso de memoria
- Envío de configuración más rápido

## Fortalecimiento de la seguridad {#security-hardening}

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
- Aplique mTLS STRICT a todos los servicios
- Use PERMISSIVE solo durante los períodos de migración
- PeerAuthentication controla el mTLS entrante del workload. Configure HTTPS/TLS externo en ServiceEntry y, cuando sea necesario, DestinationRule; no deshabilite globalmente el mTLS de la malla.

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
- Use una política de denegación predeterminada
- Aplique el principio de mínimo privilegio
- Autenticación basada en Service Account
- Aislamiento de Namespace

### 3. Control del tráfico de salida

```yaml
# Detect unregistered destinations; not an egress firewall
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    outboundTrafficPolicy:
      mode: REGISTRY_ONLY  # Known Kubernetes services and ServiceEntries
```

Aplique este ServiceEntry independiente con kubectl. Imponga el aislamiento de salida con controles de red; REGISTRY_ONLY no es un límite de seguridad.

```yaml
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

## Guía de operaciones {#operations-guide}

### 1. Estrategia de Deployment

#### Adopción gradual de Istio

![Flujo de trabajo de la ruta de adopción gradual de Istio: comienza con la inyección de sidecar solo para observabilidad, pasa por TLS mutuo PERMISSIVE y luego STRICT, continúa con funciones avanzadas de gestión del tráfico y termina con la adopción completa.](../../.gitbook/assets/en-service-mesh-istio-best-practices-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-best-practices-0.html)

**Fase 1: Observabilidad (1-2 semanas)**
```bash
# Enable sidecar injection only
kubectl label namespace default istio-injection=enabled --overwrite
kubectl rollout restart deployment -n default

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

**Fase 4: Funciones avanzadas (en curso)**
- Gestión del tráfico (Canary, Circuit Breaker)
- Política de autorización
- Rate Limiting

### 2. Estrategia de actualización

#### Actualización Canary

Use el binario objetivo de istioctl 1.31.0 de la guía de instalación; establecer un nombre de revisión no selecciona una versión de imagen. Este ejemplo actualiza desde la versión 1.30.4, conserva los ajustes de instalación existentes y requiere validar cada etapa. Los Gateways se pueden actualizar in situ con el perfil predeterminado; planifique explícitamente su rollout. Una instalación gestionada por Helm debe usar el flujo de trabajo de actualización de Helm.

```bash
# 1. Install new version Control Plane
istioctl install --set revision=1-31-0 -f existing-install.yaml

# 2. Move test namespace
kubectl label namespace test istio-injection- istio.io/rev=1-31-0 --overwrite
kubectl rollout restart deployment -n test

# 3. Move production after verification
kubectl label namespace prod istio-injection- istio.io/rev=1-31-0 --overwrite
kubectl rollout restart deployment -n prod

# 4. Remove previous version
istioctl proxy-status
# Only after every proxy/gateway has migrated; substitute the actual old revision
istioctl uninstall --revision=1-30-4
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
        hpaSpec:
          minReplicas: 3
          maxReplicas: 5
        affinity:
          podAntiAffinity:
            preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: istiod
                topologyKey: topology.kubernetes.io/zone
```

**Recomendaciones**:
- Istiod: Mínimo 3 réplicas
- Distribuya uniformemente entre las AZ
- Configure PodDisruptionBudget

### 4. Backup y recuperación

```bash
# Preserve the versioned installation input in source control
cp existing-install.yaml istio-install-backup.yaml
# Snapshot mesh configuration; this does not include Secrets or Gateway API resources
kubectl get virtualservices.networking.istio.io,destinationrules.networking.istio.io,gateways.networking.istio.io,serviceentries.networking.istio.io,sidecars.networking.istio.io,workloadentries.networking.istio.io,workloadgroups.networking.istio.io,peerauthentications.security.istio.io,requestauthentications.security.istio.io,authorizationpolicies.security.istio.io,telemetries.telemetry.istio.io -A -o yaml > istio-config-backup.yaml

# Restore the matching Istio version and CRDs first, then declarative resources
istioctl install -f istio-install-backup.yaml
kubectl apply -f istio-config-backup.yaml
```

Para las instalaciones de Helm, preserve las versiones de chart y `helm get values <release> -n <namespace> -o yaml` en su lugar. Haga backup de los Secrets de CA/TLS de forma segura e incluya cualquier recurso Gateway API, EnvoyFilter o WasmPlugin en uso. Vuelva a crear los Namespaces requeridos y revise las instantáneas generadas antes de la restauración.

## Monitoreo y observabilidad {#monitoring-and-observability}

### 1. Señales doradas

```promql
# 1. Latency (P50, P95, P99)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])) by (le)
)

# 2. Traffic (Request count)
sum(rate(istio_requests_total{reporter="destination"}[5m]))

# 3. Errors (Error rate)
sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m]))
/
sum(rate(istio_requests_total{reporter="destination"}[5m]))

# 4. Saturation (Resource utilization)
sum(rate(container_cpu_usage_seconds_total{container="istio-proxy"}[5m]))
```

### 2. Monitoreo del Control Plane

```promql
# Pilot configuration push time
histogram_quantile(0.95, sum(rate(pilot_proxy_convergence_time_bucket[5m])) by (le))

# xDS connection count
pilot_xds

# Memory usage
process_resident_memory_bytes{job="istiod"}
```

### 3. Monitoreo del Data Plane

Confirme que estas estadísticas de Envoy estén habilitadas en el matcher de estadísticas del proxy. Las etiquetas de los jobs de scraping dependen de la configuración; los ejemplos asumen `job="istiod"`. Una alerta `up` detecta la disponibilidad del scraping, no todos los fallos de preparación.

```promql
# Envoy connection count
envoy_cluster_upstream_cx_active

# Circuit Breaker open
envoy_cluster_circuit_breakers_default_rq_open

# Outlier Detection
envoy_cluster_outlier_detection_ejections_active
```

### 4. Reglas de alertas

```yaml
groups:
- name: istio
  rules:
  # High error rate
  - alert: HighErrorRate
    expr: |
      (sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m]))
      /
      sum(rate(istio_requests_total{reporter="destination"}[5m]))) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  # High latency
  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])) by (le)
      ) > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected (P95 > 1s)"

  # Pilot not ready
  - alert: IstiodScrapeUnavailable
    expr: up{job="istiod"} == 0 or absent(up{job="istiod"})
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Istiod scrape target is unavailable"
```

## Lista de verificación para producción {#production-checklist}

### Preinstalación

- [ ] Verifique la superposición de soporte de Istio/Kubernetes/EKS (ejemplo 1.31: EKS 1.34–1.37)
- [ ] Seleccione la versión de Istio (se recomienda la versión estable)
- [ ] Calcule los requisitos de recursos
- [ ] Revise las políticas de red
- [ ] Establezca un plan de backup y recuperación

### Instalación

- [ ] Use el perfil de producción
- [ ] Configure HA del Control Plane (réplicas >= 3)
- [ ] Establezca límites de recursos
- [ ] Configure PodDisruptionBudget
- [ ] Prepare la pila de monitoreo

### Seguridad

- [ ] Habilite el modo mTLS STRICT
- [ ] Aplique Authorization Policy
- [ ] Controle el tráfico de salida
- [ ] Configure la autenticación JWT (si es necesaria)
- [ ] Integre Network Policy

### Gestión del tráfico

- [ ] Configure VirtualService
- [ ] Configure DestinationRule
- [ ] Configure Circuit Breaker
- [ ] Configure Retry/Timeout
- [ ] Configure Rate Limiting

### Observabilidad

- [ ] Integre Prometheus
- [ ] Configure los dashboards de Grafana
- [ ] Configure el tracing de Jaeger/Zipkin
- [ ] Instale Kiali
- [ ] Configure las reglas de alertas

### Operaciones

- [ ] Establezca un plan de actualización
- [ ] Automatice los backups
- [ ] Documentación
- [ ] Escriba una guía de guardia
- [ ] Prepare el runbook

### Rendimiento

- [ ] Optimice los recursos del sidecar
- [ ] Ajuste el grupo de conexiones
- [ ] Configure el balanceo de carga por localidad
- [ ] Limite el alcance del sidecar
- [ ] Realice pruebas de rendimiento

### Pruebas

- [ ] Pruebas funcionales
- [ ] Pruebas de rendimiento
- [ ] Pruebas de recuperación ante desastres
- [ ] Ingeniería del caos
- [ ] Pruebas de escenarios de actualización

## Antipatrones comunes

### Aspectos que se deben evitar

1. **Adoptarlo todo de una vez**
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

5. **Deployment sin monitoreo**
   ```
   Don't deploy to production without checking metrics
   Do require Golden Signals monitoring
   ```

## Optimización de costos {#cost-optimization}

- Compare las solicitudes de recursos del sidecar medidas con ztunnel más cualquier capacidad waypoint requerida. El número de Pods por sí solo no establece un porcentaje de ahorro fijo.
- Mida los bytes entre AZ y use los precios regionales actuales de AWS para la ruta real; los pesos de localidad no se traducen directamente en una reducción de facturación universal.
- Delimite la configuración innecesaria del proxy y mida los cambios de memoria/tiempo de envío bajo una carga representativa.

## Referencias

### Documentación oficial
- [Mejores prácticas de Istio](https://istio.io/latest/docs/ops/best-practices/)
- [Rendimiento y escalabilidad](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [Mejores prácticas de seguridad](https://istio.io/latest/docs/ops/best-practices/security/)

### Comunidad
- [Comunidad de Istio](https://istio.io/latest/get-involved/)
- [Slack de Istio](https://slack.istio.io/)
- [Issues de GitHub](https://github.com/istio/istio/issues)

### Recursos adicionales
- [Mejores prácticas de Deployment de Istio](https://istio.io/latest/docs/ops/best-practices/deployment/)
- [Mejores prácticas de gestión del tráfico de Istio](https://istio.io/latest/docs/ops/best-practices/traffic-management/)

- [Actualizaciones Canary](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Opciones de IstioOperator](https://istio.io/latest/docs/reference/config/istio.operator.v1alpha1/)
- [Opciones globales de la malla](https://istio.io/latest/docs/reference/config/istio.mesh.v1alpha1/)
- [Definiciones de métricas xDS de Istio (1.31.0)](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/xds/monitoring.go)
- [Failover por localidad](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/)
- [Estadísticas de Envoy](https://istio.io/latest/docs/ops/configuration/telemetry/envoy-stats/)
- [Sidecar](https://istio.io/latest/docs/reference/config/networking/sidecar/)
- [Versiones compatibles](https://istio.io/latest/docs/releases/supported-releases/)