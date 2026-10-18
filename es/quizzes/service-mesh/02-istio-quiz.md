# Cuestionario sobre Istio

> **Última actualización**: 11 de septiembre de 2026 · Comprobaciones de ejemplos: Istio 1.31.0 / Argo Rollouts 1.10.0

El cuestionario cubre las [guías mantenidas de Istio](../../service-mesh/istio/README.md). La compatibilidad corresponde a la [guía de instalación](../../service-mesh/istio/01-installation.md); un requisito mínimo genérico para Kubernetes no es una matriz de soporte. Los ejemplos son ayudas didácticas, no despliegues probados en producción. Sustituya los espacios de nombres, nombres de host, identidades y endpoints de backend de ejemplo por valores verificados.

## Pregunta 1: Conceptos básicos de malla de servicios

<details>
<summary>¿Qué es una malla de servicios y cuáles son sus funciones principales?</summary>

Una malla añade control y observación de comunicaciones a nivel de infraestructura. Incluye enrutamiento y balanceo, reintentos y tiempos de espera con presupuestos explícitos, identidad de las cargas de trabajo, seguridad del transporte, autorización, métricas, logs de acceso e integración con trazas.

Istio ofrece planos de datos sidecar y ambient con distintas capacidades L4/L7 y formas de asociar políticas. Muchos controles no requieren cambios en la lógica de negocio, pero las aplicaciones siguen siendo responsables de propagar el contexto de las trazas, cerrarse de forma ordenada y garantizar una idempotencia duradera. Una malla no hace seguros automáticamente los reintentos no idempotentes ni instala todos los backends de observabilidad.

</details>

## Pregunta 2: Arquitectura de Istio

<details>
<summary>¿Qué funciones tienen los planos de control y datos?</summary>

- **Istiod** observa el estado de los servicios y la configuración, traduce esa configuración y la distribuye a los proxies. Kubernetes persiste los objetos CRD. La emisión y renovación de certificados utiliza la integración de CA configurada en Istiod.
- **Modo sidecar** usa Envoy junto a cada Pod inscrito para su tráfico interceptado.
- **Modo ambient** usa ztunnel por nodo para transporte/identidad L4 y waypoints Envoy opcionales para funciones L7 admitidas.
- **Gateways** gestionan rutas de entrada/salida elegidas. Su Deployment/controlador es independiente del recurso de configuración de rutas.

La afirmación «se intercepta todo el tráfico» exige verificar las exclusiones, los protocolos y la inscripción de las cargas. No existe una reducción universal del 85 %: compare el número real de proxies, sus requests/limits, el uso observado, la capacidad de los waypoints, la densidad de cargas por nodo y el coste operativo. Consulte [arquitectura](../../service-mesh/istio/03-architecture.md) y el [modelo de recursos ambient](../../service-mesh/istio/advanced/01-ambient-mode.md).

</details>

## Pregunta 3: Gestión del tráfico e integración con Argo Rollouts

<details>
<summary>¿Cómo se combinan el enrutamiento de Istio y el análisis de Argo durante un despliegue canario?</summary>

Argo modifica los pesos de una ruta HTTP de Istio identificada por nombre y mantiene la selección entre los backends estable y canario. El recurso Rollout también necesita un selector, una plantilla de Pod, Services reales, un espacio de nombres integrado en la malla y el VirtualService correspondiente. Lo siguiente es **solo un fragmento bajo Rollout.spec**, tomado del ejemplo basado en hosts de la [guía completa](../../service-mesh/istio/advanced/08-argo-rollouts.md):

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

La plantilla de análisis success-rate que aparece a continuación tiene un número finito de mediciones. Comprueba tanto el volumen de solicitudes como la disponibilidad HTTP del **Service canario**, y usa las métricas de un solo lado para no contabilizar ambos proxies:

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

El backend de Prometheus debe estar instalado y recopilar métricas de los proxies pertinentes. El ejemplo con sidecar requiere métricas HTTP con reporter source y tráfico real hacia el canario; una ruta ambient de L4, por sí sola, no proporciona esas mediciones de L7.

El resultado de Prometheus que recibe Argo es un arreglo, así que las condiciones solo consultan result[0] después de comprobar que el arreglo no esté vacío. Los valores vacíos, NaN e infinitos no deben aprobar la medición. El valor alternativo cero del numerador cubre el caso en que todas las solicitudes fallan; el control de volumen impide declarar saludable un tráfico nulo o ausente. Aquí, «disponibilidad» excluye las respuestas 5xx y el código 0; no garantiza el éxito de negocio ni se limita a respuestas 2xx.

