# Amazon EKS 클러스터 생성 퀴즈 (Part 1)

이 퀴즈는 Amazon EKS 클러스터 생성과 관련된 개념, 도구, 모범 사례에 대한 이해를 테스트합니다. 클러스터 생성 방법, VPC 구성, 노드 그룹 설정 등의 주제를 다룹니다.

## 기본 개념 문제

1. Amazon EKS 클러스터를 생성하는 데 사용할 수 있는 도구가 아닌 것은 무엇인가요?
   - A) AWS Management Console
   - B) AWS CLI
   - C) eksctl
   - D) kubectl
   
<details>
<summary>정답 보기</summary>

**정답: D) kubectl**

**설명:**
kubectl은 Kubernetes 클러스터를 관리하기 위한 명령줄 도구이지만, EKS 클러스터를 생성하는 데 사용할 수 없습니다. kubectl은 이미 존재하는 Kubernetes 클러스터에 연결하여 리소스를 관리하는 데 사용됩니다.

Amazon EKS 클러스터를 생성하는 데 사용할 수 있는 도구는 다음과 같습니다:

1. **AWS Management Console**:
   - 웹 인터페이스를 통해 EKS 클러스터를 생성할 수 있습니다.
   - 시각적인 방식으로 클러스터 구성 요소를 설정할 수 있어 초보자에게 적합합니다.
   - 단계별 마법사를 통해 클러스터 생성 과정을 안내합니다.

2. **AWS CLI**:
   - 명령줄에서 EKS 클러스터를 생성할 수 있습니다.
   - `aws eks create-cluster` 명령을 사용합니다.
   - 스크립트 및 자동화에 적합합니다.
   ```bash
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
   ```

3. **eksctl**:
   - EKS 클러스터 생성을 위해 특별히 설계된 명령줄 도구입니다.
   - Weaveworks에서 개발한 오픈 소스 도구로, EKS 클러스터 생성 및 관리를 단순화합니다.
   - 단일 명령으로 클러스터를 생성할 수 있습니다.
   ```bash
   eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
   ```

4. **Infrastructure as Code (IaC) 도구**:
   - AWS CloudFormation
   - Terraform
   - AWS CDK
   - Pulumi
   
   이러한 도구를 사용하면 코드로 EKS 클러스터를 정의하고 배포할 수 있습니다.

kubectl은 클러스터가 생성된 후에 Kubernetes 리소스(포드, 서비스, 배포 등)를 관리하는 데 사용됩니다. EKS 클러스터에 연결하려면 먼저 `aws eks update-kubeconfig` 명령을 사용하여 kubectl 구성을 업데이트해야 합니다.

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

이후에 kubectl을 사용하여 클러스터 리소스를 관리할 수 있습니다.
</details>

2. Amazon EKS 클러스터를 생성할 때 필수적으로 지정해야 하는 VPC 구성 요소는 무엇인가요?
   - A) 퍼블릭 서브넷만
   - B) 프라이빗 서브넷만
   - C) 최소 2개의 가용 영역에 걸친 서브넷
   - D) NAT 게이트웨이
   
<details>
<summary>정답 보기</summary>

**정답: C) 최소 2개의 가용 영역에 걸친 서브넷**

**설명:**
Amazon EKS 클러스터를 생성할 때 필수적으로 지정해야 하는 VPC 구성 요소는 최소 2개의 가용 영역에 걸친 서브넷입니다. 이는 EKS 클러스터의 고가용성을 보장하기 위한 AWS의 요구 사항입니다.

#### EKS 클러스터 VPC 요구 사항:

1. **최소 2개의 가용 영역(AZ)에 서브넷 필요**:
   - EKS 컨트롤 플레인은 여러 가용 영역에 걸쳐 배포되므로, 클러스터 생성 시 최소 2개의 가용 영역에 서브넷을 지정해야 합니다.
   - 이는 단일 가용 영역 장애 시에도 클러스터가 계속 작동할 수 있도록 보장합니다.

2. **서브넷 유형**:
   - 퍼블릭 서브넷만 사용하거나, 프라이빗 서브넷만 사용하거나, 또는 퍼블릭과 프라이빗 서브넷을 혼합하여 사용할 수 있습니다.
   - 프로덕션 환경에서는 보안을 위해 프라이빗 서브넷에 워커 노드를 배치하고, 퍼블릭 서브넷은 로드 밸런서용으로 사용하는 것이 권장됩니다.

3. **서브넷 CIDR 크기**:
   - 각 서브넷은 충분한 IP 주소를 가져야 합니다.
   - EKS는 각 포드에 VPC IP 주소를 할당하므로, 예상되는 포드 수에 따라 충분히 큰 CIDR 블록이 필요합니다.

4. **태그 요구 사항**:
   - EKS가 서브넷을 식별하고 적절히 사용할 수 있도록 특정 태그가 필요합니다:
     - 공유 서브넷: `kubernetes.io/cluster/<cluster-name>: shared`
     - 퍼블릭 서브넷: `kubernetes.io/role/elb: 1`
     - 프라이빗 서브넷: `kubernetes.io/role/internal-elb: 1`

#### VPC 구성 예시 (eksctl 사용):

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  cidr: 192.168.0.0/16
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
    public:
      us-west-2a:
        id: subnet-0123456789abcdef2
      us-west-2b:
        id: subnet-0123456789abcdef3
```

#### AWS CLI를 사용한 VPC 구성:

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

NAT 게이트웨이는 프라이빗 서브넷의 워커 노드가 인터넷에 접근해야 하는 경우에 필요하지만, EKS 클러스터 생성 자체에는 필수 요구 사항이 아닙니다. 퍼블릭 서브넷만 사용하는 경우 NAT 게이트웨이 없이도 클러스터를 생성할 수 있습니다(프로덕션 환경에서는 권장되지 않음).
</details>

3. Amazon EKS 클러스터를 생성할 때 필요한 IAM 역할은 무엇인가요?
   - A) EKS 서비스 역할만
   - B) 노드 인스턴스 역할만
   - C) EKS 서비스 역할과 노드 인스턴스 역할
   - D) Fargate 실행 역할
   
<details>
<summary>정답 보기</summary>

**정답: C) EKS 서비스 역할과 노드 인스턴스 역할**

**설명:**
Amazon EKS 클러스터를 생성하고 운영하기 위해서는 두 가지 주요 IAM 역할이 필요합니다: EKS 서비스 역할과 노드 인스턴스 역할입니다. 이 두 역할은 각각 다른 목적을 가지고 있으며, 클러스터의 올바른 작동을 위해 모두 필요합니다.

#### 1. EKS 서비스 역할 (EKS Cluster Role):
- **목적**: AWS EKS 서비스가 사용자를 대신하여 다른 AWS 서비스를 호출할 수 있도록 허용합니다.
- **필요한 권한**:
  - EC2, ELB, CloudWatch, KMS 등의 AWS 서비스에 접근
  - VPC 리소스 관리
  - 로그 그룹 생성 및 관리
- **관리형 정책**: `AmazonEKSClusterPolicy`
- **생성 방법**:
  ```bash
  # AWS CLI를 사용한 역할 생성
  aws iam create-role \
    --role-name EKSClusterRole \
    --assume-role-policy-document file://eks-cluster-trust-policy.json
  
  # 관리형 정책 연결
  aws iam attach-role-policy \
    --role-name EKSClusterRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
  ```

  신뢰 정책 (eks-cluster-trust-policy.json):
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "eks.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  ```

#### 2. 노드 인스턴스 역할 (Node Instance Role):
- **목적**: EKS 워커 노드(EC2 인스턴스)가 AWS 서비스와 상호 작용할 수 있도록 허용합니다.
- **필요한 권한**:
  - ECR에서 컨테이너 이미지 가져오기
  - CloudWatch에 로그 쓰기
  - EBS/EFS 볼륨 관리
  - 로드 밸런서 등록/등록 취소
- **관리형 정책**:
  - `AmazonEKSWorkerNodePolicy`
  - `AmazonEC2ContainerRegistryReadOnly`
  - `AmazonEKS_CNI_Policy`
- **생성 방법**:
  ```bash
  # AWS CLI를 사용한 역할 생성
  aws iam create-role \
    --role-name EKSNodeRole \
    --assume-role-policy-document file://ec2-trust-policy.json
  
  # 관리형 정책 연결
  aws iam attach-role-policy \
    --role-name EKSNodeRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
  
  aws iam attach-role-policy \
    --role-name EKSNodeRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
  
  aws iam attach-role-policy \
    --role-name EKSNodeRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
  ```

  신뢰 정책 (ec2-trust-policy.json):
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  ```

#### eksctl을 사용한 역할 자동 생성:
eksctl을 사용하여 클러스터를 생성할 때, 필요한 IAM 역할을 자동으로 생성할 수 있습니다:
```bash
eksctl create cluster --name my-cluster --region us-west-2
```

#### 추가 역할 (선택적):
- **Fargate 실행 역할**: Fargate 프로필을 사용하는 경우에만 필요합니다.
- **서비스 계정 IAM 역할**: IRSA(IAM Roles for Service Accounts)를 사용하는 경우 필요합니다.
- **ALB 컨트롤러 역할**: AWS Load Balancer Controller를 사용하는 경우 필요합니다.

Fargate 실행 역할은 Fargate 프로필을 사용하는 경우에만 필요하며, 기본 EKS 클러스터 생성에는 필수가 아닙니다. 따라서 EKS 클러스터를 생성하기 위해 필수적으로 필요한 IAM 역할은 EKS 서비스 역할과 노드 인스턴스 역할입니다.
</details>

4. eksctl을 사용하여 EKS 클러스터를 생성할 때, 다음 중 올바른 명령어는 무엇인가요?
   - A) `eksctl create-cluster --name my-cluster --region us-west-2`
   - B) `eksctl create cluster --name my-cluster --region us-west-2`
   - C) `eksctl new cluster --name my-cluster --region us-west-2`
   - D) `eksctl start cluster --name my-cluster --region us-west-2`
   
<details>
<summary>정답 보기</summary>

**정답: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**설명:**
eksctl을 사용하여 EKS 클러스터를 생성하는 올바른 명령어는 `eksctl create cluster --name my-cluster --region us-west-2`입니다. 이 명령어는 지정된 이름과 리전으로 기본 설정의 EKS 클러스터를 생성합니다.

#### eksctl 명령어 구조:
- `eksctl`: 기본 명령어
- `create`: 리소스를 생성하는 작업
- `cluster`: 생성할 리소스 유형(클러스터)
- `--name my-cluster`: 클러스터 이름 지정
- `--region us-west-2`: AWS 리전 지정

#### 기본 클러스터 생성 명령어:
```bash
eksctl create cluster --name my-cluster --region us-west-2
```

이 명령어는 다음과 같은 기본 설정으로 클러스터를 생성합니다:
- 2개의 m5.large 노드
- 새로운 VPC 생성
- 기본 Amazon Linux 2 AMI 사용
- 관리형 노드 그룹 사용
- 필요한 IAM 역할 자동 생성

#### 추가 옵션을 포함한 고급 명령어:
```bash
eksctl create cluster \
  --name my-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --with-oidc \
  --ssh-access \
  --ssh-public-key my-key \
  --managed
