# Cuestionario de creación de clústeres de EKS - Parte 4

> **Última actualización**: October 12, 2026

Este cuestionario conecta la guía de clústeres con Terraform con las operaciones de escalado, identidades y ciclo de vida. La sección final verifica conceptos específicos de Terraform. Los ejemplos requieren una cuenta/Region/kubeconfig, IAM y prerrequisitos de red revisados; no se implementaron durante esta auditoría.

## Preguntas de conceptos básicos

1. ¿Cuál es la principal diferencia de aprovisionamiento entre Cluster Autoscaler y Karpenter?
   * A) CA es un servicio administrado de AWS
   * B) CA escala grupos existentes; Karpenter aprovisiona capacidad individual seleccionada
   * C) CA mide solo CPU y Karpenter solo el recuento de Pods
   * D) Karpenter reemplaza al programador de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CA escala grupos existentes; Karpenter aprovisiona capacidad individual seleccionada**

Cluster Autoscaler ajusta el tamaño de los grupos de nodos/ASG predefinidos y detectados. Karpenter crea NodeClaims y capacidad de EC2 seleccionada mediante NodePools y EC2NodeClasses. Kubernetes programa Pods; Karpenter no reemplaza al programador de Kubernetes.

Ambos consideran las solicitudes de cargas de trabajo no programables y las restricciones de colocación. Ninguno es simplemente «porcentaje de CPU frente a recuento de Pods», y ninguno redimensiona una instancia de EC2 en ejecución en el mismo lugar. Karpenter puede reemplazar capacidad con instancias de distinto tamaño; VPA administra por separado las solicitudes de recursos de Pods.

**Ejemplo de Cluster Autoscaler:** para EKS 1.36, use una versión secundaria coincidente y una ServiceAccount dedicada con IAM y etiquetas de detección revisados. El chart 9.59.0 necesita la anulación explícita de la imagen v1.36.1. Renderice RBAC, la imagen y los argumentos antes de la instalación:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
Mantenga las protecciones de almacenamiento local y Pods del sistema, salvo que una política de carga de trabajo/datos revisada requiera lo contrario. Los tipos de instancia mixtos en un grupo administrado por CA deben tener formas comparables de CPU/memoria/GPU.

**Ejemplo de Karpenter:** instale un controlador/CRD compatibles y configure por separado su IAM, autorización de nodos, etiquetas de detección, manejo de interrupciones y límites de capacidad. Reemplace ambos marcadores de posición de AMI por imágenes AL2023 revisadas que coincidan con la versión del clúster y con cada arquitectura. Las imágenes de las cargas de trabajo deben admitir ambas arquitecturas si ambas están permitidas:

