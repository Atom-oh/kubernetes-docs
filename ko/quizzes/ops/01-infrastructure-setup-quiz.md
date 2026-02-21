# 인프라 구성 기초 퀴즈

> **관련 문서**: [인프라 구성 기초](../../ops/01-infrastructure-setup.md)

## 객관식 문제

### 1. Terraform 3-Layer 아키텍처에서 Network Layer의 주요 역할은 무엇인가요?

- A) EKS 클러스터와 애드온 배포
- B) ArgoCD, Prometheus 등 플랫폼 서비스 배포
- C) VPC, 서브넷, NAT Gateway 등 네트워크 인프라 구성
- D) CI/CD 파이프라인 설정

<details>
<summary>정답 보기</summary>

**정답: C) VPC, 서브넷, NAT Gateway 등 네트워크 인프라 구성**

**설명:**
Terraform 3-Layer 아키텍처에서 Network Layer는 가장 기반이 되는 계층으로, VPC, 서브넷, Internet Gateway, NAT Gateway, Route Table 등 핵심 네트워크 인프라를 구성합니다. 이 계층은 변경 빈도가 가장 낮고 blast radius가 가장 큽니다.

</details>

### 2. Terraform S3 Backend를 사용할 때 DynamoDB 테이블의 역할은 무엇인가요?

- A) Terraform 상태 파일 저장
- B) 동시 실행 방지를 위한 State Locking
- C) Terraform 로그 기록
- D) 리소스 의존성 추적

<details>
<summary>정답 보기</summary>

**정답: B) 동시 실행 방지를 위한 State Locking**

**설명:**
DynamoDB 테이블은 State Locking을 위해 사용됩니다. 여러 사용자나 CI/CD 파이프라인이 동시에 terraform apply를 실행할 때 충돌을 방지합니다. 상태 파일 자체는 S3 버킷에 저장되며, DynamoDB는 Lock ID를 관리하여 동시 접근을 제어합니다.

</details>

### 3. terraform_remote_state 데이터 소스의 주요 용도는 무엇인가요?

- A) 로컬 상태 파일 백업
- B) 다른 Terraform 스택의 output 값 참조
- C) Terraform 버전 관리
- D) 리소스 삭제 추적

<details>
<summary>정답 보기</summary>

**정답: B) 다른 Terraform 스택의 output 값 참조**

**설명:**
terraform_remote_state 데이터 소스를 사용하면 다른 Terraform 스택(State)의 output 값을 참조할 수 있습니다. 예를 들어, Cluster Layer에서 Network Layer의 VPC ID나 서브넷 ID를 참조할 때 사용합니다. 이를 통해 계층 간 의존성을 느슨하게 유지하면서도 필요한 정보를 공유할 수 있습니다.

</details>

### 4. EKS Auto Mode에서 기본적으로 활성화되지 않는 Node Pool은 무엇인가요?

- A) general-purpose
- B) system
- C) gpu
- D) A와 C 모두

<details>
<summary>정답 보기</summary>

**정답: C) gpu**

**설명:**
EKS Auto Mode에서는 general-purpose와 system Node Pool이 기본적으로 활성화됩니다. GPU Node Pool은 별도로 명시적으로 활성화해야 합니다. `node_pools = { general-purpose = { }, system = { }, gpu = { } }` 형태로 설정하면 GPU 노드 풀도 사용할 수 있습니다.

</details>

### 5. Terraform 3-Layer 아키텍처에서 변경 빈도가 가장 높은 계층은 무엇인가요?

- A) Network Layer
- B) Cluster Layer
- C) Platform Layer
- D) 모든 계층이 동일

<details>
<summary>정답 보기</summary>

**정답: C) Platform Layer**

**설명:**
Platform Layer는 ArgoCD, Prometheus, 애플리케이션 네임스페이스 등을 관리하며 변경 빈도가 가장 높습니다. Network Layer는 VPC 같은 기반 인프라로 변경이 가장 적고, Cluster Layer는 EKS 클러스터 설정으로 중간 정도의 변경 빈도를 가집니다.

