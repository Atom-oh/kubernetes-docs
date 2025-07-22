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
### 3. KEDA에서 'ScaledJob'의 주요 목적은 무엇인가요?

A. 장기 실행 워크로드의 스케일링 동작 정의  
B. 이벤트 기반으로 Kubernetes Job을 생성하고 스케일링  
C. 클러스터 노드의 스케일링 일정 정의  
D. 주기적인 백업 작업 자동화  

<details>
<summary>정답 및 설명</summary>

**정답: B. 이벤트 기반으로 Kubernetes Job을 생성하고 스케일링**

**설명:**
KEDA에서 'ScaledJob'의 주요 목적은 이벤트 기반으로 Kubernetes Job을 생성하고 스케일링하는 것입니다. ScaledJob은 외부 이벤트 소스(예: 메시지 큐, 데이터베이스 쿼리 등)에서 이벤트가 발생할 때마다 새로운 Kubernetes Job을 생성하여 해당 이벤트를 처리합니다. 이는 배치 처리 워크로드에 특히 유용하며, 각 이벤트나 메시지를 독립적인 Job으로 처리할 수 있게 합니다.

**ScaledJob의 주요 구성 요소:**

1. **jobTargetRef**: 생성할 Job의 템플릿을 지정합니다.
2. **triggers**: 스케일링 결정을 위한 하나 이상의 트리거(이벤트 소스)를 정의합니다.
3. **maxReplicaCount**: 동시에 실행할 수 있는 최대 Job 수를 지정합니다.
4. **pollingInterval**: 메트릭을 폴링하는 간격을 지정합니다.
5. **successfulJobsHistoryLimit**: 유지할 성공한 Job의 수를 지정합니다.
6. **failedJobsHistoryLimit**: 유지할 실패한 Job의 수를 지정합니다.
7. **scalingStrategy**: Job 생성 전략을 지정합니다.

**ScaledJob 예시:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: rabbitmq-consumer-job
  namespace: default
spec:
  jobTargetRef:
    template:
      spec:
        containers:
        - name: rabbitmq-consumer
          image: rabbitmq-consumer:latest
          imagePullPolicy: Always
        restartPolicy: Never
  pollingInterval: 30
  maxReplicaCount: 30
  successfulJobsHistoryLimit: 10
  failedJobsHistoryLimit: 10
  triggers:
  - type: rabbitmq
    metadata:
      queueName: hello
      host: amqp://guest:guest@rabbitmq:5672/
      queueLength: "5"
```

**ScaledJob vs ScaledObject:**

1. **ScaledJob**:
   - 각 이벤트/메시지에 대해 새로운 Job을 생성합니다.
   - 작업이 완료되면 Job이 종료됩니다.
   - 배치 처리 워크로드에 적합합니다.
   - 각 Job은 독립적으로 실행되며 완료 후 종료됩니다.

2. **ScaledObject**:
   - 기존 워크로드(Deployment, StatefulSet 등)의 레플리카 수를 조정합니다.
   - 워크로드는 계속 실행됩니다.
   - 장기 실행 서비스에 적합합니다.
   - 파드는 계속 실행되며 여러 이벤트/메시지를 처리할 수 있습니다.

**ScaledJob 작동 방식:**

1. ScaledJob이 생성되면 KEDA 컨트롤러가 이를 감지합니다.
2. 컨트롤러는 지정된 트리거에서 메트릭을 주기적으로 폴링합니다.
3. 이벤트(예: 메시지 큐에 메시지 도착)가 감지되면 컨트롤러는 새로운 Job을 생성합니다.
4. 여러 이벤트가 감지되면 maxReplicaCount까지 여러 Job을 병렬로 생성할 수 있습니다.
5. 각 Job은 완료 후 종료되며, 성공/실패 이력이 지정된 한도까지 유지됩니다.

**스케일링 전략:**

ScaledJob은 다양한 스케일링 전략을 지원합니다:

```yaml
spec:
  scalingStrategy:
    strategy: "custom"  # 또는 "default", "accurate"
    customScalingQueueLengthDeduction: 1
    customScalingRunningJobPercentage: "0.5"
    pendingPodConditions:
      - "Ready"
      - "PodScheduled"
      - "ContainersReady"
```

1. **default**: 기본 전략으로, 큐 길이에 따라 Job을 생성합니다.
2. **accurate**: 더 정확한 스케일링을 위해 실행 중인 Job 수를 고려합니다.
3. **custom**: 사용자 정의 스케일링 로직을 적용합니다.

**ScaledJob 사용 사례:**

1. **메시지 큐 처리**: 각 메시지를 독립적인 Job으로 처리합니다.
2. **배치 데이터 처리**: 데이터 배치를 개별 Job으로 처리합니다.
3. **이벤트 기반 워크플로우**: 외부 이벤트에 반응하여 워크플로우를 실행합니다.
4. **분산 작업 처리**: 작업을 여러 Job으로 분산하여 병렬 처리합니다.

**다양한 트리거 유형 예시:**

1. **Azure Queue Storage 트리거**:
```yaml
triggers:
- type: azure-queue
  metadata:
    queueName: myqueue
    connectionFromEnv: AzureWebJobsStorage
    queueLength: "5"
```

2. **Kafka 트리거**:
```yaml
triggers:
- type: kafka
  metadata:
    bootstrapServers: kafka.svc:9092
    consumerGroup: my-group
    topic: my-topic
    lagThreshold: "10"
