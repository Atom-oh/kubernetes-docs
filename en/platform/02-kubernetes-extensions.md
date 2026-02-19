# Kubernetes Extension Mechanisms

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: November 24, 2025

## Overview

Kubernetes provides various extension mechanisms to extend and customize its base functionality. This document explores Kubernetes' main extension mechanisms and explains real-world use cases and implementation methods.

## Custom Resource Definitions (CRD)

Custom Resource Definitions (CRDs) are a mechanism that allows you to extend the Kubernetes API to define custom resources.

### CRD Basic Concepts

Using CRDs provides the following benefits:

1. **Declarative API**: You can leverage Kubernetes' declarative API model.
2. **kubectl Integration**: Custom resources can be managed the same way as native Kubernetes resources.
3. **Version Management**: Resource schemas can evolve through API version management.
4. **Validation**: Resource validation can be performed through OpenAPI v3 schemas.

### CRD Creation Example

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.example.com
spec:
  group: example.com
  names:
    kind: WebApp
    listKind: WebAppList
    plural: webapps
    singular: webapp
    shortNames:
      - wa
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
                replicas:
                  type: integer
                  minimum: 1
                image:
                  type: string
                port:
                  type: integer
              required: ["image"]
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      lastTransitionTime:
                        type: string
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
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.availableReplicas
```

### Custom Resource Instance Creation

```yaml
apiVersion: example.com/v1
kind: WebApp
metadata:
  name: my-webapp
spec:
  replicas: 3
  image: nginx:1.21
  port: 80
```

## Custom Controllers

Custom resources alone cannot implement actual behavior. Custom controllers watch the state of custom resources and perform actions to achieve the desired state.

### Controller Pattern

Kubernetes controllers follow this pattern:

1. **Observe**: Observe the current state of resources.
2. **Analyze**: Analyze the difference between current state and desired state.
3. **Act**: Take action to achieve the desired state.

### Controller Implementation Methods

#### 1. Using client-go

```go
package main

import (
    "context"
    "fmt"
    "time"

    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/client-go/kubernetes"
    "k8s.io/client-go/tools/clientcmd"
    "k8s.io/client-go/util/homedir"
    "path/filepath"
)

func main() {
    // Load kubeconfig
    kubeconfig := filepath.Join(homedir.HomeDir(), ".kube", "config")
    config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
    if err != nil {
        panic(err)
    }

    // Create Kubernetes client
    clientset, err := kubernetes.NewForConfig(config)
    if err != nil {
        panic(err)
    }

    // Get pod list
    pods, err := clientset.CoreV1().Pods("default").List(context.TODO(), metav1.ListOptions{})
    if err != nil {
        panic(err)
    }

    fmt.Printf("There are %d pods in the default namespace\n", len(pods.Items))

    // Watch pods
    watch, err := clientset.CoreV1().Pods("default").Watch(context.TODO(), metav1.ListOptions{})
    if err != nil {
        panic(err)
    }

    // Handle events
    for event := range watch.ResultChan() {
        fmt.Printf("Event: %s\n", event.Type)
    }
}
```

#### 2. Using controller-runtime

```go
package main

import (
    "context"

    appsv1 "k8s.io/api/apps/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    ctrl "sigs.k8s.io/controller-runtime"
    "sigs.k8s.io/controller-runtime/pkg/client"
    "sigs.k8s.io/controller-runtime/pkg/log"

    examplev1 "example.com/api/v1"
)

// WebAppReconciler reconciles a WebApp object
type WebAppReconciler struct {
    client.Client
    Scheme *runtime.Scheme
}

