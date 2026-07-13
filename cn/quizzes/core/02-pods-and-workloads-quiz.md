# Pods and Workloads Quiz

本测验用于检验你对 Pod（容器组）、Kubernetes 的基本执行单元，以及管理它们的各种 workload resource（工作负载资源）的理解。

## Multiple Choice Questions

1. Kubernetes 中最小的可部署计算单元是什么？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>显示答案</summary>

**答案：B) Pod**

**解释：**
Pod 是 Kubernetes 中最小的可部署计算单元。Pod 是一个或多个 container 的组合，这些 container 共享存储和网络，并会被一起调度。虽然 container 是包含在 Pod 中的更小单元，但它们不是 Kubernetes 直接管理的部署单元。
</details>

2. 以下哪一项不是 Pod 的特征？
   - A) Pod 中的所有 container 共享同一个 IP 地址
   - B) Pod 中的所有 container 总是在同一个 node 上运行
   - C) Pod 可以跨多个 node 运行
   - D) Pod 拥有唯一的 IP 地址
   
<details>

<summary>显示答案</summary>

**答案：C) Pod 可以跨多个 node 运行**

**解释：**
Pod 中的所有 container 总是在同一个 node 上运行。Pod 不能跨多个 node 运行。这是 Pod 的基本特征之一，使 Pod 内的 container 能够在本地通信并共享 volume。Pod 中的所有 container 共享同一个 network namespace，因此具有相同的 IP 地址，并且每个 Pod 在 cluster 内都有唯一的 IP 地址。
</details>

3. 哪种 multi-container Pod pattern 会使用辅助 container 扩展主 container 的功能？
   - A) Ambassador pattern
   - B) Sidecar pattern
   - C) Adapter pattern
   - D) Init pattern
   
<details>

<summary>显示答案</summary>

**答案：B) Sidecar pattern**

**解释：**
sidecar pattern 会添加辅助 container 来扩展主 container 的功能。例如，日志收集器、文件同步器和代理都可以作为 sidecar container 实现。ambassador pattern 会添加充当外部服务代理的 container，adapter pattern 会添加用于标准化主 container 输出的 container，而 init pattern 会添加在主 container 启动前运行的 container。
</details>

4. 哪种 probe 会检查 container 是否已准备好处理请求，并在检查失败时将其从 service traffic 中移除？
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>显示答案</summary>

**答案：B) readinessProbe**

**解释：**
readinessProbe 会检查 container 是否已准备好处理请求，并在检查失败时将其从 service traffic 中移除。livenessProbe 会检查 container 是否存活，并在检查失败时重启它。startupProbe 会检查 container 内的 application 是否已经启动，并在成功前禁用其他 probe。Kubernetes 中不存在 healthProbe。
</details>

5. 以下哪一项不是 ReplicaSet 的主要功能？
   - A) 维持指定数量的 pod replicas
   - B) 当 pod 失败或被删除时自动创建替代 pod
   - C) 执行 rolling update
   - D) 通过 label selector 识别要管理的 pod
   
<details>

<summary>显示答案</summary>

**答案：C) 执行 rolling update**

**解释：**
Rolling update 是 Deployment 的主要功能，ReplicaSet 并不直接支持。ReplicaSet 的主要功能是维持指定数量的 pod replicas、当 pod 失败或被删除时自动创建替代 pod，以及通过 label selector 识别要管理的 pod。Deployment 通过管理 ReplicaSet 来提供 rolling update、rollback 和其他功能。
</details>

6. 以下哪一项不是 Deployment 的 update strategy？
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>显示答案</summary>

**答案：C) BlueGreen**

**解释：**
Kubernetes Deployment 默认提供两种 update strategy：RollingUpdate 和 Recreate。BlueGreen 和 Canary 是 deployment pattern，但并不是 Deployment 直接提供的 update strategy。这些 pattern 可以使用其他 Kubernetes 资源（如 Service 和 Ingress）实现，也可以使用 Argo Rollouts 等附加工具实现。
</details>

7. 哪种 workload resource 用于需要状态持久化的 application？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：C) StatefulSet**

**解释：**
StatefulSet 是用于需要状态持久化的 application 的 workload resource。它为每个 pod 分配唯一标识符，并提供稳定的网络标识符和持久化存储。它适用于需要保持状态的 application，例如 database、distributed system 和 message queue。Deployment 和 ReplicaSet 用于无状态 application，而 DaemonSet 会确保每个 node 上运行一个 pod 副本。
</details>

8. 哪种 workload resource 会确保在所有（或特定）node 上运行一个 pod 副本？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：D) DaemonSet**

