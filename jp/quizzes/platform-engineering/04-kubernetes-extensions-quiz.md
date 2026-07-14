# Kubernetes 拡張メカニズムクイズ

> **関連ドキュメント**: [Kubernetes 拡張メカニズム](../../platform-engineering/04-kubernetes-extensions.md)

## 選択式問題

### 1. CRD (Custom Resource Definition) の主な目的は何ですか？

- A) 既存の Kubernetes リソースを変更すること
- B) custom resource type で Kubernetes API を拡張すること
- C) pod networking を設定すること
- D) storage volume をプロビジョニングすること

<details>
<summary>回答を表示</summary>

**回答: B) custom resource type で Kubernetes API を拡張すること**

**解説:**
CRD を使用すると、native Kubernetes resource のように動作する custom resource type を定義して、Kubernetes API を拡張できます。

</details>

### 2. custom controller の reconciliation loop が実行する主なタスクは何ですか？

- A) リソースを即座に削除すること
- B) current state と desired state の差分を調整すること
- C) API server に新しい API を登録すること
- D) network policy を適用すること

<details>
<summary>回答を表示</summary>

**回答: B) current state と desired state の差分を調整すること**

**解説:**
custom controller の reconciliation loop は、リソースの current state を監視し、desired state (spec) と比較して、差分がある場合に desired state を実現するためのアクションを実行します。

</details>

### 3. Operator pattern の中核コンポーネントは何ですか？

- A) Deployment と Service
- B) CRD と Custom Controller
- C) ConfigMap と Secret
- D) Ingress と NetworkPolicy

<details>
<summary>回答を表示</summary>

**回答: B) CRD と Custom Controller**

**解説:**
Operator pattern は、CRD を使用してアプリケーション設定を定義し、custom controller を使用してデプロイ、アップグレード、復旧などの運用知識を自動化します。

</details>

### 4. MutatingAdmissionWebhook の主な用途は何ですか？

- A) API request を拒否すること
- B) API request を変更すること
- C) API response をログに記録すること
- D) API version をアップグレードすること

<details>
<summary>回答を表示</summary>

**回答: B) API request を変更すること**

**解説:**
MutatingAdmissionWebhook は、API request が永続化される前にそれらを変更できます。一般的な用途には、sidecar container injection、default の設定などがあります。

</details>

### 5. scheduler framework における Filter plugin の役割は何ですか？

- A) node に score を割り当てること
- B) pod を実行できない node を除外すること
- C) pod を node に bind すること
- D) node resource を reserve すること

<details>
<summary>回答を表示</summary>

**回答: B) pod を実行できない node を除外すること**

**解説:**
Filter plugin は、pod の要件を満たさない node をフィルタリングし、候補から除外します。

</details>

### 6. Aggregated API Server と CRD の違いは何ですか？

- A) 違いはなく、同じものです
- B) Aggregated API はより多くの制御を提供しますが、別個の server を実行する必要があります
- C) CRD は Aggregated API より多くの機能を提供します
- D) Aggregated API は非推奨です

<details>
<summary>回答を表示</summary>

**回答: B) Aggregated API はより多くの制御を提供しますが、別個の server を実行する必要があります**

**解説:**
Aggregated API Server は、API の動作、custom storage backend、高度な機能を完全に制御できますが、別個の API server をデプロイして維持する必要があります。CRD はよりシンプルですが、制限があります。

</details>

### 7. Kubernetes における Finalizer の目的は何ですか？

- A) リソース削除を高速化すること
- B) cleanup が完了するまでリソース削除を防ぐこと
- C) 失敗した pod を自動的に再起動すること
- D) リソース作成を検証すること

<details>
<summary>回答を表示</summary>

**回答: B) cleanup が完了するまでリソース削除を防ぐこと**

**解説:**
Finalizer は、controller が必要な cleanup operation（外部リソースの削除など）を実行して finalizer を削除するまで、リソース削除をブロックします。

