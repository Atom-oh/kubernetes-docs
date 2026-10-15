# Pods 和工作负载测验

本测验用于测试你对 Pod（Kubernetes 的基本执行单元）以及管理 Pod 的各种工作负载资源的理解。

## 选择题

1. Kubernetes 中最小的可部署计算单元是什么？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>显示答案</summary>

**答案：B) Pod**

**说明：**
Pod 是 Kubernetes 中最小的可部署计算单元。Pod 是由一个或多个共享存储和网络、并被共同调度的 Container 组成的组。尽管 Container 是包含在 Pod 中的更小单元，但它们并非由 Kubernetes 直接管理的部署单元。
</details>

2. 以下哪项不是 Pod 的特征？
   - A) Pod 中的所有 Container 共享相同的 IP 地址
   - B) Pod 中的所有 Container 始终在同一 Node 上运行
   - C) 一个 Pod 可以跨多个 Node 运行
   - D) Pod 具有唯一的 IP 地址
   
<details>

<summary>显示答案</summary>

**答案：C) 一个 Pod 可以跨多个 Node 运行**

**说明：**
Pod 中的所有 Container 始终在同一 Node 上运行。一个 Pod 不能跨多个 Node 运行。这是 Pod 的基本特征之一，使 Pod 内的 Container 能够进行本地通信并共享 Volume。Pod 中的所有 Container 共享相同的网络命名空间，因此具有相同的 IP 地址，并且每个 Pod 在集群中都有唯一的 IP 地址。
</details>

3. 使用辅助 Container 扩展主 Container 功能的多 Container Pod 模式是什么？
   - A) Ambassador pattern
   - B) Sidecar pattern
   - C) Adapter pattern
   - D) Init pattern
   
<details>

<summary>显示答案</summary>

**答案：B) Sidecar pattern**

**说明：**
Sidecar 模式会添加扩展主 Container 功能的辅助 Container。例如，日志收集器、文件同步器和代理可以实现为 Sidecar Container。Ambassador 模式添加充当外部服务代理的 Container，Adapter 模式添加用于标准化主 Container 输出的 Container，而 Init 模式添加在主 Container 启动之前运行的 Container。
</details>

4. 哪种 Probe 用于检查 Container 是否已准备好处理请求，并在失败时将其从 Service 流量中移除？
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>显示答案</summary>

**答案：B) readinessProbe**

**说明：**
readinessProbe 检查 Container 是否已准备好处理请求，并在失败时将其从 Service 流量中移除。livenessProbe 检查 Container 是否存活，并在失败时重启它。startupProbe 检查 Container 内的应用程序是否已启动，并在其成功前禁用其他 Probe。Kubernetes 中不存在 healthProbe。
</details>

5. 以下哪项不是 ReplicaSet 的主要功能？
   - A) 维持指定数量的 Pod 副本
   - B) 当 Pod 失败或被删除时自动创建替代 Pod
   - C) 执行滚动更新
   - D) 通过标签选择器识别要管理的 Pod
   
<details>

<summary>显示答案</summary>

**答案：C) 执行滚动更新**

**说明：**
滚动更新是 Deployment 的主要功能，而非 ReplicaSet 直接支持的功能。ReplicaSet 的主要功能是维持指定数量的 Pod 副本、当 Pod 失败或被删除时自动创建替代 Pod，以及通过标签选择器识别要管理的 Pod。Deployment 管理 ReplicaSet，以提供滚动更新、回滚和其他功能。
</details>

6. 以下哪些不是内置的 Deployment 更新策略？（选择两项。）
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>显示答案</summary>

**答案：C) BlueGreen 和 D) Canary**

**说明：**
Kubernetes Deployment 默认提供两种更新策略：RollingUpdate 和 Recreate。BlueGreen 和 Canary 是部署模式，但并不直接作为 Deployment 更新策略提供。这些模式可以使用 Service 和 Ingress 等其他 Kubernetes 资源，或者使用 Argo Rollouts 等附加工具来实现。
</details>

7. 哪种工作负载资源适用于需要状态持久化的应用程序？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：C) StatefulSet**

**说明：**
StatefulSet 是适用于需要状态持久化的应用程序的工作负载资源。它为每个 Pod 分配唯一标识符，并提供稳定的网络标识符和持久化存储。它适合需要维持状态的应用程序，例如数据库、分布式系统和消息队列。Deployment 和 ReplicaSet 适用于无状态应用程序，而 DaemonSet 确保 Pod 的一个副本在所有 Node 上运行。
</details>

8. 哪种工作负载资源可确保 Pod 的一个副本在所有（或特定）Node 上运行？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：D) DaemonSet**

