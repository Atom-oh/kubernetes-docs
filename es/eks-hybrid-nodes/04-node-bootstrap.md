# Bootstrap de Node

< [Anterior: Configuración Air-Gap](./03-airgap-setup.md) | [Tabla de contenidos](./README.md) | [Siguiente: Integración de GPU](./05-gpu-integration.md) >

> **Versiones compatibles**: EKS 1.31+, nodeadm 0.1+
> **Última actualización**: February 23, 2026

Este documento cubre el proceso de bootstrap de servidores on-premises como EKS Hybrid Nodes usando nodeadm.

## Descripción general del workflow de bootstrap

Los siguientes pasos describen el proceso completo de bootstrap de Node, desde la configuración de credenciales IAM hasta un Hybrid Node completamente listo.

### Pasos de bootstrap

1. **Preparar credenciales IAM** — Crear una SSM Hybrid Activation o configurar IAM Roles Anywhere
2. **Descargar nodeadm** — Descargar el binario CLI para tu arquitectura
3. **Ejecutar `nodeadm install`** — Instalar componentes de Kubernetes y dependencias
4. **Escribir NodeConfig YAML** — Configurar detalles del cluster, credenciales, kubelet y containerd
5. **Instalar certificados CA** — Agregar certificados CA de registry privado al almacén de confianza del sistema (si se usa un registry privado)
6. **Ejecutar `nodeadm init`** — Inicializar el Node y registrarlo con el cluster EKS
7. **Instalar CNI** — Desplegar Cilium mediante Helm para networking de Pods
8. **Verificar el registro** — Confirmar que el Node aparece como `Ready` en `kubectl get nodes`

## Descarga e instalación de nodeadm CLI

nodeadm es la herramienta CLI para inicializar y administrar EKS Hybrid Nodes.

### Paso 1: Descargar nodeadm

```bash
# Download nodeadm (Linux x86_64)
curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# For ARM64 architecture:
# curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/arm64/nodeadm

# Check version
nodeadm version
```

### Paso 2: Ejecutar `nodeadm install`

El comando `nodeadm install` instala componentes de Kubernetes (kubelet, kubectl, etc.) y dependencias del sistema. Debe ejecutarse antes de `nodeadm init`.

```bash
# Install with SSM credential provider
sudo nodeadm install 1.31 --credential-provider ssm

# Install with IAM Roles Anywhere credential provider
sudo nodeadm install 1.31 --credential-provider iam-ra

# Custom timeout for slow networks
sudo nodeadm install 1.31 --credential-provider ssm --timeout 20m0s
```

> **Nota**: Reemplaza `1.31` por tu versión objetivo de Kubernetes. La versión debe coincidir con la versión de tu cluster EKS.

### Rutas de archivos de instalación

| Componente | Ruta en Ubuntu/AL2023 | Ruta en RHEL |
|-----------|-------------------|-----------|
| kubelet | /usr/bin/kubelet | /usr/bin/kubelet |
| kubectl | /usr/bin/kubectl | /usr/bin/kubectl |
| SSM Agent | /snap/amazon-ssm-agent (Ubuntu) / systemd (AL2023) | /usr/bin/amazon-ssm-agent |
| containerd | /usr/bin/containerd | /usr/bin/containerd |
| nodeadm | /usr/local/bin/nodeadm | /usr/local/bin/nodeadm |

## Escritura de NodeConfig YAML

```yaml
# nodeconfig.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXXXXXXXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      -----BEGIN CERTIFICATE-----
      MIIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      -----END CERTIFICATE-----
    cidr: 10.100.0.0/16  # Service CIDR

  # Credential method selection (SSM or IAM Roles Anywhere)
  hybrid:
    # Method 1: SSM Hybrid Activations
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

    # Method 2: IAM Roles Anywhere (uncomment to use)
    # iamRolesAnywhere:
    #   nodeName: hybrid-node-001  # Must match certificate CN
    #   trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
    #   profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
    #   roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
    #   certificatePath: /etc/iam/pki/server.pem
    #   privateKeyPath: /etc/iam/pki/server.key

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu
      - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        config_path = "/etc/containerd/certs.d"

      # Private registry TLS configuration (uncomment and adjust for your registry)
      # [plugins."io.containerd.grpc.v1.cri".registry.configs."registry.internal.company.io".tls]
      #   ca_file = "/etc/ssl/certs/registry-ca.crt"
      # [plugins."io.containerd.grpc.v1.cri".registry.configs."registry.internal.company.io".auth]
      #   username = "pull-robot"
      #   password = "<token>"
```

