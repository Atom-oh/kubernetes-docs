# Cuestionario de solución de problemas de Amazon EKS

> **Última actualización**: 12 de septiembre de 2026

Este cuestionario evalúa tu capacidad para diagnosticar y resolver diversos problemas que pueden surgir en los clústeres de Amazon EKS.

## Descripción general del cuestionario

- Problemas de creación y configuración del clúster
- Problemas de red
- Problemas de nodos y Pods
- Problemas de almacenamiento
- Problemas de seguridad y acceso
- Problemas de rendimiento y escalabilidad

## Preguntas de opción múltiple

### 1. ¿Cuál es la primera medida más útil ante un fallo al crear el plano de control de EKS?

- A. Comprobar únicamente si el nombre del clúster es único
- B. Inspeccionar el error/la solicitud exactos y verificar los permisos de IAM del solicitante y del rol de servicio, la VPC/subredes y las cuotas pertinentes
- C. Crear inmediatamente otro clúster en una Región distinta
- D. Seleccionar un tipo de instancia de trabajo más grande

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inspeccionar el error/la solicitud exactos y verificar los permisos de IAM del solicitante y del rol de servicio, la VPC/subredes y las cuotas pertinentes**

Empieza por la solicitud fallida o el evento de CloudFormation. Las comprobaciones de IAM, red, cuotas y conflictos de nombres son hipótesis útiles, no un diagnóstico estadístico que pueda hacerse antes de leer el error.

**Qué verificar**

| Área | Evidencia |
| --- | --- |
| Solicitante | Cuenta/Región/perfil correctos; acciones de EKS requeridas, `iam:PassRole`, límites/controles de sesión/SCP y permiso para el rol vinculado al servicio cuando corresponda |
| Rol de servicio del clúster | ARN exacto del rol, relación de confianza de EKS y políticas requeridas para el rol de servicio; distinto del solicitante y del rol de los nodos de trabajo |
| Subredes del clúster | Zonas de disponibilidad compatibles, al menos dos AZ distintas y direcciones disponibles; la capacidad de nodos/Pods/LB es un presupuesto aparte |
| Punto de conexión/dependencias | Modo privado/público previsto, DNS, rutas, SG/NACL y acceso requerido a los servicios de AWS |
| Cuotas | Servicio/cuota real y límite aplicado actualmente a la cuenta/Región, incluidas las restricciones de vCPU de EC2 cuando se cree el nodo |
| Propietario de la infraestructura | Configuración, estado y operación fallida originales de Terraform/CloudFormation/eksctl |

El requisito actual de EKS es disponer de al menos **seis direcciones IP por cada subred seleccionada para el clúster**, con **16 como mínimo recomendado**, y subredes en al menos dos AZ. El tamaño del CIDR por sí solo no demuestra que esas direcciones sigan disponibles. La antigua formulación genérica «mínimo /28, recomendado /24» también confundía el dimensionamiento del plano de control con el de las cargas de trabajo. Una configuración privada puede usar los puntos de conexión requeridos; NAT/Internet general no es obligatorio en todos los casos.

`AmazonEKSClusterPolicy` corresponde al rol de servicio del clúster. Adjuntarla a un usuario humano no concede todos los permisos de creación/PassRole ni permisos de RBAC de Kubernetes. Del mismo modo, añadir una etiqueta de subred para la propiedad del clúster no es una solución universal a los problemas de creación.

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

Si ya existe un clúster utilizable, inspecciónalo con `describe-cluster`; si no, conserva el error de creación en lugar de tratar `ResourceNotFound` como una segunda causa raíz. Para otros propietarios de CloudFormation, inspecciona los eventos de la pila exacta. `eksctl create cluster --verbose ...` y el modo de depuración de la CLI siguen aprovisionando recursos; no son diagnósticos de solo lectura.

**Mensajes ilustrativos**

- Una llamada `eks:CreateCluster` denegada requiere examinar los permisos del solicitante; un problema con el rol de servicio sigue una ruta de permisos distinta.
- El ejemplo antiguo que informa de capacidad insuficiente en `us-west-2a` ilustra una respuesta relacionada con una AZ/la capacidad, no la disponibilidad regional actual.
- El mensaje antiguo «Current limit is 5» se conserva como ilustración histórica; consulta la cuota aplicada actualmente antes de elegir un valor para solicitar un aumento.
- `UnsupportedAvailabilityZoneException` identifica las AZ del clúster de EKS que no son compatibles con la cuenta, no simplemente la falta de ofertas de ciertos tipos de instancias EC2.

**Revisión de la configuración de infraestructura**

Inspecciona y corrige la configuración original de su propietario. Este fragmento de Terraform ilustra una intención explícita de versión/red y el resultado de estado; no es un módulo completo para un clúster nuevo ni una instrucción para aplicarlo durante el diagnóstico:

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

Proporciona entradas verificadas de roles/subredes/grupos de seguridad existentes, conserva las dependencias requeridas de políticas de roles y los demás ajustes, y revisa cualquier ruta de acceso al punto de conexión privado. Un resultado se evalúa a partir del estado de Terraform; no se garantiza que aparezca ni que contenga detalles actualizados del fallo si la creación falla. Usa los diagnósticos del proveedor y la evidencia de solicitudes/pilas de AWS. Para esta revisión no se ejecutó ningún `apply` de Terraform ni se creó ningún clúster.

Después de identificar la causa, revisa una corrección específica de permisos/red/cuota y vuelve a intentarlo a través del propietario. A es una comprobación limitada útil, pero por sí sola no basta. C cambia la ubicación/los datos/la red y puede aumentar los costos sin corregir la causa. D cambia los nodos de trabajo, no el problema de creación del plano de control.

