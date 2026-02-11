# EKS 클러스터 생성

Amazon EKS 클러스터를 생성하는 방법은 여러 가지가 있습니다. 이 장에서는 다양한 도구와 방법을 사용하여 EKS 클러스터를 생성하는 방법을 자세히 알아보겠습니다.

## 목차

1. [사전 요구 사항](#사전-요구-사항)
2. [eksctl을 사용한 클러스터 생성](#eksctl을-사용한-클러스터-생성)
3. [AWS Management Console을 사용한 클러스터 생성](#aws-management-console을-사용한-클러스터-생성)
4. [AWS CLI를 사용한 클러스터 생성](#aws-cli를-사용한-클러스터-생성)
5. [Terraform을 사용한 클러스터 생성](#terraform을-사용한-클러스터-생성)
6. [AWS CDK를 사용한 클러스터 생성](#aws-cdk를-사용한-클러스터-생성)
7. [클러스터 액세스 구성](#클러스터-액세스-구성)
8. [클러스터 검증](#클러스터-검증)
9. [클러스터 업그레이드](#클러스터-업그레이드)
10. [클러스터 삭제](#클러스터-삭제)

## 사전 요구 사항

EKS 클러스터를 생성하기 전에 다음과 같은 사전 요구 사항이 필요합니다:

### 1. AWS 계정

유효한 AWS 계정이 필요합니다. AWS 계정이 없는 경우 [AWS 웹사이트](https://aws.amazon.com/)에서 가입할 수 있습니다.

### 2. IAM 권한

EKS 클러스터를 생성하고 관리하려면 다음과 같은 IAM 권한이 필요합니다:

- `eks:*`
- `ec2:*`
- `iam:*`
- `cloudformation:*`

관리자 권한이 있는 경우 추가 권한 설정이 필요하지 않습니다. 그렇지 않은 경우 다음과 같은 IAM 정책을 사용자 또는 역할에 연결해야 합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:*",
        "ec2:*",
        "iam:*",
        "cloudformation:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. 도구 설치

EKS 클러스터를 생성하고 관리하기 위해 다음과 같은 도구를 설치해야 합니다:

#### AWS CLI

AWS CLI는 AWS 서비스를 명령줄에서 제어하기 위한 통합 도구입니다.

**macOS**:
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux**:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows**:
```
https://awscli.amazonaws.com/AWSCLIV2.msi
```

AWS CLI 설치 후 다음 명령을 실행하여 자격 증명을 구성합니다:
```bash
aws configure
```

#### kubectl

kubectl은 Kubernetes 클러스터와 통신하기 위한 명령줄 도구입니다.

**macOS**:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Linux**:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Windows**:
```bash
curl -LO "https://dl.k8s.io/release/v1.26.0/bin/windows/amd64/kubectl.exe"
```

#### eksctl

eksctl은 EKS 클러스터를 생성하고 관리하기 위한 간단한 CLI 도구입니다.

**macOS**:
```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

또는:
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Linux**:
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Windows**:
```bash
# PowerShell
$version = (Invoke-WebRequest -Uri "https://api.github.com/repos/weaveworks/eksctl/releases/latest" | ConvertFrom-Json).tag_name
Invoke-WebRequest -Uri "https://github.com/weaveworks/eksctl/releases/download/$version/eksctl_Windows_amd64.zip" -OutFile eksctl.zip
Expand-Archive -Path eksctl.zip -DestinationPath $env:USERPROFILE\.eksctl\bin
$env:PATH += ";$env:USERPROFILE\.eksctl\bin"
```

### 4. VPC 및 서브넷

EKS 클러스터는 VPC와 서브넷이 필요합니다. 기존 VPC를 사용하거나 새 VPC를 생성할 수 있습니다. EKS 클러스터를 위한 VPC는 다음 요구 사항을 충족해야 합니다:

- 최소 2개의 서브넷이 서로 다른 가용 영역에 있어야 합니다.
- 서브넷에는 인터넷 액세스가 필요합니다(NAT 게이트웨이 또는 인터넷 게이트웨이를 통해).
- 서브넷에는 충분한 IP 주소가 있어야 합니다.
- 서브넷에는 적절한 태그가 지정되어야 합니다.

#### EKS 클러스터를 위한 VPC 태그

EKS 클러스터가 VPC 및 서브넷을 올바르게 사용할 수 있도록 다음과 같은 태그를 지정해야 합니다:

**VPC 태그**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` 또는 `owned`

**퍼블릭 서브넷 태그**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` 또는 `owned`
- `kubernetes.io/role/elb`: `1`

**프라이빗 서브넷 태그**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` 또는 `owned`
- `kubernetes.io/role/internal-elb`: `1`

## eksctl을 사용한 클러스터 생성

eksctl은 EKS 클러스터를 생성하고 관리하기 위한 가장 간단한 방법입니다. eksctl은 CloudFormation을 사용하여 EKS 클러스터와 관련 리소스를 생성합니다.

### 기본 클러스터 생성

가장 기본적인 형태의 EKS 클러스터를 생성하려면 다음 명령을 실행합니다:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

이 명령은 다음과 같은 기본 설정으로 클러스터를 생성합니다:
- 2개의 m5.large 노드
- 새로운 VPC 및 서브넷
- 기본 Amazon Linux 2 AMI
- 최신 Kubernetes 버전

### 구성 파일을 사용한 클러스터 생성

더 복잡한 구성의 경우 YAML 파일을 사용하여 클러스터를 정의할 수 있습니다:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-west-2
  version: "1.26"

vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432

managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    privateNetworking: true
    volumeSize: 80
    volumeType: gp3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: true
        ebs: true
        fsx: true
        efs: true
        albIngress: true
        xRay: true
        cloudWatch: true

  - name: ng-2
    instanceType: c5.xlarge
    desiredCapacity: 2
    privateNetworking: true
    spot: true

autoModeConfig:
  enabled: true
  # 기본 노드 풀 생성 (general-purpose, system)
  # nodePools를 지정하지 않으면 기본값 사용
  # nodePools: ["general-purpose", "system"]
  # nodeRoleARN: arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole

fargate:
  profiles:
    - name: fp-default
      selectors:
        - namespace: default
          labels:
            env: fargate
    - name: fp-kube-system
      selectors:
        - namespace: kube-system
          labels:
            k8s-app: kube-dns

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
```

이 구성 파일을 사용하여 클러스터를 생성하려면 다음 명령을 실행합니다:

```bash
eksctl create cluster -f cluster.yaml
```

### 관리형 노드 그룹 생성

기존 클러스터에 관리형 노드 그룹을 추가하려면 다음 명령을 실행합니다:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --ssh-access \
  --ssh-public-key my-key
```

또는 구성 파일을 사용할 수 있습니다:

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

managedNodeGroups:
  - name: my-nodegroup
    instanceType: m5.large
    desiredCapacity: 3
    minSize: 1
    maxSize: 5
    volumeSize: 80
    volumeType: gp3
    ssh:
      allow: true
      publicKeyName: my-key
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### EKS Auto Mode 클러스터 생성

EKS Auto Mode는 2024년에 출시된 새로운 기능으로, Kubernetes 클러스터 인프라를 자동화하여 운영 오버헤드를 크게 줄입니다. Auto Mode는 컴퓨팅, 네트워킹, 스토리지 등의 인프라 관리를 AWS가 자동으로 처리합니다.

#### EKS Auto Mode의 주요 특징

- **자동화된 노드 관리**: 워크로드 요구사항에 따라 자동으로 노드를 추가/제거
- **보안 강화**: 불변 AMI, SELinux 강제 모드, 읽기 전용 루트 파일 시스템
- **자동 업그레이드**: 21일 최대 노드 수명으로 정기적인 보안 패치 및 업데이트
- **통합 구성 요소**: Pod 네트워킹, DNS, 스토리지, GPU 지원 등이 기본 제공
- **비용 최적화**: 사용하지 않는 인스턴스 자동 종료 및 워크로드 통합

#### 기본 Auto Mode 클러스터 생성

```bash
eksctl create cluster --name my-auto-cluster --enable-auto-mode --region us-west-2
```

#### 구성 파일을 사용한 Auto Mode 클러스터 생성

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-auto-cluster
  region: us-west-2
  version: "1.31"

# EKS Auto Mode 구성
autoModeConfig:
  enabled: true
  # 기본 노드 풀 생성 (general-purpose, system)
  # nodePools를 지정하지 않으면 기본값 사용
  # nodePools: ["general-purpose", "system"]
  # nodeRoleARN: arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole

# VPC 구성 (선택사항)
vpc:
  cidr: "10.0.0.0/16"
  nat:
    gateway: Single # 또는 HighlyAvailable
  clusterEndpoints:
    privateAccess: true
    publicAccess: true

# 클러스터 로깅
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]

# 애드온 구성
addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
```

클러스터 생성:
```bash
eksctl create cluster -f auto-cluster.yaml
```

#### Auto Mode vs 기존 방식 비교

| 기능 | 기존 EKS | EKS Auto Mode |
|------|----------|---------------|
| 노드 관리 | 수동 관리형 노드 그룹 | 자동 노드 관리 |
| 스케일링 | Cluster Autoscaler 설정 필요 | 자동 스케일링 내장 |
| 업그레이드 | 수동 업그레이드 | 자동 업그레이드 (21일 주기) |
| 보안 | 사용자 구성 | 강화된 보안 기본 제공 |
| 네트워킹 | CNI 플러그인 설정 | 자동 네트워킹 구성 |
| 스토리지 | CSI 드라이버 설치 필요 | EBS CSI 자동 제공 |
| GPU 지원 | 수동 드라이버 설치 | 자동 GPU 지원 |

#### Auto Mode 클러스터 검증

클러스터가 생성된 후 다음 명령으로 상태를 확인할 수 있습니다:

```bash
# 클러스터 상태 확인
kubectl get nodes

# Auto Mode 노드 풀 확인
kubectl get nodepools

# Auto Mode 노드 클래스 확인
kubectl get nodeclasses

# 시스템 파드 상태 확인
kubectl get pods -n kube-system
```

#### 커스텀 노드 풀 생성

Auto Mode에서는 기본 노드 풀 외에 커스텀 노드 풀을 생성할 수 있습니다:

```yaml
apiVersion: karpenter.k8s.aws/v1beta1
kind: NodePool
metadata:
  name: gpu-nodepool
spec:
  template:
    metadata:
      labels:
        workload-type: gpu
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["p3.2xlarge", "p3.8xlarge"]
      nodeClassRef:
        apiVersion: karpenter.k8s.aws/v1beta1
        kind: EC2NodeClass
        name: gpu-nodeclass
  limits:
    cpu: 1000
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: gpu-nodeclass
spec:
  amiFamily: AL2
  instanceStorePolicy: RAID0
  userData: |
    #!/bin/bash
    /etc/eks/bootstrap.sh my-auto-cluster
```

#### Auto Mode 제한사항

- SSH 또는 SSM을 통한 노드 직접 액세스 불가
- 노드 수명 최대 21일 (자동 교체)
- 기본 노드 풀 및 노드 클래스 수정 불가
- 특정 인스턴스 유형 제한 가능

#### Auto Mode 모니터링

Auto Mode 클러스터는 CloudWatch와 통합되어 자동으로 메트릭을 수집합니다:

```bash
# CloudWatch 메트릭 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/EKS \
  --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value=my-auto-cluster \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Average
```

### Fargate 프로필 생성

Fargate 프로필을 생성하려면 다음 명령을 실행합니다:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

또는 구성 파일을 사용할 수 있습니다:

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

fargate:
  profiles:
    - name: my-fargate-profile
      selectors:
        - namespace: default
          labels:
            env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### 클러스터 업데이트

eksctl을 사용하여 기존 클러스터를 업데이트할 수 있습니다:

```bash
# 클러스터 버전 업그레이드
eksctl upgrade cluster --name=my-cluster --version=1.27

# 노드 그룹 업그레이드
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### 클러스터 삭제

eksctl을 사용하여 클러스터를 삭제할 수 있습니다:

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## AWS Management Console을 사용한 클러스터 생성

AWS Management Console을 사용하여 EKS 클러스터를 생성하는 단계는 다음과 같습니다:

1. [AWS Management Console](https://console.aws.amazon.com/)에 로그인합니다.
2. "EKS"를 검색하거나 서비스 목록에서 "Elastic Kubernetes Service"를 선택합니다.
3. "클러스터" 페이지에서 "클러스터 생성" 버튼을 클릭합니다.

### EKS Auto Mode 클러스터 생성 (빠른 구성)

EKS Auto Mode를 사용하면 최소한의 구성으로 프로덕션 준비된 클러스터를 생성할 수 있습니다.

#### 1. 빠른 구성 선택

4. "빠른 구성" 옵션이 선택되어 있는지 확인합니다.
5. 다음 정보를 입력합니다:
   - **클러스터 이름**: 클러스터의 고유한 이름을 입력합니다.
   - **Kubernetes 버전**: 사용할 Kubernetes 버전을 선택합니다 (최신 버전 권장).

#### 2. IAM 역할 구성

6. **클러스터 IAM 역할** 선택:
   - 첫 번째 Auto Mode 클러스터인 경우 "권장 역할 생성" 옵션을 사용합니다.
   - 기존 역할이 있는 경우 재사용할 수 있습니다.
   - 권장 역할 이름: `AmazonEKSAutoClusterRole`

7. **노드 IAM 역할** 선택:
   - 첫 번째 Auto Mode 클러스터인 경우 "권장 역할 생성" 옵션을 사용합니다.
   - 권장 역할 이름: `AmazonEKSAutoNodeRole`

#### 3. 네트워킹 구성

8. **VPC 선택**:
   - 새 VPC 생성: "VPC 생성" 옵션을 선택하여 EKS용 새 VPC를 생성합니다.
   - 기존 VPC 사용: 이전에 생성한 EKS용 VPC를 선택합니다.

9. **서브넷 구성** (선택사항):
   - EKS Auto Mode는 자동으로 VPC의 프라이빗 서브넷을 선택합니다.
   - 필요에 따라 서브넷을 추가하거나 제거할 수 있습니다.

#### 4. 구성 검토 및 생성

10. **빠른 구성 기본값 보기**를 선택하여 모든 구성 값을 검토합니다.
11. **클러스터 생성**을 클릭합니다. (클러스터 생성에는 약 15분이 소요됩니다)

### 사용자 지정 구성을 사용한 클러스터 생성

더 세밀한 제어가 필요한 경우 사용자 지정 구성을 사용할 수 있습니다.

### 클러스터 구성

4. "클러스터 구성" 페이지에서 다음 정보를 입력합니다:
   - **클러스터 이름**: 클러스터의 고유한 이름을 입력합니다.
   - **Kubernetes 버전**: 사용할 Kubernetes 버전을 선택합니다.
   - **클러스터 서비스 역할**: 새 역할을 생성하거나 기존 역할을 선택합니다.
   - **EKS Auto Mode**: Auto Mode를 활성화하려면 체크박스를 선택합니다.
   - **태그**: 필요한 경우 태그를 추가합니다.
   - "다음" 버튼을 클릭합니다.

### 네트워킹 지정

5. "네트워킹 지정" 페이지에서 다음 정보를 입력합니다:
   - **VPC**: 새 VPC를 생성하거나 기존 VPC를 선택합니다.
   - **서브넷**: 클러스터에 사용할 서브넷을 선택합니다. 최소 2개의 서브넷이 서로 다른 가용 영역에 있어야 합니다.
   - **보안 그룹**: 클러스터에 사용할 보안 그룹을 선택합니다.
   - **클러스터 엔드포인트 액세스**: 클러스터 API 서버 엔드포인트에 대한 액세스를 구성합니다.
     - **퍼블릭**: 인터넷에서 API 서버에 액세스할 수 있습니다.
     - **프라이빗**: VPC 내에서만 API 서버에 액세스할 수 있습니다.
     - **퍼블릭 및 프라이빗**: 인터넷과 VPC 내에서 모두 API 서버에 액세스할 수 있습니다.
   - "다음" 버튼을 클릭합니다.

### 로깅 구성

6. "로깅 구성" 페이지에서 다음 정보를 입력합니다:
   - **컨트롤 플레인 로깅**: 활성화할 로그 유형을 선택합니다.
     - API 서버 로그
     - 감사 로그
     - 인증자 로그
     - 컨트롤러 관리자 로그
     - 스케줄러 로그
   - "다음" 버튼을 클릭합니다.

### 애드온 선택

7. "애드온 선택" 페이지에서 다음 정보를 입력합니다:
   - **Amazon VPC CNI**: 포드 네트워킹을 위한 CNI 플러그인입니다.
   - **CoreDNS**: 클러스터 내 DNS 서비스입니다.
   - **kube-proxy**: 네트워크 프록시 및 로드 밸런싱을 제공합니다.
   - **Amazon EBS CSI Driver**: EKS Auto Mode에서는 자동으로 포함됩니다.
   - "다음" 버튼을 클릭합니다.

### 검토 및 생성

8. "검토 및 생성" 페이지에서 구성을 검토하고 "생성" 버튼을 클릭합니다.

### Auto Mode가 아닌 클러스터의 노드 그룹 추가

EKS Auto Mode를 사용하지 않는 경우, 클러스터 생성 후 노드 그룹을 수동으로 추가해야 합니다.

### 노드 그룹 추가

1. "노드 그룹 구성" 페이지에서 다음 정보를 입력합니다:
   - **노드 그룹 이름**: 노드 그룹의 고유한 이름을 입력합니다.
   - **노드 IAM 역할**: 새 역할을 생성하거나 기존 역할을 선택합니다.
   - "다음" 버튼을 클릭합니다.

2. "컴퓨팅 및 크기 조정 구성 설정" 페이지에서 다음 정보를 입력합니다:
   - **AMI 유형**: 노드에 사용할 AMI 유형을 선택합니다.
   - **인스턴스 유형**: 노드에 사용할 EC2 인스턴스 유형을 선택합니다.
   - **디스크 크기**: 노드의 디스크 크기를 지정합니다.
   - **노드 수**: 최소, 최대 및 원하는 노드 수를 지정합니다.
   - "다음" 버튼을 클릭합니다.

3. "네트워킹 지정" 페이지에서 다음 정보를 입력합니다:
   - **서브넷**: 노드 그룹에 사용할 서브넷을 선택합니다.
   - **원격 액세스 구성**: SSH 액세스를 구성합니다.
   - "다음" 버튼을 클릭합니다.

4. "검토 및 생성" 페이지에서 구성을 검토하고 "생성" 버튼을 클릭합니다.

## AWS CLI를 사용한 클러스터 생성

AWS CLI를 사용하여 EKS 클러스터를 생성할 수 있습니다. 이 방법은 스크립트 자동화나 CI/CD 파이프라인에 유용합니다.

### EKS Auto Mode 클러스터 생성

#### 1. 클러스터 생성

```bash
# Auto Mode 클러스터 생성
aws eks create-cluster \
  --name my-auto-cluster \
  --version 1.31 \
  --role-arn arn:aws:iam::123456789012:role/AmazonEKSAutoClusterRole \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890 \
  --access-config authenticationMode=API_AND_CONFIG_MAP \
  --compute-config nodeRoleArn=arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole \
  --storage-config blockStorage='{enabled=true}' \
  --kubernetes-network-config ipFamily=ipv4 \
  --region us-west-2
```

#### 2. 클러스터 상태 확인

```bash
# 클러스터 상태 확인
aws eks describe-cluster --name my-auto-cluster --region us-west-2

# 클러스터가 ACTIVE 상태가 될 때까지 대기
aws eks wait cluster-active --name my-auto-cluster --region us-west-2
```

#### 3. kubeconfig 업데이트

```bash
# kubeconfig 업데이트
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2

# 클러스터 연결 확인
kubectl get nodes
```

### 기존 방식 클러스터 생성

Auto Mode를 사용하지 않는 경우의 클러스터 생성 방법입니다.

#### 기본 클러스터 생성

```bash
aws eks create-cluster \
  --name my-cluster \
  --version 1.31 \
  --role-arn arn:aws:iam::123456789012:role/eks-service-role \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,endpointConfigPrivateAccess=true,endpointConfigPublicAccess=true \
  --region us-west-2
```

#### 클러스터 상태 확인

```bash
aws eks describe-cluster --name my-cluster --region us-west-2
```

클러스터가 생성되면 상태가 `ACTIVE`로 변경됩니다. 이 과정은 약 10-15분이 소요됩니다.

#### kubeconfig 업데이트

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

#### 관리형 노드 그룹 생성

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --subnets subnet-12345 subnet-67890 \
  --instance-types m5.large \
  --ami-type AL2_x86_64 \
  --node-role arn:aws:iam::123456789012:role/NodeInstanceRole \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 \
  --remote-access ec2SshKey=my-key \
  --region us-west-2
```

#### 노드 그룹 상태 확인

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --region us-west-2
```

## Terraform을 사용한 클러스터 생성

Terraform을 사용하여 EKS 클러스터를 생성하면 인프라를 코드로 관리할 수 있습니다.

### EKS Auto Mode 클러스터 Terraform 구성

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# VPC 및 서브넷 데이터 소스
data "aws_vpc" "selected" {
  id = var.vpc_id
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
  
  tags = {
    Type = "Private"
  }
}

# EKS Auto Mode 클러스터
resource "aws_eks_cluster" "auto_mode" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = data.aws_subnets.private.ids
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  # EKS Auto Mode 구성
  compute_config {
    enabled      = true
    node_role_arn = aws_iam_role.node.arn
  }

  storage_config {
    block_storage {
      enabled = true
    }
  }

  access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]

  tags = var.tags
}

# 클러스터 IAM 역할
resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

# 노드 IAM 역할
resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "node_AmazonEKSWorkerNodePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_AmazonEKS_CNI_Policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_AmazonEC2ContainerRegistryReadOnly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node.name
}

# 변수 정의
variable "cluster_name" {
  description = "EKS 클러스터 이름"
  type        = string
  default     = "my-auto-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes 버전"
  type        = string
  default     = "1.31"
}

variable "region" {
  description = "AWS 리전"
  type        = string
  default     = "us-west-2"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "tags" {
  description = "리소스 태그"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-auto-mode"
  }
}

# 출력
output "cluster_endpoint" {
  description = "EKS 클러스터 엔드포인트"
  value       = aws_eks_cluster.auto_mode.endpoint
}

output "cluster_security_group_id" {
  description = "EKS 클러스터 보안 그룹 ID"
  value       = aws_eks_cluster.auto_mode.vpc_config[0].cluster_security_group_id
}

output "cluster_arn" {
  description = "EKS 클러스터 ARN"
  value       = aws_eks_cluster.auto_mode.arn
}
```

### Terraform 실행

```bash
# Terraform 초기화
terraform init

# 계획 확인
terraform plan -var="vpc_id=vpc-12345678"

# 적용
terraform apply -var="vpc_id=vpc-12345678"

# kubeconfig 업데이트
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2
```

### 기존 방식 Terraform 구성

Auto Mode를 사용하지 않는 경우의 Terraform 구성입니다:

```hcl
# 기존 방식 EKS 클러스터
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = data.aws_subnets.private.ids
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
  ]

  tags = var.tags
}

# 관리형 노드 그룹
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = data.aws_subnets.private.ids

  capacity_type  = "ON_DEMAND"
  instance_types = ["m5.large"]

  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]

  tags = var.tags
}
```

## AWS CDK를 사용한 클러스터 생성

AWS CDK(Cloud Development Kit)를 사용하여 EKS 클러스터를 생성할 수 있습니다.

### TypeScript를 사용한 EKS Auto Mode 클러스터

```typescript
// lib/eks-auto-mode-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC 가져오기 또는 생성
    const vpc = ec2.Vpc.fromLookup(this, 'VPC', {
      vpcId: 'vpc-12345678' // 기존 VPC ID
    });

    // 또는 새 VPC 생성
    // const vpc = new ec2.Vpc(this, 'EksVpc', {
    //   maxAzs: 3,
    //   natGateways: 1,
    // });

    // EKS Auto Mode 클러스터 생성
    const cluster = new eks.Cluster(this, 'AutoModeCluster', {
      clusterName: 'my-auto-cluster',
      version: eks.KubernetesVersion.V1_31,
      vpc: vpc,
      vpcSubnets: [
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        }
      ],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE,
      
      // Auto Mode 구성
      defaultCapacity: 0, // Auto Mode에서는 기본 용량을 0으로 설정
      
      // 로깅 활성화
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
    });

    // Auto Mode 활성화를 위한 커스텀 리소스
    const autoModeConfig = new cdk.CustomResource(this, 'AutoModeConfig', {
      serviceToken: this.createAutoModeProvider().serviceToken,
      properties: {
        ClusterName: cluster.clusterName,
        NodeRoleArn: this.createNodeRole().roleArn,
      },
    });

    // 출력
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
      description: 'EKS 클러스터 이름',
    });

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: cluster.clusterEndpoint,
      description: 'EKS 클러스터 엔드포인트',
    });
  }

  private createNodeRole(): iam.Role {
    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSWorkerNodePolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKS_CNI_Policy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEC2ContainerRegistryReadOnly'),
      ],
    });

    return nodeRole;
  }

  private createAutoModeProvider(): cdk.Provider {
    // Auto Mode 활성화를 위한 Lambda 함수
    const onEvent = new cdk.aws_lambda.Function(this, 'AutoModeHandler', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_9,
      handler: 'index.on_event',
      code: cdk.aws_lambda.Code.fromInline(`
import boto3
import json

def on_event(event, context):
    print(json.dumps(event))
    
    eks = boto3.client('eks')
    cluster_name = event['ResourceProperties']['ClusterName']
    node_role_arn = event['ResourceProperties']['NodeRoleArn']
    
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
        # Auto Mode 활성화 로직
        try:
            response = eks.update_cluster_config(
                name=cluster_name,
                computeConfig={
                    'enabled': True,
                    'nodeRoleArn': node_role_arn
                }
            )
            return {'PhysicalResourceId': cluster_name}
        except Exception as e:
            print(f"Error: {e}")
            raise e
    
    return {'PhysicalResourceId': cluster_name}
      `),
    });

    // Lambda 함수에 EKS 권한 부여
    onEvent.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'eks:UpdateClusterConfig',
        'eks:DescribeCluster',
      ],
      resources: ['*'],
    }));

    return new cdk.Provider(this, 'AutoModeProvider', {
      onEventHandler: onEvent,
    });
  }
}
```

### CDK 앱 진입점

```typescript
// bin/eks-auto-mode.ts
#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
```

### CDK 배포

```bash
# CDK 설치
npm install -g aws-cdk

