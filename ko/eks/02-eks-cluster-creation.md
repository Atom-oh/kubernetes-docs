# EKS 클러스터 생성

> **마지막 업데이트**: 2026년 9월 11일

Amazon EKS 클러스터를 생성하는 방법은 여러 가지가 있습니다. 이 장에서는 다양한 도구와 방법을 사용하여 EKS 클러스터를 생성하는 방법을 자세히 알아보겠습니다.

이 장의 생성 방법은 대안입니다. 한 방법을 선택해 새 전용 클러스터에 적용하고 같은 리소스를 여러 도구로 동시에 관리하지 않습니다. 예시 이름·계정·역할·VPC·서브넷·CIDR은 승인된 실제 값으로 바꿉니다. 별도 표시가 없는 셸 예제는 Bash 기준이며 선행 명령 실패 시 중단합니다. 실제 AWS 프로비저닝이나 워크로드 실측은 이 감사에서 수행하지 않았습니다.

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

필요한 권한은 생성 도구와 직접 관리할 리소스에 따라 달라집니다. `eks:*`, `ec2:*`, `iam:*`, `cloudformation:*`를 모든 리소스에 부여하는 정책을 필수 최소 권한으로 취급하지 않습니다.

| 작업 | 검토할 권한 범위 |
| --- | --- |
| EKS 클러스터·노드 그룹 관리 | 필요한 EKS 작업과 대상 리소스 |
| 기존 IAM 역할 전달 | 승인된 역할 ARN의 `iam:PassRole` 및 서비스 조건 |
| IAM 역할·정책·OIDC 제공자 생성 | 도구가 관리하는 IAM 리소스와 이름·태그 범위 |
| 네트워크 생성 | 새 VPC·서브넷·보안 그룹에 필요한 EC2 작업 |
| eksctl/CDK 사용 | 해당 CloudFormation 스택, 실행 역할, 부트스트랩 리소스 |

프로비저닝 사용자, 클러스터 서비스 역할, 노드 역할은 별개입니다. SCP·권한 경계·세션 정책도 적용됩니다. 합성된 템플릿/계획을 기준으로 조직의 프로비저닝 권한을 검토합니다. Auto Mode의 역할 요구 사항은 일반 노드 그룹과 다릅니다.

참고: [EKS IAM 작업과 리소스](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html), [Auto Mode 역할](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html).

### 3. 도구 설치

#### AWS CLI

[AWS CLI v2 공식 설치 지침](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)에서 OS/CPU에 맞는 패키지를 선택하고 서명 검증 절차를 따릅니다. 이전 v1/v2 설치가 있다면 업데이트·마이그레이션 절차를 먼저 확인합니다.

| 환경 | 공식 패키지/설치 방식 |
| --- | --- |
| macOS | 서명된 `AWSCLIV2.pkg` |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` 및 PGP 서명 검증 |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` 및 PGP 서명 검증 |
| Windows | 지원되는 Windows용 MSI 설치 프로그램 |

Linux x86_64 패키지를 ARM 시스템에 그대로 사용하지 않습니다. 설치 후 `aws --version`으로 실제 실행되는 CLI를 확인합니다. 조직에서 IAM Identity Center를 사용하는 경우 다음과 같이 승인된 프로필을 구성합니다. 다른 페더레이션 방식을 사용하는 조직은 그 절차를 따르며 장기 액세스 키를 전제로 하지 않습니다.

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

참고: [IAM Identity Center 인증](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html). 이후 명령에서도 승인된 계정·역할·리전을 유지합니다.

#### kubectl과 eksctl — Linux/macOS

이 장의 EKS 1.36 예제에는 kubectl **1.36.4**, eksctl **0.230.0**을 기준으로 합니다. kubectl은 서버와 같은 마이너 버전을 권장하며 허용되는 차이는 ±1 마이너입니다. 업스트림 `stable.txt`의 최신 마이너를 이전 EKS 클러스터에 무조건 설치하지 않습니다.

아래 Bash 예제는 AMD64/ARM64를 구분하고 공식 체크섬을 확인한 뒤 설치합니다. `curl`, `tar`, `awk`와 `sha256sum` 또는 `shasum`이 필요하며 `/usr/local/bin` 설치는 관리자 권한이 필요합니다. 다운로드/검증 실패 시 설치를 중단합니다.

```bash
(
  set -e
  case "$(uname -s)" in
    Linux) EKS_TOOL_OS=linux; EKS_ARCHIVE_OS=Linux ;;
    Darwin) EKS_TOOL_OS=darwin; EKS_ARCHIVE_OS=Darwin ;;
    *) printf 'Use the official installer for this operating system\n' >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64) EKS_TOOL_ARCH=amd64 ;;
    aarch64|arm64) EKS_TOOL_ARCH=arm64 ;;
    *) printf 'Select a supported CPU architecture\n' >&2; exit 1 ;;
  esac
  EKS_TOOL_ARCHIVE="eksctl_${EKS_ARCHIVE_OS}_${EKS_TOOL_ARCH}.tar.gz"
  EKS_TOOL_DIR=$(mktemp -d)
  : "${EKS_TOOL_DIR:?}"
  trap 'rm -f -- "$EKS_TOOL_DIR/kubectl" "$EKS_TOOL_DIR/kubectl.sha256" "$EKS_TOOL_DIR/eksctl" "$EKS_TOOL_DIR/eksctl_checksums.txt" "$EKS_TOOL_DIR/$EKS_TOOL_ARCHIVE" "$EKS_TOOL_DIR/selected.sha256"; rmdir -- "$EKS_TOOL_DIR"' EXIT
  cd "$EKS_TOOL_DIR" || exit 1
  verify_sha() {
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum --check "$1"
    else
      shasum -a 256 --check "$1"
    fi
  }
  EKS_KUBECTL_VERSION=v1.36.4
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl" -o kubectl || exit 1
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl.sha256" -o kubectl.sha256 || exit 1
  printf '%s  kubectl\n' "$(tr -d '[:space:]' < kubectl.sha256)" > selected.sha256
  verify_sha selected.sha256 || exit 1

  EKSCTL_VERSION=0.230.0
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/$EKS_TOOL_ARCHIVE" -o "$EKS_TOOL_ARCHIVE" || exit 1
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/eksctl_checksums.txt" -o eksctl_checksums.txt || exit 1
  awk -v name="$EKS_TOOL_ARCHIVE" '$2 == name {print; count++} END {if (count != 1) exit 1}' \
    eksctl_checksums.txt > selected.sha256 || exit 1
  verify_sha selected.sha256 || exit 1
  tar -xzf "$EKS_TOOL_ARCHIVE" eksctl || exit 1
  sudo install -m 0755 kubectl /usr/local/bin/kubectl || exit 1
  sudo install -m 0755 eksctl /usr/local/bin/eksctl || exit 1
  kubectl version --client
  eksctl version
)
```

