# Part 10: IPAM 심화

> **검토 기준**: Cilium 1.20.2 (안정, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. **[1.21 pre-release]** 표시 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다.
> **마지막 업데이트**: 2026년 10월 15일

[Part 4](04-ipam-policy.md)에서 IPAM 모드와 Helm 조각을 소개했습니다. 이 장은 그 아래 계층을 다룹니다. 어떤 주소를 누가 소유하는지, `cilium-cni ADD`부터 endpoint 생성까지 무슨 일이 일어나는지, 설치 전에 pool 크기를 어떻게 계산하는지, ENI allocator가 언제 EC2를 호출하는지, LB IPAM과 Node IPAM이 Pod IPAM과 무엇이 다른지입니다. 주소가 어떻게 라우팅되는지는 [Overlay와 Native Routing](09-overlay-native-routing.md), LB 주소 광고는 [BGP, 로드 밸런싱, Egress, Edge](11-bgp-lb-egress-edge.md)를 참고하세요.

## IPAM이란 무엇이고 무엇이 아닌가

Kubernetes 클러스터에서는 서로 다른 네 종류의 주소를 서로 다른 주체가 할당합니다. 이를 혼동하는 것이 "IPAM 문제"의 가장 흔한 원인입니다.

| 주소 | 소유자 | Cilium의 역할 |
|---|---|---|
| Pod(endpoint) IP | Cilium IPAM (이 장의 대부분) | 할당, 추적, 해제 |
| Service ClusterIP | kube-apiserver (`--service-cluster-ip-range`) | 없음. 데이터패스에 프로그래밍만 함 |
| LoadBalancer Service IP | LB IPAM(`CiliumLoadBalancerIPPool`) 또는 클라우드 컨트롤러 | operator에서 할당만 수행. 광고는 BGP Control Plane 또는 L2 Announcements가 담당 |
| 노드를 LB처럼 쓰는 주소 | Node IPAM (`loadBalancerClass: io.cilium/node`) | operator가 노드 주소를 Service status에 복사 |

`CiliumPodIPPool`은 ClusterIP를 할당하지 않고, `CiliumLoadBalancerIPPool`은 Pod IP를 할당하지 않습니다. `CiliumCIDRGroup`은 아무것도 할당하지 않는 정책용 CIDR 집합입니다.

## 큰 그림: CiliumNode 핸드셰이크

대부분의 모드는 노드마다 하나씩 존재하는 `CiliumNode` 커스텀 리소스를 통한 agent와 operator 사이의 대화입니다.

```
                        +-----------------------------+
                        |        CiliumNode <node>    |
                        |  spec.ipam.podCIDRs         |  cluster-pool
                        |  spec.ipam.pools.requested  |  multi-pool / eni (agent가 기록)
                        |  spec.ipam.pools.allocated  |  multi-pool / eni (operator가 기록)
                        |  spec.ipam.pool             |  crd (외부 allocator가 기록)
                        |  status.ipam.*              |  사용 중 IP, operator-status.error
                        |  status.eni.enis            |  eni (operator가 기록)
                        +--------------+--------------+
                 watch/update          |          watch/update
        +------------------------+     |     +--------------------------+
        |  cilium-agent (노드)   |<----+---->|  cilium-operator         |
        |  로컬 Pod IP allocator |           |  노드 CIDR, EC2/Azure    |
        |  CNI /ipam REST        |           |  API 호출, pool 할당     |
        +------------------------+           +--------------------------+
```

agent는 노드가 현재 소유한 범위에서 개별 Pod IP를 할당하고, 노드가 무엇을 소유할지는 operator(또는 Kubernetes, 외부 시스템)가 결정합니다. `cluster-pool`, `multi-pool`, `eni` 모드에서는 agent가 자기 `CiliumNode`를 직접 만듭니다(`auto-create-cilium-node-resource`, 기본 true). operator는 `ipam.cilium.io/ignore: "true"` 어노테이션이 붙은 `CiliumNode`를 무시합니다. 다른 시스템이 관리하는 노드를 위한 탈출구입니다.

### 모드별 agent allocator 연결 (1.20.2)

| `ipam.mode` | 노드 용량의 출처 | agent allocator |
|---|---|---|
| `kubernetes` | `Node.spec.podCIDRs` (또는 어노테이션) | 노드 CIDR 위의 host-scope allocator |
| `cluster-pool` (기본) | operator가 `CiliumNode.spec.ipam.podCIDRs`에 기록 | 노드 CIDR 위의 host-scope allocator |
| `multi-pool` | operator가 `spec.ipam.pools.allocated`에 기록 | multi-pool manager |
| `eni` | operator(EC2 API)가 `status.eni.enis`를 갱신, agent가 이를 `spec.ipam.pools.allocated`로 변환 | **ENI multi-pool allocator (1.20 신규)** |
| `crd`, `azure`, `alibabacloud` | `CiliumNode.spec.ipam.pool` | CRD allocator |
| `delegated-plugin` | 다른 CNI IPAM 플러그인 | no-op allocator |

Helm 상호작용: `eni.enabled=true`는 `ipam.mode`와 무관하게 `ipam: eni`를 강제하고, `eni.enabled` 없이 `ipam.mode=eni`를 쓰면 차트 검증에서 실패합니다. `gke`라는 값은 없으며 self-managed GKE는 `kubernetes`를 씁니다.

### 노드 로컬 주소

Cilium은 각 노드 범위에서 자신의 주소를 떼어 씁니다. `cilium_host` router IP, health endpoint IP, Ingress 사용 시 ingress IP입니다. `cilium-dbg status --all-addresses`에서 `(router)`, `(health)`, `(ingress)`로 표시됩니다. host-scope allocator는 노드 CIDR의 첫 주소(network)와 마지막 주소(broadcast)도 제외하므로, 용량 계산(아래 "크기 산정")에서 이를 빼야 합니다.

## Pod IP 수명 주기

`delegated-plugin`을 제외한 모든 모드에서 kubelet부터 실행 중인 endpoint까지의 경로입니다.

```
kubelet -> CRI -> cilium-cni ADD
                     |
                     | 1. 남아 있는 host 측 인터페이스 이름 제거
                     | 2. POST /ipam   (cilium-agent unix socket)
                     |       owner = <namespace>/<pod>, expiration = true
                     v
                 cilium-agent: IpamPostIpamHandler
                     | 3. pool이 비어 있으면 -> pool 선택 (어노테이션/selector, multi-pool)
                     | 4. AllocateNextWithExpiration
                     |       -> 응답: IPv4/IPv6, pool, cidrs, gateway,
                     |          master-mac, interface-number, skip-masquerade,
                     |          expiration-uuid, host-addressing (router IP)
                     |       -> 10분 expiration 타이머 시작
                     v
                 cilium-cni: veth(또는 netkit) 생성, Pod netns에 IP/route 설정
                     | 5. PUT /endpoint/{id}
                     v
                 cilium-agent: endpoint, identity, 데이터패스 구성
                     | 6. endpoint 생성이 expiration 타이머를 중지
                     v
                 Pod Running

 4단계 이후 어느 단계든 실패 -> deferred DELETE /ipam/{ip}?pool=<pool>
 CNI DEL -> endpoint 삭제 -> agent가 IP 해제 (metric ipam_events_total{action="release"})
```

1.20.2 소스에서 확인한 핵심 메커니즘입니다.

- **REST 호출**: agent API(`api/v1/openapi.yaml`)의 `POST /ipam`, `POST /ipam/{ip}`, `DELETE /ipam/{ip}`. CNI 플러그인은 `IPAMAllocate("", podName, "", true)`를 호출하며 마지막 인자가 expiration 플래그입니다.
- **Expiration 타이머**: expiration과 함께 할당된 IP는 endpoint 생성이 타이머를 멈추지 않으면 `defaults.IPAMExpiration`, 즉 10분 뒤 자동 해제됩니다. CNI 플러그인이 할당 후 endpoint 생성 전에 죽어도 agent 재시작 전까지 주소가 새는 일을 막습니다.
- **복원**: agent가 재시작하면 실행 중 endpoint의 IP를 다시 확보합니다(`cilium-dbg status --all-addresses`에 `[restored]`). `--bypass-ip-availability-upon-restore`는 ENI/Azure 업그레이드 경우에만 쓰입니다.
- **ENI 계열 모드**(`eni`, `azure`, `alibabacloud`): 응답에 ENI MAC, gateway, CIDR이 포함됩니다. 플러그인은 MAC으로 parent interface index를 정하고(ENI 한정) agent는 호스트에 endpoint별 라우팅 규칙을 설치합니다. 이 모드들이 endpoint route를 강제하는 이유입니다.
- **`delegated-plugin`**: CNI 플러그인이 직접 설정된 IPAM 바이너리(AKS의 `azure-ipam` 등)에 `DelegateAdd`를 호출하고 endpoint를 `ExternalIpam`으로 표시하므로 agent는 그 IP를 해제하지 않습니다. DEL 시 플러그인이 `DelegateDel`을 호출합니다. Pod IP 회계는 Cilium이 하지 않습니다.

점검:

```bash
# agent가 아는 모든 주소와 소유자(ns/pod). multi-pool은 pool/ip로 표시
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status --all-addresses

# 할당 요약 줄, 예: "IPAM: IPv4: N/M allocated from <cidr>"
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status | grep -i ipam
```

Pod가 `ContainerCreating`에 머물며 CNI 오류 `unable to allocate IP via local cilium agent`가 나오면 2~4단계가 실패한 것입니다. 모드별 원인은 트러블슈팅 섹션에 정리했습니다.

## 모드 카탈로그와 선택 매트릭스

### 기능 비교

1.20.2 upstream IPAM concepts 페이지를 바탕으로 정리했습니다.

| 기능 | Kubernetes host scope | Cluster scope (기본) | Multi-pool | CRD-backed | AWS ENI | Azure IPAM | GKE (host scope 경유) |
|---|---|---|---|---|---|---|---|
| Tunnel routing | 예 | 예 | 예 | 아니오 | 아니오 | 아니오 | 아니오 |
| Direct routing | 예 | 예 | 예 | 예 | 예 | 예 | 예 |
| CIDR 설정 주체 | Kubernetes | Cilium | Cilium | 외부 | AWS | Azure | GCP |
| 클러스터당 CIDR 여러 개 | 아니오 | 예 | 예 | 해당 없음 | 해당 없음 | 해당 없음 | 해당 없음 |
| 노드당 CIDR 여러 개 | 아니오 | 아니오 | 예 | 해당 없음 | 해당 없음 | 해당 없음 | 해당 없음 |
| 동적 CIDR/IP 할당 | 아니오 | 아니오 | 예 | 예 | 예 | 예 | 아니오 |

성숙도: cluster-pool, kubernetes, crd, eni는 stable입니다. Multi-pool은 1.18 문서에 "Beta" 배너가 있었고 1.19부터 사라졌습니다(이 장은 1.19부터 stable로 취급하지만 upstream이 "GA"라는 표현을 쓰지는 않습니다). ENI IPv6는 1.20에서 **beta**, cluster-pool에서 multi-pool로의 온라인 마이그레이션은 1.20 신규입니다.

### 선택 매트릭스

upstream 문서와 플랫폼 제약을 종합한 가이드이며 upstream 표는 아닙니다.

| 환경 | 권장 IPAM | 이유와 주의점 |
|---|---|---|
| EKS, VPC 라우팅 가능한 Pod IP 필요(보안 그룹 대상, ALB/NLB IP target, SNAT 없음) | `eni` + Nitro에서 prefix delegation | operator IAM 권한, native routing, `aws-node` 제거 필요. prefix delegation이 없으면 밀도는 인스턴스 ENI/IP 한도에 묶임. IPv6는 beta. Fargate/EKS Auto Mode 노드에는 해당 없음 |
| EKS, VPC IP 부족 또는 고밀도 | `cluster-pool` + VXLAN(Helm 기본) 또는 `multi-pool` | Pod는 노드 IP로 SNAT, EKS 컨트롤 플레인이 Pod IP에 닿지 못하므로 admission webhook은 host network 또는 Service로 노출해야 함 |
| EKS Hybrid Nodes(온프레미스 노드) | `cluster-pool` + VXLAN, pool 목록 = EKS "remote pod networks", 노드당 Pod 수에 맞춘 mask | AWS 지원 구성은 IPv4 전용, VXLAN, cluster-scope IPAM, BGP Control Plane. 배포 후 pool 목록/mask 변경 금지. 온프레미스에서 `eni`는 적용 불가 |
| 온프레미스, 단순 | `cluster-pool` + tunnel | operator 관리, kube-controller-manager 노드 CIDR에 의존하지 않음 |
| 온프레미스, 라우팅 가능한 Pod, 사이트/테넌트별 여러 대역 | `multi-pool` + BGP `CiliumPodIPPool` 광고, `CiliumNodeConfig`로 사이트별 기본 pool | `kubeProxyReplacement=true`, `bpf.masquerade=true` 필요, pool CIDR 중복 금지 |
| 컨트롤 플레인이 노드 CIDR을 이미 할당(kubeadm `--allocate-node-cidrs`, GKE) | `kubernetes` | 정적, 노드당 family별 CIDR 1개 |
| 외부 시스템이 주소 제공 | `crd` | 단일 IP만, direct routing만 |
| AKS | Azure CNI Powered by Cilium(`delegated-plugin`) 또는 BYOCNI + 임의 Cilium IPAM | AKS에 upstream `azure` IPAM 적용 금지 |
| self-managed Azure VM | `azure` | resource group/identity 플래그 필요, 1.21 pre-release에서 재작업 |

### 실행 중 클러스터의 모드 변경

upstream 입장은 문서화된 마이그레이션 외에는 실행 중인 클러스터의 IPAM 모드를 바꾸지 말라는 것이며 "가장 안전한 방법은 새 클러스터"입니다. 문서화된 유일한 온라인 경로는 **cluster-pool에서 multi-pool**입니다(아래 마이그레이션 절). 그 외(kubernetes에서 cluster-pool, ENI로의 전환, overlay에서 ENI)는 Pod IP 대역, 라우팅, EKS에서는 webhook 도달성까지 바뀌므로 새 클러스터나 blue/green 노드 그룹이 필요합니다. `CiliumNodeConfig`로 노드 그룹별 IPAM 모드를 섞는 방식은 upstream에 문서화돼 있지 않아 권장하지 않습니다.

## Kubernetes Host Scope와 Cluster Scope

### Kubernetes host scope (`ipam.mode=kubernetes`)

agent는 시작 시 활성화된 family마다 노드 PodCIDR을 기다립니다. 출처는 `Node.spec.podCIDRs` / `spec.podCIDR` 또는 어노테이션 `network.cilium.io/ipv4-pod-cidr`, `network.cilium.io/ipv6-pod-cidr`(그리고 `ipv4/6-cilium-host`, `ipv4/6-health-ip`, `ipv4/6-Ingress-ip`)입니다. `kube-controller-manager`에 `--allocate-node-cidrs`(및 `--cluster-cidr`, `--node-cidr-mask-size`)가 필요합니다.

```yaml
ipam:
  mode: kubernetes
k8s:
  requireIPv4PodCIDR: true     # ipam.mode=kubernetes에서만 유효
  requireIPv6PodCIDR: false
```

이 모드에서 IPv4가 켜져 있으면 agent가 `k8s-require-ipv4-pod-cidr`를 자동 활성화하므로 명시 설정은 대부분 문서화 목적입니다. 제약: 노드당 family별 CIDR 1개, 노드 등록 시 고정, 동적 증설 없음. self-managed GKE는 이 모드에 `ipv4NativeRoutingCIDR`를 클러스터 CIDR로 지정해 씁니다.

### Cluster scope / cluster-pool (기본)

operator가 노드 prefix 할당을 소유합니다. 각 노드는 `CiliumNode.spec.ipam.podCIDRs`에 CIDR을 받고, agent는 활성 family 전부에 대해 이 필드가 채워질 때까지 시작을 막은 뒤 같은 host-scope allocator를 그 위에서 실행합니다. operator는 재시작 후 기존 할당을 다시 채택하며, 충돌하면 `node has CIDRs allocated (...) that conflict with requested CIDRs`가 발생합니다.

Helm 값(1.20.2 기본값):

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.0.0.0/8"]   # 기본값
    clusterPoolIPv4MaskSize: 24                  # 기본값
    clusterPoolIPv6PodCIDRList: ["fd00::/104"]   # 기본값
    clusterPoolIPv6MaskSize: 120                 # Helm 기본값 (operator 플래그 기본값은 112)
```

렌더링되는 ConfigMap 키는 `cluster-pool-ipv4-cidr`(공백으로 연결된 목록), `cluster-pool-ipv4-mask-size`, `cluster-pool-ipv6-cidr`, `cluster-pool-ipv6-mask-size`입니다. IPv4가 켜졌는데 목록이 비어 있으면("cluster-pool-ipv4-cidr must be provided when using ClusterPool") 또는 꺼진 family에 목록을 지정하면 operator가 시작을 거부합니다.

### 크기 산정

노드 CIDR allocator는 `pkg/ipam/cidrset`입니다. pool CIDR의 prefix 길이 `P`, 노드 mask `M`일 때:

```
pool CIDR당 노드 수       = 2^(M - P)
노드당 주소 수            = 2^(32 - M)          (IPv4)     2^(128 - M) (IPv6)
노드당 사용 가능 Pod IP   = 주소 수 - 2 (network, broadcast) - 최대 3 (router, health, ingress)
```

소스 기준 제약: IPv6는 `M - P`가 16을 넘을 수 없습니다(`clusterSubnetMaxDiff = 16`, 오류 `ErrCIDRSetSubNetTooBig`). allocator가 압축하지 않은 bitmap을 쓰기 때문입니다. IPv4는 `M <= 32`만 요구합니다. upstream 권고는 노드 mask 최소 `/30`, `/29` 이상 권장입니다.

| Pool CIDR | 노드 mask | 노드 수 | 노드당 주소 | 비고 |
|---|---|---|---|---|
| `10.0.0.0/8` (기본) | `/24` | 65,536 | 256 | `2^(24-8)`, 사용 가능 약 251 |
| `10.244.0.0/16` | `/24` | 256 | 256 | 일반적인 소규모 클러스터 |
| `10.244.0.0/16` | `/26` | 1,024 | 64 | `2^(26-16)`, 사용 가능 약 59 |
| `10.244.0.0/16` | `/28` | 4,096 | 16 | 실습용 크기, 사용 가능 약 11 |
| `fd00::/104` (기본) | `/120` | 65,536 | 256 | IPv6 기본값, 차이가 정확히 16 |
| `fd00:10:244::/96` | `/112` | 65,536 | 65,536 | 허용되는 최대 차이 16 |

위 수치는 공식으로 계산한 값이며 "사용 가능"은 예약 2개와 Cilium 소유 3개를 뺀 상한입니다. 실제 Pod 밀도는 kubelet `maxPods`에도 좌우되므로 롤링 업데이트 시 신구 Pod가 겹치는 여유까지 더해 mask를 정하세요.

변경 규칙(검증이 아니라 동작으로 강제됨):

- `clusterPoolIPv4PodCIDRList`의 기존 항목을 수정/삭제하지 마세요. 늘리려면 새 CIDR을 추가합니다.
- `clusterPoolIPv4MaskSize`는 실행 중 클러스터에서 바꿀 수 없습니다.
- allocator 오류(`allocator full`)는 `CiliumNode.status.ipam.operator-status.error`에 나타납니다.

```bash
kubectl get ciliumnodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.ipam.podCIDRs}{"\t"}{.status.ipam.operator-status}{"\n"}{end}'
```

중복 위험: 기본 `10.0.0.0/8`은 대부분의 사내망/VPC 대역과 겹칩니다. 노드 네트워크와 겹치면 노드 연결을 잃으므로 목록은 항상 명시하세요.

**`nativeRoutingCIDRFromClusterPool`**(Helm, 기본 false. 1.20 신규: 1.18.14와 1.19.8의 `values.yaml`에는 없고 1.20.2와 1.21에 있음): pool에서 native-routing CIDR을 유도합니다. cluster-pool이며 활성 family마다 CIDR이 정확히 하나일 때만 유효하고 아니면 템플릿이 실패합니다.

### Dual-stack

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList: ["fd00:10:244::/96"]
    clusterPoolIPv6MaskSize: 112       # 112 - 96 = 16, 허용되는 최대값
ipv4: { enabled: true }
ipv6: { enabled: true }
```

