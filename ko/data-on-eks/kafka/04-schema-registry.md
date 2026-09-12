# Part 4: 스키마 레지스트리

> **검토 기준**: Karapace 6.2.3, Apicurio Registry 3.3.3, Strimzi 1.2.0 / Kafka 4.3.1\
> **최종 검토**: 2026년 9월 12일

## 스키마 레지스트리가 필요한 이유

Kafka는 레코드의 키와 값을 바이트로 저장합니다. 따라서 프로듀서와 컨슈머가
데이터의 구조나 의미를 다르게 해석할 수 있습니다. 필드 추가가 항상 오류를
일으키는 것은 아닙니다. 인코딩, reader 구현, 호환성 규칙에 따라 결과가 달라집니다.

레지스트리는 스키마를 버전별로 관리하고 등록 시 설정된 호환성을 검사합니다.
애플리케이션도 해당 직렬화기와 검증 경로를 사용해야 합니다. 레지스트리만 설치한다고
모든 Kafka 레코드나 통화·시간의 의미 같은 업무 규칙을 자동 검사하지는 않습니다.

JSON에도 JSON Schema, CI 검사, 버전 관리된 명세로 계약을 적용할 수 있습니다.
중앙 레지스트리는 계약의 배포와 관리를 돕고, 바이너리 인코딩은 별도 선택입니다.
메시지 크기나 저장 비용 절감은 실제 레코드와 압축을 적용해 비교해야 합니다.

### 레코드에는 무엇이 들어가는가?

일반적인 Confluent **스키마 ID 기반 payload framing**은 magic byte 1바이트와
스키마 ID 4바이트, 합계 5바이트 뒤에 직렬화된 값을 붙입니다. Protobuf 형식에는
message index도 들어갑니다. JSON Schema 직렬화기의 값은 여전히 JSON입니다.
헤더에 식별자를 넣는 방식이나 Apicurio의 네이티브 인코딩은 별도 설정을 확인합니다.

직렬화기는 스키마를 등록하거나 조회하고, 역직렬화기는 식별자로 writer 스키마를
찾습니다. 일반적으로 캐시를 사용하므로 레코드마다 HTTP 요청을 보내지는 않습니다.
새 스키마나 비어 있는 캐시는 레지스트리 연결이 필요할 수 있습니다. Kafka 데이터,
아카이브와 복구용 사본을 읽어야 하는 기간 동안 ID와 스키마의 대응 관계도 보존합니다.

## 주요 구현체 비교

| 구현체 | 관련 스키마 형식 | API와 저장 방식 |
| --- | --- | --- |
| Karapace 6.2.3 | Avro, JSON Schema, **Protobuf** | Confluent 호환 REST API, Kafka 기반 스키마 저장, REST Proxy도 제공 |
| Apicurio Registry 3.3.3 | Avro, Protobuf, JSON Schema 및 추가 artifact 유형 | 네이티브 API와 `/apis/ccompat/v7`, `/apis/ccompat/v8`; KafkaSQL·SQL 저장 방식 |
| Confluent Schema Registry | Avro, Protobuf, JSON Schema | Confluent API, 자체 관리 배포에서 Kafka 기반 저장 |

Karapace와 Apicurio는 Apache-2.0 라이선스를 제공합니다. 필요한 고지 보존 등
조건이 있으므로 “아무 제약 없음”이라는 뜻은 아닙니다. Confluent 저장소는
Community License 적용 서버 모듈과 Apache-2.0 적용 client/Avro 모듈을 구분합니다.
클러스터 규모로 상업적 이용 조건을 추정하지 말고 실제 구성요소의 라이선스와
별도 지원 계약을 확인합니다.

API 호환은 유용하지만 **URL 변경만으로 마이그레이션이 끝나는 것은 아닙니다**.
스키마 ID, 참조, subject 이름, 인증, 클라이언트 버전과 인코딩을 기존 레코드로
검증합니다. 예를 들어 Apicurio 호환 API는 Confluent의 모든 exporter·암호화 기능을
구현하지 않습니다. 요청 필드를 받아들여도 그 규칙을 실행한다는 의미는 아닙니다.
저장 가능한 artifact 유형이 모든 Kafka 직렬화기의 지원 형식과 같지도 않습니다.
Karapace에도 브로커·인증·스키마 토픽 설정이 필요합니다.