공식 절차: [Linux kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/), [macOS kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/), [eksctl 설치](https://eksctl.io/installation/).

#### Windows

PowerShell에서 [공식 kubectl 설치 절차](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)를 따릅니다. 이 장의 AMD64 예제에는 [kubectl 1.36.4](https://dl.k8s.io/release/v1.36.4/bin/windows/amd64/kubectl.exe)와 같은 경로의 `.sha256` 파일을 사용합니다. [eksctl 0.230.0 릴리스](https://github.com/eksctl-io/eksctl/releases/tag/v0.230.0)에서 CPU에 맞는 Windows ZIP과 `eksctl_checksums.txt`를 선택합니다.

`Get-FileHash -Algorithm SHA256` 결과를 공식 해시와 비교하고 불일치하면 중단합니다. 검증 후 ZIP을 풀고 실행 파일 디렉터리를 PATH에 추가한 뒤 `kubectl version --client`, `eksctl version`을 확인합니다. PowerShell 구문을 Bash로 실행하지 않습니다.

AWS CLI 예제의 JSON 생성을 위해서는 `jq`도 준비합니다. 실제 다운로드·설치·로그인은 감사에서 실행하지 않았습니다.

### 4. VPC 및 서브넷

리전 EKS 클러스터에는 같은 VPC의 서로 다른 AZ에 있는 서브넷이 최소 2개 필요합니다. 각 클러스터 서브넷은 EKS용 IP가 최소 6개 남아 있어야 하며 AWS는 16개 이상을 권장합니다. 노드·Pod·로드 밸런서·업그레이드에 필요한 IP는 별도로 계획합니다. VPC DNS 호스트명과 DNS 해석도 활성화해야 합니다.

인터넷 경로가 모든 EKS 클러스터의 필수 조건은 아닙니다. 노드와 워크로드가 API·이미지·필요한 AWS 서비스에 접근할 수 있어야 하며, NAT/인터넷 경로나 필요한 VPC 엔드포인트 및 미러 이미지를 준비합니다. 프라이빗 Kubernetes 엔드포인트는 VPC 또는 연결된 네트워크에서 올바른 DNS·라우팅으로 접근합니다.

#### EKS 클러스터를 위한 VPC 태그

`kubernetes.io/cluster/<cluster-name>` VPC 태그는 오래된 클러스터의 레거시 방식이며 현재 EKS 생성의 보편적 필수 조건이 아닙니다. 로드 밸런서의 서브넷 자동 검색에는 선택한 컨트롤러의 규칙을 따릅니다:

- 퍼블릭 로드 밸런서용 서브넷: `kubernetes.io/role/elb=1`
- 내부 로드 밸런서용 서브넷: `kubernetes.io/role/internal-elb=1`

태그만으로 라우팅·보안 그룹·가용 IP가 구성되지는 않습니다. [VPC/서브넷 요구 사항](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)과 [인터넷 없이 운영하는 클러스터](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)를 확인합니다.

## eksctl을 사용한 클러스터 생성

eksctl은 EKS 클러스터를 생성하고 관리하기 위한 가장 간단한 방법입니다. eksctl은 CloudFormation을 사용하여 EKS 클러스터와 관련 리소스를 생성합니다.

eksctl의 kubeconfig는 이 셸의 전용 경로에 저장합니다.

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### 기본 클러스터 생성

검토한 구성 파일로 기본 클러스터를 생성합니다:

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

명령 실행 전에 아래 `cluster.yaml`을 읽고 수정합니다. EKS 1.36, AL2023, 기존 VPC 서브넷과 노드 그룹 용량을 명시하는 예제입니다. 예시 식별자와 문서용 CIDR을 승인된 실제 값으로 바꿉니다. 모든 eksctl 버전의 기본값을 설명하는 목록이 아닙니다.

### 구성 파일을 사용한 클러스터 생성

더 복잡한 구성의 경우 YAML 파일을 사용하여 클러스터를 정의할 수 있습니다:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: '1.36'
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
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
managedNodeGroups:
- name: ng-1
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
  privateNetworking: true
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
- name: ng-2
  instanceType: c5.xlarge
  desiredCapacity: 2
  privateNetworking: true
  spot: true
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
fargateProfiles:
- name: fp-default
  selectors:
  - namespace: default
    labels:
      env: fargate
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
```

이 구성 파일을 사용하여 클러스터를 생성하려면 다음 명령을 실행합니다:

```bash
eksctl create cluster -f cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

위 구성은 EC2 노드와 선택적 앱 Fargate 프로필을 보여 줍니다. CoreDNS는 EC2에 두며, Fargate로 옮기려면 프로필 외에 CoreDNS의 컴퓨팅 설정도 검토해야 합니다.

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
  --managed --node-ami-family AmazonLinux2023 --node-private-networking
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
  amiFamily: AmazonLinux2023
  privateNetworking: true
  disableIMDSv1: true
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### EKS Auto Mode 클러스터 생성

EKS Auto Mode는 2024년에 출시된 새로운 기능으로, Kubernetes 클러스터 인프라를 자동화하여 운영 오버헤드를 크게 줄입니다. Auto Mode는 컴퓨팅, 네트워킹, 스토리지 등의 인프라 관리를 AWS가 자동으로 처리합니다.

#### EKS Auto Mode의 주요 특징

- **자동화된 노드 관리**: 워크로드 요구사항에 따라 자동으로 노드를 추가/제거
- **보안 강화**: 불변 AMI, SELinux 강제 모드, 읽기 전용 루트 파일 시스템
- **노드 유지 보수**: 노드 만료·드리프트에 따라 교체합니다. 21일은 클러스터 마이너 버전 업그레이드 주기가 아닙니다
- **통합 구성 요소**: Pod 네트워킹, DNS, 스토리지, GPU 지원 등이 기본 제공
- **비용 최적화**: 사용하지 않는 인스턴스 자동 종료 및 워크로드 통합

#### 기본 Auto Mode 클러스터 생성

아래 `auto-cluster.yaml`의 CIDR과 네트워크 설정을 먼저 검토합니다. Auto Mode의 네트워킹·DNS·블록 스토리지를 자체 관리형 애드온으로 중복 설치하지 않습니다. 혼합 클러스터는 컴퓨팅별 배치와 구성 요소 적용 범위를 별도로 설계합니다.

```bash
eksctl create cluster --config-file auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### 구성 파일을 사용한 Auto Mode 클러스터 생성

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-auto-cluster
  region: us-west-2
  version: '1.36'
autoModeConfig:
  enabled: true
  nodePools:
  - system
  - general-purpose
vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: Single
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
accessConfig:
  authenticationMode: API
```

클러스터 생성:
```bash
eksctl create cluster -f auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Auto Mode vs 기존 방식 비교

| 기능 | 기존 EKS | EKS Auto Mode |
|------|----------|---------------|
| 노드 관리 | 관리형 노드 그룹 또는 고객 관리 노드 | AWS 관리형 노드 수명 주기 |
| 스케일링 | Cluster Autoscaler·자체 관리 Karpenter 등 구성 | 관리형 노드 자동 확장 |
| 업그레이드 | 제어면·노드·애드온을 계획하여 갱신 | 노드/관리 구성 요소를 AWS가 갱신; 제어면 마이너 버전은 지원 정책에 따라 계획 |
| 보안 | 사용자 구성 | 강화된 보안 기본 제공 |
| 네트워킹 | CNI 플러그인 설정 | 자동 네트워킹 구성 |
| 스토리지 | CSI 드라이버 설치·권한 필요 | 관리형 EBS 프로비저너 `ebs.csi.eks.amazonaws.com` |
| GPU 지원 | 호환되는 가속 AMI와 필요한 디바이스 플러그인 구성 | 지원 인스턴스의 드라이버·플러그인 관리 |

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
apiVersion: karpenter.sh/v1
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
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.2xlarge
        - p3.8xlarge
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 336h
      taints:
      - key: nvidia.com/gpu
        value: present
        effect: NoSchedule
  limits:
    cpu: '1000'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

> **참고**: Auto Mode에서는 `EC2NodeClass`, `amiFamily`, 커스텀 `userData`(`/etc/eks/bootstrap.sh`)를 사용할 수 없습니다. 노드 AMI와 부트스트랩은 AWS가 관리하며, 서브넷/보안 그룹/임시 스토리지 등은 `eks.amazonaws.com/v1` `NodeClass`로 정의합니다.

GPU 예제는 현재 공식 지원 목록에 있는 p3를 유지합니다. 실제 AZ 용량·할당량·GPU 메모리/모델 요구를 확인해야 합니다. GPU Pod는 `nvidia.com/gpu`를 요청하고 위 taint를 허용하도록 구성합니다. 이 YAML을 검토했으며 GPU 노드를 생성하거나 성능을 측정하지 않았습니다.

#### Auto Mode 제한사항

- SSH 또는 SSM을 통한 노드 직접 액세스 불가
- 기본 만료는 336시간(14일), `expireAfter` 설정 상한은 21일입니다. 드레인·PDB·NodePool 설정에 따른 차단과 기본 24시간 종료 유예를 함께 검토합니다
- 기본 노드 풀 및 노드 클래스 수정 불가
- 특정 인스턴스 유형 제한 가능

#### Auto Mode 모니터링

Auto Mode의 인프라 관리가 워크로드의 모든 CloudWatch 메트릭 수집을 자동 구성하는 것은 아닙니다. 아래 `cluster_node_count`는 `AWS/EKS`가 아니라 **ContainerInsights** 네임스페이스의 메트릭이며, Container Insights 수집 구성이 있어야 합니다. 환경에 맞는 수집 방식을 구성한 뒤 실제 데이터가 존재하는 기간을 조회합니다.

```bash
# Requires a configured Container Insights collection pipeline and metric data.
aws cloudwatch list-metrics --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --start-time "${METRICS_START_TIME:?Set a reviewed ISO8601 start time}" \
  --end-time "${METRICS_END_TIME:?Set a later ISO8601 end time}" \
  --period 3600 --statistics Average
```

빈 결과를 노드 수 0이나 Auto Mode 실패로 해석하지 않습니다. 수집·차원·시간 범위를 먼저 확인합니다. 이 감사에서는 CloudWatch 조회나 측정을 실행하지 않았습니다. [공식 Container Insights 메트릭 목록](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)을 참조합니다.

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
fargateProfiles:
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

[클러스터 업그레이드](#클러스터-업그레이드)에서 호환성과 단계별 절차를 확인합니다.

### 클러스터 삭제

[클러스터 삭제](#클러스터-삭제)에서 앱·데이터·소유 도구와 정리 순서를 확인합니다.

## AWS Management Console을 사용한 클러스터 생성

AWS Management Console을 사용하여 EKS 클러스터를 생성하는 단계는 다음과 같습니다:

1. [AWS Management Console](https://console.aws.amazon.com/)에 로그인합니다.
2. "EKS"를 검색하거나 서비스 목록에서 "Elastic Kubernetes Service"를 선택합니다.
3. "클러스터" 페이지에서 "클러스터 생성" 버튼을 클릭합니다.

### EKS Auto Mode 클러스터 생성 (빠른 구성)

EKS Auto Mode는 인프라 설정을 줄여 줍니다. 워크로드 신원·네트워크·용량·가용성·복구는 별도로 구성하고 검증해야 합니다.

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
     - **프라이빗**: VPC 또는 연결된 네트워크에서 올바른 DNS·라우팅으로 접근합니다.
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

아래 애드온은 일반 컴퓨팅 기준입니다. Auto Mode는 겹치는 네트워킹·DNS·블록 스토리지 기능을 관리하므로 클러스터의 컴퓨팅 유형에 맞게 구성 요소를 선택합니다.

7. "애드온 선택" 페이지에서 다음 정보를 입력합니다:
   - **Amazon VPC CNI**: 포드 네트워킹을 위한 CNI 플러그인입니다.
   - **CoreDNS**: 클러스터 내 DNS 서비스입니다.
   - **kube-proxy**: 네트워크 프록시 및 로드 밸런싱을 제공합니다.
   - **스토리지/네트워킹 애드온**: 일반 컴퓨팅에는 필요한 구성 요소와 IAM 권한을 설치합니다. Auto Mode의 관리형 EBS·네트워킹·DNS와 중복되는 구성 요소를 Auto Mode 노드에 설치하지 않습니다.
   - "다음" 버튼을 클릭합니다.

### 검토 및 생성

8. "검토 및 생성" 페이지에서 구성을 검토하고 "생성" 버튼을 클릭합니다.

### Auto Mode가 아닌 클러스터의 노드 그룹 추가

일반 EC2 컴퓨팅에는 클러스터 생성 후 노드 그룹을 추가합니다. Fargate 프로필 등 다른 지원 방식에는 별도 설정이 있으며, Auto Mode가 아닌 모든 클러스터에 관리형 노드 그룹이 필수인 것은 아닙니다.

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
   - **원격 액세스 구성**: 승인된 관리 경로에 필요한 경우에만 SSH를 설정하고 소스 보안 그룹을 검토합니다.
   - "다음" 버튼을 클릭합니다.

4. "검토 및 생성" 페이지에서 구성을 검토하고 "생성" 버튼을 클릭합니다.

## AWS CLI를 사용한 클러스터 생성

아래는 **새 클러스터** 생성 예제입니다. Auto Mode와 일반 클러스터 중 하나를 선택하고 두 생성 명령을 같은 이름으로 연속 실행하지 않습니다. Bash·`jq`·현재 AWS CLI v2와 승인된 AWS 역할이 필요합니다. 코드의 EKS 1.36은 확인한 예제 버전이며 다른 버전은 해당 리전의 지원·호환성을 먼저 확인합니다.

서브넷 두 개는 같은 VPC의 서로 다른 AZ에 있어야 합니다. DNS, 여유 IP, 보안 그룹, 노드의 이미지/서비스 접근 경로를 별도로 준비합니다. `endpointPrivateAccess`와 `endpointPublicAccess`가 실제 API 필드 이름입니다. 초기 생성자 관리자 권한은 이 전용 예제의 부트스트랩을 위한 것이며 후속 접근은 access entry로 관리합니다.

### 공통 입력 준비

선택한 모드의 클러스터 역할을 미리 생성하고 필요한 `iam:PassRole` 및 서비스 연결 역할 생성 권한을 확인합니다. 계정·리전·서브넷·승인 CIDR을 검토한 다음에만 생성 명령을 실행합니다.

```bash
: "${EKS_CLUSTER_NAME:?Choose a unique new cluster name}"
: "${EKS_REGION:?Choose the intended AWS region}"
: "${EKS_CLUSTER_ROLE_ARN:?Pre-created cluster role for the chosen mode}"
: "${EKS_SUBNET_A:?Existing subnet in the intended VPC}"
: "${EKS_SUBNET_B:?Existing subnet in a different AZ of the same VPC}"
: "${EKS_PUBLIC_API_CIDR:?Approved client CIDR, normally /32}"
EKS_CREATION_DIR=$(mktemp -d /tmp/eks-create.XXXXXX)
: "${EKS_CREATION_DIR:?}"
EKS_KUBECONFIG="$EKS_CREATION_DIR/kubeconfig"
unset EKS_CREATED_CLUSTER_ARN
aws sts get-caller-identity
```

### EKS Auto Mode 클러스터 생성

클러스터 역할은 `eks.amazonaws.com`에 대한 `sts:AssumeRole`·`sts:TagSession` 신뢰와 다음 정책이 필요합니다: `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy`, `AmazonEKSNetworkingPolicy` 또는 동등한 사용자 정책입니다.

노드 역할은 `ec2.amazonaws.com`을 신뢰하고 `AmazonEKSWorkerNodeMinimalPolicy`·`AmazonEC2ContainerRegistryPullOnly`를 사용합니다. 워크로드의 AWS 권한은 별도의 Pod Identity/IRSA 경로로 구성합니다. 컴퓨팅·로드 밸런싱·블록 스토리지를 함께 켜고 자체 관리형 기본 애드온 부트스트랩을 끕니다.

```bash
: "${EKS_AUTO_NODE_ROLE_ARN:?Pre-created Auto Mode node role}"
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  --arg nodeRole "$EKS_AUTO_NODE_ROLE_ARN" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: false,
  computeConfig: {
    enabled: true, nodePools: ["system", "general-purpose"], nodeRoleArn: $nodeRole
  },
  kubernetesNetworkConfig: {ipFamily: "ipv4", elasticLoadBalancing: {enabled: true}},
  storageConfig: {blockStorage: {enabled: true}}
}' > "${EKS_CREATION_DIR:?}/create-auto.json"
cat "$EKS_CREATION_DIR/create-auto.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-auto.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### 생성 완료와 접근 확인

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

Auto Mode는 필요한 워크로드가 아직 없다면 노드가 없을 수 있습니다. NodePool/NodeClass 상태와 이후 Pod 스케줄링을 확인합니다. 클러스터 `ACTIVE`는 애플리케이션 정상 동작이나 정해진 생성 시간을 보장하지 않습니다.

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### 일반 클러스터 생성

Auto Mode를 선택하지 않은 경우에만 이 대안을 사용합니다. 클러스터 역할에는 일반 EKS 클러스터 권한이 필요하며, EC2 노드 역할과 CNI/애드온 권한은 별도입니다. 기본 네트워킹 애드온을 부트스트랩하더라도 EBS CSI나 AWS LBC까지 설치되는 것은 아닙니다.

```bash
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: true,
  kubernetesNetworkConfig: {ipFamily: "ipv4"}
}' > "${EKS_CREATION_DIR:?}/create-standard.json"
cat "$EKS_CREATION_DIR/create-standard.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-standard.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### 생성 완료와 kubeconfig

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

#### 관리형 노드 그룹 생성

EC2 노드 역할에는 워커 노드·ECR 가져오기 권한을 준비하고, CNI에는 별도 역할이나 검토된 노드 역할 권한을 제공합니다. Auto Mode의 최소 노드 역할을 그대로 재사용하지 않습니다. 프라이빗 서브넷의 NAT 또는 필요한 VPC 엔드포인트도 준비되어 있어야 합니다. 아래는 AL2023 예제이며 SSH 공개를 기본 활성화하지 않습니다.

```bash
: "${EKS_MANAGED_NODE_ROLE_ARN:?Pre-created conventional EC2 node role}"
: "${EKS_NODEGROUP_NAME:?Unique managed node group name}"
aws eks create-nodegroup \
  --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" \
  --subnets "${EKS_SUBNET_A:?}" "${EKS_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --node-role "$EKS_MANAGED_NODE_ROLE_ARN" \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 --region "${EKS_REGION:?}"

aws eks wait nodegroup-active --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
aws eks describe-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version}' --output json
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodes
```

`minSize`/`maxSize`만으로 Pod 수요 기반 노드 자동 확장이 활성화되지는 않습니다. 상태와 헬스 오류를 확인한 뒤 Cluster Autoscaler 등 별도 구성 여부를 결정합니다. 생성 실패 시 기록한 이름·ARN과 관련 리소스를 확인하며, 감사에서는 이러한 생성·대기 명령을 실행하지 않았습니다.

참고: [CreateCluster API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html), [CreateNodegroup API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html), [Auto Mode IAM and creation](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

## Terraform을 사용한 클러스터 생성

아래 완결된 예제는 최초 apply 전에 Auto Mode 또는 일반 관리형 노드 그룹을 선택해 **새 클러스터 하나**를 만듭니다. 대안을 두 번째 클러스터 리소스로 덧붙이거나 기존 클러스터에서 마이그레이션 계획 없이 전환하지 않습니다. Terraform state와 provider lock 파일은 해당 배포에 속합니다.

### EKS Auto Mode 클러스터 Terraform 구성

`main.tf`로 저장합니다. AWS provider **6.64.0**, EKS **1.36**을 사용합니다. 기존 프라이빗 서브넷 ID를 명시하며 `Type=Private` 태그만으로 라우팅·연결성을 판단하지 않습니다. precondition은 plan에서 VPC/AZ 관계를 확인하지만 프라이빗 라우팅·서비스 엔드포인트·DNS·IP 여유·로드 밸런서 서브넷 태그까지 검증하지 않습니다.

Auto Mode는 컴퓨팅·로드 밸런싱·블록 스토리지를 함께 켜고 `bootstrap_self_managed_addons = false`를 지정해야 합니다. 클러스터 역할에는 `sts:TagSession`과 정책 5개를 포함합니다. IAM 연결 의존성은 EKS가 관리형 인프라를 삭제하는 동안 권한을 유지합니다.

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_partition" "current" {}
data "aws_subnet" "selected" {
  for_each = toset(var.private_subnet_ids)
  id       = each.value
}

locals {
  cluster_policies = var.enable_auto_mode ? toset([
    "AmazonEKSClusterPolicy",
    "AmazonEKSComputePolicy",
    "AmazonEKSBlockStoragePolicyV2",
    "AmazonEKSLoadBalancingPolicy",
    "AmazonEKSNetworkingPolicy",
  ]) : toset(["AmazonEKSClusterPolicy"])
  node_policies = var.enable_auto_mode ? toset([
    "AmazonEKSWorkerNodeMinimalPolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    ]) : toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    # Conventional bootstrap baseline; see the CNI role caveat in the text.
    "AmazonEKS_CNI_Policy",
  ])
}

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = var.enable_auto_mode ? ["sts:AssumeRole", "sts:TagSession"] : ["sts:AssumeRole"]
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  for_each   = local.cluster_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["sts:AssumeRole"]
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each   = local.node_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.node.name
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }
  bootstrap_self_managed_addons = !var.enable_auto_mode

  compute_config {
    enabled       = var.enable_auto_mode
    node_pools    = var.enable_auto_mode ? ["system", "general-purpose"] : null
    node_role_arn = var.enable_auto_mode ? aws_iam_role.node.arn : null
  }
  kubernetes_network_config {
    ip_family = "ipv4"
    elastic_load_balancing {
      enabled = var.enable_auto_mode
    }
  }
  storage_config {
    block_storage {
      enabled = var.enable_auto_mode
    }
  }
  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_api_cidrs
  }
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Keep policies attached until EKS finishes deleting managed infrastructure.
  depends_on = [
    aws_iam_role_policy_attachment.cluster,
    aws_iam_role_policy_attachment.node,
  ]
  lifecycle {
    precondition {
      condition = (
        alltrue([for subnet in data.aws_subnet.selected : subnet.vpc_id == var.vpc_id]) &&
        length(toset([for subnet in data.aws_subnet.selected : subnet.availability_zone])) >= 2
      )
      error_message = "Supply subnets in at least two AZs of the selected VPC."
    }
  }
  tags = var.tags
}

resource "aws_eks_node_group" "standard" {
  count           = var.enable_auto_mode ? 0 : 1
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = aws_eks_cluster.main.version
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"
  instance_types  = ["m5.large"]
  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }
  update_config {
    max_unavailable = 1
  }
  depends_on = [aws_iam_role_policy_attachment.node]
  tags       = var.tags
}

resource "aws_eks_access_entry" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.operator_role_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_eks_access_entry.operator.principal_arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}

variable "enable_auto_mode" {
  description = "Creation-time choice. Changing an existing cluster requires a separate migration plan."
  type        = bool
  default     = true
}
variable "cluster_name" {
  description = "Unique name for this new cluster."
  type        = string
}
variable "kubernetes_version" {
  description = "EKS-supported minor version; 1.36 is the reviewed example."
  type        = string
  default     = "1.36"
}
variable "region" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(distinct(var.private_subnet_ids)) >= 2
    error_message = "At least two distinct subnet IDs are required."
  }
}
variable "public_api_cidrs" {
  type = list(string)
  validation {
    condition = length(var.public_api_cidrs) > 0 && alltrue([
      for cidr in var.public_api_cidrs :
      can(cidrhost(cidr, 0)) && cidr != "0.0.0.0/0" && cidr != "::/0"
    ])
    error_message = "Supply reviewed client CIDRs instead of unrestricted public API access."
  }
}
variable "operator_role_arn" {
  description = "Existing approved IAM role allowed to administer this cluster."
  type        = string
}
variable "tags" {
  type = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-creation-example"
  }
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}
output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}
output "cluster_security_group_id" {
  value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}
output "cluster_arn" {
  value = aws_eks_cluster.main.arn
}
```

운영자 access entry는 승인된 IAM 역할에 클러스터 관리 권한을 부여하며 생성자에게 Kubernetes 관리자 권한을 자동 부여하지 않습니다. 운영자 역할은 미리 존재해야 하고 kubectl 사용자가 AssumeRole할 수 있어야 합니다.

일반 노드 대안은 초기 부트스트랩용 CNI 권한을 노드 역할에 포함합니다. 이는 공유 권한 경계이며 강화된 프로덕션 워크로드 신원 설계가 아닙니다. 프로덕션 사용 전에 별도 CNI 역할과 Pod의 IMDS 접근 제한을 검토합니다. 앱의 AWS 권한은 워크로드별 신원에 부여하고 관련 없는 애드온 권한을 모든 노드에 추가하지 않습니다.

### Terraform 실행

새 작업 디렉터리와 인증된 프로비저닝 역할을 사용합니다. 예시 ID·문서용 CIDR을 실제 리소스·승인된 클라이언트 CIDR로 바꿉니다. 기본 선택은 Auto Mode입니다:

```hcl
# terraform.tfvars — replace every example identifier before planning.
cluster_name       = "eks-docs-unique-name"
region             = "us-west-2"
vpc_id             = "vpc-0123456789abcdef0"
private_subnet_ids = ["subnet-0123456789abcdef0", "subnet-1123456789abcdef0"]
public_api_cidrs   = ["203.0.113.10/32"]
operator_role_arn  = "arn:aws:iam::111122223333:role/ApprovedOperator"
enable_auto_mode  = true
```

```bash
# Run in a new directory containing main.tf and the reviewed terraform.tfvars.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=reviewed.tfplan
# Apply only the plan you reviewed for the intended account/region/resources.
terraform apply reviewed.tfplan

: "${EKS_REGION:?Use the same region as terraform.tfvars}"
: "${EKS_OPERATOR_ROLE_ARN:?Use the same operator role as terraform.tfvars}"
aws eks update-kubeconfig --name "$(terraform output -raw cluster_name)" \
  --region "$EKS_REGION" --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

apply 전에 state/backend, IAM·네트워크 변경과 과금 리소스를 검토합니다. `terraform validate`는 AWS 계정 권한·할당량·라우팅·노드의 실제 워크로드 실행 가능성을 검증하지 않습니다. 노드 그룹의 최소·최대 크기만으로 Pod 수요 기반 오토스케일러가 설치되지 않습니다.

### 기존 방식 Terraform 구성

**새 일반 클러스터**에는 동일한 전체 `main.tf`를 사용하고 최초 plan 전에 `terraform.tfvars`를 다음과 같이 설정합니다:

```hcl
enable_auto_mode = false
```

Auto Mode 기능 3개를 모두 끄고 일반 네트워킹 애드온을 부트스트랩하며 일반 EC2 노드 권한과 AL2023 관리형 노드 그룹을 구성합니다. EBS CSI·AWS LBC·Metrics Server·노드 오토스케일러는 설치하지 않으므로 필요한 기능을 별도로 구성합니다. 배포 후 값을 바꾸면 인프라와 IAM이 변경되므로 별도 마이그레이션 검토가 필요합니다.

검증: Terraform **1.15.7**, 서명된 AWS provider **6.64.0**으로 로컬 `terraform validate`를 수행하여 오류·경고 0건을 확인했습니다. **plan·apply·AWS API 호출은 수행하지 않았습니다.** 두 모드 모두 배포 검증이 필요하며 프로덕션 준비 상태를 입증하는 예제가 아닙니다.

참고: [AWS provider EKS cluster](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_cluster.html.markdown) · [managed node group](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_node_group.html.markdown) · [Auto Mode role requirements](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)

## AWS CDK를 사용한 클러스터 생성

이 **새 스택** 예제는 `aws-cdk-lib/aws-eks-v2`로 네이티브 `AWS::EKS::Cluster`와 access entry를 생성합니다. Auto Mode 활성화용 Lambda 커스텀 리소스가 필요하지 않습니다. 이미 배포된 construct를 이 예제로 교체하는 일을 제자리 마이그레이션으로 간주하지 않습니다.

CDK 라이브러리 **2.269.0**, CLI **2.1141.0**, EKS **1.36**을 사용합니다. 합성 중 VPC 조회 없이 기존 프라이빗 서브넷 속성을 가져옵니다. 배포 전 서브넷/AZ 대응 관계, VPC DNS, 라우팅, 서비스 접근과 로드 밸런서 서브넷 태그를 확인해야 합니다. VPC를 가져오는 코드 자체가 이를 검증하지는 않습니다.

### TypeScript를 사용한 EKS Auto Mode 클러스터

`lib/eks-auto-mode-stack.ts`로 저장합니다. 승인된 기존 운영자 역할에만 이 클러스터의 관리자 접근을 부여합니다. 워크로드 권한은 별도로 구성합니다.

```typescript
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks-v2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface EksAutoModeProps extends cdk.StackProps {
  readonly clusterName: string;
  readonly vpcId: string;
  readonly privateSubnetIds: string[];
  readonly availabilityZones: string[];
  readonly publicApiCidrs: string[];
  readonly operatorRoleArn: string;
}

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EksAutoModeProps) {
    super(scope, id, props);

    if (props.privateSubnetIds.length < 2 ||
        props.privateSubnetIds.length !== props.availabilityZones.length ||
        new Set(props.availabilityZones).size < 2 ||
        props.publicApiCidrs.length === 0) {
      throw new Error('Supply corresponding private subnets/AZs in at least two AZs and approved API CIDRs');
    }
    const vpc = ec2.Vpc.fromVpcAttributes(this, 'Vpc', {
      vpcId: props.vpcId,
      availabilityZones: props.availabilityZones,
      privateSubnetIds: props.privateSubnetIds,
    });

    const clusterRole = new iam.Role(this, 'ClusterRole', {
      assumedBy: new iam.ServicePrincipal('eks.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSClusterPolicy',
        'AmazonEKSComputePolicy',
        'AmazonEKSBlockStoragePolicyV2',
        'AmazonEKSLoadBalancingPolicy',
        'AmazonEKSNetworkingPolicy',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });
    clusterRole.assumeRolePolicy!.addStatements(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('eks.amazonaws.com')],
      actions: ['sts:TagSession'],
    }));

    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSWorkerNodeMinimalPolicy',
        'AmazonEC2ContainerRegistryPullOnly',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });

    const cluster = new eks.Cluster(this, 'Cluster', {
      clusterName: props.clusterName,
      version: eks.KubernetesVersion.V1_36,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE.onlyFrom(...props.publicApiCidrs),
      defaultCapacityType: eks.DefaultCapacityType.AUTOMODE,
      bootstrapSelfManagedAddons: false,
      bootstrapClusterCreatorAdminPermissions: false,
      // All required policies/trust are defined above. Avoid adding the older
      // BlockStoragePolicy that CDK 2.269.0 otherwise attaches automatically.
      role: clusterRole.withoutPolicyUpdates(),
      compute: {
        nodePools: ['system', 'general-purpose'],
        nodeRole: nodeRole.withoutPolicyUpdates(),
      },
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    cluster.node.addDependency(clusterRole, nodeRole);
    cluster.grantClusterAdmin('OperatorAccess', props.operatorRoleArn);

    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.clusterEndpoint });
  }
}
```

클러스터 역할은 `sts:TagSession`과 `AmazonEKSBlockStoragePolicyV2`를 포함한 Auto Mode 정책 5개를 명시합니다. `withoutPolicyUpdates()`는 CDK 2.269.0이 이전 블록 스토리지 정책을 추가하는 것을 막으므로 필요한 권한 전체를 이 예제에서 제공할 책임이 있습니다. 의존성은 클러스터 삭제 완료까지 역할을 유지합니다. 노드 역할에는 Auto Mode 최소 워커 정책과 ECR 가져오기 정책만 부여합니다.

`bootstrapSelfManagedAddons: false`로 자체 관리형 네트워킹 애드온과의 중복을 피합니다. Auto Mode는 컴퓨팅·로드 밸런싱·블록 스토리지를 함께 관리합니다. 운영자 access entry는 클러스터 실행 역할과 별도로 생성됩니다.

### CDK 앱 진입점

`bin/eks-auto-mode.ts`로 저장하고 shebang을 첫 줄에 둡니다. 예시 계정·VPC·역할을 실수로 사용하지 않도록 환경변수를 필수 입력으로 받습니다.

```typescript
#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Set ${name} before synthesis/deployment`);
  return value;
}
function list(name: string): string[] {
  return required(name).split(',').map(value => value.trim()).filter(Boolean);
}
const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: required('CDK_DEFAULT_ACCOUNT'),
    region: required('CDK_DEFAULT_REGION'),
  },
  clusterName: required('EKS_CLUSTER_NAME'),
  vpcId: required('EKS_VPC_ID'),
  privateSubnetIds: list('EKS_PRIVATE_SUBNET_IDS'),
  availabilityZones: list('EKS_AVAILABILITY_ZONES'),
  publicApiCidrs: list('EKS_PUBLIC_API_CIDRS'),
  operatorRoleArn: required('EKS_OPERATOR_ROLE_ARN'),
});
```

### CDK 배포

새 프로젝트를 초기화한 뒤 위 두 파일을 저장하고 대상 계정/리전 값을 설정합니다. 인증된 승인 역할로 실행하며 배포 전에 합성된 IAM·네트워크 설정과 diff를 검토합니다. CDK 라이브러리와 CLI는 별도 패키지로 버전 번호가 같지 않습니다.

```bash
mkdir eks-auto-mode
cd eks-auto-mode
npx --yes --package aws-cdk@2.1141.0 cdk init app --language typescript
npm install --save-exact aws-cdk-lib@2.269.0 constructs@10.5.0
npm install --save-dev --save-exact aws-cdk@2.1141.0 typescript@5.9.3

