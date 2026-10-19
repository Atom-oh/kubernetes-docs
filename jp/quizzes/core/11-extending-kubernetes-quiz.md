# Kubernetes拡張クイズ

このクイズでは、Kubernetesの拡張メカニズムに関する概念と実践的な知識を確認します。Custom Resource Definition（CRD）、カスタムコントローラー、API拡張、Webhook、Operatorパターンなどを扱います。

## 選択式問題

1. Kubernetesでカスタムリソースを定義する最も一般的な方法は何ですか？
   - A) ConfigMapでリソーススキーマを定義する
   - B) CustomResourceDefinition（CRD）を作成する
   - C) APIサーバーのコードを直接変更する
   - D) Aggregation Layerを使用する

<details>
<summary>回答を表示</summary>

**回答: B) CustomResourceDefinition（CRD）を作成する**

**解説:**
Kubernetesでカスタムリソースを定義する最も一般的な方法は、CustomResourceDefinition（CRD）を作成することです。CRDを使うと、新しいリソース型を定義してKubernetes APIを拡張できます。

CRDには次の利点があります。
- 既存のKubernetes APIサーバーを変更せずに、新しいリソース型を追加できます。
- `kubectl`などの標準ツールでカスタムリソースを管理できます。
- リソース検証、バージョン管理、statusサブリソースなどの機能を利用できます。

CRDの例:
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

他の選択肢が適さない理由:
- ConfigMapは設定データを保存するためのもので、APIを拡張する用途には適しません。
- APIサーバーのコードを直接変更すると、実装や保守が難しく、アップグレード時に問題が起きる可能性があります。
- Aggregation Layerもカスタムリソースを定義する方法ですが、独立したAPIサーバーの実装が必要なため、CRDより複雑です。
</details>

2. Kubernetes Operatorの主な目的は何ですか？
   - A) クラスターノードのリソース使用量を最適化する
   - B) 複雑なアプリケーションを運用する知識を、自動化ソフトウェアに組み込む
   - C) Kubernetes APIサーバーの性能を向上させる
   - D) クラスターのネットワーク機能を拡張する

<details>
<summary>回答を表示</summary>

**回答: B) 複雑なアプリケーションを運用する知識を、自動化ソフトウェアに組み込む**

**解説:**
Kubernetes Operatorの主な目的は、複雑なアプリケーションを運用する知識を自動化ソフトウェアに組み込むことです。Operatorパターンは、人が複雑なアプリケーションを運用する方法をソフトウェアとして実装します。

Operatorの主な特徴:
- カスタムリソースとカスタムコントローラーを組み合わせ、アプリケーション固有のロジックを実装します。
- アプリケーションのデプロイ、アップグレード、バックアップ、復旧、スケーリングなどを自動化します。
- アプリケーションの状態を継続的に監視し、望ましい状態に調整します。
- ドメイン知識をコード化し、複雑なアプリケーションを宣言的に管理できるようにします。

Operatorの一般的な用途:
- PostgreSQL、MySQL、MongoDBなどのデータベースの自動管理
- Kafka、RabbitMQなどのメッセージングシステムのデプロイと設定
- Prometheusなどの監視システムの構築と保守
- Istioなどのサービスメッシュの管理

Operatorの例 — Prometheus Operator:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  replicas: 2
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  resources:
    requests:
      memory: 400Mi
```

この宣言的な設定を使うと、Prometheus Operatorは次のような複雑な作業を自動的に処理します。
- Prometheusサーバーのデプロイ
- 設定ファイルの作成と管理
- 監視対象サービスの自動検出
- 高可用性の構成
- storageまたはvolumeClaimTemplateを設定した場合のストレージ管理
- アップグレードの調整

他の選択肢はOperatorの主な目的ではありません。
- リソース使用量の最適化は、HPA（Horizontal Pod Autoscaler）やVPA（Vertical Pod Autoscaler）などが担います。
- APIサーバーの性能向上は、Operatorの主な目的ではありません。
- ネットワーク機能の拡張は、CNIプラグインやサービスメッシュが担います。
</details>

3. KubernetesのAdmission Webhookの主な機能は何ですか？
   - A) APIサーバーの認証を処理する
   - B) リソースの作成または変更要求を受け取り、検証または変更する
   - C) クラスターイベントを監視してアラートを送信する
   - D) 外部システムと統合するためのAPIを提供する

<details>
<summary>回答を表示</summary>

**回答: B) リソースの作成または変更要求を受け取り、検証または変更する**

**解説:**
Admission Webhookは、リソースの作成または変更要求を受け取り、検証または変更します。Kubernetes APIサーバーが要求を永続ストレージ（etcd）に保存する前に介入する仕組みです。

Admission Webhookには次の2種類があります。

1. **Validating Webhook**:
   - リソースの作成、更新、削除要求を検証します。
   - 要求を許可または拒否できますが、内容は変更できません。
   - ポリシー適用、セキュリティチェック、設定検証などに使います。

2. **Mutating Webhook**:
   - リソースの作成および更新要求を検証し、内容を変更できます。
   - デフォルト値の設定、サイドカーの注入、ラベルの追加などに使います。
   - Validating Webhookより先に実行されます。

Admission Webhook設定の例:
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
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

Admission Webhookの一般的な用途:
- 特権コンテナを禁止するなど、セキュリティポリシーを適用する
- リソース要求量と上限を必須にする
- Istioなどのサイドカーコンテナを自動注入する
- ラベルやannotationを自動追加する
- 使用可能なイメージレジストリを制限する
- namespaceごとのポリシーを適用する

他の選択肢が適さない理由:
- APIサーバーの認証はAuthentication Pluginが担います。
- クラスターイベントの監視とアラート送信は、イベントリスナーや監視ツールが担います。
- 外部システムとの統合にAPIを提供するのはAPI拡張の一般的な役割ですが、Admission Webhookの主な機能ではありません。
</details>

4. Kubernetes APIサーバーのAggregation Layerの主な目的は何ですか？
   - A) APIサーバーの性能を最適化する
   - B) 複数のAPIサーバーを1つのAPIサーバーに統合する
   - C) カスタムAPIサーバーをメインAPIサーバーに統合してAPIを拡張する
   - D) クラスター内のサービスディスカバリーを提供する

<details>
<summary>回答を表示</summary>

**回答: C) カスタムAPIサーバーをメインAPIサーバーに統合してAPIを拡張する**

**解説:**
Aggregation Layerは、カスタムAPIサーバーをメインAPIサーバーに統合してAPIを拡張します。CRDより強力な機能を提供できますが、実装はより複雑です。

Aggregation Layerの主な特徴:
- カスタムAPIサーバーをKubernetes APIサーバーのURL空間に統合します。
- カスタムAPIサーバーは、独自のストレージ、ビジネスロジック、APIバージョンなどを持てます。
- メインAPIサーバーは、要求を該当するカスタムAPIサーバーにプロキシします。
- メインAPIサーバーがユーザーを認証します。拡張APIサーバーは認証プロキシを検証し、SubjectAccessReviewによる委任認可を行う必要があります。

Aggregation Layerを使うケース:
- 複雑な検証ロジックが必要な場合
- 独自のストレージバックエンドが必要な場合
- 既存APIとは異なる動作が必要な場合
- リソース変換や特殊な状態計算が必要な場合

APIServiceリソースの例:
```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1beta1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1beta1
  caBundle: <base64-encoded-serving-ca>
  groupPriorityMinimum: 100
  versionPriority: 100
