# Cuestionario de creación de clústeres EKS - Parte 1

> **Última actualización**: 12 de octubre de 2026

> Los comandos son ejemplos independientes, no un script que deba ejecutarse de arriba abajo. Use una cuenta o un clúster de formación dedicados, permisos de IAM revisados y un kubeconfig temporal privado (`EXAMPLE_KUBECONFIG`). Sustituya los ID de ejemplo y las variables obligatorias. Los comandos de creación generan cargos. Esta auditoría comprobó las fuentes, la sintaxis y los elementos locales; no aprovisionó recursos de AWS ni verificó la disponibilidad de aplicaciones.

Este cuestionario evalúa su comprensión de los conceptos, herramientas y prácticas recomendadas relacionados con la creación de clústeres de Amazon EKS. Abarca temas como los métodos de creación de clústeres, la configuración de VPC y la configuración de grupos de nodos.

## Preguntas de conceptos básicos

1. ¿Qué herramienta no tiene un comando integrado que aprovisione directamente un plano de control de EKS?
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) kubectl**

kubectl administra recursos mediante una API de Kubernetes y no tiene un comando nativo para aprovisionar EKS. Un controlador de infraestructura ya instalado, como ACK, puede reconciliar un recurso enviado con kubectl en un clúster de EKS; es una integración de controlador, no una operación de AWS integrada en kubectl.

Las herramientas que pueden utilizarse para crear clústeres de Amazon EKS incluyen:

1. **AWS Management Console**:
   * Cree clústeres de EKS mediante una interfaz web.
   * Adecuada para principiantes, ya que permite configurar visualmente los componentes del clúster.
   * Guía el proceso de creación del clúster mediante un asistente paso a paso.
2.  **AWS CLI**:

    * Cree clústeres de EKS desde la línea de comandos.
    * Utiliza el comando `aws eks create-cluster`.
    * Adecuada para scripts y automatización.

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * Una herramienta de línea de comandos diseñada específicamente para crear clústeres de EKS.
    * Desarrollada originalmente por Weaveworks; el proyecto actual se mantiene en la organización eksctl-io con contribuciones de AWS y la comunidad.
    * Puede crear un clúster con un único comando.

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Herramientas de infraestructura como código (IaC)**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    Estas herramientas permiten definir y desplegar clústeres de EKS como código.

kubectl se utiliza para administrar recursos de Kubernetes (Pods, Services, Deployments, etc.) después de crear un clúster. Para conectarse a un clúster de EKS, configure un kubeconfig autorizado, normalmente con `aws eks update-kubeconfig`.

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

Después, puede utilizar kubectl para administrar los recursos del clúster.

</details>

2. ¿Qué componente de VPC se debe especificar al crear un clúster de Amazon EKS?
   * A) Solo subredes públicas
   * B) Solo subredes privadas
   * C) Subredes en al menos 2 zonas de disponibilidad
   * D) NAT Gateway

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Subredes en al menos 2 zonas de disponibilidad**

**Explicación:** Al crear un clúster de Amazon EKS, el componente de VPC que se debe especificar son subredes en al menos 2 zonas de disponibilidad. Es un requisito de AWS para garantizar la alta disponibilidad de los clústeres de EKS.

**Requisitos de VPC para clústeres de EKS:**

1. **Se requieren subredes en al menos 2 zonas de disponibilidad (AZ)**:
   * Puesto que el plano de control de EKS se despliega en varias zonas de disponibilidad, se deben especificar subredes en al menos 2 zonas de disponibilidad al crear un clúster.
   * Esto admite la disponibilidad regional del plano de control. La disponibilidad de las cargas de trabajo también necesita planificación de la ubicación de réplicas, capacidad, almacenamiento y dependencias.
2. **Tipos de subredes**:
   * Puede utilizar solo subredes públicas, solo subredes privadas o una combinación de subredes públicas y privadas.
   * Para entornos de producción, se recomienda ubicar los nodos worker en subredes privadas por seguridad y utilizar subredes públicas para los balanceadores de carga.
3. **Tamaño de CIDR de la subred**:
   * Cada subred del clúster necesita al menos seis IP disponibles para EKS; AWS recomienda dieciséis. Planifique por separado la capacidad de nodos/Pods/balanceadores de carga.
   * Puesto que EKS asigna direcciones IP de VPC a cada Pod, se necesitan bloques CIDR suficientemente grandes según el número previsto de Pods.
4. **Requisitos de etiquetas**:
   * Las siguientes etiquetas se refieren a detección/propiedad para integraciones específicas, no son requisitos universales para crear EKS:
     * Etiqueta de propiedad heredada o específica de controlador: `kubernetes.io/cluster/<cluster-name>: shared`
     * Subredes públicas: `kubernetes.io/role/elb: 1`
     * Subredes privadas: `kubernetes.io/role/internal-elb: 1`

**Ejemplo de configuración de VPC (mediante eksctl):**

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

**Configuración de VPC mediante AWS CLI:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

Una NAT gateway es una posible ruta de salida a Internet. Los endpoints de VPC obligatorios, las imágenes replicadas y la conectividad privada pueden permitir la operación sin acceso a Internet. La ubicación en subredes privadas y la eliminación de la salida a Internet son decisiones independientes. Sustituya la VPC, las subredes y el CIDR del cliente de ejemplo por valores reales revisados.

</details>

3. ¿Qué separación de roles se aplica al configurar un plano de control de EKS convencional con workers de EC2?
   * A) Solo se necesita un rol de clúster
   * B) Solo se necesita un rol de nodo de EC2
   * C) Roles separados de clúster y de nodo de EC2
   * D) Reemplazar ambos por un rol de ejecución de Fargate

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Roles separados de clúster y de nodo de EC2**

El rol de clúster confía en `eks.amazonaws.com` y permite que EKS administre la infraestructura del clúster. EKS convencional necesita `AmazonEKSClusterPolicy` o permisos equivalentes. El rol de nodo de EC2 confía en `ec2.amazonaws.com` y se proporciona mediante un perfil de instancia. EKS configura el perfil de instancia para grupos de nodos administrados; el arranque del nodo no crea roles de IAM.

La base de EC2 es `AmazonEKSWorkerNodePolicy` y `AmazonEC2ContainerRegistryPullOnly`, o privilegio mínimo equivalente. También se requieren permisos de CNI; prefiera un rol independiente de IRSA/Pod Identity. Sin ello, el rol de nodo necesita los permisos de CNI. `AmazonEKS_CNI_Policy` de IPv4 no es una política de IPv6. Los permisos de controladores de almacenamiento, balanceador de carga y registro no se requieren universalmente en cada nodo.

Este ejemplo crea nuevos roles convencionales de clúster/nodo. Utilice una cuenta o rol autorizado y deténgase ante errores. Un conflicto de nombre no adjunta políticas al rol existente.

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

Crear solo un plano de control con `CreateCluster` todavía no requiere un rol de nodo de EC2. Añádalo para cómputo de EC2. Fargate utiliza un rol de ejecución de Pod distinto, separado de los permisos de AWS de la aplicación. Auto Mode necesita sus políticas adicionales de clúster/`sts:TagSession` y políticas mínimas de rol de nodo. Revise por separado permisos de identidad de aprovisionamiento como `iam:PassRole`.

