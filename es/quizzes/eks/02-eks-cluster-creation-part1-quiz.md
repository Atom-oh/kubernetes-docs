# Cuestionario sobre creación de clusters EKS - Parte 1

Este cuestionario evalúa tu comprensión de conceptos, herramientas y prácticas recomendadas relacionadas con la creación de clusters de Amazon EKS. Cubre temas como métodos de creación de clusters, configuración de VPC y configuración de node groups.

## Preguntas de conceptos básicos

1. ¿Cuál NO es una herramienta que se puede usar para crear un cluster de Amazon EKS?
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) kubectl**

**Explicación:** kubectl es una herramienta de línea de comandos para administrar clusters de Kubernetes, pero no se puede usar para crear clusters de EKS. kubectl se usa para conectarse a un cluster de Kubernetes existente y administrar recursos.

Las herramientas que se pueden usar para crear clusters de Amazon EKS incluyen:

1. **AWS Management Console**:
   * Crear clusters de EKS mediante una interfaz web.
   * Adecuado para principiantes, ya que permite la configuración visual de los componentes del cluster.
   * Guía el proceso de creación del cluster mediante un asistente paso a paso.
2.  **AWS CLI**:

    * Crear clusters de EKS desde la línea de comandos.
    * Usa el comando `aws eks create-cluster`.
    * Adecuado para scripts y automatización.

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * Una herramienta de línea de comandos diseñada específicamente para la creación de clusters de EKS.
    * Una herramienta de código abierto desarrollada por Weaveworks que simplifica la creación y administración de clusters de EKS.
    * Puede crear un cluster con un solo comando.

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Herramientas de Infrastructure as Code (IaC)**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    Estas herramientas permiten definir e implementar clusters de EKS como código.

kubectl se usa para administrar recursos de Kubernetes (pods, services, deployments, etc.) después de crear un cluster. Para conectarte a un cluster de EKS, primero debes actualizar la configuración de kubectl usando el comando `aws eks update-kubeconfig`.

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

Después de eso, puedes usar kubectl para administrar los recursos del cluster.

</details>

2. ¿Qué componente de VPC debe especificarse al crear un cluster de Amazon EKS?
   * A) Solo subnets públicas
   * B) Solo subnets privadas
   * C) Subnets en al menos 2 availability zones
   * D) NAT Gateway

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Subnets en al menos 2 availability zones**

**Explicación:** Al crear un cluster de Amazon EKS, el componente de VPC que debe especificarse son subnets en al menos 2 availability zones. Este es un requisito de AWS para garantizar la alta disponibilidad de los clusters de EKS.

**Requisitos de VPC para clusters de EKS:**

1. **Subnets requeridas en al menos 2 availability zones (AZs)**:
   * Dado que el control plane de EKS se implementa en varias availability zones, se deben especificar subnets en al menos 2 availability zones al crear un cluster.
   * Esto garantiza que el cluster siga funcionando incluso durante fallos de una sola availability zone.
2. **Tipos de subnet**:
   * Puedes usar solo subnets públicas, solo subnets privadas o una mezcla de subnets públicas y privadas.
   * Para entornos de producción, se recomienda ubicar los worker nodes en subnets privadas por seguridad y usar subnets públicas para load balancers.
3. **Tamaño de CIDR de subnet**:
   * Cada subnet debe tener suficientes direcciones IP.
   * Como EKS asigna direcciones IP de VPC a cada pod, se necesitan bloques CIDR suficientemente grandes según la cantidad esperada de pods.
4. **Requisitos de tags**:
   * Se requieren tags específicos para que EKS identifique y use correctamente las subnets:
     * Subnets compartidas: `kubernetes.io/cluster/<cluster-name>: shared`
     * Subnets públicas: `kubernetes.io/role/elb: 1`
     * Subnets privadas: `kubernetes.io/role/internal-elb: 1`

**Ejemplo de configuración de VPC (usando eksctl):**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  cidr: 192.168.0.0/16
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
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

**Configuración de VPC usando AWS CLI:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

Se requiere un NAT Gateway cuando los worker nodes en subnets privadas necesitan acceso a internet, pero no es un componente obligatorio para la creación del cluster de EKS en sí. Si usas solo subnets públicas, puedes crear un cluster sin un NAT Gateway (no recomendado para entornos de producción).

</details>

3. ¿Qué IAM roles se requieren al crear un cluster de Amazon EKS?
   * A) Solo EKS service role
   * B) Solo node instance role
   * C) EKS service role y node instance role
   * D) Fargate execution role

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) EKS service role y node instance role**

**Explicación:** Para crear y operar un cluster de Amazon EKS, se requieren dos IAM roles principales: el EKS service role y el node instance role. Estos dos roles tienen propósitos diferentes y ambos son necesarios para el funcionamiento correcto del cluster.

**1. EKS Service Role (EKS Cluster Role):**

* **Propósito**: Permite que el servicio AWS EKS llame a otros servicios de AWS en nombre de los usuarios.
* **Permisos requeridos**:
  * Acceso a servicios de AWS como EC2, ELB, CloudWatch, KMS, etc.
  * Administración de recursos de VPC
  * Creación y administración de log groups
* **Managed policy**: `AmazonEKSClusterPolicy`
*   **Método de creación**:

    ```bash
    # Create role using AWS CLI
    aws iam create-role \
      --role-name EKSClusterRole \
      --assume-role-policy-document file://eks-cluster-trust-policy.json

    # Attach managed policy
    aws iam attach-role-policy \
      --role-name EKSClusterRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
    ```

    Trust policy (eks-cluster-trust-policy.json):

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "eks.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    ```

**2. Node Instance Role (Node Instance Role):**

* **Propósito**: Permite que los worker nodes de EKS (instancias EC2) interactúen con servicios de AWS.
* **Permisos requeridos**:
  * Descargar imágenes de contenedor desde ECR
  * Escribir logs en CloudWatch
  * Administrar volúmenes EBS/EFS
  * Registro/desregistro de load balancers
* **Managed policies**:
  * `AmazonEKSWorkerNodePolicy`
  * `AmazonEC2ContainerRegistryReadOnly`
  * `AmazonEKS_CNI_Policy`
*   **Método de creación**:

    ```bash
    # Create role using AWS CLI
    aws iam create-role \
      --role-name EKSNodeRole \
      --assume-role-policy-document file://ec2-trust-policy.json

    # Attach managed policies
    aws iam attach-role-policy \
      --role-name EKSNodeRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

    aws iam attach-role-policy \
      --role-name EKSNodeRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

    aws iam attach-role-policy \
      --role-name EKSNodeRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
    ```

    Trust policy (ec2-trust-policy.json):

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "ec2.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    ```

**Creación automática de roles usando eksctl:**

Al crear un cluster usando eksctl, los IAM roles requeridos se pueden crear automáticamente:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

**Roles adicionales (opcionales):**

* **Fargate execution role**: Requerido solo al usar Fargate profiles.
* **Service account IAM roles**: Requeridos al usar IRSA (IAM Roles for Service Accounts).
* **ALB controller role**: Requerido al usar AWS Load Balancer Controller.

El Fargate execution role solo se requiere al usar Fargate profiles y no es obligatorio para la creación básica de clusters de EKS. Por lo tanto, los IAM roles necesarios para crear un cluster de EKS son el EKS service role y el node instance role.

</details>

4. ¿Cuál es el comando correcto para crear un cluster de EKS usando eksctl?
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**Explicación:** El comando correcto para crear un cluster de EKS usando eksctl es `eksctl create cluster --name my-cluster --region us-west-2`. Este comando crea un cluster de EKS con la configuración predeterminada en el nombre y la región especificados.

**Estructura del comando eksctl:**

* `eksctl`: Comando base
* `create`: Acción para crear un recurso
* `cluster`: Tipo de recurso que se va a crear (cluster)
* `--name my-cluster`: Especificar el nombre del cluster
* `--region us-west-2`: Especificar la región de AWS

**Comando básico de creación de cluster:**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

