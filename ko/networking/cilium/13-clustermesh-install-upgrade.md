# Part 13: 버전, 설치/업그레이드, Cluster Mesh

> **검토 기준**: Cilium 1.20.2 (안정, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. **[1.21 pre-release]** 표시 항목은 v1.21.0-pre.3 기준이며 GA 전에 바뀔 수 있습니다.
> **마지막 업데이트**: 2026년 10월 15일

이 장은 앞선 파트에서 간단히만 다룬 세 가지 운영 질문에 답합니다. 어떤 버전에 어떤 기능이 어떤 성숙도로 들어 있는지, 안전하게 설치하고 업그레이드하는 방법(EKS 세부 사항 포함), 그리고 Cluster Mesh가 control plane부터 어떻게 동작하는지입니다. 저장소에는 [IPAM 및 네트워크 정책](04-ipam-policy.md) 안의 짧은 Cluster Mesh 절만 있었고, 이 장이 상세 가이드입니다.

관련 파트: [소개](01-introduction.md), [네트워킹](03-networking.md), [IPAM](10-ipam-deep-dive.md), [BGP, LB, Egress](11-bgp-lb-egress-edge.md), [mTLS, 암호화, Identity](12-mtls-encryption-identity.md).

## 목차

1. 릴리스 트레인과 도구 버전
2. 버전별 기능 매트릭스 (1.17 ~ 1.21 pre-release)
3. 1.20.1에서 1.20.2로 바뀐 것
4. 호환성과 요구 사항
5. Helm 설치
6. EKS 설치 세부 사항
7. 업그레이드와 롤백 절차
8. Day-2 구성: drift detection, CiliumNodeConfig, identity 마이그레이션
9. Cluster Mesh 아키텍처
10. Cluster Mesh 구성
11. Global Service, affinity, EndpointSlice 동기화
12. MCS-API
13. Cluster 간 정책
14. EKS에서의 Cluster Mesh
15. 실습
16. 버전 차이, 문제 해결, 검증 한계와 출처

---

## 1. 릴리스 트레인과 도구 버전

Cilium은 서로 다른 버전을 가진 세 가지 산출물로 배포되며, 이들의 버전은 쉽게 혼동할 수 있습니다.

| 산출물 | 이번 검토 시점 | 비고 |
|---|---|---|
| Cilium (agent, operator, Helm chart) | 1.20.2 (2026-09-16) | v1.20.2 트리에서 차트 `version`/`appVersion`이 모두 1.20.2 (`install/kubernetes/cilium/Chart.yaml`) |
| Cilium CLI (`cilium`) | 0.20.1 (2026-09-24) | 0.20.1은 의존성/CI 변경뿐이며 Cilium 의존성을 v1.20.2로 올림 |
| Hubble CLI (`hubble`) | 1.20.2 (2026-10-07) | 이전 태그는 1.19.4이고 1.20.0/1.20.1 Hubble CLI 태그는 없음. 1.20.2는 기본 field mask의 policy-verdict 이벤트 `compact` 출력을 수정 |
| 백포트 브랜치 | 1.19.8, 1.18.14 (둘 다 2026-09-16) | 1.20.2와 같은 날 릴리스 |
| Pre-release | 1.21.0-pre.3 (2026-10-02) | `v1.21.0-pre.1`은 게시되지 않았고 pre.2 changelog가 pre.0부터 pre.2까지를 다룸 |

Cilium CLI는 agent와 별도의 릴리스 트레인입니다. 특정 agent 버전이 필요하면 `--version`을 명시하세요.

| 릴리스 | 날짜 | 비고 |
|---|---|---|
| v1.20.0 | 2026-07-29 | 2660 commits (릴리스 본문) |
| v1.20.1 | 2026-08-18 | Cluster Mesh 문서 개편, agent 재시작 후 CIDR 정책 처리 endpoint 수정 |
| v1.20.2 | 2026-09-16 | 최신 stable, 3절 참고 |
| v1.21.0-pre.0 | 2026-08-03 | |
| v1.21.0-pre.2 | 2026-09-09 | |
| v1.21.0-pre.3 | 2026-10-02 | 최신 pre-release |

1.21.0-pre.x는 미리보기입니다. 옵션 이름, 기본값, 업그레이드 노트가 아직 바뀔 수 있습니다.

## 2. 버전별 기능 매트릭스 (1.17 ~ 1.21 pre-release)

성숙도 표현은 해당 버전의 릴리스 노트나 트리 내 문서(`.. include:: /beta.rst` 배너)를 인용한 것입니다. `-`는 아직 존재하지 않음을 뜻합니다.

### 2.1 핵심 기능

| 기능 | 1.17 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|---|
| 최소 커널 | 5.4 | 5.10 (RHEL 8.10은 4.18) | 5.10 | 5.10 | 5.10 (네이티브 빌드는 LLVM >= 21.1) |
| 테스트된 Kubernetes | 1.17 문서 참고 | 1.33까지 (go libs 1.33) | 1.35 libs | 1.33 ~ 1.36 | 1.34 ~ 1.37 |
| Gateway API CRD | v1.2.1 | v1.3.0 | v1.4 | v1.6.1 | v1.6.1 |
| Helm OCI 차트 `quay.io/cilium/charts/cilium` | 없음 | 없음 | 있음 | 있음 (권장) | 있음 |
| MCS-API | beta (도입) | beta, EndpointSlice mirroring | beta, CRD `v1alpha1`, CRD 자동 설치 | stable, `v1beta1` (`v1alpha1`도 지원) | `v1beta1`; mirrored EndpointSlice 이름 수정 |
| Cluster Mesh 정책 기본 범위 | 모든 클러스터 | 모든 클러스터; `policy-default-local-cluster` 플래그 도입(기본 false) | 로컬 클러스터만 (기본 true) | 로컬 클러스터만; `cluster-mesh` entity | 로컬 클러스터만 |
| `clustermesh.apiserver.tls.authMode` | `legacy` (기본) | `legacy` (기본) | `migration` (기본) | `migration` (기본) | `cluster` (신규 `cluster-strict`) |
| KVStoreMesh | 1.16부터 기본 활성 | `kvstoremesh.enabled` deprecated | 기본 활성 | 기본 활성, 값 deprecated | 항상 활성, 값 제거 |
| Double Write identity 할당 | 도입 (beta) | beta | beta | beta | beta; `cilium-dbg preflight migrate-identity` deprecated |
| Multi-pool IPAM | beta | beta (+KVStore, IPsec, tunnel) | stable | stable; cluster-pool에서 multi-pool로 in-place 마이그레이션 | Azure IPAM이 multi-pool로 이동; `CiliumPodIPPool` API `cilium.io/v2` + `reservedRanges` |
| ENI IPv6 IPAM | - | - | - | beta | ENI 모드에서 IPv6 masquerade 기본 off |
| Mutual authentication (SPIFFE/SPIRE) | 있음 | 있음 | 기본 비활성 | deprecated | 제거 (방화벽 표에서 포트 4250 삭제) |
| ztunnel | - | - | beta | beta (내부 CA 또는 SPIRE) | beta (1.21 트리의 `encryption-ztunnel.rst`에 `beta.rst` 배너가 남아 있음) |
| Kafka-aware L7 정책 | 지원 | deprecated | deprecated | 제거 | 제거 |
| Envoy Go extension (proxylib) | 지원 | deprecated | deprecated | 제거 | 제거 |
| BGPv1 `CiliumBGPPeeringPolicy` | 지원 | deprecated | 제거 | - | - |
| ConfigMap drift detection (`configDriftDetection`) | - | 1.18.x 패치에 백포트 | 1.19.x 패치에 백포트 | 1.20.0에서 기본 제공 | 동일 |
| 데이터패스 모드 | `veth`(기본), `netkit`(beta), `netkit-l2`, `lb-only` | veth, netkit | tunnel에서 BIG TCP, PLPMTUD | `bpf.datapathMode=auto` (지원되면 netkit, 아니면 veth; 기본값은 여전히 veth) | 변경 없음 |

### 2.2 릴리스별 하이라이트

**1.17** (2025-02, 2761 commits): QoS pod annotation(Guaranteed/Burstable/BestEffort egress 우선순위), MCS-API 도입, 프로토콜별(TCP/UDP) 서비스 로드 밸런싱, Service별 LB 알고리즘(maglev/random), `loadBalancerSourceRanges` deny-list 모드, 태그 기반 AWS 고정 IP와 단일 IP multi-pool, 동적 MTU, `CiliumCIDRGroup` 레이블 선택, 포트 범위 HTTP 정책, 정적 Gateway 주소를 지원하는 Gateway API 1.2.1, 동적 Hubble metrics ConfigMap, Double Write identity 할당 모드(KVStore와 CRD 간 마이그레이션).

**1.18** (3298 commits): LB control plane 재설계, VXLAN-in-IPsec, 다중 egress gateway(IPv6 범위 포함), bandwidth ingress rate limit, tunnel용 IPv6 underlay, Hubble 정책 이름과 `policy log` 필드, `cluster` entity를 로컬 클러스터로 제한하는 옵션, `k8s.apiServerURLs` apiserver failover, BGP CRD와 `CiliumCIDRGroup`, `CiliumLoadBalancerIPPool`의 stable `cilium.io/v2` 승격, ENI 모드 AWS prefix delegation, Gateway API 1.3.0과 `CiliumGatewayClassConfig`, 최소 커널 5.10. 동작 변경: ENI 모드에서 `enableIPv4Masquerade` 기본값이 true에서 false로 바뀌었고(1.18 미만은 `upgradeCompatibility`를 쓰거나 명시 설정), ENI 모드 operator에 `ec2:DescribeRouteTables`가 필요하며, 기본 identity 레이블에 `io.cilium.k8s.policy.serviceaccount`가 추가되어 업그레이드 중 일시적 identity 변동이 발생합니다.

**1.19** (2934 commits): 정책 기본 범위 로컬 클러스터 활성화, mutual authentication 기본 비활성화, multi-pool IPAM stable, OCI Helm 차트, ztunnel beta, IPsec/WireGuard strict 암호화 모드, Kafka 정책 필드 deprecated와 `FromRequires/ToRequires` 제거, BGPv1 제거, MCS-API CRD 자동 설치(`clustermesh.mcsapi.installCRDs`), 인증서 생성 개편(CronJob이 더 이상 Helm hook이 아니어서 Argo CD와 `--wait`에 친화적), Gateway API 1.4, GAMMA GRPCRoute.

**1.20** (2026-07-29): Gateway API 1.6.1(ListenerSet, BackendTLSPolicy, TCPRoute/UDPRoute, ExternalAuth, CORS), datapath plugin, `bpf.datapathMode=auto`, egress gateway IPv6 egress IP, `cilium-dbg shell -- bgp/*` 기반 BGP와 GoBGP 4.6.1, ENI IPv6(beta), cluster-pool에서 multi-pool로 in-place 마이그레이션, `PreferSameZone`/`PreferSameNode` traffic distribution, `service.cilium.io/weight` Maglev 가중치(0은 drain), MCS-API stable, `cluster-mesh` 정책 entity, Kubernetes ClusterNetworkPolicy admin/baseline tier, ConfigMap drift detection, `cilium-cni` 바이너리 77 MB에서 16 MB로 축소, K8s 1.36, Envoy 1.37.x. **1.20에서 제거**: Envoy Go extension(proxylib), Kafka-aware L7 정책, `CiliumNodeConfig` `v2alpha1`, `clustermesh.enableMCSAPISupport`(`clustermesh.mcsapi.enabled` 사용), Cluster Mesh 인증서의 값 전달 방식, `cilium-docker-plugin`, 이전 `encryption.strictMode.*` 플래그(`encryption.strictMode.egress.*`로 대체), `--node-port-algorithm`/`--node-port-mode`, `--ces-slice-mode`, `encryption.ipsec.interface`. **동작 변경**: `bpf.tproxy=true`는 netkit과 호환되지 않음, SocketLB가 없거나 `socketLB.hostNamespaceOnly=true`인 Pod의 클러스터 내부 NodePort 접근은 client Pod에서 로드 밸런싱되므로 client egress와 backend ingress 정책이 모두 허용해야 함, 빈 `CiliumNetworkPolicy`/`CiliumClusterwideNetworkPolicy`(`spec`/`specs` 없음)는 admission에서 거부됨, Cluster Mesh 자동 인증서는 기본 유효기간 1년에 CronJob이 4개월마다 재생성하며 certgen은 CA 유효기간 >= leaf 유효기간을 강제함(`certgen.enforceCAValidityThroughoutLeavesDuration=false`로 비활성화).

**1.21 pre-release** (v1.21.0-pre.3): delta xDS(`envoy.xdsMode=delta-split`), Cilium Network Driver(DRA, SR-IOV), Gateway API session persistence, 정책의 AWS managed prefix list, KVStoreMesh 무조건 활성, Cluster Mesh `authMode` 기본값 `cluster`, mutual authentication 제거, `encryption.nodeEncryption`(WireGuard) deprecated(1.22 제거 예정), operator 플래그 `--aws-use-primary-address` 제거(`eni.nodeSpec.usePrimaryAddress` 사용), Gateway/GAMMA 인프라 metadata의 `cec.cilium.io/*` annotation이 생성된 `CiliumEnvoyConfig`로 더 이상 전파되지 않음, operator의 storage version 자동 마이그레이션, Kubernetes 라이브러리 1.37. pre.2 릴리스 노트의 "Enable BPF masquerading by default"는 pre.3 트리에 반영되어 있지 않습니다(검증 한계 참고).

## 3. 1.20.1에서 1.20.2로 바뀐 것

`gh api repos/cilium/cilium/compare/v1.20.1...v1.20.2`는 204 commits를 보고합니다(API가 파일 목록을 300개로 잘라 내므로 변경 파일 수는 신뢰할 수 없습니다). commit 목록에서 기능성 항목을 감사하지 않았으므로 업그레이드 위험이 낮다고 가정하기 전에 릴리스 노트를 읽으세요. 일부 구성에는 중요한 수정이 있습니다.

| 영역 | 수정 |
|---|---|
| AWS ENI IPAM | operator가 prefix-delegated IP를 사용 중인데도 개별 IP로 해제하던 문제, subnet의 prefix가 소진되면 할당이 실패하던 문제, `ipv4NativeRoutingCIDR`이 보조 VPC CIDR일 때 ENI 모드 agent가 시작 시 crash하던 문제, IPv6 ENI 라우팅(health endpoint, ingress, IPsec), masquerade 설정 변경 후 ENI endpoint 라우팅 규칙 복원, EC2 IMDS 부하 감소 |
| Cluster Mesh | 제거된 원격 클러스터가 연결된 채 남는 드문 race, Cluster Mesh에서 받은 service backend 검증 강화, 설정 변경 시 clustermesh-apiserver etcd 사용자 관리가 오래된 role을 회수하지 않던 문제(Helm 차트 사용자는 영향 없음) |
| 업그레이드 | Cilium 1.15 이하로 만든 클러스터가 `CiliumNodeConfig` `v2alpha1` CRD 버전이 빠져 업그레이드에 실패하던 문제. 이런 클러스터는 1.20.2 이상으로 올릴 것 |
| 무시되던 옵션 | 받아들여지지만 조용히 무시되던 옵션 다섯 개가 동작: `vtep-sync-interval`, `enable-xt-socket-fallback`, 사용자 CNI config 사용 시 `eni-delete-on-termination`, chaining 모드 밖의 Helm `enableIdentityMark`, `lb-retry-backoff-max`; sink에 도달하지 못하던 Hubble 설정 네 개도 수정 |
| 데이터패스 | WireGuard로 오분류되는 fragmented UDP, SNAT LB 트래픽의 ICMP error checksum, DSR 복구와 PMTU ICMP source, `externalTrafficPolicy: Local`의 L2 announcement, LocalRedirectPolicy 회귀, `policy-deny-response: icmp` egress deny metric |
| 정책 | NetworkPolicy 변경 직후 생성된 Pod가 최대 2분간 오래된 revision을 표시, named port의 동시 policy map crash, identity가 예상의 두 배 시간 동안 남던 문제 |
| Gateway API | `HTTPRoute` ExternalAuth가 잘못된 `backendRef`에서 fail closed로 동작, `bpf.tproxy`가 false(기본값)일 때 Gateway API에 iptables와 netfilter TPROXY 모듈이 필요하다는 문서 보강 |
| BGP | `defaultGateway` peer 자동 탐색이 잘못된 라우팅 테이블을 고르던 문제 |

1.20.2의 이미지/차트 변경: certgen v0.4.9에서 v0.4.11, Envoy v1.37.5에서 v1.37.6, hubble-ui v0.13.5에서 v0.13.6, SPIRE 1.15.2에서 1.15.3. `values.yaml` diff는 이미지 태그와 schema annotation 하나뿐이며 `enable-identity-mark` ConfigMap 키는 이제 `enableIdentityMark`가 설정될 때만 렌더링됩니다.

1.20.2 문서 변경: `system_requirements.rst`의 필수 커널 설정 목록에서 `CONFIG_CRYPTO_USER_API_HASH`와 `CONFIG_INET_XFRM_MODE_TUNNEL`이 빠졌고, Cluster Mesh 소개에 "Security" 절이 추가되었습니다. mesh로 연결된 모든 클러스터는 하나의 trust domain이므로 서로 신뢰하고 보안 수준이 동등한 클러스터만 연결해야 합니다.

권고: ENI 사용자, Cluster Mesh 배포, Cilium 1.15 이하로 만든 클러스터에는 `--version 1.20.2`를 사용하세요.

## 4. 호환성과 요구 사항

### 4.1 버전 호환성

| 항목 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|
| Kubernetes (테스트됨) | 1.33, 1.34, 1.35, 1.36 | 1.34, 1.35, 1.36, 1.37 |
| Linux 커널 | >= 5.10 (RHEL 8.10은 4.18) | >= 5.10 |
| clang/LLVM (네이티브 agent 빌드에만 해당) | >= 18.1 | >= 21.1 |
| Gateway API CRD | v1.6.1 필수 | v1.6.1 |
| Helm 차트 `kubeVersion` | `>= 1.21.0-0` (차트 제약이며 테스트 범위가 아님) | 동일 |
| Cilium CLI | 0.20.1 | 해당 없음 |
| Hubble CLI | 1.20.2 | 해당 없음 |

1.20.2 시스템 요구 사항의 기능별 커널 최소 버전: multicast는 AMD64 >= 5.10, AArch64 >= 6.0, IPv6 BIG TCP >= 5.19, IPv4 BIG TCP >= 6.3, netkit >= 6.8 (`CONFIG_NETKIT=y`). 1.19 노트: IPsec, kube-proxy replacement, BPF masquerade를 함께 쓰면 BPF host routing이 자동 활성화되며 이때 CVE-2025-37959 수정이 포함된 커널이 필요합니다.

Cluster Mesh에는 추가 제약이 있습니다. 연결된 모든 클러스터의 Cilium 버전은 minor가 하나 이내로만 달라야 합니다(예: 1.19.x는 1.18.x, 1.20.x와 연결 가능하지만 1.17.x와는 불가).

### 4.2 포트

노드 간에 security group 참조 또는 private CIDR로만 열고 `0.0.0.0/0`은 절대 사용하지 않습니다.

| 포트 | 용도 |
|---|---|
| UDP 8472 | VXLAN tunnel |
| UDP 6081 | Geneve tunnel |
| TCP 4240 + ICMP type 8/0 | Health check |
| TCP 4244 | Hubble server |
| TCP 4245 | Hubble Relay |
| UDP 51871 | WireGuard |
| ESP (IP protocol 50) | IPsec (AWS security group은 규칙이 없으면 ESP를 막음) |
| TCP 4250 | Mutual authentication (1.20 문서에 있고 1.21 문서에서는 제거) |
| TCP 2379 | 클러스터 간 clustermesh-apiserver |

### 4.3 Gateway API CRD

Cilium 1.20은 Gateway API CRD v1.6.1을 요구합니다(`Documentation/conf.py`의 `gateway_api_version = 'v1.6.1'`, `go.mod`의 `sigs.k8s.io/gateway-api v1.6.1`). Helm 차트는 CRD를 설치하지 않습니다. 필수 CRD는 GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant, BackendTLSPolicy, TLSRoute이고, TCPRoute, UDPRoute, ListenerSet은 선택이며 없으면 해당 기능이 비활성화됩니다. 전제 조건은 `kubeProxyReplacement=true`, `l7Proxy=true`, 그리고 `bpf.tproxy=true`(beta)가 아니면 iptables와 TPROXY 모듈입니다. `kubectl apply --server-side`로 적용합니다.

TLSRoute 함정: 이미 TLSRoute를 쓰고 있다면 `v1alpha2`를 포함한 experimental 채널의 TLSRoute v1.6.1을 설치하세요. standard 채널 v1.6 TLSRoute를 설치하면 기존 TLSRoute 객체가 읽히지 않게 됩니다(사실상 사라짐). 먼저 백업합니다(`kubectl get tlsroutes -A -o yaml`).

## 5. Helm 설치

Helm 차트는 두 위치에서 제공됩니다.

| 위치 | 상태 |
|---|---|
| `oci://quay.io/cilium/charts/cilium` | 1.19부터 문서에서 권장; cosign 서명, digest 고정 가능 |
| `https://helm.cilium.io/` (`helm repo add cilium`) | 클래식 저장소, 완전히 지원 |

차트 버전에는 `v` 접두사가 없고(`--version 1.20.2`) 이미지 태그에는 있습니다. OCI 레지스트리는 `helm search`를 지원하지 않으므로 `crane ls quay.io/cilium/charts/cilium`으로 버전을 조회합니다. 차트 서명 검증:

```bash
cosign verify \
  --certificate-identity-regexp='https://github.com/cilium/cilium/.*' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  quay.io/cilium/charts/cilium:1.20.2
```

값은 버전 관리되는 파일에 두고 `-f values.yaml`로 설치하세요. 7절에서 보듯 minor를 올릴 때마다 값을 다시 전달해야 하므로 `--set` 플래그 더미에 의존하면 안 됩니다.

## 6. EKS 설치 세부 사항

### 6.1 모드 선택

| 모드 | Helm | 데이터패스 / IPAM | 비고 |
|---|---|---|---|
| ENI (EKS의 upstream 기본) | `eni.enabled=true` | Native routing (`eni.enabled`이면 차트가 `routingMode`를 native로 기본 설정), AWS ENI IPAM, Kubernetes CRD datastore | Pod가 VPC 라우팅 가능 IP를 받음; operator에 EC2 API 권한 필요; Cilium 노드에서 `aws-node`가 실행되면 안 됨 |
| Overlay | `eni.enabled` 생략 (차트 기본은 tunnel/VXLAN) | VXLAN, cluster-pool IPAM | ENI 한도보다 많은 Pod를 노드에 배치 가능; Pod에서 VPC로 가는 트래픽은 노드 IP로 SNAT; EKS API 서버가 overlay Pod IP로 라우팅할 수 없으므로 webhook은 hostNetwork이거나 Service/ingress로 노출; VPC CNI가 남긴 `AWS-SNAT-CHAIN-0/1`, `AWS-CONNMARK-CHAIN-0/1` iptables chain을 flush |
| VPC CNI 위 chaining | `cni.chainingMode=aws-cni`, `cni.exclusive=false`, `enableIPv4Masquerade=false`, `routingMode=native` | 네트워킹은 VPC CNI, 정책/가시성은 Cilium | VPC CNI >= 1.11.2 필요; 활성화 후 기존 Pod 재시작. chaining 제한은 upstream(`cni-chaining-limitations.rst`)에 있으므로 선택 전에 읽을 것 |
| EKS Hybrid Nodes | AWS 빌드 차트 `oci://public.ecr.aws/eks/cilium/cilium` | VXLAN overlay, cluster-pool | 6.4 참고 |
| EKS Auto Mode | 지원 안 됨 | 해당 없음 | 6.5 참고 |

### 6.2 ENI 모드 설치

Cilium이 ENI를 관리하므로 Cilium이 관리하는 노드에서 VPC CNI가 실행되지 않게 해야 합니다. 어느 노드와도 일치하지 않는 node selector로 `aws-node` DaemonSet을 patch합니다(upstream 명령 그대로).

```bash
kubectl -n kube-system patch daemonset aws-node --type='strategic' \
  -p='{"spec":{"template":{"spec":{"nodeSelector":{"io.cilium/aws-node-enabled":"true"}}}}}'
```

애플리케이션 Pod가 Cilium을 기다리도록 managed node group에 taint를 붙입니다(upstream 권장).

```yaml
# eksctl ClusterConfig 일부
managedNodeGroups:
- name: ng-1
  taints:
  - key: "node.cilium.io/agent-not-ready"
    value: "true"
    effect: "NoExecute"
```

values 파일입니다. 모든 키는 1.20.2 차트에 존재하며, `eni.enabled=true`가 operator 이미지, endpoint route, CiliumNode 관리, IPv4 masquerade 기본값을 설정합니다. `eni.enabled=true` 없이 `ipam.mode=eni`를 설정하면 차트 검증이 실패합니다.

```yaml
# values-eks-eni.yaml  (Cilium 1.20.2)
eni:
  enabled: true
kubeProxyReplacement: true
k8sServiceHost: <EKS-API-ENDPOINT-FQDN-scheme-없이>
k8sServicePort: 443
cluster:
  name: eks-a
  id: 1   # ENI 모드에서는 128 미만 유지 (Helm 참조의 cluster.id 항목 참고)
```

```bash
helm install cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f values-eks-eni.yaml
```

참고 사항:

- kube-proxy replacement를 쓰면 kube-proxy를 제거하기 전에 `k8sServiceHost`와 `k8sServicePort`를 설정해야 합니다. 그렇지 않으면 agent가 API 서버에 도달하지 못합니다.
- operator에는 EC2 권한(upstream `ec2privileges` 절)이 필요하고, 1.18부터 `ec2:DescribeRouteTables`도 필요합니다.
- 1.18에서 ENI 모드의 `enableIPv4Masquerade` 기본값이 false로 바뀌었습니다. 1.18 이전 ENI 클러스터를 올리면서 masquerade에 의존한다면 명시적으로 설정하거나 `upgradeCompatibility`를 사용하세요.
- ENI IPv6는 1.20에서 beta입니다(`eni.rst`). upstream 한 페이지(`requirements-eks.rst`)는 아직 ENI가 IPv4 전용이라고 쓰고 있으므로 릴리스 노트와 `eni.rst`를 따르세요.
- ENI에는 1.20.2를 쓰세요. prefix delegation 해제, subnet prefix 소진 시 할당, 보조 VPC CIDR native routing crash가 수정되었습니다.
- Pod IP는 `default` pool에서 나오며 ENI 모드에서는 `CiliumPodIPPool`과 `ipam.cilium.io/ip-pool` annotation을 쓰지 않습니다(`eni.rst`). [IPAM](10-ipam-deep-dive.md)을 참고하세요.

### 6.3 AMI

1.20.2 시스템 요구 사항은 Amazon Linux 2와 Bottlerocket을 "all"로, Ubuntu >= 20.04, RHEL >= 8.6, Talos >= 1.5.0, Flatcar(ENI의 DHCP 주의 사항 포함)를 지원 대상으로 나열합니다. Amazon Linux 2023은 이름으로 나열되어 있지 않습니다. 커널이 5.10 최소 요구보다 새롭다는 것은 추론일 뿐 upstream의 진술이 아닙니다. AWS Hybrid Nodes 문서는 Ubuntu 20.04와 RHEL 8이 Cilium 1.18.3의 커널 요구를 충족하지 못한다고 설명합니다.

### 6.4 EKS Hybrid Nodes

AWS는 공개 ECR 저장소 `oci://public.ecr.aws/eks/cilium/cilium`의 AWS 유지 보수 빌드를 통한 Cilium만 hybrid node에서 지원합니다(AWS 문서에는 `1.17.9-0`, `1.18.3-0` 같은 버전이 나오며 더 새로운 AWS 빌드 목록은 이번 검토에서 확인하지 못했습니다). VPC CNI는 hybrid node와 호환되지 않습니다. AWS 기본 구성은 VXLAN overlay와 cluster-pool IPAM이며, pool CIDR은 EKS remote Pod network와 같아야 하고 node, VPC, Service CIDR과 겹치면 안 되며 배포 후 바꾸면 안 됩니다. agent와 operator는 `eks.amazonaws.com/compute-type In hybrid` affinity로 hybrid node에 고정하고, Pod CIDR을 라우팅 가능하게 하려면 BGP Control Plane을 사용합니다. AWS 지원 표는 hybrid node에서 Cilium Ingress와 Cilium Gateway를 지원 항목(기본 구성)으로 나열합니다([CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html), [Ingress](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-ingress.html) 페이지). `envoy.enabled: false`는 AWS 기준 예시 values에만 있으며, Cilium Ingress/Gateway와 L7 network policy는 Envoy가 필요하므로 사용한다면 AWS ingress 페이지에 따라 활성화하세요. 해당 구성에서 Cilium은 AWS 클라우드 노드에서는 지원되지 않습니다.

### 6.5 EKS Auto Mode

EKS Auto Mode는 Cilium과 함께 동작하지 않습니다. AWS는 Auto Mode가 대체 CNI 플러그인과 network policy 플러그인을 지원하지 않는다고 문서화하고 있으며(EKS 사용자 가이드의 alternate CNI plugins, auto networking 페이지), upstream Cilium 문서에도 Auto Mode 페이지가 없습니다. Cilium에는 일반 managed node group 또는 self-managed 노드를 사용하세요.

### 6.6 이 저장소의 노출 규칙

이 장의 어떤 내용도 public listener를 요구하지 않습니다. VPC 밖 클라이언트가 애플리케이션에 접근해야 한다면 CloudFront와 VPC origin을 통한 internal ALB/NLB를 사용하세요. clustermesh-apiserver Service도 internal이어야 합니다(14절).

## 7. 업그레이드와 롤백 절차

### 7.1 규칙

1. 연속된 minor 사이의 업그레이드와 롤백만 테스트됩니다(1.19에서 1.20, 그리고 되돌리기). minor를 건너뛰지 마세요.
2. 먼저 현재 minor의 최신 패치로 올려서 모든 수정이 포함된 롤백 대상을 확보하세요.
3. 모든 구성 요소(agent, operator, Hubble Relay, clustermesh-apiserver)를 같은 버전으로 올립니다. agent만 올리지 마세요.
4. L3/L4 트래픽은 영향이 거의 없거나 없지만, user-space proxy를 지나는 연결(L7 정책, Ingress, Gateway API, Envoy)은 끊기며 client가 재연결해야 합니다. 새 정책 규칙은 해당 노드의 agent가 돌아올 때까지 보류됩니다.
5. minor를 넘는 `helm upgrade --reuse-values`는 쓰지 마세요. 새 차트 기본값을 무시해 깨진 manifest가 렌더링될 수 있습니다. `--reuse-values`는 차트 버전이 같을 때(이 장 뒤쪽 Cluster Mesh 설정 업그레이드처럼)만 허용됩니다.
6. `upgradeCompatibility`는 업그레이드 직전 버전이 아니라 처음 설치한 minor로 설정하세요. 렌더링되는 ConfigMap에 예전 기본값을 고정합니다. 예를 들어 1.18 이전의 ENI masquerade 기본값을 복원합니다.
7. Cilium 1.15 이하로 만든 클러스터는 1.20.0/1.20.1이 아니라 1.20.2 이상으로 올리세요.

### 7.2 절차

```bash
# 0. 현재 값을 저장하고 이름이 바뀌었거나 제거된 키를 검토
helm get values cilium -n kube-system -o yaml > old-values.yaml

# 1. Pre-flight: 모든 노드에 새 이미지를 미리 받고 기존 CNP를 검증
helm install cilium-preflight oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system \
  --set preflight.enabled=true --set agent=false --set operator.enabled=false
#   (kube-proxy replacement를 쓰면 k8sServiceHost/k8sServicePort도 추가)
kubectl -n kube-system get ds cilium-pre-flight-check      # READY가 노드 수와 같아야 함
kubectl -n kube-system get deploy cilium-pre-flight-check  # 1/1이어야 함
kubectl -n kube-system logs deployment/cilium-pre-flight-check -c cnp-validator --previous
helm delete cilium-preflight -n kube-system

# 2. 업그레이드 (--reuse-values 사용 금지); 이 예시는 처음 설치한 minor가 1.19
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f old-values.yaml --set upgradeCompatibility=1.19

# 3. 관찰
kubectl -n kube-system rollout status ds/cilium
kubectl -n kube-system rollout status deploy/cilium-operator
cilium status --wait
```

pre-flight Deployment가 `READY 0/1`에 머물면 기존 CiliumNetworkPolicy 중 하나 이상이 새 버전에서 검증에 실패한다는 뜻입니다. 업그레이드 전에 정책을 고치세요.

### 7.3 롤백

```bash
helm history cilium -n kube-system
helm rollback cilium <REVISION> -n kube-system
# 또는 DaemonSet만:
kubectl -n kube-system rollout undo daemonset/cilium
```

새 minor의 기능(새 CR, ConfigMap opt-in)을 이미 사용했다면 롤백 전에 해당 버전의 업그레이드 노트를 읽으세요. 롤백은 이전 manifest를 복원하지만 새 버전이 만든 객체까지 되돌리지는 않습니다.

### 7.4 CRD 처리

| CRD 계열 | 설치/갱신 주체 | 조치 |
|---|---|---|
| Cilium CRD (`cilium.io`) | operator/agent가 시작 시 등록·갱신 | 별도 조치는 없으나 업그레이드 후 `kubectl get crd \| grep cilium.io`로 확인. 1.20에서 `CiliumNodeConfig` `v2alpha1`이 제거되었으므로 `cilium.io/v2` 사용 |
| Gateway API | 사용자(수동, `kubectl apply --server-side`) | 4.3절의 버전에 맞추고 TLSRoute를 먼저 백업 |
| MCS-API (`multicluster.x-k8s.io`) | `clustermesh.mcsapi.enabled=true`이면 차트가 설치(1.19부터), `clustermesh.mcsapi.installCRDs=false`이면 제외 | 다른 컨트롤러가 CRD를 소유하면 `installCRDs=false` |
| 오래된 저장 버전 | **[1.21 pre-release]** operator가 storage version을 자동 마이그레이션 | `CiliumPodIPPool` `v2`가 storage version이 됨 |

### 7.5 minor별 확인 항목

대상 minor의 "Upgrade Notes"는 항상 읽으세요. 자주 문제가 되는 항목은 ENI masquerade 기본값과 `ec2:DescribeRouteTables`(1.18), service-account 레이블 추가로 인한 identity 변동(1.18), `policy-default-local-cluster`가 true로 전환(1.19, 13절), mutual authentication 기본 비활성화(1.19), 제거된 옵션과 Kafka/proxylib 제거(1.20), netkit과 `bpf.tproxy` 조합 및 NodePort client 측 로드 밸런싱(1.20), `authMode=cluster` 기본값과 `kvstoremesh.enabled` 값 제거(1.21 pre-release)입니다.

## 8. Day-2 구성

### 8.1 ConfigMap drift detection

많은 옵션은 agent를 재시작해야 적용됩니다. `cilium-config` ConfigMap을 수정(`helm upgrade` 또는 `cilium config set`)하면 실행 중인 agent와 ConfigMap이 달라질 수 있고, drift detection은 이를 관측 가능하게 만듭니다. 1.20.0에서 기본 제공되며 1.18.x와 1.19.x 패치 릴리스로 백포트되었습니다(v1.18.14, v1.19.8 차트에는 있고 v1.18.0, v1.19.0에는 없음).

```yaml
configDriftDetection:
  enabled: true        # enable-dynamic-config: ConfigMap 감시
  driftChecker: true   # enable-drift-checker: 원하는 값과 실제 값 비교
  ignoredKeys: []      # 의도적으로 다른 키, 예: ["devices"]
```

agent는 불일치한 키마다 warning을 기록하고 gauge `cilium_drift_checker_config_delta`를 노출합니다. `0`이면 일치하고, 0보다 크면 agent가 현재 ConfigMap을 적용하지 못했으므로 재시작이 필요합니다. 롤아웃 허용 시간보다 오래 `cilium_drift_checker_config_delta > 0`이면 알림을 보내세요.

`cilium config set <key> <value>`는 ConfigMap을 수정하고 기본적으로 agent를 재시작합니다. `--restart=false`를 주면 재시작을 미루고 drift gauge로 보류 변경을 확인할 수 있습니다.

### 8.2 CiliumNodeConfig (노드별 override)

`CiliumNodeConfig`(`apiVersion: cilium.io/v2`, 네임스페이스 `kube-system`)는 `spec.nodeSelector`가 선택한 노드에서 ConfigMap/agent 키를 덮어씁니다(빈 selector `{}`는 모든 노드). 변경은 agent Pod를 다시 만들거나 노드를 재시작해야 적용됩니다. `v2alpha1`은 1.20에서 제거되었습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  namespace: kube-system
  name: enable-xdp
spec:
  nodeSelector:
    matchLabels:
      io.cilium.xdp-offload: "true"
  defaults:
    bpf-lb-acceleration: native
```

대표적인 용도는 적합한 하드웨어가 있는 노드에서만 XDP나 IPv6 BIG TCP를 켜는 것과 kube-proxy replacement의 점진적 롤아웃입니다(전환한 노드에 `io.cilium.migration/kube-proxy-replacement=true` 레이블을 붙이고, kube-proxy DaemonSet에 해당 레이블 `NotIn` affinity를 patch하고, CiliumNodeConfig에 `kube-proxy-replacement: "true"`를 설정한 뒤 노드마다 agent Pod 삭제). kube-proxy를 없애기 전에 `k8sServiceHost`와 `k8sServicePort`가 이미 설정되어 있어야 합니다.

### 8.3 KVStore에서 CRD로 identity 마이그레이션 ("Double Write", beta)

1.17에서 도입되었고 1.20.2와 1.21 pre.3에서도 beta입니다. 할당 모드는 agent 옵션 `--identity-allocation-mode`이며 Helm 값 `identityAllocationMode`로 설정합니다(차트가 `identity-allocation-mode` ConfigMap 키를 렌더링).

| 단계 | 모드 | 롤아웃 순서 | 기준 데이터 |
|---|---|---|---|
| 0 | `kvstore` | | KVStore |
| 1 | `doublewrite-readkvstore` | operator, 그다음 agent | KVStore (identity가 CRD로도 기록되지만 사용되지 않음) |
| 2 | `doublewrite-readcrd` | operator, 그다음 agent | CRD (빠른 롤백을 위해 KVStore에도 계속 기록) |
| 3 | `crd` | agent, 그다음 operator | CRD만; KVStore 폐기 가능 |

단계 사이에 수렴을 기다립니다. operator는 `cilium_operator` 네임스페이스의 gauge를 노출합니다. upstream 업그레이드 페이지는 아직 예전 이름 `cilium_operator_identity_*_count`를 나열하지만, v1.20.2의 `operator/doublewrite/metrics.go` 코드는 `doublewrite_crd_identities`, `doublewrite_kvstore_identities`, `doublewrite_crd_only_identities`, `doublewrite_kvstore_only_identities`를 등록하며 실제로는 `cilium_operator_doublewrite_*`로 보입니다. 사용 중인 버전의 정확한 이름은 operator metrics 포트에서 확인하세요. KVStore와 CRD의 garbage collection 시점이 달라 일시적 차이는 정상입니다(`--identity-gc-interval`, `--identity-heartbeat-timeout`). 반대 방향(CRD에서 KVStore)은 단계를 역순으로 반복합니다. 초기화 복구: `crd` 모드로 실행 중인 agent가 없는 상태에서 `kubectl delete ciliumid --all`.

일회성 도구 `cilium-dbg preflight migrate-identity`는 1.20.2 문서에 제약(identity 변동 불가, 쉬운 롤백 없음)과 함께 있고 1.21 pre-release에서 deprecated입니다. Double Write를 사용하세요.

## 9. Cluster Mesh 아키텍처

Cluster Mesh는 여러 Kubernetes 클러스터의 control plane을 연결해 identity, endpoint, node, service를 공유하며, Pod 트래픽은 gateway나 proxy 없이 노드 간에 직접 흐릅니다.

```
 Cluster 1                                         Cluster 2
 ┌──────────────────────────────┐                  ┌──────────────────────────────┐
 │ clustermesh-apiserver (Deploy)│                 │ clustermesh-apiserver (Deploy)│
 │  ┌────────┐ ┌──────────────┐ │  mTLS etcd 2379  │  ┌────────┐ ┌──────────────┐ │
 │  │ etcd   │◄┤ apiserver    │ │◄────────────────►│  │ etcd   │◄┤ apiserver    │ │
 │  │(로컬   │ │ (로컬 상태를 │ │  (internal LB /  │  │        │ │              │ │
 │  │ 상태)  │ │  etcd로 동기화)│ │   NodePort)     │  │        │ │              │ │
 │  └───▲────┘ └──────────────┘ │                  │  └───▲────┘ └──────────────┘ │
 │      │      ┌──────────────┐ │                  │      │      ┌──────────────┐ │
 │      └──────┤ kvstoremesh  │─┼─ 원격 상태 pull ─►│      └──────┤ kvstoremesh  │ │
 │             └──────▲───────┘ │                  │             └──────▲───────┘ │
 │   agent는 로컬 캐시만 읽음   │                  │   agent는 로컬 캐시만 읽음   │
 │   ┌────────────────┴─┐       │                  │   ┌────────────────┴─┐       │
 │   │ cilium-agent (DS)│       │                  │   │ cilium-agent (DS)│       │
 │   └─────────┬────────┘       │                  │   └─────────┬────────┘       │
 └─────────────┼────────────────┘                  └─────────────┼────────────────┘
               └──────── Pod -> Pod, 노드 간 직접 (VXLAN/Geneve 또는 native) ────┘
```

구성 요소(v1.20.2 `intro.rst`, `values.yaml`):

- **clustermesh-apiserver**는 컨테이너 세 개를 가진 Deployment입니다. `etcd`는 영속 스토리지 없는 단일 내장 인스턴스로, 시작 시 Kubernetes API 서버에서 상태를 다시 구성하며 mTLS로 노출됩니다. `apiserver`는 로컬 Cilium/Kubernetes 상태(node, endpoint, identity, service)를 그 etcd로 동기화합니다(`etcdQPS: 50`). `kvstoremesh`는 각 원격 클러스터의 상태를 로컬 etcd 캐시로 가져옵니다(`etcdQPS: 100`).
- **KVStoreMesh**: agent는 원격 상태를 로컬 캐시에서만 읽으므로 agent마다 모든 원격 etcd에 연결을 열지 않습니다. 1.16부터 기본 활성이고, `clustermesh.apiserver.kvstoremesh.enabled` 값은 1.18에서 deprecated되었으며, **[1.21 pre-release]**에서는 무조건 활성이고 값이 제거됩니다.
- **Replica**: `clustermesh.apiserver.replicas` 기본값은 1입니다. replica마다 자체 etcd 클러스터를 실행하며 원격 client는 Service를 통해 하나를 고릅니다. `service.enableSessionAffinity`(`HAOnly` 기본, `Always`, `Never`)는 재연결 후 전체 resync를 줄입니다. `podDisruptionBudget`은 기본 비활성입니다.
- **KVStore 모드**: Cilium이 이미 외부 etcd를 identity/상태 저장소로 쓴다면 Cluster Mesh가 이를 재사용할 수 있습니다(`clustermesh.apiserver.kvstoremesh.kvstoreMode: external`). `external`은 `crd` identity 할당 모드와 함께 쓸 수 없습니다.
- **단일 trust domain**(1.20.2 `intro.rst`): 침해된 클러스터가 다른 클러스터를 오염시킬 수 있으므로 서로 신뢰하고 보안 수준이 동등한 클러스터만 연결하세요.

### 9.1 데이터 경로

원격 Pod는 로컬 ipcache에 원격 노드를 tunnel endpoint로 하여(overlay) 나타나거나 underlay가 라우팅합니다(native routing). identity에 클러스터 ID가 포함되므로, 클러스터 1의 정책 판단은 원격 Pod의 숫자 identity를 사용해 gateway 없이 동작합니다. 그래서 Pod CIDR이 겹치지 않아야 하고 노드 IP 연결이 필수입니다.

## 10. Cluster Mesh 구성

### 10.1 사전 조건

| 요구 사항 | 세부 내용 |
|---|---|
| 동일한 데이터패스 모드 | 모든 클러스터가 overlay이거나 모두 native routing |
| Cilium minor 차이 | 최대 한 minor |
| 고유하고 겹치지 않는 Pod CIDR | 모든 클러스터의 모든 노드 |
| 노드 간 도달성 | 각 노드의 InternalIP 사용 (peering, TGW, VPN) |
| 방화벽 | TCP 2379 (clustermesh-apiserver), TCP 4240과 ICMP (health), UDP 8472/6081 (tunnel), UDP 51871 (WireGuard) |
| Native routing 전용 | `ipv4NativeRoutingCIDR`이 모든 클러스터의 Pod CIDR을 포함해야 하며(예: `10.0.0.0/8`) Pod가 모든 포트에서 클러스터 간 라우팅 가능해야 함 |

### 10.2 Cluster 이름과 ID

| 설정 | 규칙 |
|---|---|
| `cluster.name` | 최대 32자, 정규식 `^([a-z0-9][-a-z0-9]*)?[a-z0-9]$` (`pkg/clustermesh/types/types.go`); 클러스터마다 고유. ID가 0이 아니면 `default`는 사용 불가 |
| `cluster.id` | 기본 1~255; 0은 미설정이며 예약됨. `maxConnectedClusters: 511`이면 범위가 511까지 확장. **ENI 모드와 aws-cni chaining**: `extraConfig.allow-unsafe-policy-skb-usage=true`가 아니면 차트가 128~255(`maxConnectedClusters: 511`이면 384~511)를 거부합니다(`templates/validate.yaml:160-168`, cilium/cilium#21330). ENI 모드 EKS에서는 128 미만 ID를 쓰세요 |
| `clustermesh.maxConnectedClusters` | `255`(기본) 또는 `511`; 모든 클러스터에서 동일; 설치 시에만 설정 |

트레이드오프: 클러스터 ID가 숫자 identity의 비트를 차지합니다. 255 클러스터에서는 cluster-local identity 최대치가 65535이고 511에서는 32767로 줄어듭니다. 동작 중인 클러스터에서 `maxConnectedClusters`를 바꾸면 연결이 끊기거나 정책이 잘못 적용될 수 있습니다. `values.yaml`의 `cluster.id` 주석은 아직 1~255라고 되어 있는데 511인 경우에는 맞지 않는 오래된 설명입니다. 실행 중인 클러스터의 이름이나 ID를 바꾸면 identity가 클러스터 ID를 포함하므로 모든 workload를 재시작해야 합니다.

### 10.3 TLS와 authMode

| 값 | 의미 |
|---|---|
| `clustermesh.apiserver.tls.auto.method` | `helm`(`helm upgrade` 때만 인증서 갱신, 최소 매년 upgrade 필요), `cronJob`(기본 스케줄 `0 0 1 */4 *`, 4개월마다), `certmanager` |
| `tls.auto.certValidityDuration` | `365`일 |
| 공유 CA | 모든 클러스터가 하나의 CA를 공유해야 함: 활성화 전에 `cilium-ca` Secret을 다른 클러스터로 복사하거나 `tls.caBundle` 설정 |
| 사용자 제공 인증서 | Secret `clustermesh-apiserver-{server,admin,remote,local}-cert`; CN: server `clustermesh-apiserver.<ns>.svc`(SAN `*.mesh.cilium.io`, `127.0.0.1`, `::1`, 추가 DNS 이름), admin `admin-<cluster>`, local `local-<cluster>`, remote는 `remote`(1.20) 또는 `remote-<cluster-name>`(`cluster` 모드) |

`authMode`는 원격 clustermesh-apiserver에 연결할 때 각 클러스터가 사용할 etcd 사용자를 결정합니다.

| authMode | 동작 | 기본값인 버전 |
|---|---|---|
| `legacy` | 모든 클러스터가 사용자 `remote` 사용 | 1.17, 1.18 (`values.yaml`: v1.17.18 3416행, v1.18.14 3634행) |
| `migration` | 클러스터별 사용자를 만들지만 인증은 여전히 `remote`로 수행; legacy와 클러스터 사이를 무중단으로 이동하는 데 필요 | 1.19, 1.20 |
| `cluster` | 각 클러스터가 `remote-<cluster-name>`으로 인증; 같은 CA를 공유할 때만 의미 있음 | **[1.21 pre-release]** |
| `cluster-strict` | **[1.21 pre-release]** `cluster`와 같지만 공유 `remote` 사용자가 없음; 모든 클러스터가 `cluster`를 쓴 뒤에만 활성화 | - |

1.21 조치: `clustermesh.useAPIServer=true`이고 `tls.auto.enabled=false`라면 remote 인증서를 CN `remote-<cluster-name>`으로 재발급하거나 `authMode`를 `migration`/`legacy`로 되돌리세요. 자동 인증서에서는 전환이 투명하게 이루어질 것으로 예상됩니다. `clustermesh.config.enabled=false`이면 `clustermesh-remote-users` ConfigMap을 직접 만들어야 합니다(1.19 노트). 인증서 수명 변경: 1.19가 생성 방식을 개편(CronJob이 더 이상 Helm hook 아님), 1.20은 기본 1년 유효에 4개월마다 재생성하고 CA 유효기간 >= leaf 유효기간을 강제하며, 1.20에서 `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}`가 `clustermesh.apiserver.tls.auto.server.*`로 이동했습니다.

### 10.4 Helm 설정

클러스터별 values입니다(upstream 설정 가이드의 형태이며 internal-LB annotation은 표준 AWS Load Balancer Controller scheme annotation이며, 차트 주석에 있는지는 확인하지 않았습니다).

```yaml
# cluster1.yaml
cluster:
  name: cluster1
  id: 1
