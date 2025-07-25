# KEDA 퀴즈

이 퀴즈는 KEDA (Kubernetes Event-driven Autoscaling)에 대한 이해도를 테스트합니다.

## 문제 1: KEDA 기본 개념

<details>
<summary>KEDA란 무엇이며 주요 이점은?</summary>

**답변:**
KEDA(Kubernetes Event-driven Autoscaling)는 Kubernetes 애플리케이션을 이벤트 기반으로 자동 확장할 수 있게 해주는 오픈 소스 프로젝트입니다.

**주요 이점:**
1. **이벤트 기반 스케일링**: 다양한 이벤트 소스(메시지 큐, 데이터베이스, 스트림 등)에 기반한 스케일링
2. **제로 스케일링**: 활동이 없을 때 0개의 복제본으로 스케일 다운하여 비용 절감
3. **다양한 스케일러 지원**: 50개 이상의 내장 스케일러와 커스텀 스케일러 지원
4. **Kubernetes 네이티브**: 기존 Kubernetes HPA와 통합
5. **클라우드 중립적**: 모든 Kubernetes 환경에서 작동
6. **간단한 배포 모델**: 단일 오퍼레이터로 쉽게 배포 가능
</details>

## 문제 2: KEDA 아키텍처

<details>
<summary>KEDA의 주요 구성 요소는?</summary>

**답변:**
- **KEDA Operator**: ScaledObject 및 ScaledJob 리소스 관리
- **Metrics Adapter**: 커스텀 메트릭을 HPA에 제공
- **Admission Webhooks**: 리소스 검증 및 변형
- **ScaledObject**: 스케일링 대상과 트리거 정의
- **ScaledJob**: Job 기반 워크로드 스케일링
- **TriggerAuthentication**: 외부 시스템 인증 정보
- **ClusterTriggerAuthentication**: 클러스터 레벨 인증
</details>

## 문제 3: 스케일러 유형

<details>
<summary>KEDA에서 지원하는 주요 스케일러들은?</summary>

**답변:**
**메시지 큐 스케일러:**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**데이터베이스 스케일러:**
- MySQL, PostgreSQL, MongoDB, Cassandra

**클라우드 서비스 스케일러:**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**기타 스케일러:**
- Cron (시간 기반), HTTP (요청 기반)
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
      bootstrapServers: kafka:9092
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: '5'
      offsetResetPolicy: latest
    authenticationRef:
      name: kafka-auth

---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
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
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: http_requests_per_second
      threshold: '100'
      query: sum(rate(http_requests_total{job="my-app"}[1m]))

---
# Twitter 메트릭 기반 스케일링
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaledobject
spec:
  scaleTargetRef:
    name: twitter-processor
  triggers:
  - type: external-push
    metadata:
      scalerAddress: twitter-scaler:8080
      metricName: twitter_mentions
      threshold: '10'

---
# Google Calendar 기반 스케일링
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaledobject
spec:
  scaleTargetRef:
    name: meeting-processor
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 9 * * 1-5"  # 평일 오전 9시
      end: "0 18 * * 1-5"   # 평일 오후 6시
      desiredReplicas: "5"
```
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
spec:
  scaleTargetRef:
    name: batch-processor
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  # 업무 시간 스케일링 (평일 9-18시)
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 9 * * 1-5"
      end: "0 18 * * 1-5"
      desiredReplicas: "10"
  
  # 야간 배치 처리 (매일 자정)
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 0 * * *"
      end: "0 6 * * *"
      desiredReplicas: "5"
  
  # 주말 최소 운영
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 10 * * 0,6"
      end: "0 16 * * 0,6"
      desiredReplicas: "2"

---
# 특별 이벤트 대응 스케일링
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: event-scaledobject
spec:
  scaleTargetRef:
    name: event-handler
  triggers:
  # 블랙 프라이데이 대비
  - type: cron
    metadata:
      timezone: America/New_York
      start: "0 0 24 11 *"  # 11월 24일 자정
      end: "59 23 24 11 *"  # 11월 24일 23:59
      desiredReplicas: "50"
```
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
spec:
  jobTargetRef:
    template:
      spec:
        template:
          spec:
            containers:
            - name: batch-processor
              image: my-batch-app:latest
              command: ["./process-batch"]
            restartPolicy: Never
        backoffLimit: 4
  pollingInterval: 30
  maxReplicaCount: 10
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      queueName: batch-queue
      host: amqp://rabbitmq:5672
      queueLength: '5'
    authenticationRef:
      name: rabbitmq-auth

