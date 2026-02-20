# EKS Auto Mode 시작하기 퀴즈

> **관련 문서**: [EKS Auto Mode 시작하기](../../eks-auto-mode/01-getting-started.md)

## 객관식 문제

### 1. EKS Auto Mode의 내부 기반 기술은 무엇인가요?

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>정답 보기</summary>

**정답: B) Karpenter**

**설명:**
EKS Auto Mode는 Karpenter를 기반으로 동작하지만, AWS가 관리하는 컨트롤 플레인 내에서 실행됩니다. 사용자가 별도의 노드 관리 컴포넌트를 설치하거나 구성할 필요 없이 AWS가 모든 것을 관리합니다.

**EKS Auto Mode의 특징:**
- Karpenter 기반 자동화된 노드 관리
- AWS 컨트롤 플레인에서 실행
- 워크로드 요구사항에 따른 최적 인스턴스 자동 선택
- 수십 초 내 빠른 스케일링

</details>

### 2. EKS Auto Mode를 사용하기 위한 최소 EKS 버전은 무엇인가요?

- A) 1.27
- B) 1.28
- C) 1.29
- D) 1.30

<details>
<summary>정답 보기</summary>

**정답: C) 1.29**

**설명:**
EKS Auto Mode는 EKS 버전 1.29 이상에서만 사용할 수 있습니다.

**주요 제한 사항:**
- 최소 EKS 버전: 1.29
- 클러스터당 최대 NodePool: 100개
- NodePool당 최대 노드: 1000개
- 클러스터당 최대 노드: 5000개

</details>

### 3. eksctl을 사용하여 Auto Mode가 활성화된 새 클러스터를 생성하는 올바른 방법은 무엇인가요?

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>정답 보기</summary>

**정답: B) `eksctl create cluster --enable-auto-mode`**

**설명:**
eksctl 0.200.0 이상에서 `--enable-auto-mode` 플래그를 사용하여 Auto Mode가 활성화된 클러스터를 생성할 수 있습니다.

```bash
# 새 클러스터 생성 시 Auto Mode 활성화
eksctl create cluster \
    --name my-cluster \
    --region ap-northeast-2 \
    --enable-auto-mode

# 기존 클러스터에서 Auto Mode 활성화
eksctl update cluster \
    --name my-cluster \
    --enable-auto-mode
```

</details>

### 4. Auto Mode에서 노드 프로비저닝의 일반적인 예상 시간은 얼마인가요?

- A) 5-10초
- B) 40-90초
- C) 3-5분
- D) 10-15분

<details>
<summary>정답 보기</summary>

**정답: B) 40-90초**

**설명:**
EKS Auto Mode의 노드 프로비저닝 타임라인은 다음과 같습니다:
- EC2 인스턴스 시작: 10-30초
- AMI 부팅: 20-40초
- kubelet 등록: 5-10초
- Pod 스케줄링: 1-5초
- **총 예상 시간: 40-90초**

Bottlerocket AMI를 사용하면 AL2023보다 더 빠른 부팅 시간을 얻을 수 있습니다.

</details>

### 5. Terraform을 사용하여 기존 EKS 클러스터에서 Auto Mode를 활성화하려면 어떤 블록을 추가해야 하나요?

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>정답 보기</summary>

**정답: B) `compute_config { enabled = true }`**

**설명:**
Terraform AWS Provider 5.79.0 이상에서 `compute_config` 블록을 사용하여 Auto Mode를 활성화합니다.

```hcl
resource "aws_eks_cluster" "main" {
  name     = "my-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = "1.31"

  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = aws_iam_role.node.arn
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
    subnet_ids = var.subnet_ids
  }
}
```

</details>

### 6. Auto Mode 클러스터에 필요한 IAM 역할의 신뢰 관계에서 허용해야 하는 서비스 주체는 무엇인가요?

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>정답 보기</summary>

**정답: B) ec2.amazonaws.com**

**설명:**
Auto Mode 노드가 사용하는 IAM 역할은 EC2 서비스 주체를 신뢰해야 합니다. 노드가 EC2 인스턴스로 실행되기 때문입니다.

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

필요한 관리형 정책:
- `AmazonEKSWorkerNodeMinimalPolicy`
- `AmazonEC2ContainerRegistryPullOnly`

</details>
