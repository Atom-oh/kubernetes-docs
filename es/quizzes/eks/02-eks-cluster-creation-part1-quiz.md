# Cuestionario sobre la creación de clústeres de EKS - Parte 1

> **Última actualización**: 12 de octubre de 2026

> Los comandos son ejemplos independientes, no un script que deba ejecutarse de principio a fin. Use una cuenta/clúster de capacitación exclusivo, permisos de IAM revisados y un kubeconfig temporal privado (`EXAMPLE_KUBECONFIG`). Sustituya los ID de ejemplo y las variables obligatorias. Los comandos de creación generan cargos. Esta auditoría verificó las fuentes, la sintaxis y los recursos de prueba locales; no aprovisionó recursos de AWS ni verificó la disponibilidad de las aplicaciones.

Este cuestionario evalúa su comprensión de los conceptos, las herramientas y las prácticas recomendadas relacionadas con la creación de clústeres de Amazon EKS. Abarca temas como los métodos de creación de clústeres, la configuración de VPC y la configuración de grupos de nodos.

## Preguntas sobre conceptos básicos

1. ¿Qué herramienta no tiene un comando integrado que aprovisione directamente un plano de control de EKS?
   * A) Consola de administración de AWS
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) kubectl**

kubectl administra recursos a través de una API de Kubernetes y no tiene un comando nativo para aprovisionar EKS. Un controlador de infraestructura ya instalado, como ACK, puede conciliar un recurso enviado con kubectl en un clúster de EKS; eso es una integración de controlador, no una operación de AWS integrada en kubectl.

Entre las herramientas que se pueden usar para crear clústeres de Amazon EKS se incluyen:

1. **Consola de administración de AWS**:
   * Cree clústeres de EKS a través de una interfaz web.
   * Adecuada para principiantes, ya que permite configurar visualmente los componentes del clúster.
   * Le guía por el proceso de creación del clúster mediante un asistente paso a paso.
2.  **AWS CLI**:

    * Cree clústeres de EKS desde la línea de comandos.
    * Usa el comando `aws eks create-cluster`.
    * Adecuada para scripts y automatización.

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * Herramienta de línea de comandos diseñada específicamente para crear clústeres de EKS.
    * Desarrollada originalmente por Weaveworks; actualmente, el proyecto se mantiene en la organización eksctl-io, con contribuciones de AWS y de la comunidad.
    * Puede crear un clúster con un solo comando.

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Herramientas de infraestructura como código (IaC)**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    Estas herramientas permiten definir y desplegar clústeres de EKS como código.

kubectl se usa para administrar recursos de Kubernetes (Pods, Services, Deployments, etc.) una vez creado el clúster. Para conectarse a un clúster de EKS, configure un kubeconfig autorizado, normalmente con `aws eks update-kubeconfig`.

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

Después, puede usar kubectl para administrar los recursos del clúster.

</details>

2. ¿Qué componente de VPC se debe especificar al crear un clúster de Amazon EKS?
   * A) Solo subredes públicas
   * B) Solo subredes privadas
   * C) Subredes en al menos 2 zonas de disponibilidad
   * D) NAT Gateway

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Subredes en al menos 2 zonas de disponibilidad**

**Explicación:** Al crear un clúster de Amazon EKS, el componente de VPC que se debe especificar son las subredes en al menos 2 zonas de disponibilidad. Este es un requisito de AWS para garantizar la alta disponibilidad de los clústeres de EKS.

**Requisitos de VPC para clústeres de EKS:**

1. **Se requieren subredes en al menos 2 zonas de disponibilidad (AZ)**:
   * Como el plano de control de EKS se despliega en varias zonas de disponibilidad, al crear un clúster se deben especificar subredes en al menos 2 zonas de disponibilidad.
   * Esto favorece la disponibilidad regional del plano de control. La disponibilidad de las cargas de trabajo también requiere planificar la ubicación de las réplicas, la capacidad, el almacenamiento y las dependencias.
2. **Tipos de subredes**:
   * Puede usar solo subredes públicas, solo subredes privadas o una combinación de subredes públicas y privadas.
   * En entornos de producción, se recomienda colocar los nodos de trabajo en subredes privadas por motivos de seguridad y usar subredes públicas para los balanceadores de carga.
3. **Tamaño de CIDR de las subredes**:
   * Cada subred del clúster necesita al menos seis direcciones IP disponibles para EKS; AWS recomienda dieciséis. Planifique por separado la capacidad de nodos/Pods/balanceadores de carga.
   * Como EKS asigna direcciones IP de la VPC a cada Pod, se necesitan bloques CIDR lo bastante grandes en función del número previsto de Pods.
4. **Requisitos de etiquetado**:
   * Las etiquetas siguientes se refieren al descubrimiento y la propiedad en integraciones específicas, no son requisitos universales para crear clústeres de EKS:
     * Etiqueta heredada o específica del controlador para indicar la propiedad: `kubernetes.io/cluster/<cluster-name>: shared`
     * Subredes públicas: `kubernetes.io/role/elb: 1`
     * Subredes privadas: `kubernetes.io/role/internal-elb: 1`

**Ejemplo de configuración de VPC (con eksctl):**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["203.0.113.10/32"]
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
    public:
      us-west-2a:
        id: subnet-0123456789abcdef2
      us-west-2b:
        id: subnet-0123456789abcdef3
```

**Configuración de VPC con AWS CLI:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

Una NAT gateway es una posible vía de salida a Internet. Los VPC endpoints necesarios, las imágenes reflejadas y la conectividad privada pueden permitir operar sin acceso a Internet. La ubicación en subredes privadas y la eliminación de la salida a Internet son decisiones distintas. Sustituya la VPC, las subredes y el CIDR del cliente de ejemplo por valores reales que se hayan revisado.

</details>

3. ¿Qué separación de roles corresponde al configurar un plano de control convencional de EKS con trabajadores EC2?
   * A) Solo se necesita un rol de clúster
   * B) Solo se necesita un rol de nodo EC2
   * C) Roles separados para el clúster y los nodos EC2
   * D) Sustituir ambos por un rol de ejecución de Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Roles separados para el clúster y los nodos EC2**

El rol del clúster confía en `eks.amazonaws.com` y permite que EKS administre la infraestructura del clúster. EKS convencional necesita `AmazonEKSClusterPolicy` o permisos equivalentes. El rol del nodo EC2 confía en `ec2.amazonaws.com` y se proporciona mediante un perfil de instancia. EKS configura el perfil de instancia para los grupos de nodos administrados; el proceso de arranque del nodo no crea roles de IAM.

La base para EC2 es `AmazonEKSWorkerNodePolicy` y `AmazonEC2ContainerRegistryPullOnly`, o permisos equivalentes con privilegios mínimos. También se necesitan permisos de CNI; se recomienda usar un rol independiente de IRSA/Pod Identity. Si no se hace, el rol del nodo necesita los permisos de CNI. La política IPv4 `AmazonEKS_CNI_Policy` no es una política IPv6. Los permisos de los controladores de almacenamiento, balanceadores de carga y registro de logs no son requisitos universales para todos los nodos.

Este ejemplo crea roles convencionales nuevos para el clúster y los nodos. Use una cuenta/rol autorizado y deténgase si hay errores. Un conflicto de nombres no adjunta políticas al rol existente.

```bash
IAM_EXAMPLE_DIR=$(mktemp -d /tmp/eks-iam-example.XXXXXX)
: "${IAM_EXAMPLE_DIR:?}"
: "${NEW_CLUSTER_ROLE_NAME:?Choose an unused role name for this example}"
: "${NEW_NODE_ROLE_NAME:?Choose a different unused role name}"
cat > "$IAM_EXAMPLE_DIR/cluster-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "eks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
cat > "$IAM_EXAMPLE_DIR/node-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
# Attach policies only after successfully creating the new role.
aws iam create-role --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/cluster-trust.json" &&
aws iam attach-role-policy --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

if aws iam create-role --role-name "$NEW_NODE_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/node-trust.json"; then
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy &&
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
fi
```

Crear solo un plano de control con `CreateCluster` todavía no requiere un rol de nodo EC2. Añádalo para el cómputo EC2. Fargate usa un rol de ejecución de Pod distinto, separado de los permisos de AWS de las aplicaciones. Auto Mode necesita políticas de clúster adicionales y `sts:TagSession`, además de políticas mínimas para el rol del nodo. Revise por separado los permisos de la identidad de aprovisionamiento, como `iam:PassRole`.

[Requisitos del rol de nodo](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

</details>

4. ¿Cuál es el comando correcto para crear un clúster de EKS con eksctl?
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**Explicación:** El comando correcto para crear un clúster de EKS con eksctl es `eksctl create cluster --name my-cluster --region us-west-2`. Este comando crea un clúster de EKS con la configuración predeterminada, con el nombre y en la región especificados.

**Estructura de los comandos de eksctl:**

* `eksctl`: comando base
* `create`: acción para crear un recurso
* `cluster`: tipo de recurso que se va a crear (clúster)
* `--name my-cluster`: especifica el nombre del clúster
* `--region us-west-2`: especifica la región de AWS

**Comando básico para crear un clúster:**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

Los valores predeterminados dependen de la versión de eksctl. Seleccione explícitamente la versión de EKS, AL2023, el número de nodos y los endpoints en el archivo siguiente. La creación puede aprovisionar recursos de VPC, nodos e IAM; revise la configuración y los costos en una cuenta de prueba autorizada.

**Comando avanzado con opciones adicionales:**

```bash
eksctl create cluster \
  --name my-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --with-oidc \
  --node-ami-family AmazonLinux2023 \
  --node-private-networking \
  --managed
