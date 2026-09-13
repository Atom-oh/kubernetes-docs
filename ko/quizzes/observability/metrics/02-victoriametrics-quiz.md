# VictoriaMetrics 퀴즈

> 검토 기준: VictoriaMetrics 1.151.0 · stack chart 0.92.1

1. Prometheus 쿼리를 VictoriaMetrics로 옮길 때 정확한 설명은?
   - A) 모든 workload의 압축률이 정확히 7배 개선된다
   - B) 모든 설치의 series 한도는 100M으로 고정된다
   - C) MetricsQL에 의도적인 차이가 있으므로 실제 query 결과를 대조한다
   - D) Prometheus는 15일보다 오래 보존할 수 없다

<details>
<summary>정답 보기</summary>

**정답: C**

익숙한 구문이 rate/increase·NaN·scalar·API의 동일한 동작을 보장하지 않습니다. Benchmark에는 실제 version·data·hardware가 필요하며 기본 retention은 최대값이 아닙니다.

</details>

---

2. Cluster의 storage/query data plane 구성 요소가 아닌 것은?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) VictoriaMetrics Operator

<details>
<summary>정답 보기</summary>

**정답: D**

vminsert는 쓰기를 라우팅하고 vmstorage는 저장하며 vmselect는 조회합니다. Operator는 Kubernetes resource를 조정하는 별도 제어 구성 요소입니다.

</details>

---

3. vmagent의 역할은?
   - A) 모든 영속 저장소를 대체
   - B) Dashboard 렌더링
   - C) Metric 수집과 remote-write 목적지 전송
   - D) Alertmanager 알림 routing 대체

<details>
<summary>정답 보기</summary>

**정답: C**

Queue로 장애 구간을 buffer하지만 유한합니다. 설정한 disk 한도에서는 오래된 데이터가 삭제되고 emptyDir은 Pod 교체 시 사라집니다. 영속 저장과 감시를 따로 설계합니다.

</details>

---

4. keep_last_value(q)의 동작과 주의점은?
   - A) 저장된 최대값 반환
   - B) 평가 결과의 gap을 이전 값으로 채워 telemetry 누락을 숨길 수 있음
   - C) 손실된 scrape sample 전체 복원
   - D) 가용성 alert가 정상임을 보장

<details>
<summary>정답 보기</summary>

**정답: B**

Gap을 채운 의미가 의도한 것인지 확인합니다. 과거 정상값 유지로 수집 누락을 숨길 수 있으므로 누락을 별도로 감시합니다.

</details>

---

5. dedup.minScrapeInterval은 무엇을 제어하나요?
   - A) Target scraper의 실행 간격
   - B) 같은 series의 시간 구간마다 sample 하나 유지
   - C) 무손실 일반 압축
   - D) Alert 평가 주기

<details>
<summary>정답 보기</summary>

**정답: B**

완전히 같은 복사본뿐 아니라 유효한 고해상도 sample도 제거할 수 있습니다. Vmstorage/vmselect 설정과 storage/scraper 복제 설계를 일치시킵니다.

</details>

---

6. 단일 노드와 cluster mode를 어떻게 선택하나요?
   - A) 항상 cluster 선택
   - B) 부하·활성 series/churn·query·retention·복구 요구를 측정
   - C) 100M samples/day를 보편적 임계값으로 사용
   - D) 단일 노드에는 query API가 없음

<details>
<summary>정답 보기</summary>

**정답: B**

한 서버의 용량과 insert/storage/select 독립 확장 비용을 평가합니다. 복제 storage나 프로세스 두 개만으로 검증된 서비스 HA가 완성되지 않습니다.

</details>

---

7. vminsert replicationFactor=2는 무엇을 요청하나요?
   - A) Storage member 총수를 정확히 2개로 제한
   - B) 서로 다른 storage member에 복사본 두 개를 요청하되 실제 가용성과 이력을 확인
   - C) 정확히 두 member만 조회
   - D) 두 배 압축

<details>
<summary>정답 보기</summary>

**정답: B**

Storage 하나의 장애 중에도 복사본 두 개를 유지하려면 최소 3개와 필요한 capacity·failure-domain 조건이 필요합니다. Vmselect/dedup을 일치시키며 flag가 과거 데이터를 복제하거나 복제본 부족 쓰기의 무손실·backup을 보장하지는 않습니다.

</details>

---

8. MetricsQL default 연산자의 범위는?
   - A) 항상 올바른 service label을 생성
   - B) 우변으로 누락 point를 채우며 누락이 자동으로 무트래픽을 뜻하지는 않음
   - C) 모든 ratio에 의미가 있음을 보장
   - D) Metric 수집 간격을 변경

<details>
<summary>정답 보기</summary>

**정답: B**

오류율 뒤에 무조건 default 0을 붙이지 않습니다. Status label을 일관되게 집계하고 알려진 분모 series에만 누락 분자 0을 채우며 무트래픽은 제외합니다. Native fixture의 정상·전체 실패·10% 실패 값은 0·1·0.1이고 누락·무트래픽 service는 값이 없습니다.

</details>

---

9. vmalert의 책임은?
   - A) 모든 application metric 수집
   - B) 장기 sample 전체 저장
   - C) Alert/recording rule 평가와 설정된 notifier로 알림 전달
   - D) Grafana dashboard 렌더링

<details>
<summary>정답 보기</summary>

**정답: C**

Rule 입력/exporter·datasource URL·state 보존·notifier/routing이 준비돼야 합니다. 높은 restart 횟수만으로 CrashLoopBackOff를 증명하지 못하며 파생 series 기록이 raw 데이터의 압축·삭제를 수행하지도 않습니다.

</details>

---

10. 올바른 vmbackup 흐름은?
   - A) vminsert 설정만 백업
   - B) 같은 storage directory의 snapshot을 읽고 독립 backup 목적지를 보호
   - C) 어떤 RWO PVC든 아무 node에서 확인 없이 mount
   - D) Storage 복제를 완전한 backup으로 간주

<details>
<summary>정답 보기</summary>

**정답: B**

모든 vmstorage member를 별도 prefix에 또는 의도한 단일 노드 저장소를 백업합니다. S3/GCS/Azure/local 목적지를 지원합니다. 동일 위치·PVC 식별·workload credential·보존·실제 복원을 확인하며 로컬 snapshot 자체는 독립 복사본이 아닙니다.

</details>

---

[학습 자료로 돌아가기](../../../observability/metrics/02-victoriametrics.md)
