# Kubernetes 入门测验

本测验旨在测试你对 Kubernetes 基本概念、架构和功能的理解。

## 选择题

1. Kubernetes 这个名字在希腊语中是什么意思？
   - A) 船长
   - B) 舵手或领航员
   - C) 容器
   - D) 管理员

<details>
<summary>显示答案</summary>

**答案：B) 舵手或领航员**

**解释：**
Kubernetes 在希腊语中意为“舵手”或“领航员”，象征着它在引导容器化应用方面所发挥的作用。

</details>

2. 以下哪一项不是 Kubernetes 控制平面组件？
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>显示答案</summary>

**答案：C) kubelet**

**解释：**
kubelet 是运行在每个节点上的代理，不属于控制平面组件。

</details>

3. Kubernetes 中最小的可部署单元是什么？
   - A) 容器
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

5. 哪种资源负责管理 Pod 副本的数量？
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>显示答案</summary>

**答案：C) ReplicaSet**

**解释：**
ReplicaSet 会协调 Pod 的目标数量；当镜像、调度或应用出现故障时，它无法保证每个 Pod 都处于 Ready 状态。

</details>

6. 哪种工作负载资源专为有状态应用设计？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>显示答案</summary>

**答案：B) StatefulSet**

**解释：**
StatefulSet 为有状态应用提供唯一标识和持久化存储。

StatefulSet 的存储需要 PVC/驱动程序，并不会自动配置数据库复制或备份。
</details>

7. 哪种资源可确保每个节点上都运行一个 Pod？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>显示答案</summary>

**答案：C) DaemonSet**

**解释：**
DaemonSet 会为每个符合条件的节点协调运行一个 Pod，但仍受调度和准入限制约束。

</details>

8. 哪种资源会根据计划定期运行任务？
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>显示答案</summary>

**答案：B) CronJob**

**解释：**
CronJob 会根据指定的计划定期运行 Job。

</details>

9. 什么机制可在集群内提供资源隔离？
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>显示答案</summary>

**答案：C) Namespace**

**解释：**
Namespace 用于限定名称范围并组织资源；RBAC、配额和 NetworkPolicy 则提供额外的访问、资源和网络控制。

</details>

10. 以下哪一项不是 EKS 与自行管理的 Kubernetes 之间的主要区别？
    - A) 控制平面管理
    - B) 核心 Kubernetes API
    - C) 高可用配置
    - D) 安全补丁应用

<details>
<summary>显示答案</summary>

**答案：B) 核心 Kubernetes API**

**解释：**
两者使用相同的标准 Kubernetes API。

</details>

## 简答题

11. 哪种键值存储会保存 Kubernetes API 对象和集群状态，但不包括应用卷中的内容？

<details>
<summary>显示答案</summary>

**答案：etcd**

</details>

12. 哪个组件会为新创建的 Pod 选择节点？

<details>
<summary>显示答案</summary>

**答案：kube-scheduler**

</details>

13. 删除 Pod 时会一并删除哪种临时卷类型？

<details>
<summary>显示答案</summary>

**答案：emptyDir**

</details>

14. 哪种对象会以键值格式存储配置数据？

<details>
<summary>显示答案</summary>

**答案：ConfigMap**

</details>

15. 哪种对象会存储密码等敏感信息？

<details>
<summary>显示答案</summary>

**答案：Secret**

</details>

## 实践题

16. 编写一个 nginx Deployment，包含 3 个副本、端口 80、CPU 100m/内存 128Mi 的 requests，以及 CPU 200m/内存 256Mi 的 limits。

<details>
<summary>显示答案</summary>

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
```

请根据需要为此 Deployment 添加应用就绪检查。
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

这需要 LoadBalancer 实现以及云端/本地网络配置。外部地址处于 Pending 状态通常表示需要相应的实现；本地学习可以使用 port-forward。
</details>

18. 在 ConfigMap 中存储不含凭据的 DATABASE_URL 和 LOG_LEVEL，并在单独的 Secret 中存储数据库凭据和 API_KEY。

<details>
<summary>显示答案</summary>

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

Secret 中的值仅为示例占位符。请通过受保护的输入或密钥管理器提供真实值，不要将其提交到代码库。stringData 不能替代静态数据加密。
</details>

## 高级题

19. 编写 RBAC Role/RoleBinding，以授予读取 Pod 的权限。

<details>
<summary>显示答案</summary>

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

development Namespace 和通过外部身份验证的 jane 身份必须已存在。RoleBinding 不会创建用户账户。
</details>

20. 编写一个 NetworkPolicy，仅允许从 backend 到 database 的 3306 端口流量。

<details>
<summary>显示答案</summary>

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

这需要 production Namespace 和能够强制执行 NetworkPolicy 的网络插件。允许规则会叠加，因此其他策略可以授予额外的访问权限。此策略不会隔离出站流量。
</details>

---

[返回学习资料](../../basics/04-kubernetes-introduction.md) | [下一测验：集群架构](../core/01-cluster-architecture-quiz.md)

## 验证参考资料

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
- https://github.com/fluent/fluent-bit/releases/tag/v5.1.3
- https://github.com/fluent/fluent-bit/blob/v5.1.3/conf/parsers.conf
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