```

この設定では、`metrics.k8s.io/v1beta1` APIグループへの要求を、`kube-system` namespace内の`metrics-server`サービスに転送します。

Aggregation Layerを使った実例:
- metrics-server: ノードとPodのリソース使用量メトリクスを提供します
- service-catalog（アーカイブ済み）: 過去のservice broker統合機能です
- custom-metrics-apiserver: HPA向けのカスタムメトリクスを提供します

他の選択肢が適さない理由:
- Aggregation LayerはAPIサーバーの性能最適化を目的としていません。
- 複数のAPIサーバーを1つに統合するという説明は正確ではありません。複数のサーバーを単一のURL空間に統合しますが、サーバー自体は別々に動作します。
- Aggregation Layerはサービスディスカバリーを提供しません。それはKubernetes Serviceの役割です。
</details>

5. Kubernetesのカスタムコントローラーの主な役割は何ですか？
   - A) クラスターノードのリソース使用量を監視する
   - B) カスタムリソースの状態を監視し、望ましい状態に調整する
   - C) APIサーバー要求の認証と認可を処理する
   - D) クラスターのネットワークを管理する

<details>
<summary>回答を表示</summary>

**回答: B) カスタムリソースの状態を監視し、望ましい状態に調整する**

**解説:**
カスタムコントローラーは、カスタムリソースの状態を監視し、望ましい状態に調整します。コントローラーは、Kubernetesの基本的な運用パターンである「調整ループ」を実装し、システムの実際の状態を望ましい状態に継続的に近づけます。

カスタムコントローラーの主な特徴:
- 特定のリソース型（通常はCRDで定義したカスタムリソース）を監視します。
- リソース変更イベントに応じて、ビジネスロジックを実行します。
- 実際の状態を望ましい状態に合わせる作業を行います。
- リソースのstatusフィールドを更新して、現在の状態を報告します。

カスタムコントローラーの主な構成要素:
1. **Informer**: Kubernetes APIサーバーを監視し、リソース変更イベントを受け取ります。
2. **Work Queue**: 処理するイベントを保存し、管理します。
3. **Reconciler**: 望ましい状態と実際の状態を比較し、必要な処理を実行します。
4. **Client**: Kubernetes APIとやり取りし、リソースを作成、更新、削除します。

カスタムコントローラーの例 — 単純なreconcile関数:
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
        // Already deleted. External cleanup must run earlier using a finalizer.
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
    _, err = c.customResourceClient.CustomResources(namespace).UpdateStatus(context.TODO(), instanceCopy, metav1.UpdateOptions{})
    return err
}
```

カスタムコントローラーの一般的な用途:
- 複雑なアプリケーションのデプロイと管理を自動化する
- 外部システムと連携する（例: クラウドリソースのプロビジョニング）
- バックアップと復旧を自動化する
- カナリアリリースやBlue/Greenデプロイなど、高度なデプロイ戦略を実装する

他の選択肢が適さない理由:
- クラスターノードのリソース使用量監視は、metrics-serverやPrometheusなどの監視ツールが担います。
- APIサーバー要求の認証と認可は、認証・認可プラグインが担います。
- クラスターのネットワーク管理は、CNIプラグインやネットワークコントローラーが担います。
</details>

6. KubernetesのCRD（CustomResourceDefinition）で検証スキーマを定義する際に使う形式は何ですか？
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema

<details>
<summary>回答を表示</summary>

**回答: C) OpenAPI v3 Schema**

**解説:**
CRDの検証スキーマにはOpenAPI v3 Schemaを使います。このスキーマはカスタムリソースの構造とフィールド型を定義し、APIサーバーがリソースの作成・更新要求を検証するために使います。

CRD検証スキーマの例:
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

この例の`openAPIV3Schema`フィールドでは、次の検証ルールを定義します。
- `spec`フィールドは必須です。
- `spec`内では、`cronSpec`と`image`が必須です。
- `cronSpec`は文字列で、cron式のpatternに従う必要があります。
- `image`は文字列です。
- `replicas`は整数で、1以上10以下である必要があります。

OpenAPI v3 Schemaでは、次のような検証を定義できます。
- 必須フィールド
- データ型（string、number、boolean、object、arrayなど）
- 正規表現による文字列pattern
- 最小値、最大値などの数値範囲
- 配列の長さ
- enumで許可する値
- ネストしたobjectの構造

他の選択肢が適さない理由:
- JSON SchemaはOpenAPIの基礎ですが、KubernetesはOpenAPI v3 Schemaを使用します。
- XML SchemaはKubernetes APIでは使いません。
- GraphQL SchemaはGraphQL APIで使うもので、Kubernetes APIには使いません。
</details>

7. Kubernetesのカスタムリソースでstatusサブリソースを有効にする主な利点は何ですか？
   - A) リソース作成が速くなる
   - B) specとstatusの更新を分け、RBACで制御できる
   - C) バックアップと復旧の機能が自動で追加される
   - D) リソースバージョンの管理が簡単になる

<details>
<summary>回答を表示</summary>

**回答: B) specとstatusの更新を分け、RBACで制御できる**

**解説:**
statusサブリソースを有効にすると、specとstatusの更新を分けられ、RBAC（Role-Based Access Control）でアクセスを制御できます。

statusサブリソースを有効にする利点:

1. **責任の分離**:
   - `spec`フィールドには、利用者が指定する望ましい状態を定義します。
   - `status`フィールドには、コントローラーが観測した実際の状態を報告します。
   - これにより、利用者とコントローラーの役割が明確になります。

2. **RBACによる制御**:
   - statusの更新権限をコントローラーだけに付与し、通常の利用者には読み取り専用権限を与えられます。
   - status情報が許可なく変更されるのを防げます。