```

**다른 옵션들의 문제점:**
- A. 장기 실행 워크로드의 스케일링 동작 정의: 이는 ScaledObject의 역할입니다.
- C. 클러스터 노드의 스케일링 일정 정의: 이는 Cluster Autoscaler의 역할입니다.
- D. 주기적인 백업 작업 자동화: 이는 CronJob의 역할이며, ScaledJob은 이벤트 기반 작업에 중점을 둡니다.
</details>

### 4. KEDA에서 'TriggerAuthentication'의 주요 목적은 무엇인가요?

A. 사용자가 KEDA API에 접근하기 위한 인증 관리  
B. 외부 이벤트 소스에 접근하기 위한 인증 정보 관리  
C. Kubernetes 클러스터에 대한 인증 자동화  
D. 트리거 이벤트의 유효성 검증  

<details>
<summary>정답 및 설명</summary>

**정답: B. 외부 이벤트 소스에 접근하기 위한 인증 정보 관리**

**설명:**
KEDA에서 'TriggerAuthentication'의 주요 목적은 외부 이벤트 소스에 접근하기 위한 인증 정보를 관리하는 것입니다. TriggerAuthentication은 ScaledObject나 ScaledJob이 외부 서비스(예: 메시지 큐, 데이터베이스, 클라우드 서비스 등)에 연결하여 메트릭을 수집할 때 필요한 인증 정보를 안전하게 저장하고 참조할 수 있게 해주는 커스텀 리소스입니다.

**TriggerAuthentication의 주요 특징:**

1. **인증 정보 분리**: 스케일링 정의(ScaledObject/ScaledJob)와 인증 정보를 분리하여 보안을 강화합니다.
2. **재사용성**: 동일한 인증 정보를 여러 스케일링 정의에서 재사용할 수 있습니다.
3. **다양한 인증 방법 지원**: 시크릿, 환경 변수, 파드 ID, 인증 정보 맵 등 다양한 방법으로 인증 정보를 제공할 수 있습니다.
4. **네임스페이스 범위**: TriggerAuthentication은 네임스페이스 범위의 리소스입니다.

**TriggerAuthentication 예시:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: rabbitmq-auth
  namespace: default
spec:
  secretTargetRef:
  - parameter: host
    name: rabbitmq-secret
    key: host
  - parameter: username
    name: rabbitmq-secret
    key: username
  - parameter: password
    name: rabbitmq-secret
    key: password
```

**TriggerAuthentication 사용 예시:**
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
  triggers:
  - type: rabbitmq
    metadata:
      queueName: hello
      queueLength: "5"
    authenticationRef:
      name: rabbitmq-auth
```

**인증 정보 제공 방법:**

1. **Secret 참조**:
```yaml
spec:
  secretTargetRef:
  - parameter: connectionString
    name: my-secret
    key: connectionString
```

2. **환경 변수 참조**:
```yaml
spec:
  env:
  - parameter: connectionString
    name: CONNECTION_STRING
    containerName: my-container
```

3. **파드 ID 참조** (AWS IAM Role for Service Account 등):
```yaml
spec:
  podIdentity:
    provider: aws-eks
```

4. **인증 정보 맵 참조**:
```yaml
spec:
  hashiCorpVault:
    address: https://vault.example.com
    authentication: kubernetes
    role: keda
    mount: kubernetes
    secrets:
    - parameter: connectionString
      key: secret/data/keda/redis
      path: connectionString
```

**ClusterTriggerAuthentication:**

네임스페이스 범위를 넘어 클러스터 전체에서 사용할 수 있는 인증 정보를 정의하려면 ClusterTriggerAuthentication을 사용할 수 있습니다:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ClusterTriggerAuthentication
metadata:
  name: cluster-rabbitmq-auth
spec:
  secretTargetRef:
  - parameter: host
    name: rabbitmq-secret
    key: host
    namespace: keda
```

**다양한 인증 시나리오:**

1. **Azure Service Bus 인증**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: azure-servicebus-auth
spec:
  podIdentity:
    provider: azure-workload-identity
```

2. **AWS SQS 인증**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-sqs-auth
spec:
  podIdentity:
    provider: aws-eks
```

3. **Kafka SASL 인증**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
spec:
  secretTargetRef:
  - parameter: sasl
    name: kafka-secret
    key: sasl
  - parameter: username
    name: kafka-secret
    key: username
  - parameter: password
    name: kafka-secret
    key: password
```

**인증 정보 보안 모범 사례:**

1. **최소 권한 원칙**: 외부 서비스에 접근하는 데 필요한 최소한의 권한만 부여합니다.
2. **Secret 교체**: 정기적으로 인증 정보를 교체합니다.
3. **네임스페이스 분리**: 중요한 인증 정보는 별도의 네임스페이스에 저장합니다.
4. **RBAC 제한**: TriggerAuthentication에 대한 접근을 제한합니다.
5. **클라우드 제공자 IAM 통합**: 가능한 경우 Secret 대신 클라우드 제공자의 IAM 통합(예: AWS IRSA, Azure Workload Identity)을 사용합니다.

**다른 옵션들의 문제점:**
- A. 사용자가 KEDA API에 접근하기 위한 인증 관리: KEDA API 접근은 Kubernetes RBAC로 관리되며, TriggerAuthentication의 역할이 아닙니다.
- C. Kubernetes 클러스터에 대한 인증 자동화: 이는 Kubernetes 인증 메커니즘의 역할이며, TriggerAuthentication의 역할이 아닙니다.
- D. 트리거 이벤트의 유효성 검증: TriggerAuthentication은 인증에 중점을 두며, 이벤트 유효성 검증은 다른 메커니즘을 통해 처리됩니다.
</details>
### 5. KEDA에서 'zero to one' 스케일링이란 무엇인가요?

A. 워크로드를 0개에서 1개의 레플리카로 스케일 업하는 기능  
B. 첫 번째 이벤트가 발생할 때만 스케일링하는 기능  
C. 스케일링 시작 시 1초 이내에 스케일 업하는 기능  
D. 하나의 이벤트에 대해 하나의 파드만 생성하는 기능  

<details>
<summary>정답 및 설명</summary>

**정답: A. 워크로드를 0개에서 1개의 레플리카로 스케일 업하는 기능**

**설명:**
KEDA에서 'zero to one' 스케일링이란 워크로드를 0개에서 1개의 레플리카로 스케일 업하는 기능을 의미합니다. 이는 KEDA의 핵심 기능 중 하나로, 이벤트나 메트릭이 없을 때는 워크로드를 완전히 0으로 스케일 다운하여 리소스를 절약하고, 이벤트가 발생하면 신속하게 1개 이상의 레플리카로 스케일 업하여 이벤트를 처리할 수 있게 합니다. 이 기능은 Kubernetes의 기본 HPA(Horizontal Pod Autoscaler)가 제공하지 않는 기능으로, KEDA가 서버리스와 유사한 경험을 Kubernetes에서 제공할 수 있게 하는 중요한 요소입니다.

**'Zero to One' 스케일링의 작동 방식:**

1. **초기 상태**: ScaledObject의 minReplicaCount가 0으로 설정되어 있으면, 이벤트가 없을 때 워크로드는 0개의 레플리카로 유지됩니다.
2. **이벤트 감지**: KEDA가 외부 이벤트 소스에서 이벤트(예: 메시지 큐에 메시지 도착)를 감지합니다.
3. **활성화**: KEDA는 HPA를 통해 워크로드를 1개 이상의 레플리카로 스케일 업합니다.
4. **이벤트 처리**: 워크로드가 이벤트를 처리합니다.
5. **비활성화**: 이벤트가 모두 처리되고 일정 시간(cooldownPeriod) 동안 새 이벤트가 없으면, KEDA는 워크로드를 다시 0으로 스케일 다운합니다.

**ScaledObject 예시:**
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
  minReplicaCount: 0  # 0으로 설정하여 zero to one 스케일링 활성화
  maxReplicaCount: 10
  cooldownPeriod: 300  # 스케일 다운 전 대기 시간(초)
  pollingInterval: 30  # 메트릭 폴링 간격(초)
  triggers:
  - type: rabbitmq
    metadata:
      queueName: hello
      host: rabbitmq
      queueLength: "1"  # 큐에 메시지가 1개 이상이면 스케일 업
```

