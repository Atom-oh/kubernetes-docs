# Kubernetes 확장 메커니즘

> **지원 버전**: Kubernetes 1.31, 1.32, 1.33  
> **마지막 업데이트**: 2025년 11월 24일

## 개요

Kubernetes는 다양한 확장 메커니즘을 제공하여 기본 기능을 확장하고 사용자 정의할 수 있습니다. 이 문서에서는 Kubernetes의 주요 확장 메커니즘을 살펴보고, 실제 사용 사례와 구현 방법을 설명합니다.

## 커스텀 리소스 정의(CRD)

커스텀 리소스 정의(Custom Resource Definition, CRD)는 Kubernetes API를 확장하여 사용자 정의 리소스를 정의할 수 있게 해주는 메커니즘입니다.

### CRD 기본 개념

CRD를 사용하면 다음과 같은 이점을 얻을 수 있습니다:

1. **선언적 API**: Kubernetes의 선언적 API 모델을 활용할 수 있습니다.
2. **kubectl 통합**: 기본 Kubernetes 리소스와 동일한 방식으로 커스텀 리소스를 관리할 수 있습니다.
3. **버전 관리**: API 버전 관리를 통해 리소스 스키마를 진화시킬 수 있습니다.
4. **검증**: OpenAPI v3 스키마를 통해 리소스 유효성 검사를 수행할 수 있습니다.

### CRD 생성 예시

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

### 커스텀 리소스 인스턴스 생성

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

## 커스텀 컨트롤러

커스텀 리소스만으로는 실제 동작을 구현할 수 없습니다. 커스텀 컨트롤러는 커스텀 리소스의 상태를 감시하고 원하는 상태를 달성하기 위한 작업을 수행합니다.

### 컨트롤러 패턴

Kubernetes 컨트롤러는 다음과 같은 패턴을 따릅니다:

1. **관찰(Observe)**: 리소스의 현재 상태를 관찰합니다.
2. **분석(Analyze)**: 현재 상태와 원하는 상태의 차이를 분석합니다.
3. **조치(Act)**: 원하는 상태를 달성하기 위한 조치를 취합니다.

### 컨트롤러 구현 방법

#### 1. client-go 사용

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
    // kubeconfig 로드
    kubeconfig := filepath.Join(homedir.HomeDir(), ".kube", "config")
    config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
    if err != nil {
        panic(err)
    }
    
    // Kubernetes 클라이언트 생성
    clientset, err := kubernetes.NewForConfig(config)
    if err != nil {
        panic(err)
    }
    
    // 파드 목록 가져오기
    pods, err := clientset.CoreV1().Pods("default").List(context.TODO(), metav1.ListOptions{})
    if err != nil {
        panic(err)
    }
    
    fmt.Printf("There are %d pods in the default namespace\n", len(pods.Items))
    
    // 파드 감시
    watch, err := clientset.CoreV1().Pods("default").Watch(context.TODO(), metav1.ListOptions{})
    if err != nil {
        panic(err)
    }
    
    // 이벤트 처리
    for event := range watch.ResultChan() {
        fmt.Printf("Event: %s\n", event.Type)
    }
}
```

#### 2. controller-runtime 사용

```go
package main

