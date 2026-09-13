# Kubernetes 拡張メカニズム

> **最終更新**: September 12, 2026

## 拡張ポイントの選択

Kubernetes は API とワークロードの動作を拡張する方法を複数提供しています。CRD を登録することと、その動作を実装することは別物です。

| メカニズム | 役割 | 運用上の要件 |
| --- | --- | --- |
| CRD + controller | カスタム API と desired-state の reconciliation | スキーマ、reconciliation、RBAC、status と削除処理 |
| API aggregation | リクエストを別の API server へ委譲 | APIService、TLS、委譲された認証/認可、discovery/storage |
| Admission policy/webhook | API リクエストの検証または変更 | スコープ、失敗時の処理、CEL または webhook の可用性 |
| Scheduler plugin/extender | filtering、scoring、binding の拡張 | 互換性のある scheduler バイナリ、登録/設定、失敗時の処理 |
| CNI | コンテナネットワーキング | 実際のインターフェース、IPAM、ルート、クリーンアップ |
| CSI | Volume のライフサイクルと node でのマウント | 機能に応じた RPC とバックエンド/node 操作 |

選択した API、ライブラリ、ディストリビューションの互換性を確認してください。現行の controller-runtime 0.25.0 は Go 1.26 と Kubernetes Go モジュール 0.37.0 を使用します。以下の scheduler インターフェースに関する記述は Kubernetes 1.36.2 のソースに対して確認したものです。scheduler-plugins 0.35.7 がそれと互換であると想定しないでください。

## CRD とインスタンス

CRD は OpenAPI v3 構造を用いてカスタム API を定義します。required フィールドはそれを含むレベルに適用されるため、トップレベルの spec と spec.image の両方を明示的に required に指定してください。status はその subresource を通じて管理し、scale では実際の replicas と availableReplicas を区別してください。controller がなければ、この API はデータを保存するだけで Deployment を作成しません。

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
    shortNames: [wa]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [image]
              properties:
                replicas:
                  type: integer
                  default: 1
                  minimum: 1
                  maximum: 5
                image:
                  type: string
                  minLength: 1
                port:
                  type: integer
                  default: 8080
                  minimum: 1
                  maximum: 65535
            status:
              type: object
              properties:
                replicas:
                  type: integer
                availableReplicas:
                  type: integer
                selector:
                  type: string
                observedGeneration:
                  type: integer
                  format: int64
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
          labelSelectorPath: .status.selector
```

```yaml
apiVersion: apps.example.com/v1
kind: WebApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  port: 8080
```

controller は observed state から status.replicas、availableReplicas、selector、observedGeneration を設定しなければなりません。status が欠落していたり古いままであることは成功ではありません。served な API バージョンが複数ある場合は、storage バージョン、status.storedVersions、conversion を確認してください。conversion webhook は必要な変換を実装しなければならず、バージョン名を変更してもデータは移行されません。

## client-go、controller-runtime、Operator

client-go はクライアント、informer/キャッシュ、workqueue を提供します。1 回だけ List してから Watch するのは完全な controller ではありません。resourceVersion の連続性、watch のクローズ、410 Gone、再接続、キャッシュ同期、さらに context のキャンセルとクリーンアップを扱う必要があります。

controller-runtime は manager、キャッシュ/クライアント、workqueue、leader election、reconciliation パターンを提供します。カスタム WebApp の Go 型と scheme 登録を生成または用意し、選択したライブラリバージョンに対してコンパイルしてください。存在しない example.com/api 型や appsv1.WebApp への参照は、実行可能な実装にはなりません。

以下は **擬似コード** であり、その関数とデプロイ設定は別途実装する必要があります。

```text
Reconcile(namespace, name):
  read WebApp; return successfully if it no longer exists
  if deletionTimestamp is set:
    finish idempotent external cleanup under the declared retention policy
    remove only this controller's finalizer after cleanup succeeds
    return
  persist a required finalizer before creating external resources
  read the desired child Deployment
  reject conflicting ownership; do not silently adopt another controller's object
  reconcile image, replicas, ports and owned fields without needless updates
  handle conflicts by rereading; do not index a possibly empty container list
  observe children and patch status only when it changes
  report failure/readiness and requeue when another observation is needed
