# Depuración avanzada y respuesta a incidentes de EKS

> **Línea base de revisión**: esquemas de Kubernetes 1.36 y kubectl 1.36.2; elija una versión de EKS con soporte vigente y versiones de componentes compatibles
> **Última actualización**: September 12, 2026

Para que los clústeres de Amazon EKS funcionen de forma estable, son esenciales un marco sistemático de respuesta a incidentes y habilidades avanzadas de depuración. Este documento ofrece una guía práctica para diagnosticar y resolver rápidamente problemas complejos que se producen en entornos de producción.

## Tabla de contenido

1. [Marco de respuesta a incidentes](#1-incident-response-framework)
2. [Depuración del plano de control](#2-control-plane-debugging)
3. [Solución de problemas en los nodos](#3-node-level-troubleshooting)
4. [Depuración de cargas de trabajo](#4-workload-debugging)
5. [Diagnóstico de redes](#5-networking-diagnostics)
6. [Solución de problemas de almacenamiento](#6-storage-troubleshooting)
7. [Arquitectura de observabilidad](#7-observability-architecture)
8. [Arquitectura de detección de fallos](#8-failure-detection-architecture)
9. [Referencia rápida](#9-quick-reference)
10. [Pasos siguientes](#10-next-steps)

---

<span id="1-incident-response-framework"></span>

## 1. Marco de respuesta a incidentes

### Lista de verificación de los primeros 5 minutos (evaluación inicial)

Considere los pasos originales de 30 segundos, la evaluación del alcance de dos minutos y el total de cinco minutos como objetivos de planificación, no como tiempos de finalización medidos. Primero determine el impacto para los clientes y la cuenta, el clúster/contexto, el espacio de nombres y el cambio reciente exactos. Que un cliente de API no esté disponible puede deberse a las credenciales, la autorización, DNS/red o el plano de control; por sí solo, no demuestra que todas las aplicaciones en ejecución estén caídas.

Examine conjuntamente las condiciones de los nodos, el estado de Pod/contenedor, el estado de los despliegues de los controladores, los eventos recientes y las muestras de recursos. `phase!=Running` no detecta los Pods Running pero NotReady o CrashLooping e incluye los Jobs que se completaron correctamente. Que un Pod esté en fase Running no demuestra que esté listo. En los Deployments, compare las réplicas deseadas, actualizadas, listas/disponibles y la generación observada, en lugar de buscar cadenas de presentación como `1/1`.

El DaemonSet estándar de VPC CNI, `aws-node`, suele ejecutarse en `kube-system`; un espacio de nombres llamado `amazon-vpc-cni-system` no es un requisito previo de EKS. Auto Mode puro administra las redes y el DNS del sistema de los nodos de otra manera, por lo que la ausencia de Pods de complementos estándar debe interpretarse según el modo del nodo/controlador. Los datos de Metrics Server son una vista de recursos muestreada, no una señal de disponibilidad para los clientes.

### Script de diagnóstico inicial

Este script realiza solicitudes API acotadas y guarda evidencia privada para un espacio de nombres de carga de trabajo seleccionado, además del estado de los nodos del clúster y de los Pods del sistema. No recopila datos de Secret ni vuelca las variables de entorno/configuración de todos los Pods. Los registros, los eventos y los mensajes de error aún pueden contener datos confidenciales de la aplicación: revise/enmascare la evidencia antes de compartirla. Revise las entradas de cuenta/contexto y el directorio privado de evidencia existente antes de ejecutarlo.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended account ID}"
: "${KUBE_CONTEXT:?Set the explicit kubectl context}"
: "${NAMESPACE:?Set the owned workload namespace}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
test -d "$EVIDENCE_PARENT"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
test "$ACTUAL_ACCOUNT_ID" = "$EXPECTED_ACCOUNT_ID" || { echo "Account mismatch" >&2; exit 1; }
CLUSTER_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.endpoint --output text)
KUBE_ENDPOINT=$(kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
test "$CLUSTER_ENDPOINT" = "$KUBE_ENDPOINT" || { echo "Context/cluster mismatch" >&2; exit 1; }

umask 077
TRIAGE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-triage.XXXXXXXX")
TRIAGE_FAILED=0
k() { kubectl --context "$KUBE_CONTEXT" --request-timeout=15s "$@"; }
collect() {
  local name=$1
  shift
  if "$@" > "$TRIAGE_DIR/$name.txt" 2> "$TRIAGE_DIR/$name.stderr"; then
    printf '%s\tok\n' "$name" >> "$TRIAGE_DIR/status.tsv"
  else
    local rc=$?
    TRIAGE_FAILED=$((TRIAGE_FAILED + 1))
    printf '%s\tfailed:%s\n' "$name" "$rc" >> "$TRIAGE_DIR/status.tsv"
  fi
}
node_health() {
  k get nodes -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
    unschedulable:.spec.unschedulable,taints:.spec.taints,conditions:.status.conditions
  }]'
}
pod_health() {
  k -n "$NAMESPACE" get pods -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,owners:.metadata.ownerReferences,
    deleting:.metadata.deletionTimestamp,phase:.status.phase,conditions:.status.conditions,
    containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
    initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
  }]'
}
deployment_health() {
  k -n "$NAMESPACE" get deployments -o json | jq '[.items[] | {
    name:.metadata.name,generation:.metadata.generation,observed:.status.observedGeneration,
    desired:(.spec.replicas // 1),updated:(.status.updatedReplicas // 0),
    ready:(.status.readyReplicas // 0),available:(.status.availableReplicas // 0),
    conditions:.status.conditions
  }]'
}
load_balancers() {
  k -n "$NAMESPACE" get services -o json | jq '[.items[] | select(.spec.type=="LoadBalancer") | {
    name:.metadata.name,class:.spec.loadBalancerClass,selector:.spec.selector,
    ports:.spec.ports,status:.status.loadBalancer
  }]'
}
collect nodes node_health
collect pods pod_health
collect deployments deployment_health
collect load-balancers load_balancers
collect events k -n "$NAMESPACE" get events --sort-by='.metadata.creationTimestamp'
collect system-pods k -n kube-system get pods -o wide
collect node-resources k top nodes
collect pod-resources k -n "$NAMESPACE" top pods --sort-by=memory
printf 'Private evidence: %s; failed collections: %s\n' "$TRIAGE_DIR" "$TRIAGE_FAILED"
test "$TRIAGE_FAILED" -eq 0
```

Revise `status.tsv` y los resultados de cada fallo. La falta de permisos, las métricas no disponibles y los tiempos de espera agotados de la API siguen siendo recopilaciones fallidas; el script termina con un código distinto de cero si alguna recopilación falla y no afirma que el incidente esté resuelto. Deja intencionadamente visibles los estados de Pod completados, pendientes y Running para que se interpreten. Las consultas de seguimiento selectivas a los registros deben usar un espacio de nombres, UID de Pod y contenedor exactos, con un intervalo de tiempo o número de líneas acotado.

La lista de LoadBalancer filtra localmente el JSON de Service: `spec.type` no es un selector de campos integrado compatible para Service. Esta recopilación inicial no incluye `cluster-info dump` general, cargas automáticas de archivos, reinicios ni eliminaciones de recursos.

### Matriz de gravedad

| Gravedad | Clasificación | Alcance del impacto | Tiempo de respuesta | Ejemplos |
|----------|---------------|--------------|----------------|----------|
| **P1** | Crítica | Interrupción completa del servicio | En 15 minutos | Fallo del plano de control, todos los nodos NotReady |
| **P2** | Alta | Fallo de una función importante | En 1 hora | Fallo completo de una carga de trabajo específica, problemas de conectividad de red |
| **P3** | Media | Impacto parcial | En 4 horas | Algunos reinicios de Pods, degradación del rendimiento |
| **P4** | Baja | Problemas menores | En 24 horas | Retraso en la recopilación de registros, alertas de supervisión no críticas |

Los tiempos de respuesta de esta tabla de gravedad son objetivos organizativos de ejemplo. Clasifique el impacto real en los clientes; una interrupción exclusiva del plano de control puede dejar en ejecución el tráfico de las cargas de trabajo existentes.

### Árbol de decisiones para identificar rápidamente problemas

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![Decision-tree workflow for the first minutes of EKS incident triage: after an incident is detected it asks whether the service is accessible, then walks kubectl connectivity, node readiness, and pod status toward control-plane, node, scheduling, or app/config causes, or response delay and intermittent errors toward workload, cluster-wide, or network/DNS causes.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-0.html)
-->

---

<span id="2-control-plane-debugging"></span>

## 2. Depuración del plano de control

### Tipos de registros del plano de control de EKS

EKS ofrece cinco tipos de registros del plano de control. Se envían al grupo de registros regional de CloudWatch solo cuando están habilitados; habilitar el registro no reconstruye los registros históricos que faltan. Limite el acceso y la retención de registros, y tenga en cuenta los cargos por ingestión/almacenamiento/consulta de CloudWatch. La ausencia de un grupo/flujo puede deberse a que el registro está deshabilitado, a que no se entregaron datos, a una región incorrecta o a acceso denegado, y no necesariamente a un fallo del plano de control.

| Tipo | Evidencia |
| --- | --- |
| api | Mensajes de operación y error del servidor API |
| audit | Identidad de la solicitud a la API, verbo, recurso y estado de respuesta |
| authenticator | Evidencia de autenticación de IAM a Kubernetes |
| controllerManager | Mensajes de reconciliación del controlador |
| scheduler | Decisiones/errores de programación |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
LOG_GROUP="/aws/eks/$CLUSTER_NAME/cluster"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
aws logs describe-log-streams --region "$AWS_REGION" --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime --descending --max-items 10 \
  --query 'logStreams[].{Name:logStreamName,LastEvent:lastEventTimestamp}'
```
```bash
# MUTATION: review cost, retention, access and available subnet IPs first.
set -euo pipefail
UPDATE_ID=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --update-id "$UPDATE_ID" --query update
```
El cambio es asíncrono. Siga el ID de actualización devuelto hasta que aparezca Successful; Failed/Cancelled o un tiempo de espera del cliente no indican que haya tenido éxito. Después, verifique describe-cluster y la entrega de nuevos registros. Que el clúster esté ACTIVE por sí solo no identifica la finalización de esta actualización. La actualización puede requerir hasta cinco direcciones IP disponibles en cada subred configurada para el clúster; revise los requisitos actuales de registro de EKS.

### Consultas de CloudWatch Logs Insights

Ejecute cada bloque como una consulta **independiente de Logs Insights QL**, no como Bash ni SQL. Seleccione el grupo de registros y el intervalo de tiempo exactos en la consola o en la solicitud StartQuery. Estas consultas utilizan campos de auditoría JSON de EKS cuando CloudWatch los detecta; inspeccione registros representativos y el análisis de registros anidados si cambia su canalización. Que una consulta no encuentre eventos no demuestra que el servicio estuviera en buen estado ni que se hayan entregado registros.

#### Mensajes de error de la API

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 100
```

#### Recuento de errores en el intervalo de tiempo seleccionado

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| stats count(*) as error_count by bin(5m)
```

#### Mensajes de Authenticator que requieren inspección

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /access denied|Unauthorized|unauthorized/
| sort @timestamp desc
| limit 50
```

#### Denegaciones estructuradas de autenticación/autorización en auditoría

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 100
```

#### Actividad de auditoría de una identidad revisada

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_OBSERVED_KUBERNETES_USERNAME"
| sort @timestamp desc
| limit 50
```

#### Eventos 429 de auditoría por identidad y recurso

```text
fields user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 429
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

#### Volumen de solicitudes a la API, no necesariamente limitación de solicitudes

```text
fields user.username, verb, objectRef.resource
| filter @logStream like /kube-apiserver-audit/
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

La auditoría 401/403 distingue las denegaciones por solicitud de las búsquedas de mensajes de Authenticator. El recuento de llamadas a la API no es un recuento de llamadas limitadas, y un resultado agregado por intervalo de tiempo ya no contiene la marca @timestamp de cada evento para ordenarlo. StartQuery devuelve un ID de consulta: consulte GetQueryResults hasta que el estado sea Complete y conserve los estados Failed/Cancelled/Timeout/de datos ausentes. El [capítulo de supervisión](06-eks-monitoring-logging.md) incluye el flujo de trabajo acotado de consulta/sondeo. En esta auditoría no se ejecutó ninguna consulta activa a CloudWatch.

[Registro del plano de control de EKS](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html) · [Ejemplos de campos de auditoría de AWS](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)

### Solución de problemas de autenticación de IAM

Ejecute primero la comprobación de cuenta/contexto de la evaluación inicial. Distinga la identidad IAM humana/de automatización que usa kubectl, la identidad de arranque del nodo y la identidad de AWS que usa una aplicación dentro de un Pod. La generación correcta de un token no demuestra la autenticación ni la autorización de Kubernetes.

El token de IAM de EKS que empieza por k8s-aws-v1 es una solicitud STS prefirmada codificada en base64url, **no un JWT de tres partes**. No lo decodifique ni lo imprima como JSON ni lo pegue en registros. Los tokens proyectados de ServiceAccount de Kubernetes son una credencial JWT diferente.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
aws sts get-caller-identity
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,AuthenticationMode:accessConfig.authenticationMode}'
# Print only the credential expiry, not the bearer token.
aws eks get-token --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --query status.expirationTimestamp --output text
kubectl --context "$KUBE_CONTEXT" auth whoami
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" auth can-i get pods
```
AuthenticationMode determina dónde inspeccionar el acceso. En el modo API/API_AND_CONFIG_MAP, inspeccione la entrada de acceso del principal, el alcance de la política asociada y los enlaces RBAC; en el modo CONFIG_MAP, inspeccione la asignación heredada existente. No cambie el modo de autenticación ni sustituya aws-auth para corregir un 401/403 que aún no se haya clasificado. La migración del modo de acceso tiene sus propios requisitos previos y transiciones irreversibles. No intente adivinar rutas de roles IAM ni ARN de sesiones STS mediante sustituciones de cadenas.

```bash
# Run for API or API_AND_CONFIG_MAP authentication mode.
aws eks list-access-entries --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
: "${PRINCIPAL_ARN:?Use a reviewed IAM role/user ARN, not an STS assumed-role session ARN}"
aws eks describe-access-entry --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
aws eks list-associated-access-policies --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
```
```bash
# Read-only legacy mapping inspection for CONFIG_MAP/API_AND_CONFIG_MAP clusters.
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap aws-auth -o yaml
```
Conserve las asignaciones existentes de arranque de nodos. El nombre de un grupo por sí solo no concede permisos sin el enlace pertinente; use acceso revisado con privilegios mínimos en lugar de añadir system:masters como paso de diagnóstico. Un 403 indica una denegación de autorización, mientras que un 401 puede indicar credenciales no válidas/caducadas. Los fallos de red/TLS son evidencia distinta.

### Solución de problemas de IRSA

IRSA requiere el emisor/proveedor OIDC correcto, una política de confianza del rol que coincida con el asunto del espacio de nombres/ServiceAccount y la audiencia sts.amazonaws.com, y un SDK de carga de trabajo que use y actualice las credenciales de identidad web. La anotación que aparece a continuación es solo una parte de esa configuración. El espacio de nombres/rol son marcadores de posición; este YAML no crea ningún rol, proveedor ni permiso de bucket.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: diagnostics-example
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/owned-s3-access-role
```
```bash
set -euo pipefail
: "${SERVICE_ACCOUNT:?Set the actual ServiceAccount on the Pod}"
: "${POD_NAME:?Set an owned Pod}"; : "${CONTAINER_NAME:?Set its application container}"
: "${IRSA_ROLE_NAME:?Set the reviewed IAM role name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get serviceaccount "$SERVICE_ACCOUNT" \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text
aws iam get-role --role-name "$IRSA_ROLE_NAME" --query Role.AssumeRolePolicyDocument
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid,serviceAccount:.spec.serviceAccountName,
  envNames:[.spec.containers[] | {name,envNames:[.env[]?.name]}],
  projectedVolumes:[.spec.volumes[]? | select(.projected) | {name,projected}]
}'
```
Inspeccione los **nombres** de las variables de entorno, la ruta del archivo de token/metadatos de montaje y la cadena de credenciales del SDK sin imprimir valores de secretos ni bytes del token. Las credenciales estáticas u otro proveedor anterior en la cadena del SDK pueden reemplazar la identidad prevista. Use el contenedor real de la aplicación; un Pod o contenedor de depuración recién creado puede tener una identidad/configuración distinta.

```bash
# Optional read-only identity request, only if AWS CLI is already in this container.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- aws sts get-caller-identity
```
Una respuesta de identidad de STS identifica el rol en uso; no demuestra que haya autorización para enumerar todos los buckets ni para acceder a un objeto específico. No ejecute aws s3 ls en toda la cuenta solo para probar la identidad.

### Solución de problemas de Pod Identity

```bash
aws eks list-pod-identity-associations --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --namespace "$NAMESPACE" --service-account "$SERVICE_ACCOUNT"
: "${ASSOCIATION_ID:?Use the exact matching association ID}"
aws eks describe-pod-identity-association --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --association-id "$ASSOCIATION_ID"
# Standard EC2-node setup only; Auto Mode provides the integration itself.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods \
  -l app.kubernetes.io/name=eks-pod-identity-agent
```
Compruebe la asociación, la confianza/permisos del rol, el proveedor de credenciales del SDK compatible y la conectividad del agente/nodo. Auto Mode incorpora compatibilidad y no requiere instalar un agente duplicado; Fargate no admite EKS Pod Identity. Mantenga la creación/modificación de la asociación separada de estos diagnósticos. IRSA y Pod Identity tienen audiencias de token y vías de entrega de credenciales distintas; la identidad AWS del operador no es ninguna de ellas de forma predeterminada.

### Duración y rotación de tokens de ServiceAccount

No existe un «máximo universal de 24 horas» para los tokens proyectados: la duración solicitada y el límite configurado del servidor API son cosas distintas. Kubelet solicita la rotación cuando un token supera el 80 % de su TTL o las 24 horas, y la aplicación debe volver a cargar el archivo rotado. EKS documenta una extensión de compatibilidad de 90 días para la migración de tokens de ServiceAccount de Kubernetes API y las anotaciones de auditoría de tokens obsoletos; esto no constituye una duración segura de caché ni una garantía de vida útil para IRSA, Pod Identity o cualquier parte que confíe en ellos.

El siguiente ejemplo solicita un token personalizado de una hora para una audiencia STS. No amplía el token API predeterminado ni configura IRSA automáticamente. El espacio de nombres/ServiceAccount existente, la imagen revisada, la confianza del rol y la configuración del SDK/archivo de token de la aplicación deben prepararse por separado. No se debe asumir que un token con audiencia STS es válido para Kubernetes API.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: audience-token-example
  namespace: diagnostics-example
spec:
  serviceAccountName: owned-app
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
      readOnly: true
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600
          audience: sts.amazonaws.com
```
[Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html) · [Migración/rotación de tokens de EKS](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) · [Tokens proyectados de Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/) · [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) · [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)

### Patrones de error de complementos de EKS

Antes de cambiar un complemento, lea la versión instalada, su propietario, los ajustes de configuración/identidad y health.issues. ACTIVE es un estado del complemento, no una prueba de que todo el tráfico de los clientes funcione; DEGRADED indica problemas de estado y no significa simplemente que el rendimiento sea más lento. CREATE_FAILED/UPDATE_FAILED/DELETE_FAILED requieren los detalles reales del problema. La ausencia de un complemento estándar puede ser esperada para funciones administradas por Auto Mode.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${ADDON_NAME:?Set the existing owned add-on}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" \
  --query 'addon.{Version:addonVersion,Status:status,Issues:health.issues,Configuration:configurationValues,Role:serviceAccountRoleArn,PodIdentity:podIdentityAssociations}'
CLUSTER_VERSION=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version "$CLUSTER_VERSION" \
  --query 'addons[].addonVersions[].{Version:addonVersion,Architectures:architecture,ComputeTypes:computeTypes,Compatibility:compatibilities}'
```
No considere que la primera versión de la respuesta sea «la más reciente» ni que sea automáticamente compatible con todos los tipos de nodo. Revise la arquitectura, el tipo de cómputo, los indicadores de versión predeterminada, el esquema de configuración, IAM/Pod Identity y la secuencia de migración del componente. El resultado de la configuración puede ser confidencial; manténgalo privado. Una actualización de versión es un cambio intencional, no un diagnóstico inicial.

```bash
# MUTATION: use a reviewed compatible version and configuration/identity plan.
set -euo pipefail
: "${REVIEWED_ADDON_VERSION:?Choose from the compatible versions after review}"
: "${REVIEWED_ADDON_CONFIG:?Set the path to the reviewed JSON configuration file}"
test -f "$REVIEWED_ADDON_CONFIG"
aws eks describe-addon-configuration --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --addon-version "$REVIEWED_ADDON_VERSION" --query configurationSchema --output text
# The configuration file must be checked against this version's schema before this request.
UPDATE_ID=$(aws eks update-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --addon-version "$REVIEWED_ADDON_VERSION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG" \
  --resolve-conflicts PRESERVE --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --update-id "$UPDATE_ID" --query update
```
PRESERVE solicita a EKS que conserve los ajustes personalizados existentes al resolver conflictos; no es una copia de seguridad ni garantiza que cualquier ajuste anterior funcione con la nueva versión. OVERWRITE puede restablecer personalizaciones en conflicto y debe revisarse por separado. Siga este ID de actualización exacto hasta su finalización, inspeccione los errores y verifique el estado resultante del complemento. Revise explícitamente configurationValues y los cambios de identidad, en lugar de omitirlos o sobrescribirlos de forma silenciosa.

[Actualizar un complemento de EKS](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)

---

<span id="3-node-level-troubleshooting"></span>

## 3. Solución de problemas en los nodos

<a id="node-join-diagnosis"></a>

### Diagnóstico de fallos al unir nodos

Estas son hipótesis que se deben comprobar con respecto a la instancia/NodeClaim, los registros de arranque, la accesibilidad del endpoint y el modo de autenticación; no son ocho causas raíz garantizadas.

| Área | Qué verificar |
| --- | --- |
| Arranque y AMI | Nombre/endpoint/CA del clúster correctos, arranque específico del SO, arquitectura y kubelet/AMI compatibles; no se trata de una regla universal de igualdad exacta de versiones |
| Red/seguridad | Nodo→API TCP 443, API→kubelet TCP 10250, DNS y rutas específicas de la carga de trabajo; valide la dirección, la pertenencia al grupo de seguridad y el enrutamiento |
| DNS de VPC | Compatibilidad con DNS y nombres de host, configuración del dominio/resolver DHCP y endpoint realmente utilizado |
| Identidad | Rol IAM del nodo y entrada de acceso de nodo de Kubernetes/asignación heredada, usando un ARN de rol en lugar de un ARN de perfil de instancia |
| Etiquetas de propiedad/detección | Etiquetas de propiedad de nodos específicas del aprovisionador; no las confunda con las etiquetas de subred para detectar balanceadores de carga |
| Acceso privado | Rutas requeridas de EKS/ECR/S3/STS y otros servicios mediante endpoints o salida revisados; una NAT gateway no es obligatoria en todos los diseños de clúster privado |
| Configuración de lanzamiento | Gestión correcta del rol/perfil para el aprovisionador real, versión de launch template, capacidad y disponibilidad de IP de subred |
| Inicialización | Inspeccione la evidencia de nodeadm/cloud-init/arranque pertinente para la AMI elegida; las rutas no son universales entre AL2023, Bottlerocket, Windows o Auto Mode |

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?Set the exact owned node name}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
  os:.status.nodeInfo.osImage,kernel:.status.nodeInfo.kernelVersion,
  kubelet:.status.nodeInfo.kubeletVersion,runtime:.status.nodeInfo.containerRuntimeVersion,
  labels:.metadata.labels,taints:.spec.taints,conditions:.status.conditions
}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.uid=$NODE_UID" --sort-by='.metadata.creationTimestamp'
```
```bash
# EC2-backed nodes only: map the Node providerID to an inspected instance ID/Region.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the verified EC2 ID, not a guessed node-name conversion}"
aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,AZ:Placement.AvailabilityZone,Subnet:SubnetId,Profile:IamInstanceProfile,Groups:SecurityGroups,Image:ImageId}'
aws ec2 describe-instance-status --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --include-all-instances
```
Una instancia que aún no se haya registrado no tiene un objeto Node: use en su lugar la evidencia de la instancia/NodeClaim/grupo de nodos administrado correspondiente. Ready=False y la falta de latidos que lleva a Ready=Unknown requieren evidencia distinta. Puede haber presión en el nodo aunque esté Ready; no deduzca su causa de una sola cadena de presentación. Las instancias EC2 administradas nuevas de Auto Mode pueden ocultarse de forma predeterminada en vistas genéricas de EC2; las consultas directas por ID de instancia o la inclusión explícita de recursos administrados no equivalen a cambiar la visibilidad de toda la cuenta.

### Árbol de decisiones para un nodo NotReady

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![Decision-tree flowchart for diagnosing a NotReady EKS node, walking down through EC2 instance status, kubelet health, network connectivity, and disk/memory pressure to containerd runtime health, with the matching remediation command at each branch.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-1.html)
-->

### Diagnósticos del host y de los nodos administrados

Para los nodos Linux accesibles a los clientes, SSM requiere el agente del nodo, los requisitos previos de rol/red y acceso autorizado a esa instancia exacta. Se abre una sesión. Las instancias administradas por EKS Auto Mode no admiten acceso SSH directo; use la ruta documentada de NodeDiagnostic/salida de consola o el flujo de trabajo compatible de kubectl debug node. La guía actual de Auto Mode admite explícitamente un **perfil de depuración sysadmin** para registros en vivo; esto crea un Pod privilegiado, no una sesión SSH ni un privilegio de depuración predeterminado. La recopilación de NodeDiagnostic puede cargar registros/capturas confidenciales en S3 y requiere un alcance/permisos de almacenamiento revisados por separado.

```bash
# Interactive host access: an operational session, not an automatic triage step.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the reviewed self-managed or managed-node-group instance}"
aws ssm start-session --region "$AWS_REGION" --target "$INSTANCE_ID"
```
```bash
# Read-only Linux/systemd host checks after authorized access.
sudo systemctl show kubelet containerd --no-pager \
  -p Id -p LoadState -p ActiveState -p SubState -p ExecMainStatus
sudo journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
sudo journalctl -u containerd --since "15 minutes ago" -n 100 --no-pager
sudo crictl info
sudo crictl ps
sudo crictl ps -a
sudo crictl images
df -h
df -i
sudo journalctl --disk-usage
```
```bash
# Exact container ID only; log content may be sensitive.
: "${CONTAINER_ID:?Use an inspected CRI container ID}"
sudo crictl logs --tail=100 "$CONTAINER_ID"
```
Estos comandos de systemd/CRI presuponen que esos componentes/herramientas existen en el host seleccionado. Configure el endpoint CRI correcto para crictl. Use lecturas acotadas de journal; es posible que journalctl -f canalizado a tail nunca termine. Evite imprimir kubeconfig/claves de cliente o eliminar indiscriminadamente registros, contenedores finalizados o cachés de imágenes. Pueden contener evidencia necesaria o estar bajo la administración de la recolección de basura de kubelet. Un reinicio, drenaje, reemplazo o cambio de retención requiere una condición diagnosticada y un paso de recuperación revisado por separado.

### Presión de recursos

DiskPressure se refiere a bytes/inodos disponibles y umbrales de expulsión configurados, no solo a la capacidad de df. Inspeccione df -h y df -i, la identidad del montaje y los eventos de kubelet. Si se aprueba la limpieza de retención, el valor antiguo journalctl --vacuum-size=500M es solo un ejemplo de política; primero recopile la evidencia necesaria y no elimine patrones de /var/log. MemoryPressure y un OOM del contenedor son señales distintas: correlacione los límites de memoria, la disponibilidad del nodo, el conjunto de trabajo, los registros y las métricas de presión. Aumentar un límite o añadir un nodo no demuestra que se haya corregido la causa raíz.

```bash
# Read-only host evidence, not remediation.
free -h
awk '/MemTotal|MemFree|MemAvailable|Buffers|Cached/ {print}' /proc/meminfo
cat /proc/sys/kernel/pid_max
cat /proc/sys/kernel/threads-max
ps -eLf --no-headers | wc -l
ps -eo pid,comm,nlwp --sort=-nlwp | head -20
if [ -r /proc/pressure/memory ]; then cat /proc/pressure/memory; fi
if [ -r /proc/pressure/cpu ]; then cat /proc/pressure/cpu; fi
```
El recuento de directorios de procesos no equivale al recuento de todos los hilos/tareas. ps NLWP y los límites del kernel son indicios; los cálculos de presión de PID de kubelet y los límites de PID de cgroup requieren su propia interpretación. No etiquete un porcentaje genérico de memoria alta como la condición MemoryPressure de Kubernetes. Considere las métricas ausentes como evidencia no disponible.

### Problemas de aprovisionamiento de Karpenter {#karpenter-provisioning-issues}

```bash
# Self-managed Karpenter; use the actual release namespace and selected objects.
: "${KARPENTER_NAMESPACE:?Set the existing controller namespace}"
: "${NODEPOOL_NAME:?}"; : "${NODECLAIM_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$KARPENTER_NAMESPACE" logs \
  -l app.kubernetes.io/name=karpenter -c controller --since=15m --tail=200 --prefix
kubectl --context "$KUBE_CONTEXT" get nodepool "$NODEPOOL_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get nodeclaim "$NODECLAIM_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.name=$NODECLAIM_NAME" --sort-by='.metadata.creationTimestamp'
```
Inspeccione el estado de NodePool/NodeClass, las condiciones/eventos de NodeClaim, las restricciones, los límites, las IP de subred, IAM y la capacidad de EC2. Para Auto Mode, use NodeClaim/NodeClass/eventos del controlador incluido y evidencia de los registros de auditoría; no espere un Deployment/espacio de nombres de karpenter autoadministrado. El siguiente patrón de esquema de Karpenter v1 autoadministrado es ilustrativo y requiere una versión compatible y un EC2NodeClass existente revisado. No es una instrucción para sustituir el grupo predeterminado del clúster. Los límites de CPU/memoria son topes, no capacidad reservada; la lista de tipos de capacidad no demuestra que solo se use Spot ni que las zonas de disponibilidad estén equilibradas.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-capacity-example
spec:
  template:
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      - key: karpenter.k8s.aws/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-existing-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
```
### Códigos de error de grupos de nodos administrados

| Problema | Significado y evidencia |
| --- | --- |
| AccessDenied | Fallo de autenticación/autorización de Kubernetes API; inspeccione el acceso del nodo y RBAC de EKS node-manager además de IAM |
| AsgInstanceLaunchFailures | Fallo de lanzamiento de ASG; inspeccione el mensaje real de actividad, la plantilla, la capacidad y los permisos |
| ClusterUnreachable | Conectividad a Kubernetes API o tiempos de espera al procesar solicitudes; no indica automáticamente que falte un VPC endpoint |
| InsufficientFreeAddresses | Las subredes de nodos seleccionadas no tienen suficientes IP disponibles; el CIDR IPv4 de una subred existente no puede ampliarse en el sitio |
| NodeCreationFailure | Las instancias lanzadas no pudieron registrarse; el arranque, el acceso y las rutas de red necesarias son comprobaciones frecuentes |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${NODEGROUP_NAME:?Set the exact managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Issues:health.issues,Version:version,Release:releaseVersion,Subnets:subnets,Role:nodeRole,LaunchTemplate:launchTemplate,Repair:nodeRepairConfig}'
# For a Kubernetes authorization issue, inspect rather than blindly replace EKS-managed RBAC.
kubectl --context "$KUBE_CONTEXT" get clusterrole eks:node-manager -o yaml
kubectl --context "$KUBE_CONTEXT" get clusterrolebinding eks:node-manager -o yaml
```
Use el mensaje y los resourceIds de cada problema, así como el procedimiento de reparación actual de AWS. La guía de solución de problemas describe NodeCreationFailure cuando los nodos administrados no logran unirse en 15 minutos; esto no garantiza que cada arranque finalice en ese plazo. Si las subredes necesitan más espacio, planifique nuevo espacio de direcciones/subredes y la migración específica del aprovisionador en lugar de editar un CIDR existente. Las estructuras de RBAC administradas por EKS pueden evolucionar: no pegue un ClusterRole de reemplazo antiguo solo porque aparezca AccessDenied. La reparación/expulsión de nodos es distinta de la inspección y debe tener en cuenta las cargas de trabajo, los presupuestos, los datos y el modo activo de administración de nodos.

[Solución de problemas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html) · [Rutas de diagnóstico de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-troubleshoot.html) · [Rutas de grupos de seguridad](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html) · [Clústeres privados](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html) · [Compatibilidad de Karpenter](https://karpenter.sh/docs/upgrading/compatibility/)

### Controlador de disponibilidad de nodos (verificación de arranque por etapas)

El Node Readiness Controller de Kubernetes SIGs es un controlador externo real. La versión v0.5.0 revisada utiliza el `NodeReadinessRule` con ámbito de clúster `readiness.node.x-k8s.io/v1alpha1`; no es un procesador de ConfigMap integrado en EKS ni un campo GA de la API Node.

El controlador lee las condiciones de Node y administra taints. **No** ejecuta entradas arbitrarias `checks[].probe.exec` en un ConfigMap. Las comprobaciones originales de existencia de archivos/containerd requieren un reporter implementado y autorizado por separado o un monitor personalizado de NPD que publique las condiciones correspondientes. Que exista un archivo de configuración de CNI no demuestra por sí solo que CNI esté listo. El reporter incluido en el proyecto consulta un endpoint HTTP mediante `CHECK_ENDPOINT`, `CONDITION_TYPE` y `NODE_NAME`; su configuración no tiene el formato anterior de exec-probe.

Esta regla es una **vista previa de taint** explícita para un alcance de prueba. Aplicarla sigue creando un recurso de clúster y el controlador actualiza el estado, pero `dryRun: true` no añade ni elimina taints de nodo. Los nombres de condición y la etiqueta de nodo del ejemplo son requisitos personalizados, no etiquetas/condiciones proporcionadas automáticamente por EKS.

```yaml
apiVersion: readiness.node.x-k8s.io/v1alpha1
kind: NodeReadinessRule
metadata:
  name: reviewed-bootstrap-readiness
spec:
  dryRun: true
  enforcementMode: bootstrap-only
  nodeSelector:
    matchLabels:
      audit.example.com/readiness-demo: 'true'
  conditions:
  - type: audit.example.com/CNIReady
    requiredStatus: 'True'
  - type: audit.example.com/ContainerRuntimeReady
    requiredStatus: 'True'
  taint:
    key: readiness.k8s.io/bootstrap-not-ready
    value: pending
    effect: NoSchedule
```

Inspeccione `status.dryRunResults`, `status.nodeEvaluations`, los nodos fallidos y las condiciones Node seleccionadas antes de habilitar la aplicación.

```bash
# Read-only: the controller and released CRD must already be installed.
: "${KUBE_CONTEXT:?Set the verified context}"
kubectl --context "$KUBE_CONTEXT" get nodereadinessrule reviewed-bootstrap-readiness -o yaml
kubectl --context "$KUBE_CONTEXT" get nodes \
  -l audit.example.com/readiness-demo=true -o json
```

Para una barrera de arranque, registre los nodos nuevos con el taint de inicio coincidente antes de que la programación pueda adelantarse al controlador. El reporter y los DaemonSets del sistema necesarios deben tolerar ese taint y poder acceder a la API. Cuando se cumplen todos los requisitos, el modo bootstrap-only elimina el taint y registra la finalización; no vuelve a aplicar la barrera si esas condiciones fallan posteriormente. Continuous mode es una opción de política distinta.

`NoSchedule` impide la programación de Pods nuevos que no toleran el taint; no expulsa los Pods existentes. No establezca `defaultStatus` en reglas bootstrap-only: la versión rechaza esa combinación. La validación nativa de CRD aquí no demuestra el estado del reporter, el comportamiento del admission webhook ni el funcionamiento en todos los tipos de nodo de EKS. Durante esta auditoría no se cambiaron etiquetas, taints, controladores ni condiciones de nodos.

[Versión v0.5.0](https://github.com/kubernetes-sigs/node-readiness-controller/releases/tag/v0.5.0) · [Semántica de aplicación y dry-run](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/user-guide/concepts.md) · [Configuración del reporter](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/reference/reporter-configuration.md)

---

<span id="4-workload-debugging"></span>

## 4. Depuración de cargas de trabajo

### Estado de Pod y contenedor

Las fases de Pod son Pending, Running, Succeeded, Failed y Unknown. Los estados de contenedor son Waiting, Running y Terminated; ContainerCreating y CrashLoopBackOff son motivos/información de presentación, no fases adicionales de Pod. Running no equivale a Ready. Una política de reinicio puede reiniciar un contenedor dentro de un Pod; no convierte un Pod terminal Failed en Pending. El reemplazo de un controlador es un Pod nuevo con un UID nuevo.

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![State machine showing a Kubernetes Pod's lifecycle -- Pending to ContainerCreating to Running to Succeeded on the happy path, with ContainerCreating and Running able to fail into Failed, and Failed pods returning to Pending under the restart policy -- annotated with the major failure causes at each state.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-2.html)
-->

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,node:.spec.nodeName,
  phase:.status.phase,reason:.status.reason,conditions:.status.conditions,
  containers:.status.containerStatuses,initContainers:.status.initContainerStatuses,
  ephemeralContainers:.status.ephemeralContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=200
```
```bash
# Separate read: this can fail when no previous container log exists.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --previous --tail=200
```
El registro anterior corresponde a la instancia terminada más reciente del contenedor seleccionado, no al historial completo de reinicios. La rotación o eliminación del Pod puede hacer que los registros no estén disponibles. Registre el UID/tiempo del Pod y compruebe si se reemplaza durante la recopilación; los contenedores init/sidecar/efímeros pueden tener fallos distintos. Los registros y mensajes de estado pueden contener datos confidenciales, así que mantenga privada la evidencia recopilada. No imprima todas las variables de entorno ni los archivos de configuración de la aplicación como atajo de diagnóstico.

### kubectl debug: tres operaciones distintas

Un contenedor efímero modifica el Pod existente; `--copy-to` crea otro Pod; `node/` crea un Pod de diagnóstico en un nodo. Todas son modificaciones y requieren los permisos RBAC/admission pertinentes. En kubectl 1.36.2 comprobado, el perfil predeterminado es general. No significa automáticamente que sea privilegiado, y el acceso al espacio de nombres/sistema de archivos del host es distinto de `privileged=true`.

#### Contenedor efímero

```bash
# MUTATION: adds a permanent-to-this-Pod-spec ephemeral-container entry.
: "${DEBUG_IMAGE:?Use a reviewed non-root diagnostic image with a compatible shell}"
: "${DEBUG_CONTAINER_NAME:?Choose an unused container name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" -it \
  --container="$DEBUG_CONTAINER_NAME" --target="$CONTAINER_NAME" \
  --image="$DEBUG_IMAGE" --profile=restricted -- sh
```
El perfil restricted elimina capacidades, impide la escalada de privilegios y solicita ejecución como usuario no root/seccomp RuntimeDefault. La imagen/usuario/shell deben admitirlo; no se garantiza que se inicie una imagen BusyBox cualquiera que solo funcione como root. `--target` solicita el espacio de nombres de procesos del destino solo si el runtime lo admite. No copia el sistema de archivos/entorno de la aplicación ni elude permisos. Al salir, termina el proceso de depuración, pero la entrada del contenedor efímero no se puede eliminar del spec del Pod existente.

#### Copia de Pod

```bash
# MUTATION: copy only a reviewed reproduction Pod; inspect all side effects first.
: "${DEBUG_POD_NAME:?Choose a new owned Pod name in the same namespace}"
: "${DEBUG_IMAGE:?Use a reviewed diagnostic image that provides sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --keep-labels=false --keep-annotations=false \
  --share-processes=true --profile=general -- sleep 3600
```
La comprobación de CLI nativa confirmó que esto reemplaza la imagen/orden del contenedor seleccionado y elimina los contenedores init, a la vez que conserva el ServiceAccount y habilita el espacio de nombres de procesos compartido. Pueden conservarse otros contenedores normales, referencias a entorno/Secret y volúmenes, y ejecutarse o acceder a los mismos datos. La copia permanece en el mismo espacio de nombres, puede programarse en otro nodo y no es un clon de datos aislado. Revise la mutación admission, los efectos secundarios, la identidad, los volúmenes persistentes y la limpieza antes de usarla. Las capacidades del perfil general pueden ser rechazadas por la política del espacio de nombres; no relaje la política de forma silenciosa.

#### Diagnósticos de nodo

```bash
# MUTATION: privileged host diagnostic Pod, only where this access is authorized.
: "${NODE_NAME:?Use the exact reviewed Node}"
: "${NODE_DEBUG_IMAGE:?Use a reviewed image with nsenter}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" -it \
  --image="$NODE_DEBUG_IMAGE" --profile=sysadmin \
  -- nsenter -t 1 -m -- journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
```
La depuración de nodo monta la raíz del host en /host y utiliza los espacios de nombres del host; el perfil sysadmin explícito añade ejecución privilegiada. Esto proporciona amplio acceso al host incluso cuando el comando elegido solo lee registros. La imagen debe contener ya las herramientas de diagnóstico necesarias. La guía de usuario de Auto Mode documenta esta ruta; allí sigue sin estar disponible el acceso SSH normal. Otras clases de SO/nodo requieren su método de acceso compatible. No se puede suponer que se inicie un Pod de depuración nuevo si kubelet/runtime/red no funcionan.

Registre el nombre/UID del Pod de depuración creado en la operación real. Elimine solo ese Pod separado después de revisar la evidencia; no elimine el Pod de la aplicación para «limpiar» un contenedor efímero.

```bash
# MUTATION: remove only the separately created debug Pod after checking its identity.
: "${DEBUG_POD_NAME:?}"; : "${EXPECTED_DEBUG_UID:?Use the UID recorded at creation}"
ACTUAL_DEBUG_UID=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$DEBUG_POD_NAME" \
  -o jsonpath='{.metadata.uid}')
test "$ACTUAL_DEBUG_UID" = "$EXPECTED_DEBUG_UID" || { echo "Debug Pod changed; stop" >&2; exit 1; }
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" delete pod "$DEBUG_POD_NAME" --timeout=2m
```
La comprobación del UID es una medida de seguridad, no una precondición de eliminación atómica; coordine la operación para que el nombre no se reutilice entre la comprobación y la eliminación. En esta auditoría no se ejecutaron contenedores de depuración, cargas de trabajo privilegiadas ni comandos de nodo. Las pruebas de CLI nativa solo usaron respuestas sintéticas de API de loopback.

### Administración de despliegues de Deployment

```bash
# Read-only rollout evidence.
: "${DEPLOYMENT_NAME:?Set the owned Deployment}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=2m
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout history "deployment/$DEPLOYMENT_NAME"
```
```bash
# MUTATION: workload revision rollback, not database/PVC/control-plane rollback.
set -euo pipefail
: "${REVIEWED_REVISION:?Set an inspected compatible revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout undo \
  "deployment/$DEPLOYMENT_NAME" --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=5m
```
Un tiempo de espera agotado/fallo es evidencia que se debe inspeccionar, no un éxito. Coordine GitOps y otros reconciliadores; una reversión no restaura una base de datos ni deshace cambios de esquema. Pausar/reanudar Deployment controla el progreso del despliegue, no HPA ni toda creación de Pod. rollout restart cambia intencionadamente la plantilla de Pod y crea reemplazos aunque la referencia de imagen sea la misma; una imagen sin versión fijada puede resolverse a algo distinto. Use el espacio de nombres/Deployment exactos y un plan de actualización revisado en lugar de combinar comandos de restart/undo/scale durante la evaluación inicial.

### Problemas de escalado de HPA/VPA

```bash
# Read-only: use the actual scaler names and workload namespace.
: "${HPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa "$HPA_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe hpa "$HPA_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: diagnostics-example
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
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
        value: 100
        periodSeconds: 15
```
```bash
# VPA is a separately installed controller/CRD, not built into EKS.
: "${VPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get vpa "$VPA_NAME" -o json | jq '{
  target:.spec.targetRef,updatePolicy:.spec.updatePolicy,resourcePolicy:.spec.resourcePolicy,
  recommendation:.status.recommendation,conditions:.status.conditions
}'
```
El ejemplo de HPA requiere un Deployment existente y un proveedor de métricas de recursos, además de solicitudes de CPU/memoria pertinentes en los contenedores de destino. Los objetivos de utilización se calculan con respecto a las solicitudes, no a los límites. Cuando hay varias métricas, se elige el mayor número recomendado de réplicas; las métricas ausentes/con errores afectan las decisiones. La utilización de memoria no es una solución universal a fugas/OOM. La estabilización de reducción de escala y las políticas de ritmo no son un interruptor de pausa.

VPA se instala por separado. Inspeccione la recomendación real, las condiciones, el modo de actualización y la versión compatible. El nombre del modo heredado Auto está obsoleto en la guía actual; elija un modo documentado como Off, solo para recomendaciones, o un modo de actualización revisado. Evite permitir que VPA modifique el mismo denominador de solicitud que utiliza HPA sin coordinación.

### Configuración de probes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-probe-example
  namespace: diagnostics-example
spec:
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    ports:
    - name: http
      containerPort: 8080
    startupProbe:
      httpGet:
        path: /healthz
        port: http
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 30
    livenessProbe:
      httpGet:
        path: /healthz
        port: http
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: http
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
```
Sustituya la imagen de marcador de posición e implemente los endpoints de estado reales; este Pod independiente es un ejemplo de esquema, no una carga de trabajo de producción replicada. Startup bloquea liveness/readiness hasta que tiene éxito. Treinta intentos con un periodo de cinco segundos más el retraso inicial forman un presupuesto de arranque aproximado, no un plazo estricto de 150 segundos. El fallo de readiness elimina la disponibilidad para el enrutamiento del servicio; no reinicia el contenedor. Liveness no debería reiniciar procesos en buen estado simplemente porque una dependencia externa sea lenta. Valide por separado el cierre, la presión de recursos y los tiempos reales de respuesta.

[Ciclo de vida de Pod](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) · [Depurar Pods en ejecución](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) · [Comportamiento de HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [Modos de VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)

---

<span id="5-networking-diagnostics"></span>

## 5. Diagnóstico de redes

### VPC CNI y asignación de IP

Identifique primero la implementación del nodo/red. Los siguientes ajustes de aws-node se aplican a la ruta estándar de Amazon VPC CNI. Auto Mode tiene controles de red/NodeClass administrados propios; cambiar un DaemonSet de aws-node no configura los nodos de Auto Mode. Windows, Fargate y Hybrid Nodes tienen aplicabilidad y rutas de diagnóstico diferentes. Mantenga la comprobación inicial de cuenta/contexto y el alcance exacto de nodo/espacio de nombres.

```bash
# Standard Amazon VPC CNI on applicable nodes, not an Auto Mode control interface.
: "${KUBE_CONTEXT:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the inspected EC2 node ID}"
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset aws-node -o json | jq '{
  containers:[.spec.template.spec.containers[] | {name,image,settings:[
    .env[]? | select(.name | IN("ENABLE_PREFIX_DELEGATION","WARM_PREFIX_TARGET","WARM_IP_TARGET",
      "MINIMUM_IP_TARGET","AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG","ENI_CONFIG_LABEL_DEF"))
  ]}]
}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=aws-node -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=aws-node \
  -c aws-node --since=15m --tail=100 --prefix
aws ec2 describe-network-interfaces --region "$AWS_REGION" \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,Subnet:SubnetId,Description:Description,IPv4:PrivateIpAddresses[].PrivateIpAddress,IPv4Prefixes:Ipv4Prefixes,IPv6Prefixes:Ipv6Prefixes,Groups:Groups}'
```
```bash
# Read-only: use subnets actually selected by the node/provisioner, not all account subnets.
: "${SUBNET_ID:?Set an inspected subnet ID}"
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{ID:SubnetId,VPC:VpcId,AZ:AvailabilityZone,CIDR:CidrBlock,AvailableIPv4:AvailableIpAddressCount}'
```
Las descripciones de ENI no son un límite de propiedad. Use los ID de instancia/subred inspeccionados e incluya las ENI pertinentes de redes personalizadas o Pods. El número de direcciones libres de una subred no demuestra que haya un prefijo contiguo disponible; añadir un CIDR de VPC tampoco configura por sí solo la red de Pods.

### Delegación de prefijos

En una configuración Linux/Nitro/CNI compatible, la delegación de prefijos puede mejorar la densidad de IP y el comportamiento de asignación. Verifique el espacio de prefijos contiguos/reservas, los límites de ENI/prefijos, maxPods/Pods asignables del nodo y la preparación para la migración. No la habilite a ciegas en nodos en ejecución ni deduzca la capacidad utilizable únicamente del recuento de IPv4 libres.

Lo siguiente es un **fragmento de configuración para revisión** que se debe combinar con la configuración real compatible del complemento/chart, no un reemplazo completo de los ajustes existentes:

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
Los ajustes configurados WARM_IP_TARGET/MINIMUM_IP_TARGET prevalecen sobre WARM_PREFIX_TARGET. Un objetivo de precalentamiento conserva direcciones/prefijos de reserva; no reserva capacidad de nodo ni corrige una subred agotada o fragmentada. Revise la configuración almacenada y su propietario antes de un despliegue controlado; verifique los Pods nuevos y el estado IPAM real después.

### Redes personalizadas

Prepare espacio de direcciones de VPC no superpuesto, las subredes de Pods reales por zona de disponibilidad, el enrutamiento/salida, los grupos de seguridad y capacidad de migración suficiente antes de cambiar el modo de CNI. La creación original de CIDR/subred en dos líneas más el cambio de variable de entorno no era una receta operativa completa. El CIDR IPv4 de una subred existente no se puede ampliar en el sitio. El enfoque ENIConfig estándar que sigue es distinto de los controles de red de Auto Mode.

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```
```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
```
El ejemplo de ENIConfig cubre una sola zona de disponibilidad y utiliza ID de marcador de posición. Con selección basada en zona, cree la configuración correcta para cada zona apta y asegúrese de que el nodo tenga la etiqueta coincidente. Para varias subredes de Pods por zona se necesita un esquema de selección personalizado deliberado. Los ajustes de security-group-for-Pod pueden cambiar qué grupos se aplican; compruebe la precedencia del CNI instalado. Valide la configuración del controlador, el despliegue de nodos nuevos y la colocación de Pods antes de retirar la capacidad antigua. Consulte la [guía de redes](03-eks-networking-part1.md) para ver la configuración general.

### CoreDNS y contexto del resolver

Los nodos de Auto Mode puro ejecutan CoreDNS como servicio del sistema del nodo. Los clústeres mixtos deben conservar el Deployment para los nodos que no son de Auto. La ausencia de ese Deployment en un clúster Auto puro no constituye por sí sola una interrupción de DNS. Para DNS basado en Deployment:

```bash
# CoreDNS Deployment on standard/mixed clusters; Auto Mode node-system DNS differs.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --since=15m --tail=100 --prefix
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
# Inspect the actual resolver context in an owned application container with these tools.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- cat /etc/resolv.conf
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```
CoreDNS no registra todas las consultas DNS a menos que se habilite la configuración de registro pertinente. Un Pod de prueba nuevo puede usar una ruta de espacio de nombres/nodo/DNS/identidad/política distinta de la carga de trabajo con fallos. Use el contexto de resolución real de la carga de trabajo y un FQDN terminado en punto cuando pruebe la resolución absoluta.

El valor ndots=2 siguiente es un experimento, no una solución universal para la latencia. Cambia el comportamiento de búsqueda y puede afectar a nombres parcialmente cualificados. El comportamiento de libc, los resolvers de lenguaje y el almacenamiento en caché de la aplicación varían; no dé por sentado que opciones específicas de glibc, como single-request-reopen, sean portables.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-options-example
  namespace: diagnostics-example
spec:
  dnsPolicy: ClusterFirst
  dnsConfig:
    options:
    - name: ndots
      value: '2'
    - name: timeout
      value: '2'
    - name: attempts
      value: '3'
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
```
A continuación se muestra un Corefile ilustrativo. Compárelo con la versión instalada, los complementos necesarios, las zonas/reenviadores personalizados y la configuración del complemento administrado; no sobrescriba por completo un ConfigMap activo. Los valores de cache, max_concurrent y lameduck requieren validación de tráfico/estado. pods insecure es el modo de registros Pod del complemento Kubernetes, no un interruptor para desactivar TLS/autenticación de Kubernetes API.

```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
        max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
```
### Verificación de Service y EndpointSlice

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json | jq '{
  name:.metadata.name,type:.spec.type,clusterIP:.spec.clusterIP,ipFamilies:.spec.ipFamilies,
  externalName:.spec.externalName,selector:.spec.selector,ports:.spec.ports,
  trafficDistribution:.spec.trafficDistribution,externalTrafficPolicy:.spec.externalTrafficPolicy
}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o json | jq '[.items[] | {
    name:.metadata.name,addressType,ports,
    endpoints:[.endpoints[]? | {addresses,conditions,nodeName,zone,targetRef}]
  }]'
```
Use EndpointSlices para inspeccionar los endpoints actuales; la API Endpoints más antigua está obsoleta. Compruebe el selector/puerto/targetPort de Service, la familia de direcciones y las condiciones ready/serving/terminating de los endpoints. Los Services headless, ExternalName y sin selector tienen comportamientos distintos. Que exista una dirección de endpoint no demuestra que pueda recibir el tráfico previsto; además, el puerto de Service no siempre es el puerto del contenedor de la aplicación.

### Lógica AND/OR de NetworkPolicy

Dentro de un mismo peer, namespaceSelector y podSelector se combinan mediante AND; los peers/reglas separados son alternativas. Un peer que solo contiene podSelector selecciona Pods del espacio de nombres de la política. Todas las NetworkPolicies aplicables agregan permisos; una política restrictiva no anula un permiso más amplio de otra. Confirme la compatibilidad y el modo de aplicación de la red para el CNI/tipo de nodo real antes de tratar un manifiesto como firewall.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reviewed-api-policy
  namespace: diagnostics-example
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app.kubernetes.io/name: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context "$KUBE_CONTEXT" get namespaces --show-labels
```
Este ejemplo añade DNS TCP/UDP para los Pods CoreDNS coincidentes; de lo contrario, el egress solo a la base de datos omitiría DNS. El DNS local del nodo/Auto Mode sigue una ruta distinta y requiere verificación específica del modo. Haga coincidir las etiquetas y los puertos reales de supervisión/base de datos y añada solo dependencias externas revisadas. La política es un cambio ilustrativo, no una lista de permisos de producción demostrada.

### Pruebas de red acotadas

```bash
# An intentional, bounded request from the actual workload context with curl installed.
: "${HEALTH_URL:?Set the owned safe health-check URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```
```bash
# In an approved diagnostic context with the named tools.
: "${SERVICE_FQDN:?Set the exact owned service DNS name}"
dig +time=2 +tries=1 "$SERVICE_FQDN"
# Packet capture needs the appropriate capabilities/privileges and an owned target.
: "${TARGET_IP:?Set one reviewed peer IP}"
umask 077
timeout 30 tcpdump -i any -nn -c 100 -s 96 "host $TARGET_IP and port 443" -w owned-capture.pcap
# Separate deliberate load test: only against an agreed iperf3 server.
: "${IPERF_SERVER:?Set the owned test server}"
iperf3 -c "$IPERF_SERVER" -p 5201 -t 10 -P 1 -b 10M
```
Elija una imagen/herramienta de diagnóstico revisada con el flujo de depuración anterior; crear un Pod netshoot es una modificación, no una observación pasiva. La captura de paquetes requiere capacidades/privilegios, no solo un nombre de usuario root, y hasta las capturas acotadas pueden contener cabeceras/datos confidenciales. Guárdelas de forma privada y revíselas antes de compartirlas. dig +trace prueba rutas DNS iterativas directas, no solo el resolver configurado para la carga de trabajo. iperf3 genera tráfico deliberadamente: su rendimiento no es latencia de red ni un resultado medido en esta auditoría.

[Modo de prefijos](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html) · [Redes personalizadas](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html) · [Semántica de NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/) · [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)

---

<span id="6-storage-troubleshooting"></span>

## 6. Solución de problemas de almacenamiento

### Identificar el driver y los permisos

Lea spec.csi.driver y volumeHandle del PV enlazado, así como el provisioner de StorageClass. El driver EBS estándar es ebs.csi.aws.com; Auto Mode usa ebs.csi.eks.amazonaws.com y su controlador administrado, por lo que puede ser esperada la ausencia de un Deployment de controlador estándar. Los comandos de registro del driver estándar que aparecen abajo requieren que ese driver esté instalado. EBS no se puede montar en Pods de Fargate ni en EKS Hybrid Nodes; colocar el controlador estándar en Fargate no cambia esa restricción del plano de datos.

```bash
# Read-only: identify the actual installed driver and workload owner first.
kubectl --context "$KUBE_CONTEXT" get csidrivers
: "${CSI_NAMESPACE:?Set the namespace of the installed standard CSI controller}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" get deployments,daemonsets,pods -o wide
: "${CSI_CONTROLLER_NAME:?Use an observed controller Deployment name}"
: "${CSI_CONTAINER_NAME:?Use the CSI plugin container name}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" logs "deployment/$CSI_CONTROLLER_NAME" \
  -c "$CSI_CONTAINER_NAME" --since=15m --tail=100
```
```bash
# Inspect only the role actually used by the standard EBS CSI controller.
: "${CSI_ROLE_NAME:?Set the reviewed role name}"
aws iam get-role --role-name "$CSI_ROLE_NAME" --query Role.AssumeRolePolicyDocument
aws iam list-attached-role-policies --role-name "$CSI_ROLE_NAME"
aws iam list-role-policies --role-name "$CSI_ROLE_NAME"
```
La guía actual de EKS recomienda revisar AmazonEBSCSIDriverPolicyV2 para los permisos del driver estándar. Delimita la administración de volúmenes/snapshots mediante etiquetas de propiedad del driver, con compatibilidad para etiquetas de volúmenes migrados a CSI. Revise la migración y las etiquetas de recursos existentes antes de reemplazar una política anterior; no adjunte como solución genérica una política irrestricta Resource:* que contenga todas las mutaciones. Algunas operaciones AWS de lectura/listado requieren recursos comodín, lo cual es distinto de conceder permisos amplios de mutación.

Use el rol/política de confianza reales de Pod Identity o IRSA, no una identidad supuesta del nodo. Las claves KMS del cliente requieren la política/concesión de clave y permisos pertinentes de cifrado/descifrado; la condición documentada para CreateGrant incluye kms:GrantIsForAWSResource. El permiso para aprovisionar un volumen no demuestra por sí solo el permiso para usar la clave KMS seleccionada ni para conectarlo al nodo previsto. Estos comandos de diagnóstico no realizan cambios de IAM.

### Puntos de montaje y Access Points de EFS

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${FILE_SYSTEM_ID:?Use the owned EFS filesystem}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-mount-targets --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
: "${MOUNT_TARGET_ID:?Use the relevant mount target}"
aws efs describe-mount-target-security-groups --region "$AWS_REGION" --mount-target-id "$MOUNT_TARGET_ID"
: "${EFS_SECURITY_GROUP_ID:?Use an observed mount-target security group}"
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$EFS_SECURITY_GROUP_ID"
```
Compruebe el tipo de sistema de archivos/región, los puntos de montaje accesibles, DNS, reglas TCP 2049 y ambas direcciones de red. EFS Regional y One Zone tienen comportamientos distintos ante fallos. La autorización de IAM, la identidad POSIX/directorio de Access Point y el contexto de seguridad del Pod son capas independientes. El siguiente ejemplo de configuración usa un sistema de archivos existente e ID de marcador de posición; no es una receta completa para aprovisionar un sistema de archivos/rol/red.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  gidRangeStart: '1000'
  gidRangeEnd: '2000'
  basePath: /diagnostics-example
mountOptions:
- tls
reclaimPolicy: Retain
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: diagnostics-example
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: reviewed-efs
  resources:
    requests:
      storage: 5Gi
```
Una solicitud de PVC de 5Gi no es una cuota de capacidad impuesta en EFS. Los Access Points pueden imponer una identidad POSIX del lado del servidor; no deduzca el acceso únicamente del UID del Pod cliente ni lo corrija con chmod generalizado. El cifrado TLS del montaje y el cifrado en reposo del sistema de archivos son distintos. Retain requiere un plan explícito de limpieza de datos/Access Points y puede dejar recursos facturables. EFS en Fargate tiene una ruta de aprovisionamiento estático propia; no presuponga que este ejemplo dinámico se aplica a todos los tipos de nodo.

### Estado de PVC/PV y protección contra eliminación

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?Set the owned claim name}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{
  name:.metadata.name,namespace:.metadata.namespace,uid:.metadata.uid,
  deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
  phase:.status.phase,conditions:.status.conditions,volumeName:.spec.volumeName,
  hasStorageClassName:(.spec | has("storageClassName")),
  storageClassName:.spec.storageClassName,accessModes:.spec.accessModes,resources:.spec.resources
}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json | jq --arg claim "$PVC_NAME" '[
  .items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName? == $claim)) |
  {name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
   node:.spec.nodeName,phase:.status.phase,deleting:.metadata.deletionTimestamp}
]'
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -z "$PV_NAME" ]; then
  echo "No bound PV: inspect StorageClass, consumer scheduling and provisioning events."