clustermesh:
  useAPIServer: true
  config:
    enabled: true
  apiserver:
    service:
      type: LoadBalancer
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    tls:
      auto:
        enabled: true
        method: cronJob
        server:
          extraDnsNames:
            - cluster1.example.com
```

```yaml
# clusters.yaml  (공유; 각 cluster는 자기 자신의 항목을 무시)
clustermesh:
  config:
    clusters:
      cluster1:
        address: cluster1.example.com
        port: 2379
      cluster2:
        address: cluster2.example.com
        port: 2379
```

이미 설치된 것과 같은 차트 버전으로 적용합니다(upstream 가이드처럼 `--reuse-values`가 허용되는 경우입니다). 먼저 CA를 복사합니다.

```bash
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER1 --reuse-values -f clusters.yaml -f cluster1.yaml

kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | \
  kubectl --context $CLUSTER2 create -f -

helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER2 --reuse-values -f clusters.yaml -f cluster2.yaml
```

Service 노출: `clustermesh.apiserver.service.type` 기본값은 `NodePort`(`nodePort: 32379`)입니다. upstream은 안정적인 주소를 위해 `LoadBalancer`를 권장하고, `NodePort`는 안정적인 노드 IP가 필요하며, `ClusterIP`는 ClusterIP가 클러스터 간에 라우팅 가능해야 합니다. AWS에서는 항상 `service.beta.kubernetes.io/aws-load-balancer-scheme: internal`(그리고 peer VPC CIDR로 제한한 `loadBalancerSourceRanges`)을 쓰거나 peering/TGW 위의 NodePort/ClusterIP를 쓰세요. 이 control plane에 internet-facing LB를 쓰면 이 저장소의 정책을 위반하고 mesh trust domain이 노출됩니다. TCP 2379는 peer 클러스터의 node security group이나 private CIDR에서만 허용하는 security group과 함께 사용하세요.

Partial mesh: 각 클러스터의 `clusters` map에 연결할 클러스터만 넣습니다. 클러스터별 정적 `ips`도 지원합니다. **[1.21 pre-release]** 정적 IP를 바꿔도 Pod가 재시작되지 않고 `clustermesh.apiserver.service.port`를 설정할 수 있습니다.

CLI 대안(Helm을 감싼 래퍼이며 실습에 편리):

```bash
cilium install --set cluster.name=$CLUSTER1 --set cluster.id=1 --context $CLUSTER1
cilium install --set cluster.name=$CLUSTER2 --set cluster.id=2 --context $CLUSTER2
cilium clustermesh enable --context $CLUSTER1
cilium clustermesh enable --context $CLUSTER2
cilium clustermesh connect --context $CLUSTER1 --destination-context $CLUSTER2   # 한 방향이면 충분
cilium clustermesh status --context $CLUSTER1 --wait
cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2
```

### 10.5 Namespace: `defaultGlobalNamespace`

`clustermesh.defaultGlobalNamespace`(기본 `true`; 1.20.2 차트에 있고 1.19.8 차트에는 없음)는 네임스페이스의 CiliumEndpoint, CiliumIdentity, Service를 export할지 결정합니다. 네임스페이스에 `clustermesh.cilium.io/global: "true"` 또는 `"false"` annotation을 붙여 기본값을 덮어씁니다. 클러스터 간 연결과 정책에는 source와 destination 네임스페이스가 모두 global이어야 하고, Global Service는 global 네임스페이스에 있으면서 service annotation도 있어야 합니다. 기본값을 `false`로 두면 클러스터 간 동기화 상태가 줄어 확장성에 도움이 됩니다.

### 10.6 오래된 데이터: `cacheTTL`

`clustermesh.cacheTTL` 기본값은 `"0s"`로, 연결이 끊긴 원격 클러스터의 캐시를 회수하지 않습니다. 해당 시간 안에 연결이 복구되지 않은 경우 오래된 원격 데이터를 버리려면 기간(예: `"15m"`)을 설정하세요.

## 11. Global Service, Affinity, EndpointSlice 동기화

Global Service는 각 클러스터에서 이름과 네임스페이스가 같고 `service.cilium.io/global: "true"` annotation이 있는 Service입니다. 모든 클러스터의 backend가 합쳐집니다.

| Annotation | 효과 |
|---|---|
| `service.cilium.io/global: "true"` | Service를 global로 만듦. 어느 클러스터에서든 생략하거나 false이면 그 클러스터의 Service는 로컬로 남음 |
| `service.cilium.io/shared: "false"` | 이 클러스터의 backend를 export하지 않지만 원격 backend는 계속 사용. 양쪽 모두 global이고 둘 다 shared이면 각 클러스터가 로컬과 원격을 모두 보며, `shared: "false"`인 클러스터는 아무것도 export하지 않음 |
| `service.cilium.io/affinity: none\|local\|remote` | `local`: 정상 로컬 backend를 사용하고 로컬이 모두 불가할 때만 원격으로 fallback; `remote`는 반대; `none`(기본)은 선호 없음 |
| `service.cilium.io/global-sync-endpoint-slices: "true"` | **Beta.** 서드파티 컨트롤러가 볼 수 있도록 원격 backend의 EndpointSlice도 생성; Helm `clustermesh.enableEndpointSliceSynchronization=true`와 operator 재시작 필요. Headless global Service는 기본으로 적용 |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rebel-base
  annotations:
    service.cilium.io/global: "true"
    service.cilium.io/affinity: "local"
spec:
  type: ClusterIP
  ports:
  - port: 80
  selector:
    name: rebel-base
```

