# Observability 스택 구성 퀴즈

> **관련 문서**: [Observability 스택 구성](../../ops/09-observability-stack.md)

## 객관식 문제

### 1. Grafana Loki의 SimpleScalable 배포 모드의 특징은 무엇인가요?

- A) 단일 Pod에서 모든 기능 실행
- B) Read, Write, Backend 컴포넌트를 분리하여 독립적 스케일링 가능
- C) 모든 컴포넌트가 StatefulSet으로 배포
- D) 외부 객체 스토리지 불필요

<details>
<summary>정답 보기</summary>

**정답: B) Read, Write, Backend 컴포넌트를 분리하여 독립적 스케일링 가능**

**설명:**
SimpleScalable 모드는 Loki를 Read, Write, Backend 세 가지 컴포넌트로 분리합니다. 각 컴포넌트를 독립적으로 스케일링할 수 있어 쓰기 부하가 높으면 Write만, 쿼리 부하가 높으면 Read만 확장할 수 있습니다. 중규모 환경에 적합합니다.

</details>

### 2. Grafana Tempo에서 샘플링 전략 중 tail-based sampling의 장점은 무엇인가요?

- A) 리소스 사용량이 가장 적음
- B) 에러나 느린 요청 등 중요한 트레이스를 선택적으로 저장
- C) 구현이 가장 간단함
- D) 모든 트레이스를 저장

<details>
<summary>정답 보기</summary>

**정답: B) 에러나 느린 요청 등 중요한 트레이스를 선택적으로 저장**

**설명:**
Tail-based sampling은 트레이스가 완료된 후 전체 내용을 검사하여 샘플링 결정을 내립니다. 에러가 발생했거나 지연이 긴 트레이스를 우선 저장할 수 있어 디버깅에 유용한 데이터를 효율적으로 수집합니다. Head-based는 시작 시점에 결정하므로 이런 선택이 불가능합니다.

</details>

### 3. OpenTelemetry Collector의 주요 역할이 아닌 것은 무엇인가요?

- A) 텔레메트리 데이터 수신 (Receivers)
- B) 데이터 처리 및 변환 (Processors)
- C) 영구 데이터 저장 (Storage)
- D) 다양한 백엔드로 데이터 전송 (Exporters)

<details>
<summary>정답 보기</summary>

**정답: C) 영구 데이터 저장 (Storage)**

**설명:**
OpenTelemetry Collector는 텔레메트리 데이터의 수집(Receivers), 처리(Processors), 전송(Exporters)을 담당하는 에이전트/게이트웨이입니다. 영구 저장은 Collector의 역할이 아니며, Prometheus, Loki, Tempo 같은 백엔드 시스템이 담당합니다.

</details>

### 4. Amazon Managed Prometheus (AMP)의 Remote Write 설정에서 sigv4 인증이 필요한 이유는 무엇인가요?

- A) 데이터 압축
- B) AWS IAM 기반 인증으로 보안 액세스 제어
- C) 데이터 암호화
- D) 속도 향상

<details>
<summary>정답 보기</summary>

**정답: B) AWS IAM 기반 인증으로 보안 액세스 제어**

**설명:**
AMP는 AWS 서비스이므로 IAM 기반 인증이 필요합니다. sigv4는 AWS Signature Version 4 인증 방식으로, Prometheus가 AMP에 메트릭을 전송할 때 IAM 역할/사용자의 자격 증명을 사용하여 인증합니다. 이를 통해 무단 접근을 방지합니다.

</details>

### 5. Loki에서 로그 보존 기간을 설정하는 설정 항목은 무엇인가요?

- A) max_look_back_period
- B) retention_period
- C) compactor.retention_enabled 및 limits_config.retention_period
- D) storage.retention_size

<details>
<summary>정답 보기</summary>

**정답: C) compactor.retention_enabled 및 limits_config.retention_period**