```

**Creación de un clúster mediante un archivo de configuración:**

```bash
# Create cluster.yaml file
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR:?Set your approved client CIDR}"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    amiFamily: AmazonLinux2023
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: false
EOF

# Create cluster using configuration file
eksctl create cluster -f cluster.yaml
```

**Problemas con las demás opciones:**

* `eksctl create-cluster`: formato de comando incorrecto. eksctl usa espacios, no guiones (-), para separar los comandos.
* `eksctl new cluster`: `new` no es un comando válido de eksctl.
* `eksctl start cluster`: `start` no es un comando válido de eksctl. Use los comandos de ciclo de vida documentados en lugar de inventar un verbo.

eksctl ofrece diversos comandos para administrar clústeres de EKS:

* `eksctl create cluster`: crear un clúster nuevo
* `eksctl get cluster`: mostrar los clústeres
* `eksctl upgrade cluster`: actualizar un clúster
* `eksctl delete cluster`: eliminar un clúster
* `eksctl create nodegroup`: añadir un grupo de nodos
* `eksctl scale nodegroup`: escalar un grupo de nodos

</details>

5. ¿Qué versiones de Kubernetes se pueden elegir para un clúster de EKS nuevo?
   * A) Solo la última versión upstream
   * B) Siempre exactamente la última más dos versiones
   * C) Versiones ofrecidas en soporte estándar o extendido de EKS en la región de destino
   * D) Todas las versiones de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Versiones ofrecidas en soporte estándar o extendido de EKS en la región de destino**

Una versión secundaria de EKS recibe **14 meses de soporte estándar a partir de su fecha de lanzamiento en EKS**, seguidos de **12 meses de soporte extendido de pago**. La lista oficial al 12 de octubre de 2026 incluye **1.34–1.37** en soporte estándar y **1.31–1.33** en soporte extendido. EKS 1.37 estuvo disponible el 1 de octubre de 2026, después de su lanzamiento upstream del 26 de agosto. Consulte la región de destino para saber qué versiones están disponibles para nuevos clústeres.

El soporte extendido está habilitado de forma predeterminada; la política de actualización y las fechas de fin de soporte pueden activar actualizaciones automáticas del plano de control. Planifique por separado las actualizaciones de nodos y complementos. Siga los avisos de AWS sobre fechas de soporte en lugar de tratar la ventana máxima de soporte como una razón para retrasar las actualizaciones.

Estos son ejemplos distintos para el descubrimiento, la generación de configuraciones, la creación en AWS y la actualización de un clúster existente. Prepare el destino autorizado, los roles, las subredes y el CIDR; no ejecute a ciegas los ejemplos de creación y actualización como si fueran un único flujo de trabajo.

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table

# Generate a versioned config for review; this does not create the cluster.
EKS_VERSION_DIR=$(mktemp -d /tmp/eks-version.XXXXXX)
: "${EKS_VERSION_DIR:?}"
eksctl create cluster --name "${NEW_CLUSTER_NAME:?}" --region "$EXAMPLE_REGION" \
  --version 1.36 --dry-run > "$EKS_VERSION_DIR/version-example.yaml"
# Review all generated defaults, AMI, endpoint CIDRs and costs before creating.

# AWS CLI creation uses --kubernetes-version; the API JSON field is version.
aws eks create-cluster --name "$NEW_CLUSTER_NAME" --region "$EXAMPLE_REGION" \
  --kubernetes-version 1.36 --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API \
  --resources-vpc-config "subnetIds=${SUBNET_A:?},${SUBNET_B:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"

# Updating an existing control plane is a separate operation.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query cluster.version
# Only after upgrade-readiness checks and choosing the next supported minor:
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

Las actualizaciones progresivas del plano de control deben avanzar una versión secundaria cada vez. Revise conjuntamente las funciones necesarias, el soporte restante y la compatibilidad de complementos/cargas de trabajo. Pruebe la versión de destino en lugar de asumir que una versión anterior siempre es más segura. Buscar cadenas de versión en los metadatos de complementos no sustituye la consulta de las versiones del clúster.

[Ciclo de vida de las versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

</details>

6. ¿Qué opción no aprovisiona por sí sola capacidad de cómputo para una carga de trabajo de EKS?
   * A) Grupos de nodos administrados
   * B) Grupos de nodos autoadministrados
   * C) Perfiles de Fargate
   * D) Un espacio de nombres de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Un espacio de nombres de Kubernetes**

Un espacio de nombres organiza recursos de Kubernetes, pero no proporciona capacidad de cómputo. Los grupos de nodos EC2 administrados, los nodos EC2 autoadministrados y los perfiles de Fargate son opciones válidas de cómputo. EKS Auto Mode también aprovisiona nodos administrados, y Hybrid Nodes conecta capacidad local/perimetral administrada por el cliente. No todos estos mecanismos usan la API de grupos de nodos administrados.


Los comandos de creación siguientes son alternativas para un clúster existente y nombres de grupos/perfiles sin usar. Sustituya todas las variables obligatorias por valores revisados. Compruebe la autorización de CNI/nodos y la conectividad de las subredes privadas. Fargate requiere un rol de ejecución de Pod, Pods compatibles y subredes privadas; su perfil no crea Pods de aplicación.

**1. Grupos de nodos administrados:**

* **Características**:
  * AWS administra el aprovisionamiento y el ciclo de vida de los nodos
  * Creación y registro automáticos de instancias EC2
  * Configuración automática de ASG (grupo de Auto Scaling)
  * Actualizaciones de la versión de Kubernetes de los nodos iniciadas por el operador
  * Sustitución de instancias EC2 en mal estado; la reparación de nodos de EKS requiere señales/configuración de estado compatibles
  * Actualizaciones de AMI iniciadas por el operador mediante el flujo de trabajo administrado
*   **Método de creación**:

    ```bash
    # Create managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-mng --managed --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5

    # Create managed node group using AWS CLI
    aws eks create-nodegroup \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --nodegroup-name my-mng --ami-type AL2023_x86_64_STANDARD \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --instance-types t3.medium \
      --scaling-config minSize=1,maxSize=5,desiredSize=3 \
      --node-role "${NODE_ROLE_ARN:?}"
    ```

**2. Grupos de nodos autoadministrados:**

* **Características**:
  * El usuario administra el aprovisionamiento y el ciclo de vida de los nodos
  * Más opciones de personalización
  * Se pueden usar AMI personalizadas o scripts de arranque
  * Adecuados para tipos de instancia o requisitos de configuración específicos
*   **Método de creación**:

    ```bash
    # Create self-managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-smng --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5 \
      --managed=false

    # Can also be created manually using CloudFormation or EC2 launch templates.
    ```

**3. Perfiles de Fargate:**

* **Características**:
  * Entorno sin servidor para ejecutar contenedores
  * No requiere administrar nodos
  * Asignación de recursos y facturación por Pod
  * Ejecución selectiva en función de espacios de nombres y etiquetas específicos
*   **Método de creación**:

    ```bash
    # Create Fargate profile using eksctl
    eksctl create fargateprofile \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-fargate-profile \
      --namespace my-namespace \
      --labels app=my-app

    # Create Fargate profile using AWS CLI
    aws eks create-fargate-profile \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --fargate-profile-name my-fargate-profile \
      --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --selectors '[{"namespace":"my-namespace","labels":{"app":"my-app"}}]'
    ```

**Comparación de las opciones:**

| Característica | Grupos de nodos administrados | Nodos autoadministrados | Fargate |
| --- | --- | --- | --- |
| Administración de la infraestructura | AWS administra el proceso de sustitución; los operadores configuran las actualizaciones y el escalado | Los operadores administran la AMI, el arranque y el ciclo de vida | AWS administra los hosts; los usuarios administran las aplicaciones, los perfiles y las solicitudes |
| Costo | Evalúe las instancias, la utilización, los compromisos y las operaciones | Evalúe la optimización junto con las operaciones | Compare el tamaño asignado a los Pods, el tiempo de ejecución y las restricciones |
| Escalado | Se necesita una política o un escalador automático de nodos independiente | Se necesita automatización independiente | Proporciona cómputo a los Pods coincidentes; el escalado de réplicas de la aplicación es independiente |

Los NodePools de Auto Mode y los perfiles de Fargate son recursos distintos de los grupos de nodos administrados de EC2. Fargate sigue requiriendo administrar las cargas de trabajo, la seguridad y la disponibilidad, y no siempre es más barato ni más caro.

</details>

7. ¿Cuál no es una familia de AMI optimizada para EKS publicada por AWS para nodos nuevos de EKS 1.36?
   * A) Amazon Linux 2023
   * B) Bottlerocket
   * C) Windows Server 2022
   * D) Ubuntu Core

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Ubuntu Core**

No considere Ubuntu Core una AMI optimizada para EKS publicada por AWS. Las imágenes Canonical Ubuntu Server y las AMI creadas por el cliente tienen publicadores, compatibilidad y vías de soporte distintos; no son el mismo producto que Ubuntu Core.

**Opciones para este ejemplo**

- **AL2023**: use una AMI optimizada para EKS y el proceso de arranque `nodeadm`. Compruebe la versión secundaria de Kubernetes, la arquitectura de CPU, la región y la compatibilidad con CNI.
- **Bottlerocket**: sistema operativo orientado a contenedores, con mecanismos de configuración y actualización distintos de los de los nodos Linux de propósito general.
- **Windows**: use versiones compatibles de hosts y contenedores Windows Server, y prepare los requisitos previos de red de Windows, autenticación y cargas de trabajo del sistema. Este no es un ejemplo de Windows para Auto Mode/Fargate.

**AL2 es un origen de migración para entornos heredados.** La publicación/soporte de AMI de AL2 optimizadas para EKS terminó el 26 de noviembre de 2025; el soporte del sistema operativo AL2 terminó el 30 de junio de 2026. El soporte extendido de Kubernetes de EKS no amplía el soporte de AL2. No recomiende AL2 para nuevas implementaciones de EKS 1.36.

```bash
# Alternative examples; create only the reviewed group needed by your workload.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}"   --name al2023-nodes --managed --node-ami-family AmazonLinux2023 --node-private-networking

eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name bottlerocket-nodes --managed --node-ami-family Bottlerocket --node-private-networking

# Only after preparing the cluster for Windows:
eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name windows-nodes --managed --node-ami-family WindowsServer2022FullContainer --node-private-networking
```

También se pueden usar AMI personalizadas en las plantillas de lanzamiento de grupos de nodos administrados. Para fijar una AMI, hay que verificar su sistema operativo/entorno de ejecución, los metadatos del clúster y la configuración de arranque. Instalar solo `docker.io` en una imagen Ubuntu arbitraria no crea un nodo EKS operativo. Use una imagen Canonical para la versión de EKS de destino con una configuración de eksctl/plantilla de lanzamiento revisada. La pregunta avanzada distingue el `ImageId` de la plantilla de lanzamiento, `amiType` del grupo de nodos y las restricciones para combinar datos de usuario.

Al elegir una imagen, revise conjuntamente las actualizaciones de seguridad, el rendimiento medido de las cargas de trabajo, la compatibilidad con Kubernetes/controladores, las operaciones y los requisitos especiales, como las GPU.

[Transición de AL2](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html) · [AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [Requisitos previos de Windows](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)

</details>

8. ¿Cuáles son los valores predeterminados si se omite el acceso a los endpoints de la API CreateCluster?
   * A) Público habilitado, privado deshabilitado
   * B) Solo privado
   * C) Ambos endpoints habilitados
   * D) No se puede cambiar el acceso después de la creación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Público habilitado, privado deshabilitado**

La API establece como valores predeterminados el acceso público habilitado y el privado deshabilitado. Las rutas de creación de eksctl, CDK y la consola pueden seleccionar explícitamente otros ajustes; no se trata de un valor predeterminado universal de todas las herramientas. Los ajustes de acceso se pueden cambiar después de la creación.

| Público | Privado | Ruta de acceso |
| --- | --- | --- |
| Activado | Desactivado | Endpoint público y publicAccessCidrs; tenga en cuenta también las direcciones reales de salida de los nodos/CI |
| Activado | Activado | Ruta privada para solicitudes dentro de la VPC; CIDR públicos permitidos para acceso externo |
| Desactivado | Activado | Ruta privada desde la VPC o las redes conectadas |
| Desactivado | Desactivado | Configuración no válida |

**El grupo de seguridad del clúster controla el tráfico del endpoint privado y de kubelet, no el acceso al endpoint público.** `publicAccessCidrs` se aplica únicamente al endpoint público. La autenticación/autorización sigue siendo necesaria, independientemente de la conectividad de red. Sustituya el CIDR IPv4 de ejemplo por la dirección real de salida aprobada del cliente.

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.resourcesVpcConfig

# Select the actual approved client egress CIDR, not an arbitrary example range.
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text)
: "${ENDPOINT_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

Compruebe que la actualización anterior tenga el estado `Successful` y que las redes de administración/CI puedan usar DNS privado, enrutamiento y acceso a la API antes de deshabilitar el acceso público. No envíe inmediatamente actualizaciones asíncronas que se solapen; establezca ambas opciones de acceso en una sola solicitud.

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

El acceso privado a la API y la eliminación de la salida a Internet son decisiones de diseño independientes. Evalúe conjuntamente los controles de identidad, red y operación; el acceso privado por sí solo no garantiza seguridad ni disponibilidad. Tenga en cuenta la VPN/Direct Connect/los hosts de administración y los costos de conectividad. Los endpoints IPv6 y Hybrid Nodes tienen consideraciones adicionales de DNS/CIDR que se explican en la documentación oficial.

[Controles de acceso a los endpoints del clúster](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)

</details>

9. ¿Qué NO se debe tener en cuenta al seleccionar tipos de instancia para grupos de nodos en clústeres de Amazon EKS?
   * A) Requisitos de la carga de trabajo (CPU, memoria, almacenamiento)
   * B) Optimización de costos
   * C) El alias del contexto local de kubeconfig
   * D) Generación de la instancia (p. ej., t3 frente a t2)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) El alias del contexto local de kubeconfig**

Un alias de kubeconfig es un nombre local del cliente y no cambia el rendimiento, el precio ni la disponibilidad de las instancias. En cambio, la disponibilidad del tipo en las AZ necesarias, la capacidad real y las cuotas de la cuenta son restricciones importantes al seleccionarlo.

**Aspectos que sí deben tenerse en cuenta al seleccionar tipos de instancia para grupos de nodos:**

1. **Requisitos de la carga de trabajo (CPU, memoria, almacenamiento)**:
   * Seleccione tipos de instancia que se ajusten a los requisitos de recursos de las aplicaciones.
   * Cargas de trabajo con uso intensivo de memoria: instancias optimizadas para memoria, como r5 y r6g.
   * Cargas de trabajo con uso intensivo de cómputo: instancias optimizadas para cómputo, como c5 y c6g.
   * Cargas de trabajo equilibradas: instancias de propósito general, como m5 y m6g.
   * Cargas de trabajo con GPU: instancias de cómputo acelerado, como p3 y g4dn.
2. **Optimización de costos**:
   * Instancias bajo demanda frente a Spot
   * Instancias reservadas o Savings Plans
   * Selección del tamaño adecuado de instancia (evitar el aprovisionamiento excesivo)
   * Ahorro de costos mediante instancias Graviton basadas en ARM (p. ej., m6g y c6g)
3. **Generación de la instancia**:
   * Compare la relación precio/rendimiento específica de cada generación para la carga de trabajo real.
   * En las familias con rendimiento ampliable, tenga en cuenta el comportamiento de los créditos de CPU y el rendimiento de referencia.
   * Las generaciones más recientes ofrecen redes mejoradas, rendimiento de almacenamiento, etc.
4. **Requisitos de red**:
   * Compatibilidad con redes mejoradas (ENA, EFA, etc.)
   * Requisitos de ancho de banda de red
   * Límites de red relacionados con el máximo de Pods por instancia
5. **Requisitos de almacenamiento**:
   * Si se necesita almacenamiento local de instancia (p. ej., instancias i3 y d3)
   * Compatibilidad con la optimización de EBS
   * Requisitos de rendimiento de almacenamiento e IOPS
6. **Arquitectura de CPU**:
   * x86 (Intel, AMD) frente a ARM (AWS Graviton)
   * Consideraciones de compatibilidad de aplicaciones

**Zonas de disponibilidad e implementación de grupos de nodos:**

La cobertura necesaria de AZ limita los tipos de instancia utilizables. Que una instancia aparezca en el catálogo no garantiza que haya capacidad inmediata:

* Despliegue grupos de nodos en varias zonas de disponibilidad para lograr alta disponibilidad.
* Planifique la capacidad de los nodos y la distribución topológica de los Pods; después, verifique su ubicación real.
* Puede seleccionar todas las zonas de disponibilidad de la región o zonas específicas.

```bash
# Deploy node group to specific availability zones
eksctl create nodegroup \
  --cluster "${EXAMPLE_CLUSTER:?}" --region us-west-2 \
  --name my-nodegroup --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

**Ejemplos de selección de tipos de instancia:**

1. **Servidores de aplicaciones web**:
   * Instancias de propósito general: t3.medium, m5.large
   * Rentables y con rendimiento equilibrado
2. **Bases de datos**:
   * Instancias optimizadas para memoria: r5.xlarge, r6g.xlarge
   * Alta proporción de memoria respecto a CPU
3. **Trabajos de procesamiento por lotes**:
   * Instancias optimizadas para cómputo: c5.xlarge, c6g.xlarge
   * Alto rendimiento de CPU
4. **Cargas de trabajo de aprendizaje automático**:
   * Instancias con GPU: p3.2xlarge, g4dn.xlarge
   * Capacidades de cómputo acelerado