Este comando crea un cluster con la siguiente configuración predeterminada:

* 2 nodos m5.large
* Creación de una VPC nueva
* AMI predeterminada de Amazon Linux 2
* Managed node groups
* Creación automática de los IAM roles requeridos

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
  --ssh-access \
  --ssh-public-key my-key \
  --managed
```

**Creación de cluster usando un archivo de configuración:**

```bash
# Create cluster.yaml file
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.28"

nodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: true
      publicKeyName: my-key
EOF

# Create cluster using configuration file
eksctl create cluster -f cluster.yaml
```

**Problemas con las otras opciones:**

* `eksctl create-cluster`: Formato de comando incorrecto. eksctl usa espacios, no guiones (-), para separar comandos.
* `eksctl new cluster`: 'new' no es un comando válido de eksctl.
* `eksctl start cluster`: 'start' no es un comando válido de eksctl. El concepto de iniciar un cluster existente no se aplica a EKS.

eksctl proporciona varios comandos para la administración de clusters de EKS:

* `eksctl create cluster`: Crear un cluster nuevo
* `eksctl get cluster`: Listar clusters
* `eksctl update cluster`: Actualizar un cluster
* `eksctl delete cluster`: Eliminar un cluster
* `eksctl create nodegroup`: Agregar un node group
* `eksctl scale nodegroup`: Escalar un node group

</details>

5. ¿Qué es correcto con respecto a las versiones de Kubernetes que se pueden especificar al crear un cluster de Amazon EKS?
   * A) Solo se admite la versión más reciente
   * B) Solo se admiten la versión más reciente y las 2 versiones anteriores
   * C) Todas las versiones de Kubernetes admitidas por AWS
   * D) Todas las versiones de Kubernetes

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Todas las versiones de Kubernetes admitidas por AWS**

**Explicación:** Al crear un cluster de Amazon EKS, puedes elegir entre las versiones de Kubernetes que AWS admite actualmente. AWS normalmente admite varias versiones de Kubernetes simultáneamente, incluida la versión más reciente y varias versiones anteriores.

**Política de soporte de versiones de Kubernetes en EKS:**

1. **Período de soporte**:
   * Cada versión de Kubernetes recibe soporte durante 14 meses después de su lanzamiento en EKS.
   * Las fechas de fin de soporte se anuncian con al menos 60 días de anticipación.
2. **Versiones admitidas**:
   * Normalmente, EKS admite 3-4 versiones de Kubernetes simultáneamente.
   * Las versiones nuevas están disponibles en EKS unos meses después del lanzamiento de la comunidad de Kubernetes.
3.  **Cómo verificar versiones**:

    ```bash
    # Check supported versions using AWS CLI
    aws eks describe-addon-versions | grep kubernetesVersion | sort -u

    # Or
    aws eks get-cluster-version-list
    ```
4.  **Ejemplos de especificación de versión**:

    ```bash
    # Specify a specific version using eksctl
    eksctl create cluster --name my-cluster --version 1.28 --region us-west-2

    # Specify a specific version using AWS CLI
    aws eks create-cluster \
      --name my-cluster \
      --kubernetes-version 1.28 \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890
    ```
5.  **Actualizaciones de versión**:

    * Después de crear el cluster, puedes actualizar a versiones admitidas.
    * En general, se recomienda actualizar una versión minor a la vez.

    ```bash
    # Cluster version upgrade
    aws eks update-cluster-version \
      --name my-cluster \
      --kubernetes-version 1.28
    ```

**Consideraciones al seleccionar una versión:**

1. **Estabilidad**:
   * La versión más reciente proporciona características nuevas, pero puede tener errores iniciales.
   * Para entornos de producción donde la estabilidad es importante, puede ser mejor seleccionar una versión anterior ya probada.
2. **Requisitos de características**:
   * Si se necesitan características específicas de Kubernetes, debes seleccionar la versión mínima que admita esas características.
3. **Período de soporte**:
   * Para soporte a largo plazo, selecciona una versión lanzada recientemente para maximizar el período de soporte.
4. **Compatibilidad del ecosistema**:
   * Asegúrate de que las herramientas, add-ons y operators que usas sean compatibles con la versión de Kubernetes seleccionada.

Problemas con las otras opciones:

* No solo se admite la versión más reciente; se admiten varias versiones simultáneamente.
* La cantidad de versiones admitidas no está fija en "la versión más reciente y las 2 versiones anteriores", sino que varía según la política de soporte de AWS.
* No todas las versiones de Kubernetes son admitidas; solo se pueden usar versiones probadas y admitidas por AWS.

</details>

6. ¿Cuál NO es una opción para crear node groups en un cluster de Amazon EKS?
   * A) Managed node groups
   * B) Self-managed node groups
   * C) Fargate profiles
   * D) Serverless node groups

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Serverless node groups**

**Explicación:** "Serverless node groups" no es un concepto que exista en Amazon EKS. Las tres opciones principales para ejecutar cargas de trabajo en EKS son managed node groups, self-managed node groups y Fargate profiles.

**1. Managed Node Groups:**

* **Características**:
  * AWS administra el aprovisionamiento y el ciclo de vida de los nodos
  * Creación y registro automáticos de instancias EC2
  * Configuración automática de ASG (Auto Scaling Group)
  * Actualizaciones automáticas de la versión de Kubernetes
  * Reemplazo automático de nodos dañados
  * Actualizaciones automáticas de AMI de nodos
*   **Método de creación**:

    ```bash
    # Create managed node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-mng \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5

    # Create managed node group using AWS CLI
    aws eks create-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name my-mng \
      --subnets subnet-12345 subnet-67890 \
      --instance-types t3.medium \
      --scaling-config minSize=1,maxSize=5,desiredSize=3 \
      --node-role arn:aws:iam::123456789012:role/EksNodeRole
    ```

**2. Self-managed Node Groups:**

* **Características**:
  * El usuario administra el aprovisionamiento y el ciclo de vida de los nodos
  * Más opciones de personalización
  * Puede usar AMIs personalizadas o bootstrap scripts
  * Adecuado para instance types o requisitos de configuración específicos
*   **Método de creación**:

    ```bash
    # Create self-managed node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-smng \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5 \
      --managed=false

    # Can also be created manually using CloudFormation or EC2 launch templates.
    ```

**3. Fargate Profiles:**

* **Características**:
  * Entorno serverless de ejecución de contenedores
  * No se requiere administración de nodos
  * Asignación de recursos y facturación por pod
  * Ejecución selectiva basada en namespaces y labels específicos
*   **Método de creación**:

    ```bash
    # Create Fargate profile using eksctl
    eksctl create fargateprofile \
      --cluster my-cluster \
      --name my-fargate-profile \
      --namespace my-namespace \
      --labels app=my-app

    # Create Fargate profile using AWS CLI
    aws eks create-fargate-profile \
      --cluster-name my-cluster \
      --fargate-profile-name my-fargate-profile \
      --pod-execution-role-arn arn:aws:iam::123456789012:role/FargatePodExecutionRole \
      --selectors namespace=my-namespace,labels={app=my-app}
    ```

**Comparison of each option:**

| Feature             | Managed Node Groups | Self-managed Node Groups | Fargate Profiles             |
| ------------------- | ------------------- | ------------------------ | ---------------------------- |
| Management overhead | Low                 | High                     | None                         |
| Customization       | Medium              | High                     | Low                          |
| Cost efficiency     | Medium              | High (when optimized)    | Low (paying for convenience) |
| Scalability         | Automatic           | Manual/Automatic         | Automatic                    |
| Use case            | General workloads   | Special requirements     | Variable workloads, dev/test |

El término "serverless node groups" no existe oficialmente. Fargate proporciona un entorno serverless de ejecución de contenedores, pero se configura como "Fargate profiles", no como "node groups". Al usar Fargate, no necesitas administrar nodos directamente, y solo se aprovisionan los recursos de cómputo necesarios para la ejecución de pods.

</details>

7. ¿Cuál NO es un tipo de AMI de nodo admitido en clusters de Amazon EKS?
   * A) Amazon Linux 2
   * B) Amazon Linux 2023
   * C) Bottlerocket
   * D) Ubuntu Core

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Ubuntu Core**

**Explicación:** Ubuntu Core no es un tipo de AMI de nodo oficialmente admitido en Amazon EKS. Los tipos de AMI de nodo oficialmente admitidos en EKS son Amazon Linux 2, Amazon Linux 2023 y Bottlerocket.

**Tipos de AMI de nodo admitidos en EKS:**

1.  **Amazon Linux 2 (AL2)**:

    * Distribución Linux predeterminada proporcionada por AWS
    * Disponible como AMI optimizada para EKS
    * Recomendada para la mayoría de las cargas de trabajo de EKS
    * Soporte a largo plazo y actualizaciones de seguridad

    ```bash
    # Create Amazon Linux 2 based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name al2-nodes \
      --node-ami-family AmazonLinux2
    ```
2.  **Amazon Linux 2023 (AL2023)**:

    * Última versión de Amazon Linux
    * Seguridad y rendimiento mejorados
    * Último kernel y paquetes de software
    * Disponible como AMI optimizada para EKS

    ```bash
    # Create Amazon Linux 2023 based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name al2023-nodes \
      --node-ami-family AmazonLinux2023
    ```
3.  **Bottlerocket**:

    * OS de código abierto basado en Linux y optimizado para cargas de trabajo de contenedores
    * Superficie de ataque minimizada
    * Actualizaciones basadas en transacciones
    * Diseño centrado en contenedores

    ```bash
    # Create Bottlerocket based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name bottlerocket-nodes \
      --node-ami-family Bottlerocket
    ```

**Otras opciones de AMI admitidas:**

1.  **Windows**:

    * AMIs basadas en Windows Server 2019, 2022
    * Puede ejecutar cargas de trabajo de contenedores Windows

    ```bash
    # Create Windows based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-nodes \
      --node-ami-family WindowsServer2022FullContainer
    ```
2.  **AMIs personalizadas**:

    * Se pueden usar AMIs personalizadas para requisitos específicos
    * Se usan principalmente con self-managed node groups

    ```bash
    # Create custom AMI based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name custom-nodes \
      --node-ami ami-1234567890abcdef0
    ```

**Cómo usar Ubuntu en EKS:**

Ubuntu Core no está oficialmente admitido, pero puedes crear self-managed node groups usando AMIs estándar de Ubuntu Server. En este caso, se requiere configuración adicional:

1. Seleccionar AMI de Ubuntu Server
2. Instalar los componentes necesarios de Kubernetes
3. Usar bootstrap script para conectar los nodos al cluster

```bash
# Example of creating Ubuntu-based self-managed node group
eksctl create nodegroup \
  --cluster my-cluster \
  --name ubuntu-nodes \
  --node-ami ami-ubuntu-server-id \
  --managed=false \
  --ssh-access \
  --ssh-public-key my-key \
  --pre-bootstrap-commands 'apt-get update && apt-get install -y docker.io'
