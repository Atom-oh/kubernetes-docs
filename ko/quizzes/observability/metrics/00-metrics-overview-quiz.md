# 메트릭 개요 퀴즈

메트릭의 기본 개념과 모니터링 솔루션에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. Prometheus 메트릭의 네 가지 기본 유형 중, 값이 증가만 가능하고 재시작 시 0으로 리셋되는 유형은?
   - A) Gauge
   - B) Counter
   - C) Histogram
   - D) Summary

<details>
<summary>정답 보기</summary>

**정답: B) Counter**

**설명:**
Counter는 누적되는 값을 추적하는 메트릭 유형으로, 값은 증가만 가능하며 재시작 시 0으로 리셋됩니다. HTTP 요청 수, 에러 수, 완료된 작업 수 등을 추적하는 데 사용됩니다. Gauge는 증가/감소 모두 가능하고, Histogram과 Summary는 분포를 측정합니다.

</details>

---

2. 다음 중 카디널리티(Cardinality)에 대한 설명으로 올바른 것은?
   - A) 메트릭의 수집 간격을 의미한다
   - B) 메트릭의 고유한 시계열 조합 수를 의미한다
   - C) 메트릭의 데이터 압축률을 의미한다
   - D) 메트릭의 보존 기간을 의미한다

<details>
<summary>정답 보기</summary>

**정답: B) 메트릭의 고유한 시계열 조합 수를 의미한다**

**설명:**
카디널리티는 메트릭의 고유한 레이블 조합 수를 의미합니다. 높은 카디널리티는 스토리지 사용량과 쿼리 성능에 직접적인 영향을 미치며, user_id나 request_id와 같이 무한히 증가할 수 있는 값을 레이블로 사용하면 카디널리티가 폭발적으로 증가합니다.

</details>

---

3. Pull 모델과 Push 모델에 대한 설명으로 올바르지 않은 것은?
   - A) Prometheus는 Pull 기반 시스템이다
   - B) Pull 모델에서는 중앙에서 수집 대상과 주기를 제어한다
   - C) Push 모델은 짧은 수명 작업의 메트릭 수집에 적합하다
   - D) Pull 모델은 NAT/방화벽 뒤의 대상 접근이 쉽다

<details>
<summary>정답 보기</summary>

**정답: D) Pull 모델은 NAT/방화벽 뒤의 대상 접근이 쉽다**

**설명:**
Pull 모델에서는 모니터링 서버가 대상에 직접 HTTP 요청을 보내 메트릭을 수집하므로, NAT/방화벽 뒤의 대상에 접근하기 어렵습니다. 반면 Push 모델에서는 대상이 직접 메트릭을 전송하므로 NAT/방화벽 환경에서 유리합니다. Pushgateway를 사용하면 Pull 모델에서도 짧은 수명 작업의 메트릭을 수집할 수 있습니다.

</details>

---

4. Histogram과 Summary의 차이점에 대한 설명으로 올바른 것은?
   - A) Histogram은 클라이언트에서 분위수를 계산한다
   - B) Summary는 여러 인스턴스 간 집계가 가능하다
   - C) Histogram은 서버(쿼리 시)에서 분위수를 계산한다
   - D) Summary가 Histogram보다 스토리지 효율성이 높다

<details>
<summary>정답 보기</summary>

**정답: C) Histogram은 서버(쿼리 시)에서 분위수를 계산한다**

**설명:**
Histogram은 버킷 기반으로 데이터를 저장하고 쿼리 시 서버에서 분위수를 계산합니다. Summary는 클라이언트에서 분위수를 계산하여 저장합니다. Histogram은 여러 인스턴스 간 집계가 가능하지만, Summary는 집계가 불가능합니다. SLO/SLI 측정이나 분산 시스템에서는 Histogram이 권장됩니다.

</details>

---

5. 메트릭 네이밍 규칙으로 권장되지 않는 것은?
   - A) snake_case 사용
   - B) 단위를 접미사로 포함 (_seconds, _bytes)
   - C) camelCase 사용
   - D) 애플리케이션/도메인 접두사 사용

<details>
<summary>정답 보기</summary>

**정답: C) camelCase 사용**

**설명:**
Prometheus 스타일의 메트릭 네이밍 규칙에서는 camelCase 대신 snake_case를 사용합니다. 좋은 메트릭 이름은 `http_requests_total`, `http_request_duration_seconds`처럼 소문자와 언더스코어를 사용하고, 단위를 접미사로 포함하며, 애플리케이션/도메인 접두사를 사용합니다.

</details>

