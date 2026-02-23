# Observability 실습 Part 5: 알림 및 AIOps 퀴즈

> **마지막 업데이트**: 2026년 2월 22일

이 퀴즈는 Observability 실습 Part 5의 알림 설정과 AIOps에 대한 이해도를 테스트합니다.

---

1. Alertmanager PrometheusRule에서 `for` 필드의 역할은?
   - A) 알림 메시지의 형식을 지정한다
   - B) 조건이 지정된 시간 동안 지속될 때만 알림을 firing 상태로 전환한다
   - C) 알림 수신자를 지정한다
   - D) 알림의 심각도를 설정한다
<details>
<summary>정답 보기</summary>

**정답: B) 조건이 지정된 시간 동안 지속될 때만 알림을 firing 상태로 전환한다**

**설명:**
`for` 필드는 알림 조건이 true가 된 후 firing 상태로 전환되기까지의 대기 시간입니다. 예를 들어 `for: 5m`은 조건이 5분 동안 연속으로 충족될 때만 알림이 발생합니다. 이를 통해 일시적인 스파이크로 인한 거짓 양성(false positive) 알림을 방지합니다. 대기 중인 알림은 pending 상태로 표시됩니다.

</details>

---

2. Alertmanager의 라우팅 트리와 수신기(receiver) 구성 방식으로 올바른 것은?
   - A) 모든 알림은 하나의 수신기로만 전송된다
   - B) 라우팅 트리는 알림 레이블을 기반으로 매칭하여 적절한 수신기로 알림을 라우팅하며, 계층적 구조를 가진다
   - C) 수신기는 알림을 생성하는 역할을 한다
   - D) 라우팅은 알림 내용을 수정한다
<details>
<summary>정답 보기</summary>

**정답: B) 라우팅 트리는 알림 레이블을 기반으로 매칭하여 적절한 수신기로 알림을 라우팅하며, 계층적 구조를 가진다**

**설명:**
Alertmanager 라우팅 트리는 알림의 레이블(severity, team, service 등)을 기반으로 매칭 규칙을 정의합니다. 루트 라우트에서 시작하여 하위 라우트로 내려가며 첫 번째 매칭되는 라우트의 수신기로 알림을 전송합니다. `continue: true`를 설정하면 여러 수신기로 전송할 수 있습니다. 각 수신기는 Slack, Email, PagerDuty, SNS 등 다양한 채널로 알림을 전달합니다.

</details>

---

3. Grafana OnCall의 Escalation Chain 동작 방식으로 올바른 것은?
   - A) 모든 담당자에게 동시에 알림을 보낸다
   - B) 첫 번째 담당자가 응답하지 않으면 지정된 시간 후 다음 담당자에게 에스컬레이션하는 단계별 알림 체계이다
   - C) 알림을 자동으로 해결한다
   - D) 알림 빈도를 줄인다
<details>
<summary>정답 보기</summary>

**정답: B) 첫 번째 담당자가 응답하지 않으면 지정된 시간 후 다음 담당자에게 에스컬레이션하는 단계별 알림 체계이다**

**설명:**
Escalation Chain은 온콜 담당자가 알림에 응답하지 않을 때의 에스컬레이션 경로를 정의합니다. 예를 들어 "1차 온콜 담당자에게 알림 → 10분 후 응답 없으면 2차 담당자에게 에스컬레이션 → 추가 15분 후 팀 전체에게 알림"과 같이 구성합니다. acknowledge, resolve 액션을 통해 알림 수명주기를 관리합니다.

</details>

---

4. CloudWatch Alarms에서 평가 기간(Period)과 데이터포인트(Datapoints to Alarm) 설정의 의미는?
   - A) 두 설정은 동일한 기능을 수행한다
   - B) Period는 메트릭 집계 간격이고, Datapoints to Alarm은 알람 상태 전환에 필요한 연속 위반 횟수이다
   - C) Period는 알람 이름을 설정하고, Datapoints는 알람 설명을 설정한다
   - D) 이 설정들은 CloudWatch Logs에만 적용된다
