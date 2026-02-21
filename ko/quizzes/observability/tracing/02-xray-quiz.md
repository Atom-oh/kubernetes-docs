# AWS X-Ray 퀴즈

AWS X-Ray에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. AWS X-Ray의 주요 기능이 아닌 것은?
   - A) 서비스 맵 시각화
   - B) 분산 추적
   - C) 로그 집계
   - D) 성능 분석

<details>
<summary>정답 보기</summary>

**정답: C) 로그 집계**

**설명:**
AWS X-Ray는 분산 추적, 서비스 맵 시각화, 성능 분석을 제공하는 서비스입니다. 로그 집계는 CloudWatch Logs의 기능입니다. X-Ray는 CloudWatch Logs와 통합하여 추적과 로그를 연결할 수 있지만, 로그 자체를 수집하거나 저장하지는 않습니다.

</details>

---

2. EKS에서 X-Ray 데몬을 배포하는 권장 방식은?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>정답 보기</summary>

**정답: C) DaemonSet**

**설명:**
X-Ray Daemon은 DaemonSet으로 배포하는 것이 권장됩니다. DaemonSet은 각 노드에 하나의 Pod를 실행하므로, 해당 노드의 모든 애플리케이션 Pod가 로컬 X-Ray Daemon에 추적 데이터를 전송할 수 있습니다. 이는 네트워크 지연을 최소화하고 안정적인 데이터 전송을 보장합니다.

</details>

---

3. X-Ray에서 중앙 집중식 샘플링 규칙을 설정할 때 사용하는 파라미터가 아닌 것은?
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>정답 보기</summary>

**정답: D) RetentionDays**

**설명:**
X-Ray 샘플링 규칙에는 FixedRate(고정 샘플링 비율), ReservoirSize(초당 최소 샘플링 수), Priority(규칙 우선순위)가 포함됩니다. RetentionDays는 샘플링 규칙이 아니라 X-Ray 데이터 보존 설정에 관련된 파라미터입니다. 기본 데이터 보존 기간은 30일입니다.

</details>

---

4. X-Ray에서 Annotation과 Metadata의 차이점은?
   - A) Annotation은 최대 100개, Metadata는 제한 없음
   - B) Annotation은 인덱싱되어 필터링 가능, Metadata는 인덱싱 안됨
   - C) Annotation은 문자열만, Metadata는 모든 타입 지원
   - D) Annotation은 자동 생성, Metadata는 수동 추가

<details>
<summary>정답 보기</summary>

**정답: B) Annotation은 인덱싱되어 필터링 가능, Metadata는 인덱싱 안됨**

**설명:**
Annotation은 인덱싱되어 X-Ray 콘솔에서 필터 표현식으로 검색할 수 있습니다 (최대 50개). Metadata는 인덱싱되지 않아 검색할 수 없지만, 상세 정보를 저장하는 데 사용됩니다. Annotation은 중요한 식별자(user_id, order_id 등)에, Metadata는 요청/응답 본문 같은 상세 정보에 사용합니다.

</details>

---

5. ADOT (AWS Distro for OpenTelemetry) Collector를 사용할 때의 장점이 아닌 것은?
   - A) 벤더 중립적 표준 사용
   - B) 다중 백엔드 지원
   - C) X-Ray 전용 최적화
   - D) OpenTelemetry 프로토콜 지원

<details>
<summary>정답 보기</summary>

**정답: C) X-Ray 전용 최적화**

**설명:**
ADOT Collector는 벤더 중립적인 OpenTelemetry 기반으로, X-Ray뿐만 아니라 다양한 백엔드(Prometheus, Jaeger, Datadog 등)로 데이터를 전송할 수 있습니다. X-Ray 전용 최적화는 X-Ray Daemon의 특징입니다. ADOT의 장점은 표준화된 계측과 다중 백엔드 지원입니다.

</details>

---