**'Zero to One' 스케일링의 이점:**

1. **비용 효율성**: 이벤트가 없을 때는 리소스를 전혀 사용하지 않아 비용을 절약할 수 있습니다.
2. **서버리스 경험**: Kubernetes에서 서버리스와 유사한 경험을 제공합니다.
3. **자동 활성화**: 이벤트가 발생하면 자동으로 워크로드가 활성화됩니다.
4. **리소스 최적화**: 필요할 때만 리소스를 사용합니다.

**'Zero to One' 스케일링 고려 사항:**

1. **콜드 스타트**: 0에서 1로 스케일 업할 때 파드 시작 시간으로 인한 지연이 발생할 수 있습니다.
2. **초기화 시간**: 애플리케이션이 시작되고 요청을 처리할 준비가 되기까지 시간이 걸릴 수 있습니다.
3. **상태 유지**: 0으로 스케일 다운되면 메모리 내 상태가 손실됩니다.
4. **연결 관리**: 데이터베이스 연결 등의 리소스를 효율적으로 관리해야 합니다.

**'Zero to One' 스케일링 최적화:**

1. **이미지 최적화**: 작은 이미지와 빠른 시작 시간을 가진 애플리케이션을 사용합니다.
2. **리소스 요청 조정**: 적절한 CPU/메모리 요청을 설정하여 빠른 스케줄링을 보장합니다.
3. **노드 준비**: 워크로드를 실행할 노드가 항상 준비되어 있도록 합니다.
4. **초기화 최적화**: 애플리케이션 초기화 시간을 최소화합니다.

**'Zero to One' 스케일링 사용 사례:**

1. **이벤트 처리기**: 간헐적으로 발생하는 이벤트를 처리하는 워크로드
2. **배치 작업**: 주기적으로 실행되는 배치 처리 작업
3. **API 백엔드**: 트래픽이 간헐적인 API 서비스
4. **데이터 처리 파이프라인**: 데이터가 도착할 때만 활성화되는 처리 파이프라인

**'Zero to One' vs 'Scale to Zero':**

- **'Zero to One'**: 0에서 1 이상으로 스케일 업하는 과정을 강조합니다.
- **'Scale to Zero'**: 1 이상에서 0으로 스케일 다운하는 과정을 강조합니다.

두 용어는 동일한 기능의 다른 측면을 설명하며, KEDA는 두 기능을 모두 제공합니다.

**다른 옵션들의 문제점:**
- B. 첫 번째 이벤트가 발생할 때만 스케일링하는 기능: KEDA는 이벤트가 발생할 때마다 필요에 따라 스케일링합니다.
- C. 스케일링 시작 시 1초 이내에 스케일 업하는 기능: 스케일링 속도는 Kubernetes 클러스터와 워크로드 특성에 따라 다르며, 1초 이내를 보장하지 않습니다.
- D. 하나의 이벤트에 대해 하나의 파드만 생성하는 기능: KEDA는 이벤트 수나 메트릭 값에 따라 여러 파드를 생성할 수 있습니다.
</details>

### 6. KEDA에서 'custom metrics'를 사용하는 주요 목적은 무엇인가요?

A. Kubernetes 클러스터의 성능 모니터링  
B. 기본 제공되지 않는 외부 시스템의 메트릭에 기반한 스케일링  
C. 사용자 정의 알림 생성  
D. 클러스터 노드의 리소스 사용량 최적화  

<details>
<summary>정답 및 설명</summary>

**정답: B. 기본 제공되지 않는 외부 시스템의 메트릭에 기반한 스케일링**

**설명:**
KEDA에서 'custom metrics'를 사용하는 주요 목적은 기본 제공되지 않는 외부 시스템의 메트릭에 기반하여 스케일링하는 것입니다. KEDA는 다양한 내장 스케일러(RabbitMQ, Kafka, Prometheus 등)를 제공하지만, 모든 시스템이나 사용 사례를 커버할 수는 없습니다. 커스텀 메트릭 스케일러를 사용하면 KEDA가 기본적으로 지원하지 않는 외부 시스템이나 사용자 정의 메트릭 소스에서 메트릭을 가져와 스케일링 결정에 사용할 수 있습니다.

**커스텀 메트릭 스케일러 유형:**

KEDA는 다음과 같은 방법으로 커스텀 메트릭을 사용할 수 있습니다:

1. **외부 스케일러(External Scaler)**: gRPC 서버를 구현하여 KEDA에 메트릭을 제공합니다.
2. **Prometheus 스케일러**: Prometheus 쿼리를 사용하여 커스텀 메트릭을 가져옵니다.
3. **Metrics API 스케일러**: Kubernetes Metrics API를 통해 제공되는 커스텀 메트릭을 사용합니다.

**외부 스케일러(External Scaler) 예시:**

