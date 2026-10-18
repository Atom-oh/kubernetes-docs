# Pod 和工作负载测验

本测验将检验你对 Pod（Kubernetes 的基本执行单元）以及管理 Pod 的各种工作负载资源的理解。

## 选择题

1. Kubernetes 中最小的可部署计算单元是什么？
   - A) 容器
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>显示答案</summary>

**答案：B) Pod**

**解释：**
Pod 是 Kubernetes 中最小的可部署计算单元。Pod 是由一个或多个容器组成的组，这些容器共享存储和网络，并被一起调度。容器虽然是包含在 Pod 中的更小单元，但它们并不是 Kubernetes 直接管理的部署单元。
</details>

2. 以下哪项不是 Pod 的特征？
   - A) Pod 中的所有容器共享同一个 IP 地址
   - B) Pod 中的所有容器始终运行在同一个节点上
   - C) 一个 Pod 可以跨多个节点运行
   - D) Pod 有唯一的 IP 地址
   
<details>

<summary>显示答案</summary>

**答案：C) 一个 Pod 可以跨多个节点运行**

**解释：**
Pod 中的所有容器始终运行在同一个节点上。一个 Pod 无法跨多个节点运行。这是 Pod 的基本特征之一，因此 Pod 内的容器可以进行本地通信并共享卷。Pod 中的所有容器共享同一个网络命名空间，因此拥有相同的 IP 地址；而集群中的每个 Pod 都有唯一的 IP 地址。
</details>

3. 哪种多容器 Pod 模式通过辅助容器扩展主容器的功能？
   - A) Ambassador 模式
   - B) Sidecar 模式
   - C) Adapter 模式
   - D) Init 模式
   
<details>

<summary>显示答案</summary>

**答案：B) Sidecar 模式**

**解释：**
Sidecar 模式会添加辅助容器，以扩展主容器的功能。例如，可以将日志收集器、文件同步器和代理实现为 Sidecar 容器。Ambassador 模式会添加充当外部服务代理的容器，Adapter 模式会添加用于规范化主容器输出的容器，而 Init 模式会添加在主容器启动前运行的容器。
</details>

4. 哪种探针会检查容器是否已准备好处理请求，并在检查失败时将其从服务流量中移除？
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>显示答案</summary>

**答案：B) readinessProbe**

**解释：**
readinessProbe 会检查容器是否已准备好处理请求，并在检查失败时将其从服务流量中移除。livenessProbe 会检查容器是否存活，并在检查失败时重启容器。startupProbe 会检查容器中的应用程序是否已启动，并在检查成功之前禁用其他探针。Kubernetes 中不存在 healthProbe。
</details>

5. 以下哪项不是 ReplicaSet 的主要功能？
   - A) 维持指定数量的 Pod 副本
   - B) 在 Pod 故障或被删除时自动创建替代 Pod
   - C) 执行滚动更新
   - D) 通过标签选择器识别要管理的 Pod
   
<details>

<summary>显示答案</summary>

**答案：C) 执行滚动更新**

**解释：**
滚动更新是 Deployment 的主要功能，并非 ReplicaSet 直接支持的功能。ReplicaSet 的主要功能是维持指定数量的 Pod 副本、在 Pod 故障或被删除时自动创建替代 Pod，以及通过标签选择器识别要管理的 Pod。Deployment 通过管理 ReplicaSet 来提供滚动更新、回滚等功能。
</details>

6. 哪些不是内置的 Deployment 更新策略？（选择两项。）
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>显示答案</summary>

**答案：C) BlueGreen 和 D) Canary**

**解释：**
Kubernetes Deployment 默认提供两种更新策略：RollingUpdate 和 Recreate。BlueGreen 和 Canary 是部署模式，但并非 Deployment 直接提供的更新策略。可以使用 Service 和 Ingress 等其他 Kubernetes 资源，或 Argo Rollouts 等额外工具来实现这些模式。
</details>

7. 哪种工作负载资源适用于需要持久化状态的应用程序？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：C) StatefulSet**

**解释：**
StatefulSet 是一种适用于需要持久化状态的应用程序的工作负载资源。它会为每个 Pod 分配唯一标识，并提供稳定的网络标识和持久化存储。它适用于需要维护状态的应用程序，例如数据库、分布式系统和消息队列。Deployment 和 ReplicaSet 适用于无状态应用程序，而 DaemonSet 可确保每个节点上都运行一个 Pod 副本。
</details>

8. 哪种工作负载资源可确保在所有（或指定的）节点上都运行一个 Pod 副本？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：D) DaemonSet**

