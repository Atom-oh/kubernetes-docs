# Cuestionario de solución de problemas de Amazon EKS

> **Última actualización**: 12 de septiembre de 2026

Este cuestionario evalúa cómo diagnosticar y resolver distintos problemas que pueden aparecer en clústeres de Amazon EKS.

## Resumen del cuestionario

- Problemas de creación y configuración del clúster
- Problemas de red
- Problemas de nodos y Pods
- Problemas de almacenamiento
- Problemas de seguridad y acceso
- Problemas de rendimiento y escalabilidad

## Preguntas de opción múltiple

### 1. ¿Cuál es la primera respuesta más útil ante un fallo al crear el plano de control de EKS?

- A. Comprobar únicamente que el nombre del clúster sea único
- B. Revisar el error y la solicitud exactos, y verificar IAM del solicitante y del rol de servicio, VPC/subredes y cuotas pertinentes
- C. Crear inmediatamente otro clúster en otra región
- D. Elegir una instancia de trabajo de mayor tamaño

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Revisar el error y la solicitud exactos, y verificar IAM del solicitante y del rol de servicio, VPC/subredes y cuotas pertinentes**

Empieza por la solicitud fallida o el evento de CloudFormation. IAM, red, cuotas y conflictos de nombre son hipótesis que conviene verificar, no un diagnóstico probabilístico antes de leer el error.

**Qué verificar**

| Área | Evidencia |
| --- | --- |
| Solicitante | Cuenta, región y perfil correctos; acciones de EKS, `iam:PassRole`, límites y controles de sesión/SCP, y permiso para el rol vinculado al servicio cuando corresponda |
| Rol de servicio del clúster | ARN exacto, relación de confianza con EKS y políticas necesarias; es distinto del solicitante y del rol de los nodos |
| Subredes del clúster | Zonas de disponibilidad admitidas, al menos dos AZ distintas y direcciones disponibles; la capacidad para nodos, Pods y balanceadores tiene un presupuesto separado |
| Punto de conexión y dependencias | Modalidad privada/pública prevista, DNS, rutas, grupos de seguridad/NACL y acceso necesario a servicios de AWS |
| Cuotas | Servicio y cuota reales, límite regional vigente para esa cuenta y restricciones de vCPU de EC2 cuando se creen nodos |
| Propietario de la infraestructura | Configuración original de Terraform, CloudFormation o eksctl, estado y operación fallida |

El requisito actual de EKS es disponer de al menos **seis direcciones IP por cada subred seleccionada para el clúster**; se recomiendan **16** como mínimo, en subredes de al menos dos AZ. El tamaño del CIDR por sí solo no demuestra que esas direcciones estén libres. La antigua recomendación genérica «mínimo /28, recomendado /24» confundía el tamaño necesario para el plano de control con el de las cargas. Una configuración privada puede usar los puntos de conexión necesarios; NAT o acceso general a Internet no son requisitos universales.

`AmazonEKSClusterPolicy` corresponde al rol de servicio del clúster. Adjuntarla a una persona no concede todos los permisos de creación/`PassRole` ni el acceso RBAC de Kubernetes. Añadir una etiqueta de propiedad del clúster a la subred tampoco corrige universalmente la creación.

**Investigación de solo lectura**

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"; : "${CLUSTER_NAME:?}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch" >&2; exit 1
fi
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateCluster \
  --max-items 20 --output json
aws service-quotas list-service-quotas --service-code eks --region "$AWS_REGION"
: "${VPC_ID:?Set the VPC from the original request}"
aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,AZId:AvailabilityZoneId,AvailableIPs:AvailableIpAddressCount}'
# For an eksctl-owned creation attempt, inspect its existing stacks:
eksctl utils describe-stacks --cluster "$CLUSTER_NAME" --region "$AWS_REGION"
```

Si ya existe un clúster utilizable, inspecciónalo con `describe-cluster`; si no existe, conserva el error de creación en vez de tratar `ResourceNotFound` como otra causa raíz. Si el propietario usa CloudFormation, consulta los eventos de esa pila. `eksctl create cluster --verbose ...` y el modo de depuración de la CLI siguen aprovisionando recursos; no son diagnósticos de solo lectura.

**Mensajes ilustrativos**

- Un rechazo de `eks:CreateCluster` exige revisar los permisos del solicitante; un problema con el rol de servicio pertenece a otra ruta de permisos.
- El ejemplo antiguo de capacidad insuficiente en `us-west-2a` ilustra una respuesta de capacidad/AZ, no la disponibilidad regional actual.
- El mensaje antiguo «Current limit is 5» se conserva solo como ejemplo histórico; consulta la cuota vigente de la cuenta antes de pedir un nuevo límite.
- `UnsupportedAvailabilityZoneException` identifica AZ de clúster EKS no admitidas para esa cuenta, no solo falta de tipos de instancia EC2.

**Revisión de la configuración de infraestructura**

Inspecciona y corrige la configuración del propietario original. Este fragmento de Terraform ilustra la intención explícita de versión/red y la salida de estado; no es un módulo completo para crear un clúster ni una instrucción para aplicar cambios durante el diagnóstico:

```hcl
# Excerpt of the original state-owned configuration, not a diagnostic apply.
# Preserve its other settings and role/policy dependencies.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.cluster_version
  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = var.cluster_security_group_ids
    endpoint_private_access = true
    endpoint_public_access  = false
  }
}

output "cluster_status" {
  value = aws_eks_cluster.main.status
}
```

Proporciona roles, subredes y grupos de seguridad existentes que hayas verificado, conserva las dependencias de políticas del rol y los demás ajustes, y revisa la ruta de acceso al punto de conexión privado. Terraform evalúa una salida a partir de su estado; si la creación falla, no se garantiza que exista ni que contenga detalles recientes del fallo. Usa los diagnósticos del proveedor y la evidencia de AWS/la pila. En esta revisión no se ejecutó `terraform apply` ni se creó un clúster.

Tras identificar la causa, revisa una corrección concreta de permisos, red o cuota y vuelve a intentarlo mediante el propietario. A es una comprobación limitada útil, pero insuficiente. C cambia la ubicación, los datos y la red, y puede generar costos sin corregir el problema. D cambia los nodos de trabajo, no la creación del plano de control.

Fuentes: [Requisitos de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html), [Solución de problemas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html), [Clúster EKS de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 2. ¿Cuál es la primera investigación más eficaz ante un nodo EKS en estado NotReady?

- A. Terminar el nodo de inmediato
- B. Inspeccionar condiciones/eventos, registros, recursos y la ruta real de red e identidad
- C. Reiniciar por cuenta propia el servidor API administrado de EKS
- D. Eliminar todos los Pods del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inspeccionar condiciones/eventos, registros, recursos y la ruta real de red e identidad**

Investiga a partir del motivo y la hora de la condición y de la identidad real del nodo. `Ready=False`, la ausencia de latidos/`Ready=Unknown`, la presión de disco y la presión de memoria son evidencias diferentes; ninguna identifica automáticamente la causa raíz.

**Inventario de nodos y cargas**

El siguiente ejemplo de solo lectura selecciona el nodo por nombre/UID y sus Pods mediante `spec.nodeName`, evitando búsquedas poco fiables por IP o `grep`:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,labels:.metadata.labels,providerID:.spec.providerID,taints:.spec.taints,unschedulable:.spec.unschedulable,nodeInfo:.status.nodeInfo,conditions:.status.conditions,capacity:.status.capacity,allocatable:.status.allocatable}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A --field-selector "involvedObject.uid=$NODE_UID" \
  --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" get pods -A --field-selector "spec.nodeName=$NODE_NAME" -o wide
```

