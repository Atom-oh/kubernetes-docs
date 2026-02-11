# Kubernetes Introduction Quiz

This quiz tests your understanding of Kubernetes basic concepts, architecture, and features.

## Multiple Choice Questions

1. What does the name Kubernetes mean in Greek?
   - A) Captain
   - B) Helmsman or Pilot
   - C) Container
   - D) Administrator

<details>
<summary>Show Answer</summary>

**Answer: B) Helmsman or Pilot**

**Explanation:**
Kubernetes means 'helmsman' or 'pilot' in Greek, symbolizing its role in guiding containerized applications.

</details>

2. Which of the following is NOT a Kubernetes control plane component?
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>Show Answer</summary>

**Answer: C) kubelet**

**Explanation:**
kubelet is an agent that runs on each node and is not a control plane component.

</details>

3. What is the smallest deployable unit in Kubernetes?
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>Show Answer</summary>

**Answer: B) Pod**

**Explanation:**
A Pod is the smallest deployable unit in Kubernetes.

</details>

4. Which of the following is NOT a Kubernetes Service type?
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy

<details>
<summary>Show Answer</summary>

**Answer: D) ExternalProxy**

**Explanation:**
Service types include ClusterIP, NodePort, LoadBalancer, and ExternalName.

</details>

5. Which resource manages the number of Pod replicas?
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>Show Answer</summary>

**Answer: C) ReplicaSet**

**Explanation:**
ReplicaSet ensures that a specified number of Pod replicas are always running.

</details>

6. Which workload resource is designed for stateful applications?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>Show Answer</summary>

**Answer: B) StatefulSet**

**Explanation:**
StatefulSet provides unique identifiers and persistent storage for stateful applications.

</details>

7. Which resource ensures a Pod runs on all nodes?
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>Show Answer</summary>

**Answer: C) DaemonSet**

**Explanation:**
DaemonSet ensures a copy of a Pod runs on all (or specific) nodes.

</details>

8. Which resource runs tasks periodically according to a schedule?
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>Show Answer</summary>

**Answer: B) CronJob**

**Explanation:**
CronJob runs Jobs periodically according to a specified schedule.

</details>

9. What provides resource isolation within a cluster?
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>Show Answer</summary>

**Answer: C) Namespace**

**Explanation:**
Namespace provides a way to isolate resource groups within a single cluster.

</details>

10. Which is NOT a key difference between EKS and self-managed Kubernetes?
    - A) Control plane management
    - B) Core Kubernetes API
    - C) High availability configuration
    - D) Security patch application

<details>
<summary>Show Answer</summary>

**Answer: B) Core Kubernetes API**

**Explanation:**
Both use the same standard Kubernetes API.

</details>

## Short Answer Questions

11. What key-value store stores all cluster data?

<details>
<summary>Show Answer</summary>

**Answer: etcd**

</details>

12. What component selects a node for newly created Pods?

<details>
<summary>Show Answer</summary>

**Answer: kube-scheduler**

</details>

13. What temporary volume type is deleted when the Pod is deleted?

<details>
<summary>Show Answer</summary>

**Answer: emptyDir**

</details>

14. What object stores configuration data in key-value format?

<details>
<summary>Show Answer</summary>

**Answer: ConfigMap**

</details>

15. What object stores sensitive information like passwords?

<details>
<summary>Show Answer</summary>

**Answer: Secret**

</details>

## Practical Questions

16. Write a Deployment YAML for nginx with 3 replicas.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
```

</details>

17. Write a LoadBalancer Service YAML.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: nginx
```

</details>

18. Write a ConfigMap YAML with DATABASE_URL and LOG_LEVEL.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_URL: "mysql://localhost:3306/db"
  LOG_LEVEL: "INFO"
```

</details>

## Advanced Questions

19. Write RBAC Role/RoleBinding to grant pod read access.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "watch", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: development
subjects:
- kind: User
  name: jane
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

</details>

20. Write a NetworkPolicy allowing only backend-to-database traffic on port 3306.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
spec:
  podSelector:
    matchLabels:
      role: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: backend
    ports:
    - protocol: TCP
      port: 3306
```

</details>

---

[Return to Study Materials](../../basics/04-kubernetes-introduction.md) | [Next Quiz: Cluster Architecture](../core/01-cluster-architecture-quiz.md)
