# Pods and Workloads Quiz

This quiz tests your understanding of Pods, Kubernetes' basic execution unit, and the various workload resources that manage them.

## Multiple Choice Questions

1. What is the smallest deployable computing unit in Kubernetes?
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>Show Answer</summary>

**Answer: B) Pod**

**Explanation:**
A Pod is the smallest deployable computing unit in Kubernetes. A Pod is a group of one or more containers that share storage and network and are scheduled together. While containers are smaller units contained within Pods, they are not the deployment unit directly managed by Kubernetes.
</details>

2. Which of the following is NOT a characteristic of a Pod?
   - A) All containers in a Pod share the same IP address
   - B) All containers in a Pod always run on the same node
   - C) A Pod can run across multiple nodes
   - D) A Pod has a unique IP address
   
<details>

<summary>Show Answer</summary>

**Answer: C) A Pod can run across multiple nodes**

**Explanation:**
All containers in a Pod always run on the same node. A Pod cannot run across multiple nodes. This is one of the fundamental characteristics of Pods, allowing containers within the Pod to communicate locally and share volumes. All containers in a Pod share the same network namespace and thus have the same IP address, and each Pod has a unique IP address within the cluster.
</details>

3. What is the multi-container Pod pattern that extends the functionality of the main container with auxiliary containers?
   - A) Ambassador pattern
   - B) Sidecar pattern
   - C) Adapter pattern
   - D) Init pattern
   
<details>

<summary>Show Answer</summary>

**Answer: B) Sidecar pattern**

**Explanation:**
The sidecar pattern adds auxiliary containers that extend the functionality of the main container. For example, log collectors, file synchronizers, and proxies can be implemented as sidecar containers. The ambassador pattern adds containers that act as proxies to external services, the adapter pattern adds containers that standardize the main container's output, and the init pattern adds containers that run before the main container starts.
</details>

4. Which probe checks if a container is ready to handle requests and removes it from service traffic when it fails?
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>Show Answer</summary>

**Answer: B) readinessProbe**

**Explanation:**
readinessProbe checks if a container is ready to handle requests and removes it from service traffic when it fails. livenessProbe checks if a container is alive and restarts it when it fails. startupProbe checks if the application inside the container has started and disables other probes until it succeeds. healthProbe does not exist in Kubernetes.
</details>

5. Which of the following is NOT a main function of ReplicaSet?
   - A) Maintaining a specified number of pod replicas
   - B) Automatically creating replacement pods when pods fail or are deleted
   - C) Performing rolling updates
   - D) Identifying pods to manage through label selectors
   
<details>

<summary>Show Answer</summary>

**Answer: C) Performing rolling updates**

**Explanation:**
Rolling updates are a main function of Deployments, not directly supported by ReplicaSets. The main functions of ReplicaSets are maintaining a specified number of pod replicas, automatically creating replacement pods when pods fail or are deleted, and identifying pods to manage through label selectors. Deployments manage ReplicaSets to provide rolling updates, rollbacks, and other features.
</details>

6. Which of the following is NOT an update strategy for Deployments?
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>Show Answer</summary>

**Answer: C) BlueGreen**

**Explanation:**
Kubernetes Deployments provide two update strategies by default: RollingUpdate and Recreate. BlueGreen and Canary are deployment patterns but are not provided directly as Deployment update strategies. These patterns can be implemented using other Kubernetes resources such as Services and Ingresses, or using additional tools like Argo Rollouts.
</details>

7. Which workload resource is for applications that require state persistence?
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>Show Answer</summary>

**Answer: C) StatefulSet**

**Explanation:**
StatefulSet is a workload resource for applications that require state persistence. It assigns unique identifiers to each pod and provides stable network identifiers and persistent storage. It is suitable for applications that need to maintain state, such as databases, distributed systems, and message queues. Deployments and ReplicaSets are for stateless applications, and DaemonSets ensure that a copy of a pod runs on all nodes.
</details>

8. Which workload resource ensures that a copy of a pod runs on all (or specific) nodes?
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>Show Answer</summary>

**Answer: D) DaemonSet**

