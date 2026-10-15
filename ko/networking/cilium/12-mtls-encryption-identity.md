# Part 12: mTLS, 투명 암호화, 그리고 Identity

> **검토 기준**: Cilium 1.20.2 (안정, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. **[1.21 pre-release]** 표시 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다.
> **마지막 업데이트**: 2026년 10월 15일

Cilium 보안 모델에는 쉽게 혼동되는 세 계층이 있습니다. **Identity와 정책**은 IP가 아니라 레이블을 기준으로 누가 누구와 통신할 수 있는지 결정합니다. **투명 암호화**(WireGuard, IPsec)는 노드 사이 와이어 상의 바이트를 보호합니다. **워크로드 mTLS**(ztunnel)는 암호화된 채널을 워크로드 identity에 묶습니다. 이 장은 각 계층을 메커니즘부터 설명하고, 제거된 Mutual Authentication, 서비스 메시 옵션, Hubble/Tetragon, 인증서 관리를 다룹니다.

관련 장: [eBPF 데이터패스 내부](08-ebpf-datapath-internals.md), [오버레이와 네이티브 라우팅](09-overlay-native-routing.md)(터널/MTU), [IPAM](10-ipam-deep-dive.md), [BGP, LB, Egress](11-bgp-lb-egress-edge.md), [ClusterMesh, 설치, 업그레이드](13-clustermesh-install-upgrade.md). 정책 기초는 [IPAM 및 네트워크 정책](04-ipam-policy.md), 가시성 입문은 [보안 및 가시성](06-security-visibility.md)에 있습니다.

## 성숙도와 타임라인 요약

| 기능 | 1.18 | 1.19 | 1.20 (stable) | 1.21 pre-release |
|---|---|---|---|---|
| Mutual Authentication (SPIFFE/SPIRE, `authentication.mode: required`) | Beta | Beta, `authentication.enabled` 기본값 false | **Deprecated** (문서 제목은 여전히 "Beta") | **Removed** |
| ztunnel 투명 암호화 (`encryption.type=ztunnel`) | - | Beta (도입) | Beta, `ca.type` 추가 | Beta |
| WireGuard | Stable | Stable | Stable | Stable |
| IPsec | Stable | Stable | Stable | Stable |
| WireGuard `encryption.nodeEncryption` | 확인 안 함 | 확인 안 함 | Beta | **Deprecated, 1.22에서 제거** |
| Double Write identity 마이그레이션 | 문서화됨 | 문서화됨 | 문서화됨 | `cilium-dbg preflight migrate-identity`가 이것으로 대체되며 deprecated |
| `identityManagementMode` | 확인 안 함 | 확인 안 함 | Beta | Beta |
| CiliumEndpointSlice | 확인 안 함 | 확인 안 함 | Beta | Beta |
| Kubernetes ClusterNetworkPolicy 지원 | - | - | 신규, alpha API (v1alpha2) | alpha |

Mutual Authentication 행이 가장 자주 잘못 인용됩니다. 기록상 정확한 서술은 다음과 같습니다.

- 1.18, 1.19, 1.20에서 **Beta**였습니다(1.20 문서 페이지 제목도 "Mutual Authentication (Beta)").
- **1.20에서 deprecated**되었습니다. 1.20 업그레이드 노트는 "now deprecated and will be removed in a future version"이라 하고 ztunnel을 대안으로 안내합니다.
- **1.21에서 제거**되었습니다. 1.21 업그레이드 노트는 "has been removed after deprecation"이라 하며 업그레이드 전에 관련 설정을 제거하라고 합니다.
- 정책 API의 `authentication` 필드는 CRD 호환을 위해 **남아 있지만 1.21에서는 사용되지 않습니다**.

## Identity 모델

### 레이블에서 숫자 identity로

Cilium은 IP 주소에 정책을 적용하지 않습니다. 모든 endpoint(Pod)는 identity-relevant 레이블로부터 도출된 숫자 **security identity**를 받습니다. 레이블 집합이 같은 endpoint는 하나의 ID를 공유하므로, Deployment의 모든 replica가 정책 맵 항목 하나로 처리되고 Pod IP가 바뀌어도 정책 판단이 유지됩니다.

```
Pod 레이블 (k8s:app=web, k8s:io.kubernetes.pod.namespace=shop, ...)
        |  identity-relevant 레이블로 필터링
        v
레이블 집합  -->  allocator (CRD 또는 kvstore)  -->  숫자 identity (예: 31337)
        |
        +--> CiliumEndpoint.status.identity (게시)
        +--> ipcache:  podIP -> identity   (모든 노드가 학습)
        +--> 출발 노드가 패킷에 identity를 표시 (터널 메타데이터)
                또는 도착 노드가 ipcache로 srcIP를 해석
        +--> 도착 노드: 정책 맵 조회 (로컬 endpoint, 원격 identity, 포트, 프로토콜)
```

도착 측 조회 키는 로컬 endpoint, 원격 identity, 포트, 프로토콜입니다. identity는 패킷과 함께 이동하거나(오버레이의 터널 메타데이터), 네이티브 라우팅에서는 ipcache로 출발 IP에서 복원합니다. 그래서 오래되었거나 빠진 ipcache 항목은 정책 증상으로 나타납니다.

### 32비트 숫자 identity 레이아웃

scope는 비트 24-31에 있습니다.

| Scope | 값 | 용도 |
|---|---|---|
| Global | 0 | CRD/kvstore allocator가 할당한 identity. 비트 0-23을 identity와 cluster ID가 나눠 사용 |
| Local | `1<<24` | 한 노드에만 존재하는 identity: CIDR, FQDN에서 파생 |
| Remote-node | `2<<24` | 노드 기반 정책 선택에 쓰는 노드 identity |

ClusterMesh에서는 하위 24비트를 identity와 cluster ID가 공유합니다. `max-connected-clusters`가 255이면 identity 16비트와 cluster ID 8비트, 511이면 15비트와 9비트입니다. 256 미만은 예약됩니다(`MinimalIdentity=256`). 상수는 v1.21.0-pre.3의 `pkg/identity/numericidentity.go`에 있습니다. ClusterMesh 규모 산정은 [Part 13](13-clustermesh-install-upgrade.md)을 보세요.

### Reserved identity와 well-known identity

데이터패스 상수 기준 reserved identity(`pkg/datapath/types/types_generated.go`, v1.21.0-pre.3)입니다.

| ID | 이름 | 의미 |
|---|---|---|
| 0 | unknown | 해석되지 않은 identity |
| 1 | host | 로컬 노드 |
| 2 | world | 클러스터 밖 전체 (`0.0.0.0/0`의 CIDR identity이기도 함) |
| 3 | unmanaged | Cilium이 관리하지 않는 endpoint |
| 4 | health | Cilium health endpoint |
| 5 | init | 레이블이 아직 알려지지 않은 endpoint (Pod 시작 단계) |
| 6 | remote-node | 다른 클러스터 노드 |
| 7 | kube-apiserver | Kubernetes API 서버 |
| 8 | ingress | Cilium이 관리하는 ingress/Envoy |
| 9 / 10 | world-ipv4 / world-ipv6 | world의 주소 패밀리 분리 |
| 11-14 | 집계 identity (cluster, clustermesh, world, remote-node) | 정책 맵 집계용이며 트래픽에는 적용되지 않음 |

업스트림 용어집 페이지는 0-8만 나열하므로 9, 10은 소스에서만 확인됩니다. kvstore나 CRD 왕복 없이 존재하는 well-known identity는 `kube-dns`(102), EKS의 `kube-dns`(103), `coredns`(104), `cilium-operator`(105), EKS의 `coredns`(106)입니다(용어집과 `numericidentity.go`). EKS에서는 기본 DNS Pod가 고정 ID를 받는다는 점이 중요합니다.

기억할 동작: Pod는 레이블이 해석될 때까지 `reserved:init`에 있습니다. backend에 도달한 north-south Service 트래픽은 터널 모드에서 `reserved:world`로 도착하고, 네이티브 라우팅에서는 backend가 있는 노드에 도달하면 `world`, 아니면 `remote-node`입니다(`fromEntities: cluster`가 이를 매칭하는 이유). `Documentation/security/policy/caveats.rst`를 보세요.

### Identity-relevant 레이블과 identity churn

기본적으로 제외 목록(`io.kubernetes`, `kubernetes.io`, StatefulSet pod-name, `pod-template-hash`, `controller-revision-hash`, `annotation.*`, `topology.kubernetes.io` 등)을 뺀 모든 레이블이 identity에 쓰입니다. 패턴은 레이블 앞부분에 고정된 정규식입니다.

- **포함** 패턴을 하나라도 추가하면 allow-list 모드로 바뀌고 `reserved:`, Pod 네임스페이스, 네임스페이스 레이블, `policy.cluster`, 서비스 어카운트, `app.kubernetes.io`가 자동으로 추가됩니다.
- Helm `labels:`는 기본값에 **추가**됩니다. 목록을 정확히 덮어쓰려면 `--label-prefix-file`을 사용합니다(agent 플래그 `--labels`, `--label-prefix-file`).
- 기존 identity는 agent를 재시작하기 전까지 바뀌지 않으며, 이후 operator가 오래된 identity를 정리합니다.
- 릴리스마다 또는 Pod마다 바뀌는 레이블(빌드 SHA, 타임스탬프)은 값마다 identity를 만듭니다. identity, ipcache 항목, 정책 맵 항목이 늘어나므로 이런 레이블은 identity에서 제외하세요.

출처: `Documentation/operations/performance/scalability/identity-relevant-labels.rst`.

### 할당 모드

| Helm `identityAllocationMode` | 저장소 | 비고 |
|---|---|---|
| `crd` (차트 기본값) | `CiliumIdentity` (cilium.io/v2, cluster-scoped) | 외부 의존성 없음 |
| `kvstore` | etcd | 이미 etcd를 운영하는 대규모 클러스터 |
| `doublewrite-readkvstore` | 둘 다 쓰고 kvstore에서 읽음 | 마이그레이션 단계 |
| `doublewrite-readcrd` | 둘 다 쓰고 CRD에서 읽음 | 마이그레이션 단계 |

작성 시 함정: **agent 플래그** 기본값은 `kvstore`이고 **Helm 차트**는 `crd`로 설정합니다. 항상 `cilium-agent --help`가 아니라 ConfigMap의 실효 값을 확인하세요.

**Double Write 마이그레이션(beta)**은 identity 공백 없이 백엔드를 옮깁니다. kvstore에서 CRD로는 `doublewrite-readkvstore`, `doublewrite-readcrd`, `crd` 순서입니다. Operator를 먼저, Agent를 나중에 배포합니다(마지막 `crd`로 돌아가는 단계에서는 업그레이드 가이드대로 Agent를 먼저, Operator를 나중에). 순서는 되돌릴 수 있습니다. 수렴은 operator gauge `doublewrite_{crd,kvstore,crd_only,kvstore_only}_identities`로 관찰하며, 노출 이름은 `cilium_operator_doublewrite_crd_identities`, `cilium_operator_doublewrite_kvstore_identities`, `cilium_operator_doublewrite_crd_only_identities`, `cilium_operator_doublewrite_kvstore_only_identities`입니다(v1.20.2 `operator/doublewrite/metrics.go:13-33`, `Documentation/observability/metrics.rst`에도 같은 이름). v1.20.2 업그레이드 가이드(`Documentation/operations/upgrade.rst`)는 아직 예전 이름 `cilium_operator_identity_*_count`를 나열하지만 코드는 더 이상 등록하지 않으므로 알림 기준으로 쓰지 마세요. 다음 단계로 가기 전에 두 `*_only_identities`가 0이 될 때까지 기다립니다. 1.21에서는 `cilium-dbg preflight migrate-identity`가 Double Write로 대체되어 deprecated입니다. 출처: `Documentation/operations/upgrade.rst`.

### Operator 관리 identity (beta)

Helm `identityManagementMode`는 `agent`(기본), `operator`, `both`(마이그레이션 전용)입니다. `operator`에서는 operator가 identity를 할당하므로 여러 agent가 동시에 만들던 중복 CIDR identity가 줄어듭니다.

1. agent에서 operator로: `both`로 설정하고 operator 재시작, 이어서 `operator`로 설정하고 agent 재시작.
2. 다운그레이드: agent를 `both`로, 이어서 operator를 `agent`로.
3. identity-relevant 레이블 패턴을 바꾼 뒤에는 operator와 agent를 모두 재시작합니다.

관련 값: 차트의 `operator.identityGCInterval`(15m0s), `identityHeartbeatTimeout`(30m0s), agent 플래그 `identity-allocation-timeout`(2m), `identity-change-grace-period`(5s), `identity-restore-grace-period`(30s).

### CiliumEndpoint, CiliumEndpointSlice, ipcache

- **CiliumEndpoint (CEP)**: Cilium이 관리하는 Pod마다 하나, 이름과 네임스페이스는 Pod와 동일합니다. status에 레이블, identity ID, 적용 중인 정책이 있습니다. `cilium-health-<node>` CEP는 `kube-system`에 있습니다.
- **CiliumEndpointSlice (CES, beta; CRD는 아직 cilium.io/v2alpha1)**: operator가 슬림 CEP를 CES로 묶고 agent는 CES를 watch합니다. API 서버 부하를 줄이는 대신 새 endpoint identity를 학습하는 데 지연이 생깁니다. Helm `ciliumEndpointSlice.enabled`(기본 false)와 `rateLimits`, 네임스페이스 어노테이션 `cilium.io/ces-namespace: priority`로 네임스페이스를 우선 처리합니다. Egress Gateway와는 함께 쓸 수 없습니다. 마이그레이션은 operator 먼저, agent 나중이며 다운그레이드는 agent 먼저입니다. `--ces-slice-mode` 플래그는 1.20에서 제거되었습니다.
- **ipcache**: BPF 맵 `cilium_ipcache_v2`가 IP 또는 CIDR을 identity에 매핑합니다. `cilium-dbg bpf ipcache list|get|match`, `cilium-dbg identity list|get`으로 확인합니다.
- endpoint마다 정책 맵이 있으며 크기는 `--bpf-policy-map-max`(기본 16384)입니다.

정책에 서로 다른 CIDR이 많으면 CIDR selector마다 local scope identity가 생깁니다. 아래 `CiliumCIDRGroup`을 쓰는 이유입니다.

### Identity 상태 확인

```bash
kubectl get ciliumidentities
kubectl get cep -A -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ipcache list
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
```

## 정책 모델 심화

### 정책 리소스

| 리소스 | 범위 | 비고 |
|---|---|---|
| Kubernetes `NetworkPolicy` | 네임스페이스 | L3/L4 |
| `CiliumNetworkPolicy` (CNP, cilium.io/v2) | 네임스페이스 | L3-L7, entity, FQDN, deny |
| `CiliumClusterwideNetworkPolicy` (CCNP) | 클러스터 | `nodeSelector`로 host policy도 가능 |
| `ClusterNetworkPolicy` (policy.networking.k8s.io, v1alpha2) | 클러스터 | **1.20 신규**, alpha API, 활성화 필요 |
| `CiliumCIDRGroup` | 클러스터 | 규칙에서 참조하는 이름 붙은 CIDR 집합 |

의미론: 규칙은 allow-list이며 합집합입니다. 적용은 stateful(응답 트래픽 허용)이고, 해당 방향에서 endpoint를 선택하는 규칙이 하나라도 있으면 그 방향이 default-deny로 전환됩니다.

### 적용 모드, default deny, audit 모드

| 제어 | 설정 | 효과 |
|---|---|---|
| `policyEnforcementMode` (플래그 `enable-policy`) | `default` / `always` / `never` | `default`: 선택되기 전까지 endpoint는 열림. `always`: 모든 곳에서 기본 거부. `never`: 정책 끔 |
| 규칙의 `enableDefaultDeny: {ingress, egress}` | 규칙 단위 | 선택하는 규칙이 있어도 해당 방향을 default-deny로 바꾸지 않음 |
| Helm `enableNonDefaultDenyPolicies` | true | 이런 규칙을 위한 차트 수준 활성화 |
| Audit 모드 | agent 플래그 `--policy-audit-mode=true`(ConfigMap `policy-audit-mode`) 또는 endpoint별 | 드롭될 패킷을 드롭하지 않고 verdict `AUDIT`으로 기록 |
| `policyDenyResponse` | `none` / `icmp` | `icmp`는 experimental, egress 전용 |

중요: `enableDefaultDeny: false`는 L7에는 **적용되지 않습니다**. allow-all이 없는 L7 규칙은 해당 포트의 나머지를 여전히 드롭합니다.

클러스터 전체와 endpoint별 audit 모드:

```bash
kubectl -n kube-system patch cm cilium-config --type merge \
  -p '{"data":{"policy-audit-mode":"true"}}'
kubectl -n kube-system rollout restart ds/cilium
# 또는 한 endpoint에만 (host endpoint 포함):
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled
hubble observe --verdict AUDIT
```

default-deny 롤아웃의 첫 단계로 audit 모드를 사용하세요. Hubble의 `AUDIT` verdict가 적용 시 드롭될 트래픽을 보여 줍니다. 출처: `Documentation/security/policy-creation.rst`.

### Entity

`host`, `remote-node`, `kube-apiserver`, `ingress`, `cluster`, `cluster-mesh`, `init`, `health`, `unmanaged`, `world`, `all`. `world`는 `0.0.0.0/0`과 같습니다. `kube-apiserver` ingress는 일부 관리형 플랫폼(업스트림 기준 AKS, GKE)에서 동작하지 않을 수 있습니다. agent 플래그 `--allow-localhost=policy`는 호스트에서 로컬 Pod로의 암묵적 허용을 끕니다.

### 노드 기반 선택과 CIDR

- `fromNodes`/`toNodes`는 `nodeSelectorLabels: true`(플래그 `--enable-node-selector-labels`)가 필요합니다. 노드가 remote-node scope identity를 갖게 됩니다. 업스트림 규모 안내: `policy-cidr-match-mode=nodes`일 때 노드 1000개당 약 1 MB.
- CIDR 규칙(`fromCIDR`, `toCIDR`, `fromCIDRSet`, `toCIDRSet`의 `except`)은 기본적으로 Pod나 노드를 **매칭하지 않습니다**. `policyCIDRMatchMode`(`--policy-cidr-match-mode`, beta)로 `pods` 또는 `nodes`를 선택적으로 켭니다. `pods`는 identity를 추가로 소모합니다. `values.yaml`의 주석은 `nodes`만 언급하지만 문서는 둘 다 허용하므로 문서를 따르세요. Kubernetes ClusterNetworkPolicy 적합성 구성은 `pods,nodes`를 사용합니다.
- **CiliumCIDRGroup**은 많은 CIDR을 이름 붙은 객체 하나로 관리하며 그룹당 identity 약 1개를 쓰고 Hubble flow에 그룹 이름을 주석으로 붙입니다. CRD 저장 버전은 1.18-1.21에서 `cilium.io/v2`입니다(v2alpha1도 계속 제공). 업스트림 문서 예제는 아직 `v2alpha1`을 보여 주므로 v2를 사용하세요.

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: vpn-example-1
  labels:
    role: vpn
spec:
  externalCIDRs:
  - 10.48.0.0/24
  - 10.16.0.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: from-vpn-example
  namespace: demo
spec:
  endpointSelector: {}
  ingress:
  - fromCIDRSet:
    - cidrGroupRef: vpn-example-1
```

참조는 `cidrGroupRef: <name>` 또는 `cidrGroupSelector.matchLabels`로 합니다.

### FQDN 정책과 DNS 프록시

`toFQDNs`의 `matchName`, `matchPattern`(`*`는 레이블 하나, `**.`는 여러 레이블 접두사, `*.cilium.io`는 `cilium.io` 자체를 매칭하지 않음). 메커니즘: 각 agent 안의 DNS 프록시가 DNS 응답을 관찰하고, 해석된 IP를 FQDN 파생(local scope) identity로 설치합니다. 따라서 다음이 성립합니다.

- 프록시가 응답을 볼 수 있도록 클러스터 DNS로의 egress DNS 규칙(`toPorts.rules.dns`)이 필요합니다.
- `toFQDNs`는 같은 규칙에서 다른 L3 selector와 함께 쓸 수 없습니다.
- agent가 재시작되면 그 시간 동안 프록시로의 DNS를 사용할 수 없습니다.
- FQDN은 이름 allow-list이며 평판 검사가 아닙니다. L7 프록시가 켜진 IPsec에서는 `--dnsproxy-enable-transparent-mode=true`가 필요합니다.
- 호스트명당 endpoint별 IP 한도는 문서와 코드가 다릅니다. 산문의 숫자를 믿지 말고 사용 중인 버전의 agent 플래그 `tofqdns-endpoint-max-ip-per-hostname`과 Helm `dnsProxy.endpointMaxIpPerHostname` 실효 값을 읽으세요.
- `dnsProxy.preCache` / `--tofqdns-pre-cache`는 1.20에서 deprecated이며 1.21 제거 예정입니다. 독립형 DNS 프록시는 alpha입니다.

### Deny 정책과 우선순위

`ingressDeny`/`egressDeny`는 CNP, CCNP, Kubernetes NetworkPolicy 전반의 모든 allow보다 우선합니다. L7 deny와 `toFQDNs` deny는 없습니다. 실제 평가 순서는 다음과 같습니다.

| 순서 | 규칙 종류 | 결과 |
|---|---|---|
| 1 | deny 규칙이 일치 | allow와 무관하게 드롭 |
| 2 | allow 규칙이 일치 | 전달 |
| 3 | 이 방향에서 endpoint가 선택되었고 일치 항목 없음 | 드롭 (default deny) |
| 4 | 이 방향에서 endpoint가 선택되지 않음 | 전달 (적용 모드가 `always`가 아닌 경우) |

Kubernetes ClusterNetworkPolicy와 함께 쓰면 tier 순서는 Admin tier, NetworkPolicy tier(Kubernetes NetworkPolicy, CNP, CCNP), Baseline tier입니다. `k8sClusterNetworkPolicy.enabled=true`(기본 false, 플래그 `--enable-k8s-cluster-network-policy`)로 켜고 network-policy-api 프로젝트의 `release-0.2` CRD를 설치합니다. Cilium 1.20에서는 alpha API입니다.

### 실전 정책 패턴

**DNS와 FQDN egress를 허용하는 default deny**(네임스페이스 `demo`). egress 규칙으로 endpoint를 선택하면 egress가 default-deny가 되므로 DNS를 명시적으로, 프록시가 응답을 볼 수 있도록 DNS 규칙과 함께 허용해야 합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-fqdn
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: ANY
      rules:
        dns:
        - matchPattern: "*"
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

EKS의 DNS Pod는 `k8s-app: kube-dns` 레이블을 가진 `coredns`입니다. 배포판이 다르게 레이블링하면 selector를 조정하세요.

**클러스터 내부에서만 ingress 허용, `world`는 차단**(투명 암호화 절에서 설명하는 평문 누출 구간도 줄입니다).

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cluster-only-ingress
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingress:
  - fromEntities:
    - cluster
```

**default-deny 없이 모든 DNS 가로채기**(업스트림 intro 페이지의 패턴): `kube-system`과 `kube-dns`를 제외한 모든 Pod를 선택하고 `matchPattern: "*"`로 `kube-dns`로의 DNS를 허용하며 `enableDefaultDeny: {egress: false, ingress: false}`를 둔 `CiliumClusterwideNetworkPolicy`. 다른 트래픽에 default-deny를 켜지 않고도 DNS 프록시가 경로에 들어가 Hubble이 DNS 이름을 보게 됩니다.

**allow와 무관하게 identity 차단**:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: deny-untrusted
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingressDeny:
  - fromEndpoints:
    - matchLabels:
        trust: low
```

**Host policy 골격**(`hostFirewall.enabled=true` 필요. host endpoint에서 audit 모드로 시작하고 SSH/SSM, kubelet, API 서버 경로를 먼저 허용하세요).

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: host-ingress-from-cluster
spec:
  nodeSelector:
    matchLabels:
      node-role: worker
  ingress:
  - fromEntities:
    - cluster
    toPorts:
    - ports:
      - port: "10250"
        protocol: TCP
```

ingress 규칙이 하나라도 host endpoint를 선택하면 default-deny가 적용되므로, 이런 정책은 해당 노드에서 나머지(SSH 포함)를 모두 드롭합니다. `cilium-dbg endpoint get -l reserved:host -o jsonpath='{[0].id}'`로 host endpoint ID를 구하고, 먼저 `PolicyAuditMode=Enabled`를 설정한 뒤 `hubble observe --verdict AUDIT`로 확인하고 적용하세요.

### 정책 판단 읽기

```
cilium-dbg endpoint list                       # endpoint ID, identity, ingress/egress 적용 여부
cilium-dbg endpoint get <ID> -o json           # 레이블, identity, 정책 revision
cilium-dbg bpf policy get <ID>                 # endpoint별 정책 맵 (identity, 포트, 프로토콜, deny 플래그)
cilium-dbg policy selectors                    # 각 selector가 현재 매칭하는 identity
hubble observe --pod demo/server --verdict DROPPED -o json   # 드롭 사유와 (correlation 사용 시) 일치한 정책
```

selector가 기대보다 적은 identity를 매칭한다면 보통 identity-relevant 레이블 불일치(identity에서 제외된 레이블) 또는 selector에 네임스페이스를 암묵적으로 추가하는 네임스페이스 범위 CNP가 원인입니다.

### 빈 정책의 CEL 거부 (1.20)

1.20에서 CNP와 CCNP CRD는 CEL 규칙 `has(self.spec) || has(self.specs)`와 메시지 "spec or specs must be provided"를 가집니다. 두 필드가 모두 없는 정책을 만들거나 수정하면 admission 단계에서 거부됩니다. 기존 빈 정책은 수정하기 전까지 영향이 없습니다. 관련된 이전 변경: 1.19부터 `FromRequires`/`ToRequires`는 비어 있어야 하며 Kafka/proxylib L7 정책은 1.20에서 제거되었습니다.

### Host policy

`nodeSelector`를 가진 `CiliumClusterwideNetworkPolicy`가 host policy가 됩니다. `hostFirewall.enabled=true`(선택적으로 `devices`)가 필요합니다. 호스트 네임스페이스와 host-network Pod에 적용되고 L3/L4와 L7 DNS(beta)를 지원합니다. VRRP, IGMP, GRE, IPIP, IPV6, ESP, AH에는 `--enable-extended-ip-protocols`가 필요합니다. 업스트림의 알려진 이슈: host policy는 IPsec과 **함께 동작하지 않고**, 호스트 WireGuard 인터페이스에는 적용되지 않으며, 활성화하면 알 수 없는 L2 프로토콜이 드롭됩니다. L7 DNS host policy는 kubelet 이미지 pull과 agent 재시작을 깨뜨릴 수 있으므로 audit 모드로 시작하세요.

### 1.21 pre-release 추가 사항 **[1.21 pre-release]**

CNP egress `toPorts[].listener`가 포트를 CEC/CCEC Envoy listener로 리다이렉트합니다(같은 포트의 L7 규칙과 함께 쓸 수 없으며, 업스트림은 Gateway API/GAMMA를 권장). `--fixed-identity-mapping`은 deprecated입니다.

## 인증 타임라인: Mutual Authentication (제거됨)

### 동작 방식 (1.18-1.20)

규칙에 `authentication: {mode: required}`를 둡니다. 데이터패스에서 이 플래그가 붙은 정책 매치는 BPF 맵 `cilium_auth_map`(524288 항목, 키는 로컬 identity, 원격 identity, 원격 노드, auth 타입)을 조회합니다. 만료되지 않은 항목이 없으면 패킷은 드롭(`DROP_POLICY_AUTH_REQUIRED`, -189)되고 agent에 신호가 갑니다. agent의 `pkg/auth` 매니저가 **원격 노드의 agent**로 포트 4250(`authentication.mutual.port`)에 대역 외 TLS 1.3 연결을 열고, SPIRE agent 소켓에서 받은 SPIFFE SVID(`spiffe://spiffe.cilium/identity/<numeric-id>`)를 제시하며, 상대 인증서를 검증하고, 가장 빠른 만료 시각을 auth 맵에 저장합니다. 이후 재전송된 패킷이 통과합니다. 핵심: 핸드셰이크는 **agent 사이**에서 이루어지며 연결 단위도 데이터 경로 위도 아니었고, WireGuard나 IPsec을 함께 켜지 않으면 애플리케이션 트래픽은 암호화되지 않았습니다. 알려진 한계: ClusterMesh 불가, SPIRE만 테스트됨, 외부 mTLS와 상호운용 불가.

### 타임라인과 조치

| 릴리스 | 상태 | 조치 |
|---|---|---|
| 1.18, 1.19 | Beta. 1.19에서 `authentication.enabled` 기본값 false이며 `authentication`이 있는 정책은 인증 없이 조용히 전달(검증 경고 포함) | 유지 또는 마이그레이션 |
| 1.20 | Deprecated (문서에는 여전히 Beta 표기) | ztunnel(`encryption.type=ztunnel`) 또는 네트워크 암호화 + identity 정책으로 마이그레이션 계획 |
| 1.21 | 제거. agent `pkg/auth`와 `mesh-auth-*` agent 플래그 삭제. 정책 `authentication` 필드는 받아들이지만 사용되지 않음 | 업그레이드 **전에** `authentication.*` Helm 값과 SPIRE mutual-auth 설정 제거 |

마이그레이션 가이드:

1. `authentication`을 쓰는 정책 목록화: `kubectl get cnp,ccnp -A -o yaml | grep -n "authentication"`.
2. 실제 요구사항을 정리합니다. "전송 중 암호화"였다면 WireGuard나 IPsec([아래](#투명-암호화))을, "인증된 워크로드 identity"였다면 ztunnel mTLS나 메시(Istio)를 사용합니다.
3. 1.21에서 이 필드가 무언가를 강제한다고 가정하지 마세요. 업스트림은 호환을 위해 받아들이지만 사용하지 않는다고 하므로 `required`에 의존하던 정책은 더 이상 인증을 요구하지 않습니다. 런타임에서 agent가 이를 어떻게 알리는지는 확인하지 못했습니다.
4. 1.21에서 `authentication.mutual.spire.*` 차트 값이 남은 이유는 SPIRE 설치와 operator의 SPIRE 클라이언트를 ztunnel `ca.type=spire`가 재사용하기 때문입니다. 더 이상 mutual authentication을 설정하지 않습니다.
5. 1.21에서 Hubble `dropEventEmitter.reasons`에 더는 `auth_required`가 없습니다.

## ztunnel 워크로드 mTLS (1.19부터 Beta)

### 아키텍처

`encryption.type=ztunnel`은 Istio의 노드별 L4 프록시(ztunnel 개념)를 실행하며 Cilium 자체가 컨트롤 플레인입니다.

```
 가입된 Pod A (netns)                              가입된 Pod B (netns)
  app --> iptables (Pod 내부) --> :15001           :15008 (HBONE 수신) --> ztunnel --> :15006 --> app
                                   |                  ^
                                   v                  |
                  노드 A ztunnel (DaemonSet, hostNetwork)  ==HBONE: mTLS 위의 HTTP/2 CONNECT, TCP 15008==> 노드 B ztunnel
                                   ^   xDS (워크로드)    ^ Cilium CA로 CSR
                                   |                     |
                     Cilium agent: xDS/ADS 서버, ZDS unix 소켓 (/var/run/cilium/ztunnel.sock),
                                   내장 CA (IstioCertificateService), 가입 reconciler
```

- 노드마다 `ztunnel-cilium` DaemonSet(hostNetwork, 컨테이너 `istio-proxy`)이 실행됩니다. 1.20과 1.21의 이미지는 `quay.io/cilium/ztunnel:v1.0.0`이고 1.19는 `docker.io/istio/ztunnel` 1.28.0-distroless를 썼습니다.
- agent는 CEP에서 가져온 워크로드 데이터를 xDS로 제공하고, Pod 네트워크 네임스페이스 파일 디스크립터와 메타데이터를 ZDS unix 소켓으로 전달하며, 해당 노드에 endpoint가 있는 서비스 어카운트의 URI SAN `spiffe://<trust domain>/ns/<ns>/sa/<sa>` CSR에 서명합니다.
- iptables 규칙은 가입된 **각 Pod의 netns 내부**에 설치됩니다. 아웃바운드는 15001, 평문 인바운드는 15006으로 가고, 15008의 HBONE 인바운드는 리다이렉트하지 않습니다(mark 0x539). 와이어 프로토콜은 **TCP 15008**의 HBONE(mTLS 위의 HTTP/2 CONNECT)입니다.
- Istio ambient와의 차이: istiod, waypoint, L7 기능이 없고, 가입은 `istio.io/dataplane-mode=ambient`가 아니라 `io.cilium/mtls-enabled=true` 레이블이며, CA는 Cilium 내부 CA 또는 SPIRE입니다. 같은 Pod에서 둘을 함께 실행하지 마세요.

### Secret, CA 타입, 가입

설치 전에 bootstrap 및 CA 키 자료를 생성합니다(업스트림 저장소의 `examples/kubernetes-ztunnel/generate-secrets.sh`). `kube-system`의 secret `cilium-ztunnel-secrets`에 `bootstrap-private.key`, `bootstrap-root.crt`, `ca-private.key`, `ca-root.crt`가 들어갑니다. 업스트림 설명상 bootstrap 쌍은 ztunnel과 Cilium xDS/인증서 서버 사이 연결을 보호하고, CA 쌍은 메모리 내 임시 워크로드 인증서의 루트입니다.

```yaml
# values-ztunnel.yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal   # 기본값; "spire"는 1.20 신규
```

| `encryption.ztunnel.ca.type` | 동작 |
|---|---|
| `internal` (기본) | Cilium 내장 CA가 워크로드 인증서에 서명. SPIRE reconciler 없음 |
| `spire` (1.20+) | 외부 SPIRE 서버가 identity 발급. operator가 가입된 네임스페이스의 서비스 어카운트에 대해 항목(parent `/ztunnel`, path `/ns/<ns>/sa/<sa>`)을 등록 |

`spire` 모드는 업스트림 암호화 가이드에 설명이 없으며, 이번 검토에서는 operator 코드 경로만 확인했고 end-to-end 배포는 확인하지 못했습니다. 고급 옵션으로 보고 따로 테스트하세요.

네임스페이스 가입과 해제:

```bash
kubectl label namespace demo io.cilium/mtls-enabled=true
kubectl label namespace demo io.cilium/mtls-enabled-      # 해제
```

네임스페이스의 기존 Pod(ztunnel Pod 제외)와 이후 생성되는 Pod가 모두 가입됩니다. 가입은 네임스페이스 단위뿐이며 host-network Pod는 건너뜁니다.

### 한계

| 한계 | 내용 |
|---|---|
| 양쪽 모두 가입 | 가입-비가입 간 트래픽은 지원되지 않음 |
| TCP 전용 | UDP 등은 리다이렉트되지 않음 |
| 정책 상호작용 | Pod를 떠나기 전에 암호화되므로 L4 정책이 내부 포트를 볼 수 없음. HBONE 포트 15008만 대상으로 지정 가능 |
| 커널 | iptables 지원 필요 |
| ClusterMesh | 비호환. 둘을 함께 켜면 검증 오류 |
| 가입 단위 | 네임스페이스 레이블만. Pod 단위 가입 없음 |

EKS에서 피어는 같은 VPC에 있으므로 노드 보안 그룹은 노드 간 TCP 15008을 허용해야 하며, 노드 보안 그룹 자기 참조로 지정하고 공개 CIDR은 절대 쓰지 않습니다.

### 확인

```bash
kubectl -n kube-system describe cm cilium-config | grep enable-ztunnel -A2
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system exec ds/cilium -- cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'
# 가입된 Pod를 호스팅하는 노드의 Cilium Pod 안에서 (tcpdump 먼저 설치)
tcpdump -i eth0 port 15008      # 터널 사용 시 cilium_vxlan
```

## 투명 암호화

공통 규칙: 기본적으로 노드 사이를 오가는 Cilium 관리 Pod 트래픽만 암호화되며, 같은 노드 안 트래픽은 암호화되지 않습니다. 노드가 아직 학습하지 못한 endpoint로의 egress는 같은 ipcache/정책 메커니즘으로 판단하기 때문에 평문으로 나갈 수 있습니다. strict 모드나 `world`를 거부하는 egress 정책으로 완화합니다.

### 암호화 패킷 흐름

```
Pod A (노드 1) -> Pod B (노드 2), WireGuard, 터널 모드

 Pod A veth --> bpf_lxc: 정책 통과, ipcache가 목적지를 원격 Cilium endpoint로 판단
            --> 암호화 대상으로 패킷 표시 (목적지가 관리되는 원격 endpoint)
            --> VXLAN/Geneve 캡슐화 (cilium_vxlan / cilium_geneve)
            --> cilium_wg0로 라우팅 (WireGuard: UDP 51871, CiliumNode 공개키로 피어 선택)
            --> NIC (외부 IP: 노드 1 -> 노드 2)
 NIC (노드 2) --> cilium_wg0 복호화 --> 터널 디캡슐화 --> bpf_lxc ingress 정책 --> Pod B

네이티브 라우팅: VXLAN/Geneve 단계가 없고 내부 패킷이 Pod A -> Pod B 그대로 WireGuard 안에 들어갑니다.
IPsec도 같은 판단 지점을 쓰지만 (출발 노드, 도착 노드)용 XFRM 상태가 캡슐화 후 ESP를 적용합니다.
```

이는 개념 요약이며 BPF 프로그램의 정확한 순서를 추적한 것이 아닙니다. 프로그램 구성은 [Part 8](08-ebpf-datapath-internals.md)을 보세요. 두 가지 결론이 따릅니다. 첫째, "목적지가 관리되는 원격 endpoint인가"는 ipcache에서 오므로 학습되지 않은 목적지는 외부로 취급됩니다(누출 구간). 둘째, 암호화는 정책과 캡슐화 뒤에 일어나므로 물리 NIC 캡처에는 암호문만 보이고 `cilium_wg0` 캡처에는 내부 패킷이 보입니다.

### WireGuard (stable)

메커니즘: 각 agent가 키 쌍을 생성하고 공개키를 `CiliumNode` 어노테이션 `network.cilium.io/wg-pub-key`로 게시하며, 다른 모든 노드마다 `cilium_wg0` 장치에 WireGuard 피어를 구성합니다. 모든 노드에서 UDP **51871**을 사용합니다. 커널 WireGuard(`CONFIG_WIREGUARD`, Linux 5.6 이상 또는 out-of-tree 모듈)가 필요합니다. 터널 모드에서는 Pod 트래픽이 VXLAN/Geneve, 이어서 WireGuard로 이중 캡슐화되므로 MTU가 중요합니다([Part 9](09-overlay-native-routing.md)).

```yaml
encryption:
  enabled: true
  type: wireguard
  wireguard:
    persistentKeepalive: 0s
```

- CNI chaining(AWS VPC CNI)에서는 `cni.enableRouteMTUForCNIChaining=true`를 설정해야 하며, 그렇지 않으면 암호화된 Pod 트래픽이 단편화될 수 있습니다.
- ClusterMesh는 모든 클러스터에서 WireGuard와 클러스터 간 UDP 51871이 필요합니다.
- 장치를 구성하는 동안 패킷이 드롭되는 알려진 이슈가 있습니다(업스트림 gh-33159).
- **Node-to-node**(`encryption.nodeEncryption`, beta): 암호화를 호스트 트래픽까지 확장합니다. 컨트롤 플레인 노드는 `node-encryption-opt-out-labels`로 제외합니다. XDP나 non-Geneve DSR을 쓰는 north-south 경로에는 공백이 있습니다. **[1.21 pre-release]** deprecated이며 1.22에서 제거됩니다.

### Strict 모드

| Helm 값 | 의미 |
|---|---|
| `encryption.strictMode.egress.enabled` | 노드를 떠나 strict CIDR로 가는 비암호화 트래픽 드롭 |
| `encryption.strictMode.egress.cidr` | 적용할 Pod CIDR (IPv4 전용. IPv6는 보호되지 않음) |
| `encryption.strictMode.egress.allowRemoteNodeIdentities` | 터널링 사용 시 또는 노드/Pod CIDR이 겹칠 때 필요 |
| `encryption.strictMode.ingress.enabled` | WireGuard를 거치지 않고 도착한 클러스터 내부 ingress 드롭. **WireGuard 전용** |

Ingress strict 모드(1.19+)는 1.20.2 문서에서 터널과 네이티브 라우팅 모두 지원합니다(1.19 업그레이드 노트는 터널링이 필요하다고 했습니다). 한계: CNI chaining 불가, node-to-node 트래픽은 보호하지 않으며, Pod 트래픽이 지나갈 수 있는 모든 인터페이스에 Cilium BPF가 붙어 있어야 합니다.

**1.20의 플래그 이름 변경**: 이전 플래그 `--enable-encryption-strict-mode`, `--encryption-strict-mode-cidr`, `--encryption-strict-mode-allow-remote-node-identities`(1.19에서 deprecated)는 **제거**되었습니다. `--enable-encryption-strict-mode-egress`, `--encryption-strict-egress-cidr`, `--encryption-strict-egress-allow-remote-node-identities`, `--enable-encryption-strict-mode-ingress`를 사용하세요. Helm은 `encryption.strictMode.{enabled,cidr,allowRemoteNodeIdentities}`에서 `encryption.strictMode.egress.*`로 이동했습니다. 1.20 업그레이드 노트는 CIDR 값을 `cidrs`로 적었지만 1.20.2 차트 `values.yaml`은 `cidr`이며, 차트가 기준입니다.

### IPsec (stable)

메커니즘: agent가 Secret의 사전 공유 키로 Linux XFRM 상태와 정책을 프로그래밍합니다. 패킷은 오버레이 캡슐화 뒤에 ESP로 캡슐화됩니다(1.18부터 이 순서가 고정이며 `encryptedOverlay` 옵션은 없어졌습니다).

```bash
kubectl create -n kube-system secret generic cilium-ipsec-keys \
  --from-literal=keys="3+ rfc4106(gcm(aes)) $(dd if=/dev/urandom count=20 bs=1 2>/dev/null | xxd -p -c 64) 128"
```

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyWatcher: true
    keyRotationDuration: 5m
```

- Secret 값 형식: `key-id algorithm PSK-hex key-size`. key id 뒤의 `+`는 **터널별 파생 키**를 강제합니다. 전역 키는 1.16에서 deprecated되었습니다(GHSA-pwqm-x5x6-5586).
- 회전: key ID는 1..15 범위이며 재키마다 증가하고 15 다음에는 1로 되돌아갑니다(`encryption-ipsec.rst:206-218`, 업스트림 스니펫은 `KEYID`가 15 이상이면 0으로 리셋). 따라서 "더 큰 ID로 패치"는 15에서 실패하며 다음 Secret은 ID 1이어야 합니다. 다음 ID로 Secret을 패치하면 agent가 watch하고(`keyWatcher`) `keyRotationDuration`과 그 10분의 1까지의 지터 뒤에 이전 키를 제거합니다. 업그레이드 중에는 회전하지 마세요. ClusterMesh에서는 모든 클러스터에서 회전합니다.
- 직접 라우팅에는 `ipv4NativeRoutingCIDR`가 필요합니다. CNI chaining 불가. 최대 65535 노드, 터널 하나의 복호화는 CPU 코어 하나에 묶입니다.
- 확인: `cilium-dbg encrypt status`(사용 중인 키, XFRM 오류 카운터), `tcpdump -l -n -i eth0 esp`. 보안 그룹은 노드 간 ESP(IP 프로토콜 50)를 자기 참조로 허용해야 합니다. UDP 500/4500 요구사항은 이번 검토에서 확인하지 못했습니다.
- **1.20에서 제거**: `encryption.ipsec.interface`(`--encrypt-interface`, 1.18부터 no-op)와 `encryption.ipsec.encryptedOverlay`. 1.20.2 차트 `values.yaml`과 IPsec 가이드에는 `interface`가 아직 남아 있는데 업스트림 불일치이므로 설정하지 마세요.
- **Host policy는 IPsec과 동작하지 않습니다**(업스트림 gh-41854).

### MTU 오버헤드

암호화는 헤더 바이트를 더해 사용 가능한 Pod MTU를 줄이며, 터널 모드에서는 터널 헤더가 추가로 붙습니다. Cilium이 route MTU를 자동으로 계산하며 CNI chaining에서는 `cni.enableRouteMTUForCNIChaining`을 설정합니다. Part 9가 `pkg/mtu/mtu.go`(v1.20.2)에서 바이트 수를 계산합니다. WireGuard 95, 기본 키 크기의 IPsec 77, IPv4 언더레이의 VXLAN 50이며 [MTU 계산 절](09-overlay-native-routing.md)을 참고하세요. 측정값이 아닌 계산값이므로 Pod 사이 `ping -M do -s <size>`와 Cilium 장치의 `ip link`로 확인하세요.

### 선택 기준

| 요구 | 선택 |
|---|---|
| 키 관리 없는 단순한 Pod 간 네트워크 암호화 | WireGuard |
| FIPS/컴플라이언스, WireGuard 없는 커널, 키 회전 부담 감수 | IPsec |
| 암호화된 채널에 묶인 워크로드 identity, 네임스페이스 단위 opt-in, TCP 전용 | ztunnel |
| 클러스터 간 (ClusterMesh) | WireGuard 또는 IPsec (ztunnel은 비호환) |
| L7 인지 mTLS, 인가, waypoint | Istio |

## 서비스 메시 TLS 옵션

| 옵션 | 제공 기능 | 비고 |
|---|---|---|
| Istio sidecar | sidecar 간 mTLS, Istio의 L7 정책 | Cilium과 Istio가 HTTP 규칙을 둘 다 적용하지 않도록 하며, 해당 Pod에 Cilium L7을 쓰려면 Istio `PeerAuthentication` mTLS를 `DISABLE`로 설정 |
| Istio ambient | ztunnel/HBONE 15008, 선택적 waypoint | Cilium은 15008의 암호화된 L4만 봄. Cilium L7을 쓰려면 `istio.io/dataplane-mode`를 제거하거나 Pod에 `ambient.istio.io/redirection: disabled` 어노테이션 |
| Cilium ztunnel | L4 mTLS만 | 위 참조 |
| Cilium 내 Envoy TLS (CEC/Gateway API) | Envoy에서 TLS 종료/재시작 | ingress/egress 가시성용이며 east-west 메시 mTLS용 아님 |

Istio 공존(업스트림 `network/servicemesh/istio.rst`): `kubeProxyReplacement=false`를 권장하며, 대체를 켠다면 `socketLB.hostNamespaceOnly=true`와 `cni.exclusive=false`를 설정합니다. 오버레이에서 sidecar를 쓰면 istiod에 `hostNetwork: true`가 필요합니다. [Part 5](05-l2-l7-networking.md)도 보세요.

**TLS 인터셉션**(CNP `toPorts`의 `terminatingTLS` / `originatingTLS`): Envoy가 클라이언트가 신뢰해야 하는 내부 CA 인증서로 TLS를 종료한 뒤 목적지로 재시작합니다. Secret은 SDS로 전달됩니다(1.17부터 기본). Helm `tls.secretsNamespace.name`의 기본값은 `cilium-secrets`, `tls.readSecretsOnlyFromSecretsNamespace`는 true이며 operator가 참조된 Secret을 그곳으로 복사합니다. 암호화된 egress에 L7 정책 가시성을 제공하며 메시 mTLS의 대체물은 아닙니다.

**Gateway API TLS**: HTTPS listener 종료는 Secret을 사용하고, `BackendTLSPolicy`(gateway.networking.k8s.io/v1, `targetRefs` Service, `validation.caCertificateRefs` ConfigMap, `hostname`)가 Envoy에서 backend까지를 암호화합니다. Cilium 1.20은 Gateway API v1.6.1 CRD가 필요하며, TLSRoute는 v1이라 이전에 썼다면 experimental 채널이 필요하고 그렇지 않으면 기존 객체가 사라집니다. cert-manager는 `cert-manager.io/issuer` 어노테이션으로 연동됩니다. **노출 규칙**: 업스트림 Gateway/Ingress 예제는 `LoadBalancer` 타입 `Service`를 만듭니다. EKS에서는 internal scheme(`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`)을 쓰고 CloudFront VPC origin 뒤에 두며 internet-facing은 절대 쓰지 않습니다. Cilium 차트 기준 검증은 이번 검토에서 하지 못했습니다. [Part 11](11-bgp-lb-egress-edge.md)을 보세요.

## Hubble과 Tetragon

### Hubble 구성 요소

Hubble 서버는 각 agent 안에서 동작합니다(`hubble.listenAddress` 기본 `:4244`의 gRPC와 unix 소켓 `/var/run/cilium/hubble.sock`). **Relay**(`hubble.relay.enabled`, 기본 false, 4245 수신)는 전체 노드를 하나의 API로 집계합니다. **UI**(`hubble.ui.enabled`, 기본 false)는 Relay 위에 올라갑니다. 서버와 Relay는 기본적으로 mTLS를 사용합니다(`hubble.tls.enabled: true`). Relay와 UI는 ClusterIP(또는 CloudFront VPC origin 뒤의 internal LB)로 두고 공개하지 마세요.

이벤트 경로: 데이터패스 이벤트, agent별 ring buffer(`hubble.eventBufferCapacity`, 기본 4095, 허용 값은 65535까지의 2^n-1), 그리고 observer(CLI, Relay, exporter, 메트릭). `hubble.networkPolicyCorrelation.enabled`(기본 true)는 flow에 허용/거부한 정책을 붙입니다.

### 메트릭

`hubble.metrics.enabled`는 핸들러 목록입니다(예: `dns`, `drop`, `tcp`, `flow`, `port-distribution`, `icmp`, `httpV2`, `flows-to-world`, `policy`. `sctp`는 1.20에서 신규이며 v1.19.8에는 핸들러가 없음). 엔드포인트 포트는 9965입니다. 동적 메트릭(`hubble.metrics.dynamic.enabled`, ConfigMap `cilium-dynamic-metrics-config`)은 agent 재시작 없이 재구성됩니다. L7 핸들러는 L7 가시성이 있는 Pod에 대해서만 데이터를 생성합니다. Kafka 핸들러는 1.20에서 제거되었습니다. `hubble.metrics.portName`은 **[1.21 pre-release]** 신규입니다.

### Exporter

- 정적: `hubble.export.static.enabled`, `filePath`(기본 `/var/run/cilium/hubble/events.log`, `stdout` 허용), `fileMaxSizeMb`, `fileMaxBackups`, `fileCompress`, `allowList`, `denyList`, `fieldMask`. `fieldAggregate`와 `aggregationInterval`은 1.19부터. agent 수명주기에 묶입니다.
- 동적: `hubble.export.dynamic.enabled`와 ConfigMap `cilium-flowlog-config`에 저장되는 `config.content[]` 항목(`name`, `filePath`, `fieldMask`, `includeFilters`, `excludeFilters`, `end`, 로테이션 필드). 재시작 없이 적용됩니다(반영까지 약 1분).

### 마스킹 (L7)

`hubble.redact.enabled`(기본 false), `http.urlQuery`(false), `http.userInfo`(true), `http.headers.allow` **또는** `deny`(동시 사용 불가). 예: `Authorization`과 `Proxy-Authorization` 거부. Kafka `apiKey` 마스킹은 Kafka 지원과 함께 1.20에서 제거되었습니다.

```yaml
hubble:
  redact:
    enabled: true
    http:
      urlQuery: true
      userInfo: true
      headers:
        deny:
        - Authorization
        - Proxy-Authorization
```

### Drop 이벤트

`hubble.dropEventEmitter`(alpha)는 드롭된 트래픽에 대해 Kubernetes Event를 발생시킵니다. `interval`은 2m이고 1.20.2의 `reasons` 기본값은 `auth_required`, `policy_denied`이며 1.21에서는 `auth_required`가 더 이상 없습니다.

### Tetragon (개요만)

Tetragon은 Cilium 저장소에 포함되지 않은 별도 프로젝트로, 프로세스 실행, 파일, 네트워크 활동에 대한 eBPF 기반 런타임 보안 관찰과 강제를 `TracingPolicy` 리소스로 설정합니다. Cilium 위협 모델 문서가 런타임 가시성을 위해 이를 권장합니다. CRD 버전과 강제 동작 등 세부 사항은 이번 검토에서 **확인하지 못했으며** 이 절은 개요에 한정됩니다. 구체적인 내용은 Tetragon 프로젝트 문서를 참고하세요.

## 인증서 관리

| 구성 요소 | 인증서 출처 | 갱신 |
|---|---|---|
| Hubble 서버, Relay, 메트릭 | `hubble.tls.auto.method`: `helm`(기본), `cronJob`, `certmanager` | `helm`: Helm 렌더 시에만 재생성(자동 갱신 없음). `cronJob`: certgen CronJob, 스케줄 `0 0 1 */4 *`. `certmanager`: cert-manager가 갱신, `certManagerIssuerRef` 설정 |
| ClusterMesh API 서버 | `clustermesh.apiserver.tls.auto` 아래 동일한 세 방식 | [Part 13](13-clustermesh-install-upgrade.md) 참조 |
| ztunnel 워크로드 | 내부 CA 또는 SPIRE | 짧은 수명, 메모리 내 |
| IPsec / WireGuard | PSK secret / 자동 키 쌍 | 수동 키 회전(IPsec). WireGuard는 자동 |

알아 둘 값(1.20.2 `values.yaml`): `hubble.tls.auto.certValidityDuration` 기본값은 **365**일이고 공유 자동 생성 CA(`tls.ca.certValidityDuration`)는 **1095**일입니다. 다른 업스트림 산문에는 리프 인증서 기본값을 3년으로 적은 곳이 있지만 적용되는 값은 차트 값입니다. 서버와 Relay 인증서 및 CA는 hot-reload됩니다.

1.20 변경 사항:

- ClusterMesh 자동 인증서 기본 유효기간이 1년(`clustermesh.apiserver.tls.auto.certValidityDuration: 365`, 1.19는 1095)입니다. `helm` 방식은 차트를 렌더할 때만 갱신되므로 최소 1년에 한 번은 업그레이드하세요. `cronJob`과 `certmanager`는 자동 갱신합니다(ClusterMesh cronJob은 4개월마다 재생성).
- `certgen.enforceCAValidityThroughoutLeavesDuration` 기본값이 true입니다. CA가 리프 인증서보다 먼저 만료되면 certgen이 실패합니다. 끄려면 false.
- Helm 값으로 인증서를 직접 주는 방식은 제거되었습니다. Secret을 미리 만들고 `tls.auto.enabled=false`로 설정합니다.
- `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}`는 `...tls.auto.server.*`로 이동했습니다.

사용자 제공 Hubble 인증서에는 SAN `*.<cluster>.hubble-grpc.cilium.io`(서버), `*.hubble-relay.cilium.io`(Relay), `*.hubble-ui.cilium.io`, `<cluster>.hubble-metrics.cilium.io`가 필요하고 Secret에는 `tls.crt`, `tls.key`, `ca.crt`가 들어갑니다. **[1.21 pre-release]** Pod별 인증서: `hubble.tls.disableDefaultVolumes`, `hubble.relay.tls.disableDefaultVolumes`, `hubble.ui.tls.disableDefaultVolumes`, `extraInitContainers`로 Vault, cert-manager CSI, SPIFFE 소스를 쓸 수 있고, `clustermesh.apiserver.tls.authMode` 기본값은 `cluster`가 됩니다.

```yaml
hubble:
  tls:
    auto:
      enabled: true
      method: certmanager
      certManagerIssuerRef:
        group: cert-manager.io
        kind: ClusterIssuer
        name: hubble-issuer
```

## 실습

이 실습들은 이번 검토에서 실제 클러스터에 실행하지 않았습니다(검증 한계 참조). 일회용 클러스터를 사용하세요. 보안 그룹 관련 내용은 노드 보안 그룹 자기 참조 규칙을 전제로 하며, 어떤 포트도 `0.0.0.0/0`이나 `::/0`에 열지 마세요.

### 실습 1: Identity, ipcache, 레이블 제외

사전 조건: Cilium 1.20.2 클러스터, kubectl, agent Pod를 통한 `cilium-dbg`.

1. 네임스페이스를 만들고 `web`(`app=web`)과 `db`(`app=db`) Deployment를 각각 replica 2개로 만듭니다.
2. `kubectl get ciliumidentities`: `web` 레이블 집합에 하나, `db`에 하나의 identity가 있고 각 replica가 공유해야 합니다.
3. `kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list`로 `web`과 `db`의 ID를 기록합니다.
4. `web` Pod IP 하나로 `cilium-dbg bpf ipcache list | grep <podIP>`를 실행합니다. 항목의 identity가 `web` identity와 같아야 합니다.
5. `kubectl label pod <pod> release=r2 --overwrite`로 `web` Pod 하나의 레이블을 바꿉니다. 해당 Pod에 새 identity가 생기고 `kubectl get ciliumidentities`가 하나 늘어나 레이블 churn을 보여 줍니다.
6. 정리: 네임스페이스를 삭제합니다. Helm으로 identity-relevant 레이블을 바꿨다면 `helm upgrade`(`--reuse-values`는 클러스터가 이미 이 차트 버전 1.20.2일 때만 유효하며, 아니면 저장한 값을 명시적으로 전달)로 되돌리고 agent를 재시작합니다(identity는 agent 재시작 뒤에야 바뀝니다).

### 실습 2: WireGuard와 strict ingress

사전 조건: 커널 WireGuard가 있는 노드, 노드 보안 그룹에서 노드 보안 그룹 자신을 소스로 하는 UDP 51871 허용.

1. `helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values --set encryption.enabled=true --set encryption.type=wireguard`를 실행하고 롤아웃이 되지 않으면 agent를 재시작합니다. `--reuse-values`는 클러스터가 이미 차트 1.20.2일 때(차트 버전이 바뀌지 않을 때)만 유효합니다(업스트림 `upgrade.rst:206-221`). 다른 버전이면 `helm get values cilium -n kube-system -o yaml`로 값을 저장하고 이름이 바뀐 값을 확인한 뒤 `-f`로 전달하세요.
2. `kubectl -n kube-system exec ds/cilium -- cilium-dbg status | grep Encryption`. 노드 수 - 1과 같은 N을 가진 `Wireguard [cilium_wg0 (...Port: 51871, Peers: N)]` 줄이 보여야 합니다.
3. 서로 다른 노드의 Pod 간 트래픽을 만들고 agent Pod에서 `tcpdump -n -i cilium_wg0`를 실행합니다. 평문 Pod 간 flow가 `cilium_wg0`에서 보이고, 물리 인터페이스의 UDP 51871 캡처에는 암호화된 패킷만 보여야 합니다.
4. strict 모드 활성화: `--set encryption.strictMode.egress.enabled=true --set encryption.strictMode.egress.cidr=<podCIDR> --set encryption.strictMode.ingress.enabled=true`. 터널링이면 `allowRemoteNodeIdentities=true`도 설정합니다.
5. 일반 Pod 트래픽은 계속 동작하고, WireGuard를 우회하는 비암호화 Pod 트래픽은 드롭되어야 합니다(그런 트래픽 주입에는 호스트 수준 도구가 필요하며 선택 사항).
6. 롤백: strict 값을 먼저 false로 하고 `encryption.enabled=false`로 한 뒤 agent를 재시작합니다. 장치 재구성 중 잠시 드롭이 있을 수 있습니다(업스트림 알려진 이슈).

### 실습 3: ztunnel 가입

사전 조건: ClusterMesh 없음, iptables가 있는 노드, 노드 보안 그룹의 노드 간 TCP 15008 허용.

1. 같은 태그의 Cilium 소스 트리에서 `bash examples/kubernetes-ztunnel/generate-secrets.sh`를 실행합니다(`kube-system`에 `cilium-ztunnel-secrets` 생성).
2. `encryption.enabled=true`, `encryption.type=ztunnel`로 업그레이드합니다. `kubectl -n kube-system get ds ztunnel-cilium`과 `describe cm cilium-config | grep enable-ztunnel -A2`로 확인합니다.
3. 네임스페이스 `mtls-on`과 `mtls-off`에 각각 HTTP 서버와 curl 클라이언트를 만듭니다. `mtls-on`에만 `kubectl label ns mtls-on io.cilium/mtls-enabled=true`를 붙입니다. 기존 Pod는 자동으로 가입되므로 재시작은 필요 없습니다.
4. `cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'`에 `mtls-on`이 나와야 합니다.
5. 서로 다른 노드에 있는 `mtls-on`의 클라이언트에서 `mtls-on`의 서버로 요청: 노드의 `tcpdump -i eth0 port 15008`에 HBONE 패킷이 보입니다.
6. `mtls-on` 클라이언트에서 `mtls-off` 서버로 요청: 가입/비가입 혼합 트래픽은 지원되지 않으므로 실패해야 합니다.
7. 정리: `kubectl label ns mtls-on io.cilium/mtls-enabled-`, 네임스페이스 삭제, `encryption.enabled=false`, `cilium-ztunnel-secrets` 삭제.

### 실습 4: 정책 audit, CIDR 그룹, deny

1. 네임스페이스 `pol`에 `client`와 `server` Pod(8080 HTTP)를 만듭니다.
2. server endpoint에 audit 모드를 켭니다: `cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled`.
3. `app=client`에서 8080 ingress만 허용하는 CNP를 적용합니다. 세 번째 Pod에서 서버로 curl하고 `hubble observe --verdict AUDIT -n pol`을 실행하면 세 번째 Pod에 대해 `AUDIT` verdict가 보이고 요청은 여전히 성공합니다.
4. `PolicyAuditMode=Disabled`로 끄고 반복하면 요청이 드롭됩니다(`hubble observe --verdict DROPPED`).
5. `CiliumCIDRGroup`(위 매니페스트)과 `cidrGroupRef`를 쓰는 egress `toCIDRSet` 규칙을 추가하고, `cilium-dbg identity list`에 CIDR 파생 identity가 보이고 flow에 그룹이 주석으로 붙는지 확인합니다.
6. `app=client`에 대한 `ingressDeny` 규칙을 추가하면 allow 규칙이 있어도 클라이언트가 드롭됩니다(deny 우선).
7. 정리: 네임스페이스와 CCG 삭제.

### 실습 5: Hubble export, 마스킹, cert-manager

사전 조건: cert-manager와 ClusterIssuer가 설치되어 있어야 합니다.

1. Relay와 동적 export 활성화: `hubble.relay.enabled=true`, `hubble.export.dynamic.enabled=true`, `hubble.redact.enabled=true`, `hubble.redact.http.urlQuery=true`, `hubble.tls.auto.method=certmanager`와 `certManagerIssuerRef`.
2. ConfigMap `cilium-flowlog-config`에 `source_pod: ["kube-system/"]` 같은 `includeFilters`를 가진 exporter 항목을 추가합니다. agent 재시작 없이 agent Pod의 Hubble export 디렉터리에 새 파일이 나타나야 합니다(약 1분).
3. 쿼리 문자열과 `Authorization` 헤더가 있는 L7 가시성 HTTP 트래픽을 보냅니다(Pod에 L7 정책이 있어야 가시성 확보). `hubble observe -o json`에서 쿼리와 헤더 값이 마스킹되어야 합니다.
4. `kubectl get certificate -n kube-system`: Hubble 인증서가 사용한 ClusterIssuer로 발급되어 있어야 합니다.
5. 롤백: exporter 항목을 제거하고 `hubble.redact.enabled=false`로 하며 인증서 방식을 되돌립니다.

## 버전별 변경 사항

| 주제 | 1.18 | 1.19 | 1.20 | 1.21 pre-release |
|---|---|---|---|---|
| Mutual Authentication | Beta | Beta, 기본 비활성(`authentication.enabled=false`) | Deprecated | 제거. 정책 `authentication` 필드는 미사용 |
| ztunnel | - | 도입 (beta); 시작 시 검증이 이미 ClusterMesh를 거부(`pkg/ztunnel/cell.go:46`) | `ca.type` internal/spire, 이미지 `quay.io/cilium/ztunnel` | Beta. `ca.type=spire`용으로 SPIRE 차트 재사용 |
| Strict 모드 플래그 | `strictMode.{enabled,cidr,allowRemoteNodeIdentities}`만 존재 | `strictMode.egress.*`, `strictMode.ingress.*` 추가, 이전 플래그 deprecated | 이전 플래그 제거 (`...-egress-*` 이름) | 변화 없음 |
| IPsec | `encryptedOverlay` no-op | - | `encryptedOverlay`, `ipsec.interface` 제거 | - |
| WireGuard `nodeEncryption` | 확인 안 함 | 확인 안 함 | beta | Deprecated, 1.22 제거 |
| 정책 | Kafka/proxylib deprecated | `FromRequires`/`ToRequires` 비어 있어야 함 | Kafka/proxylib 제거, CEL이 빈 CNP/CCNP 거부, ClusterNetworkPolicy | `toPorts[].listener` 리다이렉트 |
| Hubble | - | export `fieldAggregate`/`aggregationInterval` | Kafka 메트릭/마스킹 제거, ClusterMesh 인증서 기본 1년, certgen CA 유효기간 검사 | Pod별 인증서, `portName`, UI `httpRoute` |
| Identity | Double Write 문서화 | 문서화 | 문서화 | `preflight migrate-identity` deprecated |

## 문제 해결

| 증상 | 가능한 원인 | 확인 |
|---|---|---|
| 새 Pod에서 잠시 정책 드롭 | Pod가 아직 `reserved:init`이거나 ipcache 전파 전 | `cilium-dbg endpoint list`, `cilium-dbg bpf ipcache get <ip>` |
| `fromEntities: cluster`가 NodePort 트래픽을 예상과 다르게 매칭 | 라우팅 모드에 따라 출발 identity가 `world` 또는 `remote-node` | 위 entity 주의사항, `hubble observe`로 identity 확인 |
| identity 수가 계속 증가 | 변동이 큰 레이블이 identity에 사용됨 | `kubectl get ciliumidentities \| wc -l`, 해당 레이블 제외 |
| CNP 적용이 "spec or specs must be provided"로 거부됨 | 1.20 CEL 규칙 | `spec` 또는 `specs` 제공 |
| WireGuard 피어 수가 다르거나 `cilium_wg0` 없음 | 커널 모듈 없음 또는 노드 간 UDP 51871 차단 | `cilium-dbg status \| grep Encryption`, 노드 보안 그룹 |
| 암호화 시 큰 패킷이 멈춤 | 암호화와 터널을 합치면 MTU가 너무 큼 | `ping -M do`로 테스트, CNI chaining 플래그 확인 |
| IPsec 오류 카운터 증가 | 키 불일치 또는 오래된 XFRM 상태 | `cilium-dbg encrypt status`, 키 회전으로 오래된 상태 정리 |
| IPsec에서 host policy 효과 없음 | 지원되지 않는 조합 | WireGuard 사용 또는 host policy 제거 |
| 네임스페이스 가입했는데 HBONE 패킷 없음 | 양쪽 모두 가입하지 않았거나 host-network Pod, UDP 트래픽 | `statedb dump`, Pod 종류, 프로토콜 |
| ztunnel 활성화 후 agent 시작 실패 | ClusterMesh 활성화됨 | 둘 중 하나 비활성화 |
| 1년 뒤 Hubble Relay 인증서 오류 | `helm` 방식은 자동 갱신 안 됨 | `cronJob`/`certmanager`로 전환 또는 최소 연 1회 Helm 업그레이드 |
| 1.21 이후 `authentication`이 있는 정책이 인증하지 않음 | 기능 제거 | 위 마이그레이션 절차 |

## 검증 한계와 출처

실습은 이번 검토에서 실제 클러스터에 실행하지 않았고 아래 태그의 업스트림 소스와 문서를 기준으로 확인했습니다. Tetragon, ztunnel `ca.type=spire` end-to-end 흐름, IPsec ESP/UDP 방화벽 요구사항, 남아 있는 `authentication` 정책 필드의 런타임 동작은 확인하지 못했으며 본문에 표시했습니다. **[1.21 pre-release]** 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다. 의도적으로 옮기지 않은 업스트림 불일치: FQDN 호스트명당 IP 한도(문서 대 코드 기본값), 산문과 `values.yaml`이 다른 Hubble 인증서 기본 유효기간, 저장 버전은 `v2`인데 `v2alpha1`을 보여 주는 `CiliumCIDRGroup` 문서, `policyCIDRMatchMode` 값 주석.

- [1.20 업그레이드 노트](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc), [Mutual Authentication (1.20)](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst), [Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml), [정책 개요](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/policy.rst)
- [투명 암호화](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption.rst), [WireGuard](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-wireguard.rst), [IPsec](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-ipsec.rst), [CNP CEL 규칙](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/v2/cnp_types.go)
- [1.21 업그레이드 노트 (pre-release)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc), [ztunnel 가이드 (pre-release)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/network/encryption-ztunnel.rst), [identity 할당과 Double Write](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade.rst), [숫자 identity](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/identity/numericidentity.go), [정책 layer 3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/policy/layer3.rst), [Hubble TLS](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/tls.rst), [Hubble export](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/export.rst)

## 퀴즈

[mTLS, 암호화, identity 이해도 확인하기](../../quizzes/networking/cilium/12-mtls-encryption-identity-quiz.md).

[메인 페이지로 돌아가기](README.md)
