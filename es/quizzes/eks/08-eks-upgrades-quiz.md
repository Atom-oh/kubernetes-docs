# Cuestionario sobre actualizaciones de Amazon EKS

> **Última actualización**: 12 de septiembre de 2026

Este cuestionario evalúa tu comprensión de los procesos de actualización de clústeres de Amazon EKS, las prácticas recomendadas, la solución de problemas y otras consideraciones relacionadas.

## Descripción general del cuestionario

- Planificación de actualizaciones de clústeres de EKS
- Actualizaciones del plano de control
- Actualizaciones de grupos de nodos
- Actualizaciones de complementos y componentes
- Pruebas y validación de actualizaciones
- Solución de problemas de actualización

## Preguntas de opción múltiple

### 1. ¿Cuál es el primer paso más importante al planificar una actualización de un clúster de Amazon EKS?

- A. Actualizar inmediatamente el plano de control
- B. Actualizar todas las cargas de trabajo a la vez
- C. Revisar la compatibilidad y establecer un plan de pruebas y recuperación
- D. Actualizar todos los grupos de nodos simultáneamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Revisar la compatibilidad y establecer un plan de pruebas y recuperación**

Revisa la versión de destino de EKS, los cambios de API y las dependencias de las cargas de trabajo antes de elegir una secuencia de cambios. Un inventario de compatibilidad aporta información para tomar una decisión; no certifica la disponibilidad.

**Revisión de compatibilidad**

- Inspecciona manifiestos, versiones de Helm, clientes de API, CRD, webhooks de conversión/admisión y Operators. Incluye CNI/DNS, balanceadores de carga, malla de servicios, almacenamiento, supervisión, registro y componentes de copia de seguridad.
- Usa el catálogo de versiones de clúster de EKS para consultar las versiones de clúster admitidas. En cambio, `describe-addon-versions` muestra la compatibilidad de los complementos con una versión de Kubernetes.
- Revisa EKS Upgrade Insights y las pruebas de auditoría/métricas disponibles para un período representativo. `apiserver_requested_deprecated_apis` es la métrica pertinente del servidor de API cuando está expuesta. La ausencia de una serie, una solicitud denegada o un análisis vacío no demuestra que no haya clientes de API obsoletas. Insights puede conservar el uso histórico dentro de su período de observación.
- El `.apiVersion` actual de un objeto es la representación que se devuelve, no necesariamente la versión de API que solicitó originalmente un cliente. Revisa la configuración implementada, el código fuente y los procesos en tiempo de ejecución.

Guarda `eks-upgrade-preflight.py` de la [guía de referencia](../../eks/08-eks-upgrades.md), revisa sus requisitos previos y ejecuta su inventario de solo lectura de cuenta/contexto/destino:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

El asistente falla si se producen errores en las consultas. Revisa todos los hallazgos de `preflight.json`; el asistente no ejecuta una actualización ni certifica la compatibilidad. Selecciona una versión secundaria admitida por encima de la versión actual, usando el catálogo actual de AWS.

