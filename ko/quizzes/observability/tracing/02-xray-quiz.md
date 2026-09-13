# AWS X-Ray 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

[AWS X-Ray](../../../observability/tracing/02-xray.md)

---

1. X-Ray trace pipeline만으로 자동 제공되지 않는 동작은?
   - A) 수집한 trace의 서비스 의존성 시각화
   - B) 분산 요청 추적
   - C) 모든 앱의 일반 로그 파일 수집
   - D) 수집한 span 시간 분석

<details>
<summary>정답 보기</summary>

**정답: C) 모든 앱의 일반 로그 파일 수집**

**설명:**

Tracing이 일반 application-log collector를 구성하지는 않습니다. CloudWatch Transaction Search는 구조화된 span을 aws/spans에 저장할 수 있지만 모든 앱 로그 수집과는 별개입니다. Metric·log에는 각각 구성한 pipeline과 접근 통제가 필요합니다.

</details>

---

2. Legacy daemon 경로에서 적격 EC2 worker마다 daemon을 배치할 수 있는 Kubernetes workload는?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>정답 보기</summary>

**정답: C) DaemonSet**

**설명:**

DaemonSet은 적격 노드를 선택하며 EKS Fargate에서는 지원되지 않습니다. ClusterIP Service가 다른 노드의 daemon을 선택할 수 있으므로 DaemonSet만으로 node-local·무손실 UDP 전달이 보장되지 않습니다. X-Ray SDK/daemon은 maintenance mode이며 본문은 새 instrumentation에 별도의 OpenTelemetry collector Deployment를 사용합니다.

</details>

---

3. X-Ray 중앙 sampling rule의 필드가 아닌 것은?
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>정답 보기</summary>

**정답: D) RetentionDays**

**설명:**

FixedRate·ReservoirSize·Priority는 sampling 필드입니다. RetentionDays는 sampling rule parameter가 아닙니다. 트래픽이 없을 때도 reservoir가 최소 trace 수를 보장하지는 않습니다. 호환되는 remote sampler가 필요하며 head sampling은 아직 발생하지 않은 응답 오류를 선택할 수 없습니다.

</details>

---

4. X-Ray annotation과 metadata를 올바르게 구분한 것은?
   - A) Segment마다 독립적으로 annotation100개를 색인
   - B) Annotation은 X-Ray filter용으로 색인되며 unindexed metadata도 저장되고 접근 가능
   - C) Annotation은 문자열만 허용
   - D) Metadata는 자동 redaction됨

<details>
<summary>정답 보기</summary>

**정답: B) Annotation은 X-Ray filter용으로 색인되며 unindexed metadata도 저장되고 접근 가능**

**설명:**

X-Ray는 trace당 annotation 최대50개를 색인합니다. Metadata는 annotation으로 색인되지 않지만 비공개·접근 불가라는 뜻은 아닙니다. 의도한 제한된 필드를 사용하고 수집 전에 민감 payload·식별자·token·SQL parameter를 제거합니다. index_all_attributes=false는 redaction processor가 아닙니다.

</details>

---

5. ADOT Collector에 대한 잘못된 설명은?
   - A) 지원되는 OpenTelemetry protocol을 수신
   - B) 지원되는 여러 backend로 pipeline 연결 가능
   - C) 사용하지 않는 CloudWatch Logs exporter 선언만으로 trace가 log로 자동 변환
   - D) 선택한 릴리스의 component 목록 확인 필요

<details>
<summary>정답 보기</summary>

**정답: C) 사용하지 않는 CloudWatch Logs exporter 선언만으로 trace가 log로 자동 변환**

**설명:**

Receiver·processor·exporter를 적절한 log/metric/trace pipeline에 연결해야 합니다. ADOT에는 awsxray 같은 AWS 통합이 있으므로 AWS 전용 동작이 legacy daemon에만 있는 것은 아닙니다. 선택한 ADOT 릴리스에 upstream Contrib의 모든 exporter가 포함된다고 가정하지 않습니다.