## 직렬화 형식

### Avro

다음 예제를 `order.avsc`로 저장합니다. Avro는 이름, 기본값, alias와 정의된 타입
승격 규칙으로 writer와 reader 스키마의 차이를 해석합니다.
`logicalType`은 필드의 `name` 옆이 아닌 **type 객체 안**에 둡니다.
잘못된 위치의 속성은 파싱되더라도 논리적 timestamp 선언으로 동작하지 않을 수 있습니다.

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    {
      "name": "orderId",
      "type": "string"
    },
    {
      "name": "customerId",
      "type": "string"
    },
    {
      "name": "amount",
      "type": "double"
    },
    {
      "name": "currency",
      "type": "string",
      "default": "USD"
    },
    {
      "name": "createdAt",
      "type": {
        "type": "long",
        "logicalType": "timestamp-millis"
      }
    }
  ]
}
```

`amount`의 double은 형식 설명용입니다. 실제 계약에서는 단위·정밀도·반올림을
정의하고, 정확한 십진 금액이 필요하면 적절한 정수나 decimal 표현을 선택합니다.

### Protobuf와 JSON Schema

Protobuf는 필드 번호와 언어별 생성 코드·런타임 API를 사용합니다. 시간 단위를
명시해야 하며 `int64`만으로 논리적 timestamp를 선언하지는 않습니다.
삭제한 필드 번호를 재사용하지 말고 필요한 번호·이름을 `reserved`로 남깁니다.

```protobuf
syntax = "proto3";
package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at_millis = 5;
}
```

JSON Schema는 JSON 값을 검증합니다. draft와 호환성 분석 지원은 구현체별로
다르며, 어떤 키워드의 값 검증을 지원한다고 스키마 진화 분석까지 완전히 지원하는
것은 아닙니다. 세 형식은 서로 바꿔 읽을 수 있는 인코딩이 아닙니다.

| 형식 | 전송 표현 | 스키마 진화 시 고려사항 |
| --- | --- | --- |
| Avro | writer 스키마로 해석하는 바이너리 | reader/writer 해석, 기본값, 이름, 타입 승격 |
| Protobuf | 필드 번호 기반 바이너리 | 번호·wire type 유지 및 애플리케이션 의미 확인 |
| JSON Schema | JSON | 허용 값 집합, 필수 필드, 추가 속성, draft 지원 |

## 호환성과 배포 순서

Confluent 호환 API에서는 **subject**별로 호환성을 설정하거나 전역 기본값을
상속합니다. 기본 `TopicNameStrategy`에서 `orders` 토픽의 값은 `orders-value`
subject를 사용합니다. 다른 전략은 여러 토픽이 subject를 공유하거나 한 토픽의
레코드 유형을 나눌 수 있습니다.

| 모드 | 요구하는 관계 | 일반적인 스키마 배포 순서 |
| --- | --- | --- |
| BACKWARD | 새 reader가 이전 writer의 데이터를 읽음 | 컨슈머 먼저 |
| FORWARD | 이전 reader가 새 writer의 데이터를 읽음 | 프로듀서 먼저 |
| FULL | 두 방향 모두 충족 | 검사한 스키마 관계에서는 어느 순서든 가능 |
| NONE | 호환성 검사 없음 | 명시적 조율과 테스트 필요 |

일반 모드는 직전 버전과 비교하고 `_TRANSITIVE` 모드는 모든 이전 버전과
비교합니다. 오래 보존한 레코드 재처리는 직전 버전 검사만으로 부족할 수 있습니다.
`FULL`은 업무 의미·코드 동작·모든 과거 버전과의 호환을 보장하지 않습니다.
`FULL_TRANSITIVE`도 스키마 비교 범위를 확장하며 업무 동작까지 보장하지는 않습니다.

Avro에 다음 필드를 추가하면 새 reader가 옛 레코드에서 `null`을 채울 수 있습니다.

```json
{"name":"discountCode","type":["null","string"],"default":null}
```

기본값은 **reader의 스키마 해석 규칙**입니다. writer가 임의의 필수 필드를
생략해도 된다는 의미는 아닙니다.

| Avro 변경 | 확인할 조건 |
| --- | --- |
| reader 기본값 없는 필드 추가 | 새 reader는 해당 필드가 없는 옛 레코드를 읽지 못함 |
| 필드 제거 | BACKWARD 가능; FORWARD는 옛 reader에 기본값이 있는지에 따라 달라짐 |
| `double` → `string` | 호환 불가; Avro 숫자 타입 승격이 아님 |
| `int` → `long` | 새 reader는 옛 정수 값을 읽을 수 있지만 반대 방향은 다름 |
| 필드 이름 변경 | reader alias나 적용 가능한 기본값에 따라 결과가 달라지므로 양방향 검사 |

레지스트리 호환성 API와 대표적인 과거 데이터를 사용한 reader/writer 테스트를
함께 실행합니다. 두 검사는 발견하는 오류의 범위가 다릅니다.

## Strimzi 기준 구성에 Apicurio 배포

다음은 **비공개 실습용 배포**이며 인증된 공개 레지스트리 구성은 아닙니다.
[Part 2](./02-strimzi-operator.md)의 `kafka` 네임스페이스, `my-cluster`,
브로커 3대, Topic/User Operator와 TLS/SCRAM 리스너 9093을 전제로 합니다.
예제 HTTP API에는 애플리케이션 인증이 없습니다. NetworkPolicy를 집행하는 CNI에서
같은 네임스페이스의 지정된 라벨을 가진 Pod만 8080으로 접근하게 제한합니다.
Pod 생성·라벨 변경 권한도 통제해야 합니다. 공동 운영 환경에는 API TLS·인증·인가를
Kafka SASL과 별도로 구성합니다. 내부 Service만으로 이 기능이 제공되지는 않습니다.

### 저장 토픽과 Kafka 사용자

`registry-storage.yaml`로 저장합니다. 애플리케이션 사용자는 지정된 토픽 3개와
자신의 컨슈머 그룹 접두사만 사용합니다. Topic Operator로 토픽을 미리 생성하므로
애플리케이션에 토픽 생성 권한은 부여하지 않습니다.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-journal
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-snapshots
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: registry-events
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: apicurio-registry
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
          name: kafkasql-journal
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: kafkasql-snapshots
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: registry-events
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: group
          name: apicurio-registry-
          patternType: prefix
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

KafkaSQL 3.3.3은 journal·snapshots·events 토픽을 초기화합니다. 기본 검사에서
journal과 snapshots 토픽은 `cleanup.policy=delete`, `retention.ms=-1`,
`retention.bytes=-1`이 필요합니다. 일반적인 `_schemas` compaction 설정이나
이벤트 토픽의 7일 보존 설정을 그대로 적용하지 않습니다. 무기한 보존이므로 디스크
증가를 관찰하고 검증된 백업·정리 절차를 설계해야 합니다.

KafkaSQL은 journal과 사용 가능한 스냅샷으로 로컬 SQL 상태를 복원합니다.
snapshots 토픽에는 스냅샷 전체가 아닌 **파일 경로**가 기록됩니다. 다음 실습은
예약 스냅샷을 끄고 전체 journal을 유지합니다. Pod가 사라지면 다시 읽어야 하므로
시작이 오래 걸릴 수 있습니다. 영속·공유 스냅샷 저장소, 백업·복원, journal 정리는
별도 복구 설계가 필요합니다. 그룹 접두사는 지정할 수 있지만 고정 `group.id`로
상태를 보존하지 않습니다. 이 릴리스는 시작 시 재처리를 위해 고유 그룹을 만듭니다.

### Deployment와 Service

`registry.yaml`로 저장합니다. CA와 JAAS 정보는 Strimzi Secret에서 가져오며
호스트 이름 검증을 명시적으로 켭니다. 리소스 크기와 10분의 시작 허용 시간은
실습의 초깃값이므로 메모리와 journal 재처리 시간을 측정해 조정합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apicurio-registry
  template:
    metadata:
      labels:
        app: apicurio-registry
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: registry
          image: quay.io/apicurio/apicurio-registry:3.3.3
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          ports:
            - name: http
              containerPort: 8080
            - name: management
              containerPort: 9000
          env:
            - name: APICURIO_STORAGE_KIND
              value: kafkasql
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: my-cluster-kafka-bootstrap.kafka.svc:9093
            - name: APICURIO_KAFKASQL_TOPIC_AUTO_CREATE
              value: "false"
            - name: APICURIO_KAFKASQL_CONSUMER_GROUP_PREFIX
              value: apicurio-registry-
            - name: APICURIO_KAFKASQL_SNAPSHOT_SCHEDULED_ENABLED
              value: "false"
            - name: APICURIO_KAFKA_COMMON_SECURITY_PROTOCOL
              value: SASL_SSL
            - name: APICURIO_KAFKA_COMMON_SASL_MECHANISM
              value: SCRAM-SHA-512
            - name: APICURIO_KAFKA_COMMON_SASL_JAAS_CONFIG
              valueFrom:
                secretKeyRef:
                  name: apicurio-registry
                  key: sasl.jaas.config
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_TYPE
              value: PKCS12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_LOCATION
              value: /etc/kafka-ca/ca.p12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: my-cluster-cluster-ca-cert
                  key: ca.password
            - name: APICURIO_KAFKA_COMMON_SSL_ENDPOINT_IDENTIFICATION_ALGORITHM
              value: HTTPS
          volumeMounts:
            - name: kafka-ca
              mountPath: /etc/kafka-ca
              readOnly: true
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          startupProbe:
            httpGet:
              path: /health/ready
              port: management
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /health/ready
              port: management
          livenessProbe:
            httpGet:
              path: /health/live
              port: management
      volumes:
        - name: kafka-ca
          secret:
            secretName: my-cluster-cluster-ca-cert
            items:
              - key: ca.p12
                path: ca.p12
---
apiVersion: v1
kind: Service
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  selector:
    app: apicurio-registry
  ports:
    - name: http
      port: 8080
      targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apicurio-registry-ingress
  namespace: kafka
spec:
  podSelector:
    matchLabels:
      app: apicurio-registry
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              docs.example.com/registry-client: "true"
      ports:
        - protocol: TCP
          port: 8080
```