Con una versión revisada de Pluto, analiza los manifiestos renderizados, los metadatos de Helm y la configuración aplicada más recientemente:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"; : "${MANIFEST_DIR:?}"
pluto detect-files --directory "$MANIFEST_DIR" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-helm --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-api-resources --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
```

Un código de salida distinto de cero en un comando anterior detiene este bloque de shell para que se investigue; completa las comprobaciones restantes después de tratar ese resultado. La detección de recursos de API depende de las anotaciones almacenadas y no puede observar todas las solicitudes en tiempo de ejecución. El proyecto kube-no-trouble proporciona el binario `kubent`, no `kubectl-no-trouble`.

**Ejemplos históricos de eliminación de API** (historial de migraciones, no son destinos actuales de actualización de EKS):

| Versión de Kubernetes | API de servicio eliminada / migración |
| --- | --- |
| 1.22 | Se eliminaron varias API beta, incluida la Ingress `networking.k8s.io/v1beta1`; migra a las API estables y sus esquemas de campos |
| 1.25 | `policy/v1beta1` PodSecurityPolicy: migra la aplicación de políticas. `batch/v1beta1` CronJob → `batch/v1` |
| 1.26 | `autoscaling/v2beta2` HPA → `autoscaling/v2`; se eliminó `v1beta1` de control de flujo |
| 1.27 | `storage.k8s.io/v1beta1` CSIStorageCapacity → `storage.k8s.io/v1` |
| 1.29 / 1.32 | Se eliminaron, respectivamente, `v1beta2` / `v1beta3` de FlowSchema / PriorityLevelConfiguration; usa `flowcontrol.apiserver.k8s.io/v1` y migra los campos/valores predeterminados |

Para kubelet 1.25 y versiones posteriores, la política upstream permite kubelets hasta tres versiones secundarias por detrás del servidor de API; nunca permite un kubelet más nuevo. Para kubelets anteriores, el límite es de dos versiones secundarias. Las distintas versiones del servidor de API durante una actualización de alta disponibilidad reducen ese margen. Este es un límite de compatibilidad admitida, no una prueba de que todos los complementos o aplicaciones funcionen. La preparación conservadora para EKS lleva los nodos a la versión **actual** del plano de control antes de la siguiente actualización del plano de control.

**Plantilla de ensayo y plan**

Usa definiciones de infraestructura revisadas para preparar un entorno independiente con redes, IAM, tipos de cómputo, datos y controladores representativos. Registra las diferencias respecto de producción, los costos y quién se encargará de la limpieza. Empieza en desarrollo/puesta en escena y prueba las funciones de negocio, el escalado, la recuperación y las alertas; no ejecutes pruebas de inyección de fallos en producción de manera incidental. El ejemplo antiguo de 1.27→1.28 es histórico, no una recomendación actual de aprovisionamiento.

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

Registra observaciones en lugar de rellenar por adelantado «todo es compatible» o «no hay cambios en las CRD». Revertir una versión no restaura los datos de las aplicaciones; la pregunta 5 aborda los requisitos de elegibilidad y el orden de los tipos de cómputo. A, B y D omiten pruebas o combinan cambios de manera tan amplia que dificultan el diagnóstico y la recuperación.

Fuentes: [Guía de migración de API](https://kubernetes.io/docs/reference/using-api/deprecation-guide/), [política de compatibilidad entre versiones](https://kubernetes.io/releases/version-skew-policy/), [actualizaciones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [Pluto](https://pluto.docs.fairwinds.com/), [kube-no-trouble](https://github.com/doitintl/kube-no-trouble).

</details>

### 2. Tras alinear los nodos con los requisitos previos, ¿cuál es el orden correcto para una actualización local a la siguiente versión secundaria?

- A. Llevar kubelets a la versión secundaria de destino mientras el servidor de API sigue en la versión secundaria anterior
- B. Actualizar el plano de control a la versión secundaria de destino y, después, actualizar por etapas revisadas los grupos de nodos a la versión de destino
- C. Iniciar simultáneamente todos los cambios del plano de control y de los nodos a la versión de destino
- D. Es obligatorio crear un clúster nuevo para cada actualización de versión secundaria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Actualizar el plano de control a la versión secundaria de destino y, después, actualizar por etapas revisadas los grupos de nodos a la versión de destino**

Llevar los nodos a la versión secundaria **actual** del plano de control es una preparación. Pasarlos a la versión secundaria **de destino** debe hacerse después de que el plano de control la admita. EKS actualiza una versión secundaria a la vez. La compatibilidad admitida entre versiones no garantiza la compatibilidad de las aplicaciones. Sigue los requisitos de dependencia de cada componente, incluidas las versiones puente de complementos que podrían ser necesarias antes del cambio del plano de control.

**Preparación y ejecución**

1. Confirma la cuenta, el contexto, la compatibilidad de las versiones actual y de destino, el estado del clúster/nodos, Insights, la capacidad de direcciones IP de las subredes y el acceso. Planifica la capacidad de sustitución y las medidas para controlar las interrupciones de las cargas de trabajo.
2. Valida las copias de seguridad y la restauración. Los usuarios de EKS no pueden ejecutar `etcdctl` contra el plano de control administrado. `kubectl get all` omite muchos recursos y datos persistentes. Usa AWS Backup EKS o copias de seguridad de Velero/aplicaciones configuradas adecuadamente, y prueba su cobertura y restauración.
3. Revisa la comprobación previa de la pregunta 1. Antes de este paso de modificación independiente, guarda `eks-wait-update.py` de la [guía de referencia](../../eks/08-eks-upgrades.md) para el destino revisado, siempre que no haya ninguna actualización en conflicto.

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

El sondeador sigue esta solicitud exacta. Solo `Successful` cuenta como éxito; los errores, la cancelación, un estado desconocido y los errores de API detienen el procedimiento. El tiempo de espera del cliente no cancela la operación de AWS. El estado `ACTIVE` por sí solo no demuestra que esta actualización haya tenido éxito, y `aws eks wait update-successful` no es un waiter de la CLI de EKS.

Como alternativa, `eksctl upgrade cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --version "$TARGET_VERSION"` previsualiza el cambio; `--approve` lo inicia. Elige un único responsable y una sola ruta de ejecución, en lugar de enviar cambios tanto mediante la CLI como mediante Terraform.

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

El endpoint de preparación de la API requiere permisos y es solo una señal. Inspecciona las cargas de trabajo y los controladores reales, en vez de usar objetos obsoletos de `ComponentStatus` o dar por hecho que existe un Pod de etcd administrado. Auto Mode puro usa CoreDNS a nivel de nodo; los clústeres mixtos conservan DNS para los nodos que no son de Auto Mode. La ausencia de los Deployments estándar `aws-node`, kube-proxy o CoreDNS no es, por sí sola, una falla de Auto Mode. `kubectl top` requiere Metrics Server; la disponibilidad de métricas es independiente del éxito de una solicitud.

Continúa con un grupo de nodos/canario revisado y la secuencia de complementos requerida, validando cada etapa. Auto Mode administra los nodos después de la actualización del plano de control. Los Pods de Fargate existentes conservan su versión de kubelet; coordina su sustitución, a cargo del responsable correspondiente, y la disponibilidad.

**Disponibilidad y duración**

La estimación antigua de «20–30 minutos» no incluye información sobre la procedencia de sus mediciones y se conserva únicamente como ejemplo histórico de planificación, no como garantía de duración. Reserva una ventana basándote en los ensayos. Los clientes de API deben reconectarse mientras se sustituyen los servidores de API. Los contenedores existentes pueden seguir ejecutándose, pero los controladores y las aplicaciones que dependen de la API aún pueden verse afectados. Una actualización normal del plano de control, una vez iniciada, no se puede pausar ni cancelar. Conserva los ID de actualización y los errores, y recurre al AWS Support cuando sea necesario; la reversión posterior de versión está sujeta a requisitos de elegibilidad independientes.

**Ejemplo de administración con Terraform**

Modifica el recurso/módulo existente y conserva sus demás opciones y dependencias. Este fragmento no es una definición completa ni un segundo recurso que deba crearse para un clúster existente:

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

Proporciona los valores de IAM, subredes y grupos de seguridad existentes, junto con un destino revisado. Inspecciona el plan del proveedor para detectar sustituciones no deseadas o cambios no relacionados. `prevent_destroy` protege contra la destrucción mediante Terraform, no contra interrupciones del servicio. `ignore_changes = []` vacío no espera ni valida una actualización; el proveedor tiene sus propios waiters/tiempos de espera. El tiempo de espera de IaC no cancela el servicio, y revertir Git no equivale a revertir la versión de EKS. Tras el cambio, usa la validación acotada de la pregunta 6. En esta revisión no se ejecutó nada en un clúster activo.

A hace que kubelet sea más nuevo que el servidor de API. C elimina las etapas de validación. D es falso: la migración a un clúster nuevo es opcional y tiene costos propios de migración de tráfico/datos.

Fuentes: [Procedimiento de actualización de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [copias de seguridad de EKS](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html), [recurso EKS de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 3. ¿Qué método permite controlar una actualización de un grupo de nodos de EKS?

- A. Terminar todos los nodos simultáneamente
- B. Usar una actualización por etapas de un grupo de nodos administrado o una migración azul/verde validada
- C. Dejar las versiones de los nodos sin cambios indefinidamente
- D. Sustituir individualmente los binarios de kubelet en los nodos administrados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar una actualización por etapas de un grupo de nodos administrado o una migración azul/verde validada**

Elige la estrategia según la tolerancia a las interrupciones de las cargas de trabajo, la capacidad, el almacenamiento con estado y el responsable del cómputo. Ni una actualización administrada ni una migración azul/verde garantizan un servicio ininterrumpido.

**Grupos de nodos administrados**

La estrategia de actualización `DEFAULT` crea capacidad de sustitución antes de retirar los nodos antiguos; `MINIMAL` retira la capacidad antigua primero. `maxUnavailable` limita la indisponibilidad simultánea. La ruta normal de desalojo gradual respeta los PDB, pero una actualización forzada puede omitirlos. Estas estrategias difieren de la opción de la consola entre actualización gradual y forzada. Una actualización fallida **no** implica la reversión automática de toda la flota.

Guarda `eks-wait-update.py` de la guía de referencia y completa la revisión de cuenta/contexto/capacidad de la pregunta 1. Para un grupo existente que use una AMI optimizada para EKS, selecciona explícitamente tanto la versión de Kubernetes como una versión compatible de la AMI:

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

El procedimiento se detiene si falla la solicitud o el sondeo. Comprueba las versiones y el estado real de los nodos, la asignación de Pods, los eventos y los SLO de las aplicaciones antes de pasar al siguiente grupo. Para una AMI personalizada, usa una versión revisada nueva de la **misma plantilla de lanzamiento original** y omite `--kubernetes-version` y `--release-version`; sigue la ruta independiente para AMI personalizadas de la guía de referencia. No edites paquetes de kubelet en el lugar ni des por sentado que se actualizaron la AMI, el entorno de ejecución y el proceso de arranque.

`eksctl upgrade nodegroup` usa `--kubernetes-version`; `eksctl create nodegroup` usa `--version`. Para crear el grupo, conserva las subredes, IAM, AMI, etiquetas y taints revisados en la configuración existente del clúster, en lugar de usar una opción `--taints` no admitida o una receta incompleta de una sola línea.

**Secuencia azul/verde**

1. Conserva la capacidad azul. El responsable de infraestructura debe crear la verde con una versión que no sea más nueva que la del plano de control, y con una AMI/arquitectura equivalente, redes privadas y cuotas/capacidad de IP/AZ suficientes.
2. Verifica que los nodos verdes estén `Ready` y prueba DNS, redes, almacenamiento y dependencias de las cargas de trabajo. Aplica un taint a la capacidad verde para los canarios hasta que haya cargas de trabajo adecuadas que lo toleren.
3. Migra por etapas las plantillas de Pod de las cargas de trabajo. La afinidad preferida es solo una preferencia y no mueve los Pods existentes. Usa una selección explícita cuando la ubicación sea obligatoria e inicia una actualización gradual controlada bajo la responsabilidad del propietario de la carga de trabajo.
4. Inspecciona las cargas de trabajo de cada nodo antiguo y drena los nodos de uno en uno. Detente si falla un desalojo; no continúes con la terminación después de un drenaje fallido.
5. Retira la capacidad azul solo después de revisar las pruebas sobre las cargas de trabajo/datos/tráfico y el período de recuperación. Una respuesta afirmativa a una pregunta o una lista de nodos `Ready` no demuestra que la migración haya finalizado.

Lo siguiente es un **ejemplo independiente completo para un canario**, no un manifiesto de reemplazo para una aplicación existente. Prepara deliberadamente su espacio de nombres. Necesita al menos tres nodos Linux verdes aptos debido a la antiafinidad obligatoria por nombre de host. La toleration permite el taint; el selector de nodos elige los nodos verdes. Adapta por separado la imagen/configuración de la aplicación, la política de interrupciones y los parámetros de actualización gradual.

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

La actualización gradual del propio Deployment se controla mediante su estrategia, no mediante el PDB. Un PDB rige los desalojos voluntarios, no la reducción ordinaria de escala de Deployment/ReplicaSet ni todas las terminaciones de infraestructura. La antiafinidad obligatoria puede impedir la programación si desaparece la capacidad adecuada. No se afirma que se haya ejecutado esta imagen ni en un clúster.

Para un nodo antiguo revisado, el drenaje acotado de la guía de referencia conserva las protecciones para los Pods no administrados y los datos de `emptyDir`:

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

Un drenaje fallido puede dejar un nodo aislado o parcialmente drenado; investiga y recupérate deliberadamente. No añadas `--force`, `--delete-emptydir-data` ni `--disable-eviction` solo para terminar la migración.

**Ejemplo azul/verde de Terraform**

Conserva las direcciones y opciones existentes de los recursos. Estos fragmentos para AMI optimizadas para EKS mantienen **ambos** grupos con capacidad positiva; el taint verde coincide deliberadamente con el canario anterior.

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

Proporciona el clúster/rol/subredes existentes, tipos de instancia/familia de AMI compatibles y las versiones y versiones de lanzamiento azul/verde revisadas por separado. La versión verde ya debe ser compatible con el plano de control. La regla para ignorar `desired_size` presupone que un autoscaler es responsable de ese campo; elimínala si Terraform debe ser el responsable. Los cambios de mínimo/máximo siguen aplicándose, y cambiar la configuración de escalado de un grupo de nodos administrado **no** respeta los PDB. No uses un indicador booleano para reducir a cero el grupo azul mientras creas el verde ni establezcas `max_size = 0` (no es válido). La creación de nodos, la migración de cargas de trabajo y el retiro son cambios independientes; una dependencia de Terraform por sí sola no demuestra que las cargas de trabajo estén listas.

Define de antemano los criterios de recuperación. Mientras se conserve la capacidad azul, la ubicación de las cargas de trabajo podría ser reversible, siempre que la compatibilidad de API/datos lo permita. La reversión del plano de control y de la versión del MNG está sujeta a las condiciones adicionales de la pregunta 5. A, C y D amplían las interrupciones, acumulan incompatibilidades de versiones no admitidas o eluden el ciclo de vida de sustitución administrada.

Fuentes: [actualizaciones de nodos administrados](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html), [comportamiento de las actualizaciones](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [PDB](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/), [grupos de nodos de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group).

</details>

### 4. ¿Cuál es el enfoque correcto para administrar complementos durante una actualización de EKS?

- A. Ignorar las actualizaciones de los complementos
- B. Actualizar todos los complementos antes del plano de control, sin importar la compatibilidad
- C. Seleccionar versiones compatibles y seguir la secuencia de dependencias y versiones puente de cada componente
- D. Eliminar todos los complementos y volver a instalarlos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Seleccionar versiones compatibles y seguir la secuencia de dependencias y versiones puente de cada componente**

No existe una regla universal según la cual «todos los complementos se actualizan después del plano de control». Algunos componentes necesitan una versión intermedia compatible con ambas versiones del plano de control antes del cambio; otros se actualizan después. Revisa las versiones de Kubernetes, las arquitecturas, los tipos de cómputo, las API y la ruta de actualización admitidas por cada versión. Las versiones de los complementos administrados por EKS no se actualizan automáticamente junto con la versión del plano de control, y que un complemento sea «administrado» no garantiza la instalación automática de todas las versiones de seguridad.

**Inspeccionar, seleccionar y conservar la configuración**

Para un complemento administrado instalado y bajo tu responsabilidad, inspecciona su estado actual, las versiones candidatas compatibles y el esquema de una versión candidata revisada. El primer elemento de una matriz no es una garantía de que se trate de la «versión más reciente compatible».

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

`addon-before.json` incluye información de versión/configuración/identidad. Un único ConfigMap `aws-node` no es una copia de seguridad completa de CNI; también pueden ser importantes los ajustes de DaemonSet, los recursos personalizados y IAM/Pod Identity. Protege los archivos de evidencia. `addon-config-candidate.json` es un archivo de entrada para revisar, no una configuración de destino que sea válida automáticamente. Combina los ajustes deseados con el nuevo esquema y revisa los campos eliminados/definidos por defecto y las notas de la versión.

Después de completar esa revisión, usa el sondeador de solicitudes exactas de la guía de referencia y un archivo completo de configuración de destino:

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

`PRESERVE` aborda los conflictos con los campos existentes; no garantiza que una carga útil de configuración explícita se combine por completo, se acepte o funcione correctamente. `NONE` falla cuando hay conflictos; `OVERWRITE` puede sustituir las personalizaciones por los valores predeterminados de EKS. No uses overwrite como atajo automático de recuperación. Comprueba tanto que la actualización haya tenido éxito **como** el estado del complemento y el comportamiento de las cargas de trabajo antes de seguir con la siguiente dependencia; esperar 30 segundos no es una comprobación de finalización.

**Comprobaciones específicas de cada componente**

| Componente | Comprobación antes de continuar |
| --- | --- |
| VPC CNI | Ruta de actualización admitida, asignación de IP, redes de nodos/Pods, redes personalizadas e IAM |
| CoreDNS | Resolución de DNS, cambios de Corefile/esquema, programación/estado de preparación y ajustes de PDB |
| kube-proxy | Compatibilidad entre versiones de Kubernetes, accesibilidad de Service y plano de datos real del clúster |
| Cluster Autoscaler | Versión secundaria de Kubernetes admitida, detección/IAM y responsabilidad del escalado |
| Metrics Server | Versiones admitidas, disponibilidad de APIService y acceso/TLS de kubelet |
| Load Balancer Controller / ExternalDNS / malla | Compatibilidad de controlador/chart/CRD/API, IAM, webhook y comportamiento del tráfico |

Auto Mode puro proporciona redes y DNS a nivel de nodo, y no requiere estos complementos de nodos estándar del mismo modo. Los clústeres mixtos deben conservar los componentes necesarios para los nodos que no son de Auto Mode, incluida la cobertura de Deployment de CoreDNS. Identifica quién es responsable antes de actualizar o eliminar cualquier componente.

**Complementos administrados con Terraform**

Usa mapas de versiones/configuración revisados en los recursos existentes administrados por el estado; conserva sus ajustes de IAM/Pod Identity. Estos fragmentos se aplican a complementos para nodos estándar, no a una instalación universal de Auto Mode:

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

El proveedor actual separa `resolve_conflicts_on_create` y `resolve_conflicts_on_update`. La creación no acepta `PRESERVE`; `NONE` expone deliberadamente los conflictos de migración. No añadas un recurso de clúster duplicado para actualizar un complemento. Cambia únicamente el componente previsto para la etapa actual; enumerar tres recursos independientes no establece un orden de actualización seguro. La destrucción de recursos o los cambios de configuración requieren su propia revisión.

**Versiones de Helm autoadministradas**

Usa el responsable de la versión existente, una referencia/versión de chart revisada y valores migrados. La instalación, la migración de propiedad y la actualización son operaciones distintas. Conserva las CRD, la identidad, el ServiceAccount, los ajustes de recursos/programación y el comportamiento actual:

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

Prepara los valores revisados antes del comando final. `--wait` no demuestra que se cumplan los SLO de la aplicación ni gestiona todas las migraciones de CRD. No instales en bloque un segundo controlador ni cambies indicadores de autoscaler no relacionados durante una actualización. Valida los Pods, eventos y funciones representativas de cada versión; registra los errores en lugar de indicar que todo ha terminado incondicionalmente.

A ignora el mantenimiento de seguridad y compatibilidad. B puede instalar versiones incompatibles con el plano de control aún antiguo. D descarta innecesariamente la propiedad/configuración y puede interrumpir las redes o el DNS.

Fuentes: [actualización de complementos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html), [redes de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [complementos de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon), [actualización de Helm](https://helm.sh/docs/helm/helm_upgrade/).

</details>

### 5. ¿Cuál es el enfoque más eficaz para resolver problemas durante una actualización de EKS?

- A. Crear inmediatamente un clúster nuevo
- B. Depender únicamente del AWS Support sin recopilar pruebas
- C. Usar una solución de problemas sistemática, registros y comprobación de hipótesis
- D. Ignorar los problemas de actualización

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Usar una solución de problemas sistemática, registros y comprobación de hipótesis**

Define el síntoma, la hora de inicio, las cargas de trabajo afectadas y el impacto en el negocio; relaciónalos con cambios específicos. Recopila pruebas antes de poner a prueba las hipótesis. Aplica una corrección específica solo después de revisar el impacto esperado; luego verifica la recuperación y registra medidas preventivas. Las posibles causas no son causas raíz confirmadas.

**Diagnóstico de solo lectura**

Confirma la cuenta/contexto y el ID exacto de la operación. El siguiente recopilador valida el tipo de operación antes de realizar consultas y usa un nuevo directorio privado para las pruebas. Un error de consulta detiene el proceso; los archivos escritos hasta ese momento son pruebas parciales, no un diagnóstico satisfactorio.

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

Para una operación de grupo de nodos o de complemento, inspecciona también `health.issues` de ese recurso y su versión/configuración mediante `describe-nodegroup` o `describe-addon`. Comprueba los ProviderID de los nodos, el estado de EC2, IAM/arranque/AMI/redes y las restricciones de programación, según corresponda. No deduzcas la causa únicamente del estado `Failed` de una actualización.

Lee los registros existentes del plano de control en un período acotado:

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

Habilitar el registro es un cambio independiente del clúster y no completa retroactivamente los eventos anteriores. La ausencia de un grupo de registros, un error de permisos o una consulta vacía son limitaciones de visibilidad. Cuando exista un Pod pertinente, inspecciónalo explícitamente:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${AFFECTED_NAMESPACE:?}"; : "${AFFECTED_POD:?}"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" describe pod "$AFFECTED_POD"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" logs "$AFFECTED_POD" \
  --all-containers=true --prefix=true --since=15m --tail=100
```