`ipv6.enabled`는 IPv6 Service CIDR이나 underlay IPv6 연결을 만들어 주지 않습니다. 모드별: host scope는 `podCIDRs` 두 항목과 `k8s.requireIPv6PodCIDR`가 필요하고, multi-pool pool은 `ipv4`, `ipv6`, 또는 둘 다 가질 수 있으며 family별 어노테이션 `ipam.cilium.io/ipv4-pool`, `ipam.cilium.io/ipv6-pool`이 있습니다. ENI IPv6는 beta(아래 참조), LB IPAM은 Service의 `ipFamilyPolicy`를 따릅니다. AWS가 지원하는 EKS Hybrid Nodes 구성은 IPv4 전용입니다.

## Multi-Pool IPAM

### 개념

Multi-pool은 "클러스터 전체에 하나의 CIDR 목록" 대신 이름 있는 **pool**(`CiliumPodIPPool`)을 사용합니다. 한 노드가 여러 pool의 블록을 동시에 가질 수 있고 agent가 필요할 때 요청합니다. 테넌트별 대역, 일부 Pod만 라우팅 가능하게(pool 단위 BGP 광고), 사이트별 대역, 출발지 IP 유지가 필요한 pool에 씁니다.

### 전제 조건과 설치

upstream 튜토리얼은 `kubeProxyReplacement=true`와 `bpf.masquerade=true`를 요구합니다. 알려진 제약: iptables 기반 masquerade는 `egressMasqueradeInterfaces`가 필요하므로(upstream issue 22273) eBPF masquerade가 지원 경로입니다. pool CIDR끼리 겹치면 안 됩니다(IP cache가 prefix 하나를 identity 하나에 매핑).