---

6. Prometheus의 장기 저장소로 별도 솔루션이 필요한 이유로 적절하지 않은 것은?
   - A) 압축률이 낮아 디스크 사용량이 증가한다
   - B) 단일 노드 아키텍처로 확장에 제한이 있다
   - C) PromQL이 복잡한 쿼리를 지원하지 않는다
   - D) 네이티브 HA 클러스터링을 지원하지 않는다

<details>
<summary>정답 보기</summary>

**정답: C) PromQL이 복잡한 쿼리를 지원하지 않는다**

**설명:**
PromQL은 매우 강력한 쿼리 언어로, 복잡한 쿼리도 지원합니다. Prometheus가 장기 저장소로 적합하지 않은 이유는 상대적으로 낮은 압축률, 단일 노드 아키텍처의 확장 제한, 네이티브 HA 클러스터링 미지원, 장기간 데이터에 대한 쿼리 속도 저하 등입니다.

</details>

---

7. 다음 솔루션 비교 중 올바르지 않은 것은?
   - A) VictoriaMetrics는 Prometheus보다 높은 압축률을 제공한다
   - B) CloudWatch는 완전 관리형 서비스이다
   - C) Mimir는 로컬 디스크만 지원한다
   - D) Datadog은 SaaS 모델로 제공된다

<details>
<summary>정답 보기</summary>

**정답: C) Mimir는 로컬 디스크만 지원한다**

**설명:**
Grafana Mimir는 객체 스토리지(S3, GCS, Azure Blob 등)를 필수로 사용하는 분산 메트릭 저장소입니다. 로컬 디스크가 아닌 클라우드 객체 스토리지를 활용하여 무제한 확장성과 장기 보존을 제공합니다. VictoriaMetrics는 로컬 디스크와 객체 스토리지 모두 지원합니다.

</details>

---

8. 높은 카디널리티 문제를 방지하기 위한 방법으로 적절하지 않은 것은?
   - A) 사용자 ID를 메트릭 레이블로 사용하지 않는다
   - B) 요청 ID를 메트릭 레이블로 사용하지 않는다
   - C) HTTP 상태 코드를 그룹화한다 (200 → 2xx)
   - D) 모든 레이블 값을 고유하게 유지한다

<details>
<summary>정답 보기</summary>

**정답: D) 모든 레이블 값을 고유하게 유지한다**

**설명:**
높은 카디널리티를 방지하려면 레이블 값이 무한히 증가하지 않도록 해야 합니다. 사용자 ID, 요청 ID, 세션 ID 등 무한히 증가할 수 있는 값은 레이블로 사용하지 않아야 하고, HTTP 상태 코드는 그룹화(200 → 2xx), URL 경로는 정규화(/users/123 → /users/{id})하는 것이 좋습니다.

</details>

---

9. Kubernetes 환경에서 주요 메트릭 소스와 역할의 연결이 올바른 것은?
   - A) node-exporter - Kubernetes 객체 상태 메트릭
   - B) kube-state-metrics - 노드 수준 하드웨어 메트릭
   - C) cAdvisor - 컨테이너별 리소스 메트릭
   - D) metrics-server - 장기 메트릭 저장

<details>
<summary>정답 보기</summary>

**정답: C) cAdvisor - 컨테이너별 리소스 메트릭**

**설명:**
cAdvisor(Container Advisor)는 컨테이너별 CPU, 메모리, I/O 등의 리소스 메트릭을 수집합니다. node-exporter는 노드 수준의 하드웨어/OS 메트릭, kube-state-metrics는 Kubernetes API 객체(Pod, Deployment, Node 등)의 상태 메트릭, metrics-server는 HPA/VPA용 실시간 리소스 메트릭을 제공합니다.

</details>

---

10. 메트릭 솔루션 선택 시 고려사항으로 적절하지 않은 것은?
    - A) 팀의 운영 역량과 규모
    - B) 멀티클라우드 요구사항
    - C) 비용 구조와 예산
    - D) 메트릭 이름의 길이

<details>
<summary>정답 보기</summary>

**정답: D) 메트릭 이름의 길이**

**설명:**
메트릭 솔루션 선택 시 팀의 운영 역량, 멀티클라우드 요구사항, 비용 구조, 확장성 요구사항, 기존 에코시스템과의 통합 등을 고려해야 합니다. 메트릭 이름의 길이는 솔루션 선택에 영향을 미치지 않습니다. 대신 카디널리티, 데이터 보존 기간, 쿼리 성능 등이 중요한 고려사항입니다.

</details>