<details>
<summary>정답 보기</summary>

**정답: B) Period는 메트릭 집계 간격이고, Datapoints to Alarm은 알람 상태 전환에 필요한 연속 위반 횟수이다**

**설명:**
Period는 메트릭을 집계하는 시간 간격(예: 60초, 300초)입니다. Datapoints to Alarm은 "M out of N" 형식으로, N개의 연속 평가 기간 중 M개에서 임계값을 위반해야 알람이 발생합니다. 예를 들어 Period=60초, Datapoints=3/5는 5분 동안 3번 이상 위반 시 알람이 발생합니다. 이를 통해 일시적 스파이크에 대한 과민 반응을 방지합니다.

</details>

---

5. CloudWatch Investigations가 AI 기반 근본 원인 분석을 수행하는 방식으로 올바른 것은?
   - A) 사용자가 수동으로 모든 로그를 분석해야 한다
   - B) 알람이나 이상 징후 발생 시 관련 메트릭, 로그, 트레이스를 자동으로 수집하고 AI가 패턴을 분석하여 근본 원인을 제안한다
   - C) 외부 도구와 연동이 불가능하다
   - D) 메트릭만 분석할 수 있다
<details>
<summary>정답 보기</summary>

**정답: B) 알람이나 이상 징후 발생 시 관련 메트릭, 로그, 트레이스를 자동으로 수집하고 AI가 패턴을 분석하여 근본 원인을 제안한다**

**설명:**
CloudWatch Investigations는 AWS의 AI 기반 문제 분석 기능입니다. 알람 발생 시 관련 리소스의 메트릭, 로그, X-Ray 트레이스를 자동으로 수집하고 시간순으로 상관관계를 분석합니다. 생성형 AI가 수집된 데이터를 분석하여 가능한 근본 원인과 해결 방안을 자연어로 제안합니다. 이를 통해 MTTR(평균 복구 시간)을 단축할 수 있습니다.

</details>

---

6. Lambda 기반 AIOps Agent에서 텔레메트리 수집 순서로 올바른 것은?
   - A) 메트릭 → 로그 → 트레이스 순서로만 수집해야 한다
   - B) 메트릭, 로그, 트레이스를 병렬로 수집하여 응답 시간을 최소화한다
   - C) 트레이스만 수집한다
   - D) 수집 순서는 중요하지 않으며 항상 순차적으로 수집한다
<details>
<summary>정답 보기</summary>

**정답: B) 메트릭, 로그, 트레이스를 병렬로 수집하여 응답 시간을 최소화한다**

**설명:**
AIOps Agent가 알림을 처리할 때 다양한 텔레메트리 소스(CloudWatch Metrics, CloudWatch Logs, X-Ray, Prometheus/AMP, Loki, Tempo 등)에서 데이터를 수집해야 합니다. 이 수집 작업들은 서로 독립적이므로 병렬로 실행하여 전체 응답 시간을 최소화합니다. Python의 asyncio나 concurrent.futures를 사용하여 동시에 여러 API를 호출합니다.

</details>

---

7. Amazon Bedrock Claude를 SRE 전문가로 활용할 때 시스템 프롬프트 설계 원칙으로 올바른 것은?
   - A) 가능한 한 짧고 일반적인 프롬프트를 사용한다
   - B) SRE 도메인 지식, 분석 프레임워크, 출력 형식을 명확히 정의하고 구조화된 컨텍스트를 제공한다
   - C) 프롬프트에 비밀 정보를 포함한다
   - D) 매 요청마다 다른 프롬프트를 사용한다
<details>
<summary>정답 보기</summary>

**정답: B) SRE 도메인 지식, 분석 프레임워크, 출력 형식을 명확히 정의하고 구조화된 컨텍스트를 제공한다**

