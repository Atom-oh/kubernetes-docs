# Parte 1: Requisitos previos

> **Última actualización**: October 16, 2026

Hay varias formas de crear un clúster de Amazon EKS. En este capítulo, aprenderemos a crear un clúster de EKS con diversas herramientas y métodos.

**Versión actual:** EKS 1.37 estuvo disponible el 1 de octubre de 2026.

**Versión de referencia del ejemplo:** Los capítulos sobre la creación de clústeres usan la versión de referencia revisada de EKS 1.36. Antes de elegir otra versión compatible, comprueba la compatibilidad con sus herramientas, imágenes de nodos y complementos.

## Tabla de contenido

1. [Requisitos previos](#prerequisites)
2. [eksctl](02-eks-cluster-creation-part2.md)
3. [Consola de administración de AWS y CLI](02-eks-cluster-creation-part3.md)
4. [Terraform](02-eks-cluster-creation-part4.md)
5. [Acceso, validación, actualizaciones y eliminación](02-eks-cluster-creation-part5.md)
6. [Guía completa y CDK](02-eks-cluster-creation.md)

## Requisitos previos {#prerequisites}

Antes de crear un clúster de EKS, se requieren los siguientes requisitos previos:

### 1. Cuenta de AWS

Se necesita una cuenta válida de AWS. Si no tienes una cuenta de AWS, puedes registrarte en el [sitio web de AWS](https://aws.amazon.com/).

### 2. Permisos de IAM

Los permisos necesarios dependen de la herramienta y de los recursos que administra. Una política que conceda `eks:*`, `ec2:*`, `iam:*` y `cloudformation:*` en todos los recursos no es una política de privilegio mínimo necesaria.

| Tarea | Alcance de permisos que se debe revisar |
| --- | --- |
| Administración de clústeres de EKS/grupos de nodos | Acciones de EKS necesarias y recursos de destino |
| Transferencia de roles de IAM existentes | `iam:PassRole` para ARN de roles aprobados y condiciones de servicio |
| Creación de roles/políticas/proveedores de OIDC de IAM | Recursos de IAM administrados por la herramienta y alcance de nombres/etiquetas |
| Creación de redes | Acciones de EC2 para la VPC, las subredes y los grupos de seguridad nuevos |
| Uso de eksctl/CDK | Pilas de CloudFormation pertinentes, roles de ejecución y recursos de arranque |

La identidad de aprovisionamiento, el rol de servicio del clúster y el rol del nodo son distintos. Los SCP, los límites de permisos y las políticas de sesión siguen aplicándose. Revisa los permisos de aprovisionamiento de tu organización comparándolos con la plantilla o el plan sintetizados. Los requisitos de roles de Auto Mode difieren de los de los grupos de nodos convencionales.

Referencias: [Acciones y recursos de IAM de EKS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html), [Roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

### 3. Instalación de herramientas

#### AWS CLI

Elige el paquete correspondiente a tu sistema operativo/CPU y sigue los pasos de verificación de firmas de la [guía oficial de instalación de AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Si ya tienes instalada la versión 1 o 2, revisa primero el procedimiento de actualización/migración correspondiente.

| Entorno | Paquete/método de instalación oficial |
| --- | --- |
| macOS | `AWSCLIV2.pkg` firmado |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` con verificación de firma PGP |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` con verificación de firma PGP |
| Windows | Instalador MSI para las versiones compatibles de Windows |

No uses sin cambios el paquete de Linux x86_64 en ARM. Comprueba la CLI activa con `aws --version`. Si tu organización usa IAM Identity Center, configura un perfil aprobado de la siguiente manera. De lo contrario, sigue el procedimiento de federación correspondiente en lugar de dar por sentado que debes usar claves de acceso de larga duración.

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

Consulta [Autenticación de IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). Sigue usando la cuenta, el rol y la región aprobados para los comandos posteriores.

#### kubectl y eksctl (Linux/macOS)

Los ejemplos de EKS 1.36 de este capítulo usan kubectl **1.36.5** y eksctl **0.231.0** como versión de referencia. Es preferible usar la misma versión menor de kubectl que la del servidor; la diferencia de versiones menores compatible es de ±1. No instales sin más la versión menor más reciente de `stable.txt` upstream para un clúster de EKS anterior.

Este ejemplo de Bash selecciona AMD64/ARM64 y verifica las sumas de comprobación oficiales antes de la instalación. Necesita `curl`, `tar`, `awk` y `sha256sum` o `shasum`; la instalación en `/usr/local/bin` requiere permisos de administrador. Si falla la descarga o la verificación de la suma de comprobación, se detiene la instalación.

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

Sigue el [procedimiento oficial de instalación de kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) en PowerShell. Para el ejemplo AMD64 de este capítulo, usa [kubectl 1.36.5](https://dl.k8s.io/release/v1.36.5/bin/windows/amd64/kubectl.exe) y el archivo `.sha256` en la misma ruta. Elige el ZIP de Windows que corresponda a tu CPU y `eksctl_checksums.txt` de la [versión 0.231.0 de eksctl](https://github.com/eksctl-io/eksctl/releases/tag/v0.231.0).

Compara `Get-FileHash -Algorithm SHA256` con el hash oficial y detente si no coinciden. Tras la verificación, extrae el ZIP, agrega el directorio del ejecutable a PATH y comprueba `kubectl version --client` y `eksctl version`. No ejecutes sintaxis de PowerShell en Bash.

También prepara `jq` para generar JSON en los ejemplos de AWS CLI. Durante esta auditoría no se descargó ni instaló ningún cliente ni se inició sesión.

### 4. VPC y subredes

![Diagrama de arquitectura de VPC de EKS con balanceadores de carga en subredes públicas, NAT Gateways y nodos de trabajo en subredes privadas en dos zonas de disponibilidad.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part1-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part1-0.html)

Este diagrama muestra una configuración basada en NAT, no un requisito para que todos los clústeres tengan acceso a Internet.

Un clúster regional de EKS requiere al menos dos subredes en distintas AZ de la misma VPC. Cada subred del clúster necesita al menos seis direcciones IP disponibles para EKS; AWS recomienda al menos dieciséis. Planifica direcciones adicionales para nodos, Pods, balanceadores de carga y actualizaciones. Habilita los nombres de host DNS y la resolución DNS de la VPC.

No todos los clústeres de EKS necesitan acceso a Internet. Los nodos y las cargas de trabajo necesitan acceso a la API de Kubernetes, a las imágenes y a los servicios de AWS necesarios, a través de rutas NAT/Internet o de los puntos de conexión de VPC requeridos y de imágenes reflejadas. Se puede acceder al punto de conexión privado de Kubernetes desde la VPC o desde redes conectadas con DNS y enrutamiento adecuados.

#### Etiquetas de VPC para el clúster de EKS

La etiqueta de VPC `kubernetes.io/cluster/<cluster-name>` es un mecanismo heredado, no un requisito universal vigente para crear clústeres de EKS. Sigue las reglas de detección de subredes del controlador elegido para el balanceo de carga:

- Subredes para balanceadores de carga públicos: `kubernetes.io/role/elb=1`
- Subredes para balanceadores de carga internos: `kubernetes.io/role/internal-elb=1`

Las etiquetas no configuran el enrutamiento, los grupos de seguridad ni la capacidad disponible de direcciones IP. Consulta [Requisitos de VPC/subredes](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) y [Clústeres sin acceso a Internet](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html).

## Cuestionario

Para comprobar lo que has aprendido en este capítulo, prueba el [Cuestionario sobre la creación de clústeres de EKS - Parte 1](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md).
