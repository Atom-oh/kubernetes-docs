# Cilium 딥다이브: 클라우드 네이티브 네트워킹의 미래

## 개요와 검토 기준

Cilium 네트워킹, 정책, 관측성을 다룹니다. 예제 검토 기준은 **Cilium/Helm 차트 1.20.1**, Cilium CLI **0.20.0**, Hubble CLI **1.19.4**입니다. Cilium 1.20 호환성 문서의 Kubernetes 테스트 범위는 **1.33–1.36**이며 업스트림 1.37 출시만으로 자동 확대되지 않습니다. 호스트는 AMD64/AArch64 Linux, 커널 **5.10 이상** 또는 문서화된 배포판 동등 조건(예: RHEL 8.10의 backport된 4.18)을 충족해야 합니다. 개별 기능에는 추가 조건이 있습니다.

> **마지막 업데이트**: 2026년 9월 12일

### 릴리스 이력

아래 날짜는 GitHub 공개 시각의 UTC 날짜로 해당 릴리스 기록이며 현재 설치 버전 지정이 아닙니다. 릴리스 라인마다 백포트 내용이 다릅니다.

| 날짜 | 릴리스 | 확인한 주요 내용 |
| --- | --- | --- |
| 2026-07-14 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 1.20 첫 release candidate |
| 2026-07-16 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gateway access-log 설정은 1.19.6/1.18.12에, 여기서 다루는 restart-policy·ClusterMesh affinity 수정은 1.19.6에 명시되어 있으며 세 릴리스 모두의 변경이 아님 |
| 2026-07-21 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 1.20 두 번째 release candidate |
| 2026-07-29 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA 릴리스, 주요 변경은 아래 설명 |
| 2026-08-03 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 다음 사이클 prerelease, 이 가이드의 배포 기준이 아님 |
| 2026-08-18 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMesh 문서와 restart/CIDR-policy 처리 등 버그 수정 |
| 2026-08-18 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | ENI 인터페이스 타이밍, Service/LB 등 수정 |
| 2026-08-18 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP host-firewall 지원 및 관련 수정 |

1.20.0 발표는 **2,660개 이상의 새 커밋**과 **1,100명 이상 기여자의 커뮤니티**를 소개합니다. 후자는 해당 릴리스 작성자 수가 아닌 커뮤니티 규모입니다. 주요 변경은 다음과 같습니다.

- Gateway API **1.6.1**, TCPRoute/UDPRoute, BackendTLSPolicy, ListenerSets, ExternalAuth, CORS 지원이며 각각의 설정과 API 성숙도를 확인해야 합니다.
- Datapath plugin과 명시적으로 선택하는 `bpf.datapathMode=auto`, 발표된 기본값은 여전히 veth입니다. Dual-stack 클러스터에는 IPv6 egress gateway 주소를 지정할 수 있습니다.
- **Beta** IPv6 ENI IPAM 및 클러스터를 재구축하지 않는 cluster-pool→multi-pool 전환입니다. In-place가 중단 없음을 보장하지는 않습니다.
- 트래픽 분배 힌트, 가중치 Maglev backend, stable MCS 통합, Kubernetes ClusterNetworkPolicy, **beta** ztunnel 워크로드 identity 지원입니다.
- 발표된 `cilium-cni` 바이너리 크기 감소는 약 **77MB→16MB**입니다. ADS/Delta xDS 개선은 1.20 발표 내용이며 1.18.13 패치 내용으로 귀속하면 안 됩니다. 이 감사에서 다시 측정한 결과가 아닌 업스트림 릴리스의 설명입니다.

레거시 Mutual Authentication, Envoy Go 확장, Kafka 인지 정책, 이전 CiliumNodeConfig API, libnetwork, 사용자 정의 CNI 설정의 제거/변경은 [1.20 업그레이드 안내](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)를 확인하세요.