Confirma `ProviderID`, cuenta/región y tipo de cómputo del nodo antes de acceder a EC2 o al host. En grupos administrados, revisa su estado y la configuración de reparación/actualización:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,release:releaseVersion,nodeRole:nodeRole,repair:nodeRepairConfig,update:updateConfig}'
```

En un nodo Linux estándar accesible, usa el [procedimiento de sesión remota de la guía de origen](../../eks/09-eks-troubleshooting.md) para inspeccionar los registros de kubelet/containerd, bytes e inodos, memoria y rutas. La imagen real puede no tener un daemon Docker ni `/var/log/syslog`. El DNS del nodo no equivale automáticamente al DNS de clúster de los Pods. Verifica TLS del punto de conexión con la CA del clúster; `curl -k` oculta errores de certificado.

Conserva la evidencia antes de purgar imágenes, borrar diarios o reiniciar. `kubectl top` necesita una ruta de métricas funcional y puede fallar si el nodo no está sano. Inspecciona las rutas de certificados configuradas sin exponer claves privadas. `kubeadm alpha certs renew all` no es un comando genérico vigente ni un procedimiento de reparación de nodos EKS; `eksctl replace nodegroup` no está admitido.

**Recuperación y reparación automática**

Después de determinar la causa, coordina el reemplazo o reinicio con el propietario del nodo y teniendo en cuenta capacidad, PDB y datos. Detente si un drenado acotado falla; no continúes hasta terminar el nodo ni lo descordones inmediatamente después de un reinicio asíncrono.

La reparación automática de nodos sí existe en EKS. `update_config.max_unavailable` controla la interrupción durante una actualización de versión; no habilita la reparación, y `health_check { type = "EKS" }` no es un bloque válido de `aws_eks_node_group`. El proveedor actual expone `node_repair_config`:

```hcl
# Fragment of a reviewed EKS-optimized-AMI managed node group.
resource "aws_eks_node_group" "self_healing" {
  cluster_name    = var.cluster_name
  node_group_name = var.node_group_name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.node_kubernetes_version
  ami_type        = var.ami_type
  release_version = var.ami_release
  instance_types  = var.instance_types

  scaling_config {
    desired_size = 3
    min_size     = 3
    max_size     = 6
  }
  update_config {
    max_unavailable = 1
  }
  node_repair_config {
    enabled                           = true
    max_parallel_nodes_repaired_count = 1
  }
}
```

Es un fragmento de configuración, no un módulo de producción probado. Proporciona entradas compatibles y revisadas para Kubernetes, AMI e instancia, y conserva la propiedad existente. Coordina la capacidad deseada si la administra un autoescalador. Las etiquetas del grupo de nodos no demuestran por sí solas que el ASG subyacente tenga etiquetas de descubrimiento del CA.

Los valores predeterminados y umbrales de reparación dependen del propietario del cómputo. Auto Mode habilita la reparación de forma predeterminada; hay que habilitarla en grupos administrados, mientras que Karpenter tiene sus propios requisitos. La supervisión de nodos puede informar problemas aunque la reparación esté deshabilitada. La tabla actual de reparación predeterminada **no** repara automáticamente `MemoryPressure` ni `DiskPressure`. Los umbrales de estado de la flota, el paralelismo y los controles ARC pueden limitar las acciones; no prometas reemplazos incondicionales ni protección PDB.

**Ejemplo de supervisión**

No se puede asumir que `AWS/EKS`, métrica `NodeNotReady`, sea una métrica integrada de esta receta. Una instalación existente de kube-state-metrics/Prometheus Operator puede evaluar las condiciones reales del nodo:

```yaml
# Existing single-cluster Prometheus Operator/KSM installation required.
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-readiness-example
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
    - name: node-readiness-example
      rules:
        - alert: NodeNotReady
          expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="Ready",status="true"}) == 0
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Node {{ $labels.node }} is not Ready"
            description: "Investigate node conditions, reachability and workload impact before recovery."
```

Ajusta los selectores de namespace, release y job a la instalación real. La espera de diez minutos es ilustrativa. Si faltan scrapes o datos de condiciones, hace falta supervisar la salud de la telemetría por separado; no deben contarse como nodos sanos. Esta alarma no configura notificaciones ni ejecuta una recuperación; compruébalas aparte. Crear un Lambda inexistente llamado `node-recovery.zip` no establece una remediación automática segura.

C no es una vía de reinicio administrada por el cliente para el servidor API de EKS, aunque un problema de conectividad con la API sí puede afectar al estado del nodo. A y D amplían la interrupción y pueden destruir evidencia sin resolver la causa.

Fuentes: [Reparación de nodos EKS](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html), [Recurso de nodo administrado de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group), [Métricas de nodos](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md).

</details>

### 3. ¿Qué método investiga correctamente un ImagePullBackOff en EKS?

- A. Aumentar el límite de memoria de todos los contenedores
- B. Leer el error de descarga y verificar la imagen/plataforma y la ruta real de identidad/red de descarga
- C. Forzar otra descarga de imagen sin revisar el error
- D. Eliminar todas las políticas de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Leer el error de descarga y verificar la imagen/plataforma y la ruta real de identidad/red de descarga**

`ImagePullBackOff` es un estado de reintento con espera, no una prueba de una única causa «más probable». Inspecciona el evento exacto de kubelet y todos los contenedores afectados, incluidos los init:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
  node:.spec.nodeName,serviceAccount:.spec.serviceAccountName,
  imagePullSecrets:.spec.imagePullSecrets,
  containers:[.spec.containers[] | {name,image,imagePullPolicy,resources}],
  initContainers:[.spec.initContainers[]? | {name,image,resources}],
  phase:.status.phase,reason:.status.reason,message:.status.message,
  conditions:.status.conditions,containerStatuses:.status.containerStatuses,
  initContainerStatuses:.status.initContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
```

Distingue entre repositorio/etiqueta/digest inexistente, arquitectura no compatible, credenciales/autorización, límites del registro, DNS/TLS/egress del nodo y problemas de disco/runtime local. Una descarga desde Docker local utiliza otra identidad y ruta; no demuestra que el nodo pueda descargar la imagen.

**Identidad y red para ECR**

Normalmente las instancias EC2 usan las credenciales de descarga del rol del nodo; Fargate usa el rol de ejecución del Pod. IRSA/Pod Identity de la aplicación no es la identidad que descarga la imagen antes de iniciar la aplicación. Según corresponda, verifica la política del repositorio y el acceso entre cuentas. Crear un rol nuevo sin asociarlo al cómputo pertinente no cambia las descargas.

Usa explícitamente repositorio, cuenta, región y etiqueta **o** digest; no dividas una cadena arbitraria de imagen con `cut`:

```bash
set -euo pipefail
: "${REGISTRY_REGION:?Set the image registry Region}"
: "${REGISTRY_ACCOUNT_ID:?Set its account ID}"
: "${REPOSITORY_NAME:?Set the exact repository path}"
: "${ECR_IMAGE_ID:?Set imageTag=... or imageDigest=sha256:...}"
aws ecr describe-images --region "$REGISTRY_REGION" \
  --registry-id "$REGISTRY_ACCOUNT_ID" --repository-name "$REPOSITORY_NAME" \
  --image-ids "$ECR_IMAGE_ID" \
  --query 'imageDetails[].{digest:imageDigest,tags:imageTags,pushedAt:imagePushedAt,mediaType:imageManifestMediaType}'
```

Esto consulta metadatos de imagen con las credenciales AWS del operador; no valida los permisos de kubelet. El acceso privado a ECR puede requerir rutas a ECR API/DKR y S3, políticas de punto de conexión/grupos de seguridad y DNS. `ecr.dkr` no es un punto de conexión para cualquier registro privado. Los cambios normales de NetworkPolicy del Pod no suelen reparar la autenticación del runtime del nodo.

**Ejemplo de permisos**

Para un rol existente de nodo EC2 seleccionado deliberadamente, estos permisos ilustran la descarga desde un único repositorio. `GetAuthorizationToken` no admite limitar el recurso al repositorio, por eso su declaración usa `*` con una condición de región; las lecturas de imagen sí se limitan al repositorio:

```hcl
# Permission example for a reviewed existing EC2 node role.
# This does not create/associate a new role or create an image-pull Secret.
data "aws_iam_role" "node" {
  name = var.existing_node_role_name
}

resource "aws_iam_policy" "ecr_pull" {
  name = var.pull_policy_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:RequestedRegion" = var.registry_region }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = var.repository_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = data.aws_iam_role.node.name
  policy_arn = aws_iam_policy.ecr_pull.arn
}
```

Usa el ARN/región reales del repositorio y revisa concesiones, límites/SCP y políticas de repositorio entre cuentas existentes. Añadir una política limitada no elimina una política más amplia ya vigente. Fargate requiere su propia configuración de rol de ejecución; este ejemplo del rol EC2 no crea un Secret de Kubernetes ni configura un perfil Fargate. Durante esta revisión no se aplicó ningún cambio de IAM.

**Secrets para descargar imágenes**

Para registros que necesitan un Secret, usa un archivo Docker auth autónomo y protegido, junto con el [procedimiento de Secret namespaced y plantilla del Pod de la guía de origen](../../eks/09-eks-troubleshooting.md). No imprimas datos del Secret/tokens ni pases contraseñas en argumentos de diagnóstico. Una referencia al helper de credenciales del escritorio no basta como dato de autenticación para kubelet.

En general, un `imagePullSecrets` de un Pod existente no se puede modificar en el sitio. Cambia la plantilla del Deployment/StatefulSet propietario, conserva su lista actual de Secrets y realiza un rollout controlado. Actualizar un ServiceAccount afecta a los Pods nuevos admitidos; evita modificar el ServiceAccount predeterminado de aplicaciones no relacionadas.

**Diseño de renovación de credenciales**

Las descargas estándar de ECR en EKS no requieren el CronJob antiguo de renovación de token. Los tokens de autorización de ECR duran 12 horas. Si un consumidor no nativo realmente necesita un Secret de descarga ECR administrado manualmente, usa su mecanismo compatible o diseña explícitamente un flujo de renovación.

El horario antiguo `*/6 * * * *` significa **cada seis minutos**, no cada seis horas; para cada seis horas se usa `0 */6 * * *`, con la zona horaria del controlador o un `.spec.timeZone` explícito y compatible. El horario por sí solo no constituye un renovador funcional: hacen falta una imagen revisada con las herramientas requeridas, identidad AWS, permisos Kubernetes limitados, namespace de destino exacto, tratamiento de solapamientos/fallos y rotación probada. Déjalo suspendido hasta validar esos elementos. Actualiza un Secret nombrado precreado en lugar de borrarlo y dejar un intervalo sin credenciales. Una imagen oficial de AWS CLI no garantiza que contenga kubectl.

Fija los digests de imagen previstos, mantén disponible el registro e investiga el evento real antes de cambiar la política de descarga. `Always` no arregla una imagen inexistente ni la falta de permisos. A/C/D no identifican la ruta que falló.