```yaml
# Karpenter NodePool (karpenter.sh/v1) + EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole-my-cluster
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_REVIEWED_AMD64_IMAGE
    - id: ami-REPLACE_WITH_REVIEWED_ARM64_IMAGE
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
| Comparación | Cluster Autoscaler | Karpenter |
| --- | --- | --- |
| Unidad de escalado | Capacidad de grupo de nodos/ASG existente | NodeClaims y capacidad de EC2 seleccionada |
| Configuración | Grupos, detección, IAM y controlador | NodePools, EC2NodeClasses, IAM y controlador |
| Eliminación | Requiere comprobaciones de programación e interrupción | Sujeta a consolidación, presupuestos y controles de interrupción |
| Afirmación histórica de tiempo en la guía original | 2–10 minutos, sin verificar | Menos de 1 minuto, sin verificar |

Los números de tiempo originales se conservan como **afirmaciones históricas sin verificar**, no como puntos de referencia reproducidos en esta auditoría ni como rendimiento actual garantizado. El arranque de nodos, las imágenes, las cuotas y las restricciones de las cargas de trabajo afectan a ambas herramientas. No infiera de esa tabla una clasificación universal de coste, simplicidad o latencia.

</details>

2. ¿Qué tipos de capacidad están en la API actual de EKS CreateNodegroup?
   * A) Reserved, On-Demand, Spot
   * B) On-Demand, Spot, Dedicated
   * C) ON_DEMAND, SPOT, CAPACITY_BLOCK
   * D) Standard, Burstable, Compute-Optimized

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ON_DEMAND, SPOT, CAPACITY_BLOCK**

La API actual de EKS CreateNodegroup incluye **ON_DEMAND, SPOT y CAPACITY_BLOCK**. Un grupo de nodos administrado usa un tipo de capacidad; use grupos separados para grupos de capacidad distintos.

On-Demand evita la recuperación de Spot, pero no es una garantía de interrupción ni de disponibilidad. Spot usa capacidad sobrante y requiere cargas de trabajo tolerantes a interrupciones; los descuentos anunciados no son ahorros garantizados. Reserved Instances/Savings Plans son acuerdos de facturación, no valores de enumeración adicionales de CreateNodegroup.

Los Capacity Blocks son un flujo de trabajo independiente de reserva limitada en el tiempo para instancias/Regions compatibles. Requieren una plantilla de lanzamiento personalizada dirigida a la reserva, una AZ/subred coincidente y escalado consciente de la reserva. EKS crea una reducción de escala programada 40 minutos antes de que finalice la reserva; no modifique ni elimine esa acción. Los ejemplos siguientes son alternativas convencionales de On-Demand/Spot, no aprovisionamiento de Capacity Block.

**AWS CLI:** use un nombre de grupo de nodos sin utilizar, subredes privadas existentes y un rol de nodo de EC2 aprobado (incluida la ruta de identidad de CNI necesaria). Espere a que el grupo se active y luego verifique la preparación real de Node/carga de trabajo:

```bash
set -euo pipefail
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types t3.medium t3a.medium --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}"
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$NEW_NODEGROUP_NAME"
```
**Alternativa con eksctl:** guarde una configuración para el clúster existente y nombres de grupo sin utilizar, y luego use `eksctl create nodegroup -f nodegroups.yaml`. Use `managedNodeGroups` y `spot`, no los campos `capacityType` no compatibles del ejemplo original:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: ng-on-demand
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 5
  spot: false
- name: ng-spot
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large]
  privateNetworking: true
  desiredCapacity: 2
  minSize: 0
  maxSize: 5
  spot: true
```
Use afinidad/selectores y toleraciones para colocar las cargas de trabajo adecuadas. Los grupos de nodos administrados tienen manejo integrado de reequilibrio/drenaje de Spot; Node Termination Handler no es un requisito adicional universal. Los PDB no pueden impedir que EC2 recupere una instancia de Spot, y no todos los Pods reciben la ventana completa de interrupción. Planifique puntos de control, capacidad de reserva y recuperación ante interrupciones.

</details>

3. ¿Qué campo es obligatorio en cada selector de perfil de Fargate?
   * A) Tipo de instancia
   * B) Namespace; las etiquetas son opcionales
   * C) ID de grupo de seguridad
   * D) Recuento máximo de Pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Namespace; las etiquetas son opcionales**

Cada selector de perfil requiere un **namespace**; las etiquetas son opcionales. Un perfil también necesita un nombre y un rol de ejecución de Pod, y usa subredes privadas aptas. No tiene ningún parámetro de grupo de seguridad. Los grupos de seguridad de Pods son un mecanismo de política compatible independiente, no un campo de perfil de Fargate.

Use un nombre de perfil sin utilizar e ID de subred privada revisados. Este selector se dirige intencionalmente solo a Pods de aplicación, y deja sin cambios la colocación existente de CoreDNS:

```bash
set -euo pipefail
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"fargate-lab","labels":{"app":"nginx"}}]'
aws eks describe-fargate-profile --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --fargate-profile-name "$NEW_FARGATE_PROFILE" \
  --query 'fargateProfile.{status:status,subnets:subnets,selectors:selectors}'
```
Espere a `ACTIVE` antes de iniciar Pods coincidentes. A continuación se muestra una definición de perfil alternativa de eksctl; valide la detección de subred privada y la configuración del rol de ejecución del clúster antes de crearlo:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: fp-application
  selectors:
  - namespace: fargate-lab
    labels:
      app: nginx