1. **외부 스케일러 서버 구현**:
외부 스케일러는 KEDA의 gRPC 프로토콜을 구현한 서버로, 다음과 같은 메서드를 제공해야 합니다:
- `IsActive`: 스케일링이 필요한지 여부를 결정합니다.
- `GetMetricSpec`: 메트릭 사양을 제공합니다.
- `GetMetrics`: 현재 메트릭 값을 제공합니다.

2. **ScaledObject에서 외부 스케일러 참조**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: custom-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: external
    metadata:
      scalerAddress: my-custom-scaler.default:6000
      metricName: custom_metric
      metricThreshold: "10"
```

**Prometheus를 사용한 커스텀 메트릭 예시:**

Prometheus는 커스텀 메트릭을 수집하고 쿼리하는 데 널리 사용되는 도구입니다. KEDA는 Prometheus 쿼리 결과를 기반으로 스케일링할 수 있습니다:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: prometheus-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-server.monitoring.svc.cluster.local
      metricName: custom_metric_total
      threshold: '10'
      query: sum(rate(custom_metric_total{job="my-service"}[2m]))
```

**Twitter API를 사용한 커스텀 메트릭 예시:**

Twitter API를 사용하여 특정 해시태그의 트윗 수에 따라 스케일링하는 외부 스케일러를 구현할 수 있습니다:

1. **외부 스케일러 서비스 배포**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twitter-scaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: twitter-scaler
  template:
    metadata:
      labels:
        app: twitter-scaler
    spec:
      containers:
      - name: twitter-scaler
        image: twitter-scaler:latest
        env:
        - name: TWITTER_API_KEY
          valueFrom:
            secretKeyRef:
              name: twitter-api-secret
              key: api-key
        - name: TWITTER_API_SECRET
          valueFrom:
            secretKeyRef:
              name: twitter-api-secret
              key: api-secret
        ports:
        - containerPort: 6000
---
apiVersion: v1
kind: Service
metadata:
  name: twitter-scaler
spec:
  selector:
    app: twitter-scaler
  ports:
  - port: 6000
    targetPort: 6000
```

2. **ScaledObject 정의**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-hashtag-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: hashtag-processor
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: external
    metadata:
      scalerAddress: twitter-scaler:6000
      hashtag: kubernetes
      tweetsPerReplica: "10"
```

**Google Calendar API를 사용한 커스텀 메트릭 예시:**

Google Calendar API를 사용하여 예정된 이벤트 수에 따라 스케일링하는 외부 스케일러를 구현할 수 있습니다:

1. **외부 스케일러 서비스 배포**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calendar-scaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: calendar-scaler
  template:
    metadata:
      labels:
        app: calendar-scaler
    spec:
      containers:
      - name: calendar-scaler
        image: calendar-scaler:latest
        env:
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /secrets/google-credentials.json
        volumeMounts:
        - name: google-credentials
          mountPath: /secrets
          readOnly: true
        ports:
        - containerPort: 6000
      volumes:
      - name: google-credentials
        secret:
          secretName: google-calendar-credentials
---
apiVersion: v1
kind: Service
metadata:
  name: calendar-scaler
spec:
  selector:
    app: calendar-scaler
  ports:
  - port: 6000
    targetPort: 6000
```

2. **ScaledObject 정의**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-event-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: event-processor
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: external
    metadata:
      scalerAddress: calendar-scaler:6000
      calendarId: primary
      lookAheadMinutes: "60"
      eventsPerReplica: "5"
```

**커스텀 메트릭 스케일러 개발 고려 사항:**

1. **성능**: 스케일러는 효율적이어야 하며, KEDA의 폴링 간격마다 호출됩니다.
2. **신뢰성**: 스케일러는 안정적이어야 하며, 오류 처리 메커니즘을 포함해야 합니다.
3. **보안**: 외부 시스템에 접근하기 위한 인증 정보를 안전하게 관리해야 합니다.
4. **확장성**: 스케일러는 여러 인스턴스의 ScaledObject에서 사용될 수 있어야 합니다.
5. **모니터링**: 스케일러 자체의 성능과 동작을 모니터링해야 합니다.

**다른 옵션들의 문제점:**
- A. Kubernetes 클러스터의 성능 모니터링: 커스텀 메트릭은 주로 스케일링 결정을 위한 것이며, 일반적인 모니터링 목적으로는 Prometheus와 같은 도구를 직접 사용하는 것이 더 적합합니다.
- C. 사용자 정의 알림 생성: 알림은 주로 Prometheus Alertmanager와 같은 도구를 통해 처리됩니다.
- D. 클러스터 노드의 리소스 사용량 최적화: 이는 Cluster Autoscaler나 Kubernetes Scheduler의 역할입니다.
</details>
### 7. KEDA에서 'Istio metrics'를 활용한 스케일링의 주요 이점은 무엇인가요?

A. Istio 서비스 메시의 보안 기능 활용  
B. 트래픽 라우팅 자동화  
C. 요청 속도(requests/sec)와 같은 네트워크 수준 메트릭에 기반한 스케일링  
D. 서비스 메시 구성 자동화  

<details>
<summary>정답 및 설명</summary>

**정답: C. 요청 속도(requests/sec)와 같은 네트워크 수준 메트릭에 기반한 스케일링**

**설명:**
KEDA에서 'Istio metrics'를 활용한 스케일링의 주요 이점은 요청 속도(requests/sec)와 같은 네트워크 수준 메트릭에 기반하여 스케일링할 수 있다는 것입니다. Istio는 서비스 메시 내의 모든 트래픽에 대한 상세한 메트릭을 수집하며, KEDA는 이러한 메트릭을 활용하여 애플리케이션의 실제 트래픽 패턴에 따라 스케일링 결정을 내릴 수 있습니다. 이는 CPU나 메모리 사용량과 같은 리소스 메트릭보다 애플리케이션의 실제 부하를 더 정확하게 반영할 수 있습니다.

**Istio 메트릭 기반 스케일링의 작동 방식:**

