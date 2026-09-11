# KEDA 퀴즈

> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 KEDA (Kubernetes Event-driven Autoscaling)에 대한 이해도를 테스트합니다.

## 문제 1: KEDA 기본 개념

<details>
<summary>KEDA란 무엇이며 주요 이점은?</summary>

**답변:**
KEDA(Kubernetes Event-driven Autoscaling)는 Kubernetes 애플리케이션을 이벤트 기반으로 자동 확장할 수 있게 해주는 오픈 소스 프로젝트입니다.

**주요 이점:**
1. **이벤트 기반 스케일링**: 다양한 이벤트 소스(메시지 큐, 데이터베이스, 스트림 등)에 기반한 스케일링
2. **제로 스케일링**: 지원 트리거가 최소 복제본·활성화 임계값·쿨다운에 따라 워크로드를 활성화·비활성화합니다.
3. **다양한 스케일러 지원**: 50개 이상의 내장 스케일러와 커스텀 스케일러 지원
4. **Kubernetes 네이티브**: 기존 Kubernetes HPA와 통합
5. **클라우드 중립적**: 필요한 API·인증·통신 경로를 갖춘 호환 Kubernetes 환경에서 실행합니다.
6. **배포 모델**: 기본 설치는 오퍼레이터·메트릭 API 서버·어드미션 웹훅을 포함합니다.

KEDA2.20 예제의 공개 Kubernetes 테스트 범위는1.33–1.35입니다. Kubernetes1.37 HPA도 object/external 메트릭의 제로 스케일링을 beta로 지원하므로 KEDA만 가능한 기능은 아닙니다.
</details>

## 문제 2: KEDA 아키텍처

<details>
<summary>KEDA의 주요 구성 요소는?</summary>

**답변:**
- **KEDA Operator**: ScaledObject 및 ScaledJob 리소스 관리
- **Metrics Adapter**: Kubernetes API 집계와 오퍼레이터 메트릭 서비스를 통해 외부 메트릭을 HPA에 제공합니다.
- **Admission Webhooks**: 지원하는 KEDA 리소스 구성을 검증합니다.
- **ScaledObject**: 스케일링 대상과 트리거 정의
- **ScaledJob**: 오퍼레이터가 Job을 생성하며 HPA로 해당 Job을 스케일링하지 않습니다.
- **TriggerAuthentication**: 외부 시스템 인증 정보
- **ClusterTriggerAuthentication**: 클러스터 레벨 인증

ScaledObject는 KEDA가 활성화·제로 처리를, HPA가 0보다 큰 복제본을 관리합니다. 폴링·HPA 동기화·메트릭 캐시는 다릅니다. 워크로드당 스케일링 소유자는 하나여야 합니다.
</details>

## 문제 3: 스케일러 유형

<details>
<summary>KEDA에서 지원하는 주요 스케일러들은?</summary>

**답변:**
**메시지 큐 스케일러:**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**데이터베이스 스케일러:**
- MySQL, PostgreSQL, MongoDB

**클라우드 서비스 스케일러:**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**기타 스케일러:**
- Cron(시간 기반), metrics-api(숫자 HTTP 엔드포인트); 요청 가로채기·버퍼링은 별도 HTTP add-on 역할
- CPU/Memory, External Push

**커스텀 스케일러:**
- External Scaler를 통한 사용자 정의 메트릭
</details>

## 문제 4: ScaledObject 구성

<details>
<summary>Kafka 기반 ScaledObject 구성 예시는?</summary>

**답변:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: kafka-consumer
  minReplicaCount: 0
  maxReplicaCount: 30
  pollingInterval: 30
  cooldownPeriod: 300
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka.default.svc.cluster.local:9093
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: '5'
      offsetResetPolicy: latest
      tls: enable
    authenticationRef:
      name: kafka-auth
---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
  namespace: default
spec:
  secretTargetRef:
  - parameter: sasl
    name: kafka-secrets
    key: sasl
  - parameter: username
    name: kafka-secrets
    key: username
  - parameter: password
    name: kafka-secrets
    key: password
```

기존 TLS Kafka 리스너·신뢰 CA와 유효한 SASL 설정·자격 증명의 kafka-secrets를 가정합니다. 사설 CA라면 CA 참조를 추가하세요. 소비자 애플리케이션의 인증·오프셋 동작도 맞아야 합니다. 기본 allowIdleConsumers=false에서는 복제본 수가 파티션 수로 제한되며 새 그룹의 latest/잘못된 오프셋에는 활성화 주의점이 있습니다.
</details>

## 문제 5: 커스텀 메트릭 스케일링

<details>
<summary>Prometheus 메트릭을 사용한 커스텀 스케일링 구성은?</summary>

**답변:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: prometheus-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '100'
      query: sum(rate(http_requests_total{job="my-app"}[1m]))
      ignoreNullValues: 'false'
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: twitter-processor
  triggers:
  - type: metrics-api
    metadata:
      url: http://twitter-metrics-collector.default.svc.cluster.local/metrics
      targetValue: '10'
      valueLocation: tweet_count
  minReplicaCount: 1
  maxReplicaCount: 20
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: calendar-processor
  triggers:
  - type: metrics-api
    metadata:
      url: http://calendar-metrics-collector.default.svc.cluster.local/metrics
      targetValue: '1'
      valueLocation: upcoming_events
  minReplicaCount: 1
  maxReplicaCount: 10
```