El resultado escalar antiguo result >= 0.95, la dirección del proveedor omitida, la falta de una plantilla de latencia y un Rollout incompleto no formaban una receta de automatización completa. failureLimit cuenta los **fallos permitidos**: el valor 2 permite dos y falla con el tercero; este ejemplo usa 0. El tiempo de respuesta depende de los intervalos de medición, la reconciliación del controlador y la propagación de la ruta; no se garantiza una reversión inmediata.

</details>

## Pregunta 4: Funciones de seguridad

<details>
<summary>¿En qué difieren mTLS, autorización y validación JWT?</summary>

PeerAuthentication controla qué conexiones mTLS entrantes se aceptan; no define la política TLS saliente del cliente. La política siguiente supone que los llamantes ya están preparados para STRICT. Si se colocara en el espacio de nombres raíz de la malla, tendría un alcance mayor:

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

En los Pods de backend **integrados mediante sidecar**, estas políticas exigen a la vez la identidad de la carga frontend, un JWT válido y una ruta GET permitida:

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

RequestAuthentication valida el JWT si la solicitud lo presenta, pero por sí sola también acepta solicitudes sin JWT. La condición requestPrincipals es la que exige aquí un JWT validado. El emisor, la URL de JWKS y la audiencia son valores de ejemplo que deben sustituirse por los de un proveedor real. La identidad principal de la carga y la identidad principal del JWT son distintas.

Las políticas L7 en ambient requieren asociación waypoint admitida; no copie una política HTTP con selector sidecar a ztunnel. Consulte las [guías de seguridad](../../service-mesh/istio/security/README.md) para targetRefs, migración y confianza.

</details>

## Pregunta 5: Gateway e Ingress

<details>
<summary>¿Cómo se configuran terminación TLS y rutas de aplicación?</summary>

Este ejemplo usa el recurso **Gateway de Istio**, no la API Kubernetes Gateway. El Deployment del gateway, las etiquetas coincidentes de sus Pods y los puertos del Service ya deben estar configurados. La aplicación está en bookinfo; la carga de trabajo del gateway y su credencial están en istio-ingress:

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

SIMPLE termina la conexión TLS del cliente y, a continuación, VirtualService enruta el tráfico HTTP. El listener HTTP redirige únicamente el dominio de ejemplo admitido. La ruta desactiva explícitamente los reintentos, también para las escrituras. Antes de usar el ejemplo, sustituya el dominio propio y los valores reales de espacio de nombres, Service y selector.

```bash
kubectl -n istio-ingress create secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo-fullchain.pem
```

Esto empaqueta un certificado y una clave ya existentes; no emite certificados ni establece la confianza del cliente. Revise los SAN, la cadena, la fecha de caducidad y el acceso del gateway a la credencial. La API Kubernetes Gateway usa la asociación GatewayClass/Gateway/HTTPRoute y el estado del controlador, en lugar de este esquema de recursos.

</details>

## Pregunta 6: Herramientas de observabilidad

<details>
<summary>¿Qué miden los componentes de telemetría y qué debe configurarse?</summary>

Prometheus recopila métricas; Grafana muestra paneles; Kiali utiliza la telemetría configurada y el estado de la malla; y Jaeger u otro backend de trazas almacena lo que recibe a través del proveedor o collector configurado. Son integraciones: el perfil predeterminado de Istio no instala automáticamente estas herramientas.

Las consultas seleccionan un único flujo con reporter source para el servicio reviews de la aplicación. La latencia se expresa en **segundos**, el tráfico en **solicitudes por segundo** y los errores incluyen tanto las respuestas 5xx como el código 0:

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

La consulta de CPU usa la etiqueta **container**, no un nombre ficticio de Pod que contenga istio-proxy. El resultado indica los núcleos de CPU consumidos y no representa por sí solo un porcentaje de saturación; compárelo con los límites y la capacidad, y revise la limitación de CPU (throttling). La consulta necesita las métricas correspondientes de kubelet/cAdvisor. Si el denominador está vacío o el tráfico es cero, el resultado será no-data/NaN, lo que no demuestra que el servicio esté sano. El valor alternativo cero del numerador solo se aplica cuando el total es positivo.

Para enviar trazas, configure un receptor OTLP gRPC real y un proveedor con nombre; después, selecciónelo mediante Telemetry:

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

El bloque IstioOperator sirve como entrada de instalación para istioctl. No despliega el collector ni Jaeger. La tasa de muestreo del 1 % es ilustrativa, no un objetivo universal; las aplicaciones deben propagar el contexto de las trazas. Antes de cambiar la configuración, revise los protocolos del backend, la retención y los costes del muestreo.

