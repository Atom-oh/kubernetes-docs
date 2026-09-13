# Grafana Tempo 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

기준: Tempo 3.0.3, 차트 3.6.0.

---

1. Tempo 저장·검색의 올바른 설명은?

   - A) 모든 속성을 Elasticsearch에 인덱싱해야 한다
   - B) 오브젝트 스토리지 Parquet 블록으로 TraceID/TraceQL을 지원하며 저장·조회 비용은 남는다
   - C) ID만 알면 손실된 모든 스팬을 복구한다
   - D) 추적을 영구 보관한다

<details>
<summary>정답 보기</summary>

**정답: B) 오브젝트 스토리지 Parquet 블록으로 TraceID/TraceQL을 지원하며 저장·조회 비용은 남는다**

전용 컬럼·메타데이터·캐시가 있으므로 인덱싱·조회 비용이 0이라는 뜻이 아닙니다. 정상 수집되어 보관 중인 데이터만 조회할 수 있습니다.

</details>

---

2. Tempo 3 분산 쓰기 경로에서 Kafka에 기록하기 전에 추적을 수신·검증하는 구성 요소는?

   - A) Block-builder
   - B) Querier
   - C) Distributor
   - D) Backend worker

<details>
<summary>정답 보기</summary>

**정답: C) Distributor**

Distributor가 Kafka에 기록하고 Live-store·Block-builder·선택적인 Metrics-generator가 각각 소비합니다. Tempo 2 Ingester 경로와 다릅니다.

</details>

---

3. 오류 상태 스팬을 선택하는 TraceQL은?

   - A) `{ duration > 1s }`
   - B) `{ status = error }`
   - C) `{ status = ok }`
   - D) `{ span.http.response.status_code = 200 }`

<details>
<summary>정답 보기</summary>

**정답: B) `{ status = error }`**

스팬 상태 error는 지연 임계치나 특정 HTTP 응답 조건과 별개입니다.

</details>

---

4. 이 EKS/S3 예제가 사용하는 주체 설정은?

   - A) Helm values의 정적 access key
   - B) 모든 워크로드가 공유하는 노드 역할
   - C) 정확한 OIDC sub/aud와 제한된 S3 권한으로 monitoring:tempo에 연결한 IRSA
   - D) Pod와 연결되지 않은 무관한 ServiceAccount

<details>
<summary>정답 보기</summary>

**정답: C) 정확한 OIDC sub/aud와 제한된 S3 권한으로 monitoring:tempo에 연결한 IRSA**

역할 annotation과 모든 Tempo Pod의 ServiceAccount가 일치해야 합니다. 다른 워크로드 자격 증명 방식은 고정 이미지와의 호환성을 별도로 확인합니다.

</details>

---

5. 예제 Metrics-generator 프로세서가 추적에서 생성하지 않는 것은?

   - A) Service graph 메트릭
   - B) Span metrics
   - C) 임의의 애플리케이션 로그 메트릭
   - D) 스팬에서 파생한 Rate/Error/Duration 메트릭

<details>
<summary>정답 보기</summary>

**정답: C) 임의의 애플리케이션 로그 메트릭**

Span-metrics·service-graphs는 명시적 프로세서 활성화와 remote write가 필요합니다. 임의 로그를 메트릭으로 바꾸는 기능이 아닙니다.

</details>

---

6. Tempo 3 내구성에 대한 올바른 설명은?

   - A) Tempo 복제본 3개면 항상 무손실이다
   - B) 마이크로서비스는 Kafka를 사용하며 복제·ISR·보존·복구를 별도로 설계해야 한다
   - C) 모놀리식에도 항상 Kafka가 필요하다
   - D) 모든 StatefulSet에는 자동으로 영구 PVC가 생긴다

<details>
<summary>정답 보기</summary>

**정답: B) 마이크로서비스는 Kafka를 사용하며 복제·ISR·보존·복구를 별도로 설계해야 한다**

차트의 Live-store·Block-builder 데이터는 emptyDir입니다. Tempo 복제본 수가 Kafka 내구성을 정하지 않으며 모놀리식에는 Kafka가 필수가 아닙니다.

</details>

---

7. Grafana 상관분석 방향의 올바른 설명은?

   - A) 같은 namespace만으로 상관분석이 생긴다
   - B) Tempo tracesToLogsV2는 Trace→Logs, Loki derivedFields는 Logs→Trace이다
   - C) 두 시스템이 같은 S3 버킷을 공유해야 한다
   - D) derivedFields가 애플리케이션의 TraceID를 생성한다

<details>
<summary>정답 보기</summary>

**정답: B) Tempo tracesToLogsV2는 Trace→Logs, Loki derivedFields는 Logs→Trace이다**

식별자·데이터 소스 UID·라벨·조회 구간이 실제 데이터와 일치해야 합니다. 링크가 없는 텔레메트리를 복구하지는 않습니다.

</details>

---

8. Tempo 3 백그라운드 compaction·보존 작업을 담당하는 구성 요소는?

   - A) Grafana 브라우저 탭
   - B) OTLP 클라이언트
   - C) Backend scheduler와 backend worker
   - D) 수정 없이 복사한 과거 compactor 설정

<details>
<summary>정답 보기</summary>

**정답: C) Backend scheduler와 backend worker**

이 구성 요소는 이전 Compactor 구조를 대체합니다. 보존 처리는 비동기이며 별도 S3 전체 만료 규칙은 백엔드 동작과 충돌할 수 있습니다.

</details>

---

9. `{ resource.service.name = "A" } >> { resource.service.name = "B" }`의 선택 대상은?

   - A) 다른 추적에 있는 임의의 두 스팬
   - B) 조건에 맞는 A 스팬의 B 후손 스팬
   - C) B가 아닌 A 부모만
   - D) B 직계 자식만

<details>
<summary>정답 보기</summary>

**정답: B) 조건에 맞는 A 스팬의 B 후손 스팬**

결과는 오른쪽 대상입니다. 직계 자식은 >를 사용하며 형제 관계나 같은 추적에 속하는 조건과 다릅니다.

</details>

---

10. 느린 쿼리와 최근 검색의 빈 결과를 조사할 때 적절한 첫 대응은?

   - A) Tempo 2의 ingester.max_block_duration: 30m을 복사한다
   - B) 모든 lag·최근 쿼리 보호를 끈다
   - C) 튜닝 전에 시간 범위·실제 수집 데이터·lag·조회량·제한을 확인한다
   - D) 텔레메트리 부재와 무트래픽을 정상 수치로 강제 변환한다

<details>
<summary>정답 보기</summary>

**정답: C) 튜닝 전에 시간 범위·실제 수집 데이터·lag·조회량·제한을 확인한다**

Tempo 3는 구성 요소·기본값이 다릅니다. 빈 결과·무트래픽·실패를 구분하고 설정 렌더링만으로 운영 동작이 증명된다고 판단하지 않습니다.

</details>

---

[Tempo 본문 복습](../../../observability/tracing/01-tempo.md).
