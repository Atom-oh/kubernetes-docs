# Amazon EKS Hybrid Nodes 퀴즈

이 퀴즈는 Amazon EKS Hybrid Nodes의 아키텍처, nodeadm 도구, Harbor 레지스트리 연동, GPU 통합, Dynamic Resource Allocation(DRA), 네트워크 구성, 비용 최적화에 대한 이해를 테스트합니다.

## 퀴즈 개요
- EKS Hybrid Nodes 아키텍처 및 구성 요소
- nodeadm을 통한 노드 부트스트래핑
- Harbor 프라이빗 레지스트리 연동
- GPU 및 가속기 통합 (MIG, Time-Slicing)
- Dynamic Resource Allocation (DRA)
- 하이브리드 네트워크 구성
- 비용 최적화 전략

## 객관식 문제

### 1. EKS Hybrid Nodes의 주요 사용 사례로 적합하지 않은 것은?

A. 온프레미스 데이터센터의 GPU 서버 활용
B. 규제 준수를 위한 데이터 로컬리티 요구사항
C. 순수 클라우드 네이티브 워크로드 실행
D. 레이턴시에 민감한 엣지 워크로드

<details>
<summary>정답 보기</summary>

**정답: C. 순수 클라우드 네이티브 워크로드 실행**

**설명:**
순수 클라우드 네이티브 워크로드는 일반 EKS 노드 그룹이나 Fargate에서 실행하는 것이 더 효율적입니다. Hybrid Nodes는 특별한 요구사항(온프레미스, 엣지, 규제 등)이 있을 때 사용합니다.

**EKS Hybrid Nodes 적합한 사용 사례:**
- 온프레미스 GPU/특수 하드웨어 활용
- 데이터 주권/규제 준수 요구사항
- 레이턴시에 민감한 엣지 컴퓨팅
- 클라우드 마이그레이션 과도기
- 기존 인프라 투자 보호

```bash
# Hybrid Node 등록 예시
nodeadm init \
  --cluster-name my-cluster \
  --region ap-northeast-2 \
  --hybrid-node
```

</details>

### 2. nodeadm의 주요 역할은 무엇인가요?

A. EKS 클러스터 생성
B. 노드의 kubelet, containerd 등 구성 요소 설치 및 부트스트래핑
C. Pod 스케줄링 결정
D. 클러스터 네트워크 정책 관리

<details>
<summary>정답 보기</summary>

**정답: B. 노드의 kubelet, containerd 등 구성 요소 설치 및 부트스트래핑**

**설명:**
nodeadm은 EKS 노드 부트스트래핑을 위한 공식 도구로, kubelet, containerd, aws-iam-authenticator 등 필요한 구성 요소를 설치하고 구성합니다.

```bash
# nodeadm 설치
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# nodeadm으로 노드 초기화
sudo nodeadm init \
  --config-source file://nodeadm-config.yaml

# nodeadm 설정 파일 예시 (nodeadm-config.yaml)
---
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://xxxxx.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: LS0tLS1CRUdJTi...
  kubelet:
    config:
      maxPods: 110
    flags:
      - "--node-labels=node.kubernetes.io/lifecycle=hybrid"
```

**nodeadm 기능:**
- Kubernetes 구성 요소 설치 (kubelet, containerd)
- AWS IAM Authenticator 구성
- kubelet 인증서 부트스트래핑
- 노드 레이블 및 taints 설정

</details>

### 3. Harbor 프라이빗 레지스트리를 Kubernetes와 연동할 때 사용하는 Secret 유형은?

A. Opaque
B. kubernetes.io/dockerconfigjson
C. kubernetes.io/tls
D. kubernetes.io/service-account-token

<details>
<summary>정답 보기</summary>

**정답: B. kubernetes.io/dockerconfigjson**

**설명:**
Docker/Container 레지스트리 인증 정보는 `kubernetes.io/dockerconfigjson` 타입의 Secret으로 저장합니다. imagePullSecrets에서 이 Secret을 참조하여 프라이빗 이미지를 풀링합니다.

```bash
# Harbor 레지스트리 Secret 생성
kubectl create secret docker-registry harbor-secret \
  --docker-server=harbor.example.com \
  --docker-username=admin \
  --docker-password=Harbor12345 \
  --docker-email=admin@example.com

# 또는 YAML로 직접 생성
apiVersion: v1
kind: Secret
metadata:
  name: harbor-secret
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: eyJhdXRocyI6eyJoYXJib3IuZXhhbXBsZS5jb20iOnsidXNlcm5hbWUiOiJhZG1pbiIsInBhc3N3b3JkIjoiSGFyYm9yMTIzNDUiLCJhdXRoIjoiWVdSdGFXNDZTR0Z5WW05eU1USXpORFU9In19fQ==
```

```yaml
# Pod에서 imagePullSecrets 사용
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: harbor.example.com/project/my-app:v1
  imagePullSecrets:
  - name: harbor-secret
```

</details>