```yaml
ipam:
  mode: multi-pool
  multiPoolPreAllocation: "default=8,mars=4"
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4: { cidrs: ["10.10.0.0/16"], maskSize: 27 }
      mars:
        ipv4: { cidrs: ["10.20.0.0/16"], maskSize: 27 }
kubeProxyReplacement: true
bpf: { masquerade: true }
```

`autoCreateCiliumPodIPPools`는 없는 pool만 만들고 기존 pool을 갱신하지 않습니다. operator 플래그 `--auto-create-cilium-pod-ip-pools <pool>=ipv4-cidrs:...;ipv4-mask-size:...[;allow-first-ip:...][;allow-last-ip:...]`로 매핑되는데 이 문법은 `podSelector`, `namespaceSelector`, (1.21) `pool[].reservedRanges`를 표현할 수 없습니다. 그런 pool은 커스텀 리소스로 만드세요.

### CiliumPodIPPool

```yaml
apiVersion: cilium.io/v2alpha1      # 1.20.x. 1.21부터는 cilium.io/v2 [1.21 pre-release]
kind: CiliumPodIPPool
metadata:
  name: mars
spec:
  # allowFirstIP / allowLastIP는 spec의 필드입니다(spec.ipv4 아님). 기본 false,
  # /31 /32 /127 /128에서는 무시됨
  ipv4:
    cidrs: ["10.20.0.0/16"]
    maskSize: 27
  podSelector:
    matchLabels:
      io.kubernetes.pod.namespace: tenant-mars   # synthetic label
  namespaceSelector:
    matchLabels:
      tenant: mars
```

cluster-scoped, 짧은 이름 `cpip`. `maskSize`, `allowFirstIP`, `allowLastIP`는 변경 불가입니다(CEL `self == oldSelf`). 노드에 **할당된 블록**의 첫/마지막 주소는 `allowFirstIP`/`allowLastIP`를 켜지 않으면 예약됩니다. 특정 family 블록이 없는 pool은 그 family에서 건너뜁니다.

**API 버전 주의.** 1.20.2는 `cilium.io/v2alpha1`을 제공합니다. **[1.21 pre-release]** `cilium.io/v2`가 storage 버전이 되고 `v2alpha1`은 deprecated입니다. v2는 `cidrs`를 32개로 제한하고 `spec.ipv4.pool[]` / `spec.ipv6.pool[]`를 추가합니다. 1.21로 올릴 때 매니페스트와 도구를 v2로 바꾸세요.

### Pool 선택

Pod 생성 시점에 한 번만 평가됩니다(실행 중 Pod의 어노테이션을 바꿔도 효과 없음). 우선순위(`pkg/ipam/metadata/manager.go`와 문서 기준):

1. **Pod 어노테이션**: `ipam.cilium.io/ipv4-pool` / `ipam.cilium.io/ipv6-pool`(family별)이 `ipam.cilium.io/ip-pool`보다 우선합니다.
2. **Namespace 어노테이션**: Pod namespace의 같은 키들.
3. **`CiliumPodIPPool` selector**: `podSelector`와 `namespaceSelector`(둘 다 있으면 모두 일치해야 함). family당 pool이 정확히 하나만 일치해야 하며 아니면 오류와 이벤트와 함께 할당이 **실패**합니다.
4. **기본 pool**: `ipam-default-ip-pool`(기본 `default`). 단 Pod나 namespace에 `ipam.cilium.io/require-pool-match: "true"`가 있으면 할당이 막힙니다.

올바른 어노테이션 키는 `ipam.cilium.io/ip-pool`입니다(`pkg/annotation/k8s.go`). upstream 튜토리얼 일부에는 `ipam.cilium.io/ipam-pool`이라고 적혀 있는데 이 키는 아무 효과가 없습니다.

```bash
kubectl annotate namespace tenant-mars ipam.cilium.io/ip-pool=mars
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pinned
  annotations:
    ipam.cilium.io/ip-pool: mars
spec:
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
```

### agent가 용량을 요청하는 방식

agent는 수요를 `CiliumNode.spec.ipam.pools.requested[] {pool, needed{ipv4-addrs, ipv6-addrs}}`에 기록합니다. operator는 노드의 가용 주소가 `needed`를 채울 때까지 pool의 `maskSize` 단위 블록을 잘라 `spec.ipam.pools.allocated[] {pool, cidrs[], allowFirstIP, allowLastIP}`에 추가합니다. agent는 완전히 비었고 수요를 넘는 블록을 돌려줍니다. 오류는 `status.ipam.operator-status.error`에 기록됩니다.

문서화된 공식은 `neededIPs = roundUp(inUse + pending + preAlloc, preAlloc)`입니다. 실제 코드(`pkg/ipam/multipool_manager.go`의 `neededIPCeil`)는 "다음의 다음" 배수로 올림하므로 `preAlloc = P`일 때 수요 0은 `P`, 1~`P`는 `2P`, `P+1`은 `3P`를 요청합니다. 즉 최소 pre-allocation 한 단위의 여유가 항상 생깁니다. agent 플래그는 `--ipam-multi-pool-pre-allocation`(Helm `ipam.multiPoolPreAllocation`)이고 비어 있으면 `default=8`, 다른 pool은 0입니다. 개수는 활성 family마다 적용됩니다.

블록은 `maskSize` 단위로 할당되므로 블록이 `preAlloc`의 몇 배가 되게 `maskSize`를 고르세요(예: `preAlloc=8`에 `/27` = 32주소). 그렇지 않으면 노드가 작은 블록을 계속 얻고 반납합니다.

### 노드별 기본 pool, masquerade, 라우팅

**노드별 기본 pool**은 `CiliumNodeConfig`(`cilium.io/v2`, namespace `kube-system`)로 지정합니다. 변경은 agent Pod를 재시작해야 적용됩니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  name: ip-pool-dc1
  namespace: kube-system
spec:
  defaults:
    ipam-default-ip-pool: dc1-pool
  nodeSelector:
    matchLabels:
      topology.kubernetes.io/zone: dc1
