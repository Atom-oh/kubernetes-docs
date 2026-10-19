# Cuestionario de depuración avanzada de Amazon EKS {#amazon-eks-advanced-debugging-quiz}

> **Última actualización**: 12 de septiembre de 2026

El [capítulo de referencia](../../eks/11-eks-advanced-debugging.md) define las API vigentes, el alcance y las condiciones de seguridad. Los ejemplos no son resultados obtenidos en un clúster real ni pruebas de rendimiento. Durante esta revisión no se ejecutaron acciones en la nube ni en ningún clúster.

Este cuestionario evalúa su comprensión de las técnicas avanzadas de depuración de Amazon EKS: respuesta a incidentes, diagnóstico del plano de control, resolución de problemas de nodos, kubectl debug, consultas PromQL y observabilidad.

## Descripción general del cuestionario {#quiz-overview}
- Proceso de respuesta a incidentes
- Depuración del plano de control de EKS
- Resolución de problemas de nodos y kubelet
- Uso del comando kubectl debug
- Consultas PromQL y análisis de métricas
- Trazas distribuidas y análisis de registros

## Preguntas de opción múltiple {#multiple-choice-questions}

### 1. ¿Dónde se consultan normalmente los registros de auditoría habilitados del plano de control de EKS? {#1-where-are-enabled-eks-control-plane-audit-logs-normally-queried}

A. En un directorio /var/log/kubernetes administrado por el cliente
B. En Amazon CloudWatch Logs
C. Mediante acceso directo a etcd administrado
D. Con kubectl logs sobre un Pod del plano de control de AWS

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Amazon CloudWatch Logs**

Use `/aws/eks/<cluster-name>/cluster` en la región y cuenta correctas. Los cinco tipos disponibles son api, audit, authenticator, controllerManager y scheduler. Deben habilitarse de forma explícita; activarlos no reconstruye registros anteriores. Un 403 indica un problema de autorización, no necesariamente un fallo de autenticación de IAM. Ejecute la consulta por separado como Logs Insights QL y seleccione un intervalo de tiempo explícito.