### 4. NVIDIA GPU의 Multi-Instance GPU (MIG) 기술의 주요 특징은?

A. 여러 GPU를 하나로 통합
B. 단일 GPU를 물리적으로 격리된 여러 인스턴스로 분할
C. GPU 메모리만 공유
D. 소프트웨어 레벨의 시분할

<details>
<summary>정답 보기</summary>

**정답: B. 단일 GPU를 물리적으로 격리된 여러 인스턴스로 분할**

**설명:**
MIG(Multi-Instance GPU)는 NVIDIA A100, H100 등의 GPU를 최대 7개의 물리적으로 격리된 인스턴스로 분할합니다. 각 인스턴스는 독립적인 메모리, 캐시, 컴퓨팅 리소스를 가집니다.

**MIG vs Time-Slicing 비교:**

| 특성 | MIG | Time-Slicing |
|-----|-----|--------------|
| 격리 수준 | 물리적 (완전 격리) | 시간 기반 (소프트웨어) |
| 메모리 격리 | 완전 격리 | 공유 |
| 지원 GPU | A100, H100 | 모든 NVIDIA GPU |
| QoS 보장 | 예 | 아니오 |

```yaml
# MIG 설정 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: nvidia-mig-config
  namespace: gpu-operator
data:
  config.yaml: |
    version: v1
    mig-configs:
      all-1g.5gb:
        - devices: all
          mig-enabled: true
          mig-devices:
            "1g.5gb": 7
      all-3g.20gb:
        - devices: all
          mig-enabled: true
          mig-devices:
            "3g.20gb": 2
```

```yaml
# MIG 리소스 요청
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/mig-1g.5gb: 1
```

</details>

### 5. Dynamic Resource Allocation (DRA)의 주요 장점은?

A. 정적 리소스 할당만 지원
B. 벤더별 플러그인 없이 모든 디바이스 지원
C. 사용자 정의 리소스에 대한 유연한 요청/할당 메커니즘
D. CPU와 메모리만 관리

<details>
<summary>정답 보기</summary>

**정답: C. 사용자 정의 리소스에 대한 유연한 요청/할당 메커니즘**

**설명:**
DRA(Dynamic Resource Allocation)는 Kubernetes 1.26에서 도입된 기능으로, GPU, FPGA, 네트워크 디바이스 등 사용자 정의 리소스에 대해 더 유연한 요청 및 할당 메커니즘을 제공합니다.

**DRA의 핵심 구성 요소:**
- **ResourceClass**: 드라이버가 제공하는 리소스 유형 정의
- **ResourceClaim**: 리소스에 대한 요청
- **ResourceClaimTemplate**: 재사용 가능한 클레임 템플릿

```yaml
# ResourceClass 정의
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: nvidia-gpu
driverName: gpu.nvidia.com

---
# ResourceClaimTemplate
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClaimTemplate
metadata:
  name: gpu-claim-template
spec:
  spec:
    resourceClassName: nvidia-gpu
    parametersRef:
      apiGroup: gpu.nvidia.com
      kind: GpuClaimParameters
      name: single-gpu

---
# Pod에서 DRA 사용
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      claims:
      - name: gpu
  resourceClaims:
  - name: gpu
    source:
      resourceClaimTemplateName: gpu-claim-template
```

**DRA vs Device Plugin 비교:**
- DRA: 더 유연한 리소스 속성 지정 가능
- DRA: Pod 간 리소스 공유 지원
- DRA: 런타임에 동적 리소스 할당

</details>

### 6. EKS Hybrid Nodes에서 온프레미스와 클라우드 간 네트워크 연결에 권장되는 방식은?

A. 인터넷 공용 연결
B. AWS Direct Connect 또는 Site-to-Site VPN
C. SSH 터널링
D. HTTP 프록시

<details>
<summary>정답 보기</summary>

**정답: B. AWS Direct Connect 또는 Site-to-Site VPN**

**설명:**
EKS Hybrid Nodes는 EKS 컨트롤 플레인과 안정적이고 보안된 네트워크 연결이 필요합니다. AWS Direct Connect(전용선) 또는 Site-to-Site VPN이 권장됩니다.

**네트워크 요구사항:**
- EKS API 서버 엔드포인트 접근 (443/TCP)
- AWS 서비스 엔드포인트 접근 (ECR, S3, STS 등)
- 안정적인 저지연 연결

```bash
# Site-to-Site VPN 설정 확인
aws ec2 describe-vpn-connections \
  --filters Name=state,Values=available

# VPN 연결 상태 모니터링
aws cloudwatch get-metric-statistics \
  --namespace AWS/VPN \
  --metric-name TunnelState \
  --dimensions Name=VpnId,Value=vpn-xxxxxx
```

```yaml
# Hybrid Node용 nodeadm 네트워크 설정
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://xxxxx.gr7.ap-northeast-2.eks.amazonaws.com
  hybrid:
    ssm: false  # SSM 대신 VPN/Direct Connect 사용
  containerd:
    config: |
      [plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.onprem.local"]
        endpoint = ["https://harbor.onprem.local"]
```