# Save the source files above, then set the required environment values.
: "${CDK_DEFAULT_ACCOUNT:?Set the intended AWS account ID}"
: "${CDK_DEFAULT_REGION:?Set the intended AWS region}"
: "${EKS_CLUSTER_NAME:?Use a unique name for this new cluster}"
: "${EKS_VPC_ID:?}"
: "${EKS_PRIVATE_SUBNET_IDS:?Comma-separated existing subnet IDs}"
: "${EKS_AVAILABILITY_ZONES:?Corresponding comma-separated AZs}"
: "${EKS_PUBLIC_API_CIDRS:?Approved client CIDRs, normally /32}"
: "${EKS_OPERATOR_ROLE_ARN:?Existing operator role you may assume}"
# Export the variables so the CDK application receives them.
export CDK_DEFAULT_ACCOUNT CDK_DEFAULT_REGION EKS_CLUSTER_NAME EKS_VPC_ID
export EKS_PRIVATE_SUBNET_IDS EKS_AVAILABILITY_ZONES EKS_PUBLIC_API_CIDRS EKS_OPERATOR_ROLE_ARN

npx tsc --noEmit
npx cdk synth
# Bootstrap creates AWS resources; review the account/region and execution policy.
npx cdk bootstrap "aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION"
npx cdk diff
npx cdk deploy

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$CDK_DEFAULT_REGION" \
  --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

