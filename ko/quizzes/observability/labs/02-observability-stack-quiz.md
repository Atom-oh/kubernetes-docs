# Observability 실습 Part 2: Observability 스택 퀴즈

> **마지막 업데이트**: 2025년 2월

이 퀴즈는 Observability 실습 Part 2의 Observability 스택 구성에 대한 이해도를 테스트합니다.

---

1. OpenTelemetry Collector의 DaemonSet 배포 패턴과 Gateway 배포 패턴의 차이점으로 올바른 것은?
   - A) DaemonSet은 클러스터당 하나의 Collector를 실행하고, Gateway는 노드당 하나를 실행한다
   - B) DaemonSet은 각 노드에서 로컬 텔레메트리를 수집하고, Gateway는 중앙에서 데이터를 집계하고 처리한다
   - C) DaemonSet은 트레이스만 수집하고, Gateway는 메트릭만 수집한다
   - D) 두 패턴은 동일하며 이름만 다르다
<details>
<summary>정답 보기</summary>

**정답: B) DaemonSet은 각 노드에서 로컬 텔레메트리를 수집하고, Gateway는 중앙에서 데이터를 집계하고 처리한다**

**설명:**
DaemonSet 패턴은 각 노드에 Collector를 배포하여 해당 노드의 Pod에서 생성되는 텔레메트리를 로컬에서 수집합니다. 네트워크 홉을 줄이고 노드 수준의 메타데이터를 쉽게 추가할 수 있습니다. Gateway 패턴은 중앙 집중식으로 Collector를 배포하여 여러 소스의 데이터를 집계, 변환, 라우팅합니다. 일반적으로 두 패턴을 함께 사용하여 Agent(DaemonSet) → Gateway 계층 구조를 구성합니다.

</details>

---

2. OpenTelemetry Collector 파이프라인의 Receiver, Processor, Exporter 각각의 역할로 올바른 것은?
   - A) Receiver는 데이터를 전송하고, Processor는 수신하며, Exporter는 변환한다
   - B) Receiver는 텔레메트리 데이터를 수신하고, Processor는 데이터를 변환/필터링하며, Exporter는 백엔드로 전송한다
   - C) 세 컴포넌트는 모두 동일한 역할을 수행한다
   - D) Receiver만 필수이고 나머지는 선택 사항이다
<details>
<summary>정답 보기</summary>

**정답: B) Receiver는 텔레메트리 데이터를 수신하고, Processor는 데이터를 변환/필터링하며, Exporter는 백엔드로 전송한다**

**설명:**
OTel Collector 파이프라인은 세 가지 컴포넌트로 구성됩니다. Receiver는 다양한 형식(OTLP, Prometheus, Jaeger 등)의 텔레메트리를 수신합니다. Processor는 배치 처리, 속성 추가/제거, 샘플링, 필터링 등 데이터 변환 작업을 수행합니다. Exporter는 처리된 데이터를 AMP, Tempo, Loki 등 백엔드 시스템으로 전송합니다.

</details>

---

3. Prometheus remote write를 Amazon Managed Prometheus (AMP)로 전송할 때 사용하는 인증 방식은?
   - A) Basic Authentication (사용자명/비밀번호)
   - B) API Key
   - C) IRSA를 통한 IAM 역할과 SigV4 서명
   - D) mTLS 인증서
<details>
<summary>정답 보기</summary>

**정답: C) IRSA를 통한 IAM 역할과 SigV4 서명**

**설명:**
AMP는 AWS 서비스이므로 AWS SigV4 서명을 사용한 인증을 요구합니다. EKS에서는 IRSA를 통해 Prometheus 또는 OTel Collector Pod에 IAM 역할을 부여하고, sigv4 proxy 또는 AWS SDK가 자동으로 요청에 SigV4 서명을 추가합니다. 이 방식은 자격 증명을 코드에 포함하지 않고도 안전하게 인증할 수 있습니다.

