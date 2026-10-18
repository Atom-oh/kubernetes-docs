# Gestión del tráfico con Argo CD

> **Versiones de referencia**: Argo CD 3.5.2, Argo Rollouts 1.10.0 y chart de Helm 2.43.1. Tras revisar las notas de las versiones, se actualizaron las referencias a Argo CD 3.5.4 y al chart 2.43.6, manteniendo Rollouts 1.10.0. Los ejemplos no se volvieron a ejecutar.
> **Última actualización**: 12 de octubre de 2026

## Índice
- [Descripción general de Argo Rollouts](#argo-rollouts-overview)
- [Instalación](#installation)
- [Despliegues blue-green](#blue-green-deployments)
- [Despliegues canary](#canary-deployments)
- [Análisis y verificación](#analysis-and-verification)
- [Integración con Ingress](#ingress-integration)
- [Estrategias de reversión](#rollback-strategies)
- [Experimentos](#experiments)
- [Notificaciones](#notifications)

## Descripción general de Argo Rollouts {#argo-rollouts-overview}

Argo Rollouts es un controlador de Kubernetes que incorpora despliegues blue-green, despliegues canary y otras funciones de entrega progresiva.

### ¿Por qué Argo Rollouts?

Los Deployment de Kubernetes admiten RollingUpdate y Recreate, además de pausar y reanudar un despliegue. La tabla compara el comportamiento de los controladores nativos; otros controladores o una combinación de varios Deployment pueden implementar patrones adicionales:

| Función | Deployment de Kubernetes | Argo Rollouts |
|---------|----------------|---------------|
| Actualización gradual | Sí | Sí |
| Blue-green | No | Sí |
| Canary | No | Sí |
| Distribución del tráfico | No | Sí |
| Reversión automática | No | Sí |
| Análisis y verificación | No | Sí |
| Pausa y reanudación | Sí | Sí |
| Experimentos | No | Sí |

### Arquitectura

![El controlador de Argo Rollouts ejecuta estrategias blue-green, canary y de experimentos; distribuye el tráfico mediante el controlador de Ingress y la malla de servicios, y consulta a un proveedor de análisis cuyo resultado permite avanzar, abortar o pausar el despliegue.](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-0.html)

## Instalación {#installation}

### Instalar el controlador de Argo Rollouts

```bash
set -euo pipefail
ROLLOUTS_VERSION=v1.10.0
kubectl create namespace argo-rollouts --dry-run=client -o yaml | kubectl apply -f -
kubectl apply --server-side -n argo-rollouts \
  -f "https://github.com/argoproj/argo-rollouts/releases/download/${ROLLOUTS_VERSION}/install.yaml"
kubectl rollout status deployment/argo-rollouts -n argo-rollouts --timeout=180s
```

### Instalar el plugin de kubectl

```bash
set -euo pipefail
ROLLOUTS_VERSION=v1.10.0
case "$(uname -s)" in
  Linux) plugin_os=linux ;;
  Darwin) plugin_os=darwin ;;
  *) echo "Use the Windows release asset for Windows" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64) plugin_arch=amd64 ;;
  aarch64|arm64) plugin_arch=arm64 ;;
  *) echo "Unsupported architecture" >&2; exit 1 ;;
esac
plugin_asset="kubectl-argo-rollouts-${plugin_os}-${plugin_arch}"
plugin_dir="$(mktemp -d)"
trap 'rm -rf "$plugin_dir"' EXIT
plugin_base="https://github.com/argoproj/argo-rollouts/releases/download/${ROLLOUTS_VERSION}"
curl --fail --location --retry 3 "$plugin_base/$plugin_asset" -o "$plugin_dir/$plugin_asset"
curl --fail --location --retry 3 "$plugin_base/argo-rollouts-checksums.txt" -o "$plugin_dir/checksums.txt"
awk -v artifact="$plugin_asset" '$2 == artifact { print }' "$plugin_dir/checksums.txt" > "$plugin_dir/selected.sha256"
test -s "$plugin_dir/selected.sha256"
(
  cd "$plugin_dir"
  if [ "$plugin_os" = darwin ]; then
    shasum -a 256 -c selected.sha256
  else
    sha256sum -c selected.sha256
  fi
)
install -d "$HOME/.local/bin"
install -m 0755 "$plugin_dir/$plugin_asset" "$HOME/.local/bin/kubectl-argo-rollouts"
export PATH="$HOME/.local/bin:$PATH"
kubectl argo rollouts version
```

### Instalar mediante Helm

Elija uno de los dos métodos para gestionar el controlador: la instalación mediante manifiestos anterior o Helm. Guarde estos ajustes en `rollouts-values.yaml`. `AWS_REGION` corresponde al **controlador de Rollouts** que consulta CloudWatch; puede omitirse si no utiliza ese proveedor.

```yaml
controller:
  replicas: 2
  metrics:
    enabled: true
    serviceMonitor:
      enabled: false  # Enable after installing/configuring Prometheus Operator
  pdb:
    enabled: true
    minAvailable: 1
  extraEnv:
    - name: AWS_REGION
      value: ap-northeast-2

dashboard:
  enabled: false
```

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm upgrade --install argo-rollouts argo/argo-rollouts \
  --version 2.43.6 --namespace argo-rollouts --create-namespace \
  --values rollouts-values.yaml --wait --timeout 5m
```

Habilite ServiceMonitor cuando estén configurados su CRD y los selectores de Prometheus. Si comparte el panel, añada una capa de autenticación y autorización. El comando `dashboard` de la CLI 1.10.0 escucha en todas las interfaces y utiliza los privilegios de su kubeconfig; que muestre una URL de localhost no limita el acceso.

### Acceso al panel con una instalación de Helm

En una instalación de Helm, habilite el panel de solo lectura con un Service ClusterIP y reenvíe su puerto a una dirección local de loopback:

```bash
helm upgrade --install argo-rollouts argo/argo-rollouts \
  --version 2.43.6 --namespace argo-rollouts --create-namespace \
  --values rollouts-values.yaml \
  --set dashboard.enabled=true --set dashboard.readonly=true \
  --set dashboard.service.type=ClusterIP --set dashboard.ingress.enabled=false \
  --wait --timeout 5m
kubectl port-forward --address 127.0.0.1 -n argo-rollouts \
  service/argo-rollouts-dashboard 3100:3100
```

Abra `http://127.0.0.1:3100/rollouts`. Para compartir el acceso, utilice un proxy independiente que autentique a los usuarios y compruebe sus permisos.

## Despliegues blue-green {#blue-green-deployments}

Sustituya las imágenes y el registro de ejemplo de `myapp`, la cuenta y la etiqueta de ECR, y los nombres de las métricas por los de su aplicación. Prepare los espacios de nombres, el acceso a las imágenes, las respuestas de las sondas de disponibilidad, la recopilación de métricas y los AnalysisTemplate. Ejecute cada escenario por separado. En el despliegue inicial no existe un ReplicaSet estable anterior: despliegue v1 correctamente y después cambie la imagen a v2 en Git para observar el proceso de actualización.

Argo CD aplica la especificación del Rollout desde Git. El controlador de Rollouts, que es independiente, gestiona los ReplicaSet y el tráfico. Abortar el despliegue y devolver el tráfico a la versión estable no revierte el commit de Git ni una migración de la base de datos.

En un despliegue blue-green se conservan el ReplicaSet anterior y el nuevo del Rollout, y después se cambia el selector del Service activo. Esto no duplica todo el entorno del clúster. La propagación de los cambios en el plano de datos y el vaciado de las conexiones requieren tiempo.

### Rollout blue-green básico

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  replicas: 5
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myregistry/myapp:v1.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
  strategy:
    blueGreen:
      activeService: myapp-active
      previewService: myapp-preview
      autoPromotionEnabled: false
      previewReplicaCount: 2
      prePromotionAnalysis:
        templates:
        - templateName: smoke-tests
        args:
        - name: service-name
          value: myapp-preview
      postPromotionAnalysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: myapp-active
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-active
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-preview
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
```

`previewReplicaCount` limita las réplicas de la versión de vista previa; el nuevo ReplicaSet aumenta hasta `spec.replicas` antes de promoverse. `autoPromotionSeconds` se ignora cuando autoPromotionEnabled es false. El ejemplo que exige un análisis previo a la promoción también omite autoPromotionSeconds, por lo que se mantiene separado del ejemplo de promoción automática por tiempo. Se omite scaleDownDelaySeconds para evitar que un plazo fijo de reducción de réplicas cancele el análisis posterior a la promoción. El registro y la retirada de destinos del ALB, junto con el vaciado de conexiones, todavía pueden causar interrupciones; compruebe el comportamiento real del plano de datos.

### Flujo de un despliegue blue-green

![Antes del cambio blue-green, el balanceador envía el tráfico a Blue v1.0.0 mientras Green v2.0.0 espera como versión de vista previa. Después, el selector del Service activo pasa a Green v2.0.0 y se reducen las réplicas de Blue v1.0.0 según los ajustes del análisis y del período de espera.](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-1.html)

### Blue-green con promoción automática

```yaml
strategy:
  blueGreen:
    activeService: myapp-active
    previewService: myapp-preview
    autoPromotionEnabled: true
    autoPromotionSeconds: 60  # Wait 60s before auto-promoting
    previewReplicaCount: 3
```

## Despliegues canary {#canary-deployments}

`setWeight` cambia los pesos relativos del enrutador cuando se configura trafficRouting. Sin un enrutador, se aproxima la proporción mediante el número de réplicas de los ReplicaSet, sin garantizar un porcentaje exacto de solicitudes. Con un enrutador, la capacidad de la versión estable es independiente del peso de tráfico asignado.

Un despliegue canary dirige gradualmente el tráfico a la nueva versión.

Los despliegues canary con enrutamiento de tráfico mantienen, de forma predeterminada, el 100 % de la capacidad de la versión estable. Planifique la capacidad de ambas versiones conjuntamente. maxSurge controla el cálculo del número deseado de réplicas en un canary básico sin trafficRouting; con enrutamiento de tráfico, no establece un límite para el total de pods. maxUnavailable sí puede limitar la reducción de réplicas del ReplicaSet anterior.

### Rollout canary básico

Este ejemplo requiere el plugin Gateway API 0.17.0, el HTTPRoute `myapp-route`, un Gateway disponible y los Service de las versiones estable y canary correspondientes, que se muestran más adelante. Compruebe las condiciones Accepted y ResolvedRefs del HTTPRoute, así como la disponibilidad del plano de datos.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp-canary
  namespace: myapp
spec:
  replicas: 10
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myregistry/myapp:v1.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
  strategy:
    canary:
      canaryService: myapp-canary
      stableService: myapp-stable
      trafficRouting:
        plugins:
          argoproj-labs/gatewayAPI:
            httpRoute: myapp-route
            namespace: myapp
      steps:
      - setWeight: 5
      - pause:
          duration: 2m
      - setWeight: 10
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: myapp-canary
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 75
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency-check
          args:
          - name: service-name
            value: myapp-canary
      - setWeight: 100
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-stable
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-canary
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
```

### Explicación de los pasos canary

| Tipo de paso | Descripción |
|-----------|-------------|
| `setWeight` | Asigna al canary su porcentaje de tráfico |
| `pause` | Espera durante un período determinado o hasta recibir aprobación manual |
| `analysis` | Ejecuta un AnalysisTemplate |
| `setCanaryScale` | Establece el número de réplicas canary |
| `setHeaderRoute` | Enruta por cabecera cuando el proveedor de tráfico lo permite |

### Canary con aprobación manual

```yaml
strategy:
  canary:
    steps:
      - setWeight: 10
      - pause: {}  # Indefinite pause - requires manual promotion

      - setWeight: 50
      - pause: {duration: 10m}

      - setWeight: 100
```

Promueva el despliegue manualmente:

```bash
# Promote to next step
kubectl argo rollouts promote myapp-canary -n myapp

# Promote fully (skip remaining steps)
# Deliberate override only: skips remaining steps and analysis gates
# kubectl argo rollouts promote myapp-canary -n myapp --full
```

### Flujo de tráfico canary

![El balanceador distribuye las solicitudes con un peso relativo de 90 al Service estable, que tiene 10 pods, y de 10 al Service canary, que tiene 1 pod. Corresponde al paso del 10 % del ejemplo con la política de capacidad predeterminada para el enrutamiento de tráfico.](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-2.html)

## Análisis y verificación {#analysis-and-verification}

Los AnalysisTemplate definen cómo comprobar el estado del despliegue.

Las métricas http_requests_total/http_request_duration_seconds_bucket y las etiquetas service/version requieren instrumentar la aplicación y configurar la recopilación de métricas. Sustituya prometheus.monitoring.svc.cluster.local:9090 por el Service real. Los umbrales y las ventanas son orientativos; defina también el tráfico mínimo necesario y los requisitos del SLO.

failureLimit indica cuántas **mediciones fallidas** se toleran: un valor de 3 se supera con la cuarta medición fallida. Los errores del proveedor se controlan con consecutiveErrorLimit, y los resultados indeterminados, con inconclusiveLimit. Las condiciones siguientes impiden que valores ausentes, vectores vacíos, NaN o Infinity superen la comprobación. count es el número de mediciones, no de solicitudes HTTP; las ventanas de consulta que se solapan no son muestras independientes.

### Análisis de Prometheus

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: myapp
spec:
  args:
  - name: service-name
  metrics:
  - name: success-rate
    interval: 1m
    count: 5
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] >= 0.95
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (sum(rate(
            http_requests_total{
              service="{{args.service-name}}",
              status=~"2.."
            }[5m]
          )) or vector(0)) /
          sum(rate(
            http_requests_total{
              service="{{args.service-name}}"
            }[5m]
          ))
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] < 0.95
    inconclusiveLimit: 0
```

### Análisis de latencia

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency-check
  namespace: myapp
spec:
  args:
  - name: service-name
  metrics:
  - name: p99-latency
    interval: 2m
    count: 3
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <
      500
    failureLimit: 2
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          histogram_quantile(0.99,
            sum(rate(
              http_request_duration_seconds_bucket{
                service="{{args.service-name}}"
              }[5m]
            )) by (le)
          ) * 1000
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      500
    inconclusiveLimit: 0
```

### Análisis web mediante un endpoint HTTP

El Service debe devolver una respuesta HTTP satisfactoria con el JSON `{"status":"OK"}`. Como jsonPath extrae la cadena de estado, compare directamente result, en lugar de result.status. Ajuste la condición al contrato de respuesta real.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: smoke-tests
  namespace: myapp
spec:
  args:
  - name: service-name
  metrics:
  - name: smoke-test
    interval: 30s
    count: 3
    successCondition: result == "OK"
    failureLimit: 1
    provider:
      web:
        url: http://{{ args.service-name }}.myapp.svc.cluster.local/health
        jsonPath: '{$.status}'
        timeoutSeconds: 10
    failureCondition: result != nil && result != "OK"
```

### Análisis de Datadog

Las fórmulas de Datadog v2 separan las consultas del campo de fórmula. Cree el Secret datadog con address/api-key/app-key en el mismo espacio de nombres que el AnalysisTemplate. asFloat(default(result, -1)) distingue la ausencia de datos de una tasa de error válida de cero y evita pasar nil a funciones con tipos definidos.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: datadog-success-rate
  namespace: myapp
spec:
  args:
  - name: service-name
  metrics:
  - name: error-rate
    interval: 5m
    count: 3
    successCondition: |
      let rate = asFloat(default(result, -1));
      !isNaN(rate) && !isInf(rate) && rate >= 0 && rate <= 1 && rate < 0.05
    failureLimit: 2
    provider:
      datadog:
        apiVersion: v2
        interval: 5m
        aggregator: sum
        secretRef:
          name: datadog
          namespaced: true
        queries:
          a: sum:http.requests{service:{{args.service-name}},status:5xx}.as_count()
          b: sum:http.requests{service:{{args.service-name}}}.as_count()
        formula: a / b
    failureCondition: |
      let rate = asFloat(default(result, -1));
      !isNaN(rate) && !isInf(rate) && rate >= 0 && rate <= 1 && rate >= 0.05
    inconclusiveLimit: 0
```

### Análisis mediante un Job

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: integration-tests
  namespace: myapp
spec:
  args:
  - name: service-url
  metrics:
  - name: integration-tests
    provider:
      job:
        spec:
          backoffLimit: 1
          template:
            spec:
              restartPolicy: Never
              containers:
              - name: test-runner
                image: myregistry/integration-tests:v1.0.0
                env:
                - name: TARGET_URL
                  value: '{{args.service-url}}'
                command:
                - /bin/sh
                - -ec
                - exec npm run test:integration
              automountServiceAccountToken: false
          activeDeadlineSeconds: 300
```

### ClusterAnalysisTemplate

Comparta plantillas de análisis entre espacios de nombres:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ClusterAnalysisTemplate
metadata:
  name: global-success-rate
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: success-rate
    interval: 1m
    count: 5
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] >= 0.95
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (sum(rate(
            http_requests_total{
              namespace="{{args.namespace}}",
              service="{{args.service-name}}",
              status=~"2.."
            }[5m]
          )) or vector(0)) /
          sum(rate(
            http_requests_total{
              namespace="{{args.namespace}}",
              service="{{args.service-name}}"
            }[5m]
          ))
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] < 0.95
    inconclusiveLimit: 0
```

## Integración con Ingress {#ingress-integration}

Argo Rollouts admite proveedores de tráfico nativos y extensiones mediante plugins. Para los proveedores que carecen de integración nativa, como Kong, se utiliza el **plugin Gateway API**.

| Proveedor | Integración | Notas |
|---|---|---|
| NGINX Ingress | Nativa (`trafficRouting.nginx`) | Modifica directamente la anotación `canary-weight` |
| AWS ALB | Nativa (`trafficRouting.alb`) | El puerto de backend del Ingress debe ser `use-annotation`; consulte los [resultados de verificación](#verification-results-on-eks) |
| Istio | Nativa (`trafficRouting.istio`) | Modifica directamente el VirtualService y el DestinationRule |
| SMI | Nativa (`trafficRouting.smi`) | El proyecto SMI prácticamente carece de mantenimiento; no se recomienda adoptarlo en proyectos nuevos |
| Ambassador, Apache APISIX, Traefik | Nativa | No se abordan en esta guía; consulte la [documentación oficial](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/) |
| **Kong** y otras implementaciones compatibles con Gateway API, como kgateway | **Plugin Gateway API** (`trafficRouting.plugins`) | No existe el campo nativo `trafficRouting.kong` |

### NGINX Ingress (instalaciones existentes)

El proyecto comunitario ingress-nginx se retiró en marzo de 2026. Esta sección sirve como referencia de migración para instalaciones existentes; los ejemplos nuevos utilizan Gateway API. Cada ejemplo de enrutamiento necesita los Service de las versiones estable y canary correspondientes en su espacio de nombres.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        nginx:
          stableIngress: myapp-ingress
          additionalIngressAnnotations:
            canary-by-header: X-Canary
            canary-by-header-value: 'true'
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 100
  replicas: 5
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myregistry/myapp:v2.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: myapp
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp-stable
            port:
              number: 80
```

### Ingress de AWS ALB {#aws-alb-ingress}

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        alb:
          ingress: myapp-ingress
          rootService: myapp-root
          servicePort: 80
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 100
  replicas: 5
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myregistry/myapp:v2.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: myapp
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/actions.myapp-root: |
      {
        "type": "forward",
        "forwardConfig": {
          "targetGroups": [
            {
              "serviceName": "myapp-stable",
              "servicePort": 80,
              "weight": 100
            },
            {
              "serviceName": "myapp-canary",
              "servicePort": 80,
              "weight": 0
            }
          ]
        }
      }
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp-root
            port:
              name: use-annotation
  ingressClassName: alb
```

> **Comprobación de la configuración del ALB**: Deben coincidir el rootService del Rollout (o stableService si se omite), el nombre de la anotación de acción y el nombre de backend del Ingress. El puerto de backend `name: use-annotation` selecciona la acción con pesos. Un puerto numérico selecciona un backend Service ordinario; según ese Service, la reconciliación puede fallar o producir un enrutamiento diferente. Compruebe los eventos del controlador y el ForwardConfig real con `aws elbv2 describe-rules`.

### Distribución del tráfico con Istio

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 100
  replicas: 5
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myregistry/myapp:v2.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-vsvc
  namespace: myapp
spec:
  hosts:
  - myapp.example.com
  gateways:
  - myapp-gateway
  http:
  - name: primary
    route:
    - destination:
        host: myapp-stable
        port:
          number: 80
      weight: 100
    - destination:
        host: myapp-canary
        port:
          number: 80
      weight: 0
```

### Plugin Gateway API (HTTPRoute) {#gateway-api-plugin-httproute}

Kong, kgateway y otras implementaciones compatibles utilizan el [plugin Gateway API](https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi), mantenido por argoproj-labs. Traefik también dispone de una integración nativa con TraefikService; para Gateway API puede utilizar este plugin. La guía toma como referencia el plugin 0.17.0, publicado el 1 de septiembre de 2026, que actualiza los pesos de backend del HTTPRoute. La compatibilidad con otros tipos de Route y con el enrutamiento por cabeceras depende de los CRD instalados y de la implementación. Compruebe el estado de la ruta y la distribución real de solicitudes.

El binario siguiente corresponde al **nodo Linux amd64 en el que se ejecuta el pod del controlador**. En arm64, utilice gatewayapi-plugin-linux-arm64 y la suma SHA256 `5221279f7bf2c9b2c0ff6ed7ff12718ecce1d4892f1ff5e5224bb723cfd0fd92`. Con Helm, gestione las mismas entradas en controller.trafficRouterPlugins. Si instaló mediante manifiestos, incorpórelas a los datos del ConfigMap existente y reinicie el controlador. El Role mostrado limita las actualizaciones de pesos del HTTPRoute a un espacio de nombres; revise los permisos adicionales antes de utilizar otros tipos de Route o crear rutas por cabecera.

Registre el plugin en el ConfigMap `argo-rollouts-config` para que el controlador descargue el binario al iniciarse:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argo-rollouts-config
  namespace: argo-rollouts
data:
  trafficRouterPlugins: |
    - name: argoproj-labs/gatewayAPI
      location: https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi/releases/download/v0.17.0/gatewayapi-plugin-linux-amd64
      sha256: 1904ca787d33107c140521899d61fff030ee75d99908bd175fca5a4647759061
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: argo-rollouts-gateway-api-plugin
  namespace: myapp
rules:
- apiGroups:
  - ''
  resources:
  - services
  verbs:
  - get
- apiGroups:
  - gateway.networking.k8s.io
  resources:
  - httproutes
  verbs:
  - get
  - list
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: argo-rollouts-gateway-api-plugin
  namespace: myapp
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: argo-rollouts-gateway-api-plugin
subjects:
- kind: ServiceAccount
  name: argo-rollouts
  namespace: argo-rollouts
```

El Rollout hace referencia al HTTPRoute mediante `trafficRouting.plugins`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  replicas: 5
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:v2.0.0
        ports:
        - containerPort: 8080
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        plugins:
          argoproj-labs/gatewayAPI:
            httpRoute: myapp-route
            namespace: myapp
      steps:
      - setWeight: 20
      - pause:
          duration: 1m
      - setWeight: 50
      - pause:
          duration: 1m
      - setWeight: 100
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: myapp-route
  namespace: myapp
spec:
  parentRefs:
  - name: myapp-gateway
  rules:
  - backendRefs:
    - name: myapp-stable
      kind: Service
      port: 80
      weight: 100
    - name: myapp-canary
      kind: Service
      port: 80
      weight: 0
```

En cada paso `setWeight`, el plugin actualiza directamente los dos valores `backendRefs[].weight` siguientes.

### Kong (mediante el plugin Gateway API)

Kong Ingress Controller (KIC) carece de integración nativa con Argo Rollouts y utiliza el plugin Gateway API anterior. La configuración siguiente corresponde a un KIC independiente que gestiona un plano de datos existente de Kong Gateway, sin Kong Operator. Este modo requiere la anotación unmanaged; los Gateway gestionados por Kong Operator tienen un ciclo de vida distinto:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: kong
  annotations:
    konghq.com/gatewayclass-unmanaged: "true"   # required: without it the Gateway stays stuck on "Waiting for controller"
spec:
  controllerName: konghq.com/kic-gateway-controller   # note: different from KIC's IngressClass controller string
```

Aplique después la configuración del [plugin Gateway API](#gateway-api-plugin-httproute) anterior; los YAML del Rollout y del HTTPRoute son idénticos.

### Resultados de verificación en EKS {#verification-results-on-eks}

La versión anterior de la guía informó de estos resultados con EKS 1.36, Rollouts 1.9.0, AWS Load Balancer Controller 3.2.1, Istio 1.30, KIC 3.5 y el plugin 0.16.0. No adjuntó los registros originales, el número de solicitudes, la duración de las mediciones ni los manifiestos ejecutados, por lo que esta revisión estática no pudo reproducirlos. Son observaciones históricas: no corresponden a pruebas nuevas de 1.10.0/0.17.0 ni garantizan transiciones instantáneas o sin interrupciones.

| Proveedor | Comprobación realizada | Resultado informado |
|---|---|---|
| NGINX | Cambio de la anotación `canary-weight` de 20→50→100 % | ✅ Confirmado: la proporción del tráfico observado con curl coincidió con el valor de la anotación |
| Istio | Cambio del peso del VirtualService de 20→50→100 % y retorno inmediato al 0 % al ejecutar `abort` | ✅ Confirmado: la proporción observada con curl coincidió con el peso y el tráfico volvió a la versión estable anterior justo después de abortar |
| AWS ALB | Cambio del peso de reenvío de la regla del listener, contrastado con el estado real de AWS mediante `aws elbv2 describe-rules` | ✅ Confirmado, con la condición de utilizar [`use-annotation`](#aws-alb-ingress) descrita anteriormente |
| Kong mediante el plugin Gateway API | Cambio de `HTTPRoute.backendRefs[].weight` y tráfico real a través del plano de datos de Kong | ✅ Confirmado, aunque es fácil configurar incorrectamente la anotación `gatewayclass-unmanaged` o el valor exacto de `controllerName`; consulte la sección anterior |

Cuando Argo CD gestione los recursos de enrutamiento, limite las exclusiones de diferencias a los campos que controla Rollouts: la anotación de acción del ALB correspondiente, los pesos de las rutas de Istio, los pesos de backend del HTTPRoute y el selector rollouts-pod-template-hash del Service. Evite excluir especificaciones completas o todos los campos de un gestor. Para conservar esos valores durante la sincronización también se necesita RespectIgnoreDifferences=true, cuya aplicación está limitada a recursos ya existentes.

## Estrategias de reversión {#rollback-strategies}

### Reversión automática cuando falla el análisis

```yaml
strategy:
  canary:
    steps:
      - setWeight: 10
      - analysis:
          templates:
            - templateName: success-rate
          args:
            - name: service-name
              value: myapp-canary
    # Analysis failure automatically triggers rollback
```

### Reversión manual

```bash
# Abort current rollout and rollback
kubectl argo rollouts abort myapp -n myapp

# Undo to previous version
kubectl argo rollouts undo myapp -n myapp

# Undo to specific revision
kubectl argo rollouts undo myapp -n myapp --to-revision=2
```

Abortar devuelve el tráfico a la versión estable, pero no cambia la plantilla de pod deseada. undo modifica la plantilla del recurso activo; si Argo CD gestiona la carga de trabajo, también debe revisar y aplicar el cambio correspondiente en Git para que la autocorrección no restaure la revisión defectuosa. Ninguna de estas operaciones revierte los efectos sobre la base de datos. Un resultado Inconclusive pausa el proceso para investigarlo; se diferencia de los estados Failed y Error.

### Configuración de la reversión

Este fragmento de especificación corresponde a un Rollout existente con trafficRouting. dynamicStableScale reduce la capacidad de la versión estable y puede exigir aumentarla de nuevo al abortar: ahorra recursos a costa de reducir la capacidad disponible para recuperarse. El análisis en línea solo bloquea ese paso; el análisis en segundo plano se configura en strategy.canary.analysis.

```yaml
spec:
  strategy:
    canary:
      abortScaleDownDelaySeconds: 30
      dynamicStableScale: true
      steps:
      - setWeight: 10
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: myapp-canary
```

## Experimentos {#experiments}

En 1.10.0, si terminan correctamente todos los análisis con `requiredForCompletion: true`, el Experiment puede finalizar antes de `duration`. Por tanto, duration no establece un período mínimo de validación. Compruebe los selectores de los Service y del enrutador para aislar el tráfico del experimento. Consulte el [análisis detallado](10-rollouts-experiment.md) para conocer las transiciones de estado y los períodos de espera antes de limpiar recursos.

Ejecute pruebas A/B con varias versiones simultáneamente.

> Para conocer la creación encadenada de recursos, las reglas de nombres, el aislamiento del tráfico y los resultados de AnalysisRun, consulte el [análisis detallado de los experimentos de Rollouts](10-rollouts-experiment.md).

**Requisitos previos:** Un Experiment no genera tráfico de usuario. Proporcione tráfico de prueba y recopilación de métricas, y exponga el valor `rollouts-pod-template-hash` del pod como etiqueta de métrica `rollouts_pod_template_hash`. La comparación siguiente utiliza, como ejemplo, un aumento de un punto porcentual en la tasa de error; no sustituye las pruebas de significación estadística ni la validación de un tamaño mínimo de muestra. La ausencia de datos mantiene el resultado en Inconclusive. `progressDeadlineSeconds` limita el tiempo para que el ReplicaSet esté disponible; no establece una espera antes del análisis.

Cree el AnalysisTemplate al que se hace referencia en el mismo espacio de nombres:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: compare-analysis
  namespace: myapp
spec:
  args:
  - name: baseline-hash
  - name: canary-hash
  metrics:
  - name: canary-error-rate-increase
    interval: 30s
    count: 5
    failureLimit: 0
    inconclusiveLimit: 0
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <=
      0.01
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >
      0.01
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (
            sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}",status=~"5.."}[5m]))
            or vector(0)
          ) / sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}"}[5m]))
          -
          (
            sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.baseline-hash }}",status=~"5.."}[5m]))
            or vector(0)
          ) / sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.baseline-hash }}"}[5m]))
  - name: canary-absolute-error-rate
    interval: 30s
    count: 5
    failureLimit: 0
    inconclusiveLimit: 0
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] < 0.05
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0.05
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (
            sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}",status=~"5.."}[5m]))
            or vector(0)
          ) / sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}"}[5m]))
```

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Experiment
metadata:
  name: myapp-experiment
  namespace: myapp
spec:
  duration: 1h
  progressDeadlineSeconds: 300
  templates:
  - name: baseline
    replicas: 2
    selector:
      matchLabels:
        app: myapp-experiment
        variant: baseline
    template:
      metadata:
        labels:
          app: myapp-experiment
          variant: baseline
      spec:
        containers:
        - name: myapp
          image: myregistry/myapp:v1.0.0
          ports:
          - containerPort: 8080
  - name: canary
    replicas: 2
    selector:
      matchLabels:
        app: myapp-experiment
        variant: canary
    template:
      metadata:
        labels:
          app: myapp-experiment
          variant: canary
      spec:
        containers:
        - name: myapp
          image: myregistry/myapp:v2.0.0
          ports:
          - containerPort: 8080
  analyses:
  - name: compare-metrics
    templateName: compare-analysis
    args:
    - name: baseline-hash
      value: '{{templates.baseline.podTemplateHash}}'
    - name: canary-hash
      value: '{{templates.canary.podTemplateHash}}'
    requiredForCompletion: true
```

## Notificaciones {#notifications}

Integre los eventos del despliegue con los sistemas de notificación.

### Configurar notificaciones en un Rollout existente

Incorpore el siguiente fragmento de metadatos a un Rollout existente; no constituye un manifiesto de recurso completo.

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-rollout-completed.slack: deployments
    notifications.argoproj.io/subscribe.on-rollout-aborted.slack: deployments
    notifications.argoproj.io/subscribe.on-analysis-run-failed.slack: alerts
```

### Activadores y plantillas de notificación

Configure argo-rollouts-notification-secret en el espacio de nombres del controlador, con slack-token, mediante su proceso de gestión de secretos. Los eventos integrados de Rollout seleccionan estos nombres de activador; el estado Degraded por sí solo no demuestra que se haya abortado un despliegue. Configure todos los activadores y las plantillas a los que se hace referencia, incluido el del fallo de análisis.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argo-rollouts-notification-configmap
  namespace: argo-rollouts
data:
  service.slack: |
    token: $slack-token
  trigger.on-rollout-completed: |
    - send: [rollout-completed]
  trigger.on-rollout-aborted: |
    - send: [rollout-aborted]
  template.rollout-completed: |
    message: |
      Rollout {{.rollout.metadata.name}} completed successfully!
      Revision: {{.rollout.status.currentPodHash}}
      Image: {{(index .rollout.spec.template.spec.containers 0).image}}
  template.rollout-aborted: |
    message: |
      Rollout {{.rollout.metadata.name}} was aborted!
      Reason: {{.rollout.status.message}}
  trigger.on-analysis-run-failed: |
    - send: [analysis-run-failed]
  template.analysis-run-failed: |
    message: |
      Analysis failed for Rollout {{.rollout.metadata.name}}. Inspect its AnalysisRun.
```

## Referencias

- [Argo Rollouts 1.10.0](https://github.com/argoproj/argo-rollouts/releases/tag/v1.10.0)
- [Semántica de análisis](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/docs/features/analysis.md)
- [Umbrales del controlador de análisis](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/analysis/analysis.go)
- [Implementación del proveedor CloudWatch](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/metricproviders/cloudwatch/cloudwatch.go)
- [Plugin Gateway API 0.17.0](https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi/releases/tag/v0.17.0)

## Cuestionario

Compruebe lo aprendido con el [cuestionario de gestión del tráfico con Argo CD](../../quizzes/gitops/argocd/05-traffic-management-quiz.md).
