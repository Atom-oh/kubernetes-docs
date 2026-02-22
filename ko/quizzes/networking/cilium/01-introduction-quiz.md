# Cilium 소개 및 기본 개념 퀴즈

이 퀴즈는 Cilium의 기본 개념, eBPF 기술, 아키텍처, 주요 구성 요소, CNI 비교 등에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Cilium의 핵심 기술로, 커널 내에서 프로그래밍 가능한 데이터 경로를 제공하는 것은 무엇인가요?
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>

<summary>정답 보기</summary>

**정답: B) eBPF**

**설명:**
eBPF(extended Berkeley Packet Filter)는 Linux 커널 내에서 안전하게 프로그램을 실행할 수 있는 기술입니다. Cilium은 eBPF를 활용하여 커널 수준에서 네트워킹, 보안, 관찰 가능성 기능을 구현합니다. 이를 통해 iptables 기반 솔루션보다 훨씬 높은 성능과 유연성을 제공하며, 커널을 재컴파일하지 않고도 동적으로 네트워크 정책을 적용할 수 있습니다.
</details>

2. Cilium이 제공하는 네트워크 정책은 어떤 계층까지 지원하나요?
   - A) L3 (네트워크 계층)만
   - B) L3-L4 (네트워크 및 전송 계층)
   - C) L3-L7 (네트워크부터 애플리케이션 계층)
   - D) L2-L3 (데이터 링크 및 네트워크 계층)

<details>

<summary>정답 보기</summary>

**정답: C) L3-L7 (네트워크부터 애플리케이션 계층)**

**설명:**
Cilium은 L3(IP), L4(TCP/UDP 포트)뿐만 아니라 L7(애플리케이션 계층)까지 네트워크 정책을 지원합니다. 이는 HTTP 메서드, 경로, 헤더, gRPC 메서드, Kafka 주제 등 애플리케이션 수준의 트래픽을 필터링할 수 있음을 의미합니다. 이러한 API 인식 네트워킹은 마이크로서비스 아키텍처에서 세밀한 보안 정책을 구현하는 데 매우 유용합니다.
</details>

3. Cilium에서 네트워크 가시성과 모니터링을 제공하는 도구는 무엇인가요?
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>

<summary>정답 보기</summary>

**정답: B) Hubble**

**설명:**
Hubble은 Cilium의 네트워크 관찰성 계층으로, eBPF를 활용하여 네트워크 흐름을 실시간으로 모니터링하고 분석합니다. Hubble은 서비스 간 의존성 맵 생성, 네트워크 정책 위반 감지, HTTP/gRPC/DNS 요청 추적, 네트워크 레이턴시 측정 등의 기능을 제공합니다. Prometheus와 Grafana는 메트릭 수집 및 시각화 도구이고, Jaeger는 분산 추적 도구입니다.
</details>

4. Cilium의 분산 로드 밸런싱 기능은 어떤 Kubernetes 구성 요소를 대체할 수 있나요?
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>

<summary>정답 보기</summary>

**정답: B) kube-proxy**

**설명:**
Cilium은 kube-proxy를 완전히 대체할 수 있는 eBPF 기반 서비스 로드 밸런싱을 제공합니다. kube-proxy는 iptables나 IPVS를 사용하여 서비스 트래픽을 백엔드 포드로 라우팅하지만, Cilium은 eBPF를 사용하여 더 높은 성능과 확장성을 제공합니다. Cilium의 kube-proxy 대체 모드를 활성화하면 DSR(Direct Server Return), Maglev 해싱, 소켓 수준 로드 밸런싱 등의 고급 기능도 사용할 수 있습니다.
</details>

5. Cilium에서 지원하는 노드 간 트래픽 암호화 방식이 아닌 것은 무엇인가요?
   - A) IPsec
   - B) WireGuard
   - C) TLS
   - D) 둘 다 지원 (A와 B)

<details>

<summary>정답 보기</summary>

**정답: C) TLS**

**설명:**
Cilium은 노드 간 트래픽 암호화를 위해 IPsec과 WireGuard 두 가지 방식을 지원합니다. IPsec은 전통적인 VPN 프로토콜 스위트로 널리 사용되며, WireGuard는 더 현대적이고 간단하며 빠른 VPN 프로토콜입니다. TLS는 애플리케이션 계층의 암호화 프로토콜로, Cilium의 네트워크 계층 암호화와는 다른 용도로 사용됩니다. Cilium에서는 설정 옵션을 통해 IPsec 또는 WireGuard 중 하나를 선택하여 투명한 네트워크 암호화를 구현할 수 있습니다.
</details>