**解释：**
DaemonSet 会确保在所有（或特定）node 上运行一个 pod 副本。当 node 加入 cluster 时，会自动添加该 pod；当 node 被移除时，该 pod 也会被移除。它主要用于运行后台服务，例如日志收集器、监控 agent 和网络 plugin。Deployment 和 ReplicaSet 会维持指定数量的 pod replicas，而 StatefulSet 用于需要状态持久化的 application。
</details>

9. 哪种 workload resource 用于运行一次性任务？
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>显示答案</summary>

**答案：B) Job**

**解释：**
Job 是一种 workload resource，会创建一个或多个 pod，并持续执行直到指定数量的 pod 成功终止。它用于运行一次性任务。Deployment 用于持续运行的 application，CronJob 会根据 schedule 周期性运行 job，而 DaemonSet 会在所有 node 上运行 pod 副本。
</details>

10. 哪种 workload resource 会根据 schedule 周期性运行任务？
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>显示答案</summary>

**答案：C) CronJob**

**解释：**
CronJob 是一种 workload resource，会根据指定 schedule 周期性运行 job。它的工作方式类似 Linux cron job，用于备份、报告生成和邮件发送等定期任务。Deployment 用于持续运行的 application，Job 运行一次性任务，而 StatefulSet 用于需要状态持久化的 application。
</details>

## Short Answer Questions

11. 在 pod 中的 container 启动前运行的特殊 container 名称是什么？

<details>

<summary>显示答案</summary>

**答案：Init Container**

**解释：**
Init Container 是在 pod 中的 app container 启动前运行的特殊 container。Init container 会按照定义的顺序一次运行一个，并且每个 init container 只有在前一个成功完成后才会启动。如果某个 init container 失败，它会根据 pod 的 restart policy 重新启动。它们主要用于 app container 启动前的 setup、dependency check 和 permission configuration。
</details>

12. 当 pod 被终止时，首先发送给 container 的信号是什么？

<details>

<summary>显示答案</summary>

**答案：SIGTERM**

**解释：**
当 pod 被终止时，kubelet 会首先向 container 发送 SIGTERM 信号。这为 application 优雅关闭提供了时间。如果 container 未在默认终止期限（30 秒）内终止，则会发送 SIGKILL 信号。当 application 收到 SIGTERM 信号时，它可以完成正在进行的工作、关闭连接、清理资源并执行其他任务。
</details>

13. Deployment 管理的 resource 名称是什么？

<details>

<summary>显示答案</summary>

**答案：ReplicaSet**

**解释：**
Deployment 管理 ReplicaSet。Deployment 创建 ReplicaSet，而 ReplicaSet 创建并管理 pod。Deployment 通过 ReplicaSet 提供 rolling update、rollback、scaling 和其他功能。当部署 application 的新版本时，Deployment 会创建新的 ReplicaSet，并逐步缩减之前的 ReplicaSet。
</details>

14. StatefulSet 中分配给 pod 的唯一标识符格式是什么？（例如，如果 StatefulSet 名称是 'web'）

<details>

<summary>显示答案</summary>

**答案：\<StatefulSet name\>-\<ordinal index\> (e.g., web-0, web-1, web-2)**

**解释：**
StatefulSet 会为 pod 分配格式为 `<StatefulSet name>-<ordinal index>` 的唯一标识符。例如，`web` StatefulSet 会创建类似 `web-0`、`web-1`、`web-2` 的 pod。即使 pod 被重新调度，该标识符也会保持不变，并用于提供稳定的网络标识符和持久化存储。
</details>

15. CronJob 中当之前的 job 仍在运行时跳过新 job 的 concurrency policy 是什么？

<details>

<summary>显示答案</summary>

**答案：Forbid**

**解释：**
CronJob 中的 `Forbid` concurrency policy 会在之前的 job 仍在运行时跳过新 job。CronJob 提供三种 concurrency policy：`Allow`（多个 job 可以同时运行，默认）、`Forbid`（如果之前的 job 仍在运行则跳过新 job）和 `Replace`（如果之前的 job 仍在运行，则用新 job 替换之前的 job）。这些 policy 可以通过 `concurrencyPolicy` 字段设置。
</details>

## Hands-on Questions

16. 编写一个满足以下要求的 multi-container pod YAML 文件：
    - Pod name: web-app
    - 第一个 container：nginx web server（image: nginx:1.21）
    - 第二个 container：log collector（image: fluentd:v1.14）
    - 用于在两个 container 之间共享日志目录的 emptyDir volume
    - nginx container 暴露端口 80
    - Log volume 挂载到 nginx container 中的 /var/log/nginx，以及 fluentd container 中的 /fluentd/log

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
      image: nginx:1.21
      ports:
        - containerPort: 80
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/nginx
    - name: log-collector
      image: fluentd:v1.14
      volumeMounts:
        - name: log-volume
          mountPath: /fluentd/log
  volumes:
    - name: log-volume
      emptyDir: {}
