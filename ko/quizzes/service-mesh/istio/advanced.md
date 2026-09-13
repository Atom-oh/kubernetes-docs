# Istio 고급 주제 퀴즈

> **검증 기준**: Istio 1.31.0, Kubernetes 1.32–1.36, Argo Rollouts 1.10.0
> **마지막 검토**: 2026년 9월 11일

설정, 실제 실행 동작, 검증 근거를 구분하는 퀴즈입니다. 예제는 서로 독립적이며 선택한 토폴로지와 연결된 가이드의 전제조건을 따라야 합니다. 아래 과거 계산 입력값은 현재 가격이나 새 벤치마크 결과가 아닙니다.

## 객관식 문제 (1–5번)

### 문제 1: Ambient와 Sidecar 모드

Ambient에서 workload별 proxy overhead를 줄일 수 있는 구조적 변화는 무엇인가요?

- A. Ambient는 항상 sidecar보다 많은 기능을 제공합니다.
- B. 노드별 ztunnel이 L4를 처리하고 필요한 L7 처리를 별도 waypoint에 배치합니다.
- C. 설치 속도가 반드시 열 배 빨라집니다.
- D. 설정 변경 없이 모든 정책의 보안 수준이 높아집니다.

<details>
<summary>정답 및 해설</summary>

**정답: B**

Ambient는 등록된 workload Pod마다 sidecar proxy가 있어야 하는 구조를 바꿉니다. ztunnel은 L4 보안 overlay를 제공하며 목적지의 waypoint 등록과 지원되는 L7 정책에 따라 추가 처리 경로가 결정됩니다. Waypoint는 양쪽 ztunnel이 임의로 선택하는 보편적인 공유 중간 지점이 아닙니다.

| 항목 | 올바른 비교 |
|---|---|
| CPU/메모리 | 동일한 트래픽·정책·telemetry와 실제 노드 수·waypoint replica를 기준으로 측정합니다. 보편적인 98% 절감 보장은 없습니다. |
| 등록 | Sidecar가 없는 기존 Pod는 앱 재시작 없이 ambient에 등록할 수 있습니다. 이미 있는 sidecar를 제거하려면 workload 교체가 필요합니다. |
| 기능 | 지원 범위가 다릅니다. Waypoint의 EnvoyFilter는 지원되지 않으며 ambient multicluster에는 별도 Beta 토폴로지 제약이 있습니다. |
| 성숙도 | Ambient 핵심 기능은 Istio 1.24에서 GA가 되었습니다. 이후 모든 기능이 GA라는 뜻은 아닙니다. |
| 보안 | 실제 경로와 지원되는 정책 연결 방식에 따라 mTLS·정책을 검증합니다. L7 강제가 필요하면 waypoint 우회도 방지해야 합니다. |

예를 들어 sidecar 1,000개의 사용량을 각각 50 MB/0.1 vCPU로 **가정**하면 합계는 50,000 MB/100 vCPU입니다. ztunnel 10개를 각각 50 MB/0.1 vCPU, waypoint 하나를 200 MB/0.5 vCPU로 가정하면 700 MB/1.5 vCPU이며 산술 절감률은 98.6%/98.5%입니다. 임의의 입력값이므로 실측이나 용량 보장이 아닙니다.

지원되는 ambient component를 설치하고 기존 revision/injection label을 검토한 뒤 등록합니다.

```bash
kubectl label namespace ambient-demo istio.io/dataplane-mode=ambient --overwrite
kubectl get daemonset ztunnel -n istio-system
istioctl ztunnel-config workloads --workload-namespace ambient-demo
```

Namespace가 이미 존재하고 ambient용으로 선택되어 있으며 workload가 호환되어야 합니다. 이 명령만으로 CNI/ztunnel 설치, waypoint 구성, 주입된 Pod의 안전한 migration이 이루어지지는 않습니다.