</details>

### 7. Harbor에서 이미지 복제(Replication)를 위한 정책 유형으로 올바르지 않은 것은?

A. Push-based
B. Pull-based
C. Event-based
D. Sync-based

<details>
<summary>정답 보기</summary>

**정답: D. Sync-based**

**설명:**
Harbor는 Push-based, Pull-based, Event-based 복제 정책을 지원합니다. "Sync-based"는 Harbor의 공식 용어가 아닙니다.

**Harbor 복제 정책 유형:**
1. **Push-based**: 소스 Harbor에서 타겟 레지스트리로 푸시
2. **Pull-based**: 타겟 Harbor가 소스에서 이미지를 가져옴
3. **Event-based**: 이미지 푸시 이벤트 발생 시 자동 복제

```yaml
# Harbor 복제 정책 API 예시
POST /api/v2.0/replication/policies
{
  "name": "ecr-replication",
  "src_registry": {
    "id": 1
  },
  "dest_registry": {
    "id": 2
  },
  "dest_namespace": "production",
  "trigger": {
    "type": "event_based"
  },
  "filters": [
    {
      "type": "name",
      "value": "myapp/**"
    },
    {
      "type": "tag",
      "value": "v*"
    }
  ],
  "enabled": true,
  "deletion": false
}
```

</details>

### 8. GPU Time-Slicing에서 oversubscription이 발생할 때 예상되는 현상은?

A. GPU 작업 완전 실패
B. 컨텍스트 스위칭으로 인한 성능 저하
C. 자동 GPU 추가
D. 메모리 자동 확장

<details>
<summary>정답 보기</summary>

**정답: B. 컨텍스트 스위칭으로 인한 성능 저하**

**설명:**
Time-Slicing은 하나의 GPU를 시간 단위로 여러 워크로드가 공유합니다. Oversubscription(초과 할당) 시 컨텍스트 스위칭이 빈번해져 성능이 저하됩니다.

```yaml
# GPU Time-Slicing 설정 (NVIDIA Device Plugin)
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: false
        resources:
        - name: nvidia.com/gpu
          replicas: 4  # 1 GPU를 4개로 분할
```

```yaml
# Time-Slicing GPU 요청
apiVersion: v1
kind: Pod
metadata:
  name: gpu-timeslice-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/gpu: 1  # 실제로는 1/4 GPU
```

**Time-Slicing 고려사항:**
- 메모리는 공유되므로 OOM 발생 가능
- 추론(inference) 워크로드에 적합
- 학습(training)에는 MIG 또는 전용 GPU 권장
- 적절한 replicas 수 설정 중요

</details>

### 9. EKS Hybrid Nodes에서 IAM 인증에 사용되는 방식은?

A. 정적 토큰
B. x509 인증서만
C. IAM Roles Anywhere 또는 IAM 사용자 자격 증명
D. LDAP 인증

<details>
<summary>정답 보기</summary>

**정답: C. IAM Roles Anywhere 또는 IAM 사용자 자격 증명**

**설명:**
EKS Hybrid Nodes는 온프레미스에서 AWS IAM 인증이 필요합니다. IAM Roles Anywhere를 사용하면 온프레미스 서버에서도 IAM 역할을 사용할 수 있습니다.

```bash
# IAM Roles Anywhere Trust Anchor 생성
aws rolesanywhere create-trust-anchor \
  --name hybrid-nodes-anchor \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CERT_DATA}"

# IAM Roles Anywhere Profile 생성
aws rolesanywhere create-profile \
  --name hybrid-node-profile \
  --role-arns arn:aws:iam::123456789012:role/HybridNodeRole \
  --duration-seconds 3600

# 자격 증명 가져오기 (노드에서)
aws_signing_helper credential-process \
  --certificate /path/to/cert.pem \
  --private-key /path/to/key.pem \
  --trust-anchor-arn arn:aws:rolesanywhere:region:account:trust-anchor/id \
  --profile-arn arn:aws:rolesanywhere:region:account:profile/id \
  --role-arn arn:aws:iam::account:role/HybridNodeRole
```

```yaml
# nodeadm 설정에서 IAM Roles Anywhere 사용
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
  iam:
    mode: rolesAnywhere
    rolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/HybridNodeRole
      certificatePath: /etc/pki/hybrid/cert.pem
      privateKeyPath: /etc/pki/hybrid/key.pem
```

</details>

### 10. Hybrid Nodes 환경에서 비용 최적화를 위한 전략으로 적합하지 않은 것은?

A. 온프레미스 GPU는 추론 워크로드에 활용
B. 버스트 트래픽은 클라우드 노드에서 처리
C. 모든 워크로드를 Hybrid Nodes로 이전
D. 데이터 로컬리티가 필요한 워크로드는 온프레미스에서 실행

<details>
<summary>정답 보기</summary>

