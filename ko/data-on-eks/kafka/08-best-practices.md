# Part 8: 모범 사례

> **검토 기준**: Kafka 4.3.1, Strimzi 1.2.0\
> **최종 검토**: 2026년 9월 12일

앞 장의 예제를 운영에서 검증할 결정으로 정리합니다. 다음에는
[벤치마크 장](./09-kafka-benchmark.md)이 이어집니다. 체크리스트만으로 실제 부하와
장애 시험을 대신할 수는 없습니다.

## 파티션 설계와 측정

일반적인 컨슈머 그룹에서는 한 파티션을 동시에 최대 한 멤버에게 할당합니다.
독립적으로 소비하는 멤버 20개를 모두 사용하려면 최소 20개 파티션이 필요합니다.
파티션당 처리량, 키 편중, 레코드 크기, 복제 비용, 복구 시간과 브로커·컨트롤러
용량도 함께 측정합니다. Share group이나 애플리케이션 내부 병렬 처리는 의미가
다르므로 모든 소비 API에 적용되는 규칙으로 일반화하지 않습니다.

파티션이 늘면 metadata, replica, buffer와 복구 작업도 늘어납니다. 비용을
보편적인 파티션당 메모리·파일 디스크립터 공식으로 계산하지 않습니다. 과거의
4,000/200,000 경험치를 현재의 공통 한계로 쓰지 말고 정상·장애 부하에서 측정합니다.
논리 파티션뿐 아니라 브로커당 replica 배치 수도 구분합니다.

### 토픽 헤더 대신 파티션 세기

`grep -c "PartitionCount"`는 파티션이 아닌 **토픽 요약 줄 수**를 셉니다.
다음을 `partition_summary.py`로 저장합니다. 현재 CLI의 파티션 줄과
`Leader: none`을 읽어 논리 파티션, replica 배치와 리더 분포를 따로 계산합니다.

```python
import collections
import json
from pathlib import Path
import re
import sys

def summarize(text):
    pattern = re.compile(
        r"^\s*Topic:\s+(\S+)\s+Partition:\s+(\d+)\s+Leader:\s+(none|-?\d+)"
        r"\s+Replicas:[ \t]*([\d,]*)[ \t]+Isr:[ \t]*([\d,]*)"
    )
    partitions = {}
    topics = collections.Counter()
    leaders = collections.Counter()
    replicas = collections.Counter()
    offline = []
    for line in text.splitlines():
        if not re.search(r"\bPartition:", line):
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError("Unrecognized partition row; check Kafka CLI version/output.")
        topic, partition, leader, replica_text, _ = match.groups()
        key = (topic, int(partition))
        if key in partitions:
            raise ValueError("Duplicate topic/partition row.")
        replica_ids = [int(x) for x in replica_text.split(",") if x]
        if not replica_ids or len(set(replica_ids)) != len(replica_ids):
            raise ValueError("Missing or duplicate replica IDs.")
        partitions[key] = True
        topics[topic] += 1
        replicas.update(replica_ids)
        if leader == "none" or int(leader) < 0:
            offline.append({"topic": topic, "partition": int(partition)})
        else:
            leaders[int(leader)] += 1
    if not partitions:
        raise ValueError("No partition rows; empty visibility is not proof of a healthy cluster.")
    return {
        "visible_topics": len(topics),
        "logical_partitions": len(partitions),
        "replica_assignments": sum(replicas.values()),
        "partitions_by_topic": dict(sorted(topics.items())),
        "leaders_by_broker": dict(sorted(leaders.items())),
        "replicas_by_broker": dict(sorted(replicas.items())),
        "offline_partitions": offline,
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 partition_summary.py topics.txt")
    print(json.dumps(summarize(Path(sys.argv[1]).read_text()), indent=2))
```

```bash
set -euo pipefail
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
# Run from a Kafka 4.3.1 client installation. admin.properties is local to this client.
bin/kafka-topics.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe > topics.txt
python3 partition_summary.py topics.txt
```

결과는 호출 사용자와 명령 필터에 보이는 토픽 범위이며 반환된 내부 토픽도 포함합니다.
실패·빈 결과는 파티션 0개나 정상 클러스터의 증거가 아닙니다. 관리 조회에 맞는
권한을 사용하고 브로커 Pod ID나 평문 localhost:9092를 가정하지 않습니다.

