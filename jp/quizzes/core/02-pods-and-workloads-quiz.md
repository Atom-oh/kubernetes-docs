# Pods and Workloads Quiz

このクイズでは、Kubernetes の基本実行単位である Pod と、それらを管理するさまざまな workload resources についての理解を確認します。

## Multiple Choice Questions

1. Kubernetes でデプロイ可能な最小の computing unit は何ですか？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>答えを表示</summary>

**解答: B) Pod**

**解説:**
Pod は Kubernetes でデプロイ可能な最小の computing unit です。Pod は、storage と network を共有し、まとめてスケジュールされる 1 つ以上の containers のグループです。Containers は Pod 内に含まれるより小さな単位ですが、Kubernetes によって直接管理される deployment unit ではありません。
</details>

2. 次のうち、Pod の特徴ではないものはどれですか？
   - A) Pod 内のすべての containers は同じ IP address を共有する
   - B) Pod 内のすべての containers は常に同じ node 上で実行される
   - C) Pod は複数の nodes にまたがって実行できる
   - D) Pod は一意の IP address を持つ
   
<details>

<summary>答えを表示</summary>

**解答: C) Pod は複数の nodes にまたがって実行できる**

**解説:**
Pod 内のすべての containers は常に同じ node 上で実行されます。Pod は複数の nodes にまたがって実行できません。これは Pod の基本的な特徴の 1 つであり、Pod 内の containers がローカルに通信し、volumes を共有できるようにします。Pod 内のすべての containers は同じ network namespace を共有するため同じ IP address を持ち、各 Pod は cluster 内で一意の IP address を持ちます。
</details>

3. 補助 containers によって main container の機能を拡張する multi-container Pod pattern は何ですか？
   - A) Ambassador pattern
   - B) Sidecar pattern
   - C) Adapter pattern
   - D) Init pattern
   
<details>

<summary>答えを表示</summary>

**解答: B) Sidecar pattern**

**解説:**
Sidecar pattern は、main container の機能を拡張する補助 containers を追加します。たとえば、log collectors、file synchronizers、proxies は sidecar containers として実装できます。Ambassador pattern は external services への proxies として機能する containers を追加し、adapter pattern は main container の output を標準化する containers を追加し、init pattern は main container が起動する前に実行される containers を追加します。
</details>

4. Container が requests を処理する準備ができているかを確認し、失敗した場合に service traffic から除外する probe はどれですか？
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>答えを表示</summary>

**解答: B) readinessProbe**

**解説:**
readinessProbe は、container が requests を処理する準備ができているかを確認し、失敗した場合に service traffic から除外します。livenessProbe は container が稼働しているかを確認し、失敗した場合に再起動します。startupProbe は container 内の application が起動したかを確認し、成功するまで他の probes を無効にします。healthProbe は Kubernetes には存在しません。
</details>

5. 次のうち、ReplicaSet の主な機能ではないものはどれですか？
   - A) 指定された数の pod replicas を維持する
   - B) pods が失敗または削除されたときに replacement pods を自動的に作成する
   - C) Rolling updates を実行する
   - D) label selectors を通じて管理対象の pods を識別する
   
<details>

<summary>答えを表示</summary>

**解答: C) Rolling updates を実行する**

**解説:**
Rolling updates は Deployments の主な機能であり、ReplicaSets によって直接サポートされるものではありません。ReplicaSets の主な機能は、指定された数の pod replicas を維持すること、pods が失敗または削除されたときに replacement pods を自動的に作成すること、label selectors を通じて管理対象の pods を識別することです。Deployments は ReplicaSets を管理して、rolling updates、rollbacks、その他の機能を提供します。
</details>

6. 次のうち、Deployments の update strategy ではないものはどれですか？
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>答えを表示</summary>

**解答: C) BlueGreen**

**解説:**
Kubernetes Deployments は、デフォルトで 2 つの update strategies を提供します: RollingUpdate と Recreate です。BlueGreen と Canary は deployment patterns ですが、Deployment update strategies として直接提供されているわけではありません。これらの patterns は Services や Ingresses などの他の Kubernetes resources を使用するか、Argo Rollouts のような追加ツールを使用して実装できます。
</details>

