# Cuestionario sobre actualizaciones de Amazon EKS

> **Última actualización**: 12 de septiembre de 2026

Este cuestionario evalúa tus conocimientos sobre los procesos de actualización de clústeres de Amazon EKS, las prácticas recomendadas, la resolución de problemas y otros aspectos relacionados.

## Descripción general del cuestionario

- Planificación de actualizaciones de clústeres EKS
- Actualizaciones del plano de control
- Actualizaciones de grupos de nodos
- Actualizaciones de complementos y componentes
- Pruebas y validación de actualizaciones
- Resolución de problemas durante las actualizaciones

## Preguntas de opción múltiple

### 1. ¿Cuál es el primer paso más importante al planificar una actualización de un clúster de Amazon EKS?

- A. Actualizar de inmediato el plano de control
- B. Actualizar todas las cargas de trabajo a la vez
- C. Revisar la compatibilidad y definir un plan de pruebas y recuperación
- D. Actualizar todos los grupos de nodos simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Revisar la compatibilidad y definir un plan de pruebas y recuperación**

Antes de elegir la secuencia de cambios, revisa la versión objetivo de EKS, los cambios de API y las dependencias de las cargas de trabajo. El inventario de compatibilidad aporta información para decidir, pero no certifica la disponibilidad.

**Revisión de compatibilidad**

- Inspecciona los manifiestos, las versiones de Helm, los clientes de API, las CRD, los webhooks de conversión y admisión, y los operadores. Incluye los componentes de CNI y DNS, balanceadores de carga, service mesh, almacenamiento, supervisión, registro y copias de seguridad.
- Consulta el catálogo de versiones de clúster de EKS para ver las versiones de clúster admitidas. En cambio, `describe-addon-versions` muestra la compatibilidad de los complementos con una versión de Kubernetes.
- Revisa EKS Upgrade Insights y los registros y métricas de auditoría disponibles durante un período representativo. `apiserver_requested_deprecated_apis` es la métrica pertinente del servidor de API cuando está expuesta. Una serie ausente, una solicitud denegada o un análisis vacío no demuestra que no haya clientes obsoletos. Insights puede conservar el uso histórico dentro de su período de observación.
- El `.apiVersion` actual de un objeto representa la forma en que se devuelve, no necesariamente la versión de API que solicitó originalmente un cliente. Revisa la configuración desplegada, el código fuente y los consumidores en tiempo de ejecución.

Guarda `eks-upgrade-preflight.py` de la [guía de origen](../../eks/08-eks-upgrades.md), revisa sus requisitos previos y ejecuta su inventario de solo lectura de cuenta, contexto y versión objetivo:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

El ayudante se detiene si falla una consulta. Revisa todos los hallazgos de `preflight.json`; el script no ejecuta una actualización ni certifica la compatibilidad. Selecciona una versión menor superior a la actual que esté admitida según el catálogo vigente de AWS.

Con una versión revisada de Pluto, analiza los manifiestos renderizados, los metadatos de Helm y la configuración aplicada por última vez:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"; : "${MANIFEST_DIR:?}"
pluto detect-files --directory "$MANIFEST_DIR" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-helm --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-api-resources --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
```

Un resultado distinto de cero anterior detiene este bloque de shell para que se investigue; una vez atendido, completa las comprobaciones restantes. La detección de recursos de API depende de las anotaciones almacenadas y no puede observar todas las solicitudes en tiempo de ejecución. El proyecto kube-no-trouble proporciona el binario `kubent`, no `kubectl-no-trouble`.

**Ejemplos históricos de eliminación de API** (historial de migración, no versiones objetivo para las actualizaciones actuales de EKS):

| Versión de Kubernetes | API de servicio eliminada o migración |
| --- | --- |
| 1.22 | Se eliminaron varias API beta, incluida Ingress `networking.k8s.io/v1beta1`; migra a las API estables y sus esquemas de campos |
| 1.25 | PodSecurityPolicy `policy/v1beta1`: migra la aplicación de políticas. CronJob `batch/v1beta1` → `batch/v1` |
| 1.26 | HPA `autoscaling/v2beta2` → `autoscaling/v2`; se eliminó `v1beta1` de control de flujo |
| 1.27 | CSIStorageCapacity `storage.k8s.io/v1beta1` → `storage.k8s.io/v1` |
| 1.29 / 1.32 | Se eliminaron, respectivamente, `v1beta2` / `v1beta3` de FlowSchema / PriorityLevelConfiguration; usa `flowcontrol.apiserver.k8s.io/v1` y migra los campos y valores predeterminados |

Para kubelet 1.25 y posteriores, la política upstream permite que kubelet esté hasta tres versiones menores por detrás del servidor de API, pero nunca que sea más nuevo; para versiones anteriores de kubelet, el límite es de dos versiones menores. Durante una actualización de alta disponibilidad del servidor de API, las distintas versiones de los servidores reducen ese margen. Este límite de soporte no demuestra que todas las aplicaciones o complementos funcionen. Como preparación conservadora para EKS, actualiza los nodos hasta la versión actual del plano de control antes de la siguiente actualización de este.

**Ensayo y plantilla del plan**

Usa definiciones de infraestructura revisadas para preparar un entorno separado con redes, IAM, tipos de cómputo, datos y controladores representativos. Registra las diferencias con producción, los costos y quién se encargará de la limpieza. Empieza en desarrollo o ensayo y prueba las funciones de negocio, el escalado, la recuperación y las alertas; no ejecutes pruebas de fallos de forma incidental en producción. El antiguo ejemplo de 1.27→1.28 es histórico y no una recomendación actual de aprovisionamiento.

```markdown
# EKS upgrade plan: fill from evidence, not assumed results

- Account / Region / cluster ARN / kube context: TBD
- Current / target minor and EKS support status: TBD
- Node groups, Fargate, Auto Mode, hybrid nodes: inventory required
- Add-on / controller / CRD / webhook versions and owner: TBD
- Compatibility evidence, observation window and unresolved findings: TBD
- Backup coverage, application consistency, restore test and RPO/RTO: TBD
- Subnet IPs, EC2 quotas, placement, surge capacity and cost: TBD
- Rehearsal environment and differences from production: TBD

## Ordered change gates