### 키의 의미 유지

Java 기본 producer의 keyed 배치는 **직렬화한 키 바이트**에
`toPositive(murmur2(keyBytes)) % partitionCount`를 적용합니다. 명시적 파티션,
사용자 partitioner나 키 무시 설정이 있으면 달라집니다. 다른 언어 클라이언트도 같은
배치가 필요하면 partitioner·serializer 호환성을 맞춥니다.

카디널리티가 높아도 특정 고객의 트래픽이 많으면 편중됩니다. 랜덤·timestamp salt는
키 단위 순서, 조인과 compaction의 동일성도 바꿉니다. 데이터 계약이 허용할 때만
적용하며 필요하면 재결합·순서 복원 전략을 설계합니다.

파티션 수를 늘리면 일부 키가 재배치될 수 있지만 옛 레코드는 재분배되지 않습니다.
키 순서와 co-partitioned 조인의 가정이 깨질 수 있으며 요구사항은 조인·토폴로지에
따라 다릅니다. 모든 Streams 조인이 같은 co-partitioning을 요구하지는 않습니다.
순서·상태 의존 워크로드는 새 토픽 등을 이용한 재분배·이전을 설계하고 시험합니다.

## 프로듀서 튜닝

다음은 기존 인증된 클라이언트 설정에 추가할 측정용 시작 프로필이며 공통 최적값은 아닙니다.

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

- `acks=all`은 현재 ISR을 기다립니다. RF=3, 토픽·브로커의
  `min.insync.replicas=2`에서 ISR이 2 미만이면 두 번째 replica를 무기한 기다리는
  대신 쓰기가 거부됩니다. 남은 replica·quorum과 의존성이 조건을 만족해야 단일
  장애를 견딜 수 있습니다.
- `enable.idempotence=true`는 지원되는 producer 재시도 중복을 억제하며 acks·retries·
  `max.in.flight.requests.per.connection`이 호환되어야 합니다. 호환되는 속성을
  명시했다고 멱등성이 꺼지는 것은 아닙니다.
- Kafka 4.3의 기본 linger는 5ms이며 여기의 10ms·32KiB는 튜닝 예시입니다.
  `batch.size`는 파티션별 배치·할당 설정이지 레코드나 요청 크기의 엄격한 상한이
  아닙니다. 큐 대기와 전달 기한도 지연에 영향을 줍니다.
- 실제 데이터·CPU·지연으로 lz4·zstd·gzip·무압축을 비교합니다. 특정 codec이 항상
  총비용에서 가장 유리하다고 가정하지 않습니다.

`min.insync.replicas`는 producer가 아닌 토픽·브로커 속성입니다.
`delivery.timeout.ms`가 전달 시도 시간을 제한하므로 retries가 커도 무한 재시도는
아닙니다. send 실패를 반드시 처리합니다.

멱등성은 애플리케이션이 임의로 다시 보낸 이벤트나 외부 DB의 부수 효과를
중복 제거하지 않습니다. Kafka consume-transform-produce의 exactly-once에는
트랜잭션 수명주기, 출력·입력 오프셋의 원자적 커밋, fencing과 read-committed 소비도
필요합니다. `transactional.id` 문자열만으로 완성되지 않습니다.

## 컨슈머 처리와 멤버십

다음은 **`group.protocol=classic`**을 명시하여 클라이언트 heartbeat/session
설정을 적용하는 프로필입니다. `group.protocol=consumer`에서는 해당 간격을
브로커의 consumer-group 설정으로 제어합니다.

```properties
group.id=order-processor
group.protocol=classic
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

레코드 수뿐 아니라 실제 처리 시간을 제한합니다. 느린 레코드 하나로도
`max.poll.interval.ms`를 넘을 수 있습니다. 동적·정적 멤버의 재할당 시점은
같지 않습니다. 정적 멤버는 poll timeout 후 heartbeat를 멈추고 session 만료까지
재할당이 지연될 수 있습니다.

### 처리가 영속적으로 완료된 뒤 커밋

자동 커밋은 비동기 외부 작업이 언제 끝났는지 알지 못합니다. 순서를 올바르게
설계한 동기 루프에서 사용할 수는 있지만 worker pool의 완료까지 추적한다고
가정하지 않습니다. 다음 helper는 auto-commit을 끄고 동기 처리 후 명시적으로
커밋하는 예입니다.

```java
import java.time.Duration;
import java.util.Properties;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;

