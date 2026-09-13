# Part 1: 소개

> **검토 기준**: Cilium 1.20.1 / Cilium CLI 0.20.0 / Hubble CLI 1.19.4. **마지막 업데이트**: 2026년 9월 12일

## 실습 환경 설정

격리된 준비 환경을 사용하세요. Cilium 1.20의 Kubernetes 테스트 범위는 **1.33–1.36**입니다. 노드는 AMD64/AArch64 Linux와 커널 **5.10 이상**, 또는 문서화된 동등 조건(예: RHEL 8.10의 backport된 4.18)을 충족해야 합니다. Kind/minikube는 노드/VM 커널을 사용하므로 워크스테이션 OS 이름만으로 호환성이 확인되지는 않습니다. 기능별 추가 조건도 확인하세요.

Kubectl은 API 서버와 한 마이너 버전 이내여야 합니다. [메인 가이드](README.md)에 따라 OS/아키텍처에 맞는 Cilium/Hubble CLI 자산과 체크섬을 검증하세요. Helm으로 설정을 렌더링·검토할 수 있으며 이 감사는 Helm 3.21.3을 사용했습니다. 검증하지 않은 `latest` AMD64 다운로드나 장마다 같은 release 재설치를 반복하지 마세요.

### 선택한 구성으로 한 번 설치

EKS ENI, VPC CNI chaining, 일반 cluster-pool은 전제조건이 다릅니다. [메인 가이드](README.md)를 참고하세요. 다음은 kube-proxy/DNS가 작동하고 하나의 CNI 소유자를 준비한 **일반 IPv4 cluster-pool 대안**입니다. EKS 마이그레이션 레시피가 아닙니다. Pod CIDR이 Service, 노드, 연결 네트워크와 겹치지 않는지 확인하세요.

`cilium-lab-values.yaml`로 저장합니다.

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

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
kubectl --context "$CILIUM_LAB_CONTEXT" get nodes -o wide
cilium version --client

# 클러스터/CNI 소유권과 values를 준비한 새 설치에만 적용합니다.
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.1 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

이미 Cilium이 있다면 버전/설정을 확인하고 소유자의 업그레이드 절차를 따르세요. 설치/status 명령이나 이후 connectivity test가 프로덕션 호환성을 증명하지는 않습니다. 이 감사에서 클러스터를 프로비저닝하지 않았습니다.

## Cilium이란?

Cilium은 Linux eBPF 데이터플레인과 Kubernetes 통합으로 네트워킹, 보안, 관측성을 제공합니다. Endpoint 정책, 모드별 IPAM/라우팅, Service 처리, Hubble flow 가시성이 포함됩니다. Docker libnetwork 통합은 1.20에서 제거되었으므로 Kubernetes, Docker, Mesos를 현재 동일한 설치 대상으로 제시하면 안 됩니다.

### 핵심 컴포넌트와 기능

| 컴포넌트 / 기능 | 역할과 조건 |
| --- | --- |
| Cilium Agent | 노드 endpoint/dataplane 관리, 모든 호스트 네트워킹 기능을 소유하는 것은 아님 |
| Cilium Operator | 클러스터 할당/identity/controller 작업, 여러 replica와 해당 작업의 leader election 지원, 검토한 차트 기본 replica는 2 |
| eBPF | 검증과 기능 요건을 따르는 커널 hook의 프로그램/map, 실제 성능은 측정 필요 |
| L3/L4와 L7 정책 | L7은 지원 Envoy/DNS proxy 경로 필요, Kafka 인지 L7은 1.20에서 제거되었지만 Kafka 연결의 L4 제어는 가능 |
| kube-proxy 교체 | 선택적인 Service 처리, DSR·Maglev·XDP는 별도 설정/토폴로지 조건 |
| 암호화 | `encryption.type`에서 `ipsec`, `wireguard`, beta `ztunnel`을 선택하며, ztunnel 워크로드 mTLS는 별도의 enrollment·bootstrap·트래픽·정책 전제가 필요 |
| Hubble | 네트워크/proxy flow와 서비스 맵 관측, 자동 end-to-end 애플리케이션 tracing이 아님 |
| ClusterMesh / BGP | ClusterMesh는 identity·신뢰·네트워크 도달성 필요, BGP는 광고 기능이며 내부 라우팅을 설정하지 않음 |

컴포넌트 관계는 kubelet이 **CRI**로 Pod sandbox 작업을 요청하고, 컨테이너 런타임이 **CNI 플러그인**을 호출하며, Cilium이 endpoint 설정을 조정하고 agent가 dataplane을 설정하는 구조입니다. CNI는 패킷마다 통과하는 전달 계층이 아닙니다. Envoy는 설정한 L7 proxy 트래픽을 처리하고 Hubble flow event와 Prometheus scrape는 별도 경로입니다.

### 보안 Identity

Security identity는 해당 할당 범위에서 endpoint의 **보안 관련 레이블 집합**에 할당한 숫자 식별자입니다. 레이블은 필터링/설정되며 namespace에서 파생한 레이블을 포함할 수 있습니다. 같은 `app` 값만으로 네임스페이스나 클러스터가 다른 Pod가 같은 identity를 공유한다고 보장할 수 없습니다. 숫자 ID는 영구적 전역 hash나 Pod IP가 아니며 다른 endpoint 유형도 identity를 사용합니다.