</details>

---

4. VictoriaMetrics가 Prometheus와 호환되는 주요 이유는?
   - A) VictoriaMetrics가 Prometheus의 포크이기 때문
   - B) VictoriaMetrics가 Prometheus remote write/read API와 PromQL을 지원하기 때문
   - C) 두 시스템이 동일한 스토리지 엔진을 사용하기 때문
   - D) CNCF에서 호환성을 강제하기 때문
<details>
<summary>정답 보기</summary>

**정답: B) VictoriaMetrics가 Prometheus remote write/read API와 PromQL을 지원하기 때문**

**설명:**
VictoriaMetrics는 Prometheus의 포크가 아닌 독립적으로 개발된 시계열 데이터베이스입니다. 그러나 Prometheus remote write/read 프로토콜을 완벽히 지원하고 PromQL 호환 쿼리 언어(MetricsQL)를 제공합니다. 이를 통해 기존 Prometheus 기반 시스템에서 쉽게 마이그레이션할 수 있으며, Grafana 등 Prometheus 데이터소스를 사용하는 도구와 그대로 연동됩니다.

</details>

---

5. Grafana Mimir의 단일 바이너리(monolithic) 모드의 특징으로 올바른 것은?
   - A) 프로덕션 환경에서만 사용할 수 있다
   - B) 모든 컴포넌트(ingester, querier, compactor 등)가 하나의 프로세스에서 실행되어 소규모 환경이나 테스트에 적합하다
   - C) 수평 확장이 마이크로서비스 모드보다 더 쉽다
   - D) 단일 바이너리 모드는 메트릭만 지원하고 로그는 지원하지 않는다
<details>
<summary>정답 보기</summary>

**정답: B) 모든 컴포넌트(ingester, querier, compactor 등)가 하나의 프로세스에서 실행되어 소규모 환경이나 테스트에 적합하다**

**설명:**
Mimir의 단일 바이너리 모드는 distributor, ingester, querier, compactor, store-gateway 등 모든 컴포넌트를 하나의 프로세스로 실행합니다. 운영 복잡성이 낮아 개발, 테스트, 소규모 프로덕션 환경에 적합합니다. 대규모 환경에서는 각 컴포넌트를 독립적으로 스케일링할 수 있는 마이크로서비스 모드가 권장됩니다.

</details>

---

6. Grafana Loki SimpleScalable 모드의 구성 요소에 해당하지 않는 것은?
   - A) Read 컴포넌트
   - B) Write 컴포넌트
   - C) Backend 컴포넌트
   - D) Transformer 컴포넌트
<details>
<summary>정답 보기</summary>

**정답: D) Transformer 컴포넌트**

**설명:**
Loki SimpleScalable 모드는 세 가지 타겟으로 구성됩니다. Write 컴포넌트는 로그 수집 및 청크 생성을 담당하고, Read 컴포넌트는 쿼리 처리를 담당합니다. Backend 컴포넌트는 compactor, index-gateway 등 백그라운드 작업을 수행합니다. Transformer는 Loki의 구성 요소가 아닙니다. 이 모드는 전체 마이크로서비스 모드보다 단순하면서도 적절한 수준의 확장성을 제공합니다.

</details>

---

7. ClickHouse를 로그 저장소로 사용할 때의 주요 장점은?
   - A) JSON 로그만 저장할 수 있다
   - B) 컬럼 기반 스토리지로 집계 쿼리가 빠르고, 높은 압축률로 스토리지 비용을 절감할 수 있다
   - C) Kubernetes 환경에서만 사용할 수 있다
   - D) 실시간 로그 스트리밍만 지원한다
<details>
<summary>정답 보기</summary>

**정답: B) 컬럼 기반 스토리지로 집계 쿼리가 빠르고, 높은 압축률로 스토리지 비용을 절감할 수 있다**

