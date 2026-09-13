# 용어집 퀴즈

> **검토 기준**: Cilium 1.20.1.
> **최종 검토**: 2026년 9월 12일.

이 퀴즈는 Cilium, eBPF, Kubernetes, 네트워킹과 관련된 주요 용어 및 개념에 대한 이해도를 테스트합니다.

## 객관식 문제

1. eBPF의 정식 명칭은 무엇인가요?

   - A) Enhanced Berkeley Packet Filter
   - B) Extended Berkeley Packet Filter
   - C) Embedded BPF Filter
   - D) External Berkeley Protocol Filter

<details>

<summary>정답 보기</summary>

**정답: B) Extended Berkeley Packet Filter**

**설명:** eBPF는 classic BPF를 확장하며 네트워킹·추적 등의 커널 훅에 사용됩니다. 검증기는 프로그램 속성을 검사하지만 커널·검증기의 구현 오류가 없음을 보장하지는 않습니다.

</details>

2. Cilium에서 네트워크 정책이 적용되는 기본 단위를 무엇이라고 부르나요?

   - A) Pod
   - B) Node
   - C) Endpoint
   - D) Service

<details>

<summary>정답 보기</summary>

**정답: C) Endpoint**

**설명:** Cilium 엔드포인트는 보통 관리 대상 Pod에 해당합니다. 엔드포인트 ID는 에이전트에 로컬이며 보안 ID는 공유할 수 있습니다. 담당 에이전트 안에서 `cilium-dbg endpoint list`를 사용합니다.

</details>

3. 지원 네트워크 장치에서 native XDP는 어느 위치에서 실행되나요?

   - A) L7 프로토콜 분석
   - B) 네트워크 드라이버 수준에서 패킷 처리
   - C) TLS 암호화
   - D) DNS 해석

<details>

<summary>정답 보기</summary>

**정답: B) 네트워크 드라이버 수준에서 패킷 처리**

**설명:** Native XDP는 지원 드라이버의 수신 경로에서 실행됩니다. PASS는 스택으로 계속 전달하고 DROP·TX·REDIRECT는 다른 동작을 수행합니다. Generic·offload 모드는 다릅니다. Cilium 서비스 가속은 조건부 기능이며 보편적인 패킷 처리율이나 내장 DDoS 방어를 보장하지 않습니다.

</details>

4. Cilium의 네트워크 관찰성 플랫폼의 이름은 무엇인가요?

   - A) Prometheus
   - B) Grafana
   - C) Hubble
   - D) Jaeger

<details>

<summary>정답 보기</summary>

**정답: C) Hubble**

**설명:** Hubble은 CLI·UI와 구성된 연동을 통해 흐름 기록, 판정과 지원 프로토콜 메트릭을 제공합니다. Relay는 영구 저장소가 아니며 외부 알림·보존은 별도 구성해야 하고 이벤트가 손실될 수 있습니다.

</details>

5. VXLAN의 정식 명칭과 주요 용도는 무엇인가요?

   - A) Virtual Extended LAN - 가상 네트워크 생성
   - B) Virtual Extensible LAN - L2 오버레이 네트워크
   - C) Very Extended LAN - 대규모 네트워크 확장
   - D) Variable Extensible LAN - 동적 네트워크 구성

<details>

<summary>정답 보기</summary>

**정답: B) Virtual Extensible LAN - L2 오버레이 네트워크**

**설명:** VXLAN은 UDP와 24비트 VNI로 IP underlay 위에 L2 오버레이를 운반합니다. 필드에 약 1,600만 개 값이 가능하다는 뜻이며 Cilium 용량 보장이 아닙니다. Cilium은 오버레이 메타데이터로 ID 정보도 전달합니다.

</details>

6. BPF Map의 주요 역할은 무엇인가요?

   - A) 네트워크 라우팅 테이블 관리
   - B) eBPF 프로그램 간 데이터 공유 및 저장
   - C) DNS 레코드 캐싱
   - D) TLS 인증서 저장

<details>

<summary>정답 보기</summary>

**정답: B) eBPF 프로그램 간 데이터 공유 및 저장**

**설명:** BPF 맵은 커널 관리 상태·이벤트를 프로그램과 사용자 공간에 공유합니다. Hash·array 맵은 키를 사용하지만 ring buffer 등 일부 유형은 일반 lookup/update/delete를 지원하지 않습니다.

</details>

7. Cilium에서 포드의 보안 신원을 나타내는 숫자 식별자를 무엇이라고 부르나요?

   - A) Pod ID
   - B) Security Context
   - C) Identity
   - D) Endpoint ID

<details>

<summary>정답 보기</summary>

**정답: C) Identity**