```
El namespace y la carga de trabajo etiquetada aún deben crearse por separado. Si coinciden varios perfiles, EKS usa el orden alfanumérico de nombres de perfil, salvo que el Pod seleccione un perfil coincidente con `eks.amazonaws.com/fargate-profile`. Los perfiles son inmutables; reemplazarlos/eliminarlos afecta a sus Pods.

El rol de ejecución de Pod sirve a la infraestructura de Fargate, no al acceso de AWS de la aplicación. Use una identidad de carga de trabajo compatible como IRSA; EKS Pod Identity no es compatible con Fargate. Mover CoreDNS a Fargate requiere su configuración de cómputo y un perfil coincidente, no simplemente añadir `kube-system` a un selector.

Fargate cobra por la **capacidad aprovisionada**, determinada por los recursos solicitados más sobrecarga/redondeo; no factura solo el uso muestreado de CPU/memoria. Inspeccione `CapacityProvisioned`. EKS Fargate no admite Spot, DaemonSets, contenedores privilegiados, redes de host ni volúmenes de carga de trabajo montados en EBS. EFS persistente usa aprovisionamiento estático; la coincidencia de perfil por sí sola no crea un sistema de archivos/PV/PVC. Tenga en cuenta DNS, extracción de imágenes, STS y otras rutas de red necesarias.

</details>

4. ¿Cuál no es un campo de NodegroupUpdateConfig?
   * A) maxUnavailable
   * B) maxUnavailablePercentage
   * C) updateStrategy
   * D) Tiempo de espera de operación de grupo de nodos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Tiempo de espera de operación de grupo de nodos**

`NodegroupUpdateConfig` admite `maxUnavailable` entero, `maxUnavailablePercentage` entero y `updateStrategy` (`DEFAULT` o `MINIMAL`). Establezca el recuento o el porcentaje, no ambos. Un porcentaje no es un valor válido para `maxUnavailable` en sí mismo.

Un tiempo de espera de operación no es un campo de NodegroupUpdateConfig. `--force` pertenece a una solicitud de actualización de versión y puede omitir la protección de expulsión de Pods; no es un ajuste de configuración de actualización almacenado. Un tiempo de espera de CLI/IaC también es distinto de la operación de servicio.

```bash
set -euo pipefail
UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":2,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
Para la configuración porcentual alternativa, use `{"maxUnavailablePercentage":20,"updateStrategy":"DEFAULT"}`. Siga el ID de actualización devuelto hasta `Successful` antes de iniciar una actualización de versión. `DEFAULT` inicia primero capacidad de reemplazo; `MINIMAL` termina primero los nodos antiguos seleccionados para reducir la capacidad extra temporal.

Para un Deployment revisado de tres réplicas en `update-lab`, este PDB restringe la expulsión voluntaria:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
Un PDB no es una garantía general de disponibilidad. Las eliminaciones directas, los fallos y el propio despliegue del controlador de carga de trabajo difieren de la expulsión. Compruebe la capacidad de reserva, la preparación y los volúmenes. No prometa que una actualización de EKS ya en ejecución pueda simplemente pausarse o revertirse; detenga los cambios planificados posteriores y siga el procedimiento de recuperación aplicable.

</details>

5. ¿Qué paso de actualización del plano de control es compatible con el flujo de trabajo normal de versiones de EKS?
   * A) Omitir directamente dos versiones secundarias
   * B) Saltar a cualquier versión upstream
   * C) Pasar a la siguiente versión secundaria compatible con EKS después de comprobaciones de preparación
   * D) Actualizar nodos por encima de la versión del plano de control primero

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Pasar a la siguiente versión secundaria compatible con EKS después de comprobaciones de preparación**

Las actualizaciones del plano de control de EKS proceden **una versión secundaria a la vez**, como 1.34 → 1.35 → 1.36. Confirme que EKS ofrezca cada destino; una versión upstream de Kubernetes no prueba la disponibilidad de EKS. No infiera una política de actualización futura de versiones principales a partir del flujo de trabajo actual de Kubernetes 1.x.

