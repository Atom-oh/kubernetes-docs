# Parte 3: despliegue de MSA y canary

<span id="application-structure"></span>
<span id="architecture-overview"></span>
<span id="canary-state-diagram"></span>
<span id="cleanup"></span>
<span id="exercise-1-msa-application-overview"></span>
<span id="exercise-2-karpenter-nodepool-configuration"></span>
<span id="exercise-3-keda-scaledobject-configuration"></span>
<span id="exercise-4-argocd-application-deployment"></span>
<span id="exercise-5-opentelemetry-auto-instrumentation"></span>
<span id="exercise-6-argo-rollouts-canary-deployment"></span>
<span id="exercise-7-intentional-failure-and-automatic-rollback"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="prerequisites"></span>
<span id="references"></span>
<span id="repository-structure"></span>
<span id="sample-code-snippets"></span>
<span id="service-call-flow"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="summary"></span>
<span id="troubleshooting"></span>
<span id="verification"></span>
<span id="verification-1"></span>
<span id="verification-2"></span>
<span id="verification-3"></span>
<span id="verification-4"></span>
<span id="verification-5"></span>

> **Dificultad**: avanzada
> **Última actualización**: 16 de octubre de 2026
Despliega cinco roles ejecutables en Python como cargas de trabajo independientes. El [README de la aplicación](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application) define las entradas de código, base de datos, imagen y chart. Los pagos y las notificaciones son sintéticos: no se realiza ningún cargo real ni se envía correo electrónico o SMS.

![Cargas de trabajo independientes, outbox transaccional, distribución fanout de SNS y consumidores](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-10.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-10.html)

## 1. Contratos compartidos de API y persistencia {#contracts}

| Solicitud/rol | Contrato |
|---|---|
| `POST /orders` | 201 + `id`; el pedido y el outbox se confirman en la misma transacción |
| `POST /payments` | 200 + `status: completed`; la misma combinación de pedido/importe/método es idempotente; los valores en conflicto devuelven 409 |
| `GET /orders/{id}` | 200 + el mismo ID, o 404 |
| `notification` | Cola SQS propia y notificación sintética persistida |
| `analytics` | Cola SQS independiente y resultado independiente persistido |

El contexto W3C atraviesa los límites HTTP entre gateway y servicio, y entre productor y consumidor. Si el proceso falla después de publicar el outbox pero antes de registrar esa publicación en la base de datos, el mensaje se entrega de nuevo; por eso, los consumidores deduplican transaccionalmente los IDs de evento. Esto no garantiza que los efectos externos de correo o pago ocurran exactamente una vez. No se incluye un manejo general de `Idempotency-Key` para las solicitudes POST de pedidos.

Las métricas de la aplicación son `lab_http_requests_total` y `lab_http_request_duration_seconds`, etiquetadas por servicio, ruta, estado y revisión. Los registros JSON incluyen service/level/trace_id/span_id; los datos de clientes y pagos no se usan como etiquetas de métricas.

## 2. Archivo de base de datos e imagen {#image-database}

Usa la cuenta de ejecución dedicada y el archivo de conexión privada de la parte 1. Las rutas dentro del Pod son `/run/database-ca/global-bundle.pem` y `/run/database/connection.json`; monta el archivo de conexión y la CA pública de RDS por separado como Secret y ConfigMap.

```bash
cd examples/labs/observability/application
kubectl --context service create namespace msa --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context service -n msa create secret generic lab-database --from-file=connection.json="$LAB_STATE/runtime-pod-connection.json"
kubectl --context service -n msa create configmap lab-database-ca --from-file=global-bundle.pem="$LAB_STATE/global-bundle.pem"
docker buildx build --platform linux/amd64 \
  --tag "$IMAGE_REPOSITORY:$IMAGE_TAG" --push .
docker buildx imagetools inspect "$IMAGE_REPOSITORY:$IMAGE_TAG"
```
Usa la versión inmutable seleccionada en la parte 1. Actualiza los Secrets existentes mediante el procedimiento de rotación de la organización, sin imprimir sus valores ni incluirlos en archivos del chart. El Dockerfile fija el digest de la imagen base, el UID 10001 y un contexto de compilación acotado.