public final class ConsumerExamples {
    public static void setStaticIdentity(Properties props, String instanceId) {
        if (instanceId == null || instanceId.isBlank() || instanceId.contains("${")) {
            throw new IllegalArgumentException("Supply a resolved, stable, unique consumer instance ID.");
        }
        props.setProperty(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, instanceId);
    }

    public static int processOneBatch(
            Consumer<String, String> consumer,
            java.util.function.Consumer<ConsumerRecord<String, String>> processDurably) {
        var records = consumer.poll(Duration.ofMillis(500));
        for (var record : records) {
            processDurably.accept(record);
        }
        if (!records.isEmpty()) {
            consumer.commitSync();
        }
        return records.count();
    }
}
```

```java
// props already includes bootstrap, TLS/SCRAM, deserializers and the profile below.
try (var consumer = new KafkaConsumer<String, String>(props)) {
    consumer.subscribe(List.of("orders"));
    while (!Thread.currentThread().isInterrupted()) {
        ConsumerExamples.processOneBatch(consumer, application::processDurably);
    }
}
```

`application.processDurably`는 필요한 작업이 성공한 뒤에만 반환하는 애플리케이션
코드입니다. 처리·커밋 실패 시 중단·복구하거나 올바른 위치로 seek해야 하며
**오류를 잡고 다음 poll로 넘어가지 않습니다**. 재시작하면 이미 처리한 레코드도
다시 올 수 있으므로 외부 작업의 멱등성·트랜잭션을 설계합니다. 종료는 KafkaConsumer가
지원하는 wakeup·close 패턴으로 구성합니다.

KafkaConsumer는 일반적으로 thread-safe하지 않습니다. 비동기 처리에는 제한된 큐,
파티션 순서, consumer 스레드의 pause/resume, 연속 완료 오프셋과 rebalance 처리가
필요합니다. thread pool로 넘기는 것만으로 안정성이 개선되지는 않습니다.

### 안정적인 정적 멤버 ID를 실제 값으로 설정

Java `Properties`는 `group.instance.id=${POD_NAME}`을 **환경변수로 치환하지
않습니다**. 컨슈머를 만들기 전에 애플리케이션·설정 코드에서 값을 넣습니다.

```java
// One consumer instance per stable logical member in this example.
ConsumerExamples.setStaticIdentity(props, System.getenv("KAFKA_GROUP_INSTANCE_ID"));
```

StatefulSet Pod 하나에 컨슈머 하나라면 Downward API의 `metadata.name`을 안정적인
논리 ID로 사용할 수 있습니다. Deployment Pod 이름은 여러 종류의 rollout에서
바뀌고, 한 Pod의 여러 컨슈머에는 서로 다른 ID가 필요합니다. 동시에 활성화된
각 컨슈머는 고유해야 하며 교체 인스턴스가 의도적으로 재사용하도록 설계합니다.
중복 활성 ID는 fencing을 일으킬 수 있습니다.

정적 멤버십은 조건이 맞는 짧은 재시작의 불필요한 rebalance를 줄이지만 시간 내
복귀만으로 항상 할당 유지를 보장하지는 않습니다. 토폴로지·멤버·구독도 영향을 주며
긴 session timeout은 실제 장애 멤버의 복구를 늦춥니다.

## 인증·인가·네트워크

### 두 CA와 listener 속성 구분

기본 Strimzi 관리 CA를 사용할 때:

- **cluster CA**는 브로커·내부 구성요소 인증서에 서명하며 클라이언트는 알맞은
  서버 인증서 체인을 신뢰합니다.
- **clients CA**는 mTLS용 `KafkaUser` 클라이언트 인증서에 서명합니다.
- `user.crt`·`user.key`는 클라이언트 자격증명입니다. 사용자 Secret의 clients CA
  인증서가 브로커의 신뢰 체인을 대신하지는 않습니다.

listener 노출 방식은 `type: internal`, `loadbalancer` 등입니다. 암호화는
`tls: true`, 클라이언트 인증은 `authentication.type: tls`로 지정합니다.
`tls`라는 listener 노출 type은 없습니다.

다음은 기존 `spec.kafka.listeners`에 **추가할 항목 하나**이며 Part 2의
TLS/SCRAM listener를 대체하지 않습니다. 추가 전에 전체 Kafka 원하는 상태를 검토합니다.

```yaml
name: mtls
port: 9094
type: internal
tls: true
authentication:
  type: tls