7. 状態の永続化を必要とする applications 向けの workload resource はどれですか？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>答えを表示</summary>

**解答: C) StatefulSet**

**解説:**
StatefulSet は、状態の永続化を必要とする applications 向けの workload resource です。各 pod に一意の identifiers を割り当て、stable network identifiers と persistent storage を提供します。Databases、distributed systems、message queues など、状態を維持する必要がある applications に適しています。Deployments と ReplicaSets は stateless applications 向けであり、DaemonSets は pod の copy がすべての nodes 上で実行されることを保証します。
</details>

8. Pod の copy がすべての（または特定の）nodes 上で実行されることを保証する workload resource はどれですか？
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>答えを表示</summary>

**解答: D) DaemonSet**

**解説:**
DaemonSet は、pod の copy がすべての（または特定の）nodes 上で実行されることを保証します。Node が cluster に追加されると pod は自動的に追加され、node が削除されると pod も削除されます。主に log collectors、monitoring agents、network plugins などの background services を実行するために使用されます。Deployments と ReplicaSets は指定された数の pod replicas を維持し、StatefulSets は状態の永続化を必要とする applications 向けです。
</details>

9. 1 回限りの tasks を実行するための workload resource はどれですか？
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>答えを表示</summary>

**解答: B) Job**

**解説:**
Job は、1 つ以上の pods を作成し、指定された数の pods が正常終了するまで実行を継続する workload resource です。1 回限りの tasks を実行するために使用されます。Deployments は継続的に実行される applications 向け、CronJobs は schedule に従って jobs を定期的に実行し、DaemonSets はすべての nodes 上で pods の copies を実行します。
</details>

10. Schedule に従って tasks を定期的に実行する workload resource はどれですか？
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>答えを表示</summary>

**解答: C) CronJob**

**解説:**
CronJob は、指定された schedule に従って jobs を定期的に実行する workload resource です。Linux cron jobs と同様に動作し、backups、report generation、email sending などの定期的な tasks に使用されます。Deployments は継続的に実行される applications 向け、Jobs は 1 回限りの tasks を実行し、StatefulSets は状態の永続化を必要とする applications 向けです。
</details>

## Short Answer Questions

11. Pod 内の containers が起動する前に実行される特別な container の名前は何ですか？

<details>

<summary>答えを表示</summary>

**解答: Init Container**

**解説:**
Init Containers は、pod 内の app containers が起動する前に実行される特別な containers です。Init containers は定義された順序で 1 つずつ実行され、各 init container は前のものが正常に完了した後にのみ起動します。Init container が失敗した場合、pod の restart policy に従って再起動されます。主に app containers の起動前の setup、dependency checking、permission configuration に使用されます。
</details>

12. Pod が終了されるとき、container に最初に送信される signal は何ですか？

<details>

<summary>答えを表示</summary>

**解答: SIGTERM**

**解説:**
Pod が終了されるとき、kubelet はまず containers に SIGTERM signal を送信します。これにより、application が graceful に shut down するための時間が提供されます。Container がデフォルトの termination period（30 秒）内に終了しない場合、SIGKILL signal が送信されます。Application が SIGTERM signal を受信すると、進行中の作業の完了、connections の close、resources の cleanup、その他の tasks を実行できます。
</details>

13. Deployments が管理する resource の名前は何ですか？

<details>

<summary>答えを表示</summary>

**解答: ReplicaSet**

**解説:**
Deployments は ReplicaSets を管理します。Deployments は ReplicaSets を作成し、ReplicaSets は pods を作成して管理します。Deployments は ReplicaSets を通じて rolling updates、rollbacks、scaling、その他の機能を提供します。Application の新しい version をデプロイするとき、Deployment は新しい ReplicaSet を作成し、以前の ReplicaSet を段階的に scale down します。
</details>