func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // Get WebApp instance
    var webapp examplev1.WebApp
    if err := r.Get(ctx, req.NamespacedName, &webapp); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }

    // Create or update Deployment
    deployment := &appsv1.Deployment{}
    err := r.Get(ctx, client.ObjectKey{Namespace: webapp.Namespace, Name: webapp.Name}, deployment)
    if client.IgnoreNotFound(err) != nil {
        return ctrl.Result{}, err
    }

    if err != nil {
        // Create Deployment if it doesn't exist
        deployment = &appsv1.Deployment{
            ObjectMeta: metav1.ObjectMeta{
                Name:      webapp.Name,
                Namespace: webapp.Namespace,
            },
        }

        if err := ctrl.SetControllerReference(&webapp, deployment, r.Scheme); err != nil {
            return ctrl.Result{}, err
        }

        // Set Deployment spec
        replicas := int32(webapp.Spec.Replicas)
        deployment.Spec.Replicas = &replicas
        deployment.Spec.Selector = &metav1.LabelSelector{
            MatchLabels: map[string]string{"app": webapp.Name},
        }
        deployment.Spec.Template.ObjectMeta.Labels = map[string]string{"app": webapp.Name}
        deployment.Spec.Template.Spec.Containers = []corev1.Container{
            {
                Name:  "webapp",
                Image: webapp.Spec.Image,
                Ports: []corev1.ContainerPort{
                    {
                        ContainerPort: int32(webapp.Spec.Port),
                    },
                },
            },
        }

        if err := r.Create(ctx, deployment); err != nil {
            log.Error(err, "Failed to create Deployment")
            return ctrl.Result{}, err
        }

        log.Info("Created Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
    } else {
        // Update Deployment if it exists
        replicas := int32(webapp.Spec.Replicas)
        deployment.Spec.Replicas = &replicas
        deployment.Spec.Template.Spec.Containers[0].Image = webapp.Spec.Image

        if err := r.Update(ctx, deployment); err != nil {
            log.Error(err, "Failed to update Deployment")
            return ctrl.Result{}, err
        }

        log.Info("Updated Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
    }

    // Update status
    webapp.Status.AvailableReplicas = int(deployment.Status.AvailableReplicas)
    if err := r.Status().Update(ctx, &webapp); err != nil {
        log.Error(err, "Failed to update WebApp status")
        return ctrl.Result{}, err
    }

    return ctrl.Result{}, nil
}

func (r *WebAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&examplev1.WebApp{}).
        Owns(&appsv1.Deployment{}).
        Complete(r)
}

func main() {
    scheme := runtime.NewScheme()
    _ = examplev1.AddToScheme(scheme)
    _ = appsv1.AddToScheme(scheme)
    _ = corev1.AddToScheme(scheme)

    mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
        Scheme: scheme,
    })
    if err != nil {
        panic(err)
    }

    if err := (&WebAppReconciler{
        Client: mgr.GetClient(),
        Scheme: mgr.GetScheme(),
    }).SetupWithManager(mgr); err != nil {
        panic(err)
    }

    if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
        panic(err)
    }
}
```

### Operator Pattern

An Operator is a pattern that combines CRDs and controllers to automate application-specific operational knowledge.

**Key Characteristics of Operators:**

1. **Domain Knowledge Automation**: Implements application domain knowledge as code.
2. **Declarative Management**: Users declare the desired state, and the Operator performs actions to achieve it.
3. **Self-healing**: Detects failure conditions and automatically recovers.
4. **Upgrade Management**: Safely handles application upgrades.

**Operator Examples:**

- **Prometheus Operator**: Manages the Prometheus monitoring stack.
- **Elasticsearch Operator**: Manages Elasticsearch clusters.
- **PostgreSQL Operator**: Manages PostgreSQL databases.

### Operator SDK

Operator SDK is a tool that simplifies Operator development.

**Operator Creation:**

```bash
# Install Operator SDK
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.25.0/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
sudo mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# Create Operator project
operator-sdk init --domain example.com --repo github.com/example/webapp-operator

# Create API
operator-sdk create api --group apps --version v1 --kind WebApp --resource --controller

# Generate CRD
make manifests

# Build and deploy Operator
make docker-build docker-push
make deploy
```

## API Server Extensions

API server extensions provide ways to extend the functionality of the Kubernetes API server.

### 1. Aggregation Layer

The aggregation layer is a mechanism that allows additional APIs to be registered with the Kubernetes API server.

**Key Features:**

1. **API Extension**: New APIs can be added to the existing API server.
2. **In-cluster Execution**: Extension API servers run within the cluster.
3. **Authentication Delegation**: The main API server handles authentication and delegates to the extension API server.

**APIService Example:**

```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
```

**Extension API Server Implementation:**

```go
package main

import (
    "fmt"
    "net/http"

    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/apimachinery/pkg/runtime/schema"
    "k8s.io/apimachinery/pkg/runtime/serializer"
    "k8s.io/apiserver/pkg/registry/rest"
    genericapiserver "k8s.io/apiserver/pkg/server"
    genericoptions "k8s.io/apiserver/pkg/server/options"
)

var (
    scheme = runtime.NewScheme()
    codecs = serializer.NewCodecFactory(scheme)
)

