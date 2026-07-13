# Extending Kubernetes Quiz

このクイズでは、Kubernetes の拡張メカニズムに関する概念的および実践的な知識を確認します。Custom Resource Definitions (CRD)、custom controllers、API extensions、webhooks、operator pattern などのトピックを扱います。

## Multiple Choice Questions

1. Kubernetes で custom resources を定義する最も一般的な方法は何ですか？
   - A) ConfigMap を使用して resource schema を定義する
   - B) CustomResourceDefinition (CRD) を作成する
   - C) API server のコードを直接変更する
   - D) Aggregation Layer を使用する

<details>
<summary>回答を表示</summary>

**回答: B) CustomResourceDefinition (CRD) を作成する**

**解説:**
Kubernetes で custom resources を定義する最も一般的な方法は、CustomResourceDefinition (CRD) を作成することです。CRD は、新しい resource type を定義することで Kubernetes API を拡張できるメカニズムです。

CRDs を使用すると、次の利点があります。
- 既存の Kubernetes API server を変更せずに、新しい resource type を追加できます。
- `kubectl` のような標準的な Kubernetes tools を使用して custom resources を管理できます。
- resource validation、versioning、status subresources などの機能を活用できます。

CRD の例:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
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
              properties:
                cronSpec:
                  type: string
                image:
                  type: string
                replicas:
                  type: integer
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

他の選択肢の問題点:
- ConfigMaps は設定データを保存するために使用され、API extensions には適していません。
- API server のコードを直接変更するのは複雑で、保守が難しく、upgrade 時に問題を引き起こす可能性があります。
- Aggregation Layer も custom resources を定義する別の方法ですが、別個の API server を実装する必要があるため、CRDs より複雑です。
</details>

2. Kubernetes Operator の主な目的は何ですか？
   - A) cluster nodes の resource usage を最適化する
   - B) 複雑な applications の operational knowledge を自動化された software にエンコードする
   - C) Kubernetes API server の performance を向上させる
   - D) cluster networking functionality を拡張する

<details>
<summary>回答を表示</summary>

**回答: B) 複雑な applications の operational knowledge を自動化された software にエンコードする**

**解説:**
Kubernetes Operator の主な目的は、複雑な applications の operational knowledge を自動化された software にエンコードすることです。operator pattern は、人間の operator が複雑な applications を管理する方法を software として実装したものです。

operators の主な特徴:
- custom resources と custom controllers を組み合わせて、application 固有の logic を実装します。
- application deployment、upgrades、backup、recovery、scaling などの operational tasks を自動化します。
- application state を継続的に監視し、desired state に調整します。
- domain knowledge をコード化し、複雑な applications の declarative management を可能にします。

operators の一般的な use cases:
- databases の自動管理（例: PostgreSQL、MySQL、MongoDB）
- messaging systems の deployment と configuration（例: Kafka、RabbitMQ）
- monitoring systems の setup と maintenance（例: Prometheus）
- service meshes の管理（例: Istio）

Operator 例 - Prometheus Operator:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  replicas: 2
  version: v2.35.0
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  resources:
    requests:
      memory: 400Mi