- [ ] Align nodes to the current control-plane version; verify supported skew
- [ ] Complete API migrations and any required bridge add-on versions
- [ ] Complete a representative non-production rehearsal
- [ ] Upgrade the control plane by one minor; verify the exact update ID
- [ ] Upgrade nodes/add-ons in their reviewed dependency order
- [ ] Verify workloads and monitor agreed SLOs before retiring old capacity

## Test coverage and evidence

- [ ] Deployments: create, readiness, rollout and scaling
- [ ] StatefulSets / PVCs: write, reschedule, read and restore
- [ ] Services, DNS, Ingress / Gateway and external dependencies
- [ ] Jobs / CronJobs, operators, CRDs and admission webhooks
- [ ] API latency, Pod startup, network and resource baselines
- [ ] Controlled node/network/resource-pressure recovery in a test environment
- [ ] Alert delivery and incident ownership
- Result / timestamp / environment / evidence location: NOT RUN

## Recovery decision

- Stop criteria and incident owner: TBD
- Previous minor, upgrade completion time and 7-day rollback deadline: TBD
- Rollback eligibility, compute-type order and add-on compatibility: TBD
- Data restore or forward-fix procedure when version rollback is unsuitable: TBD
```

Registra las observaciones en lugar de rellenar de antemano «todo es compatible» o «no hay cambios de CRD». Revertir una versión no restaura los datos de la aplicación; la pregunta 5 explica los requisitos y el orden del cómputo. Las opciones A, B y D omiten pruebas o combinan cambios de forma tan amplia que dificultan el diagnóstico y la recuperación.

Fuentes: [guía de migración de API](https://kubernetes.io/docs/reference/using-api/deprecation-guide/), [política de desfase de versiones](https://kubernetes.io/releases/version-skew-policy/), [actualizaciones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [Pluto](https://pluto.docs.fairwinds.com/), [kube-no-trouble](https://github.com/doitintl/kube-no-trouble).

</details>

### 2. Después de alinear previamente los nodos, ¿cuál es el orden correcto para realizar una actualización in situ a la siguiente versión menor?

- A. Pasar kubelet a la versión menor objetivo mientras el servidor de API sigue en la versión menor anterior
- B. Actualizar el plano de control a la versión menor objetivo y luego actualizar en etapas revisadas los grupos de nodos que usarán esa versión
- C. Iniciar al mismo tiempo los cambios del plano de control y de todos los nodos objetivo
- D. Es obligatorio crear un clúster nuevo para cada actualización de versión menor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Actualizar el plano de control a la versión menor objetivo y luego actualizar en etapas revisadas los grupos de nodos que usarán esa versión**

Llevar los nodos a la versión menor **actual** del plano de control es una preparación. Los nodos pasan a la versión menor **objetivo** después de que el plano de control la admita. EKS se actualiza una versión menor a la vez. El desfase admitido no garantiza la compatibilidad de la aplicación. Sigue los requisitos de dependencia de cada componente, incluidas las versiones puente de complementos que quizá sean necesarias antes de cambiar el plano de control.

**Preparación y ejecución**

1. Confirma la cuenta, el contexto, el soporte de la versión actual y la objetivo, el estado del clúster y de los nodos, Insights, la capacidad de IP de las subredes y el acceso. Planifica capacidad de reemplazo y controles para las interrupciones de las cargas de trabajo.
2. Valida las copias de seguridad y la restauración. Los usuarios de EKS no pueden ejecutar `etcdctl` en el plano de control administrado. `kubectl get all` omite muchos recursos y datos persistentes. Usa AWS Backup para EKS, Velero o copias de seguridad de aplicaciones con la configuración adecuada; prueba su cobertura y restauración.
3. Revisa el análisis previo de la pregunta 1. Antes de esta fase de cambio independiente, guarda `eks-wait-update.py` de la [guía de origen](../../eks/08-eks-upgrades.md) para la versión objetivo revisada, sin actualizaciones que entren en conflicto.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${AWS_REGION:?Set the reviewed Region}"
: "${TARGET_VERSION:?Set the next supported EKS minor version}"
umask 077
aws eks update-cluster-version \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --output json --no-cli-pager \
  > control-plane-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' control-plane-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

El monitor sigue exactamente esta solicitud. Solo el estado `Successful` cuenta como éxito; si hay errores, cancelación, un estado desconocido o errores de API, el procedimiento se detiene. El tiempo de espera del cliente no cancela la operación de AWS. Que el clúster esté `ACTIVE` por sí solo no demuestra que la actualización se haya completado correctamente; `aws eks wait update-successful` no es un waiter de la CLI de EKS.

Como alternativa, `eksctl upgrade cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --version "$TARGET_VERSION"` muestra una vista previa del cambio; `--approve` lo inicia. Elige un único responsable y una vía de ejecución, en lugar de enviar cambios tanto por la CLI como por Terraform.

**Después de que la solicitud se complete correctamente**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,platformVersion:platformVersion}'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl --context "$KUBE_CONTEXT" get --raw='/readyz'
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -n kube-system
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp'
```

El endpoint de disponibilidad de la API requiere permisos y es solo una señal. Inspecciona las cargas de trabajo, el DNS y los controladores reales, no objetos `ComponentStatus` obsoletos ni un Pod de etcd administrado que se dé por supuesto. Auto Mode puro usa CoreDNS a nivel de nodo; los clústeres mixtos mantienen DNS para los nodos que no usan Auto Mode. La ausencia de despliegues estándar de `aws-node`, kube-proxy o CoreDNS no constituye por sí misma un fallo de Auto Mode. `kubectl top` requiere Metrics Server; que haya métricas disponibles es algo distinto de que la solicitud haya tenido éxito.

Continúa con un grupo de nodos o un canario revisado y la secuencia necesaria de complementos, validando cada etapa. Auto Mode administra los nodos después de la actualización del plano de control. Los Pods de Fargate existentes conservan su versión de kubelet; coordina con el responsable el reemplazo de los Pods y su disponibilidad.

**Disponibilidad y duración**

La antigua estimación de «20–30 minutos» no tiene una procedencia de medición indicada y se conserva solo como referencia histórica para planificar, no como garantía de duración. Reserva una ventana según los ensayos. Los clientes de API deben volver a conectarse mientras se reemplazan los servidores de API. Los contenedores existentes pueden seguir ejecutándose, pero los controladores y aplicaciones que dependen de la API aún pueden verse afectados. Una actualización normal del plano de control que ya empezó no se puede pausar ni cancelar. Conserva los ID y errores de la actualización y contacta con AWS Support cuando corresponda; la elegibilidad para revertir después la versión tiene requisitos propios.