**解释：**
DaemonSet 可确保在所有（或指定的）节点上都运行一个 Pod 副本。向集群添加节点时，系统会自动添加 Pod；移除节点时，也会移除相应的 Pod。DaemonSet 主要用于运行后台服务，例如日志收集器、监控代理和网络插件。Deployment 和 ReplicaSet 会维持指定数量的 Pod 副本，而 StatefulSet 适用于需要持久化状态的应用程序。
</details>

9. 哪种工作负载资源用于运行一次性任务？
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：B) Job**

**解释：**
Job 是一种工作负载资源，它会创建一个或多个 Pod，并持续执行，直到指定数量的 Pod 成功终止。它用于运行一次性任务。Deployment 用于运行持续运行的应用程序，CronJob 按照计划定期运行 Job，而 DaemonSet 会在所有节点上运行 Pod 副本。
</details>

10. 哪种工作负载资源会按照计划定期运行任务？
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>显示答案</summary>

**答案：C) CronJob**

**解释：**
CronJob 是一种按照指定计划定期运行 Job 的工作负载资源。它的工作方式类似于 Linux cron 作业，可用于备份、生成报告和发送电子邮件等定期任务。Deployment 用于运行持续运行的应用程序，Job 用于运行一次性任务，而 StatefulSet 适用于需要持久化状态的应用程序。
</details>

## 简答题

11. 在 Pod 中的容器启动之前运行的特殊容器叫什么？

<details>

<summary>显示答案</summary>

**答案：Init Container**

**解释：**
Init Container 是在 Pod 中的应用容器启动之前运行的特殊容器。Init Container 会按照定义的顺序逐个运行，并且只有在前一个 Init Container 成功完成后，下一个才会启动。如果 Init Container 失败，它会根据 Pod 的重启策略重新启动。Init Container 主要用于在应用容器启动前进行初始化设置、依赖项检查和权限配置。
</details>

12. 如果镜像/容器没有覆盖默认停止信号，那么 Pod 终止时的默认停止信号是什么？

<details>

<summary>显示答案</summary>

**答案：SIGTERM**

**解释：**
Pod 终止时，kubelet 会先运行任何 preStop hook，然后要求运行时默认发送 SIGTERM。hook 会占用宽限期的一部分；镜像中的 STOPSIGNAL 或受支持的容器覆盖设置可以指定其他信号。这样应用程序就有时间正常关闭。如果容器在默认终止期限（30 秒）内未能终止，系统就会发送 SIGKILL 信号。应用程序收到 SIGTERM 信号后，可以完成正在进行的工作、关闭连接、清理资源并执行其他任务。
</details>

13. Deployment 管理的资源叫什么？

<details>

<summary>显示答案</summary>

**答案：ReplicaSet**

**解释：**
Deployment 管理 ReplicaSet。Deployment 创建 ReplicaSet，而 ReplicaSet 创建并管理 Pod。Deployment 通过 ReplicaSet 提供滚动更新、回滚、扩缩容等功能。部署应用程序的新版本时，Deployment 会创建新的 ReplicaSet，并逐步缩减旧 ReplicaSet 的规模。
</details>

14. StatefulSet 分配给 Pod 的唯一标识采用什么格式？（例如，StatefulSet 的名称为 'web'）

<details>

<summary>显示答案</summary>

**答案：\<StatefulSet name\>-\<ordinal index\>（例如，web-0、web-1、web-2）**

**解释：**
StatefulSet 会按照 `<StatefulSet name>-<ordinal index>` 格式为 Pod 分配唯一标识。例如，名为 `web` 的 StatefulSet 会创建 `web-0`、`web-1`、`web-2` 这样的 Pod。即使 Pod 被重新调度，该标识仍会保持不变，并用于提供稳定的网络标识和持久化存储。
</details>

15. CronJob 中哪种并发策略会在先前的 Job 仍在运行时跳过新 Job？

<details>

<summary>显示答案</summary>

**答案：Forbid**

**解释：**
CronJob 中的 `Forbid` 并发策略会在先前的 Job 仍在运行时跳过新 Job。CronJob 提供三种并发策略：`Allow`（允许多个 Job 同时运行，默认值）、`Forbid`（先前的 Job 仍在运行时跳过新 Job）和 `Replace`（如果先前的 Job 仍在运行，则用新 Job 替换它）。这些策略可以通过 `concurrencyPolicy` 字段设置。
</details>

## 实践题