Los registros de agentes de los Pods no incluyen todos los diarios del host de kubelet/entorno de ejecución. Auto Mode, Fargate y EC2 estándar tienen distintos métodos de acceso para el diagnóstico. Protege las instantáneas y enmascara la configuración sensible antes de compartirla con AWS Support; evita volcar indiscriminadamente el clúster.

| Síntoma | Hipótesis que deben comprobarse con pruebas |
| --- | --- |
| Falló la solicitud al plano de control | Errores exactos de actualización, requisitos previos, IP de subredes/grupos de seguridad y fallos del lado del servicio de AWS |
| Nodo no `Ready` / Pod `Pending` | AMI/arranque, capacidad de EC2, IAM/redes/CNI, taints, afinidad, topología de PVC o recursos |
| Complemento `CrashLoopBackOff` | Configuración/esquema, identidad, imagen/inicio, recursos o compatibilidad de versiones |
| Errores de API de aplicaciones | Clientes de API eliminadas, webhooks de admisión/conversión, permisos o regresión de la aplicación |

Reintentar, eliminar un grupo de nodos o sobrescribir la configuración de un complemento no es un diagnóstico. La recuperación de complementos requiere una versión compatible **y** una configuración/identidad revisada, con supervisión de la solicitud exacta como se describe en la pregunta 4.

