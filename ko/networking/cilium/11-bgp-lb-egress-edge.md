# Part 11: BGP Control Plane, Load Balancer IP, Egress

> **검토 기준**: Cilium 1.20.2 (안정, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. **[1.21 pre-release]** 표시 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다.
> **마지막 업데이트**: 2026년 10월 15일

이 챕터는 Cilium 클러스터를 Pod 네트워크 **바깥**과 연결하는 모든 요소를 다룹니다. BGP Control Plane으로 경로 광고하기, LoadBalancer IP 할당과 공지(LB IPAM, L2 announcements, Node IPAM), 아웃바운드 트래픽 제어(Egress Gateway), 노드 로컬 백엔드로의 트래픽 가로채기(Local Redirect Policy), 가까운 백엔드 우선 선택(traffic distribution), L7 진입점(Ingress, Gateway API)입니다. 마지막에는 온프레미스 ToR + BGP와 EKS + CloudFront 두 가지 참조 토폴로지를 정리합니다.

관련 챕터: [IPAM 심화](10-ipam-deep-dive.md) (BGP가 무엇을 광고할 수 있는지 결정하는 Pod IPAM), [오버레이와 네이티브 라우팅](09-overlay-native-routing.md), [eBPF 데이터패스 내부](08-ebpf-datapath-internals.md) (아래 Service 로드밸런싱이 의존하는 kube-proxy replacement), [ClusterMesh와 업그레이드](13-clustermesh-install-upgrade.md).

## 1. North-South에서 Cilium의 위치

"로드밸런서"라는 말 안에는 서로 다른 세 가지 일이 섞여 있습니다.

| 역할 | 답하는 질문 | Cilium 구성요소 |
|---|---|---|
| 주소 할당 | 이 Service는 어떤 IP를 받는가? | LB IPAM(`CiliumLoadBalancerIPPool`), Node IPAM, 클라우드 컨트롤러 |
| 도달성 | 외부 네트워크가 이 IP가 어느 노드에 있는지 어떻게 아는가? | BGP Control Plane, L2 announcements, 클라우드 LB |
| 로드밸런싱 | 패킷이 노드에 도착한 뒤 어느 백엔드 Pod가 받는가? | eBPF Service 로드밸런싱(kube-proxy replacement), L7은 Envoy |

따라서 BGP Control Plane, L2 announcements, LB IPAM은 **서로 독립된** 기능이며 조합해서 씁니다. 온프레미스의 전형적 조합은 `LB IPAM`(VIP 할당) + `BGP Control Plane`(광고) + eBPF kube-proxy replacement(분산)입니다. 어느 기능이 Service를 맡을지는 `loadBalancerClass`가 결정합니다(6절).

**BGP가 하지 않는 일.** BGP Control Plane은 경로를 *광고*만 합니다. 로컬 데이터패스를 프로그래밍하지 않으며, 피어에게서 받은 경로는 커널이나 eBPF 맵에 설치되지 않습니다. 클러스터 내부 도달성을 만들 수 없습니다([upstream 개요](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)). 노드 간 Pod 라우팅은 오버레이/네이티브 라우팅의 몫입니다([Part 9](09-overlay-native-routing.md)).

## 2. BGP Control Plane v2

**성숙도**: 1.19, 1.20, 1.21-pre에서 BGP Control Plane은 v2(`cilium.io/v2` CRD)뿐입니다. v1 `CiliumBGPPeeringPolicy`는 1.19에서 제거되었습니다(2.9절).

### 2.1 아키텍처

```
                  사용자 작성 (cluster-scoped, cilium.io/v2)
   +--------------------+   +-------------------+   +----------------------+
   | CiliumBGPCluster   |-->| CiliumBGPPeer     |   | CiliumBGPAdvertise-  |
   | Config             |   | Config            |<--| ment (PeerConfig가   |
   |  nodeSelector      |   |  timers, GR, MD5, |   |  LABEL로 선택)       |
   |  bgpInstances[]    |   |  families[]       |   +----------------------+
   |  peers[] -> ref    |   +-------------------+
   +---------+----------+
             | cilium-operator가 watch
             v
   +--------------------+   (선택된 노드마다 1개, 이름 == 노드 이름,
   | CiliumBGPNodeConfig|    사용자에게는 read-only, status에 세션 상태)
   +---------+----------+   +--------------------------+
             | 해당 노드의   | CiliumBGPNodeConfig-     |  선택적 노드별
             | agent가 watch | Override (이름 == 노드)  |  routerID/ASN/소스
             v              +--------------------------+
   +--------------------------------------------+
   | cilium-agent: BGP "router manager"         |
   |   bgpInstance마다 내장 GoBGP 인스턴스 1개   |
   |   입력: NodeConfig, PeerConfig, Advert.,   |
   |   Secret, Service/EndpointSlice/backend,   |
   |   CiliumNode PodCIDR / CiliumPodIPPool     |
   +----------------------+---------------------+
                          | TCP/179 (agent가 먼저 연결, 기본은 active-only)
                          v
                    ToR / 상위 라우터
```

제어 흐름([`pkg/bgp/README.md`](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/README.md)): operator는 `CiliumBGPClusterConfig`와 이 설정이 참조하는 `CiliumBGPPeerConfig`/`CiliumBGPAdvertisement`를 watch하면서, `nodeSelector`에 맞는 노드마다 `CiliumBGPNodeConfig`를 하나씩 생성/갱신/삭제합니다. 각 agent는 자기 노드의 `CiliumBGPNodeConfig`와 peer/advertisement 설정, Secret, Service, (multi-pool이면) `CiliumPodIPPool`만 보고 GoBGP 인스턴스를 reconcile합니다. 따라서 설정 변경이 전파되려면 operator가 떠 있어야 합니다.

스피커는 agent에 내장된 GoBGP이며 유일하게 지원되는 라우터 구현입니다. 내장 라이브러리는 `gobgp/v3`(1.19)에서 `gobgp/v4`(1.20.2, 1.21.0-pre.3; 각 태그의 `go.mod`)로 바뀌었습니다. IPv4/IPv6, 싱글/듀얼 스택을 지원하지만 agent가 실제로 운영 중인 주소 패밀리만 광고할 수 있습니다.

### 2.2 활성화

```yaml
bgpControlPlane:
  enabled: true              # 기본 false
  statusReport:
    enabled: true            # 기본 true; 아주 큰 클러스터에서는 API 부하 절감을 위해 끔
  routerIDAllocation:
    mode: default            # default | ip-pool
```

```bash
helm upgrade cilium cilium/cilium -n kube-system --reuse-values \
  --set bgpControlPlane.enabled=true
kubectl -n kube-system rollout restart ds/cilium deploy/cilium-operator
```

| Helm 값 | agent/operator 플래그 | 기본값 | 의미 |
|---|---|---|---|
| `bgpControlPlane.enabled` | `--enable-bgp-control-plane` | `false` | 기능 활성화 |
| `bgpControlPlane.secretsNamespace.name` / `.create` | `--bgp-secrets-namespace` | `kube-system` / `false` | `authSecretRef` Secret을 읽는 네임스페이스. 차트가 생성 가능 |
| `bgpControlPlane.statusReport.enabled` | `--enable-bgp-control-plane-status-report` | `true` | 세션 상태를 `CiliumBGPNodeConfig.status`에 기록. 끄면 status가 지워짐 |
| `bgpControlPlane.routerIDAllocation.mode` / `.ipPool` | `--bgp-router-id-allocation-mode` / `-ip-pool` | `default` / 빈 값 | Router ID 전략(2.7절) |
| `bgpControlPlane.legacyOriginAttribute.enabled` | `--enable-bgp-legacy-origin-attribute` | `false` | `LoadBalancerIP` 경로의 ORIGIN을 `IGP` 대신 `INCOMPLETE`(MetalLB 호환)로 설정 |
| `enableNoServiceEndpointsRoutable` | `--enable-no-service-endpoints-routable` | `true` | 백엔드가 0개인 Cluster 정책 VIP를 계속 광고할지(2.5절) |

`bgpControlPlane.*` 값은 1.18.14, 1.19.8, 1.20.2, 1.21.0-pre.3의 `values.yaml`을 diff한 결과 동일합니다. **[1.21 pre-release]** BGP 플래그가 `pkg/bgp/config` 모듈로 이동하여 router ID 플래그를 포함한 동일 플래그가 operator 플래그 목록에도 나타납니다. Helm 사용법은 그대로입니다.

TCP/179 listen은 선택 사항입니다. 기본적으로 `bgpInstance`에 `localPort`가 없으므로 agent는 **active-only**이며 피어로 먼저 접속만 합니다. `localPort: 179`를 쓰려면 차트의 `securityContext.capabilities.ciliumAgent`에 `CAP_NET_BIND_SERVICE`가 필요하고, 높은 포트를 쓰면 필요 없습니다.

### 2.3 다섯 가지 CRD

모두 cluster-scoped `cilium.io/v2`입니다. 같은 kind의 `cilium.io/v2alpha1` 사본은 **deprecated**(1.20.2, 1.21.0-pre.3에서 `+kubebuilder:deprecatedversion`으로 여전히 제공)이므로 새 매니페스트는 `cilium.io/v2`로 작성합니다.

| Kind | 약칭 | 작성 주체 | 용도 |
|---|---|---|---|
| `CiliumBGPClusterConfig` | `cbgpcluster` | 사용자 | 어떤 노드가 어떤 BGP 인스턴스/피어를 쓰는가 |
| `CiliumBGPPeerConfig` | `cbgppeer` | 사용자 | 세션 파라미터와 피어별 광고 선택 |
| `CiliumBGPAdvertisement` | `cbgpadvert` | 사용자 | 무엇을 어떤 속성으로 광고하는가 |
| `CiliumBGPNodeConfig` | `cbgpnode` | operator (사용자 read-only) | 노드별 해석 결과 + 세션 status |
| `CiliumBGPNodeConfigOverride` | `cbgpnodeoverride` | 사용자 | 노드별 router ID, ASN, 포트, 소스 주소 |

연결 방식이 두 가지로 서로 다르다는 점이 흔한 실수의 원인입니다.

```
CiliumBGPClusterConfig.spec.bgpInstances[].peers[].peerConfigRef.name  --이름-->  CiliumBGPPeerConfig
CiliumBGPPeerConfig.spec.families[].advertisements (label selector)    --레이블-> CiliumBGPAdvertisement.metadata.labels
```

PeerConfig는 `CiliumBGPAdvertisement` 오브젝트의 spec이 아니라 **metadata 레이블**과 매칭해 광고를 고릅니다. 한 피어에 여러 advertisement 오브젝트가 매칭될 수 있습니다. 아무것도 매칭되지 않으면 세션은 올라오지만 아무것도 광고되지 않습니다.

#### CiliumBGPClusterConfig

| 필드 | 타입 / 제한 | 비고 |
|---|---|---|
| `spec.nodeSelector` | LabelSelector | nil 또는 빈 값은 **모든** 노드. 한 노드는 하나의 `CiliumBGPClusterConfig`에만 매칭 가능 |
| `spec.bgpInstances[]` | 1~16개, 키 `name` | 각각 GoBGP 인스턴스 1개 |
| `.name` | 1~255자, 고유 | override에서 참조, 메트릭에서는 `instance_name` |
| `.localASN` | 1~4294967295 | 여기서는 선택. 노드별 override로 지정 가능 |
| `.localPort` | 1~65535 | 미설정이면 listen하지 않음 |
| `.peers[]` | 키 `name` | |
| `.peers[].peerAddress` | IPv4 또는 IPv6 | `autoDiscovery`일 때만 생략 가능 |
| `.peers[].peerASN` | 0~4294967295, 기본 0 | 0이면 피어 OPEN 메시지의 ASN 검증을 건너뜀 |
| `.peers[].autoDiscovery` | `mode: DefaultGateway`, `defaultGateway.addressFamily: ipv4\|ipv6` | 노드의 기본 게이트웨이를 피어로 사용(아래) |
| `.peers[].peerConfigRef.name` | string | **`cilium.io/v2`에는 `name`만 있음**. `group`/`kind`는 deprecated v2alpha1 CRD에만 존재 |

클러스터 설정의 status condition: `cilium.io/NoMatchingNode`, `cilium.io/MissingPeerConfigs`, `cilium.io/ConflictingClusterConfig`(두 클러스터 설정이 같은 노드를 선택하면 operator가 나중 것을 거부).

**Auto-discovery(`DefaultGateway`).** 고정 `peerAddress` 대신 노드의 기본 게이트웨이와 피어링합니다. ToR는 동적 neighbor(FRR의 `bgp listen range`)를 쓰고 모든 ToR가 같은 local ASN을 가져야 합니다. link-local 기본 게이트웨이는 지원되지 않습니다. 기본 경로가 여러 개(multihoming)면 Cilium은 주소 패밀리당 **세션 하나**를 metric이 낮은 경로로 만들고, 장애 시 다른 경로로 옮겨갑니다. 같은 패밀리에 두 세션을 만들 수는 없으므로 두 세션이 필요하면 정적 `peerAddress`를 쓰세요.

#### CiliumBGPPeerConfig

| 필드 | 기본값 / 제한 | 비고 |
|---|---|---|
| `spec.transport.peerPort` | 179 (1~65535) | 원격 포트 |
| `spec.transport.sourceInterface` | 없음 | 해당 인터페이스에서 소스 IP 선택. 패밀리별로 적합한 주소(loopback, multicast, IPv6 link-local 제외)가 최대 1개여야 함. 인터페이스가 없으면 egress 인터페이스 자동 탐지로 fallback. 1.18 문서에는 없고 1.19+ |
| `spec.timers.connectRetryTimeSeconds` | 120 (최소 1) | 지터가 있어 실제 재시도는 [N, 2N) |
| `spec.timers.holdTimeSeconds` | 90 (3~65535) | hold/keepalive를 바꾸면 세션 리셋 |
| `spec.timers.keepAliveTimeSeconds` | 30 (1~65535) | CRD 규칙: keepalive <= holdTime |
| `spec.authSecretRef` | 없음 | BGP secrets 네임스페이스의 Secret 이름. 키 `password` (RFC 2385 TCP MD5) |
| `spec.gracefulRestart.enabled` | 블록이 있으면 필수 | |
| `spec.gracefulRestart.restartTimeSeconds` | 120 (1~4095) | |
| `spec.ebgpMultihop` | 1 (1~255) | 기본 TTL 1. iBGP에서는 무시 |
| `spec.families[]` | afi + safi + `advertisements` selector | `ipv4/unicast`, `ipv6/unicast`만 지원. `families`를 생략하면 두 unicast 패밀리가 협상되지만 광고는 **없음** |

Status condition: `cilium.io/MissingAuthSecret`.

> **Upstream 문서 정정.** upstream 설정 문서는 "가능한 최솟값"을 `holdTimeSeconds=9`, `keepAliveTimeSeconds=3`이라고 적고 있습니다. CRD의 실제 최솟값은 hold >= 3, keepalive >= 1(keepalive <= hold)입니다. 9/3은 권장되는 공격적 설정일 뿐 하한이 아닙니다.

#### CiliumBGPAdvertisement

`spec.advertisements[]` 항목:

| 필드 | 비고 |
|---|---|
| `advertisementType` | `PodCIDR`, `CiliumPodIPPool`, `Service`, `Interface` |
| `service.addresses[]` | `LoadBalancerIP`, `ClusterIP`, `ExternalIP` 중 1개 이상. `Service` 타입에서 필수 |
| `service.aggregationLengthIPv4` / `IPv6` | 0~31 / 0~127. /32, /128 대신 집계 |
| `interface.name` | `Interface` 타입에서 필수 |
| `selector` | Service(또는 pool)에 대한 LabelSelector. PodCIDR 외 타입에서 미설정이면 아무것도 선택하지 않음. `PodCIDR`에는 지정 불가 |
| `attributes.communities` | `standard[]`, `wellKnown[]`, `large[]` |
| `attributes.localPreference` | iBGP 피어에만 전송 |

CEL 검증: `Service`는 `service` 필요, `Interface`는 `interface` 필요, `PodCIDR`은 `selector` 불가.

#### CiliumBGPNodeConfig (operator 산출물)

`spec`은 해석된 설정(`routerID`, `localAddress` 추가)을 그대로 반영합니다. `status.bgpInstances[].peers[]`에는 `name`, `peerAddress`, `peerASN`, `peeringState`, `establishedTime`, `timers.appliedHoldTimeSeconds`/`appliedKeepaliveSeconds`, `routeCount[]`(afi, safi, received, advertised)가 들어갑니다. reconcile 실패는 `cilium.io/BGPReconcileError` condition으로 나타납니다. agent에 exec하지 않고도 읽을 수 있으므로 자동화와 알림의 기준 소스로 적합합니다.

#### CiliumBGPNodeConfigOverride

`metadata.name`은 **반드시 노드 이름**과 같아야 하고, instance/peer 이름은 클러스터 설정과 일치해야 합니다.

| 필드 | 비고 |
|---|---|
| `spec.bgpInstances[].name` | 클러스터 설정의 instance와 일치 |
| `.routerID` | IPv4 주소 문자열 |
| `.localPort` | listen 포트 override |
| `.localASN` | 1~4294967295. 노드/랙별 ASN 가능 |
| `.peers[].name` | 클러스터 설정의 peer와 일치 |
| `.peers[].localAddress` | 소스 주소(따라서 egress 링크) 강제. 기본은 피어 주소에 대한 라우트 조회 |
| `.peers[].localPort` | 접속 시 사용할 소스 포트 |

### 2.4 피어 설정 실무

**Timers.** 기본값은 120/90/30(connect-retry/hold/keepalive)입니다. BFD가 없으므로 직접 연결되지 않은 피어의 장애 감지는 hold time에만 의존하고, 그래서 ToR 링크에서는 9/3 같은 공격적 값을 흔히 씁니다. 대신 keepalive 부하가 늘고 agent CPU 정체에 더 민감해집니다.

**Graceful Restart.** `gracefulRestart.enabled: true`이면 Cilium이 Restarting Speaker(RFC 4724 및 알림이 있는 graceful restart인 RFC 8538)로 동작합니다. agent가 재시작되면 피어는 `restartTimeSeconds`가 지날 때까지 학습한 경로를 유지하므로, eBPF에서 계속 동작하는 데이터 플레인이 agent 업그레이드 동안 블랙홀되지 않습니다. `restartTimeSeconds`는 이미지 pull을 포함한 최악의 agent 재시작 시간보다 크게 잡고, 업그레이드 전에 이미지를 미리 pull하세요. 단점은 노드가 실제로 죽으면 GR 때문에 해당 경로가 최대 restart time 동안 유지되어 `externalTrafficPolicy: Cluster` VIP로 죽은 노드에 트래픽이 갈 수 있다는 점입니다.

**Multihop.** `ebgpMultihop: N`은 1홉보다 먼 eBGP 피어(loopback 피어링 ToR, route server)의 TTL을 정합니다. iBGP에는 영향이 없습니다.

**MD5.**

```bash
kubectl -n kube-system create secret generic bgp-auth \
  --from-literal=password='<시크릿 저장소에서 가져온 값>'
```

`authSecretRef: bgp-auth`로 참조합니다. 비밀번호가 틀리면 커널이 서명이 잘못된 세그먼트를 버리므로 인증 오류가 아니라 `dial: i/o timeout`으로 보입니다. Secret이 없어도 세션은 멈추지 않고 Cilium이 **빈** 비밀번호로 진행하며 오류 로그와 `cilium.io/MissingAuthSecret`만 남깁니다. 세션이 NAT를 지나면 MD5는 동작하지 않습니다.

**BFD 없음.** 1.18~1.21-pre 어디에서도 BFD를 지원하지 않습니다. 완화책: 낮은 hold timer, 직접 연결 링크(링크 다운 시 TCP가 즉시 닫힘), agent 재시작에는 Graceful Restart, 노드 장애에는 resilient hashing/Maglev.

### 2.5 광고(Advertisement)

#### PodCIDR

노드에 할당된 PodCIDR(전체 pool이 아님)을 광고합니다. 노드마다 PodCIDR를 주는 IPAM 모드(`cluster-pool`, Kubernetes host scope)에서만 효과가 있습니다. **ENI, Azure 등 클라우드 IPAM에서는 `PodCIDR` 광고가 효과가 없습니다.** Pod IP가 Cilium이 소유한 노드별 prefix가 아니라 VPC(VNet) 주소이고 클라우드 패브릭이 이미 라우팅하기 때문입니다. [IPAM 심화](10-ipam-deep-dive.md)를 보세요.

#### CiliumPodIPPool

multi-pool IPAM용입니다. `selector`는 pool 레이블에 매칭하며, 특수 키 `io.cilium.podippool.namespace`, `io.cilium.podippool.name`으로 pool 이름 기준 선택을 합니다. 실제로 `CiliumNode`에 할당된 CIDR만 광고됩니다. 1.20.2의 BGP 코드는 `v2alpha1.CiliumPodIPPool`을 watch합니다. **[1.21 pre-release]** `CiliumPodIPPool`이 `cilium.io/v2`로 승격되고 BGP도 따라갑니다(v1.21.0-pre.3의 `pkg/bgp/manager/reconciler/pod_ip_pool.go`).

#### Service

기본은 정확한 `/32`, `/128` 경로입니다.

| 소스 | 출처 | 적용되는 traffic policy |
|---|---|---|
| `LoadBalancerIP` | `.status.loadBalancer.ingress[].ip` | `externalTrafficPolicy`만 |
| `ExternalIP` | `.spec.externalIPs` (KPR이면 `externalIPs.enabled` 필요) | `externalTrafficPolicy`만 |
| `ClusterIP` | `.spec.clusterIP(s)` (외부 접근에는 "External access to ClusterIP services" BPF 설정 필요) | `internalTrafficPolicy`만 |

Selector 특수 키: `io.kubernetes.service.namespace`, `io.kubernetes.service.name`.

**Traffic policy 상호작용.**

| 정책 | 광고하는 노드 |
|---|---|
| `Cluster` | 클러스터 설정이 선택한 모든 노드 |
| `Local` | ready 상태의 로컬 백엔드가 1개 이상 있는 노드만. 경로가 Pod를 따라다님 |

백엔드가 **0개**일 때: `externalTrafficPolicy: Cluster`는 `--enable-no-service-endpoints-routable=true`(기본)이면 모든 노드에서 VIP를 계속 광고하고, 아니면 withdraw합니다. `Local`은 withdraw합니다.

**`loadBalancerClass`.** Cilium은 class가 비어 있거나 `io.cilium/bgp-control-plane`인 Service만 광고합니다. 다른 class(예: `service.k8s.aws/nlb`)의 Service는 무시합니다.

**광고 중복(1.18 이상).** 한 Service에 여러 advertisement가 매칭되면 community는 **합집합**, `localPreference`는 **최댓값**입니다. 1.18 이전에는 마지막 매칭이 이겼습니다.

**집계.** `aggregationLengthIPv4/6`은 Local traffic policy에서 무시됩니다. 알려진 문제: 집계 범위 안의 미할당 VIP에 대한 라우팅 루프, 두 광고가 같은 집계를 서로 다른 속성으로 만들 때의 미정의 동작([cilium/cilium#37623](https://github.com/cilium/cilium/pull/37623), [#40585](https://github.com/cilium/cilium/issues/40585)).

**ECMP.** 같은 VIP를 여러 노드에서 광고하고 라우터의 ECMP 경로 수 제한을 따릅니다. 노드 장애 시 라우터가 resilient hashing을 쓰지 않으면 흐름이 재배치됩니다. Cilium의 Maglev는 `Cluster` 정책에서 노드 간 백엔드 선택을 일관되게 합니다.

#### Interface (1.19 이상)

로컬 인터페이스의 주소를 /32, /128 경로로 광고합니다. 제외: loopback 대역, multicast, IPv6 link-local, v4-mapped. 인터페이스는 admin up이고 oper 상태가 `up` 또는 `unknown`이어야 합니다. Cilium이 주소를 설정해 주지는 않으며, 안정적인 노드/애니캐스트 주소를 가진 dummy 인터페이스가 대표적 용도입니다.

#### Attributes

| 속성 | 값 |
|---|---|
| `communities.standard` | `"65000:99"` 또는 4바이트 십진수 |
| `communities.wellKnown` | `internet`, `planned-shut`, `accept-own`, `route-filter-translated-v4`, `route-filter-v4`, `route-filter-translated-v6`, `route-filter-v6`, `llgr-stale`, `no-llgr`, `blackhole`, `no-export`, `no-advertise`, `no-export-subconfed`, `no-peer` |
| `communities.large` | `"A:B:C"` |
| `localPreference` | iBGP 전용. eBGP 피어에는 속성이 생략됨 |

Cilium은 (피어, 패밀리, advertisement 타입)마다 GoBGP export policy(예: `65000-ipv4-PodCIDR`)와 import policy `allow-local`을 만듭니다. 이는 내부 구현입니다. **v2에는 사용자용 route-policy, prefix-list, AS-prepend, MED, next-hop CRD가 없습니다.** community를 연결 고리로 쓰고, 정책은 ToR의 route-map(community 기준)에서 구현하세요.

### 2.6 전체 예제: 랙별 eBGP, ToR 2대

주소와 ASN은 예시입니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata: {name: rack0}
spec:
  nodeSelector: {matchLabels: {rack: rack0}}
  bgpInstances:
  - name: instance-65001
    localASN: 65001
    peers:
    - {name: tor1, peerASN: 65000, peerAddress: 10.10.0.1, peerConfigRef: {name: tor-peer}}
    - {name: tor2, peerASN: 65000, peerAddress: 10.10.0.2, peerConfigRef: {name: tor-peer}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata: {name: tor-peer}
spec:
  timers: {connectRetryTimeSeconds: 5, holdTimeSeconds: 9, keepAliveTimeSeconds: 3}
  gracefulRestart: {enabled: true, restartTimeSeconds: 120}
  authSecretRef: bgp-auth
  families:
  - afi: ipv4
    safi: unicast
    advertisements: {matchLabels: {advertise: bgp}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata: {name: svc-and-pods, labels: {advertise: bgp}}
spec:
  advertisements:
  - advertisementType: PodCIDR
    attributes: {communities: {standard: ["65001:100"]}}
  - advertisementType: Service
    service: {addresses: [LoadBalancerIP]}
    selector: {matchLabels: {bgp: "true"}}
    attributes: {communities: {large: ["65001:1:100"]}}
```

노드별 override(`metadata.name`에 노드 이름):

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPNodeConfigOverride
metadata: {name: <node-name>}
spec:
  bgpInstances:
  - name: instance-65001
    routerID: "192.168.10.1"
    localPort: 1790
    localASN: 65010
    peers:
    - {name: tor1, localAddress: 10.10.0.11}
```

### 2.7 Router ID

| 모드 | ID 결정 방식 |
|---|---|
| `default` | 노드의 IPv4 주소(IPv4, 듀얼 스택). IPv6 전용 노드는 `cilium_host` MAC의 하위 32비트 |
| `ip-pool` | `bgpControlPlane.routerIDAllocation.ipPool`(IPv4 CIDR)에서 할당 |
| 수동(`NodeConfigOverride.routerID`) | `default` 모드에서는 검증 없음. `ip-pool` 모드에서 pool 안의 값이면 충돌하면 안 됨 |

### 2.8 점검

**Status 먼저**(exec 불필요):

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements,ciliumbgpnodeconfigs
kubectl get ciliumbgpnodeconfigs <node> \
  -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'
kubectl describe ciliumbgpclusterconfig rack0
```

**CLI.** `cilium bgp peers [-o json|summary] [--node N]`, `cilium bgp routes <available|advertised|received> <afi> <safi>`는 1.20.2에서 동작합니다. 이들은 agent REST API를 호출하며, 이 경로는 **1.20에서 deprecated**입니다(아래). 1.21.0-pre.3 in-tree 소스의 CLI도 여전히 agent Pod에서 `cilium bgp peers -o json`을 exec합니다.

**Hive shell(1.20부터 권장).** upstream 1.20 업그레이드 노트는 로컬 REST API와 `cilium-dbg bgp` 명령으로 BGP peer/route/route-policy를 조회하는 방식이 deprecated이며 BGP hive shell 명령을 쓰라고 안내합니다. agent 바이너리는 `cilium-dbg`입니다.

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/peers
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/routes out ipv4 unicast
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/route-policies
```

| 명령 | 의미 |
|---|---|
| `bgp/peers [-f table\|table-json\|json\|detailed] [-o file] [--no-uptime]` | 세션 표 |
| `bgp/routes <loc\|in\|out> <afi> <safi> [-a\|--with-attrs] [--no-age] [-f ...]` | `loc` = Loc-RIB, `in` = Adj-RIB-In, `out` = Adj-RIB-Out |
| `bgp/route-policies [-i instance]` | Cilium이 생성한 export/import policy |

세 명령은 1.20.2와 1.21.0-pre.3에 동일하게 있습니다(`pkg/bgp/commands/cell.go`). `cilium` CLI에는 `shell` 하위 명령이 없으므로 agent Pod 안의 `cilium-dbg`를 쓰세요.

**로그.** agent `subsys=bgp-control-plane`, operator `subsys=bgp-cp-operator`.

**메트릭**(agent, 접두사 `cilium_bgp_control_plane_`): `session_state`(1 = established), `advertised_routes`, `received_routes`(레이블 `instance_name`, `local_asn`, `neighbor`, `neighbor_asn`, `afi`, `safi`), `reconcile_errors_total{instance_name}`, `reconcile_run_duration_seconds{instance_name}`. operator: `cilium_operator_bgp_control_plane_reconcile_errors_total{resource_kind,resource_name}`, `..._reconcile_run_duration_seconds`.

> **메트릭 레이블 변경.** 1.19.8 메트릭 문서의 레이블은 `vrouter`, 1.20.2의 레이블은 `instance_name`입니다. 1.20 업그레이드 노트에는 이 변경이 언급되지 않으므로, `vrouter` 기준 대시보드/알림은 1.19에서 1.20으로 올릴 때 조용히 매칭이 끊깁니다. 업그레이드 작업에 쿼리 수정을 포함하세요.

### 2.9 v1 제거와 CRD 버전 타임라인

| 릴리스 | 상태 |
|---|---|
| 1.18 | `CiliumBGPPeeringPolicy`(v1) deprecated. v1과 v2가 한 노드에 모두 매칭되면 PeeringPolicy 우선. v2alpha1 BGP v2 CRD는 `cilium.io/v2`로 대체되어 deprecated |
| 1.19 | v1 CRD와 컨트롤 플레인(`pkg/bgpv1`) **제거**. 업그레이드 전에 마이그레이션 필수 |
| 1.20 | v2 BGP CRD의 v2alpha1 사본은 여전히 제공되지만 deprecated |
| 1.21-pre | 동일 |

1.19 이전 v2alpha1 PeerConfig의 `spec.transport.localPort`는 제거되었고, 포트 설정은 클러스터 설정 instance의 `localPort`와 override에 있습니다.

### 2.10 운영과 장애 시나리오

| 이벤트 | 동작 | 완화 |
|---|---|---|
| agent 재시작/업그레이드 | 스피커가 agent 안에 있으므로 세션 끊김. 데이터패스는 계속 전달 | Graceful Restart, `restartTimeSeconds` > agent 부팅 시간, 새 이미지 사전 pull |
| 노드 크래시 | 피어가 hold time(GR이면 restart time 추가)만큼 대기 | 낮은 hold timer, resilient hashing ECMP |
| 링크 다운, 직접 연결 | TCP 즉시 종료 | 해당 없음 |
| 링크 다운, 다중 홉 | hold timer(기본 90초) | hold time 단축. BFD 불가 |
| operator 다운 | 새 `CiliumBGPNodeConfig` 생성 안 됨. operator의 PodCIDR/LB IP 할당도 중단 | operator HA |
| Service 백엔드 전부 소실 | 2.5절 | 정책을 의도적으로 선택 |

**노드 종료 런북.** 노드를 drain합니다. 레이블을 바꿔 `nodeSelector`에서 빠지게 하면 세션이 Notification과 함께 닫힙니다. 피어가 경로를 withdraw할 때까지(즉시, 또는 RFC 8538 사용 시 stale timer 후) 기다립니다. ECMP 재해시로 일부 연결이 리셋될 수 있습니다.

**[1.21 pre-release]** BGP 컨트롤러가 호스트 데이터패스 BPF 프로그램 attach와 LB 맵 채움을 기다린 뒤에야 경로를 광고합니다(`pkg/bgp/agent/datapath_waiter.go`). agent 시작 직후 서비스할 수 없는 상태에서 경로가 광고되던 구간을 없애며, 1.20에는 없습니다.

### 2.11 온프레미스 ToR 참조 토폴로지

```
            [ 상위 L3 / 방화벽 ]
                 |            |
             ToR-A (AS65000) ToR-B (AS65000)    정적 neighbor 또는 `bgp listen range`
              |  \  /  |     ECMP, resilient hashing, GR helper
      node1..N (Cilium AS65001, 랙별 CiliumBGPClusterConfig 1개)
        광고: PodCIDR (cluster-pool / host-scope IPAM)
            + Service LoadBalancerIP (LB IPAM pool에서 할당)
        eTP: Cluster (전체 노드, Maglev 추가) 또는 Local (백엔드 있는 노드만)
```

설계 체크리스트: 랙당 클러스터 설정 1개(노드는 하나에만 매칭), 랙당 피어 2개, hold 9 / keepalive 3과 agent 부팅보다 긴 restart time의 GR, `authSecretRef`로 MD5, ToR route-map에서 Pod 경로와 Service 경로를 구분할 community, ToR 최대 ECMP 경로 수 확인, BFD 없음.

### 2.12 BGP와 AWS

ENI IPAM을 쓰는 EKS에서 Pod IP는 VPC 주소이고 VPC 패브릭이 이미 라우팅합니다. 노드가 PodCIDR를 소유하지 않으므로 PodCIDR 광고는 효과가 없고, 노드 경로를 받아 줄 BGP 스피커도 VPC에는 없습니다. 따라서 AWS에서 BGP는 주로 온프레미스에서 도는 EKS Hybrid Nodes에 의미가 있으며 이때 피어는 온프레미스 ToR입니다([hybrid nodes 네트워크 구성](../../eks-hybrid-nodes/02-network-configuration.md)). 이 저장소의 hybrid-node 예제는 1.18 빌드를 고정해 `v2alpha1` API를 쓰고 있으니, 1.19 이상에서는 `cilium.io/v2`를 사용하세요.

## 3. LB IPAM

**성숙도**: 안정 CRD `cilium.io/v2` `CiliumLoadBalancerIPPool`(1.18.14에서 v2가 storage 버전이고 v2alpha1도 계속 제공되며, v2alpha1은 1.19.8에서 처음 deprecated로 표시됨). LB IPAM은 operator에 내장되어 있고 첫 pool을 만들기 전까지는 휴면입니다(`--enable-lb-ipam`, 기본 true). 주소 할당만 하며 공지는 하지 않습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata: {name: blue-pool}
spec:
  blocks:
  - cidr: "10.0.10.0/24"
  - start: "10.0.20.100"
    stop: "10.0.20.200"
  serviceSelector:
    matchLabels: {bgp: "true"}
---
apiVersion: v1
kind: Service
metadata: {name: web, namespace: example, labels: {bgp: "true"}}
spec:
  type: LoadBalancer
  loadBalancerClass: io.cilium/bgp-control-plane
  ports: [{port: 80}]
  selector: {app: web}
```

`serviceSelector`는 `blocks` 아래가 아니라 `spec` 아래에 둡니다(upstream 문서 예제는 들여쓰기가 잘못되어 있습니다).

| Pool 필드 | 비고 |
|---|---|
| `blocks[]` | `cidr` 또는 `start`+`stop` |
| `serviceSelector` | 특수 키 `io.kubernetes.service.namespace`/`.name` |
| `disabled` | 기본 false |
| `allowFirstLastIPs` | `Yes` 또는 `No`. `No`는 CIDR 블록의 첫/마지막 주소만 예약. /31, /32, /127, /128과 start/stop 블록에서는 무시 |

알아둘 동작:

- CIDR이 겹치면 나중 pool이 conflicting(`cilium.io/PoolConflict`)으로 표시됩니다. Status condition `cilium.io/IPsTotal`, `IPsAvailable`, `IPsUsed`는 `kubectl get ippools`로 볼 수 있습니다.
- pool을 수정하면 기존 Service의 IP가 재할당될 수 있습니다.
- class 처리: class가 없는 `LoadBalancer` Service는 기본적으로 LB IPAM이 처리합니다. Helm `defaultLBServiceIPAM`은 `lbipam`(기본), `nodeipam`, `none`이며, `none`이면 인식되는 class가 있는 Service만 IP를 받습니다. Cilium이 모르는 class는 조용히 무시됩니다. Service에는 `cilium.io/IPAMRequestSatisfied` condition이 붙습니다.
- IP 패밀리는 `ipFamilyPolicy`를 따릅니다: SingleStack(둘 다 가능하면 IPv4), PreferDualStack, RequireDualStack.
- 특정 주소는 `lbipam.cilium.io/ips: "a,b"`로 요청합니다(pool selector는 그대로 적용, `.spec.loadBalancerIP`는 deprecated). pool의 첫/마지막 주소는 요청하지 마세요.
- **공유**: `lbipam.cilium.io/sharing-key`, `lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"|"*"`. 1.20.2는 포트/프로토콜 충돌이 없으면 공유합니다. **[1.21 pre-release]** 더 엄격한 호환 규칙: 같은 포트+프로토콜 불가, `externalTrafficPolicy` 동일, `Local`이면 모든 Service가 `lbipam.cilium.io/sharing-permit-different-pods: "true"`를 지정하지 않는 한 같은 Pod를 선택해야 함(BGP와 L2는 L4를 인식하지 못해 트래픽이 드롭될 수 있음), cross-namespace가 허용되지 않으면 같은 네임스페이스.
- **1.19 데이터패스 변경**: LB-IPAM IP로 오는 N/S TCP/UDP 중 어떤 Service에도 정의되지 않은 포트는 드롭됩니다.
- Gateway API: `Gateway.spec.addresses`가 LB IPAM에 전달됩니다. `spec.infrastructure.annotations`의 `io.cilium/lb-ipam-ips` 어노테이션이 우선하며 이후 deprecated 예정입니다.

Pod IPAM은 별개 주제입니다: [IPAM 심화](10-ipam-deep-dive.md).

## 4. L2 announcements

**성숙도**: 1.20.2, 1.21.0-pre.3에서 beta. CRD는 아직 `cilium.io/v2alpha1` `CiliumL2AnnouncementPolicy`입니다.

Service마다 선출된 노드 하나가 Service의 external/LoadBalancer IP에 대한 ARP(IPv4)/NDP(IPv6)에 응답하고, 이후 eBPF로 분산합니다. BGP가 없는 온프레미스 LAN이 대상입니다. **AWS VPC 안에서는 적용할 수 없습니다.** VPC는 VIP에 L2 브로드캐스트 의미나 gratuitous ARP 장애조치를 제공하지 않습니다. 온프레미스나 하이브리드 사이트에서만 사용하세요.

```yaml
l2announcements:
  enabled: true
  leaseDuration: 3s
  leaseRenewDeadline: 1s
  leaseRetryPeriod: 200ms
kubeProxyReplacement: true
k8sClientRateLimit: {qps: 32, burst: 64}
```

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata: {name: policy1}
spec:
  serviceSelector: {matchLabels: {color: blue}}
  nodeSelector:
    matchExpressions:
    - {key: node-role.kubernetes.io/control-plane, operator: DoesNotExist}
  interfaces: ["^eth[0-9]+"]
  externalIPs: true
  loadBalancerIPs: true
```

| 필드 | 비고 |
|---|---|
| `nodeSelector`, `serviceSelector` | 공지 가능한 노드, 대상 Service |
| `interfaces[]` | Go 정규식(OR). 보안 통제 수단이 아님. 장치는 Cilium의 `--devices` 집합에도 있어야 함 |
| `externalIPs`, `loadBalancerIPs` | boolean, 기본 모두 false |

Service의 `loadBalancerClass`는 없거나 `io.cilium/l2-announcer`여야 합니다.

**리더 선출.** Service마다 Cilium 네임스페이스에 `cilium-l2announce-<ns>-<svc>` 이름의 `coordination.k8s.io` Lease가 하나씩 생기며, 선착순이라 부하가 고르지 않습니다. 새 리더는 gratuitous ARP를 보냅니다. 기본값: `leaseDuration` 15s, `leaseRenewDeadline` 5s, `leaseRetryPeriod` 2s. 제약: duration > renewDeadline, renewDeadline은 1.2(leader-election JitterFactor) x retryPeriod보다 엄격히 커야 하며, 아니면 agent가 경고를 남기고 timer를 덮어씁니다. 장애조치는 `leaseDuration - leaseRenewDeadline`에서 `leaseDuration + leaseRenewDeadline` 사이에 일어나며, 기본값이면 10~20초, 3s/1s/200ms이면 2~4초입니다.

**API 부하.** 각 Service lease는 대략 `leaseRenewDeadline`마다 갱신되므로 `QPS ~ Service 수 x (1 / leaseRenewDeadline)`를 예산으로 잡습니다(재시도와 조회를 무시한 대략적 추정). agent 클라이언트 기본 제한은 10 QPS / burst 20이며 agent의 다른 API 트래픽과 공유합니다. 기본 5s에서는 Service당 약 0.2 QPS라 수십 개만 리더로 맡아도 예산의 상당 부분을 쓰고, 1s timer에서는 Service 약 10개만으로 예산을 전부 소진합니다. timer를 줄이기 전에 `k8sClientRateLimit`을 올리세요. RBAC에는 lease create/get/update/list/delete가 필요합니다.

**제한.** `externalTrafficPolicy: Local`과 호환되지 않습니다(선출된 노드에 Pod가 없으면 트래픽 드롭). 한 IP의 모든 트래픽을 한 노드가 받으므로 클러스터 앞단 로드밸런싱이 없습니다.

**L2 Pod announcements**는 별도 기능입니다. `l2podAnnouncements.enabled`와 `.interfacePattern`(정규식)이 로컬 Pod IP에 대한 GARP/NA를 보냅니다. 기존 `--l2-pod-announcements-interface` 플래그는 1.19에서 제거되었습니다.

점검: `kubectl -n kube-system get lease | grep cilium-l2announce`, `cilium-dbg shell -- db/show l2-announce`, `cilium-dbg shell -- db/show devices`, LAN의 다른 호스트에서 `arping`.

## 5. Node IPAM

Helm `nodeIPAM.enabled=true`(기본 false, operator `--enable-node-ipam`, operator 재시작 필요). `loadBalancerClass: io.cilium/node`(또는 `defaultLBServiceIPAM: nodeipam`)인 Service에는 노드 주소가 `.status.loadBalancer`에 게시됩니다. ExternalIP가 있으면 그것을, 없으면 InternalIP를 쓰고 `ipFamilies`를 따릅니다. `Cluster`는 모든 노드, `Local`은 EndpointSlice에 Pod가 있는 노드만 게시합니다. 레이블 `node.kubernetes.io/exclude-from-external-load-balancers` 또는 taint `ToBeDeletedByClusterAutoscaler`가 있는 노드는 제외되고, 어노테이션 `io.cilium.nodeipam/match-node-labels`로 노드를 제한할 수 있습니다. Cilium Ingress/Gateway Service의 `Local` 정책에서는 (가짜 EndpointSlice 때문에) 동작하지 않습니다. BGP와 L2가 모두 불가능한 곳에서만, 그리고 사설 노드 주소로만 쓰세요. 공인 노드 IP를 게시하면 CloudFront만 진입점이라는 규칙 밖에 공개 진입점이 생깁니다.

## 6. 어떤 기능이 Service를 맡는가

| `loadBalancerClass` | 담당 | 필요 조건 |
|---|---|---|
| 없음 | 기본은 LB IPAM(`defaultLBServiceIPAM`) | pool, 도달 가능하려면 BGP 또는 L2 |
| `io.cilium/bgp-control-plane` | LB IPAM + BGP 광고 | BGP Control Plane |
| `io.cilium/l2-announcer` | LB IPAM + L2 공지 | L2 announcements |
| `io.cilium/node` | Node IPAM | `nodeIPAM.enabled` |
| `service.k8s.aws/nlb` | AWS Load Balancer Controller | Cilium BGP/LB IPAM은 무시 |

## 7. Egress Gateway

**성숙도**: `CiliumEgressGatewayPolicy`는 `cilium.io/v2`(cluster-scoped, 약칭 `cegp`)이며 1.20 문서에서 beta로 표시되지 않습니다.

선택한 Pod가 선택한 목적지 CIDR로 보내는 트래픽을 게이트웨이 노드로 보내 고정된 소스 IP로 SNAT합니다. 외부 방화벽이 예측 가능한 주소를 볼 수 있게 하는 용도입니다.

요건: `egressGateway.enabled=true`, `bpf.masquerade=true`, `kubeProxyReplacement=true`, agent와 operator **모두** 재시작. identity 모드 `kvstore`(`crd` 사용), ClusterMesh(게이트웨이가 같은 클러스터에 있어야 함), CiliumEndpointSlice와는 호환되지 않습니다. `--enable-ipv4-egress-gateway`는 1.19에서 제거되었습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumEgressGatewayPolicy
metadata: {name: egress-sample}
spec:
  selectors:
  - podSelector:
      matchLabels: {org: empire, class: mediabot, io.kubernetes.pod.namespace: default}
  destinationCIDRs: ["192.0.2.0/24"]
  egressGateway:
    nodeSelector: {matchLabels: {egress-node: "true"}}
    egressIP: 10.168.60.100
```

| 필드 | 비고 |
|---|---|
| `selectors[]` | `podSelector` 및/또는 `namespaceSelector`(네임스페이스는 레이블 `io.kubernetes.pod.namespace`). `nodeSelector` 단독은 불가 |
| `destinationCIDRs[]`, `excludedCIDRs[]` | IPv4/IPv6. excluded는 부분집합이어야 함. 내부 주소(Pod, 노드, API 서버)는 항상 EGW에서 제외 |
| `egressGateway.nodeSelector` | 필수. 여러 노드가 매칭되면 노드 이름 순으로 첫 번째. **매칭 없음: 목적지 CIDR로 가는 트래픽은 드롭** |
| `egressGateway.interface` / `egressIP` | 상호 배타(둘 다 있으면 정책 무시). `interface`는 첫 IPv4/IPv6 사용, `egressIP`는 Cilium이 관리하는 장치에 있어야 함, 둘 다 없으면 기본 경로 인터페이스 사용 |
| `egressGateways[]` | 최대 64개. 비어 있지 않으면 `egressGateway`는 무시 |

제한 사항:

- **1.20.2, 1.21.0-pre.3에는 HA가 없습니다.** `egressGateways[]`는 정적 multi-gateway이며, 각 소스 엔드포인트는 CiliumEndpoint UID 해시로 게이트웨이 하나에 고정됩니다. 집합이 바뀌면 엔드포인트가 재배정되어 기존 연결이 끊깁니다(cilium/cilium#39245). 죽은 게이트웨이의 health check나 자동 failover는 두 버전의 소스(`pkg/egressgateway` 검색)에서 확인되지 않습니다. 1.21-pre의 CRD는 1.20.2와 CIDR 타입만 다릅니다.
- 게이트웨이는 선택 후의 IP 변경을 따라가지 않으므로 정책을 다시 적용해야 합니다.
- 설정한 IP가 없으면 "No Egress IP configured" 사유로 드롭됩니다.
- 새 Pod는 정책이 프로그래밍되기 전 잠시 Pod/노드 자신의 IP로 트래픽을 보낼 수 있습니다.
- (egress IP, 원격 IP:포트)당 SNAT 포트 예산은 약 65535에서 node-port 범위 상한(기본 32767)을 뺀 값, 즉 32768 연결입니다. `cilium-dbg shell -- db/show nat-stats`로 확인합니다.

점검: `kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf egress list`(소스 IP, 목적지 CIDR, egress IP, 게이트웨이 IP).

**EKS에서.** 게이트웨이 노드에는 egress 주소가 붙은 ENI(추가 ENI 또는 보조 사설 IP)가 필요합니다. egress IP는 사설 VPC 주소이며, 인터넷으로 나가려면 NAT gateway를 경유시킵니다. 게이트웨이 노드에 공인 IP나 EIP를 붙이지 마세요. ENI IPAM에서는 `--egress-multi-home-ip-rule-compat`가 1.19에서 제거되었으므로 1.18에서 먼저 이전하세요.

## 8. Local Redirect Policy

`CiliumLocalRedirectPolicy`(`cilium.io/v2`, namespaced)는 Service ClusterIP 또는 임의 IP:포트로 향하는 트래픽을 노드 로컬 백엔드 Pod로 리다이렉트합니다.

`localRedirectPolicies.enabled=true`로 활성화합니다(기존 `localRedirectPolicy` 키는 deprecated). operator와 agent를 재시작합니다. 선택적 클러스터 전체 허용 목록은 `localRedirectPolicies.addressMatcherCIDRs`입니다(upstream 문서의 YAML은 철자가 다른 키를 보여주지만 실제 Helm 키는 `addressMatcherCIDRs`).

```yaml
apiVersion: cilium.io/v2
kind: CiliumLocalRedirectPolicy
metadata: {name: lrp-svc}
spec:
  redirectFrontend:
    serviceMatcher: {serviceName: my-service, namespace: default}
  redirectBackend:
    localEndpointSelector: {matchLabels: {app: proxy}}
    toPorts: [{port: "80", protocol: TCP}]
```

| Matcher | 용도 |
|---|---|
| `serviceMatcher` | ClusterIP Service 전용. Service 항목을 `LocalRedirect` 타입으로 바꾸고 노드 로컬 백엔드만 사용 |
| `addressMatcher{ip, toPorts[]}` | Service가 아닌 IP. 기존 ClusterIP 프런트엔드는 덮어쓰지 않음 |

규칙: 백엔드 Pod는 정책과 같은 네임스페이스여야 하고, 다중 포트는 named port가 필요하며, **새** 연결만 리다이렉트되고(클라이언트 재시작 필요), 정책은 수정할 수 없습니다(삭제 후 재생성). 지원되는 kube-proxy replacement 구성: 전체 KPR, KPR + `socketLB.hostNamespaceOnly=true`, KPR 끔 + `socketLB.enabled=true`, KPR 끔 단독(Pod에서 ClusterIP만). 대표 용도는 node-local DNS(kube-dns 프런트엔드를 자체 네트워크 네임스페이스의 node-local-dns Pod로 리다이렉트)이며, `cilium-dbg lrp list`로 확인합니다.

## 9. Service traffic distribution

`loadBalancer.serviceTopology`(기본 `false`, 플래그 `--enable-service-topology`)를 켜면 kube-proxy replacement가 Topology Aware Routing 힌트와 `spec.trafficDistribution`을 **모두** 존중합니다. `PreferSameZone`(및 deprecated 별칭 `PreferClose`)은 EndpointSlice zone 힌트를 노드의 `topology.kubernetes.io/zone` 레이블과 비교하고, `PreferSameNode`는 로컬 노드 백엔드를 우선하며 후보가 없으면 기본 동작으로 돌아갑니다. **[1.21 pre-release]** 활성(ready) 백엔드만 선호 후보가 됩니다. `externalTrafficPolicy`/`internalTrafficPolicy: Local`은 "선호"가 아니라 "제한"이므로 별개입니다. 멀티 AZ EKS에서는 `serviceTopology: true`와 `trafficDistribution: PreferSameZone`으로 AZ 간 트래픽을 줄일 수 있습니다. Gateway API에서는 `CiliumGatewayClassConfig.spec.service.trafficDistribution`이 생성된 Service로 전달됩니다.

## 10. L7 진입점: Ingress와 Gateway API

전제 조건: `kubeProxyReplacement=true`, `l7Proxy=true`(기본), TPROXY 지원(기본은 iptables, `bpf.tproxy=true`는 beta이며 iptables 의존을 제거), LoadBalancer Service 지원(또는 host-network 모드, 1.16+).

**트래픽 흐름.** eBPF가 Service 포트로 오는 패킷을 가로채 노드별 Envoy로 TPROXY합니다. 트래픽은 특수 `ingress` identity를 받으므로 정책이 두 번(world에서 ingress, ingress에서 백엔드) 적용됩니다. 소스 IP는 두 `externalTrafficPolicy` 값 모두에서 보존되며, `Local`에서는 Cilium이 모든 노드가 health check 포트를 통과시키게 합니다. `CiliumNetworkPolicy`는 두 구간을 모두 허용해야 합니다. TLS passthrough에서는 백엔드가 Envoy IP를 봅니다.

### Ingress

| Helm 값 | 기본값 |
|---|---|
| `ingressController.enabled` / `.default` | `false` / `false` |
| `ingressController.loadbalancerMode` | `dedicated` (`shared` 또는 `dedicated`, Ingress별 어노테이션 `ingress.cilium.io/loadbalancer-mode`) |
| `ingressController.enforceHttps` | `true` |
| `ingressController.useRemoteAddress`, `.xffNumTrustedHops` | `true`, `0` |
| `ingressController.ingressLBAnnotationPrefixes` | `lbipam.cilium.io`, `nodeipam.cilium.io`, `service.beta.kubernetes.io`, `service.kubernetes.io`, `cloud.google.com` (Ingress에서 Service로 전파) |
| `ingressController.service.*` (shared) | `name: cilium-ingress`, `type: LoadBalancer`, `externalTrafficPolicy: Cluster`, annotations, `loadBalancerClass` |
| `ingressController.hostNetwork.*` | `enabled: false`, `sharedListenerPort: 8080` |

### Gateway API

Cilium 1.20.2와 1.21.0-pre.3은 **Gateway API v1.6.1**을 사용합니다(1.19.8: v1.4.1, 1.18.14: v1.3.0). 지원 kind: GatewayClass, Gateway, HTTPRoute, GRPCRoute, TLSRoute, BackendTLSPolicy, ReferenceGrant, ListenerSet, TCPRoute, UDPRoute. 필수 CRD: GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant, BackendTLSPolicy, TLSRoute. TCPRoute, UDPRoute, ListenerSet은 선택이며 없으면 해당 기능이 꺼집니다. `kubectl apply --server-side`로 설치합니다.

> **업그레이드 함정: Gateway API v1.6.1과 TLSRoute.** v1.6.1에서 TLSRoute가 `v1alpha2`에서 `v1`로 승격되었고, 1.20 업그레이드 노트는 v1.6.1을 최소 버전으로 요구합니다. 기존 TLSRoute 오브젝트가 있다면 v1.6.1의 **experimental 채널** TLSRoute CRD를 설치해야 합니다(`v1alpha2` 버전을 여전히 포함). **standard 채널** v1.6 TLSRoute CRD를 설치하면 기존 `v1alpha2` 오브젝트를 읽을 수 없게 되어 etcd에서 사라진 것처럼 보입니다. TLSRoute를 백업하고, Cilium을 1.20으로 올리기 **전에** Gateway API CRD를 먼저 업그레이드하세요.

| Helm 값 | 기본값 |
|---|---|
| `gatewayAPI.enabled` | `false` |
| `gatewayAPI.gatewayClass.create` | `auto` |
| `gatewayAPI.enableProxyProtocol`, `.enableAppProtocol`, `.enableAlpn` | `false` |
| `gatewayAPI.useRemoteAddress`, `.xffNumTrustedHops` | `true`, `0` |
| `gatewayAPI.externalTrafficPolicy` | `Cluster` (host network에서는 무시) |
| `gatewayAPI.secretsNamespace` | `create: true`, `name: cilium-secrets`, `sync: true` |
| `gatewayAPI.hostNetwork.enabled` / `.nodes.matchLabels` | `false` / `{}` |

생성되는 Service 이름은 `cilium-gateway-<gateway>`이며 기본 타입은 `LoadBalancer`입니다. `CiliumGatewayClassConfig`(`cilium.io/v2alpha1`, namespaced, `GatewayClass.parametersRef`에서 참조, alpha)로 조정합니다: `spec.service{type, externalTrafficPolicy, loadBalancerClass, ipFamilies, ipFamilyPolicy, allocateLoadBalancerNodePorts, loadBalancerSourceRanges, loadBalancerSourceRangesPolicy, trafficDistribution}`, `envoy.serverHeaderTransformation`, `httpOptions.grpcWebTranslation.enabled`. Gateway별로는 `spec.infrastructure.annotations`/`labels`가 생성된 Service로 복사되며, 이것이 `service.beta.kubernetes.io/aws-load-balancer-*` 어노테이션을 전달하는 방법입니다. `spec.infrastructure.parametersRef`는 지원되지 않습니다.

Host-network 모드(`gatewayAPI.hostNetwork.enabled=true`): Envoy가 노드 인터페이스에서 listen합니다. 1023 초과 포트를 쓰거나 `NET_BIND_SERVICE`를 부여해야 하며, LoadBalancer Service 모드와 배타적이고, TCPRoute/UDPRoute와는 호환되지 않으며, Service는 NodePort가 되고, Gateway status에는 최대 16개 주소가 표시됩니다.

### EKS 패턴: CloudFront VPC origin, internal NLB, Cilium

공개 진입점은 CloudFront뿐입니다. 어떤 구성요소도 internet-facing이 아닙니다.

```
Internet --> CloudFront --(VPC origin)--> INTERNAL NLB (private subnet)
         --> 노드 NodePort --> Cilium Envoy (Ingress 또는 Gateway) --> Pod
```

```yaml
kubeProxyReplacement: true
ingressController:
  enabled: true
  loadbalancerMode: shared
  service:
    type: LoadBalancer
    loadBalancerClass: service.k8s.aws/nlb
    allocateLoadBalancerNodePorts: true
    externalTrafficPolicy: Cluster
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-scheme: internal
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
      service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-<nlb-sg>
      service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules: "true"
```

Gateway API 방식은 `CiliumGatewayClassConfig.spec.service.loadBalancerClass: service.k8s.aws/nlb`로 설정하고 같은 `aws-load-balancer-*` 어노테이션을 `Gateway.spec.infrastructure.annotations`에 넣습니다.

이 패턴의 규칙:

- `scheme: internal`은 필수입니다. 절대 `internet-facing`을 쓰지 않습니다.
- `target-type: instance`를 씁니다. Cilium의 shared Ingress Service는 가짜 EndpointSlice를 쓰므로 `ip` 타깃은 Pod로 해석되지 않습니다. [Ingress와 Gateway API](../../service-mesh/cilium-service-mesh/05-ingress-gateway.md)를 참고하세요.
- 로드밸런서의 보안 그룹은 CloudFront만 허용합니다. VPC origin 생성 후 만들어지는 서비스 관리 보안 그룹 `CloudFront-VPCOrigins-Service-SG`(더 제한적이라 권장, 직접 만드는 그룹 이름에 이 접두사를 쓰지 마세요) 또는 CloudFront 관리형 prefix list `com.amazonaws.global.cloudfront.origin-facing`(듀얼 스택이면 `com.amazonaws.global.ipv6.cloudfront.origin-facing` 추가)입니다. `0.0.0.0/0`, `::/0` ingress는 금지이고 노드에 공인 IP/EIP도 붙이지 않습니다([AWS: VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)).
- 노드 보안 그룹은 인터넷에 열린 CIDR이 아니라 NLB의 보안 그룹만 NodePort 범위에서 허용합니다.

## 11. SRv6와 정적 라우팅

SRv6는 지원 기능으로서 **없습니다**. 1.20.2, 1.21.0-pre.3 소스에는 문서 페이지, Helm 키, CRD가 없고, 숨겨진 `--enable-srv6` agent 플래그, BPF 훅, `cilium-dbg bpf srv6` 점검 명령만 OSS 컨트롤 플레인 없이 남아 있습니다. 계획에 넣지 마세요. 정적 라우팅은 `autoDirectNodeRoutes`를 쓰는 네이티브 라우팅이나 클라우드 라우트 테이블에 맡깁니다([Part 9](09-overlay-native-routing.md)).

## 실습

> 실습 1~4는 FRR 같은 라우터 컨테이너를 둘 수 있는 로컬 환경(kind 또는 VM 몇 대)이 필요하고, 실습 5는 `--profile <SANDBOX_PROFILE>`로 일회용 샌드박스 AWS 계정을 대상으로 합니다. 기대 결과는 말로만 설명하며 실제 출력은 포함하지 않습니다.

### 실습 1: FRR ToR와 BGP 세션

**사전 조건**: worker 2개인 kind 클러스터와 같은 Docker 네트워크의 FRR 컨테이너(AS 65000, 노드 IP를 neighbor로 설정, remote AS 65001), `bgpControlPlane.enabled=true`인 Cilium, 노드 IP에 맞게 고친 2.6절 매니페스트(`authSecretRef`는 제거하거나 Secret을 먼저 생성).

1. worker에 `rack=rack0` 레이블을 붙이고 ClusterConfig, PeerConfig, Advertisement를 적용합니다.
2. `kubectl get ciliumbgpnodeconfigs`에 레이블이 붙은 노드마다 오브젝트가 하나씩 나타납니다.
3. `kubectl get ciliumbgpnodeconfigs <node> -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'`와 `cilium-dbg shell -- bgp/peers`가 `established`를 보고해야 하고, FRR의 `show bgp summary`에도 neighbor가 up으로 보여야 합니다.
4. `cilium-dbg shell -- bgp/routes out ipv4 unicast`에 노드의 PodCIDR가 보이고, FRR `show ip route bgp`에 학습된 경로가 보입니다.
5. 한 노드의 agent Pod를 삭제합니다. GR을 켠 경우 FRR은 restart time까지 경로를 (stale로) 유지하고, GR이 없으면 경로가 즉시 사라집니다. 둘을 비교하세요.

**롤백/정리**: BGP 리소스 3개를 삭제하고 노드 레이블을 제거합니다. ClusterConfig를 삭제하면 operator가 NodeConfig를 지우고 세션이 닫힙니다.

### 실습 2: LB IPAM + BGP와 traffic policy 상호작용

**사전 조건**: 실습 1 실행 중.

1. 3절의 pool과 Service를 생성합니다(FRR 컨테이너가 받아들이는 범위 안의 블록 사용).
2. `kubectl get svc web -n example`에 pool의 EXTERNAL-IP가 보이고 `kubectl get ippools`의 `IPsUsed`가 1입니다.
3. `bgp/routes out ipv4 unicast`에 선택된 모든 노드의 /32가 보입니다. FRR 컨테이너에서 `curl <VIP>`를 실행합니다.
4. `kubectl patch svc web -n example -p '{"spec":{"externalTrafficPolicy":"Local"}}'`. 경로는 ready Pod가 있는 노드에만 남아야 합니다. Deployment를 스케일하며 경로가 따라가는지 확인하세요.

**정리**: Service, Deployment, pool 삭제.

### 실습 3: L2 announcements

**사전 조건**: Linux 브리지 위의 kind 클러스터, KPR 사용, 3s/1s/200ms와 상향한 client rate limit으로 `l2announcements.enabled=true`, 같은 브리지의 클라이언트 컨테이너.

1. L2 정책과 pool에서 주소를 받는 `LoadBalancer` Service를 적용합니다.
2. `kubectl -n kube-system get lease | grep cilium-l2announce`에 해당 Service의 lease가 보이고, 클라이언트의 `arping`은 리더 노드의 MAC을 반환합니다.
3. 리더 노드의 Cilium agent Pod를 삭제하거나 노드 컨테이너를 중지하고 `arping`이 실패하는 시간을 측정합니다. 이 timer에서는 수 초, 기본값에서는 10~20초가 예상됩니다.

**정리**: 정책과 Service 삭제. 롤백: lease 값을 기본값으로 되돌립니다.

### 실습 4: Egress Gateway

**사전 조건**: KPR, `bpf.masquerade=true`, `egressGateway.enabled=true`, agent와 operator 재시작 완료. 클라이언트 IP를 로깅하는 외부 웹 서버 컨테이너, 장치에 보조 주소가 있는 `egress-node=true` 레이블 노드.

1. 그 주소와 서버 CIDR로 7절과 같은 정책을 적용합니다.
2. 선택된 Pod에서 서버로 `curl`하면 서버 로그에 노드/Pod IP가 아니라 egress IP가 찍혀야 합니다.
3. 소스 노드의 `cilium-dbg bpf egress list`에 항목이 나옵니다. 노드 레이블을 제거하면 해당 CIDR 트래픽은 드롭되어야 합니다(게이트웨이 없음).

**정리/롤백**: 정책 삭제, 레이블 제거. 적용 중에는 선택된 트래픽에 영향을 주는 작업입니다.

### 실습 5: CloudFront 뒤의 EKS internal NLB (샌드박스 계정)

**사전 조건**: `aws sts get-caller-identity --profile <SANDBOX_PROFILE>`가 예상한 샌드박스 계정 `<ACCOUNT_ID>`와 의도한 assumed role을 보여야 합니다. Cilium과 AWS Load Balancer Controller가 있는 EKS 클러스터, 이미 생성된 CloudFront VPC origin.

1. 10절의 Helm 값(원하면 Gateway API 방식)으로 설치합니다.
2. `aws elbv2 describe-load-balancers --profile <SANDBOX_PROFILE> --query 'LoadBalancers[].[LoadBalancerName,Scheme]'`에서 새 NLB가 `internal`이어야 합니다.
3. `aws ec2 describe-security-groups --profile <SANDBOX_PROFILE> --group-ids <nlb-sg> --query 'SecurityGroups[].IpPermissions'`에서 소스가 CloudFront VPC-origin 그룹 또는 prefix list뿐이어야 하며 `0.0.0.0/0`, `::/0`은 없어야 합니다.
4. NLB를 VPC origin의 대상으로 지정하고 CloudFront 도메인으로 요청합니다.

**정리**: Ingress 또는 Gateway를 삭제하면 컨트롤러가 NLB를 지웁니다. `deleting` 상태가 아니라 실제 not-found 응답이 나올 때까지 확인하세요.

## 버전 차이 (Version Delta)

| 영역 | 1.18 | 1.19 | 1.20 | 1.21-pre |
|---|---|---|---|---|
| BGP v1 `CiliumBGPPeeringPolicy` | deprecated | **제거** | 제거 | 제거 |
| BGP CRD | v2 (및 v2alpha1) | `cilium.io/v2` storage, v2alpha1 deprecated | 동일 | 동일 |
| BGP `Interface` 광고, `transport.sourceInterface` | 문서에 없음 | 있음 | 있음 | 있음 |
| GoBGP | 이번 검토 범위 밖 | gobgp v3 (1.19.8) | gobgp v4 | gobgp v4 |
| BGP 메트릭 레이블 | 해당 없음 | `vrouter` (문서) | `instance_name` | `instance_name` |
| `cilium-dbg bgp` / REST 조회 | 지원 | 지원 | **deprecated**, hive shell `bgp/*` 사용 | deprecated 표기 |
| 데이터패스 준비 전 광고 방지 | 없음 | 없음 | 없음 | **있음** |
| `CiliumLoadBalancerIPPool` | v2(storage), v2alpha1도 제공 | `cilium.io/v2` (v2alpha1 deprecated) | v2 | v2, 더 엄격한 공유 규칙 |
| Gateway API CRD | v1.3.0 | v1.4.1 | **v1.6.1** (TLSRoute 함정) | v1.6.1 |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | **v2** |
| Egress Gateway | CRD v2 | `--enable-ipv4-egress-gateway`, `--egress-multi-home-ip-rule-compat` 제거 | HA 없음 | HA 없음 |
| L2 announcements | beta | beta | beta (CRD v2alpha1) | beta |
| SRv6 | 없음 | 없음 | 없음 | 없음 (숨겨진 플래그만) |

## 트러블슈팅

| 증상 | 가능한 원인 | 확인 |
|---|---|---|
| `CiliumBGPNodeConfig`가 생성되지 않음 | operator 미실행 또는 `nodeSelector`가 아무것도 선택하지 않음 | ClusterConfig condition `NoMatchingNode`, operator 로그 `subsys=bgp-cp-operator` |
| 클러스터 설정이 거부됨 | 다른 클러스터 설정이 같은 노드를 선택 | `ConflictingClusterConfig` |
| 세션이 멈춤, `dial: i/o timeout` | MD5 비밀번호 오류, ACL, 잘못된 소스 주소 | `authSecretRef`, `cilium.io/MissingAuthSecret`, `localAddress`/`sourceInterface` |
| 세션은 up인데 경로 없음 | PeerConfig `families[].advertisements`가 advertisement 레이블과 불일치 | 레이블 비교, `bgp/route-policies` |
| EKS에서 PodCIDR가 광고되지 않음 | ENI IPAM에는 노드별 PodCIDR가 없음 | [IPAM](10-ipam-deep-dive.md) |
| Service VIP가 광고되지 않음 | `loadBalancerClass`가 `io.cilium/bgp-control-plane`/없음이 아님, selector 불일치, ready 백엔드가 없는 `Local` 정책 | Service YAML, `bgp/routes out` |
| agent 업그레이드 때 경로 소실 | Graceful Restart 없음 또는 restart time 부족 | PeerConfig GR, 이미지 사전 pull |
| 1.20 이후 Grafana BGP 패널이 빔 | 레이블 `vrouter`가 `instance_name`으로 변경 | 쿼리 수정 |
| LB IP가 `<pending>` | pool 없음, selector 불일치, pool 충돌, 모르는 class | `kubectl get ippools`, Service condition |
| L2 VIP가 흔들리거나 실패 | `Local` 정책, lease API 스로틀링 | Lease 오브젝트, `k8sClientRateLimit` 상향 |
| Egress 트래픽 드롭 | 게이트웨이 `nodeSelector`에 맞는 노드 없음 또는 장치에 IP 없음 | `bpf egress list`, 드롭 사유 |
| Gateway API CRD 업그레이드 후 TLSRoute 소실 | v1alpha2 데이터 위에 standard 채널 v1.6 CRD 설치 | 백업에서 복원, experimental 채널 CRD 사용 |
| Gateway Service가 생성되지 않음 | 필수 Gateway API CRD 누락, KPR 꺼짐 | operator 로그, `cilium status` |

## 검증 한계와 출처

이 실습은 이번 검토에서 실제 클러스터에서 실행하지 않았으며, upstream 소스와 문서를 기준으로 점검했습니다. `bgp/peers`, `bgp/routes` 명령 문법은 `pkg/bgp/commands`에서 확인했으나 실제 표 출력은 캡처하지 않아 싣지 않았습니다. EKS 네이티브(비 hybrid) 클러스터에서의 BGP(Transit Gateway Connect, VPC Route Server 피어링 등)는 조사하지 않아 제외했습니다. 확인하지 못한 항목: 1.21 GA에서 Egress Gateway에 health 기반 failover가 생기는지, 메트릭 레이블 변경이 1.19와 1.20 사이 정확히 어느 릴리스에서 이뤄졌는지(1.20.2에는 있고 1.19.8 문서에는 없음).

출처(별도 표기가 없으면 태그 v1.20.2):

- [BGP Control Plane 개요](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst), [설정](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst), [운영](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [BGP CRD 타입](https://github.com/cilium/cilium/tree/v1.20.2/pkg/k8s/apis/cilium.io/v2), [hive shell 명령](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/commands/cell.go)
- [LB IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst), [L2 announcements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst), [Node IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst)
- [Egress Gateway](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/egress-gateway/egress-gateway.rst), [Local Redirect Policy](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/local-redirect-policy.rst)
- [1.20 업그레이드 노트](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc), [Gateway API](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/servicemesh/gateway-api)
- [v1.21.0-pre.3 BGP datapath waiter](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/bgp/agent/datapath_waiter.go), [v1.21.0-pre.3 LB IPAM](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst)

## 퀴즈

[Part 11 퀴즈](../../quizzes/networking/cilium/11-bgp-lb-egress-edge-quiz.md)로 확인해 보세요.