```

**Consideraciones al seleccionar AMI:**

* **Seguridad**: Actualizaciones y parches de seguridad regulares
* **Rendimiento**: Kernel y configuración optimizados para la carga de trabajo
* **Compatibilidad**: Compatibilidad con la versión de Kubernetes
* **Facilidad de administración**: Procesos de actualización y mantenimiento
* **Requisitos especiales**: Soporte de GPU, kernel modules, etc.

Ubuntu Core es un sistema operativo ligero para dispositivos IoT y edge, y no está oficialmente admitido ni optimizado para usarse como nodos de EKS. Por lo tanto, Ubuntu Core no es un tipo de AMI de nodo admitido en clusters de EKS.

</details>

8. ¿Qué es correcto con respecto a la configuración de acceso a endpoints para clusters de Amazon EKS?
   * A) De forma predeterminada, solo el endpoint público está habilitado
   * B) De forma predeterminada, solo el endpoint privado está habilitado
   * C) De forma predeterminada, tanto el endpoint público como el privado están habilitados
   * D) El acceso a endpoints no se puede cambiar después de crear el cluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) De forma predeterminada, solo el endpoint público está habilitado**

**Explicación:** Al crear un cluster de Amazon EKS, de forma predeterminada, solo el endpoint público está habilitado y el endpoint privado está deshabilitado. Esta configuración se puede cambiar después de crear el cluster, y se pueden seleccionar varias configuraciones de acceso a endpoints según los requisitos de seguridad.

**Opciones de acceso a endpoints del cluster de EKS:**

1.  **Solo endpoint público habilitado (configuración predeterminada)**:

    * Cluster API server accesible a través de internet
    * El acceso se puede restringir mediante security groups
    * Adecuado para entornos de desarrollo o prueba

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=false
    ```
2.  **Endpoints público y privado habilitados**:

    * Accesible mediante IP privada desde dentro de la VPC
    * También accesible a través de internet
    * Adecuado para entornos híbridos

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true
    ```
3.  **Solo endpoint privado habilitado**:

    * Cluster API server accesible solo desde dentro de la VPC
    * Sin acceso a través de internet
    * Proporciona el nivel más alto de seguridad
    * Recomendado para entornos de producción

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
    ```
4.  **Restricción de acceso público**:

    * Permitir acceso al endpoint público solo desde bloques CIDR específicos
    * Restringir el acceso solo desde la red corporativa o VPN

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]
    ```

**Configuración de endpoints al crear un cluster con eksctl:**

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  clusterEndpoints:
    publicAccess: true   # Enable public endpoint
    privateAccess: true  # Enable private endpoint
  publicAccessCIDRs: ["203.0.113.0/24"]  # Restrict public access
```

```bash
eksctl create cluster -f cluster.yaml
```

**Cambio de la configuración de acceso a endpoints:**

```bash
# Enable private endpoint
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPrivateAccess=true

# Disable public endpoint
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false
```

**Consideraciones al configurar el acceso a endpoints:**

1. **Requisitos de seguridad**:
   * Usar solo endpoint privado proporciona el nivel más alto de seguridad
   * Aplica restricciones CIDR cuando se necesita acceso público
2. **Conectividad de red**:
   * Al usar solo endpoint privado, el acceso solo es posible desde dentro de la VPC o mediante VPN/Direct Connect
   * Habilitar ambos endpoints puede ser útil en entornos de trabajo híbridos
3. **Requisitos operativos**:
   * Considera cuándo CI/CD pipelines, herramientas externas, etc. necesitan acceso al cluster
4. **Costo**:
   * No hay costo adicional por la configuración de endpoints en sí
   * Considera los costos de VPN o Direct Connect al usar solo endpoint privado

Problemas con las otras opciones:

* De forma predeterminada, solo el endpoint público está habilitado, no el endpoint privado.
* De forma predeterminada, no están habilitados tanto el endpoint público como el privado; solo el endpoint público está habilitado.
* El acceso a endpoints se puede cambiar después de crear el cluster.

</details>

9. ¿Cuál NO es una consideración al seleccionar instance types para node groups en clusters de Amazon EKS?
   * A) Requisitos de la carga de trabajo (CPU, memoria, almacenamiento)
   * B) Optimización de costos
   * C) Número de availability zones
   * D) Generación de instancia (por ejemplo, t3 frente a t2)

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Número de availability zones**

**Explicación:** El número de availability zones no es una consideración directa al seleccionar instance types para node groups. Las availability zones están relacionadas con dónde se implementan los node groups, y son independientes de la selección de los instance types en sí. Los instance types deben seleccionarse considerando los requisitos de carga de trabajo, la optimización de costos, la generación de instancia, etc.

**Consideraciones reales al seleccionar instance types para node groups:**

1. **Requisitos de la carga de trabajo (CPU, memoria, almacenamiento)**:
   * Seleccionar instance types que coincidan con los requisitos de recursos de la aplicación
   * Cargas de trabajo intensivas en memoria: instancias optimizadas para memoria, como r5, r6g
   * Cargas de trabajo intensivas en cómputo: instancias optimizadas para cómputo, como c5, c6g
   * Cargas de trabajo equilibradas: instancias de uso general, como m5, m6g
   * Cargas de trabajo de GPU: instancias de accelerated computing, como p3, g4dn
