# Cuestionario de requisitos previos de EKS Hybrid Nodes

> **Documento relacionado**: [Requisitos previos](../../eks-hybrid-nodes/01-prerequisites.md)

## Preguntas de opción múltiple

### 1. ¿Cuál NO es un caso de uso adecuado para EKS Hybrid Nodes?

A. Utilizar servidores GPU en centros de datos on-premises
B. Requisitos de localidad de datos para cumplimiento normativo
C. Ejecutar workloads puramente cloud-native
D. Workloads de edge sensibles a la latencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Ejecutar workloads puramente cloud-native**

**Explicación:**
Los workloads puramente cloud-native se ejecutan de forma más eficiente en EKS node groups normales o en Fargate. Hybrid Nodes se usa cuando existen requisitos especiales (on-premises, edge, regulatorios, etc.).

**Casos de uso adecuados para EKS Hybrid Nodes:**
- Utilizar hardware GPU/especializado on-premises
- Requisitos de soberanía de datos/cumplimiento normativo
- Edge computing sensible a la latencia
- Período de transición de migración a la nube
- Proteger inversiones existentes en infraestructura

</details>

### 2. ¿Qué sistema operativo es compatible con EKS Hybrid Nodes?

A. Solo Windows Server 2019
B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9
C. macOS Ventura o posterior
D. FreeBSD 13 o posterior

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9**

**Explicación:**
EKS Hybrid Nodes solo admite sistemas operativos basados en Linux. Las versiones de OS compatibles incluyen:
- Ubuntu 20.04 LTS, 22.04 LTS
- Amazon Linux 2023
- Red Hat Enterprise Linux (RHEL) 8, 9
- Bottlerocket (container-optimized OS)

```bash
# Check OS version
cat /etc/os-release

# Check kernel version (5.4 or later recommended)
uname -r
```

</details>

### 3. ¿Cuál NO es un requisito mínimo para ejecutar workloads de GPU en Hybrid Nodes?

A. NVIDIA Driver 525 o posterior
B. CUDA Toolkit 11.8 o posterior
C. Mínimo 4GB de memoria GPU
D. La arquitectura x86_64 o arm64 es obligatoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. La arquitectura x86_64 o arm64 es obligatoria**

**Explicación:**
La arquitectura x86_64 o arm64 es un requisito de arquitectura de CPU, no un requisito directo para workloads de GPU. Los requisitos clave para workloads de GPU son:

- **NVIDIA Driver**: 525 o posterior (soporte para CUDA 12)
- **CUDA Toolkit**: 11.8 o posterior
- **Memoria GPU**: Mínimo 4GB recomendado (varía según el workload)
- **containerd**: 1.6 o posterior (soporte para contenedores GPU)

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader

# Check CUDA version
nvcc --version
```

</details>

### 4. ¿Cuáles son los requisitos mínimos de hardware para EKS Hybrid Nodes?

A. CPU de 1 núcleo, memoria de 512MB
B. CPU de 2 núcleos, memoria de 2GB
C. CPU de 4 núcleos, memoria de 8GB
D. CPU de 8 núcleos, memoria de 16GB

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. CPU de 2 núcleos, memoria de 2GB**

**Explicación:**
Los requisitos mínimos de hardware para EKS Hybrid Nodes son:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores or more |
| Memory | 2GB | 4GB or more |
| Disk | 20GB | 50GB or more (SSD recommended) |
| Network | 100Mbps | 1Gbps or more |

Los entornos de producción pueden requerir especificaciones más altas según los requisitos del workload.

</details>

### 5. ¿Cuál NO es un componente de software requerido para la configuración de EKS Hybrid Nodes?

A. containerd runtime
B. kubelet
C. Docker Engine
D. aws-iam-authenticator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Docker Engine**

**Explicación:**
EKS Hybrid Nodes usa containerd como container runtime, y Docker Engine no es necesario. Los componentes requeridos son:

- **containerd**: Container runtime (1.6 o posterior)
- **kubelet**: Agente de Kubernetes node
- **aws-iam-authenticator**: Autenticación de AWS IAM
- **CNI plugins**: Redes de contenedores

```bash
# nodeadm automatically installs components
sudo nodeadm init --config-source file://nodeadm-config.yaml

# Check installed components
systemctl status containerd
systemctl status kubelet
```

</details>

### 6. ¿Cuál es la versión mínima de NVIDIA driver requerida para usar GPU H100 con Hybrid Nodes?

A. 450.x
B. 470.x
C. 525.x
D. 535.x

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. 535.x**

**Explicación:**
La GPU NVIDIA H100 usa arquitectura Hopper y requiere los drivers más recientes:

| GPU Model | Minimum Driver Version | Recommended Driver Version |
|-----------|----------------------|---------------------------|
| A100 | 450.x | 525.x or later |
| H100 | 525.x | 535.x or later |
| H200 | 535.x | 545.x or later |

```bash
# Verify H100 driver installation
nvidia-smi

# Update driver
sudo apt-get update
sudo apt-get install nvidia-driver-535
```

Se recomienda la versión de driver 535.x o posterior para aprovechar por completo las características clave de H100 (expansión MIG, Transformer Engine, etc.).

</details>