import (
    "context"
    
    appsv1 "k8s.io/api/apps/v1"
    corev1 "k8s.io/api/core/v1"
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
    
    // WebApp 인스턴스 가져오기
    var webapp examplev1.WebApp
    if err := r.Get(ctx, req.NamespacedName, &webapp); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }
    
    // Deployment 생성 또는 업데이트
    deployment := &appsv1.Deployment{}
    err := r.Get(ctx, client.ObjectKey{Namespace: webapp.Namespace, Name: webapp.Name}, deployment)
    if client.IgnoreNotFound(err) != nil {
        return ctrl.Result{}, err
    }
    
    if err != nil {
        // Deployment가 존재하지 않으면 생성
        deployment = &appsv1.Deployment{
            ObjectMeta: metav1.ObjectMeta{
                Name:      webapp.Name,
                Namespace: webapp.Namespace,
            },
        }
        
        if err := ctrl.SetControllerReference(&webapp, deployment, r.Scheme); err != nil {
            return ctrl.Result{}, err
        }
        
        // Deployment 스펙 설정
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
                        ContainerPort: webapp.Spec.Port,
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
        // Deployment가 존재하면 업데이트
        replicas := int32(webapp.Spec.Replicas)
        deployment.Spec.Replicas = &replicas
        deployment.Spec.Template.Spec.Containers[0].Image = webapp.Spec.Image
        
        if err := r.Update(ctx, deployment); err != nil {
            log.Error(err, "Failed to update Deployment")
            return ctrl.Result{}, err
        }
        
        log.Info("Updated Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
    }
    
    // 상태 업데이트
    webapp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
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

### Operator 패턴

Operator는 CRD와 컨트롤러를 결합하여 애플리케이션별 운영 지식을 자동화하는 패턴입니다.

**Operator의 주요 특징:**

1. **도메인 지식 자동화**: 애플리케이션 도메인 지식을 코드로 구현합니다.
2. **선언적 관리**: 사용자는 원하는 상태를 선언하고, Operator는 이를 달성하기 위한 작업을 수행합니다.
3. **자가 복구**: 장애 상황을 감지하고 자동으로 복구합니다.
4. **업그레이드 관리**: 애플리케이션 업그레이드를 안전하게 처리합니다.

**Operator 예시:**

- **Prometheus Operator**: Prometheus 모니터링 스택을 관리합니다.
- **Elasticsearch Operator**: Elasticsearch 클러스터를 관리합니다.
- **PostgreSQL Operator**: PostgreSQL 데이터베이스를 관리합니다.

### Operator SDK

Operator SDK는 Operator 개발을 간소화하는 도구입니다.

**Operator 생성:**

```bash
# Operator SDK 설치
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.25.0/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
sudo mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# Operator 프로젝트 생성
operator-sdk init --domain example.com --repo github.com/example/webapp-operator

# API 생성
operator-sdk create api --group apps --version v1 --kind WebApp --resource --controller

# CRD 생성
make manifests

# Operator 빌드 및 배포
make docker-build docker-push
make deploy
```
## API 서버 확장

API 서버 확장은 Kubernetes API 서버의 기능을 확장하는 방법을 제공합니다.

### 1. 어그리게이션 레이어(Aggregation Layer)

어그리게이션 레이어는 Kubernetes API 서버에 추가 API를 등록할 수 있게 해주는 메커니즘입니다.

**주요 특징:**

1. **API 확장**: 기존 API 서버에 새로운 API를 추가할 수 있습니다.
2. **클러스터 내 실행**: 확장 API 서버는 클러스터 내에서 실행됩니다.
3. **인증 위임**: 기본 API 서버가 인증을 처리하고 확장 API 서버로 위임합니다.

**APIService 예시:**

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

**확장 API 서버 구현:**

```go
package main

import (
    "fmt"
    "net/http"
    
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
    // 서버 옵션 생성
    serverOptions := genericoptions.NewRecommendedOptions("/tmp/apiserver.etcd", codecs.LegacyCodec())
    
    // 서버 구성
    config := genericapiserver.NewRecommendedConfig(codecs)
    if err := serverOptions.ApplyTo(config); err != nil {
        panic(err)
    }
    
    // API 서버 생성
    server, err := config.Complete().New("example-apiserver", genericapiserver.NewEmptyDelegate())
    if err != nil {
        panic(err)
    }
    
    // API 그룹 설치
    apiGroupInfo := genericapiserver.NewDefaultAPIGroupInfo("example.com", scheme, metav1.ParameterCodec, codecs)
    server.InstallAPIGroup(&apiGroupInfo)
    
    // 서버 실행
    server.RunServer()
}
```

### 2. 웹훅(Webhook)

웹훅은 Kubernetes API 서버가 특정 이벤트 발생 시 외부 서비스를 호출하여 추가 처리를 수행하는 메커니즘입니다.

#### 어드미션 웹훅(Admission Webhook)

어드미션 웹훅은 API 요청이 영구 저장소에 저장되기 전에 요청을 검증하거나 수정할 수 있습니다.

**주요 유형:**

1. **변경 어드미션 웹훅(MutatingAdmissionWebhook)**: 요청을 수정할 수 있습니다.
2. **검증 어드미션 웹훅(ValidatingAdmissionWebhook)**: 요청을 검증만 하고 수정하지 않습니다.

**웹훅 구성 예시:**

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

**웹훅 서버 구현:**

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
    // 요청 본문 읽기
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, fmt.Sprintf("Failed to read body: %v", err), http.StatusBadRequest)
        return
    }
    
    // AdmissionReview 객체로 변환
    var admissionReview admissionv1.AdmissionReview
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, fmt.Sprintf("Failed to decode body: %v", err), http.StatusBadRequest)
        return
    }
    
    // 파드 객체 추출
    var pod corev1.Pod
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, fmt.Sprintf("Failed to unmarshal pod: %v", err), http.StatusBadRequest)
        return
    }
    
    // 패치 생성
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
    
    // 응답 생성
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
    
    // 응답 전송
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

