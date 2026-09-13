# CloudWatch Logs 퀴즈

> **마지막 업데이트**: 2026년 9월 13일

[가이드](../../../observability/logging/03-cloudwatch-logs.md)

---

1. EKS 컨트롤 플레인 로그 유형이 아닌 것은?

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>정답 보기</summary>

**정답: C**

5개 유형은 api, audit, authenticator, controllerManager, scheduler입니다. Worker·앱 로그와 Auto Mode 관리 컴포넌트 전송은 별도 경로입니다.

</details>

---

2. CloudWatch Logs 비용 요인은 어떻게 비교해야 하는가?

   - A) 수집이 항상 가장 큰 월간 비용임
   - B) 저장은 항상 무료임
   - C) 모든 S3 전송 경로가 무료임
   - D) 실제 수집량·보존·scan·class·Region·downstream 비용을 비교함

<details>
<summary>정답 보기</summary>

**정답: D**

수집 GB당 가격만으로 GB-month 저장이나 반복 scan 비용의 순위를 정할 수 없습니다. 가이드의 $1,575는 가상 산술이며 현재 서울 단가나 완전한 청구액이 아닙니다.

</details>

---

3. Glob 또는 정규식으로 필드를 추출하는 Logs Insights QL 명령은?

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>정답 보기</summary>

**정답: B**

parse는 필드를 추출하며 JSON 메시지는 jsonParse로 파싱할 수 있습니다. 수집기 구조의 앱 필드는 log_processed 아래에 있습니다. Glob에서 임의 JSON key 순서를 가정하지 않습니다.

</details>

---

4. 가이드의 수동 애플리케이션 수집기가 사용하는 그룹은?

   - A) /aws/containerinsights/example-eks/application
   - B) /aws/eks/example-eks/logs
   - C) /var/log/containers/example-eks
   - D) 모든 클러스터가 하나의 고정 그룹을 사용함

<details>
<summary>정답 보기</summary>

**정답: A**

설정한 application group은 컨트롤 플레인의 /aws/eks/example-eks/cluster와 다릅니다. 그룹을 먼저 준비하며 수집기는 그룹 생성·보존 변경을 하지 않습니다.

</details>

---

5. Subscription 전송에 대한 올바른 설명은?

   - A) S3 bucket ARN이 subscription filter의 직접 목적지임
   - B) CloudWatch subscription batch를 Firehose의 OpenSearch 목적지로 전송할 수 있음
   - C) Subscription은 Lambda·Kinesis·Firehose로 보낼 수 있고 Firehose 이후 S3 보관은 별도 단계임
   - D) Subscription이 exactly-once와 모든 과거 데이터 backfill을 보장함

<details>
<summary>정답 보기</summary>

**정답: C**

목적지 API와 입력 형식이 중요합니다. CloudWatch Logs→Firehose→OpenSearch는 명시적으로 미지원입니다. Subscription은 비동기·at-least-once이며 export task와 vended-log delivery는 별도 API입니다.

</details>

---

6. CloudWatch Logs용 native C Fluent Bit output plugin 이름은?

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>정답 보기</summary>

**정답: B**

cloudwatch_logs가 native plugin이고 cloudwatch는 이전 Go plugin 이름입니다. 자격 증명, 실제 ServiceAccount, output group과 IAM policy도 일치해야 합니다.

</details>

---

7. 시간별 이벤트 건수를 집계하고 결과 시간 bucket을 정렬하는 QL 쿼리는?

   - A) stats count(*) group by hour
   - B) stats count(*) as log_count by bin(1h) as bucket | sort bucket asc
   - C) select count(*) from logs group by hour
   - D) stats count(*) by bin(1h) | sort @message

<details>
<summary>정답 보기</summary>

**정답: B**

stats 이후에는 사용할 수 있는 결과 필드가 달라지므로 bucket alias로 정렬합니다. 백분위 함수는 percentile이 아닌 pct이며 대소문자 무시 regex는 slash 안의 (?i)를 사용합니다.

</details>

---

8. 비용 통제의 기본 정책으로 위험한 것은?

   - A) 반드시 보존할 레코드로 filter 검증
   - B) 그룹의 단일 소유자가 retention 관리
   - C) 모든 DEBUG를 무기한 보관하고 이를 상쇄하려고 보안상 필요한 레코드를 무차별 폐기
   - D) 변경 전에 수집량·scan 측정

<details>
<summary>정답 보기</summary>

**정답: C**

필요한 진단·보안 기록을 보존하며 volume을 통제해야 합니다. ConfigMap의 LOG_LEVEL은 앱이 읽어야 효과가 있고 retention 변경은 데이터를 삭제할 수 있습니다.

</details>

---

9. Metric filter와 default zero를 올바르게 설명한 것은?

   - A) 모든 과거 레코드를 S3로 내보냄
   - B) 새 일치 로그에서 metric을 만들며 로그가 들어왔지만 매칭되지 않을 때 zero를 사용함
   - C) 로그 자체가 없어도 항상 zero를 발행함
   - D) 모든 log class에서 모든 기능을 지원함

<details>
<summary>정답 보기</summary>

**정답: B**

이 장은 Standard class에서 $.log_processed.level을 검사하는 JSON filter를 사용합니다. 유입이 없으면 missing data가 될 수 있습니다. 알람은 5분 구간 두 번의 오류 건수이며 오류율이나 서비스 정상 보장이 아닙니다.

</details>

---

10. 수동 로그 전용 수집기에 맞는 IAM·소유권 구성은?

   - A) 모든 Pod에 administrator role 부여
   - B) cloudwatch-agent에만 정책을 붙이고 다른 ServiceAccount로 배포
   - C) s3:PutObject만 사용
   - D) 그룹을 먼저 만들고 해당 ARN의 logs:CreateLogStream/logs:PutLogEvents를 실제 collector ServiceAccount에 연결

<details>
<summary>정답 보기</summary>

**정답: D**

수동 구성은 logging/fluent-bit-cloudwatch와 승인된 IRSA trust를 사용합니다. 이 경로에 PutMetricData나 광범위한 logs:*는 필요하지 않습니다. 전체 관측성 chart는 별도 구성이며 Fluent Bit Pod가 cloudwatch-agent를 사용합니다.

</details>