else
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o json | jq '{
    name:.metadata.name,uid:.metadata.uid,claimRef:.spec.claimRef,
    deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
    reclaimPolicy:.spec.persistentVolumeReclaimPolicy,csi:.spec.csi,nodeAffinity:.spec.nodeAffinity
  }'
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json | jq --arg pv "$PV_NAME" '[
    .items[] | select(.spec.source.persistentVolumeName == $pv) |
    {name:.metadata.name,driver:.spec.attacher,node:.spec.nodeName,status:.status}
  ]'
fi
```
Los nombres de PVC son locales al espacio de nombres; la búsqueda del consumidor debe utilizar el espacio de nombres de la claim. Inspeccione los UID de claim/PV, los propietarios de controladores, VolumeAttachments y finalizers. La marca deletion timestamp produce el estado de presentación Terminating; no es un status.phase adicional de PVC. Pending puede ser esperado con WaitForFirstConsumer hasta que exista un consumidor programable. La omisión de storageClassName difiere de una cadena vacía explícita, que solicita no usar ninguna clase.

No anule todos los finalizers de PVC/PV para finalizar la eliminación. La protección de PVC, el trabajo de eliminación/desconexión de CSI y la política de recuperación protegen distintas partes del ciclo de vida. Primero identifique los consumidores (incluidos los controladores que podrían recrearlos), el estado de conexión, los errores del controlador, las copias de seguridad y la propiedad de los datos. Una reparación de huérfanos como último recurso requiere el procedimiento de recuperación específico del driver y un estado de datos/conexión verificado; eliminar metadatos no realiza una desconexión segura ni restaura los datos. La eliminación puede borrar el almacenamiento subyacente, y Retain no es una copia de seguridad.

### WaitForFirstConsumer, topología y cifrado

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-ebs-wffc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: 'true'
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```
Este es el provisioner de EBS CSI estándar. WaitForFirstConsumer tiene en cuenta las restricciones del scheduler al aprovisionar/enlazar inicialmente; no hace que EBS abarque varias zonas ni repara un volumen atrapado en una zona de disponibilidad deteriorada. Si restringe cargas de trabajo a zonas como ap-northeast-2a/2c, alinee sus restricciones de programación con la topología CSI y la capacidad disponibles reales. No dé por sentado que la primera expresión de afinidad del PV siempre es la zona ni que la afinidad solicitada por un Pod coincide con su ubicación real.

