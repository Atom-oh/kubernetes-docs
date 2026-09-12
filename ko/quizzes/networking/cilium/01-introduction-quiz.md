# Cilium 소개 및 기본 개념 퀴즈

> **기준**: Cilium 1.20.1 / CLI 0.20.0. **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

1. Cilium의 프로그래밍 가능한 커널 데이터패스를 제공하는 기술은?
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>
<summary>정답 보기</summary>

**정답: B) eBPF**

**설명:**
Cilium은 지원 kernel hook에 검증된 eBPF 프로그램을 로드합니다. 네트워킹/관측성 기능을 구현하지만 모든 대안보다 높은 성능을 보장하지는 않으므로 선택한 워크로드와 설정을 측정해야 합니다.

</details>

2. 필요한 통합을 갖춘 Cilium이 지원할 수 있는 정책 계층은?
   - A) L3만
   - B) L3–L4만
   - C) L3/L4 및 지원되는 L7 프로토콜
   - D) L2–L3만

<details>
<summary>정답 보기</summary>

**정답: C) L3/L4 및 지원되는 L7 프로토콜**

**설명:**
HTTP/DNS 정책에는 지원 proxy 경로가 필요하고 암호화된 HTTP에는 알맞은 termination/통합이 필요합니다. Kafka 인지 L7 규칙은 1.20에서 제거되었지만 Kafka 연결의 L4 제어는 가능합니다.

</details>

3. Cilium에서 네트워크 flow 가시성을 제공하는 컴포넌트는?
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>
<summary>정답 보기</summary>

**정답: B) Hubble**

**설명:**
Hubble은 네트워크/proxy flow와 서비스 관계를 관측합니다. HTTP 가시성은 proxy 경로에 달려 있습니다. 완전한 애플리케이션 trace가 자동 생성되지는 않으며 Prometheus 메트릭과 분산 tracing은 별도 목적입니다.

</details>

4. 지원 구성에서 Cilium이 대체할 수 있는 Kubernetes Service 컴포넌트는?
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>
<summary>정답 보기</summary>

**정답: B) kube-proxy**

**설명:**
kubeProxyReplacement는 Cilium Service 처리를 요청합니다. API/bootstrap 접근과 전환 전제가 필요하며 DSR/Maglev/XDP는 자동 성능 보장이 아닌 별도 선택입니다.

</details>

5. Cilium의 투명 네트워크 암호화 모드 두 가지는?
   - A) IPsec과 WireGuard
   - B) TLS와 SSH
   - C) GRE와 HTTP
   - D) DNS와 VXLAN

<details>
<summary>정답 보기</summary>

**정답: A) IPsec과 WireGuard**

**설명:**
encryption.type은 모드/플랫폼 조건을 가진 IPsec과 WireGuard를 사용합니다. 별도의 beta ztunnel 워크로드 mTLS는 다른 설정이므로 Cilium이 TLS를 전혀 사용하지 않는다는 설명은 틀립니다.

</details>

6. Cilium의 멀티클러스터 연결 기능 이름은?
   - A) Cluster Federation
   - B) ClusterMesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>
<summary>정답 보기</summary>

**정답: B) ClusterMesh**

**설명:**
ClusterMesh는 identity, 신뢰, 네트워크 도달성을 설정한 호환 클러스터를 연결합니다. Underlay 전체를 만들거나 모든 Service를 자동으로 전역 공개하지는 않습니다.

</details>

7. Cilium이 선택적 초기 패킷/로드밸런싱 가속에 사용할 수 있는 기술은?
   - A) DPDK
   - B) XDP
   - C) RDMA
   - D) SR-IOV

<details>
<summary>정답 보기</summary>

**정답: B) XDP**

**설명:**
XDP는 지원 hook/driver에서 일부 트래픽을 일찍 처리할 수 있습니다. 모든 패킷이 XDP를 거치지는 않으며 활성화만으로 초당 패킷 수나 완전한 DDoS 방어가 보장되지 않습니다.

</details>

8. 문서화된 vendor backport 동등 조건을 제외한 Cilium 1.20의 일반 업스트림 Linux 커널 기준은?
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>
<summary>정답 보기</summary>