3. **競合への対処**:
   - specとstatusは別々に更新できますが、同じresourceVersionを共有するため、同時書き込みで409 Conflictが返る場合があります。
   - 最新のオブジェクトを読み直し、競合時は再試行またはreconcileしてください。

4. **Scaleサブリソースの利用**:
   - Scaleサブリソースは、`specReplicasPath`、`statusReplicasPath`と、任意の`labelSelectorPath`を使って別途設定します。
   - これにより、HPA（Horizontal Pod Autoscaler）など標準のKubernetesスケーリングツールを利用できます。

CRDでstatusサブリソースを有効にする例:
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
      status: {}
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
          status:
            type: object
            properties:
              phase:
                type: string
              message:
                type: string
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

コントローラーからstatusを更新する例:
```go
// Update status only
statusUpdate := instance.DeepCopy() // Preserve resourceVersion from a current read.
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(ctx, statusUpdate, metav1.UpdateOptions{})
```

他の選択肢が適さない理由:
- statusサブリソースを有効にしても、リソース作成は速くなりません。
- バックアップと復旧の機能は追加されません。
- リソースバージョンの管理はCRDの`versions`フィールドで行い、statusサブリソースとは直接関係ありません。
</details>

8. KubernetesのWebhook Conversionの主な目的は何ですか？
   - A) API要求を外部サービスに転送する
   - B) カスタムリソースの異なるバージョン間の変換を処理する
   - C) 認証トークンを異なる形式に変換する
   - D) ログデータを構造化形式に変換する

<details>
<summary>回答を表示</summary>

**回答: B) カスタムリソースの異なるバージョン間の変換を処理する**

**解説:**
Webhook Conversionは、カスタムリソースの異なるバージョン間の変換を処理します。複数バージョンのCRDをサポートし、バージョン間の移行を可能にします。

Webhook Conversionの主な特徴:

1. **複数バージョンのサポート**:
   - CRDは複数のAPIバージョン（例: v1alpha1、v1beta1、v1）を同時に提供できます。
   - バージョンごとに異なるschemaやfieldを定義できます。

2. **自動変換**:
   - APIサーバーは、クライアントが要求したバージョンと保存バージョン間の変換を処理します。
   - その処理中にWebhookが独自の変換ロジックを適用します。

3. **保存バージョンからの独立性**:
   - 保存バージョンを変更しても、以前のバージョンを使うクライアントは引き続き動作できます。
   - Webhookは提供対象の各バージョン間を双方向に変換します。ただし、`storage: true`を変更しても既存データは書き換わりません。古い`status.storedVersions`の項目を削除する前に、保存済みオブジェクトを移行してください。

CRDでWebhook Conversionを設定する例:
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
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cronSpec
            - image
            properties:
              cronSpec:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
  - name: v1beta1
    served: true
    storage: false
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cron
            - image
            properties:
              cron:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: webhook-system
          name: crd-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions:
      - v1
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

Conversion Webhookサーバー実装の例:
```go
// Include encoding/json, net/http, fmt and the Kubernetes types below in the server.
// apiextensionsv1 "k8s.io/apiextensions-apiserver/pkg/apis/apiextensions/v1"
// metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
// "k8s.io/apimachinery/pkg/runtime"
func convertCron(raw []byte, desired string) ([]byte, error) {
    var obj map[string]interface{}
    if err := json.Unmarshal(raw, &obj); err != nil { return nil, err }
    source, _ := obj["apiVersion"].(string)
    valid := func(v string) bool { return v == "stable.example.com/v1" || v == "stable.example.com/v1beta1" }
    if !valid(source) || !valid(desired) || obj["kind"] != "CronTab" {
        return nil, fmt.Errorf("unsupported CronTab conversion %q -> %q", source, desired)
    }
    spec, ok := obj["spec"].(map[string]interface{})
    if !ok { return nil, fmt.Errorf("spec object required") }
    if source != desired {
        oldField, newField := "cron", "cronSpec"
        if desired == "stable.example.com/v1beta1" { oldField, newField = newField, oldField }
        value, ok := spec[oldField]
        if !ok { return nil, fmt.Errorf("missing %s", oldField) }
        if _, collision := spec[newField]; collision { return nil, fmt.Errorf("ambiguous cron fields") }
        spec[newField] = value
        delete(spec, oldField)
    }
    obj["apiVersion"] = desired
    // Preserve metadata (including UID/resourceVersion), status and all other fields.
    return json.Marshal(obj)
}

func serveConvert(w http.ResponseWriter, r *http.Request) {
    var review apiextensionsv1.ConversionReview
    if r.Method != http.MethodPost || r.Body == nil {
        http.Error(w, "POST body required", http.StatusBadRequest); return
    }
    if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8<<20)).Decode(&review); err != nil ||
        review.APIVersion != "apiextensions.k8s.io/v1" || review.Kind != "ConversionReview" ||
        review.Request == nil || review.Request.UID == "" {
        http.Error(w, "Invalid ConversionReview v1", http.StatusBadRequest); return
    }
    response := &apiextensionsv1.ConversionResponse{
        UID: review.Request.UID, Result: metav1.Status{Status: "Success"},
    }
    for _, obj := range review.Request.Objects {
        raw, err := convertCron(obj.Raw, review.Request.DesiredAPIVersion)
        if err != nil {
            response.Result = metav1.Status{Status: "Failure", Message: err.Error()}
            response.ConvertedObjects = nil
            break
        }
        response.ConvertedObjects = append(response.ConvertedObjects, runtime.RawExtension{Raw: raw})
    }
    out := apiextensionsv1.ConversionReview{
        TypeMeta: metav1.TypeMeta{APIVersion: "apiextensions.k8s.io/v1", Kind: "ConversionReview"},
        Response: response,
    }
    w.Header().Set("Content-Type", "application/json")
    _ = json.NewEncoder(w).Encode(out)
}
```

他の選択肢が適さない理由:
- API要求を外部サービスへ転送するのはAPI Aggregationの役割です。
- 認証トークンの変換は認証プラグインが担います。
- ログデータの変換はログシステムが担います。
</details>

9. 次のうち、Kubernetes Operatorの開発を支援するframeworkではないものはどれですか？
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray

<details>
<summary>回答を表示</summary>

**回答: D) Kubespray**

**解説:**
KubesprayはKubernetes Operator開発を支援するframeworkではありません。Ansible playbookを使ってKubernetesクラスターをデプロイ、管理するツールであり、クラスターのインストールと設定を対象とします。

Operator開発に使われるframeworkには次のものがあります。

