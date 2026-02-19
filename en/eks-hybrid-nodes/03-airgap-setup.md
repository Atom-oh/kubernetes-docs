# Air-Gap Environment Setup and Harbor Registry

< [Previous: Network Configuration](./02-network-configuration.md) | [Table of Contents](./README.md) | [Next: Node Bootstrap](./04-node-bootstrap.md) >

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **Last Updated**: February 2025

This document covers setting up air-gapped environments for EKS Hybrid Nodes, including Harbor registry installation, container image mirroring, and offline node bootstrap procedures.

## What is an Air-Gapped Environment?

An air-gapped environment is a network that is physically isolated from the public internet. This isolation is critical for:

- **Security**: Prevents unauthorized access and reduces attack surface
- **Compliance**: Meets regulatory requirements for handling sensitive data (HIPAA, PCI-DSS, government classifications)
- **Data Sovereignty**: Ensures data never leaves controlled premises
- **Operational Resilience**: Systems continue operating during internet outages

### Why Air-Gap Matters for Hybrid Nodes

EKS Hybrid Nodes in air-gapped environments face unique challenges:

1. **No direct access to public container registries** (Docker Hub, ECR Public, GCR)
2. **Cannot download nodeadm or Kubernetes binaries** from AWS endpoints
3. **No access to package repositories** (apt, yum) for system dependencies
4. **Certificate and CA bundle updates** must be manually managed

The solution involves pre-staging all required artifacts and running a local container registry (Harbor) to serve images to your hybrid nodes.

## Container Image Mirroring for Air-Gapped Environments

Before deploying hybrid nodes, you must mirror all required container images to your local Harbor registry.

### Required Images for EKS Hybrid Nodes

```bash
# EKS Core Images (replace REGION and K8S_VERSION as needed)
# K8S_VERSION example: 1.31

# Pause container (required by kubelet)
602401143452.dkr.ecr.REGION.amazonaws.com/eks/pause:3.9

# CoreDNS
602401143452.dkr.ecr.REGION.amazonaws.com/eks/coredns:v1.11.1-eksbuild.6

# Kube-proxy
602401143452.dkr.ecr.REGION.amazonaws.com/eks/kube-proxy:v1.31.0-eksbuild.5

# VPC CNI (if using AWS VPC CNI on hybrid nodes)
602401143452.dkr.ecr.REGION.amazonaws.com/amazon-k8s-cni-init:v1.18.0
602401143452.dkr.ecr.REGION.amazonaws.com/amazon-k8s-cni:v1.18.0

# AWS Node Termination Handler (optional)
public.ecr.aws/aws-ec2/aws-node-termination-handler:v1.22.0
```

### Image Mirroring Script Using skopeo

```bash
#!/bin/bash
# mirror-images.sh - Mirror required images to Harbor

set -e

# Configuration
HARBOR_URL="harbor.internal.company.io"
HARBOR_PROJECT="eks-system"
AWS_REGION="ap-northeast-2"
K8S_VERSION="1.31"

# Source images (run this from a machine with internet access)
declare -A IMAGES=(
    ["pause"]="602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/eks/pause:3.9"
    ["coredns"]="602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/eks/coredns:v1.11.1-eksbuild.6"
    ["kube-proxy"]="602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/eks/kube-proxy:v${K8S_VERSION}.0-eksbuild.5"
    ["cni-init"]="602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/amazon-k8s-cni-init:v1.18.0"
    ["cni"]="602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/amazon-k8s-cni:v1.18.0"
)

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    skopeo login --username AWS --password-stdin 602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com

# Login to Harbor
echo "Enter Harbor password:"
skopeo login ${HARBOR_URL}

# Mirror each image
for name in "${!IMAGES[@]}"; do
    src="${IMAGES[$name]}"
    dst="docker://${HARBOR_URL}/${HARBOR_PROJECT}/${name}:${src##*:}"

    echo "Mirroring: ${src} -> ${dst}"
    skopeo copy "docker://${src}" "${dst}" --all
done

echo "Image mirroring complete!"
```

### Image Mirroring Using crane