감사에서는 더미 식별자로 두 TypeScript 파일을 컴파일하고 로컬 합성을 수행했습니다. Auto Mode 기능 3개, 제한된 API CIDR, 필요한 역할과 운영자 access entry 1개를 확인했고 Lambda/커스텀 리소스는 생성되지 않았습니다. 필수 입력 누락도 거부되었습니다. **부트스트랩·조회·배포·클러스터 생성·AWS API 호출은 수행하지 않았으므로** 계정 할당량·네트워크·워크로드 가용성은 실제 배포 시 검증해야 합니다.

참고: [EKS V2 construct library](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html) · [Auto Mode cluster role](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html) · [Auto Mode creation](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

## 클러스터 액세스 구성

선택한 도구가 만든 클러스터 이름·리전·별도 kubeconfig 경로를 설정합니다. Terraform/CDK 예제에서는 승인된 운영자 역할을 `EKS_OPERATOR_ROLE_ARN`에 지정합니다. CLI 생성자 접근을 사용하면 생략할 수 있습니다. kubeconfig 생성 자체가 Kubernetes 권한을 부여하지는 않습니다.

```bash
: "${EKS_CLUSTER_NAME:?Use the selected cluster name}"
: "${EKS_REGION:?Use the selected region}"
: "${EKS_KUBECONFIG:?Set the dedicated kubeconfig path for this method}"
aws sts get-caller-identity
if [[ -n ${EKS_OPERATOR_ROLE_ARN:-} ]]; then
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig "$EKS_KUBECONFIG"
else
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --kubeconfig "$EKS_KUBECONFIG"
fi
eks_kubectl() {
  kubectl --kubeconfig "${EKS_KUBECONFIG:?}" "$@"
}
eks_kubectl config current-context
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query cluster.accessConfig.authenticationMode
```

### RBAC 구성

신규 IAM 접근은 access entry를 사용합니다. 아래는 기존 `dev` 네임스페이스의 조회 전용 새 역할 예제이며, 생성 도구가 관리하는 운영자 entry와 중복 생성하지 않습니다. 인증 모드는 `API` 또는 `API_AND_CONFIG_MAP`이어야 합니다. 기존 `aws-auth`는 deprecated이며 전체 ConfigMap을 덮어쓰지 않습니다. 전환이 필요하면 공식 이전 절차를 따릅니다.

```bash
# A new reader identity, distinct from the operator already granted by IaC.
: "${EKS_READER_ROLE_ARN:?Existing approved IAM role without an access entry yet}"
if eks_kubectl get namespace dev &&
   aws eks create-access-entry --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --principal-arn "$EKS_READER_ROLE_ARN" \
  --type STANDARD --kubernetes-groups eks-docs-readers; then
EKS_ACCESS_DIR=$(mktemp -d /tmp/eks-access.XXXXXX)
: "${EKS_ACCESS_DIR:?}"
cat > "$EKS_ACCESS_DIR/rbac.yaml" << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: eks-docs-reader
  namespace: dev
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-docs-readers
  namespace: dev
subjects:
- kind: Group
  name: eks-docs-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: eks-docs-reader
  apiGroup: rbac.authorization.k8s.io
EOF
eks_kubectl create -f "$EKS_ACCESS_DIR/rbac.yaml"
fi
```

조회 역할에는 Secret API나 변경 권한을 부여하지 않습니다. 실제 역할로 인증해 `kubectl auth can-i`를 확인하며 다른 RBAC/EKS 접근 정책의 허용이 합산될 수 있습니다.

참고: [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)

## 클러스터 검증

위 액세스 절차의 `eks_kubectl`과 같은 전용 kubeconfig를 사용합니다. 제어면 접근만으로 노드·워크로드 정상 상태를 판단하지 않습니다.

### 기본 검증

```bash
eks_kubectl cluster-info
eks_kubectl get nodes
eks_kubectl get pods -n kube-system
eks_kubectl get events --sort-by='.lastTimestamp'
```

### Auto Mode 특정 검증

Auto Mode 프로비저닝 컨트롤러는 AWS가 관리하므로 `karpenter` 네임스페이스의 자체 관리형 컨트롤러 Pod를 기대하지 않습니다. NodePool/NodeClass 상태·이벤트와 용량이 필요한 워크로드의 NodeClaim을 확인합니다.

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### 샘플 애플리케이션 배포

새 네임스페이스에서 이미지 접근·스케줄링·HTTP readiness·Service를 확인합니다. 순수 Fargate 구성에는 먼저 이 네임스페이스에 맞는 프로필이 필요합니다.

```bash
EKS_SAMPLE_DIR=$(mktemp -d /tmp/eks-validate.XXXXXX)
: "${EKS_SAMPLE_DIR:?}"
unset EKS_SAMPLE_NAMESPACE EKS_SAMPLE_UID
EKS_SAMPLE_CANDIDATE=$(basename "$EKS_SAMPLE_DIR" | tr '[:upper:].' '[:lower:]-')
if EKS_SAMPLE_UID=$(eks_kubectl create namespace "$EKS_SAMPLE_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  EKS_SAMPLE_NAMESPACE=$EKS_SAMPLE_CANDIDATE
fi
: "${EKS_SAMPLE_NAMESPACE:?Namespace creation failed}"
: "${EKS_SAMPLE_UID:?Namespace UID missing}"
cat > "$EKS_SAMPLE_DIR/sample-app.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: ${EKS_SAMPLE_NAMESPACE}
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
      automountServiceAccountToken: false
      containers:
      - name: app
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: http
EOF
eks_kubectl apply -f "$EKS_SAMPLE_DIR/sample-app.yaml"
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" rollout status deployment/sample-app --timeout=180s
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" get pods,services
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" port-forward --address 127.0.0.1 service/sample-app-service 8080:80
```

포트 포워딩 중 `http://127.0.0.1:8080`을 열고 Ctrl-C로 종료합니다. 이는 ClusterIP 접근 검증이며 외부 로드 밸런서 검증은 아닙니다. NLB에는 Auto Mode의 `eks.amazonaws.com/nlb` 또는 설치·권한 설정된 AWS LBC의 `service.k8s.aws/nlb`를 선택하고 네트워크·비용 조건을 별도로 확인합니다. 실제 배포나 포트 포워딩은 감사에서 실행하지 않았습니다.

## 클러스터 업그레이드

업그레이드 인사이트·제거 API·웹훅·애드온 호환성, 노드 버전, IP 여유와 복구 계획을 먼저 확인합니다. 오래된 노드를 현재 제어면 버전에 맞춘 뒤 다음 지원 마이너로 한 단계씩 진행합니다. 일부 구성 요소는 제어면보다 먼저 호환 버전으로 갱신해야 합니다.

Auto Mode가 제어면 마이너 버전을 21일마다 올리는 것은 아닙니다. 운영자가 버전 업그레이드를 계획하고 지원 정책에 따른 자동 업그레이드도 고려합니다.

```bash
aws eks describe-cluster-versions --region "${EKS_REGION:?}" --output table
aws eks describe-cluster --name "${EKS_CLUSTER_NAME:?}" --region "$EKS_REGION" \
  --query 'cluster.{version:version,status:status}' --output table
eks_kubectl get nodes

# After readiness/compatibility review, choose the next supported minor.
: "${NEXT_MINOR_VERSION:?Select one supported minor step, for example 1.35 to 1.36}"
EKS_UPDATE_ID=$(aws eks update-cluster-version --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --kubernetes-version "$NEXT_MINOR_VERSION" \
  --query update.id --output text)
: "${EKS_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --update-id "$EKS_UPDATE_ID" --query 'update.{status:status,errors:errors}'

# Alternative interface; do not execute both:
# eksctl upgrade cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" --version "$NEXT_MINOR_VERSION" --approve
```

업데이트가 `Successful`인지 확인한 후 데이터 플레인으로 진행합니다. Auto Mode 노드는 AWS가 점진적으로 갱신하며 일반 관리형 노드 그룹은 별도 업데이트가 필요합니다.

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

자체 관리형/Hybrid Nodes, Fargate Pod 재생성, 애드온·kubectl 갱신을 각 방식에 맞게 계획합니다. PDB와 여유 용량을 확인하고 실패를 강제 옵션으로 숨기지 않습니다. 조건을 만족하는 제어면 업그레이드는 완료 후 7일 이내 이전 마이너로 롤백할 수 있지만, 노드·애드온·API 호환성과 지원 정책 제약이 있으며 앱 데이터 복구를 대신하지 않습니다.

참고: [Upgrade procedure](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [Rollback conditions](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## 클러스터 삭제

삭제는 선택한 생성 도구의 원래 상태·계정·리전에서 수행합니다. 먼저 앱과 Ingress/LoadBalancer Service를 담당 컨트롤러가 실행 중일 때 제거하고 완료를 확인합니다. PVC/PV·스냅샷·로그의 보존·복구 결정을 먼저 내립니다. 타임아웃이나 finalizer 문제를 강제로 우회하지 않습니다.

### 실습 네임스페이스 정리

```bash
EKS_SAMPLE_CLEANUP_OK=true
if [[ -n ${EKS_SAMPLE_NAMESPACE:-} && -n ${EKS_SAMPLE_UID:-} ]]; then
  current_uid=$(eks_kubectl get namespace "$EKS_SAMPLE_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [[ "$current_uid" = "$EKS_SAMPLE_UID" ]]; then
    eks_kubectl delete namespace "$EKS_SAMPLE_NAMESPACE" --wait=true --timeout=180s || EKS_SAMPLE_CLEANUP_OK=false
  else
    EKS_SAMPLE_CLEANUP_OK=false
  fi
elif [[ -n ${EKS_SAMPLE_NAMESPACE:-} || -n ${EKS_SAMPLE_UID:-} ]]; then
  EKS_SAMPLE_CLEANUP_OK=false
fi
# Remove local files only after successful sample cleanup.
if [[ "$EKS_SAMPLE_CLEANUP_OK" = true ]]; then
if [[ -n ${EKS_SAMPLE_DIR:-} ]]; then
  rm -f -- "$EKS_SAMPLE_DIR/sample-app.yaml"
  rmdir -- "$EKS_SAMPLE_DIR"
fi
if [[ -n ${EKS_ACCESS_DIR:-} ]]; then
  rm -f -- "$EKS_ACCESS_DIR/rbac.yaml"
  rmdir -- "$EKS_ACCESS_DIR"
fi
else
  printf 'Sample cleanup could not be verified; stop before deleting the cluster\n' >&2
fi
```

정리가 실패하면 여기서 중단하고 원인을 해결합니다. 다음 ARN은 현재 조회 결과를 무조건 복사하지 말고 생성 결과나 소유한 IaC state의 값과 대조합니다.

```bash
: "${EKS_EXPECTED_CLUSTER_ARN:?Copy the ARN from the creation result or owning IaC state}"
: "${EKS_CLUSTER_NAME:?}"
: "${EKS_REGION:?}"
EKS_DELETE_TARGET_VERIFIED=false
if [[ ${EKS_SAMPLE_CLEANUP_OK:-false} != true ]]; then
  printf 'Complete the sample cleanup check above first\n' >&2
else
current_arn=$(aws eks describe-cluster --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --query cluster.arn --output text) || current_arn=""
if [[ "$current_arn" = "$EKS_EXPECTED_CLUSTER_ARN" ]]; then
  EKS_DELETE_TARGET_VERIFIED=true
  aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
else
  printf 'Target mismatch; stop and check the account, region and owning tool\n' >&2
fi
fi
```

### eksctl을 사용한 삭제

eksctl이 만든 클러스터에만 이 방법을 사용합니다.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### AWS CLI를 사용한 삭제

CLI로 직접 생성한 클러스터용입니다. 앞에서 조회한 소유 노드 그룹/프로필 이름을 설정하고 각 리소스에 대해 반복합니다. 삭제 완료를 기다리고 남은 리소스가 없는지 확인한 뒤 클러스터를 삭제합니다.

```bash
# For a cluster created directly with the AWS CLI, after workload/data cleanup.
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  if [[ -n ${EKS_NODEGROUP_NAME:-} ]]; then
    aws eks delete-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" &&
    aws eks wait nodegroup-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
  fi
  if [[ -n ${EKS_FARGATE_PROFILE_NAME:-} ]]; then
    aws eks delete-fargate-profile --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION" &&
    aws eks wait fargate-profile-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION"
  fi
  remaining_nodes=$(aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(nodegroups)' --output text) || remaining_nodes=unknown
  remaining_profiles=$(aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(fargateProfileNames)' --output text) || remaining_profiles=unknown
  if [[ "$remaining_nodes" = 0 && "$remaining_profiles" = 0 ]]; then
    aws eks delete-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" &&
      aws eks wait cluster-deleted --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  else
    printf 'Owned node groups/Fargate profiles remain, or their status could not be verified\n' >&2
  fi
fi
```

### Terraform을 사용한 삭제

원래 구성·backend·workspace에서 리소스와 계정을 검토한 삭제 계획만 적용합니다.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  terraform plan -destroy -out=reviewed-destroy.tfplan &&
    terraform apply reviewed-destroy.tfplan
fi
```

### CDK를 사용한 삭제

원래 앱·환경변수·계정·리전에서 대상 스택을 확인합니다.

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

완료 후 실제 EKS/CloudFormation 상태와 남은 ELB·디스크·NAT·로그·IAM 리소스를 확인합니다. Auto Mode 역할과 정책은 관리형 인프라 삭제가 끝날 때까지 유지합니다. VPC·IAM 역할·로그·보존 데이터가 다른 도구/소유자에게 속한다면 클러스터 삭제만으로 제거된다고 가정하지 않습니다. 감사에서는 삭제 명령을 실행하지 않았습니다.

## 결론

EKS 클러스터 생성에는 여러 가지 방법이 있으며, 각각의 장단점이 있습니다:

- **EKS Auto Mode**: 인프라 운영을 자동화하지만 앱의 운영 준비 상태는 별도 검증 필요
- **eksctl**: 간단하고 빠른 클러스터 생성
- **AWS Management Console**: GUI를 통한 직관적인 생성
- **AWS CLI**: 스크립트 자동화에 적합
- **Terraform**: 인프라를 코드로 관리
- **AWS CDK**: 프로그래밍 언어를 사용한 인프라 정의

프로덕션에서는 요구 사항에 맞는 컴퓨팅 모델과 인프라 도구를 선택하고 IAM·연결성·용량·중단·복구 동작을 검증합니다. 템플릿이나 클러스터 생성 성공만으로 운영 준비 상태가 입증되지는 않습니다.

### 감사 검증 범위

두 언어의 전체 문서를 읽고 공식 문서·스키마와 대조했습니다. 셸/JSON/YAML, CDK 컴파일·합성, Terraform validate 및 모의 실패 경로를 검증했습니다. AWS 프로비저닝·업그레이드·삭제, 실제 앱 실행·부하 시험·비용 측정은 수행하지 않았습니다.
