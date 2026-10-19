# Escalado automático con KEDA y métricas de Istio

> **Base de verificación**: KEDA/chart 2.20.2, Istio 1.31.0, Kubernetes 1.32–1.37
> **Última revisión**: 16 de octubre de 2026

Esta guía explica las señales de escalado y sus límites. Presupone que las cargas de trabajo ya existen, que las métricas están verificadas y que el clúster tiene capacidad suficiente. Los ejemplos que apuntan al mismo Deployment son **alternativas**: elige un único propietario de ScaledObject/HPA por destino; no apliques todos los objetos de esta página.

## Tabla de contenido

1. [Descripción general](#overview)
2. [Arquitectura](#architecture)
3. [Escalado mediante métricas de Prometheus](#prometheus-metrics-based-scaling)
4. [Escalado mediante métricas de CloudWatch](#cloudwatch-metrics-based-scaling)
5. [Estrategias prácticas de escalado](#practical-scaling-strategies)
6. [Prácticas recomendadas](#best-practices)
7. [Solución de problemas](#troubleshooting)
8. [Referencia: instalación de KEDA](#reference-keda-installation)

## Descripción general {#overview}

Kubernetes HPA admite métricas de recursos, personalizadas y externas a través de las API correspondientes, incluidas varias métricas a la vez. CloudWatch puede integrarse mediante un adaptador; no es inherentemente incompatible con HPA. KEDA proporciona escaladores, una API de métricas externas y gestión de activación, mientras que HPA sigue encargándose del escalado habitual de réplicas.

| Señal | Significado | Uso y limitación |
|---|---|---|
| `istio_requests_total` | Contador de solicitudes HTTP/gRPC | La tasa puede medir la carga admitida; elige un reporter y la carga de trabajo de destino reales |
| `istio_request_duration_milliseconds_bucket` | Cubos del histograma clásico de latencia | Los cuantiles son observaciones de calidad, no señales inversas de capacidad garantizadas |
| `istio_tcp_connections_opened_total` | Contador acumulado de conexiones abiertas | Su tasa mide la creación de conexiones, no las conexiones que siguen activas |
| `istio_request_bytes_sum` | Bytes acumulados de solicitudes HTTP observados | La tasa mide el caudal; limita el alcance por reporter y carga de trabajo |
| `envoy_cluster_upstream_rq_pending_overflow` | Contador de desbordamientos del clúster del lado cliente | Diagnostica límites del pool y dependencias antes de decidir qué carga, si alguna, debe escalarse |

Una métrica de demanda o trabajo pendiente calibrada sirve como punto de partida. La latencia, los errores y los eventos del circuit breaker pueden deberse a fallos posteriores que no se solucionan añadiendo réplicas. La gestión de la pertenencia de los miembros en cargas con estado, el almacenamiento y la semántica de la aplicación también limitan el escalado; que una carga sea «con estado» o «sensible a la latencia» no basta para elegir una política segura.

## Arquitectura {#architecture}

KEDA crea o configura un HPA para el destino y expone métricas externas. El controlador HPA solicita métricas a través de esa API y actualiza el subrecurso `/scale` del destino; luego, el controlador del destino y el planificador crean y ubican los Pods.

| Ajuste o componente | Responsabilidad |
|---|---|
| KEDA `pollingInterval` | Consultar los disparadores y gestionar la activación, incluido el paso de 0→1 |
| Sincronización del controlador HPA | Solicitudes adicionales de métricas y decisiones de 1→N; el periodo predeterminado es de 15 segundos y se puede configurar en el clúster |
| `useCachedMetrics` | Almacenamiento opcional en caché de métricas de KEDA entre consultas; no se activa en estos ejemplos |
| `activationThreshold` | Umbral de activación para 0↔1, no un segundo umbral de reducción de réplicas de HPA |
| `cooldownPeriod` | Espera tras la inactividad antes de que KEDA reduzca a 0; no es una pausa después de cada reducción |
| HPA `behavior` | Límites de estabilización y velocidad de cambio de 1→N |

Si `minReplicaCount` es mayor que 0, no uses la activación ni el cooldown como histéresis habitual de réplicas. La captura→scrapeo→consulta→HPA→inicio y preparación del Pod añaden latencia; ni una consulta cada 15 segundos ni una estabilización de cero garantizan capacidad lista de inmediato.

### Tipos de métricas y cálculo ideal

Sin tener en cuenta la tolerancia de HPA, los Pods no listos o con métricas ausentes, los límites ni las políticas de comportamiento:

- **AverageValue + demanda total**: réplicas deseadas ≈ `ceil(total metric / target per Pod)`.
- **Value + valor de toda la carga**: réplicas deseadas ≈ `ceil(current replicas × observed value / target value)`.

Con 600 RPS y 100 RPS/Pod, AverageValue solicita 6 réplicas. Si primero divides la consulta entre 3 Pods, obtienes 200 y solicitas erróneamente 2. `count(up)` cuenta objetivos de scrapeo y tampoco es un divisor seguro de réplicas.

Con 4 réplicas, una latencia global de 300 ms y un objetivo Value de 200 ms sugieren 6 réplicas. Si añadir réplicas no reduce esa latencia, las decisiones repetidas pueden llevar la carga hasta su límite máximo. Considera los controladores basados en latencia o tasa de errores como experimentos que requieren pruebas de retroalimentación negativa, no como valores predeterminados para producción.

## Escalado mediante métricas de Prometheus {#prometheus-metrics-based-scaling}

Los ejemplos presuponen un Deployment real llamado `reviews` en `default`. Un nombre de Service no es un destino de escalado. Bookinfo publicado suele usar nombres de Deployment como `reviews-v1`; adapta `scaleTargetRef` y los selectores de métricas a la carga real, en vez de suponer que coinciden con un Service.

Verifica un scrapeo de cada proxy pertinente y sus etiquetas reales. Los ejemplos principales usan `reporter="destination"` para evitar contar dos veces los informes de solicitudes. Esto mide las solicitudes admitidas por el destino; los rechazos o las colas en el borde pueden requerir una señal de demanda medida por separado.

### 1. Escalado basado en RPS

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-rps-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

La consulta incluye las solicitudes fallidas como carga y devuelve el RPS total. `threshold: "100"` es el objetivo por réplica de AverageValue; no es un interruptor global que signifique «si se supera 100, añade un Pod». No vuelvas a dividir por el número de Pods.

Con `ignoreNullValues: "false"`, en KEDA 2.20.2 los resultados ausentes, NaN o infinitos de Prometheus se consideran errores. Una tasa de contador realmente igual a cero sigue siendo 0. Configura y prueba el fallback ante fallos del origen; no conviertas silenciosamente cualquier métrica ausente en 0. Establece el contrato de captura y métricas antes de activar el escalador.

En este caso, el fallback usa el valor mayor entre el mínimo configurado y las réplicas actuales una vez alcanzado el umbral de errores configurado, y sigue sujeto a los límites y al comportamiento de HPA. No protege si la API de métricas de KEDA está caída o no hay capacidad de nodos.

### 2. Control basado en latencia: experimento sujeto a validación

Esta alternativa usa explícitamente Value para el p95 de toda la carga:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-latency-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

La consulta devuelve 0 solo cuando la tasa del recuento real del histograma es cero. Si faltan datos de telemetría, el resultado sigue ausente; los cuantiles inválidos continúan siendo errores, no un 0 saludable. Un p95 de 0 en una ventana inactiva es un valor de control intencional, no una solicitud observada con duración cero.

Los cuantiles múltiples también son métricas Value:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-quantile-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p50
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.5, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '50'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p99
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.99, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '500'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

HPA elige el mayor número de réplicas deseado, no un promedio ni una combinación ponderada. Los cuantiles están correlacionados; más disparadores no mejoran necesariamente la estabilidad ni garantizan la latencia.

### 3. Control de tasa de errores: experimento sujeto a validación

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-error-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: error-percent
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (100 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
          and on() (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '5'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Se trata de un porcentaje global de respuestas 5xx o con estado cero y un objetivo Value. El tráfico inactivo conocido devuelve 0; la ausencia de telemetría no se presenta como 0. Usa un controlador basado en errores solo después de demostrar que esos errores se deben a falta de réplicas. Las interrupciones de dependencias, los fallos de autorización o los límites del pool del cliente pueden volver ineficaz o perjudicial el escalado.

### 4. Métricas compuestas

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-composite-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

La entrada RPS es demanda total con AverageValue; la entrada de latencia es Value. HPA aplica la recomendación mayor. En el escalado, `selectPolicy: Max` elige el mayor cambio permitido: una política de cinco Pods no es un tope absoluto si la política porcentual permite más. Estas alternativas también requieren pruebas de carga y capacidad.

## Escalado mediante métricas de CloudWatch {#cloudwatch-metrics-based-scaling}

La cadencia del origen de CloudWatch, la latencia de publicación, el periodo de agregación, la ventana de consulta y el desfase determinan la antigüedad de los datos. Existen métricas personalizadas de alta resolución; es incorrecto afirmar que «CloudWatch siempre tiene un retraso de 1–3 minutos». Prometheus también tiene latencia de recopilación y del bucle de control.

### Identidad y contrato de las métricas publicadas

Estos ejemplos usan un rol del operador de KEDA configurado mediante IRSA y este TriggerAuthentication en el espacio de nombres de la carga:

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
```

`podIdentity.provider: aws` es el proveedor actual para IRSA. Su `identityOwner: keda` es distinto de los metadatos obsoletos del escalador `identityOwner: operator/pod`, que siguen admitidos en la versión 2.20 pero está previsto eliminarlos en la 3. No confundas el antiguo nombre de proveedor `aws-eks` con una nueva asociación de EKS Pod Identity. Usa la configuración de proveedor y credenciales del SDK documentada para el mecanismo de identidad elegido.

El ejemplo de publicación que aparece más adelante en esta guía emite:

| Métrica | Espacio de nombres y dimensiones exactas | Interpretación |
|---|---|---|
| `IstioRequestsPerSecond` | `IstioScaling`; ClusterName=`eks-demo`, destination_workload=`reviews`, destination_workload_namespace=`default` | Indicador RPS precalculado |
| `IstioP95LatencyMilliseconds` | El mismo conjunto de dimensiones | Indicador p95 precalculado por ventana, en milisegundos |

Todas las dimensiones deben coincidir. Una consulta que solo incluya destination_workload no identifica la misma métrica personalizada.

### Indicador RPS

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Promediar el indicador durante su periodo de 60 segundos conserva las unidades de RPS. Sumar muestras acumuladas de `istio_requests_total` no produce un recuento de solicitudes por minuto. Si se publica una métrica de deltas por periodo, deriva para ella un objetivo distinto y calibrado.

`minMetricValue` aparece explícitamente para el analizador de escaladores publicado, pero `ignoreNullValues: "false"` prevalece cuando no hay resultados. `metricEndTimeOffset` omite puntos recientes que quizá estén incompletos; añade demora y no demuestra que los datos sean recientes. Supervisa las marcas de tiempo y el estado del publicador, incluidos los resultados antiguos pero no vacíos.

### Indicador de latencia precalculada

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-p95-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-p95
    metricType: Value
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioP95LatencyMilliseconds
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '200'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Maximum
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Esto solicita el valor más alto del indicador p95 publicado para el periodo. **No** es el p95 de todas las solicitudes de ese periodo de CloudWatch. No solicites `metricStat: p95` sobre una conversión de histograma de Prometheus ni sobre un indicador p95 de otro p95 alegando que conserva la distribución original. Para usar percentiles nativos de CloudWatch hacen falta muestras o estadísticas publicadas de forma adecuada.

### Varias fuentes no son conmutación ordenada por prioridad

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-dual-source-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: prom-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Ambas métricas participan en la recomendación máxima de HPA. «Prometheus principal, CloudWatch secundario» no define prioridad ni conmutación por error; los valores antiguos pueden mantener elevada la recomendación de réplicas. Elige una única fuente deliberadamente o diseña y prueba la combinación de fuentes y fallback.

## Estrategias prácticas de escalado {#practical-scaling-strategies}

### 1. Mínimo programado de réplicas

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-scheduled-floor
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Durante la ventana laborable de Asia/Seoul, el disparador Cron establece un mínimo de 20 réplicas, mientras la demanda puede solicitar más hasta el máximo configurado. Es escalado programado, no un modelo de predicción del tráfico. Programa el aumento antes de la demanda si el inicio y la preparación requieren tiempo.

### 2. Escalado explícito a cero fuera del horario

Para una carga que puede no estar disponible fuera del horario de oficina, usa un recuento deseado positivo durante la ventana y `minReplicaCount: 0`:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: analytics-office-hours
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: analytics-service
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
```

`desiredReplicas: "0"` no es válido en Cron. Fuera de la ventana activa, KEDA puede volver a 0 según sus reglas de inactividad y cooldown. Una solicitud del cliente no activa una carga que solo usa Cron. Las métricas de Istio del lado del destino desaparecen junto con la aplicación, por lo que no pueden proporcionar por sí solas una señal fiable de demanda para pasar de 0→1. Si se necesita disponibilidad bajo demanda, usa una cola o interceptor observable de forma independiente, o mantén un mínimo positivo.

PromQL `hour()` usa UTC; no hereda la zona horaria Asia/Seoul del escalador Cron. No mezcles ambos como si sus ventanas de horario laboral fueran idénticas.

### 3. Primero, señales diagnósticas del circuit breaker

El desbordamiento del lado cliente y las conexiones actuales se pueden inspeccionar por separado:

```promql
sum(increase(envoy_cluster_upstream_rq_pending_overflow{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
}[1m]))

sum(envoy_cluster_upstream_cx_active{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})

max(envoy_cluster_circuit_breakers_default_cx_open{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})
```

Verifica el nombre y puerto reales del clúster, las estadísticas exportadas y el alcance del scrapeo. `cx_open` es una bandera de circuit breaker con valor 0/1, no la capacidad de conexiones; dividir las conexiones activas por ese valor no calcula un porcentaje de saturación. Añadir réplicas de backend no aumenta los límites fijos del pool de conexiones de un cliente. Diagnostica el límite o la dependencia antes de asignar un objetivo de escalado.

### 4. Las políticas de escalado no son niveles de carga

Las listas de políticas de HPA con Percent/Pods y `selectPolicy: Max` o `Min` limitan los cambios permitidos durante periodos móviles. No eligen automáticamente niveles de carga «bajo», «medio» y «alto» a partir de comentarios. Usa el ejemplo principal de comportamiento para limitar los cambios y valídalo frente a la respuesta medida de la carga.

### 5. Demanda de backend observada por el gateway

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: backend-gateway-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: gateway-backend-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="source",source_workload="istio-ingressgateway",source_workload_namespace="istio-system",destination_service_name="backend",destination_service_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Verifica el nombre real de la carga del gateway y las etiquetas del Service de destino. Esto mide el tráfico de ese gateway hacia un backend concreto. `envoy_http_downstream_rq_active` cuenta solicitudes HTTP activas, no conexiones pendientes, y el agregado de todo el gateway incluye servicios ajenos. No uses ese agregado para escalar un backend arbitrario.

Este ejemplo mantiene un mínimo positivo. Si consideras usar 0 réplicas, demuestra primero que el gateway o interceptor independiente sigue emitiendo la métrica sin endpoints de backend y ofrece el comportamiento deseado de buffering de solicitudes o de errores.

## Prácticas recomendadas {#best-practices}

### 1. Un destino, un solo propietario del escalador

No instales varios ScaledObjects de ejemplo ni un «HPA de respaldo» adicional para el mismo destino. Coordina quién es propietario del HPA existente y los campos de réplicas de GitOps antes de cambiar nada. Un ScaledObject puede contener varias métricas; HPA nativo puede omitir la reducción de réplicas cuando una métrica falla y, aun así, permitir una recomendación válida de aumento.

El fallback de KEDA 2.20 admite disparadores AverageValue y Value, excepto CPU/memoria; se aplica a ScaledObjects, no a ScaledJobs. Un disparador de CPU/memoria requiere sus propios prerrequisitos de metrics-server y de solicitudes de recursos, y no es un controlador independiente de conmutación por error.

### 2. Ejemplo de planificación de capacidad, no un benchmark

Los siguientes valores se conservan como **datos hipotéticos de entrada**:

| Supuesto o cálculo | Resultado |
|---|---|
| Capacidad medida asumida: 200 RPS/Pod × factor de utilización elegido del 70 % | Objetivo de 140 RPS/Pod |
| Carga normal 500 / 140, redondeada hacia arriba | 4 réplicas |
| Pico de carga 2000 / 140, redondeado hacia arriba | 15 réplicas |
| Máximo elegido con margen adicional | 20, sujeto a la capacidad realmente planificable |

Esta auditoría no midió esos valores. Ejecuta una prueba de carga acotada y aprobada con un objetivo y recuento de réplicas conocidos; registra latencia, errores, recursos y preparación. Que un Service distribuya carga entre varias réplicas no mide directamente la capacidad de un Pod.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-capacity-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 4
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '140'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 4
    behavior: currentReplicasIfHigher
```

No existe una regla universal «maxReplicaCount ≤70 % de la capacidad del clúster»: el número de Pods no es un porcentaje de CPU, memoria, direcciones IP ni cuota. HPA/KEDA escalan cargas de trabajo; la capacidad de nodos requiere una configuración de aprovisionamiento o escalado automático aparte.

### 3. Recursos y estado de salud

Combina este fragmento con el Deployment y contenedor **existentes**, tras confirmar el nombre del contenedor y el endpoint de salud real. Conserva su imagen, selectores y etiquetas reales:

```yaml
spec:
  template:
    spec:
      containers:
      - name: reviews
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /health
            port: 9080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
```

Las solicitudes y límites de recursos y las sondas son parámetros de ajuste, no una garantía de caudal medido. La preparación, el arranque y el drenaje afectan cuándo se puede usar la capacidad. La sonda de liveness no debe reiniciar un proceso sano solo porque una dependencia posterior no esté disponible.

### 4. Varios clústeres y regiones

Usa un escalador en cada clúster de destino con un origen de datos local al clúster y verificado, o etiquetas de clúster explícitas que existan de verdad en un almacén federado. Con métricas del reporter de destino locales al clúster, este ejemplo cuenta toda la demanda local de backend:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-local-demand
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 3
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: local-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Aplica cada configuración en el contexto de clúster previsto. Las etiquetas de metadatos como `region` no hacen que un ScaledObject controle un clúster remoto. `source_cluster` describe el origen, no la capacidad de destino que se debe escalar; multiplicar tráfico ya filtrado por 0.6/0.4 no implementa una división global del tráfico.

Los patrones de nombres de Service como `*-us-*` no demuestran la geografía del cliente, y `destination_region` no es una etiqueta predeterminada garantizada de Istio. Los SLO regionales requieren telemetría y capacidad de carga verificadas, no nombres de países supuestos en las etiquetas de servicios.

### 5. Cargas de pagos y colas

Una carga de pagos puede empezar con demanda calibrada y límites prudentes, mientras la latencia y los errores siguen siendo indicadores de calidad:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: payment-capacity-example
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-service
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 5
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 600
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="payment-service",destination_workload_namespace="production"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 5
    behavior: currentReplicasIfHigher
```

El objetivo de 100 RPS y los límites son ilustrativos. Confirma la causa del cuello de botella, la idempotencia, los límites de dependencias posteriores y el comportamiento ante fallos representativo antes de añadir disparadores basados en proporciones.

En una carga de trabajo que procesa colas, la cola sigue siendo visible cuando las réplicas de workers son 0:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: data-processor-queue
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-processor
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-sqs-queue
    name: backlog
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/data-processing-queue
      queueLength: '10'
      activationQueueLength: '0'
      scaleOnInFlight: 'true'
      scaleOnDelayed: 'false'
      awsRegion: us-west-2
```

Sustituye la cuenta y la URL de cola del ejemplo y configura la identidad indicada. `queueLength: "10"` significa el trabajo pendiente objetivo por réplica, no un umbral de activación de diez. La activación usa de forma predeterminada una cola con mensajes pendientes, con el umbral de activación explícitamente en cero. El ejemplo cuenta los mensajes visibles y los que están en curso, y excluye los retrasados; alinea esto con la concurrencia de procesamiento, el tiempo de visibilidad y el comportamiento de apagado.

La latencia HTTP de Istio no equivale automáticamente al tiempo de procesamiento de trabajos de SQS. Instrumenta por separado el procesamiento de negocio en vez de añadir al worker en cero un disparador de latencia de Pods que no estará disponible.

### 6. Supervisión

Expón y recopila las métricas del **operador** para conocer la salud de los escaladores. Las métricas del adaptador no incluyen todos los contadores del operador de KEDA. La etiqueta de métrica `namespace` de KEDA identifica el espacio de nombres del recurso escalado; no la sustituyas por el espacio de nombres del Pod exportador.

Este es un fragmento de configuración de scrapeo para combinar con la configuración de Prometheus existente, junto con RBAC de descubrimiento limitado por espacio de nombres para EndpointSlices, Services y Pods:

```yaml
scrape_configs:
- job_name: keda-components
  kubernetes_sd_configs:
  - role: endpointslice
    namespaces:
      names:
      - keda
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_service_name
    regex: keda-operator|keda-operator-metrics-apiserver
    action: keep
  - source_labels:
    - __meta_kubernetes_endpointslice_port_name
    regex: metrics
    action: keep
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: exporter_namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: exporter_pod
```

Descubre cada endpoint en vez de alternar entre Pods del operador de alta disponibilidad mediante un Service balanceado. Confirma los nombres y puertos reales del Service, las etiquetas de destino, el acceso TLS/malla y los resultados del scrapeo. Con Prometheus Operator, usa ServiceMonitors equivalentes con los selectores correspondientes en vez de sobrescribir su ConfigMap generado.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: keda-scaling-alerts
  namespace: keda
spec:
  groups:
  - name: keda-scaling
    rules:
    - alert: KEDAMaxReplicasReached
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        ) >= on(namespace, horizontalpodautoscaler)
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_spec_max_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        )
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: KEDA-managed HPA is at its configured maximum
    - alert: KEDAScalerErrors
      expr: sum by (namespace, scaledObject) (increase(keda_scaler_detail_errors_total[5m])) > 0
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Scaler retrieval errors observed; inspect source/identity and fallback
    - alert: KEDAReplicaCountChurn
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         changes(kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}[10m])
        ) > 6
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Frequent observed replica-count changes; inspect demand, rollout and stabilization
```

PrometheusRule necesita un selector de reglas del Operator y un espacio de nombres coincidentes. Los filtros HPA usan el prefijo de nombre predeterminado de KEDA; ajústalos si los nombres de HPA son personalizados. `keda_scaler_detail_errors_total` es el contador de errores publicado; `keda_scaler_active` es un indicador y no se debe pasar a `rate()` para medir oscilaciones de réplicas.

Los cambios en el recuento de réplicas pueden reflejar demanda o despliegues, no necesariamente oscilaciones perjudiciales. Estas alertas sirven para investigar; no demuestran que el escalado haya fallado ni que haya suficiente capacidad lista.

## Solución de problemas {#troubleshooting}

```bash
kubectl get scaledobject reviews-rps-scaler -n default -o yaml
kubectl describe hpa keda-hpa-reviews-rps-scaler -n default
kubectl logs -n keda deployment/keda-operator
kubectl get apiservice v1beta1.external.metrics.k8s.io
kubectl get pods -n default -o wide

# Local query inspection; use a second terminal while port-forward is active.
kubectl port-forward -n istio-system svc/prometheus 9090:9090
```

```bash
promtool query instant http://127.0.0.1:9090 'sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))'
```

Un reenvío de puerto local no demuestra la conectividad del Pod de KEDA ni que tenga credenciales. Comprueba los errores del proveedor, DNS, TLS/política de malla, existencia y etiquetas de la métrica y disponibilidad de la API agregada desde la ruta del componente real.

Si el escalado es lento, inspecciona la antigüedad del origen, la ventana de consulta, la sincronización y el comportamiento de HPA, la planificación, las descargas de imágenes y la preparación antes de reducir pollingInterval. Los umbrales de activación no aceleran el escalado habitual de 1→N cuando se usa un mínimo positivo. Si el recuento es inestable, examina la respuesta medida de capacidad y los límites de velocidad y estabilización de HPA; cooldownPeriod no es el control general de reducción de HPA.

Para CloudWatch, inspecciona las marcas de tiempo devueltas, todas las dimensiones, la estadística y unidad, la ventana de recopilación, el desfase y los permisos IAM. Un umbral mayor en una segunda métrica no la convierte en respaldo pasivo.

## Referencia: instalación de KEDA {#reference-keda-installation}

### Versión fijada del chart y compatibilidad real

El requisito de despliegue publicado para KEDA 2.20 es Kubernetes 1.30 o posterior, mientras que los metadatos del chart indican un mínimo más permisivo de 1.23. Que Helm acepte una versión no demuestra que tenga soporte en ejecución. Usa la intersección con las versiones 1.32–1.37 admitidas por Istio 1.31 y las versiones soportadas por la plataforma administrada.

Para una instalación nueva o una actualización revisada que conserve los valores existentes, usa estos valores. Antes de actualizar, revisa también los cambios de la versión y el procedimiento de propiedad o migración de las CRD:

```yaml
operator:
  replicaCount: 2
prometheus:
  operator:
    enabled: true
  metricServer:
    enabled: true
    port: 9022
```

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore
helm upgrade --install keda kedacore/keda --version 2.20.2   --namespace keda --create-namespace --values keda-values.yaml
kubectl get deployments,services,pods -n keda
```

`operator.replicaCount: 2` y la anulación del puerto 9022 del adaptador de métricas son valores válidos del chart; 9022 reemplaza explícitamente el puerto 8080 predeterminado del chart. Esto también habilita las métricas del operador en 8080. Tener dos réplicas del operador no hace que el adaptador de métricas, el webhook ni toda la ruta de escalado tengan alta disponibilidad por sí solos.

Si se inyectan los componentes en Istio, KEDA documenta esta exclusión opcional de puertos como solución para sus propios protocolos internos protegidos por TLS:

```yaml
podAnnotations:
  keda:
    traffic.sidecar.istio.io/excludeInboundPorts: '9666'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9443,6443
  metricsAdapter:
    traffic.sidecar.istio.io/excludeInboundPorts: '6443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,9443
  webhooks:
    traffic.sidecar.istio.io/excludeInboundPorts: '9443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,6443
```

Verifica los puertos y la configuración de inyección reales antes de combinar los valores. KEDA conserva su TLS nativo; la autorización de Istio no cubre el tráfico excluido. Esto no autoriza a desactivar TLS de forma global. Prueba la agregación de la API, la admisión, la conectividad operador↔adaptador y Prometheus.

### Identidad de lectura de AWS

Crea o revisa el rol de IAM y su confianza OIDC de EKS fuera de este ejemplo, limitado al ServiceAccount real del operador. Aplica los valores Helm correspondientes sin sobrescribir a ciegas un ServiceAccount existente:

```yaml
podIdentity:
  aws:
    irsa:
      enabled: true
      roleArn: arn:aws:iam::123456789012:role/KedaMetricsReader
```

Para el escalador de CloudWatch mostrado, la implementación publicada llama a GetMetricData:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-west-2"
        }
      }
    }
  ]
}
```

Este permiso permite leer métricas de la región; no limita por espacio de nombres de métrica. `cloudwatch:namespace` en la política AWS del ejemplo limita la **publicación mediante PutMetricData**, no esta consulta. La API PromQL de CloudWatch tiene requisitos IAM distintos; no los deduzcas a partir de este escalador.

Si se usa el ejemplo de SQS, el operador también necesita permiso para leer atributos de la cola concreta:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-west-2:123456789012:data-processing-queue"
    }
  ]
}
```

El worker de la cola necesita sus propios permisos de recepción, eliminación y visibilidad, según corresponda; el rol de lectura del escalador no se los concede. Limita quién puede crear o cambiar ScaledObjects y TriggerAuthentications mediante las identidades del operador.

### Publicación opcional mediante CloudWatch EMF

Este ejemplo usa **Collector Contrib upstream 0.158.0 junto con Operator 0.158.0**, de acuerdo con la recomendación de versión menor del operador. Operator 0.158 admite Kubernetes 1.25–1.36. El operador no actualiza automáticamente una imagen personalizada. ADOT es una alternativa solo tras verificar sus componentes y configuración; no se afirma que los comandos siguientes se hayan probado con una imagen ADOT no especificada.

Primero, carga este archivo de reglas de grabación en el Prometheus existente (o en un PrometheusRule equivalente con las etiquetas de selección adecuadas):

```yaml
groups:
- name: istio-scaling-export
  interval: 30s
  rules:
  - record: istio_scaling_requests_per_second
    expr: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
  - record: istio_scaling_p95_milliseconds
    expr: |-
      (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
        and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
      or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
```

Solo se exporta la carga mostrada. Son indicadores RPS ya calculados y p95 de una ventana móvil; no son contadores acumulados de solicitudes sin procesar ni permiten reconstruir la distribución de latencia original.

Después, con el Operator/CRD compatible y un rol de publicación y grupo de registros existentes y revisados:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-metrics-publisher
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/IstioMetricsPublisher
---
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: istio-scaling
  namespace: istio-system
spec:
  mode: deployment
  replicas: 1
  serviceAccount: istio-metrics-publisher
  image: otel/opentelemetry-collector-contrib:0.158.0
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      memory: 512Mi
  config:
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      prometheus:
        config:
          scrape_configs:
          - job_name: istio-scaling-federate
            scrape_interval: 60s
            honor_labels: true
            metrics_path: /federate
            params:
              match[]:
              - '{__name__=~"istio_scaling_requests_per_second|istio_scaling_p95_milliseconds"}'
            static_configs:
            - targets:
              - prometheus.istio-system.svc.cluster.local:9090
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 256
        spike_limit_mib: 64
      metricstransform:
        transforms:
        - include: istio_scaling_requests_per_second
          action: update
          new_name: IstioRequestsPerSecond
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
        - include: istio_scaling_p95_milliseconds
          action: update
          new_name: IstioP95LatencyMilliseconds
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
      batch:
        timeout: 60s
        send_batch_size: 256
    exporters:
      awsemf:
        namespace: IstioScaling
        region: us-west-2
        log_group_name: /aws/otel/istio-scaling
        log_stream_name: eks-demo
        dimension_rollup_option: NoDimensionRollup
        metric_declarations:
        - dimensions:
          - - ClusterName
            - destination_workload
            - destination_workload_namespace
          metric_name_selectors:
          - ^IstioRequestsPerSecond$
          - ^IstioP95LatencyMilliseconds$
        metric_descriptors:
        - metric_name: IstioRequestsPerSecond
          unit: Count/Second
          overwrite: true
        - metric_name: IstioP95LatencyMilliseconds
          unit: Milliseconds
          overwrite: true
    service:
      extensions:
      - health_check
      pipelines:
        metrics:
          receivers:
          - prometheus
          processors:
          - memory_limiter
          - metricstransform
          - batch
          exporters:
          - awsemf
```

La configuración `v1beta1` es un objeto. La API anterior `v1alpha1` sigue sirviéndose en esta versión del operador, por lo que no se debe describir como eliminada; este ejemplo usa el formato actual y una imagen Contrib explícita con los componentes necesarios.

El Collector solo federa las dos métricas de grabación indicadas, conserva las dimensiones de la carga, añade el ClusterName configurado y envía EMF a un flujo de registros fijo. Mantén alineados el espacio de nombres, los nombres y unidades de las métricas y las tres dimensiones de los escaladores CloudWatch. El exportador EMF descarta NaN/Inf; la expresión de grabación distingue el 0 inactivo conocido de la telemetría no disponible.

En este ejemplo se usa una réplica publicadora para evitar consultas duplicadas; no es un diseño de alta disponibilidad. Configura la autenticación real de Prometheus y el acceso por malla, la identidad del publicador, la retención del grupo de registros y los límites de recursos. Esta auditoría no desplegó ni probó contra AWS el operador/controlador ni la entrega EMF.

El grupo de registros del publicador debe existir previamente y tener una retención administrada por la plataforma. El rol del ejemplo necesita crear flujos y escribir dentro de ese grupo:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/otel/istio-scaling:log-stream:eks-demo"
    }
  ]
}
```

EMF pasa por CloudWatch Logs; `cloudwatch:PutMetricData` por sí solo no autoriza este exportador. Una condición del espacio de nombres en PutMetricData no aplica el espacio de nombres configurado para las llamadas de Logs. La ingesta y el almacenamiento de registros y las métricas personalizadas generadas tienen costos distintos; controla la cardinalidad y la retención en vez de suponer que reducir réplicas reduce la factura.

## Referencias

- [Especificación de ScaledObject de KEDA](https://keda.sh/docs/2.20/reference/scaledobject-spec/)
- [Activación y escalado](https://keda.sh/docs/2.20/concepts/scaling-deployments/)
- [Escalador de Prometheus](https://keda.sh/docs/2.20/scalers/prometheus/)
- [Escalador de CloudWatch](https://keda.sh/docs/2.20/scalers/aws-cloudwatch/)
- [Escalador de SQS](https://keda.sh/docs/2.20/scalers/aws-sqs/)
- [Escalador Cron](https://keda.sh/docs/2.20/scalers/cron/)
- [Proveedor IRSA de AWS](https://keda.sh/docs/2.20/authentication-providers/aws/)
- [Métricas de KEDA](https://keda.sh/docs/2.20/integrations/prometheus/)
- [KEDA con Istio](https://keda.sh/docs/2.20/integrations/istio-integration/)
- [Requisitos de despliegue de KEDA](https://keda.sh/docs/2.20/deploy/)
- [HPA de Kubernetes](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Métricas estándar de Istio](https://istio.io/latest/docs/reference/config/metrics/)
- [Compatibilidad de Operator 0.158](https://raw.githubusercontent.com/open-telemetry/opentelemetry-operator/v0.158.0/docs/getting-started/compatibility.md)
- [Exportador EMF de Collector 0.158](https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector-contrib/v0.158.0/exporter/awsemfexporter/README.md)
- [CloudWatch EMF](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- [Condiciones de namespace de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/iam-cw-condition-keys-namespace.html)
- [Observabilidad](../observability/README.md)
- [Resiliencia](../resilience/README.md)
- [Gestión del tráfico](../traffic-management/README.md)

Antes de usarlo en producción, valida la semántica de las señales, las etiquetas y antigüedad reales de las métricas, el comportamiento con datos inactivos o ausentes, la existencia de un solo propietario del escalado, la capacidad, la respuesta ante fallos representativos y la recuperación. Los umbrales, mínimos de réplicas y tiempos del ejemplo son valores iniciales para esas pruebas.
