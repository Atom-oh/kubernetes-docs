# Observability Lab 03 퀴즈

<span id="observability-실습-part-3-msa-배포-및-카나리-퀴즈"></span>

> **마지막 업데이트**: 2026년 9월 13일

1. 주문과 outbox의 transaction 경계는?
   - A) 주문 commit 후 메시지 실패는 무시
   - B) 같은 DB transaction으로 둘 다 commit 또는 rollback
   - C) SNS와 DB가 자동으로 원자적
   - D) 매번 DB를 초기화

<details>
<summary>정답 보기</summary>

**정답: B) 같은 DB transaction으로 둘 다 commit 또는 rollback**

실제 DB rollback과 미발행 outbox 보존을 검증합니다.

</details>

---

2. payment workload 소유자는?
   - A) Deployment와 Rollout 동시
   - B) Rollout 하나
   - C) KEDA와 Rollout이 서로 replicas 경쟁
   - D) Grafana

<details>
<summary>정답 보기</summary>

**정답: B) Rollout 하나**

컨트롤러 소유권과 Git desired state를 명확히 합니다.

</details>

---

3. notification/analytics queue를 나누는 이유는?
   - A) 한 큐 경쟁 소비가 fanout이므로
   - B) 각 소비자가 같은 이벤트를 독립적으로 받기 위해
   - C) SQS는 queue 하나만 지원
   - D) 중복이 없어지므로

<details>
<summary>정답 보기</summary>

**정답: B) 각 소비자가 같은 이벤트를 독립적으로 받기 위해**

SNS fanout과 각 소비자 event-ID dedup은 별도 책임입니다.

</details>

---

4. 반복된 동일 합성 결제 요청은?
   - A) 항상 새 결제
   - B) 저장 결과 재사용; 다른 금액 등 충돌은 409
   - C) 실제 카드 청구
   - D) 주문이 없어도 항상 성공

<details>
<summary>정답 보기</summary>

**정답: B) 저장 결과 재사용; 다른 금액 등 충돌은 409**

이 실습은 실제 결제 gateway를 구현하지 않습니다.

</details>

---

5. SNS publish 후 DB mark 전 실패하면?
   - A) exactly-once가 자동 보장
   - B) 재발행 가능하므로 소비자 dedup 필요
   - C) outbox를 전부 삭제
   - D) 메시지를 무조건 ack

<details>
<summary>정답 보기</summary>

**정답: B) 재발행 가능하므로 소비자 dedup 필요**

외부 side effect의 idempotency는 추가 계약이 필요합니다.

</details>

---

6. SQS backlog로 확장하는 workload는?
   - A) 항상 API producer만
   - B) 해당 queue consumer
   - C) database admin
   - D) NLB

<details>
<summary>정답 보기</summary>

**정답: B) 해당 queue consumer**

KEDA는 메시지를 소비하지 않고 queue attributes를 조회합니다.

</details>

---

7. 카나리 성공률 query의 범위는?
   - A) stable과 canary 전체
   - B) 새 pod-template revision만
   - C) 모든 namespace
   - D) 배포 이전 평균만

<details>
<summary>정답 보기</summary>

**정답: B) 새 pod-template revision만**

많은 stable 트래픽이 실패한 canary를 숨기지 않도록 합니다.

</details>

---

8. 빈/NaN/Inf 결과의 처리 방식은?
   - A) 항상 100% 성공
   - B) 성공 조건을 통과시키지 않는다
   - C) 모두 0으로 바꿔 성공
   - D) metric이 불필요

<details>
<summary>정답 보기</summary>

**정답: B) 성공 조건을 통과시키지 않는다**

최소 요청 수와 실제 관측 가능성을 함께 확인합니다.

</details>

---

9. metric label에 넣을 값은?
   - A) 모든 orderID
   - B) service·고정 route·status·revision
   - C) 고객 이름/카드 정보
   - D) 전체 request body

<details>
<summary>정답 보기</summary>

**정답: B) service·고정 route·status·revision**

고유 ID는 cardinality와 민감 정보 문제를 유발하므로 trace/log correlation으로 분리합니다.

</details>

---

10. Rollout abort의 의미는?
   - A) Git도 자동 revert
   - B) Git revert나 desired image 복구와 별도이므로 원본 상태를 명시적으로 복구
   - C) 모든 DB write도 rollback
   - D) 새 이미지가 영구 삭제

<details>
<summary>정답 보기</summary>

**정답: B) Git revert나 desired image 복구와 별도이므로 원본 상태를 명시적으로 복구**

직접 Helm과 ArgoCD를 동시에 소유자로 두지 않습니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/03-msa-deployment-lab.md)