```

#### 구성 파일을 사용한 클러스터 생성:
```bash
# cluster.yaml 파일 생성
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.28"

nodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: true
      publicKeyName: my-key
EOF

# 구성 파일을 사용한 클러스터 생성
eksctl create cluster -f cluster.yaml
```

#### 다른 옵션들의 문제점:
- `eksctl create-cluster`: 잘못된 명령어 형식입니다. eksctl에서는 하이픈(-)이 아닌 공백을 사용하여 명령어를 구분합니다.
- `eksctl new cluster`: 'new'는 eksctl의 유효한 명령어가 아닙니다.
- `eksctl start cluster`: 'start'는 eksctl의 유효한 명령어가 아닙니다. 이미 존재하는 클러스터를 시작하는 개념은 EKS에 적용되지 않습니다.

eksctl은 EKS 클러스터 관리를 위한 다양한 명령어를 제공합니다:
- `eksctl create cluster`: 새 클러스터 생성
- `eksctl get cluster`: 클러스터 목록 조회
- `eksctl update cluster`: 클러스터 업데이트
- `eksctl delete cluster`: 클러스터 삭제
- `eksctl create nodegroup`: 노드 그룹 추가
- `eksctl scale nodegroup`: 노드 그룹 크기 조정
</details>

5. Amazon EKS 클러스터를 생성할 때 지정할 수 있는 Kubernetes 버전으로 올바른 것은 무엇인가요?
   - A) 최신 버전만 지원됨
   - B) 최신 버전과 이전 2개 버전만 지원됨
   - C) AWS에서 지원하는 모든 Kubernetes 버전
   - D) 모든 Kubernetes 버전
   
<details>
<summary>정답 보기</summary>

**정답: C) AWS에서 지원하는 모든 Kubernetes 버전**

**설명:**
Amazon EKS 클러스터를 생성할 때는 AWS에서 현재 지원하는 Kubernetes 버전 중에서 선택할 수 있습니다. AWS는 일반적으로 여러 Kubernetes 버전을 동시에 지원하며, 이는 최신 버전과 이전의 몇 가지 버전을 포함합니다.

#### EKS의 Kubernetes 버전 지원 정책:

1. **지원 기간**:
   - 각 Kubernetes 버전은 EKS에서 출시된 후 14개월 동안 지원됩니다.
   - 지원 종료 날짜는 최소 60일 전에 공지됩니다.

2. **지원되는 버전**:
   - 일반적으로 EKS는 3-4개의 Kubernetes 버전을 동시에 지원합니다.
   - 새 버전은 Kubernetes 커뮤니티 출시 후 몇 개월 내에 EKS에서 사용 가능해집니다.

3. **버전 확인 방법**:
   ```bash
   # AWS CLI를 사용하여 지원되는 버전 확인
   aws eks describe-addon-versions | grep kubernetesVersion | sort -u
   
   # 또는
   aws eks get-cluster-version-list
   ```

4. **버전 지정 예시**:
   ```bash
   # eksctl을 사용한 특정 버전 지정
   eksctl create cluster --name my-cluster --version 1.28 --region us-west-2
   
   # AWS CLI를 사용한 특정 버전 지정
   aws eks create-cluster \
     --name my-cluster \
     --kubernetes-version 1.28 \
     --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890
   ```

5. **버전 업그레이드**:
   - 클러스터 생성 후에도 지원되는 버전으로 업그레이드할 수 있습니다.
   - 일반적으로 한 번에 한 마이너 버전씩 업그레이드하는 것이 권장됩니다.
   ```bash
   # 클러스터 버전 업그레이드
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.28
   ```

#### 버전 선택 시 고려 사항:

1. **안정성**:
   - 최신 버전은 새로운 기능을 제공하지만, 초기 버그가 있을 수 있습니다.
   - 안정성이 중요한 프로덕션 환경에서는 검증된 이전 버전을 선택하는 것이 좋을 수 있습니다.

2. **기능 요구 사항**:
   - 특정 Kubernetes 기능이 필요한 경우, 해당 기능을 지원하는 최소 버전을 선택해야 합니다.

3. **지원 기간**:
   - 장기 지원이 필요한 경우, 최근에 출시된 버전을 선택하여 지원 기간을 최대화할 수 있습니다.

4. **에코시스템 호환성**:
   - 사용 중인 도구, 애드온, 운영자 등이 선택한 Kubernetes 버전과 호환되는지 확인해야 합니다.

다른 옵션들의 문제점:
- 최신 버전만 지원되는 것이 아니라, 여러 버전이 동시에 지원됩니다.
- 지원되는 버전 수는 고정된 "최신 버전과 이전 2개 버전"이 아니라, AWS의 지원 정책에 따라 달라집니다.
- 모든 Kubernetes 버전이 지원되는 것이 아니라, AWS에서 테스트하고 지원하는 버전만 사용할 수 있습니다.
</details>
6. Amazon EKS 클러스터에서 노드 그룹을 생성할 때 선택할 수 있는 옵션이 아닌 것은 무엇인가요?
   - A) 관리형 노드 그룹
   - B) 자체 관리형 노드 그룹
   - C) Fargate 프로필
   - D) 서버리스 노드 그룹
   
<details>
<summary>정답 보기</summary>

**정답: D) 서버리스 노드 그룹**

**설명:**
"서버리스 노드 그룹"은 Amazon EKS에 존재하지 않는 개념입니다. EKS에서 워크로드를 실행하기 위한 세 가지 주요 옵션은 관리형 노드 그룹, 자체 관리형 노드 그룹, 그리고 Fargate 프로필입니다.

#### 1. 관리형 노드 그룹 (Managed Node Groups):
- **특징**:
  - AWS에서 노드의 프로비저닝 및 수명 주기 관리
  - 자동 EC2 인스턴스 생성 및 등록
  - 자동 ASG(Auto Scaling Group) 구성
  - 자동 Kubernetes 버전 업그레이드
  - 손상된 노드 자동 교체
  - 노드 AMI 자동 업데이트

- **생성 방법**:
  ```bash
  # eksctl을 사용한 관리형 노드 그룹 생성
  eksctl create nodegroup \
    --cluster my-cluster \
    --name my-mng \
    --node-type t3.medium \
    --nodes 3 \
    --nodes-min 1 \
    --nodes-max 5
  
  # AWS CLI를 사용한 관리형 노드 그룹 생성
  aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name my-mng \
    --subnets subnet-12345 subnet-67890 \
    --instance-types t3.medium \
    --scaling-config minSize=1,maxSize=5,desiredSize=3 \
    --node-role arn:aws:iam::123456789012:role/EksNodeRole
  ```

#### 2. 자체 관리형 노드 그룹 (Self-managed Node Groups):
- **특징**:
  - 사용자가 노드의 프로비저닝 및 수명 주기 관리
  - 더 많은 사용자 지정 옵션
  - 특수 AMI 또는 부트스트랩 스크립트 사용 가능
  - 특정 인스턴스 유형 또는 구성 요구 사항에 적합

- **생성 방법**:
  ```bash
  # eksctl을 사용한 자체 관리형 노드 그룹 생성
  eksctl create nodegroup \
    --cluster my-cluster \
    --name my-smng \
    --node-type t3.medium \
    --nodes 3 \
    --nodes-min 1 \
    --nodes-max 5 \
    --managed=false
  
  # CloudFormation 또는 EC2 시작 템플릿을 사용하여 수동으로 생성할 수도 있습니다.
  ```

#### 3. Fargate 프로필 (Fargate Profiles):
- **특징**:
  - 서버리스 컨테이너 실행 환경
  - 노드 관리 불필요
  - 포드 단위로 리소스 할당 및 비용 청구
  - 특정 네임스페이스 및 레이블에 기반한 선택적 실행

- **생성 방법**:
  ```bash
  # eksctl을 사용한 Fargate 프로필 생성
  eksctl create fargateprofile \
    --cluster my-cluster \
    --name my-fargate-profile \
    --namespace my-namespace \
    --labels app=my-app
  
  # AWS CLI를 사용한 Fargate 프로필 생성
  aws eks create-fargate-profile \
    --cluster-name my-cluster \
    --fargate-profile-name my-fargate-profile \
    --pod-execution-role-arn arn:aws:iam::123456789012:role/FargatePodExecutionRole \
    --selectors namespace=my-namespace,labels={app=my-app}
  ```

#### 각 옵션의 비교:

| 특성 | 관리형 노드 그룹 | 자체 관리형 노드 그룹 | Fargate 프로필 |
|------|----------------|-------------------|--------------|
| 관리 오버헤드 | 낮음 | 높음 | 없음 |
| 사용자 지정 | 중간 | 높음 | 낮음 |
| 비용 효율성 | 중간 | 높음 (최적화 시) | 낮음 (편의성에 비용 지불) |
| 확장성 | 자동 | 수동/자동 | 자동 |
| 사용 사례 | 일반적인 워크로드 | 특수 요구 사항 | 가변적 워크로드, 개발/테스트 |

"서버리스 노드 그룹"이라는 용어는 공식적으로 존재하지 않습니다. Fargate는 서버리스 컨테이너 실행 환경을 제공하지만, 이는 "노드 그룹"이 아닌 "Fargate 프로필"로 구성됩니다. Fargate를 사용하면 노드를 직접 관리할 필요가 없으며, 포드 실행에 필요한 컴퓨팅 리소스만 프로비저닝됩니다.
</details>
7. Amazon EKS 클러스터에서 노드 AMI 유형으로 지원되지 않는 것은 무엇인가요?
   - A) Amazon Linux 2
   - B) Amazon Linux 2023
   - C) Bottlerocket
   - D) Ubuntu Core
   
<details>
<summary>정답 보기</summary>

**정답: D) Ubuntu Core**

**설명:**
Ubuntu Core는 Amazon EKS에서 공식적으로 지원하는 노드 AMI 유형이 아닙니다. EKS에서 공식적으로 지원하는 노드 AMI 유형은 Amazon Linux 2, Amazon Linux 2023, Bottlerocket입니다.

#### EKS에서 지원하는 노드 AMI 유형:

1. **Amazon Linux 2 (AL2)**:
   - AWS에서 제공하는 기본 Linux 배포판
   - EKS 최적화 AMI로 제공됨
   - 대부분의 EKS 워크로드에 권장됨
   - 장기 지원 및 보안 업데이트

   ```bash
   # Amazon Linux 2 기반 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name al2-nodes \
     --node-ami-family AmazonLinux2
   ```

2. **Amazon Linux 2023 (AL2023)**:
   - Amazon Linux의 최신 버전
   - 향상된 보안 및 성능
   - 최신 커널 및 소프트웨어 패키지
   - EKS 최적화 AMI로 제공됨

   ```bash
   # Amazon Linux 2023 기반 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name al2023-nodes \
     --node-ami-family AmazonLinux2023
   ```

3. **Bottlerocket**:
   - 컨테이너 워크로드에 최적화된 오픈 소스 Linux 기반 OS
   - 최소화된 공격 표면
   - 트랜잭션 기반 업데이트
   - 컨테이너 중심 설계

   ```bash
   # Bottlerocket 기반 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name bottlerocket-nodes \
     --node-ami-family Bottlerocket
   ```

#### 기타 지원되는 AMI 옵션:

1. **Windows**:
   - Windows Server 2019, 2022 기반 AMI
   - Windows 컨테이너 워크로드 실행 가능

   ```bash
   # Windows 기반 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name windows-nodes \
     --node-ami-family WindowsServer2022FullContainer
   ```

2. **사용자 지정 AMI**:
   - 특정 요구 사항에 맞게 사용자 지정된 AMI 사용 가능
   - 자체 관리형 노드 그룹에서 주로 사용

   ```bash
   # 사용자 지정 AMI 기반 노드 그룹 생성
   eksctl create nodegroup \
     --cluster my-cluster \
     --name custom-nodes \
     --node-ami ami-1234567890abcdef0
   ```

#### Ubuntu를 EKS에서 사용하는 방법:
Ubuntu Core는 공식적으로 지원되지 않지만, 표준 Ubuntu Server AMI를 사용하여 자체 관리형 노드 그룹을 생성할 수 있습니다. 이 경우 다음과 같은 추가 구성이 필요합니다:

1. Ubuntu Server AMI 선택
2. 필요한 Kubernetes 구성 요소 설치
3. 부트스트랩 스크립트를 사용하여 노드를 클러스터에 연결

```bash
# Ubuntu 기반 자체 관리형 노드 그룹 생성 예시
eksctl create nodegroup \
  --cluster my-cluster \
  --name ubuntu-nodes \
  --node-ami ami-ubuntu-server-id \
  --managed=false \
  --ssh-access \
  --ssh-public-key my-key \
  --pre-bootstrap-commands 'apt-get update && apt-get install -y docker.io'
