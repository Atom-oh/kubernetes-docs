# 용어집 퀴즈

이 퀴즈는 Cilium, eBPF, Kubernetes, 네트워킹과 관련된 주요 용어 및 개념에 대한 이해도를 테스트합니다.

## 객관식 문제

1. eBPF의 정식 명칭은 무엇인가요?
   * A) Enhanced Berkeley Packet Filter
   * B) Extended Berkeley Packet Filter
   * C) Embedded BPF Filter
   * D) External Berkeley Protocol Filter

<details>

<summary>정답 보기</summary>

**정답: B) Extended Berkeley Packet Filter**

**설명:** eBPF는 Extended Berkeley Packet Filter의 약자로, 원래 네트워크 패킷 캡처를 위해 개발된 BPF(Berkeley Packet Filter)의 확장 버전입니다. eBPF는 Linux 커널 내에서 안전하게 프로그램을 실행할 수 있는 기술로, 네트워크 패킷 처리뿐만 아니라 시스템 호출 추적, 성능 모니터링 등 다양한 용도로 사용됩니다. Cilium은 eBPF를 핵심 기술로 활용하여 고성능 네트워킹, 보안, 관찰성 기능을 제공합니다.

</details>

2. Cilium에서 네트워크 정책이 적용되는 기본 단위를 무엇이라고 부르나요?
   * A) Pod
   * B) Node
   * C) Endpoint
   * D) Service

<details>

<summary>정답 보기</summary>

**정답: C) Endpoint**

**설명:** Cilium에서 Endpoint는 네트워크 정책이 적용되는 네트워크 엔드포인트를 의미하며, 일반적으로 Kubernetes 포드에 해당합니다. 각 Endpoint는 고유한 ID를 가지며, Cilium은 이 Endpoint를 기반으로 네트워크 정책을 적용하고 트래픽을 제어합니다. Endpoint는 Cilium Agent에 의해 관리되며, 포드가 생성되면 자동으로 해당 Endpoint가 생성됩니다. `cilium endpoint list` 명령어로 현재 노드의 모든 Endpoint를 확인할 수 있습니다.

</details>

3. XDP(eXpress Data Path)의 주요 특징은 무엇인가요?
   * A) L7 프로토콜 분석
   * B) 네트워크 드라이버 수준에서 패킷 처리
   * C) TLS 암호화
   * D) DNS 해석

<details>

<summary>정답 보기</summary>

**정답: B) 네트워크 드라이버 수준에서 패킷 처리**

**설명:** XDP(eXpress Data Path)는 eBPF 기반 기술로, 네트워크 드라이버 수준(인터럽트 컨텍스트)에서 패킷을 처리합니다. 이는 커널 네트워크 스택을 바이패스하여 매우 높은 성능(초당 수백만 패킷)의 패킷 처리를 가능하게 합니다. XDP는 패킷을 DROP, PASS, TX(전송), REDIRECT 등의 액션으로 처리할 수 있습니다. Cilium은 XDP를 활용하여 DDoS 방어, 고성능 로드 밸런싱, 패킷 필터링 등을 구현합니다.

</details>

4. Cilium의 네트워크 관찰성 플랫폼의 이름은 무엇인가요?
   * A) Prometheus
   * B) Grafana
   * C) Hubble
   * D) Jaeger

<details>

<summary>정답 보기</summary>

**정답: C) Hubble**

**설명:** Hubble은 Cilium의 네트워크 관찰성 플랫폼으로, eBPF를 활용하여 네트워크 흐름을 실시간으로 모니터링하고 분석합니다. Hubble의 주요 기능으로는 네트워크 플로우 모니터링, 서비스 의존성 맵 생성, 네트워크 정책 위반 감지, 성능 메트릭 수집, 보안 이벤트 추적 등이 있습니다. Hubble은 CLI와 웹 기반 UI를 제공하며, Prometheus 및 Grafana와 통합하여 메트릭을 시각화할 수 있습니다.

</details>

5. VXLAN의 정식 명칭과 주요 용도는 무엇인가요?
   * A) Virtual Extended LAN - 가상 네트워크 생성
   * B) Virtual Extensible LAN - L2 오버레이 네트워크
   * C) Very Extended LAN - 대규모 네트워크 확장
   * D) Variable Extensible LAN - 동적 네트워크 구성

<details>

<summary>정답 보기</summary>

