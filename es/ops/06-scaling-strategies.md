# Estrategias de escalado

> **Validación en producción**: Antes de adoptar Spot, usa [Experimentos de producción de EKS Spot y evaluación de resultados](./17-spot-production-experiments.md) para verificar la reclamación de capacidad, la alternativa de respaldo, la corrección y el costo. Los ejemplos de configuración y los ahorros proyectados no son mediciones.

> **Base de revisión**: Prometheus Adapter 0.12.0 / chart 5.3.0, KEDA 2.21.0, VPA 1.8.0 / chart oficial 0.14.0, Goldilocks 4.16.2 / chart 11.2.0\
> **Última revisión**: 16 de octubre de 2026. Se comprobaron los charts versionados, las CRD, la API OpenAPI de Kubernetes y el renderizado local. No se realizaron instalaciones en vivo, pruebas de carga, accesos a SQS o bases de datos ni redimensionamientos de Pods.

< [Anterior: Automatización de GitOps](05-gitops-automation.md) | [Contenido](README.md) | [Siguiente: Alertas operativas](07-observability-alerts.md) >

Separa el HPA con métricas personalizadas, KEDA, VPA y la ubicación en nodos Spot. **Un solo autoscaler debe ser propietario del recuento de réplicas de una carga de trabajo.** El HPA y los ScaledObject de RPS y de Cron que apuntan a `podinfo` son alternativas; no los apliques a la vez.

La documentación oficial de implementación de KEDA 2.21 indica un intervalo probado de Kubernetes 1.34–1.36. Comprueba ese intervalo y valida por separado las distribuciones más recientes. Las comprobaciones de objetos nativos de esta guía usaron la API OpenAPI de Kubernetes 1.36.2; no constituyen una prueba de compatibilidad en vivo.

## 1. HPA y métricas personalizadas

![Valores de métricas recopilados, respuestas a consultas del adaptador, agregación de API y actualización de la escala del Deployment por el controlador HPA.](../.gitbook/assets/en-ops-06-scaling-strategies-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-06-scaling-strategies-0.html)

| API | Proveedor en este ejemplo | Responsabilidad |
|---|---|---|
| `metrics.k8s.io` | metrics-server | Métricas de recursos de CPU y memoria |
| `custom.metrics.k8s.io` | Prometheus Adapter | Métricas asociadas a objetos de Kubernetes, como los Pods |
| `external.metrics.k8s.io` | Servidor de API de métricas de KEDA si se elige KEDA | Métricas de eventos externos |

Prometheus Adapter también puede ofrecer las API de recursos y externas, pero este ejemplo solo habilita métricas personalizadas. Evita que varios componentes sean propietarios de la misma APIService. Instalar únicamente CloudWatch Exporter no crea una API de métricas externas de Kubernetes.

### Requisitos previos y aplicación de demostración

Prepara metrics-server, Prometheus Operator/Prometheus y cert-manager. Sustituye la dirección del Service de Prometheus en los valores por el endpoint real. Sus selectores `serviceMonitorSelector` y `serviceMonitorNamespaceSelector` deben seleccionar el ServiceMonitor de `scaling-demo`. Comprueba que las series recopiladas tengan las etiquetas de destino `namespace`, `pod` y `service` esperadas.

Se verificó el digest indicado a continuación para la imagen pública multiplataforma Podinfo 6.15.0. Al adaptar el ejemplo, sustitúyela por una aplicación aprobada que implemente los contratos reales de métricas, sondas y apagado.

```yaml
# fixtures/application.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: scaling-demo
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: podinfo
  template:
    metadata:
      labels:
        app: podinfo
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 45
      containers:
        - name: podinfo
          image: ghcr.io/stefanprodan/podinfo@sha256:ec73780a8425f59ea49f5bc8cdff0d598805a224fbaa1f86c67a244f250fa9da
          ports:
            - name: http
              containerPort: 9898
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: "1"
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
---
apiVersion: v1
kind: Service
metadata:
  name: podinfo
  namespace: scaling-demo
  labels:
    app: podinfo
spec:
  selector:
    app: podinfo
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  selector:
    matchLabels:
      app: podinfo
  namespaceSelector:
    matchNames: [scaling-demo]
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

`http_requests_total` de Podinfo es un contador de solicitudes HTTP. Puede incluir solicitudes operativas, como las comprobaciones de estado; no supongas que mide únicamente el tráfico de negocio de producción. No agregues una segunda ruta de scraping basada en anotaciones que vuelva a recopilar el mismo destino.

### Configuración del adaptador

```yaml
# fixtures/adapter-values.yaml
replicas: 2
prometheus:
  url: http://prometheus.monitoring.svc
  port: 9090