affinity는 `cilium-dbg service list --clustermesh-affinity`로 확인합니다(선호 backend에 `(preferred)` 표시). 제한: Global NodePort와 host-network client는 kube-proxy replacement(또는 `socketLB.enabled=true`와 `socketLB.hostNamespaceOnly=true`)가 있을 때만 원격 backend로 로드 밸런싱됩니다. Cilium ingress controller는 EndpointSlice 동기화 없이도 mesh에서 동작하지만 다른 ingress controller에는 EndpointSlice 동기화가 필요할 수 있습니다. 1.19에서 추가된 metric: `cilium_agent_clustermesh_remote_cluster_endpoints`.

## 12. MCS-API (Multi-Cluster Services)

MCS-API는 Kubernetes SIG-Multicluster API입니다. `ServiceExport`가 Service를 게시하면 모든 클러스터에 `ServiceImport`가 생기고 DNS 이름은 `<svc>.<ns>.svc.clusterset.local`입니다. Cilium은 import를 `derived-<hash>`라는 파생 Service로 구현하며 Global Services 메커니즘을 재사용하므로 두 방식은 함께 쓸 수 있습니다.

| 항목 | 값 |
|---|---|
| 성숙도 | 1.19 beta (CRD `multicluster.x-k8s.io/v1alpha1`); 1.20 stable (`v1beta1`, `v1alpha1`도 지원) |
| 활성화 | `clustermesh.mcsapi.enabled=true` (제거된 `clustermesh.enableMCSAPISupport` 대체) |
| CRD | 차트가 설치(`clustermesh.mcsapi.installCRDs`, 기본 true) |
| CoreDNS | `clustermesh.mcsapi.corednsAutoConfigure.enabled` (CoreDNS >= 1.12.2 필요, Kubernetes >= 1.35의 기본값). 수동 방법: ClusterRole `coredns-mcsapi`(`serviceimports` list/watch)와 CoreDNS `multicluster clusterset.local` plugin |
| Namespace | Service의 네임스페이스가 모든 클러스터에 있어야 함 |