**정답: C. 모든 워크로드를 Hybrid Nodes로 이전**

**설명:**
모든 워크로드를 Hybrid Nodes로 이전하면 오히려 복잡성이 증가하고 비용 효율성이 떨어집니다. 워크로드 특성에 따라 적절한 위치를 선택해야 합니다.

**비용 최적화 전략:**

| 워크로드 유형 | 권장 위치 | 이유 |
|-------------|----------|-----|
| 상시 GPU 추론 | 온프레미스 | 기존 하드웨어 활용 |
| 버스트 트래픽 | 클라우드 | 탄력적 확장 |
| 데이터 집약적 | 데이터 근처 | 전송 비용 절감 |
| 스테이트리스 | 클라우드 | 관리 용이성 |
| 규제 대상 | 온프레미스 | 컴플라이언스 |

```yaml
# 워크로드별 노드 선택 (NodeSelector)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  template:
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: hybrid  # 온프레미스 GPU
      containers:
      - name: inference
        resources:
          limits:
            nvidia.com/gpu: 1
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: burst-handler
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/capacityType: SPOT  # 클라우드 Spot
```

</details>

## 단답형 문제

### 1. nodeadm을 사용하여 Hybrid Node를 초기화할 때 반드시 제공해야 하는 3가지 클러스터 정보는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
1. **클러스터 이름 (name)**
2. **API 서버 엔드포인트 (apiServerEndpoint)**
3. **인증 기관(CA) 인증서 (certificateAuthority)**

```yaml
# nodeadm 설정 파일 필수 항목
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster                    # 필수 1
    region: ap-northeast-2
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com  # 필수 2
    certificateAuthority: LS0tLS1CRUdJTi...             # 필수 3
```

```bash
# EKS에서 필수 정보 가져오기
aws eks describe-cluster --name my-cluster --query "cluster.{name:name,endpoint:endpoint,ca:certificateAuthority.data}" --output json
```

</details>

### 2. NVIDIA GPU MIG 구성에서 "1g.5gb"의 의미는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:**
- **1g**: 1 GPU Instance (컴퓨팅 슬라이스 1개)
- **5gb**: 5GB GPU 메모리

MIG 인스턴스 이름 형식: `<compute-slices>g.<memory-size>gb`

**A100 MIG 프로파일 예시:**
- `1g.5gb`: 1 컴퓨팅 슬라이스, 5GB 메모리 (최대 7개)
- `2g.10gb`: 2 컴퓨팅 슬라이스, 10GB 메모리 (최대 3개)
- `3g.20gb`: 3 컴퓨팅 슬라이스, 20GB 메모리 (최대 2개)
- `4g.40gb`: 4 컴퓨팅 슬라이스, 40GB 메모리 (최대 1개)
- `7g.40gb`: 7 컴퓨팅 슬라이스, 40GB 메모리 (전체 GPU)

```bash
# MIG 인스턴스 확인
nvidia-smi mig -lgi
```

</details>

### 3. Harbor에서 이미지 취약점 스캔을 위해 기본으로 제공되는 스캐너는 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** Trivy

**설명:**
Harbor 2.0부터 Trivy가 기본 취약점 스캐너로 포함되어 있습니다. Clair도 선택적으로 사용할 수 있습니다.

```bash
# Harbor 취약점 스캔 API
POST /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/scan

# 스캔 결과 조회
GET /api/v2.0/projects/{project_name}/repositories/{repository_name}/artifacts/{reference}/additions/vulnerabilities
```

**Harbor 스캔 정책 설정:**
```yaml
# 프로젝트 레벨 자동 스캔 활성화
# Harbor UI: Projects > Configuration > Vulnerability scanning
# - Automatically scan images on push: enabled
# - Prevent vulnerable images from running: enabled (CVE severity threshold)
```

</details>

### 4. DRA(Dynamic Resource Allocation)에서 ResourceClaim의 상태가 "Bound"가 되려면 어떤 조건이 충족되어야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 드라이버가 ResourceClaim에 대해 실제 리소스를 할당(Allocation)하고, 해당 클레임을 사용하는 Pod가 스케줄링되어야 합니다.

**ResourceClaim 상태 흐름:**
1. **Pending**: 클레임 생성됨, 아직 할당 안됨
2. **Allocated**: 드라이버가 리소스 할당 완료
3. **Bound**: Pod에 바인딩되어 사용 중

```yaml
# ResourceClaim 상태 확인
kubectl get resourceclaim gpu-claim -o yaml

# 예상 출력
status:
  allocation:
    resourceHandles:
    - driverName: gpu.nvidia.com
      data: '{"gpu":"GPU-abc123"}'
  reservedFor:
  - name: gpu-workload
    uid: xxx-xxx-xxx
```

</details>

### 5. EKS Hybrid Nodes에서 AWS 서비스 접근을 위해 필요한 VPC 엔드포인트 3가지를 나열하세요.

<details>
<summary>정답 보기</summary>