```bash
# Read-only: confirm logging is enabled before searching the owned group.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.logging
```
```text
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

</details>

### 2. ¿Qué opción de kubectl debug solicita una copia independiente de un Pod? {#2-which-kubectl-debug-flag-requests-a-separate-copy-of-a-pod}

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. --copy-to**

La versión anterior de esta pregunta describía incorrectamente la adición de un contenedor al Pod original. --copy-to crea otro Pod. Añadir un contenedor efímero al Pod existente para depurarlo no utiliza esa opción ni una opción --ephemeral. --target solicita un espacio de nombres de procesos cuando el entorno de ejecución lo admite. La copia puede conservar la ServiceAccount, las referencias a variables de entorno y Secrets, los volúmenes y otros contenedores normales. Desactivar los contenedores de inicialización y cambiar un comando no convierte esa copia en una reproducción de datos aislada.

```bash
# MUTATION: separate reviewed reproduction Pod, not an ephemeral container in the original.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${DEBUG_POD_NAME:?Choose a new owned name}"; : "${DEBUG_IMAGE:?Reviewed image providing sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --share-processes=true --profile=general -- sleep 3600
```

</details>

### 3. Tras comprobar la condición y los latidos de un nodo NotReady, ¿qué evidencias son útiles? {#3-which-evidence-is-useful-after-checking-the-node-condition-and-heartbeat-for-a-notready-node}

A. Solo registros de aplicaciones no relacionadas
B. El estado y los registros aplicables de kubelet y del entorno de ejecución, correlacionados con evidencias de red y EC2
C. La manipulación directa de etcd administrado por AWS
D. Los registros de CoreDNS como única prueba

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. El estado y los registros aplicables de kubelet y del entorno de ejecución, correlacionados con evidencias de red y EC2**

No hay una frecuencia medida que respalde la antigua afirmación sobre «la causa más común». Ready=False, la pérdida de latidos o el estado Unknown, la presión de recursos y un fallo de instancia son señales distintas. Use acceso al host autorizado en nodos compatibles, NodeDiagnostic o el acceso de depuración documentado de Auto Mode. SSH y systemctl no sirven para todos los tipos de nodo. Recopile registros acotados antes de reiniciar o sustituir el nodo mediante un procedimiento revisado por separado.

```bash
# Read-only Kubernetes evidence first; no automatic kubelet restart.
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,nodeInfo:.status.nodeInfo,conditions:.status.conditions
}'
```

</details>

### 4. ¿Qué cálculo mide el uso de CPU de un contenedor respecto a un límite de CPU configurado y positivo? {#4-which-calculation-measures-container-cpu-use-relative-to-a-positive-configured-cpu-limit}

A. Una métrica supuesta cpu_usage >80
B. Segundos de CPU por segundo >0.8, sin denominador
C. Uso de CPU en núcleos / límite de CPU positivo del mismo contenedor, en núcleos
D. Una métrica supuesta container_cpu_percent

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. Uso de CPU en núcleos / límite de CPU positivo del mismo contenedor, en núcleos**

rate(cpu_usage_seconds_total) devuelve núcleos de CPU, no un porcentaje por sí sola. Combine las series según el alcance del clúster, el espacio de nombres, el Pod y el contenedor, usando los límites positivos correspondientes. Un contenedor sin límite o sin la serie del límite no tiene una utilización del 0 %. La utilización del HPA suele calcularse respecto a los recursos solicitados, lo que constituye otro cálculo. Estas consultas suponen el contrato de un único clúster, etiquetas y recopilación del capítulo de referencia, y muestran una fracción superior a 0,8.

```promql
(sum by (namespace,pod,container) (
  rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
)
/ on (namespace,pod,container)
max by (namespace,pod,container) (
  kube_pod_container_resource_limits{namespace="diagnostics-example",resource="cpu",unit="core"} > 0
)) > 0.8
```
```promql
(max by (namespace,pod,container) (container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"})
/ on (namespace,pod,container)
max by (namespace,pod,container) (kube_pod_container_resource_limits{namespace="diagnostics-example",resource="memory",unit="byte"} > 0)) > 0.8
```

</details>

### 5. ¿Qué herramienta no se usa normalmente para diagnosticar la red entre nodos en EKS administrado? {#5-which-is-not-the-normal-tool-for-customer-diagnosis-of-inter-node-networking-in-managed-eks}

A. tcpdump con captura autorizada
B. Wireshark para analizar una captura guardada y autorizada
C. Pruebas acotadas de curl o DNS desde una carga de trabajo
D. etcdctl contra el endpoint de etcd administrado por AWS

<details>
<summary>Ver respuesta</summary>

**Respuesta: D. etcdctl contra el endpoint de etcd administrado por AWS**

Los clientes no reciben un endpoint de acceso directo a etcd administrado. Esto no significa que etcdctl nunca pueda ayudar a diagnosticar la red de un sistema etcd autogestionado. La captura de paquetes necesita las capacidades y el contexto del host apropiados, un alcance limitado y un manejo privado de los datos. Un nuevo Pod de depuración puede seguir una política o ruta DNS distinta de la carga que falla. Un contador de tráfico no mide la latencia.

```bash
# Deliberate bounded request from an owned workload with curl installed.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${HEALTH_URL:?Set a reviewed safe health URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```

</details>

### 6. ¿Qué enfoque puede reducir el tiempo de detección sin limitarse a bajar todos los umbrales? {#6-which-approach-can-reduce-detection-delay-without-simply-lowering-every-threshold}

A. Únicamente más observación manual
B. Los umbrales más bajos posibles para todas las métricas
C. Alertas apropiadas basadas en mediciones, comprobaciones de cobertura y escalamiento
D. Solo una mayor retención de registros

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. Alertas apropiadas basadas en mediciones, comprobaciones de cobertura y escalamiento**

Ajuste las alertas a los SLO reales y a los modos de fallo. Los umbrales bajos pueden causar fatiga por alertas. El contador HTTP y las etiquetas de estado del ejemplo requieren instrumentación de la aplicación. Un denominador de solicitudes igual a cero o ausente no demuestra que todo funcione. Use el motivo de espera CrashLoopBackOff en lugar de interpretar cualquier reinicio como un bucle de fallos. Prometheus debe seleccionar la regla y el espacio de nombres; la entrega de notificaciones se comprueba por separado. Aquí no se midió ningún resultado de MTTD.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-quiz-alerts
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: reviewed-quiz-alerts
    rules:
    - alert: HighErrorRate
      expr: "(\n  sum(rate(http_requests_total{namespace=\"diagnostics-example\",job=\"\
        owned-app\",status=~\"5..\"}[5m]))\n  / sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m]))\n) > 0.05\nand on() (sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m])) > 0)"
      for: 2m
      labels:
        severity: critical
    - alert: PodCrashLooping
      expr: max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"}
        == 1)
      for: 5m
      labels:
        severity: warning
```

</details>

### 7. ¿Qué forma de comando crea un Pod de diagnóstico en un nodo? {#7-which-command-form-creates-a-diagnostic-pod-on-a-node}

A. `kubectl debug node/<node-name> --image=<reviewed-image>`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>Ver respuesta</summary>

**Respuesta: A. `kubectl debug node/<node-name> --image=<reviewed-image>`**

El perfil general probado monta /host y utiliza los espacios de nombres del host, pero establece privileged en false. El perfil sysadmin explícito concede privilegios más amplios. El funcionamiento de chroot, nsenter, las herramientas y SELinux depende de la plataforma y de los permisos. Crear el Pod modifica el clúster; no es una inspección pasiva. Un fallo de kubelet o del entorno de ejecución puede impedir que arranque. Registre el nombre y UID creados y use el procedimiento de limpieza revisado.

```bash
# MUTATION: creates a node diagnostic Pod; general is not automatically privileged.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${NODE_NAME:?}"; : "${NODE_DEBUG_IMAGE:?Reviewed image}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" \
  --image="$NODE_DEBUG_IMAGE" --profile=general --attach=false -- true