```

**解释：**
此 YAML 文件定义了一个 multi-container pod，其中包含一个 nginx web server 和一个 fluentd log collector。它创建名为 `log-volume` 的 emptyDir volume，并将其挂载到 nginx container 中的 `/var/log/nginx` 和 fluentd container 中的 `/fluentd/log`。这使 fluentd 能够收集 nginx 生成的日志。nginx container 暴露端口 80。这是 sidecar pattern 的示例。
</details>

17. 编写一个满足以下要求的 Deployment YAML 文件：
    - Name: nginx-deployment
    - Labels: app=nginx, tier=frontend
    - Replica count: 3
    - Rolling update strategy：max surge 1，max unavailable 0
    - Container image: nginx:1.21
    - Container port: 80
    - Resource requests：CPU 100m，memory 128Mi
    - Resource limits：CPU 200m，memory 256Mi
    - Liveness probe：HTTP GET /，initial delay 30 seconds，period 10 seconds
    - Readiness probe：HTTP GET /，initial delay 5 seconds，period 5 seconds

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
          image: nginx:1.21
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
此 YAML 文件定义了一个使用 nginx:1.21 image、包含 3 个 replica 的 Deployment。rolling update strategy 配置为 max surge 1（可超出期望数量创建的 pod 最大数量）和 max unavailable 0（update 期间可不可用的 pod 最大数量），从而实现无 downtime 更新。每个 container 暴露端口 80，并具有 resource constraint：CPU request 100m、memory request 128Mi、CPU limit 200m 和 memory limit 256Mi。Liveness 和 readiness probe 通过 HTTP GET request 验证 container 状态。
</details>

18. 编写一个满足以下要求的 CronJob YAML 文件：
    - Name: database-backup
    - Schedule：每天凌晨 2 点运行（使用 cron expression）
    - Concurrency policy: Forbid
    - Successful job history limit: 3
    - Failed job history limit: 1
    - Container image: postgres:14
    - Command: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - Environment variables：PGHOST=postgres-service，PGUSER 和 PGPASSWORD 来自 postgres-secret
    - Volume：将 backup-pvc 挂载到 /backup
    - Restart policy: OnFailure

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
此 YAML 文件定义了一个每天凌晨 2 点运行的 database backup CronJob。`concurrencyPolicy: Forbid` 会在之前的 job 仍在运行时跳过新 job。`successfulJobsHistoryLimit: 3` 和 `failedJobsHistoryLimit: 1` 分别将成功和失败 job 的历史记录限制为 3 和 1。container 使用 postgres:14 image，并运行 pg_dump command 来备份 database。环境变量 PGHOST 直接设置，而 PGUSER 和 PGPASSWORD 从 postgres-secret 中获取。backup-pvc volume 挂载到 /backup 目录以存储备份文件。restart policy 设置为 OnFailure，因此如果 job 失败，container 会被重新启动。
</details>

## Advanced Questions

19. 说明面向高可用有状态 application 的 StatefulSet 设计，并编写一个满足以下要求的 MySQL replication cluster 的 StatefulSet YAML：
    - 由 1 个 master 和 2 个 slave 组成
    - 提供稳定的网络标识符
    - 为每个 instance 提供持久化存储
    - 顺序部署和扩缩容
    - master node 发生故障时具备自动恢复机制

<details>

<summary>显示答案</summary>

**答案：**

**高可用有状态 Application 的设计原则**

以下原则适用于为有状态 application 设计高可用：

1. **稳定的网络标识符**：每个 instance 即使在重启后也保持相同的网络标识符
2. **持久化存储**：即使 instance 被重新调度，也能访问相同的数据
3. **顺序部署和扩缩容**：按顺序创建和删除 instance，以保证数据一致性
4. **自动恢复机制**：故障发生时自动恢复的机制
5. **备份和恢复**：按需执行定期备份和恢复流程

**MySQL Replication Cluster 的 StatefulSet YAML**

```yaml
# Headless service definition
apiVersion: v1
kind: Service
metadata:
  name: mysql
  labels:
    app: mysql
spec:
  ports:
    - port: 3306
      name: mysql
  clusterIP: None
  selector:
    app: mysql