**설명:**
ClickHouse는 컬럼 기반(columnar) 데이터베이스로, 특정 컬럼만 읽는 분석 쿼리에서 뛰어난 성능을 보입니다. 동일한 컬럼의 데이터가 함께 저장되어 압축 효율이 높고, 대규모 로그 데이터의 스토리지 비용을 크게 줄일 수 있습니다. SQL 기반 쿼리를 지원하여 학습 곡선이 낮고, 다양한 데이터 형식을 지원합니다.

</details>

---

8. FluentBit과 Grafana Alloy의 차이점으로 올바른 것은?
   - A) FluentBit은 로그만 수집하고, Grafana Alloy는 메트릭, 로그, 트레이스를 모두 수집할 수 있다
   - B) Grafana Alloy는 로그만 수집할 수 있다
   - C) FluentBit이 Grafana Alloy보다 더 많은 기능을 제공한다
   - D) 두 도구는 완전히 동일한 기능을 제공한다
<details>
<summary>정답 보기</summary>

**정답: A) FluentBit은 로그만 수집하고, Grafana Alloy는 메트릭, 로그, 트레이스를 모두 수집할 수 있다**

**설명:**
FluentBit은 경량 로그 수집기로 로그 수집, 파싱, 필터링, 전송에 특화되어 있습니다. Grafana Alloy(이전 Grafana Agent)는 OpenTelemetry 기반의 통합 텔레메트리 수집기로, 메트릭(Prometheus 스크래핑), 로그(Loki로 전송), 트레이스(Tempo로 전송)를 모두 처리할 수 있습니다. Alloy는 단일 에이전트로 모든 텔레메트리를 수집하려는 경우에 적합합니다.

</details>

---

9. Grafana에서 Tempo와 Loki 간 TraceID derived field를 설정하는 목적은?
   - A) 로그와 트레이스 데이터를 동일한 스토리지에 저장하기 위해
   - B) 로그에서 TraceID를 추출하여 해당 트레이스로 바로 이동할 수 있는 링크를 생성하기 위해
   - C) Tempo의 성능을 향상시키기 위해
   - D) Loki의 저장 용량을 줄이기 위해
<details>
<summary>정답 보기</summary>

**정답: B) 로그에서 TraceID를 추출하여 해당 트레이스로 바로 이동할 수 있는 링크를 생성하기 위해**

**설명:**
Derived field는 로그 라인에서 정규표현식으로 특정 값(예: TraceID)을 추출하고, 해당 값을 다른 데이터소스(예: Tempo)로 연결하는 링크를 자동 생성합니다. 이를 통해 로그를 보다가 관련 트레이스로 한 번의 클릭으로 이동할 수 있어 문제 분석 시간을 크게 단축할 수 있습니다. 이것이 Observability의 핵심인 상관관계(correlation) 기능입니다.

</details>

---

10. Alertmanager에서 Amazon SNS receiver를 설정하는 방법으로 올바른 것은?
    - A) Alertmanager가 SNS를 기본으로 지원하므로 별도 설정이 필요 없다
    - B) SNS webhook URL을 Alertmanager의 webhook_configs에 직접 입력한다
    - C) Alertmanager의 sns_configs를 사용하여 AWS 리전, 토픽 ARN, sigv4 인증을 설정한다
    - D) SNS는 Alertmanager와 연동할 수 없다
<details>
<summary>정답 보기</summary>

**정답: C) Alertmanager의 sns_configs를 사용하여 AWS 리전, 토픽 ARN, sigv4 인증을 설정한다**

**설명:**
Alertmanager는 기본으로 Amazon SNS를 receiver로 지원합니다. sns_configs 섹션에서 AWS 리전, SNS 토픽 ARN을 지정하고, sigv4 인증 블록에서 IAM 역할 기반 인증을 설정합니다. IRSA를 사용하면 Alertmanager Pod가 자동으로 IAM 자격 증명을 획득하여 SNS에 알림을 발행할 수 있습니다.

</details>
