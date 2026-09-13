# Part 5: Kafka Connect와 MirrorMaker

> **검토 기준**: Strimzi 1.2.0, Kafka 4.3.1, Debezium PostgreSQL 3.6.2.Final, Aiven S3 sink 3.4.3\
> **최종 검토**: 2026년 9월 12일

## Connect 워커와 커넥터

Kafka Connect는 Kafka와 외부 시스템 사이에서 데이터를 이동하는 플러그인을
실행합니다. 알맞은 플러그인이 이미 있고 DB·스토리지 권한, 데이터 형식과 네트워크
조건을 갖춘 경우에 설정만으로 연동할 수 있습니다.

| 방향 | 예시 | 구분할 점 |
| --- | --- | --- |
| 소스: 외부 시스템 → Kafka | Debezium PostgreSQL CDC | 최초 스냅샷과 논리 WAL 스트리밍은 JDBC 폴링과 다름 |
| 싱크: Kafka → 외부 시스템 | Aiven S3 sink | 지원 형식과 전달 동작은 선택한 플러그인에 따라 다름 |

분산 모드에서는 **Kafka 브로커**가 워커 그룹을 조정하고, 선출된 워커 리더가
할당을 계산합니다. 워커 장애 후 재할당에는 시간이 걸리고 재처리가 발생할 수
있습니다. 커넥터 태스크 실패와 워커 장애는 같은 사건이 아닙니다. 실패를 살피고
필요한 재시작 동작을 구성합니다.

Standalone도 컨테이너나 Kubernetes에서 실행할 수 있지만 분산 워커 장애 조치를
제공하지 않습니다. Strimzi의 `KafkaConnect`는 분산 모드를 관리합니다. 워커가
3개라고 단일 태스크 PostgreSQL 커넥터가 태스크 3개를 실행하는 것은 아닙니다.

분산 Connect의 config·source offset·status 토픽은 compaction을 사용합니다.
config 토픽은 **파티션 1개**여야 합니다. 배포마다 고유한 그룹 ID와 내부 토픽 이름을
사용합니다. 이 예제는 브로커가 3대라 RF=3을 사용하며, 더 적은 브로커에서도 적용할
수 있는 보편적 최솟값은 아닙니다. 복제는 백업을 대신하지 않습니다. 싱크의 소비
오프셋은 일반적으로 source-offset 저장 토픽이 아닌 Kafka 컨슈머 그룹에 있습니다.

## Strimzi v1은 apiVersion만 바꾸는 변경이 아님

Strimzi 1.2.0은 `kafka.strimzi.io/v1` API를 제공합니다. 업그레이드 전에 해당
릴리스의 변환 절차를 수행하며 `v1beta2` 문자열만 바꾸지 않습니다.

| 리소스 | 현재 v1 필드 |
| --- | --- |
| KafkaConnect 워커 그룹 | `spec.groupId` |
| KafkaConnect 내부 토픽 이름 | `spec.configStorageTopic`, `spec.offsetStorageTopic`, `spec.statusStorageTopic` |
| KafkaMirrorMaker2 목적지·워커 저장소 | `spec.target` 및 그 안의 `groupId`, 내부 토픽 이름 3개 |
| KafkaMirrorMaker2 소스 연결 | `spec.mirrors[].source` |

기존 MM2의 `connectCluster`, `clusters`, `sourceCluster`, `targetCluster`,
`heartbeatConnector`는 이 v1 스키마의 필드가 아닙니다. Apache MM2에 heartbeat
커넥터 구현이 있다고 `KafkaMirrorMaker2` v1에서 해당 필드를 설정할 수 있는 것은 아닙니다.

## Connect 예제 준비

[Part 2](./02-strimzi-operator.md)의 브로커 3대인 `my-cluster`, TLS/SCRAM과
Topic/User Operator를 사용합니다. ECR 계정·저장소와 DB/S3 예제 이름을 실제 값으로
바꾸고 다음 의존성을 준비합니다.

- `debezium-db-credentials`: `password` 키를 가진 Kubernetes Secret.
- `rds-ca`: PostgreSQL/RDS의 신뢰할 CA 체인을 `ca.crt`로 가진 Secret.
- 기존 ECR 저장소, `kubernetes.io/dockerconfigjson` 타입의 유효한
  `ecr-registry-credentials` push Secret과 노드의 이미지 pull 권한.
- **Connect Pod**의 S3 접근용 워크로드 ID. Pod Identity 또는 IRSA를 구성하고
  실제 플러그인의 자격증명 체인을 확인하며 대상 버킷·접두사로 권한을 제한합니다.
  이미지 빌드·push와 실행 중 S3 접근은 서로 다른 인증 경로입니다.