**정답:**
1. **ec2.region.amazonaws.com** (EC2 API)
2. **ecr.api.region.amazonaws.com** (ECR API)
3. **sts.region.amazonaws.com** (STS - IAM 인증)

**추가 권장 엔드포인트:**
- `ecr.dkr.region.amazonaws.com` (ECR Docker Registry)
- `s3.region.amazonaws.com` (S3 - ECR 이미지 저장소)
- `logs.region.amazonaws.com` (CloudWatch Logs)
- `ssm.region.amazonaws.com` (Systems Manager)

```bash
# VPC 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.ap-northeast-2.sts \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxx \
  --security-group-ids sg-xxx
```

</details>

## 실습 문제

### 1. Harbor 프라이빗 레지스트리에서 이미지를 가져올 수 있도록 Kubernetes Secret과 ServiceAccount를 구성하세요.
- Harbor URL: harbor.company.local
- 프로젝트: production
- 사용자: k8s-puller (비밀번호: PullSecret123)

<details>
<summary>정답 보기</summary>

```bash
# 1. Docker Registry Secret 생성
kubectl create secret docker-registry harbor-creds \
  --docker-server=harbor.company.local \
  --docker-username=k8s-puller \
  --docker-password=PullSecret123 \
  --namespace=default
```

```yaml
# 2. ServiceAccount에 imagePullSecrets 연결
apiVersion: v1
kind: ServiceAccount
metadata:
  name: harbor-puller
  namespace: default
imagePullSecrets:
- name: harbor-creds

---
# 3. Deployment에서 사용
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: harbor-puller
      containers:
      - name: app
        image: harbor.company.local/production/myapp:v1.0
        ports:
        - containerPort: 8080
```

**검증 명령어:**
```bash
# Secret 확인
kubectl get secret harbor-creds -o yaml

# ServiceAccount 확인
kubectl get sa harbor-puller -o yaml

# Pod 이미지 풀링 확인
kubectl describe pod -l app=myapp | grep -A 5 "Events:"
```

</details>

### 2. NVIDIA GPU Time-Slicing을 구성하여 1개의 GPU를 4개의 가상 GPU로 분할하는 ConfigMap을 작성하세요.

<details>
<summary>정답 보기</summary>

```yaml
# 1. Time-Slicing ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: false
        resources:
        - name: nvidia.com/gpu
          replicas: 4

---
# 2. NVIDIA Device Plugin DaemonSet 업데이트 (ConfigMap 참조)
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: nvidia-device-plugin
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      containers:
      - name: nvidia-device-plugin-ctr
        image: nvcr.io/nvidia/k8s-device-plugin:v0.14.3
        env:
        - name: CONFIG_FILE
          value: /etc/kubernetes/nvidia-device-plugin/config.yaml
        volumeMounts:
        - name: device-plugin-config
          mountPath: /etc/kubernetes/nvidia-device-plugin
      volumes:
      - name: device-plugin-config
        configMap:
          name: device-plugin-config
```

```yaml
# 3. Time-Slicing GPU 사용 Pod
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime-ubuntu22.04
    command: ["nvidia-smi", "-L"]
    resources:
      limits:
        nvidia.com/gpu: 1  # 논리적 1 GPU (물리적 1/4)
```

**검증 명령어:**
```bash
# GPU 리소스 확인
kubectl describe node | grep nvidia.com/gpu

# 예상 출력: nvidia.com/gpu: 4 (1 물리 GPU * 4 replicas)

# Time-slicing 적용 확인
kubectl get pods -n nvidia-device-plugin
kubectl logs -n nvidia-device-plugin -l name=nvidia-device-plugin-ds
```

</details>

### 3. EKS Hybrid Node를 위한 nodeadm 설정 파일을 작성하세요.
- 클러스터 이름: hybrid-cluster
- 리전: ap-northeast-2
- 노드 레이블: `location=onprem`, `gpu=nvidia-a100`
- containerd가 온프레미스 Harbor(harbor.onprem.local)에서 이미지를 가져올 수 있도록 구성

<details>
<summary>정답 보기</summary>

```yaml
# nodeadm-config.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUM...
      # Base64 인코딩된 CA 인증서

  kubelet:
    config:
      maxPods: 110
      clusterDNS:
        - 10.100.0.10
    flags:
      - "--node-labels=location=onprem,gpu=nvidia-a100"
      - "--register-with-taints=dedicated=gpu:NoSchedule"

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
          [plugins."io.containerd.grpc.v1.cri".registry.mirrors."harbor.onprem.local"]
            endpoint = ["https://harbor.onprem.local"]

        [plugins."io.containerd.grpc.v1.cri".registry.configs]
          [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.onprem.local".tls]
            ca_file = "/etc/containerd/certs.d/harbor.onprem.local/ca.crt"
          [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.onprem.local".auth]
            username = "k8s-node"
            password = "NodePullSecret123"

  hybrid:
    # IAM Roles Anywhere 설정 (온프레미스 IAM 인증)
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
      certificatePath: /etc/pki/hybrid/node-cert.pem
      privateKeyPath: /etc/pki/hybrid/node-key.pem
```

