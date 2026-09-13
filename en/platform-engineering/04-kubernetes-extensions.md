# Kubernetes Extension Mechanisms

> **Last Updated**: September 12, 2026

## Choosing an Extension Point

Kubernetes offers several ways to extend APIs and workload behavior. Registering a CRD is different from implementing its behavior.

| Mechanism | Role | Operational requirements |
| --- | --- | --- |
| CRD + controller | Custom API and desired-state reconciliation | Schema, reconciliation, RBAC, status and deletion |
| API aggregation | Delegate requests to a separate API server | APIService, TLS, delegated authentication/authorization, discovery/storage |
| Admission policy/webhook | Validate or mutate API requests | Scope, failure handling, CEL or webhook availability |
| Scheduler plugin/extender | Extend filtering, scoring or binding | Compatible scheduler binary, registration/configuration, failure handling |
| CNI | Container networking | Actual interfaces, IPAM, routes and cleanup |
| CSI | Volume lifecycle and node mounting | Capability-appropriate RPCs and backend/node operations |

Check compatibility for the chosen APIs, libraries and distribution. Current controller-runtime 0.25.0 uses Go 1.26 and Kubernetes Go modules 0.37.0. Scheduler interface notes below were checked against Kubernetes 1.36.2 source; do not assume scheduler-plugins 0.35.7 is interchangeable with it.

## CRDs and Instances

A CRD defines a custom API with an OpenAPI v3 structure. Required fields apply at their containing level, so require both top-level spec and spec.image explicitly. Manage status through its subresource and distinguish actual replicas from availableReplicas for scale. Without a controller, this API stores data but creates no Deployment.

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

The controller must populate status.replicas, availableReplicas, selector and observedGeneration from observed state. Missing or stale status is not success. For multiple served API versions, review storage version, status.storedVersions and conversion. A conversion webhook must implement required transformations; renaming a version does not migrate data.

## client-go, controller-runtime and Operators

client-go provides clients, informers/caches and workqueues. A one-shot List followed by Watch is not a complete controller: handle resourceVersion continuity, watch closure, 410 Gone, reconnection and cache synchronization, as well as context cancellation and cleanup.

controller-runtime supplies managers, cache/clients, workqueues, leader election and reconciliation patterns. Generate or provide the custom WebApp Go types and scheme registration, then compile against the chosen library version. References to missing example.com/api types or appsv1.WebApp do not form a runnable implementation.

The following is **pseudocode**; its functions and deployment configuration must be implemented separately.

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

ownerReferences must match UID, namespace and scope constraints as well as name. Blindly updating a same-named Deployment can mutate another controller's workload. Garbage collection depends on propagation, owners and finalizers; an ownerReference does not clean up arbitrary external AWS data.

An Operator implements domain knowledge; failover, rolling upgrades and backups are not automatically safe. Database designs need primary fencing, quorum, replica catch-up, WAL/backup restoration tests, schema compatibility, disruption budgets and shutdown ordering.

Use the official Operator SDK 1.42.3 installation instructions to select OS/architecture and checksums. Do not install the old amd64-only 1.25.0 binary everywhere. Verify init/create api/make manifests against the chosen SDK/plugin, compile/test the generated project, then separately build/push images and deploy.

## API Aggregation

APIService routes a group/version path to an extension API server's Service. The server needs TLS, discovery, storage and API behaviors such as list/watch. Validate front-proxy certificate CA/CN, preserve the trust boundary around forwarded user identity and configure delegated authorization.

Inspect installed discovery for the actual metrics-server API version. Do not use an invented v1.metrics.k8s.io APIService or insecureSkipTLSVerify:true as a default. Group/version, Service and caBundle must match the real server. A simple HTTP handler or empty API group is not a complete Kubernetes API server.

## Admission Policies and Webhooks

ValidatingAdmissionPolicy has been stable since Kubernetes 1.30 and runs CEL validation in-process. This policy/binding limits replicas to 1–5 for Deployments and deployments/scale requests in the production namespace. It also checks HPA and kubectl scale updates; align HPA maxReplicas with the limit. Namespace names are not equivalent to arbitrary environment labels. Review the operational impact before applying a policy.

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

Validating webhooks allow or deny requests; mutating webhooks can return JSON Patch. Respond using the same AdmissionReview version and request UID. patchType is JSONPatch and patch bytes are Base64-encoded in JSON.