1. **Operator Framework**:
   - Red Hatが開発したOperator開発ツールキットです。
   - 主な構成要素:
     - Operator SDK: Operatorのscaffoldingと開発ツール
     - Operator Lifecycle Manager（OLM）: Operatorのインストールとアップグレード管理
     - Operator Metering: Operator利用状況のレポート
   - Go、Ansible、Helmを使ったOperator開発をサポートします。

2. **Kubebuilder**:
   - Kubernetes SIG（Special Interest Group）が開発したframeworkです。
   - Goでcontrollerを開発するためのSDKを提供します。
   - コード生成、CRD管理、テストツールを提供します。
   - controller-runtime libraryを基盤としています。

3. **Metacontroller**:
   - 軽量なWebhookベースのOperator frameworkです。
   - さまざまな言語でcontroller logicを実装できます。
   - 宣言的にcontrollerを定義できます。
   - 単純なcontrollerを素早く開発する用途に適しています。

各frameworkの機能比較:

| Framework | 主な言語 | 複雑さ | 機能 |
|-----------|----------|--------|------|
| Operator Framework | Go、Ansible、Helm | 中〜高 | 包括的なツールキット、多様な開発方法 |
| Kubebuilder | Go | 中 | 標準化されたpattern、コード生成ツール |
| Metacontroller | 言語に依存しない | 低 | Webhookベース、単純な実装 |

Kubebuilderを使ったOperator開発の例:
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

他の選択肢について:
- Operator Frameworkは、Red Hatの包括的なOperator開発ツールキットです。
- Kubebuilderは、Kubernetes SIGが開発したGoベースのcontroller開発frameworkです。
- Metacontrollerは、軽量なWebhookベースのOperator frameworkです。
</details>

10. KubernetesのCustom Resource Definition（CRD）とAggregated APIの主な違いは何ですか？
    - A) CRDはバージョン管理をサポートしないが、Aggregated APIはサポートする
    - B) CRDは検証schemaをサポートしないが、Aggregated APIはサポートする
    - C) CRDは簡単に実装できるが柔軟性に制限があり、Aggregated APIは実装が複雑な分、柔軟性が高い
    - D) CRDはcluster-scoped resourceだけを、Aggregated APIはnamespace-scoped resourceだけをサポートする

<details>
<summary>回答を表示</summary>

**回答: C) CRDは簡単に実装できるが柔軟性に制限があり、Aggregated APIは実装が複雑な分、柔軟性が高い**

**解説:**
CRDとAggregated APIの主な違いは、実装の複雑さと柔軟性のバランスです。CRDは簡単に実装できますが柔軟性に制限があり、Aggregated APIは実装が複雑な分、より高い柔軟性を提供します。

**CRDの特徴:**
- **実装が簡単**: 1つのYAMLファイルでAPIリソースを定義できます。
- **既存のAPIサーバーを使用**: 独立したAPIサーバーを実装する必要はありません。
- **柔軟性に制限**:
  - ストレージはetcdに限られます。
  - デフォルトAPIサーバーの動作を引き継ぎます。
  - CEL検証、admission/conversion Webhookに対応します。一方、独自ストレージや標準と異なるAPI動作には制約があります。
- **Webhookによる拡張**: validating Webhookやconversion Webhookなどで機能を拡張できます。

**Aggregated APIの特徴:**
- **実装が複雑**: 別のAPIサーバーを開発、デプロイする必要があります。
- **柔軟性が高い**:
  - 独自のストレージバックエンドを使用できます。
  - 複雑なビジネスロジックを実装できます。
  - 独自の認証・認可ロジックを実装できます。
  - 特殊な状態計算や変換ロジックを実装できます。
- **APIサーバーの全機能**: 標準Kubernetes APIサーバーの全機能を活用できます。

**選択基準:**

| 基準 | CRDを選ぶ場合 | Aggregated APIを選ぶ場合 |
|------|--------------|--------------------------|
| 実装の複雑さ | 低 — 単純なYAML定義 | 高 — 独立したAPIサーバーの開発が必要 |
| 開発期間 | 短い — 数分で実装可能 | 長い — APIサーバー全体の開発が必要 |
| 保守 | 容易 — 既存APIサーバーが管理 | 難しい — 独立したサービスの保守が必要 |
| ストレージの選択肢 | etcdのみ | 独自ストレージバックエンドも可能 |
| ビジネスロジック | 限定的 — controllerで実装 | 柔軟 — APIサーバー内に直接実装可能 |
| 性能 | 通常は良好 | 独自の最適化が可能 |
| 用途 | 単純なCRUD操作、標準的なpattern | 複雑なAPI動作、特殊な検証や変換 |

**利用例:**

CRDに適したケース:
- 単純なアプリケーション設定の管理
- 主な要件が基本的なCRUD操作である場合
- 迅速な試作と開発

Aggregated APIに適したケース:
- 外部データベースとの統合
- 複雑なデータ変換や検証
- 特殊な認証方式が必要な場合
- 高性能または特殊用途のAPI

他の選択肢が適さない理由:
- CRDはバージョン管理をサポートします（Aは誤りです）。
- CRDはOpenAPI v3 Schemaによる検証schemaをサポートします（Bは誤りです）。
- CRDとAggregated APIの両方がcluster-scopedとnamespace-scopedのresourceをサポートします（Dは誤りです）。
</details>

> `cronSpec`の正規表現が確認するのは、数字、アスタリスク、stepで構成される限定的な5フィールド形式だけです。範囲、リスト、名前、すべての有効な時刻値までは検証しません。controllerまたはWebhookに実際のcron parserを追加してください。CRDだけでは定期実行処理は行われません。

## 記述式問題

1. CustomResourceDefinition（CRD）を使ってカスタムリソースを定義する方法と、検証ルールを設定する方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**CustomResourceDefinition（CRD）の定義方法:**

CRDはKubernetes APIを拡張して新しいリソース型を定義する仕組みです。CRDを作成すると、新しいREST API endpointが作られ、`kubectl`などの標準ツールでそのリソースを管理できます。

**1. CRDの基本構造:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: <plural>.<group>
spec:
  group: <api-group>
  names:
    kind: <kind-name>
    plural: <plural-name>
    singular: <singular-name>
    shortNames:
    - <short-name>
  scope: Namespaced
  versions:
  - name: <version>
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required:
        - spec
        properties:
          spec:
            type: object
            required:
            - cronSpec
            - image
            properties:
              cronSpec:
                type: string
              image:
                type: string
              replicas:
                type: integer
          status:
            type: object
            properties:
              phase:
                type: string