**설명:** 보안 관련 레이블이 ID를 결정하며 모든 메타데이터 레이블이 참여하지는 않습니다. 할당 범위 안에서 엔드포인트가 ID를 공유할 수 있습니다. 숫자 엔드포인트 ID는 에이전트 로컬이며 다른 식별자입니다.

</details>

8. IPAM의 정식 명칭과 Cilium에서의 역할은 무엇인가요?

   - A) IP Address Management - IP 주소 할당 및 관리
   - B) Internet Protocol Access Manager - 인터넷 접근 관리
   - C) IP Assignment Module - IP 할당 모듈
   - D) Internal Protocol Address Mapper - 내부 프로토콜 주소 매핑

<details>

<summary>정답 보기</summary>

**정답: A) IP Address Management - IP 주소 할당 및 관리**

**설명:** IPAM은 주소를 할당·추적합니다. Cilium의 cluster-pool, multi-pool, Kubernetes host-scope, ENI 등은 모드마다 할당 주체가 다릅니다. GKE는 플랫폼이며 보편적인 독립 ipam.mode 값이 아니므로 관리형 플랫폼 연동을 확인합니다.

</details>

9. WireGuard의 주요 특징과 Cilium에서의 용도는 무엇인가요?

   - A) 패킷 캡처 도구 - 네트워크 분석
   - B) 현대적인 VPN 프로토콜 - 노드 간 트래픽 암호화
   - C) 로드 밸런싱 알고리즘 - 트래픽 분산
   - D) DNS 프록시 - 이름 해석

<details>

<summary>정답 보기</summary>

**정답: B) 현대적인 VPN 프로토콜 - 노드 간 트래픽 암호화**

**설명:** Cilium WireGuard는 지원되는 노드 간 트래픽을 보호합니다. 동일 노드 Pod 트래픽은 노드 터널을 통과하지 않으며 외부·노드 트래픽에는 별도 조건이 있습니다. 항상 IPsec보다 빠른 것은 아니므로 동등한 워크로드·보호 조건으로 비교합니다.

</details>

10. CNI의 정식 명칭과 역할은 무엇인가요?

    - A) Container Network Interface - 컨테이너 네트워크 플러그인 표준 인터페이스
    - B) Cloud Native Infrastructure - 클라우드 네이티브 인프라
    - C) Cluster Network Integration - 클러스터 네트워크 통합
    - D) Container Node Interconnect - 컨테이너 노드 연결

<details>

<summary>정답 보기</summary>

**정답: A) Container Network Interface - 컨테이너 네트워크 플러그인 표준 인터페이스**

**설명:** CNI는 런타임과 네트워크 플러그인 사이의 인터페이스를 정의합니다. 현재 Kubernetes에서 kubelet은 CRI를 사용하고 컨테이너 런타임이 CNI 호출을 관리합니다. kubelet의 직접 CNI 관리 플래그는 Kubernetes 1.24에서 제거되었습니다.

</details>

## 단답형 문제

11. Cilium에서 L7 프록시 및 서비스 메시 기능을 제공하는 오픈 소스 구성 요소의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Envoy

**설명:** Envoy는 구성된 HTTP/gRPC 프록시 기능을 제공합니다. DNS 정책은 Cilium DNS 프록시를 사용하며 Kafka L7 규칙은 제거되었습니다. 프록시 배포·수명은 설치 설정에 따르며 임의 L7 규칙마다 자동 배포되는 것은 아닙니다.

</details>

12. 각 노드에서 실행되며 eBPF 프로그램 로딩, 네트워크 정책 구현, 엔드포인트 관리를 담당하는 Cilium 구성 요소의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** Cilium Agent

**설명:** 에이전트는 Cilium 관리 대상 적격 노드의 로컬 엔드포인트, BPF 프로그램과 정책·데이터 경로 상태를 관리합니다. IPAM 책임은 모드에 따라 에이전트·operator·플랫폼에 나뉩니다.

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

**설명:** Service는 논리적 백엔드 접근 추상화입니다. 일반 ClusterIP에는 가상 IP가 있지만 headless에는 없으며 ExternalName은 DNS 별칭입니다. 선택자 없는 Service는 수동 관리·외부 엔드포인트를 표현할 수 있습니다.

</details>

15. 패킷의 소스 IP 주소를 수정하는 NAT 유형의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답:** SNAT (Source Network Address Translation)

**설명:** SNAT는 출발지 주소를 바꿉니다. Masquerading은 송신 경로·인터페이스와 관련된 주소를 선택하며 예외 범위와 선택한 게이트웨이 IP를 고려해야 합니다. 모든 Pod 송신 패킷이 반드시 변환되는 것은 아닙니다. DNAT는 목적지를 바꿉니다.

</details>

