# Kubernetes 확장 메커니즘

> **검토일**: 2026년 9월 12일

## 확장 지점 선택

Kubernetes API와 workload의 동작을 확장하는 여러 방법이 있습니다. CRD를 등록하는 것과 실제 동작을 구현하는 것은 다릅니다.

| 방식 | 역할 | 운영 시 필요한 것 |
| --- | --- | --- |
| CRD + controller | 사용자 API와 원하는 상태의 조정 | schema, reconciliation, RBAC, 상태·삭제 처리 |
| API aggregation | 별도 API 서버로 요청 위임 | APIService, TLS, 인증·인가 위임, discovery·storage |
| Admission policy/webhook | API 요청의 검증 또는 변경 | 대상 범위, failure 처리, CEL 또는 webhook 가용성 |
| Scheduler plugin/extender | 배치 후보와 점수·바인딩 동작 확장 | 호환되는 scheduler binary, 등록·설정, 장애 처리 |
| CNI | container 네트워크 연결 | 실제 interface·IPAM·route·cleanup |
| CSI | volume lifecycle과 node mount | capability에 맞는 RPC와 backend·node 동작 |

지원 버전은 선택한 API·라이브러리·배포판에 따라 확인합니다. 현재 controller-runtime 0.25.0의 go.mod는 Go 1.26 및 Kubernetes Go module 0.37.0을 사용합니다. 아래 scheduler 인터페이스 설명은 Kubernetes 1.36.2 소스를 대조했으며 scheduler-plugins 0.35.7과 숫자가 다르다는 이유만으로 호환성을 가정하지 않습니다.

## CRD와 인스턴스

CRD는 OpenAPI v3 구조로 사용자 API를 정의합니다. required는 위치별로 적용되므로 최상위 spec과 spec.image를 각각 지정해야 합니다. status는 subresource로 관리하고 scale의 현재 replicas와 availableReplicas를 구분합니다. 아래 API는 controller 구현 전에는 데이터를 저장할 뿐 Deployment를 만들지 않습니다.

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

controller가 status.replicas, availableReplicas, selector와 observedGeneration을 실제 관찰값으로 갱신해야 합니다. status가 없거나 오래된 상태를 성공으로 표시하지 않습니다. 여러 API version을 serving할 때 저장 version, status.storedVersions와 conversion을 검토하며 conversion webhook은 필요한 변환 동작을 구현해야 합니다. version 문자열만 바꾸는 것이 데이터 migration은 아닙니다.

## client-go, controller-runtime과 Operator

client-go는 client, informer/cache, workqueue 등 controller를 구성할 도구를 제공합니다. List 후 단발 Watch를 여는 예제는 resourceVersion 간격, Watch 종료·410 Gone·재연결·cache sync를 처리하는 전체 controller가 아닙니다. context 취소와 watcher 정리도 필요합니다.

controller-runtime은 manager, cache/client, workqueue, leader election과 reconcile 구성을 제공합니다. 사용자 WebApp Go 타입과 scheme 등록을 생성하거나 준비하고, 선택한 버전의 API로 compile해야 합니다. 존재하지 않는 example.com/api 타입이나 appsv1.WebApp을 참조한 코드는 완성된 실행 예제가 아닙니다.

다음은 **의사코드**이며 함수 구현과 배포 구성이 별도로 필요합니다.

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

ownerReference는 이름뿐 아니라 UID·namespace·scope 조건에 맞아야 합니다. 이름이 같은 Deployment를 무조건 갱신하면 다른 controller의 workload를 변경할 수 있습니다. GC는 삭제 propagation·owner 관계·finalizer의 영향을 받으며, ownerReference 하나가 임의의 외부 AWS 데이터를 정리해 주지 않습니다.

Operator는 도메인 운영 지식을 구현하는 패턴입니다. failover, rolling upgrade와 backup이 자동으로 안전해지는 것은 아닙니다. DB를 예로 들면 primary fencing, quorum, replica catch-up, WAL·backup 복구 시험, schema 호환성, PDB와 종료 순서를 설계해야 합니다.