Las familias anteriores son ejemplos, no un catálogo de productos actual ni una clasificación de rendimiento medido. Revise conjuntamente la carga de trabajo, el precio, la arquitectura, los controladores y las ofertas/capacidad en las AZ necesarias.

</details>

10. ¿Cuál es el comando correcto para configurar kubectl después de crear un clúster de Amazon EKS?
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**Explicación:** El comando correcto para configurar kubectl después de crear un clúster de Amazon EKS es `aws eks update-kubeconfig --name my-cluster --region us-west-2`. Este comando usa el módulo EKS de AWS CLI para actualizar el archivo kubeconfig del clúster especificado.

**Proceso de configuración de kubectl:**

1. **Actualización del archivo kubeconfig**:
   * El archivo kubeconfig almacena la información de configuración que kubectl necesita para comunicarse con los clústeres de Kubernetes.
   * El orden de selección es: `--kubeconfig` explícito, la primera ruta de `KUBECONFIG` y, después, `~/.kube/config`.
   * El comando combina la configuración del clúster/autenticación exec y cambia el contexto actual en el archivo seleccionado; no concede permisos en el clúster.
2. **Componentes del comando**:
   * `--name`: nombre del clúster de EKS
   * `--region`: región de AWS donde se encuentra el clúster
   * `--kubeconfig` (opcional): ruta de un archivo kubeconfig personalizado
   * `--role-arn` (opcional): rol de IAM que se usará para acceder al clúster
3.  **Ejemplo de comando completo**:

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
4.  **Opciones adicionales**:

    ```bash
    # Use custom kubeconfig file
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Use specific IAM role
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Set alias
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
5.  **Verificación de la configuración**:

    ```bash
    # Check current context
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config current-context

    # List all contexts
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config get-contexts

    # Test cluster connection
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" cluster-info
    ```

**Problemas con las demás opciones:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: este comando no existe. AWS CLI no tiene ningún subcomando `get-kubeconfig`.
* `kubectl config set-cluster my-cluster --region us-west-2`: la sintaxis de este comando es incorrecta. `kubectl config set-cluster` no admite la opción `--region` y no configura automáticamente la información de autenticación necesaria para los clústeres de EKS.
* `eksctl configure kubectl --name my-cluster --region us-west-2`: este comando no existe. eksctl no tiene un subcomando `configure kubectl`. Al crear un clúster con eksctl, kubeconfig se configura automáticamente; para clústeres existentes, use `aws eks update-kubeconfig` o `eksctl utils write-kubeconfig`.

**Escritura de la configuración de un clúster existente con eksctl:**

Para un clúster existente, escriba su configuración sin crear otro clúster:

```bash
eksctl utils write-kubeconfig --cluster my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

Esto escribe kubeconfig para el clúster existente. Verifique por separado la autenticación de IAM y la autorización mediante access entry/RBAC. La creación del clúster también escribe kubeconfig de forma predeterminada, salvo que se deshabilite.

**Administración de varios clústeres:**

Al administrar varios clústeres de EKS, puede añadirlos al archivo kubeconfig ejecutando el comando `aws eks update-kubeconfig` para cada uno:

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2 --alias cluster1-west --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1 --alias cluster2-east --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Switch context
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --context cluster1-west get nodes
```

Por tanto, el comando correcto para configurar kubectl después de crear un clúster de Amazon EKS es `aws eks update-kubeconfig --name my-cluster --region us-west-2`.

</details>

## Ejercicios prácticos

### Ejercicio 1: crear un clúster de EKS con eksctl

**Escenario:** prepare un clúster convencional con grupo de nodos administrados de EC2 para un equipo de desarrollo. Este es un diseño de capacitación, no una prueba de que esté preparado para producción ni un resultado de costos medido.

**Requisitos:** use dos AZ, dos nodos `t3.medium` AL2023 inicialmente, límites de escalado de 2–5, redes privadas para los nodos y ambos endpoints de API con un CIDR público aprobado. Los límites por sí solos no instalan un escalador automático. Compruebe los créditos de CPU de las instancias con rendimiento ampliable, la memoria, la capacidad de IP, las cuotas y las necesidades reales de las cargas de trabajo antes de elegir `t3.medium`.

<details>
<summary>Mostrar respuesta</summary>

**1. Prepare las herramientas y la identidad.** Use las instrucciones de instalación verificadas con checksum y específicas para la arquitectura en [Parte 1](../../eks/02-eks-cluster-creation-part1.md). Este ejemplo se revisó con EKS 1.36 y eksctl 0.230.0; antes de ejecutarlo, compruebe las versiones de EKS disponibles en la región y las versiones compatibles del cliente y los complementos. `kubectl` debe cumplir los límites de desviación de versiones. Use un rol de IAM de operador aprobado que ya exista y que pueda asumir con su inicio de sesión; los permisos de aprovisionamiento y el acceso a Kubernetes son independientes.

**2. Genere y revise una configuración local privada.** El nombre generado está destinado a un clúster nuevo de capacitación. El CIDR público debe ser su rango real de salida permitido. Las dos AZ son ejemplos para `us-west-2`, sujetos a la oferta y la capacidad disponibles.

```bash
# Use a dedicated training account/role with reviewed provisioning permissions.
aws sts get-caller-identity
eksctl version
kubectl version --client
EKS_LAB_DIR=$(mktemp -d /tmp/eks-creation-lab.XXXXXX)
: "${EKS_LAB_DIR:?}"
EKS_LAB_CLUSTER="creation-quiz-$(date +%s)-$$"
EKS_LAB_REGION=us-west-2
EKS_LAB_KUBECONFIG="$EKS_LAB_DIR/kubeconfig"
: "${APPROVED_API_CIDR:?Set your actual approved administration egress CIDR}"
: "${OPERATOR_ROLE_ARN:?Set an existing IAM role ARN, not an STS session ARN}"

cat > "$EKS_LAB_DIR/cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_LAB_CLUSTER}
  region: ${EKS_LAB_REGION}
  version: "1.36"
availabilityZones: ["us-west-2a", "us-west-2b"]
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR}"]
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: false
  accessEntries:
    - principalARN: "${OPERATOR_ROLE_ARN}"
      type: STANDARD
      accessPolicies:
        - policyARN: arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy
          accessScope:
            type: cluster
managedNodeGroups:
  - name: dev-ng
    amiFamily: AmazonLinux2023
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    privateNetworking: true
    disableIMDSv1: true
    ssh:
      allow: false
    tags:
      Environment: development
      Owner: training
EOF

# Review the local configuration; this command does not create resources.
eksctl create cluster -f "$EKS_LAB_DIR/cluster.yaml" --dry-run \
  > "$EKS_LAB_DIR/resolved.yaml"
```

Esto concede acceso de administrador del clúster al operador indicado, únicamente para el laboratorio, y deshabilita el acceso de administrador automático para quien lo crea. No crea el rol del operador ni concede a quien ejecuta el comando permiso para asumirlo. eksctl crea los roles necesarios para el clúster y los nodos; revise el alcance de las políticas generadas. La configuración convencional puede asignar al rol del nodo los permisos de VPC CNI. Para un aislamiento más estricto de las cargas de trabajo, configure un rol dedicado para `aws-node` siguiendo la guía oficial de IAM para CNI. No añada a todos los nodos permisos amplios de publicación de imágenes, DNS, almacenamiento, balanceadores de carga o registro de logs solo porque esos complementos puedan usarse más adelante.

**3. Aprovisione solo después de revisar la configuración y los costos.** La topología predeterminada de una VPC nueva puede crear NAT y otra infraestructura facturable. `eksctl` usa CloudFormation para los recursos de VPC/subredes/grupos de seguridad/roles/clúster/grupo de nodos. Si se produce un error, pueden quedar recursos parciales; inspeccione los eventos de las pilas en lugar de asumir que se limpiarán por completo de forma automática.

```bash
# Provisioning step: creates billable AWS resources.
if eksctl create cluster -f "${EKS_LAB_DIR:?}/cluster.yaml" --write-kubeconfig=false; then
  EKS_LAB_ARN=$(aws eks describe-cluster \
    --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
    --query cluster.arn --output text)
  : "${EKS_LAB_ARN:?Could not record the created cluster ARN}"
  aws eks update-kubeconfig --name "$EKS_LAB_CLUSTER" \
    --region "$EKS_LAB_REGION" --role-arn "${OPERATOR_ROLE_ARN:?}" \
    --kubeconfig "${EKS_LAB_KUBECONFIG:?}" --alias "$EKS_LAB_CLUSTER"
fi
```

**4. Verifique el estado real, el acceso y los límites de escalado.** Espere a que el clúster y el grupo de nodos tengan el estado `ACTIVE` y a que los nodos estén `Ready`; inspeccione los Pods del sistema en mal estado y verifique la ubicación prevista en las AZ. Que una solicitud de creación haya tenido éxito o que se haya podido obtener una lista mediante RBAC no demuestra que el clúster funcione ni que sea seguro.

```bash
aws eks describe-cluster --name "${EKS_LAB_CLUSTER:?}" \
  --region "${EKS_LAB_REGION:?}" \
  --query 'cluster.{status:status,version:version,endpoint:resourcesVpcConfig,access:accessConfig}'
