# 로깅 개요 퀴즈

로깅 기본 개념에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. 구조화된 로깅(Structured Logging)의 주요 장점이 아닌 것은?

   - A) 검색 및 필터링 효율성 향상
   - B) 로그 파일 크기 감소
   - C) 일관된 로그 형식 유지
   - D) 자동화된 분석 도구와의 호환성

<details>
<summary>정답 보기</summary>

**정답: B) 로그 파일 크기 감소**

**설명:**
구조화된 로깅(특히 JSON 형식)은 실제로 비구조화된 텍스트 로그보다 파일 크기가 더 클 수 있습니다. 필드명과 구분자가 추가되기 때문입니다. 구조화된 로깅의 실제 장점은 검색 효율성, 일관성, 자동화 도구 호환성입니다.

</details>

---

2. 프로덕션 환경에서 권장되는 로그 레벨은?

   - A) DEBUG
   - B) TRACE
   - C) INFO 또는 WARN
   - D) FATAL

<details>
<summary>정답 보기</summary>

**정답: C) INFO 또는 WARN**

**설명:**
프로덕션 환경에서는 INFO 또는 WARN 레벨이 권장됩니다. DEBUG나 TRACE는 너무 상세하여 로그 볼륨이 과도해지고, FATAL만 사용하면 중요한 운영 정보를 놓칠 수 있습니다.

</details>

---

3. Kubernetes에서 가장 권장되는 로그 수집 패턴은?

   - A) 파일 기반 로깅 + Sidecar
   - B) stdout/stderr + DaemonSet 에이전트
   - C) 원격 로깅 서버 직접 전송
   - D) 로컬 파일 저장 후 수동 수집

<details>
<summary>정답 보기</summary>

**정답: B) stdout/stderr + DaemonSet 에이전트**

**설명:**
Kubernetes에서는 컨테이너가 stdout/stderr로 로그를 출력하고, DaemonSet으로 배포된 에이전트가 노드의 `/var/log/containers/`에서 로그를 수집하는 방식이 표준입니다. 이 방식은 kubectl logs 명령어 호환, 자동 로테이션, 별도 볼륨 불필요 등의 장점이 있습니다.

</details>

---

4. 로그 저장소 선택 시 "비용 최적화"가 최우선인 경우 권장되는 솔루션은?

   - A) Amazon OpenSearch Service
   - B) CloudWatch Logs
   - C) Grafana Loki + S3
   - D) Elasticsearch on EC2

<details>
<summary>정답 보기</summary>

**정답: C) Grafana Loki + S3**

**설명:**
Loki는 로그 콘텐츠를 인덱싱하지 않고 레이블만 인덱싱하여 스토리지 비용을 크게 절감합니다. S3를 백엔드로 사용하면 GB당 $0.023 수준의 저렴한 저장 비용을 달성할 수 있습니다.

</details>

---

5. JSON 로그 형식에서 분산 추적을 위해 포함해야 할 필수 필드는?

   - A) user_id, session_id
   - B) trace_id, span_id
   - C) request_id, response_time
   - D) level, message

<details>
<summary>정답 보기</summary>

**정답: B) trace_id, span_id**

**설명:**
분산 추적을 위해서는 trace_id(전체 요청 추적)와 span_id(개별 작업 식별)가 필수입니다. 이 필드들을 통해 여러 서비스에 걸친 요청의 흐름을 추적할 수 있습니다.

</details>

---

6. 로그 수집 파이프라인에서 "처리 계층"의 역할이 아닌 것은?

   - A) 로그 파싱 및 정규화
   - B) Kubernetes 메타데이터 추가
   - C) 로그 저장 및 인덱싱
   - D) 필터링 및 샘플링

<details>
<summary>정답 보기</summary>

**정답: C) 로그 저장 및 인덱싱**

**설명:**
로그 저장 및 인덱싱은 "저장 계층(Storage Layer)"의 역할입니다. 처리 계층은 파싱, 메타데이터 추가, 필터링, 버퍼링 등을 담당합니다.

</details>

---

7. 로그 보존 기간 설정 시 금융 규정 준수를 위한 권장 기간은?

   - A) 30일
   - B) 1년
   - C) 7년
   - D) 90일

<details>
<summary>정답 보기</summary>

**정답: C) 7년**

**설명:**
금융 규정 준수(예: SOX, PCI-DSS 관련)를 위해서는 일반적으로 7년의 로그 보존이 권장됩니다. 의료(HIPAA)는 6년, 일반적인 운영 로그는 1년 정도가 권장됩니다.

</details>

---

8. Sidecar 패턴으로 로그를 수집해야 하는 경우는?

   - A) 모든 표준 Kubernetes 워크로드
   - B) 레거시 애플리케이션이 파일로만 로그를 출력하는 경우
   - C) CPU 리소스가 제한된 환경
   - D) 단일 컨테이너 파드만 있는 경우

<details>
<summary>정답 보기</summary>

**정답: B) 레거시 애플리케이션이 파일로만 로그를 출력하는 경우**

**설명:**
Sidecar 패턴은 레거시 애플리케이션(stdout/stderr 대신 파일 로깅), 멀티테넌트 환경에서 로그 격리, 특수 로그 형식 처리가 필요한 경우에 사용됩니다. 리소스 오버헤드가 있으므로 표준 워크로드에는 DaemonSet 방식이 더 효율적입니다.

</details>

---

9. 다음 중 쿼리 성능과 전문 검색(Full-text Search) 모두 "우수"한 로그 저장소는?

   - A) Grafana Loki
   - B) CloudWatch Logs
   - C) Amazon OpenSearch Service
   - D) ClickHouse

<details>
<summary>정답 보기</summary>

**정답: C) Amazon OpenSearch Service**

**설명:**
OpenSearch(Elasticsearch 포크)는 Lucene 기반의 강력한 전문 검색 기능과 복잡한 집계 쿼리를 모두 지원합니다. Loki는 전문 검색이 제한적이고, CloudWatch와 ClickHouse는 전문 검색이 양호 수준입니다.

</details>

---

10. EKS 컨트롤 플레인 로깅에서 보안 감사를 위해 반드시 활성화해야 하는 로그 유형은?

    - A) scheduler
    - B) controllerManager
    - C) audit
    - D) api

<details>
<summary>정답 보기</summary>

**정답: C) audit**

**설명:**
audit 로그는 Kubernetes API 서버에 대한 모든 요청을 기록하는 감사 로그입니다. 누가, 언제, 무엇을 했는지 추적할 수 있어 보안 감사 및 규정 준수에 필수적입니다. api 로그도 중요하지만, 보안 감사 목적으로는 audit이 가장 핵심입니다.

</details>
