# Configuración de entorno Air-Gap (S3 + VPC Endpoint)

< [Anterior: Configuración de red](./02-network-configuration.md) | [Tabla de contenidos](./README.md) | [Siguiente: Bootstrap del nodo](./04-node-bootstrap.md) >

> **Versiones compatibles**: EKS 1.31+, nodeadm 0.1+
> **Última actualización**: February 23, 2026

Este documento cubre la configuración de entornos air-gapped (aislados) para EKS Hybrid Nodes. Los artefactos binarios se acceden mediante un bucket S3 privado a través de VPC Endpoints, y las imágenes de contenedor se acceden mediante ECR VPC Endpoints.

## ¿Qué es un entorno Air-Gapped?

Un entorno air-gapped es una red completamente aislada de Internet público. Estos entornos son esenciales en industrias críticas para la seguridad.

### Por qué se necesita Air-Gap

| Requisito | Descripción |
|-------------|-------------|
| **Cumplimiento de seguridad** | Las industrias que manejan datos sensibles (finanzas, salud, defensa) requieren legalmente aislamiento de redes externas |
| **Prevención de exfiltración de datos** | Elimina el riesgo de fuga de datos al bloquear todas las rutas de comunicación externas |
| **Prevención de ataques a la cadena de suministro** | Evita que se introduzcan imágenes maliciosas mediante registries externos |
| **Estabilidad de red** | Las interrupciones de servicios externos no afectan a los sistemas internos |

### Tipos de entornos Air-Gapped

```mermaid
graph TD
    subgraph type1["Fully Air-Gapped"]
        A1[No Internet Connectivity] --> A2[Physical Media Delivery]
        A2 --> A3[USB / DVD / Removable HDD]
    end

    subgraph type2["Partially Air-Gapped - Proxy"]
        B1[Internal Network<br/>Restricted Access] -->|Allow-listed| B2[Proxy Server]
        B2 -->|Selective| B3[Internet]
    end

    subgraph type3["Private Connectivity - VPN/DX + VPC Endpoint"]
        C1[On-Premises<br/>Network] -->|VPN / Direct Connect| C2[AWS VPC]
        C2 --> C3[VPC Endpoints<br/>S3, ECR, etc.]
    end

    style type1 fill:#fee,stroke:#c00
    style type2 fill:#ffe,stroke:#cc0
    style type3 fill:#efe,stroke:#0a0
```

---

## Descripción general de la arquitectura Air-Gap

La arquitectura air-gap configurada en este documento es la siguiente:

```mermaid
graph TD
    subgraph prep["Preparation - Internet-Connected Host"]
        P1[hybrid-assets.eks.amazonaws.com] -->|Download manifest.yaml| P2[ekshybrid-download.sh]
        P2 -->|Binaries + Checksums| P3[Upload to Private S3 Bucket]
        P2 -->|Container Image List| P4[Pull from ECR via VPC Endpoint]
    end

    subgraph runtime["Runtime - Air-Gapped Environment"]
        R1[On-Premises Node] -->|Binary Downloads| R2[PHZ: hybrid-assets.eks.amazonaws.com]
        R2 --> R3[S3 Interface VPC Endpoint]
        R3 --> R4[Private S3 Bucket]
        R1 -->|Container Image Pulls| R5[ECR API/DKR VPC Endpoint]
        R5 --> R6[ECR]
    end

    prep -.->|"Artifacts pre-staged"| runtime

    style prep fill:#e8f4fd,stroke:#1976d2
    style runtime fill:#fce4ec,stroke:#c62828
```

### Responsabilidades de almacenamiento de artefactos

| Tipo de artefacto | Almacenamiento | Ruta de acceso |
|---------------|---------|-------------|
| nodeadm, kubelet, kubectl, kube-proxy | S3 Bucket | S3 Interface VPC Endpoint |
| cni-plugins, ecr-credential-provider | S3 Bucket | S3 Interface VPC Endpoint |
| aws-iam-authenticator, aws_signing_helper | S3 Bucket | S3 Interface VPC Endpoint |
| Archivos de checksum (.sha256) | S3 Bucket | S3 Interface VPC Endpoint |
| manifest.yaml | S3 Bucket | S3 Interface VPC Endpoint |
| imágenes pause, coredns, kube-proxy | ECR | ECR API/DKR VPC Endpoint |
| imágenes vpc-cni, vpc-cni-init | ECR | ECR API/DKR VPC Endpoint |

---

## Descarga de artefactos basada en manifest.yaml

### Estructura de manifest.yaml

`hybrid-assets.eks.amazonaws.com/manifest.yaml` contiene URLs y checksums para todos los binarios requeridos por EKS Hybrid Nodes, organizados por versión y arquitectura.

```yaml
# manifest.yaml structure (excerpt)
supported_eks_releases:
- latest_patch_version: "3"
  major_minor_version: "1.33"
  patch_releases:
  - version: "1.33.3"
    artifacts:
    - arch: amd64
      checksum_uri: https://hybrid-assets.eks.amazonaws.com/artifacts/1.33.0/.../kubelet.sha256
      name: kubelet
      os: linux
      uri: https://hybrid-assets.eks.amazonaws.com/artifacts/1.33.0/.../kubelet
    - arch: amd64
      checksum_uri: https://hybrid-assets.eks.amazonaws.com/artifacts/1.33.0/.../kubectl.sha256
      name: kubectl
      os: linux
      uri: https://hybrid-assets.eks.amazonaws.com/artifacts/1.33.0/.../kubectl
    # ... cni, cni-plugins, kube-proxy, ecr-credential-provider, aws-iam-authenticator
```