```

</details>

### 8. ¿Qué representa un span en las trazas distribuidas? {#8-what-does-a-span-represent-in-distributed-tracing}

A. Solo la duración total de la solicitud de extremo a extremo
B. Una unidad de trabajo con su duración y metadatos asociados
C. Solo la latencia de red
D. La marca de tiempo de un registro

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Una unidad de trabajo con su duración y metadatos asociados**

Un span puede describir una llamada HTTP, una operación de base de datos u otra unidad de trabajo. Los identificadores de traza asocian los spans; las relaciones entre padres e hijos y los enlaces representan trabajo relacionado. La propagación y el muestreo determinan qué se puede observar. Baggage es contexto propagado, no un atributo de span automático, y no debe contener secretos. El JSON siguiente es un registro ilustrativo y legible, no un mensaje OTLP transmitido ni una solicitud medida. Para configurar el Collector, use el ejemplo actual del capítulo de referencia, con v1beta1 y configuración como objeto, además de un backend y una ruta OTLP compatibles. La antigua receta del exportador jaeger y el puerto 14250 ya no es una guía vigente.

```json
{
  "exampleOnly": true,
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "parent_span_id": "fedcba9876543210",
  "name": "GET /api/products",
  "kind": "SERVER",
  "duration_ms": 85
}
```

</details>

### 9. Si CoreDNS se ejecuta mediante un Deployment, ¿qué evidencias ayudan a investigar errores de DNS? {#9-for-deployment-based-coredns-which-evidence-is-useful-when-investigating-dns-errors}

A. El estado y los registros de los Pods de CoreDNS dentro del alcance investigado, y comprobaciones del resolver de la carga de trabajo
B. Solo describe service kubernetes
C. Solo los metadatos del clúster de AWS
D. Solo la antigua lista de Endpoints

<details>
<summary>Ver respuesta</summary>

**Respuesta: A. El estado y los registros de los Pods de CoreDNS dentro del alcance investigado, y comprobaciones del resolver de la carga de trabajo**

No todas las consultas DNS se registran de forma predeterminada. Correlacione la configuración del resolver, el estado de los Pods y Services y los errores de los servidores DNS de destino. Un clúster compuesto únicamente por Auto Mode utiliza el DNS del sistema de los nodos; los clústeres mixtos conservan el Deployment para los nodos que no son Auto Mode. Pruebe desde el Pod y contenedor afectados cuando dispongan de herramientas, no desde un Pod no relacionado del espacio de nombres predeterminado con una imagen antigua. Las opciones de depuración de nslookup dependen de la herramienta y no son universales.

```bash
# Deployment-based CoreDNS only; use the Auto Mode path when applicable.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns --since=15m --tail=100
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```

</details>

### 10. ¿Qué comando muestra muestras recientes de recursos de los Pods desde la API de métricas de recursos? {#10-which-command-displays-recent-pod-resource-samples-from-the-resource-metrics-api}

A. kubectl describe pod
B. kubectl top pods
C. kubectl get pods -o wide
D. kubectl logs

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. kubectl top pods**

kubectl top necesita un proveedor funcional de metrics.k8s.io, habitualmente Metrics Server. Muestra muestras recientes de CPU y memoria, no una medición instantánea ni un historial. Que falten métricas no significa que el uso sea cero. Compare por separado las solicitudes y límites pertinentes y use un backend de monitorización para el análisis histórico.

```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --sort-by=memory
kubectl --context "$KUBE_CONTEXT" top nodes
```

</details>

## Preguntas de respuesta corta {#short-answer-questions}

### 1. ¿Cuál es el patrón del grupo de CloudWatch Logs para los registros habilitados del plano de control de EKS? {#1-what-is-the-cloudwatch-logs-group-pattern-for-enabled-eks-control-plane-logs}

<details>
<summary>Ver respuesta</summary>

**Respuesta:** `/aws/eks/<cluster-name>/cluster`. Los tipos de registro deben habilitarse para el clúster; hacerlo no reconstruye eventos anteriores. Seleccione la cuenta, región, grupo e intervalo de tiempo correctos. Ejecute por separado las siguientes consultas Logs Insights QL. Los nombres de usuario de auditoría son identidades registradas, no necesariamente el nombre corto del rol de IAM.

```sql
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @logStream not like /kube-apiserver-audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50
```

```sql
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_EXACT_AUDIT_USERNAME"
| sort @timestamp desc
| limit 100
```

</details>

### 2. ¿Es necesario habilitar la antigua opción EphemeralContainers en las versiones actuales de Kubernetes? {#2-does-current-kubernetes-require-enabling-the-old-ephemeralcontainers-feature-gate}

<details>
<summary>Ver respuesta</summary>

**Respuesta:** No. `EphemeralContainers` era la opción histórica de activación de la función, que pasó a beta en 1.23 y a estable en 1.25. En las versiones actuales, compruebe en cambio RBAC para `pods/ephemeralcontainers`, las políticas de admisión, el acceso a imágenes y la compatibilidad del entorno de ejecución. Añadir un contenedor modifica el Pod, y después su entrada no puede cambiarse ni eliminarse. La visibilidad de procesos con `--target` depende del entorno de ejecución. Reutilice el procedimiento de creación revisado de forma explícita en el capítulo de referencia. Este comando solo enumera metadatos.

```bash
# Read-only inventory; adding an ephemeral container is a separate mutation.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq '{
    uid:.metadata.uid,
    ephemeralContainers:[.spec.ephemeralContainers[]? | {name,image,targetContainerName}],
    ephemeralStatuses:.status.ephemeralContainerStatuses
  }'
