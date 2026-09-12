# 인프라 구성 고급 퀴즈

> **관련 문서**: [인프라 구성 고급](../../ops/02-infrastructure-advanced.md)

## 객관식 문제

### 1. NLB 가중치 5:5의 의미는?

- A) 각 클러스터에 노드 5개를 만든다
- B) 새 플로우를 상대적으로 동일한 비율로 분배하도록 설정한다
- C) 5초 안에 기존 연결이 모두 이동한다
- D) 합계가 100이 아니므로 잘못된 값이다

<details>
<summary>정답 보기</summary>

**정답: B) 새 플로우를 상대적으로 동일한 비율로 분배하도록 설정한다**

NLB 가중치는 0–999 정수의 상대값입니다. 실제 바이트/요청 비율은 플로우 크기·stickiness·관측 기간에 따라 달라질 수 있습니다.

</details>

### 2. NLB weight를 0으로 내릴 때 고려할 점은?

- A) 기존 연결은 반드시 자연 종료할 때까지 유지된다
- B) 현재 가이드는 잠시 후 기존 연결도 종료된다고 설명하므로 재연결 영향을 검증한다
- C) deregistration delay가 모든 전환 시간을 보장한다
- D) 변경 API 성공 즉시 모든 트래픽이 이동한다

<details>
<summary>정답 보기</summary>

**정답: B) 현재 가이드는 잠시 후 기존 연결도 종료된다고 설명하므로 재연결 영향을 검증한다**

일반 weight 변경과 0 전환을 구분합니다. 제어면 설정 성공과 실제 플로우 전환은 별개이며 NewFlowCount·ActiveFlowCount·오류율·지연을 확인합니다.

</details>

### 3. blue와 green DNS가 같은 공유 NLB를 가리킬 때, DNS weight로 무엇을 할 수 있나요?

- A) NLB 뒤의 타겟 그룹을 독립적으로 선택한다
- B) DNS 이름만으로 AZ를 고정한다
- C) 같은 LB를 선택할 뿐 클러스터별 타겟 그룹을 선택하지 못한다
- D) 동일한 DB 복제본으로 자동 전환한다

<details>
<summary>정답 보기</summary>

**정답: C) 같은 LB를 선택할 뿐 클러스터별 타겟 그룹을 선택하지 못한다**

DNS 선택을 사용하려면 각 클러스터로 이어지는 별도 실제 LB endpoint가 필요합니다. NLB forward weight와 DNS record weight는 다른 계층의 제어입니다.

</details>

### 4. 특정 AZ의 Auto Mode 노드를 사용하는 파드 배치에 대한 설명은?

- A) Pod nodeSelector가 혼자 노드를 생성한다
- B) NodePool에 subnet_ids를 넣으면 된다
- C) Pod 선택 조건, NodePool requirements, NodeClass subnet 선택을 함께 맞춘다
- D) blue라는 클러스터 이름만 지정하면 된다

<details>
<summary>정답 보기</summary>

**정답: C) Pod 선택 조건, NodePool requirements, NodeClass subnet 선택을 함께 맞춘다**

NodeSelector/affinity는 적합한 노드를 고릅니다. 오토스케일러의 생성 범위와 taint/toleration도 맞아야 하며 EKS의 리전 컨트롤 플레인과 워커 배치를 구분합니다.

</details>

### 5. 외부 IaC가 TG 수명 주기를 소유하는 이 예제의 TGB는?

- A) Auto Mode 내장 API로 바꿔도 삭제 동작이 항상 같다
- B) 별도 AWS Load Balancer Controller의 elbv2.k8s.aws/v1beta1이며 내장 Auto Mode TGB와 구분한다
- C) Service나 targetPort 없이 ARN만 넣으면 된다
- D) Terraform으로 Pod IP를 영구 고정해야 한다

<details>
<summary>정답 보기</summary>

**정답: B) 별도 AWS Load Balancer Controller의 elbv2.k8s.aws/v1beta1이며 내장 Auto Mode TGB와 구분한다**

