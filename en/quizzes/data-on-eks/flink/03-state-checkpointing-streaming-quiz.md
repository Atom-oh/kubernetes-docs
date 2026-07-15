# State, Checkpointing, and Streaming Patterns Quiz

This quiz tests your understanding of the HashMap vs RocksDB state backend trade-off, the difference between checkpoints and savepoints, how Kafka exactly-once delivery works through Flink's two-phase-commit protocol, and when Flink SQL/Table API is the better fit over the DataStream API.

## Multiple Choice Questions

1. What is the core trade-off between `HashMapStateBackend` and `EmbeddedRocksDBStateBackend`?
   - A) HashMap is off-heap and RocksDB is on-heap
   - B) HashMap is faster but limited by heap memory; RocksDB is slower per-access but can spill state to disk, scaling beyond memory
   - C) RocksDB doesn't support checkpointing at all
   - D) There is no functional difference — it's purely a naming choice

<details>

<summary>Show Answer</summary>

**Answer: B) HashMap is faster but limited by heap memory; RocksDB is slower per-access but can spill state to disk, scaling beyond memory**

**Explanation:**
HashMapStateBackend keeps state as native Java objects on the JVM heap, which is fast but bounded by available memory and adds GC pressure as state grows. EmbeddedRocksDBStateBackend stores state off-heap in a local RocksDB instance that spills to disk, trading some per-record latency (serialization overhead) for the ability to hold state far larger than memory.
</details>

2. Which state backend is required to enable incremental checkpoints?
   - A) HashMapStateBackend
   - B) EmbeddedRocksDBStateBackend
   - C) Either one, with no configuration difference
   - D) Neither — incremental checkpoints are always on

<details>

<summary>Show Answer</summary>

**Answer: B) EmbeddedRocksDBStateBackend**

**Explanation:**
Incremental checkpointing (`execution.checkpointing.incremental: true`) relies on persisting only the RocksDB SSTable files that changed since the previous checkpoint. HashMapStateBackend has no equivalent on-disk file structure to diff against, so it only supports full checkpoints.
</details>

3. What exactly does an incremental checkpoint persist?
   - A) A full copy of every key's current value
   - B) Only the changed RocksDB SSTable files since the last checkpoint, plus a manifest referencing still-valid prior files
   - C) Only the job's configuration, not its state
   - D) A diff computed by re-reading every key from the previous checkpoint

<details>

<summary>Show Answer</summary>

**Answer: B) Only the changed RocksDB SSTable files since the last checkpoint, plus a manifest referencing still-valid prior files**

**Explanation:**
Rather than re-uploading the entire state, an incremental checkpoint persists only the SSTable deltas produced since the previous checkpoint, along with a manifest recording which earlier SSTable files are still needed to reconstruct full state on restore.
</details>

4. Under what condition can restoring from an incremental checkpoint actually be slower than restoring from a full checkpoint?
   - A) It is never slower under any condition
   - B) When checkpoint storage access is network-bound, since recovery may require fetching many more individual files
   - C) When the job has no state at all
   - D) When `execution.checkpointing.mode` is set to `AT_LEAST_ONCE`

<details>

<summary>Show Answer</summary>

**Answer: B) When checkpoint storage access is network-bound, since recovery may require fetching many more individual files**

**Explanation:**
Recovering from an incremental checkpoint means fetching the latest delta plus every prior file the manifest still references — more individual fetches than a full checkpoint's single snapshot. If the path to storage (e.g., S3) is network-bound, that extra fetch count can make recovery slower. If the bottleneck is instead CPU/IOPS on the TaskManager, incremental checkpoints typically recover faster because there's less total data to write back to RocksDB.
</details>

5. What is the fundamental difference between a checkpoint and a savepoint?
   - A) They are the same mechanism with different names
   - B) Checkpoints are automatic and used for failure recovery; savepoints are explicit, user-triggered snapshots for planned upgrades and migrations
   - C) Savepoints are stored in memory, checkpoints on disk
   - D) Checkpoints can only be taken once per job's lifetime

<details>

<summary>Show Answer</summary>

**Answer: B) Checkpoints are automatic and used for failure recovery; savepoints are explicit, user-triggered snapshots for planned upgrades and migrations**