Antes de actualizar el plano de control, lleve los nodos administrados y Fargate a su versión secundaria actual según lo requerido por el procedimiento de EKS; actualice los nodos autoadministrados/híbridos según lo recomendado. Los kubelets nunca deben ser más recientes que el servidor de API. El límite general de desfase para Kubernetes 1.28+ permite kubelets hasta tres versiones secundarias más antiguos, pero eso no es una recomendación para ignorar los prerrequisitos de actualización de EKS.

Primero revise las perspectivas, las API eliminadas, la compatibilidad de complementos, la capacidad y las copias de seguridad de aplicaciones/datos. EKS no proporciona acceso normal de shell de administrador a su etcd administrado para un comando de snapshot hecho por usted mismo; use procedimientos compatibles de copia de seguridad/restauración de clústeres/recursos y datos persistentes. Este comando solo impone el paso de una versión secundaria; no reemplaza esas comprobaciones:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${NEXT_KUBERNETES_VERSION:?Confirm the next supported EKS minor}"
CURRENT_KUBERNETES_VERSION=$(aws eks describe-cluster \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --query cluster.version --output text)
if [[ "$CURRENT_KUBERNETES_VERSION" =~ ^1\.([0-9]+)$ ]]; then
  CURRENT_MINOR="${BASH_REMATCH[1]}"
else
  printf '%s\n' 'Unexpected cluster version; stop and inspect.' >&2
  exit 1
