# Kubernetes 入門クイズ

このクイズでは、Kubernetes の基本概念、アーキテクチャ、機能についての理解を確認します。

## 選択問題

1. Kubernetes という名前はギリシャ語で何を意味しますか？
   - A) 船長
   - B) 舵取りまたは操縦士
   - C) コンテナ
   - D) 管理者

<details>
<summary>解答を表示</summary>

**解答: B) 舵取りまたは操縦士**

**解説:**
Kubernetes はギリシャ語で「舵取り」または「操縦士」を意味し、コンテナ化されたアプリケーションを導く役割を象徴しています。

</details>

2. 次のうち、Kubernetes のコントロールプレーンコンポーネントではないものはどれですか？
   - A) kube-apiserver
   - B) etcd
   - C) kubelet
   - D) kube-scheduler

<details>
<summary>解答を表示</summary>

**解答: C) kubelet**

**解説:**
kubelet は各ノードで動作するエージェントであり、コントロールプレーンコンポーネントではありません。

</details>

3. Kubernetes でデプロイできる最小単位は何ですか？
   - A) コンテナ
   - B) Pod
   - C) Deployment
   - D) Service

<details>
<summary>解答を表示</summary>

**解答: B) Pod**

**解説:**
Pod は Kubernetes でデプロイできる最小単位です。

</details>

4. 次のうち、Kubernetes の Service type ではないものはどれですか？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalProxy

<details>
<summary>解答を表示</summary>

**解答: D) ExternalProxy**

**解説:**
Service type には ClusterIP、NodePort、LoadBalancer、ExternalName があります。

</details>

5. Pod のレプリカ数を管理するリソースはどれですか？
   - A) Service
   - B) ConfigMap
   - C) ReplicaSet
   - D) Namespace

<details>
<summary>解答を表示</summary>

**解答: C) ReplicaSet**

**解説:**
ReplicaSet は Pod の希望数を調整します。ただし、イメージ取得、スケジューリング、アプリケーションに問題がある場合に、すべての Pod が Ready になることを保証するわけではありません。

</details>

6. ステートフルアプリケーション向けに設計されたワークロードリソースはどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>解答を表示</summary>

**解答: B) StatefulSet**

**解説:**
StatefulSet はステートフルアプリケーションに、一意の識別子と永続ストレージを提供します。

StatefulSet のストレージには PVC とストレージドライバーが必要です。また、データベースのレプリケーションやバックアップが自動的に構成されるわけではありません。

</details>

7. 各ノードで Pod を実行するリソースはどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) CronJob

<details>
<summary>解答を表示</summary>

**解答: C) DaemonSet**

**解説:**
DaemonSet は、スケジューリングやアドミッションの制約に従い、対象となる各ノードで 1 つの Pod を調整します。

</details>

8. スケジュールに従って定期的にタスクを実行するリソースはどれですか？
   - A) Job
   - B) CronJob
   - C) Deployment
   - D) ReplicaSet

<details>
<summary>解答を表示</summary>

**解答: B) CronJob**

**解説:**
CronJob は、指定されたスケジュールに従って Job を定期的に実行します。

</details>

9. クラスター内でリソースの名前空間と整理を管理するものは何ですか？
   - A) Label
   - B) Annotation
   - C) Namespace
   - D) ConfigMap

<details>
<summary>解答を表示</summary>

**解答: C) Namespace**

**解説:**
Namespace は名前のスコープとリソースの整理を管理します。アクセス、リソース、ネットワークの制御には、RBAC、クォータ、NetworkPolicy も使用します。

</details>

10. EKS とセルフマネージド Kubernetes の主な違いではないものはどれですか？
    - A) コントロールプレーンの管理
    - B) Kubernetes のコア API
    - C) 高可用性の構成
    - D) セキュリティパッチの適用

<details>
<summary>解答を表示</summary>

**解答: B) Kubernetes のコア API**

**解説:**
どちらも標準の Kubernetes API を使用します。

</details>

## 短答問題

11. アプリケーションのボリューム内容を除き、Kubernetes API オブジェクトとクラスターの状態を保存する key-value ストアは何ですか？

<details>
<summary>解答を表示</summary>

**解答: etcd**

</details>

12. 新しく作成された Pod を配置するノードを選ぶコンポーネントは何ですか？

<details>
<summary>解答を表示</summary>

**解答: kube-scheduler**

</details>

13. Pod が削除されると一緒に削除される一時ボリュームの種類は何ですか？

<details>
<summary>解答を表示</summary>

**解答: emptyDir**

</details>

14. key-value 形式の構成データを保存するオブジェクトは何ですか？

<details>
<summary>解答を表示</summary>

**解答: ConfigMap**

</details>

15. パスワードなどの機密情報を保存するオブジェクトは何ですか？

<details>
<summary>解答を表示</summary>

**解答: Secret**

</details>

## 実践問題

16. レプリカ 3 つ、ポート 80、CPU 100m／メモリ 128Mi の requests、CPU 200m／メモリ 256Mi の limits を指定した nginx Deployment を作成してください。

<details>
<summary>解答を表示</summary>

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

必要に応じて、この Deployment にアプリケーションの readiness check を追加してください。

</details>

17. LoadBalancer Service の YAML を作成してください。

<details>
<summary>解答を表示</summary>

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

LoadBalancer の実装と、クラウドまたはローカルのネットワーク設定が必要です。外部アドレスが Pending のままなら、通常はその実装が必要です。ローカルで学習する場合は port-forward を使えます。

</details>

18. 認証情報を含まない DATABASE_URL と LOG_LEVEL を ConfigMap に保存し、データベースの認証情報と API_KEY は別の Secret に格納してください。

<details>
<summary>解答を表示</summary>

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

Secret の値は例示用のプレースホルダーです。保護された入力経路または Secret Manager から実際の値を与え、値をコミットしないでください。`stringData` は保存時の暗号化の代わりにはなりません。

</details>

## 応用問題

19. Pod の読み取りアクセスを許可する RBAC Role と RoleBinding を作成してください。

<details>
<summary>解答を表示</summary>

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

development namespace と、外部認証された jane という ID が事前に存在している必要があります。RoleBinding はユーザーアカウントを作成しません。

</details>

20. backend から database へのポート 3306 の通信だけを許可する NetworkPolicy を作成してください。

<details>
<summary>解答を表示</summary>

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

production namespace と、NetworkPolicy を適用するネットワークプラグインが必要です。許可ルールは加算されるため、ほかのポリシーが追加のアクセスを許可することがあります。このポリシーは egress を分離しません。

</details>

---

[学習資料に戻る](../../basics/04-kubernetes-introduction.md) | [次のクイズ: クラスターアーキテクチャ](../core/01-cluster-architecture-quiz.md)

## 検証用リファレンス

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
