# Strimzi Operator 퀴즈

이 퀴즈는 Strimzi Operator의 기본 개념, 설치 방법, 핵심 CRD, KRaft 노드 역할, EKS 배포 고려사항에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Strimzi는 어떤 종류의 CNCF 프로젝트인가요?
   - A) 서비스 메시
   - B) Kubernetes 위에서 Apache Kafka를 운영하기 위한 Operator
   - C) 컨테이너 런타임
   - D) CI/CD 파이프라인 도구

<details>

<summary>정답 보기</summary>

**정답: B) Kubernetes 위에서 Apache Kafka를 운영하기 위한 Operator**

**설명:**
Strimzi는 CNCF Incubating 프로젝트로, Kubernetes Operator 패턴을 사용해 Apache Kafka 클러스터의 배포와 전체 라이프사이클(설치, 업그레이드, 스케일링, 인증서 관리 등)을 관리합니다. Kafka 브로커를 직접 StatefulSet으로 작성해 운영하는 대신, CRD를 통해 선언적으로 원하는 상태를 정의하면 Operator가 이를 실제 클러스터 상태에 반영합니다.
</details>

2. Strimzi를 사용하지 않고 Kafka를 StatefulSet으로 직접 운영할 때 겪게 되는 어려움으로 가장 거리가 먼 것은?
   - A) 순차적 롤링 업그레이드 처리
   - B) TLS 인증서 발급 및 로테이션
   - C) 컨테이너 이미지 빌드 자체의 불가능
   - D) 파티션 리밸런싱 시 데이터 이동 관리

<details>

<summary>정답 보기</summary>

**정답: C) 컨테이너 이미지 빌드 자체의 불가능**

**설명:**
StatefulSet으로 Kafka를 직접 운영하는 것 자체가 불가능한 것은 아닙니다. 문제는 운영 편의성과 안정성입니다. 순차적 업그레이드, 인증서 로테이션, 리밸런싱 시 데이터 이동과 같은 작업들은 손으로 관리하기 어렵고 오류가 발생하기 쉬운데, Strimzi는 이를 CRD와 Operator 로직으로 자동화합니다.
</details>

3. Strimzi Cluster Operator를 Helm으로 설치할 때 사용하는 저장소 추가 명령어는 무엇인가요?
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>정답 보기</summary>

**정답: A) `helm repo add strimzi https://strimzi.io/charts/`**

**설명:**
Strimzi의 공식 Helm 저장소는 `https://strimzi.io/charts/` 입니다. 이 저장소를 추가한 후 `helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator --namespace kafka --create-namespace` 명령으로 Cluster Operator를 설치합니다.
</details>

4. Strimzi Cluster Operator가 기본적으로 감시(watch)하는 네임스페이스 범위는 어떻게 되나요?
   - A) 클러스터 전체 네임스페이스
   - B) 모든 kube-system 네임스페이스
   - C) 자신이 배포된 네임스페이스만
   - D) default 네임스페이스만

<details>

<summary>정답 보기</summary>

**정답: C) 자신이 배포된 네임스페이스만**

**설명:**
Cluster Operator는 기본적으로 자기 자신이 배포된 네임스페이스의 리소스만 감시합니다. 여러 네임스페이스를 감시하려면 Operator Deployment의 `STRIMZI_NAMESPACE` 환경 변수에 쉼표로 구분된 네임스페이스 목록을 지정하거나, `*`로 설정해 클러스터 전체를 감시하도록 확장할 수 있습니다.
</details>

5. Strimzi 0.45 이상에서 KRaft 모드가 기본이 되면서 더 이상 필요하지 않게 된 필드는 무엇인가요?
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>정답 보기</summary>

**정답: B) `Kafka.spec.zookeeper`**

**설명:**
Strimzi가 KRaft 모드를 기본으로 채택하면서 ZooKeeper 없이 컨트롤러 쿼럼이 메타데이터를 직접 관리하게 되었고, 과거 필수였던 `Kafka.spec.zookeeper` 블록은 더 이상 필요하지 않습니다. 대신 브로커와 컨트롤러 역할은 별도의 `KafkaNodePool` 리소스로 정의합니다.
</details>