14. StatefulSet 内の pods に割り当てられる一意の identifier の format は何ですか？（たとえば、StatefulSet name が 'web' の場合）

<details>

<summary>答えを表示</summary>

**解答: \<StatefulSet name\>-\<ordinal index\>（例: web-0, web-1, web-2）**

**解説:**
StatefulSets は、pods に `<StatefulSet name>-<ordinal index>` という format の一意の identifiers を割り当てます。たとえば、`web` StatefulSet は `web-0`、`web-1`、`web-2` のような pods を作成します。この identifier は pods が再スケジュールされても維持され、stable network identifiers と persistent storage を提供するために使用されます。
</details>

15. 前の jobs がまだ実行中の場合に新しい jobs をスキップする CronJob の concurrency policy は何ですか？

<details>

<summary>答えを表示</summary>

**解答: Forbid**

**解説:**
CronJob の `Forbid` concurrency policy は、前の jobs がまだ実行中の場合に新しい jobs をスキップします。CronJobs は 3 つの concurrency policies を提供します: `Allow`（複数の jobs を同時に実行可能、default）、`Forbid`（前の jobs がまだ実行中の場合に新しい jobs をスキップ）、`Replace`（前の jobs がまだ実行中の場合に新しい jobs で置き換える）です。これらの policies は `concurrencyPolicy` field を通じて設定できます。
</details>

## Hands-on Questions

16. 次の要件を満たす multi-container pod YAML file を作成してください:
    - Pod name: web-app
    - First container: nginx web server（image: nginx:1.21）
    - Second container: log collector（image: fluentd:v1.14）
    - 2 つの containers 間で log directory を共有するための emptyDir volume
    - nginx container は port 80 を公開する
    - Log volume は nginx container では /var/log/nginx に、fluentd container では /fluentd/log に mount する

<details>

<summary>答えを表示</summary>

**解答:**
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

**解説:**
この YAML file は、nginx web server と fluentd log collector を含む multi-container pod を定義します。`log-volume` という名前の emptyDir volume を作成し、nginx container では `/var/log/nginx` に、fluentd container では `/fluentd/log` に mount します。これにより、fluentd は nginx によって生成された logs を収集できます。nginx container は port 80 を公開します。これは sidecar pattern の例です。
</details>

17. 次の要件を満たす Deployment YAML file を作成してください:
    - Name: nginx-deployment
    - Labels: app=nginx, tier=frontend
    - Replica count: 3
    - Rolling update strategy: max surge 1, max unavailable 0
    - Container image: nginx:1.21
    - Container port: 80
    - Resource requests: CPU 100m, memory 128Mi
    - Resource limits: CPU 200m, memory 256Mi
    - Liveness probe: HTTP GET /, initial delay 30 seconds, period 10 seconds
    - Readiness probe: HTTP GET /, initial delay 5 seconds, period 5 seconds

<details>

<summary>答えを表示</summary>

**解答:**
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

**解説:**
この YAML file は、nginx:1.21 image を使用する 3 replicas の Deployment を定義します。Rolling update strategy は、max surge 1（desired number を超えて作成できる pods の最大数）と max unavailable 0（update 中に unavailable になれる pods の最大数）で設定され、downtime なしの updates を可能にします。各 container は port 80 を公開し、CPU request 100m、memory request 128Mi、CPU limit 200m、memory limit 256Mi の resource constraints を持ちます。Liveness と readiness probes は HTTP GET requests を通じて container status を検証します。
</details>

18. 次の要件を満たす CronJob YAML file を作成してください:
    - Name: database-backup
    - Schedule: 毎日午前 2 時に実行（cron expression を使用）
    - Concurrency policy: Forbid
    - Successful job history limit: 3
    - Failed job history limit: 1
    - Container image: postgres:14
    - Command: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - Environment variables: PGHOST=postgres-service、PGUSER と PGPASSWORD は postgres-secret から取得
    - Volume: backup-pvc を /backup に mount
    - Restart policy: OnFailure

<details>