</details>

### 6. EKS Pod Identity를 설정할 때 필요한 Terraform 리소스 조합은 무엇인가요?

- A) aws_iam_role + aws_iam_role_policy_attachment만
- B) aws_iam_role + aws_eks_pod_identity_association
- C) aws_iam_policy + aws_iam_user
- D) aws_eks_addon + aws_iam_instance_profile

<details>
<summary>정답 보기</summary>

**정답: B) aws_iam_role + aws_eks_pod_identity_association**

**설명:**
EKS Pod Identity를 설정하려면 먼저 aws_iam_role을 생성하고(assume_role_policy에 pods.eks.amazonaws.com 서비스 포함), 그 다음 aws_eks_pod_identity_association 리소스로 클러스터, 네임스페이스, 서비스 어카운트와 IAM 역할을 연결합니다.

</details>

### 7. Terraform S3 Backend 설정에서 권장되는 S3 버킷 설정은 무엇인가요?

- A) 버전 관리 비활성화, 암호화 비활성화
- B) 버전 관리 활성화, 서버 측 암호화 활성화
- C) 퍼블릭 액세스 허용, 버전 관리 활성화
- D) 암호화만 활성화, 버전 관리 비활성화

<details>
<summary>정답 보기</summary>

**정답: B) 버전 관리 활성화, 서버 측 암호화 활성화**

**설명:**
Terraform 상태 파일에는 민감한 정보가 포함될 수 있으므로 S3 버킷에는 버전 관리(실수로 삭제 시 복구 가능), 서버 측 암호화(KMS 또는 SSE-S3), 퍼블릭 액세스 차단을 설정해야 합니다. 버전 관리를 통해 상태 파일 변경 이력도 추적할 수 있습니다.

</details>

### 8. EKS Auto Mode Terraform 설정에서 cluster_compute_config 블록의 역할은 무엇인가요?

- A) 클러스터 로깅 설정
- B) Auto Mode 활성화 및 Node Role 지정
- C) VPC CNI 설정
- D) 클러스터 엔드포인트 액세스 설정

<details>
<summary>정답 보기</summary>

**정답: B) Auto Mode 활성화 및 Node Role 지정**

**설명:**
cluster_compute_config 블록은 EKS Auto Mode를 활성화하고(enabled = true), 노드가 사용할 IAM Role ARN을 지정합니다. 이 설정을 통해 EKS가 자동으로 노드를 프로비저닝하고 관리할 수 있게 됩니다.

</details>

### 9. Terraform 3-Layer 아키텍처에서 계층 분리의 주요 이점이 아닌 것은 무엇인가요?

- A) Blast Radius 최소화
- B) 팀별 책임 분리 가능
- C) 모든 리소스 동시 배포 가능
- D) 독립적인 상태 파일 관리

<details>
<summary>정답 보기</summary>

**정답: C) 모든 리소스 동시 배포 가능**

**설명:**
계층 분리의 이점은 Blast Radius 최소화(한 계층의 변경이 다른 계층에 영향 최소화), 팀별 책임 분리, 독립적인 상태 파일 관리입니다. 오히려 계층 간에는 의존성이 있어 순차적으로 배포해야 합니다(Network → Cluster → Platform).

</details>

### 10. EKS VPC 구성에서 프라이빗 서브넷에 필요한 태그는 무엇인가요?

- A) kubernetes.io/role/elb = 1
- B) kubernetes.io/role/internal-elb = 1
- C) kubernetes.io/cluster/NAME = shared
- D) B와 C 모두

<details>
<summary>정답 보기</summary>

**정답: D) B와 C 모두**

**설명:**
EKS 프라이빗 서브넷에는 `kubernetes.io/role/internal-elb = 1` 태그(Internal Load Balancer용)와 `kubernetes.io/cluster/CLUSTER_NAME = shared` 태그(클러스터 소유권 표시)가 필요합니다. 퍼블릭 서브넷에는 `kubernetes.io/role/elb = 1` 태그를 사용합니다.

</details>
