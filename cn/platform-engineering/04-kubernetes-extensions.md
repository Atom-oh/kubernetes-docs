# Kubernetes 扩展机制

> **最后更新**: September 12, 2026

## 选择扩展点

Kubernetes 提供多种扩展 API 和工作负载行为的方式。注册 CRD 与实现其行为是不同的事情。

| 机制 | 作用 | 运维要求 |
| --- | --- | --- |
| CRD + controller | 自定义 API 和期望状态调谐 | Schema、调谐、RBAC、状态和删除 |
| API aggregation | 将请求委托给独立的 API server | APIService、TLS、委托身份验证/授权、发现/存储 |
| Admission policy/webhook | 验证或变更 API 请求 | 范围、失败处理、CEL 或 webhook 可用性 |
| Scheduler plugin/extender | 扩展过滤、评分或绑定 | 兼容的 scheduler 二进制文件、注册/配置、失败处理 |
| CNI | 容器网络 | 实际接口、IPAM、路由和清理 |
| CSI | 卷生命周期和节点挂载 | 与能力相符的 RPC 及后端/节点操作 |

检查所选 API、库和发行版的兼容性。当前 controller-runtime 0.25.0 使用 Go 1.26 和 Kubernetes Go modules 0.37.0。下文的 Scheduler 接口说明已根据 Kubernetes 1.36.2 源码检查；不要假定 scheduler-plugins 0.35.7 可与其互换。

## CRD 和实例

CRD 使用 OpenAPI v3 结构定义自定义 API。必填字段在其所在层级生效，因此必须同时显式要求顶层 spec 和 spec.image。通过其 subresource 管理 status，并针对扩缩容区分实际 replicas 和 availableReplicas。没有 controller 时，此 API 只会存储数据，而不会创建 Deployment。

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

controller 必须根据观测到的状态填充 status.replicas、availableReplicas、selector 和 observedGeneration。缺失或陈旧的 status 不代表成功。对于多个已提供的 API 版本，请审查存储版本、status.storedVersions 和转换。转换 webhook 必须实现所需的转换；重命名版本不会迁移数据。

## client-go、controller-runtime 和 Operator

client-go 提供 client、informer/cache 和 workqueue。一次性执行 List 后再 Watch 并非完整的 controller：除了 context 取消和清理外，还要处理 resourceVersion 连续性、watch 关闭、410 Gone、重连和 cache 同步。

controller-runtime 提供 manager、cache/client、workqueue、leader election 和调谐模式。生成或提供自定义的 WebApp Go 类型及 scheme 注册，然后针对所选库版本进行编译。对缺失的 example.com/api 类型或 appsv1.WebApp 的引用不能构成可运行的实现。

以下内容为**伪代码**；其函数和 Deployment 配置必须单独实现。

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

ownerReferences 除名称外，还必须匹配 UID、namespace 和 scope 约束。盲目更新同名 Deployment 可能会变更另一个 controller 的工作负载。垃圾回收依赖传播策略、owner 和 finalizer；ownerReference 不会清理任意外部 AWS 数据。

Operator 实现领域知识；故障转移、滚动升级和备份并不会自动安全。数据库设计需要主节点隔离、法定人数、副本追赶、WAL/备份恢复测试、Schema 兼容性、干扰预算和关闭顺序。

使用官方 Operator SDK 1.42.3 安装说明选择 OS/架构和校验和。不要在所有环境中都安装旧的仅限 amd64 的 1.25.0 二进制文件。根据所选 SDK/plugin 验证 init/create api/make manifests，编译/测试生成的项目，然后单独构建/推送 image 并部署。

## API 聚合

APIService 将 group/version 路径路由到扩展 API server 的 Service。该 server 需要 TLS、发现、存储以及 list/watch 等 API 行为。验证 front-proxy 证书的 CA/CN，维护围绕转发用户身份的信任边界，并配置委托授权。

检查已安装的发现信息以确认实际的 metrics-server API 版本。不要使用虚构的 v1.metrics.k8s.io APIService，也不要默认使用 insecureSkipTLSVerify:true。group/version、Service 和 caBundle 必须与实际 server 匹配。简单的 HTTP handler 或空 API group 并非完整的 Kubernetes API server。

## Admission Policy 和 Webhook

ValidatingAdmissionPolicy 自 Kubernetes 1.30 起已稳定，并在进程内执行 CEL 验证。此 policy/binding 将 production namespace 中 Deployment 和 deployments/scale 请求的 replicas 限制为 1–5。它还会检查 HPA 和 kubectl scale 更新；请使 HPA maxReplicas 与该限制一致。namespace 名称不等同于任意环境 label。应用 policy 前请审查运维影响。

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

Validating webhook 可以允许或拒绝请求；mutating webhook 可以返回 JSON Patch。请使用相同的 AdmissionReview 版本和请求 UID 进行响应。patchType 为 JSONPatch，且 patch 字节会在 JSON 中进行 Base64 编码。

此 Go handler 会在 Pod CREATE 时添加一个示例 label。它会在 labels map 缺失/null 时创建该 map，保留现有 labels，并且在值已匹配时省略 patch。它会检查大小、method、content type、版本、UID 以及 null 请求/对象。此 label 实际上不会注入 sidecar。

### 已测试的 Webhook 代码