```

#### AMI 선택 시 고려 사항:
- **보안**: 정기적인 보안 업데이트 및 패치
- **성능**: 워크로드에 최적화된 커널 및 구성
- **호환성**: Kubernetes 버전과의 호환성
- **관리 용이성**: 업데이트 및 유지 관리 프로세스
- **특수 요구 사항**: GPU 지원, 커널 모듈 등

Ubuntu Core는 IoT 및 엣지 디바이스를 위한 경량 운영 체제로, EKS 노드로 사용하기 위한 공식 지원이나 최적화가 되어 있지 않습니다. 따라서 EKS 클러스터에서 노드 AMI 유형으로 지원되지 않는 것은 Ubuntu Core입니다.
</details>
8. Amazon EKS 클러스터의 엔드포인트 액세스 구성에 대한 설명으로 올바른 것은 무엇인가요?
   - A) 기본적으로 퍼블릭 엔드포인트만 활성화됨
   - B) 기본적으로 프라이빗 엔드포인트만 활성화됨
   - C) 기본적으로 퍼블릭 및 프라이빗 엔드포인트 모두 활성화됨
   - D) 엔드포인트 액세스는 클러스터 생성 후 변경할 수 없음
   
<details>
<summary>정답 보기</summary>

**정답: A) 기본적으로 퍼블릭 엔드포인트만 활성화됨**

**설명:**
Amazon EKS 클러스터를 생성할 때, 기본적으로 퍼블릭 엔드포인트만 활성화되고 프라이빗 엔드포인트는 비활성화됩니다. 이 구성은 클러스터 생성 후에 변경할 수 있으며, 보안 요구 사항에 따라 다양한 엔드포인트 액세스 구성을 선택할 수 있습니다.

#### EKS 클러스터 엔드포인트 액세스 옵션:

1. **퍼블릭 엔드포인트만 활성화 (기본 설정)**:
   - 인터넷을 통해 클러스터 API 서버에 접근 가능
   - 보안 그룹을 통해 접근 제한 가능
   - 개발 환경이나 테스트 환경에 적합

   ```bash
   # AWS CLI를 사용한 구성
   aws eks update-cluster-config \
     --name my-cluster \
     --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=false
   ```

2. **퍼블릭 및 프라이빗 엔드포인트 모두 활성화**:
   - VPC 내부에서 프라이빗 IP를 통한 접근 가능
   - 인터넷을 통한 접근도 가능
   - 하이브리드 환경에 적합

   ```bash
   # AWS CLI를 사용한 구성
   aws eks update-cluster-config \
     --name my-cluster \
     --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true
   ```

3. **프라이빗 엔드포인트만 활성화**:
   - VPC 내부에서만 클러스터 API 서버에 접근 가능
   - 인터넷을 통한 접근 불가
   - 가장 높은 수준의 보안을 제공
   - 프로덕션 환경에 권장

   ```bash
   # AWS CLI를 사용한 구성
   aws eks update-cluster-config \
     --name my-cluster \
     --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
   ```

4. **퍼블릭 액세스 제한**:
   - 특정 CIDR 블록에서만 퍼블릭 엔드포인트 접근 허용
   - 회사 네트워크 또는 VPN에서만 접근 가능하도록 제한

   ```bash
   # AWS CLI를 사용한 구성
   aws eks update-cluster-config \
     --name my-cluster \
     --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]
   ```

#### eksctl을 사용한 클러스터 생성 시 엔드포인트 구성:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  clusterEndpoints:
    publicAccess: true   # 퍼블릭 엔드포인트 활성화
    privateAccess: true  # 프라이빗 엔드포인트 활성화
  publicAccessCIDRs: ["203.0.113.0/24"]  # 퍼블릭 액세스 제한
```

```bash
eksctl create cluster -f cluster.yaml
```

#### 엔드포인트 액세스 구성 변경:

```bash
# 프라이빗 엔드포인트 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPrivateAccess=true

# 퍼블릭 엔드포인트 비활성화
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false
```

#### 엔드포인트 액세스 구성 시 고려 사항:

1. **보안 요구 사항**:
   - 프라이빗 엔드포인트만 사용하면 가장 높은 수준의 보안 제공
   - 퍼블릭 액세스가 필요한 경우 CIDR 제한 적용

2. **네트워크 연결**:
   - 프라이빗 엔드포인트만 사용하는 경우, VPC 내부 또는 VPN/Direct Connect를 통해서만 접근 가능
   - 하이브리드 작업 환경에서는 두 엔드포인트 모두 활성화하는 것이 유용할 수 있음

3. **운영 요구 사항**:
   - CI/CD 파이프라인, 외부 도구 등이 클러스터에 접근해야 하는 경우 고려

4. **비용**:
   - 엔드포인트 구성 자체에는 추가 비용이 없음
   - 프라이빗 엔드포인트만 사용하는 경우 VPN 또는 Direct Connect 비용 고려

다른 옵션들의 문제점:
- 기본적으로 프라이빗 엔드포인트만 활성화되는 것이 아니라, 퍼블릭 엔드포인트만 활성화됩니다.
- 기본적으로 퍼블릭 및 프라이빗 엔드포인트 모두 활성화되는 것이 아니라, 퍼블릭 엔드포인트만 활성화됩니다.
- 엔드포인트 액세스는 클러스터 생성 후에도 변경할 수 있습니다.
</details>
9. Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 선택할 때 고려해야 할 사항이 아닌 것은 무엇인가요?
   - A) 워크로드 요구 사항 (CPU, 메모리, 스토리지)
   - B) 비용 최적화
   - C) 가용 영역 수
   - D) 인스턴스 세대 (예: t3 vs t2)
   
<details>
<summary>정답 보기</summary>

**정답: C) 가용 영역 수**

**설명:**
가용 영역 수는 노드 그룹의 인스턴스 유형을 선택할 때 직접적인 고려 사항이 아닙니다. 가용 영역은 노드 그룹이 배포되는 위치와 관련이 있으며, 인스턴스 유형 자체의 선택과는 별개입니다. 인스턴스 유형은 워크로드 요구 사항, 비용 최적화, 인스턴스 세대 등을 고려하여 선택해야 합니다.

#### 노드 그룹 인스턴스 유형 선택 시 실제 고려 사항:

1. **워크로드 요구 사항 (CPU, 메모리, 스토리지)**:
   - 애플리케이션의 리소스 요구 사항에 맞는 인스턴스 유형 선택
   - 메모리 집약적 워크로드: r5, r6g 등의 메모리 최적화 인스턴스
   - 컴퓨팅 집약적 워크로드: c5, c6g 등의 컴퓨팅 최적화 인스턴스
   - 균형 잡힌 워크로드: m5, m6g 등의 범용 인스턴스
   - GPU 워크로드: p3, g4dn 등의 가속 컴퓨팅 인스턴스