func main() {
    // Create server options
    serverOptions := genericoptions.NewRecommendedOptions("/tmp/apiserver.etcd", codecs.LegacyCodec())

    // Configure server
    config := genericapiserver.NewRecommendedConfig(codecs)
    if err := serverOptions.ApplyTo(config); err != nil {
        panic(err)
    }

    // Create API server
    server, err := config.Complete().New("example-apiserver", genericapiserver.NewEmptyDelegate())
    if err != nil {
        panic(err)
    }

    // Install API group
    apiGroupInfo := genericapiserver.NewDefaultAPIGroupInfo("example.com", scheme, metav1.ParameterCodec, codecs)
    server.InstallAPIGroup(&apiGroupInfo)

    // Run server
    server.PrepareRun().Run(make(chan struct{}))
}
```

### 2. Webhooks

Webhooks are a mechanism where the Kubernetes API server calls external services to perform additional processing when specific events occur.

#### Admission Webhooks

Admission webhooks can validate or modify API requests before they are persisted to storage.

**Main Types:**

1. **MutatingAdmissionWebhook**: Can modify requests.
2. **ValidatingAdmissionWebhook**: Only validates requests without modification.

**Webhook Configuration Example:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: example-webhook
webhooks:
- name: example.webhook.com
  clientConfig:
    url: https://example.webhook.com/mutate
    caBundle: <BASE64_ENCODED_CA_CERT>
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

**Webhook Server Implementation:**

```go
package main