Fuentes: [Rol de ejecución de Fargate](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html), [Comando de token ECR](https://docs.aws.amazon.com/cli/latest/reference/ecr/get-authorization-token.html), [Secrets de registros privados](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/).

</details>

### 4. ¿Qué conviene investigar primero cuando un Service no llega a sus Pods?

- A. Recrear el Service inmediatamente
- B. Revisar selector/tipo, estado Ready de los Pods, EndpointSlices, puertos y la ruta realmente permitida
- C. Reiniciar todos los Pods
- D. Reiniciar por cuenta propia el servidor API administrado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Revisar selector/tipo, estado Ready de los Pods, EndpointSlices, puertos y la ruta realmente permitida**

Sigue la ruta de descubrimiento/enrutamiento del Service antes de cambiar recursos. Usa el namespace y cliente de origen afectados, y compara la configuración del Service con los listeners y condiciones de readiness reales de la aplicación:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
SERVICE_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json)
printf '%s\n' "$SERVICE_JSON" | jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace}, spec: .spec, status: .status}'
SELECTOR=$(printf '%s\n' "$SERVICE_JSON" | jq -r '(.spec.selector // {}) | to_entries | map("\(.key)=\(.value)") | join(",")')
if [ -n "$SELECTOR" ]; then
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o json \
    | jq '.items[] | {name:.metadata.name,phase:.status.phase,ready:[.status.conditions[]? | select(.type=="Ready")],containers:.status.containerStatuses}'
else
  printf 'No selector: inspect ExternalName or explicitly managed EndpointSlices as applicable.\n'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
