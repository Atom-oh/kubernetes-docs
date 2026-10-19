# Cuestionario de gestión del tráfico

> **Versión revisada**: Istio 1.31.0 **Versiones de EKS**: 1.34–1.36 **Última actualización**: 11 de septiembre de 2026

Este cuestionario comprueba tu comprensión de las funciones de gestión del tráfico de Istio.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Función de VirtualService

¿Cuál afirmación sobre VirtualService es **correcta**?

A. Es un recurso que sustituye a Kubernetes Service\
B. Solo puede definir algoritmos de balanceo de carga\
C. Define reglas de enrutamiento y controla el tráfico\
D. Envía todas las solicitudes de la aplicación a través de istiod

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

VirtualService es un CRD central de Istio que controla el tráfico al definir **reglas de enrutamiento**.

**Explicación:**

* A (X): VirtualService no sustituye a Kubernetes Service; añade reglas de enrutamiento sobre el servicio.
* B (X): DestinationRule configura el balanceo de carga; VirtualService define las reglas de enrutamiento.
* C (O): VirtualService puede definir:
  * reglas de enrutamiento HTTP/TCP;
  * enrutamiento basado en la ruta URL;
  * enrutamiento basado en encabezados;
  * división del tráfico por pesos;
  * ajustes de timeout y reintentos.
* D (X): istiod compila el objeto de la API VirtualService; Envoy aplica la configuración de enrutamiento resultante en el plano de datos.

**Ejemplo:**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

**Referencia:**