**Condiciones actuales de reversión de EKS**

La guía actual de EKS admite la reversión local del plano de control. Es distinta de restaurar datos de aplicaciones y de sustituir un nodo fallido.

- Iníciala dentro de los siete días posteriores a la finalización de una actualización local, y vuelve a la versión secundaria inmediatamente anterior. Un clúster creado con la versión actual no cumple los requisitos; no se admiten reversiones repetidas a versiones secundarias sucesivamente más antiguas.
- La versión de destino debe seguir siendo compatible. Si el destino requiere soporte extendido, se necesita la política `EXTENDED` y se aplican sus cargos. No se puede revertir una actualización automática al final del soporte extendido; los casos al final del soporte estándar están sujetos a las condiciones de política documentadas.
- Comprueba el estado `ACTIVE`, las actualizaciones en conflicto, las funciones incompatibles con versiones anteriores y los demás requisitos previos. Los hallazgos `ERROR`/`UNKNOWN` de `ROLLBACK_READINESS` bloquean el proceso; `WARNING` es una advertencia. `--force` omite las comprobaciones de Insights, no los requisitos de elegibilidad/requisitos previos ni los controles de interrupción de Auto Mode. Esto difiere de la reversión temporal de la aplicación de `--force` de las comprobaciones normales de Upgrade Insights.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

