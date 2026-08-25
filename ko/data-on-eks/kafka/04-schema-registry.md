# Part 4: 스키마 레지스트리

> **지원 버전**: Karapace 4.x, Apicurio Registry 3.x, Confluent Schema Registry (호환 API)\
> **마지막 업데이트**: 2026년 7월 9일

## 왜 스키마 레지스트리가 필요한가

Kafka 자체는 메시지를 바이트 배열로만 취급합니다. 프로듀서가 어떤 형식으로 데이터를 넣든 Kafka는 신경 쓰지 않습니다. 문제는 프로듀서와 컨슈머가 서로 다른 팀, 다른 배포 주기를 가진 별도의 애플리케이션이라는 점입니다. 프로듀서가 필드를 하나 추가하거나 타입을 바꾸는 순간, 그 사실을 모르는 컨슈머는 역직렬화에 실패하거나 잘못된 값을 읽게 됩니다.

### 스키마 없는 JSON의 문제

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

이런 JSON 페이로드는 사람이 읽기 쉽지만 다음과 같은 문제가 있습니다.

* **강제되는 계약이 없음**: 프로듀서가 `amount`를 문자열로 바꿔도 브로커는 막지 않습니다.
* **검증은 런타임에만**: 필드가 빠지거나 타입이 달라도 컨슈머가 파싱을 시도할 때야 실패합니다.
* **페이로드 크기**: 필드명을 매 메시지마다 반복 전송하므로 바이너리 포맷보다 크고, 처리량이 큰 스트림에서는 네트워크·스토리지 비용으로 직결됩니다.
* **버전 관리 부재**: "이 토픽의 v3 스키마는 무엇이었는가"를 답할 방법이 없습니다.

### 스키마 레지스트리가 푸는 문제

스키마 레지스트리는 Avro/Protobuf/JSON Schema 같은 구조화된 포맷의 스키마를 중앙에서 저장·버전 관리하고, 호환성 규칙을 강제하는 별도 서비스입니다. 동작 방식은 대략 다음과 같습니다.

1. 프로듀서가 메시지를 보내기 전에 스키마를 레지스트리에 등록(또는 조회)합니다.
2. 레지스트리는 스키마 ID를 반환하고, 프로듀서는 실제 데이터 앞에 이 ID(보통 5바이트 magic byte + ID)만 붙여 직렬화합니다.
3. 컨슈머는 메시지에 포함된 스키마 ID로 레지스트리에서 스키마를 조회해 역직렬화합니다.
4. 레지스트리는 새 스키마가 등록될 때 이전 버전과의 호환성을 검사하고, 규칙을 어기면 등록 자체를 거부합니다.

이 구조 덕분에 프로듀서와 컨슈머는 **서로의 배포 일정을 몰라도** 안전하게 독립적으로 진화할 수 있습니다. 또한 페이로드에는 스키마 ID만 들어가므로 Avro/Protobuf 바이너리 인코딩은 JSON보다 훨씬 작습니다.

## 주요 구현체 비교

| 항목 | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **개발사** | Aiven | Red Hat | Confluent |
| **라이선스** | Apache License 2.0 | Apache License 2.0 | Confluent Community License (2018년 이후 완전한 오픈소스 아님) |
| **지원 포맷** | Avro, JSON Schema | Avro, Protobuf, JSON Schema, OpenAPI, AsyncAPI, GraphQL, Kconnect 등 | Avro, Protobuf, JSON Schema |
| **API 호환성** | Confluent REST API와 호환 | Confluent REST API 호환 모드 제공(`ccompat`) | 원조 API (사실상 표준) |
| **스토리지 백엔드** | Kafka 토픽 | Kafka 토픽 또는 SQL(PostgreSQL 등) | Kafka 토픽 |
| **REST Proxy 포함** | 포함(Karapace REST Proxy) | 별도 구성요소 없음(Registry만) | 별도 상용 REST Proxy |
| **상용 지원 조건** | Aiven 서비스 이용 시 또는 커뮤니티 | Red Hat 구독 시 | Confluent Platform 라이선스 필요(운영 규모에 따라) |
| **EKS/Strimzi 적합성** | 높음 — 순수 오픈소스, 가볍음 | 높음 — 멀티 포맷·멀티 백엔드 | 라이선스 검토 필요 |

