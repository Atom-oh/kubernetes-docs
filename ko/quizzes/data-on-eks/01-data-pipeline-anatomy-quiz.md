# 모던 데이터 파이프라인 해부 퀴즈

> **마지막 업데이트**: 2026년 9월 12일

1. Kafka offset을 되감아 재소비할 때 먼저 확인할 것은?
   - A) 보존·compaction 이후 필요한 레코드가 실제로 남아 있는지
   - B) Kafka가 모든 외부 sink의 중복을 자동 제거하는지
   - C) 배치 입력을 모두 삭제했는지
   - D) 항상 처음부터 모든 이벤트가 남는지

<details>
<summary>정답 보기</summary>

**정답: A) 보존·compaction 이후 필요한 레코드가 실제로 남아 있는지**

재처리에는 남아 있는 원본과 일관된 상태 복구가 필요합니다. end-to-end exactly-once는 sink 트랜잭션·멱등성과 외부 부작용 처리도 포함합니다.

</details>

2. ETL과 ELT를 구분하는 기준은?
   - A) 레이크 사용 여부
   - B) 대상 적재 전 변환하면 ETL, 대상 적재 후 변환하면 ELT
   - C) Kafka 사용 여부
   - D) ELT는 항상 정확하고 ETL은 항상 근사

<details>
<summary>정답 보기</summary>

**정답: B) 대상 적재 전 변환하면 ETL, 대상 적재 후 변환하면 ELT**

정제본을 웨어하우스로 옮기는 것만으로 ELT가 되지는 않습니다. 변환 시점과 대상 시스템을 확인합니다.

</details>

3. 배치와 스트림의 정확성에 대한 올바른 설명은?
   - A) 스트림은 항상 근사치이다
   - B) 배치는 항상 정확하다
   - C) 지연 데이터·중복·상태·출력 계약에 따라 달라지며 빠른 잠정 결과와 추후 확정을 조합할 수 있다
   - D) checkpoint를 사용하면 외부 API 부작용도 자동 exactly-once가 된다

<details>
<summary>정답 보기</summary>

**정답: C) 지연 데이터·중복·상태·출력 계약에 따라 달라지며 빠른 잠정 결과와 추후 확정을 조합할 수 있다**

event time·watermark·허용 지연·sink 의미를 설계해야 합니다. Spark와 Flink 모두 하나의 처리 방식만 지원하는 제품이 아닙니다.

</details>

4. Schema Registry 호환성 검사에 대한 올바른 설명은?
   - A) 모든 DB DDL과 업무 의미 변경을 자동 차단한다
   - B) 등록·serialization·CI에서 실제로 적용한 경로를 검증하며 소비자 테스트도 필요하다
   - C) 한 번 등록하면 모든 버전에 대한 전이적 호환성이 자동 보장된다
   - D) 호환성 규칙이 있으면 데이터 품질 검사는 필요 없다

<details>
<summary>정답 보기</summary>

**정답: B) 등록·serialization·CI에서 실제로 적용한 경로를 검증하며 소비자 테스트도 필요하다**

검사를 우회하는 경로나 업무 의미 변경은 별도 검증 대상입니다. 후방/전방 및 transitive 설정에 따른 검사 범위를 확인합니다.

</details>

[학습 자료](../../data-on-eks/01-data-pipeline-anatomy.md) | [Kafka 퀴즈](./kafka/01-kafka-fundamentals-quiz.md)