</details>

### 8. pod が node に bind された後に実行される scheduler extension point はどれですか？

- A) PreFilter
- B) PostBind
- C) Reserve
- D) Score

<details>
<summary>回答を表示</summary>

**回答: B) PostBind**

**解説:**
PostBind plugin は、pod が node に正常に bind された後に呼び出されます。これらは情報提供用で、cleanup や通知に使用されます。

</details>

### 9. Istio で admission webhook を介して sidecar を injection するために使用される annotation は何ですか？

- A) istio.io/inject
- B) sidecar.istio.io/inject
- C) istio-injection
- D) auto-inject.istio.io

<details>
<summary>回答を表示</summary>

**回答: B) sidecar.istio.io/inject**

**解説:**
`sidecar.istio.io/inject` annotation は、Istio の mutating webhook が Envoy sidecar を pod に注入するかどうかを制御します。Namespace レベルの制御では `istio-injection` label を使用します。

</details>

### 10. scheduler framework における Score plugin の目的は何ですか？

- A) 不適切な node をフィルタリングすること
- B) node をランク付けして最適なものを選択すること
- C) pod を選択された node に bind すること
- D) pod specification を検証すること

<details>
<summary>回答を表示</summary>

**回答: B) node をランク付けして最適なものを選択すること**

**解説:**
Score plugin は、フィルタリングを通過した node に score を割り当てます。scheduler は、すべての Score plugin からの合計 score が最も高い node を選択します。

</details>

## 短答問題

### 1. CRD の schema validation にはどの標準が使用されますか？

<details>
<summary>回答を表示</summary>

**回答: OpenAPI v3 Schema (openAPIV3Schema)**

**解説:**
CRD は `spec.versions[].schema.openAPIV3Schema` の OpenAPI v3 schema を使用して、custom resource の構造と validation rule を定義します。

</details>

### 2. Kubernetes controller における Owner Reference の役割は何ですか？

<details>
<summary>回答を表示</summary>

**回答: リソース間の ownership relationship を定義し、garbage collection と event propagation を管理すること**

**解説:**
Owner Reference は親子関係を定義し、Kubernetes garbage collection によって親が削除されたときに子を自動的に削除します。

</details>

### 3. ValidatingAdmissionPolicy と ValidatingAdmissionWebhook の違いは何ですか？

<details>
<summary>回答を表示</summary>

**回答: ValidatingAdmissionPolicy は CEL expression を使用して in-process で実行される一方、ValidatingAdmissionWebhook は external HTTP endpoint を呼び出します。**

**解説:**
ValidatingAdmissionPolicy（1.26 で導入）は、より優れたパフォーマンスを提供し、external webhook infrastructure を必要としませんが、webhook より柔軟性は低くなります。

</details>

### 4. controller-runtime library とは何で、なぜ一般的に使用されますか？

<details>
<summary>回答を表示</summary>

**回答: controller-runtime は、client caching、leader election、reconciliation loop management など、Kubernetes controller を構築するための共通パターンを提供する library です。**

**解説:**
Kubebuilder project の一部である controller-runtime は、boilerplate code と best practice を抽象化し、信頼性の高い operator をより簡単に構築できるようにします。

</details>

### 5. CRD における conversion webhook の目的は何ですか？

<details>
<summary>回答を表示</summary>

**回答: Conversion webhook は、同じ CRD の異なる API version 間でリソースを変換します。**

**解説:**
CRD に複数の version（例: v1alpha1、v1beta1、v1）がある場合、conversion webhook は version 間の変換を処理し、API evolution をサポートします。

</details>

## ハンズオン問題

### 1. 次の要件を満たす CRD を作成してください:

- Name: WebApp
- Group: apps.example.com
- Fields: replicas (integer, minimum 1), image (string, required)