Binarios clave incluidos en manifest.yaml:

| Binario | Propósito |
|--------|---------|
| `kubelet` | Agente de Kubernetes del Node |
| `kubectl` | CLI de Kubernetes |
| `kube-proxy` | Proxy de red |
| `cni` / `cni-plugins` | Container Network Interface |
| `ecr-credential-provider` | Ayudante de autenticación de ECR |
| `aws-iam-authenticator` | Autenticación IAM |

### Script de descarga y carga a S3 (ekshybrid-download.sh)

Ejecute esto en un host conectado a Internet para descargar todos los binarios basados en manifest.yaml y cargarlos en S3.

```bash
#!/bin/bash
# ekshybrid-download.sh - EKS Hybrid nodeadm air-gap setup script
# Usage: ./ekshybrid-download.sh <S3_BUCKET_NAME> [KUBERNETES_VERSION] [ARCHITECTURE]
# Example: ./ekshybrid-download.sh ekshybrid-my-bucket 1.33.3 amd64

set -e

# Default values
KUBERNETES_VERSION="${2:-1.33.3}"
ARCHITECTURE="${3:-amd64}"
REGION="ap-northeast-2"
MANIFEST_URL="https://hybrid-assets.eks.amazonaws.com/manifest.yaml"
WORK_DIR="/tmp/nodeadm-offline"
LOG_FILE="/tmp/nodeadm-offline-setup.log"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"; }
error(){ echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"; exit 1; }
info() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"; }

# Parameter validation
if [ $# -lt 1 ]; then
    echo "Usage: $0 <S3_BUCKET_NAME> [KUBERNETES_VERSION] [ARCHITECTURE]"
    echo ""
    echo "Parameters:"
    echo "  S3_BUCKET_NAME      : S3 bucket name to store binaries (required)"
    echo "  KUBERNETES_VERSION  : Kubernetes version (default: 1.33.3)"
    echo "  ARCHITECTURE        : Architecture (default: amd64, option: arm64)"
    echo ""
    echo "Examples:"
    echo "  $0 my-nodeadm-bucket"
    echo "  $0 my-nodeadm-bucket 1.33.3 amd64"
    exit 1
fi

S3_BUCKET="$1"

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    local missing_tools=()

    command -v aws &>/dev/null  || missing_tools+=("aws-cli")
    command -v curl &>/dev/null || missing_tools+=("curl")
    command -v yq &>/dev/null   || missing_tools+=("yq (https://github.com/mikefarah/yq)")
    command -v jq &>/dev/null   || missing_tools+=("jq")

    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "The following tools are required: ${missing_tools[*]}"
    fi
    log "Prerequisites check complete"
}

# Setup work directory
setup_work_directory() {
    log "Setting up work directory..."
    rm -rf "$WORK_DIR"
    mkdir -p "$WORK_DIR"/{binaries,checksums,images}
    cd "$WORK_DIR"
}

# Download manifest.yaml
download_manifest() {
    log "Downloading manifest.yaml..."
    curl -sL "$MANIFEST_URL" -o manifest.yaml
    [ -f manifest.yaml ] || error "Failed to download manifest.yaml"
    log "manifest.yaml download complete"
}

# Extract binary URLs from manifest.yaml (using yq)
extract_binary_urls() {
    log "Extracting binary URLs for Kubernetes $KUBERNETES_VERSION ($ARCHITECTURE)..."
    local MAJOR_MINOR=$(echo "$KUBERNETES_VERSION" | cut -d. -f1,2)

    # Extract binary URLs
    yq -r ".supported_eks_releases[]
      | select(.major_minor_version == \"$MAJOR_MINOR\")
      | .patch_releases[]
      | select(.version == \"$KUBERNETES_VERSION\")
      | .artifacts[]
      | select(.os == \"linux\" and .arch == \"$ARCHITECTURE\")
      | .uri" manifest.yaml > binary_urls.txt

    # Extract checksum URLs
    yq -r ".supported_eks_releases[]
      | select(.major_minor_version == \"$MAJOR_MINOR\")
      | .patch_releases[]
      | select(.version == \"$KUBERNETES_VERSION\")
      | .artifacts[]
      | select(.os == \"linux\" and .arch == \"$ARCHITECTURE\")
      | .checksum_uri" manifest.yaml > checksum_urls.txt

    [ -s binary_urls.txt ] || error "No binaries found for the specified version/architecture"

    # Generate additional URLs and metadata as JSON
    local ECR_ACCOUNT_ID=$(yq -r ".region_config.\"$REGION\".ecr_account_id // \"602401143452\"" manifest.yaml)
    local SIGNING_URI=$(yq -r "[.iam_roles_anywhere_releases[].artifacts[] | select(.os == \"linux\" and .arch == \"$ARCHITECTURE\")] | .[0].uri // \"\"" manifest.yaml)
    local SIGNING_CHECKSUM=$(yq -r "[.iam_roles_anywhere_releases[].artifacts[] | select(.os == \"linux\" and .arch == \"$ARCHITECTURE\")] | .[0].checksum_uri // \"\"" manifest.yaml)

    jq -n \
      --arg ecr "$ECR_ACCOUNT_ID" \
      --arg nodeadm "https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/${ARCHITECTURE}/nodeadm" \
      --arg ssm "https://amazon-ssm-us-west-2.s3.us-west-2.amazonaws.com/latest/linux_${ARCHITECTURE}/ssm-setup-cli" \
      --arg signing_uri "$SIGNING_URI" \
      --arg signing_checksum "$SIGNING_CHECKSUM" \
      '{ecr_account_id: $ecr, nodeadm: $nodeadm, ssm_setup_cli: $ssm,
        aws_signing_helper: {uri: $signing_uri, checksum_uri: $signing_checksum}}' \
      > additional_urls.json

    # Generate container image list
    # Note: image tags are not included in manifest.yaml, so they are hardcoded
    local ECR_REGISTRY="${ECR_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
    cat > container_images.txt <<IMGEOF
${ECR_REGISTRY}/eks/kube-proxy:v${KUBERNETES_VERSION}-minimal-eksbuild.1
${ECR_REGISTRY}/eks/pause:3.5
${ECR_REGISTRY}/amazon-k8s-cni:v1.18.5-eksbuild.1
${ECR_REGISTRY}/amazon-k8s-cni-init:v1.18.5-eksbuild.1
${ECR_REGISTRY}/eks/coredns:v1.11.3-eksbuild.1
IMGEOF

    log "Extraction complete: $(wc -l < binary_urls.txt) binaries, $(wc -l < checksum_urls.txt) checksums, $(wc -l < container_images.txt) images"
}

# Download binaries
download_binaries() {
    log "Downloading binaries..."
    local count=0
    local total=$(wc -l < binary_urls.txt)
    while IFS= read -r url; do
        [ -n "$url" ] || continue
        count=$((count + 1))
        filename=$(basename "$url")
        info "[$count/$total] Downloading $filename..."
        curl -sL -o "binaries/$filename" "$url" && log "  $filename complete" || warn "  $filename failed"
    done < binary_urls.txt
}

# Download checksums
download_checksums() {
    log "Downloading checksum files..."
    local count=0
    local total=$(wc -l < checksum_urls.txt)
    while IFS= read -r url; do
        [ -n "$url" ] || continue
        count=$((count + 1))
        filename=$(basename "$url")
        info "[$count/$total] Downloading $filename..."
        curl -sL -o "checksums/$filename" "$url" && log "  $filename complete" || warn "  $filename failed"
    done < checksum_urls.txt
}

# Download additional binaries (nodeadm, ssm-setup-cli, aws_signing_helper)
download_additional_binaries() {
    log "Downloading additional required binaries..."
    if [ -f additional_urls.json ]; then
        local nodeadm_url=$(jq -r '.nodeadm // empty' additional_urls.json)
        [ -n "$nodeadm_url" ] && { info "Downloading nodeadm..."; curl -sL -o "binaries/nodeadm" "$nodeadm_url"; chmod +x "binaries/nodeadm"; }

        local ssm_url=$(jq -r '.ssm_setup_cli // empty' additional_urls.json)
        [ -n "$ssm_url" ] && { info "Downloading ssm-setup-cli..."; curl -sL -o "binaries/ssm-setup-cli" "$ssm_url"; chmod +x "binaries/ssm-setup-cli"; }

        local signing_helper=$(jq -r '.aws_signing_helper.uri // empty' additional_urls.json)
        [ -n "$signing_helper" ] && { info "Downloading aws_signing_helper..."; curl -sL -o "binaries/aws_signing_helper" "$signing_helper"; chmod +x "binaries/aws_signing_helper"; }
    fi
}

# Verify checksums
verify_checksums() {
    log "Verifying checksums..."
    local verified=0 failed=0
    for checksum_file in checksums/*.sha256; do
        [ -f "$checksum_file" ] || continue
        checksum_name=$(basename "$checksum_file" .sha256)
        binary_file="binaries/$checksum_name"
        [ -f "$binary_file" ] || continue
        expected=$(awk '{print $1}' "$checksum_file")
        actual=$(sha256sum "$binary_file" | awk '{print $1}')
        if [ "$expected" = "$actual" ]; then
            info "  $checksum_name verification passed"; verified=$((verified + 1))
        else
            warn "  $checksum_name verification failed"; failed=$((failed + 1))
        fi
    done
    log "Checksum verification complete: $verified passed, $failed failed"
}

# Upload to S3
upload_to_s3() {
    log "Uploading to S3 bucket ($S3_BUCKET)..."
    aws s3 ls "s3://$S3_BUCKET" --region "$REGION" &>/dev/null || {
        info "Creating S3 bucket..."; aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
    }
    aws s3 cp manifest.yaml "s3://$S3_BUCKET/manifest.yaml" --region "$REGION"
    aws s3 sync binaries/  "s3://$S3_BUCKET/binaries/"  --region "$REGION"
    aws s3 sync checksums/ "s3://$S3_BUCKET/checksums/" --region "$REGION"
    aws s3 cp container_images.txt "s3://$S3_BUCKET/container_images.txt" --region "$REGION"
    aws s3 cp additional_urls.json "s3://$S3_BUCKET/additional_urls.json" --region "$REGION"
    log "S3 upload complete"
}

# Main execution
main() {
    log "Starting EKS Hybrid nodeadm air-gap setup"
    log "S3 bucket: $S3_BUCKET, Kubernetes: $KUBERNETES_VERSION, Architecture: $ARCHITECTURE"

    check_prerequisites
    setup_work_directory
    download_manifest
    extract_binary_urls
    download_binaries
    download_checksums
    download_additional_binaries
    verify_checksums
    upload_to_s3

    log "=== Upload Summary ==="
    info "Binaries: $(ls binaries/ | wc -l) files → /binaries subfolder"
    info "Checksums: $(ls checksums/ | wc -l) files → /checksums subfolder"
    info "Container images: $(wc -l < container_images.txt) → container_images.txt"
    log "All tasks completed!"
}

main "$@"
```