Fuentes: [Requisitos de red de EKS](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html), [Solución de problemas de EKS](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html), [Clúster de EKS de Terraform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 2. ¿Cuál es la investigación inicial más eficaz de un nodo de EKS en estado NotReady?

- A. Terminar el nodo inmediatamente
- B. Inspeccionar las condiciones y los eventos del nodo, los registros, los recursos y la ruta real de red/identidad
- C. Reiniciar por tu cuenta el servidor de la API de EKS administrado
- D. Eliminar todos los Pods del clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inspeccionar las condiciones y los eventos del nodo, los registros, los recursos y la ruta real de red/identidad**

Investiga a partir del motivo/hora de la condición y de la identidad real del nodo. Ready=False, la ausencia de latidos/Ready=Unknown, la presión de disco y la presión de memoria son evidencias de tipos distintos; ninguna identifica automáticamente la causa raíz.

**Inventario de nodos y cargas de trabajo**

El siguiente ejemplo de solo lectura selecciona el nodo por nombre/UID y sus Pods mediante `spec.nodeName`, evitando la coincidencia poco fiable por IP/grep:

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

Confirma el ProviderID/la cuenta/la Región y el tipo de cómputo del nodo antes de acceder a EC2 o al host. Para grupos administrados, inspecciona su estado de salud y la configuración de reparación/actualización:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,release:releaseVersion,nodeRole:nodeRole,repair:nodeRepairConfig,update:updateConfig}'
```

En un nodo Linux estándar accesible, usa el [procedimiento de sesión remota de la guía de origen](../../eks/09-eks-troubleshooting.md) para inspeccionar los registros de kubelet/containerd, bytes/inodos, memoria y enrutamiento. Puede que el daemon de Docker o `/var/log/syslog` no existan en la imagen real. El DNS del nodo no es automáticamente el DNS del clúster de los Pods. Usa la CA del clúster para TLS del punto de conexión; `curl -k` oculta los problemas de certificados.

Conserva la evidencia antes de podar imágenes, eliminar registros o reiniciar. `kubectl top` requiere que funcione la ruta de métricas y puede fallar en un nodo en mal estado. Inspecciona las rutas de certificados configuradas sin exponer claves privadas. `kubeadm alpha certs renew all` no es un comando genérico actual ni un procedimiento para reparar nodos de EKS; `eksctl replace nodegroup` no es compatible.

**Recuperación frente a reparación automática**

Una vez determinada la causa, coordina el reemplazo/reinicio del nodo teniendo en cuenta la capacidad, los PDB, los datos y el propietario del nodo. Detente si un vaciado acotado falla; no continúes con la terminación ni vuelvas a quitar el cordón inmediatamente después de un reinicio asíncrono.

La reparación automática de nodos es un mecanismo real de EKS. `update_config.max_unavailable` controla la interrupción durante las actualizaciones de versión; no habilita la reparación, y `health_check { type = "EKS" }` no es un bloque de `aws_eks_node_group`. El proveedor actual expone `node_repair_config`:

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

Este es un fragmento de configuración, no un módulo de producción probado. Proporciona entradas compatibles y revisadas de Kubernetes/AMI/instancias y conserva la propiedad existente. Coordina la capacidad deseada con un autoscaler si este la administra. Las etiquetas del grupo de nodos no demuestran automáticamente que el ASG subyacente tenga las etiquetas de detección de CA requeridas.

Los valores predeterminados y umbrales de reparación varían según el propietario del cómputo. Auto Mode habilita de forma predeterminada su comportamiento de reparación; los grupos administrados requieren habilitarlo y Karpenter tiene sus propios requisitos de funciones. La supervisión de nodos puede informar de problemas sin que la reparación esté habilitada. La tabla de reparación predeterminada actual **no** repara automáticamente MemoryPressure ni DiskPressure. Los umbrales de estado de la flota, el paralelismo y los controles de ARC pueden limitar las acciones; no prometas un reemplazo incondicional ni protección de PDB.

**Ejemplo de supervisión**

`AWS/EKS` con el nombre de métrica `NodeNotReady` no es una métrica integrada cuya existencia pueda dar por sentada esta receta. Una instalación existente de kube-state-metrics/Prometheus Operator puede evaluar en su lugar las condiciones reales de los nodos:

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

Configura los selectores de namespace/release/job según la instalación real. La espera de diez minutos es ilustrativa. La falta de datos de sondeo/condición requiere supervisión independiente del estado de la telemetría y no debe tratarse como si los nodos estuvieran en buen estado. Esta alerta no configura notificaciones ni realiza la recuperación; verifícalas por separado. Crear una Lambda `node-recovery.zip` no definida no establecería una remediación automática segura.

C no es una vía de reinicio operada por el cliente para el servidor de la API de EKS administrado, y los problemas de conectividad con la API sí pueden causar problemas de disponibilidad del nodo. A y D amplían la interrupción y pueden destruir evidencia sin resolver la causa subyacente.

Fuentes: [Reparación de nodos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html), [Recurso Terraform de nodos administrados](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group), [Métricas de nodos](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md).

</details>

### 3. ¿Qué enfoque permite investigar correctamente ImagePullBackOff en EKS?

- A. Aumentar el límite de memoria de todos los contenedores
- B. Leer el error de descarga y verificar la imagen/plataforma y la ruta real de identidad/red usada para descargarla
- C. Forzar una nueva descarga de la imagen sin comprobar el error
- D. Eliminar todas las políticas de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Leer el error de descarga y verificar la imagen/plataforma y la ruta real de identidad/red usada para descargarla**

ImagePullBackOff es un estado de reintento/espera progresiva, no una prueba de una única causa «más probable». Inspecciona todos los contenedores afectados, incluidos los contenedores normales y de inicialización, y el evento exacto de kubelet:

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

Distingue entre repositorio/etiqueta/digest inexistente, arquitectura no compatible, credenciales/autorización, límites de solicitudes del registro, DNS/TLS/egreso del nodo y fallos locales de disco/runtime. Una descarga local con Docker usa una identidad/ruta distintas; no demuestra que el nodo pueda descargar la imagen.

**Identidad y red de ECR**

Los nodos EC2 normalmente usan la ruta de credenciales de descarga del nodo; Fargate usa el rol de ejecución del Pod. IRSA/Pod Identity de la aplicación no es la identidad que descarga la imagen antes de que se inicie la aplicación. Verifica la política del repositorio y el acceso entre cuentas cuando corresponda. Crear un rol de IAM sin asociarlo al cómputo pertinente no cambia la descarga de imágenes.

Usa el repositorio/la cuenta/la Región explícitos y una etiqueta **o** un digest, en lugar de dividir una cadena arbitraria de imagen con `cut`:

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

Esto comprueba los metadatos de la imagen con las credenciales de AWS del operador; no valida los permisos de kubelet. El acceso a ECR privado puede requerir rutas de ECR API/DKR y S3, políticas de puntos de conexión/grupos de seguridad y DNS. `ecr.dkr` no es un punto de conexión para registros privados arbitrarios. Por lo general, los cambios de NetworkPolicy de los Pods no reparan la autenticación del registro del runtime del nodo.

**Ejemplo de permisos**

Para un rol de nodo EC2 existente seleccionado deliberadamente, estos permisos ilustran la descarga desde un solo repositorio. `GetAuthorizationToken` no puede limitarse a un recurso de repositorio, por lo que su sentencia usa `*` con una condición de Región; las lecturas de imagen están restringidas al repositorio:

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

Usa el ARN/Región real del repositorio y revisa las concesiones/límites/SCP existentes y la política del repositorio entre cuentas. Añadir una política limitada no elimina una política más amplia que ya exista. Fargate necesita su propia configuración del rol de ejecución; este ejemplo para un rol EC2 no crea un Secret de Kubernetes ni configura un perfil de Fargate. Durante la revisión no se ejecutó ningún cambio de IAM.

**Secrets para descargar imágenes**

Para registros que necesiten un Secret, usa un archivo de autenticación Docker autónomo y protegido, y el [procedimiento de Secret con ámbito de namespace/plantilla de Pod de la guía de origen](../../eks/09-eks-troubleshooting.md). No imprimas datos de Secret/tokens ni pases contraseñas en líneas de comandos de diagnóstico. Una referencia a un ayudante de credenciales de escritorio no proporciona datos de autenticación suficientes para kubelet.

Por lo general, los `imagePullSecrets` de un Pod existente no se pueden modificar directamente. Cambia la plantilla del propietario, ya sea un Deployment o un StatefulSet, conserva su lista actual de Secrets de descarga y realiza una actualización controlada. Actualizar un ServiceAccount afecta a los Pods admitidos posteriormente; evita cambiar el ServiceAccount predeterminado para aplicaciones no relacionadas.

**Diseño de renovación de credenciales**

Las descargas estándar de ECR en EKS no requieren el antiguo CronJob de renovación de tokens. Los tokens de autorización de ECR son válidos durante 12 horas. Si un consumidor no nativo realmente necesita un Secret de descarga de ECR administrado manualmente, usa su mecanismo de credenciales compatible o un flujo de renovación diseñado expresamente.

La programación antigua `*/6 * * * *` significa **cada seis minutos**, no cada seis horas; un ejemplo de cada seis horas es `0 */6 * * *`, con la zona horaria del controlador o un `.spec.timeZone` compatible y explícito. La programación por sí sola no renueva credenciales: se necesita una imagen revisada que contenga las herramientas necesarias, identidad de AWS, permisos de Kubernetes limitados, el namespace de destino exacto, gestión de solapamientos/fallos y rotación probada. Déjalo suspendido hasta validar esos aspectos. Actualiza un Secret existente y previamente creado, en lugar de eliminarlo y dejar un intervalo sin credenciales. Una imagen estándar de AWS CLI no implica que incluya kubectl.

Fija los digest de imagen previstos, mantén la disponibilidad del registro e investiga el evento real antes de cambiar la política de descarga. `Always` no puede corregir una imagen inexistente ni la falta de permisos. A/C/D no identifican la ruta de descarga fallida.

Fuentes: [Rol de ejecución de Fargate](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html), [Comando de token de ECR](https://docs.aws.amazon.com/cli/latest/reference/ecr/get-authorization-token.html), [Secrets para registros privados](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/).

</details>

### 4. ¿Cuál es la primera investigación más útil cuando un Service no llega a sus Pods?

- A. Volver a crear inmediatamente el Service
- B. Comprobar su selector/tipo, la disponibilidad de los Pods, los EndpointSlices, los puertos y la ruta realmente permitida
- C. Reiniciar todos los Pods
- D. Reiniciar por tu cuenta el servidor de la API administrado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Comprobar su selector/tipo, la disponibilidad de los Pods, los EndpointSlices, los puertos y la ruta realmente permitida**

Sigue la ruta de descubrimiento/enrutamiento del Service antes de cambiar recursos. Usa el namespace afectado y el cliente de origen, y compara la configuración del Service con los escuchas reales de la aplicación y su disponibilidad:

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

El ayudante gestiona los Services sin selector sin seleccionar por accidente todos los Pods. ExternalName resuelve un alias; los Services headless usan intencionadamente `clusterIP: None`; los EndpointSlices administrados manualmente son otra posibilidad válida. Inspecciona las condiciones Ready/serving/terminating de los puntos de conexión y los ajustes de política de tráfico. Que un sidecar esté listo o que el estado sea phase=Running no equivale a la condición Ready del Pod.

**Corregir el problema observado**

- Selector que no coincide: actualiza el Service/la plantilla de Pod del propietario, no solo la etiqueta de un Pod reemplazable.
- Puerto que no coincide: el puerto del Service, el `targetPort` con nombre y el listener real de la aplicación deben coincidir; declarar `containerPort` no crea un listener.
- Restricción de políticas: comprueba tanto el egreso del origen como el ingreso del destino, las etiquetas y la cobertura de la implementación. No elimines políticas ni permitas el acceso de todos los namespaces a todos los puertos.
- DNS/plano de datos: distingue la resolución del transporte e identifica kube-proxy estándar, una implementación alternativa o Auto Mode. Auto Mode puro usa el DNS del nodo; los clústeres mixtos conservan DNS para los nodos que no son de Auto Mode.

Esta **ilustración de política independiente** permite solo un par/puerto revisado. Adapta las etiquetas/namespaces y la matriz completa de flujos requeridos antes de usarla:

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

Puede aislar otros ingresos al backend, a menos que otra política los permita, y no crea las reglas de egreso del cliente. Se necesitan pruebas positivas y negativas.

**Fixture de Terraform para Service/Deployment**

El ejemplo original de Service a Pod se conserva como fixture desechable para Linux, con un listener real declarado, etiquetas coincidentes, disponibilidad y recursos limitados. Configura el proveedor para el contexto de prueba revisado, elige un namespace nuevo y no importes un namespace de aplicación existente:

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

No es una aplicación de producción ni una recomendación de recursos basada en mediciones. No tiene requisitos de API/RBAC para la aplicación. Se revisaron los campos del proveedor, pero no se afirma que se haya ejecutado un `apply` real de Terraform ni la imagen.

**Job de conectividad acotado**

Cuando el Service y los Pods del fixture estén listos, guarda el siguiente Job y sustituye el namespace por el namespace preparado. La sonda no necesita un binario de kubectl ni un token de la API de Kubernetes:

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

Crea un Job nuevo con nombre generado en lugar de reutilizar un nombre común:

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

Si la espera falla, conserva el Job generado e inspecciona sus Pods/eventos/registros; no muestres un mensaje de éxito incondicional ni elimines un namespace existente. Registra su UID y elimina solo los recursos de prueba de tu propiedad después de revisar la evidencia. La prueba cubre DNS y una solicitud HTTP, no todas las identidades de clientes, rutas directas a Pods, balanceadores de carga ni SLO. Cuando sea necesario, compara por separado el acceso directo al Pod y el acceso al Service desde el mismo origen autorizado.

A/C destruyen evidencia o aumentan la interrupción antes del diagnóstico. D no es una acción del plano de control de EKS que pueda realizar el cliente; si la evidencia apunta allí, inspecciona el estado de la API/del controlador.

Fuentes: [Services](https://kubernetes.io/docs/concepts/services-networking/service/), [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 5. ¿Qué deberías investigar primero cuando un PVC permanece en estado Pending?

- A. Añadir siempre nodos más grandes
- B. Inspeccionar la reclamación/clase, el modo de enlace, la programación del consumidor, el controlador y la identidad de aprovisionamiento
- C. Aumentar siempre la prioridad del Pod
- D. Instalar siempre Cluster Autoscaler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inspeccionar la reclamación/clase, el modo de enlace, la programación del consumidor, el controlador y la identidad de aprovisionamiento**

Pending no es, por sí mismo, un fallo de almacenamiento. Con WaitForFirstConsumer, una reclamación puede esperar correctamente hasta que se programe un Pod consumidor adecuado. Identifica la ruta real del controlador/cómputo antes de dar por hecho que el problema es de EBS o IAM.

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

El ayudante distingue entre un `storageClassName` ausente y uno vacío, y selecciona consumidores usando JSON. Kubernetes no admite el antiguo selector de campos de Pod `spec.volumes.persistentVolumeClaim.claimName`. Si una reclamación está Bound, investiga el montaje/la legibilidad en lugar de tratar el enlace como una validación completa de la aplicación.

**Comprueba la condición observada**

- Clase/provisionador: verifica que la clase referenciada exista y corresponda a EBS estándar, Auto Mode, EFS u otro controlador. Una clase explícitamente vacía solicita una ruta de enlace distinta a la de una clase predeterminada omitida.
- Enlace retrasado: inspecciona las solicitudes del consumidor, las restricciones de taints/afinidad, la zona y la capacidad. La disponibilidad de nodos, la prioridad y el escalado automático pueden afectar indirectamente al progreso del PVC a través de ese consumidor; A/C/D no son soluciones universales.
- Identidad: inspecciona el IRSA/Pod Identity real del controlador y los permisos de KMS, no solo el rol del nodo. Fargate no puede montar volúmenes EBS; Auto Mode usa su propio aprovisionador.
- CSI: inspecciona el estado del controlador y los nodos, los eventos, la versión actual y compatible del add-on y su propiedad. No reinstales con force antes de encontrar el error.

**Clase y ciclo de vida de los datos**

No modifiques el modo de enlace inmutable de un StorageClass existente ni cambies la clase predeterminada del clúster para solucionar un único PVC. Una clase nueva, seleccionada explícitamente, para el controlador estándar puede usar:

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

El YAML es un ejemplo de configuración, no un comando para aplicar a una clase existente. Retain conserva el almacenamiento para una decisión separada sobre su ciclo de vida y puede generar costos. El YAML de un PVC no es una copia de seguridad de los datos; eliminar y volver a crear la reclamación puede destruir datos o dejar un volumen retenido que requiera volver a enlazarlo deliberadamente.

Auto Mode requiere `ebs.csi.eks.amazonaws.com`, no el aprovisionador estándar anterior. El cifrado del disco raíz/de datos del nodo no implica que todos los PVC aprovisionados dinámicamente estén cifrados. Solicita explícitamente `encrypted: "true"` e inspecciona el volumen/clave EBS real. Usa el procedimiento de instantáneas o el procedimiento de migración Retain/estática correspondiente, documentado, en lugar de cambiar el provisionador/la clase de una reclamación ya enlazada.

**Ejemplos de propiedad en Terraform**

Para un add-on existente de EBS CSI estándar, selecciona una versión revisada, una configuración completa validada según el esquema y la identidad preparada del controlador. Este ejemplo de IRSA no configura también Pod Identity:

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

Conserva/importa la propiedad existente. El rol del controlador necesita permisos de EBS actuales y limitados, condiciones de etiquetas y permisos para la clave del cliente cuando corresponda. El antiguo par de versión del módulo de IAM/add-on no era una garantía de compatibilidad actual, y `--role-only` no adjunta un rol a un add-on. Sigue la [fuente sobre almacenamiento](../../eks/04-eks-storage-part1.md) y el catálogo actual de add-ons.

La misma clase nueva puede administrarse con el recurso actual de Kubernetes:

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

Elige YAML **o** Terraform como propietario de esa clase. Los campos/sintaxis del proveedor pueden revisarse localmente; esto no demuestra la validez de IAM, el aprovisionamiento de CSI ni la recuperación de datos en el clúster de destino.

**Prueba de aprovisionamiento aislada**

Para probar una ruta de EC2 Linux revisada, guarda el ayudante completo `eks-upgrade-smoke.py` de [Actualizaciones de EKS](../../eks/08-eks-upgrades.md) y usa un contexto/clase de prueba seleccionados explícitamente:

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

Crea un namespace único y un escritor de PVC antes de esperar al enlace retrasado; después lee el marcador con un consumidor independiente. Registra la evidencia y conserva los fallos. Si ejecutas realmente la prueba, ten en cuenta los costos reales de almacenamiento y la limpieza de los recursos Retain. En esta auditoría no se ejecutó ningún aprovisionamiento en la nube, creación de volúmenes, montaje ni benchmark; no uses el antiguo Job de AWS CLI que creaba un volumen facturable no relacionado como diagnóstico de un PVC.

Fuentes: [StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/), [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [Clases de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html).

</details>

### 6. ¿Cuál es la investigación más eficaz cuando el escalado automático no se comporta como se esperaba?

- A. Asignar más recursos a todos los Pods
- B. Añadir nodos manualmente y dejar de investigar
- C. Identificar quién administra las réplicas/recursos/nodos e inspeccionar sus métricas, condiciones, límites, identidad y eventos
- D. Volver a crear el clúster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Identificar quién administra las réplicas/recursos/nodos e inspeccionar sus métricas, condiciones, límites, identidad y eventos**

Separa el escalado de réplicas de HPA, las recomendaciones/actualizaciones de recursos de VPA y el aprovisionamiento de nodos de CA/Karpenter/Auto Mode. Cada uno administra recursos distintos y depende de señales diferentes; no es necesario que estén todos instalados.

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

Comprueba las condiciones de HPA, las métricas actuales, las solicitudes, los límites mínimo/máximo y el comportamiento. La discrepancia entre réplicas deseadas y actuales puede corresponder a una convergencia normal. La falta de datos de métricas o los errores pueden impedir la reducción del escalado. Las métricas de recursos de CPU/memoria usan Metrics Server; las métricas personalizadas/externas necesitan su propio adaptador/integración. Una consulta fallida no demuestra que falte una API/CRD.

Para un grupo de nodos administrado existente, inspecciona su ASG real en lugar de buscar en todos los grupos de la cuenta con etiquetas supuestas:

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

CA responde a Pods no programables y a sus restricciones, no simplemente a un promedio alto de uso de CPU de los nodos. Comprueba la versión minor de Kubernetes compatible, la identidad exacta del Pod, los permisos de detección/escalado con privilegios mínimos, las etiquetas del ASG, el tamaño máximo, las cuotas de EC2/IP y los fallos de lanzamiento. Las etiquetas del grupo de nodos por sí solas no demuestran que existan las etiquetas de detección del ASG. Da preferencia al propietario de EKS/infraestructura para los límites de grupos administrados; modificar directamente el ASG puede generar divergencias y los cambios de configuración de escalado no respetan los PDB.

Para Karpenter/Auto Mode, inspecciona los límites y eventos del NodePool/NodeClaim/proveedor pertinentes. No recomiendes instalar CA solo porque una etiqueta fija de Pod de CA no devuelve objetos. En VPA, Off e Initial pueden ser intencionales. Auto está obsoleto en favor de Recreate; los cambios de modo pueden interrumpir las cargas de trabajo e interactuar con HPA si usan la misma señal de CPU/memoria.

**Ejemplo de configuración de Helm/Terraform**

Úsalo únicamente para instalaciones existentes de CA y Metrics Server administradas por Helm. Proporciona versiones del chart revisadas y una versión de imagen de CA compatible con la versión minor del clúster; la imagen predeterminada de un chart puede ir a la zaga del destino. Mantén un solo propietario por componente.

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

Usa documentos de valores compatibles con Helm provider 3.x, no la forma eliminada de bloques `set {}` repetidos. El nombre del ServiceAccount de CA es explícito y debe coincidir con el asunto de confianza de IRSA; Pod Identity es una configuración independiente con su propio propietario. El rol sigue necesitando los permisos limitados descritos en la [fuente sobre costos/escalado](../../eks/07-eks-cost-optimization.md); no adjuntes AutoScalingFullAccess como solución genérica.

Combina los valores revisados reales de la instalación de Metrics Server. Los valores predeterminados actuales del chart upstream utilizan la ruta segura de conexión a kubelet y no implican `--kubelet-insecure-tls`. Diagnostica los problemas de certificados/confianza/direcciones antes de elegir una alternativa solo para laboratorio. No crees un release de Helm duplicado donde un add-on de EKS sea el propietario del componente. La compatibilidad entre chart/identidad/red/runtime debe probarse en el entorno de destino; aquí no se ejecutó ninguna instalación de Helm.

**Métricas y comportamiento de HPA**

Este ejemplo de métricas de recursos conserva los conceptos de políticas de CPU/memoria y escalado:

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

Debe haber solicitudes definidas para los objetivos de utilización. HPA elige la recomendación de número de réplicas más alta entre las métricas, mientras que las métricas ausentes/con errores pueden inhibir una reducción del escalado. La política Max/Min selecciona la tasa de cambio permitida; la estabilización no es un «periodo de espera» fijo y universal. Los porcentajes, límites y ventanas son ilustrativos, y el comportamiento del escalado por memoria puede no seguir el del escalado por CPU. Evita que Terraform/GitOps y otros autoscalers compitan por el mismo número de réplicas.

**Ejemplo de panel**

Para una disposición existente de kube-prometheus-stack de un solo clúster, con el UID de origen de datos `prometheus` y un sidecar que observa la etiqueta `grafana_dashboard=1` en `monitoring`:

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

Adapta los selectores/UID/namespace a la instalación. Las series de HPA conservan la identidad del namespace; las muestras duplicadas del exportador se reducen antes de agregarlas. La CPU es uso en núcleos y la memoria es el conjunto de trabajo en bytes, no porcentajes. Para fuentes con varios clústeres, añade una dimensión/filtro de clúster. Los sondeos ausentes deben seguir apareciendo como datos ausentes/desconocidos, no como un cero saludable. El panel no demuestra el éxito del escalado ni constituye una canalización de alertas/automatización.

A/B pueden cambiar temporalmente la capacidad, pero no identifican fallos del controlador/métricas. D añade riesgo de migración sin diagnosticarlos. Registra el comportamiento esperado frente al observado y el cambio preciso que lo restableció.

Fuentes: [Comportamiento de HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/), [Cluster Autoscaler para AWS](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md), [Chart de CA](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler), [Metrics Server](https://github.com/kubernetes-sigs/metrics-server), [VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler).

</details>

### 7. ¿Cuál es la investigación más eficaz cuando las políticas de red se comportan de manera inesperada?

- A. Eliminar todas las políticas de red
- B. Inspeccionar la implementación real de la aplicación, los selectores/semántica de las políticas, los registros y el flujo que falla
- C. Configurar hostNetwork en todos los Pods
- D. Reconstruir la VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Inspeccionar la implementación real de la aplicación, los selectores/semántica de las políticas, los registros y el flujo que falla**

Comprueba tanto la política declarada como la implementación que la aplica. Crear un objeto NetworkPolicy no instala por sí solo un motor de aplicación.

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

Una lista vacía de Pods sigue produciendo un código de salida correcto de kubectl. No uses `if kubectl get pods -l ...` como prueba de que VPC CNI, Calico o Cilium están instalados. Inspecciona el propietario configurado, los objetos/imágenes reales, el estado del agente de políticas y los cómputos/kernel/versiones compatibles. Auto Mode usa controles de red integrados de NodeClass y no acepta instalaciones arbitrarias de CNI alternativas.

VPC CNI admite políticas nativas. La guía actual de AWS distingue el modo de inicio estándar (permiso inicial mientras se configuran las reglas de un Pod nuevo) del modo estricto (denegación inicial; requiere las rutas de DNS/dependencias necesarias). Inspecciona el contenedor real del agente de políticas y el registro de eventos habilitado; no des por sentado que se aplica la antigua indicación «VPC CNI no admite políticas».

Para la **NetworkPolicy estándar `networking.k8s.io/v1`**, el tráfico permitido por las políticas es aditivo, sin prioridad de reglas ni resolución de conflictos de «gana la última». Tanto el egreso de un origen aislado como el ingreso del destino deben permitir una conexión. Las API de políticas administrativas, de clúster o de proveedores tienen semánticas distintas y deben considerarse por separado. El comportamiento de HostNetwork también depende de la implementación; configurarlo en todos los Pods no es una solución segura.

**Ejemplo de política acotada**

Los dos documentos siguientes usan `---` entre objetos. Se supone que ya existen un namespace backend, Pods web frontend, Pods de base de datos y puntos de conexión de Pods CoreDNS tradicionales:

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

Los selectores de namespace y Pod están en el **mismo par**, por lo que ambos deben coincidir. Los pares separados funcionarían como OR. Los nombres de namespace usan la etiqueta estándar kubernetes.io/metadata.name; no des por sentado que existe una etiqueta personalizada `name`.

La denegación predeterminada selecciona todos los Pods del backend; solo los Pods API seleccionados reciben las excepciones mostradas. Otras cargas de trabajo del backend y otras dependencias de la API necesitan sus propias reglas revisadas. Esto no configura el egreso del frontend ni el ingreso de la base de datos. La regla DNS apunta a Pods CoreDNS, no a una ruta universal de resolución de Auto Mode/NodeLocal.

Prueba una ruta permitida frontend-web→API:8080, rutas denegadas con namespace/etiqueta/puerto incorrectos, API→base de datos:5432 y la ruta DNS real usando cargas de trabajo de prueba adecuadas administradas por sus propietarios. Un Pod de depuración recién creado y sin etiquetas puede tener una política distinta a la del Pod afectado; hacer ping por sí solo no demuestra la política TCP/UDP. Limita cualquier captura autorizada al namespace/flujo de red previsto y al tiempo necesario; un Pod tcpdump separado no puede observar todos los demás Pods.

**Alternativa de Terraform**

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

Usa un solo propietario y revisa/aplica la matriz completa de flujos en un entorno aislado. Se comprobaron los campos actuales del proveedor de Kubernetes, pero durante esta auditoría no se aplicó ninguna política ni se probó la aplicación del tráfico. Instalar una versión de Calico/Cilium sin fijar o cambiar solo la imagen de aws-node no es una reparación general de políticas; sigue el procedimiento de actualización/migración compatible con la implementación actual.

**El inventario no constituye evidencia de aplicación**

El ejemplo original de `kube_networkpolicy_info`/`calico_denied_packets` no demostraba que esas métricas existieran con las etiquetas supuestas. La documentación actual de kube-state-metrics describe indicadores experimentales de creación/reglas de ingreso/reglas de egreso. Con una configuración de sondeo existente de un solo clúster y un sidecar de Grafana, este ConfigMap muestra el inventario declarado:

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

Verifica que estas métricas experimentales estén expuestas y adapta los selectores de job/UID/namespace. Cero reglas puede representar denegación de todo, y el número de políticas/reglas no mide las conexiones descartadas ni demuestra que se apliquen las políticas. La falta de telemetría sigue siendo desconocida, no un cero saludable. Para obtener evidencia de denegación/permiso, usa los registros de decisiones/la observabilidad de flujos habilitados en la implementación real y valida el esquema/las etiquetas publicados; no inventes un contador ni trates todo registro que contenga «policy» como una denegación.

Eliminar políticas, cambiar hostNetwork de todas las cargas de trabajo o reconstruir la VPC puede ampliar la exposición sin encontrar la causa. Conserva la evidencia del flujo fallido y cambia solo el problema verificado de política/configuración.

Fuentes: [NetworkPolicy de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Políticas de VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [Redes de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [Métricas de políticas de kube-state-metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/policy/networkpolicy-metrics.md).

</details>

### 8. ¿Cuál es el enfoque más eficaz ante un problema de despliegue de Helm?

- A. Eliminar todos los releases de Helm
- B. Volver a crear el clúster de EKS
- C. Inspeccionar la configuración del cliente/chart/dependencias, la propiedad del release, los permisos, los eventos y el comportamiento de la carga de trabajo
- D. Sustituir toda la administración de releases por objetos manuales

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Inspeccionar la configuración del cliente/chart/dependencias, la propiedad del release, los permisos, los eventos y el comportamiento de la carga de trabajo**

Separa los errores del cliente/chart, los permisos/admisión de Kubernetes, la disponibilidad de las cargas de trabajo y el comportamiento de la aplicación. Tiller de Helm 2 pertenece a los debates históricos sobre migraciones; las operaciones actuales con Helm 3/4 no requieren un despliegue de Tiller.

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

Los fallos de consulta pueden deberse a problemas de permisos/red/contexto; no demuestran que el release no exista. Los valores y manifiestos renderizados pueden contener credenciales o datos de Secret; protégelos y oculta los datos sensibles antes de compartirlos. Las etiquetas como app.kubernetes.io/instance son convenciones, no un inventario completo de propiedad. Usa el manifiesto del release para identificar los recursos exactos e inspecciona sus condiciones/eventos.

La identidad de Kubernetes del cliente de Helm es distinta del ServiceAccount de la carga de trabajo seleccionado en los valores del chart. Actualmente no existe la opción `helm install --service-account`. Usa los valores documentados del chart para el ServiceAccount e inspecciona el RBAC del actor específico. La suplantación de identidad requiere permiso y no reproduce todas las concesiones de políticas de acceso de EKS.

**Validar la configuración antes de un cambio**

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

Renderizar/validar no demuestra la compatibilidad del servidor con API/admisión, la existencia de una CRD instalada, el funcionamiento de una imagen, la disponibilidad ni el éxito de las pruebas de la aplicación. `--debug` en una instalación sigue instalando. `helm dependency update` puede cambiar el bloqueo/la selección de dependencias; para mayor reproducibilidad, usa un `Chart.lock` revisado y `dependency build`. Sin un bloqueo, la compilación puede resolver dependencias, así que no la describas como una verificación bloqueada.

Para conflictos de recursos, identifica al propietario existente y la migración prevista. No desinstales automáticamente un release, elimines recursos residuales, uses force/adoptes propiedad ni elijas otro nombre de release. Esas acciones pueden afectar los datos y crear controladores duplicados. Conserva los valores actuales, el esquema/las CRD y las dependencias con estado antes de una actualización bajo propiedad.

**Semántica del proveedor Helm de Terraform**

Este ejemplo apunta al esquema del proveedor Helm 3.3 comprobado localmente y a un namespace/propietario de release preparado y existente. Usa un kubeconfig con un flujo de credenciales exec revisado, en lugar de un token de corta duración capturado una sola vez para una operación apply prolongada:

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

`lint` es un campo **válido** del release y ejecuta Helm lint durante la planificación. `debug` pertenece al proveedor, no a helm_release. El proveedor 3.x usa atributos de valores anidados como `set = [...]`; la forma de archivo de valores anterior evita los bloques set heredados y repetidos.

`verify` comprueba la procedencia del paquete del chart con un anillo de claves de confianza; **no** ejecuta los hooks de prueba de Helm. Habilítalo solo con la configuración real de procedencia/confianza del artefacto y verifica el método de distribución pertinente. `wait_for_jobs` y `wait` esperan la disponibilidad/los Jobs, no ejecutan todas las pruebas de la aplicación. `atomic` proporciona la limpieza de Helm tras un fallo de instalación y el comportamiento de reversión de una actualización, pero no restaura datos de base de datos/PVC ni revierte automáticamente todos los efectos secundarios de hooks/CRD/externos.

`set_sensitive` oculta los valores al mostrarlos, pero no hace seguros para publicar los valores almacenados en el estado normal o en el release. Es mejor usar referencias a secretos administrados por separado y proteger el estado de Terraform y el almacenamiento de releases de Helm. En esta revisión no se ejecutó ningún `apply` del proveedor ni se instaló ningún release.

**Hooks de prueba del chart**

El chart debe definir `my-chart.fullname`, usar ese nombre de Service y exponer las rutas HTTP configuradas. Estos son dos archivos de plantilla **separados**, con un fragmento de valores:

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

Las etiquetas de prueba deliberadamente no copian las etiquetas de selección de la aplicación. Las sondas escriben las respuestas en stdout, no usan un token de la API de Kubernetes y tienen límites de duración de solicitud/Pod. before-hook-creation permite repetir las pruebas conservando los resultados en los registros hasta la siguiente ejecución/limpieza de recursos propios. Estas comprobaciones HTTP no validan todo el comportamiento empresarial; `/api/health` debe existir realmente.

Para un clúster de prueba aislado y preparado, especifica los nombres de release/namespace:

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

Si falla, conserva los recursos e inspecciona los registros de hooks/cargas de trabajo. Registra el UID del namespace y verifícalo antes de limpiar ese namespace de prueba; no elimines un namespace preexistente. El antiguo null_resource sin desencadenadores de cambios no garantizaba una nueva validación después de cada cambio del release.

**Ejemplo de CI estática**

Este flujo de trabajo comprueba un chart con dependencias/Chart.lock confirmados y un `ci/values.yaml` sin secretos. Ajusta la ruta del chart y la versión objetivo de capacidades. Para un chart sin dependencias, omite los pasos de bloqueo/compilación. No crea un clúster ni afirma que se hayan superado pruebas en tiempo de ejecución:

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

Los pins de la acción de configuración y del release se verificaron con sus metadatos oficiales. Cuando sea necesario, ejecuta la fase de integración/hooks de prueba por separado en un entorno desechable propio. Si usas chart-testing, utiliza las opciones de prueba y el release/namespace que informa; los nombres de los directorios de charts no determinan el bucle posterior de `helm test`.

Eliminar todos los charts, volver a crear EKS o abandonar el administrador de releases no diagnostica el problema original de chart/permisos/runtime.

Fuentes: [Depuración de Helm](https://helm.sh/docs/chart_template_guide/debugging/), [Pruebas de charts](https://helm.sh/docs/topics/chart_tests/), [Release del proveedor Helm](https://registry.terraform.io/providers/hashicorp/helm/latest/docs/resources/release), [Release de setup-helm](https://github.com/Azure/setup-helm/releases/tag/v5.0.1), [Helm 3.21.3](https://github.com/helm/helm/releases/tag/v3.21.3).

</details>

### 9. ¿Qué enfoque permite distinguir una fuga de memoria de otras causas de presión de memoria?

- A. Reiniciar todos los Pods
- B. Aumentar únicamente el tamaño de los nodos
- C. Correlacionar la evidencia de memoria/procesos, los límites, los perfiles del runtime y el código de la aplicación
- D. Añadir únicamente nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Correlacionar la evidencia de memoria/procesos, los límites, los perfiles del runtime y el código de la aplicación**

Un conjunto de trabajo creciente, un contenedor OOMKilled o un nodo con MemoryPressure no bastan, por sí solos, para diagnosticar una fuga de memoria. Compara la carga, el tiempo de vida/UID del proceso, el heap/la memoria nativa, las cachés y los límites antes de elegir una corrección.

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

Son diez observaciones con esperas de 30 segundos entre ellas, aproximadamente el plan de muestreo original de cinco minutos más el tiempo de ejecución de los comandos. No se ejecutó durante la auditoría. Un intervalo breve no puede demostrar una fuga de larga duración. Un error en la consulta detiene la recopilación y deja evidencia parcial; no conviertas la falta de métricas en un uso cero.

Usa etiquetas explícitas en lugar de tratar un prefijo del nombre del Pod como valor de etiqueta, y usa la salida de kubectl que reconoce las unidades en lugar de ordenar una cuarta columna inexistente. Las instantáneas del Pod registran el UID y los estados de los contenedores normales/de inicialización; los nombres pueden reutilizarse después de reemplazar un Pod. Las solicitudes de métricas y estado no constituyen una instantánea atómica. Inspecciona los motivos de terminación actuales/anteriores y los recuentos de reinicios, teniendo en cuenta que el estado conserva un historial limitado.

**Interpretar la presión de memoria**

- El conjunto de trabajo, RSS, heap administrado y asignaciones nativas son medidas distintas. El crecimiento de una caché o un aumento del tráfico puede parecer una fuga.
- Un contenedor puede alcanzar su límite cgroup cuando el nodo todavía dispone de memoria libre. Por sí sola, una gran diferencia entre la solicitud y el límite no causa un OOM.
- kubelet es un proceso del nodo, no un `kubelet-pod` genérico cuyos registros puedan leerse desde kube-system. Usa la ruta de nodo/supervisión compatible.
- La fragmentación es una hipótesis que requiere evidencia; reiniciar periódicamente el nodo o forzar la recolección de basura no son soluciones universales.

**Ejemplo actual de métricas y unidades**

Para una disposición existente de kube-prometheus-stack de un solo clúster, estas reglas usan las métricas actuales de límites por contenedor, reducen las muestras duplicadas del exportador y filtran los límites ausentes/cero:

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

Adapta los selectores de namespace/release/job a la instalación real. Estas reglas usan límites normales por contenedor; inspecciona por separado los presupuestos de los contenedores de inicialización y del Pod. Los contenedores sin un límite positivo informado no producen esta relación; supervisa esa cobertura por separado en lugar de considerarlos saludables. Los umbrales de conjunto de trabajo/límite son observaciones ilustrativas, no un detector de fugas del heap.

`deriv` devuelve **bytes por segundo** en este caso. Dividir `5 * 1024 * 1024` entre 60 establece el umbral en **5 MiB/min**. La expresión antigua comparaba con 5 MiB/s aunque el texto indicaba por minuto. Una regresión de 30 minutos junto con una retención de `for: 30m` no demuestra un crecimiento monótono en cada instante. La interpretación depende de los sondeos ausentes, los reinicios y los cambios de carga de trabajo.

**Requisitos previos para el perfilado del runtime**

| Runtime | Alcance correcto de la investigación |
| --- | --- |
| JVM | Usa herramientas/permisos de JDK coincidentes con el PID de la JVM previsto; `jcmd PID GC.heap_info` es un comando de inspección compatible. Los informes de memoria nativa requieren un seguimiento habilitado al inicio. Los volcados del heap pueden pausar el proceso y contener secretos |
| Node.js | Usa el mecanismo de inspección/perfilado compatible con el proceso objetivo; iniciar `node --inspect` lanza un proceso nuevo. Restringe el acceso al depurador |
| Python | Configura el perfilado/tracemalloc en la aplicación real o en una reproducción controlada. Un intérprete independiente no inspecciona las asignaciones de un proceso existente, y el seguimiento de asignaciones de Python no cubre todo el RSS nativo |
| Go | Recopila un perfil real y protegido del heap y usa información coincidente del binario/símbolos con pprof. No des por hecho que hay un punto de conexión de perfilado sin autenticar ni un `/tmp/profile` preexistente |

Verifica las versiones de las herramientas/runtime y la sobrecarga de captura antes de usarlas en producción. No instales paquetes de perfilado arbitrarios en una aplicación en ejecución como paso predeterminado. Aquí no se ejecutó ninguna JVM, perfilador, volcado del heap ni experimento de memoria activo.

**Ejemplo de configuración de la aplicación**

Los valores originales de heap 256m/768m y de contenedor 1Gi se conservan como ilustración, no como óptimo medido. OpenJDK 21 lee JAVA_TOOL_OPTIONS; JAVA_OPTS solo funciona si el entrypoint de la imagen lo reenvía. Los indicadores de línea de comandos o _JAVA_OPTIONS pueden reemplazar estos ajustes, así que verifica las opciones efectivas de la JVM. Estas opciones pueden imprimirse al inicio de la JVM, por lo que no incluyas secretos en ellas.

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

Conserva la imagen real de la aplicación, el comportamiento de inicio y las demás variables de entorno/volúmenes/contexto de seguridad. Verifica que el UID de la aplicación pueda escribir en el volumen de diagnóstico. `MaxGCPauseMillis` es un objetivo flexible. El tamaño del heap es solo una parte de la memoria del proceso: deja margen medido para asignaciones nativas, hilos, código/metaspace y otra sobrecarga.

El emptyDir respaldado por disco tiene límites, pero no es duradero tras eliminar el Pod. Recopila/protege los artefactos deliberadamente y ten en cuenta las colisiones de nombres de archivos cuando se reutilicen los PID de los contenedores. SIGKILL del kernel/cgroup puede impedir por completo la gestión de volcados del heap de la JVM. `ExitOnOutOfMemoryError` gestiona un OOM lanzado por la JVM; no garantiza un volcado ni resuelve la causa de las asignaciones.

Las variables MEMORY_MONITOR_* anteriores no son funciones propias de JVM/Kubernetes. Las rutas de disponibilidad/preparación de Spring Actuator solo se aplican cuando la aplicación realmente las habilita y expone; utiliza su contrato de estado real en lugar de suponer que esas URL funcionan.

**Administrar la supervisión existente**

```hcl
# Prometheus Operator CRD must already exist before planning this resource.
# Save the reviewed PrometheusRule YAML above as the supplied file.
resource "kubernetes_manifest" "memory_alerts" {
  manifest = yamldecode(file(var.memory_rules_file))
}
```

El proveedor de manifiestos de Kubernetes necesita la CRD PrometheusRule durante la planificación; usar `depends_on` para una instalación de Helm en el mismo apply no es una solución general al descubrimiento de esquemas. Reutiliza la pila de supervisión existente y los paneles de conjunto de trabajo de la pregunta 6; no instales otra pila ni hagas referencia a un archivo de panel sin explicar. Confirma la selección de reglas, el enrutamiento de alertas y el estado de la telemetría en el entorno real.

A/B/D pueden mitigar temporalmente la capacidad, pero no demuestran ni corrigen el defecto de asignación. Registra la causa demostrada y valida la corrección real de código/configuración con una carga representativa.

Fuentes: [deriv de Prometheus](https://prometheus.io/docs/prometheus/latest/querying/functions/#deriv), [Métricas actuales de Pods](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md), [Procesamiento de opciones de OpenJDK 21](https://github.com/openjdk/jdk21u/blob/master/src/hotspot/share/runtime/arguments.cpp), [Opciones de Java 21](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html), [jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html).

</details>

### 10. ¿Cuál es la investigación más eficaz ante fallos de resolución DNS en EKS?

- A. Asignar IP estáticas a todos los Pods
- B. Seguir el resolver real del Pod, la implementación DNS, la política/el transporte y la configuración ascendente
- C. Usar ExternalName para todos los Services
- D. Reconstruir la VPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Seguir el resolver real del Pod, la implementación DNS, la política/el transporte y la configuración ascendente**

Empieza por el resolver del Pod afectado y el nombre que falla. Distingue entre herramientas ausentes, respuestas DNS, transporte UDP/TCP, configuración de zonas privadas/ascendentes y caché de la aplicación.

**Inspeccionar la ruta real del Pod**

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

Una imagen sin cat/nslookup tiene una limitación de herramientas, no un fallo DNS. Usa un método de diagnóstico preparado que conserve el contexto pertinente de red/identidad del Pod. Un Pod de depuración nuevo puede tener etiquetas, políticas y DNS distintos. Para probar el transporte del resolver, usa la IP real del servidor de nombres en lugar de depender de DNS para resolver el propio nombre del Service del servidor DNS. Comprueba UDP y TCP 53 según corresponda; una comprobación de conexión solo TCP no valida las respuestas DNS.

Para CoreDNS tradicional, inspecciona la disponibilidad del Deployment, el Service/EndpointSlices, la configuración y los registros:

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

**En los nodos de Auto Mode, CoreDNS se ejecuta como un servicio del sistema del nodo.** Auto Mode puro no necesita tener el Deployment tradicional; los clústeres mixtos deben conservarlo para los nodos que no son de Auto Mode. No diagnostiques la ausencia del Deployment como un fallo en todos los clústeres ni instales un segundo servicio DNS local al nodo en Auto Mode.

**Configuración del resolver y políticas**

ClusterFirst es la ruta normal de un Pod cuando se pretende usar el DNS del clúster. Un Pod configurado intencionadamente con hostNetwork suele necesitar ClusterFirstWithHostNet para ese fin. Configurar hostNetwork solo para solucionar DNS cambia el aislamiento y no es una solución general. DNSPolicy None requiere una configuración completa y deliberada del resolver.

La antigua dirección `169.254.20.10` es una dirección elegida para NodeLocal DNSCache, no un resolver VPC universal. Un resolver público como `8.8.8.8` no sirve las zonas de Service de Kubernetes ni los nombres privados de AWS, y una lista de servidores de nombres no garantiza una alternativa con reconocimiento de zonas. Inspecciona el upstream y el dominio del clúster reales de CoreDNS/NodeLocal en lugar de codificar `172.20.0.10` o una alternativa pública.

Para Pods CoreDNS estándar, el siguiente ejemplo permite DNS solo hacia el backend seleccionado. Revisa todo el resto del egreso de la aplicación antes de aplicarlo:

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

Puede ser necesario permitir tanto el egreso de origen como el ingreso de destino. Los selectores de namespace y Pod se combinan con AND dentro de un solo par. Las rutas de Auto Mode/NodeLocal requieren un tratamiento específico de su implementación; no des por sentado que la selección por etiquetas de Pod apunta a una caché del host. Un Pod tcpdump separado no captura las consultas de otra carga de trabajo; usa una captura autorizada y acotada en el contexto pertinente.

**Leer correctamente la configuración DNS de la VPC**

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

Los atributos DNS se obtienen de DescribeVpcAttribute, no de campos de DescribeVpcs. El nombre del clúster y la Región son explícitos; no es seguro dividir en partes alias arbitrarios de kubeconfig para obtener el nombre del clúster. Verifica la cuenta/contexto antes de estas consultas. Revisa las opciones DHCP, el enrutamiento/reenvío DNS y las zonas privadas antes de cambiar ajustes compartidos de la VPC; crear y asociar un nuevo conjunto de opciones DHCP no es una solución genérica.

**Configuración y propiedad de CoreDNS**

Para un add-on CoreDNS de EKS administrado instalado, inspecciona la versión/configuración y el esquema del candidato revisado:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name coredns --output json
: "${COREDNS_ADDON_VERSION:?Select a reviewed compatible candidate}"
aws eks describe-addon-configuration --addon-name coredns \
  --addon-version "$COREDNS_ADDON_VERSION" --region "$AWS_REGION" --output json
```