**정답: D) 5.10**

**설명:**
현재 요구사항은 Linux 5.10 이상이며 RHEL 8.10의 backport된 4.18 같은 명시적 동등 조건이 있습니다. 개별 기능에는 더 최신 커널이 필요할 수 있고 워크스테이션 OS가 아닌 노드/VM 커널을 확인해야 합니다.

</details>

9. Cilium의 eBPF 데이터플레인 없이 VXLAN/host-gw 연결을 제공하는 선택지는?
   - A) Cilium native routing
   - B) Calico BPF 모드
   - C) Flannel VXLAN/host-gw
   - D) Cilium netkit 모드

<details>
<summary>정답 보기</summary>

**정답: C) Flannel VXLAN/host-gw**

**설명:**
Flannel 연결 backend는 다른 구현입니다. 선택적 정책 컨트롤러나 다른 정책 통합은 별도 평가해야 하며 보편적인 자원/성능 등급으로 비교하지 마세요.

</details>

10. CiliumNetworkPolicy의 API 버전은?
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

<details>
<summary>정답 보기</summary>

**정답: C) cilium.io/v2**

**설명:**
표준 Kubernetes NetworkPolicy와 별도 CRD/API입니다. 실제 기능은 Cilium 버전과 dataplane/proxy 구성에 따라 달라집니다.

</details>

## 단답형 문제

11. 노드별 endpoint와 eBPF 정책을 설정하는 컴포넌트는?

<details>
<summary>정답 보기</summary>

**정답: Cilium Agent**

**설명:**
Agent는 노드 로컬 작업을 수행합니다. 컨테이너 런타임/CNI 플러그인, operator, proxy, 호스트 OS도 각 책임이 있으므로 모든 네트워킹 작업을 Agent가 소유하지는 않습니다.

</details>

12. 클러스터 수준 할당/controller 작업을 조정하는 컴포넌트는?

<details>
<summary>정답 보기</summary>

**정답: Cilium Operator**

**설명:**
여러 replica를 사용할 수 있으며 검토한 차트 기본값은 2이고 해당 작업에는 leader election을 사용합니다. 책임은 IPAM/identity 모드에 따라 다릅니다. 본질적으로 단일 인스턴스나 모든 ClusterMesh 연결의 유일한 소유자가 아닙니다.

</details>

13. Cilium connectivity 테스트 워크로드를 실행하는 CLI 명령은?

<details>
<summary>정답 보기</summary>

**정답: cilium connectivity test**

**설명:**
워크로드/정책을 생성하므로 승인한 테스트 환경과 권한이 필요합니다. 읽기 전용 조사는 cilium status, endpoint 진단, Hubble부터 시작하세요. 관리 명령 cilium monitor는 현재 Agent 진단 인터페이스가 아닙니다.

</details>

14. Endpoint의 보안 관련 레이블에 대응하는 숫자 식별자는?

<details>
<summary>정답 보기</summary>

**정답: Security identity (Cilium identity)**

**설명:**
해당 할당 범위의 선택된 보안 레이블 집합이 identity를 결정합니다. Namespace 파생 레이블도 다를 수 있으므로 같은 app 값만으로 같다고 판단할 수 없습니다. 숫자 ID는 할당되며 영구적인 전역 hash가 아닙니다.

</details>

15. 컨테이너 네트워크 플러그인 인터페이스를 정의하는 규격은?

<details>
<summary>정답 보기</summary>

**정답: CNI (Container Network Interface)**

**설명:**
Kubelet은 CRI로 런타임과 통신하고 런타임이 CNI를 호출합니다. CNI는 네트워크 설정/결과와 설정/제거를 다루며 kubelet의 이전 CNI 설정 플래그는 Kubernetes 1.24에서 제거되었습니다.

</details>

## 실습 문제

16. 설치한 CLI, 준비한 lab values, 명시적인 context로 Cilium 1.20.1을 새로 설치하는 명령을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium version --client
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.1 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

**설명:**
본문의 환경/CNI 소유권, CIDR, values 전제를 준비해야 합니다. 기존 release라면 설치를 건너뛰고 소유자의 업그레이드 경로를 사용하세요. Status가 허용/거부 트래픽 테스트를 대신하지는 않습니다.