# 프로젝트 초기화
cdk init app --language typescript

# 의존성 설치
npm install

# CDK 부트스트랩 (처음 한 번만)
cdk bootstrap

# 배포
cdk deploy

# kubeconfig 업데이트
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2
```

## 클러스터 액세스 구성

EKS 클러스터에 액세스하기 위해서는 적절한 권한과 구성이 필요합니다.

### kubeconfig 구성

```bash
# kubeconfig 업데이트
aws eks update-kubeconfig --name my-cluster --region us-west-2

# 특정 프로필 사용
aws eks update-kubeconfig --name my-cluster --region us-west-2 --profile my-profile

# 역할 ARN 사용
aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EKSAccessRole
```

### RBAC 구성

```yaml
# rbac.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/NodeInstanceRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

```bash
kubectl apply -f rbac.yaml
```

## 클러스터 검증

클러스터가 올바르게 생성되었는지 확인하는 방법입니다.

### 기본 검증

```bash
# 클러스터 정보 확인
kubectl cluster-info

# 노드 상태 확인
kubectl get nodes

# 시스템 파드 상태 확인
kubectl get pods -n kube-system

# 서비스 계정 확인
kubectl get serviceaccounts -n kube-system
```

### Auto Mode 특정 검증

```bash
# Auto Mode 노드 풀 확인
kubectl get nodepools

# Auto Mode 노드 클래스 확인
kubectl get nodeclasses

# Karpenter 상태 확인 (Auto Mode에서 사용)
kubectl get pods -n karpenter
```