La estructura resultante del bucket S3 después de la ejecución:

```
s3://<BUCKET_NAME>/
├── manifest.yaml
├── container_images.txt
├── additional_urls.json
├── binaries/
│   ├── nodeadm
│   ├── kubelet
│   ├── kubectl
│   ├── kube-proxy
│   ├── cni-plugins-linux-amd64-*.tgz
│   ├── ecr-credential-provider
│   ├── aws-iam-authenticator
│   ├── ssm-setup-cli
│   └── aws_signing_helper
└── checksums/
    ├── kubelet.sha256
    ├── kubectl.sha256
    ├── kube-proxy.sha256
    └── ...
```

---

## Configuración del bucket S3

### Creación del bucket y versionado

```bash
BUCKET_NAME="my-hybrid-assets-$(aws sts get-caller-identity --query Account --output text)"
REGION="ap-northeast-2"

# Create S3 bucket
aws s3 mb s3://${BUCKET_NAME} --region ${REGION}

# Enable versioning (for rollback)
aws s3api put-bucket-versioning \
  --bucket ${BUCKET_NAME} \
  --versioning-configuration Status=Enabled
```

### Política del bucket S3 (restricción de VPC Endpoint)

Restrinja el acceso para que solo se permitan solicitudes a través del VPC Endpoint.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowVPCEndpointAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-hybrid-assets-<ACCOUNT_ID>",
        "arn:aws:s3:::my-hybrid-assets-<ACCOUNT_ID>/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:sourceVpce": "<VPCE_ID>"
        }
      }
    },
    {
      "Sid": "DenyNonVPCEndpointAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::my-hybrid-assets-<ACCOUNT_ID>",
        "arn:aws:s3:::my-hybrid-assets-<ACCOUNT_ID>/*"
      ],
      "Condition": {
        "StringNotEquals": {
          "aws:sourceVpce": "<VPCE_ID>"
        }
      }
    }
  ]
}
```

```bash
# Apply bucket policy
aws s3api put-bucket-policy \
  --bucket my-hybrid-assets-<ACCOUNT_ID> \
  --policy file://bucket-policy.json
