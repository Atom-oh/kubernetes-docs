# Cilium IPAM 및 네트워크 정책 퀴즈

> **Cilium 1.20.1 · 2026-09-12**

## IPAM

1. **플랫폼 override가 없을 때 일반 기본 IPAM 모드와 할당 모델은 무엇인가요?**
   - A) kubernetes; 모든 Pod가 Kubernetes API에 IP 요청
   - B) cluster-pool; Operator가 노드 CIDR, agent가 로컬 Pod IP 할당
   - C) crd; 모든 Pod가 CiliumPodIPPool 생성
   - D) 모든 플랫폼에서 eni

   <details>
   <summary>정답 보기</summary>

   **정답: B) cluster-pool; Operator가 노드 CIDR, agent가 로컬 Pod IP 할당**

   Cluster-pool은 CiliumNode를 통한 노드 prefix 할당을 사용합니다. Pod마다 중앙에 주소를 요청하는 구조가 아니며 플랫폼 프로필은 다른 backend를 선택할 수 있습니다.

   </details>

2. **Cilium Operator의 cluster-pool 할당 대신 Kubernetes Node 상태에서 노드 prefix를 얻는 모드는 무엇인가요?**
   - A) cluster-pool
   - B) kubernetes(host scope)
   - C) multi-pool만
   - D) eni만

   <details>
   <summary>정답 보기</summary>

   **정답: B) kubernetes(host scope)**

   Kubernetes가 필요한 노드 CIDR을 제공하고 agent가 그 안에서 할당합니다. Host scope와 cluster-pool 모두 개별 주소를 로컬 할당하며 prefix 조정이 없어지지는 않습니다.

   </details>

3. **준비된 EC2 노드 설치에서 Cilium 자체가 AWS ENI와 VPC 주소를 관리할 때 사용할 backend는 무엇인가요?**
   - A) kubernetes
   - B) cluster-pool
   - C) eni
   - D) 모든 AWS 노드의 delegated-plugin

   <details>
   <summary>정답 보기</summary>

   **정답: C) eni**

   ENI IPAM에 해당합니다. AWS VPC CNI chaining은 주소 할당을 VPC CNI가 유지하고 Hybrid Nodes는 별도 경로입니다. Fargate·Auto Mode는 이 대체 구성을 지원하지 않습니다.

   </details>

4. **Host-scope IPAM과 관련된 Kubernetes 필드는 무엇인가요?**
   - A) Node.spec.podCIDRs와 이전·단일 계열 필드 Node.spec.podCIDR
   - B) Node.spec.subnet
   - C) Service.spec.podCIDR
   - D) CiliumPodIPPool.spec.selector

   <details>
   <summary>정답 보기</summary>

   **정답: A) Node.spec.podCIDRs와 이전·단일 계열 필드 Node.spec.podCIDR**

   Kubernetes Node 필드입니다. Cluster-pool은 CiliumNode.spec.ipam.podCIDRs를 사용하며 기준 상태는 선택한 모드에 따라 다릅니다.

   </details>

5. **유효 IPAM 설정은 어떻게 조사해야 하나요?**
   - A) ipam을 포함한 grep 한 줄을 전체 설정으로 간주
   - B) Pod Ready만 확인
   - C) 항상 CiliumNode 첫 주소와 CIDR 사용
   - D) 의도한 값·노드 override, 실제 agent·operator 상태와 할당 모드의 리소스를 비교

   <details>
   <summary>정답 보기</summary>

   **정답: D) 의도한 값·노드 override, 실제 agent·operator 상태와 할당 모드의 리소스를 비교**

   Helm·ConfigMap 값, 노드 override, 할당 상태는 서로 보완합니다. CiliumNode가 모든 모드의 기준은 아니며 배열 순서가 next hop을 결정하지 않습니다.

   </details>

## 정책 기본

6. **이 가이드의 CiliumNetworkPolicy API 버전은 무엇인가요?**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>정답 보기</summary>

   **정답: C) cilium.io/v2**

   CiliumNetworkPolicy는 cilium.io/v2입니다. CiliumPodIPPool의 v2alpha1이나 일반 Kubernetes NetworkPolicy와 구분합니다.

   </details>

7. **Namespace 범위 CiliumNetworkPolicy의 endpointSelector는 무엇을 선택하나요?**
   - A) 해당 namespace에서 정책 대상이 되는 endpoint
   - B) 새로 생성할 Kubernetes Service
   - C) 모든 namespace의 호스트 노드
   - D) 상속할 다른 정책

   <details>
   <summary>정답 보기</summary>

   **정답: A) 해당 namespace에서 정책 대상이 되는 endpoint**

   정책을 적용할 endpoint를 선택합니다. 리소스 범위·선택자는 ingress·egress에 기술하는 통신 peer와 별개입니다.

   </details>

