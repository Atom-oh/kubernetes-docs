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

6. Which are NOT built-in Deployment update strategies? (Select two.)
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>Show Answer</summary>

**Answer: C) BlueGreen and D) Canary**

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

12. What is the default stop signal when a Pod terminates, if the image/container has not overridden it?

<details>

<summary>Show Answer</summary>

**Answer: SIGTERM**

**Explanation:**
When a pod is terminated, kubelet runs any preStop hook and then asks the runtime to send SIGTERM by default. The hook consumes part of the grace period; an image STOPSIGNAL or supported container override can select a different signal. This provides time for the application to gracefully shut down. If the container does not terminate within the default termination period (30 seconds), a SIGKILL signal is sent. When the application receives the SIGTERM signal, it can complete in-progress work, close connections, clean up resources, and perform other tasks.
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
    - First container: nginx web server (image: nginx:1.30.4)
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
      image: nginx:1.30.4
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
This YAML file defines a multi-container pod containing an nginx web server and a fluentd log collector. It creates an emptyDir volume named `log-volume` and mounts it at `/var/log/nginx` in the nginx container and `/fluentd/log` in the fluentd container. This shares the files; actual collection also requires a Fluentd tail source for `/fluentd/log/*.log` and an output configuration. The nginx container exposes port 80. This is an example of the sidecar pattern.
</details>

17. Write a Deployment YAML file that meets the following requirements:
    - Name: nginx-deployment
    - Labels: app=nginx, tier=frontend
    - Replica count: 3
    - Rolling update strategy: max surge 1, max unavailable 0
    - Container image: nginx:1.30.4
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

**Explanation:**
This YAML file defines a Deployment with 3 replicas using the nginx:1.30.4 image. The rolling update strategy is configured with max surge 1 (maximum number of pods that can be created beyond the desired number) and max unavailable 0 (maximum number of pods that can be unavailable during the update), enabling updates without downtime. Each container exposes port 80 and has resource constraints of CPU request 100m, memory request 128Mi, CPU limit 200m, and memory limit 256Mi. Liveness and readiness probes verify container status through HTTP GET requests.
</details>

18. Write a CronJob YAML file that meets the following requirements:
    - Name: database-backup
    - Schedule: Runs daily at 2 AM UTC (use cron expression and timeZone)
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

**Explanation:**
This YAML file defines a database backup CronJob that runs daily at 2 AM. `concurrencyPolicy: Forbid` skips new jobs if previous jobs are still running. `successfulJobsHistoryLimit: 3` and `failedJobsHistoryLimit: 1` limit the history of successful and failed jobs to 3 and 1 respectively. The container uses the postgres:14 image and runs the pg_dump command to back up the database. The environment variable PGHOST is set directly, while PGUSER and PGPASSWORD are retrieved from postgres-secret. The backup-pvc volume is mounted to the /backup directory to store backup files. The restart policy is set to OnFailure, so the container is restarted if the job fails.
</details>

## Advanced Questions

19. Explain which responsibilities a StatefulSet provides for a MySQL cluster with one primary and two replicas, and which require a database operator or replication controller. Why is it incorrect to configure a local MySQL server from a regular init container?

<details>
<summary>Show Answer</summary>

**Answer:**

- A StatefulSet supplies stable Pod names, a governing headless Service, per-Pod PVCs, and ordered scaling by default. It replaces failed Pods with the same ordinal and storage, subject to storage availability.
- It does not copy database data, configure replication, elect/promote a primary, fence an old primary, or redirect database clients. A tested database operator/runbook must implement these behaviors, replication credentials, backups, and restore checks.
- Regular init containers finish before the local application container starts. Attempting a local SQL connection from an init container cannot configure a MySQL server that has not started. Replication setup must run at an appropriate database lifecycle stage.
- Three independent MySQL Pods are not a replicated HA database. Reusing the same server ID across replicas or embedding replication passwords in a ConfigMap is also incorrect.
- See the chapter's single-instance StatefulSet example for Kubernetes identity/storage wiring; do not scale it to three and claim replication or automatic failover.

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
| **Job** | - One-time tasks<br>- Completion tracking (can fail)<br>- Parallel execution possible<br>- Retry on failure | - Batch processing<br>- Data migration<br>- Computation tasks<br>- One-time management tasks |
| **CronJob** | - Schedule-based execution<br>- Periodic tasks<br>- Concurrency policy<br>- History limits | - Scheduled backups<br>- Data synchronization<br>- Report generation<br>- Cleanup tasks |

**Appropriate Workload Resources by Scenario**

1. **Web Application Frontend**
  - **Appropriate resource: Deployment**
  - **Reason**: Web application frontends are typically stateless applications. Deployments can deploy new versions without downtime through rolling updates, are easy to scale horizontally, and provide automatic recovery. They can also be used with HorizontalPodAutoscaler to automatically scale based on traffic.

2. **Distributed Database Cluster**
  - **Appropriate resource: StatefulSet**
  - **Reason**: Distributed databases require state persistence, and each instance needs a unique identifier and persistent storage. StatefulSets provide stable network identifiers (`<StatefulSet name>-<ordinal index>`) and persistent storage, and support ordered deployment and scaling; the database must implement replication and consistency. Suitable for distributed database clusters such as MySQL, PostgreSQL, MongoDB, and Cassandra.

3. **Log Collection Agent**
  - **Appropriate resource: DaemonSet**
  - **Reason**: Log collection agents need to run on all nodes in the cluster. DaemonSets ensure that a copy of a pod runs on all (or specific) nodes, and automatically deploy log collection agents when new nodes are added to the cluster. Suitable for deploying log collection agents such as Fluentd, Logstash, and Filebeat.

4. **Daily Data Backup**
  - **Appropriate resource: CronJob**
  - **Reason**: Daily data backup is a task that needs to run periodically according to a set schedule. CronJobs can specify execution schedules using cron expressions and can be set to run backup tasks at a specific time each day. They can also define behavior when previous backups are still running through `concurrencyPolicy` and can limit Job history; backup-file retention needs a separate policy.

5. **One-time Data Migration**
  - **Appropriate resource: Job**
  - **Reason**: Data migration is a one-time task that must complete successfully. Jobs continue execution until a specified number of pods successfully terminate and provide retry mechanisms on failure. Additionally, large data migrations can be processed faster by running multiple pods in parallel through `parallelism` settings.

**Conclusion**

Each workload resource is designed for specific use cases, and it is important to select the appropriate resource based on application requirements. Deployments are suitable for stateless applications, StatefulSets for applications requiring state persistence, DaemonSets for services that must run on all nodes, Jobs for one-time tasks, and CronJobs for periodic tasks. Understanding these characteristics and selecting the appropriate workload resource enables efficient application management in Kubernetes.
</details>

---

[Return to Learning Materials](../../core/02-pods-and-workloads.md) | [Next Quiz: Services and Networking](../core/03-services-networking-quiz.md)