```

この単純な declarative configuration により、Prometheus Operator は次のような複雑な tasks を自動的に処理します。
- Prometheus servers の deployment
- configuration files の作成と管理
- service monitoring targets の自動検出
- high availability setup
- storage management
- upgrade coordination

他の選択肢は operators の主な目的ではありません。
- Resource usage optimization は HPA (Horizontal Pod Autoscaler)、VPA (Vertical Pod Autoscaler) などの役割です。
- API server performance の向上は operators の主な目的ではありません。
- networking functionality の拡張は CNI plugins または service meshes の役割です。
</details>

3. Kubernetes における Admission Webhooks の主な機能は何ですか？
   - A) API server の authentication を処理する
   - B) resource の作成または変更 requests を intercept し、それらを validate または modify する
   - C) cluster events を監視して alerts を送信する
   - D) external systems との integration のための APIs を提供する

<details>
<summary>回答を表示</summary>

**回答: B) resource の作成または変更 requests を intercept し、それらを validate または modify する**

**解説:**
Kubernetes における Admission Webhooks の主な機能は、resource の作成または変更 requests を intercept し、それらを validate または modify することです。Admission webhooks は、Kubernetes API server が requests を persistent storage (etcd) に保存する前に intercept するメカニズムを提供します。

admission webhooks には 2 種類があります。

1. **Validating Webhook**:
   - resource の create、update、delete requests を validate します。
   - requests を allow または deny できますが、modify はできません。
   - policy enforcement、security checks、configuration validation などに使用されます。

2. **Mutating Webhook**:
   - resource の create および update requests を validate し、modify できます。
   - defaults の設定、sidecar containers の injection、labels の追加などに使用されます。
   - validating webhooks より前に実行されます。

Admission webhook configuration 例:
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-namespace
      name: webhook-service
      path: "/validate-pods"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

admission webhooks の一般的な use cases:
- security policies の enforcement（例: privileged containers の禁止）
- resource requests と limits の enforcement
- sidecar containers の自動 injection（例: Istio）
- labels と annotations の自動追加
- image registries の制限
- namespace-based policies の適用

他の選択肢の問題点:
- API server の authentication を処理するのは Authentication Plugins の役割です。
- cluster events の監視と alerts の送信は event listeners または monitoring tools の役割です。
- external systems との integration のための APIs を提供することは API extensions の一般的な目的ですが、admission webhooks の主な機能ではありません。
</details>

4. Kubernetes API server における Aggregation Layer の主な目的は何ですか？
   - A) API server performance を最適化する
   - B) 複数の API servers を単一の API server に統合する
   - C) custom API servers を main API server に統合して API を拡張する
   - D) cluster 内で service discovery を提供する

<details>
<summary>回答を表示</summary>

**回答: C) custom API servers を main API server に統合して API を拡張する**

**解説:**
Kubernetes API server における Aggregation Layer の主な目的は、custom API servers を main API server に統合して API を拡張することです。これは Kubernetes API を拡張する別の方法を提供し、CRDs よりも強力な機能を提供しますが、より複雑です。

Aggregation Layer の主な特徴:
- custom API servers を Kubernetes API server の URL space に統合します。
- custom API servers は独自の storage、business logic、API versions などを持つことができます。
- main API server は requests を適切な custom API server に proxy します。
- authentication と authorization は main API server によって処理されます。

Aggregation Layer が使用される cases:
- 複雑な validation logic が必要な場合
- custom storage backend が必要な場合
- 既存 APIs とは異なる behavior が必要な場合
- resource transformation または special state calculation が必要な場合

APIService resource 例:
```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1alpha1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1alpha1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
```

この configuration は、`metrics.k8s.io/v1alpha1` API group への requests を `kube-system` namespace 内の `metrics-server` service に routing します。

Aggregation Layer を使用する実例:
- metrics-server: node と pod の resource usage metrics を提供します
- service-catalog: external service brokers との integration
- custom-metrics-apiserver: HPA 用の custom metrics を提供します

他の選択肢の問題点:
- Aggregation Layer は API server performance を最適化するためのものではありません。
- 複数の API servers を 1 つに統合するという説明は正確ではありません。Aggregation Layer は複数の API servers を単一の URL space に統合しますが、servers は別々に実行されます。
- Aggregation Layer は service discovery を提供しません。それは Kubernetes Services の役割です。
</details>

5. Kubernetes における Custom Controller の主な役割は何ですか？
   - A) cluster nodes の resource usage を監視する
   - B) custom resources の state を観察し、desired state に reconcile する
   - C) API server requests の authentication と authorization を処理する
   - D) cluster networking を管理する

<details>
<summary>回答を表示</summary>

**回答: B) custom resources の state を観察し、desired state に reconcile する**

**解説:**
Kubernetes における Custom Controller の主な役割は、custom resources の state を観察し、desired state に reconcile することです。Controllers は、Kubernetes の中核的な operational pattern である「reconciliation loop」を実装し、system の actual state を desired state に継続的に調整します。

custom controllers の主な特徴:
- 特定の resource types（通常は CRDs で定義された custom resources）を watch します。
- resource change events に反応し、business logic を実行します。
- resources の actual state を desired state に調整する tasks を実行します。
- 現在の state を反映するために resources の status field を更新します。

custom controllers の一般的な components:
1. **Informer**: Kubernetes API server を watch し、resource change events を受け取ります。
2. **Work Queue**: 処理される events を保存および管理します。
3. **Reconciler**: resources の desired state と actual state を比較し、必要な tasks を実行します。
4. **Client**: Kubernetes API とやり取りして resources を create、update、delete します。

Custom controller 例 - simple reconcile function:
```go
func (c *Controller) reconcile(key string) error {
    // Split key into namespace and name
    namespace, name, err := cache.SplitMetaNamespaceKey(key)
    if err != nil {
        return err
    }

    // Get custom resource
    instance, err := c.customResourceLister.CustomResources(namespace).Get(name)
    if errors.IsNotFound(err) {
        // Resource deleted - perform cleanup
        return nil
    }
    if err != nil {
        return err
    }

    // Check resource state and perform necessary tasks
    // e.g., create sub-resources, integrate with external systems, update status, etc.

    // Update status
    instanceCopy := instance.DeepCopy()
    instanceCopy.Status.Phase = "Reconciled"
    _, err = c.customResourceClient.CustomResources(namespace).UpdateStatus(instanceCopy)
    return err
}
```

custom controllers の一般的な use cases:
- 複雑な application deployment と management の自動化
- external systems との integration（例: cloud resource provisioning）
- backup と recovery processes の自動化
- 高度な deployment strategies の実装（例: canary deployments、blue-green deployments）

他の選択肢の問題点:
- cluster nodes の resource usage を監視するのは metrics-server または Prometheus などの monitoring tools の役割です。
- API server requests の authentication と authorization を処理するのは authentication and authorization plugins の役割です。
- cluster networking を管理するのは CNI plugins または network controllers の役割です。
</details>

6. Kubernetes で CRDs (CustomResourceDefinitions) の validation schemas を定義するために使用される format は何ですか？
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema

<details>
<summary>回答を表示</summary>

**回答: C) OpenAPI v3 Schema**

**解説:**
Kubernetes で CRDs (CustomResourceDefinitions) の validation schemas を定義するために使用される format は OpenAPI v3 Schema です。この schema は custom resources の structure と field types を定義し、API server が resource creation と update requests を validate するために使用されます。

CRD validation schema の例:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

この例では、`openAPIV3Schema` field が次の validation rules を定義しています。
- `spec` field は必須です。
- `spec` の中では、`cronSpec` と `image` fields が必須です。
- `cronSpec` は string で、cron expression pattern に従う必要があります。
- `image` は string です。
- `replicas` は integer で、1 から 10 の間である必要があります。

OpenAPI v3 Schema はさまざまな validation features を提供します。
- required fields の指定
- data type validation（string、number、boolean、object、array など）
- string pattern validation（regular expressions）
- number range validation（minimum、maximum）
- array length validation
- enum value validation
- nested object structure definition

他の選択肢の問題点:
- JSON Schema は OpenAPI の基礎ですが、Kubernetes は具体的に OpenAPI v3 Schema を使用します。
- XML Schema は Kubernetes API では使用されません。
- GraphQL Schema は GraphQL APIs で使用されますが、Kubernetes API では使用されません。
</details>

7. Kubernetes の custom resources で status subresource を有効にする主な利点は何ですか？
   - A) resource creation が速くなる
   - B) spec と status updates の分離、および RBAC control
   - C) automatic backup と recovery features
   - D) resource version management の簡素化

<details>
<summary>回答を表示</summary>

**回答: B) spec と status updates の分離、および RBAC control**

**解説:**
Kubernetes の custom resources で status subresource を有効にする主な利点は、spec と status updates の分離、および RBAC (Role-Based Access Control) を通じて access を制御できることです。

status subresource を有効にする利点:

1. **Separation of Concerns**:
   - `spec` field は users が指定する desired state を定義します。
   - `status` field は controllers が観察した actual state を報告します。
   - この分離により、users と controllers の責任が明確になります。

2. **RBAC Control**:
   - status update permissions は controllers のみに付与し、通常の users には read-only permissions を与えることができます。
   - これにより、status information の不正な変更を防止できます。

3. **Conflict Prevention**:
   - user が `spec` を更新している間に controller が `status` を更新しても、conflict は発生しません。
   - これは 2 つの fields が別々の API requests を通じて更新されるためです。

4. **Scale Subresource Support**:
   - status subresource を有効にすると、scale subresource も有効化できます。
   - これにより、HPA (Horizontal Pod Autoscaler) のような標準的な Kubernetes scaling tools を使用できます。

CRD で status subresource を有効にする例:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      subresources:
        status: {}  # Enable status subresource
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                # Spec field definitions...
            status:
              type: object
              properties:
                # Status field definitions...
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

controller からの status update の例:
```go
// Update status only
statusUpdate := &v1alpha1.MyResource{}
statusUpdate.Name = instance.Name
statusUpdate.Namespace = instance.Namespace
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(statusUpdate)
```

他の選択肢の問題点:
- status subresource は resource creation speed を向上させません。
- automatic backup と recovery features は提供しません。
- resource version management は CRD の `versions` field を通じて処理され、status subresource とは直接関係ありません。
</details>

8. Kubernetes における Webhook Conversion の主な目的は何ですか？
   - A) API requests を external services に route する
   - B) custom resources の異なる versions 間の conversion を処理する
   - C) authentication tokens を異なる formats に変換する
   - D) log data を structured formats に変換する

<details>
<summary>回答を表示</summary>

**回答: B) custom resources の異なる versions 間の conversion を処理する**

**解説:**
Kubernetes における Webhook Conversion の主な目的は、custom resources の異なる versions 間の conversion を処理することです。この機能は CRDs の multiple versions をサポートし、versions 間のスムーズな migration を可能にします。

webhook conversion の主な特徴:

1. **Multi-Version Support**:
   - CRDs は複数の API versions を同時にサポートできます（例: v1alpha1、v1beta1、v1）。
   - 各 version は異なる schemas と fields を持つことができます。

2. **Automatic Conversion**:
   - API server は client が request した version と storage version の間の conversion を自動的に処理します。
   - conversion webhook はこの process で custom conversion logic を提供します。

3. **Storage Version Independence**:
   - storage version が変更されても、以前の versions を使用する clients は引き続き動作できます。
   - webhook は old versions と new versions の間の bidirectional conversion を処理します。

CRD における conversion webhook configuration の例:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          # v1 schema definition...
    - name: v1beta1
      served: true
      storage: false
      schema:
        openAPIV3Schema:
          # v1beta1 schema definition...
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: webhook-system
          name: crd-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions: ["v1", "v1beta1"]
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

conversion webhook server implementation の例:
```go
func (s *WebhookServer) ServeConvert(w http.ResponseWriter, r *http.Request) {
    var body []byte
    if r.Body != nil {
        if data, err := ioutil.ReadAll(r.Body); err == nil {
            body = data
        }
    }

    // Decode ConversionReview request
    convertReview := v1.ConversionReview{}
    if err := json.Unmarshal(body, &convertReview); err != nil {
        // Error handling
        return
    }

    // Perform conversion logic
    if convertReview.Request.DesiredAPIVersion == "stable.example.com/v1" {
        // v1beta1 -> v1 conversion
        for i, obj := range convertReview.Request.Objects {
            v1beta1Obj := &v1beta1.CronTab{}
            if err := json.Unmarshal(obj.Raw, v1beta1Obj); err != nil {
                // Error handling
                return
            }

            // Conversion logic
            v1Obj := &v1.CronTab{
                Spec: v1.CronTabSpec{
                    CronSpec: v1beta1Obj.Spec.Cron,  // Field name change
                    Image: v1beta1Obj.Spec.Image,
                    Replicas: v1beta1Obj.Spec.Replicas,
                },
            }

            // Encode converted object
            raw, err := json.Marshal(v1Obj)
            if err != nil {
                // Error handling
                return
            }

            convertReview.Response.ConvertedObjects = append(
                convertReview.Response.ConvertedObjects,
                runtime.RawExtension{Raw: raw},
            )
        }
    } else {
        // v1 -> v1beta1 conversion
        // Similar logic...
    }

    // Set response
    convertReview.Response.UID = convertReview.Request.UID
    convertReview.Response.Result.Status = "Success"

    // Send response
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(convertReview)
}
```

他の選択肢の問題点:
- API requests を external services に routing するのは API aggregation の役割です。
- authentication tokens の conversion は authentication plugins の役割です。
- log data の conversion は logging systems の役割です。
</details>

9. 次のうち、Kubernetes operators の開発を支援する framework ではないものはどれですか？
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray

<details>
<summary>回答を表示</summary>

**回答: D) Kubespray**

**解説:**
Kubespray は Kubernetes operators の開発を支援する framework ではありません。Kubespray は Ansible playbooks を使用して Kubernetes clusters を deploy および manage するための tool です。cluster installation と configuration に重点を置いており、operator development とは関係ありません。

Kubernetes operator development のための実際の frameworks は次のとおりです。

1. **Operator Framework**:
   - Red Hat によって開発された operator development toolkit
   - 主な components:
     - Operator SDK: Operator scaffolding と development tools
     - Operator Lifecycle Manager (OLM): Operator installation と upgrade management
     - Operator Metering: Operator usage reporting
   - Go、Ansible、Helm-based operator development をサポート

2. **Kubebuilder**:
   - Kubernetes SIG (Special Interest Group) によって開発された framework
   - Go で controllers を開発するための SDK
   - code generation、CRD management、testing tools を提供
   - controller-runtime library に基づく

3. **Metacontroller**:
   - lightweight webhook-based operator framework
   - さまざまな languages で controller logic を実装可能
   - declarative controller definition
   - simple controllers を素早く開発するのに適している

各 framework の feature comparison:

| Framework | Primary Language | Complexity | Features |
|-----------|------------------|------------|----------|
| Operator Framework | Go, Ansible, Helm | Medium-High | Comprehensive toolkit, various development options |
| Kubebuilder | Go | Medium | Standardized patterns, code generation tools |
| Metacontroller | Language-independent | Low | Webhook-based, simple implementation |

Operator development example (using Kubebuilder):
```bash
# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Implement controller (edit controller.go file)