```bash
kubectl apply -f registry-storage.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/kafkasql-journal kafkatopic/kafkasql-snapshots kafkatopic/registry-events \
  kafkauser/apicurio-registry
kubectl apply -f registry.yaml
kubectl -n kafka rollout status deployment/apicurio-registry --timeout=600s
kubectl -n kafka port-forward --address=127.0.0.1 service/apicurio-registry 8080:8080
```

포트 포워딩에는 Kubernetes 접근 권한이 필요하며 해당 터미널에서 계속 실행됩니다.
Secret을 참조하는 환경변수를 변경한 경우 워크로드를 다시 시작합니다.
SQL 저장 방식을 선택할 때 `APICURIO_STORAGE_KIND=sql`만으로 PostgreSQL 연결이
완성되지는 않습니다. SQL 종류, 전용 데이터베이스, TLS·자격증명과 복구 절차가
필요합니다. 기본 메모리 H2 데이터베이스는 영속적인 운영 저장소가 아닙니다.

## 애플리케이션과 동일한 스키마 등록

다른 터미널에서 `order.avsc`를 `orders-value`에 등록합니다. 앞의 여러 필드와
namespace를 가진 예제 대신 curl 문자열 속 다른 단일 필드 스키마를 등록하는
실수를 방지합니다. 첫 요청은 subject의 호환성을 명시하며 HTTP 실패 시 curl도
실패 상태를 반환합니다.