```

---

## Anulación DNS con PHZ

### El problema

`hybrid-assets.eks.amazonaws.com` es la URL donde AWS aloja binarios de nodeadm mediante CloudFront. Este dominio **no se puede alcanzar a través de VPC endpoints estándar**:

- Es una **distribución de CloudFront**, por lo que los endpoints de VPC de S3 o EKS no pueden enrutar hacia ella
- En entornos air-gapped, `nodeadm install` intenta descargar binarios desde esta URL y falla
- Sin una ruta a Internet, la instalación de nodeadm es imposible

### Solución

Refleje los artefactos en un bucket S3 privado y luego use una Private Hosted Zone (PHZ) para anular DNS de modo que las solicitudes a `hybrid-assets.eks.amazonaws.com` se enruten a un S3 Interface VPC Endpoint.

### S3 Interface VPC Endpoint

El S3 Interface VPC Endpoint ya se creó en el [documento de Configuración de red](./02-network-configuration.md#vpc-private-endpoints-air-gapprivate-environments). Verifique el nombre DNS del endpoint:

```bash
# Get S3 Interface VPC Endpoint DNS name
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.<REGION>.s3" \
             "Name=vpc-endpoint-type,Values=Interface" \
  --query 'VpcEndpoints[0].DnsEntries[0].DnsName' \
  --output text
# Example output: *.vpce-0abc123def456789a-xyz12345.s3.ap-northeast-2.vpce.amazonaws.com
```

### Crear Private Hosted Zone

```bash
# 1. Create Private Hosted Zone
HOSTED_ZONE_ID=$(aws route53 create-hosted-zone \
  --name "hybrid-assets.eks.amazonaws.com" \
  --vpc VPCRegion=<REGION>,VPCId=<VPC_ID> \
  --caller-reference "hybrid-assets-phz-$(date +%s)" \
  --hosted-zone-config PrivateZone=true \
  --query 'HostedZone.Id' --output text)

echo "PHZ created: ${HOSTED_ZONE_ID}"