### NetworkPolicy 보안 권고

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r)의 프로젝트 권고문 공개일은 **2026년 7월 6일**입니다. 프로젝트 API와 GitHub 통합 권고 API의 날짜는 다르며 통합 기록은 9월 3일입니다. 이 릴리스 연혁에는 프로젝트 공개일을 사용하며 통합 기록 날짜를 새로운 수정 릴리스 날짜로 취급하지 않습니다. 권고문이 설명하는 custom cluster-name 조건에서 **1.19.0–1.19.4**가 영향을 받으며, 표준 Kubernetes NetworkPolicy의 `ipBlock`만 있는 peer 규칙이 선택한 Pod와 같은 네임스페이스의 워크로드 ingress를 의도하지 않게 허용할 수 있습니다. 해당 문제는 **1.19.5**에서 수정되었고 실제 배포에는 적절한 최신 패치 버전을 선택해야 합니다. 권고문은 CiliumNetworkPolicy/ClusterwideNetworkPolicy와 1.19.0 이전 릴리스는 이 특정 문제의 영향을 받지 않는다고 설명합니다.

## 소개

Cilium은 지원되는 Linux Kubernetes 환경의 네트워킹, 보안, 관측성을 제공합니다. 라우팅, IPAM, 암호화, Service 처리는 별도 선택이며 eBPF 선택만으로 모든 기능이나 성능이 보장되지는 않습니다. 이전 Docker libnetwork 통합은 1.20에서 제거되었으므로 Docker/Mesos를 현재 동일한 설치 대상으로 나열하면 안 됩니다.

### eBPF와 주요 기능

커널은 eBPF 프로그램을 로드하기 전에 검증하고 지원 hook에서 실행하도록 JIT 컴파일할 수 있습니다. 별도 커널 모듈 없이 패킷 처리와 관측성을 구현할 수 있지만 verifier가 애플리케이션이나 정책의 정확성을 증명하지는 않습니다. 실제 처리량, 지연, 메모리는 프로그램·플랫폼·워크로드에 따라 달라집니다.

Cilium은 L3/L4 정책, Envoy/DNS proxy 통합의 L7 정책, 선택적 WireGuard/IPsec, Service 부하 분산, Hubble flow 가시성, ClusterMesh, BGP 광고를 제공합니다. XDP 가속은 장치·설정에 따른 선택 기능입니다. L7은 노드별 Envoy를 사용할 수 있고 ztunnel 워크로드 identity에는 별도 beta 설정이 필요합니다. 에이전트 설치만으로 모든 mesh·암호화·멀티클러스터 동작이 활성화되지는 않습니다.

### 다른 네트워킹 프로젝트와 비교

| 프로젝트 | 연결 / IPAM | 정책과 관련 기능 |
| --- | --- | --- |
| Cilium | Native/overlay 라우팅, ENI 등 IPAM 모드 | eBPF, Cilium/Kubernetes 정책, L7 통합, Hubble, 선택적 암호화 |
| Calico | Calico 또는 외부 IPAM과 native/IPIP/VXLAN 구성 | Linux Iptables/Nftables/BPF, 지원 Windows HNS, OSS WireGuard·staged policy·별도 L7 통합 |
| Flannel | VXLAN/host-gw/WireGuard 등 선택한 backend의 Pod 연결 | 라우팅 데몬 자체는 NetworkPolicy를 강제하지 않지만 차트의 netpol.enabled로 SIGs 정책 컨트롤러를 함께 배포하거나 다른 정책 구현과 결합 가능 |
| AWS VPC CNI | VPC ENI 주소 할당/네트워킹 | 지원 EC2 Linux의 네이티브 정책과 별도 SG-for-Pods, EKS Auto Mode는 다른 관리형 구현 |

라우팅 모드와 패킷 처리 구현은 같은 분류가 아닙니다. Calico는 iptables/IPVS로 제한되지 않고 Flannel에는 암호화 backend가 있으며 AWS 정책과 Security Group도 동일하지 않습니다. 서비스 메시는 선택 계층이고 클러스터 간 VPC 연결이 Transit Gateway로만 가능한 것도 아닙니다. 보편적인 성능 등급 대신 실제 워크로드와 지원 매트릭스를 비교하세요.

## 아키텍처