aws eks describe-nodegroup --cluster-name "$EKS_LAB_CLUSTER" \
  --nodegroup-name dev-ng --region "$EKS_LAB_REGION" \
  --query 'nodegroup.{status:status,scaling:scalingConfig,ami:amiType}'
kubectl --kubeconfig "${EKS_LAB_KUBECONFIG:?}" config current-context
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get pods -n kube-system
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" auth can-i get nodes
```

**5. Añada solo los componentes necesarios.** Cluster Autoscaler requiere la configuración de IAM/cuenta de servicio/detección con alcance limitado de la pregunta avanzada 2; los límites no responden por sí solos a la demanda de las cargas de trabajo. `kubectl top` requiere que Metrics Server esté instalado y en buen estado. En la configuración de referencia auditada de Metrics Server 0.9.0, se admite Kubernetes 1.34 y versiones posteriores; verifique la versión que esté instalada realmente. Mida el uso de cargas de trabajo representativas antes de afirmar que habrá ahorro de costos o que el dimensionamiento es correcto.

**6. Elimine este clúster de capacitación.** Primero elimine los Services LoadBalancer/Ingress creados en el laboratorio y espere a que sus controladores liberen los recursos de AWS; inspeccione las políticas de recuperación de PVC y los volúmenes que se conserven. Este ejercicio no crea esos recursos de aplicación. Después, elimine únicamente el clúster registrado:

```bash
# Only after removing this lab's workloads and checking retained resources.
if CURRENT_LAB_ARN=$(aws eks describe-cluster \
  --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
  --query cluster.arn --output text) &&
  [ "$CURRENT_LAB_ARN" = "${EKS_LAB_ARN:?Original cluster ARN required}" ]; then
  eksctl delete cluster --name "$EKS_LAB_CLUSTER" --region "$EKS_LAB_REGION" --wait
else
  printf '%s\n' 'Cluster lookup/identity mismatch; no deletion attempted.' >&2
fi
```

Después, compruebe CloudFormation y los inventarios de recursos de AWS para detectar eliminaciones fallidas, volúmenes conservados y roles/endpoints creados de forma independiente. Conserve el registro de configuración/ARN hasta confirmar la limpieza; cuando ya no necesite el kubeconfig temporal, elimine localmente su directorio.

</details>

### Ejercicio 2: crear un clúster de EKS con la consola de administración de AWS

**Escenario:** revise un diseño convencional con grupo de nodos administrados que pueda servir de referencia para una futura implementación de producción. El dimensionamiento de las cargas de trabajo, el enrutamiento, IAM, la disponibilidad, las actualizaciones y la recuperación siguen siendo supuestos específicos del entorno que deben probarse. Durante la auditoría no se aprovisionó ni se sometió a pruebas de carga este recorrido.

<details>
<summary>Mostrar respuesta</summary>

**1. Prepare roles de IAM separados.**

- Rol del clúster: confíe en `eks.amazonaws.com` y adjunte `AmazonEKSClusterPolicy`.
- Rol del nodo EC2: confíe en `ec2.amazonaws.com`, adjunte `AmazonEKSWorkerNodePolicy` y `AmazonEC2ContainerRegistryPullOnly`. Cuando sea compatible, asigne a VPC CNI su propio rol de IRSA/Pod Identity. Si decide deliberadamente usar la alternativa más sencilla del rol de nodo IPv4, adjunte explícitamente `AmazonEKS_CNI_Policy` y documente la contrapartida de compartir permisos.
- Identidad de operador/aprovisionamiento: use permisos de IAM aprobados y limitados a los recursos, y `iam:PassRole` para estos roles. Añada una access entry de EKS para el rol existente del operador con la política de acceso necesaria para el laboratorio. Crear kubeconfig no concede autorización en Kubernetes.

**2. Revise la VPC y las subredes.** El siguiente ejemplo oficial sigue siendo una referencia útil; la fecha de su URL no es una versión de EKS:

```text
https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
```

Lea la plantilla de CloudFormation antes de crear una pila de capacitación con un nombre único. Sus valores predeterminados crean una VPC con **dos subredes públicas y dos privadas en dos AZ, una gateway de Internet y dos NAT gateways/EIP**. Por tanto, se trata de un diseño con NAT y salida a Internet, no de un clúster privado sin salida. Revise la superposición de CIDR, las AZ, la capacidad de IP y los cargos por NAT en lugar de conservar los valores predeterminados para producción.

Registre `VpcId`, `SubnetIds` y `SecurityGroups`. `SubnetIds` incluye **tanto las subredes públicas como las privadas**; inspeccione cada tabla de enrutamiento y seleccione las subredes privadas reales para los nodos. El grupo de seguridad personalizado de salida no demuestra que existan todas las reglas de comunicación necesarias. Revise el grupo de seguridad del clúster de EKS, los grupos adicionales y las reglas de comunicación entre el plano de control y los nodos.

**3. Cree un clúster convencional.** En la consola de EKS, elija la ruta de configuración personalizada y deshabilite Auto Mode para este ejercicio. Seleccione una versión disponible y compatible con soporte estándar de EKS (1.36 es el ejemplo auditado), el rol de servicio del clúster y la VPC/subredes revisadas.

- Seleccione la autenticación mediante access entries de API y conceda el acceso adecuado al operador indicado; no dependa de un valor predeterminado de acceso de administrador para quien lo crea que no esté explicado.
- Para una API de acceso solo privado, verifique primero el enrutamiento/DNS privado de la red de administración. Como alternativa, habilite el acceso público y privado, y restrinja `publicAccessCidrs` al rango aprobado de salida de administración.
- Mantenga los complementos compatibles de VPC CNI, kube-proxy y CoreDNS para este clúster convencional de EC2; revise su configuración y sus permisos. Habilite los registros de logs del plano de control necesarios y tenga en cuenta sus costos.
- Revise y cree el clúster; luego, espere a que tenga el estado `ACTIVE`. La duración de la creación es variable: que se indique un número aproximado de minutos no significa que haya terminado.

**4. Añada un grupo de nodos administrados.** Seleccione el rol del nodo EC2, la AMI AL2023 x86_64 y un tipo de instancia compatible, como el ejemplo ilustrativo `m5.large`. El ejemplo usa un disco raíz de 50 GiB, tamaño deseado 3, mínimo 2 y máximo 5, y las subredes privadas revisadas. Son ejemplos de dimensionamiento, no recomendaciones de producción. Configure el acceso, IMDS y el cifrado del almacenamiento según sea necesario; espere a que el grupo de nodos tenga el estado `ACTIVE` y a que los nodos estén `Ready`.

**5. Verifique el acceso e inspeccione los grupos de seguridad reales de AWS.** Use el nombre del clúster registrado en la consola y su rol de operador aprobado:

```bash
CONSOLE_LAB_DIR=$(mktemp -d /tmp/eks-console-lab.XXXXXX)
: "${CONSOLE_LAB_DIR:?}"
CONSOLE_KUBECONFIG="$CONSOLE_LAB_DIR/kubeconfig"
aws eks update-kubeconfig --name "${CONSOLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --role-arn "${OPERATOR_ROLE_ARN:?}" \
  --kubeconfig "$CONSOLE_KUBECONFIG" --alias "$CONSOLE_CLUSTER"
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get pods -n kube-system

