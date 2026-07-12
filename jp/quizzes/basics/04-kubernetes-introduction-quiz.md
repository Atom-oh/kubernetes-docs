# Kubernetes Introduction Quiz

このクイズでは、Kubernetes の基本概念、アーキテクチャ、機能についての理解を確認します。

## Multiple Choice Questions

1. Kubernetes という名前はギリシャ語で何を意味しますか？
   - A) 船長
   - B) 舵取りまたは操縦者
   - C) Container
   - D) 管理者

<details>
<summary>答えを表示</summary>

**答え: B) 舵取りまたは操縦者**

**解説:**
Kubernetes はギリシャ語で「舵取り」または「操縦者」を意味し、containerized application を導く役割を象徴しています。

</details>

2. 次のうち、Kubernetes control plane コンポーネントではないものはどれですか？
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>答えを表示</summary>

**答え: C) kubelet**

**解説:**
kubelet は各 node で実行されるエージェントであり、control plane コンポーネントではありません。

</details>

3. Kubernetes でデプロイ可能な最小単位は何ですか？
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>答えを表示</summary>

**答え: B) Pod**

**解説:**
Pod は Kubernetes でデプロイ可能な最小単位です。

</details>

4. 次のうち、Kubernetes Service のタイプではないものはどれですか？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy

<details>
<summary>答えを表示</summary>

**答え: D) ExternalProxy**

**解説:**
Service のタイプには ClusterIP、NodePort、LoadBalancer、ExternalName があります。

</details>

5. Pod レプリカの数を管理するリソースはどれですか？
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>答えを表示</summary>

**答え: C) ReplicaSet**

**解説:**
ReplicaSet は、指定された数の Pod レプリカが常に実行されるようにします。

</details>

6. ステートフルアプリケーション向けに設計された workload リソースはどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>答えを表示</summary>

**答え: B) StatefulSet**

**解説:**
StatefulSet は、ステートフルアプリケーションのために一意の識別子と永続ストレージを提供します。

</details>

7. すべての node で Pod が実行されるようにするリソースはどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>答えを表示</summary>

**答え: C) DaemonSet**

**解説:**
DaemonSet は、Pod のコピーがすべての（または特定の）node で実行されるようにします。

</details>

8. スケジュールに従って定期的にタスクを実行するリソースはどれですか？
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>答えを表示</summary>

**答え: B) CronJob**

**解説:**
CronJob は、指定されたスケジュールに従って定期的に Job を実行します。

</details>

9. cluster 内でリソースの分離を提供するものは何ですか？
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>答えを表示</summary>

**答え: C) Namespace**

**解説:**
Namespace は、単一の cluster 内でリソースグループを分離する方法を提供します。

</details>

10. EKS とセルフマネージド Kubernetes の主な違いではないものはどれですか？
    - A) control plane 管理
    - B) コア Kubernetes API
    - C) 高可用性構成
    - D) セキュリティパッチの適用

<details>
<summary>答えを表示</summary>

**答え: B) コア Kubernetes API**

**解説:**
どちらも同じ標準 Kubernetes API を使用します。

</details>

## Short Answer Questions

11. すべての cluster データを保存する key-value store は何ですか？

<details>
<summary>答えを表示</summary>

**答え: etcd**

</details>

12. 新しく作成された Pod の node を選択するコンポーネントは何ですか？

<details>
<summary>答えを表示</summary>

**答え: kube-scheduler**

</details>

13. Pod が削除されたときに削除される一時 volume タイプは何ですか？

<details>
<summary>答えを表示</summary>

**答え: emptyDir**

</details>

14. 設定データを key-value 形式で保存するオブジェクトは何ですか？

<details>
<summary>答えを表示</summary>

**答え: ConfigMap**

</details>

15. パスワードなどの機密情報を保存するオブジェクトは何ですか？

<details>
<summary>答えを表示</summary>

**答え: Secret**

</details>

## Practical Questions

16. レプリカ数 3 の nginx 用 Deployment YAML を書いてください。

<details>
<summary>答えを表示</summary>

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

17. LoadBalancer Service YAML を書いてください。

<details>
<summary>答えを表示</summary>

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

18. DATABASE_URL と LOG_LEVEL を含む ConfigMap YAML を書いてください。

<details>
<summary>答えを表示</summary>

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

19. pod の読み取りアクセスを付与する RBAC Role/RoleBinding を書いてください。

<details>
<summary>答えを表示</summary>

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

20. ポート 3306 で backend から database へのトラフィックのみを許可する NetworkPolicy を書いてください。

<details>
<summary>答えを表示</summary>

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