**Kubernetes API 서버**가 Kubernetes/Cilium 리소스를 저장합니다. Cilium Agent는 관련 상태를 감시해 노드 데이터플레인을 설정하고 Operator는 선택한 IPAM, identity/controller 작업 등 클러스터 수준 책임을 담당합니다. 기본 구조에 별도의 필수 클러스터 전체 “Cilium API Server” Deployment는 없습니다. Agent 로컬 API와 선택적 ClusterMesh API server는 서로 다른 목적입니다.

| 컴포넌트 | 역할 |
| --- | --- |
| Cilium Agent | 노드 endpoint, 정책, routing/Service 상태, eBPF 관리 |
| Cilium Operator | 클러스터 수준 조정과 모드별 할당/controller 작업 |
| Envoy | 활성화한 L7 정책, Ingress/Gateway 등 userspace 프록시 |
| Hubble server | Agent와 통합된 노드 로컬 flow API |
| Hubble Relay / UI | Flow stream 집계 / 서비스 맵과 flow 표시 |
| Prometheus metrics endpoint | 별도 통계 수집, Relay/UI는 metrics scrape 파이프라인이 아님 |
| cilium / cilium-dbg / hubble | 클러스터 관리 CLI / Agent 진단 / Flow 클라이언트 |

### 네트워킹과 패킷 경로

Native routing에는 도달 가능한 underlay가 필요하고 tunneling은 VXLAN 또는 Geneve를 사용합니다. AWS ENI와 Azure IPAM은 플랫폼 전제가 있는 할당/통합 선택입니다. Cilium BGP Control Plane은 라우터에 경로를 광고하며 **datapath를 설정하거나 클러스터 내부 라우팅을 제공하지 않습니다**.

모든 패킷이 XDP→TC→Pod로 이동하는 것은 아닙니다. Socket load balancing은 패킷 생성 전에 작동할 수 있고 TC/netkit hook은 datapath에 따라 다르며 선택적 XDP는 일부 트래픽을 가속하고 L7은 Envoy를 거칠 수 있습니다. 반환 경로도 NAT, conntrack, DSR 선택에 따라 달라집니다. 해당 구성의 네트워킹/eBPF 장을 참고하세요.

## Amazon EKS와의 통합

설치 전에 실제 네트워킹과 컴퓨팅 구성을 선택하세요. 기존 예제의 `cilium` / `v1.17.0-eksbuild.1` 애드온 이름·버전은 검증된 AWS 배포판이 아니므로 설치 명령에서 제거했습니다. Vendor 애드온을 고려한다면 리전의 실제 카탈로그, 게시자, 라이선스, 지원 컴퓨팅 유형을 확인해야 합니다.

| EKS 구성 | 확인할 사항 |
| --- | --- |
| 일반 EC2, Cilium ENI로 VPC CNI 교체 | 업스트림/파트너 관리 CNI이며 AWS가 지원하는 EC2 CNI는 VPC CNI, CNI 소유권·IAM·주소·경로·bootstrap·노드 전환 계획 필요 |
| 일반 EC2, AWS VPC CNI chaining | VPC CNI가 인터페이스/IPAM을 소유하고 이후 Cilium이 연결, 기존 Pod 재생성과 L7/IPsec 제약 확인 |
| Hybrid Nodes | AWS 전용 CNI 가이드와 AWS 유지 Cilium 빌드 매트릭스 사용, 업스트림 1.20.1이 자동으로 AWS 지원 빌드가 아님 |
| Auto Mode | 대체 CNI/정책 플러그인 미지원, 관리형 NodeClass/네트워킹 사용 |
| Fargate | 대체 CNI/DaemonSet 설치 미지원 |
| Windows | Cilium Agent 요구사항은 Linux, 이 레시피를 Windows 워커에 적용하지 않음 |

AWS 일반 대체 CNI 문서와 Hybrid 전용 가이드의 Calico 지원 표현은 다르며 예제 저장소 이동만으로 지원 종료가 입증되지는 않습니다. Hybrid는 정확한 배포판·기능·지원 주체를 확인하세요. Auto Mode의 node-local CoreDNS/시스템 네트워킹도 이 문서의 일반 EC2 구성과 다릅니다. Non-Auto 노드가 섞이면 기존 DNS Deployment가 여전히 필요합니다.

