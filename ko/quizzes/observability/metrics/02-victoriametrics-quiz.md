# VictoriaMetrics 퀴즈

VictoriaMetrics에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. VictoriaMetrics의 Prometheus 대비 주요 장점으로 올바르지 않은 것은?
   - A) 최대 7배 더 효율적인 데이터 압축
   - B) 복잡한 쿼리에서 최대 20배 빠른 성능
   - C) 별도의 쿼리 언어 학습 필요
   - D) 수평적 확장 가능

<details>
<summary>정답 보기</summary>

**정답: C) 별도의 쿼리 언어 학습 필요**

**설명:**
VictoriaMetrics는 MetricsQL이라는 쿼리 언어를 사용하지만, 이는 PromQL의 상위 호환(superset)입니다. 기존 PromQL 쿼리가 모두 동작하며, 추가적인 편의 기능만 제공합니다. 따라서 별도의 쿼리 언어를 학습할 필요가 없습니다.

</details>

---

2. VictoriaMetrics 클러스터 모드의 구성 요소가 아닌 것은?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) vmoperator

<details>
<summary>정답 보기</summary>

**정답: D) vmoperator**

**설명:**
VictoriaMetrics 클러스터 모드는 세 가지 핵심 구성 요소로 이루어집니다: vminsert(쓰기 요청 라우팅), vmstorage(데이터 저장), vmselect(쿼리 처리). vmoperator는 별도의 Kubernetes Operator로, 클러스터 모드의 핵심 구성 요소가 아닙니다.

</details>

---

3. vmagent의 주요 역할은?
   - A) 데이터 장기 저장
   - B) 대시보드 렌더링
   - C) 메트릭 수집 및 Remote Write 전송
   - D) 알림 라우팅

<details>
<summary>정답 보기</summary>

**정답: C) 메트릭 수집 및 Remote Write 전송**

**설명:**
vmagent는 메트릭을 수집하고 VictoriaMetrics나 다른 원격 저장소로 전송하는 경량 에이전트입니다. Prometheus scrape 설정과 호환되며, 데이터 버퍼링, 재전송, 레이블 재작성 등의 기능을 제공합니다.

</details>

---

4. MetricsQL에서 `keep_last_value()` 함수의 용도는?
   - A) 최대값 유지
   - B) 마지막 값 유지 (갭 채우기)
   - C) 첫 번째 값 유지
   - D) 평균값 유지

<details>
<summary>정답 보기</summary>

**정답: B) 마지막 값 유지 (갭 채우기)**

**설명:**
`keep_last_value()`는 MetricsQL의 확장 함수로, 시계열 데이터에서 누락된 값(갭)을 마지막으로 알려진 값으로 채웁니다. 스크랩 실패나 일시적인 데이터 누락이 있을 때 대시보드나 알림에서 갭을 방지하는 데 유용합니다.

</details>

---

5. VictoriaMetrics에서 `--dedup.minScrapeInterval` 플래그의 역할은?
   - A) 최소 스크랩 간격 설정
   - B) 지정된 간격 내 중복 샘플 제거
   - C) 데이터 압축 간격 설정
   - D) 알림 평가 간격 설정

<details>
<summary>정답 보기</summary>

**정답: B) 지정된 간격 내 중복 샘플 제거**

**설명:**
`--dedup.minScrapeInterval`은 지정된 시간 간격 내에서 동일한 시계열의 중복 샘플을 제거합니다. 예를 들어, `--dedup.minScrapeInterval=30s`는 30초 내의 중복 데이터 포인트를 하나로 병합합니다. HA 구성에서 여러 Prometheus가 동일한 대상을 스크랩할 때 유용합니다.

</details>

---

6. vmsingle과 vmcluster 선택 기준으로 올바른 것은?
   - A) 항상 vmcluster를 사용해야 한다
   - B) 일일 100M 샘플 이하이고 고가용성이 필요 없으면 vmsingle 권장
   - C) vmsingle은 쿼리 기능을 지원하지 않는다
   - D) vmcluster는 단일 노드에서만 동작한다

<details>
<summary>정답 보기</summary>

**정답: B) 일일 100M 샘플 이하이고 고가용성이 필요 없으면 vmsingle 권장**

**설명:**
vmsingle(단일 노드 모드)은 설정이 간단하고 소규모~중규모 환경에 적합합니다. 일일 100M 샘플 이하이고 고가용성이 필수가 아닌 경우 vmsingle이 권장됩니다. 대규모 환경이나 고가용성이 필요한 경우 vmcluster를 사용합니다.

</details>

---

7. VictoriaMetrics 클러스터에서 `replicationFactor=2` 설정의 의미는?
   - A) 2개의 스토리지 노드만 사용
   - B) 각 데이터 포인트를 2개의 스토리지 노드에 복제
   - C) 쿼리를 2개 노드에서만 실행
   - D) 2배 압축 적용

<details>
<summary>정답 보기</summary>

**정답: B) 각 데이터 포인트를 2개의 스토리지 노드에 복제**

**설명:**
`replicationFactor=2`는 vminsert가 각 데이터 포인트를 2개의 vmstorage 노드에 복제하도록 설정합니다. 이를 통해 하나의 스토리지 노드가 실패해도 데이터 손실 없이 서비스를 지속할 수 있습니다. 고가용성을 위해 권장되는 설정입니다.

</details>

---

8. MetricsQL의 `default` 연산자의 용도는?
   - A) 기본 레이블 설정
   - B) 결과가 없을 때 기본값 반환
   - C) 기본 집계 함수 설정
   - D) 기본 시간 범위 설정

<details>
<summary>정답 보기</summary>

**정답: B) 결과가 없을 때 기본값 반환**

**설명:**
MetricsQL의 `default` 연산자는 쿼리 결과가 없거나 NaN일 때 기본값을 반환합니다. 예를 들어, `rate(http_requests_total[5m]) / rate(http_requests_total[5m]) default 0`은 0으로 나누기 오류 대신 0을 반환합니다. PromQL에서는 이런 처리를 위해 복잡한 조건문이 필요합니다.

</details>

---

9. vmalert의 역할로 올바른 것은?
   - A) 메트릭 수집
   - B) 데이터 저장
   - C) 알림 규칙 평가 및 알림 생성
   - D) 대시보드 생성

<details>
<summary>정답 보기</summary>

**정답: C) 알림 규칙 평가 및 알림 생성**

**설명:**
vmalert는 Prometheus의 알림 기능과 유사하게 알림 규칙을 평가하고, 조건이 충족되면 Alertmanager로 알림을 전송합니다. VictoriaMetrics나 Prometheus를 데이터 소스로 사용할 수 있으며, 기록 규칙(recording rules)도 지원합니다.

</details>

---

10. VictoriaMetrics에서 vmbackup의 주요 용도는?
    - A) 실시간 데이터 복제
    - B) 객체 스토리지로 백업 생성
    - C) 로그 백업
    - D) 설정 파일 백업

<details>
<summary>정답 보기</summary>

**정답: B) 객체 스토리지로 백업 생성**

**설명:**
vmbackup은 VictoriaMetrics 데이터를 S3, GCS, Azure Blob 등의 객체 스토리지로 백업하는 도구입니다. 스냅샷 기능을 활용하여 일관된 백업을 생성하며, vmrestore를 사용하여 복원할 수 있습니다. 재해 복구 및 데이터 보호를 위해 필수적인 도구입니다.

</details>
