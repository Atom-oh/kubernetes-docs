# 인프라 구성 고급 퀴즈

> **관련 문서**: [인프라 구성 고급](../../ops/02-infrastructure-advanced.md)

## 객관식 문제

### 1. NLB Weighted Target Group에서 blue/green 배포 시 5:5 비율 설정의 의미는 무엇인가요?

- A) 5개의 인스턴스를 각 클러스터에 배포
- B) 트래픽을 두 클러스터에 50%씩 분배
- C) 5초마다 트래픽 전환
- D) 5개의 가용 영역 사용

<details>
<summary>정답 보기</summary>

**정답: B) 트래픽을 두 클러스터에 50%씩 분배**

**설명:**
NLB의 Weighted Target Group을 사용하면 각 Target Group에 가중치를 부여하여 트래픽을 분배할 수 있습니다. 5:5 비율은 blue 클러스터와 green 클러스터에 각각 50%의 트래픽을 분배한다는 의미입니다. 이를 통해 점진적인 트래픽 전환이나 카나리 배포가 가능합니다.

</details>

### 2. Single Zone 클러스터 구축 시 특정 가용 영역에만 노드를 배포하기 위해 사용하는 Kubernetes 기능은 무엇인가요?

- A) PodAffinity
- B) TopologySpreadConstraints
- C) NodeSelector 또는 NodeAffinity
- D) Taints and Tolerations

<details>
<summary>정답 보기</summary>

**정답: C) NodeSelector 또는 NodeAffinity**

**설명:**
특정 가용 영역에만 노드를 배포하려면 NodeSelector나 NodeAffinity를 사용합니다. `topology.kubernetes.io/zone: ap-northeast-2a` 같은 레이블을 지정하여 노드가 특정 AZ에만 생성되도록 제한할 수 있습니다. TopologySpreadConstraints는 Pod 분산에 사용됩니다.

</details>

### 3. Route53 Weighted Routing Policy의 주요 용도는 무엇인가요?

- A) 지리적 위치 기반 라우팅
- B) 장애 조치(Failover) 라우팅
- C) 여러 엔드포인트에 트래픽 비율 분배
- D) 지연 시간 기반 라우팅

<details>
<summary>정답 보기</summary>

**정답: C) 여러 엔드포인트에 트래픽 비율 분배**

**설명:**
Route53 Weighted Routing Policy는 동일한 도메인에 대해 여러 레코드를 생성하고 각각에 가중치를 부여하여 트래픽을 분배합니다. blue/green 배포 시 트래픽 비율을 조절하거나, 새 버전으로 점진적으로 트래픽을 이동할 때 유용합니다.

</details>

### 4. EKS Auto Mode에서 특정 가용 영역에만 노드를 생성하도록 제한하는 방법은 무엇인가요?

- A) EKS 콘솔에서 직접 설정
- B) NodePool의 subnet 설정으로 특정 AZ의 서브넷만 지정
- C) AWS CLI로 노드 수동 생성
- D) EC2 Auto Scaling Group 설정 변경

<details>
<summary>정답 보기</summary>

**정답: B) NodePool의 subnet 설정으로 특정 AZ의 서브넷만 지정**

**설명:**
EKS Auto Mode에서는 NodePool 설정 시 특정 가용 영역의 서브넷만 지정하여 노드 생성 위치를 제한할 수 있습니다. 예를 들어, a 존 전용 클러스터는 ap-northeast-2a의 서브넷만, c 존 전용 클러스터는 ap-northeast-2c의 서브넷만 지정합니다.

</details>

### 5. Blue/Green 클러스터 아키텍처에서 데이터 레이어를 클러스터 외부에 두는 이유는 무엇인가요?

- A) 비용 절감
- B) 성능 향상
- C) 클러스터 전환 시에도 데이터 영속성 유지
- D) 보안 강화

<details>
<summary>정답 보기</summary>

**정답: C) 클러스터 전환 시에도 데이터 영속성 유지**