### 준비된 EC2 클러스터의 Cilium ENI

다음은 **준비된 IPv4 EC2 클러스터용 Cilium Helm values**이며 전체 클러스터 생성이나 in-place 전환 레시피가 아닙니다. 사용 전에 다음을 준비하세요.

1. 지원 EKS/Kubernetes 버전과 Linux AMI, 하나의 CNI 소유자를 선택합니다. 기존 워크로드 클러스터에서 `aws-node`를 삭제하는 단축 방법을 사용하지 않습니다.
2. Cilium이 노드를 관리하기 전까지 워크로드가 기다리도록 taint/스케줄링을 준비합니다. 업스트림 EKS 가이드는 `node.cilium.io/agent-not-ready=true:NoExecute`를 사용하므로 실제 노드 수명주기의 eviction/bootstrap 영향을 검토해야 합니다.
3. 서브넷 용량, ENI quota/Security Group, 노드 metadata 접근, operator의 EC2 권한을 준비합니다. 아래 ARN은 **cilium-operator ServiceAccount**를 올바르게 신뢰하는 역할의 자리표시자이며 values 파일이 역할을 생성하지는 않습니다.
4. 이 `kubeProxyReplacement: false` 예제는 작동하는 kube-proxy와 DNS를 유지합니다. 교체 모드는 별도 API 직접 접근/bootstrap DNS 조건을 따르세요. max-Pods는 보편적인 110이 아닌 실제 인스턴스/IPAM 용량으로 결정합니다.

`cilium-eni-values.yaml`로 저장하고 역할·인터페이스를 검토한 값으로 변경하세요.

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
egressMasqueradeInterfaces: eth0
serviceAccounts:
  operator:
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/CiliumOperatorENI
```

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# 클러스터 준비와 렌더링 결과 검토 후:
helm install cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-eni-values.yaml
```

설치 소유 경로에서 설정을 관리하세요. 몇 개 키만 있는 `cilium-config`로 교체하면 다른 필수 설정을 잃을 수 있습니다. 이전 `tunnel=disabled` 대신 `routingMode: native`를 사용합니다. ENI 할당/권한과 SNAT 동작은 실제 환경에서 검증해야 하며 렌더링 성공만으로 EC2 네트워킹이 입증되지는 않습니다.

**IPv6 조건:** 1.20.1 ENI IPAM 참조는 IPv6를 beta로 설명하지만 같은 버전 EKS 전제 페이지에는 여전히 IPv4-only ENI 제한이 있습니다. 이 가이드는 IPv4 예제를 유지하고 문서 불일치를 기록하며 어느 한 문장만으로 프로덕션 EKS IPv6 호환성이 증명되었다고 판단하지 않습니다. 별도 IPv6 설계에는 현재 ENI/dual-stack 서브넷 조건을 확인하세요.

### 대안: VPC CNI Chaining

업스트림 chaining 가이드는 VPC CNI 1.11.2 이상과 다음 구성을 문서화합니다.

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

ENI 교체 values 위에 추가하는 설정이 아닌 **별도 구성**으로 사용하세요. VPC CNI가 할당자로 남습니다. 과거 업스트림 DaemonSet을 적용하는 대신 실제 관리 애드온을 소유 경로에서 업데이트합니다. 같은 endpoint의 경쟁 정책 엔진을 피하세요. CNI chain이 바뀌어도 기존 Pod가 자동으로 Cilium에 연결되지는 않습니다. 계획한 rollout으로 재생성하고 endpoint 관리를 확인해야 합니다. Chaining에는 L7 정책/IPsec 제약이 있으므로 아래 모든 예제가 해당 구성에서도 작동한다고 가정하지 마세요.

### ClusterMesh

