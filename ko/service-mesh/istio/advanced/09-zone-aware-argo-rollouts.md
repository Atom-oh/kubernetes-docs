# Zone-Aware Argo Rollouts

> **검증 기준**: Istio 1.31.0, Argo Rollouts 1.10.0, Kubernetes 1.32–1.36
> **마지막 검토**: 2026년 9월 11일
> **난이도**: 고급

이 가이드는 AZ별 독립 canary와 cross-AZ failover를 구분합니다. 본문은 client cohort가 한 zone의 stable/canary Service를 선택하는 **zone 라우팅·격리 설계 예제**입니다. 해당 endpoint가 사라졌을 때 다른 zone으로 자동 failover하는 기능은 구현하지 않습니다.

## 목차

1. [문제 정의](#문제-정의)
2. [아키텍처 개요](#아키텍처-개요)
3. [핵심 설계 결정](#핵심-설계-결정)
4. [구현 가이드](#구현-가이드)
5. [트래픽 흐름](#트래픽-흐름)
6. [문제 해결](#문제-해결)
7. [모범 사례](#모범-사례)

## 문제 정의

### Spot 중단과 PDB

Spot 용량은 회수될 수 있으므로 상관된 용량 손실에 대비해야 합니다. 중단 알림은 best effort이며 stop/terminate는 일반적으로2분 전에 알리지만 hibernation은 즉시 시작합니다. EKS managed node group은 교체·rebalance를 시도하지만 중단 노드를 drain하기 전에 교체 노드가 Ready가 된다고 보장하지 않습니다.

PodDisruptionBudget은 자발적인 Eviction API 작업을 제한합니다. EC2 중단·node 장애·직접 Pod 삭제·모든 controller update를 막지는 않습니다. 아래 PDB는 Rollouts가 생성·관리하는 리소스가 아니라 앱 운영자가 정의하고 Kubernetes가 status를 계산합니다.

건강한 Pod9개에 **정수 `minAvailable: 6`**이라면 설명용 자발적 disruption 여유는3개입니다. 건강한 Pod가6개로 줄면 여유는0개입니다. “33% minimum이6개를 요구”하는 계산이 아닙니다. Expected Pod9개에서 `minAvailable: "33%"`는 올림하여3개이며, percentage `maxUnavailable`는 의미와 controller scale 조건이 다릅니다.

이를 zone마다 `minAvailable: 1`로 나누면 보호 수준도 바뀝니다. 한 zone이 사라지면 나머지 두 budget은 전체6개를 유지하는 대신 zone마다 건강한 Pod1개까지 자발적 eviction을 허용할 수 있습니다. 독립 운영에 유용할 수 있지만 다른 가용성·용량 정책입니다. Stable과 canary를 함께 선택하는 budget은 각 weighted destination의 용량을 따로 보장하지도 않습니다.

### 목표와 제약

| 설계 | Zone별 독립 버전 | Cross-AZ failover | 주요 제약 |
|---|---|---|---|
| 여러 AZ endpoint를 포함한 공통 revision/subset | Zone마다 독립 revision 제어는 하지 않음 | 선택된 endpoint pool 안에서 가능 | 다른 AZ에 건강한 용량과 호환되는 release/data 상태 필요 |
| 본문의 zone별 Rollout과 zone-filtered Service | 가능 | Locality 설정만으로 제공하지 않음 | 선택한 zone의 pool이 비면 그대로 비어 있음 |
| Zonal gateway/pipeline 앞의 별도 health-aware 진입 라우팅 | 설계 가능 | 별도 policy/controller·검증 필요 | 추가 routing·용량·identity·복구 조율 필요 |

엄격한 zone 필터, 서로 다른 zone별 hash, 투명한 failover를 DestinationRule 하나로 모두 얻을 수는 없습니다. 별도 진입 라우팅 설계는 이 배포 예제 범위 밖이며 여기서 production 검증하지 않았습니다.

## 아키텍처 개요

공통 `test` Service가 DNS 이름을 제공합니다. 주입된 client에는 VirtualService가 **명시적인 client Pod label**로 zone route를 선택합니다. 각 route는 해당 zone의 stable/canary Service를 가리키며, 별도 Rollout이 Service hash와 자신의 named route weight를 관리합니다.

Istiod는 설정을 Envoy에 반영하며 VirtualService·DestinationRule 객체가 network hop인 것은 아닙니다. Mesh 밖 client는 공통 Service의 일반 Kubernetes endpoint 선택을 사용하여 규칙을 우회할 수 있으므로 routing label은 보안 경계가 아닙니다.

각 zone의 Pod는 지정한 AZ에만 배치됩니다. 따라서 zone A Service에는 B/C fallback endpoint가 없습니다. 배포 상태를 분리해도 공통 control plane·API server·network·DB 의존성까지 사라지지는 않습니다.

## 핵심 설계 결정

### 1. Route 관리 범위

Rollouts1.10은 지정한 route weight와 지원되는 managed destination을 조정하며 destination 배열 전체를 무조건 교체하지 않습니다. 다른 route 이름으로 desired weight 충돌을 피할 수 있지만, 세 controller가 같은 VirtualService를 수정하면 Kubernetes `resourceVersion` 충돌·재조정 지연이 생길 수 있습니다. 더 강한 control-plane 격리가 필요하면 별도 객체/진입 routing을 검토합니다.

본문은 서로 다른 route(`zone-a-route`, `zone-b-route`, `zone-c-route`)와 **host-level 분할**을 사용하며 Service hash와 DestinationRule subset 관리를 혼합하지 않습니다. 두 대안은 [통합 가이드](08-argo-rollouts.md)에서 설명합니다.

### 2. Client Label과 실제 AZ

`sourceLabels`는 Istiod가 mesh 설정을 만들 때 source workload를 선택하며 runtime request-header 조건이 아닙니다. Node의 `topology.kubernetes.io/zone` label은 Pod에 자동 복사되지 않습니다. `routing.example.com/zone: a` 같은 Pod label을 사용한다면 실제 AZ 배치도 검증해야 합니다.

이 selector는 mesh client용이며 ingress gateway로 들어오는 일반 외부 요청을 분류하지 않습니다. `mesh` gateway 범위를 유지합니다. 예제는 알 수 없는 client cohort에 다른 zone을 조용히 선택하는 대신503을 반환합니다.

### 3. 선택된 Pool 밖으로는 Locality가 이동하지 않음

`zone: a`와 Rollout A hash로 선택한 subset은 형제 zone B subset으로 failover할 수 없습니다. Zone-filtered Service도 같습니다. Outlier detection은 선택한 upstream pool 안의 endpoint 적격성만 바꾸며 다른 VirtualService route로 점프하지 않습니다.

또한 `localityLbSetting.distribute`·`failover`·`failoverPriority`는 대안 관계이며 자유롭게 결합하는 필드가 아닙니다. `failover.from/to`는 `region/zone` 문자열이 아닌 **region**입니다. 이 필드로 A→B→C→A AZ 순환을 설정할 수 없습니다.

## 구현 가이드

### 전제조건

[Argo Rollouts 통합](08-argo-rollouts.md)의 controller·CLI·주입·Prometheus·workload 전제조건을 사용합니다. Default/legacy injection의 격리된 sidecar HTTP demo이며 revision mesh에서는 설치된 revision/tag를 선택해야 합니다. 호환되는 EC2 기반 Linux worker node·quota·network·image 접근·관측 구성이 필요합니다. Fargate는 이 예제 범위 밖이며 Istio 호환 범위 안의 현재 지원되는 EKS 버전을 선택하세요.

예시 `us-east-1a/b/c`는 실제 Node label로 바꿉니다. 계정마다 AZ 이름 매핑이 다를 수 있으므로 여러 계정의 물리 zone을 맞출 때는 AZ ID를 확인하세요. 고정한 demo image는 Linux amd64 전용이므로 각 AZ에 호환되는 node가 있거나 별도로 검증한 대체 image를 사용해야 합니다.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone,kubernetes.io/arch
```

### 1. Namespace와 공통/Zone Service

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: zone-rollouts-demo
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Service
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
```

공통 Service는 mesh caller의 DNS 진입점이며 인가 장치가 아닙니다.6개 zonal Service는 실제 Pod `zone` selector를 가지고 Rollouts가 stable/canary hash를 추가합니다.

### 2. Client Template 조건

다음 조각을 **기존 `zone-client-a` Deployment**에 병합하며 selector·container·검증한 image·resource·기존 배치 제약을 유지합니다. Deployment metadata에만 붙이지 말고 실제 Pod template에 route label을 둡니다.

```yaml
metadata:
  name: zone-client-a
  namespace: zone-rollouts-demo
spec:
  template:
    metadata:
      labels:
        routing.example.com/zone: a
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
```

B/C를 시험할 때도 label과 실제 AZ 제약이 일치하는 client를 준비합니다. Affinity 병합 시 기존 AND/OR 제한을 유지하여 node 허용 범위를 넓히지 마세요. `.spec.nodeName`과 선택된 Node의 zone을 대조합니다. 이 조각은 client를 배포하거나 node metadata를 자동 복사하지 않습니다.

### 3. 독립 Route를 가진 공통 VirtualService

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  hosts:
  - test
  - test.zone-rollouts-demo.svc.cluster.local
  gateways:
  - mesh
  http:
  - name: zone-a-route
    match:
    - sourceLabels:
        routing.example.com/zone: a
    route:
    - destination:
        host: test-stable-a
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-a
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-b-route
    match:
    - sourceLabels:
        routing.example.com/zone: b
    route:
    - destination:
        host: test-stable-b
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-b
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-c-route
    match:
    - sourceLabels:
        routing.example.com/zone: c
    route:
    - destination:
        host: test-stable-c
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-c
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: unclassified-client
    directResponse:
      status: 503
      body:
        string: No reviewed client-zone route
```

트래픽을 보내기 전에 각 controller가 의도한 hash·건강한 endpoint를 선택했는지 확인합니다. 초기 weight는 조정되지 않은90/10이 아닌100/0입니다. 각 named route는 mesh 재시도를 명시적으로 끄며 앱의 retry 동작은 별도입니다.

### 4. Zone별 Rollout

Workload·replica 수·requests/limits·pause는 demo 입력값입니다. Replica3개가 자동으로 node3개에 분산되지는 않습니다. 실제 배포에는 node-level spread/anti-affinity, 용량, PDB와 stable/canary 여유를 검토해야 합니다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-a
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: a
  template:
    metadata:
      labels:
        app: test
        zone: a
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
  strategy:
    canary:
      stableService: test-stable-a
      canaryService: test-canary-a
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-a-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-b
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: b
  template:
    metadata:
      labels:
        app: test
        zone: b
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1b
  strategy:
    canary:
      stableService: test-stable-b
      canaryService: test-canary-b
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-b-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-c
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: c
  template:
    metadata:
      labels:
        app: test
        zone: c
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1c
  strategy:
    canary:
      stableService: test-stable-c
      canaryService: test-canary-c
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-c-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
```

각 Rollout은 별도 selector, image/revision 상태, Service와 Analysis argument를 가집니다. 첫5% gate 뒤에는 의도적으로 promote해야 하는 무기한 pause가 있습니다. 강제 zone affinity 때문에 해당 AZ에 용량이 없으면 Pod는 Pending으로 남으며 건강한 다른 AZ로 이동하지 않습니다.

### 5. 명시적인 PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-a-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: a
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-b-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: b
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-c-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: c
```

Zone마다 최소1개라는 기존 예시 입력을 유지합니다. 앞의 전체 최소6개와 동등하지 않으며 weighted revision 각각을 보호하지 않습니다. 자발적인 유지보수 전에 `currentHealthy`·`desiredHealthy`·`disruptionsAllowed`를 확인하세요.

### 6. Zone별 Analysis

Rollout보다 먼저 이 template을 생성합니다. 없는 Pod-zone label 대신 실제 zonal canary Service 이름과 표준 source-reporter metric을 사용합니다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-check
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

기존 가이드의 성공 정의인 **HTTP2xx**를 분자로 사용합니다. 모두5xx인 창은 빈 분자가 아닌0이 되고, 무트래픽·누락 데이터는 finite-value/volume gate를 통과하지 않습니다. Source proxy를 수집하고 provider가 해당 Prometheus에 접근할 수 있어야 하며 실제 label이 selector와 일치해야 합니다.

`http://test.zone-rollouts-demo.svc.cluster.local:8080/color`로 대표성 있는 mesh 트래픽을 지속합니다. Caller label이 zone을 선택하고 controller가 해당 zone의 stable/canary weight를 정합니다.5분 warm-up은2분 metric lookback보다 길며20개 요청 추정값·측정 횟수는 설명용이지 통계적 신뢰도가 아닙니다.

## 트래픽 흐름

### 정상 Zonal 경로

검토한 AZ에 배치되고 올바른 label을 가진 client A에는 `zone-a-route`가 적용되어 A의 stable/canary Service를 선택합니다. 실제 비율은 표본·session·readiness에 따라 달라지며 요청10개마다 정확한 비율을 보장하지 않습니다.

### Zone 손실

적격 A endpoint가 모두 사라지면 A route에 건강한 upstream이 없습니다. Outlier threshold나 PDB를 바꾸어도 A Service에 B endpoint가 생기지는 않습니다. 용량 또는 별도로 설계한 상위 routing 정책이 바뀌기 전까지 예제는 실패를 반환합니다.

AZ 간 연속성이 필요하면 동일한 선택 release pool에 건강한 원격 endpoint를 두거나 별도 진입-layer failover 정책을 구현·검증해야 합니다. 원격 용량·데이터 일관성·인증·진행 중 요청·failback을 고려하세요. 위 zonal code는 투명하거나 순환하는 failover를 제공하지 않습니다.

### 별도 Shared-endpoint Locality 대안

다음은 적격 endpoint가 여러 AZ에 있고 release 상태가 호환되는 기존 `shared-app` Service 또는 선택 subset을 위한 **다른 구성**입니다. 위 zonal Service에 failover를 추가하는 patch가 아닙니다. 해당 shared host/subset을 관리하는 DestinationRule이 이미 있으면 경쟁하는 새 rule을 만들지 말고 trafficPolicy를 기존 rule에 병합하세요.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: shared-endpoint-locality
  namespace: zone-rollouts-demo
spec:
  host: shared-app.zone-rollouts-demo.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
```

Locality priority는 일치하는 region/zone을 우선하고 이후 트래픽을 적격한 건강한 endpoint로 전환할 수 있지만 고정된 AZ 순환 순서는 아닙니다. 현재 필드는 `consecutive5xxErrors`이며 연속 오류 감지는 트래픽으로 발생하고 `interval`은 주기적 감지 작업에 적용됩니다. 모든 endpoint를 제외하면 오류가 생길 수 있으며 이미 실패한 요청을 자동 재생하지 않습니다. [Zone-Aware Routing](../resilience/03-zone-aware-routing.md)을 참고하세요.

## 문제 해결

```bash
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo
kubectl get virtualservice test -n zone-rollouts-demo -o yaml
kubectl get services test-stable-a test-canary-a -n zone-rollouts-demo -o yaml
kubectl get pods -n zone-rollouts-demo -l app=test -o wide --show-labels
kubectl get endpointslices -n zone-rollouts-demo -l kubernetes.io/service-name=test-canary-a
kubectl get pdb -n zone-rollouts-demo -o wide

istioctl proxy-config routes <client-a-pod> -n zone-rollouts-demo
istioctl proxy-config endpoints <client-a-pod> -n zone-rollouts-demo --cluster 'outbound|8080||test-canary-a.zone-rollouts-demo.svc.cluster.local'
kubectl get analysisruns -n zone-rollouts-demo
kubectl logs -n argo-rollouts deployment/argo-rollouts
```

- **Update 충돌**: 같은 route의 관리 충돌과 공통 VirtualService의 일시적인 object-version 충돌을 구분합니다. Subset 이름만 바꾸어 해결할 수는 없습니다.
- **잘못된 Zone 선택**: 실제 caller Pod label, Node 배치와 생성된 route를 비교합니다. Node zone label이 Pod에 복사되었다고 가정하지 마세요.
- **Fallback 없음**: 선택된 Service/subset의 적격 endpoint부터 확인합니다. A 밖의 endpoint가 없다면 outlier 감지를 빠르게 해도 cross-AZ failover가 생기지 않습니다.
- **Canary 트래픽 없음**: Mesh 경유, 준비된 EndpointSlice, hash selector, 실제 weight와 충분한 표본을 확인합니다.
- **Analysis 중단/실패**: Rollout phase만 보지 말고 원본 result·provider error를 확인합니다. 사용자 정의 zone label이 기본 telemetry는 아닙니다.

## 모범 사례

### 1. 버전 변경을 명시적으로 조율

Promote는 기존 pause를 재개하며 새 image를 배포하거나 다른 AZ의 건강 상태를 증명하지 않습니다. Git에서 한 zone의 desired image를 바꾸고(격리된 lab에서는 직접 변경), Analysis·workload 상태를 관찰한 뒤 다음 zone의 진행을 판단합니다. 고정5분 대기만으로 충분한 검증이 되지는 않습니다.

```bash
# Git 변경의 격리된 lab 대안이며 Zone A에만 적용합니다.
kubectl argo rollouts set image test-a app=argoproj/rollouts-demo@sha256:e32df3d15f759d36c323b3dccb7003d38df1a4274d37217715151f085c24c58f -n zone-rollouts-demo
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo --watch
# 의도한 manual pause와 검토 후:
kubectl argo rollouts promote test-a -n zone-rollouts-demo
```

Abort는 Git의 desired image를 되돌리지 않습니다. GitOps가 zone별 managed weight·Service hash selector를 덮어쓰지 않도록 앞의 통합 가이드에 따라 조율합니다.

### 2. Continuous Analysis 대안

지속적인 감시가 필요하면 inline step 일정을 의도적으로 교체합니다. Background template의 count는 생략하고 `startingStep: 2`는 세 번째 step입니다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-continuous
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
---
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: zone-canary-continuous
        startingStep: 2
        args:
        - name: service-name
          value: test-canary-a
        - name: namespace
          value: zone-rollouts-demo
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause: {}
```

A 조각을 B/C로 바꿀 때 해당 zone의 route·Service·argument를 유지하세요. 독립 Analysis도 공통 Prometheus·network·control-plane 가용성에 의존할 수 있습니다.

### 3. 모니터링 규칙

PrometheusRule에는 Prometheus Operator와 일치하는 rule namespace/label selector가 필요합니다. Standalone Istio addon Prometheus가 이 CRD를 자동으로 읽지는 않습니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: zone-rollout-alerts
  namespace: zone-rollouts-demo
spec:
  groups:
  - name: zone-rollout
    rules:
    - alert: HighErrorRateZoneACanary
      expr: |-
        ((sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) > 0.05
        and
        (sum(increase(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) >= 20
      for: 2m
      annotations:
        summary: Zone A canary has elevated 5xx/zero-status rate with observed traffic
    - alert: UnexpectedDemoZoneRoute
      expr: |-
        sum(rate(istio_requests_total{
          reporter="source",source_workload="zone-client-a",source_workload_namespace="zone-rollouts-demo",
          destination_service_namespace="zone-rollouts-demo",destination_service_name=~"test-(stable|canary)-(b|c)"
        }[5m])) > 0
      for: 5m
      annotations:
        summary: Demo client A is using a B/C destination Service; inspect route/placement assumptions
```

첫 규칙은5xx/zero-status 실패를 확인합니다.4xx도 Analysis의2xx 비율을 낮추지만 이 오류 규칙을 발동하지는 않습니다. 트래픽 부족/누락에는 별도로 설계한 expected-traffic·telemetry-health 신호가 필요하며, 데이터가 없다고 canary가 건강하다는 뜻은 아닙니다.

두 번째는 일반적인 물리 cross-AZ 감지기가 아닌 **demo routing invariant 경고**입니다. 실제 source Deployment가 `zone-client-a`이고 A에 배치되며 B/C Service의 zone selector가 유지된다고 가정합니다. 물리 zone 측정에는 routing/observability 가이드의 검증된 node/endpoint locality 또는 명시적으로 보강한 telemetry를 사용하세요.

### 4. 복구와 용량

실제 EKS/node provisioning 방식에 맞춰 Spot 용량을 분산하고 장애를 견딜 여유를 확보합니다. Zonal affinity·중단 처리·PDB만으로 교체 용량을 보장하지 못하므로 node group lifecycle과 앱 종료·복원 절차를 확인해야 합니다.

이 설계 예제의 resource·latency 실측값은 없습니다. 실제 workload의 재조정 부하, endpoint 수, resource 사용량과 정상/실패 경로 지연을 측정하여 Istiod·proxy·Rollouts controller 용량을 정해야 합니다.

## 참고 자료와 다음 단계

- [Argo Rollouts 통합](08-argo-rollouts.md)
- [Zone-Aware Routing](../resilience/03-zone-aware-routing.md)
- [Outlier Detection](../resilience/01-outlier-detection.md)
- [DestinationRule](../traffic-management/03-destination-rule.md)
- [Istio VirtualService source selector](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio locality failover](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/)
- [Istio DestinationRule API](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Argo Rollouts Istio 통합](https://argoproj.github.io/argo-rollouts/features/traffic-management/istio/)
- [Kubernetes disruption](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [PDB 설정·반올림](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Node affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [EC2 중단 알림](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [EKS managed-node Spot 동작](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [AWS AZ ID와 계정 매핑](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
- [AWS Region·Availability Zone](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)

위의 유지보수되는 통합/routing 가이드를 lab 검증의 시작점으로 사용하세요. [Multi-cluster](02-multi-cluster.md)는 추가 trust·connectivity·failure-domain 설계가 필요하며 이 예제에서 설정 하나를 늘리는 확장이 아닙니다.
