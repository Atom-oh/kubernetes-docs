# Kubernetes 入门测验

本测验考查你对 Kubernetes 基本概念、架构和功能的理解。

## 选择题

1. Kubernetes 这个名称在希腊语中是什么意思？
   - A) 船长
   - B) 舵手或领航员
   - C) Container
   - D) 管理员

<details>
<summary>显示答案</summary>

**答案：B) 舵手或领航员**

**解析：**
Kubernetes 在希腊语中意为“舵手”或“领航员”，象征着它在引导容器化应用程序方面的作用。

</details>

2. 以下哪项不是 Kubernetes control plane（控制平面）组件？
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>显示答案</summary>

**答案：C) kubelet**

**解析：**
kubelet 是在每个 node（节点）上运行的 agent，不是 control plane 组件。

</details>

3. Kubernetes 中最小的可部署单元是什么？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>显示答案</summary>

**答案：B) Pod**

**解析：**
Pod 是 Kubernetes 中最小的可部署单元。

</details>

4. 以下哪项不是 Kubernetes Service 类型？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy

<details>
<summary>显示答案</summary>

**答案：D) ExternalProxy**

**解析：**
Service 类型包括 ClusterIP、NodePort、LoadBalancer 和 ExternalName。

</details>

5. 哪种 resource 管理 Pod 副本数量？
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>显示答案</summary>

**答案：C) ReplicaSet**

**解析：**
ReplicaSet 确保始终运行指定数量的 Pod 副本。

</details>

6. 哪种 workload resource 专为有状态应用程序设计？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>显示答案</summary>

**答案：B) StatefulSet**

**解析：**
StatefulSet 为有状态应用程序提供唯一标识符和持久存储。

</details>

7. 哪种 resource 确保一个 Pod 在所有 node 上运行？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>显示答案</summary>

**答案：C) DaemonSet**

**解析：**
DaemonSet 确保一个 Pod 的副本在所有（或特定）node 上运行。

</details>

8. 哪种 resource 会根据 schedule 周期性运行任务？
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>显示答案</summary>

**答案：B) CronJob**

**解析：**
CronJob 会根据指定的 schedule 周期性运行 Job。

</details>

9. 什么在 cluster 内提供 resource 隔离？
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>显示答案</summary>

**答案：C) Namespace**

**解析：**
Namespace 提供了一种在单个 cluster 内隔离 resource 组的方式。

</details>

10. 以下哪项不是 EKS 与自托管 Kubernetes 之间的关键差异？
    - A) control plane 管理
    - B) 核心 Kubernetes API
    - C) 高可用性配置
    - D) 安全补丁应用

<details>
<summary>显示答案</summary>

**答案：B) 核心 Kubernetes API**

**解析：**
两者都使用相同的标准 Kubernetes API。

</details>

## 简答题

11. 哪种键值存储会存储所有 cluster 数据？

<details>
<summary>显示答案</summary>

**答案：etcd**

</details>

12. 哪个组件会为新创建的 Pod 选择 node？

<details>
<summary>显示答案</summary>

**答案：kube-scheduler**

</details>

13. 当 Pod 被删除时，哪种临时 volume 类型也会被删除？

<details>
<summary>显示答案</summary>

**答案：emptyDir**

</details>

14. 哪个 object 以键值格式存储配置数据？

<details>
<summary>显示答案</summary>

**答案：ConfigMap**

</details>

15. 哪个 object 存储密码等敏感信息？

<details>
<summary>显示答案</summary>

**答案：Secret**

</details>

## 实践题

16. 编写一个包含 3 个副本的 nginx Deployment YAML。

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

19. 编写 RBAC Role/RoleBinding，以授予 Pod 读取访问权限。

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

20. 编写一个 NetworkPolicy，只允许从 backend 到 database 的流量通过端口 3306。

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

[返回学习材料](../../basics/04-kubernetes-introduction.md) | [下一测验：集群架构](../core/01-cluster-architecture-quiz.md)