# Security groups are AWS resources; kubeconfig does not contain their rules.
aws eks describe-cluster --name "$CONSOLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_CLUSTER_SG_ID:?Copy the cluster SG ID from the result above}"
```

**6. Ejercicio opcional de NetworkPolicy.** Primero verifique que el CNI seleccionado y su configuración apliquen NetworkPolicy. La compatibilidad de políticas de AWS VPC CNI debe estar habilitada y ser compatible con la configuración de los nodos y el sistema operativo. La siguiente política de denegación predeterminada solo para ingreso se limita a un espacio de nombres de laboratorio nuevo y vacío; no deniega el egreso ni demuestra que la aplicación de políticas funcione simplemente porque `apply` tenga éxito.

```bash
# An optional isolated policy example, after enabling CNI policy enforcement.
NP_LAB_NAMESPACE="np-quiz-$(date +%s)-$$"
if kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" create namespace "$NP_LAB_NAMESPACE"; then
  NP_LAB_UID=$(kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    get namespace "$NP_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}')
  : "${NP_LAB_UID:?Namespace identity lookup failed}"
  cat > "${CONSOLE_LAB_DIR:?}/default-deny.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: ${NP_LAB_NAMESPACE}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
EOF
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    apply -f "$CONSOLE_LAB_DIR/default-deny.yaml"
fi
```

Pruebe el tráfico permitido y denegado con Pods de prueba dedicados y añada las políticas de autorización necesarias para la aplicación antes de usar este patrón con cargas de trabajo reales. No la aplique a un espacio de nombres compartido `default` existente. Cuando termine, elimine el espacio de nombres aislado:

```bash
# Remove only the namespace created above, after confirming its UID.
if CURRENT_NP_UID=$(kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" \
  get namespace "${NP_LAB_NAMESPACE:?}" -o jsonpath='{.metadata.uid}') &&
  [ "$CURRENT_NP_UID" = "${NP_LAB_UID:?Original namespace UID required}" ]; then
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" delete namespace "$NP_LAB_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace lookup/identity mismatch; no deletion attempted.' >&2
fi
```

**7. Limpieza en la consola:** elimine las cargas de trabajo del laboratorio y espere a que se liberen los recursos de nube asociados; después, elimine el grupo de nodos administrados del laboratorio, espere a que se elimine y elimine el clúster del laboratorio. Elimine la pila de CloudFormation de la VPC del laboratorio solo después de que desaparezcan sus recursos de EKS y las dependencias externas. Elimine únicamente los roles de IAM/endpoints creados exclusivamente para este laboratorio; conserve los recursos compartidos e inspeccione los recursos que no se hayan eliminado o que se hayan retenido. Esta revisión no ejecutó esas operaciones.

</details>

## Temas avanzados

Las siguientes preguntas tratan temas avanzados relacionados con la creación de clústeres de Amazon EKS. Esta sección evalúa su comprensión de los conceptos avanzados y las prácticas recomendadas para crear clústeres de EKS.

1. ¿Cuál es una ventaja principal de las plantillas de lanzamiento personalizadas para los grupos de nodos administrados de EC2 de EKS?
   * A) Garantizan una creación más rápida del clúster
   * B) Permiten personalizar los datos de usuario de los nodos y la configuración de volúmenes
   * C) Permiten instalar complementos del plano de control
   * D) Actualizan automáticamente todos los nodos existentes a cada nueva AMI publicada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permiten personalizar los datos de usuario de los nodos y la configuración de volúmenes**

Las plantillas de lanzamiento permiten personalizar **grupos de nodos administrados de EC2**, incluido el almacenamiento, los metadatos de instancia y los datos de usuario específicos del sistema operativo. No configuran el plano de control de EKS ni los nodos de EKS Auto Mode.

**Datos de usuario de AL2023:** use datos MIME multipart. Si se usa una AMI seleccionada por EKS (sin `ImageId` en la plantilla), EKS proporciona/combina la configuración del nodo. Si se usa un ID de AMI personalizado, proporcione el `NodeConfig` completo descrito en la pregunta avanzada 5. Los servicios systemd de AL2023 ejecutan `nodeadm`; no llame a `/etc/eks/bootstrap.sh`, no vuelva a ejecutar `nodeadm init` ni inicie kubelet manualmente. El software adicional debe ser compatible con el sistema operativo seleccionado y tener acceso a una fuente de paquetes confiable.

Esta personalización mínima es para el caso de una AMI AL2023 seleccionada por EKS; solo crea un directorio para la aplicación:

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_CUSTOMIZATION"

--EKS_CUSTOMIZATION
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_CUSTOMIZATION--
```

**Almacenamiento:** el siguiente fragmento de `LaunchTemplateData` es válido. Confirme el nombre del dispositivo raíz de la AMI. Adjuntar un volumen no lo formatea ni lo monta. Ambos volúmenes de ejemplo están cifrados y se eliminan con la instancia; use un PV administrado por CSI y una política de recuperación/copia de seguridad adecuada para los datos de aplicaciones que deban sobrevivir a la sustitución de nodos.

```json
{
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 100,
        "VolumeType": "gp3",
        "Iops": 3000,
        "Throughput": 125,
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    },
    {
      "DeviceName": "/dev/sdf",
      "Ebs": {
        "VolumeSize": 500,
        "VolumeType": "gp3",
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    }
  ]
}
```

**Red y metadatos:** sustituya el grupo de seguridad de ejemplo por uno cuyas reglas permitan el tráfico necesario del plano de control, los nodos, DNS y las cargas de trabajo. Si se proporcionan grupos de seguridad personalizados, EKS **no** añade automáticamente el grupo de seguridad del clúster. Especifique los grupos de seguridad en el nivel de instancia o de interfaz de red, no en ambos.

```json
{
  "NetworkInterfaces": [
    {
      "DeviceIndex": 0,
      "Groups": ["sg-0123456789abcdef0"],
      "DeleteOnTermination": true
    }
  ],
  "MetadataOptions": {
    "HttpEndpoint": "enabled",
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1
  }
}
```

El límite de saltos de 1 presupone que los Pods usan IRSA o EKS Pod Identity en lugar de las credenciales del nodo. Las cargas de trabajo que necesitan acceso a IMDSv2 desde un contenedor pueden requerir un límite de saltos de 2. Ni esta opción ni IMDSv2 aíslan los Pods `hostNetwork`. Las interfaces múltiples, la ubicación y los dispositivos de almacenamiento de instancia requieren tipos de instancia compatibles y deben cumplir las restricciones de las plantillas de lanzamiento de EKS; no son opciones intercambiables en todos los casos.

**Cree el grupo de nodos:** elija la configuración de eksctl o el ejemplo de AWS CLI después de revisar los ID reales, los permisos y las rutas de red. Son alternativas, no instrucciones secuenciales:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    subnets: ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
```

```bash
# Use an existing reviewed template version and a new node group name.
aws eks create-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --launch-template "id=${LAUNCH_TEMPLATE_ID:?},version=${LAUNCH_TEMPLATE_VERSION:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --node-role "${NODE_ROLE_ARN:?}"
```

No incluya `SubnetId` ni `IamInstanceProfile` en la plantilla de lanzamiento: las subredes y el rol de IAM del nodo pertenecen a la solicitud del grupo de nodos. Si usa una plantilla de lanzamiento, no establezca también `diskSize` ni `remoteAccess` en el grupo de nodos. Establezca los tipos de instancia en la plantilla **o** en la solicitud del grupo de nodos. Si se incluye `ImageId`, omita `amiType`, `releaseVersion` y `version` del grupo de nodos, y verifique la compatibilidad de la AMI personalizada con kubelet y el plano de control.

Un `ImageId` explícito fija una AMI; una plantilla sin él puede usar una AMI seleccionada por EKS. Ninguno de los dos casos actualiza automáticamente los nodos existentes cada vez que se publica una AMI. Para actualizar una plantilla personalizada, se necesita una nueva versión de la **misma** plantilla y una actualización explícita del grupo de nodos, que sustituirá las instancias.

Referencias: [restricciones de plantillas de lanzamiento](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [campos de CreateNodegroup](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [inicialización de AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html).

</details>

2. ¿Qué enfoque no basta por sí solo para optimizar los costos de EKS?
   * A) Usar Spot para cargas de trabajo que toleran interrupciones
   * B) Configurar y autorizar Cluster Autoscaler
   * C) Elegir la generación de instancia más reciente para todas las cargas de trabajo sin medir
   * D) Evaluar Fargate de forma selectiva según las necesidades de las cargas de trabajo y el costo total

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Elegir la generación de instancia más reciente para todas las cargas de trabajo sin medir**

Elegir todos los nodos únicamente porque pertenecen a la generación más reciente no es un análisis de costos suficiente. Compare la arquitectura, el rendimiento, la latencia, la memoria, la disponibilidad regional y la tolerancia a interrupciones de la carga de trabajo. Una generación más reciente puede resultar más económica; ni las generaciones más nuevas ni las más antiguas son siempre más baratas para el mismo trabajo útil.

1. **Spot y diversificación:** AWS anuncia descuentos de hasta el 90 % frente a On-Demand para Spot; se trata de un posible descuento de precio, no de un ahorro medido o garantizado para este laboratorio. Tenga en cuenta las interrupciones y la capacidad de sustitución. Para Cluster Autoscaler, los distintos tipos de una misma familia de instancias deben tener la misma capacidad de CPU/memoria/GPU, porque la simulación del planificador usa el primer tipo. Compruebe por separado cualquier dependencia de discos locales.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: spot-ng
    amiFamily: AmazonLinux2023
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    spot: true
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 5
```

2. **Cluster Autoscaler:** los tamaños mínimo/máximo solo fijan límites de escalado. Instale y autorice un controlador para que cambie la capacidad deseada en respuesta a Pods que no se puedan programar y a capacidad que pueda retirarse. No conceda permisos de escalado amplios a todos los nodos. Antes de esta **nueva instalación**, prepare una cuenta de servicio `kube-system/cluster-autoscaler` con un rol de IRSA dedicado (relación de confianza OIDC limitada a esa cuenta de servicio) o una configuración compatible de Pod Identity. Limite las escrituras de escalado a los grupos de Auto Scaling previstos para el clúster y etiquete esos grupos con `k8s.io/cluster-autoscaler/enabled=true` y `k8s.io/cluster-autoscaler/<cluster-name>=owned`. Las etiquetas de recursos del grupo de nodos no demuestran por sí solas que esté configurado el descubrimiento del ASG.

La versión secundaria del controlador debe coincidir con la del clúster. Chart 9.59.0 usa por defecto el controlador 1.35.0, por lo que este ejemplo para EKS 1.36 selecciona explícitamente 1.36.1. Para otras versiones del clúster, se necesita una versión coincidente del controlador. Confirme que no haya una instalación existente de CA que administre los mismos grupos.

```bash
# EKS 1.36 example: first prepare the dedicated service account/IAM role
# and discovery tags on the target Auto Scaling groups.
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  --set-string "autoDiscovery.clusterName=${EXAMPLE_CLUSTER:?}" \
  --set-string "awsRegion=${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  --wait --timeout 5m
```

3. **Fargate y dimensionamiento adecuado:** Fargate reduce el trabajo de administración de hosts, pero cobra por los recursos asignados y el tiempo de ejecución, no solo por el uso de CPU medido. Ajuste los perfiles a los Pods compatibles y a las redes de subredes privadas; compare el costo total con EC2. `kubectl top` requiere Metrics Server, y una muestra breve no es un plan de capacidad.
4. **Graviton:** pruebe las imágenes ARM64 y sus dependencias antes de crear un grupo de nodos ARM. La afirmación de que una generación ofrece «hasta un 40 % más de relación precio/rendimiento» no significa que la factura se reduzca universalmente un 40 % ni garantiza el mismo rendimiento.

```bash
# Metrics Server must already be installed and healthy.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top nodes
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top pods --all-namespaces

# Alternative compute examples: each creates separately billed resources.
eksctl create fargateprofile --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name fp-dev --namespace dev
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name arm-ng \
  --managed --node-ami-family AmazonLinux2023 \
  --node-type m6g.large --nodes 2 --node-private-networking
```

5. **Compromisos:** las instancias reservadas y Savings Plans pueden reducir el costo del uso previsible que cumpla los requisitos. Los ahorros anunciados de hasta el 72 % dependen del producto, el plazo, la forma de pago y el uso; los compromisos no utilizados pueden anular el ahorro.
6. **Solicitudes y límites:** mida las cargas de trabajo representativas antes de elegir valores. Las solicitudes afectan a la programación y a las decisiones del escalador automático; los límites demasiado bajos pueden causar limitación de CPU o terminación por OOM. Estos son valores ilustrativos por contenedor:

```yaml
# Fragment inside spec.template.spec.containers[].
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

7. **Asignación de costos:** use Cost Explorer y los informes/herramientas de asignación configurados. Las etiquetas de Kubernetes no se convierten automáticamente en etiquetas de asignación de costos de AWS activadas. Incluya los costos del plano de control, las tarifas de Auto Mode cuando correspondan, el almacenamiento, los balanceadores de carga, NAT, la transferencia y el registro de logs.

Referencias: [CA en EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html), [Chart de CA](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler), [CA 1.36.1](https://github.com/kubernetes/autoscaler/releases/tag/cluster-autoscaler-1.36.1), [precios de Spot](https://aws.amazon.com/ec2/spot/), [precios de Fargate](https://aws.amazon.com/fargate/pricing/), [Graviton](https://aws.amazon.com/ec2/graviton/), [Savings Plans](https://aws.amazon.com/savingsplans/).

</details>

3. ¿Qué diseño satisface tanto el acceso a la API de Kubernetes solo de forma privada como la ausencia de salida a Internet desde los nodos/Pods?
   * A) API privada, subredes privadas para los nodos sin salida a Internet, endpoints de servicio necesarios y una ruta privada de administración
   * B) Solo nodos privados, sin cambiar los ajustes de API ni de salida
   * C) Deshabilitar los endpoints públicos y privados de la API de Kubernetes
   * D) Deshabilitar la API pública y mantener salida NAT sin restricciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) API privada, subredes privadas para los nodos sin salida a Internet, endpoints de servicio necesarios y una ruta privada de administración**

Separe dos decisiones: **quién puede acceder a la API de Kubernetes** y **a dónde pueden enviar tráfico los nodos/Pods**. Una API solo privada no elimina las rutas NAT, no bloquea el tráfico de salida de las cargas de trabajo ni garantiza que todos los paquetes permanezcan en una sola VPC. Las redes conectadas pueden acceder a la API privada si lo permiten el enrutamiento, DNS, los grupos de seguridad y la autorización.

Para esta pregunta, el requisito combina el acceso a la API solo de forma privada con nodos/Pods sin salida a Internet. Habilite el endpoint privado, deshabilite el público, use subredes privadas para los nodos sin una ruta de salida a Internet y proporcione los endpoints de servicio, las imágenes de registro y la ruta de administración que necesiten las cargas de trabajo.

**Transición de endpoints:** habilite primero el acceso privado, espere a que la actualización se complete correctamente y pruebe el acceso autenticado de `kubectl` desde la red privada prevista. Solo entonces use la alternativa independiente para acceso solo privado que aparece a continuación. Compruebe la actualización hasta que devuelva `Successful` y vuelva a verificar el acceso. El endpoint público se restringe mediante `publicAccessCidrs`, no mediante el grupo de seguridad del clúster; este último controla el tráfico del endpoint privado.

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

**Ubicación de los nodos:** este fragmento usa una VPC y subredes privadas existentes; sustituya los ID y verifique las rutas antes de usarlo. No crea VPC endpoints ni elimina rutas NAT existentes. Ejecutar eksctl desde una estación de trabajo con acceso únicamente a Internet y sin conexión con la VPC no permitirá acceder a una API privada de Kubernetes.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
managedNodeGroups:
  - name: private-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 3
    privateNetworking: true
```

**Conectividad con los servicios de AWS:** los siguientes ejemplos de ECR y S3 solo son parte del diseño. Revise primero los endpoints existentes para evitar conflictos de DNS privado por duplicados. Los endpoints de interfaz necesitan DNS privado y entrada HTTPS desde los clientes previstos; el endpoint de gateway de S3 necesita las tablas de enrutamiento privadas y políticas adecuadas para el endpoint y el bucket.

```bash
# Example fragments for a reviewed no-internet VPC design.
# Interface endpoint SG must allow HTTPS from the intended nodes/clients.
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.api" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.dkr" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.s3" \
  --vpc-endpoint-type Gateway \
  --route-table-ids "${PRIVATE_ROUTE_TABLE_A:?}" "${PRIVATE_ROUTE_TABLE_B:?}"
```

| Dependencia | Conectividad privada sin salida a Internet |
| --- | --- |
| Descarga de imágenes de ECR privado | `ecr.api`, `ecr.dkr` y gateway de S3; copie las imágenes públicas a un registro privado accesible |
| API de EC2 utilizadas por los nodos/CNI | `ec2`, permisos adecuados y política del endpoint |
| Credenciales de IRSA | `sts` regional; configure los SDK para usar el endpoint regional |
| Descubrimiento OIDC/JWKS desde la VPC | `oidc-eks`, por ejemplo, al configurar el proveedor OIDC de IAM; independiente de STS |
| Credenciales de EKS Pod Identity | `eks-auth` y un agente/configuración compatible de Pod Identity |
| API de administración de EKS | `eks`; no sustituye el endpoint privado de la API de Kubernetes |
| Logs, escalado automático, balanceo de carga, SSM | Endpoints y permisos para los servicios que se usen realmente; SSM también necesita conectividad de mensajería |

Los servicios de endpoint y los nombres DNS varían según la región/partición. Compruebe todas las dependencias de cada carga de trabajo, incluidos los registros de imágenes, las descargas de paquetes, las API externas y las funciones de los complementos. El endpoint de un servicio de AWS no sustituye a Internet de uso general.

**Administración:** use conectividad enrutada mediante VPN/Direct Connect, un host controlado con acceso privado o una sesión de SSM configurada adecuadamente. Un bastion no necesita intrínsecamente una IP pública. SSM sigue necesitando su agente, autorización de IAM y conectividad con los servicios.

Una API privada con nodos privados respaldados por NAT también es un diseño válido de EKS, pero no cumple el requisito de esta pregunta de no tener salida a Internet. Del mismo modo, una ruta pública de la subred no demuestra por sí sola que un nodo concreto sea accesible desde Internet; importan la asignación de direcciones y los controles de seguridad.

Referencias: [requisitos de clústeres privados](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [acceso a endpoints de API](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [PrivateLink y OIDC de EKS](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html).

</details>

4. ¿Cuál NO es el mecanismo de los grupos de nodos administrados de EKS para aplicar una nueva AMI de nodo?
   * A) Sustituir instancias mediante una actualización progresiva administrada
   * B) Crear y validar un grupo de nodos blue/green separado
   * C) Actualizar los paquetes del sistema operativo en las instancias en ejecución en vez de sustituirlas
   * D) Validar una nueva AMI en un grupo de nodos canario pequeño antes de ampliar la sustitución

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Actualizar los paquetes del sistema operativo en las instancias en ejecución en vez de sustituirlas**