[Requisitos de rol de nodo](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

</details>

4. ¿Cuál es el comando correcto para crear un clúster de EKS mediante eksctl?
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**Explicación:** El comando correcto para crear un clúster de EKS mediante eksctl es `eksctl create cluster --name my-cluster --region us-west-2`. Este comando crea un clúster de EKS con la configuración predeterminada en el nombre y la región especificados.

**Estructura de comandos de eksctl:**

* `eksctl`: Comando base
* `create`: Acción para crear un recurso
* `cluster`: Tipo de recurso que se va a crear (clúster)
* `--name my-cluster`: Especifica el nombre del clúster
* `--region us-west-2`: Especifica la región de AWS

**Comando básico de creación de clúster:**

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

**Creación de clúster mediante un archivo de configuración:**

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

**Problemas con las otras opciones:**

* `eksctl create-cluster`: Formato de comando incorrecto. eksctl utiliza espacios, no guiones (-), para separar comandos.
* `eksctl new cluster`: 'new' no es un comando válido de eksctl.
* `eksctl start cluster`: 'start' no es un comando válido de eksctl. Utilice los comandos de ciclo de vida documentados en lugar de inventar un verbo.

eksctl proporciona diversos comandos para administrar clústeres de EKS:

* `eksctl create cluster`: Crear un nuevo clúster
* `eksctl get cluster`: Enumerar clústeres
* `eksctl upgrade cluster`: Actualizar un clúster
* `eksctl delete cluster`: Eliminar un clúster
* `eksctl create nodegroup`: Agregar un grupo de nodos
* `eksctl scale nodegroup`: Escalar un grupo de nodos

</details>

5. ¿Qué versiones de Kubernetes puede elegir para un nuevo clúster de EKS?
   * A) Solo la versión upstream más reciente
   * B) Siempre exactamente la más reciente más dos versiones
   * C) Versiones ofrecidas con soporte estándar o extendido de EKS en la región de destino
   * D) Todas las versiones de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Versiones ofrecidas con soporte estándar o extendido de EKS en la región de destino**

Una versión secundaria de EKS recibe **14 meses de soporte estándar desde su fecha de lanzamiento de EKS**, seguidos de **12 meses de soporte extendido de pago**. La lista oficial el 12 de octubre de 2026 es soporte estándar **1.34–1.37** y soporte extendido **1.31–1.33**. EKS 1.37 estuvo disponible el 1 de octubre de 2026, después de su lanzamiento upstream del 26 de agosto. Consulte la región de destino para conocer las versiones disponibles para nuevos clústeres.

El soporte extendido está habilitado de forma predeterminada; la política de actualización y las fechas de fin de soporte pueden desencadenar actualizaciones automáticas del plano de control. Planifique por separado las actualizaciones de nodos/add-ons. Siga los avisos de fechas de soporte de AWS en lugar de considerar la ventana máxima de soporte como un motivo para retrasar actualizaciones.

Estos son ejemplos distintos para descubrimiento, generación de configuración, creación de AWS y actualización de un clúster existente. Prepare el destino autorizado, los roles, las subredes y el CIDR; no ejecute a ciegas ejemplos de creación y actualización como un único flujo de trabajo.

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

Las actualizaciones del plano de control deben avanzar una versión secundaria cada vez. Revise conjuntamente las características necesarias, el soporte restante y la compatibilidad de add-ons/cargas de trabajo. Pruebe la versión de destino en lugar de asumir que una versión anterior siempre es más segura. Buscar cadenas de versión en los metadatos de add-ons no sustituye el descubrimiento de versiones de clúster.

[Ciclo de vida de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

</details>

6. ¿Qué opción no aprovisiona por sí misma cómputo para una carga de trabajo de EKS?
   * A) Grupos de nodos administrados
   * B) Grupos de nodos autoadministrados
   * C) Perfiles de Fargate
   * D) Un namespace de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Un namespace de Kubernetes**

Un namespace organiza recursos de Kubernetes, pero no proporciona cómputo. Los grupos de nodos administrados de EC2, los nodos autoadministrados de EC2 y los perfiles de Fargate son rutas de cómputo válidas. EKS Auto Mode también aprovisiona nodos administrados, y Hybrid Nodes conecta capacidad local/perimetral administrada por el cliente. Estos mecanismos no utilizan todos la API de grupos de nodos administrados.


Los comandos de creación siguientes son alternativas para un clúster existente y nombres de grupo/perfil no utilizados. Sustituya todas las variables obligatorias por valores revisados. Compruebe la autorización de CNI/nodos y la conectividad de subredes privadas. Fargate requiere un rol de ejecución de Pod, Pods compatibles y subredes privadas; su perfil no crea Pods de aplicación.

**1. Grupos de nodos administrados:**

* **Características**:
  * AWS administra el aprovisionamiento y el ciclo de vida de los nodos
  * Creación y registro automáticos de instancias de EC2
  * Configuración automática de ASG (Auto Scaling Group)
  * Actualizaciones de versión de Kubernetes del nodo iniciadas por el operador
  * Reemplazo por estado de EC2; la reparación de nodos de EKS necesita sus señales/configuración de estado compatibles
  * Actualizaciones de AMI iniciadas por el operador mediante el flujo administrado
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
  * Puede utilizar AMI personalizadas o scripts de arranque
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
  * Entorno de ejecución de contenedores sin servidor
  * No se requiere administración de nodos
  * Asignación y facturación de recursos por Pod
  * Ejecución selectiva según namespaces y etiquetas específicos
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

**Comparación de cada opción:**

| Característica | Grupos de nodos administrados | Nodos autoadministrados | Fargate |
| --- | --- | --- | --- |
| Administración de infraestructura | AWS administra el flujo de reemplazo; los operadores configuran actualizaciones/escalado | Los operadores administran AMI, arranque y ciclo de vida | AWS administra los hosts; los usuarios administran aplicaciones, perfiles y solicitudes |
| Costo | Evalúe instancia, utilización, compromisos y operaciones | Evalúe la optimización junto con las operaciones | Compare tamaños de Pod asignados, tiempo de ejecución y restricciones |
| Escalado | Se requiere un escalador/política de nodos independiente | Se requiere automatización independiente | Proporciona cómputo para los Pods coincidentes; el escalado de réplicas de aplicación es independiente |

Los NodePools de Auto Mode y los perfiles de Fargate son recursos distintos de los grupos de nodos administrados de EC2. Fargate aún requiere la administración de cargas de trabajo, seguridad y disponibilidad, y no es universalmente más barato ni más caro.

</details>

7. ¿Cuál no es una familia de AMI optimizada para EKS publicada por AWS para nuevos nodos de EKS 1.36?
   * A) Amazon Linux 2023
   * B) Bottlerocket
   * C) Windows Server 2022
   * D) Ubuntu Core

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Ubuntu Core**

