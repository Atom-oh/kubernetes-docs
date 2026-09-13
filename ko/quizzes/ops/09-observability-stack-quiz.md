# Observability 스택 구성 퀴즈

> **관련 문서**: [Observability 스택 구성](../../ops/09-observability-stack.md)

## 1. Loki 신규 배포 모드를 고를 때 올바른 설명은?

- A) SimpleScalable은 모든 신규 배포의 영구 기본값이다
- B) SimpleScalable은 deprecated이며 4.0 제거 예정이므로 대안을 검토한다
- C) Monolithic은 객체 저장소를 사용할 수 없다
- D) 복제본 3개면 AZ 장애 격리가 자동 보장된다

<details>
<summary>정답 보기</summary>

**정답: B**

SSD의 read/write/backend 구분은 역사적 구조 설명입니다. 신규 설계는 지원 수명과 Monolithic/Distributed의 용량·운영 제약을 함께 평가합니다.

</details>

## 2. Tempo 3 분산 모드와 단일 프로세스 모드의 차이는?

- A) 두 모드 모두 기존 ingester를 사용한다
- B) 단일 프로세스도 반드시 Kafka가 필요하다
- C) 분산 모드는 Kafka 경로를 사용하며 단일 프로세스는 Kafka 없이 동작한다
- D) 단일 차트 replicas를 늘리면 지원되는 분산 HA가 된다

<details>
<summary>정답 보기</summary>

**정답: C**

3.x는 분산 ingester 대신 block-builder/live-store를, compactor 대신 backend-scheduler/worker를 사용합니다. 단일 프로세스 경로와 혼용하지 않습니다.

</details>

## 3. Tail sampling의 한계에 대한 설명으로 맞는 것은?

- A) 모든 오류 trace를 반드시 보존한다
- B) decision_wait 안에 받은 span으로 결정하며 head 단계 손실을 복구할 수 없다
- C) 무작위 Service 분산으로도 동일 trace가 항상 한 sampler에 모인다
- D) num_traces는 초당 trace 처리량이다

<details>
<summary>정답 보기</summary>

**정답: B**

늦은 span, buffer 한계, 재시작과 전송 실패가 있습니다. 여러 sampler에는 trace-ID 기반 라우팅이 필요합니다.

</details>

## 4. Collector batch processor의 send_batch_size는 무엇인가요?

- A) 최대 배치 크기
- B) 최대 trace 지연
- C) 전송을 시작하는 항목 수 trigger
- D) 영구 저장 용량

<details>
<summary>정답 보기</summary>

**정답: C**

최대 배치 크기는 send_batch_max_size입니다. memory_limiter와 샘플링 등 데이터 제거 처리 뒤에 batch를 배치합니다.

</details>

## 5. Alloy DaemonSet의 모든 Pod가 클러스터의 모든 로그 대상을 읽으면?

- A) 자동으로 완전한 HA dedup이 된다
- B) 중복 수집할 수 있어 대상 분할 또는 source clustering 구성이 필요하다
- C) Kubernetes API가 자동으로 한 수집기만 허용한다
- D) 반드시 hostPath가 있어야 하므로 시작할 수 없다

<details>
<summary>정답 보기</summary>

**정답: B**

Kubernetes 로그 API source는 파일 tail과 다릅니다. 단일 Deployment/Recreate 예제는 중복을 줄이지만 HA나 무중단을 보장하지 않습니다.

</details>

## 6. Loki 보존 설정에 필요한 조합은?

- A) retention_period만 설정
- B) TSDB 24시간 인덱스, compactor retention 활성화와 delete_request_store, 보존 기간
- C) S3 버킷의 모든 객체를 같은 날짜에 삭제
- D) Grafana dashboard의 시간 범위

<details>
<summary>정답 보기</summary>

**정답: B**

삭제는 지연·비동기 처리되며 compactor 상태와 marker도 유지해야 합니다. 버킷 전체 lifecycle은 인덱스 등 필요한 객체를 손상시킬 수 있습니다.

</details>

## 7. AMP HA 중복 제거에 사용하는 레이블은?

- A) namespace와 pod
- B) cluster와 __replica__
- C) service와 trace_id
- D) region만 있으면 충분하다

<details>
<summary>정답 보기</summary>

**정답: B**

같은 scrape 데이터의 replica는 같은 cluster와 서로 다른 __replica__를 사용합니다. 독립 scrape 범위를 같은 HA 그룹으로 묶으면 데이터가 빠질 수 있습니다.

</details>

## 8. AMP 보존 기간에 대한 올바른 설명은?

- A) 150일이 변경 불가능한 최대값이다
- B) workspace에서 변경할 수 있으며 최대 1,095일이다
- C) 항상 무제한이다
- D) 기간을 늘리면 이미 삭제된 메트릭도 복구된다

<details>
<summary>정답 보기</summary>

**정답: B**

보존 요구·비용·서비스 한도를 확인해 설정합니다. 만료된 데이터가 소급 복원되는 것은 아닙니다.

</details>

## 9. Grafana에서 Loki 로그를 Tempo trace에 연결하려면?

- A) 둘을 설치하면 자동 연결된다
- B) 정확한 trace ID 추출과 명시적 datasource UID, 접근 가능한 trace 데이터
- C) trace ID를 일반 Prometheus label로 추가
- D) HTTP/2만 활성화

<details>
<summary>정답 보기</summary>

**정답: B**

derivedFields와 tracesToLogsV2의 mapping, 시간·tenant·권한을 맞춰야 합니다. exemplar도 계측·OpenMetrics·저장 설정이 모두 필요합니다.

</details>

## 10. 차트 렌더링 성공 후에도 확인해야 할 것은?

- A) 없다. unknown values도 모두 적용된다
- B) 실제 PVC·Service·identity·backend 설정과 쓰기/조회 경로
- C) YAML 들여쓰기만 확인
- D) 모든 리소스를 최신 태그로 바꾸기

<details>
<summary>정답 보기</summary>

**정답: B**

일부 chart values는 오류 없이 무시될 수 있습니다. 예제의 claims/accessModes와 Service 포트, native parser 검증과 실환경 연결 검증을 구별합니다.

</details>