This Go handler adds an illustrative label on Pod CREATE. It creates the labels map when missing/null, preserves existing labels and omits a patch when the value already matches. It checks size, method, content type, version, UID and null requests/objects. This label does not actually inject a sidecar.

### Tested Webhook Code

examples/platform/extensions/webhook contains go.mod, this implementation and its tests. It uses only Go 1.25 standard libraries. The structs declare consumed AdmissionReview fields and ignore additional fields.

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

Tests invoked the handler through httptest without opening a TLS listener. Deployment still requires an image, Service, certificate/key files, actual CA bundle, API-server connectivity, caller authentication and network policy. This TLS server does not configure client authentication by default. Match webhook resources, operations and paths to the handler.

Review failurePolicy, timeoutSeconds, sideEffects/dryRun, reinvocationPolicy and selectors. Fail can block API requests when a webhook is unavailable; Ignore can bypass its check. Declaring None must reflect actual absence of external side effects.

Current Istio per-Pod injection uses the sidecar.istio.io/inject **label**; namespaces use istio-injection or revision labels. Verify Pod-template label placement and version-specific injection rules rather than keeping old annotation examples as defaults.

## Scheduler Framework and Extenders

Framework plugins are compiled and registered inside a scheduler binary. Naming CustomFilter in YAML does not load missing code. Match the profile's schedulerName with Pod spec.schedulerName to select a separate scheduler.

Filter removes candidates and Score ranks feasible nodes. Account for NormalizeScore, plugin weights and tie selection. Reserve/Unreserve maintain plugin reservation state, not a permanent capacity-reservation API. Permit can allow, reject or wait; PreBind/Bind/PostBind handle binding stages.

The Kubernetes 1.36.2 public framework uses CycleState/NodeInfo from k8s.io/kube-scheduler/framework and passes NodeInfo to Score. Do not blindly copy old nodeName-string/pointer signatures; compile against the exact minor version. scheduler-plugins 0.35.7 is not automatically interchangeable with 1.36/1.37 binaries.

An extender exposes separate HTTP(S) endpoints. Configure only implemented filter/prioritize/bind handlers and support Nodes versus NodeNames according to nodeCacheCapable. The former example configured bindVerb without implementing it. Handle nil inputs, body limits, timeouts, TLS/authentication, failure policy and score ranges. For simple zone selection, first consider built-in node affinity.

## CNI

CNI is the runtime/network-plugin execution contract. CNI library 1.3.1 is distinct from config cniVersion. Verify shared spec versions and support for operations such as ADD, DEL, CHECK, STATUS and GC.

Successful ADD must reflect actual namespace interface, IPAM and route setup. Returning a fixed IP in JSON creates no connection and can cause collisions. DEL must clean up partial failures or missing namespaces; CHECK must inspect real state. Copying the same host-local subnet onto several nodes does not provide cluster IPAM.

Check selected Calico, Cilium or Flannel releases for features and distribution compatibility. The original Weave Net repository is archived and is not presented as a default new-install option. This audit changed no host networking, veth, routes or CNI configuration.

## CSI

CSI 1.13.0 defines Identity, Controller and Node RPC sets and capabilities. Every deployment need not supply all three in one process. Node-only plugins are possible; advertised capabilities must match actual RPC behavior.

CreateVolume must handle idempotency, capacity ranges, topology, backend IDs and errors. NodePublishVolume must mount correctly with requested permissions/read-only behavior; NodeUnpublish/Delete must handle retries. Always returning vol-123 or reporting success without mounting does not implement a real driver.

A StorageClass/PVC is not a driver deployment. The provisioner name must match an installed driver and parameters are driver-specific. Check controller sidecars, node registration/socket/host mounts, credentials, topology, volumeBindingMode and reclaimPolicy. Follow the official installation/support guidance for EBS, PD, Azure Disk or Ceph CSI.

## Verification and References

The original 983-line Korean and 987-line English guides, both 652-line quizzes and 36 unique code blocks were read. Checks covered six CRD input cases, six policy CEL cases, 14 Go webhook cases and four actual RFC6902 patch applications. No complete cluster controller, aggregated API server, scheduler or CNI/CSI driver was executed. Explanatory pseudocode is not labeled as tested implementation.

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

[Extension mechanisms quiz](../quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