```

</details>

### 3. ¿En qué se diferencian rate() e irate() en PromQL? {#3-how-do-rate-and-irate-differ-in-promql}

<details>
<summary>Ver respuesta</summary>

`rate()` estima el incremento de un contador por segundo durante el intervalo seleccionado, ajusta los reinicios y extrapola hasta los extremos del intervalo. `irate()` usa únicamente las dos últimas muestras de ese intervalo y ajusta los reinicios. Ambas necesitan suficientes muestras y ninguna detecta un pico que no se haya muestreado. Aplique la función antes de agregar las series para que los reinicios de cada una sigan siendo detectables. Normalmente se usa `rate()` para alertas; `irate()` puede ayudar a examinar contadores volátiles, pero no garantiza una mejor detección de incidentes. Son funciones para contadores, no derivadas genéricas de gauges. Los dos primeros ejemplos usan un contador de aplicación instrumentado; el último devuelve núcleos de CPU, no un porcentaje. Use un único clúster y el contrato de etiquetas y recopilación del capítulo de referencia.

```promql
sum by (namespace,service) (
  rate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
sum by (namespace,service) (
  irate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

</details>

### 4. ¿Dónde monta kubectl debug node el sistema de archivos del host y qué permite ese montaje? {#4-where-does-kubectl-debug-node-mount-the-host-filesystem-and-what-does-that-permit}

<details>
<summary>Ver respuesta</summary>

**Respuesta:** `/host`. El perfil `general` no concede privilegios automáticamente. Montar el host no garantiza que funcionen `chroot`, `systemctl` ni la lectura de archivos protegidos. La imagen debe contener las herramientas, y también influyen la admisión, las capacidades, SELinux, el sistema operativo y el estado del nodo. El perfil `sysadmin`, explícitamente privilegiado, necesita un procedimiento de diagnóstico autorizado por separado. Auto Mode admite los procedimientos documentados de depuración de nodos; el acceso SSH directo y las rutas habituales del host no son universales. Para crear y limpiar los recursos, consulte la pregunta 7 y el capítulo de referencia. No muestre archivos kubeconfig ni credenciales.


</details>

### 5. ¿Cómo se descompone el tiempo de recuperación de un incidente sin contar intervalos dos veces? {#5-how-can-incident-recovery-time-be-decomposed-without-double-counting}

<details>
<summary>Ver respuesta</summary>

Defina la convención antes de usar «MTTR»: algunos equipos empiezan a medir desde la detección y otros desde el inicio del incidente. Resolver, reparar y recuperar tienen significados distintos. Aquí se define `t0 = service impact starts` (inicio del impacto), `t1 = detected` (detección), `t2 = actionable diagnosis` (diagnóstico que permite actuar) y `t3 = service restored` (servicio restaurado). Los intervalos sin solapamiento son detección `t1−t0`, investigación `t2−t1` y restauración `t3−t2`; su suma es `t3−t0`. Al calcular los promedios de los mismos incidentes con estas definiciones, se conserva la suma. Un único incidente de 45 minutos es una duración, no una media demostrada. La confirmación de la causa raíz y el trabajo posterior pueden ocurrir después de restaurar el servicio; no fuerce todos los incidentes a seguir esa secuencia. Mejore la cobertura de monitorización, las guías de respuesta y los procedimientos de recuperación probados, y mida sus resultados reales.


</details>

## Ejercicios prácticos {#hands-on-exercises}

### 1. Encuentre contenedores de production cuyo incremento estimado de reinicios sea de al menos dos en cinco minutos. {#1-find-production-containers-with-an-estimated-restart-increase-of-at-least-two-in-five-minutes}

<details>
<summary>Ver respuesta</summary>

Use un único clúster y kube-state-metrics con etiquetas `namespace`, `pod`, `uid` y `container`. `increase()` trata los reinicios de contadores y extrapola, por lo que el resultado puede ser fraccionario y no constituye un registro completo de eventos. `max` evita sumar réplicas idénticas del exportador, pero no es una solución universal de deduplicación para alta disponibilidad. Compruebe la salud de la recopilación y la deduplicación del backend. Conserve el UID del Pod para distinguir las sustituciones que reutilizan el mismo nombre. Las variantes siguientes muestran un recuento acumulado >5, los diez **Pods** con mayor suma de incrementos de reinicios de sus contenedores durante una hora y la tasa de reinicios por segundo para una gráfica. Las series ausentes no equivalen a cero reinicios.

```promql
max by (namespace,pod,uid,container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2
```

```promql
max by (namespace,pod,uid,container) (
  kube_pod_container_status_restarts_total{namespace="production"}
) > 5
```

```promql
topk(10,
  sum by (namespace,pod,uid) (
    max by (namespace,pod,uid,container) (
      increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
    )
  )
)
```

```promql
max by (namespace,pod,uid,container) (
  rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])
)
```

</details>

### 2. Recopile evidencias acotadas de un contenedor en CrashLoopBackOff antes de modificar la carga de trabajo. {#2-collect-scoped-evidence-for-a-container-in-crashloopbackoff-before-changing-the-workload}

<details>
<summary>Ver respuesta</summary>

`CrashLoopBackOff` es un motivo de espera del contenedor; el Pod puede seguir en fase `Running`. Seleccione el contexto, espacio de nombres, Pod y contenedor afectados. Compruebe el UID actual antes de recopilar registros. Las llamadas de registro por nombre no son atómicas con la comprobación del UID. Empiece con la inspección acotada siguiente e investigue el código y motivo de salida, los errores de aplicación, las referencias de configuración, la presión del nodo y los fallos de dependencias. Los fallos de las sondas de arranque y de actividad (startup y liveness) pueden reiniciar un contenedor; la sonda de disponibilidad (readiness) por sí sola no lo hace. La falta de Secrets o datos de configuración también puede impedir la creación en lugar de causar un bucle de fallos. No muestre todas las variables de entorno, valores de Secrets ni archivos de configuración.

```bash
# Read-only, bounded evidence for one owned Pod and container.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE")
pod_state=$("${k[@]}" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid, phase:.status.phase, conditions:.status.conditions,
  containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
  initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
}')
printf '%s\n' "$pod_state"
pod_uid=$(jq -er '.uid' <<<"$pod_state")
"${k[@]}" get events --field-selector "involvedObject.uid=$pod_uid" \
  --sort-by='.metadata.creationTimestamp'
# These logs can contain sensitive application data; keep the terminal/evidence private.
# A missing previous instance/log is an evidence gap, not an empty successful result.
if ! "${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" --previous \
  --tail=100 --limit-bytes=65536 --timestamps; then
  printf '%s\n' 'Previous container log unavailable; retain this limitation.' >&2
fi
"${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=100 --limit-bytes=65536 --timestamps
```

Si necesita reproducir el problema, use la pregunta 2 y las instrucciones del capítulo solo después de revisar la identidad de la copia, sus referencias a Secrets, volúmenes, otros contenedores y efectos externos. Sustituir una imagen o comando y desactivar los contenedores de inicialización no aísla esos recursos. Prefiera una reproducción con datos depurados en un entorno apropiado, registre el nuevo nombre y UID y revise la limpieza por separado. Que un contenedor de depuración permanezca dormido no demuestra que la aplicación esté reparada.

</details>

### 3. Consulte los eventos 403 de auditoría de EKS de la última hora y espere a obtener los resultados completos. {#3-query-eks-audit-403-events-for-the-last-hour-and-wait-for-complete-results}

<details>
<summary>Ver respuesta</summary>

El registro de auditoría debe estar habilitado previamente. Seleccione la cuenta y región administradas y `/aws/eks/<cluster-name>/cluster`; en la consola, seleccione la última hora. Cada bloque es una consulta Logs Insights QL independiente. Use los campos JSON detectados en lugar de suponer un orden fijo de claves. Estas consultas cuentan eventos de auditoría, no necesariamente solicitudes únicas: las etapas de auditoría pueden repetir un identificador. Un 403 indica denegación de autorización, pero no demuestra por sí solo qué política IAM o RBAC la causó. El ejemplo de CLI necesita AWS CLI, Bash, jq y Python; consulta como máximo 100 registros y guarda los resultados de forma privada. Solo `Complete` es definitivo, aunque una consulta en ejecución ya devuelva filas. El vencimiento de la espera no cancela la consulta en el servicio.

```sql
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

```sql
filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| stats count(*) as deniedEvents by user.username, verb, objectRef.resource
| sort deniedEvents desc
| limit 100
```

```bash
# Read-only query with possible CloudWatch scan charges; no log configuration changes.
set -euo pipefail
umask 077
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
evidence_dir=$(mktemp -d "$PWD/eks-audit403.XXXXXX")
printf 'Private evidence directory: %s\n' "$evidence_dir"
read -r start_epoch end_epoch < <(python3 - <<'PY'
import time
end = int(time.time())
print(end - 3600, end)
PY
)
query_string='fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100'
query_id=$(aws logs start-query --region "$AWS_REGION" --no-cli-pager \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$start_epoch" --end-time "$end_epoch" \
  --query-string "$query_string" --query queryId --output text)
if [[ ! "$query_id" =~ ^[0-9a-fA-F-]{36}$ ]]; then
  printf '%s\n' 'No valid query ID returned.' >&2
  exit 1
fi
printf '%s\n' "$query_id" > "$evidence_dir/query-id.txt"
for attempt in {1..15}; do
  aws logs get-query-results --region "$AWS_REGION" --no-cli-pager \
    --query-id "$query_id" --output json > "$evidence_dir/result.json"
  status=$(jq -er '.status' "$evidence_dir/result.json")
  case "$status" in
    Complete)
      printf 'Query complete; inspect private file %s/result.json\n' "$evidence_dir"
      exit 0
      ;;
    Scheduled|Running) sleep 2 ;;
    *)
      printf 'Query ended without complete results: %s\n' "$status" >&2
      exit 1
      ;;
  esac