Las actualizaciones de los grupos de nodos administrados de EKS sustituyen instancias EC2. Actualizar los paquetes del sistema operativo en las instancias en ejecución no es el mecanismo de actualización de AMI administrado. Evite la afirmación ambigua de que no se admiten todas las «actualizaciones en el mismo lugar»: AWS también usa esa expresión para describir la retención del recurso del grupo de nodos al cambiar la versión de AMI de una plantilla de lanzamiento, lo que sigue sustituyendo las instancias.

**Actualización progresiva:** `DEFAULT` crea capacidad de sustitución antes de retirar los nodos antiguos; `MINIMAL` puede terminar determinados nodos antiguos antes de crear los nodos de sustitución. `maxUnavailable` es 1 de forma predeterminada, pero se puede configurar, por lo que no siempre se actualiza exactamente un nodo a la vez. Compruebe las cuotas, la capacidad de las AZ, la ubicación de los Pods y la estrategia de actualización. Con una AMI personalizada, seleccione explícitamente la nueva versión de la misma plantilla de lanzamiento; el comando siguiente ilustra, en cambio, el caso de una AMI seleccionada por EKS:

```bash
# EKS-selected AMI case: inspect first, then initiate a reviewed update.
aws eks describe-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'nodegroup.{status:status,version:version,ami:amiType,release:releaseVersion,update:updateConfig}'
if NODE_UPDATE_ID=$(aws eks update-nodegroup-version \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODE_UPDATE_ID" \
    --region "$EXAMPLE_REGION" \
    --query 'update.{status:status,errors:errors}'
fi
```