```

El ayudante contempla Services sin selector para no seleccionar accidentalmente todos los Pods. `ExternalName` resuelve un alias; un Service headless tiene intencionalmente `clusterIP: None`; los EndpointSlices administrados manualmente también son válidos. Inspecciona las condiciones Ready/serving/terminating y la política de tráfico. Un sidecar listo o `phase=Running` no equivale a que el Pod esté Ready.

**Corregir el problema observado**

- Selector incorrecto: corrige el Service/plantilla de Pods del propietario, no solo la etiqueta de un Pod reemplazable.
- Puerto incorrecto: el puerto del Service, `targetPort` con nombre y listener real de la aplicación deben coincidir; declarar `containerPort` no crea un listener.
- Restricción de políticas: revisa tanto egress de origen como ingress de destino, etiquetas y cobertura de la implementación. No elimines políticas ni permitas que todos los namespaces accedan a todos los puertos.
- DNS/data plane: separa resolución de transporte e identifica kube-proxy estándar, otra implementación o Auto Mode. Auto Mode puro usa DNS del nodo; los clústeres mixtos conservan el DNS para nodos ajenos a Auto Mode.

Esta **ilustración de política independiente** permite solo un peer/puerto revisado. Adapta etiquetas/namespaces y la matriz completa de flujos necesarios antes de usarla:

```yaml
# Example ingress policy only: review both peers and the complete allowed-flow matrix.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-web
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
```

Puede aislar el ingress de otros backends a menos que otra política lo permita; no crea las reglas de egress del cliente. Se necesitan pruebas positivas y negativas.

**Fixture de Service/Deployment con Terraform**

El ejemplo original Service-a-Pod queda como fixture Linux desechable, con listener declarado real, etiquetas coincidentes, readiness y recursos acotados. Configura el proveedor para el contexto de prueba revisado, elige un namespace nuevo y no importes el namespace de una aplicación existente:

```hcl
# Disposable example; configure the Kubernetes provider/context externally.
variable "test_namespace" {
  type = string
  validation {
    condition     = can(regex("^docs-service-check-[a-z0-9]{8,16}$", var.test_namespace))
    error_message = "Supply a new unique namespace with the test prefix."
  }
}
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.test_namespace
  }
}
resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = "app-deployment"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    replicas = 2
    selector {
      match_labels = { app = "service-demo" }
    }
    template {
      metadata {
        labels = { app = "service-demo" }
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
          name    = "app"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args    = ["mkdir -p /tmp/www; printf 'ok\\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www"]
          port {
            name           = "http"
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "http"
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
            name       = "tmp"
            mount_path = "/tmp"
          }
        }
        volume {
          name = "tmp"
          empty_dir {}
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "app" {
  metadata {
    name      = "app-service"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    selector = { app = "service-demo" }
    type     = "ClusterIP"
    port {
      name        = "http"
      port        = 80
      target_port = "http"
    }
  }
}
```

No es una aplicación de producción ni una recomendación de recursos medida. No necesita API/RBAC de la aplicación. Se revisaron los campos del proveedor, pero no se ejecutó `terraform apply` ni una imagen en vivo.

**Job de conectividad acotado**

Una vez listos el Service y los Pods del fixture, guarda este Job y sustituye el namespace por el preparado. La sonda no necesita el binario kubectl ni un token de API de Kubernetes:

```yaml
# Use kubectl create; replace namespace with the prepared fixture namespace.
apiVersion: batch/v1
kind: Job
metadata:
  generateName: service-probe-
  namespace: docs-service-check-12345678
spec:
  activeDeadlineSeconds: 60
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: probe
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - nslookup app-service; wget -T 5 -q -O- http://app-service:80
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
```

Crea un Job nuevo con nombre generado, no reutilices un nombre común:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TEST_NAMESPACE:?}"; : "${SERVICE_PROBE_FILE:?}"
JOB_NAME=$(kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" create \
  -f "$SERVICE_PROBE_FILE" -o jsonpath='{.metadata.name}')
: "${JOB_NAME:?Job creation did not return a name}"
printf 'Created probe: %s/%s\n' "$TEST_NAMESPACE" "$JOB_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" wait \
  --for=condition=complete "job/$JOB_NAME" --timeout=90s
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" logs "job/$JOB_NAME"
```

Si falla la espera, conserva el Job generado e inspecciona Pod/eventos/logs; no declares éxito incondicional ni elimines un namespace existente. Anota su UID y, después de revisar la evidencia, limpia solo los recursos de prueba propios. La prueba cubre DNS y una solicitud HTTP, no todas las identidades de cliente, rutas directas a Pods, balanceadores ni SLO. Cuando sea necesario, compara por separado el acceso directo al Pod y al Service con el mismo origen autorizado.

A/C hacen perder evidencia o añaden interrupción antes del diagnóstico. D no es una acción del cliente sobre el plano de control de EKS; inspecciona la salud de API/controladores si la evidencia apunta allí.

Fuentes: [Services](https://kubernetes.io/docs/concepts/services-networking/service/), [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 5. ¿Qué deberías investigar primero si una PVC permanece Pending?

- A. Añadir siempre nodos más grandes
- B. Inspeccionar claim/clase, modo de enlace, planificación del consumidor, controlador e identidad de aprovisionamiento
- C. Aumentar siempre la prioridad del Pod
- D. Instalar siempre Cluster Autoscaler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inspeccionar claim/clase, modo de enlace, planificación del consumidor, controlador e identidad de aprovisionamiento**

`Pending` no significa por sí solo que el almacenamiento haya fallado. Con `WaitForFirstConsumer`, es correcto que una claim espere a que se programe un Pod consumidor compatible. Identifica el controlador y la ruta de cómputo reales antes de suponer un problema de EBS o IAM.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,status:.status,spec:.spec,storageClassFieldPresent:(.spec | has("storageClassName"))}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
SC_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.storageClassName // empty')
if [ -n "$SC_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get storageclass "$SC_NAME" -o yaml
else
  printf 'Inspect absent versus explicitly empty storageClassName and default/static binding intent.\n'
fi
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -n "$PV_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o yaml
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json \
    | jq --arg pv "$PV_NAME" '.items[] | select(.spec.source.persistentVolumeName == $pv) | {name:.metadata.name,spec,status}'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json \
  | jq --arg pvc "$PVC_NAME" '.items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName == $pvc)) | {name:.metadata.name,node:.spec.nodeName,phase:.status.phase,conditions:.status.conditions}'
```

El ayudante diferencia `storageClassName` omitido/vacío y selecciona consumidores mediante JSON. Kubernetes no admite el antiguo selector de campos de Pod `spec.volumes.persistentVolumeClaim.claimName`. Si la claim está Bound, investiga el montaje/lectura en vez de considerar que el enlace valida toda la aplicación.

**Comprobar la condición observada**

- Clase/provisioner: confirma que la clase referenciada existe y coincide con el controlador de EBS estándar, Auto Mode, EFS u otro. Una clase explícitamente vacía solicita una ruta de enlace distinta de la clase predeterminada omitida.
- Enlace diferido: inspecciona solicitudes del consumidor, taints/afinidad, zona y capacidad. Oferta de nodos, prioridad y autoescalado pueden afectar indirectamente el progreso de PVC a través del consumidor; A/C/D no son arreglos universales.
- Identidad: revisa IRSA/Pod Identity y permisos KMS del controlador real, no solo el rol del nodo. Fargate no puede montar volúmenes EBS; Auto Mode usa otro provisioner.
- CSI: revisa salud de controladores/nodos, eventos, versión compatible vigente del add-on y su propietario. No reinstales a la fuerza antes de hallar el error.

**Clase y ciclo de vida de datos**

No intentes modificar el modo de enlace inmutable de una StorageClass existente ni cambiar la clase predeterminada del clúster para arreglar una claim. Una clase nueva del controlador estándar, seleccionada explícitamente, puede usar:

```yaml
# New, explicitly selected StorageClass for standard EBS CSI, not an in-place edit.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

El YAML es un ejemplo de configuración, no una orden para aplicar a una clase existente. `Retain` conserva el almacenamiento para decidir aparte su ciclo de vida y puede generar costos. El YAML de una PVC no es un respaldo de datos; borrarla/recrearla puede destruir datos o dejar un volumen retenido que requiera un enlace deliberado.

Auto Mode requiere `ebs.csi.eks.amazonaws.com`, no el provisioner estándar anterior. El cifrado del volumen raíz/datos del nodo no implica que todas las PVC dinámicas estén cifradas. Solicita explícitamente `encrypted: "true"` e inspecciona el volumen/clave EBS real. Sigue el procedimiento documentado de snapshots o migración Retain/estática aplicable, no cambies la clase/provisioner de una claim ya enlazada.

**Ejemplos de propiedad de Terraform**

Para un add-on EBS CSI estándar existente, selecciona una versión revisada, configuración completa validada por esquema e identidad preparada del controlador. Este ejemplo IRSA no configura también Pod Identity:

```hcl
# Existing standard EBS CSI add-on with a reviewed IRSA identity.
# Preserve/import its existing resource ownership; do not create a duplicate add-on.
resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = var.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.reviewed_ebs_addon_version
  service_account_role_arn    = var.controller_irsa_role_arn
  configuration_values        = file(var.reviewed_configuration_file)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

Conserva/importa la propiedad existente. El rol del controlador necesita permisos EBS actuales y limitados con condiciones de etiquetas y, si procede, permisos para la clave del cliente. La antigua pareja de versión del módulo IAM/add-on no era garantía de compatibilidad vigente y `--role-only` no asocia un rol a un add-on. Sigue la [guía de almacenamiento de origen](../../eks/04-eks-storage-part1.md) y el catálogo actual de add-ons.

La misma clase nueva se puede administrar con el recurso actual de Kubernetes:

```hcl
# New standard-driver class, explicitly selected by test PVCs.
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "diagnostic-ebs-gp3"
  }
  storage_provisioner    = "ebs.csi.aws.com"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Retain"
  parameters = {
    type                        = "gp3"
    encrypted                   = "true"
    "csi.storage.k8s.io/fstype" = "ext4"
  }
}
```

Elige YAML **o** Terraform para administrar esa clase. Los campos/sintaxis del proveedor se pueden revisar localmente; eso no demuestra permisos IAM, aprovisionamiento CSI ni recuperación de datos en el clúster destino.

**Prueba de aprovisionamiento aislada**

Para probar una ruta Linux revisada en EC2, guarda el ayudante completo `eks-upgrade-smoke.py` de [Actualizaciones de EKS](../../eks/08-eks-upgrades.md) y usa un contexto/clase de prueba seleccionado explícitamente:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test context}"
: "${TEST_STORAGE_CLASS:?Set the reviewed compatible test class}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
# Save the complete helper from the EKS upgrades source guide first.
python3 eks-upgrade-smoke.py
```

Crea un namespace único y una PVC escritora antes de esperar al enlace diferido; luego lee el marcador desde otro consumidor. Registra evidencia y conserva los fallos. Al ejecutarla, ten en cuenta costos reales de almacenamiento y limpieza de `Retain`. En esta auditoría no se aprovisionó nada en la nube, ni se creó/montó un volumen ni se ejecutó un benchmark; no uses el antiguo Job de AWS CLI que creaba un volumen facturable ajeno al diagnóstico de PVC.

Fuentes: [StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/), [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [Clases de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html).

</details>

### 6. ¿Cuál es la investigación más eficaz cuando el autoescalado no coincide con lo esperado?

- A. Asignar más recursos a todos los Pods
- B. Añadir nodos manualmente y dejar de investigar
- C. Identificar quién administra réplicas/recursos/nodos y revisar sus métricas, condiciones, límites, identidad y eventos
- D. Recrear el clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Identificar quién administra réplicas/recursos/nodos y revisar sus métricas, condiciones, límites, identidad y eventos**

Separa el escalado de réplicas de HPA, las recomendaciones/actualizaciones de recursos de VPA y el aprovisionamiento de nodos de CA/Karpenter/Auto Mode. Cada uno controla recursos distintos y depende de señales diferentes; no es necesario tenerlos todos instalados.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa -o json \
  | jq '.items[] | {name:.metadata.name,target:.spec.scaleTargetRef,min:.spec.minReplicas,max:.spec.maxReplicas,current:.status.currentReplicas,desired:.status.desiredReplicas,metrics:.status.currentMetrics,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

Revisa condiciones de HPA, métricas actuales, requests, mínimo/máximo y comportamiento. Una diferencia entre réplicas deseadas y actuales puede ser convergencia normal. Falta de métricas o errores puede impedir la reducción. Métricas de recursos CPU/memoria usan Metrics Server; métricas personalizadas/externas necesitan su propio adaptador/integración. Una consulta fallida no demuestra que falte una API/CRD.

Para un grupo administrado existente, inspecciona su ASG real en lugar de buscar todos los grupos de la cuenta con etiquetas supuestas:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{scaling:scalingConfig,health:health,autoScalingGroups:resources.autoScalingGroups}'
: "${ASG_NAME:?Select the actual group returned above}"
aws autoscaling describe-auto-scaling-groups --region "$AWS_REGION" \
  --auto-scaling-group-names "$ASG_NAME" \
  --query 'AutoScalingGroups[].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:Instances,Tags:Tags}'
```

CA reacciona a Pods imposibles de programar y sus restricciones, no al promedio alto de CPU de los nodos. Comprueba su minor de Kubernetes compatible, identidad exacta del Pod, permisos de descubrimiento/escalado de privilegio mínimo, etiquetas ASG, tamaño máximo, cuotas EC2/IP y fallos de lanzamiento. Las etiquetas del grupo de nodos no prueban que el ASG tenga etiquetas de descubrimiento. Para límites de grupos administrados, prefiere al propietario EKS/infraestructura; editar directamente el ASG puede crear drift, y los cambios de configuración de escalado no respetan PDB.

Para Karpenter/Auto Mode, inspecciona límites y eventos del NodePool/NodeClaim/proveedor pertinente. No recomiendes instalar CA solo porque una etiqueta fija de Pod de CA no devuelve objetos. En VPA, los modos Off e Initial pueden ser intencionales. Auto está obsoleto en favor de Recreate; cambiar el modo puede interrumpir cargas e interactuar con un HPA que use la misma señal CPU/memoria.

**Ejemplo de configuración Helm/Terraform**

Úsalo únicamente para instalaciones existentes de CA y Metrics Server administradas por Helm. Proporciona versiones de chart revisadas y versión de imagen CA compatible con el minor del clúster; la imagen predeterminada de un chart puede ir retrasada. Mantén un único propietario por componente.

```hcl
# Existing Helm-owned installations only; supply reviewed compatible versions.
# The IRSA trust subject must match kube-system:cluster-autoscaler.
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  version    = var.ca_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  values = [yamlencode({
    autoDiscovery = { clusterName = var.cluster_name }
    awsRegion     = var.aws_region
    image         = { tag = var.ca_image_tag }
    rbac = {
      serviceAccount = {
        create = true
        name   = "cluster-autoscaler"
        annotations = {
          "eks.amazonaws.com/role-arn" = var.ca_irsa_role_arn
        }
      }
    }
  })]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  # Retain/migrate the existing owner's reviewed values.
  values = [file(var.metrics_server_values_file)]
}
```

Usa documentos de valores compatibles con Helm provider 3.x, no el formato repetido `set {}` eliminado. El nombre de ServiceAccount de CA debe coincidir explícitamente con el sujeto de confianza IRSA; Pod Identity es otra configuración administrada. El rol sigue necesitando los permisos limitados descritos en la [guía de costos/escalado](../../eks/07-eks-cost-optimization.md); no adjuntes `AutoScalingFullAccess` como remedio genérico.

Combina con los valores reales revisados de Metrics Server ya instalado. Los valores actuales del chart upstream utilizan la conexión kubelet segura; no implican `--kubelet-insecure-tls`. Diagnostica certificados/confianza/direcciones antes de adoptar una excepción de laboratorio. No crees otro release Helm si un add-on de EKS ya posee el componente. Deben probarse compatibilidad de chart/identidad/red/runtime en el entorno destino; aquí no se instaló Helm.

**Métricas y comportamiento de HPA**

Este ejemplo de métricas de recursos conserva los conceptos de políticas CPU/memoria y de escalado ascendente/descendente:

```yaml
# Example resource metrics and behavior; requires an existing target with requests.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: applications
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
    scaleUp:
      stabilizationWindowSeconds: 60
      selectPolicy: Max
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      selectPolicy: Min
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

Para objetivos de utilización hacen falta requests. HPA elige el mayor número de réplicas deseado entre las recomendaciones de las métricas; las métricas ausentes/con error pueden frenar la reducción. La política Max/Min selecciona la tasa de cambio permitida; estabilización no es un «periodo de enfriamiento» fijo universal. Porcentajes, límites y ventanas son ilustrativos, y el comportamiento con memoria puede diferir del de CPU. Evita que Terraform/GitOps y otros autoescaladores compitan por el mismo número de réplicas.

**Ejemplo de dashboard**

Para una instalación existente de un solo clúster con kube-prometheus-stack, UID de datasource `prometheus` y sidecar que observa la etiqueta `grafana_dashboard=1` en `monitoring`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoscaling-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  autoscaling-dashboard.json: |
    {
      "uid": "eks-autoscaling-diagnostics",
      "title": "EKS Autoscaling Diagnostics",
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
          "title": "HPA replicas",
          "type": "timeseries",
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
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_current_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Current {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "B",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_desired_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Desired {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "C",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_min_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Min {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "D",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_max_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Max {{namespace}}/{{horizontalpodautoscaler}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Observed node count",
          "type": "timeseries",
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
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count(max by (node) (kube_node_info{job=\"kube-state-metrics\"}))",
              "legendFormat": "Nodes"
            }
          ]
        },
        {
          "id": 3,
          "title": "Pod CPU usage (cores)",
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
              "unit": "cores"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        },
        {
          "id": 4,
          "title": "Pod working set (bytes)",
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
              "unit": "bytes"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (container_memory_working_set_bytes{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        }
      ]
    }
```

Adapta selectores/UID/namespace a la instalación. Las series HPA conservan la identidad del namespace; reduce las muestras duplicadas del exporter antes de agregarlas. CPU se expresa en núcleos usados y memoria en bytes de working set, no en porcentajes. Para varios clústeres, agrega una dimensión/filtro de clúster. Scrapes ausentes deben seguir siendo sin datos/desconocidos, no cero saludable. El dashboard no demuestra que el escalado funcionara ni constituye una canalización de alertas/automatización.

A/B pueden modificar temporalmente la capacidad, pero no identifican fallos del controlador/métrica. D añade riesgo de migración sin diagnosticar. Registra el comportamiento esperado/observado y el cambio preciso que lo corrigió.

Fuentes: [Comportamiento de HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/), [Cluster Autoscaler para AWS](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md), [Chart de CA](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler), [Metrics Server](https://github.com/kubernetes-sigs/metrics-server), [VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler).

</details>

### 7. ¿Qué conviene investigar cuando las NetworkPolicies se comportan de forma inesperada?

- A. Eliminar todas las NetworkPolicies
- B. Inspeccionar la implementación real de aplicación, selectores/semántica, registros y flujo que falla
- C. Activar `hostNetwork` en todos los Pods
- D. Reconstruir la VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inspeccionar la implementación real de aplicación, selectores/semántica, registros y flujo que falla**

Revisa tanto la política declarada como la implementación que la hace cumplir. Crear un objeto NetworkPolicy no instala por sí mismo un motor de aplicación.

**Inventario y semántica**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,labels:.metadata.labels,owners:.metadata.ownerReferences,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,status:.status.phase}'
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" --show-labels
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" get daemonsets -A -o json \
  | jq '.items[] | {namespace:.metadata.namespace,name:.metadata.name,containers:[.spec.template.spec.containers[] | {name,image}]}'
```

Una lista vacía de Pods igualmente produce un código de salida kubectl exitoso. No uses `if kubectl get pods -l ...` para demostrar que VPC CNI, Calico o Cilium están instalados. Inspecciona el propietario configurado, los objetos/imágenes reales, estado del agente de políticas y cómputo/kernel/versiones compatibles. Auto Mode usa controles de red integrados en su NodeClass y no admite instalar CNI alternativos arbitrarios.

VPC CNI sí admite políticas nativas. La guía actual de AWS diferencia modo de inicio estándar (permiso inicial mientras se configuran reglas para un Pod nuevo) del modo estricto (denegación inicial, que requiere habilitar rutas DNS/dependencias necesarias). Inspecciona el contenedor real del agente de políticas y si se habilitó el registro de eventos; no supongas que la antigua afirmación «VPC CNI no admite políticas» siga vigente.

En una **NetworkPolicy estándar `networking.k8s.io/v1`**, el tráfico permitido por las políticas es aditivo: no hay prioridad de reglas ni resolución de conflictos «gana la última». Para una conexión se deben permitir tanto el egress de un origen aislado como el ingress del destino. Las APIs de políticas de administración/clúster o de proveedor tienen otra semántica y deben examinarse por separado. El comportamiento de `hostNetwork` también depende de la implementación; no lo actives en todos los Pods como arreglo.

**Ejemplo de política limitada**

Los siguientes dos documentos usan `---` entre objetos. Presuponen un namespace backend, Pods web frontend, Pods de base de datos y endpoints tradicionales de Pods CoreDNS:

```yaml
# Independent example for a reviewed backend namespace and traditional CoreDNS Pods.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: backend
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: database
          podSelector:
            matchLabels:
              app: db
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

Los selectores de namespace y Pod están en el **mismo peer**, por tanto ambos deben coincidir. Peers separados se combinan con OR. Los namespaces usan la etiqueta estándar `kubernetes.io/metadata.name`; no des por existente una etiqueta personalizada `name`.

La denegación predeterminada selecciona todos los Pods backend; las excepciones mostradas solo se aplican a los Pods API seleccionados. Otros backends y dependencias del API requieren sus propias autorizaciones revisadas. Esto no configura el egress del frontend ni el ingress de la base de datos. La regla DNS apunta a Pods CoreDNS, no a una ruta universal para Auto Mode/NodeLocal.

Prueba el flujo permitido frontend-web→API:8080, las rutas denegadas con namespace/etiqueta/puerto incorrectos, API→base-datos:5432 y la ruta DNS real usando cargas de prueba adecuadas y administradas por su propietario. Un Pod de depuración recién creado sin etiquetas puede tener otra política que el Pod afectado; `ping` por sí solo no prueba una política TCP/UDP. Limita cualquier captura autorizada al namespace/tráfico y duración previstos; un Pod tcpdump separado no puede observar todos los demás Pods.

**Alternativa Terraform**

```hcl
# Alternative owner for the same policy intent; do not also apply duplicate YAML.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}
resource "kubernetes_network_policy_v1" "api" {
  metadata {
    name      = "api-allow"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {
      match_labels = { app = "api" }
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "frontend" }
        }
        pod_selector {
          match_labels = { app = "web" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "8080"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "database" }
        }
        pod_selector {
          match_labels = { app = "db" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "5432"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
      ports {
        protocol = "TCP"
        port     = "53"
      }
    }
  }
}
```

Usa un propietario único y revisa/aplica la matriz completa de flujos en un entorno aislado. Se verificaron los campos actuales del proveedor Kubernetes, pero en esta auditoría no se aplicó una política ni se probaron flujos. Instalar una versión no fijada de Calico/Cilium o cambiar solo la imagen de aws-node no es una reparación general; sigue el procedimiento vigente de actualización/migración de la implementación.

**El inventario no demuestra que se aplique la política**

El ejemplo original `kube_networkpolicy_info`/`calico_denied_packets` no demostraba que existieran esas métricas con las etiquetas supuestas. kube-state-metrics documenta ahora gauges experimentales para políticas creadas y reglas ingress/egress. Con un scrape existente de un solo clúster y sidecar de Grafana, este ConfigMap muestra el inventario declarado:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: network-policy-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  network-policy-dashboard.json: |
    {
      "uid": "eks-network-policy-inventory",
      "title": "Declared NetworkPolicy Inventory",
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
          "title": "Declared policies by namespace",
          "type": "timeseries",
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
              "expr": "count by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_created{job=\"kube-state-metrics\"}))",
              "legendFormat": "{{namespace}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Declared ingress/egress rule counts",
          "type": "timeseries",
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
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_ingress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Ingress {{namespace}}"
            },
            {
              "refId": "B",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_egress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Egress {{namespace}}"
            }
          ]
        }
      ]
    }
```

Verifica que las métricas experimentales se expongan y adapta selectores de job/UID/namespace. Cero reglas puede representar denegación total; contar políticas/reglas no mide conexiones descartadas ni prueba la aplicación. La falta de telemetría es desconocida, no cero saludable. Para evidencia de permitir/denegar, usa los registros de decisión/observabilidad de flujos de la implementación real, habilitados y con esquema/etiquetas publicados; no inventes un contador ni trates cualquier log que diga «policy» como denegación.

Eliminar políticas, activar `hostNetwork` para todas las cargas o reconstruir la VPC puede ampliar la exposición sin identificar la causa. Conserva la evidencia del flujo fallido y corrige solo la política/configuración verificada.

Fuentes: [NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Políticas de VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [Red de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [Métricas de políticas de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/policy/networkpolicy-metrics.md).

</details>

### 8. ¿Qué enfoque es más eficaz ante un problema de despliegue con Helm?

- A. Eliminar todos los releases de Helm
- B. Recrear el clúster EKS
- C. Inspeccionar cliente/chart/dependencias, propiedad del release, permisos, eventos y comportamiento de la carga
- D. Sustituir la gestión de releases por recursos manuales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Inspeccionar cliente/chart/dependencias, propiedad del release, permisos, eventos y comportamiento de la carga**

Separa errores de cliente/chart, admisión/permisos de Kubernetes, readiness de la carga y comportamiento de la aplicación. Helm 2/Tiller pertenece a una conversación histórica de migración; el uso actual de Helm 3/4 no requiere un despliegue Tiller.

**Inspeccionar el release real**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${RELEASE_NAME:?}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
HELM_EVIDENCE=$(mktemp -d "$EVIDENCE_PARENT/helm-diagnosis.XXXXXXXX")
helm version --short
helm status "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm history "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm get values "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > "$HELM_EVIDENCE/values.yaml"
helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  > "$HELM_EVIDENCE/manifest.yaml"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp' > "$HELM_EVIDENCE/events.txt"
printf 'Review protected evidence in %s\n' "$HELM_EVIDENCE"
```

Un fallo al consultar puede deberse a permisos, red o contexto; no prueba que el release esté ausente. Los values y manifiestos renderizados pueden contener credenciales o datos de Secrets: protégelos y ocúltalos antes de compartirlos. Las etiquetas como `app.kubernetes.io/instance` son convenciones, no un inventario completo de propiedad. Usa el manifiesto del release para identificar los recursos exactos e inspecciona sus condiciones/eventos.

La identidad de Kubernetes del cliente Helm es distinta del ServiceAccount de carga que seleccionen los values del chart. No existe una opción actual `helm install --service-account`. Usa los valores documentados del chart para ServiceAccount e inspecciona RBAC del actor concreto. La suplantación de identidad requiere permisos y no reproduce todos los grants de políticas de acceso EKS.

**Validar configuración antes de cambiarla**

```bash
set -euo pipefail
: "${CHART_DIR:?}"; : "${VALUES_FILE:?}"; : "${KUBE_VERSION:?Set the target capability version}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
RENDER_DIR=$(mktemp -d "$EVIDENCE_PARENT/helm-render.XXXXXXXX")
# For charts with dependencies, first review/commit Chart.lock and build from that lock.
helm lint "$CHART_DIR" --values "$VALUES_FILE"
helm template review "$CHART_DIR" --namespace review \
  --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
  > "$RENDER_DIR/rendered.yaml"
```

Renderizar/lintar no demuestra compatibilidad con API/admisión del servidor, CRD instalada, imagen funcional, readiness ni una prueba de aplicación satisfactoria. `--debug` en una instalación sigue instalando. `helm dependency update` puede cambiar la selección/lock de dependencias; para reproducibilidad usa un `Chart.lock` revisado y `dependency build`. Sin un lock, `build` puede resolver dependencias, así que no lo describas como verificación bloqueada.

Ante conflictos de recursos, identifica el propietario existente y la migración prevista. No desinstales automáticamente un release, borres recursos sobrantes, uses `force`/`take-ownership` ni elijas otro nombre de release. Podrías afectar datos y crear controladores duplicados. Antes de una actualización del propietario, conserva values actuales, esquema/CRD y dependencias con estado.

**Semántica del proveedor Helm de Terraform**

Este ejemplo se dirige al esquema 3.3 del proveedor Helm revisado localmente y a un namespace/propietario de release preparado. Usa kubeconfig con el flujo de credenciales `exec` revisado en lugar de capturar un token de corta duración para una ejecución larga:

```hcl
# Choose the existing release/configuration owner and reviewed chart artifact.
variable "verify_chart_provenance" {
  type = bool
}
provider "helm" {
  debug = false
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}
resource "helm_release" "example" {
  name              = var.release_name
  repository        = var.chart_repository
  chart             = var.chart_name
  version           = var.chart_version
  namespace         = var.release_namespace
  create_namespace  = false
  values            = [file(var.reviewed_values_file)]
  dependency_update = false
  lint              = true
  wait              = true
  wait_for_jobs     = true
  timeout           = 600
  atomic            = true
  verify            = var.verify_chart_provenance
  keyring           = var.chart_keyring
}
```

`lint` es un campo válido del release y ejecuta Helm lint durante el plan. `debug` pertenece al proveedor, no a `helm_release`. Provider 3.x usa atributos de valores anidados como `set = [...]`; el formulario de archivo values evita los bloques `set` repetidos heredados.

`verify` comprueba la procedencia del paquete del chart con una keyring confiable; **no** ejecuta hooks de prueba Helm. Actívalo solo con la configuración real de procedencia/confianza del artefacto y verifica cómo se distribuye. `wait_for_jobs` y `wait` esperan jobs/readiness, no todas las pruebas de aplicación. `atomic` limpia fallos de instalación o revierte una actualización en Helm, no restaura datos de base de datos/PVC ni deshace automáticamente todos los efectos laterales de hooks/CRD/servicios externos.

`set_sensitive` oculta la presentación, pero no hace seguros para publicar los valores normales almacenados en state o releases. Prefiere referencias a Secrets administrados aparte y protege el estado Terraform y el almacenamiento de releases Helm. En esta revisión no se aplicó el proveedor ni se instaló un release.

**Hooks de prueba del chart**

El chart debe definir `my-chart.fullname`, usar ese nombre de Service y exponer las rutas HTTP configuradas. Estos son dos **archivos de plantilla separados**, además de un fragmento de values:

```yaml
# Relevant values fragment for the chart that owns the Service.
service:
  port: 80
tests:
  enabled: true
  image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
  apiPath: /api/health
```

Guárdalo como `templates/tests/test-connection.yaml`:

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-connection" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v/" (include "my-chart.fullname" .) .Values.service.port | quote }}
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
{{- end }}
```

Guárdalo como `templates/tests/test-api.yaml`:

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-api" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v%s" (include "my-chart.fullname" .) .Values.service.port .Values.tests.apiPath | quote }}
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
{{- end }}
```

Las etiquetas de prueba no copian deliberadamente las etiquetas selectoras de la aplicación. Las sondas escriben respuestas en stdout, no usan token de API de Kubernetes y limitan la duración de solicitudes/Pods. `before-hook-creation` permite repetir pruebas y conservar resultados en logs hasta la siguiente ejecución o limpieza propia. Estas pruebas HTTP no validan todo el comportamiento empresarial; `/api/health` debe existir de verdad.

Para un clúster de pruebas aislado y preparado, usa nombres explícitos de release/namespace:

```bash
set -euo pipefail
: "${TEST_CONTEXT:?Set the owned disposable cluster context}"
: "${TEST_NAMESPACE:?Choose a new unique namespace}"
: "${TEST_RELEASE:?}"; : "${CHART_DIR:?}"; : "${VALUES_FILE:?}"
# Fails on an existing namespace rather than adopting it.
TEST_NAMESPACE_UID=$(kubectl --context "$TEST_CONTEXT" create namespace "$TEST_NAMESPACE" \
  -o jsonpath='{.metadata.uid}')
printf 'Test namespace: %s UID: %s\n' "$TEST_NAMESPACE" "$TEST_NAMESPACE_UID"
helm install "$TEST_RELEASE" "$CHART_DIR" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --values "$VALUES_FILE" --wait --timeout 5m
helm test "$TEST_RELEASE" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --logs --timeout 90s
```

Si falla, conserva recursos e inspecciona logs de hooks/cargas. Registra el UID del namespace y verifícalo antes de limpiar ese namespace de prueba; no borres uno preexistente. El antiguo `null_resource` sin triggers de cambio no garantizaba volver a validar después de cada cambio de release.

**Ejemplo de CI estática**

Este workflow comprueba un chart con dependencias/`Chart.lock` versionados y un `ci/values.yaml` sin Secrets. Ajusta la ruta del chart y la versión de capacidades destino. Si el chart no tiene dependencias, omite los pasos de lock/build. No crea un clúster ni afirma que hayan pasado pruebas de runtime:

```yaml
name: Static Helm chart validation
on:
  pull_request:
    paths:
      - charts/**
      - ci/values.yaml
      - .github/workflows/helm-validate.yml
permissions:
  contents: read
jobs:
  lint-render:
    runs-on: ubuntu-24.04
    env:
      CHART_DIR: charts/my-chart
      VALUES_FILE: ci/values.yaml
      KUBE_VERSION: "1.36.0"
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: Azure/setup-helm@9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310 # v5.0.1
        with:
          version: v3.21.3
      - name: Build reviewed dependencies, lint and render
        shell: bash
        run: |
          set -euo pipefail
          umask 077
          test -f "$CHART_DIR/Chart.lock"
          helm dependency build "$CHART_DIR"
          helm lint "$CHART_DIR" --values "$VALUES_FILE"
          helm template chart-ci "$CHART_DIR" --namespace chart-ci \
            --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
            > "$RUNNER_TEMP/chart-rendered.yaml"
```

Se revisaron los pines de action/setup y release en sus metadatos oficiales. Ejecuta aparte la etapa de integración/hooks en un entorno desechable propio cuando corresponda. Si usas chart-testing, emplea el release/namespace que informa y sus opciones de prueba; el nombre del directorio del chart no es contrato para un ciclo `helm test` posterior.

Eliminar todos los charts, recrear EKS o abandonar el administrador de releases no diagnostica el problema original de chart/permisos/runtime.

Fuentes: [Depuración de Helm](https://helm.sh/docs/chart_template_guide/debugging/), [Pruebas de charts](https://helm.sh/docs/topics/chart_tests/), [Release del proveedor Helm](https://registry.terraform.io/providers/hashicorp/helm/latest/docs/resources/release), [Release de setup-helm](https://github.com/Azure/setup-helm/releases/tag/v5.0.1), [Helm 3.21.3](https://github.com/helm/helm/releases/tag/v3.21.3).

</details>

### 9. ¿Qué método permite distinguir una fuga de memoria de otras causas de presión de memoria?

- A. Reiniciar todos los Pods
- B. Aumentar únicamente el tamaño de los nodos
- C. Correlacionar evidencia de memoria/procesos, límites, perfiles de runtime y código de aplicación
- D. Añadir únicamente nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Correlacionar evidencia de memoria/procesos, límites, perfiles de runtime y código de aplicación**

Un working set creciente, un contenedor `OOMKilled` o un nodo `MemoryPressure` no diagnostican por sí solos una fuga de memoria. Compara carga, duración/UID del proceso, heap/memoria nativa, cachés y límites antes de elegir una corrección.

**Recopilar evidencia comparable**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${APP_SELECTOR:?Set an explicit label selector}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
MEMORY_DIR=$(mktemp -d "$EVIDENCE_PARENT/memory-observation.XXXXXXXX")
for sample in {1..10}; do
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$MEMORY_DIR/sample-$sample.time"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$APP_SELECTOR" -o json \
    | jq '[.items[] | {
        name:.metadata.name,uid:.metadata.uid,created:.metadata.creationTimestamp,
        node:.spec.nodeName,phase:.status.phase,
        resources:[.spec.containers[] | {name,resources}],
        containers:((.status.initContainerStatuses // []) + (.status.containerStatuses // []))
      }]' > "$MEMORY_DIR/sample-$sample.pods.json"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods \
    -l "$APP_SELECTOR" --containers > "$MEMORY_DIR/sample-$sample.usage.txt"
  if [ "$sample" -lt 10 ]; then sleep 30; fi
done
printf 'Observations saved to %s; these samples do not establish a leak.\n' "$MEMORY_DIR"
```

Son diez observaciones con pausas de 30 segundos (aproximadamente el plan original de muestreo de cinco minutos, más tiempo de comandos). No se ejecutó durante esta auditoría. Una ventana breve no prueba una fuga de larga duración. Si falla una consulta, se detiene la recopilación y queda evidencia parcial; no conviertas métricas ausentes en uso cero.

Usa etiquetas explícitas en lugar de tratar un prefijo del nombre del Pod como valor de etiqueta y la salida con unidades de kubectl en lugar de ordenar por una supuesta cuarta columna inexistente. Las capturas de Pods guardan UID y estados de contenedores normales/init; un nombre puede reutilizarse tras el reemplazo. Consultas de métricas y estado no forman una captura atómica. Inspecciona motivos de terminación actuales/anteriores y número de reinicios, recordando que el estado solo conserva historial limitado.

**Interpretar la presión de memoria**

- Working set, RSS, heap administrado y asignaciones nativas son mediciones diferentes. El crecimiento de caché o mayor tráfico puede parecer una fuga.
- Un contenedor puede alcanzar su límite cgroup aunque al nodo aún le quede memoria libre. Una gran diferencia entre request y limit no causa por sí sola un OOM.
- kubelet es un proceso del nodo, no un `kubelet-pod` genérico cuyos logs se consultan en kube-system. Usa la ruta de nodo/supervisión compatible.
- La fragmentación es una hipótesis que requiere evidencia; reiniciar periódicamente nodos o forzar GC no es una reparación universal.

**Ejemplo vigente de métrica y unidades**

Para un scrape existente de kube-prometheus-stack de un solo clúster, estas reglas usan métricas actuales de límite por contenedor, reducen muestras duplicadas del exporter y filtran límites faltantes/cero:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: memory-observation
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
  - name: memory-observation
    rules:
    - alert: ContainerWorkingSetHigh
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Container working set is above 85% of its declared limit
        description: Inspect {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container
          }} and actual termination/pressure evidence.
    - alert: ContainerWorkingSetCritical
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Container working set is above 95% of its declared limit
        description: This is an observation threshold, not proof of a leak or guaranteed
          OOM prediction.
    - alert: ContainerWorkingSetGrowth
      expr: max by (namespace, pod, container) (deriv(container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""}[30m]))
        > 5 * 1024 * 1024 / 60
      for: 30m
      labels:
        severity: warning
      annotations:
        summary: Estimated working-set slope exceeds 5 MiB/min
        description: The rolling 30-minute regression has stayed above the threshold;
          correlate with load and process lifetime.
    - alert: NodeMemoryPressure
      expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"})
        == 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Node {{ $labels.node }} reports MemoryPressure
        description: Investigate node resources and workloads; this is distinct from
          a container limit OOM.
```

Adapta selectores de namespace/release/job a la instalación real. Las reglas usan límites normales por contenedor; examina por separado contenedores init y presupuestos a nivel Pod. Contenedores sin límite positivo informado no generan esta proporción; supervisa esa cobertura aparte, no los llames sanos. Los umbrales working-set/límite son observaciones ilustrativas, no detector de fugas de heap.

Aquí `deriv` devuelve **bytes por segundo**. Dividir `5 * 1024 * 1024` entre 60 produce un umbral de **5 MiB/min**. La expresión antigua comparaba con 5 MiB/s aunque el texto decía por minuto. Una regresión de 30 minutos más una espera `for: 30m` no prueba crecimiento monotónico a cada instante. La interpretación depende de scrapes ausentes, reinicios y cambios de carga.

**Requisitos previos para perfilar cada runtime**

| Runtime | Alcance correcto de la investigación |
| --- | --- |
| JVM | Usa herramientas/permisos JDK compatibles con el PID JVM previsto; `jcmd PID GC.heap_info` es un comando de inspección compatible. Los informes de memoria nativa necesitan seguimiento habilitado al inicio. Los heap dumps pueden pausar el proceso y contener secretos |
| Node.js | Usa el mecanismo compatible de inspección/profiling del proceso destino; iniciar `node --inspect` crea otro proceso. Restringe el acceso del depurador |
| Python | Configura profiling/tracemalloc en la aplicación real o en una reproducción controlada. Otro intérprete no inspecciona asignaciones de un proceso existente, y el seguimiento de asignaciones Python no cubre todo el RSS nativo |
| Go | Recopila un perfil heap real y protegido y usa pprof con binario/símbolos correspondientes. No supongas un endpoint de profiling sin autenticación ni `/tmp/profile` preexistente |

Verifica versiones de herramientas/runtime y costo de captura antes de usar en producción. No instales paquetes arbitrarios de profiling en una aplicación en ejecución como paso predeterminado. Aquí no se ejecutó JVM, profiler, heap dump ni experimento de memoria en vivo.

**Ejemplo de configuración de aplicación**

Se conservan los heaps 256m/768m y el contenedor de 1Gi como ilustración, no como óptimo medido. OpenJDK 21 lee `JAVA_TOOL_OPTIONS`; `JAVA_OPTS` solo sirve si el entrypoint de la imagen lo transmite. Los flags de línea de comandos o `_JAVA_OPTIONS` pueden sobrescribirlos; verifica las opciones JVM efectivas. Estas opciones pueden imprimirse al arrancar la JVM, así que no pongas secretos en ellas.

```yaml
# Pod-template fragment for an existing reviewed OpenJDK 21 application container.
# Merge through its owner; this is not a standalone Deployment manifest.
spec:
  template:
    spec:
      containers:
        - name: java-app
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
              ephemeral-storage: 2Gi
            limits:
              cpu: "1"
              memory: 1Gi
              ephemeral-storage: 4Gi
          env:
            - name: JAVA_TOOL_OPTIONS
              value: >-
                -XX:+UseG1GC -XX:MaxGCPauseMillis=200
                -Xms256m -Xmx768m
                -XX:+HeapDumpOnOutOfMemoryError
                -XX:HeapDumpPath=/diagnostics
                -XX:+ExitOnOutOfMemoryError
          volumeMounts:
            - name: heap-diagnostics
              mountPath: /diagnostics
      volumes:
        - name: heap-diagnostics
          emptyDir:
            sizeLimit: 2Gi
```

Conserva la imagen, comportamiento de inicio, otras variables/volúmenes y contexto de seguridad reales de la aplicación. Verifica que su UID pueda escribir en el volumen de diagnóstico. `MaxGCPauseMillis` es un objetivo flexible. El heap es solo parte de la memoria del proceso: deja margen medido para asignaciones nativas, hilos, código/metaspace y otros gastos.

El `emptyDir` respaldado por disco está acotado, pero no es persistente tras borrar el Pod. Recopila/protege artefactos deliberadamente y contempla colisiones de nombres de archivo si se reutilizan PID de contenedor. Un `SIGKILL` del kernel/cgroup puede impedir por completo que la JVM genere heap dump. `ExitOnOutOfMemoryError` trata un OOM lanzado por la JVM; no garantiza un dump ni resuelve la causa de asignación.

Las antiguas variables `MEMORY_MONITOR_*` no son funciones propias de JVM/Kubernetes. Las rutas de liveness/readiness de Spring Actuator solo aplican si la aplicación realmente las habilita y expone; usa su contrato real de salud, sin suponer que funcionen esas URL.

**Administrar la supervisión existente**

```hcl
# Prometheus Operator CRD must already exist before planning this resource.
# Save the reviewed PrometheusRule YAML above as the supplied file.
resource "kubernetes_manifest" "memory_alerts" {
  manifest = yamldecode(file(var.memory_rules_file))
}
```

El proveedor del manifiesto Kubernetes necesita la CRD PrometheusRule durante la planificación; `depends_on` para una instalación Helm en el mismo apply no resuelve de forma general el descubrimiento de esquema. Reutiliza la pila de supervisión existente y los paneles working-set de la Pregunta 6; no instales otra pila ni aludas a un archivo de dashboard inexplicado. Confirma en el entorno real la selección de reglas, el enrutamiento de alertas y la salud de telemetría.

A/B/D pueden mitigar temporalmente la capacidad, pero no demuestran ni corrigen el defecto de asignación. Registra la causa demostrada y valida la corrección de código/configuración con carga representativa.

Fuentes: [Prometheus deriv](https://prometheus.io/docs/prometheus/latest/querying/functions/#deriv), [Métricas actuales de Pods](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md), [Procesamiento de opciones OpenJDK 21](https://github.com/openjdk/jdk21u/blob/master/src/hotspot/share/runtime/arguments.cpp), [Opciones Java 21](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html), [jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html).

</details>

### 10. ¿Cuál es la investigación más eficaz ante fallos de resolución DNS en EKS?

- A. Asignar IP estáticas a todos los Pods
- B. Seguir el resolver del Pod real, implementación DNS, políticas/transporte y upstream configurado
- C. Usar ExternalName para cada Service
- D. Reconstruir la VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Seguir el resolver del Pod real, implementación DNS, políticas/transporte y upstream configurado**

Empieza por el resolver del Pod afectado y el nombre que falla. Separa herramientas ausentes, respuestas DNS, transporte UDP/TCP, configuración upstream/zona privada y caché de la aplicación.

**Inspeccionar la ruta del Pod real**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,dnsPolicy:.spec.dnsPolicy,dnsConfig:.spec.dnsConfig}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- cat /etc/resolv.conf
# Run only where the selected container actually has this diagnostic tool.
: "${DNS_TEST_NAME:?Set the actual Service FQDN or reviewed external name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- nslookup "$DNS_TEST_NAME"
```

Que una imagen no tenga `cat`/`nslookup` es una limitación de herramientas, no un fallo DNS. Usa un método de diagnóstico preparado que conserve contexto relevante de red/identidad del Pod. Un Pod de depuración nuevo puede tener etiquetas, políticas y DNS distintos. Para probar transporte del resolver, usa la IP real del nameserver en vez de depender de que DNS resuelva su propio nombre de Service. Cuando corresponda, comprueba UDP y TCP 53; una comprobación de conexión solo TCP no valida respuestas DNS.

Para CoreDNS tradicional, inspecciona readiness del Deployment, Service/EndpointSlices, configuración y registros:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"
# Traditional CoreDNS path only; pure Auto Mode node DNS is different.
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get service kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get endpointslices \
  -l kubernetes.io/service-name=kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --all-containers=true --prefix=true --since=15m --tail=100
```

**En Auto Mode, CoreDNS se ejecuta como servicio del sistema en los nodos.** En Auto Mode puro puede no haber Deployment tradicional; los clústeres mixtos deben conservarlo para nodos ajenos a Auto. No diagnostiques la falta de ese Deployment como fallo en todos los clústeres ni instales otro DNS node-local en Auto Mode.

**Configuración del resolver y políticas**

`ClusterFirst` es la ruta normal del Pod cuando se quiere DNS de clúster. Un Pod configurado deliberadamente con `hostNetwork` suele necesitar `ClusterFirstWithHostNet` para ese fin. Cambiar a `hostNetwork` solo para corregir DNS altera el aislamiento y no es una solución general. `DNSPolicy None` requiere configuración deliberada completa del resolver.

La antigua dirección `169.254.20.10` era una dirección elegida para NodeLocal DNSCache, no un resolver VPC universal. Un resolver público como `8.8.8.8` no sirve zonas Service de Kubernetes ni nombres privados de AWS, y una lista de nameservers no garantiza fallback consciente de zonas. Inspecciona upstream y dominio de clúster reales de CoreDNS/NodeLocal en vez de codificar `172.20.0.10` o un respaldo público.

Para Pods CoreDNS estándar, este ejemplo permite DNS solo al backend seleccionado. Revisa todo otro egress de la aplicación antes de aplicarlo:

```yaml
# Example for application Pods using traditional CoreDNS Pod endpoints.
# This selects applications and isolates other egress unless another policy allows it.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-dns-egress
  namespace: applications
spec:
  podSelector:
    matchLabels:
      app: example
  policyTypes:
    - Egress
  egress:
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

Puede que hagan falta permisos tanto en el egress del origen como en el ingress del destino. Los selectores de namespace y Pod se combinan con AND en un mismo peer. Las rutas de Auto Mode/NodeLocal requieren tratamiento propio según implementación; no supongas que un selector de etiqueta de Pod apunta a una caché en el host. Un Pod tcpdump separado no captura las consultas de otra carga; utiliza una captura autorizada y limitada en el contexto pertinente.

**Consultar correctamente la configuración DNS de VPC**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
VPC_ID=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsHostnames
DHCP_OPTIONS_ID=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$AWS_REGION" \
  --query 'Vpcs[0].DhcpOptionsId' --output text)
aws ec2 describe-dhcp-options --dhcp-options-ids "$DHCP_OPTIONS_ID" --region "$AWS_REGION"
```

Los atributos DNS se obtienen con `DescribeVpcAttribute`, no de campos de `DescribeVpcs`. El nombre de clúster y región son explícitos; no es seguro dividir alias arbitrarios de kubeconfig para deducir el nombre. Verifica cuenta/contexto antes de esas consultas. Revisa opciones DHCP, rutas/reenviadores DNS y zonas privadas antes de cambiar ajustes VPC compartidos; crear y asociar un nuevo conjunto DHCP no es un arreglo genérico.

**Configuración y propiedad de CoreDNS**

Para un add-on CoreDNS administrado por EKS ya instalado, inspecciona su versión/configuración y el esquema de una propuesta revisada:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name coredns --output json
: "${COREDNS_ADDON_VERSION:?Select a reviewed compatible candidate}"
aws eks describe-addon-configuration --addon-name coredns \
  --addon-version "$COREDNS_ADDON_VERSION" --region "$AWS_REGION" --output json
```

Conserva zonas/reenviadores personalizados y haz coincidir plugins `health`/`ready` con sondas reales. Cantidad de réplicas, CPU/memoria, PDB, ubicación y autoescalado requieren revisión de la carga concreta; el ejemplo anterior de 3 réplicas/70Mi/170Mi no estaba optimizado universalmente. No sustituyas el Deployment propietario por una antigua imagen EKS-Distro 1.8.7 ni apliques un Corefile genérico completo encima de personalizaciones locales.

Un propietario Terraform puede administrar el add-on existente e inspeccionar la VPC existente:

```hcl
# Existing EKS-managed CoreDNS for standard/mixed clusters only.
# Preserve/import the existing resource; do not duplicate its ownership.
resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.reviewed_coredns_version
  configuration_values        = file(var.complete_reviewed_coredns_config)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

# Read an existing VPC; do not add a second aws_vpc resource to repair DNS.
data "aws_vpc" "cluster" {
  id = var.cluster_vpc_id
}
output "vpc_dns_attributes" {
  value = {
    enable_dns_support   = data.aws_vpc.cluster.enable_dns_support
    enable_dns_hostnames = data.aws_vpc.cluster.enable_dns_hostnames
  }
}
```

El archivo de configuración completo debe validarse con el esquema del add-on elegido y sus valores actuales. `PRESERVE` no garantiza combinar por completo una carga explícita. Sigue el procedimiento exacto de actualización de [Actualizaciones EKS](../../eks/08-eks-upgrades.md) y vuelve a verificar el DNS real. Este ejemplo no configura DNS de nodo en Auto Mode ni autoriza reemplazar una VPC compartida.

**NodeLocal DNSCache opcional para una configuración admitida de nodos estándar**

Usa la [guía oficial de instalación](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) y un manifiesto publicado y revisado. El antiguo DaemonSet escrito a mano estaba incompleto; cambiar solo la imagen no aporta interfaces, reglas de filtrado, montajes, Service upstream ni cableado de kubelet.

| Decisión | Preparación requerida |
| --- | --- |
| Dirección local | Elige una IP local de nodo sin conflictos y el dominio de clúster/IP del Service CoreDNS reales; contempla sintaxis de dirección/puerto IPv6 |
| Data plane existente | En la ruta documentada de iptables, la caché escucha en la IP local y la del Service CoreDNS. En una configuración IPVS compatible, escucha solo localmente y hay que cambiar el DNS de clúster de kubelet. Otros modos requieren su integración vigente aplicable |
| Manifiesto/configuración | Renderiza los marcadores de posición documentados y conserva privilegios, interfaces, filtrado, montajes de lock, sondas y upstream necesarios. No sustituyas todo por un DaemonSet antiguo parcial |
| Migración de cargas | Haz coincidir ajustes de nodo/kubelet y comportamiento del resolver de Pods nuevos/existentes; planifica despliegue gradual y reversión de cambios de caché y kubelet |
| Memoria/operación | Dimensiona observando consultas/caché/concurrencia, supervisa fallos y mantén DNS durante reinicios/rollouts |

NodeLocal DNSCache reenvía los fallos de caché al upstream adecuado; no hace que toda consulta acierte en la caché local. La guía oficial advierte que una terminación OOM puede dejar reglas de filtrado apuntando a una caché local no disponible hasta que se reinicie, interrumpiendo DNS. Una solicitud de memoria diminuta fija o añadir una caché no garantizan rendimiento.

Durante esta revisión no se ejecutó una consulta DNS, captura de paquetes, actualización CoreDNS, instalación NodeLocal ni `terraform apply`. Valida la topología y los supuestos en un entorno controlado.

IP estáticas para Pods, `ExternalName` para todo Service o reconstruir la VPC no identifican la ruta de resolver que falla. Registra consulta/respuesta real, contexto de origen, cambio de configuración y evidencia de recuperación.

Fuentes: [CoreDNS en EKS](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html), [DNS de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [DNS de Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [DNS de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html), [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/).

</details>