6. Cilium의 멀티 클러스터 네트워킹 기능을 무엇이라고 부르나요?
   - A) Cluster Federation
   - B) Cluster Mesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>

<summary>정답 보기</summary>

**정답: B) Cluster Mesh**

**설명:**
Cluster Mesh는 Cilium의 멀티 클러스터 네트워킹 기능으로, 여러 Kubernetes 클러스터를 연결하여 단일 네트워크처럼 작동하게 합니다. Cluster Mesh를 사용하면 클러스터 간 서비스 디스커버리, 로드 밸런싱, 네트워크 정책 적용이 가능합니다. 이 기능은 하이브리드 클라우드, 멀티 클라우드, 재해 복구 시나리오에서 유용하며, 각 클러스터의 포드가 다른 클러스터의 서비스에 직접 접근할 수 있게 해줍니다.
</details>

7. 다음 중 Cilium에서 패킷 처리 성능을 최적화하기 위해 사용하는 기술은 무엇인가요?
   - A) DPDK
   - B) XDP (eXpress Data Path)
   - C) RDMA
   - D) SR-IOV

<details>

<summary>정답 보기</summary>

**정답: B) XDP (eXpress Data Path)**

**설명:**
XDP(eXpress Data Path)는 eBPF 기반 기술로, 네트워크 드라이버 수준에서 패킷을 처리할 수 있게 해줍니다. XDP는 커널 네트워크 스택을 바이패스하여 매우 높은 성능(초당 수백만 패킷)의 패킷 처리를 가능하게 합니다. Cilium은 XDP를 활용하여 DDoS 방어, 고성능 로드 밸런싱, 패킷 필터링 등을 구현합니다. DPDK, RDMA, SR-IOV도 고성능 네트워킹 기술이지만, Cilium의 핵심 기술은 eBPF/XDP입니다.
</details>

8. Cilium 1.18 버전에서 지원하는 최소 Linux 커널 버전은 무엇인가요?
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>

<summary>정답 보기</summary>

**정답: C) 4.19**

**설명:**
Cilium 1.18은 Linux 커널 4.19 이상을 필요로 합니다. 이는 Cilium이 사용하는 eBPF 기능들이 이 버전 이상에서 완전히 지원되기 때문입니다. 더 최신 커널 버전(5.x 이상)을 사용하면 추가적인 eBPF 기능과 더 나은 성능을 얻을 수 있습니다. 예를 들어, XDP 네이티브 모드, BPF-to-BPF 함수 호출, BTF(BPF Type Format) 등의 고급 기능은 더 최신 커널에서 더 잘 지원됩니다.
</details>

9. 다음 CNI 플러그인 중 eBPF 기반이 아닌 것은 무엇인가요?
   - A) Cilium
   - B) Calico (eBPF 모드)
   - C) Flannel
   - D) 둘 다 eBPF 기반이 아님 (C만 해당)

<details>

<summary>정답 보기</summary>

**정답: C) Flannel**

**설명:**
Flannel은 VXLAN이나 host-gw를 사용하는 간단한 오버레이 네트워크 솔루션으로, eBPF를 사용하지 않습니다. 반면 Cilium은 처음부터 eBPF 기반으로 설계되었고, Calico도 최근 버전에서 eBPF 데이터 플레인 모드를 지원합니다. Flannel은 설정이 간단하고 리소스 사용량이 적지만, L7 네트워크 정책이나 고급 관찰성 기능은 제공하지 않습니다.
</details>

10. Cilium 네트워크 정책의 API 버전은 무엇인가요?
    - A) networking.k8s.io/v1
    - B) cilium.io/v1
    - C) cilium.io/v2
    - D) policy.cilium.io/v1

<details>

<summary>정답 보기</summary>

**정답: C) cilium.io/v2**

**설명:**
CiliumNetworkPolicy는 `cilium.io/v2` API 버전을 사용합니다. 이는 표준 Kubernetes NetworkPolicy(`networking.k8s.io/v1`)와 별개로, Cilium의 고급 기능(L7 정책, DNS 기반 정책, 엔드포인트 셀렉터 등)을 지원하기 위한 CRD(Custom Resource Definition)입니다. Cilium은 표준 Kubernetes NetworkPolicy도 지원하지만, CiliumNetworkPolicy를 사용하면 더 세밀한 제어가 가능합니다.
</details>

## 단답형 문제

11. Cilium의 각 노드에서 실행되며 eBPF 프로그램을 로딩하고 네트워크 정책을 구현하는 핵심 구성 요소의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Cilium Agent**