# 2. Get S3 Interface VPC Endpoint regional DNS name
VPCE_DNS=$(aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.<REGION>.s3" \
             "Name=vpc-endpoint-type,Values=Interface" \
  --query 'VpcEndpoints[0].DnsEntries[?contains(DnsName, `vpce`)].DnsName | [0]' \
  --output text)

# 3. Get S3 VPC Endpoint Hosted Zone ID
VPCE_HZ_ID=$(aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.<REGION>.s3" \
             "Name=vpc-endpoint-type,Values=Interface" \
  --query 'VpcEndpoints[0].DnsEntries[?contains(DnsName, `vpce`)].HostedZoneId | [0]' \
  --output text)

# 4. Create Alias record
aws route53 change-resource-record-sets \
  --hosted-zone-id ${HOSTED_ZONE_ID} \
  --change-batch "{
    \"Changes\": [{
      \"Action\": \"UPSERT\",
      \"ResourceRecordSet\": {
        \"Name\": \"hybrid-assets.eks.amazonaws.com\",
        \"Type\": \"A\",
        \"AliasTarget\": {
          \"DNSName\": \"${VPCE_DNS}\",
          \"HostedZoneId\": \"${VPCE_HZ_ID}\",
          \"EvaluateTargetHealth\": true
        }
      }
    }]
  }"

echo "PHZ Alias record created"
```

### Integración de DNS on-premises

Configure su DNS on-premises para que las consultas de `hybrid-assets.eks.amazonaws.com` se resuelvan mediante la PHZ y devuelvan la IP privada del S3 VPC Endpoint.

Si ya creó un Route 53 Resolver Inbound Endpoint como se describe en el [documento de Configuración de red](./02-network-configuration.md), verifique que el reenvío condicional de su DNS on-premises incluya el dominio `eks.amazonaws.com`.

```
# BIND example - forward all eks.amazonaws.com to Route 53
zone "eks.amazonaws.com" {
    type forward;
    forward only;
    forwarders {
        10.0.1.10;    # Route 53 Inbound Endpoint IP #1
        10.0.2.10;    # Route 53 Inbound Endpoint IP #2
    };
};
```

---

## Instalación en Nodes Air-Gapped

Una vez configurada la anulación DNS con PHZ, ejecute `nodeadm install` y `nodeadm init` tal como en un entorno normal.
`nodeadm install` descarga binarios desde `hybrid-assets.eks.amazonaws.com`,
y la PHZ enruta estas solicitudes al S3 VPC Endpoint.

```bash
# 1. Install EKS components (downloaded from S3 via PHZ)
sudo nodeadm install 1.31 --credential-provider ssm

# 2. Verify installation
nodeadm version
```

### Ejecutar nodeadm init

Después de la instalación, registre el node con el cluster de EKS:

```yaml
# nodeconfig.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      -----BEGIN CERTIFICATE-----
      ...
      -----END CERTIFICATE-----
    cidr: 10.100.0.0/16

  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

  kubelet:
    config:
      maxPods: 110
    flags:
      - --node-labels=topology.kubernetes.io/zone=on-premises
```

```bash
# Validate configuration file
nodeadm config check --config-source file://nodeconfig.yaml

# Initialize node
sudo -E nodeadm init --config-source file://nodeconfig.yaml
```

---

## Acceso a imágenes de contenedor (ECR VPC Endpoint)

### Imágenes de contenedor requeridas

Las imágenes de contenedor requeridas para la operación de EKS Hybrid Nodes se proporcionan mediante ECR:

| Imagen | Propósito | Registry de origen |
|-------|---------|-----------------|
| `pause` | Contenedor de infraestructura de Pod | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/pause` |
| `coredns` | DNS del cluster | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/coredns` |
| `kube-proxy` | Proxy de red | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/kube-proxy` |
| `vpc-cni-init` | Inicialización de VPC CNI | `602401143452.dkr.ecr.<region>.amazonaws.com/amazon-k8s-cni-init` |
| `aws-node` | AWS VPC CNI | `602401143452.dkr.ecr.<region>.amazonaws.com/amazon-k8s-cni` |

### Acceso a imágenes mediante ECR VPC Endpoint