certManager:
  enabled: true
podDisruptionBudget:
  enabled: true
  minAvailable: 1
  maxUnavailable: null
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
rules:
  default: false
  external: []
  custom:
    - seriesQuery: 'http_requests_total{namespace="scaling-demo",pod!=""}'
      resources:
        overrides:
          namespace:
            resource: namespace
          pod:
            resource: pod
      name:
        matches: "^http_requests_total$"
        as: http_requests_per_second
      metricsQuery: 'sum(rate(http_requests_total{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install prometheus-adapter prometheus-community/prometheus-adapter \
  --version 5.3.0 --namespace monitoring --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values adapter-values.yaml

kubectl --context "$TARGET_CONTEXT" get --raw \
  /apis/custom.metrics.k8s.io/v1beta1
```

cert-manager administra el certificado y la inyección de la CA en APIService. No deduzcas que el transporte está cifrado únicamente por el nombre de una opción de Helm, como `tls.enable=false`; inspecciona la APIService renderizada, el certificado y la configuración de verificación. Como aquí no hay reglas externas, no se espera una API externa propiedad del adaptador.

`rules.custom` de Helm y la configuración sin procesar del servidor del adaptador tienen estructuras distintas. Crear un ConfigMap arbitrario no hace que un chart existente lo lea. Mantén un único propietario de la configuración.

### HPA con RPS por Pod y CPU

```yaml
# fixtures/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
        - type: Pods
          value: 2
          periodSeconds: 60
      selectPolicy: Min
```

Varias métricas no constituyen una lista de prioridades ni un simple «respaldo de CPU». HPA calcula recomendaciones y selecciona el **mayor requisito de réplicas**. Una métrica no disponible puede impedir reducir la escala; una métrica válida que solicite aumentarla puede permitir el incremento.

Si todas las métricas y los Pods de destino están listos, la proporción básica es `ceil(currentReplicas × currentMetric / targetMetric)`. Cuatro Pods con un promedio de 250 RPS y un objetivo de 100 producen un objetivo calculado de diez. Los mínimos y máximos, los Pods no listos, las métricas ausentes, la tolerancia y el comportamiento pueden cambiar la decisión real.

| Configuración | Significado |
|---|---|
| Estabilización al aumentar la escala | Considera recomendaciones recientes más bajas para amortiguar aumentos rápidos |
| Estabilización al reducir la escala | Considera recomendaciones recientes más altas para amortiguar reducciones rápidas |
| `periodSeconds` | Ventana retrospectiva para el cambio permitido |
| `selectPolicy: Max` | Política que permite un cambio mayor |
| `Min` al reducir la escala | Política que permite menos eliminaciones |

La estabilización no inicia un período fijo de espera nuevo con cada observación. `periodSeconds` admite valores de 1 a 1.800 y la estabilización, de 0 a 3.600; una política de 300 segundos es válida. Un aumento del 500 % permite **un 500 % adicional**, hasta seis veces el recuento actual.

Con veinte réplicas actuales, las políticas Percent 10% y Pods 2 de este ejemplo de reducción permiten eliminar como máximo dos Pods cada una. Siguen aplicándose el historial, las recomendaciones y otros límites; esto no garantiza que haya dieciocho Pods listos en un instante determinado.

El valor general `minReplicas: 0` de HPA depende de la versión de Kubernetes, `HPAScaleToZero` y los requisitos previos de las métricas. Este ejemplo usa tres; el escalado de colas externas a cero se muestra por separado con KEDA. Que la API de métricas responda correctamente no elimina las demoras de descarga de imágenes, capacidad de nodos o inicio de la aplicación.

### Métricas externas e inspección

La profundidad de cola es una métrica de tipo gauge. Cambiar el nombre de un contador acumulativo `*_total` no lo convierte en el backlog actual. Para una cola global con un objetivo de trabajo por Pod, `AverageValue` suele ser el tipo de objetivo adecuado; no supongas que `Value` se calcula igual.

La integración con CloudWatch requiere un scaler directo de KEDA o la ruta completa Exporter → Prometheus → regla externa de Adapter. Alinea los nombres y etiquetas reales del exporter con HPA y evita conflictos de propiedad de APIService. No agregues una dimensión TargetGroup arbitraria a `AWS/ApplicationELB RequestCount`. Consulta los ejemplos de CloudWatch en la [guía de KEDA revisada](../autoscaling/01-keda.md).

```bash
kubectl --context "$TARGET_CONTEXT" get --raw \
  '/apis/custom.metrics.k8s.io/v1beta1/namespaces/scaling-demo/pods/*/http_requests_per_second'
