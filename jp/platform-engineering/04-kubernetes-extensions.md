# Kubernetes 拡張メカニズム

> **サポート対象バージョン**: Kubernetes 1.31, 1.32, 1.33
> **最終更新**: February 21, 2026

## 概要

Kubernetes は、その基本機能を拡張しカスタマイズするためのさまざまな拡張メカニズムを提供します。このドキュメントでは、Kubernetes の主要な拡張メカニズムを取り上げ、実際のユースケースと実装方法を説明します。

## Custom Resource Definitions (CRD)

Custom Resource Definitions (CRD) は、Kubernetes API を拡張してカスタムリソースを定義できるようにするメカニズムです。

### CRD の基本概念

CRD を使用すると、次の利点があります。

1. **宣言型 API**: Kubernetes の宣言型 API モデルを活用できます。
2. **kubectl との統合**: カスタムリソースを、Kubernetes のネイティブリソースと同じ方法で管理できます。
3. **バージョン管理**: API バージョン管理を通じてリソーススキーマを進化させることができます。
4. **バリデーション**: OpenAPI v3 スキーマを通じてリソースのバリデーションを実行できます。

### CRD 作成例

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

### カスタムリソースインスタンスの作成

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

カスタムリソースだけでは実際の動作を実装できません。Custom controllers はカスタムリソースの状態を監視し、望ましい状態を実現するためのアクションを実行します。

### Controller パターン

Kubernetes controllers は次のパターンに従います。

1. **Observe**: リソースの現在の状態を監視します。
2. **Analyze**: 現在の状態と望ましい状態の差分を分析します。
3. **Act**: 望ましい状態を実現するためのアクションを実行します。

### Controller の実装方法

#### 1. client-go の使用

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

#### 2. controller-runtime の使用

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

### Operator パターン

Operator は、CRD と controllers を組み合わせて、アプリケーション固有の運用知識を自動化するパターンです。

**Operator の主な特徴:**

1. **ドメイン知識の自動化**: アプリケーションのドメイン知識をコードとして実装します。
2. **宣言型管理**: ユーザーが望ましい状態を宣言し、Operator がそれを実現するためのアクションを実行します。
3. **自己修復**: 障害状態を検出し、自動的に復旧します。
4. **アップグレード管理**: アプリケーションのアップグレードを安全に処理します。

**Operator の例:**

- **Prometheus Operator**: Prometheus 監視スタックを管理します。
- **Elasticsearch Operator**: Elasticsearch クラスターを管理します。
- **PostgreSQL Operator**: PostgreSQL データベースを管理します。

### Operator SDK

Operator SDK は、Operator 開発を簡素化するツールです。

**Operator の作成:**

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

API server extensions は、Kubernetes API server の機能を拡張する方法を提供します。

### 1. Aggregation Layer

Aggregation layer は、追加の API を Kubernetes API server に登録できるようにするメカニズムです。

**主な機能:**

1. **API 拡張**: 既存の API server に新しい API を追加できます。
2. **クラスター内実行**: Extension API servers はクラスター内で実行されます。
3. **認証の委任**: メインの API server が認証を処理し、extension API server に委任します。

**APIService の例:**

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

**Extension API Server の実装:**

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

Webhooks は、特定のイベントが発生したときに Kubernetes API server が外部サービスを呼び出して追加処理を実行するメカニズムです。

#### Admission Webhooks

Admission webhooks は、API リクエストがストレージに永続化される前に、それらを検証または変更できます。

**主な種類:**

1. **MutatingAdmissionWebhook**: リクエストを変更できます。
2. **ValidatingAdmissionWebhook**: 変更せずにリクエストを検証するだけです。

**Webhook 設定例:**

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

**Webhook Server の実装:**

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

Kubernetes scheduler は、Pod をどの node に配置するかを決定します。Scheduler extensions を使用すると、この意思決定プロセスをカスタマイズできます。

### 1. Scheduler Framework

Scheduler framework は、スケジューリングパイプラインのさまざまな段階で plugin を追加するための拡張メカニズムを提供します。

**主な拡張ポイント:**

1. **Filter**: Pod を実行できない node を除外します。
2. **Score**: 適切な node にスコアを割り当てます。
3. **Bind**: Pod を node にバインドします。
4. **Reserve/Unreserve**: node リソースを予約または解放します。
5. **Permit**: Pod のスケジューリングを許可、拒否、または遅延します。

**Scheduler 設定例:**

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

**Scheduler Plugin の実装:**

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

Scheduler extender は、HTTP webhooks を通じてスケジューリングの判断に影響を与えることができる外部プロセスです。

**Scheduler 設定例:**

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

**Extender Server の実装:**

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

Kubernetes は Container Network Interface (CNI) を通じて network plugins をサポートします。

### CNI (Container Network Interface)

CNI は、container runtimes と network plugins の間の標準インターフェースを定義します。

**主要な CNI Plugins:**

1. **Calico**: BGP ベースのネットワークと network policies を提供します。
2. **Cilium**: eBPF ベースのネットワーク、セキュリティ、可観測性を提供します。
3. **Flannel**: シンプルな overlay networking を提供します。
4. **Weave Net**: マルチホストの container networking を提供します。

**CNI 設定例:**

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

**CNI Plugin の実装:**

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

Kubernetes は Container Storage Interface (CSI) を通じて storage plugins をサポートします。

### CSI (Container Storage Interface)

CSI は、container orchestration systems と storage providers の間の標準インターフェースを定義します。

**主要な CSI Plugins:**

1. **AWS EBS CSI Driver**: Amazon EBS volumes を提供します。
2. **GCE PD CSI Driver**: Google Compute Engine persistent disks を提供します。
3. **Azure Disk CSI Driver**: Azure disks を提供します。
4. **Ceph CSI**: Ceph RBD と CephFS を提供します。

**CSI Driver デプロイ例:**

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

**CSI Driver の実装:**

CSI drivers は 3 つの主要なサービスを実装する必要があります。

1. **Identity Service**: Driver の識別と機能検出
2. **Controller Service**: Volume のプロビジョニングと管理
3. **Node Service**: node 上での volume のマウントとアンマウント

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

## まとめ

Kubernetes 拡張メカニズムは、さまざまなユースケースや要件に合わせて Kubernetes をカスタマイズするための強力な方法を提供します。CRD と custom controllers で新しい API を定義し、admission webhooks で API リクエストを検証または変更し、scheduler extensions で Pod 配置の判断をカスタマイズし、CNI と CSI でネットワークおよびストレージソリューションを統合できます。

これらの拡張メカニズムを活用することで、Kubernetes を組織固有の要件に合わせて調整し、複雑なアプリケーション管理を自動化し、cloud-native エコシステムの利点を最大限に引き出すことができます。