```bash
# Use the actual consumer node, not the Pod's requested node-affinity text.
: "${NODE_NAME:?Set an observed consumer node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  name:.metadata.name,providerID:.spec.providerID,
  topologyLabels:(.metadata.labels | with_entries(select(.key | contains("topology"))))
}'
kubectl --context "$KUBE_CONTEXT" get csinode "$NODE_NAME" -o json | jq '.spec.drivers'
# For an actual EBS-backed PV, inspect the volume handle and Region before this lookup.
: "${AWS_REGION:?}"; : "${EBS_VOLUME_ID:?Set the inspected EBS volume ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[].{ID:VolumeId,AZ:AvailabilityZone,State:State,Encrypted:Encrypted,KMS:KmsKeyId,Attachments:Attachments}'
```
Para Auto Mode, use su provisioner independiente y sus requisitos de compatibilidad de nodo. **Establezca encrypted: "true" explícitamente e inspeccione el volumen/clave KMS resultantes.** La tabla actual de parámetros de Auto Mode tiene encrypted desactivado de forma predeterminada; que los discos raíz/de datos de los nodos de Auto Mode estén cifrados no demuestra que todos los PVC de cargas de trabajo lo estén. Cambiar StorageClass no modifica retroactivamente un volumen existente.

Un volumen EBS existente no se puede conectar entre zonas solo porque la clase use WaitForFirstConsumer. Una migración/recuperación requiere el procedimiento documentado de snapshot o volumen estático controlado, etiquetas de propiedad/IAM correctas y gestión de datos coherente con la aplicación; no consiste en cambiar el nombre del driver. Los controladores/CRD de snapshot son requisitos previos independientes, y crear un snapshot no demuestra que se pueda restaurar. ReadWriteOnce permite el acceso desde un nodo y no significa universalmente «un Pod»; el aislamiento SELinux de Auto Mode puede añadir restricciones entre Pods. Conserve los datos y revise el modelo de acceso/coherencia previsto antes de cambiarlo.