**nodeadm 실행:**
```bash
# CA 인증서 배치
sudo mkdir -p /etc/containerd/certs.d/harbor.onprem.local/
sudo cp harbor-ca.crt /etc/containerd/certs.d/harbor.onprem.local/ca.crt

# nodeadm 초기화
sudo nodeadm init --config-source file://nodeadm-config.yaml

# 노드 상태 확인
kubectl get nodes -l location=onprem
```

</details>

## 심화 문제

### 1. 제조 기업이 공장의 엣지 서버에서 실시간 품질 검사 AI 모델을 실행하고자 합니다. EKS Hybrid Nodes, GPU(MIG), Harbor 레지스트리를 활용한 MLOps 파이프라인을 설계하세요. 모델 업데이트, 롤백, 모니터링 전략을 포함해야 합니다.

<details>
<summary>정답 보기</summary>

**제조 품질 검사 AI MLOps 파이프라인 설계**

**1. 아키텍처 개요:**

```
[클라우드 (AWS)]                    [엣지 (공장)]
┌─────────────────────┐            ┌─────────────────────┐
│  EKS Control Plane  │◄──VPN────►│  Hybrid Nodes       │
│  Harbor (Primary)   │            │  Harbor (Mirror)    │
│  MLflow             │            │  GPU Servers (A100) │
│  Model Registry     │            │  Inference Service  │
└─────────────────────┘            └─────────────────────┘
```

**2. Harbor 레지스트리 구성 (이중화):**

```yaml
# Harbor Replication 정책 (Cloud -> Edge)
apiVersion: v1
kind: ConfigMap
metadata:
  name: harbor-replication-config
data:
  policy.json: |
    {
      "name": "edge-model-sync",
      "src_registry": {"id": 0},
      "dest_registry": {
        "url": "https://harbor.factory.local",
        "credential_type": "basic",
        "access_key": "replicator"
      },
      "trigger": {"type": "event_based"},
      "filters": [
        {"type": "name", "value": "qc-models/**"},
        {"type": "tag", "value": "prod-*"}
      ],
      "enabled": true
    }
```

**3. GPU MIG 구성 (품질 검사 최적화):**

```yaml
# A100 MIG 설정 - 품질 검사 모델용
apiVersion: v1
kind: ConfigMap
metadata:
  name: mig-config
  namespace: nvidia-gpu-operator
data:
  config.yaml: |
    version: v1
    mig-configs:
      qc-inference:
        - devices: all
          mig-enabled: true
          mig-devices:
            "2g.10gb": 3  # 중형 모델 3개 동시 실행
      qc-mixed:
        - devices: [0]
          mig-enabled: true
          mig-devices:
            "3g.20gb": 1  # 대형 모델
            "1g.5gb": 2   # 소형 모델
```

**4. 추론 서비스 배포 (Canary):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qc-inference-stable
  namespace: qc-system
  labels:
    app: qc-inference
    version: stable
spec:
  replicas: 2
  selector:
    matchLabels:
      app: qc-inference
      version: stable
  template:
    metadata:
      labels:
        app: qc-inference
        version: stable
    spec:
      nodeSelector:
        location: onprem
        gpu: nvidia-a100
      containers:
      - name: inference
        image: harbor.factory.local/qc-models/defect-detector:prod-v2.1
        resources:
          limits:
            nvidia.com/mig-2g.10gb: 1
        ports:
        - containerPort: 8080
        env:
        - name: MODEL_NAME
          value: "defect_detector_v2.1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080

---
# Canary 배포 (신규 모델)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qc-inference-canary
  namespace: qc-system
  labels:
    app: qc-inference
    version: canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: qc-inference
      version: canary
  template:
    spec:
      containers:
      - name: inference
        image: harbor.factory.local/qc-models/defect-detector:prod-v2.2-rc1
```

**5. 트래픽 분산 (Istio):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: qc-inference-vs
spec:
  hosts:
  - qc-inference
  http:
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: qc-inference
        subset: canary
  - route:
    - destination:
        host: qc-inference
        subset: stable
      weight: 95
    - destination:
        host: qc-inference
        subset: canary
      weight: 5

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: qc-inference-dr
spec:
  host: qc-inference
  subsets:
  - name: stable
    labels:
      version: stable
  - name: canary
    labels:
      version: canary
```

**6. 자동 롤백 정책:**

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: qc-inference-canary
  namespace: qc-system
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: qc-inference-canary
  service:
    port: 8080
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: accuracy
      templateRef:
        name: model-accuracy
      thresholdRange:
        min: 0.95  # 95% 미만이면 롤백
    - name: latency-p99
      threshold: 200  # 200ms 초과 시 롤백
    - name: error-rate
      threshold: 1    # 1% 초과 시 롤백
    webhooks:
    - name: load-test
      url: http://flagger-loadtester/
      timeout: 5s