```

ownerReferences は name だけでなく、UID、namespace、スコープの制約にも一致しなければなりません。同名の Deployment を無条件に更新すると、別の controller のワークロードを変更してしまう可能性があります。ガベージコレクションは propagation、owner、finalizer に依存します。ownerReference は任意の外部 AWS データをクリーンアップするものではありません。

Operator はドメイン知識を実装するものであり、フェイルオーバー、ローリングアップグレード、バックアップが自動的に安全になるわけではありません。データベースの設計では、primary の fencing、quorum、レプリカの追従、WAL/バックアップのリストアテスト、スキーマ互換性、disruption budget、シャットダウン順序が必要です。

公式の Operator SDK 1.42.3 のインストール手順に従って、OS/アーキテクチャとチェックサムを選択してください。古い amd64 専用の 1.25.0 バイナリをどこにでもインストールしないでください。init/create api/make manifests は選択した SDK/plugin に対して検証し、生成されたプロジェクトをコンパイル/テストしたうえで、イメージのビルド/プッシュとデプロイを別途行ってください。

## API Aggregation

APIService は group/version のパスを拡張 API server の Service にルーティングします。その server には TLS、discovery、storage、および list/watch などの API 動作が必要です。front-proxy 証明書の CA/CN を検証し、転送されるユーザー identity を巡る信頼境界を維持し、委譲された認可を設定してください。

metrics-server の実際の API バージョンは、インストール済みの discovery を調べて確認してください。実在しない v1.metrics.k8s.io の APIService や、既定値としての insecureSkipTLSVerify:true を使用しないでください。group/version、Service、caBundle は実際の server と一致しなければなりません。単純な HTTP ハンドラーや空の API group は、完全な Kubernetes API server ではありません。

## Admission Policy と Webhook

ValidatingAdmissionPolicy は Kubernetes 1.30 以降で stable であり、CEL による検証をプロセス内で実行します。以下の policy/binding は、production namespace の Deployment および deployments/scale リクエストに対して replicas を 1〜5 に制限します。HPA や kubectl scale による更新もチェックされるため、HPA の maxReplicas をこの制限に合わせてください。namespace 名は任意の環境ラベルと同等ではありません。policy を適用する前に運用への影響を確認してください。

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: reviewed-replica-limit
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [apps]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [deployments, deployments/scale]
  validations:
    - expression: "!has(object.spec.replicas) || (object.spec.replicas >= 1 && object.spec.replicas <= 5)"
      message: replicas must be between 1 and 5
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: reviewed-replica-limit-production
spec:
  policyName: reviewed-replica-limit
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: production
```

Validating webhook はリクエストを許可または拒否し、mutating webhook は JSON Patch を返すことができます。応答は同じ AdmissionReview バージョンとリクエストの UID を使用してください。patchType は JSONPatch であり、patch のバイト列は JSON 内で Base64 エンコードされます。

次の Go ハンドラーは、Pod の CREATE 時に説明用のラベルを追加します。labels マップが存在しない/null の場合は作成し、既存のラベルは保持し、値が既に一致している場合は patch を省略します。サイズ、メソッド、コンテンツタイプ、バージョン、UID、null のリクエスト/オブジェクトをチェックします。このラベルは実際にサイドカーを注入するものではありません。

### テスト済みの Webhook コード

examples/platform/extensions/webhook には go.mod、この実装、およびそのテストが含まれています。Go 1.25 の標準ライブラリのみを使用しています。構造体は使用する AdmissionReview のフィールドを宣言し、それ以外のフィールドは無視します。

