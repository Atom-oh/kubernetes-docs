# Kubernetes 拡張メカニズム

> **最終更新**: October 12, 2026

## 拡張ポイントの選択

Kubernetes には、API とワークロードの動作を拡張する複数の方法があります。CRD の登録と、その動作の実装は別のものです。

| メカニズム | 役割 | 運用上の要件 |
| --- | --- | --- |
| CRD + controller | カスタム API と望ましい状態の調整 | スキーマ、調整、RBAC、status、削除 |
| API aggregation | リクエストを別の API server に委譲 | APIService、TLS、委譲された認証/認可、discovery/storage |
| Admission policy/webhook | API リクエストの検証または変更 | スコープ、失敗時の処理、CEL または webhook の可用性 |
| Scheduler plugin/extender | フィルタリング、スコアリング、またはバインディングを拡張 | 互換性のある scheduler binary、登録/設定、失敗時の処理 |
| CNI | コンテナネットワーク | 実際の interface、IPAM、route、クリーンアップ |
| CSI | Volume のライフサイクルと node へのマウント | capability に適した RPC と backend/node 操作 |

選択した API、library、distribution の互換性を確認してください。レビュー対象の controller-runtime 0.25.0 の go.mod は Go 1.26.0 と Kubernetes Go module 0.37.0 を使用しています（2026 年 10 月 12 日時点の最新リリースは v0.25.2）。以下の Scheduler interface に関する注記は Kubernetes 1.36.2 のソースに照らして確認しました。scheduler-plugins 0.35.7 がこれと置き換え可能であると仮定しないでください。

## CRD とインスタンス

CRD は OpenAPI v3 構造を持つカスタム API を定義します。必須フィールドはそれを含むレベルに適用されるため、トップレベルの spec と spec.image の両方を明示的に必須にします。status はその subresource を通じて管理し、スケールのために実際の replicas と availableReplicas を区別してください。controller がなければ、この API はデータを保存するだけで Deployment は作成しません。

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

controller は、観測した状態から status.replicas、availableReplicas、selector、observedGeneration を設定する必要があります。status が欠落している、または古い状態は成功ではありません。複数の提供する API version については、storage version、status.storedVersions、conversion を確認してください。conversion webhook は必要な変換を実装しなければなりません。version 名を変更してもデータは移行されません。

## client-go、controller-runtime、Operator

client-go は client、informer/cache、workqueue を提供します。一度だけ List してから Watch するだけでは完全な controller ではありません。resourceVersion の継続性、watch の終了、410 Gone、再接続、cache の同期に加えて、context のキャンセルとクリーンアップを処理してください。

controller-runtime は manager、cache/client、workqueue、leader election、調整パターンを提供します。カスタム WebApp Go type と scheme registration を生成または提供してから、選択した library version に対してコンパイルしてください。存在しない example.com/api type や appsv1.WebApp への参照では、実行可能な実装になりません。

以下は**疑似コード**です。その関数と Deployment 設定は別途実装する必要があります。

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

ownerReferences は、name だけでなく UID、namespace、scope の制約にも一致しなければなりません。同名の Deployment を無条件に更新すると、別の controller のワークロードを変更する可能性があります。garbage collection は propagation、owner、finalizer に依存します。ownerReference は任意の外部 AWS データをクリーンアップしません。

Operator はドメイン知識を実装します。failover、rolling upgrade、backup が自動的に安全になるわけではありません。データベース設計では、primary fencing、quorum、replica の追いつき、WAL/backup 復元テスト、schema の互換性、disruption budget、shutdown の順序が必要です。

公式の Operator SDK 1.42.3 インストール手順を使用して、OS/architecture と checksum を選択してください。古い amd64 専用の 1.25.0 binary をあらゆる場所にインストールしないでください。選択した SDK/plugin に対して init/create api/make manifests を検証し、生成した project をコンパイル/テストしてから、image を個別に build/push して deploy してください。

## API Aggregation

APIService は、group/version のパスを拡張 API server の Service にルーティングします。server には TLS、discovery、storage、list/watch などの API 動作が必要です。front-proxy certificate の CA/CN を検証し、転送された user identity に関する trust boundary を維持し、委譲された authorization を設定してください。

実際の metrics-server API version について、インストール済みの discovery を調べてください。架空の v1.metrics.k8s.io APIService や insecureSkipTLSVerify:true をデフォルトとして使用しないでください。group/version、Service、caBundle は実際の server と一致する必要があります。単純な HTTP handler や空の API group は完全な Kubernetes API server ではありません。

## Admission Policy と Webhook

ValidatingAdmissionPolicy は Kubernetes 1.30 以降 stable であり、CEL validation をプロセス内で実行します。この policy/binding は、production namespace における Deployment と deployments/scale リクエストの replicas を 1～5 に制限します。HPA と kubectl scale の更新もチェックするため、HPA の maxReplicas をこの制限と合わせてください。namespace 名は任意の environment label と同等ではありません。policy を適用する前に運用上の影響を確認してください。

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

Validating webhook はリクエストを許可または拒否します。mutating webhook は JSON Patch を返すことができます。同じ AdmissionReview version と request UID を使用して応答してください。patchType は JSONPatch であり、patch bytes は JSON 内で Base64 エンコードされます。

この Go handler は Pod CREATE 時に例示的な label を追加します。label map が存在しない/null の場合は作成し、既存の label を保持し、値がすでに一致する場合は patch を省略します。size、method、content type、version、UID、null の request/object をチェックします。この label は実際に sidecar を inject するものではありません。