**자체 관리 EKS + Strimzi 스택에서는 Karapace 또는 Apicurio Registry를 권장합니다.** 둘 다 Apache-2.0 라이선스로 배포·수정·재배포에 제약이 없고, Confluent Schema Registry가 사용하는 Confluent Community License는 특정 상용 서비스 제공을 금지하는 조항이 있어 완전한 오픈소스로 보기 어렵습니다. 새 Kafka Java 클라이언트 라이브러리(`kafka-avro-serializer` 등)는 Confluent가 배포하지만, API가 호환되므로 Karapace나 Apicurio를 가리키도록 `schema.registry.url`만 바꿔도 대부분 그대로 동작합니다.

## 직렬화 포맷

### Avro

Avro는 스키마를 JSON으로 정의하고, 데이터는 컴팩트한 바이너리로 직렬화합니다. Kafka 생태계에서 가장 널리 쓰이는 포맷이며, **writer 스키마**(데이터를 쓸 때 사용한 스키마)와 **reader 스키마**(데이터를 읽을 때 사용하는 스키마)가 서로 달라도 규칙에 따라 해석(schema resolution)할 수 있다는 점이 강력합니다.

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    { "name": "orderId", "type": "string" },
    { "name": "customerId", "type": "string" },
    { "name": "amount", "type": "double" },
    { "name": "currency", "type": "string", "default": "USD" },
    { "name": "createdAt", "type": "long", "logicalType": "timestamp-millis" }
  ]
}
```

### Protobuf

Protobuf는 `.proto` 파일로 스키마를 정의하고 `protoc`로 각 언어의 코드를 생성합니다. Avro와 유사하게 컴팩트한 바이너리 인코딩을 사용하지만, 필드에 번호를 명시적으로 부여하고 강한 타입 시스템을 가지고 있어 다중 언어 코드 생성 품질이 뛰어납니다. 최근 Kafka 생태계에서 Protobuf 채택이 늘고 있습니다.

```protobuf
syntax = "proto3";

