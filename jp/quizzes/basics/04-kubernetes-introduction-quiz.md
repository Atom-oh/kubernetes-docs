# Kubernetes 入門クイズ

このクイズでは、Kubernetes の基本概念、アーキテクチャ、機能についての理解を確認します。

## 選択問題

1. Kubernetes という名前はギリシャ語で何を意味しますか？
   - A) 船長
   - B) 舵取りまたは操縦士
   - C) Container
   - D) 管理者

<details>
<summary>回答を表示</summary>

**回答: B) 舵取りまたは操縦士**

**解説:**
Kubernetes はギリシャ語で「舵取り」または「操縦士」を意味し、コンテナ化されたアプリケーションを導く役割を象徴しています。

</details>

2. 次のうち、Kubernetes control plane component ではないものはどれですか？
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>回答を表示</summary>

**回答: C) kubelet**

**解説:**
kubelet は各 node で実行されるエージェントであり、control plane component ではありません。

</details>

3. Kubernetes でデプロイ可能な最小単位は何ですか？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>回答を表示</summary>

**回答: B) Pod**

**解説:**
Pod は Kubernetes でデプロイ可能な最小単位です。

</details>

4. 次のうち、Kubernetes Service type ではないものはどれですか？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy

<details>
<summary>回答を表示</summary>

**回答: D) ExternalProxy**

**解説:**
Service type には ClusterIP、NodePort、LoadBalancer、ExternalName が含まれます。

</details>

5. Pod replicas の数を管理するリソースはどれですか？
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>回答を表示</summary>

**回答: C) ReplicaSet**

**解説:**
ReplicaSet は、指定された数の Pod replicas が常に実行されていることを保証します。

</details>

6. stateful applications 向けに設計された workload resource はどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>回答を表示</summary>

**回答: B) StatefulSet**

**解説:**
StatefulSet は stateful applications に一意の識別子と永続ストレージを提供します。

</details>

7. すべての node で Pod が実行されることを保証するリソースはどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>回答を表示</summary>

**回答: C) DaemonSet**

**解説:**
DaemonSet は、すべての（または特定の）node で Pod のコピーが実行されることを保証します。

</details>

8. スケジュールに従って定期的にタスクを実行するリソースはどれですか？
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>回答を表示</summary>

**回答: B) CronJob**

**解説:**
CronJob は、指定されたスケジュールに従って Job を定期的に実行します。

</details>

9. cluster 内でリソース分離を提供するものは何ですか？
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>回答を表示</summary>

**回答: C) Namespace**

**解説:**
Namespace は、単一の cluster 内でリソースグループを分離する方法を提供します。

</details>

10. EKS と self-managed Kubernetes の主な違いではないものはどれですか？
    - A) Control plane management
    - B) Core Kubernetes API
    - C) High availability configuration
    - D) Security patch application

<details>
<summary>回答を表示</summary>

**回答: B) Core Kubernetes API**

**解説:**
どちらも同じ標準 Kubernetes API を使用します。

</details>

## 短答問題

11. すべての cluster データを保存する key-value store は何ですか？

<details>
<summary>回答を表示</summary>

**回答: etcd**

</details>

12. 新しく作成された Pod の node を選択する component は何ですか？

<details>
<summary>回答を表示</summary>

**回答: kube-scheduler**

</details>

13. Pod が削除されると削除される一時 volume type は何ですか？

<details>
<summary>回答を表示</summary>

**回答: emptyDir**

</details>

14. configuration data を key-value 形式で保存する object は何ですか？

<details>
<summary>回答を表示</summary>

**回答: ConfigMap**

</details>

15. password などの機密情報を保存する object は何ですか？

<details>
<summary>回答を表示</summary>

**回答: Secret**

</details>

## 実践問題

16. replicas が 3 つの nginx 用 Deployment YAML を作成してください。

<details>
<summary>回答を表示</summary>

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

17. LoadBalancer Service YAML を作成してください。

<details>
<summary>回答を表示</summary>

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

18. DATABASE_URL と LOG_LEVEL を含む ConfigMap YAML を作成してください。

<details>
<summary>回答を表示</summary>

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

## 応用問題

19. pod の読み取りアクセスを付与する RBAC Role/RoleBinding を作成してください。

<details>
<summary>回答を表示</summary>

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

20. port 3306 で backend-to-database traffic のみを許可する NetworkPolicy を作成してください。

<details>
<summary>回答を表示</summary>

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

[学習資料に戻る](../../basics/04-kubernetes-introduction.md) | [次のクイズ: Cluster Architecture](../core/01-cluster-architecture-quiz.md)
