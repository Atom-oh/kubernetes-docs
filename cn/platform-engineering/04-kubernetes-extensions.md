# Kubernetes 扩展机制

> **最后更新**: October 12, 2026

## 选择扩展点

Kubernetes 提供多种扩展 API 和工作负载行为的方式。注册 CRD 与实现其行为是不同的事情。

| 机制 | 角色 | 运维要求 |
| --- | --- | --- |
| CRD + controller | 自定义 API 和期望状态协调 | Schema、协调、RBAC、状态和删除 |
| API aggregation | 将请求委派给独立的 API server | APIService、TLS、委派的身份验证/授权、发现/存储 |
| Admission policy/webhook | 验证或变更 API 请求 | 范围、失败处理、CEL 或 webhook 可用性 |
| Scheduler plugin/extender | 扩展过滤、评分或绑定 | 兼容的 scheduler 二进制文件、注册/配置、失败处理 |
| CNI | 容器网络 | 实际接口、IPAM、路由和清理 |
| CSI | 卷生命周期和节点挂载 | 与能力相匹配的 RPC 以及后端/节点操作 |

检查所选 API、库和发行版的兼容性。经审核的 controller-runtime 0.25.0 go.mod 使用 Go 1.26.0 和 Kubernetes Go modules 0.37.0（截至 October 12, 2026，最新版本为 v0.25.2）。下文的 Scheduler 接口说明根据 Kubernetes 1.36.2 源码检查；不要假定 scheduler-plugins 0.35.7 可与其互换。

## CRD 和实例

CRD 使用 OpenAPI v3 结构定义自定义 API。必填字段在其所在层级生效，因此应明确要求顶层 spec 和 spec.image。通过其子资源管理 status，并区分实际 replicas 与用于扩缩容的 availableReplicas。没有 controller 时，此 API 会存储数据，但不会创建 Deployment。

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

controller 必须根据观测到的状态填充 status.replicas、availableReplicas、selector 和 observedGeneration。缺失或过时的 status 并不代表成功。对于多个已服务的 API 版本，请审核存储版本、status.storedVersions 和转换。转换 webhook 必须实现所需的转换；重命名版本不会迁移数据。

## client-go、controller-runtime 和 Operator

client-go 提供客户端、informer/cache 和 workqueue。一次性的 List 后跟 Watch 并不是完整的 controller：还应处理 resourceVersion 连续性、watch 关闭、410 Gone、重新连接和 cache 同步，以及 context 取消和清理。

controller-runtime 提供 manager、cache/client、workqueue、leader election 和协调模式。生成或提供自定义 WebApp Go 类型及 scheme 注册，然后根据所选库版本进行编译。对缺失的 example.com/api 类型或 appsv1.WebApp 的引用无法构成可运行的实现。

以下内容是**伪代码**；必须单独实现其函数和 Deployment 配置。

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

ownerReferences 除名称外，还必须匹配 UID、namespace 和范围约束。盲目更新同名 Deployment 可能会变更另一个 controller 的工作负载。垃圾回收取决于传播方式、owner 和 finalizer；ownerReference 不会清理任意外部 AWS 数据。

Operator 实现领域知识；故障转移、滚动升级和备份并不会自动变得安全。数据库设计需要主节点隔离、仲裁、副本追赶、WAL/备份恢复测试、Schema 兼容性、disruption budget 和关闭顺序。

使用官方 Operator SDK 1.42.3 安装说明选择 OS/architecture 和校验和。不要在所有地方安装旧的、仅支持 amd64 的 1.25.0 二进制文件。根据所选 SDK/plugin 验证 init/create api/make manifests，编译/测试生成的项目，然后单独构建/推送镜像并部署。

## API Aggregation

APIService 将 group/version 路径路由到扩展 API server 的 Service。该 server 需要 TLS、发现、存储和 API 行为，例如 list/watch。验证 front-proxy certificate CA/CN，保留转发用户身份周围的信任边界，并配置委派授权。

检查已安装的发现信息以获取实际的 metrics-server API 版本。不要将虚构的 v1.metrics.k8s.io APIService 或 insecureSkipTLSVerify:true 用作默认值。group/version、Service 和 caBundle 必须与真实 server 相匹配。简单的 HTTP handler 或空 API group 并非完整的 Kubernetes API server。

## Admission Policies 和 Webhooks

ValidatingAdmissionPolicy 自 Kubernetes 1.30 起已稳定，并在进程内运行 CEL 验证。此 policy/binding 将 production namespace 中 Deployment 和 deployments/scale 请求的 replicas 限制为 1–5。它还会检查 HPA 和 kubectl scale 更新；使 HPA maxReplicas 与该限制保持一致。namespace 名称并不等同于任意环境 label。应用 policy 前请审核其运维影响。

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

Validating webhook 可允许或拒绝请求；mutating webhook 可返回 JSON Patch。使用相同的 AdmissionReview 版本和请求 UID 进行响应。patchType 为 JSONPatch，且 patch 字节在 JSON 中经过 Base64 编码。