kubectl --context "$TARGET_CONTEXT" describe hpa podinfo -n scaling-demo
kubectl --context "$TARGET_CONTEXT" get deployment,pods -n scaling-demo
```

Ejecuta pruebas de carga acotadas en un entorno de pruebas separado, en lugar de usar una imagen BusyBox obsoleta con un bucle sin límite. Alinea la propiedad de GitOps sobre `replicas` del Deployment con la del autoscaler.

## 2. Escalado basado en eventos con KEDA

El operador de KEDA administra los ScaledObject/HPA y las transiciones de activación y de escala a cero. HPA participa en el escalado horizontal por encima de cero. ScaledJob crea Jobs por separado; HPA no cambia el campo de réplicas de un Job.

### Instalación e identidad de AWS

Sigue la [guía de KEDA](../autoscaling/01-keda.md) para conocer la instalación general, la compatibilidad y las redes. El ejemplo de AWS usa explícitamente **IRSA en el operador de KEDA**. Primero prepara el proveedor OIDC del clúster, la confianza exacta para el namespace y la ServiceAccount, y el rol con acceso de lectura a la cola.

```yaml
# fixtures/keda-values.yaml
# This example explicitly uses IRSA on the KEDA operator.
# Prepare the cluster OIDC provider, scoped trust and queue-read role first.
podIdentity:
  aws:
    irsa:
      enabled: true
      roleArn: arn:aws:iam::123456789012:role/KedaQueueReadRole
```

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm upgrade --install keda kedacore/keda \
  --version 2.21.0 --namespace keda --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values keda-values.yaml
```

Sustituye el ARN del rol por el rol aprobado. La opción antigua `provider: aws-eks` no significa EKS Pod Identity. IRSA y Pod Identity son configuraciones distintas; cualquier otro método elegido debe contar con la cadena de credenciales del SDK del operador, la asociación y la confianza correspondientes.

### ScaledObject de RPS

Elige esta **alternativa** después de quitar la propiedad conflictiva de HPA o de seguir un procedimiento de migración compatible.

```yaml
# fixtures/keda-rps.yaml
# Alternative to hpa.yaml. Do not let both own podinfo's replica count.
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  minReplicaCount: 3
  maxReplicaCount: 20
  pollingInterval: 15
  cooldownPeriod: 300
  fallback:
    failureThreshold: 3
    replicas: 5
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
  triggers:
    - type: prometheus
      name: requests
      metricType: AverageValue
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(rate(http_requests_total{namespace="scaling-demo",service="podinfo"}[2m]))
        threshold: "100"
        activationThreshold: "0"
        ignoreNullValues: "false"
    - type: cpu
      metricType: Utilization
      metadata:
        value: "70"
```

Un umbral `AverageValue` de 100 es un **objetivo de 100 RPS por Pod**, no un umbral incondicional para aumentar la escala según el tráfico total. Por ejemplo, un total de 1.000 RPS implica diez réplicas antes de aplicar otros límites. Los umbrales de activación controlan la activación y son distintos de los objetivos de HPA.

`ignoreNullValues=false` evita tratar silenciosamente resultados de consulta ausentes como si fueran una carga cero saludable. Devuelve un único valor agregado y gestiona deliberadamente los errores, NaN y el tráfico cero. El fallback responde a fallos repetidos de las métricas compatibles; no recupera todas las interrupciones del proveedor de métricas, HPA o nodos.

El ejemplo HTTP conserva tres Pods. Si se eliminan todos y la única señal de actividad procede de esos Pods, es posible que las nuevas solicitudes HTTP no tengan una ruta de observación y activación. Para escalar a cero se necesita una cola externa u otro mecanismo de activación.

