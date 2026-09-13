# State, Checkpointing and Streaming Patterns Quiz

Distinguish the chapter's Flink/Kafka and Flink/Iceberg version combinations.

1. Does choosing RocksDB remove heap, GC and memory-sizing concerns?

<details>
<summary>Show Answer</summary>

**Answer:** No. Native caches, managed memory, user objects, operator state and buffers still consume resources.

**Explanation:** Keyed-operator backends can share a slot memory budget. Measure workloads/state and checkpoint/restore rather than using a fixed MB cutoff.

</details>

2. Are incremental snapshots exclusive to RocksDB in Flink 2.2?

<details>
<summary>Show Answer</summary>

**Answer:** No. Experimental ForSt also uses asynchronous incremental snapshots.

**Explanation:** Check its remote-SST/local-cache model and API/snapshot limitations. This chapter's configuration example uses RocksDB.

</details>

3. Does incremental-checkpoint upload size depend only on logical key changes?

<details>
<summary>Show Answer</summary>

**Answer:** No. It persists new SSTs/metadata, and compaction can rewrite large files.

**Explanation:** Reusable shared SSTs are referenced. Expiring files that are still referenced can break recovery.

</details>

4. Does incremental restore replay all earlier checkpoints sequentially?

<details>
<summary>Show Answer</summary>

**Answer:** No. It restores files referenced by the selected checkpoint.

**Explanation:** Full checkpoints are not necessarily single files. Recovery depends on networking, file counts, I/O and canonical-state reconstruction costs.

</details>

5. Is a savepoint always permanent until someone manually deletes it?

<details>
<summary>Show Answer</summary>

**Answer:** No. Operator retention/disposal and CLAIM/NO_CLAIM ownership affect its lifecycle.

**Explanation:** Checkpoints can also have explicit triggers and externalized retention. Check storage, references and deletion responsibility.

</details>

6. Does Operator last-state always use one last checkpoint file?

<details>
<summary>Show Answer</summary>

**Answer:** Recovery depends on accessible HA metadata or the last checkpoint/savepoint and the applicable path.

**Explanation:** Valid metadata, state compatibility, UIDs and serializers are required; the label alone does not guarantee recovery or migration safety.

</details>

7. What do Kafka EXACTLY_ONCE guarantees require from checkpoints and consumers?

<details>
<summary>Show Answer</summary>

**Answer:** Transaction commits are coordinated with checkpoint completion, and downstream consumers must use read_committed.

**Explanation:** Replayable sources and recoverable state are also needed. Different sinks/all subtasks do not become one global transaction.

</details>

8. When should transactionalIdPrefix be unique, and when should it remain stable?

<details>
<summary>Show Answer</summary>

**Answer:** Unique across independent concurrent sinks/jobs; stable across restarts of the same logical execution.

**Explanation:** Collisions can cause fencing, while changes can delay lingering-transaction cleanup and consumer progress.

</details>

9. Does a 60-second checkpoint interval cap added Kafka latency at 60 seconds?

<details>
<summary>Show Answer</summary>

**Answer:** No. Checkpoint duration, commits, failures/recovery and consumer delay also contribute.

**Explanation:** Align transaction timeout with broker limits and worst-case recovery. The 5.0.0 builder defaults to one hour.

</details>

10. Does every Kafka connector transaction-naming strategy create a new ID each time?

<details>
<summary>Show Answer</summary>

**Answer:** No. Optional POOLING reuses names, unlike default INCREMENTING.

**Explanation:** POOLING requires Kafka 3+, additional topic-read permissions and migration checks. Measure frequent-commit load separately.

</details>

11. What real DynamicIcebergSink API and runtime combination were checked?

<details>
<summary>Show Answer</summary>

**Answer:** forInput → generator → catalogLoader → append; Iceberg 1.11.0 with Flink 2.1.3.

**Explanation:** The generator emits DynamicRecords to a Collector. A Flink 2.1 runtime JAR is not presented as validated with Flink 2.2.1.

</details>

12. Can the insert-only Dynamic Iceberg helper serve unchanged as a Debezium CDC processor?

<details>
<summary>Show Answer</summary>

**Answer:** No. Validate RowKind, equality fields, upsert, table formats and schema-evolution limits.

**Explanation:** Managed Firehose/MSK Connect alternatives also need source, permissions, keys, formats, buffering and failure handling checked.

</details>

13. Is declaring an event_time TIMESTAMP column enough for the SQL window query?

<details>
<summary>Show Answer</summary>

**Answer:** A streaming event-time window needs a time attribute; the example declares a WATERMARK.

**Explanation:** The reviewed planner rejects the plain-timestamp variant without it. Connector/format JARs are also needed.

</details>

14. What version-specific limits apply to the S3 plugin and bundled demo?

<details>
<summary>Show Answer</summary>

**Answer:** The plugin contains end-of-support AWS SDK v1.12.779; StateMachineExample sets a two-second checkpoint interval in code.

**Explanation:** Do not mix in v2 provider classes blindly. Inspect min-pause and application overrides rather than inferring cadence only from config.

</details>

15. Are late records after a watermark always dropped or automatically sent to a side output?

<details>
<summary>Show Answer</summary>

**Answer:** No. Watermarks estimate progress; windows can fire again during allowed lateness.

**Explanation:** Side output after cleanup requires explicit configuration. Check timestamp extraction, idleness and SQL/DataStream differences.

</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/03-state-checkpointing-streaming.md)