* [Enrutamiento](../../../service-mesh/istio/traffic-management/02-routing.md)
* [Conceptos de VirtualService](../../../service-mesh/istio/02-basic-concepts.md#1-virtualservice)

</details>

***

### Pregunta 2: Funciones de DestinationRule

¿Cuál de estas opciones **NO** es una función de DestinationRule?

A. Definir subconjuntos\
B. Configurar algoritmos de balanceo de carga\
C. Enrutar por la ruta HTTP\
D. Configurar el grupo de conexiones

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

El enrutamiento por la ruta HTTP corresponde a **VirtualService**.

**Explicación:**

**Funciones principales de DestinationRule:**

1. **Definir subconjuntos (A - O)**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

2. **Configurar el balanceo de carga (B - O)**

```yaml
spec:
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN  # RANDOM, LEAST_REQUEST, etc.
```

3. **Configurar el grupo de conexiones (D - O)**

```yaml
spec:
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
```

4. **Enrutar por la ruta HTTP (C - X)**

* Esta función corresponde a VirtualService:

```yaml
# Handled by VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: path-routing-example
spec:
  hosts:
  - api-service
  http:
  - match:
    - uri:
        prefix: /api  # Path-based routing
    route:
    - destination:
        host: api-service
```

**Tabla comparativa:**

| Función | VirtualService | DestinationRule |
| --- | --- | --- |
| Reglas de enrutamiento | Sí | No |
| Coincidencia de rutas | Sí | No |
| Definición de subconjuntos | No | Sí |
| Balanceo de carga | No | Sí |
| Grupo de conexiones | No | Sí |

**Referencia:**

* [Balanceo de carga](../../../service-mesh/istio/traffic-management/06-load-balancing.md)
* [Grupo de conexiones](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md)

</details>

***

### Pregunta 3: División del tráfico en un despliegue canary

¿Qué proporción del tráfico se dirige a v1 y a v2 con la siguiente configuración de VirtualService?

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 80
    - destination:
        host: reviews
        subset: v2
      weight: 20
```

A. v1: 50 %, v2: 50 %\
B. v1: 80 %, v2: 20 %\
C. v1: 20 %, v2: 80 %\
D. v1: 100 %, v2: 0 %

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

Como los valores de peso son **v1: 80, v2: 20**, el tráfico se reparte en **80 % para v1** y **20 % para v2**.

**Explicación:**

**División del tráfico por pesos:**

* El campo `weight` representa proporciones relativas.
* Peso total: 80 + 20 = 100.
* Proporción para v1: 80/100 = 80 %.
* Proporción para v2: 20/100 = 20 %.

**Etapas de un despliegue canary:**

```yaml
# Stage 1: 10% Canary
- weight: 90  # v1
- weight: 10  # v2

# Stage 2: 25% Canary
- weight: 75  # v1
- weight: 25  # v2

# Stage 3: 50% Canary
- weight: 50  # v1
- weight: 50  # v2

# Stage 4: 100% v2
- weight: 0   # v1
- weight: 100 # v2
```

**Despliegue canary automatizado con Argo Rollouts:**

```yaml
# Strategy fragment; merge into a complete Rollout with selector/template
strategy:
  canary:
    trafficRouting:
      istio:
        virtualService:
          name: reviews
        destinationRule:
          name: reviews
          stableSubsetName: v1
          canarySubsetName: v2
    steps:
    - setWeight: 10
    - pause: {duration: 2m}
    - setWeight: 25
    - pause: {duration: 2m}
    - setWeight: 50
    - pause: {duration: 2m}
```

**Referencia:**

* [División del tráfico](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md)
* [Integración con Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

***

### Pregunta 4: Propósito de Gateway

¿Cuál de estas opciones **NO** es una función de la configuración de un Gateway de entrada de Istio?

A. Definir puertos de escucha, protocolos y hosts permitidos\
B. Configurar la terminación TLS con un Secret de certificado\
C. Inyectar automáticamente un proxy en todos los pods de aplicación y proteger por sí solo todo el tráfico este-oeste\
D. Vincular el tráfico de entrada con el enrutamiento de VirtualService

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Un Gateway de Istio configura un proxy de gateway ya existente. La incorporación de cargas de trabajo a la malla y la seguridad entre servicios requieren el plano de datos sidecar o ambient, junto con sus políticas. Los proxies de gateway también pueden iniciar mTLS hacia los servicios upstream, por lo que la afirmación «Gateway nunca usa mTLS» también sería incorrecta. Gateway no emite certificados: `credentialName` hace referencia a un Secret que se administra por separado en el namespace de la carga de gateway.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts: [bookinfo.example.com]
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
```

[Gateway y VirtualService](../../../service-mesh/istio/traffic-management/01-gateway-virtualservice.md)

</details>

***

### Pregunta 5: Política de timeout y reintentos

¿Qué significa la siguiente configuración de VirtualService?

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
```

A. Reintenta hasta 3 veces después de la solicitud original; cada entrega dura como máximo 2 segundos y la solicitud completa, como máximo 10 segundos\
B. Reintenta hasta 3 veces dentro de un total de 2 segundos; cada intento dura como máximo 10 segundos\
C. Reintenta sin límite dentro de un total de 10 segundos; cada intento dura como máximo 2 segundos\
D. Falla después de 10 segundos sin reintentos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

Esta configuración permite **hasta 3 reintentos adicionales después de la solicitud original**, limita cada entrega a **2 segundos** y limita la solicitud completa a **10 segundos**. Por tanto, puede enviar la solicitud al servicio upstream hasta cuatro veces.

**Explicación:**

**Interpretación de la configuración:**

```yaml
timeout: 10s           # Maximum time for entire request
retries:
  attempts: 3          # Up to 3 retries after the original request
  perTryTimeout: 2s    # Time limit for each delivery
```

Estos ejemplos de tiempo presuponen un fallo que cumple `retryOn` y no incluyen el tiempo de espera entre intentos ni el procesamiento. Un timeout no implica que todas las políticas vayan a reintentar.

**Escenarios de ejecución:**

```
Scenario 1: First attempt succeeds
+- 1st attempt: 1.5s elapsed -> Success
+- Total time: 1.5s

Scenario 2: Success after 2 attempts
+- 1st attempt: 2s timeout -> Failure
+- 2nd attempt: 1.8s elapsed -> Success
+- Total time: 3.8s

Scenario 3: Original request plus all 3 retries fail
+- 1st attempt: 2s timeout -> Failure
+- 2nd attempt: 2s timeout -> Failure
+- 3rd attempt: 2s timeout -> Failure
+- 4th attempt: 2s timeout -> Failure
+- Total time: about 8s
```

**Configuración de las condiciones de reintento:**

```yaml
retries:
  attempts: 3
  perTryTimeout: 2s
  retryOn: 5xx,connect-failure,refused-stream  # Retry conditions
```

**Prácticas recomendadas:**

```yaml
# Read requests: limited retry
- match:
  - method:
      regex: "^(GET|HEAD)$"
  retries:
    attempts: 2
    perTryTimeout: 2s
    retryOn: connect-failure,refused-stream

# Write requests: disable mesh retry
- match:
  - method:
      regex: "^(POST|PUT|PATCH|DELETE)$"
  retries:
    attempts: 0
```

**Precauciones:**

* Para reservar tiempo para todos los reintentos, `timeout` debería ser, aproximadamente, mayor que `(1 + attempts) x perTryTimeout`, además del tiempo de espera entre intentos.
* Demasiados reintentos pueden causar fallos en cascada.
* `attempts: 0` desactiva los reintentos; `attempts: 1` permite repetir una vez después de la solicitud original.
* Desactiva de forma predeterminada los reintentos de malla para POST/PATCH: el servidor puede haber confirmado la operación y haberse perdido solo la respuesta.
* El mTLS de las cargas de trabajo o el cifrado de red no hacen segura la repetición de una solicitud.

**Referencia:**

* [Timeout y reintentos](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

***

## Preguntas de respuesta corta (6-10)

### Pregunta 6: Despliegue canary con Argo Rollouts e Istio

Describe un despliegue canary basado en subconjuntos, con controles automáticos basados en métricas. Incluye los recursos, el orden de creación y las condiciones de aborto.

<details>
<summary>Mostrar respuesta</summary>

Usa un Service, subconjuntos estable/canary en DestinationRule, una ruta VirtualService, AnalysisTemplates y un recurso Rollout completo. Argo actualiza los pesos de la ruta y los hashes de las plantillas de pods; no crea los recursos de Istio a los que se hace referencia previamente. La integración a nivel de host usa Services estables y canary separados. Los nombres de ruta deben coincidir con la lista de rutas explícita de Rollout; si hay una sola ruta, se puede omitir esa lista.

Usa un namespace de laboratorio nuevo con inyección sidecar y un controlador/CLI de Argo Rollouts compatible (la guía auditada usa v1.10.0). Añade a Prometheus la siguiente regla de relabeling para el scrape de pods y confirma que el tráfico canary tenga las etiquetas `rollout_hash` y `reporter="destination"`. Estos controles miden el ReplicaSet más reciente, en vez de promediarlo con el estable.

```yaml
# Existing workload pod scrape job: relabel_configs fragment
- source_labels: [__meta_kubernetes_pod_label_rollouts_pod_template_hash]
  target_label: rollout_hash
```

Crea primero los requisitos previos:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: default
spec:
  ports:
  - port: 9080
    name: http
  selector:
    app: reviews
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-destrule
  namespace: default
spec:
  host: reviews
  subsets:
  - name: stable
    labels:
      app: reviews
  - name: canary
    labels:
      app: reviews
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-vsvc
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - name: primary
    route:
    - destination:
        host: reviews
        subset: stable
      weight: 100
    - destination:
        host: reviews
        subset: canary
      weight: 0
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: default
spec:
  args:
  - name: service-name
  - name: pod-template-hash
  metrics:
  - name: success-rate
    interval: 30s
    count: 4
    successCondition: len(result) == 1 && !isNaN(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: "sum(rate(\n  istio_requests_total{\n    destination_service_name=\"\
          {{args.service-name}}\",\n    reporter=\"destination\",\n    rollout_hash=\"\
          {{args.pod-template-hash}}\",\n    destination_workload_namespace=\"default\"\
          ,\n    response_code!~\"5.*\"\n  }[2m]\n))\n/\nsum(rate(\n  istio_requests_total{\n\
          \    destination_service_name=\"{{args.service-name}}\",\n    reporter=\"\
          destination\",\n    rollout_hash=\"{{args.pod-template-hash}}\",\n    destination_workload_namespace=\"\
          default\"\n  }[2m]\n))\n"
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency
  namespace: default
spec:
  args:
  - name: service-name
  - name: pod-template-hash
  metrics:
  - name: latency-p95
    interval: 30s
    count: 4
    successCondition: len(result) == 1 && !isNaN(result[0]) && result[0] <= 500
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: "histogram_quantile(0.95,\n  sum(rate(\n    istio_request_duration_milliseconds_bucket{\n\
          \      destination_service_name=\"{{args.service-name}}\",\n    reporter=\"\
          destination\",\n    rollout_hash=\"{{args.pod-template-hash}}\",\n     \
          \ destination_workload_namespace=\"default\"\n    }[2m]\n  )) by (le)\n\
          )\n"
```

Después crea Rollout:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: reviews
  namespace: default
spec:
  replicas: 5
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: reviews
  template:
    metadata:
      labels:
        app: reviews
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: reviews
        image: docker.io/istio/examples-bookinfo-reviews-v2:1.20.3
        ports:
        - containerPort: 9080
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
  strategy:
    canary:
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
      steps:
      - setWeight: 10
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
      - setWeight: 25
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
      - setWeight: 50
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
      - setWeight: 75
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
```

El primer despliegue establece la versión estable; actualiza la imagen para probar las etapas canary. Cada etapa con peso tiene un control de análisis en línea y de duración finita. Con `failureLimit 0`, una medición fallida aborta el despliegue activo; un dato ausente/NaN no puede aprobarlo. Si el control se supera, se avanza a la etapa siguiente. El tiempo depende del tráfico, los intervalos de scraping/análisis y la reconciliación; no se garantiza que solo tarde unos segundos.

```bash
kubectl argo rollouts get rollout reviews --watch
kubectl get analysisruns
kubectl argo rollouts set image reviews reviews=istio/examples-bookinfo-reviews-v3:1.20.3
# Stop a failing active rollout; undo is a separate desired-template rollback
kubectl argo rollouts abort reviews
```

Deja que se propague la configuración y confirma que los endpoints estén sanos antes de desplazar el tráfico activo. Evita que otro controlador sobrescriba los pesos o hashes que administra Argo. Consulta la [guía completa de despliegues](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md) para los requisitos previos de instalación y ejecución.

</details>

***

### Pregunta 7: Blue/Green frente a canary

Compara cómo se desplaza el tráfico, los recursos necesarios, la reversión y los casos de uso adecuados.

<details>
<summary>Mostrar respuesta</summary>

| Aspecto | Blue/Green | Canary |
| --- | --- | --- |
| Tráfico | Primero vista previa; después se cambia el selector del Service activo | Se aumenta gradualmente el peso de las solicitudes enrutadas |
| Validación | Análisis antes y después de la promoción | Análisis en línea/en segundo plano durante el avance |
| Capacidad | A menudo hay dos revisiones completas durante la transición; el tamaño de la vista previa puede variar | Depende de las réplicas y de la política de escalado; conservar toda la capacidad estable puede acercarse a dos revisiones |
| Reversión | Volver a la revisión anterior mientras sigan disponibles esa revisión y su capacidad | Abortar el despliegue activo para volver a estable; después de la promoción, deshacer o volver a desplegar según corresponda |
| Principal contrapartida | Cambio de producción sencillo, con un impacto amplio al promover | Menor exposición en cada etapa, con más coordinación de enrutamiento/análisis |

Ninguno de los cambios de tráfico es atómico a nivel de red: importan la propagación de endpoints/proxies y las conexiones existentes. Ninguno revierte migraciones de bases de datos ni efectos externos. Mantén compatibles los esquemas y contratos de API mientras coexistan las versiones. El peso canary no identifica un grupo estable de usuarios; las pruebas A/B necesitan una clave de grupo explícita.

Blue/Green es adecuado para versiones que se puedan previsualizar ampliamente y dispongan de capacidad temporal suficiente. Canary sirve para validar gradualmente en producción cuando hay tráfico representativo y métricas confiables. No elijas canary suponiendo un coste de «1x más un poco»: revisa sus ajustes de escalado, incluido `dynamicStableScale` si se usa.

```yaml
# Alternative strategy fragment for a complete Rollout
strategy:
  blueGreen:
    activeService: myapp-active
    previewService: myapp-preview
    autoPromotionEnabled: false
    scaleDownDelaySeconds: 600
    prePromotionAnalysis:
      templates:
      - templateName: smoke-tests
    postPromotionAnalysis:
      templates:
      - templateName: post-promotion-tests
```

Crea los Services y los AnalysisTemplates coincidentes con sus argumentos obligatorios antes de usarlos. Elige una retención que cubra las necesidades de análisis posterior a la promoción y de reversión. Una progresión híbrida es un flujo de trabajo diseñado; cambiar un campo de estrategia durante un despliegue no lo convierte automáticamente de canary a Blue/Green.

[Estrategias de despliegue y ejemplos](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md)

</details>

***

### Pregunta 8: Reflejo del tráfico (pruebas en sombra)

Explica cómo probar de forma segura versiones nuevas mediante el reflejo del tráfico. Incluye **casos de uso**, **métodos de configuración** y **precauciones**.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Concepto de reflejo del tráfico:**

El reflejo del tráfico duplica el tráfico de producción y lo envía a una versión nueva, pero **ignora sus respuestas**. También se conoce como «prueba en sombra».

***

**1. Cómo funciona**

![Un usuario envía una solicitud que Envoy duplica: la solicitud principal llega a la versión 1 de producción y la solicitud reflejada a la versión 2 de prueba, cuya respuesta se descarta.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-traffic-management-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-traffic-management-0.html)

**Características clave:**

* Los usuarios solo reciben la respuesta de v1.
* Envoy descarta la respuesta de v2.
* Aunque la respuesta de v2 no se devuelve al cliente, la contención de recursos compartidos y los efectos secundarios de escritura pueden afectar a los usuarios.

***

**2. Métodos de configuración**

**Reflejo básico (100 %):**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100  # Primary traffic
    mirror:
      host: reviews
      subset: v2  # Mirror target
    mirrorPercentage:
      value: 100  # 100% mirroring
```

**Reflejo parcial (50 %):**

```yaml
spec:
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100
    mirror:
      host: reviews
      subset: v2
    mirrorPercentage:
      value: 50  # Only 50% mirroring (reduce traffic load)
```

**Combinación de reflejo y canary:**

```yaml
spec:
  http:
  - route:
    # Primary traffic: 90% v1, 10% v2
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10

    # Mirroring: Mirror all traffic to v3 (test)
    mirror:
      host: reviews
      subset: v3
    mirrorPercentage:
      value: 100
```

***

**3. Casos de uso**

**Caso 1: Pruebas de rendimiento de una versión nueva**

```
Purpose: Verify if v2's performance is better than v1

1. Run v1 (production) + v2 (mirror) simultaneously
2. Monitor v2's latency, CPU, memory
3. If v2 is faster than v1 -> Proceed with Canary deployment
4. If v2 is slower than v1 -> Optimize and retest
```

**Caso 2: Validación de una migración de base de datos**

```
Purpose: Verify new database schema

1. v1 -> Existing DB
2. v2 -> New DB (mirroring)
3. Verify v2's query performance and error rate
4. If no issues -> Switch to v2
```

**Caso 3: Validación de una corrección de errores**

```
Purpose: Verify that bug fix actually works

1. Run v1 (with bug) + v2 (fixed version, mirror)
2. Test v2 with production traffic
3. If v2's error rate decreases -> Deploy
```

**Caso 4: Calentamiento de caché**

```
Purpose: Pre-populate new version's cache

1. Deploy v2, then warm its cache with mirror traffic before cutover
2. Once v2's cache is sufficiently populated
3. Warmup can reduce cache misses; it does not guarantee no cold start
```

***

**4. Configuración de la supervisión**

**Supervisar el tráfico reflejado con consultas de Prometheus:**

```promql
# v2 (mirror) error rate
sum(rate(
  istio_requests_total{
    destination_version="v2",
    response_code=~"5.."
  }[5m]
))
/
sum(rate(
  istio_requests_total{
    destination_version="v2"
  }[5m]
))

# v1 vs v2 latency comparison
histogram_quantile(0.95,
  sum(rate(
    istio_request_duration_milliseconds_bucket[5m]
  )) by (destination_version, le)
)
```

**Panel de Grafana:**

```yaml
# Panel 1: Error rate comparison (v1 vs v2)
# Panel 2: Latency comparison (P50, P95, P99)
# Panel 3: CPU/Memory usage
# Panel 4: Request count (v1: actual, v2: mirror)
```

***

**5. Precauciones**

**Advertencia: aumento de carga**

```
Mirroring increases service load.

Example:
- v1: 1000 RPS
- v2: 1000 RPS (mirror)
- Total load: 2000 RPS

Choose the percentage from shadow capacity and the test hypothesis; 50% is not a universal safe limit
```

**Advertencia: vigila los efectos secundarios**

```text
# Don't mirror write operations!

# Bad example
POST /api/orders  # Both v1 and v2 create orders -> Duplicates!

# Good example
GET /api/orders   # Mirror only read-only operations
```

**Advertencia: coste**

```
Mirroring increases resources and costs.

- 100% mirroring duplicates request volume on that route
- CPU, response traffic, and database cost depend on workload behavior

Solution: Mirror only for short periods (1-2 days)
```

**Advertencia: las respuestas no se pueden validar**

```
Mirror traffic responses are discarded, so
Istio does not compare response content. Application instrumentation or a dedicated shadow comparison system can validate correctness separately.

Can validate:
- Error rate
- Latency
- Resource usage

Cannot validate:
- Response/business correctness requires additional validation tooling
```

***

**6. Prácticas recomendadas**

```text
# Good examples
1. Mirror only read-only APIs
2. mirrorPercentage: 50% (reduce load)
3. Short-term testing (1-2 days)
4. Automatic validation based on metrics

# Bad examples
1. Mirroring write operations (duplicate data)
2. mirrorPercentage: 100% without capacity planning
3. Long-term mirroring (cost increase)
4. Manual validation (slow)
```

**Referencia:**

* [Reflejo del tráfico](../../../service-mesh/istio/traffic-management/09-traffic-mirror.md)

</details>

***

### Pregunta 9: Localidad y costes entre zonas de disponibilidad

Explica el enrutamiento por localidad en EKS, los requisitos para la conmutación por error y cómo estimar el ahorro a partir del tráfico medido.

<details>
<summary>Mostrar respuesta</summary>

istiod obtiene la localidad de la topología de los nodos; los pods no heredan automáticamente las etiquetas del nodo. Inspecciona los nodos y la localidad de los endpoints del proxy:

```bash
kubectl get pods -o wide
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config endpoints <pod-name> -o json
```

Este es un ejemplo de distribución ponderada:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-locality
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80
            "us-east-1/us-east-1b/*": 20
        - from: us-east-1/us-east-1b/*
          to:
            "us-east-1/us-east-1b/*": 80
            "us-east-1/us-east-1a/*": 20
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

El 20 % remoto es tráfico activo, no capacidad de reserva inactiva. `failover` explícito es una alternativa a `distribute`, y sus valores `from`/`to` son **regiones**, por ejemplo, us-east-1 a us-west-2; no son rutas región/zona. La conmutación por error entre zonas usa la localidad y el estado de salud de los endpoints. Mantén capacidad sana en otras zonas de disponibilidad y verifica el comportamiento de expulsión y pánico. Un PDB limita las interrupciones voluntarias; no crea réplicas ni evita un fallo de zona.

**Cálculo hipotético, no cotización de AWS:** supón 200 000 GB facturables al mes, una reducción de la proporción entre zonas del 70 % al 20 % y una tarifa efectiva de 0,01 USD por GB facturable para la ruta medida.

| | Antes | Después |
| --- | ---: | ---: |
| GB entre zonas | 140 000 | 40 000 |
| Cargo mensual modelado | 1 400 USD | 400 USD |

El ahorro modelado es de 1 000 USD al mes (71,4 %) o 12 000 USD al año. Usa las tarifas reales de la ruta de facturación, las direcciones, los cargos de balanceadores/NAT/servicios y los bytes medidos; no calcules el tráfico multiplicando el número de servicios por sí mismo. Las tarifas actuales dependen de la región y del servicio/ruta, y el tráfico dentro de una misma zona no está necesariamente exento de todos los cargos de procesamiento.

`source_cluster` y `destination_cluster` son identificadores de clúster, no zonas de disponibilidad. Las métricas estándar de Istio no proporcionan automáticamente todas las etiquetas de zona de origen/destino. Usa telemetría de topología configurada explícitamente o VPC Flow Logs con la correspondencia temporalmente correcta de endpoints/zonas y los datos de facturación. Mide la latencia con tráfico controlado; no se garantiza una mejora fija del 30–60 %.

- [Precios de transferencia de EC2](https://aws.amazon.com/ec2/pricing/on-demand/)
- [Campos de VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html)
- [Guía de localidad](../../../service-mesh/istio/traffic-management/06-load-balancing.md)

</details>

***

### Pregunta 10: Configuración TLS de Gateway

Explica la terminación TLS en Istio frente a la terminación TLS de ACM en un NLB, incluidos los redireccionamientos HTTP y la renovación de certificados.

<details>
<summary>Mostrar respuesta</summary>

Elige un único diseño de terminación. Supón que la carga de gateway está en `istio-system`, con etiquetas `istio=ingressgateway`, puertos de Service coincidentes y AWS Load Balancer Controller instalado. Aplica los cambios del Service mediante la herramienta que lo administra. El ARN del certificado del NLB y `credentialName` de Istio son objetos distintos.

**1. Terminación TLS en Istio**

Usa passthrough TCP en el NLB. Para una prueba local, genera un certificado con SAN DNS y confía en él explícitamente desde el cliente. Sustituye los nombres de host de ejemplo por un dominio que controles:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout bookinfo.key -out bookinfo.crt \
  -subj "/CN=bookinfo.example.com" \
  -addext "subjectAltName=DNS:bookinfo.example.com"
kubectl create secret tls bookinfo-secret -n istio-system \
  --key=bookinfo.key --cert=bookinfo.crt
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts: [bookinfo.example.com]
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts: [bookinfo.example.com]
    tls:
      httpsRedirect: true
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo-vs
  namespace: default
spec:
  hosts: [bookinfo.example.com]
  gateways: [istio-system/bookinfo-gateway]
  http:
  - route:
    - destination:
        host: productpage
        port:
          number: 9080
```

```bash
# INGRESS_HOST is the actual LB hostname; preserve the certificate hostname/SNI
curl --cacert bookinfo.crt \
  --connect-to "bookinfo.example.com:443:${INGRESS_HOST}:443" \
  https://bookinfo.example.com/productpage
curl -I --connect-to "bookinfo.example.com:80:${INGRESS_HOST}:80" \
  http://bookinfo.example.com/productpage
```

**2. Terminación TLS en ACM en el NLB**

Usa un certificado ACM con estado `ISSUED` y validado por DNS en la región del NLB. Solicitar un certificado no completa la validación. Un NLB es un balanceador de capa de transporte y no realiza redireccionamientos HTTP; la política de negociación SSL solo selecciona versiones/cifrados TLS. Envía el tráfico descifrado del puerto 443 a un puerto de destino del gateway distinto del puerto del listener de redirección HTTP para evitar un bucle:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: external
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:us-east-1:123456789012:certificate/replace-with-issued-certificate
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
    service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
spec:
  type: LoadBalancer
  selector:
    istio: ingressgateway
    app: istio-ingressgateway
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: https
    port: 443
    targetPort: 8081
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http-redirect
      protocol: HTTP
    hosts: [bookinfo.example.com]
    tls:
      httpsRedirect: true
  - port:
      number: 443
      name: http-after-nlb
      protocol: HTTP
    hosts: [bookinfo.example.com]
```

Esta alternativa sustituye el Gateway TLS anterior y usa la misma asociación VirtualService. En este ejemplo, el tramo entre el NLB y el gateway está en texto claro. Para cifrar ese tramo, configura un diseño TLS de backend separado; no combines de forma incompatible un listener SIMPLE y uno passthrough.

**3. Autenticación de cliente con certificados en Istio**

Para un listener Istio MUTUAL, usa un Secret que contenga las credenciales del servidor y la CA de confianza del cliente; no combines `credentialName` con una ruta de archivo de CA separada:

```bash
kubectl create secret generic server-cert-secret -n istio-system \
  --from-file=tls.crt=server.crt --from-file=tls.key=server.key \
  --from-file=ca.crt=client-ca.crt
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: mutual-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https-mutual
      protocol: HTTPS
    hosts: [secure.example.com]
    tls:
      mode: MUTUAL
      credentialName: server-cert-secret
      minProtocolVersion: TLSV1_2
```

```bash
curl --cacert server-ca.crt --cert client.crt --key client.key \
  https://secure.example.com/api
```

Configura un VirtualService/DNS que coincida con ese host. Un SAN comodín como `*.example.com` cubre una etiqueta a la izquierda (`api.example.com`), pero no `example.com` ni `x.api.example.com`. Define los SAN de forma explícita. El campo `cipherSuites` configura suites anteriores a TLS 1.3; no selecciona suites de cifrado de TLS 1.3.

**4. Renovación de certificados**

cert-manager 1.21 admite Kubernetes 1.33–1.36; vuelve a comprobar su matriz de versiones antes de instalarlo o actualizarlo. Si aún no se administra en el clúster, la versión auditada es v1.21.1:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.21.1/cert-manager.yaml
```

Configura un Issuer/ClusterIssuer en estado Ready con un solucionador de desafíos que coincida con tu configuración real de ingress/Gateway API/DNS. Una cadena de clase ingress por sí sola no garantiza que se pueda acceder a los desafíos ACME. Después, crea el Certificate en el namespace de la carga de gateway:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: bookinfo-cert
  namespace: istio-system
spec:
  secretName: bookinfo-secret
  issuerRef:
    name: configured-issuer
    kind: ClusterIssuer
  dnsNames: [bookinfo.example.com]
```

```bash
kubectl wait --for=condition=Ready certificate/bookinfo-cert -n istio-system --timeout=120s
```

Istio observa el Secret resultante; cert-manager realiza la renovación. Evita que haya varios propietarios manuales del Secret. Un ingreso público necesita certificados en los que confíen sus clientes; el ejemplo autofirmado anterior sirve para configurar la confianza en un laboratorio, mientras que una PKI interna exige administrar deliberadamente la distribución de confianza y el ciclo de vida.

- [Integración de cert-manager con Istio](https://istio.io/latest/docs/ops/integrations/certmanager/)
- [Versiones compatibles con cert-manager](https://cert-manager.io/docs/releases/)
- [Ejemplos de integración con AWS](../../../service-mesh/istio/04-aws-integration.md)

</details>

***

## Cálculo de la puntuación

* Preguntas de opción múltiple 1-5: 10 puntos cada una (50 puntos en total).
* Preguntas de respuesta corta 6-10: 10 puntos cada una (50 puntos en total).
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90-100 puntos: Excelente (especialista en gestión del tráfico de Istio).
* 80-89 puntos: Bueno (preparado para operaciones de producción).
* 70-79 puntos: Promedio (se recomienda estudiar más).
* 60-69 puntos: Por debajo del promedio (conviene repasar los conceptos básicos).
* 0-59 puntos: Necesita volver a estudiar.

## Recursos de aprendizaje

* [Documentación de gestión del tráfico](../../../service-mesh/istio/traffic-management/README.md)
* [VirtualService](../../../service-mesh/istio/traffic-management/02-routing.md)
* [Gateway](../../../service-mesh/istio/traffic-management/01-gateway-virtualservice.md)
* [División del tráfico](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md)
* [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

* [Referencia principal 1](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
* [Referencia principal 2](https://istio.io/latest/docs/reference/config/networking/gateway/)
* [Referencia principal 3](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
* [Referencia principal 4](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.0/docs/features/traffic-management/istio.md)
* [Referencia principal 5](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.0/docs/analysis/prometheus.md)
* [Referencia principal 6](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.0/docs/features/bluegreen.md)
* [Referencia principal 7](https://aws.amazon.com/ec2/pricing/on-demand/)
* [Referencia principal 8](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html)
* [Referencia principal 9](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
* [Referencia principal 10](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)
* [Referencia principal 11](https://cert-manager.io/docs/releases/)
* [Referencia principal 12](https://istio.io/latest/docs/ops/integrations/certmanager/)
* [Referencia principal 13](https://cert-manager.io/docs/usage/certificate/)
* [Referencia principal 14](https://www.rfc-editor.org/rfc/rfc9525.html)