```

**7. 모니터링 및 알림:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: qc-model-alerts
spec:
  groups:
  - name: qc-inference.rules
    rules:
    - alert: ModelAccuracyDegraded
      expr: |
        qc_model_accuracy{model="defect_detector"} < 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "품질 검사 모델 정확도 저하"
        runbook: "https://wiki/runbooks/qc-model-accuracy"

    - alert: InferenceLatencyHigh
      expr: |
        histogram_quantile(0.99, rate(qc_inference_duration_seconds_bucket[5m])) > 0.2
      for: 3m
      labels:
        severity: warning

    - alert: GPUMemoryPressure
      expr: |
        nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes > 0.9
      for: 5m
      labels:
        severity: warning
```

**8. CI/CD 파이프라인:**

```yaml
# GitHub Actions Workflow
name: QC Model Deploy
on:
  push:
    tags:
      - 'model-v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Build Model Image
      run: |
        docker build -t harbor.cloud.local/qc-models/defect-detector:${{ github.ref_name }} .
        docker push harbor.cloud.local/qc-models/defect-detector:${{ github.ref_name }}

    - name: Trigger Edge Replication
      run: |
        curl -X POST "https://harbor.cloud.local/api/v2.0/replication/executions" \
          -H "Authorization: Basic ${{ secrets.HARBOR_AUTH }}" \
          -d '{"policy_id": 1}'

    - name: Update Canary Deployment
      run: |
        kubectl set image deployment/qc-inference-canary \
          inference=harbor.factory.local/qc-models/defect-detector:${{ github.ref_name }}

    - name: Monitor Canary
      run: |
        kubectl wait --for=condition=Promoted canary/qc-inference-canary --timeout=30m
```

</details>

### 2. 글로벌 AI 스타트업이 여러 지역(한국, 일본, 미국)에 분산된 GPU 리소스를 단일 EKS 클러스터로 관리하고자 합니다. Hybrid Nodes, DRA, 비용 최적화를 고려한 멀티 리전 GPU 리소스 관리 전략을 수립하세요.

<details>
<summary>정답 보기</summary>

**글로벌 GPU 리소스 관리 전략**

**1. 아키텍처 개요:**

```
                    ┌─────────────────────────┐
                    │  EKS Control Plane      │
                    │  (ap-northeast-2)       │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ 한국 (Seoul)   │     │ 일본 (Tokyo)  │     │ 미국 (Oregon) │
│ On-prem GPU   │     │ EC2 GPU       │     │ On-prem GPU   │
│ A100 x 8      │     │ p4d.24xl x 4  │     │ H100 x 16     │
│ Direct Connect│     │ Native Node   │     │ VPN           │
└───────────────┘     └───────────────┘     └───────────────┘
```

**2. DRA를 통한 GPU 리소스 추상화:**

```yaml
# GPU ResourceClass 정의 (지역별)
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: gpu-korea-a100
driverName: gpu.nvidia.com
parametersRef:
  apiGroup: gpu.nvidia.com
  kind: GpuClassParameters
  name: a100-params

---
apiVersion: gpu.nvidia.com/v1
kind: GpuClassParameters
metadata:
  name: a100-params
spec:
  sharing:
    strategy: TimeSlicing
    timeSlicingConfig:
      replicas: 4
  nodeSelector:
    topology.kubernetes.io/region: ap-northeast-2
    gpu.nvidia.com/gpu-model: A100

---
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: gpu-japan-p4d
driverName: gpu.nvidia.com
parametersRef:
  apiGroup: gpu.nvidia.com
  kind: GpuClassParameters
  name: p4d-params

---
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClass
metadata:
  name: gpu-us-h100
driverName: gpu.nvidia.com
parametersRef:
  apiGroup: gpu.nvidia.com
  kind: GpuClassParameters
  name: h100-params
```

**3. 스마트 GPU 스케줄러:**

```yaml
# 워크로드 유형별 GPU 선호도 정의
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpu-scheduler-config
data:
  policy.yaml: |
    # 추론 워크로드: 비용 최적화, 지연 시간 고려
    inference:
      preferredRegions:
        - ap-northeast-2  # 한국 사용자 우선
        - ap-northeast-1  # 일본 백업
      gpuPreference:
        - gpu-korea-a100  # 온프레미스 우선 (비용)
        - gpu-japan-p4d   # 클라우드 백업

    # 학습 워크로드: 성능 최적화
    training:
      preferredRegions:
        - us-west-2       # H100 있는 곳
      gpuPreference:
        - gpu-us-h100     # 최신 GPU
        - gpu-korea-a100

    # 배치 워크로드: 비용 최적화
    batch:
      preferredRegions:
        - any             # 가용한 곳 어디든
      gpuPreference:
        - gpu-korea-a100  # 온프레미스 우선
        - gpu-us-h100
        - gpu-japan-p4d   # Spot 인스턴스
```

**4. 워크로드별 ResourceClaim 템플릿:**