[Ambient 가이드](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

### 문제 2: Multicluster 서비스 검색

Istio sidecar multicluster에서 허용된 Kubernetes 서비스 registry를 읽고 proxy discovery 설정을 생성하는 component는 무엇인가요?

- A. Istiod
- B. CoreDNS 단독
- C. East-west gateway 단독
- D. ServiceEntry 객체 단독

<details>
<summary>정답 및 해설</summary>

**정답: A**

각 primary Istiod는 접근 권한을 가진 Kubernetes API를 읽습니다. Primary-remote에서는 remote workload가 primary control plane을 사용하며, remote 설치는 상위 “super-primary”가 관리하는 두 번째 전체 Istiod가 아닙니다. Multi-primary에서는 각 primary가 자체 control plane과 허용된 remote discovery를 가집니다.

Istiod는 proxy 설정을 생성·배포하지만 VirtualService/DestinationRule Kubernetes 객체나 앱 데이터를 모든 cluster로 복사하지 않습니다. 설정을 별도로 배포해야 합니다. 동일한 meshID만으로 공통 CA가 생기지 않으며 신뢰를 명시적으로 구성해야 합니다.

CoreDNS는 forwarding 등의 설정을 사용할 수 있지만 Istio의 cross-cluster registry는 아닙니다. Gateway는 다른 network로 트래픽을 전달하고 ServiceEntry는 외부 서비스 등을 registry에 명시적으로 등록합니다.

가상의 `data.kubeconfig`를 작성하지 말고 실제 remote secret을 생성합니다.

```bash
# Remote 설치 후 실행하며 각 context가 의도한 cluster인지 확인합니다.
istioctl create-remote-secret --context="$CTX_CLUSTER2" --name=cluster2   | kubectl --context="$CTX_CLUSTER1" apply -f -
```

이 secret은 primary가 **remote API**에 접근할 권한을 제공합니다. Credential을 보호하고 생성되는 RBAC를 검토하세요. Network를 연결하거나 정책 객체를 복제하는 기능은 아닙니다.

[Multicluster 가이드](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### 문제 3: EnvoyFilter의 목적

EnvoyFilter의 주요 목적은 무엇인가요?

- A. Kubernetes Service 생성
- B. 모든 VirtualService 자동 생성
- C. 선택한 Envoy proxy의 생성된 설정 커스터마이징
- D. 모든 Istiod 설치 설정 대체

<details>
<summary>정답 및 해설</summary>

**정답: C**

먼저 목적에 맞는 routing·telemetry·security·extension API를 사용합니다. 해당 API로 제공되지 않는 동작이 필요하고 생성된 설정을 이해하는 경우 EnvoyFilter를 고려합니다. 다음 sidecar 전용 Lua 예제는 outbound 요청의 설명용 header를 바꿉니다.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: quiz-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(handle)
                handle:headers():replace("x-quiz-example", "yes")
              end
```

Namespace와 selector가 실제 proxy와 일치해야 합니다. Selector가 없으면 일반적으로 resource namespace의 proxy에 적용되며 root namespace의 resource는 mesh 전체 범위가 될 수 있습니다. 하나의 YAML 객체에 `workloadSelector`를 두 번 작성하면 안 됩니다. Lua가 추가한 header는 인증된 identity가 아닙니다.

다른 사용 사례에도 전체 의존성이 필요합니다. Wasm에는 검증된 artifact/runtime과 mount 또는 지원되는 WasmPlugin 전달 경로가 필요합니다. Global rate limiting에는 접근 가능한 service, 일치하는 descriptor와 실패 정책이 필요합니다. Filter 이름만 삽입해서 이런 시스템이 완성되지는 않습니다. Ambient waypoint는 EnvoyFilter를 지원하지 않습니다.

업그레이드 때 정확한 Istio/Envoy 버전, 적용 범위, filter 순서, typed payload와 생성된 proxy 설정을 검증하세요. Istiod 설치값은 Helm/istioctl에서 관리합니다. In-cluster operator는 제거되었지만 IstioOperator YAML은 istioctl 입력으로 계속 사용됩니다.

[EnvoyFilter 가이드](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>

### 문제 4: Sidecar 주입

새로 생성하는 Pod의 자동 sidecar 주입을 비활성화할 수 있는 설정은 무엇인가요?

- A. Namespace label을 명시적으로 `istio-injection=disabled`로 설정
- B. Workload Pod template의 label을 `sidecar.istio.io/inject: "false"`로 설정
- C. 설정 변경 없이 Istiod 재시작
- D. A와 B 모두 가능

<details>
<summary>정답 및 해설</summary>

**정답: D**

```bash
kubectl label namespace example istio-injection=disabled --overwrite
kubectl get namespace example -L istio-injection,istio.io/rev
```

다음 조각을 기존 Deployment의 spec 아래에 병합하며 image·selector와 다른 필드를 보존합니다.

```yaml
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: 'false'
```

Namespace 또는 Pod의 비활성화 label이 우선합니다. Pod opt-in은 `istio-injection=disabled`를 덮어쓰지 못합니다. `istio-injection=enabled`만 제거한다고 항상 비활성화되는 것은 아닙니다. Revision label, Pod opt-in, injector 기본값도 확인해야 합니다. 구형 inject annotation 대신 label을 사용하며 서로 모순되는 설정을 피하세요.

변경은 새 Pod에 적용되며 이미 주입된 proxy를 제거하지 않습니다. 기존 Pod 변경은 workload의 검토된 rollout 절차를 따릅니다. Namespace는 주입을 활성화하고 일부 template만 제외할 수 있지만 해당 workload의 mesh·보안 참여도 달라집니다.

```bash
kubectl get pod "$POD" -n "$NAMESPACE" -o json   | jq '{containers: [.spec.containers[].name],
         initContainers: [.spec.initContainers[]? | {name, restartPolicy}]}'
```

Native sidecar는 initContainers에 `restartPolicy: Always`로 나타날 수 있습니다. 일반 containers만 검사하거나 항상 Ready `2/2`를 기대하면 안 됩니다. Ambient 등록은 별도 메커니즘입니다.

[주입 가이드](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

### 문제 5: Argo Rollouts 트래픽 분할

Argo Rollouts가 변경하는 HTTP route weight를 담는 Istio의 **선언적 resource**는 무엇인가요?

- A. Rollouts controller process
- B. VirtualService
- C. Kubernetes Service 단독
- D. Gateway 단독

<details>
<summary>정답 및 해설</summary>

**정답: B**

Rollouts가 이름으로 지정한 route weight를 바꾸고 Istiod가 설정을 변환하며 **Envoy가 실제 routing을 실행**합니다. VirtualService는 packet을 처리하는 process가 아닙니다. 10%는 확률적인 weight이며 요청 100개마다 정확히 10개가 canary로 간다는 보장이 아닙니다. Retry·장기 연결도 관측값에 영향을 줍니다.

Subset 방식에는 앱을 선택하는 Service 하나, 두 subset, revision label에 대한 Rollouts ownership이 필요합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  host: test
  subsets:
  - name: stable
    labels:
      app: test
  - name: canary
    labels:
      app: test
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  hosts:
  - test
  - test.rollouts-demo.svc.cluster.local
  http:
  - name: primary
    route:
    - destination:
        host: test
        port:
          number: 8080
        subset: stable
      weight: 100
    - destination:
        host: test
        port:
          number: 8080
        subset: canary
      weight: 0
    retries:
      attempts: 0
```

다음 strategy 조각은 가이드의 완전한 matching Rollout에 병합합니다. 불완전한 resource로 적용하거나 다른 host-level 분할 방식과 혼합하지 마세요.

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: test-subsets
            routes:
            - primary
          destinationRule:
            name: test-subsets
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
      - setWeight: 10
      - pause: {}
```

`test` Service, 전체 Rollout selector/template, controller/RBAC와 `rollouts-demo` namespace가 있어야 합니다. Rollouts가 subset revision label을 갱신합니다. `retries.attempts: 0`은 이 route의 mesh retry를 막으며 앱 자체 retry는 별도로 관리합니다.

분석은 설정한 경우에만 실행됩니다. 분석 실패로 rollout을 중단할 수 있지만 앱/DB 부작용을 되돌리지는 않습니다. 가이드의 완전한 host-level 또는 subset 예제를 하나씩 선택하세요.

[Argo Rollouts 가이드](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

## 주관식 문제 (6–10번)

### 문제 6: Ambient 리소스·비용 분석

원래 가정값인 Pod 500개, r5.xlarge 노드 5개, 월 730시간과 노드당 시간당 $0.252를 사용해 proxy resource를 계산하고 청구 비용 절감 여부를 설명하세요. Sidecar는 각각 50 MB/0.1 vCPU, ztunnel은 각각 50 MB/0.1 vCPU, waypoint는 200 MB/0.5 vCPU로 가정합니다.

<details>
<summary>예시 답안</summary>

가격과 resource 수치는 **연습문제 입력값**이며 현재 AWS 견적이나 Istio 실측이 아닙니다. 아래 MB/GB 계산은 십진 단위입니다.

| Resource | Sidecar | 가정한 노드 5개의 ambient | 산술 감소량 |
|---|---|---|---|
| 메모리 |500 × 50 = 25,000 MB|5 × 50 + 200 = 450 MB|24,550 MB, 98.2%|
| CPU |500 × 0.1 = 50 vCPU|5 × 0.1 + 0.5 = 1 vCPU|49 vCPU, 98%|

r5.xlarge는 vCPU 4개와 메모리 32 GiB를 제공합니다. 노드 5개는 system/app 용량을 제외하기 전에도 20 vCPU뿐이므로 sidecar 50 vCPU 가정부터 이 고정 노드 구성에서 불가능합니다. Proxy CPU만의 하한은 ceil(50/4) = 13개 노드이며 앱 CPU, system 예약, 메모리, IP 제한, placement와 복원력 요구사항을 제외한 값입니다.

이 13개 하한을 “ambient 노드 하나”와 비교하면서 ztunnel은 계속 노드 5개분으로 계산하면 안 됩니다. **실제로 유지할 노드 수**에 맞춰 ztunnel 용량을 다시 계산하고 waypoint HA/트래픽 용량과 다른 workload도 포함해야 합니다.

가정 가격에서:

- 노드 한 개의 한 달 비용은 `0.252 × 730 = $183.96`입니다.
- 동일한 노드 5개를 유지하면 두 모드 모두 `$919.80/월`입니다. Proxy 여유 용량만 늘었다고 청구액이 줄지는 않습니다.
- 노드 13개의 한 달 비용은 `$2,391.48`로 기존 산술 오류를 바로잡습니다. 필요한 운영 fleet이 13개라는 검증은 아닙니다.
- 검증된 fleet이 Nₛ개와 Nₐ개라면 다른 비용·약정을 제외한 compute 차이는 `(Nₛ − Nₐ) × $183.96/월`입니다.

전체 비교에는 EKS/control-plane, load balancer, AZ/Region 전송, storage, telemetry와 실제 구매 약정을 포함하세요. Sidecar도 local 통신을 사용하며 ambient가 network 비용이나 OOM을 자동 제거하지 않습니다.

연습문제의 migration effort $6,000에 대한 회수 기간은 실측 순절감액 S가 양수일 때만 `6000 / S`개월입니다. 청구 용량이 같으면 S가 0일 수 있어 유한한 회수 기간이 나오지 않습니다. Proxy 산술만으로 기존의 92% 비용 절감이나 2.7개월 ROI를 주장할 수 없습니다.

[Ambient 가이드](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>


### 문제 7: Primary-Remote EKS Mesh

us-east-1과 us-west-2에 있는 기존 EKS cluster 두 개의 primary-remote 설계를 설명하세요. Discovery, trust, network 전제조건과 cross-cluster 검증 예시를 포함하세요.

<details>
<summary>예시 답안</summary>

이는 **sidecar** 설계입니다. 현재 ambient multicluster Beta는 multi-primary/multi-network를 지원하며 이 primary-remote 모델과 다릅니다. Primary Istiod가 remote proxy를 관리하며 더 높은 primary에게 설정을 받는 별도 전체 remote Istiod는 없습니다.

설치 전에 검토된 공통 trust, API 접근, DNS, security group/firewall과 L4 control/data 경로를 마련합니다. 서로 다른 network ID는 network를 식별할 뿐 연결을 생성하지 않습니다. 여러 network에서는 양쪽에 remote endpoint로 갈 적절한 east-west gateway가 필요합니다. Region 간 비용·장애 복구는 별도 책임입니다.

Primary의 핵심 istioctl 입력은 다음과 같습니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      externalIstiod: true
      multiCluster:
        clusterName: cluster1
      network: network1
```

Remote 설정의 **198.51.100.10은 문서용 placeholder**이며 실제 EKS endpoint가 아닙니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: remote
  values:
    istiodRemote:
      injectionPath: /inject/cluster/cluster2/net/network2
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
      remotePilotAddress: 198.51.100.10
```

Remote namespace에는 관리하는 primary도 지정합니다.

```bash
kubectl --context="$CTX_CLUSTER2" annotate namespace istio-system   topology.istio.io/controlPlaneClusters=cluster1 --overwrite
```

유지보수되는 가이드에 따라 trust를 준비하고 같은 Istio release에서 gateway를 생성하며 primary discovery/injection을 노출합니다. Remote profile 설치 후 문제 2의 remote-access secret을 생성합니다. 이 두 network 예제의 remote injection path는 `net/network2`로 끝납니다.

EKS NLB는 일반적으로 DNS 이름을 제공합니다. 해당 release는 DNS-valued remotePilotAddress를 표현할 수 있지만 chart render만으로 discovery/injection 연결과 certificate 이름이 검증되지는 않습니다. 공식 external-control-plane의 DNS/certificate/injection-URL 설계를 완성해야 하며 누락된 LB IP를 임의 주소로 대체하면 안 됩니다.

검증에는 같은 Istio 배포본의 `helloworld`와 `curl` sample을 사용합니다. 양쪽 cluster에 같은 namespace/Service identity를 만들고 문서화된 version별 workload를 배포합니다. Local endpoint가 없는 Service도 로컬 Kubernetes DNS를 제공할 수 있으며 Istio는 remote endpoint를 검색할 수 있습니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: helloworld
  namespace: sample
spec:
  selector:
    app: helloworld
  ports:
  - name: http
    port: 5000
    targetPort: 5000
```

이 Service만으로 앱이 배포되지는 않습니다. Sample backend는 실제로 5000 port를 사용합니다. ContainerPort를 8080으로 선언한다고 기본 nginx process의 listen port가 바뀌지 않습니다. 전체 sample 배포 후 확인한 curl Pod/container를 선택하고 설정과 응답을 모두 확인합니다.

```bash
kubectl --context="$CTX_CLUSTER1" get service,endpointslice -n sample
kubectl --context="$CTX_CLUSTER2" get service,endpointslice -n sample
istioctl --context="$CTX_CLUSTER1" proxy-status
istioctl --context="$CTX_CLUSTER1" proxy-config endpoints "$CURL_POD" -n sample   --cluster 'outbound|5000||helloworld.sample.svc.cluster.local'
kubectl --context="$CTX_CLUSTER1" exec -n sample "$CURL_POD" -c curl --   curl --fail --max-time 5 http://helloworld.sample.svc.cluster.local:5000/hello
```

다른 network의 경우 client는 remote Pod IP 대신 east-west gateway endpoint를 볼 수 있습니다. 응답 하나는 해당 호출만 입증합니다. 양방향, endpoint version, trust, policy와 실패 시나리오를 확인하세요.

**동일한 host/subset/port**를 가진 destination 두 개의 weight가 local 80%/remote 20%를 뜻하지 않습니다. 선택 가능한 endpoint에 대해 지원되는 locality 또는 명시적 destination 모델을 설계하세요. Cross-cluster 관측은 reporter 하나와 실제 source_cluster/destination_cluster label을 사용합니다.

[Multicluster 가이드](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### 문제 8: 공유 사용자별 Rate Limiting

`/api/premium/*`에 사용자별 분당 100개 요청의 공유 quota를 구현하고 identity, descriptor, 실패 동작을 설명하세요.

<details>
<summary>예시 답안</summary>

요청 경로는 **인증된 진입점 → 전용 Envoy gateway → 공유 rate-limit service/Redis 판단 → backend 또는 거부**입니다. Local proxy bucket은 gateway replica 사이에 공유되는 quota가 아닙니다.

다음 예제에는 전제조건이 있습니다.

- `istio-system`의 전용 gateway에 실제 `app: premium-gateway` label이 있고 TLS/route 설정과 backend Service가 준비되어야 합니다.
- 신뢰하는 인증 계층이 client가 보낸 x-user-id를 제거하고 비어 있지 않은 정규화된 사용자 identity 하나를 넣습니다. 이 인증 경로만 gateway/backend에 접근할 수 있어야 합니다. Caller가 임의로 쓴 header는 사용자 인증이 아닙니다.
- 아래의 격리된 lab Redis endpoint가 이미 있어야 합니다. 운영 Redis 인증/TLS, persistence, HA, failover와 연결 설정은 별도로 설계해야 하며 replica 수만으로 완성되지 않습니다.

Descriptor는 `(header_match=premium, user_id=<신뢰한 사용자>)`라는 **두 entry의 순서**입니다. Server config는 premium 아래에 dynamic user entry를 중첩해야 합니다. 최상위 user_id 하나만 선언한 descriptor는 일치하지 않습니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: premium-ratelimit
    descriptors:
    - key: header_match
      value: premium
      descriptors:
      - key: user_id
        rate_limit:
          unit: minute
          requests_per_unit: 100
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: ratelimit
        image: docker.io/envoyproxy/ratelimit:8fe6ea42@sha256:a61547259607d40aff153050c2a87873ca1676d1d9f5f06937d412000dcc2df1
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: grpc
        env:
        - name: LOG_LEVEL
          value: info
        - name: CONFIG_TYPE
          value: FILE
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: ratelimit
        - name: RUNTIME_APPDIRECTORY
          value: config
        - name: RUNTIME_WATCH_ROOT
          value: 'false'
        - name: RUNTIME_IGNOREDOTFILES
          value: 'true'
        - name: USE_STATSD
          value: 'false'
        - name: REDIS_SOCKET_TYPE
          value: tcp
        - name: REDIS_URL
          value: redis-ratelimit.istio-system.svc.cluster.local:6379
        - name: HOST
          value: '::'
        - name: GRPC_HOST
          value: '::'
        - name: HEALTHY_WITH_AT_LEAST_ONE_CONFIG_LOADED
          value: 'true'
        volumeMounts:
        - name: config-volume
          mountPath: /data/ratelimit/config
          readOnly: true
        command:
        - /bin/ratelimit
        resources:
          requests:
            memory: 128Mi
            cpu: 100m
          limits:
            memory: 512Mi
            cpu: 500m
        readinessProbe:
          httpGet:
            path: /healthcheck
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
---
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8080
    name: http
    targetPort: 8080
  - port: 8081
    name: grpc
    targetPort: 8081
  selector:
    app: ratelimit
```

Image는 검증한 upstream commit 8fe6ea42와 digest로 고정하며 움직이는 master tag가 아닙니다. gRPC는 **8081**, HTTP health는 **8080** port입니다. Workload와 맞는 injector와 실제 mesh/network 접근이 필요합니다. 보호된 Redis credential은 적절한 Secret/mount로 설정하세요. 새 config가 실제 로드되었는지 확인하며 이 file-mode 예제가 hot reload를 증명하지는 않습니다.

기존 service discovery/TLS 정책이 적용되도록 Istio가 생성한 gRPC cluster를 사용합니다.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: premium-ratelimit
          failure_mode_deny: true
          timeout: 0.1s
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: outbound|8081||ratelimit.istio-system.svc.cluster.local
                authority: ratelimit.istio-system.svc.cluster.local
            transport_api_version: V3
---
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: premium-ratelimit-actions
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: VIRTUAL_HOST
    match:
      context: GATEWAY
    patch:
      operation: MERGE
      value:
        rate_limits:
        - actions:
          - header_value_match:
              descriptor_value: premium
              headers:
              - name: :path
                string_match:
                  prefix: /api/premium/
          - request_headers:
              header_name: x-user-id
              descriptor_key: user_id
              skip_if_absent: false
```

Action은 전용 gateway에 한정합니다. 공유 gateway라면 실제 생성된 vhost로 범위를 좁혀야 합니다. Prefix 밖에서는 premium descriptor가 생성되지 않습니다. Encoded path와 별도 backend 접근까지 포함해 route/path normalization과 인증 정책을 일치시키세요.

Premium 경로의 identity가 없거나 비어 있을 때 descriptor 생성 누락으로 우회하지 못하도록 거부합니다.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: premium-requires-identity
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: premium-gateway
  action: DENY
  rules:
  - to:
    - operation:
        paths:
        - /api/premium/*
    when:
    - key: request.headers[x-user-id]
      notValues:
      - '*'
```

이 DENY 정책은 누락 header 방어일 뿐 제공된 값의 인증이 아닙니다. 필수 trusted-entry/우회 방지, 기존 ALLOW 정책, TLS, 앱 인가를 대체하지 않습니다.

`failure_mode_deny: true`에서 rate-limit service 오류는 일반적으로 HTTP 500이며 over-limit 판단은 429입니다. 100 ms RPC budget은 Redis·network latency에 맞춰 검증할 예시입니다. Header나 counter 하나만으로 quota 강제가 입증되지는 않습니다.

| 검증 사례 | 확인할 동작 |
|---|---|
| 같은 인증 사용자로 gateway replica 두 개 사용 | 하나의 공유 descriptor/window budget |
| 다른 사용자 | 별도의 user descriptor |
| 누락·위조 identity | Guard/인증 경계에서 거부되며 무료 quota 우회가 아님 |
| Premium prefix 밖 경로 | Premium descriptor 없음; 다른 보안·rate 정책은 계속 적용 |
| Redis/RLS 접근 불가 | 의도한 fail-closed와 실제 status/latency |
| Window 경계·Redis 재시작 | Counter/window 동작 측정; 나눠 실행한 시험에서 항상 101번째가 거부된다고 단정하지 않음 |

허용된 read-only endpoint에 bounded 요청을 보내며 새 test identity/window를 사용합니다. 50회 다음 150회를 실행한다고 두 번 모두 새 budget이 시작되지 않습니다. Rate-limit 응답 header에는 지원되는 service 응답과 filter 설정이 필요하므로 remaining/reset 값을 만들어 쓰지 마세요.

RLS health, 로드된 config와 실제 Envoy stat을 확인합니다. HTTP stat prefix 아래의 `ratelimit.ok`, `ratelimit.over_limit`, `ratelimit.error` 등이 해당합니다. 실제 Prometheus 이름/label을 확인하며 `rejected_total`을 추측하지 마세요. 큰 운영 keyspace에 Redis `KEYS *`를 실행하거나 내부 counter를 남은 quota로 해석하면 안 됩니다. 고정한 distroless RLS image는 redis-cli shell이 아닙니다.

[Rate-limiting 가이드](../../../service-mesh/istio/resilience/02-rate-limiting.md) · [EnvoyFilter 가이드](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>


### 문제 9: 분석을 포함한 Blue/Green

Preview와 승격 후 분석을 포함한 Blue/Green Rollout을 구성하세요. 지표 누락을 성공으로 처리하지 않으면서 트래픽 전환과 실패 동작을 설명하세요.

<details>
<summary>예시 답안</summary>

이는 문제 5의 canary와 **대안 관계**인 strategy입니다. Argo Rollouts 1.10 controller/CRD, Istio가 주입된 demo workload·caller, 해당 source-reporter metric을 수집하는 Prometheus와 검증된 demo image를 위한 Linux amd64 용량을 가정합니다. Lab 예제이며 검증된 운영 배포가 아닙니다.

기존 `rollouts-demo` namespace에 Service와 전체 Rollout을 만듭니다. Rollouts가 Service revision-hash selector를 관리하므로 GitOps가 이 동적 필드를 덮어쓰지 않도록 해야 합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-active
  namespace: rollouts-demo
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
  name: test-preview
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test
  namespace: rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
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
  strategy:
    blueGreen:
      activeService: test-active
      previewService: test-preview
      autoPromotionEnabled: true
      prePromotionAnalysis:
        templates:
        - templateName: preview-analysis
        args:
        - name: service-name
          value: test-preview
        - name: namespace
          value: rollouts-demo
      postPromotionAnalysis:
        templates:
        - templateName: active-analysis
        args:
        - name: service-name
          value: test-active
        - name: namespace
          value: rollouts-demo
      scaleDownDelaySeconds: 600
```

초기 image는 검증한 blue demo digest이며 가이드에 update용 green digest도 있습니다. 새 revision이 생기면 preview가 candidate를 가리킵니다. 사전 분석 성공 후 `autoPromotionEnabled: true`는 자동 승격을 허용합니다. 명시적 수동 승격이 필요하면 false를 선택하며 이는 별도의 정책입니다.

여기서는 meshed client가 내부 Service로 접근합니다. 운영 edge 노출에는 실제 Gateway, TLS, 일치하는 host binding과 인가가 필요합니다. 두 번째 VirtualService hostname을 만드는 것만으로 Gateway에 추가되거나 preview 접근이 보호되지는 않습니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-bluegreen
  namespace: rollouts-demo
spec:
  hosts:
  - test-active
  - test-active.rollouts-demo.svc.cluster.local
  http:
  - name: active
    route:
    - destination:
        host: test-active
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-preview-route
  namespace: rollouts-demo
spec:
  hosts:
  - test-preview
  - test-preview.rollouts-demo.svc.cluster.local
  http:
  - name: preview
    route:
    - destination:
        host: test-preview
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
```

두 route 모두 mesh retry를 명시적으로 비활성화합니다. 승격 시 preview Service가 자동으로 구 stable version과 맞교환되지는 않습니다. Active Service selector가 새 revision으로 바뀌고 구 ReplicaSet은 이후 **scale down**되며 반드시 삭제되는 것은 아닙니다. 기존 연결이나 앱/DB 부작용은 selector 변경으로 되돌아가지 않습니다.

Preview 분석 전과 분석 중에 preview Service를 통과하는 대표적인 허용 트래픽을 생성해야 합니다. Prometheus query는 트래픽을 만들지 않습니다. 예제는 2분 window의 추정 요청 수 20 이상, 유한한 2xx 성공률 95% 이상, p95 0.5초 이하, 5xx/zero-status 오류율 1% 이하를 요구합니다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: preview-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
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
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: active-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
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
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
```

두 template은 같은 gate 정의를 서로 다른 Service 인수로 사용합니다. `initialDelay: 5m`은 2분 window가 전환 이전 구간에서 벗어날 여유를 주지만 source freshness와 실제 트래픽은 여전히 확인해야 합니다. 구 active-version sample을 candidate 근거로 읽으면 안 됩니다.

Prometheus 결과는 vector이므로 길이와 유한한 값인지 확인한 뒤 `result[0]`을 사용합니다. 분자의 `or vector(0)`은 2xx가 없는 전체 5xx와 5xx가 없는 정상 사례를 처리합니다. 분모와 volume 검사가 누락·idle telemetry의 통과를 막습니다. 성공률은 2xx만 포함하므로 4xx는 성공률을 낮추지만 5xx/zero-status 오류 분자에는 포함되지 않습니다.

`failureLimit: 0`은 첫 실패 측정에서 중단합니다. 2이면 세 번째 실패가 한도를 초과합니다. 실패를 허용한 sample 5개가 모두 성공해야 한다는 뜻은 아닙니다. Initial delay와 provider 오류 등을 포함하면 30초 간격 5회가 정확히 2.5분의 wall-clock phase라고 보장할 수도 없습니다.

승격 전 실패는 기존 active 대상을 유지합니다. 승격 후 실패는 controller 규칙에 따라 이전 ReplicaSet이 사용 가능한 동안 중단하고 이전 active 선택을 복구합니다. 모든 요청이 즉시 복구되는 보장은 아닙니다. 구 version 용량을 충분히 유지하고 전파, session, drain과 DB 호환성을 확인하세요.

```bash
kubectl argo rollouts get rollout test -n rollouts-demo --watch
kubectl get analysisrun -n rollouts-demo
kubectl get service test-active test-preview -n rollouts-demo -o yaml
```

복사한 status 출력이나 존재하지 않는 metric 대신 실제 AnalysisRun condition과 revision tree를 확인합니다. Scale-down, endpoint 전파와 앱 복구는 해당 환경에서 검증해야 합니다.

[Argo Rollouts 가이드](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

### 문제 10: DNS 동작과 성능 측정

Istio DNS capture와 Envoy upstream DNS resolution을 구분하고 유효한 설정과 재현 가능한 성능 비교를 제시하세요. 기존 미검증 benchmark 수치를 새 측정값으로 제시하지 않고 평가하세요.

<details>
<summary>예시 답안</summary>

앱 DNS, Istio DNS capture, CoreDNS/cache 동작과 Envoy upstream resolution은 서로 다릅니다. 새 HTTP 요청이 매번 새 DNS query나 connection을 필요로 하지는 않습니다. DNS capture는 임의의 upstream 응답을 모두 cache하는 기능이 아닙니다.

Sidecar에서는 istio-agent가 capture된 DNS 요청을 처리합니다. Ambient에는 별도로 문서화된 DNS 경로가 있고 Istio 1.25부터 capture가 기본 활성화됩니다. 알려진 mesh 이름은 name table에서 응답하고 모르는 이름은 forwarding할 수 있습니다. Envoy는 DNS 기반 upstream endpoint를 독립적으로 해석합니다.

앱이 HTTPS를 시작하는 외부 서비스를 유효한 ServiceEntry로 등록합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.github.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

이 설정은 TLS를 한 겹 더 시작하거나 egress firewall을 생성하지 않으며 암호화된 HTTP path를 sidecar가 읽게 하지도 않습니다. 적절한 network policy와 앱 TLS 검증은 계속 필요합니다.

Sidecar capture에는 다음 istioctl 입력을 기존 설치값에 병합하고 영향받는 workload를 정상 변경 절차로 rollout합니다.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: 'true'
```

DestinationRule에 `trafficPolicy.dnsRefreshRate`는 **없으며** `consecutiveErrors`도 현재 outlier 필드가 아닙니다. Istio 1.31이 생성하는 DNS cluster는 DNS TTL을 존중하며 관련 fallback에 사용하는 mesh `dnsRefreshRate` 기본값은 60초입니다. 5분을 설정한다고 모든 양수 TTL을 무시하고 고정 주기로 조회하지는 않습니다.

가상의 `envoy.filters.network.dns_cache` filter/type을 삽입하면 안 됩니다. Dynamic forward proxy와 현재 DYNAMIC_DNS ServiceEntry mode는 각각 요구사항이 있는 별도 설계이며 일반 cache toggle이 아닙니다. 필요한 경우 DNS 가이드의 명시적 범위·버전 검증을 거친 cluster customization을 참고하세요.

Bounded 시험에는 curl이 실제 들어 있는 caller와 DNS/TTL을 제어할 수 있는 **소유하거나 허가받은** HTTPS endpoint를 사용하고 BENCH_URL을 명시합니다. 이는 process 관점 timing이며 Envoy의 DNS latency만 측정하지 않습니다.

```bash
: "${BENCH_URL:?Set an authorized HTTPS benchmark endpoint}"
for i in $(seq 1 20); do
  curl --silent --show-error --fail --max-time 5 --output /dev/null     --write-out '%{http_code},%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}
'     "$BENCH_URL" || break
  sleep 0.2
done
```

Client/image, Istio/Kubernetes 버전, proxy mode, TTL/응답 변경, DNS 경로, connection reuse, concurrency, payload, TLS와 warm/cold 절차를 기록합니다. 매번 새 curl process를 만들면 process-local 상태가 초기화되므로 connection reuse를 별도로 통제해야 합니다. 공개 GitHub API에 부하를 주거나 curl image에 ApacheBench도 있다고 가정하지 마세요. 통계 계산 전에 실패 sample도 명시적으로 처리해야 합니다.

기존 한국어 문서에는 EKS 1.34, Istio 1.28.0, r5.xlarge/us-east-1과 api.github.com이 적혀 있었지만 raw sample이나 재현 가능한 artifact가 없었습니다. 이 **과거 맥락**을 보존하며 Istio 1.31 결과로 이름만 바꾸지 않습니다.

| 원래 미검증 수치 | Before | After | 산술만 검산 |
|---|---:|---:|---:|
| 평균 응답 시간 |287 ms|152 ms|47.04% 감소|
| p95 |350 ms|180 ms|48.57% 감소|
| p99 |420 ms|210 ms|50% 감소|
| 처리량 |12.34 RPS|23.15 RPS|87.60% 증가|
| 주장한 cache hit rate |0%|99%|유효한 hit/miss 근거 없음|
| 주장한 connection reuse |0%|95%|유효한 재사용 측정 없음|

전체 응답 시간 차이를 모두 DNS 때문이라고 해석할 수 없습니다. Concurrency 10일 때 ApacheBench의 mean time per request는 약 `1000 × 10 / RPS` ms이고 “across all concurrent requests”는 `1000 / RPS` ms입니다. 기존 label이 반대로 적혀 있었습니다. 이를 고친다고 benchmark가 인증되는 것은 아닙니다.

실제로 export했다면 `istio_agent_dns_requests_total`, `istio_agent_dns_upstream_requests_total`, `istio_agent_dns_upstream_failures_total`과 upstream duration histogram 등을 관측할 수 있습니다. Upstream success/(success+failure)는 query 성공률이며 cache hit rate가 아닙니다. `envoy_cluster_upstream_cx_active`는 gauge이므로 rate()로 connection reuse를 측정할 수 없습니다.

생성된 cluster DNS 설정, 검증된 export counter와 실제 resolver/connection trace를 확인합니다. 평균 latency뿐 아니라 DNS 변경과 실패 복구를 시험하세요. Workload 근거 없이 5–15분 refresh나 고정 성능 향상률을 권장하면 안 됩니다.

[DNS 가이드](../../../service-mesh/istio/advanced/04-dns-cache.md)

</details>

## 점수 계산

- 객관식 1–5번은 각 10점으로 총 50점입니다. 정답은 **B, A, C, D, B**입니다.
- 주관식 6–10번은 각 10점으로 총 50점입니다. 정확한 동작, 전체 전제조건, 유효한 설정, 의미 있는 검증과 측정 한계 설명을 평가합니다.
- 총점은 100점입니다. 퀴즈 점수는 문항 이해도를 나타내며 운영 전문성 인증이 아닙니다.

## 학습 자료

- [Ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [Multicluster](../../../service-mesh/istio/advanced/02-multi-cluster.md)
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
- [DNS](../../../service-mesh/istio/advanced/04-dns-cache.md)
- [gRPC](../../../service-mesh/istio/advanced/05-grpc.md)
- [WebSocket](../../../service-mesh/istio/advanced/06-websocket.md)
- [주입](../../../service-mesh/istio/advanced/07-sidecar-injection.md)
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
- [KEDA](../../../service-mesh/istio/advanced/10-keda-autoscaling.md)