<summary>答えを表示</summary>

**解答:**
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

**解説:**
この YAML file は、毎日午前 2 時に実行される database backup CronJob を定義します。`concurrencyPolicy: Forbid` は、前の jobs がまだ実行中の場合に新しい jobs をスキップします。`successfulJobsHistoryLimit: 3` と `failedJobsHistoryLimit: 1` は、成功および失敗した jobs の history をそれぞれ 3 と 1 に制限します。Container は postgres:14 image を使用し、database を backup するために pg_dump command を実行します。Environment variable PGHOST は直接設定され、PGUSER と PGPASSWORD は postgres-secret から取得されます。backup-pvc volume は backup files を保存するために /backup directory に mount されます。Restart policy は OnFailure に設定されているため、job が失敗した場合に container が再起動されます。
</details>

## Advanced Questions

19. High availability stateful application のための StatefulSet の設計を説明し、次の要件を満たす MySQL replication cluster の StatefulSet YAML を作成してください:
    - 1 master と 2 slaves で構成される
    - Stable network identifiers を提供する
    - 各 instance に persistent storage を提供する
    - Sequential deployment and scaling
    - Master node failure 時の automatic recovery mechanism

<details>

<summary>答えを表示</summary>

**解答:**

**High Availability Stateful Applications の設計原則**

Stateful applications の high availability を設計する際には、次の原則が適用されます:

1. **Stable network identifiers**: 各 instance は restart 後も同じ network identifier を維持する
2. **Persistent storage**: Instances が再スケジュールされても同じ data にアクセスできる
3. **Sequential deployment and scaling**: Data consistency のために instances を順序どおりに作成および削除する
4. **Automatic recovery mechanism**: Failures が発生したときに自動的に recovery する mechanism
5. **Backup and restore**: 必要に応じた定期 backups と restore procedures

**MySQL Replication Cluster の StatefulSet YAML**

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

**解説:**

この YAML file は、1 master と 2 slaves で構成される MySQL replication cluster の StatefulSet を定義します。

1. **Headless service**: `mysql` service は `clusterIP: None` で設定され、各 pod の DNS records を作成します。これにより、`mysql-0.mysql`、`mysql-1.mysql`、`mysql-2.mysql` のような stable network identifiers が提供されます。

2. **ConfigMap**: MySQL configuration のための ConfigMap を定義します。Master node と slave nodes の別々の configurations、および initialization SQL script を含みます。

3. **StatefulSet**: 3 replicas の MySQL StatefulSet を定義します。
  - `podManagementPolicy: OrderedReady`: Pods を順序どおりに作成および削除します。
  - `updateStrategy: RollingUpdate`: Rolling update strategy を使用します。
  - Init containers: Pod index に基づいて master または slave configuration を適用し、slave nodes は master node から replication を設定します。
  - Persistent storage: `volumeClaimTemplates` を通じて各 pod の persistent volume claims を作成します。
  - Resource requests and limits: 各 MySQL instance の resource requests と limits を設定します。
  - Liveness and readiness probes: MySQL instances の status を検証します。

4. **Automatic recovery mechanism**:
  - Pod が失敗すると、StatefulSet は新しい pod を自動的に作成します。
  - 新しい pod は同じ network identifier と persistent storage を使用します。
  - Slave nodes は data consistency を維持するために master node から replication を設定します。

この設計は high availability MySQL cluster を提供し、master node が失敗した場合に slave nodes の 1 つを新しい master に昇格させる mechanism を実装できます（この例には automatic promotion mechanism は含まれておらず、通常は MySQL Operator または追加の controllers を通じて実装されます）。
</details>

20. さまざまな workload resources（Deployment、StatefulSet、DaemonSet、Job、CronJob）の特徴と use cases を比較し、次の scenarios に最も適した workload resource を選択して、その理由を説明してください:
    - Web application frontend
    - Distributed database cluster
    - Log collection agent
    - Daily data backup
    - One-time data migration

<details>

<summary>答えを表示</summary>

**解答:**

