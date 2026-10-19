# Creación de clústeres de EKS

> **Última actualización**: 16 de octubre de 2026

Hay varias formas de crear un clúster de Amazon EKS. En este capítulo, aprenderemos en detalle a crear un clúster de EKS con distintas herramientas y métodos.

Los métodos de creación de este capítulo son alternativas. Elija uno para un clúster nuevo y dedicado, y no administre los mismos recursos simultáneamente con varias herramientas. Sustituya los nombres, las cuentas, los roles, las VPC, las subredes y los CIDR de ejemplo por valores reales aprobados. Los ejemplos de shell usan Bash, salvo que se indique lo contrario; deténgase si falla algún requisito previo. Durante esta auditoría no se realizó ningún aprovisionamiento de AWS ni medición de cargas de trabajo.

**Versión actual:** EKS 1.37 está disponible desde el 1 de octubre de 2026.

**Línea base de los ejemplos:** Los ejemplos de abajo conservan la línea base revisada de EKS 1.36. Si selecciona otra versión, consulte el [calendario actual de versiones de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) y la documentación de compatibilidad de los componentes.

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

## Requisitos previos {#prerequisites}

Antes de crear un clúster de EKS, se necesitan los siguientes requisitos previos:

### 1. Cuenta de AWS

Se necesita una cuenta de AWS válida. Si no tiene una cuenta de AWS, puede registrarse en el [sitio web de AWS](https://aws.amazon.com/).

### 2. Permisos de IAM

Los permisos necesarios dependen de la herramienta y de los recursos que administre. Una política que conceda `eks:*`, `ec2:*`, `iam:*` y `cloudformation:*` en todos los recursos no es una política de privilegio mínimo necesaria.

| Tarea | Ámbito de permisos que se debe revisar |
| --- | --- |
| Administración de clústeres y grupos de nodos de EKS | Acciones de EKS necesarias y recursos de destino |
| Transferencia de roles de IAM existentes | `iam:PassRole` para los ARN de roles aprobados y las condiciones del servicio |
| Creación de roles/políticas/proveedores OIDC de IAM | Recursos de IAM administrados por la herramienta y ámbito de nombres/etiquetas |
| Creación de redes | Acciones de EC2 para la nueva VPC, las subredes y los grupos de seguridad |
| Uso de eksctl/CDK | Pilas de CloudFormation pertinentes, roles de ejecución y recursos de bootstrap |

La identidad de aprovisionamiento, el rol de servicio del clúster y el rol de los nodos son distintos. Siguen aplicándose las SCP, los límites de permisos y las políticas de sesión. Revise los permisos de aprovisionamiento de su organización comparándolos con la plantilla/el plan sintetizado. Los requisitos de roles de Auto Mode son distintos de los de los grupos de nodos convencionales.

Referencias: [Acciones y recursos de IAM de EKS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html), [Roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

### 3. Instalación de herramientas

#### AWS CLI

Elija el paquete correspondiente a su sistema operativo/CPU y siga el procedimiento de verificación de firmas de la [guía oficial de instalación de AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Si ya tiene instalada la versión 1 o 2, revise primero el procedimiento de actualización/migración.

| Entorno | Paquete/método de instalación oficial |
| --- | --- |
| macOS | `AWSCLIV2.pkg` firmado |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` con verificación de firma PGP |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` con verificación de firma PGP |
| Windows | Instalador MSI para las versiones de Windows compatibles |

No use sin modificar el paquete Linux x86_64 en ARM. Compruebe la CLI activa con `aws --version`. Si su organización usa IAM Identity Center, configure un perfil aprobado de la siguiente manera. De lo contrario, siga el procedimiento de federación correspondiente en lugar de asumir credenciales de acceso de larga duración.

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

Consulte [Autenticación con IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). Siga usando la cuenta, el rol y la región aprobados en los comandos posteriores.

#### kubectl y eksctl (Linux/macOS)

Los ejemplos de EKS 1.36 de este capítulo usan kubectl **1.36.5** y eksctl **0.231.0** como línea base. Se recomienda usar la misma versión menor de kubectl que la del servidor; la diferencia admitida es de ±1 versión menor. No instale a ciegas la versión menor más reciente de `stable.txt` de upstream para un clúster de EKS más antiguo.

Este ejemplo de Bash selecciona AMD64/ARM64 y verifica las sumas de comprobación oficiales antes de la instalación. Necesita `curl`, `tar`, `awk` y `sha256sum` o `shasum`; la instalación en `/usr/local/bin` requiere permisos de administrador. Si falla la descarga o la suma de comprobación, se detiene la instalación.

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

Procedimientos oficiales: [kubectl para Linux](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/), [kubectl para macOS](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/), [Instalación de eksctl](https://eksctl.io/installation/).

#### Windows

Siga en PowerShell el [procedimiento oficial de instalación de kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/). Para el ejemplo AMD64 de este capítulo, use [kubectl 1.36.5](https://dl.k8s.io/release/v1.36.5/bin/windows/amd64/kubectl.exe) y el archivo `.sha256` de la misma ruta. Seleccione el ZIP de Windows que corresponda a su CPU y `eksctl_checksums.txt` de la [versión 0.231.0 de eksctl](https://github.com/eksctl-io/eksctl/releases/tag/v0.231.0).

Compare `Get-FileHash -Algorithm SHA256` con el hash oficial y deténgase si no coinciden. Tras la verificación, extraiga el ZIP, añada el directorio del ejecutable a PATH y compruebe `kubectl version --client` y `eksctl version`. No ejecute sintaxis de PowerShell en Bash.

Prepare también `jq` para generar JSON en los ejemplos de AWS CLI. Durante esta auditoría no se descargaron ni instalaron clientes, ni se inició sesión.

### 4. VPC y subredes

Un clúster regional de EKS necesita al menos dos subredes en distintas AZ de la misma VPC. Cada subred del clúster necesita al menos seis direcciones IP disponibles para EKS; AWS recomienda al menos dieciséis. Planifique direcciones adicionales para los nodos, los Pods, los balanceadores de carga y las actualizaciones. Habilite los nombres de host DNS y la resolución DNS de la VPC.

No todos los clústeres de EKS necesitan acceso a Internet. Los nodos y las cargas de trabajo necesitan acceso a la API de Kubernetes, a las imágenes y a los servicios de AWS necesarios mediante rutas NAT/Internet o los puntos de conexión de VPC necesarios y las imágenes reflejadas. Se puede acceder al punto de conexión privado de Kubernetes desde la VPC o desde redes conectadas con el DNS y el enrutamiento adecuados.

#### Etiquetas de VPC para el clúster de EKS

La etiqueta de VPC `kubernetes.io/cluster/<cluster-name>` es un mecanismo heredado, no un requisito universal vigente para crear clústeres de EKS. Para el balanceo de carga, siga las reglas de detección de subredes del controlador elegido:

- Subredes para balanceadores de carga públicos: `kubernetes.io/role/elb=1`
- Subredes para balanceadores de carga internos: `kubernetes.io/role/internal-elb=1`

Las etiquetas no configuran el enrutamiento, los grupos de seguridad ni la capacidad de IP libres. Consulte [Requisitos de VPC/subredes](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) y [Clústeres sin acceso a Internet](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html).

## Creación de un clúster con eksctl {#creating-a-cluster-using-eksctl}

eksctl es la forma más sencilla de crear y administrar clústeres de EKS. eksctl usa CloudFormation para crear clústeres de EKS y recursos relacionados.

Almacene el kubeconfig de eksctl en una ruta dedicada para este shell.

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### Creación básica de un clúster

Cree el clúster básico a partir de un archivo de configuración revisado:

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

Lea y edite el archivo `cluster.yaml` de abajo antes de ejecutar este comando. Selecciona explícitamente EKS 1.36, AL2023, subredes de una VPC existente y capacidades de los grupos de nodos. Sustituya los identificadores de ejemplo y el CIDR de documentación por valores reales aprobados. Estos son valores seleccionados, no afirmaciones sobre los valores predeterminados de todas las versiones de eksctl.

### Creación de un clúster con un archivo de configuración

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

Para crear un clúster con este archivo de configuración, ejecute el siguiente comando:

```bash
eksctl create cluster -f cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

La configuración de arriba muestra nodos EC2 y un perfil Fargate opcional para aplicaciones. CoreDNS permanece en EC2; para trasladarlo a Fargate, es necesario revisar tanto la configuración de cómputo de CoreDNS como el perfil.

### Creación de grupos de nodos administrados

Para añadir un grupo de nodos administrados a un clúster existente, ejecute el siguiente comando:

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

EKS Auto Mode pasó a estar disponible de forma general en 2024 y automatiza la infraestructura de los clústeres de Kubernetes para reducir la carga operativa. AWS administra sus capacidades de cómputo, redes y almacenamiento.

#### Características principales de EKS Auto Mode

- **Administración automatizada de nodos**: Añade/elimina nodos automáticamente según los requisitos de las cargas de trabajo
- **Seguridad mejorada**: AMI inmutable, modo de aplicación de SELinux, sistema de archivos raíz de solo lectura
- **Mantenimiento de nodos**: Los nodos se sustituyen por vencimiento y desviación de configuración. Veintiún días no es un ciclo de actualización de versión menor del plano de control
- **Componentes integrados**: Redes de Pod, DNS, almacenamiento y compatibilidad con GPU se proporcionan de forma predeterminada
- **Optimización de costos**: Terminación automática de instancias no utilizadas y consolidación de cargas de trabajo

#### Creación básica de un clúster de Auto Mode

Revise primero el CIDR y la red de `auto-cluster.yaml` de abajo. No duplique las redes, el DNS ni el almacenamiento en bloques de Auto Mode con complementos autoadministrados. Los clústeres mixtos necesitan una ubicación explícita y un ámbito de componentes definido para cada tipo de cómputo.

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

Cree el clúster:
```bash
eksctl create cluster -f auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Comparación entre Auto Mode y el enfoque tradicional

| Característica | EKS tradicional | EKS Auto Mode |
|---------|-----------------|---------------|
| Administración de nodos | Grupos de nodos administrados o nodos administrados por el cliente | Ciclo de vida de nodos administrado por AWS |
| Escalado | Configurar Cluster Autoscaler, Karpenter autoadministrado u otra estrategia | Escalado automático de nodos administrado |
| Actualizaciones | Planificar las actualizaciones del plano de control, los nodos y los complementos | AWS administra las actualizaciones de nodos/componentes; planificar las versiones menores del plano de control según la política de soporte |
| Seguridad | Configurada por el usuario | Seguridad mejorada de forma predeterminada |
| Redes | Configuración del complemento CNI | Configuración automática de redes |
| Almacenamiento | Se requiere instalar CSI y configurar permisos | Aprovisionador de EBS administrado `ebs.csi.eks.amazonaws.com` |
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

En Auto Mode, además de los grupos de nodos predeterminados, puede crear grupos de nodos personalizados:

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

> **Nota**: En Auto Mode no se pueden usar `EC2NodeClass`, `amiFamily` ni `userData` personalizado (`/etc/eks/bootstrap.sh`). AWS administra la AMI de los nodos y el bootstrap; las subredes, los grupos de seguridad y el almacenamiento efímero se definen en su lugar mediante una `NodeClass` `eks.amazonaws.com/v1`.

El ejemplo de GPU conserva p3, que aparece en la lista oficial de tipos compatibles vigente. Compruebe la capacidad de las AZ, las cuotas y los requisitos de memoria/modelo de GPU. Los Pods con GPU deben solicitar `nvidia.com/gpu` y tolerar la taint anterior. Se revisó este YAML; no se aprovisionó ni se comparó el rendimiento de ningún nodo GPU.

#### Limitaciones de Auto Mode

- No hay acceso directo a los nodos mediante SSH o SSM
- El vencimiento predeterminado es de 336 horas (14 días), con un valor máximo compatible de `expireAfter` de 21 días. Revise conjuntamente el vaciado, los bloqueos de PDB/NodePool y el período de gracia de terminación predeterminado de 24 horas
- No se pueden modificar los grupos de nodos ni las clases de nodos predeterminados
- Puede haber restricciones en determinados tipos de instancia

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

Revise la compatibilidad del plano de control, los nodos y los complementos y, después, siga el procedimiento de [Actualización del clúster](#cluster-upgrade).

### Eliminación de un clúster

Revise las cargas de trabajo, los balanceadores de carga, la retención de datos y la herramienta propietaria y, después, siga el procedimiento de [Eliminación del clúster](#cluster-deletion).

## Creación de un clúster con la consola de administración de AWS {#creating-a-cluster-using-aws-management-console}

Los pasos para crear un clúster de EKS con la consola de administración de AWS son los siguientes:

1. Inicie sesión en la [consola de administración de AWS](https://console.aws.amazon.com/).
2. Busque «EKS» o seleccione «Elastic Kubernetes Service» en la lista de servicios.
3. En la página «Clusters», haga clic en el botón «Create cluster».

### Creación de un clúster de EKS Auto Mode (configuración rápida)

EKS Auto Mode reduce la configuración de la infraestructura. La identidad de las cargas de trabajo, las redes, la capacidad, la disponibilidad y la recuperación siguen necesitando configuración y validación explícitas.

#### 1. Seleccione la configuración rápida

4. Asegúrese de que esté seleccionada la opción «Quick configuration».
5. Introduzca la siguiente información:
   - **Nombre del clúster**: Introduzca un nombre único para el clúster.
   - **Versión de Kubernetes**: Seleccione la versión de Kubernetes que desea usar (se recomienda la versión más reciente).

#### 2. Configure los roles de IAM

6. Selección del **rol de IAM del clúster**:
   - Para el primer clúster de Auto Mode, use la opción «Create recommended role».
   - Si tiene un rol existente, puede reutilizarlo.
   - Nombre de rol recomendado: `AmazonEKSAutoClusterRole`

7. Selección del **rol de IAM de los nodos**:
   - Para el primer clúster de Auto Mode, use la opción «Create recommended role».
   - Nombre de rol recomendado: `AmazonEKSAutoNodeRole`

#### 3. Configure las redes

8. **Seleccione la VPC**:
   - Crear una VPC nueva: Seleccione la opción «Create VPC» para crear una VPC nueva para EKS.
   - Usar una VPC existente: Seleccione una VPC de EKS creada previamente.

9. **Configuración de subredes** (opcional):
   - EKS Auto Mode selecciona automáticamente subredes privadas de la VPC.
   - Puede añadir o quitar subredes según sea necesario.

#### 4. Revise la configuración y cree el clúster

10. Seleccione **View quick configuration defaults** para revisar todos los valores de configuración.
11. Haga clic en **Create cluster**. (La creación del clúster tarda aproximadamente 15 minutos).

### Creación de un clúster con configuración personalizada

Si necesita un control más detallado, puede usar una configuración personalizada.

### Configuración del clúster

4. En la página «Configure cluster», introduzca la siguiente información:
   - **Nombre del clúster**: Introduzca un nombre único para el clúster.
   - **Versión de Kubernetes**: Seleccione la versión de Kubernetes que desea usar.
   - **Rol de servicio del clúster**: Cree un rol nuevo o seleccione uno existente.
   - **EKS Auto Mode**: Marque la casilla para habilitar Auto Mode.
   - **Etiquetas**: Añada etiquetas si es necesario.
   - Haga clic en el botón «Next».

### Especifique las redes

5. En la página «Specify networking», introduzca la siguiente información:
   - **VPC**: Cree una VPC nueva o seleccione una existente.
   - **Subredes**: Seleccione las subredes que usará el clúster. Al menos dos subredes deben estar en distintas zonas de disponibilidad.
   - **Grupos de seguridad**: Seleccione los grupos de seguridad que usará el clúster.
   - **Acceso al punto de conexión del clúster**: Configure el acceso al punto de conexión del servidor de API del clúster.
     - **Público**: Se puede acceder al servidor de API desde Internet.
     - **Privado**: El acceso desde la VPC o desde redes conectadas requiere DNS y enrutamiento adecuados.
     - **Público y privado**: Se puede acceder al servidor de API tanto desde Internet como desde la VPC.
   - Haga clic en el botón «Next».

### Configure el registro

6. En la página «Configure logging», introduzca la siguiente información:
   - **Registro del plano de control**: Seleccione los tipos de registros que desea habilitar.
     - Registros del servidor de API
     - Registros de auditoría
     - Registros del autenticador
     - Registros del administrador de controladores
     - Registros del planificador
   - Haga clic en el botón «Next».

### Seleccione los complementos

Los siguientes complementos corresponden al cómputo convencional. Auto Mode administra capacidades coincidentes de redes, DNS y almacenamiento en bloques; seleccione los componentes según los tipos de cómputo del clúster.

7. En la página «Select add-ons», introduzca la siguiente información:
   - **Amazon VPC CNI**: Complemento CNI para las redes de los Pod.
   - **CoreDNS**: Servicio DNS dentro del clúster.
   - **kube-proxy**: Proporciona un proxy de red y balanceo de carga.
   - **Complementos de almacenamiento/redes**: El cómputo convencional necesita los componentes instalados y los permisos de IAM adecuados. Auto Mode proporciona capacidades administradas de EBS/redes/DNS; no instale componentes coincidentes en los nodos de Auto Mode.
   - Haga clic en el botón «Next».

### Revise y cree el clúster

8. En la página «Review and create», revise la configuración y haga clic en el botón «Create».

### Incorporación de grupos de nodos a clústeres que no usan Auto Mode

Para el cómputo EC2 convencional, añada grupos de nodos después de crear el clúster. Otras opciones compatibles, como los perfiles de Fargate, tienen su propia configuración; no es obligatorio tener un grupo de nodos administrado en todos los clústeres que no usan Auto Mode.

### Añada un grupo de nodos

1. En la página «Node group configuration», introduzca la siguiente información:
   - **Nombre del grupo de nodos**: Introduzca un nombre único para el grupo de nodos.
   - **Rol de IAM de los nodos**: Cree un rol nuevo o seleccione uno existente.
   - Haga clic en el botón «Next».

2. En la página «Set compute and scaling configuration», introduzca la siguiente información:
   - **Tipo de AMI**: Seleccione el tipo de AMI que se usará para los nodos.
   - **Tipo de instancia**: Seleccione el tipo de instancia EC2 que se usará para los nodos.
   - **Tamaño del disco**: Especifique el tamaño del disco de los nodos.
   - **Cantidad de nodos**: Especifique la cantidad mínima, máxima y deseada de nodos.
   - Haga clic en el botón «Next».

3. En la página «Specify networking», introduzca la siguiente información:
   - **Subredes**: Seleccione las subredes que se usarán para el grupo de nodos.
   - **Configuración de acceso remoto**: Deje SSH deshabilitado, salvo que una ruta de administración aprobada lo requiera; no especifique una clave SSH sin revisar los grupos de seguridad de origen.
   - Haga clic en el botón «Next».

4. En la página «Review and create», revise la configuración y haga clic en el botón «Create».

## Creación de un clúster con AWS CLI {#creating-a-cluster-using-aws-cli}

Estos ejemplos crean un **clúster nuevo**. Elija Auto Mode o EKS convencional; no ejecute consecutivamente ambos comandos de creación con el mismo nombre. Use Bash, `jq`, una versión actual de AWS CLI v2 y un rol de AWS autorizado. EKS 1.36 es la versión de ejemplo verificada; revise la compatibilidad y la disponibilidad en la región antes de seleccionar otra versión.

Las dos subredes deben estar en distintas AZ de la misma VPC. Prepare por separado el DNS, las IP libres, los grupos de seguridad y el acceso de los nodos a imágenes/servicios. Los nombres reales de los campos de la API son `endpointPrivateAccess` y `endpointPublicAccess`. El acceso de administrador del creador inicializa este ejemplo dedicado; administre el acceso posterior mediante entradas de acceso.

### Prepare entradas comunes

Cree de antemano el rol del clúster para el modo seleccionado y verifique que tenga los permisos necesarios para `iam:PassRole` y para crear roles vinculados a servicios. Revise la cuenta, la región, las subredes y el CIDR aprobado antes de ejecutar un comando de creación.

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

El rol del clúster necesita confianza para `sts:AssumeRole` y `sts:TagSession` de `eks.amazonaws.com`, además de `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy` y `AmazonEKSNetworkingPolicy`, o permisos personalizados equivalentes.

El rol de los nodos confía en `ec2.amazonaws.com` y usa `AmazonEKSWorkerNodeMinimalPolicy` y `AmazonEC2ContainerRegistryPullOnly`. Conceda por separado permisos de AWS a las cargas de trabajo mediante Pod Identity/IRSA. Habilite conjuntamente el cómputo, el balanceo de carga y el almacenamiento en bloques, y deshabilite el bootstrap de los complementos autoadministrados predeterminados.

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

Es posible que Auto Mode no tenga nodos antes de que las cargas de trabajo los necesiten. Compruebe el estado de NodePool/NodeClass y la programación posterior de los Pod. Que el clúster esté `ACTIVE` no demuestra el estado de las aplicaciones ni garantiza una duración fija de creación.

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### Creación de un clúster convencional

Use esta alternativa solo si no seleccionó Auto Mode. El rol del clúster necesita permisos convencionales de clúster de EKS; el rol de nodo EC2 y los permisos de CNI/complementos son independientes. El bootstrap de los complementos de redes predeterminados no instala EBS CSI ni AWS LBC.

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

#### Espere a que termine la creación y configure kubeconfig

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

Prepare los permisos de los nodos de trabajo y de extracción de ECR para el rol de nodo EC2, así como un rol CNI independiente o permisos CNI revisados en el rol de nodo. No reutilice sin cambios el rol mínimo de nodo de Auto Mode. Las subredes privadas también necesitan NAT o los puntos de conexión de VPC necesarios. Este ejemplo de AL2023 no habilita SSH de forma predeterminada.

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

`minSize`/`maxSize` por sí solos no habilitan el escalado de nodos según la demanda de los Pod. Revise los errores de estado y de salud y, después, configure un escalador automático si es necesario. Si falla la creación, inspeccione los nombres/ARN registrados y los recursos relacionados. Durante la auditoría no se ejecutaron estos comandos de creación ni de espera.

Referencias: [API CreateCluster](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html), [API CreateNodegroup](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [IAM y creación de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Creación de un clúster con Terraform {#creating-a-cluster-using-terraform}

El siguiente ejemplo completo admite **un clúster nuevo**, con Auto Mode o un grupo de nodos administrado convencional seleccionado antes del primer apply. No añada la alternativa como un segundo recurso de clúster ni cambie un clúster existente sin un plan de migración. El estado de Terraform y su archivo de bloqueo del proveedor pertenecen a este despliegue específico.

### Configuración de Terraform para un clúster de EKS Auto Mode

Guárdela como `main.tf`. El ejemplo fija el proveedor de AWS en **6.69.1** y usa EKS **1.36**. Proporcione explícitamente los ID de las subredes privadas existentes; una etiqueta personalizada `Type=Private` no sustituye de forma fiable la verificación de las rutas y la conectividad. La condición previa comprueba las relaciones entre VPC/AZ durante la planificación, pero no verifica el enrutamiento privado, los puntos de conexión de servicios, el DNS, la capacidad de IP ni las etiquetas de subredes para balanceadores de carga.

Auto Mode necesita que el cómputo, el balanceo de carga y el almacenamiento en bloques estén habilitados conjuntamente, con `bootstrap_self_managed_addons = false`. El rol del clúster incluye `sts:TagSession` y las cinco políticas necesarias. Las dependencias de asociación de políticas de IAM conservan los permisos mientras EKS elimina la infraestructura administrada.

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

La entrada de acceso del operador concede al rol de IAM aprobado permisos de administración del clúster; al creador no se le concede automáticamente acceso de administrador de Kubernetes. Ese rol de operador debe existir de antemano y la persona que usa kubectl debe poder asumirlo.

La alternativa de nodos convencionales incluye permisos CNI en el rol de nodo como línea base de bootstrap inicial. Este límite de permisos compartido no es un diseño reforzado de identidad de cargas de trabajo para producción. Antes de usarlo en producción, revise la posibilidad de usar un rol CNI dedicado y restrinja el acceso de los Pod a IMDS. Los permisos de AWS de las aplicaciones deben asignarse a identidades específicas de las cargas de trabajo; no adjunte permisos de complementos no relacionados a todos los nodos.

### Ejecución de Terraform

Use un directorio de trabajo nuevo y un rol de aprovisionamiento autenticado. Sustituya los ID de ejemplo y el CIDR de documentación por los recursos de la cuenta prevista y el CIDR de cliente aprobado. La configuración predeterminada elige Auto Mode:

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

Revise el estado/backend, los cambios propuestos de IAM y redes y todos los recursos facturables antes del apply. `terraform validate` no puede verificar los permisos de la cuenta de AWS, las cuotas, el enrutamiento ni si los nodos seleccionados pueden ejecutar sus cargas de trabajo. Los límites de escalado de los grupos de nodos no instalan un escalador automático basado en la demanda de los Pod.

### Configuración tradicional de Terraform

Para un **clúster convencional nuevo**, use el mismo `main.tf` completo y establezca el siguiente valor en `terraform.tfvars` antes del primer plan:

```hcl
enable_auto_mode = false
```

Esto deshabilita las tres capacidades de Auto Mode, inicializa los complementos de redes convencionales, selecciona permisos convencionales para EC2 y crea el grupo de nodos administrado de AL2023. No instala EBS CSI, AWS LBC, Metrics Server ni un escalador automático de nodos; configure por separado los componentes que necesite su carga de trabajo. Cambiar este valor después del despliegue modifica la infraestructura y IAM y requiere una revisión de migración independiente.

Validación: Terraform **1.16.6** con el proveedor de AWS firmado **6.69.1** superó `terraform validate` local sin errores ni advertencias. **No se ejecutó ningún plan, apply ni llamada a la API de AWS.** Ambos modos siguen necesitando validación del despliegue; el ejemplo no demuestra que esté listo para producción.

Referencias: [Clúster de EKS del proveedor de AWS](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_cluster.html.markdown), [grupo de nodos administrado](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_node_group.html.markdown), [Requisitos de roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

## Creación de un clúster con AWS CDK {#creating-a-cluster-using-aws-cdk}

Use `aws-cdk-lib/aws-eks-v2` para este ejemplo de **pila nueva**. Crea un `AWS::EKS::Cluster` nativo y una entrada de acceso; no se necesita ningún recurso personalizado de Lambda para habilitar Auto Mode. No considere la sustitución de un constructo existente ya desplegado por este ejemplo como una migración in situ.

El ejemplo usa la biblioteca CDK **2.273.0**, la CLI **2.1145.0** y EKS **1.36**. Importa subredes privadas existentes mediante atributos, sin una búsqueda de VPC durante la síntesis. Verifique la correspondencia entre las subredes/AZ proporcionadas, el DNS de la VPC, el enrutamiento, el acceso a los servicios y las etiquetas de subredes para balanceadores de carga antes del despliegue. Una definición de VPC importada no valida esas condiciones.

### Clúster de EKS Auto Mode con TypeScript

Guárdelo como `lib/eks-auto-mode-stack.ts`. Quien realice la llamada proporciona un rol de operador existente y aprobado; solo ese rol recibe acceso de administrador a este clúster. Los permisos de las cargas de trabajo siguen siendo independientes.

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

El rol del clúster incluye explícitamente `sts:TagSession` y las cinco políticas de Auto Mode, incluida `AmazonEKSBlockStoragePolicyV2`. `withoutPolicyUpdates()` evita que CDK 2.273.0 añada la política antigua de almacenamiento en bloques; este ejemplo se encarga de proporcionar todos los permisos necesarios. Las dependencias conservan esos roles hasta que finalice la eliminación del clúster. El rol de los nodos solo tiene las políticas mínimas de trabajador de Auto Mode y extracción de ECR.

`bootstrapSelfManagedAddons: false` evita que se superpongan complementos de redes autoadministrados. Auto Mode administra conjuntamente el cómputo, el balanceo de carga y el almacenamiento en bloques. La entrada de acceso del operador se crea por separado del rol de ejecución del clúster.

### Punto de entrada de la aplicación CDK

Guárdelo como `bin/eks-auto-mode.ts`; mantenga la línea shebang en la primera línea. Los valores de entorno son obligatorios para evitar el uso accidental de valores de ejemplo de cuenta, VPC o rol.

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

### Despliegue de CDK

Cree un proyecto nuevo, guarde los dos archivos de arriba después de la inicialización y proporcione los valores de la cuenta/región prevista. Use un rol de AWS autenticado y autorizado. Revise la configuración sintetizada de IAM/redes y la diferencia antes del despliegue. Las versiones de la biblioteca y la CLI de CDK son paquetes separados y no comparten el mismo número de versión.

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

En la auditoría se compilaron ambos archivos TypeScript y se sintetizó localmente la pila con identificadores ficticios: se verificaron las tres capacidades de Auto Mode, los CIDR de API acotados, los roles necesarios y una entrada de acceso de operador. No se generó ninguna Lambda ni recurso personalizado. Se rechazaron las entradas obligatorias ausentes. **No se ejecutó ningún bootstrap, búsqueda, despliegue, creación de clúster ni llamada a la API de AWS**, por lo que las cuotas de la cuenta, las redes y la disponibilidad de las cargas de trabajo siguen siendo verificaciones del despliegue.

Referencias: [Biblioteca de constructos EKS V2](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html), [Rol de clúster de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html), [Creación de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Configuración del acceso al clúster {#configuring-cluster-access}

Establezca el nombre del clúster, la región y la ruta dedicada de kubeconfig que haya generado el método seleccionado. Para los ejemplos de Terraform/CDK, establezca el rol de operador aprobado en `EKS_OPERATOR_ROLE_ARN`. Puede omitirlo si usa el acceso del creador mediante CLI. Escribir kubeconfig no concede permisos de Kubernetes.

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

Use entradas de acceso para el acceso nuevo de IAM. Este ejemplo concede a un rol nuevo acceso de lectura en el espacio de nombres `dev` existente; no duplique la entrada del operador administrada por su herramienta de IaC. El modo de autenticación debe ser `API` o `API_AND_CONFIG_MAP`. El método heredado `aws-auth` está obsoleto; no sobrescriba todo su ConfigMap. Cuando sea necesario, siga el procedimiento oficial de migración.

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

Este rol de lectura no concede acceso a la API de Secret ni permisos de modificación. Autentíquese como ese rol y compruebe `kubectl auth can-i`; otras concesiones de RBAC/políticas de EKS pueden añadir permisos. [Entradas de acceso de EKS](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)

## Validación del clúster {#cluster-validation}

Use `eks_kubectl` y el mismo kubeconfig dedicado de la sección de acceso. El acceso al plano de control por sí solo no demuestra el estado de los nodos ni de las cargas de trabajo.

### Validación básica

```bash
eks_kubectl cluster-info
eks_kubectl get nodes
eks_kubectl get pods -n kube-system
eks_kubectl get events --sort-by='.lastTimestamp'
```

### Validación específica de Auto Mode

AWS administra el controlador de aprovisionamiento de Auto Mode. No espere encontrar un Pod de controlador autoadministrado en un espacio de nombres `karpenter`. Inspeccione las condiciones y los eventos de NodePool/NodeClass, además de los NodeClaims de las cargas de trabajo que necesiten capacidad.

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### Despliegue de una aplicación de ejemplo

Use un espacio de nombres nuevo para comprobar el acceso a imágenes, la programación, la disponibilidad HTTP y un Service. Una configuración solo con Fargate necesita primero un perfil que coincida con este espacio de nombres.

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

Mientras se ejecuta el reenvío de puertos, abra `http://127.0.0.1:8080` y luego deténgalo con Ctrl-C. Esto comprueba el acceso a ClusterIP, no a un balanceador de carga externo. Para un NLB, elija `eks.amazonaws.com/nlb` de Auto Mode o `service.k8s.aws/nlb` de un AWS LBC instalado y autorizado, y revise por separado los requisitos previos de redes/costos. Durante esta auditoría no se realizó ningún despliegue ni reenvío de puertos.

## Actualización del clúster {#cluster-upgrade}

Revise primero las perspectivas de actualización, las API eliminadas, la compatibilidad de webhooks/complementos, las versiones de los nodos, las IP libres y el plan de recuperación. Actualice los nodos rezagados a la versión actual del plano de control y luego avance de una versión menor compatible a la vez. Algunos componentes necesitan actualizaciones compatibles antes que el plano de control.

Auto Mode no actualiza las versiones menores del plano de control cada 21 días. Los operadores planifican las actualizaciones de versiones menores y deben tener en cuenta las actualizaciones automáticas según la política de soporte de versiones.

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

Continúe con el plano de datos solo cuando la actualización indique `Successful`. AWS actualiza los nodos de Auto Mode de forma incremental; los grupos de nodos administrados convencionales necesitan una actualización aparte.

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

Planifique las actualizaciones de los nodos autoadministrados/Hybrid, la sustitución de los Pod de Fargate, las actualizaciones de los complementos y las actualizaciones de kubectl mediante sus respectivos mecanismos. Compruebe los PDB y la capacidad disponible en lugar de ocultar fallos con indicadores de forzado. Las actualizaciones del plano de control que cumplan los requisitos pueden revertirse una versión menor en un plazo de siete días, sujeto a la compatibilidad de los nodos/complementos/API y a las restricciones de la política de soporte; la reversión no sustituye la recuperación de los datos de las aplicaciones.

[Procedimiento de actualización](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [Condiciones de reversión](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## Eliminación del clúster {#cluster-deletion}

Elimine el clúster mediante la herramienta/el estado que lo administra originalmente, en la cuenta y región previstas. Primero elimine las cargas de trabajo y los Services de Ingress/LoadBalancer mientras sus controladores sigan ejecutándose y, después, verifique que se haya completado la eliminación. Decida cómo conservar o recuperar los PVC/PV, las instantáneas y los registros. No eluda los tiempos de espera ni los finalizadores usando opciones de forzado.

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

Use este método para un clúster creado con eksctl.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### Eliminación con AWS CLI

Para un clúster creado directamente con la CLI, establezca los nombres de los grupos de nodos/perfiles propios que se muestran arriba y repita el proceso para cada recurso. Espere a que finalice la eliminación y compruebe que no quede ninguno antes de eliminar el clúster.

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

Use la aplicación, las entradas, la cuenta y la región originales y verifique la pila de destino.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

Al finalizar, verifique el estado de EKS/CloudFormation y los recursos ELB, de disco, NAT, de registro e IAM que queden. Conserve los roles/políticas de Auto Mode hasta que termine la eliminación de la infraestructura administrada. No dé por hecho que la eliminación del clúster elimina una VPC, un rol de IAM, registros o datos conservados que sean propiedad de otros recursos. Durante la auditoría no se ejecutó ningún comando de eliminación.

## Conclusión

Hay varios métodos para crear un clúster de EKS, cada uno con sus ventajas y desventajas:

- **EKS Auto Mode**: Automatiza las operaciones de infraestructura; la preparación de las aplicaciones sigue necesitando validación
- **eksctl**: Creación sencilla y rápida de clústeres
- **Consola de administración de AWS**: Creación intuitiva mediante una interfaz gráfica
- **AWS CLI**: Adecuada para automatizar scripts
- **Terraform**: Administración de infraestructura como código
- **AWS CDK**: Definición de infraestructura mediante lenguajes de programación

Para producción, elija el modelo de cómputo y la herramienta de infraestructura que se ajusten a sus requisitos, y valide IAM, la conectividad, la capacidad, las interrupciones y el comportamiento de recuperación. Una plantilla correcta o la creación satisfactoria de un clúster no demuestran que esté listo para producción.

### Alcance de la validación de la auditoría

Se leyeron ambas versiones completas del lenguaje y se cotejaron con la documentación y los esquemas oficiales. La validación abarcó shell/JSON/YAML, compilación/síntesis de CDK, `terraform validate` y rutas de error simuladas. No se realizó ningún aprovisionamiento de AWS, actualización, eliminación, prueba de carga/ejecución de aplicaciones ni medición de costos.
