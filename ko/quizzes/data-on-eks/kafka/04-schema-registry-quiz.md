# 스키마 레지스트리 퀴즈

이 퀴즈는 스키마 레지스트리가 필요한 이유, Avro/Protobuf 직렬화 포맷, 4가지 호환성 모드, 주요 구현체(Karapace, Apicurio, Confluent)의 라이선스 차이에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kafka 브로커가 메시지의 내용을 검증하지 않는다는 사실이 야기하는 가장 근본적인 문제는 무엇인가요?
   - A) 브로커의 처리량이 낮아짐
   - B) 프로듀서와 컨슈머가 서로의 스키마 변경을 인지하지 못해 역직렬화 실패가 발생할 수 있음
   - C) 토픽을 여러 개 만들 수 없음
   - D) 파티션 리밸런싱이 불가능해짐

<details>

<summary>정답 보기</summary>

**정답: B) 프로듀서와 컨슈머가 서로의 스키마 변경을 인지하지 못해 역직렬화 실패가 발생할 수 있음**

**설명:**
Kafka는 메시지를 바이트 배열로만 다루므로 데이터 형식을 강제하지 않습니다. 프로듀서와 컨슈머는 독립적으로 배포되는 별도 애플리케이션이기 때문에, 한쪽이 스키마를 바꾸면 다른 쪽이 이를 모른 채 역직렬화에 실패하거나 잘못된 값을 읽을 위험이 있습니다. 스키마 레지스트리는 이 계약을 중앙에서 관리하고 호환성을 강제하여 이 문제를 해결합니다.
</details>

2. 스키마가 없는 JSON 페이로드와 비교했을 때 Avro/Protobuf 같은 바이너리 포맷 + 스키마 레지스트리 조합의 가장 큰 장점은 무엇인가요?
   - A) 사람이 읽기 더 쉬워짐
   - B) 페이로드가 작아지고 스키마 변경이 중앙에서 검증됨
   - C) 파티션 수를 자동으로 조절함
   - D) 컨슈머 그룹이 필요 없어짐

<details>

<summary>정답 보기</summary>

**정답: B) 페이로드가 작아지고 스키마 변경이 중앙에서 검증됨**

**설명:**
Avro/Protobuf는 필드명을 반복하지 않는 컴팩트 바이너리 인코딩을 사용하므로 JSON보다 페이로드가 작습니다. 또한 메시지에는 스키마 전체가 아니라 스키마 ID만 포함되고, 실제 스키마는 레지스트리가 관리하며 새 버전 등록 시 호환성을 검증합니다. 반면 사람이 직접 읽기는 JSON이 더 쉽습니다.
</details>

3. 스키마 레지스트리를 사용할 때 실제로 전송되는 메시지에 포함되는 것은 무엇인가요?
   - A) 스키마 전체 정의
   - B) 스키마 ID를 포함한 짧은 헤더와 바이너리 인코딩된 데이터
   - C) 스키마 레지스트리의 URL
   - D) 컨슈머 그룹 ID

<details>

<summary>정답 보기</summary>

**정답: B) 스키마 ID를 포함한 짧은 헤더와 바이너리 인코딩된 데이터**

**설명:**
프로듀서는 스키마를 레지스트리에 등록(또는 조회)하고 반환된 스키마 ID를 magic byte와 함께 메시지 앞에 붙입니다. 실제 스키마 정의 자체는 메시지에 포함되지 않고 레지스트리에만 저장되므로 페이로드 크기가 크게 줄어듭니다. 컨슈머는 이 ID로 레지스트리에서 스키마를 조회해 역직렬화합니다.
</details>

4. 다음 중 Apache License 2.0으로 배포되는 스키마 레지스트리 구현체는 무엇인가요?
   - A) Confluent Schema Registry
   - B) Karapace와 Apicurio Registry
   - C) Karapace만
   - D) Apicurio Registry만

<details>

<summary>정답 보기</summary>