[EBS CSI/IAM](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Ámbitos de políticas administradas](https://docs.aws.amazon.com/eks/latest/userguide/security-iam-awsmanpol.html) · [Parámetros de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [Ciclo de vida de PV](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

---

<span id="7-observability-architecture"></span>

## 7. Arquitectura de observabilidad

### Inspeccionar la recopilación existente

No instale el complemento antiguo v1.0.0 como atajo de respuesta a incidentes. Seleccione un complemento/chart compatible actualmente y un único propietario mediante la [guía de configuración de supervisión](06-eks-monitoring-logging.md). Inspeccione IAM/Pod Identity, los ajustes de registro/métricas, la aplicabilidad a nodos y las opciones de instrumentación/reinicio automático antes de hacer cambios. Las versiones recientes de operadores pueden afectar a la instrumentación de aplicaciones y al despliegue; instalar dos propietarios puede generar conflictos.

```bash
# Read-only: inspect the installed owner/version rather than installing during triage.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name amazon-cloudwatch-observability \
  --query 'addon.{Version:addonVersion,Status:status,Issues:health.issues,Configuration:configurationValues,Role:serviceAccountRoleArn,PodIdentity:podIdentityAssociations}'
kubectl --context "$KUBE_CONTEXT" -n amazon-cloudwatch get pods,deployments,daemonsets -o wide
# If Helm owns the installation, inspect that existing release instead.
helm list -n amazon-cloudwatch --kube-context "$KUBE_CONTEXT"
```
La ausencia del complemento puede significar que Helm es propietario de la recopilación o que el componente no está instalado. Que el Pod esté Running/el complemento ACTIVE no demuestra la entrega, cobertura ni estado visible para el usuario. Verifique los destinos de scraping, IAM/red/TLS, errores de ingestión, retención y costes; los ejemplos siguientes suponen esos requisitos previos, no una plataforma de producción probada.

### PromQL: definir qué mide cada métrica

Las consultas presuponen un conjunto de datos **de un solo clúster y correctamente etiquetado**, y el espacio de nombres diagnostics-example seleccionado. Añada los selectores reales de clúster/job para un backend compartido. Deben recopilarse cAdvisor y kube-state-metrics; estas series no aparecen simplemente por escribir una consulta. La agregación elimina etiquetas duplicadas de instancias de exportador solo dentro del alcance indicado. Compruebe las marcas de tiempo, la identidad de Pod/contenedor y la disponibilidad de métricas específica de cada versión, incluidas las métricas de última terminación.

#### Fracción de periodos CFS limitados por contenedor

```promql
sum by (namespace,pod,container) (rate(container_cpu_cfs_throttled_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))
/ on (namespace,pod,container) (sum by (namespace,pod,container) (rate(container_cpu_cfs_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])) > 0)
```

#### Diez contenedores principales por fracción de periodos limitados

```promql
topk(10, sum by (namespace,pod,container) (rate(container_cpu_cfs_throttled_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))
/ on (namespace,pod,container) (sum by (namespace,pod,container) (rate(container_cpu_cfs_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])) > 0))
```

#### El motivo de terminación informado más recientemente es OOM; no es un recuento de eventos nuevos

```promql
max by (namespace,pod,container) (kube_pod_container_status_last_terminated_reason{namespace="diagnostics-example",reason="OOMKilled"} == 1)
```

#### Aumento reciente de reinicios cuyo último motivo informado es OOM; no es un recuento exacto de OOM

```promql
(max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m])) > 0)
and on (namespace,pod,container) (max by (namespace,pod,container) (kube_pod_container_status_last_terminated_reason{namespace="diagnostics-example",reason="OOMKilled"} == 1))
```

#### Conjunto de trabajo / límite de memoria configurado positivo por contenedor

```promql
max by (namespace,pod,container) (container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"})
/ on (namespace,pod,container)
max by (namespace,pod,container) (kube_pod_container_resource_limits{namespace="diagnostics-example",resource="memory",unit="byte"} > 0)
```

#### Aumento estimado de reinicios de contenedores normales por Pod durante 15 minutos

```promql
sum by (namespace,pod) (max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m])))
```

#### Diez Pods principales por aumento estimado de reinicios

```promql
topk(10, sum by (namespace,pod) (max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m]))))
```

#### Motivo de espera CrashLoopBackOff informado actualmente

```promql
max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"} == 1)
```

#### Pods activos que no se están eliminando y tienen Ready=false, incluidos los Pods Running

```promql
((1 - max by (namespace,pod) (kube_pod_status_ready{namespace="diagnostics-example",condition="true"})) > 0)
and on (namespace,pod) (max by (namespace,pod) (kube_pod_status_phase{namespace="diagnostics-example",phase=~"Pending|Running|Unknown"} == 1))
unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="diagnostics-example"}
```

Los periodos CFS limitados no son utilización de CPU ni un porcentaje del tiempo de CPU transcurrido. Los ratios de memoria solo incluyen contenedores con límite positivo configurado; los límites/datos ausentes no equivalen a utilización cero. increase() es una estimación de contador extrapolada que tiene en cuenta reinicios y puede ser fraccionaria; changes(restarts_total) cuenta cambios observados del valor, no eventos OOM. El último motivo de terminación junto con un aumento de reinicios es una correlación, no un recuento exacto de eventos OOM ni una prueba de fuga de memoria. CrashLoopBackOff se comprueba mediante el motivo de espera, no se deduce de cada reinicio.

La consulta de readiness incluye Pods Running pero NotReady y excluye los Pods terminales/en proceso de eliminación. Estos ejemplos no sustituyen la supervisión independiente de scraping/destinos ausentes. La ausencia de series devueltas no debe interpretarse como prueba de que las cargas de trabajo estén en buen estado.

### CloudWatch Logs Insights

Ejecute cada bloque por separado en el grupo de registros/intervalo de tiempo correspondiente. Los campos kubernetes.* dependen del esquema del recopilador; inspeccione los registros reales. Los recuentos de mensajes de error y las palabras clave OOM son indicios de diagnóstico, no tasas de error de solicitudes ni historiales completos de fallos.

#### Muestras de mensajes de error, no una tasa de error de solicitudes

```text
fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name
| filter kubernetes.namespace_name = "diagnostics-example"
| filter @message like /error|Error|ERROR|exception|Exception|EXCEPTION/
| sort @timestamp desc
| limit 100
```

#### Un Pod en el espacio de nombres seleccionado

```text
fields @timestamp, @message
| filter kubernetes.namespace_name = "diagnostics-example" and kubernetes.pod_name = "REPLACE_WITH_OBSERVED_POD"
| sort @timestamp desc
| limit 100
```

#### Campo de tiempo de respuesta de la aplicación, solo si el formato del registro lo define

```text
fields @timestamp, @message
| filter kubernetes.namespace_name = "diagnostics-example"
| parse @message /response_time=(?<response_time>\d+)ms/
| filter ispresent(response_time)
| stats avg(response_time) as avg_response_ms, max(response_time) as max_response_ms by bin(5m)
```

#### Mensajes de registro relacionados con OOM que requieren correlación

```text
fields @timestamp, @message
| filter @message like /OOMKilled|Out of memory|oom-kill/
| sort @timestamp desc
| limit 50
```

### Selección y alertas de PrometheusRule

Sustituya la etiqueta release por el valor que requiera el ruleSelector de Prometheus previsto y verifique ruleNamespaceSelector. Que se acepte un CRD no demuestra que la regla se haya cargado ni que funcionen las notificaciones. Los umbrales y las duraciones son ejemplos que se deben ajustar al SLO de la carga de trabajo; las alertas no autorizan la eliminación/reinicio automáticos.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-eks-diagnostics
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: reviewed-eks-diagnostics
    rules:
    - alert: NodeNotReady
      expr: kube_node_status_condition{condition="Ready",status="true"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Node {{ $labels.node }} reports Ready=false/unknown; inspect the
          node condition and heartbeat.
    - alert: NodeMemoryPressure
      expr: kube_node_status_condition{condition="MemoryPressure",status="true"} ==
        1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Node {{ $labels.node }} reports MemoryPressure.
    - alert: NodeDiskPressure
      expr: kube_node_status_condition{condition="DiskPressure",status="true"} ==
        1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Node {{ $labels.node }} reports DiskPressure.
    - alert: PodCrashLooping
      expr: max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"}
        == 1)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: '{{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container }}
          reports CrashLoopBackOff.'
    - alert: ActivePodNotReady
      expr: '((1 - max by (namespace,pod) (kube_pod_status_ready{namespace="diagnostics-example",condition="true"}))
        > 0)

        and on (namespace,pod) (max by (namespace,pod) (kube_pod_status_phase{namespace="diagnostics-example",phase=~"Pending|Running|Unknown"}
        == 1))

        unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="diagnostics-example"}'
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: Active Pod {{ $labels.namespace }}/{{ $labels.pod }} is not Ready.
    - alert: ContainerRecentOOM
      expr: '(max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m]))
        > 0)

        and on (namespace,pod,container) (max by (namespace,pod,container) (kube_pod_container_status_last_terminated_reason{namespace="diagnostics-example",reason="OOMKilled"}
        == 1))'
      for: 0m
      labels:
        severity: warning
      annotations:
        summary: Recent restart and last reported OOM for {{ $labels.namespace }}/{{
          $labels.pod }}/{{ $labels.container }}; verify events.
    - alert: HighCPUThrottling
      expr: '(sum by (namespace,pod,container) (rate(container_cpu_cfs_throttled_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))

        / on (namespace,pod,container) (sum by (namespace,pod,container) (rate(container_cpu_cfs_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))
        > 0)) > 0.5'
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: More than 50% of CFS periods were throttled for {{ $labels.namespace
          }}/{{ $labels.pod }}/{{ $labels.container }}.
