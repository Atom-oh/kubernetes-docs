# Kubernetes 확장

> **지원 버전**: Kubernetes 1.32, 1.33, 1.34
> **마지막 업데이트**: 2026년 2월 19일

Kubernetes는 확장성을 고려하여 설계된 플랫폼으로, 다양한 방법으로 기능을 확장할 수 있습니다. 이 장에서는 Kubernetes를 확장하는 다양한 방법과 Amazon EKS에서의 확장 기능 활용 방법에 대해 알아보겠습니다.

## 목차
1. [Kubernetes 확장 개요](#kubernetes-확장-개요)
2. [커스텀 리소스](#커스텀-리소스)
3. [오퍼레이터 패턴](#오퍼레이터-패턴)
4. [어드미션 컨트롤러](#어드미션-컨트롤러)
5. [API 서버 확장](#api-서버-확장)
6. [스케줄러 확장](#스케줄러-확장)
7. [클라우드 컨트롤러 매니저](#클라우드-컨트롤러-매니저)
8. [CSI(Container Storage Interface)](#csicontainer-storage-interface)
9. [CNI(Container Network Interface)](#cnicontainer-network-interface)
10. [디바이스 플러그인](#디바이스-플러그인)
11. [Amazon EKS에서의 확장 기능](#amazon-eks에서의-확장-기능)
12. [모범 사례](#모범-사례)
13. [결론](#결론)

## Kubernetes 확장 개요

Kubernetes는 다양한 확장 지점을 제공하여 기본 기능을 확장하고 사용자 정의할 수 있습니다. 주요 확장 지점은 다음과 같습니다:

1. **커스텀 리소스**: 새로운 API 객체 유형 정의
2. **오퍼레이터**: 커스텀 리소스와 컨트롤러를 결합하여 복잡한 애플리케이션 관리
3. **어드미션 컨트롤러**: API 요청을 가로채고 수정하거나 검증
4. **API 서버 확장**: API 서버에 새로운 엔드포인트 추가
5. **스케줄러 확장**: 포드 스케줄링 로직 사용자 정의
6. **클라우드 컨트롤러 매니저**: 클라우드 제공업체별 기능 통합
7. **CSI(Container Storage Interface)**: 스토리지 시스템 통합
8. **CNI(Container Network Interface)**: 네트워킹 솔루션 통합
9. **디바이스 플러그인**: 특수 하드웨어 통합

다음 다이어그램은 Kubernetes의 주요 확장 지점을 보여줍니다:

```mermaid
flowchart TD
    User[사용자/클라이언트] --> API[API 서버]
    
    subgraph "API 확장"
        API --> CR[커스텀 리소스]
        API --> AC[어드미션 컨트롤러]
        API --> AE[API 서버 확장]
    end
    
    subgraph "컨트롤러 확장"
        CR --> OP[오퍼레이터]
        API --> CCM[클라우드 컨트롤러 매니저]
    end
    
    subgraph "스케줄링 확장"
        API --> SCH[스케줄러 확장]
    end
    
    subgraph "노드 확장"
        Node[노드] --> CSI[CSI 드라이버]
        Node --> CNI[CNI 플러그인]
        Node --> DP[디바이스 플러그인]
    end
    
    API --> Node
    
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    class API,CR,AC,AE,OP,CCM,SCH,Node k8sComponent;
    class User userApp;
    class CSI,CNI,DP default;
```

### 확장 방법 선택

적절한 확장 방법을 선택하는 데 고려해야 할 사항:

1. **사용 사례**: 확장하려는 기능의 유형
2. **복잡성**: 구현 및 유지 관리의 복잡성
3. **성능 영향**: 확장이 클러스터 성능에 미치는 영향
4. **업그레이드 호환성**: Kubernetes 버전 업그레이드와의 호환성
5. **커뮤니티 지원**: 확장 방법에 대한 커뮤니티 지원 수준

## 커스텀 리소스

커스텀 리소스는 Kubernetes API를 확장하여 새로운 객체 유형을 정의하는 방법입니다.

다음 다이어그램은 커스텀 리소스의 작동 방식을 보여줍니다:

```mermaid
flowchart TD
    User[사용자] --> |1. 생성/수정| CRD[커스텀 리소스 정의]
    User --> |2. 생성/수정| CR[커스텀 리소스 인스턴스]
    
    CRD --> |정의| CR
    
    subgraph "Kubernetes API 서버"
        CRD
        CR
        API[API 등록]
        VAL[검증]
        STOR[(etcd 스토리지)]
    end
    
    CRD --> |등록| API
    CR --> |검증| VAL
    CR --> |저장| STOR
    
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    class CRD,CR,API,VAL k8sComponent;
    class User userApp;
    class STOR dataStore;
```

### 커스텀 리소스 정의(CRD)

CRD는 새로운 리소스 유형을 정의하는 가장 간단한 방법입니다:

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

위 예시에서 `Backup`이라는 새로운 리소스 유형을 정의하고, 해당 리소스의 스키마와 추가 프린터 열을 지정합니다.

### 커스텀 리소스 인스턴스 생성

CRD를 정의한 후 해당 유형의 리소스 인스턴스를 생성할 수 있습니다:

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

### 커스텀 리소스 검증

CRD에서 OpenAPI v3 스키마를 사용하여 커스텀 리소스의 유효성을 검증할 수 있습니다:

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
          pattern: '^[a-zA-Z0-9./:_-]+$'
      required:
      - replicas
      - image
```

위 예시에서 `replicas` 필드는 1에서 10 사이의 정수여야 하고, `image` 필드는 지정된 패턴과 일치해야 합니다.

### 버전 관리

CRD는 여러 버전을 지원하여 API 진화를 가능하게 합니다:

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

위 예시에서 `v1alpha1`, `v1beta1`, `v1` 세 가지 버전이 제공되지만, 데이터는 `v1` 형식으로 저장됩니다.

### 변환 웹훅

서로 다른 버전 간의 변환을 처리하기 위해 변환 웹훅을 사용할 수 있습니다:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: backups.example.com
spec:
  # ... 다른 필드 생략 ...
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: default
          name: example-conversion-webhook
          path: /convert
      conversionReviewVersions:
      - v1
```

## 오퍼레이터 패턴

오퍼레이터 패턴은 커스텀 리소스와 컨트롤러를 결합하여 복잡한 애플리케이션의 운영 지식을 자동화하는 방법입니다.

다음 다이어그램은 오퍼레이터 패턴의 작동 방식을 보여줍니다:

```mermaid
flowchart TD
    User[사용자] --> |1. 생성/수정| CR[커스텀 리소스]
    
    subgraph "Kubernetes API 서버"
        CR
        STOR[(etcd 스토리지)]
    end
    
    CR --> |저장| STOR
    
    subgraph "오퍼레이터"
        CTRL[컨트롤러] --> |2. 감시| CR
        CTRL --> |3. 상태 확인| CR
        CTRL --> |6. 상태 업데이트| CR
    end
    
    CTRL --> |4. 조치 결정| ACT[액션]
    ACT --> |5. 실행| K8S[Kubernetes 리소스]
    
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    class CR,K8S k8sComponent;
    class User userApp;
    class STOR dataStore;
    class CTRL,ACT default;
```

### 오퍼레이터 개념

오퍼레이터는 다음 구성 요소로 이루어집니다:

1. **커스텀 리소스 정의(CRD)**: 관리할 리소스의 스키마 정의
2. **컨트롤러**: 커스텀 리소스의 상태를 모니터링하고 원하는 상태로 조정하는 로직
3. **Kubernetes API 클라이언트**: Kubernetes API와 상호 작용하기 위한 클라이언트

### 오퍼레이터 예시

데이터베이스 오퍼레이터 예시:

```yaml
# 커스텀 리소스 정의
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
# 데이터베이스 인스턴스
apiVersion: example.com/v1
kind: Database
metadata:
  name: my-db
spec:
  engine: postgresql
  version: "13.4"
  storageSize: 10Gi
  replicas: 3
```

### 오퍼레이터 개발 도구

오퍼레이터를 개발하기 위한 도구:

1. **Operator SDK**: Go, Ansible, Helm을 사용하여 오퍼레이터 개발
2. **KUDO(Kubernetes Universal Declarative Operator)**: 선언적 방식으로 오퍼레이터 개발
3. **Kubebuilder**: Go 기반 오퍼레이터 개발 프레임워크
4. **Metacontroller**: 웹훅 기반 오퍼레이터 개발

#### Operator SDK 예시

Operator SDK를 사용한 오퍼레이터 생성:

```bash
# Operator SDK 설치
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.16.0/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# 새 오퍼레이터 프로젝트 생성
operator-sdk init --domain example.com --repo github.com/example/database-operator

# API 생성
operator-sdk create api --group database --version v1 --kind Database --resource --controller

# 컨트롤러 구현 (main.go, controllers/database_controller.go 등)

# 오퍼레이터 빌드 및 배포
make docker-build docker-push
make deploy
```

### 인기 있는 오퍼레이터

많이 사용되는 오픈 소스 오퍼레이터:

1. **Prometheus Operator**: Prometheus 모니터링 스택 관리
2. **Elasticsearch Operator**: Elasticsearch 클러스터 관리
3. **etcd Operator**: etcd 클러스터 관리
4. **PostgreSQL Operator**: PostgreSQL 데이터베이스 관리
5. **Jaeger Operator**: Jaeger 분산 추적 시스템 관리
6. **Strimzi Kafka Operator**: Apache Kafka 클러스터 관리
7. **Istio Operator**: Istio 서비스 메시 관리
## 어드미션 컨트롤러

어드미션 컨트롤러는 Kubernetes API 서버에 대한 요청을 가로채고 수정하거나 검증하는 플러그인입니다.

다음 다이어그램은 어드미션 컨트롤러의 작동 방식을 보여줍니다:

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Auth as 인증<br/>권한 부여
    participant MAC as 변형<br/>어드미션 컨트롤러
    participant MWH as 변형 웹훅
    participant VAC as 검증<br/>어드미션 컨트롤러
    participant VWH as 검증 웹훅
    participant API as API 처리
    participant STOR as etcd 스토리지

    User->>Auth: 1. API 요청
    Auth->>MAC: 2. 요청 통과
    MAC-->>MWH: 웹훅 호출
    MWH-->>MAC: 응답
    MAC->>VAC: 3. 변형된 요청
    VAC-->>VWH: 웹훅 호출
    VWH-->>VAC: 응답
    VAC->>API: 4. 검증된 요청
    API->>STOR: 5. 저장
```

### 어드미션 컨트롤러 유형

Kubernetes에는 두 가지 유형의 어드미션 컨트롤러가 있습니다:

1. **변형(Mutating) 어드미션 컨트롤러**: 리소스를 변경할 수 있음
2. **검증(Validating) 어드미션 컨트롤러**: 리소스를 검증만 할 수 있음

### 내장 어드미션 컨트롤러

Kubernetes에는 여러 내장 어드미션 컨트롤러가 있습니다:

1. **NamespaceLifecycle**: 삭제 중인 네임스페이스에 리소스 생성을 방지
2. **LimitRanger**: 포드 및 컨테이너에 기본 리소스 제한 설정
3. **ServiceAccount**: 서비스 계정 자동 생성 및 토큰 추가
4. **DefaultStorageClass**: PVC에 기본 스토리지 클래스 할당
5. **ResourceQuota**: 네임스페이스별 리소스 사용량 제한
6. **PodSecurityPolicy**: 포드 보안 정책 적용
7. **NodeRestriction**: 노드가 수정할 수 있는 리소스 제한

### 웹훅 어드미션 컨트롤러

사용자 정의 로직을 구현하기 위해 웹훅 어드미션 컨트롤러를 사용할 수 있습니다:

```yaml
# 변형 웹훅 구성
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
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

```yaml
# 검증 웹훅 구성
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
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

### 웹훅 서버 구현

웹훅 서버는 다음과 같은 엔드포인트를 구현해야 합니다:

```go
// 변형 웹훅 예시
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    var body []byte
    if r.Body != nil {
        if data, err := ioutil.ReadAll(r.Body); err == nil {
            body = data
        }
    }

    // AdmissionReview 객체로 변환
    admissionReview := v1.AdmissionReview{}
    if err := json.Unmarshal(body, &admissionReview); err != nil {
        http.Error(w, "Could not parse admission review request", http.StatusBadRequest)
        return
    }

    // 포드 객체 추출
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Could not parse pod object", http.StatusBadRequest)
        return
    }

    // 패치 생성
    patches := []map[string]interface{}{
        {
            "op":    "add",
            "path":  "/metadata/labels/injected-by",
            "value": "mutating-webhook",
        },
    }

    patchBytes, _ := json.Marshal(patches)

    // 응답 생성
    admissionResponse := v1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: true,
        Patch:   patchBytes,
        PatchType: func() *v1.PatchType {
            pt := v1.PatchTypeJSONPatch
            return &pt
        }(),
    }

    admissionReview.Response = &admissionResponse
    resp, _ := json.Marshal(admissionReview)
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}
```

```go
// 검증 웹훅 예시
func validateHandler(w http.ResponseWriter, r *http.Request) {
    var body []byte
    if r.Body != nil {
        if data, err := ioutil.ReadAll(r.Body); err == nil {
            body = data
        }
    }

    // AdmissionReview 객체로 변환
    admissionReview := v1.AdmissionReview{}
    if err := json.Unmarshal(body, &admissionReview); err != nil {
        http.Error(w, "Could not parse admission review request", http.StatusBadRequest)
        return
    }

    // 포드 객체 추출
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Could not parse pod object", http.StatusBadRequest)
        return
    }

    // 검증 로직
    allowed := true
    var message string
    for _, container := range pod.Spec.Containers {
        if container.Image == "nginx:latest" {
            allowed = false
            message = "Using 'latest' tag is not allowed. Please specify a version."
            break
        }
    }

    // 응답 생성
    admissionResponse := v1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: allowed,
    }

    if !allowed {
        admissionResponse.Result = &metav1.Status{
            Message: message,
        }
    }

    admissionReview.Response = &admissionResponse
    resp, _ := json.Marshal(admissionReview)
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}
```

### 인기 있는 어드미션 컨트롤러 프로젝트

1. **OPA Gatekeeper**: Open Policy Agent를 사용한 정책 적용
2. **Kyverno**: YAML 기반 정책 엔진
3. **Istio**: 서비스 메시 사이드카 주입
4. **cert-manager**: TLS 인증서 관리

## API 서버 확장

API 서버 확장은 Kubernetes API 서버에 새로운 엔드포인트를 추가하는 방법입니다.

### 확장 API 서버

확장 API 서버는 Kubernetes API 서버와 별도로 실행되는 서버로, 커스텀 API를 제공합니다:

```yaml
# APIService 정의
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

### 확장 API 서버 구현

확장 API 서버는 다음과 같은 구성 요소로 이루어집니다:

1. **API 서버**: Kubernetes API 서버와 유사한 인터페이스 제공
2. **리소스 핸들러**: 특정 리소스 유형에 대한 요청 처리
3. **스토리지 백엔드**: 리소스 데이터 저장

```go
// 확장 API 서버 예시
func main() {
    // 서버 구성
    config := genericapiserver.NewRecommendedConfig(apiserver.Codecs)
    config.OpenAPIConfig = genericapiserver.DefaultOpenAPIConfig(
        sampleopenapi.GetOpenAPIDefinitions,
        openapi.NewDefinitionNamer(apiserver.Scheme),
    )
    config.EnableIndex = true
    config.EnableDiscovery = true

    // 서버 생성
    server, err := config.Complete().New("sample-apiserver", genericapiserver.NewEmptyDelegate())
    if err != nil {
        log.Fatalf("Error creating server: %v", err)
    }

    // API 그룹 정보 설정
    apiGroupInfo := genericapiserver.NewDefaultAPIGroupInfo(
        samplev1alpha1.GroupName,
        apiserver.Scheme,
        metav1.ParameterCodec,
        apiserver.Codecs,
    )

    // 스토리지 설정
    apiGroupInfo.VersionedResourcesStorageMap["v1alpha1"] = map[string]rest.Storage{
        "widgets": NewWidgetStorage(),
    }

    // API 그룹 설치
    if err := server.InstallAPIGroup(&apiGroupInfo); err != nil {
        log.Fatalf("Error installing API group: %v", err)
    }

    // 서버 실행
    if err := server.PrepareRun().Run(stopCh); err != nil {
        log.Fatalf("Error running server: %v", err)
    }
}
```

### 애그리게이션 레이어

애그리게이션 레이어는 여러 API 서버를 단일 API 서버처럼 보이게 합니다:

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

## 스케줄러 확장

스케줄러 확장은 Kubernetes 스케줄러의 동작을 사용자 정의하는 방법입니다.

### 스케줄러 프레임워크

Kubernetes 1.15부터 도입된 스케줄러 프레임워크는 플러그인을 통해 스케줄링 파이프라인의 다양한 단계를 확장할 수 있습니다:

1. **Queue Sort**: 스케줄링 큐의 포드 정렬
2. **Pre-filter**: 필터링 전 포드 및 클러스터 상태 검사
3. **Filter**: 포드를 실행할 수 없는 노드 필터링
4. **Post-filter**: 필터링 후 작업 수행
5. **Pre-score**: 점수 계산 전 작업 수행
6. **Score**: 노드에 점수 부여
7. **Normalize Score**: 점수 정규화
8. **Reserve**: 포드를 위한 리소스 예약
9. **Permit**: 포드 스케줄링 허용, 거부 또는 지연
10. **Pre-bind**: 바인딩 전 작업 수행
11. **Bind**: 포드를 노드에 바인딩
12. **Post-bind**: 바인딩 후 작업 수행

### 스케줄러 구성

스케줄러 구성 예시:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1beta1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
clientConnection:
  kubeconfig: /etc/kubernetes/scheduler.conf
profiles:
- schedulerName: default-scheduler
  plugins:
    queueSort:
      enabled:
      - name: PrioritySort
    preFilter:
      enabled:
      - name: NodeResourcesFit
      - name: NodePorts
      - name: PodTopologySpread
      - name: InterPodAffinity
      - name: VolumeBinding
      - name: NodeAffinity
    filter:
      enabled:
      - name: NodeUnschedulable
      - name: NodeName
      - name: TaintToleration
      - name: NodeAffinity
      - name: NodePorts
      - name: NodeResourcesFit
      - name: VolumeRestrictions
      - name: EBSLimits
      - name: GCEPDLimits
      - name: NodeVolumeLimits
      - name: AzureDiskLimits
      - name: VolumeBinding
      - name: VolumeZone
      - name: PodTopologySpread
      - name: InterPodAffinity
    postFilter:
      enabled:
      - name: DefaultPreemption
    preScore:
      enabled:
      - name: InterPodAffinity
      - name: PodTopologySpread
      - name: TaintToleration
      - name: NodeAffinity
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 1
      - name: ImageLocality
        weight: 1
      - name: InterPodAffinity
        weight: 1
      - name: NodeResourcesFit
        weight: 1
      - name: NodeAffinity
        weight: 1
      - name: PodTopologySpread
        weight: 2
      - name: TaintToleration
        weight: 1
    reserve:
      enabled:
      - name: VolumeBinding
    permit:
      enabled: []
    preBind:
      enabled:
      - name: VolumeBinding
    bind:
      enabled:
      - name: DefaultBinder
    postBind:
      enabled: []
```

### 사용자 정의 스케줄러

자체 스케줄러를 구현하여 Kubernetes와 함께 실행할 수도 있습니다:

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
      containers:
      - name: custom-scheduler
        image: example/custom-scheduler:v1.0.0
        command:
        - /custom-scheduler
        - --kubeconfig=/etc/kubernetes/scheduler.conf
        volumeMounts:
        - name: kubeconfig
          mountPath: /etc/kubernetes/scheduler.conf
          readOnly: true
      volumes:
      - name: kubeconfig
        hostPath:
          path: /etc/kubernetes/scheduler.conf
          type: File
```

포드에서 사용자 정의 스케줄러 지정:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: custom-scheduler
  containers:
  - name: container
    image: nginx
```

## 클라우드 컨트롤러 매니저

클라우드 컨트롤러 매니저는 Kubernetes와 클라우드 제공업체 간의 인터페이스를 제공합니다.

### 클라우드 컨트롤러 매니저 구성 요소

클라우드 컨트롤러 매니저는 다음과 같은 컨트롤러로 구성됩니다:

1. **노드 컨트롤러**: 클라우드 제공업체 API를 통해 노드 정보 업데이트
2. **라우트 컨트롤러**: 클라우드 네트워크에 라우트 설정
3. **서비스 컨트롤러**: 클라우드 로드 밸런서 생성, 업데이트, 삭제

### AWS 클라우드 컨트롤러 매니저

AWS 클라우드 컨트롤러 매니저 구성 예시:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-cloud-controller-manager
  namespace: kube-system
data:
  cloud.conf: |
    [global]
    zone = us-east-1a
    vpc = vpc-xxx
    subnet-id = subnet-xxx
    role-arn = arn:aws:iam::xxx:role/xxx
    kubernetes.io/cluster/my-cluster = owned
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: aws-cloud-controller-manager
  namespace: kube-system
spec:
  selector:
    matchLabels:
      k8s-app: aws-cloud-controller-manager
  template:
    metadata:
      labels:
        k8s-app: aws-cloud-controller-manager
    spec:
      nodeSelector:
        node-role.kubernetes.io/master: ""
      tolerations:
      - key: node.cloudprovider.kubernetes.io/uninitialized
        value: "true"
        effect: NoSchedule
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
      serviceAccountName: cloud-controller-manager
      containers:
      - name: aws-cloud-controller-manager
        image: k8s.gcr.io/cloud-controller-manager:v1.21.0
        command:
        - /usr/local/bin/cloud-controller-manager
        - --cloud-provider=aws
        - --cloud-config=/etc/kubernetes/cloud.conf
        - --use-service-account-credentials
        - --allocate-node-cidrs=false
        volumeMounts:
        - name: cloud-config
          mountPath: /etc/kubernetes/cloud.conf
          readOnly: true
      volumes:
      - name: cloud-config
        configMap:
          name: aws-cloud-controller-manager
```
## CSI(Container Storage Interface)

CSI는 Kubernetes와 스토리지 시스템 간의 표준 인터페이스를 제공합니다.

다음 다이어그램은 CSI의 아키텍처와 작동 방식을 보여줍니다:

```mermaid
flowchart TD
    User[사용자] --> |1. 생성| PVC[PersistentVolumeClaim]
    
    subgraph "Kubernetes 컴포넌트"
        PVC --> |참조| SC[StorageClass]
        SC --> |지정| PROV[CSI 외부 프로비저너]
        PROV --> |2. 볼륨 생성 요청| CSI[CSI 드라이버]
        CSI --> |3. 볼륨 생성| PV[PersistentVolume]
        PV --> |바인딩| PVC
        
        POD[Pod] --> |마운트 요청| PVC
        CSI --> |4. 볼륨 마운트| POD
    end
    
    subgraph "CSI 드라이버"
        CSI --> CTRL[컨트롤러 서비스]
        CSI --> NODE[노드 서비스]
    end
    
    CTRL --> |5. 볼륨 관리| STOR[(스토리지 시스템)]
    NODE --> |6. 볼륨 마운트| STOR
    
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    class PVC,SC,PROV,PV,POD k8sComponent;
    class User userApp;
    class STOR dataStore;
    class CSI,CTRL,NODE default;
```

### CSI 아키텍처

CSI는 다음과 같은 구성 요소로 이루어집니다:

1. **CSI 컨트롤러 플러그인**: 볼륨 생성, 삭제, 스냅샷 등의 작업 처리
2. **CSI 노드 플러그인**: 볼륨 마운트, 언마운트 등의 작업 처리
3. **CSI 드라이버**: 특정 스토리지 시스템과 통합하는 구현체

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

### CSI 드라이버 배포

CSI 드라이버 배포 예시:

```yaml
# CSI 컨트롤러 서비스
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
      containers:
      - name: csi-provisioner
        image: k8s.gcr.io/sig-storage/csi-provisioner:v2.1.0
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
        image: k8s.gcr.io/sig-storage/csi-attacher:v3.1.0
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

# CSI 노드 서비스
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
      hostNetwork: true
      containers:
      - name: csi-node-driver-registrar
        image: k8s.gcr.io/sig-storage/csi-node-driver-registrar:v2.1.0
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

### 스토리지 클래스 및 PVC

CSI 드라이버를 사용하는 스토리지 클래스 및 PVC 예시:

```yaml
# 스토리지 클래스
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: example-csi
provisioner: example.csi.k8s.io
parameters:
  type: ssd
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: Immediate

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

### 인기 있는 CSI 드라이버

1. **AWS EBS CSI 드라이버**: AWS EBS 볼륨 관리
2. **AWS EFS CSI 드라이버**: AWS EFS 파일 시스템 관리
3. **GCE PD CSI 드라이버**: Google Compute Engine 영구 디스크 관리
4. **Azure Disk CSI 드라이버**: Azure 디스크 관리
5. **Ceph RBD CSI 드라이버**: Ceph RBD 볼륨 관리
6. **NFS CSI 드라이버**: NFS 볼륨 관리

## CNI(Container Network Interface)

CNI는 Kubernetes와 네트워킹 솔루션 간의 표준 인터페이스를 제공합니다.

다음 다이어그램은 CNI의 아키텍처와 작동 방식을 보여줍니다:

```mermaid
flowchart TD
    subgraph "Kubernetes 컴포넌트"
        API[API 서버] --> |포드 생성| KUB[kubelet]
        KUB --> |1. 컨테이너 생성| CRI[컨테이너 런타임]
        CRI --> |2. 네트워크 설정 요청| CNI[CNI 플러그인]
    end
    
    subgraph "CNI 플러그인"
        CNI --> |3. IP 할당 요청| IPAM[IPAM 플러그인]
        CNI --> |5. 네트워크 설정| NET[네트워크 구성]
    end
    
    IPAM --> |4. IP 할당| IPPOOL[(IP 풀)]
    NET --> |6. 네트워크 구성 적용| POD[포드 네트워크]
    
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    class API,KUB,CRI,POD k8sComponent;
    class IPPOOL dataStore;
    class CNI,IPAM,NET default;
```

### CNI 아키텍처

CNI는 다음과 같은 구성 요소로 이루어집니다:

1. **CNI 플러그인**: 컨테이너 네트워크 인터페이스 구성
2. **IPAM 플러그인**: IP 주소 할당 및 관리
3. **메타 플러그인**: 여러 플러그인을 조합하여 사용

```
+-------------------+
|                   |
|  Kubernetes       |
|  (kubelet)        |
|                   |
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

### CNI 플러그인 구성

CNI 플러그인 구성 예시:

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

### 인기 있는 CNI 플러그인

1. **Calico**: 네트워크 정책 및 보안 기능이 강화된 CNI
2. **Flannel**: 간단한 오버레이 네트워크 제공
3. **Cilium**: eBPF 기반의 네트워킹 및 보안 솔루션
4. **Weave Net**: 멀티 호스트 컨테이너 네트워킹 솔루션
5. **AWS VPC CNI**: AWS VPC와 통합된 CNI
6. **Azure CNI**: Azure 가상 네트워크와 통합된 CNI
7. **Antrea**: Open vSwitch 기반의 네트워킹 솔루션

### CNI 플러그인 설치

Calico CNI 플러그인 설치 예시:

```bash
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
```

## 디바이스 플러그인

디바이스 플러그인은 Kubernetes와 특수 하드웨어 간의 인터페이스를 제공합니다.

### 디바이스 플러그인 아키텍처

디바이스 플러그인은 다음과 같은 구성 요소로 이루어집니다:

1. **디바이스 플러그인 서버**: 디바이스 검색, 할당, 초기화 등의 작업 처리
2. **kubelet**: 디바이스 플러그인과 통신하여 포드에 디바이스 할당

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

### NVIDIA GPU 디바이스 플러그인

NVIDIA GPU 디바이스 플러그인 배포 예시:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: nvidia-device-plugin-ctr
        image: nvidia/k8s-device-plugin:v0.9.0
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        volumeMounts:
        - name: device-plugin
          mountPath: /var/lib/kubelet/device-plugins
      volumes:
      - name: device-plugin
        hostPath:
          path: /var/lib/kubelet/device-plugins
```

### GPU 요청 포드

GPU를 요청하는 포드 예시:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: cuda-container
    image: nvidia/cuda:11.0-base
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

### 인기 있는 디바이스 플러그인

1. **NVIDIA GPU 디바이스 플러그인**: NVIDIA GPU 관리
2. **AMD GPU 디바이스 플러그인**: AMD GPU 관리
3. **FPGA 디바이스 플러그인**: FPGA 디바이스 관리
4. **InfiniBand 디바이스 플러그인**: InfiniBand 디바이스 관리
5. **SRIOV 네트워크 디바이스 플러그인**: SR-IOV 네트워크 디바이스 관리

## Amazon EKS에서의 확장 기능

Amazon EKS는 다양한 확장 기능을 지원하여 Kubernetes 클러스터의 기능을 확장할 수 있습니다.

다음 다이어그램은 Amazon EKS의 확장 기능 아키텍처를 보여줍니다:

```mermaid
flowchart TD
    subgraph "Amazon EKS"
        EKS[EKS 클러스터] --> |관리| CP[컨트롤 플레인]
        EKS --> |관리| NG[노드 그룹]
        
        subgraph "EKS 추가 기능"
            CP --> VCNI[Amazon VPC CNI]
            CP --> CDNS[CoreDNS]
            CP --> KP[kube-proxy]
            CP --> EBSCSI[Amazon EBS CSI 드라이버]
            CP --> ALBC[AWS Load Balancer Controller]
        end
    end
    
    subgraph "AWS 서비스"
        VCNI --> VPC[Amazon VPC]
        EBSCSI --> EBS[Amazon EBS]
        ALBC --> ELB[Elastic Load Balancing]
        
        IAM[AWS IAM] --> |IRSA| NG
        ACK[AWS Controllers for Kubernetes] --> AWS[AWS 서비스]
    end
    
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    class EKS,CP,NG,VCNI,CDNS,KP,EBSCSI,ALBC,ACK k8sComponent;
    class VPC,EBS,ELB,IAM,AWS awsService;
```

### EKS 추가 기능

Amazon EKS는 다음과 같은 추가 기능을 제공합니다:

1. **Amazon VPC CNI**: AWS VPC와 통합된 네트워킹
2. **CoreDNS**: 클러스터 내 DNS 서비스
3. **kube-proxy**: 네트워크 프록시
4. **Amazon EBS CSI 드라이버**: EBS 볼륨 관리
5. **AWS Load Balancer Controller**: AWS 로드 밸런서 관리

```bash
# EKS 추가 기능 목록 확인
aws eks list-addons --cluster-name my-cluster

# EKS 추가 기능 설치
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-ebs-csi-driver \
  --service-account-role-arn arn:aws:iam::123456789012:role/AmazonEKS_EBS_CSI_DriverRole

# EKS 추가 기능 업데이트
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name amazon-ebs-csi-driver \
  --addon-version v1.5.0-eksbuild.1

# EKS 추가 기능 삭제
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name amazon-ebs-csi-driver
```

### AWS Controllers for Kubernetes(ACK)

ACK는 Kubernetes에서 AWS 리소스를 관리할 수 있게 해주는 오퍼레이터 모음입니다:

```bash
# ACK 컨트롤러 설치
helm repo add ack-controller https://aws.github.io/aws-controllers-k8s
helm install ack-s3-controller ack-controller/s3-chart

# S3 버킷 생성
cat <<EOF | kubectl apply -f -
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  name: my-bucket-123456
EOF
```

### AWS Load Balancer Controller

AWS Load Balancer Controller는 Kubernetes 서비스 및 인그레스를 AWS 로드 밸런서와 통합합니다:

```yaml
# ALB 인그레스 예시
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
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

### IAM Roles for Service Accounts(IRSA)

IRSA는 Kubernetes 서비스 계정에 AWS IAM 역할을 연결하여 포드가 AWS 서비스에 안전하게 접근할 수 있게 합니다:

```bash
# OIDC 제공자 생성
eksctl utils associate-iam-oidc-provider \
  --cluster my-cluster \
  --approve

# IAM 역할 및 서비스 계정 생성
eksctl create iamserviceaccount \
  --cluster my-cluster \
  --namespace default \
  --name my-service-account \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve

# 서비스 계정을 사용하는 포드
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
spec:
  serviceAccountName: my-service-account
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
EOF
```

## 모범 사례

Kubernetes 확장 기능을 구현할 때 고려해야 할 모범 사례를 알아보겠습니다.

### 설계 모범 사례

1. **표준 인터페이스 사용**: 가능한 경우 CSI, CNI 등의 표준 인터페이스 사용
2. **선언적 API 설계**: 명령형이 아닌 선언적 API 설계
3. **Kubernetes 디자인 원칙 준수**: 컨트롤러 패턴, 레벨 트리거링 등의 원칙 준수
4. **버전 관리**: API 버전 관리 및 호환성 유지
5. **최소 권한 원칙**: 필요한 최소한의 권한만 부여

### 구현 모범 사례

1. **재사용 가능한 라이브러리 활용**: client-go, controller-runtime 등의 라이브러리 활용
2. **적절한 오류 처리**: 오류 상황에 대한 적절한 처리 및 로깅
3. **지수 백오프**: 재시도 시 지수 백오프 사용
4. **리소스 제한 설정**: 메모리 및 CPU 제한 설정
5. **상태 보고**: 리소스 상태 정확히 보고

### 배포 모범 사례

1. **점진적 롤아웃**: 한 번에 모든 것을 변경하지 않고 점진적으로 롤아웃
2. **버전 관리**: 이미지 태그에 latest 사용 지양
3. **헬스 체크**: 적절한 활성 및 준비 프로브 구성
4. **로깅 및 모니터링**: 포괄적인 로깅 및 모니터링 구성
5. **문서화**: API 및 사용 방법 문서화

### 보안 모범 사례

1. **최소 권한 원칙**: 필요한 최소한의 권한만 부여
2. **RBAC 사용**: 적절한 RBAC 정책 구성
3. **네트워크 정책**: 적절한 네트워크 정책 구성
4. **이미지 스캐닝**: 컨테이너 이미지 취약점 스캐닝
5. **시크릿 관리**: 시크릿 안전하게 관리

### EKS 특화 모범 사례

1. **관리형 추가 기능 사용**: 가능한 경우 EKS 관리형 추가 기능 사용
2. **IRSA 사용**: 포드별 IAM 권한 관리를 위해 IRSA 사용
3. **VPC CNI 구성**: 네트워킹 요구 사항에 맞게 VPC CNI 구성
4. **보안 그룹**: 적절한 보안 그룹 구성
5. **비용 최적화**: 적절한 인스턴스 유형 및 크기 선택

## 결론

Kubernetes는 다양한 확장 지점을 제공하여 기본 기능을 확장하고 사용자 정의할 수 있습니다. 커스텀 리소스, 오퍼레이터, 어드미션 컨트롤러, API 서버 확장, 스케줄러 확장, CSI, CNI, 디바이스 플러그인 등의 확장 메커니즘을 통해 Kubernetes를 다양한 환경과 요구 사항에 맞게 조정할 수 있습니다.

Amazon EKS는 이러한 확장 기능을 지원하고, 추가적으로 EKS 추가 기능, ACK, AWS Load Balancer Controller, IRSA 등의 AWS 특화 기능을 제공하여 Kubernetes와 AWS 서비스 간의 통합을 간소화합니다.

Kubernetes 확장 기능을 구현할 때는 표준 인터페이스 사용, 선언적 API 설계, 최소 권한 원칙 등의 모범 사례를 따르는 것이 중요합니다. 이를 통해 안정적이고 확장 가능한 Kubernetes 환경을 구축할 수 있습니다.

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [Kubernetes 확장 퀴즈](../quizzes/core/11-extending-kubernetes-quiz.md)를 풀어보세요.