2. **비용 최적화**:
   - 온디맨드 vs 스팟 인스턴스
   - 예약 인스턴스 또는 Savings Plans 활용
   - 적절한 크기의 인스턴스 선택 (오버프로비저닝 방지)
   - ARM 기반 Graviton 인스턴스(예: m6g, c6g)를 통한 비용 절감

3. **인스턴스 세대**:
   - 최신 세대 인스턴스는 일반적으로 더 나은 성능과 비용 효율성 제공
   - 예: t3는 t2보다 더 나은 성능과 가격 대비 성능 제공
   - 최신 세대는 향상된 네트워킹, 스토리지 성능 등의 기능 제공

4. **네트워킹 요구 사항**:
   - 향상된 네트워킹 지원 (ENA, EFA 등)
   - 네트워크 대역폭 요구 사항
   - 인스턴스당 최대 포드 수와 관련된 네트워킹 제한

5. **스토리지 요구 사항**:
   - 로컬 인스턴스 스토리지 필요 여부 (예: i3, d3 인스턴스)
   - EBS 최적화 지원
   - 스토리지 처리량 및 IOPS 요구 사항

6. **CPU 아키텍처**:
   - x86 (Intel, AMD) vs ARM (AWS Graviton)
   - 애플리케이션 호환성 고려

#### 가용 영역과 노드 그룹 배포:

가용 영역 수는 인스턴스 유형 선택이 아닌, 노드 그룹 배포 전략과 관련이 있습니다:

- 노드 그룹은 여러 가용 영역에 걸쳐 배포하여 고가용성 확보
- 각 가용 영역에 균등하게 노드 배포
- 리전 내 모든 가용 영역 또는 특정 가용 영역 선택 가능

```bash
# 특정 가용 영역에 노드 그룹 배포
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

#### 인스턴스 유형 선택 예시:

1. **웹 애플리케이션 서버**:
   - 범용 인스턴스: t3.medium, m5.large
   - 비용 효율적이면서 균형 잡힌 성능 제공

2. **데이터베이스**:
   - 메모리 최적화 인스턴스: r5.xlarge, r6g.xlarge
   - 높은 메모리 대 CPU 비율 제공

3. **배치 처리 작업**:
   - 컴퓨팅 최적화 인스턴스: c5.xlarge, c6g.xlarge
   - 높은 CPU 성능 제공

4. **기계 학습 워크로드**:
   - GPU 인스턴스: p3.2xlarge, g4dn.xlarge
   - 가속 컴퓨팅 기능 제공

인스턴스 유형 선택은 워크로드 특성, 비용 제약, 성능 요구 사항 등을 고려하여 결정해야 하며, 가용 영역 수는 인스턴스 유형 자체의 선택보다는 노드 그룹의 배포 전략과 관련이 있습니다.
</details>
9. Amazon EKS 클러스터에서 노드 그룹의 인스턴스 유형을 선택할 때 고려해야 할 사항이 아닌 것은 무엇인가요?
   - A) 워크로드 요구 사항 (CPU, 메모리, 스토리지)
   - B) 비용 최적화
   - C) 가용 영역 수
   - D) 인스턴스 세대 (예: t3 vs t2)
   
<details>
<summary>정답 보기</summary>

**정답: C) 가용 영역 수**

**설명:**
가용 영역 수는 노드 그룹의 인스턴스 유형을 선택할 때 직접적인 고려 사항이 아닙니다. 가용 영역은 노드 그룹이 배포되는 위치와 관련이 있으며, 인스턴스 유형 자체의 선택과는 별개입니다. 인스턴스 유형은 워크로드 요구 사항, 비용 최적화, 인스턴스 세대 등을 고려하여 선택해야 합니다.

#### 노드 그룹 인스턴스 유형 선택 시 실제 고려 사항:

1. **워크로드 요구 사항 (CPU, 메모리, 스토리지)**:
   - 애플리케이션의 리소스 요구 사항에 맞는 인스턴스 유형 선택
   - 메모리 집약적 워크로드: r5, r6g 등의 메모리 최적화 인스턴스
   - 컴퓨팅 집약적 워크로드: c5, c6g 등의 컴퓨팅 최적화 인스턴스
   - 균형 잡힌 워크로드: m5, m6g 등의 범용 인스턴스
   - GPU 워크로드: p3, g4dn 등의 가속 컴퓨팅 인스턴스

2. **비용 최적화**:
   - 온디맨드 vs 스팟 인스턴스
   - 예약 인스턴스 또는 Savings Plans 활용
   - 적절한 크기의 인스턴스 선택 (오버프로비저닝 방지)
   - ARM 기반 Graviton 인스턴스(예: m6g, c6g)를 통한 비용 절감

3. **인스턴스 세대**:
   - 최신 세대 인스턴스는 일반적으로 더 나은 성능과 비용 효율성 제공
   - 예: t3는 t2보다 더 나은 성능과 가격 대비 성능 제공
   - 최신 세대는 향상된 네트워킹, 스토리지 성능 등의 기능 제공

4. **네트워킹 요구 사항**:
   - 향상된 네트워킹 지원 (ENA, EFA 등)
   - 네트워크 대역폭 요구 사항
   - 인스턴스당 최대 포드 수와 관련된 네트워킹 제한

5. **스토리지 요구 사항**:
   - 로컬 인스턴스 스토리지 필요 여부 (예: i3, d3 인스턴스)
   - EBS 최적화 지원
   - 스토리지 처리량 및 IOPS 요구 사항

6. **CPU 아키텍처**:
   - x86 (Intel, AMD) vs ARM (AWS Graviton)
   - 애플리케이션 호환성 고려

#### 가용 영역과 노드 그룹 배포:

가용 영역 수는 인스턴스 유형 선택이 아닌, 노드 그룹 배포 전략과 관련이 있습니다:

- 노드 그룹은 여러 가용 영역에 걸쳐 배포하여 고가용성 확보
- 각 가용 영역에 균등하게 노드 배포
- 리전 내 모든 가용 영역 또는 특정 가용 영역 선택 가능

```bash
# 특정 가용 영역에 노드 그룹 배포
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

#### 인스턴스 유형 선택 예시:

1. **웹 애플리케이션 서버**:
   - 범용 인스턴스: t3.medium, m5.large
   - 비용 효율적이면서 균형 잡힌 성능 제공

2. **데이터베이스**:
   - 메모리 최적화 인스턴스: r5.xlarge, r6g.xlarge
   - 높은 메모리 대 CPU 비율 제공

3. **배치 처리 작업**:
   - 컴퓨팅 최적화 인스턴스: c5.xlarge, c6g.xlarge
   - 높은 CPU 성능 제공

4. **기계 학습 워크로드**:
   - GPU 인스턴스: p3.2xlarge, g4dn.xlarge
   - 가속 컴퓨팅 기능 제공

인스턴스 유형 선택은 워크로드 특성, 비용 제약, 성능 요구 사항 등을 고려하여 결정해야 하며, 가용 영역 수는 인스턴스 유형 자체의 선택보다는 노드 그룹의 배포 전략과 관련이 있습니다.
</details>
10. Amazon EKS 클러스터를 생성한 후 kubectl을 구성하는 올바른 명령어는 무엇인가요?
    - A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    - B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    - C) `kubectl config set-cluster my-cluster --region us-west-2`
    - D) `eksctl configure kubectl --name my-cluster --region us-west-2`
    
<details>
<summary>정답 보기</summary>

**정답: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**설명:**
Amazon EKS 클러스터를 생성한 후 kubectl을 구성하는 올바른 명령어는 `aws eks update-kubeconfig --name my-cluster --region us-west-2`입니다. 이 명령어는 AWS CLI의 EKS 모듈을 사용하여 지정된 클러스터에 대한 kubeconfig 파일을 업데이트합니다.

#### kubectl 구성 과정:

1. **kubeconfig 파일 업데이트**:
   - kubeconfig 파일은 kubectl이 Kubernetes 클러스터와 통신하는 데 필요한 구성 정보를 저장합니다.
   - 기본적으로 `~/.kube/config` 위치에 저장됩니다.
   - `aws eks update-kubeconfig` 명령어는 이 파일을 자동으로 업데이트합니다.

2. **명령어 구성 요소**:
   - `--name`: EKS 클러스터 이름
   - `--region`: 클러스터가 위치한 AWS 리전
   - `--kubeconfig` (선택 사항): 사용자 지정 kubeconfig 파일 경로
   - `--role-arn` (선택 사항): 클러스터 접근에 사용할 IAM 역할

3. **전체 명령어 예시**:
   ```bash
   aws eks update-kubeconfig --name my-cluster --region us-west-2
   ```

4. **추가 옵션**:
   ```bash
   # 사용자 지정 kubeconfig 파일 사용
   aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig ~/.kube/eks-config

   # 특정 IAM 역할 사용
   aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole

   # 별칭 설정
   aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias
   ```

5. **구성 확인**:
   ```bash
   # 현재 컨텍스트 확인
   kubectl config current-context

   # 모든 컨텍스트 나열
   kubectl config get-contexts

   # 클러스터 연결 테스트
   kubectl cluster-info
   ```

#### 다른 옵션들의 문제점:

- `aws eks get-kubeconfig --name my-cluster --region us-west-2`: 이 명령어는 존재하지 않습니다. AWS CLI에는 `get-kubeconfig` 하위 명령어가 없습니다.

- `kubectl config set-cluster my-cluster --region us-west-2`: 이 명령어는 구문이 잘못되었습니다. `kubectl config set-cluster`는 `--region` 플래그를 지원하지 않으며, EKS 클러스터에 필요한 인증 정보를 자동으로 구성하지 않습니다.

- `eksctl configure kubectl --name my-cluster --region us-west-2`: 이 명령어는 존재하지 않습니다. eksctl에는 `configure kubectl` 하위 명령어가 없습니다. eksctl로 클러스터를 생성한 경우, 자동으로 kubeconfig를 구성하지만, 기존 클러스터에 대해서는 `aws eks update-kubeconfig` 명령어를 사용해야 합니다.

#### eksctl을 사용한 클러스터 생성 및 구성:

eksctl을 사용하여 클러스터를 생성하는 경우, kubeconfig는 자동으로 업데이트됩니다:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

이 명령어는 클러스터를 생성하고 kubeconfig를 자동으로 업데이트합니다. 그러나 기존 클러스터에 연결하거나, 다른 도구로 생성된 클러스터에 연결하려면 `aws eks update-kubeconfig` 명령어를 사용해야 합니다.

#### 여러 클러스터 관리:

여러 EKS 클러스터를 관리하는 경우, 각 클러스터에 대해 `aws eks update-kubeconfig` 명령어를 실행하여 kubeconfig 파일에 추가할 수 있습니다:

```bash
# 첫 번째 클러스터 구성
aws eks update-kubeconfig --name cluster1 --region us-west-2

# 두 번째 클러스터 구성
aws eks update-kubeconfig --name cluster2 --region us-east-1

# 컨텍스트 전환
kubectl config use-context arn:aws:eks:us-west-2:123456789012:cluster/cluster1
```

따라서, Amazon EKS 클러스터를 생성한 후 kubectl을 구성하는 올바른 명령어는 `aws eks update-kubeconfig --name my-cluster --region us-west-2`입니다.
</details>

## 실습 문제

### 실습 1: eksctl을 사용하여 EKS 클러스터 생성

**시나리오:**
당신은 회사의 DevOps 엔지니어로, 개발 팀을 위한 Amazon EKS 클러스터를 생성해야 합니다. 클러스터는 비용 효율적이면서도 확장 가능해야 하며, 기본적인 보안 설정을 갖추어야 합니다.

**요구사항:**
1. eksctl을 사용하여 EKS 클러스터 생성
2. 2개의 가용 영역에 걸쳐 배포
3. t3.medium 인스턴스 타입 사용
4. 오토스케일링 구성 (최소 2, 최대 5 노드)
5. 프라이빗 및 퍼블릭 엔드포인트 모두 활성화

**해결 방법:**

<details>
<summary>해결 방법 보기</summary>

#### 1. eksctl 설치 (아직 설치되지 않은 경우)

```bash
# macOS
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Linux
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version
```

#### 2. 클러스터 구성 파일 생성

```bash
cat > eks-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true

availabilityZones: ["us-west-2a", "us-west-2b"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        ebs: true
        albIngress: true
        cloudWatch: true
    ssh:
      allow: false
    privateNetworking: true
    tags:
      Environment: development
      Owner: devops-team
EOF
```

#### 3. 클러스터 생성

```bash
eksctl create cluster -f eks-cluster.yaml
```

이 명령어는 다음 작업을 수행합니다:
- CloudFormation 스택 생성
- VPC 및 서브넷 생성
- 보안 그룹 구성
- EKS 클러스터 생성
- 관리형 노드 그룹 생성
- 노드 부트스트래핑 및 클러스터 연결
- kubeconfig 구성

#### 4. 클러스터 확인

```bash
# 클러스터 상태 확인
eksctl get cluster --name dev-cluster --region us-west-2

# 노드 확인
kubectl get nodes -o wide

# 시스템 포드 확인
kubectl get pods -n kube-system
```

#### 5. 클러스터 액세스 구성

```bash
# kubeconfig 확인
kubectl config current-context

# 클러스터 정보 확인
kubectl cluster-info
```

#### 6. 기본 보안 설정 확인

```bash
# 네임스페이스 확인
kubectl get namespaces

# RBAC 설정 확인
kubectl get clusterroles
kubectl get clusterrolebindings
```

#### 7. 클러스터 리소스 모니터링

```bash
# 노드 리소스 사용량 확인
kubectl top nodes

# 포드 리소스 사용량 확인
kubectl top pods --all-namespaces
```

이 실습을 통해 eksctl을 사용하여 비용 효율적이고 확장 가능한 EKS 클러스터를 생성하는 방법을 배웠습니다. t3.medium 인스턴스는 비용 효율적인 선택이며, 오토스케일링 구성을 통해 워크로드에 따라 노드 수를 자동으로 조정할 수 있습니다. 또한 프라이빗 및 퍼블릭 엔드포인트를 모두 활성화하여 내부 및 외부에서 클러스터에 접근할 수 있도록 구성했습니다.
</details>
### 실습 2: AWS Management Console을 사용하여 EKS 클러스터 생성

**시나리오:**
당신은 AWS Management Console을 사용하여 EKS 클러스터를 생성하고 구성해야 합니다. 이 클러스터는 프로덕션 환경을 위한 것으로, 보안과 고가용성이 중요합니다.

**요구사항:**
1. AWS Management Console을 사용하여 EKS 클러스터 생성
2. 프라이빗 서브넷에 노드 배치
3. 클러스터 엔드포인트에 대한 퍼블릭 액세스 제한
4. 관리형 노드 그룹 구성
5. 필요한 IAM 역할 생성

**해결 방법:**

<details>
<summary>해결 방법 보기</summary>

#### 1. 필요한 IAM 역할 생성

**EKS 클러스터 역할 생성:**

1. AWS Management Console에 로그인하고 IAM 서비스로 이동합니다.
2. 왼쪽 메뉴에서 "역할"을 선택하고 "역할 생성"을 클릭합니다.
3. 신뢰할 수 있는 엔터티 유형으로 "AWS 서비스"를 선택합니다.
4. 사용 사례에서 "EKS"를 선택하고 "EKS - 클러스터"를 선택합니다.
5. "다음"을 클릭합니다.
6. `AmazonEKSClusterPolicy`가 자동으로 선택되어 있는지 확인합니다.
7. "다음"을 클릭합니다.
8. 역할 이름을 "EKSClusterRole"로 입력하고 "역할 생성"을 클릭합니다.

**EKS 노드 역할 생성:**

1. IAM 서비스에서 "역할 생성"을 다시 클릭합니다.
2. 신뢰할 수 있는 엔터티 유형으로 "AWS 서비스"를 선택합니다.
3. 사용 사례에서 "EC2"를 선택합니다.
4. "다음"을 클릭합니다.
5. 다음 정책을 검색하여 선택합니다:
   - `AmazonEKSWorkerNodePolicy`
   - `AmazonEC2ContainerRegistryReadOnly`
   - `AmazonEKS_CNI_Policy`
6. "다음"을 클릭합니다.
7. 역할 이름을 "EKSNodeRole"로 입력하고 "역할 생성"을 클릭합니다.

#### 2. VPC 및 서브넷 준비

프로덕션 환경을 위해 적절한 VPC 구성이 필요합니다. AWS CloudFormation 템플릿을 사용하여 EKS에 최적화된 VPC를 생성할 수 있습니다:

1. CloudFormation 콘솔로 이동합니다.
2. "스택 생성" > "새 리소스 사용(표준)"을 선택합니다.
3. Amazon S3 URL에 다음 주소를 입력합니다:
   ```
   https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
   ```
4. "다음"을 클릭합니다.
5. 스택 이름을 "eks-vpc"로 입력합니다.
6. 기본 파라미터를 그대로 두고 "다음"을 클릭합니다.
7. 다음 페이지에서도 기본 옵션을 그대로 두고 "다음"을 클릭합니다.
8. "스택 생성"을 클릭합니다.
9. 스택 생성이 완료되면 "출력" 탭에서 다음 값을 기록해 둡니다:
   - VpcId
   - SubnetIds
   - SecurityGroups

#### 3. EKS 클러스터 생성

1. AWS Management Console에서 EKS 서비스로 이동합니다.
2. "클러스터 생성"을 클릭합니다.
3. "클러스터 구성" 페이지에서:
   - 클러스터 이름: "prod-cluster"
   - Kubernetes 버전: 최신 버전 선택 (예: 1.28)
   - 클러스터 서비스 역할: 이전에 생성한 "EKSClusterRole" 선택
   - "다음"을 클릭합니다.

4. "네트워킹 지정" 페이지에서:
   - VPC: 이전에 생성한 VPC 선택
   - 서브넷: 프라이빗 서브넷만 선택 (퍼블릭 서브넷 선택 해제)
   - 보안 그룹: 기본 보안 그룹 선택
   - 클러스터 엔드포인트 액세스:
     - "프라이빗"을 선택하거나
     - "퍼블릭 및 프라이빗"을 선택하고 CIDR 블록을 회사 IP 범위로 제한
   - "다음"을 클릭합니다.

5. "로깅 구성" 페이지에서:
   - 필요한 로그 유형 선택 (API 서버, 감사, 인증자, 컨트롤러 관리자, 스케줄러)
   - "다음"을 클릭합니다.

6. "애드온 선택" 페이지에서:
   - 기본 애드온 유지 (kube-proxy, CoreDNS, VPC CNI)
   - "다음"을 클릭합니다.

7. 검토 페이지에서 모든 설정을 확인하고 "생성"을 클릭합니다.
8. 클러스터 생성이 완료될 때까지 기다립니다 (약 15-20분 소요).

#### 4. 관리형 노드 그룹 생성

1. 클러스터가 생성되면 클러스터 이름을 클릭합니다.
2. "컴퓨팅" 탭으로 이동하고 "노드 그룹 추가"를 클릭합니다.
3. "노드 그룹 구성" 페이지에서:
   - 이름: "prod-nodes"
   - 노드 IAM 역할: 이전에 생성한 "EKSNodeRole" 선택
   - "다음"을 클릭합니다.

4. "컴퓨팅 및 크기 조정 구성" 페이지에서:
   - AMI 유형: Amazon Linux 2 (x86)
   - 인스턴스 유형: m5.large 선택
   - 디스크 크기: 50 GiB
   - 노드 그룹 크기 조정 구성:
     - 최소 크기: 2
     - 최대 크기: 5
     - 원하는 크기: 3
   - "다음"을 클릭합니다.

5. "네트워킹 지정" 페이지에서:
   - 서브넷: 프라이빗 서브넷만 선택
   - "다음"을 클릭합니다.

6. "검토 및 생성" 페이지에서 모든 설정을 확인하고 "생성"을 클릭합니다.
7. 노드 그룹 생성이 완료될 때까지 기다립니다 (약 5분 소요).

#### 5. kubectl 구성 및 클러스터 액세스