**정답: B) Virtual Extensible LAN - L2 오버레이 네트워크**

**설명:** VXLAN(Virtual Extensible LAN)은 계층 2(L2) 네트워크를 계층 3(L3) 네트워크 위에 오버레이하는 네트워크 가상화 기술입니다. VXLAN은 UDP 캡슐화를 사용하여 터널링하며, 24비트 VNI(VXLAN Network Identifier)로 최대 약 1,600만 개의 네트워크 세그먼트를 지원합니다. Cilium에서 VXLAN은 노드 간 포드 통신을 위한 오버레이 네트워킹 모드로 사용됩니다. 대안으로 GENEVE나 네이티브 라우팅 모드를 사용할 수도 있습니다.

</details>

6. BPF Map의 주요 역할은 무엇인가요?
   * A) 네트워크 라우팅 테이블 관리
   * B) eBPF 프로그램 간 데이터 공유 및 저장
   * C) DNS 레코드 캐싱
   * D) TLS 인증서 저장

<details>

<summary>정답 보기</summary>

**정답: B) eBPF 프로그램 간 데이터 공유 및 저장**

**설명:** BPF Map은 eBPF 프로그램에서 데이터를 저장하고 검색하는 데 사용되는 키-값 저장소입니다. BPF Map은 커널 공간과 사용자 공간 간의 데이터 공유에도 사용됩니다. 주요 유형으로는 Hash Map(키-값 저장소), Array Map(인덱스 기반 배열), LRU Map(최근 사용 기반 캐시), Ring Buffer(순환 버퍼) 등이 있습니다. Cilium은 BPF Map을 사용하여 서비스 맵, 백엔드 맵, 연결 추적 테이블 등을 저장합니다.

</details>

7. Cilium에서 포드의 보안 신원을 나타내는 숫자 식별자를 무엇이라고 부르나요?
   * A) Pod ID
   * B) Security Context
   * C) Identity
   * D) Endpoint ID

<details>

<summary>정답 보기</summary>

**정답: C) Identity**

**설명:** Cilium Identity는 포드의 레이블 집합을 기반으로 생성되는 숫자 식별자입니다. 동일한 레이블을 가진 모든 포드는 동일한 Identity를 공유합니다. Identity 기반 정책은 IP 주소 대신 Identity를 사용하여 네트워크 정책을 적용하므로, 포드 IP가 변경되어도 정책이 일관되게 유지됩니다. 이 방식은 확장성이 뛰어나며, 대규모 클러스터에서도 효율적으로 동작합니다. Endpoint ID는 특정 포드 인스턴스를 식별하는 것으로, Identity와는 다릅니다.

</details>

8. IPAM의 정식 명칭과 Cilium에서의 역할은 무엇인가요?
   * A) IP Address Management - IP 주소 할당 및 관리
   * B) Internet Protocol Access Manager - 인터넷 접근 관리
   * C) IP Assignment Module - IP 할당 모듈
   * D) Internal Protocol Address Mapper - 내부 프로토콜 주소 매핑

<details>

<summary>정답 보기</summary>

**정답: A) IP Address Management - IP 주소 할당 및 관리**

**설명:** IPAM(IP Address Management)은 IP 주소의 계획, 할당, 추적 및 관리를 담당하는 시스템입니다. Cilium은 여러 IPAM 모드를 지원합니다: Cluster Pool(클러스터 전체 IP 풀 관리), Kubernetes(Kubernetes 노드 CIDR 사용), AWS ENI(AWS Elastic Network Interface 활용), Azure(Azure 네트워킹 통합), GKE(Google Kubernetes Engine 통합) 등이 있습니다. IPAM 모드 선택은 클러스터 환경과 네트워킹 요구 사항에 따라 달라집니다.

</details>

9. WireGuard의 주요 특징과 Cilium에서의 용도는 무엇인가요?
   * A) 패킷 캡처 도구 - 네트워크 분석
   * B) 현대적인 VPN 프로토콜 - 노드 간 트래픽 암호화
   * C) 로드 밸런싱 알고리즘 - 트래픽 분산
   * D) DNS 프록시 - 이름 해석

<details>

<summary>정답 보기</summary>

**정답: B) 현대적인 VPN 프로토콜 - 노드 간 트래픽 암호화**