# Create CRD and deploy controller
make install
make deploy
```

他の選択肢の説明:
- Operator Framework は Red Hat の包括的な operator development toolkit です。
- Kubebuilder は Kubernetes SIG によって開発された Go-based controller development framework です。
- Metacontroller は lightweight webhook-based operator framework です。
</details>

10. Kubernetes における Custom Resource Definitions (CRD) と Aggregated APIs の主な違いは何ですか？
    - A) CRDs は versioning をサポートしないが、Aggregated APIs はサポートする
    - B) CRDs は validation schemas をサポートしないが、Aggregated APIs はサポートする
    - C) CRDs は実装が簡単だが flexibility が限られており、Aggregated APIs は実装が複雑だがより高い flexibility を提供する
    - D) CRDs は cluster-scoped resources のみをサポートし、Aggregated APIs は namespace-scoped resources のみをサポートする

<details>
<summary>回答を表示</summary>

**回答: C) CRDs は実装が簡単だが flexibility が限られており、Aggregated APIs は実装が複雑だがより高い flexibility を提供する**

**解説:**
Kubernetes における Custom Resource Definitions (CRD) と Aggregated APIs の主な違いは、implementation complexity と flexibility のバランスです。CRDs は実装が簡単ですが flexibility が限られており、Aggregated APIs は実装が複雑ですがより高い flexibility を提供します。

**CRDs (CustomResourceDefinitions) の特徴:**
- **Simple implementation**: 単一の YAML file で新しい API resources を定義できます。
- **Uses existing API server**: 別個の API server を実装する必要がありません。
- **Limited flexibility**:
  - Storage は etcd に限定されます。
  - default API server の behavior を継承します。
  - 複雑な validation または conversion logic の実装が難しいです。
- **Extension through webhooks**: 一部の functionality は validating webhooks、conversion webhooks などを通じて拡張できます。

**Aggregated APIs の特徴:**
- **Complex implementation**: 別個の API server を開発し、deploy する必要があります。
- **High flexibility**:
  - custom storage backends を使用できます
  - 複雑な business logic を実装できます
  - custom authentication と authorization logic を実装できます
  - special state calculation と conversion logic を実装できます
- **Full API server functionality**: 標準的な Kubernetes API server のすべての features を活用できます。

**Selection Criteria:**

| Criteria | Choose CRD | Choose Aggregated API |
|----------|------------|----------------------|
| Implementation complexity | Low - Simple YAML definition | High - Requires separate API server development |
| Development time | Short - Can implement in minutes | Long - Requires complete API server development |
| Maintenance | Easy - Managed by existing API server | Difficult - Requires maintaining separate service |
| Storage options | etcd only | Custom storage backends possible |
| Business logic | Limited - Implement via controllers | Flexible - Can implement directly in API server |
| Performance | Generally good | Custom optimization possible |
| Use cases | Simple CRUD operations, standard patterns | Complex API behavior, special validation/conversion |

**Example Scenarios:**

CRDs に適した cases:
- simple application configuration management
- main requirements としての basic CRUD operations
- rapid prototyping と development

Aggregated APIs に適した cases:
- external databases との integration
- 複雑な data transformation と validation
- special authentication mechanisms が必要な場合
- high-performance または special-purpose APIs

他の選択肢の問題点:
- CRDs は versioning をサポートします（A は誤り）。
- CRDs は OpenAPI v3 Schema を通じて validation schemas をサポートします（B は誤り）。
- CRDs と Aggregated APIs はどちらも cluster-scoped と namespace-scoped resources をサポートします（D は誤り）。
</details>

## Short Answer Questions

1. CustomResourceDefinition (CRD) を使用して custom resources を定義する方法と、それらの resources に validation rules を設定する方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**CustomResourceDefinition (CRD) の定義方法:**

CRD は、Kubernetes API を拡張して新しい resource types を定義するメカニズムです。CRD を作成すると、新しい RESTful API endpoint が作成され、`kubectl` のような標準 tools を使用してその resource を管理できます。

**1. Basic CRD Structure:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: <plural>.<group>  # e.g., crontabs.stable.example.com
spec:
  group: <api-group>      # e.g., stable.example.com
  names:
    kind: <kind-name>     # e.g., CronTab
    plural: <plural-name> # e.g., crontabs
    singular: <singular-name>  # e.g., crontab
    shortNames:           # optional
    - <short-name>        # e.g., ct
  scope: Namespaced       # or Cluster
  versions:
    - name: <version>     # e.g., v1
      served: true        # whether to serve via API server
      storage: true       # whether this is the storage version
      schema:
        openAPIV3Schema:
          # schema definition
```

