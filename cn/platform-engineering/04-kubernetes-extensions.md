# Kubernetes 扩展机制

> **最后更新**：2026 年 10 月 16 日

## 选择扩展点

Kubernetes 提供了多种扩展 API 和工作负载行为的方式。注册 CRD 与实现其行为是两回事。

| 机制 | 作用 | 运维要求 |
| --- | --- | --- |
| CRD + controller | 自定义 API 和期望状态协调 | Schema、协调、RBAC、状态和删除 |
| API 聚合 | 将请求委托给单独的 API server | APIService、TLS、委托式身份验证/授权、发现/存储 |
| Admission policy/webhook | 验证或变更 API 请求 | 作用范围、故障处理、CEL 或 webhook 可用性 |
| Scheduler plugin/extender | 扩展筛选、评分或绑定 | 兼容的 scheduler 二进制文件、注册/配置、故障处理 |
| CNI | 容器网络 | 实际接口、IPAM、路由和清理 |
| CSI | 卷生命周期和节点挂载 | 与能力相符的 RPC 以及后端/节点操作 |

请检查所选 API、库和发行版的兼容性。截至 2026 年 10 月 16 日，审核时最新发布的 controller-runtime 0.25.2，其 go.mod 使用 Go 1.26.0 和 Kubernetes Go 模块 0.37.0。以下关于 Scheduler 接口的说明根据 Kubernetes 1.36.2 源码核对；不要假设 scheduler-plugins 0.35.7 可以与之互换。

## CRD 和实例

CRD 使用 OpenAPI v3 结构定义自定义 API。必填字段适用于其所在层级，因此必须同时显式要求顶层 spec 和 spec.image。通过 status 子资源管理状态，并区分实际副本数与 availableReplicas 以支持扩缩容。如果没有 controller，此 API 只会存储数据，不会创建 Deployment。

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
  image: nginxinc/nginx-unprivileged:1.30.6-alpine
  port: 8080