**설명:** WireGuard는 현대적이고 빠르며 안전한 VPN(Virtual Private Network) 터널 프로토콜입니다. IPsec보다 더 간단하고 빠르며, 코드베이스가 작아 보안 감사가 용이합니다. Cilium에서 WireGuard는 노드 간 트래픽 암호화에 사용됩니다. WireGuard를 활성화하면 클러스터 내 모든 포드 간 트래픽이 투명하게 암호화됩니다. Cilium은 IPsec과 WireGuard 중 하나를 선택하여 암호화를 구현할 수 있습니다.

</details>

10. CNI의 정식 명칭과 역할은 무엇인가요?
    * A) Container Network Interface - 컨테이너 네트워크 플러그인 표준 인터페이스
    * B) Cloud Native Infrastructure - 클라우드 네이티브 인프라
    * C) Cluster Network Integration - 클러스터 네트워크 통합
    * D) Container Node Interconnect - 컨테이너 노드 연결

<details>

<summary>정답 보기</summary>

**정답: A) Container Network Interface - 컨테이너 네트워크 플러그인 표준 인터페이스**

**설명:** CNI(Container Network Interface)는 컨테이너 런타임과 네트워크 플러그인 간의 표준 인터페이스를 정의하는 CNCF 프로젝트입니다. Kubernetes에서 kubelet은 CNI 인터페이스를 통해 네트워크 플러그인(Cilium, Calico, Flannel 등)과 통신합니다. CNI는 컨테이너 추가/제거 시 네트워크 설정을 위한 표준 API를 정의하며, 플러그인 아키텍처를 통해 다양한 네트워킹 솔루션을 통합할 수 있습니다. Cilium은 CNI 구현체 중 하나입니다.

</details>

## 단답형 문제

11. Cilium에서 L7 프록시 및 서비스 메시 기능을 제공하는 오픈 소스 구성 요소의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Envoy

**설명:** Envoy는 L7 프록시 및 통신 버스로 사용되는 오픈 소스 엣지 및 서비스 프록시입니다. Cilium은 L7 네트워크 정책 구현을 위해 Envoy를 통합하고 있습니다. CiliumNetworkPolicy에 HTTP, gRPC, Kafka, DNS 등의 L7 규칙을 정의하면 Cilium은 자동으로 Envoy 프록시를 투명하게 배치합니다. Envoy는 고급 로드 밸런싱, 트래픽 분할, 메트릭 수집 등의 기능도 제공합니다.

</details>

12. 각 노드에서 실행되며 eBPF 프로그램 로딩, 네트워크 정책 구현, 엔드포인트 관리를 담당하는 Cilium 구성 요소의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Cilium Agent

**설명:** Cilium Agent는 각 Kubernetes 노드에서 DaemonSet으로 실행되는 Cilium의 핵심 구성 요소입니다. Agent의 주요 책임은 eBPF 프로그램을 커널에 로딩 및 관리, 네트워크 정책 구현 및 적용, 서비스 로드 밸런싱 수행, IP 주소 관리(IPAM), 네트워크 엔드포인트 관리, 메트릭 및 로그 수집, Kubernetes API 서버와의 통신 등입니다. 각 노드의 로컬 네트워킹 작업은 해당 노드의 Cilium Agent가 담당합니다.

</details>

13. OSI 모델에서 IP 주소를 사용하여 패킷 라우팅을 담당하는 계층의 이름과 번호는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** L3 (네트워크 계층, Network Layer)

**설명:** L3(네트워크 계층)은 OSI 모델의 3번째 계층으로, IP 주소를 사용한 논리적 주소 지정과 패킷 라우팅을 담당합니다. 이 계층에서 IP(Internet Protocol), ICMP(Internet Control Message Protocol) 등이 작동합니다. Cilium L3 정책에서는 IP 주소, CIDR 블록을 기반으로 트래픽을 필터링할 수 있습니다. L2(데이터 링크 계층)는 MAC 주소, L4(전송 계층)는 포트 번호를 사용합니다.

</details>

14. Kubernetes에서 포드 집합에 대한 안정적인 네트워크 엔드포인트를 제공하는 리소스의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Service

**설명:** Kubernetes Service는 포드 집합에 대한 안정적인 네트워크 엔드포인트(ClusterIP, DNS 이름)를 제공하는 추상화입니다. 포드는 동적으로 생성/삭제되어 IP가 변경될 수 있지만, Service는 고정된 IP와 DNS 이름을 제공하여 클라이언트가 일관되게 접근할 수 있게 합니다. Cilium은 Service에 대한 로드 밸런싱을 eBPF를 통해 구현하며, kube-proxy를 대체할 수 있습니다. Service 타입에는 ClusterIP, NodePort, LoadBalancer, ExternalName이 있습니다.

