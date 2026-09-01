# Databases on Kubernetes Overview

> **Last Updated**: September 1, 2026

"Should you run databases on Kubernetes?" is no longer a yes/no question. The real question is **which database, operated by which operator, on top of which storage**. This section covers that decision framework — and backs it with measured data rather than spec sheets.

## What's in this section

| Document | What it covers |
|----------|----------------|
| [ClickHouse on EKS Measured Benchmark](./01-clickhouse-on-eks.md) | A single-node ClickHouse on EKS loaded with 100 million log rows — measured ingest throughput, compression ratios, query latency, and the effect of a skip index |

## Managed vs self-hosted on Kubernetes

| Criterion | Managed (RDS/Aurora/ElastiCache) wins | K8s self-hosted wins |
|-----------|---------------------------------------|----------------------|
| Operations staffing | No dedicated DBA/platform team | A platform team owns the lifecycle |
| Engine availability | PostgreSQL/MySQL/Redis with mature managed offerings | ClickHouse, specific extensions, versions the managed service doesn't offer |
| Cost structure | A few large instances | Many small/medium clusters (managed markup compounds) |
| Deployment density | Few tenants | Dozens of per-tenant databases stamped out via GitOps |
| Compliance | Standard certifications suffice | You must control data placement and encryption yourself |

The core principle: **operating a raw StatefulSet is not one of the options.** The only realistic path to production databases on Kubernetes is a mature operator — it owns failover, backups, minor-version upgrades, and replication topology.

## The operator landscape (2026)

| Database | Leading operators | Maturity notes |
|----------|-------------------|----------------|
| PostgreSQL | CloudNativePG, Crunchy PGO, Zalando | CloudNativePG is converging on de-facto standard status in the CNCF ecosystem |
| MySQL | Percona Operator, Vitess (sharding), MySQL Operator (Oracle) | Vitess if you need horizontal sharding, otherwise Percona |
| Redis/Valkey | OT-CONTAINER-KIT redis-operator, Valkey Operator | For cache use, always compare against ElastiCache pricing first |
| ClickHouse | Altinity clickhouse-operator | One of the most commonly self-hosted databases relative to its managed offering |
| MongoDB | MongoDB Community Operator, Percona | Mind the SSPL license |
| Kafka | Strimzi | Streaming lives in the [Data Pipeline section](../data-on-eks/kafka/README.md) |

## Four operational pillars for databases on K8s

1. **Storage** — the volume type is your performance budget. As the [EBS gp2 vs gp3 benchmark](../storage/01-ebs-gp2-gp3-benchmark.md) shows, identical capacities can differ by 10x in IOPS. Databases start at gp3, with provisioned IOPS on the table.
2. **Topology** — spread replicas across AZs with `topologySpreadConstraints`, and price in cross-AZ transfer cost and replication lag while you're at it.
3. **Resource isolation** — database pods should run Guaranteed QoS (requests = limits), and the memory limit must agree with the engine's own cache settings or you'll trade cache hits for OOMKills.
4. **Backups you have actually restored** — enabling the operator's backup (e.g. CloudNativePG's barman-cloud to S3) is table stakes; scheduled restore rehearsals are what make it real.

## Related reading

- [ClickHouse as a log backend](../observability/logging/04-clickhouse.md) — ClickHouse from the observability-pipeline angle
- [Kubernetes Storage](../core/04-storage.md) / [Storage section](../storage/README.md)
- [EKS Storage Part 1](../eks/04-eks-storage-part1.md)