**설명:**
Cilium Agent는 각 Kubernetes 노드에서 DaemonSet으로 실행되는 Cilium의 핵심 구성 요소입니다. Agent의 주요 책임은 eBPF 프로그램을 커널에 로딩 및 관리, 네트워크 정책 구현 및 적용, 서비스 로드 밸런싱 수행, IP 주소 관리(IPAM), 네트워크 엔드포인트 관리, 메트릭 및 로그 수집, API 서버와의 통신 등입니다. Cilium Agent는 로컬 노드의 모든 네트워킹 작업을 담당합니다.
</details>

12. Cilium에서 클러스터 전체에서 실행되며 CRD 동기화, IP 할당 조정 등의 작업을 수행하는 구성 요소는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Cilium Operator**

**설명:**
Cilium Operator는 클러스터 전체에서 단일 인스턴스로 실행되는 Kubernetes Operator입니다. Agent가 각 노드의 로컬 작업을 담당하는 반면, Operator는 클러스터 전체 수준의 작업을 담당합니다. 주요 기능으로는 CiliumIdentity 및 CiliumEndpoint CRD 관리, 클러스터 수준 IPAM 관리, 노드 간 CIDR 할당 조정, 가비지 컬렉션(사용되지 않는 리소스 정리), Cluster Mesh 연결 관리 등이 있습니다.
</details>

13. Cilium의 연결성 문제를 진단하기 위해 사용하는 CLI 명령어는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: cilium connectivity test**

**설명:**
`cilium connectivity test` 명령어는 Cilium 클러스터의 네트워크 연결성을 종합적으로 테스트합니다. 이 명령어는 포드 간 통신, 서비스 연결, 외부 연결, 네트워크 정책 적용 등 다양한 시나리오를 자동으로 테스트합니다. 테스트 결과는 성공/실패로 표시되며, 실패한 테스트에 대한 상세 정보를 제공합니다. 이 외에도 `cilium status`로 Cilium 상태를 확인하고, `cilium monitor`로 실시간 트래픽을 모니터링할 수 있습니다.
</details>

14. Cilium에서 포드의 보안 신원을 나타내는 숫자 식별자를 무엇이라고 부르나요?

<details>

<summary>정답 보기</summary>

**정답: Identity (또는 Security Identity, Cilium Identity)**

**설명:**
Cilium Identity는 포드의 레이블 집합을 기반으로 생성되는 숫자 식별자입니다. 동일한 레이블을 가진 모든 포드는 동일한 Identity를 공유합니다. 이 접근 방식은 IP 주소 대신 Identity를 사용하여 네트워크 정책을 적용할 수 있게 해주어, 포드 IP가 변경되어도 정책이 일관되게 유지됩니다. Identity 기반 정책은 확장성이 뛰어나며, 대규모 클러스터에서도 효율적으로 동작합니다.
</details>

15. 컨테이너 런타임과 네트워크 플러그인 간의 표준 인터페이스를 정의하는 CNCF 프로젝트의 약자는 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: CNI (Container Network Interface)**

**설명:**
CNI(Container Network Interface)는 컨테이너 런타임과 네트워크 플러그인 간의 표준 인터페이스를 정의하는 CNCF 프로젝트입니다. Kubernetes에서 kubelet은 CNI 인터페이스를 통해 네트워크 플러그인(Cilium, Calico, Flannel 등)과 통신합니다. CNI는 컨테이너 추가/제거 시 네트워크 설정을 위한 표준 API를 정의하며, 플러그인 아키텍처를 통해 다양한 네트워킹 솔루션을 통합할 수 있습니다.
</details>

## 실습 문제

16. Cilium CLI를 사용하여 Kubernetes 클러스터에 Cilium 1.18.0을 설치하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# Cilium CLI 설치
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Cilium 설치
cilium install --version 1.18.0

# 설치 상태 확인
cilium status