내장 Auto Mode TGB는 eks.amazonaws.com/v1이며 공식 안내에 TG 삭제 동작이 명시되어 있습니다. 여기서는 별도 컨트롤러로 동적 타겟 등록과 networking 규칙을 관리합니다.

</details>

### 6. 단일 PostgreSQL StatefulSet과 Retain PVC만 있으면 무엇이 보장되나요?

- A) 클러스터 간 데이터 복제
- B) AZ 장애 시 무중단 DB 전환
- C) 기존 연결의 무조건 유지
- D) 그것만으로 HA·백업·복구를 보장하지 않는다

<details>
<summary>정답 보기</summary>

**정답: D) 그것만으로 HA·백업·복구를 보장하지 않는다**

Retain은 볼륨 회수 정책입니다. 복제·백업·쓰기 소유권·복구 절차가 별도로 필요하며 NLB weight가 볼륨을 다른 AZ로 이동시키지 않습니다.

</details>

### 7. 알람 입력 SNS와 결과 알림 SNS를 분리하는 이유는?

- A) 입력으로 다시 전달되어 불필요한 실행·오류가 생기는 것을 막는다
- B) IAM 권한이 없어도 publish하기 위해
- C) Lambda를 무한히 재시도하기 위해
- D) DNS TTL을 없애기 위해

<details>
<summary>정답 보기</summary>

**정답: A) 입력으로 다시 전달되어 불필요한 실행·오류가 생기는 것을 막는다**

이 예제는 SNS envelope만 받습니다. CloudWatch 직접 Lambda 이벤트는 다른 형식이므로 두 경로를 중복 연결하지 않습니다. 결과 알림 실패가 이미 성공한 리스너 변경을 재실행하게 하지도 않습니다.

</details>

### 8. automatic_failover=false 기본값은 무엇을 하나요?

- A) 즉시 모든 트래픽을 Green으로 전환한다
- B) 변경안을 생성하며 ModifyListener 권한을 주지 않는다
- C) 헬스 체크를 생략한다
- D) 사용 가능한 모든 리스너를 수정한다

<details>
<summary>정답 보기</summary>

**정답: B) 변경안을 생성하며 ModifyListener 권한을 주지 않는다**

자동 모드는 목적지 용량·SLO·재연결·변경자 조정 절차를 검증한 후 켭니다. Reserved concurrency=1도 외부 Terraform/수동 변경자를 직렬화하지는 않습니다.

</details>

### 9. 수동 전환 스크립트의 적절한 동작은?

- A) 입력 문자열을 Bash 산술식으로 바로 실행한다
- B) 현재 상태와 관계없이 100/0에서 시작한다
- C) 가중치와 목적지 헬스를 확인하고 전체 plan을 검토·승인한다
- D) STEP=0도 타이머 루프로 반복한다

<details>
<summary>정답 보기</summary>

**정답: C) 가중치와 목적지 헬스를 확인하고 전체 plan을 검토·승인한다**

정수 범위를 먼저 확인하고, 필요한 변수 파일·backend를 사용합니다. 단계 사이에 실제 SLO와 데이터 호환성을 검증하며 API/apply 성공만으로 전환 완료라고 판단하지 않습니다.

</details>

### 10. Route 53 weight와 TTL에 대한 올바른 설명은?

- A) weight는 0–255 정수이며 TTL만으로 복구 시간을 보장할 수 없다
- B) weight는 항상 0–999다
- C) TTL 60초는 복구 SLA 60초다
- D) 모든 후보가 비정상이면 DNS가 반드시 아무 응답도 하지 않는다

<details>
<summary>정답 보기</summary>

**정답: A) weight는 0–255 정수이며 TTL만으로 복구 시간을 보장할 수 없다**

Alias는 타겟 TTL을 따릅니다. 건강 상태·resolver 캐시·연결 수명·폴백 동작을 고려하며 모든 가중치를 0으로 만드는 것을 트래픽 차단 수단으로 쓰지 않습니다.

</details>