2. **Optimización de costos**:
   * Instancias On-Demand frente a Spot instances
   * Reserved Instances o Savings Plans
   * Selección de tamaño de instancia adecuado (evitar sobreaprovisionamiento)
   * Ahorro de costos mediante instancias basadas en ARM Graviton (por ejemplo, m6g, c6g)
3. **Generación de instancia**:
   * Las instancias de última generación generalmente ofrecen mejor rendimiento y eficiencia de costos
   * Ejemplo: t3 ofrece mejor rendimiento y relación precio-rendimiento que t2
   * Las últimas generaciones proporcionan enhanced networking, rendimiento de almacenamiento, etc.
4. **Requisitos de red**:
   * Soporte de enhanced networking (ENA, EFA, etc.)
   * Requisitos de ancho de banda de red
   * Límites de red relacionados con el máximo de pods por instancia
5. **Requisitos de almacenamiento**:
   * Si se necesita almacenamiento local de instancia (por ejemplo, instancias i3, d3)
   * Soporte de optimización de EBS
   * Requisitos de throughput e IOPS de almacenamiento
6. **Arquitectura de CPU**:
   * x86 (Intel, AMD) frente a ARM (AWS Graviton)
   * Consideraciones de compatibilidad de aplicaciones

**Availability zones e implementación de node groups:**

El número de availability zones está relacionado con la estrategia de implementación de node groups, no con la selección de instance types:

* Implementar node groups en varias availability zones para alta disponibilidad
* Distribuir nodos de manera uniforme en cada availability zone
* Se pueden seleccionar todas las availability zones de la región o availability zones específicas

```bash
# Deploy node group to specific availability zones
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

**Ejemplos de selección de instance type:**

1. **Servidores de aplicaciones web**:
   * Instancias de uso general: t3.medium, m5.large
   * Rentables con rendimiento equilibrado
2. **Bases de datos**:
   * Instancias optimizadas para memoria: r5.xlarge, r6g.xlarge
   * Alta relación memoria/CPU
3. **Trabajos de procesamiento batch**:
   * Instancias optimizadas para cómputo: c5.xlarge, c6g.xlarge
   * Alto rendimiento de CPU
4. **Cargas de trabajo de machine learning**:
   * Instancias GPU: p3.2xlarge, g4dn.xlarge
   * Capacidades de accelerated computing

La selección de instance types debe determinarse por las características de la carga de trabajo, las restricciones de costo, los requisitos de rendimiento, etc., y el número de availability zones está relacionado con la estrategia de implementación de node groups en lugar de con la selección de los instance types en sí.

</details>

10. ¿Cuál es el comando correcto para configurar kubectl después de crear un cluster de Amazon EKS?
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**Explicación:** El comando correcto para configurar kubectl después de crear un cluster de Amazon EKS es `aws eks update-kubeconfig --name my-cluster --region us-west-2`. Este comando usa el módulo EKS de AWS CLI para actualizar el archivo kubeconfig del cluster especificado.

**Proceso de configuración de kubectl:**

1. **Actualización del archivo kubeconfig**:
   * El archivo kubeconfig almacena la información de configuración necesaria para que kubectl se comunique con clusters de Kubernetes.
   * De forma predeterminada, se almacena en `~/.kube/config`.
   * El comando `aws eks update-kubeconfig` actualiza este archivo automáticamente.
2. **Componentes del comando**:
   * `--name`: Nombre del cluster de EKS
   * `--region`: Región de AWS donde se encuentra el cluster
   * `--kubeconfig` (opcional): Ruta del archivo kubeconfig personalizado
   * `--role-arn` (opcional): IAM role que se usará para el acceso al cluster
3.  **Ejemplo de comando completo**:

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2
    ```
4.  **Opciones adicionales**:

    ```bash
    # Use custom kubeconfig file
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig ~/.kube/eks-config

    # Use specific IAM role
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole

    # Set alias
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias
    ```
5.  **Verificar la configuración**:

    ```bash
    # Check current context
    kubectl config current-context

    # List all contexts
    kubectl config get-contexts

    # Test cluster connection
    kubectl cluster-info
    ```

**Problemas con las otras opciones:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: Este comando no existe. No hay un subcomando `get-kubeconfig` en AWS CLI.
* `kubectl config set-cluster my-cluster --region us-west-2`: Este comando tiene sintaxis incorrecta. `kubectl config set-cluster` no admite la flag `--region` y no configura automáticamente la información de autenticación necesaria para clusters de EKS.
* `eksctl configure kubectl --name my-cluster --region us-west-2`: Este comando no existe. eksctl no tiene un subcomando `configure kubectl`. Al crear un cluster con eksctl, kubeconfig se configura automáticamente, pero para clusters existentes, debes usar el comando `aws eks update-kubeconfig`.

**Creación y configuración de cluster usando eksctl:**

Al crear un cluster usando eksctl, kubeconfig se actualiza automáticamente:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

Este comando crea el cluster y actualiza kubeconfig automáticamente. Sin embargo, para conectarte a un cluster existente o a un cluster creado por otra herramienta, debes usar el comando `aws eks update-kubeconfig`.

**Administración de múltiples clusters:**

Al administrar varios clusters de EKS, puedes agregarlos al archivo kubeconfig ejecutando el comando `aws eks update-kubeconfig` para cada cluster:

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1

# Switch context
kubectl config use-context arn:aws:eks:us-west-2:123456789012:cluster/cluster1
```

Por lo tanto, el comando correcto para configurar kubectl después de crear un cluster de Amazon EKS es `aws eks update-kubeconfig --name my-cluster --region us-west-2`.

</details>

## Ejercicios prácticos

### Ejercicio 1: Crear un cluster de EKS usando eksctl

**Escenario:** Eres un ingeniero DevOps en tu empresa y necesitas crear un cluster de Amazon EKS para el equipo de desarrollo. El cluster debe ser rentable pero escalable, con configuraciones básicas de seguridad.

**Requisitos:**

1. Crear un cluster de EKS usando eksctl
2. Implementar en 2 availability zones
3. Usar instance type t3.medium
4. Configurar auto-scaling (mínimo 2, máximo 5 nodos)
5. Habilitar endpoints privados y públicos

**Solución:**

<details>

<summary>Mostrar respuesta</summary>

**1. Instalar eksctl (si aún no está instalado)**

```bash
# macOS
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Linux
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version
```

**2. Crear archivo de configuración del cluster**

```bash
cat > eks-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true