networkPolicyPeers:
- namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: kafka-clients
  podSelector:
    matchLabels:
      app: order-service
```

두 selector가 **한 peer 안**에 있으므로 `kafka-clients` 네임스페이스 **이면서**
`app=order-service`인 Pod를 선택합니다. peer 두 개로 나누면 OR가 되어 policy
네임스페이스의 일치 Pod 또는 선택한 네임스페이스의 모든 Pod를 허용합니다.
NetworkPolicy는 합산되며 CNI 집행이 필요합니다. 다른 정책에서 허용한 트래픽을
덮어써 거부하지 않습니다. egress와 실제 외부·노드 경로도 확인합니다.

별도의 mTLS 사용자를 만들어 기존 SCRAM 사용자를 보존합니다.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

User Operator의 조정과 브로커 simple authorizer 활성화가 필요합니다. 사용자
자격증명·브로커 신뢰를 애플리케이션 네임스페이스에 배포하고 회전시키는 통제된
절차를 갖춥니다. Kubernetes는 다른 네임스페이스 Secret을 직접 마운트하지 못합니다.
현재 generation, TLS·인증과 허용·거부 작업을 검증합니다. YAML 커밋만으로
동작하는 접근 권한이 완성되지는 않습니다.

기존 SCRAM 경로에도 TLS 암호화와 비밀번호 회전이 필요합니다. Kafka ACL과
NetworkPolicy는 서로를 대신하지 않습니다.

### 새 영속 볼륨 암호화를 명시

표준 EBS CSI에서는 암호화 StorageClass와 계정·리전의 EBS encryption-by-default를
검토합니다. 다음은 볼륨을 Retain하고 스케줄링 후 AZ를 선택하는 예제입니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
parameters:
  type: gp3
  encrypted: 'true'
```

Auto Mode는 Part 2의 별도 `ebs.csi.eks.amazonaws.com` provisioner·topology
구성을 사용하면서 `encrypted: "true"`도 명시합니다. Auto Mode의 노드·임시 디스크
암호화 설명으로 동적 PVC까지 추정하지 않습니다. StorageClass 파라미터 문서는
encrypted 기본값을 false로 명시하므로 실제 EBS 볼륨의 암호화·KMS 키를 확인합니다.

고객 관리 키는 `key/xxxxxxxx`가 아닌 실제 ARN과 역할·키 권한이 필요합니다.
StorageClass나 계정 기본값 변경은 기존 볼륨을 소급 암호화하지 않습니다.
영속 볼륨 교체 전에 지원되는 데이터·스냅샷 이전과 복구 접근을 검증합니다.

## 용량·tiering·보존

Kafka는 page cache의 도움을 받지만 CPU(TLS·압축 포함), 네트워크, 저장소
처리량·IOPS나 cgroup 메모리가 병목이 될 수도 있습니다. heap·off-heap·page cache와
다른 워크로드를 함께 측정합니다. “heap 4~8GB면 충분”이나 메모리 최적화 인스턴스가
항상 비용에서 유리하다는 규칙은 없습니다.

Kafka tiered storage는 3.9부터 production-ready이며 Strimzi 1.2도 지원합니다.
여전히 호환되는 **RemoteStorageManager 플러그인**과 이미지의 의존성, 원격
접근·권한, 보존·정리·복구 설정이 필요합니다. Strimzi custom 연동은
`spec.kafka.tieredStorage`의 class/path/config를 사용합니다.
`remote.log.storage.system.enable`만 켜도 S3와 연결되는 것은 아닙니다.
해당 버전의 기능 제약을 읽고 원격 저장소 불능·복구를 시험합니다.