```yaml
# 추론 워크로드용
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClaimTemplate
metadata:
  name: inference-gpu-claim
spec:
  spec:
    resourceClassName: gpu-korea-a100
    parametersRef:
      apiGroup: gpu.nvidia.com
      kind: GpuClaimParameters
      name: inference-params

---
apiVersion: gpu.nvidia.com/v1
kind: GpuClaimParameters
metadata:
  name: inference-params
spec:
  count: 1
  requirements:
    memory: "5Gi"  # MIG 1g.5gb 수준
    computeCapability: "8.0"

---
# 학습 워크로드용
apiVersion: resource.k8s.io/v1alpha2
kind: ResourceClaimTemplate
metadata:
  name: training-gpu-claim
spec:
  spec:
    resourceClassName: gpu-us-h100
    parametersRef:
      apiGroup: gpu.nvidia.com
      kind: GpuClaimParameters
      name: training-params

---
apiVersion: gpu.nvidia.com/v1
kind: GpuClaimParameters
metadata:
  name: training-params
spec:
  count: 4
  requirements:
    memory: "80Gi"
    interconnect: "nvlink"  # GPU 간 고속 통신
```

**5. 비용 최적화 정책:**

```yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: gpu-spot-provisioner
spec:
  requirements:
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot", "on-demand"]
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["p4d.24xlarge", "p3.16xlarge"]
  - key: topology.kubernetes.io/zone
    operator: In
    values: ["ap-northeast-1a", "ap-northeast-1c"]

  # Spot 인스턴스 우선
  weight: 100

  limits:
    resources:
      nvidia.com/gpu: 32

  # 비용 최적화: 사용 안하면 빠르게 축소
  ttlSecondsAfterEmpty: 300
  ttlSecondsUntilExpired: 2592000  # 30일

---
# 비용 기반 스케줄링 우선순위
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: cost-optimized-batch
value: 100
preemptionPolicy: Never
globalDefault: false
description: "Low priority batch jobs using spot/on-prem GPUs"

---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: latency-critical-inference
value: 1000
preemptionPolicy: PreemptLowerPriority
description: "High priority inference with preemption rights"
```

**6. 글로벌 부하 분산:**

```yaml
# Istio 기반 지역 인식 라우팅
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: global-inference-routing
spec:
  hosts:
  - inference.global.ai-startup.com
  http:
  - match:
    - headers:
        x-client-region:
          exact: "APAC"
    route:
    - destination:
        host: inference.ap-northeast-2.svc.cluster.local
      weight: 80
    - destination:
        host: inference.ap-northeast-1.svc.cluster.local
      weight: 20
  - match:
    - headers:
        x-client-region:
          exact: "US"
    route:
    - destination:
        host: inference.us-west-2.svc.cluster.local
  # 기본: 지연 시간 기반 라우팅
  - route:
    - destination:
        host: inference.ap-northeast-2.svc.cluster.local
```

**7. 비용 모니터링 및 최적화:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gpu-cost-optimization
spec:
  groups:
  - name: gpu.cost.rules
    rules:
    # GPU 유휴 시간 감지
    - alert: GPUUnderutilized
      expr: |
        avg_over_time(DCGM_FI_DEV_GPU_UTIL[1h]) < 20
      for: 2h
      labels:
        severity: info
      annotations:
        summary: "GPU 사용률 20% 미만 - 비용 최적화 검토 필요"

    # 온프레미스 vs 클라우드 비용 비교
    - record: gpu:cost:hourly
      expr: |
        # 클라우드 GPU 시간당 비용
        sum(kube_pod_container_resource_requests{resource="nvidia.com/gpu"}
          * on(node) group_left()
          kube_node_labels{label_node_kubernetes_io_instance_type=~"p4d.*"}) * 32.77
        +
        # 온프레미스는 고정 비용으로 계산 (감가상각)
        sum(kube_pod_container_resource_requests{resource="nvidia.com/gpu"}
          * on(node) group_left()
          kube_node_labels{label_location="onprem"}) * 5.00

    # 지역별 GPU 사용량
    - record: gpu:usage:by_region
      expr: |
        sum(DCGM_FI_DEV_GPU_UTIL) by (kubernetes_node)
        * on(kubernetes_node) group_left(region)
        kube_node_labels
```

**8. 재해 복구 및 페일오버:**

```yaml
# 지역 장애 시 자동 페일오버
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: inference-global-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: global-inference

---
# 지역별 최소 복제본 보장
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 6
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 2
        topologyKey: topology.kubernetes.io/region
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: global-inference
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["onprem"]  # 온프레미스 우선 (비용)
          - weight: 50
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values: ["spot"]    # Spot 차선
```

**비용 절감 예상:**
- 온프레미스 GPU 활용: 클라우드 대비 60% 절감
- Spot 인스턴스: 온디맨드 대비 70% 절감
- 지역 기반 라우팅: 데이터 전송 비용 40% 절감
- 유휴 GPU 최적화: 추가 20% 절감

</details>