```

**2. 検証ルールの設定:**

CRDの検証ルールは`openAPIV3Schema`フィールドに設定します。このschemaはOpenAPI v3形式に従い、リソースの構造とフィールド型を定義します。

**基本的な検証ルールの例:**

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

**3. 高度な検証機能:**

OpenAPI v3 Schemaでは、次のような検証機能を使えます。

- **必須フィールド**: フィールド名を`required`配列に追加します。
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **データ型**: `type`フィールドでデータ型を指定します。
  ```yaml
  type: string  # Choose one supported type, not a pipe-separated union.
  ```

- **文字列の制約**: 文字列の長さやpatternを検証します。
  ```yaml
  minLength: 3
  maxLength: 64
  pattern: '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
  ```

- **数値の制約**: 数値の範囲を検証します。
  ```yaml
  minimum: 0
  maximum: 100
  multipleOf: 5
  ```

- **配列の制約**: 配列の長さと要素を検証します。
  ```yaml
  minItems: 1
  maxItems: 10
  x-kubernetes-list-type: set
  items:
    type: string
  ```

- **enum値**: 許可する値の一覧を指定します。
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **デフォルト値**: フィールドのデフォルト値を指定します。
  ```yaml
  default: "default-value"
  ```

- **Mapの値**: 型付きのMap要素を定義します。CRDでは`additionalProperties: false`を使えません。通常、未知のフィールドはpruneされます。
  ```yaml
  additionalProperties:
    type: string
  ```

**4. CRDの全体例:**

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

**5. CRDの適用と使用:**

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

**6. 検証ルールのテスト:**

無効な値を使ってリソースを作成すると、検証エラーになります。

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

このコマンドでは、次のようなエラーが返ります。
APIサーバーはCRDのschema検証によって、無効な`cronSpec`または`replicas`を拒否します。この例では別のadmission Webhookをインストールしていません。エラーの正確な文面はバージョンによって異なります。

**7. ベストプラクティス:**

- 明確で詳細なschemaを定義する
- 必須フィールドを明示する
- 適切なデフォルト値を設定する
- 文字列patternと数値範囲を適切に限定する
- statusサブリソースを有効にする
- 追加のprinter columnを設定する
- バージョン管理方針を決める
</details>

2. Kubernetes Operatorパターンの基本概念と、Operatorを実装する一般的な方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Kubernetes Operatorパターンの基本概念:**

Operatorパターンは、アプリケーション固有の運用知識をソフトウェアに組み込み、複雑なアプリケーションを自動管理するKubernetesの拡張メカニズムです。人が複雑なシステムを運用する方法を模倣します。

**1. 基本概念:**

- **宣言的な管理**: 利用者が望ましい状態を宣言し、Operatorが現在の状態をその状態に近づけます。
- **ドメイン知識のコード化**: 特定のアプリケーションに関する運用知識とベストプラクティスを組み込みます。
- **調整ループ**: 実際の状態を継続的に観察し、望ましい状態に調整します。
- **カスタムリソース**: アプリケーション固有の設定と状態を保存します。
- **コントローラー**: カスタムリソースの変更を監視し、必要な処理を実行します。

**2. Operatorの一般的な機能:**

- **インストールとアップグレード**: アプリケーション構成要素をデプロイし、バージョンを更新します。
- **自動復旧**: 障害を検出し、復旧処理を行います。
- **バックアップと復元**: データのバックアップと復元を自動化します。
- **スケーリング**: ワークロードの要件に合わせて拡大、縮小します。
- **設定管理**: アプリケーション固有の設定変更を処理します。
- **運用の自動化**: データベースのcompactやindex再構築など、定型作業を自動化します。

**Operatorの実装方法:**

**1. Operator SDKを使う:**

[Operator SDK](https://sdk.operatorframework.io/)はRed Hat Operator Frameworkの一部で、Operator開発を簡単にするツールです。

```bash
: "${OPERATOR_IMAGE:?Set a registry image tag or digest you control}"
# Install a supported released SDK/CLI and verify its checksum before scaffolding.

# Create Go-based operator project
operator-sdk init --domain example.com --repo github.com/example/my-operator

# Create API
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --resource --controller

# Create CRD
make manifests

# Build and deploy operator
make docker-build docker-push IMG="$OPERATOR_IMAGE"
make deploy IMG="$OPERATOR_IMAGE"
```

**2. Kubebuilderを使う:**

[Kubebuilder](https://book.kubebuilder.io/)はKubernetes SIGが開発したframeworkで、controller開発用ツールを提供します。

```bash
: "${OPERATOR_IMAGE:?Set a registry image tag or digest you control}"
# Install a supported released SDK/CLI and verify its checksum before scaffolding.

# Initialize project
kubebuilder init --domain example.com --repo github.com/example/my-operator

# Create API
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# Create CRD and deploy controller
make install
make deploy IMG="$OPERATOR_IMAGE"
```

**3. Controllerを実装する:**

Operatorの中核はreconciliation関数です。この関数はカスタムリソースの現在の状態を確認し、必要な処理を実行します。

```go
// Uses the scaffold's client.Client and Scheme. Import controllerutil and sort.
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    var myApp appsv1alpha1.MyApp
    if err := r.Get(ctx, req.NamespacedName, &myApp); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }
    if !myApp.DeletionTimestamp.IsZero() { return ctrl.Result{}, nil }
    deployment := &appsv1.Deployment{ObjectMeta: metav1.ObjectMeta{Name: myApp.Name, Namespace: myApp.Namespace}}
    _, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
        if deployment.UID != "" && !metav1.IsControlledBy(deployment, &myApp) {
            return fmt.Errorf("refusing to modify Deployment owned by another actor")
        }
        labels := map[string]string{"myapp.example.com/owner-uid": string(myApp.UID)}
        if deployment.Spec.Selector == nil {
            deployment.Spec.Selector = &metav1.LabelSelector{MatchLabels: labels}
        }
        if deployment.Spec.Template.Labels == nil { deployment.Spec.Template.Labels = map[string]string{} }
        deployment.Spec.Template.Labels["myapp.example.com/owner-uid"] = string(myApp.UID)
        size := myApp.Spec.Size
        deployment.Spec.Replicas = &size
        keys := []string{}
        for key := range myApp.Spec.Config { keys = append(keys, key) }
        sort.Strings(keys) // Stable output avoids unnecessary updates.
        env := []corev1.EnvVar{}
        for _, key := range keys { env = append(env, corev1.EnvVar{Name: key, Value: myApp.Spec.Config[key]}) }
        // This operator owns its application container; update image as well as replicas.
        deployment.Spec.Template.Spec.Containers = []corev1.Container{{
            Name: "myapp", Image: myApp.Spec.Image, Env: env,
            Ports: []corev1.ContainerPort{{ContainerPort: 8080, Name: "http"}},
        }}
        return ctrl.SetControllerReference(&myApp, deployment, r.Scheme)
    })
    if err != nil { return ctrl.Result{}, err }
    if myApp.Status.AvailableReplicas != deployment.Status.AvailableReplicas {
        myApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
        if err := r.Status().Update(ctx, &myApp); err != nil { return ctrl.Result{}, err }
    }
    return ctrl.Result{}, nil
}