### Cola de SQS

Prepara el Deployment real `sqs-worker` y sus propios permisos de consumidor de la cola. Las lecturas de atributos de la cola que hace KEDA son distintas de los permisos del worker para recibir, eliminar o cambiar la visibilidad de mensajes.

```yaml
# fixtures/keda-sqs.yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws
  namespace: scaling-demo
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-worker
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-worker
  minReplicaCount: 0
  maxReplicaCount: 50
  pollingInterval: 15
  cooldownPeriod: 60
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: keda-aws
      metadata:
        queueURL: https://sqs.ap-northeast-2.amazonaws.com/REPLACE_ACCOUNT/my-queue
        queueLength: "10"
        activationQueueLength: "0"
        scaleOnInFlight: "true"
        scaleOnDelayed: "false"
        awsRegion: ap-northeast-2
```

`activationQueueLength: "0"` activa el escalado cuando la cantidad supera cero. Un valor de `"1"` significa **más de uno**, no uno o más. Revisa la gestión de mensajes en vuelo o demorados y los tiempos de espera de visibilidad. El backlog de una DLQ no se incluye automáticamente.

El intervalo de sondeo determina las comprobaciones de KEDA, no el período de sincronización de HPA ni cuánto tarda en iniciarse un Pod. Escalar de uno a varios Pods es distinto de pasar a cero; `cooldownPeriod` no es una espera universal antes de reducir la escala. Los trabajos prolongados requieren una gestión deliberada de la terminación, los reintentos, la deduplicación y la visibilidad.

### Cola de trabajo de PostgreSQL

Escalar una aplicación porque aumentaron las conexiones a la base de datos puede empeorar la presión sobre ellas. Este ejemplo usa trabajo pendiente que el worker realmente consume.

```yaml
# fixtures/keda-postgresql.yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: queue-database
  namespace: scaling-demo
spec:
  secretTargetRef:
    - parameter: connection
      name: queue-database
      key: connection
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: database-worker
  namespace: scaling-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: database-worker
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: postgresql
      authenticationRef:
        name: queue-database
      metricType: AverageValue
      metadata:
        query: SELECT count(*) FROM public.job_queue WHERE status = 'pending'
        targetQueryValue: "50"
        activationTargetQueryValue: "0"
```

La clave `connection` del Secret `queue-database` debe contener un DSN válido. Configura la verificación del nombre de host y de la CA con `sslmode=verify-full` y las rutas de CA necesarias en el entorno del operador de KEDA. No guardes credenciales en Git. Concede a KEDA acceso de lectura a la tabla de cola por separado de los permisos de escritura del worker.

Devuelve un único valor numérico. Filtrar todos los trabajos pendientes con más de una hora puede ocultar el backlog. El worker sigue necesitando una asignación atómica, deduplicación y gestión del estado de finalización.

### Cron y varias métricas

```yaml
# fixtures/keda-cron.yaml
# Alternative to the preceding podinfo HPA/ScaledObject.
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  scaleTargetRef:
    name: podinfo
  minReplicaCount: 3
  maxReplicaCount: 50
  triggers:
    - type: cron
      metadata:
        timezone: Asia/Seoul
        start: "0 9 * * 1-5"
        end: "0 18 * * 1-5"
        desiredReplicas: "20"
    - type: cron
      metadata:
        timezone: Asia/Seoul
        start: "30 11 * * 1-5"
        end: "30 13 * * 1-5"
        desiredReplicas: "40"
    - type: prometheus
      metricType: AverageValue
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(rate(http_requests_total{namespace="scaling-demo",service="podinfo"}[2m]))
        threshold: "100"
        ignoreNullValues: "false"
```

Se comparan veinte réplicas durante el horario laboral y cuarenta durante la franja del almuerzo con la demanda determinada por métricas. Gana el mayor requisito activo; Cron y Prometheus no tienen prioridades arbitrarias. El mínimo fuera de esas franjas es tres. Al agregar horarios nocturnos o de fin de semana, prueba los límites y las superposiciones en la zona horaria configurada.

La versión actual de KEDA admite `advanced.scalingModifiers`. Es incorrecto describir las fórmulas como una función futura o afirmar que solo existe el comportamiento OR. Este ejemplo combina dos **métricas gauge de cola con las mismas unidades**, que consume un mismo worker:

```yaml
# fixtures/keda-composite.yaml
# Requires a worker that consumes both queues and the two named gauge series.
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: shared-queue-worker
  namespace: scaling-demo
spec:
  scaleTargetRef:
    name: shared-queue-worker
  minReplicaCount: 1
  maxReplicaCount: 30
  advanced:
    scalingModifiers:
      formula: queue_a + queue_b
      target: "50"
      activationTarget: "0"
      metricType: AverageValue
  triggers:
    - type: prometheus
      name: queue_a
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(queue_messages_pending{queue="a"})
        threshold: "50"
        ignoreNullValues: "false"
    - type: prometheus
      name: queue_b
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: sum(queue_messages_pending{queue="b"})
        threshold: "50"
        ignoreNullValues: "false"
```

Los nombres de los triggers deben poder usarse en la expresión, y la fórmula debe devolver una métrica numérica. No combines a la ligera triggers de recursos o unidades incompatibles. Para un comportamiento similar a AND, diseña un resultado numérico condicional y prueba el riesgo de inanición, la activación y la gestión de fallos.

### ScaledJob

Esta es una plantilla que necesita una imagen de worker real y la ServiceAccount `batch-worker`.

```yaml
# fixtures/keda-job.yaml
# Supply an actual bounded, idempotent SQS consumer image and worker identity.
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: batch-processor
  namespace: scaling-demo
spec:
  pollingInterval: 30
  minReplicaCount: 0
  maxReplicaCount: 20
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  scalingStrategy:
    strategy: default
  jobTargetRef:
    parallelism: 1
    completions: 1
    activeDeadlineSeconds: 600
    backoffLimit: 2
    template:
      spec:
        serviceAccountName: batch-worker
        restartPolicy: Never
        containers:
          - name: processor
            image: REPLACE_WITH_APPROVED_WORKER_IMAGE
            env:
              - name: SQS_QUEUE_URL
                value: https://sqs.ap-northeast-2.amazonaws.com/REPLACE_ACCOUNT/batch-queue
            resources:
              requests:
                cpu: 250m
                memory: 256Mi
  triggers:
    - type: aws-sqs-queue
      authenticationRef:
        name: keda-aws
      metadata:
        queueURL: https://sqs.ap-northeast-2.amazonaws.com/REPLACE_ACCOUNT/batch-queue
        queueLength: "1"
        awsRegion: ap-northeast-2
```

Los límites del historial son **recuentos**, no segundos. `queueLength: "1"` no vincula exactamente un mensaje concreto a un Job. El worker debe recibir, procesar y eliminar mensajes, y tolerar reintentos. Las estrategias default, accurate, custom y eager difieren en cómo influyen la cola y los Jobs en ejecución o pendientes en la creación de otros Jobs.

Un trigger Cron de ScaledJob puede crear Jobs repetidamente mientras su ventana esté activa. Para ejecutar «una vez al día», usa un CronJob de Kubernetes con `schedule`/`timeZone`, concurrencia y políticas de reintento deliberadas. No dejes activada accidentalmente la opción `autoscaling.keda.sh/paused-replicas` en un ejemplo de ajuste.

## 3. VPA y redimensionamiento en el lugar

VPA recomienda principalmente **solicitudes de recursos**. Los límites dependen de `controlledValues` y de las proporciones existentes; no calcula universalmente un límite óptimo independiente.

### Chart oficial y modo de recomendaciones

Usa el chart oficial de VPA 0.14.0 con VPA 1.8.0. No instales una segunda versión de VPA sobre una instalación existente; primero revisa la migración de CRD, RBAC y configuración. Lo siguiente usa cert-manager/cainjector para los certificados del webhook.

```yaml
# fixtures/vpa-values.yaml
admissionController:
  replicas: 2
  certGen:
    enabled: false
  certManager:
    enabled: true
    createSelfSignedIssuer:
      enabled: true
recommender:
  replicas: 2
updater:
  replicas: 2
  extraArgs:
    - --in-place-skip-disruption-budget=false
```

```bash
helm upgrade --install vpa \
  https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-chart-0.14.0/vertical-pod-autoscaler-0.14.0.tgz \
  --namespace vpa --create-namespace --kube-context "$TARGET_CONTEXT" \
  --values vpa-values.yaml
```