1. **Istio 설치**: Kubernetes 클러스터에 Istio 서비스 메시를 설치합니다.
2. **Prometheus 통합**: Istio는 기본적으로 Prometheus와 통합되어 메트릭을 저장합니다.
3. **KEDA 설정**: KEDA의 Prometheus 스케일러를 사용하여 Istio 메트릭에 기반한 스케일링을 구성합니다.
4. **메트릭 쿼리**: Prometheus 쿼리를 통해 Istio가 수집한 메트릭(예: 요청 속도, 오류율 등)을 가져옵니다.
5. **스케일링 결정**: 메트릭 값에 따라 KEDA가 워크로드를 스케일링합니다.

**Istio 메트릭 기반 스케일링 예시:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-service
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.istio-system:9090
      metricName: istio_requests_per_second
      threshold: "10"
      query: sum(rate(istio_requests_total{destination_service="my-service.default.svc.cluster.local"}[2m]))
```

이 예시에서:
- Istio가 수집한 `istio_requests_total` 메트릭을 사용합니다.
- 지난 2분 동안의 초당 요청 수(rate)를 계산합니다.
- 초당 요청 수가 10을 초과하면 스케일 업합니다.

**Istio 메트릭의 종류:**

1. **요청 관련 메트릭**:
   - `istio_requests_total`: 총 요청 수
   - `istio_request_duration_milliseconds`: 요청 처리 시간
   - `istio_request_size`: 요청 크기

2. **응답 관련 메트릭**:
   - `istio_response_size`: 응답 크기
   - `istio_request_messages_total`: 요청 메시지 수 (gRPC)
   - `istio_response_messages_total`: 응답 메시지 수 (gRPC)

3. **오류 관련 메트릭**:
   - `istio_requests_total{response_code=~"5.*"}`: 5xx 오류 수
   - `istio_requests_total{response_code=~"4.*"}`: 4xx 오류 수

**다양한 스케일링 시나리오:**

1. **요청 속도 기반 스케일링**:
```yaml
triggers:
- type: prometheus
  metadata:
    serverAddress: http://prometheus.istio-system:9090
    metricName: requests_per_second
    threshold: "50"
    query: sum(rate(istio_requests_total{destination_service="my-service.default.svc.cluster.local"}[1m]))
```

2. **오류율 기반 스케일링**:
```yaml
triggers:
- type: prometheus
  metadata:
    serverAddress: http://prometheus.istio-system:9090
    metricName: error_rate
    threshold: "0.05"  # 5% 오류율
    query: sum(rate(istio_requests_total{destination_service="my-service.default.svc.cluster.local",response_code=~"5.*"}[1m])) / sum(rate(istio_requests_total{destination_service="my-service.default.svc.cluster.local"}[1m]))
```

3. **지연 시간 기반 스케일링**:
```yaml
triggers:
- type: prometheus
  metadata:
    serverAddress: http://prometheus.istio-system:9090
    metricName: p95_latency
    threshold: "500"  # 500ms
    query: histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket{destination_service="my-service.default.svc.cluster.local"}[1m])) by (le))
```

4. **특정 경로에 대한 요청 기반 스케일링**:
```yaml
triggers:
- type: prometheus
  metadata:
    serverAddress: http://prometheus.istio-system:9090
    metricName: api_requests
    threshold: "20"
    query: sum(rate(istio_requests_total{destination_service="my-service.default.svc.cluster.local",request_path=~"/api/.*"}[1m]))
```

**Istio 메트릭 기반 스케일링의 이점:**

1. **애플리케이션 중심 스케일링**: CPU나 메모리 사용량이 아닌 실제 애플리케이션 트래픽에 기반한 스케일링이 가능합니다.
2. **세분화된 메트릭**: 서비스, 경로, 메서드, 응답 코드 등 다양한 차원으로 메트릭을 필터링할 수 있습니다.
3. **선제적 스케일링**: 리소스 사용량이 증가하기 전에 트래픽 패턴에 기반하여 선제적으로 스케일링할 수 있습니다.
4. **비즈니스 메트릭 연계**: 트래픽 패턴은 종종 비즈니스 활동과 직접적으로 연관되어 있어, 비즈니스 요구에 더 잘 부합하는 스케일링이 가능합니다.

**Istio와 KEDA 통합 시 고려 사항:**

1. **메트릭 정확성**: Istio 메트릭이 정확하게 수집되고 있는지 확인해야 합니다.
2. **쿼리 최적화**: Prometheus 쿼리가 효율적이고 정확한지 확인해야 합니다.
3. **지연 시간**: 메트릭 수집과 스케일링 결정 사이에 지연이 있을 수 있습니다.
4. **리소스 사용량**: Istio와 Prometheus는 추가적인 리소스를 사용합니다.
5. **임계값 조정**: 적절한 스케일링 임계값을 찾기 위해 실험과 조정이 필요할 수 있습니다.

**다른 옵션들의 문제점:**
- A. Istio 서비스 메시의 보안 기능 활용: KEDA는 Istio의 보안 기능을 활용하는 것이 아니라 메트릭을 활용합니다.
- B. 트래픽 라우팅 자동화: 트래픽 라우팅은 Istio의 기능이며, KEDA는 스케일링에 중점을 둡니다.
- D. 서비스 메시 구성 자동화: 서비스 메시 구성은 Istio의 역할이며, KEDA는 이에 관여하지 않습니다.
</details>

### 8. KEDA에서 'cron' 스케일러의 주요 목적은 무엇인가요?

A. 주기적인 백업 작업 실행  
B. 시간 기반 스케일링 일정 정의  
C. 클러스터 유지 관리 자동화  
D. 워크로드의 자동 재시작 일정 설정  

<details>
<summary>정답 및 설명</summary>

**정답: B. 시간 기반 스케일링 일정 정의**

**설명:**
KEDA에서 'cron' 스케일러의 주요 목적은 시간 기반 스케일링 일정을 정의하는 것입니다. cron 스케일러를 사용하면 특정 시간이나 주기에 따라 워크로드를 자동으로 스케일 업하거나 스케일 다운할 수 있습니다. 이는 예측 가능한 트래픽 패턴이 있는 워크로드(예: 업무 시간 중에만 활성화되는 서비스, 특정 시간에 배치 작업을 처리하는 워크로드 등)에 특히 유용합니다.

**cron 스케일러의 작동 방식:**

1. **cron 표현식 정의**: 표준 cron 표현식을 사용하여 스케일링 일정을 정의합니다.
2. **시간 기반 활성화**: 지정된 시간에 도달하면 스케일러가 활성화됩니다.
3. **레플리카 수 설정**: 활성화되면 지정된 레플리카 수로 워크로드를 스케일링합니다.
4. **비활성화**: 지정된 시간이 지나면 스케일러가 비활성화되고, 다른 트리거가 없으면 워크로드가 스케일 다운됩니다.

**cron 스케일러 예시:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-service
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul  # 타임존 지정
      start: 30 * * * *     # 매시간 30분에 스케일 업
      end: 45 * * * *       # 매시간 45분에 스케일 다운
      desiredReplicas: "5"  # 활성화 시 5개의 레플리카로 스케일링
```