**설명:**
효과적인 SRE AI 에이전트를 위해 시스템 프롬프트에는 다음을 포함해야 합니다: (1) 역할 정의 - "당신은 숙련된 SRE 엔지니어입니다", (2) 분석 프레임워크 - "RED 메트릭을 확인하고, 변경 사항을 파악하고, 의존성을 추적합니다", (3) 출력 형식 - "근본 원인, 영향 범위, 권장 조치를 구조화된 형식으로 제공합니다". 일관된 고품질 분석을 위해 프롬프트 템플릿을 재사용합니다.

</details>

---

8. AlertManager webhook과 API Gateway → Lambda 트리거 연결 방식으로 올바른 것은?
   - A) Alertmanager가 직접 Lambda를 호출한다
   - B) Alertmanager webhook_configs에 API Gateway 엔드포인트를 설정하고, API Gateway가 Lambda 함수를 트리거한다
   - C) Lambda가 Alertmanager를 폴링한다
   - D) SNS를 반드시 중간에 사용해야 한다
<details>
<summary>정답 보기</summary>

**정답: B) Alertmanager webhook_configs에 API Gateway 엔드포인트를 설정하고, API Gateway가 Lambda 함수를 트리거한다**

**설명:**
Alertmanager의 webhook_configs receiver에 API Gateway의 HTTP 엔드포인트 URL을 설정합니다. 알림 발생 시 Alertmanager가 POST 요청으로 알림 데이터를 API Gateway로 전송하고, API Gateway가 Lambda 함수를 동기 또는 비동기로 호출합니다. Lambda 함수는 알림 페이로드를 파싱하여 AIOps 분석, 자동 복구 등의 작업을 수행합니다.

</details>

---

9. Fault Injection으로 HighLatency 알림을 트리거하는 방법은?
   - A) 서버를 물리적으로 차단한다
   - B) 애플리케이션에 인위적인 지연을 주입하거나, 리소스 제한을 통해 처리 속도를 저하시켜 지연 시간 임계값을 초과하게 한다
   - C) Alertmanager 설정을 수정한다
   - D) 네트워크 케이블을 분리한다
<details>
<summary>정답 보기</summary>

**정답: B) 애플리케이션에 인위적인 지연을 주입하거나, 리소스 제한을 통해 처리 속도를 저하시켜 지연 시간 임계값을 초과하게 한다**

**설명:**
Fault Injection은 시스템의 복원력을 테스트하는 카오스 엔지니어링 기법입니다. HighLatency 알림을 트리거하려면 (1) 코드에 sleep() 추가, (2) Istio/Envoy의 fault injection 기능으로 지연 주입, (3) CPU/메모리 제한으로 처리 속도 저하, (4) 네트워크 지연 시뮬레이션 등의 방법을 사용합니다. 이를 통해 알림 파이프라인과 대응 절차를 검증합니다.

</details>

---

10. A2A (Agent-to-Agent) 패턴에서 Collaborator Agent의 역할은?
    - A) 최종 사용자와 직접 상호작용한다
    - B) 특정 도메인(로그 분석, 메트릭 분석, 네트워크 진단 등)에 특화된 작업을 수행하고 결과를 오케스트레이터 에이전트에 반환한다
    - C) 데이터베이스를 관리한다
    - D) 알림을 생성한다
<details>
<summary>정답 보기</summary>

**정답: B) 특정 도메인(로그 분석, 메트릭 분석, 네트워크 진단 등)에 특화된 작업을 수행하고 결과를 오케스트레이터 에이전트에 반환한다**

**설명:**
A2A(Agent-to-Agent) 패턴에서 Collaborator Agent는 특정 전문 영역을 담당합니다. 예를 들어 로그 분석 에이전트는 Loki/CloudWatch Logs를 쿼리하고, 메트릭 분석 에이전트는 Prometheus/CloudWatch Metrics를 분석합니다. 오케스트레이터 에이전트가 작업을 분배하고 각 Collaborator의 결과를 통합하여 종합적인 분석을 제공합니다. 이 패턴은 복잡한 문제를 전문화된 에이전트들의 협업으로 해결합니다.

</details>