**Ejemplo de propiedad en Terraform**

Modifica el recurso o módulo existente y conserva sus demás ajustes y dependencias. Este fragmento no es una definición completa ni un segundo recurso que debas crear para un clúster existente:

```hcl
# Fragment of the existing, state-managed cluster resource.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.target_version

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.cluster_security_group_id]
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

Proporciona los valores existentes de IAM, subredes y grupos de seguridad, así como un objetivo revisado. Inspecciona el plan del proveedor para detectar reemplazos no previstos o cambios ajenos a la actualización. `prevent_destroy` protege frente a la destrucción de Terraform, no frente a interrupciones del servicio. `ignore_changes = []` vacío no espera ni valida una actualización; el proveedor tiene sus propios tiempos de espera y waiter. Un timeout de IaC no cancela el servicio, y revertir Git no revierte la versión de EKS. Después del cambio, usa la validación acotada de la pregunta 6. Esta revisión no ejecutó ningún clúster en vivo.

A hace que kubelet sea más reciente que el servidor de API. C elimina controles de validación. D es incorrecta: migrar a un clúster nuevo es opcional e implica costos diferenciados de migración de tráfico y datos.

Fuentes: [procedimiento de actualización de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [copias de seguridad de EKS](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html), [recurso EKS de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 3. ¿Qué enfoque permite actualizar de forma controlada un grupo de nodos de EKS?

- A. Terminar todos los nodos simultáneamente
- B. Usar una actualización escalonada de un grupo de nodos administrado o una migración blue/green validada
- C. Dejar indefinidamente las versiones de los nodos sin cambios
- D. Reemplazar individualmente los binarios de kubelet en los nodos administrados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar una actualización escalonada de un grupo de nodos administrado o una migración blue/green validada**

Elige la estrategia según la tolerancia de las cargas de trabajo a las interrupciones, la capacidad, el almacenamiento con estado y quién administra el cómputo. Ni una actualización administrada ni una migración blue/green garantizan un servicio ininterrumpido.

**Grupos de nodos administrados**

La estrategia de actualización `DEFAULT` crea capacidad de reemplazo antes de retirar los nodos antiguos; `MINIMAL` retira primero la capacidad antigua. `maxUnavailable` limita la cantidad de nodos que pueden no estar disponibles al mismo tiempo. La ruta normal de desalojo gradual respeta los PDB, pero una actualización forzada puede omitirlos. Estas estrategias difieren de la elección de actualización gradual o forzada de la consola. Una actualización fallida **no** implica una reversión automática de toda la flota.

Guarda `eks-wait-update.py` de la guía de origen y completa la revisión de cuenta, contexto y capacidad de la pregunta 1. Para un grupo existente que usa una AMI optimizada para EKS, selecciona explícitamente tanto la versión de Kubernetes como la versión compatible de la AMI:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${TARGET_VERSION:?Set the reviewed target, no newer than the control plane}"
: "${TARGET_AMI_RELEASE:?Set the reviewed EKS-optimized AMI release}"
umask 077
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" --output json > nodegroup-before.json
if jq -e '.nodegroup.amiType == "CUSTOM"' nodegroup-before.json >/dev/null; then
  echo "Use the custom launch-template path for this node group" >&2
  exit 1
fi
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --release-version "$TARGET_AMI_RELEASE" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

El script se detiene si falla la solicitud o el sondeo. Antes de pasar al siguiente grupo, comprueba las versiones y la disponibilidad reales de los nodos, la ubicación de los Pods, los eventos y los SLO de la aplicación. Para una AMI personalizada, usa una nueva versión revisada de la **misma plantilla de lanzamiento original** y omite `--kubernetes-version` y `--release-version`; sigue la ruta separada para AMI personalizadas de la guía de origen. No edites paquetes de kubelet in situ suponiendo que así se actualizaron la AMI, el entorno de ejecución y el arranque.

`eksctl upgrade nodegroup` usa `--kubernetes-version`; `eksctl create nodegroup` usa `--version`. Para crear el grupo, conserva en la configuración existente del clúster las subredes, IAM, AMI, etiquetas y taints revisados, en lugar de usar una opción `--taints` no admitida o una receta incompleta de una sola línea.

**Secuencia blue/green**

1. Conserva la capacidad azul. El responsable de infraestructura debe crear el entorno verde con una versión no más nueva que el plano de control, la AMI y arquitectura correspondientes, redes privadas y cuota, IP y capacidad de AZ suficientes.
2. Comprueba que los nodos verdes estén `Ready` y prueba DNS, redes, almacenamiento y dependencias de las cargas de trabajo. Aplica un taint a los nodos verdes para los canarios hasta que las cargas adecuadas tengan la tolerancia necesaria.
3. Migra por etapas las plantillas de Pods de las cargas de trabajo. La afinidad preferida es solo una preferencia y no mueve los Pods existentes. Cuando la ubicación sea obligatoria, usa una selección explícita e inicia un despliegue controlado con el responsable de la carga de trabajo.
4. Inspecciona las cargas de trabajo de cada nodo antiguo y drénalo de uno en uno. Si falla el desalojo, detente; no termines el nodo después de un drenaje fallido.
5. Retira la flota azul solo después de revisar las evidencias de cargas de trabajo, datos y tráfico, además de la ventana de recuperación. Una respuesta afirmativa a una pregunta de confirmación o una lista de nodos `Ready` no demuestra que la migración haya terminado.

Lo siguiente es un **ejemplo de canario independiente y completo**, no un manifiesto sustituto de una aplicación existente. Prepara su espacio de nombres deliberadamente. Necesita al menos tres nodos Linux verdes aptos por la antiafinidad obligatoria de nombre de host. La tolerancia permite el taint; el selector de nodos elige la flota verde. Adapta por separado la imagen y configuración de la aplicación, la política de interrupciones y los parámetros del despliegue.

```yaml
# Independent fixture in an explicitly prepared test namespace.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  replicas: 3
  selector:
    matchLabels:
      app: upgrade-canary
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
        example.com/upgrade: green
      tolerations:
        - key: example.com/upgrade
          operator: Equal
          value: green
          effect: NoSchedule
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: upgrade-canary
              topologyKey: kubernetes.io/hostname
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: http
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - mkdir -p /tmp/www; printf 'ok\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 5
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: upgrade-canary
```

La estrategia del propio Deployment controla su actualización gradual, no el PDB. Un PDB rige el desalojo voluntario, no la reducción ordinaria de escala de un Deployment o ReplicaSet ni todos los casos de terminación de infraestructura. La antiafinidad obligatoria puede impedir la programación si desaparece capacidad adecuada. No se afirma que esta plantilla se haya ejecutado en una imagen o clúster.

Para un nodo antiguo revisado, el drenaje acotado de la guía de origen conserva las protecciones para los Pods no administrados y los datos de `emptyDir`:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

Si falla el drenaje, el nodo puede quedar en cuarentena o drenado parcialmente; investiga y recupéralo de forma deliberada. No agregues `--force`, `--delete-emptydir-data` ni `--disable-eviction` solo para terminar la migración.

**Ejemplo blue/green en Terraform**

Conserva las direcciones y los ajustes de los recursos existentes. Estos fragmentos para AMI optimizadas para EKS mantienen **ambos** grupos con capacidad positiva; el taint verde coincide intencionalmente con el canario anterior.

```hcl
# Existing blue resource address is retained; green is separate capacity.
# Inputs describe reviewed EKS-optimized AMIs, not a custom launch template.
variable "capacity" {
  type    = object({ desired = number, min = number, max = number })
  default = { desired = 3, min = 3, max = 6 }
  validation {
    condition = (
      var.capacity.min >= 1 &&
      var.capacity.desired >= var.capacity.min &&
      var.capacity.max >= var.capacity.desired &&
      alltrue([for n in values(var.capacity) : floor(n) == n])
    )
    error_message = "Retain positive integer capacity: 1 <= min <= desired <= max."
  }
}