1. AWS CLI가 설치되어 있는지 확인합니다.
2. 다음 명령어를 실행하여 kubectl 구성 파일을 업데이트합니다:
   ```bash
   aws eks update-kubeconfig --name prod-cluster --region us-west-2
   ```

3. 클러스터 연결을 확인합니다:
   ```bash
   kubectl get nodes
   kubectl cluster-info
   ```

#### 6. 기본 보안 강화

1. AWS 보안 그룹 규칙 검토 및 제한:
   ```bash
   # 현재 컨텍스트의 클러스터 정보 확인
   kubectl config view --minify
   ```

2. 네트워크 정책 적용 (선택 사항):
   ```yaml
   # default-deny.yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
     namespace: default
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
   ```

   ```bash
   kubectl apply -f default-deny.yaml
   ```

이 실습을 통해 AWS Management Console을 사용하여 프로덕션 환경에 적합한 보안 및 고가용성 설정을 갖춘 EKS 클러스터를 생성하는 방법을 배웠습니다. 프라이빗 서브넷에 노드를 배치하고 클러스터 엔드포인트에 대한 퍼블릭 액세스를 제한하여 보안을 강화했으며, 관리형 노드 그룹을 사용하여 노드 관리를 간소화했습니다.
</details>
## 고급 주제

다음은 Amazon EKS 클러스터 생성에 관한 고급 주제에 대한 질문입니다. 이 섹션은 EKS 클러스터 생성의 심화 개념과 모범 사례에 대한 이해를 테스트합니다.

1. Amazon EKS 클러스터에서 사용자 지정 시작 템플릿(Launch Template)을 사용하는 주요 이점은 무엇인가요?
   - A) 클러스터 생성 시간 단축
   - B) 노드 부트스트랩 스크립트 사용자 지정 및 추가 볼륨 구성 가능
   - C) 클러스터 컨트롤 플레인 사용자 지정
   - D) 자동으로 최신 AMI 버전 사용
   
<details>
<summary>정답 보기</summary>

**정답: B) 노드 부트스트랩 스크립트 사용자 지정 및 추가 볼륨 구성 가능**

**설명:**
Amazon EKS 클러스터에서 사용자 지정 시작 템플릿(Launch Template)을 사용하는 주요 이점은 노드 부트스트랩 스크립트를 사용자 지정하고 추가 볼륨을 구성할 수 있다는 것입니다. 시작 템플릿을 통해 EC2 인스턴스의 다양한 측면을 세밀하게 제어할 수 있으며, 이는 기본 노드 그룹 생성 옵션으로는 불가능한 고급 구성을 가능하게 합니다.

#### 시작 템플릿을 사용한 사용자 지정 가능 항목:

1. **부트스트랩 스크립트 사용자 지정**:
   - 노드가 클러스터에 조인하기 전에 실행되는 사용자 지정 스크립트 정의
   - 추가 소프트웨어 설치 및 구성
   - 시스템 설정 조정 (커널 파라미터, 네트워크 설정 등)
   - 예시:
     ```bash
     #!/bin/bash
     # 사용자 지정 부트스트랩 스크립트
     echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
     sysctl -p
     
     # 추가 패키지 설치
     yum install -y amazon-cloudwatch-agent
     
     # EKS 부트스트랩 스크립트 실행
     /etc/eks/bootstrap.sh my-cluster --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker'
     ```

2. **추가 볼륨 구성**:
   - 루트 볼륨 크기, 유형, IOPS 사용자 지정
   - 데이터, 로그, 임시 스토리지 등을 위한 추가 EBS 볼륨 연결
   - 인스턴스 스토어 볼륨 구성
   - 예시:
     ```json
     {
       "DeviceName": "/dev/xvda",
       "Ebs": {
         "VolumeSize": 100,
         "VolumeType": "gp3",
         "Iops": 3000,
         "Throughput": 125,
         "DeleteOnTermination": true
       }
     },
     {
       "DeviceName": "/dev/sdf",
       "Ebs": {
         "VolumeSize": 500,
         "VolumeType": "gp3",
         "DeleteOnTermination": true
       }
     }
     ```

3. **고급 네트워킹 구성**:
   - 향상된 네트워킹 활성화
   - 다중 네트워크 인터페이스 구성
   - 배치 그룹 지정
   - 예시:
     ```json
     {
       "NetworkInterfaces": [
         {
           "DeviceIndex": 0,
           "Groups": ["sg-12345"],
           "DeleteOnTermination": true
         }
       ]
     }
     ```

4. **인스턴스 메타데이터 옵션**:
   - IMDSv2 요구 (보안 강화)
   - 홉 제한 설정
   - 예시:
     ```json
     {
       "MetadataOptions": {
         "HttpTokens": "required",
         "HttpPutResponseHopLimit": 2
       }
     }
     ```

5. **사용자 데이터 스크립트**:
   - 인스턴스 시작 시 실행되는 스크립트 제공
   - 클러스터 조인 전 사용자 지정 구성 수행
   - 예시:
     ```bash
     #!/bin/bash
     # 사용자 데이터 스크립트
     mkdir -p /opt/app
     mount -t tmpfs -o size=10G tmpfs /opt/app
     ```

#### 시작 템플릿 생성 및 사용 방법:

1. **AWS Management Console에서 시작 템플릿 생성**:
   - EC2 콘솔 > 시작 템플릿 > 시작 템플릿 생성
   - AMI, 인스턴스 유형, 키 페어, 보안 그룹 등 구성
   - 스토리지, 네트워크 인터페이스, 사용자 데이터 등 고급 설정 구성

2. **eksctl을 사용한 시작 템플릿 기반 노드 그룹 생성**:
   ```yaml
   apiVersion: eksctl.io/v1alpha5
   kind: ClusterConfig
   
   metadata:
     name: my-cluster
     region: us-west-2
   
   managedNodeGroups:
     - name: custom-ng
       launchTemplate:
         id: lt-12345abcdef
         version: "1"
   ```

3. **AWS CLI를 사용한 시작 템플릿 기반 노드 그룹 생성**:
   ```bash
   aws eks create-nodegroup \
     --cluster-name my-cluster \
     --nodegroup-name custom-ng \
     --launch-template id=lt-12345abcdef,version=1 \
     --subnets subnet-12345 subnet-67890 \
     --node-role arn:aws:iam::123456789012:role/EKSNodeRole
   ```

#### 다른 옵션들의 문제점:

- **클러스터 생성 시간 단축**: 시작 템플릿 사용이 클러스터 생성 시간을 단축하지는 않습니다. 오히려 추가 구성으로 인해 약간 더 오래 걸릴 수 있습니다.

- **클러스터 컨트롤 플레인 사용자 지정**: 시작 템플릿은 워커 노드에만 적용되며, EKS 컨트롤 플레인은 AWS에서 관리하므로 시작 템플릿을 통해 사용자 지정할 수 없습니다.

- **자동으로 최신 AMI 버전 사용**: 시작 템플릿은 특정 AMI ID를 지정하므로, 오히려 AMI 버전을 고정하는 효과가 있습니다. 최신 AMI를 자동으로 사용하려면 시작 템플릿을 사용하지 않거나, 정기적으로 시작 템플릿을 업데이트해야 합니다.

시작 템플릿은 EKS 노드 그룹의 고급 사용자 지정이 필요한 경우에 특히 유용하며, 표준 구성으로는 충족할 수 없는 특수한 요구 사항이 있을 때 사용하는 것이 좋습니다.
</details>
2. Amazon EKS 클러스터에서 비용 최적화를 위한 전략이 아닌 것은 무엇인가요?
   - A) 스팟 인스턴스 사용
   - B) 클러스터 오토스케일러 구성
   - C) 모든 워커 노드에 최신 인스턴스 유형 사용
   - D) Fargate 프로필 선택적 사용
   
<details>
<summary>정답 보기</summary>

**정답: C) 모든 워커 노드에 최신 인스턴스 유형 사용**

**설명:**
모든 워커 노드에 최신 인스턴스 유형을 사용하는 것은 반드시 비용 최적화 전략이 아닙니다. 최신 인스턴스 유형은 종종 더 나은 성능과 기능을 제공하지만, 항상 비용 효율적인 것은 아닙니다. 워크로드 요구 사항에 맞는 적절한 인스턴스 유형을 선택하는 것이 더 중요합니다.

#### EKS 클러스터의 실제 비용 최적화 전략:

1. **스팟 인스턴스 사용**:
   - 온디맨드 인스턴스 대비 최대 90% 비용 절감 가능
   - 중단 허용 워크로드에 적합 (배치 작업, 개발/테스트 환경 등)
   - 관리형 노드 그룹에서 스팟 인스턴스 구성:
     ```bash
     eksctl create nodegroup \
       --cluster my-cluster \
       --name spot-ng \
       --node-type m5.large \
       --nodes 2 \
       --nodes-min 1 \
       --nodes-max 5 \
       --spot
     ```
   - 여러 인스턴스 유형을 혼합하여 가용성 향상:
     ```yaml
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     managedNodeGroups:
       - name: spot-ng
         instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
         spot: true
     ```

2. **클러스터 오토스케일러 구성**:
   - 워크로드 요구 사항에 따라 노드 수 자동 조정
   - 사용하지 않는 노드 자동 제거로 비용 절감
   - 설치 및 구성:
     ```bash
     # Helm을 사용한 Cluster Autoscaler 설치
     helm repo add autoscaler https://kubernetes.github.io/autoscaler
     
     helm install cluster-autoscaler autoscaler/cluster-autoscaler \
       --namespace kube-system \
       --set autoDiscovery.clusterName=my-cluster \
       --set awsRegion=us-west-2 \
       --set rbac.create=true
     ```

3. **Fargate 프로필 선택적 사용**:
   - 서버리스 컨테이너 실행 환경으로 노드 관리 오버헤드 제거
   - 사용한 리소스에 대해서만 비용 지불
   - 간헐적 워크로드나 개발/테스트 환경에 적합
   - 특정 네임스페이스나 레이블에 대해서만 Fargate 사용:
     ```bash
     eksctl create fargateprofile \
       --cluster my-cluster \
       --name fp-dev \
       --namespace dev
     ```

4. **적절한 인스턴스 크기 선택**:
   - 워크로드 요구 사항에 맞는 인스턴스 크기 선택
   - 오버프로비저닝 방지
   - 리소스 사용량 모니터링 및 분석:
     ```bash
     kubectl top nodes
     kubectl top pods --all-namespaces
     ```