본문 HTTP 수집기를 사용하는 별도의 대안들입니다. 고정 Cron은 Google Calendar를 조회하지 않고 external-push에는 실제 KEDA gRPC 서비스가 필요합니다. collector는 독립적으로 유지하고 누락·오래된 메트릭은 0이 아닌 오류로 처리하세요.
</details>

## 문제 6: Cron 기반 스케일링

<details>
<summary>시간 기반 스케일링을 구현하는 방법은?</summary>

**답변:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: batch-processor
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '10'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 0 * * *
      end: 0 6 * * *
      desiredReplicas: '5'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 10 * * 0,6
      end: 0 16 * * 0,6
      desiredReplicas: '2'
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: event-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: event-handler
  triggers:
  - type: cron
    metadata:
      timezone: America/New_York
      start: 0 0 24 11 *
      end: 59 23 24 11 *
      desiredReplicas: '50'
```

Cron 구간은 복제본 하한을 제안하고 HPA는 합산이 아닌 가장 큰 제안을 선택합니다. 제로 축소는 쿨다운·컨트롤러 실행을 기다립니다. 두 번째 예제는 매년11월24일 일정이며 블랙 프라이데이를 자동 계산하지 않습니다. Cron에는 연도 필드가 없으므로 일회성 일정은 사용 후 재검토·제거해야 합니다.
</details>

## 문제 7: ScaledJob 구성

<details>
<summary>Job 기반 워크로드 스케일링 구성은?</summary>

**답변:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: batch-job-scaler
  namespace: default
spec:
  jobTargetRef:
    backoffLimit: 4
    template:
      spec:
        containers:
        - name: batch-processor
          image: my-batch-app:latest
          command:
          - ./process-batch
        restartPolicy: Never
  pollingInterval: 30
  maxReplicaCount: 10
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: batch-queue
      mode: QueueLength
      value: '5'
    authenticationRef:
      name: rabbitmq-auth
---
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: sqs-job-scaler
  namespace: default
spec:
  jobTargetRef:
    backoffLimit: 4
    template:
      spec:
        containers:
        - name: sqs-processor
          image: sqs-worker:latest
        restartPolicy: Never
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
      queueLength: '10'
      awsRegion: us-east-1
    authenticationRef:
      name: aws-credentials
  maxReplicaCount: 10
```

본문의 rabbitmq-auth·credentials와 aws-credentials(provider: aws, identityOwner: keda)를 해당 큐에 맞춰 사용합니다. 실제 worker 이미지·소비자 인증·승인·가시성 시간 제한·멱등성을 준비하세요. jobTargetRef는 template 하나를 갖는 JobSpec이며 ScaledJob은 HPA를 사용하지 않습니다.
</details>

## 문제 8: Istio 메트릭 스케일링

<details>
<summary>Istio 서비스 메시 메트릭을 사용한 스케일링은?</summary>

**답변:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: productpage
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '50'
      query: "sum(rate(istio_requests_total{\n  reporter=\"destination\",\n      \
        \    destination_service_namespace=\"default\",\n          destination_service_name=\"\
        productpage\",\n  response_code!~\"5.*\"\n}[1m]))\n"
      ignoreNullValues: 'false'
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '0.5'
      query: "histogram_quantile(0.95,\n  sum(rate(istio_request_duration_milliseconds_bucket{\n\
        \    reporter=\"destination\",\n          destination_service_namespace=\"\
        default\",\n          destination_service_name=\"productpage\"\n  }[1m]))\
        \ by (le)\n) / 1000\n"
      ignoreNullValues: 'false'
    metricType: Value
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: error-rate-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: backend-service
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '0.05'
      query: (sum(rate(istio_requests_total{reporter="destination",destination_service_namespace="default",destination_service_name="backend-service",response_code=~"5.*"}[2m]))
        or vector(0)) / clamp_min(sum(rate(istio_requests_total{reporter="destination",destination_service_namespace="default",destination_service_name="backend-service"}[2m])),
        0.001)
      ignoreNullValues: 'false'
    metricType: Value
  minReplicaCount: 1
  maxReplicaCount: 10