done
printf 'Polling limit reached; query %s may still run. Partial results are not final.\n' "$query_id" >&2
exit 2
```

</details>

## Preguntas avanzadas {#advanced-questions}

### 1. Diseñe una estrategia de trazas, métricas y registros para la latencia intermitente de una API. {#1-develop-a-tracing-metrics-and-logs-strategy-for-intermittent-api-latency}

<details>
<summary>Ver respuesta</summary>

**1. Defina el contrato de medición.** Use un único clúster, un `api-gateway` instrumentado en `diagnostics-example` y un histograma clásico en segundos con valores acotados de la etiqueta `endpoint` y un bucket `le="0.5"`. Confirme que el bucket y el contador tienen el mismo alcance de series. Kubernetes no proporciona estas métricas de aplicación automáticamente. Compare las rutas afectadas, el volumen de tráfico y los intervalos de tiempo. Las consultas siguientes muestran p99, las tasas acumulativas de los buckets para un mapa de calor y la fracción de solicitudes que tardan más de 0,5 segundos. Restar únicamente las tasas devuelve solicitudes por segundo, no una proporción. Con tráfico cero, la proporción no está definida.

```promql
histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (
  rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[5m])
))
```

```promql
sum by (le,namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[1m]))
```

```promql
(
  (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) - sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway",le="0.5"}[5m])))
  / sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m]))
)
and on (namespace,service,endpoint) (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) > 0)
```

**2. Examine las trazas.** En la interfaz del backend, seleccione el servicio `api-gateway`, el intervalo afectado, una duración >2 segundos y la operación pertinente, como `GET /api/products`. Examine los spans con errores y las llamadas a otros servicios con los nombres de atributo reales del backend. Son criterios de búsqueda de la interfaz, no una configuración YAML importable de Jaeger. Compruebe antes la propagación y el muestreo: la ausencia de un span no demuestra que no se produjera una llamada. No sume sin más los spans paralelos para calcular la duración de una solicitud.

**3. Correlacione los registros.** Si los registros estructurados contienen `trace_id`, sustituya el marcador por un identificador de traza real y ejecute esta consulta Logs Insights QL independiente en el grupo de registros de la aplicación y el intervalo administrados. Esto requiere instrumentación de la aplicación. Evite registrar tokens, cuerpos de solicitud y secretos propagados. La correlación acota una hipótesis, pero no demuestra causalidad.

```sql
fields @timestamp, @message
| filter trace_id = "REPLACE_WITH_ACTUAL_TRACE_ID"
| sort @timestamp asc
| limit 100
```

**4. Compare evidencias de infraestructura.** En orden, estas consultas devuelven segundos de limitación de CPU por segundo, bytes recibidos por segundo y segundos de pausas de GC de JVM por segundo. El caudal de red **no es latencia de red**. Para medir la latencia, use spans del cliente y servidor con el alcance correcto o una prueba de RTT autorizada y acotada. La tasa de pausas de GC no indica el retraso de cada solicitud. Los nombres y etiquetas dependen de los exportadores y del entorno de ejecución. Compare el nodo o Pod real y el intervalo correspondiente, no totales no relacionados del clúster.

```promql
rate(container_cpu_cfs_throttled_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
rate(container_network_receive_bytes_total{namespace="diagnostics-example",pod!=""}[5m])
```

```promql
rate(jvm_gc_pause_seconds_sum{namespace="diagnostics-example",service="api-gateway"}[5m])
```

**5. Diseñe un panel.** Esta tabla define paneles; no es un archivo importable de Grafana. Use el editor o formato de exportación de la versión de Grafana instalada y el UID real de la fuente de datos.

| Panel | Medición |
|---|---|
| Latencia p50/p95/p99 | Tres consultas independientes de cuantiles de histograma con 0.50, 0.95 y 0.99 |
| Tasa de solicitudes por estado | Tasa del contador de solicitudes instrumentado, agrupada por la etiqueta de estado real |
| Mapa de calor | Tasas correspondientes de los buckets de un histograma clásico, conservando `le` y el alcance de la ruta |
| Latencia de servicios de destino | El histograma y contrato de etiquetas propios del servicio de destino |
| Recursos de los Pods | Tasa del contador de CPU en núcleos; gauge del conjunto de trabajo de memoria en bytes |

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"}
```

**6. Evalúe una alerta de comparación.** Seleccione esta regla y espacio de nombres en Prometheus y sustituya la etiqueta de la versión de Helm. El umbral del 50 % y la espera de cinco minutos son ejemplos que deben ajustarse al tráfico y a los SLO. El p99 de la ventana más larga **no es una latencia media de una hora** e incluye los cinco minutos recientes. Es una regla de comparación, no un modelo predictivo. Se necesita un valor de referencia positivo; los datos ausentes o NaN no demuestran un estado saludable. Compruebe por separado la recopilación y el tráfico bajo, y pruebe la entrega de notificaciones.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-comparison-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: latency-comparison-example
    rules:
    - record: diagnostics:http_duration_seconds:p99_5m
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[5m])\n))"
    - record: diagnostics:http_duration_seconds:p99_1h
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[1h])\n))"
    - alert: LatencyComparedWithLongerWindow
      expr: "(\n  diagnostics:http_duration_seconds:p99_5m\n  / diagnostics:http_duration_seconds:p99_1h\
        \ > 1.5\n)\nand on (namespace,service,endpoint) (diagnostics:http_duration_seconds:p99_1h\
        \ > 0)"
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Five-minute p99 exceeds one-hour p99 by over 50%; investigate.
```

Mantenga separadas las hipótesis: el comportamiento de un endpoint, las llamadas a servicios de destino, la limitación de CPU, el GC, la ruta de red y los cambios de tráfico necesitan evidencias propias. Aquí no se midió una reducción de latencia ni se realizó una prueba de rendimiento.

</details>

### 2. Establezca un proceso de RCA basado en evidencias para nodos que pasan a NotReady de forma intermitente. {#2-establish-an-evidence-based-rca-process-for-intermittent-notready-nodes}

<details>
<summary>Ver respuesta</summary>

**1. Recopile la identidad y los tiempos.** Distinga `Ready=False` de la pérdida de latidos o `Unknown`. Registre el UID del nodo, el identificador del proveedor, las versiones del sistema operativo y del entorno de ejecución, las horas de transición de condiciones y la renovación del lease. La retención de Events es limitada; una lista vacía no descarta un fallo anterior. Un nodo detenido puede no admitir la depuración mediante node-debug.

```bash
# Read-only scoped node evidence; confirm account/cluster/Region first.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s)
node_state=$("${k[@]}" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,
  nodeInfo:.status.nodeInfo,conditions:.status.conditions
}')
printf '%s\n' "$node_state"
node_uid=$(jq -er '.uid' <<<"$node_state")
"${k[@]}" get events --all-namespaces \
  --field-selector "involvedObject.uid=$node_uid" --sort-by='.metadata.creationTimestamp'