</details>

15. 패킷의 소스 IP 주소를 수정하는 NAT 유형의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** SNAT (Source NAT) 또는 Masquerading

**설명:** SNAT(Source Network Address Translation)는 패킷의 소스 IP 주소를 다른 IP 주소로 변환하는 NAT 유형입니다. Masquerading(마스커레이딩)은 SNAT의 특수한 형태로, 소스 IP를 아웃바운드 인터페이스의 IP로 자동 변환합니다. Cilium에서 마스커레이딩은 클러스터 내부 포드에서 외부로 나가는 트래픽의 소스 IP를 노드 IP로 변환하는 데 사용됩니다. 반대로 DNAT(Destination NAT)는 목적지 IP를 수정합니다.

</details>

## 실습 문제

16. 다음 Cilium 관련 용어들의 정의를 연결하세요: Cluster Mesh, CRD, FQDN, mTLS

<details>

<summary>정답 보기</summary>

**정답:**

* **Cluster Mesh**: Cilium의 멀티 클러스터 네트워킹 기능. 여러 Kubernetes 클러스터를 연결하여 클러스터 간 서비스 디스커버리, 로드 밸런싱, 네트워크 정책 적용을 가능하게 합니다.
* **CRD (Custom Resource Definition)**: Kubernetes API를 확장하여 사용자 정의 리소스를 정의하는 방법. Cilium은 CRD를 사용하여 CiliumNetworkPolicy, CiliumEndpoint 등을 정의합니다.
* **FQDN (Fully Qualified Domain Name)**: 호스트의 전체 도메인 이름 (예: www.example.com). Cilium FQDN 정책은 IP 대신 도메인 이름으로 외부 서비스에 대한 접근을 제어합니다.
* **mTLS (mutual TLS)**: 클라이언트와 서버 모두가 인증서로 서로를 인증하는 TLS의 확장. 양방향 인증을 통해 더 강력한 보안을 제공합니다.

**설명:** 이 용어들은 Cilium과 Kubernetes 네트워킹에서 자주 사용됩니다. Cluster Mesh는 하이브리드/멀티 클라우드 환경에서 유용하고, CRD는 Kubernetes 확장성의 핵심이며, FQDN 정책은 동적 IP를 가진 외부 서비스 접근 제어에 필수적이고, mTLS는 서비스 간 보안 통신에 중요합니다.

</details>

17. Cilium CLI를 사용하여 현재 클러스터의 모든 Identity와 해당 레이블을 조회하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```bash
# 모든 Identity 조회
cilium identity list

# 또는 kubectl을 사용하여 CiliumIdentity CRD 조회
kubectl get ciliumidentity -A

# 특정 Identity의 상세 정보 조회
cilium identity get <identity_id>

# JSON 형식으로 상세 정보 조회
kubectl get ciliumidentity <identity_id> -o json

# 특정 레이블을 가진 Identity 필터링
kubectl get ciliumidentity -o json | jq '.items[] | select(.metadata.labels."k8s:app" == "frontend")'

# Endpoint에서 Identity 확인
cilium endpoint list
kubectl exec -n kube-system ds/cilium -- cilium endpoint list
```

**설명:** Cilium Identity는 포드의 레이블 집합을 기반으로 생성되는 숫자 식별자입니다. `cilium identity list` 명령어는 현재 클러스터의 모든 Identity와 해당 레이블을 표시합니다. CiliumIdentity는 CRD로 저장되므로 kubectl로도 조회할 수 있습니다. Identity는 네트워크 정책의 기반이 되며, 동일한 레이블을 가진 모든 포드는 동일한 Identity를 공유합니다.

</details>

