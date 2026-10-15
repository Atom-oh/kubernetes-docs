# Parte 1: Requisitos previos

> **Última actualización**: October 12, 2026

Hay varias formas de crear un clúster de Amazon EKS. En este capítulo, aprenderemos a crear un clúster de EKS utilizando diversas herramientas y métodos.

**Versión actual:** EKS 1.37 estuvo disponible el 1 de octubre de 2026.

**Base del ejemplo:** Los capítulos de creación de clústeres utilizan la base revisada de EKS 1.36. Antes de elegir otra versión compatible, compruebe la compatibilidad con sus herramientas, imágenes de nodos y complementos.

## Tabla de contenidos

1. [Requisitos previos](#prerequisites)
2. [eksctl](02-eks-cluster-creation-part2.md)
3. [AWS Management Console y CLI](02-eks-cluster-creation-part3.md)
4. [Terraform](02-eks-cluster-creation-part4.md)
5. [Acceso, validación, actualizaciones y eliminación](02-eks-cluster-creation-part5.md)
6. [Guía completa y CDK](02-eks-cluster-creation.md)

## Requisitos previos

Antes de crear un clúster de EKS, se requieren los siguientes requisitos previos:

### 1. Cuenta de AWS

Se requiere una cuenta de AWS válida. Si no tiene una cuenta de AWS, puede registrarse en el [sitio web de AWS](https://aws.amazon.com/).

### 2. Permisos de IAM

Los permisos necesarios dependen de la herramienta y los recursos que administra. Una política que conceda `eks:*`, `ec2:*`, `iam:*` y `cloudformation:*` sobre cada recurso no es una política de privilegios mínimos obligatoria.

| Tarea | Alcance de permisos que se debe revisar |
| --- | --- |
| Administración de clúster/grupo de nodos de EKS | Acciones de EKS requeridas y recursos de destino |
| Transferir roles de IAM existentes | `iam:PassRole` para ARN de roles aprobados y condiciones de servicio |
| Crear roles/políticas/proveedores de OIDC de IAM | Recursos de IAM administrados por la herramienta y alcance de nombre/etiqueta |
| Crear redes | Acciones de EC2 para la nueva VPC, subredes y grupos de seguridad |
| Usar eksctl/CDK | Pilas relevantes de CloudFormation, roles de ejecución y recursos de bootstrap |

La identidad de aprovisionamiento, el rol de servicio del clúster y el rol de nodo son independientes. Las SCP, los límites de permisos y las políticas de sesión se siguen aplicando. Revise los permisos de aprovisionamiento de su organización con respecto a la plantilla o el plan sintetizado. Los requisitos de roles de Auto Mode difieren de los grupos de nodos convencionales.

Referencias: [acciones y recursos de IAM para EKS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html), [roles de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

### 3. Instalación de herramientas

#### AWS CLI

Elija el paquete para su SO/CPU y siga la verificación de firma en la [guía oficial de instalación de AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Para una instalación existente de v1/v2, revise primero su procedimiento de actualización o migración.

| Entorno | Método oficial de paquete/instalación |
| --- | --- |
| macOS | `AWSCLIV2.pkg` firmado |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` con verificación de firma PGP |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` con verificación de firma PGP |
| Windows | Instalador MSI para versiones compatibles de Windows |

No utilice sin cambios el paquete de Linux x86_64 en ARM. Compruebe la CLI activa con `aws --version`. Si su organización utiliza IAM Identity Center, configure un perfil aprobado de la siguiente manera. De lo contrario, siga su procedimiento de federación en lugar de asumir claves de acceso de larga duración.

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

Consulte la [autenticación de IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). Siga utilizando la cuenta, el rol y la región aprobados para los comandos posteriores.

#### kubectl y eksctl — Linux/macOS

Los ejemplos de EKS 1.36 de este capítulo usan kubectl **1.36.4** y eksctl **0.230.0** como base. Prefiera la misma versión menor de kubectl que la del servidor; la diferencia de versiones compatible es de ±1 versión menor. No instale a ciegas la versión menor más reciente desde el `stable.txt` ascendente para un clúster de EKS más antiguo.

Este ejemplo de Bash selecciona AMD64/ARM64 y verifica las sumas de comprobación oficiales antes de la instalación. Necesita `curl`, `tar`, `awk` y `sha256sum` o `shasum`; la instalación en `/usr/local/bin` requiere permiso de administrador. Un fallo en la descarga o la suma de comprobación detiene la instalación.

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

Procedimientos oficiales: [kubectl para Linux](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/), [kubectl para macOS](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/), [instalación de eksctl](https://eksctl.io/installation/).

#### Windows

Siga el [procedimiento oficial de instalación de kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) en PowerShell. Para el ejemplo AMD64 de este capítulo, use [kubectl 1.36.4](https://dl.k8s.io/release/v1.36.4/bin/windows/amd64/kubectl.exe) y el archivo `.sha256` en la misma ruta. Seleccione el ZIP de Windows que coincida con su CPU y `eksctl_checksums.txt` de la [versión de eksctl 0.230.0](https://github.com/eksctl-io/eksctl/releases/tag/v0.230.0).

Compare `Get-FileHash -Algorithm SHA256` con el hash oficial y deténgase si no coincide. Después de la verificación, extraiga el ZIP, añada el directorio del ejecutable a PATH y compruebe `kubectl version --client` y `eksctl version`. No ejecute sintaxis de PowerShell en Bash.

Prepare también `jq` para la generación de JSON en los ejemplos de AWS CLI. Durante esta auditoría no se realizó ninguna descarga/instalación de cliente ni inicio de sesión real.

### 4. VPC y subredes

![Diagrama de arquitectura de VPC de EKS que ubica balanceadores de carga en subredes públicas, NAT Gateways y nodos de trabajo en subredes privadas a través de dos zonas de disponibilidad.](../.gitbook/assets/en-eks-02-eks-cluster-creation-part1-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part1-0.html)

Este diagrama muestra una disposición basada en NAT, no un requisito de que todos los clústeres tengan acceso a Internet.

Un clúster regional de EKS requiere al menos dos subredes en distintas AZ de la misma VPC. Cada subred del clúster necesita al menos seis IP disponibles para EKS; AWS recomienda al menos dieciséis. Planifique direcciones adicionales para nodos, Pods, balanceadores de carga y actualizaciones. Habilite los nombres de host de DNS y la resolución de DNS de la VPC.

El acceso a Internet no es obligatorio para todos los clústeres de EKS. Los nodos y las cargas de trabajo necesitan acceso a la API de Kubernetes, imágenes y los servicios de AWS necesarios a través de rutas de NAT/Internet o los endpoints de VPC necesarios e imágenes reflejadas. El endpoint privado de Kubernetes es accesible desde la VPC o redes conectadas con DNS y enrutamiento adecuados.

#### Etiquetas de VPC para el clúster de EKS

La etiqueta de VPC `kubernetes.io/cluster/<cluster-name>` es un mecanismo heredado, no un requisito universal actual para la creación de EKS. Siga las reglas de descubrimiento de subredes del controlador elegido para el balanceo de carga:

- Subredes para balanceadores de carga públicos: `kubernetes.io/role/elb=1`
- Subredes para balanceadores de carga internos: `kubernetes.io/role/internal-elb=1`

Las etiquetas no configuran el enrutamiento, los grupos de seguridad ni la capacidad de IP libre. Consulte los [requisitos de VPC/subred](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) y los [clústeres sin acceso a Internet](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html).

## Cuestionario

Para probar lo que aprendió en este capítulo, intente el [Cuestionario de creación de clúster de EKS - Parte 1](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md).