이 예시에서:
- 매시간 30분에 워크로드가 5개의 레플리카로 스케일 업됩니다.
- 매시간 45분에 워크로드가 스케일 다운됩니다(다른 트리거가 없으면 minReplicaCount로).

**cron 표현식:**

cron 표현식은 다음과 같은 형식을 따릅니다:
```
┌───────────── 분 (0 - 59)
│ ┌───────────── 시 (0 - 23)
│ │ ┌───────────── 일 (1 - 31)
│ │ │ ┌───────────── 월 (1 - 12)
│ │ │ │ ┌───────────── 요일 (0 - 6) (일요일부터 토요일까지)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

**다양한 cron 스케일링 시나리오:**

1. **업무 시간 중 스케일 업**:
```yaml
triggers:
- type: cron
  metadata:
    timezone: Asia/Seoul
    start: 0 9 * * 1-5    # 평일 오전 9시에 스케일 업
    end: 0 18 * * 1-5     # 평일 오후 6시에 스케일 다운
    desiredReplicas: "5"
```

2. **야간 배치 작업을 위한 스케일 업**:
```yaml
triggers:
- type: cron
  metadata:
    timezone: Asia/Seoul
    start: 0 1 * * *      # 매일 오전 1시에 스케일 업
    end: 30 1 * * *       # 매일 오전 1시 30분에 스케일 다운
    desiredReplicas: "3"
```

3. **주말 트래픽 증가 대비**:
```yaml
triggers:
- type: cron
  metadata:
    timezone: Asia/Seoul
    start: 0 9 * * 6,0    # 토요일과 일요일 오전 9시에 스케일 업
    end: 0 22 * * 6,0     # 토요일과 일요일 오후 10시에 스케일 다운
    desiredReplicas: "8"
```

4. **월말 처리를 위한 스케일 업**:
```yaml
triggers:
- type: cron
  metadata:
    timezone: Asia/Seoul
    start: 0 0 28-31 * *  # 매월 28-31일 자정에 스케일 업
    end: 0 6 28-31 * *    # 매월 28-31일 오전 6시에 스케일 다운
    desiredReplicas: "10"
```

**여러 트리거 조합:**

cron 스케일러는 다른 트리거와 함께 사용할 수 있습니다:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: combined-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-service
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: "5"
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-server
      metricName: http_requests_per_second
      threshold: "10"
      query: sum(rate(http_requests_total{service="my-service"}[2m]))
```

이 예시에서:
- 평일 업무 시간 중에는 기본적으로 5개의 레플리카가 유지됩니다.
- 트래픽이 증가하면 Prometheus 메트릭에 따라 최대 20개까지 스케일 업될 수 있습니다.
- 업무 시간 외에는 트래픽이 없으면 0으로 스케일 다운됩니다.

**cron 스케일러의 이점:**

1. **예측 가능한 패턴 대응**: 알려진 트래픽 패턴에 맞춰 사전에 스케일링할 수 있습니다.
2. **비용 최적화**: 필요한 시간에만 리소스를 사용하여 비용을 절약할 수 있습니다.
3. **피크 시간 준비**: 트래픽이 증가하기 전에 미리 스케일 업하여 성능 저하를 방지할 수 있습니다.
4. **정기적인 작업 처리**: 정기적으로 실행되는 배치 작업을 위한 리소스를 효율적으로 관리할 수 있습니다.

**cron 스케일러 사용 시 고려 사항:**

1. **타임존 설정**: 올바른 타임존을 지정하여 예상한 시간에 스케일링이 발생하도록 해야 합니다.
2. **중복 트리거**: 여러 cron 트리거가 겹치는 경우 동작을 이해하고 관리해야 합니다.
3. **다른 트리거와의 상호 작용**: cron 트리거와 다른 트리거(예: CPU, 메모리 등)가 함께 사용될 때의 동작을 이해해야 합니다.
4. **일정 변경**: 트래픽 패턴이 변경되면 cron 일정도 업데이트해야 합니다.

**다른 옵션들의 문제점:**
- A. 주기적인 백업 작업 실행: 백업 작업 실행은 Kubernetes CronJob의 역할이며, KEDA의 cron 스케일러는 스케일링에 중점을 둡니다.
- C. 클러스터 유지 관리 자동화: 클러스터 유지 관리는 별도의 도구나 프로세스를 통해 관리됩니다.
- D. 워크로드의 자동 재시작 일정 설정: 워크로드 재시작은 Kubernetes Deployment의 롤링 업데이트나 CronJob을 통해 관리됩니다.
</details>
### 9. KEDA와 Kubernetes HPA(Horizontal Pod Autoscaler)의 주요 차이점은 무엇인가요?

A. KEDA는 CPU와 메모리 메트릭만 지원하지만 HPA는 더 다양한 메트릭을 지원함  
B. KEDA는 외부 이벤트 소스 및 메트릭을 지원하고 0으로 스케일링이 가능하지만 HPA는 CPU/메모리 중심이며 0으로 스케일링이 불가능함  
C. KEDA는 수직 스케일링을 지원하지만 HPA는 수평 스케일링만 지원함  
D. KEDA는 클러스터 수준 스케일링을 지원하지만 HPA는 네임스페이스 수준 스케일링만 지원함  

<details>
<summary>정답 및 설명</summary>

**정답: B. KEDA는 외부 이벤트 소스 및 메트릭을 지원하고 0으로 스케일링이 가능하지만 HPA는 CPU/메모리 중심이며 0으로 스케일링이 불가능함**