16. 编写一个满足以下要求的多容器 Pod YAML 文件：
    - Pod 名称：web-app
    - 第一个容器：nginx Web 服务器（镜像：nginx:1.30.6）
    - 第二个容器：日志收集器（镜像：fluentd:v1.19-debian-1）
    - 使用 emptyDir 卷在两个容器之间共享日志目录
    - nginx 容器暴露端口 80
    - 日志卷在 nginx 容器中挂载到 /var/log/nginx，在 fluentd 容器中挂载到 /fluentd/log

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
      image: nginx:1.30.6
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

**解释：**
此 YAML 文件定义了一个多容器 Pod，其中包含 nginx Web 服务器和 fluentd 日志收集器。文件会创建一个名为 `log-volume` 的 emptyDir 卷，并将其挂载到 nginx 容器中的 `/var/log/nginx` 和 fluentd 容器中的 `/fluentd/log`。这会共享文件；要实际收集日志，还需要为 `/fluentd/log/*.log` 配置 Fluentd tail source 和输出配置。nginx 容器暴露端口 80。这是 Sidecar 模式的一个示例。
</details>

17. 编写一个满足以下要求的 Deployment YAML 文件：
    - 名称：nginx-deployment
    - 标签：app=nginx, tier=frontend
    - 副本数：3
    - 滚动更新策略：max surge 为 1，max unavailable 为 0
    - 容器镜像：nginx:1.30.6
    - 容器端口：80
    - 资源请求：CPU 100m，内存 128Mi
    - 资源限制：CPU 200m，内存 256Mi
    - 存活探针：HTTP GET /，初始延迟 30 秒，周期 10 秒
    - 就绪探针：HTTP GET /，初始延迟 5 秒，周期 5 秒

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
          image: nginx:1.30.6
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

**解释：**
此 YAML 文件定义了一个包含 3 个副本、使用 nginx:1.30.6 镜像的 Deployment。滚动更新策略配置为 max surge 1（超出期望数量时最多可创建的 Pod 数量）和 max unavailable 0（更新期间最多可处于不可用状态的 Pod 数量），从而实现无停机更新。每个容器都暴露端口 80，并设有资源约束：CPU 请求为 100m，内存请求为 128Mi，CPU 限制为 200m，内存限制为 256Mi。存活探针和就绪探针通过 HTTP GET 请求检查容器状态。
</details>

18. 编写一个满足以下要求的 CronJob YAML 文件：
    - 名称：database-backup
    - 计划：每天 UTC 时间凌晨 2 点运行（使用 cron 表达式和 timeZone）
    - 并发策略：Forbid
    - 成功 Job 历史记录上限：3
    - 失败 Job 历史记录上限：1
    - 容器镜像：postgres:14
    - 命令：pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - 环境变量：PGHOST=postgres-service，PGUSER 和 PGPASSWORD 从 postgres-secret 获取
    - 卷：将 backup-pvc 挂载到 /backup
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

**解释：**
此 YAML 文件定义了一个每天凌晨 2 点运行的数据库备份 CronJob。`concurrencyPolicy: Forbid` 会在先前的 Job 仍在运行时跳过新 Job。`successfulJobsHistoryLimit: 3` 和 `failedJobsHistoryLimit: 1` 分别将成功和失败 Job 的历史记录数量限制为 3 和 1。容器使用 postgres:14 镜像，并运行 pg_dump 命令备份数据库。环境变量 PGHOST 直接设置，而 PGUSER 和 PGPASSWORD 从 postgres-secret 中获取。backup-pvc 卷挂载到 /backup 目录，用于存储备份文件。重启策略设置为 OnFailure，因此 Job 失败时容器会重新启动。
</details>

## 进阶题

19. 说明 StatefulSet 对一个包含一个主节点和两个副本的 MySQL 集群负责提供哪些功能，哪些功能需要数据库 Operator 或复制控制器实现。为什么不能通过常规 Init Container 配置本地 MySQL 服务器？

<details>
<summary>显示答案</summary>

**答案：**

- StatefulSet 默认提供稳定的 Pod 名称、管理用的无头 Service、每个 Pod 各自的 PVC，以及有序扩缩容。它会使用相同的序号和存储替换故障 Pod，但前提是存储可用。
- 它不会复制数据库数据、配置复制、选举/提升主节点、隔离旧主节点或重定向数据库客户端。经过验证的数据库 Operator/运维手册必须实现这些行为、复制凭据、备份和恢复检查。
- 常规 Init Container 会在本地应用容器启动之前结束。尝试从 Init Container 建立本地 SQL 连接，无法配置尚未启动的 MySQL 服务器。复制设置必须在数据库生命周期中合适的阶段运行。
- 三个彼此独立的 MySQL Pod 并不是具备复制能力的高可用数据库。在多个副本间重复使用同一个服务器 ID，或将复制密码写入 ConfigMap，也是不正确的做法。
- 请参阅本章中的单实例 StatefulSet 示例，了解 Kubernetes 身份/存储配置；不要将其扩展到三个实例后就声称它具备复制或自动故障转移能力。