---
# AWS SQS 기반 Job 스케일링
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: sqs-job-scaler
spec:
  jobTargetRef:
    template:
      spec:
        template:
          spec:
            containers:
            - name: sqs-processor
              image: sqs-worker:latest
            restartPolicy: Never
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
      queueLength: '10'
      awsRegion: us-east-1
    authenticationRef:
      name: aws-credentials
```
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
spec:
  scaleTargetRef:
    name: productpage
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  # 요청 속도 기반 스케일링
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: istio_request_rate
      threshold: '50'
      query: |
        sum(rate(istio_requests_total{
          destination_service_name="productpage",
          response_code!~"5.*"
        }[1m]))
  
  # 응답 시간 기반 스케일링
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: istio_response_time
      threshold: '0.5'
      query: |
        histogram_quantile(0.95,
          sum(rate(istio_request_duration_milliseconds_bucket{
            destination_service_name="productpage"
          }[1m])) by (le)
        ) / 1000

---
# 서비스 메시 에러율 기반 스케일링
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: error-rate-scaler
spec:
  scaleTargetRef:
    name: backend-service
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: error_rate
      threshold: '0.05'  # 5% 에러율
      query: |
        sum(rate(istio_requests_total{
          destination_service_name="backend-service",
          response_code=~"5.*"
        }[1m])) /
        sum(rate(istio_requests_total{
          destination_service_name="backend-service"
        }[1m]))
```
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
   kubectl logs -n keda -l app=keda-metrics-apiserver
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
   # 스케일러 연결 테스트
   kubectl exec -n keda deployment/keda-operator -- /manager --zap-log-level=debug
   
   # 메트릭 어댑터 상태 확인
   kubectl get apiservice v1beta1.external.metrics.k8s.io
   
   # 인증 정보 확인
   kubectl get triggerauthentication
   kubectl describe secret <auth-secret>
   ```
</details>

## 문제 10: Amazon EKS 통합

<details>
<summary>KEDA를 Amazon EKS와 통합할 때 고려사항은?</summary>

**답변:**
1. **IAM 권한 설정**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) 구성
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/keda-role
   ```

2. **AWS 서비스 통합**:
   ```yaml
   # SQS 스케일러
   - type: aws-sqs-queue
     metadata:
       queueURL: https://sqs.region.amazonaws.com/account/queue-name
       awsRegion: us-west-2
   
   # CloudWatch 스케일러
   - type: aws-cloudwatch
     metadata:
       namespace: AWS/ApplicationELB
       metricName: RequestCount
       dimensionName: LoadBalancer
       dimensionValue: app/my-alb/1234567890
   ```

3. **네트워크 고려사항**:
   - VPC 엔드포인트 사용 (비용 절약)
   - 보안 그룹 구성
   - 서브넷 라우팅 설정

4. **모니터링 통합**:
   ```yaml
   # CloudWatch Container Insights
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "8080"
     prometheus.io/path: "/metrics"
   ```

5. **Fargate 고려사항**:
   - KEDA Operator는 EC2 노드에서 실행
   - 스케일링 대상 워크로드는 Fargate 가능
   - 리소스 제한 및 스케일링 정책 조정

6. **비용 최적화**:
   - Spot 인스턴스와 함께 사용
   - 제로 스케일링으로 비용 절약
   - 적절한 스케일링 임계값 설정
</details>

---

**점수 계산:**
- 8-10개 정답: 우수 (KEDA 전문가 수준)
- 6-7개 정답: 양호 (추가 학습 권장)
- 4-5개 정답: 보통 (기본 개념 복습 필요)
- 0-3개 정답: 미흡 (전체 내용 재학습 필요)