**Explanation:**
DaemonSet ensures that a copy of a pod runs on all (or specific) nodes. When a node is added to the cluster, the pod is automatically added, and when a node is removed, the pod is also removed. It is mainly used for running background services such as log collectors, monitoring agents, and network plugins. Deployments and ReplicaSets maintain a specified number of pod replicas, and StatefulSets are for applications that require state persistence.
</details>

9. Which workload resource is for running one-time tasks?
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>Show Answer</summary>

**Answer: B) Job**

**Explanation:**
A Job is a workload resource that creates one or more pods and continues execution until a specified number of pods successfully terminate. It is used for running one-time tasks. Deployments are for continuously running applications, CronJobs run jobs periodically according to a schedule, and DaemonSets run copies of pods on all nodes.
</details>

10. Which workload resource runs tasks periodically according to a schedule?
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>Show Answer</summary>

**Answer: C) CronJob**

**Explanation:**
CronJob is a workload resource that runs jobs periodically according to a specified schedule. It works similar to Linux cron jobs and is used for regular tasks such as backups, report generation, and email sending. Deployments are for continuously running applications, Jobs run one-time tasks, and StatefulSets are for applications that require state persistence.
</details>

## Short Answer Questions

11. What is the name of the special container that runs before the containers in a pod start?

<details>

<summary>Show Answer</summary>

**Answer: Init Container**

**Explanation:**
Init Containers are special containers that run before the app containers in a pod start. Init containers run one at a time in the defined order, and each init container only starts after the previous one has successfully completed. If an init container fails, it is restarted according to the pod's restart policy. They are mainly used for setup before app containers start, dependency checking, and permission configuration.
</details>

12. What signal is first sent to a container when a pod is terminated?

<details>

<summary>Show Answer</summary>

**Answer: SIGTERM**

**Explanation:**
When a pod is terminated, kubelet first sends a SIGTERM signal to the containers. This provides time for the application to gracefully shut down. If the container does not terminate within the default termination period (30 seconds), a SIGKILL signal is sent. When the application receives the SIGTERM signal, it can complete in-progress work, close connections, clean up resources, and perform other tasks.
</details>

13. What is the name of the resource that Deployments manage?

<details>

<summary>Show Answer</summary>

**Answer: ReplicaSet**

**Explanation:**
Deployments manage ReplicaSets. Deployments create ReplicaSets, and ReplicaSets create and manage pods. Deployments provide rolling updates, rollbacks, scaling, and other features through ReplicaSets. When deploying a new version of an application, the Deployment creates a new ReplicaSet and gradually scales down the previous ReplicaSet.
</details>

14. What is the format of the unique identifier assigned to pods in a StatefulSet? (For example, if the StatefulSet name is 'web')

<details>

<summary>Show Answer</summary>

**Answer: \<StatefulSet name\>-\<ordinal index\> (e.g., web-0, web-1, web-2)**

**Explanation:**
StatefulSets assign unique identifiers in the format `<StatefulSet name>-<ordinal index>` to pods. For example, the `web` StatefulSet creates pods like `web-0`, `web-1`, `web-2`. This identifier is maintained even when pods are rescheduled and is used to provide stable network identifiers and persistent storage.
</details>

15. What is the concurrency policy in CronJob that skips new jobs when previous jobs are still running?

<details>

<summary>Show Answer</summary>

**Answer: Forbid**

**Explanation:**
The `Forbid` concurrency policy in CronJob skips new jobs if previous jobs are still running. CronJobs provide three concurrency policies: `Allow` (multiple jobs can run simultaneously, default), `Forbid` (skips new jobs if previous jobs are still running), and `Replace` (replaces previous jobs with new jobs if still running). These policies can be set through the `concurrencyPolicy` field.
</details>

## Hands-on Questions

16. Write a multi-container pod YAML file that meets the following requirements:
    - Pod name: web-app
    - First container: nginx web server (image: nginx:1.21)
    - Second container: log collector (image: fluentd:v1.14)
    - emptyDir volume for sharing log directory between the two containers
    - nginx container exposes port 80
    - Log volume mounted at /var/log/nginx in the nginx container and /fluentd/log in the fluentd container

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
This YAML file defines a multi-container pod containing an nginx web server and a fluentd log collector. It creates an emptyDir volume named `log-volume` and mounts it at `/var/log/nginx` in the nginx container and `/fluentd/log` in the fluentd container. This allows fluentd to collect logs generated by nginx. The nginx container exposes port 80. This is an example of the sidecar pattern.
</details>