6. `KafkaNodePool.spec.roles`에 지정할 수 있는 값으로 옳지 않은 것은?
   - A) `controller`
   - B) `broker`
   - C) `controller`와 `broker`를 함께 지정한 dual-role
   - D) `zookeeper`

<details>

<summary>정답 보기</summary>

**정답: D) `zookeeper`**

**설명:**
KRaft 기반 `KafkaNodePool`의 `roles` 필드는 `controller`, `broker`, 또는 두 역할을 모두 부여하는 dual-role(`[controller, broker]`) 조합만 지원합니다. `zookeeper`는 유효한 역할이 아니며, KRaft 모드에서는 ZooKeeper 자체가 존재하지 않습니다.
</details>

7. 컨트롤러 노드 풀을 3개로 구성하는 주된 이유는 무엇인가요?
   - A) 브로커 수와 반드시 동일해야 하기 때문
   - B) 컨트롤러 쿼럼이 과반수 합의를 필요로 하므로 홀수 개가 안전하기 때문
   - C) Kafka 클라이언트 라이브러리가 3개 이상을 요구하기 때문
   - D) EBS 볼륨 한도 때문

<details>

<summary>정답 보기</summary>

**정답: B) 컨트롤러 쿼럼이 과반수 합의를 필요로 하므로 홀수 개가 안전하기 때문**

**설명:**
KRaft 컨트롤러 쿼럼은 Raft와 유사한 합의 프로토콜로 동작하며, 리더 선출과 메타데이터 커밋에 과반수 투표가 필요합니다. 짝수 개의 컨트롤러는 동수 분할(split vote) 상황에서 가용성을 해칠 수 있어, 3개 또는 5개처럼 홀수 개로 구성하는 것이 일반적입니다. 이는 브로커 수와 독립적으로 결정됩니다.
</details>

8. Amazon EKS에서 Kafka 브로커용 EBS StorageClass를 정의할 때 사용하는 CSI 프로비저너 이름은 무엇인가요?
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>정답 보기</summary>

**정답: B) `ebs.csi.aws.com`**

**설명:**
Amazon EBS CSI 드라이버가 사용하는 프로비저너 이름은 `ebs.csi.aws.com`입니다. `kubernetes.io/aws-ebs`는 사용 중단(deprecated)된 in-tree 프로비저너 이름입니다. `KafkaNodePool.spec.storage`의 `persistent-claim` 볼륨은 이 프로비저너를 사용하는 StorageClass를 참조해 EBS gp3 볼륨을 동적으로 프로비저닝합니다.
</details>

9. 브로커 Pod를 여러 AZ에 균등하게 분산시키기 위해 `KafkaNodePool.spec.template.pod`에 지정하는 필드는 무엇인가요?
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>정답 보기</summary>

**정답: B) `topologySpreadConstraints`**

**설명:**
`topologySpreadConstraints`는 `topologyKey`(예: `topology.kubernetes.io/zone`)를 기준으로 Pod를 균등하게 분산시키는 스케줄링 제약입니다. Kafka 브로커를 여러 AZ에 분산시키면 하나의 AZ에 장애가 발생해도 나머지 브로커로 가용성을 유지할 수 있습니다. `whenUnsatisfiable: DoNotSchedule`로 설정하면 제약을 만족하지 못하는 스케줄링을 강제로 막을 수 있습니다.
</details>

10. 외부 클라이언트가 클러스터 밖에서 Kafka 브로커에 접근해야 할 때 `Kafka.spec.kafka.listeners`에 추가할 수 있는 리스너 타입은 무엇인가요?
    - A) `internal`과 `clusterip`
    - B) `loadbalancer` 또는 `nodeport`
    - C) `ingress`만 가능
    - D) 외부 노출은 지원하지 않음

<details>

<summary>정답 보기</summary>