### テスト済み Webhook コード

examples/platform/extensions/webhook には、go.mod、この実装、およびそのテストが含まれます。Go 1.25 の標準 library のみを使用します。struct は使用する AdmissionReview field を宣言し、追加の field は無視します。

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

テストは TLS listener を開かずに httptest を介して handler を呼び出しました。Deployment には依然として image、Service、certificate/key file、実際の CA bundle、API-server connectivity、caller authentication、network policy が必要です。この TLS server はデフォルトでは client authentication を設定しません。webhook resource、operation、path を handler に一致させてください。

failurePolicy、timeoutSeconds、sideEffects/dryRun、reinvocationPolicy、selector を確認してください。webhook が利用できない場合、Fail は API リクエストをブロックする可能性があり、Ignore はそのチェックをバイパスする可能性があります。None を宣言する場合は、外部 side effect が実際に存在しないことを反映しなければなりません。

現在の Istio の Pod 単位の injection には sidecar.istio.io/inject **label** を使用します。namespace では istio-injection または revision label を使用します。古い annotation の例をデフォルトのままにするのではなく、Pod template の label 配置と version 固有の injection rule を検証してください。

## Scheduler Framework と Extender

Framework plugin は scheduler binary 内にコンパイルされ、登録されます。YAML で CustomFilter という名前を指定しても、存在しない code は読み込まれません。別の scheduler を選択するには、profile の schedulerName を Pod spec.schedulerName と一致させてください。

Filter は候補を除外し、Score は実行可能な node をランク付けします。NormalizeScore、plugin weight、同点時の選択を考慮してください。Reserve/Unreserve は plugin の予約状態を維持するものであり、永続的な capacity-reservation API ではありません。Permit は許可、拒否、待機を行うことができます。PreBind/Bind/PostBind はバインディング段階を処理します。

Kubernetes 1.36.2 の公開 framework は k8s.io/kube-scheduler/framework の CycleState/NodeInfo を使用し、Score に NodeInfo を渡します。古い nodeName-string/pointer signature を無批判にコピーせず、正確な minor version に対してコンパイルしてください。scheduler-plugins 0.35.7 は 1.36/1.37 binary と自動的に置き換え可能ではありません。

extender は個別の HTTP(S) endpoint を公開します。実装済みの filter/prioritize/bind handler のみを設定し、nodeCacheCapable に応じて Nodes と NodeNames をサポートしてください。以前の例では、実装していない bindVerb を設定していました。nil input、body limit、timeout、TLS/authentication、failure policy、score range を処理してください。単純な zone 選択では、まず組み込みの node affinity を検討してください。

## CNI

CNI は runtime/network-plugin の実行契約です。CNI library 1.3.1 は config の cniVersion とは異なります。共有する spec version と、ADD、DEL、CHECK、STATUS、GC などの operation のサポートを検証してください。

成功した ADD は、実際の namespace interface、IPAM、route 設定を反映しなければなりません。JSON で固定 IP を返しても接続は作成されず、競合を引き起こす可能性があります。DEL は部分的な失敗または存在しない namespace をクリーンアップする必要があり、CHECK は実際の状態を検査する必要があります。同じ host-local subnet を複数の node にコピーしても、cluster IPAM は提供されません。

選択した Calico、Cilium、Flannel のリリースについて、機能と distribution の互換性を確認してください。元の Weave Net repository はアーカイブされており、新規インストールのデフォルト選択肢として提示されていません。この監査では、host networking、veth、route、CNI 設定を変更していません。

## CSI

CSI 1.13.0 は Identity、Controller、Node の RPC set と capability を定義します。すべての Deployment が 3 つすべてを 1 つの process で提供する必要はありません。Node 専用 plugin も可能であり、提示する capability は実際の RPC 動作と一致しなければなりません。

CreateVolume は、idempotency、capacity range、topology、backend ID、error を処理する必要があります。NodePublishVolume は要求された permission/read-only 動作で正しく mount する必要があり、NodeUnpublish/Delete は retry を処理する必要があります。常に vol-123 を返す、または mount せずに成功を報告することは、実際の driver の実装ではありません。

StorageClass/PVC は driver deployment ではありません。provisioner 名はインストールされた driver と一致し、parameter は driver 固有です。controller sidecar、node registration/socket/host mount、credential、topology、volumeBindingMode、reclaimPolicy を確認してください。EBS、PD、Azure Disk、Ceph CSI については、公式のインストール/サポートガイダンスに従ってください。

## 検証と参考資料

元の 983 行の韓国語ガイドと 987 行の英語ガイド、どちらも 652 行の quiz、および 36 個の一意な code block を読みました。6 件の CRD input case、6 件の policy CEL case、14 件の Go webhook case、4 件の実際の RFC6902 patch application を確認しました。完全な cluster controller、aggregated API server、scheduler、CNI/CSI driver は実行していません。説明用の疑似コードは、テスト済み実装としては示していません。

- [CRD](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Aggregation](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/)
- [Scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Framework 1.36.2](https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/kube-scheduler/framework/interface.go)
- [controller-runtime 0.25.0](https://github.com/kubernetes-sigs/controller-runtime/tree/v0.25.0)
- [Operator SDK](https://sdk.operatorframework.io/docs/installation/)
- [CNI 1.3.1 source](https://github.com/containernetworking/cni/blob/v1.3.1/SPEC.md)
- [CSI 1.13.0](https://github.com/container-storage-interface/spec/blob/v1.13.0/spec.md)
- [Istio injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

[拡張メカニズム quiz](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)