availabilityZones: ["us-west-2a", "us-west-2b"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        ebs: true
        albIngress: true
        cloudWatch: true
    ssh:
      allow: false
    privateNetworking: true
    tags:
      Environment: development
      Owner: devops-team
EOF
```

**3. Crear el cluster**

```bash
eksctl create cluster -f eks-cluster.yaml
```

Este comando realiza las siguientes tareas:

* Crea stacks de CloudFormation
* Crea VPC y subnets
* Configura security groups
* Crea el cluster de EKS
* Crea managed node groups
* Inicializa nodos y los conecta al cluster
* Configura kubeconfig

**4. Verificar el cluster**

```bash
# Check cluster status
eksctl get cluster --name dev-cluster --region us-west-2

# Check nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system
```

**5. Configurar acceso al cluster**

```bash
# Verify kubeconfig
kubectl config current-context

# Check cluster information
kubectl cluster-info
```

**6. Verificar configuraciones básicas de seguridad**

```bash
# Check namespaces
kubectl get namespaces

# Check RBAC settings
kubectl get clusterroles
kubectl get clusterrolebindings
```

**7. Monitorear recursos del cluster**

```bash
# Check node resource usage
kubectl top nodes

# Check pod resource usage
kubectl top pods --all-namespaces
```

A través de este ejercicio, aprendiste cómo crear un cluster de EKS rentable y escalable usando eksctl. Las instancias t3.medium son una opción rentable, y la configuración de auto-scaling permite ajustar automáticamente la cantidad de nodos según la carga de trabajo. Se habilitaron endpoints privados y públicos para permitir el acceso al cluster desde fuentes internas y externas.

</details>

### Ejercicio 2: Crear un cluster de EKS usando AWS Management Console

**Escenario:** Necesitas crear y configurar un cluster de EKS usando AWS Management Console. Este cluster es para un entorno de producción donde la seguridad y la alta disponibilidad son importantes.

**Requisitos:**

1. Crear un cluster de EKS usando AWS Management Console
2. Colocar nodos en subnets privadas
3. Restringir el acceso público al endpoint del cluster
4. Configurar managed node groups
5. Crear los IAM roles requeridos

**Solución:**

<details>

<summary>Mostrar respuesta</summary>

**1. Crear los IAM roles requeridos**

**Crear EKS cluster role:**

1. Inicia sesión en AWS Management Console y navega al servicio IAM.
2. Selecciona "Roles" en el menú izquierdo y haz clic en "Create role".
3. Selecciona "AWS service" como tipo de entidad de confianza.
4. En caso de uso, selecciona "EKS" y luego "EKS - Cluster".
5. Haz clic en "Next".
6. Verifica que `AmazonEKSClusterPolicy` se haya seleccionado automáticamente.
7. Haz clic en "Next".
8. Ingresa "EKSClusterRole" como nombre del role y haz clic en "Create role".

**Crear EKS node role:**

1. Haz clic en "Create role" nuevamente en el servicio IAM.
2. Selecciona "AWS service" como tipo de entidad de confianza.
3. Selecciona "EC2" en caso de uso.
4. Haz clic en "Next".
5. Busca y selecciona las siguientes policies:
   * `AmazonEKSWorkerNodePolicy`
   * `AmazonEC2ContainerRegistryReadOnly`
   * `AmazonEKS_CNI_Policy`
6. Haz clic en "Next".
7. Ingresa "EKSNodeRole" como nombre del role y haz clic en "Create role".

**2. Preparar VPC y subnets**

Se requiere una configuración de VPC adecuada para entornos de producción. Puedes usar una plantilla de AWS CloudFormation para crear una VPC optimizada para EKS:

1. Navega a la consola de CloudFormation.
2. Selecciona "Create stack" > "With new resources (standard)".
3.  Ingresa la siguiente dirección en Amazon S3 URL:

    ```
    https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
    ```
4. Haz clic en "Next".
5. Ingresa "eks-vpc" como nombre del stack.
6. Deja los parámetros predeterminados y haz clic en "Next".
7. Deja las opciones predeterminadas en la siguiente página y haz clic en "Next".
8. Haz clic en "Create stack".
9. Una vez que se complete la creación del stack, anota los siguientes valores de la pestaña "Outputs":
   * VpcId
   * SubnetIds
   * SecurityGroups

**3. Crear cluster de EKS**

1. Navega al servicio EKS en AWS Management Console.
2. Haz clic en "Create cluster".
3. En la página "Cluster configuration":
   * Nombre del cluster: "prod-cluster"
   * Versión de Kubernetes: Selecciona la versión más reciente (por ejemplo, 1.28)
   * Cluster service role: Selecciona "EKSClusterRole" creado previamente
   * Haz clic en "Next".
4. En la página "Specify networking":
   * VPC: Selecciona la VPC creada previamente
   * Subnets: Selecciona solo subnets privadas (desmarca subnets públicas)
   * Security groups: Selecciona el security group predeterminado
   * Cluster endpoint access:
     * Selecciona "Private" o
     * Selecciona "Public and Private" y restringe los bloques CIDR al rango IP de la empresa
   * Haz clic en "Next".
5. En la página "Configure logging":
   * Selecciona los tipos de log requeridos (API server, Audit, Authenticator, Controller manager, Scheduler)
   * Haz clic en "Next".
6. En la página "Select add-ons":
   * Mantén los add-ons predeterminados (kube-proxy, CoreDNS, VPC CNI)
   * Haz clic en "Next".
7. Revisa todas las configuraciones en la página de revisión y haz clic en "Create".
8. Espera a que se complete la creación del cluster (aproximadamente 15-20 minutos).

**4. Crear managed node group**

1. Una vez creado el cluster, haz clic en el nombre del cluster.
2. Ve a la pestaña "Compute" y haz clic en "Add node group".
3. En la página "Node group configuration":
   * Nombre: "prod-nodes"
   * Node IAM role: Selecciona "EKSNodeRole" creado previamente
   * Haz clic en "Next".
4. En la página "Set compute and scaling configuration":
   * AMI type: Amazon Linux 2 (x86)
   * Instance type: Selecciona m5.large
   * Disk size: 50 GiB
   * Configuración de escalado del node group:
     * Tamaño mínimo: 2
     * Tamaño máximo: 5
     * Tamaño deseado: 3
   * Haz clic en "Next".
5. En la página "Specify networking":
   * Subnets: Selecciona solo subnets privadas
   * Haz clic en "Next".
6. Revisa todas las configuraciones en la página "Review and create" y haz clic en "Create".
7. Espera a que se complete la creación del node group (aproximadamente 5 minutos).

**5. Configurar kubectl y acceder al cluster**

1. Verifica que AWS CLI esté instalado.
2.  Ejecuta el siguiente comando para actualizar el archivo de configuración de kubectl:

    ```bash
    aws eks update-kubeconfig --name prod-cluster --region us-west-2
    ```
3.  Verifica la conexión al cluster:

    ```bash
    kubectl get nodes
    kubectl cluster-info
    ```

**6. Mejorar la seguridad básica**

1.  Revisa y restringe las reglas de AWS security group:

    ```bash
    # Check cluster information for current context
    kubectl config view --minify
    ```
2.  Aplica network policies (opcional):

    ```yaml
    # default-deny.yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: default-deny
      namespace: default
    spec:
      podSelector: {}
      policyTypes:
      - Ingress
    ```

    ```bash
    kubectl apply -f default-deny.yaml
    ```

A través de este ejercicio, aprendiste cómo crear un cluster de EKS con configuraciones de seguridad y alta disponibilidad adecuadas para entornos de producción usando AWS Management Console. La seguridad se mejoró al colocar nodos en subnets privadas y restringir el acceso público al endpoint del cluster, y la administración de nodos se simplificó al usar managed node groups.

</details>

## Temas avanzados

Las siguientes son preguntas sobre temas avanzados relacionados con la creación de clusters de Amazon EKS. Esta sección evalúa tu comprensión de conceptos avanzados y prácticas recomendadas para la creación de clusters de EKS.

1. ¿Cuál es el principal beneficio de usar Launch Templates personalizados en clusters de Amazon EKS?
   * A) Tiempo de creación del cluster reducido
   * B) Bootstrap scripts de nodos personalizables y configuración de volúmenes adicionales
   * C) Personalización del control plane del cluster
   * D) Usa automáticamente la versión de AMI más reciente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Bootstrap scripts de nodos personalizables y configuración de volúmenes adicionales**

**Explicación:** El principal beneficio de usar Launch Templates personalizados en clusters de Amazon EKS es la capacidad de personalizar bootstrap scripts de nodos y configurar volúmenes adicionales. Los launch templates permiten un control detallado sobre varios aspectos de las instancias EC2, lo que habilita configuraciones avanzadas que no son posibles con las opciones predeterminadas de creación de node groups.

**Elementos personalizables con Launch Templates:**

1. **Bootstrap scripts personalizados**:
   * Definir scripts personalizados que se ejecutan antes de que los nodos se unan al cluster
   * Instalar y configurar software adicional
   * Ajustar configuraciones del sistema (parámetros del kernel, configuraciones de red, etc.)
   *   Ejemplo:

       ```bash
       #!/bin/bash
       # Custom bootstrap script
       echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
       sysctl -p

       # Install additional packages
       yum install -y amazon-cloudwatch-agent

       # Run EKS bootstrap script
       /etc/eks/bootstrap.sh my-cluster --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker'
       ```
2. **Configuración de volúmenes adicionales**:
   * Personalizar tamaño, tipo e IOPS del volumen raíz
   * Adjuntar volúmenes EBS adicionales para datos, logs, almacenamiento temporal
   * Configurar volúmenes de instance store
   *   Ejemplo:

       ```json
       {
         "DeviceName": "/dev/xvda",
         "Ebs": {
           "VolumeSize": 100,
           "VolumeType": "gp3",
           "Iops": 3000,
           "Throughput": 125,
           "DeleteOnTermination": true
         }
       },
       {
         "DeviceName": "/dev/sdf",
         "Ebs": {
           "VolumeSize": 500,
           "VolumeType": "gp3",
           "DeleteOnTermination": true
         }
       }
       ```
3. **Configuración avanzada de red**:
   * Habilitar enhanced networking
   * Configurar múltiples interfaces de red
   * Especificar placement groups
   *   Ejemplo:

       ```json
       {
         "NetworkInterfaces": [
           {
             "DeviceIndex": 0,
             "Groups": ["sg-12345"],
             "DeleteOnTermination": true
           }
         ]
       }
       ```
4. **Opciones de metadatos de instancia**:
   * Requerir IMDSv2 (seguridad mejorada)
   * Establecer hop limit
   *   Ejemplo:

       ```json
       {
         "MetadataOptions": {
           "HttpTokens": "required",
           "HttpPutResponseHopLimit": 2
         }
       }
       ```
5. **User data scripts**:
   * Proporcionar scripts que se ejecutan al iniciar la instancia
   * Realizar configuración personalizada antes de unirse al cluster
   *   Ejemplo:

       ```bash
       #!/bin/bash
       # User data script
       mkdir -p /opt/app
       mount -t tmpfs -o size=10G tmpfs /opt/app
       ```

**Creación y uso de Launch Templates:**

1. **Crear Launch Template en AWS Management Console**:
   * EC2 Console > Launch Templates > Create launch template
   * Configurar AMI, instance type, key pair, security groups, etc.
   * Configurar ajustes avanzados como almacenamiento, interfaces de red, user data
2.  **Crear node group basado en launch template usando eksctl**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig

    metadata:
      name: my-cluster
      region: us-west-2

    managedNodeGroups:
      - name: custom-ng
        launchTemplate:
          id: lt-12345abcdef
          version: "1"
    ```
3.  **Crear node group basado en launch template usando AWS CLI**:

    ```bash
    aws eks create-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name custom-ng \
      --launch-template id=lt-12345abcdef,version=1 \
      --subnets subnet-12345 subnet-67890 \
      --node-role arn:aws:iam::123456789012:role/EKSNodeRole
    ```

**Problemas con las otras opciones:**

* **Tiempo de creación del cluster reducido**: Usar launch templates no reduce el tiempo de creación del cluster. De hecho, la configuración adicional puede hacer que tarde un poco más.
* **Personalización del control plane del cluster**: Los launch templates solo se aplican a worker nodes; el control plane de EKS es administrado por AWS y no se puede personalizar mediante launch templates.
* **Usa automáticamente la versión de AMI más reciente**: Los launch templates especifican un ID de AMI específico, lo que en realidad tiene el efecto de bloquear la versión de AMI. Para usar automáticamente la AMI más reciente, debes no usar launch templates o actualizar regularmente el launch template.

Los launch templates son particularmente útiles cuando se necesita personalización avanzada de node groups de EKS, y deben usarse cuando hay requisitos especiales que no se pueden cumplir con la configuración estándar.

</details>

2. ¿Cuál NO es una estrategia de optimización de costos para clusters de Amazon EKS?
   * A) Usar Spot instances
   * B) Configurar Cluster Autoscaler
   * C) Usar los instance types más recientes para todos los worker nodes
   * D) Uso selectivo de Fargate profiles

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar los instance types más recientes para todos los worker nodes**