**Explanation:**
Both use the same filesystem-based checkpoint storage backend, but they serve different purposes: checkpoints are triggered automatically by Flink on a fixed interval and used for failure recovery, while savepoints are explicitly triggered (by a user or the Operator's `FlinkStateSnapshot`) and retained as durable artifacts for deliberate upgrades, migrations, or version bumps.
</details>

6. The Flink Kubernetes Operator's `last-state` upgrade mode restores from which artifact?
   - A) The most recent savepoint
   - B) The most recent checkpoint
   - C) A full re-read of the source topic from the beginning
   - D) A manually exported state file

<details>

<summary>Show Answer</summary>

**Answer: B) The most recent checkpoint**

**Explanation:**
`last-state` upgrade mode restores from the last completed checkpoint rather than a savepoint, which is what makes it fast and fully automatic — at the cost of being tied to the specific job graph that produced that checkpoint. Deliberate version bumps or migrations should use an explicit savepoint instead.
</details>

7. In Flink's `KafkaSink` two-phase-commit protocol for exactly-once delivery, what does the **KafkaCommitter** do?
   - A) It writes records to Kafka inside an open transaction
   - B) It commits the Kafka transaction only after the corresponding Flink checkpoint completes successfully
   - C) It deletes old checkpoints from S3
   - D) It negotiates the initial TCP connection to the broker

<details>

<summary>Show Answer</summary>

**Answer: B) It commits the Kafka transaction only after the corresponding Flink checkpoint completes successfully**

**Explanation:**
The KafkaWriter writes records inside an open Kafka transaction between checkpoints; those records stay invisible to `read_committed` consumers. Only once the enclosing Flink checkpoint completes does the KafkaCommitter commit the transaction, making the records visible downstream.
</details>

8. Why does `KafkaSink` with `EXACTLY_ONCE` require a stable `transactionalIdPrefix`?
   - A) It's purely cosmetic and shows up in logs only
   - B) Flink derives each subtask's transactional ID from it, and on restore it must match prior IDs so open transactions from before a failure can be correctly resolved
   - C) It sets the Kafka topic's replication factor
   - D) It determines the number of partitions in the sink topic

<details>

<summary>Show Answer</summary>

**Answer: B) Flink derives each subtask's transactional ID from it, and on restore it must match prior IDs so open transactions from before a failure can be correctly resolved**

**Explanation:**
Each sink subtask's actual Kafka transactional ID is derived from the configured prefix. If this prefix changes between runs, Flink can't line up the IDs used before a restart with the ones it uses after, breaking its ability to correctly abort or resolve transactions left open by a failure.
</details>

9. What is the direct latency cost of using `KafkaSink` with `DeliveryGuarantee.EXACTLY_ONCE`?
   - A) None — output latency is unaffected
   - B) Output becomes visible to `read_committed` consumers roughly one checkpoint interval later, since commits only happen after checkpoints complete
   - C) It doubles the number of Kafka partitions required
   - D) It requires disabling checkpointing entirely

<details>

<summary>Show Answer</summary>

**Answer: B) Output becomes visible to `read_committed` consumers roughly one checkpoint interval later, since commits only happen after checkpoints complete**

**Explanation:**
Because a Kafka transaction only commits once its enclosing Flink checkpoint completes, downstream consumers reading with `read_committed` see output delayed by roughly one checkpoint interval — a 60-second interval means up to ~60 seconds of added end-to-end latency.
</details>

10. What risk does setting the checkpoint interval too short introduce when using exactly-once `KafkaSink`?
    - A) It has no downside — shorter is always better
    - B) It can flood the Kafka broker's transaction coordinator with transactional IDs to track, since each checkpoint cycle opens a fresh transaction per sink subtask
    - C) It disables incremental checkpoints automatically
    - D) It forces the job to switch to `AT_LEAST_ONCE` mode

<details>

<summary>Show Answer</summary>

**Answer: B) It can flood the Kafka broker's transaction coordinator with transactional IDs to track, since each checkpoint cycle opens a fresh transaction per sink subtask**

**Explanation:**
Every checkpoint cycle opens a new transaction per sink subtask. Pushing the checkpoint interval down to just a few seconds across many parallel subtasks means the coordinator has to track many more transactional IDs, adding load. Checkpoint interval should be tuned as a balance between output latency and coordinator load, not purely for faster recovery.
</details>