import (
    "encoding/json"
    "fmt"
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

func handleMutate(w http.ResponseWriter, r *http.Request) {
    // Read request body
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, fmt.Sprintf("Failed to read body: %v", err), http.StatusBadRequest)
        return
    }

    // Convert to AdmissionReview object
    var admissionReview admissionv1.AdmissionReview
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, fmt.Sprintf("Failed to decode body: %v", err), http.StatusBadRequest)
        return
    }

    // Extract pod object
    var pod corev1.Pod
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, fmt.Sprintf("Failed to unmarshal pod: %v", err), http.StatusBadRequest)
        return
    }

    // Create patch
    patch := []map[string]interface{}{
        {
            "op":    "add",
            "path":  "/metadata/labels/example.com~1injected",
            "value": "true",
        },
    }

    patchBytes, err := json.Marshal(patch)
    if err != nil {
        http.Error(w, fmt.Sprintf("Failed to marshal patch: %v", err), http.StatusInternalServerError)
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

    admissionReview.Response = &admissionResponse

    // Send response
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, fmt.Sprintf("Failed to marshal response: %v", err), http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

func main() {
    http.HandleFunc("/mutate", handleMutate)
    http.ListenAndServeTLS(":8443", "tls.crt", "tls.key", nil)
}
```

## Scheduler Extensions

The Kubernetes scheduler determines which node to place pods on. Scheduler extensions allow you to customize this decision process.

### 1. Scheduler Framework

The scheduler framework provides an extension mechanism to add plugins at various stages of the scheduling pipeline.

**Key Extension Points:**

1. **Filter**: Filters out nodes where the pod cannot run.
2. **Score**: Assigns scores to suitable nodes.
3. **Bind**: Binds the pod to a node.
4. **Reserve/Unreserve**: Reserves or releases node resources.
5. **Permit**: Allows, denies, or delays pod scheduling.

**Scheduler Configuration Example:**

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    filter:
      enabled:
      - name: NodeResourcesFit
      - name: NodeName
      - name: CustomFilter
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 1
      - name: CustomScore
        weight: 5
  pluginConfig:
  - name: CustomFilter
    args:
      foo: bar
```

**Scheduler Plugin Implementation:**

```go
package main

import (
    "context"

    v1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/kubernetes/pkg/scheduler/framework"
)

// CustomPlugin is a scheduler framework plugin.
type CustomPlugin struct {
    handle framework.Handle
}

var _ framework.FilterPlugin = &CustomPlugin{}
var _ framework.ScorePlugin = &CustomPlugin{}

// Name returns the name of the plugin.
func (p *CustomPlugin) Name() string {
    return "CustomPlugin"
}

// Filter filters nodes where the pod can run.
func (p *CustomPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, node *framework.NodeInfo) *framework.Status {
    // Implement filtering logic
    return framework.NewStatus(framework.Success, "")
}

// Score assigns scores to nodes.
func (p *CustomPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // Implement score calculation logic
    return 100, framework.NewStatus(framework.Success, "")
}

// ScoreExtensions provides score normalization methods.
func (p *CustomPlugin) ScoreExtensions() framework.ScoreExtensions {
    return p
}

// NormalizeScore normalizes scores.
func (p *CustomPlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    // Implement score normalization logic
    return framework.NewStatus(framework.Success, "")
}

// New creates a new instance of the plugin.
func New(configuration runtime.Object, f framework.Handle) (framework.Plugin, error) {
    return &CustomPlugin{handle: f}, nil
}
```

### 2. Scheduler Extender

A scheduler extender is an external process that can influence scheduling decisions through HTTP webhooks.

**Scheduler Configuration Example:**

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
extenders:
- urlPrefix: "http://extender.example.com"
  filterVerb: "filter"
  prioritizeVerb: "prioritize"
  weight: 5
  bindVerb: "bind"
  enableHTTPS: false
```

**Extender Server Implementation:**

```go
package main

import (
    "encoding/json"
    "net/http"

    v1 "k8s.io/api/core/v1"
    extender "k8s.io/kube-scheduler/extender/v1"
)

func filter(w http.ResponseWriter, r *http.Request) {
    var extenderArgs extender.ExtenderArgs
    var extenderFilterResult extender.ExtenderFilterResult

    // Parse request
    if err := json.NewDecoder(r.Body).Decode(&extenderArgs); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement filtering logic
    filteredNodes := make([]v1.Node, 0, len(extenderArgs.Nodes.Items))
    failedNodes := make(map[string]string)

    for _, node := range extenderArgs.Nodes.Items {
        // Node filtering logic
        if /* check if node is suitable */ true {
            filteredNodes = append(filteredNodes, node)
        } else {
            failedNodes[node.Name] = "Node is not suitable"
        }
    }

    // Create result
    extenderFilterResult = extender.ExtenderFilterResult{
        Nodes: &v1.NodeList{
            Items: filteredNodes,
        },
        FailedNodes: failedNodes,
        Error:       "",
    }

    // Send response
    if err := json.NewEncoder(w).Encode(extenderFilterResult); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

func prioritize(w http.ResponseWriter, r *http.Request) {
    var extenderArgs extender.ExtenderArgs
    var hostPriorityList extender.HostPriorityList

    // Parse request
    if err := json.NewDecoder(r.Body).Decode(&extenderArgs); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Implement priority logic
    hostPriorityList = make(extender.HostPriorityList, 0, len(extenderArgs.Nodes.Items))

    for _, node := range extenderArgs.Nodes.Items {
        // Node score calculation logic
        score := int64(0)
        hostPriorityList = append(hostPriorityList, extender.HostPriority{
            Host:  node.Name,
            Score: score,
        })
    }

    // Send response
    if err := json.NewEncoder(w).Encode(hostPriorityList); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

func main() {
    http.HandleFunc("/filter", filter)
    http.HandleFunc("/prioritize", prioritize)
    http.ListenAndServe(":8888", nil)
}
```

## Network Plugins

Kubernetes supports network plugins through the Container Network Interface (CNI).

### CNI (Container Network Interface)

CNI defines a standard interface between container runtimes and network plugins.

**Major CNI Plugins:**

1. **Calico**: Provides BGP-based networking and network policies.
2. **Cilium**: Provides eBPF-based networking, security, and observability.
3. **Flannel**: Provides simple overlay networking.
4. **Weave Net**: Provides multi-host container networking.

**CNI Configuration Example:**

```json
{
  "cniVersion": "0.4.0",
  "name": "mynet",
  "type": "bridge",
  "bridge": "cni0",
  "isGateway": true,
  "ipMasq": true,
  "ipam": {
    "type": "host-local",
    "subnet": "10.244.0.0/16",
    "routes": [
      { "dst": "0.0.0.0/0" }
    ]
  }
}
```

**CNI Plugin Implementation:**

```go
package main

import (
    "encoding/json"
    "net"

    "github.com/containernetworking/cni/pkg/skel"
    "github.com/containernetworking/cni/pkg/types"
    current "github.com/containernetworking/cni/pkg/types/100"
    "github.com/containernetworking/cni/pkg/version"
)

func cmdAdd(args *skel.CmdArgs) error {
    // Parse configuration
    conf := &types.NetConf{}
    if err := json.Unmarshal(args.StdinData, conf); err != nil {
        return err
    }

    // Implement network setup logic
    // ...

    // Return result
    result := &current.Result{
        CNIVersion: conf.CNIVersion,
        IPs: []*current.IPConfig{
            {
                Address: net.IPNet{
                    IP:   net.ParseIP("10.244.0.2"),
                    Mask: net.CIDRMask(24, 32),
                },
                Gateway: net.ParseIP("10.244.0.1"),
            },
        },
    }

    return types.PrintResult(result, conf.CNIVersion)
}

func cmdDel(args *skel.CmdArgs) error {
    // Implement network teardown logic
    // ...

    return nil
}

func cmdCheck(args *skel.CmdArgs) error {
    // Implement network status check logic
    // ...

    return nil
}

func main() {
    skel.PluginMain(cmdAdd, cmdCheck, cmdDel, version.All, "My CNI Plugin v0.1.0")
}
```

## Storage Plugins

Kubernetes supports storage plugins through the Container Storage Interface (CSI).

### CSI (Container Storage Interface)

CSI defines a standard interface between container orchestration systems and storage providers.

**Major CSI Plugins:**

1. **AWS EBS CSI Driver**: Provides Amazon EBS volumes.
2. **GCE PD CSI Driver**: Provides Google Compute Engine persistent disks.
3. **Azure Disk CSI Driver**: Provides Azure disks.
4. **Ceph CSI**: Provides Ceph RBD and CephFS.

**CSI Driver Deployment Example:**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-sc
provisioner: example.csi.driver
parameters:
  type: ssd
  fsType: ext4
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: csi-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: csi-sc
```

**CSI Driver Implementation:**

CSI drivers must implement three main services:

1. **Identity Service**: Driver identification and capability discovery
2. **Controller Service**: Volume provisioning and management
3. **Node Service**: Volume mounting and unmounting on nodes

```go
package main

import (
    "context"
    "net"
    "os"
    "os/signal"
    "syscall"

    "github.com/container-storage-interface/spec/lib/go/csi"
    "google.golang.org/grpc"
)

type driver struct {
    csi.UnimplementedIdentityServer
    csi.UnimplementedControllerServer
    csi.UnimplementedNodeServer
}

// Identity Service
func (d *driver) GetPluginInfo(ctx context.Context, req *csi.GetPluginInfoRequest) (*csi.GetPluginInfoResponse, error) {
    return &csi.GetPluginInfoResponse{
        Name:          "example.csi.driver",
        VendorVersion: "v0.1.0",
    }, nil
}

// Controller Service
func (d *driver) CreateVolume(ctx context.Context, req *csi.CreateVolumeRequest) (*csi.CreateVolumeResponse, error) {
    // Implement volume creation logic
    // ...

    return &csi.CreateVolumeResponse{
        Volume: &csi.Volume{
            VolumeId:      "vol-123",
            CapacityBytes: req.GetCapacityRange().GetRequiredBytes(),
            VolumeContext: req.GetParameters(),
        },
    }, nil
}

// Node Service
func (d *driver) NodePublishVolume(ctx context.Context, req *csi.NodePublishVolumeRequest) (*csi.NodePublishVolumeResponse, error) {
    // Implement volume mount logic
    // ...

    return &csi.NodePublishVolumeResponse{}, nil
}

func main() {
    // Set up gRPC server
    server := grpc.NewServer()

    // Create CSI driver instance
    d := &driver{}

    // Register CSI services
    csi.RegisterIdentityServer(server, d)
    csi.RegisterControllerServer(server, d)
    csi.RegisterNodeServer(server, d)

    // Create socket listener
    listener, err := net.Listen("unix", "/csi/csi.sock")
    if err != nil {
        panic(err)
    }

    // Start server
    go server.Serve(listener)

    // Handle termination signals
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
    <-sigCh

    server.GracefulStop()
}
```

## Conclusion

Kubernetes extension mechanisms provide powerful ways to customize Kubernetes for various use cases and requirements. You can define new APIs with CRDs and custom controllers, validate or modify API requests with admission webhooks, customize pod placement decisions with scheduler extensions, and integrate networking and storage solutions with CNI and CSI.

By leveraging these extension mechanisms, you can tailor Kubernetes to your organization's specific requirements, automate complex application management, and maximize the benefits of the cloud-native ecosystem.
