# Air-Gap (エアギャップ) 環境セットアップ (S3 + VPC Endpoint)

< [前へ: Network Configuration](./02-network-configuration.md) | [目次](./README.md) | [次へ: Node Bootstrap](./04-node-bootstrap.md) >

> **サポート対象バージョン**: EKS 1.31+, nodeadm 0.1+
> **最終更新**: February 23, 2026

このドキュメントでは、EKS Hybrid Nodes 向けの Air-Gap 環境のセットアップについて説明します。バイナリアーティファクトは VPC Endpoints 経由で private S3 bucket からアクセスし、container images は ECR VPC Endpoints 経由でアクセスします。

## Air-Gap 環境とは

Air-Gap 環境とは、public internet から完全に分離された network です。このような環境は、security が重要な業界で不可欠です。

### Air-Gap が必要な理由

| 要件 | 説明 |
|-------------|-------------|
| **Security Compliance** | 機密データを扱う業界 (金融、医療、防衛) では、外部 network からの分離が法的に求められます |
| **Data Exfiltration Prevention** | すべての外部通信経路をブロックすることで、データ漏えいリスクを排除します |
| **Supply Chain Attack Prevention** | 外部 registry から悪意のある images が持ち込まれることを防ぎます |
| **Network Stability** | 外部サービスの停止が内部システムに影響しません |

### Air-Gap 環境の種類

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

## Air-Gap アーキテクチャ概要

このドキュメントで構成する Air-Gap アーキテクチャは次のとおりです。

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

### アーティファクト保存の責任範囲

| アーティファクト種別 | 保存先 | アクセス経路 |
|---------------|---------|-------------|
| nodeadm, kubelet, kubectl, kube-proxy | S3 Bucket | S3 Interface VPC Endpoint |
| cni-plugins, ecr-credential-provider | S3 Bucket | S3 Interface VPC Endpoint |
| aws-iam-authenticator, aws_signing_helper | S3 Bucket | S3 Interface VPC Endpoint |
| Checksum files (.sha256) | S3 Bucket | S3 Interface VPC Endpoint |
| manifest.yaml | S3 Bucket | S3 Interface VPC Endpoint |
| pause, coredns, kube-proxy images | ECR | ECR API/DKR VPC Endpoint |
| vpc-cni, vpc-cni-init images | ECR | ECR API/DKR VPC Endpoint |

---

## manifest.yaml に基づくアーティファクトのダウンロード

### manifest.yaml の構造

`hybrid-assets.eks.amazonaws.com/manifest.yaml` には、EKS Hybrid Nodes に必要なすべての binaries の URLs と checksums が含まれており、version と architecture ごとに整理されています。

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

manifest.yaml に含まれる主な binaries:

| Binary | 目的 |
|--------|---------|
| `kubelet` | Node の Kubernetes agent |
| `kubectl` | Kubernetes CLI |
| `kube-proxy` | Network proxy |
| `cni` / `cni-plugins` | Container Network Interface |
| `ecr-credential-provider` | ECR authentication helper |
| `aws-iam-authenticator` | IAM authentication |

### ダウンロードと S3 アップロードスクリプト (ekshybrid-download.sh)

manifest.yaml に基づいてすべての binaries をダウンロードし、S3 にアップロードするために、internet に接続された host でこれを実行します。

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

実行後の S3 bucket 構造は次のようになります。

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

## S3 Bucket 設定

### Bucket の作成と Versioning

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

### S3 Bucket Policy (VPC Endpoint 制限)

VPC Endpoint 経由のリクエストのみを許可するようにアクセスを制限します。

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

## PHZ DNS Override

### 問題

`hybrid-assets.eks.amazonaws.com` は、AWS が CloudFront 経由で nodeadm binaries をホストしている URL です。この domain には **標準の VPC endpoints 経由では到達できません**。

- これは **CloudFront distribution** であるため、S3 または EKS VPC endpoints ではそこへ route できません
- Air-Gap 環境では、`nodeadm install` がこの URL から binaries をダウンロードしようとして失敗します
- internet 経路がない場合、nodeadm の installation は不可能です

### 解決策

アーティファクトを private S3 bucket にミラーリングし、Private Hosted Zone (PHZ) を使用して DNS を override することで、`hybrid-assets.eks.amazonaws.com` へのリクエストが S3 Interface VPC Endpoint に route されるようにします。

### S3 Interface VPC Endpoint

