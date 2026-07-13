# Kubernetes Extension Mechanisms

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33
> **Última actualización**: February 21, 2026

## Overview

Kubernetes proporciona varios mecanismos de extensión para ampliar y personalizar su funcionalidad base. Este documento explora los principales mecanismos de extensión de Kubernetes y explica casos de uso del mundo real y métodos de implementación.

## Custom Resource Definitions (CRD)

Custom Resource Definitions (CRDs) son un mecanismo que permite extender la Kubernetes API para definir custom resources.

### CRD Basic Concepts

Usar CRDs proporciona los siguientes beneficios:

1. **API declarativa**: Puedes aprovechar el modelo de API declarativa de Kubernetes.
2. **Integración con kubectl**: Los custom resources pueden gestionarse de la misma manera que los recursos nativos de Kubernetes.
3. **Gestión de versiones**: Los schemas de recursos pueden evolucionar mediante la gestión de versiones de API.
4. **Validación**: La validación de recursos puede realizarse mediante schemas OpenAPI v3.

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

Los custom resources por sí solos no pueden implementar comportamiento real. Los custom controllers observan el estado de los custom resources y realizan acciones para alcanzar el estado deseado.

### Controller Pattern

Los Kubernetes controllers siguen este patrón:

1. **Observar**: Observan el estado actual de los recursos.
2. **Analizar**: Analizan la diferencia entre el estado actual y el estado deseado.
3. **Actuar**: Realizan acciones para alcanzar el estado deseado.

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

Un Operator es un patrón que combina CRDs y controllers para automatizar conocimiento operativo específico de una aplicación.

**Características clave de los Operators:**

1. **Automatización del conocimiento del dominio**: Implementa como código el conocimiento del dominio de la aplicación.
2. **Gestión declarativa**: Los usuarios declaran el estado deseado y el Operator realiza acciones para alcanzarlo.
3. **Self-healing**: Detecta condiciones de falla y se recupera automáticamente.
4. **Gestión de upgrades**: Maneja de forma segura los upgrades de aplicaciones.

**Ejemplos de Operators:**

- **Prometheus Operator**: Gestiona el stack de monitoreo Prometheus.
- **Elasticsearch Operator**: Gestiona clusters Elasticsearch.
- **PostgreSQL Operator**: Gestiona bases de datos PostgreSQL.

### Operator SDK

Operator SDK es una herramienta que simplifica el desarrollo de Operators.

**Creación de Operator:**

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

Las extensiones de API server proporcionan formas de ampliar la funcionalidad del Kubernetes API server.

### 1. Aggregation Layer

La aggregation layer es un mecanismo que permite registrar APIs adicionales en el Kubernetes API server.

**Características clave:**

1. **Extensión de API**: Pueden añadirse nuevas APIs al API server existente.
2. **Ejecución dentro del cluster**: Los extension API servers se ejecutan dentro del cluster.
3. **Delegación de autenticación**: El API server principal gestiona la autenticación y delega al extension API server.

**Ejemplo de APIService:**

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

**Implementación de Extension API Server:**

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

Los webhooks son un mecanismo en el que el Kubernetes API server llama a servicios externos para realizar procesamiento adicional cuando ocurren eventos específicos.

#### Admission Webhooks

Los admission webhooks pueden validar o modificar solicitudes de API antes de que se persistan en storage.

**Tipos principales:**

1. **MutatingAdmissionWebhook**: Puede modificar solicitudes.
2. **ValidatingAdmissionWebhook**: Solo valida solicitudes sin modificación.

**Ejemplo de configuración de Webhook:**

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

**Implementación de Webhook Server:**

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

El Kubernetes scheduler determina en qué node colocar los pods. Las extensiones del scheduler permiten personalizar este proceso de decisión.

### 1. Scheduler Framework

El scheduler framework proporciona un mecanismo de extensión para añadir plugins en varias etapas del scheduling pipeline.

**Puntos de extensión clave:**

1. **Filter**: Filtra los nodes donde el pod no puede ejecutarse.
2. **Score**: Asigna puntuaciones a los nodes adecuados.
3. **Bind**: Vincula el pod a un node.
4. **Reserve/Unreserve**: Reserva o libera recursos de node.
5. **Permit**: Permite, deniega o retrasa el scheduling del pod.

**Ejemplo de configuración de Scheduler:**

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

**Implementación de Scheduler Plugin:**

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

Un scheduler extender es un proceso externo que puede influir en las decisiones de scheduling mediante HTTP webhooks.

**Ejemplo de configuración de Scheduler:**

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

**Implementación de Extender Server:**

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

Kubernetes admite network plugins mediante Container Network Interface (CNI).

### CNI (Container Network Interface)

CNI define una interfaz estándar entre los container runtimes y los network plugins.

**Principales CNI plugins:**

1. **Calico**: Proporciona networking basado en BGP y network policies.
2. **Cilium**: Proporciona networking, seguridad y observabilidad basados en eBPF.
3. **Flannel**: Proporciona networking overlay sencillo.
4. **Weave Net**: Proporciona networking de containers multi-host.

**Ejemplo de configuración de CNI:**

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

**Implementación de CNI Plugin:**

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

Kubernetes admite storage plugins mediante Container Storage Interface (CSI).

### CSI (Container Storage Interface)

CSI define una interfaz estándar entre los sistemas de orquestación de containers y los storage providers.

**Principales CSI plugins:**

1. **AWS EBS CSI Driver**: Proporciona volúmenes Amazon EBS.
2. **GCE PD CSI Driver**: Proporciona persistent disks de Google Compute Engine.
3. **Azure Disk CSI Driver**: Proporciona discos Azure.
4. **Ceph CSI**: Proporciona Ceph RBD y CephFS.

**Ejemplo de despliegue de CSI Driver:**

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

**Implementación de CSI Driver:**

Los CSI drivers deben implementar tres servicios principales:

1. **Identity Service**: Identificación del driver y descubrimiento de capacidades
2. **Controller Service**: Aprovisionamiento y gestión de volúmenes
3. **Node Service**: Montaje y desmontaje de volúmenes en nodes

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

Los mecanismos de extensión de Kubernetes proporcionan formas potentes de personalizar Kubernetes para diversos casos de uso y requisitos. Puedes definir nuevas APIs con CRDs y custom controllers, validar o modificar solicitudes de API con admission webhooks, personalizar las decisiones de colocación de pods con extensiones del scheduler e integrar soluciones de networking y storage con CNI y CSI.

Al aprovechar estos mecanismos de extensión, puedes adaptar Kubernetes a los requisitos específicos de tu organización, automatizar la gestión de aplicaciones complejas y maximizar los beneficios del ecosistema cloud-native.