17. Write a Deployment YAML file that meets the following requirements:
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

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
This YAML file defines a Deployment with 3 replicas using the nginx:1.21 image. The rolling update strategy is configured with max surge 1 (maximum number of pods that can be created beyond the desired number) and max unavailable 0 (maximum number of pods that can be unavailable during the update), enabling updates without downtime. Each container exposes port 80 and has resource constraints of CPU request 100m, memory request 128Mi, CPU limit 200m, and memory limit 256Mi. Liveness and readiness probes verify container status through HTTP GET requests.
</details>

18. Write a CronJob YAML file that meets the following requirements:
    - Name: database-backup
    - Schedule: Runs daily at 2 AM (use cron expression)
    - Concurrency policy: Forbid
    - Successful job history limit: 3
    - Failed job history limit: 1
    - Container image: postgres:14
    - Command: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - Environment variables: PGHOST=postgres-service, PGUSER and PGPASSWORD from postgres-secret
    - Volume: Mount backup-pvc to /backup
    - Restart policy: OnFailure

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
This YAML file defines a database backup CronJob that runs daily at 2 AM. `concurrencyPolicy: Forbid` skips new jobs if previous jobs are still running. `successfulJobsHistoryLimit: 3` and `failedJobsHistoryLimit: 1` limit the history of successful and failed jobs to 3 and 1 respectively. The container uses the postgres:14 image and runs the pg_dump command to back up the database. The environment variable PGHOST is set directly, while PGUSER and PGPASSWORD are retrieved from postgres-secret. The backup-pvc volume is mounted to the /backup directory to store backup files. The restart policy is set to OnFailure, so the container is restarted if the job fails.
</details>

## Advanced Questions

19. Explain the design of a StatefulSet for a high availability stateful application and write a StatefulSet YAML for a MySQL replication cluster that meets the following requirements:
    - Composed of 1 master and 2 slaves
    - Provides stable network identifiers
    - Provides persistent storage for each instance
    - Sequential deployment and scaling
    - Automatic recovery mechanism in case of master node failure

<details>

<summary>Show Answer</summary>

**Answer:**

**Design Principles for High Availability Stateful Applications**

The following principles apply to designing high availability for stateful applications:

1. **Stable network identifiers**: Each instance maintains the same network identifier even after restarts
2. **Persistent storage**: Access to the same data even when instances are rescheduled
3. **Sequential deployment and scaling**: Create and delete instances in order for data consistency
4. **Automatic recovery mechanism**: Mechanism to automatically recover when failures occur
5. **Backup and restore**: Regular backups and restore procedures when needed

**StatefulSet YAML for MySQL Replication Cluster**

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

**Explanation:**

This YAML file defines a StatefulSet for a MySQL replication cluster consisting of 1 master and 2 slaves.

1. **Headless service**: The `mysql` service is configured with `clusterIP: None`, which creates DNS records for each pod. This provides stable network identifiers like `mysql-0.mysql`, `mysql-1.mysql`, `mysql-2.mysql`.

2. **ConfigMap**: Defines a ConfigMap for MySQL configuration. Includes separate configurations for master and slave nodes and an initialization SQL script.

3. **StatefulSet**: Defines a MySQL StatefulSet with 3 replicas.
  - `podManagementPolicy: OrderedReady`: Creates and deletes pods in order.
  - `updateStrategy: RollingUpdate`: Uses rolling update strategy.
  - Init containers: Apply master or slave configuration based on pod index, and slave nodes set up replication from the master node.
  - Persistent storage: Creates persistent volume claims for each pod through `volumeClaimTemplates`.
  - Resource requests and limits: Sets resource requests and limits for each MySQL instance.
  - Liveness and readiness probes: Verify the status of MySQL instances.

4. **Automatic recovery mechanism**:
  - When a pod fails, the StatefulSet automatically creates a new pod.
  - The new pod uses the same network identifier and persistent storage.
  - Slave nodes set up replication from the master node to maintain data consistency.