**설명:**
Loki에서 로그 보존을 설정하려면 compactor에서 `retention_enabled: true`를 설정하고, limits_config에서 `retention_period`(예: 720h = 30일)를 지정합니다. Compactor가 주기적으로 오래된 청크를 삭제하여 스토리지를 관리합니다.

</details>

### 6. Grafana에서 여러 데이터 소스(Prometheus, Loki, Tempo)를 연결하기 위해 설정하는 기능은 무엇인가요?

- A) Alerting Rules
- B) Derived Fields / Data Source Correlation
- C) Dashboard Variables
- D) Annotations

<details>
<summary>정답 보기</summary>

**정답: B) Derived Fields / Data Source Correlation**

**설명:**
Grafana의 Derived Fields(Loki) 또는 Data Source Correlation 기능을 사용하면 데이터 소스 간 연결을 설정할 수 있습니다. 예를 들어, Loki 로그에서 추출한 Trace ID를 클릭하면 Tempo에서 해당 트레이스를 조회하도록 연결할 수 있습니다.

</details>

### 7. Tempo에서 트레이스 검색 성능을 향상시키기 위한 기능은 무엇인가요?

- A) Compaction
- B) Search (TraceQL) 및 metrics-generator
- C) Sampling
- D) Replication

<details>
<summary>정답 보기</summary>

**정답: B) Search (TraceQL) 및 metrics-generator**

**설명:**
Tempo는 기본적으로 Trace ID 기반 조회에 최적화되어 있지만, Search 기능(TraceQL)을 활성화하면 속성 기반 검색이 가능합니다. metrics-generator는 트레이스에서 RED 메트릭을 자동 생성하여 빠른 성능 분석을 지원합니다.

</details>

### 8. OTEL Collector에서 batch processor의 역할은 무엇인가요?

- A) 데이터 필터링
- B) 여러 텔레메트리 데이터를 묶어서 효율적으로 전송
- C) 데이터 암호화
- D) 샘플링 결정

<details>
<summary>정답 보기</summary>

**정답: B) 여러 텔레메트리 데이터를 묶어서 효율적으로 전송**

**설명:**
batch processor는 개별 텔레메트리 데이터를 모아서 배치로 전송합니다. send_batch_size(한 번에 보낼 최대 항목 수)와 timeout(최대 대기 시간)을 설정합니다. 이를 통해 네트워크 효율성을 높이고 백엔드 부하를 줄입니다.

</details>

### 9. Loki Distributed 모드에서 Ingester의 역할은 무엇인가요?

- A) 쿼리 실행
- B) 로그 데이터를 메모리에 버퍼링하고 청크로 압축하여 저장
- C) 트래픽 분산
- D) 인증 처리

<details>
<summary>정답 보기</summary>

**정답: B) 로그 데이터를 메모리에 버퍼링하고 청크로 압축하여 저장**

**설명:**
Ingester는 Distributor로부터 받은 로그 데이터를 메모리에 버퍼링합니다. 충분한 데이터가 모이면 청크로 압축하여 객체 스토리지(S3 등)에 저장합니다. StatefulSet으로 배포되며 데이터 내구성을 위해 복제본을 유지합니다.

</details>

### 10. Prometheus에서 높은 카디널리티 메트릭을 관리하기 위한 방법이 아닌 것은 무엇인가요?

- A) 불필요한 레이블 제거
- B) Recording Rules로 사전 집계
- C) 모든 메트릭에 고유 ID 레이블 추가
- D) Metric Relabeling으로 필터링

<details>
<summary>정답 보기</summary>

**정답: C) 모든 메트릭에 고유 ID 레이블 추가**

**설명:**
고유 ID 레이블을 추가하면 카디널리티가 급격히 증가하여 오히려 문제가 됩니다. 카디널리티 관리를 위해서는 불필요한 레이블 제거, Recording Rules로 자주 사용되는 쿼리 사전 집계, Metric Relabeling으로 불필요한 메트릭 필터링 등의 방법을 사용합니다.

</details>