Conserva las zonas/reenviadores personalizados y adapta los plugins de health/ready a las sondas reales. El número de réplicas, CPU/memoria, PDB, ubicación y escalado automático requieren una revisión específica de la carga de trabajo; el antiguo ejemplo de 3 réplicas/70Mi/170Mi no era una configuración optimizada universal. No reemplaces el Deployment del propietario con una imagen EKS-Distro 1.8.7 antigua ni apliques un Corefile genérico completo sobre personalizaciones locales.

Un propietario de Terraform puede administrar el add-on existente e inspeccionar la VPC existente:

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

El archivo de configuración completo debe validarse con el esquema del add-on seleccionado y los ajustes actuales. PRESERVE no garantiza una combinación completa de una carga útil explícita. Sigue el procedimiento exacto de actualización de [Actualizaciones de EKS](../../eks/08-eks-upgrades.md) y verifica el comportamiento DNS real después. Este ejemplo no configura el DNS de nodo de Auto Mode ni autoriza reemplazar una VPC compartida.

**NodeLocal DNSCache opcional para una configuración de nodos estándar compatible**

Usa la [guía oficial de instalación](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) y un manifiesto publicado y revisado. El antiguo DaemonSet escrito a mano estaba incompleto; cambiar solo su imagen no proporciona todas las interfaces, reglas de filtrado, montajes, Service ascendente ni integración con kubelet.

