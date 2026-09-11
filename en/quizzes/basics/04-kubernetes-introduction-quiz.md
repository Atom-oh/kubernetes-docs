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
ReplicaSet reconciles the desired Pod count; it does not guarantee that every Pod is Ready when images, scheduling or applications fail.

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

StatefulSet storage needs PVCs/drivers and does not automatically configure database replication or backups.
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
DaemonSet reconciles one Pod per eligible node, subject to scheduling and admission constraints.

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
Namespace scopes names and resource organization; RBAC, quotas and NetworkPolicy provide additional access/resource/network controls.

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

11. What key-value store stores Kubernetes API objects and cluster state, excluding application volume contents?

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

16. Write an nginx Deployment with 3 replicas, port80, requests of CPU100m/memory128Mi and limits of CPU200m/memory256Mi.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
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
```

Add application readiness checks to this Deployment as appropriate.
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

Requires a LoadBalancer implementation and cloud/local networking setup. A Pending external address usually needs that implementation; local learning can use port-forward.
</details>

18. Store a credential-free DATABASE_URL and LOG_LEVEL in a ConfigMap, and place database credentials and API_KEY in a separate Secret.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_URL: mysql://mysql.default.svc.cluster.local:3306/db
  LOG_LEVEL: INFO
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  DB_USERNAME: replace-from-protected-source
  DB_PASSWORD: replace-from-protected-source
  API_KEY: replace-from-protected-source
```

Secret values are illustrative placeholders. Supply real values through protected input or a secret manager, and do not commit them. stringData does not replace encryption at rest.
</details>

## Advanced Questions

19. Write RBAC Role/RoleBinding to grant pod read access.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: development
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - watch
  - list
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: development
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

The development namespace and an externally authenticated jane identity must exist. RoleBinding does not create a user account.
</details>

20. Write a NetworkPolicy allowing only backend-to-database traffic on port 3306.

<details>
<summary>Show Answer</summary>

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: production
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

Requires the production namespace and a network plugin that enforces NetworkPolicy. Allows are additive, so other policies can grant additional access. This policy does not isolate egress.
</details>

---

[Return to Study Materials](../../basics/04-kubernetes-introduction.md) | [Next Quiz: Cluster Architecture](../core/01-cluster-architecture-quiz.md)

## Verification References

- https://kubernetes.io/releases/version-skew-policy/
- https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
- https://kubernetes.io/docs/setup/production-environment/container-runtimes/
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- https://kubernetes.io/docs/concepts/storage/persistent-volumes/
- https://kubernetes.io/docs/reference/networking/virtual-ips/
- https://kubernetes.io/docs/concepts/services-networking/network-policies/
- https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/
- https://coredns.io/plugins/kubernetes/
- https://github.com/fluent/fluent-bit/releases/tag/v5.1.2
- https://github.com/fluent/fluent-bit/blob/v5.1.2/conf/parsers.conf
- https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html
- https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
- https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html
- https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html
- https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html
- https://eksctl.io/installation/
- https://minikube.sigs.k8s.io/docs/tutorials/multi_node/
- https://kind.sigs.k8s.io/docs/user/quick-start/
- https://github.com/kubernetes/dashboard/blob/master/README.md
- https://headlamp.dev/docs/latest/installation/in-cluster/
- https://github.com/kubernetes-sigs/headlamp/blob/main/charts/headlamp/values.yaml
