# Cuestionario sobre instalación de OS y migración de servidores bare metal

> **Documento relacionado**: [Guía de instalación de OS y migración de servidores bare metal](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es un beneficio clave de ejecutar EKS Hybrid Nodes en servidores bare metal?

A. Velocidades de red más rápidas que las instancias AWS EC2
B. Ahorro en costos de licencias de VMware y eliminación de la sobrecarga del hypervisor
C. Capacidad de usar Bottlerocket OS
D. Cobertura de AWS Support Plans

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ahorro en costos de licencias de VMware y eliminación de la sobrecarga del hypervisor**

**Explicación:**
Ejecutar EKS Hybrid Nodes en servidores bare metal te permite ahorrar en costos de licencias de VMware (que pasaron a un modelo de suscripción después de la adquisición de Broadcom) y en tarifas de suscripción de OpenShift. Además, eliminar la capa de hypervisor optimiza el rendimiento.

</details>

### 2. ¿Cuáles son los componentes esenciales requeridos para la infraestructura de arranque PXE?

A. Servidor DNS y servidor NFS
B. Servidor DHCP y servidor TFTP
C. Servidor FTP y servidor SMTP
D. Servidor LDAP y servidor Kerberos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Servidor DHCP y servidor TFTP**

**Explicación:**
Los componentes principales de la infraestructura de arranque PXE son:
- Servidor DHCP: proporciona asignación de direcciones IP e información de arranque PXE (next-server, filename)
- Servidor TFTP: sirve el bootloader (pxelinux.0), el kernel (vmlinuz) y el disco RAM inicial (initrd.img)
- Servidor HTTP (opcional): aloja imágenes de instalación de OS y archivos de configuración

</details>

### 3. ¿Cuál empareja correctamente el método de instalación automatizada de Ubuntu con el método de instalación automatizada de RHEL?

A. Ubuntu: Kickstart, RHEL: Autoinstall
B. Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart
C. Ubuntu: Preseed, RHEL: Anaconda
D. Ubuntu: YAML, RHEL: JSON

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart**

**Explicación:**
- Ubuntu usa Autoinstall (basado en cloud-init) para la instalación automatizada por PXE. Usa archivos de configuración en formato YAML.
- RHEL usa Kickstart para la instalación automatizada por PXE. La configuración se realiza mediante archivos ks.cfg.

</details>

### 4. Según la matriz de soporte de infraestructura de OS, ¿cuál es el entorno compatible con Bottlerocket?

A. Compatible tanto con bare metal como con VMware
B. Solo bare metal
C. Solo VMware
D. Solo AWS EC2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Solo VMware**

**Explicación:**
Bottlerocket solo es compatible con entornos VMware para EKS Hybrid Nodes (v1.37.0+, solo x86_64). Para servidores bare metal, debes usar Ubuntu, RHEL o Amazon Linux 2023. Bottlerocket no usa nodeadm; usa settings.toml para la configuración.

</details>

### 5. ¿Qué herramienta y formato de configuración usa Bottlerocket de forma diferente a otros sistemas operativos?

A. nodeadm (YAML)
B. ansible (INI)
C. govc (TOML)
D. terraform (HCL)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) govc (TOML)**

**Explicación:**
Bottlerocket no usa nodeadm; en su lugar, usa archivos settings.toml para la configuración. El flujo de trabajo de despliegue con govc es: clonar plantilla → inyectar user-data → encender. En contraste, Ubuntu, RHEL y Amazon Linux 2023 usan nodeadm (YAML).

</details>

### 6. Al seleccionar un proveedor de credenciales para un entorno sin infraestructura PKI y con conectividad a internet, ¿qué opción se recomienda?

A. IAM Roles Anywhere
B. SSM Hybrid Activations
C. Kubernetes Service Account
D. OIDC Provider

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) SSM Hybrid Activations**

**Explicación:**
Guía de selección del proveedor de credenciales:
- Sin infraestructura PKI, internet disponible: SSM
- Infraestructura PKI existente: IAM Roles Anywhere
- Entorno aislado (air-gapped): IAM Roles Anywhere
- Se necesitan nombres de nodos personalizados: IAM Roles Anywhere

SSM se recomienda para la mayoría de los entornos debido a su configuración simple y a que no requiere certificados.

</details>

### 7. ¿Qué opción debe usarse al instalar containerd con nodeadm en RHEL?

A. `--containerd-source distro`
B. `--containerd-source docker`
C. `--containerd-source eks`
D. `--containerd-version latest`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `--containerd-source docker`**

**Explicación:**
En RHEL, debes usar la opción `--containerd-source docker`. La fuente predeterminada de la distribución (distro) no es compatible con RHEL:

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker
```

La instalación fallará sin esta opción.

</details>

### 8. ¿Cuál es el orden correcto de las fases al migrar de VMware a bare metal + EKS Hybrid Nodes?

A. Retirar VMware → Containerizar cargas de trabajo → Transición de red → Construir infraestructura paralela
B. Containerizar cargas de trabajo → Construir infraestructura paralela → Retirar VMware → Transición de red
C. Construir infraestructura paralela → Containerizar cargas de trabajo → Transición de red → Retirar VMware
D. Transición de red → Construir infraestructura paralela → Containerizar cargas de trabajo → Retirar VMware

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Construir infraestructura paralela → Containerizar cargas de trabajo → Transición de red → Retirar VMware**

**Explicación:**
Fases de migración de VMware → Bare Metal + EKS Hybrid Nodes:
1. Fase 1: Construir infraestructura paralela (desplegar el cluster EKS y la infraestructura de nodos híbridos junto a VMware)
2. Fase 2: Containerizar cargas de trabajo (migrar cargas de trabajo basadas en VM a containers)
3. Fase 3: Transición de red (transición de NSX-T a Cilium BGP)
4. Fase 4: Retirar VMware (después de verificar que todas las cargas de trabajo se hayan migrado)

</details>

### 9. ¿A qué corresponde el concepto Route de OpenShift en EKS Hybrid Nodes?

A. Service
B. Ingress / Gateway API
C. NetworkPolicy
D. Endpoint

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ingress / Gateway API**

**Explicación:**
Mapeo de conceptos al migrar de OpenShift a EKS Hybrid Nodes:

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC | PSS (Pod Security Standards) |
| OLM | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD |
| DeploymentConfig | Deployment |

</details>

### 10. ¿Cuál es la solución cuando los Pods no terminan en Ubuntu 24.04 debido a problemas de containerd?

A. Deshabilitar SELinux y reiniciar
B. Actualizar containerd a v1.7.19+ o modificar el perfil de AppArmor y reiniciar
C. Cambiar el container runtime a Docker
D. Hacer downgrade a cgroup v1

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actualizar containerd a v1.7.19+ o modificar el perfil de AppArmor y reiniciar**

**Explicación:**
Ubuntu 24.04 requiere containerd v1.7.19 o posterior, o se necesitan cambios en el perfil de AppArmor (bug de Ubuntu #2065423):

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

Sin reiniciar, es posible que los Pods no terminen correctamente.

</details>
