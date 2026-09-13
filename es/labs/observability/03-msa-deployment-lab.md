# Parte 3: Despliegue de MSA y canary

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

> **Dificultad**: Avanzado
> **Última actualización**: September 13, 2026
Despliegue cinco roles de Python ejecutables como cargas de trabajo (workloads) independientes. El [README de la aplicación](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application) define el código, la BD, la imagen y las entradas del chart. Los pagos y las notificaciones son sintéticos; no se realiza ningún cargo real ni se envía correo electrónico o SMS.

![Separate workloads, transactional outbox, SNS fanout and consumers](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-10.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-10.html)

## 1. Contratos compartidos de API y persistencia {#contracts}

| Solicitud/rol | Contrato |
|---|---|
| `POST /orders` | 201 + `id`; el pedido y el outbox se confirman juntos |
| `POST /payments` | 200 + `status: completed`; el mismo pedido/importe/método es idempotente |
| `GET /orders/{id}` | 200 + el mismo ID, o 404 |
| `notification` | Cola SQS propia, notificación sintética persistida |
| `analytics` | Cola SQS separada, resultado persistido independiente |

El contexto W3C atraviesa el HTTP del gateway/servicio y los límites de productor/consumidor. Una caída después de la publicación en el outbox pero antes de la marca en la BD provoca una reentrega, por lo que los consumidores deduplican los IDs de evento de forma transaccional. Esto no hace que los efectos externos de correo electrónico/pago sean exactamente una vez. No se incluye un manejo general de Idempotency-Key para el POST de pedidos.

Las métricas de la aplicación son `lab_http_requests_total` y `lab_http_request_duration_seconds`, etiquetadas por service/route/status/revision. Los logs JSON incluyen service/level/trace_id/span_id; los payloads de cliente/pago no son etiquetas de métricas.

## 2. Archivo de base de datos e imagen {#image-database}

Use la cuenta de runtime dedicada y el archivo de conexión privada de la Parte 1. Las rutas en el Pod son `/run/database-ca/global-bundle.pem` y `/run/database/connection.json`; monte el archivo de conexión y la CA pública de RDS por separado como Secret/ConfigMap.

```bash
cd examples/labs/observability/application
kubectl --context service create namespace msa --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context service -n msa create secret generic lab-database --from-file=connection.json="$LAB_STATE/runtime-pod-connection.json"
kubectl --context service -n msa create configmap lab-database-ca --from-file=global-bundle.pem="$LAB_STATE/global-bundle.pem"
docker buildx build --platform linux/amd64 \
  --tag "$IMAGE_REPOSITORY:$IMAGE_TAG" --push .
docker buildx imagetools inspect "$IMAGE_REPOSITORY:$IMAGE_TAG"
```
Use la versión inmutable seleccionada en la Parte 1. Actualice los Secrets existentes mediante el procedimiento de rotación de la organización, sin imprimir valores ni colocarlos en archivos del chart. El Dockerfile fija un digest base, el UID 10001 y un contexto de build acotado.

Los nodos `m6i.large` generados usan AMD64. Use un builder de Buildx con AMD64 o capaz de compilación multiplataforma y verifique `linux/amd64` en el manifiesto publicado antes del despliegue. La prueba de humo local en ARM64 de la auditoría no valida la compilación AMD64.

## 3. Instalar controladores y chart {#deployment}

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install keda kedacore/keda --version 2.20.2   --kube-context service -n keda --create-namespace -f "$LAB_STATE/helm-inputs/keda.yaml"
helm upgrade --install argo-rollouts argo/argo-rollouts --version 2.43.1   --kube-context service -n argo-rollouts --create-namespace
helm upgrade --install observability-lab ./chart --kube-context service -n msa   -f "$LAB_STATE/helm-inputs/application.yaml"
kubectl --context service -n msa get deployment,rollout,pods,svc,scaledobject
```
Verifique los cinco ServiceAccounts y los subjects de IRSA. El gateway no tiene rol de AWS; los publicadores acceden a SNS, los consumidores a sus propias colas y KEDA solo a los atributos de las colas. No configure rutas duplicadas de Pod Identity/IRSA en una misma carga de trabajo. El readiness comprueba la BD/el esquema, no la entrega correcta a SQS/IAM.

Las etiquetas del ServiceMonitor coinciden con el release de Prometheus del servicio y `honorLabels` preserva la etiqueta de servicio de la aplicación. Los managed node groups pueden ejecutar la línea base; añada Karpenter solo después de que su [guía separada](../../autoscaling/02-karpenter.md) verifique IAM/discovery/EC2NodeClass/AMI/taints.

![Deployment and observability across management/service scopes](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-0.html)

## 4. Verificar el procesamiento HTTP y asíncrono {#verify}

```bash
kubectl --context service -n msa port-forward svc/api-gateway 8080:8080
# Run in another terminal from the repository root:
BASE_URL=http://127.0.0.1:8080 LOAD_PROFILE=smoke   k6 run --no-usage-report examples/labs/observability/load-test/k6-scenario.js
```
Lea únicamente los IDs creados y valide el estado del pago sintético. Verifique la entrega independiente por cola y el incremento de los contadores de `/stats`/BD/logs de los consumidores. Notification y analytics usan colas separadas; consumidores compitiendo en una sola cola no proporcionarían fanout. Los mensajes fallidos/envenenados permanecen sin confirmar para la política de DLQ.

Compare el trace_id JSON de CloudWatch/Loki, los spans reales de Tempo y los IDs de exemplar de Prometheus. Instalar un collector no es una verificación de extremo a extremo.

## 5. Canary y propiedad de GitOps {#canary}


![Manual inspection, canary-only analysis, promotion or abort](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-1.html)
Un único Rollout es propietario de payment-service. Con cinco réplicas, el paso del 20% se basa en réplicas y no garantiza el 20% de las solicitudes reales. Genere tráfico hacia la nueva revisión durante la pausa manual, antes del análisis. Las consultas seleccionan `rollouts-pod-template-hash`, requieren al menos cinco solicitudes recientes y un 99% de éxito, y rechazan resultados vacíos/NaN/Inf/multi-serie.

Se probó la evaluación real de condiciones y PromQL de Rollouts 1.10.0, pero no se ejecutó la promoción en el clúster. Un abort no es un revert de Git ni una restauración de la imagen deseada. Para ArgoCD opcional, siga su [guía de instalación](../../gitops/argocd/01-installation.md), apunte a la ruta de chart real/revisión revisada de este repositorio y evite la propiedad simultánea mediante Helm directo. Referencie Secrets existentes en lugar de confirmarlos en el repositorio. Las sync waves de app-of-apps por sí solas no garantizan el readiness de los hijos.

### Practicar la pausa manual

Estos pasos usan Helm como propietario del estado deseado. Bajo GitOps, revise los cambios de imagen y la recuperación en Git y no mezcle escrituras directas de Helm. Instale el plugin correspondiente a su SO/CPU después de comprobar el binario y la suma de verificación de la [release de Argo Rollouts 1.10.0](https://github.com/argoproj/argo-rollouts/releases/tag/v1.10.0).

```bash
# ROLLOUTS_BINARY: checksum-verified binary for your OS/architecture.
: "${ROLLOUTS_BINARY:?Set the verified Argo Rollouts 1.10.0 binary path}"
mkdir -p "$HOME/.local/bin"
install -m 755 "$ROLLOUTS_BINARY" "$HOME/.local/bin/kubectl-argo-rollouts"
export PATH="$HOME/.local/bin:$PATH"
kubectl argo rollouts version --short
```

Confirme un Rollout estable y conserve sus valores completos antes de publicar una imagen AMD64 realmente revisada con una nueva etiqueta inmutable siguiendo el procedimiento de build de la Parte 3. La instalación inicial no tiene una revisión estable previa y no es este ejercicio de actualización. El chart comparte una única configuración de imagen entre todos los roles, por lo que cambiarla también actualiza los demás roles como Deployments ordinarios; solo payment sigue los pasos del Rollout.

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

Mantenga la vista de --watch en una terminal separada y deténgala con Ctrl+C cuando sea necesario. Ejecute el tráfico y los comandos de promote/abort en otra terminal.

Mientras esté en Paused, continúe con el tráfico de la sección 4 y verifique en Prometheus que al menos cinco solicitudes recientes llegaron a la nueva revisión de rollouts-pod-template-hash. La falta de tráfico o los fallos de consulta no son un éxito. Después de la inspección, avance la pausa manual como se indica abajo para que se ejecuten el AnalysisRun configurado y los pasos posteriores. No use --full: omite el análisis y las pausas.

```bash
kubectl argo rollouts promote payment-service --context service -n msa
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
kubectl --context service -n msa get analysisruns
```

Si ocurre un problema, haga abort en lugar de promover y luego restaure la imagen deseada mediante los valores completos originales. El abort por sí solo no restaura spec.template ni Git.

```bash
kubectl argo rollouts abort payment-service --context service -n msa
helm upgrade observability-lab ./chart --kube-context service -n msa \
  -f "$LAB_STATE/helm-inputs/application.yaml"
kubectl argo rollouts get rollout payment-service --context service -n msa --watch
```

Tras una promoción exitosa, conserve el overlay de imagen aprobado en los comandos de Helm posteriores o incorpórelo a sus valores deseados gestionados. Preserve la evidencia del análisis de fallos e inspeccione el estado final. Esta auditoría verificó las sumas de verificación/la ayuda de la CLI y la lógica del chart/análisis; no ejecutó estos comandos de actualización/promote/abort en el clúster.

Continúe con la [Parte 4](./04-load-testing-scaling-lab.md). Siga la [Parte 6](./06-distributed-tracing-lab.md#cleanup) para una limpieza que tenga en cuenta la propiedad y las dependencias.

## Alcance de la validación

Las comprobaciones cubrieron SQLite/PostgreSQL local, tres servicios HTTP, la correlación de OTel, los stubs del SDK de SNS/SQS, la prueba de humo del contenedor, Helm/CRD y las condiciones de PromQL/Argo. No se ejercitaron TLS real de Aurora, EKS/IRSA, el fanout de SNS, KEDA/Karpenter ni las divisiones de tráfico canary.
