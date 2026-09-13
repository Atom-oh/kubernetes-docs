# Extending Kubernetes

> **Upstream Kubernetes versions reviewed**: Kubernetes 1.35, 1.36, 1.37
> **Last Updated**: September 11, 2026

Kubernetes is a platform designed with extensibility in mind, allowing you to extend its functionality in various ways. In this chapter, we will explore the various methods to extend Kubernetes and how to leverage extension features in Amazon EKS.

## Table of Contents
1. [Kubernetes Extension Overview](#kubernetes-extension-overview)
2. [Custom Resources](#custom-resources)
3. [Operator Pattern](#operator-pattern)
4. [Admission Controllers](#admission-controllers)
5. [API Server Extensions](#api-server-extensions)
6. [Scheduler Extensions](#scheduler-extensions)
7. [Cloud Controller Manager](#cloud-controller-manager)
8. [CSI (Container Storage Interface)](#csi-container-storage-interface)
9. [CNI (Container Network Interface)](#cni-container-network-interface)
10. [Device Plugins](#device-plugins)
11. [Extension Features in Amazon EKS](#extension-features-in-amazon-eks)
12. [Best Practices](#best-practices)
13. [Conclusion](#conclusion)

## Kubernetes Extension Overview

Kubernetes provides various extension points to extend and customize its base functionality. The main extension points are:

1. **Custom Resources**: Define new API object types
2. **Operators**: Combine custom resources and controllers to manage complex applications
3. **Admission Controllers**: Intercept, modify, or validate API requests
4. **API Server Extensions**: Add new endpoints to the API server
5. **Scheduler Extensions**: Customize pod scheduling logic
6. **Cloud Controller Manager**: Integrate cloud provider-specific features
7. **CSI (Container Storage Interface)**: Integrate storage systems
8. **CNI (Container Network Interface)**: Integrate networking solutions
9. **Device Plugins**: Integrate special hardware

The following diagram shows the main extension points in Kubernetes:

![Architecture diagram showing the API server as the hub for custom resources, admission controllers, API server extensions, operators, the cloud controller manager, and scheduler extensions, with the node extended by CSI drivers, CNI plugins, and device plugins.](../.gitbook/assets/en-core-11-extending-kubernetes-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-core-11-extending-kubernetes-0.html)

### Choosing an Extension Method

Considerations when choosing an appropriate extension method:

1. **Use Case**: The type of functionality you want to extend
2. **Complexity**: Complexity of implementation and maintenance
3. **Performance Impact**: Impact of the extension on cluster performance
4. **Upgrade Compatibility**: Compatibility with Kubernetes version upgrades
5. **Community Support**: Level of community support for the extension method

## Custom Resources

Custom resources are a way to extend the Kubernetes API to define new object types.

The following diagram shows how custom resources work:

![Architecture diagram showing a user creating a CustomResourceDefinition and a custom resource instance, where the CRD defines and registers the schema, and the API server validates and stores the resulting instance in etcd.](../.gitbook/assets/en-core-11-extending-kubernetes-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-core-11-extending-kubernetes-1.html)

### Custom Resource Definitions (CRD)

CRD is the simplest way to define new resource types:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: backups.example.com
spec:
  group: example.com
  names:
    kind: Backup
    listKind: BackupList
    plural: backups
    singular: backup
    shortNames:
    - bk
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
            properties:
              source:
                type: string
              destination:
                type: string
              schedule:
                type: string
            required:
            - source
            - destination
          status:
            type: object
            properties:
              phase:
                type: string
              lastBackupTime:
                type: string
                format: date-time
    subresources:
      status: {}
    additionalPrinterColumns:
    - name: Status
      type: string
      jsonPath: .status.phase
    - name: Age
      type: date
      jsonPath: .metadata.creationTimestamp
```

In the above example, we define a new resource type called `Backup` and specify the resource's schema and additional printer columns.

### Creating Custom Resource Instances

After the CRD Established condition is true, create an instance. A CRD stores/validates data; it does not execute backups without a controller.

```yaml
apiVersion: example.com/v1
kind: Backup
metadata:
  name: daily-backup
spec:
  source: /data
  destination: s3://my-bucket/backups
  schedule: "0 0 * * *"
```

### Custom Resource Validation

You can validate custom resources using OpenAPI v3 schemas in CRDs:

```yaml
openAPIV3Schema:
  type: object
  properties:
    spec:
      type: object
      properties:
        replicas:
          type: integer
          minimum: 1
          maximum: 10
        image:
          type: string
          minLength: 1
      required:
      - replicas
      - image
```

In the above example, the `replicas` field must be an integer between 1 and 10, and the `image` field must be nonempty; image availability and signature checks require separate policy.

### Version Management

CRDs support multiple versions to enable API evolution:

```yaml
versions:
- name: v1alpha1
  served: true
  storage: false
- name: v1beta1
  served: true
  storage: false
- name: v1
  served: true
  storage: true
```

In the above example, three versions `v1alpha1`, `v1beta1`, and `v1` are served, but new writes use `v1`. This is a versions fragment: include a structural schema for every version. Existing objects are not automatically rewritten; migrate storage before removing an old storedVersions entry.

### Conversion Webhooks

You can use conversion webhooks to handle conversions between different versions:

```yaml
# Merge this spec fragment into the complete CRD above.
spec:
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: default
          name: example-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions:
      - v1
```

## Operator Pattern

The operator pattern is a way to automate operational knowledge of complex applications by combining custom resources and controllers.

The following diagram shows how the operator pattern works:

![Architecture diagram of the operator pattern: a user creates a custom resource stored in etcd via the Kubernetes API server, the operator's controller watches it and checks its status, determines an action, executes it against Kubernetes resources, and updates the custom resource status.](../.gitbook/assets/en-core-11-extending-kubernetes-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-core-11-extending-kubernetes-2.html)

### Operator Concepts

An operator consists of the following components:

1. **Custom Resource Definition (CRD)**: Defines the schema of resources to manage
2. **Controller**: Logic that monitors custom resources and reconciles them to the desired state
3. **Kubernetes API Client**: Client for interacting with the Kubernetes API

### Operator Example

Database operator example:

```yaml
# Custom Resource Definition
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databases.example.com
spec:
  group: example.com
  names:
    kind: Database
    listKind: DatabaseList
    plural: databases
    singular: database
    shortNames:
    - db
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
            properties:
              engine:
                type: string
                enum:
                - mysql
                - postgresql
              version:
                type: string
              storageSize:
                type: string
              replicas:
                type: integer
                minimum: 1
            required:
            - engine
            - version
            - storageSize
          status:
            type: object
            properties:
              phase:
                type: string
              endpoint:
                type: string
    subresources:
      status: {}
```

```yaml
# Database Instance
apiVersion: example.com/v1
kind: Database
metadata:
  name: my-db
spec:
  engine: postgresql
  version: "17"
  storageSize: 10Gi
  replicas: 3
```

### Operator Development Tools

Tools for developing operators:

1. **Operator SDK**: Develop operators using Go, Ansible, or Helm
2. **KUDO (Kubernetes Universal Declarative Operator)**: Develop operators declaratively
3. **Kubebuilder**: Go-based operator development framework
4. **Metacontroller**: Webhook-based operator development

#### Operator SDK Example

Creating an operator using Operator SDK:

```bash
: "${OPERATOR_IMAGE:?Set a registry image tag or digest you control}"
# Install a reviewed supported Operator SDK release and verify its checksum first.

# Create new operator project
operator-sdk init --domain example.com --repo github.com/example/database-operator

# Create API
operator-sdk create api --group database --version v1 --kind Database --resource --controller

# Implement controller (main.go, controllers/database_controller.go, etc.)

# Build and deploy operator
make docker-build docker-push IMG="$OPERATOR_IMAGE"
make deploy IMG="$OPERATOR_IMAGE"
```

### Popular Operators

Popular open source operators:

1. **Prometheus Operator**: Manages Prometheus monitoring stack
2. **Elasticsearch Operator**: Manages Elasticsearch clusters
3. **CoreOS etcd Operator (archived)**: Historical etcd automation example; not a current installation recommendation.
4. **PostgreSQL Operator**: Manages PostgreSQL databases
5. **OpenTelemetry Operator**: Deploys Jaeger v2; the former Jaeger Operator supports retired Jaeger v1 only.
6. **Strimzi Kafka Operator**: Manages Apache Kafka clusters
7. **Istio in-cluster Operator (removed in 1.24)**: Historical example; use supported Helm/istioctl installation workflows.
## Admission Controllers

Admission controllers are plugins that intercept requests to the Kubernetes API server and modify or validate them.

The following diagram shows how admission controllers work:

![Sequence diagram showing an API request passing through authentication and authorization, a mutating webhook, and a validating webhook before the API server persists the validated request to etcd.](../.gitbook/assets/en-core-11-extending-kubernetes-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-core-11-extending-kubernetes-3.html)

### Admission Controller Types

Kubernetes has two types of admission controllers:

1. **Mutating Admission Controllers**: Can modify resources
2. **Validating Admission Controllers**: Can only validate resources

### Built-in Admission Controllers

Kubernetes has several built-in admission controllers:

1. **NamespaceLifecycle**: Prevents resource creation in namespaces being deleted
2. **LimitRanger**: Sets default resource limits for pods and containers
3. **ServiceAccount**: Defaults/validates the Pod service account and injects a projected token volume unless automount is disabled; separate controllers create default accounts.
4. **DefaultStorageClass**: Assigns default storage class to PVCs
5. **ResourceQuota**: Limits resource usage per namespace
6. **PodSecurity**: Enforces namespace Pod Security Standards; PodSecurityPolicy was removed in 1.25.
7. **NodeRestriction**: Limits resources nodes can modify

### Webhook Admission Controllers

You can use webhook admission controllers to implement custom logic:

```yaml
# Mutating Webhook Configuration
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: pod-mutating-webhook
webhooks:
- name: pod-mutator.example.com
  clientConfig:
    service:
      namespace: default
      name: pod-mutating-webhook
      path: "/mutate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
    operations: ["CREATE"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

```yaml
# Validating Webhook Configuration
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-validating-webhook
webhooks:
- name: pod-validator.example.com
  clientConfig:
    service:
      namespace: default
      name: pod-validating-webhook
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
    operations: ["CREATE", "UPDATE"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

### Webhook Server Implementation

These Go snippets belong to one file and implement v1 AdmissionReview handlers. Wire /mutate and /validate to HTTPS with a Service-matching certificate and CA bundle. They perform no external side effects and are safe for dry-run; scope the webhook configuration to the intended namespaces. The tag check is a policy example, not full image-reference or signature validation.

```go
package main

import (
    "encoding/json"
    "net/http"
    "strings"
    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
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
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    if pod.Labels["injected-by"] == "mutating-webhook" {
        writePatch(w, req, nil)
        return
    }
    if pod.Labels == nil { pod.Labels = map[string]string{} }
    pod.Labels["injected-by"] = "mutating-webhook"
    // Add the whole map, preserving existing labels. Works when labels was absent.
    writePatch(w, req, []map[string]interface{}{{"op": "add", "path": "/metadata/labels", "value": pod.Labels}})
}
```

```go
func validateHandler(w http.ResponseWriter, r *http.Request) {
    req, pod, ok := readPodReview(w, r)
    if !ok { return }
    images := []string{}
    for _, c := range pod.Spec.Containers { images = append(images, c.Image) }
    for _, c := range pod.Spec.InitContainers { images = append(images, c.Image) }
    for _, c := range pod.Spec.EphemeralContainers { images = append(images, c.Image) }
    for _, image := range images {
        if strings.Contains(image, "@") { continue } // Digest references have no implicit latest tag.
        last := image[strings.LastIndex(image, "/")+1:]
        if !strings.Contains(last, ":") || strings.HasSuffix(last, ":latest") {
            deny(w, req, "Use an explicit non-latest tag or digest for every container")
            return
        }
    }
    writeReview(w, admissionv1.AdmissionResponse{UID: req.UID, Allowed: true})
}
```

### Popular Admission Controller Projects

1. **OPA Gatekeeper**: Policy enforcement using Open Policy Agent
2. **Kyverno**: YAML-based policy engine
3. **Istio**: Service mesh sidecar injection
4. **cert-manager**: TLS certificate management

## API Server Extensions

API server extensions are a way to add new endpoints to the Kubernetes API server.

### Extension API Servers

Extension API servers are servers that run separately from the Kubernetes API server and provide custom APIs:

```yaml
# APIService Definition
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1.example.com
spec:
  group: example.com
  version: v1
  groupPriorityMinimum: 1000
  versionPriority: 15
  service:
    name: example-api
    namespace: default
  caBundle: <base64-encoded-ca-cert>
```

### Extension API Server Implementation

An extension API server consists of the following components:

1. **API Server**: Provides an interface similar to the Kubernetes API server
2. **Resource Handlers**: Handles requests for specific resource types
3. **Storage Backend**: Stores resource data

This is an implementation outline, not a standalone program. Start from the official sample-apiserver version matching your k8s.io dependencies; configure secure serving, delegated authentication/authorization, the actual example.com/v1 types, storage and shutdown context. APIService group/version must match the server.

```go
// Extension API Server Example
func main() {
    // Server configuration
    config := genericapiserver.NewRecommendedConfig(apiserver.Codecs)
    config.OpenAPIConfig = genericapiserver.DefaultOpenAPIConfig(
        sampleopenapi.GetOpenAPIDefinitions,
        openapi.NewDefinitionNamer(apiserver.Scheme),
    )
    config.EnableIndex = true
    config.EnableDiscovery = true

    // Create server
    server, err := config.Complete().New("sample-apiserver", genericapiserver.NewEmptyDelegate())
    if err != nil {
        log.Fatalf("Error creating server: %v", err)
    }

    // Set API group info
    apiGroupInfo := genericapiserver.NewDefaultAPIGroupInfo(
        samplev1.GroupName,
        apiserver.Scheme,
        metav1.ParameterCodec,
        apiserver.Codecs,
    )

    // Set storage
    apiGroupInfo.VersionedResourcesStorageMap["v1"] = map[string]rest.Storage{
        "widgets": NewWidgetStorage(),
    }

    // Install API group
    if err := server.InstallAPIGroup(&apiGroupInfo); err != nil {
        log.Fatalf("Error installing API group: %v", err)
    }

    // Run server
    if err := server.PrepareRun().Run(stopCh); err != nil {
        log.Fatalf("Error running server: %v", err)
    }
}
```

### Aggregation Layer

The aggregation layer makes multiple API servers appear as a single API server:

```
                                   +-----------------+
                                   |                 |
                                   |  kube-apiserver |
                                   |                 |
                                   +-------+---------+
                                           |
                                           v
                      +--------------------+--------------------+
                      |                                         |
                      |                                         |
          +-----------v-----------+               +------------v------------+
          |                       |               |                         |
          |  metrics-server       |               |  example-apiserver      |
          |                       |               |                         |
          +-----------------------+               +-------------------------+
```

## Scheduler Extensions

Scheduler extensions are a way to customize the behavior of the Kubernetes scheduler.

### Scheduler Framework

The scheduler framework introduced in Kubernetes 1.15 allows extending various stages of the scheduling pipeline through plugins:

1. **Queue Sort**: Sort pods in the scheduling queue
2. **Pre-filter**: Check pod and cluster state before filtering
3. **Filter**: Filter out nodes that cannot run the pod
4. **Post-filter**: Perform actions after filtering
5. **Pre-score**: Perform actions before score calculation
6. **Score**: Assign scores to nodes
7. **Normalize Score**: Normalize scores
8. **Reserve**: Reserve resources for the pod
9. **Permit**: Allow, deny, or delay pod scheduling
10. **Pre-bind**: Perform actions before binding
11. **Bind**: Bind the pod to a node
12. **Post-bind**: Perform actions after binding

### Scheduler Configuration

Scheduler configuration example:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

### Custom Scheduler

The following Deployment requires a built custom-scheduler image, a ConfigMap named custom-scheduler-config containing the preceding config.yaml, and a ServiceAccount with reviewed scheduling/Lease RBAC. Use in-cluster authentication; a worker cannot mount a managed control plane’s scheduler.conf. The schedulerName must match the Pod.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: custom-scheduler
  template:
    metadata:
      labels:
        app: custom-scheduler
    spec:
      serviceAccountName: custom-scheduler
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: custom-scheduler
        image: example/custom-scheduler:REPLACE_WITH_TESTED_RELEASE
        command: [/custom-scheduler, --config=/etc/scheduler/config.yaml]
        volumeMounts:
        - name: config
          mountPath: /etc/scheduler
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: custom-scheduler-config
```

Specifying a custom scheduler for a pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: custom-scheduler
  containers:
  - name: container
    image: nginx:1.30.4
```

## Cloud Controller Manager

The cloud controller manager provides an interface between Kubernetes and cloud providers.

### Cloud Controller Manager Components

The cloud controller manager consists of the following controllers:

1. **Node Controller**: Updates node information through cloud provider APIs
2. **Route Controller**: Sets up routes in cloud networks
3. **Service Controller**: Creates, updates, and deletes cloud load balancers

### AWS Cloud Controller Manager

The external AWS CCM is for **self-managed Kubernetes on AWS**. Choose a cloud-provider-aws release compatible with Kubernetes and follow its existing-cluster procedure for ServiceAccount/RBAC, IAM, cluster tags, node naming and `--cloud-provider=external` migration prerequisites. Its image repository is `registry.k8s.io/provider-aws/cloud-controller-manager`. Arbitrary cloud.conf entries cannot replace VPC/subnet tagging.

You cannot install this DaemonSet into the AWS-managed EKS control plane or mount its scheduler.conf. On EKS, use service-managed cloud integration and supported AWS Load Balancer Controller or Auto Mode capabilities, with one controller owner per resource.

## CSI (Container Storage Interface)

CSI provides a standard interface between Kubernetes and storage systems.

The following diagram shows the architecture and operation of CSI:

![Architecture diagram showing a user-created PersistentVolumeClaim referencing a StorageClass and CSI external provisioner that requests a volume from the CSI driver, whose controller and node services create and mount the volume on the storage system, bound as a PersistentVolume and mounted into the Pod.](../.gitbook/assets/en-core-11-extending-kubernetes-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-core-11-extending-kubernetes-4.html)

### CSI Architecture

CSI consists of the following components:

1. **CSI Controller Plugin**: Handles volume creation, deletion, snapshots, etc.
2. **CSI Node Plugin**: Handles volume mount, unmount, etc.
3. **CSI Driver**: Implementation that integrates with specific storage systems

```
+-------------------+
|                   |
|  Kubernetes       |
|  (External        |
|   Provisioner)    |
|                   |
+--------+----------+
         |
         | gRPC
         v
+--------+----------+
|                   |
|  CSI Driver       |
|                   |
+--------+----------+
         |
         | Storage Protocol
         v
+--------+----------+
|                   |
|  Storage System   |
|                   |
+-------------------+
```

### CSI Driver Deployment

The following is a driver-author template, not a complete install. Supply the driver image/arguments, compatible sidecar releases, ServiceAccounts/RBAC and CSIDriver registration from the vendor. NodePlugin runs on Linux and requires the documented host paths and privileges.

```yaml
# CSI Controller Service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: csi-controller
spec:
  replicas: 1
  selector:
    matchLabels:
      app: csi-controller
  template:
    metadata:
      labels:
        app: csi-controller
    spec:
      serviceAccountName: csi-controller
      nodeSelector:
        kubernetes.io/os: linux
      containers:
      - name: csi-provisioner
        image: registry.k8s.io/sig-storage/csi-provisioner:REPLACE_WITH_COMPATIBLE_RELEASE
        args:
        - "--csi-address=$(ADDRESS)"
        - "--v=5"
        env:
        - name: ADDRESS
          value: /var/lib/csi/sockets/pluginproxy/csi.sock
        volumeMounts:
        - name: socket-dir
          mountPath: /var/lib/csi/sockets/pluginproxy/
      - name: csi-attacher
        image: registry.k8s.io/sig-storage/csi-attacher:REPLACE_WITH_COMPATIBLE_RELEASE
        args:
        - "--csi-address=$(ADDRESS)"
        - "--v=5"
        env:
        - name: ADDRESS
          value: /var/lib/csi/sockets/pluginproxy/csi.sock
        volumeMounts:
        - name: socket-dir
          mountPath: /var/lib/csi/sockets/pluginproxy/
      - name: csi-driver
        image: example/csi-driver:v1.0.0
        args:
        - "--endpoint=$(CSI_ENDPOINT)"
        - "--nodeid=$(NODE_ID)"
        env:
        - name: CSI_ENDPOINT
          value: unix:///var/lib/csi/sockets/pluginproxy/csi.sock
        - name: NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        volumeMounts:
        - name: socket-dir
          mountPath: /var/lib/csi/sockets/pluginproxy/
      volumes:
      - name: socket-dir
        emptyDir: {}

---
# CSI Node Service
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: csi-node
spec:
  selector:
    matchLabels:
      app: csi-node
  template:
    metadata:
      labels:
        app: csi-node
    spec:
      serviceAccountName: csi-node
      nodeSelector:
        kubernetes.io/os: linux
      hostNetwork: true
      containers:
      - name: csi-node-driver-registrar
        image: registry.k8s.io/sig-storage/csi-node-driver-registrar:REPLACE_WITH_COMPATIBLE_RELEASE
        args:
        - "--csi-address=$(ADDRESS)"
        - "--kubelet-registration-path=$(DRIVER_REG_SOCK_PATH)"
        - "--v=5"
        env:
        - name: ADDRESS
          value: /csi/csi.sock
        - name: DRIVER_REG_SOCK_PATH
          value: /var/lib/kubelet/plugins/example.csi.k8s.io/csi.sock
        volumeMounts:
        - name: plugin-dir
          mountPath: /csi
        - name: registration-dir
          mountPath: /registration
      - name: csi-driver
        image: example/csi-driver:v1.0.0
        args:
        - "--endpoint=$(CSI_ENDPOINT)"
        - "--nodeid=$(NODE_ID)"
        env:
        - name: CSI_ENDPOINT
          value: unix:///csi/csi.sock
        - name: NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        securityContext:
          privileged: true
        volumeMounts:
        - name: plugin-dir
          mountPath: /csi
        - name: pods-mount-dir
          mountPath: /var/lib/kubelet/pods
          mountPropagation: "Bidirectional"
      volumes:
      - name: plugin-dir
        hostPath:
          path: /var/lib/kubelet/plugins/example.csi.k8s.io
          type: DirectoryOrCreate
      - name: registration-dir
        hostPath:
          path: /var/lib/kubelet/plugins_registry
          type: Directory
      - name: pods-mount-dir
        hostPath:
          path: /var/lib/kubelet/pods
          type: Directory
```

### Storage Class and PVC

Storage class and PVC example using CSI driver:

```yaml
# Storage Class
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: example-csi
provisioner: example.csi.k8s.io
parameters:
  type: ssd
  csi.storage.k8s.io/fstype: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer

---
# PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: example-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: example-csi
```

### Popular CSI Drivers

1. **AWS EBS CSI Driver**: AWS EBS volume management
2. **AWS EFS CSI Driver**: AWS EFS file system management
3. **GCE PD CSI Driver**: Google Compute Engine persistent disk management
4. **Azure Disk CSI Driver**: Azure disk management
5. **Ceph RBD CSI Driver**: Ceph RBD volume management
6. **NFS CSI Driver**: NFS volume management

## CNI (Container Network Interface)

CNI provides a standard interface between Kubernetes and networking solutions.

The following diagram shows the architecture and operation of CNI:

![Architecture diagram showing kubelet asking the container runtime to create a container, which requests network setup from the CNI plugin, which in turn allocates an IP from the IPAM plugin's pool and applies network configuration to the pod network.](../.gitbook/assets/en-core-11-extending-kubernetes-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-core-11-extending-kubernetes-5.html)

### CNI Architecture

CNI consists of the following components:

1. **CNI Plugin**: Configures container network interfaces
2. **IPAM Plugin**: IP address allocation and management
3. **Meta Plugin**: Combines multiple plugins together

```
+-------------------+
|                   |
|  Kubernetes       |
|  CRI runtime      |
|  (via kubelet)    |
+--------+----------+
         |
         | CNI Spec
         v
+--------+----------+
|                   |
|  CNI Plugin       |
|                   |
+--------+----------+
         |
         | Network Configuration
         v
+--------+----------+
|                   |
|  Network          |
|                   |
+-------------------+
```

### CNI Plugin Configuration

This single-node bridge/host-local example illustrates the CNI contract; a cluster needs unique per-node subnets and cross-node routing. CNI is called by the CRI runtime, not directly by modern kubelet.

```json
{
  "cniVersion": "0.4.0",
  "name": "example-network",
  "type": "bridge",
  "bridge": "cni0",
  "isGateway": true,
  "ipMasq": true,
  "ipam": {
    "type": "host-local",
    "subnet": "10.244.0.0/24",
    "routes": [
      { "dst": "0.0.0.0/0" }
    ]
  }
}
```

### Popular CNI Plugins

1. **Calico**: CNI with enhanced network policy and security features
2. **Flannel**: Provides simple overlay networking
3. **Cilium**: eBPF-based networking and security solution
4. **Weave Net (archived)**: Historical multi-host networking project; evaluate maintained alternatives.
5. **AWS VPC CNI**: CNI integrated with AWS VPC
6. **Azure CNI**: CNI integrated with Azure virtual networks
7. **Antrea**: Open vSwitch-based networking solution

### CNI Plugin Installation

Calico CNI plugin installation example:

```bash
# Use the official Calico installation guide for your distribution.
# Select a supported release and inspect the operator/custom-resources manifests.
# Do not install a second primary CNI over an existing cluster network.
kubectl get nodes -o wide
kubectl -n kube-system get daemonsets
```

## Device Plugins

Device plugins provide an interface between Kubernetes and special hardware.

### Device Plugin Architecture

Device plugins consist of the following components:

1. **Device Plugin Server**: Handles device discovery, allocation, initialization, etc.
2. **kubelet**: Communicates with device plugins to allocate devices to pods

```
+-------------------+
|                   |
|  Kubernetes       |
|  (kubelet)        |
|                   |
+--------+----------+
         |
         | Device Plugin API
         v
+--------+----------+
|                   |
|  Device Plugin    |
|                   |
+--------+----------+
         |
         | Device Management
         v
+--------+----------+
|                   |
|  Hardware Device  |
|                   |
+-------------------+
```

### NVIDIA GPU Device Plugin

NVIDIA GPU device plugin deployment example:

First configure compatible NVIDIA drivers, Container Toolkit and container runtime. Pin a tested official NVIDIA device-plugin Helm chart release and select Linux GPU nodes. Avoid a duplicate installation when GPU Operator or Auto Mode already owns the plugin.

### GPU Request Pod

Pod example requesting GPU:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  restartPolicy: Never
  nodeSelector:
    kubernetes.io/os: linux
  containers:
  - name: cuda-container
    image: nvidia/cuda:REPLACE_WITH_DRIVER_COMPATIBLE_TAG
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

### Popular Device Plugins

1. **NVIDIA GPU Device Plugin**: NVIDIA GPU management
2. **AMD GPU Device Plugin**: AMD GPU management
3. **FPGA Device Plugin**: FPGA device management
4. **InfiniBand Device Plugin**: InfiniBand device management
5. **SR-IOV Network Device Plugin**: SR-IOV network device management

## Extension Features in Amazon EKS

EKS version support differs from upstream. As of 2026-09-11, EKS standard support covers 1.34–1.36; check each add-on/controller compatibility matrix too.

Amazon EKS supports various extension features to extend Kubernetes cluster functionality.

The following diagram shows the extension feature architecture in Amazon EKS:

![EKS manages the control plane; add-on workloads run on compatible worker compute. IRSA grants permissions to Pods using ServiceAccounts, while node IAM roles are separate. ACK reconciles AWS resources through AWS APIs.](../.gitbook/assets/en-core-11-extending-kubernetes-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-core-11-extending-kubernetes-6.html)

### EKS Add-ons

Amazon EKS provides the following add-ons:

1. **Amazon VPC CNI**: Networking integrated with AWS VPC
2. **CoreDNS**: DNS service within the cluster
3. **kube-proxy**: Network proxy
4. **Amazon EBS CSI Driver**: EBS volume management
5. **AWS Load Balancer Controller**: Separately installed with supported Helm/manifests; do not assume every extension is an EKS managed add-on.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set cluster name}"
KUBERNETES_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --query cluster.version --output text)
aws eks list-addons --cluster-name "$CLUSTER_NAME"
aws eks describe-addon-versions --addon-name amazon-ebs-csi-driver --kubernetes-version "$KUBERNETES_VERSION"
# Choose a compatible version and prepare the controller's scoped IAM role first.
: "${ADDON_VERSION:?Set reviewed compatible add-on version}"
: "${EBS_ROLE_ARN:?Set EBS CSI IRSA role ARN}"
aws eks create-addon --cluster-name "$CLUSTER_NAME" --addon-name amazon-ebs-csi-driver \
  --addon-version "$ADDON_VERSION" --service-account-role-arn "$EBS_ROLE_ARN"
# For an existing installation, use update-addon instead of create-addon.
# To stop EKS management while retaining the workload (not uninstall it):
# aws eks delete-addon --cluster-name "$CLUSTER_NAME" --addon-name amazon-ebs-csi-driver --preserve
```

### AWS Controllers for Kubernetes (ACK)

ACK is a collection of operators that allows managing AWS resources from Kubernetes:

```bash
set -euo pipefail
: "${ACK_VERSION:?Set a reviewed S3 controller chart version}"
: "${AWS_REGION:?Set target service region}"
# First prepare ack-s3-controller ServiceAccount with scoped IRSA/Pod Identity permissions.
helm upgrade --install ack-s3-controller oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version "$ACK_VERSION" --namespace ack-system --create-namespace \
  --set aws.region="$AWS_REGION" --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller
# Creating a Bucket CR provisions a real AWS resource: review IAM, naming and retention first.
```

The following Bucket example provisions an actual AWS resource when the controller and IAM permissions are configured. Replace the name with a globally unique value and review lifecycle/retention settings. Deleting the Kubernetes object can delete the bucket; configure the controller deletion policy for your data-retention requirements.

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: example-bucket
spec:
  name: replace-with-your-globally-unique-bucket-name
```

### AWS Load Balancer Controller

The AWS Load Balancer Controller integrates Kubernetes services and ingresses with AWS load balancers:

```yaml
# ALB Ingress example
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

### IAM Roles for Service Accounts (IRSA)

IRSA allows pods to securely access AWS services by associating AWS IAM roles with Kubernetes service accounts:

```bash
# Create OIDC provider
: "${S3_READ_POLICY_ARN:?Set a customer-managed policy restricted to your bucket/prefix}"
eksctl utils associate-iam-oidc-provider \
  --cluster my-cluster \
  --approve

# Create IAM role and service account
eksctl create iamserviceaccount \
  --cluster my-cluster \
  --namespace default \
  --name my-service-account \
  --attach-policy-arn "$S3_READ_POLICY_ARN" \
  --approve

# Pod using service account
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
spec:
  serviceAccountName: my-service-account
  restartPolicy: Never
  containers:
  - name: aws-cli
    image: public.ecr.aws/aws-cli/aws-cli:REPLACE_WITH_TESTED_RELEASE
    command: [aws]
    args: [sts, get-caller-identity]
EOF
```

## Best Practices

Let's explore best practices to consider when implementing Kubernetes extension features.

### Design Best Practices

1. **Use Standard Interfaces**: Use standard interfaces like CSI, CNI when possible
2. **Declarative API Design**: Design declarative APIs rather than imperative
3. **Follow Kubernetes Design Principles**: Follow principles like controller pattern, level-triggering
4. **Version Management**: Manage API versions and maintain compatibility
5. **Least Privilege Principle**: Grant only the minimum necessary permissions

### Implementation Best Practices

1. **Leverage Reusable Libraries**: Leverage libraries like client-go, controller-runtime
2. **Proper Error Handling**: Proper handling and logging for error situations
3. **Exponential Backoff**: Use exponential backoff for retries
4. **Set Resource Limits**: Set memory and CPU limits
5. **Status Reporting**: Report resource status accurately

### Deployment Best Practices

1. **Gradual Rollout**: Roll out gradually rather than changing everything at once
2. **Version Management**: Avoid using latest tag for images
3. **Health Checks**: Configure appropriate liveness and readiness probes
4. **Logging and Monitoring**: Configure comprehensive logging and monitoring
5. **Documentation**: Document APIs and usage

### Security Best Practices

1. **Least Privilege Principle**: Grant only the minimum necessary permissions
2. **Use RBAC**: Configure appropriate RBAC policies
3. **Network Policies**: Configure appropriate network policies
4. **Image Scanning**: Scan container images for vulnerabilities
5. **Secret Management**: Manage secrets securely

### EKS-Specific Best Practices

1. **Use Managed Add-ons**: Use EKS managed add-ons when possible
2. **Use IRSA**: Use IRSA for per-pod IAM permission management
3. **VPC CNI Configuration**: Configure VPC CNI according to networking requirements
4. **Security Groups**: Configure appropriate security groups
5. **Cost Optimization**: Select appropriate instance types and sizes

## Conclusion

Kubernetes provides various extension points to extend and customize its base functionality. Custom resources, operators, admission controllers, API server extensions, scheduler extensions, CSI, CNI, and device plugins allow you to adapt Kubernetes to various environments and requirements.

Amazon EKS supports these extension features and additionally provides AWS-specific features like EKS add-ons, ACK, AWS Load Balancer Controller, and IRSA to simplify integration between Kubernetes and AWS services.

When implementing Kubernetes extension features, it's important to follow best practices such as using standard interfaces, declarative API design, and the least privilege principle. This allows you to build stable and scalable Kubernetes environments.

## Quiz

To test what you learned in this chapter, try the [Extending Kubernetes Quiz](../quizzes/core/11-extending-kubernetes-quiz.md).

## Verification References

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