**정답: B) Karapace와 Apicurio Registry**

**설명:**
Karapace(Aiven)와 Apicurio Registry(Red Hat)는 모두 Apache License 2.0으로 배포되는 순수 오픈소스 프로젝트입니다. Confluent Schema Registry는 2018년 이후 Confluent Community License를 적용하고 있어 특정 상용 이용 제한이 있는, 완전한 오픈소스는 아닙니다.
</details>

5. 자체 관리(self-managed) EKS + Strimzi 스택에서 라이선스 마찰을 피하기 위해 권장되는 스키마 레지스트리 조합은 무엇인가요?
   - A) Confluent Schema Registry 단독
   - B) Karapace 또는 Apicurio Registry
   - C) 스키마 레지스트리 없이 JSON만 사용
   - D) AWS Glue Schema Registry만 사용 가능

<details>

<summary>정답 보기</summary>

**정답: B) Karapace 또는 Apicurio Registry**

**설명:**
Karapace와 Apicurio Registry는 Apache-2.0 라이선스로 제약 없이 자체 호스팅할 수 있습니다. Confluent Schema Registry는 Confluent Community License의 제약 때문에 자체 관리 환경에서 라이선스 검토가 필요합니다. 두 오픈소스 구현체 모두 Confluent REST API와 호환되므로 클라이언트 코드 변경 없이 대체할 수 있습니다.
</details>

6. Avro 직렬화의 스키마 진화(schema evolution)를 가능하게 하는 핵심 메커니즘은 무엇인가요?
   - A) 필드 번호 기반 매핑
   - B) writer 스키마와 reader 스키마 간의 해석(resolution) 규칙
   - C) JSON Schema의 `$ref` 참조
   - D) 컴파일 타임 코드 생성

<details>

<summary>정답 보기</summary>

**정답: B) writer 스키마와 reader 스키마 간의 해석(resolution) 규칙**

**설명:**
Avro는 데이터를 쓸 때 사용한 writer 스키마와 읽을 때 사용하는 reader 스키마가 정확히 같지 않아도, 정의된 해석 규칙(필드 매칭, 기본값 적용 등)에 따라 데이터를 올바르게 읽어낼 수 있습니다. 필드 번호 기반 매핑은 Protobuf의 특징입니다.
</details>

7. Protobuf가 Avro에 비해 상대적으로 강점을 갖는 부분은 무엇인가요?
   - A) 페이로드가 항상 더 작음
   - B) 명시적 필드 번호와 강한 타입 시스템으로 인한 우수한 다중 언어 코드 생성
   - C) 스키마 레지스트리가 필요 없음
   - D) JSON보다 사람이 읽기 쉬움

<details>

<summary>정답 보기</summary>

**정답: B) 명시적 필드 번호와 강한 타입 시스템으로 인한 우수한 다중 언어 코드 생성**

**설명:**
Protobuf는 `.proto` IDL에서 필드마다 명시적인 번호를 부여하고 엄격한 타입 시스템을 가지고 있어, `protoc`로 생성하는 다중 언어 클라이언트 코드의 품질이 우수한 편입니다. 페이로드 크기는 Avro와 대체로 비슷한 수준이며, Protobuf도 스키마 레지스트리와 함께 사용하는 경우가 많습니다.
</details>

8. 호환성 모드가 BACKWARD로 설정된 토픽에서 안전하게 먼저 업그레이드해야 하는 쪽은 어디인가요?
   - A) 프로듀서
   - B) 컨슈머
   - C) 브로커
   - D) ZooKeeper 또는 KRaft 컨트롤러

<details>

<summary>정답 보기</summary>

**정답: B) 컨슈머**

**설명:**
BACKWARD 호환성은 "새 스키마로 만든 리더가 이전 스키마로 쓰여진 데이터를 읽을 수 있어야 한다"는 뜻입니다. 즉 새 스키마를 사용하는 컨슈머를 먼저 배포해도, 아직 이전 스키마로 데이터를 쓰고 있는 프로듀서와 안전하게 공존할 수 있습니다. 반대로 FORWARD는 프로듀서를 먼저 업그레이드하는 순서에 안전합니다.
</details>