**Explicación:** Usar los instance types más recientes para todos los worker nodes no es necesariamente una estrategia de optimización de costos. Los instance types más recientes suelen ofrecer mejor rendimiento y características, pero no siempre son rentables. Es más importante seleccionar instance types adecuados que coincidan con los requisitos de la carga de trabajo.

**Estrategias reales de optimización de costos para clusters de EKS:**

1. **Usar Spot instances**:
   * Hasta 90% de ahorro de costos en comparación con instancias On-Demand
   * Adecuado para cargas de trabajo interrumpibles (batch jobs, entornos dev/test, etc.)
   *   Configurar Spot instances en managed node groups:

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name spot-ng \
         --node-type m5.large \
         --nodes 2 \
         --nodes-min 1 \
         --nodes-max 5 \
         --spot
       ```
   *   Mezclar múltiples instance types para mejorar la disponibilidad:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: spot-ng
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
           spot: true
       ```
2. **Configurar Cluster Autoscaler**:
   * Ajustar automáticamente la cantidad de nodos según los requisitos de la carga de trabajo
   * Ahorro de costos al eliminar automáticamente nodos no utilizados
   *   Instalación y configuración:

       ```bash
       # Install Cluster Autoscaler using Helm
       helm repo add autoscaler https://kubernetes.github.io/autoscaler

       helm install cluster-autoscaler autoscaler/cluster-autoscaler \
         --namespace kube-system \
         --set autoDiscovery.clusterName=my-cluster \
         --set awsRegion=us-west-2 \
         --set rbac.create=true
       ```
3. **Uso selectivo de Fargate profiles**:
   * El entorno serverless de ejecución de contenedores elimina la carga de administración de nodos
   * Paga solo por los recursos utilizados
   * Adecuado para cargas de trabajo intermitentes o entornos dev/test
   *   Usar Fargate solo para namespaces o labels específicos:

       ```bash
       eksctl create fargateprofile \
         --cluster my-cluster \
         --name fp-dev \
         --namespace dev
       ```
4. **Seleccionar tamaños de instancia adecuados**:
   * Seleccionar tamaños de instancia que coincidan con los requisitos de la carga de trabajo
   * Evitar el sobreaprovisionamiento
   *   Monitorear y analizar el uso de recursos:

       ```bash
       kubectl top nodes
       kubectl top pods --all-namespaces
       ```
