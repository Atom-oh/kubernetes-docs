# CloudWatch Alarms 퀴즈

CloudWatch Alarms에 대한 이해도를 테스트하는 퀴즈입니다.

---

1. CloudWatch Alarm의 세 가지 상태는 무엇인가요?
   - A) Active, Inactive, Pending
   - B) OK, ALARM, INSUFFICIENT_DATA
   - C) Normal, Warning, Critical
   - D) Green, Yellow, Red

<details>
<summary>정답 보기</summary>

**정답: B) OK, ALARM, INSUFFICIENT_DATA**

**설명:**
CloudWatch Alarm은 세 가지 상태를 가집니다:
- **OK**: 메트릭이 정상 범위 내에 있음
- **ALARM**: 메트릭이 정의된 임계값을 위반함
- **INSUFFICIENT_DATA**: 알림 평가에 필요한 데이터가 충분하지 않음

이 상태들은 메트릭 값과 알림 구성에 따라 자동으로 전환됩니다.

</details>

---

2. CloudWatch Alarm에서 `evaluation-periods`와 `datapoints-to-alarm` 설정의 차이점은?
   - A) 두 설정은 동일한 기능을 수행한다
   - B) evaluation-periods는 평가 기간 수, datapoints-to-alarm은 ALARM 상태가 되기 위해 필요한 데이터 포인트 수
   - C) evaluation-periods는 초 단위, datapoints-to-alarm은 분 단위이다
   - D) evaluation-periods는 메트릭 수집 간격, datapoints-to-alarm은 알림 전송 간격이다

<details>
<summary>정답 보기</summary>

**정답: B) evaluation-periods는 평가 기간 수, datapoints-to-alarm은 ALARM 상태가 되기 위해 필요한 데이터 포인트 수**

**설명:**
- `evaluation-periods`: 알림 평가에 사용되는 기간의 수 (예: 3)
- `datapoints-to-alarm`: ALARM 상태로 전환되기 위해 임계값을 위반해야 하는 데이터 포인트 수 (예: 2)

예를 들어, evaluation-periods=3, datapoints-to-alarm=2로 설정하면 "3개 기간 중 2개 이상에서 임계값 위반 시 ALARM"이 됩니다. 이를 "M of N" 알림이라고 합니다.

</details>

---

3. CloudWatch Metric Math에서 ALB의 오류율을 계산하는 올바른 표현식은?
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>정답 보기</summary>

**정답: B) `(errors / requests) * 100`**

**설명:**
오류율(Error Rate)은 오류 수를 전체 요청 수로 나눈 후 100을 곱하여 백분율로 계산합니다. CloudWatch Metric Math에서는 여러 메트릭을 조합하여 이러한 계산을 수행할 수 있으며, 결과를 알림 조건으로 사용할 수 있습니다.

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. Composite Alarm에 대한 설명으로 올바르지 않은 것은?
   - A) 여러 Metric Alarm을 조합하여 복잡한 조건을 정의할 수 있다
   - B) AND, OR, NOT 논리 연산자를 사용할 수 있다
   - C) Composite Alarm 안에 다른 Composite Alarm을 포함할 수 있다
   - D) Composite Alarm은 자체 메트릭을 정의할 수 있다

<details>
<summary>정답 보기</summary>

**정답: D) Composite Alarm은 자체 메트릭을 정의할 수 있다**

**설명:**
Composite Alarm은 자체 메트릭을 정의하지 않습니다. 대신 기존 Metric Alarm들의 상태를 조합하여 복잡한 알림 조건을 만듭니다. Composite Alarm의 규칙은 `ALARM(alarm-name)`, `OK(alarm-name)` 등의 함수와 AND, OR, NOT 연산자로 구성됩니다. Composite Alarm 안에 다른 Composite Alarm을 중첩할 수도 있습니다.

</details>

---

5. CloudWatch Anomaly Detection의 작동 원리로 올바른 것은?
   - A) 고정된 임계값을 기반으로 이상치 탐지
   - B) 기계 학습을 사용하여 메트릭의 예상 범위를 학습하고 벗어나면 알림
   - C) 다른 메트릭과의 상관관계를 분석하여 이상치 탐지
   - D) 사용자가 정의한 패턴과 일치하지 않으면 알림

<details>
<summary>정답 보기</summary>

**정답: B) 기계 학습을 사용하여 메트릭의 예상 범위를 학습하고 벗어나면 알림**

**설명:**
CloudWatch Anomaly Detection은 기계 학습 알고리즘을 사용하여 메트릭의 과거 데이터를 분석하고, 시간대별, 요일별 패턴 등을 학습합니다. 이를 바탕으로 예상 범위(expected band)를 생성하고, 실제 메트릭 값이 이 범위를 벗어나면 이상치로 감지합니다. `ANOMALY_DETECTION_BAND(metric, stddev)` 함수로 표준편차 배수를 조정할 수 있습니다.

