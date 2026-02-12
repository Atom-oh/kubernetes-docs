# EKS 클러스터 생성 - 3부

## AWS Management Console을 사용한 클러스터 생성

AWS Management Console을 사용하여 EKS 클러스터를 생성하는 단계는 다음과 같습니다:

![AWS Management Console을 통한 EKS 클러스터 생성 워크플로우](../assets/generated-diagrams/eks_console_cluster_creation_workflow.drawio)

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

## AWS CLI를 사용한 클러스터 생성

AWS CLI를 사용하여 EKS 클러스터를 생성하는 과정은 여러 단계로 이루어져 있습니다. 이 방법은 더 많은 제어가 필요한 경우에 유용합니다.

![AWS CLI를 통한 EKS 클러스터 생성 워크플로우](../assets/generated-diagrams/eks_cli_cluster_creation_workflow.drawio)

### 1. 클러스터 IAM 역할 생성

EKS 클러스터에는 Kubernetes 컨트롤 플레인이 AWS 리소스를 관리할 수 있도록 하는 IAM 역할이 필요합니다.

```bash
# 역할 생성
aws iam create-role \
  --role-name EKSClusterRole \
  --assume-role-policy-document '{
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
  }'

# 필요한 정책 연결
aws iam attach-role-policy \
  --role-name EKSClusterRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
```

### 2. VPC 및 서브넷 생성

EKS 클러스터에는 VPC와 서브넷이 필요합니다. 기존 VPC를 사용하거나 새 VPC를 생성할 수 있습니다.

```bash
# VPC 생성
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=EKS-VPC}]' \
  --query Vpc.VpcId \
  --output text

# 서브넷 생성
aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-west-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Subnet-1}]' \
  --query Subnet.SubnetId \
  --output text

aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-west-2b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Subnet-2}]' \
  --query Subnet.SubnetId \
  --output text
```

### 3. 클러스터 보안 그룹 생성

EKS 클러스터에는 보안 그룹이 필요합니다.

```bash
# 보안 그룹 생성
aws ec2 create-security-group \
  --group-name EKS-Cluster-SG \
  --description "Security group for EKS cluster" \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --query GroupId \
  --output text

# 인바운드 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxxxxxxxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### 4. EKS 클러스터 생성

이제 EKS 클러스터를 생성할 수 있습니다.

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
  --resources-vpc-config subnetIds=subnet-xxxxxxxxxxxxxxxxx,subnet-yyyyyyyyyyyyyyyyy,securityGroupIds=sg-zzzzzzzzzzzzzzzzz \
  --kubernetes-version 1.26
```

클러스터 생성이 완료될 때까지 기다립니다. 클러스터 상태를 확인하려면 다음 명령을 실행합니다:

```bash
aws eks describe-cluster \
  --name my-cluster \
  --query "cluster.status"
```

### 5. 노드 IAM 역할 생성

EKS 노드에는 AWS 리소스에 액세스할 수 있는 IAM 역할이 필요합니다.

```bash
# 역할 생성
aws iam create-role \
  --role-name EKSNodeRole \
  --assume-role-policy-document '{
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
  }'

# 필요한 정책 연결
aws iam attach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam attach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

aws iam attach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

### 6. 노드 그룹 생성

이제 노드 그룹을 생성할 수 있습니다.

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --node-role arn:aws:iam::123456789012:role/EKSNodeRole \
  --subnets subnet-xxxxxxxxxxxxxxxxx subnet-yyyyyyyyyyyyyyyyy \
  --disk-size 80 \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --instance-types m5.large
```

노드 그룹 생성이 완료될 때까지 기다립니다. 노드 그룹 상태를 확인하려면 다음 명령을 실행합니다:

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --query "nodegroup.status"
```

### 7. kubeconfig 구성

클러스터에 액세스하려면 kubeconfig 파일을 구성해야 합니다.

```bash
aws eks update-kubeconfig \
  --name my-cluster \
  --region us-west-2
```

### 8. 클러스터 확인

클러스터가 올바르게 구성되었는지 확인합니다.

```bash
kubectl get nodes
```

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [EKS 클러스터 생성 - 3부 퀴즈](../quizzes/eks/02-eks-cluster-creation-part3-quiz.md)를 풀어보세요.
