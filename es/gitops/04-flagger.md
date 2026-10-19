# Entrega progresiva con Flagger

> **Versiones de referencia revisadas**: Flagger/Chart 1.45.0, Loadtester 0.39.0, Flux 2.9.5 (actualizado al parche 2.9.6 tras revisar las notas de la versión; los ejemplos no se volvieron a ejecutar), Podinfo 6.15.0
> **Última actualización**: 12 de octubre de 2026

Flagger gestiona la entrega progresiva de cargas de trabajo de Kubernetes mediante el CRD Canary. Controla el tráfico y las revisiones, pero no revierte transacciones de bases de datos ni efectos secundarios en sistemas externos. Para usar estos ejemplos de laboratorio, adapte la red, la instrumentación y la autorización a su entorno, y defina los SLO del servicio.

Los ejemplos incluyen tanto manifiestos completos como fragmentos de especificaciones y valores de Helm. Integre cada fragmento en el recurso que se indica. Las estrategias que usan el mismo nombre de recurso son alternativas; elija una en lugar de aplicar todos los bloques en secuencia.

## Tabla de contenido

- [Descripción general y objetivos de aprendizaje](#overview-and-learning-objectives)
- [Arquitectura de Flagger](#flagger-architecture)
- [Instalación y configuración de EKS](#eks-installation-and-configuration)
- [Estrategia de despliegue Canary](#canary-deployment-strategy)
- [Estrategia de despliegue Blue-Green](#blue-green-deployment-strategy)
- [Estrategia de pruebas A/B](#ab-testing-strategy)
- [Métricas personalizadas y Webhooks](#custom-metrics-and-webhooks)
- [Integración de GitOps (Flux + Flagger)](#gitops-integration-flux--flagger)
- [Observabilidad y alertas](#observability-and-alerting)
- [Prácticas recomendadas para producción](#production-best-practices)

## Descripción general y objetivos de aprendizaje {#overview-and-learning-objectives}

La estrategia RollingUpdate de un Deployment de Kubernetes ya sustituye los Pods de forma gradual. Flagger añade un control explícito del tráfico entre revisiones y decide la promoción a partir de métricas y pruebas. Este capítulo explica quién gestiona cada recurso, tres estrategias de despliegue, las métricas y los controles de aprobación, la integración con GitOps y la observabilidad.

| Estrategia | Control | Qué comprobar |
|---|---|---|
| Canary | Incrementos del peso de tráfico | Réplicas adicionales, tráfico mínimo y criterios de fallo |
| Blue-Green | Validar una revisión independiente y después cambiar el tráfico | Capacidad para ambas cargas de trabajo y las réplicas temporales adicionales, y compatibilidad de la base de datos |
| A/B | Coincidencias de encabezados o cookies admitidas por el proveedor | Asignación de cohortes, análisis estadístico y autorización independiente |

Blue-Green no garantiza que se necesite exactamente el doble de recursos, que la reversión sea instantánea ni que el servicio funcione sin interrupciones. Flagger actualiza la carga de trabajo primary a la nueva revisión; después no mantiene una copia completa de la versión anterior en espera.

### Flagger y Argo Rollouts

| Aspecto | Flagger | Argo Rollouts |
|---|---|---|
| Recursos | Canary referencia una carga de trabajo existente | Rollout CRD, incluido Deployment workloadRef |
| GitOps | Flux y otras herramientas GitOps | Argo CD y otras herramientas GitOps |
| Análisis | MetricTemplate, umbrales, webhooks | AnalysisTemplate/AnalysisRun y proveedores Web/Job |
| Familia de proyecto | Flux graduado de CNCF | Argo graduado de CNCF |

La integración con un ecosistema no obliga a usar exclusivamente sus herramientas. Evite que dos controladores de entrega progresiva gestionen la misma carga de trabajo.

## Arquitectura de Flagger {#flagger-architecture}

![Flagger observa los recursos Canary/carga de trabajo y conecta enrutamiento, métricas y notificaciones.](../.gitbook/assets/en-gitops-04-flagger-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-1.html)

En el ejemplo de Deployment, podinfo es el recurso original y la carga de trabajo canary. La nueva carga de trabajo estable es podinfo-primary. podinfo-canary es un nombre de Service, no un Deployment o CloneSet adicional.

| Recurso | Propiedad/finalidad |
|---|---|
| podinfo Deployment | Plantilla de Pod de Git/Helm, control canary de Flagger |
| podinfo-primary Deployment | Carga de trabajo estable creada/promovida por Flagger |
| podinfo / podinfo-primary / podinfo-canary Services | Selección de entrada/destino administrada por Flagger |
| Autoscaler primary | Autoscaler correspondiente cuando se usa autoscalerRef |
| VirtualService/DestinationRule/HTTPRoute, etc. | Enrutamiento para el proveedor seleccionado |

![Los cambios conducen al análisis canary, actualizaciones de primary y transiciones de tráfico.](../.gitbook/assets/en-gitops-04-flagger-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-2.html)

Tras configurar inicialmente primary, los cambios en la plantilla de Pod o en los ConfigMap y Secret supervisados preparan la revisión canary. Después de las comprobaciones previas, el análisis y el ajuste del enrutamiento, la promoción envía tráfico al canary que está listo mientras primary adopta la nueva especificación. Cuando primary está listo, el tráfico vuelve a él y se reducen las réplicas del canary.

Un **fallo durante el análisis** suele devolver el tráfico a un primary que funciona correctamente. Un **fallo al actualizar primary** requiere otro tratamiento: durante Promoting/Finalising, la versión 1.45.0 puede mantener o devolver el tráfico al canary que funciona correctamente mientras informa del fallo. El estado Failed, por sí solo, no demuestra que el primary anterior esté recibiendo tráfico.

### Proveedores y ciclo de vida

| Proveedor | Comprobación |
|---|---|
| Istio | VirtualService/DestinationRule y métricas HTTP de sidecar |
| gatewayapi:v1 | Características de Gateway HTTPRoute y MetricTemplate |
| Linkerd/Contour/Gloo/Traefik/Kuma, etc. | Capacidades de la versión instalada y contrato de métricas |
| kubernetes | Blue-Green con cambio de Service, no enrutamiento L7 ponderado/A/B |
| App Mesh / ingress-nginx / OSM | Límites de ciclo de vida heredado a continuación |

El soporte de AWS App Mesh **finalizó el 2026-09-30**; AWS indica que su consola y sus recursos ya no son accesibles después de esa fecha. El ingress-nginx de la comunidad se retiró en marzo de 2026 y el repositorio de OSM está archivado.

Que exista un adaptador no garantiza que reciba mantenimiento suficiente para una nueva instalación en producción. Compruebe en cada implementación la compatibilidad con A/B, duplicación de tráfico y afinidad de sesión.

## Instalación y configuración de EKS {#eks-installation-and-configuration}

La base requiere EKS/Kubernetes admitidos, un entorno de sidecar Istio instalado y Prometheus recopilando las métricas requeridas. Reemplace su URL por el Service real. Flagger no instala Istio ni la instrumentación. La imagen de Prometheus incluida en el chart es la antigua 2.41.0, por lo que está deshabilitada.

Elija un único método para instalar y gestionar la versión de Flagger. Si instala instancias independientes en distintos namespaces, ambas podrían controlar el mismo Canary. Los ejemplos usan flagger-system para los controladores y flagger-demo para las cargas de trabajo. Adapte las etiquetas de inyección a la revisión de Istio que tenga instalada.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: flagger-system
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: flagger-demo
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: flagger-loadtester
  namespace: flagger-system
automountServiceAccountToken: false
```

### Instalación de Flagger con Helm

```yaml
fullnameOverride: flagger
meshProvider: istio
namespace: flagger-demo
noCrossNamespaceRefs: true
metricsServer: http://prometheus.monitoring.svc.cluster.local:9090
prometheus:
  install: false
leaderElection:
  enabled: true
  replicaCount: 2
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: '1'
    memory: 512Mi
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

```bash
helm repo add flagger https://flagger.app
helm repo update flagger
helm upgrade --install flagger flagger/flagger --version 1.45.0 \
  --namespace flagger-system -f flagger-values.yaml --wait --timeout 5m
```

namespace limita los recursos que Flagger observa, pero no los permisos del ClusterRole del chart. Restrinja por separado el RBAC de cada tenant. leaderElection.replicaCount es un valor admitido por el chart. A diferencia de la instalación inicial, una actualización ordinaria con Helm no actualiza crds/. Aplique por separado los CRD revisados o utilice la política de CRD de Flux.

```bash
kubectl apply --server-side -f https://raw.githubusercontent.com/fluxcd/flagger/v1.45.0/artifacts/flagger/crd.yaml
```

### Loadtester y ámbito de acceso

```yaml
fullnameOverride: flagger-loadtester
replicaCount: 1
service:
  type: ClusterIP
  port: 80
serviceAccountName: flagger-loadtester
rbac:
  create: false
cmd:
  timeout: 2m
  namespaceRegexp: ^flagger-demo$
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
securityContext:
  enabled: true
  context:
    allowPrivilegeEscalation: false
    capabilities:
      drop:
      - ALL
    readOnlyRootFilesystem: true
    runAsUser: 100
    runAsGroup: 101
volumes:
- name: tmp
  emptyDir: {}
volumeMounts:
- name: tmp
  mountPath: /tmp
```

```bash
helm upgrade --install flagger-loadtester flagger/loadtester --version 0.39.0 \
  --namespace flagger-system -f loadtester-values.yaml --wait --timeout 5m
```

Loadtester ejecuta comandos recibidos mediante solicitudes HTTP. namespaceRegexp filtra una cadena del cuerpo de la solicitud; no autentica al solicitante. Evite exponerlo a Internet y limite mediante una política del CNI las conexiones entrantes a las procedentes de los Pods del controlador. Use RBAC para controlar quién puede ejecutar exec o port-forward. En los laboratorios con controles de aprobación en memoria, use una sola réplica.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: flagger-loadtester-ingress
  namespace: flagger-system
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: loadtester
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: flagger-system
      podSelector:
        matchLabels:
          app.kubernetes.io/name: flagger
    ports:
    - protocol: TCP
      port: 8080
```

Permita el tráfico necesario para el mTLS de Istio y la recopilación de métricas. Este loadtester no realiza operaciones de API, por lo que se deshabilita el montaje automático del token de ServiceAccount. Si añade pruebas con Helm o kubectl, configure explícitamente los permisos y las rutas donde deban escribir.

### Alternativa de Gateway API

El ejemplo requiere una GatewayClass de Istio existente y CRD de Gateway API compatibles. No los sustituya por un paquete antiguo. Si usa otra implementación, adapte la instrumentación y las consultas. Configure para su entorno la exposición mediante Service o balanceador de carga, el DNS y el TLS.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: podinfo-gateway
  namespace: flagger-demo
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Same
```

Use **gatewayapi:v1** y Canary service.gatewayRefs, no un valor Helm gatewayApi.gateway inventado. Prepare los tres MetricTemplates de abajo y use este Canary como una **alternativa** al enfoque de Istio.

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  provider: gatewayapi:v1
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: podinfo
  progressDeadlineSeconds: 120
  service:
    port: 9898
    targetPort: 9898
    hosts:
    - app.example.com
    gatewayRefs:
    - name: podinfo-gateway
      namespace: flagger-demo
      sectionName: http
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: error-rate
      templateRef:
        name: istio-error-rate
      thresholdRange:
        min: 0
        max: 1
      interval: 1m
    - name: latency-p99-ms
      templateRef:
        name: istio-latency-ms
      thresholdRange:
        min: 0
        max: 500
      interval: 1m
    - name: request-count
      templateRef:
        name: istio-request-count
      thresholdRange:
        min: 100
      interval: 1m
    webhooks:
    - name: smoke-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 30s
      metadata:
        type: bash
        cmd: |-
          set -euo pipefail
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/healthz >/dev/null
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/readyz >/dev/null
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 5s
      metadata:
        type: cmd
        cmd: hey -z 1m -q 10 -c 2 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/
```

```bash
helm upgrade --install flagger flagger/flagger --version 1.45.0 \
  --namespace flagger-system -f flagger-values.yaml --set meshProvider=gatewayapi:v1
```

## Estrategia de despliegue Canary {#canary-deployment-strategy}

Estos son la carga de trabajo de Istio y el HPA base; Metrics Server es obligatorio. Omita las réplicas de Deployment de Git para que HPA/Flagger puedan controlar el escalado, y no cree un Service que compita. Elija estos manifiestos o la alternativa HelmRelease posterior.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  selector:
    matchLabels:
      app: podinfo
  template:
    metadata:
      labels:
        app: podinfo
    spec:
      containers:
      - name: podinfo
        image: ghcr.io/stefanprodan/podinfo:6.15.0
        ports:
        - name: http
          containerPort: 9898
        readinessProbe:
          httpGet:
            path: /readyz
            port: http
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 256Mi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  minReplicas: 2
  maxReplicas: 4
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

![El Canary ponderado avanza después del análisis y evalúa fallos acumulados.](../.gitbook/assets/en-gitops-04-flagger-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-3.html)

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  provider: istio
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: podinfo
  progressDeadlineSeconds: 120
  service:
    port: 9898
    targetPort: 9898
    portName: http
    gateways:
    - mesh
    hosts:
    - podinfo
    trafficPolicy:
      tls:
        mode: ISTIO_MUTUAL
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
        max: 100
      interval: 1m
    - name: request-duration
      thresholdRange:
        min: 0
        max: 500
      interval: 1m
    webhooks:
    - name: smoke-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 30s
      metadata:
        type: bash
        cmd: |-
          set -euo pipefail
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/healthz >/dev/null
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/readyz >/dev/null
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 5s
      metadata:
        type: cmd
        cmd: hey -z 1m -q 10 -c 2 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/
```

Iterations selecciona Blue-Green, o A/B si también se define match; no combine estos ajustes con un Canary ponderado. StepWeight 10 y maxWeight 50 indican que se analiza el tráfico en los pasos 10→20→30→40→50 % antes de la promoción. La duración total depende de cuándo estén listas las cargas de trabajo, de la latencia de las comprobaciones, de los fallos o aprobaciones y del despliegue de primary.

Analysis.interval establece la frecuencia del análisis; el intervalo de cada métrica determina la ventana de consulta y agregación. Threshold 5 cuenta los fallos acumulados de las comprobaciones para una revisión. No es un contador de fallos consecutivos que se reinicie tras cada éxito. Al alcanzar cinco, la siguiente reconciliación inicia la reversión. Se incluyen los fallos de las comprobaciones previas al despliegue, del despliegue y de las métricas. ProgressDeadlineSeconds limita el tiempo de progreso y preparación de la carga de trabajo; no equivale al doble de la duración total del despliegue.

Para pesos no lineales, use stepWeights y elimine stepWeight/maxWeight existentes. Las conexiones y la convergencia de enrutamiento significan que los pesos configurados no garantizan una proporción exacta de solicitudes en cada instante.

```yaml
spec:
  analysis:
    stepWeights:
    - 1
    - 2
    - 5
    - 10
    - 25
    - 50
```

```bash
kubectl get canary podinfo -n flagger-demo --watch
kubectl describe canary podinfo -n flagger-demo
kubectl logs -n flagger-system -l app.kubernetes.io/name=flagger -c flagger --prefix --tail=100
```

Después de la configuración estable inicial, aplique mediante Git un cambio revisado de imagen/tag/digest o de plantilla de Pod para iniciar el análisis. Reemplazar contenido remoto tras la misma etiqueta no sustituye un cambio de Git. No edite directamente los recursos generados de primary, Service o enrutamiento.

## Estrategia de despliegue Blue-Green {#blue-green-deployment-strategy}

![Blue-Green valida canary, actualiza primary y luego reduce canary.](../.gitbook/assets/en-gitops-04-flagger-4.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-4.html)

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  provider: istio
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: podinfo
  progressDeadlineSeconds: 120
  service:
    port: 9898
    targetPort: 9898
    portName: http
    gateways:
    - mesh
    hosts:
    - podinfo
    trafficPolicy:
      tls:
        mode: ISTIO_MUTUAL
  analysis:
    interval: 1m
    threshold: 5
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
        max: 100
      interval: 1m
    - name: request-duration
      thresholdRange:
        min: 0
        max: 500
      interval: 1m
    webhooks:
    - name: smoke-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 30s
      metadata:
        type: bash
        cmd: |-
          set -euo pipefail
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/healthz >/dev/null
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/readyz >/dev/null
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 5s
      metadata:
        type: cmd
        cmd: hey -z 1m -q 10 -c 2 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/
    iterations: 10
```

Este ejemplo analiza tráfico sintético mientras el tráfico real sigue llegando a primary. Si el análisis se supera, el tráfico pasa al canary mientras primary se actualiza y vuelve a primary cuando está listo. Los umbrales de fallo siguen vigentes: una única medición fallida no siempre inicia una reversión inmediata. Al terminar, no se conserva un entorno independiente con una copia completa de la versión anterior.

### Duplicación opcional de tráfico

```yaml
spec:
  analysis:
    mirror: true
    mirrorWeight: 10
```

Los proveedores compatibles pueden duplicar tráfico como fase previa de Canary o en un despliegue Blue-Green. En Gateway API, compruebe la compatibilidad con RequestMirror. Descartar las respuestas de la copia no evita escrituras en bases de datos, pagos, mensajes ni carga adicional. Use solicitudes cuya condición de solo lectura haya verificado o aísle el entorno receptor. Duplicar tráfico no replica bases de datos ni permite revertirlas.

<span id="ab-testing-strategy"></span>

## Estrategia de pruebas A/B

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  provider: istio
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: podinfo
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: podinfo
  progressDeadlineSeconds: 120
  service:
    port: 9898
    targetPort: 9898
    portName: http
    gateways:
    - mesh
    hosts:
    - podinfo
    trafficPolicy:
      tls:
        mode: ISTIO_MUTUAL
  analysis:
    interval: 1m
    threshold: 5
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
        max: 100
      interval: 1m
    - name: request-duration
      thresholdRange:
        min: 0
        max: 500
      interval: 1m
    webhooks:
    - name: smoke-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 30s
      metadata:
        type: bash
        cmd: |-
          set -euo pipefail
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/healthz >/dev/null
          curl -fsS --max-time 10 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/readyz >/dev/null
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/
      timeout: 5s
      metadata:
        type: cmd
        cmd: hey -z 1m -q 10 -c 2 http://podinfo-canary.flagger-demo.svc.cluster.local:9898/
    iterations: 10
    match:
    - headers:
        x-canary:
          exact: insider
    - headers:
        cookie:
          regex: (^|.*;\s*)canary=always(;.*|$)
```

Las entradas match se combinan como alternativas OR; las condiciones de una misma entrada siguen las reglas del proveedor. La expresión regular de la cookie admite espacios después de los puntos y coma. En Istio, sourceLabels identifica etiquetas de la carga de trabajo, no direcciones IP de origen. Compruebe qué criterios de coincidencia admite la implementación y versión de Gateway que utiliza.

El enrutamiento no es autorización ni un experimento estadístico completo. No confíe en marcadores controlados por el cliente como permisos de empleados. Asigne cohortes en un borde de confianza y autorice en el lado del servidor; las conclusiones A/B significativas también requieren muestras, diseño de asignación y pruebas estadísticas.

Verifique la ruta de la malla desde el Pod de loadtester con el sidecar inyectado. Para las rutas externas de Gateway, pruebe el host, TLS y acceso de entrada que se utilizarán realmente. Una llamada directa a -canary no valida las reglas de coincidencia del enrutamiento.

```bash
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -fsS http://podinfo.flagger-demo.svc.cluster.local:9898/
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -fsS -H 'x-canary: insider' http://podinfo.flagger-demo.svc.cluster.local:9898/
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -fsS -b 'canary=always' http://podinfo.flagger-demo.svc.cluster.local:9898/
```

## Métricas personalizadas y Webhooks {#custom-metrics-and-webhooks}

### Prometheus MetricTemplate

Estas consultas dependen de las métricas del sidecar de Istio. Compruebe las etiquetas de namespace y carga de trabajo, el valor de reporter y la recopilación de datos. Si falta una serie 5xx, el numerador se considera cero; si no hay tráfico o el denominador es cero, el resultado no se considera satisfactorio. El mínimo de 100 solicitudes y los demás límites son ejemplos: ajústelos a los SLO y al tamaño de muestra necesario.

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: istio-error-rate
  namespace: flagger-demo
spec:
  provider:
    type: prometheus
    address: http://prometheus.monitoring.svc.cluster.local:9090
  query: |
    (sum(rate(istio_requests_total{reporter="destination", destination_workload_namespace="{{ namespace }}", destination_workload="{{ target }}", response_code=~"5.."}[{{ interval }}])) or vector(0)) / sum(rate(istio_requests_total{reporter="destination", destination_workload_namespace="{{ namespace }}", destination_workload="{{ target }}"}[{{ interval }}])) * 100
---
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: istio-latency-ms
  namespace: flagger-demo
spec:
  provider:
    type: prometheus
    address: http://prometheus.monitoring.svc.cluster.local:9090
  query: |
    histogram_quantile(0.99, sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination", destination_workload_namespace="{{ namespace }}", destination_workload="{{ target }}"}[{{ interval }}])) by (le))
---
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: istio-request-count
  namespace: flagger-demo
spec:
  provider:
    type: prometheus
    address: http://prometheus.monitoring.svc.cluster.local:9090
  query: |
    sum(increase(istio_requests_total{reporter="destination", destination_workload_namespace="{{ namespace }}", destination_workload="{{ target }}"}[{{ interval }}]))
---
spec:
  analysis:
    metrics:
    - name: error-rate
      templateRef:
        name: istio-error-rate
      thresholdRange:
        min: 0
        max: 1
      interval: 1m
    - name: latency-p99-ms
      templateRef:
        name: istio-latency-ms
      thresholdRange:
        min: 0
        max: 500
      interval: 1m
    - name: request-count
      templateRef:
        name: istio-request-count
      thresholdRange:
        min: 100
      interval: 1m
```

MetricTemplate debe devolver un valor numérico. El proveedor Prometheus rechaza resultados vacíos/NaN. Limite los porcentajes a rangos finitos de 0–100 y alinee las unidades de latencia personalizadas. Los límites son inclusivos. Las mediciones con ventanas de consulta superpuestas no son muestras independientes.

### Unidades de Datadog y punto de datos seleccionado

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: datadog-average-latency-ms
  namespace: flagger-demo
spec:
  provider:
    type: datadog
    address: https://api.datadoghq.com
    secretRef:
      name: datadog-api
  query: |
    avg:myapp.request_duration_ms{kube_deployment:{{ target }},kube_namespace:{{ namespace }}}.rollup(avg, 60)
---
apiVersion: v1
kind: Secret
metadata:
  name: datadog-api
  namespace: flagger-demo
type: Opaque
stringData:
  datadog_api_key: REPLACE_WITH_API_KEY
  datadog_application_key: REPLACE_WITH_APPLICATION_KEY
```

myapp.request_duration_ms es una latencia media personalizada en ms que debe publicar; no es P99. Seleccione el sitio con provider.address. El cliente lee las dos claves de Secret mostradas, no datadog_site. Consulta diez veces el intervalo de métrica y devuelve el punto más antiguo de la primera serie. No lo use por sí solo como prueba de la salud actual del canary; combínelo con mediciones recientes específicas de la revisión.

Las pruebas locales con respuestas simuladas del cliente original también confirmaron que un primer punto de datos nulo se interpreta como cero. Por ello, un control de latencia que acepte cero milisegundos puede dar una señal engañosa. Use un componente intermediario que valide las marcas de tiempo y los valores ausentes, o mediciones recientes de Prometheus.

### Campos y límites de CloudWatch

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: cloudwatch-error-percent
  namespace: flagger-demo
spec:
  provider:
    type: cloudwatch
    region: ap-northeast-2
  query: |
    [
      {
        "Id": "errorrate",
        "Expression": "IF(FILL(requests,0)>=100,100*FILL(errors,0)/FILL(requests,0),-1)",
        "Label": "CanaryErrorPercent",
        "ReturnData": true
      },
      {
        "Id": "errors",
        "MetricStat": {
          "Metric": {
            "Namespace": "MyApp",
            "MetricName": "5xxErrors",
            "Dimensions": [
              {
                "Name": "Service",
                "Value": "{{ target }}"
              },
              {
                "Name": "Namespace",
                "Value": "{{ namespace }}"
              }
            ]
          },
          "Period": 60,
          "Stat": "Sum"
        },
        "ReturnData": false
      },
      {
        "Id": "requests",
        "MetricStat": {
          "Metric": {
            "Namespace": "MyApp",
            "MetricName": "TotalRequests",
            "Dimensions": [
              {
                "Name": "Service",
                "Value": "{{ target }}"
              },
              {
                "Name": "Namespace",
                "Value": "{{ namespace }}"
              }
            ]
          },
          "Period": 60,
          "Stat": "Sum"
        },
        "ReturnData": false
      }
    ]
---
spec:
  analysis:
    metrics:
    - name: cw-error-percent
      templateRef:
        name: cloudwatch-error-percent
      thresholdRange:
        min: 0
        max: 1
      interval: 1m
```

Provider.region es un campo admitido y obligatorio. Publique por separado las métricas MyApp y sus dimensiones Service/Namespace. La expresión devuelve -1 para períodos sin datos o con poco tráfico, por lo que el resultado queda fuera del intervalo permitido de 0–1 %. Los retrasos de ingestión pueden hacer que se rechace un despliegue; compruebe la publicación efectiva de las métricas y las ventanas de agregación y consulta.

El proveedor nativo consulta diez veces el intervalo de métrica y selecciona el primer valor del primer resultado sin validar por separado timestamp/StatusCode. Complételo con comprobaciones actuales de solicitudes/salud de Prometheus específicas de la revisión para que puntos antiguos o métricas ALB agregadas no se confundan con la salud actual del canary. Su permiso de API de AWS es GetMetricData.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "cloudwatch:GetMetricData",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    }
  ]
}
```

Configure la autenticación de ServiceAccount y la confianza de rol de Flagger cuando se use CloudWatch, y haga coincidir la condición de región. Esta revisión no llamó a API de AWS ni desplegó un rol.

### Contrato de Webhook

| Tipo | Función y comportamiento ante el rechazo |
|---|---|
| confirm-rollout | Esperar la aprobación para iniciar |
| pre-rollout | Comprobar antes del primer cambio de tráfico; acumula fallos |
| rollout | Ejecutar durante el análisis; acumula fallos |
| confirm-traffic-increase | Esperar antes de aumentar el peso de tráfico |
| confirm-promotion | Esperar antes de la promoción |
| post-rollout | Notificar o limpiar después de Succeeded o Failed; no revierte el resultado |
| rollback | Una respuesta satisfactoria durante el análisis o la espera de aprobación solicita una reversión |
| event | Reenviar eventos relacionados con el estado |

Normalmente devuelva HTTP 200. La versión 1.45.0 trata los códigos superiores a 202 como errores, por lo que no suponga que 204 tiene éxito. Los metadatos se copian literalmente; `{{ .Version }}` no se interpola. Use name/namespace/phase/checksum de la carga útil. Los cuerpos no exitosos pueden llegar a logs/events, así que no devuelva valores sensibles.

```yaml
name: podinfo
namespace: flagger-demo
phase: Progressing
checksum: example-revision-checksum
metadata:
  gate: promotion
```

La configuración de Webhook no proporciona encabezados Authorization arbitrarios. Implemente la autenticación requerida mediante un límite de mTLS/proxy interno revisado; no coloque secretos en URL/metadatos públicos de Git ni deshabilite la verificación de TLS de forma predeterminada.

Las pruebas de carga de tipo cmd se aceptan de forma asíncrona; una respuesta HTTP satisfactoria no demuestra que la prueba haya cumplido sus objetivos. Bash espera a que termine el comando, que debe completarse dentro de su tiempo de espera. La imagen 0.39.0 incluye curl/jq/hey/wrk/bash, pero no k6. Para usar k6, verifique otra imagen y defina umbrales: check() por sí solo no hace que el proceso termine con un código de error.

Este script es para una imagen de prueba dedicada con k6 instalado, no un comando que funcione en la imagen loadtester predeterminada.

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 2,
  duration: '20s',
  thresholds: {
    checks: ['rate==1'],
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(99)<500'],
  },
};
export default function () {
  const result = http.get('http://podinfo-canary.flagger-demo.svc.cluster.local:9898/');
  check(result, { 'HTTP 200': (response) => response.status === 200 });
  sleep(0.5);
}
```

### Controles de aprobación manual

```yaml
spec:
  analysis:
    webhooks:
    - name: promotion-approval
      type: confirm-promotion
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/gate/check
      timeout: 5s
      metadata:
        gate: promotion
```

Integre esta entrada en la lista de webhooks del Canary existente. /gate/approve aprueba siempre; no sirve como control de aprobación manual. /gate/check consulta el estado en memoria identificado por name.namespace. Envíe el mismo cuerpo JSON a los endpoints open, close y check. Cerrar el control deja la promoción en espera; no inicia una reversión.

```bash
# Close before starting a new revision.
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"podinfo","namespace":"flagger-demo"}' http://localhost:8080/gate/close
# Approve the reviewed revision.
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"podinfo","namespace":"flagger-demo"}' http://localhost:8080/gate/open
# A closed gate returns 403.
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' \
  -d '{"name":"podinfo","namespace":"flagger-demo"}' http://localhost:8080/gate/check
```

El control integrado no distingue revisiones por checksum, pierde su estado al reiniciar el Pod y no comparte el estado entre réplicas. Ciérrelo antes de la siguiente revisión. En producción, la aprobación necesita autenticación, auditoría, caducidad y un estado identificado por name/namespace/checksum/gate. Compartir un único control en memoria entre el inicio y la promoción no equivale a obtener dos aprobaciones independientes.

### Rollback manual y suspensión

```yaml
spec:
  analysis:
    webhooks:
    - name: operator-rollback
      type: rollback
      url: http://flagger-loadtester.flagger-system.svc.cluster.local/rollback/check
      timeout: 5s
```

El endpoint de rollback suele devolver 403 si no hay una solicitud de reversión y 200 cuando la hay. Si usa aquí un receptor de notificaciones que devuelve éxito, podría iniciar una reversión involuntaria. Las solicitudes siguientes piden la reversión durante la reconciliación normal, mientras se realiza el análisis o se espera la aprobación de la promoción. No son un mecanismo de recuperación instantánea válido para todas las fases.

```bash
kubectl get canary podinfo -n flagger-demo -o jsonpath='{.status.phase}{"\n"}'
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"podinfo","namespace":"flagger-demo"}' http://localhost:8080/rollback/open
kubectl get canary podinfo -n flagger-demo --watch
# Reset the request after observing the operation.
kubectl exec -n flagger-system deployment/flagger-loadtester -- \
  curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"podinfo","namespace":"flagger-demo"}' http://localhost:8080/rollback/close
```

Un fallo del controlador, una carga de trabajo que no esté lista o un control confirm-rollout cerrado pueden interrumpir la reconciliación antes de que se ejecute este hook. Los fallos de primary durante Promoting/Finalising requieren el procedimiento de recuperación descrito anteriormente. Si deja abierta la solicitud de rollback al finalizar, podría afectar a la siguiente revisión.

Las anotaciones flagger.app/rollback, flagger.app/suspend y flagger.app/skipAnalysis no son API de control. Suspend y skipAnalysis son campos de la especificación. Suspend detiene la reconciliación, incluidos los hooks de rollback, sin devolver el tráfico a primary. SkipAnalysis promueve la revisión sin analizarla; no la revierte. Actualice también la configuración en Git que gestiona el recurso.

```yaml
spec:
  suspend: true
```

<span id="gitops-integration-flux--flagger"></span>

## Integración de GitOps (Flux + Flagger)

![Flux aplica las cargas de trabajo deseadas; Flagger administra la entrega progresiva por separado.](../.gitbook/assets/en-gitops-04-flagger-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-0.html)

![Flux aplica las cargas de trabajo deseadas mientras Flagger controla el análisis Canary.](../.gitbook/assets/en-gitops-04-flagger-5.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-5.html)

El bootstrap de Flux no instala Flagger como controlador integrado. Instálelo por separado mediante HelmRelease o Kustomization. Evite gestionar simultáneamente la misma instalación con la CLI de Helm. Incluya también en Git los namespaces, ServiceAccount y NetworkPolicy descritos anteriormente.

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: flagger
  namespace: flagger-system
spec:
  interval: 1h
  url: https://flagger.app
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: flagger
  namespace: flagger-system
spec:
  interval: 1h
  releaseName: flagger
  chart:
    spec:
      chart: flagger
      version: 1.45.0
      sourceRef:
        kind: HelmRepository
        name: flagger
  install:
    crds: Create
  upgrade:
    crds: CreateReplace
  values:
    fullnameOverride: flagger
    meshProvider: istio
    namespace: flagger-demo
    noCrossNamespaceRefs: true
    metricsServer: http://prometheus.monitoring.svc.cluster.local:9090
    prometheus:
      install: false
    leaderElection:
      enabled: true
      replicaCount: 2
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: '1'
        memory: 512Mi
    podDisruptionBudget:
      enabled: true
      minAvailable: 1
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: loadtester
  namespace: flagger-system
spec:
  interval: 1h
  releaseName: flagger-loadtester
  chart:
    spec:
      chart: loadtester
      version: 0.39.0
      sourceRef:
        kind: HelmRepository
        name: flagger
  values:
    fullnameOverride: flagger-loadtester
    replicaCount: 1
    service:
      type: ClusterIP
      port: 80
    serviceAccountName: flagger-loadtester
    rbac:
      create: false
    cmd:
      timeout: 2m
      namespaceRegexp: ^flagger-demo$
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
    securityContext:
      enabled: true
      context:
        allowPrivilegeEscalation: false
        capabilities:
          drop:
          - ALL
        readOnlyRootFilesystem: true
        runAsUser: 100
        runAsGroup: 101
    volumes:
    - name: tmp
      emptyDir: {}
    volumeMounts:
    - name: tmp
      mountPath: /tmp
```

El manejo CreateReplace de CRD de Flux no es una garantía de migración segura. Revise los cambios de CRD y los objetos almacenados antes de las actualizaciones. Aplique objetos Canary después de que las fuentes y la instalación del proveedor estén listas.

### Alternativa HelmRelease de aplicación

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  interval: 1h
  url: https://stefanprodan.github.io/podinfo
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: podinfo
  namespace: flagger-demo
spec:
  interval: 5m
  releaseName: podinfo
  chart:
    spec:
      chart: podinfo
      version: 6.15.0
      sourceRef:
        kind: HelmRepository
        name: podinfo
  values:
    service:
      enabled: false
    hpa:
      enabled: true
      minReplicas: 2
      maxReplicas: 4
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
```

Podinfo 6.15.0 service.enabled=false evita la propiedad de Service en competencia. Con hpa.enabled=true el chart no fija las réplicas de Deployment. No aplique este HelmRelease junto con los manifiestos de carga de trabajo nativos. Verifique el comportamiento equivalente renderizando otros charts, en lugar de asumir nombres de valores idénticos.

Gestione el Canary anterior junto con la aplicación. El estado Ready de Flux/Helm indica que los recursos se han aplicado y están listos; no demuestra por sí solo que Flagger haya promovido la revisión actual. Antes de avanzar al siguiente entorno, compruebe el estado y checksum del Canary y que la versión desplegada corresponda al cambio previsto.

### Alternativa Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: flagger-demo
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./apps/podinfo
  prune: true
  timeout: 5m
```

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: flagger-demo
resources:
- deployment.yaml
- hpa.yaml
- canary.yaml
```

El sourceRef usa el nombre predeterminado de GitRepository del bootstrap. Almacene los manifiestos nativos bajo apps/podinfo y omita los recursos de Service/primary propiedad de Flagger. El éxito de la aplicación Kustomization no es la finalización de la promoción.

Una superposición de entorno puede aplicar parches explícitos a configuraciones escalares. Estas son elecciones ilustrativas, no un estándar universal de producción. Compruebe también el comportamiento de reemplazo de arrays al aplicar parches a CRD.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- ../base
patches:
- target:
    group: flagger.app
    version: v1beta1
    kind: Canary
    name: podinfo
  patch: |
    - op: replace
      path: /spec/analysis/threshold
      value: 3
    - op: replace
      path: /spec/analysis/maxWeight
      value: 30
    - op: replace
      path: /spec/analysis/stepWeight
      value: 5
```

### Automatización de imágenes y ramas de promoción

![Las imágenes seleccionadas llegan a Git mediante una rama/PR dedicada antes del análisis Canary.](../.gitbook/assets/en-gitops-04-flagger-6.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-6.html)

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageRepository
metadata:
  name: podinfo
  namespace: flux-system
spec:
  image: ghcr.io/stefanprodan/podinfo
  interval: 5m
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImagePolicy
metadata:
  name: podinfo
  namespace: flux-system
  labels:
    app: podinfo
spec:
  imageRepositoryRef:
    name: podinfo
  policy:
    semver:
      range: '>=6.15.0 <7.0.0'
  digestReflectionPolicy: IfNotPresent
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageUpdateAutomation
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: flux-system
  policySelector:
    matchLabels:
      app: podinfo
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        name: Flux
        email: flux@example.com
      messageTemplate: |-
        Update podinfo image
        {{ range .Changed.Changes }}{{ .OldValue }} -> {{ .NewValue }}
        {{ end }}
    push:
      branch: flux/podinfo-updates
  update:
    path: ./apps/podinfo
    strategy: Setters
```

Este flujo requiere los controladores image-reflector/image-automation, marcadores de política y acceso de escritura a Git. Los cambios se envían a una rama dedicada; la creación del PR, sus comprobaciones y la fusión se realizan por separado. Adapte el repositorio y las rutas, y reserve la rama para la automatización. Use el modelo actual .Changed en la plantilla del mensaje de commit; .NewTag no es un campo válido.

```yaml
# Native Deployment Pod-template fragment.
spec:
  template:
    spec:
      containers:
      - name: podinfo
        image: ghcr.io/stefanprodan/podinfo:6.15.0 # {"$imagepolicy": "flux-system:podinfo"}
```

```yaml
# Alternative: merge into HelmRelease.spec.values.
image:
  repository: ghcr.io/stefanprodan/podinfo
  tag: "6.15.0" # {"$imagepolicy": "flux-system:podinfo:tag"}
```

Un marcador solo de tag no fija un digest. Verifique la compatibilidad de digest del chart o la inmutabilidad y validación de etiquetas del registro. No sobrescriba una imagen de forma inconsistente mediante Kustomize images y un marcador de Deployment. ECR necesita autenticación AWS independiente de image-reflector y autorización real para extraer imágenes de Pod.

## Observabilidad y alertas {#observability-and-alerting}

Las métricas de Flagger y las métricas de Istio/aplicación son destinos de recopilación diferentes. Las anotaciones no hacen que cada instalación de Prometheus recopile automáticamente. Para Prometheus Operator, alinee el serviceMonitor.enabled del chart con los selectores, namespaces y acceso mTLS reales.

```yaml
serviceMonitor:
  enabled: true
  labels:
    release: prometheus
```

La etiqueta release es ilustrativa y debe coincidir con el serviceMonitorSelector de Prometheus. Los CRD del Operator instalados son un requisito previo.

| Métrica | Tipo/significado real |
|---|---|
| flagger_info | Gauge, versión/mesh_provider |
| flagger_canary_total | Gauge, conteo de objetos Canary por namespace |
| flagger_canary_status | Gauge, 0=Progressing, 2=Failed, otras fases se asignan a 1 |
| flagger_canary_weight | Gauge, peso de tráfico por carga de trabajo/namespace |
| flagger_canary_metric_analysis | Gauge, valor de métrica real, no un booleano genérico de éxito/fallo |
| flagger_canary_duration_seconds | Histogram, tiempo de procesamiento de reconciliación de análisis, no duración total de rollout |
| flagger_canary_successes_total / failures_total | Counter, resultados con etiquetas strategy/analysis_status |

No infiera Succeeded del valor de estado 1; las fases de aprobación/promoción y otras pueden compartirlo. Compruebe Canary.status.phase y la revisión prevista. La etiqueta name es targetRef.name, no necesariamente el nombre del objeto Canary. Weight usa workload en lugar de name. Lea status.iterations en vez de asumir que existe una métrica iterations exportada.

### Dashboard de Grafana

Use las siguientes consultas en paneles actuales Stat/Time series de Grafana. Filtre una etiqueta externa de cluster al agregar centralmente. Flagger clusterName afecta a las alertas; no añade automáticamente una etiqueta de cluster a las métricas de Prometheus.

```promql
flagger_canary_status{namespace="flagger-demo"}
flagger_canary_weight{namespace="flagger-demo",workload="podinfo"}
flagger_canary_metric_analysis{namespace="flagger-demo",name="podinfo",metric="request-success-rate"}
increase(flagger_canary_successes_total{namespace="flagger-demo",analysis_status="completed"}[7d])
increase(flagger_canary_failures_total{namespace="flagger-demo",analysis_status="completed"}[7d])
```

El JSON del dashboard oficial de Istio es una referencia; valide sus nombres de datasource y la compatibilidad de panel/esquema en Grafana actual, y luego expórtelo. El JSON de dashboard no es un manifiesto de Kubernetes. Aprovisione el modelo de dashboard exportado, no un sobre de API HTTP {"dashboard": ...}.

```bash
curl -fsSL -o flagger-istio-reference.json \
  https://raw.githubusercontent.com/fluxcd/flagger/v1.45.0/charts/grafana/dashboards/istio.json
# After reviewing/exporting flagger-dashboard.json in Grafana:
jq -e '.title and (.panels | type == "array")' flagger-dashboard.json >/dev/null
kubectl create configmap flagger-dashboard -n monitoring \
  --from-file=flagger-dashboard.json=./flagger-dashboard.json \
  --dry-run=client -o yaml > flagger-dashboard-cm.yaml
kubectl label --local -f flagger-dashboard-cm.yaml grafana_dashboard=1 \
  -o yaml > flagger-dashboard-ready.yaml
```

Revise el ConfigMap generado y colóquelo bajo GitOps. Configure el sidecar/provisioner de Grafana para que observe su etiqueta y namespace. No se base en un ID de dashboard no verificado como guía de instalación.

### Alertas de Prometheus

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: flagger-alerts
  namespace: monitoring
spec:
  groups:
  - name: flagger
    rules:
    - alert: FlaggerAnalysisFailed
      expr: flagger_canary_status == 2
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: Flagger analysis failed for {{ $labels.namespace }}/{{ $labels.name }}
        description: Inspect Canary phase, events, and actual routing before assuming the old primary is serving
          traffic.
    - alert: FlaggerAnalysisLongRunning
      expr: flagger_canary_status == 0
      for: 1h
      labels:
        severity: warning
      annotations:
        summary: Flagger analysis remains active for {{ $labels.namespace }}/{{ $labels.name }}
        description: Check approval gates, failed checks and workload readiness; this is not a measurement of rollout
          duration.
```

Estas reglas presuponen un Prometheus local al clúster. La condición ==0 con for:1h detecta un estado Progressing observado de forma continua; no cubre todas las fases activas ni calcula el tiempo desde el inicio del despliegue. Evalúe por separado las esperas de aprobación intencionales. Los buckets del histograma miden tiempos breves de procesamiento de la reconciliación. No use time()-duration ni un umbral de 600 segundos como alerta de P99 de duración del despliegue.

### Slack, Teams y notificaciones externas

```yaml
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: slack
  namespace: flagger-demo
spec:
  type: slack
  channel: C0123456789
  username: flagger
  secretRef:
    name: slack-bot
---
apiVersion: v1
kind: Secret
metadata:
  name: slack-bot
  namespace: flagger-demo
type: Opaque
stringData:
  address: https://slack.com/api/chat.postMessage
  token: REPLACE_WITH_SLACK_BOT_TOKEN
---
spec:
  analysis:
    alerts:
    - name: deployment-alerts
      severity: info
      providerRef:
        name: slack
```

Los valores de Secret son marcadores de posición; mantenga los tokens reales fuera de Git. AlertProvider secretRef requiere address en esta versión, más token para Slack Bot API. Configure chat:write y la pertenencia al canal, y reemplace el canal por el ID real. Para Incoming Webhooks, verifique el canal vinculado y las anulaciones permitidas.

Severity es un nivel mínimo, no enrutamiento exclusivo: info recibe todos los niveles, warn recibe warn/error y error recibe errores. Las suscripciones duplicadas pueden duplicar notificaciones.

El msteams nativo de Flagger 1.45.0 aún emite MessageCard. No suponga que basta intercambiar su URL por un endpoint de Workflows Adaptive Card. Configure un convertidor compatible o receptor de eventos con autenticación y conversión de carga útil. Esto difiere del comportamiento de Teams de Flux 2.9.6.

No suponga un AlertProvider nativo de PagerDuty Events API. Enviar type: slack directamente a una URL de PagerDuty genera una carga útil incorrecta. Use una integración de Slack establecida o un adaptador de eventos verificado.

### Historial y eventos de despliegue

```yaml
spec:
  analysis:
    webhooks:
    - name: deployment-events
      type: event
      url: http://deployment-events.flagger-system.svc.cluster.local/events
      timeout: 5s
      metadata:
        environment: demo
```

Deployment-events es un receptor interno que debe implementar por separado. Valide y almacene name/namespace/phase/checksum y eventMessage/eventType/timestamp. Post-rollout se ejecuta tanto tras el éxito como tras el fallo, por lo que no registre siempre el resultado como una promoción. eventSources de Flux Notification Alert no admite Canary ni recopila automáticamente eventos arbitrarios de Kubernetes.

```bash
kubectl get events -n flagger-demo \
  --field-selector involvedObject.kind=Canary,involvedObject.name=podinfo \
  --sort-by='.lastTimestamp'
kubectl get canaries -A -o custom-columns=\
NAME:.metadata.name,NAMESPACE:.metadata.namespace,PHASE:.status.phase,WEIGHT:.status.canaryWeight,LAST:.status.lastTransitionTime
```

Los eventos de Kubernetes tienen límites de retención; conserve el historial duradero externamente. changes(status[7d]) cuenta transiciones, no despliegues. Interprete los contadores de resultados considerando skipped/completed y las revisiones reales.

## Prácticas recomendadas para producción {#production-best-practices}

Comience con cargas de trabajo no críticas/de laboratorio y pruebe éxito, fallo, datos ausentes, espera de aprobación y fallo de promoción de primary. Un umbral de fallo mayor puede retrasar el rollback en lugar de mejorar la seguridad. Un stepWeight mayor expone a más usuarios; intervalos de análisis más largos pueden retrasar la detección.

| Decisión | Datos en los que basarla |
|---|---|
| Límites de error y latencia | SLO del servicio, unidades reales y distribución habitual de los valores |
| Solicitudes mínimas y ventana de consulta | Tráfico bajo, retraso de ingestión y tamaño de muestra |
| Umbral de fallo | Tiempo de exposición permitido y falsas alarmas |
| Incrementos del peso de tráfico | Alcance del impacto y capacidad de réplicas o nodos disponibles |
| Plazo de progreso | Arranque de los Pods, preparación y avance de la actualización gradual |
| Aprobación y reversión | Autenticación, identidad de la revisión y procedimiento de recuperación |

No derive 99.9 %, 200 ms o duraciones exactas de rollout únicamente de etiquetas de entorno/industria. Mida, ajuste y verifique regularmente el comportamiento de fallo/recuperación.

### Seguimiento de configuración y escalado automático

El seguimiento de ConfigMap/Secret está habilitado de forma predeterminada y los cambios de configuración referenciada pueden activar análisis. Excluya un ConfigMap/Secret seleccionado con esta anotación en dicho recurso. También es posible configTracking.enabled=false globalmente, pero revise su efecto en la detección y las copias de configuración de primary.

```yaml
metadata:
  annotations:
    flagger.app/config-tracking: disabled
```

Los escaladores HPA/KEDA compatibles necesitan el autoscalerRef correcto y Metrics Server/proveedor de métricas. Verifique que Flux/Helm no sobrescriba continuamente el control de escalado/Service de Flagger. Los PDB principalmente regulan desalojos voluntarios, no protección garantizada frente a reducción de escala del controlador o actualizaciones continuas de Deployment. Configure por separado la estrategia de rollout y la disponibilidad de la carga de trabajo.

### Flagger multicluster

![Un patrón de Flux central requiere autorización explícita de Kustomization remota; Flagger se ejecuta en cada cluster.](../.gitbook/assets/en-gitops-04-flagger-8.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-04-flagger-8.html)

Inicie Flux por cluster con rutas de Git distintas, o configure Flux central con kubeConfig/identidad de carga de trabajo explícitos para la reconciliación remota. Compartir un repositorio Git no concede acceso remoto. Flagger controla las cargas de trabajo localmente en cada cluster.

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: podinfo-production-a
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: flagger-demo
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./apps/podinfo/overlays/production-a
  prune: true
```

Este objeto se ejecuta en la instancia de Flux del clúster de destino. Evite que dependa de sí mismo y no espere que dependsOn encuentre un objeto del mismo nombre en otro clúster independiente. Incluso con Kustomizations remotas distintas en un mismo plano de control, Ready no demuestra por sí solo la promoción de la revisión actual. Condicione el cambio en Git del siguiente entorno a los resultados reales de la entrega.

Configure etiquetas de cluster y retención para la observabilidad centralizada. Las alertas/MetricTemplates con namespace por sí solas no completan el aislamiento de tenants; restrinja también RBAC, referencias entre namespaces, redes y acceso a Secret.

## Referencias

- [Código fuente de Flagger 1.45.0](https://github.com/fluxcd/flagger/tree/v1.45.0)
- [Estrategias de despliegue](https://github.com/fluxcd/flagger/blob/v1.45.0/docs/gitbook/usage/deployment-strategies.md)
- [Contrato de Webhook](https://github.com/fluxcd/flagger/blob/v1.45.0/docs/gitbook/usage/webhooks.md)
- [Registrador real de métricas](https://github.com/fluxcd/flagger/blob/v1.45.0/pkg/metrics/recorder.go)
- [Comportamiento del controlador y reversión](https://github.com/fluxcd/flagger/blob/v1.45.0/pkg/controller/scheduler.go)
- [Ejemplos de Gateway API](https://github.com/fluxcd/flagger/blob/v1.45.0/docs/gitbook/tutorials/gatewayapi-progressive-delivery.md)
- [Fin de soporte de AWS App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)
- [Interrupciones / PDB de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [FluxCD](02-fluxcd.md)
- [Gestión de tráfico de Argo Rollouts](argocd/05-traffic-management.md)

[Anterior: Comparación de GitOps](03-gitops-comparison.md) · [Siguiente: Feature Flags](05-feature-flags.md) · [Descripción general](README.md)

## Cuestionario

Compruebe sus conocimientos con el [cuestionario de Flagger](../quizzes/gitops/04-flagger-quiz.md).