**说明：**
DaemonSet 确保 Pod 的一个副本在所有（或特定）Node 上运行。当 Node 添加到集群时，Pod 会自动添加；当 Node 被移除时，Pod 也会被移除。它主要用于运行日志收集器、监控 Agent 和网络插件等后台服务。Deployment 和 ReplicaSet 维持指定数量的 Pod 副本，而 StatefulSet 适用于需要状态持久化的应用程序。
</details>

9. 哪种工作负载资源适用于运行一次性任务？
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：B) Job**

**说明：**
Job 是一种工作负载资源，会创建一个或多个 Pod，并持续执行，直到指定数量的 Pod 成功终止。它用于运行一次性任务。Deployment 适用于持续运行的应用程序，CronJob 根据计划定期运行 Job，而 DaemonSet 在所有 Node 上运行 Pod 的副本。
</details>

10. 哪种工作负载资源会根据计划定期运行任务？
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>显示答案</summary>

**答案：C) CronJob**

**说明：**
CronJob 是一种工作负载资源，会根据指定计划定期运行 Job。它的工作方式类似于 Linux cron job，用于备份、生成报告和发送电子邮件等定期任务。Deployment 适用于持续运行的应用程序，Job 运行一次性任务，而 StatefulSet 适用于需要状态持久化的应用程序。
</details>

## 简答题

11. 在 Pod 中的 Container 启动之前运行的特殊 Container 名称是什么？

<details>

<summary>显示答案</summary>

**答案：Init Container**

**说明：**
Init Container 是在 Pod 中的应用 Container 启动之前运行的特殊 Container。Init Container 按定义的顺序逐个运行，且每个 Init Container 只有在前一个成功完成后才会启动。如果 Init Container 失败，则会根据 Pod 的重启策略重启。它们主要用于应用 Container 启动前的设置、依赖项检查和权限配置。
</details>

12. 当 Pod 终止时，如果 image/Container 未对其进行覆盖，默认的停止信号是什么？

<details>

<summary>显示答案</summary>

**答案：SIGTERM**

**说明：**
当 Pod 终止时，kubelet 会运行所有 preStop hook，然后要求运行时默认发送 SIGTERM。该 hook 会消耗部分宽限期；image STOPSIGNAL 或受支持的 Container 覆盖设置可以选择不同的信号。这为应用程序优雅关闭提供了时间。如果 Container 未在默认终止期限（30 秒）内终止，则会发送 SIGKILL 信号。当应用程序接收到 SIGTERM 信号时，可以完成进行中的工作、关闭连接、清理资源以及执行其他任务。
</details>

13. Deployment 管理的资源名称是什么？

<details>

<summary>显示答案</summary>

**答案：ReplicaSet**

**说明：**
Deployment 管理 ReplicaSet。Deployment 创建 ReplicaSet，而 ReplicaSet 创建和管理 Pod。Deployment 通过 ReplicaSet 提供滚动更新、回滚、扩缩容和其他功能。部署应用程序的新版本时，Deployment 会创建新的 ReplicaSet，并逐步缩减之前的 ReplicaSet。
</details>

14. StatefulSet 中分配给 Pod 的唯一标识符格式是什么？（例如，如果 StatefulSet 名称为 'web'）

<details>

<summary>显示答案</summary>

**答案：\<StatefulSet name\>-\<ordinal index\>（例如，web-0、web-1、web-2）**

**说明：**
StatefulSet 会以 `<StatefulSet name>-<ordinal index>` 格式为 Pod 分配唯一标识符。例如，`web` StatefulSet 会创建 `web-0`、`web-1`、`web-2` 等 Pod。即使 Pod 被重新调度，此标识符仍会保留，并用于提供稳定的网络标识符和持久化存储。
</details>

15. 当之前的 Job 仍在运行时，CronJob 中会跳过新 Job 的并发策略是什么？

<details>

<summary>显示答案</summary>

**答案：Forbid**

**说明：**
CronJob 中的 `Forbid` 并发策略会在之前的 Job 仍在运行时跳过新 Job。CronJob 提供三种并发策略：`Allow`（多个 Job 可以同时运行，默认值）、`Forbid`（如果之前的 Job 仍在运行则跳过新 Job）和 `Replace`（如果之前的 Job 仍在运行则使用新 Job 替换它）。这些策略可以通过 `concurrencyPolicy` 字段设置。
</details>

## 实践题

16. 编写一个满足以下要求的多 Container Pod YAML 文件：
    - Pod 名称：web-app
    - 第一个 Container：nginx Web 服务器（image：nginx:1.30.4）
    - 第二个 Container：日志收集器（image：fluentd:v1.19-debian-1）
    - 使用 emptyDir Volume 在两个 Container 之间共享日志目录
    - nginx Container 暴露端口 80
    - 日志 Volume 在 nginx Container 中挂载到 /var/log/nginx，在 fluentd Container 中挂载到 /fluentd/log

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
spec:
  containers:
    - name: nginx
      image: nginx:1.30.4
      ports:
        - containerPort: 80
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/nginx
    - name: log-collector
      image: fluentd:v1.19-debian-1
      volumeMounts:
        - name: log-volume
          mountPath: /fluentd/log
  volumes:
    - name: log-volume
      emptyDir: {}