---
# ConfigMap for configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: mysql-config
data:
  master.cnf: |
    [mysqld]
    log-bin=mysql-bin
    binlog-format=ROW
    server-id=1
  slave.cnf: |
    [mysqld]
    server-id=100
    log_bin=mysql-bin
    relay_log=mysql-relay-bin
    read_only=1
  init.sql: |
    CREATE DATABASE IF NOT EXISTS mydb;
    GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%' IDENTIFIED BY 'replpass';
    FLUSH PRIVILEGES;
---
# MySQL StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 3
  updateStrategy:
    type: RollingUpdate
  podManagementPolicy: OrderedReady
  template:
    metadata:
      labels:
        app: mysql
    spec:
      initContainers:
        - name: init-mysql
          image: mysql:8.0
          command:
            - bash
            - "-c"
            - |
              set -ex
              # Configure as master or slave based on pod index
              [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
              ordinal=${BASH_REMATCH[1]}
              if [[ $ordinal -eq 0 ]]; then
                # Master configuration
                cp /mnt/config-map/master.cnf /etc/mysql/conf.d/
                # Copy initialization SQL script
                cp /mnt/config-map/init.sql /docker-entrypoint-initdb.d/
              else
                # Slave configuration
                cp /mnt/config-map/slave.cnf /etc/mysql/conf.d/
              fi
          volumeMounts:
            - name: conf
              mountPath: /etc/mysql/conf.d
            - name: config-map
              mountPath: /mnt/config-map
            - name: initdb
              mountPath: /docker-entrypoint-initdb.d
        - name: clone-mysql
          image: mysql:8.0
          command:
            - bash
            - "-c"
            - |
              set -ex
              # Only slaves set up replication
              [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
              ordinal=${BASH_REMATCH[1]}
              if [[ $ordinal -eq 0 ]]; then
                # Master does nothing
                exit 0
              fi

              # Wait for master to be ready
              until mysql -h mysql-0.mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SELECT 1"; do
                echo "Waiting for mysql-0.mysql to be ready..."
                sleep 2
              done

              # Check master status
              master_status=$(mysql -h mysql-0.mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SHOW MASTER STATUS\G")
              file=$(echo "$master_status" | grep File | awk '{print $2}')
              position=$(echo "$master_status" | grep Position | awk '{print $2}')

              # Configure slave
              mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "CHANGE MASTER TO MASTER_HOST='mysql-0.mysql', MASTER_USER='repl', MASTER_PASSWORD='replpass', MASTER_LOG_FILE='$file', MASTER_LOG_POS=$position; START SLAVE;"
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
      containers:
        - name: mysql
          image: mysql:8.0
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
          ports:
            - name: mysql
              containerPort: 3306
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
            - name: conf
              mountPath: /etc/mysql/conf.d
            - name: initdb
              mountPath: /docker-entrypoint-initdb.d
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 1
              memory: 2Gi
          livenessProbe:
            exec:
              command: ["mysqladmin", "ping", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
          readinessProbe:
            exec:
              command: ["mysql", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}", "-e", "SELECT 1"]
            initialDelaySeconds: 5
            periodSeconds: 2
            timeoutSeconds: 1
      volumes:
        - name: conf
          emptyDir: {}
        - name: config-map
          configMap:
            name: mysql-config
        - name: initdb
          emptyDir: {}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "standard"
        resources:
          requests:
            storage: 10Gi
```

**解释：**

此 YAML 文件定义了一个由 1 个 master 和 2 个 slave 组成的 MySQL replication cluster 的 StatefulSet。

1. **Headless service**：`mysql` service 配置为 `clusterIP: None`，这会为每个 pod 创建 DNS 记录。它提供类似 `mysql-0.mysql`、`mysql-1.mysql`、`mysql-2.mysql` 的稳定网络标识符。

2. **ConfigMap**：定义用于 MySQL 配置的 ConfigMap。包含 master 和 slave node 的独立配置以及初始化 SQL script。

3. **StatefulSet**：定义具有 3 个 replica 的 MySQL StatefulSet。
  - `podManagementPolicy: OrderedReady`：按顺序创建和删除 pod。
  - `updateStrategy: RollingUpdate`：使用 rolling update strategy。
  - Init container：根据 pod index 应用 master 或 slave 配置，slave node 从 master node 设置 replication。
  - 持久化存储：通过 `volumeClaimTemplates` 为每个 pod 创建 persistent volume claim。
  - Resource request 和 limit：为每个 MySQL instance 设置 resource request 和 limit。
  - Liveness 和 readiness probe：验证 MySQL instance 的状态。

4. **自动恢复机制**：
  - 当 pod 失败时，StatefulSet 会自动创建新的 pod。
  - 新 pod 使用相同的网络标识符和持久化存储。
  - Slave node 从 master node 设置 replication，以保持数据一致性。

此设计提供了高可用 MySQL cluster，并且可以实现一种机制，在 master node 失败时将某个 slave node 提升为新的 master（此示例不包含自动提升机制，该机制通常通过 MySQL Operator 或附加 controller 实现）。
</details>

20. 比较各种 workload resource（Deployment、StatefulSet、DaemonSet、Job、CronJob）的特征和 use case，并为以下场景选择最合适的 workload resource 并说明原因：
    - Web 应用前端
    - 分布式 database cluster
    - 日志收集 agent
    - 每日 data backup
    - 一次性 data migration

<details>

<summary>显示答案</summary>

**答案：**

**Workload Resource 对比**

| Workload Resource | Key Characteristics | Use Cases |
|--------------|---------|---------|
| **Deployment** | - Stateless applications<br>- Rolling update support<br>- Auto scaling<br>- ReplicaSet management | - Web servers<br>- API servers<br>- Stateless microservices<br>- Frontend applications |
| **StatefulSet** | - Stable network identifiers<br>- Persistent storage<br>- Sequential deployment and scaling<br>- Ordered pod creation guaranteed | - Databases<br>- Distributed systems<br>- Message queues<br>- Stateful applications |
| **DaemonSet** | - Runs on all nodes<br>- Auto deployment when nodes are added<br>- Auto cleanup when nodes are removed<br>- Node selection possible | - Log collectors<br>- Monitoring agents<br>- Network plugins<br>- Storage daemons |
| **Job** | - One-time tasks<br>- Completion guarantee<br>- Parallel execution possible<br>- Retry on failure | - Batch processing<br>- Data migration<br>- Computation tasks<br>- One-time management tasks |
| **CronJob** | - Schedule-based execution<br>- Periodic tasks<br>- Concurrency policy<br>- History limits | - Scheduled backups<br>- Data synchronization<br>- Report generation<br>- Cleanup tasks |

**按场景选择合适的 Workload Resource**

1. **Web 应用前端**
  - **合适的 resource：Deployment**
  - **原因**：Web 应用前端通常是无状态 application。Deployment 可以通过 rolling update 在无 downtime 的情况下部署新版本，易于水平扩展，并提供自动恢复。它们还可以与 HorizontalPodAutoscaler 配合使用，根据 traffic 自动扩缩容。

2. **分布式 Database Cluster**
  - **合适的 resource：StatefulSet**
  - **原因**：分布式 database 需要状态持久化，并且每个 instance 都需要唯一标识符和持久化存储。StatefulSet 提供稳定的网络标识符（`<pod name>-<ordinal index>`）和持久化存储，并可以通过顺序部署和扩缩容维护数据一致性。适用于 MySQL、PostgreSQL、MongoDB 和 Cassandra 等 distributed database cluster。

3. **日志收集 Agent**
  - **合适的 resource：DaemonSet**
  - **原因**：日志收集 agent 需要在 cluster 中的所有 node 上运行。DaemonSet 确保在所有（或特定）node 上运行一个 pod 副本，并在新 node 添加到 cluster 时自动部署日志收集 agent。适用于部署 Fluentd、Logstash 和 Filebeat 等日志收集 agent。

4. **每日 Data Backup**
  - **合适的 resource：CronJob**
  - **原因**：每日 data backup 是需要按照固定 schedule 周期性运行的任务。CronJob 可以使用 cron expression 指定执行 schedule，并可以设置为每天在特定时间运行 backup task。它们还可以通过 `concurrencyPolicy` 定义之前的 backup 仍在运行时的行为，并限制 backup history。

5. **一次性 Data Migration**
  - **合适的 resource：Job**
  - **原因**：Data migration 是必须成功完成的一次性任务。Job 会持续执行，直到指定数量的 pod 成功终止，并在失败时提供 retry 机制。此外，大规模 data migration 可以通过 `parallelism` 设置并行运行多个 pod，从而更快完成处理。

**结论**

每种 workload resource 都是为特定 use case 设计的，重要的是根据 application requirements 选择合适的 resource。Deployment 适用于无状态 application，StatefulSet 适用于需要状态持久化的 application，DaemonSet 适用于必须在所有 node 上运行的 service，Job 适用于一次性任务，CronJob 适用于周期性任务。理解这些特征并选择合适的 workload resource，可以在 Kubernetes 中实现高效的 application management。
</details>

---

[返回学习资料](../../core/02-pods-and-workloads.md) | [下一个测验：Services and Networking](../core/03-services-networking-quiz.md)