```bash
# Run from a directory containing the order.avsc above.
# Keep kubectl port-forward running in a separate terminal.
REGISTRY_URL="http://127.0.0.1:8080/apis/ccompat/v7"
python3 - <<'PY'
import json
from pathlib import Path
schema = json.loads(Path("order.avsc").read_text())
Path("register-order.json").write_text(json.dumps({
    "schemaType": "AVRO",
    "schema": json.dumps(schema)
}) + "\n")
PY
curl --fail-with-body --silent --show-error \
  -X PUT "$REGISTRY_URL/config/orders-value" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary '{"compatibility":"BACKWARD_TRANSITIVE"}'
curl --fail-with-body --silent --show-error \
  -X POST "$REGISTRY_URL/subjects/orders-value/versions" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary @register-order.json
curl --fail-with-body --silent --show-error \
  "$REGISTRY_URL/subjects/orders-value/versions/latest"
```

## 프로듀서와 컨슈머 설정

다음은 Part 2의 브로커 주소·TLS 신뢰와 각 애플리케이션의 Kafka 사용자가 이미
설정된 상태에 **추가하는** 속성입니다. 레지스트리 HTTP 인증과 Kafka SASL 인증은
별개입니다. 애플리케이션에 호환되는 버전으로 고정한 Confluent Avro serializer
의존성을 포함합니다. Kafka나 Strimzi 설치만으로 이 라이브러리가 생기지 않습니다.

