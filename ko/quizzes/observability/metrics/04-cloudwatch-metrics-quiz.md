# CloudWatch Metrics 퀴즈

2026-09-13 가이드의 수집 모델과 검증 범위를 기준으로 답하세요.

1. 관리형 CloudWatch backend가 팀의 책임에서 없애는 것은 무엇인가요?

   - A) 모든 수집·IAM 작업
   - B) AWS backend 운영이며 collector·identity·retention·대응 책임은 남음
   - C) 모든 network 전제
   - D) 모든 조회·log 비용

<details>
<summary>정답 보기</summary>

**정답: B**

기존·enhanced·OTel은 이름과 과금 모델이 다릅니다. 관리형 저장소가 운영 업무 0을 뜻하지 않습니다.

</details>

2. EKS 설치에 대한 올바른 설명은 무엇인가요?

   - A) update-cluster-logging이 Container Insights를 설치함
   - B) 모든 플랫폼이 같은 host DaemonSet을 실행함
   - C) 호환 add-on 또는 소유권이 정해진 Helm 설치를 선택하고 플랫폼·identity 전제를 확인함
   - D) Helm 6.6.0이 반드시 EKS add-on 버전임

<details>
<summary>정답 보기</summary>

**정답: C**

Control-plane logging은 별도입니다. Fargate에는 이 host DaemonSet을 쓰지 못하며 Auto Mode/혼합 compute도 호환성을 확인합니다. Pod Identity/IRSA 구성이 필요합니다.

</details>

3. SEARCH 결과에서 상위 10개 dashboard view를 만드는 것은 무엇인가요?

   - A) SEARCH만 쓰면 항상 10개로 제한됨
   - B) SLICE(SORT(SEARCH(...), AVG, DESC), 0, 10)
   - C) PERCENTILE(SEARCH(...), 10)
   - D) SEARCH 배열을 직접 일반 alarm으로 사용

<details>
<summary>정답 보기</summary>

**정답: B**

SEARCH는 matching series를 반환하므로 명시적으로 정렬·제한합니다. 평가는 조회 구간 기준이며 SEARCH는 직접 alarm으로 쓸 수 없습니다.

</details>

4. Percentile과 비율의 올바른 설명은 무엇인가요?

   - A) PERCENTILE(METRICS(),95)가 전체 request p95를 계산함
   - B) 무트래픽이면 항상 정상 오류율 0임
   - C) AVG(METRICS()) PERIOD(300)이 moving average임
   - D) 지원되는 p95 statistic을 쓰고 count 비율은 무트래픽·telemetry 누락을 구분함

<details>
<summary>정답 보기</summary>

**정답: D**

ALB count는 Sum과 IF(m2>0,100*m1/m2)를 사용합니다. CloudWatch 산술은 누락값을 0으로 처리하고 0 나눗셈 결과를 버립니다. Service p95만으로 전체 p95를 복원할 수 없습니다.

</details>

5. ADOT/EMF declaration이 사용하는 dimension에 필요한 것은 무엇인가요?

   - A) Discovery/relabel 또는 application이 실제 제공한 label과 값
   - B) Exporter config의 dimension 이름만
   - C) 모든 label의 secret access key
   - D) 모든 node replica가 모든 Pod를 scrape

<details>
<summary>정답 보기</summary>

**정답: A**

awsemf는 기존 지표 추출용 log event를 보냅니다. 예제는 ClusterName/Namespace/Service를 생성하고 gauge를 사용합니다. 직접 OTLP 경로는 다른 선택입니다.

</details>

6. 이 가이드에서 안전하지 않거나 호환되지 않는 비용 조치는 무엇인가요?

   - A) 수집·조회 사용량 측정
   - B) 소유 log group 하나에 승인된 retention 설정
   - C) EMF/Container Insights log를 Infrequent Access로 옮기고 무기한 log group 전체의 보존기간 단축
   - D) 중복 scrape와 불필요한 label 검토

<details>
<summary>정답 보기</summary>

**정답: C**

Infrequent Access는 EMF/Container Insights 수집을 지원하지 않습니다. Retention 단축은 기존 기록을 만료시킬 수 있습니다. 고해상도는 request/alarm 비용 요인이지 보편적 10배 저장 단가가 아닙니다.

</details>

7. PutMetricData helper에 대한 올바른 설명은 무엇인가요?

   - A) IAM을 자동 생성함
   - B) Caller가 준 client와 UTC timestamp를 사용하고 오류를 caller로 전달함
   - C) 재시도가 exactly-once business count를 보장함
   - D) 모든 aggregate dimension set이 자동 생성됨

<details>
<summary>정답 보기</summary>

**정답: B**

전체 dimension set이 custom metric을 식별합니다. Idempotency token이 없어 응답 불명확 재시도는 sample을 중복시킬 수 있습니다. 예제는 구간 count를 Sum으로 조회합니다.

</details>

8. 기존 지표 dimension과 OTel label은 어떻게 다른가요?

   - A) 둘 다 언제나 무제한
   - B) 150 label이 PutMetricData 한도를 대체함
   - C) 기존 지표는 30 dimension, 문서화된 OTel 모델은 최대 150 label
   - D) Label은 payload 비용·공개 범위에 영향이 없음

<details>
<summary>정답 보기</summary>

**정답: C**

서로 다른 수집 모델입니다. Label은 payload와 metadata 공개 범위를 늘리며 이름의 개수만으로 cardinality를 측정할 수 없습니다.

</details>

9. 올바른 지표 해석은 무엇인가요?

   - A) node_network_total_bytes는 bytes/second이며 namespace_number_of_running_pods는 Pod 수임
   - B) cluster_cpu_utilization이 표준 발행 지표임
   - C) 실행 container 수는 항상 Pod 수와 같음
   - D) 모든 reserved-capacity 지표가 enhanced 전용임

<details>
<summary>정답 보기</summary>

**정답: A**

실제 목록과 dimension을 확인합니다. Pod CPU/memory 사용률의 분모가 node limit일 수 있습니다. Enhanced는 지표·dimension을 추가하고 별도 과금 모델을 사용합니다.

</details>

10. Anomaly 또는 restart alarm에서 확인할 것은 무엇인가요?

   - A) Alarm 생성만으로 실제 telemetry가 증명됨
   - B) Restart total은 언제나 구간 증가량임
   - C) 관측 anomaly series의 ReturnData를 무조건 제거함
   - D) 이력·정확한 identity·total/delta 의미·누락 데이터·알림 전달

<details>
<summary>정답 보기</summary>

**정답: D**

ANOMALY_DETECTION_BAND는 학습한 기대 범위입니다. 문서화된 형태에서는 관측 series와 band를 모두 반환할 수 있습니다. PodName/Namespace/ClusterName restart total은 자동으로 5분간 새 재시작 5회를 뜻하지 않습니다.

</details>

---

[학습 자료로 돌아가기](../../../observability/metrics/04-cloudwatch-metrics.md)
