# Guía de instalación y migración del sistema operativo para servidores bare metal

< [Anterior: Operaciones y mantenimiento](./08-operations.md) | [Tabla de contenido](./README.md) | [Siguiente: Gateway de Hybrid Nodes](./10-hybrid-nodes-gateway.md) >

> **Base de validación**: Se revisaron la documentación de AWS Hybrid para SO/nodeadm y los precios públicos el 13 de septiembre de 2026; nodeadm 1.0.20 es la referencia de CLI revisada. Elija una combinación de EKS/SO/CNI compatible en la actualidad.
> **Última actualización**: 13 de septiembre de 2026

Esta guía separa la instalación destructiva del SO, la preparación de imágenes, la incorporación al clúster y las comprobaciones de aceptación de solo lectura. Los ejemplos contienen marcadores de posición y requieren un plan de instalación específico para cada host. Para esta revisión no se ejecutó ninguna instalación de SO, compilación de Packer, creación de VM ni operación de AWS/clúster.

## Descripción general

### Por qué elegir bare metal

Eliminar un hipervisor puede evitar sus costos de licencia y su capa de ejecución, pero no garantiza un menor costo total ni un mejor rendimiento de las aplicaciones. Antes de elegir una alternativa, haga un inventario de las funciones de virtualización, la disponibilidad, las copias de seguridad, el almacenamiento, las redes, los contratos de soporte y el esfuerzo de migración. Las aplicaciones de VM no se convierten automáticamente en contenedores, y las obligaciones de licencia existentes no desaparecen cuando se inicia un clúster piloto.

### Matriz de compatibilidad de la infraestructura del SO

| SO | Bare metal | Virtualización local | Límites de configuración y soporte |
| --- | --- | --- | --- |
| Ubuntu 20.04/22.04/24.04 | Familias de Hybrid OS enumeradas | Infraestructura host compatible, sujeta a los requisitos de SO/kernel/CNI | nodeadm/YAML; verifique por separado el ciclo de vida y el soporte de Ubuntu |
| RHEL 8/9 | Familias de Hybrid OS enumeradas | Infraestructura host compatible, sujeta a los requisitos de SO/kernel/CNI | nodeadm/YAML; la suscripción y el soporte de SO de Red Hat siguen siendo independientes |
| AL2023 | **No es la ruta de implementación compatible** | Huésped virtualizado local | nodeadm/YAML; AWS Support Plans no cubren AL2023 fuera de EC2 |
| Variantes de Bottlerocket VMware a partir de 1.37.0 | **No compatible con Hybrid bare metal** | VMware vSphere, **x86_64** | Configuración/bootstrap de Bottlerocket; govc administra las VM de VMware |

AWS admite la integración de Hybrid con las familias Ubuntu/RHEL enumeradas, no las obligaciones de soporte del proveedor del SO. Compruebe las versiones específicas, la arquitectura y los requisitos de CNI/kernel. AL2023 fuera de EC2 es una opción de VM huésped, no una recomendación genérica de imagen sin procesar para bare metal. Las variantes de Kubernetes de Bottlerocket para VMware comienzan en 1.28; esto indica el historial de variantes, no recomienda ejecutar esa versión antigua de EKS. Las instalaciones y actualizaciones con SSM requieren nodeadm 1.0.19 o posterior, ya que las versiones anteriores usan una clave de firma de SSM obsoleta.

## Análisis comparativo de costos

### Comparación de costos de licencias/suscripciones

#### VMware vSphere

Solicite una cotización actual para el paquete de productos real, los núcleos con licencia, los mínimos, el plazo y el soporte. La cifra anterior de $4.500–8.500 por socket/año no tiene aquí una fuente verificada y no puede considerarse una cotización actual de vSphere.

#### OpenShift

Normalice los derechos reales de Red Hat, las métricas de núcleos físicos/virtuales o de sockets y los niveles de soporte. La estimación anterior de $2.500–5.000 por nodo/año y la afirmación de que «incluye soporte prémium» no están verificadas; no las use como precio actual ni como garantía de derechos.

#### EKS Hybrid Nodes

