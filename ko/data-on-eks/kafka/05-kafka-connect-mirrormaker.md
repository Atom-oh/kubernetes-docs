# Part 5: Kafka Connect와 MirrorMaker

> **지원 버전**: Strimzi 0.45+, Kafka 3.9, MirrorMaker 2\
> **마지막 업데이트**: 2026년 7월 9일

## Kafka Connect 개요

Kafka Connect는 Kafka와 외부 시스템(데이터베이스, 객체 스토리지, 검색 엔진 등) 사이에서 데이터를 이동시키기 위한 프레임워크입니다. 커넥터 플러그인을 직접 코드로 작성하지 않고도, 설정(config)만으로 데이터 이동 파이프라인을 선언적으로 구성할 수 있습니다.

커넥터는 방향에 따라 두 종류로 나뉩니다.

* **소스 커넥터(Source Connector)**: 외부 시스템의 데이터를 Kafka 토픽으로 끌어옵니다. 대표적으로 Debezium은 데이터베이스의 WAL/binlog를 읽어 변경 이벤트를 Kafka로 스트리밍하는 CDC(Change Data Capture) 소스 커넥터이며, JDBC Source Connector는 쿼리 기반으로 테이블 데이터를 주기적으로 폴링해 Kafka에 적재합니다.
* **싱크 커넥터(Sink Connector)**: Kafka 토픽의 데이터를 외부 시스템으로 내보냅니다. 대표적으로 S3 Sink Connector는 토픽 데이터를 Parquet/JSON 형식으로 S3에 적재하고, Elasticsearch Sink Connector는 검색/분석을 위해 Elasticsearch 인덱스에 데이터를 반영합니다.

Kafka Connect는 두 가지 실행 모드를 지원합니다.

* **분산 모드(Distributed Mode)**: 여러 워커 프로세스(Pod)가 그룹을 이루어 하나의 Connect 클러스터로 동작합니다. 워커 중 하나가 그룹 코디네이터 역할을 맡아 커넥터/태스크를 워커들에게 분배하며, 워커가 죽으면 해당 태스크는 살아있는 다른 워커로 자동 재배치됩니다. 커넥터 생성·삭제·설정 변경은 REST API(기본 포트 8083)를 통해 수행합니다. Kubernetes/Strimzi 환경에서는 항상 이 모드를 사용합니다.
* **standalone 모드**: 단일 프로세스에서 파일 기반 오프셋 저장소로 동작하는 모드로, 로컬 개발/테스트 용도입니다. 고가용성과 확장성이 없어 Kubernetes 위에서는 사용하지 않습니다.

분산 모드의 워커들은 오프셋, 커넥터/태스크 설정, 실행 상태를 저장하기 위해 각각 내부 토픽(`offset.storage.topic`, `config.storage.topic`, `status.storage.topic`)을 사용합니다. 이 토픽들이 손상되면 클러스터의 모든 커넥터 상태가 유실될 수 있으므로, 운영 환경에서는 반드시 복제 팩터를 3 이상으로 설정합니다.

## Strimzi에서 Kafka Connect 배포

Strimzi는 `KafkaConnect` CRD로 분산 모드 Connect 클러스터 자체를, `KafkaConnector` CRD로 그 위에서 동작하는 개별 커넥터 인스턴스를 각각 선언적으로 관리합니다. `KafkaConnector`를 사용하면 REST API를 직접 호출하지 않고도 GitOps 방식으로 커넥터를 배포·버전 관리할 수 있습니다. `KafkaConnector`를 활성화하려면 `KafkaConnect` 리소스에 `strimzi.io/use-connector-resources: "true"` 어노테이션이 필요합니다.

커넥터 플러그인은 기본 Strimzi Kafka Connect 이미지에 포함되어 있지 않으므로, 별도로 이미지를 빌드해야 합니다. Strimzi가 권장하는 방식은 Dockerfile을 직접 작성하는 대신 `KafkaConnect.spec.build`에 플러그인 아티팩트(tgz/zip/jar, Maven 좌표 등)의 URL만 선언하면 Strimzi Operator가 빌드를 수행하고 결과 이미지를 지정한 레지스트리(예: Amazon ECR)로 푸시하는 것입니다.

### KafkaConnect 빌드 스펙

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 3.9.0
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap:9093
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  config:
    group.id: connect-cluster
    offset.storage.topic: connect-cluster-offsets
    config.storage.topic: connect-cluster-configs
    status.storage.topic: connect-cluster-status
    offset.storage.replication.factor: 3
    config.storage.replication.factor: 3
    status.storage.replication.factor: 3
    key.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter: org.apache.kafka.connect.json.JsonConverter
  build:
    output:
      type: docker
      image: <account-id>.dkr.ecr.<region>.amazonaws.com/connect-cluster:latest
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.7.3.Final/debezium-connector-postgres-2.7.3.Final-plugin.tar.gz
      - name: aiven-s3-sink
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.0/s3-sink-connector-for-apache-kafka-3.4.0.zip
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

Operator는 `spec.build`가 바뀔 때마다(플러그인 추가/버전 변경) 자동으로 새 이미지를 빌드하고 Deployment를 롤아웃합니다. ECR 푸시를 위해서는 `pushSecret`으로 지정한 Kubernetes Secret에 레지스트리 인증 정보(`docker-registry` 타입)가 있어야 하며, 필요 시 IRSA를 통해 ECR 접근 권한을 부여할 수도 있습니다.

### KafkaConnector — Debezium PostgreSQL 소스 예시

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

### KafkaConnector — S3 싱크 예시

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.S3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: orders-data-lake
    aws.s3.region: us-east-1
    format.output.type: jsonl
    file.compression.type: gzip
    flush.size: 10000
    rotate.schedule.interval.ms: 300000
```

`kubectl get kafkaconnector -n kafka`로 각 커넥터의 상태를 조회할 수 있으며, `status.conditions`에 `Ready: True`가 표시되면 태스크가 정상적으로 배정되어 실행 중임을 의미합니다.

## MirrorMaker 2 아키텍처

MirrorMaker 2(MM2)는 Kafka Connect 프레임워크 위에서 동작하는 토픽 단위 클러스터 간 복제 도구입니다. 단순히 메시지를 복사하는 것을 넘어, 소스 클러스터의 파티셔닝을 그대로 보존하고 컨슈머 그룹의 오프셋까지 변환해주기 때문에 재해복구(DR) 시 컨슈머를 원활하게 전환할 수 있습니다. MM2는 내부적으로 세 가지 커넥터로 구성됩니다.

* **MirrorSourceConnector**: 실제 메시지 복제를 담당하며, 토픽/설정/ACL도 함께 동기화합니다.
* **MirrorCheckpointConnector**: 소스 클러스터의 컨슈머 그룹 오프셋을 타깃 클러스터의 오프셋으로 주기적으로 변환(offset translation)하여 체크포인트 토픽에 기록합니다. 이 정보가 있어야 페일오버 시 컨슈머가 "어디까지 처리했는지"를 DR 클러스터에서도 알 수 있습니다.
* **MirrorHeartbeatConnector**: 소스 클러스터가 살아있고 복제 파이프라인이 정상 동작 중임을 나타내는 하트비트 메시지를 주기적으로 전송하여, 복제 지연이나 단절을 감지할 수 있게 합니다.

MM2는 복제된 토픽에 원본 토픽과 동일한 이름을 그대로 사용하지 않습니다. 기본 `DefaultReplicationPolicy`는 `<소스 클러스터 별칭>.<토픽>` 형식으로 원격 토픽 이름을 짓습니다. 예를 들어 별칭이 `us-east-1`인 클러스터의 `orders` 토픽을 복제하면 타깃 클러스터에는 `us-east-1.orders` 토픽이 생성됩니다. 이 네이밍 규칙 덕분에 컨슈머는 메시지가 로컬에서 생성된 것인지 다른 리전에서 복제되어 온 것인지 토픽 이름만으로 구분할 수 있고, 동시에 양방향 복제 시 무한 루프를 방지하는 기준으로도 사용됩니다.

## 재해복구 패턴

### Active-Passive

가장 널리 쓰이는 패턴으로, 프라이머리 리전 클러스터에서 DR 리전 클러스터로 단방향 복제만 수행합니다. 평상시 애플리케이션은 프라이머리 클러스터만 사용하고, DR 클러스터는 대기 상태로 복제된 데이터만 쌓아둡니다. 리전 장애가 발생하면 MirrorCheckpointConnector가 기록해 둔 오프셋 변환 정보를 이용해 컨슈머 그룹을 DR 클러스터로 전환하고, 가능한 최근 체크포인트부터 소비를 재개합니다. 완벽한 정확히-한-번(exactly-once) 전환은 아니며 페일오버 시점에 따라 소량의 메시지가 중복 처리될 수 있고, MM2 복제는 비동기이므로 장애 시점에 아직 DR로 복제되지 않은 메시지는 유실될 수 있습니다(RPO는 0이 아니라 복제 랙에 의해 결정됩니다) — 그럼에도 유실 범위를 복제 랙 수준으로 최소화하면서 빠르게 서비스를 재개할 수 있다는 점이 핵심 가치입니다.

### Active-Active

두 리전이 모두 트래픽을 받는 구조로, 양쪽 클러스터가 서로를 향해 양방향으로 복제를 수행합니다. 이 구조에서는 A → B로 복제된 토픽(`A.orders`)이 다시 B → A 방향으로 재복제되어 무한 루프가 발생하지 않도록 반드시 루프 방지 장치가 필요합니다. Strimzi/MM2는 `replication.policy.class`로 지정하는 네이밍 정책(기본 `DefaultReplicationPolicy` 또는 원본 이름을 그대로 유지하는 `IdentityReplicationPolicy`)을 통해, 이미 원격 접두사가 붙은 토픽(`A.orders`)은 다시 미러링 대상에서 제외하는 방식으로 루프를 차단합니다. 여기에 더해 `topicsPattern`으로 애초에 미러링할 토픽 범위를 좁혀두면 의도치 않은 순환 복제 위험을 한 번 더 줄일 수 있습니다.

### KafkaMirrorMaker2 CR 예시

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
      tls:
        trustedCertificates:
          - secretName: primary-cluster-ca-cert
            certificate: ca.crt
      authentication:
        type: tls
        certificateAndKey:
          secretName: mm2-user
          certificate: user.crt
          key: user.key
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

`connectCluster: dr-region`은 MM2 워커 Pod 자체가 어느 클러스터(여기서는 DR 리전)를 기준으로 커넥트 내부 토픽을 저장할지를 지정합니다. `sync.group.offsets.enabled: "true"`를 켜면 MirrorCheckpointConnector가 변환한 오프셋을 DR 클러스터의 `__consumer_offsets`에 주기적으로 반영해, 페일오버 시 컨슈머가 별도 커밋 없이 이어서 소비를 시작할 수 있습니다.

## 지역 간 복제 시 고려사항

* **네트워크 비용과 지연**: 리전 간(또는 AZ 간) 복제는 데이터 전송 비용과 왕복 지연을 동반합니다. MM2 워커는 대상 리전에 배치하고 소스 클러스터로부터 데이터를 "당겨오는(pull)" 구조로 운영하는 것이 일반적이며, 배치 크기(`producer.override.batch.size`)와 압축(`producer.override.compression.type: zstd`)을 조정해 전송량을 줄이는 것이 비용 절감에 직접적으로 도움이 됩니다.
* **`sync.topic.acls.enabled`**: 소스 클러스터의 토픽 ACL을 타깃 클러스터에도 동기화할지 여부를 결정합니다. 활성화하면 접근 제어 정책을 이중으로 관리할 필요가 없지만, 두 클러스터의 보안 모델이 다르다면(예: DR 클러스터에서 더 제한적인 접근이 필요한 경우) 비활성화하고 별도로 관리하는 편이 안전할 수 있습니다.
* **복제 지연 모니터링**: MM2는 자체 메트릭으로 복제 상태를 노출합니다. `replication-latency-ms`는 소스에서 메시지가 생성된 시점부터 타깃에 복제 완료되기까지의 지연을, 체크포인트 커넥터의 랙 관련 메트릭은 오프셋 변환이 얼마나 최신 상태를 반영하고 있는지를 보여줍니다. 이 메트릭들을 Prometheus로 스크레이핑해 SLA(예: "복제 지연 5분 이내")를 알람으로 설정해 두면, DR 클러스터가 실제 페일오버에 사용할 수 있는 상태인지 지속적으로 검증할 수 있습니다.

## 다음 단계

Kafka Connect와 MirrorMaker 2로 데이터 이동과 재해복구 파이프라인을 구성했다면, 다음으로는 이 워크로드를 완전 관리형 서비스인 Amazon MSK와 어떻게 통합하거나 비교할지 살펴볼 차례입니다. 이는 [Part 6: MSK 통합](./06-msk-integration.md)에서 다룹니다.

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)를 풀어보세요.