**2. Validation Rules の設定:**

CRDs の validation rules は `openAPIV3Schema` field を通じて設定します。この schema は OpenAPI v3 format に従い、resources の structure と field types を定義します。

**Basic Validation Rules Example:**

```yaml
schema:
  openAPIV3Schema:
    type: object
    required: ["spec"]
    properties:
      spec:
        type: object
        required: ["cronSpec", "image"]
        properties:
          cronSpec:
            type: string
            pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
          image:
            type: string
          replicas:
            type: integer
            minimum: 1
            maximum: 10
            default: 1
```

**3. Advanced Validation Features:**

OpenAPI v3 Schema はさまざまな validation features を提供します。

- **Required fields**: field names を `required` array に追加します
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **Data types**: `type` field を使用して data types を指定します
  ```yaml
  type: string | number | integer | boolean | array | object
  ```

- **String constraints**: string length と patterns を validate します
  ```yaml
  minLength: 3
  maxLength: 64
  pattern: '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
  ```

- **Number constraints**: number ranges を validate します
  ```yaml
  minimum: 0
  maximum: 100
  multipleOf: 5
  ```

- **Array constraints**: array length と items を validate します
  ```yaml
  minItems: 1
  maxItems: 10
  uniqueItems: true
  items:
    type: string
  ```