```
```bash
# Read-only: this rule must be selected by the intended Prometheus instance.
kubectl --context "$KUBE_CONTEXT" -n monitoring get prometheus -o json | jq '[
  .items[] | {name:.metadata.name,ruleSelector:.spec.ruleSelector,ruleNamespaceSelector:.spec.ruleNamespaceSelector}
]'
kubectl --context "$KUBE_CONTEXT" -n monitoring get prometheusrule reviewed-eks-diagnostics -o yaml
```
### ADOT Collector: canalizaciones y requisitos previos explícitos

El ejemplo usa la configuración con objeto v1beta1 revisada de Operator 0.158.0 y componentes ADOT 0.50.0. Prepare el espacio de nombres, Operator/CRD, el Secret TLS del receptor, la CA de cliente de confianza y una identidad AWS de ServiceAccount configurada adecuadamente. El Role de abajo solo permite la detección de Pods de Kubernetes; no concede acceso a X-Ray, CloudWatch Logs ni AMP. Revise los permisos IAM del exporter y los valores reales de región/grupo de registros/workspace antes del despliegue. El ejemplo no se ha ejecutado ni se afirma que esté listo para producción.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: adot-diagnostics
  namespace: diagnostics-example
```
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: adot-pod-discovery
  namespace: diagnostics-example
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
```
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: adot-pod-discovery
  namespace: diagnostics-example
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: adot-pod-discovery
subjects:
- kind: ServiceAccount
  name: adot-diagnostics
  namespace: diagnostics-example
```
```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-diagnostics
  namespace: diagnostics-example
spec:
  mode: deployment
  replicas: 1
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-diagnostics
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: 'true'
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: '1'
      memory: 512Mi
  volumes:
  - name: receiver-tls
    secret:
      secretName: otel-receiver-tls
  volumeMounts:
  - name: receiver-tls
    mountPath: /etc/otel/tls
    readOnly: true
  config:
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
            tls:
              cert_file: /etc/otel/tls/tls.crt
              key_file: /etc/otel/tls/tls.key
          http:
            endpoint: 0.0.0.0:4318
            tls:
              cert_file: /etc/otel/tls/tls.crt
              key_file: /etc/otel/tls/tls.key
      prometheus:
        config:
          scrape_configs:
          - job_name: owned-pod-metrics
            scrape_interval: 30s
            kubernetes_sd_configs:
            - role: pod
              namespaces:
                names:
                - diagnostics-example
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_annotation_prometheus_io_scrape
              action: keep
              regex: 'true'
            - source_labels:
              - __meta_kubernetes_pod_phase
              action: keep
              regex: Running
            - source_labels:
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: metrics
            - source_labels:
              - __meta_kubernetes_pod_container_port_protocol
              action: keep
              regex: TCP
            - source_labels:
              - __meta_kubernetes_pod_annotation_prometheus_io_path
              action: replace
              target_label: __metrics_path__
              regex: (.+)
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
            - source_labels:
              - __meta_kubernetes_pod_container_name
              target_label: container
    processors:
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
        spike_limit_percentage: 15
      batch:
        timeout: 30s
        send_batch_size: 8192
    exporters:
      awsxray:
        region: us-west-2
        local_mode: true
        no_verify_ssl: false
        index_all_attributes: false
        telemetry:
          enabled: false
      awsemf:
        region: us-west-2
        namespace: EKS/DiagnosticsExample
        log_group_name: /aws/eks/REPLACE_WITH_CLUSTER/otel-metrics
        log_stream_name: adot-diagnostics
        dimension_rollup_option: NoDimensionRollup
        resource_to_telemetry_conversion:
          enabled: false
      prometheusremotewrite:
        endpoint: https://aps-workspaces.us-west-2.amazonaws.com/workspaces/REPLACE_WITH_WORKSPACE_ID/api/v1/remote_write
        auth:
          authenticator: sigv4auth
        resource_to_telemetry_conversion:
          enabled: false
    extensions:
      sigv4auth:
        region: us-west-2
        service: aps
      health_check:
        endpoint: 0.0.0.0:13133
    service:
      extensions:
      - sigv4auth
      - health_check
      pipelines:
        traces:
          receivers:
          - otlp
          processors:
          - memory_limiter
          - batch
          exporters:
          - awsxray
        metrics:
          receivers:
          - otlp
          - prometheus
          processors:
          - memory_limiter
          - batch
          exporters:
          - awsemf
          - prometheusremotewrite
```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: adot-otlp-ingress
  namespace: diagnostics-example
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/managed-by: opentelemetry-operator
      app.kubernetes.io/instance: diagnostics-example.adot-diagnostics
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          telemetry-client: 'true'
    ports:
    - protocol: TCP
      port: 4317
    - protocol: TCP
      port: 4318