5. **Graviton(ARM) 기반 인스턴스 사용**:
   - x86 기반 인스턴스 대비 최대 40% 비용 절감 가능
   - 동등한 성능 제공
   - 호환성 확인 필요
   - 예시:
     ```bash
     eksctl create nodegroup \
       --cluster my-cluster \
       --name arm-ng \
       --node-type m6g.large \
       --nodes 2
     ```

6. **예약 인스턴스 또는 Savings Plans 활용**:
   - 장기 약정을 통한 비용 절감
   - 예측 가능한 워크로드에 적합
   - 온디맨드 대비 최대 72% 비용 절감 가능

7. **리소스 요청 및 제한 최적화**:
   - 포드 리소스 요청을 적절히 설정하여 노드 활용도 향상
   - 오버프로비저닝 방지
   - 예시:
     ```yaml
     resources:
       requests:
         cpu: 100m
         memory: 128Mi
       limits:
         cpu: 500m
         memory: 256Mi
     ```

8. **비용 모니터링 및 분석**:
   - AWS Cost Explorer 사용
   - Kubernetes 비용 할당 태그 설정
   - 타사 비용 모니터링 도구 활용 (Kubecost, CloudHealth 등)

#### 최신 인스턴스 유형 사용의 문제점:

1. **비용 증가**:
   - 최신 인스턴스 유형은 종종 이전 세대보다 비쌀 수 있음
   - 모든 워크로드가 최신 인스턴스의 기능을 필요로 하지 않음

2. **오버프로비저닝**:
   - 워크로드 요구 사항을 초과하는 리소스 제공
   - 불필요한 비용 발생

3. **가용성 제한**:
   - 최신 인스턴스 유형은 모든 리전이나 가용 영역에서 사용하지 못할 수 있음
   - 특히 스팟 인스턴스로 사용 시 가용성 제한

4. **호환성 문제**:
   - 일부 워크로드는 특정 인스턴스 유형에서 최적화되어 있을 수 있음
   - 새로운 인스턴스 유형으로 전환 시 테스트 필요

비용 최적화를 위해서는 워크로드 특성, 리소스 요구 사항, 가용성 요구 사항 등을 종합적으로 고려하여 적절한 인스턴스 유형과 크기를 선택하는 것이 중요합니다. 최신 인스턴스 유형이 항상 비용 효율적인 선택은 아니며, 워크로드에 맞는 적절한 인스턴스 유형을 선택하는 것이 더 중요합니다.
</details>
3. Amazon EKS 클러스터에서 프라이빗 클러스터를 구성하는 올바른 방법은 무엇인가요?
   - A) 프라이빗 서브넷에만 노드 배치 및 퍼블릭 엔드포인트 비활성화
   - B) 프라이빗 서브넷에만 노드 배치 및 퍼블릭 엔드포인트 활성화
   - C) 퍼블릭 서브넷에 노드 배치 및 퍼블릭 엔드포인트 비활성화
   - D) VPC 엔드포인트 없이 프라이빗 서브넷에만 노드 배치
   
<details>
<summary>정답 보기</summary>

**정답: A) 프라이빗 서브넷에만 노드 배치 및 퍼블릭 엔드포인트 비활성화**

**설명:**
Amazon EKS 클러스터에서 완전한 프라이빗 클러스터를 구성하려면 프라이빗 서브넷에만 노드를 배치하고 퍼블릭 엔드포인트를 비활성화해야 합니다. 이렇게 하면 클러스터의 Kubernetes API 서버가 인터넷에서 접근할 수 없게 되고, 모든 트래픽이 VPC 내에서만 이루어집니다.

#### 프라이빗 EKS 클러스터 구성 요소:

1. **엔드포인트 액세스 구성**:
   - 퍼블릭 엔드포인트 비활성화
   - 프라이빗 엔드포인트 활성화
   - AWS CLI 구성 예시:
     ```bash
     aws eks update-cluster-config \
       --name my-cluster \
       --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
     ```
   - eksctl 구성 예시:
     ```yaml
     apiVersion: eksctl.io/v1alpha5
     kind: ClusterConfig
     metadata:
       name: my-cluster
       region: us-west-2
     vpc:
       clusterEndpoints:
         publicAccess: false
         privateAccess: true
     ```

2. **노드 배치**:
   - 프라이빗 서브넷에만 노드 배치
   - 퍼블릭 IP 할당 없음
   - 관리형 노드 그룹 구성 예시:
     ```bash
     eksctl create nodegroup \
       --cluster my-cluster \
       --name private-ng \
       --node-type m5.large \
       --nodes 3 \
       --node-private-networking \
       --subnet-ids subnet-private1,subnet-private2
     ```

3. **VPC 엔드포인트 구성**:
   프라이빗 클러스터가 AWS 서비스에 접근하기 위해 필요한 VPC 엔드포인트:
   - com.amazonaws.region.ecr.api
   - com.amazonaws.region.ecr.dkr
   - com.amazonaws.region.s3
   - com.amazonaws.region.logs (선택 사항)
   - com.amazonaws.region.sts (선택 사항)

   ```bash
   # ECR API 엔드포인트 생성
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345 \
     --service-name com.amazonaws.us-west-2.ecr.api \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-private1 subnet-private2 \
     --security-group-ids sg-12345 \
     --private-dns-enabled
   
   # ECR Docker 엔드포인트 생성
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345 \
     --service-name com.amazonaws.us-west-2.ecr.dkr \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-private1 subnet-private2 \
     --security-group-ids sg-12345 \
     --private-dns-enabled
   
   # S3 엔드포인트 생성 (게이트웨이 유형)
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345 \
     --service-name com.amazonaws.us-west-2.s3 \
     --vpc-endpoint-type Gateway \
     --route-table-ids rtb-12345
   ```

4. **네트워크 구성**:
   - 프라이빗 서브넷에 NAT 게이트웨이 또는 VPC 엔드포인트 필요
   - 보안 그룹 규칙으로 트래픽 제한
   - 라우팅 테이블 구성

#### 프라이빗 클러스터 접근 방법:

1. **VPN 또는 Direct Connect를 통한 접근**:
   - AWS Client VPN
   - AWS Site-to-Site VPN
   - AWS Direct Connect

2. **배스천 호스트(Bastion Host)를 통한 접근**:
   - 퍼블릭 서브넷에 배스천 호스트 배치
   - 배스천 호스트에서 클러스터 API 서버에 접근
   ```bash
   # 배스천 호스트에서 kubeconfig 구성
   aws eks update-kubeconfig --name my-cluster --region us-west-2
   ```

3. **AWS Systems Manager Session Manager를 통한 접근**:
   - 인터넷 게이트웨이 없이 EC2 인스턴스에 접근
   - IAM 권한 및 로깅을 통한 접근 제어

#### 다른 옵션들의 문제점:

- **프라이빗 서브넷에만 노드 배치 및 퍼블릭 엔드포인트 활성화**: 퍼블릭 엔드포인트가 활성화되어 있으면 인터넷에서 클러스터 API 서버에 접근할 수 있으므로 완전한 프라이빗 클러스터가 아닙니다. 보안 그룹이나 CIDR 제한으로 접근을 제한할 수 있지만, 여전히 퍼블릭 네트워크에 노출됩니다.

- **퍼블릭 서브넷에 노드 배치 및 퍼블릭 엔드포인트 비활성화**: 노드가 퍼블릭 서브넷에 있으면 인터넷에서 직접 접근할 수 있으므로 완전한 프라이빗 클러스터가 아닙니다. 보안 그룹으로 접근을 제한할 수 있지만, 노드에 퍼블릭 IP가 할당될 수 있습니다.

- **VPC 엔드포인트 없이 프라이빗 서브넷에만 노드 배치**: VPC 엔드포인트 없이 프라이빗 서브넷에 노드를 배치하면 노드가 ECR, S3 등의 AWS 서비스에 접근할 수 없게 됩니다. 이 경우 NAT 게이트웨이를 통해 인터넷에 접근해야 하므로, 완전한 프라이빗 클러스터 구성이 아닙니다.

프라이빗 EKS 클러스터는 높은 수준의 보안이 요구되는 환경에 적합하며, 모든 클러스터 트래픽이 VPC 내에서만 이루어지도록 보장합니다. 그러나 구성이 더 복잡하고, 클러스터 접근을 위한 추가 인프라(VPN, Direct Connect, 배스천 호스트 등)가 필요할 수 있습니다.
</details>
4. Amazon EKS 클러스터에서 노드 그룹 업그레이드 전략으로 올바르지 않은 것은 무엇인가요?
   - A) 롤링 업그레이드
   - B) 블루/그린 배포
   - C) 인플레이스 업그레이드
   - D) 캐니리 배포
   
<details>
<summary>정답 보기</summary>

**정답: C) 인플레이스 업그레이드**

**설명:**
"인플레이스 업그레이드"는 Amazon EKS 노드 그룹의 공식적인 업그레이드 전략이 아닙니다. EKS 관리형 노드 그룹은 기본적으로 롤링 업그레이드 방식을 사용하며, 자체 관리형 노드 그룹의 경우 블루/그린 배포나 캐니리 배포와 같은 전략을 구현할 수 있습니다.

#### EKS 노드 그룹 업그레이드 전략:

1. **롤링 업그레이드 (Rolling Upgrade)**:
   - EKS 관리형 노드 그룹의 기본 업그레이드 방식
   - 노드를 하나씩 교체하여 워크로드 중단 최소화
   - 프로세스:
     1. 새 노드 생성
     2. 기존 노드에 코드네이션(cordoning) 적용 (새 포드 스케줄링 방지)
     3. 기존 노드에서 포드 드레이닝(draining) (포드 이전)
     4. 기존 노드 종료
     5. 다음 노드에 대해 반복
   - 구성 예시:
     ```bash
     # 관리형 노드 그룹 업그레이드
     aws eks update-nodegroup-version \
       --cluster-name my-cluster \
       --nodegroup-name my-nodegroup
     
     # 업그레이드 상태 확인
     aws eks describe-update \
       --name <update-id> \
       --nodegroup-name my-nodegroup \
       --cluster-name my-cluster
     ```