Operator SDK 1.42.3의 공식 설치 안내에서 OS/architecture와 checksum을 선택합니다. 원문의 amd64 1.25.0 파일을 모든 환경에 설치하지 않습니다. init/create api/make manifests 등은 선택한 SDK/plugin에서 확인하고 generated project가 compile·test된 후 image build/push와 배포를 별도로 수행합니다.

## API aggregation

APIService는 group/version 경로를 별도 extension API server의 Service에 연결합니다. extension 서버는 TLS와 discovery, 저장 backend와 list/watch 등 API 동작을 구현해야 합니다. front-proxy 인증서의 CA/CN을 검증하고 원본 사용자 정보의 신뢰 경계를 유지하며 위임 authorization도 구성합니다.

실제 metrics-server API version은 설치본의 discovery로 확인합니다. 임의의 v1.metrics.k8s.io APIService와 insecureSkipTLSVerify:true를 기본 예제로 쓰지 않습니다. APIService의 group/version·Service·caBundle이 실제 서버와 일치해야 합니다. 단순 HTTP handler나 빈 APIGroup 설치만으로 Kubernetes API server 구현이 완성되지 않습니다.

## Admission 정책과 webhook

ValidatingAdmissionPolicy는 Kubernetes 1.30부터 stable인 in-process CEL 검증 방식입니다. 아래 정책과 binding은 정확히 production namespace의 Deployment replica를 1~5로 제한하는 예제입니다. namespace 이름과 임의 environment label을 혼동하지 않습니다. 실제 적용은 운영 정책 변경이므로 영향 범위를 검토합니다.

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
        resources: [deployments]
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

Validating webhook은 요청을 허용·거절하고 mutating webhook은 JSON Patch로 변경할 수 있습니다. webhook은 같은 AdmissionReview version과 request UID를 돌려줘야 합니다. patchType은 JSONPatch이며 patch byte 배열은 JSON 응답에서 Base64로 인코딩됩니다.

아래 Go handler는 Pod CREATE 요청에 예시 label을 추가합니다. labels가 없거나 null이면 map을 먼저 만들고 기존 label은 보존하며, 이미 값이 맞으면 patch를 반환하지 않습니다. 요청 크기·method·content type·version·UID·nil request와 object를 검사합니다. 이 label은 실제 sidecar를 주입한다는 뜻이 아닙니다.

### 테스트한 webhook 코드

examples/platform/extensions/webhook에는 go.mod와 이 코드, 테스트가 있습니다. Go 1.25 표준 라이브러리만 사용했습니다. 코드는 AdmissionReview에서 사용하는 필드만 선언하고 알 수 없는 나머지 필드는 무시합니다.

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

이번 검증은 httptest로 handler를 호출했으며 실제 TLS listener를 열지 않았습니다. 배포하려면 image, Service, 인증서/키 파일, 실제 CA bundle, API server 연결 경로와 호출자 인증·network policy를 구성해야 합니다. 위 서버의 TLS는 기본적으로 client 인증을 구성하지 않습니다. webhook configuration의 resource/operation/path가 handler와 일치해야 합니다.

failurePolicy, timeoutSeconds, sideEffects와 dryRun, reinvocationPolicy, namespace/object selector를 검토합니다. unavailable webhook의 Fail 정책은 API 요청을 차단할 수 있고 Ignore는 검증을 건너뛸 수 있습니다. None은 선언만 적는 것이 아니라 실제로 외부 side effect가 없어야 합니다.

Istio의 현재 Pod별 주입 제어는 sidecar.istio.io/inject **label**을 사용하고 namespace에는 istio-injection 또는 revision label을 사용합니다. Pod template의 labels 위치와 해당 Istio 버전의 주입 규칙을 확인하며, 오래된 annotation 예제를 새 기본값으로 유지하지 않습니다.

## Scheduler Framework와 Extender

Framework plugin은 scheduler binary 안에 compile·등록됩니다. YAML에 CustomFilter 이름만 추가해도 코드가 로드되는 것은 아닙니다. profile의 schedulerName과 Pod의 spec.schedulerName을 맞춰 별도 scheduler로 전달해야 합니다.