```
Los clientes OTLP deben confiar en el certificado y usar el Service, protocolo y puerto 4317/4318 generados correctos. Debe existir aplicación de NetworkPolicy; la política selecciona solo los Pods Collector y permite clientes etiquetados del mismo espacio de nombres. Configure TLS/autenticación de destinos de métricas y las políticas de ingreso de cargas de trabajo cuando sea necesario. La detección de Prometheus se limita a un espacio de nombres y acepta únicamente Pods Running anotados con un puerto TCP llamado metrics; el puerto procede de ese endpoint, lo que evita una reescritura no configurada de la anotación de puerto.

Una réplica evita duplicar todo el scraping en este ejemplo; el escalado requiere un diseño de asignador/partición de destinos. memory_limiter precede a batch, pero los ajustes de memoria/batch no garantizan una entrega sin pérdidas. AWS X-Ray recibe trazas, awsemf escribe métricas mediante CloudWatch Logs y AMP recibe remote write autenticado con SigV4. Las métricas personalizadas EKS/DiagnosticsExample no son automáticamente el esquema/dashboard de Container Insights. Los nombres de registro fijos evitan que un {ClusterName} no resuelto quede indefinido; los atributos de recursos del exporter aún pueden afectar al enrutamiento, así que limite los datos del productor y IAM. No convierta todos los atributos de recursos en etiquetas de métricas sin revisar la cardinalidad.

Conserve la identidad del servicio de aplicación y la propagación; un Collector por sí solo no instrumenta todas las solicitudes ni elimina los huecos de muestreo. Elimine conjuntamente los exporters sin uso y sus referencias en las canalizaciones. En esta auditoría no se produjo telemetría, no se realizaron solicitudes a AWS ni se reiniciaron aplicaciones, ni se instaló Collector u Operator.

[Configuración de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html) · [Métricas de Pod](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md) · [API de Operator](https://github.com/open-telemetry/opentelemetry-operator/releases/tag/v0.158.0) · [Versiones de componentes ADOT](https://github.com/aws-observability/aws-otel-collector/blob/v0.50.0/go.mod) · [Receptor Prometheus](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/receiver/prometheusreceiver) · [Exporter EMF](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awsemfexporter)

---

<span id="8-failure-detection-architecture"></span>

## 8. Arquitectura de detección de fallos

### Canalización de detección de cuatro capas

![Canalización de detección de fallos de EKS en cuatro etapas, que muestra métricas, registros, trazas y eventos que fluyen desde las fuentes de datos a través de herramientas de recopilación (CloudWatch Agent, Fluent Bit, ADOT Collector, Prometheus), hacia una capa de análisis (CloudWatch Logs Insights, alarmas de métricas, detección de anomalías, alarmas compuestas) y hasta canales de alerta (SNS, Slack, PagerDuty, EventBridge).](../.gitbook/assets/en-eks-11-eks-advanced-debugging-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-3.html)

La figura muestra alternativas conceptuales, no un despliegue totalmente conectado. La recopilación, el almacenamiento/consulta, la evaluación de alarmas y las notificaciones requieren cada uno configuración, identidad, acceso a la red y evidencia de entrega satisfactoria. El análisis de trazas también requiere el backend de trazas configurado; Logs Insights no convierte automáticamente todas las trazas en alarmas.

### Recopilación de registros nativa de AWS: contrato de configuración

Lo siguiente es un ejemplo de configuración de Fluent Bit para nodos Linux revisados, no un DaemonSet instalado. Use un propietario administrado existente o la [configuración completa de supervisión](06-eks-monitoring-logging.md); no instale un segundo recopilador que compita con el primero. El proceso necesita montajes de registros del host de solo lectura, RBAC de metadatos de Kubernetes, una identidad AWS adecuada y directorios **separados** de puntos de control/búfer con permiso de escritura. Defina AWS_REGION, CLUSTER_NAME y NODE_NAME mediante el despliegue/Downward API. Cree y autorice previamente el grupo de registros de destino porque auto_create_group es false.

```text
[SERVICE]
    Flush                   5
    Grace                   30
    Log_Level               info
    Daemon                  off
    storage.path            /var/fluent-bit/buffer
    storage.sync            normal
    storage.checksum        on
    storage.max_chunks_up   32