Los comandos de los paneles solo se conectan con backends instalados y detectables:

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
| Adopción | Inyección y recreación de los Pods previstos | Requisitos de CNI e inscripción; migrar desde sidecars existentes también requiere un despliegue controlado |
| Rendimiento | Medir carga real | Medir L4 y L7 separadamente; sin superioridad ni ahorro fijo |

Consulte la [guía de instalación y migración de ambient](../../service-mesh/istio/advanced/01-ambient-mode.md). Aplicar profile=ambient a cualquier instalación compartida y etiquetar cargas como default no constituye un procedimiento de migración completo ni seguro. Revise la compatibilidad de CNI, NetworkPolicy/HBONE, las etiquetas sidecar en conflicto, las funciones de los waypoints y la inscripción efectiva.

```bash
kubectl get namespace app --show-labels
istioctl ztunnel-config workloads -n istio-system
```

Estas comprobaciones de solo lectura no integran cargas en ambient ni demuestran que se apliquen políticas L7. El número de Services o Pods y una cifra fija de «50 MB por nodo» no bastan para predecir el consumo ni el ahorro.

</details>

## Pregunta 8: Patrones de resiliencia

<details>
<summary>¿En qué se diferencian la detección de endpoints anómalos, los límites del pool de conexiones y la limitación de tasa?</summary>

La detección de endpoints anómalos los excluye temporalmente cuando se observan fallos; los circuit breakers del pool limitan recursos concretos, como las conexiones y las solicitudes pendientes o activas. Ninguno de estos mecanismos impone una cuota de solicitudes por segundo.

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

consecutive5xxErrors es el campo vigente. La detección de fallos consecutivos puede actuar en línea; el campo interval no implica que se espere 30 segundos antes de cada exclusión. baseEjectionTime puede aumentar tras exclusiones repetidas, y la capacidad y los endpoints disponibles en cada proxy también importan. maxEjectionPercent no garantiza una disponibilidad global.

Para un listener HTTP **entrante del sidecar** en el puerto 9080, este ejemplo de token bucket local comienza con una ráfaga de 100 tokens y repone 10 tokens por segundo:

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

Se necesitan el type URL, la coincidencia con la carga, el listener y el router, y las fracciones de habilitación y aplicación. Un bucket configurado pero no habilitado y aplicado no impone un límite efectivo. De forma predeterminada, el límite es local al proceso del proxy, por lo que las réplicas multiplican la capacidad agregada; no es una cuota global de la malla. EnvoyFilter en un waypoint no está admitido. Los límites globales requieren un servicio de rate limiting y descriptores coincidentes; consulte la [limitación de tasa](../../service-mesh/istio/resilience/02-rate-limiting.md).

</details>

## Pregunta 9: Balanceo por localidad en EKS

<details>
<summary>¿Qué aporta la preferencia de localidad y qué no garantiza?</summary>

La selección por localidad utiliza la información topológica del origen y de los endpoints para priorizar destinos adecuados. Esta regla DestinationRule es una **alternativa** a la DestinationRule denominada reviews del ejemplo anterior y usa prioridades por región y zona, junto con detección de endpoints anómalos:

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