| Decisión | Preparación requerida |
| --- | --- |
| Dirección local | Elige una IP local del nodo sin conflictos y el dominio real del clúster/IP del Service CoreDNS; ten en cuenta la sintaxis de dirección/puerto IPv6 |
| Plano de datos existente | En la ruta iptables documentada, la caché escucha en la IP local y en la IP del Service CoreDNS. En una configuración IPVS compatible, solo escucha localmente y deben cambiar los ajustes de DNS del clúster de kubelet. Otros modos necesitan las instrucciones de integración actuales que correspondan |
| Manifiesto/configuración | Renderiza los marcadores de posición documentados y conserva los privilegios/interfaces/filtros/montajes de bloqueo, sondas y configuración ascendente requeridos. No sustituyas el DaemonSet por una versión antigua parcial |
| Migración de cargas de trabajo | Asegúrate de que los ajustes de nodo/kubelet y el comportamiento del resolver de los Pods nuevos/existentes coincidan; planifica un despliegue gradual y la reversión tanto de los cambios de caché como de kubelet |
| Memoria/operaciones | Dimensiona según las observaciones de consultas/caché/concurrencia, supervisa los fallos y mantén DNS durante el reinicio/despliegue |

NodeLocal DNSCache reenvía las consultas que no están en la caché al upstream correspondiente; no convierte cada consulta en un acierto de caché local. La guía oficial señala que la terminación por OOM puede dejar reglas de filtrado de paquetes que apunten a la caché local no disponible hasta que se reinicie, lo que provoca una interrupción de DNS. Una solicitud de memoria diminuta y fija o añadir una caché no garantizan automáticamente un mejor rendimiento.

Durante esta revisión no se ejecutó ninguna consulta DNS, captura de paquetes, actualización de CoreDNS, instalación de NodeLocal ni `apply` de Terraform. Valida la topología y los supuestos elegidos en un entorno controlado.

Las IP estáticas para Pods, ExternalName para todos los Services o reconstruir la VPC no identifican la ruta del resolver que falla. Registra la consulta/respuesta real, el contexto de origen, el cambio de configuración y la evidencia de resolución.

Fuentes: [CoreDNS de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html), [DNS de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [DNS de Pod](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [DNS de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html), [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/).

</details>