This design provides a high availability MySQL cluster, and a mechanism can be implemented to promote one of the slave nodes to a new master when the master node fails (this example does not include automatic promotion mechanism, which is typically implemented through MySQL Operator or additional controllers).
</details>

20. Compare the characteristics and use cases of various workload resources (Deployment, StatefulSet, DaemonSet, Job, CronJob), and select the most appropriate workload resource for the following scenarios and explain why:
    - Web application frontend
    - Distributed database cluster
    - Log collection agent
    - Daily data backup
    - One-time data migration

<details>

<summary>Show Answer</summary>

**Answer:**

**Workload Resource Comparison**

| Workload Resource | Key Characteristics | Use Cases |
|--------------|---------|---------|
| **Deployment** | - Stateless applications<br>- Rolling update support<br>- Auto scaling<br>- ReplicaSet management | - Web servers<br>- API servers<br>- Stateless microservices<br>- Frontend applications |
| **StatefulSet** | - Stable network identifiers<br>- Persistent storage<br>- Sequential deployment and scaling<br>- Ordered pod creation guaranteed | - Databases<br>- Distributed systems<br>- Message queues<br>- Stateful applications |
| **DaemonSet** | - Runs on all nodes<br>- Auto deployment when nodes are added<br>- Auto cleanup when nodes are removed<br>- Node selection possible | - Log collectors<br>- Monitoring agents<br>- Network plugins<br>- Storage daemons |
| **Job** | - One-time tasks<br>- Completion guarantee<br>- Parallel execution possible<br>- Retry on failure | - Batch processing<br>- Data migration<br>- Computation tasks<br>- One-time management tasks |
| **CronJob** | - Schedule-based execution<br>- Periodic tasks<br>- Concurrency policy<br>- History limits | - Scheduled backups<br>- Data synchronization<br>- Report generation<br>- Cleanup tasks |

**Appropriate Workload Resources by Scenario**

1. **Web Application Frontend**
  - **Appropriate resource: Deployment**
  - **Reason**: Web application frontends are typically stateless applications. Deployments can deploy new versions without downtime through rolling updates, are easy to scale horizontally, and provide automatic recovery. They can also be used with HorizontalPodAutoscaler to automatically scale based on traffic.

2. **Distributed Database Cluster**
  - **Appropriate resource: StatefulSet**
  - **Reason**: Distributed databases require state persistence, and each instance needs a unique identifier and persistent storage. StatefulSets provide stable network identifiers (`<pod name>-<ordinal index>`) and persistent storage, and can maintain data consistency through sequential deployment and scaling. Suitable for distributed database clusters such as MySQL, PostgreSQL, MongoDB, and Cassandra.

3. **Log Collection Agent**
  - **Appropriate resource: DaemonSet**
  - **Reason**: Log collection agents need to run on all nodes in the cluster. DaemonSets ensure that a copy of a pod runs on all (or specific) nodes, and automatically deploy log collection agents when new nodes are added to the cluster. Suitable for deploying log collection agents such as Fluentd, Logstash, and Filebeat.

4. **Daily Data Backup**
  - **Appropriate resource: CronJob**
  - **Reason**: Daily data backup is a task that needs to run periodically according to a set schedule. CronJobs can specify execution schedules using cron expressions and can be set to run backup tasks at a specific time each day. They can also define behavior when previous backups are still running through `concurrencyPolicy` and can limit backup history.

5. **One-time Data Migration**
  - **Appropriate resource: Job**
  - **Reason**: Data migration is a one-time task that must complete successfully. Jobs continue execution until a specified number of pods successfully terminate and provide retry mechanisms on failure. Additionally, large data migrations can be processed faster by running multiple pods in parallel through `parallelism` settings.

**Conclusion**

Each workload resource is designed for specific use cases, and it is important to select the appropriate resource based on application requirements. Deployments are suitable for stateless applications, StatefulSets for applications requiring state persistence, DaemonSets for services that must run on all nodes, Jobs for one-time tasks, and CronJobs for periodic tasks. Understanding these characteristics and selecting the appropriate workload resource enables efficient application management in Kubernetes.
</details>

---

[Return to Learning Materials](../../core/02-pods-and-workloads.md) | [Next Quiz: Services and Networking](../core/03-services-networking-quiz.md)
