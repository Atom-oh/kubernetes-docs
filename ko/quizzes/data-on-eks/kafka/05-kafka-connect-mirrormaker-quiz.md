# Kafka Connect와 MirrorMaker 퀴즈

본문의 Strimzi v1 구성, 실제 플러그인, 복제와 복구 조건을 확인합니다.

## 1. Debezium PostgreSQL과 S3 싱크는 각각 어느 방향으로 데이터를 이동하나요?

<details>
<summary>정답 보기</summary>

Debezium은 최초 스냅샷·WAL 변경을 Kafka로 보내는 소스이고 S3 싱크는 Kafka 레코드를 S3로 보냅니다. 지원 형식과 전달 보장은 각 플러그인별로 확인합니다.

</details>

## 2. Aiven S3 싱크가 Debezium 레코드를 저장하면 현재 DB 테이블이 자동 복원되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 본문은 작업 유형과 before/after를 포함하는 CDC 이벤트를 저장합니다. 현재 상태 재구성에는 키, 삭제·tombstone, 순서와 재처리를 처리하는 별도 로직이 필요합니다.

</details>

## 3. 분산 Connect의 그룹 코디네이터와 할당을 계산하는 워커 리더는 무엇이 다른가요?

<details>
<summary>정답 보기</summary>

Kafka 브로커가 그룹 코디네이터이고 선출된 워커 리더가 할당을 계산합니다. 워커 장애 후 재할당은 지연·재처리를 동반할 수 있고 태스크 자체의 실패와도 구분합니다.

</details>

## 4. Standalone Connect는 Kubernetes에서 실행할 수 없나요?

<details>
<summary>정답 보기</summary>

실행할 수 있지만 분산 워커 장애 조치를 제공하지 않습니다. Strimzi의 KafkaConnect가 관리하는 것은 분산 모드입니다. 워커 수를 늘려도 단일 태스크 커넥터가 자동 병렬화되지는 않습니다.

</details>

## 5. KafkaConnector CR로 관리할 때 REST에서 설정을 직접 수정하면 어떤 문제가 있나요?

<details>
<summary>정답 보기</summary>

Operator가 CR의 원하는 상태로 되돌릴 수 있습니다. 변경 경로를 CR로 통일하고 Kubernetes 갱신 권한과 Connect REST API 접근을 제한합니다.

</details>

## 6. KafkaConnector 조정을 활성화하는 어노테이션과 현재 API 버전은 무엇인가요?

<details>
<summary>정답 보기</summary>

`strimzi.io/use-connector-resources: "true"`와 `kafka.strimzi.io/v1`입니다. v1은 groupId·내부 토픽 이름 등 필드 변환도 필요하며 apiVersion만 바꾸지 않습니다.

</details>

## 7. Connect spec.build에서 무엇을 고정·검증하며 ECR 인증은 어떻게 다루나요?

<details>
<summary>정답 보기</summary>

플러그인 버전·URL·체크섬과 결과 이미지 태그를 명시합니다. 유효한 push Secret과 이미지 pull 권한이 필요하고 ECR 토큰은 12시간 뒤 만료됩니다. 런타임 S3 역할과 빌드 push 인증을 구분합니다.

</details>

## 8. MM2의 offset-sync 매핑과 체크포인트는 각각 무엇을 위한 것인가요?

<details>
<summary>정답 보기</summary>

MirrorSourceConnector가 소스·타깃 오프셋 대응 정보를 생성하고 MirrorCheckpointConnector가 이를 사용해 소스 그룹의 커밋 위치를 변환합니다. 양쪽 오프셋 숫자가 같다고 가정하지 않습니다.

</details>

## 9. DefaultReplicationPolicy가 붙이는 이름과 순환 방지 범위는 무엇인가요?

<details>
<summary>정답 보기</summary>

`<소스별칭>.<토픽>`을 사용하며 기원 경로에 이미 있는 타깃 별칭으로 돌아가는 순환을 감지합니다. 모든 접두사 토픽을 제외하는 것은 아니며 제3 클러스터로의 다단계 복제는 가능할 수 있습니다.

</details>

## 10. Active-passive 장애 전환에서 MM2 외에 무엇을 준비해야 하나요?

<details>
<summary>정답 보기</summary>