fi
EXPECTED_NEXT_VERSION="1.$((CURRENT_MINOR + 1))"
[ "$NEXT_KUBERNETES_VERSION" = "$EXPECTED_NEXT_VERSION" ] || {
  printf '%s\n' 'Only the next minor version is allowed in this upgrade example.' >&2
  exit 1
}
CLUSTER_UPDATE_ID=$(aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --kubernetes-version "$NEXT_KUBERNETES_VERSION" \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$CLUSTER_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
Espere a que ese ID de actualización tenga éxito, y luego actualice los nodos y los componentes de clúster compatibles en su orden documentado. Haga coincidir la versión secundaria de Cluster Autoscaler con el clúster y kubectl dentro de su desfase compatible.

EKS actual ofrece reversión condicional a la versión secundaria anterior durante siete días después de una actualización in situ completada. No está disponible para un clúster creado en esa versión ni para una actualización automática al final del soporte extendido. Primero prepare nodos/complementos compatibles; Auto Mode administra la reversión de sus nodos. La reversión no retrocede etcd, las cargas de trabajo ni los datos persistentes. Consulte los requisitos oficiales de preparación para la reversión en lugar de tratarla como una deshacer incondicional.

</details>

## Preguntas de respuesta corta

6. ¿Cómo se puede cambiar el tipo de instancia de un grupo de nodos administrado de EKS?

<details>
<summary>Respuesta y explicación</summary>

Depende de dónde esté configurado el tipo de instancia:

* Un tipo establecido en `instanceTypes` del grupo de nodos administrado no es un campo de `UpdateNodegroupConfig`. Cree un grupo de reemplazo, valide la capacidad y migre las cargas de trabajo antes de retirar el antiguo.
* Si el grupo se creó originalmente con **su plantilla de lanzamiento personalizada**, con el tipo de instancia en esa plantilla en lugar de en el campo de grupo de EKS, puede actualizar a una nueva versión de la **misma plantilla**. EKS recicla los nodos. No modifique la plantilla generada por EKS ni suponga que puede cambiar a ID de plantilla arbitrarios.
* Para ASG autoadministrados, una actualización de plantilla de lanzamiento/actualización de instancias también necesita un diseño de drenaje y ciclo de vida consciente de Kubernetes; el reemplazo de EC2 por sí solo no es una migración consciente de PDB.

Revise la arquitectura de AMI, los controladores, los límites de IP de Pod, las etiquetas/toleraciones, la topología de almacenamiento, las cuotas y los PDB. Para recursos propiedad de Terraform, realice el cambio mediante el estado propietario e inspeccione las acciones de reemplazo; no haga un cambio de CLI fuera de banda y suponga que el estado sigue siendo correcto.

</details>

7. ¿Cómo se permite solo el acceso privado al endpoint de la API de Kubernetes?

<details>
<summary>Respuesta y explicación</summary>

Establezca el acceso privado como verdadero y el acceso público como falso. En el módulo v21 son `endpoint_private_access` y `endpoint_public_access`; cámbielos mediante el estado de Terraform propietario cuando corresponda.

Antes de deshabilitar el acceso público, verifique DNS, rutas y reglas de seguridad desde la red conectada del administrador hasta el endpoint privado. Un sistema puede alcanzarlo desde la VPC **u otra red correctamente conectada**; no necesita residir físicamente en la VPC. Esto cambia el endpoint de la API de Kubernetes, no el acceso a la API de servicio AWS EKS independiente.

Para un clúster propiedad de API, la operación de CLI equivalente es:

```bash
set -euo pipefail
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config \
  --region "${EXAMPLE_REGION:?}" --name "${EXAMPLE_CLUSTER:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
aws eks describe-update --region "$EXAMPLE_REGION" --name "$EXAMPLE_CLUSTER" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
Siga ese ID de actualización hasta `Successful` y pruebe el acceso autenticado de kubectl desde la ruta de administración prevista. Una única respuesta `InProgress` no es finalización.

</details>

8. ¿Cuál es el ciclo de vida de soporte de versiones de Kubernetes de EKS?

<details>
<summary>Respuesta y explicación</summary>

Una versión secundaria de EKS recibe **14 meses de soporte estándar**, seguidos de **12 meses de soporte extendido** con un coste adicional por hora de clúster. El reloj comienza en su fecha de lanzamiento de EKS, no en la fecha de lanzamiento upstream.

El 12 de octubre de 2026, EKS enumera 1.34–1.37 en soporte estándar y 1.31–1.33 en soporte extendido. EKS 1.37 estuvo disponible el 1 de octubre de 2026, después de su lanzamiento upstream del 26 de agosto. Consulte el calendario de lanzamientos actual de EKS antes de seleccionar un destino de implementación/actualización.

El soporte extendido está habilitado de forma predeterminada. La política de actualización del clúster determina el comportamiento al final del soporte estándar. Tras finalizar el soporte extendido, EKS actualiza automáticamente el plano de control a la versión extendida compatible más antigua; la versión antigua no se ejecuta indefinidamente sin actualizaciones. Los nodos y complementos administrados/autoadministrados/híbridos requieren sus propias acciones de ciclo de vida, mientras que Auto Mode administra sus capacidades y nodos.

No se base en una regla fija de «cuatro versiones», «aviso de 60 días» o «retraso de lanzamiento de 2–3 meses» del cuestionario anterior. Use las fechas y la política publicadas para el clúster real. Kubernetes upstream tiene su propio calendario de soporte; la antigua comparación de nueve meses no es orientación actual.

</details>

## Preguntas prácticas

9. Diseñe el escalado automático de Pods con objetivos de utilización de CPU de 75 % / memoria de 80 % y un grupo de nodos limitado a 2–10 nodos, inicialmente 3.

<details>
<summary>Respuesta y explicación</summary>

Separe el **escalado de demanda de Pods** del **escalado de capacidad de nodos**. Use objetivos de utilización de recursos de HPA de CPU 75 % y memoria 80 %, con Metrics Server y solicitudes de contenedor válidas. HPA elige la mayor recomendación de réplicas de las métricas, sujeta a tolerancia, límites y estabilización; no es una alarma inmediata de «umbral superado».

Luego use Cluster Autoscaler para un grupo de nodos administrado con min=2, max=10 y deseado inicial=3. Los campos equivalentes de grupo de nodos del módulo de Terraform son `min_size`, `max_size` y `desired_size`; revise la configuración propietaria. Esta alternativa completa de eksctl es para un grupo nuevo en el clúster existente revisado:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: autoscaling-workers
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  minSize: 2
  maxSize: 10
  desiredCapacity: 3
```
Use la configuración dedicada y autorizada de Cluster Autoscaler de la pregunta 1. Los límites por sí solos no ejecutan un escalador automático. CA reacciona a solicitudes de Pod no programables y restricciones de eliminación; no implementa por sí mismo los porcentajes solicitados de CPU/memoria.

En un nuevo namespace `autoscaling-lab`, el siguiente Deployment/HPA demuestra solicitudes y ambas métricas. El rango de réplicas de Pod 2–20 es independiente del rango de nodos 2–10:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: autoscaling-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: my-app}
  template:
    metadata:
      labels: {app: my-app}
    spec:
      automountServiceAccountToken: false
      containers:
      - name: web
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```
Inspeccione las condiciones de HPA, la disponibilidad de métricas, los motivos de Pending y las decisiones del escalador automático bajo una prueba de carga aprobada. El uso de memoria puede no disminuir proporcionalmente al aumentar las réplicas, así que valide esa métrica para la aplicación. Estos valores de solicitud/límite son ejemplos, no dimensionamiento medido.

No añada políticas independientes de seguimiento de destino de CPU/memoria de ASG al mismo bucle de capacidad deseada. Pueden competir con CA y tener distinto comportamiento de drenaje. EC2 no proporciona utilización de memoria normal de forma predeterminada; cualquier diseño independiente sin CA necesita una métrica personalizada publicada correctamente y un namespace personalizado, no una métrica de memoria supuesta de `AWS/EC2`. No se requiere tal política de ASG para esta solución HPA+CA.

</details>

## Preguntas avanzadas

10. Explique una actualización de grupo de nodos blue/green, sus riesgos y un flujo de trabajo de migración con protecciones.

<details>
<summary>Respuesta y explicación</summary>

Cree capacidad de reemplazo, pruébela, migre gradualmente y retire el grupo antiguo solo después de validar la aplicación/los datos. Mantenga la capacidad antigua y el estado compatible mientras siga siendo necesaria la reversión; compartir un clúster no es aislamiento completo ni una garantía de cero tiempo de inactividad.

Revise cuotas, IP de subred, imágenes/arquitectura, etiquetas, toleraciones, sobrecarga de daemon, PDB, datos locales y restricciones de AZ/asociación de volúmenes. La pertenencia a StatefulSet no hace por sí sola que un volumen sea portátil. Investigue los fallos de DNS antes de cambiar TTL o añadir una malla de servicios. Confirme que los recopiladores de monitoreo/registros realmente cubran los nuevos nodos.

El siguiente ejemplo de CLI es para **grupos propiedad de API**, con nombres de grupo green sin utilizar. Para grupos propiedad de Terraform o eksctl/CloudFormation, realice cambios equivalentes mediante ese propietario para evitar desviaciones y stacks huérfanos.

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${OLD_NODEGROUP_NAME:?}" "${GREEN_NODEGROUP_NAME:?}"
[ "$OLD_NODEGROUP_NAME" != "$GREEN_NODEGROUP_NAME" ]
OLD_NODEGROUP_ARN=$(aws eks describe-nodegroup --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$OLD_NODEGROUP_NAME" \
  --query nodegroup.nodegroupArn --output text)
aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME" --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --instance-types t3.large \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}" \
  --labels audit.example.com/pool=green
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME"
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l "eks.amazonaws.com/nodegroup=$GREEN_NODEGROUP_NAME" -o wide
```
Una etiqueta de grupo de nodos no prueba que el ASG subyacente tenga etiquetas de detección de Cluster Autoscaler. Verifique las etiquetas/IAM del ASG real si CA lo administrará. Compruebe la preparación del nuevo Node y una carga de trabajo canary con alcance separado antes de migrar la carga de trabajo principal.