```

cluster-pool 마이그레이션에서 지정한 기본 pool 이름에는 이 override를 쓰지 마세요.

**Masquerade.** agent 옵션 `--only-masquerade-default-pool`(eBPF masquerade 필요) 또는 `CiliumPodIPPool`의 어노테이션 `ipam.cilium.io/skip-masquerade="true"`가 기본이 아닌 pool의 Pod 출발지 IP를 보존합니다. 새 Pod에만 적용됩니다. agent 옵션에 대응하는 전용 Helm 키는 없으므로 `extraConfig.only-masquerade-default-pool: "true"`를 쓰세요(이 정확한 경로는 이번 검토에서 실행하지 않았습니다).

**라우팅.** pool CIDR은 BGP Control Plane(`advertisementType: CiliumPodIPPool`, [Part 11](11-bgp-lb-egress-edge.md))으로 광고하거나 같은 L2 세그먼트에서 `autoDirectNodeRoutes`로 도달시킵니다.

### Pool을 안전하게 바꾸기와 `reservedRanges` [1.21 pre-release]

규칙: 새 pool과 추가 CIDR은 실시간으로 넣을 수 있습니다. 노드가 사용 중인 CIDR은 제거하면 안 되고 사용 중인 pool은 삭제하면 안 됩니다(operator가 `CIDR from pool still in use by node` 경고를 남김). 1.20의 CIDR 교체 절차는 pool 수정, operator 재시작, 그 뒤 노드 그룹마다 cordon, drain, 해당 `CiliumNode` 삭제, agent 재시작, uncordon을 한 그룹씩 반복하는 것입니다.

**[1.21 pre-release]** `cilium.io/v2`는 CIDR별 설정과 `reservedRanges`를 추가해, 기존 할당을 고아로 만들지 않고 CIDR을 퇴역시킬 수 있게 합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumPodIPPool
metadata:
  name: default
spec:
  ipv4:
    cidrs: ["10.10.0.0/16", "10.20.0.0/16"]
    maskSize: 24
    pool:
    - cidr: 10.10.0.0/16
      reservedRanges:
      - start: 10.10.0.0
        end: 10.10.255.255
```

`10.10.0.0/16`에서 이미 받은 노드 블록은 계속 동작하고 새 블록은 `10.20.0.0/16`에서만 나옵니다. 모든 노드 그룹이 이전을 마친 뒤 `cidrs`에서 옛 CIDR과 대응하는 `pool` 항목을 제거합니다. 각 `pool[].cidr`은 `cidrs` 중 하나여야 합니다(CEL 검증).

### Cluster-pool에서 multi-pool로 온라인 마이그레이션 (1.20+)

1.19 이하에는 없습니다. operator 옵션: `enable-cluster-pool-to-multi-pool-migration`(기본 false), `multi-pool-migration-workers`(기본 16), `ipam-default-ip-pool`.

전제: 마이그레이션은 단방향(롤백 없음). 기존 Pod는 모두 **기본 pool**에 속합니다. 기본 pool은 operator 재시작 전에 존재해야 하며(커스텀 리소스 또는 `autoCreateCiliumPodIPPools`) 할당된 모든 노드 CIDR을 포함하고 같은 mask 크기여야 합니다. 노드별로 기본 pool 이름을 override하지 마세요.

```bash
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set ipam.mode=multi-pool \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.cidrs='{10.0.0.0/8}' \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.maskSize=24 \
  --set-string extraConfig.enable-cluster-pool-to-multi-pool-migration=true \
  --set operator.rollOutPods=true \
  --set rollOutCiliumPods=false
```

이후: 각 `CiliumNode`의 기존 PodCIDR이 `spec.ipam.pools.allocated`에 나타날 때까지 기다립니다. BGP Control Plane이 PodCIDR을 광고 중이면 agent를 재시작하기 **전에** `CiliumBGPAdvertisement`를 `advertisementType: PodCIDR`에서 기본 pool을 선택하는 `CiliumPodIPPool`로 바꿉니다(아직 cluster-pool 모드인 agent가 마이그레이션된 할당의 광고를 멈추므로 일시적인 경로 철회가 예상됩니다). 그다음 agent를 한꺼번에 또는 점진적으로 재시작합니다. 롤아웃 중 cluster-pool과 multi-pool agent가 섞여도 연결은 유지됩니다. 모든 agent가 재시작되기 전에는 기본이 아닌 pool의 Pod를 스케줄하지 마세요.

### 제약과 BGP 연계

pool 간 CIDR 중복 불가, `egressMasqueradeInterfaces` 없는 iptables masquerade 미지원, 서로 떨어진 pool에는 `ip-masq-agent` 고려. 사용 중인 pool CIDR 변경은 위의 drain 절차가 필요합니다.

## CRD-Backed IPAM (`ipam.mode=crd`)

agent는 자기 노드 이름의 `CiliumNode`를 watch합니다. `spec.ipam.pool`은 사용 가능한 **단일 IP**의 맵 `ip -> {owner, resource}`이며 CIDR은 지원하지 않습니다. 사용 중인 IP는 `status.ipam.used`에 보고되고 status 갱신은 최대 15초에 한 번입니다(Helm `ipam.ciliumNodeUpdateRate`). IPv6는 `spec.ipam.ipv6-pool`과 `status.ipam.ipv6-used`를 씁니다. direct routing 전용입니다.

시작 시 agent가 `Waiting for initial IP to become available in '<node>' custom resource`를 로그로 남기며 IP가 최소 1개(health check 사용 시 최소 2개) 필요합니다. RBAC은 `ciliumnodes`와 `ciliumnodes/status` 전체 권한이 필요합니다. upstream 문장에는 아직 `available`/`inuse`가 남아 있지만 스키마는 `pool`/`used`이므로 설치된 CRD를 따르세요.

## AWS ENI IPAM

### 아키텍처 (1.20.2)

EC2 API를 호출하는 것은 operator뿐입니다. operator는 ENI 인벤토리를 `CiliumNode.status.eni.enis`에 기록하고, agent는 이를 pool `default`의 `spec.ipam.pools.allocated` CIDR로 변환합니다. 보조 IP는 `/32`, 위임된 prefix는 `/28`(IPv4) 또는 `/80`(IPv6)입니다. agent가 로컬에서 Pod IP를 할당하고 수요를 `spec.ipam.pools.requested`에 보고합니다. 1.20 ENI 모드에는 `CiliumPodIPPool`도 `ip-pool` 어노테이션도 없습니다. 1.19와 1.18의 ENI는 CRD allocator(`spec.ipam.pool`, `status.ipam.used`)였습니다. 1.19에서 1.20으로의 롤링 업그레이드는 지원됩니다. operator가 `spec.ipam.pools.requested`의 존재와 `status.ipam.used`의 부재로 새 agent를 구분합니다.

ENI 모드는 native routing과 endpoint route를 강제하며(`eni.enabled=true`가 이미 설정하므로 values의 `routingMode: native`, `endpointRoutes.enabled`는 중복) agent는 터널링과의 조합을 거부합니다. `enableIPv4Masquerade`는 1.18부터 ENI 모드 기본값이 false이고 **[1.21 pre-release]** `enableIPv6Masquerade`도 ENI 모드에서 기본 false입니다.

### 설치와 노드 준비

VPC CNI(`aws-node`)는 DaemonSet에 존재하지 않는 `nodeSelector`를 패치해 제거하고(upstream은 `io.cilium/aws-node-enabled=true` 사용) `eni.enabled=true`로 설치합니다. 노드 그룹에 시작 taint `node.cilium.io/agent-not-ready=true:NoExecute`를 두어 워크로드가 agent를 기다리게 합니다. `eth0` 외의 `eth*`를 NetworkManager / systemd-networkd가 관리하지 못하게 해야 합니다. 그렇지 않으면 OS가 보조 IP를 지울 수 있습니다(Amazon Linux 2023에서 특히 중요). VPC CNI를 교체할 때는 `AWS-SNAT-CHAIN-*`, `AWS-CONNMARK-CHAIN-*` iptables 체인을 비웁니다.

operator IAM 권한(upstream 목록, 가능하면 태그로 리소스 범위 제한): `ec2:DeleteNetworkInterface`, `DescribeInstanceTypes`, `DescribeNetworkInterfaces`, `DescribeSubnets`, `DescribeVpcs`, `DescribeRouteTables`(1.18부터 필수), `DescribeSecurityGroups`, `CreateNetworkInterface`, `AttachNetworkInterface`, `ModifyNetworkInterfaceAttribute`, `AssignPrivateIpAddresses`, `CreateTags`. 추가로 `DescribeTags`(ENI 가비지 컬렉션, 기본 켜짐), `UnassignPrivateIpAddresses`(해제), `AssignIpv6Addresses`(IPv6), `DescribeInstances`(`--instance-tags-filter` 사용 시). **[1.21 pre-release]** 선택적으로 `GetSecurityGroupsForVpc`(실패 시 경고 한 번 후 대체 동작)와 `DescribeManagedPrefixLists` / `GetManagedPrefixListEntries`. upstream은 prefix 작업용으로 private IP assign/unassign 액션만 문서화하므로, 최소 권한 정책을 쓰기 전에 정확한 IAM 액션을 AWS 문서로 확인하세요. 자격 증명은 `eni.iamRole`(IRSA) 또는 `cilium-aws` secret으로 제공합니다.

### Helm 값