이전 writer 차단, 복제·체크포인트 최신성 측정, 타깃 권한·스키마 확인, 주소·구독 변경과 재개 위치 검증이 필요합니다. 소스가 복구 불가능하면 미복제 데이터 손실이 가능하며 중복 재처리 범위도 측정해야 합니다.

</details>

## 11. Apache MirrorHeartbeatTask가 하트비트를 만들면 소스 데이터 복제도 정상임이 증명되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 태스크는 소스 데이터를 읽지 않고도 하트비트를 만들 수 있습니다. 파티션 진행·오류·체크포인트 최신성을 함께 확인합니다. 이 Apache 클래스와 Strimzi 1.2의 v1 필드 지원도 구분합니다.

</details>

## 12. Connect v1 내부 토픽 필드와 파티션·보존 요구사항은 무엇인가요?

<details>
<summary>정답 보기</summary>

`spec.configStorageTopic`, `spec.offsetStorageTopic`, `spec.statusStorageTopic`입니다. compaction을 사용하고 config 토픽은 파티션 1개여야 합니다. 워커 그룹은 spec.groupId로 지정하며 싱크 그룹 오프셋은 별도입니다.

</details>

## 13. sync.topic.acls.enabled=true는 소스 보안 정책 전체를 그대로 복사하나요?

<details>
<summary>정답 보기</summary>

아닙니다. Kafka 4.3.1은 선택된 literal 토픽 ACL을 처리하고 ALLOW WRITE를 제외하며 ALLOW ALL은 READ로 낮춥니다. 사용자·클러스터·외부 IAM 정책 전체를 이전하지 않습니다. 본문은 복사를 끄고 타깃 정책을 별도로 관리합니다.

</details>

## 14. replication-latency-ms의 해석과 리전 간 압축에서 주의할 점은 무엇인가요?

<details>
<summary>정답 보기</summary>

타깃 확인 시점과 레코드 timestamp의 차이이므로 시계 오차·timestamp 모드·재처리 영향을 받습니다. 타깃 리전 워커의 target producer 압축은 소스에서 이미 가져온 리전 간 fetch를 줄이지 않습니다.

</details>

## 15. KafkaMirrorMaker2 v1에서 타깃과 소스 연결은 어디에 정의하나요?

<details>
<summary>정답 보기</summary>

`spec.target`과 `spec.mirrors[].source`입니다. target에는 alias·bootstrapServers·groupId·내부 토픽 이름 3개가 필요합니다. 기존 connectCluster/clusters/heartbeatConnector 구조를 사용하지 않습니다.

</details>

## 16. 본문과 일치하는 Debezium PostgreSQL KafkaConnector를 작성하고 사전 조건을 설명하세요.

<details>
<summary>정답 보기</summary>

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

논리 복제·권한·publication과 적절한 replica identity가 필요합니다. password는 허용한 Secret 디렉터리 provider로 읽고 DB TLS 호스트 이름을 검증합니다. 태스크는 1개이며 멈춘 slot의 WAL 보존량을 관찰합니다.

</details>

## 17. 본문의 v1 MM2 예제에서 그룹 오프셋 동기화의 핵심 조건은 무엇인가요?

<details>
<summary>정답 보기</summary>

source와 checkpoint의 replication policy·offset-syncs 위치를 일치시키고 `sync.group.offsets.enabled=true`를 설정합니다. 변환 가능한 매핑·체크포인트와 권한이 필요하며 타깃 그룹은 비활성 또는 미존재여야 합니다. 소비 중인 그룹은 덮어쓰지 않습니다. 실제 리소스는 본문의 mm2.yaml과 동일한 target/source 구조를 사용합니다.

</details>

## 18. IdentityReplicationPolicy와 topicsPattern만으로 임의의 양방향 쓰기 구성이 안전해지나요?

<details>
<summary>정답 보기</summary>

아닙니다. Identity는 기원 접두사 정보를 잃어 기본 정책과 같은 순환 방지를 제공하지 않습니다. 방향별 토픽 소유권·필터·쓰기 정책과 전환 절차를 설계합니다. 토픽 필터가 데이터 충돌이나 중복을 자동 해결하지는 않습니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [다음 퀴즈](./06-msk-integration-quiz.md)
