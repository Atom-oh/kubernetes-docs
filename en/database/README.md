# Databases on Kubernetes Overview

> **Last Updated**: September 11, 2026

"Should you run databases on Kubernetes?" is no longer a yes/no question. The real question is **which database, operated by which operator, on top of which storage**. This section covers that decision framework — and backs it with measured data rather than spec sheets.

## What's in this section

| Document | What it covers |
|----------|----------------|
| [ClickHouse on EKS Measured Benchmark](./01-clickhouse-on-eks.md) | A single-node ClickHouse on EKS loaded with 100 million log rows — measured ingest throughput, compression ratios, query latency, and the effect of a skip index |

## Managed vs self-hosted on Kubernetes

| Criterion | Managed (RDS/Aurora/ElastiCache) wins | K8s self-hosted wins |
|-----------|---------------------------------------|----------------------|
| Operations staffing | No dedicated DBA/platform team | A platform team owns the lifecycle |
| Engine availability | PostgreSQL/MySQL/Redis with mature managed offerings | Required regions/extensions/versions that available managed services cannot satisfy; also compare ClickHouse Cloud |
| Cost structure | Service price plus operations savings | Infrastructure, HA, backup, upgrades and staffing together |
| Deployment density | Few tenants | Dozens of per-tenant databases stamped out via GitOps |
| Control requirements | Check offered regions, encryption and audit capabilities | Own both the additional control and operational responsibility |

The key question is **who owns database lifecycle and recovery responsibilities**. A validated operator can automate parts of that work, but installation alone does not establish HA/backups. Verify supported engine/Kubernetes combinations and recovery features. A team using raw StatefulSets must implement the corresponding automation and operational responsibilities itself.

## The operator landscape (2026)

| Database | Leading operators | Maturity notes |
|----------|-------------------|----------------|
| PostgreSQL | CloudNativePG, Crunchy PGO, Zalando | Compare supported PostgreSQL/Kubernetes versions and recovery behavior |
| MySQL | Percona Operator, Vitess (sharding), MySQL Operator (Oracle) | Vitess is a sharding platform; compare Percona/Oracle engine and feature support |
| Redis/Valkey | OT-CONTAINER-KIT redis-operator and alternatives; verify engine support | For cache use, always compare against ElastiCache pricing first |
| ClickHouse | Altinity clickhouse-operator | Apache-2.0 database with a mature community operator; the managed alternative is ClickHouse Cloud |
| MongoDB | MongoDB Controllers for Kubernetes, Percona | Legacy Community Operator is deprecated; use the current repository/migration guide |
| Kafka | Strimzi | Streaming lives in the [Data Pipeline section](../data-on-eks/kafka/README.md) |

## Four operational pillars for databases on K8s

1. **Storage** — the volume type is your performance budget. As the [EBS gp2 vs gp3 benchmark](../storage/01-ebs-gp2-gp3-benchmark.md) shows, identical capacities can differ by 10x in IOPS. Databases start at gp3, with provisioned IOPS on the table.
2. **Topology** — spread replicas across AZs with `topologySpreadConstraints`, and price in cross-AZ transfer cost and replication lag while you're at it.
3. **Resource isolation** — when Guaranteed QoS is desired, every container needs equal CPU/memory requests and limits. It does not eliminate OOM, CPU throttling or node failures. Size CPU limits, caches, background work and query-memory headroom for the measured workload.
4. **Backups you have actually restored** — enabling the operator's backup (e.g. CloudNativePG's supported Barman Cloud plugin to S3) is table stakes; scheduled restore rehearsals are what make it real.

## Related reading

- [ClickHouse as a log backend](../observability/logging/04-clickhouse.md) — ClickHouse from the observability-pipeline angle
- [Kubernetes Storage](../core/04-storage.md) / [Storage section](../storage/README.md)
- [EKS Storage Part 1](../eks/04-eks-storage-part1.md)

## References

- [MongoDB operator migration](https://github.com/mongodb/mongodb-kubernetes/blob/master/docs/migration/community-operator-migration.md)
- [CloudNativePG](https://cloudnative-pg.io/docs/)
- [ClickHouse Cloud](https://clickhouse.com/cloud)
- [Altinity ClickHouse Operator](https://github.com/Altinity/clickhouse-operator)
