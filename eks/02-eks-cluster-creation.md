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

### 클러스터 구성

4. "클러스터 구성" 페이지에서 다음 정보를 입력합니다:
   - **클러스터 이름**: 클러스터의 고유한 이름을 입력합니다.
   - **Kubernetes 버전**: 사용할 Kubernetes 버전을 선택합니다.
   - **클러스터 서비스 역할**: 새 역할을 생성하거나 기존 역할을 선택합니다.
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
   - "다음" 버튼을 클릭합니다.

### 검토 및 생성

8. "검토 및 생성" 페이지에서 구성을 검토하고 "생성" 버튼을 클릭합니다.

클러스터 생성이 완료되면 "노드 그룹 추가" 버튼을 클릭하여 노드 그룹을 추가할 수 있습니다.

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