func (r *MyAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&appsv1alpha1.MyApp{}).
        Owns(&appsv1.Deployment{}).
        Complete(r)
}
```

**4. Custom Resource Definition:**

Operatorが管理するカスタムリソースのAPIを定義します。

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

**5. AnsibleまたはHelmベースのOperator:**

Operator SDKはGoだけでなく、AnsibleまたはHelmを使うOperator開発もサポートします。

**AnsibleベースのOperator:**
```bash
# Create Ansible-based operator
operator-sdk init --plugins=ansible --domain example.com
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --generate-role

# Edit roles/myapp/tasks/main.yml
```

**HelmベースのOperator:**
```bash
# Create Helm-based operator
operator-sdk init --plugins=helm --domain example.com --helm-chart=<chart-name>
```

**6. Operatorのデプロイとテスト:**

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

**7. Operatorの成熟度レベル:**

Operator成熟度モデルでは、Operatorの機能を次の段階に分けます。

1. **Basic Install**: アプリケーションのインストールと設定
2. **Seamless Upgrades**: バージョン間の自動アップグレード
3. **Full Lifecycle**: バックアップ、復元、障害復旧など
4. **Deep Insights**: 自動スケーリング、チューニングなど
5. **Auto Pilot**: 監視に基づく自動最適化

**8. ベストプラクティス:**

- 小さな機能から始め、段階的に実装する
- エラー処理とログを十分に整備する
- 冪等性を確保する（同じ入力に対して同じ結果になる）
- owner referenceを設定し、リソース階層とガベージコレクションを管理する
- status更新で進捗を報告する
- 単体テストと統合テストを書く
- 分かりやすいドキュメントを用意する
</details>

3. KubernetesのAdmission Webhookの種類と、それぞれの用途を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Kubernetes Admission Webhookの種類と用途:**

Admission Webhookは、Kubernetes APIサーバーが要求を永続ストレージ（etcd）に保存する前に、要求を受け取り変更または検証できる仕組みです。Mutating WebhookとValidating Webhookの2種類に大別されます。

**1. Mutating Webhook:**

Mutating WebhookはAPIサーバーに届いた要求オブジェクトを変更できます。Validating Webhookより先に実行されます。

**主な特徴:**
- 要求オブジェクトを変更できます。
- 複数のMutating Webhookが順番に実行されます。
- 各Webhookは、直前のWebhookが変更したオブジェクトを受け取ります。

**設定例:**
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
      name: webhook-server
      path: "/mutate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

**一般的な用途:**

1. **サイドカーコンテナの注入:**
   - IstioやLinkerdなどのサービスメッシュでプロキシサイドカーを自動注入する
   - ログ収集や監視用のサイドカーを追加する
   - 例: Istioのsidecar injectorはPodの作成時にEnvoyプロキシコンテナを追加します。

2. **デフォルト値の設定:**
   - リソース要求量と上限を自動設定する
   - security contextのデフォルト値を適用する
   - ラベルとannotationを自動追加する
   - 例: すべてのPodにデフォルトのCPUとメモリー要求量を設定する

3. **イメージポリシーの適用:**
   - イメージレジストリURLを変更する
   - イメージtagをdigestに変換する
   - 例: `nginx:latest`を`internal-registry.example.com/nginx:1.30.6`に変更する

4. **ボリュームの変更:**
   - デフォルトのvolume mountを追加する
   - ConfigMapやSecretを自動的にmountする
   - 例: ServiceAccount admissionは、`automountServiceAccountToken: false`で無効にされていない限り、投影tokenをすでに注入します。この明示的な無効化設定を上書きしないでください。

5. **Podのネットワーク設定:**
   - デフォルトのネットワーク設定を追加する
   - DNS設定を変更する
   - 例: 特定namespace内のすべてのPodに特定のDNS設定を適用する

**2. Validating Webhook:**

Validating WebhookはAPIサーバーに届いた要求を検証し、許可または拒否できます。Mutating Webhookの後に実行されます。

**主な特徴:**
- 要求オブジェクトを変更できません。
- 要求を許可または拒否するだけです。
- 複数のValidating Webhookは並列に実行されます。
- 一致したWebhookがすべて許可する必要があります。呼び出しエラーやtimeout時は`failurePolicy`に従うため、応答がなくても`Ignore`なら要求が許可される場合があります。

**設定例:**
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
      name: webhook-server
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

**一般的な用途:**

1. **セキュリティポリシーの適用:**
   - 特権コンテナを禁止する
   - rootユーザーでの実行を禁止する
   - host network、PID、IPCの使用を制限する
   - 例: privileged modeで実行するPodを拒否する

2. **リソース制約の検証:**
   - リソース要求量と上限を必須にする
   - リソース上限を適用する
   - QoS classを適用する
   - 例: memory limitがないPodを拒否する

3. **イメージポリシーの検証:**
   - 承認済みレジストリだけを許可する
   - `latest` tagを禁止する
   - 脆弱性スキャン結果を確認する
   - 例: 公式レジストリのイメージだけを許可する

4. **ラベルとannotationの検証:**
   - 必須ラベルを確認する
   - ラベル形式を検証する
   - 例: すべてのPodで`app`と`environment`ラベルを必須にする

5. **namespaceごとのポリシー:**
   - namespaceごとのリソース上限を設定する
   - namespaceごとに機能を制限する
   - 例: production namespaceにより厳格なポリシーを適用する

**3. Webhookの実装方法:**

Admission Webhookは、HTTPS endpointを提供するServiceとして実装します。Serviceは`AdmissionReview`要求を受け取り、処理して`AdmissionResponse`を返します。

**Webhookサーバーの基本実装例（Go）:**

```go
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"
    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/api/resource"
)

