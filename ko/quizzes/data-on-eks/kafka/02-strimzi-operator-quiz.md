# Strimzi Operator 퀴즈

> **검토 기준**: 2026-09-12, Strimzi 1.2.0 / Kafka 4.3.1.

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
Strimzi 1.2는 CNCF incubating 프로젝트이며 커스텀 리소스의 원하는 상태를 조정합니다. 현재 Kafka Pod 관리는 StrimziPodSet 기반입니다. Operator 사용만으로 모든 운영 정책이나 가용성 보장이 완성되지는 않습니다.
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
직접 운영도 가능하지만 Kafka 업그레이드·인증서·저장소·재배치 절차를 운영자가 구현해야 합니다. Strimzi가 반복 작업을 조정하더라도 실제 데이터 복구와 가용성 정책은 별도 검증 대상입니다.
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
공식 chart 저장소를 추가한 뒤 버전을 1.2.0으로 고정해 새 설치합니다. 기존 beta API/CRD가 있는 클러스터는 먼저 공식 전환 절차를 수행해야 하며, namespace만 새로 만들어도 cluster-scoped CRD 충돌은 사라지지 않습니다.
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
기본 chart는 release namespace를 감시합니다. 추가 watchNamespaces를 지정하면 1.2 chart는 release namespace도 포함해 중복 제거하고 RoleBinding을 생성합니다. 환경 변수만 바꾸면 필요한 RBAC가 누락될 수 있습니다.
</details>

5. 현재 Strimzi 1.2의 KRaft 기반 배포에서 지원되지 않는 블록은?
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>정답 보기</summary>

**정답: B) `Kafka.spec.zookeeper`**

**설명:**
현재 Strimzi 1.2는 KRaft를 사용하고 ZooKeeper 블록을 지원하지 않습니다. KafkaNodePool에서 controller와 broker 역할을 정의하며, 예전 활성화 annotation도 필요하지 않습니다.
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
실제 enum 값은 controller와 broker입니다. 둘을 함께 넣는 [controller, broker]가 가능하지만 dual-role이라는 문자열을 roles에 넣는 것은 아닙니다.
</details>

7. controller voter 3개를 선택하는 주요 이유는?
   - A) 브로커 수와 반드시 동일해야 하기 때문
   - B) 한 voter 장애 뒤에도 과반수 2개를 유지할 수 있기 때문
   - C) Kafka 클라이언트 라이브러리가 3개 이상을 요구하기 때문
   - D) EBS 볼륨 한도 때문

<details>

<summary>정답 보기</summary>

**정답: B) 한 voter 장애 뒤에도 과반수 2개를 유지할 수 있기 때문**

**설명:**
3개 voter의 과반수는 2개이므로 한 voter 장애 후에도 과반수를 유지할 수 있습니다. 짝수도 과반수 계산이 가능하며, 홀수는 같은 장애 허용 수준에서 효율적인 선택입니다. broker 수와 독립적이고 연결성 등 다른 조건도 필요합니다.
</details>

8. 표준 Amazon EBS CSI 드라이버 경로의 StorageClass provisioner는?
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>정답 보기</summary>

**정답: B) `ebs.csi.aws.com`**

**설명:**
표준 EBS CSI는 ebs.csi.aws.com입니다. EKS Auto Mode는 ebs.csi.eks.amazonaws.com을 사용하므로 서로 다른 경로를 구분합니다. StorageClass provisioner 변경만으로 기존 PVC가 이관되지는 않습니다.
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
실제 Pod label과 selector가 일치해야 하며, 세 eligible AZ를 요구한다면 minDomains: 3 같은 조건도 필요합니다. maxSkew: 1만으로 세 AZ가 생기지 않습니다. 배치와 Kafka replica rack placement는 별도로 확인합니다.
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
Strimzi는 LoadBalancer Service 또는 NodePort 등을 생성합니다. 어떤 클라우드 LB가 만들어지는지는 설치된 controller와 class에 달려 있습니다. 본문은 AWS Load Balancer Controller class를 고정하고 bootstrap과 모든 broker Service에 internal/IP target 설정을 적용합니다.
</details>

## 단답형 문제

11. `KafkaTopic`, `KafkaUser` CR을 실제 Kafka 리소스와 동기화하는 두 개의 Strimzi 내부 컴포넌트 이름을 각각 쓰세요.

<details>

<summary>정답 보기</summary>

**정답: Topic Operator, User Operator**

**설명:**
Topic Operator와 User Operator는 활성화한 Entity Operator에 포함될 수 있으며 별도 설치 방식도 있습니다. 토픽과 사용자 CR은 Kafka와 같은 namespace 및 올바른 cluster label을 사용해야 합니다.
</details>

12. Cluster Operator가 여러 네임스페이스를 감시하도록 설정할 때 지정하는 환경 변수 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `STRIMZI_NAMESPACE`**

**설명:**
변수 이름은 STRIMZI_NAMESPACE입니다. Helm 관리 설치에서는 watchNamespaces/watchAnyNamespace values로 변경하고 대응 RBAC도 함께 관리하여 kubectl set env에 의한 drift를 피합니다.
</details>

