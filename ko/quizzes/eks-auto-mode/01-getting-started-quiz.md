# EKS Auto Mode 시작하기 퀴즈

> **관련 문서**: [EKS Auto Mode 시작하기](../../eks-auto-mode/01-getting-started.md)

## 객관식 문제

### 1. EKS Auto Mode의 관리형 컴퓨팅 프로비저닝 기반 기술은 무엇인가요?

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>정답 보기</summary>

**정답: B) Karpenter**

**설명:**
Auto Mode는 AWS가 운영하는 Karpenter 기반 컨트롤러를 사용합니다. Auto Mode용 Karpenter 컨트롤러를 별도로 설치하지 않습니다. 워크로드 requests, NodePool/NodeClass, 중단 제약과 애플리케이션 autoscaling 구성은 여전히 사용자 책임입니다. 인프라 자동화가 애플리케이션 가용성 책임까지 AWS로 이전하지는 않습니다.

</details>

### 2. 새 Auto Mode 클러스터의 Kubernetes 버전은 어떻게 선택해야 하나요?

- A) 모든 upstream Kubernetes 버전을 EKS에서 즉시 사용할 수 있다
- B) 초기 기능 지원 하한이 현재 지원을 보장하므로 항상 1.29를 쓴다
- C) 현재 AWS EKS 지원 일정과 리전별 가용성을 확인한다
- D) 항상 확장 지원 버전을 선택한다

<details>
<summary>정답 보기</summary>

**정답: C) 현재 AWS EKS 지원 일정과 리전별 가용성을 확인한다**

**설명:**
초기 기능 지원 하한인 1.29+는 현재 지원 보장이 아닙니다. 2026년 9월 12일에는 EKS 1.34–1.36이 표준 지원 대상이며 본문 예제는 1.36을 사용합니다. [AWS 버전 일정](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)과 적용 요금을 확인하세요. 이전 퀴즈의 근거 없는 고정 NodePool·노드 수에 의존하지 말고 실제 서비스 할당량과 서브넷 용량을 확인해야 합니다.

</details>

### 3. eksctl로 새 클러스터를 생성할 때 Auto Mode를 활성화하는 플래그는 무엇인가요?

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>정답 보기</summary>

**정답: B) `eksctl create cluster --enable-auto-mode`**

**설명:**
검사한 eksctl 0.229.0에서 `--enable-auto-mode` 생성 플래그는 유효합니다. 본문은 역할과 네트워크를 명확히 지정하도록 `autoModeConfig.enabled`, `nodePools`, `nodeRoleARN`을 포함한 검토된 구성 파일을 사용합니다.

기존 eksctl 관리 클러스터에는 `eksctl update auto-mode-config --config-file <reviewed-config>`를 사용합니다. `eksctl update cluster`는 deprecated된 컨트롤 플레인 업그레이드 명령이며 Auto Mode 활성화 명령이 아닙니다. 기능 활성화만을 위해 노드 그룹 drain을 추가하지 마세요. [eksctl 참조](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)를 확인하세요.

</details>

### 4. Auto Mode 프로비저닝 시간에 관한 올바른 설명은 무엇인가요?

- A) 모든 노드와 Pod가 5–10초 안에 준비된다
- B) 용량·부트스트랩·이미지 다운로드·배치 제약에 따라 달라지므로 워크로드를 측정한다
- C) AWS가 모든 프로비저닝의 5분 이내 완료를 보장한다
- D) 컨트롤 플레인의 ACTIVE 상태가 모든 애플리케이션 준비 완료를 증명한다

<details>
<summary>정답 보기</summary>

**정답: B) 용량·부트스트랩·이미지 다운로드·배치 제약에 따라 달라지므로 워크로드를 측정한다**

**설명:**
이 예제에는 고정된 종단 간 준비 시간 보장이 없습니다. 노드 시작, 노드 readiness와 애플리케이션 readiness를 구분해야 합니다.

이전 퀴즈에는 총 **40–90초**, EC2 시작 **10–30초**, AMI 부팅 **20–40초**, kubelet 등록 **5–10초**, 스케줄링 **1–5초**가 제시됐습니다. 이 수치는 **출처를 확인하지 못한 과거 교육용 추정값**으로 보존하며 실측 결과나 현재 SLO가 아닙니다. 이번 감사에서 측정 근거를 확인하지 못했습니다. Auto Mode는 관리형 Bottlerocket 변형을 선택하므로, 더 빠른 부팅을 위해 AL2023과 Bottlerocket 중 선택하라는 이전 설명도 부정확했습니다.

</details>

### 5. Terraform `aws_eks_cluster` 리소스에서 compute를 구성하는 블록은 무엇인가요?

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>정답 보기</summary>

**정답: B) `compute_config { enabled = true }`**

**설명:**
리소스는 `compute_config`를 사용하지만 compute만으로는 충분하지 않습니다. Auto Mode의 compute, load balancing, block storage를 함께 구성하고, API 기반 접근과 기본 풀용 적절한 노드 역할을 제공해야 합니다. 아래 조각은 검토된 역할·provider·변수가 다른 곳에 정의돼 있다고 가정하며 독립적인 배포 예제가 아닙니다.

```hcl
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.auto_cluster_role_arn
  version  = "1.36"

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true # Dedicated lab only.
  }
  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = var.auto_node_role_arn
  }
  kubernetes_network_config {
    elastic_load_balancing {
      enabled = true
    }
  }
  storage_config {
    block_storage {
      enabled = true
    }
  }
  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = [var.api_client_cidr]
  }
}
```

본문은 EKS 모듈 21.25.0을 사용합니다. AWS provider 6.59 이상이 필요하며 6.64.0으로 검증했습니다. 이 버전의 모듈 입력도 `compute_config`이며, 이전 모듈 v20의 `cluster_compute_config`는 리소스 블록 이름이 아닙니다. 적용 전에 저장된 plan과 역할의 필수 정책을 검토하세요.

</details>

### 6. Auto Mode **노드 IAM 역할**이 신뢰해야 하는 서비스 주체는 무엇인가요?

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>정답 보기</summary>

**정답: B) ec2.amazonaws.com**

**설명:**
노드 역할은 EC2 관리형 인스턴스에 연결되며 `ec2.amazonaws.com`을 신뢰합니다. 별도의 **클러스터 역할**은 `eks.amazonaws.com`을 신뢰하고 Auto Mode를 위해 `sts:AssumeRole`과 함께 `sts:TagSession`이 필요합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

노드 역할에는 `AmazonEKSWorkerNodeMinimalPolicy`와 `AmazonEC2ContainerRegistryPullOnly`를 사용합니다. 애플리케이션의 AWS 권한은 Pod Identity 등으로 연결한 별도 워크로드 역할에 둡니다. [AWS 역할 요구 사항](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)을 확인하세요.

</details>
