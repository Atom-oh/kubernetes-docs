# Cuestionario sobre Istio

> **Última actualización**: 11 de septiembre de 2026 · Comprobaciones de ejemplos: Istio 1.31.0 / Argo Rollouts 1.10.0

El cuestionario cubre las [guías mantenidas de Istio](../../service-mesh/istio/README.md). La compatibilidad corresponde a la [guía de instalación](../../service-mesh/istio/01-installation.md); un mínimo genérico Kubernetes no es una matriz de soporte. Los ejemplos son ayudas didácticas, no despliegues probados en producción. Sustituya namespaces, hosts, identidades y endpoints ilustrativos por entradas verificadas.

## Pregunta 1: Conceptos básicos de malla de servicios

<details>
<summary>¿Qué es una malla de servicios y cuáles son sus funciones principales?</summary>

Una malla añade control y observación de comunicaciones a nivel de infraestructura. Incluye enrutamiento/balanceo, reintentos/timeouts con presupuestos explícitos, identidad de cargas y seguridad de transporte, autorización, métricas, logs de acceso e integración de trazas.

Istio ofrece planos sidecar y ambient con capacidades L4/L7 y asociaciones de políticas diferentes. Muchos controles no requieren cambios de negocio, pero las aplicaciones siguen participando en propagación de contexto, cierre ordenado e idempotencia duradera. Una malla no hace seguros automáticamente los reintentos no idempotentes ni instala todos los backends de observabilidad.

</details>

## Pregunta 2: Arquitectura de Istio

<details>
<summary>¿Qué funciones tienen los planos de control y datos?</summary>

- **Istiod** observa servicios/configuración, la traduce y distribuye a proxies. Kubernetes persiste los CRD. La emisión/renovación de certificados usa la integración CA configurada en Istiod.
- **Modo sidecar** usa Envoy junto a cada Pod inscrito para su tráfico interceptado.
- **Modo ambient** usa ztunnel por nodo para transporte/identidad L4 y waypoints Envoy opcionales para funciones L7 admitidas.
- **Gateways** gestionan rutas de entrada/salida elegidas. Su Deployment/controlador es independiente del recurso de configuración de rutas.

«Todo el tráfico se intercepta» exige verificar exclusiones, protocolos e inscripción. No hay reducción universal del 85%: compare proxies reales, requests/limits, uso, capacidad waypoint, empaquetado de nodos y coste operativo. Consulte [arquitectura](../../service-mesh/istio/03-architecture.md) y el [modelo de recursos ambient](../../service-mesh/istio/advanced/01-ambient-mode.md).

</details>

## Pregunta 3: Gestión de tráfico e integración Argo Rollouts

<details>
<summary>¿Cómo combinan Istio y el análisis Argo un despliegue canary?</summary>

Argo cambia pesos en una ruta HTTP Istio nombrada manteniendo la selección de backend estable/canary. Rollout también necesita selector, plantilla Pod, Services reales, namespace inscrito y VirtualService correspondiente. Lo siguiente es **solo un fragmento bajo Rollout.spec**, del ejemplo basado en hosts de la [guía completa](../../service-mesh/istio/advanced/08-argo-rollouts.md):

```yaml
strategy:
  canary:
    stableService: test-stable
    canaryService: test-canary
    maxSurge: 1
    maxUnavailable: 0
    trafficRouting:
      istio:
        virtualService:
          name: test
          routes:
          - primary
    steps:
    - setWeight: 10
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 50
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 80
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
```

La plantilla nombrada de tasa de éxito es finita. Comprueba volumen y disponibilidad HTTP del **Service canary**, usando un único reporter para no contar ambos proxies:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

Prometheus debe existir y recoger los proxies pertinentes. El ejemplo sidecar espera métricas HTTP del reporter source y tráfico canary real; una ruta ambient L4 sola no proporciona esas mediciones L7.

El resultado Prometheus de Argo es un array, por lo que se consulta result[0] solo tras comprobar longitud. Vacío, NaN e infinito no deben pasar. El fallback cero del numerador maneja tráfico totalmente fallido, y el control de volumen impide declarar saludable tráfico cero/ausente. «Disponibilidad» excluye aquí 5xx y código 0; no garantiza éxito de negocio ni solo respuestas 2xx.

El antiguo escalar result >= 0.95, dirección del proveedor omitida, plantilla de latencia ausente y Rollout incompleto no eran una receta completa. failureLimit cuenta **fallos permitidos**: 2 permite dos y falla al tercero; aquí se usa 0. La reacción depende de intervalos, reconciliación y propagación, no promete rollback inmediato.

