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