**Workload Resource Comparison**

| Workload Resource | Key Characteristics | Use Cases |
|--------------|---------|---------|
| **Deployment** | - Stateless applications<br>- Rolling update support<br>- Auto scaling<br>- ReplicaSet management | - Web servers<br>- API servers<br>- Stateless microservices<br>- Frontend applications |
| **StatefulSet** | - Stable network identifiers<br>- Persistent storage<br>- Sequential deployment and scaling<br>- Ordered pod creation guaranteed | - Databases<br>- Distributed systems<br>- Message queues<br>- Stateful applications |
| **DaemonSet** | - Runs on all nodes<br>- Auto deployment when nodes are added<br>- Auto cleanup when nodes are removed<br>- Node selection possible | - Log collectors<br>- Monitoring agents<br>- Network plugins<br>- Storage daemons |
| **Job** | - One-time tasks<br>- Completion guarantee<br>- Parallel execution possible<br>- Retry on failure | - Batch processing<br>- Data migration<br>- Computation tasks<br>- One-time management tasks |
| **CronJob** | - Schedule-based execution<br>- Periodic tasks<br>- Concurrency policy<br>- History limits | - Scheduled backups<br>- Data synchronization<br>- Report generation<br>- Cleanup tasks |

**Scenario 別の適切な Workload Resources**

1. **Web Application Frontend**
  - **適切な resource: Deployment**
  - **理由**: Web application frontends は通常 stateless applications です。Deployments は rolling updates を通じて downtime なしで新しい versions をデプロイでき、horizontal scaling が容易で、automatic recovery を提供します。また、HorizontalPodAutoscaler と併用して traffic に基づいて自動的に scale することもできます。

2. **Distributed Database Cluster**
  - **適切な resource: StatefulSet**
  - **理由**: Distributed databases は state persistence を必要とし、各 instance には一意の identifier と persistent storage が必要です。StatefulSets は stable network identifiers（`<pod name>-<ordinal index>`）と persistent storage を提供し、sequential deployment and scaling を通じて data consistency を維持できます。MySQL、PostgreSQL、MongoDB、Cassandra などの distributed database clusters に適しています。

3. **Log Collection Agent**
  - **適切な resource: DaemonSet**
  - **理由**: Log collection agents は cluster 内のすべての nodes 上で実行される必要があります。DaemonSets は pod の copy がすべての（または特定の）nodes 上で実行されることを保証し、新しい nodes が cluster に追加されたときに log collection agents を自動的にデプロイします。Fluentd、Logstash、Filebeat などの log collection agents のデプロイに適しています。

4. **Daily Data Backup**
  - **適切な resource: CronJob**
  - **理由**: Daily data backup は、設定された schedule に従って定期的に実行する必要がある task です。CronJobs は cron expressions を使用して execution schedules を指定でき、毎日特定の時刻に backup tasks を実行するよう設定できます。また、`concurrencyPolicy` を通じて前の backups がまだ実行中の場合の behavior を定義でき、backup history を制限できます。

5. **One-time Data Migration**
  - **適切な resource: Job**
  - **理由**: Data migration は正常に完了する必要がある 1 回限りの task です。Jobs は指定された数の pods が正常終了するまで実行を継続し、失敗時の retry mechanisms を提供します。さらに、大規模な data migrations は `parallelism` settings によって複数の pods を並列実行することで、より速く処理できます。

**Conclusion**

各 workload resource は特定の use cases のために設計されており、application requirements に基づいて適切な resource を選択することが重要です。Deployments は stateless applications に、StatefulSets は state persistence を必要とする applications に、DaemonSets はすべての nodes 上で実行する必要がある services に、Jobs は 1 回限りの tasks に、CronJobs は periodic tasks に適しています。これらの特徴を理解し、適切な workload resource を選択することで、Kubernetes における効率的な application management が可能になります。
</details>

---

[学習資料に戻る](../../core/02-pods-and-workloads.md) | [次のクイズ: Services and Networking](../core/03-services-networking-quiz.md)