**정답: B) `loadbalancer` 또는 `nodeport`**

**설명:**
Strimzi 리스너는 `internal`, `route`, `ingress`, `loadbalancer`, `nodeport` 타입을 지원합니다. EKS에서 외부 클라이언트 접근이 필요할 때는 주로 `loadbalancer`(AWS NLB 자동 프로비저닝)나 `nodeport`(워커 노드 포트 + 별도 로드밸런서) 타입을 사용합니다. `loadbalancer` 타입은 어노테이션을 통해 AWS Load Balancer Controller의 NLB 설정(내부/외부 스킴 등)을 제어할 수 있습니다.
</details>

## 단답형 문제

11. `KafkaTopic`, `KafkaUser` CR을 실제 Kafka 리소스와 동기화하는 두 개의 Strimzi 내부 컴포넌트 이름을 각각 쓰세요.

<details>

<summary>정답 보기</summary>

**정답: Topic Operator, User Operator**

**설명:**
Topic Operator는 `KafkaTopic` CR을 소스 오브 트루스로 삼아 실제 Kafka 토픽에 단방향으로 동기화하며, User Operator는 `KafkaUser` CR을 기반으로 SCRAM-SHA-512 또는 TLS 인증 자격 증명과 ACL을 관리합니다. 이 두 컴포넌트는 각 Kafka 클러스터마다 하나의 Pod로 묶여 배포되는 Entity Operator의 일부입니다.
</details>

12. Cluster Operator가 여러 네임스페이스를 감시하도록 설정할 때 지정하는 환경 변수 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `STRIMZI_NAMESPACE`**

**설명:**
`STRIMZI_NAMESPACE` 환경 변수를 Cluster Operator Deployment에 설정하면 감시할 네임스페이스 범위를 제어할 수 있습니다. 쉼표로 구분된 네임스페이스 목록을 지정하거나 `*`로 설정해 클러스터 전체를 감시 대상으로 확장할 수 있습니다.
</details>

13. `KafkaNodePool.spec.storage`에서 브로커당 여러 개의 EBS 볼륨을 지정해 I/O를 분산시킬 수 있게 해주는 스토리지 타입은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: JBOD (type: jbod)**

**설명:**
JBOD(Just a Bunch Of Disks) 타입 스토리지는 하나의 브로커에 여러 개의 `persistent-claim` 볼륨을 각각 다른 `id`로 지정할 수 있게 해줍니다. 이를 통해 단일 EBS 볼륨의 처리량 한계를 넘어서는 I/O를 여러 볼륨으로 분산시킬 수 있습니다.
</details>

14. Kafka 클러스터의 `Kafka` 리소스 상태에서 브로커/컨트롤러가 정상적으로 쿼럼을 형성하고 리스너가 활성화되었음을 나타내는 조건(condition) 값은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `Ready: True`**

**설명:**
`kubectl get kafka -n kafka`로 확인할 수 있는 `Kafka` 리소스의 상태 조건 중 `Ready` 조건이 `True`가 되면 클러스터의 모든 구성 요소(브로커, 컨트롤러, 리스너, Entity Operator)가 정상 동작 중임을 의미합니다.
</details>

15. 소스/싱크 커넥터(예: Debezium)를 실행하기 위한 별도의 워커 클러스터를 정의하는 Strimzi CRD의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `KafkaConnect`**

**설명:**
`KafkaConnect`는 Kafka Connect 워커 클러스터를 정의하는 CRD입니다. 개별 커넥터 인스턴스는 `KafkaConnector` CR로 선언적으로 관리하며, `KafkaConnect` 클러스터에 배포됩니다.
</details>

## 실습 문제

16. Strimzi Cluster Operator를 Helm으로 `kafka` 네임스페이스에 설치하는 전체 명령어 시퀀스를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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