"${k[@]}" -n kube-node-lease get lease "$NODE_NAME" \
  -o jsonpath='{.spec.renewTime}{"\n"}'
```

Para la instancia EC2 correspondiente, `Maximum=1` indica que al menos una muestra de la comprobación de estado falló en ese intervalo. `Sum` no mide la duración de la interrupción y la ausencia de datos no indica éxito. Fargate e Hybrid Nodes necesitan evidencias de su propia infraestructura.

```bash
# EC2-backed nodes only: resolve the actual instance from providerID, not a guessed name.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Verified EC2 instance ID}"
read -r start_time end_time < <(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc)
print((end-timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
      end.strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" --no-cli-pager \
  --namespace AWS/EC2 --metric-name StatusCheckFailed \
  --dimensions "Name=InstanceId,Value=$INSTANCE_ID" \
  --start-time "$start_time" --end-time "$end_time" --period 300 \
  --statistics Maximum --query 'sort_by(Datapoints,&Timestamp)'
```

**2. Recopile las evidencias del host que correspondan.** Use acceso al host autorizado, NodeDiagnostic o la ruta de diagnóstico documentada de Auto Mode del capítulo de referencia. `general` no es un atajo privilegiado para ejecutar chroot. Las lecturas siguientes son aplicables a un host Linux compatible con systemd, no a cualquier imagen de depuración ni a todas las rutas de Bottlerocket o Auto Mode. Los registros pueden contener datos sensibles; recójalos de forma privada antes de una reparación revisada por separado.

```bash
# Only inside an already authorized, compatible systemd Linux host context.
# These are bounded reads, not instructions to restart or prune the node.
journalctl -u kubelet --since '24 hours ago' -n 200 --no-pager
journalctl -u containerd --since '24 hours ago' -n 200 --no-pager
dmesg | tail -n 100
free -h
vmstat 1 5
cat /proc/pressure/memory /proc/pressure/cpu
```

**3. Compruebe la ruta de red pertinente.** Esta solicitud valida TLS usando el kubeconfig seleccionado y necesita autorización para `/readyz`. Prueba la ruta del cliente que la ejecuta, no necesariamente la del nodo que falla. Un 401 o 403 demuestra que hubo una respuesta HTTP, pero no confirma que el servicio esté listo. Los errores DNS, de tiempo de espera y de certificado necesitan diagnósticos separados. No use `curl -k` para ocultar fallos de confianza.

```bash
# Uses the selected kubeconfig CA and authentication; do not disable TLS verification.
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=10s get --raw='/readyz'
```

Solo para VPC CNI estándar, examine el Pod aws-node real y las ENI de la instancia afectada. Auto Mode utiliza su ruta de red administrada; no deduzca que la ausencia de un DaemonSet significa un fallo.

```bash
# Standard VPC CNI on an EC2 node; choose the aws-node Pod on the affected node.
: "${KUBE_CONTEXT:?}"; : "${AWS_NODE_POD:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  logs "$AWS_NODE_POD" -c aws-node --since=15m --tail=100 --limit-bytes=65536
aws ec2 describe-network-interfaces --region "$AWS_REGION" --no-cli-pager \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ENI:NetworkInterfaceId,Subnet:SubnetId,Status:Status,IPv4Prefixes:Ipv4Prefixes,PrivateIPs:PrivateIpAddresses[].PrivateIpAddress}'
```

**4. Interprete las señales de recursos.** Estas consultas de un único clúster muestran el margen de memoria, la capacidad del sistema de archivos raíz, la utilización del límite de hilos del sistema y una condición real de presión de kubelet. Requieren las series correspondientes de Node Exporter y kube-state-metrics y los montajes y etiquetas correctos del host. `processes` está desactivado de forma predeterminada en Node Exporter; `node_processes_max_threads` es el límite `threads-max` de Linux. Esa proporción no determina PIDPressure de kubelet ni el `pids.max` de un contenedor. Los límites del sistema de archivos, inodos, imagefs y cgroups, así como los fallos de recopilación, requieren comprobaciones aparte. Los umbrales son ejemplos, no valores predeterminados.

```promql
(1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0)) * 100 > 90
```

```promql
(1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0)) * 100 > 85
```

```promql
node_processes_threads / (node_processes_max_threads > 0) * 100 > 80
```

```promql
max by (node) (kube_node_status_condition{condition=~"MemoryPressure|DiskPressure|PIDPressure",status="true"}) == 1
```

**5. Compruebe las hipótesis.** Correlacione los registros OOM del kernel con el proceso terminado, la memoria de la carga de trabajo y sus límites; relacione el agotamiento de disco o inodos con el sistema de archivos afectado. Compare los registros de kubelet y del entorno de ejecución, la conectividad del nodo con la API, las evidencias de CNI/IP y la salud de EC2 con marcas de tiempo coincidentes. Un uso elevado de memoria o una sonda fallida no demuestran por sí solos una fuga de memoria ni un fallo de infraestructura.

**6. Evite la recurrencia según el modelo de cómputo real.** Auto Mode incluye monitorización y reparación de nodos. En los grupos de nodos administrados, compruebe su configuración de reparación. La reparación de Karpenter autogestionado necesita una versión compatible, `NodeRepair=true` y las condiciones y políticas de reparación aplicables; los agentes de diagnóstico aportan condiciones adicionales. La política actual de Karpenter permite 30 minutos para `Ready=False/Unknown`, bloquea las reparaciones cuando más del 20 % de un NodePool está en mal estado y puede forzar la terminación en lugar del drenaje ordenado habitual. No trate los presupuestos de interrupción voluntaria ni los PDB como garantías universales de reparación. La reparación de EKS no corrige de forma predeterminada `MemoryPressure`, `DiskPressure` ni `PIDPressure`; atienda la presión de las cargas de trabajo. Estas funciones de monitorización y reparación de EKS solo admiten Linux y el agente de monitorización no está disponible en Fargate. Use el capítulo de referencia y la configuración vigente del proveedor en lugar de desplegar un DaemonSet incompleto y privilegiado de Node Problem Detector o duplicar un agente existente.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: node-health-example
    rules:
    - alert: NodeHighMemoryUse
      expr: (1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0))
        * 100 > 90
      for: 5m
      labels:
        severity: warning
    - alert: NodeRootFilesystemLowSpace
      expr: (1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}
        / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0))
        * 100 > 85
      for: 5m
      labels:
        severity: warning
    - alert: NodeNotReady
      expr: max by (node) (kube_node_status_condition{condition="Ready",status="true"})
        == 0
      for: 2m
      labels:
        severity: critical
```

