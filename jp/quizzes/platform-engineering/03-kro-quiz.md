# KRO Helm移行クイズ

> **関連ドキュメント**: [Kubernetes Resource Operator (KRO)](../../platform-engineering/03-kro.md)

## 多肢選択問題

### 1. 次のうち、Kubernetes Resource Operator (KRO) の中核概念ではないものはどれですか？

- A) 宣言的なリソース関係
- B) 状態ベースの reconciliation
- C) 命令型スクリプト実行
- D) リソースグラフ

<details>
<summary>回答を表示</summary>

**回答: C) 命令型スクリプト実行**

**解説:**
KRO はリソースを宣言的に管理します。宣言的なリソース関係、状態ベースの reconciliation、リソースグラフ、自動ライフサイクル管理は中核概念ですが、命令型スクリプト実行は KRO の中核概念には含まれません。

</details>

### 2. ResourceGraphDefinition (RGD) における `childResources` の役割は何ですか？

- A) 親リソースのメタデータを定義する
- B) 親リソースから作成される子リソースのリストを定義する
- C) クラスター全体の設定を定義する
- D) Namespace ポリシーを定義する

<details>
<summary>回答を表示</summary>

**回答: B) 親リソースから作成される子リソースのリストを定義する**

**解説:**
`childResources` は、親 Custom Resource（カスタムリソース）から作成される子 Kubernetes リソース（Deployment、Service、Ingress など）のリストとテンプレートを定義します。

</details>

### 3. Helm と比較した KRO の主な差別化要素は何ですか？

- A) Go template の使用
- B) Chart アーカイブのパッケージ化
- C) 明示的なリソース関係のモデリングと自動的な状態伝播
- D) リリース履歴管理

<details>
<summary>回答を表示</summary>

**回答: C) 明示的なリソース関係のモデリングと自動的な状態伝播**

**解説:**
KRO はリソース間の関係を明示的なグラフとしてモデル化し、子リソースの状態を親リソースへ自動的に伝播します。

</details>

### 4. RGD テンプレート内の `.parent` は何を参照しますか？

- A) Kubernetes cluster
- B) 親 Custom Resource
- C) Namespace
- D) Controller pod

<details>
<summary>回答を表示</summary>

**回答: B) 親 Custom Resource**

**解説:**
RGD テンプレートでは、`.parent` は ResourceGraphDefinition が適用される親 Custom Resource を参照します。

</details>

### 5. KRO で条件付きの子リソース作成に使用されるフィールドはどれですか？

- A) `when`
- B) `if`
- C) `condition`
- D) `enabled`

<details>
<summary>回答を表示</summary>

**回答: C) `condition`**

**解説:**
RGD の childResources にある `condition` フィールドを使用して、子リソースを条件付きで作成できます。

</details>

### 6. RGD における `statusMappings` の目的は何ですか？

- A) エラー処理の動作を定義する
- B) 子リソースの status を親リソースの status にマッピングする
- C) ログレベルを設定する
- D) Resource quota を設定する

<details>
<summary>回答を表示</summary>

**回答: B) 子リソースの status を親リソースの status にマッピングする**

**解説:**
`statusMappings` は、子リソースから status 情報を抽出し、それを親 Custom Resource の status フィールドへ伝播する方法を定義します。

</details>

### 7. KRO はリソースの依存関係をどのように扱いますか？

- A) YAML ファイル内の手動の順序付けによって
- B) 作成順序を自動的に決定するリソースグラフによって
- C) 数値の優先度フィールドによって
- D) アルファベット順によって

<details>
<summary>回答を表示</summary>

**回答: B) 作成順序を自動的に決定するリソースグラフによって**

**解説:**
KRO はリソースグラフを使用してリソース間の依存関係を理解し、リソースの作成と削除の正しい順序を自動的に決定します。

</details>

### 8. KRO で親 Custom Resource が削除されるとどうなりますか？

- A) 子リソースは孤立したまま残る
- B) 子リソースは自動的に garbage collection される
- C) 手動のクリーンアップが必要になる
- D) エラーがスローされる

<details>
<summary>回答を表示</summary>

**回答: B) 子リソースは自動的に garbage collection される**

**解説:**
KRO は子リソースに owner reference を設定するため、親が削除されると、Kubernetes の garbage collector がすべての子リソースを自動的に削除します。

</details>

### 9. KRO で Custom Resource の変更を監視するコンポーネントはどれですか？

- A) API Server
- B) Scheduler
- C) KRO Controller
- D) Kubelet

<details>
<summary>回答を表示</summary>

**回答: C) KRO Controller**

**解説:**
KRO Controller は、ResourceGraphDefinitions によって定義された Custom Resource の変更を監視し、望ましい状態へ reconciliation します。

</details>

### 10. KRO における Helm の `helm upgrade --install` 動作に相当するものは何ですか？

- A) Custom Resource に対する `kubectl apply`
- B) Custom Resource に対する `kubectl replace`
- C) Custom Resource に対する `kubectl patch`
- D) `kubectl create --save-config`

<details>
<summary>回答を表示</summary>

**回答: A) Custom Resource に対する `kubectl apply`**

**解説:**
`kubectl apply` は、`helm upgrade --install` と同様の冪等な動作を提供します。リソースが存在しない場合は作成し、存在する場合は更新します。

</details>

## 短答問題

### 1. Custom Resource と Kubernetes native リソースの関係を定義する、KRO の中核リソースは何ですか？

<details>
<summary>回答を表示</summary>

**回答: ResourceGraphDefinition (RGD)**

**解説:**
ResourceGraphDefinition (RGD) は KRO の中核コンポーネントであり、Custom Resource（親）と Kubernetes native リソース（子）の関係を宣言的に定義します。