- **Enum values**: allowed value list を指定します
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **Default values**: fields の default values を指定します
  ```yaml
  default: "default-value"
  ```

- **Additional properties**: additional properties を許可するかどうかを制御します
  ```yaml
  additionalProperties: false
  ```

**4. Complete CRD Example:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                  default: 1
            status:
              type: object
              properties:
                active:
                  type: boolean
                lastScheduleTime:
                  type: string
                  format: date-time
      subresources:
        status: {}  # Enable status subresource
      additionalPrinterColumns:
        - name: Schedule
          type: string
          description: The cron schedule
          jsonPath: .spec.cronSpec
        - name: Image
          type: string
          description: The image to use
          jsonPath: .spec.image
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

**5. CRD の適用と使用:**

```bash
# Apply CRD
kubectl apply -f crontab-crd.yaml

# Create custom resource
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: my-crontab
spec:
  cronSpec: "* * * * */5"
  image: my-cron-image
  replicas: 3
EOF

# View custom resources
kubectl get crontabs
kubectl get ct  # Using short name
```

**6. Validation Rules のテスト:**

無効な values を持つ resource を作成すると、validation errors が発生します。

```bash
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: invalid-crontab
spec:
  cronSpec: "invalid-cron-spec"  # Pattern mismatch
  image: my-cron-image
  replicas: 20  # Exceeds maximum
EOF
```

この command は次のような errors を返します。
```
Error from server (Invalid): error when creating "STDIN": admission webhook "validate-crontab.example.com" denied the request:
- spec.cronSpec: Invalid value: "invalid-cron-spec": does not match pattern '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
- spec.replicas: Invalid value: 20: must be less than or equal to 10
```

**7. Best Practices:**

- 明確で詳細な schema definitions
- required fields を明示的に指定する
- 適切な default values を提供する
- string patterns と number ranges を制限する
- status subresource を有効にする
- additional printer columns を設定する
- versioning strategy を確立する
</details>

2. Kubernetes Operator Pattern の core concepts と、operators を実装する一般的な methods を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Kubernetes Operator Pattern の Core Concepts:**

operator pattern は、application 固有の operational knowledge を software にエンコードして複雑な applications を自動的に管理する Kubernetes extension mechanism です。この pattern は、人間の operator が複雑な systems を管理する方法を模倣します。

**1. Core Concepts:**

- **Declarative Management**: users が desired state を宣言し、operator が current state を desired state に調整します。
- **Encoding Domain Knowledge**: 特定の applications に関する operational knowledge と best practices をコード化します。
- **Reconciliation Loop**: actual state を継続的に観察し、desired state に調整します。
- **Custom Resources**: application 固有の configuration と state を保存するために使用されます。
- **Controllers**: custom resources の変更を watch し、必要な tasks を実行します。

**2. Operators の Common Functions:**

- **Installation and Upgrades**: application components を deploy し、versions を upgrade する
- **Automatic Recovery**: failures を検出し、recovery tasks を実行する
- **Backup and Restore**: data backup と restore processes を自動化する
- **Scaling**: workload requirements に基づく automatic expansion と contraction
- **Configuration Management**: application 固有の configuration changes を処理する
- **Operations Automation**: routine operational tasks（例: database compaction、index rebuilding）を自動化する

**Operators の実装方法:**

**1. Operator SDK の使用:**