Este chart usa `replicas`; no mezcles la estructura `replicaCount` ni `extraArgs` de otro chart. Habilita la elección de líder para varias réplicas de recommender/updater. Aquí se deshabilita explícitamente omitir el presupuesto de interrupción. Añadir opciones no documentadas para el historial de Prometheus no crea automáticamente una canalización de historial funcional.

```yaml
# fixtures/vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: podinfo
        controlledResources: [cpu, memory]
        controlledValues: RequestsOnly
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: "1"
          memory: 512Mi
```

`Off` genera recomendaciones sin aplicarlas a los Pods. Comprueba las solicitudes y los límites, la cuota y la capacidad de los nodos antes de aplicar las recomendaciones. No instales varios VPA alternativos en el mismo Deployment.

| Modo | Comportamiento de VPA 1.8.0 |
|---|---|
| `Off` | Solo recomendaciones |
| `Initial` | Aplica los cambios al crear el Pod |
| `Recreate` | Aplica los cambios mediante la expulsión y recreación cuando sea necesario |
| `InPlaceOrRecreate` | Intenta actualizar en el lugar y, si falla, recurre a la recreación |
| `InPlace` | Reintenta la actualización en el lugar sin recurrir a la expulsión; requiere una feature gate independiente |
| `Auto` | Está obsoleto y actualmente equivale a Recreate; elige un modo explícito |

Comprueba Kubernetes 1.33+ y los demás requisitos previos para los modos en el lugar de VPA 1.8.0. La feature gate anterior de VPA `InPlaceOrRecreate` se eliminó en 1.7, pero `InPlace` necesita `--feature-gates=InPlace=true`. `minReplicas` es un requisito de elegibilidad para updater, no una garantía de que haya esa cantidad de Pods disponibles.

### Redimensionamiento de Kubernetes

El redimensionamiento de Pods en el lugar comenzó como alfa en 1.27, pasó a beta en 1.33 y es estable desde 1.35. Esto no significa que todo clúster 1.27+ ofrezca actualizaciones sin interrupciones de forma predeterminada. Comprueba los nodos y el runtime compatibles, la clase QoS y las políticas de redimensionamiento.

```yaml
# Container fragment; select the restart behavior required by the application.
resizePolicy:
  - resourceName: cpu
    restartPolicy: NotRequired
  - resourceName: memory
    restartPolicy: RestartContainer
```

Este parche cambia la solicitud de CPU del Pod de demostración. Confirma el nombre real del Pod antes de usar el subrecurso de redimensionamiento.

```json
{
  "spec": {
    "containers": [
      {
        "name": "podinfo",
        "resources": {
          "requests": {"cpu": "200m"},
          "limits": {"cpu": "1"}
        }
      }
    ]
  }
}
```

```bash
kubectl --context "$TARGET_CONTEXT" patch pod "$POD_NAME" -n scaling-demo \
  --subresource=resize --type=strategic --patch-file=resize-patch.json
kubectl --context "$TARGET_CONTEXT" get pod "$POD_NAME" -n scaling-demo -o json |
  jq '.status.conditions[]? | select(.type | startswith("PodResize"))'
```

Inspecciona las razones Deferred/Infeasible en `PodResizePending` y el estado `PodResizeInProgress`. No dependas únicamente del campo obsoleto `.status.resize`. Un Pod puede seguir existiendo mientras una política `RestartContainer` reinicia su contenedor. Los cambios de QoS, los contenedores init/efímeros no compatibles, las políticas de nodo y los sistemas operativos introducen otras limitaciones.

El redimensionamiento directo de un Pod no actualiza permanentemente la plantilla del Deployment. Persiste la configuración prevista mediante VPA o Git si quieres que las sustituciones la conserven.

### Goldilocks y coexistencia con HPA

```yaml
# fixtures/goldilocks-values.yaml
vpa:
  enabled: false
controller:
  enabled: true
dashboard:
  enabled: true
  service:
    type: ClusterIP
```

```bash
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm repo update
helm upgrade --install goldilocks fairwinds-stable/goldilocks \
  --version 11.2.0 --namespace goldilocks --create-namespace \
  --kube-context "$TARGET_CONTEXT" --values goldilocks-values.yaml
```

Reutiliza la instalación existente de VPA y mantén el dashboard en ClusterIP. Usa una ruta interna autenticada o un reenvío de puertos a localhost para revisarlo. Habilitar Goldilocks en un namespace puede crear VPA; evita conflictos de propiedad con un objetivo VPA existente administrado manualmente.