5. **Usar instancias basadas en Graviton (ARM)**:
   * Hasta 40% de ahorro de costos en comparación con instancias basadas en x86
   * Proporciona rendimiento equivalente
   * Se requiere verificación de compatibilidad
   *   Ejemplo:

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name arm-ng \
         --node-type m6g.large \
         --nodes 2
       ```
6. **Utilizar Reserved Instances o Savings Plans**:
   * Ahorro de costos mediante compromisos a largo plazo
   * Adecuado para cargas de trabajo predecibles
   * Hasta 72% de ahorro de costos en comparación con On-Demand
7. **Optimizar resource requests y limits**:
   * Mejorar la utilización de nodos configurando correctamente los resource requests de pods
   * Evitar el sobreaprovisionamiento
   *   Ejemplo:

       ```yaml
       resources:
         requests:
           cpu: 100m
           memory: 128Mi
         limits:
           cpu: 500m
           memory: 256Mi
       ```
8. **Monitoreo y análisis de costos**:
   * Usar AWS Cost Explorer
   * Configurar Kubernetes cost allocation tags
   * Usar herramientas de monitoreo de costos de terceros (Kubecost, CloudHealth, etc.)

**Problemas con el uso de los instance types más recientes:**

1. **Costos incrementados**:
   * Los instance types más recientes a menudo pueden ser más costosos que generaciones anteriores
   * No todas las cargas de trabajo requieren características de las instancias más recientes
2. **Sobreaprovisionamiento**:
   * Proporcionar recursos que exceden los requisitos de la carga de trabajo
   * Produce costos innecesarios
3. **Limitaciones de disponibilidad**:
   * Los instance types más recientes pueden no estar disponibles en todas las regiones o availability zones
   * Disponibilidad especialmente limitada al usar Spot instances
4. **Problemas de compatibilidad**:
   * Algunas cargas de trabajo pueden estar optimizadas para instance types específicos
   * Se requieren pruebas al migrar a nuevos instance types

Para la optimización de costos, es importante considerar integralmente las características de la carga de trabajo, los requisitos de recursos, los requisitos de disponibilidad, etc., y seleccionar instance types y tamaños adecuados. Los instance types más recientes no siempre son la opción más rentable, y es más importante seleccionar instance types adecuados para la carga de trabajo.

</details>

3. ¿Cuál es la forma correcta de configurar un cluster privado en Amazon EKS?
   * A) Colocar nodos solo en subnets privadas y deshabilitar el endpoint público
   * B) Colocar nodos solo en subnets privadas y habilitar el endpoint público
   * C) Colocar nodos en subnets públicas y deshabilitar el endpoint público
   * D) Colocar nodos solo en subnets privadas sin VPC endpoints

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Colocar nodos solo en subnets privadas y deshabilitar el endpoint público**

**Explicación:** Para configurar un cluster completamente privado en Amazon EKS, necesitas colocar nodos solo en subnets privadas y deshabilitar el endpoint público. Esto garantiza que el Kubernetes API server del cluster no sea accesible desde internet y que todo el tráfico ocurra solo dentro de la VPC.

**Componentes de configuración de un cluster privado de EKS:**

1. **Configuración de acceso a endpoints**:
   * Deshabilitar endpoint público
   * Habilitar endpoint privado
   *   Ejemplo de configuración de AWS CLI:

       ```bash
       aws eks update-cluster-config \
         --name my-cluster \
         --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
       ```
   *   Ejemplo de configuración de eksctl:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       vpc:
         clusterEndpoints:
           publicAccess: false
           privateAccess: true
       ```
