# Creación de clúster de EKS

> **Última actualización**: October 12, 2026

Hay varias formas de crear un clúster de Amazon EKS. En este capítulo, aprenderemos en detalle cómo crear un clúster de EKS mediante diversas herramientas y métodos.

Los métodos de creación de este capítulo son alternativas. Elija uno para un nuevo clúster dedicado y no administre los mismos recursos con varias herramientas simultáneamente. Reemplace los nombres, cuentas, roles, VPC, subredes y CIDR de ejemplo por valores reales aprobados. Los ejemplos de shell usan Bash salvo que se indique lo contrario; deténgase si fallan los requisitos previos. Durante esta auditoría no se realizó aprovisionamiento de AWS ni medición de cargas de trabajo.

**Versión actual:** EKS 1.37 estuvo disponible el 1 de octubre de 2026.

**Referencia de ejemplo:** Los ejemplos siguientes conservan la referencia revisada de EKS 1.36. Al seleccionar otra versión, consulte el [calendario de versiones actuales de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) y la documentación sobre compatibilidad de componentes.

## Tabla de contenido

1. [Requisitos previos](#prerequisites)
2. [Crear un clúster mediante eksctl](#creating-a-cluster-using-eksctl)
3. [Crear un clúster mediante AWS Management Console](#creating-a-cluster-using-aws-management-console)
4. [Crear un clúster mediante AWS CLI](#creating-a-cluster-using-aws-cli)
5. [Crear un clúster mediante Terraform](#creating-a-cluster-using-terraform)
6. [Crear un clúster mediante AWS CDK](#creating-a-cluster-using-aws-cdk)
7. [Configurar el acceso al clúster](#configuring-cluster-access)
8. [Validación del clúster](#cluster-validation)
9. [Actualización del clúster](#cluster-upgrade)
10. [Eliminación del clúster](#cluster-deletion)

## Requisitos previos

Antes de crear un clúster de EKS, se requieren los siguientes requisitos previos:

### 1. Cuenta de AWS

Se requiere una cuenta de AWS válida. Si no tiene una cuenta de AWS, puede registrarse en el [sitio web de AWS](https://aws.amazon.com/).

### 2. Permisos de IAM

Los permisos requeridos dependen de la herramienta y de los recursos que esta administra. Una política que conceda `eks:*`, `ec2:*`, `iam:*` y `cloudformation:*` sobre cada recurso no es una política obligatoria de privilegio mínimo.

| Tarea | Ámbito de permisos que se debe revisar |
| --- | --- |
| Administración de clústeres/grupos de nodos de EKS | Acciones de EKS requeridas y recursos de destino |
| Transferencia de roles de IAM existentes | `iam:PassRole` para ARN de roles aprobados y condiciones de servicio |
| Creación de roles/políticas/proveedores de OIDC de IAM | Recursos de IAM administrados por la herramienta y ámbito de nombre/etiqueta |
| Creación de redes | Acciones de EC2 para la nueva VPC, subredes y grupos de seguridad |
| Uso de eksctl/CDK | Stacks de CloudFormation pertinentes, roles de ejecución y recursos de bootstrap |

La identidad de aprovisionamiento, el rol de servicio del clúster y el rol de nodo son independientes. Las SCP, los límites de permisos y las políticas de sesión siguen aplicándose. Revise los permisos de aprovisionamiento de su organización frente a la plantilla o el plan sintetizados. Los requisitos de roles de Auto Mode difieren de los de los grupos de nodos convencionales.

Referencias: [acciones y recursos de IAM para EKS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html), [roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

### 3. Instalación de herramientas

#### AWS CLI

Elija el paquete para su SO/CPU y siga la verificación de firma de la [guía oficial de instalación de AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Para una instalación existente de v1/v2, revise primero su procedimiento de actualización o migración.

| Entorno | Método oficial de paquete/instalación |
| --- | --- |
| macOS | `AWSCLIV2.pkg` firmado |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` con verificación de firma PGP |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` con verificación de firma PGP |
| Windows | Instalador MSI para las versiones compatibles de Windows |

No use sin cambios el paquete de Linux x86_64 en ARM. Compruebe la CLI activa con `aws --version`. Si su organización usa IAM Identity Center, configure un perfil aprobado como se muestra a continuación. De lo contrario, siga su procedimiento de federación en lugar de asumir claves de acceso de larga duración.

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

Consulte la [autenticación de IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). Continúe usando la cuenta, el rol y la región aprobados para los comandos posteriores.

#### kubectl y eksctl — Linux/macOS

Los ejemplos de EKS 1.36 de este capítulo usan kubectl **1.36.4** y eksctl **0.230.0** como referencia. Prefiera la misma versión secundaria de kubectl que el servidor; la desviación admitida es ±1 versión secundaria. No instale a ciegas la versión secundaria más reciente desde `stable.txt` upstream para un clúster de EKS anterior.

Este ejemplo de Bash selecciona AMD64/ARM64 y verifica las sumas de comprobación oficiales antes de la instalación. Necesita `curl`, `tar`, `awk` y `sha256sum` o `shasum`; la instalación en `/usr/local/bin` requiere permisos de administrador. La descarga o el fallo de la suma de comprobación detiene la instalación.

```bash
(
  set -e
  case "$(uname -s)" in
    Linux) EKS_TOOL_OS=linux; EKS_ARCHIVE_OS=Linux ;;
    Darwin) EKS_TOOL_OS=darwin; EKS_ARCHIVE_OS=Darwin ;;
    *) printf 'Use the official installer for this operating system\n' >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64) EKS_TOOL_ARCH=amd64 ;;
    aarch64|arm64) EKS_TOOL_ARCH=arm64 ;;
    *) printf 'Select a supported CPU architecture\n' >&2; exit 1 ;;
  esac
  EKS_TOOL_ARCHIVE="eksctl_${EKS_ARCHIVE_OS}_${EKS_TOOL_ARCH}.tar.gz"
  EKS_TOOL_DIR=$(mktemp -d)
  : "${EKS_TOOL_DIR:?}"
  trap 'rm -f -- "$EKS_TOOL_DIR/kubectl" "$EKS_TOOL_DIR/kubectl.sha256" "$EKS_TOOL_DIR/eksctl" "$EKS_TOOL_DIR/eksctl_checksums.txt" "$EKS_TOOL_DIR/$EKS_TOOL_ARCHIVE" "$EKS_TOOL_DIR/selected.sha256"; rmdir -- "$EKS_TOOL_DIR"' EXIT
  cd "$EKS_TOOL_DIR" || exit 1
  verify_sha() {
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum --check "$1"
    else
      shasum -a 256 --check "$1"
    fi
  }
  EKS_KUBECTL_VERSION=v1.36.4
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl" -o kubectl || exit 1
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl.sha256" -o kubectl.sha256 || exit 1
  printf '%s  kubectl\n' "$(tr -d '[:space:]' < kubectl.sha256)" > selected.sha256
  verify_sha selected.sha256 || exit 1

  EKSCTL_VERSION=0.230.0
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/$EKS_TOOL_ARCHIVE" -o "$EKS_TOOL_ARCHIVE" || exit 1
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/eksctl_checksums.txt" -o eksctl_checksums.txt || exit 1
  awk -v name="$EKS_TOOL_ARCHIVE" '$2 == name {print; count++} END {if (count != 1) exit 1}' \
    eksctl_checksums.txt > selected.sha256 || exit 1
  verify_sha selected.sha256 || exit 1
  tar -xzf "$EKS_TOOL_ARCHIVE" eksctl || exit 1
  sudo install -m 0755 kubectl /usr/local/bin/kubectl || exit 1
  sudo install -m 0755 eksctl /usr/local/bin/eksctl || exit 1
  kubectl version --client
  eksctl version
)
```

Procedimientos oficiales: [kubectl en Linux](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/), [kubectl en macOS](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/), [instalación de eksctl](https://eksctl.io/installation/).

#### Windows

Siga el [procedimiento oficial de instalación de kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) en PowerShell. Para el ejemplo AMD64 de este capítulo, use [kubectl 1.36.4](https://dl.k8s.io/release/v1.36.4/bin/windows/amd64/kubectl.exe) y el archivo `.sha256` en la misma ruta. Seleccione el ZIP de Windows correspondiente a su CPU y `eksctl_checksums.txt` de la [versión de eksctl 0.230.0](https://github.com/eksctl-io/eksctl/releases/tag/v0.230.0).

Compare `Get-FileHash -Algorithm SHA256` con el hash oficial y deténgase si no coincide. Después de la verificación, extraiga el ZIP, agregue el directorio de ejecutables a PATH y compruebe `kubectl version --client` y `eksctl version`. No ejecute sintaxis de PowerShell en Bash.

Prepare también `jq` para la generación de JSON en los ejemplos de AWS CLI. Durante esta auditoría no se realizó ninguna descarga, instalación ni inicio de sesión real de clientes.

### 4. VPC y subredes

Un clúster regional de EKS requiere al menos dos subredes en distintas AZ de la misma VPC. Cada subred del clúster necesita al menos seis IP disponibles para EKS; AWS recomienda al menos dieciséis. Planifique direcciones adicionales para nodos, Pods, balanceadores de carga y actualizaciones. Habilite los nombres de host DNS y la resolución DNS de la VPC.

El acceso a Internet no es obligatorio para todos los clústeres de EKS. Los nodos y las cargas de trabajo necesitan acceso a la API de Kubernetes, las imágenes y los servicios de AWS requeridos mediante rutas NAT/Internet o los endpoints de VPC e imágenes replicadas necesarios. El endpoint privado de Kubernetes es accesible desde la VPC o las redes conectadas con DNS y enrutamiento adecuados.

#### Etiquetas de VPC para el clúster de EKS

La etiqueta de VPC `kubernetes.io/cluster/<cluster-name>` es un mecanismo heredado, no un requisito universal actual para la creación de EKS. Siga las reglas de descubrimiento de subredes del controlador elegido para el balanceo de carga:

- Subredes para balanceadores de carga públicos: `kubernetes.io/role/elb=1`
- Subredes para balanceadores de carga internos: `kubernetes.io/role/internal-elb=1`

Las etiquetas no configuran el enrutamiento, los grupos de seguridad ni la capacidad de IP libre. Consulte los [requisitos de VPC/subred](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) y los [clústeres sin acceso a Internet](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html).

## Crear un clúster mediante eksctl

eksctl es la forma más sencilla de crear y administrar clústeres de EKS. eksctl usa CloudFormation para crear clústeres de EKS y recursos relacionados.

Almacene el kubeconfig de eksctl en una ruta dedicada para este shell.

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### Creación básica de clúster

Cree el clúster básico a partir de un archivo de configuración revisado:

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

Lea y edite el siguiente `cluster.yaml` antes de ejecutar este comando. Selecciona explícitamente EKS 1.36, AL2023, subredes de VPC existentes y capacidades de grupos de nodos. Reemplace los identificadores de ejemplo y el CIDR de documentación por valores reales aprobados. Estas son configuraciones seleccionadas, no afirmaciones sobre los valores predeterminados de cada versión de eksctl.

### Crear un clúster mediante un archivo de configuración

Para configuraciones más complejas, puede definir el clúster mediante un archivo YAML:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: '1.36'
vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
managedNodeGroups:
- name: ng-1
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
  privateNetworking: true
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
- name: ng-2
  instanceType: c5.xlarge
  desiredCapacity: 2
  privateNetworking: true
  spot: true
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
fargateProfiles:
- name: fp-default
  selectors:
  - namespace: default
    labels:
      env: fargate
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
```

Para crear un clúster mediante este archivo de configuración, ejecute el siguiente comando:

```bash
eksctl create cluster -f cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

La configuración anterior demuestra nodos de EC2 y un perfil de Fargate de aplicación opcional. CoreDNS permanece en EC2; moverlo a Fargate requiere revisar tanto la configuración de cómputo de CoreDNS como el perfil.

### Crear grupos de nodos administrados

Para agregar un grupo de nodos administrado a un clúster existente, ejecute el siguiente comando:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking
```

También puede usar un archivo de configuración:

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: my-nodegroup
  instanceType: m5.large
  desiredCapacity: 3
  minSize: 1
  maxSize: 5
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  privateNetworking: true
  disableIMDSv1: true
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### Crear un clúster de EKS Auto Mode

EKS Auto Mode pasó a estar disponible de forma general en 2024 y automatiza la infraestructura del clúster de Kubernetes para reducir la sobrecarga operativa. AWS administra sus capacidades de cómputo, red y almacenamiento.

#### Características principales de EKS Auto Mode

- **Administración automatizada de nodos**: Agrega o elimina nodos automáticamente según los requisitos de la carga de trabajo
- **Seguridad mejorada**: AMI inmutable, modo de aplicación de SELinux y sistema de archivos raíz de solo lectura
- **Mantenimiento de nodos**: Los nodos se reemplazan por expiración y desviación. Veintiún días no es un ciclo de actualización de versión secundaria del plano de control
- **Componentes integrados**: Redes de Pod, DNS, almacenamiento y compatibilidad con GPU proporcionados de forma predeterminada
- **Optimización de costos**: Terminación automática de instancias no utilizadas y consolidación de cargas de trabajo

#### Creación básica de clúster de Auto Mode

Revise primero el CIDR y la red en el siguiente `auto-cluster.yaml`. No duplique las redes, DNS y almacenamiento de bloques de Auto Mode con complementos autoadministrados. Los clústeres mixtos necesitan una ubicación explícita y ámbito de componentes para cada tipo de cómputo.

```bash
eksctl create cluster --config-file auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Crear un clúster de Auto Mode mediante un archivo de configuración

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-auto-cluster
  region: us-west-2
  version: '1.36'
autoModeConfig:
  enabled: true
  nodePools:
  - system
  - general-purpose
vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: Single
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
accessConfig:
  authenticationMode: API
```

Crear clúster:
```bash
eksctl create cluster -f auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Comparación entre Auto Mode y el enfoque tradicional

| Característica | EKS tradicional | EKS Auto Mode |
|---------|-----------------|---------------|
| Administración de nodos | Grupos de nodos administrados o nodos administrados por el cliente | Ciclo de vida de nodos administrado por AWS |
| Escalado | Configure Cluster Autoscaler, Karpenter autoadministrado u otra estrategia | Escalado automático de nodos administrado |
| Actualizaciones | Planifique las actualizaciones del plano de control, nodos y complementos | AWS administra las actualizaciones de nodos/componentes; planifique las versiones secundarias del plano de control según la política de soporte |
| Seguridad | Configurada por el usuario | Seguridad mejorada de forma predeterminada |
| Redes | Configuración del complemento CNI | Configuración de red automática |
| Almacenamiento | Se requieren instalación y permisos de CSI | Aprovisionador de EBS administrado `ebs.csi.eks.amazonaws.com` |
| Compatibilidad con GPU | Seleccione AMI aceleradas compatibles y complementos de dispositivos requeridos | Controladores/complementos administrados para instancias compatibles |

#### Validación de clúster de Auto Mode

Después de crear el clúster, puede comprobar su estado con los siguientes comandos:

```bash
# Check cluster status
kubectl get nodes

# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check system pod status
kubectl get pods -n kube-system
```

#### Crear Node Pools personalizados

En Auto Mode, puede crear Node Pools personalizados además de los Node Pools predeterminados:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-nodepool
spec:
  template:
    metadata:
      labels:
        workload-type: gpu
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.2xlarge
        - p3.8xlarge
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 336h
      taints:
      - key: nvidia.com/gpu
        value: present
        effect: NoSchedule
  limits:
    cpu: '1000'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

> **Nota**: En Auto Mode no puede usar `EC2NodeClass`, `amiFamily` ni `userData` personalizado (`/etc/eks/bootstrap.sh`). AWS administra la AMI de nodo y el bootstrap; las subredes, los grupos de seguridad y el almacenamiento efímero se definen a través de un `NodeClass` de `eks.amazonaws.com/v1`.

El ejemplo de GPU conserva p3, que está en la lista oficial actual de tipos compatibles. Compruebe la capacidad de las AZ, las cuotas y los requisitos de memoria/modelo de GPU. Los Pods de GPU deben solicitar `nvidia.com/gpu` y tolerar la contaminación anterior. Este YAML fue revisado; no se aprovisionó ni se sometió a pruebas de rendimiento ningún nodo de GPU.

#### Limitaciones de Auto Mode

- No hay acceso directo a nodos mediante SSH o SSM
- La expiración predeterminada es de 336 horas (14 días), con una configuración máxima admitida de `expireAfter` de 21 días. Revise conjuntamente los bloqueadores de drenaje, PDB/NodePool y el período de gracia de terminación predeterminado de 24 horas
- No se pueden modificar los Node Pools y las clases de nodo predeterminados
- Posibles restricciones para determinados tipos de instancia

#### Monitorización de Auto Mode

La infraestructura administrada no configura automáticamente las métricas de CloudWatch de todas las cargas de trabajo. `cluster_node_count` pertenece a **ContainerInsights**, no a `AWS/EKS`, y requiere una canalización de recopilación de Container Insights configurada. Configure la recopilación para su entorno y consulte un intervalo de tiempo con datos reales.

```bash
# Requires a configured Container Insights collection pipeline and metric data.
aws cloudwatch list-metrics --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --start-time "${METRICS_START_TIME:?Set a reviewed ISO8601 start time}" \
  --end-time "${METRICS_END_TIME:?Set a later ISO8601 end time}" \
  --period 3600 --statistics Average
```

Un resultado vacío no demuestra que haya cero nodos ni un fallo de Auto Mode. Compruebe primero la recopilación, las dimensiones y el intervalo de tiempo. No se ejecutaron consultas ni mediciones de CloudWatch durante esta auditoría. Consulte el [catálogo oficial de métricas de Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html).

### Crear perfiles de Fargate

Para crear un perfil de Fargate, ejecute el siguiente comando:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

También puede usar un archivo de configuración:

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: my-fargate-profile
  selectors:
  - namespace: default
    labels:
      env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### Actualizar un clúster

Revise la compatibilidad del plano de control, los nodos y los complementos; luego siga [Actualización del clúster](#cluster-upgrade).

### Eliminar un clúster

Revise las cargas de trabajo, los balanceadores de carga, la retención de datos y la herramienta propietaria; luego siga [Eliminación del clúster](#cluster-deletion).

## Crear un clúster mediante AWS Management Console

Los pasos para crear un clúster de EKS mediante AWS Management Console son los siguientes:

1. Inicie sesión en la [AWS Management Console](https://console.aws.amazon.com/).
2. Busque "EKS" o seleccione "Elastic Kubernetes Service" en la lista de servicios.
3. En la página "Clusters", haga clic en el botón "Create cluster".

### Crear un clúster de EKS Auto Mode (configuración rápida)

EKS Auto Mode reduce la configuración de infraestructura. La identidad de carga de trabajo, la red, la capacidad, la disponibilidad y la recuperación aún requieren configuración y validación explícitas.

#### 1. Seleccionar configuración rápida

4. Asegúrese de que esté seleccionada la opción "Quick configuration".
5. Introduzca la siguiente información:
   - **Nombre del clúster**: Introduzca un nombre único para el clúster.
   - **Versión de Kubernetes**: Seleccione la versión de Kubernetes que desea usar (se recomienda la versión más reciente).

#### 2. Configurar roles de IAM

6. Selección de **rol de IAM del clúster**:
   - Para su primer clúster de Auto Mode, use la opción "Create recommended role".
   - Si tiene un rol existente, puede reutilizarlo.
   - Nombre de rol recomendado: `AmazonEKSAutoClusterRole`

7. Selección de **rol de IAM de nodo**:
   - Para su primer clúster de Auto Mode, use la opción "Create recommended role".
   - Nombre de rol recomendado: `AmazonEKSAutoNodeRole`

#### 3. Configurar redes

8. **Seleccionar VPC**:
   - Crear una VPC nueva: Seleccione la opción "Create VPC" para crear una VPC nueva para EKS.
   - Usar una VPC existente: Seleccione una VPC de EKS creada anteriormente.

9. **Configuración de subredes** (opcional):
   - EKS Auto Mode selecciona automáticamente las subredes privadas de la VPC.
   - Puede agregar o eliminar subredes según sea necesario.

#### 4. Revisar la configuración y crear

10. Seleccione **View quick configuration defaults** para revisar todos los valores de configuración.
11. Haga clic en **Create cluster**. (La creación del clúster tarda aproximadamente 15 minutos)

### Crear un clúster con configuración personalizada

Si necesita un control más granular, puede usar una configuración personalizada.

### Configuración del clúster

4. En la página "Configure cluster", introduzca la siguiente información:
   - **Nombre del clúster**: Introduzca un nombre único para el clúster.
   - **Versión de Kubernetes**: Seleccione la versión de Kubernetes que desea usar.
   - **Rol de servicio del clúster**: Cree un rol nuevo o seleccione uno existente.
   - **EKS Auto Mode**: Marque la casilla para habilitar Auto Mode.
   - **Etiquetas**: Agregue etiquetas si es necesario.
   - Haga clic en el botón "Next".

### Especificar redes

5. En la página "Specify networking", introduzca la siguiente información:
   - **VPC**: Cree una VPC nueva o seleccione una VPC existente.
   - **Subredes**: Seleccione las subredes que desea usar para el clúster. Al menos 2 subredes deben estar en distintas zonas de disponibilidad.
   - **Grupos de seguridad**: Seleccione los grupos de seguridad que desea usar para el clúster.
   - **Acceso al endpoint del clúster**: Configure el acceso al endpoint del servidor de API del clúster.
     - **Público**: Se puede acceder al servidor de API desde Internet.
     - **Privado**: El acceso desde la VPC o las redes conectadas requiere DNS y enrutamiento adecuados.
     - **Público y privado**: Se puede acceder al servidor de API tanto desde Internet como desde la VPC.
   - Haga clic en el botón "Next".

### Configurar el registro

6. En la página "Configure logging", introduzca la siguiente información:
   - **Registro del plano de control**: Seleccione los tipos de registro que desea habilitar.
     - Registros del servidor de API
     - Registros de auditoría
     - Registros de autenticador
     - Registros de controller manager
     - Registros de scheduler
   - Haga clic en el botón "Next".

### Seleccionar complementos

Los siguientes complementos describen cómputo convencional. Auto Mode administra capacidades superpuestas de red, DNS y almacenamiento de bloques; seleccione componentes de acuerdo con los tipos de cómputo de su clúster.

7. En la página "Select add-ons", introduzca la siguiente información:
   - **Amazon VPC CNI**: Complemento CNI para redes de Pod.
   - **CoreDNS**: Servicio DNS dentro del clúster.
   - **kube-proxy**: Proporciona proxy de red y balanceo de carga.
   - **Complementos de almacenamiento/red**: El cómputo convencional necesita los componentes instalados y permisos de IAM apropiados. Auto Mode proporciona capacidades administradas de EBS/red/DNS; no instale componentes superpuestos en nodos de Auto Mode.
   - Haga clic en el botón "Next".

### Revisar y crear

8. En la página "Review and create", revise la configuración y haga clic en el botón "Create".

### Agregar grupos de nodos para clústeres que no son de Auto Mode

Para cómputo convencional de EC2, agregue grupos de nodos después de crear el clúster. Otras opciones compatibles, como los perfiles de Fargate, tienen su propia configuración; un grupo de nodos administrado no es obligatorio para todos los clústeres que no son de Auto Mode.

### Agregar grupo de nodos

1. En la página "Node group configuration", introduzca la siguiente información:
   - **Nombre de grupo de nodos**: Introduzca un nombre único para el grupo de nodos.
   - **Rol de IAM de nodo**: Cree un rol nuevo o seleccione uno existente.
   - Haga clic en el botón "Next".

2. En la página "Set compute and scaling configuration", introduzca la siguiente información:
   - **Tipo de AMI**: Seleccione el tipo de AMI que desea usar para los nodos.
   - **Tipo de instancia**: Seleccione el tipo de instancia de EC2 que desea usar para los nodos.
   - **Tamaño de disco**: Especifique el tamaño de disco para los nodos.
   - **Recuento de nodos**: Especifique la cantidad mínima, máxima y deseada de nodos.
   - Haga clic en el botón "Next".

3. En la página "Specify networking", introduzca la siguiente información:
   - **Subredes**: Seleccione las subredes que desea usar para el grupo de nodos.
   - **Configuración de acceso remoto**: Deje SSH deshabilitado a menos que una ruta de administración aprobada lo requiera; no especifique una clave SSH sin revisar los grupos de seguridad de origen.
   - Haga clic en el botón "Next".

4. En la página "Review and create", revise la configuración y haga clic en el botón "Create".

## Crear un clúster mediante AWS CLI

Estos ejemplos crean un **clúster nuevo**. Elija Auto Mode o EKS convencional; no ejecute ambos comandos de creación consecutivamente con el mismo nombre. Use Bash, `jq`, una AWS CLI v2 actual y un rol de AWS autorizado. EKS 1.36 es la versión de ejemplo verificada; revise la compatibilidad regional y de componentes antes de seleccionar otra versión.

Las dos subredes deben estar en distintas AZ de la misma VPC. Prepare por separado DNS, IP libres, grupos de seguridad y acceso de los nodos a imágenes/servicios. Los nombres de campo de API reales son `endpointPrivateAccess` y `endpointPublicAccess`. El acceso de administrador del creador inicializa este ejemplo dedicado; administre el acceso posterior mediante entradas de acceso.

### Preparar entradas comunes

Cree previamente el rol de clúster para el modo seleccionado y compruebe los permisos requeridos de `iam:PassRole` y creación de roles vinculados al servicio. Revise la cuenta, región, subredes y CIDR aprobados antes de ejecutar un comando de creación.

```bash
: "${EKS_CLUSTER_NAME:?Choose a unique new cluster name}"
: "${EKS_REGION:?Choose the intended AWS region}"
: "${EKS_CLUSTER_ROLE_ARN:?Pre-created cluster role for the chosen mode}"
: "${EKS_SUBNET_A:?Existing subnet in the intended VPC}"
: "${EKS_SUBNET_B:?Existing subnet in a different AZ of the same VPC}"
: "${EKS_PUBLIC_API_CIDR:?Approved client CIDR, normally /32}"
EKS_CREATION_DIR=$(mktemp -d /tmp/eks-create.XXXXXX)
: "${EKS_CREATION_DIR:?}"
EKS_KUBECONFIG="$EKS_CREATION_DIR/kubeconfig"
unset EKS_CREATED_CLUSTER_ARN
aws sts get-caller-identity
```

### Crear un clúster de EKS Auto Mode

El rol de clúster necesita confianza de `sts:AssumeRole` y `sts:TagSession` para `eks.amazonaws.com`, con `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy` y `AmazonEKSNetworkingPolicy`, o permisos personalizados equivalentes.

El rol de nodo confía en `ec2.amazonaws.com` y usa `AmazonEKSWorkerNodeMinimalPolicy` más `AmazonEC2ContainerRegistryPullOnly`. Conceda permisos de AWS a las cargas de trabajo por separado mediante Pod Identity/IRSA. Habilite juntos cómputo, balanceo de carga y almacenamiento de bloques, y deshabilite el bootstrap de los complementos autoadministrados predeterminados.

```bash
: "${EKS_AUTO_NODE_ROLE_ARN:?Pre-created Auto Mode node role}"
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  --arg nodeRole "$EKS_AUTO_NODE_ROLE_ARN" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: false,
  computeConfig: {
    enabled: true, nodePools: ["system", "general-purpose"], nodeRoleArn: $nodeRole
  },
  kubernetesNetworkConfig: {ipFamily: "ipv4", elasticLoadBalancing: {enabled: true}},
  storageConfig: {blockStorage: {enabled: true}}
}' > "${EKS_CREATION_DIR:?}/create-auto.json"
cat "$EKS_CREATION_DIR/create-auto.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-auto.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### Verificar la creación y el acceso

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

Auto Mode puede no tener nodos antes de que las cargas de trabajo los requieran. Compruebe el estado de NodePool/NodeClass y la programación posterior de Pods. Que el clúster esté en `ACTIVE` no demuestra el estado de la aplicación ni garantiza una duración de creación fija.

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### Crear un clúster convencional

Use esta alternativa solo si no seleccionó Auto Mode. El rol de clúster necesita permisos convencionales de clúster de EKS; el rol de nodo de EC2 y los permisos de CNI/complementos son independientes. Inicializar los complementos de red predeterminados no instala EBS CSI ni AWS LBC.

```bash
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: true,
  kubernetesNetworkConfig: {ipFamily: "ipv4"}
}' > "${EKS_CREATION_DIR:?}/create-standard.json"
cat "$EKS_CREATION_DIR/create-standard.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-standard.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### Esperar la creación y configurar kubeconfig

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

#### Crear un grupo de nodos administrado

Prepare permisos de extracción de nodos de trabajo y ECR para el rol de nodo de EC2, y un rol de CNI independiente o permisos de CNI del rol de nodo revisados. No reutilice sin cambios el rol de nodo mínimo de Auto Mode. Las subredes privadas también requieren NAT o los endpoints de VPC necesarios. Este ejemplo de AL2023 no habilita SSH de forma predeterminada.

```bash
: "${EKS_MANAGED_NODE_ROLE_ARN:?Pre-created conventional EC2 node role}"
: "${EKS_NODEGROUP_NAME:?Unique managed node group name}"
aws eks create-nodegroup \
  --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" \
  --subnets "${EKS_SUBNET_A:?}" "${EKS_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --node-role "$EKS_MANAGED_NODE_ROLE_ARN" \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 --region "${EKS_REGION:?}"

aws eks wait nodegroup-active --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
aws eks describe-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version}' --output json
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodes
```

`minSize`/`maxSize` por sí solos no habilitan el escalado de nodos basado en la demanda de Pods. Inspeccione los errores de estado y salud y, después, configure un escalador automático si es necesario. Si falla la creación, inspeccione los nombres/ARN registrados y los recursos relacionados. Estos comandos de creación y espera no se ejecutaron durante la auditoría.

Referencias: [API CreateCluster](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html), [API CreateNodegroup](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [IAM y creación de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Crear un clúster mediante Terraform

El siguiente ejemplo completo admite **un clúster nuevo**, eligiendo Auto Mode o un grupo de nodos administrado convencional antes del primer apply. No agregue la alternativa como un segundo recurso de clúster ni alterne un clúster existente sin un plan de migración. El estado de Terraform y su archivo de bloqueo del proveedor pertenecen a esta implementación específica.

### Configuración de Terraform para un clúster de EKS Auto Mode

Guarde como `main.tf`. El ejemplo fija el proveedor de AWS **6.64.0** y usa EKS **1.36**. Proporcione explícitamente los ID de subredes privadas existentes; una etiqueta personalizada `Type=Private` no es un sustituto fiable de verificar rutas y conectividad. La precondición comprueba las relaciones de VPC/AZ durante la planificación, pero no verifica el enrutamiento privado, los endpoints de servicio, DNS, la capacidad de IP ni las etiquetas de subred de los balanceadores de carga.

Auto Mode necesita cómputo, balanceo de carga y almacenamiento de bloques habilitados conjuntamente, con `bootstrap_self_managed_addons = false`. El rol de clúster incluye `sts:TagSession` y las cinco políticas requeridas. Las dependencias de adjuntos de IAM preservan los permisos mientras EKS elimina la infraestructura administrada.

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_partition" "current" {}
data "aws_subnet" "selected" {
  for_each = toset(var.private_subnet_ids)
  id       = each.value
}

locals {
  cluster_policies = var.enable_auto_mode ? toset([
    "AmazonEKSClusterPolicy",
    "AmazonEKSComputePolicy",
    "AmazonEKSBlockStoragePolicyV2",
    "AmazonEKSLoadBalancingPolicy",
    "AmazonEKSNetworkingPolicy",
  ]) : toset(["AmazonEKSClusterPolicy"])
  node_policies = var.enable_auto_mode ? toset([
    "AmazonEKSWorkerNodeMinimalPolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    ]) : toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    # Conventional bootstrap baseline; see the CNI role caveat in the text.
    "AmazonEKS_CNI_Policy",
  ])
}

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = var.enable_auto_mode ? ["sts:AssumeRole", "sts:TagSession"] : ["sts:AssumeRole"]
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  for_each   = local.cluster_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["sts:AssumeRole"]
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each   = local.node_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.node.name
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }
  bootstrap_self_managed_addons = !var.enable_auto_mode

  compute_config {
    enabled       = var.enable_auto_mode
    node_pools    = var.enable_auto_mode ? ["system", "general-purpose"] : null
    node_role_arn = var.enable_auto_mode ? aws_iam_role.node.arn : null
  }
  kubernetes_network_config {
    ip_family = "ipv4"
    elastic_load_balancing {
      enabled = var.enable_auto_mode
    }
  }
  storage_config {
    block_storage {
      enabled = var.enable_auto_mode
    }
  }
  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_api_cidrs
  }
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Keep policies attached until EKS finishes deleting managed infrastructure.
  depends_on = [
    aws_iam_role_policy_attachment.cluster,
    aws_iam_role_policy_attachment.node,
  ]
  lifecycle {
    precondition {
      condition = (
        alltrue([for subnet in data.aws_subnet.selected : subnet.vpc_id == var.vpc_id]) &&
        length(toset([for subnet in data.aws_subnet.selected : subnet.availability_zone])) >= 2
      )
      error_message = "Supply subnets in at least two AZs of the selected VPC."
    }
  }
  tags = var.tags
}

resource "aws_eks_node_group" "standard" {
  count           = var.enable_auto_mode ? 0 : 1
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = aws_eks_cluster.main.version
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"
  instance_types  = ["m5.large"]
  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }
  update_config {
    max_unavailable = 1
  }
  depends_on = [aws_iam_role_policy_attachment.node]
  tags       = var.tags
}

resource "aws_eks_access_entry" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.operator_role_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_eks_access_entry.operator.principal_arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}

variable "enable_auto_mode" {
  description = "Creation-time choice. Changing an existing cluster requires a separate migration plan."
  type        = bool
  default     = true
}
variable "cluster_name" {
  description = "Unique name for this new cluster."
  type        = string
}
variable "kubernetes_version" {
  description = "EKS-supported minor version; 1.36 is the reviewed example."
  type        = string
  default     = "1.36"
}
variable "region" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(distinct(var.private_subnet_ids)) >= 2
    error_message = "At least two distinct subnet IDs are required."
  }
}
variable "public_api_cidrs" {
  type = list(string)
  validation {
    condition = length(var.public_api_cidrs) > 0 && alltrue([
      for cidr in var.public_api_cidrs :
      can(cidrhost(cidr, 0)) && cidr != "0.0.0.0/0" && cidr != "::/0"
    ])
    error_message = "Supply reviewed client CIDRs instead of unrestricted public API access."
  }
}
variable "operator_role_arn" {
  description = "Existing approved IAM role allowed to administer this cluster."
  type        = string
}
variable "tags" {
  type = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-creation-example"
  }
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}
output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}
output "cluster_security_group_id" {
  value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}
output "cluster_arn" {
  value = aws_eks_cluster.main.arn
}
```

La entrada de acceso del operador concede al rol de IAM aprobado la administración del clúster; al creador no se le concede automáticamente acceso de administrador de Kubernetes. Ese rol de operador ya debe existir y la persona que usa kubectl debe poder asumirlo.

La alternativa de nodo convencional incluye permisos de CNI en el rol de nodo como referencia inicial de bootstrap. Es un límite de permisos compartido, no un diseño de identidad de carga de trabajo de producción reforzado. Revise un rol de CNI dedicado y restrinja el acceso de Pod a IMDS antes de usarlo en producción. Los permisos de AWS de la aplicación pertenecen a identidades específicas de la carga de trabajo; no adjunte permisos de complementos no relacionados a cada nodo.

### Ejecutar Terraform

Use un directorio de trabajo nuevo y un rol de aprovisionamiento autenticado. Reemplace los ID de ejemplo y el CIDR de documentación por los recursos de la cuenta prevista y el CIDR de cliente aprobado. El valor predeterminado selecciona Auto Mode:

```hcl
# terraform.tfvars — replace every example identifier before planning.
cluster_name       = "eks-docs-unique-name"
region             = "us-west-2"
vpc_id             = "vpc-0123456789abcdef0"
private_subnet_ids = ["subnet-0123456789abcdef0", "subnet-1123456789abcdef0"]
public_api_cidrs   = ["203.0.113.10/32"]
operator_role_arn  = "arn:aws:iam::111122223333:role/ApprovedOperator"
enable_auto_mode  = true
```

```bash
# Run in a new directory containing main.tf and the reviewed terraform.tfvars.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=reviewed.tfplan
# Apply only the plan you reviewed for the intended account/region/resources.
terraform apply reviewed.tfplan

: "${EKS_REGION:?Use the same region as terraform.tfvars}"
: "${EKS_OPERATOR_ROLE_ARN:?Use the same operator role as terraform.tfvars}"
aws eks update-kubeconfig --name "$(terraform output -raw cluster_name)" \
  --region "$EKS_REGION" --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

Revise el estado/backend, los cambios propuestos de IAM y red, y todos los recursos facturables antes de apply. `terraform validate` no puede verificar los permisos de la cuenta de AWS, las cuotas, el enrutamiento ni si los nodos seleccionados pueden ejecutar sus cargas de trabajo. Los límites de escalado de grupos de nodos no instalan un escalador automático basado en la demanda de Pods.

### Configuración tradicional de Terraform

Para un **clúster convencional nuevo**, use el mismo `main.tf` completo y establezca el siguiente valor en `terraform.tfvars` antes del primer plan:

```hcl
enable_auto_mode = false
```

Esto deshabilita las tres capacidades de Auto Mode, inicializa los complementos de red convencionales, selecciona permisos convencionales de nodos de EC2 y crea el grupo de nodos administrado AL2023. No instala EBS CSI, AWS LBC, Metrics Server ni un escalador automático de nodos; configure por separado los componentes que requiere su carga de trabajo. Cambiar este valor después de la implementación modifica la infraestructura e IAM y requiere una revisión de migración independiente.

Validación: Terraform **1.15.7** con el proveedor de AWS firmado **6.64.0** superó `terraform validate` local con cero errores/advertencias. **No se ejecutó ningún plan, apply ni llamada a API de AWS.** Ambos modos aún necesitan validación de implementación; el ejemplo no es evidencia de preparación para producción.

Referencias: [clúster de EKS del proveedor de AWS](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_cluster.html.markdown), [grupo de nodos administrado](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_node_group.html.markdown), [requisitos de roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

## Crear un clúster mediante AWS CDK

Use `aws-cdk-lib/aws-eks-v2` para este ejemplo de **stack nuevo**. Crea un `AWS::EKS::Cluster` nativo y una entrada de acceso; no se necesita ningún recurso personalizado Lambda para habilitar Auto Mode. No considere que reemplazar un construct implementado existente por este ejemplo sea una migración in situ.

El ejemplo usa la biblioteca de CDK **2.269.0**, CLI **2.1141.0** y EKS **1.36**. Importa subredes privadas existentes por atributos sin una búsqueda de VPC en tiempo de síntesis. Verifique la correspondencia de subred/AZ proporcionada, el DNS de la VPC, el enrutamiento, el acceso a servicios y las etiquetas de subred del balanceador de carga antes de la implementación. Una definición de VPC importada no valida esas condiciones.

### Clúster de EKS Auto Mode mediante TypeScript

Guarde como `lib/eks-auto-mode-stack.ts`. La persona que llama proporciona un rol de operador existente y aprobado; solo ese rol recibe acceso de administrador a este clúster. Los permisos de carga de trabajo permanecen separados.

```typescript
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks-v2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface EksAutoModeProps extends cdk.StackProps {
  readonly clusterName: string;
  readonly vpcId: string;
  readonly privateSubnetIds: string[];
  readonly availabilityZones: string[];
  readonly publicApiCidrs: string[];
  readonly operatorRoleArn: string;
}

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EksAutoModeProps) {
    super(scope, id, props);

    if (props.privateSubnetIds.length < 2 ||
        props.privateSubnetIds.length !== props.availabilityZones.length ||
        new Set(props.availabilityZones).size < 2 ||
        props.publicApiCidrs.length === 0) {
      throw new Error('Supply corresponding private subnets/AZs in at least two AZs and approved API CIDRs');
    }
    const vpc = ec2.Vpc.fromVpcAttributes(this, 'Vpc', {
      vpcId: props.vpcId,
      availabilityZones: props.availabilityZones,
      privateSubnetIds: props.privateSubnetIds,
    });

    const clusterRole = new iam.Role(this, 'ClusterRole', {
      assumedBy: new iam.ServicePrincipal('eks.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSClusterPolicy',
        'AmazonEKSComputePolicy',
        'AmazonEKSBlockStoragePolicyV2',
        'AmazonEKSLoadBalancingPolicy',
        'AmazonEKSNetworkingPolicy',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });
    clusterRole.assumeRolePolicy!.addStatements(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('eks.amazonaws.com')],
      actions: ['sts:TagSession'],
    }));

    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSWorkerNodeMinimalPolicy',
        'AmazonEC2ContainerRegistryPullOnly',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });

    const cluster = new eks.Cluster(this, 'Cluster', {
      clusterName: props.clusterName,
      version: eks.KubernetesVersion.V1_36,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE.onlyFrom(...props.publicApiCidrs),
      defaultCapacityType: eks.DefaultCapacityType.AUTOMODE,
      bootstrapSelfManagedAddons: false,
      bootstrapClusterCreatorAdminPermissions: false,
      // All required policies/trust are defined above. Avoid adding the older
      // BlockStoragePolicy that CDK 2.269.0 otherwise attaches automatically.
      role: clusterRole.withoutPolicyUpdates(),
      compute: {
        nodePools: ['system', 'general-purpose'],
        nodeRole: nodeRole.withoutPolicyUpdates(),
      },
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    cluster.node.addDependency(clusterRole, nodeRole);
    cluster.grantClusterAdmin('OperatorAccess', props.operatorRoleArn);

    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.clusterEndpoint });
  }
}
```

El rol de clúster incluye explícitamente `sts:TagSession` y las cinco políticas de Auto Mode, incluida `AmazonEKSBlockStoragePolicyV2`. `withoutPolicyUpdates()` evita que CDK 2.269.0 agregue la política de almacenamiento de bloques anterior; este ejemplo es responsable de proporcionar todos los permisos requeridos. Las dependencias retienen esos roles hasta que se completa la eliminación del clúster. El rol de nodo solo tiene las políticas de extracción de ECR y de worker mínimo de Auto Mode.

`bootstrapSelfManagedAddons: false` evita complementos de red autoadministrados superpuestos. Auto Mode administra conjuntamente cómputo, balanceo de carga y almacenamiento de bloques. La entrada de acceso del operador se crea separadamente del rol de ejecución del clúster.

### Punto de entrada de la aplicación CDK

Guarde como `bin/eks-auto-mode.ts`; mantenga el shebang en la primera línea. Los valores de entorno son obligatorios para evitar el uso accidental de valores de cuenta, VPC o rol de ejemplo.

```typescript
#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Set ${name} before synthesis/deployment`);
  return value;
}
function list(name: string): string[] {
  return required(name).split(',').map(value => value.trim()).filter(Boolean);
}
const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: required('CDK_DEFAULT_ACCOUNT'),
    region: required('CDK_DEFAULT_REGION'),
  },
  clusterName: required('EKS_CLUSTER_NAME'),
  vpcId: required('EKS_VPC_ID'),
  privateSubnetIds: list('EKS_PRIVATE_SUBNET_IDS'),
  availabilityZones: list('EKS_AVAILABILITY_ZONES'),
  publicApiCidrs: list('EKS_PUBLIC_API_CIDRS'),
  operatorRoleArn: required('EKS_OPERATOR_ROLE_ARN'),
});
```

### Implementación de CDK

Cree un proyecto nuevo, guarde los dos archivos anteriores después de la inicialización y proporcione los valores de la cuenta/región previstos. Use un rol de AWS autenticado y autorizado. Revise la configuración sintetizada de IAM/red y el diff antes de implementar. Las versiones de la biblioteca/CLI de CDK son paquetes independientes y no comparten el mismo número de versión.

```bash
mkdir eks-auto-mode
cd eks-auto-mode
npx --yes --package aws-cdk@2.1141.0 cdk init app --language typescript
npm install --save-exact aws-cdk-lib@2.269.0 constructs@10.5.0
npm install --save-dev --save-exact aws-cdk@2.1141.0 typescript@5.9.3

# Save the source files above, then set the required environment values.
: "${CDK_DEFAULT_ACCOUNT:?Set the intended AWS account ID}"
: "${CDK_DEFAULT_REGION:?Set the intended AWS region}"
: "${EKS_CLUSTER_NAME:?Use a unique name for this new cluster}"
: "${EKS_VPC_ID:?}"
: "${EKS_PRIVATE_SUBNET_IDS:?Comma-separated existing subnet IDs}"
: "${EKS_AVAILABILITY_ZONES:?Corresponding comma-separated AZs}"
: "${EKS_PUBLIC_API_CIDRS:?Approved client CIDRs, normally /32}"
: "${EKS_OPERATOR_ROLE_ARN:?Existing operator role you may assume}"
# Export the variables so the CDK application receives them.
export CDK_DEFAULT_ACCOUNT CDK_DEFAULT_REGION EKS_CLUSTER_NAME EKS_VPC_ID
export EKS_PRIVATE_SUBNET_IDS EKS_AVAILABILITY_ZONES EKS_PUBLIC_API_CIDRS EKS_OPERATOR_ROLE_ARN

npx tsc --noEmit
npx cdk synth
# Bootstrap creates AWS resources; review the account/region and execution policy.
npx cdk bootstrap "aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION"
npx cdk diff
npx cdk deploy

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$CDK_DEFAULT_REGION" \
  --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

La auditoría compiló ambos archivos TypeScript y sintetizó localmente el stack con identificadores ficticios: se verificaron las tres capacidades de Auto Mode, los CIDR de API con ámbito definido, los roles requeridos y una entrada de acceso de operador. No se generó ningún recurso personalizado/Lambda. Se rechazó la entrada requerida faltante. **No se ejecutaron bootstrap, búsqueda, implementación, creación de clúster ni llamadas a API de AWS**, por lo que las cuotas de cuenta, redes y disponibilidad de cargas de trabajo siguen siendo comprobaciones de implementación.

Referencias: [biblioteca de constructs EKS V2](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html), [rol de clúster de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html), [creación de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Configurar el acceso al clúster

Establezca el nombre del clúster, la región y la ruta dedicada de kubeconfig generada por el método seleccionado. Para los ejemplos de Terraform/CDK, establezca el rol de operador aprobado en `EKS_OPERATOR_ROLE_ARN`. Se puede omitir al usar acceso de creador mediante CLI. Escribir kubeconfig no concede permisos de Kubernetes.

```bash
: "${EKS_CLUSTER_NAME:?Use the selected cluster name}"
: "${EKS_REGION:?Use the selected region}"
: "${EKS_KUBECONFIG:?Set the dedicated kubeconfig path for this method}"
aws sts get-caller-identity
if [[ -n ${EKS_OPERATOR_ROLE_ARN:-} ]]; then
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig "$EKS_KUBECONFIG"
else
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --kubeconfig "$EKS_KUBECONFIG"
fi
eks_kubectl() {
  kubectl --kubeconfig "${EKS_KUBECONFIG:?}" "$@"
}
eks_kubectl config current-context
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query cluster.accessConfig.authenticationMode
```

### Configuración de RBAC

Use entradas de acceso para el nuevo acceso de IAM. Este ejemplo concede a un nuevo rol acceso de lectura en el espacio de nombres `dev` existente; no duplique la entrada de operador administrada por su herramienta de creación. El modo de autenticación debe ser `API` o `API_AND_CONFIG_MAP`. El método heredado `aws-auth` está en desuso; no sobrescriba todo su ConfigMap. Siga el procedimiento oficial de migración cuando sea necesario.

```bash
# A new reader identity, distinct from the operator already granted by IaC.
: "${EKS_READER_ROLE_ARN:?Existing approved IAM role without an access entry yet}"
if eks_kubectl get namespace dev &&
   aws eks create-access-entry --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --principal-arn "$EKS_READER_ROLE_ARN" \
  --type STANDARD --kubernetes-groups eks-docs-readers; then
EKS_ACCESS_DIR=$(mktemp -d /tmp/eks-access.XXXXXX)
: "${EKS_ACCESS_DIR:?}"
cat > "$EKS_ACCESS_DIR/rbac.yaml" << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: eks-docs-reader
  namespace: dev
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-docs-readers
  namespace: dev
subjects:
- kind: Group
  name: eks-docs-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: eks-docs-reader
  apiGroup: rbac.authorization.k8s.io
EOF
eks_kubectl create -f "$EKS_ACCESS_DIR/rbac.yaml"
fi
```

Este rol de lector no concede acceso a la API de Secret ni permisos de modificación. Autentíquese como ese rol y compruebe `kubectl auth can-i`; otras concesiones de políticas RBAC/EKS pueden añadir permisos. [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)

## Validación del clúster

Use `eks_kubectl` y el mismo kubeconfig dedicado de la sección de acceso. El acceso al plano de control por sí solo no demuestra el estado de los nodos ni de las cargas de trabajo.

### Validación básica

```bash
eks_kubectl cluster-info
eks_kubectl get nodes
eks_kubectl get pods -n kube-system
eks_kubectl get events --sort-by='.lastTimestamp'
```

### Validación específica de Auto Mode

AWS administra el controlador de aprovisionamiento de Auto Mode. No espere un Pod de controlador autoadministrado en un espacio de nombres `karpenter`. Inspeccione las condiciones y eventos de NodePool/NodeClass, además de los NodeClaims para cargas de trabajo que requieren capacidad.

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### Implementar aplicación de ejemplo

Use un espacio de nombres nuevo para comprobar acceso a imágenes, programación, preparación HTTP y un Service. Una configuración solo de Fargate primero necesita un perfil que coincida con este espacio de nombres.

```bash
EKS_SAMPLE_DIR=$(mktemp -d /tmp/eks-validate.XXXXXX)
: "${EKS_SAMPLE_DIR:?}"
unset EKS_SAMPLE_NAMESPACE EKS_SAMPLE_UID
EKS_SAMPLE_CANDIDATE=$(basename "$EKS_SAMPLE_DIR" | tr '[:upper:].' '[:lower:]-')
if EKS_SAMPLE_UID=$(eks_kubectl create namespace "$EKS_SAMPLE_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  EKS_SAMPLE_NAMESPACE=$EKS_SAMPLE_CANDIDATE
fi
: "${EKS_SAMPLE_NAMESPACE:?Namespace creation failed}"
: "${EKS_SAMPLE_UID:?Namespace UID missing}"
cat > "$EKS_SAMPLE_DIR/sample-app.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      automountServiceAccountToken: false
      containers:
      - name: app
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: http
EOF
eks_kubectl apply -f "$EKS_SAMPLE_DIR/sample-app.yaml"
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" rollout status deployment/sample-app --timeout=180s
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" get pods,services
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" port-forward --address 127.0.0.1 service/sample-app-service 8080:80
```

Mientras se ejecuta el reenvío de puertos, abra `http://127.0.0.1:8080` y, después, deténgalo con Ctrl-C. Esto comprueba el acceso ClusterIP, no un balanceador de carga externo. Para un NLB, seleccione `eks.amazonaws.com/nlb` de Auto Mode o `service.k8s.aws/nlb` de un AWS LBC instalado y autorizado, y revise por separado los requisitos de red/costo. Durante esta auditoría no se ejecutó ninguna implementación ni reenvío de puertos.

## Actualización del clúster

Primero revise las observaciones de actualización, las API eliminadas, la compatibilidad de webhook/complementos, las versiones de los nodos, las IP de reserva y el plan de recuperación. Lleve los nodos atrasados a la versión actual del plano de control y, luego, avance una versión secundaria compatible a la vez. Algunos componentes necesitan actualizaciones compatibles antes que el plano de control.

Auto Mode no actualiza las versiones secundarias del plano de control cada 21 días. Los operadores planifican actualizaciones secundarias y consideran las actualizaciones automáticas conforme a la política de soporte de versiones.

```bash
aws eks describe-cluster-versions --region "${EKS_REGION:?}" --output table
aws eks describe-cluster --name "${EKS_CLUSTER_NAME:?}" --region "$EKS_REGION" \
  --query 'cluster.{version:version,status:status}' --output table
eks_kubectl get nodes

# After readiness/compatibility review, choose the next supported minor.
: "${NEXT_MINOR_VERSION:?Select one supported minor step, for example 1.35 to 1.36}"
EKS_UPDATE_ID=$(aws eks update-cluster-version --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --kubernetes-version "$NEXT_MINOR_VERSION" \
  --query update.id --output text)
: "${EKS_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --update-id "$EKS_UPDATE_ID" --query 'update.{status:status,errors:errors}'

# Alternative interface; do not execute both:
# eksctl upgrade cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" --version "$NEXT_MINOR_VERSION" --approve
```

Proceda al plano de datos solo después de que la actualización informe `Successful`. AWS actualiza incrementalmente los nodos de Auto Mode; los grupos de nodos administrados convencionales necesitan una actualización independiente.

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

Planifique las actualizaciones de nodos autoadministrados/híbridos, el reemplazo de Pods de Fargate, las actualizaciones de complementos y las actualizaciones de kubectl según sus mecanismos respectivos. Compruebe los PDB y la capacidad de reserva en lugar de ocultar fallos con indicadores de fuerza. Las actualizaciones elegibles del plano de control pueden revertirse una versión secundaria en un plazo de siete días, sujetas a las restricciones de compatibilidad de nodos/complementos/API y de la política de soporte; la reversión no sustituye la recuperación de datos de aplicaciones.

[Procedimiento de actualización](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [Condiciones de reversión](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## Eliminación del clúster

Elimine mediante la herramienta/estado propietario original en la cuenta y región previstas. Primero elimine las cargas de trabajo y los Services Ingress/LoadBalancer mientras sus controladores aún se ejecutan y, después, compruebe que hayan finalizado. Decida cómo se conservarán o recuperarán PVC/PV, instantáneas y registros. No omita los tiempos de espera ni los finalizadores con opciones de fuerza.

### Limpiar el espacio de nombres de ejemplo

```bash
EKS_SAMPLE_CLEANUP_OK=true
if [[ -n ${EKS_SAMPLE_NAMESPACE:-} && -n ${EKS_SAMPLE_UID:-} ]]; then
  current_uid=$(eks_kubectl get namespace "$EKS_SAMPLE_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [[ "$current_uid" = "$EKS_SAMPLE_UID" ]]; then
    eks_kubectl delete namespace "$EKS_SAMPLE_NAMESPACE" --wait=true --timeout=180s || EKS_SAMPLE_CLEANUP_OK=false
  else
    EKS_SAMPLE_CLEANUP_OK=false
  fi
elif [[ -n ${EKS_SAMPLE_NAMESPACE:-} || -n ${EKS_SAMPLE_UID:-} ]]; then
  EKS_SAMPLE_CLEANUP_OK=false
fi
# Remove local files only after successful sample cleanup.
if [[ "$EKS_SAMPLE_CLEANUP_OK" = true ]]; then
if [[ -n ${EKS_SAMPLE_DIR:-} ]]; then
  rm -f -- "$EKS_SAMPLE_DIR/sample-app.yaml"
  rmdir -- "$EKS_SAMPLE_DIR"
fi
if [[ -n ${EKS_ACCESS_DIR:-} ]]; then
  rm -f -- "$EKS_ACCESS_DIR/rbac.yaml"
  rmdir -- "$EKS_ACCESS_DIR"
fi
else
  printf 'Sample cleanup could not be verified; stop before deleting the cluster\n' >&2
fi
```

Deténgase e investigue si falla la limpieza. Compare el ARN objetivo con el resultado de la creación o el estado de IaC propietario, no simplemente con una consulta actual no revisada.

```bash
: "${EKS_EXPECTED_CLUSTER_ARN:?Copy the ARN from the creation result or owning IaC state}"
: "${EKS_CLUSTER_NAME:?}"
: "${EKS_REGION:?}"
EKS_DELETE_TARGET_VERIFIED=false
if [[ ${EKS_SAMPLE_CLEANUP_OK:-false} != true ]]; then
  printf 'Complete the sample cleanup check above first\n' >&2
else
current_arn=$(aws eks describe-cluster --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --query cluster.arn --output text) || current_arn=""
if [[ "$current_arn" = "$EKS_EXPECTED_CLUSTER_ARN" ]]; then
  EKS_DELETE_TARGET_VERIFIED=true
  aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
else
  printf 'Target mismatch; stop and check the account, region and owning tool\n' >&2
fi
fi
```

### Eliminar mediante eksctl

Use esto para un clúster creado por eksctl.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### Eliminar mediante AWS CLI

Para un clúster creado directamente con la CLI, establezca los nombres de grupo de nodos/perfil de propiedad enumerados anteriormente y repita para cada recurso. Espere la eliminación y verifique que no quede ninguno antes de eliminar el clúster.

```bash
# For a cluster created directly with the AWS CLI, after workload/data cleanup.
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  if [[ -n ${EKS_NODEGROUP_NAME:-} ]]; then
    aws eks delete-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" &&
    aws eks wait nodegroup-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
  fi
  if [[ -n ${EKS_FARGATE_PROFILE_NAME:-} ]]; then
    aws eks delete-fargate-profile --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION" &&
    aws eks wait fargate-profile-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION"
  fi
  remaining_nodes=$(aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(nodegroups)' --output text) || remaining_nodes=unknown
  remaining_profiles=$(aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(fargateProfileNames)' --output text) || remaining_profiles=unknown
  if [[ "$remaining_nodes" = 0 && "$remaining_profiles" = 0 ]]; then
    aws eks delete-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" &&
      aws eks wait cluster-deleted --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  else
    printf 'Owned node groups/Fargate profiles remain, or their status could not be verified\n' >&2
  fi
fi
```

### Eliminar mediante Terraform

Use la configuración, backend y espacio de trabajo originales; aplique únicamente el plan de destrucción revisado para los recursos/cuenta previstos.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  terraform plan -destroy -out=reviewed-destroy.tfplan &&
    terraform apply reviewed-destroy.tfplan
fi
```

### Eliminar mediante CDK

Use la aplicación, las entradas, la cuenta y la región originales y verifique el stack objetivo.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

Después de completarse, compruebe el estado de EKS/CloudFormation y cualquier recurso restante de ELB, disco, NAT, registros e IAM. Conserve los roles/políticas de Auto Mode hasta que finalice la eliminación de la infraestructura administrada. No asuma que eliminar el clúster elimina una VPC, rol de IAM, registros o datos retenidos que son propiedad de otra parte. Durante la auditoría no se ejecutó ningún comando de eliminación.

## Conclusión

Existen varios métodos para crear un clúster de EKS, cada uno con sus propias ventajas y desventajas:

- **EKS Auto Mode**: Automatiza las operaciones de infraestructura; la preparación de las aplicaciones aún requiere validación
- **eksctl**: Creación de clúster simple y rápida
- **AWS Management Console**: Creación intuitiva mediante GUI
- **AWS CLI**: Adecuada para la automatización de scripts
- **Terraform**: Administrar infraestructura como código
- **AWS CDK**: Definir infraestructura mediante lenguajes de programación

Para producción, elija el modelo de cómputo y la herramienta de infraestructura que se ajusten a sus requisitos y valide el comportamiento de IAM, conectividad, capacidad, interrupción y recuperación. Una plantilla o creación de clúster exitosa no es evidencia de preparación para producción.

### Ámbito de validación de la auditoría

Ambas versiones completas del idioma se leyeron y comprobaron frente a la documentación y los esquemas oficiales. La validación cubrió shell/JSON/YAML, compilación/síntesis de CDK, validación de Terraform y rutas de fallo simuladas. No se realizó aprovisionamiento de AWS, actualizaciones, eliminación, pruebas de ejecución/carga de aplicaciones ni medición de costos.