HPA por utilización de CPU y los cambios de solicitudes de CPU de VPA interactúan a través del denominador de utilización. `Initial` también cambia las solicitudes de los Pods nuevos. Empieza con recomendaciones o usa métricas de carga, como RPS/backlog, para HPA mientras VPA gestiona el dimensionamiento, y verifica su comportamiento conjunto. HPA de CPU con VPA que solo gestiona memoria también puede afectar a los reinicios y la programación.

## 4. Costo de eliminación de Pods

La anotación es una **preferencia de mejor esfuerzo para reducir la escala de ReplicaSet**. No es una prioridad global para interrupciones de nodos, expulsiones, Jobs, StatefulSets ni proporciones de réplicas entre distintos Deployments.

```yaml
metadata:
  annotations:
    controller.kubernetes.io/pod-deletion-cost: "100"
```

El orden actual de ReplicaSet compara primero la asignación, la fase y disponibilidad del Pod; después compara el costo de eliminación. Luego considera la densidad de réplicas en el nodo, el tiempo que lleva listo, los recuentos de reinicios y las fechas de creación. Un costo menor no siempre coloca un Pod por delante de todos los demás candidatos.

Los valores usan el intervalo de enteros con signo de 32 bits y cero es el valor predeterminado. Comprueba quién administra los Pods y su estado actual dentro del **mismo ReplicaSet** antes de cambiar las preferencias:

```bash
kubectl --context "$TARGET_CONTEXT" get pod "$POD_A" "$POD_B" \
  -n scaling-demo -o json |
  jq '.items[] | {name:.metadata.name,node:.spec.nodeName,
    owners:.metadata.ownerReferences,phase:.status.phase}'

kubectl --context "$TARGET_CONTEXT" annotate pod "$POD_A" -n scaling-demo \
  controller.kubernetes.io/pod-deletion-cost=-100 --overwrite
kubectl --context "$TARGET_CONTEXT" annotate pod "$POD_B" -n scaling-demo \
  controller.kubernetes.io/pod-deletion-cost=100 --overwrite
```

El mismo costo en la plantilla de todos los Pods no permite distinguirlos. Por lo general, un webhook de admisión CREATE no puede saber en qué nodo se asignará el Pod. `preStop` se ejecuta después de que se elija el Pod para su eliminación, así que llega demasiado tarde para influir en esa elección.

Un controlador dinámico real necesita gestionar los Pods después de su vinculación, comprobar con precisión la propiedad del controlador y su UID, tener permisos de parcheo limitados, gestionar anotaciones nulas, reconectar watches y tratar los errores de API. Que un Pod esté listo no demuestra que el trabajo haya finalizado, y anotar el progreso de un Job no hace que su terminación siga las reglas de costo de eliminación de ReplicaSet.

## 5. Ubicación en Spot y terminación

Lo siguiente supone un clúster de demostración de Auto Mode con un NodeClass `default` existente. Ambos pools ofrecen la misma etiqueta de carga de trabajo, por lo que los dos tipos de capacidad pueden seleccionarse.

```yaml
# fixtures/nodepools.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-spot
spec:
  weight: 100
  template:
    metadata:
      labels:
        workload-type: web
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: [spot]
        - key: kubernetes.io/arch
          operator: In
          values: [amd64, arm64]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m7i.large, m7i.xlarge, m7g.large, m7g.xlarge, c7i.large, c7g.large]
  limits:
    cpu: "100"
    memory: 200Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m
    budgets:
      - nodes: "10%"
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-ondemand
spec:
  weight: 10
  template:
    metadata:
      labels:
        workload-type: web
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand]
        - key: kubernetes.io/arch
          operator: In
          values: [amd64, arm64]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [m7i.large, m7i.xlarge, m7g.large, m7g.xlarge, c7i.large, c7g.large]
  limits:
    cpu: "50"
    memory: 100Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
```

Un peso mayor es una preferencia de aprovisionamiento. No garantiza que On-Demand se use únicamente después de agotar toda la capacidad Spot, ni un porcentaje fijo de Spot ni capacidad de respaldo reservada con antelación. Los nodos existentes, las restricciones de programación, la disponibilidad por zona y tipo, las cuotas y la capacidad afectan el resultado.

