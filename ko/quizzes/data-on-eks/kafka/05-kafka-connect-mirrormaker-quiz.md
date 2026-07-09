# Kafka Connect와 MirrorMaker 퀴즈

이 퀴즈는 Kafka Connect의 소스/싱크 커넥터 구조, 분산 모드, Strimzi의 `KafkaConnect`/`KafkaConnector` CRD, MirrorMaker 2의 아키텍처와 재해복구 패턴에 대한 이해도를 테스트합니다.

## 객관식 문제

1. 데이터베이스의 WAL/binlog를 읽어 변경 이벤트를 Kafka로 스트리밍하는 Debezium과 같은 커넥터는 어떤 종류에 속하나요?
   - A) 싱크 커넥터
   - B) 소스 커넥터
   - C) 필터 커넥터
   - D) 트랜스폼 커넥터

<details>

<summary>정답 보기</summary>

**정답: B) 소스 커넥터**

**설명:**
소스 커넥터(Source Connector)는 외부 시스템의 데이터를 Kafka 토픽으로 끌어오는 역할을 합니다. Debezium은 데이터베이스의 WAL(Write-Ahead Log) 또는 binlog를 읽어 행 단위 변경 이벤트를 Kafka로 스트리밍하는 CDC(Change Data Capture) 소스 커넥터의 대표적인 예시입니다. 반대로 싱크 커넥터(Sink Connector)는 Kafka의 데이터를 S3, Elasticsearch 같은 외부 시스템으로 내보내는 역할을 합니다.
</details>

2. S3 Sink Connector와 Elasticsearch Sink Connector의 공통적인 역할은 무엇인가요?
   - A) 외부 시스템 데이터를 Kafka로 가져온다
   - B) Kafka 토픽의 데이터를 외부 시스템으로 내보낸다
   - C) 토픽 간 데이터를 복제한다
   - D) 컨슈머 그룹의 오프셋을 관리한다

<details>

<summary>정답 보기</summary>

**정답: B) Kafka 토픽의 데이터를 외부 시스템으로 내보낸다**

**설명:**
S3 Sink Connector와 Elasticsearch Sink Connector는 모두 싱크 커넥터로, Kafka 토픽에 쌓인 데이터를 외부 시스템으로 내보내는 역할을 합니다. S3 Sink Connector는 데이터를 JSON/Parquet 등의 형식으로 S3 버킷에 적재하고, Elasticsearch Sink Connector는 검색과 분석을 위해 데이터를 Elasticsearch 인덱스에 반영합니다.
</details>

3. Kafka Connect의 분산 모드(Distributed Mode)에서 워커 하나가 죽으면 어떤 일이 발생하나요?
   - A) 전체 Connect 클러스터가 중단된다
   - B) 죽은 워커의 태스크가 살아있는 다른 워커로 자동 재배치된다
   - C) 커넥터가 standalone 모드로 자동 전환된다
   - D) 모든 오프셋 정보가 초기화된다

<details>

<summary>정답 보기</summary>

**정답: B) 죽은 워커의 태스크가 살아있는 다른 워커로 자동 재배치된다**

**설명:**
분산 모드에서는 여러 워커 프로세스가 그룹을 이루어 하나의 Connect 클러스터로 동작하며, 그룹 코디네이터가 커넥터/태스크를 워커들에게 분배합니다. 워커 중 하나가 죽으면 코디네이터가 이를 감지하고 해당 태스크를 살아있는 다른 워커로 자동으로 재배치하여 가용성을 유지합니다. 이는 단일 프로세스로 동작하며 고가용성이 없는 standalone 모드와의 핵심적인 차이입니다.
</details>

4. Kubernetes/Strimzi 환경에서 Kafka Connect의 standalone 모드가 사용되지 않는 주된 이유는 무엇인가요?
   - A) REST API를 지원하지 않기 때문
   - B) 고가용성과 수평 확장성이 없기 때문
   - C) 소스 커넥터만 지원하기 때문
   - D) TLS를 지원하지 않기 때문