Los ECR API (`ecr.api`) y ECR DKR (`ecr.dkr`) Interface VPC Endpoints ya se crearon en el [documento de Configuración de red](./02-network-configuration.md#vpc-private-endpoints-air-gapprivate-environments). Estos permiten extraer imágenes directamente desde ECR incluso en entornos air-gapped.

### Configuración de ecr-credential-provider

kubelet requiere autenticación para extraer imágenes desde ECR. `ecr-credential-provider` ya fue descargado e instalado en `/usr/local/bin/` por ekshybrid-download.sh.

```bash
# Create credential provider config directory
sudo mkdir -p /etc/kubernetes/image-credential-provider

# Create credential provider config file
cat <<EOF | sudo tee /etc/kubernetes/image-credential-provider/config.json
{
  "apiVersion": "kubelet.config.k8s.io/v1",
  "kind": "CredentialProviderConfig",
  "providers": [
    {
      "name": "ecr-credential-provider",
      "matchImages": [
        "*.dkr.ecr.*.amazonaws.com",
        "*.dkr.ecr.*.amazonaws.com.cn"
      ],
      "defaultCacheDuration": "12h",
      "apiVersion": "credentialprovider.kubelet.k8s.io/v1"
    }
  ]
}
EOF
```

### Exportación/importación de imágenes para entornos completamente Air-Gapped

Para entornos completamente air-gapped donde los ECR VPC Endpoints tampoco están disponibles, exporte las imágenes a archivos y transfiéralas mediante medios físicos.

```bash
# Export images to tar on internet-connected environment
IMAGES=(
  "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/pause:3.5"
  "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/coredns:v1.11.3-eksbuild.1"
  "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/kube-proxy:v1.33.3-minimal-eksbuild.1"
)

EXPORT_DIR="/media/usb/eks-images"
mkdir -p $EXPORT_DIR

for img in "${IMAGES[@]}"; do
  filename=$(echo $img | tr '/:' '_')
  echo "Exporting: $img"
  skopeo copy "docker://${img}" "oci-archive:${EXPORT_DIR}/${filename}.tar"
done

# Generate checksums
cd $EXPORT_DIR && sha256sum *.tar > checksums.sha256
```

```bash
# Import images on air-gapped environment (using containerd)
IMPORT_DIR="/media/usb/eks-images"

cd $IMPORT_DIR
sha256sum -c checksums.sha256

for tarfile in $IMPORT_DIR/*.tar; do
  echo "Importing: $tarfile"
  sudo ctr -n k8s.io images import "$tarfile"
done
```

---

## Configuración de repositorio local RPM/DEB

Para implementaciones a gran escala, puede configurar un repositorio local de paquetes.

```bash
# Ubuntu/Debian - Local APT repository setup
mkdir -p /srv/apt-repo/pool
cp /media/usb/nodeadm-packages/debs/* /srv/apt-repo/pool/

cd /srv/apt-repo
dpkg-scanpackages pool /dev/null | gzip -9c > Packages.gz

# Client configuration
echo "deb [trusted=yes] file:///srv/apt-repo ./" > /etc/apt/sources.list.d/local.list
apt-get update
```

```bash
# RHEL/CentOS - Local YUM repository setup
mkdir -p /srv/yum-repo
cp /media/usb/nodeadm-packages/rpms/* /srv/yum-repo/

cd /srv/yum-repo
createrepo .

# Client configuration
cat <<EOF > /etc/yum.repos.d/local.repo
[local]
name=Local Repository
baseurl=file:///srv/yum-repo
enabled=1
gpgcheck=0
EOF

yum clean all
yum makecache
```

---

## Configuración de proxy

Para entornos parcialmente air-gapped, se puede permitir acceso externo restringido mediante un proxy.

### Configuración de proxy del sistema

```bash
# Add proxy settings to /etc/environment
cat <<EOF | sudo tee -a /etc/environment
HTTP_PROXY="http://proxy.internal.company.io:3128"
HTTPS_PROXY="http://proxy.internal.company.io:3128"
NO_PROXY="localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com"
http_proxy="http://proxy.internal.company.io:3128"
https_proxy="http://proxy.internal.company.io:3128"
no_proxy="localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com"
EOF

source /etc/environment
```

### Configuración de proxy de containerd

```bash
sudo mkdir -p /etc/systemd/system/containerd.service.d

cat <<EOF | sudo tee /etc/systemd/system/containerd.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com"
EOF

sudo systemctl daemon-reload
sudo systemctl restart containerd
```

### Configuración de proxy de kubelet

```bash
sudo mkdir -p /etc/systemd/system/kubelet.service.d

cat <<EOF | sudo tee /etc/systemd/system/kubelet.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com"
EOF

sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

### Configuración de proxy de nodeadm

```yaml
# Add proxy settings to nodeconfig.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      -----BEGIN CERTIFICATE-----
      ...
      -----END CERTIFICATE-----
    cidr: 10.100.0.0/16

  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

  kubelet:
    config:
      maxPods: 110
    flags:
      - --node-labels=topology.kubernetes.io/zone=on-premises

  containerd:
    config: |
      version = 2

      [proxy]
        [proxy.http]
          address = "http://proxy.internal.company.io:3128"
        [proxy.https]
          address = "http://proxy.internal.company.io:3128"
        [proxy.no_proxy]
          addresses = ["localhost", "127.0.0.1", "10.0.0.0/8", ".eks.amazonaws.com"]
```

### Configuración de proxy de SSM Agent específica del OS

El agente SSM requiere archivos de configuración de proxy en diferentes ubicaciones según el OS.

| OS | Ruta de configuración de proxy |
|----|-------------------|
| Ubuntu | `/etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d/http-proxy.conf` |
| AL2023 | `/etc/systemd/system/amazon-ssm-agent.service.d/http-proxy.conf` |
| RHEL | `/etc/systemd/system/amazon-ssm-agent.service.d/http-proxy.conf` |

**Ubuntu (basado en snap):**

```bash
sudo mkdir -p /etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d

cat <<EOF | sudo tee /etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,169.254.169.254,10.0.0.0/8,.eks.amazonaws.com"
EOF

sudo systemctl daemon-reload
sudo systemctl restart snap.amazon-ssm-agent.amazon-ssm-agent.service
```

**AL2023 / RHEL:**

```bash
sudo mkdir -p /etc/systemd/system/amazon-ssm-agent.service.d

cat <<EOF | sudo tee /etc/systemd/system/amazon-ssm-agent.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,169.254.169.254,10.0.0.0/8,.eks.amazonaws.com"
EOF

sudo systemctl daemon-reload
sudo systemctl restart amazon-ssm-agent
```

### Configuración de proxy de kube-proxy DaemonSet

Es posible que necesite configurar variables de entorno de proxy para el DaemonSet kube-proxy. Esta configuración debe aplicarse **después de la creación del cluster pero antes de ejecutar nodeadm init**.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kube-proxy
  namespace: kube-system
spec:
  template:
    spec:
      containers:
        - name: kube-proxy
          command:
            - kube-proxy
          env:
            - name: HTTP_PROXY
              value: "http://proxy.internal.company.io:3128"
            - name: HTTPS_PROXY
              value: "http://proxy.internal.company.io:3128"
            - name: NO_PROXY
              value: "localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.eks.amazonaws.com,.svc,.cluster.local"
```

```bash
# Patch existing kube-proxy DaemonSet with environment variables
kubectl patch daemonset kube-proxy -n kube-system --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/env",
    "value": [
      {"name": "HTTP_PROXY", "value": "http://proxy.internal.company.io:3128"},
      {"name": "HTTPS_PROXY", "value": "http://proxy.internal.company.io:3128"},
      {"name": "NO_PROXY", "value": "localhost,127.0.0.1,10.0.0.0/8,.eks.amazonaws.com,.svc,.cluster.local"}
    ]
  }
]'
```

> **Nota**: La configuración de proxy de kube-proxy debe aplicarse después de la creación del cluster pero antes de ejecutar nodeadm init. De lo contrario, kube-proxy podría no iniciar correctamente en hybrid nodes.

### Configuración de proxy de IAM Roles Anywhere

Al usar IAM Roles Anywhere, el servicio `aws_signing_helper` también requiere configuración de proxy.

```bash
sudo mkdir -p /etc/systemd/system/aws_signing_helper_update.service.d

cat <<EOF | sudo tee /etc/systemd/system/aws_signing_helper_update.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,169.254.169.254,10.0.0.0/8,.eks.amazonaws.com"
EOF

sudo systemctl daemon-reload
sudo systemctl restart aws_signing_helper_update.service
```

### Configuración de proxy del administrador de paquetes

El administrador de paquetes de su sistema operativo también puede requerir configuración de proxy.

**Ubuntu - apt:**

```bash
cat <<EOF | sudo tee /etc/apt/apt.conf.d/proxy.conf
Acquire::http::Proxy "http://proxy.internal.company.io:3128";
Acquire::https::Proxy "http://proxy.internal.company.io:3128";
EOF
```

**Ubuntu - snap:**

```bash
sudo snap set system proxy.http="http://proxy.internal.company.io:3128"
sudo snap set system proxy.https="http://proxy.internal.company.io:3128"
```

**AL2023 - dnf:**

```bash
cat <<EOF | sudo tee -a /etc/dnf/dnf.conf
proxy=http://proxy.internal.company.io:3128
EOF
```

**RHEL - yum:**

```bash
cat <<EOF | sudo tee -a /etc/yum.conf
proxy=http://proxy.internal.company.io:3128
EOF
```

### Resumen de configuración de proxy

| Componente | Archivo de configuración |
|-----------|-------------------|
| En todo el sistema | `/etc/environment` |
| containerd | `/etc/systemd/system/containerd.service.d/http-proxy.conf` |
| kubelet | `/etc/systemd/system/kubelet.service.d/http-proxy.conf` |
| SSM Agent (Ubuntu) | `/etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d/http-proxy.conf` |
| SSM Agent (AL2023/RHEL) | `/etc/systemd/system/amazon-ssm-agent.service.d/http-proxy.conf` |
| IAM Roles Anywhere | `/etc/systemd/system/aws_signing_helper_update.service.d/http-proxy.conf` |
| apt (Ubuntu) | `/etc/apt/apt.conf.d/proxy.conf` |
| snap (Ubuntu) | `snap set system proxy.*` |
| dnf (AL2023) | `/etc/dnf/dnf.conf` |
| yum (RHEL) | `/etc/yum.conf` |
| kube-proxy | Variables de entorno del DaemonSet |

---

## Validación del entorno Air-Gap

### Script de validación

```bash
#!/bin/bash
# verify-airgap.sh - Air-gap environment validation script

echo "=== Air-Gap Environment Validation ==="
PASS=0
FAIL=0

# 1. DNS Resolution Test (hybrid-assets → private IP)
echo ""
echo "1. DNS Resolution Test"
RESOLVED_IP=$(nslookup hybrid-assets.eks.amazonaws.com | grep "Address:" | tail -1 | awk '{print $2}')
echo "   hybrid-assets.eks.amazonaws.com → ${RESOLVED_IP}"

if [[ "$RESOLVED_IP" == 10.* ]] || [[ "$RESOLVED_IP" == 172.* ]] || [[ "$RESOLVED_IP" == 192.168.* ]]; then
  echo "   [PASS] Resolved to private IP (via VPC Endpoint)"
  ((PASS++))
else
  echo "   [FAIL] Resolved to public IP — check PHZ or DNS forwarding"
  ((FAIL++))
fi

# 2. S3 VPC Endpoint Connectivity Test
echo ""
echo "2. S3 VPC Endpoint Status"
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.*.s3" \
             "Name=vpc-endpoint-type,Values=Interface" \
  --query 'VpcEndpoints[].{ID:VpcEndpointId, State:State}' \
  --output table
((PASS++))

# 3. S3 Binary Download Test
echo ""
echo "3. S3 Binary Download Test"
if aws s3 ls "s3://<BUCKET_NAME>/binaries/nodeadm" --region ap-northeast-2 &>/dev/null; then
  echo "   [PASS] nodeadm verified in S3 bucket"
  ((PASS++))
else
  echo "   [FAIL] S3 bucket access failed"
  ((FAIL++))
fi

# 4. ECR VPC Endpoint Connectivity Test
echo ""
echo "4. ECR VPC Endpoint Test"
if aws ecr describe-repositories --region ap-northeast-2 &>/dev/null; then
  echo "   [PASS] ECR API connection successful"
  ((PASS++))
else
  echo "   [FAIL] ECR API connection failed"
  ((FAIL++))
fi

# 5. Container Image Pull Test
echo ""
echo "5. ECR Image Pull Test"
if sudo ctr -n k8s.io images pull 602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/pause:3.5 2>/dev/null; then
  echo "   [PASS] ECR image pull successful"
  ((PASS++))
else
  echo "   [FAIL] ECR image pull failed"
  ((FAIL++))
fi

# 6. EKS API Server Connectivity Test
echo ""
echo "6. EKS API Server Connectivity Test"
if curl -sk --connect-timeout 5 https://XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com/healthz | grep -q "ok"; then
  echo "   [PASS] EKS API server reachable"
  ((PASS++))
else
  echo "   [FAIL] EKS API server unreachable (check VPN/Direct Connect)"
  ((FAIL++))
fi

# 7. Required Binaries Check
echo ""
echo "7. Required Binaries Check"
for bin in nodeadm kubelet kubectl containerd runc; do
  if command -v $bin &>/dev/null; then
    echo "   [PASS] $bin installed"
    ((PASS++))
  else
    echo "   [FAIL] $bin not installed"
    ((FAIL++))
  fi
done

# 8. nodeadm Dry-Run Test
echo ""
echo "8. nodeadm Configuration Validation"
if [ -f /etc/eks/nodeconfig.yaml ]; then
  if sudo nodeadm init -c file:///etc/eks/nodeconfig.yaml --dry-run 2>/dev/null; then
    echo "   [PASS] nodeadm configuration valid"
    ((PASS++))
  else
    echo "   [FAIL] nodeadm configuration error"
    ((FAIL++))
  fi
else
  echo "   [SKIP] No nodeconfig.yaml found"
fi

# Summary
echo ""
echo "=== Validation Summary ==="
echo "Passed: ${PASS}"
echo "Failed: ${FAIL}"

if [ ${FAIL} -eq 0 ]; then
  echo ""
  echo "All checks passed! Ready for hybrid node initialization."
  exit 0
else
  echo ""
  echo "Some checks failed. Please resolve issues before proceeding."
  exit 1
fi
```

---

## Automatización de sincronización del mirror

Configure un cron job para sincronizar automáticamente el bucket S3 privado cuando se publiquen nuevas versiones de nodeadm.

```bash
#!/bin/bash
# sync-hybrid-assets.sh - Run on an internet-connected jump host
# crontab example: 0 2 * * 0 /opt/scripts/sync-hybrid-assets.sh

BUCKET_NAME="my-hybrid-assets-$(aws sts get-caller-identity --query Account --output text)"
LOG_FILE="/var/log/hybrid-assets-sync.log"

echo "$(date): Sync started" >> ${LOG_FILE}

for ARCH in amd64 arm64; do
  REMOTE_URL="https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/${ARCH}/nodeadm"
  S3_KEY="releases/latest/bin/linux/${ARCH}/nodeadm"
  LOCAL_TMP="/tmp/nodeadm-${ARCH}"

  # Download
  curl -sLo "${LOCAL_TMP}" "${REMOTE_URL}"

  # Compare checksum with existing file
  LOCAL_SHA=$(sha256sum "${LOCAL_TMP}" | awk '{print $1}')
  REMOTE_SHA=$(aws s3api head-object --bucket ${BUCKET_NAME} --key ${S3_KEY} \
    --query 'Metadata.sha256' --output text 2>/dev/null || echo "none")

  if [ "${LOCAL_SHA}" != "${REMOTE_SHA}" ]; then
    echo "$(date): New version detected (${ARCH}) — uploading" >> ${LOG_FILE}
    aws s3 cp "${LOCAL_TMP}" "s3://${BUCKET_NAME}/${S3_KEY}" \
      --metadata sha256="${LOCAL_SHA}"
  else
    echo "$(date): No changes (${ARCH})" >> ${LOG_FILE}
  fi

  rm -f "${LOCAL_TMP}"
done

echo "$(date): Sync complete" >> ${LOG_FILE}
```

---

< [Anterior: Configuración de red](./02-network-configuration.md) | [Tabla de contenidos](./README.md) | [Siguiente: Bootstrap del nodo](./04-node-bootstrap.md) >