```

**说明：**
此 YAML 文件定义了一个多 Container Pod，其中包含 nginx Web 服务器和 fluentd 日志收集器。它创建了名为 `log-volume` 的 emptyDir Volume，并将其在 nginx Container 中挂载到 `/var/log/nginx`，在 fluentd Container 中挂载到 `/fluentd/log`。这会共享文件；实际收集还需要为 `/fluentd/log/*.log` 配置 Fluentd tail source 和输出配置。nginx Container 暴露端口 80。这是 Sidecar 模式的示例。
</details>

17. 编写一个满足以下要求的 Deployment YAML 文件：
    - 名称：nginx-deployment
    - 标签：app=nginx，tier=frontend
    - 副本数：3
    - 滚动更新策略：最大激增数为 1，最大不可用数为 0
    - Container image：nginx:1.30.4
    - Container 端口：80
    - 资源请求：CPU 100m，内存 128Mi
    - 资源限制：CPU 200m，内存 256Mi
    - 存活 Probe：HTTP GET /，初始延迟 30 秒，周期 10 秒
    - 就绪 Probe：HTTP GET /，初始延迟 5 秒，周期 5 秒

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: nginx
        tier: frontend
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.4
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
```

**说明：**
此 YAML 文件定义了一个使用 nginx:1.30.4 image、具有 3 个副本的 Deployment。滚动更新策略配置为最大激增数 1（可在所需数量之外创建的 Pod 最大数量）和最大不可用数 0（更新期间不可用 Pod 的最大数量），从而实现零停机更新。每个 Container 都暴露端口 80，并具有 CPU 请求 100m、内存请求 128Mi、CPU 限制 200m 和内存限制 256Mi 的资源约束。存活和就绪 Probe 通过 HTTP GET 请求验证 Container 状态。
</details>

18. 编写一个满足以下要求的 CronJob YAML 文件：
    - 名称：database-backup
    - 计划：每天 UTC 时间凌晨 2 点运行（使用 cron 表达式和 timeZone）
    - 并发策略：Forbid
    - 成功 Job 历史记录限制：3
    - 失败 Job 历史记录限制：1
    - Container image：postgres:14
    - 命令：pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - 环境变量：PGHOST=postgres-service，PGUSER 和 PGPASSWORD 来自 postgres-secret
    - Volume：将 backup-pvc 挂载到 /backup
    - 重启策略：OnFailure

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:14
              env:
                - name: PGHOST
                  value: postgres-service
                - name: PGUSER
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: username
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: password
              command:
                - /bin/sh
                - -c
                - pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          restartPolicy: OnFailure
          volumes:
            - name: backup-volume
              persistentVolumeClaim:
                claimName: backup-pvc
```

**说明：**
此 YAML 文件定义了一个每天凌晨 2 点运行的数据库备份 CronJob。`concurrencyPolicy: Forbid` 会在之前的 Job 仍在运行时跳过新 Job。`successfulJobsHistoryLimit: 3` 和 `failedJobsHistoryLimit: 1` 分别将成功和失败 Job 的历史记录限制为 3 和 1。Container 使用 postgres:14 image 并运行 pg_dump 命令来备份数据库。环境变量 PGHOST 直接设置，而 PGUSER 和 PGPASSWORD 从 postgres-secret 获取。backup-pvc Volume 挂载到 /backup 目录以存储备份文件。重启策略设置为 OnFailure，因此如果 Job 失败，Container 会重启。
</details>

## 高级题

19. 说明 StatefulSet 为具有一个主节点和两个副本的 MySQL 集群提供哪些职责，以及哪些职责需要数据库 Operator 或复制控制器。为什么不能使用常规 Init Container 配置本地 MySQL server？

<details>
<summary>显示答案</summary>

**答案：**

- StatefulSet 默认提供稳定的 Pod 名称、管理用 Headless Service、每个 Pod 的 PVC 以及有序扩缩容。它会使用相同的序数和存储替换失败的 Pod，但受限于存储可用性。
- 它不会复制数据库数据、配置复制、选举/提升主节点、隔离旧主节点或重定向数据库客户端。经过测试的数据库 Operator/runbook 必须实现这些行为、复制凭据、备份和还原检查。
- 常规 Init Container 会在本地应用 Container 启动之前完成。尝试从 Init Container 建立本地 SQL 连接无法配置尚未启动的 MySQL server。复制设置必须在适当的数据库生命周期阶段运行。
- 三个彼此独立的 MySQL Pod 并不是已复制的 HA 数据库。跨副本重用相同的 server ID，或在 ConfigMap 中嵌入复制密码，也是不正确的。
- 有关 Kubernetes 身份/存储连接，请参阅本章的单实例 StatefulSet 示例；不要将其扩展到三个副本后便声称它具有复制或自动故障转移能力。

</details>

20. 比较各种工作负载资源（Deployment、StatefulSet、DaemonSet、Job、CronJob）的特征和使用场景，并为以下场景选择最合适的工作负载资源并说明原因：
    - Web 应用程序前端
    - 分布式数据库集群
    - 日志收集 Agent
    - 每日数据备份
    - 一次性数据迁移

<details>

<summary>显示答案</summary>

**答案：**

**工作负载资源对比**

| 工作负载资源 | 关键特征 | 使用场景 |
|--------------|---------|---------|
| **Deployment** | - 无状态应用程序<br>- 支持滚动更新<br>- 自动扩缩容<br>- ReplicaSet 管理 | - Web 服务器<br>- API 服务器<br>- 无状态微服务<br>- 前端应用程序 |
| **StatefulSet** | - 稳定的网络标识符<br>- 持久化存储<br>- 顺序部署和扩缩容<br>- 保证有序创建 Pod | - 数据库<br>- 分布式系统<br>- 消息队列<br>- 有状态应用程序 |
| **DaemonSet** | - 在所有 Node 上运行<br>- 添加 Node 时自动部署<br>- 移除 Node 时自动清理<br>- 可选择 Node | - 日志收集器<br>- 监控 Agent<br>- 网络插件<br>- 存储守护进程 |
| **Job** | - 一次性任务<br>- 完成情况跟踪（可能失败）<br>- 可并行执行<br>- 失败时重试 | - 批处理<br>- 数据迁移<br>- 计算任务<br>- 一次性管理任务 |
| **CronJob** | - 基于计划执行<br>- 定期任务<br>- 并发策略<br>- 历史记录限制 | - 定期备份<br>- 数据同步<br>- 生成报告<br>- 清理任务 |

**按场景选择合适的工作负载资源**

1. **Web 应用程序前端**
  - **合适的资源：Deployment**
  - **原因**：Web 应用程序前端通常是无状态应用程序。Deployment 可以通过滚动更新无停机地部署新版本，易于水平扩缩容，并提供自动恢复。它们还可以与 HorizontalPodAutoscaler 配合使用，以根据流量自动扩缩容。

2. **分布式数据库集群**
  - **合适的资源：StatefulSet**
  - **原因**：分布式数据库需要状态持久化，并且每个实例都需要唯一标识符和持久化存储。StatefulSet 提供稳定的网络标识符（`<StatefulSet name>-<ordinal index>`）和持久化存储，并支持有序部署和扩缩容；数据库必须自行实现复制和一致性。适用于 MySQL、PostgreSQL、MongoDB 和 Cassandra 等分布式数据库集群。

3. **日志收集 Agent**
  - **合适的资源：DaemonSet**
  - **原因**：日志收集 Agent 需要在集群中的所有 Node 上运行。DaemonSet 确保 Pod 的一个副本在所有（或特定）Node 上运行，并在新 Node 添加到集群时自动部署日志收集 Agent。适合部署 Fluentd、Logstash 和 Filebeat 等日志收集 Agent。

4. **每日数据备份**
  - **合适的资源：CronJob**
  - **原因**：每日数据备份是一项需要按照设定计划定期运行的任务。CronJob 可以使用 cron 表达式指定执行计划，并可设置为每天在特定时间运行备份任务。它们还可以通过 `concurrencyPolicy` 定义之前的备份仍在运行时的行为，并可限制 Job 历史记录；备份文件保留需要单独的策略。

5. **一次性数据迁移**
  - **合适的资源：Job**
  - **原因**：数据迁移是必须成功完成的一次性任务。Job 会持续执行，直到指定数量的 Pod 成功终止，并提供失败重试机制。此外，大型数据迁移可以通过 `parallelism` 设置并行运行多个 Pod，以更快地完成处理。

**结论**

每种工作负载资源都为特定使用场景而设计，根据应用程序要求选择合适的资源非常重要。Deployment 适用于无状态应用程序，StatefulSet 适用于需要状态持久化的应用程序，DaemonSet 适用于必须在所有 Node 上运行的服务，Job 适用于一次性任务，而 CronJob 适用于定期任务。理解这些特征并选择合适的工作负载资源，可以在 Kubernetes 中实现高效的应用程序管理。
</details>

---

[返回学习材料](../../core/02-pods-and-workloads.md) | [下一份测验：Service 和网络](../core/03-services-networking-quiz.md)
