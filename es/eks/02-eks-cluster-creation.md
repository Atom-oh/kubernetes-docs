# Creación de clústeres de EKS

> **Última actualización**: October 16, 2026

Hay varias maneras de crear un clúster de Amazon EKS. En este capítulo, aprenderemos en detalle a crear un clúster de EKS con distintas herramientas y métodos.

Los métodos de creación de este capítulo son alternativas. Elija uno para un clúster nuevo y dedicado, y no administre los mismos recursos simultáneamente con varias herramientas. Reemplace los nombres, las cuentas, los roles, las VPC, las subredes y los CIDR de ejemplo por valores reales aprobados. Los ejemplos de shell usan Bash, a menos que se indique lo contrario; deténgase si falla algún requisito previo. Durante esta auditoría no se realizaron aprovisionamientos de AWS ni mediciones de cargas de trabajo.

**Versión actual:** EKS 1.37 estuvo disponible el 1 de octubre de 2026.

**Configuración de referencia de los ejemplos:** Los ejemplos siguientes conservan la configuración de referencia revisada de EKS 1.36. Si selecciona otra versión, consulte el [calendario actual de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) y la documentación de compatibilidad de los componentes.

## Tabla de contenido

1. [Requisitos previos](#prerequisites)
2. [Creación de un clúster con eksctl](#creating-a-cluster-using-eksctl)
3. [Creación de un clúster con la consola de administración de AWS](#creating-a-cluster-using-aws-management-console)
4. [Creación de un clúster con AWS CLI](#creating-a-cluster-using-aws-cli)
5. [Creación de un clúster con Terraform](#creating-a-cluster-using-terraform)
6. [Creación de un clúster con AWS CDK](#creating-a-cluster-using-aws-cdk)
7. [Configuración del acceso al clúster](#configuring-cluster-access)
8. [Validación del clúster](#cluster-validation)
9. [Actualización del clúster](#cluster-upgrade)
10. [Eliminación del clúster](#cluster-deletion)

## Requisitos previos

Antes de crear un clúster de EKS, se requieren los siguientes requisitos previos:

### 1. Cuenta de AWS

Se requiere una cuenta de AWS válida. Si no tiene una cuenta de AWS, puede registrarse en el [sitio web de AWS](https://aws.amazon.com/).

### 2. Permisos de IAM

Los permisos requeridos dependen de la herramienta y de los recursos que esta administre. Una política que otorgue `eks:*`, `ec2:*`, `iam:*` y `cloudformation:*` en todos los recursos no es una política de privilegio mínimo necesaria.

| Tarea | Alcance de los permisos que se deben revisar |
| --- | --- |
| Administración del clúster de EKS y de los grupos de nodos | Acciones de EKS requeridas y recursos de destino |
| Transferencia de roles de IAM existentes | `iam:PassRole` para ARN de roles aprobados y condiciones de servicio |
| Creación de roles/políticas/proveedores de OIDC de IAM | Recursos de IAM administrados por la herramienta y alcance de nombres/etiquetas |
| Creación de redes | Acciones de EC2 para la nueva VPC, las subredes y los grupos de seguridad |
| Uso de eksctl/CDK | Pilas de CloudFormation pertinentes, roles de ejecución y recursos de arranque |

La identidad de aprovisionamiento, el rol de servicio del clúster y el rol del nodo son distintos. También se aplican las SCP, los límites de permisos y las políticas de sesión. Revise los permisos de aprovisionamiento de su organización comparándolos con la plantilla/el plan sintetizados. Los requisitos de roles de Auto Mode difieren de los de los grupos de nodos convencionales.

Referencias: [Acciones y recursos de IAM de EKS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html), [Roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

### 3. Instalación de herramientas

#### AWS CLI

Elija el paquete adecuado para su sistema operativo/CPU y siga los pasos de verificación de firmas de la [guía oficial de instalación de AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Si ya tiene instalada la versión v1/v2, revise primero el procedimiento de actualización/migración correspondiente.

| Entorno | Paquete/método de instalación oficial |
| --- | --- |
| macOS | `AWSCLIV2.pkg` firmado |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` con verificación de firma PGP |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` con verificación de firma PGP |
| Windows | Instalador MSI para las versiones de Windows compatibles |

No use sin cambios el paquete de Linux x86_64 en ARM. Compruebe la CLI activa con `aws --version`. Si su organización usa IAM Identity Center, configure un perfil aprobado de la siguiente manera. De lo contrario, siga el procedimiento de federación correspondiente en vez de dar por sentado que se usan claves de acceso de larga duración.

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

Consulte [Autenticación de IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). Use la cuenta, el rol y la región aprobados para los comandos posteriores.

#### kubectl y eksctl (Linux/macOS)

Los ejemplos de EKS 1.36 de este capítulo usan kubectl **1.36.5** y eksctl **0.231.0** como configuración de referencia. Se recomienda usar la misma versión secundaria de kubectl que la del servidor; la diferencia admitida es de ±1 versión secundaria. No instale a ciegas la versión secundaria más reciente de `stable.txt` upstream para un clúster de EKS antiguo.

Este ejemplo de Bash selecciona AMD64/ARM64 y verifica las sumas de comprobación oficiales antes de la instalación. Necesita `curl`, `tar`, `awk` y `sha256sum` o `shasum`; la instalación en `/usr/local/bin` requiere permisos de administrador. Si falla una descarga o una suma de comprobación, se detiene la instalación.

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
  EKS_KUBECTL_VERSION=v1.36.5
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl" -o kubectl || exit 1
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl.sha256" -o kubectl.sha256 || exit 1
  printf '%s  kubectl\n' "$(tr -d '[:space:]' < kubectl.sha256)" > selected.sha256
  verify_sha selected.sha256 || exit 1

  EKSCTL_VERSION=0.231.0
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

Procedimientos oficiales: [kubectl para Linux](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/), [kubectl para macOS](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/), [instalación de eksctl](https://eksctl.io/installation/).

#### Windows

Siga en PowerShell el [procedimiento oficial de instalación de kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/). Para el ejemplo AMD64 de este capítulo, use [kubectl 1.36.5](https://dl.k8s.io/release/v1.36.5/bin/windows/amd64/kubectl.exe) y el archivo `.sha256` de la misma ruta. Seleccione el ZIP de Windows que corresponda a su CPU y `eksctl_checksums.txt` de la [versión 0.231.0 de eksctl](https://github.com/eksctl-io/eksctl/releases/tag/v0.231.0).

Compare `Get-FileHash -Algorithm SHA256` con el hash oficial y deténgase si no coinciden. Después de verificarlo, extraiga el ZIP, agregue el directorio del ejecutable a PATH y compruebe `kubectl version --client` y `eksctl version`. No ejecute sintaxis de PowerShell en Bash.

Prepare también `jq` para generar JSON en los ejemplos de AWS CLI. Durante esta auditoría no se descargaron ni instalaron clientes ni se inició sesión.

### 4. VPC y subredes

Un clúster regional de EKS requiere al menos dos subredes en distintas AZ de la misma VPC. Cada subred del clúster necesita al menos seis direcciones IP disponibles para EKS; AWS recomienda al menos dieciséis. Planifique direcciones adicionales para los nodos, los Pods, los balanceadores de carga y las actualizaciones. Habilite los nombres de host DNS y la resolución DNS de la VPC.

No todos los clústeres de EKS requieren acceso a Internet. Los nodos y las cargas de trabajo necesitan acceso a la API de Kubernetes, a las imágenes y a los servicios de AWS necesarios mediante rutas NAT/Internet o los endpoints de VPC necesarios y las imágenes reflejadas. Se puede acceder al endpoint privado de Kubernetes desde la VPC o desde redes conectadas que tengan DNS y enrutamiento adecuados.

#### Etiquetas de VPC para el clúster de EKS

La etiqueta de VPC `kubernetes.io/cluster/<cluster-name>` es un mecanismo heredado, no un requisito universal vigente para crear EKS. Para el balanceo de carga, siga las reglas de detección de subredes del controlador elegido:

- Subredes para balanceadores de carga públicos: `kubernetes.io/role/elb=1`
- Subredes para balanceadores de carga internos: `kubernetes.io/role/internal-elb=1`

Las etiquetas no configuran el enrutamiento, los grupos de seguridad ni la capacidad de IP disponible. Consulte [Requisitos de VPC/subredes](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) y [clústeres sin acceso a Internet](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html).

## Creación de un clúster con eksctl

eksctl es la forma más sencilla de crear y administrar clústeres de EKS. eksctl usa CloudFormation para crear clústeres de EKS y recursos relacionados.

Guarde el kubeconfig de eksctl en una ruta dedicada para este shell.

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### Creación básica del clúster

Cree el clúster básico a partir de un archivo de configuración revisado:

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

Lea y edite `cluster.yaml` a continuación antes de ejecutar este comando. Selecciona explícitamente EKS 1.36, AL2023, subredes de una VPC existente y capacidades de grupos de nodos. Reemplace los identificadores de ejemplo y el CIDR reservado para documentación por valores reales aprobados. Son opciones seleccionadas, no afirmaciones sobre los valores predeterminados de todas las versiones de eksctl.

### Creación de un clúster mediante un archivo de configuración

Para configuraciones más complejas, puede definir el clúster con un archivo YAML:

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

La configuración anterior muestra nodos EC2 y un perfil de Fargate opcional para aplicaciones. CoreDNS permanece en EC2; para moverlo a Fargate, hay que revisar la configuración de cómputo de CoreDNS además del perfil.

### Creación de grupos de nodos administrados

Para agregar un grupo de nodos administrados a un clúster existente, ejecute el siguiente comando:

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

### Creación de un clúster de EKS Auto Mode

EKS Auto Mode estuvo disponible de forma general en 2024 y automatiza la infraestructura del clúster de Kubernetes para reducir la carga operativa. AWS administra sus capacidades de cómputo, redes y almacenamiento.

#### Características principales de EKS Auto Mode

- **Administración automatizada de nodos**: Agrega o elimina nodos automáticamente según los requisitos de las cargas de trabajo
- **Seguridad mejorada**: AMI inmutable, modo de aplicación de SELinux y sistema de archivos raíz de solo lectura
- **Mantenimiento de nodos**: Los nodos se reemplazan cuando vencen o presentan desviaciones. Veintiún días no es un ciclo de actualización de versiones secundarias del plano de control
- **Componentes integrados**: Redes de Pod, DNS, almacenamiento y compatibilidad con GPU proporcionados de forma predeterminada
- **Optimización de costos**: Terminación automática de instancias sin uso y consolidación de cargas de trabajo

#### Creación básica de un clúster de Auto Mode

Revise primero el CIDR y la configuración de red en `auto-cluster.yaml`. No duplique las funciones de redes, DNS y almacenamiento en bloques de Auto Mode con complementos autoadministrados. Los clústeres mixtos necesitan una ubicación explícita y un alcance de componentes para cada tipo de cómputo.

```bash
eksctl create cluster --config-file auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Creación de un clúster de Auto Mode mediante un archivo de configuración

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
| Administración de nodos | Grupos de nodos administrados o nodos administrados por el cliente | Ciclo de vida de los nodos administrado por AWS |
| Escalado | Configurar Cluster Autoscaler, Karpenter autoadministrado u otra estrategia | Escalado automático de nodos administrado |
| Actualizaciones | Planificar actualizaciones del plano de control, los nodos y los complementos | AWS administra las actualizaciones de nodos/componentes; planificar las versiones secundarias del plano de control conforme a la política de soporte |
| Seguridad | Configurada por el usuario | Seguridad mejorada de forma predeterminada |
| Redes | Configuración del complemento CNI | Configuración automática de redes |
| Almacenamiento | Se requieren la instalación de CSI y permisos | Aprovisionador de EBS administrado `ebs.csi.eks.amazonaws.com` |
| Compatibilidad con GPU | Seleccionar AMI aceleradas compatibles y los complementos de dispositivo necesarios | Controladores/complementos administrados para las instancias compatibles |

#### Validación del clúster de Auto Mode

Una vez creado el clúster, puede comprobar su estado con los siguientes comandos:

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

#### Creación de grupos de nodos personalizados

En Auto Mode, puede crear grupos de nodos personalizados además de los grupos de nodos predeterminados:

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

> **Nota**: En Auto Mode no se pueden usar `EC2NodeClass`, `amiFamily` ni `userData` personalizado (`/etc/eks/bootstrap.sh`). AWS administra la AMI y el arranque de los nodos; las subredes, los grupos de seguridad y el almacenamiento efímero se definen mediante una `NodeClass` `eks.amazonaws.com/v1`.

El ejemplo de GPU conserva p3, que figura en la lista oficial de compatibilidad actual. Compruebe la capacidad de las AZ, las cuotas y los requisitos de memoria/modelo de GPU. Los Pods con GPU deben solicitar `nvidia.com/gpu` y tolerar la taint anterior. Se revisó este YAML; no se aprovisionó ni evaluó el rendimiento de ningún nodo con GPU.

#### Limitaciones de Auto Mode

- No se puede acceder directamente a los nodos mediante SSH o SSM
- El vencimiento predeterminado es de 336 horas (14 días), con una configuración máxima compatible de `expireAfter` de 21 días. Revise conjuntamente el drenaje, los bloqueos de PDB/NodePool y el período de gracia predeterminado de terminación de 24 horas
- No se pueden modificar los grupos de nodos ni las clases de nodos predeterminados
- Es posible que existan restricciones para ciertos tipos de instancia

#### Supervisión de Auto Mode

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

Un resultado vacío no demuestra que haya cero nodos ni que Auto Mode haya fallado. Compruebe primero la recopilación, las dimensiones y el intervalo de tiempo. Durante esta auditoría no se ejecutaron consultas ni mediciones de CloudWatch. Consulte el [catálogo oficial de métricas de Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html).

### Creación de perfiles de Fargate

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

### Actualización de un clúster

Revise la compatibilidad del plano de control, los nodos y los complementos, y siga [Actualización del clúster](#cluster-upgrade).

### Eliminación de un clúster

Revise las cargas de trabajo, los balanceadores de carga, la retención de datos y la herramienta propietaria, y siga [Eliminación del clúster](#cluster-deletion).

## Creación de un clúster con la consola de administración de AWS

Los pasos para crear un clúster de EKS con la consola de administración de AWS son los siguientes:

1. Inicie sesión en la [consola de administración de AWS](https://console.aws.amazon.com/).
2. Busque «EKS» o seleccione «Elastic Kubernetes Service» en la lista de servicios.
3. En la página «Clusters», haga clic en el botón «Create cluster».

### Creación de un clúster de EKS Auto Mode (configuración rápida)

EKS Auto Mode reduce la configuración de la infraestructura. La identidad de las cargas de trabajo, las redes, la capacidad, la disponibilidad y la recuperación siguen requiriendo una configuración y validación explícitas.

#### 1. Seleccione Quick Configuration

4. Asegúrese de que esté seleccionada la opción «Quick configuration».
5. Introduzca la siguiente información:
   - **Nombre del clúster**: Introduzca un nombre único para el clúster.
   - **Versión de Kubernetes**: Seleccione la versión de Kubernetes que se usará (se recomienda la versión más reciente).

#### 2. Configure los roles de IAM

6. Selección del **rol de IAM del clúster**:
   - Para su primer clúster de Auto Mode, use la opción «Create recommended role».
   - Si ya tiene un rol, puede reutilizarlo.
   - Nombre de rol recomendado: `AmazonEKSAutoClusterRole`

7. Selección del **rol de IAM del nodo**:
   - Para su primer clúster de Auto Mode, use la opción «Create recommended role».
   - Nombre de rol recomendado: `AmazonEKSAutoNodeRole`

#### 3. Configure las redes

8. **Seleccione una VPC**:
   - Crear una VPC nueva: Seleccione la opción «Create VPC» para crear una VPC nueva para EKS.
   - Usar una VPC existente: Seleccione una VPC de EKS creada anteriormente.

9. **Configuración de subredes** (opcional):
   - EKS Auto Mode selecciona automáticamente subredes privadas en la VPC.
   - Puede agregar o quitar subredes según sea necesario.

#### 4. Revise la configuración y cree el clúster

10. Seleccione **View quick configuration defaults** para revisar todos los valores de configuración.
11. Haga clic en **Create cluster**. (La creación del clúster tarda aproximadamente 15 minutos)

### Creación de un clúster con configuración personalizada

Si necesita un control más granular, puede usar una configuración personalizada.

### Configuración del clúster

4. En la página «Configure cluster», introduzca la siguiente información:
   - **Nombre del clúster**: Introduzca un nombre único para el clúster.
   - **Versión de Kubernetes**: Seleccione la versión de Kubernetes que se usará.
   - **Rol de servicio del clúster**: Cree un rol nuevo o seleccione uno existente.
   - **EKS Auto Mode**: Marque la casilla para habilitar Auto Mode.
   - **Etiquetas**: Agregue etiquetas si es necesario.
   - Haga clic en el botón «Next».

### Especifique las redes

5. En la página «Specify networking», introduzca la siguiente información:
   - **VPC**: Cree una VPC nueva o seleccione una existente.
   - **Subredes**: Seleccione las subredes que se usarán para el clúster. Al menos 2 subredes deben estar en distintas zonas de disponibilidad.
   - **Grupos de seguridad**: Seleccione los grupos de seguridad que se usarán para el clúster.
   - **Acceso al endpoint del clúster**: Configure el acceso al endpoint del servidor de la API del clúster.
     - **Público**: Se puede acceder al servidor de la API desde Internet.
     - **Privado**: El acceso desde la VPC o desde redes conectadas requiere DNS y enrutamiento adecuados.
     - **Público y privado**: Se puede acceder al servidor de la API tanto desde Internet como desde la VPC.
   - Haga clic en el botón «Next».

### Configure el registro

6. En la página «Configure logging», introduzca la siguiente información:
   - **Registro del plano de control**: Seleccione los tipos de registros que se habilitarán.
     - Registros del servidor de la API
     - Registros de auditoría
     - Registros del autenticador
     - Registros del administrador de controladores
     - Registros del planificador
   - Haga clic en el botón «Next».

### Seleccione los complementos

Los siguientes complementos corresponden al cómputo convencional. Auto Mode administra capacidades superpuestas de redes, DNS y almacenamiento en bloques; seleccione los componentes según los tipos de cómputo del clúster.

7. En la página «Select add-ons», introduzca la siguiente información:
   - **Amazon VPC CNI**: Complemento CNI para las redes de los Pods.
   - **CoreDNS**: Servicio DNS dentro del clúster.
   - **kube-proxy**: Proporciona un proxy de red y balanceo de carga.
   - **Complementos de almacenamiento/redes**: El cómputo convencional necesita los componentes instalados y permisos de IAM adecuados. Auto Mode proporciona capacidades administradas de EBS/redes/DNS; no instale componentes superpuestos en nodos de Auto Mode.
   - Haga clic en el botón «Next».

### Revise y cree el clúster

8. En la página «Review and create», revise la configuración y haga clic en el botón «Create».

### Incorporación de grupos de nodos para clústeres que no son de Auto Mode

Para el cómputo EC2 convencional, agregue grupos de nodos después de crear el clúster. Otras opciones compatibles, como los perfiles de Fargate, tienen su propia configuración; no es obligatorio tener un grupo de nodos administrado en todos los clústeres que no sean de Auto Mode.

### Agregar un grupo de nodos

1. En la página «Node group configuration», introduzca la siguiente información:
   - **Nombre del grupo de nodos**: Introduzca un nombre único para el grupo de nodos.
   - **Rol de IAM del nodo**: Cree un rol nuevo o seleccione uno existente.
   - Haga clic en el botón «Next».

2. En la página «Set compute and scaling configuration», introduzca la siguiente información:
   - **Tipo de AMI**: Seleccione el tipo de AMI que se usará para los nodos.
   - **Tipo de instancia**: Seleccione el tipo de instancia EC2 que se usará para los nodos.
   - **Tamaño del disco**: Especifique el tamaño del disco para los nodos.
   - **Cantidad de nodos**: Especifique la cantidad mínima, máxima y deseada de nodos.
   - Haga clic en el botón «Next».

3. En la página «Specify networking», introduzca la siguiente información:
   - **Subredes**: Seleccione las subredes que se usarán para el grupo de nodos.
   - **Configuración del acceso remoto**: Deje SSH deshabilitado, a menos que una ruta de administración aprobada lo requiera; no especifique una clave SSH sin revisar los grupos de seguridad de origen.
   - Haga clic en el botón «Next».

4. En la página «Review and create», revise la configuración y haga clic en el botón «Create».

## Creación de un clúster con AWS CLI

Estos ejemplos crean un **clúster nuevo**. Elija Auto Mode o EKS convencional; no ejecute ambos comandos de creación consecutivamente con el mismo nombre. Use Bash, `jq`, una versión actual de AWS CLI v2 y un rol de AWS autorizado. EKS 1.36 es la versión del ejemplo verificada; revise la compatibilidad regional y de componentes antes de seleccionar otra versión.

Las dos subredes deben estar en distintas AZ de la misma VPC. Prepare por separado el DNS, las IP disponibles, los grupos de seguridad y el acceso de los nodos a las imágenes/servicios. Los nombres reales de los campos de API son `endpointPrivateAccess` y `endpointPublicAccess`. El acceso de administrador del creador inicializa este ejemplo dedicado; administre los accesos posteriores mediante entradas de acceso.

### Prepare entradas comunes

Cree de antemano el rol del clúster para el modo seleccionado y verifique los permisos requeridos `iam:PassRole` y para crear roles vinculados a servicios. Revise la cuenta, la región, las subredes y el CIDR aprobado antes de ejecutar un comando de creación.

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

### Creación de un clúster de EKS Auto Mode

El rol del clúster necesita confianza para `sts:AssumeRole` y `sts:TagSession` con `eks.amazonaws.com`, y `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy` y `AmazonEKSNetworkingPolicy`, o permisos personalizados equivalentes.

El rol del nodo confía en `ec2.amazonaws.com` y usa `AmazonEKSWorkerNodeMinimalPolicy` más `AmazonEC2ContainerRegistryPullOnly`. Conceda permisos de AWS a las cargas de trabajo por separado mediante Pod Identity/IRSA. Habilite conjuntamente el cómputo, el balanceo de carga y el almacenamiento en bloques, y deshabilite el arranque de los complementos autoadministrados predeterminados.

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

#### Verifique la creación y el acceso

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

Auto Mode puede no tener nodos antes de que las cargas de trabajo los necesiten. Compruebe el estado de NodePool/NodeClass y la programación posterior de los Pods. Que el clúster esté `ACTIVE` no demuestra que las aplicaciones estén en buen estado ni garantiza una duración fija de creación.

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### Creación de un clúster convencional

Use esta alternativa solo si no seleccionó Auto Mode. El rol del clúster necesita permisos convencionales de clúster de EKS; el rol del nodo EC2 y los permisos de CNI/complementos son independientes. El arranque de los complementos de red predeterminados no instala EBS CSI ni AWS LBC.

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

#### Espere a que se cree el clúster y configure kubeconfig

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

#### Cree un grupo de nodos administrado

Prepare permisos de nodos de trabajo y de extracción de ECR para el rol de nodo EC2, y un rol de CNI independiente o permisos de CNI revisados en el rol del nodo. No reutilice sin cambios el rol mínimo de nodo de Auto Mode. Las subredes privadas también requieren NAT o los endpoints de VPC necesarios. Este ejemplo de AL2023 no habilita SSH de forma predeterminada.

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

`minSize`/`maxSize` por sí solos no habilitan el escalado de nodos en función de la demanda de los Pods. Inspeccione los errores de estado y de salud, y luego configure un escalador automático si es necesario. Si falla la creación, inspeccione los nombres/ARN registrados y los recursos relacionados. Durante la auditoría no se ejecutaron estos comandos de creación y espera.

Referencias: [API CreateCluster](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html), [API CreateNodegroup](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [IAM y creación de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Creación de un clúster con Terraform

El siguiente ejemplo completo admite **un clúster nuevo** y requiere elegir Auto Mode o un grupo de nodos administrado convencional antes de la primera aplicación. No agregue la alternativa como un segundo recurso de clúster ni cambie un clúster existente sin un plan de migración. El estado de Terraform y su archivo de bloqueo del proveedor corresponden a esta implementación específica.

### Configuración de Terraform para un clúster de EKS Auto Mode

Guárdelo como `main.tf`. El ejemplo fija el proveedor de AWS en **6.69.1** y usa EKS **1.36**. Proporcione explícitamente los ID de subredes privadas existentes; una etiqueta personalizada `Type=Private` no sustituye de manera fiable la verificación de las rutas y la conectividad. La precondición comprueba las relaciones entre VPC/AZ durante la planificación, pero no verifica el enrutamiento privado, los endpoints de servicio, el DNS, la capacidad de IP ni las etiquetas de subred para balanceadores de carga.

Auto Mode requiere habilitar conjuntamente el cómputo, el balanceo de carga y el almacenamiento en bloques, con `bootstrap_self_managed_addons = false`. El rol del clúster incluye `sts:TagSession` y las cinco políticas requeridas. Las dependencias de las asociaciones de IAM conservan los permisos mientras EKS elimina la infraestructura administrada.

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
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

La entrada de acceso del operador concede al rol de IAM aprobado privilegios de administración del clúster; el creador no recibe automáticamente acceso de administrador de Kubernetes. Ese rol de operador debe existir previamente y la persona que usa kubectl debe poder asumirlo.

La alternativa de nodos convencionales incluye permisos de CNI en el rol del nodo como configuración inicial de arranque. Este es un límite de permisos compartido, no un diseño reforzado de identidad de cargas de trabajo para producción. Antes de usarlo en producción, revise un rol de CNI dedicado y restrinja el acceso de los Pods a IMDS. Los permisos de AWS de las aplicaciones deben asignarse a identidades específicas de las cargas de trabajo; no adjunte permisos de complementos no relacionados a todos los nodos.

### Ejecución de Terraform

Use un directorio de trabajo nuevo y un rol de aprovisionamiento autenticado. Reemplace los ID de ejemplo y el CIDR reservado para documentación por recursos de la cuenta de destino y un CIDR de cliente aprobado. Auto Mode es la opción predeterminada:

```hcl
# terraform.tfvars: replace every example identifier before planning.
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

Revise el estado/backend, los cambios de IAM y redes propuestos y todos los recursos facturables antes de aplicar. `terraform validate` no puede verificar los permisos de la cuenta de AWS, las cuotas, el enrutamiento ni si los nodos seleccionados pueden ejecutar sus cargas de trabajo. Los límites de escalado del grupo de nodos no instalan un escalador automático basado en la demanda de los Pods.

### Configuración de Terraform tradicional

Para un **clúster convencional nuevo**, use el mismo `main.tf` completo y establezca el siguiente valor en `terraform.tfvars` antes del primer plan:

```hcl
enable_auto_mode = false
```

Esto deshabilita las tres capacidades de Auto Mode, inicia los complementos de redes convencionales, selecciona permisos convencionales para EC2 y crea el grupo de nodos administrado de AL2023. No instala EBS CSI, AWS LBC, Metrics Server ni un escalador automático de nodos; configure por separado los componentes que requiera la carga de trabajo. Cambiar este valor después de la implementación modifica la infraestructura y el IAM, por lo que se requiere una revisión de migración independiente.

Validación: Terraform **1.16.6** con el proveedor de AWS firmado **6.69.1** superó localmente `terraform validate` sin errores ni advertencias. **No se ejecutaron planes, aplicaciones ni llamadas a la API de AWS.** Ambos modos siguen requiriendo validación de implementación; el ejemplo no demuestra que esté listo para producción.

Referencias: [Clúster EKS del proveedor de AWS](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_cluster.html.markdown), [grupo de nodos administrado](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_node_group.html.markdown), [requisitos de roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

## Creación de un clúster con AWS CDK

Use `aws-cdk-lib/aws-eks-v2` para este ejemplo de **pila nueva**. Crea un `AWS::EKS::Cluster` nativo y una entrada de acceso; no se necesita ningún recurso personalizado de Lambda para habilitar Auto Mode. No considere que reemplazar un constructo existente ya implementado por este ejemplo sea una migración in situ.

El ejemplo usa la biblioteca CDK **2.273.0**, CLI **2.1145.0** y EKS **1.36**. Importa subredes privadas existentes mediante atributos, sin una búsqueda de VPC durante la síntesis. Verifique la correspondencia de las subredes/AZ proporcionadas, el DNS de la VPC, el enrutamiento, el acceso a servicios y las etiquetas de subred para balanceadores de carga antes de la implementación. Una definición de VPC importada no valida esas condiciones.

### Clúster de EKS Auto Mode con TypeScript

Guárdelo como `lib/eks-auto-mode-stack.ts`. Quien invoque el constructo proporciona un rol de operador existente y aprobado; solo ese rol recibe acceso de administrador a este clúster. Los permisos de las cargas de trabajo se mantienen separados.

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
      // BlockStoragePolicy that CDK 2.273.0 otherwise attaches automatically.
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

El rol del clúster incluye explícitamente `sts:TagSession` y las cinco políticas de Auto Mode, incluida `AmazonEKSBlockStoragePolicyV2`. `withoutPolicyUpdates()` impide que CDK 2.273.0 agregue la política de almacenamiento en bloques más antigua; este ejemplo se encarga de proporcionar todos los permisos requeridos. Las dependencias conservan esos roles hasta que se completa la eliminación del clúster. El rol del nodo solo tiene las políticas mínimas de trabajo de Auto Mode y de extracción de ECR.

`bootstrapSelfManagedAddons: false` evita la superposición de complementos de redes autoadministrados. Auto Mode administra conjuntamente el cómputo, el balanceo de carga y el almacenamiento en bloques. La entrada de acceso del operador se crea por separado del rol de ejecución del clúster.

### Punto de entrada de la aplicación CDK

Guárdelo como `bin/eks-auto-mode.ts`; mantenga el shebang en la primera línea. Los valores de entorno son obligatorios para evitar el uso accidental de valores de cuenta, VPC o rol de ejemplo.

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

### Implementación con CDK

Cree un proyecto nuevo, guarde los dos archivos anteriores después de inicializarlo y proporcione los valores de la cuenta/región de destino. Use un rol de AWS autenticado y autorizado. Revise la configuración sintetizada de IAM/redes y las diferencias antes de implementar. La biblioteca CDK y la CLI son paquetes separados y no comparten el mismo número de versión.

```bash
mkdir eks-auto-mode
cd eks-auto-mode
npx --yes --package aws-cdk@2.1145.0 cdk init app --language typescript
npm install --save-exact aws-cdk-lib@2.273.0 constructs@10.5.0
npm install --save-dev --save-exact aws-cdk@2.1145.0 typescript@5.9.3

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

La auditoría compiló ambos archivos TypeScript y sintetizó la pila localmente con identificadores ficticios: se verificaron las tres capacidades de Auto Mode, los CIDR de API delimitados, los roles requeridos y una entrada de acceso del operador. No se generó ninguna Lambda/recurso personalizado. Se rechazó la falta de entradas obligatorias. **No se ejecutaron el arranque, búsquedas, implementación, creación de clúster ni llamadas a la API de AWS**, por lo que las cuotas de cuenta, las redes y la disponibilidad de las cargas de trabajo siguen pendientes de validación durante la implementación.

Referencias: [Biblioteca de constructos EKS V2](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html), [rol del clúster de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html), [creación de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Configuración del acceso al clúster

Establezca el nombre del clúster, la región y la ruta dedicada de kubeconfig que generó el método seleccionado. Para los ejemplos de Terraform/CDK, establezca en `EKS_OPERATOR_ROLE_ARN` el rol de operador aprobado. Puede omitirse si se usa el acceso del creador mediante CLI. Escribir kubeconfig no otorga permisos de Kubernetes.

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

Use entradas de acceso para conceder acceso nuevo a IAM. Este ejemplo otorga acceso de lectura a un rol nuevo en el espacio de nombres `dev` existente; no duplique la entrada del operador que administra su herramienta de IaC. El modo de autenticación debe ser `API` o `API_AND_CONFIG_MAP`. El método heredado `aws-auth` está obsoleto; no sobrescriba todo su ConfigMap. Si es necesario, siga el procedimiento oficial de migración.

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

Este rol de lector no concede acceso a la API de Secret ni permisos de modificación. Autentíquese con ese rol y compruebe `kubectl auth can-i`; otros permisos de RBAC/EKS pueden agregar permisos. [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)

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

AWS administra el controlador de aprovisionamiento de Auto Mode. No espere encontrar un Pod de controlador autoadministrado en un espacio de nombres `karpenter`. Inspeccione las condiciones y los eventos de NodePool/NodeClass, además de los NodeClaims de las cargas de trabajo que requieran capacidad.

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### Implementación de una aplicación de ejemplo

Use un espacio de nombres nuevo para comprobar el acceso a imágenes, la programación, la disponibilidad HTTP y un Service. Una configuración exclusiva de Fargate primero necesita un perfil que coincida con este espacio de nombres.

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
        image: nginx:1.30.6-alpine
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

Mientras se ejecuta el reenvío de puertos, abra `http://127.0.0.1:8080` y luego deténgalo con Ctrl-C. Esto comprueba el acceso a ClusterIP, no a un balanceador de carga externo. Para un NLB, seleccione `eks.amazonaws.com/nlb` de Auto Mode o `service.k8s.aws/nlb` de un AWS LBC instalado y autorizado, y revise por separado los requisitos previos de redes/costos. Durante esta auditoría no se realizaron implementaciones ni reenvíos de puertos.

## Actualización del clúster

Primero revise los datos de actualización, las API eliminadas, la compatibilidad de los webhooks/complementos, las versiones de los nodos, las IP disponibles y el plan de recuperación. Actualice los nodos rezagados a la versión actual del plano de control y luego avance una versión secundaria admitida a la vez. Algunos componentes necesitan actualizaciones compatibles antes de la del plano de control.

Auto Mode no actualiza las versiones secundarias del plano de control cada 21 días. Los operadores planifican las actualizaciones de versiones secundarias y tienen en cuenta las actualizaciones automáticas conforme a la política de soporte de versiones.

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

Continúe con el plano de datos solo después de que la actualización informe `Successful`. AWS actualiza los nodos de Auto Mode de forma incremental; los grupos de nodos administrados convencionales necesitan una actualización independiente.

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

Planifique las actualizaciones de nodos autoadministrados/Hybrid, la sustitución de Pods de Fargate, las actualizaciones de complementos y las actualizaciones de kubectl según los mecanismos correspondientes. Compruebe los PDB y la capacidad disponible en lugar de ocultar fallos con indicadores de forzado. Las actualizaciones del plano de control que cumplan los requisitos pueden revertirse una versión secundaria dentro de siete días, sujetas a la compatibilidad de nodos/complementos/API y a las restricciones de la política de soporte; la reversión no sustituye la recuperación de los datos de las aplicaciones.

[Procedimiento de actualización](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [Condiciones de reversión](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## Eliminación del clúster

Elimine el clúster mediante la herramienta/el estado que lo creó, en la cuenta y región previstas. Primero elimine las cargas de trabajo y los Services de Ingress/LoadBalancer mientras sus controladores sigan ejecutándose y, después, verifique que la eliminación se haya completado. Decida cómo conservar o recuperar los PVC/PV, las instantáneas y los registros. No omita tiempos de espera ni finalizadores con opciones de forzado.

### Limpieza del espacio de nombres de ejemplo

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

Deténgase e investigue si falla la limpieza. Compare el ARN de destino con el resultado de creación o el estado de IaC propietario, no solo con una búsqueda actual no revisada.

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

### Eliminación con eksctl

Use esta opción para un clúster creado con eksctl.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### Eliminación con AWS CLI

Para un clúster creado directamente con la CLI, establezca los nombres de los grupos de nodos/perfiles propios que aparecen arriba y repita el proceso para cada recurso. Espere a que se complete la eliminación y compruebe que no quede ninguno antes de eliminar el clúster.

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

### Eliminación con Terraform

Use la configuración, el backend y el espacio de trabajo originales; aplique solo el plan de destrucción revisado para los recursos/la cuenta previstos.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  terraform plan -destroy -out=reviewed-destroy.tfplan &&
    terraform apply reviewed-destroy.tfplan
fi
```

### Eliminación con CDK

Use la aplicación, las entradas, la cuenta y la región originales, y verifique la pila de destino.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

Una vez completada la eliminación, verifique el estado de EKS/CloudFormation y los recursos restantes de ELB, discos, NAT, registros e IAM. Conserve los roles/políticas de Auto Mode hasta que se complete la eliminación de la infraestructura administrada. No suponga que la eliminación del clúster borra una VPC, un rol de IAM, los registros o los datos retenidos que pertenezcan a otros recursos. Durante la auditoría no se ejecutaron comandos de eliminación.

## Conclusión

Hay varios métodos para crear un clúster de EKS, cada uno con sus ventajas y desventajas:

- **EKS Auto Mode**: Automatiza las operaciones de infraestructura; aun así, se debe validar la preparación de las aplicaciones
- **eksctl**: Creación sencilla y rápida de clústeres
- **Consola de administración de AWS**: Creación intuitiva mediante una interfaz gráfica
- **AWS CLI**: Adecuada para la automatización con scripts
- **Terraform**: Administración de infraestructura como código
- **AWS CDK**: Definición de infraestructura mediante lenguajes de programación

Para producción, elija el modelo de cómputo y la herramienta de infraestructura que se ajusten a sus requisitos, y valide IAM, conectividad, capacidad, interrupciones y recuperación. Que una plantilla o la creación de un clúster se complete correctamente no demuestra que esté listo para producción.

### Alcance de la validación de la auditoría

Se leyeron ambas versiones lingüísticas completas y se cotejaron con la documentación y los esquemas oficiales. La validación abarcó shell/JSON/YAML, compilación/síntesis de CDK, `terraform validate` y rutas de error simuladas. No se realizaron aprovisionamientos de AWS, actualizaciones, eliminaciones, pruebas de carga/ejecución de aplicaciones ni mediciones de costos.