```yaml
eni:
  enabled: true
  iamRole: arn:aws:iam::<account-id>:role/cilium-operator
  awsEnablePrefixDelegation: true
  awsReleaseExcessIPs: true
  eniTags:
    team: platform
  gcInterval: 5m                        # "0s"이면 ENI 가비지 컬렉션 비활성화
  nodeSpec:                             # 노드별 설정, 1.19부터
    firstInterfaceIndex: 1              # eth0는 노드 트래픽용으로 유지
    subnetTags: ["pod-subnet=true"]
    securityGroupTags: ["cilium-pod-sg=true"]
    excludeInterfaceTags: ["no-cilium=true"]
    deleteOnTermination: true
ipam:
  nodeSpec:
    ipamMinAllocate: 16
    ipamPreAllocate: 8
  operator:
    externalAPILimitQPS: 8
    externalAPILimitBurstSize: 40
```

태그 목록 항목은 ConfigMap에서 쉼표로 이어진 `key=value` 문자열로 렌더링됩니다(예: `eni-subnet-tags`). 필터는 두 종류이며 서로 바꿔 쓸 수 없습니다. operator 수준의 `eni.subnetIDsFilter`, `eni.subnetTagsFilter`, `eni.instanceTagsFilter`는 operator가 관리할 인스턴스/서브넷을 제한하며 배포 시점에 각 인스턴스가 이미 일치하는 서브넷에 ENI를 갖고 있다고 가정합니다. Cilium이 **새로 만드는** ENI만 제어하려면 노드별 `eni.nodeSpec` 값(또는 커스텀 CNI 설정의 `eni` 섹션, 같은 필드에서는 Helm보다 우선)을 쓰세요. operator API limiter 기본값은 4 QPS, burst 20입니다.

알아둘 operator 플래그(cmdref `cilium-operator-aws`): `--aws-enable-prefix-delegation`, `--aws-release-excess-ips`, `--excess-ip-release-delay`(기본 180초), `--eni-gc-interval`(5분), `--eni-tags`, `--parallel-alloc-workers`(50), `--limit-ipam-api-qps`, `--limit-ipam-api-burst`, `--aws-max-results-per-call`.

### 할당 알고리즘

노드별 값(`CiliumNode.spec.ipam`): `min-allocate`, `pre-allocate`(0이면 8로 취급), `max-allocate`, `max-above-watermark`(agent 플래그나 Helm 키 없음. `CiliumNode`에 직접 또는 CNI 설정의 `ipam` 섹션에서 지정), `static-ip-tags`. `operator/pkg/ipam/nodemanager/node.go`의 공식:

```
deficit (needed) = max( preAllocate + used - available ,  minAllocate - available )
                   maxAllocate가 있으면 상한 적용;  하한 0
excess  (--aws-release-excess-ips일 때만)
                 = max( available - used - preAllocate - maxAboveWatermark , 0 )
                   (used가 작은 동안에는 available >= minAllocate + maxAboveWatermark 유지)
선택된 ENI에서 한 사이클의 할당량
                 = min( AvailableOnSubnet,
                        min( AvailableOnENI, needed + maxAboveWatermark + surgeAllocate ) )
   surgeAllocate = pendingPods - needed
```

계산 예: `preAllocate=8`, `minAllocate=16`, available 10, used 4인 노드의 deficit는 max(8 + 4 - 10, 16 - 10) = 6이므로 operator가 최소 6개를 더 할당합니다. 작은 인스턴스에서는 pre-allocate가 `min(8, (adapters - firstIndex) x (ipsPerENI - 1))`로 자동 하향됩니다. `max-allocate` 기본값은 인스턴스 한도 `(adapters - firstInterfaceIndex) x (ipv4PerENI - 1)`이고 prefix delegation에서는 16배가 됩니다. `usePrimaryAddress`를 쓰면 ENI마다 주소가 하나 늘어납니다.

스케줄링: deficit는 `CiliumNode`가 갱신될 때마다 평가되고 1분마다 전체 스캔합니다. 작업 큐는 필요 시 처리하되 초당 최대 1회, deficit가 가장 큰 노드부터이며 할당이 해제보다 먼저 실행됩니다.

IP의 출처: operator는 인덱스가 `first-interface-index` 이상이고 여유 용량과 서브넷 주소가 있는 연결된 ENI를 순회하고, 없으면 ENI를 새로 만듭니다. 서브넷 후보는 같은 VPC와 AZ이며 `subnet-ids`(우선) 또는 `subnet-tags`(모두 일치)로 좁히고 여유 주소가 가장 많은 서브넷을 고릅니다. 둘 다 없으면 노드 primary ENI의 서브넷, 같은 route table의 서브넷, VPC/AZ에서 가장 큰 서브넷 순입니다. 보안 그룹은 `spec.eni.security-groups`, 없으면 `security-group-tags`, 없으면 eth0의 그룹을 상속합니다. ENI 설명은 `Cilium-CNI (<instance-id>)`이고 클러스터 태그와 `--eni-tags`가 붙습니다. 호출하는 API: `CreateNetworkInterface`, `AttachNetworkInterface`, `ModifyNetworkInterfaceAttribute`(delete-on-termination, 기본 true), `AssignPrivateIpAddresses`.

### Prefix delegation

`eni.awsEnablePrefixDelegation=true`(노드 단위 opt-out: `eni.nodeSpec.disablePrefixDelegation`)는 operator가 보조 IP 대신 `/28` prefix(16주소)를 할당하게 해 ENI당 용량을 16배로 늘립니다. 소스 기준 제약:

- **Nitro 또는 bare-metal** 인스턴스 타입에서만 유효합니다.
- 혼합 불가: 어떤 ENI에든 보조 `/32` IP가 이미 있는 노드에서는 쓰이지 않습니다(primary ENI IP는 이 판정에서 제외).
- 할당은 `AssignENIPrefixes`를 개수 `ceil(needed / 16)`으로 호출합니다. 서브넷이 `InsufficientPrefixesInSubnet`을 반환하면 operator가 해당 노드에서 더 이상 prefix를 할당하지 않겠다고 로그를 남기고 `/32` 보조 IP로 되돌아갑니다.
- 서브넷에 연속된 빈 `/28` 블록이 필요하므로 조각난 서브넷은 주소보다 prefix가 먼저 바닥날 수 있습니다(AWS 쪽 동작이며 AWS prefix delegation 문서 참조).

### 해제, use-primary-address, IPv6

**해제**(IPv4 전용, `--aws-release-excess-ips=true` 필요): agent가 완전히 빈 CIDR을 `spec.ipam.pools.allocated`에서 제거하고, operator가 `--excess-ip-release-delay`(기본 180초)를 기다린 뒤 `UnassignPrivateIpAddresses`(`/32`) 또는 prefix 해제(`/28`)를 호출합니다. 해제로 ENI가 분리되거나 삭제되지는 **않으며** 오래된 ENI는 ENI GC(태그 `io.cilium/cilium-managed=true`, `io.cilium/cluster-name=<name>`)가 정리합니다. 1.19 방식의 `status.ipam.release-ips` 핸드셰이크는 레거시 CRD-allocator agent에만 해당합니다.

**`usePrimaryAddress`**: ENI의 primary private IP를 Pod에 줄 수 있게 합니다(ENI당 +1). **[1.21 pre-release]** operator 플래그 `--aws-use-primary-address`가 **제거**됩니다. `eni.nodeSpec.usePrimaryAddress=true`(agent 플래그 `--eni-use-primary-address`, `CiliumNode.spec.eni.use-primary-address`에 저장)를 쓰세요. 차트가 agent 쪽만 연결했으므로 Helm 사용자는 영향이 없습니다.

**IPv6 (1.20 beta, agent가 beta 경고를 로그로 남김)**: `ipam.mode=eni`, `eni.enabled=true`, `ipv6.enabled=true`. 노드마다 위임된 `/80` prefix를 정확히 하나 받으며 ENI 생성 시 또는 `AssignIpv6Addresses`로 할당되고 해제되지 않습니다. watermark가 없고 서브넷은 반드시 dual-stack이어야 하며 각 ENI에 primary IPv4가 필요하므로 IPv6 전용 서브넷은 지원되지 않습니다. upstream EKS 요구사항 페이지는 아직 ENI가 IPv4 전용이라고 적고 있으나 ENI 페이지와 런타임 beta 경고가 더 최신 근거입니다.

### ENI 주의점

Pod 밀도는 `(ENI 수 - firstIndex) x (ENI당 IP 수 - 1)`로 제한됩니다(prefix 사용 시 x16). 노드 ENI 보안 그룹을 Pod가 공유하며 노드 그룹별 `spec.eni.security-groups`로 구성할 수 있습니다. Cluster Mesh에서 cluster ID 128~255와 ENI를 함께 쓰면 알려진 policy drop 문제가 있습니다([Part 13](13-clustermesh-install-upgrade.md) 참조). 1.20에서 제거된 항목(1.19에는 존재): `CiliumNode.spec.eni.min-allocate`, `pre-allocate`, `max-above-watermark`, `instance-id`. 같은 값은 `spec.ipam` 아래에 있습니다. VPC CNI 위의 chaining은 별개 설계이므로 여기서 다루지 않습니다.

## Azure, AKS, Alibaba Cloud

**AKS.** Azure CNI Powered by Cilium은 관리형입니다. `ipam: delegated-plugin`, CNI 설정 `"ipam": {"type": "azure-ipam"}`, `local-router-ipv4: 169.254.23.0`이며 Cilium은 Pod IP를 할당하지 않습니다. BYOCNI 클러스터는 어떤 Cilium IPAM이든 쓸 수 있고, Helm `azure.enabled`는 BYOCNI와 호환되지 않으므로 `aksbyocni.enabled`를 씁니다.

