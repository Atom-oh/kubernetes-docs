# 상태·체크포인트·스트리밍 패턴 퀴즈

본문의 Flink/Kafka와 Flink/Iceberg 버전 조합을 구분해 답하세요.

1. RocksDB를 선택하면 heap과 GC, memory sizing을 신경 쓰지 않아도 되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Native cache·managed memory·사용자 객체·operator state·buffer 등도 자원을 사용합니다.

**설명:** Keyed operator별 backend 인스턴스가 slot memory budget을 공유할 수 있습니다. 고정 MB 기준 대신 부하·state·checkpoint/restore를 측정합니다.

</details>

2. Flink 2.2에서 incremental snapshot은 RocksDB만 가능한가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Experimental ForSt도 async incremental snapshot을 사용합니다.

**설명:** ForSt는 remote SST/local cache 모델과 API/snapshot 제한을 확인해야 합니다. 이 장의 실제 설정 예제는 RocksDB입니다.

</details>

3. Incremental checkpoint 업로드량은 논리적 key 변경량에만 비례하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 새로운 SST와 metadata를 저장하며 compaction이 큰 파일을 다시 만들 수 있습니다.

**설명:** 재사용 shared SST는 참조됩니다. 아직 참조 중인 파일을 storage lifecycle로 임의 삭제하면 복구가 깨질 수 있습니다.

</details>

4. Incremental restore는 모든 이전 checkpoint를 순서대로 재생하나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 선택한 checkpoint가 참조하는 파일들을 복원합니다.

**설명:** Full checkpoint도 반드시 하나의 파일은 아닙니다. Network·파일 수·I/O와 canonical state 재구축 비용에 따라 복구 속도가 달라집니다.

</details>

5. Savepoint는 항상 수동 삭제 전까지 영구 보관되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Operator retention/dispose 설정과 CLAIM/NO_CLAIM 소유권에 따라 달라집니다.

**설명:** Checkpoint도 explicit trigger와 externalized retention을 사용할 수 있습니다. 저장소·파일 참조 관계·삭제 책임을 확인합니다.

</details>

6. Operator last-state는 항상 마지막 checkpoint 하나만 사용하나요?

<details>
<summary>정답 보기</summary>

**정답:** 접근 가능한 HA metadata나 마지막 checkpoint/savepoint 등 복구 경로에 따릅니다.

**설명:** State compatibility·UID·serializer·유효한 metadata가 필요합니다. 이름만으로 자동 복구나 migration 안전성을 보장하지 않습니다.

</details>

7. Kafka EXACTLY_ONCE는 checkpoint와 consumer에 어떤 조건이 있나요?

<details>
<summary>정답 보기</summary>

**정답:** Checkpoint 완료와 transaction commit이 연동되며 downstream은 read_committed를 사용해야 합니다.

**설명:** 재생 가능한 source와 복구 가능한 state도 필요합니다. 서로 다른 sink나 모든 subtask의 commit이 하나의 전역 transaction이 되는 것은 아닙니다.

</details>

8. transactionalIdPrefix는 언제 고유하고 언제 안정적이어야 하나요?

<details>
<summary>정답 보기</summary>

**정답:** 독립적인 동시 sink/job 사이에는 고유하고, 같은 논리적 실행의 재시작 동안에는 안정적으로 유지합니다.

**설명:** 충돌은 fencing을 일으킬 수 있고 prefix 변경은 lingering transaction 정리와 consumer 진행을 지연할 수 있습니다.

</details>

9. 60초 checkpoint interval이면 Kafka 출력 추가 지연은 최대 60초인가요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Checkpoint 소요·commit·실패/복구와 consumer 지연도 더해집니다.

**설명:** Transaction timeout은 broker 최대값과 worst-case checkpoint/recovery 시간에 맞춰야 합니다. 5.0.0 builder 기본값은 1시간입니다.

</details>

10. 모든 Kafka connector transaction naming 방식이 매번 새 ID를 만드나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. 기본 INCREMENTING과 달리 선택적 POOLING은 이름을 재사용합니다.

**설명:** POOLING에는 Kafka 3+·추가 topic read 권한과 migration 조건이 있습니다. 짧은 주기의 commit 부하는 별도로 측정합니다.

</details>

11. 실제 DynamicIcebergSink API와 이 장에서 검증한 runtime 조합은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답:** forInput → generator → catalogLoader → append이며 Iceberg 1.11.0 / Flink 2.1.3입니다.

**설명:** Generator는 Collector에 DynamicRecord를 내보냅니다. 2.1 runtime JAR를 Flink 2.2.1과 검증된 조합으로 취급하지 않습니다.

</details>

12. Insert-only Dynamic Iceberg helper를 그대로 Debezium CDC 처리기로 써도 되나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. RowKind·equality fields·upsert·table format과 schema 변경 제약을 검증해야 합니다.

**설명:** 관리형 Firehose/MSK Connect 대안도 source·권한·key·format·buffering과 오류 처리 조건을 확인해야 합니다.

</details>

13. SQL window query에서 event_time TIMESTAMP 컬럼만 선언하면 충분한가요?

<details>
<summary>정답 보기</summary>

**정답:** Streaming event-time window에는 time attribute가 필요하며 예제는 WATERMARK를 선언합니다.

**설명:** 검토한 Flink planner는 watermark를 뺀 일반 timestamp 변형을 거부했습니다. Connector/format JAR도 별도로 필요합니다.

</details>

14. 이 장의 S3 plugin과 bundled demo에 어떤 버전 제약이 있나요?

<details>
<summary>정답 보기</summary>

**정답:** Plugin은 지원 종료된 AWS SDK v1.12.779를 포함하고, StateMachineExample은 코드에서 2초 checkpoint interval을 설정합니다.

**설명:** v2 provider class를 그대로 섞지 않습니다. Config의 interval만 보고 실행 주기를 단정하지 말고 min-pause와 application override를 확인합니다.

</details>

15. Watermark 이후의 늦은 record는 항상 버리거나 자동 side output으로 보내나요?

<details>
<summary>정답 보기</summary>

**정답:** 아니요. Watermark는 진행 추정치이고 allowed lateness 동안 window가 다시 발행될 수 있습니다.

**설명:** Cleanup 이후 side output에는 명시적 설정이 필요합니다. Timestamp 추출·idleness·SQL과 DataStream의 차이를 확인합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/flink/03-state-checkpointing-streaming.md)