Filter는 후보를 제외하고 Score는 적합한 후보에 점수를 부여합니다. NormalizeScore와 plugin weight를 적용한 합산 및 동률 선택을 고려합니다. Reserve/Unreserve는 plugin 상태의 예약·해제이며 영구적인 capacity 예약 API가 아닙니다. Permit은 허용·거절·대기하고 PreBind/Bind/PostBind는 바인딩 전후 단계를 처리합니다.

Kubernetes 1.36.2의 외부 framework 인터페이스는 k8s.io/kube-scheduler/framework의 CycleState/NodeInfo를 사용하고 Score에도 NodeInfo가 전달됩니다. 예전 nodeName string과 포인터 타입 signature를 그대로 복사하지 말고 정확한 minor 버전에서 compile하세요. v0.35.7 scheduler-plugins 배포를 1.36/1.37 binary와 무조건 혼합하지 않습니다.

Extender는 별도 HTTP(S) API입니다. filter/prioritize/bind 중 실제 구현한 endpoint만 설정하고 nodeCacheCapable에 따라 Nodes 또는 NodeNames가 전달되는 차이를 처리해야 합니다. 원문의 서버는 bind를 구현하지 않았는데 설정에서는 bindVerb를 켰습니다. nil Nodes, 제한된 요청 크기, timeout, TLS·인증, 장애 시 정책과 score 범위를 검토합니다. 단순 zone 선택이면 먼저 node affinity 같은 내장 기능을 검토하세요.

## CNI

CNI는 runtime과 network plugin 사이의 실행 계약입니다. CNI library 1.3.1과 config의 cniVersion은 다른 버전 값입니다. runtime/plugin이 공통으로 지원하는 spec version과 ADD/DEL/CHECK/STATUS/GC 등 작업의 지원을 확인합니다.

ADD 성공은 실제 namespace의 interface·IPAM·route 설정이 끝났음을 뜻해야 합니다. 고정 IP를 JSON으로 반환만 하는 구현은 연결을 만들지 않으며 충돌을 유발할 수 있습니다. DEL은 부분 실패나 namespace가 사라진 경우도 정리하고, CHECK는 실제 상태를 검사해야 합니다. host-local subnet을 여러 node에 동일하게 복사하는 것만으로 cluster IPAM이 완성되지 않습니다.

Calico, Cilium, Flannel 등은 선택한 버전의 기능과 배포판 호환성을 확인합니다. 원문에 나열된 Weave Net 저장소는 archived 상태이므로 새 설치 기본 선택지처럼 안내하지 않습니다. 이 검토에서 host network, veth, route 또는 CNI 설정은 변경하지 않았습니다.

## CSI

CSI 1.13.0은 Identity, Controller, Node RPC 집합과 capability를 정의합니다. 모든 배포가 한 process에서 세 서비스를 모두 제공해야 하는 것은 아닙니다. node-only plugin도 가능하며 광고하는 capability와 실제 RPC를 맞춰야 합니다.

CreateVolume은 idempotency, capacity 범위, topology, backend ID와 오류를 처리해야 합니다. NodePublishVolume은 실제 mount와 권한·읽기 전용 요구를 적용하고 NodeUnpublish/Delete가 재호출돼도 올바르게 처리해야 합니다. 항상 같은 vol-123을 반환하거나 아무 mount 없이 성공하는 코드는 실제 driver가 아닙니다.

StorageClass/PVC는 driver 배포가 아닙니다. provisioner 이름은 설치한 CSI driver와 정확히 일치하고 parameters는 driver별 값입니다. controller sidecar, node registrar와 socket/host mount, credential, topology·volumeBindingMode, reclaimPolicy를 함께 확인합니다. EBS, PD, Azure Disk, Ceph CSI 등은 각각의 공식 설치와 지원 표를 따릅니다.

## 검증 범위와 참고 자료

원문 한국어 983줄·영어 987줄과 각 퀴즈 652줄, 36개 고유 code block을 읽었습니다. 본문의 CRD 입력 6사례, 정책 CEL 6사례, Go webhook 14사례와 실제 RFC6902 patch 적용 4사례를 검증했습니다. 전체 cluster controller, aggregated API server, scheduler, CNI/CSI driver를 실행한 것은 아닙니다. 설명용 의사코드는 실행 검증된 구현으로 표시하지 않았습니다.

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

[확장 메커니즘 퀴즈](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