Inspecciona hallazgos concretos con `describe-insight --id "$INSIGHT_ID"`. No interpretes una lista vacía de Insights como prueba de que se cumplen todos los requisitos previos.

| Tipo de cómputo | Orden y límites |
| --- | --- |
| Grupos de nodos administrados | Revierte los grupos correspondientes con `UpdateNodegroupVersion` antes que el plano de control, siguiendo la guía de referencia y los requisitos para AMI personalizadas; verifica los nodos reales |
| Autoadministrados / híbridos | El responsable coordina nodos compatibles y la migración de las cargas de trabajo antes que el plano de control |
| Auto Mode | El servicio revierte primero los nodos y después el plano de control; sigue el ID de actualización aunque el estado del clúster sea `ACTIVE` durante la fase de nodos |
| Fargate | No es posible revertir kubelet en el lugar; coordina el comportamiento y la disponibilidad de Pods/controladores/HPA/GitOps/Jobs para que los Pods de sustitución no vuelvan a crear inmediatamente kubelet más nuevo antes de revertir el plano de control |

Después de validar la secuencia de nodos correspondiente y todos los requisitos previos, la solicitud del plano de control usa `update-cluster-version`, no un comando `rollback-cluster`. Guarda primero el sondeador de la guía de referencia:

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

Para Auto Mode, usa la solicitud alternativa `--rollback-config timeoutMinutes=...` de la guía de referencia, no una segunda solicitud simultánea. El valor predeterminado es 720 minutos, con un intervalo admitido de 120–10080; no es un plazo exacto de finalización. Los presupuestos de deriva en cero o las exclusiones de interrupción de nodos pueden bloquear el avance. Los PDB/las exclusiones de interrupción de Pods interactúan con los períodos de gracia de terminación y no implican protección indefinida. `--force` no omite esos controles.