**설명:**
KEDA와 Kubernetes HPA(Horizontal Pod Autoscaler)의 주요 차이점은 KEDA는 외부 이벤트 소스 및 메트릭을 지원하고 0으로 스케일링이 가능한 반면, HPA는 주로 CPU/메모리 메트릭에 중점을 두며 0으로 스케일링이 불가능하다는 것입니다. 이러한 차이점으로 인해 KEDA는 이벤트 기반 워크로드와 서버리스 시나리오에 더 적합하며, HPA는 일반적인 리소스 기반 스케일링에 적합합니다.

**KEDA와 HPA의 주요 차이점:**

1. **메트릭 소스**:
   - **KEDA**: 다양한 외부 이벤트 소스(메시지 큐, 데이터베이스, 클라우드 서비스 등)와 커스텀 메트릭을 지원합니다.
   - **HPA**: 기본적으로 CPU/메모리 메트릭을 지원하며, 메트릭 서버를 통해 일부 커스텀 메트릭을 지원할 수 있습니다.

2. **스케일 투 제로**:
   - **KEDA**: 워크로드를 0개의 레플리카로 스케일 다운할 수 있습니다(스케일 투 제로).
   - **HPA**: 최소 1개의 레플리카를 유지해야 하며, 0으로 스케일 다운할 수 없습니다.

3. **아키텍처**:
   - **KEDA**: 자체 컨트롤러와 메트릭 어댑터를 사용하며, HPA를 내부적으로 생성하고 관리합니다.
   - **HPA**: Kubernetes의 기본 컴포넌트로, 메트릭 서버에서 제공하는 메트릭을 사용합니다.

4. **사용 사례**:
   - **KEDA**: 이벤트 기반 워크로드, 서버리스 시나리오, 외부 시스템과의 통합에 적합합니다.
   - **HPA**: 리소스 사용량에 기반한 일반적인 애플리케이션 스케일링에 적합합니다.

**KEDA와 HPA 비교 예시:**

1. **HPA 예시** (CPU 사용량 기반):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicas: 1  # 최소 1개 (0으로 설정 불가)
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
```

2. **KEDA 예시** (RabbitMQ 큐 길이 기반):
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: rabbitmq-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicaCount: 0  # 0으로 스케일 다운 가능
  maxReplicaCount: 10
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: hello
      host: rabbitmq
      queueLength: "5"
```

**KEDA가 HPA를 사용하는 방식:**

KEDA는 내부적으로 HPA를 생성하고 관리합니다:

1. **ScaledObject 생성**: 사용자가 ScaledObject를 생성합니다.
2. **HPA 생성**: KEDA 컨트롤러가 해당 ScaledObject에 대한 HPA를 생성합니다.
3. **메트릭 제공**: KEDA 메트릭 서버가 외부 메트릭을 HPA에 제공합니다.
4. **스케일링 결정**: HPA가 메트릭에 기반하여 스케일링 결정을 내립니다.
5. **스케일 투 제로**: KEDA 컨트롤러가 필요한 경우 워크로드를 0으로 스케일 다운합니다.

**KEDA와 HPA 함께 사용하기:**

KEDA와 HPA를 함께 사용하여 다양한 메트릭에 기반한 스케일링을 구현할 수 있습니다:

```yaml
# HPA로 CPU/메모리 기반 스케일링
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: resource-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50

---
# KEDA로 외부 메트릭 기반 스케일링
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: external-scaler
  annotations:
    autoscaling.keda.sh/paused: "true"  # HPA와 충돌 방지를 위해 일시 중지
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
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

**KEDA의 추가 기능:**

1. **ScaledJob**: 이벤트 기반으로 Kubernetes Job을 생성합니다.
2. **TriggerAuthentication**: 외부 시스템에 대한 인증 정보를 관리합니다.
3. **다양한 스케일러**: 50개 이상의 내장 스케일러를 제공합니다.
4. **외부 스케일러**: gRPC를 통한 커스텀 스케일러 구현을 지원합니다.

**HPA의 추가 기능:**

1. **다중 메트릭**: 여러 메트릭에 기반한 스케일링을 지원합니다.
2. **스케일링 동작 구성**: 스케일 업/다운 동작을 세밀하게 구성할 수 있습니다.
3. **컨테이너 리소스 메트릭**: 특정 컨테이너의 리소스 메트릭에 기반한 스케일링을 지원합니다.

**어떤 것을 선택해야 할까?**

1. **KEDA 선택 시나리오**:
   - 외부 이벤트 소스에 기반한 스케일링이 필요한 경우
   - 0으로 스케일 다운이 필요한 경우
   - 이벤트 기반 워크로드나 서버리스 시나리오
   - 다양한 외부 시스템과의 통합이 필요한 경우

2. **HPA 선택 시나리오**:
   - CPU/메모리와 같은 기본 리소스 메트릭에 기반한 스케일링이 충분한 경우
   - 최소 1개의 레플리카를 항상 유지해야 하는 경우
   - 간단한 스케일링 요구 사항이 있는 경우
   - Kubernetes 기본 기능만 사용하고 싶은 경우

**다른 옵션들의 문제점:**
- A. KEDA는 CPU와 메모리 메트릭만 지원하지만 HPA는 더 다양한 메트릭을 지원함: 실제로는 반대입니다. KEDA가 더 다양한 메트릭을 지원합니다.
- C. KEDA는 수직 스케일링을 지원하지만 HPA는 수평 스케일링만 지원함: 둘 다 수평 스케일링만 지원합니다. 수직 스케일링은 Vertical Pod Autoscaler(VPA)의 역할입니다.
- D. KEDA는 클러스터 수준 스케일링을 지원하지만 HPA는 네임스페이스 수준 스케일링만 지원함: 둘 다 워크로드 수준의 스케일링을 지원하며, 클러스터 수준 스케일링은 Cluster Autoscaler의 역할입니다.
</details>

### 10. KEDA를 사용하여 AWS SQS 큐 기반 스케일링을 구현할 때 가장 적절한 방법은 무엇인가요?

A. AWS Lambda 함수를 트리거하여 Kubernetes 워크로드 스케일링  
B. CloudWatch 메트릭을 사용하여 큐 길이 모니터링  
C. KEDA의 aws-sqs-queue 스케일러와 적절한 IAM 권한 사용  
D. SQS 큐에 폴링 서비스 배포  

<details>
<summary>정답 및 설명</summary>

**정답: C. KEDA의 aws-sqs-queue 스케일러와 적절한 IAM 권한 사용**

**설명:**
KEDA를 사용하여 AWS SQS 큐 기반 스케일링을 구현할 때 가장 적절한 방법은 KEDA의 aws-sqs-queue 스케일러와 적절한 IAM 권한을 사용하는 것입니다. KEDA는 AWS SQS 큐의 메시지 수에 기반하여 Kubernetes 워크로드를 자동으로 스케일링할 수 있는 내장 스케일러를 제공합니다. 이 스케일러는 SQS API를 직접 호출하여 큐 길이를 확인하고, 이에 따라 워크로드를 스케일링합니다.

**AWS SQS 스케일러 구현 단계:**

1. **IAM 권한 설정**: SQS 큐에 접근하기 위한 적절한 IAM 권한을 설정합니다.
2. **인증 구성**: AWS 자격 증명을 KEDA에 제공하기 위한 TriggerAuthentication을 구성합니다.
3. **ScaledObject 정의**: SQS 큐를 모니터링하고 워크로드를 스케일링하기 위한 ScaledObject를 정의합니다.

**필요한 IAM 권한:**

SQS 큐 길이를 확인하기 위해 최소한 다음 권한이 필요합니다:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl"
      ],
      "Resource": "arn:aws:sqs:*:*:*"
    }
  ]
}
```