<details>

<summary>정답 보기</summary>

**정답: B) 고가용성과 수평 확장성이 없기 때문**

**설명:**
standalone 모드는 단일 프로세스에서 파일 기반 오프셋 저장소로 동작하며 로컬 개발/테스트 용도로 설계되었습니다. 워커가 하나뿐이므로 장애가 발생하면 복구할 다른 워커가 없고, 워크로드를 여러 노드로 분산시킬 수도 없습니다. 이러한 한계 때문에 Kubernetes/Strimzi 환경에서는 항상 여러 워커 Pod로 구성되는 분산 모드를 사용합니다.
</details>

5. Strimzi에서 `KafkaConnector` CRD를 사용하는 주된 장점은 무엇인가요?
   - A) REST API를 직접 호출하지 않고 GitOps 방식으로 커넥터를 선언적으로 관리할 수 있다
   - B) 커넥터 플러그인을 자동으로 개발해준다
   - C) 분산 모드를 standalone 모드로 전환해준다
   - D) 오프셋 저장소를 필요 없게 만든다

<details>

<summary>정답 보기</summary>

**정답: A) REST API를 직접 호출하지 않고 GitOps 방식으로 커넥터를 선언적으로 관리할 수 있다**

**설명:**
`KafkaConnector` CRD를 사용하면 커넥터 생성·삭제·설정 변경을 위해 Connect REST API를 직접 호출할 필요 없이, YAML 매니페스트로 원하는 상태를 선언하면 Strimzi Operator가 이를 실제 커넥터 상태와 동기화합니다. 이를 통해 커넥터 설정을 Git 저장소에서 버전 관리하고 코드 리뷰/CI 파이프라인을 통해 배포하는 GitOps 워크플로가 가능해집니다.
</details>

6. `KafkaConnect` 리소스에서 `KafkaConnector` CRD를 활성화하기 위해 필요한 어노테이션은 무엇인가요?
   - A) `strimzi.io/kraft: enabled`
   - B) `strimzi.io/node-pools: enabled`
   - C) `strimzi.io/use-connector-resources: "true"`
   - D) `strimzi.io/connect-mode: distributed`

<details>

<summary>정답 보기</summary>

**정답: C) `strimzi.io/use-connector-resources: "true"`**

**설명:**
`KafkaConnect` 리소스의 메타데이터에 `strimzi.io/use-connector-resources: "true"` 어노테이션을 추가해야 Strimzi Operator가 해당 Connect 클러스터에 대해 `KafkaConnector` 리소스를 감시하고 실제 커넥터로 반영합니다. 이 어노테이션이 없으면 `KafkaConnector` 리소스를 생성해도 아무런 효과가 없습니다.
</details>

7. Strimzi의 `KafkaConnect.spec.build`를 사용해 커스텀 커넥터 플러그인이 포함된 이미지를 만드는 방식의 특징은 무엇인가요?
   - A) 사용자가 직접 Dockerfile을 작성해야 한다
   - B) 플러그인 아티팩트 URL만 선언하면 Operator가 빌드하고 지정한 레지스트리에 푸시한다
   - C) 항상 Docker Hub에만 이미지를 푸시할 수 있다
   - D) standalone 모드에서만 사용할 수 있다

<details>

<summary>정답 보기</summary>

**정답: B) 플러그인 아티팩트 URL만 선언하면 Operator가 빌드하고 지정한 레지스트리에 푸시한다**

**설명:**
Strimzi가 권장하는 패턴은 `KafkaConnect.spec.build`에 `output`(레지스트리 이미지 경로와 푸시 시크릿)과 `plugins`(플러그인 아티팩트의 tgz/zip/jar URL 또는 Maven 좌표)만 선언적으로 작성하는 것입니다. Dockerfile을 직접 작성할 필요 없이 Strimzi Operator가 빌드 과정을 수행하고 결과 이미지를 Amazon ECR 같은 지정된 레지스트리로 푸시합니다.
</details>