Solo la fase de nodos de Auto Mode anterior a la reversión del plano de control admite `CancelUpdate` como mejor esfuerzo; las interrupciones en curso podrían completarse. El tiempo de espera/la cancelación deja sin cambios el plano de control y los nodos vuelven a reconciliarse hacia su versión. El tiempo de espera del cliente por sí solo no cancela la operación. Los reintentos siguen sujetos al plazo de elegibilidad original.

La reversión conserva etcd y los datos de las cargas de trabajo/PV, en lugar de restaurar una copia de seguridad; los complementos no se revierten automáticamente. La versión secundaria anterior recibe su versión de plataforma más reciente, que no tiene por qué ser exactamente la versión de plataforma anterior. Revertir CloudFormation o Git no es esta operación del servicio. Sigue el procedimiento de decisión completo de la guía de referencia; durante esta revisión no se ejecutó ninguno de estos comandos contra AWS.

**Registro del incidente**

Se conserva la marca de tiempo original que aparece a continuación. No se proporcionaron pruebas del incidente ni de la causa alegada, así que ambas siguen siendo una ilustración con hipótesis:

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

Comparte el ID exacto de actualización, los registros/errores acotados, el impacto y las acciones intentadas con AWS Support. A puede añadir una migración no planificada sin resolver la causa; B omite pruebas útiles; D deja sin tratar los problemas de fiabilidad/seguridad.