2. **Ubicación de nodos**:
   * Colocar nodos solo en subnets privadas
   * Sin asignación de IP pública
   *   Ejemplo de configuración de managed node group:

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name private-ng \
         --node-type m5.large \
         --nodes 3 \
         --node-private-networking \
         --subnet-ids subnet-private1,subnet-private2
       ```
3.  **Configuración de VPC endpoints**: VPC endpoints requeridos para que los clusters privados accedan a servicios de AWS:

    * com.amazonaws.region.ecr.api
    * com.amazonaws.region.ecr.dkr
    * com.amazonaws.region.s3
    * com.amazonaws.region.logs (opcional)
    * com.amazonaws.region.sts (opcional)

    ```bash
    # Create ECR API endpoint
    aws ec2 create-vpc-endpoint \
      --vpc-id vpc-12345 \
      --service-name com.amazonaws.us-west-2.ecr.api \
      --vpc-endpoint-type Interface \
      --subnet-ids subnet-private1 subnet-private2 \
      --security-group-ids sg-12345 \
      --private-dns-enabled

    # Create ECR Docker endpoint
    aws ec2 create-vpc-endpoint \
      --vpc-id vpc-12345 \
      --service-name com.amazonaws.us-west-2.ecr.dkr \
      --vpc-endpoint-type Interface \
      --subnet-ids subnet-private1 subnet-private2 \
      --security-group-ids sg-12345 \
      --private-dns-enabled

    # Create S3 endpoint (Gateway type)
    aws ec2 create-vpc-endpoint \
      --vpc-id vpc-12345 \
      --service-name com.amazonaws.us-west-2.s3 \
      --vpc-endpoint-type Gateway \
      --route-table-ids rtb-12345
    ```
4. **Configuración de red**:
   * NAT Gateway o VPC endpoints requeridos en subnets privadas
   * Restricción de tráfico con reglas de security group
   * Configuración de routing table

**Métodos para acceder a clusters privados:**

1. **Acceso mediante VPN o Direct Connect**:
   * AWS Client VPN
   * AWS Site-to-Site VPN
   * AWS Direct Connect
2.  **Acceso mediante Bastion Host**:

    * Colocar bastion host en subnet pública
    * Acceder al cluster API server desde bastion host

    ```bash
    # Configure kubeconfig on bastion host
    aws eks update-kubeconfig --name my-cluster --region us-west-2
    ```
3. **Acceso mediante AWS Systems Manager Session Manager**:
   * Acceder a instancias EC2 sin internet gateway
   * Control de acceso mediante permisos IAM y logging

**Problemas con las otras opciones:**

* **Colocar nodos solo en subnets privadas y habilitar endpoint público**: Cuando el endpoint público está habilitado, el cluster API server es accesible desde internet, por lo que no es un cluster completamente privado. El acceso se puede restringir con security groups o restricciones CIDR, pero sigue expuesto a redes públicas.
* **Colocar nodos en subnets públicas y deshabilitar endpoint público**: Cuando los nodos están en subnets públicas, pueden ser accedidos directamente desde internet, por lo que no es un cluster completamente privado. El acceso se puede restringir con security groups, pero los nodos pueden tener IPs públicas asignadas.
* **Colocar nodos solo en subnets privadas sin VPC endpoints**: Colocar nodos en subnets privadas sin VPC endpoints impide que los nodos accedan a servicios de AWS como ECR, S3, etc. En este caso, se requeriría acceso a internet mediante NAT Gateway, lo que no es una configuración de cluster completamente privado.

Los clusters privados de EKS son adecuados para entornos que requieren alta seguridad, ya que garantizan que todo el tráfico del cluster ocurra solo dentro de la VPC. Sin embargo, la configuración es más compleja, y puede necesitarse infraestructura adicional (VPN, Direct Connect, bastion hosts, etc.) para acceder al cluster.

</details>

4. ¿Cuál NO es una estrategia válida de actualización de node groups en clusters de Amazon EKS?
   * A) Rolling upgrade
   * B) Blue/Green deployment
   * C) In-place upgrade
   * D) Canary deployment

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) In-place upgrade**

**Explicación:** "In-place upgrade" no es una estrategia oficial de actualización para node groups de Amazon EKS. Los managed node groups de EKS usan un enfoque de rolling upgrade de forma predeterminada, y para self-managed node groups se pueden implementar estrategias como blue/green deployment o canary deployment.

**Estrategias de actualización de node groups de EKS:**

1. **Rolling Upgrade**:
   * Método de actualización predeterminado para managed node groups de EKS
   * Minimiza la interrupción de cargas de trabajo reemplazando los nodos uno a la vez
   * Proceso:
     1. Crear nodo nuevo
     2. Aplicar cordoning al nodo existente (evitar scheduling de pods nuevos)
     3. Drenar pods del nodo existente (migrar pods)
     4. Terminar el nodo existente
     5. Repetir para el siguiente nodo
   *   Ejemplo de configuración:

       ```bash
       # Managed node group upgrade
       aws eks update-nodegroup-version \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup

       # Check upgrade status
       aws eks describe-update \
         --name <update-id> \
         --nodegroup-name my-nodegroup \
         --cluster-name my-cluster
       ```
2. **Blue/Green Deployment**:
   * Crear un node group completamente nuevo y luego cambiar el tráfico
   * Rollback sencillo y bajo riesgo
   * El uso de recursos aumenta temporalmente (el doble de nodos en ejecución)
   * Pasos de implementación:
     1. Crear node group nuevo (green)
     2. Implementar y probar cargas de trabajo en el node group nuevo
     3. Cambiar el tráfico al node group nuevo
     4. Eliminar el node group existente (blue)
   *   Ejemplo de configuración:

       ```bash
       # Create new node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name my-nodegroup-v2 \
         --node-type m5.large \
         --nodes 3 \
         --node-ami-family AmazonLinux2

       # Check node labels
       kubectl get nodes --show-labels

       # Delete existing node group
       eksctl delete nodegroup \
         --cluster my-cluster \
         --name my-nodegroup-v1
       ```
3. **Canary Deployment**:
   * Minimizar el riesgo actualizando primero solo algunos nodos
   * Limita el alcance del impacto si ocurren problemas
   * Posible despliegue gradual
   * Pasos de implementación:
     1. Crear node group nuevo pequeño
     2. Mover algunas cargas de trabajo al node group nuevo
     3. Monitorear y verificar
     4. Actualizar los nodos restantes si no hay problemas
   *   Ejemplo de configuración:

       ```bash
       # Create canary node group (small scale)
       eksctl create nodegroup \
         --cluster my-cluster \
         --name canary-ng \
         --node-type m5.large \
         --nodes 1 \
         --node-labels "deployment=canary"

       # Deploy specific workloads to canary nodes
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: my-app
       spec:
         template:
           spec:
             nodeSelector:
               deployment: canary
       ```

**Problemas con las actualizaciones in-place:**

El término "in-place upgrade" puede significar actualizar nodos existentes sin terminarlos. Esto no es adecuado para node groups de EKS por las siguientes razones:

1. **Viola los principios de infraestructura inmutable**:
   * Los entornos cloud-native recomiendan reemplazar recursos en lugar de modificarlos
   * Evita la deriva de configuración de nodos
2. **Riesgo de fallo en la actualización**:
   * Los nodos pueden volverse inestables si falla la actualización in-place
   * El rollback es difícil
3. **Estructura de AMI de nodo de EKS**:
   * Las AMIs optimizadas para EKS tienen IDs de AMI diferentes por versión
   * La AMI no se puede cambiar mediante actualización in-place
4. **Limitaciones de managed node groups**:
   * Los managed node groups de EKS no admiten actualizaciones in-place
   * Siempre usan el método de rolling upgrade

**Prácticas recomendadas para actualizar node groups:**

1.  **Configurar PodDisruptionBudget**:

    * Garantiza la disponibilidad de la aplicación durante las actualizaciones

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
2. **Garantizar recursos suficientes**:
   * Se necesita capacidad de reserva para reubicar pods durante el drenaje de nodos
   * Considerar la configuración de Cluster Autoscaler
3. **Probar antes de actualizar**:
   * Probar actualizaciones primero en entornos no productivos
   * Verificar la compatibilidad de la aplicación
4. **Monitoreo mejorado**:
   * Monitorear el sistema durante y después de la actualización
   * Detección temprana de anomalías

Las actualizaciones de node groups de EKS son tareas importantes para aplicar parches de seguridad, correcciones de errores y nuevas características mientras se minimiza la interrupción de las cargas de trabajo. Elige estrategias como rolling upgrade, blue/green deployment o canary deployment según tu situación para realizar actualizaciones de forma segura.

</details>

5. ¿Qué NO ocurre durante el proceso de bootstrap de nodos en clusters de Amazon EKS?
   * A) Configuración e inicio de kubelet
   * B) Instalación de componentes del control plane del cluster
   * C) Configuración de AWS IAM Authenticator
   * D) Registro del nodo con el cluster

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Instalación de componentes del control plane del cluster**

**Explicación:** Durante el proceso de bootstrap de nodos de Amazon EKS, no se instalan componentes del control plane del cluster. EKS es un servicio administrado donde el control plane (API server, controller manager, scheduler, etc.) es administrado por AWS y se ejecuta por separado de los worker nodes. Durante el proceso de bootstrap de nodos, solo se realiza la configuración para conectar el nodo al cluster de EKS existente.

**Qué ocurre realmente durante el bootstrap de nodos de EKS:**

1. **Configuración e inicio de kubelet**:
   * Crear archivo de configuración de kubelet (`/etc/kubernetes/kubelet/kubelet-config.json`)
   * Configurar endpoint del cluster, certificados, DNS del cluster, etc.
   * Iniciar el servicio kubelet
   *   Ejemplo de configuración:

       ```json
       {
         "kind": "KubeletConfiguration",
         "apiVersion": "kubelet.config.k8s.io/v1beta1",
         "address": "0.0.0.0",
         "authentication": {
           "anonymous": {
             "enabled": false
           },
           "webhook": {
             "cacheTTL": "2m0s",
             "enabled": true
           },
           "x509": {
             "clientCAFile": "/etc/kubernetes/pki/ca.crt"
           }
         },
         "clusterDomain": "cluster.local",
         "clusterDNS": ["10.100.0.10"],
         "podCIDR": "",
         "maxPods": 58
       }
       ```
2. **Configuración de AWS IAM Authenticator**:
   * Configurar aws-iam-authenticator para autenticación IAM
   * Crear archivo kubeconfig
   * Configurar node IAM role
   *   Ejemplo de configuración:

       ```yaml
       apiVersion: v1
       kind: Config
       clusters:
       - cluster:
           certificate-authority: /etc/kubernetes/pki/ca.crt
           server: https://my-cluster.eks.amazonaws.com
         name: kubernetes
       contexts:
       - context:
           cluster: kubernetes
           user: kubelet
         name: kubelet
       current-context: kubelet
       users:
       - name: kubelet
         user:
           exec:
             apiVersion: client.authentication.k8s.io/v1beta1
             command: aws-iam-authenticator
             args:
               - token
               - -i
               - my-cluster
               - --role
               - arn:aws:iam::123456789012:role/EKSNodeRole
       ```
3. **Registro del nodo con el cluster**:
   * Crear objeto node
   * Establecer labels y taints del nodo
   * Registrarse con el cluster API server
   *   Ejemplo de log:

       ```
       Node my-node-1 successfully registered with API server
       ```
4. **Configuración del CNI plugin**:
   * Configurar Amazon VPC CNI plugin
   * Configurar networking de pods
   * Configurar asignación de direcciones IP
   *   Ejemplo de configuración:

       ```json
       {
         "cniVersion": "0.3.1",
         "name": "aws-vpc",
         "plugins": [
           {
             "name": "aws-vpc",
             "type": "vpc-cni",
             "vethPrefix": "eni",
             "mtu": "9001",
             "ipam": {
               "type": "aws-cni"
             }
           }
         ]
       }
       ```
5. **Configuración de kube-proxy**:
   * Configurar kube-proxy para networking del cluster
   * Configurar enrutamiento de IPs de service
   *   Ejemplo de configuración:

       ```yaml
       apiVersion: kubeproxy.config.k8s.io/v1alpha1
       kind: KubeProxyConfiguration
       bindAddress: 0.0.0.0
       clientConnection:
         acceptContentTypes: ""
         burst: 10
         contentType: application/vnd.kubernetes.protobuf
         kubeconfig: /var/lib/kube-proxy/kubeconfig
         qps: 5
       ```
6. **Aplicación de labels y taints de nodos**:
   * Establecer labels basados en instance type, availability zone, etc.
   * Aplicar labels personalizados
   * Aplicar taints si es necesario
   *   Ejemplo de comandos:

       ```bash
       kubectl label node my-node-1 eks.amazonaws.com/nodegroup=my-nodegroup
       kubectl label node my-node-1 topology.kubernetes.io/zone=us-west-2a
       ```

**Bootstrap script:**

El bootstrap de nodos de EKS se realiza mediante el script `/etc/eks/bootstrap.sh`. Este script puede recibir los siguientes parámetros:

```bash
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker' \
  --b64-cluster-ca <base64-encoded-ca> \
  --apiserver-endpoint <api-server-endpoint> \
  --dns-cluster-ip 10.100.0.10
```

Al usar un launch template personalizado, puedes llamar a este script en la sección user data para realizar configuración adicional:

```bash
#!/bin/bash
set -ex
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=environment=prod,node-type=worker' \
  --max-pods 110
```

**Componentes del control plane del cluster:**

Los componentes del control plane del cluster de EKS son administrados por AWS y están separados del proceso de bootstrap de nodos:

* API server
* Controller manager
* Scheduler
* etcd
* CoreDNS

Estos componentes se ejecutan en infraestructura administrada por AWS y garantizan alta disponibilidad y escalabilidad. Los nodos solo se conectan a estos componentes del control plane; no los instalan ni administran directamente.

Por lo tanto, lo que NO ocurre durante el bootstrap de nodos de Amazon EKS es la "instalación de componentes del control plane del cluster".

</details>