Auto Mode/Karpenter usa `karpenter.sh/capacity-type` con `spot`/`on-demand`. Distingue esa etiqueta de `eks.amazonaws.com/capacityType` de los grupos de nodos administrados y de las taints personalizadas. `kubernetes.io/capacity-type` no es la etiqueta de este ejemplo.

### Parche de ubicación y PDB

```yaml
# fixtures/placement-patch.yaml
# Kustomize strategic-merge patch for application.yaml; not standalone.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  template:
    spec:
      nodeSelector:
        workload-type: web
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 80
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: [spot]
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: podinfo
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: podinfo
```

```yaml
# fixtures/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: podinfo
  namespace: scaling-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: podinfo
```

```yaml
# fixtures/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - application.yaml
  - hpa.yaml
  - nodepools.yaml
  - pdb.yaml
patches:
  - path: placement-patch.yaml
```

Coloca los archivos juntos e inspecciona `kustomize build .`. El parche no es un Deployment independiente. `ScheduleAnyway` es flexible y `DoNotSchedule` sigue dependiendo de los dominios de topología elegibles. Las restricciones de distribución no crean una proporción arbitraria de 80/20 ni nodos de reserva.

Los PDB limitan las expulsiones voluntarias compatibles. No impiden que HPA/ReplicaSet reduzca el número de réplicas ni que se pierda realmente un nodo Spot. `minAvailable: 2` no garantiza que siempre haya dos Pods en ejecución.

### Interrupción y apagado ordenado

Evita añadir otro controlador de drenaje sobre la gestión de interrupciones que Auto Mode ya administra. Karpenter autoadministrado requiere configurar una cola de interrupciones/EventBridge y los permisos correspondientes. Usa Node Termination Handler solo si identificas claramente el modo de nodo y cumples todos los requisitos previos.

No interpretes la notificación Spot como garantía de que a la aplicación le queden 120 segundos. Ten en cuenta las excepciones de hibernación, las demoras de detección, drenaje y terminación, y el plazo real.

`terminationGracePeriodSeconds` pertenece a la **especificación del Pod**, y `preStop` consume ese plazo. Implementa el comportamiento real de SIGTERM/drenaje y verifica las conexiones, los mensajes y el manejo de reintentos después de que el Pod deje de estar listo. Tocar `/tmp/unhealthy` no hace que una sonda HTTP falle automáticamente, y mostrar «close connections» no cierra un pool de conexiones de base de datos.

Las notificaciones externas o llamadas a Pushgateway no deben bloquear indefinidamente la terminación. Las clases de prioridad y el costo de eliminación no impiden la reclamación de capacidad Spot.

### Costo y capacidad

Un `increase()` de un gauge de solicitudes de CPU no equivale a horas de nodo. Usa el tiempo real de ejecución y los datos de costo correspondientes a la hora, zona de disponibilidad, plataforma y tipo de compra. No trates los precios ausentes como si fueran cero.

Compara el gasto real con una línea base de On-Demand claramente definida para un uso equivalente. Especifica cómo incluyes Savings Plans/RI, EKS/Auto Mode, almacenamiento, redes, reintentos y capacidad inactiva. Ni un «descuento del 70 %» fijo ni un «mix 80/20 ahorra al menos el 50 %» están garantizados.

Crear una Capacity Reservation dirigida no hace que un NodePool la consuma automáticamente. Comprueba los selectores compatibles de NodeClass, la coincidencia de zona/tipo, el precio y la capacidad no utilizada. Valida el diseño de respaldo con pruebas de carga y fallos adecuadas para el requisito de disponibilidad.

## Referencias

- [Comportamiento de HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [ScaledObject de KEDA 2.21](https://keda.sh/docs/2.21/reference/scaledobject-spec/)
- [ScaledJob de KEDA 2.21](https://keda.sh/docs/2.21/reference/scaledjob-spec/)
- [Funciones de VPA 1.8.0](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/features.md)
- [Redimensionamiento de Pods](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/)
- [Costo de eliminación de ReplicaSet](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
- [Cuestionario del capítulo](../quizzes/ops/06-scaling-strategies-quiz.md)

< [Anterior: Automatización de GitOps](05-gitops-automation.md) | [Contenido](README.md) | [Siguiente: Alertas operativas](07-observability-alerts.md) >
