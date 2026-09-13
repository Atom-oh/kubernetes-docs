# 메트릭 개요 퀴즈

> 검토: 2026-09-12

1. 리셋될 수 있는 누적 횟수를 표현하는 유형은 무엇인가요?

   - A) Gauge
   - B) Counter
   - C) 미리 계산한 p99
   - D) Scrape timestamp

<details>
<summary>정답 보기</summary>

**정답: B**

Counter는 음수가 아닌 증가량을 누적합니다. 측정하는 상태가 다시 만들어지면 리셋될 수 있습니다. rate()는 관측한 리셋을 처리하지만 관측하지 못한 증가량까지 복원하지는 않습니다.

</details>

2. 메서드 5개, 경로 20개, 상태 코드 10개는 무엇을 의미하나요?

   - A) 모든 배포에서 저장 시계열이 정확히 1,000개이다
   - B) 모든 조합이 가능할 때 애플리케이션 레이블 조합은 최대 1,000개이다
   - C) 하루 샘플이 정확히 1,000개이다
   - D) 자원 사용량에는 영향이 없다

<details>
<summary>정답 보기</summary>

**정답: B**

곱셈 결과는 상한입니다. 실제 발생 조합, 대상·복제본 레이블, Histogram 버킷, 과거 시계열 churn이 실제 시계열 수와 저장량에 영향을 줍니다.

</details>

3. Pushgateway 사용 방식으로 적절한 것은 무엇인가요?

   - A) 모든 짧은 Pod를 HOSTNAME별 그룹으로 만들고 자동 만료를 기다린다
   - B) 적합한 서비스 단위 배치에 안정적인 그룹·성공 시각·명시적인 폐기 정책을 사용한다
   - C) Gateway의 up=1을 모든 배치 성공의 증거로 삼는다
   - D) 배치가 실패해도 성공 시각을 전송한다

<details>
<summary>정답 보기</summary>

**정답: B**

Pushgateway는 모든 짧은 작업의 기본 선택지가 아니며 그룹에 자동 TTL이 없습니다. Scrape 상태와 배치의 최근 성공 여부는 다릅니다. honor_labels는 전송한 작업 식별자를 유지합니다.

</details>

4. Histogram과 Summary에 대한 설명으로 맞는 것은 무엇인가요?

   - A) Summary 분위수는 항상 정확하다
   - B) 인스턴스 p99의 평균이 전체 p99이다
   - C) 호환되는 classic 버킷은 합칠 수 있고, Summary sum/count도 평균 계산을 위해 합칠 수 있다
   - D) Summary의 모든 데이터는 집계할 수 없다

<details>
<summary>정답 보기</summary>

**정답: C**

Classic 버킷은 계측한 생산자에서 집계하고 Prometheus가 조회 시 분위수를 계산합니다. Summary 분위수는 알고리즘·시간 구간에 따른 오차가 있으며 전체 분위수로 집계할 수 없습니다. 반면 음수가 아닌 지연 시간의 sum/count 변화율로 전체 평균을 계산할 수 있습니다.

</details>

5. 새 Prometheus 애플리케이션 메트릭의 권장 관례가 아닌 것은 무엇인가요?

   - A) 의미 있는 접두사 사용
   - B) _seconds, _bytes 같은 단위 접미사 사용
   - C) 일반적인 기본 단위 관례보다 camelCase·밀리초를 우선 사용
   - D) 누적 Counter를 _total로 표시

<details>
<summary>정답 보기</summary>

**정답: C**

의미 있는 언더스코어 구분 이름과 기본 단위를 권장합니다. _total은 Counter 표시이지 물리 단위가 아닙니다. node_memory_MemAvailable_bytes처럼 기존 exporter가 공개한 이름은 유지합니다.

</details>

6. Prometheus 보존 기간에 대해 맞는 설명은 무엇인가요?

   - A) 30일보다 오래 보존할 수 없다
   - B) 시간·용량 보존 설정이 없으면 기본 15일이며, 더 오래 보존하려면 적절한 설정과 용량이 필요하다
   - C) Local 데이터를 압축하지 않는다
   - D) Mimir 없이 독립 수집 복제본을 구성할 수 없다

<details>
<summary>정답 보기</summary>

**정답: B**

기본 보존 기간은 최대값이 아닙니다. Local TSDB는 복제된 분산 저장소가 아니므로 수집 중복성·조회 중복 제거·내구성·복구를 구분해 설계합니다.

</details>

7. 제품·저장소에 대한 주장 중 틀린 것은 무엇인가요?

   - A) VictoriaMetrics single-node와 cluster는 운영 요구가 다르다
   - B) 기존 CloudWatch metrics는 시간이 지나면 해상도가 낮아진다
   - C) Mimir의 object storage가 무제한 확장과 모든 local storage 제거를 보장한다
   - D) Datadog 메트릭 쿼리는 rollup을 적용하므로 보존 기간이 모든 그래프의 최초 해상도를 보장하지는 않는다

<details>
<summary>정답 보기</summary>

**정답: C**

Object storage는 Mimir 구조의 일부일 뿐 무제한 용량 보장이 아닙니다. Ingest/local 자원, query 제한, 복제와 운영 용량이 여전히 중요합니다. 백업 대상이나 edition별 기능도 기본 저장 구조와 구분해야 합니다.

</details>

8. 메트릭 카디널리티를 제어하지 못하는 방법은 무엇인가요?

   - A) 정규화한 경로 template 사용
   - B) 일반 레이블에서 사용자·세션 ID 제외
   - C) 상세 구분을 잃어도 될 때 상태 코드 그룹화
   - D) 매 요청마다 새로운 request_id 레이블 값 부여

<details>
<summary>정답 보기</summary>

**정답: D**

서로 다른 레이블 값은 시계열을 늘리며 값에 hash를 적용해도 개수가 줄지는 않습니다. 필요한 요청 문맥은 적절히 통제한 로그·트레이스로 다룹니다. 카디널리티와 민감 정보 노출을 함께 검토합니다.

</details>

9. Kubernetes 메트릭 역할의 올바른 연결은 무엇인가요?

   - A) node-exporter — Kubernetes API 객체 상태
   - B) kube-state-metrics — 실제 컨테이너 CPU 사용량
   - C) cAdvisor/kubelet 메트릭 — 컨테이너 자원 측정
   - D) metrics-server — 장기 Prometheus TSDB

<details>
<summary>정답 보기</summary>

**정답: C**

node-exporter는 호스트 OS, kube-state-metrics는 API 객체 상태, metrics-server는 Resource Metrics API를 담당합니다. Prometheus/vmalert/Mimir rule이 알림을 평가하고 Alertmanager는 전달합니다. vmagent는 수집·전달기이지 조회 가능한 TSDB가 아닙니다.

</details>

10. 검토 가능한 비용 비교에 필요한 것은 무엇인가요?

   - A) 팀 규모만으로 정한 제품 순위
   - B) 수집 주기·기능 조건이 없는 노드 수
   - C) 측정한 시계열·샘플량, 보존·해상도, HA·조회 요구와 선택한 기능의 최신 단가
   - D) 메트릭 이름과 값의 길이는 절대 중요하지 않다는 가정

<details>
<summary>정답 보기</summary>

**정답: C**

실제 노출 시계열 100만 개를 15초마다 30일간 수집하면 filtering/deduplication 전 1,728억 샘플입니다. 인프라·index/WAL·복제본·조회량·custom metric 제공량·운영 인력에 따라 비용이 달라집니다. 업무량 계산이지 공급자의 견적이 아닙니다.

</details>

[학습 자료로 돌아가기](../../../observability/metrics/README.md)
