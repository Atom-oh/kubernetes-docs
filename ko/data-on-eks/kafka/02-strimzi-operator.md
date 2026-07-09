# Part 2: Strimzi Operator

> **지원 버전**: Strimzi 0.45+, Kubernetes 1.28+\
> **마지막 업데이트**: 2026년 7월 9일

## 실습 환경 설정

이 문서의 예제를 따라하기 위해서는 다음과 같은 도구와 환경이 필요합니다:

### 필수 도구

* kubectl v1.28 이상
* Helm v3.12 이상
* 작동하는 Kubernetes 클러스터 (Amazon EKS 권장)
* Amazon EBS CSI 드라이버가 설치된 클러스터 (스토리지용)

## Strimzi란 무엇인가?

Strimzi는 Kubernetes 위에서 Apache Kafka를 운영하기 위한 CNCF Incubating 프로젝트로, Operator 패턴을 통해 Kafka 클러스터의 전체 라이프사이클을 관리합니다. Kafka 브로커를 직접 StatefulSet으로 작성해 운영할 수도 있지만, 실제 운영 환경에서는 다음과 같은 반복적이고 오류가 발생하기 쉬운 작업들이 발생합니다.

* 브로커/컨트롤러의 순차적 롤링 업그레이드와 설정 변경 반영
* TLS 인증서 발급, 갱신, 로테이션
* 파티션 리밸런싱과 스케일 인/아웃 시의 데이터 이동
* 사용자(ACL), 토픽, 커넥터 같은 부속 리소스의 선언적 관리

Strimzi는 이 모든 작업을 `Kafka`, `KafkaNodePool`, `KafkaTopic`, `KafkaUser`, `KafkaConnect` 같은 CRD(Custom Resource Definition)로 추상화합니다. 원하는 상태(desired state)를 YAML로 선언하면 Operator가 현재 상태와 비교하여 필요한 변경을 자동으로 수행하므로, 손으로 작성한 StatefulSet + 스크립트 조합보다 훨씬 안정적이고 재현 가능한 운영이 가능합니다.

### 주요 구성 요소

* **Cluster Operator**: `Kafka`, `KafkaNodePool`, `KafkaConnect` 등 클러스터 수준 리소스를 감시하고 StatefulSet/Pod/Service/ConfigMap 등을 생성·관리
* **Topic Operator**: `KafkaTopic` CR을 실제 Kafka 토픽과 동기화 (단방향 동기화 — CR을 소스 오브 트루스로 삼아 실제 토픽에 반영)
* **User Operator**: `KafkaUser` CR을 기반으로 SCRAM-SHA-512 또는 TLS 인증 자격 증명과 ACL을 관리
* **Entity Operator**: Topic Operator와 User Operator를 하나의 Pod로 묶어 각 Kafka 클러스터마다 배포

## 설치

### 방법 1: Helm Chart (권장)

```bash
# Strimzi Helm 저장소 추가
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# kafka 네임스페이스에 Cluster Operator 설치
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --namespace kafka \
  --create-namespace \
  --version 0.45.0

# 설치 확인
kubectl get pods -n kafka
kubectl get crd | grep strimzi
```

### 방법 2: install YAML / OperatorHub

Helm 없이 설치하거나 OLM(Operator Lifecycle Manager) 기반 OperatorHub를 통해 설치할 수도 있습니다.

```bash
# 특정 네임스페이스를 대상으로 install YAML 적용
kubectl create namespace kafka
curl -L https://github.com/strimzi/strimzi-kafka-operator/releases/download/0.45.0/strimzi-cluster-operator-0.45.0.yaml \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl apply -f - -n kafka
```

Cluster Operator는 기본적으로 자신이 배포된 네임스페이스만 감시합니다. 여러 네임스페이스를 감시 대상으로 지정하려면 Operator Deployment의 `STRIMZI_NAMESPACE` 환경 변수에 쉼표로 구분된 네임스페이스 목록을 설정하거나, `*`를 지정해 클러스터 전체를 감시하도록 설정합니다.

```bash
kubectl set env deployment/strimzi-cluster-operator \
  -n kafka STRIMZI_NAMESPACE=kafka,kafka-staging
```

## 핵심 CRD

### Kafka와 KafkaNodePool

Strimzi 0.45+ 부터는 KRaft 모드(ZooKeeper 없는 Kafka)가 기본값이며, 브로커/컨트롤러 역할을 `KafkaNodePool` 리소스로 분리해 정의하는 방식이 표준 배포 형태가 되었습니다. 과거의 `Kafka.spec.zookeeper` 블록은 KRaft 전환에 따라 더 이상 필요하지 않으며, 노드 풀별로 역할(`controller`, `broker`, 또는 두 역할을 겸하는 `dual-role`)과 리소스, 스토리지를 독립적으로 지정합니다.