</details>

---

6. CloudWatch Alarm의 `treat-missing-data` 옵션 중 `notBreaching`의 의미는?
   - A) 데이터가 없으면 알림을 발생시킨다
   - B) 데이터가 없으면 이전 상태를 유지한다
   - C) 데이터가 없으면 임계값을 위반하지 않은 것으로 처리한다
   - D) 데이터가 없으면 INSUFFICIENT_DATA 상태로 전환한다

<details>
<summary>정답 보기</summary>

**정답: C) 데이터가 없으면 임계값을 위반하지 않은 것으로 처리한다**

**설명:**
`treat-missing-data` 옵션 값들의 의미:
- `notBreaching`: 누락된 데이터를 임계값을 위반하지 않은 것으로 처리 (OK로 간주)
- `breaching`: 누락된 데이터를 임계값을 위반한 것으로 처리 (ALARM으로 간주)
- `ignore`: 현재 상태 유지
- `missing`: INSUFFICIENT_DATA 상태로 전환

일반적으로 `notBreaching`이 권장되며, 데이터 누락으로 인한 불필요한 알림을 방지합니다.

</details>

---

7. CloudWatch Alarm Action으로 직접 실행할 수 없는 것은?
   - A) EC2 인스턴스 중지/시작/재부팅
   - B) Auto Scaling 정책 트리거
   - C) SNS 토픽으로 메시지 전송
   - D) EKS 파드 재시작

<details>
<summary>정답 보기</summary>

**정답: D) EKS 파드 재시작**

**설명:**
CloudWatch Alarm Action은 다음과 같은 AWS 네이티브 작업을 직접 실행할 수 있습니다:
- EC2 Actions: 중지, 시작, 재부팅, 복구, 종료
- Auto Scaling Actions: 스케일 아웃/인 정책 트리거
- SNS Actions: 토픽으로 메시지 전송

EKS 파드 재시작은 직접 지원되지 않으며, SNS → Lambda → Kubernetes API 체인을 통해 간접적으로 구현해야 합니다.

</details>

---

8. Container Insights에서 EKS 클러스터의 파드 재시작 횟수를 모니터링하는 메트릭은?
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>정답 보기</summary>

**정답: B) pod_number_of_container_restarts**

**설명:**
Container Insights의 주요 EKS 메트릭:
- `pod_number_of_container_restarts`: 파드 내 컨테이너 재시작 횟수
- `pod_cpu_utilization`: 파드 CPU 사용률
- `pod_memory_utilization`: 파드 메모리 사용률
- `node_cpu_utilization`: 노드 CPU 사용률
- `cluster_node_count`: 클러스터 노드 수

이 메트릭들은 `ContainerInsights` 네임스페이스에서 사용 가능합니다.

</details>

---

9. CloudWatch Alarms 비용 최적화를 위한 권장 사항으로 올바르지 않은 것은?
   - A) 중요하지 않은 알림은 Standard Resolution(60초) 사용
   - B) 여러 Metric Alarm을 Composite Alarm으로 통합
   - C) 모든 알림에 High Resolution(10초) 사용
   - D) 사용하지 않는 알림 정기적 삭제

<details>
<summary>정답 보기</summary>

**정답: C) 모든 알림에 High Resolution(10초) 사용**

**설명:**
High Resolution 알림은 Standard Resolution보다 3배 비쌉니다 ($0.30 vs $0.10/알림/월). 비용 최적화를 위해:
- Critical 알림에만 High Resolution 사용
- Warning/Info 알림은 Standard Resolution 사용
- 여러 관련 알림을 Composite Alarm으로 통합
- 사용하지 않는 알림 정기적 삭제
- Anomaly Detection은 필요한 경우에만 사용 (추가 비용 $0.30/메트릭/월)

</details>

---

10. EventBridge와 CloudWatch Alarm을 통합하여 자동 대응을 구성할 때의 이벤트 패턴에서 알림 상태 변경을 감지하는 `detail-type`은?
    - A) "AWS CloudWatch Alarm"
    - B) "CloudWatch Alarm State Change"
    - C) "CloudWatch Metric Alarm"
    - D) "AWS Alarm Notification"

<details>
<summary>정답 보기</summary>

**정답: B) "CloudWatch Alarm State Change"**

**설명:**
CloudWatch Alarm 상태 변경을 EventBridge에서 감지하는 이벤트 패턴:
```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "state": {
      "value": ["ALARM"]
    }
  }
}
```

이 패턴을 사용하면 알림 상태가 ALARM으로 변경될 때 Lambda 함수, Step Functions, SSM Automation 등을 트리거하여 자동 대응을 구현할 수 있습니다.

</details>

---

## 추가 학습 자료

- [Amazon CloudWatch Alarms Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Container Insights Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