S3 Interface VPC Endpoint は、[Network Configuration ドキュメント](./02-network-configuration.md#vpc-private-endpoints-air-gapprivate-environments)ですでに作成済みです。endpoint DNS 名を確認します。

```bash
# Get S3 Interface VPC Endpoint DNS name
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.<REGION>.s3" \
             "Name=vpc-endpoint-type,Values=Interface" \
  --query 'VpcEndpoints[0].DnsEntries[0].DnsName' \
  --output text
# Example output: *.vpce-0abc123def456789a-xyz12345.s3.ap-northeast-2.vpce.amazonaws.com
```

### Private Hosted Zone の作成

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

### On-Premises DNS 統合

`hybrid-assets.eks.amazonaws.com` に対する query が PHZ 経由で解決され、S3 VPC Endpoint の private IP が返されるように、on-premises DNS を設定します。

[Network Configuration ドキュメント](./02-network-configuration.md)に記載されているとおり Route 53 Resolver Inbound Endpoint をすでに作成している場合は、on-premises DNS の conditional forwarding に `eks.amazonaws.com` domain が含まれていることを確認します。

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

## Air-Gapped Nodes へのインストール

PHZ DNS override を構成したら、通常の環境と同じように `nodeadm install` と `nodeadm init` を実行します。
`nodeadm install` は `hybrid-assets.eks.amazonaws.com` から binaries をダウンロードし、
PHZ はこれらのリクエストを S3 VPC Endpoint に route します。

```bash
# 1. Install EKS components (downloaded from S3 via PHZ)
sudo nodeadm install 1.31 --credential-provider ssm

# 2. Verify installation
nodeadm version
```

### nodeadm init の実行

installation 後、node を EKS cluster に登録します。

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

## Container Image Access (ECR VPC Endpoint)

### 必要な Container Images

EKS Hybrid Nodes の運用に必要な container images は ECR を通じて提供されます。

| Image | 目的 | Source Registry |
|-------|---------|-----------------|
| `pause` | Pod infrastructure container | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/pause` |
| `coredns` | Cluster DNS | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/coredns` |
| `kube-proxy` | Network proxy | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/kube-proxy` |
| `vpc-cni-init` | VPC CNI initialization | `602401143452.dkr.ecr.<region>.amazonaws.com/amazon-k8s-cni-init` |
| `aws-node` | AWS VPC CNI | `602401143452.dkr.ecr.<region>.amazonaws.com/amazon-k8s-cni` |

### ECR VPC Endpoint 経由の Image Access

ECR API (`ecr.api`) と ECR DKR (`ecr.dkr`) Interface VPC Endpoints は、[Network Configuration ドキュメント](./02-network-configuration.md#vpc-private-endpoints-air-gapprivate-environments)ですでに作成済みです。これにより、Air-Gap 環境でも ECR から直接 images を pull できます。

### ecr-credential-provider 設定

kubelet が ECR から images を pull するには authentication が必要です。`ecr-credential-provider` は ekshybrid-download.sh によりすでにダウンロードされ、`/usr/local/bin/` にインストールされています。

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

### Fully Air-Gapped 環境向けの Image Export/Import

ECR VPC Endpoints も利用できない Fully Air-Gap 環境では、images を file に export し、physical media で転送します。

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

## Local RPM/DEB Repository 設定

大規模な deployment では、local package repository をセットアップできます。

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

## Proxy 設定

Partially Air-Gap 環境では、proxy 経由で制限された外部アクセスを許可できます。

### System Proxy Settings

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

### containerd Proxy Settings

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

### kubelet Proxy Settings

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

### nodeadm Proxy Configuration

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

### OS 固有の SSM Agent Proxy Settings

SSM agent には、OS に応じて異なる場所に proxy configuration files が必要です。

| OS | Proxy Config Path |
|----|-------------------|
| Ubuntu | `/etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d/http-proxy.conf` |
| AL2023 | `/etc/systemd/system/amazon-ssm-agent.service.d/http-proxy.conf` |
| RHEL | `/etc/systemd/system/amazon-ssm-agent.service.d/http-proxy.conf` |

**Ubuntu (snap-based):**

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

### kube-proxy DaemonSet Proxy Settings

kube-proxy DaemonSet に proxy environment variables を設定する必要がある場合があります。この設定は **cluster 作成後、nodeadm init 実行前** に適用する必要があります。

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

> **注記**: kube-proxy proxy settings は、cluster 作成後、nodeadm init 実行前に適用する必要があります。そうしないと、kube-proxy が hybrid nodes 上で正しく起動しない可能性があります。

### IAM Roles Anywhere Proxy Settings

IAM Roles Anywhere を使用する場合、`aws_signing_helper` service にも proxy configuration が必要です。

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

### Package Manager Proxy Settings

使用している operating system の package manager にも proxy configuration が必要な場合があります。

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

### Proxy Configuration Summary

| Component | Configuration File |
|-----------|-------------------|
| System-wide | `/etc/environment` |
| containerd | `/etc/systemd/system/containerd.service.d/http-proxy.conf` |
| kubelet | `/etc/systemd/system/kubelet.service.d/http-proxy.conf` |
| SSM Agent (Ubuntu) | `/etc/systemd/system/snap.amazon-ssm-agent.amazon-ssm-agent.service.d/http-proxy.conf` |
| SSM Agent (AL2023/RHEL) | `/etc/systemd/system/amazon-ssm-agent.service.d/http-proxy.conf` |
| IAM Roles Anywhere | `/etc/systemd/system/aws_signing_helper_update.service.d/http-proxy.conf` |
| apt (Ubuntu) | `/etc/apt/apt.conf.d/proxy.conf` |
| snap (Ubuntu) | `snap set system proxy.*` |
| dnf (AL2023) | `/etc/dnf/dnf.conf` |
| yum (RHEL) | `/etc/yum.conf` |
| kube-proxy | DaemonSet environment variables |

---

## Air-Gap 環境の検証

### 検証スクリプト

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

## Mirror Sync Automation

新しい nodeadm versions が release されたときに private S3 bucket を自動的に同期する cron job を設定します。

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

< [前へ: Network Configuration](./02-network-configuration.md) | [目次](./README.md) | [次へ: Node Bootstrap](./04-node-bootstrap.md) >