[Operator SDK](https://sdk.operatorframework.io/) は Red Hat の Operator Framework の一部であり、operator development を簡素化する tool です。

```bash
# Install Operator SDK
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.25.0/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
sudo mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# Create Go-based operator project
operator-sdk init --domain example.com --repo github.com/example/my-operator

# Create API
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --resource --controller

# Create CRD
make manifests

# Build and deploy operator
make docker-build docker-push
make deploy
```

**2. Kubebuilder の使用:**

[Kubebuilder](https://book.kubebuilder.io/) は Kubernetes SIG によって開発された framework で、controller development のための tools を提供します。

```bash
# Install Kubebuilder
curl -L https://go.kubebuilder.io/dl/latest/$(go env GOOS)/$(go env GOARCH) | tar -xz -C /tmp/
sudo mv /tmp/kubebuilder_*/bin/kubebuilder /usr/local/bin/

# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Create CRD and deploy controller
make install
make deploy
```

**3. Controller Implementation:**

operator の中核は reconciliation function です。この function は custom resources の current state を観察し、必要な tasks を実行します。

```go
// Reconcile function example
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := r.Log.WithValues("myapp", req.NamespacedName)

    // Get custom resource
    var myApp appsv1alpha1.MyApp
    if err := r.Get(ctx, req.NamespacedName, &myApp); err != nil {
        if errors.IsNotFound(err) {
            // Resource deleted - perform cleanup
            return ctrl.Result{}, nil
        }
        // Error occurred
        return ctrl.Result{}, err
    }

    // 1. Check if required resources exist
    deployment := &appsv1.Deployment{}
    err := r.Get(ctx, types.NamespacedName{Name: myApp.Name, Namespace: myApp.Namespace}, deployment)
    if errors.IsNotFound(err) {
        // Create deployment if it doesn't exist
        deployment = r.deploymentForMyApp(&myApp)
        log.Info("Creating a new Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
        if err := r.Create(ctx, deployment); err != nil {
            log.Error(err, "Failed to create new Deployment")
            return ctrl.Result{}, err
        }
        // Deployment creation successful
        return ctrl.Result{Requeue: true}, nil
    } else if err != nil {
        log.Error(err, "Failed to get Deployment")
        return ctrl.Result{}, err
    }

    // 2. Check if deployment is in desired state
    size := myApp.Spec.Size
    if *deployment.Spec.Replicas != size {
        deployment.Spec.Replicas = &size
        if err := r.Update(ctx, deployment); err != nil {
            log.Error(err, "Failed to update Deployment")
            return ctrl.Result{}, err
        }
        // Deployment update successful
        return ctrl.Result{Requeue: true}, nil
    }

    // 3. Update status
    if myApp.Status.AvailableReplicas != deployment.Status.AvailableReplicas {
        myApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
        if err := r.Status().Update(ctx, &myApp); err != nil {
            log.Error(err, "Failed to update MyApp status")
            return ctrl.Result{}, err
        }
    }

    return ctrl.Result{}, nil
}

// Deployment creation function
func (r *MyAppReconciler) deploymentForMyApp(m *appsv1alpha1.MyApp) *appsv1.Deployment {
    ls := labelsForMyApp(m.Name)
    replicas := m.Spec.Size

    dep := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      m.Name,
            Namespace: m.Namespace,
        },
        Spec: appsv1.DeploymentSpec{
            Replicas: &replicas,
            Selector: &metav1.LabelSelector{
                MatchLabels: ls,
            },
            Template: corev1.PodTemplateSpec{
                ObjectMeta: metav1.ObjectMeta{
                    Labels: ls,
                },
                Spec: corev1.PodSpec{
                    Containers: []corev1.Container{{
                        Image: m.Spec.Image,
                        Name:  "myapp",
                        Ports: []corev1.ContainerPort{{
                            ContainerPort: 8080,
                            Name:          "http",
                        }},
                    }},
                },
            },
        },
    }

    // Set owner reference
    ctrl.SetControllerReference(m, dep, r.Scheme)
    return dep
}
```

**4. Custom Resource Definition:**

operator によって管理される custom resources の API を定義します。

```go
// MyApp API
type MyAppSpec struct {
    // Application image
    Image string `json:"image"`

    // Number of replicas
    Size int32 `json:"size"`

    // Configuration options
    Config map[string]string `json:"config,omitempty"`
}

type MyAppStatus struct {
    // Number of available replicas
    AvailableReplicas int32 `json:"availableReplicas"`

    // Last update time
    LastUpdateTime metav1.Time `json:"lastUpdateTime,omitempty"`

    // Status message
    Message string `json:"message,omitempty"`
}

// MyApp resource
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Replicas",type=integer,JSONPath=`.spec.size`
// +kubebuilder:printcolumn:name="Available",type=integer,JSONPath=`.status.availableReplicas`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`
type MyApp struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`

    Spec   MyAppSpec   `json:"spec,omitempty"`
    Status MyAppStatus `json:"status,omitempty"`
}
```

**5. Ansible または Helm-Based Operators:**

Operator SDK は Go に加えて、Ansible または Helm を使用した operator development もサポートしています。

**Ansible-based operator:**
```bash
# Create Ansible-based operator
operator-sdk init --plugins=ansible --domain example.com
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --generate-role

# Edit roles/myapp/tasks/main.yml
```

**Helm-based operator:**
```bash
# Create Helm-based operator
operator-sdk init --plugins=helm --domain example.com --helm-chart=<chart-name>
```

**6. Operators の Deploy と Test:**

```bash
# Deploy operator
make deploy

# Create custom resource
kubectl apply -f config/samples/

# Check operator logs
kubectl logs -f deployment/my-operator-controller-manager -n my-operator-system

# Check resource status
kubectl get myapps
kubectl describe myapp my-app
```

**7. Operator Maturity Levels:**

operator maturity model は operators の capability levels を定義します。

1. **Basic Install**: Application installation と configuration
2. **Seamless Upgrades**: versions 間の automatic upgrades
3. **Full Lifecycle**: Backup、restore、failure recovery など
4. **Deep Insights**: Auto-scaling、tuning など
5. **Auto Pilot**: monitoring-based automatic optimization

**8. Best Practices:**

- features を段階的に実装する（simple things から始める）
- 徹底した error handling と logging
- idempotency を確保する（同じ input には同じ result）
- owner references を設定する（resource hierarchy と garbage collection）
- status updates を通じて progress を報告する
- unit tests と integration tests を書く
- 明確な documentation
</details>

3. Kubernetes における Admission Webhooks の種類と、それぞれの use cases を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Kubernetes Admission Webhooks の種類と Use Cases:**

Admission webhooks は、Kubernetes API server が requests を persistent storage (etcd) に保存する前に、それらを intercept して modify または validate できるメカニズムです。Admission webhooks は大きく 2 種類に分かれます: Mutating webhooks と Validating webhooks です。

**1. Mutating Webhook:**

Mutating webhooks は API server に入ってくる request objects を modify できます。これらの webhooks は validating webhooks より前に実行されます。

**Key Characteristics:**
- request objects を modify できます
- 複数の mutating webhooks が chain で実行されます
- 各 webhook は前の webhook によって modify された object を受け取ります

**Configuration Example:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: sidecar-injector
      path: "/inject"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**Common Use Cases:**

1. **Sidecar Container Injection:**
   - Istio や Linkerd のような service meshes における automatic proxy sidecar injection
   - logging と monitoring sidecars の追加
   - 例: Istio の sidecar injector は pods が作成されると Envoy proxy containers を自動的に追加します

2. **Setting Defaults:**
   - automatic resource requests と limits setting
   - security context defaults の適用
   - labels と annotations の自動追加
   - 例: すべての pods に default CPU と memory requests を設定する

3. **Applying Image Policies:**
   - image registry URLs の変更
   - image tags から digests への変換
   - 例: `nginx:latest` を `internal-registry.example.com/nginx:v1.19.0` に変更する

4. **Volume Modifications:**
   - default volume mounts の追加
   - ConfigMap または Secret の自動 mounting
   - 例: すべての pods に対する automatic service account token volume mounting

5. **Applying Network Policies:**
   - default network settings の追加
   - DNS configuration の変更
   - 例: 特定の namespace 内のすべての pods に特定の DNS settings を適用する

**2. Validating Webhook:**

Validating webhooks は API server に入ってくる requests を validate し、allow または deny できます。これらの webhooks は mutating webhooks の後に実行されます。

**Key Characteristics:**
- request objects を modify できません
- requests を allow または deny することだけができます
- 複数の validating webhooks が parallel に実行されます
- request が処理されるには、すべての webhooks が allow する必要があります

**Configuration Example:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: pod-policy-validator
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**Common Use Cases:**

1. **Enforcing Security Policies:**
   - privileged containers の禁止
   - root user execution の禁止
   - host network/PID/IPC usage の制限
   - 例: privileged mode で実行される pods を deny する

2. **Validating Resource Constraints:**
   - resource requests と limits の必須化
   - resource caps の適用
   - QoS classes の enforcement
   - 例: memory limits のない pods を deny する

3. **Validating Image Policies:**
   - approved registries のみを許可
   - latest tag usage の禁止
   - vulnerability scan results の検証
   - 例: official registries からの images のみを許可する

4. **Validating Labels and Annotations:**
   - required labels の確認
   - label formats の検証
   - 例: すべての pods で `app` と `environment` labels を必須にする

5. **Namespace-Based Policies:**
   - per-namespace resource limits
   - per-namespace feature restrictions
   - 例: production namespaces でより厳格な policies を適用する

**3. Webhook Implementation Methods:**

Admission webhooks は HTTPS endpoints を提供する services として実装されます。これらの services は `AdmissionReview` requests を受け取り、処理し、`AdmissionResponse` を返します。

**Basic Webhook Server Implementation Example (Go):**

```go
package main

import (
    "encoding/json"
    "io/ioutil"
    "net/http"

    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/apimachinery/pkg/runtime/serializer"
)

var (
    runtimeScheme = runtime.NewScheme()
    codecs        = serializer.NewCodecFactory(runtimeScheme)
    deserializer  = codecs.UniversalDeserializer()
)

// Mutating webhook handler
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }

    // Decode AdmissionReview request
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }

    // Decode pod object
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }

    // Create patch (add sidecar container)
    patch := []map[string]interface{}{
        {
            "op": "add",
            "path": "/spec/containers/-",
            "value": map[string]interface{}{
                "name": "sidecar",
                "image": "sidecar-image:latest",
                "resources": map[string]interface{}{
                    "limits": map[string]interface{}{
                        "cpu": "100m",
                        "memory": "100Mi",
                    },
                    "requests": map[string]interface{}{
                        "cpu": "50m",
                        "memory": "50Mi",
                    },
                },
            },
        },
    }

    // Convert patch to JSON
    patchBytes, err := json.Marshal(patch)
    if err != nil {
        http.Error(w, "Failed to marshal patch", http.StatusInternalServerError)
        return
    }

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: true,
        Patch:   patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

// Validating webhook handler
func validateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }

    // Decode AdmissionReview request
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }

    // Decode pod object
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }

    // Validation logic
    allowed := true
    var message string

    // Check for privileged containers
    for _, container := range pod.Spec.Containers {
        if container.SecurityContext != nil && container.SecurityContext.Privileged != nil && *container.SecurityContext.Privileged {
            allowed = false
            message = "Privileged containers are not allowed"
            break
        }
    }

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: allowed,
    }

    if !allowed {
        admissionResponse.Result = &metav1.Status{
            Message: message,
            Status:  "Failure",
            Reason:  metav1.StatusReasonForbidden,
            Code:    403,
        }
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

func main() {
    http.HandleFunc("/mutate", mutateHandler)
    http.HandleFunc("/validate", validateHandler)

    fmt.Println("Starting webhook server on :8443")
    http.ListenAndServeTLS(":8443", "tls.crt", "tls.key", nil)
}
```

**4. Webhook Deployment and Configuration:**

Webhook servers は通常 Kubernetes cluster 内に deploy され、service と TLS certificates が必要です。

```yaml
# Webhook server deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webhook-server
  template:
    metadata:
      labels:
        app: webhook-server
    spec:
      containers:
      - name: server
        image: webhook-server:latest
        ports:
        - containerPort: 8443
        volumeMounts:
        - name: tls
          mountPath: "/etc/webhook/certs"
          readOnly: true
      volumes:
      - name: tls
        secret:
          secretName: webhook-server-tls

---
# Webhook server service
apiVersion: v1
kind: Service
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  selector:
    app: webhook-server
  ports:
  - port: 443
    targetPort: 8443
```

**5. Best Practices:**

- **Performance Optimization**: Webhooks は API server request path 上にあるため、迅速に応答する必要があります。
- **Error Handling**: webhook server が失敗した場合の behavior を考慮し、`failurePolicy` を適切に設定します。
- **Scope Limitation**: webhooks は必要な resources と operations にのみ適用します。
- **Testing**: さまざまな scenarios で webhook behavior を徹底的に test します。
- **Monitoring**: webhook server performance と errors を monitor します。
- **Version Management**: API version changes に備えて、AdmissionReview の複数 versions をサポートします。
</details>

## Hands-on Questions

1. 次の requirements を満たす CustomResourceDefinition (CRD) を書いてください。
   - API Group: webapp.example.com
   - Version: v1
   - Kind: WebApp
   - Scope: Namespaced
   - Required fields: spec.image, spec.replicas
   - Validation rules: replicas must be an integer between 1 and 10
   - Enable status subresource

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.webapp.example.com
spec:
  group: webapp.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["image", "replicas"]
              properties:
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                port:
                  type: integer
                  default: 80
                env:
                  type: array
                  items:
                    type: object
                    required: ["name"]
                    properties:
                      name:
                        type: string
                      value:
                        type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                phase:
                  type: string
      subresources:
        status: {}
      additionalPrinterColumns:
      - name: Replicas
        type: integer
        jsonPath: .spec.replicas
      - name: Image
        type: string
        jsonPath: .spec.image
      - name: Age
        type: date
        jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: webapps
    singular: webapp
    kind: WebApp
    shortNames:
    - wa
```

この CRD には次の特徴があります。

1. **Basic Information**:
   - API Group: `webapp.example.com`
   - Version: `v1`
   - Kind: `WebApp`
   - Scope: `Namespaced`

2. **Schema Validation**:
   - `spec` field は必須です。
   - `spec.image` と `spec.replicas` は required fields です。
   - `spec.replicas` は 1 から 10 の間の integer である必要があります。
   - `spec.port` は default value 80 を持つ optional field です。
   - `spec.env` は environment variables の array を定義する optional field です。

3. **Status Subresource**:
   - `status` subresource が有効化され、controllers が status を update できます。
   - `status.availableReplicas` と `status.phase` fields が定義されています。

4. **Additional Printer Columns**:
   - `kubectl get webapps` を実行すると、Replicas、Image、Age columns が表示されます。

5. **Name Configuration**:
   - Plural: `webapps`
   - Singular: `webapp`
   - Kind: `WebApp`
   - Short name: `wa`

この CRD を使用すると、次のような custom resources を作成できます。

```yaml
apiVersion: webapp.example.com/v1
kind: WebApp
metadata:
  name: my-webapp
  namespace: default
spec:
  image: nginx:1.19
  replicas: 3
  port: 8080
  env:
    - name: ENV_VAR1
      value: "value1"
    - name: ENV_VAR2
      value: "value2"
```

Controllers はこの resource を watch して status を update できます。

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. 次の requirements を満たす Mutating Admission Webhook configuration を書いてください。
   - Add sidecar container to all pod creation requests
   - Apply only to a specific namespace (monitoring)
   - Webhook service: webhook-service.webhook-system.svc
   - Path: /mutate

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-service
      path: "/mutate"
    caBundle: ${CA_BUNDLE}  # Replace with base64-encoded CA certificate in actual environment
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  namespaceSelector:
    matchLabels:
      monitoring-injection: enabled
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
  failurePolicy: Fail
---
# Add label to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    monitoring-injection: enabled
```

この configuration には次の特徴があります。

1. **Webhook Configuration**:
   - Name: `sidecar-injector`
   - Webhook service: `webhook-service.webhook-system.svc`
   - Path: `/mutate`

2. **Scope**:
   - API Group: `""` (core API group)
   - API Version: `v1`
   - Operation: `CREATE` (pod creation 時のみ適用)
   - Resource: `pods`
   - Scope: `Namespaced`

3. **Namespace Selector**:
   - `monitoring-injection: enabled` label を持つ namespaces にのみ適用
   - この label を `monitoring` namespace に追加します

4. **Additional Settings**:
   - `admissionReviewVersions`: サポートされる AdmissionReview API versions
   - `sideEffects`: webhook による side effects はありません
   - `timeoutSeconds`: webhook response wait time
   - `failurePolicy`: webhook failure 時に requests を deny

webhook server は次のような logic を実装する必要があります。

```go
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    // Decode request
    body, _ := ioutil.ReadAll(r.Body)
    admissionReview := admissionv1.AdmissionReview{}
    deserializer.Decode(body, nil, &admissionReview)

    // Decode pod object
    pod := corev1.Pod{}
    json.Unmarshal(admissionReview.Request.Object.Raw, &pod)

    // Define sidecar container
    sidecarContainer := corev1.Container{
        Name:  "monitoring-sidecar",
        Image: "monitoring-agent:latest",
        Resources: corev1.ResourceRequirements{
            Limits: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("100m"),
                corev1.ResourceMemory: resource.MustParse("100Mi"),
            },
            Requests: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("50m"),
                corev1.ResourceMemory: resource.MustParse("50Mi"),
            },
        },
        VolumeMounts: []corev1.VolumeMount{
            {
                Name:      "shared-data",
                MountPath: "/var/monitoring",
            },
        },
    }

    // Create patch
    patch := []map[string]interface{}{
        {
            "op":    "add",
            "path":  "/spec/containers/-",
            "value": sidecarContainer,
        },
        {
            "op":   "add",
            "path": "/spec/volumes/-",
            "value": map[string]interface{}{
                "name": "shared-data",
                "emptyDir": map[string]interface{}{},
            },
        },
    }

    // Convert patch to JSON
    patchBytes, _ := json.Marshal(patch)

    // Create response
    admissionResponse := admissionv1.AdmissionResponse{
        UID:       admissionReview.Request.UID,
        Allowed:   true,
        Patch:     patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }

    // Send response
    admissionReview.Response = &admissionResponse
    resp, _ := json.Marshal(admissionReview)
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}
```

この webhook は `monitoring` namespace で作成されるすべての pods に monitoring sidecar container を自動的に追加します。sidecar container は monitoring agent image を使用し、main container と data を共有するために shared volume を mount します。
</details>