</details>

17. cilium-intro-demo에서 frontend Pod의 backend TCP 8080 ingress를 허용하는 정책을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**

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

**설명:**
네임스페이스와 워크로드가 있어야 합니다. 출발 namespace를 명시하여 다른 namespace의 같은 레이블까지 허용하지 않습니다. 다른 allow/deny 정책과 host 트래픽이 결과를 바꾸며 HTTP 필터링이나 egress 제한 규칙은 아닙니다.

</details>

18. kube-proxy 교체와 native-routing DSR/Geneve dispatch를 요청하는 부분 values를 작성하고 남은 전제를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
kubeProxyReplacement: true
k8sServiceHost: api.lab.example.internal
k8sServicePort: 443
routingMode: native
tunnelProtocol: geneve
ipv4NativeRoutingCIDR: 10.244.0.0/16
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

**설명:**
별도 native 구성이며 VXLAN 실습에 DSR을 켜라는 명령이 아닙니다. API host/port, native-routing CIDR을 실제 준비한 값으로 변경하세요. API/bootstrap DNS, underlay Pod 경로, Geneve/MTU, 반환/출발지 주소 경로를 확인한 후 지원되는 kube-proxy 전환 절차를 따릅니다. 정적 values가 클라우드 LB 호환성이나 모든 병목 제거를 보장하지는 않습니다.

</details>

19. 클러스터 상태, 선택한 backend endpoint의 로컬 상태, 원하는 정책 리소스를 조회하는 명령을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
CILIUM_LAB_NS=cilium-intro-demo
BACKEND_POD=replace-with-actual-backend-pod
cilium status --context "$CILIUM_LAB_CONTEXT" --verbose
kubectl --context "$CILIUM_LAB_CONTEXT" get pod "$BACKEND_POD" -n "$CILIUM_LAB_NS" -o wide
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent on the backend Pod's node.
CILIUM_AGENT_POD=replace-with-agent-pod-on-that-node
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint list
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint get "pod-name:$CILIUM_LAB_NS:$BACKEND_POD"
kubectl --context "$CILIUM_LAB_CONTEXT" get networkpolicy -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get ccnp -o yaml
```

**설명:**
Endpoint 식별자와 realized 상태는 선택한 agent/노드에 속합니다. cilium-dbg가 지원하는 Pod 식별자를 사용하세요. kubectl은 desired 정책 리소스를 읽으며 적용 성공의 증거가 아닙니다. cilium-dbg policy get은 deprecated이고 관리 cilium endpoint/policy/monitor 명령과 동일하지 않습니다.

</details>

20. 클라이언트 도구가 있는 상태에서 기존 lab release의 Hubble을 활성화하고 flow를 관찰하세요.

<details>
<summary>정답 보기</summary>

**정답:**

```bash
# Terminal 1; the lab Cilium release and client tools must already exist.
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium hubble enable --context "$CILIUM_LAB_CONTEXT" --ui
cilium hubble port-forward --context "$CILIUM_LAB_CONTEXT" --port-forward 4245
```

```bash
# Terminal 2, with the port-forward still running.
BACKEND_POD=replace-with-actual-backend-pod
hubble observe --server 127.0.0.1:4245 --namespace cilium-intro-demo
hubble observe --server 127.0.0.1:4245 --pod "cilium-intro-demo/$BACKEND_POD"
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
```

**설명:**
GitOps 소유 release라면 CLI 변경 대신 소유 Helm values를 바꾸고 이미 활성화되어 있으면 enable을 건너뜁니다. Foreground port-forward를 유지하고 TLS Relay에는 client TLS를 설정해야 합니다. HTTP event는 지원 L7 proxy 경로가 필요하며 DROPPED가 모든 애플리케이션 실패를 뜻하지는 않습니다. UI는 별도 터미널에서 같은 명시적 context로 cilium hubble ui를 사용하세요.

</details>

[학습 자료로 돌아가기](../../../networking/cilium/01-introduction.md) | [다음 퀴즈: eBPF 기초](02-ebpf-quiz.md)