Prometheus debe seleccionar estas reglas. Las series ausentes de condiciones o exportadores requieren alertas independientes de recopilación e inventario. Las alertas de capacidad no se denominan condiciones de presión de kubelet porque miden señales distintas.

Si administra un kubelet Linux configurable, lo siguiente es un **fragmento que debe revisar e integrar en su configuración existente**, no una configuración completa ni un comando para sobrescribir un archivo de un nodo de EKS. Use el mecanismo de arranque compatible con el sistema operativo o aprovisionador. `mergeDefaultEvictionSettings` conserva los valores estrictos predeterminados que no se especifiquen; de lo contrario, una modificación parcial puede poner a cero los umbrales omitidos. Los umbrales flexibles necesitan sus períodos de gracia correspondientes, y `evictionMaxPodGracePeriod` limita la gracia de terminación. Los valores de ejemplo requieren validación de cargas y capacidad; no son instrucciones de personalización de Auto Mode.

```json
{
  "mergeDefaultEvictionSettings": true,
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  },
  "evictionMaxPodGracePeriod": 60
}
```

**Ejemplo de plantilla histórica de RCA.** Esta plantilla no documenta un incidente verificado. Se conservan las fechas, cantidades y zona horaria originales de cada idioma. Los ejemplos PST y KST no afirman representar el mismo instante. El material de referencia no aporta evidencias de la fuga de memoria alegada, de una reparación realizada ni de tareas completadas. Sustituya los marcadores por evidencias antes de usar la plantilla en operaciones.