No considere Ubuntu Core como una AMI optimizada para EKS publicada por AWS. Las imágenes de Ubuntu Server de Canonical y las AMI creadas por clientes tienen publicadores, compatibilidad y rutas de soporte distintos; no son el mismo producto que Ubuntu Core.

**Opciones para este ejemplo**

- **AL2023**: Use una AMI optimizada para EKS y el arranque `nodeadm`. Compruebe la versión secundaria de Kubernetes, la arquitectura de CPU, la región y la compatibilidad de CNI.
- **Bottlerocket**: Un sistema operativo centrado en contenedores con mecanismos de configuración y actualización distintos de los nodos Linux de propósito general.
- **Windows**: Haga coincidir las versiones compatibles de host/contenedor de Windows Server y prepare los requisitos previos de redes, autenticación y cargas de trabajo del sistema de Windows. Este no es un ejemplo de Windows para Auto Mode/Fargate.

**AL2 es una fuente de migración para entornos heredados.** La publicación/el soporte de AMI AL2 optimizadas para EKS finalizó el 26 de noviembre de 2025; el soporte de SO AL2 finalizó el 30 de junio de 2026. El soporte extendido de Kubernetes de EKS no extiende el soporte de AL2. No recomiende AL2 para nuevos despliegues de EKS 1.36.

```bash
# Alternative examples; create only the reviewed group needed by your workload.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}"   --name al2023-nodes --managed --node-ami-family AmazonLinux2023 --node-private-networking

eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name bottlerocket-nodes --managed --node-ami-family Bottlerocket --node-private-networking

# Only after preparing the cluster for Windows:
eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name windows-nodes --managed --node-ami-family WindowsServer2022FullContainer --node-private-networking
```

También se pueden utilizar AMI personalizadas en plantillas de lanzamiento de grupos de nodos administrados. Fijar una AMI requiere verificar su SO/runtime, metadatos de clúster y configuración de arranque. Instalar únicamente `docker.io` en una imagen arbitraria de Ubuntu no produce un nodo de EKS funcional. Utilice una imagen de Canonical para la versión de EKS objetivo con una configuración revisada de eksctl/plantilla de lanzamiento. La pregunta avanzada distingue `ImageId` de plantilla de lanzamiento, `amiType` de grupo de nodos y las restricciones de combinación de datos de usuario.

Revise las actualizaciones de seguridad, el rendimiento medido de la carga de trabajo, la compatibilidad de Kubernetes/controladores, las operaciones y requisitos especiales como GPU al seleccionar una imagen.

[Transición de AL2](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html) · [AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [Requisitos previos de Windows](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)

</details>

8. ¿Cuáles son los valores predeterminados cuando se omite el acceso a endpoints en la API CreateCluster?
   * A) Público habilitado, privado deshabilitado
   * B) Solo privado
   * C) Ambos endpoints habilitados
   * D) El acceso no se puede cambiar después de la creación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Público habilitado, privado deshabilitado**

La API tiene de forma predeterminada el acceso público habilitado y el privado deshabilitado. Las rutas de creación con eksctl, CDK y consola pueden seleccionar explícitamente configuraciones diferentes; no es un valor predeterminado universal de herramientas. La configuración de acceso se puede cambiar después de la creación.

| Público | Privado | Ruta de acceso |
| --- | --- | --- |
| Activado | Desactivado | Endpoint público y publicAccessCidrs; considere también las direcciones reales de salida de nodo/CI |
| Activado | Activado | Ruta privada para solicitudes en la VPC; CIDR públicos permitidos externamente |
| Desactivado | Activado | Ruta privada desde la VPC o redes conectadas |
| Desactivado | Desactivado | Configuración no válida |

**El grupo de seguridad del clúster controla el tráfico del endpoint privado y de kubelet, no el acceso al endpoint público.** `publicAccessCidrs` se aplica solo al endpoint público. La autenticación/autorización sigue siendo obligatoria independientemente de la accesibilidad de red. Sustituya el CIDR IPv4 de ejemplo por la dirección de salida real del cliente aprobada.

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

Verifique que la actualización anterior sea `Successful` y que las redes de administración/CI puedan utilizar DNS privado, enrutamiento y acceso a API antes de deshabilitar el acceso público. No envíe de inmediato actualizaciones asíncronas superpuestas; establezca ambas marcas de acceso en una única solicitud.

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

El acceso privado a la API y la eliminación de la salida a Internet son decisiones de diseño independientes. Evalúe conjuntamente los controles de identidad, red y operación; el acceso privado por sí solo no garantiza seguridad ni disponibilidad. Considere VPN/Direct Connect/hosts de administración y los costos de conectividad. Los endpoints IPv6 y Hybrid Nodes tienen consideraciones adicionales de DNS/CIDR cubiertas en la guía oficial.

[Controles de acceso a endpoints de clúster](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)

</details>

9. ¿Qué NO es una consideración al seleccionar tipos de instancia para grupos de nodos en clústeres de Amazon EKS?
   * A) Requisitos de la carga de trabajo (CPU, memoria, almacenamiento)
   * B) Optimización de costos
   * C) El alias de contexto kubeconfig local
   * D) Generación de instancia (por ejemplo, t3 frente a t2)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) El alias de contexto kubeconfig local**

Un alias de kubeconfig es un nombre de cliente local y no cambia el rendimiento, los precios ni la disponibilidad de instancias. En cambio, son restricciones de selección importantes que un tipo se ofrezca en las AZ requeridas, la capacidad real y las cuotas de cuenta.

**Consideraciones reales al seleccionar tipos de instancia para grupos de nodos:**

1. **Requisitos de carga de trabajo (CPU, memoria, almacenamiento)**:
   * Seleccione tipos de instancia que coincidan con los requisitos de recursos de la aplicación
   * Cargas de trabajo intensivas en memoria: instancias optimizadas para memoria como r5, r6g
   * Cargas de trabajo intensivas en cómputo: instancias optimizadas para cómputo como c5, c6g
   * Cargas de trabajo equilibradas: instancias de propósito general como m5, m6g
   * Cargas de trabajo de GPU: instancias de cómputo acelerado como p3, g4dn
2. **Optimización de costos**:
   * Instancias bajo demanda frente a Spot
   * Reserved Instances o Savings Plans
   * Selección correcta del tamaño de instancia (evite el sobreaprovisionamiento)
   * Ahorro de costos mediante instancias Graviton basadas en ARM (por ejemplo, m6g, c6g)
3. **Generación de instancia**:
   * Compare el precio/rendimiento específico de la generación para la carga de trabajo real
   * Para familias con ráfagas, incluya el comportamiento de créditos de CPU y el rendimiento de referencia
   * Las generaciones más recientes proporcionan redes mejoradas, rendimiento de almacenamiento, etc.
4. **Requisitos de red**:
   * Compatibilidad con redes mejoradas (ENA, EFA, etc.)
   * Requisitos de ancho de banda de red
   * Límites de red relacionados con el número máximo de Pods por instancia
5. **Requisitos de almacenamiento**:
   * Si se necesita almacenamiento local de instancia (por ejemplo, instancias i3, d3)
   * Compatibilidad con optimización de EBS
   * Requisitos de rendimiento de almacenamiento e IOPS