프로듀서:

```properties
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
auto.register.schemas=false
```

컨슈머:

```properties
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
specific.avro.reader=false
```

프로듀서는 일치하는 스키마가 먼저 등록되어 있어야 합니다.
`specific.avro.reader=false`는 generic Avro record를 사용합니다. 생성한
SpecificRecord 클래스를 쓰려면 해당 코드와 reader 설정을 맞춥니다.
기본 subject 전략에서 애플리케이션의 Kafka 토픽 이름은 `orders`여야 합니다.

레지스트리 변경 전에는 캐시가 빈 컨슈머의 과거 데이터 읽기, 새 버전 등록,
호환성 거부, 스키마 참조와 재시작·복구를 테스트합니다. 기존 스키마 ID 매핑을
보존하거나 명시적으로 지원되는 데이터·식별자 이전 절차를 수행합니다.
HTTP 상태 검사의 성공만으로 직렬화가 검증되는 것은 아닙니다.

## 참고 자료와 검증 범위

예제는 고정한 릴리스의 설정, Strimzi·Kubernetes 스키마와 로컬 Avro reader/writer
테스트로 검토했습니다. 이 검사는 실제 이미지 배포, TLS 브로커 접속과 애플리케이션의
정확한 직렬화기 버전으로 수행하는 연동 테스트를 대신하지 않습니다.

- [Apache Avro specification](https://avro.apache.org/docs/1.12.0/specification/)
- [Protocol Buffers: updating a message type](https://protobuf.dev/programming-guides/proto3/#updating)
- [Confluent compatibility rules](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [Confluent serializers and wire format](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html)
- [Karapace 6.2.3](https://github.com/Aiven-Open/karapace/tree/6.2.3)
- [Apicurio Registry 3.3.3](https://github.com/Apicurio/apicurio-registry/tree/3.3.3)
- [Apicurio compatibility API support matrix](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/ccompat/rest/README.md)
- [Apicurio KafkaSQL configuration](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/kafkasql/KafkaSqlConfiguration.java)
- [Apicurio topic configuration verification](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/util/KafkaAdminUtil.java)
- [Confluent component licenses](https://github.com/confluentinc/schema-registry/blob/master/LICENSE)

## 다음 단계

[Part 5](./05-kafka-connect-mirrormaker.md)에서는 외부 연동과 클러스터 간 복제를
다룹니다. 레코드 복제와 함께 스키마 저장·ID 이전도 고려해야 합니다.

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

[주제 퀴즈](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
