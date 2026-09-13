# Observability Lab Part5 알림 및 AIOps 퀴즈

<span id="observability-실습-part-5-알림-및-aiops-퀴즈"></span>

> **마지막 업데이트**: 2026년 9월 13일

1. PrometheusRule을 평가하는 컴포넌트는?
   - A) Alertmanager
   - B) Prometheus
   - C) SNS
   - D) Lambda DLQ

<details>
<summary>정답 보기</summary>

**정답: B) Prometheus**

Prometheus가 평가하고 Alertmanager는 grouping·routing·notification을 처리합니다.

</details>

---

2. CloudWatch DatapointsToAlarm=2, EvaluationPeriods=3의 뜻은?
   - A) 반드시 2개 연속 위반
   - B) 평가 범위 3개 중 2개 위반이며 반드시 연속일 필요는 없다
   - C) 3초마다 2개 알림
   - D) 2개 리전 사용

<details>
<summary>정답 보기</summary>

**정답: B) 평가 범위 3개 중 2개 위반이며 반드시 연속일 필요는 없다**

Period는 metric 집계 간격이며 평가 수행 빈도와 동의어가 아닙니다.

</details>

---

3. 현재 Grafana OnCall OSS 신규 설치 안내에서 고려할 점은?
   - A) 영구 지원된다
   - B) 2026-03-24 보관 처리와 Cloud Connection 종료를 반영한다
   - C) SMS 지원은 계속 무조건 무료다
   - D) 임의 YAML만 적용하면 운영된다

<details>
<summary>정답 보기</summary>

**정답: B) 2026-03-24 보관 처리와 Cloud Connection 종료를 반영한다**

조직이 사용하는 지원 가능한 incident/notification 경로와 실제 수신을 검증합니다.

</details>

---

4. SNS input/output topic을 분리하는 이유는?
   - A) 메트릭 단위를 바꾸기 위해
   - B) reporter가 자신의 결과를 다시 처리하는 순환을 막기 위해
   - C) SNS는 한 topic만 지원하므로
   - D) 로그를 공개하기 위해

<details>
<summary>정답 보기</summary>

**정답: B) reporter가 자신의 결과를 다시 처리하는 순환을 막기 위해**

구독과 IAM publish 권한도 입력/결과 경계에 맞춰 제한합니다.

</details>

---

5. Alertmanager의 `{{ . | toJson }}` 출력에서 파서가 고려할 점은?
   - A) 항상 plain text다
   - B) JSON tag의 소문자/camelCase key와 Go template 대문자 필드 접근의 차이
   - C) JSON은 parse할 필요가 없다
   - D) 모든 SNS message는 같은 필드다

<details>
<summary>정답 보기</summary>

**정답: B) JSON tag의 소문자/camelCase key와 Go template 대문자 필드 접근의 차이**

실제0.34.0 template 직렬화와 정상/오류 payload를 검증했습니다.

</details>

---

6. 지표가 없거나 query가 실패한 경우의 올바른 보고는?
   - A) 오류 0으로 바꾼다
   - B) missing/no_data/error로 표시하고 측정값을 만들지 않는다
   - C) 쿼리 문자열을 실제 값처럼 보여준다
   - D) 항상 정상이라고 답한다

<details>
<summary>정답 보기</summary>

**정답: B) missing/no_data/error로 표시하고 측정값을 만들지 않는다**

근거가 충분하지 않으면 model 호출도 생략할 수 있습니다.

</details>

---

7. Powertools idempotency를 사용하면 보장되는 것은?
   - A) SNS end-to-end exactly-once
   - B) 설정한 24시간 동안 성공한 같은 message ID의 중복 작업을 억제한다
   - C) 새 message ID도 모두 같은 작업
   - D) publish와DBcommit을 원자적으로 합친다

<details>
<summary>정답 보기</summary>

**정답: B) 설정한 24시간 동안 성공한 같은 message ID의 중복 작업을 억제한다**

publish 후 commit 전 장애의 중복 통지 가능성과 SNS/Lambda 재시도를 구분합니다.

</details>

---

8. Converse 결과의 성공 판정은?
   - A) 응답이 오면 항상 성공
   - B) maxTokens를 명시하고 end_turn과 비어 있지 않은 text를 확인한다
   - C) max_tokens 중단도 완성된 원인 분석
   - D) 모델의 command를 즉시 실행

<details>
<summary>정답 보기</summary>

**정답: B) maxTokens를 명시하고 end_turn과 비어 있지 않은 text를 확인한다**

이 reporter는 사람 검토용 가설만 만들며 자동 복구 도구가 없습니다.

</details>

---

9. CloudWatch Investigations를 alarm으로 시작하는 설정은?
   - A) list-dashboards 호출
   - B) 준비한 investigation group ARN을 alarm action에 추가한다
   - C) put-insight-rule만 호출
   - D) Application Signals discovery만 켠다

<details>
<summary>정답 보기</summary>

**정답: B) 준비한 investigation group ARN을 alarm action에 추가한다**

group·권한·보존·암호화와 실제 alarm action 연결을 별도로 준비합니다.

</details>

---

10. 여러 분석 모듈을 호출하면 바로 A2A 프로토콜 구현인가?
   - A) 함수2개면 자동으로A2A다
   - B) 아니며 discovery·인증·task/message 계약 등을 별도로 구현해야 한다
   - C) SNS가 있으면 항상A2A다
   - D) DynamoDB만 있으면 된다

<details>
<summary>정답 보기</summary>

**정답: B) 아니며 discovery·인증·task/message 계약 등을 별도로 구현해야 한다**

전문 분석 모듈 분할은 설계 패턴이며 특정 agent protocol 준수와는 다릅니다.

</details>

---

[본문으로 돌아가기](../../../labs/observability/05-alerting-aiops-lab.md)
