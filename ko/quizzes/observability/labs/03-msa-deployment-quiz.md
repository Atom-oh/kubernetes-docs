# Observability Lab 03 퀴즈

<span id="observability-실습-part-3-msa-배포-및-카나리-퀴즈"></span>

> **마지막 업데이트**: 2026년 9월 13일

1. 주문과 outbox의 transaction 경계는?
   - A) 주문commit후메시지실패는무시
   - B) 같은DBtransaction으로둘다commit또는rollback
   - C) SNS와DB가자동원자적
   - D) 매번DB를초기화

<details>
<summary>정답 보기</summary>

**정답: B) 같은DBtransaction으로둘다commit또는rollback**

실제DBrollback과미발행outbox보존을검증합니다.

</details>

---

2. payment workload 소유자는?
   - A) Deployment와Rollout동시
   - B) Rollout하나
   - C) KEDA와Rollout이서로replicas경쟁
   - D) Grafana

<details>
<summary>정답 보기</summary>

**정답: B) Rollout하나**

컨트롤러소유권과Gitdesiredstate를명확히합니다.

</details>

---

3. notification/analytics queue를 나누는 이유는?
   - A) 한큐경쟁소비가fanout이므로
   - B) 각소비자가같은이벤트를독립적으로받기위해
   - C) SQS는queue하나만지원
   - D) 중복이없어지므로

<details>
<summary>정답 보기</summary>

**정답: B) 각소비자가같은이벤트를독립적으로받기위해**

SNSfanout과각소비자event-IDdedup은별도책임입니다.

</details>

---

4. 반복된 동일 합성 결제 요청은?
   - A) 항상새결제
   - B) 저장결과재사용;다른금액등충돌은409
   - C) 실제카드청구
   - D) 주문이없어도항상성공

<details>
<summary>정답 보기</summary>

**정답: B) 저장결과재사용;다른금액등충돌은409**

이실습은실제결제gateway를구현하지않습니다.

</details>

---

5. SNS publish 후 DB mark 전 실패하면?
   - A) exactly-once가자동보장
   - B) 재발행가능하므로소비자dedup필요
   - C) outbox를전부삭제
   - D) 메시지를무조건ack

<details>
<summary>정답 보기</summary>

**정답: B) 재발행가능하므로소비자dedup필요**

외부sideeffect의idempotency는추가계약이필요합니다.

</details>

---

6. SQS backlog로 확장하는 workload는?
   - A) 항상APIproducer만
   - B) 해당queueconsumer
   - C) databaseadmin
   - D) NLB

<details>
<summary>정답 보기</summary>

**정답: B) 해당queueconsumer**

KEDA는메시지를소비하지않고queueattributes를조회합니다.

</details>

---

7. 카나리 성공률 query의 범위는?
   - A) stable과canary전체
   - B) 새pod-template revision만
   - C) 모든namespace
   - D) 배포이전평균만

<details>
<summary>정답 보기</summary>

**정답: B) 새pod-template revision만**

많은stable트래픽이실패한canary를숨기지않도록합니다.

</details>

---

8. 빈/NaN/Inf 결과의 처리 방식은?
   - A) 항상100%성공
   - B) 성공조건을통과시키지않는다
   - C) 모두0으로바꿔성공
   - D) metric이불필요

<details>
<summary>정답 보기</summary>

**정답: B) 성공조건을통과시키지않는다**

최소요청수와실제관측가능성을함께확인합니다.

</details>

---

9. metric label에 넣을 값은?
   - A) 모든orderID
   - B) service·고정route·status·revision
   - C) 고객이름/카드정보
   - D) 전체requestbody

<details>
<summary>정답 보기</summary>

**정답: B) service·고정route·status·revision**

고유ID는cardinality와민감정보문제를유발하므로trace/logcorrelation으로분리합니다.

</details>

---

10. Rollout abort의 의미는?
   - A) Git도자동revert
   - B) Gitrevert나desiredimage복구와별도이므로원본상태를명시적으로복구
   - C) 모든DBwrite도rollback
   - D) 새이미지가영구삭제

<details>
<summary>정답 보기</summary>

**정답: B) Gitrevert나desiredimage복구와별도이므로원본상태를명시적으로복구**

직접Helm과ArgoCD를동시에소유자로두지않습니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/03-msa-deployment-lab.md)