No combine distribute con failover ni con failoverPriority en una misma configuración de localidad. Una regla distribute 80/20 envía intencionadamente el 20 % del tráfico a destinos remotos incluso cuando todo funciona; no significa «usar destinos remotos solo si hay un fallo». failover requiere endpoints detectados y accesibles, además de capacidad suficiente. No puede alcanzar una zona de disponibilidad o un clúster remoto excluido por el selector del Service o ausente del registro.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
```

Compruebe las etiquetas reales y la localidad de los endpoints que ve el proxy. Los nombres de las zonas de disponibilidad pueden variar entre cuentas de AWS; use el mapeo AZ-ID apropiado para comparar zonas físicas entre cuentas. El coste depende del volumen de tráfico y de la ruta concreta de EC2, el balanceador y la red. Habilitar la selección por localidad no implica un precio universal de $0.01/GB, una latencia fija ni un ahorro del 85 %.

</details>

## Pregunta 10: Integración Amazon EKS y buenas prácticas

<details>
<summary>¿Qué debe comprobarse antes de instalar u operar Istio en EKS?</summary>

1. Compruebe la combinación exacta de versiones de Istio, Kubernetes y EKS que se admite, y fije las versiones de la CLI y del chart. No hay un perfil de producción integrado. Utilice la configuración de Helm/istioctl que haya revisado el responsable de la instalación.
2. Identifique quién administra el balanceador: AWS Load Balancer Controller, EKS Auto Mode y el aprovisionamiento heredado tienen responsables y ajustes diferentes. Haga coincidir los selectores y puertos del Service con el gateway real. Decida si TLS terminará en el NLB o en el gateway; no envíe texto sin cifrar a un listener TLS ni añada una segunda capa TLS por accidente.
3. Conceda permisos de AWS al componente que llama a las API de AWS, como el controlador del balanceador o el collector de telemetría. Envoy no necesita un rol de IAM únicamente para reenviar tráfico. Configure la relación de confianza y los permisos de IRSA o de la integración compatible con EKS Pod Identity; una anotación por sí sola no basta.
4. Abra solo las rutas de red necesarias y en la dirección requerida. Los puertos de interceptación del proxy no son una lista de puertos que deban exponerse indiscriminadamente en los grupos de seguridad. Incluya webhook/xDS, comprobaciones de estado y las rutas reales de entrada o ambient que correspondan.
5. Dimensione Istiod y los proxies según la carga observada, y asegure capacidad para programarlos y mantener su disponibilidad. Los PDB cubren determinadas interrupciones voluntarias; el número de réplicas por sí solo no garantiza diversidad entre zonas ni protección frente a todos los fallos.
6. Configure métricas, logs y trazas por separado. Un fragmento de salida cloudwatch_logs de Fluent Bit no constituye Container Insights ni una canalización completa con entrada CRI, parser, IAM y log stream.

Esta es una configuración ilustrativa de instalación para el HPA del plano de control y los requests/limits de los proxies:

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

Las 3–5 réplicas y las cantidades de recursos son ejemplos, no un dimensionamiento validado para producción. Revise las métricas del HPA, la ubicación de las cargas y la capacidad disponible. Evalúe ambient y el alcance de la configuración con mediciones reales de recursos y costes; no hay una garantía general de ahorro del 85 % ni del 30–50 %.

Consulte la [guía de integración de AWS](../../service-mesh/istio/04-aws-integration.md) y [buenas prácticas](../../service-mesh/istio/best-practices.md) para procedimientos completos.

</details>

## Pregunta adicional: Entrega progresiva

<details>
<summary>¿Qué hace útil el análisis de entrega progresiva y cuáles son sus límites?</summary>

Un Rollout completo necesita destinos de enrutamiento reales, capacidad estable, argumentos de análisis explícitos y una política de medición finita y significativa. La siguiente plantilla amplía el ejemplo del Service canario con volumen de solicitudes, disponibilidad HTTP y latencia P95:

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

Haga referencia a esta plantilla desde el paso de análisis correspondiente de un Rollout completo. No sustituye los selectores, la plantilla ni los Services que falten en un ejemplo incompleto de Rollout. Los umbrales son ilustrativos: los selectores de consulta, las unidades, el volumen de tráfico y el SLO de negocio deben ser coherentes entre sí.

Una medición fallida, un error del proveedor, un resultado no concluyente, un aborto y el despliegue posterior de una revisión anterior son estados diferentes. Inspeccione el estado de AnalysisRun/Rollout; no los describa a todos como una reversión instantánea. Abortar no revierte escrituras en la base de datos ni otros efectos de la aplicación. Los intervalos de los controladores, la disponibilidad del backend estable y la propagación de la configuración limitan el tiempo de recuperación.

La automatización puede reducir decisiones repetitivas, pero ningún umbral métrico demuestra que un despliegue sea seguro en todos los casos ni elimina la necesidad de diagnóstico humano. Pruebe los casos sin tráfico, con series ausentes, con todos los intentos fallidos, con NaN/infinito y de recuperación. La [guía completa](../../service-mesh/istio/advanced/08-argo-rollouts.md) incluye los recursos relacionados y los límites de validación.

</details>

## Autoevaluación

Use las 11 respuestas para identificar qué temas debe repasar. Una puntuación alta no demuestra preparación para operar en producción; incluya revisión y validación práctica en un entorno controlado.

## Recursos de aprendizaje

- [Documentación mantenida de Istio](../../service-mesh/istio/README.md)
- [Documentación oficial de Istio](https://istio.io/latest/docs/)
- [Integración Istio de Argo Rollouts](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Semántica de análisis Argo](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Resultados de consulta instantánea Prometheus](https://argo-rollouts.readthedocs.io/en/stable/analysis/prometheus/)
- [Configuración TLS de Istio](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Referencia API de Istio](https://istio.io/latest/docs/reference/config/)