```

controller 必须根据观测到的状态填充 status.replicas、availableReplicas、selector 和 observedGeneration。状态缺失或过时都不代表成功。对于提供多个 API 版本的情况，请检查存储版本、status.storedVersions 和转换。转换 webhook 必须实现所需的转换；更改版本名称并不会迁移数据。

## client-go、controller-runtime 和 Operators

client-go 提供 clients、informers/caches 和 workqueues。先执行一次 List 再执行 Watch 并不是完整的 controller：还要处理 resourceVersion 连续性、watch 关闭、410 Gone、重新连接和缓存同步，以及 context 取消和清理。

controller-runtime 提供 managers、cache/clients、workqueues、leader election 和协调模式。生成或提供自定义的 WebApp Go 类型并注册 scheme，然后针对所选库版本编译。引用缺失的 example.com/api 类型或 appsv1.WebApp 并不能构成可运行的实现。

以下内容是**伪代码**；其函数和部署配置必须另行实现。

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

ownerReferences 除了名称之外，还必须符合 UID、namespace 和作用域约束。盲目更新同名 Deployment 可能会修改其他 controller 的工作负载。垃圾回收取决于传播策略、所有者和 finalizer；ownerReference 不会清理任意外部 AWS 数据。

Operator 实现领域知识；故障转移、滚动升级和备份并不会自动变得安全。数据库设计需要考虑主节点隔离、quorum、副本追赶、WAL/备份恢复测试、Schema 兼容性、中断预算和关闭顺序。

按照官方 Operator SDK 1.42.3 安装说明选择操作系统/架构并核对校验和。不要在所有地方都安装旧的、仅支持 amd64 的 1.25.0 二进制文件。针对所选 SDK/plugin 验证 init/create api/make manifests，编译并测试生成的项目，然后分别构建/推送镜像并部署。

## API 聚合

APIService 将 group/version 路径路由到扩展 API server 的 Service。该 server 需要 TLS、发现、存储以及 list/watch 等 API 行为。验证 front-proxy 证书 CA/CN，维护转发用户身份的信任边界，并配置委托授权。

检查已安装的发现信息，确认实际的 metrics-server API 版本。不要使用虚构的 v1.metrics.k8s.io APIService，也不要默认使用 insecureSkipTLSVerify:true。Group/version、Service 和 caBundle 必须与真实 server 匹配。简单的 HTTP handler 或空 API group 并不是完整的 Kubernetes API server。

## Admission 策略和 Webhook

ValidatingAdmissionPolicy 自 Kubernetes 1.30 起已稳定，可在进程内运行 CEL 验证。此策略/绑定会将 production namespace 中的 Deployments 和 deployments/scale 请求的副本数限制为 1–5。它也会检查 HPA 和 kubectl scale 更新；请将 HPA maxReplicas 与此限制保持一致。Namespace 名称不等同于任意环境标签。应用策略前，请评估其运维影响。

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

Validating webhook 可以允许或拒绝请求；mutating webhook 可以返回 JSON Patch。响应时使用相同的 AdmissionReview 版本和请求 UID。patchType 为 JSONPatch，patch 字节在 JSON 中使用 Base64 编码。

此 Go handler 会在 Pod CREATE 时添加一个示例标签。标签缺失或为 null 时会创建 labels map，保留现有标签，并在值已匹配时不生成 patch。它会检查大小、方法、content type、版本、UID 以及 null 请求/对象。此标签并不会实际注入 sidecar。

### 已测试的 Webhook 代码

examples/platform/extensions/webhook 包含 go.mod、此实现及其测试。它只使用 Go 1.25 标准库。这些结构体声明了所用的 AdmissionReview 字段，并忽略其他字段。

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

测试通过 httptest 调用 handler，未打开 TLS listener。部署仍需要镜像、Service、证书/密钥文件、实际 CA bundle、API server 连通性、调用方身份验证和网络策略。此 TLS server 默认未配置客户端身份验证。Webhook 资源、操作和路径应与 handler 相匹配。

检查 failurePolicy、timeoutSeconds、sideEffects/dryRun、reinvocationPolicy 和 selectors。Webhook 不可用时，Fail 可能会阻止 API 请求；Ignore 则可能绕过检查。声明 None 必须与实际上不存在外部副作用的情况相符。

当前 Istio 的逐 Pod 注入使用 sidecar.istio.io/inject **标签**；namespace 使用 istio-injection 或 revision 标签。请核对 Pod 模板标签的位置和特定版本的注入规则，不要将旧的 annotation 示例继续作为默认配置。

## Scheduler Framework 和 Extender

Framework plugin 会编译并注册到 scheduler 二进制文件中。在 YAML 中命名为 CustomFilter 并不会加载缺失的代码。将 profile 的 schedulerName 与 Pod spec.schedulerName 匹配，以选择单独的 scheduler。

Filter 会移除候选项，Score 会为可行节点评分。请考虑 NormalizeScore、plugin 权重和并列结果的选择方式。Reserve/Unreserve 用于维护 plugin 的预留状态，并非永久性的容量预留 API。Permit 可以允许、拒绝或等待；PreBind/Bind/PostBind 负责绑定阶段。

Kubernetes 1.36.2 的公开 framework 使用 k8s.io/kube-scheduler/framework 中的 CycleState/NodeInfo，并将 NodeInfo 传给 Score。不要不加甄别地复制旧版的 nodeName-string/pointer 签名；请针对确切的次要版本编译。scheduler-plugins 0.35.7 不能自动与 1.36/1.37 二进制文件互换。

Extender 会公开独立的 HTTP(S) 端点。只配置已实现的 filter/prioritize/bind handler，并根据 nodeCacheCapable 支持 Nodes 或 NodeNames。之前的示例配置了 bindVerb，却没有实现它。请处理 nil 输入、请求体大小限制、超时、TLS/身份验证、故障策略和评分范围。对于简单的区域选择，应优先考虑内置的 node affinity。

## CNI

CNI 是运行时/网络插件的执行契约。CNI 库 1.3.1 与配置中的 cniVersion 不同。请验证共享的规范版本以及对 ADD、DEL、CHECK、STATUS 和 GC 等操作的支持。

成功的 ADD 必须反映实际的 namespace 接口、IPAM 和路由设置。在 JSON 中返回固定 IP 并不会建立连接，还可能导致冲突。DEL 必须清理部分失败的情况或缺失的 namespace；CHECK 必须检查实际状态。在多个节点上复制同一个 host-local 子网并不能提供集群 IPAM。

请检查所选 Calico、Cilium 或 Flannel 版本的功能及发行版兼容性。原始 Weave Net 仓库已归档，因此不将其作为新安装的默认选项。本次审核没有更改任何主机网络、veth、路由或 CNI 配置。

## CSI

CSI 1.13.0 定义了 Identity、Controller 和 Node RPC 集合及其能力。每个部署不一定都要在一个进程中提供全部三种集合。可以使用仅包含 Node 的 plugin；但声明的能力必须与实际 RPC 行为相符。

CreateVolume 必须处理幂等性、容量范围、拓扑、后端 ID 和错误。NodePublishVolume 必须根据请求的权限/只读行为正确挂载；NodeUnpublish/Delete 必须能够处理重试。始终返回 vol-123 或未挂载却报告成功，都不算实现了真正的 driver。

StorageClass/PVC 并不等于 driver 部署。provisioner 名称必须与已安装的 driver 匹配，参数也取决于具体 driver。请检查 controller sidecar、节点注册/socket/主机挂载、凭据、拓扑、volumeBindingMode 和 reclaimPolicy。请遵循 EBS、PD、Azure Disk 或 Ceph CSI 的官方安装/支持指南。

## 验证与参考资料

已阅读原始的 983 行韩文和 987 行英文指南、两份各 652 行的测验，以及 36 个不同的代码块。检查涵盖六种 CRD 输入情况、六种策略 CEL 情况、14 种 Go webhook 情况，以及四次实际 RFC6902 patch 应用。未执行完整的集群 controller、聚合 API server、scheduler 或 CNI/CSI driver。说明性伪代码并未标记为经过测试的实现。

- [CRD](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [聚合](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/)
- [Scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
- [Framework 1.36.2](https://github.com/kubernetes/kubernetes/blob/v1.36.2/staging/src/k8s.io/kube-scheduler/framework/interface.go)
- [controller-runtime 0.25.2](https://github.com/kubernetes-sigs/controller-runtime/tree/v0.25.2)
- [Operator SDK](https://sdk.operatorframework.io/docs/installation/)
- [CNI 1.3.1 源码](https://github.com/containernetworking/cni/blob/v1.3.1/SPEC.md)
- [CSI 1.13.0](https://github.com/container-storage-interface/spec/blob/v1.13.0/spec.md)
- [Istio 注入](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

[扩展机制测验](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
