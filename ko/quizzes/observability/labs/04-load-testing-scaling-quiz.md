# Observability Lab Part 4 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

1. k6 VU와 RPS의 관계는?
   - A) VU 1개는 항상 1 RPS
   - B) VU는 동시 실행 context이며 RPS는 요청 수·응답 시간·sleep에도 영향을 받는다
   - C) VU는 노드 수와 같다
   - D) RPS는 응답 시간과 무관하다

<details>
<summary>정답 보기</summary>

**정답: B) VU는 동시 실행 context이며 RPS는 요청 수·응답 시간·sleep에도 영향을 받는다**

같은 VU 수라도 workload와 대기 시간이 다르면 처리량이 다릅니다.

</details>

---

2. k6 check 실패를 CI 실패로 연결하려면?
   - A) check만 호출하면 항상 종료 코드가 1이다
   - B) checks 또는 실패율에 threshold를 설정하고 종료 코드를 확인한다
   - C) summary JSON이 있으면 성공이다
   - D) HTTP 200만 세면 된다

<details>
<summary>정답 보기</summary>

**정답: B) checks 또는 실패율에 threshold를 설정하고 종료 코드를 확인한다**

HTTP 성공 코드와 비즈니스 성공은 다릅니다. JSON·ID·결제 상태도 assertion으로 검사합니다.

</details>

---

3. GET 부하에서 조회할 주문 ID는?
   - A) 임의 1~1000
   - B) 테스트가 실제 생성한 ID
   - C) 고객 ID
   - D) HTTP 상태 코드

<details>
<summary>정답 보기</summary>

**정답: B) 테스트가 실제 생성한 ID**

임의 ID의 404가 부하 결과를 오염시키지 않도록 생성 응답의 ID를 사용합니다.

</details>

---

4. SQS backlog 기반으로 직접 늘려야 하는 대상은?
   - A) 항상 API producer만
   - B) 그 큐를 처리하는 consumer
   - C) Alertmanager replica
   - D) 큐 이름

<details>
<summary>정답 보기</summary>

**정답: B) 그 큐를 처리하는 consumer**

KEDA는 큐 속성을 읽고 HPA와 scale target을 조정합니다. 자체적으로 메시지를 소비하지 않습니다.

</details>

---

5. KEDA cooldownPeriod가 적용되는 경우는?
   - A) 모든 10→9 replica 변경
   - B) 마지막 active trigger 이후 0으로 줄일 때
   - C) EC2 부팅 지연
   - D) 로그 보존 기간

<details>
<summary>정답 보기</summary>

**정답: B) 마지막 active trigger 이후 0으로 줄일 때**

1→N 범위는 HPA behavior와 stabilization window를 함께 확인합니다.

</details>

---

6. HPA scale-down stabilization window는?
   - A) 모든 노드를 고정한다
   - B) window 안에서 가장 높은 replica 권고를 고려한다
   - C) 현재 CPU만 본다
   - D) 지정 시간마다 Pod를 삭제한다

<details>
<summary>정답 보기</summary>

**정답: B) window 안에서 가장 높은 replica 권고를 고려한다**

window가 무조건 고정 대기 timer라는 설명은 부정확합니다. 정책·권고 이력이 결과를 결정합니다.

</details>

---

7. Karpenter가 해결할 수 있는 대표 문제는?
   - A) 잘못된 이미지 이름
   - B) NodePool 조건에 맞는 capacity가 없어 unschedulable인 Pod
   - C) 앱 문법 오류
   - D) 잘못된 DB 비밀번호

<details>
<summary>정답 보기</summary>

**정답: B) NodePool 조건에 맞는 capacity가 없어 unschedulable인 Pod**

노드가 늘어도 image pull·앱 오류는 해결되지 않습니다. Pending 이유를 먼저 확인합니다.

</details>

---

8. kube_deployment_status_replicas는 무엇인가?
   - A) 항상 ready 수
   - B) Deployment의 전체 replica 수이며 ready 수와 다르다
   - C) Rollout을 포함한 모든 controller 수
   - D) 노드 수

<details>
<summary>정답 보기</summary>

**정답: B) Deployment의 전체 replica 수이며 ready 수와 다르다**

ready는 kube_deployment_status_replicas_ready로 확인합니다. Rollout은 별도 상태/exporter가 필요합니다.

</details>

---

9. Running Pod 수를 phase metric으로 세는 방법은?
   - A) Running series를 조건 없이 count한다
   - B) 값이 1인 Running series를 합한다
   - C) Pod 이름 길이를 합한다
   - D) 항상 3을 반환한다

<details>
<summary>정답 보기</summary>

**정답: B) 값이 1인 Running series를 합한다**

phase=Running series도 값 0으로 존재할 수 있어 count만 하면 과대 계산합니다.

</details>

---

10. 부하 실험 성공의 근거는?
   - A) 문서 예상 숫자와 같은 표
   - B) 실제 요청·오류·지연·큐·replica·노드 기록과 종료 상태
   - C) Job 생성 성공
   - D) 노드 수 감소만

<details>
<summary>정답 보기</summary>

**정답: B) 실제 요청·오류·지연·큐·replica·노드 기록과 종료 상태**

미측정 throughput·가용성·비용을 성공 결과로 쓰지 않습니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/04-load-testing-scaling-lab.md)