</details>

20. 比较各种工作负载资源（Deployment、StatefulSet、DaemonSet、Job、CronJob）的特征和用例，并为以下场景选择最合适的工作负载资源并说明原因：
    - Web 应用前端
    - 分布式数据库集群
    - 日志收集代理
    - 每日数据备份
    - 一次性数据迁移

<details>

<summary>显示答案</summary>

**答案：**

**工作负载资源对比**

| 工作负载资源 | 主要特征 | 用例 |
|--------------|---------|---------|
| **Deployment** | - 无状态应用程序<br>- 支持滚动更新<br>- 自动扩缩容<br>- 管理 ReplicaSet | - Web 服务器<br>- API 服务器<br>- 无状态微服务<br>- 前端应用程序 |
| **StatefulSet** | - 稳定的网络标识<br>- 持久化存储<br>- 按顺序部署和扩缩容<br>- 保证按顺序创建 Pod | - 数据库<br>- 分布式系统<br>- 消息队列<br>- 有状态应用程序 |
| **DaemonSet** | - 在所有节点上运行<br>- 添加节点时自动部署<br>- 移除节点时自动清理<br>- 可以选择节点 | - 日志收集器<br>- 监控代理<br>- 网络插件<br>- 存储守护进程 |
| **Job** | - 一次性任务<br>- 跟踪完成情况（可能失败）<br>- 可以并行执行<br>- 失败时重试 | - 批处理<br>- 数据迁移<br>- 计算任务<br>- 一次性管理任务 |
| **CronJob** | - 按计划执行<br>- 定期任务<br>- 并发策略<br>- 历史记录上限 | - 定期备份<br>- 数据同步<br>- 生成报告<br>- 清理任务 |

**各场景适用的工作负载资源**

1. **Web 应用前端**
  - **适用资源：Deployment**
  - **原因**：Web 应用前端通常是无状态应用程序。Deployment 可以通过滚动更新部署新版本而不中断服务，易于水平扩缩容，并能自动恢复。也可以与 HorizontalPodAutoscaler 搭配使用，根据流量自动扩缩容。

2. **分布式数据库集群**
  - **适用资源：StatefulSet**
  - **原因**：分布式数据库需要持久化状态，并且每个实例都需要唯一标识和持久化存储。StatefulSet 提供稳定的网络标识（`<StatefulSet name>-<ordinal index>`）和持久化存储，并支持按顺序部署和扩缩容；复制和一致性则必须由数据库实现。适用于 MySQL、PostgreSQL、MongoDB 和 Cassandra 等分布式数据库集群。

3. **日志收集代理**
  - **适用资源：DaemonSet**
  - **原因**：日志收集代理需要在集群的所有节点上运行。DaemonSet 可确保在所有（或指定的）节点上都运行一个 Pod 副本，并会在集群添加新节点时自动部署日志收集代理。适用于部署 Fluentd、Logstash 和 Filebeat 等日志收集代理。

4. **每日数据备份**
  - **适用资源：CronJob**
  - **原因**：每日数据备份是需要按照设定计划定期运行的任务。CronJob 可以使用 cron 表达式指定执行计划，并设置为每天在特定时间运行备份任务。还可以通过 `concurrencyPolicy` 定义先前的备份仍在运行时的行为，并限制 Job 历史记录；备份文件保留则需要单独的策略。

5. **一次性数据迁移**
  - **适用资源：Job**
  - **原因**：数据迁移是必须成功完成的一次性任务。Job 会持续执行，直到指定数量的 Pod 成功终止，并在失败时提供重试机制。此外，大规模数据迁移可以通过 `parallelism` 设置并行运行多个 Pod，从而加快处理速度。

**结论**

每种工作负载资源都是为特定用例设计的，因此应根据应用程序需求选择合适的资源。Deployment 适用于无状态应用程序，StatefulSet 适用于需要持久化状态的应用程序，DaemonSet 适用于必须在所有节点上运行的服务，Job 适用于一次性任务，而 CronJob 适用于定期任务。理解这些特征并选择适当的工作负载资源，有助于高效管理 Kubernetes 中的应用程序。
</details>

---

[返回学习资料](../../core/02-pods-and-workloads.md) | [下一个测验：Service 和网络](../core/03-services-networking-quiz.md)