9. 다음 중 FORWARD 호환성 모드에 대한 올바른 설명은 무엇인가요?
   - A) 새 스키마로 쓰여진 데이터를 이전 스키마의 리더가 읽을 수 있어야 한다
   - B) 이전 스키마로 쓰여진 데이터를 새 스키마의 리더가 읽을 수 있어야 한다
   - C) 호환성 검사를 전혀 수행하지 않는다
   - D) 컨슈머를 항상 먼저 업그레이드해야 한다

<details>

<summary>정답 보기</summary>

**정답: A) 새 스키마로 쓰여진 데이터를 이전 스키마의 리더가 읽을 수 있어야 한다**

**설명:**
FORWARD는 "옛 스키마(리더 기준)가 새 데이터를 읽을 수 있어야 한다"는 의미입니다. 이 모드에서는 프로듀서가 새 스키마로 먼저 업그레이드되어도, 아직 이전 스키마를 사용하는 컨슈머가 문제없이 데이터를 읽을 수 있습니다. B는 BACKWARD의 정의이며, C는 NONE, D는 BACKWARD에서의 안전한 순서에 해당합니다.
</details>

10. 다음 중 BACKWARD 호환성을 위반하는 스키마 변경은 무엇인가요?
    - A) 기본값이 있는 선택적 필드 추가
    - B) 기본값 없이 필수 필드를 추가
    - C) 필드에 문서 주석(doc) 추가
    - D) 필드 순서만 재배치(이름·타입 변경 없이)

<details>

<summary>정답 보기</summary>

**정답: B) 기본값 없이 필수 필드를 추가**

**설명:**
새 스키마에 기본값 없는 필수 필드를 추가하면, 그 새 스키마로 옛 데이터(해당 필드가 아예 없던 데이터)를 읽을 때 리더가 값을 기대하지만 데이터에는 존재하지 않아 읽기가 실패합니다. 반대로 필드를 **제거**하는 것은 BACKWARD 호환입니다 — 새 스키마의 리더는 애초에 그 필드를 찾지 않기 때문입니다(다만 FORWARD는 깨뜨립니다). 기본값이 있는 선택적 필드 추가는 대표적인 BACKWARD 호환 변경이며, 문서 주석 추가나 필드 재배치(Avro는 이름 기반 매칭)는 데이터 구조에 영향을 주지 않습니다.
</details>

## 단답형 문제

11. 컨슈머가 메시지를 역직렬화할 때 사용할 스키마를 찾기 위해 메시지에서 읽어내는 정보는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 스키마 ID (Schema ID)**

**설명:**
프로듀서는 메시지를 직렬화할 때 스키마 전체가 아니라 레지스트리에서 발급받은 스키마 ID(보통 magic byte와 함께 앞부분에 인코딩)만 포함시킵니다. 컨슈머는 이 ID를 읽어 레지스트리에 조회 요청을 보내고, 반환된 스키마 정의로 나머지 바이너리 데이터를 역직렬화합니다.
</details>

12. BACKWARD와 FULL을 동시에 만족하는, 즉 양방향 호환성을 모두 요구하는 호환성 모드의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: FULL**

**설명:**
FULL 모드는 BACKWARD(새 리더가 옛 데이터를 읽음)와 FORWARD(옛 리더가 새 데이터를 읽음)를 동시에 요구합니다. 이 모드에서는 프로듀서와 컨슈머의 업그레이드 순서에 관계없이 안전하지만, 그만큼 스키마 변경에 가장 엄격한 제약이 걸립니다.
</details>

13. Apicurio Registry가 지원하는 두 가지 스토리지 백엔드 종류는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Kafka 토픽 기반(kafkasql)과 SQL 기반(sql, 예: PostgreSQL)**

