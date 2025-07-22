# KEDA (Kubernetes Event-driven Autoscaling) 퀴즈

이 퀴즈는 KEDA(Kubernetes Event-driven Autoscaling)에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. KEDA(Kubernetes Event-driven Autoscaling)의 주요 목적은 무엇인가요?

A. Kubernetes 클러스터의 노드 자동 스케일링  
B. 이벤트 기반 워크로드를 위한 서버리스 아키텍처 구현  
C. 외부 이벤트 소스 및 메트릭에 기반한 Kubernetes 워크로드 자동 스케일링  
D. Kubernetes 클러스터의 네트워크 트래픽 자동 조절  

<details>
<summary>정답 및 설명</summary>

**정답: C. 외부 이벤트 소스 및 메트릭에 기반한 Kubernetes 워크로드 자동 스케일링**

**설명:**
KEDA(Kubernetes Event-driven Autoscaling)의 주요 목적은 외부 이벤트 소스 및 메트릭에 기반하여 Kubernetes 워크로드를 자동으로 스케일링하는 것입니다. KEDA는 Kubernetes의 기본 Horizontal Pod Autoscaler(HPA)를 확장하여 CPU 및 메모리 사용량 외에도 다양한 외부 이벤트 소스(예: 메시지 큐, 데이터베이스 쿼리, 클라우드 이벤트 등)에 기반한 스케일링을 가능하게 합니다.

**KEDA의 주요 특징:**

1. **이벤트 기반 스케일링**: 외부 이벤트 소스의 메트릭에 기반하여 워크로드를 스케일링합니다.
2. **제로 스케일링**: 활성 이벤트가 없을 때 워크로드를 0으로 스케일 다운하고, 이벤트가 발생하면 자동으로 스케일 업합니다.
3. **다양한 스케일러 지원**: 다양한 이벤트 소스(AWS SQS, Azure Service Bus, Kafka, RabbitMQ, Prometheus 등)에 대한 스케일러를 제공합니다.
4. **HPA 통합**: Kubernetes의 기본 HPA와 통합되어 작동합니다.
5. **커스텀 스케일러**: 사용자 정의 스케일러를 개발하여 확장할 수 있습니다.

**KEDA 아키텍처:**

KEDA는 두 가지 주요 구성 요소로 이루어져 있습니다:

1. **Operator/Controller**: Kubernetes 컨트롤러로, ScaledObject 및 ScaledJob CRD를 감시하고 HPA를 생성/관리합니다.
2. **Metrics Adapter**: Kubernetes 메트릭 API를 구현하여 외부 메트릭을 HPA에 제공합니다.

**KEDA 작동 방식:**

1. 사용자가 ScaledObject 또는 ScaledJob CRD를 생성합니다.
2. KEDA 컨트롤러가 이를 감지하고 HPA를 생성합니다.
3. KEDA 메트릭 어댑터가 외부 이벤트 소스에서 메트릭을 수집합니다.
4. HPA가 메트릭에 기반하여 워크로드를 스케일링합니다.
5. 메트릭이 임계값 이하로 떨어지면 KEDA가 워크로드를 0으로 스케일 다운할 수 있습니다.

**KEDA 사용 예시:**

RabbitMQ 큐 길이에 기반한 스케일링:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: rabbitmq-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rabbitmq-consumer
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: hello
      host: rabbitmq
      queueLength: "5"