func readPodReview(w http.ResponseWriter, r *http.Request) (*admissionv1.AdmissionRequest, *corev1.Pod, bool) {
    if r.Method != http.MethodPost || r.Body == nil {
        http.Error(w, "POST body required", http.StatusBadRequest)
        return nil, nil, false
    }
    var review admissionv1.AdmissionReview
    if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 2<<20)).Decode(&review); err != nil {
        http.Error(w, "Invalid AdmissionReview JSON", http.StatusBadRequest)
        return nil, nil, false
    }
    req := review.Request
    if review.APIVersion != "admission.k8s.io/v1" || review.Kind != "AdmissionReview" || req == nil || req.UID == "" {
        http.Error(w, "AdmissionReview v1 request and UID required", http.StatusBadRequest)
        return nil, nil, false
    }
    if req.Kind.Group != "" || req.Kind.Version != "v1" || req.Kind.Kind != "Pod" ||
        (req.Operation != admissionv1.Create && req.Operation != admissionv1.Update) {
        http.Error(w, "Only Pod CREATE/UPDATE is supported", http.StatusBadRequest)
        return nil, nil, false
    }
    var pod corev1.Pod
    if err := json.Unmarshal(req.Object.Raw, &pod); err != nil {
        http.Error(w, "Invalid Pod JSON", http.StatusBadRequest)
        return nil, nil, false
    }
    return req, &pod, true
}

func writeReview(w http.ResponseWriter, response admissionv1.AdmissionResponse) {
    review := admissionv1.AdmissionReview{
        TypeMeta: metav1.TypeMeta{APIVersion: "admission.k8s.io/v1", Kind: "AdmissionReview"},
        Response: &response,
    }
    data, err := json.Marshal(review)
    if err != nil {
        http.Error(w, "Response encoding failed", http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    _, _ = w.Write(data)
}

func writePatch(w http.ResponseWriter, req *admissionv1.AdmissionRequest, patches []map[string]interface{}) {
    response := admissionv1.AdmissionResponse{UID: req.UID, Allowed: true}
    if len(patches) > 0 {
        data, err := json.Marshal(patches)
        if err != nil {
            http.Error(w, "Patch encoding failed", http.StatusInternalServerError)
            return
        }
        patchType := admissionv1.PatchTypeJSONPatch
        response.PatchType, response.Patch = &patchType, data
    }
    writeReview(w, response)
}

func deny(w http.ResponseWriter, req *admissionv1.AdmissionRequest, message string) {
    writeReview(w, admissionv1.AdmissionResponse{
        UID: req.UID, Allowed: false,
        Result: &metav1.Status{Status: "Failure", Reason: metav1.StatusReasonForbidden, Code: 403, Message: message},
    })
}
var sidecarImage string

func mutateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    // This example targets explicitly declared Linux Pods on CREATE only.
    if req.Operation != admissionv1.Create || pod.Spec.OS == nil || pod.Spec.OS.Name != corev1.Linux {
        writePatch(w, req, nil)
        return
    }
    if sidecarImage == "" {
        deny(w, req, "Configure a tested SIDE_CAR_IMAGE first")
        return
    }
    changed, foundVolume, foundSidecar := false, false, false
    for _, volume := range pod.Spec.Volumes {
        if volume.Name == "shared-data" {
            if volume.EmptyDir == nil {
                deny(w, req, "shared-data is reserved for an emptyDir volume")
                return
            }
            foundVolume = true
        }
    }
    if !foundVolume {
        pod.Spec.Volumes = append(pod.Spec.Volumes, corev1.Volume{
            Name: "shared-data", VolumeSource: corev1.VolumeSource{EmptyDir: &corev1.EmptyDirVolumeSource{}},
        })
        changed = true
    }
    for i := range pod.Spec.Containers {
        c := &pod.Spec.Containers[i]
        if c.Name == "monitoring-sidecar" {
            if c.Image != sidecarImage {
                deny(w, req, "monitoring-sidecar name is reserved")
                return
            }
            foundSidecar = true
        }
        mounted := false
        for _, mount := range c.VolumeMounts {
            if mount.MountPath == "/var/monitoring" {
                if mount.Name != "shared-data" || mount.SubPath != "" || mount.SubPathExpr != "" {
                    deny(w, req, "/var/monitoring is reserved for shared-data")
                    return
                }
                mounted = true
            }
        }
        if !mounted {
            c.VolumeMounts = append(c.VolumeMounts, corev1.VolumeMount{Name: "shared-data", MountPath: "/var/monitoring"})
            changed = true
        }
    }
    if !foundSidecar {
        pod.Spec.Containers = append(pod.Spec.Containers, corev1.Container{
            Name: "monitoring-sidecar", Image: sidecarImage,
            VolumeMounts: []corev1.VolumeMount{{Name: "shared-data", MountPath: "/var/monitoring", ReadOnly: true}},
            Resources: corev1.ResourceRequirements{
                Requests: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("50m"), corev1.ResourceMemory: resource.MustParse("50Mi")},
                Limits: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("100m"), corev1.ResourceMemory: resource.MustParse("100Mi")},
            },
        })
        changed = true
    }
    if !changed { writePatch(w, req, nil); return }
    // Whole-array add also works when volumes was absent; preserve all existing entries.
    writePatch(w, req, []map[string]interface{}{
        {"op": "add", "path": "/spec/volumes", "value": pod.Spec.Volumes},
        {"op": "add", "path": "/spec/containers", "value": pod.Spec.Containers},
    })
}

func validateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    contexts := []*corev1.SecurityContext{}
    for _, c := range pod.Spec.Containers { contexts = append(contexts, c.SecurityContext) }
    for _, c := range pod.Spec.InitContainers { contexts = append(contexts, c.SecurityContext) }
    for _, c := range pod.Spec.EphemeralContainers { contexts = append(contexts, c.SecurityContext) }
    for _, sc := range contexts {
        if sc != nil && sc.Privileged != nil && *sc.Privileged {
            deny(w, req, "Privileged containers are not allowed")
            return
        }
    }
    writeReview(w, admissionv1.AdmissionResponse{UID: req.UID, Allowed: true})
}