La [página oficial de precios](https://aws.amazon.com/eks/pricing/) aplica niveles marginales mensuales sobre las **horas-vCPU de los nodos declaradas**: las primeras 576.000 a $0,020; las siguientes 576.000 a $0,014; las siguientes 4.608.000 a $0,010; las siguientes 5.760.000 a $0,008; por encima de 11.520.000, a $0,006. No se trata de una tarifa plana universal de $0,01.

Los niveles se agregan dentro de una cuenta/Región o entre cuentas de la misma Región con la facturación consolidada de AWS Organizations. Los núcleos bare metal con hyperthreading pueden declarar dos vCPU cada uno. Los cargos comienzan cuando se incorpora un nodo y terminan cuando se elimina; las cargas de trabajo inactivas no eliminan el cargo del nodo. AWS pide a los clientes que se pongan en contacto con su equipo de cuenta para máquinas de más de 32 vCPU. Los cargos por clúster, plano de control/capacidad aprovisionados, red, registros, almacenamiento, SO y otros servicios de soporte son independientes.

### Comparación de costos anuales por escala (servidores de 32 vCPU)

Lo siguiente es un **modelo** determinista, no una factura ni una medición: 32 vCPU declaradas por nodo, 730 horas cada mes, una Región/ámbito de agregación, ningún otro uso de Hybrid y doce meses modelados idénticos. La última columna suma un clúster de nivel básico con soporte estándar a $0,10/hora. Excluye otros servicios, descuentos/impuestos, hardware, energía, derechos del SO, mano de obra y migración; la duración real de los meses y los reinicios de nivel afectan las facturas.

| Nodos | Horas-vCPU mensuales | Tarifa mensual de nodos | Tarifa anualizada de nodos | Nodos anualizados + un clúster con soporte estándar básico |
| --- | --- | --- | --- | --- |
| 10 | 233.600 | $4.672,00 | $56.064,00 | $56.940,00 |
| 50 | 1.168.000 | $19.744,00 | $236.928,00 | $237.804,00 |
| 100 | 2.336.000 | $31.424,00 | $377.088,00 | $377.964,00 |

<details>
<summary>Estimaciones históricas conservadas (no verificadas y no son precios actuales)</summary>

La tabla original se conserva para facilitar la trazabilidad. No se pudieron verificar las fuentes de las cotizaciones de proveedores. La columna de EKS usaba el supuesto obsoleto `32 × $0,01 × 8.760 = $2.803,20 por nodo/año`, sin tarifa de clúster ni niveles marginales. Estas cifras no son evidencia válida y actual para una comparación del costo total de propiedad.

| Escala | VMware vSphere (estimación anual anterior) | OpenShift (estimación anual anterior) | EKS Hybrid (estimación obsoleta de tarifa plana) |
| --- | --- | --- | --- |
| 10 nodos | ~$45.000–85.000 | ~$25.000–50.000 | ~$28.032 |
| 50 nodos | ~$225.000–425.000 | ~$125.000–250.000 | ~$140.160 |
| 100 nodos | ~$450.000–850.000 | ~$250.000–500.000 | ~$280.320 |

</details>

### Consideraciones sobre el costo total de propiedad (TCO)

Incluya capacidad de reserva, instalaciones/energía, aplicación de parches del SO y de seguridad, operaciones de PKI/SSM, almacenamiento/copias de seguridad/restauración, conectividad, supervisión, personal, obligaciones de licencia y capacidad de reversión. Compare ámbitos equivalentes de disponibilidad/soporte; no afirme un porcentaje de ahorro basándose en la tabla anterior no verificada.

## Instalación bare metal específica del SO

### Requisitos previos

#### Configuración de BIOS/UEFI

Verifique el instalador seleccionado, el firmware, el modo de arranque, los controladores de NIC/almacenamiento y la cadena de arranque firmada. Mantenga Secure Boot cuando la cadena validada de cargador de arranque/kernel/módulos lo admita; no lo desactive como requisito general para contenedores. Los contenedores Linux habituales con containerd/runc no requieren virtualización de hardware VT-x/AMD-V. Los entornos aislados basados en VM, los generadores de imágenes QEMU/KVM y otras cargas de trabajo de virtualización tienen requisitos propios.

#### Infraestructura de red

El PXE heredado suele usar DHCP/ProxyDHCP y TFTP, mientras que los diseños UEFI HTTP/iPXE pueden usar otros transportes de arranque. `pxelinux.0` no es un cargador universal para UEFI. Use el cargador de arranque adecuado para el firmware, verifique la integridad de ISO/kernel/initrd y separe las redes de aprovisionamiento de las redes de cargas de trabajo. Proteja la configuración específica de cada host; no sirva códigos de activación, claves privadas ni contraseñas desde una raíz HTTP/TFTP compartida y sin autenticación.

#### Plantillas de Packer para AWS

El [directorio de ejemplos de AWS](https://github.com/aws/eks-hybrid/tree/main/example/packer) contiene actualmente `hybrid-nodes-template.pkr.hcl`, no el archivo inventado originalmente `bare-metal-template.pkr.hcl`. Su parámetro de entrada `CREDENTIAL_PROVIDER` acepta `ssm` o `iam`; su HCL asigna `iam` a `iam-ra` de nodeadm. La salida de QEMU usa `PACKER_OUTPUT_FORMAT`, no una variable `output_format`. Revise la plantilla y los scripts de aprovisionamiento en una confirmación aprobada, incluidos los parámetros obligatorios del generador y el manejo de contraseñas/datos de usuario.

```bash
# From a reviewed checkout of aws/eks-hybrid/example/packer:
export NODEADM_ARCH=amd       # This template uses amd/arm, not amd64/arm64.
export CREDENTIAL_PROVIDER=ssm # The template accepts ssm/iam; maps iam to nodeadm iam-ra.
export PACKER_OUTPUT_FORMAT=raw
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
: "${ISO_URL:?Set the approved Ubuntu or RHEL installer ISO}"
: "${ISO_CHECKSUM:?Set the verified vendor ISO checksum}"
export K8S_VERSION ISO_URL ISO_CHECKSUM
# Also prepare the selected builder's required inputs using the reviewed template.
packer validate -syntax-only hybrid-nodes-template.pkr.hcl
# A separate build action, not a validation step:
# packer build -only=general-build.qemu.ubuntu24 hybrid-nodes-template.pkr.hcl
```

La plantilla también incluye generadores de AMI/vSphere: seleccione solo el generador previsto antes de una compilación autorizada por separado. La validación de sintaxis solamente no genera ni prueba una imagen. No copie ejemplos obsoletos de Kubernetes, contraseñas predeterminadas del generador, archivos de credenciales legibles por todo el mundo ni identidades de máquina/SSM registradas en una imagen reutilizable.

Para un host aprovisionado manualmente, prepare una versión/arquitectura aprobada de nodeadm con una suma de comprobación revisada. Este es un **paso de instalación**, no una comprobación de estado. Obtenga la suma de comprobación mediante el proceso aprobado de verificación de versiones; no la invente ni omita una discrepancia.

```bash
set -euo pipefail
: "${NODEADM_VERSION:?Set the approved release, at least 1.0.19 for SSM}"
: "${NODEADM_SHA256:?Set the approved SHA-256 for this release and architecture}"
: "${NODEADM_ARTIFACT:?Set the local file delivered through the approved artifact channel}"
case "$(uname -m)" in
  x86_64) NODEADM_ARCH=amd64 ;;
  aarch64|arm64) NODEADM_ARCH=arm64 ;;
  *) printf 'Unsupported architecture\n' >&2; exit 2 ;;
esac
[[ "$NODEADM_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 2
[[ "$NODEADM_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || exit 2
[[ "$(printf '%s\n' 1.0.19 "$NODEADM_VERSION" | sort -V | head -n 1)" == 1.0.19 ]] || exit 2
umask 077
STAGING_DIR=$(mktemp -d)
trap 'rm -f -- "$STAGING_DIR/nodeadm"; rmdir -- "$STAGING_DIR"' EXIT
cp -- "$NODEADM_ARTIFACT" "$STAGING_DIR/nodeadm"
printf '%s  %s\n' "$NODEADM_SHA256" "$STAGING_DIR/nodeadm" | sha256sum --check -
chmod 0700 "$STAGING_DIR/nodeadm"
# Check the verified staged binary before replacing the installed executable.
ACTUAL_VERSION=$("$STAGING_DIR/nodeadm" --version)
VERSION_RE="(^|[^0-9.])v?${NODEADM_VERSION//./\\.}([^0-9A-Za-z.+-]|$)"
[[ "$ACTUAL_VERSION" =~ $VERSION_RE ]] || { printf 'Artifact version mismatch\n' >&2; exit 2; }
printf '%s\n' "$ACTUAL_VERSION"
sudo install -m 0755 "$STAGING_DIR/nodeadm" /usr/local/bin/nodeadm
/usr/local/bin/nodeadm --version
```

### Ubuntu LTS (22.04/24.04)

Autoinstall de Ubuntu Server usa YAML; cloud-init puede proporcionar su configuración. La plantilla siguiente mantiene deliberadamente interactivo el almacenamiento y exige un número de serie de disco aprobado exacto y una clave SSH antes de usarse. Seleccionar o particionar un disco destruye sus datos existentes. Confirme primero las copias de seguridad, el inventario de discos, la entrega del instalador, el acceso/la recuperación y la compatibilidad del firmware en un destino desechable. No es apropiado usar coincidencias de disco vacías o comodines ni suponer que se trata del «disco más grande» en un host con discos de datos.

#### Ejemplo de configuración de Autoinstall

```yaml
#cloud-config
autoinstall:
  version: 1
  interactive-sections: [storage]
  locale: en_US.UTF-8
  keyboard:
    layout: us
  storage:
    layout:
      name: lvm
      match:
        serial: REPLACE_WITH_APPROVED_DISK_SERIAL
  identity:
    hostname: replace-with-unique-hostname
    username: hybrid-admin
    password: "!"
  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
    - "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
  packages: [curl, jq]
  shutdown: poweroff
```

`password: "!"` bloquea la autenticación por contraseña en esta plantilla; verifique el acceso SSH aprobado real y la ruta de recuperación. Proporcione la configuración de red/NIC/VLAN/agregación adecuada para el host y el instalador elegido. La comprobación local del esquema no prueba la selección del disco, el arranque ni el inicio de sesión. nodeadm se prepara/instala en el paso independiente anterior; el instalador no descarga un binario `latest` sin verificar.

#### Notas específicas para Ubuntu 24.04

El [error 2065423 de Ubuntu](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423) se refiere a la denegación de señales de AppArmor durante la terminación de contenedores y cuenta con correcciones en paquetes publicados. La página de SO de AWS aún describe el contexto de la corrección para la versión 1.7.19 o posterior. Compruebe el paquete/backport real de la distribución, el perfil cargado, el runtime y los registros de denegaciones. Esto no es un diagnóstico universal para todos los Pod bloqueados ni una recomendación de permanecer en una versión antigua de containerd.

```bash
# Read-only investigation on the affected host:
containerd --version
dpkg-query -W 'containerd*' 'runc*' 'apparmor*'
sudo journalctl -k --since '30 minutes ago' --no-pager -n 200
if test -f /run/reboot-required.pkgs; then cat /run/reboot-required.pkgs; fi
```

Para la transición documentada del paquete/perfil afectado, el problema de Ubuntu requiere un reinicio para cargar los perfiles corregidos; programe el drenado, el reinicio y las comprobaciones de cargas de trabajo mediante el procedimiento del ciclo de vida. No generalice que toda modificación de AppArmor requiere un reinicio. `aa-remove-unknown` elimina todos los perfiles cargados que no están en `/etc/apparmor.d`; no es un editor de perfiles específico ni el comando de reparación predeterminado.

### RHEL 9

RHEL usa Kickstart. Lo siguiente es una plantilla de instalación, **no Bash**. Sustituya los marcadores de posición por un identificador aprobado para un único disco de instalación, un hash de contraseña y una clave pública SSH completa. `ignoredisk --only-use` y `clearpart --drives` deben especificar ese mismo disco verificado; no use un `clearpart --all` sin restricciones. Adapte los detalles de repositorio/stage2/cargador de arranque/red al instalador de RHEL elegido y valídelos con su ksvalidator antes de usarlos.

#### Ejemplo de configuración de Kickstart

```text
# Template: substitute and validate the approved target disk, key and password hash.
lang en_US.UTF-8
keyboard us
timezone UTC --utc
rootpw --lock
user --name=hybrid-admin --groups=wheel --iscrypted --password=REPLACE_WITH_CRYPT_HASH
sshkey --username=hybrid-admin "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
network --bootproto=dhcp --device=link --activate
ignoredisk --only-use=REPLACE_WITH_APPROVED_INSTALL_DISK
clearpart --all --initlabel --drives=REPLACE_WITH_APPROVED_INSTALL_DISK
autopart --type=lvm
selinux --enforcing
services --enabled=sshd
%packages
@core
openssh-server
curl
jq
%end
poweroff
```

Mantenga SELinux en modo enforcing y diagnostique los requisitos específicos de política/contexto. nodeadm documenta la configuración de SELinux de containerd y los contextos de seguridad de Pod; no marque `container_t` como permisivo de forma generalizada. Los paquetes del SO y la instalación de nodeadm/containerd son etapas independientes.

#### Notas sobre la instalación de containerd en RHEL

`distro` no es una fuente compatible de containerd para nodeadm en RHEL. Elija `docker` para que nodeadm instale el paquete compatible distribuido por Docker, o `none` si instala y mantiene containerd por separado. Afirmar que «RHEL siempre requiere docker» es demasiado general.

```bash
set -euo pipefail
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
sudo nodeadm install "$K8S_VERSION" --credential-provider ssm \
  --containerd-source docker
# If containerd is separately installed and maintained, choose --containerd-source none.
```

#### Entornos a gran escala: integración con Satellite/Foreman

Satellite/Foreman puede administrar plantillas Kickstart revisadas, repositorios y flujos de trabajo de aprovisionamiento. Valide los discos por host, las identidades de hardware, las suscripciones, la integridad de los artefactos y la recuperación ante errores; una plantilla compartida sintácticamente válida no autoriza a borrar una flota arbitraria.

### Amazon Linux 2023

Esta es una **referencia para huéspedes virtualizados**, no una opción de instalación bare metal. AWS proporciona imágenes de VM KVM, VMware y Hyper-V para AL2023 fuera de EC2. AWS Support Plans no cubre ese uso del SO AL2023 fuera de EC2; distíngalo del soporte de integración de EKS Hybrid. Use la imagen adecuada y el transporte de cloud-init. Este es un fragmento mínimo de identidad de VM:

```yaml
#cloud-config
# VM identity fragment only; it does not install or join a Hybrid Node.
hostname: replace-with-unique-hostname
manage_etc_hosts: true
ssh_pwauth: false
```

Deliberadamente no crea un administrador, no incorpora claves ni inicializa un nodo. Prepare el acceso aprobado y use el flujo de bootstrap revisado por separado. `--containerd-source docker` no es compatible con AL2023; use su fuente de distribución compatible o administre containerd por su cuenta de forma deliberada.

### Bottlerocket en VMware (referencia)

Para EKS Hybrid Nodes, use variantes de VMware compatibles a partir de 1.37.0 en x86_64. La configuración y los contenedores de bootstrap de Bottlerocket configuran el SO/autenticación; govc es una CLI de administración de VM de VMware, no un analizador de configuración TOML. Use la [guía completa de bootstrap](./04-node-bootstrap.md) para consultar los ajustes versionados, los datos de usuario privados y la configuración de credenciales.

## Comparación de configuración de proveedores de credenciales

### Configuración basada en nodeadm (Ubuntu/RHEL/AL2023)

Estas son alternativas independientes de SSM y IAM Roles Anywhere. Sustituya todos los marcadores de posición por el clúster/Región/identidad aprobados, proteja NodeConfig con propiedad de root y modo 0600, y mantenga privadas las claves privadas de cada host. No incluya el estado de registro de SSM ni una misma clave de host compartida en imágenes maestras clonadas.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: "REPLACE_WITH_PRIVATE_ACTIVATION_CODE"
      activationId: "REPLACE_WITH_PRIVATE_ACTIVATION_ID"
```

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_WITH_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_WITH_ID
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

nodeadm valida la configuración y obtiene los metadatos del clúster necesarios mediante la identidad de AWS configurada. Verifique la conectividad real con la API, las entradas de acceso de EKS, la confianza/los permisos y las rutas de los certificados antes de incorporarse; analizar YAML por sí solo no demuestra que haya autorización.

### Configuración basada en Bottlerocket (VMware)

Los bloques anteriores `[settings.hybrid.ssm]` y `[settings.hybrid.iam-roles-anywhere]` no eran configuraciones válidas de Bottlerocket. Use los ajustes de Kubernetes compatibles y las entradas documentadas para el contenedor de bootstrap de Hybrid descritas en [bootstrap de nodos](./04-node-bootstrap.md). Los datos de usuario codificados en Base64 no están cifrados; proteja guestinfo de VMware y los registros de aprovisionamiento.

### Guía de selección de proveedor de credenciales

| Situación | Consideración para la selección |
| --- | --- |
| Sin PKI administrada | La activación híbrida de SSM puede reducir el trabajo de administración de certificados; mantenga el ciclo de vida de identidades/activación |
| PKI administrada existente | IAM Roles Anywhere puede usar identidad X.509 por host; mantenga la emisión, la confianza, el vencimiento y la revocación |
| Sin acceso a Internet público | Cualquiera de las opciones necesita acceso a las API de AWS requeridas a través de una ruta privada/proxy aprobada; verifique la compatibilidad de los puntos de conexión |
| Totalmente desconectado/DDIL | EKS Hybrid Nodes no es el modelo operativo compatible; IAM Roles Anywhere sigue llamando a AWS CreateSession |
| Identidad de nodo personalizada | Revise las reglas de nomenclatura y ciclo de vida del proveedor; no dé por sentado que el nombre de Node es un nombre de host resoluble |

Consulte [conectividad privada](./03-airgap-setup.md). «Sin acceso a Internet público» y «sin conectividad con AWS» son requisitos distintos.

## Automatización del aprovisionamiento a gran escala

### Configuración de la infraestructura de arranque PXE

```text
Approved host/firmware inventory
  → matching DHCP/HTTP/PXE boot configuration
  → verified signed loader and installer kernel/initrd
  → protected host-specific installation configuration
  → explicit approved disk / OS installation
  → unique host identity / separate Hybrid bootstrap
```

La combinación TFTP/PXELINUX mostrada describe BIOS heredado. El PXE UEFI también puede usar TFTP, pero necesita un cargador compatible con UEFI; elija transportes seguros compatibles con el entorno real. Las sumas de comprobación de ISO y la confianza en firmas son independientes de la disponibilidad de DHCP.

### Playbook de automatización de Ansible

El siguiente playbook es una **comprobación previa de solo lectura para hosts ya preparados**. Se detiene si faltan componentes/servicios y no usa la existencia de `/usr/bin/kubelet` como prueba de que esté instalada la versión deseada. No instala binarios, no implementa plantillas secretas ni ejecuta nodeadm init repetidamente.

```yaml
# Read-only preflight; does not provision, install, or initialize hosts.
- name: Inspect approved Hybrid hosts
  hosts: hybrid_nodes
  become: true
  gather_facts: false
  serial: 1
  any_errors_fatal: true
  tasks:
  - name: Read OS release
    ansible.builtin.command:
      argv: [cat, /etc/os-release]
    changed_when: false
  - name: Read architecture
    ansible.builtin.command:
      argv: [uname, -m]
    changed_when: false
  - name: Read installed nodeadm version
    ansible.builtin.command:
      argv: [/usr/local/bin/nodeadm, --version]
    changed_when: false
  - name: Check each required service
    ansible.builtin.command:
      argv: [systemctl, is-active, --quiet, "{{ item }}"]
    loop: [containerd, kubelet]
    changed_when: false
```

Para aprovisionar, use etapas aprobadas distintas: validar el inventario de hosts/discos → preparar los artefactos/SO verificados → proporcionar configuración privada para cada host → ejecutar el [procedimiento de estado/identidad de bootstrap](./04-node-bootstrap.md) → verificar el UID real de Node, la versión, el Lease nuevo y el estado de las cargas de trabajo. Para los hosts existentes, use la [administración del ciclo de vida](./07-node-lifecycle.md). Coordine un host a la vez, deténgase ante errores y conserve evidencia del estado parcial; no oculte cambios detrás de `creates: /usr/bin/kubelet`.

## Estrategias de migración

### VMware → bare metal + EKS Hybrid Nodes

#### Fase 1: Crear infraestructura paralela

Haga un inventario de cargas de trabajo, máquinas virtuales, licencias, funciones de red/seguridad, almacenamiento y dependencias. Prepare un destino paralelo compatible, conectividad privada y capacidad de reversión. Bottlerocket en VMware puede permanecer durante una transición, pero no se convierte en un SO bare metal.

#### Fase 2: Contenerizar las cargas de trabajo

Contenerice explícitamente las cargas de trabajo adecuadas; algunas VM quizá deban seguir siendo VM. Valide la migración del estado, el comportamiento de CSI, los permisos, las copias de seguridad y las restauraciones antes de trasladar las cargas de trabajo que escriben datos. Las bases de datos administradas de AWS son una opción arquitectónica, no una conversión automática.

#### Fase 3: Transición de red

Haga un inventario por separado de las funciones de enrutamiento, superposición, firewall, balanceo de carga y políticas de NSX-T. Cilium BGP intercambia rutas; no reemplaza de forma equivalente todas las funciones de NSX-T. Valide el direccionamiento, las rutas de retorno, el ingreso/TLS, DNS, las políticas y las conexiones establecidas antes de cambiar el tráfico.

#### Fase 4: Retirar VMware

Retire VMware solo después de la aceptación de las cargas de trabajo/datos, de acordar una ventana de reversión, de comprobar la recuperación de las copias de seguridad y de tomar decisiones sobre licencias/retención. Verifique la infraestructura real que se va a retirar; no convierta la cancelación de licencias ni el borrado de discos en un paso final automático de la canalización.

### OpenShift → EKS Hybrid Nodes

#### Correspondencia conceptual

| OpenShift | Destino candidato | Brecha de migración que debe resolverse |
| --- | --- | --- |
| Route | Controlador de Ingress / Gateway API | La terminación TLS, reencrypt/passthrough, los pesos, las anotaciones y las políticas dependen del controlador |
| SCC | PSS/Pod Security Admission más las políticas/los valores predeterminados necesarios | PSS no reproduce las estrategias de UID/SELinux/grupos ni la mutación de SCC |
| OLM | OLM compatible, Helm o distribución de EKS add-on/operator | OLM puede ejecutarse en Kubernetes; la conversión de CRD, las actualizaciones y las dependencias no se migran automáticamente |
| MachineSet | Automatización del ciclo de vida/aprovisionamiento de hosts | nodeadm/Ansible no es un controlador de Machine API con semántica de reemplazo/escalado |
| ImageStream | Registro más automatización de promoción de imágenes/activadores | ECR almacena imágenes; no reemplaza la importación/etiquetado/activación de cambios de ImageStream |
| BuildConfig | CI/CD externo revisado | Reproduzca el comportamiento de origen, imagen, credenciales y políticas de compilación |
| DeploymentConfig | Deployment más la automatización de implementación necesaria | Preserve los activadores, los hooks, las estrategias y el comportamiento de reversión |

#### Lista de comprobación para la migración de cargas de trabajo

- Haga un inventario de cada Route, política/valor predeterminado, CRD/operator, activador de imagen, compilación y hook de implementación.
- Pruebe el comportamiento del destino y el ámbito de service accounts/RBAC con cargas de trabajo representativas.
- Verifique la coherencia de datos, las instantáneas/restauraciones, DNS/TLS, los controles de red y la observabilidad.
- Ensaye el cambio y la reversión antes de retirar el origen.

#### Migración por fases

Evalúe las dependencias → haga un piloto con una carga de trabajo representativa no crítica → realice la transición en oleadas controladas → acepte los datos/las operaciones y conserve evidencia de recuperación → retire el origen después del período de reversión acordado.

## Verificación posterior a la instalación

La verificación no debe reinstalar paquetes ni inicializar un host ya incorporado. Estas lecturas son solo observaciones; la actividad de procesos o una condición Ready antigua por sí sola no constituyen aceptación de cargas de trabajo.

```bash
# Read-only, on the host mapped to the intended Kubernetes Node:
set -euo pipefail
cat /etc/os-release
uname -m -r
/usr/local/bin/nodeadm --version
containerd --version
for service in containerd kubelet; do
  systemctl is-active --quiet "$service"
done
```

```bash
# From the approved administrative context; these are reads, not installation:
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved context}"
: "${NODE:?Set the actual registered Node name from inventory}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o yaml
```

Use la correspondencia entre Node y host del inventario, inspeccione un Lease reciente y su versión, confirme CNI/DNS/almacenamiento y ejecute las comprobaciones aprobadas de cargas de trabajo de las guías de [bootstrap](./04-node-bootstrap.md) y [ciclo de vida](./07-node-lifecycle.md). Las lecturas fallidas/desconocidas no son una aprobación.

## Solución de problemas

| Problema | Comprobaciones y siguiente paso acotado |
| --- | --- |
| Error de arranque | Modo de firmware, cargador firmado, diseño DHCP/HTTP/TFTP, controladores de NIC y sumas de comprobación de imágenes aprobadas |
| Error de Autoinstall/Kickstart | Registros/esquema del instalador, disco previsto, repositorio/stage2 y configuración específica del host; no vuelva a intentar a ciegas el particionado destructivo |
| Problema de terminación en Ubuntu | Evidencia real de denegación de señales de AppArmor, paquete/backport corregido y reinicio planificado requerido |
| containerd en RHEL | Seleccione la fuente compatible docker/none y verifique el runtime real y la política de SELinux |
| nodeadm/autenticación | Verifique que nodeadm esté actualizado, la configuración protegida, la conectividad privada con AWS, la identidad y la confianza; evite volver a registrar a ciegas |

## Alcance de la validación y referencias

La evidencia local incluye 50 comprobaciones de esquemas/contratos/dobles de comandos, doce casos de subprocesos de artefactos/hosts/lecturas de API, el analizador pykickstart 3.78 para RHEL 9 y diez aserciones de precios con Decimal. El esquema canónico de Autoinstall permite claves raíz adicionales y no reemplaza la validación con el instalador seleccionado. No se realizó ninguna instalación real de SO, borrado de disco, arranque/inicio de sesión, compilación de imagen Packer, operación SSH de Ansible, ejecución de nodeadm, creación de VM ni llamada a AWS/Kubernetes. Los destinos de prueba y ejecutables temporales eran sintéticos.

- [Requisitos de SO de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm de AWS Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Precios de AWS EKS](https://aws.amazon.com/eks/pricing/)
- [Ejemplo de Packer de AWS](https://github.com/aws/eks-hybrid/tree/main/example/packer)
- [Referencia de Autoinstall de Canonical](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [Referencia de Kickstart de RHEL 9](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/automatically_installing_rhel/kickstart-commands-and-options-reference_rhel-installer)
- [Error 2065423 de Ubuntu](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)
- [Manual de aa-remove-unknown](https://manpages.ubuntu.com/manpages/noble/man8/aa-remove-unknown.8.html)
- [AL2023 fuera de EC2](https://docs.aws.amazon.com/linux/al2023/ug/outside-ec2.html)
- [Operator Lifecycle Manager](https://olm.operatorframework.io/docs/)
- [API SCC de OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_apis/securitycontextconstraints-security-openshift-io-v1)


---

< [Anterior: Operaciones y mantenimiento](./08-operations.md) | [Tabla de contenido](./README.md) | [Siguiente: Gateway de Hybrid Nodes](./10-hybrid-nodes-gateway.md) >