```bash
#!/bin/bash
# mirror-images-crane.sh - Alternative using crane

set -e

HARBOR_URL="harbor.internal.company.io"
HARBOR_PROJECT="eks-system"
AWS_REGION="ap-northeast-2"

# Authenticate to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    crane auth login 602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com -u AWS --password-stdin

# Authenticate to Harbor
crane auth login ${HARBOR_URL}

# Copy images
crane copy 602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/eks/pause:3.9 \
    ${HARBOR_URL}/${HARBOR_PROJECT}/pause:3.9

crane copy 602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/eks/coredns:v1.11.1-eksbuild.6 \
    ${HARBOR_URL}/${HARBOR_PROJECT}/coredns:v1.11.1-eksbuild.6

crane copy 602401143452.dkr.ecr.${AWS_REGION}.amazonaws.com/eks/kube-proxy:v1.31.0-eksbuild.5 \
    ${HARBOR_URL}/${HARBOR_PROJECT}/kube-proxy:v1.31.0-eksbuild.5
```

### Offline Image Transfer (Sneakernet)

For fully air-gapped environments, export images to tarball and transfer physically:

```bash
# On internet-connected machine: save images to tarball
skopeo copy docker://602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/pause:3.9 \
    oci-archive:pause-3.9.tar

skopeo copy docker://602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/coredns:v1.11.1-eksbuild.6 \
    oci-archive:coredns-v1.11.1.tar

# Transfer tarballs to air-gapped environment (USB, secure file transfer, etc.)

# On air-gapped machine: load images to Harbor
skopeo copy oci-archive:pause-3.9.tar \
    docker://harbor.internal.company.io/eks-system/pause:3.9

skopeo copy oci-archive:coredns-v1.11.1.tar \
    docker://harbor.internal.company.io/eks-system/coredns:v1.11.1-eksbuild.6
```

## Offline nodeadm Installation

### Downloading nodeadm and Dependencies

On an internet-connected machine, download all required binaries:

```bash
#!/bin/bash
# download-nodeadm-offline.sh

DOWNLOAD_DIR="/tmp/nodeadm-offline"
mkdir -p ${DOWNLOAD_DIR}

# Download nodeadm binary
curl -Lo ${DOWNLOAD_DIR}/nodeadm \
    https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x ${DOWNLOAD_DIR}/nodeadm

# Download kubelet binary
KUBELET_VERSION="v1.31.0"
curl -Lo ${DOWNLOAD_DIR}/kubelet \
    https://dl.k8s.io/release/${KUBELET_VERSION}/bin/linux/amd64/kubelet
chmod +x ${DOWNLOAD_DIR}/kubelet

# Download kubectl binary
curl -Lo ${DOWNLOAD_DIR}/kubectl \
    https://dl.k8s.io/release/${KUBELET_VERSION}/bin/linux/amd64/kubectl
chmod +x ${DOWNLOAD_DIR}/kubectl

# Download containerd
CONTAINERD_VERSION="1.7.14"
curl -Lo ${DOWNLOAD_DIR}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz \
    https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz

# Download runc
RUNC_VERSION="v1.1.12"
curl -Lo ${DOWNLOAD_DIR}/runc.amd64 \
    https://github.com/opencontainers/runc/releases/download/${RUNC_VERSION}/runc.amd64
chmod +x ${DOWNLOAD_DIR}/runc.amd64

# Download CNI plugins
CNI_VERSION="v1.4.0"
curl -Lo ${DOWNLOAD_DIR}/cni-plugins-linux-amd64-${CNI_VERSION}.tgz \
    https://github.com/containernetworking/plugins/releases/download/${CNI_VERSION}/cni-plugins-linux-amd64-${CNI_VERSION}.tgz

# Create tarball for transfer
tar czf nodeadm-offline-bundle.tar.gz -C ${DOWNLOAD_DIR} .
echo "Bundle created: nodeadm-offline-bundle.tar.gz"
```

### Creating a Local RPM/DEB Repository

For RHEL-based systems:

```bash
#!/bin/bash
# create-local-repo-rhel.sh

REPO_DIR="/var/www/html/repos/eks-hybrid"
mkdir -p ${REPO_DIR}

# Download required RPM packages (run on internet-connected RHEL)
yum install --downloadonly --downloaddir=${REPO_DIR} \
    conntrack-tools \
    socat \
    ebtables \
    ipset \
    ipvsadm

# Create repository metadata
createrepo ${REPO_DIR}

# On air-gapped node, configure local repo
cat <<EOF | sudo tee /etc/yum.repos.d/eks-hybrid-local.repo
[eks-hybrid-local]
name=EKS Hybrid Local Repository
baseurl=file://${REPO_DIR}
enabled=1
gpgcheck=0
EOF
```

For Ubuntu/Debian systems:

```bash
#!/bin/bash
# create-local-repo-ubuntu.sh

REPO_DIR="/var/www/html/repos/eks-hybrid"
mkdir -p ${REPO_DIR}

# Download required DEB packages
cd ${REPO_DIR}
apt-get download \
    conntrack \
    socat \
    ebtables \
    ipset \
    ipvsadm

# Generate Packages file
dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz

# On air-gapped node, configure local repo
echo "deb [trusted=yes] file://${REPO_DIR} ./" | \
    sudo tee /etc/apt/sources.list.d/eks-hybrid-local.list
```

### Installing nodeadm from Local Sources

```bash
#!/bin/bash
# install-nodeadm-offline.sh

BUNDLE_DIR="/opt/eks-hybrid-bundle"

# Extract the offline bundle
tar xzf nodeadm-offline-bundle.tar.gz -C ${BUNDLE_DIR}

# Install containerd
sudo tar xzf ${BUNDLE_DIR}/containerd-*-linux-amd64.tar.gz -C /usr/local

# Install runc
sudo install -m 755 ${BUNDLE_DIR}/runc.amd64 /usr/local/sbin/runc

# Install CNI plugins
sudo mkdir -p /opt/cni/bin
sudo tar xzf ${BUNDLE_DIR}/cni-plugins-*.tgz -C /opt/cni/bin

# Install kubelet
sudo install -m 755 ${BUNDLE_DIR}/kubelet /usr/local/bin/kubelet

# Install kubectl
sudo install -m 755 ${BUNDLE_DIR}/kubectl /usr/local/bin/kubectl

# Install nodeadm
sudo install -m 755 ${BUNDLE_DIR}/nodeadm /usr/local/bin/nodeadm

# Configure containerd systemd service
cat <<EOF | sudo tee /etc/systemd/system/containerd.service
[Unit]
Description=containerd container runtime
Documentation=https://containerd.io
After=network.target local-fs.target

[Service]
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/local/bin/containerd
Type=notify
Delegate=yes
KillMode=process
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Start containerd
sudo systemctl daemon-reload
sudo systemctl enable --now containerd

# Verify installation
nodeadm version
containerd --version
kubelet --version
```

## Proxy Configuration for Partially-Connected Environments

For environments with restricted internet access through a proxy server.

### Systemd Environment Configuration

```bash
# Configure proxy for containerd
sudo mkdir -p /etc/systemd/system/containerd.service.d
cat <<EOF | sudo tee /etc/systemd/system/containerd.service.d/proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com,.amazonaws.com"
EOF

# Configure proxy for kubelet
sudo mkdir -p /etc/systemd/system/kubelet.service.d
cat <<EOF | sudo tee /etc/systemd/system/kubelet.service.d/proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com,.amazonaws.com"
EOF

# Reload systemd and restart services
sudo systemctl daemon-reload
sudo systemctl restart containerd
```

### nodeadm Proxy Configuration

Add proxy settings to your NodeConfig:

```yaml
# nodeconfig.yaml with proxy
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

  # Proxy configuration
  kubelet:
    config:
      maxPods: 110
    flags:
      - --node-labels=topology.kubernetes.io/zone=on-premises
    environment:
      HTTP_PROXY: "http://proxy.internal.company.io:3128"
      HTTPS_PROXY: "http://proxy.internal.company.io:3128"
      NO_PROXY: "localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com"

  containerd:
    config: |
      version = 2

      [proxy]
        http_proxy = "http://proxy.internal.company.io:3128"
        https_proxy = "http://proxy.internal.company.io:3128"
        no_proxy = "localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io"
```

### Shell Environment Proxy

```bash
# Add to /etc/profile.d/proxy.sh for system-wide proxy
cat <<EOF | sudo tee /etc/profile.d/proxy.sh
export HTTP_PROXY="http://proxy.internal.company.io:3128"
export HTTPS_PROXY="http://proxy.internal.company.io:3128"
export NO_PROXY="localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,.eks.amazonaws.com,.amazonaws.com"
export http_proxy="\$HTTP_PROXY"
export https_proxy="\$HTTPS_PROXY"
export no_proxy="\$NO_PROXY"
EOF

source /etc/profile.d/proxy.sh
```

## Validating Air-Gap Readiness

Run this validation checklist before initializing hybrid nodes.

### Validation Script

```bash
#!/bin/bash
# validate-airgap-readiness.sh

echo "=== Air-Gap Readiness Validation ==="
PASS=0
FAIL=0

# 1. Check Harbor connectivity
echo ""
echo "1. Harbor Registry Connectivity"
if curl -sk https://harbor.internal.company.io/api/v2.0/health | grep -q "healthy"; then
    echo "   [PASS] Harbor is healthy"
    ((PASS++))
else
    echo "   [FAIL] Cannot connect to Harbor"
    ((FAIL++))
fi

# 2. Test image pull from Harbor
echo ""
echo "2. Image Pull Test"
if sudo ctr images pull harbor.internal.company.io/eks-system/pause:3.9 2>/dev/null; then
    echo "   [PASS] Can pull images from Harbor"
    ((PASS++))
else
    echo "   [FAIL] Cannot pull images from Harbor"
    ((FAIL++))
fi

# 3. DNS resolution
echo ""
echo "3. DNS Resolution"
if nslookup harbor.internal.company.io >/dev/null 2>&1; then
    echo "   [PASS] Harbor DNS resolution works"
    ((PASS++))
else
    echo "   [FAIL] Harbor DNS resolution failed"
    ((FAIL++))
fi

# 4. EKS API server connectivity
echo ""
echo "4. EKS API Server Connectivity"
EKS_ENDPOINT="XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com"
if curl -sk --connect-timeout 5 https://${EKS_ENDPOINT}/healthz | grep -q "ok"; then
    echo "   [PASS] EKS API server reachable"
    ((PASS++))
else
    echo "   [FAIL] Cannot reach EKS API server"
    ((FAIL++))
fi

# 5. Required binaries
echo ""
echo "5. Required Binaries"
for bin in nodeadm kubelet containerd runc; do
    if command -v $bin &>/dev/null; then
        echo "   [PASS] $bin is installed"
        ((PASS++))
    else
        echo "   [FAIL] $bin is not installed"
        ((FAIL++))
    fi
done

# 6. containerd service
echo ""
echo "6. containerd Service"
if systemctl is-active containerd >/dev/null 2>&1; then
    echo "   [PASS] containerd is running"
    ((PASS++))
else
    echo "   [FAIL] containerd is not running"
    ((FAIL++))
fi

# 7. nodeadm dry-run
echo ""
echo "7. nodeadm Configuration Validation"
if [ -f /etc/eks/nodeconfig.yaml ]; then
    if sudo nodeadm init -c file:///etc/eks/nodeconfig.yaml --dry-run 2>/dev/null; then
        echo "   [PASS] nodeadm configuration is valid"
        ((PASS++))
    else
        echo "   [FAIL] nodeadm configuration validation failed"
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

### Image Availability Check

```bash
#!/bin/bash
# check-required-images.sh

HARBOR_URL="harbor.internal.company.io"
PROJECT="eks-system"

REQUIRED_IMAGES=(
    "pause:3.9"
    "coredns:v1.11.1-eksbuild.6"
    "kube-proxy:v1.31.0-eksbuild.5"
)

echo "Checking required images in Harbor..."

for image in "${REQUIRED_IMAGES[@]}"; do
    if curl -sk "https://${HARBOR_URL}/v2/${PROJECT}/${image%:*}/manifests/${image#*:}" \
        -H "Accept: application/vnd.docker.distribution.manifest.v2+json" | grep -q "schemaVersion"; then
        echo "[OK] ${image}"
    else
        echo "[MISSING] ${image}"
    fi
done
```

## Harbor 2.13 Installation

In Hybrid Nodes environments, operating your own container registry on-premises is efficient. Harbor is an open-source registry providing enterprise-grade features.

### Prerequisites

```bash
# Add Helm repository
helm repo add harbor https://helm.goharbor.io
helm repo update

# Create namespace
kubectl create namespace harbor
```

### TLS Certificate Generation (Self-Signed)

```bash
# Generate CA key and certificate
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -sha512 -days 3650 \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=Company/OU=IT/CN=harbor-ca" \
  -key ca.key \
  -out ca.crt

# Generate Harbor server key
openssl genrsa -out harbor.key 4096

# Create CSR configuration file
cat > harbor-csr.conf <<EOF
[req]
default_bits = 4096
distinguished_name = req_distinguished_name
req_extensions = req_ext
prompt = no