## 컨테이너 네트워킹 기초

Host networking은 호스트 network namespace를 공유합니다. Bridge는 호스트의 인터페이스를 연결하고 overlay는 underlay 위에 캡슐화합니다. Native routing은 underlay가 Pod 주소에 도달할 수 있어야 합니다. 이 개념은 함께 사용될 수 있으며 eBPF와 Netfilter 구현 선택과 혼동하면 안 됩니다.

운영에서는 주소 용량, 라우팅/MTU, Service 동작, tenant 정책, 관측성, 장애 복구를 검토합니다. 네트워크 모델 하나만으로 성능이나 보안이 결정되지는 않습니다.

## CNI 이해하기

CNI는 컨테이너 네트워크 설정을 위한 CNCF 규격/라이브러리/플러그인 체계입니다. JSON으로 설정과 결과를 교환하고 IPAM 플러그인에 주소 할당을 위임할 수 있습니다. CNI의 설정/제거 계약은 kubelet과 컨테이너 런타임 사이의 CRI와 다릅니다. Kubernetes 1.24부터 kubelet은 제거된 `--network-plugin`/`--cni-bin-dir` 설정 플래그를 소유하지 않습니다.

| 프로젝트 | 구분할 사항 |
| --- | --- |
| Cilium | Linux eBPF, 여러 routing/IPAM 모드, proxy를 사용하는 L7 정책과 Hubble |
| Calico | Linux Iptables/Nftables/BPF와 지원 Windows HNS, OSS WireGuard·staged policy·별도 L7 통합 |
| Flannel | VXLAN/host-gw/WireGuard 등 연결 backend, 선택적 차트 컨트롤러나 다른 구현으로 정책 추가 |
| AWS VPC CNI | VPC 주소 할당/네트워킹, 지원 EC2 Linux의 네이티브 정책과 별도 SG-for-Pods |
| Weave Net | 원래 weaveworks/weave 저장소는 archived 상태, 과거 선택지로 구분하고 사용할 유지 배포판은 별도 확인 |

지원 경계는 [현재 비교](README.md)를 참고하세요. 상한 없는 Kubernetes 호환성이나 “매우 높음/높음/중간” 성능 등급을 배포 근거로 사용하지 마세요. 서비스 메시는 일반 Pod 네트워킹의 필수 요건이 아닌 선택적 통합입니다.

## 실습: 제한된 L4 정책

선택한 context와 전용 네임스페이스를 사용합니다. 예제는 정책을 정의하며 애플리케이션 서버나 클라이언트 이미지를 **배포하지 않습니다**. 승인된 이미지/도구로 controller가 관리하는 테스트 워크로드를 준비하세요.

- `app=backend` 레이블과 TCP 8080 listener가 있는 backend Pod.
- 적절한 테스트 클라이언트가 있는 `app=frontend` Pod와 다른 레이블의 client Pod.
- 일반 관리 Pod 인터페이스, 기본 레이블 처리, 확인한 DNS/Service 구성, 의도한 격리를 무효화할 다른 matching allow 정책이 없는 환경.

네임스페이스 정의를 `cilium-intro-namespace.yaml`로 저장·적용한 뒤 테스트 워크로드를 준비하세요:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cilium-intro-demo
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-namespace.yaml
```

다음을 `cilium-intro-policy.yaml`로 저장합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n cilium-intro-demo --show-labels
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-policy.yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n cilium-intro-demo
```

위 전제와 추가 matching allow가 없을 때 **일반 Pod 간 ingress**의 기대 결과는 다음과 같습니다.

| 출발지 / 목적지 | 기대 결과 |
| --- | --- |
| 같은 namespace frontend → backend TCP 8080 | 허용 |
| 다른 client 레이블 → backend TCP 8080 | 거부 |
| Frontend → backend의 다른 port/protocol | 이 정책에서는 허용하지 않음 |
| 다른 namespace의 같은 app 레이블 | 이 정책에서는 허용하지 않음 |

정책 반영 후 성공/실패 연결을 모두 검증하세요. 다른 allow/deny 정책, host 트래픽과 probe는 결과를 바꿀 수 있습니다. 이 ingress 규칙은 frontend egress나 HTTP method/path를 제한하지 않습니다. API 접수 성공을 적용 성공으로 가정하지 말고 실제 트래픽과 endpoint 상태를 확인하세요.

`cilium connectivity test`는 워크로드와 정책을 만드는 추가 테스트 runner입니다. 필요한 권한을 갖춘 검토 환경에서만 실행하며 읽기 전용 status 명령이 아닙니다. 별도 성능 runner는 `cilium connectivity perf`이며 측정 시 실제 버전·토폴로지·원본 결과를 보존하세요.

## 참고 자료와 다음 단계

- [Cilium 요구사항과 설정](README.md)
- [CNI 프로젝트](https://github.com/containernetworking/cni)
- [Kubernetes network plugin과 runtime 소유권](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes client version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Cilium identity와 용어](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/gettingstarted/terminology.rst)
- [원래 Weave 저장소 metadata](https://api.github.com/repos/weaveworks/weave)

[eBPF](02-ebpf.md)로 진행하거나 [소개 퀴즈](../../quizzes/networking/cilium/01-introduction-quiz.md)로 이해를 확인하세요.