resource "aws_eks_node_group" "blue" {
  cluster_name    = var.cluster_name
  node_group_name = "blue-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.blue_version
  release_version = var.blue_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "blue" }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "green" {
  cluster_name    = var.cluster_name
  node_group_name = "green-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.green_version
  release_version = var.green_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "green" }
  taint {
    key    = "example.com/upgrade"
    value  = "green"
    effect = "NO_SCHEDULE"
  }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}
```

Proporciona el clúster, rol y subredes existentes, tipos de instancia y familia de AMI compatibles, y versiones y revisiones de lanzamiento azul y verde por separado. El plano de control ya debe admitir la versión verde. La regla `desired_size` de ignorar cambios presupone que un escalador administra ese campo; quítala si Terraform debe ser su responsable. Los cambios de mínimo y máximo siguen aplicándose, y cambiar la configuración de escalado de un grupo de nodos administrado **no** respeta los PDB. No uses un interruptor booleano para reducir la flota azul a cero mientras creas la verde ni asignes `max_size = 0` (valor no válido). Crear nodos, migrar cargas de trabajo y retirar nodos son cambios separados; una dependencia de Terraform no demuestra por sí sola que las cargas estén listas.

Define de antemano los criterios de recuperación. Mientras conserves la flota azul, la ubicación de las cargas de trabajo puede ser reversible según la compatibilidad de API y datos. La reversión del plano de control y la de la versión de un MNG tienen las condiciones adicionales indicadas en la pregunta 5. A, C y D aumentan el alcance de las interrupciones, acumulan un desfase de versiones no admitido o eluden el ciclo de reemplazo administrado.

Fuentes: [actualizaciones de nodos administrados](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html), [comportamiento de actualización](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [PDB](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/), [grupos de nodos de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group).

</details>

### 4. ¿Cuál es el enfoque correcto para administrar complementos durante una actualización de EKS?

- A. Ignorar las actualizaciones de complementos
- B. Actualizar todos los complementos antes del plano de control, sin importar la compatibilidad
- C. Elegir versiones compatibles y seguir las dependencias y las versiones puente de cada componente
- D. Eliminar todos los complementos y volver a instalarlos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Elegir versiones compatibles y seguir las dependencias y las versiones puente de cada componente**

No existe una regla universal según la cual «todos los complementos se actualizan después del plano de control». Algunos componentes necesitan antes del cambio una versión intermedia compatible con ambas versiones del plano de control; otros se actualizan después. Revisa para cada versión las versiones de Kubernetes, arquitecturas, tipos de cómputo, API y ruta de actualización que admite. Las versiones de los complementos administrados por EKS no se actualizan automáticamente junto con el plano de control, y el hecho de que sean «administrados» no promete que se instale automáticamente cada actualización de seguridad.

**Inspeccionar, elegir y conservar la configuración**

Para un complemento administrado instalado y bajo tu responsabilidad, inspecciona el estado actual, las versiones compatibles y el esquema de la versión candidata revisada. El primer elemento de una matriz no garantiza ser «la versión compatible más reciente».

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"
: "${TARGET_VERSION:?Set the Kubernetes version for this stage}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json > addon-before.json
aws eks describe-addon-versions --addon-name "$ADDON_NAME" \
  --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json > addon-candidates.json
# Select ADDON_VERSION after reviewing compatibility, architecture, compute type, and upgrade path.
: "${ADDON_VERSION:?Set the reviewed add-on version}"
aws eks describe-addon-configuration --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --output json > addon-schema.json
jq -r '.addon.configurationValues // "{}"' addon-before.json > addon-config-candidate.json
```

`addon-before.json` incluye información de versión, configuración e identidad. Un único ConfigMap `aws-node` no es una copia de seguridad completa de CNI; también pueden ser pertinentes la configuración del DaemonSet, los recursos personalizados y IAM o Pod Identity. Protege los archivos de evidencia. `addon-config-candidate.json` es un dato de entrada que debe revisarse, no una configuración objetivo automáticamente válida. Combina los ajustes deseados con el esquema nuevo y revisa los campos eliminados o predeterminados y las notas de la versión.

Después de completar esa revisión, usa el monitor de solicitudes exactas de la guía de origen y un archivo completo de configuración objetivo:

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"; : "${ADDON_VERSION:?}"
: "${REVIEWED_ADDON_CONFIG_FILE:?Provide the complete reviewed target configuration JSON}"
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG_FILE" \
  --resolve-conflicts PRESERVE --output json > addon-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' addon-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID ADDON_NAME