</details>

### 2. Helm の values.yaml に相当する KRO のものは何ですか？

<details>
<summary>回答を表示</summary>

**回答: Custom Resource (CR) の spec フィールド**

**解説:**
Helm が values.yaml を通じて設定をカスタマイズするのと同様に、KRO は Custom Resource の spec フィールドを通じてアプリケーション設定を定義します。

</details>

### 3. RGD テンプレートで sibling の子リソースの出力をどのように参照しますか？

<details>
<summary>回答を表示</summary>

**回答: `.children.<resourceId>` 構文を使用する**

**解説:**
RGD テンプレートでは、`.children.<resourceId>` を使用して他の子リソースを参照し、それらの metadata、spec、status フィールドにアクセスして、リソース間参照に利用できます。

</details>

### 4. KRO は管理対象リソースを追跡するためにどの annotation を使用しますか？

<details>
<summary>回答を表示</summary>

**回答: `kro.run/owner` annotation**

**解説:**
KRO は Kubernetes owner reference とともに `kro.run/owner` annotation を使用して、どのリソースがどの親 Custom Resource によって管理されているかを追跡します。

</details>

### 5. KRO は Custom Resource の schema validation をどのように扱いますか？

<details>
<summary>回答を表示</summary>

**回答: RGD の spec.schema フィールドで定義された OpenAPI v3 Schema によって**

**解説:**
KRO は RGD から CRD を生成し、schema validation は ResourceGraphDefinition で定義された OpenAPI v3 Schema を使用して実行されます。

</details>

## ハンズオン問題

### 1. 次の Helm values.yaml を KRO Custom Resource インスタンスに変換してください。

```yaml
# Helm values.yaml
replicaCount: 2
image:
  repository: myapp
  tag: "1.0.0"
service:
  type: ClusterIP
  port: 8080
```

<details>
<summary>回答を表示</summary>

```yaml
apiVersion: kro.example.com/v1
kind: MyApp
metadata:
  name: my-application
spec:
  replicas: 2
  image:
    repository: myapp
    tag: "1.0.0"
  service:
    type: ClusterIP
    port: 8080
```

</details>

### 2. 親 spec に基づいて Deployment を作成する RGD childResource 定義を書いてください。

<details>
<summary>回答を表示</summary>

```yaml
childResources:
  - id: deployment
    resource:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: "{{.parent.metadata.name}}"
      spec:
        replicas: "{{.parent.spec.replicas}}"
        selector:
          matchLabels:
            app: "{{.parent.metadata.name}}"
        template:
          metadata:
            labels:
              app: "{{.parent.metadata.name}}"
          spec:
            containers:
              - name: app
                image: "{{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}"
                ports:
                  - containerPort: "{{.parent.spec.service.port}}"
```

</details>

### 3. Deployment の available replicas を親 status に公開する statusMappings 設定を書いてください。

<details>
<summary>回答を表示</summary>

```yaml
statusMappings:
  - childResourceId: deployment
    fieldPath: status.availableReplicas
    parentFieldPath: status.availableReplicas
  - childResourceId: deployment
    fieldPath: status.conditions
    parentFieldPath: status.deploymentConditions
```

**解説:**
statusMappings は子リソースの status から特定のフィールドを抽出し、それらを親 Custom Resource の status にマッピングすることで、ユーザーが親リソースを通じてアプリケーションの状態を確認できるようにします。

</details>

## 応用問題

### 1. KRO を使用してマルチ環境（dev/staging/production）の deployment 戦略を設計してください。

<details>
<summary>回答を表示</summary>

**環境固有の Custom Resource インスタンス:**

```yaml
# dev/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-dev
spec:
  replicas: 1
  image:
    tag: "dev-latest"
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
---
# staging/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-staging
spec:
  replicas: 2
  image:
    tag: "rc-1.0.0"
  resources:
    requests:
      cpu: "250m"
      memory: "256Mi"
---
# production/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-prod
spec:
  replicas: 3
  image:
    tag: "v1.0.0"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"
```

**GitOps 統合:**
ArgoCD ApplicationSet を使用して、すべての環境で単一の RGD による環境固有の deployment を自動化します。

</details>

### 2. データベースクラスターのような stateful application を管理する場合の Helm と KRO の運用上の違いを比較してください。

<details>
<summary>回答を表示</summary>

**Helm アプローチ:**
- テンプレートベース: インストール時に静的な manifests を生成する
- リリース管理: Secrets/ConfigMaps を介してバージョンを追跡する
- アップグレードプロセス: `helm upgrade` コマンドが必要
- 状態追跡: 初回 deployment 後の組み込み reconciliation はない
- ロールバック: 保存されたリリース履歴を使用する

**KRO アプローチ:**
- Reconciliation ベース: drift を継続的に監視して修正する
- Native Kubernetes: 標準の kubectl と CRDs を使用する
- アップグレードプロセス: CR spec を変更すると、controller が reconciliation する
- 状態追跡: controller が継続的に監視して reconciliation する
- ロールバック: CR spec を以前の状態に戻す

**Stateful Applications における主な違い:**

| Aspect | Helm | KRO |
|--------|------|-----|
| Drift Detection | Manual | Automatic |
| Self-healing | No | Yes |
| Status Visibility | External (helm status) | Native (kubectl get) |
| Dependency Management | Chart dependencies | Resource graph |
| Lifecycle Hooks | pre/post hooks | Controller logic |

**推奨:**
KRO は、継続的な reconciliation、自動的な drift 修正、複雑なライフサイクル管理を必要とする stateful application により適しています。Helm は、単純な deployment を持つ stateless application に対してよりシンプルです。

</details>