```

**KEDA의 이점:**

1. **효율적인 리소스 사용**: 필요할 때만 리소스를 사용하고, 필요하지 않을 때는 0으로 스케일 다운합니다.
2. **비용 절감**: 사용하지 않는 워크로드에 대한 리소스 비용을 절약할 수 있습니다.
3. **이벤트 기반 아키텍처**: 이벤트 기반 및 메시지 기반 아키텍처에 적합합니다.
4. **서버리스 경험**: Kubernetes에서 서버리스와 유사한 경험을 제공합니다.
5. **다양한 이벤트 소스 지원**: 다양한 외부 시스템과의 통합을 지원합니다.

**다른 옵션들의 문제점:**
- A. Kubernetes 클러스터의 노드 자동 스케일링: 이는 Cluster Autoscaler의 역할입니다.
- B. 이벤트 기반 워크로드를 위한 서버리스 아키텍처 구현: KEDA는 서버리스와 유사한 경험을 제공하지만, 완전한 서버리스 아키텍처를 구현하는 것은 아닙니다.
- D. Kubernetes 클러스터의 네트워크 트래픽 자동 조절: 이는 KEDA의 역할이 아닙니다.
</details>

### 2. KEDA에서 'ScaledObject'의 주요 목적은 무엇인가요?

A. Kubernetes 클러스터의 노드를 스케일링하기 위한 정책 정의  
B. 배치 작업(Job)의 스케일링 동작 정의  
C. 장기 실행 워크로드(Deployment, StatefulSet 등)의 스케일링 동작 정의  
D. 외부 이벤트 소스와의 연결 정의  

<details>
<summary>정답 및 설명</summary>

**정답: C. 장기 실행 워크로드(Deployment, StatefulSet 등)의 스케일링 동작 정의**

**설명:**
KEDA에서 'ScaledObject'의 주요 목적은 장기 실행 워크로드(Deployment, StatefulSet 등)의 스케일링 동작을 정의하는 것입니다. ScaledObject는 KEDA의 핵심 커스텀 리소스로, 어떤 워크로드를 스케일링할지, 어떤 트리거(이벤트 소스)에 기반하여 스케일링할지, 그리고 스케일링 파라미터(최소/최대 레플리카 수, 쿨다운 기간 등)를 정의합니다.

**ScaledObject의 주요 구성 요소:**

1. **scaleTargetRef**: 스케일링할 대상 워크로드(Deployment, StatefulSet 등)를 지정합니다.
2. **triggers**: 스케일링 결정을 위한 하나 이상의 트리거(이벤트 소스)를 정의합니다.
3. **minReplicaCount**: 최소 레플리카 수를 지정합니다(0으로 설정 가능).
4. **maxReplicaCount**: 최대 레플리카 수를 지정합니다.
5. **pollingInterval**: 메트릭을 폴링하는 간격을 지정합니다.
6. **cooldownPeriod**: 스케일 다운 전 대기 시간을 지정합니다.
7. **advanced**: 고급 스케일링 옵션을 지정합니다.

**ScaledObject 예시:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: prometheus-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 30
  cooldownPeriod: 300
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-server.monitoring.svc.cluster.local
      metricName: http_requests_total
      threshold: '100'
      query: sum(rate(http_requests_total{deployment="my-deployment"}[2m]))
```

**ScaledObject vs ScaledJob:**

KEDA는 두 가지 주요 스케일링 리소스를 제공합니다:

1. **ScaledObject**: 장기 실행 워크로드(Deployment, StatefulSet 등)의 스케일링에 사용됩니다.
2. **ScaledJob**: 배치 작업(Job)의 스케일링에 사용됩니다. 이벤트가 발생할 때마다 새 Job을 생성합니다.

**ScaledObject 작동 방식:**

1. ScaledObject가 생성되면 KEDA 컨트롤러가 이를 감지합니다.
2. 컨트롤러는 HPA(Horizontal Pod Autoscaler)를 생성하고 KEDA 메트릭 서버를 통해 외부 메트릭을 제공합니다.
3. HPA는 제공된 메트릭에 기반하여 대상 워크로드의 레플리카 수를 조정합니다.
4. 메트릭이 임계값 이하로 떨어지면 KEDA는 워크로드를 minReplicaCount(0 포함)로 스케일 다운할 수 있습니다.

**다양한 트리거 유형 예시:**

1. **Kafka 트리거**:
```yaml
triggers:
- type: kafka
  metadata:
    bootstrapServers: kafka.svc:9092
    consumerGroup: my-group
    topic: my-topic
    lagThreshold: "10"
```

2. **AWS SQS 트리거**:
```yaml
triggers:
- type: aws-sqs-queue
  metadata:
    queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
    queueLength: "5"
    awsRegion: us-east-1
```

3. **Prometheus 트리거**:
```yaml
triggers:
- type: prometheus
  metadata:
    serverAddress: http://prometheus-server
    metricName: http_requests_total
    threshold: '100'
    query: sum(rate(http_requests_total{deployment="my-deployment"}[2m]))
```

4. **CPU 트리거**:
```yaml
triggers:
- type: cpu
  metadata:
    type: Utilization
    value: "50"
```

**고급 스케일링 옵션:**
```yaml
spec:
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 100
            periodSeconds: 15
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 100
            periodSeconds: 15
          - type: Pods
            value: 4
            periodSeconds: 15
          selectPolicy: Max
```

**다른 옵션들의 문제점:**
- A. Kubernetes 클러스터의 노드를 스케일링하기 위한 정책 정의: 이는 Cluster Autoscaler의 역할입니다.
- B. 배치 작업(Job)의 스케일링 동작 정의: 이는 ScaledJob의 역할입니다.
- D. 외부 이벤트 소스와의 연결 정의: 이는 ScaledObject의 일부 기능이지만, 주요 목적은 아닙니다.
</details>
