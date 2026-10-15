# Gestión del tráfico de ArgoCD

> **Revisado con respecto a**: Argo CD 3.5.2, Argo Rollouts 1.10.0, Helm chart 2.43.1; actualizado a Argo CD 3.5.4 y chart 2.43.6 (aún Rollouts 1.10.0) tras revisar las notas de lanzamiento (ejemplos no ejecutados de nuevo)
> **Última actualización**: October 12, 2026

## Tabla de contenidos
- [Descripción general de Argo Rollouts](#argo-rollouts-overview)
- [Instalación](#installation)
- [Despliegues Blue-Green](#blue-green-deployments)
- [Despliegues Canary](#canary-deployments)
- [Análisis y verificación](#analysis-and-verification)
- [Integración de Ingress](#ingress-integration)
- [Estrategias de rollback](#rollback-strategies)
- [Experimentos](#experiments)
- [Notificaciones](#notifications)

## Descripción general de Argo Rollouts

Argo Rollouts es un controlador de Kubernetes que proporciona capacidades avanzadas de despliegue, incluidos despliegues blue-green, despliegues canary y funciones de entrega progresiva.

### ¿Por qué Argo Rollouts?

Los Deployment de Kubernetes admiten RollingUpdate y Recreate, así como pausa/reanudación. La tabla compara el comportamiento del controlador nativo; los controladores adicionales o varios Deployment pueden implementar otros patrones:

| Función | Deployment de K8s | Argo Rollouts |
|---------|----------------|---------------|
| Rolling Update | Sí | Sí |
| Blue-Green | No | Sí |
| Canary | No | Sí |
| División del tráfico | No | Sí |
| Rollback automatizado | No | Sí |
| Análisis/verificación | No | Sí |
| Pausa/reanudación | Sí | Sí |
| Experimentos | No | Sí |

### Arquitectura

![El controlador de Argo Rollouts ejecuta estrategias blue-green, canary y de experimentos, desplaza el tráfico mediante el controlador de Ingress y la service mesh, y consulta un proveedor de análisis cuyo resultado hace avanzar, aborta o pausa el rollout.](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-0.html)

## Instalación

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

Elija la instalación mediante manifiesto anterior o Helm para gestionar la propiedad del controlador. Guarde esta configuración como `rollouts-values.yaml`. `AWS_REGION` corresponde al **controlador de Rollouts** que consulta CloudWatch y puede omitirse si no se utiliza ese proveedor.

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

Habilite ServiceMonitor solo después de configurar su CRD y los selectores de Prometheus. Un Dashboard compartido requiere una capa independiente de autenticación/autorización. El comando `dashboard` de la CLI 1.10.0 se enlaza a todas las interfaces y usa los privilegios de su kubeconfig; la URL de localhost que imprime no restringe el acceso.

### Acceso al Dashboard (instalación con Helm)

Para las instalaciones con Helm, habilite el Dashboard ClusterIP de solo lectura y realice port-forward a una dirección de loopback:

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

Abra `http://127.0.0.1:3100/rollouts`. El acceso compartido requiere un proxy independiente autenticado y autorizado.

## Despliegues Blue-Green

Sustituya las imágenes de ejemplo `myapp`/registry, la cuenta/etiqueta de ECR y los nombres de métricas por la configuración de su aplicación. Prepare namespaces, acceso a las imágenes, respuestas de readiness, recopilación de métricas y AnalysisTemplates; ejecute cada escenario de forma independiente. Un despliegue inicial no tiene un ReplicaSet estable anterior. Despliegue correctamente v1 y, a continuación, cambie la imagen a v2 en Git para observar un rollout.

Argo CD aplica la especificación de Rollout desde Git; el controlador de Rollouts independiente gestiona los ReplicaSet y el tráfico. Abortar y devolver el tráfico a estable no revierte el commit de Git ni una migración de base de datos.

Blue-green conserva los ReplicaSet anterior y nuevo de un Rollout y después cambia el selector del Service activo. No duplica un entorno de clúster completo. La propagación del plano de datos y el drenaje de conexiones requieren tiempo.

### Rollout Blue-Green básico

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

`previewReplicaCount` limita la capacidad de preview; el nuevo ReplicaSet escala a `spec.replicas` antes de la promoción. `autoPromotionSeconds` se ignora cuando autoPromotionEnabled es false. El ejemplo de análisis previo a la promoción requerido también omite autoPromotionSeconds, con lo que se mantiene separado del ejemplo de promoción automática basada en tiempo. Este ejemplo omite scaleDownDelaySeconds, de modo que un plazo de reducción fijo no cancele el análisis posterior a la promoción. El registro/anulación del registro de destinos de ALB y el drenaje de conexiones aún pueden causar interrupciones; verifique el plano de datos real.

### Flujo Blue-Green

![Antes del cambio blue-green, el balanceador de carga envía tráfico a Blue v1.0.0 mientras Green v2.0.0 espera como preview; después del cambio, el selector del Service activo pasa a Green v2.0.0 y el Blue v1.0.0 anterior se reduce según la configuración de análisis y retraso.](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-1.html)

### Blue-Green con promoción automática

```yaml
strategy:
  blueGreen:
    activeService: myapp-active
    previewService: myapp-preview
    autoPromotionEnabled: true
    autoPromotionSeconds: 60  # Wait 60s before auto-promoting
    previewReplicaCount: 3
```

## Despliegues Canary

`setWeight` cambia los pesos relativos del router cuando se configura trafficRouting. Sin un router, aproxima la proporción mediante los recuentos de ReplicaSet; no se garantiza un porcentaje exacto de solicitudes. Con un router, la capacidad de réplicas estables es independiente del peso del tráfico.

El despliegue canary desplaza gradualmente el tráfico a la nueva versión.

Los canary con enrutamiento de tráfico mantienen el 100 % de la capacidad estable de forma predeterminada, por lo que debe planificar conjuntamente la capacidad estable y canary. maxSurge controla la aritmética de réplicas deseadas para canary básico sin trafficRouting; no es un límite total de Pod en modo de enrutamiento de tráfico. maxUnavailable aún puede limitar la reducción del ReplicaSet antiguo.

### Rollout Canary básico

Este ejemplo requiere el plugin Gateway API 0.17.0, el HTTPRoute `myapp-route`, un Gateway listo y los Service estable/canary coincidentes que se muestran más adelante. Compruebe HTTPRoute Accepted/ResolvedRefs y la disponibilidad del plano de datos.

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

### Explicación de los pasos Canary

| Tipo de paso | Descripción |
|-----------|-------------|
| `setWeight` | Establecer el porcentaje de tráfico para canary |
| `pause` | Esperar una duración o aprobación manual |
| `analysis` | Ejecutar AnalysisTemplate |
| `setCanaryScale` | Establecer el número de réplicas canary |
| `setHeaderRoute` | Enrutar por encabezado (para routers de tráfico) |

### Canary con controles manuales

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

Promover manualmente:

```bash
# Promote to next step
kubectl argo rollouts promote myapp-canary -n myapp

# Promote fully (skip remaining steps)
# Deliberate override only: skips remaining steps and analysis gates
# kubectl argo rollouts promote myapp-canary -n myapp --full
```

### Flujo de tráfico Canary

![Diagrama que muestra solicitudes de cliente divididas en el balanceador de carga: el peso relativo 90 se dirige al Service estable con 10 Pod y el peso 10 se dirige al Service canary con 1 Pod en el paso de 10 % del ejemplo bajo la política predeterminada de capacidad de enrutamiento de tráfico.](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-2.html)

## Análisis y verificación

Los AnalysisTemplates definen cómo verificar el estado del despliegue.

Las métricas http_requests_total/http_request_duration_seconds_bucket y las etiquetas de servicio/versión requieren instrumentación de la aplicación y configuración de scrape. Sustituya prometheus.monitoring.svc.cluster.local:9090 por el Service real. Los umbrales/ventanas son ilustrativos; defina también los requisitos mínimos de tráfico y SLO.

failureLimit cuenta las **mediciones fallidas** toleradas: un valor de 3 se supera con la cuarta medición fallida. Los errores del proveedor usan consecutiveErrorLimit y los resultados indeterminados usan inconclusiveLimit. Las condiciones a continuación evitan que los valores ausentes, vectores vacíos, NaN e Infinity superen el control. count es un número de mediciones, no un número de solicitudes HTTP; las ventanas de consulta superpuestas no son muestras independientes.

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

### Análisis web (endpoint HTTP)

El Service debe devolver una respuesta HTTP correcta con JSON `{"status":"OK"}`. jsonPath extrae la cadena de estado, por lo que debe comparar result directamente, no result.status. Ajuste la condición al contrato real de la respuesta.

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

Las fórmulas v2 de Datadog usan consultas y campos de fórmula independientes. Aprovisione el Secret datadog con address/api-key/app-key en este namespace de AnalysisTemplate. asFloat(default(result, -1)) distingue los datos ausentes de una tasa de error cero válida y evita pasar nil a funciones tipadas.

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

### Análisis basado en Job

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

Comparta plantillas de análisis entre namespaces:

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

## Integración de Ingress

Argo Rollouts admite proveedores de tráfico nativos y extensiones mediante plugins. Los proveedores sin integración nativa, como Kong, se admiten mediante el **plugin Gateway API** en su lugar.

| Proveedor | Integración | Notas |
|---|---|---|
| NGINX Ingress | Nativa (`trafficRouting.nginx`) | Manipula directamente la anotación `canary-weight` |
| AWS ALB | Nativa (`trafficRouting.alb`) | El puerto de backend de Ingress debe ser `use-annotation`; consulte los [resultados de verificación](#verification-results-on-eks) |
| Istio | Nativa (`trafficRouting.istio`) | Manipula directamente VirtualService/DestinationRule |
| SMI | Nativa (`trafficRouting.smi`) | El proyecto SMI está en la práctica sin mantenimiento; no se recomienda para adopciones nuevas |
| Ambassador, Apache APISIX, Traefik | Nativa | No se abordan en este documento; consulte la [documentación oficial](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/) |
| **Kong** y otras implementaciones compatibles con Gateway API (kgateway, etc.) | **Plugin Gateway API** (`trafficRouting.plugins`) | No existe un campo nativo `trafficRouting.kong` |

### NGINX Ingress (instalaciones existentes)

El ingress-nginx de la comunidad se retiró en marzo de 2026; esta es una referencia de migración para instalaciones existentes. Los ejemplos nuevos usan la ruta de Gateway API. Cada ejemplo de enrutamiento requiere los Service estable/canary coincidentes en su namespace.

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

### AWS ALB Ingress

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

> **Comprobación de configuración de ALB**: El rootService de Rollout (o stableService cuando se omite), el nombre de la anotación de acción y el nombre de backend de Ingress deben coincidir. El puerto de backend `name: use-annotation` selecciona la acción ponderada. Un puerto numérico selecciona en cambio un backend de Service normal; según ese Service, la reconciliación puede fallar o producir un enrutamiento diferente. Compruebe los eventos del controlador y el ForwardConfig real con `aws elbv2 describe-rules`.

### División de tráfico de Istio

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

### Plugin Gateway API (HTTPRoute)

Las rutas de Gateway API para Kong, kgateway y otras implementaciones compatibles utilizan el [plugin Gateway API](https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi) mantenido por argoproj-labs. Traefik también tiene una integración nativa de TraefikService; su ruta de Gateway API puede usar este plugin. Este capítulo usa el plugin 0.17.0, publicado el 2026-09-01. Actualiza los pesos de backend de HTTPRoute. Otros tipos de Route y el enrutamiento por encabezado dependen de los CRD instalados y de las capacidades de implementación; verifique el estado de la ruta y la distribución real de solicitudes.

El binario siguiente está destinado al **nodo Linux amd64 que ejecuta el Pod del controlador**. En arm64, use gatewayapi-plugin-linux-arm64 y SHA256 `5221279f7bf2c9b2c0ff6ed7ff12718ecce1d4892f1ff5e5224bb723cfd0fd92`. Para Helm, gestione las mismas entradas en controller.trafficRouterPlugins. Para instalaciones mediante manifiestos, incorpórelo a los datos existentes de ConfigMap y reinicie el controlador. El Role mostrado limita las actualizaciones de peso de HTTPRoute a un namespace; otros tipos de Route/la creación de rutas por encabezado necesitan una revisión de permisos adicional.

Instale el plugin registrándolo en el ConfigMap `argo-rollouts-config` para que el controlador descargue el binario al iniciarse:

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

En cada paso `setWeight`, el plugin actualiza directamente estos dos valores `backendRefs[].weight`.

### Kong (mediante el plugin Gateway API)

El Kong Ingress Controller (KIC) no tiene integración nativa con Argo Rollouts; utiliza el plugin Gateway API anterior. La configuración siguiente es para KIC independiente que gestiona un plano de datos de Kong Gateway existente sin Kong Operator. Esa configuración utiliza la anotación unmanaged; los Gateways gestionados por Kong Operator tienen un ciclo de vida diferente:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: kong
  annotations:
    konghq.com/gatewayclass-unmanaged: "true"   # required — without it the Gateway stays stuck on "Waiting for controller"
spec:
  controllerName: konghq.com/kic-gateway-controller   # note: different from KIC's IngressClass controller string
```

Desde aquí, aplique la misma configuración del [plugin Gateway API](#gateway-api-plugin-httproute) anterior; los YAML de Rollout y HTTPRoute son idénticos.

### Resultados de verificación en EKS

El documento anterior informó de estos resultados con EKS 1.36, Rollouts 1.9.0, AWS Load Balancer Controller 3.2.1, Istio 1.30, KIC 3.5 y plugin0.16.0. No se adjuntan logs sin procesar, recuentos de solicitudes, duración de las mediciones ni manifiestos ejecutados, por lo que esta revisión estática no pudo reproducir el informe. Estas son observaciones históricas, no resultados nuevos de 1.10.0/0.17.0 ni garantías de transiciones instantáneas sin tiempo de inactividad.

| Proveedor | Qué se comprobó | Resultado |
|---|---|---|
| NGINX | Transición de la anotación `canary-weight` 20→50→100 % | ✅ Confirmado: la proporción de tráfico curl en vivo coincidió con el valor de la anotación |
| Istio | Transición de peso de VirtualService 20→50→100 % y reversión inmediata a 0 % en `abort` | ✅ Confirmado: la proporción de curl coincidió con el peso y el tráfico volvió a la versión estable anterior justo después de abortar |
| AWS ALB | Transición del peso de reenvío de la regla de listener, verificada de forma cruzada con el estado de AWS en vivo mediante `aws elbv2 describe-rules` | ✅ Confirmado (pero requiere la salvedad de [`use-annotation`](#aws-alb-ingress) anterior) |
| Kong (plugin Gateway API) | Transición de `HTTPRoute.backendRefs[].weight` y tráfico real a través del plano de datos de Kong | ✅ Confirmado, aunque es fácil equivocarse con la anotación `gatewayclass-unmanaged` y el `controllerName` exacto (véase arriba) |

Cuando Argo CD gestiona recursos de enrutamiento, revise exclusiones de diff limitadas para campos propiedad de Rollouts: la anotación de acción ALB relevante, los pesos de ruta de Istio, los pesos de backend de HTTPRoute y el selector de Service rollouts-pod-template-hash. Evite ignorar especificaciones/gestores completos. Conservar valores durante sync también requiere RespectIgnoreDifferences=true y su limitación de recursos existentes.

## Estrategias de rollback

### Rollback automático ante un fallo de análisis

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

### Rollback manual

```bash
# Abort current rollout and rollback
kubectl argo rollouts abort myapp -n myapp

# Undo to previous version
kubectl argo rollouts undo myapp -n myapp

# Undo to specific revision
kubectl argo rollouts undo myapp -n myapp --to-revision=2
```

Abort devuelve el tráfico a estable, pero deja sin cambios la plantilla de Pod deseada. undo cambia la plantilla de Pod en vivo; una carga de trabajo gestionada por Argo CD también requiere un cambio de Git revisado para que la autocorrección no restaure la revisión defectuosa. Ninguna operación revierte los efectos en la base de datos. El análisis Inconclusive se pausa para su investigación; no es lo mismo que Failed/Error.

### Configuración de rollback

Este es un fragmento de especificación para un Rollout existente con trafficRouting. dynamicStableScale reduce la capacidad estable y puede requerir volver a escalarla al abortar; intercambia capacidad de recuperación por uso de recursos. Los bloques de análisis en línea solo bloquean este paso, mientras que el análisis de fondo se configura en strategy.canary.analysis.

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

## Experimentos

En 1.10.0, si todos los análisis `requiredForCompletion: true` tienen éxito, pueden finalizar un Experiment antes de `duration`. No trate duration como una ventana mínima de validación. Verifique explícitamente los selectores de Service/router para el aislamiento del tráfico del experimento. Consulte el [análisis detallado](10-rollouts-experiment.md) para las transiciones de estado y los retrasos de limpieza.

Ejecute pruebas A/B con varias versiones simultáneamente.

> Para conocer el comportamiento detallado (cadena de creación de recursos, reglas de nomenclatura, aislamiento del tráfico y veredictos de AnalysisRun), consulte el [análisis detallado de Experimentos de Rollouts](10-rollouts-experiment.md).

**Requisitos previos:** Un Experiment no genera tráfico de usuario. Proporcione tráfico de prueba y scraping, y exponga `rollouts-pod-template-hash` del Pod como la etiqueta de métrica `rollouts_pod_template_hash`. La comparación siguiente usa un aumento ilustrativo de un punto porcentual en la tasa de error; no sustituye las pruebas de significancia ni la validación de muestras mínimas. Los datos ausentes permanecen Inconclusive. `progressDeadlineSeconds` limita la disponibilidad de ReplicaSet, no un retraso antes del análisis.

Cree el AnalysisTemplate referenciado en el mismo namespace:

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

## Notificaciones

Integre los eventos de rollout con sistemas de notificación.

### Configurar notificaciones en un Rollout existente

Lo siguiente es un fragmento de metadata que debe fusionarse en un Rollout existente, no un manifiesto de recurso completo.

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-rollout-completed.slack: deployments
    notifications.argoproj.io/subscribe.on-rollout-aborted.slack: deployments
    notifications.argoproj.io/subscribe.on-analysis-run-failed.slack: alerts
```

### Triggers y plantillas de notificación

Configure argo-rollouts-notification-secret en el namespace del controlador con slack-token mediante su proceso de gestión de secretos. Los eventos de Rollout integrados seleccionan estos nombres de trigger; Degraded por sí solo no demuestra que un rollout fue abortado. Configure todos los triggers/plantillas referenciados, incluido el fallo de análisis.

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

Para comprobar lo que ha aprendido, pruebe el [cuestionario de gestión de tráfico de ArgoCD](../../quizzes/gitops/argocd/05-traffic-management-quiz.md).