8. **Ingress 규칙은 무엇을 설명하나요?**
   - A) 선택된 endpoint로 들어오는 트래픽
   - B) 선택된 endpoint에서 나가는 트래픽
   - C) 새 IP pool
   - D) 경로 광고

   <details>
   <summary>정답 보기</summary>

   **정답: A) 선택된 endpoint로 들어오는 트래픽**

   Ingress는 선택한 대상 endpoint 기준입니다. 해당 peer·port·지원 protocol 제약을 적용합니다.

   </details>

9. **Egress 규칙은 무엇을 설명하나요?**
   - A) 선택된 endpoint로 들어오는 트래픽
   - B) 선택된 endpoint에서 나가는 트래픽
   - C) 모든 곳의 모든 트래픽
   - D) Kubernetes 밖에서 오는 트래픽만

   <details>
   <summary>정답 보기</summary>

   **정답: B) 선택된 endpoint에서 나가는 트래픽**

   Egress는 선택된 endpoint의 outgoing 트래픽을 제어합니다. 필요한 DNS·애플리케이션 의존성을 의도적으로 유지해야 합니다.

   </details>

10. **선택적인 Cilium 규칙의 spec.labels 용도는 무엇인가요?**
    - A) endpointSelector 대신 대상 Pod 선택
    - B) 규칙 식별과 메타데이터
    - C) 같은 label 정책을 모두 상속
    - D) Pod IP 할당

    <details>
    <summary>정답 보기</summary>

    **정답: B) 규칙 식별과 메타데이터**

    규칙 label은 식별·조회에 사용할 수 있고 고유할 필요는 없습니다. 다른 정책을 참조·상속하지 않으며 Kubernetes metadata.labels는 리소스 자체를 표시합니다.

    </details>

## 통신 대상 선택

11. **toCIDR/toCIDRSet의 목적과 기본 경계는 무엇인가요?**
    - A) 주로 외부 peer의 IP prefix 선택이며 관리 Pod·노드 매칭에는 문서화된 기본 제한이 있음
    - B) HTTP URL 필터링
    - C) Service 자동 생성
    - D) 해당 prefix의 주소 할당

    <details>
    <summary>정답 보기</summary>

    **정답: A) 주로 외부 peer의 IP prefix 선택이며 관리 Pod·노드 매칭에는 문서화된 기본 제한이 있음**

    일반 관리 Pod 정책은 endpoint selector를 사용합니다. 이 릴리스는 identity 소비 영향을 가진 선택적 beta pods/nodes CIDR 매칭을 문서화합니다. 기본 동작을 무조건적인 IP 매칭으로 설명하면 안 됩니다.

    </details>

12. **toFQDNs가 허용하는 것은 무엇인가요?**
    - A) 자동으로 모든 DNS 질의
    - B) 도메인 아래 모든 HTTP URL
    - C) 선택한 이름에서 학습한 IP로의 트래픽을 port 등 정책 제약에 따라 허용
    - D) 정적으로 지정한 IP만

    <details>
    <summary>정답 보기</summary>

    **정답: C) 선택한 이름에서 학습한 IP로의 트래픽을 port 등 정책 제약에 따라 허용**

    별도 DNS proxy 규칙으로 이름·IP를 관찰해야 합니다. 53번 포트 허용만으로 학습이 활성화되지 않으며 IP 허용이 HTTP hostname·사용자 인가 검사는 아닙니다.

    </details>

13. **world entity는 무엇을 나타내나요?**
    - A) 모든 로컬·원격 Pod를 구분 없이
    - B) 넓은 외부 identity 범주
    - C) 제어플레인 노드만
    - D) 공용 인터넷 주소만

    <details>
    <summary>정답 보기</summary>

    **정답: B) 넓은 외부 identity 범주**

    사설 외부 peer도 포함할 수 있으며 all이나 특정 원격 클러스터 선택자가 아닙니다. 필요하면 명시적인 peer와 더 좁은 규칙을 사용합니다.

    </details>

14. **toServices는 어떻게 동작하나요?**
    - A) Kubernetes Service selector 또는 selectorless EndpointSlice 주소를 정책 selector로 변환
    - B) Service와 경로를 자동 생성
    - C) 모든 DNS 이름에 도달 가능하게 함
    - D) 모든 kube-apiserver entity 규칙 대체

    <details>
    <summary>정답 보기</summary>

    **정답: A) Kubernetes Service selector 또는 selectorless EndpointSlice 주소를 정책 selector로 변환**

    Selectorless Service는 CIDR 기반 selector와 해당 제한을 사용합니다. 특수 default/kubernetes Service를 일반 workload selector처럼 가정하면 안 됩니다.

    </details>