```yaml
# 컨트롤러 전용 노드 풀 (3개, 쿼럼 구성)
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: controller
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - controller
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 20Gi
        class: gp3-kafka
        deleteClaim: false
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
---
# 브로커 전용 노드 풀 (3개)
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: broker
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 100Gi
        class: gp3-kafka
        deleteClaim: false
  resources:
    requests:
      cpu: "2"
      memory: 4Gi
    limits:
      cpu: "4"
      memory: 4Gi
---
# Kafka 클러스터 본체 (KRaft, ZooKeeper 미사용)
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
spec:
  kafka:
    version: 3.9.0
    metadataVersion: 3.9-IV0
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

브로커 3개, 컨트롤러 3개로 쿼럼을 구성한 것은 컨트롤러 쿼럼이 과반수 합의를 필요로 하기 때문이며, 운영 환경에서는 홀수 개(3 또는 5)의 컨트롤러를 두는 것이 일반적입니다. 노드가 `dual-role`(`roles: [controller, broker]`)로 지정되면 소규모 클러스터에서 별도 컨트롤러 없이 하나의 풀로 운영할 수도 있지만, 프로덕션에서는 컨트롤러와 브로커 역할을 분리하는 것이 리소스 경쟁과 장애 격리 측면에서 권장됩니다.

### KafkaTopic

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: orders
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 12
  replicas: 3
  config:
    retention.ms: 604800000
    min.insync.replicas: 2
```

### KafkaUser

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
        operations: [Read, Write, Describe]
```

### KafkaConnect

토픽/유저와 달리 `KafkaConnect`는 소스/싱크 커넥터(예: Debezium, S3 Sink)를 실행하는 별도의 워커 클러스터를 정의합니다. `KafkaConnector` CR을 통해 개별 커넥터를 선언적으로 관리할 수 있습니다.

## EKS 배포 고려사항

### 1. EBS gp3 기반 StorageClass

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "250"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

브로커는 지속적인 순차 쓰기 위주이므로 `gp3`의 기본 처리량(125MiB/s)을 넘어서는 워크로드라면 `throughput`과 `iops`를 상향 조정합니다. `KafkaNodePool.spec.storage`는 JBOD(Just a Bunch Of Disks) 타입으로 여러 개의 `persistent-claim` 볼륨을 지정할 수 있어, 브로커당 여러 개의 EBS 볼륨으로 I/O를 분산시킬 수도 있습니다.

### 2. AZ 분산을 위한 Pod Anti-Affinity / Topology Spread

브로커 Pod가 동일 AZ에 몰리면 AZ 장애 시 쿼럼이나 파티션 가용성을 잃을 수 있습니다. `KafkaNodePool.spec.template.pod`에 `topologySpreadConstraints`를 지정해 AZ별로 균등하게 분산시킵니다.

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: broker
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles: [broker]
  template:
    pod:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              strimzi.io/cluster: my-cluster
              strimzi.io/name: my-cluster-broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 100Gi
        class: gp3-kafka
```

### 3. 리스너와 외부 노출

내부 통신은 클러스터 내부에서만 접근 가능한 `internal` 리스너(평문 또는 TLS)로, 외부 클라이언트 접근이 필요하면 `loadbalancer` 또는 `nodeport` 타입 리스너를 별도로 추가합니다.

```yaml
listeners:
  - name: plain
    port: 9092
    type: internal
    tls: false
  - name: tls
    port: 9093
    type: internal
    tls: true
  - name: external
    port: 9094
    type: loadbalancer
    tls: true
    configuration:
      bootstrap:
        annotations:
          service.beta.kubernetes.io/aws-load-balancer-type: nlb
          service.beta.kubernetes.io/aws-load-balancer-scheme: internal
```

`type: loadbalancer`를 사용하면 Strimzi가 브로커별 부트스트랩/개별 서비스를 각각 NLB로 노출합니다. VPC 내부에서만 접근이 필요하다면 `internal` 스킴을 사용하고, 완전한 퍼블릭 접근이 필요한 경우에만 `internet-facing`으로 변경합니다. 비용과 리스너 수를 줄이려면 `nodeport` 타입으로 전환해 워커 노드의 NodePort와 외부 로드밸런서(또는 Route 53) 조합으로 노출할 수도 있습니다.

## 배포 절차

```bash
# 1. Cluster Operator 설치 확인
kubectl get pods -n kafka

# 2. KafkaNodePool + Kafka CR 적용
kubectl apply -f controller-pool.yaml -n kafka
kubectl apply -f broker-pool.yaml -n kafka
kubectl apply -f kafka-cluster.yaml -n kafka

# 3. 클러스터 상태 확인 (Ready 조건이 True가 될 때까지 대기)
kubectl get kafka -n kafka -w
kubectl get pods -n kafka

# 4. 토픽 생성
kubectl apply -f orders-topic.yaml -n kafka
kubectl get kafkatopic -n kafka

# 5. 프로듀서/컨슈머 테스트
kubectl run kafka-producer -n kafka -ti --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders

kubectl run kafka-consumer -n kafka -ti --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders --from-beginning
```

`Kafka` 리소스의 상태 조건이 `Ready: True`가 되면 브로커와 컨트롤러가 정상적으로 쿼럼을 형성하고 리스너가 활성화된 것입니다. `kubectl get pods -n kafka`로 각 노드 풀에 대응하는 Pod(`my-cluster-broker-0`, `my-cluster-controller-0` 등)가 `Running` 상태인지 확인합니다.

## 다음 단계

클러스터를 배포했다면 다음으로는 스케일링, Cruise Control을 이용한 파티션 리밸런싱, 무중단 버전 업그레이드 같은 day-2 운영 작업이 필요합니다. 이는 [Part 3: Kafka 운영](./03-kafka-operations.md)에서 다룹니다.

[메인 페이지로 돌아가기](./)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)를 풀어보세요.
