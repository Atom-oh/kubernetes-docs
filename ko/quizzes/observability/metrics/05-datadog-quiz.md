# Datadog 퀴즈

Datadog에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Datadog의 주요 배포 모델은?
   - A) 자체 호스팅 전용
   - B) SaaS (Software as a Service)
   - C) 온프레미스 전용
   - D) 하이브리드 필수

<details>
<summary>정답 보기</summary>

**정답: B) SaaS (Software as a Service)**

**설명:**
Datadog은 SaaS 모델로 제공되는 통합 관측성 플랫폼입니다. 사용자는 Datadog Agent만 배포하면 되고, 데이터 저장, 처리, 시각화는 Datadog의 클라우드 인프라에서 처리됩니다. 이를 통해 운영 오버헤드 없이 강력한 모니터링 기능을 사용할 수 있습니다.

</details>

---

2. Datadog Cluster Agent의 역할은?
   - A) 컨테이너 로그 수집
   - B) 클러스터 레벨 메트릭 및 이벤트 수집
   - C) APM 트레이스 처리
   - D) 대시보드 렌더링

<details>
<summary>정답 보기</summary>

**정답: B) 클러스터 레벨 메트릭 및 이벤트 수집**

**설명:**
Datadog Cluster Agent는 Kubernetes 클러스터 레벨의 메트릭과 이벤트를 수집합니다. 또한 HPA(Horizontal Pod Autoscaler)를 위한 커스텀 메트릭 서버 역할과 Admission Controller를 통한 자동 APM 계측 주입 기능도 제공합니다.

</details>

---

3. Datadog에서 자동 APM 계측을 활성화하는 방법은?
   - A) 애플리케이션 코드 수정 필수
   - B) Admission Controller와 파드 라벨 사용
   - C) 별도 APM 서버 배포
   - D) 수동으로 라이브러리 주입

<details>
<summary>정답 보기</summary>

**정답: B) Admission Controller와 파드 라벨 사용**

**설명:**
Datadog Admission Controller를 활성화하면, `admission.datadoghq.com/enabled: "true"` 라벨이 있는 파드에 자동으로 APM 계측 라이브러리가 주입됩니다. Java, Python, Node.js, .NET, Ruby 등 주요 언어를 지원하며, 코드 수정 없이 트레이싱을 시작할 수 있습니다.

</details>

---

4. DogStatsD의 역할은?
   - A) 로그 수집
   - B) 커스텀 메트릭 수집 (StatsD 호환)
   - C) 대시보드 생성
   - D) 알림 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) 커스텀 메트릭 수집 (StatsD 호환)**

**설명:**
DogStatsD는 Datadog Agent에 포함된 StatsD 호환 메트릭 수집 데몬입니다. 애플리케이션에서 UDP를 통해 커스텀 메트릭(카운터, 게이지, 히스토그램, 분포)을 전송할 수 있습니다. StatsD 프로토콜과 호환되며, 태그 기능이 추가되어 있습니다.

</details>

---

5. Datadog에서 트레이스와 로그를 연결하는 방법은?
   - A) 수동으로 로그 파일 업로드
   - B) 로그에 trace_id와 span_id 포함
   - C) 별도의 연결 서비스 배포
   - D) 로그와 트레이스 시간대 일치

<details>
<summary>정답 보기</summary>

**정답: B) 로그에 trace_id와 span_id 포함**

**설명:**
Datadog에서 트레이스와 로그를 연결하려면 로그에 `dd.trace_id`와 `dd.span_id`를 포함해야 합니다. Datadog APM 라이브러리는 MDC(Mapped Diagnostic Context)를 통해 이 정보를 자동으로 주입할 수 있습니다. 이를 통해 APM에서 관련 로그를 바로 조회할 수 있습니다.

</details>

---

6. Datadog의 비용 구조에서 인프라 모니터링의 과금 단위는?
   - A) 메트릭 수
   - B) 호스트 수
   - C) API 호출 수
   - D) 데이터 전송량

<details>
<summary>정답 보기</summary>

**정답: B) 호스트 수**

**설명:**
Datadog 인프라 모니터링은 호스트 수 기준으로 과금됩니다. 각 노드, 인스턴스, 컨테이너 호스트가 과금 대상입니다. APM, 로그 관리, 기타 기능은 별도의 과금 체계를 가지며, 호스트 기반 과금으로 비용 예측이 용이합니다.

</details>

---

7. Datadog Watchdog의 기능은?
   - A) 수동 알림 설정
   - B) AI 기반 자동 이상 탐지
   - C) 로그 검색
   - D) 대시보드 생성

<details>
<summary>정답 보기</summary>

**정답: B) AI 기반 자동 이상 탐지**

**설명:**
Watchdog은 Datadog의 AI/ML 기반 자동 이상 탐지 기능입니다. 인프라, APM, 로그 데이터에서 비정상적인 패턴을 자동으로 감지하고 알림을 생성합니다. 수동으로 임계값을 설정할 필요 없이 이상 상황을 파악할 수 있습니다.

</details>

---

8. Datadog Agent에서 Prometheus 메트릭을 수집하는 방법은?
   - A) 별도의 Prometheus 서버 필요
   - B) 파드 어노테이션으로 자동 디스커버리 설정
   - C) 수동으로 각 엔드포인트 등록
   - D) Prometheus를 Datadog으로 교체

<details>
<summary>정답 보기</summary>

**정답: B) 파드 어노테이션으로 자동 디스커버리 설정**

**설명:**
Datadog Agent는 `ad.datadoghq.com/<container>.checks` 어노테이션을 사용하여 Prometheus 메트릭 엔드포인트를 자동으로 발견하고 수집합니다. Prometheus scrape 설정과 유사한 방식으로 설정할 수 있으며, 별도의 Prometheus 서버 없이 메트릭을 수집할 수 있습니다.

</details>

---

9. Datadog에서 SLO(Service Level Objective)를 설정할 때 사용할 수 있는 메트릭 유형은?
   - A) 로그 이벤트만
   - B) 메트릭 기반, 모니터 기반, 타임 슬라이스 기반
   - C) APM 트레이스만
   - D) 인프라 메트릭만

<details>
<summary>정답 보기</summary>

**정답: B) 메트릭 기반, 모니터 기반, 타임 슬라이스 기반**

**설명:**
Datadog SLO는 세 가지 유형을 지원합니다: 메트릭 기반(성공/실패 카운트), 모니터 기반(기존 모니터 상태), 타임 슬라이스 기반(시간 간격별 상태). APM 트레이스, 커스텀 메트릭, 로그 기반 메트릭 등 다양한 데이터 소스를 활용할 수 있습니다.

</details>

---

10. Datadog 비용 최적화 전략으로 올바르지 않은 것은?
    - A) APM 트레이스 샘플링 레이트 조정
    - B) 불필요한 로그 필터링
    - C) 모든 메트릭을 최고 해상도로 수집
    - D) 커스텀 메트릭 카디널리티 관리

<details>
<summary>정답 보기</summary>

**정답: C) 모든 메트릭을 최고 해상도로 수집**

**설명:**
Datadog 비용 최적화를 위해서는 APM 트레이스 샘플링, 로그 필터링, 커스텀 메트릭 카디널리티 관리가 중요합니다. 모든 메트릭을 최고 해상도로 수집하면 비용이 급증합니다. 필요한 메트릭만 선별적으로 수집하고, 적절한 샘플링을 적용해야 합니다.

</details>