ECR 인증 토큰은 12시간 뒤 만료되므로 빌드 전에 push Secret을 갱신·관리합니다.
IRSA 역할만 부여했다고 선택한 이미지 빌더의 ECR 로그인이 검증되는 것은 아닙니다.
Strimzi 1.2는 기본적으로 Buildah 빌드 기능을 사용하므로 실제 노드에서 빌드 Pod의
요구사항을 확인합니다.

다음을 `create-topics.py`로 저장·실행하고 생성한 `connect-topics.json`을
적용합니다. 데이터 토픽의 7일 보존은 실습의 선택이며 장애·복구 요구에 맞게
보존 기간과 용량을 결정해야 합니다.

```python
import json
from pathlib import Path

topics = [
    ("connect-cluster-configs", 1, "compact"),
    ("connect-cluster-offsets", 3, "compact"),
    ("connect-cluster-status", 3, "compact"),
    ("orders-db.public.orders", 3, "delete"),
    ("orders-db.public.order_items", 3, "delete"),
]
items = []
for name, partitions, cleanup in topics:
    config = {"cleanup.policy": cleanup, "min.insync.replicas": 2}
    if cleanup == "delete":
        config["retention.ms"] = 604800000
    items.append({
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaTopic",
        "metadata": {"name": name, "namespace": "kafka",
                     "labels": {"strimzi.io/cluster": "my-cluster"}},
        "spec": {"partitions": partitions, "replicas": 3, "config": config},
    })
Path("connect-topics.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": items}, indent=2) + "\n")
```

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: connect-cluster
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
          name: connect-cluster-
          patternType: prefix
        operations: [Read, Write, Create, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: orders-db.
          patternType: prefix
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: connect-cluster
          patternType: literal
        operations: [Read]
      - resource:
          type: group
          name: connect-orders-s3-sink
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

사용자 리소스는 `connect-user.yaml`로 저장합니다. 생성 권한은 Connect 내부 토픽
접두사로 제한하고 Topic Operator로 5개 토픽을 명시적인 설정으로 미리 생성합니다.
소스의 데이터 토픽 자동 생성은 끕니다. 테이블이나 토픽을 추가하면 이 구성도
명시적으로 갱신합니다.

## Connect 빌드와 배포

`connect.yaml`로 저장합니다. 두 플러그인 다운로드에 SHA-512 검증값을 넣었습니다.
`spec.build`는 지원되는 한 가지 방법이며, 미리 검증한 이미지나 지원되는 플러그인
이미지 볼륨도 선택할 수 있습니다. 빌드 성공이 DB/S3 접근 성공을 뜻하지는 않습니다.

directory config provider는 허용한 경로에 마운트된 Secret을 읽으므로 Kubernetes
API의 Secret 읽기 RBAC가 필요하지 않습니다. provider와 권한 구성이 빠진 기존
`${secrets:...}` 예제를 이 방식으로 바꿨습니다.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 4.3.1
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
  groupId: connect-cluster
  configStorageTopic: connect-cluster-configs
  offsetStorageTopic: connect-cluster-offsets
  statusStorageTopic: connect-cluster-status
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  authentication:
    type: scram-sha-512
    username: connect-cluster
    passwordSecret:
      secretName: connect-cluster
      password: password
  config:
    config.storage.replication.factor: 3
    offset.storage.replication.factor: 3
    status.storage.replication.factor: 3
    offset.flush.interval.ms: 60000
    topic.creation.enable: false
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    config.providers: dir
    config.providers.dir.class: org.apache.kafka.common.config.provider.DirectoryConfigProvider
    config.providers.dir.param.allowed.paths: /mnt/debezium
  template:
    pod:
      volumes:
        - name: debezium-credentials
          secret:
            secretName: debezium-db-credentials
        - name: rds-ca
          secret:
            secretName: rds-ca
    connectContainer:
      volumeMounts:
        - name: debezium-credentials
          mountPath: /mnt/debezium
          readOnly: true
        - name: rds-ca
          mountPath: /mnt/rds-ca
          readOnly: true
  build:
    output:
      type: docker
      image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/connect-cluster:kafka4.3.1-deb3.6.2-s3-3.4.3
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo.maven.apache.org/maven2/io/debezium/debezium-connector-postgres/3.6.2.Final/debezium-connector-postgres-3.6.2.Final-plugin.tar.gz
            sha512sum: eabc5416446a32c3c763749262cd03115fbc2804bf48018348184f660222e9e5c8395306d9e795c9d52cbe246a5386142bdae376d418f6cf1bd5233e83e8ffe7
      - name: aiven-s3
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.3/s3-sink-connector-for-apache-kafka-3.4.3.zip
            sha512sum: d355c7d41713dab83384a51e28b6670f63775a0aa394eb0d9e99172d862f53d9e42c54534369cdcfefadfeb4f50e7ffac2029c65dd878f0def3db33058627758
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

```bash
python3 create-topics.py
kubectl apply -f connect-topics.json -f connect-user.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/connect-cluster
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/connect-cluster-configs kafkatopic/connect-cluster-offsets \
  kafkatopic/connect-cluster-status kafkatopic/orders-db.public.orders \
  kafkatopic/orders-db.public.order_items
kubectl apply -f connect.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=900s kafkaconnect/connect-cluster
```

`strimzi.io/use-connector-resources: "true"`일 때 커넥터 변경은 CR로 관리합니다.
REST에서 직접 변경하면 조정 과정에서 되돌아갈 수 있습니다. Connect REST API와
Kubernetes 갱신 권한을 제한합니다. 같은 워커 배포의 플러그인들은 마운트된 Secret과
워크로드 ID를 공유하므로 신뢰 범위가 다르면 Connect 배포도 분리합니다.

## PostgreSQL CDC 소스

`source.yaml` 적용 전에 PostgreSQL 논리 복제, replication slot·WAL sender,
복제 사용자와 테이블 권한을 준비합니다. RDS PostgreSQL의 논리 복제 파라미터 활성화는
재부팅이 필요할 수 있으므로 실제 엔진 버전의 절차를 따릅니다. 멈춘 slot이 WAL을
계속 보존해 저장소를 채울 수 있으므로 관찰합니다. 재시작할 때마다 slot을 삭제하지 않습니다.

권한이 있는 테이블 소유자가 `orders` DB에서 publication을 만듭니다.

```sql
CREATE PUBLICATION debezium_orders_pub
FOR TABLE public.orders, public.order_items;
```

필요한 update/delete 이벤트에 맞는 기본 키·replica identity를 갖춥니다.
커넥터는 최초 스냅샷 후 WAL을 읽습니다. PostgreSQL 커넥터는 태스크 1개를 사용하며
`tasksMax`는 최대치이지 병렬 실행 보장이 아닙니다.

```yaml
apiVersion: kafka.strimzi.io/v1
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
    database.hostname: orders-db.REPLACE.ap-northeast-2.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${dir:/mnt/debezium:password}"
    database.dbname: orders
    database.sslmode: verify-full
    database.sslrootcert: /mnt/rds-ca/ca.crt
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    publication.name: debezium_orders_pub
    publication.autocreate.mode: disabled
    table.include.list: 'public[.]orders,public[.]order_items'
    snapshot.mode: initial
```

비밀번호는 마운트 경로로 참조하며 매니페스트에 출력하지 않습니다. Secret 변경이
기존 DB 연결에 즉시 반영된다고 가정하지 말고 자격증명 교체와 재시작·재설정을 시험합니다.

## Aiven S3 싱크

`sink.yaml`로 저장합니다. 3.4.3의 실제 클래스는
`io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector`입니다.
기존 예제의 `io.aiven.kafka.connect.s3.S3SinkConnector`는 해당 아티팩트에 없습니다.
`flush.size`, `rotate.schedule.interval.ms`도 이 커넥터의 설정 키가 아니므로
다른 공급자의 S3 커넥터 설정을 그대로 복사하지 않습니다.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: REPLACE-WITH-YOUR-BUCKET
    aws.s3.region: ap-northeast-2
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    format.output.type: jsonl
    format.output.fields: key,value,offset,timestamp
    file.compression.type: gzip
    file.max.records: 10000
```

이 구성은 작업 유형과 before/after 값을 가진 **CDC 이벤트 envelope**를 저장하며
현재 행 상태의 테이블을 자동 생성하지 않습니다. 소스와 싱크 모두 schema envelope를
켜 둔 JSON converter를 사용합니다. 실제 Kafka 레코드와 converter 설정을 맞춥니다.
`file.max.records`는 묶을 레코드 수를 제어하고 워커의 `offset.flush.interval.ms`는
주기적인 flush에 영향을 줍니다. 모든 객체가 정해진 시간 안에 도착한다는 보장은 아닙니다.

명시적 자격증명 옵션이 없으면 AWS 기본 자격증명 체인을 사용합니다. 필요한 객체·
multipart 권한은 대상 범위로 제한하고 필요하면 KMS 키 권한도 준비합니다.
정상 이벤트, 삭제, tombstone, 재시도와 재시작 시 재처리를 시험한 뒤 복구용
아카이브로 사용합니다. S3 객체 저장만으로 전체 경로의 exactly-once가 보장되지 않습니다.

```bash
kubectl apply -f source.yaml -f sink.yaml
kubectl -n kafka get kafkaconnector orders-db-source orders-s3-sink -o yaml
```

현재 generation, conditions, `status.connectorStatus.connector.state`와
모든 태스크의 state/trace를 확인하고 실제 소스·목적지의 데이터 진행도 검사합니다.
`Ready=True`는 Operator의 상태 관찰이며 데이터가 최신이라는 증거는 아닙니다.

## MirrorMaker 2와 재해복구

MM2는 레코드 바이트와 파티션 번호를 유지하면서 새 타깃 오프셋으로 씁니다.
소스의 오프셋 숫자, 스키마 레지스트리 ID 매핑, 애플리케이션 트랜잭션,
외부 싱크 상태와 모든 보안 정책을 자동 이전하지는 않습니다.

| 구성요소 | 역할과 한계 |
| --- | --- |
| MirrorSourceConnector | 레코드 복사와 offset-sync 매핑 생성; 토픽·설정·ACL 동기화는 옵션에 따라 동작 |
| MirrorCheckpointConnector | 소스 그룹 오프셋 변환과 체크포인트 생성; 조건을 만족하는 비활성 타깃 그룹 갱신 가능 |
| Apache MirrorHeartbeatConnector | 하트비트 생성; 태스크가 소스 데이터를 읽지 않고도 생성할 수 있어 수신만으로 소스 정상·전체 복제 완료를 보장하지 않음 |

Active-passive는 단방향 복제와 명시적인 전환 절차를 사용합니다. 소스를 복구할 수
없으면 장애 전까지 복제되지 않은 레코드를 잃을 수 있습니다. 재처리 중복의 범위가
항상 작지는 않습니다. 복제·체크포인트의 최신성을 측정하고 이전 writer를 차단한 뒤,
타깃 권한·스키마를 확인하고 애플리케이션 주소·구독 토픽을 바꾸어 재개 위치를
검증합니다. MM2가 이러한 애플리케이션 전환까지 수행하지는 않습니다.

Active-active에서 `DefaultReplicationPolicy`는 원격 토픽 접두사를 사용하여
**기원 경로에 이미 있는 별칭으로 돌아가는 순환**을 감지합니다. 접두사가 있는 모든
토픽을 제외하는 것은 아닙니다. 제3 클러스터로의 다단계 복제는 가능할 수 있습니다.
`IdentityReplicationPolicy`는 이 이름 정보를 잃으므로 같은 수준의 순환 방지를
제공하지 않습니다. 방향별 필터와 쓰기 소유권을 설계하며 두 writer의 충돌을
자동 해결하는 기능으로 취급하지 않습니다.

## 현재 KafkaMirrorMaker2 v1 예제

이 단방향 템플릿은 클러스터 간 DNS·네트워크, 타깃 브로커 3대, `kafka` 네임스페이스의
소스·타깃 Secret과 별도로 준비한 Kafka ACL을 요구합니다. 주소는 자리표시자입니다.
워커는 두 클러스터에 접근할 수 있는 곳에 배치합니다. `spec.target`은 Kafka 저장소를
선택하며 Kubernetes 배포 리전을 정하지 않습니다.

| 사용자 | 계획할 권한 범위 |
| --- | --- |
| 소스 | 선택한 토픽 읽기·조회, 선택한 그룹 오프셋 조회 |
| 타깃 | Connect 내부 토픽·워커 그룹, 의도한 원격·MM2 내부 토픽 쓰기·생성, 매핑·체크포인트 읽기, 선택한 비활성 그룹 오프셋 갱신 |

내부 토픽을 알맞은 compaction·파티션 구성으로 미리 만들거나 필요한 생성 권한을
부여합니다. 양쪽 클러스터의 자격증명은 다를 수 있습니다. 예제는 offset-syncs를
타깃에 저장하며 타깃 정책을 명시적으로 관리하도록 ACL·설정 복사를 끕니다.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 4.3.1
  replicas: 3
  target:
    alias: dr-region
    bootstrapServers: dr-kafka-bootstrap.REPLACE.example.com:9093
    groupId: primary-to-dr
    configStorageTopic: primary-to-dr-configs
    offsetStorageTopic: primary-to-dr-offsets
    statusStorageTopic: primary-to-dr-status
    tls:
      trustedCertificates:
        - secretName: dr-cluster-ca-cert
          certificate: ca.crt
    authentication:
      type: scram-sha-512
      username: mm2-target
      passwordSecret:
        secretName: mm2-target
        password: password
    config:
      config.storage.replication.factor: 3
      offset.storage.replication.factor: 3
      status.storage.replication.factor: 3
  mirrors:
    - source:
        alias: us-east-1
        bootstrapServers: primary-kafka-bootstrap.REPLACE.example.com:9093
        tls:
          trustedCertificates:
            - secretName: primary-cluster-ca-cert
              certificate: ca.crt
        authentication:
          type: scram-sha-512
          username: mm2-source
          passwordSecret:
            secretName: mm2-source
            password: password
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.topic.acls.enabled: false
          sync.topic.configs.enabled: false
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.group.offsets.enabled: true
          sync.group.offsets.interval.seconds: 60
          emit.checkpoints.interval.seconds: 60
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      topicsPattern: 'orders[.].*|payments[.].*'
      groupsPattern: 'orders-consumer-.*'
```

패턴은 `orders.`와 `payments.` 접두사에 일치하며 단독 이름인 `orders`, `payments`,
앞의 `orders-db.public.orders`는 포함하지 않습니다. 실제 토픽 목록에 맞춰 바꿉니다.
source·checkpoint 커넥터의 replication policy, separator와 offset-syncs 위치를
동일하게 맞춥니다.

`sync.group.offsets.enabled=true`는 변환 가능한 오프셋을 가진 **비활성·미존재**
타깃 그룹에만 조건에 따라 반영합니다. 소비 중인 그룹의 오프셋을 덮어쓰지 않습니다.
그룹 멤버, 권한, 매핑·체크포인트 존재와 타깃의 기존 커밋 위치가 결과에 영향을 줍니다.
이 옵션이나 Ready 상태만 보고 장애 전환이 성공했다고 판단하지 않습니다.

## 네트워크와 모니터링

워커가 타깃 리전에 있으면 소스에서 워커로 가져오는 fetch가 리전 간 통신입니다.
워커의 **타깃 producer** 압축 설정은 이미 지나온 fetch 트래픽을 압축하지 않습니다.
소스 producer·토픽 압축과 배치 위치를 고려하고 양쪽 경로의 전송량·CPU·지연을
측정합니다. 설정 하나로 비용 절감을 보장하지 않습니다.

`replication-latency-ms`는 타깃이 레코드를 확인한 시점과 레코드 timestamp의
차이입니다. timestamp 모드, 과거 데이터 재처리와 시계 오차의 영향을 받습니다.
`record-age-ms`는 읽는 경로에서 관찰합니다. 파티션별 진행, 오류, 데이터·체크포인트
최신성도 함께 확인합니다. 멈췄거나 비어 있는 스트림은 오래된 값이나 누락을 만들 수
있습니다. Prometheus 이름은 exporter 매핑에 달려 있으므로 Kafka 메트릭 이름을
그대로 PromQL 이름으로 간주하지 않습니다.

## 참고 자료와 검증 범위

예제는 릴리스된 v1 CRD와 실제 커넥터 설정 정의로 확인했습니다. 로컬 MM2 동작
검사는 실제 리전 간 연결, DB 권한, ECR 빌드, S3 전달이나 재해복구 전환 성공을
의미하지 않습니다.

- [Strimzi 1.2.0 CRDs: authoritative resource fields](https://github.com/strimzi/strimzi-kafka-operator/tree/1.2.0/install/cluster-operator)
- [Strimzi 1.2.0 deployment guide](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Debezium 3.6 PostgreSQL connector](https://debezium.io/documentation/reference/3.6/connectors/postgresql.html)
- [Aiven S3 connector 3.4.3](https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/blob/v3.4.3/s3-sink-connector/README.md)
- [ECR authorization token lifetime](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_GetAuthorizationToken.html)
- [Kafka 4.3.1 MirrorSourceConnector](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceConnector.java)
- [Kafka 4.3.1 MirrorCheckpointTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorCheckpointTask.java)
- [Kafka 4.3.1 MirrorHeartbeatTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorHeartbeatTask.java)
- [Kafka 4.3.1 MirrorSourceTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceTask.java)

## 다음 단계

[Part 6: MSK 통합](./06-msk-integration.md)에서 관리형 선택지를 비교합니다.

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

[주제 퀴즈](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