func main() {
    sidecarImage = os.Getenv("SIDE_CAR_IMAGE")
    if sidecarImage == "" { log.Fatal("Set SIDE_CAR_IMAGE to a tested Linux image tag/digest") }
    mux := http.NewServeMux()
    mux.HandleFunc("/mutate", mutateHandler)
    mux.HandleFunc("/validate", validateHandler)
    server := &http.Server{Addr: ":8443", Handler: mux, ReadHeaderTimeout: 5*time.Second}
    log.Fatal(server.ListenAndServeTLS("/etc/webhook/certs/tls.crt", "/etc/webhook/certs/tls.key"))
}
```

**4. Webhookのデプロイと設定:**

上記のサーバー全体をbuildし、serverとsidecarのimage placeholderを置き換え、`webhook-system`と`webhook-server-tls`を作成してください。サーバー証明書は`webhook-server.webhook-system.svc`（および使用する別名Service）を対象にし、その署名CAを`caBundle`に含めます。sidecar imageはアプリケーションのfilesystem権限に対応する必要があります。これは通常のsidecarの例です。Job向けのshutdownやnative sidecarの動作は別途設定してください。

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
        image: example/webhook-server:REPLACE_WITH_TESTED_RELEASE
        env:
        - name: SIDE_CAR_IMAGE
          value: example/monitoring-agent:REPLACE_WITH_TESTED_RELEASE
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

**5. ベストプラクティス:**

- **性能の最適化**: WebhookはAPIサーバーのrequest path上で実行されるため、すばやく応答する必要があります。
- **エラー処理**: Webhookサーバーの障害時の動作を考慮し、`failurePolicy`を適切に設定します。
- **適用範囲の限定**: 必要なリソースと操作だけにWebhookを適用します。
- **テスト**: さまざまな状況でWebhookの動作を十分にテストします。
- **監視**: Webhookサーバーの性能とエラーを監視します。
- **バージョン管理**: 実装済みのAdmissionReview versionだけをadvertiseし、要求と同じversionで応答します。
</details>

## ハンズオン問題

1. 次の要件を満たすCustomResourceDefinition（CRD）を作成してください。
   - API Group: webapp.example.com
   - Version: v1
   - Kind: WebApp
   - Scope: Namespaced
   - 必須フィールド: spec.image、spec.replicas
   - 検証ルール: replicasは1以上10以下の整数
   - statusサブリソースを有効にする

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

このCRDには次の特徴があります。

1. **基本情報**:
   - API Group: `webapp.example.com`
   - Version: `v1`
   - Kind: `WebApp`
   - Scope: `Namespaced`

2. **schemaによる検証**:
   - `spec`フィールドは必須です。
   - `spec.image`と`spec.replicas`は必須フィールドです。
   - `spec.replicas`は1以上10以下の整数である必要があります。
   - `spec.port`はデフォルト値80を持つ任意フィールドです。
   - `spec.env`は環境変数の配列を定義する任意フィールドです。

3. **statusサブリソース**:
   - statusサブリソースを有効にして、コントローラーからstatusを更新できるようにします。
   - `status.availableReplicas`と`status.phase`フィールドを定義します。

4. **追加printer column**:
   - `kubectl get webapps`を実行すると、Replicas、Image、Age columnが表示されます。

5. **名前の設定**:
   - 複数形: `webapps`
   - 単数形: `webapp`
   - Kind: `WebApp`
   - 短縮名: `wa`

このCRDを使うと、次のようなカスタムリソースを作成できます。

```yaml
apiVersion: webapp.example.com/v1
kind: WebApp
metadata:
  name: my-webapp
  namespace: default
spec:
  image: nginx:1.30.6
  replicas: 3
  port: 80
  env:
    - name: ENV_VAR1
      value: "value1"
    - name: ENV_VAR2
      value: "value2"
```

コントローラーはこのリソースを監視してstatusを更新できます。

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. 次の要件を満たすMutating Admission Webhook設定を作成してください。
   - `spec.os.name: linux`を明示しているPodのCREATE要求にsidecarを追加する
   - 特定のnamespace（`monitoring`）だけに適用する
   - Webhook Service: webhook-service.webhook-system.svc
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
      kubernetes.io/metadata.name: monitoring
  matchConditions:
  - name: explicit-linux-pod
    expression: "has(object.spec.os) && object.spec.os.name == 'linux'"
  admissionReviewVersions: ["v1"]
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
    kubernetes.io/metadata.name: monitoring
```

この設定の特徴:

1. **Webhookの設定**:
   - 名前: `sidecar-injector`
   - Webhook Service: `webhook-service.webhook-system.svc`
   - Path: `/mutate`

2. **適用範囲**:
   - API Group: `""`（core API group）
   - API Version: `v1`
   - Operation: `CREATE`（Podの作成時のみ適用）
   - Resource: `pods`
   - Scope: `Namespaced`

3. **namespace selector**:
   - `kubernetes.io/metadata.name: monitoring` labelを持つnamespaceだけに適用します。
   - APIサーバーは`monitoring` namespaceに、この変更できない名前labelを設定します。

4. **追加設定**:
   - `admissionReviewVersions`: サポートするAdmissionReview API version
   - `sideEffects`: Webhookによる副作用がないこと
   - `timeoutSeconds`: Webhook応答の待機時間
   - `failurePolicy`: Webhook障害時に要求を拒否する設定

Webhookサーバーは、次のような処理を実装します。

上記のサーバー全体にある`mutateHandler`と共通のrequest/response helperを使います。volume配列がない場合は作成し、既存の項目を保持し、重複注入を防ぎます。また、`shared-data`をアプリケーションとsidecarの両方にmountします。予約済みの名前またはpathが競合する場合は要求を拒否します。

このWebhookは、`monitoring` namespaceで作成されるPodのうち、`spec.os.name: linux`を宣言したものにmonitoring sidecarを追加します。sidecarはmonitoring agent imageを使い、共有volumeをmountしてメインコンテナとデータを共有します。
</details>

> Controllerのコード例には、生成済みのproject type、client、RBACが必要です。Deploymentの所有関係を確認し、image、replicas、環境設定をreconcileします。また、status変更を監視する`Owns` watchを使います。削除前にfinalizerで外部リソースをcleanupしてください。このレビューではKubernetesまたはAWSへのデプロイは実行していません。

## 確認用リンク

- https://kubernetes.io/releases/
- https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/
- https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/
- https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/
- https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/
- https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/
- https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/
- https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/scheduler/apis/config/types.go
- https://github.com/kubernetes/cloud-provider-aws/blob/master/docs/prerequisites.md
- https://github.com/kubernetes/cloud-provider-aws/blob/master/examples/existing-cluster/base/aws-cloud-controller-manager-daemonset.yaml
- https://github.com/kubernetes-sigs/kubebuilder/blob/master/README.md
- https://github.com/operator-framework/operator-sdk/blob/master/README.md
- https://github.com/NVIDIA/k8s-device-plugin/blob/main/README.md
- https://github.com/jaegertracing/jaeger-operator/blob/main/README.md
- https://istio.io/latest/blog/2024/in-cluster-operator-deprecation-announcement/
- https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
- https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html
- https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html
- https://github.com/aws-controllers-k8s/community/blob/main/docs/content/docs/user-docs/install.md
- https://github.com/aws-controllers-k8s/s3-controller/blob/main/helm/values.yaml