Drene un nodo antiguo confirmado cada vez. Esto omite intencionalmente la eliminación automática de emptyDir y la expulsión forzada:

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
Después de cada paso, verifique la preparación, la salud de la aplicación y los datos persistentes. Deténgase cuando falle el drenaje y resuelva la causa. Una vez validadas todas las cargas de trabajo y cuando el grupo antiguo conservado ya no sea necesario, compare su ARN original antes de esta eliminación final independiente:

```bash
# A separate final step for API-owned groups only.
: "${OLD_NODEGROUP_ARN:?Use the ARN captured before migration}"
if [ "${MIGRATION_VERIFIED:?Set yes only after application/data checks}" = yes ]; then
  CURRENT_OLD_GROUP_ARN=$(aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --nodegroup-name "${OLD_NODEGROUP_NAME:?}" \
    --query nodegroup.nodegroupArn --output text) || exit 1
  [ "$CURRENT_OLD_GROUP_ARN" = "$OLD_NODEGROUP_ARN" ] || {
    printf '%s\n' 'Node-group identity changed; no deletion attempted.' >&2
    exit 1
  }
  aws eks delete-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME" || exit 1
  aws eks wait nodegroup-deleted --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME"
fi
```

</details>


## Comprobaciones de Terraform

11. ¿A qué puede acceder un lector de terraform_remote_state?
   * A) Solo a las salidas declaradas en la capa de almacenamiento
   * B) A la instantánea completa de estado, aunque HCL exponga salidas
   * C) A ningún valor confidencial bajo ninguna condición
   * D) Solo a los recursos de su propio módulo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) A la instantánea completa de estado, aunque HCL exponga salidas**