6. X-Ray 서비스 맵에서 노드 색상이 빨간색으로 표시되는 경우는?
   - A) 응답 시간이 느린 경우
   - B) 트래픽이 높은 경우
   - C) 오류율이 높은 경우
   - D) 새로 추가된 서비스인 경우

<details>
<summary>정답 보기</summary>

**정답: C) 오류율이 높은 경우**

**설명:**
X-Ray 서비스 맵에서 노드 색상은 서비스의 상태를 나타냅니다. 빨간색은 오류율이 높은 서비스를 나타내고, 노란색은 경고 수준의 문제가 있는 서비스, 초록색은 정상적인 서비스를 나타냅니다. 이를 통해 문제가 있는 서비스를 빠르게 식별할 수 있습니다.

</details>

---

7. X-Ray에서 OpenTelemetry 추적 데이터를 수신하려면 어떤 설정이 필요한가요?
   - A) X-Ray SDK 설치
   - B) AWS X-Ray Propagator와 ID Generator 설정
   - C) CloudWatch Agent 설치
   - D) Lambda Layer 추가

<details>
<summary>정답 보기</summary>

**정답: B) AWS X-Ray Propagator와 ID Generator 설정**

**설명:**
OpenTelemetry에서 X-Ray로 추적 데이터를 전송하려면 AWS X-Ray Propagator(컨텍스트 전파)와 AWS X-Ray ID Generator(X-Ray 형식의 TraceID 생성)를 설정해야 합니다. 이를 통해 OpenTelemetry 표준을 사용하면서도 X-Ray와 호환되는 추적 데이터를 생성할 수 있습니다.

</details>

---

8. X-Ray 필터 표현식에서 응답 시간이 2초 이상인 요청을 찾는 올바른 쿼리는?
   - A) `duration > 2`
   - B) `responsetime > 2`
   - C) `latency >= 2000`
   - D) `time > 2s`

<details>
<summary>정답 보기</summary>

**정답: B) responsetime > 2**

**설명:**
X-Ray 필터 표현식에서 응답 시간은 `responsetime` 키워드를 사용하며, 단위는 초입니다. `responsetime > 2`는 2초 이상 걸린 요청을 필터링합니다. 다른 유용한 필터로는 `fault = true`(서버 오류), `error = true`(클라이언트 오류), `service("name")`(특정 서비스) 등이 있습니다.

</details>

---

9. CloudWatch ServiceLens에서 X-Ray와 연동할 때 제공되는 기능이 아닌 것은?
   - A) 추적과 메트릭 통합 뷰
   - B) 서비스 맵에서 CloudWatch 알람 표시
   - C) 자동 코드 계측
   - D) 로그와 추적 연결

<details>
<summary>정답 보기</summary>

**정답: C) 자동 코드 계측**

**설명:**
CloudWatch ServiceLens는 X-Ray 추적, CloudWatch 메트릭, 로그를 통합된 뷰로 제공합니다. 서비스 맵에 CloudWatch 알람을 표시하고, 로그와 추적을 연결하는 기능을 제공합니다. 하지만 자동 코드 계측은 X-Ray SDK나 OpenTelemetry auto-instrumentation을 통해 수행해야 합니다.

</details>

---

10. X-Ray 그룹(Group)의 주요 용도는?
    - A) 사용자 권한 관리
    - B) 필터 기반 추적 그룹화 및 알림
    - C) 리소스 비용 할당
    - D) 데이터 보존 정책 설정

<details>
<summary>정답 보기</summary>

**정답: B) 필터 기반 추적 그룹화 및 알림**

**설명:**
X-Ray 그룹은 필터 표현식을 사용하여 추적을 그룹화합니다. 예를 들어 프로덕션 환경, 특정 서비스, 오류 요청 등으로 그룹을 만들 수 있습니다. 각 그룹에 대해 CloudWatch 알람을 설정하여 특정 조건(오류율 증가 등)에 대한 알림을 받을 수 있습니다.

</details>

---
