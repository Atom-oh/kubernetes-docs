# Guía de instalación de OS en servidores bare metal y migración

< [Anterior: Operaciones y mantenimiento](./08-operations.md) | [Tabla de contenidos](./README.md) | [Siguiente: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

> **Versiones compatibles**: EKS 1.31+, nodeadm 0.1+
> **Última actualización**: February 23, 2026

Este documento cubre los métodos de instalación de OS para desplegar EKS Hybrid Nodes en servidores bare metal y las estrategias de migración desde VMware/OpenShift.

## Descripción general

### Por qué elegir bare metal

Ejecutar EKS Hybrid Nodes en servidores bare metal ofrece los siguientes beneficios:

1. **Ahorro en costos de licencias de VMware**: Después de la adquisición de VMware por parte de Broadcom, la transición a un modelo de suscripción aumentó significativamente los costos de licenciamiento.
2. **Reducción de costos de suscripción de OpenShift**: Elimine las tarifas de suscripción de Red Hat OpenShift por nodo.
3. **Eliminación de la sobrecarga del hipervisor**: Ejecute cargas de trabajo directamente sin una capa de virtualización para optimizar el rendimiento.
4. **Simplificación de la gestión de licencias**: Reduzca la carga de los acuerdos de licencia complejos y del cumplimiento de auditorías.

### Matriz de compatibilidad de infraestructura de OS

| OS | Bare Metal | VMware | Credenciales | Herramienta de configuración |
|----|-----------|--------|-------------|-------------|
| Ubuntu 22.04/24.04 LTS | O | O | SSM / IAM RA | nodeadm (YAML) |
| RHEL 8/9 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Amazon Linux 2023 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Bottlerocket v1.37.0+ | X | O (solo VMware) | SSM / IAM RA | govc (TOML) |

> **Nota**: Bottlerocket solo es compatible en entornos VMware. Para servidores bare metal, use Ubuntu, RHEL o Amazon Linux 2023.

## Análisis comparativo de costos

### Comparación de costos de licencia/suscripción

#### VMware vSphere
Después de la adquisición por Broadcom, VMware pasó de licencias perpetuas a un modelo de suscripción:
- Licencia Enterprise Plus: Aproximadamente $4,500-8,500 por socket de CPU al año
- Componentes adicionales como vSAN y NSX-T generan costos separados

#### OpenShift
Basado en suscripción de Red Hat:
- Aproximadamente $2,500-5,000 por nodo al año (suscripción basada en cores)
- Incluye soporte premium

#### EKS Hybrid Nodes
- $0.01 por vCPU por hora (varía según la región)
- No se requiere licenciamiento adicional

### Comparación de costos anuales por escala (servidores de 32 vCPU)

| Escala | VMware vSphere (Anual) | OpenShift (Anual) | EKS Hybrid Nodes (Anual) |
|-------|------------------------|-------------------|--------------------------|
| 10 nodos | ~$45,000-85,000 | ~$25,000-50,000 | ~$28,032 |
| 50 nodos | ~$225,000-425,000 | ~$125,000-250,000 | ~$140,160 |
| 100 nodos | ~$450,000-850,000 | ~$250,000-500,000 | ~$280,320 |

> **Cálculo**: EKS Hybrid Nodes = 32 vCPU × $0.01/hora × 8,760 horas = $2,803.20/nodo/año
>
> **Nota**: Los costos anteriores son estimaciones. Los costos reales pueden variar según los términos del contrato, la región y los descuentos.

### Consideraciones de TCO (Total Cost of Ownership)

Además de los costos de licencia/suscripción, considere los siguientes factores:
- Costos de capacitación del personal de operaciones
- Sobrecarga de gestión de licencias y cumplimiento de auditorías
- Costos de soporte técnico y consultoría
- Costos de migración (una sola vez)

## Instalación bare metal específica por OS

### Requisitos previos

#### Configuración de BIOS/UEFI
- Configure la prioridad de arranque PXE
- Deshabilite Secure Boot o use bootloaders firmados
- Habilite las extensiones de virtualización (VT-x/AMD-V) para containerd

#### Infraestructura de red
- Servidor DHCP: Proporciona direcciones IP e información de arranque PXE
- Servidor TFTP: Sirve imágenes de bootloader y kernel
- Servidor HTTP: Aloja imágenes de instalación del OS y archivos de configuración

#### Plantillas de AWS Packer
Al crear imágenes para bare metal, establezca la variable de entorno `CREDENTIAL_PROVIDER`:

```bash
# Create Qcow2 or Raw format images
export CREDENTIAL_PROVIDER=ssm  # or iam-ra

packer build \
  -var "credential_provider=${CREDENTIAL_PROVIDER}" \
  -var "output_format=raw" \
  bare-metal-template.pkr.hcl
```

### Ubuntu LTS (22.04/24.04)

Ubuntu usa Autoinstall (basado en cloud-init) para la instalación automatizada por PXE.

#### Ejemplo de configuración de Autoinstall

```yaml
#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  network:
    ethernets:
      ens0:
        dhcp4: true
    version: 2
  storage:
    layout:
      name: lvm
  identity:
    hostname: hybrid-node
    username: ubuntu
    password: "$6$rounds=4096$..."  # Encrypted password
  ssh:
    install-server: true
    authorized-keys:
      - ssh-rsa AAAA...  # SSH public key
  packages:
    - curl
    - jq
    - open-iscsi
    - nfs-common
  late-commands:
    - curtin in-target -- bash -c 'curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm && chmod +x nodeadm && mv nodeadm /usr/local/bin/'
```

#### Notas específicas de Ubuntu 24.04

Ubuntu 24.04 requiere containerd v1.7.19 o posterior, o se necesitan cambios en el perfil de AppArmor (bug de Ubuntu #2065423):

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

> **Importante**: Se requiere reiniciar después de los cambios de AppArmor. Sin reiniciar, es posible que los Pods no finalicen correctamente.

### RHEL 9

RHEL usa Kickstart para la instalación automatizada por PXE.

#### Ejemplo de configuración de Kickstart

```bash
# ks.cfg
lang en_US.UTF-8
keyboard us
timezone America/New_York --utc
rootpw --iscrypted $6$rounds=4096$...
network --bootproto=dhcp --device=ens0 --activate
autopart --type=lvm
clearpart --all --initlabel

%packages
@core
curl
jq
container-tools
%end

%post
# Install nodeadm
curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm && mv nodeadm /usr/local/bin/

# SELinux configuration (if needed)
semanage permissive -a container_t
%end
```

#### Notas de instalación de containerd en RHEL

En RHEL, debe usar la opción `--containerd-source docker`. La fuente predeterminada de la distribución no es compatible:

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker

# Incorrect installation method (will fail)
# sudo nodeadm install 1.31 --credential-provider ssm
```

#### Entornos a gran escala: integración con Satellite/Foreman

Para despliegues de RHEL a gran escala, use Red Hat Satellite o Foreman para:
- Gestión centralizada de plantillas de Kickstart
- Replicación de repositorios de paquetes
- Automatización del flujo de trabajo de provisioning

### Amazon Linux 2023

Amazon Linux 2023 usa configuración basada en cloud-init.

```yaml
#cloud-config
hostname: hybrid-node
users:
  - name: ec2-user
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-rsa AAAA...

packages:
  - curl
  - jq

runcmd:
  - curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
  - chmod +x nodeadm && mv nodeadm /usr/local/bin/
```

> **Nota de AWS Support**: Al ejecutar Amazon Linux 2023 fuera de EC2 (en bare metal), los AWS Support Plans no aplican. Solo está disponible el soporte de la comunidad.

### Bottlerocket en VMware (referencia)

Bottlerocket solo es compatible en entornos VMware (v1.37.0+, solo x86_64).

- Usa `settings.toml` en lugar de nodeadm para la configuración
- Flujo de trabajo de despliegue con govc: clonar plantilla → inyectar user-data → encender

Para una configuración TOML detallada de Bottlerocket, consulte [04-node-bootstrap.md](./04-node-bootstrap.md).

## Comparación de configuración de Credential Provider

### Configuración basada en nodeadm (Ubuntu/RHEL/AL2023)

```yaml
# nodeconfig.yaml - SSM method
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
```

```yaml
# nodeconfig.yaml - IAM Roles Anywhere method
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:us-west-2:111122223333:trust-anchor/...
      profileArn: arn:aws:rolesanywhere:us-west-2:111122223333:profile/...
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

### Configuración basada en Bottlerocket (VMware)

```toml
# settings.toml - SSM method
[settings.hybrid.ssm]
activation-code = "<activation-code>"
activation-id = "<activation-id>"

[settings.kubernetes]
cluster-name = "my-cluster"
```

```toml
# settings.toml - IAM Roles Anywhere method
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "arn:aws:rolesanywhere:..."
profile-arn = "arn:aws:rolesanywhere:..."
role-arn = "arn:aws:iam::..."
certificate-path = "/etc/eks/pki/node.crt"
private-key-path = "/etc/eks/pki/node.key"
```

### Guía de selección de Credential Provider

| Condición | Proveedor recomendado |
|-----------|---------------------|
| Sin infraestructura PKI | SSM |
| Infraestructura PKI existente | IAM Roles Anywhere |
| Se necesitan nombres de nodo personalizados | IAM Roles Anywhere |
| Entorno air-gapped | IAM Roles Anywhere |
| Configuración simple, internet disponible | SSM |

## Automatización de provisioning a gran escala

### Configuración de infraestructura de PXE Boot

```
┌─────────────────────────────────────────────────────────┐
│                    PXE Boot Server                       │
├─────────────────────────────────────────────────────────┤
│  DHCP Server                                            │
│  ├── IP address allocation                              │
│  ├── next-server: TFTP server address                   │
│  └── filename: pxelinux.0                              │
├─────────────────────────────────────────────────────────┤
│  TFTP Server                                            │
│  ├── pxelinux.0 (bootloader)                           │
│  ├── vmlinuz (kernel)                                   │
│  └── initrd.img (initial RAM disk)                     │
├─────────────────────────────────────────────────────────┤
│  HTTP Server                                            │
│  ├── OS installation images                             │
│  ├── Autoinstall/Kickstart config files                │
│  └── nodeadm binary                                     │
└─────────────────────────────────────────────────────────┘
```

### Ansible Automation Playbook

```yaml
# provision-hybrid-nodes.yaml
---
- hosts: hybrid_nodes
  become: true
  vars:
    k8s_version: "1.31"
    cred_provider: "ssm"
    cluster_name: "my-cluster"
    region: "us-west-2"

  tasks:
    - name: Download nodeadm
      get_url:
        url: https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
        dest: /usr/local/bin/nodeadm
        mode: '0755'

    - name: Install EKS components
      command: >
        nodeadm install {{ k8s_version }}
        --credential-provider {{ cred_provider }}
        {% if ansible_distribution == 'RedHat' %}--containerd-source docker{% endif %}
      args:
        creates: /usr/bin/kubelet

    - name: Deploy node configuration
      template:
        src: nodeconfig.yaml.j2
        dest: /etc/eks/nodeconfig.yaml
        mode: '0600'

    - name: Initialize node
      command: nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
      register: init_result
      changed_when: init_result.rc == 0
```

Para obtener información detallada sobre la gestión de fleets, consulte [07-node-lifecycle.md](./07-node-lifecycle.md).

## Estrategias de migración

### VMware → Bare Metal + EKS Hybrid Nodes

#### Fase 1: Crear infraestructura paralela
- Despliegue el cluster EKS y la infraestructura de hybrid nodes junto con VMware
- Configure la conectividad de red (Direct Connect/VPN)
- Bottlerocket en VMware puede coexistir durante el período de transición

#### Fase 2: Containerizar cargas de trabajo
- Migre cargas de trabajo basadas en VM a containers
- Configure drivers CSI antes de migrar cargas de trabajo stateful
- Considere migrar bases de datos a servicios administrados de AWS

#### Fase 3: Transición de red
- Transición de NSX-T a Cilium BGP
- Migre las configuraciones de load balancer e ingress
- Actualice registros DNS

#### Fase 4: Retirar VMware
- Verifique que todas las cargas de trabajo se hayan migrado
- Termine las licencias de VMware
- Recicle o retire el hardware

### OpenShift → EKS Hybrid Nodes

#### Mapeo de conceptos

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC (Security Context Constraints) | PSS (Pod Security Standards) |
| OLM (Operator Lifecycle Manager) | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | CI/CD externo (CodeBuild, GitHub Actions) |
| DeploymentConfig | Deployment (Kubernetes estándar) |

#### Checklist de migración de cargas de trabajo

- [ ] Convertir Routes a Ingress o Gateway API
- [ ] Mapear SCCs a PSS para la configuración de seguridad de Pods
- [ ] Reemplazar Operators gestionados por OLM con Helm Charts o EKS Add-ons
- [ ] Cambiar referencias de ImageStream a URLs de imágenes de ECR
- [ ] Reconfigurar BuildConfigs como pipelines de GitHub Actions/CodeBuild
- [ ] Convertir DeploymentConfigs a Deployments estándar
- [ ] Revisar service accounts y configuraciones de RBAC

#### Migración por fases

1. **Fase de evaluación**: Cree un inventario de las cargas de trabajo actuales de OpenShift
2. **Fase piloto**: Migre cargas de trabajo no críticas a EKS Hybrid Nodes
3. **Fase de transición**: Migre secuencialmente las cargas de trabajo críticas
4. **Fase de finalización**: Retire el cluster OpenShift

## Verificación posterior a la instalación

```bash
#!/bin/bash
# verify-bare-metal.sh

echo "=== OS Level Verification ==="
# Check OS version
cat /etc/os-release

# Check kernel version
uname -r

# Check containerd status
systemctl status containerd

# Check nodeadm version
nodeadm version

echo "=== EKS Integration Verification ==="
# Install and initialize
sudo nodeadm install 1.31 --credential-provider ssm
sudo nodeadm init --config-source file://nodeconfig.yaml

# Verify node from cluster
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid

# Check node details
kubectl describe node <node-name> | grep -A 5 "Labels:"
```

Para obtener información detallada sobre el proceso de bootstrap, consulte [04-node-bootstrap.md](./04-node-bootstrap.md).

## Solución de problemas

| Problema | Síntoma | Solución |
|-------|---------|----------|
| Falla de PXE boot | El nodo no arranca desde la red | Verifique la configuración DHCP/TFTP, el orden de arranque del BIOS, el cable de red |
| Timeout de Autoinstall | La instalación de Ubuntu se cuelga | Verifique la sintaxis YAML de cloud-init, revise la accesibilidad del servidor HTTP |
| Error de Kickstart | La instalación de RHEL falla | Valide la sintaxis de ks.cfg, revise la accesibilidad del medio |
| containerd en Ubuntu 24.04 | Los Pods no finalizan | Actualice containerd a v1.7.19+, reinicie para AppArmor |
| containerd en RHEL | La instalación falla | Use el flag `--containerd-source docker` |
| nodeadm init falla | Timeout de conexión | Verifique la conectividad VPN/DX, revise los puertos del firewall |

---

< [Anterior: Operaciones y mantenimiento](./08-operations.md) | [Tabla de contenidos](./README.md) | [Siguiente: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >
