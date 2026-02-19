# 에어갭 환경 구성 및 Harbor 레지스트리

< [이전: 네트워크 구성](./02-network-configuration.md) | [목차](./README.md) | [다음: 노드 부트스트랩](./04-node-bootstrap.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 에어갭(Air-Gapped) 환경에서 EKS Hybrid Nodes를 구성하는 방법과 Harbor 레지스트리 통합을 다룹니다.

## 에어갭 환경이란?

에어갭(Air-Gapped) 환경은 외부 인터넷과 완전히 격리된 네트워크 환경을 의미합니다. 이러한 환경은 보안이 중요한 산업에서 필수적으로 요구됩니다.

### 에어갭 환경이 필요한 이유

| 요구 사항 | 설명 |
|-----------|------|
| **보안 규정 준수** | 금융, 의료, 국방 등 민감한 데이터를 다루는 산업에서는 외부 네트워크와의 격리가 법적으로 요구됩니다 |
| **데이터 유출 방지** | 외부 통신 경로를 차단하여 데이터 유출 위험을 원천적으로 차단합니다 |
| **공급망 공격 방지** | 외부 레지스트리에서 악성 이미지가 유입되는 것을 방지합니다 |
| **네트워크 안정성** | 외부 서비스 장애가 내부 시스템에 영향을 미치지 않습니다 |

### 에어갭 환경의 유형

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        완전 에어갭 환경                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  인터넷 연결 없음                                                  │   │
│  │  모든 소프트웨어/이미지는 물리적 미디어로 전달                        │   │
│  │  USB, DVD, 이동식 하드 드라이브 사용                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        부분 에어갭 환경 (프록시)                          │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐        │
│  │  내부 네트워크  │ ─→ │   프록시 서버   │ ─→ │   인터넷        │        │
│  │  (제한된 접근)  │    │  (허용 목록만)  │    │  (선별된 접근)  │        │
│  └────────────────┘    └────────────────┘    └────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

## 에어갭 환경에서의 컨테이너 이미지 미러링

### 필수 EKS/Kubernetes 이미지 목록

EKS Hybrid Nodes를 운영하려면 다음 이미지들을 로컬 레지스트리에 미러링해야 합니다:

| 이미지 | 용도 | 소스 레지스트리 |
|--------|------|-----------------|
| `pause` | Pod 인프라 컨테이너 | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/pause` |
| `coredns` | 클러스터 DNS | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/coredns` |
| `kube-proxy` | 네트워크 프록시 | `602401143452.dkr.ecr.<region>.amazonaws.com/eks/kube-proxy` |
| `vpc-cni-init` | VPC CNI 초기화 | `602401143452.dkr.ecr.<region>.amazonaws.com/amazon-k8s-cni-init` |
| `aws-node` | AWS VPC CNI | `602401143452.dkr.ecr.<region>.amazonaws.com/amazon-k8s-cni` |

### skopeo를 사용한 이미지 미러링

```bash
#!/bin/bash
# mirror-eks-images.sh - EKS 필수 이미지 미러링 스크립트

# 설정
SOURCE_REGISTRY="602401143452.dkr.ecr.ap-northeast-2.amazonaws.com"
TARGET_REGISTRY="harbor.internal.company.io/eks-system"
EKS_VERSION="1.31"

# AWS ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  skopeo login --username AWS --password-stdin $SOURCE_REGISTRY

# Harbor 로그인
skopeo login $TARGET_REGISTRY --username admin --password 'StrongP@ssw0rd!'

# 미러링할 이미지 목록
declare -A IMAGES=(
  ["eks/pause:3.9"]="pause:3.9"
  ["eks/coredns:v1.11.1-eksbuild.8"]="coredns:v1.11.1"
  ["eks/kube-proxy:v${EKS_VERSION}.0-eksbuild.1"]="kube-proxy:v${EKS_VERSION}.0"
  ["amazon-k8s-cni-init:v1.18.0"]="vpc-cni-init:v1.18.0"
  ["amazon-k8s-cni:v1.18.0"]="aws-node:v1.18.0"
)

# 이미지 미러링
for src in "${!IMAGES[@]}"; do
  dst="${IMAGES[$src]}"
  echo "Mirroring: $src -> $dst"
  skopeo copy --all \
    "docker://${SOURCE_REGISTRY}/${src}" \
    "docker://${TARGET_REGISTRY}/${dst}"
done

echo "이미지 미러링 완료!"
```

### crane을 사용한 이미지 미러링

```bash
#!/bin/bash
# mirror-with-crane.sh - crane을 사용한 이미지 미러링

# crane 설치 (필요한 경우)
# GO111MODULE=on go install github.com/google/go-containerregistry/cmd/crane@latest

SOURCE_REGISTRY="602401143452.dkr.ecr.ap-northeast-2.amazonaws.com"
TARGET_REGISTRY="harbor.internal.company.io/eks-system"

# ECR 인증
aws ecr get-login-password --region ap-northeast-2 | \
  crane auth login $SOURCE_REGISTRY --username AWS --password-stdin

# Harbor 인증
crane auth login $TARGET_REGISTRY --username admin --password 'StrongP@ssw0rd!'

# 이미지 복사
crane copy "${SOURCE_REGISTRY}/eks/pause:3.9" "${TARGET_REGISTRY}/pause:3.9"
crane copy "${SOURCE_REGISTRY}/eks/coredns:v1.11.1-eksbuild.8" "${TARGET_REGISTRY}/coredns:v1.11.1"
crane copy "${SOURCE_REGISTRY}/eks/kube-proxy:v1.31.0-eksbuild.1" "${TARGET_REGISTRY}/kube-proxy:v1.31.0"
```

### 오프라인 환경을 위한 이미지 내보내기/가져오기

완전한 에어갭 환경에서는 이미지를 파일로 내보내 물리적 미디어로 전달해야 합니다.

```bash
#!/bin/bash
# export-images.sh - 이미지를 tar 파일로 내보내기

EXPORT_DIR="/media/usb/eks-images"
mkdir -p $EXPORT_DIR

# 이미지 목록
IMAGES=(
  "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/pause:3.9"
  "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/coredns:v1.11.1-eksbuild.8"
  "602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/eks/kube-proxy:v1.31.0-eksbuild.1"
)

# 이미지 저장
for img in "${IMAGES[@]}"; do
  filename=$(echo $img | tr '/:' '_')
  echo "Exporting: $img"
  skopeo copy "docker://${img}" "oci-archive:${EXPORT_DIR}/${filename}.tar"
done

# 체크섬 생성
cd $EXPORT_DIR
sha256sum *.tar > checksums.sha256
```

```bash
#!/bin/bash
# import-images.sh - tar 파일에서 이미지 가져오기 (에어갭 환경)

IMPORT_DIR="/media/usb/eks-images"
TARGET_REGISTRY="harbor.internal.company.io/eks-system"

# 체크섬 검증
cd $IMPORT_DIR
sha256sum -c checksums.sha256

# Harbor 로그인
skopeo login $TARGET_REGISTRY --username admin --password 'StrongP@ssw0rd!'

# 이미지 가져오기
for tarfile in $IMPORT_DIR/*.tar; do
  # 파일명에서 이미지 이름 추출
  basename=$(basename $tarfile .tar)
  # 간단한 이름으로 변환 (예: pause_3.9)
  simple_name=$(echo $basename | sed 's/.*_eks_//' | tr '_' ':')

  echo "Importing: $tarfile -> $TARGET_REGISTRY/$simple_name"
  skopeo copy "oci-archive:${tarfile}" "docker://${TARGET_REGISTRY}/${simple_name}"
done
```

## nodeadm 오프라인 설치

에어갭 환경에서는 nodeadm과 필요한 바이너리를 미리 다운로드하여 로컬 저장소에서 설치해야 합니다.

### 필요한 패키지 다운로드 (인터넷 연결 환경)

```bash
#!/bin/bash
# download-nodeadm-packages.sh - 오프라인 설치를 위한 패키지 다운로드

DOWNLOAD_DIR="/media/usb/nodeadm-packages"
mkdir -p $DOWNLOAD_DIR/{binaries,rpms,debs}

# nodeadm 바이너리 다운로드
curl -Lo $DOWNLOAD_DIR/binaries/nodeadm \
  https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x $DOWNLOAD_DIR/binaries/nodeadm

# containerd 바이너리 다운로드
CONTAINERD_VERSION="1.7.13"
curl -Lo $DOWNLOAD_DIR/binaries/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz \
  https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz

# runc 다운로드
RUNC_VERSION="1.1.12"
curl -Lo $DOWNLOAD_DIR/binaries/runc.amd64 \
  https://github.com/opencontainers/runc/releases/download/v${RUNC_VERSION}/runc.amd64

# CNI 플러그인 다운로드
CNI_VERSION="1.4.0"
curl -Lo $DOWNLOAD_DIR/binaries/cni-plugins-linux-amd64-v${CNI_VERSION}.tgz \
  https://github.com/containernetworking/plugins/releases/download/v${CNI_VERSION}/cni-plugins-linux-amd64-v${CNI_VERSION}.tgz

# Ubuntu/Debian용 패키지 다운로드
cd $DOWNLOAD_DIR/debs
apt-get download \
  iptables \
  conntrack \
  socat \
  ethtool \
  ebtables

# RHEL/CentOS용 패키지 다운로드
cd $DOWNLOAD_DIR/rpms
yumdownloader \
  iptables \
  conntrack-tools \
  socat \
  ethtool \
  ebtables

echo "패키지 다운로드 완료: $DOWNLOAD_DIR"
```

### 에어갭 환경에서 설치

```bash
#!/bin/bash
# install-nodeadm-offline.sh - 오프라인 환경에서 nodeadm 설치

PACKAGE_DIR="/media/usb/nodeadm-packages"

# OS 감지
if [ -f /etc/debian_version ]; then
  PKG_TYPE="deb"
  PKG_INSTALL="dpkg -i"
elif [ -f /etc/redhat-release ]; then
  PKG_TYPE="rpm"
  PKG_INSTALL="rpm -ivh"
else
  echo "지원되지 않는 OS입니다"
  exit 1
fi

# 의존성 패키지 설치
echo "의존성 패키지 설치 중..."
$PKG_INSTALL $PACKAGE_DIR/${PKG_TYPE}s/*

# containerd 설치
echo "containerd 설치 중..."
tar -xzf $PACKAGE_DIR/binaries/containerd-*-linux-amd64.tar.gz -C /usr/local

# runc 설치
echo "runc 설치 중..."
install -m 755 $PACKAGE_DIR/binaries/runc.amd64 /usr/local/sbin/runc

# CNI 플러그인 설치
echo "CNI 플러그인 설치 중..."
mkdir -p /opt/cni/bin
tar -xzf $PACKAGE_DIR/binaries/cni-plugins-linux-amd64-*.tgz -C /opt/cni/bin

# nodeadm 설치
echo "nodeadm 설치 중..."
install -m 755 $PACKAGE_DIR/binaries/nodeadm /usr/local/bin/nodeadm

# containerd 서비스 설정
cat <<EOF | sudo tee /etc/systemd/system/containerd.service
[Unit]
Description=containerd container runtime
Documentation=https://containerd.io
After=network.target

[Service]
ExecStart=/usr/local/bin/containerd
Restart=always
RestartSec=5
Delegate=yes
KillMode=process
OOMScoreAdjust=-999
LimitNOFILE=1048576
LimitNPROC=infinity
LimitCORE=infinity

[Install]
WantedBy=multi-user.target
EOF

# containerd 시작
systemctl daemon-reload
systemctl enable --now containerd

# 설치 확인
echo ""
echo "=== 설치 확인 ==="
nodeadm version
containerd --version
runc --version
```

### 로컬 RPM/DEB 저장소 구성

대규모 배포를 위해 로컬 패키지 저장소를 구성할 수 있습니다.

```bash
# Ubuntu/Debian - 로컬 APT 저장소 구성
mkdir -p /srv/apt-repo/pool
cp /media/usb/nodeadm-packages/debs/* /srv/apt-repo/pool/

cd /srv/apt-repo
dpkg-scanpackages pool /dev/null | gzip -9c > Packages.gz

# 클라이언트 설정
echo "deb [trusted=yes] file:///srv/apt-repo ./" > /etc/apt/sources.list.d/local.list
apt-get update
```

```bash
# RHEL/CentOS - 로컬 YUM 저장소 구성
mkdir -p /srv/yum-repo
cp /media/usb/nodeadm-packages/rpms/* /srv/yum-repo/

cd /srv/yum-repo
createrepo .

# 클라이언트 설정
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

## 프록시 환경 구성

부분 에어갭 환경에서는 프록시를 통해 제한된 외부 접근을 허용할 수 있습니다.

### 시스템 프록시 설정

```bash
# /etc/environment에 프록시 설정 추가
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

### containerd 프록시 설정

```bash
# containerd 서비스에 프록시 환경 변수 추가
sudo mkdir -p /etc/systemd/system/containerd.service.d

cat <<EOF | sudo tee /etc/systemd/system/containerd.service.d/http-proxy.conf
[Service]
Environment="HTTP_PROXY=http://proxy.internal.company.io:3128"
Environment="HTTPS_PROXY=http://proxy.internal.company.io:3128"
Environment="NO_PROXY=localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal.company.io,harbor.internal.company.io"
EOF

sudo systemctl daemon-reload
sudo systemctl restart containerd
```

### kubelet 프록시 설정

```bash
# kubelet 서비스에 프록시 환경 변수 추가
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

### nodeadm 프록시 설정

```yaml
# nodeconfig.yaml에 프록시 설정 추가
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

  # 프록시 설정
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
          addresses = ["localhost", "127.0.0.1", "10.0.0.0/8", "harbor.internal.company.io"]
```

## 에어갭 환경 검증

### 이미지 풀링 테스트

```bash
#!/bin/bash
# verify-airgap.sh - 에어갭 환경 검증 스크립트

echo "=== 에어갭 환경 검증 ==="

# Harbor 연결 테스트
echo ""
echo "1. Harbor 레지스트리 연결 테스트"
curl -sk https://harbor.internal.company.io/api/v2.0/systeminfo | jq '.harbor_version'
if [ $? -eq 0 ]; then
  echo "   [PASS] Harbor 연결 성공"
else
  echo "   [FAIL] Harbor 연결 실패"
fi

# 이미지 풀링 테스트
echo ""
echo "2. 이미지 풀링 테스트"
ctr image pull harbor.internal.company.io/eks-system/pause:3.9 --skip-verify
if [ $? -eq 0 ]; then
  echo "   [PASS] 이미지 풀링 성공"
else
  echo "   [FAIL] 이미지 풀링 실패"
fi

# DNS 해석 테스트
echo ""
echo "3. DNS 해석 테스트"
nslookup harbor.internal.company.io
if [ $? -eq 0 ]; then
  echo "   [PASS] DNS 해석 성공"
else
  echo "   [FAIL] DNS 해석 실패"
fi

# EKS API 서버 연결 테스트
echo ""
echo "4. EKS API 서버 연결 테스트"
curl -sk --connect-timeout 5 https://XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com/healthz
if [ $? -eq 0 ]; then
  echo "   [PASS] EKS API 서버 연결 성공"
else
  echo "   [FAIL] EKS API 서버 연결 실패 (VPN/Direct Connect 확인 필요)"
fi

# nodeadm dry-run 테스트
echo ""
echo "5. nodeadm dry-run 테스트"
sudo nodeadm init -c file://nodeconfig.yaml --dry-run
if [ $? -eq 0 ]; then
  echo "   [PASS] nodeadm 구성 유효"
else
  echo "   [FAIL] nodeadm 구성 오류"
fi

echo ""
echo "=== 검증 완료 ==="
```

## Harbor 레지스트리 통합

Hybrid Nodes 환경에서는 온프레미스에 자체 컨테이너 레지스트리를 운영하는 것이 효율적입니다. Harbor는 엔터프라이즈급 기능을 제공하는 오픈소스 레지스트리입니다.

### Harbor 2.13 설치 (Helm)

#### 사전 준비

```bash
# Helm 저장소 추가
helm repo add harbor https://helm.goharbor.io
helm repo update

# 네임스페이스 생성
kubectl create namespace harbor
```

#### TLS 인증서 생성 (Self-Signed)

```bash
# CA 키 및 인증서 생성
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -sha512 -days 3650 \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=Company/OU=IT/CN=harbor-ca" \
  -key ca.key \
  -out ca.crt

# Harbor 서버 키 생성
openssl genrsa -out harbor.key 4096

# CSR 설정 파일 생성
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

# CSR 생성
openssl req -new -key harbor.key -out harbor.csr -config harbor-csr.conf

# 인증서 서명
openssl x509 -req -sha512 -days 3650 \
  -extfile harbor-csr.conf \
  -extensions req_ext \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -in harbor.csr \
  -out harbor.crt

# Kubernetes Secret 생성
kubectl create secret tls harbor-tls \
  --cert=harbor.crt \
  --key=harbor.key \
  -n harbor
```

#### Harbor Helm Values 구성

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
# Harbor 설치
helm install harbor harbor/harbor \
  --namespace harbor \
  --values harbor-values.yaml \
  --version 1.14.0

# 설치 확인
kubectl get pods -n harbor
kubectl get svc -n harbor
```

### Robot Account 생성

Kubernetes에서 이미지를 풀링할 때 사용할 Robot Account를 생성합니다.

```bash
# Harbor CLI 또는 API를 통한 Robot Account 생성
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

### Kubernetes 통합

#### Docker Registry Secret 생성

```bash
# Harbor 자격 증명으로 Secret 생성
kubectl create secret docker-registry harbor-registry-secret \
  --docker-server=harbor.internal.company.io \
  --docker-username='robot$k8s-pull-robot' \
  --docker-password='<robot-account-token>' \
  --docker-email=admin@company.io \
  --namespace=default

# 모든 네임스페이스에 복제 (선택사항)
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get secret harbor-registry-secret -n default -o yaml | \
    sed "s/namespace: default/namespace: $ns/" | \
    kubectl apply -f -
done
```

#### ServiceAccount에 imagePullSecrets 설정

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
# 기존 default ServiceAccount 패치
kubectl patch serviceaccount default \
  -p '{"imagePullSecrets": [{"name": "harbor-registry-secret"}]}'
```

#### CoreDNS에서 Harbor 호스트명 해석 설정

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

< [이전: 네트워크 구성](./02-network-configuration.md) | [목차](./README.md) | [다음: 노드 부트스트랩](./04-node-bootstrap.md) >