13. `KafkaNodePool.spec.storage`에서 브로커당 여러 개의 EBS 볼륨을 지정해 I/O를 분산시킬 수 있게 해주는 스토리지 타입은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: JBOD (type: jbod)**

**설명:**
JBOD는 여러 volume ID를 사용할 수 있게 합니다. 자동 데이터 균등 분산이나 인스턴스 EBS/네트워크 한도 해제를 보장하지 않습니다. KRaft metadata는 최대 한 볼륨의 kraftMetadata: shared로 지정할 수 있습니다.
</details>

14. Operator의 마지막 Kafka 조정 성공을 나타내는 condition은?

<details>

<summary>정답 보기</summary>

**정답: `Ready: True`**

**설명:**
Ready=True는 Operator의 마지막 조정 관찰입니다. observedGeneration과 현재 generation을 비교하고 Pod readiness, quorum과 인증된 실제 client 연결을 확인해야 합니다.
</details>

15. 소스/싱크 커넥터(예: Debezium)를 실행하기 위한 별도의 워커 클러스터를 정의하는 Strimzi CRD의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `KafkaConnect`**

**설명:**
KafkaConnect는 Connect worker 클러스터를 정의하고 KafkaConnector는 개별 connector를 표현합니다. connector 리소스 관리를 활성화하는 설정과 worker 인증·권한은 별도로 맞춰야 합니다.
</details>

## 실습 문제

16. 본문의 operator-values.yaml을 사용하여 Strimzi 1.2.0을 새 kafka namespace에 설치하는 명령을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.2.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io
```

**설명:**
이 명령은 새 설치 기준입니다. chart version을 고정하고 Operator 가용성과 CRD를 확인합니다. 기존 Strimzi가 있는 클러스터는 v1 API 변환과 CRD 소유권·업그레이드 절차를 먼저 검토합니다.
</details>

17. 본문과 같은 namespace·스토리지·세 AZ 조건을 가진 3개 broker 전용 KafkaNodePool을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: broker
  namespace: kafka
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
      kraftMetadata: shared
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      memory: 4Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: broker
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 3
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            strimzi.io/cluster: my-cluster
            docs.example.com/kafka-role: broker
```

**설명:**
본문의 표준 gp3-kafka StorageClass와 세 AZ 요구를 사용합니다. namespace와 cluster label을 맞추고 deleteClaim: false로 PVC를 보존합니다. Auto Mode라면 별도 StorageClass를 선택하며, 풀 분리는 물리 worker node 분리를 보장하지 않습니다.
</details>

18. 인증된 kafka-client Pod가 준비되어 있다고 가정하고 orders 토픽을 만들고 TLS/SCRAM producer/consumer로 확인하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1
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

```bash
kubectl apply -f orders-topic.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
printf 'strimzi-auth-smoke-test\n' |
  kubectl -n kafka exec -i kafka-client -- \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
    --producer.config /client/client.properties --topic orders
kubectl -n kafka exec kafka-client -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
  --consumer.config /client/client.properties --group order-processor \
  --topic orders --from-beginning --max-messages 1 --timeout-ms 10000
```

**설명:**
본문의 KafkaUser, CA Secret 및 인증된 kafka-client Pod가 먼저 준비되어 있어야 합니다. 평문 endpoint 대신 TLS/SCRAM client properties를 사용합니다. 기존 토픽의 첫 레코드가 방금 전송한 값인지는 출력으로 확인합니다.
</details>

19. orders 생산·소비와 order-processor 그룹 및 idempotent producer를 위한 SCRAM 사용자를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1
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
          patternType: literal
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: order-processor
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

**설명:**
Kafka의 listener authentication과 cluster authorizer도 켜야 합니다. topic ACL 외에 order-processor group Read와 idempotent producer 동작을 위한 권한을 명시했습니다. 실제 서비스에서는 생산/소비 주체 분리를 검토합니다.
</details>

20. broker KafkaNodePool의 spec 아래에 실제 label과 일치하고 세 eligible AZ를 요구하는 template 발췌를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
# Merge under KafkaNodePool.spec
template:
  pod:
    metadata:
      labels:
        docs.example.com/kafka-role: broker
    topologySpreadConstraints:
    - maxSkew: 1
      minDomains: 3
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      nodeAffinityPolicy: Honor
      nodeTaintsPolicy: Honor
      labelSelector:
        matchLabels:
          strimzi.io/cluster: my-cluster
          docs.example.com/kafka-role: broker
```

**설명:**
이 발췌는 broker KafkaNodePool의 spec 아래에 넣습니다. metadata label과 selector가 같고 minDomains=3이므로 세 eligible AZ가 없으면 Pending이 될 수 있습니다. AZ 손실 뒤 엄격한 제약이 대체 Pod 배치를 막을 수 있으며 Kafka rack awareness는 별도 설정입니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/02-strimzi-operator.md) | [다음 퀴즈: Kafka 운영](./03-kafka-operations-quiz.md)