## 스케줄러 확장

Kubernetes 스케줄러는 파드를 어떤 노드에 배치할지 결정하는 역할을 합니다. 스케줄러 확장을 통해 이 결정 과정을 사용자 정의할 수 있습니다.

### 1. 스케줄러 프레임워크

스케줄러 프레임워크는 스케줄링 파이프라인의 다양한 단계에 플러그인을 추가할 수 있는 확장 메커니즘을 제공합니다.

**주요 확장 포인트:**

1. **Filter**: 파드를 실행할 수 없는 노드를 필터링합니다.
2. **Score**: 적합한 노드에 점수를 매깁니다.
3. **Bind**: 파드를 노드에 바인딩합니다.
4. **Reserve/Unreserve**: 노드의 리소스를 예약하거나 해제합니다.
5. **Permit**: 파드 스케줄링을 허용, 거부 또는 지연시킵니다.

**스케줄러 구성 예시:**

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

**스케줄러 플러그인 구현:**

```go
package main

import (
    "context"
    
    v1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/kubernetes/pkg/scheduler/framework"
)

// CustomPlugin은 스케줄러 프레임워크 플러그인입니다.
type CustomPlugin struct {
    handle framework.Handle
}

var _ framework.FilterPlugin = &CustomPlugin{}
var _ framework.ScorePlugin = &CustomPlugin{}

// Name은 플러그인의 이름을 반환합니다.
func (p *CustomPlugin) Name() string {
    return "CustomPlugin"
}

// Filter는 파드를 실행할 수 있는 노드를 필터링합니다.
func (p *CustomPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, node *framework.NodeInfo) *framework.Status {
    // 필터링 로직 구현
    return framework.NewStatus(framework.Success, "")
}

// Score는 노드에 점수를 매깁니다.
func (p *CustomPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // 점수 계산 로직 구현
    return 100, framework.NewStatus(framework.Success, "")
}

// ScoreExtensions는 점수 정규화 메서드를 제공합니다.
func (p *CustomPlugin) ScoreExtensions() framework.ScoreExtensions {
    return p
}

// NormalizeScore는 점수를 정규화합니다.
func (p *CustomPlugin) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
    // 점수 정규화 로직 구현
    return framework.NewStatus(framework.Success, "")
}

// New는 플러그인의 새 인스턴스를 생성합니다.
func New(configuration runtime.Object, f framework.Handle) (framework.Plugin, error) {
    return &CustomPlugin{handle: f}, nil
}
```

### 2. 스케줄러 익스텐더(Scheduler Extender)

스케줄러 익스텐더는 HTTP 웹훅을 통해 스케줄링 결정에 영향을 미칠 수 있는 외부 프로세스입니다.

**스케줄러 구성 예시:**

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

**익스텐더 서버 구현:**

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
    
    // 요청 파싱
    if err := json.NewDecoder(r.Body).Decode(&extenderArgs); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // 필터링 로직 구현
    filteredNodes := make([]v1.Node, 0, len(extenderArgs.Nodes.Items))
    failedNodes := make(map[string]string)
    
    for _, node := range extenderArgs.Nodes.Items {
        // 노드 필터링 로직
        if /* 노드가 적합한지 확인 */ true {
            filteredNodes = append(filteredNodes, node)
        } else {
            failedNodes[node.Name] = "노드가 적합하지 않음"
        }
    }
    
    // 결과 생성
    extenderFilterResult = extender.ExtenderFilterResult{
        Nodes: &v1.NodeList{
            Items: filteredNodes,
        },
        FailedNodes: failedNodes,
        Error:       "",
    }
    
    // 응답 전송
    if err := json.NewEncoder(w).Encode(extenderFilterResult); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
}