# 연결성 테스트
cilium connectivity test
```

**설명:**
위 명령어는 먼저 Cilium CLI 바이너리를 다운로드하여 `/usr/local/bin`에 설치합니다. 그 후 `cilium install` 명령어로 지정된 버전의 Cilium을 Kubernetes 클러스터에 설치합니다. 설치 후 `cilium status`로 모든 구성 요소가 정상적으로 실행 중인지 확인하고, `cilium connectivity test`로 네트워크 연결성을 검증합니다. Helm을 사용한 설치도 가능하며, 이 경우 더 세밀한 설정 옵션을 지정할 수 있습니다.
</details>

17. frontend 포드에서 backend 포드의 8080 포트로의 TCP 트래픽만 허용하는 CiliumNetworkPolicy를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

**설명:**
이 CiliumNetworkPolicy는 `app: backend` 레이블을 가진 포드에 대해, `app: frontend` 레이블을 가진 포드로부터의 TCP 8080 포트 인그레스 트래픽만 허용합니다. `endpointSelector`는 정책이 적용될 대상 포드를 선택하고, `ingress` 섹션은 허용될 수신 트래픽을 정의합니다. `fromEndpoints`로 소스 포드를 지정하고, `toPorts`로 허용될 포트와 프로토콜을 지정합니다. 이 정책이 적용되면 다른 포드에서 backend로의 트래픽은 차단됩니다.
</details>

18. kube-proxy 대체 모드를 활성화하여 Cilium을 설치하는 명령어와 DSR(Direct Server Return) 모드를 활성화하는 설정을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# kube-proxy 대체 및 DSR 모드로 Cilium 설치
cilium install --version 1.18.0 \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr

# 또는 Helm을 사용한 설치
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=<API_SERVER_PORT>

# 설치 확인
cilium status --verbose
```

**설명:**
`kubeProxyReplacement=true` 옵션은 Cilium이 kube-proxy의 모든 기능을 대체하도록 설정합니다. 이 모드에서는 기존 kube-proxy를 제거하거나 비활성화해야 합니다. `loadBalancer.mode=dsr`은 Direct Server Return 모드를 활성화하여, 응답 트래픽이 로드 밸런서를 거치지 않고 직접 클라이언트로 전송되도록 합니다. DSR 모드는 로드 밸런서의 병목 현상을 제거하고 대역폭을 절약하며, 특히 대용량 응답을 처리할 때 효과적입니다.
</details>

19. Cilium의 상태를 확인하고, 특정 포드의 엔드포인트 정보와 적용된 네트워크 정책을 조회하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# Cilium 전체 상태 확인
cilium status

# 상세 상태 확인 (모든 구성 요소)
cilium status --verbose

# 모든 엔드포인트 목록 조회
cilium endpoint list

# 특정 엔드포인트의 상세 정보 조회 (endpoint ID 사용)
cilium endpoint get <endpoint_id>

# 포드 이름으로 엔드포인트 조회
kubectl exec -n kube-system <cilium-agent-pod> -- cilium endpoint list | grep <pod-name>

# 적용된 네트워크 정책 조회
cilium policy get

# 특정 엔드포인트에 적용된 정책 조회
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# 실시간 트래픽 모니터링
cilium monitor
```

**설명:**
`cilium status`는 Cilium Agent, Operator, Hubble 등 모든 구성 요소의 상태를 보여줍니다. `cilium endpoint list`는 현재 노드의 모든 엔드포인트(포드)를 나열하며, 각 엔드포인트의 ID, 상태, 레이블, Identity 등을 확인할 수 있습니다. `cilium policy get`은 클러스터에 적용된 모든 네트워크 정책을 조회합니다. `cilium monitor`는 실시간으로 네트워크 트래픽을 모니터링하여 패킷 흐름, 정책 적용, 드롭된 패킷 등을 확인할 수 있습니다.
</details>

20. Hubble을 활성화하고 Hubble CLI를 사용하여 네트워크 흐름을 관찰하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# Hubble이 활성화된 Cilium 설치
cilium install --version 1.18.0 \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# 기존 Cilium에서 Hubble 활성화
cilium hubble enable

# Hubble CLI 설치
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Hubble 포트 포워딩
cilium hubble port-forward &

# 네트워크 흐름 관찰
hubble observe

# 특정 네임스페이스의 흐름 관찰
hubble observe --namespace default

# 특정 포드의 흐름 관찰
hubble observe --pod default/frontend

# HTTP 트래픽만 필터링
hubble observe --protocol http

# 드롭된 패킷만 관찰
hubble observe --verdict DROPPED

# Hubble UI 접근 (별도 터미널)
cilium hubble ui
```

**설명:**
Hubble은 Cilium의 관찰성 계층으로, eBPF를 활용하여 네트워크 흐름을 실시간으로 모니터링합니다. `hubble.enabled=true`로 Hubble을 활성화하고, `hubble.relay.enabled=true`로 Hubble Relay를 활성화하여 클러스터 전체의 흐름을 수집합니다. `hubble.ui.enabled=true`는 웹 기반 UI를 활성화합니다. `hubble observe` 명령어는 다양한 필터 옵션을 제공하여 특정 네임스페이스, 포드, 프로토콜, 판정(verdict) 등을 기준으로 트래픽을 필터링할 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../networking/cilium/01-introduction.md) | [다음 퀴즈: eBPF 기초](./02-ebpf-quiz.md)