El acceso al estado es un límite de autorización. Publique por separado los valores seleccionados cuando los consumidores no deban leer la instantánea completa.

</details>

12. ¿Qué nombres de entrada coinciden con el ejemplo del módulo EKS v21?
   * A) cluster_name y cluster_version
   * B) name y kubernetes_version
   * C) clusterId y versionNumber
   * D) cluster_addons y cluster_compute_config

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) name y kubernetes_version**

El módulo v21 cambió el nombre de estas entradas. Los campos de recursos de AWS como aws_eks_addon.cluster_name y las salidas de módulo como cluster_name siguen usando sus propios nombres documentados; no reemplace globalmente cada ocurrencia.

</details>

13. ¿Qué afirmación sobre el ejemplo de backend de S3 es correcta?
   * A) encrypt=true también habilita el bloqueo de estado
   * B) DynamoDB es la única opción de bloqueo
   * C) use_lockfile=true habilita el bloqueo de S3; los clientes y los permisos IAM de archivo de bloqueo deben estar preparados
   * D) Un bloqueo coordina todas las claves de estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) use_lockfile=true habilita el bloqueo de S3; los clientes y los permisos IAM de archivo de bloqueo deben estar preparados**

Use Terraform 1.10+ para archivos de bloqueo de S3. El bloqueo de DynamoDB está en desuso; migre los clientes coordinados en lugar de eliminar la tabla mientras los clientes antiguos todavía dependan de ella.

</details>

14. ¿Un aws_eks_pod_identity_association crea la Kubernetes ServiceAccount?
   * A) Sí, con cluster-admin
   * B) No; el namespace/ServiceAccount y la ruta de agente/SDK compatible son prerrequisitos independientes
   * C) Sí, e instala Metrics Server
   * D) Solo en Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; el namespace/ServiceAccount y la ruta de agente/SDK compatible son prerrequisitos independientes**

La asociación vincula la identidad de AWS a una identidad existente de Kubernetes. Limite la confianza y los permisos, mantenga habilitadas las etiquetas de sesión necesarias, gestione la propagación y verifique el rol asumido real.

</details>

15. ¿Qué permite la restricción de módulo ~> 21.0?
   * A) Solo 21.0.0
   * B) Solo parches en 21.0.x
   * C) Versiones secundarias y de parche compatibles de 21.x inferiores a 22.0, sin garantizar comportamiento
   * D) Toda versión principal futura

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Versiones secundarias y de parche compatibles de 21.x inferiores a 22.0, sin garantizar comportamiento**

~> 21.0.0 restringe el intervalo a 21.0.x. La guía fija explícitamente las versiones de módulo; .terraform.lock.hcl registra las selecciones de proveedor en lugar de las versiones de módulo remotas. Revise los planes guardados antes de aplicar.

</details>

## Referencias

- [API_CreateNodegroup.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)
- [ml-node-groups.html](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-groups.html)
- [fargate-profile.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)
- [fargate-pod-configuration.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-pod-configuration.html)
- [API_NodegroupUpdateConfig.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_NodegroupUpdateConfig.html)
- [launch-templates.html](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)
- [kubernetes-versions.html](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [update-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [rollback-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [cas.html](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [horizontal-pod-autoscale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [s3](https://developer.hashicorp.com/terraform/language/backend/s3)
- [remote-state-data](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