고유한 cluster identity, 호환 버전, 접근 가능하고 중복되지 않는 Pod 네트워크, 인증된 API 연결, 적절한 노출 방식이 필요합니다. LoadBalancer Service는 클라우드 리소스를 만들 수 있어 의도적인 네트워크/보안 설계가 필요합니다. 공개 endpoint 두 개만 만든다고 안전한 클러스터 연결이 완성되지는 않습니다. 선택한 토폴로지의 [ClusterMesh 가이드](../../service-mesh/cilium-service-mesh/01-architecture.md)와 고급 장을 따르세요.

## 설치 및 구성

### 클라이언트 도구

워크스테이션 OS/아키텍처에 맞는 공식 Cilium CLI 0.20.0, Hubble CLI 1.19.4 자산을 사용하고 압축 해제 전에 제공된 체크섬을 검증하세요. Linux ARM64/AMD64는 다르며 macOS는 해당 Darwin 자산을 사용합니다. CLI 버전은 Cilium Agent/chart 버전과 별개입니다. [검증된 CLI 설치 안내](../../service-mesh/cilium-service-mesh/README.md)를 참고하세요.

```bash
cilium version --client
hubble version
```

### 일반 Cluster-Pool 예제

다음은 kube-proxy와 DNS가 작동하는 일반 Linux 클러스터의 **별도 대안**입니다. 예시 Pod 범위 `10.244.0.0/16`이 클러스터와 맞고 Service, 노드, VPC, 연결 네트워크와 중복되지 않아야 합니다. ENI 모드에 이 pool 설정을 사용하지 마세요.

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - icmp
    - httpV2
```

`cilium-values.yaml`로 저장하고 고정 버전 차트를 렌더링한 후 준비된 클러스터에만 설치합니다.

```bash
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

기존 release는 업그레이드/GitOps 경로에서 소유 values를 보존하며 버전별 절차를 따릅니다. `cilium install`을 반복하는 것은 개별 설정 변경의 일반적인 방법이 아닙니다.

| 선택 | 현재 설정과 전제 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel`과 `tunnelProtocol`, 해당 캡슐화 허용과 경로 MTU 설정 |
| Native routing | `routingMode: native`, underlay의 Pod 주소 라우팅 필요, `autoDirectNodeRoutes`는 임의의 다중 서브넷이 아닌 적합한 직접 연결 전제 |
| kube-proxy 교체 | 이전 `strict` 대신 `kubeProxyReplacement: true`/`false`, 교체 시 도달 가능한 `k8sServiceHost`/`k8sServicePort`와 bootstrap 계획 필요 |
| WireGuard | 커널/플랫폼과 peer 경로 확인 후 지원 모드 활성화, 모든 트래픽 자동 암호화가 아님 |
| IPsec | 문서화된 key Secret, 키 배포/교체, 호환 모드 필요, Helm enable 플래그만으로 불충분 |
| XDP/DSR/BBR | 장치/커널/토폴로지별 별도 선택, 보편적인 설치 프리셋이 아님 |

## 네트워크 정책

Kubernetes `networking.k8s.io/v1` NetworkPolicy와 Cilium `cilium.io/v2` 정책은 별도 API입니다. 여러 allow 정책이 합쳐질 수 있습니다. 다음은 L4 허용이 L7 제한을 우회하지 않도록 **각기 다른 준비된 테스트 네임스페이스**를 사용합니다. 실제 endpoint를 선택하는 모든 정책을 검토하세요.

### L4 예제

`cilium-l4-demo`에서 backend Pod를 선택하고 같은 네임스페이스 frontend Pod의 TCP 8080 ingress를 허용합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-l4-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - port: 8080
      protocol: TCP
```

### HTTP 예제

별도 `cilium-l7-demo`에서 backend Pod를 선택하고 해당 네임스페이스 frontend의 TCP 8080 평문 HTTP를 지정한 method/path로 제한합니다. 선택한 CNI 모드에서 L7 proxy를 지원해야 하며 암호화된 HTTP가 지원 termination 설정 없이 자동 검사되지는 않습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-product-read
  namespace: cilium-l7-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-l7-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/api/v1/products$