## Crear una SSM Hybrid Activation

```bash
# Create SSM Hybrid Activation
aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" \
  --registration-limit 100 \
  --region ap-northeast-2 \
  --tags "Key=Environment,Value=Production" "Key=NodeType,Value=Hybrid"

# Enter the output ActivationCode and ActivationId in nodeconfig.yaml
```

## Configuración de IAM Roles Anywhere (alternativa)

Si usas IAM Roles Anywhere en lugar de SSM, configura el trust anchor, el profile y los certificados:

```bash
# Create Trust Anchor
TRUST_ANCHOR_ARN=$(aws rolesanywhere create-trust-anchor \
  --name "eks-hybrid-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat ca.pem)}" \
  --enabled \
  --query 'trustAnchor.trustAnchorArn' --output text)

# Create Profile
PROFILE_ARN=$(aws rolesanywhere create-profile \
  --name "eks-hybrid-profile" \
  --role-arns arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --enabled \
  --query 'profile.profileArn' --output text)

echo "Trust Anchor ARN: $TRUST_ANCHOR_ARN"
echo "Profile ARN: $PROFILE_ARN"
# Enter these values in nodeconfig.yaml under spec.hybrid.iamRolesAnywhere
```

NodeConfig YAML para IAM Roles Anywhere:

```yaml
spec:
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001  # Must match certificate CN
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

> **Nota**: Cuando uses IAM Roles Anywhere, habilita `acceptRoleSessionName` en el profile de IAM RA y establece `MaxSessionDuration` en el role IAM en al menos 1 hora (recomendado: 12 horas) para evitar refrescos frecuentes de credenciales.

## Instalar certificado CA en el sistema (registry privado)

Si usas un container registry privado con un certificado CA autofirmado o interno, instala el certificado CA en cada Node:

```bash
# Install CA certificate on system (Ubuntu)
sudo cp ca.crt /usr/local/share/ca-certificates/registry-ca.crt
sudo update-ca-certificates

# RHEL/CentOS
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/registry-ca.crt
sudo update-ca-trust extract

# Configure directory for containerd to find certificate
sudo mkdir -p /etc/containerd/certs.d/<REGISTRY_HOST>
cat <<EOF | sudo tee /etc/containerd/certs.d/<REGISTRY_HOST>/hosts.toml
server = "https://<REGISTRY_HOST>"