### 보존은 데이터에 관한 결정

다음은 기존 토픽을 3일 또는 **파티션당 50GiB** 중 먼저 도달하는 조건으로
변경하는 예입니다. segment 단위·비동기 삭제이므로 즉시 적용되는 정확한 byte 상한은 아닙니다.

```bash
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe \
  --entity-type topics --entity-name application-logs
# After reviewing retention/recovery requirements: shortening retention can delete data.
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --alter \
  --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

보존을 줄이면 재처리·복구에 필요한 레코드가 영구 삭제될 수 있습니다.
`cleanup.policy=compact`도 비동기 정리이며 tombstone·cleaner 동작에 따라 키별
최신 값을 남깁니다. 키가 계속 늘거나 active·미정리 segment가 있으면 용량도 늘므로
엄격한 저장소 상한이 아닙니다. `compact,delete`는 삭제 보존도 적용해 오래된 키의
마지막 값까지 지울 수 있습니다. 상태 복원과 tombstone 보존 요구를 명시합니다.

### Spot과 disruption

운영 기준 구성에서는 컨트롤러 quorum에 적절한 안정적 용량을 사용합니다.
위험을 감수할 수 있는 워크로드는 브로커 Spot을 검토할 수 있지만 Pod 분산만으로
연관된 회수를 막지는 못합니다. 브로커 rack-aware replica 배치, 노드·AZ 분산,
EBS 볼륨 AZ의 대체 용량과 검증한 복구·여유 용량을 함께 설계합니다.

Strimzi 1.2 PDB는 Kafka 클러스터 Pod의 자발적 eviction을 제한합니다.
강제 삭제, 노드 장애, Spot 회수나 모든 Operator rolling에서 quorum을 보장하지
않습니다. RF=3/minISR=2, PDB, On-Demand 컨트롤러는 설계 입력이며 무손실·무중단의
증명은 아닙니다.

## 운영 투입 전에 남길 증거

- 버전·API 호환성과 업그레이드·rollback·인증서 회전 리허설.
- 장애 상황의 파티션·replica·CPU·메모리·네트워크·저장소 한계 측정.
- 인가 경계, 클라이언트 ID와 Secret·신뢰 회전 검증.
- 스키마·과거 데이터 호환성, 처리·커밋과 중복 처리 동작.
- 필요한 스키마·키를 포함한 복구·전환 및 RPO/RTO 측정.
- 수집·알람·전달 범위, 컨슈머 용량과 애플리케이션 SLO.
- 보존, 저장소 암호화, 비용 가정과 운영 담당자.

워크로드에 맞는 통제를 적용하고 남은 한계를 기록합니다. 공통 체크리스트를 모두
체크했다는 사실만으로 운영 준비를 인증할 수는 없습니다.

## 참고 자료와 검증 범위

Kafka 4.3.1 설정 클래스, 실제 keyed partitioner, MockConsumer 처리·커밋 테스트,
릴리스된 리소스 스키마와 토픽 출력 fixture로 예제를 검토했습니다. 실제 TLS/CNI
집행, 암호화 볼륨 조회, 장애 복구와 애플리케이션 정확성 시험을 대신하지 않습니다.

- [Kafka 4.3 producer configuration](https://kafka.apache.org/43/configuration/producer-configs/)
- [Kafka 4.3 consumer configuration](https://kafka.apache.org/43/configuration/consumer-configs/)
- [Kafka 4.3 tiered storage](https://kafka.apache.org/43/operations/tiered-storage/)
- [Kafka 4.3.1 keyed partitioner](https://github.com/apache/kafka/blob/4.3.1/clients/src/main/java/org/apache/kafka/clients/producer/internals/BuiltInPartitioner.java)
- [Kafka 4.3.1 topic-description output](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/TopicCommand.java)
- [Strimzi 1.2.0 deployment, TLS and tiered-storage guide](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Kubernetes NetworkPolicy selector semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EBS encryption by default](https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html)
- [EKS Auto Mode StorageClass parameters](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)

## 다음 단계

[Part 9: Kafka 벤치마크](./09-kafka-benchmark.md)

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

[주제 퀴즈](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
