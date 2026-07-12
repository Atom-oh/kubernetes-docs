# Kubernetes 介绍测验

本测验测试你对 Kubernetes 基本概念、架构和功能的理解。

## 选择题

1. Kubernetes 这个名称在希腊语中是什么意思？
   - A) 船长
   - B) 舵手或领航员
   - C) Container
   - D) 管理员

<details>
<summary>显示答案</summary>

**答案：B) 舵手或领航员**

**解释：**
Kubernetes 在希腊语中的意思是“舵手”或“领航员”，象征着它在引导容器化应用程序方面的作用。

</details>

2. 以下哪一项不是 Kubernetes control plane（控制平面）组件？
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>显示答案</summary>

**答案：C) kubelet**

**解释：**
kubelet 是在每个 Node 上运行的代理，不是 control plane 组件。

</details>

3. Kubernetes 中最小的可部署单元是什么？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>显示答案</summary>

**答案：B) Pod**

**解释：**
Pod 是 Kubernetes 中最小的可部署单元。

</details>

4. 以下哪一项不是 Kubernetes Service 类型？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy

<details>
<summary>显示答案</summary>

**答案：D) ExternalProxy**

**解释：**
Service 类型包括 ClusterIP、NodePort、LoadBalancer 和 ExternalName。

</details>

5. 哪种资源管理 Pod 副本的数量？
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>显示答案</summary>

**答案：C) ReplicaSet**

**解释：**
ReplicaSet 确保指定数量的 Pod 副本始终在运行。

</details>

6. 哪种 workload resource 是为有状态应用程序设计的？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>显示答案</summary>

**答案：B) StatefulSet**

**解释：**
StatefulSet 为有状态应用程序提供唯一标识符和持久化存储。

</details>

7. 哪种资源确保 Pod 在所有 Node 上运行？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>显示答案</summary>

**答案：C) DaemonSet**

**解释：**
DaemonSet 确保 Pod 的一个副本在所有（或特定）Node 上运行。

</details>

8. 哪种资源会按照 schedule 周期性运行任务？
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>显示答案</summary>

**答案：B) CronJob**

**解释：**
CronJob 会根据指定的 schedule 周期性运行 Job。

</details>

9. 什么在 cluster 内提供资源隔离？
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>显示答案</summary>

**答案：C) Namespace**

**解释：**
Namespace 提供了一种在单个 cluster 内隔离资源组的方法。

</details>

10. 哪一项不是 EKS 与 self-managed Kubernetes 之间的关键差异？
    - A) control plane 管理
    - B) 核心 Kubernetes API
    - C) 高可用性配置
    - D) 安全补丁应用

<details>
<summary>显示答案</summary>

**答案：B) 核心 Kubernetes API**

**解释：**
两者都使用相同的标准 Kubernetes API。

</details>

## 简答题

11. 什么 key-value store 存储所有 cluster 数据？

<details>
<summary>显示答案</summary>

**答案：etcd**

</details>

12. 哪个组件为新创建的 Pods 选择 Node？

<details>
<summary>显示答案</summary>

**答案：kube-scheduler**

</details>

13. 哪种临时 volume 类型会在 Pod 被删除时被删除？

<details>
<summary>显示答案</summary>

**答案：emptyDir**

</details>

14. 哪个对象以 key-value 格式存储配置数据？

<details>
<summary>显示答案</summary>

**答案：ConfigMap**

</details>

15. 哪个对象存储密码等敏感信息？

<details>
<summary>显示答案</summary>

**答案：Secret**

</details>

## 实践题

16. 编写一个包含 3 个 replicas 的 nginx Deployment YAML。

<details>
<summary>显示答案</summary>

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

17. 编写一个 LoadBalancer Service YAML。

<details>
<summary>显示答案</summary>

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

18. 编写一个包含 DATABASE_URL 和 LOG_LEVEL 的 ConfigMap YAML。

<details>
<summary>显示答案</summary>

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

## 进阶题

19. 编写 RBAC Role/RoleBinding，以授予 pod 读取访问权限。

<details>
<summary>显示答案</summary>

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

20. 编写一个 NetworkPolicy，只允许 backend-to-database 流量通过端口 3306。

<details>
<summary>显示答案</summary>

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

[返回学习资料](../../basics/04-kubernetes-introduction.md) | [下一个测验：Cluster Architecture](../core/01-cluster-architecture-quiz.md)