</details>

---

6. X-Ray/CloudWatch trace map의 빨간 트래픽 범주가 뜻하는 것은?
   - A) 모든 느린 요청
   - B) 많은 트래픽
   - C) HTTP5xx 등의 server fault
   - D) 새로 발견한 서비스

<details>
<summary>정답 보기</summary>

**정답: C) HTTP5xx 등의 server fault**

**설명:**

Red는 server fault, yellow는 client error, purple은 HTTP429 같은 throttle, green은 성공을 나타냅니다. 임의 지연 임계값이나 모든 red service가 사용자 정의 오류율 알람 기준을 초과했다는 의미는 아닙니다.

</details>

---

7. 본문의 X-Ray 수집 경로로 OpenTelemetry span을 보내기 위해 필요한 것은?
   - A) 모든 producer의 legacy X-Ray SDK 사용
   - B) 호환되고 인증된 OTLP collector/export pipeline과 올바른 AWS identity
   - C) 모든 앱에 CloudWatch Agent 설치
   - D) 모든 EKS Pod에 Lambda Layer 설치

<details>
<summary>정답 보기</summary>

**정답: B) 호환되고 인증된 OTLP collector/export pipeline과 올바른 AWS identity**

**설명:**

본문은 mTLS OTLP를 ADOT로 보내고 awsxray exporter가 서명한 classic X-Ray API를 호출합니다. X-Ray는 W3C128-bit ID를 지원하므로 전용 ID generator/propagator가 언제나 필수는 아닙니다. 대안인 native OTLP HTTPS endpoint에는 SigV4와 Transaction Search가 필요합니다. 실제 통합에 맞는 propagation을 선택합니다.

</details>

---

8. X-Ray에서 응답 시간이 정확히2초인 요청을 제외하고2초 초과만 선택하는 filter는?
   - A) `responsetime > 2000`
   - B) `responsetime > 2`
   - C) `responsetime >= 2`
   - D) `time > 2s`

<details>
<summary>정답 보기</summary>

**정답: B) `responsetime > 2`**

**설명:**

응답 시간 단위는 초입니다. >2는 정확히2초를 제외하고 >=2는 포함합니다. 이는 X-Ray filter 문법이며 셸 명령이나 Logs Insights QL이 아닙니다. duration도 문서화된 X-Ray keyword이므로 존재하지 않는 잘못된 keyword로 취급하지 않습니다.

</details>

---

9. CloudWatch trace map을 열었다는 사실만으로 입증되지 않는 것은?
   - A) 이미 수집한 trace 의존성 보기
   - B) 구성한 metric/alarm과의 연계
   - C) 모든 앱의 자동 instrumentation과 수집 성공
   - D) 적절한 식별자로 연계한 log 링크

<details>
<summary>정답 보기</summary>

**정답: C) 모든 앱의 자동 instrumentation과 수집 성공**

**설명:**

Instrumentation·수집·identity·연계는 별도로 구성합니다. 기존 ServiceLens와 X-Ray map이 CloudWatch trace map으로 통합되어 수집한 telemetry를 연계할 수 있습니다. Mount하지 않은 ConfigMap이나 빈 화면은 agent·앱 설정 완료의 증거가 아닙니다.

</details>

---

10. X-Ray Group의 용도는?
   - A) IAM 인가 대체
   - B) 일치하는 trace를 분석·관련 metric/alarm용으로 그룹화
   - C) AWS 비용 소유권 자동 지정
   - D) Sampling rule로 retention 설정

<details>
<summary>정답 보기</summary>

**정답: B) 일치하는 trace를 분석·관련 metric/alarm용으로 그룹화**

**설명:**

Group은 filter 표현식으로 trace를 선택합니다. 해당 metric을 확인하고 CloudWatch alarm을 별도로 구성합니다. Group 생성이 producer instrumentation, sampling 재정의, IAM 격리나 실제 알림 전달 성공을 뜻하지는 않습니다.

</details>

---