8. MirrorMaker 2에서 소스 클러스터의 컨슈머 그룹 오프셋을 타깃 클러스터의 오프셋으로 변환하는 역할을 하는 커넥터는 무엇인가요?
   - A) MirrorSourceConnector
   - B) MirrorHeartbeatConnector
   - C) MirrorCheckpointConnector
   - D) MirrorTopicConnector

<details>

<summary>정답 보기</summary>

**정답: C) MirrorCheckpointConnector**

**설명:**
MirrorCheckpointConnector는 소스 클러스터의 컨슈머 그룹 오프셋을 주기적으로 타깃 클러스터의 오프셋으로 변환(offset translation)하여 체크포인트 토픽에 기록합니다. 이 정보가 있어야 페일오버 시 컨슈머 그룹이 DR 클러스터에서 "어디까지 처리했는지"를 알고 이어서 소비를 재개할 수 있습니다. MirrorSourceConnector는 실제 메시지/토픽/ACL 복제를 담당하고, MirrorHeartbeatConnector는 복제 파이프라인의 생존 여부를 알리는 하트비트를 전송합니다.
</details>

9. MirrorMaker 2의 기본 `DefaultReplicationPolicy`에서 사용하는 원격 토픽 이름 규칙은 무엇인가요?
   - A) `<토픽>.<소스 클러스터 별칭>`
   - B) `<소스 클러스터 별칭>.<토픽>`
   - C) `mirror-<토픽>`
   - D) 원본 토픽 이름을 그대로 유지

<details>

<summary>정답 보기</summary>

**정답: B) `<소스 클러스터 별칭>.<토픽>`**

**설명:**
`DefaultReplicationPolicy`는 원격 토픽 이름을 `<소스 클러스터 별칭>.<토픽>` 형식으로 짓습니다. 예를 들어 별칭이 `us-east-1`인 클러스터의 `orders` 토픽을 복제하면 타깃 클러스터에는 `us-east-1.orders` 토픽이 생성됩니다. 원본 이름을 그대로 유지하려면 `IdentityReplicationPolicy`를 사용해야 하지만, 이 경우 active-active 구성에서 루프 방지가 더 어려워집니다.
</details>

10. Active-Passive DR 패턴과 Active-Active DR 패턴의 핵심적인 차이는 무엇인가요?
    - A) Active-Passive는 데이터를 압축하고 Active-Active는 압축하지 않는다
    - B) Active-Passive는 단방향 복제만 수행하고, Active-Active는 양방향 복제를 수행하며 루프 방지가 필요하다
    - C) Active-Active는 MirrorMaker 2를 사용하지 않는다
    - D) Active-Passive만 KafkaConnector CRD를 사용한다

<details>

<summary>정답 보기</summary>

**정답: B) Active-Passive는 단방향 복제만 수행하고, Active-Active는 양방향 복제를 수행하며 루프 방지가 필요하다**

**설명:**
Active-Passive 패턴은 프라이머리 클러스터에서 DR 클러스터로만 단방향 복제를 수행하며, DR 클러스터는 평상시 대기 상태입니다. Active-Active 패턴은 두 클러스터가 서로를 향해 양방향으로 복제를 수행하여 두 리전 모두 트래픽을 처리할 수 있게 하지만, 복제된 토픽이 다시 원본 클러스터로 재복제되어 무한 루프가 발생하지 않도록 `replication.policy.class`와 토픽 필터를 이용한 루프 방지 장치가 반드시 필요합니다.
</details>

## 단답형 문제

11. MirrorMaker 2에서 소스 클러스터가 살아있고 복제 파이프라인이 정상 동작 중임을 알리기 위해 주기적으로 하트비트 메시지를 전송하는 커넥터의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: MirrorHeartbeatConnector**

**설명:**
MirrorHeartbeatConnector는 소스 클러스터가 정상적으로 동작하고 있으며 복제 파이프라인이 단절되지 않았음을 나타내는 하트비트 메시지를 주기적으로 전송합니다. 이 하트비트가 일정 시간 이상 수신되지 않으면 복제 지연이나 소스 클러스터 연결 장애를 감지할 수 있는 신호로 활용할 수 있습니다.
</details>

12. Strimzi Kafka Connect 분산 워커들이 오프셋, 커넥터/태스크 설정, 실행 상태를 저장하기 위해 사용하는 세 가지 내부 토픽 설정 키의 접미사 이름을 각각 무엇이라 부르나요? (예: offset.storage.topic)

<details>

<summary>정답 보기</summary>

**정답: `offset.storage.topic`, `config.storage.topic`, `status.storage.topic`**

**설명:**
분산 모드 Connect 워커는 오프셋을 저장하는 `offset.storage.topic`, 커넥터/태스크 설정을 저장하는 `config.storage.topic`, 실행 상태를 저장하는 `status.storage.topic` 세 가지 내부 토픽을 사용합니다. 이 토픽들이 손상되면 클러스터의 모든 커넥터 상태가 유실될 수 있으므로, 운영 환경에서는 반드시 복제 팩터를 3 이상으로 설정해야 합니다.
</details>

13. MirrorMaker 2의 소스 클러스터 토픽 ACL을 타깃 클러스터에도 동기화할지를 제어하는 설정 키는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `sync.topic.acls.enabled`**

**설명:**
`sync.topic.acls.enabled`를 `true`로 설정하면 소스 클러스터의 토픽 ACL이 타깃 클러스터에도 그대로 동기화되어 접근 제어 정책을 이중으로 관리할 필요가 없습니다. 다만 두 클러스터의 보안 모델이 다르다면(예: DR 클러스터에서 더 제한적인 접근이 필요한 경우) 비활성화하고 별도로 관리하는 것이 더 안전할 수 있습니다.
</details>

14. MirrorMaker 2가 노출하는, 소스에서 메시지가 생성된 시점부터 타깃에 복제 완료되기까지의 지연을 나타내는 메트릭 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `replication-latency-ms`**

**설명:**
`replication-latency-ms`는 MirrorMaker 2가 노출하는 핵심 메트릭 중 하나로, 소스 클러스터에서 메시지가 생성된 시점부터 타깃 클러스터에 완전히 복제되기까지 걸린 시간을 나타냅니다. 이 메트릭을 Prometheus로 수집하고 알람을 설정하면 복제 지연 SLA를 지속적으로 검증할 수 있습니다.
</details>

15. Strimzi에서 여러 개의 `KafkaMirrorMaker2` 클러스터 설정 중, MM2 워커 Pod가 자체 내부 토픽(오프셋, 설정 등)을 저장할 클러스터를 지정하는 `spec` 필드의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `connectCluster`**

**설명:**
`KafkaMirrorMaker2.spec.connectCluster`는 `spec.clusters` 목록에 정의된 클러스터 별칭 중 하나를 가리키며, MM2 워커 Pod가 자신의 Kafka Connect 내부 토픽(오프셋, 설정, 상태 저장 토픽)을 어느 클러스터에 저장할지를 결정합니다. 일반적으로 DR 또는 타깃 클러스터를 `connectCluster`로 지정합니다.
</details>

## 실습 문제

16. `strimzi.io/use-connector-resources: "true"` 어노테이션이 설정된 `KafkaConnect` 클러스터 `connect-cluster` 위에서 동작할, Debezium PostgreSQL 소스 커넥터에 대한 `KafkaConnector` 리소스를 작성하세요. 태스크는 1개로 제한합니다.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-db-source
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: orders-db.xxxxxxx.us-east-1.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${secrets:kafka/debezium-db-credentials:password}"
    database.dbname: orders
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    table.include.list: public.orders,public.order_items
```

**설명:**
`metadata.labels.strimzi.io/cluster: connect-cluster`는 이 `KafkaConnector`가 어느 `KafkaConnect` 클러스터 위에서 실행되어야 하는지를 Strimzi Operator에게 알려줍니다. `spec.class`는 실제 커넥터 구현 클래스(Debezium PostgreSQL 커넥터)를 지정하며, `plugin.name: pgoutput`은 PostgreSQL의 논리적 복제 출력 플러그인을 지정합니다. `tasksMax: 1`은 PostgreSQL 소스 커넥터가 단일 복제 슬롯만 사용할 수 있어 태스크를 병렬화할 수 없기 때문입니다.
</details>

17. 두 개의 Kafka 클러스터(별칭 `us-east-1`, `dr-region`) 사이에서 `us-east-1`의 `orders.*`, `payments.*` 패턴 토픽을 `dr-region`으로 단방향 복제하고, 컨슈머 그룹 오프셋도 함께 동기화하는 `KafkaMirrorMaker2` 리소스를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 3.9.0
  replicas: 3
  connectCluster: dr-region
  clusters:
    - alias: us-east-1
      bootstrapServers: primary-kafka-bootstrap.us-east-1.example.com:9093
    - alias: dr-region
      bootstrapServers: dr-kafka-bootstrap.us-west-2.example.com:9093
      config:
        config.storage.replication.factor: 3
        offset.storage.replication.factor: 3
        status.storage.replication.factor: 3
  mirrors:
    - sourceCluster: us-east-1
      targetCluster: dr-region
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          sync.topic.acls.enabled: "true"
      heartbeatConnector:
        config:
          heartbeats.topic.replication.factor: 3
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          sync.group.offsets.enabled: "true"
      topicsPattern: "orders.*|payments.*"
      groupsPattern: "orders-consumer-.*"
```

**설명:**
`mirrors` 목록의 각 항목이 하나의 복제 방향(`sourceCluster` → `targetCluster`)을 정의합니다. `topicsPattern`으로 복제 대상 토픽을 `orders.*`와 `payments.*`로 제한하고, `checkpointConnector.config.sync.group.offsets.enabled: "true"`를 설정해 컨슈머 그룹 오프셋 변환 결과를 타깃 클러스터의 `__consumer_offsets`에 반영합니다. `connectCluster: dr-region`은 MM2 워커가 내부 토픽을 저장할 클러스터를 DR 리전으로 지정합니다.
</details>

18. Active-Active 구성에서 토픽이 A → B → A로 무한히 재복제되는 것을 방지하기 위해 확인해야 할 두 가지 설정을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
1. `replication.policy.class` — 기본값인 `DefaultReplicationPolicy`를 사용하면 이미 원격 접두사(`<별칭>.<토픽>`)가 붙은 토픽은 자동으로 재복제 대상에서 제외됩니다.
2. `topicsPattern` — 각 미러 방향에서 실제로 복제가 필요한 토픽만 명시적으로 포함하도록 패턴을 좁혀, 의도치 않은 토픽이 순환 복제되는 상황을 원천적으로 방지합니다.

**설명:**
`DefaultReplicationPolicy`의 네이밍 규칙(`<소스 클러스터 별칭>.<토픽>`) 자체가 루프 방지의 1차 방어선입니다. 원격 접두사가 붙은 토픽(예: `A.orders`)을 B에서 다시 A로 미러링하려고 하면, MM2는 이미 접두사가 붙은 토픽임을 인식하고 재복제하지 않습니다. 여기에 더해 `topicsPattern`으로 미러링 범위를 명확히 좁혀두면 설정 실수나 예외적인 토픽 이름 패턴으로 인한 루프 위험을 한 번 더 줄일 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [다음 퀴즈: MSK 통합](./06-msk-integration-quiz.md)