**설명:**
`helm repo add`로 Strimzi 저장소를 등록하고 `helm repo update`로 최신 차트 정보를 가져옵니다. `helm install`에 `--create-namespace`를 추가하면 `kafka` 네임스페이스가 없어도 자동으로 생성합니다. 설치 후 `kubectl get pods -n kafka`로 Cluster Operator Pod가 `Running` 상태인지, `kubectl get crd | grep strimzi`로 `Kafka`, `KafkaNodePool` 등의 CRD가 등록되었는지 확인합니다.
</details>

17. 브로커 역할만 수행하는 3개 노드로 구성된 `KafkaNodePool`을 작성하세요. 각 브로커는 gp3 기반 `persistent-claim` 볼륨 100Gi를 사용합니다.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
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
```

**설명:**
`strimzi.io/cluster` 라벨은 이 노드 풀이 속한 `Kafka` 리소스의 이름과 일치해야 합니다. `roles: [broker]`로 브로커 전용 노드임을 지정하고, `storage.type: jbod` 아래 `persistent-claim` 볼륨을 통해 EBS 기반 영구 스토리지를 100Gi 크기로 프로비저닝합니다. `class`는 `ebs.csi.aws.com` 프로비저너를 사용하는 StorageClass 이름을 참조합니다.
</details>

18. `orders`라는 이름의 `KafkaTopic`을 파티션 12개, 복제본 3개로 생성하고, 이후 콘솔 프로듀서/컨슈머로 테스트하는 명령어까지 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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
    min.insync.replicas: 2
```

```bash
# 토픽 적용
kubectl apply -f orders-topic.yaml -n kafka
kubectl get kafkatopic -n kafka

# 프로듀서 테스트
kubectl run kafka-producer -n kafka -ti \
  --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders

# 컨슈머 테스트
kubectl run kafka-consumer -n kafka -ti \
  --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders --from-beginning
```

**설명:**
`KafkaTopic` CR은 `strimzi.io/cluster` 라벨을 통해 어느 `Kafka` 클러스터에 속하는지를 Topic Operator에게 알려줍니다. 적용 후 `kubectl get kafkatopic -n kafka`로 토픽이 실제로 생성되었는지 확인할 수 있습니다. 테스트용 프로듀서/컨슈머는 Strimzi가 제공하는 Kafka 이미지를 임시 Pod로 실행해 부트스트랩 서비스(`my-cluster-kafka-bootstrap:9092`)에 연결합니다.
</details>

19. `orders` 토픽에 대해 Read/Write/Describe 권한만 가진 SCRAM-SHA-512 인증 `KafkaUser`를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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

**설명:**
`authentication.type: scram-sha-512`는 User Operator가 SCRAM 자격 증명을 생성하고 이를 Secret으로 저장하도록 지시합니다. `authorization.type: simple`은 Kafka의 기본 ACL 기반 권한 부여 방식을 사용함을 의미하며, `acls` 목록에 `orders` 토픽에 대한 `Read`, `Write`, `Describe` 작업만 허용하도록 제한합니다. 이 방식으로 최소 권한 원칙을 CR 수준에서 선언적으로 구현할 수 있습니다.
</details>

20. 브로커 Pod를 AZ별로 균등하게 분산시키기 위한 `topologySpreadConstraints`를 `KafkaNodePool`의 `spec.template.pod`에 추가하세요.

<details>

<summary>정답 보기</summary>

**정답:**
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

**설명:**
`topologyKey: topology.kubernetes.io/zone`는 EKS 워커 노드의 AZ 라벨을 기준으로 Pod를 분산시킵니다. `maxSkew: 1`은 AZ 간 Pod 수 차이를 최대 1개까지만 허용하며, `whenUnsatisfiable: DoNotSchedule`은 조건을 만족할 수 없는 경우 스케줄링 자체를 막아 강제로 균등 분산을 보장합니다. `labelSelector`는 이 제약이 어떤 Pod 집합(같은 브로커 노드 풀)을 대상으로 스큐를 계산할지 지정합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/02-strimzi-operator.md) | [다음 퀴즈: Kafka 운영](./03-kafka-operations-quiz.md)