examples/platform/extensions/webhook 包含 go.mod、此实现及其测试。它只使用 Go 1.25 标准库。这些 struct 声明了会使用的 AdmissionReview 字段，并忽略额外字段。

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

测试通过 httptest 调用 handler，未打开 TLS listener。Deployment 仍需要 image、Service、证书/key 文件、实际 CA bundle、API-server 连通性、调用方身份验证和 network policy。该 TLS server 默认不配置 client 身份验证。请使 webhook resource、operation 和 path 与 handler 匹配。

审查 failurePolicy、timeoutSeconds、sideEffects/dryRun、reinvocationPolicy 和 selector。当 webhook 不可用时，Fail 可能阻塞 API 请求；Ignore 可能绕过其检查。声明 None 必须反映确实不存在外部副作用。

当前每 Pod 的 Istio 注入使用 sidecar.istio.io/inject **label**；namespace 使用 istio-injection 或 revision label。请验证 Pod-template 的 label 放置位置和特定版本的注入规则，而不是将旧 annotation 示例保留为默认值。

## Scheduler Framework 和 Extender

Framework plugin 在 scheduler 二进制文件内部编译和注册。在 YAML 中命名 CustomFilter 不会加载缺失的代码。将 profile 的 schedulerName 与 Pod spec.schedulerName 匹配，以选择独立的 scheduler。

Filter 会移除候选项，Score 会对可行节点进行排名。要考虑 NormalizeScore、plugin 权重和并列选择。Reserve/Unreserve 维护 plugin 保留状态，并非永久的 capacity-reservation API。Permit 可以允许、拒绝或等待；PreBind/Bind/PostBind 处理绑定阶段。

Kubernetes 1.36.2 公共 framework 使用来自 k8s.io/kube-scheduler/framework 的 CycleState/NodeInfo，并将 NodeInfo 传递给 Score。不要盲目复制旧的 nodeName-string/pointer 签名；应针对精确的 minor 版本编译。scheduler-plugins 0.35.7 并非自动可与 1.36/1.37 二进制文件互换。

extender 暴露独立的 HTTP(S) endpoint。仅配置已实现的 filter/prioritize/bind handler，并根据 nodeCacheCapable 支持 Nodes 与 NodeNames。前一个示例配置了 bindVerb 却未实现它。处理 nil 输入、body 限制、timeout、TLS/身份验证、failure policy 和 score 范围。对于简单的 zone 选择，先考虑内置 node affinity。

## CNI

CNI 是 runtime/network-plugin 执行约定。CNI library 1.3.1 与配置 cniVersion 不同。验证共享 spec 版本以及对 ADD、DEL、CHECK、STATUS 和 GC 等操作的支持。

成功的 ADD 必须反映实际的 namespace interface、IPAM 和 route 设置。在 JSON 中返回固定 IP 不会创建连接，还可能导致冲突。DEL 必须清理部分失败或缺失 namespace；CHECK 必须检查实际状态。将相同的 host-local subnet 复制到多个 node 并不能提供 cluster IPAM。

检查所选 Calico、Cilium 或 Flannel 版本的特性和发行版兼容性。原始 Weave Net repository 已归档，不应作为默认的新安装选项。本次审计未更改任何 host networking、veth、route 或 CNI 配置。

## CSI

CSI 1.13.0 定义了 Identity、Controller 和 Node RPC 集及其能力。并非每个 Deployment 都需要在一个进程中提供全部三者。可以使用仅 Node 的 plugin；所声明的能力必须与实际 RPC 行为匹配。

CreateVolume 必须处理幂等性、capacity range、topology、backend ID 和错误。NodePublishVolume 必须按请求的 permission/read-only 行为正确挂载；NodeUnpublish/Delete 必须处理重试。始终返回 vol-123 或未挂载便报告成功，并不代表实现了真实 driver。

StorageClass/PVC 不是 driver Deployment。provisioner 名称必须与已安装的 driver 匹配，且 parameter 为 driver 特定。检查 controller sidecar、node 注册/socket/host mount、凭证、topology、volumeBindingMode 和 reclaimPolicy。请遵循 EBS、PD、Azure Disk 或 Ceph CSI 的官方安装/支持指南。

## 验证和参考资料

已阅读原始的 983 行韩文指南和 987 行英文指南、两份各 652 行的测验以及 36 个唯一代码块。检查涵盖六个 CRD 输入案例、六个 policy CEL 案例、14 个 Go webhook 案例以及四次实际 RFC6902 patch 应用。未执行完整的 cluster controller、aggregated API server、scheduler 或 CNI/CSI driver。说明性伪代码未标记为已测试的实现。

- [CRD](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [聚合](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/)
- [Scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Framework 1.36.2](https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/kube-scheduler/framework/interface.go)
- [controller-runtime 0.25.0](https://github.com/kubernetes-sigs/controller-runtime/tree/v0.25.0)
- [Operator SDK](https://sdk.operatorframework.io/docs/installation/)
- [CNI 1.3.1 源码](https://github.com/containernetworking/cni/blob/v1.3.1/SPEC.md)
- [CSI 1.13.0](https://github.com/container-storage-interface/spec/blob/v1.13.0/spec.md)
- [Istio 注入](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

[扩展机制测验](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