unset NODEGROUP_NAME
python3 eks-wait-update.py
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json
```

`PRESERVE` aborda los conflictos con campos existentes; no garantiza que la carga útil explícita de configuración se combine por completo, sea aceptada o funcione correctamente. `NONE` falla ante conflictos; `OVERWRITE` puede reemplazar las personalizaciones con valores predeterminados de EKS. No uses `OVERWRITE` como atajo de recuperación automático. Antes de avanzar con la siguiente dependencia, comprueba que la actualización se haya completado **y** que el complemento y las cargas de trabajo estén sanos; esperar 30 segundos no es una comprobación de finalización.

**Comprobaciones específicas de los componentes**

| Componente | Comprobación antes de continuar |
| --- | --- |
| VPC CNI | Ruta de actualización admitida, asignación de IP, redes de nodos y Pods, redes personalizadas e IAM |
| CoreDNS | Resolución DNS, cambios en Corefile o esquema, programación y disponibilidad, y ajustes de PDB |
| kube-proxy | Desfase de versión de Kubernetes, acceso a los Services y plano de datos real del clúster |
| Cluster Autoscaler | Versión menor de Kubernetes admitida, descubrimiento e IAM, y responsabilidad del escalado |
| Metrics Server | Versiones admitidas, disponibilidad de APIService y acceso o TLS de kubelet |
| Load Balancer Controller / ExternalDNS / mesh | Compatibilidad de controlador, chart, CRD y API; IAM, webhook y comportamiento del tráfico |

Auto Mode puro proporciona DNS y redes a nivel de nodo y no requiere estos complementos de nodos estándar de la misma manera. Los clústeres mixtos deben conservar los componentes que necesitan los nodos que no usan Auto Mode, incluida la cobertura del Deployment de CoreDNS. Identifica quién es responsable antes de actualizar o quitar componentes.

**Complementos administrados por Terraform**

Usa mapas de versiones y configuración revisados en los recursos existentes bajo control del estado; conserva sus ajustes de IAM y Pod Identity. Estos fragmentos se aplican a complementos de nodos estándar, no a una instalación universal de Auto Mode:

```hcl
# Fragments of existing, imported/state-managed standard-node add-ons.
# Preserve each resource's existing IAM/Pod Identity settings as applicable.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = var.cluster_name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions["vpc-cni"]
  configuration_values        = file(var.addon_config_files["vpc-cni"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions["coredns"]
  configuration_values        = file(var.addon_config_files["coredns"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = var.cluster_name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions["kube-proxy"]
  configuration_values        = file(var.addon_config_files["kube-proxy"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

El proveedor actual distingue `resolve_conflicts_on_create` de `resolve_conflicts_on_update`. Al crear, no se acepta `PRESERVE`; `NONE` deja que se manifiesten deliberadamente los conflictos de migración. No agregues un recurso duplicado de clúster para actualizar un complemento. Cambia solo el componente previsto para la etapa actual; enumerar tres recursos independientes no establece un orden de actualización seguro. La destrucción de recursos o los cambios de configuración requieren una revisión propia.

**Versiones de Helm administradas por separado**

Usa el responsable existente de la versión, una referencia y versión de chart revisadas y valores migrados. La instalación, la migración de propiedad y la actualización son operaciones distintas. Conserva las CRD, identidad, ServiceAccount, ajustes de recursos y programación, y comportamiento actual:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${RELEASE:?}"; : "${ADDON_NAMESPACE:?}"
: "${CHART_REF:?Set the verified repository/chart or OCI reference}"
: "${CHART_VERSION:?Set a reviewed compatible chart version}"
: "${REVIEWED_VALUES_FILE:?Set the complete reviewed target values file}"
umask 077
helm get values "$RELEASE" --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > addon-values-before.yaml
helm show values "$CHART_REF" --version "$CHART_VERSION" > addon-values-defaults.yaml
# Merge/migrate values and handle CRDs/IAM through the owner before this step.
helm upgrade "$RELEASE" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  -f "$REVIEWED_VALUES_FILE" --wait --timeout 15m
```

Prepara los valores revisados antes del último comando. `--wait` no demuestra que se cumplan los SLO de la aplicación ni gestiona todas las migraciones de CRD. No instales en bloque un segundo controlador ni cambies indicadores ajenos del escalador durante una actualización. Valida los Pods, eventos y funciones representativas de cada versión; registra los fallos en lugar de declarar incondicionalmente que todo terminó.

A ignora el mantenimiento de seguridad y compatibilidad. B puede instalar versiones incompatibles con el plano de control, que aún es anterior. D descarta innecesariamente la propiedad y configuración, y puede interrumpir las redes o el DNS.

Fuentes: [actualización de complementos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html), [redes de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [complementos de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon), [actualización de Helm](https://helm.sh/docs/helm/helm_upgrade/).

</details>

### 5. ¿Cuál es el enfoque más eficaz para resolver problemas durante una actualización de EKS?

- A. Crear inmediatamente un clúster nuevo
- B. Depender únicamente de AWS Support sin recopilar evidencia
- C. Diagnosticar sistemáticamente con registros y comprobación de hipótesis
- D. Ignorar los problemas de actualización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Diagnosticar sistemáticamente con registros y comprobación de hipótesis**

Define los síntomas, la hora de inicio, las cargas de trabajo afectadas y el impacto en el negocio; relaciónalos con cambios concretos. Recopila evidencia antes de probar hipótesis. Aplica una corrección específica solo tras revisar su impacto previsto; después verifica la recuperación y registra medidas preventivas. Las causas posibles no son causas raíz confirmadas.

**Diagnóstico de solo lectura**

Confirma la cuenta, el contexto y el ID exacto de la operación. El siguiente recopilador valida el tipo de operación antes de consultar y usa un nuevo directorio privado de evidencias. Si falla una consulta, se detiene; los archivos ya escritos son evidencia parcial, no un diagnóstico satisfactorio.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${UPDATE_ID:?Set the exact affected update ID}"
: "${ISSUE_KIND:?Set control-plane, nodegroup, or addon}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
args=(--name "$CLUSTER_NAME" --region "$AWS_REGION" --update-id "$UPDATE_ID")
case "$ISSUE_KIND" in
  control-plane) ;;
  nodegroup) : "${NODEGROUP_NAME:?}"; args+=(--nodegroup-name "$NODEGROUP_NAME") ;;
  addon) : "${ADDON_NAME:?}"; args+=(--addon-name "$ADDON_NAME") ;;
  *) echo "Unknown ISSUE_KIND" >&2; exit 2 ;;
esac
umask 077
EVIDENCE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-upgrade-diagnosis.XXXXXXXX")
printf 'Evidence directory: %s\n' "$EVIDENCE_DIR"
aws eks describe-update "${args[@]}" --output json --no-cli-pager \
  > "$EVIDENCE_DIR/update.json" 2> "$EVIDENCE_DIR/update.stderr"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,health:health,logging:logging}' \
  --output json --no-cli-pager > "$EVIDENCE_DIR/cluster.json"
kubectl --context "$KUBE_CONTEXT" get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl --context "$KUBE_CONTEXT" get pods -A -o wide > "$EVIDENCE_DIR/pods.txt"
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp' \
  > "$EVIDENCE_DIR/events.txt"
printf 'Snapshots collected; review errors and workload evidence before changing anything.\n'
```

Para una operación de grupo de nodos o complemento, inspecciona también `health.issues` de ese recurso y su versión y configuración mediante `describe-nodegroup` o `describe-addon`. Según corresponda, comprueba los ProviderID de los nodos, el estado de EC2, IAM, el arranque, la AMI, las redes y CNI, y las restricciones de programación. No deduzcas la causa solo porque una actualización tenga el estado `Failed`.

Lee los registros existentes del plano de control durante un intervalo acotado:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${START_TIME_MS:?Set the reviewed start timestamp in epoch milliseconds}"
: "${END_TIME_MS:?Set the reviewed analysis-window end timestamp}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.logging' --output json --no-cli-pager
# Read existing logs; enabling logging is a separate change and does not backfill history.
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
```

Habilitar el registro es un cambio independiente del clúster y no completa registros de eventos anteriores. Si no hay grupo de registros, falta permiso o la consulta está vacía, hay una limitación de visibilidad. Cuando exista un Pod pertinente, inspecciónalo de forma explícita:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${AFFECTED_NAMESPACE:?}"; : "${AFFECTED_POD:?}"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" describe pod "$AFFECTED_POD"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" logs "$AFFECTED_POD" \
  --all-containers=true --prefix=true --since=15m --tail=100
```

Los registros del agente del Pod no son todos los diarios del host de kubelet y del entorno de ejecución. Auto Mode, Fargate y EC2 estándar ofrecen distintos accesos de diagnóstico. Protege las capturas y elimina la configuración sensible antes de compartirla con AWS Support; evita volcar el clúster indiscriminadamente.

| Síntoma | Hipótesis que se deben probar con evidencia |
| --- | --- |
| Falló la solicitud del plano de control | Errores exactos de la actualización, requisitos previos, IP de subredes, grupos de seguridad y fallo del servicio de AWS |
| Nodo no está `Ready` / Pod en `Pending` | AMI o arranque, capacidad de EC2, IAM, redes o CNI, taints, afinidad, topología de PVC o recursos |
| Complemento en `CrashLoopBackOff` | Configuración o esquema, identidad, imagen o inicio, recursos o compatibilidad de versiones |
| Errores de API de la aplicación | Clientes de API eliminadas, webhooks de admisión o conversión, permisos o regresión de la aplicación |

Reintentar, eliminar un grupo de nodos o sobrescribir la configuración de un complemento no es un diagnóstico. La recuperación del complemento requiere una versión compatible **y** configuración e identidad revisadas, además del seguimiento exacto de actualización explicado en la pregunta 4.

**Condiciones actuales de reversión de EKS**

La guía actual de EKS admite revertir un plano de control actualizado in situ. Esto es distinto de restaurar datos de aplicaciones y de reemplazar un nodo averiado.

- Inicia la reversión en un plazo de siete días desde una actualización in situ completada, hacia la versión menor inmediatamente anterior. Un clúster creado en la versión actual no reúne los requisitos; no se admiten reversiones repetidas a versiones menores progresivamente más antiguas.
- La versión objetivo debe seguir estando admitida. Una versión objetivo con soporte extendido requiere la política `EXTENDED` y genera cargos. No se puede revertir una actualización automática al finalizar el soporte extendido; los casos al terminar el soporte estándar están sujetos a las condiciones de política documentadas.
- Comprueba el estado `ACTIVE`, que no haya actualizaciones en conflicto, las funciones incompatibles hacia atrás y los demás requisitos previos. Las conclusiones `ERROR` o `UNKNOWN` de `ROLLBACK_READINESS` bloquean la reversión; `WARNING` es consultiva. `--force` omite las comprobaciones de insights, no los requisitos previos y de elegibilidad ni los controles de interrupción de Auto Mode. Esto difiere de la aplicación temporal de `--force` en los insights normales de actualización.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

Inspecciona cada hallazgo con `describe-insight --id "$INSIGHT_ID"`. Una lista de insights vacía no demuestra que se cumplan todos los requisitos previos.

| Tipo de cómputo | Orden y límites |
| --- | --- |
| Grupos de nodos administrados | Antes del plano de control, revierte los grupos pertinentes mediante `UpdateNodegroupVersion`, según la guía de origen y los requisitos de AMI personalizada; verifica los nodos reales |
| Nodos autoadministrados / híbridos | El responsable coordina nodos compatibles y la migración de cargas de trabajo antes del plano de control |
| Auto Mode | El servicio revierte primero los nodos y luego el plano de control; sigue el ID de actualización aunque el estado del clúster sea `ACTIVE` durante la fase de nodos |
| Fargate | No se puede revertir in situ kubelet; coordina el comportamiento y la disponibilidad de Pods, controladores, HPA, GitOps y Jobs para que los Pods de reemplazo no vuelvan a crear inmediatamente el kubelet más nuevo antes de revertir el plano de control |

Después de validar la secuencia de nodos pertinente y todos los requisitos, la solicitud al plano de control usa `update-cluster-version`, no un comando `rollback-cluster`. Guarda antes el monitor de la guía de origen:

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ROLLBACK_VERSION:?}"
: "${WAIT_TIMEOUT_SECONDS:?Set an explicit client wait for the approved rollback}"
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID WAIT_TIMEOUT_SECONDS
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

Para Auto Mode, usa la solicitud alternativa `--rollback-config timeoutMinutes=...` de la guía de origen, no una segunda solicitud simultánea. El valor predeterminado es 720 minutos y el intervalo admitido va de 120 a 10080; no es una fecha límite exacta de finalización. Los presupuestos de desviación en cero o las exclusiones de interrupción de nodos pueden bloquear el progreso. Los PDB y las exclusiones de interrupción de Pods interactúan con los períodos de gracia de terminación y no implican protección indefinida. `--force` no omite esos controles.

Solo se admite el mejor esfuerzo de `CancelUpdate` durante la fase de nodos de Auto Mode y antes de revertir el plano de control; las interrupciones ya iniciadas pueden completarse. Un timeout o cancelación deja intacto el plano de control y reconcilia los nodos hacia su versión. Un timeout del cliente por sí solo no cancela la operación. Los reintentos siguen sujetos al plazo de elegibilidad original.

La reversión conserva los datos de etcd, cargas de trabajo y PV en vez de restaurar una copia de seguridad; los complementos no se revierten automáticamente. La versión menor anterior recibe su última versión de plataforma, no necesariamente la versión exacta que tenía antes. Revertir CloudFormation o Git no equivale a esta operación del servicio. Sigue el procedimiento completo de decisión de la guía de origen; ninguno de estos comandos se ejecutó en AWS para esta revisión.

**Registro del incidente**

Se conserva la marca de tiempo original. El escenario y la causa atribuida no tienen evidencia de incidente adjunta, por lo que se mantienen como un ejemplo con hipótesis:

```markdown
# Upgrade troubleshooting report (illustrative, not a verified incident)

## Problem description

- Example symptom: CoreDNS Pods in CrashLoopBackOff after a node-group update
- Example impact: service discovery and application connections affected
- Original illustrative timestamp: 2023-07-15 14:30 UTC
- Provenance: no incident logs or measurement evidence supplied

## Investigation

1. Record the exact update ID, versions, changes and affected workloads.
2. Inspect CoreDNS logs/events, node conditions and resource availability.
3. Compare the owned Corefile/configuration with the reviewed baseline.
4. Check connectivity, network policies, scheduling and dependency changes.

## Hypotheses, not established findings

- A configuration parsing error is one possible explanation.
- A ConfigMap modification requires a diff/audit record and relevant log evidence.
- Record evidence that supports or rejects each hypothesis.

## Conditional remediation

1. If a configuration regression is demonstrated, restore compatible reviewed settings.
2. Coordinate any restart with replicas, readiness, PDB and DNS availability.
3. Verify service discovery and application SLOs, not just Pod phase.

## Prevention and record

- Version and back up owned configuration; rehearse restoration.
- Add regression checks and staged rollout gates.
- Actual actions, results and evidence: NOT RUN / TO BE RECORDED.
```

Comparte con AWS Support el ID exacto de actualización, los errores y registros acotados, el impacto y las medidas ya probadas. A puede añadir una migración no planificada sin resolver la causa; B omite evidencia útil; D deja sin atender problemas de fiabilidad y seguridad.

Fuentes: [reversión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), [reversión de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html), [resolución de problemas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html).

</details>

### 6. ¿Cuál es el enfoque más completo para validar después de una actualización?

- A. Contar únicamente los nodos
- B. Verificar únicamente la versión del clúster
- C. Validar por etapas el estado de la solicitud, los componentes, las funciones de las cargas de trabajo y el rendimiento representativo
- D. Enviar de inmediato todo el tráfico de producción sin validar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Validar por etapas el estado de la solicitud, los componentes, las funciones de las cargas de trabajo y el rendimiento representativo**

Primero verifica la solicitud de actualización exacta, la versión y el estado de nodos y complementos. Después prueba la funcionalidad y compara las métricas de la aplicación con una línea de base registrada. Superar una prueba rápida cubre menos que demostrar que está lista para producción o que cumple un SLO.

| Área | Evidencia |
| --- | --- |
| Plano de control | Resultado de actualización, disponibilidad y respuesta de API, y métricas o registros admitidos; no se puede acceder directamente a etcd administrado |
| Nodos | Condiciones `Ready`, kubelet, AMI y entorno de ejecución esperados, programación y estado específico del tipo de cómputo |
| Red | Comunicación de Pod y Service, DNS, Ingress y Gateway, salida y conectividad con dependencias |
| Almacenamiento | Aprovisionamiento, escritura y lectura entre consumidores, topología, reprogramación y restauración coherente con la aplicación |
| Seguridad | Comportamiento previsto de autenticación y autorización, seguridad de Pods, NetworkPolicy y cifrado |
| Cargas de trabajo | Despliegue y escalado, StatefulSets, Jobs y CronJobs, CRD y operadores, y webhooks |
| Rendimiento | Tasa de solicitudes comparable, latencia y distribución de errores, tiempo de inicio y uso de recursos durante un período representativo |

Usa `eks-upgrade-smoke.py` de la guía de origen para una prueba acotada en una instancia Linux de EC2, después de revisar el contexto, la StorageClass compatible, el controlador CSI y su IAM, la programación, la política de admisión y red, y los costos. Guarda la implementación proporcionada; esto no hace referencia a una imagen o script de validación no definido.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test cluster context}"
: "${TEST_STORAGE_CLASS:?Set an existing compatible test StorageClass}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
python3 eks-upgrade-smoke.py
```

El ayudante crea un espacio de nombres único, registra su UID, ejecuta el despliegue y escalado de un Deployment y 20 solicitudes HTTP, y escribe y luego lee un marcador de PVC mediante Jobs separados. El proceso de escritura se crea antes de esperar a que se vincule el volumen, para que un consumidor pueda programarse con `WaitForFirstConsumer`; el escritor se elimina antes de crear el lector. Los fallos conservan la evidencia y los recursos. La limpieza opcional tras el éxito exige que coincida el UID del espacio de nombres; un PV con política `Retain` puede seguir generando cargos. La prueba no cubre todas las cargas de trabajo, los procedimientos de restauración, Fargate o Auto Mode, los límites de rendimiento ni los controles de seguridad.

Elige pruebas funcionales y de carga adicionales revisadas por sus responsables a partir de la tabla. `kubectl top` depende de Metrics Server y muestra el uso actual, no prueba el rendimiento ni la latencia. No ejecutes en producción un bucle ilimitado de wget. Registra el tráfico objetivo, la duración, los criterios de éxito y error, la línea de base, las diferencias del entorno y los resultados reales; no infieras un benchmark a partir de plantillas sintéticas.

**Plantilla opcional de Terraform**

Esta plantilla administrada por separado conserva el ejemplo didáctico del espacio de nombres, Deployment, Service y PVC. Configura el proveedor para el contexto revisado, indica un espacio de nombres nuevo y una StorageClass compatible, e inspecciona el plan. No adoptes ni destruyas un espacio de nombres preexistente. Es una plantilla de ejemplo, no un veredicto automatizado de validación.

```hcl
# Separate disposable fixture; configure the Kubernetes provider/context externally.
variable "validation_namespace" {
  type = string
  validation {
    condition     = can(regex("^eks-upgrade-validation-[a-z0-9]{8,16}$", var.validation_namespace))
    error_message = "Supply a new, unique namespace with the required validation prefix."
  }
}
variable "test_storage_class" {
  type = string
  validation {
    condition     = length(trimspace(var.test_storage_class)) > 0
    error_message = "Select an existing compatible test StorageClass."
  }
}

resource "kubernetes_namespace_v1" "validation" {
  metadata {
    name = var.validation_namespace
  }
}

resource "kubernetes_persistent_volume_claim_v1" "validation_pvc" {
  metadata {
    name      = "validation-pvc"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_until_bound = false
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = var.test_storage_class
    resources {
      requests = { storage = "1Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "validation_app" {
  metadata {
    name      = "validation-app"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_for_rollout = true
  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "validation-app" }
    }
    template {
      metadata {
        labels = { app = "validation-app" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "http"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args = [
            "test -f /data/index.html || printf 'fixture\\n' > /data/index.html; exec httpd -f -p 8080 -h /data"
          ]
          port {
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "8080"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "data"
            mount_path = "/data"
          }
        }
        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.validation_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "validation_service" {
  metadata {
    name      = "validation-service"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  spec {
    selector = { app = "validation-app" }
    type     = "ClusterIP"
    port {
      port        = 80
      target_port = "8080"
    }
  }
}
```

`wait_until_bound = false` permite que Terraform cree el consumidor antes de que se vincule un PVC con `WaitForFirstConsumer`. El Deployment espera a que finalice el despliegue y esté listo. Una réplica y `Recreate` evitan presuponer que un volumen RWO pueda adjuntarse durante una actualización gradual en varios nodos; esto provoca indisponibilidad deliberadamente. El PVC sí está montado, pero servir un archivo no demuestra persistencia tras un reemplazo ni una restauración correcta de una copia de seguridad. Reúne evidencia independiente de escritura, reemplazo y lectura, y de restauración. Revisa la política de recuperación del PV antes de limpiarlo. Los campos de recursos `_v1` se contrastaron con la documentación del proveedor; no se ejecutó `apply` del proveedor de Kubernetes ni la plantilla en un entorno activo.

**Panel de validación**

El siguiente ConfigMap presupone que existe un sidecar de paneles de Grafana que observa `monitoring` con la etiqueta `grafana_dashboard=1`, el UID de origen de datos `prometheus` y una disposición de scrape de kube-prometheus-stack de un solo clúster. Ajusta esos valores y las etiquetas de job a la instalación real. No instales una segunda pila de supervisión para esta plantilla.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-validation-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  cluster-validation.json: |
    {
      "uid": "eks-upgrade-validation",
      "title": "EKS Upgrade Validation",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Ready nodes",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum(max by (node) (kube_node_status_condition{job=\"kube-state-metrics\",condition=\"Ready\",status=\"true\"}))"
            }
          ]
        },
        {
          "id": 2,
          "title": "Ready active Pods (%)",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * sum(max by (namespace, pod, uid) (kube_pod_status_ready{job=\"kube-state-metrics\",condition=\"true\"}) and on (namespace, pod, uid) (max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}) == 1)) / sum(max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}))"
            }
          ]
        },
        {
          "id": 3,
          "title": "API requests / second",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "reqps"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (code) (rate(apiserver_request_total{job=\"apiserver\"}[5m]))"
            }
          ]
        },
        {
          "id": 4,
          "title": "Node CPU busy (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - avg by (instance) (max by (instance, cpu) (rate(node_cpu_seconds_total{job=\"node-exporter\",mode=\"idle\"}[5m]))))"
            }
          ]
        },
        {
          "id": 5,
          "title": "Node memory used (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 16
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - max by (instance) (node_memory_MemAvailable_bytes{job=\"node-exporter\"}) / max by (instance) (node_memory_MemTotal_bytes{job=\"node-exporter\"}))"
            }
          ]
        }
      ]
    }
```

«Pods activos listos» usa el estado de disponibilidad y excluye las fases completadas o fallidas; `Running` por sí solo no indica disponibilidad. El panel de CPU usa la tasa del contador de tiempo inactivo, y la memoria tiene su propio panel de porcentaje. Las muestras duplicadas del exportador se reducen dentro del ámbito declarado de un solo clúster. Para fuentes de varios clústeres, filtra o agrupa por la etiqueta del clúster antes de combinar series. Si faltan métricas o el denominador de Pods activos es cero, el resultado debe quedar como desconocido o sin datos, no reemplazarse por un cero que parezca saludable. El panel no verifica por sí mismo una actualización ni aplica una condición de lanzamiento.

Guarda los ID de actualización, evidencias de la prueba rápida, entorno y hora de las pruebas, consultas y períodos de métricas, fallos y cobertura pendiente en un directorio privado de resultados. Observa el tráfico canario y los criterios de recuperación antes de aumentarlo en producción. A y B son comprobaciones parciales útiles; ninguna cubre la funcionalidad. D expone a los usuarios antes de completar las comprobaciones.

Fuentes: [volúmenes persistentes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [ciclo de vida de Pods](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [PVC de Terraform](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume_claim_v1), [funciones de Prometheus](https://prometheus.io/docs/prometheus/latest/querying/functions/).

</details>
