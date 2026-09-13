# 스키마 레지스트리 퀴즈

스키마 계약, 인코딩, 호환성, 저장·복구와 본문 배포 예제를 확인합니다.

## 1. Kafka의 기본 레코드 저장 기능만으로 스키마 계약을 강제할 수 없는 이유는 무엇인가요?

<details>
<summary>정답 보기</summary>

키와 값을 바이트로 저장하기 때문입니다. 구조·업무 의미의 검증은 사용하는 직렬화기, 애플리케이션과 별도 검증 경로에 달려 있습니다. 필드 추가가 항상 오류를 일으키지는 않습니다.

</details>

## 2. 레지스트리가 없는 JSON에는 버전 관리나 사전 검증을 적용할 수 없나요?

<details>
<summary>정답 보기</summary>

적용할 수 있습니다. JSON Schema, CI 검사와 버전 관리된 명세도 계약을 제공할 수 있습니다. 레지스트리는 중앙 관리와 배포를 돕고 바이너리 인코딩은 별도 선택입니다.

</details>

## 3. Confluent의 일반적인 스키마 ID payload framing에서 앞 5바이트의 구성은 무엇인가요?

<details>
<summary>정답 보기</summary>

magic byte 1바이트와 스키마 ID 4바이트입니다. 뒤에 값이 이어지며 Protobuf는 message index도 포함합니다. 모든 레지스트리·인코딩에 동일하게 적용되는 규칙은 아닙니다.

</details>

## 4. Karapace 6.2.3은 어떤 주요 스키마 형식을 지원하나요?

<details>
<summary>정답 보기</summary>

Avro, JSON Schema, Protobuf입니다. JSON Schema draft·키워드의 값 검증 지원과 호환성 분석 지원 범위는 별도로 확인합니다.

</details>

## 5. Apache-2.0과 Confluent 구성요소의 라이선스를 검토할 때 주의할 점은 무엇인가요?

<details>
<summary>정답 보기</summary>

Apache-2.0에도 고지 보존 등의 조건이 있습니다. Confluent 서버와 client/Avro 모듈은 라이선스가 다를 수 있습니다. 실제 구성요소와 지원 계약을 확인하며 규모만으로 비용·이용 조건을 단정하지 않습니다.

</details>

## 6. Avro 스키마 진화의 핵심 메커니즘과 기본값의 용도는 무엇인가요?

<details>
<summary>정답 보기</summary>

writer와 reader 스키마 간 해석 규칙입니다. 기본값은 writer 스키마에 없는 필드를 reader가 읽을 때 사용합니다. writer가 임의의 필수 필드를 생략해도 된다는 뜻은 아닙니다.

</details>

## 7. Protobuf 필드를 삭제한 뒤 같은 번호를 다른 의미의 필드에 재사용해도 되나요?

<details>
<summary>정답 보기</summary>

재사용하지 않습니다. 과거 데이터나 이전 클라이언트가 해당 번호를 다른 의미로 해석할 수 있습니다. 필요한 번호와 이름을 reserved로 남기고 wire type과 애플리케이션 의미를 검사합니다.

</details>

## 8. BACKWARD 호환성을 확인한 스키마의 일반적인 배포 순서는 무엇인가요?

<details>
<summary>정답 보기</summary>

컨슈머 먼저입니다. 새 reader가 이전 writer의 데이터를 읽을 수 있어야 합니다. 스키마 호환성 외의 업무 동작도 테스트해야 하며 토픽 자체가 아닌 subject 설정이라는 점에 유의합니다.

</details>

## 9. FORWARD는 어느 방향의 호환성을 뜻하나요?

<details>
<summary>정답 보기</summary>

이전 reader가 새 writer의 데이터를 읽는 방향입니다. 일반적으로 프로듀서를 먼저 갱신합니다. 이것만으로 새 reader의 오래된 데이터 재처리까지 검증되지는 않습니다.

</details>

## 10. Avro 필드를 제거하면 항상 FORWARD 호환성이 깨지나요?

<details>
<summary>정답 보기</summary>

아닙니다. 옛 reader에 그 필드의 기본값이 있으면 새 writer 데이터에서 빠진 값을 채울 수 있습니다. 기본값이 없으면 실패합니다. 새 reader가 제거된 필드를 요구하지 않는 BACKWARD 방향과 구분합니다.