```yaml
apiVersion: multicluster.x-k8s.io/v1beta1
kind: ServiceExport
metadata:
  name: rebel-base
spec:
  exportedLabels:
    app.kubernetes.io/name: rebel-base
  exportedAnnotations:
    service.cilium.io/affinity: local
```

export 간에 조정되는 속성은 SessionAffinity, Ports(합집합), Type(ClusterSetIP 또는 Headless), InternalTrafficPolicy, TrafficDistribution, 레이블/annotation입니다. 충돌이 있으면 Cilium은 `ServiceExport` status에 conflict condition을 설정하고 생성 시각이 오래된 순으로 해결하므로, 자동 해결에 기대지 말고 충돌을 직접 고치세요. 클러스터별 DNS 이름은 지원되지 않으므로 `mysvc-eu`와 `mysvc-us`를 따로 export합니다. StatefulSet Pod의 hostname은 `<hostname>.<cluster>.<svc>.<ns>.svc.clusterset.local`로 해석됩니다. Gateway API는 `ServiceImport`를 `backendRef`로 사용할 수 있습니다. **[1.21 pre-release]** prefix 제거 후 이름이 40자를 넘는 mirrored EndpointSlice는 업그레이드 중 다시 만들어질 수 있고 이때 짧은 중단이 생깁니다.

