# CloudWatch Alarms

> **마지막 업데이트**: 2026년 9월 13일

이 장의 CLI·Terraform 예제는 **기존 CloudWatch Metric Alarm**과 Composite Alarm을 다룹니다. 현재 CloudWatch에는 OTLP로 수집한 메트릭을 조회하는 **PromQL Alarm**과 Logs Insights 결과를 평가하는 **Log Alarm**도 있습니다. PromQL Alarm은 `PendingPeriod`/`RecoveryPeriod`를 사용하므로 아래 M-of-N·누락 데이터 설정을 그대로 적용하지 않습니다. 계정·리전·리소스 값은 예시입니다. 생성·변경 명령을 사용하기 전에 실제 대상, IAM 권한, 비용과 알림 수신자를 확인하세요. `PutMetricAlarm`/`PutCompositeAlarm`은 기존 설정을 전체 교체하므로 현재 구성을 보존한 뒤 변경합니다.

## 목차

- [CloudWatch Alarms 개요](#cloudwatch-alarms-개요)
- [아키텍처](#아키텍처)
- [Metric Alarms](#metric-alarms)
- [Composite Alarms](#composite-alarms)
- [Anomaly Detection](#anomaly-detection)
- [SNS 통합](#sns-통합)
- [EventBridge 통합](#eventbridge-통합)
- [Container Insights 알림](#container-insights-알림)
- [CloudWatch Alarm Actions](#cloudwatch-alarm-actions)
- [비용 최적화](#비용-최적화)
- [Prometheus 메트릭 연동](#prometheus-메트릭-연동)
- [Terraform 예시](#terraform-예시)

---

## CloudWatch Alarms 개요

Amazon CloudWatch Alarms는 AWS 네이티브 모니터링 서비스의 알림 기능입니다. CloudWatch 메트릭을 기반으로 알림을 생성하고, SNS, Lambda, EC2 Auto Scaling 등과 통합하여 자동화된 대응이 가능합니다.

### 주요 기능

1. **Metric Alarms**: 단일 메트릭 또는 metric math·Metrics Insights 결과 평가
2. **Composite Alarms**: 여러 알림 조건 조합
3. **Anomaly Detection**: 기계 학습 기반 이상 탐지
4. **Alarm Actions**: 알림 발생 시 자동 액션 실행
5. **AWS 서비스 통합**: EC2, ECS, EKS, Lambda 등과 네이티브 연동

### CloudWatch Alarms vs Prometheus Alertmanager

| 특성 | CloudWatch Alarms | Prometheus Alertmanager |
|------|-------------------|-------------------------|
| **유형** | AWS 관리형 서비스 | 오픈소스 |
| **데이터 소스** | CloudWatch 메트릭·OTLP 메트릭·로그 (알림 유형별) | Prometheus 등이 평가해 보낸 알림 |
| **평가** | 알림 유형에 맞는 metric math·PromQL·Logs Insights | PromQL 평가는 Prometheus, Alertmanager는 그룹화·억제·전달 |
| **비용** | 유형·평가 메트릭·쿼리·기여자 수 등에 따른 과금 | 소프트웨어 라이선스 비용 없음; 운영·인프라 비용 별도 |
| **복잡한 라우팅** | 제한적 | 고급 라우팅 지원 |
| **AWS 통합** | 네이티브 | 추가 설정 필요 |

---

## 아키텍처

### CloudWatch Alarms 동작 흐름

![EC2, EKS, RDS, Lambda 등 다양한 메트릭 소스가 CloudWatch로 모여 Metrics, Metrics Math, Anomaly Detection을 거쳐 Alarms가 판정하고, 그 결과가 SNS/Auto Scaling 등 알림 액션과 Email/SMS 등 알림 채널로 이어지는 전체 흐름을 보여준다.](../../.gitbook/assets/ko-observability-alerting-02-cloudwatch-alarms-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-alerting-02-cloudwatch-alarms-0.html)

### 알림 상태

기존 Metric Alarm은 생성 직후 `INSUFFICIENT_DATA`에서 시작해 평가 후 `OK` 또는 `ALARM`으로 바뀝니다. 데이터 누락이 항상 `INSUFFICIENT_DATA`를 뜻하지는 않습니다. `missing`은 모든 평가 데이터가 누락된 경우 데이터 부족을 나타내며, `notBreaching`은 정상으로, `breaching`은 위반으로 채우고 `ignore`는 현재 상태를 유지합니다. CloudWatch가 추가 조회한 실제 데이터로 평가할 수 있으면 누락 데이터 대체 설정을 쓰지 않습니다. 따라서 heartbeat에 `notBreaching`을 일괄 적용하면 수집 중단을 숨길 수 있습니다. Composite Alarm의 `INSUFFICIENT_DATA`는 최초 생성 시에만 나타납니다.

![기존 Metric Alarm은 생성 시 INSUFFICIENT_DATA에서 시작합니다. 정상·위반 상태와 누락 데이터 정책에 따른 전이를 구분합니다.](../../.gitbook/assets/ko-observability-alerting-02-cloudwatch-alarms-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-alerting-02-cloudwatch-alarms-1.html)

---

## Metric Alarms

### 기본 알림 생성 (Console/CLI)

#### AWS CLI

```bash
# CPU 사용률 알림 생성
aws cloudwatch put-metric-alarm \
  --alarm-name "HighCPUUtilization" \
  --alarm-description "CPU usage exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:alerts \
  --ok-actions arn:aws:sns:ap-northeast-2:123456789012:alerts \
  --treat-missing-data missing
```

### 알림 구성 요소

| 파라미터 | 설명 | 예시 |
|----------|------|------|
| `metric-name` | 모니터링할 메트릭 이름 | `CPUUtilization` |
| `namespace` | 메트릭 네임스페이스 | `AWS/EC2`, `AWS/EKS` |
| `statistic` | 통계 함수 | `Average`, `Sum`, `Maximum`, `Minimum`, `SampleCount` |
| `period` | 평가 주기 (초) | `60`, `300`, `3600` |
| `threshold` | 임계값 | `80` |
| `comparison-operator` | 비교 연산자 | `GreaterThanThreshold` |
| `evaluation-periods` | 평가 기간 수 N | `3` (M은 `datapoints-to-alarm`) |
| `datapoints-to-alarm` | 알림 발생 데이터포인트 수 | `2` of `3` |
| `treat-missing-data` | 데이터 없을 때 처리 | `notBreaching`, `breaching`, `ignore`, `missing` |

`p99`는 `--statistic`이 아니라 `--extended-statistic p99`로 지정합니다. N개 중 M개 위반은 연속일 필요가 없으며, M을 생략하면 N과 같습니다. `Period`는 집계 길이이지 알림 전송 주기가 아닙니다. 기존 metric alarm의 10·20·30초 기간은 고해상도이며 해당 해상도로 수집한 데이터가 필요합니다. 60초는 표준 해상도입니다. 기간×N은 최대 7일, 기간이 1시간 미만이면 최대 1일입니다. 자동 조정 액션을 제외한 액션은 보통 상태 전이 때 실행됩니다.

### 비교 연산자

```yaml
# 사용 가능한 비교 연산자
comparison-operators:
  - GreaterThanThreshold           # 초과
  - GreaterThanOrEqualToThreshold  # 이상
  - LessThanThreshold              # 미만
  - LessThanOrEqualToThreshold     # 이하
  - LessThanLowerOrGreaterThanUpperThreshold  # 범위 벗어남
  - LessThanLowerThreshold         # 하한 미만
  - GreaterThanUpperThreshold      # 상한 초과
```

### Metrics Math를 사용한 알림

```bash
# 오류율 계산 알림 (오류 수 / 전체 요청 수)
aws cloudwatch put-metric-alarm \
  --alarm-name "HighErrorRate" \
  --alarm-description "Error rate exceeds 5%" \
  --metrics '[
    {
      "Id": "errors",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationELB",
          "MetricName": "HTTPCode_Target_5XX_Count",
          "Dimensions": [
            {"Name": "LoadBalancer", "Value": "app/my-alb/1234567890"}
          ]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": false
    },
    {
      "Id": "requests",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationELB",
          "MetricName": "RequestCount",
          "Dimensions": [
            {"Name": "LoadBalancer", "Value": "app/my-alb/1234567890"}
          ]
        },
        "Period": 300,
        "Stat": "Sum"
      },
      "ReturnData": false
    },
    {
      "Id": "error_rate",
      "Expression": "IF(requests > 0, 100 * FILL(errors, 0) / requests, 0)",
      "ReturnData": true
    }
  ]' \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:alerts
```

이 식은 ALB가 target으로 전달한 요청의 target 5xx 비율입니다. ALB 자체의 오류나 target 선택 전 실패까지 포함한 전체 사용자 오류율은 아닙니다. 요청이 있을 때 미발행 5xx는 0으로 채우고, 요청이 0이면 이 예제는 0%로 정의합니다. 요청·수집 데이터 자체의 부재는 별도 알림으로 감시하세요. Classic metric math alarm은 최종 결과가 단일 시계열이어야 합니다. `SEARCH`는 그래프용이며 alarm의 식으로 사용할 수 없습니다. `RATE`는 희소 메트릭에서 평가 범위에 따라 달라질 수 있어 수집 형태를 먼저 확인합니다.

### Metrics Math 함수

```yaml
# 자주 사용하는 함수
math-functions:
  # 산술 연산
  - "m1 + m2"           # 합계
  - "m1 - m2"           # 차이
  - "m1 * m2"           # 곱
  - "m1 / m2"           # 나눗셈
  - "(m1 / m2) * 100"   # 백분율

  # 통계 함수
  - "AVG(METRICS())"    # 평균
  - "SUM(METRICS())"    # 합계
  - "MIN(METRICS())"    # 최솟값
  - "MAX(METRICS())"    # 최댓값

  # 조건 함수
  - "IF(m1 > 100, m1, 0)"  # 조건부

  # 시간 관련
  - "RATE(m1)"          # 변화율
  - "DIFF(m1)"          # 차이
  - "PERIOD(m1)"        # 기간

  # 검색
  - "SEARCH('{AWS/EC2,InstanceId} MetricName=\"CPUUtilization\"', 'Average', 300)"
```

---

## Composite Alarms

### Composite Alarm 개념

Composite Alarm은 여러 개의 Metric Alarm을 조합하여 복잡한 조건을 정의할 수 있습니다.

![High CPU, High Memory, High Disk 세 개의 Metric Alarm이 (CPU AND Memory) OR Disk 규칙으로 결합되어 Composite Alarm(Server Resource Critical)을 발생시키고, 이 Composite Alarm만 SNS/Lambda 액션을 호출하는 구조를 보여준다.](../../.gitbook/assets/ko-observability-alerting-02-cloudwatch-alarms-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-alerting-02-cloudwatch-alarms-2.html)

`CWAgent`의 메모리·디스크 메트릭은 agent 설치와 실제 발행 차원 구성이 필요합니다. 아래 `InstanceId`만 사용하는 예제는 agent가 그 차원 조합으로 집계해 발행할 때만 동작합니다. `disk_used_percent`는 보통 `path`·`device`·`fstype` 등의 차원도 있으므로 `list-metrics`로 확인한 **전체 차원 조합**을 사용하세요. 예제의 child alarm은 액션이 없고 composite만 알립니다.

### Composite Alarm 생성

```bash
# 개별 알림 생성
aws cloudwatch put-metric-alarm \
  --alarm-name "HighCPU" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0

aws cloudwatch put-metric-alarm \
  --alarm-name "HighMemory" \
  --metric-name mem_used_percent \
  --namespace CWAgent \
  --statistic Average \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0

aws cloudwatch put-metric-alarm \
  --alarm-name "HighDisk" \
  --metric-name disk_used_percent \
  --namespace CWAgent \
  --statistic Average \
  --period 300 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0

# Composite Alarm 생성
aws cloudwatch put-composite-alarm \
  --alarm-name "ServerResourceCritical" \
  --alarm-description "Server resources are critical" \
  --alarm-rule '(ALARM("HighCPU") AND ALARM("HighMemory")) OR ALARM("HighDisk")' \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:critical-alerts \
  --ok-actions arn:aws:sns:ap-northeast-2:123456789012:alerts
```

### 알림 규칙 문법

```yaml
# Composite Alarm 규칙 문법
rule-syntax:
  # 기본 연산자
  - "ALARM(alarm-name)"      # 알림 상태 확인
  - "OK(alarm-name)"         # OK 상태 확인
  - "INSUFFICIENT_DATA(alarm-name)"  # 데이터 부족 상태

  # 논리 연산자
  - "AND"                    # 모든 조건 충족
  - "OR"                     # 하나 이상 충족
  - "NOT"                    # 부정
  - "()"                     # 그룹화

examples:
  # 모든 조건 충족
  - "ALARM(A1) AND ALARM(A2) AND ALARM(A3)"

  # 하나 이상 충족
  - "ALARM(A1) OR ALARM(A2)"

  # 복합 조건
  - "(ALARM(A1) AND ALARM(A2)) OR ALARM(A3)"

  # 부정
  - "ALARM(A1) AND NOT ALARM(A2)"

  # M of N 패턴 (3개 중 2개 이상)
  - "(ALARM(A1) AND ALARM(A2)) OR (ALARM(A1) AND ALARM(A3)) OR (ALARM(A2) AND ALARM(A3))"
```

### 알림 억제 패턴

`set-alarm-state`는 테스트용 임시 전환입니다. Metric Alarm은 빠르게 실제 상태로 돌아가므로 유지보수 창 전체를 보장하지 않습니다. 다음 예제는 외부 제어자가 유지보수 상태를 지속 발행하는 `MaintenanceMode` alarm을 전제로 합니다. `ActionsSuppressor`는 composite의 평가 상태를 바꾸지 않고 액션을 억제합니다. wait/extension 시간까지 운영 창에 포함해 검증하세요.

```bash
aws cloudwatch put-composite-alarm  \
  --alarm-name ProductionAlerts  \
  --alarm-rule 'ALARM("HighCPU")'  \
  --actions-suppressor MaintenanceMode  \
  --actions-suppressor-wait-period 60  \
  --actions-suppressor-extension-period 60  \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:alerts
```

---

## Anomaly Detection

### Anomaly Detection 개요

CloudWatch Anomaly Detection은 기계 학습을 사용하여 메트릭의 정상 패턴을 학습하고, 이상치를 탐지합니다.

![과거 데이터를 ML 모델이 학습해 예상 범위(Expected Band)를 만들고, 현재 메트릭이 그 범위를 벗어나면 Anomaly Alert, 이내이면 Normal로 판정하는 CloudWatch Anomaly Detection의 학습·탐지 흐름을 보여준다.](../../.gitbook/assets/ko-observability-alerting-02-cloudwatch-alarms-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-alerting-02-cloudwatch-alarms-3.html)

### Anomaly Detection 알림 생성

```bash
# Anomaly Detection 모델 생성 (자동)
# 첫 알림 생성 시 모델이 자동으로 생성됨

aws cloudwatch put-metric-alarm \
  --alarm-name "CPUAnomalyDetection" \
  --alarm-description "CPU usage is anomalous" \
  --metrics '[
    {
      "Id": "m1",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/EC2",
          "MetricName": "CPUUtilization",
          "Dimensions": [
            {"Name": "InstanceId", "Value": "i-1234567890abcdef0"}
          ]
        },
        "Period": 300,
        "Stat": "Average"
      },
      "ReturnData": true
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)",
      "ReturnData": true
    }
  ]' \
  --threshold-metric-id ad1 \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:alerts
```

### Anomaly Detection 설정

```yaml
# ANOMALY_DETECTION_BAND 함수
# ANOMALY_DETECTION_BAND(metric, stddev)
# - metric: 분석할 메트릭
# - stddev: 표준편차 배수 (기본값 2)

examples:
  # 폭 조절 값 2: 고정 95% 신뢰구간을 보장하지 않음
  - "ANOMALY_DETECTION_BAND(m1, 2)"

  # 폭 조절 값 3: 더 넓은 예상 범위
  - "ANOMALY_DETECTION_BAND(m1, 3)"

  # 더 민감한 탐지 (1 표준편차)
  - "ANOMALY_DETECTION_BAND(m1, 1)"
```

이 값은 모델의 예상 범위 폭을 조절합니다. 정규분포에 따른 고정 95%·99.7% 보장으로 해석하지 마세요. 모델은 최대 2주 이력을 사용하며 그보다 적은 데이터로도 활성화할 수 있습니다. 아래 제외 날짜는 형식 예시이므로 실제 학습 범위의 구간으로 바꿉니다.

### 모델 학습 기간 조정

```bash
# 기존 모델에 제외 기간 추가 (유지보수, 장애 기간 등)
aws cloudwatch put-anomaly-detector \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --stat Average \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --configuration '{
    "ExcludedTimeRanges": [
      {
        "StartTime": "2025-02-15T00:00:00Z",
        "EndTime": "2025-02-15T06:00:00Z"
      }
    ]
  }'
```

---

## SNS 통합

### SNS Topic 생성

```bash
# SNS Topic 생성
aws sns create-topic --name eks-alerts

# Email 구독 추가
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-2:123456789012:eks-alerts \
  --protocol email \
  --notification-endpoint team@example.com

# SMS 구독 추가
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-2:123456789012:eks-alerts \
  --protocol sms \
  --notification-endpoint "$VERIFIED_SMS_NUMBER"

# Lambda 구독 추가
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-2:123456789012:eks-alerts \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:ap-northeast-2:123456789012:function:alert-handler
```

### SNS 메시지 필터링

기본 CloudWatch SNS 알림에는 예제의 `severity`·`environment` 메시지 속성이 자동으로 붙지 않습니다. 본문의 `NewStateValue`를 필터링하려면 `FilterPolicyScope=MessageBody`를 지정합니다. 이 필터는 `OK` 복구 알림을 제외합니다. Email은 구독 확인이 필요하고, SMS는 검증된 번호·샌드박스·리전별 발송 조건과 비용을 확인해야 합니다. Lambda 구독에는 `sns.amazonaws.com`의 호출을 해당 topic ARN으로 제한한 Lambda resource policy도 필요합니다.

```bash
aws sns set-subscription-attributes  \
  --subscription-arn "$SUBSCRIPTION_ARN"  \
  --attribute-name FilterPolicyScope  \
  --attribute-value MessageBody
aws sns set-subscription-attributes  \
  --subscription-arn "$SUBSCRIPTION_ARN"  \
  --attribute-name FilterPolicy  \
  --attribute-value '{"NewStateValue": ["ALARM"]}'
```

### SNS to Slack 통합 (Lambda)

표준 CloudWatch 알림은 **Amazon Q Developer in chat applications**(이전 AWS Chatbot)에 SNS topic과 승인된 Slack 채널을 연결해 전달할 수 있습니다. 채널의 IAM 역할과 guardrail policy를 알림 수신 목적에 맞게 제한합니다.

직접 Lambda를 구현해야 한다면 webhook을 Secrets Manager 등에서 읽고 URL·연결/읽기 timeout·응답 상태를 검증하세요. HTTP 429/5xx를 성공으로 반환하지 않고 재시도/DLQ와 중복 전달 처리를 구성해야 합니다. SNS의 `Records[].Sns.Message` 본문은 아래 EventBridge 예제의 envelope와 다릅니다. 이 장의 검증은 실제 Slack 메시지 전송을 포함하지 않습니다.

---

## EventBridge 통합

### EventBridge 규칙 생성

```bash
# CloudWatch Alarm 상태 변경을 EventBridge로 라우팅
aws events put-rule \
  --name "CloudWatchAlarmStateChange" \
  --event-pattern '{
    "source": ["aws.cloudwatch"],
    "detail-type": ["CloudWatch Alarm State Change"],
    "detail": {
      "state": {
        "value": ["ALARM"]
      }
    }
  }'

# Lambda 타겟 추가
aws events put-targets \
  --rule "CloudWatchAlarmStateChange" \
  --targets '[
    {
      "Id": "AlertHandler",
      "Arn": "arn:aws:lambda:ap-northeast-2:123456789012:function:alert-handler"
    }
  ]'
```

### 자동 대응 구성

![CloudWatch Alarm의 ALARM 상태 변경이 EventBridge의 Event Rule에 매칭되어 Lambda 함수, SSM Runbook, Step Functions 복구 워크플로우 등 다섯 가지 자동 대응 타겟으로 분기되는 흐름을 보여준다.](../../.gitbook/assets/ko-observability-alerting-02-cloudwatch-alarms-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-alerting-02-cloudwatch-alarms-4.html)

### EventBridge 이벤트 패턴

```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "account": ["123456789012"],
  "region": ["ap-northeast-2"],
  "resources": ["arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:EKS-Node-HighCPU"],
  "detail": {
    "alarmName": ["EKS-Node-HighCPU"],
    "state": {"value": ["ALARM"]}
  }
}
```

`previousState=OK`로 제한하면 `INSUFFICIENT_DATA → ALARM` 전이를 놓칩니다. 특정 alarm ARN을 고정하면 metric math나 composite의 서로 다른 configuration 구조에 의존하지 않습니다. `put-targets`에는 Lambda 호출 권한이 자동으로 포함되지 않습니다. `events.amazonaws.com`을 principal로, 해당 rule ARN을 `SourceArn`으로 제한한 Lambda resource policy와 재시도/DLQ를 설정하세요.

### 자동 복구 Lambda 예시

고CPU는 재부팅이 필요한 장애라는 증거가 아닙니다. 이 예제는 자동 복구의 **입력 점검 단계**로, 상태·계정·리전·alarm ARN을 확인하고 메트릭을 반환합니다. 실제 EventBridge의 `dimensions`는 객체이고 SNS alarm 본문의 dimension 목록과 다릅니다. metric math의 첫 항목이 expression이거나 composite에 metric 목록이 없어도 처리합니다.

[검증된 event normalizer와 테스트](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/observability/cloudwatch-alarms)를 Lambda package에 포함한 뒤 다음처럼 호출할 수 있습니다.

```python
from event_normalizer import normalize_alarm_event

def lambda_handler(event, context):
    return normalize_alarm_event(
        event,
        expected_account="123456789012",
        expected_region="ap-northeast-2",
    )
```

이 함수는 AWS 변경을 실행하지 않습니다. payload의 필드 검사는 송신자 인증을 대신하지 않습니다. 복구를 추가할 때는 target allowlist, 현재 alarm/리소스 상태 재확인, 중복 실행 방지, cooldown, 최소 권한과 롤백을 별도로 구현해야 합니다.

---

## Container Insights 알림

### EKS Container Insights 메트릭

여기서는 기존 `ContainerInsights` CloudWatch metric 경로를 사용합니다. enhanced observability·OTel 경로와 메트릭 이름/차원/과금을 혼용하지 않습니다. CloudWatch Agent와 Fluent Bit를 설치하는 [현재 EKS add-on 가이드](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)를 따르고, 클러스터 Kubernetes 버전·리전과 호환되는 add-on 버전을 선택하세요. EKS Pod Identity를 사용할 경우 agent association과 IAM 권한을 먼저 구성합니다.

`update-addon`은 이미 설치된 add-on을 갱신합니다. 최초 설치는 `create-addon`이며, 현재 구성과 Pod Identity association을 보존해야 합니다. 이전 `v1.2.0` 고정 및 무검토 `latest` Fluentd manifest 적용 대신 버전을 조회하고 배포 계획에서 선택합니다.

```bash
aws eks describe-addon-versions  \
  --addon-name amazon-cloudwatch-observability  \
  --kubernetes-version "$KUBERNETES_VERSION"  \
  --region "$AWS_REGION"
aws cloudwatch list-metrics  \
  --namespace ContainerInsights  \
  --metric-name pod_number_of_container_restarts  \
  --dimensions Name=ClusterName,Value=my-cluster  \
  --region "$AWS_REGION"
```

### Container Insights 알림 예시

```bash
# 클러스터 집계 CPU 사용률 알림
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Node-HighCPU" \
  --metric-name node_cpu_utilization \
  --namespace ContainerInsights \
  --dimensions Name=ClusterName,Value=my-cluster \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-alerts

# 파드 메모리 사용률 알림
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Pod-HighMemory" \
  --metric-name pod_memory_utilization_over_pod_limit \
  --namespace ContainerInsights \
  --dimensions Name=ClusterName,Value=my-cluster Name=Namespace,Value=production \
  --statistic Average \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-alerts

# 특정 Pod의 누적 재시작 수 알림 (최근 5분 증가량 아님)
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Pod-Restarts" \
  --metric-name pod_number_of_container_restarts \
  --namespace ContainerInsights \
  --dimensions Name=ClusterName,Value=my-cluster Name=Namespace,Value=production Name=PodName,Value=my-pod \
  --statistic Maximum \
  --period 300 \
  --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-alerts
```

위 CPU 예제는 클러스터 집계입니다. 개별 노드는 `ClusterName`·`NodeName`·`InstanceId` 전체 조합을 사용합니다. `pod_memory_utilization`의 분모는 **노드 메모리**이며, Pod limit 대비 비율은 `pod_memory_utilization_over_pod_limit`입니다. Pod의 어느 컨테이너라도 memory limit이 없으면 후자의 메트릭이 나타나지 않을 수 있습니다. `pod_number_of_container_restarts`는 `ClusterName`·`Namespace`·`PodName` 조합의 누적 수입니다. `Maximum > 3`은 관측된 누적 값이 3을 넘었다는 뜻이며 샘플을 `Sum`해 최근 재시작 횟수로 해석하면 안 됩니다. Pod 교체·counter reset·동일 이름 재사용도 고려하고 최근 증가량은 reset-aware PromQL `increase()` 또는 별도 delta 메트릭으로 평가합니다.

### Container Insights 주요 메트릭

| 메트릭 | 설명 | 차원 |
|--------|------|------|
| `cluster_node_count` | 클러스터 노드 수 | ClusterName |
| `cluster_failed_node_count` | 실패한 노드 수 | ClusterName |
| `node_cpu_utilization` | 노드 CPU 사용률 | ClusterName, NodeName, InstanceId; or ClusterName |
| `node_memory_utilization` | 노드 메모리 사용률 | ClusterName, NodeName, InstanceId; or ClusterName |
| `node_filesystem_utilization` | 노드 디스크 사용률 | ClusterName, NodeName, InstanceId; or ClusterName |
| `pod_cpu_utilization` | 파드 CPU 사용률 | ClusterName, Namespace, PodName |
| `pod_memory_utilization` | 파드 메모리 사용률 | ClusterName, Namespace, PodName |
| `pod_number_of_container_restarts` | 컨테이너 재시작 횟수 | ClusterName, Namespace, PodName |
| `service_number_of_running_pods` | 서비스별 실행 중인 파드 수 | ClusterName, Namespace, Service |

---

## CloudWatch Alarm Actions

### EC2 Actions

직접 EC2 액션은 stop·terminate·reboot·recover이며 **start는 없습니다**. 아래 예제는 실제로 인스턴스를 변경하므로 지원 인스턴스·권한·중지 영향과 사전 승인을 확인한 전용 대상에서만 사용합니다. 누락 데이터는 `missing`, 변경 액션은 `ALARM`에만 연결합니다. metric math/composite alarm은 EC2 액션을 직접 실행하지 못합니다.


```bash
# EC2 인스턴스 복구 (시스템 상태 검사 실패 시)
aws cloudwatch put-metric-alarm \
  --alarm-name "EC2-SystemCheckFailed" \
  --metric-name StatusCheckFailed_System \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Maximum \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 2 \
  --treat-missing-data missing \
  --alarm-actions arn:aws:automate:ap-northeast-2:ec2:recover

# EC2 인스턴스 중지
aws cloudwatch put-metric-alarm \
  --alarm-name "EC2-LowUtilization-Stop" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 3600 \
  --threshold 5 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 24 \
  --treat-missing-data missing \
  --alarm-actions arn:aws:automate:ap-northeast-2:ec2:stop
```

### Auto Scaling Actions

```bash
# Auto Scaling 정책 연결
aws cloudwatch put-metric-alarm \
  --alarm-name "ASG-ScaleOut" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=AutoScalingGroupName,Value=my-asg \
  --statistic Average \
  --period 300 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:autoscaling:ap-northeast-2:123456789012:scalingPolicy:xxx:autoScalingGroupName/my-asg:policyName/scale-out

aws cloudwatch put-metric-alarm \
  --alarm-name "ASG-ScaleIn" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=AutoScalingGroupName,Value=my-asg \
  --statistic Average \
  --period 300 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:autoscaling:ap-northeast-2:123456789012:scalingPolicy:xxx:autoScalingGroupName/my-asg:policyName/scale-in
```

### Systems Manager Actions

`AlarmActions`에 `automation-definition/...` ARN을 넣어 임의의 SSM Automation runbook을 직접 실행할 수는 없습니다. 직접 SSM 통합은 API에 열거된 OpsItem 등이며, Automation은 **EventBridge → SSM Automation target** 또는 별도 Lambda/Step Functions 경로로 연결합니다. EventBridge target의 실행 역할, `ssm:StartAutomationExecution` 범위, runbook 파라미터와 Automation 실행 역할을 각각 제한하세요. 단순 디스크 임계값만으로 임의 파일을 삭제하는 동작은 넣지 않습니다.

---

## 비용 최적화

### 비용 요소

다음은 2026-09-13 공식 가격 페이지의 **US East 예시**입니다. 서울 리전의 확정 견적이 아니며 해당 리전 가격표를 확인해야 합니다. 메트릭 alarm은 식에서 평가하는 메트릭별, composite는 alarm별로 과금됩니다. Anomaly Detection은 실제 메트릭과 상·하한 두 개를 포함합니다. 원본 child alarm 비용은 composite를 추가해도 남으므로 composite는 알림 소음을 줄이지만 자동 비용 절감은 아닙니다.


| 항목 | 비용 |
|------|------|
| Standard Resolution 알림 (60초) | 월 $0.10/알림 |
| High Resolution 알림 (10초) | 월 $0.30/알림 |
| 표준 Anomaly Detection alarm: 실제 1개 + band 2개 | 월 $0.30/alarm 예시 |
| Composite Alarm | 월 $0.50/알림 |

### 비용 최적화 전략

![중복·해상도·평가 메트릭 수를 검토하고, Composite는 child alarm 비용에 추가된다는 점과 삭제 전 의존성 확인을 보여줍니다.](../../.gitbook/assets/ko-observability-alerting-02-cloudwatch-alarms-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-observability-alerting-02-cloudwatch-alarms-5.html)

### 권장 설정

```yaml
# 비용 효율적인 알림 설정

# Critical: Standard Resolution (60초; 10/20/30초만 고해상도)
critical-alerts:
  period: 60  # 1분
  evaluation-periods: 2

# Warning: Standard Resolution
warning-alerts:
  period: 300  # 5분
  evaluation-periods: 2

# Info: Standard Resolution (느슨한 감지)
info-alerts:
  period: 900  # 15분
  evaluation-periods: 3
```

### 알림 정리 스크립트

아래 명령은 삭제 후보 점검용 목록만 반환합니다. `INSUFFICIENT_DATA` 자체는 미사용 증거가 아니며, 고정 과거 날짜로 90일을 판정하지 않습니다. `StateTransitionedTimestamp`와 현재 시각의 차이, 실제 수집 상태·업무 소유자·composite 의존성을 검토한 뒤 별도 변경 절차로 삭제합니다. `StateUpdatedTimestamp`는 상태 이유 갱신에도 바뀔 수 있어 지속 상태 기간과 혼동하면 안 됩니다.

```bash
aws cloudwatch describe-alarms  \
  --alarm-types MetricAlarm  \
  --state-value INSUFFICIENT_DATA  \
  --query 'MetricAlarms[].{Name:AlarmName,StateSince:StateTransitionedTimestamp,Updated:StateUpdatedTimestamp}'  \
  --output json
```

---

## Prometheus 메트릭 연동

### Amazon Managed Prometheus (AMP) 연동

AMP에 저장한 모든 메트릭이 classic CloudWatch metric으로 자동 복제되는 것은 아닙니다. 목적에 따라 경로를 선택합니다.

- **AMP 안에서 알림**: workspace의 Prometheus alerting rules → 관리형 Alertmanager → 지원 receiver(SNS 또는 PagerDuty)를 구성합니다.
- **CloudWatch PromQL Alarm**: CloudWatch OTLP endpoint로 수집한 메트릭을 대상으로 합니다. AMP workspace를 그대로 조회하는 기능과 혼동하지 않습니다.
- **기존 CloudWatch metric으로 재발행**: 필요한 집계만 별도 exporter에서 정의합니다. 일관된 frozen 임시 자격증명으로 SigV4 서명하고 timeout/HTTP 오류/응답 유형/유한한 숫자/데이터 시각/차원을 검증해야 합니다. 빈 결과·NaN·실패를 0이나 성공으로 바꾸지 마세요. 이 경로에는 쿼리·custom metric·실행 비용과 지연이 추가됩니다.

이전 예제의 CPU mode별 평균은 전체 CPU 사용률과 같지 않고, 무제한·서로 다른 Pod의 메모리 평균 비율은 각 Pod의 한도 초과를 나타내지 않습니다. 메트릭의 label과 reset semantics를 보존하는 PromQL을 선택한 뒤 rule unit test와 실제 수집 데이터로 검증하세요.

---

## Terraform 예시

아래 블록은 하나의 module로 함께 검증하는 예시입니다. 배포 전 실제 리소스 값과 SNS topic policy를 설정하고 `terraform plan`의 변경을 검토합니다. 예제 검증은 provider schema/구문 검사이며 AWS 배포나 실제 알림 수신을 뜻하지 않습니다.


### 기본 알림

```hcl
# SNS Topic
resource "aws_sns_topic" "alerts" {
  name = "eks-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "team@example.com"
}

# EC2 CPU 알림
resource "aws_cloudwatch_metric_alarm" "ec2_cpu" {
  alarm_name          = "ec2-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EC2 CPU usage exceeds 80%"

  dimensions = {
    InstanceId = "i-1234567890abcdef0"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  treat_missing_data = "missing"
}
```

### Metrics Math 알림

```hcl
resource "aws_cloudwatch_metric_alarm" "alb_error_rate" {
  alarm_name          = "alb-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 5
  alarm_description   = "ALB error rate exceeds 5%"

  metric_query {
    id          = "errors"
    return_data = false

    metric {
      metric_name = "HTTPCode_Target_5XX_Count"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "Sum"

      dimensions = {
        LoadBalancer = "app/my-alb/1234567890"
      }
    }
  }

  metric_query {
    id          = "requests"
    return_data = false

    metric {
      metric_name = "RequestCount"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "Sum"

      dimensions = {
        LoadBalancer = "app/my-alb/1234567890"
      }
    }
  }

  metric_query {
    id          = "error_rate"
    expression  = "IF(requests > 0, 100 * FILL(errors, 0) / requests, 0)"
    label       = "Error Rate"
    return_data = true
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

### Composite Alarm

```hcl
# 개별 알림
resource "aws_cloudwatch_metric_alarm" "cpu_alarm" {
  alarm_name          = "high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80

  dimensions = {
    InstanceId = "i-1234567890abcdef0"
  }
}

resource "aws_cloudwatch_metric_alarm" "memory_alarm" {
  alarm_name          = "high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "mem_used_percent"
  namespace           = "CWAgent"
  period              = 300
  statistic           = "Average"
  threshold           = 85

  dimensions = {
    InstanceId = "i-1234567890abcdef0"
  }
}

# Composite Alarm
resource "aws_cloudwatch_composite_alarm" "server_critical" {
  alarm_name        = "server-critical"
  alarm_description = "Server CPU and Memory are both high"

  alarm_rule = "ALARM(${aws_cloudwatch_metric_alarm.cpu_alarm.alarm_name}) AND ALARM(${aws_cloudwatch_metric_alarm.memory_alarm.alarm_name})"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}
```

### EKS Container Insights 알림

```hcl
resource "aws_cloudwatch_metric_alarm" "eks_node_cpu" {
  alarm_name          = "eks-node-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "node_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EKS Node CPU usage exceeds 80%"

  dimensions = {
    ClusterName = "my-eks-cluster"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "eks_pod_restarts" {
  alarm_name          = "eks-pod-restarts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "pod_number_of_container_restarts"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Maximum"
  threshold           = 3
  alarm_description   = "Observed cumulative restart count exceeds 3; not a 5-minute increase"

  dimensions = {
    ClusterName = "my-eks-cluster"
    Namespace   = "production"
    PodName     = "my-pod"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

### Anomaly Detection 알림

```hcl
resource "aws_cloudwatch_metric_alarm" "cpu_anomaly" {
  alarm_name          = "cpu-anomaly-detection"
  comparison_operator = "LessThanLowerOrGreaterThanUpperThreshold"
  evaluation_periods  = 2
  threshold_metric_id = "ad1"
  alarm_description   = "CPU usage is anomalous"

  metric_query {
    id          = "m1"
    return_data = true

    metric {
      metric_name = "CPUUtilization"
      namespace   = "AWS/EC2"
      period      = 300
      stat        = "Average"

      dimensions = {
        InstanceId = "i-1234567890abcdef0"
      }
    }
  }

  metric_query {
    id          = "ad1"
    expression  = "ANOMALY_DETECTION_BAND(m1, 2)"
    label       = "CPUUtilization (Expected)"
    return_data = true
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

---

## 참고 자료

- [CloudWatch alarm types](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)
- [PutMetricAlarm API](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html)
- [Missing data evaluation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarms-and-missing-data.html)
- [Composite alarms and action suppression](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutCompositeAlarm.html)
- [Metric math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [Anomaly detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [SNS alarm message schemas](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Notify_Users_Alarm_Changes.html)
- [SNS filter policy scope](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering-scope.html)
- [EventBridge alarm events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-and-eventbridge.html)
- [EventBridge target permissions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [Container Insights metric dimensions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
- [CloudWatch Observability EKS add-on](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [PromQL alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-promql.html)
- [Log alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Alarm-On-Logs.html)
- [AMP alert receivers](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-alertmanager-receiver.html)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [CloudWatch Alarms 퀴즈](../../quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)를 풀어보세요.
