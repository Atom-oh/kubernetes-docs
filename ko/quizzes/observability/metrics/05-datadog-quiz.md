# Datadog 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

1. Datadog SaaS를 사용해도 팀에 남는 책임은?

   - A) Agent 설치 후에는 없음
   - B) Dashboard 색상 선택만
   - C) Collector·identity·계측·데이터 처리·monitor·비용
   - D) Datadog 물리 DB server

<details>
<summary>정답 보기</summary>

**정답: C**

SaaS가 backend를 관리합니다. APM·profiling·log 등은 entitlement/과금이 다르며 Agent 설치만으로 모두 포함되지는 않습니다.

</details>

2. Credential/integration에 대한 올바른 설명은?

   - A) 기본 Agent 수집에는 API key가 필요하고 application key/AWS role은 추가 기능별로 구성
   - B) 모든 Agent에 application key와 광범위 AWS 조회 role이 필요
   - C) IRSA만 붙이면 SaaS AWS integration이 자동 구성
   - D) 추측한 SA 이름이면 충분

<details>
<summary>정답 보기</summary>

**정답: A**

External metrics provider에는 추가 API 권한/key가 필요합니다. SaaS AWS integration은 cross-account role/external ID를 사용하며 실제 Agent SA를 확인해야 합니다.

</details>

3. admission.datadoghq.com/enabled=true만으로 APM SDK 주입이 증명되나요?

   - A) 모든 언어/버전을 자동 포함하므로 예
   - B) 아니요. SDK annotation/SSI target을 설정하고 새 Pod와 실제 trace를 확인
   - C) Cluster Agent namespace에서도 항상 예
   - D) Trace socket만 있으면 예

<details>
<summary>정답 보기</summary>

**정답: B**

Mutation/연결 설정과 library 주입은 다릅니다. 현재 local injection은 kube-system과 Cluster Agent namespace를 제외하며 library/runtime/mount/security 호환성도 필요합니다.

</details>

4. Application Pod가 node DogStatsD Agent에 연결하는 방법은?

   - A) 항상 application localhost 사용
   - B) 모든 UDP packet에 API key 삽입
   - C) 무관한 ConfigMap 생성
   - D) Mount한 Linux UDS directory 등 실제 접근 가능한 endpoint 사용

<details>
<summary>정답 보기</summary>

**정답: D**

Application localhost는 node Agent가 아닙니다. UDS 경로·권한·SDK 인자 형식을 맞추고 datagram 전달을 SaaS 수집 확인이나 exactly-once ledger로 취급하지 않습니다.

</details>

5. 올바른 지표 해석은?

   - A) kubernetes.cpu.usage.total은 percent
   - B) Legacy 목록에 없으면 모두 제거된 지표
   - C) kubernetes.cpu.usage.total은 nanocore이며 Kubelet restart는 누적 gauge
   - D) 반복 restart sample 합이 새 restart 횟수

<details>
<summary>정답 보기</summary>

**정답: C**

system.cpu.idle은 percent입니다. Kubelet/State Core 목록과 tag를 구분합니다. 예제 restart monitor는 total이며 최근 증가량은 reset을 고려해 검증해야 합니다.

</details>

6. .as_count() 오류 비율 경로가 계산하는 것은?

   - A) 시간 집계한 error/total count의 비율
   - B) 각 time-bucket 비율의 합
   - C) 전체 p95
   - D) 무트래픽의 자동 100% 성공

<details>
<summary>정답 보기</summary>

**정답: A**

Sum aggregation과 같은 grouping을 사용합니다. Helper는 good/error 0도 발행하지만 무트래픽·누락·오류 없는 traffic은 여전히 다른 상태입니다.

</details>

7. OpenMetrics/log 설정에 대한 올바른 설명은?

   - A) 모든 ConfigMap은 자동 mount됨
   - B) Container annotation/current check field를 맞추고 Logs Grok는 match_rules/support_rules 사용
   - C) Chart root prometheus.enabled가 전부 구성
   - D) Grok camelCase와 snake_case는 동일

<details>
<summary>정답 보기</summary>

**정답: B**

현재 OpenMetrics check는 openmetrics_endpoint를 사용합니다. datadog.confd는 chart가 mount하며 독립 ConfigMap은 자동 설치되지 않습니다. Schema 검증은 실제 scrape/Grok parsing과 다릅니다.

</details>

8. 수동 trace-log correlation에서 보존할 것은?

   - A) dd.trace_id만 남기고 다른 MDC field 삭제
   - B) 128-bit ID를 임의 정수로 변환
   - C) 고정된 성공 trace ID
   - D) 기존 caller MDC context와 문자열 ID, 실제 계측/데이터 조건

<details>
<summary>정답 보기</summary>

**정답: D**

Helper는 application 오류가 나도 기존 context를 복원하며 동기 범위입니다. 자동 주입/parsing·service tag·실제 trace 존재도 별도로 확인합니다.

</details>

9. Service 50개를 APM host 50개로 계산하면 무엇이 문제인가요?

   - A) APM은 항상 무료
   - B) Log 수집료가 log 전체 비용
   - C) Service와 billable host 단위가 다르며 계약 포함량/사용량을 계산해야 함
   - D) 모든 cluster는 host 1개

<details>
<summary>정답 보기</summary>

**정답: C**

기존 예시는 측정 청구액이 아닙니다. Indexing/retention·span 포함량·custom metric·다른 상품도 계산합니다. nonLocalTraffic은 접근 범위이지 비용 quota가 아닙니다.

</details>

10. 올바른 Watchdog/SLO/진단 운영은?

   - A) Watchdog insight가 있으면 paging 전달이 증명됨
   - B) SLO 모델/good-total 정책을 맞추고 routing을 시험하며 로컬 진단 bundle을 공유 전 검토
   - C) 로컬 flare 생성이 upload 승인을 뜻함
   - D) Trace가 없으면 모든 DD_ env 값 출력

<details>
<summary>정답 보기</summary>

**정답: B**

Metric/monitor/time-slice SLO를 지원합니다. Notification/no-data를 검증하고 env dump의 key 노출을 피합니다. --local은 우선 로컬에서 flare를 수집합니다.

</details>

---

[학습 자료로 돌아가기](../../../observability/metrics/05-datadog.md)