15. **Host firewall 대상 선택에 nodeSelector를 사용하는 곳은 어디인가요?**
    - A) 조건 없이 모든 namespace CiliumNetworkPolicy
    - B) Host firewall을 구성한 CiliumClusterwideNetworkPolicy
    - C) 모든 Pod IP를 할당하는 CiliumPodIPPool
    - D) Service annotation

    <details>
    <summary>정답 보기</summary>

    **정답: B) Host firewall을 구성한 CiliumClusterwideNetworkPolicy**

    Rule API는 nodeSelector를 CiliumClusterwideNetworkPolicy로 제한합니다. endpointSelector 및 fromNodes/toNodes peer 선택과 구분합니다.

    </details>

## L7 정책

16. **지원되는 Cilium L7 HTTP 규칙이 제한할 수 있는 속성은 무엇인가요?**
    - A) Path
    - B) Method
    - C) Header
    - D) 위의 모든 것

    <details>
    <summary>정답 보기</summary>

    **정답: D) 위의 모든 것**

    보이는 HTTP 트래픽에 Envoy가 규칙을 적용합니다. 별도 무제한 L4 허용이 겹치는 L7 제한을 우회할 수 있으며 정책 허용도 애플리케이션 성공을 보장하지 않습니다.

    </details>

17. **Cilium1.20.1의 rules.kafka에 대한 설명으로 맞는 것은 무엇인가요?**
    - A) 기본적으로 topic 인가 제공
    - B) apiVersion을 v2alpha1로 바꾸면 활성화
    - C) Broker 연결을 자동 암호화
    - D) 내장 Kafka L7 API가 제거되었으며 적절한 네트워크 제어와 broker 인가를 사용

    <details>
    <summary>정답 보기</summary>

    **정답: D) 내장 Kafka L7 API가 제거되었으며 적절한 네트워크 제어와 broker 인가를 사용**

    이전 topic·API-key·client-ID 정책을 적용하지 않습니다. 실제 listener port로 L4 연결을 제어하고 broker의 인증·인가 기능을 사용합니다.

    </details>

18. **이 릴리스 구현과 일치하는 wildcard 설명은 무엇인가요?**
    - A) `*.example.com`은 example.com과 a.b.example.com도 일치
    - B) `*.example.com`은 한 하위 label, `**.example.com`은 한 단계 이상이며 둘 다 apex 제외
    - C) 모든 별표가 항상 점도 일치
    - D) matchName과 matchPattern이 DNS 주소 할당

    <details>
    <summary>정답 보기</summary>

    **정답: B) `*.example.com`은 한 하위 label, `**.example.com`은 한 단계 이상이며 둘 다 apex 제외**

    정규화된 DNS 이름 전체를 매칭합니다. 정확한 이름, 한 label wildcard, 다단계 prefix는 의미가 다르며 apex는 별도 matchName으로 포함할 수 있습니다.

    </details>

19. **지원되는 gRPC 서비스·메서드·metadata 제약은 어떻게 표현하나요?**
    - A) rules.grpc의 protobuf 필드 필터
    - B) L3 CIDR 매칭만
    - C) 지원 Envoy 경로의 HTTP/2 path와 header 매칭
    - D) CNI를 kube-proxy로 교체

    <details>
    <summary>정답 보기</summary>

    **정답: C) 지원 Envoy 경로의 HTTP/2 path와 header 매칭**

    gRPC 서비스·메서드는 HTTP/2 path, metadata는 header에 나타납니다. 임의 protobuf payload 검사가 아니며 TLS 가시성도 필요합니다.

    </details>

20. **구성 요소를 올바르게 구분한 설명은 무엇인가요?**
    - A) kube-proxy가 모든 L7 규칙 집행
    - B) 지원 HTTP/gRPC는 Envoy, DNS 정책은 Cilium DNS proxy
    - C) DNS 정책에 NGINX Ingress 필수
    - D) 모든 L7 parser가 커널 BPF에서만 실행

    <details>
    <summary>정답 보기</summary>

    **정답: B) 지원 HTTP/gRPC는 Envoy, DNS 정책은 Cilium DNS proxy**

    DNS proxy는 기본적으로 agent 내부이며 별도 alpha standalone 모드도 문서화됩니다. 모든 DNS 규칙에 Envoy가 필요하거나 암호화된 내용이 자동으로 보인다고 가정하지 않습니다.

    </details>

[본문 복습](../../../networking/cilium/04-ipam-policy.md).