</details>

## 11. 캐시가 비어 있는 컨슈머와 레지스트리 마이그레이션에서 무엇을 확인해야 하나요?

<details>
<summary>정답 보기</summary>

기존 레코드의 식별자로 동일한 writer 스키마를 찾을 수 있어야 합니다. ID 매핑, 참조, subject 전략, 인코딩, 인증과 클라이언트 버전을 검증합니다. URL만 바꾸는 것으로 충분하다고 가정하지 않습니다.

</details>

## 12. BACKWARD와 FORWARD를 동시에 요구하는 모드와 그 TRANSITIVE 변형은 무엇인가요?

<details>
<summary>정답 보기</summary>

FULL입니다. FULL_TRANSITIVE는 모든 이전 버전과 양방향 스키마 호환성을 검사합니다. 일반 FULL은 직전 버전과 비교하며 어느 쪽도 업무 의미나 코드 동작까지 보장하지 않습니다.

</details>

## 13. Apicurio KafkaSQL의 snapshots 토픽에 파일 전체가 저장되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 파일 경로를 기록합니다. 파일 자체의 영속성·공유·복구는 별도 설계가 필요합니다. 본문 실습은 예약 스냅샷을 끄고 전체 journal을 보존하여 재시작 때 재처리합니다.

</details>

## 14. KafkaSQL 3.3.3 journal·snapshots 토픽의 기본 보존 검사를 만족하는 설정은 무엇인가요?

<details>
<summary>정답 보기</summary>

`cleanup.policy=delete`, `retention.ms=-1`, `retention.bytes=-1`입니다. 무기한 보존이므로 디스크 증가를 관찰합니다. `_schemas`의 compaction이나 일반 이벤트의 짧은 보존 기간을 그대로 복사하지 않습니다.

</details>

## 15. Avro Producer와 Consumer에 각각 필요한 직렬화 관련 속성은 무엇인가요?

<details>
<summary>정답 보기</summary>

프로듀서는 `value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer`, 컨슈머는 `value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer`입니다. 둘 다 registry URL이 필요하며 브로커 TLS/SASL 설정과 라이브러리 의존성도 별도로 갖춰야 합니다.

</details>

## 16. timestamp-millis 필드와 기본값 있는 discountCode 필드의 Avro 정의를 작성하세요.

<details>
<summary>정답 보기</summary>

```json
[
  {"name":"createdAt","type":{"type":"long","logicalType":"timestamp-millis"}},
  {"name":"discountCode","type":["null","string"],"default":null}
]
```

이는 record의 `fields` 배열에 넣을 필드 정의입니다. 논리 타입은 type 객체 안에 놓고, 추가 필드의 null 기본값은 옛 데이터를 읽는 새 reader에 적용됩니다.

</details>

## 17. 본문과 같은 order.avsc를 orders-value subject에 등록하려면 무엇을 해야 하나요?

<details>
<summary>정답 보기</summary>

본문의 `register.sh` 예제처럼 JSON을 읽어 `schema` 문자열과 `schemaType: AVRO`를 가진 요청 파일을 만듭니다. `/apis/ccompat/v7/subjects/orders-value/versions`에 POST하고 HTTP 실패를 검사합니다. 먼저 호환성을 명시하고 등록 후 latest 버전을 조회합니다. 기본 TopicNameStrategy에서는 토픽 이름이 `orders`입니다.

</details>

## 18. 본문의 Apicurio 배포가 앞 장의 Strimzi 환경과 연결되기 위해 갖춰야 할 요소를 설명하세요.

<details>
<summary>정답 보기</summary>

3.3.3 이미지, `APICURIO_STORAGE_KIND=kafkasql`, `my-cluster-kafka-bootstrap.kafka.svc:9093`, SASL_SSL/SCRAM-SHA-512, CA truststore와 Secret의 JAAS 정보, 명시적 호스트 이름 검증이 필요합니다. 저장 토픽 3개와 사용자 ACL을 먼저 만들고 자동 토픽 생성을 끕니다. 관리 포트 9000의 health 검사와 HTTP API 8080을 구분합니다. HTTP API 인증은 Kafka 인증과 별개이며 실습 구성은 공개 서비스가 아닙니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/04-schema-registry.md) | [다음 퀴즈](./05-kafka-connect-mirrormaker-quiz.md)