## 13. Cluster 간 정책

- **기본 범위(1.19 이상)**: selector는 로컬 클러스터의 endpoint만 선택합니다(`policy-default-local-cluster`, Helm `clustermesh.policyDefaultLocalCluster: true`). 1.18까지는 기본이 모든 클러스터였습니다. 1.18에서 올리기 전에 `cilium clustermesh inspect-policy-default-local-cluster --all-namespaces`(또는 `-p <namespace>`)로 점검하세요. 이전 판에는 이 명령의 CLI 버그가 pre.3 트리에서 수정되었다고 적혀 있었으나 확인되지 않았으므로 사용 중인 CLI 버전의 출력으로 확인하세요.
- **원격 클러스터 선택**은 `io.cilium.k8s.policy.cluster` 레이블로 합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cross-cluster
spec:
  endpointSelector:
    matchLabels:
      name: x-wing
  egress:
  - toEndpoints:
    - matchLabels:
        name: rebel-base
        io.cilium.k8s.policy.cluster: cluster2
```

모든 클러스터를 대상으로 하려면 `matchExpressions: [{key: io.cilium.k8s.policy.cluster, operator: Exists}]`를 사용합니다.

- **Entity**: `cluster`는 로컬 클러스터로 제한하지 않는 한 mesh의 원격 노드를 포함합니다(1.18 옵션). 1.20에서 `cluster-mesh`가 추가되어 mesh로 연결된 클러스터의 모든 endpoint와 `cluster`의 모든 대상을 포함합니다.
- 정책은 복제되지 않으므로 각 클러스터에 적용해야 합니다.
- Mutual authentication(SPIRE)은 Cluster Mesh와 함께 지원되지 않으며 1.21 pre-release에서는 완전히 제거됩니다. 이 저장소의 service mesh 문서에 따르면 ztunnel도 Cluster Mesh와 함께 지원되지 않습니다. [mTLS, 암호화, Identity](12-mtls-encryption-identity.md)를 참고하세요.
- Host firewall은 Cluster Mesh와 조합할 때 제한이 있습니다(`host.rst`). 데이터 플레인 암호화는 control plane의 mTLS와 별개이며, WireGuard나 IPsec은 모든 클러스터에서 동일하게 구성하고 클러스터 사이에서 UDP 51871을 열어야 합니다. Cluster Mesh와 암호화의 정확한 주의 사항은 이번에 다시 확인하지 못했습니다.

## 14. EKS에서의 Cluster Mesh

upstream의 `eks-clustermesh-prep.rst`는 `eksctl`, 겹치지 않는 CIDR의 VPC 두 개(예: `10.0.0.0/16`, `10.1.0.0/16`, `172.17.0.0/16`은 피함), VPC peering, 자기 자신과 peer를 허용하는 security group을 사용합니다. 이 가이드는 인터넷 게이트웨이가 있는 public subnet도 만듭니다. 이 저장소에서는 다음과 같이 조정하세요.

- 노드는 private subnet에만 두고 노드에 public IP나 EIP를 붙이지 않습니다.
- VPC를 peering(또는 Transit Gateway)하고 private route table에 peer CIDR 경로를 추가합니다.
- Security group 규칙은 두 클러스터의 node security group(또는 private CIDR)을 참조하며 `0.0.0.0/0`이나 `::/0`은 쓰지 않습니다.
- clustermesh-apiserver는 internal NLB(`aws-load-balancer-scheme: internal`) 또는 peering 링크 위의 NodePort로 노출하고 `loadBalancerSourceRanges`를 peer VPC CIDR로 설정합니다.
- ENI 모드는 VPC에서 라우팅 가능한 Pod IP를 주므로 native routing에서는 `ipv4NativeRoutingCIDR`이 두 VPC의 Pod 대역을 포함하기만 하면 됩니다. overlay 모드에서는 노드 간 도달성(UDP 8472)만 필요합니다.
- EKS 클러스터마다 `cluster.name`/`cluster.id`를 다르게 하고 `maxConnectedClusters`는 같게 합니다. ENI 모드에서는 `cluster.id`를 128 미만으로 두세요. `extraConfig.allow-unsafe-policy-skb-usage=true`가 없으면 차트가 128~255(`maxConnectedClusters: 511`이면 384~511)를 거부합니다(`validate.yaml:160-168`).

## 15. 실습

> 이 실습들은 이번 검토에서 실제 클러스터에 대해 실행하지 않았고 upstream 소스와 문서로 확인했습니다. 일회용 클러스터에서만 실행하세요.

### 실습 1: 두 클러스터 Cluster Mesh

사전 조건: 노드끼리 도달 가능한 일회용 클러스터 두 개(한 Docker 호스트의 kind 클러스터 두 개에 서로 다른 `networking.podSubnet`/`serviceSubnet`과 `disableDefaultCNI: true`를 쓰거나, peering된 VPC의 EKS 클러스터 두 개), Helm 3, Cilium CLI 0.20.1, `$CLUSTER1`/`$CLUSTER2` context.

1. 각 클러스터에 서로 다른 `cluster.name`, `cluster.id`, 겹치지 않는 Pod CIDR(cluster-pool 목록이 달라야 함)로 Cilium 1.20.2를 설치합니다.
2. CA를 복사합니다: `kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | kubectl --context $CLUSTER2 create -f -`.
3. 10.4절의 values 파일을 적용합니다. 로드 밸런서가 없는 kind에서는 `service.type: NodePort`를 쓰고 `clustermesh.config.clusters.<name>.ips`에 노드 IP를, 포트에 `32379`를 지정합니다.
4. `cilium clustermesh status --context $CLUSTER1 --wait`를 실행한 뒤 `cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2`를 실행합니다.

확인: `cilium clustermesh status`가 clustermesh-apiserver 준비 완료와 원격 클러스터 연결을 보고합니다. `kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg status --all-clusters`가 원격 클러스터를 ready로, 클러스터 ID와 `synchronization status` 전부 true로 보여 주고 `cilium-dbg node list`에 원격 노드가 포함됩니다.

정리: 두 클러스터에서 `helm uninstall cilium -n kube-system`을 실행하거나 일회용 클러스터를 삭제합니다. connect 실패 롤백: `clusters.yaml` 항목을 제거하고 같은 차트 버전으로 `helm upgrade`를 다시 실행합니다.

### 실습 2: Global Service, `shared`, affinity

사전 조건: 실습 1.

1. 두 클러스터에 같은 네임스페이스와 `service.cilium.io/global: "true"`가 붙은 Deployment 및 Service `rebel-base`를 만들고 Pod가 자신의 클러스터 이름으로 응답하게 합니다.
2. 클러스터 1의 client Pod에서 curl 루프를 실행하고 양쪽 클러스터의 응답을 관찰합니다.
3. 클러스터 1의 Service에 `service.cilium.io/affinity=local`을 붙이고 반복합니다. 응답이 클러스터 1에서만 옵니다. 로컬 backend를 0으로 줄여 클러스터 2로 failover되는 것을 관찰합니다.
4. 클러스터 2에서 `service.cilium.io/shared: "false"`로 바꾸면 클러스터 1은 클러스터 2 backend를 보지 못하고 클러스터 2는 여전히 클러스터 1에 도달합니다.

확인: agent에서 `cilium-dbg service list --clustermesh-affinity`가 선호 backend를 보여 주고 `cilium-dbg bpf lb list`가 원격 backend 주소를 보여 줍니다.

정리: 두 클러스터의 네임스페이스를 삭제합니다.

### 실습 3: MCS-API

사전 조건: `clustermesh.mcsapi.enabled=true`와 `corednsAutoConfigure.enabled=true`로 구성한 실습 1(CoreDNS를 수동 구성하면 재시작).

1. 두 클러스터에 네임스페이스와 Service를 만들고 같은 이름의 `ServiceExport`를 각각 만듭니다.
2. Pod에서 `rebel-base.<namespace>.svc.clusterset.local`을 조회하고 curl합니다.
3. 클러스터 사이에 export 포트를 다르게 만들고 `kubectl get serviceexport -o yaml`에서 conflict condition을 확인합니다.

확인: 두 클러스터에 `ServiceImport`가 있고 `derived-<hash>` 파생 Service가 나타나며 DNS 이름이 해석됩니다.

정리: ServiceExport, Service, 네임스페이스를 삭제합니다.

### 실습 4: drift detection을 포함한 업그레이드 연습

사전 조건: values 파일로 설치한 1.19.8 일회용 클러스터, 접근 가능한 Prometheus metrics endpoint(또는 `cilium-dbg metrics list` 사용).

1. 값을 저장합니다: `helm get values cilium -n kube-system -o yaml > old-values.yaml`.
2. 1.20.2 pre-flight 차트를 실행해 검사가 통과하는지 확인하고 삭제합니다.
3. `--version 1.20.2 -f old-values.yaml --set upgradeCompatibility=1.19`로 업그레이드합니다.
4. `cilium config set --restart=false <key> <value>`로 agent 재시작이 필요한 ConfigMap 키 하나를 바꾸고 drift metric을 읽습니다: `kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg metrics list | grep drift_checker_config_delta`.
5. 롤백합니다: `helm history cilium -n kube-system` 후 `helm rollback cilium <REVISION> -n kube-system`.

확인: 4단계 뒤 `cilium_drift_checker_config_delta`가 0이 아니고 agent가 재시작된 뒤 0으로 돌아옵니다. 업그레이드 후와 롤백 후 `cilium status`가 정상입니다.

정리: 일회용 클러스터를 삭제합니다. 롤백 주의: 이 실습은 롤백 경로를 연습하는 것이므로 1.20 전용 기능을 사용한 클러스터에서는 실행하지 마세요.

### 실습 5: CiliumNodeConfig 노드별 override

사전 조건: 노드가 둘 이상인 Cilium 1.20.2 cluster.

1. 노드 하나에 레이블을 붙입니다: `kubectl label node <node> io.cilium.test-override=true`.
2. 그 레이블을 선택하고 `debug: "true"` 같은 무해한 `defaults` 키를 가진 `CiliumNodeConfig`를 `kube-system`에 적용합니다.
3. 레이블이 붙은 노드와 붙지 않은 노드 하나의 agent Pod를 삭제합니다.

확인: 레이블이 붙은 노드에서는 재생성된 agent의 실제 구성(`cilium-dbg config`)에 override가 반영되고 붙지 않은 노드에서는 그렇지 않습니다.

정리: CiliumNodeConfig를 삭제하고 레이블을 제거한 뒤 agent Pod를 다시 한 번 재생성합니다.

## 버전 차이

| 영역 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|
| 최소 커널 | 5.10 | 5.10 | 5.10 | 5.10 (LLVM 21.1) |
| Gateway API CRD | 1.3.0 | 1.4 | 1.6.1 | 1.6.1 |
| Helm OCI 차트 | 없음 | 있음 | 있음 (권장) | 있음 |
| MCS-API | beta | beta (`v1alpha1`, CRD 자동 설치) | stable (`v1beta1`) | `v1beta1` |
| Cluster Mesh 정책 기본값 | 모든 클러스터 | 로컬만 | 로컬만; `cluster-mesh` entity | 로컬만 |
| authMode 기본값 | `legacy` | `migration` | `migration` | `cluster` (+ `cluster-strict`) |
| KVStoreMesh | `enabled` deprecated | 기본 활성 | 기본 활성 | 항상 활성 |
| Mutual auth | 있음 | 기본 비활성 | deprecated | 제거 |
| Kafka L7 / proxylib | deprecated | Kafka deprecated | 제거 | 제거 |
| BGPv1 | deprecated | 제거 | - | - |
| Multi-pool IPAM | beta | stable | + cluster-pool 마이그레이션 | Azure IPAM이 multi-pool로 |
| Double Write | beta | beta | beta | beta; `migrate-identity` deprecated |
| configDriftDetection | 백포트 | 백포트 | 기본 제공 | 동일 |
| ENI masquerade 기본값 | IPv4가 false로 전환 | false | false | IPv6 masquerade도 off |

## 문제 해결

| 증상 | 확인 |
|---|---|
| 원격 클러스터가 연결되지 않음 | `cilium clustermesh status --wait`; `kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg troubleshoot clustermesh [cluster...]` (DNS, 연결, TLS, etcd 인가); KVStoreMesh에서는 `kubectl exec -n kube-system deploy/clustermesh-apiserver -c kvstoremesh -- clustermesh-apiserver kvstoremesh-dbg troubleshoot`도 실행 |
| 원격별 상태 | `cilium-dbg status --all-clusters` (node, endpoint, identity, service, MCS-API export, reconnection, `has-quorum`, `cluster-id`, `kvstoremesh`, synchronization status); `... kvstoremesh-dbg status --verbose` |
| 로그 | agent: `New remote cluster configuration`, `Connection to remote cluster established`, `Unable to establish etcd connection to remote cluster`; `kubectl logs -n kube-system deployment/clustermesh-apiserver -c apiserver` |
| TLS 오류 | CA 불일치(`cilium-ca` 복사), 인증서 만료(`helm` 방식은 1년 후), `authMode`에 맞지 않는 CN; Secret `cilium-clustermesh`, `cilium-kvstoremesh` |
| `*.mesh.cilium.io` 이름 해석 | hostAliases가 `cluster1.mesh.cilium.io`를 LB IP로 매핑: KVStoreMesh가 없으면 DaemonSet, 있으면 clustermesh-apiserver Deployment |
| 포트 | TCP 2379를 security group에서 참조/private CIDR로 허용해야 함 |
| Cluster 간 트래픽 거부 | `cilium-dbg identity list`(레이블 `io.cilium.k8s.policy.cluster`), `cilium-dbg bpf ipcache list`, `cilium-dbg service list`, `cilium-health status`; 1.19 이후 로컬 클러스터 기본 정책 범위와 두 네임스페이스가 모두 global이어야 한다는 점을 기억 |
| CIDR 중복 또는 ID 중복 | `cilium-dbg node list`에서 충돌하는 노드 대역 확인; 해결은 IP 재할당과 workload 재시작 필요 |
| 오래된 클러스터의 1.20 업그레이드 정체 | 1.20.2 이상 사용 (`CiliumNodeConfig v2alpha1` CRD 버그) |
| 설정 변경이 적용되지 않음 | `cilium_drift_checker_config_delta > 0`: agent 재시작 |

## 검증 한계와 출처

실습은 이번 검토에서 실제 클러스터에 대해 실행하지 않았고 아래 태그의 upstream 소스와 문서로 확인했습니다. 확인하지 못한 사실은 단정하지 않고 여기에 나열합니다.

- Cilium 1.21이 BPF masquerading을 기본으로 켜는지 여부. pre.2 릴리스 노트는 그렇다고 하지만 pre.3 트리는 daemon 기본값 `false`, 차트 `bpf.masquerade` 기본 false, `upgrade-next.inc`의 "Changed Options"가 비어 있음을 보여 줍니다.
- WireGuard/IPsec과 Cluster Mesh: 정확한 주의 사항은 다시 확인하지 않았습니다.
- EKS의 chaining 모드 제한, EKS managed kube-proxy add-on을 제거하는 정확한 명령, Amazon Linux 2023이 이름으로 나열되는지 여부.
- 1.17.9-0, 1.18.3-0 이후의 AWS 유지 보수 Cilium 빌드 버전.
- 인용한 "beta" 이상의 `bpf.tproxy` 및 ENI IPv6 성숙도.
- 1.19.0 릴리스 날짜와 1.17의 정확한 Kubernetes 테스트 매트릭스.
- MCS-API "stable" 표기는 v1.20.0 릴리스 본문에서 가져왔고, 소스는 beta 배너 제거와 `v1beta1` CRD로 이를 뒷받침합니다.
- Double Write metric 이름: upstream 업그레이드 페이지와 코드가 다릅니다(8.3절). v1.20.2 코드를 따랐습니다.
- 차트의 `kubeVersion`은 차트 제약이며 테스트된 Kubernetes 범위가 아닙니다.

출처:

- [Cilium v1.20.2 문서: operations/upgrade.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade.rst)
- [v1.20.2 업그레이드 노트](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)
- [v1.20.2 Cluster Mesh 문서](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/clustermesh)
- [v1.20.2 Cluster Mesh 문제 해결](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/troubleshooting_clustermesh.rst)
- [v1.20.2 Helm 설치와 EKS](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/k8s-install-helm.rst), [requirements-eks.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [v1.20.2 ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [v1.20.2 시스템 요구 사항](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [v1.20.2 per-node config](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/per-node-config.rst), [ConfigMap drift detection](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/configmap-drift-detection.rst)
- [v1.20.2 Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- [v1.20.2 Double Write metrics 코드](https://github.com/cilium/cilium/blob/v1.20.2/operator/doublewrite/metrics.go)
- [v1.21.0-pre.3 업그레이드 노트](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc), [values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- 릴리스 노트: [v1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2), [v1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0), [v1.19.0](https://github.com/cilium/cilium/releases/tag/v1.19.0), [v1.18.0](https://github.com/cilium/cilium/releases/tag/v1.18.0), [v1.17.0](https://github.com/cilium/cilium/releases/tag/v1.17.0), [v1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3)
- AWS: alternate CNI plugins, Auto Mode 네트워킹, hybrid nodes CNI에 관한 EKS 사용자 가이드 페이지.

## 퀴즈

[Part 13 퀴즈](../../quizzes/networking/cilium/13-clustermesh-install-upgrade-quiz.md)로 학습 내용을 점검하세요.