6. **Arquitectura de CPU**:
   * x86 (Intel, AMD) frente a ARM (AWS Graviton)
   * Consideraciones de compatibilidad de aplicaciones

**Zonas de disponibilidad y despliegue de grupos de nodos:**

La cobertura de AZ requerida limita los tipos de instancia utilizables. Una oferta de catálogo no garantiza capacidad inmediata:

* Despliegue grupos de nodos en varias zonas de disponibilidad para alta disponibilidad
* Planifique la capacidad de nodos y la distribución de topología de Pods y después verifique la ubicación real
* Puede seleccionar todas las zonas de disponibilidad de la región o zonas de disponibilidad específicas

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

**Ejemplos de selección de tipo de instancia:**

1. **Servidores de aplicaciones web**:
   * Instancias de propósito general: t3.medium, m5.large
   * Rentables con rendimiento equilibrado
2. **Bases de datos**:
   * Instancias optimizadas para memoria: r5.xlarge, r6g.xlarge
   * Alta relación de memoria a CPU
3. **Trabajos de procesamiento por lotes**:
   * Instancias optimizadas para cómputo: c5.xlarge, c6g.xlarge
   * Alto rendimiento de CPU
4. **Cargas de trabajo de aprendizaje automático**:
   * Instancias de GPU: p3.2xlarge, g4dn.xlarge
   * Capacidades de cómputo acelerado

Las familias anteriores son ejemplos, no un catálogo actual de productos ni una clasificación de rendimiento medida. Revise en conjunto la carga de trabajo, el precio, la arquitectura, los controladores y las ofertas/capacidad en las AZ requeridas.

</details>

10. ¿Cuál es el comando correcto para configurar kubectl después de crear un clúster de Amazon EKS?
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**Explicación:** El comando correcto para configurar kubectl después de crear un clúster de Amazon EKS es `aws eks update-kubeconfig --name my-cluster --region us-west-2`. Este comando utiliza el módulo EKS de AWS CLI para actualizar el archivo kubeconfig del clúster especificado.

**Proceso de configuración de kubectl:**

1. **Actualización del archivo kubeconfig**:
   * El archivo kubeconfig almacena la información de configuración que kubectl necesita para comunicarse con clústeres de Kubernetes.
   * El orden de selección es `--kubeconfig` explícito, la primera ruta `KUBECONFIG` y después `~/.kube/config`.
   * El comando combina la configuración de clúster/autenticación exec y cambia el contexto actual en el archivo seleccionado; no concede permisos de clúster.
2. **Componentes del comando**:
   * `--name`: Nombre de clúster de EKS
   * `--region`: Región de AWS donde se encuentra el clúster
   * `--kubeconfig` (opcional): Ruta de archivo kubeconfig personalizada
   * `--role-arn` (opcional): Rol de IAM que se utilizará para el acceso al clúster
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
5.  **Verificar la configuración**:

    ```bash
    # Check current context
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config current-context

    # List all contexts
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config get-contexts

    # Test cluster connection
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" cluster-info
    ```

**Problemas con las otras opciones:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: Este comando no existe. No hay ningún subcomando `get-kubeconfig` en AWS CLI.
* `kubectl config set-cluster my-cluster --region us-west-2`: Este comando tiene sintaxis incorrecta. `kubectl config set-cluster` no admite la marca `--region` y no configura automáticamente la información de autenticación necesaria para clústeres de EKS.
* `eksctl configure kubectl --name my-cluster --region us-west-2`: Este comando no existe. eksctl no tiene un subcomando `configure kubectl`. Al crear un clúster con eksctl, kubeconfig se configura automáticamente, pero para clústeres existentes use `aws eks update-kubeconfig` o `eksctl utils write-kubeconfig`.

**Escritura de configuración para un clúster existente con eksctl:**

Para un clúster existente, escriba su configuración sin crear otro clúster:

```bash
eksctl utils write-kubeconfig --cluster my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

Esto escribe kubeconfig para el clúster existente. Verifique por separado la autenticación de IAM y la autorización de entrada de acceso/RBAC. La creación del clúster también escribe kubeconfig de forma predeterminada, salvo que se deshabilite.

**Administración de varios clústeres:**

Al administrar varios clústeres de EKS, puede agregarlos al archivo kubeconfig ejecutando el comando `aws eks update-kubeconfig` para cada clúster:

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

### Ejercicio 1: Crear un clúster de EKS mediante eksctl

**Escenario:** prepare un clúster convencional de grupos de nodos administrados de EC2 para un equipo de desarrollo. Este es un diseño de formación, no evidencia de preparación de producción probada ni de un resultado de costo medido.

**Requisitos:** use dos AZ, inicialmente dos nodos AL2023 `t3.medium`, límites de escalado de 2–5, redes privadas de nodos y ambos endpoints de API con un CIDR público aprobado. Los límites por sí solos no instalan un autoscaler. Compruebe los créditos de CPU de instancias con ráfagas, la memoria, la capacidad de IP, las cuotas y las necesidades reales de carga de trabajo antes de elegir `t3.medium`.

<details>
<summary>Mostrar respuesta</summary>

**1. Prepare las herramientas y la identidad.** Use las instrucciones de instalación específicas de arquitectura y con suma de comprobación de la [Parte 1](../../eks/02-eks-cluster-creation-part1.md). Este ejemplo se revisó con EKS 1.36 y eksctl 0.230.0; compruebe las versiones de EKS disponibles en la región y las versiones compatibles de cliente/add-on antes de ejecutarlo. `kubectl` debe cumplir los límites de diferencia de versiones. Utilice un rol de IAM de operador aprobado y existente que su inicio de sesión pueda asumir; los permisos de aprovisionamiento y el acceso a Kubernetes son independientes.

**2. Genere y revise una configuración local privada.** El nombre generado es para un nuevo clúster de formación. El CIDR público debe ser su rango de salida permitido real. Las dos AZ son ejemplos para `us-west-2`, sujetos a ofertas y capacidad.

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

Esto concede al operador nombrado acceso de cluster-admin específicamente para el laboratorio y deshabilita el acceso automático de administrador del creador. No crea el rol de operador ni concede a quien llama permiso para asumirlo. eksctl crea los roles de clúster/nodo requeridos; revise el ámbito de sus políticas generadas. La base convencional puede colocar permisos de VPC CNI en el rol de nodo. Para un aislamiento más fuerte de las cargas de trabajo, configure un rol `aws-node` dedicado mediante la guía oficial de IAM de CNI. No agregue permisos amplios de envío de imágenes, DNS, almacenamiento, balanceador de carga o registro a todos los nodos simplemente porque esos add-ons podrían utilizarse más adelante.

**3. Aprovisione solo después de revisar la configuración y los costos.** La topología predeterminada de nueva VPC puede crear NAT y otra infraestructura facturable. `eksctl` utiliza CloudFormation para recursos de VPC/subred/grupo de seguridad/rol/clúster/grupo de nodos. Los errores pueden dejar recursos parciales; inspeccione los eventos de stack en lugar de asumir una limpieza completa automática.

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

**4. Verifique el estado, acceso y límites de escalado reales.** Espere los estados `ACTIVE` de grupo de nodos/clúster y nodos `Ready`, inspeccione Pods de sistema no saludables y verifique la ubicación esperada en AZ. Una solicitud de creación correcta o una lista de RBAC por sí sola no establece un clúster seguro y funcional.

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

**5. Agregue solo los componentes necesarios.** Cluster Autoscaler requiere la configuración de IAM/cuenta de servicio/detección con alcance de la pregunta avanzada 2; los límites no reaccionan por sí solos a la demanda de carga de trabajo. `kubectl top` requiere un Metrics Server instalado y saludable. En la base auditada de Metrics Server 0.9.0, Kubernetes 1.34+ es compatible; verifique la versión realmente instalada. Mida el uso representativo antes de afirmar ahorros de costos o un dimensionamiento correcto.

**6. Limpie este clúster de formación.** Primero elimine cualquier Service/Ingress de tipo LoadBalancer creado por el laboratorio y espere que sus controladores liberen recursos de AWS; inspeccione las políticas de reclamación de PVC y los volúmenes retenidos. Este ejercicio no crea recursos de aplicación de ese tipo. Después elimine solo el clúster registrado:

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

Compruebe después CloudFormation e inventarios de recursos de AWS para eliminaciones fallidas, volúmenes retenidos y roles/endpoints creados independientemente. Conserve el registro de configuración/ARN hasta confirmar la limpieza; elimine localmente el directorio kubeconfig temporal cuando ya no sea necesario.

</details>

### Ejercicio 2: Crear un clúster de EKS mediante AWS Management Console

**Escenario:** revise un diseño convencional de grupos de nodos administrados que podría orientar un despliegue de producción posterior. Su dimensionamiento de carga de trabajo, enrutamiento, IAM, disponibilidad, actualizaciones y recuperación siguen siendo supuestos específicos del entorno que requieren pruebas. Este recorrido no se aprovisionó ni sometió a pruebas de carga durante la auditoría.

<details>
<summary>Mostrar respuesta</summary>

**1. Prepare roles de IAM independientes.**

- Rol de clúster: confía en `eks.amazonaws.com` y adjunta `AmazonEKSClusterPolicy`.
- Rol de nodo de EC2: confía en `ec2.amazonaws.com`, adjunta `AmazonEKSWorkerNodePolicy` y `AmazonEC2ContainerRegistryPullOnly`. Otorgue a VPC CNI su propio rol de IRSA/Pod Identity cuando sea compatible. Si utiliza deliberadamente el respaldo más simple de rol de nodo IPv4, adjunte explícitamente `AmazonEKS_CNI_Policy` y documente la compensación de permisos compartidos.
- Identidad de aprovisionamiento/operador: use permisos de IAM aprobados y con ámbito de recursos, y `iam:PassRole` para estos roles. Agregue una entrada de acceso de EKS para el rol de operador existente con la política de acceso requerida del laboratorio. Crear kubeconfig por sí solo no concede autorización de Kubernetes.

**2. Revise VPC y subredes.** El siguiente ejemplo oficial sigue siendo una referencia utilizable; la fecha de su URL no es una versión de EKS:

```text
https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
```

Lea la plantilla de CloudFormation antes de crear un stack de formación con un nombre único. Sus valores predeterminados crean una VPC con **dos subredes públicas y dos privadas en dos AZ, una Internet gateway y dos NAT gateways/EIP**. Por lo tanto, es un diseño respaldado por NAT con Internet saliente, no un clúster privado sin salida. Revise la superposición de CIDR, AZ, capacidad de IP y cargos de NAT en lugar de conservar valores predeterminados para producción.

Registre `VpcId`, `SubnetIds` y `SecurityGroups`. `SubnetIds` contiene **subredes públicas y privadas**; inspeccione cada tabla de rutas y seleccione las subredes privadas reales para los nodos. El grupo de seguridad personalizado de salida no prueba que existan todas las reglas de comunicación requeridas. Revise el grupo de seguridad del clúster de EKS, los grupos adicionales y las reglas de comunicación entre plano de control/nodos.

**3. Cree un clúster convencional.** En la consola de EKS, elija la ruta de configuración personalizada y deshabilite Auto Mode para este ejercicio. Seleccione una versión disponible y compatible en soporte estándar de EKS (1.36 es el ejemplo auditado), el rol de servicio del clúster y la VPC/subredes revisadas.

- Seleccione autenticación de entrada de acceso a API y conceda acceso adecuado al operador nombrado; no se base en un valor predeterminado de administrador del creador sin explicación.
- Para acceso solo de API privada, verifique primero el enrutamiento/DNS privado de la red de administración. Como alternativa, habilite el acceso público y privado y limite `publicAccessCidrs` al rango de salida de administración aprobado.
- Mantenga add-ons compatibles de VPC CNI, kube-proxy y CoreDNS para este clúster de EC2 convencional; revise su configuración/permisos. Habilite los registros de plano de control necesarios y considere los cargos de registro.
- Revise y cree el clúster; después espere a `ACTIVE`. La duración de creación es variable; un número de minutos citado no es una prueba de finalización.

**4. Agregue un grupo de nodos administrados.** Seleccione el rol de nodo de EC2, AMI AL2023 x86_64 y un tipo de instancia compatible como el ilustrativo `m5.large`. El ejemplo usa un disco raíz de 50 GiB, tamaño deseado 3, mínimo 2, máximo 5 y las subredes privadas revisadas. Son ejemplos de dimensionamiento, no recomendaciones de producción. Configure acceso, IMDS y cifrado de almacenamiento según sea necesario; espere que el grupo de nodos alcance `ACTIVE` y los nodos estén `Ready`.

**5. Verifique el acceso e inspeccione los grupos de seguridad reales de AWS.** Use el nombre de clúster registrado en la consola y su rol de operador aprobado:

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

**6. Ejercicio opcional de NetworkPolicy.** Primero verifique que el CNI seleccionado y su configuración apliquen NetworkPolicy. La compatibilidad de políticas de AWS VPC CNI debe estar habilitada y ser compatible con la configuración de nodo/SO. La siguiente denegación predeterminada solo de entrada se limita a un nuevo namespace de laboratorio vacío; no deniega la salida ni prueba la aplicación de políticas simplemente porque `apply` tenga éxito.

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

Pruebe el tráfico permitido y denegado con Pods de prueba dedicados y agregue las políticas de permiso requeridas por la aplicación antes de utilizar este patrón para cargas de trabajo reales. No lo aplique a un namespace `default` compartido existente. Elimine el namespace aislado al finalizar:

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

**7. Limpieza de consola:** elimine las cargas de trabajo de laboratorio y espere que se liberen los recursos de nube asociados; luego elimine el grupo de nodos administrados de este laboratorio, espere su eliminación y elimine el clúster de laboratorio. Elimine el stack de CloudFormation de VPC del laboratorio solo después de que desaparezcan sus recursos de EKS y dependencias externas. Elimine únicamente roles/endpoints de IAM creados exclusivamente para este laboratorio; conserve los recursos compartidos e inspeccione cualquier recurso fallido o retenido. Esta revisión no ejecutó esas operaciones.

</details>

## Temas avanzados {#advanced-topics}

Las siguientes son preguntas sobre temas avanzados relacionados con la creación de clústeres de Amazon EKS. Esta sección evalúa su comprensión de conceptos avanzados y prácticas recomendadas para la creación de clústeres de EKS.

1. ¿Cuál es un beneficio principal de las plantillas de lanzamiento personalizadas para grupos de nodos administrados de EKS EC2?
   * A) Creación de clúster garantizada más corta
   * B) Datos de usuario de nodo y configuración de volumen personalizados
   * C) Instalación de complementos de plano de control
   * D) Actualizaciones automáticas de todos los nodos existentes a cada AMI recién publicada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Datos de usuario de nodo y configuración de volumen personalizados**

Las plantillas de lanzamiento personalizan los **grupos de nodos administrados de EC2**, incluido el almacenamiento, los metadatos de instancia y los datos de usuario específicos del SO. No configuran el plano de control de EKS ni los nodos de EKS Auto Mode.

**Datos de usuario de AL2023:** use datos MIME multipartes. Con una AMI seleccionada por EKS (sin `ImageId` en la plantilla), EKS proporciona/combina la configuración de nodo. Con un ID de AMI personalizado, proporcione el `NodeConfig` completo descrito en la pregunta avanzada 5. Los servicios systemd de AL2023 ejecutan `nodeadm`; no llame a `/etc/eks/bootstrap.sh`, no ejecute de nuevo `nodeadm init` ni inicie kubelet manualmente. El software adicional debe ser compatible con el SO seleccionado y tener una fuente de paquetes confiable y accesible.

Esta personalización mínima es para el caso de AMI AL2023 seleccionada por EKS; solo crea un directorio de aplicación:

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

**Almacenamiento:** lo siguiente es un fragmento `LaunchTemplateData` válido. Confirme el nombre del dispositivo raíz de la AMI. Adjuntar un volumen no lo formatea ni lo monta. Ambos volúmenes de ejemplo están cifrados y se eliminan con la instancia; use un PV administrado por CSI y una política de reclamación/copia de seguridad adecuada para datos de aplicación que deban sobrevivir al reemplazo de nodos.

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

**Redes y metadatos:** sustituya el grupo de seguridad de ejemplo por uno cuyas reglas permitan el tráfico requerido de plano de control, nodo, DNS y carga de trabajo. Cuando se proporcionan grupos de seguridad personalizados, EKS **no** agrega automáticamente el grupo de seguridad del clúster. Especifique grupos de seguridad en el nivel de instancia o de interfaz de red, no en ambos.

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

El límite de saltos de 1 supone que los Pods utilizan IRSA o EKS Pod Identity en lugar de credenciales de nodo. Las cargas de trabajo que requieren acceso IMDSv2 desde un contenedor pueden necesitar un límite de saltos de 2. Ni esta configuración ni IMDSv2 crean aislamiento para Pods `hostNetwork`. Múltiples interfaces, ubicación y dispositivos de almacenamiento de instancia requieren tipos de instancia compatibles y las restricciones de plantilla de lanzamiento de EKS; no son opciones universalmente intercambiables.

**Cree el grupo de nodos:** elija la configuración de eksctl o el ejemplo de AWS CLI después de revisar ID, permisos y rutas de red reales. Son alternativas, no instrucciones secuenciales:

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

Mantenga `SubnetId` e `IamInstanceProfile` fuera de la plantilla de lanzamiento: las subredes y el rol de IAM de nodo pertenecen a la solicitud de grupo de nodos. Con una plantilla de lanzamiento, no establezca también `diskSize` ni `remoteAccess` de grupo de nodos. Establezca los tipos de instancia en la plantilla **o** en la solicitud de grupo de nodos. Cuando existe `ImageId`, omita `amiType`, `releaseVersion` y `version` de grupo de nodos, y verifique la compatibilidad kubelet/plano de control de la AMI personalizada.

Un `ImageId` explícito fija una AMI; una plantilla sin él puede utilizar una AMI seleccionada por EKS. Ningún caso actualiza automáticamente los nodos existentes cada vez que se publica una AMI. Actualizar una plantilla personalizada requiere una nueva versión de la **misma** plantilla y una actualización explícita de grupo de nodos, que reemplaza instancias.

Referencias: [restricciones de plantilla de lanzamiento](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html), [campos CreateNodegroup](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [inicialización de AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html).

</details>

2. ¿Qué enfoque es insuficiente por sí solo para optimizar los costos de EKS?
   * A) Utilizar Spot para cargas de trabajo tolerantes a interrupciones
   * B) Configurar y autorizar Cluster Autoscaler
   * C) Elegir la generación de instancia más reciente para cada carga de trabajo sin medición
   * D) Evaluar Fargate selectivamente frente a las necesidades de carga de trabajo y el costo total

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Elegir la generación de instancia más reciente para cada carga de trabajo sin medición**

Elegir cada nodo únicamente porque pertenece a la generación más reciente no constituye un análisis de costos suficiente. Compare la arquitectura, rendimiento, latencia, memoria, disponibilidad regional y tolerancia a interrupciones de la carga de trabajo. Una generación más reciente puede ser más económica; ni la más reciente ni la más antigua es siempre más barata para el mismo trabajo útil.

1. **Spot y diversificación:** AWS anuncia descuentos de hasta el 90 % frente a On-Demand para Spot; este es un posible descuento de precios, no un ahorro medido o garantizado para este laboratorio. Considere las interrupciones y la capacidad de reemplazo. Para Cluster Autoscaler, los tipos mezclados en un grupo de nodos deben tener la misma forma de CPU/memoria/GPU porque la simulación de programación utiliza el primer tipo. Verifique por separado cualquier dependencia de disco local.

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

2. **Cluster Autoscaler:** los tamaños mínimo/máximo solo establecen límites de escalado. Instale y autorice un controlador para cambiar la capacidad deseada en respuesta a Pods no programables y capacidad que se pueda eliminar. No conceda a cada nodo permisos amplios de autoscaling. Antes de esta **nueva instalación**, prepare una cuenta de servicio `kube-system/cluster-autoscaler` con un rol de IRSA dedicado (confianza OIDC limitada a esa cuenta de servicio) o una configuración compatible de Pod Identity. Limite las escrituras de escalado a los Auto Scaling groups del clúster previsto y etiquete esos grupos con `k8s.io/cluster-autoscaler/enabled=true` y `k8s.io/cluster-autoscaler/<cluster-name>=owned`. Las etiquetas de recursos de grupo de nodos por sí solas no demuestran que la detección de ASG esté configurada.

La versión secundaria del controlador debe coincidir con el clúster. El chart 9.59.0 usa de forma predeterminada el controlador 1.35.0, por lo que este ejemplo de EKS 1.36 selecciona explícitamente 1.36.1. Otras versiones de clúster necesitan una versión de controlador coincidente. Confirme que no existe una instalación de CA que administre los mismos grupos.

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

3. **Fargate y dimensionamiento adecuado:** Fargate reduce el trabajo de administración de hosts, pero cobra por recursos asignados y tiempo de ejecución, no solo por CPU medida. Haga coincidir perfiles con Pods compatibles y redes de subred privada; compare el costo total con EC2. `kubectl top` requiere Metrics Server y una muestra corta no es un plan de capacidad.
4. **Graviton:** pruebe imágenes y dependencias ARM64 antes de crear un grupo de nodos ARM. Una afirmación de “hasta un 40 % mejor precio/rendimiento” específica de una generación no es una reducción universal del 40 % de la factura ni una garantía de rendimiento igual.

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

5. **Compromisos:** Reserved Instances y Savings Plans pueden reducir costos de uso predecible que cumpla los requisitos. Los ahorros anunciados de hasta el 72 % dependen del producto, plazo, opción de pago y uso; los compromisos sin uso pueden eliminar los ahorros.
6. **Solicitudes y límites:** mida cargas de trabajo representativas antes de elegir valores. Las solicitudes afectan la programación y las decisiones de autoscaler; límites demasiado pequeños pueden causar limitación de CPU o terminación OOM. Estos son valores ilustrativos por contenedor:

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

7. **Asignación de costos:** use Cost Explorer y herramientas/informes de asignación configurados. Las etiquetas de Kubernetes no se convierten automáticamente en etiquetas de asignación de costos activadas de AWS. Incluya plano de control, tarifas de Auto Mode cuando corresponda, almacenamiento, balanceadores de carga, NAT, transferencia y costos de registro.

Referencias: [CA en EKS](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html), [chart de CA](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler), [CA 1.36.1](https://github.com/kubernetes/autoscaler/releases/tag/cluster-autoscaler-1.36.1), [precios Spot](https://aws.amazon.com/ec2/spot/), [precios Fargate](https://aws.amazon.com/fargate/pricing/), [Graviton](https://aws.amazon.com/ec2/graviton/), [Savings Plans](https://aws.amazon.com/savingsplans/).

</details>

3. ¿Qué diseño satisface tanto el acceso solo privado a la API de Kubernetes como la ausencia de Internet saliente desde nodos/Pods?
   * A) API privada, subredes de nodo privadas sin salida a Internet, endpoints de servicio requeridos y una ruta de administración privada
   * B) Solo nodos privados, dejando sin cambios toda la configuración de API y salida
   * C) Deshabilitar endpoints de API pública y privada de Kubernetes
   * D) Deshabilitar la API pública mientras se mantiene salida NAT sin restricciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) API privada, subredes de nodo privadas sin salida a Internet, endpoints de servicio requeridos y una ruta de administración privada**

Separe dos decisiones: **quién puede alcanzar la API de Kubernetes** y **a dónde pueden enviar tráfico los nodos/Pods**. Una API solo privada no elimina rutas NAT, bloquea la salida de cargas de trabajo ni garantiza que todos los paquetes permanezcan en una VPC. Las redes conectadas pueden alcanzar la API privada cuando el enrutamiento, DNS, grupos de seguridad y autorización lo permiten.

Para esta pregunta, el requisito es tanto acceso de API solo privado como nodos/Pods sin Internet saliente. Habilite el endpoint privado, deshabilite el endpoint público, use subredes de nodo privadas sin ruta de salida a Internet y proporcione los endpoints de servicio, las imágenes de registro y la ruta de administración que necesitan las cargas de trabajo.

**Transición de endpoint:** primero habilite el acceso privado, espere que esa actualización tenga éxito y pruebe el acceso `kubectl` autenticado desde la red privada prevista. Solo entonces utilice la alternativa independiente solo privada a continuación. Compruebe la actualización devuelta hasta que sea `Successful` y después vuelva a comprobar el acceso. El endpoint público se restringe mediante `publicAccessCidrs`, no el grupo de seguridad del clúster; este último gobierna el tráfico de endpoint privado.

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

**Ubicación de nodos:** este fragmento utiliza una VPC existente y subredes privadas; reemplace los ID y verifique las rutas antes de usarlo. No crea endpoints de VPC ni elimina rutas NAT existentes. Ejecutar eksctl desde una estación de trabajo no relacionada con solo Internet no proporcionará acceso a una API de Kubernetes solo privada.

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

**Conectividad de servicios de AWS:** los siguientes ejemplos de ECR y S3 son solo parte del diseño. Revise primero los endpoints existentes para evitar conflictos de DNS privado duplicados. Los endpoints de interfaz necesitan DNS privado y entrada HTTPS de clientes previstos; el endpoint de gateway de S3 necesita las tablas de rutas privadas y políticas de endpoint/bucket adecuadas.

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

| Dependencia | Conectividad privada cuando no existe ruta a Internet |
| --- | --- |
| Descargas de imágenes de ECR privado | `ecr.api`, `ecr.dkr` y gateway de S3; copie imágenes públicas a un registro privado accesible |
| API de EC2 utilizadas por nodos/CNI | `ec2`, permisos adecuados y política de endpoint |
| Credenciales de IRSA | `sts` regional; configure los SDK para usar el endpoint regional |
| Descubrimiento OIDC/JWKS desde dentro de la VPC | `oidc-eks`, por ejemplo al configurar el proveedor OIDC de IAM; separado de STS |
| Credenciales de EKS Pod Identity | `eks-auth` más una configuración/agente de Pod Identity compatible |
| API de administración de EKS | `eks`; esto no reemplaza el endpoint privado de API de Kubernetes |
| Registros, autoscaling, balanceo de carga, SSM | Endpoints y permisos para los servicios realmente utilizados; SSM también necesita su conectividad de mensajería |

Los servicios de endpoint y los nombres DNS varían según la región/partición. Compruebe todas las dependencias de cada carga de trabajo, incluidos registros de imágenes, descargas de paquetes, API externas y características de add-ons. Un endpoint para un servicio de AWS no sustituye Internet de propósito general.

**Administración:** use conectividad VPN/Direct Connect enrutada, un host controlado con acceso privado o una sesión SSM configurada adecuadamente. Un bastion no necesita inherentemente una IP pública. SSM aún necesita su agente, autorización de IAM y conectividad de servicio.

Una API privada con nodos privados respaldados por NAT también es un diseño de EKS válido, pero no satisface el requisito de esta pregunta de no tener salida a Internet. De forma similar, una ruta pública de una subred por sí sola no demuestra que un nodo individual sea accesible desde Internet; importan la asignación de direcciones y los controles de seguridad.

Referencias: [requisitos de clúster privado](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [acceso a endpoint de API](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html), [EKS PrivateLink y OIDC](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html).

</details>

4. ¿Cuál NO es el mecanismo de grupos de nodos administrados de EKS para aplicar una nueva AMI de nodo?
   * A) Reemplazar instancias mediante una actualización gradual administrada
   * B) Crear y validar un grupo de nodos blue/green independiente
   * C) Actualizar paquetes de SO en instancias en ejecución en lugar de reemplazarlas
   * D) Validar una AMI nueva en un grupo de nodos canary pequeño antes de un reemplazo más amplio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Actualizar paquetes de SO en instancias en ejecución en lugar de reemplazarlas**

Las actualizaciones de grupos de nodos administrados de EKS reemplazan instancias de EC2. Actualizar paquetes de SO en las instancias en ejecución no es el mecanismo de actualización de AMI administrado. Evite la afirmación ambigua de que no se admiten todas las “actualizaciones in situ”: AWS también utiliza esa frase para conservar el recurso de grupo de nodos al cambiar su versión de AMI de plantilla de lanzamiento, lo que aun así reemplaza instancias.

**Actualización gradual:** `DEFAULT` crea capacidad de reemplazo antes de retirar nodos antiguos; `MINIMAL` puede terminar nodos antiguos seleccionados antes de crear reemplazos. `maxUnavailable` tiene como valor predeterminado 1, pero es configurable, por lo que no siempre es exactamente un nodo a la vez. Compruebe cuotas, capacidad de AZ, ubicación de Pods y estrategia de actualización. Con una AMI personalizada, seleccione explícitamente la nueva versión de la misma plantilla de lanzamiento; el siguiente comando muestra en cambio el caso de AMI seleccionada por EKS:

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

Registre el ID de actualización devuelto y repita `describe-update` hasta un estado terminal. El envío correcto de una API no es la finalización. Investigue los errores informados antes de continuar. Un PDB que impide la expulsión puede provocar `PodEvictionFailure`; no lo omita con `--force` simplemente para terminar el comando.

**Blue/green:** cree un grupo de nodos AL2023 compatible e independiente, pruebe la programación y preparación de cargas de trabajo y después migre gradualmente. Conserve la capacidad anterior hasta que se satisfagan las comprobaciones de aplicación, restricciones de volumen/AZ y requisitos de reversión. Solo enumerar etiquetas de nodo no es validación, y el tráfico sigue los endpoints/Pods de Service en lugar de los nombres de grupo de nodos. No elimine automáticamente el grupo anterior inmediatamente después de crear el nuevo.

**Canary:** use un grupo pequeño, etiquetado y con taints independientes. El taint desalienta que Pods no relacionados lleguen allí; solo la carga de trabajo de prueba lo selecciona y tolera. Los DaemonSets del sistema aún pueden ejecutarse cuando sus tolerations lo permiten. Esta es una configuración ilustrativa para un clúster de prueba existente:

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

Cree un namespace `upgrade-lab` no utilizado en su contexto de prueba dedicado antes de aplicar este Deployment de demostración completo. Un canary real también debe ejercitar las dependencias propias de la aplicación y el tráfico representativo; este Pod NGINX solo comprueba la programación y preparación básicas.

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

**Presupuestos de interrupción y capacidad:** este ejemplo independiente supone una carga de trabajo `my-app` real en `app-namespace`, normalmente con al menos tres réplicas listas. No es el PDB del canary de una sola réplica anterior:

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

Un PDB limita las expulsiones voluntarias gestionadas mediante la API de expulsión; no garantiza disponibilidad, no evita fallos de hardware ni impide la eliminación directa de Pod/Deployment. `minAvailable: 2` bloquea la expulsión cuando solo hay dos Pods coincidentes saludables. Verifique la capacidad sobrante, topología, probes, comportamiento de terminación y recuperación de fallos. Los planes blue/green o canary no demuestran por sí solos una reversión segura, especialmente para datos con estado.

Referencias: [comportamiento de actualización administrada](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [migración de AL2023](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html), [presupuestos de interrupción de Pods](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/).

</details>

5. ¿Qué acción no forma parte del arranque de un worker EC2 AL2023 optimizado para EKS?
   * A) Configurar kubelet/runtime de contenedor
   * B) Instalar componentes de plano de control administrados por AWS en el worker
   * C) Configurar autenticación/conectividad de cliente de nodo
   * D) Registrar el nodo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Instalar componentes de plano de control administrados por AWS en el worker**

Los workers no instalan el servidor de API, etcd, controller manager ni scheduler; estos pertenecen al plano de control administrado por AWS. **CoreDNS en EKS convencional es un add-on de clúster del plano de datos, no uno de esos componentes de plano de control.**

Las AMI AL2023 optimizadas para EKS usan `nodeadm` para configurar containerd y kubelet. `nodeadm-config` establece la configuración base antes de los datos de usuario, y `nodeadm-run` completa la configuración e inicia los daemons posteriormente. La AMI ejecuta esto automáticamente; no invoque `nodeadm init` otra vez desde los datos de usuario. El flujo `/etc/eks/bootstrap.sh` de AL2 no es la ruta de arranque actual de AL2023.

**Separe la unión de nodo de las redes de clúster**

1. Aprovisione el rol de IAM/perfil de instancia de nodo y la autorización de acceso de nodo necesaria antes del lanzamiento. El arranque no crea roles de IAM. Utilice la ruta kubeconfig/autenticación generada por la AMI en lugar de un kubeconfig manual que asuma innecesariamente de nuevo el rol propio de la instancia.
2. Kubelet registra el nodo. La preparación depende del estado del runtime/CNI y de la conectividad de clúster.
3. EKS convencional despliega/administra `aws-node`, `kube-proxy` y CoreDNS como add-ons de clúster. El arranque del host no instala todos estos add-ons; no sobrescriba la configuración de CNI con un archivo inventado.
4. No falsifique manualmente etiquetas propiedad del proveedor `eks.amazonaws.com/nodegroup` o `topology.kubernetes.io/zone`. Administre etiquetas/taints personalizados mediante la configuración de grupo de nodos/provisionador.

**Ejemplo de entrada NodeConfig**

Lo siguiente se ejecuta en la estación de trabajo de administración para generar datos de usuario a partir de los metadatos reales de un clúster IPv4 existente. Es para AMI personalizadas/nodos autoadministrados basados en AL2023 optimizados para EKS revisados; los grupos de nodos administrados sin ID de AMI personalizada usan la generación/combinación de metadatos de EKS. `NodeConfig` es configuración de arranque de host, no un recurso normal de Kubernetes que se deba enviar con `kubectl apply`.

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

No codifique de forma rígida una única IP de servicio DNS ni un valor maxPods para cada nodo. Siga las reglas documentadas de CIDR de servicio de clúster, configuración de instancia/CNI/prefijo y dimensionamiento. Estos comandos de inspección describen configuraciones convencionales de EC2; los componentes administrados difieren en Auto Mode/Fargate.

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" describe node "${EXAMPLE_NODE:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get daemonset aws-node kube-proxy
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get deployment coredns
```

La unión de nodos, la ejecución de daemons, el comportamiento de red y los registros de runtime no se ejecutaron ni recopilaron durante esta auditoría.

[Ciclo de vida de AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [API NodeConfig](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)

</details>

## Referencias oficiales

- [Versiones compatibles de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Rol de IAM de nodo EKS](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [Rol de IAM de VPC CNI](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [Requisitos previos de NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Requisitos de Metrics Server](https://github.com/kubernetes-sigs/metrics-server#requirements)
- [Esquema de configuración de eksctl](https://schema.eksctl.io/)