func prioritize(w http.ResponseWriter, r *http.Request) {
    var extenderArgs extender.ExtenderArgs
    var hostPriorityList extender.HostPriorityList
    
    // 요청 파싱
    if err := json.NewDecoder(r.Body).Decode(&extenderArgs); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // 우선순위 로직 구현
    hostPriorityList = make(extender.HostPriorityList, 0, len(extenderArgs.Nodes.Items))
    
    for _, node := range extenderArgs.Nodes.Items {
        // 노드 점수 계산 로직
        score := 0
        hostPriorityList = append(hostPriorityList, extender.HostPriority{
            Host:  node.Name,
            Score: score,
        })
    }
    
    // 응답 전송
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

## 네트워크 플러그인

Kubernetes는 컨테이너 네트워크 인터페이스(CNI)를 통해 네트워크 플러그인을 지원합니다.

### CNI(Container Network Interface)

CNI는 컨테이너 런타임과 네트워크 플러그인 간의 표준 인터페이스를 정의합니다.

**주요 CNI 플러그인:**

1. **Calico**: BGP 기반의 네트워킹 및 네트워크 정책을 제공합니다.
2. **Cilium**: eBPF 기반의 네트워킹, 보안 및 관찰성을 제공합니다.
3. **Flannel**: 간단한 오버레이 네트워크를 제공합니다.
4. **Weave Net**: 멀티 호스트 컨테이너 네트워킹을 제공합니다.

**CNI 구성 예시:**

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

**CNI 플러그인 구현:**

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
    
    "github.com/containernetworking/cni/pkg/skel"
    "github.com/containernetworking/cni/pkg/types"
    current "github.com/containernetworking/cni/pkg/types/100"
    "github.com/containernetworking/cni/pkg/version"
)

func cmdAdd(args *skel.CmdArgs) error {
    // 구성 파싱
    conf := &types.NetConf{}
    if err := json.Unmarshal(args.StdinData, conf); err != nil {
        return err
    }
    
    // 네트워크 설정 로직 구현
    // ...
    
    // 결과 반환
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
    // 네트워크 해제 로직 구현
    // ...
    
    return nil
}

func cmdCheck(args *skel.CmdArgs) error {
    // 네트워크 상태 확인 로직 구현
    // ...
    
    return nil
}

func main() {
    skel.PluginMain(cmdAdd, cmdCheck, cmdDel, version.All, "My CNI Plugin v0.1.0")
}
```

## 스토리지 플러그인

Kubernetes는 컨테이너 스토리지 인터페이스(CSI)를 통해 스토리지 플러그인을 지원합니다.

### CSI(Container Storage Interface)

CSI는 컨테이너 오케스트레이션 시스템과 스토리지 제공자 간의 표준 인터페이스를 정의합니다.

**주요 CSI 플러그인:**

1. **AWS EBS CSI Driver**: Amazon EBS 볼륨을 제공합니다.
2. **GCE PD CSI Driver**: Google Compute Engine 영구 디스크를 제공합니다.
3. **Azure Disk CSI Driver**: Azure 디스크를 제공합니다.
4. **Ceph CSI**: Ceph RBD 및 CephFS를 제공합니다.

**CSI 드라이버 배포 예시:**

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

**CSI 드라이버 구현:**

CSI 드라이버는 다음과 같은 세 가지 주요 서비스를 구현해야 합니다:

1. **Identity Service**: 드라이버 식별 및 기능 검색
2. **Controller Service**: 볼륨 프로비저닝 및 관리
3. **Node Service**: 노드에 볼륨 마운트 및 마운트 해제

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
    // ...
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
    // 볼륨 생성 로직 구현
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
    // 볼륨 마운트 로직 구현
    // ...
    
    return &csi.NodePublishVolumeResponse{}, nil
}

func main() {
    // gRPC 서버 설정
    server := grpc.NewServer()
    
    // CSI 드라이버 인스턴스 생성
    d := &driver{}
    
    // CSI 서비스 등록
    csi.RegisterIdentityServer(server, d)
    csi.RegisterControllerServer(server, d)
    csi.RegisterNodeServer(server, d)
    
    // 소켓 리스너 생성
    listener, err := net.Listen("unix", "/csi/csi.sock")
    if err != nil {
        panic(err)
    }
    
    // 서버 시작
    go server.Serve(listener)
    
    // 종료 시그널 처리
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
    <-sigCh
    
    server.GracefulStop()
}
```

## 결론

Kubernetes 확장 메커니즘은 다양한 사용 사례와 요구 사항에 맞게 Kubernetes를 사용자 정의할 수 있는 강력한 방법을 제공합니다. CRD와 커스텀 컨트롤러를 통해 새로운 API를 정의하고, 어드미션 웹훅을 통해 API 요청을 검증하거나 수정하며, 스케줄러 확장을 통해 파드 배치 결정을 사용자 정의하고, CNI 및 CSI를 통해 네트워킹 및 스토리지 솔루션을 통합할 수 있습니다.

이러한 확장 메커니즘을 활용하면 Kubernetes를 조직의 특정 요구 사항에 맞게 조정하고, 복잡한 애플리케이션 관리를 자동화하며, 클라우드 네이티브 생태계의 이점을 최대한 활용할 수 있습니다.
