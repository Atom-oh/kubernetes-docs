# Kubernetes 上的数据库概览

> **最后更新**：2026 年 9 月 11 日

“是否应在 Kubernetes 上运行数据库？”已经不再是简单的是非题。真正的问题是：**要用哪种数据库、由哪个 Operator 运维、运行在哪种存储之上**。本节介绍该决策框架，并使用实测数据而非规格表来佐证。

## 本节内容

| 文档 | 内容 |
|----------|----------------|
| [EKS 上 ClickHouse 的实测基准](./01-clickhouse-on-eks.md) | 在 EKS 单节点 ClickHouse 中加载 1 亿条日志，测量写入吞吐量、压缩率、查询延迟以及跳过索引的影响 |

## 托管服务与 Kubernetes 自托管

| 标准 | 托管服务（RDS/Aurora/ElastiCache）的优势 | K8s 自托管的优势 |
|-----------|---------------------------------------|----------------------|
| 运维人员配置 | 无需专职 DBA/平台团队 | 平台团队负责整个生命周期 |
| 引擎可用性 | PostgreSQL/MySQL/Redis 有成熟的托管服务 | 所需区域/扩展/版本无法由现有托管服务满足；同时比较 ClickHouse Cloud |
| 成本结构 | 服务价格加上运维成本节省 | 将基础设施、高可用、备份、升级和人员成本合并评估 |
| 部署密度 | 租户数量较少 | 通过 GitOps 批量部署数十个租户各自的数据库 |
| 控制要求 | 核实所提供的区域、加密和审计能力 | 自行承担额外控制措施和运维责任 |

关键问题是：**由谁负责数据库生命周期和恢复工作**。经过验证的 Operator 可以自动化其中一部分，但仅安装 Operator 并不能证明已经具备高可用/备份能力。应核实受支持的引擎/Kubernetes 组合和恢复功能。使用原生 StatefulSet 的团队必须自行实现相应自动化并履行运维职责。

## Operator 生态（2026 年）

| 数据库 | 主要 Operator | 成熟度说明 |
|----------|-------------------|----------------|
| PostgreSQL | CloudNativePG、Crunchy PGO、Zalando | 比较支持的 PostgreSQL/Kubernetes 版本和恢复行为 |
| MySQL | Percona Operator、Vitess（分片）、MySQL Operator（Oracle） | Vitess 是分片平台；比较 Percona/Oracle 对引擎和功能的支持 |
| Redis/Valkey | OT-CONTAINER-KIT redis-operator 等方案；应核实引擎支持情况 | 用于缓存时，应先与 ElastiCache 定价比较 |
| ClickHouse | Altinity clickhouse-operator | 采用 Apache-2.0 许可证的数据库，拥有成熟的社区 Operator；托管替代方案是 ClickHouse Cloud |
| MongoDB | MongoDB Controllers for Kubernetes、Percona | 旧版 Community Operator 已弃用；请使用当前仓库/迁移指南 |
| Kafka | Strimzi | 流处理内容位于[数据管道章节](../data-on-eks/kafka/README.md) |

## 在 K8s 上运行数据库的四个运维支柱

1. **存储**：卷类型决定性能预算。[EBS gp2 与 gp3 基准测试](../storage/01-ebs-gp2-gp3-benchmark.md)显示，即使容量相同，IOPS 也可能相差 10 倍。数据库通常从 gp3 开始，必要时可选择预置 IOPS。
2. **拓扑**：使用 `topologySpreadConstraints` 将副本分散到不同 AZ，同时评估跨 AZ 传输成本和复制延迟。
3. **资源隔离**：需要 Guaranteed QoS 时，每个容器的 CPU/内存 requests 和 limits 必须相等。这并不能消除 OOM、CPU throttling 或节点故障。应根据实测工作负载为 CPU limits、缓存、后台任务和查询内存预留量设置容量。
4. **实际执行过还原的备份**：启用 Operator 备份（例如 CloudNativePG 支持的 Barman Cloud 插件并备份至 S3）只是基本要求；定期演练还原才算真正具备恢复能力。

## 延伸阅读

- [将 ClickHouse 用作日志后端](../observability/logging/04-clickhouse.md)：从可观测性管道的角度介绍 ClickHouse
- [Kubernetes 存储](../core/04-storage.md) / [存储章节](../storage/README.md)
- [EKS 存储第 1 部分](../eks/04-eks-storage-part1.md)

## 参考资料

- [MongoDB Operator 迁移指南](https://github.com/mongodb/mongodb-kubernetes/blob/master/docs/migration/community-operator-migration.md)
- [CloudNativePG](https://cloudnative-pg.io/docs/)
- [ClickHouse Cloud](https://clickhouse.com/cloud)
- [Altinity ClickHouse Operator](https://github.com/Altinity/clickhouse-operator)
