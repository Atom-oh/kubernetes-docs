# CloudWatch Logs 퀴즈

Amazon CloudWatch Logs에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. EKS 컨트롤 플레인 로깅에서 지원하는 로그 유형이 아닌 것은?

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>정답 보기</summary>

**정답: C) worker**

**설명:**
EKS 컨트롤 플레인은 api, audit, authenticator, controllerManager, scheduler 5가지 로그 유형을 지원합니다. worker 노드 로그는 컨트롤 플레인 로그가 아니며, Container Insights나 FluentBit을 통해 별도로 수집해야 합니다.

</details>

---

2. CloudWatch Logs의 비용 구조에서 가장 비용이 높은 항목은?

   - A) 저장 (Storage)
   - B) 수집 (Ingestion)
   - C) 쿼리 (Logs Insights)
   - D) S3 내보내기

<details>
<summary>정답 보기</summary>

**정답: B) 수집 (Ingestion)**

**설명:**
CloudWatch Logs 수집 비용은 GB당 $0.50으로, 저장($0.03/GB/월)이나 쿼리($0.005/GB 스캔)보다 훨씬 높습니다. 따라서 불필요한 로그 필터링이 비용 최적화에 중요합니다.

</details>

---

3. CloudWatch Logs Insights에서 특정 필드를 추출하는 명령어는?

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>정답 보기</summary>

**정답: B) parse**

**설명:**
CloudWatch Logs Insights에서 `parse` 명령어를 사용하여 로그 메시지에서 특정 패턴의 필드를 추출합니다. 예: `parse @message '"level":"*"' as level`

</details>

---

4. Container Insights를 통해 수집되는 로그 그룹 경로 형식은?

   - A) `/aws/eks/cluster-name/logs`
   - B) `/aws/containerinsights/cluster-name/application`
   - C) `/var/log/containers/cluster-name`
   - D) `/kubernetes/cluster-name/logs`

<details>
<summary>정답 보기</summary>

**정답: B) `/aws/containerinsights/cluster-name/application`**

**설명:**
Container Insights는 `/aws/containerinsights/{cluster-name}/` 경로 아래에 application, host, dataplane, performance 등의 로그 그룹을 생성합니다.

</details>

---

5. CloudWatch Logs에서 실시간 로그 처리를 위해 Lambda 함수로 로그를 전달하는 기능은?

   - A) Log Stream
   - B) Metric Filter
   - C) Subscription Filter
   - D) Log Insight

<details>
<summary>정답 보기</summary>

**정답: C) Subscription Filter**

**설명:**
Subscription Filter는 로그 그룹의 로그를 실시간으로 다른 서비스(Lambda, Kinesis Data Firehose, Kinesis Data Streams)로 전달합니다. 필터 패턴을 지정하여 특정 로그만 전달할 수도 있습니다.

</details>

---

6. FluentBit에서 CloudWatch Logs로 로그를 전송할 때 사용하는 OUTPUT 플러그인 이름은?

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>정답 보기</summary>

**정답: B) cloudwatch_logs**

**설명:**
FluentBit의 CloudWatch Logs 출력 플러그인 이름은 `cloudwatch_logs`입니다. AWS에서 제공하는 `aws-for-fluent-bit` 이미지에 기본 포함되어 있습니다.

</details>

---

7. CloudWatch Logs Insights 쿼리에서 시간대별 로그 수를 집계하는 올바른 쿼리는?

   - A) `stats count(*) group by hour`
   - B) `stats count(*) as log_count by bin(1h)`
   - C) `select count(*) from logs group by hour`
   - D) `aggregate count by time(1h)`

<details>
<summary>정답 보기</summary>

**정답: B) `stats count(*) as log_count by bin(1h)`**

**설명:**
CloudWatch Logs Insights에서 시간 기반 집계는 `stats` 명령어와 `bin()` 함수를 사용합니다. `bin(1h)`는 1시간 단위로 데이터를 그룹화합니다.

</details>

---

8. CloudWatch Logs 비용 최적화를 위한 권장 전략이 아닌 것은?

   - A) 불필요한 로그 필터링 (healthcheck 등)
   - B) 환경별 보존 기간 차등 설정
   - C) 모든 로그를 DEBUG 레벨로 수집
   - D) 장기 보존 로그는 S3로 아카이브

<details>
<summary>정답 보기</summary>

**정답: C) 모든 로그를 DEBUG 레벨로 수집**

**설명:**
DEBUG 레벨 로그는 매우 상세하여 로그 볼륨을 크게 증가시킵니다. 프로덕션 환경에서는 INFO 이상 레벨만 수집하는 것이 비용 최적화에 도움됩니다.

</details>

---

9. CloudWatch Logs에서 Metric Filter를 사용하는 주요 목적은?

   - A) 로그를 S3로 내보내기
   - B) 로그 패턴에서 CloudWatch 메트릭 생성
   - C) 로그 보존 기간 설정
   - D) 로그 암호화 설정

<details>
<summary>정답 보기</summary>

**정답: B) 로그 패턴에서 CloudWatch 메트릭 생성**

**설명:**
Metric Filter는 로그에서 특정 패턴(예: ERROR)을 감지하여 CloudWatch 메트릭을 생성합니다. 이 메트릭을 기반으로 CloudWatch Alarm을 설정하여 알림을 받을 수 있습니다.

</details>

---

10. EKS 클러스터에서 Container Insights 설정 시 IRSA(IAM Roles for Service Accounts)에 필요한 권한이 아닌 것은?

    - A) logs:CreateLogGroup
    - B) logs:PutLogEvents
    - C) s3:PutObject
    - D) cloudwatch:PutMetricData

<details>
<summary>정답 보기</summary>

**정답: C) s3:PutObject**

**설명:**
Container Insights 기본 설정에서는 S3 권한이 필요하지 않습니다. CloudWatch Logs(logs:*)와 CloudWatch Metrics(cloudwatch:PutMetricData) 권한만 필요합니다. S3 권한은 로그를 S3로 내보내는 별도 설정 시에만 필요합니다.

</details>