</details>

## Pregunta 4: Funciones de seguridad

<details>
<summary>¿En qué difieren mTLS, autorización y validación JWT?</summary>

PeerAuthentication controla el mTLS entrante aceptado. No establece la política TLS saliente del cliente. La política siguiente supone llamantes preparados para STRICT; ubicarla en el namespace raíz tendría mayor alcance:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

Para Pods backend **inscritos con sidecar**, estas políticas exigen conjuntamente identidad frontend, JWT validado y ruta GET permitida:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-default-deny
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-read
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - '*'
    to:
    - operation:
        methods:
        - GET
        paths:
        - /api/*
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: backend-jwt
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://auth.example.com
    jwksUri: https://auth.example.com/.well-known/jwks.json
    audiences:
    - backend-api
```

La primera es una política **ALLOW** vacía del backend seleccionado, que deniega por defecto hasta que coincida una regla ALLOW. No es un DENY explícito que anule el permiso posterior. Otras ALLOW coincidentes pueden ampliar acceso; revise el conjunto completo.

RequestAuthentication valida un JWT proporcionado, pero por sí sola acepta solicitudes sin él. requestPrincipals hace obligatorio el JWT validado aquí. Issuer, URL JWKS y audience son marcadores para un proveedor real. Principal de carga y principal JWT son identidades distintas.

Las políticas L7 en ambient requieren asociación waypoint admitida; no copie una política HTTP con selector sidecar a ztunnel. Consulte las [guías de seguridad](../../service-mesh/istio/security/README.md) para targetRefs, migración y confianza.

</details>

## Pregunta 5: Gateway e Ingress

<details>
<summary>¿Cómo se configuran terminación TLS y rutas de aplicación?</summary>

Este ejemplo usa **Istio Gateway**, no Kubernetes Gateway API. Deben estar configurados Deployment de gateway, etiquetas Pod coincidentes y puertos Service. La aplicación está en bookinfo; gateway y credencial, en istio-ingress:

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - bookinfo.example.com
    tls:
      httpsRedirect: true
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: bookinfo
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - istio-ingress/bookinfo-gateway
  http:
  - route:
    - destination:
        host: productpage.bookinfo.svc.cluster.local
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 0
```

SIMPLE termina TLS downstream y VirtualService enruta HTTP. El listener HTTP redirige solo el dominio de ejemplo admitido. La ruta desactiva explícitamente reintentos, incluidas escrituras. Sustituya dominio propio y namespace/Service/selector reales antes de usar.

```bash
kubectl -n istio-ingress create secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo-fullchain.pem
```

Esto empaqueta un certificado/clave existente; no emite certificado ni establece confianza del cliente. Revise SAN, cadena, caducidad y acceso a credenciales del gateway. Kubernetes Gateway API usa asociación GatewayClass/Gateway/HTTPRoute y estado del controlador en vez de este esquema.

</details>

## Pregunta 6: Herramientas de observabilidad

<details>
<summary>¿Qué miden los componentes de telemetría y qué debe configurarse?</summary>

Prometheus recoge métricas; Grafana renderiza dashboards; Kiali usa telemetría y estado configurados; Jaeger u otro backend almacena trazas enviadas mediante el proveedor/collector. Son integraciones, no herramientas instaladas automáticamente por el perfil predeterminado Istio.

Las consultas seleccionan un flujo source-reporter para reviews en app. La latencia está en **segundos**, el tráfico en **solicitudes/segundo**, y los errores incluyen 5xx más código 0:

```promql
# latency
histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))) / 1000

# traffic
sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# error
(sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app",response_code=~"5..|0"}[5m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# cpu
sum(rate(container_cpu_usage_seconds_total{namespace="app",container="istio-proxy",pod!=""}[5m]))
```

La consulta CPU selecciona la etiqueta **container**, no un nombre Pod ficticio que contenga istio-proxy. Devuelve núcleos consumidos, no por sí misma saturación porcentual; compare límites/capacidad y throttling. Necesita kubelet/cAdvisor correspondientes. Denominadores vacíos/cero generan no-data/NaN, no salud; el fallback del numerador es 0 solo con un total positivo.

Para trazas, configure un receptor OTLP gRPC real y un proveedor nombrado, y selecciónelo con Telemetry:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: tracing
  namespace: app
spec:
  tracing:
  - providers:
    - name: otel
    randomSamplingPercentage: 1.0
```

IstioOperator es entrada de instalación istioctl. No despliega el collector ni Jaeger. El 1% de muestreo es ilustrativo, no objetivo universal; las aplicaciones deben propagar contexto. Revise protocolos backend, retención y costes antes de cambiarlos.

Los comandos de dashboard solo conectan con backends instalados y descubribles:

```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```

</details>

## Pregunta 7: Modo ambient

<details>
<summary>¿En qué difiere ambient del modo sidecar?</summary>

| Aspecto | Sidecar | Ambient |
|---|---|---|
| Ubicación | Envoy junto a cada Pod inscrito | ztunnel por nodo y waypoints elegidos |
| Transporte L4 | Proxy de carga | ztunnel/HBONE |
| Funciones L7 | Funciones Envoy y alcance API admitidos | Requieren waypoint y asociación/API compatibles |
| Recursos | Dependen de Pods, carga y configuración | Dependen de nodos, despliegue/capacidad waypoint y carga |
| Adopción | Inyección/recreación de Pods previstos | Requisitos CNI/inscripción; retirar sidecars existentes aún requiere rollout controlado |
| Rendimiento | Medir carga real | Medir L4 y L7 separadamente; sin superioridad ni ahorro fijo |

Use la [guía de instalación/migración ambient](../../service-mesh/istio/advanced/01-ambient-mode.md). Aplicar profile=ambient a una instalación compartida arbitraria y etiquetar default no es una migración completa segura. Revise compatibilidad CNI, NetworkPolicy/HBONE, etiquetas sidecar en conflicto, funciones waypoint e inscripción efectiva.

```bash
kubectl get namespace app --show-labels
istioctl ztunnel-config workloads -n istio-system
```

Estas comprobaciones de lectura no inscriben cargas ni demuestran políticas L7. Número de Services/Pods y «50MB por nodo» fijos no bastan para predecir consumo o ahorro.

</details>

## Pregunta 8: Patrones de resiliencia

<details>
<summary>¿En qué difieren detección de anomalías, límites de pools y rate limiting?</summary>

La detección de anomalías expulsa endpoints no saludables por fallos observados; los circuit breakers de pools acotan recursos como conexiones, solicitudes pendientes o activas. No imponen una cuota de solicitudes por segundo.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

consecutive5xxErrors es el campo actual. La detección consecutiva puede actuar en línea; interval no promete esperar 30 segundos antes de cada expulsión. baseEjectionTime puede aumentar con repeticiones, e importan endpoint/capacidad por proxy. maxEjectionPercent no es garantía global de disponibilidad.

Para un listener HTTP **entrante del sidecar** en 9080, este bucket local ilustrativo empieza con capacidad de ráfaga 100 y repone 10 tokens/s:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: reviews-local-rate-limit
  namespace: app
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 9080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            runtime_key: local_rate_limit_enabled
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            runtime_key: local_rate_limit_enforced
            default_value:
              numerator: 100
              denominator: HUNDRED
```

Type URL, coincidencia de carga/listener/router y fracciones de habilitación/aplicación son necesarios. Un bucket configurado pero no habilitado/aplicado no limita efectivamente. El límite es local al proceso por defecto; las réplicas multiplican capacidad agregada, no es cuota global de malla. EnvoyFilter en waypoint no está soportado. Límites globales requieren servicio y descriptores coincidentes; consulte [rate limiting](../../service-mesh/istio/resilience/02-rate-limiting.md).

</details>

## Pregunta 9: Balanceo por localidad en EKS

<details>
<summary>¿Qué aporta la preferencia de localidad y qué no garantiza?</summary>

La localidad usa topología de endpoints/origen para preferir destinos adecuados. Esta **alternativa** al DestinationRule reviews anterior usa prioridad región/zona con detección de anomalías:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
```

No combine distribute con failover o failoverPriority en un ajuste. Una regla 80/20 envía deliberadamente 20% remoto mientras todo está sano; no es «remoto solo si falla». Failover necesita endpoints descubiertos y accesibles y capacidad suficiente. No alcanza una AZ/clúster remota excluida por el Service o ausente del registro.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
```

Verifique etiquetas reales y localidad de endpoints del proxy. Los nombres AZ pueden diferir entre cuentas AWS; use mapeo AZ-ID al comparar zonas físicas. El coste depende de volumen y ruta exacta EC2/balanceador/red; habilitar localidad no implica precio universal $0.01/GB, latencia fija ni ahorro del 85%.

</details>

## Pregunta 10: Integración Amazon EKS y buenas prácticas

<details>
<summary>¿Qué debe comprobarse antes de instalar u operar Istio en EKS?</summary>

1. Use la intersección exacta admitida Istio/Kubernetes/EKS y CLI/chart fijados. No existe perfil production integrado. Use configuración Helm/istioctl revisada mediante su propietario.
2. Identifique el controlador LB: AWS Load Balancer Controller, Auto Mode y aprovisionamiento heredado tienen propietarios/ajustes distintos. Haga coincidir selectores/puertos Service con el gateway real. Decida terminar TLS en NLB o gateway; no envíe texto plano a un listener TLS ni añada TLS doble accidental.
3. Conceda permisos AWS al componente que llama API AWS, como controlador LB o collector. Envoy no necesita IAM solo para reenviar. Configure confianza y permisos IRSA o Pod Identity compatible; una anotación no basta.
4. Abra solo rutas direccionales necesarias. Los puertos de interceptación no son una lista para exponer indiscriminadamente en grupos de seguridad. Incluya webhook/xDS, salud y rutas reales ingress/ambient donde proceda.
5. Dimensione Istiod/proxies con evidencia y capacidad de planificación/disponibilidad. PDB cubre interrupciones voluntarias concretas; réplicas por sí solas no garantizan diversidad zonal ni protegen de todos los fallos.
6. Configure métricas, logs y trazas separadamente. Un fragmento de salida Fluent Bit cloudwatch_logs no es Container Insights ni un pipeline completo CRI/parser/IAM/log-stream.

Una entrada ilustrativa de instalación para HPA del plano de control y requests/limits de proxy es:

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
          minReplicas: 3
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
            memory: 1Gi
```

Las 3–5 réplicas y recursos son ejemplos, no dimensionamiento productivo validado. Revise métricas HPA, ubicación y capacidad. Evalúe ambient y alcance de configuración con mediciones reales de recursos/facturación; no hay garantía general de ahorro del 85% o 30–50%.

Use la [guía de integración AWS](../../service-mesh/istio/04-aws-integration.md) y [buenas prácticas](../../service-mesh/istio/best-practices.md) para procedimientos completos.

</details>

## Pregunta adicional: Entrega progresiva

<details>
<summary>¿Qué hace útil el análisis de entrega progresiva y cuáles son sus límites?</summary>

Un rollout completo necesita destinos reales, capacidad estable, argumentos explícitos y una política de medición finita y significativa. La plantilla amplía el ejemplo canary con volumen, disponibilidad HTTP y latencia P95:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: comprehensive-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.99
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

Referencie la plantilla desde un paso de análisis correspondiente de un Rollout completo. No sustituye selector/plantilla/Services ausentes en un ejemplo incompleto. Los umbrales son ilustrativos; selectores, unidades, volumen y SLO de negocio deben coincidir.

Medición fallida, error de proveedor, resultado inconcluso, aborto y despliegue posterior de una revisión anterior son estados distintos. Inspeccione AnalysisRun/Rollout; no los llame a todos rollback instantáneo. Abortar no deshace escrituras de base de datos ni otros efectos. Intervalos de controladores, disponibilidad del backend estable y propagación acotan la recuperación.

Automatizar reduce decisiones repetitivas, pero ningún control métrico establece despliegue universalmente seguro ni garantiza que no haga falta diagnóstico humano. Pruebe sin tráfico, series ausentes, fallos totales, NaN/infinito y recuperación. La [guía completa](../../service-mesh/istio/advanced/08-argo-rollouts.md) contiene recursos circundantes y límites de validación.

</details>

## Autoevaluación

Use las 11 respuestas para identificar qué repasar. Una puntuación alta no demuestra preparación operativa de producción; incluya revisión y validación práctica en un entorno controlado.

## Recursos de aprendizaje

- [Documentación mantenida de Istio](../../service-mesh/istio/README.md)
- [Documentación oficial de Istio](https://istio.io/latest/docs/)
- [Integración Istio de Argo Rollouts](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Semántica de análisis Argo](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Resultados de consulta instantánea Prometheus](https://argo-rollouts.readthedocs.io/en/stable/analysis/prometheus/)
- [Configuración TLS de Istio](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Referencia API de Istio](https://istio.io/latest/docs/reference/config/)