[INPUT]
    Name                    tail
    Tag                     kube.*
    Path                    /var/log/containers/*.log
    Exclude_Path            /var/log/containers/*_amazon-cloudwatch_*.log
    multiline.parser        cri
    DB                      /var/fluent-bit/state/containers.db
    Mem_Buf_Limit           50MB
    Skip_Long_Lines         On
    Refresh_Interval        10
    storage.type            filesystem

[FILTER]
    Name                    kubernetes
    Match                   kube.*
    Kube_URL                https://kubernetes.default.svc:443
    Kube_CA_File            /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File         /var/run/secrets/kubernetes.io/serviceaccount/token
    Kube_Tag_Prefix         kube.var.log.containers.
    Merge_Log               On
    Merge_Log_Key           log_processed
    K8S-Logging.Exclude      Off

[OUTPUT]
    Name                    cloudwatch_logs
    Match                   kube.*
    region                  ${AWS_REGION}
    log_group_name          /aws/eks/${CLUSTER_NAME}/containers
    log_stream_name         ${NODE_NAME}
    auto_create_group       false
    storage.total_limit_size 100M
```
El parser cri multiline integrado gestiona el formato de flujo/registro parcial CRI que utiliza containerd; un parser JSON de Docker es un formato distinto. Ajuste la exclusión de autorregistros al espacio de nombres real del agente. log_processed contiene el JSON fusionado de la aplicación y sirve para el ejemplo de filtro de métricas de abajo. El almacenamiento en búfer del sistema de archivos y los puntos de control DB resuelven problemas distintos: no garantizan entrega sin pérdidas ni exactamente una vez. Una cola de salida llena descarta los bloques más antiguos, omitir líneas largas puede perder registros y la rotación del contenedor/nodo puede eliminar datos no leídos. Se deben supervisar los límites de tamaño, la retención, el espacio de disco y los fallos de IAM/KMS. Fargate/Auto Mode/Windows tienen sus propias rutas compatibles de recopilación; este ejemplo con montajes del host no es portable universalmente.

### Alertmanager: configuración cargada y archivos Secret

Para Prometheus Operator, use un Secret que contenga la clave alertmanager.yaml y haga referencia a ella con el configSecret existente de la especificación de Alertmanager. Un ConfigMap llamado alertmanager-config no se consume automáticamente. Lo siguiente es un **fragmento de spec** que se debe integrar con el propietario revisado de Helm/operator, no un despliegue completo nuevo de Alertmanager. Los Secrets separados deben proporcionar entradas url/key, montadas en `/etc/alertmanager/secrets/<secret-name>/`.

```yaml
spec:
  configSecret: alertmanager-reviewed
  secrets:
  - alertmanager-slack
  - alertmanager-pagerduty
```
```yaml
global:
  resolve_timeout: 5m
  slack_api_url_file: /etc/alertmanager/secrets/alertmanager-slack/url
route:
  receiver: default
  group_by:
  - alertname
  - cluster
  - namespace
  - pod
  - node
  - severity
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
  - matchers:
    - severity="critical"
    receiver: critical
  - matchers:
    - severity="warning"
    receiver: warnings
receivers:
- name: default
  slack_configs:
  - channel: '#alerts-default'
    send_resolved: true
- name: critical
  slack_configs:
  - channel: '#incidents'
    send_resolved: true
  pagerduty_configs:
  - routing_key_file: /etc/alertmanager/secrets/alertmanager-pagerduty/key
    severity: critical
- name: warnings
  slack_configs:
  - channel: '#alerts-warnings'
    send_resolved: true
    title: '{{ .Status | toUpper }}: {{ .CommonAnnotations.summary }}'
    text: '{{ .CommonAnnotations.description }}'
inhibit_rules:
- source_matchers:
  - severity="critical"
  target_matchers:
  - severity="warning"
  equal:
  - alertname
  - cluster
  - namespace
  - pod
  - container
  - node
```
Esta configuración envía las alertas críticas tanto a Slack como a PagerDuty mediante un receptor, las alertas de advertencia a Slack y las demás alertas al receptor predeterminado. continue:true no invoca también el receptor padre/predeterminado después de coincidir con una ruta secundaria. Los matchers/source_matchers/target_matchers actuales evitan la sintaxis de asignación obsoleta. Las etiquetas de identidad del recurso incluidas en equal para la inhibición hacen que las etiquetas ausentes se comparen como vacías, así que revise el contrato real de etiquetas para evitar suprimir una alerta de otro Pod/nodo. Valide por separado la configuración cargada, las rutas y el transporte. El análisis y el enrutamiento sintético no demuestran que Slack/PagerDuty haya aceptado una notificación; el correo electrónico/SMS requieren cableado explícito adicional.

### Umbrales de CloudWatch, anomalías y alarmas compuestas

Use dimensiones, unidades y estadísticos reales de las métricas. Un filtro de list-metrics puede devolver series con más dimensiones que el filtro; seleccione un conjunto de dimensiones publicadas **completo**. Container Insights debe estar configurado; el espacio de nombres de métricas ADOT personalizado de la sección anterior no lo sustituye. node_cpu_utilization es distinto de la relación CPU/solicitud/límite de un Pod. Los nombres de alarma, ARN de tema y valores de clúster de abajo son ejemplos; revise los nombres existentes antes de ejecutar comandos que puedan reemplazar su configuración. Los temas de notificación, las políticas de acceso/KMS y los destinatarios deben prepararse por separado.

```bash
# Read-only: select an actual published metric and its complete dimension set.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace ContainerInsights \
  --metric-name node_cpu_utilization --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --query 'Metrics[].{Name:MetricName,Namespace:Namespace,Dimensions:Dimensions}'
```
```bash
# MUTATION: creates/replaces this named alarm and can trigger configured notifications.
: "${AWS_REGION:?}"; : "${SNS_TOPIC_ARN:?Use the owned topic ARN}"
: "${METRIC_DIMENSIONS_FILE:?JSON array containing one reviewed complete dimension set}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name owned-eks-high-cpu --alarm-description "Example node CPU utilization threshold" \
  --namespace ContainerInsights --metric-name node_cpu_utilization \
  --dimensions "file://$METRIC_DIMENSIONS_FILE" --statistic Average \
  --period 300 --evaluation-periods 3 --datapoints-to-alarm 3 \
  --threshold 80 --comparison-operator GreaterThanThreshold \
  --treat-missing-data missing --alarm-actions "$SNS_TOPIC_ARN"
```
El ejemplo utiliza tres periodos de 300 segundos y tres puntos de datos que superan el umbral: una ventana de evaluación de 15 minutos, no un tiempo de detección garantizado de dos minutos. TreatMissingData=missing conserva el estado de datos ausentes; elija otra política solo para una métrica cuya semántica lo justifique. Inspeccione el estado inicial INSUFFICIENT_DATA y las transiciones de estado en vez de suponer que la creación implica una alarma funcional.

El ejemplo de anomalía sigue la estructura de métricas/banda específica de la API para anomalías: m1 es la serie medida y ad1 es la banda seleccionada por ThresholdMetricId. El modelo, el periodo, el estadístico y las dimensiones deben coincidir. El modelo necesita datos/formación adecuados y no garantiza predecir una interrupción. Las dimensiones de ejemplo literales del JSON se deben sustituir para que coincidan con el archivo de dimensiones revisado antes de usarlo.

```json
{
  "AlarmName": "owned-eks-anomaly-cpu",
  "AlarmDescription": "Example anomaly model for an observed Container Insights metric",
  "Metrics": [
    {
      "Id": "m1",
      "ReturnData": true,
      "MetricStat": {
        "Metric": {
          "Namespace": "ContainerInsights",
          "MetricName": "node_cpu_utilization",
          "Dimensions": [
            {
              "Name": "ClusterName",
              "Value": "REPLACE_WITH_CLUSTER"
            }
          ]
        },
        "Period": 300,
        "Stat": "Average"
      }
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)"
    }
  ],
  "EvaluationPeriods": 3,
  "ThresholdMetricId": "ad1",
  "ComparisonOperator": "LessThanLowerOrGreaterThanUpperThreshold",
  "TreatMissingData": "missing",
  "AlarmActions": [
    "arn:aws:sns:us-west-2:123456789012:owned-eks-alerts"
  ]
}
```
```bash
# MUTATIONS: same observed metric/statistic/dimensions as the reviewed model.
aws cloudwatch put-anomaly-detector --region "$AWS_REGION" \
  --namespace ContainerInsights --metric-name node_cpu_utilization --stat Average \
  --dimensions "file://$METRIC_DIMENSIONS_FILE"
# Replace the example cluster/topic/metric dimensions in the JSON before this request.
aws cloudwatch put-metric-alarm --region "$AWS_REGION" --cli-input-json file://anomaly-alarm-reviewed.json
```
```bash
# Read-only prerequisites: both named alarms must exist and have understood state.
aws cloudwatch describe-alarms --region "$AWS_REGION" \
  --alarm-names owned-eks-high-cpu owned-eks-high-memory
# MUTATION: the AND policy requires both alarms to be ALARM.
aws cloudwatch put-composite-alarm --region "$AWS_REGION" \
  --alarm-name owned-eks-combined-resource \
  --alarm-rule 'ALARM("owned-eks-high-cpu") AND ALARM("owned-eks-high-memory")' \
  --alarm-actions "$SNS_TOPIC_ARN"
```
El ejemplo de alarma compuesta presupone que ambas alarmas referenciadas ya existen en la cuenta/región correspondiente; requiere deliberadamente que las dos estén en ALARM. AND y OR expresan políticas de incidentes distintas, no garantías de resiliencia intercambiables. Según la documentación de PutMetricAlarm, una alarma de modelo de anomalías no puede tener acciones de Auto Scaling.

### Métricas basadas en registros

El siguiente patrón espera el JSON fusionado de Fluent Bit en log_processed.level. Adáptelo a los registros reales y a una clase de grupo de registros que admita filtros de métricas; no copie un patrón delimitado por espacios con varias elipsis. Un filtro cuenta eventos de registro coincidentes desde su creación, no solicitudes históricas ni errores únicos. defaultValue=0 no demuestra que se entreguen registros cuando no llegan eventos.

```bash
# MUTATION: structured JSON must actually contain log_processed.level.
aws logs put-metric-filter --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/containers" \
  --filter-name OwnedApplicationErrors \
  --filter-pattern '{ $.log_processed.level = "ERROR" }' \
  --metric-transformations "metricName=ApplicationErrors,metricNamespace=EKS/$CLUSTER_NAME/Application,metricValue=1,defaultValue=0,unit=Count"
```
### Objetivos de madurez y límites de automatización

Los valores originales de MTTD de 30/15/5/2 minutos se conservan como objetivos de planificación no verificados. Las configuraciones de aquí no demuestran esos resultados; mida de forma coherente las marcas de tiempo de ocurrencia/detección/restauración en todos los incidentes. La detección ML/anomalías no establece por sí sola la precisión predictiva ni autoriza la corrección automática.

| Nivel | Objetivo ilustrativo original de MTTD | Capacidad que se debe verificar |
| --- | --- | --- |
| Básico | 30 minutos | Métricas básicas e investigación manual de registros |
| Reactivo | 15 minutos | Umbrales ajustados, métricas de registros y paneles |
| Proactivo | 5 minutos | Alarmas correlacionadas y runbooks revisados |
| Objetivo de diseño predictivo | 2 minutos | Predicción validada, automatización acotada y ejercicios controlados |

### Recepción de diagnóstico EventBridge → Lambda

Use una regla de alarma con cuenta/región exactas y autorización explícita para invocar el destino. El ejemplo clasifica un evento y registra una solicitud de diagnóstico pequeña; no tiene cliente de mutación de Kubernetes/AWS. Una alarma agregada no identifica de forma fiable el nombre/espacio de nombres/UID de un Pod, por lo que eliminar un Pod supuesto no es una reparación predeterminada adecuada de CrashLoopBackOff.

```json
{
  "source": [
    "aws.cloudwatch"
  ],
  "detail-type": [
    "CloudWatch Alarm State Change"
  ],
  "account": [
    "123456789012"
  ],
  "region": [
    "us-west-2"
  ],
  "resources": [
    "arn:aws:cloudwatch:us-west-2:123456789012:alarm:owned-eks-pod-crashlooping"
  ],
  "detail": {
    "alarmName": [
      "owned-eks-pod-crashlooping"
    ],
    "state": {
      "value": [
        "ALARM"
      ]
    }
  }
}
```
```python
"""EventBridge alarm intake example: classification/logging only, no AWS or Kubernetes client."""
import datetime
import json
import os

def classify_alarm(event, expected_alarm_arn, now):
    parts=expected_alarm_arn.split(':',5)
    if len(parts)!=6 or parts[2]!='cloudwatch' or not parts[5].startswith('alarm:'):
        raise ValueError('Configure one exact CloudWatch alarm ARN')
    if not isinstance(event,dict):
        return {'status':'ignored','reason':'invalid event'}
    detail=event.get('detail')
    state=detail.get('state') if isinstance(detail,dict) else None
    resources=event.get('resources')
    if (event.get('source')!='aws.cloudwatch'
        or event.get('detail-type')!='CloudWatch Alarm State Change'
        or event.get('account')!=parts[4] or event.get('region')!=parts[3]
        or not isinstance(resources,list) or expected_alarm_arn not in resources
        or not isinstance(state,dict) or state.get('value')!='ALARM'
        or detail.get('alarmName')!=parts[5][len('alarm:'):]):
        return {'status':'ignored','reason':'outside configured alarm/state'}
    event_id=event.get('id')
    if not isinstance(event_id,str) or not 1<=len(event_id)<=128:
        return {'status':'ignored','reason':'missing or invalid event ID'}
    try:
        changed=datetime.datetime.fromisoformat(state['timestamp'].replace('Z','+00:00'))
        if changed.tzinfo is None or now.tzinfo is None:
            raise ValueError('Timezone required')
        age=(now-changed).total_seconds()
    except (KeyError,TypeError,ValueError,AttributeError):
        return {'status':'ignored','reason':'invalid timestamp'}
    if age < -300 or age > 3600:
        return {'status':'ignored','reason':'outside example event-age window'}
    return {'status':'diagnostic_request','event_id':event_id,
            'alarm_arn':expected_alarm_arn,'state_changed_at':changed.isoformat(),
            'action':'inspect evidence and select a reviewed runbook'}

def lambda_handler(event,context):
    result=classify_alarm(event,os.environ['EXPECTED_ALARM_ARN'],
                          datetime.datetime.now(datetime.timezone.utc))
    print(json.dumps(result))
    return result
```
Establezca EXPECTED_ALARM_ARN en la alarma exacta de su propiedad. La ventana de antigüedad de una hora/tolerancia de cinco minutos en el futuro son opciones de política de ejemplo. Restrinja a quienes pueden invocar la Lambda real; comprobar campos de eventos no constituye verificación criptográfica del origen. La invocación asíncrona de EventBridge no reenvía el diccionario devuelto como acción: un flujo de trabajo/cola de diagnóstico real debe conectarse explícitamente. Registrar esta selección no significa que se haya «ejecutado una corrección automática».

Antes de habilitar un runbook de mutación, implemente la revalidación de identidad/UID, la deduplicación duradera de ID de eventos, límites de frecuencia, privilegios mínimos, control de concurrencia, comprobaciones de carga de trabajo/datos/PDB, reversión y verificación posterior a la acción. Los reintentos o eventos duplicados no deben provocar eliminaciones repetidas. Este clasificador no afirma que se haya implementado ninguno de esos controles de mutación de producción.

| Gravedad de ejemplo | Slack | PagerDuty | Otros canales | Política de mutación |
| --- | --- | --- | --- | --- |
| P1 Crítica | Incidentes | Política inmediata | Correo electrónico o SMS para jefe de equipo/on-call, si está conectado | Solo un runbook revisado y acotado |
| P2 Alta | Alertas altas | Escalamiento de ejemplo a los 15 minutos | Correo electrónico del equipo, si está conectado | Revisión condicional |
| P3 Media | Alertas | Opcional | Correo electrónico del equipo, si está conectado | Sin cambios automáticos de forma predeterminada |
| P4 Baja | Alertas bajas | Ninguno | Resumen diario de ejemplo | Sin cambios automáticos |

Esta es una política de enrutamiento de ejemplo, no una prueba de que todos los canales estén desplegados o entreguen a tiempo. En esta auditoría no se crearon ni ejecutaron alarmas, temas, políticas, funciones Lambda, recursos en la nube ni notificaciones.

[Análisis CRI de Fluent Bit](https://docs.fluentbit.io/manual/administration/configuring-fluent-bit/multiline-parsing) · [Límites de almacenamiento en búfer](https://docs.fluentbit.io/manual/administration/buffering-and-storage) · [Salida de CloudWatch](https://docs.fluentbit.io/manual/pipeline/outputs/cloudwatch) · [Configuración de Alertmanager 0.34](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/configuration.md) · [Ejemplos de PutMetricAlarm](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html) · [Dimensiones de métricas](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)

---

<span id="9-quick-reference"></span>

## 9. Referencia rápida

### Interprete los síntomas antes de elegir un cambio

| Síntoma | Evidencia e interpretación |
| --- | --- |
| CrashLoopBackOff | Salidas/reinicios repetidos del contenedor con retroceso; inspeccione el código de salida, el último estado, las probes y los registros actuales/anteriores. Exit0 con restartAlways también puede entrar en bucle |
| ImagePullBackOff | Retraso de reintento tras un fallo de descarga; inspeccione el error anterior, la imagen/tag/digest, la plataforma, la identidad de descarga, el registro/red/CA/límites de frecuencia |
| ErrImagePull | Falló un intento de descarga; no demuestra por sí solo que haya un fallo de red ni un problema de IRSA de la aplicación |
| OOMKilled | Correlacione el motivo del runtime, el límite/conjunto de trabajo de memoria y la evidencia del nodo; exit137 por sí solo o un uso elevado por sí solo no demuestran una fuga |
| CreateContainerConfigError | Compruebe las referencias a ConfigMap/Secret/volumen, el espacio de nombres y las claves; evite volcar valores de credenciales |
| Pending: recursos | Compare las solicitudes, la sobrecarga de init/Pod, los recursos asignables, los límites de Pod y los eventos de programación reales antes de aprovisionar |
| Pending: colocación | Inspeccione selector/afinidad/taints/topología/restricciones de almacenamiento; algunos estados Pending son intencionales |
| ContainerCreating | Motivo/estado de presentación del contenedor, no una fase de Pod; inspeccione runtime, imagen, CNI y configuración de volúmenes |
| RunContainerError | Inspeccione el error real de runtime/seguridad/comando; no hay una solución universal de reinicio |
| Fallo del hook postStart | Inspeccione el controlador y el inicio de la aplicación; postStart no garantiza el orden antes de ENTRYPOINT y no tiene un campo timeoutSeconds general |
| Fallo del hook preStop | Inspeccione los errores del controlador y el presupuesto del periodo de gracia, que incluye el tiempo del hook; la terminación forzada no equivale a un drenaje satisfactorio |
| FailedScheduling | Lea el mensaje completo, incluidas las restricciones de PVC/afinidad/recursos, en lugar de suponer que falta CPU |
| FailedMount | Compruebe la propiedad de CSI, las claims, la conexión/topología, los permisos y el estado del backend/red; no elimine todos los finalizers |
| NetworkNotReady | Inspeccione la implementación de red real del nodo y la evidencia de readiness; los comandos estándar de aws-node dependen del modo |
| NodeNotReady | Distinga Ready=False de Unknown por falta de latidos e inspeccione la evidencia de nodo/EC2/runtime/red |
| Evicted | Compruebe la evidencia de presión del nodo/almacenamiento efímero y el motivo del Pod; aumentar límites o eliminar registros no es automáticamente una reparación |
| BackOff | Comportamiento de reintento; el fallo precedente explica qué investigar |
| InvalidImageName | Valide la sintaxis de la referencia de imagen; esto ocurre antes de resolver correctamente el registro |

### Comandos de lectura con alcance definido

```bash
# Use the account/context guard and the actual namespace/Pod/container from triage.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events --field-selector type=Warning
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" --since=15m --tail=100
# Run separately: previous-container logs may not exist.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" --previous --tail=100
```
```bash
# Authorized reads; print names/keys only, not configuration or Secret values.
: "${CONFIGMAP_NAME:?Set one relevant ConfigMap}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get configmap "$CONFIGMAP_NAME" -o json | jq '{
  name:.metadata.name,textKeys:(.data // {} | keys),binaryKeys:(.binaryData // {} | keys)
}'
: "${SECRET_NAME:?Set one Secret whose read permission is explicitly authorized}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$SECRET_NAME" -o json | jq '{
  name:.metadata.name,type:.type,keyNames:(.data // {} | keys)
}'
```
El comando Secret reduce la salida mostrada, pero aun así solicita un Secret a la API y requiere permiso de lectura de Secret; no es un límite de autorización. Las marcas de tiempo de eventos pueden representar ocurrencias agregadas, y top es una muestra reciente de métricas, no una verdad histórica/instantánea. Para endpoints, use el flujo de trabajo de EndpointSlice anterior.

Mantenga la creación/depuración/ejecución de Pods, rollout undo/restart, escalado, drenaje/reparación y eliminación en sus pasos operativos revisados por separado. La eliminación forzada de un Pod elimina su objeto de API sin demostrar que el proceso antiguo se haya detenido; puede provocar escritores duplicados. No incluya ese comando en la evaluación rutinaria ni lo use para eludir salvaguardas de datos/expulsión.

### Selección de herramientas

| Herramienta | Uso y límites |
| --- | --- |
| netshoot | Imagen/caja de herramientas de diagnóstico revisada; crear un Pod y enviar tráfico requiere el flujo de trabajo acotado anterior |
| eks-node-viewer | Solicitudes de Pods programados frente a la capacidad asignable de nodo, no uso real de CPU/memoria de Pods; revise la versión y el acceso al clúster/AWS |
| crictl | Inspección de estado/registros de CRI en un host compatible autorizado y con endpoint de runtime configurado |
| kubeconform | Fije la versión de esquema de Kubernetes y proporcione esquemas CRD; los esquemas ausentes/omitidos no equivalen a una validación satisfactoria |
| stern | Inspección de registros de varios Pods con contexto/espacio de nombres/selectores explícitos y salida acotada |
| k9s | TUI interactiva; use el modo readonly documentado y RBAC apropiado cuando se pretenda inspeccionar |
| kubectx/kubens | Cambian el contexto/espacio de nombres predeterminado local; los indicadores de contexto explícitos son más seguros en procedimientos de diagnóstico compartidos |

Elija versiones revisadas antes de un incidente; no ejecute go install @latest sin fijar una versión como reparación. Kubeconform admite ubicaciones de esquemas locales/sin conexión; la validación de esquemas no ejecuta admission webhooks ni demuestra el comportamiento en runtime. Server-side dry-run se conecta al servidor API seleccionado y es distinto de una comprobación sin conexión. K9s admite --readonly; no es de solo lectura de forma predeterminada. En esta auditoría no se ejecutaron pruebas de herramientas ni sesiones interactivas.

### Recopilador de registros de EKS para un caso de soporte propio

La ruta oficial del recopilador de registros de EKS estaba disponible durante esta revisión; no se reemplaza basándose en un movimiento supuesto del repositorio. Recopila información del host/sistema/runtime/red y escribe un archivo. Use solo las instrucciones oficiales actuales para un nodo compatible y autorizado, y revise la versión del recopilador. Auto Mode recomienda NodeDiagnostic y admite su ruta documentada de contenedor de depuración, no el acceso SSH directo normal.

```bash
# Download only; do not automatically execute a newly downloaded host script.
set -euo pipefail
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
: "${COLLECTOR_REF:?Set a reviewed full 40-character commit SHA from the official repository}"
[[ "$COLLECTOR_REF" =~ ^[0-9a-fA-F]{40}$ ]]
test -d "$EVIDENCE_PARENT"
umask 077
COLLECTOR_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-support.XXXXXXXX")
curl --fail --location --silent --show-error --connect-timeout 5 --max-time 30 \
  "https://raw.githubusercontent.com/awslabs/amazon-eks-ami/$COLLECTOR_REF/log-collector-script/linux/eks-log-collector.sh" \
  --output "$COLLECTOR_DIR/eks-log-collector.sh"
sha256sum "$COLLECTOR_DIR/eks-log-collector.sh"
```
Compare el resumen con un registro de artefacto revisado de forma independiente; imprimir sha256sum no constituye autenticación. La ejecución del recopilador es una acción de host separada y autorizada, con implicaciones para el disco/CPU y los datos confidenciales. Inspeccione/enmascare el archivo antes de adjuntarlo manualmente a un caso propio de AWS Support. No dé por sentado que kubeconfig/material de claves, registros de aplicaciones, direcciones de endpoints y detalles del entorno sean seguros para compartir públicamente. En esta auditoría no se generó ni cargó ningún archivo de soporte.

[Kubeconform](https://github.com/yannh/kubeconform) · [K9s](https://github.com/derailed/k9s) · [eks-node-viewer](https://github.com/awslabs/eks-node-viewer) · [Solución de problemas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)

---

<span id="10-next-steps"></span>

## 10. Pasos siguientes

### Cuestionario

Para poner a prueba su comprensión del contenido de este documento, pruebe el [Cuestionario de depuración avanzada de EKS](../quizzes/eks/11-eks-advanced-debugging-quiz.md).

### Documento siguiente

Consulte la [hoja de ruta de versiones de Kubernetes](12-kubernetes-version-roadmap.md) para el tema de planificación de versiones que sigue a este capítulo.

Para aprender a integrar clústeres de EKS con entornos locales, consulte [EKS Hybrid Nodes](../eks-hybrid-nodes/README.md).

### Recursos de aprendizaje adicionales

- [Documentación oficial de AWS EKS: solución de problemas](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)
- [Documentación oficial de Kubernetes: depuración](https://kubernetes.io/docs/tasks/debug/)
- [Guía de prácticas recomendadas de Amazon EKS](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