Registre el ID de actualización devuelto y repita `describe-update` hasta que la actualización llegue a un estado terminal. Que el envío a la API haya tenido éxito no significa que la actualización haya terminado. Investigue los errores indicados antes de continuar. Un PDB que impida la expulsión puede producir `PodEvictionFailure`; no lo eluda con `--force` solo para que el comando termine.

**Blue/green:** cree un grupo de nodos AL2023 separado y compatible, pruebe la programación y la disponibilidad de las cargas de trabajo y luego migre gradualmente. Conserve la capacidad antigua hasta que se hayan satisfecho las comprobaciones de la aplicación, las restricciones de volumen/AZ y los requisitos de reversión. Limitarse a enumerar las etiquetas de los nodos no es una validación, y el tráfico sigue los endpoints de Service/Pods, no los nombres de los grupos de nodos. No elimine automáticamente el grupo antiguo inmediatamente después de crear el nuevo.

**Canario:** use un grupo pequeño etiquetado y con taint por separado. El taint evita que Pods ajenos se programen allí; solo la carga de prueba selecciona el nodo y tolera el taint. Los DaemonSets del sistema pueden seguir ejecutándose si sus tolerancias lo permiten. Esta es una configuración ilustrativa para un clúster de prueba existente:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: canary-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 1
    minSize: 1
    maxSize: 2
    privateNetworking: true
    labels:
      example.com/upgrade-track: canary
    taints:
      - key: example.com/upgrade-track
        value: canary
        effect: NoSchedule
```

Cree un espacio de nombres `upgrade-lab` sin usar en el contexto de prueba exclusivo antes de aplicar este Deployment demostrativo completo. Un canario real también debe probar las dependencias propias de la aplicación y tráfico representativo; este Pod de NGINX solo comprueba la programación y la disponibilidad básicas.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: upgrade-canary
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      nodeSelector:
        example.com/upgrade-track: canary
      tolerations:
        - key: example.com/upgrade-track
          operator: Equal
          value: canary
          effect: NoSchedule
      containers:
        - name: nginx
          image: nginx:1.30.6
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
```

**Presupuestos de interrupción y capacidad:** este ejemplo independiente presupone una carga de trabajo real `my-app` en `app-namespace`, normalmente con al menos tres réplicas disponibles. No es el PDB del canario de una sola réplica anterior:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: app-namespace
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

Un PDB limita las expulsiones voluntarias gestionadas mediante la API de expulsión; no garantiza la disponibilidad, no evita fallos de hardware ni impide la eliminación directa de un Pod/Deployment. `minAvailable: 2` impide las expulsiones cuando solo hay dos Pods coincidentes en buen estado. Verifique la capacidad disponible, la topología, las sondas, el comportamiento al terminar y la recuperación ante fallos. Los planes blue/green o canario no demuestran por sí solos que la reversión sea segura, especialmente para datos con estado.

Referencias: [comportamiento de las actualizaciones administradas](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [migración a AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [presupuestos de interrupción de Pods](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).

</details>

5. ¿Qué acción no forma parte del arranque de un trabajador EC2 con AL2023 optimizado para EKS?
   * A) Configurar kubelet/el entorno de ejecución de contenedores
   * B) Instalar en el trabajador componentes del plano de control administrados por AWS
   * C) Configurar la autenticación/conectividad del cliente del nodo
   * D) Registrar el nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Instalar en el trabajador componentes del plano de control administrados por AWS**

Los trabajadores no instalan el servidor de API, etcd, el administrador de controladores ni el planificador; estos pertenecen al plano de control administrado por AWS. **En EKS convencional, CoreDNS es un complemento del clúster del plano de datos, no uno de esos componentes del plano de control.**

Las AMI AL2023 optimizadas para EKS usan `nodeadm` para configurar containerd y kubelet. `nodeadm-config` establece la configuración básica antes de los datos de usuario y `nodeadm-run` completa la configuración e inicia los daemons después. La AMI ejecuta este proceso automáticamente; no vuelva a invocar `nodeadm init` desde los datos de usuario. El flujo `/etc/eks/bootstrap.sh` de AL2 no es la ruta de arranque actual de AL2023.

**Separar la unión del nodo de la red del clúster**

1. Aprovisione el rol de IAM/perfil de instancia del nodo y la autorización de acceso necesaria antes del lanzamiento. El proceso de arranque no crea roles de IAM. Use la ruta de kubeconfig/autenticación generada por la AMI en lugar de un kubeconfig manual que vuelva a asumir innecesariamente el propio rol de la instancia.
2. Kubelet registra el nodo. La disponibilidad depende tanto del estado del entorno de ejecución/CNI como de la conectividad del clúster.
3. En EKS convencional, `aws-node`, `kube-proxy` y CoreDNS se despliegan y administran como complementos del clúster. El arranque del host no instala todos estos complementos; no sobrescriba la configuración de CNI con un archivo inventado.
4. No falsifique manualmente las etiquetas `eks.amazonaws.com/nodegroup` o `topology.kubernetes.io/zone`, propiedad de los proveedores. Administre las etiquetas/taints personalizados mediante la configuración del grupo de nodos/proveedor de aprovisionamiento.

**Ejemplo de entrada NodeConfig**

Lo siguiente se ejecuta en la estación de trabajo de administración para generar datos de usuario a partir de metadatos reales de un clúster IPv4 existente. Está destinado a AMI personalizadas/nodos autoadministrados basados en AL2023 optimizado para EKS y revisados; los grupos de nodos administrados sin un ID de AMI personalizado usan la generación/combinción de metadatos de EKS. `NodeConfig` es configuración de arranque del host, no un recurso de Kubernetes normal que se envíe con `kubectl apply`.

```bash
# Run on the administration workstation to prepare reviewed IPv4 node user data.
NODE_CONFIG_DIR=$(mktemp -d /tmp/eks-nodeconfig.XXXXXX)
: "${NODE_CONFIG_DIR:?}"
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster --output json > "$NODE_CONFIG_DIR/cluster.json" || exit 1

jq -e '
  (.name | type == "string" and length > 0) and
  (.endpoint | startswith("https://")) and
  (.certificateAuthority.data | type == "string" and length > 0) and
  (.kubernetesNetworkConfig.ipFamily == "ipv4") and
  (.kubernetesNetworkConfig.serviceIpv4Cidr | type == "string" and length > 0)
' "$NODE_CONFIG_DIR/cluster.json" >/dev/null || exit 1

jq '{
  apiVersion: "node.eks.aws/v1alpha1",
  kind: "NodeConfig",
  spec: {
    cluster: {
      name: .name,
      apiServerEndpoint: .endpoint,
      certificateAuthority: .certificateAuthority.data,
      cidr: .kubernetesNetworkConfig.serviceIpv4Cidr
    }
  }
}' "$NODE_CONFIG_DIR/cluster.json" > "$NODE_CONFIG_DIR/nodeconfig.json" || exit 1

{
  printf 'MIME-Version: 1.0\n'
  printf 'Content-Type: multipart/mixed; boundary="EKS_NODE_CONFIG"\n\n'
  printf '%s\n' '--EKS_NODE_CONFIG' 'Content-Type: application/node.eks.aws' ''
  cat "$NODE_CONFIG_DIR/nodeconfig.json"
  printf '\n%s\n' '--EKS_NODE_CONFIG--'
} > "$NODE_CONFIG_DIR/user-data.mime"
printf 'Review user data: %s\n' "$NODE_CONFIG_DIR/user-data.mime"
# An EC2 LaunchTemplateData.UserData JSON field needs the MIME file base64 encoded.
# The console user-data editor can accept raw text when its encoding option is set accordingly.
```

No fije una única IP de servicio DNS ni un valor maxPods para todos los nodos. Siga el CIDR de servicio del clúster, la configuración de instancias/CNI/prefijos y las reglas de dimensionamiento documentadas. Estos comandos de inspección describen configuraciones convencionales de EC2; los componentes administrados son distintos en Auto Mode/Fargate.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" describe node "${EXAMPLE_NODE:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get daemonset aws-node kube-proxy
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get deployment coredns
```

Durante esta auditoría no se probaron la unión de nodos, la ejecución de daemons ni el comportamiento de la red, y tampoco se recopilaron registros del entorno de ejecución.

[Ciclo de vida de AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [API NodeConfig](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)

</details>

## Referencias oficiales

- [Versiones compatibles de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Rol de IAM del nodo de EKS](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [Rol de IAM de VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [Requisitos previos de NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Access entries de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Requisitos de Metrics Server](https://github.com/kubernetes-sigs/metrics-server#requirements)
- [Esquema de configuración de eksctl](https://schema.eksctl.io/)