```

같은 peer/port에 제한 없는 L4 allow를 추가하지 마세요. Cilium 문서는 이 경우 더 좁은 L7 제한이 효력을 잃는다고 설명합니다. L7 거부는 패킷 drop 대신 HTTP 403을 반환할 수 있습니다. 실제 endpoint identity로 허용 GET과 거부 method/path를 테스트하세요.

### DNS/FQDN 예제

`cilium-dns-demo`에서 일반 CoreDNS Pod로의 DNS 질의와 `api.example.com`에서 학습한 주소의 TCP 443을 허용합니다. 도메인은 예시이므로 승인한 대상으로 바꾸세요. 광범위한 `*.amazonaws.com`은 계정/리소스 경계가 아니므로 제외했습니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-api-domain
  namespace: cilium-dns-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:k8s-app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

DNS wildcard는 선택한 resolver로 질의를 허용할 뿐 반환된 모든 주소로의 연결을 허용하지는 않습니다. 임의 DNS 이름을 전달할 수 있으므로 필요하면 search suffix까지 고려해 질의 이름을 제한하세요. NodeLocal DNS나 다른 resolver에는 알맞은 목적지 선택이 필요합니다. FQDN 정책은 DNS로 얻은 IP 인가이며 TLS hostname 검증이나 HTTP URL 인가가 아닙니다. 공유 IP와 애플리케이션 TLS/인증도 고려해야 합니다.

## Hubble 관측성

위 cluster-pool values는 Relay/UI와 메트릭을 활성화합니다. 기존 설치는 소유 경로에서 의도한 Hubble values를 적용하세요. `cilium hubble enable --ui`는 지원 편의 명령이지만 `cilium hubble enable --metrics=...`는 CLI 0.20.0의 지원 플래그가 아닙니다. Helm의 `hubble.metrics.enabled`를 설정하고 이전 `http`와 `httpV2` handler를 동시에 켜지 마세요.

한 터미널에서 Relay port-forward를 유지합니다.

```bash
cilium hubble port-forward --port-forward 4245
```

Hubble CLI가 있는 다른 터미널에서 실행합니다.

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

로컬 예제는 Relay 서버 기본 구성을 전제로 하며 TLS를 켠 Relay에는 맞는 client trust/인증이 필요합니다. HTTP event는 해당 트래픽이 설정한 L7 proxy를 거쳐야 나옵니다. `DROPPED`는 datapath verdict이며 모든 애플리케이션 실패를 뜻하지 않습니다. UI port-forward는 `cilium hubble ui`를 사용하고 Prometheus target discovery는 별도로 설정합니다. Hubble flow streaming 자체가 분산 애플리케이션 tracing은 아닙니다.

## 테스트와 운영

Connectivity/performance 명령은 테스트 워크로드를 만들며 정책을 바꾸거나 상당한 트래픽을 생성할 수 있습니다. 검토한 테스트 네임스페이스/환경과 권한을 사용해야 합니다. 이 감사에서는 실제 클러스터에 실행하지 않았습니다.

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

성능 runner는 `cilium connectivity perf`입니다. `connectivity test --test=performance`는 테스트 이름 filter일 뿐 성능 runner가 아닙니다. 처리량/지연 비교 전에 소프트웨어 버전, 토폴로지, 트래픽, 원본 결과를 기록하세요.

조회 시 관리 CLI와 **에이전트 내부 `cilium-dbg`**를 구분합니다.

```bash
cilium status --verbose
kubectl get cnp,ccnp -A
kubectl get pods -n kube-system -l k8s-app=cilium -o wide