**self-managed Azure (upstream `--ipam=azure`).** operator 플래그 `--azure-subscription-id`, `--azure-resource-group`(VMSS는 VMSS가 속한 resource group이며 틀리면 주소를 받지 못함), `--azure-user-assigned-identity-id`(resource ID가 아니라 client ID), `--azure-use-primary-address`. 인증은 DefaultAzureCredential 체인입니다. 노드별로 `azure.nodeSpec.azureInterfaceName`을 씁니다. 1.20에서 operator는 `status.azure.interfaces[]`에 새 `subnet{id,cidr}` 객체를 게시합니다(기존 flat `cidr`, `addresses[].subnet`은 deprecated). **[1.21 pre-release]** Azure가 ENI와 같은 공용 cloud multi-pool 프레임워크로 옮겨갑니다. `succeeded` 상태 주소가 모두 기본 pool의 host prefix가 되고, 초과 IP는 더 이상 해제되지 않으며, agent는 유효한 IPv4 서브넷 CIDR을 최대 5분 기다려 `--ipv4-native-routing-cidr`가 없으면 그 값을 native-routing CIDR로 씁니다.

**Alibaba Cloud.** `ipam.mode=alibabacloud`, `alibabacloud.enabled`, 노드별 `alibabacloud.nodeSpec.{vSwitches,vSwitchTags,securityGroups,securityGroupTags}`. CRD allocator를 쓰며 설치 가이드는 Terway/Flannel을 교체하고 `cilium-alibabacloud` secret을 사용합니다. 이 장은 여기까지만 다루며 Alibaba 한도와 IPv6 동작은 검토하지 않았습니다.

## Pod IP를 넘어서: LB IPAM, Node IPAM, CiliumCIDRGroup

### LB IPAM과 `CiliumLoadBalancerIPPool`

LB IPAM은 `type: LoadBalancer` Service의 주소를 할당합니다. operator(`operator/pkg/lbipam`)에서 동작하고 항상 빌드에 포함되어 있으며(Helm `enableLBIPAM`, 기본 true) 첫 pool이 생길 때까지 휴면 상태입니다. **할당만** 합니다. 주소에 도달하려면 BGP Control Plane(`loadBalancerClass: io.cilium/bgp-control-plane`)이나 L2 Announcements(`io.cilium/l2-announcer`)가 따로 필요하며 [Part 11](11-bgp-lb-egress-edge.md)에서 다룹니다.

> **보안 범위.** LB IPAM pool은 사설 대역이어야 합니다. BGP나 라우팅 연동 없이는 VPC 안에서 LB IPAM VIP에 도달할 수 없으므로 EKS에서는 내부 AWS 로드 밸런서를 쓰고, 공개 경로는 항상 CloudFront에서 내부 ALB/NLB로 가는 것 하나입니다. LB IPAM은 BGP나 L2 announcement를 쓰는 온프레미스/하이브리드 사이트에 맞습니다. upstream 예제는 `20.0.0.0/8` 같은 공인처럼 보이는 대역을 쓰지만 이 장은 RFC 1918 대역을 사용합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: blue-pool
spec:
  blocks:
  - cidr: 10.0.10.0/24
  - start: 10.0.20.100        # start와 stop은 하나의 block. 같은 목록 항목에 둘 것
    stop: 10.0.20.200
  serviceSelector:
    matchLabels:
      color: blue
  allowFirstLastIPs: "No"     # 기본 "Yes". "No"는 network/broadcast 예약. cidr block에만 적용
  # disabled: true            # 신규 할당 중지, 기존 할당 유지
```

사실 관계: API는 `cilium.io/v2`(`v2alpha1`은 1.19.8에서 처음 deprecated로 표시됨), cluster-scoped, 짧은 이름 `ippools`, `ippool`, `lbippool`, `lbippools`, 출력 열은 Disabled, Conflicting, IPs Available입니다. `serviceSelector`는 레이블과 synthetic 레이블 `io.kubernetes.service.namespace`, `io.kubernetes.service.name`을 받습니다. pool이 겹치면 나중 것이 Conflicting(condition `cilium.io/PoolConflict`)으로 표시되고 아무것도 할당하지 않습니다. pool condition에는 `cilium.io/IPsTotal`, `IPsAvailable`, `IPsUsed`도 있습니다. pool을 수정하면 기존 Service IP가 재할당될 수 있으므로(upstream issue 40358) 새 pool을 추가하거나 `disabled: true`를 쓰는 편이 안전합니다.

Service 처리: `loadBalancerClass`가 없는 `LoadBalancer` Service는 Helm `defaultLBServiceIPAM`이 `none`이 아니면 LB IPAM이 처리합니다(값: `lbipam`, `nodeipam`, `none`). 알 수 없는 class는 무시됩니다. Service condition `cilium.io/IPAMRequestSatisfied`는 이유 `satisfied` 또는 `no_pool`을 보고합니다. 주소 family는 기본 single-stack(둘 다 켜져 있으면 IPv4), `PreferDualStack`은 둘 다 시도하고, `RequireDualStack`은 family 하나가 꺼져 있으면 충족되지 않습니다.

특정 주소 요청: 어노테이션 `lbipam.cilium.io/ips: "10.0.10.100,10.0.10.101"`(기존 `.spec.loadBalancerIP`는 deprecated). pool의 `serviceSelector`는 그대로 적용되며 `allowFirstLastIPs: "No"`인 pool의 첫/마지막 주소는 요청하면 안 됩니다.

Service 간 IP 공유:

```yaml
metadata:
  annotations:
    lbipam.cilium.io/sharing-key: "web-vip"
    lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"   # 또는 "*"
```

1.20에서는 같은 sharing key의 두 Service가 port/protocol이 충돌하지 않으면 IP 하나를 공유하고, 충돌하면 같은 key 집합의 다른 IP를 받습니다. **[1.21 pre-release]** 호환성 검사가 더 엄격해져 Service들이 같은 `externalTrafficPolicy`를 가져야 하며 `Local`이면 같은 Pod를 선택해야 합니다. 새 어노테이션 `lbipam.cilium.io/sharing-permit-different-pods: "true"`는 이 안전 검사를 끄며 Cilium BGP나 L2 announcement와는 안전하지 않습니다(L4를 인식하지 못해 서로 다른 노드가 같은 IP에 응답할 수 있음).

메트릭(문서상 접두사는 `cilium_`이지만 controller가 operator에서 돌고 operator registry가 namespace를 덮어쓸 수 있어 런타임 접두사는 `cilium_operator_lbipam_*`일 수 있습니다. 런타임에서 확인하지 못했으니 실제 scrape 결과로 이름을 확인하세요): `cilium_lbipam_conflicting_pools`, `cilium_lbipam_ips_available{pool}`, `cilium_lbipam_ips_used{pool}`, `cilium_lbipam_services_matching`, `cilium_lbipam_services_unsatisfied`.

데이터패스 참고(1.19): LB IPAM 또는 ClusterIP 주소로 향하는 north-south TCP/UDP는 포트가 프로비저닝된 Service와 맞지 않으면 드롭됩니다.

### Node IPAM

`nodeIPAM.enabled=true`(기본 false, `enable-node-ipam` 설정)를 켜면 `loadBalancerClass: io.cilium/node`(또는 `defaultLBServiceIPAM: nodeipam`)인 Service가 노드 주소를 load balancer ingress로 게시합니다. 기존 설치에서 켠 뒤에는 operator를 재시작하세요(`kubectl -n kube-system rollout restart deployment/cilium-operator`). operator는 선택된 각 노드의 ExternalIP가 있으면 그것을, 없으면 InternalIP를 `ipFamilies`에 맞춰 `status.loadBalancer.ingress`에 채웁니다. `externalTrafficPolicy: Cluster`는 모든 노드, `Local`은 선택된 Pod를 가진 노드를 씁니다(EndpointSlice 필요, Cilium Ingress/Gateway의 dummy endpoint와는 사용 불가). 레이블 `node.kubernetes.io/exclude-from-external-load-balancers` 또는 taint `ToBeDeletedByClusterAutoscaler`가 있는 노드는 제외되며 Service 어노테이션 `io.cilium.nodeipam/match-node-labels`로 레이블 기준 노드 제한이 가능합니다.

Node IPAM은 노드 주소를 서비스 주소로 게시하므로 노드 IP가 사설일 때만 쓰세요. AWS에서 공개 노출 수단이 아닙니다.

### CiliumCIDRGroup

`CiliumCIDRGroup`은 CIDR 목록(`spec.externalCIDRs`)에 이름을 붙여 정책이 CIDR을 직접 나열하는 대신 `cidrGroupRef` 또는 `cidrGroupSelector`로 참조하게 합니다. 크기와 상관없이 그룹당 security identity가 하나라 큰 목록에서 확장성이 좋고 Hubble 플로우에 그룹 이름이 표시됩니다. cluster-scoped이며 짧은 이름은 `ccg`입니다. `cilium.io/v2`를 쓰세요. `v2alpha1`은 deprecated인데 일부 upstream 예제에는 아직 남아 있습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: corp-ranges
  labels:
    tier: internal
spec:
  externalCIDRs:
  - 10.30.0.0/16
  - 192.168.100.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-corp
spec:
  endpointSelector:
    matchLabels:
      app: batch
  egress:
  - toCIDRSet:
    - cidrGroupRef: corp-ranges
```

## 운영: 점검, 메트릭, 업그레이드