[host."https://<REGISTRY_HOST>"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
EOF
```

## Inicialización del Node

### Validación de la configuración

Se recomienda validar el archivo de configuración antes de inicializar el Node:

```bash
# Validate configuration (recommended before node initialization)
nodeadm config check --config-source file://nodeconfig.yaml
```

### Ejecutar la inicialización

```bash
# Initialize node using nodeadm
sudo nodeadm init -c file://nodeconfig.yaml

# Check initialization logs
sudo journalctl -u kubelet -f

# Check node status (from EKS cluster)
kubectl get nodes -o wide
```

## Verificar el registro del Node

```bash
# Check node list
kubectl get nodes --show-labels

# Expected output:
# NAME                STATUS   ROLES    AGE   VERSION   LABELS
# ip-10-0-1-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2a
# ip-10-0-2-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2b
# hybrid-node-001     Ready    <none>   5m    v1.31.0   eks.amazonaws.com/compute-type=hybrid

# Check node details
kubectl describe node hybrid-node-001

# Filter Hybrid Nodes
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid
```

---

## Bootstrap automatizado con systemd

Para despliegues a gran escala, puedes configurar un service de systemd para ejecutar automáticamente `nodeadm install` y `nodeadm init` cuando un Node arranca. Los archivos marcadores garantizan que la instalación solo se ejecute en el primer arranque y se omita en los arranques posteriores.

### Prerrequisitos

Los siguientes archivos deben estar ubicados previamente en el Node antes del bootstrap automático:

- `/etc/eks/nodeconfig.yaml` — Archivo de configuración NodeConfig
- `/etc/eks/bootstrap.env` — Variables de entorno de bootstrap
- `/usr/local/bin/nodeadm` — Binario nodeadm

> **Nota**: Estos archivos se pueden colocar previamente mediante builds de imágenes de VM (Packer, etc.), cloud-init o herramientas de administración de configuración (Ansible, etc.).

### Archivo de configuración de entorno

```bash
# /etc/eks/bootstrap.env
K8S_VERSION="1.31"
CREDENTIAL_PROVIDER="ssm"          # ssm or iam-ra
NODECONFIG_PATH="/etc/eks/nodeconfig.yaml"
```

### Script de bootstrap

```bash
#!/bin/bash
# /usr/local/bin/eks-hybrid-bootstrap.sh
set -euo pipefail

LOG_TAG="eks-hybrid-bootstrap"
MARKER_DIR="/var/lib/eks"
INSTALL_MARKER="${MARKER_DIR}/.nodeadm-installed"
INIT_MARKER="${MARKER_DIR}/.nodeadm-initialized"

# Load environment variables
source /etc/eks/bootstrap.env

log() { logger -t "$LOG_TAG" "$1"; echo "[$(date '+%H:%M:%S')] $1"; }

mkdir -p "$MARKER_DIR"

# --- install phase (first boot only) ---
if [ -f "$INSTALL_MARKER" ]; then
  log "nodeadm install already completed — skipping"
else
  log "Starting nodeadm install ${K8S_VERSION} (credential-provider: ${CREDENTIAL_PROVIDER})"
  nodeadm install "${K8S_VERSION}" --credential-provider "${CREDENTIAL_PROVIDER}"
  touch "$INSTALL_MARKER"
  log "nodeadm install completed"
fi

# --- init phase (first boot only) ---
if [ -f "$INIT_MARKER" ]; then
  log "nodeadm init already completed — skipping"
else
  log "Starting nodeadm init"
  nodeadm init -c "file://${NODECONFIG_PATH}"
  touch "$INIT_MARKER"
  log "nodeadm init completed — node registered with EKS cluster"
fi
```

```bash
sudo chmod +x /usr/local/bin/eks-hybrid-bootstrap.sh
```

### Unidad de service systemd

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=EKS Hybrid Node Bootstrap (install + init)
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/eks/.nodeadm-initialized

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> **ConditionPathExists**: El prefijo `!` significa que el service solo se ejecuta cuando el archivo **no existe**. Una vez que init se completa y crea el archivo marcador, el service se omite automáticamente en los arranques posteriores.

### Habilitar el service

```bash
sudo systemctl daemon-reload
sudo systemctl enable eks-hybrid-bootstrap.service
```

### Verificar la operación

```bash
# Check service status
sudo systemctl status eks-hybrid-bootstrap.service

# View bootstrap logs
sudo journalctl -u eks-hybrid-bootstrap.service

# Check marker files
ls -la /var/lib/eks/.nodeadm-*
```

### Reinstalación

Para empezar de cero, elimina los archivos marcadores y reinicia:

```bash
# Clean up existing state
sudo nodeadm uninstall
sudo rm -f /var/lib/eks/.nodeadm-installed /var/lib/eks/.nodeadm-initialized

# Reboot triggers automatic install + init
sudo reboot
```

### Preguntas frecuentes

**P: ¿Qué significa cada configuración en el archivo de unidad systemd?**

| Configuración | Significado |
|---------|---------|
| `Type=oneshot` | Se ejecuta una vez durante el boot y sale |
| `After=network-online.target` | Se ejecuta solo después de que la red esté completamente lista |
| `ConditionPathExists=!/var/lib/eks/.nodeadm-initialized` | Prefijo `!` — se ejecuta solo cuando el archivo marcador **no existe** |
| `RemainAfterExit=true` | El service permanece en estado activo después de que el proceso termina (permite verificaciones de estado) |
| `WantedBy=multi-user.target` | Se inicia automáticamente durante el boot normal |

**P: ¿Necesito un nuevo código de activación SSM cada vez que se reinicia el Node?**

No. La SSM Hybrid Activation `activationCode`/`activationId` se usa solo una vez durante `nodeadm init` para registrar el SSM agent con AWS. Después del registro, el SSM agent renueva sus propias credenciales automáticamente, por lo que **los códigos de activación no son necesarios en reinicios normales**.

Sin embargo, si ejecutas `nodeadm uninstall`, los artefactos de SSM se eliminan y se requiere volver a registrarse. Puedes reutilizar el mismo código de activación si no se ha alcanzado el `registration-limit`.

**P: ¿`nodeadm init` une el Node al cluster?**

Sí. `nodeadm init` realiza los siguientes pasos en orden:
1. Genera archivos de configuración de kubelet (`/etc/kubernetes/`)
2. Registra credenciales de SSM o IAM Roles Anywhere
3. Inicia el service systemd de kubelet
4. kubelet registra (une) el Node con el API server de EKS

En otras palabras, `nodeadm init` es el **comando real para unir al cluster**.

**P: ¿El registro de activación SSM ocurre durante `install` o `init`?**

| Fase | Acción relacionada con SSM |
|-------|-------------------|
| `nodeadm install --credential-provider ssm` | Instala **solo el binario** de SSM Agent |
| `nodeadm init` | **Registra** el SSM Agent con AWS usando `activationCode`/`activationId` de nodeconfig.yaml |

La activación SSM (registro) ocurre durante la **fase init**.

**P: ¿Cómo elimino y vuelvo a registrar un Node conservando la activación SSM?**

`kubectl delete node <NODE_NAME>` no afecta el registro SSM (SSM opera a nivel de OS; el registro del Node está a nivel de Kubernetes). Si kubelet todavía se está ejecutando, el Node se volverá a registrar automáticamente:

```bash
# Remove node from cluster
kubectl delete node hybrid-node-001

# If kubelet is running, it auto-registers
# If stopped, restart manually
sudo systemctl restart kubelet
```

**P: Después de `drain → delete → shutdown`, ¿el Node se volverá a registrar automáticamente en el reinicio mediante systemd?**

El Node se volverá a registrar, pero lo gestiona el **service kubelet en sí**, no el service de bootstrap systemd:

1. `nodeadm init` instala kubelet como un service systemd
2. En el reinicio, kubelet se inicia automáticamente y se vuelve a registrar con el API server
3. El service de bootstrap se omite porque el archivo marcador existe (este es el comportamiento esperado)

```bash
# No need to delete marker files in this workflow
kubectl drain hybrid-node-001 --ignore-daemonsets --delete-emptydir-data
kubectl delete node hybrid-node-001
# Shutdown and reboot → kubelet auto-registers
```

> **Nota**: Solo cuando se haya ejecutado `nodeadm uninstall` debes eliminar los archivos marcadores y depender del service de bootstrap para la reinstalación.

---

## Instalación de Cilium CNI

Cilium es el CNI compatible con AWS para EKS Hybrid Nodes. Los Hybrid Nodes aparecen con estado `Not Ready` hasta que se instala un CNI. Amazon VPC CNI **no es compatible** con Hybrid Nodes.

> **Versiones compatibles**: Cilium v1.17.x y v1.18.x para todas las versiones de Kubernetes compatibles con Amazon EKS
> **Repositorio Helm**: `oci://public.ecr.aws/eks/cilium/cilium`

> **Prerrequisitos**:
> - **Versión del kernel**: Cilium requiere kernel Linux **5.10 o superior**. Los kernels predeterminados de Ubuntu 20.04 y RHEL 8 están por debajo de 5.10 — debes actualizar el kernel antes de instalar Cilium v1.18.x.
> - **Solo Hybrid Nodes**: La affinity de Cilium debe configurarse para ejecutarse solo en Hybrid Nodes (`eks.amazonaws.com/compute-type: hybrid`). No ejecutes Cilium en cloud nodes que usan VPC CNI.
> - **La configuración IPAM es inmutable**: Los valores `clusterPoolIPv4PodCIDRList` y `clusterPoolIPv4MaskSize` **no se pueden cambiar** después del despliegue inicial. Planifica cuidadosamente la asignación de CIDR de Pods antes de instalar.

### Crear YAML de valores de Cilium

```yaml
# cilium-values.yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: In
          values:
          - hybrid

ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList:
    - <POD_CIDR>  # Same as your EKS cluster's remote pod networks

loadBalancer:
  serviceTopology: true

operator:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: In
            values:
            - hybrid
  unmanagedPodWatcher:
    restart: false

envoy:
  enabled: false

kubeProxyReplacement: "false"
```

### Instalar Cilium

```bash
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version 1.18.3-0 \
  --namespace kube-system \
  --values cilium-values.yaml
```

### Verificar la instalación

```bash
# Check Cilium pods are running
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# Nodes should now show Ready
kubectl get nodes -o wide
```

### Upgrade de Cilium

Procedimiento para actualizar Cilium a una nueva versión:

```bash
# 1. Preflight check (validate compatibility before upgrade)
helm install cilium-preflight oci://public.ecr.aws/eks/cilium/cilium \
  --version NEW_VERSION \
  --namespace kube-system \
  --set preflight.enabled=true \
  --set agent=false --set operator.enabled=false

# 2. Upgrade while preserving existing values
helm upgrade cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version NEW_VERSION \
  --namespace kube-system \
  --reuse-values

# 3. Verify status
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# 4. Rollback (if issues occur)
helm rollback cilium --namespace kube-system
```

### Desinstalación de Cilium

Procedimiento para eliminar Cilium por completo:

```bash
# 1. Helm uninstall
helm uninstall cilium --namespace kube-system

# 2. Delete CRDs
kubectl get crds -o name | grep cilium | xargs kubectl delete

# 3. On-disk cleanup (run on each node)
sudo rm -rf /var/run/cilium /var/lib/cilium /etc/cni/net.d/05-cilium.conflist
sudo rm -f /opt/cni/bin/cilium-cni
```

### Aviso de deprecación de Calico

> **Nota**: Calico ya no cuenta con soporte oficial para EKS Hybrid Nodes y se movió al repositorio `eks-hybrid-examples`. Para nuevos despliegues, se recomienda Cilium. Los despliegues existentes de Calico seguirán funcionando, pero con soporte oficial limitado de AWS.

---

## Configuración de Bottlerocket

Bottlerocket solo es compatible en entornos VMware vSphere (v1.37.0+) y solo para arquitectura x86_64. Bottlerocket **no usa nodeadm** y se inicializa mediante configuración basada en TOML y user data.

### Configuración de SSM Hybrid Activation (settings.toml)

```toml
[settings.kubernetes]
cluster-name = "CLUSTER_NAME"
api-server = "API_SERVER_ENDPOINT"
cluster-certificate = "BASE64_CA_CERT"
service-cidr = "SERVICE_CIDR"

[settings.hybrid]
enable-credentials-file = true  # Required for Pod Identity

[settings.hybrid.ssm]
activation-id = "ACTIVATION_ID"
activation-code = "ACTIVATION_CODE"
```

### Configuración de IAM Roles Anywhere (settings.toml)

```toml
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "TRUST_ANCHOR_ARN"
profile-arn = "PROFILE_ARN"
role-arn = "ROLE_ARN"
node-name = "NODE_NAME"  # Must match certificate CN
certificate-path = "/PATH/TO/CERT"
private-key-path = "/PATH/TO/KEY"
```

### Despliegue de VMware con govc

```bash
# Clone from VM template
govc vm.clone -vm "/PATH/TO/TEMPLATE" -ds="DATASTORE" \
  -on=false -template=false -folder=/FOLDER "VM_NAME"

# Configure user data
govc vm.change -dc="DC" -vm "VM_NAME" \
  -e guestinfo.userdata="${USER_DATA}" \
  -e guestinfo.userdata.encoding=gzip+base64

# Start VM
govc vm.power -on "VM_NAME"
```

> **Nota**: `USER_DATA` es el contenido de settings.toml comprimido con gzip y codificado en base64.

---

## Guía de ubicación de webhooks y add-ons

Algunos add-ons de EKS usan webhooks que requieren que el API server alcance directamente los Pods. Si tu CIDR de Pods on-premises **no es enrutable**, estos add-ons deben ejecutarse solo en cloud nodes.

### Add-ons solo en cloud (CIDR de Pods no enrutable)

Usa `nodeAffinity` para restringir add-ons basados en webhooks a cloud nodes:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - hybrid
```

Add-ons que requieren este tratamiento: AWS Load Balancer Controller, CloudWatch Observability Agent, ADOT, cert-manager.

### Modo mixto de CoreDNS

CoreDNS debe ejecutarse en **ambos** cloud nodes y Hybrid Nodes para resiliencia de DNS. Usa `topologySpreadConstraints` con al menos 4 réplicas (2 por lado). Consulta [Configuración de red - Despliegue de CoreDNS en doble ubicación](./02-network-configuration.md#coredns-dual-location-deployment-on-premises--cloud).

### EKS Pod Identity Agent

EKS Pod Identity Agent requiere el VPC endpoint `eks-auth` en entornos privados/air-gap. Instálalo como un add-on administrado de EKS:

```bash
aws eks create-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name eks-pod-identity-agent \
  --addon-version v1.3.3-eksbuild.1
```

---

## Upgrade de Node

Los Hybrid Nodes siguen la misma política de version skew de Kubernetes que upstream Kubernetes: no pueden ser más nuevos que el control plane y pueden estar hasta tres versiones minor por detrás.

### Migración por cutover (recomendada)

Cuando haya capacidad libre disponible, crea nuevos Nodes en la versión objetivo y migra workloads de forma ordenada:

```bash
# 1. Install nodeadm on new hosts with target version
nodeadm install K8S_VERSION --credential-provider CREDS_PROVIDER

# 2. Cordon old nodes
kubectl cordon NODE_NAME

# 3. Scale CoreDNS for resiliency
kubectl scale deployments/coredns --replicas=2 -n kube-system

# 4. Drain old nodes
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 5. Uninstall old nodes
sudo nodeadm uninstall

# 6. Delete old node resource
kubectl delete node NODE_NAME
```

### Upgrade in-place

Cuando no haya capacidad libre disponible, actualiza los Nodes in-place (produce downtime):

```bash
# 1. Cordon the node
kubectl cordon NODE_NAME

# 2. Drain workloads
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 3. Run nodeadm upgrade
sudo nodeadm upgrade K8S_VERSION -c file://nodeConfig.yaml

# 4. Uncordon after upgrade completes
kubectl uncordon NODE_NAME

# 5. Monitor
kubectl get nodes -o wide -w
```

---

## Solución de problemas

### nodeadm debug

El comando `nodeadm debug` valida el acceso de red, las credenciales y la conectividad del cluster:

```bash
sudo nodeadm debug -c file://nodeConfig.yaml
```

Esto valida:
- Acceso de red a las APIs de AWS
- Obtención de credenciales AWS para el IAM role de Hybrid Nodes
- Acceso de red al endpoint de la API de Kubernetes de EKS
- Autenticación del Node con el cluster EKS

### Problemas comunes y soluciones

#### Problemas de instalación

| Problema | Síntoma | Solución |
|-------|---------|-----|
| Debe ejecutarse como root | `"msg":"Command failed","error":"must run as root"` | Ejecuta `nodeadm` con `sudo` |
| No se puede conectar a las dependencias | `max retries achieved for http request` | Verifica el acceso de red a los repositorios de dependencias |
| Error del package manager | `failed to run update using package manager` | Ejecuta primero `apt update` o `dnf update` |
| Timeout | `context deadline exceeded` | Usa el flag `--timeout 20m0s` |

#### Problemas de conexión

| Problema | Síntoma | Solución |
|-------|---------|-----|
| IP del Node no está en CIDR | `node IP is not in any of the remote network CIDR blocks` | Verifica que `RemoteNodeNetworks` incluya el rango de IPs del Node |
| API server inalcanzable | `Unable to connect to the server` / `dial tcp: i/o timeout` | Revisa el túnel VPN/DX, el puerto 443 del firewall y las rutas VPC hacia TGW/VGW |
| Unauthorized | `Failed to ensure lease exists: Unauthorized` | Verifica el IAM role y la entrada de acceso EKS con tipo `HYBRID_LINUX` |
| Node permanece NotReady | Node registrado pero NotReady | Instala CNI (Cilium), revisa el puerto VXLAN 8472 |
| Error de resolución DNS | `no such host` para el endpoint de la API de EKS | Configura Route 53 Resolver Inbound Endpoint, actualiza el DNS on-prem |
| Error de pull de imagen | `ErrImagePull` en system pods | Verifica los VPC endpoints de ECR, la configuración de registry de containerd y los certificados CA |
| Error de certificado | `x509: certificate signed by unknown authority` | Instala el certificado CA en el almacén de confianza del sistema, ejecuta `update-ca-certificates` |
| Existe un hybrid profile | `hybrid profile already exists` | Ejecuta `nodeadm uninstall`, luego `nodeadm install` y después `nodeadm init` |

#### Problemas de credenciales SSM

| Problema | Síntoma | Solución |
|-------|---------|-----|
| Activación inválida | `InvalidActivation` | Verifica la región, activationCode y activationId en nodeConfig.yaml |
| Activación expirada | `ActivationExpired` | Crea una nueva SSM hybrid activation, actualiza nodeConfig.yaml |
| Token expirado | `ExpiredTokenException` | Reinicia el SSM agent: `systemctl restart amazon-ssm-agent` |

#### Problemas de IAM Roles Anywhere

| Problema | Síntoma | Solución |
|-------|---------|-----|
| Certificado no encontrado | `open /etc/iam/pki/server.pem: no such file or directory` | Crea el directorio `/etc/iam/pki/`, copia el certificado y la clave |
| No autorizado | `not authorized to perform: sts:AssumeRole` | Verifica la trust policy, el trust anchor ARN y el IAM RA profile |

### Comandos de diagnóstico

```bash
# Check kubelet status and logs
sudo systemctl status kubelet
sudo journalctl -u kubelet -f

# Check containerd
sudo systemctl status containerd

# Validate credentials
sudo aws sts get-caller-identity

# Check SSM agent (AL2023/RHEL)
sudo systemctl status amazon-ssm-agent

# Check SSM agent (Ubuntu)
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent

# Run nodeadm diagnostics
sudo nodeadm debug -c file://nodeConfig.yaml
```

### Reset de Node

Si el bootstrap falla y necesitas empezar de cero:

```bash
# Basic uninstall
sudo nodeadm uninstall

# Force uninstall (cleans all state, skips confirmation prompt)
sudo nodeadm uninstall --force

# Re-run initialization
sudo nodeadm init -c file://nodeconfig.yaml
```

**Rutas eliminadas por nodeadm uninstall:**
- `/etc/kubernetes` - Archivos de configuración de Kubernetes
- `/etc/eks` - Configuración relacionada con EKS
- Artefactos de SSM/IAM Roles Anywhere

**Cambios de v1.0.9+:**
- `/var/lib/kubelet` se **preserva de forma predeterminada** (mejora de protección de datos)
- La opción `--force` elimina todos los artefactos, incluidos los que normalmente se preservan

---

< [Anterior: Configuración Air-Gap](./03-airgap-setup.md) | [Tabla de contenidos](./README.md) | [Siguiente: Integración de GPU](./05-gpu-integration.md) >