# 문제가 있는 노드의 Agent Pod를 선택합니다.
CILIUM_POD=replace-with-actual-cilium-pod
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg metrics list
kubectl logs -n kube-system "$CILIUM_POD" -c cilium-agent --since=15m --tail=200 --timestamps
```

관리 CLI의 `cilium endpoint list`, `cilium bpf maps list`, `cilium metrics list`는 같은 명령이 아닙니다. `cilium sysdump`로 진단 자료를 모을 수 있지만 인프라/로그 자료를 보호해야 합니다. Agent Ready나 scrape 성공은 애플리케이션과 거부 정책 테스트를 대신하지 않습니다.

### 운영 우선순위

- Map preallocation, XDP, DSR, BBR, 고정 device 패턴을 켜기 전에 측정하세요. 자원을 사용하거나 패킷 경로를 바꾸므로 기능별 검증이 필요합니다.
- 선택한 범위에서 DNS, API, identity, 애플리케이션 의존성을 명시적으로 허용한 뒤 default-deny를 도입합니다. 기존 연결뿐 아니라 신규 Pod와 업그레이드 전환도 확인하세요.
- 암호화, 인증서/키 교체, 정책 적용, 관측성을 별도 인수 검사로 다룹니다. 사용할 수 있는 관리/복구 경로를 보존하세요.
- 현재 플랫폼 매트릭스와 지원 업그레이드 경로를 확인합니다. 과거 릴리스 발표로 현재 배포 호환성이 증명되지는 않습니다.

## 딥다이브 목차

**[Cilium 소개 및 기본 개념](01-introduction.md)**
- Cilium 개요 및 역사
- 컨테이너 네트워킹 기초
- CNI(Container Network Interface) 이해하기
- Cilium의 차별화 포인트

**[eBPF 기술 심층 분석](02-ebpf.md)**
- eBPF 기술 소개 및 역사
- 커널 내 eBPF 작동 방식
- eBPF 프로그램 유형 및 맵
- Cilium에서의 eBPF 활용

**[네트워킹 모델 및 VXLAN](03-networking.md)**
- 컨테이너 네트워킹 모델 비교
- VXLAN 기술 심층 분석
- Cilium의 오버레이 네트워킹
- 성능 최적화 기법
- 라우팅 메커니즘 (Encapsulation vs Native-Routing)
- 클라우드 제공업체별 네트워킹 (AWS ENI, Google Cloud)

**[IPAM 및 네트워크 정책](04-ipam-policy.md)**
- IP 주소 관리(IPAM) 전략
- Kubernetes와 Cilium IPAM 통합
- 네트워크 정책 설계 및 구현
- 멀티 클러스터 시나리오
- IPAM 모드 심층 분석 (Cluster Scope, Kubernetes Host Scope, Multi-Pool)
- 클라우드 제공업체별 IPAM (Azure IPAM, AWS ENI, GKE)
- CRD 기반 IPAM

**[L2-L7 네트워킹 및 로드 밸런싱](05-l2-l7-networking.md)**
- OSI 모델 계층 이해 (L2, L3, L4, L7)
- Cilium의 계층별 기능
- 서비스 메시 통합
- 로드 밸런싱 아키텍처
- 마스커레이딩 구성 및 구현 모드
- IPv4 프래그먼트 처리

**[보안 및 가시성](06-security-visibility.md)**
- Cilium의 보안 기능
- 네트워크 가시성 및 모니터링
- Hubble 아키텍처 및 활용
- 실시간 위협 탐지

**[고급 주제 및 실제 사례](07-advanced-topics.md)**
- 성능 튜닝 및 문제 해결
- 대규모 배포 전략
- 실제 사용 사례 연구
- 미래 로드맵 및 발전 방향

## 추가 자료

- [네트워킹 개념 심층 분석](networking-concepts.md)
- [용어 및 약어](glossary.md)

## 참고 자료

- [Cilium 1.20 Kubernetes 호환성](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/compatibility.rst)
- [Cilium 시스템 요구사항](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)
- [EKS 전제조건](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst)
- [AWS 대체 CNI 지원](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7 정책 의미](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst)
- [Hubble 프로젝트](https://github.com/cilium/hubble)
- [Flannel 네트워킹/정책 통합](https://github.com/flannel-io/flannel)
- [Calico 비교 용어](../calico/glossary.md)

## 퀴즈

이 섹션에서 배운 내용을 테스트하려면 [Cilium 딥다이브 퀴즈](../../quizzes/networking/cilium/01-introduction-quiz.md)를 풀어보세요.