此 Go handler 会在 Pod CREATE 时添加一个示例 label。当 labels map 缺失/null 时会创建它，保留现有 label，并在值已匹配时省略 patch。它会检查大小、方法、content type、版本、UID 以及 null request/object。该 label 实际上并不会注入 sidecar。

### 已测试的 Webhook 代码

examples/platform/extensions/webhook 包含 go.mod、此实现及其测试。它仅使用 Go 1.25 标准库。这些 struct 声明了所使用的 AdmissionReview 字段，并忽略额外字段。

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

测试通过 httptest 调用了 handler，而未开启 TLS listener。Deployment 仍需要镜像、Service、certificate/key 文件、实际 CA bundle、API-server 连通性、调用方身份验证和 network policy。此 TLS server 默认不配置 client authentication。将 webhook resources、operations 和 paths 与 handler 匹配。

审核 failurePolicy、timeoutSeconds、sideEffects/dryRun、reinvocationPolicy 和 selectors。当 webhook 不可用时，Fail 可能阻止 API 请求；Ignore 可能绕过其检查。声明 None 必须反映实际不存在外部副作用。

当前的 Istio 按 Pod 注入使用 sidecar.istio.io/inject **label**；namespace 使用 istio-injection 或 revision labels。验证 Pod-template label 位置和特定版本的注入规则，而不是继续将旧 annotation 示例作为默认值。

## Scheduler Framework 和 Extenders

Framework plugins 在 scheduler 二进制文件内进行编译和注册。在 YAML 中命名 CustomFilter 不会加载缺失的代码。将 profile 的 schedulerName 与 Pod spec.schedulerName 匹配，以选择独立的 scheduler。

Filter 移除候选节点，而 Score 对可行节点进行排名。考虑 NormalizeScore、plugin weights 和平局选择。Reserve/Unreserve 维护 plugin reservation state，而不是永久的 capacity-reservation API。Permit 可以允许、拒绝或等待；PreBind/Bind/PostBind 处理绑定阶段。

Kubernetes 1.36.2 公共 framework 使用来自 k8s.io/kube-scheduler/framework 的 CycleState/NodeInfo，并将 NodeInfo 传递给 Score。不要盲目复制旧的 nodeName-string/pointer signatures；应针对精确的 minor version 编译。scheduler-plugins 0.35.7 并不能自动与 1.36/1.37 二进制文件互换。

extender 公开独立的 HTTP(S) endpoints。仅配置已实现的 filter/prioritize/bind handlers，并根据 nodeCacheCapable 支持 Nodes 与 NodeNames。之前的示例配置了 bindVerb，却没有实现它。处理 nil inputs、body limits、timeouts、TLS/authentication、failure policy 和 score ranges。对于简单的 zone 选择，先考虑内置 node affinity。

## CNI

CNI 是 runtime/network-plugin 的执行契约。CNI library 1.3.1 与配置 cniVersion 不同。验证共享的 spec versions 及对 ADD、DEL、CHECK、STATUS 和 GC 等操作的支持。

成功的 ADD 必须反映实际的 namespace interface、IPAM 和 route 设置。在 JSON 中返回固定 IP 不会创建连接，并且可能导致冲突。DEL 必须清理部分失败或缺失 namespace 的情况；CHECK 必须检查真实状态。将同一 host-local subnet 复制到多个 node 并不能提供 cluster IPAM。

检查所选 Calico、Cilium 或 Flannel release 的功能和发行版兼容性。原始 Weave Net repository 已归档，且不作为新的默认安装选项。本审核未更改任何 host networking、veth、routes 或 CNI 配置。

## CSI

CSI 1.13.0 定义了 Identity、Controller 和 Node RPC 集及能力。并非每个 Deployment 都需要在一个进程中提供全部三个。可以使用仅 Node 的 plugin；所声明的 capabilities 必须与实际 RPC 行为一致。

CreateVolume 必须处理幂等性、capacity ranges、topology、backend IDs 和 errors。NodePublishVolume 必须按照请求的 permissions/read-only 行为正确挂载；NodeUnpublish/Delete 必须处理重试。始终返回 vol-123 或在未挂载时报告成功，都不能实现真实 driver。

StorageClass/PVC 并不是 driver Deployment。provisioner 名称必须匹配已安装的 driver，且 parameters 是特定于 driver 的。检查 controller sidecars、node registration/socket/host mounts、credentials、topology、volumeBindingMode 和 reclaimPolicy。遵循 EBS、PD、Azure Disk 或 Ceph CSI 的官方安装/支持指南。

## 验证和参考资料

已阅读原始的 983 行韩语指南和 987 行英语指南、两个均为 652 行的 quiz，以及 36 个唯一代码块。检查覆盖了六个 CRD 输入案例、六个 policy CEL 案例、14 个 Go webhook 案例和四个实际 RFC6902 patch 应用。未执行完整的 cluster controller、aggregated API server、scheduler 或 CNI/CSI driver。说明性伪代码未标记为经过测试的实现。

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

[扩展机制测验](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