```

전체 RPS는 AverageValue(전체값/목표값)를 사용합니다. 서비스 전체 p95 지연·오류 비율은 Value(현재 복제본×메트릭/목표값)를 사용하므로 피드백 방식이 다릅니다. 지정한 네임스페이스의 destination 메트릭과 대표성 있는 비어 있지 않은 표본을 가정합니다. 누락·NaN을 처리하고 확장을 제한하며 복제본 추가가 실제 도움이 되는지 검증하세요. 지연·오류가 하위 시스템에서 발생할 수 있어 알림 신호가 더 적합할 수 있으며 운영 스케일링 효과를 실측하지 않았습니다.
</details>

## 문제 9: 모니터링 및 문제 해결

<details>
<summary>KEDA의 스케일링 활동을 모니터링하는 방법은?</summary>

**답변:**
1. **KEDA 메트릭 확인**:
   ```bash
   kubectl get scaledobject
   kubectl describe scaledobject <name>
   kubectl get hpa
   ```

2. **KEDA 로그 확인**:
   ```bash
   kubectl logs -n keda -l app=keda-operator
   kubectl logs -n keda -l app=keda-operator-metrics-apiserver
   ```

3. **이벤트 모니터링**:
   ```bash
   kubectl get events --field-selector involvedObject.name=<scaledobject-name>
   ```

4. **Prometheus 메트릭**:
   ```promql
   # KEDA 스케일러 메트릭
   keda_scaler_metrics_value
   keda_scaled_object_paused
   keda_scaled_object_errors_total
   
   # HPA 메트릭
   kube_horizontalpodautoscaler_status_current_replicas
   kube_horizontalpodautoscaler_status_desired_replicas
   ```

5. **일반적인 문제 해결**:
   ```bash
   # 기존 오퍼레이터 진단 로그 확인
   kubectl logs -n keda deployment/keda-operator --since=10m
   
   # 메트릭 어댑터 상태 확인
   kubectl get apiservice v1beta1.external.metrics.k8s.io
   
   # 인증 정보 확인
   kubectl get triggerauthentication
   kubectl get secret <auth-secret> -o json | jq '{name: .metadata.name, type: .type, keys: ((.data // {}) | keys)}'
   ```

오퍼레이터 Pod 안에서 /manager를 하나 더 시작하는 명령은 연결 시험이 아니므로 제거했습니다. 기존 로그·리소스 조건·APIService 상태를 확인하세요. KEDA 메트릭은2.20에서 확인했으며 HPA 복제본 메트릭에는 kube-state-metrics와 구성된 스크레이퍼가 필요합니다.
</details>

## 문제 10: Amazon EKS 통합

<details>
<summary>KEDA를 Amazon EKS와 통합할 때 고려사항은?</summary>

**답변:**
1. **IAM 권한 설정**:
   ```yaml
   serviceAccount:
     operator:
       create: true
       name: keda-operator
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/keda-role
         eks.amazonaws.com/sts-regional-endpoints: 'true'
   ```

2. **AWS 서비스 통합**:
   ```yaml
   - type: aws-sqs-queue
     metadata:
       queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/my-queue
       awsRegion: us-west-2
       queueLength: '5'
     authenticationRef:
       name: aws-credentials
   - type: aws-cloudwatch
     metadata:
       namespace: AWS/ApplicationELB
       metricName: RequestCount
       dimensionName: LoadBalancer
       dimensionValue: app/my-alb/1234567890
       awsRegion: us-west-2
       targetMetricValue: '100'
       minMetricValue: '0'
       metricStat: Sum
       metricStatPeriod: '60'
       metricCollectionTime: '300'
     authenticationRef:
       name: aws-credentials
   ```

3. **네트워크 고려사항**:
   - 목적지에 맞는 VPC 엔드포인트·DNS·경로·정책과 NAT·엔드포인트·AZ 총비용을 평가합니다. 절감 효과는 워크로드에 따라 다릅니다.
   - 보안 그룹 구성
   - 서브넷 라우팅 설정

4. **모니터링 통합**:
   ```yaml
   annotations:
     prometheus.io/scrape: 'true'
     prometheus.io/port: '8080'
     prometheus.io/path: /metrics
   ```

5. **Fargate 고려사항**:
   - EC2는 흔한 KEDA 배치 선택이지만 보편적인 프로토콜 요구사항은 아닙니다. 컴퓨팅 배치·API 집계 도달성·웹훅을 검증하세요.
   - 조건을 충족한 대상은 적절한 프로파일·용량으로 Fargate를 사용할 수 있습니다. EKS Pod Identity는 Fargate를 지원하지 않으므로 IRSA 등 적용 가능한 방식을 사용하세요.
   - 리소스 제한 및 스케일링 정책 조정

6. **비용 최적화**:
   - Spot 인스턴스와 함께 사용
   - 제로 스케일링으로 비용 절약
   - 적절한 스케일링 임계값 설정

트리거 목록 YAML은 별도 ScaledObject에 넣는 조각이며 본문의 aws-credentials 인증을 가정합니다. CloudWatch RequestCount의 Sum/60초는 RPS가 아닌 기간별 건수입니다. IRSA에는 올바르게 제한된 기존 OIDC 신뢰·조회 권한이 필요하고 소비자 권한은 별도입니다. 스크레이프 주석만으로 CloudWatch Container Insights가 설치·구성되지는 않으며 수집기·IAM·내보내기 목적지를 설정해야 합니다. 워크로드가0개가 되어도 노드나 모든 비용이 자동 제거되지는 않습니다.
</details>

---

**점수 계산:**
- 8-10개 정답: 우수 (KEDA 전문가 수준)
- 6-7개 정답: 양호 (추가 학습 권장)
- 4-5개 정답: 보통 (기본 개념 복습 필요)
- 0-3개 정답: 미흡 (전체 내용 재학습 필요)