### 샘플 애플리케이션 배포

```yaml
# sample-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
spec:
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

```bash
kubectl apply -f sample-app.yaml
kubectl get pods
kubectl get services
```

## 클러스터 업그레이드

EKS 클러스터의 Kubernetes 버전을 업그레이드하는 방법입니다.

### Auto Mode 클러스터 업그레이드

Auto Mode 클러스터는 자동으로 업그레이드되지만, 수동으로도 가능합니다:

```bash
# eksctl을 사용한 업그레이드
eksctl upgrade cluster --name my-auto-cluster --version 1.32

# AWS CLI를 사용한 업그레이드
aws eks update-cluster-version --name my-auto-cluster --kubernetes-version 1.32
```

### 기존 방식 클러스터 업그레이드

```bash
# 클러스터 업그레이드
eksctl upgrade cluster --name my-cluster --version 1.32

# 노드 그룹 업그레이드
eksctl upgrade nodegroup --cluster my-cluster --name my-nodegroup
```

## 클러스터 삭제

클러스터를 삭제하는 방법입니다.

### eksctl을 사용한 삭제

```bash
eksctl delete cluster --name my-cluster --region us-west-2
```

### AWS CLI를 사용한 삭제

```bash
# 노드 그룹 삭제 (Auto Mode가 아닌 경우)
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# 클러스터 삭제
aws eks delete-cluster --name my-cluster
```

### Terraform을 사용한 삭제

```bash
terraform destroy
```

### CDK를 사용한 삭제

```bash
cdk destroy
```

## 결론

EKS 클러스터 생성에는 여러 가지 방법이 있으며, 각각의 장단점이 있습니다:

- **EKS Auto Mode**: 최소한의 운영 오버헤드로 프로덕션 준비된 클러스터 제공
- **eksctl**: 간단하고 빠른 클러스터 생성
- **AWS Management Console**: GUI를 통한 직관적인 생성
- **AWS CLI**: 스크립트 자동화에 적합
- **Terraform**: 인프라를 코드로 관리
- **AWS CDK**: 프로그래밍 언어를 사용한 인프라 정의

프로덕션 환경에서는 EKS Auto Mode나 Terraform/CDK를 사용하여 일관되고 반복 가능한 인프라를 구축하는 것을 권장합니다.