**설명:**
데이터베이스(RDS, ElastiCache 등)를 클러스터 외부에 두면 blue에서 green으로 클러스터를 전환하거나 클러스터를 재생성해도 데이터가 유지됩니다. 이를 통해 무중단 배포와 롤백이 가능합니다.

</details>

### 6. NLB Health Check 설정에서 unhealthy_threshold의 역할은 무엇인가요?

- A) 건강한 것으로 판단하기 위한 연속 성공 횟수
- B) 비정상으로 판단하기 위한 연속 실패 횟수
- C) 헬스 체크 간격
- D) 헬스 체크 타임아웃

<details>
<summary>정답 보기</summary>

**정답: B) 비정상으로 판단하기 위한 연속 실패 횟수**

**설명:**
unhealthy_threshold는 타겟을 비정상(unhealthy)으로 판단하기 위해 필요한 연속 헬스 체크 실패 횟수입니다. 예를 들어 값이 3이면 3번 연속 헬스 체크에 실패해야 해당 타겟이 비정상으로 표시되고 트래픽이 차단됩니다.

</details>

### 7. Terraform에서 blue/green 클러스터 전환을 위한 가중치 변경 시 사용하는 접근 방식은 무엇인가요?

- A) 클러스터를 삭제하고 재생성
- B) terraform variable로 가중치를 정의하고 값 변경 후 apply
- C) AWS 콘솔에서 수동으로 변경
- D) kubectl로 직접 설정 변경

<details>
<summary>정답 보기</summary>

**정답: B) terraform variable로 가중치를 정의하고 값 변경 후 apply**

**설명:**
Terraform에서는 `variable "blue_weight"`, `variable "green_weight"` 같은 변수를 정의하고, Target Group Forward 설정에서 이 변수를 참조합니다. 가중치 변경이 필요하면 변수 값만 수정하고 terraform apply를 실행하면 됩니다.

</details>

### 8. Single Zone 클러스터의 장점이 아닌 것은 무엇인가요?

- A) 동일 AZ 내 낮은 네트워크 지연 시간
- B) Cross-AZ 데이터 전송 비용 절감
- C) 가용 영역 장애 시에도 서비스 지속 가능
- D) 데이터 지역성(Data Locality) 확보

<details>
<summary>정답 보기</summary>

**정답: C) 가용 영역 장애 시에도 서비스 지속 가능**

**설명:**
Single Zone 클러스터는 하나의 가용 영역에만 존재하므로 해당 AZ에 장애가 발생하면 서비스가 중단됩니다. 이는 단점이며, 이를 보완하기 위해 다른 AZ에 별도의 클러스터(예: green)를 운영하여 장애 조치할 수 있습니다.

</details>

### 9. NLB Listener Rule에서 forward action의 target_groups 설정 시 weight 속성의 유효 범위는 무엇인가요?

- A) 0-1 (소수점)
- B) 0-100 (백분율)
- C) 0-999 (상대적 가중치)
- D) 1-10 (정수)

<details>
<summary>정답 보기</summary>

**정답: C) 0-999 (상대적 가중치)**

**설명:**
NLB/ALB의 forward action에서 target_groups의 weight는 0부터 999까지의 정수 값을 가집니다. 이는 절대적인 백분율이 아닌 상대적인 가중치이며, 모든 타겟 그룹의 가중치 합계에 대한 비율로 트래픽이 분배됩니다.

</details>

### 10. Blue/Green 클러스터 구성에서 공통 인프라로 분리해야 하는 것이 아닌 것은 무엇인가요?

- A) RDS 데이터베이스
- B) ElastiCache
- C) Pod Deployment 설정
- D) Route53 DNS 레코드

<details>
<summary>정답 보기</summary>

**정답: C) Pod Deployment 설정**

**설명:**
Pod Deployment 설정은 각 클러스터 내부에 존재하는 애플리케이션 워크로드이므로 공통 인프라가 아닙니다. RDS, ElastiCache는 데이터 영속성을 위해, Route53과 NLB는 트래픽 라우팅을 위해 클러스터 외부의 공통 인프라로 분리합니다.

</details>