```go
package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"mime"
	"net/http"
	"time"
)

type groupVersionResource struct {
	Group    string `json:"group"`
	Version  string `json:"version"`
	Resource string `json:"resource"`
}

type admissionRequest struct {
	UID         string               `json:"uid"`
	Operation   string               `json:"operation"`
	Resource    groupVersionResource `json:"resource"`
	SubResource string               `json:"subResource"`
	Object      json.RawMessage      `json:"object"`
}

type admissionResponse struct {
	UID       string `json:"uid"`
	Allowed   bool   `json:"allowed"`
	Patch     []byte `json:"patch,omitempty"`
	PatchType string `json:"patchType,omitempty"`
}

type review struct {
	APIVersion string             `json:"apiVersion"`
	Kind       string             `json:"kind"`
	Request    *admissionRequest  `json:"request,omitempty"`
	Response   *admissionResponse `json:"response,omitempty"`
}

type podInput struct {
	APIVersion string `json:"apiVersion"`
	Kind       string `json:"kind"`
	Metadata   *struct {
		Labels map[string]string `json:"labels"`
	} `json:"metadata"`
}

type patchOperation struct {
	Op    string `json:"op"`
	Path  string `json:"path"`
	Value any    `json:"value"`
}

func mutate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "POST required", http.StatusMethodNotAllowed)
		return
	}
	mediaType, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
	if err != nil || mediaType != "application/json" {
		http.Error(w, "application/json required", http.StatusUnsupportedMediaType)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	defer r.Body.Close()
	decoder := json.NewDecoder(r.Body)
	var incoming review
	if err := decoder.Decode(&incoming); err != nil {
		http.Error(w, "invalid admission body", http.StatusBadRequest)
		return
	}
	if err := decoder.Decode(new(any)); !errors.Is(err, io.EOF) {
		http.Error(w, "single JSON document required", http.StatusBadRequest)
		return
	}
	if incoming.APIVersion != "admission.k8s.io/v1" || incoming.Kind != "AdmissionReview" ||
		incoming.Request == nil || incoming.Request.UID == "" {
		http.Error(w, "v1 AdmissionReview request with UID required", http.StatusBadRequest)
		return
	}
	request := incoming.Request
	response := admissionResponse{UID: request.UID, Allowed: true}
	if request.Resource == (groupVersionResource{Group: "", Version: "v1", Resource: "pods"}) &&
		request.SubResource == "" && request.Operation == "CREATE" {
		var pod podInput
		if err := json.Unmarshal(request.Object, &pod); err != nil ||
			pod.APIVersion != "v1" || pod.Kind != "Pod" || pod.Metadata == nil {
			http.Error(w, "valid Pod object required", http.StatusBadRequest)
			return
		}
		if pod.Metadata.Labels["example.com/injected"] != "true" {
			operation := patchOperation{
				Op: "add", Path: "/metadata/labels/example.com~1injected", Value: "true",
			}
			if pod.Metadata.Labels == nil {
				operation.Path = "/metadata/labels"
				operation.Value = map[string]string{"example.com/injected": "true"}
			}
			patch, err := json.Marshal([]patchOperation{operation})
			if err != nil {
				http.Error(w, "patch encoding failed", http.StatusInternalServerError)
				return
			}
			response.Patch = patch
			response.PatchType = "JSONPatch"
		}
	}
	outgoing := review{
		APIVersion: "admission.k8s.io/v1", Kind: "AdmissionReview", Response: &response,
	}
	body, err := json.Marshal(outgoing)
	if err != nil {
		http.Error(w, "response encoding failed", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	if _, err := w.Write(body); err != nil {
		log.Printf("write admission response: %v", err)
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/mutate", mutate)
	server := &http.Server{
		Addr: ":8443", Handler: mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       30 * time.Second,
	}
	// Mount the approved certificate/key as files; the key is never an environment variable.
	log.Fatal(server.ListenAndServeTLS("/tls/tls.crt", "/tls/tls.key"))
}
```

```bash
cd examples/platform/extensions/webhook
go test ./...
```

テストは TLS リスナーを開かず、httptest を通じてハンドラーを呼び出しました。デプロイには依然としてイメージ、Service、証明書/キーのファイル、実際の CA バンドル、API server への接続性、呼び出し元の認証、ネットワークポリシーが必要です。この TLS server は既定ではクライアント認証を設定しません。webhook のリソース、operation、パスをハンドラーに一致させてください。

failurePolicy、timeoutSeconds、sideEffects/dryRun、reinvocationPolicy、selector を確認してください。Fail は webhook が利用できないときに API リクエストをブロックし得ます。Ignore はそのチェックをバイパスし得ます。None を宣言する場合は、外部への副作用が実際に存在しないことを反映していなければなりません。

現行の Istio における Pod 単位の注入は sidecar.istio.io/inject **ラベル** を使用します。namespace では istio-injection またはリビジョンのラベルを使用します。古い annotation の例を既定として残すのではなく、Pod テンプレートでのラベル配置とバージョン固有の注入ルールを確認してください。

## Scheduler Framework と Extender

Framework plugin は scheduler バイナリの内部でコンパイルされ登録されます。YAML で CustomFilter という名前を指定しても、存在しないコードは読み込まれません。別の scheduler を選択するには、profile の schedulerName を Pod の spec.schedulerName と一致させてください。