18. BPF Map의 내용을 조회하여 서비스 로드 밸런싱 맵과 연결 추적 테이블을 확인하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```bash
# Cilium Agent 포드에서 BPF 맵 조회

# 서비스 맵 (Service -> Backend 매핑)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list

# 백엔드 맵 (백엔드 포드 정보)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list --backends

# 연결 추적 테이블 (Connection Tracking)
kubectl exec -n kube-system ds/cilium -- cilium bpf ct list global

# NAT 맵 (마스커레이딩/SNAT 정보)
kubectl exec -n kube-system ds/cilium -- cilium bpf nat list

# 정책 맵 (Identity 기반 정책)
kubectl exec -n kube-system ds/cilium -- cilium bpf policy get --all

# Endpoint 맵
kubectl exec -n kube-system ds/cilium -- cilium bpf endpoint list

# 모든 BPF 맵 목록
kubectl exec -n kube-system ds/cilium -- cilium bpf map list
```

**설명:** BPF Map은 Cilium의 데이터 플레인에서 사용하는 핵심 데이터 구조입니다. `cilium bpf lb list`는 서비스 로드 밸런싱 정보를 보여주며, 서비스 IP/포트와 백엔드 포드 IP/포트의 매핑을 확인할 수 있습니다. `cilium bpf ct list`는 연결 추적 테이블을 보여주며, 현재 활성 연결 상태를 확인할 수 있습니다. 이러한 명령어들은 네트워크 문제 해결과 성능 분석에 유용합니다.

</details>

19. FQDN 기반 네트워크 정책을 사용하여 포드가 `api.example.com`과 `*.googleapis.com` 도메인으로만 외부 통신을 허용하는 CiliumNetworkPolicy를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "fqdn-egress-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  # DNS 쿼리 허용 (FQDN 정책 작동에 필수)
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        - matchPattern: "*"
  # 특정 FQDN으로의 HTTPS 트래픽 허용
  - toFQDNs:
    - matchName: "api.example.com"
    - matchPattern: "*.googleapis.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**설명:** FQDN(Fully Qualified Domain Name) 기반 정책은 IP 주소 대신 도메인 이름으로 외부 서비스에 대한 접근을 제어합니다. 이 정책이 작동하려면 DNS 쿼리를 허용해야 합니다(첫 번째 egress 규칙). `toFQDNs`에서 `matchName`은 정확한 도메인 이름을, `matchPattern`은 와일드카드를 사용한 패턴 매칭을 지정합니다. `*.googleapis.com`은 모든 Google API 서브도메인을 허용합니다. FQDN 정책은 동적 IP를 가진 외부 서비스 접근 제어에 특히 유용합니다.

</details>

20. Cilium Operator의 역할과 Cilium Agent와의 차이점을 설명하고, Operator의 상태를 확인하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```bash
# Cilium Operator 상태 확인
kubectl -n kube-system get deployment cilium-operator

# Operator 포드 상태 확인
kubectl -n kube-system get pods -l name=cilium-operator

# Operator 로그 확인
kubectl -n kube-system logs -l name=cilium-operator

# 전체 Cilium 상태에서 Operator 확인
cilium status --verbose

# CiliumIdentity 리소스 확인 (Operator가 관리)
kubectl get ciliumidentity -A

# CiliumEndpoint 리소스 확인
kubectl get ciliumendpoint -A
```

**Cilium Operator vs Cilium Agent 역할 비교:**

| 구성 요소               | 실행 위치                   | 주요 역할                                                                                                         |
| ------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Cilium Agent**    | 각 노드 (DaemonSet)        | <p>- eBPF 프로그램 로딩/관리<br>- 네트워크 정책 적용<br>- 로컬 엔드포인트 관리<br>- 서비스 로드 밸런싱<br>- 노드 수준 IPAM</p>                     |
| **Cilium Operator** | 클러스터 (Deployment, 1-2개) | <p>- CiliumIdentity CRD 관리<br>- 클러스터 수준 IPAM<br>- CiliumEndpoint 동기화<br>- 가비지 컬렉션<br>- Cluster Mesh 연결 관리</p> |

**설명:** Cilium Agent는 각 노드에서 실행되며 해당 노드의 네트워킹 작업을 담당합니다. 반면 Cilium Operator는 클러스터 전체에서 단일(또는 HA를 위해 2개) 인스턴스로 실행되며 클러스터 수준의 조정 작업을 담당합니다. Operator는 클러스터 전체에서 Identity의 일관성을 유지하고, 사용되지 않는 리소스를 정리하며, 클러스터 수준 IPAM을 관리합니다.

</details>

***

[학습 자료로 돌아가기](../../../networking/cilium/glossary.md) | [Cilium 퀴즈 목록](https://github.com/Atom-oh/kubernetes-docs/blob/main/ko/quizzes/networking/cilium/README.md)