<details>
<summary>回答を表示</summary>

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames:
      - wa
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["image"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  default: 1
                image:
                  type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
      additionalPrinterColumns:
        - name: Replicas
          type: integer
          jsonPath: .spec.replicas
        - name: Available
          type: integer
          jsonPath: .status.availableReplicas
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
```

</details>

### 2. "production" namespace 内のすべての Deployment を検証する ValidatingAdmissionWebhook configuration を作成してください。

<details>
<summary>回答を表示</summary>

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: deployment-validator
webhooks:
  - name: validate-deployment.example.com
    clientConfig:
      service:
        name: webhook-service
        namespace: webhook-system
        path: /validate-deployment
      caBundle: <base64-encoded-ca-cert>
    rules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
        scope: Namespaced
    namespaceSelector:
      matchLabels:
        environment: production
    failurePolicy: Fail
    sideEffects: None
    admissionReviewVersions: ["v1"]
    timeoutSeconds: 10
```

**解説:**
- `namespaceSelector` は webhook を `environment: production` label を持つ namespace に制限します
- `failurePolicy: Fail` は webhook が利用できない場合に request を拒否します
- `sideEffects: None` は webhook に副作用がないことを示します

</details>

### 3. custom controller の簡単な reconciliation loop pseudocode を作成してください。

<details>
<summary>回答を表示</summary>

```go
func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // 1. Fetch the WebApp resource
    var webapp appsv1.WebApp
    if err := r.Get(ctx, req.NamespacedName, &webapp); err != nil {
        if errors.IsNotFound(err) {
            // Resource deleted, nothing to do
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // 2. Check if being deleted (handle finalizers)
    if !webapp.DeletionTimestamp.IsZero() {
        if containsFinalizer(webapp, finalizerName) {
            // Perform cleanup
            if err := r.cleanupExternalResources(&webapp); err != nil {
                return ctrl.Result{}, err
            }
            // Remove finalizer
            removeFinalizer(&webapp, finalizerName)
            if err := r.Update(ctx, &webapp); err != nil {
                return ctrl.Result{}, err
            }
        }
        return ctrl.Result{}, nil
    }

    // 3. Add finalizer if not present
    if !containsFinalizer(webapp, finalizerName) {
        addFinalizer(&webapp, finalizerName)
        if err := r.Update(ctx, &webapp); err != nil {
            return ctrl.Result{}, err
        }
    }

    // 4. Create or update Deployment
    deployment := r.constructDeployment(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, deployment, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, deployment); err != nil {
        return ctrl.Result{}, err
    }

    // 5. Create or update Service
    service := r.constructService(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, service, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, service); err != nil {
        return ctrl.Result{}, err
    }

    // 6. Update status
    webapp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
    if err := r.Status().Update(ctx, &webapp); err != nil {
        return ctrl.Result{}, err
    }

    // 7. Requeue after interval for periodic reconciliation
    return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
}
```

**重要ポイント:**
- resource not found を常に処理する（削除済みの場合があります）
- 外部リソースの cleanup には finalizer を使用する
- garbage collection のために owner reference を設定する
- status subresource を個別に更新する
- 定期的なチェックのために requeue interval を考慮する

</details>

## 高度な問題

### 1. 複雑な分散システム向けの Kubernetes Operator を設計してください。

<details>
<summary>回答を表示</summary>

**CRD 設計:**
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: postgresclusters.database.example.com
spec:
  group: database.example.com
  names:
    kind: PostgresCluster
    plural: postgresclusters
    shortNames:
      - pg
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["replicas", "version"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                version:
                  type: string
                  enum: ["14", "15", "16"]
                storage:
                  type: object
                  properties:
                    size:
                      type: string
                      default: "10Gi"
                    storageClass:
                      type: string
                backup:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                      default: true
                    schedule:
                      type: string
                      default: "0 2 * * *"
                    retention:
                      type: integer
                      default: 7
            status:
              type: object
              properties:
                phase:
                  type: string
                  enum: ["Creating", "Running", "Upgrading", "Failed", "Deleting"]
                primaryEndpoint:
                  type: string
                replicaEndpoints:
                  type: array
                  items:
                    type: string
                currentVersion:
                  type: string
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      reason:
                        type: string
                      message:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.readyReplicas
```

**Controller の中核ロジック:**
- **phase-based state management**（Creating、Running、Upgrading、Failed）
- **自動障害復旧**（Primary が失敗した場合の Failover）
- **rolling upgrade strategy**（replica を先にアップグレードし、その後 primary をアップグレード）
- **backup management**（scheduled backup のための CronJob）

**Architecture:**
```
PostgresCluster CR
       |
       v
   Controller
       |
       +---> StatefulSet (PostgreSQL pods)
       +---> Service (Primary endpoint)
       +---> Service (Replica endpoint)
       +---> Secret (Credentials)
       +---> ConfigMap (PostgreSQL config)
       +---> CronJob (Backups)
       +---> PodDisruptionBudget
```

</details>

### 2. scheduler framework を使用して custom scheduler を実装する方法を説明してください。

<details>
<summary>回答を表示</summary>

**Scheduler Plugin Implementation:**

```go
// Plugin implementing multiple extension points
type CustomSchedulerPlugin struct {
    handle framework.Handle
}

// Implement PreFilter - check pod requirements
func (p *CustomSchedulerPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) (*framework.PreFilterResult, *framework.Status) {
    // Validate pod has required annotations
    if _, ok := pod.Annotations["custom-scheduler/zone"]; !ok {
        return nil, framework.NewStatus(framework.Unschedulable, "missing zone annotation")
    }
    return nil, framework.NewStatus(framework.Success, "")
}

// Implement Filter - exclude unsuitable nodes
func (p *CustomSchedulerPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    requiredZone := pod.Annotations["custom-scheduler/zone"]
    nodeZone := nodeInfo.Node().Labels["topology.kubernetes.io/zone"]
    
    if requiredZone != nodeZone {
        return framework.NewStatus(framework.Unschedulable, "zone mismatch")
    }
    return framework.NewStatus(framework.Success, "")
}

// Implement Score - rank suitable nodes
func (p *CustomSchedulerPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := p.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, err.Error())
    }
    
    // Score based on available resources
    allocatable := nodeInfo.Node().Status.Allocatable
    requested := nodeInfo.Requested
    
    cpuScore := calculateResourceScore(allocatable.Cpu(), requested.Cpu)
    memScore := calculateResourceScore(allocatable.Memory(), requested.Memory)
    
    return (cpuScore + memScore) / 2, framework.NewStatus(framework.Success, "")
}

// Register the plugin
func New(_ runtime.Object, h framework.Handle) (framework.Plugin, error) {
    return &CustomSchedulerPlugin{handle: h}, nil
}
```

**Scheduler Configuration:**

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: custom-scheduler
    plugins:
      preFilter:
        enabled:
          - name: CustomSchedulerPlugin
      filter:
        enabled:
          - name: CustomSchedulerPlugin
      score:
        enabled:
          - name: CustomSchedulerPlugin
        disabled:
          - name: NodeResourcesBalancedAllocation
```

**Extension Points Summary:**

| Extension Point | Purpose | Runs When |
|----------------|---------|-----------|
| PreFilter | Pod-level checks | Before filtering |
| Filter | Node elimination | For each node |
| PostFilter | Handle unschedulable | When no node fits |
| PreScore | Prepare for scoring | Before scoring |
| Score | Node ranking | For filtered nodes |
| NormalizeScore | Score normalization | After all scores |
| Reserve | Resource reservation | After node selection |
| Permit | Final approval | Before binding |
| PreBind | Pre-binding actions | Before API binding |
| Bind | Actual binding | API server update |
| PostBind | Post-binding cleanup | After binding |

</details>