[req_distinguished_name]
C = KR
ST = Seoul
L = Seoul
O = Company
OU = IT
CN = harbor.internal.company.io

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = harbor.internal.company.io
DNS.2 = harbor
DNS.3 = harbor.harbor.svc.cluster.local
IP.1 = 192.168.1.100
EOF

# Generate CSR
openssl req -new -key harbor.key -out harbor.csr -config harbor-csr.conf

# Sign certificate
openssl x509 -req -sha512 -days 3650 \
  -extfile harbor-csr.conf \
  -extensions req_ext \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -in harbor.csr \
  -out harbor.crt

# Create Kubernetes Secret
kubectl create secret tls harbor-tls \
  --cert=harbor.crt \
  --key=harbor.key \
  -n harbor
```

### Harbor Helm Values Configuration

```yaml
# harbor-values.yaml
expose:
  type: loadBalancer
  tls:
    enabled: true
    certSource: secret
    secret:
      secretName: harbor-tls

externalURL: https://harbor.internal.company.io

persistence:
  enabled: true
  persistentVolumeClaim:
    registry:
      storageClass: "local-path"
      size: 500Gi
    database:
      storageClass: "local-path"
      size: 10Gi
    redis:
      storageClass: "local-path"
      size: 5Gi
    trivy:
      storageClass: "local-path"
      size: 10Gi

harborAdminPassword: "StrongP@ssw0rd!"

database:
  type: internal
  internal:
    resources:
      requests:
        memory: 256Mi
        cpu: 100m

redis:
  type: internal

trivy:
  enabled: true
  skipUpdate: false
  resources:
    requests:
      memory: 512Mi
      cpu: 200m

metrics:
  enabled: true
  serviceMonitor:
    enabled: true
  core:
    path: /metrics
    port: 8001
  registry:
    path: /metrics
    port: 8001
  exporter:
    path: /metrics
    port: 8001

portal:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m

core:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m

jobservice:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m

registry:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m
```

```bash
# Install Harbor
helm install harbor harbor/harbor \
  --namespace harbor \
  --values harbor-values.yaml \
  --version 1.14.0

# Verify installation
kubectl get pods -n harbor
kubectl get svc -n harbor
```

### Robot Account Creation

Create a Robot Account for Kubernetes to use when pulling images.

```bash
# Create Robot Account via Harbor CLI or API
curl -k -X POST "https://harbor.internal.company.io/api/v2.0/robots" \
  -H "Content-Type: application/json" \
  -u "admin:StrongP@ssw0rd!" \
  -d '{
    "name": "k8s-pull-robot",
    "description": "Robot account for Kubernetes image pulling",
    "duration": -1,
    "level": "system",
    "permissions": [
      {
        "kind": "project",
        "namespace": "*",
        "access": [
          {"resource": "repository", "action": "pull"},
          {"resource": "artifact", "action": "read"}
        ]
      }
    ]
  }'
```

### Kubernetes Integration

#### Create Docker Registry Secret

```bash
# Create Secret with Harbor credentials
kubectl create secret docker-registry harbor-registry-secret \
  --docker-server=harbor.internal.company.io \
  --docker-username='robot$k8s-pull-robot' \
  --docker-password='<robot-account-token>' \
  --docker-email=admin@company.io \
  --namespace=default

# Replicate to all namespaces (optional)
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get secret harbor-registry-secret -n default -o yaml | \
    sed "s/namespace: default/namespace: $ns/" | \
    kubectl apply -f -
done
```

#### Configure imagePullSecrets in ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: default
  namespace: default
imagePullSecrets:
- name: harbor-registry-secret
```

```bash
# Patch existing default ServiceAccount
kubectl patch serviceaccount default \
  -p '{"imagePullSecrets": [{"name": "harbor-registry-secret"}]}'
```

#### Configure Harbor Hostname Resolution in CoreDNS

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns-custom
  namespace: kube-system
data:
  harbor.server: |
    harbor.internal.company.io:53 {
        errors
        cache 30
        hosts {
            192.168.1.100 harbor.internal.company.io
            fallthrough
        }
    }
```

---

< [Previous: Network Configuration](./02-network-configuration.md) | [Table of Contents](./README.md) | [Next: Node Bootstrap](./04-node-bootstrap.md) >