**설명:**
Apicurio Registry는 `APICURIO_STORAGE_KIND` 환경변수로 `kafkasql`(Kafka 토픽에 저장) 또는 `sql`(PostgreSQL 등 관계형 DB에 저장) 백엔드를 선택할 수 있습니다. Karapace는 이와 달리 항상 Kafka 토픽(`_schemas`)만 스토리지로 사용합니다.
</details>

14. Confluent Schema Registry가 2018년 이후 완전한 오픈소스가 아니게 된 이유는 어떤 라이선스로 전환했기 때문인가요?

<details>

<summary>정답 보기</summary>

**정답: Confluent Community License**

**설명:**
Confluent는 2018년경 여러 핵심 컴포넌트(Schema Registry 포함)를 Confluent Community License로 전환했습니다. 이 라이선스는 소스 코드를 볼 수 있게 하지만, 이를 이용해 Confluent와 경쟁하는 관리형 서비스를 제공하는 것을 금지하는 등 OSI 승인 오픈소스 라이선스보다 제약이 많습니다.
</details>

15. Kafka 클라이언트에서 Avro 직렬화기가 스키마 레지스트리의 위치를 알기 위해 설정하는 속성 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: schema.registry.url**

**설명:**
`schema.registry.url` 속성은 `KafkaAvroSerializer`/`KafkaAvroDeserializer` 등이 스키마를 등록하거나 조회할 레지스트리의 REST 엔드포인트를 지정합니다. 이 속성만 Karapace, Apicurio, Confluent 중 원하는 구현체의 엔드포인트로 바꾸면 애플리케이션 코드 변경 없이 레지스트리를 교체할 수 있습니다.
</details>

## 실습 문제

16. `discountCode`라는 선택적 필드를 기존 Avro `Order` 스키마에 BACKWARD 호환 방식으로 추가하는 필드 정의를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

**설명:**
유니온 타입 `["null", "string"]`과 `default: null`을 함께 지정하면, 새 스키마로 만든 리더가 이 필드가 없는 옛 데이터를 읽을 때 자동으로 `null`이 채워집니다. 기본값이 없는 필수 필드를 추가하면 BACKWARD 호환성이 깨지므로, 기존 데이터와의 호환을 유지하려면 항상 기본값을 지정해야 합니다.
</details>

17. `Order-value` 서브젝트에 새로운 Avro 스키마를 등록하는 Confluent 호환 REST API 호출을 curl로 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

**설명:**
`/subjects/<subject>/versions`에 `POST` 요청을 보내면 스키마가 등록됩니다. `<topic>-value`는 해당 토픽의 값(value) 페이로드에 대한 스키마를 지정하는 Confluent의 표준 서브젝트 명명 규칙입니다. 요청 본문의 `schema` 필드는 실제 Avro 스키마 JSON을 문자열로 이스케이프하여 전달합니다. 등록 시 레지스트리는 설정된 호환성 모드에 따라 이전 버전과 검증을 수행합니다.
</details>

18. Strimzi Kafka 클러스터와 같은 네임스페이스에서, Kafka 토픽을 스토리지 백엔드로 사용하는 Apicurio Registry Deployment의 핵심 컨테이너 스펙(이미지, 환경변수)을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
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
```

**설명:**
`APICURIO_STORAGE_KIND=kafkasql`은 Apicurio가 스키마 메타데이터를 별도 DB 없이 Kafka 토픽에 저장하도록 지정합니다. `APICURIO_KAFKASQL_BOOTSTRAP_SERVERS`는 Strimzi가 생성한 부트스트랩 서비스(`<cluster-name>-kafka-bootstrap`)를 가리켜야 합니다. SQL 백엔드를 사용하려면 `APICURIO_STORAGE_KIND=sql`과 데이터소스 연결 정보를 대신 설정합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/04-schema-registry.md) | [다음 퀴즈: Kafka Connect와 MirrorMaker](./05-kafka-connect-mirrormaker-quiz.md)
