# Grafana 대시보드 퀴즈

Grafana에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Grafana에서 데이터 소스 프로비저닝에 사용되는 방법이 아닌 것은?
   - A) ConfigMap with sidecar
   - B) Grafana API
   - C) 환경 변수
   - D) provisioning 디렉토리

<details>
<summary>정답 보기</summary>

**정답: C) 환경 변수**

**설명:**
Grafana 데이터 소스는 provisioning 디렉토리의 YAML 파일, ConfigMap을 사용한 sidecar 방식, 또는 Grafana API를 통해 프로비저닝할 수 있습니다. 환경 변수는 Grafana 설정(grafana.ini)에 사용되지만, 데이터 소스를 직접 정의하는 데는 사용되지 않습니다.

</details>

---

2. RED Method에서 'R', 'E', 'D'가 의미하는 것은?
   - A) Resource, Error, Duration
   - B) Rate, Error, Duration
   - C) Request, Exception, Delay
   - D) Response, Event, Data

<details>
<summary>정답 보기</summary>

**정답: B) Rate, Error, Duration**

**설명:**
RED Method는 서비스 수준 메트릭을 분석하기 위한 방법론입니다. Rate(요청 처리율), Error(오류율), Duration(응답 시간)의 세 가지 핵심 메트릭을 모니터링합니다. 이는 마이크로서비스의 상태를 파악하는 데 효과적인 프레임워크입니다.

</details>

---

3. Grafana에서 Tempo와 Loki를 연결하여 trace-to-log 상관분석을 구현할 때 필요한 설정은?
   - A) 동일한 데이터베이스 사용
   - B) Tempo 데이터 소스의 tracesToLogs 설정
   - C) 별도의 플러그인 설치
   - D) Grafana Enterprise 라이선스

<details>
<summary>정답 보기</summary>

**정답: B) Tempo 데이터 소스의 tracesToLogs 설정**

**설명:**
Tempo 데이터 소스 설정에서 tracesToLogs 섹션을 구성하면 추적에서 관련 로그로 바로 이동할 수 있습니다. datasourceUid로 Loki를 지정하고, tags로 연결에 사용할 레이블을 설정합니다. 이는 Grafana의 기본 기능으로 추가 플러그인이 필요하지 않습니다.

</details>

---

4. USE Method에서 'U', 'S', 'E'가 의미하는 것은?
   - A) User, Service, Event
   - B) Utilization, Saturation, Errors
   - C) Uptime, Status, Exceptions
   - D) Usage, Speed, Efficiency

<details>
<summary>정답 보기</summary>

**정답: B) Utilization, Saturation, Errors**

**설명:**
USE Method는 시스템 리소스 분석을 위한 방법론입니다. Utilization(사용률), Saturation(포화도), Errors(오류)를 모니터링합니다. CPU, 메모리, 디스크, 네트워크 등 각 리소스에 대해 이 세 가지 메트릭을 분석하여 병목을 식별합니다.

</details>

---

5. Grafana Alerting에서 evaluation interval의 역할은?
   - A) 알림 메시지 전송 간격
   - B) 알림 규칙 평가 주기
   - C) 데이터 보존 기간
   - D) 대시보드 새로고침 간격

<details>
<summary>정답 보기</summary>

**정답: B) 알림 규칙 평가 주기**

**설명:**
evaluation interval은 알림 규칙이 얼마나 자주 평가되는지를 결정합니다. 예를 들어 1m으로 설정하면 매분마다 조건을 검사합니다. 이는 알림의 민감도와 리소스 사용량에 영향을 미칩니다. 너무 짧으면 리소스를 많이 사용하고, 너무 길면 문제 감지가 지연됩니다.

</details>

---

6. Google SRE의 4 Golden Signals에 포함되지 않는 것은?
   - A) Latency
   - B) Traffic
   - C) Availability
   - D) Saturation

<details>
<summary>정답 보기</summary>

**정답: C) Availability**

**설명:**
4 Golden Signals는 Latency(지연 시간), Traffic(트래픽), Errors(오류), Saturation(포화도)입니다. Availability(가용성)는 중요한 메트릭이지만 4 Golden Signals에는 포함되지 않습니다. 가용성은 Errors와 관련이 있지만 별도의 개념입니다.

</details>

---

7. Grafana에서 dashboard variable을 사용하는 주요 이점은?
   - A) 대시보드 로딩 속도 향상
   - B) 동적 필터링으로 대시보드 재사용성 증가
   - C) 데이터 저장 용량 감소
   - D) 보안 강화

<details>
<summary>정답 보기</summary>

**정답: B) 동적 필터링으로 대시보드 재사용성 증가**

**설명:**
Dashboard variable을 사용하면 하나의 대시보드로 여러 클러스터, 네임스페이스, 서비스를 모니터링할 수 있습니다. 드롭다운에서 값을 선택하면 모든 패널의 쿼리가 동적으로 업데이트됩니다. 이를 통해 대시보드 수를 줄이고 유지보수를 간소화할 수 있습니다.

</details>

---

8. Grafana와 Prometheus를 연동할 때 Exemplar 기능의 역할은?
   - A) 메트릭 데이터 압축
   - B) 메트릭과 추적 데이터 연결
   - C) 쿼리 캐싱
   - D) 데이터 백업

<details>
<summary>정답 보기</summary>

**정답: B) 메트릭과 추적 데이터 연결**

**설명:**
Exemplar는 Prometheus 메트릭에 TraceID를 연결하는 기능입니다. 히스토그램이나 카운터 메트릭에 샘플 TraceID를 저장하여, Grafana에서 메트릭 그래프의 특정 지점을 클릭하면 해당 시점의 추적 데이터를 바로 조회할 수 있습니다.

</details>

---

9. Grafana Cloud와 Self-hosted Grafana의 차이점으로 올바른 것은?
   - A) Grafana Cloud는 무료
   - B) Self-hosted는 플러그인 설치 불가
   - C) Grafana Cloud는 자동 확장 및 SLA 제공
   - D) Self-hosted는 데이터 소스 제한 있음

<details>
<summary>정답 보기</summary>

**정답: C) Grafana Cloud는 자동 확장 및 SLA 제공**

**설명:**
Grafana Cloud는 관리형 서비스로 자동 확장, 99.9% SLA, 자동 업데이트 등을 제공합니다. Self-hosted는 완전한 제어권과 모든 플러그인 설치가 가능하지만 인프라 관리가 필요합니다. 두 옵션 모두 다양한 데이터 소스를 지원합니다.

</details>

---

10. Grafana 대시보드 프로비저닝에서 sidecar를 사용할 때 ConfigMap에 필요한 레이블은?
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>정답 보기</summary>

**정답: B) grafana_dashboard: "true"**

**설명:**
Grafana Helm 차트의 sidecar 기능을 사용할 때, 대시보드 JSON을 포함한 ConfigMap에 `grafana_dashboard: "true"` 레이블을 추가해야 합니다. Sidecar 컨테이너가 이 레이블을 가진 ConfigMap을 감시하고 자동으로 대시보드를 프로비저닝합니다.

</details>

---