2. **블루/그린 배포 (Blue/Green Deployment)**:
   - 완전히 새로운 노드 그룹 생성 후 트래픽 전환
   - 롤백이 쉽고 위험이 낮음
   - 리소스 사용량이 일시적으로 증가 (두 배의 노드 실행)
   - 구현 단계:
     1. 새 노드 그룹 생성 (그린)
     2. 새 노드 그룹에 워크로드 배포 및 테스트
     3. 트래픽을 새 노드 그룹으로 전환
     4. 기존 노드 그룹 삭제 (블루)
   - 구성 예시:
     ```bash
     # 새 노드 그룹 생성
     eksctl create nodegroup \
       --cluster my-cluster \
       --name my-nodegroup-v2 \
       --node-type m5.large \
       --nodes 3 \
       --node-ami-family AmazonLinux2
     
     # 노드 레이블 확인
     kubectl get nodes --show-labels
     
     # 기존 노드 그룹 삭제
     eksctl delete nodegroup \
       --cluster my-cluster \
       --name my-nodegroup-v1
     ```

3. **캐니리 배포 (Canary Deployment)**:
   - 일부 노드만 먼저 업그레이드하여 위험 최소화
   - 문제 발생 시 영향 범위 제한
   - 점진적인 롤아웃 가능
   - 구현 단계:
     1. 소규모 새 노드 그룹 생성
     2. 일부 워크로드를 새 노드 그룹으로 이동
     3. 모니터링 및 검증
     4. 문제가 없으면 나머지 노드 업그레이드
   - 구성 예시:
     ```bash
     # 캐니리 노드 그룹 생성 (소규모)
     eksctl create nodegroup \
       --cluster my-cluster \
       --name canary-ng \
       --node-type m5.large \
       --nodes 1 \
       --node-labels "deployment=canary"
     
     # 특정 워크로드를 캐니리 노드에 배포
     apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: my-app
     spec:
       template:
         spec:
           nodeSelector:
             deployment: canary
     ```

#### 인플레이스 업그레이드의 문제점:

"인플레이스 업그레이드"라는 용어는 기존 노드를 종료하지 않고 그 자리에서 업그레이드하는 것을 의미할 수 있습니다. 이는 다음과 같은 이유로 EKS 노드 그룹에 적합하지 않습니다:

1. **불변 인프라 원칙 위반**:
   - 클라우드 네이티브 환경에서는 리소스를 수정하기보다 교체하는 것이 권장됨
   - 노드 구성 드리프트 방지

2. **업그레이드 실패 위험**:
   - 인플레이스 업그레이드 중 실패 시 노드 상태가 불안정해질 수 있음
   - 롤백이 어려움

3. **EKS 노드 AMI 구조**:
   - EKS 최적화 AMI는 버전별로 다른 AMI ID를 가짐
   - 인플레이스 업그레이드로는 AMI 변경 불가

4. **관리형 노드 그룹 제한**:
   - EKS 관리형 노드 그룹은 인플레이스 업그레이드를 지원하지 않음
   - 항상 롤링 업그레이드 방식 사용

#### 노드 그룹 업그레이드 모범 사례:

1. **PodDisruptionBudget 구성**:
   - 업그레이드 중 애플리케이션 가용성 보장
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: app-pdb
   spec:
     minAvailable: 2  # 또는 maxUnavailable: 1
     selector:
       matchLabels:
         app: my-app
   ```

2. **충분한 리소스 확보**:
   - 노드 드레이닝 중 포드 재배치를 위한 여유 용량 필요
   - 클러스터 오토스케일러 구성 고려

3. **업그레이드 전 테스트**:
   - 비프로덕션 환경에서 먼저 업그레이드 테스트
   - 애플리케이션 호환성 확인

4. **모니터링 강화**:
   - 업그레이드 중 및 후 시스템 모니터링
   - 이상 징후 조기 발견

EKS 노드 그룹 업그레이드는 워크로드 중단을 최소화하면서 보안 패치, 버그 수정, 새로운 기능을 적용하기 위한 중요한 작업입니다. 롤링 업그레이드, 블루/그린 배포, 캐니리 배포와 같은 전략을 상황에 맞게 선택하여 안전하게 업그레이드를 수행해야 합니다.
</details>
5. Amazon EKS 클러스터에서 노드 부트스트랩 과정 중 발생하는 일이 아닌 것은 무엇인가요?
   - A) kubelet 구성 및 시작
   - B) 클러스터 컨트롤 플레인 구성 요소 설치
   - C) AWS IAM Authenticator 구성
   - D) 노드를 클러스터에 등록
   
<details>
<summary>정답 보기</summary>

**정답: B) 클러스터 컨트롤 플레인 구성 요소 설치**

**설명:**
Amazon EKS 노드 부트스트랩 과정 중에는 클러스터 컨트롤 플레인 구성 요소를 설치하지 않습니다. EKS는 관리형 서비스로, 컨트롤 플레인(API 서버, 컨트롤러 관리자, 스케줄러 등)은 AWS에서 관리하며 워커 노드와는 별도로 실행됩니다. 노드 부트스트랩 과정에서는 노드가 기존 EKS 클러스터에 연결되기 위한 구성만 수행합니다.

#### EKS 노드 부트스트랩 과정에서 실제로 발생하는 일:

1. **kubelet 구성 및 시작**:
   - kubelet 구성 파일 생성 (`/etc/kubernetes/kubelet/kubelet-config.json`)
   - 클러스터 엔드포인트, 인증서, 클러스터 DNS 등 설정
   - kubelet 서비스 시작
   - 예시 구성:
     ```json
     {
       "kind": "KubeletConfiguration",
       "apiVersion": "kubelet.config.k8s.io/v1beta1",
       "address": "0.0.0.0",
       "authentication": {
         "anonymous": {
           "enabled": false
         },
         "webhook": {
           "cacheTTL": "2m0s",
           "enabled": true
         },
         "x509": {
           "clientCAFile": "/etc/kubernetes/pki/ca.crt"
         }
       },
       "clusterDomain": "cluster.local",
       "clusterDNS": ["10.100.0.10"],
       "podCIDR": "",
       "maxPods": 58
     }
     ```

2. **AWS IAM Authenticator 구성**:
   - IAM 인증을 위한 aws-iam-authenticator 설정
   - kubeconfig 파일 생성
   - 노드 IAM 역할 구성
   - 예시 구성:
     ```yaml
     apiVersion: v1
     kind: Config
     clusters:
     - cluster:
         certificate-authority: /etc/kubernetes/pki/ca.crt
         server: https://my-cluster.eks.amazonaws.com
       name: kubernetes
     contexts:
     - context:
         cluster: kubernetes
         user: kubelet
       name: kubelet
     current-context: kubelet
     users:
     - name: kubelet
       user:
         exec:
           apiVersion: client.authentication.k8s.io/v1beta1
           command: aws-iam-authenticator
           args:
             - token
             - -i
             - my-cluster
             - --role
             - arn:aws:iam::123456789012:role/EKSNodeRole
     ```

3. **노드를 클러스터에 등록**:
   - 노드 객체 생성
   - 노드 레이블 및 테인트 설정
   - 클러스터 API 서버에 등록
   - 예시 로그:
     ```
     Node my-node-1 successfully registered with API server
     ```

4. **CNI 플러그인 구성**:
   - Amazon VPC CNI 플러그인 구성
   - 포드 네트워킹 설정
   - IP 주소 할당 구성
   - 예시 구성:
     ```json
     {
       "cniVersion": "0.3.1",
       "name": "aws-vpc",
       "plugins": [
         {
           "name": "aws-vpc",
           "type": "vpc-cni",
           "vethPrefix": "eni",
           "mtu": "9001",
           "ipam": {
             "type": "aws-cni"
           }
         }
       ]
     }
     ```

5. **kube-proxy 설정**:
   - 클러스터 네트워킹을 위한 kube-proxy 구성
   - 서비스 IP 라우팅 설정
   - 예시 구성:
     ```yaml
     apiVersion: kubeproxy.config.k8s.io/v1alpha1
     kind: KubeProxyConfiguration
     bindAddress: 0.0.0.0
     clientConnection:
       acceptContentTypes: ""
       burst: 10
       contentType: application/vnd.kubernetes.protobuf
       kubeconfig: /var/lib/kube-proxy/kubeconfig
       qps: 5
     ```

6. **노드 레이블 및 테인트 적용**:
   - 인스턴스 유형, 가용 영역 등에 기반한 레이블 설정
   - 사용자 지정 레이블 적용
   - 필요한 경우 테인트 적용
   - 예시 명령:
     ```bash
     kubectl label node my-node-1 eks.amazonaws.com/nodegroup=my-nodegroup
     kubectl label node my-node-1 topology.kubernetes.io/zone=us-west-2a
     ```

#### 부트스트랩 스크립트:

EKS 노드 부트스트랩은 `/etc/eks/bootstrap.sh` 스크립트를 통해 수행됩니다. 이 스크립트는 다음과 같은 매개변수를 받을 수 있습니다:

```bash
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker' \
  --b64-cluster-ca <base64-encoded-ca> \
  --apiserver-endpoint <api-server-endpoint> \
  --dns-cluster-ip 10.100.0.10
```

사용자 지정 시작 템플릿을 사용하는 경우, 사용자 데이터 섹션에서 이 스크립트를 호출하여 추가 구성을 수행할 수 있습니다:

```bash
#!/bin/bash
set -ex
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=environment=prod,node-type=worker' \
  --max-pods 110
```

#### 클러스터 컨트롤 플레인 구성 요소:

EKS 클러스터의 컨트롤 플레인 구성 요소는 AWS에서 관리하며, 노드 부트스트랩 과정과는 별개입니다:

- API 서버
- 컨트롤러 관리자
- 스케줄러
- etcd
- CoreDNS

이러한 구성 요소는 AWS에서 관리하는 인프라에서 실행되며, 고가용성과 확장성을 보장합니다. 노드는 이러한 컨트롤 플레인 구성 요소에 연결되기만 하고, 직접 설치하거나 관리하지 않습니다.

따라서, Amazon EKS 노드 부트스트랩 과정 중 발생하지 않는 일은 "클러스터 컨트롤 플레인 구성 요소 설치"입니다.
</details>