```bash
# 노드가 소유한 범위 보기
kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs
kubectl get ciliumnode <node> -o yaml        # .spec.ipam, .status.ipam, .status.eni.enis
kubectl get ciliumpodippools                 # multi-pool. 짧은 이름 cpip
kubectl get ippools                          # LB IPAM pool
kubectl -n kube-system logs deploy/cilium-operator | grep -i ipam
```

**agent 메트릭:** `cilium_ipam_capacity{family,cidr}`(`cidr` 레이블은 cluster-pool/kubernetes 모드에서는 노드 CIDR, 그 외에는 비어 있음), `cilium_ipam_events_total{action,family}`, `cilium_ip_addresses{family}`.

**operator 메트릭**(접두사 `cilium_operator_`, `operator.prometheus.enabled`로 활성화): `ipam_available_ips{target_node}`, `ipam_used_ips`, `ipam_needed_ips`, `ipam_ip_allocation_ops{subnet_id}`, `ipam_ip_release_ops`, `ipam_interface_creation_ops`, `ipam_interface_candidates`, `ipam_empty_interface_slots`, `ipam_available_ips_per_subnet{subnet_id,availability_zone}`, `ipam_nodes{category=total|in-deficit|at-capacity}`, `ipam_resync_total`, `ipam_allocation_duration_seconds`, `ipam_release_duration_seconds`, `ipam_background_sync_duration_seconds`. upstream 메트릭 표는 오래되어 `interface_candidates`, `empty_interface_slots`, `available_ips_per_subnet`, `background_sync_duration_seconds`가 빠져 있으며 위 목록은 소스를 따랐습니다. 클라우드 API 호출 메트릭은 `ipam_` 아래에 있지 않습니다. subsystem이 클라우드 이름이므로 AWS에서는 `cilium_operator_ec2_api_duration_seconds{operation,response_code}`와 `cilium_operator_ec2_api_rate_limit_duration_seconds{operation}`입니다(Azure와 Alibaba Cloud는 각자의 subsystem 사용). 1.20에서 `ipam_ips`, `ipam_available_interfaces`가 제거되었습니다.

권장 알림: `ipam_nodes{category="at-capacity"} > 0`, `ipam_nodes{category="in-deficit"}` 증가, AZ별 `ipam_available_ips_per_subnet`이 임계값 미만, `ec2_api_rate_limit_duration_seconds` 지속, `lbipam_conflicting_pools > 0`.

**업그레이드 참고.** ENI는 1.19에서 1.20으로의 롤링 업그레이드가 지원됩니다. **[1.21 pre-release]** operator ClusterRole에 `ciliumpodippools` list/patch 권한이 추가되고(storage 버전 마이그레이션) operator 플래그 `--aws-use-primary-address`가 제거됩니다. Helm이 아니라 operator에 직접 지정했다면 업그레이드 전에 `eni.nodeSpec.usePrimaryAddress=true`로 바꾸세요.

## 실습

> 이 실습은 이번 검토에서 실제 클러스터에 대해 실행하지 않았고 upstream 소스와 문서로 검증했습니다. 출력 형식이 동일하다고 기대하지 말고 설명된 기대 동작과 비교하세요.

### 실습 1: Cluster-pool 크기 산정과 고갈 (kind)

사전 조건: worker 2개의 kind 클러스터, 기본 `cluster-pool`로 Helm 설치한 Cilium, kubectl, Helm.

1. 일부러 작은 노드 mask로 설치합니다.

   ```bash
   helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
     --set ipam.mode=cluster-pool \
     --set ipam.operator.clusterPoolIPv4PodCIDRList='{10.244.0.0/16}' \
     --set ipam.operator.clusterPoolIPv4MaskSize=28
   ```
2. 노드별 블록을 확인합니다: `kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs`. 각 노드가 `/28`(16주소)을 소유합니다.
3. `nodeSelector`로 Deployment를 worker 하나에 고정하고 replica를 20으로 늘립니다.
4. 기대 결과: 처음 Pod들은 실행되고, 노드의 사용 가능한 주소(16에서 network, broadcast, router/health/ingress를 뺀 수)를 다 쓰면 나머지는 CNI 할당 오류와 함께 `ContainerCreating`에 머뭅니다. `cilium-dbg status`에는 노드 범위가 모두 할당된 것으로 표시됩니다.
5. 크기 산정 공식으로 예상 한계를 계산해 관찰한 개수와 비교합니다.

정리: Deployment 삭제. 롤백: mask는 실행 중 클러스터에서 변경 불가이므로 값을 고치지 말고 클러스터를 다시 만드세요.

### 실습 2: Multi-pool 선택 (kind)

사전 조건: kind, `ipam.mode=multi-pool`, `kubeProxyReplacement=true`, `bpf.masquerade=true`와 pool 설치 절의 `default`, `mars` pool이 있는 Cilium 1.20.2.

1. namespace 두 개를 만들고 하나에 `kubectl annotate namespace ns-a ipam.cilium.io/ip-pool=mars`를 적용합니다.
2. 각 namespace에 Pod를 띄우고 `kubectl get pods -A -o wide`로 확인합니다. 기대 결과: 어노테이션이 있는 namespace의 Pod는 `10.20.0.0/16`, 다른 쪽은 `10.10.0.0/16` 주소를 받습니다.
3. 어노테이션이 없는 namespace에서 Pod 어노테이션 `ipam.cilium.io/ip-pool: mars`를 가진 Pod를 띄웁니다. 기대 결과: Pod 어노테이션이 namespace 기본보다 우선합니다.
4. 세 번째 namespace에 일치하는 pool 없이 `ipam.cilium.io/require-pool-match: "true"`를 붙이고 Pod를 띄웁니다. 기대 결과: pool 일치 오류와 함께 pending 상태가 됩니다.
5. `kubectl get ciliumnode <n> -o yaml`에서 `spec.ipam.pools.requested`와 `allocated`를 읽고, `cilium-dbg status --all-addresses`에서 `pool/ip` 항목을 확인합니다.

정리: namespace와 필요하면 클러스터 삭제.

### 실습 3: Cluster-pool에서 multi-pool 마이그레이션 (kind)

사전 조건: cluster-pool로 1.20.2가 설치되고 Pod가 실행 중인 kind 클러스터. 단방향이므로 일회용 클러스터를 쓰세요.

1. `kubectl get ciliumnodes -o yaml | grep -A3 podCIDRs`로 현재 값을 기록합니다.
2. 기록한 CIDR을 포함하고 mask가 같은 기본 pool로 마이그레이션 절의 Helm upgrade를 실행합니다.
3. 각 노드의 PodCIDR이 `spec.ipam.pools.allocated`에 나타날 때까지 기다립니다.
4. agent를 재시작합니다(`kubectl -n kube-system rollout restart ds/cilium`). 기대 결과: 기존 Pod는 주소를 유지하고 복원된 것으로 표시되며 롤아웃 중에도 노드 간 Pod 통신이 유지됩니다.

롤백: 지원되지 않음. 클러스터를 다시 만드세요.

### 실습 4: L2 announcement와 LB IPAM (kind, 사설 대역)

사전 조건: `l2announcements.enabled=true`, `kubeProxyReplacement=true`인 kind. kind Docker 네트워크 안의 비어 있는 사설(RFC 1918) 대역을 고르세요.

1. 작은 `start`/`stop` block과 `serviceSelector`를 가진 `CiliumLoadBalancerIPPool`을 적용합니다.
2. L2 announcement 정책(Part 11 참조)과 레이블이 일치하는 `LoadBalancer` Service를 적용합니다.
3. 기대 결과: `kubectl get ippools`의 사용 가능 IP가 줄고, Service가 block에서 external IP를 받으며 condition `cilium.io/IPAMRequestSatisfied`가 `satisfied`를 보고합니다.
4. block이 겹치는 두 번째 pool을 만듭니다. 기대 결과: Conflicting으로 표시되고 아무것도 할당하지 않습니다.
5. 첫 pool에 `disabled: true`를 설정하고 다른 Service를 만듭니다. 기대 결과: 새 할당은 없고 기존 Service는 IP를 유지합니다.

정리: Service, pool, 정책 삭제.

### 실습 5: EKS ENI 모드와 prefix delegation (샌드박스 계정)

사전 조건: private subnet만 있는 VPC의 일회용 EKS 클러스터, Nitro 인스턴스 타입 노드, 노드에 공인 IP 없음, 노드 보안 그룹은 VPC/클러스터 보안 그룹 참조만 허용(`0.0.0.0/0`, `::/0` 금지), 설치 및 노드 준비 절의 operator IAM, 대상 샌드박스 계정용 AWS CLI profile.

1. 노드 그룹에 taint `node.cilium.io/agent-not-ready=true:NoExecute`를 두어 생성합니다. VPC CNI는 비활성화합니다(관리형 add-on을 설치하지 않거나 `aws-node`에 존재하지 않는 node selector를 패치).
2. `eni.enabled=true`, `eni.awsEnablePrefixDelegation=true`, `eni.awsReleaseExcessIPs=true`, `eni.iamRole`과 Helm 값 절의 나머지 값으로 Cilium을 설치합니다.
3. 인벤토리를 확인합니다: `kubectl get ciliumnode <n> -o jsonpath='{.status.eni.enis}'`가 prefix를 가진 ENI를 나열하고 `aws ec2 describe-network-interfaces --filters Name=description,Values='Cilium-CNI*'`가 같은 ENI를 반환합니다. 기대 결과: `spec.ipam.pools.allocated`에 `/28` 블록이 있습니다.
4. 노드당 16개를 넘도록 Deployment를 늘립니다. 기대 결과: operator가 prefix를 추가 할당하고 `cilium_operator_ipam_available_ips`가 `used + preAllocate` 위에 유지됩니다.
5. 다시 줄이고 180초 넘게 기다립니다. 기대 결과: 사용하지 않는 prefix가 해제되고 ENI는 연결된 채 남습니다.

정리: replica 0으로 줄이고 Cilium 삭제, 노드 그룹과 남은 `Cilium-CNI` ENI 삭제(ENI GC가 켜져 있으면 태그된 고아 ENI를 정리). 롤백: 새 노드 그룹에서 VPC CNI add-on을 다시 켜세요. 같은 실행 중 노드에서 IPAM을 전환하지 마세요.

### 실습 6: Node IPAM (kind)

사전 조건: `nodeIPAM.enabled=true`로 설치한 kind의 Cilium(켠 뒤 operator 재시작).

1. `loadBalancerClass: io.cilium/node`인 `LoadBalancer` Service를 만듭니다.
2. 기대 결과: `status.loadBalancer.ingress`에 노드 InternalIP가 나열됩니다(kind 노드에는 ExternalIP가 없음).
3. 노드 하나에 `node.kubernetes.io/exclude-from-external-load-balancers` 레이블을 붙입니다. 기대 결과: 그 노드 주소가 목록에서 빠집니다.

정리: Service와 레이블 삭제.

## 버전 차이

| 주제 | 1.18 | 1.19 | 1.20 | 1.21 pre-release |
|---|---|---|---|---|
| Multi-pool 성숙도 | Beta 배너 | 배너 제거 | stable | stable |
| Pool 선택 | `ip-pool` 어노테이션만 | + `ipv4-pool`/`ipv6-pool` 어노테이션과 `podSelector`/`namespaceSelector`(1.18.14에 이미 있음). `require-pool-match`, `skip-masquerade`, `--only-masquerade-default-pool`은 1.19에서 처음 등장 | + `allowFirstIP`/`allowLastIP` | 동일 + `pool[].reservedRanges` |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | v2 storage, v2alpha1 deprecated, `cidrs` 최대 32 |
| cluster-pool에서 multi-pool 마이그레이션 | 없음 | 없음 | 신규(`enable-cluster-pool-to-multi-pool-migration`) | 동일 |
| ENI agent 모델 | CRD allocator | CRD allocator | multi-pool allocator, IPv6 beta(`/80`), `pools.allocated`로 해제 | Azure와 공유하는 cloud multi-pool 프레임워크 |
| ENI 노드별 Helm(`eni.nodeSpec`, `ipam.nodeSpec`) | CNI conf만 | 추가 | 동일 | 동일 |
| ENI masquerade 기본값 | `enableIPv4Masquerade` false(신규) | | | `enableIPv6Masquerade` false(신규) |
| ENI IAM | + `DescribeRouteTables` | | | + 선택적 `GetSecurityGroupsForVpc`, `DescribeManagedPrefixLists`, `GetManagedPrefixListEntries` |
| operator `--aws-use-primary-address` | 있음 | 있음 | 있음 | **제거** |
| `CiliumNode.spec.eni.{min,pre}-allocate`, `max-above-watermark`, `instance-id` | 있음 | 있음 | 제거 | 제거 |
| operator IPAM 메트릭 | 노드별 `available/used/needed_ips`, `interface_candidates` 이미 존재 | 동일 | `ipam_ips`, `ipam_available_interfaces` 제거 | |
| Azure IPAM | CRD allocator | CRD allocator | `status.azure.interfaces[].subnet` | multi-pool 프로토콜, 초과 해제 없음 |
| `CiliumLoadBalancerIPPool` API | v2 | v2alpha1 deprecated | v2 | v2 |
| `CiliumCIDRGroup` API | v2alpha1 deprecated | v2 | v2 | v2 |
| LB IPAM 공유 | key + cross-namespace | | port 충돌 규칙 | 더 엄격한 호환성 + `sharing-permit-different-pods` |

## 트러블슈팅

증상: Pod가 `ContainerCreating`에 머물고 `kubectl describe pod`에 `unable to allocate IP via local cilium agent`가 표시됩니다.

| 모드 | 가능한 원인 | 확인 | 조치 |
|---|---|---|---|
| cluster-pool / kubernetes | 노드 범위 소진(`IPAM: IPv4: N/M allocated`) | `cilium-dbg status`, `--all-addresses` | 밀도 축소, 노드 추가. mask는 변경 불가이므로 더 큰 범위는 새 pool/클러스터 계획 |
| cluster-pool | pool 소진 | `status.ipam.operator-status.error` = `allocator full` | 목록에 CIDR 추가(기존 항목은 수정 금지) |
| cluster-pool | agent가 시작하지 않음 | CiliumNode에 `spec.ipam.podCIDRs` 없음 | operator 로그, CIDR 중복, 충돌 오류 확인 |
| kubernetes | 노드 PodCIDR 없음 | `kubectl get node -o jsonpath='{.spec.podCIDRs}'` | `--allocate-node-cidrs` 활성화 |
| multi-pool | `needed`가 pool 여유를 초과 | `operator-status.error`: `failed to allocate ipv4 address for node ... from pool ...` | pool에 CIDR 추가 또는 pool 추가 |
| multi-pool | pool 없음 또는 아직 sync 안 됨 | `kubectl get cpip`, 오류 `ErrPoolNotReadyYet`, `ErrManagerPoolsNotSynced` | Pod보다 먼저 pool 생성, 기본 pool 존재 확인 |
| multi-pool | pool 두 개가 일치 | 오류 `multiple CiliumPodIPPools match pod` | selector를 좁힘 |
| multi-pool | `require-pool-match` | Pod나 namespace의 어노테이션 | 일치하는 pool 또는 어노테이션 추가 |
| ENI | 인스턴스 ENI/IP 한도 | `ipam_nodes{category="at-capacity"}` | 큰 인스턴스, prefix delegation |
| ENI | 서브넷 IP 소진 | `ipam_available_ips_per_subnet` | 태그/ID로 서브넷 추가. PD는 조각화 확인(`/32` fallback) |
| ENI | EC2 throttling | `ec2_api_rate_limit_duration_seconds` | `externalAPILimitQPS` / `externalAPILimitBurstSize` 조정 |
| ENI | IAM 액션 누락 | operator 로그 | 설치 및 노드 준비 절의 액션 추가 |
| ENI | OS가 보조 IP를 제거 | NetworkManager / systemd-networkd 로그 | `eth0`을 제외한 `eth*`를 관리 대상에서 제외 |
| 공통 | CNI 크래시로 IP 누수 | endpoint에는 없는데 점유 중 | 10분 expiration 대기, agent 재시작으로 정합 |

LB IPAM: Service에 external IP가 없으면 pool의 Conflicting 여부, `cilium.io/IPAMRequestSatisfied` condition, `serviceSelector` 일치 여부, 그리고 BGP나 L2가 실제로 주소를 광고하는지 확인하세요. IPAM 모드는 토글이 아닙니다. 변경 후 실행 중인 모드와 Helm 값이 어긋난다면 ConfigMap을 고칠 때가 아니라 멈추고 마이그레이션을 계획할 때입니다.

## 검증 한계와 출처

이 실습은 이번 검토에서 실제 클러스터에 대해 실행하지 않았습니다. 명령, 필드 이름, 기본값, 공식, 플래그는 표시된 태그의 Cilium 소스와 문서로 확인했습니다. 확인하지 못한 항목: prefix 할당/해제용 IAM 액션 이름(upstream은 private-IP 액션만 나열), `only-masquerade-default-pool`의 Helm 경로(`extraConfig` 사용), Alibaba Cloud 한도, 그리고 pre-release 태그 v1.21.0-pre.3에서 가져온 1.21 항목. Azure, `reservedRanges`, cloud multi-pool 프레임워크에 대한 버전 표기는 GA 전에 바뀔 수 있습니다. ENI 예제는 private subnet 샌드박스를 대상으로 하며 어떤 예제도 보안 그룹을 인터넷에 열거나, 인터넷 노출 로드 밸런서를 만들거나, 컴퓨트에 공인 IP를 붙이지 않습니다.

출처(별도 표기 없으면 v1.20.2):

- IPAM concepts: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst
- Cluster scope: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst
- Multi-pool: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst
- Cluster-pool에서 multi-pool로 마이그레이션: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst
- AWS ENI: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst
- LB IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst
- Node IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst
- 어노테이션(`ip-pool` 키): https://github.com/cilium/cilium/blob/v1.20.2/pkg/annotation/k8s.go
- 노드 CIDR allocator: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/cidrset/cidr_set.go
- Multi-pool manager: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/multipool_manager.go
- ENI node manager 공식: https://github.com/cilium/cilium/blob/v1.20.2/operator/pkg/ipam/nodemanager/node.go
- 메트릭: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/observability/metrics.rst
- [1.21 pre-release] multi-pool과 `reservedRanges`: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/concepts/ipam/multi-pool.rst
- [1.21 pre-release] 업그레이드 노트: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc
- [1.21 pre-release] LB IPAM 공유: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst
- AWS, EKS Hybrid Nodes CNI: https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html

## 퀴즈

[Part 10 퀴즈](../../quizzes/networking/cilium/10-ipam-deep-dive-quiz.md)로 확인해 보세요.