## 실습 문제

16. ClusterMesh, CRD, FQDN, mTLS를 정의와 연결하세요.

<details>

<summary>정답 보기</summary>

**정답:**

- **ClusterMesh**: 클러스터 간 네트워크 메타데이터·연결 기능입니다. 모든 정책 리소스를 자동 복제하지 않습니다.
- **CRD**: Kubernetes API에 사용자 정의 리소스 종류를 추가하는 정의입니다.
- **FQDN**: DNS 트리에서 전체 위치를 나타내는 절대 이름입니다. toFQDNs는 학습한 IP를 허용합니다.
- **mTLS**: 양쪽 피어가 인증하는 TLS 사용 방식입니다. 인증과 애플리케이션 인가는 별개입니다.

</details>


17. CRD로 할당한 ID와 실제 보안 레이블을 조회하고 에이전트의 보기와 구분하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```bash
set -euo pipefail
kubectl get ciliumidentities -o json > identities.json
jq '.items[]
| select(.["security-labels"]["k8s:app"] == "frontend")
| {id: .metadata.name, labels: .["security-labels"]}' identities.json
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
```

CRD 할당 모드를 가정합니다. CiliumIdentity는 클러스터 범위이며 `security-labels`가 보안 레이블 원본입니다. `metadata.labels`와 혼동하지 않습니다. 예약 ID·노드 로컬 ID가 모두 CRD에 나타나는 것은 아니므로 에이전트의 보기도 구분합니다. `CILIUM_POD`는 [대상 노드 선택 절차](../../../networking/cilium/07-advanced-topics.md)로 지정합니다.

</details>


18. 선택한 에이전트의 서비스·CT·NAT·정책·엔드포인트 맵을 조회하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```bash
set -eu
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf ct list global
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf policy get --all
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
```

담당 노드의 에이전트를 먼저 선택합니다. `--backends`와 정책 맵의 `--all`은 유효한 플래그입니다. 전체 CT·정책 맵 출력은 클 수 있으므로 필요할 때 대상 노드에서 사용합니다. `map list`는 에이전트가 관리하는 열린 맵의 목록이며 모든 커널 맵이나 활성 애플리케이션 연결을 완전하게 증명하지는 않습니다.

</details>


19. DNS 예외와 함께 api.example.com 및 한 단계 *.googleapis.com 이름에서 학습한 IP의 TCP 443을 허용하는 정책을 작성하고 한계를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: fqdn-egress-policy
  namespace: cilium-glossary-demo
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

정책만 작성하는 예제입니다. `cilium-glossary-demo` 네임스페이스와 해당 레이블의 클라이언트, 실제 CoreDNS 경로를 준비해야 합니다. TCP·UDP DNS와 DNS 프록시 관측을 허용합니다. `*.googleapis.com`은 한 단계 하위 이름만 일치시키며 apex나 `a.b.googleapis.com`에는 일치하지 않습니다. DNS `*`는 모든 질의 이름을 허용합니다. toFQDNs의 결과는 IP 허용이며 공유 IP의 HTTPS Host 제한이나 원격 서버 인증이 아닙니다. 다른 허용 정책과 TLS 검증도 확인합니다.

</details>


20. Operator와 Agent의 역할을 비교하고 Operator 상태를 확인하세요.

<details>

<summary>정답 보기</summary>

**정답:**

```bash
kubectl -n kube-system get deployment cilium-operator
kubectl -n kube-system get pods -l name=cilium-operator
kubectl -n kube-system logs -l name=cilium-operator -c cilium-operator --prefix --since=10m --tail=100
cilium status --verbose
kubectl get ciliumidentities
kubectl get ciliumendpoints --all-namespaces
```

| 구성 요소 | 범위와 역할 |
| --- | --- |
| Agent | 관리 대상 노드의 엔드포인트, BPF 프로그램, 정책·데이터 경로 상태와 모드별 로컬 IPAM 작업. |
| Operator | 클러스터 수준 CRD 등록, 모드별 IPAM/LB IPAM, 고아 객체·ID 회수, 활성화한 Ingress/Gateway 변환 등. |

`name=cilium-operator`는 현재 차트에서 유효합니다. 복제본 수는 `operator.replicas`로 구성하며 1–2개로 제한되지 않습니다. 기본 ID 생성 주체는 Agent이며 Operator ID 관리는 별도 Beta 모드입니다. 활성화한 기능에 따라 ClusterMesh EndpointSlice/MCS 동기화 등도 수행하므로 모든 역할을 고정된 단일 목록으로 일반화하지 않습니다.

</details>


***

[학습 자료로 돌아가기](../../../networking/cilium/glossary.md) | [Cilium 퀴즈 목록](../../README.md#cilium)
