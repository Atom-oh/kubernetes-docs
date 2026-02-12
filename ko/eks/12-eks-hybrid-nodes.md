# EKS Hybrid Nodes 가이드

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

Amazon EKS Hybrid Nodes는 온프레미스 서버를 AWS EKS 컨트롤 플레인에서 관리할 수 있게 해주는 기능입니다. 이 문서에서는 EKS Hybrid Nodes의 개념, 설정 방법, 그리고 실제 운영 환경에서의 활용 방법을 상세히 다룹니다.

## 목차

1. [EKS Hybrid Nodes 개요](#eks-hybrid-nodes-개요)
2. [시스템 요구 사항](#시스템-요구-사항)
3. [네트워크 구성](#네트워크-구성)
4. [Harbor 레지스트리 통합](#harbor-레지스트리-통합)
5. [Hybrid Node 설정](#hybrid-node-설정)
6. [GPU 서버 통합](#gpu-서버-통합)
7. [워크로드 배치 전략](#워크로드-배치-전략)
8. [비용 최적화](#비용-최적화)
9. [운영과 유지보수](#운영과-유지보수)
10. [다음 단계](#다음-단계)

## EKS Hybrid Nodes 개요

### Hybrid Nodes란?

EKS Hybrid Nodes는 온프레미스 데이터센터나 엣지 환경에 있는 서버를 AWS EKS 컨트롤 플레인에서 관리되는 Kubernetes 노드로 등록할 수 있게 해주는 기능입니다. 이를 통해 클라우드와 온프레미스 인프라를 단일 Kubernetes 클러스터로 통합 관리할 수 있습니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    EKS Control Plane                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │ API Server  │  │    etcd     │  │ Controller  │               │   │
│  │  │             │  │             │  │  Manager    │               │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                    VPN / Direct Connect                                  │
│                              │                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────────┐
│         On-Premises          │        Data Center                        │
│  ┌───────────────────────────┴────────────────────────────────────────┐ │
│  │                     Hybrid Nodes                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │ │
│  │  │   Node 1    │  │   Node 2    │  │  GPU Node   │                 │ │
│  │  │  (Worker)   │  │  (Worker)   │  │   (H100)    │                 │ │
│  │  │  nodeadm    │  │  nodeadm    │  │  nodeadm    │                 │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 왜 Hybrid Nodes를 사용하는가?

#### 1. 규제 준수 및 데이터 주권

특정 산업(금융, 의료, 공공기관)에서는 데이터가 특정 지역이나 시설을 벗어나지 못하도록 규정하고 있습니다. Hybrid Nodes를 사용하면 민감한 데이터를 온프레미스에 유지하면서도 EKS의 관리 기능을 활용할 수 있습니다.

```yaml
# 규제 준수 워크로드 배치 예시
apiVersion: v1
kind: Pod
metadata:
  name: financial-data-processor
spec:
  nodeSelector:
    topology.kubernetes.io/zone: "on-premises"
    compliance.company.io/data-sovereignty: "required"
  containers:
  - name: processor
    image: harbor.internal.company.io/finance/data-processor:v1.2.0
```

#### 2. 데이터 중력 (Data Gravity)

대용량 데이터셋이 온프레미스에 존재하는 경우, 데이터를 클라우드로 이동하는 것보다 컴퓨팅을 데이터 가까이로 가져오는 것이 더 효율적입니다.

#### 3. 기존 하드웨어 활용

이미 투자한 고성능 서버(특히 GPU 서버)를 계속 활용하면서 Kubernetes 기반의 현대적인 워크로드 관리 방식을 적용할 수 있습니다.

#### 4. 통합 관리

클라우드와 온프레미스의 Kubernetes 워크로드를 단일 컨트롤 플레인에서 관리함으로써 운영 복잡성을 줄일 수 있습니다.

### 아키텍처 구성 요소

EKS Hybrid Nodes 아키텍처는 다음 구성 요소로 이루어집니다:

| 구성 요소 | 위치 | 역할 |
|-----------|------|------|
| EKS Control Plane | AWS | API 서버, etcd, 컨트롤러 매니저, 스케줄러 |
| nodeadm | On-Premises | 노드 부트스트랩 및 관리 에이전트 |
| kubelet | On-Premises | 파드 실행 및 노드 상태 보고 |
| containerd | On-Premises | 컨테이너 런타임 |
| VPN/Direct Connect | 네트워크 | AWS와 온프레미스 간 보안 연결 |
| SSM Agent 또는 IAM Roles Anywhere | On-Premises | 자격 증명 관리 |

### 주요 사용 사례

1. **AI/ML 워크로드**: 온프레미스 GPU 서버에서 모델 학습, 클라우드에서 추론 서비스
2. **금융 서비스**: 거래 데이터 처리는 온프레미스, 분석은 클라우드
3. **제조업**: 공장 내 엣지 컴퓨팅과 중앙 클라우드 통합
4. **미디어 처리**: 대용량 미디어 파일 처리는 데이터가 있는 곳에서 수행

## 시스템 요구 사항

### 온프레미스 노드 요구 사항

#### 지원 운영 체제

| 운영 체제 | 버전 | 아키텍처 |
|-----------|------|----------|
| Ubuntu LTS | 20.04, 22.04, 24.04 | x86_64, arm64 |
| RHEL | 8, 9 | x86_64, arm64 |
| Amazon Linux | 2023 | x86_64, arm64 |

#### 컨테이너 런타임

```bash
# containerd 버전 확인
containerd --version
# 필요 버전: 1.6.x 이상

# Docker Engine 버전 확인 (containerd 포함)
docker --version
# 필요 버전: 20.10.10 이상
```

#### 최소 하드웨어 사양

| 리소스 | 최소 사양 | 권장 사양 |
|--------|----------|----------|
| CPU | 2 코어 | 4 코어 이상 |
| RAM | 4 GB | 8 GB 이상 |
| 디스크 | 50 GB SSD | 100 GB NVMe SSD |
| 네트워크 | 1 Gbps | 10 Gbps 이상 |

#### 시스템 설정 확인

```bash
# 스왑 비활성화 확인
free -h
# Swap이 0이어야 함

# 스왑 비활성화
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# 필요한 커널 모듈 로드
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# 커널 파라미터 설정
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

### GPU 서버 요구 사항 (선택사항)

#### NVIDIA 드라이버

```bash
# NVIDIA 드라이버 버전 확인
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# 필요 버전: 550.x 이상

# CUDA 버전 확인
nvcc --version
# 권장 버전: CUDA 12.x
```

#### 지원 GPU 모델

| GPU 모델 | VRAM | 주요 용도 |
|----------|------|----------|
| NVIDIA H100 | 80 GB | 대규모 LLM 학습/추론 |
| NVIDIA H200 | 141 GB | 초대규모 모델 |
| NVIDIA A100 | 40/80 GB | AI/ML 범용 |
| NVIDIA L40S | 48 GB | 추론 최적화 |

#### GPU 드라이버 설치 (Ubuntu 예시)

```bash
# NVIDIA 드라이버 저장소 추가
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# 드라이버 설치 (버전 550)
sudo apt install -y nvidia-driver-550

# NVIDIA Container Toolkit 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

# containerd 설정 업데이트
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

### 네트워크 요구 사항

#### 대역폭 및 지연 시간

| 항목 | 최소 요구 | 권장 사양 |
|------|----------|----------|
| 대역폭 | 1 Gbps | 10 Gbps 이상 |
| 지연 시간 | 50 ms 이하 | 5 ms 이하 |
| 패킷 손실 | 0.1% 이하 | 0.01% 이하 |
| MTU | 1500 | 9000 (Jumbo Frame) |

#### Jumbo Frame 설정

```bash
# MTU 설정 확인
ip link show eth0 | grep mtu

# MTU 9000으로 설정 (임시)
sudo ip link set dev eth0 mtu 9000

# 영구 설정 (Ubuntu - Netplan)
cat <<EOF | sudo tee /etc/netplan/01-netcfg.yaml
network:
  version: 2
  ethernets:
    eth0:
      mtu: 9000
      dhcp4: true
EOF

sudo netplan apply
```

## 네트워크 구성

### 필수 방화벽 포트

온프레미스와 AWS 간 통신을 위해 다음 포트를 열어야 합니다:

| 포트 | 프로토콜 | 방향 | 용도 |
|------|----------|------|------|
| 443 | TCP | 양방향 | Kubernetes API 서버 |
| 10250 | TCP | AWS → On-Prem | Kubelet API |
| 53 | TCP/UDP | 양방향 | DNS 쿼리 |
| 4500 | UDP | 양방향 | IPSec NAT-T (VPN) |
| 500 | UDP | 양방향 | IKE (VPN) |

#### iptables 규칙 예시

```bash
# Kubernetes API 서버 통신 허용
sudo iptables -A INPUT -p tcp --dport 443 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 443 -d 10.0.0.0/8 -j ACCEPT

# Kubelet API 허용
sudo iptables -A INPUT -p tcp --dport 10250 -s 10.0.0.0/8 -j ACCEPT

# DNS 허용
sudo iptables -A INPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

# 규칙 저장
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### Pod CIDR 방화벽 전략

Pod 간 통신을 위해 전체 Pod CIDR 범위에 대한 방화벽 규칙을 등록해야 합니다.

```bash
# Pod CIDR 범위 예시: 10.244.0.0/16
# 클러스터의 Pod CIDR 확인
kubectl cluster-info dump | grep -m 1 cluster-cidr

# Pod CIDR에 대한 방화벽 규칙 추가
sudo iptables -A INPUT -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -d 10.244.0.0/16 -j ACCEPT

# Service CIDR도 추가 (예: 172.20.0.0/16)
sudo iptables -A INPUT -s 172.20.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 172.20.0.0/16 -j ACCEPT
```

### DNS 구성

#### Route 53 Resolver Inbound Endpoint

온프레미스에서 AWS 도메인을 쿼리할 수 있도록 Inbound Endpoint를 생성합니다.

```bash
# Inbound Endpoint 생성
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-inbound-$(date +%s)" \
  --name "hybrid-inbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction INBOUND \
  --ip-addresses SubnetId=subnet-111111111,Ip=10.0.1.10 SubnetId=subnet-222222222,Ip=10.0.2.10

# Endpoint IP 확인
aws route53resolver list-resolver-endpoint-ip-addresses \
  --resolver-endpoint-id rslvr-in-xxxxxxxxxxxxx
```

#### Route 53 Resolver Outbound Endpoint

AWS에서 온프레미스 도메인을 쿼리할 수 있도록 Outbound Endpoint와 전달 규칙을 생성합니다.

```bash
# Outbound Endpoint 생성
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-outbound-$(date +%s)" \
  --name "hybrid-outbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction OUTBOUND \
  --ip-addresses SubnetId=subnet-111111111 SubnetId=subnet-222222222

# 전달 규칙 생성 (온프레미스 도메인)
aws route53resolver create-resolver-rule \
  --creator-request-id "forward-onprem-$(date +%s)" \
  --name "forward-to-onprem" \
  --rule-type FORWARD \
  --domain-name "internal.company.io" \
  --resolver-endpoint-id rslvr-out-xxxxxxxxxxxxx \
  --target-ips "Ip=192.168.1.10,Port=53" "Ip=192.168.1.11,Port=53"

# VPC에 규칙 연결
aws route53resolver associate-resolver-rule \
  --resolver-rule-id rslvr-rr-xxxxxxxxxxxxx \
  --vpc-id vpc-0123456789abcdef0
```

#### CoreDNS 커스텀 도메인 구성

온프레미스 도메인에 대한 DNS 쿼리를 온프레미스 DNS 서버로 전달합니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
    internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
    harbor.internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
```

```bash
# CoreDNS ConfigMap 적용
kubectl apply -f coredns-configmap.yaml

# CoreDNS 재시작
kubectl rollout restart deployment coredns -n kube-system

# DNS 해석 테스트
kubectl run dns-test --rm -it --image=busybox --restart=Never -- nslookup harbor.internal.company.io
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

## Hybrid Node 설정

### nodeadm CLI 설치

nodeadm은 EKS Hybrid Nodes를 초기화하고 관리하는 CLI 도구입니다.

```bash
# nodeadm 다운로드 (Linux x86_64)
curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# 버전 확인
nodeadm version
```

### NodeConfig YAML 작성

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

  # 자격 증명 방식 선택 (SSM 또는 IAM Roles Anywhere)
  hybrid:
    # 방법 1: SSM Hybrid Activations
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

    # 방법 2: IAM Roles Anywhere (주석 해제하여 사용)
    # iamRolesAnywhere:
    #   trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
    #   profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
    #   roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
    #   certificatePath: /etc/eks/pki/node.crt
    #   privateKeyPath: /etc/eks/pki/node.key

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=topology.kubernetes.io/zone=on-premises,node.kubernetes.io/instance-type=on-prem-gpu
      - --register-with-taints=location=on-premises:NoSchedule

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        config_path = "/etc/containerd/certs.d"

      [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal.company.io".tls]
        ca_file = "/etc/ssl/certs/harbor-ca.crt"

      [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal.company.io".auth]
        username = "robot$k8s-pull-robot"
        password = "<robot-account-token>"
```

### SSM Hybrid Activation 생성

```bash
# SSM Hybrid Activation 생성
aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" \
  --registration-limit 100 \
  --region ap-northeast-2 \
  --tags "Key=Environment,Value=Production" "Key=NodeType,Value=Hybrid"

# 출력된 ActivationCode와 ActivationId를 nodeconfig.yaml에 입력
```

### CA 인증서 시스템 설치

```bash
# Harbor CA 인증서 시스템에 설치 (Ubuntu)
sudo cp ca.crt /usr/local/share/ca-certificates/harbor-ca.crt
sudo update-ca-certificates

# RHEL/CentOS
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/harbor-ca.crt
sudo update-ca-trust extract

# containerd가 인증서를 찾을 수 있도록 디렉토리 구성
sudo mkdir -p /etc/containerd/certs.d/harbor.internal.company.io
cat <<EOF | sudo tee /etc/containerd/certs.d/harbor.internal.company.io/hosts.toml
server = "https://harbor.internal.company.io"

[host."https://harbor.internal.company.io"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/harbor-ca.crt"
EOF
```

### 노드 초기화

```bash
# nodeadm을 사용하여 노드 초기화
sudo nodeadm init -c file://nodeconfig.yaml

# 초기화 로그 확인
sudo journalctl -u kubelet -f

# 노드 상태 확인 (EKS 클러스터에서)
kubectl get nodes -o wide
```

### 노드 등록 확인

```bash
# 노드 목록 확인
kubectl get nodes --show-labels

# 예상 출력:
# NAME                STATUS   ROLES    AGE   VERSION   LABELS
# ip-10-0-1-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2a
# ip-10-0-2-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2b
# hybrid-node-001     Ready    <none>   5m    v1.31.0   topology.kubernetes.io/zone=on-premises

# 노드 상세 정보 확인
kubectl describe node hybrid-node-001

# Hybrid Node 필터링
kubectl get nodes -l topology.kubernetes.io/zone=on-premises
```

## GPU 서버 통합

### NVIDIA GPU Operator 배포

GPU Operator는 Kubernetes 클러스터에서 NVIDIA GPU를 관리하기 위한 모든 구성 요소를 자동으로 배포합니다.

```bash
# NVIDIA GPU Operator Helm 저장소 추가
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# GPU Operator 설치
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --set driver.enabled=false \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true \
  --set migManager.enabled=false \
  --set dcgmExporter.enabled=true
```

> **참고**: 온프레미스 노드에 이미 NVIDIA 드라이버가 설치되어 있으므로 `driver.enabled=false`로 설정합니다.

### H100/H200 서버 통합

#### Device Plugin 구성 확인

```bash
# GPU 노드에서 Device Plugin 상태 확인
kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset

# GPU 리소스 확인
kubectl describe node hybrid-gpu-node-001 | grep -A 10 "Allocatable:"
# 예상 출력:
# Allocatable:
#   cpu:                128
#   memory:             1024Gi
#   nvidia.com/gpu:     8
```

#### GPU 리소스 검증

```bash
# 테스트 Pod으로 GPU 접근 확인
kubectl run gpu-test --rm -it \
  --image=nvidia/cuda:12.3.1-base-ubuntu22.04 \
  --restart=Never \
  --overrides='
{
  "spec": {
    "nodeSelector": {"topology.kubernetes.io/zone": "on-premises"},
    "tolerations": [{"key": "location", "operator": "Equal", "value": "on-premises", "effect": "NoSchedule"}],
    "containers": [{
      "name": "gpu-test",
      "image": "nvidia/cuda:12.3.1-base-ubuntu22.04",
      "command": ["nvidia-smi"],
      "resources": {"limits": {"nvidia.com/gpu": "1"}}
    }]
  }
}' \
  -- nvidia-smi
```

### Dynamic Resource Allocation (DRA)

Kubernetes 1.31+에서는 DRA를 통해 더 유연한 GPU 리소스 관리가 가능합니다.

#### ResourceClass 정의

```yaml
# gpu-resource-class.yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClass
metadata:
  name: nvidia-gpu
driverName: gpu.nvidia.com
suitableNodes:
  nodeSelectorTerms:
  - matchExpressions:
    - key: nvidia.com/gpu.present
      operator: In
      values: ["true"]
---
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClass
metadata:
  name: high-memory-gpu
driverName: gpu.nvidia.com
suitableNodes:
  nodeSelectorTerms:
  - matchExpressions:
    - key: nvidia.com/gpu.product
      operator: In
      values: ["NVIDIA-H100-80GB-HBM3", "NVIDIA-H200"]
```

#### ResourceClaim 템플릿

```yaml
# gpu-resource-claim-template.yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaimTemplate
metadata:
  name: gpu-claim-template
  namespace: ai-workloads
spec:
  spec:
    resourceClassName: nvidia-gpu
    allocationMode: WaitForFirstConsumer
```

#### DRA를 사용하는 Pod 정의

```yaml
# pod-with-dra.yaml
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference-pod
  namespace: ai-workloads
spec:
  nodeSelector:
    topology.kubernetes.io/zone: on-premises
  tolerations:
  - key: location
    operator: Equal
    value: on-premises
    effect: NoSchedule
  containers:
  - name: llm-server
    image: harbor.internal.company.io/ai/vllm-server:v0.4.0
    resources:
      claims:
      - name: gpu-resource
    env:
    - name: CUDA_VISIBLE_DEVICES
      value: "0,1,2,3"
  resourceClaims:
  - name: gpu-resource
    source:
      resourceClaimTemplateName: gpu-claim-template
```

#### DRA 모니터링 메트릭

```bash
# ResourceClaim 상태 확인
kubectl get resourceclaims -n ai-workloads

# ResourceClaim 상세 정보
kubectl describe resourceclaim gpu-claim-template-xxxxx -n ai-workloads

# DRA 컨트롤러 로그 확인
kubectl logs -n gpu-operator -l app=nvidia-dra-driver -f
```

## 워크로드 배치 전략

### Node Affinity 및 Taints/Tolerations

#### Hybrid 노드 Taint 설정

```bash
# 온프레미스 노드에 Taint 추가
kubectl taint nodes hybrid-node-001 location=on-premises:NoSchedule

# GPU 노드에 추가 Taint
kubectl taint nodes hybrid-gpu-node-001 gpu=true:NoSchedule
```

#### 온프레미스 전용 워크로드

```yaml
# on-prem-workload.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
  namespace: analytics
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-processor
  template:
    metadata:
      labels:
        app: data-processor
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - on-premises
      tolerations:
      - key: location
        operator: Equal
        value: on-premises
        effect: NoSchedule
      containers:
      - name: processor
        image: harbor.internal.company.io/analytics/data-processor:v2.1.0
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

### GPU 워크로드 온프레미스, CPU 워크로드 클라우드 패턴

```yaml
# hybrid-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-training
  namespace: ai-workloads
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ml-training
  template:
    metadata:
      labels:
        app: ml-training
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - on-premises
              - key: nvidia.com/gpu.present
                operator: In
                values:
                - "true"
      tolerations:
      - key: location
        operator: Equal
        value: on-premises
        effect: NoSchedule
      - key: gpu
        operator: Equal
        value: "true"
        effect: NoSchedule
      containers:
      - name: trainer
        image: harbor.internal.company.io/ai/model-trainer:v1.0.0
        resources:
          limits:
            nvidia.com/gpu: 4
          requests:
            cpu: "16"
            memory: "64Gi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference-api
  namespace: ai-workloads
spec:
  replicas: 5
  selector:
    matchLabels:
      app: ml-inference-api
  template:
    metadata:
      labels:
        app: ml-inference-api
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: NotIn
                values:
                - on-premises
      containers:
      - name: api
        image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/ai/inference-api:v1.0.0
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

### Karpenter를 활용한 Cloud Bursting

온프레미스 용량이 초과되면 자동으로 AWS로 확장합니다.

#### Karpenter NodePool 구성

```yaml
# karpenter-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cloud-burst-pool
spec:
  template:
    metadata:
      labels:
        node-type: cloud-burst
        topology.kubernetes.io/zone: ap-northeast-2a
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m6i.4xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2023
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-hybrid-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-hybrid-cluster
  role: KarpenterNodeRole-my-hybrid-cluster
```

#### Topology-Aware 스케줄링

```yaml
# topology-aware-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: latency-sensitive-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: latency-sensitive
  template:
    metadata:
      labels:
        app: latency-sensitive
    spec:
      topologySpreadConstraints:
      - maxSkew: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: latency-sensitive
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - on-premises
          - weight: 50
            preference:
              matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - ap-northeast-2a
                - ap-northeast-2b
      containers:
      - name: app
        image: harbor.internal.company.io/apps/latency-app:v1.0.0
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
```

## 비용 최적화

### 온프레미스 GPU vs 클라우드 GPU 비용 비교

#### 월간 비용 비교 (예시)

| 항목 | 온프레미스 H100 서버 | AWS p5.48xlarge |
|------|---------------------|-----------------|
| GPU | 8x H100 80GB | 8x H100 80GB |
| 시간당 비용 | ~$24.96 (TCO 기반) | ~$98.32 |
| 월간 비용 (24/7) | ~$17,971 | ~$70,790 |
| 3년 TCO | ~$647,000 | ~$2,548,440 |

> **계산 기준**: 온프레미스는 하드웨어, 전력, 냉각, 공간, 관리 인력 포함. 클라우드는 On-Demand 가격 기준.

#### 비용 계산 스크립트

```bash
#!/bin/bash
# cost-calculator.sh - Hybrid 환경 비용 계산기

# 온프레미스 H100 서버 월간 비용 (TCO 기반)
ONPREM_H100_MONTHLY=17971

# AWS p5.48xlarge 시간당 비용
AWS_P5_HOURLY=98.32

# 사용 시간 입력
read -p "월간 GPU 사용 시간 (시간): " HOURS

# 비용 계산
AWS_COST=$(echo "$AWS_P5_HOURLY * $HOURS" | bc)
ONPREM_COST=$ONPREM_H100_MONTHLY

echo ""
echo "=== 월간 비용 비교 ==="
echo "온프레미스 H100: \$${ONPREM_COST}"
echo "AWS p5.48xlarge: \$${AWS_COST}"
echo ""

# 손익분기점 계산
BREAKEVEN=$(echo "$ONPREM_COST / $AWS_P5_HOURLY" | bc)
echo "손익분기점: 월 ${BREAKEVEN}시간"
echo "현재 사용량이 ${BREAKEVEN}시간 이상이면 온프레미스가 유리합니다."
```

### 손익분기점 분석

```
월간 사용 시간에 따른 비용 비교:

  $80,000 |                                        ___
          |                                   ____/
  $60,000 |                              ____/
          |                         ____/
  $40,000 |                    ____/
          |               ____/
  $20,000 |----------____/------------------------ 온프레미스 (고정비)
          |     ____/
        0 |____/
          +----+----+----+----+----+----+----+----+
            100  200  300  400  500  600  700  730
                     월간 GPU 사용 시간

손익분기점: 약 183시간/월 (25% 가동률)
- 183시간 미만: AWS가 유리
- 183시간 이상: 온프레미스가 유리
```

### AWS Cost Explorer 통합

```bash
# 하이브리드 환경 비용 태그 설정
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=TAG,Key=Environment Type=TAG,Key=NodeType \
  --filter '{
    "Tags": {
      "Key": "kubernetes.io/cluster/my-hybrid-cluster",
      "Values": ["owned"]
    }
  }'

# EKS 클러스터별 비용 분석
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter '{
    "Tags": {
      "Key": "eks:cluster-name",
      "Values": ["my-hybrid-cluster"]
    }
  }'
```

### 선택적 워크로드 분배 권장사항

| 워크로드 유형 | 권장 위치 | 이유 |
|--------------|----------|------|
| 대규모 모델 학습 | 온프레미스 GPU | 장시간 사용, 비용 효율 |
| 실시간 추론 (고부하) | 온프레미스 GPU | 일관된 지연시간 |
| 실시간 추론 (변동) | AWS (Karpenter) | 탄력적 확장 |
| 데이터 전처리 | 온프레미스 CPU | 데이터 이동 최소화 |
| API 서빙 | AWS | 글로벌 배포, Auto Scaling |
| 배치 처리 | AWS Spot | 비용 최적화 |

## 운영과 유지보수

### Harbor 취약점 스캔 자동화

```yaml
# harbor-scan-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: harbor-vulnerability-scan
  namespace: harbor
spec:
  schedule: "0 2 * * *"  # 매일 오전 2시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scanner
            image: curlimages/curl:latest
            command:
            - /bin/sh
            - -c
            - |
              # 모든 프로젝트의 이미지 스캔 트리거
              for project in $(curl -sk -u admin:$HARBOR_PASSWORD \
                "https://harbor.internal.company.io/api/v2.0/projects" | \
                jq -r '.[].name'); do

                for repo in $(curl -sk -u admin:$HARBOR_PASSWORD \
                  "https://harbor.internal.company.io/api/v2.0/projects/$project/repositories" | \
                  jq -r '.[].name'); do

                  # 최신 태그 스캔
                  curl -sk -X POST -u admin:$HARBOR_PASSWORD \
                    "https://harbor.internal.company.io/api/v2.0/projects/$project/repositories/${repo#*/}/artifacts/latest/scan"
                done
              done
            env:
            - name: HARBOR_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: harbor-admin-secret
                  key: password
          restartPolicy: OnFailure
```

### 데이터베이스 백업 절차

```bash
#!/bin/bash
# harbor-backup.sh - Harbor 데이터베이스 백업 스크립트

BACKUP_DIR="/backup/harbor/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# PostgreSQL 백업
kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres registry > $BACKUP_DIR/registry.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notarysigner > $BACKUP_DIR/notarysigner.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notaryserver > $BACKUP_DIR/notaryserver.sql

# Redis 백업
kubectl exec -n harbor harbor-redis-0 -- \
  redis-cli BGSAVE

kubectl cp harbor/harbor-redis-0:/data/dump.rdb $BACKUP_DIR/redis-dump.rdb

# 레지스트리 데이터 백업 (선택사항 - 대용량)
# kubectl exec -n harbor harbor-registry-xxx -- \
#   tar czf - /storage > $BACKUP_DIR/registry-storage.tar.gz

echo "백업 완료: $BACKUP_DIR"
ls -la $BACKUP_DIR
```

### Prometheus 메트릭 수집

```yaml
# hybrid-node-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-nodes
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: kubelet
  namespaceSelector:
    matchNames:
    - kube-system
  endpoints:
  - port: https-metrics
    scheme: https
    tlsConfig:
      insecureSkipVerify: true
    bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_topology_kubernetes_io_zone]
      regex: on-premises
      action: keep
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: gpu-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames:
    - gpu-operator
  podMetricsEndpoints:
  - port: metrics
    interval: 15s
```

#### Grafana 대시보드 쿼리 예시

```promql
# Hybrid Node CPU 사용률
100 - (avg by (node) (rate(node_cpu_seconds_total{mode="idle", node=~"hybrid-.*"}[5m])) * 100)

# Hybrid Node 메모리 사용률
(1 - (node_memory_MemAvailable_bytes{node=~"hybrid-.*"} / node_memory_MemTotal_bytes{node=~"hybrid-.*"})) * 100

# GPU 사용률 (DCGM)
DCGM_FI_DEV_GPU_UTIL{kubernetes_node=~"hybrid-gpu-.*"}

# GPU 메모리 사용률
DCGM_FI_DEV_FB_USED{kubernetes_node=~"hybrid-gpu-.*"} / DCGM_FI_DEV_FB_FREE{kubernetes_node=~"hybrid-gpu-.*"} * 100
```

### Direct Connect 성능 검증

```bash
#!/bin/bash
# network-validation.sh - Direct Connect 네트워크 성능 검증

echo "=== Direct Connect 성능 검증 ==="

# 타겟 설정
EKS_API_ENDPOINT="XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com"
AWS_VPC_HOST="10.0.1.100"

# 지연시간 테스트
echo ""
echo "1. 지연시간 테스트 (목표: <5ms)"
LATENCY=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f2)
echo "   평균 지연시간: ${LATENCY}ms"
if (( $(echo "$LATENCY < 5" | bc -l) )); then
    echo "   [PASS] 지연시간 목표 충족"
else
    echo "   [WARN] 지연시간이 목표(5ms)를 초과합니다"
fi

# 지터 테스트
echo ""
echo "2. 지터 테스트 (목표: <2ms)"
JITTER=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f4)
echo "   지터: ${JITTER}ms"
if (( $(echo "$JITTER < 2" | bc -l) )); then
    echo "   [PASS] 지터 목표 충족"
else
    echo "   [WARN] 지터가 목표(2ms)를 초과합니다"
fi

# 패킷 손실 테스트
echo ""
echo "3. 패킷 손실 테스트 (목표: <0.01%)"
PACKET_LOSS=$(ping -c 1000 $AWS_VPC_HOST | grep "packet loss" | awk '{print $6}' | tr -d '%')
echo "   패킷 손실률: ${PACKET_LOSS}%"
if (( $(echo "$PACKET_LOSS < 0.01" | bc -l) )); then
    echo "   [PASS] 패킷 손실 목표 충족"
else
    echo "   [WARN] 패킷 손실이 목표(0.01%)를 초과합니다"
fi

# 대역폭 테스트 (iperf3 필요)
echo ""
echo "4. 대역폭 테스트 (목표: >1Gbps)"
if command -v iperf3 &> /dev/null; then
    BANDWIDTH=$(iperf3 -c $AWS_VPC_HOST -t 10 -f g | grep "sender" | awk '{print $7}')
    echo "   대역폭: ${BANDWIDTH} Gbps"
else
    echo "   [SKIP] iperf3가 설치되지 않았습니다"
fi

echo ""
echo "=== 검증 완료 ==="
```

### 인증서 갱신 관리

```bash
#!/bin/bash
# cert-renewal.sh - 인증서 만료 확인 및 갱신 알림

# Harbor 인증서 만료일 확인
echo "=== 인증서 만료 확인 ==="

HARBOR_CERT="/etc/ssl/certs/harbor-ca.crt"
DAYS_WARNING=30

if [ -f "$HARBOR_CERT" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in $HARBOR_CERT | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    echo "Harbor CA 인증서"
    echo "  만료일: $EXPIRY_DATE"
    echo "  남은 일수: $DAYS_LEFT일"

    if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
        echo "  [WARN] 인증서 갱신이 필요합니다!"
        # 알림 전송 (Slack, Email 등)
    else
        echo "  [OK] 인증서 유효"
    fi
fi

# Kubernetes 인증서 확인
echo ""
echo "Kubernetes 클러스터 인증서"
kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].lastHeartbeatTime}'
```

### 일반적인 문제 해결

#### ImagePullBackOff 진단

```bash
# 문제 파드 확인
kubectl get pods --all-namespaces | grep ImagePullBackOff

# 상세 정보 확인
kubectl describe pod <pod-name> -n <namespace>

# 일반적인 원인 및 해결책:
# 1. Harbor 인증 실패
kubectl get secret harbor-registry-secret -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq

# 2. 인증서 문제 확인
openssl s_client -connect harbor.internal.company.io:443 -CAfile /etc/ssl/certs/harbor-ca.crt

# 3. DNS 해석 문제
kubectl run dns-debug --rm -it --image=busybox --restart=Never -- nslookup harbor.internal.company.io

# 4. 네트워크 연결 문제
kubectl run net-debug --rm -it --image=nicolaka/netshoot --restart=Never -- curl -v https://harbor.internal.company.io/v2/
```

#### DNS 해석 문제

```bash
# CoreDNS 로그 확인
kubectl logs -n kube-system -l k8s-app=kube-dns -f

# DNS 쿼리 테스트
kubectl run dnsutils --rm -it --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 --restart=Never -- bash
# Pod 내에서:
nslookup harbor.internal.company.io
nslookup kubernetes.default.svc.cluster.local
dig +short harbor.internal.company.io

# CoreDNS 재시작
kubectl rollout restart deployment coredns -n kube-system
```

#### 노드 연결 문제

```bash
# 노드 상태 확인
kubectl get nodes
kubectl describe node hybrid-node-001

# kubelet 로그 확인 (노드에서 실행)
sudo journalctl -u kubelet -f --since "10 minutes ago"

# API 서버 연결 테스트 (노드에서 실행)
curl -k https://<EKS-API-ENDPOINT>:443/healthz

# SSM Agent 상태 확인 (노드에서 실행)
sudo systemctl status amazon-ssm-agent

# 노드 재등록
sudo nodeadm reset
sudo nodeadm init -c file://nodeconfig.yaml
```

## 다음 단계

EKS Hybrid Nodes에 대한 이해를 더욱 깊이 하고 실습을 진행하려면 다음 리소스를 참고하세요:

### 퀴즈

이 문서의 내용을 테스트하려면 다음 퀴즈를 풀어보세요:
- [EKS Hybrid Nodes 퀴즈](../../quizzes/eks/12-eks-hybrid-nodes-quiz.md)

### 관련 문서

- [EKS 복원력 가이드](./10-eks-resiliency.md) - 하이브리드 환경에서의 고가용성 구성
- [EKS 비용 최적화](./07-eks-cost-optimization.md) - 비용 관리 전략
- [EKS 모니터링 및 로깅](./06-eks-monitoring-logging.md) - 통합 모니터링 구성

### 공식 문서

- [AWS EKS Hybrid Nodes 공식 문서](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes.html)
- [nodeadm 사용자 가이드](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Harbor 공식 문서](https://goharbor.io/docs/)
- [NVIDIA GPU Operator 문서](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