Los nodos `m6i.large` generados usan AMD64. Usa un builder de Buildx con AMD64 o capaz de compilar para varias plataformas y verifica `linux/amd64` en el manifiesto publicado antes del despliegue. La prueba de humo local en ARM64 de esta auditoría no valida la compilación para AMD64.

## 3. Instalar los controladores y el chart {#deployment}

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install keda kedacore/keda --version 2.20.2   --kube-context service -n keda --create-namespace -f "$LAB_STATE/helm-inputs/keda.yaml"
helm upgrade --install argo-rollouts argo/argo-rollouts --version 2.43.1   --kube-context service -n argo-rollouts --create-namespace
helm upgrade --install observability-lab ./chart --kube-context service -n msa   -f "$LAB_STATE/helm-inputs/application.yaml"
kubectl --context service -n msa get deployment,rollout,pods,svc,scaledobject
```
Verifica las cinco ServiceAccounts y los subjects de IRSA. El gateway no tiene un rol de AWS; los publicadores acceden a SNS, los consumidores a sus propias colas y KEDA solo consulta los atributos de las colas. No configures rutas duplicadas de Pod Identity e IRSA para una misma carga de trabajo. La comprobación de readiness valida la base de datos y el esquema, no la entrega correcta mediante SQS/IAM.

Las etiquetas de ServiceMonitor coinciden con el release de Prometheus del servicio y `honorLabels` conserva la etiqueta del servicio de la aplicación. Los grupos de nodos administrados pueden ejecutar la configuración base; añade Karpenter solo después de verificar IAM, el descubrimiento, EC2NodeClass, las AMI y las taints según su [guía independiente](../../autoscaling/02-karpenter.md).

![Despliegue y observabilidad en los ámbitos de administración y servicio](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-0.html)

## 4. Verificar el procesamiento HTTP y asíncrono {#verify}

```bash
kubectl --context service -n msa port-forward svc/api-gateway 8080:8080
# Run in another terminal from the repository root:
BASE_URL=http://127.0.0.1:8080 LOAD_PROFILE=smoke   k6 run --no-usage-report examples/labs/observability/load-test/k6-scenario.js
```
Lee únicamente los IDs creados y valida el estado del pago sintético. Verifica la entrega independiente a cada cola y que aumenten los contadores de `/stats`, la base de datos y los registros de los consumidores. Notification y analytics usan colas separadas; varios consumidores que compiten por una sola cola no proporcionan fanout. Los mensajes fallidos o poison quedan sin confirmar conforme a la política de DLQ.

Compara los trace_id de los registros JSON de CloudWatch/Loki, los spans reales de Tempo y los IDs de exemplars de Prometheus. Instalar un collector no constituye una verificación de extremo a extremo.

## 5. Despliegue canary y propiedad de GitOps {#canary}


![Inspección manual, análisis exclusivo de canary, promoción o cancelación](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-1.html)
Un único Rollout administra `payment-service`. Con cinco réplicas, el paso del 20 % se basa en el número de réplicas y no garantiza que el 20 % de las solicitudes reales llegue a la nueva versión. Antes del análisis, genera tráfico a la nueva revisión durante la pausa manual. Las consultas seleccionan `rollouts-pod-template-hash`, requieren al menos cinco solicitudes recientes y un 99 % de éxito, y rechazan resultados vacíos, NaN, Inf o con varias series.

Se probaron la evaluación real de condiciones de Rollouts 1.10.0 y las consultas PromQL, pero no se ejecutó la promoción en el clúster. Abortar no equivale a revertir Git ni restaura la imagen deseada. Si usas ArgoCD de forma opcional, sigue su [guía de instalación](../../gitops/argocd/01-installation.md), apunta a la ruta real del chart y a una revisión revisada de este repositorio, y evita que Helm directo y ArgoCD administren el mismo recurso a la vez. Haz referencia a Secrets existentes en lugar de confirmarlos en el repositorio. Las sync waves de app-of-apps por sí solas no garantizan que los recursos secundarios estén listos.

### Practicar la pausa manual

Estos pasos usan Helm como propietario del estado deseado. Con GitOps, revisa en Git los cambios de imagen y el procedimiento de recuperación; no mezcles escrituras directas de Helm. Instala el plugin correspondiente al sistema operativo y la arquitectura de CPU después de comprobar el binario y la suma de verificación de la [versión 1.10.0 de Argo Rollouts](https://github.com/argoproj/argo-rollouts/releases/tag/v1.10.0).

```bash
# ROLLOUTS_BINARY: checksum-verified binary for your OS/architecture.
: "${ROLLOUTS_BINARY:?Set the verified Argo Rollouts 1.10.0 binary path}"
mkdir -p "$HOME/.local/bin"
install -m 755 "$ROLLOUTS_BINARY" "$HOME/.local/bin/kubectl-argo-rollouts"
export PATH="$HOME/.local/bin:$PATH"
kubectl argo rollouts version --short
```

Confirma que el Rollout esté estable y conserva todos sus valores antes de publicar, con una nueva etiqueta inmutable, una imagen AMD64 que realmente se haya compilado y revisado mediante el procedimiento de compilación de la parte 3. La instalación inicial no tiene una revisión estable anterior, así que no corresponde a este ejercicio de actualización. El chart comparte una sola configuración de imagen entre todos los roles; cambiarla también actualiza los demás roles como Deployments normales. Solo el servicio de pagos sigue los pasos del Rollout.

```bash
# Run from examples/labs/observability/application.
: "${CANARY_IMAGE_TAG:?Set an actually built and reviewed immutable AMD64 image tag}"
# Keep the original application.yaml as the stable revision's complete values.
CANARY_VALUES="$LAB_STATE/helm-inputs/canary-image.yaml"
python3 - "$CANARY_VALUES" "$CANARY_IMAGE_TAG" <<'PYIMAGE'
import sys, json
with open(sys.argv[1], "w") as output:
    json.dump({"image": {"tag": sys.argv[2]}}, output)