```markdown
## Incident summary (illustrative)
- Start: 2024-01-15 14:30 PST
- Example impact: 3 nodes, 45 Pods
- Example restoration: 2024-01-15 15:15 PST (duration 45 minutes, not a measured mean)

## Example timeline (evidence required for every entry)
- 14:30 NodeNotReady alert
- 14:35 Investigation starts
- 14:50 Hypothesis: memory pressure killed kubelet; confirm with kernel/process evidence
- 15:00 Proposed drain/restart; record actual authorization, effects and data safety checks
- 15:15 Proposed restoration point; supply workload/SLO verification

## Root-cause hypothesis
A memory leak could exhaust node memory; not established by this template.

## Follow-up proposals (no completion asserted)
1. Validate application memory behavior and appropriate requests/limits.
2. Evaluate alert threshold change from 90% to 80% against noise and capacity.
3. Review existing node monitoring before considering Node Problem Detector.
```

</details>

**Referencias principales para estos ejercicios:**

- [Funciones de Prometheus](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Interrupciones y reparación de nodos de Karpenter](https://karpenter.sh/docs/concepts/disruption/)
- [Monitorización y reparación de nodos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html)
- [Desalojo por presión de nodos en kubelet](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Recopiladores de Node Exporter](https://github.com/prometheus/node_exporter#disabled-by-default)