**AWS 자격 증명 제공 방법:**

1. **AWS IAM Role for Service Account (IRSA)**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
spec:
  podIdentity:
    provider: aws-eks
```

2. **환경 변수**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
spec:
  env:
  - parameter: awsAccessKeyID
    name: AWS_ACCESS_KEY_ID
    containerName: my-container
  - parameter: awsSecretAccessKey
    name: AWS_SECRET_ACCESS_KEY
    containerName: my-container
```

3. **Secret**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-secrets
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
spec:
  secretTargetRef:
  - parameter: awsAccessKeyID
    name: aws-secrets
    key: AWS_ACCESS_KEY_ID
  - parameter: awsSecretAccessKey
    name: aws-secrets
    key: AWS_SECRET_ACCESS_KEY
```

**ScaledObject 예시:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: aws-sqs-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-consumer
  minReplicaCount: 0
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
      queueLength: "5"  # 메시지 5개당 1개의 레플리카
      awsRegion: us-east-1
      identityOwner: pod  # 또는 "operator"
    authenticationRef:
      name: aws-credentials
```

**전체 예시 (IRSA 사용):**

1. **Deployment 정의**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sqs-consumer
spec:
  replicas: 0  # KEDA가 관리
  selector:
    matchLabels:
      app: sqs-consumer
  template:
    metadata:
      labels:
        app: sqs-consumer
    spec:
      serviceAccountName: sqs-consumer-sa  # IRSA 구성된 서비스 계정
      containers:
      - name: consumer
        image: sqs-consumer:latest
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 1
            memory: 512Mi
```

2. **서비스 계정 정의**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sqs-consumer-sa
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/sqs-consumer-role
```

3. **TriggerAuthentication 정의**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
spec:
  podIdentity:
    provider: aws-eks
```

4. **ScaledObject 정의**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: aws-sqs-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-consumer
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
      queueLength: "5"
      awsRegion: us-east-1
      identityOwner: pod
    authenticationRef:
      name: aws-credentials
```

**고급 구성 옵션:**

1. **여러 큐 모니터링**:
```yaml
triggers:
- type: aws-sqs-queue
  metadata:
    queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/high-priority-queue
    queueLength: "1"  # 높은 우선순위 큐는 메시지당 1개의 레플리카
    awsRegion: us-east-1
- type: aws-sqs-queue
  metadata:
    queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/low-priority-queue
    queueLength: "10"  # 낮은 우선순위 큐는 메시지 10개당 1개의 레플리카
    awsRegion: us-east-1
```

2. **대기 중인 메시지만 고려**:
```yaml
triggers:
- type: aws-sqs-queue
  metadata:
    queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
    queueLength: "5"
    awsRegion: us-east-1
    scaleOnInFlight: "false"  # 처리 중인 메시지는 제외
```

3. **ScaledJob 사용**:
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: aws-sqs-job-scaler
spec:
  jobTargetRef:
    template:
      spec:
        containers:
        - name: sqs-job-processor
          image: sqs-processor:latest
        restartPolicy: Never
  pollingInterval: 30
  maxReplicaCount: 30
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
      queueLength: "1"  # 메시지당 1개의 Job
      awsRegion: us-east-1
    authenticationRef:
      name: aws-credentials
```

**AWS SQS 스케일러 사용 시 고려 사항:**

1. **IAM 권한**: 최소 권한 원칙에 따라 필요한 최소한의 권한만 부여합니다.
2. **지역 설정**: 올바른 AWS 지역을 지정해야 합니다.
3. **폴링 간격**: 적절한 폴링 간격을 설정하여 API 호출 비용과 응답성 사이의 균형을 맞춥니다.
4. **큐 길이 임계값**: 워크로드 특성에 맞는 적절한 큐 길이 임계값을 설정합니다.
5. **비용 고려**: SQS API 호출과 Kubernetes 워크로드 실행 비용을 모두 고려합니다.

**다른 옵션들의 문제점:**
- A. AWS Lambda 함수를 트리거하여 Kubernetes 워크로드 스케일링: 이는 불필요하게 복잡하며, KEDA가 직접 SQS 큐를 모니터링하는 것이 더 효율적입니다.
- B. CloudWatch 메트릭을 사용하여 큐 길이 모니터링: CloudWatch를 통한 간접적인 모니터링보다 KEDA의 직접적인 SQS 스케일러를 사용하는 것이 더 간단하고 효율적입니다.
- D. SQS 큐에 폴링 서비스 배포: 별도의 폴링 서비스는 불필요한 복잡성을 추가하며, KEDA가 이미 폴링 기능을 제공합니다.
</details>