PYIMAGE
helm upgrade observability-lab ./chart --kube-context service -n msa \
  -f "$LAB_STATE/helm-inputs/application.yaml" -f "$CANARY_VALUES"
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
```

Mantén la salida de `--watch` en una terminal aparte y detenla con Ctrl+C cuando sea necesario. Ejecuta el tráfico y los comandos de promoción o cancelación en otra terminal.

Mientras el Rollout esté en estado Paused, continúa el tráfico de la sección 4 y verifica en Prometheus que al menos cinco solicitudes recientes hayan llegado a la nueva revisión de `rollouts-pod-template-hash`. La falta de tráfico o los errores de consulta no indican éxito. Después de inspeccionar los resultados, avanza la pausa manual como se indica abajo para ejecutar el AnalysisRun configurado y los pasos siguientes. No uses `--full`: omite el análisis y las pausas.

```bash
kubectl argo rollouts promote payment-service --context service -n msa
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
kubectl --context service -n msa get analysisruns
```

Si surge un problema, cancela el Rollout en lugar de promoverlo y luego restaura la imagen deseada mediante el archivo original con todos los valores. Abortar por sí solo no restaura `spec.template` ni Git.

```bash
kubectl argo rollouts abort payment-service --context service -n msa
helm upgrade observability-lab ./chart --kube-context service -n msa \
  -f "$LAB_STATE/helm-inputs/application.yaml"
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
```

Después de una promoción correcta, conserva el overlay de la imagen aprobada en los siguientes comandos de Helm o incorpóralo a los valores deseados administrados. Conserva las pruebas del análisis de fallos e inspecciona el estado final. Esta auditoría verificó las sumas de comprobación y la ayuda de la CLI, además de la lógica del chart y del análisis; no ejecutó en el clúster los comandos de actualización, promoción o cancelación.

Continúa con la [parte 4](./04-load-testing-scaling-lab.md). Sigue la [parte 6](./06-distributed-tracing-lab.md#cleanup) para limpiar los recursos teniendo en cuenta su propiedad y dependencias.

## Alcance de la validación

Las comprobaciones abarcaron SQLite/PostgreSQL local, tres servicios HTTP, correlación de OTel, stubs de los SDK de SNS/SQS, pruebas de humo del contenedor, Helm/CRD y las condiciones de PromQL/Argo. No se probaron TLS real de Aurora, EKS/IRSA, la distribución fanout de SNS, KEDA/Karpenter ni las divisiones de tráfico canary.