Fuentes: [reversión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), [reversión de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html), [solución de problemas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html).

</details>

### 6. ¿Cuál es el enfoque más completo para validar después de una actualización?

- A. Contar solo los nodos
- B. Verificar solo la versión del clúster
- C. Validar por etapas el estado de la solicitud, los componentes, las funciones de las cargas de trabajo y el rendimiento representativo
- D. Enviar inmediatamente todo el tráfico de producción sin validar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Validar por etapas el estado de la solicitud, los componentes, las funciones de las cargas de trabajo y el rendimiento representativo**

Primero verifica la solicitud de actualización exacta, la versión y el estado de los nodos/complementos. Después, prueba la funcionalidad y compara las métricas de la aplicación con una referencia registrada. Superar una prueba básica es menos que demostrar la preparación para producción o el cumplimiento de un SLO.

| Área | Pruebas |
| --- | --- |
| Plano de control | Resultado de la actualización, disponibilidad/capacidad de respuesta de la API y métricas/registros admitidos; no se puede acceder directamente a etcd administrado |
| Nodos | Condiciones `Ready`, kubelet/AMI/entorno de ejecución esperados, programación y estado específico de cada tipo de cómputo |
| Red | Pod/Service/DNS, Ingress/Gateway, tráfico de salida y conectividad con dependencias |
| Almacenamiento | Aprovisionamiento, escritura/lectura entre consumidores, topología, reprogramación y restauración coherente con la aplicación |
| Seguridad | Comportamiento previsto de autenticación/autorización, seguridad de Pods, NetworkPolicy y cifrado |
| Cargas de trabajo | Actualización gradual/escalado de Deployment, StatefulSets, Jobs/CronJobs, CRD/Operators y webhooks |
| Rendimiento | Tasa de solicitudes comparable, distribución de latencia/errores, tiempo de inicio y uso de recursos durante un período representativo |

