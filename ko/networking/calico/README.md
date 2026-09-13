# Calico 딥다이브: Kubernetes 네트워킹과 정책

> **검토 기준**: Calico Open Source 3.32.2 · **마지막 업데이트**: 2026년 9월 12일
> Calico 3.32의 공식 시험 대상은 Kubernetes 1.34–1.36입니다. `3.29+ / Kubernetes 1.28+` 전체의 호환성을 보장하는 범위가 아닙니다.

## 개요

Calico는 Kubernetes 네트워킹과 네트워크 정책을 제공하며, 배포 방식과 제품 에디션에 따라 호스트·VM 기능도 제공합니다. 이 시리즈는 아키텍처, 캡슐화와 라우팅, BGP, 정책, eBPF, EKS 통합과 운영을 다룹니다. 출처 없는 성숙도·리소스 순위 대신 [현재 요구사항](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)을 기준으로 구성을 선택하세요.

### 2026년 7월: Calico for VMs on Kubernetes

Tigera의 [공식 발표](https://www.tigera.io/news/tigera-launches-ebpf-powered-calico-for-vms-on-kubernetes-vm-migration-that-doesnt-require-rebuilding-the-network/) 날짜는 **2026년 7월 23일**입니다. VMware 마이그레이션을 위한 VM·컨테이너 네트워킹, IP 유지, L2 브리지 확장, 정책과 관측성을 설명합니다. 모든 광고 기능이 Calico Open Source에 포함된다는 뜻은 아닙니다. 정확한 에디션·토폴로지·기능 상태를 확인하세요. [Enterprise 3.23 릴리스 노트](https://docs.tigera.io/calico-enterprise/latest/release-notes/)는 KubeVirt live migration을 여전히 tech preview로 표시합니다. 제품 출시 발표와 개별 기능의 지원 상태를 구분해야 합니다.

## 호환성과 기능 범위

- Calico 3.32.2는 2026년 8월 30일에 공개되었습니다. 공식 Kubernetes 시험 대상은 1.34·1.35·1.36이며, Kubernetes 1.37이 출시되었다고 호환성이 입증된 것은 아닙니다.
- 일반 Linux 요구사항은 필요한 모듈을 포함한 커널 5.10 이상입니다. 지원 아키텍처·벤더 백포트·개별 기능의 더 높은 요구사항은 eBPF 가이드에서 확인합니다.
- Linux 데이터플레인에는 iptables·nftables·eBPF가 있습니다. 기본값은 설치 방식과 플랫폼에 따라 다르며 현재 자체 관리 kubeadm의 operator 설치는 eBPF가 기본일 수 있습니다. 모든 기능이 동일하다고 보장하지 않습니다.
- [Calico for Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)는 명시된 IPv4 VXLAN·BGP 구성을 지원하지만 Linux eBPF·IPIP·IPv6/dual stack·WireGuard와 모든 Linux 정책 기능을 지원하지는 않습니다.
- Open Source에도 정책 tier, Goldmane 플로우 집계와 Whisker UI가 있습니다. DNS/FQDN 정책·애플리케이션 계층 정책 등은 [제품 비교](https://docs.tigera.io/calico/latest/about/calico-product-editions)의 에디션 구분을 확인해야 합니다.

## Calico와 Cilium

| 요구사항 | Calico | Cilium |
|---|---|---|
| Linux 데이터플레인 | 구성에 따라 iptables / nftables / eBPF | eBPF, 해당 L7 기능에는 Envoy 사용 |
| Kubernetes NetworkPolicy | 지원, Calico 정책과 tier 확장 | 지원, Cilium 정책 확장 |
| L7 / DNS 정책 | Enterprise/Cloud 라이선스와 기능 상태 확인 | HTTP·DNS 정책 제공, 프로토콜별 제약 확인 |
| BGP | 해당 네트워킹 모드에서 BIRD 기반 라우팅 | BGP 컨트롤 플레인 광고, 필요한 경로·토폴로지 확인 |
| 관측성 | Open Source Goldmane/Whisker와 메트릭, 추가 유료 기능 | Hubble과 메트릭 |
| Windows | 상당한 제약이 있는 명시적 구성 지원 | Cilium 1.20 에이전트는 Linux 필요, Windows beta 데이터플레인 아님 |
| kube-proxy 대체 | eBPF 데이터플레인에서 가능 | 구성 시 가능 |
| 멀티클러스터 / 메시 | 별도 기능·통합이며 에디션에 따라 다름 | Cluster Mesh와 선택적 메시 기능, 설치만으로 모두 활성화되지 않음 |

둘 다 운영 환경의 선택지가 될 수 있습니다. 리소스 사용량과 운영 복잡도는 정책·트래픽·플랫폼·설정에 따라 달라집니다. 대상 환경에서 필요한 기능을 검증하세요. 서로 다른 환경에서 동작한다는 이유로 한 클러스터에 기본 CNI 두 개를 설치하면 안 됩니다. Cilium의 [버전별 요구사항](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)과 이 사이트의 [Cilium 서비스 메시 가이드](../../service-mesh/cilium-service-mesh/README.md)에서 플랫폼·메시 범위를 확인할 수 있습니다.

## 아키텍처

컴포넌트는 네트워킹 모드에 따라 달라집니다. 아래 EKS policy-only 예제는 Kubernetes 데이터스토어를 사용하고 BIRD/confd는 사용하지 않습니다. “컨트롤 플레인”은 논리적 역할이며 EKS 관리형 컨트롤 플레인 머신에 배포한다는 뜻이 아닙니다. Typha는 노드별 프로세스가 아니라 별도 Deployment입니다.

| 컴포넌트 | 역할과 범위 |
|---|---|
| Felix | 워크로드 노드에서 정책과 해당 라우트 프로그래밍 |
| BIRD / confd | 해당 백엔드를 켰을 때 BGP와 설정 생성, policy-only에는 없음 |
| Typha | 선택적 데이터스토어 업데이트 캐시·분배, operator가 규모에 맞춰 복제 수 관리, 항상 3개가 아님 |
| kube-controllers | Kubernetes 리소스 조정·동기화·정리 |
| Calico CNI / IPAM | Calico가 네트워킹을 맡을 때 인터페이스·Pod 주소 관리, EKS 예제에서는 Amazon VPC CNI/IPAM이 담당 |
| Calico API server | 기본 모델에서 내부 CRD 위에 `projectcalico.org/v3` 집계 API 제공, native v3 CRD는 별도의 tech preview |

[아키텍처 레퍼런스](https://docs.tigera.io/calico/latest/reference/architecture/overview)와 실제 렌더링된 워크로드로 활성 컴포넌트를 확인하세요. 이 가이드는 Kubernetes API 데이터스토어를 사용하며 etcd 기반 설계에는 별도의 설치·기능 제약이 있습니다.

## 네트워킹 모드와 MTU

| 모드 | 캡슐화와 라우팅 | MTU 1500인 IPv4 언더레이의 Pod MTU 예 |
|---|---|---|
| IPIP | IPv4-in-IPv4, 일반적으로 BGP로 라우트 배포 | 1480 |
| VXLAN | 기본 UDP 4789, VXLAN Pod 라우팅에는 BGP가 필수가 아님 | 1450 |
| 비캡슐화 | 언더레이에서 Pod 주소 라우팅 필요, BGP는 경로 배포 방법 중 하나 | 1500 |
| CrossSubnet | 노드 서브넷을 넘을 때만 캡슐화하는 IPIP 또는 VXLAN 설정 | 터널이 필요한 경로의 오버헤드를 여전히 확보해야 함 |

이 MTU는 예시이며 고정 상수가 아닙니다. IPv6 VXLAN 오버헤드·점보 언더레이·WireGuard·클라우드 경로 한도에 따라 달라집니다. IPIP는 IPv4 전용이며 IPIP가 부적합한 환경에서도 IPv4 VXLAN을 사용할 수 있습니다. [MTU 설정](https://docs.tigera.io/calico/latest/networking/configuring/mtu)과 [오버레이 요구사항](https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip)을 확인하세요. BGP가 가능하다고 언더레이 모든 홉의 Pod CIDR 라우팅이 보장되지는 않으며, 라우팅된 비캡슐화 패브릭에 동일 L2 인접성이 항상 필요한 것도 아닙니다. 언더레이·포트·주소 패밀리·플랫폼을 먼저 계획해야 합니다.

## EKS: Amazon VPC CNI를 유지하고 Calico 정책 추가

기존의 지원되는 Amazon VPC CNI를 사용하는 Linux EC2 노드용 예제이며 Pod 네트워킹을 교체하지 않습니다. Auto Mode나 Fargate 설치 절차는 아닙니다. [공식 EKS 가이드](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)의 조건은 다음과 같습니다.

1. Calico를 정책 엔진으로 선택하기 전에 Amazon VPC CNI의 기본 네트워크 정책 강제를 비활성화해야 합니다. 둘을 함께 실행하면 충돌합니다. 보호 중인 기존 클러스터에서는 무방비 전환 구간이 생기지 않도록 정책 인계를 계획하고 검증합니다.
2. VPC CNI에 `ANNOTATE_POD_IP=true`를 설정하고 `aws-node` ServiceAccount에 Pod `patch` 권한을 부여합니다. 조정 루프가 되돌리지 않도록 설치된 애드온·설정 소유자를 통해 관리합니다. 아래 추가 RBAC 예제를 적용하기 전에 실제 ServiceAccount 이름을 확인하세요.
3. `ENABLE_V4_EGRESS=true`인 IPv6 Pod의 강제를 보장하면 안 됩니다. Calico EKS 가이드는 이 조합을 명시적으로 제외합니다.
4. 아래 설치 방식 중 **하나만** 선택합니다. 새 설치용이며 기존 operator의 소유권을 가져오거나 활성 CNI를 마이그레이션하는 명령이 아닙니다.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-ip-patch
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-ip-patch
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-ip-patch
subjects:
  - kind: ServiceAccount
    name: aws-node
    namespace: kube-system
```

### 방식 A: 버전을 고정한 operator 매니페스트

```bash
set -euo pipefail
CALICO_VERSION=v3.32.2
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/v1_crd_projectcalico_org.yaml"
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml"
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=300s
kubectl apply -f - <<'YAML'
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
```

### 방식 B: 버전을 고정한 Helm 설치

동일한 VPC CNI 사전 조건을 먼저 충족합니다. Calico 3.32는 CRD 설치와 operator 차트를 분리하므로 새 클러스터에서 작은 operator 차트만 설치해서는 충분하지 않습니다. 아래 값을 `calico-eks-values.yaml`로 저장합니다.

```yaml
installation:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
apiServer:
  enabled: true
```

```bash
set -euo pipefail
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico-crds projectcalico/crd.projectcalico.org.v1 --version v3.32.2   | kubectl apply --server-side -f -
helm install calico projectcalico/tigera-operator --version v3.32.2   --namespace tigera-operator --create-namespace -f calico-eks-values.yaml
```

이 버전의 차트는 Goldmane와 Whisker도 기본으로 활성화합니다. 렌더링한 매니페스트에서 해당 컴포넌트와 접근 통제를 검토하세요. native `projectcalico.org/v3` CRD는 별도의 tech preview이며 여기서는 기존 내부 CRD와 집계 API 서버를 사용합니다.

### 설치를 확인한 뒤 정책 동작 검증

```bash
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl get felixconfigurations.projectcalico.org
```

Degraded·Progressing 상태를 확인하고 임시 워크로드로 허용·거부 흐름을 모두 시험한 뒤 정책 강제를 신뢰하세요. Ready DaemonSet만으로 정책이 입증되지는 않습니다. AmazonVPC policy-only에서는 AWS가 Pod IPAM과 네트워킹을 제공하므로 Calico IPPool이 없거나 BIRD 세션이 없는 것이 반드시 장애는 아닙니다.

### Calico 전체 네트워킹과 다른 설치 방법

EKS에서 Calico가 전체 네트워킹을 맡는 구성은 별도의 새 클러스터 설계입니다. 공식 절차는 워크로드 노드가 없는 상태에서 시작해 CNI를 설정한 뒤 노드를 추가합니다. 실행 중인 VPC CNI 클러스터에 `cni.type: Calico` 조각을 덮어 적용하지 마세요. [EKS 통합](08-eks-integration.md)과 공식 EKS 절차를 참고하세요. CNI가 아직 없는 자체 관리 클러스터에는 [온프레미스 가이드](https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises)를 사용합니다. 직접 매니페스트도 대안이지만 네임스페이스·Typha 구성·수명주기가 operator 설치와 다릅니다. Helm·operator·`calico.yaml`을 겹치지 말고 소유자를 하나 선택하세요.

## 적용 범위를 명시한 정책 예제

전용 `calico-demo` 네임스페이스를 사용합니다. 아래 ingress·egress 예제는 해당 네임스페이스만 선택하며 클러스터 전체의 제로 트러스트 전환 절차가 아닙니다. 기존 Calico tier와 앞선 정책이 결과에 영향을 줄 수 있습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: calico-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

peer의 `podSelector`는 **같은 네임스페이스**의 frontend Pod를 뜻합니다. 사용자 인증·같은 네임스페이스 전체 통신 허용·egress 정책 설정을 의미하지 않습니다. 다음 별도 예제는 데모 네임스페이스의 egress를 선택된 CoreDNS Pod의 UDP/TCP 53으로 제한하고 나머지를 거부합니다.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-dns-only
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: all()
  order: 100
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Deny
```

실제 DNS 엔드포인트와 라벨을 먼저 확인합니다. 이 selector 예제는 일반 CoreDNS Pod용이며 NodeLocal DNSCache나 Auto Mode 시스템 리졸버용 정책이 아닙니다. 53번 포트만으로 승인된 DNS 서버를 식별할 수는 없습니다. 애플리케이션 egress도 필요하면 마지막 Deny를 켜기 전에 명시적인 허용을 설계하고 시험하세요. 뒤의 별도 Allow는 이미 매칭된 앞선 Calico Deny를 뒤집지 못합니다.

### FQDN 정책은 에디션별 기능

Calico Enterprise/Cloud DNS 정책의 `destination.domains` 필드는 **Open Source 3.32.2 NetworkPolicy 스키마에 없습니다**. 이 Open Source 설치에 적용하면 안 됩니다. 해당 제품을 사용하는 배포에서는 [도메인 기반 정책 가이드](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy)에 따라 신뢰하는 DNS 서버와 DNS 허용 경로를 구성하세요. `*.amazonaws.com`은 광범위한 허용이며 특정 AWS 계정이나 서비스의 인증이 아닙니다. DNS-IP 기반 허용은 HTTP Host나 TLS 신원 검증과도 다릅니다.

## 모니터링과 상태 확인

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
```

Felix 메트릭은 기본 비활성입니다. 리스너를 켠다고 Prometheus scrape job이 만들어지거나 공개 노출이 안전해지는 것은 아닙니다. [메트릭 가이드](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)에 따라 사설 디스커버리와 접근 통제를 구성하세요. `flowLogsFileEnabled`는 Open Source FelixConfiguration 필드가 아닙니다. Enterprise 파일 로그 설정을 복사하지 말고 지원되는 [Goldmane/Whisker 플로우 로그 경로](https://docs.tigera.io/calico/latest/observability/view-flow-logs)를 사용합니다.

| 메트릭 | 의미 |
|---|---|
| `felix_active_local_endpoints` | 활성 로컬 workload·host 엔드포인트 |
| `felix_active_local_policies` | 이 노드의 엔드포인트에 활성인 정책 |
| `felix_iptables_rules` | 활성 iptables 규칙, 데이터플레인에 따라 적용 |
| `felix_int_dataplane_failures` | 재시도할 데이터플레인 업데이트 실패 |
| `felix_cluster_num_hosts` | Felix가 보는 클러스터 전체 호스트 수, 모든 Felix 값 합산 금지 |
| `typha_connections_accepted` | 누적 수락 연결 수, 현재 연결 수가 아님 |
| `typha_connections_active` | 현재 열린 클라이언트 연결 수 |

[Felix](https://docs.tigera.io/calico/latest/reference/felix/prometheus)와 [Typha](https://docs.tigera.io/calico/latest/reference/typha/prometheus) 레퍼런스를 참고하세요. 컴포넌트 상태·설정 메트릭이며 보편적인 거부 패킷 카운터가 아닙니다. Felix 상태 서버의 기본값은 localhost:9099이고 Typha는 활성화 시 일반적으로 9098을 사용합니다. 실제 배포의 probe부터 확인하세요. 노트북에서 `curl localhost`를 실행해도 노드 상태 서버를 검사하는 것은 아닙니다.

## 트러블슈팅

```bash
kubectl -n calico-system get pods -o wide
kubectl -n calico-system logs -l k8s-app=calico-node -c calico-node --tail=100
kubectl get installations.operator.tigera.io default -o yaml
kubectl get networkpolicies.networking.k8s.io -A
kubectl get networkpolicies.projectcalico.org -A
kubectl get globalnetworkpolicies.projectcalico.org
kubectl get ippools.projectcalico.org -o wide
```

Operator는 일반적으로 `calico-system`, 직접 매니페스트는 `kube-system`을 사용할 수 있습니다. Kubernetes와 Calico NetworkPolicy를 구분하도록 전체 API 리소스 이름을 사용하세요. `kubectl get nodes ...status.conditions`는 Calico 라우팅 상태 명령이 아닙니다. BIRD 상태 명령은 BGP가 켜진 경우에만 적용되고, `calicoctl node status`는 임의의 관리자 노트북이 아니라 적절한 Calico 노드 환경이 필요합니다.

| 증상 | 설정 변경 전에 확인할 사항 |
|---|---|
| Pod IP 없음 | 먼저 IPAM 소유자 확인, policy-only EKS는 VPC CNI 로그·용량, 그 외는 Calico IPAM |
| 노드 간 실패 | 경로·언더레이/방화벽 허용·MTU·선택한 캡슐화, 무작정 터널을 켜면 장애 악화 가능 |
| 정책 불일치 | 엔드포인트 라벨·네임스페이스·방향·tier/order·기존 정책·실제 데이터플레인 |
| 높은 CPU | 트래픽/규칙 규모와 메트릭·프로파일 근거, eBPF 전환은 즉석 만능 해결책이 아닌 계획된 변경 |

필요할 때만 일치하는 버전의 [calicoctl](https://docs.tigera.io/calico/latest/reference/calicoctl/)을 사용하고 실제 운영체제·CPU 아키텍처와 릴리스 파일을 검증하세요. BGP나 Calico IPAM 상태가 없다는 이유만으로 policy-only 장애를 단정하면 안 됩니다.

## 딥다이브 목차

| 파트 | 주제 |
|---|---|
| [1](01-introduction.md) | 소개·프로젝트 이력·실습 준비 |
| [2](02-architecture.md) | 컴포넌트·데이터스토어·패킷 흐름 |
| [3](03-networking-modes.md) | 캡슐화·직접 라우팅·MTU |
| [4](04-bgp-deep-dive.md) | BGP·라우트 리플렉터·외부 연동 |
| [5](05-network-policy.md) | NetworkPolicy·tier·정책 설계 |
| [6](06-ebpf-dataplane.md) | eBPF 설정·제약·트러블슈팅 |
| [7](07-advanced-topics.md) | 고급 네트워킹·보안 주제 |
| [8](08-eks-integration.md) | EKS·VPC CNI 통합 |
| [9](09-operations.md) | 운영·진단 |
| [용어집](glossary.md) | 용어 정리 |

[Calico 소개 퀴즈](../../quizzes/networking/calico/01-introduction-quiz.md) · [공식 문서](https://docs.tigera.io/calico/latest/about/) · [3.32.2 릴리스](https://github.com/projectcalico/calico/releases/tag/v3.32.2)