package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at = 5;
}
```

### JSON Schema

JSON Schema는 JSON 페이로드 자체에 대한 검증 규칙을 정의합니다. 사람이 읽기 쉽고 디버깅이 편하지만, 필드명을 매 메시지마다 반복하므로 Avro/Protobuf보다 페이로드가 훨씬 큽니다. 스키마 검증은 필요하지만 성능·비용에 덜 민감한 워크로드에 적합합니다.

### 세 포맷 비교

| 항목 | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| 스키마 정의 | JSON | `.proto` IDL | JSON Schema |
| 페이로드 크기 | 작음 | 작음 | 큼 |
| 사람이 읽기 | 스키마만 가능 | 스키마만 가능 | 페이로드도 가능 |
| 언어 간 코드 생성 | 보통 | 우수 | 보통 |
| Kafka 생태계 채택도 | 매우 높음 | 높음(증가 중) | 중간 |
| 스키마 진화 규칙 | writer/reader 해석 | 필드 번호 기반 | JSON Schema 검증 규칙 |

## 호환성 전략

스키마 레지스트리는 새 스키마를 등록할 때 호환성 모드에 따라 이전 버전과 비교해 검증합니다. 4가지 모드를 정확히 구분해야 합니다.

| 모드 | 의미 | 업그레이드 순서 |
| --- | --- | --- |
| **BACKWARD** | 새 스키마로 만든 리더가 **이전** 스키마로 쓰여진 데이터를 읽을 수 있어야 함 | **컨슈머**를 먼저 업그레이드 |
| **FORWARD** | 이전 스키마로 만든 리더가 **새** 스키마로 쓰여진 데이터를 읽을 수 있어야 함 | **프로듀서**를 먼저 업그레이드 |
| **FULL** | BACKWARD와 FORWARD를 동시에 만족 | 순서 무관 |
| **NONE** | 호환성 검사를 하지 않음 | 수동 조율 필요 |

헷갈리기 쉬운 부분을 다시 짚어보면:

* **BACKWARD**는 "새 스키마(리더 기준)가 옛 데이터를 읽는다"는 뜻이므로, 실제로는 **새 스키마를 쓰는 컨슈머를 먼저 배포**해도 안전합니다. 프로듀서가 아직 옛 스키마로 데이터를 쓰고 있어도 새 컨슈머가 문제없이 읽습니다.
* **FORWARD**는 "옛 스키마(리더 기준)가 새 데이터를 읽는다"는 뜻이므로, **프로듀서를 먼저 새 스키마로 업그레이드**해도 옛 컨슈머가 여전히 읽을 수 있습니다.

### 호환 가능한 변경 예시

`Order` 스키마에 기본값이 있는 선택적 필드를 추가하는 것은 BACKWARD 호환입니다.

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

새 스키마로 만든 컨슈머가 옛 데이터(이 필드가 없는 데이터)를 읽으면 `default` 값(`null`)이 채워지므로 안전합니다.

### 깨지는 변경 예시

다음은 대표적인 BACKWARD 호환성 위반입니다.

* **기본값 없이 필수 필드 추가**: 새 스키마에 기본값 없는 `discount_code` 필드를 추가하면, 새 스키마로 옛 데이터(이 필드가 없는 데이터)를 읽을 때 필수 필드가 없어 실패합니다. (반대로 필드를 **제거**하는 것은 BACKWARD 호환이지만 FORWARD를 깨뜨립니다 — 옛 스키마로 만든 리더가 새 데이터를 읽을 때 이미 사라진 필드를 필수로 기대하기 때문입니다.)
* **필드 타입 변경**: `amount`를 `double`에서 `string`으로 바꾸면 기존 바이너리 데이터를 새 타입으로 해석할 수 없습니다.
* **필드 이름 변경**(alias 없이): 리더는 새 이름의 필드를 찾지만 옛 데이터에는 옛 이름으로만 존재합니다.

## Strimzi/EKS 배포

### Apicurio Registry 배포 (Kafka 토픽 스토리지)

Strimzi로 이미 Kafka 클러스터가 떠 있다는 전제로, Apicurio Registry를 같은 네임스페이스에 Deployment로 배포하고 스토리지를 Kafka 토픽 기반으로 구성할 수 있습니다.

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
      containers:
        - name: apicurio-registry
          image: quay.io/apicurio/apicurio-registry:3.0.6
          ports:
            - containerPort: 8080
          env:
            - name: APICURIO_STORAGE_KIND
              value: "kafkasql"
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: "my-kafka-cluster-kafka-bootstrap.kafka.svc:9092"
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
    - port: 8080
      targetPort: 8080
```

Apicurio는 `kafkasql` 대신 PostgreSQL 같은 SQL 백엔드(`APICURIO_STORAGE_KIND=sql`)도 지원하므로, 이미 운영 중인 RDS 인스턴스가 있다면 그쪽을 재사용할 수도 있습니다. Karapace를 쓴다면 스토리지는 항상 Kafka 토픽(`_schemas`)이며 별도 백엔드 설정이 필요 없습니다.

### 스키마 등록

레지스트리가 뜨면 REST API로 스키마를 등록합니다(Confluent 호환 API 기준).

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### 클라이언트 설정

Kafka Producer/Consumer 애플리케이션은 직렬화기에 레지스트리 URL을 지정합니다.

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

Karapace를 쓰는 경우도 동일한 `KafkaAvroSerializer`를 그대로 사용할 수 있습니다. `schema.registry.url`만 Karapace REST 엔드포인트(기본 포트 8081)로 바꾸면 됩니다. 즉 애플리케이션 코드는 레지스트리 구현체를 바꿔도 수정할 필요가 없습니다 — 이것이 Confluent 호환 API의 핵심 가치입니다.

## 다음 단계

스키마 레지스트리로 프로듀서와 컨슈머 간 데이터 계약을 안전하게 관리하는 방법을 다뤘습니다. 다음 Part 5에서는 Kafka Connect와 MirrorMaker를 이용해 외부 시스템과 데이터를 연동하고 클러스터 간 복제를 구성하는 방법을 살펴봅니다.

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)를 풀어보세요.