Usa `eks-upgrade-smoke.py` de la guía de referencia para una prueba acotada en EC2 Linux, después de revisar el contexto, StorageClass compatible, controlador/IAM de CSI, programación, políticas de admisión/red y costos. Guarda localmente la implementación proporcionada; no es una referencia a una imagen ni a un script de validación indefinidos.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test cluster context}"
: "${TEST_STORAGE_CLASS:?Set an existing compatible test StorageClass}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
python3 eks-upgrade-smoke.py
```

El asistente crea un espacio de nombres único, registra su UID, ejecuta la actualización gradual/escalado de un Deployment y 20 solicitudes HTTP, y escribe y lee un marcador de PVC mediante Jobs independientes. El escritor se crea antes de esperar a que se enlace, para que `WaitForFirstConsumer` pueda programar un consumidor; después se elimina el escritor y, a continuación, se ejecuta el lector. Los fallos conservan las pruebas/recursos. La limpieza opcional tras el éxito exige el mismo UID del espacio de nombres; un PV con política `Retain` podría seguir generando costos. El asistente no prueba todas las cargas de trabajo, los procedimientos de restauración, las configuraciones de Fargate/Auto, los límites de rendimiento ni los controles de seguridad.

Elige pruebas funcionales y de carga adicionales, revisadas por los responsables, de la tabla. `kubectl top` depende de Metrics Server y muestra el uso actual, no demuestra el rendimiento ni la latencia. No uses un bucle wget sin límite contra producción. Registra el tráfico objetivo, la duración, los criterios de éxito/error, la referencia, las diferencias entre entornos y los resultados reales; nunca deduzcas un resultado de referencia a partir de pruebas sintéticas.

**Fixture opcional de Terraform**

Este fixture administrado por separado conserva el ejemplo didáctico de espacio de nombres/Deployment/Service/PVC. Configura el proveedor para el contexto revisado, proporciona un espacio de nombres nuevo y un StorageClass compatible, e inspecciona el plan. No adoptes ni destruyas un espacio de nombres preexistente. Es un fixture, no un veredicto de validación automatizado.

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

`wait_until_bound = false` permite que Terraform cree el consumidor antes de que se enlace un PVC con `WaitForFirstConsumer`. El Deployment espera a que la actualización gradual finalice y alcance el estado de preparación. Una réplica y `Recreate` evitan dar por supuesta la asociación gradual entre varios nodos para un volumen RWO; esto provoca deliberadamente una interrupción. El PVC se monta efectivamente, pero servir un archivo no demuestra la persistencia tras un reemplazo ni que la restauración desde una copia de seguridad haya sido satisfactoria. Usa pruebas independientes de escritura/recreación/lectura y de restauración. Inspecciona la política de recuperación del PV antes de limpiarlo. Los campos de los recursos `_v1` se comprobaron con la documentación del proveedor; no se aplicó la configuración del proveedor de Kubernetes ni se ejecutó el fixture en un entorno activo.

**Panel de validación**

El siguiente ConfigMap presupone que ya existe un sidecar de paneles de Grafana que vigila `monitoring` con la etiqueta `grafana_dashboard=1`, el UID del origen de datos `prometheus` y una disposición de scrape de kube-prometheus-stack para un único clúster. Ajusta esos valores y las etiquetas de los Jobs a la instalación real. No instales una segunda pila de supervisión para este fixture.

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

«Pods activos listos» usa el estado de preparación y excluye las fases del ciclo de vida completadas/fallidas; `Running` por sí solo no significa que estén listos. El panel de CPU usa una tasa del contador de tiempo inactivo, y la memoria tiene su propio panel porcentual. Las muestras duplicadas de los exporters se reducen dentro del ámbito indicado de un único clúster. Para fuentes de varios clústeres, filtra/agrupa por la etiqueta del clúster antes de combinar las series. Las métricas ausentes o un denominador de Pods activos igual a cero deben seguir siendo desconocidos/sin datos, no sustituirse por un cero que indique buen estado. El panel no verifica por sí mismo una actualización ni aplica una condición para autorizar un lanzamiento.

Guarda los ID de actualización, las pruebas básicas, el entorno/horario de las pruebas, las consultas/períodos de métricas, los fallos y la cobertura pendiente en un directorio privado de resultados. Observa el tráfico del canario y los criterios de recuperación antes de aumentar el tráfico de producción. A y B son comprobaciones parciales útiles, pero ninguna cubre la funcionalidad. D expone a los usuarios antes de realizar esas comprobaciones.

Fuentes: [volúmenes persistentes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [ciclo de vida de los Pods](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [PVC de Terraform](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume_claim_v1), [funciones de Prometheus](https://prometheus.io/docs/prometheus/latest/querying/functions/).

</details>
