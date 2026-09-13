# Prometheus 퀴즈

> 검토: 2026-09-12

1. Prometheus의 일반적인 메트릭 수집 경로는 무엇인가요?

   - A) 애플리케이션이 모든 샘플을 직접 push해야 한다
   - B) Prometheus가 설정한 대상을 HTTP로 scrape한다
   - C) 스트리밍 이벤트 로그만 사용한다
   - D) CSV 파일만 주기적으로 가져온다

<details>
<summary>정답 보기</summary>

**정답: B**

기본 경로는 pull/scrape입니다. Remote write·선택적 배치 통합은 다른 전달 경로를 추가합니다. up은 scrape 성공이며 애플리케이션의 전체 가용성을 증명하지 않습니다.

</details>

2. Counter의 최근 5분 평균 초당 변화율을 계산하는 식은 무엇인가요?

   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>정답 보기</summary>

**정답: B**

rate()는 range vector를 사용해 관측한 리셋·외삽을 처리합니다. increase()는 초당 변화율이 아니라 총 증가량 추정입니다. 집계 전에 rate를 적용하며 놓친 모든 증가량이 복원된다고 해석하지 않습니다.

</details>

3. 정상적으로 동작할 ServiceMonitor는 무엇을 설명해야 하나요?

   - A) Grafana 대시보드
   - B) Prometheus container image만
   - C) Prometheus 설정과 selector·port 이름이 일치하는 대상 Service와 scrape endpoint
   - D) 완전한 애플리케이션 Deployment

<details>
<summary>정답 보기</summary>

**정답: C**

Prometheus가 먼저 monitor의 namespace·레이블을 선택하고 monitor가 Service를 선택합니다. Endpoint port는 Service port 이름입니다. RBAC·TLS/네트워크·계측한 애플리케이션도 필요합니다.

</details>

4. Classic histogram에서 histogram_quantile()이 반환하는 값은 무엇인가요?

   - A) 정확한 Summary 분위수
   - B) 버킷 기반 분위수 추정값
   - C) 버킷 해상도와 무관한 정확한 분위수
   - D) Counter의 요청 변화율

<details>
<summary>정답 보기</summary>

**정답: B**

호환되는 classic 버킷을 합칠 때 le를 유지합니다. 결과는 버킷 내부 보간값입니다. Summary 분위수에도 알고리즘·시간 구간에 따른 오차가 있으며 평균으로 전체 분위수를 만들 수 없습니다.

</details>

5. kube-prometheus-stack 패키지에 포함되지 않는 것은 무엇인가요?

   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>정답 보기</summary>

**정답: C**

차트는 활성 values에 따라 Prometheus·Alertmanager·Operator·Grafana·exporter를 제공합니다. VictoriaMetrics는 별도 배포입니다. 임의의 이미지 버전을 혼합하기보다 확인한 차트 조합을 고정합니다.

</details>

6. Remote write의 용도는 무엇인가요?

   - A) Alertmanager 알림 전송
   - B) 설정한 외부 수신기에 샘플을 비동기로 전달
   - C) 무제한 장애 버퍼 보장
   - D) Grafana 대시보드 동기화

<details>
<summary>정답 보기</summary>

**정답: B**

AMP·VictoriaMetrics·Mimir 등 수신기는 각각의 endpoint·identity·쿼터·HA 계약을 가집니다. WAL 버퍼는 유한합니다. Local Prometheus 보존 기간도 설정 가능하며 보편적으로 30일에 제한되는 것은 아닙니다.

</details>

7. Alert rule의 for 시간은 무엇을 제어하나요?

   - A) 메트릭 보존 기간
   - B) 같은 조건·레이블 집합이 firing 전에 pending으로 유지되는 시간
   - C) Alertmanager 재전송 주기
   - D) Prometheus 복제본 수

<details>
<summary>정답 보기</summary>

**정답: B**

해당 alert 식별자가 평가마다 조건을 계속 충족해야 합니다. 데이터 누락·레이블 변경은 pending을 끊을 수 있습니다. Notification 그룹화·시간은 별도의 Alertmanager 설정입니다.

</details>

8. predict_linear()를 어떻게 해석해야 하나요?

   - A) 보장된 디스크 장애 시각
   - B) Gauge의 선형 추세를 미래로 외삽한 값
   - C) 계절성 triple-exponential 예측
   - D) 모든 용량 측정을 대신하는 값

<details>
<summary>정답 보기</summary>

**정답: B**

관측한 선형 추세를 투영합니다. 부하 변화·정리 작업·희소 데이터·비선형 동작에 따라 맞지 않을 수 있습니다. Prometheus 3의 옛 holt_winters 대체 함수는 명시적인 실험적 double-exponential 평활화이며 계절성 모델이 아닙니다.

</details>

9. AlertmanagerConfig의 groupBy는 무엇을 하나요?

   - A) 모든 namespace의 alert를 자동 승인
   - B) 선택한 레이블로 notification 그룹화
   - C) Prometheus for 시간 정의
   - D) 일치하는 모든 형제 route 실행

<details>
<summary>정답 보기</summary>

**정답: B**

groupBy는 native 설정의 group_by가 됩니다. Continue를 설정하지 않으면 보통 첫 형제 route 일치에서 멈춥니다. Inhibition은 다른 서비스·노드 warning을 억제하지 않도록 의미 있는 자원 식별 equal 레이블이 필요합니다.

</details>

10. TSDB의 WAL이 제공하는 것은 무엇인가요?

   - A) 쿼리 결과 캐시
   - B) Block에 저장하기 전 비정상 종료 복구를 돕는 순차 기록
   - C) 볼륨을 잃어도 보존되는 백업
   - D) 무제한 remote-write 전송 queue

<details>
<summary>정답 보기</summary>

**정답: B**

WAL replay는 내구성 장치이지 손상·볼륨 장애·긴 원격 장애에서 무손실을 보장하지 않습니다. Retention과 WAL·head·compaction 디스크 요구도 구분해야 하며 검증한 백업·복구 절차를 보존합니다.

</details>

[학습 자료로 돌아가기](../../../observability/metrics/01-prometheus.md)