Filter は候補を除外し、Score は実行可能な node をランク付けします。NormalizeScore、plugin の weight、同点時の選択を考慮してください。Reserve/Unreserve は plugin の予約状態を維持するもので、恒久的な容量予約 API ではありません。Permit は allow、reject、wait が可能で、PreBind/Bind/PostBind は binding の各段階を扱います。

Kubernetes 1.36.2 の公開 framework は k8s.io/kube-scheduler/framework の CycleState/NodeInfo を使用し、Score に NodeInfo を渡します。古い nodeName の文字列/ポインタのシグネチャを無条件にコピーせず、正確なマイナーバージョンに対してコンパイルしてください。scheduler-plugins 0.35.7 は 1.36/1.37 のバイナリと自動的に互換になるわけではありません。

Extender は別個の HTTP(S) エンドポイントを公開します。実装済みの filter/prioritize/bind ハンドラーのみを設定し、nodeCacheCapable に応じて Nodes と NodeNames をサポートしてください。以前の例では bindVerb を実装せずに設定していました。nil 入力、ボディサイズ制限、タイムアウト、TLS/認証、失敗時のポリシー、スコア範囲を扱ってください。単純な zone の選択であれば、まず組み込みの node affinity を検討してください。

## CNI

CNI は runtime とネットワーク plugin の実行契約です。CNI ライブラリ 1.3.1 は設定の cniVersion とは別物です。共有される spec のバージョンと、ADD、DEL、CHECK、STATUS、GC などの操作のサポート状況を確認してください。

ADD の成功は、実際の namespace インターフェース、IPAM、ルート設定を反映していなければなりません。JSON で固定 IP を返しても接続は作られず、衝突を引き起こす可能性があります。DEL は部分的な失敗や namespace の欠落をクリーンアップしなければならず、CHECK は実際の状態を検査しなければなりません。同じ host-local サブネットを複数の node にコピーしても、クラスター全体の IPAM にはなりません。

選択した Calico、Cilium、Flannel のリリースについて、機能とディストリビューションの互換性を確認してください。オリジナルの Weave Net リポジトリはアーカイブ済みであり、新規導入の既定の選択肢として提示していません。この監査では host のネットワーキング、veth、ルート、CNI 設定を一切変更していません。

## CSI

CSI 1.13.0 は Identity、Controller、Node の RPC セットと capability を定義します。すべてのデプロイが 1 つのプロセスで 3 つすべてを提供する必要はありません。Node のみの plugin も可能であり、公表する capability は実際の RPC の動作と一致していなければなりません。

CreateVolume は冪等性、容量範囲、topology、バックエンド ID、エラーを扱わなければなりません。NodePublishVolume は要求された権限/読み取り専用の動作で正しくマウントしなければならず、NodeUnpublish/Delete はリトライを扱わなければなりません。常に vol-123 を返したり、マウントせずに成功を報告することは、実際のドライバーの実装ではありません。

StorageClass/PVC はドライバーのデプロイではありません。provisioner 名はインストール済みのドライバーと一致しなければならず、parameters はドライバー固有です。controller サイドカー、node の登録/ソケット/host マウント、認証情報、topology、volumeBindingMode、reclaimPolicy を確認してください。EBS、PD、Azure Disk、Ceph CSI については公式のインストール/サポートガイダンスに従ってください。

## 検証と参考資料

元の 983 行の韓国語ガイドと 987 行の英語ガイド、いずれも 652 行のクイズ 2 本、および 36 個の一意なコードブロックを読みました。チェックは CRD の入力 6 ケース、policy の CEL 6 ケース、Go webhook の 14 ケース、および RFC6902 patch の実適用 4 件を対象としました。完全なクラスター controller、aggregated API server、scheduler、CNI/CSI ドライバーは実行していません。説明用の擬似コードはテスト済みの実装として表示していません。

- [CRDs](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Aggregation](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/)
- [Scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Framework 1.36.2](https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/kube-scheduler/framework/interface.go)
- [controller-runtime 0.25.0](https://github.com/kubernetes-sigs/controller-runtime/tree/v0.25.0)
- [Operator SDK](https://sdk.operatorframework.io/docs/installation/)
- [CNI 1.3.1 source](https://github.com/containernetworking/cni/blob/v1.3.1/SPEC.md)
- [CSI 1.13.0](https://github.com/container-storage-interface/spec/blob/v1.13.0/spec.md)
- [Istio injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

[拡張メカニズムのクイズ](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
