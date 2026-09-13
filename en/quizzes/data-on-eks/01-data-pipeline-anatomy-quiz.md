# Anatomy of a Modern Data Pipeline Quiz

> **Last Updated**: September 12, 2026

1. What must be checked before replaying Kafka offsets?
   - A) Whether the needed records remain after retention/compaction
   - B) Whether Kafka automatically deduplicates every external sink
   - C) Whether all batch inputs were deleted
   - D) Whether every event always remains forever

<details>
<summary>Show Answer</summary>

**Answer: A) Whether the needed records remain after retention/compaction**

Replay requires retained input and consistent state recovery. End-to-end exactly-once also depends on sink transactions, idempotency and external effects.

</details>

2. What distinguishes ETL from ELT?
   - A) Whether a lake is used
   - B) ETL transforms before destination load; ELT transforms after destination load
   - C) Whether Kafka is used
   - D) ELT is always exact and ETL always approximate

<details>
<summary>Show Answer</summary>

**Answer: B) ETL transforms before destination load; ELT transforms after destination load**

Moving curated data into a warehouse does not by itself make the process ELT. Check the transformation order and destination.

</details>

3. Which statement about batch and stream accuracy is correct?
   - A) Streaming is always approximate
   - B) Batch is always exact
   - C) It depends on late data, duplicates, state and output contracts; fast provisional results can be followed by finalization
   - D) Checkpoints automatically make external API effects exactly-once

<details>
<summary>Show Answer</summary>

**Answer: C) It depends on late data, duplicates, state and output contracts; fast provisional results can be followed by finalization**

Design event time, watermarks, allowed lateness and sink semantics. Spark and Flink are not limited to one processing mode each.

</details>

4. Which statement about Schema Registry compatibility checks is correct?
   - A) They automatically block every database DDL and semantic change
   - B) They validate the registration/serialization/CI paths where applied, and consumer tests are still needed
   - C) One registration automatically ensures transitive compatibility across every version
   - D) Compatibility rules remove the need for data-quality checks

<details>
<summary>Show Answer</summary>

**Answer: B) They validate the registration/serialization/CI paths where applied, and consumer tests are still needed**

Bypass paths and business-semantic changes need separate validation. Check the scope of backward/forward and transitive settings.

</details>

[Study material](../../data-on-eks/01-data-pipeline-anatomy.md) | [Kafka quiz](./kafka/01-kafka-fundamentals-quiz.md)