11. What capability does Flink's Dynamic Iceberg Sink add over the standard Iceberg sink?
    - A) It can only write to a single, statically defined table
    - B) It can write to multiple Iceberg tables from one sink, choosing the destination table per record and evolving schema automatically based on record content
    - C) It removes the need for a schema entirely
    - D) It replaces the need for a Kafka source

<details>

<summary>Show Answer</summary>

**Answer: B) It can write to multiple Iceberg tables from one sink, choosing the destination table per record and evolving schema automatically based on record content**

**Explanation:**
The Dynamic Iceberg Sink extends the standard Iceberg sink to route each record to a table determined at runtime from its content, and to evolve that table's schema automatically as needed — a strong fit for CDC fan-out from a shared Kafka topic across many source tables.
</details>

12. When is a simpler connector-based pipeline (e.g., MSK → Data Firehose → S3 Tables/Iceberg, or MSK Connect with an Iceberg sink connector) preferable to Flink on EKS?
    - A) Never — Flink is always the better choice
    - B) When the pipeline is a straight passthrough or simple format conversion with no real computation needed
    - C) Only when using DataStream API instead of Table API
    - D) Only when the source is not Kafka

<details>

<summary>Show Answer</summary>

**Answer: B) When the pipeline is a straight passthrough or simple format conversion with no real computation needed**

**Explanation:**
Flink earns its operational cost when a pipeline needs actual computation — joins, windowed aggregation, per-record routing, complex event-time handling, or dynamic multi-table fan-out. For simple passthrough or format conversion, a fully managed Firehose pipeline or an MSK Connect sink connector is less to build and operate.
</details>

13. For which kind of use case is Flink SQL / Table API the recommended starting point?
    - A) Typical ETL, aggregation, and windowing that can be expressed declaratively
    - B) Only for jobs that need custom operators with fine-grained checkpoint control
    - C) Only for jobs with no state at all
    - D) Table API cannot connect to Kafka or Iceberg

<details>

<summary>Show Answer</summary>

**Answer: A) Typical ETL, aggregation, and windowing that can be expressed declaratively**

**Explanation:**
Flink SQL/Table API is the recommended entry point for most jobs because it requires far less code and ships with built-in connectors for Kafka, Iceberg, JDBC, and more. DataStream API remains necessary when a job needs custom operators, complex event-time/state logic, or fine control over checkpointing and backpressure behavior that the Table API planner doesn't expose.
</details>

14. Why would a job need to drop down to the DataStream API instead of staying in Flink SQL / Table API?
    - A) DataStream API is always faster for every workload
    - B) The job needs custom operators, complex event-time/state logic, or fine-grained control over checkpointing/backpressure that the SQL planner doesn't expose
    - C) SQL cannot read from Kafka
    - D) DataStream API requires less code in every case

<details>

<summary>Show Answer</summary>

**Answer: B) The job needs custom operators, complex event-time/state logic, or fine-grained control over checkpointing/backpressure that the SQL planner doesn't expose**

**Explanation:**
The Table API planner decides operator behavior on your behalf, which is fine for standard ETL/aggregation logic but limiting when a job needs a hand-written operator, direct access to custom state, or manual control over checkpoint alignment and backpressure — cases where DataStream API's lower-level control is necessary.
</details>

15. What role do watermarks play in event-time windowing?
    - A) They set the number of partitions for a window
    - B) They are a heuristic signal asserting no more records older than the watermark should arrive, letting windows know when it's safe to close and emit results
    - C) They control which state backend is used
    - D) They determine the Kafka transactional ID prefix

<details>

<summary>Show Answer</summary>

**Answer: B) They are a heuristic signal asserting no more records older than the watermark should arrive, letting windows know when it's safe to close and emit results**

**Explanation:**
Watermarks are periodically injected into the stream and assert that no further records with an older event-time timestamp should arrive. Windows rely on this signal, rather than wall-clock processing time, to decide when to close and emit a correct result — which keeps output consistent even under consumer lag or replay of historical data.
</details>

---

[Return to Learning Materials](../../../data-on-eks/flink/03-state-checkpointing-streaming.md)
