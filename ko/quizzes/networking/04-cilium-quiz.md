# Cilium 퀴즈

이 퀴즈는 Cilium의 eBPF 기반 네트워킹, 보안 정책, Hubble 관찰성, 서비스 메시 및 Amazon EKS 통합에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Cilium이 고성능 네트워킹을 제공하기 위해 사용하는 핵심 Linux 커널 기술은 무엇인가요?
   - A) iptables
   - B) netfilter
   - C) eBPF (extended Berkeley Packet Filter)
   - D) nftables

<details>

<summary>정답 보기</summary>

**정답: C) eBPF (extended Berkeley Packet Filter)**

**설명:**
Cilium은 eBPF(extended Berkeley Packet Filter) 기술을 기반으로 합니다. eBPF는 Linux 커널 내에서 샌드박스 가상 머신처럼 작동하여, 커널 코드를 수정하지 않고도 커널 내에서 프로그램을 안전하게 실행할 수 있게 해줍니다. 이를 통해 네트워크 패킷 처리, 정책 시행, 모니터링 등을 기존 iptables 기반 접근 방식보다 훨씬 효율적으로 수행할 수 있습니다.
</details>

2. Cilium에서 기존 kube-proxy를 완전히 대체하는 모드는 무엇인가요?
   - A) kubeProxyReplacement=partial
   - B) kubeProxyReplacement=strict
   - C) kubeProxyReplacement=disabled
   - D) kubeProxyReplacement=full

<details>

<summary>정답 보기</summary>

**정답: B) kubeProxyReplacement=strict**

**설명:**
Cilium은 kube-proxy를 대체하여 서비스 로드 밸런싱을 eBPF로 처리할 수 있습니다. `kubeProxyReplacement=strict` 모드는 kube-proxy를 완전히 대체하여 모든 서비스 로드 밸런싱을 Cilium이 담당합니다. 이 모드에서는 kube-proxy가 실행되지 않아야 하며, Cilium이 모든 ClusterIP, NodePort, LoadBalancer 서비스를 처리합니다. `partial` 모드는 일부 기능만 대체합니다.
</details>

3. Cilium에서 네트워크 흐름을 시각화하고 모니터링하기 위한 관찰성 도구는 무엇인가요?
   - A) Prometheus
   - B) Grafana
   - C) Hubble
   - D) Jaeger

<details>

<summary>정답 보기</summary>

**정답: C) Hubble**

**설명:**
Hubble은 Cilium의 네이티브 관찰성 계층으로, eBPF를 통해 수집된 네트워크 흐름 데이터를 시각화하고 분석할 수 있게 해줍니다. Hubble은 CLI, UI, 그리고 Relay 구성 요소를 제공하여 실시간 네트워크 흐름 관찰, 서비스 맵 시각화, 정책 결정 모니터링 등을 지원합니다. Prometheus와 Grafana는 메트릭 수집 및 시각화 도구이지만, Hubble은 Cilium 전용 관찰성 솔루션입니다.
</details>

4. Cilium 네트워크 정책에서 L7(애플리케이션 계층) HTTP 트래픽을 제어하기 위해 사용하는 CRD는 무엇인가요?
   - A) NetworkPolicy
   - B) CiliumNetworkPolicy
   - C) IngressPolicy
   - D) HTTPPolicy

<details>

<summary>정답 보기</summary>

**정답: B) CiliumNetworkPolicy**

**설명:**
CiliumNetworkPolicy는 Cilium의 커스텀 리소스로, 표준 Kubernetes NetworkPolicy보다 훨씬 강력한 L3-L7 네트워크 정책을 지원합니다. HTTP 메서드, 경로, 헤더 등 애플리케이션 계층의 세부적인 트래픽 제어가 가능합니다. 표준 NetworkPolicy는 L3/L4(IP, 포트) 수준의 정책만 지원하지만, CiliumNetworkPolicy는 HTTP, gRPC, Kafka 등 다양한 L7 프로토콜을 지원합니다.
</details>

5. Cilium에서 노드 간 트래픽 암호화를 위해 지원하는 프로토콜은 무엇인가요?
   - A) SSL/TLS만 지원
   - B) IPsec과 WireGuard
   - C) SSH 터널링만 지원
   - D) mTLS만 지원

<details>

<summary>정답 보기</summary>

**정답: B) IPsec과 WireGuard**

**설명:**
Cilium은 노드 간 투명한 암호화를 위해 IPsec과 WireGuard 두 가지 프로토콜을 지원합니다. WireGuard는 최신 암호화 프로토콜로 더 나은 성능을 제공하며, IPsec은 광범위한 호환성을 제공합니다. 암호화는 `--set encryption.enabled=true --set encryption.type=wireguard` (또는 ipsec) 설정으로 활성화할 수 있습니다. 이를 통해 애플리케이션 수정 없이 네트워크 계층에서 암호화가 적용됩니다.
</details>

6. Cilium에서 특정 FQDN(도메인 이름)으로의 이그레스 트래픽만 허용하는 정책을 구성할 때 사용하는 필드는 무엇인가요?
   - A) toEndpoints
   - B) toEntities
   - C) toFQDNs
   - D) toDomains

<details>

<summary>정답 보기</summary>

**정답: C) toFQDNs**

**설명:**
CiliumNetworkPolicy에서 `toFQDNs` 필드를 사용하면 특정 도메인 이름으로의 이그레스 트래픽을 허용할 수 있습니다. `matchName`으로 정확한 도메인을 지정하거나 `matchPattern`으로 와일드카드 패턴을 사용할 수 있습니다. 예를 들어 `matchPattern: "*.amazonaws.com"`으로 모든 AWS 서비스로의 트래픽을 허용할 수 있습니다. 이 기능은 DNS 기반 접근 제어를 가능하게 하여 동적 IP를 가진 외부 서비스에 대한 정책을 쉽게 관리할 수 있습니다.
</details>

7. Amazon EKS에서 Cilium을 AWS ENI 모드로 설치할 때 필요한 IPAM 설정은 무엇인가요?
   - A) ipam.mode=kubernetes
   - B) ipam.mode=cluster-pool
   - C) ipam.mode=eni
   - D) ipam.mode=aws

<details>

<summary>정답 보기</summary>

**정답: C) ipam.mode=eni**

**설명:**
Amazon EKS에서 Cilium을 사용할 때 `ipam.mode=eni` 설정으로 AWS Elastic Network Interface(ENI)를 활용하여 네이티브 AWS 네트워킹 성능을 얻을 수 있습니다. 이 모드에서는 파드 IP가 VPC 서브넷에서 직접 할당되어 AWS 네트워크와 완전히 통합됩니다. 또한 `eni.enabled=true`와 `tunnel=disabled`를 함께 설정하여 오버레이 네트워킹 없이 직접 라우팅을 사용합니다.
</details>

8. Cilium에서 클러스터 전체에 적용되는 네트워크 정책을 정의하기 위한 CRD는 무엇인가요?
   - A) CiliumGlobalPolicy
   - B) CiliumClusterwideNetworkPolicy
   - C) CiliumClusterPolicy
   - D) ClusterNetworkPolicy

<details>

<summary>정답 보기</summary>

**정답: B) CiliumClusterwideNetworkPolicy**

**설명:**
CiliumClusterwideNetworkPolicy(CCNP)는 네임스페이스에 관계없이 클러스터 전체에 적용되는 네트워크 정책을 정의하는 CRD입니다. 이를 통해 클러스터 수준의 기본 거부 정책, DNS 허용 정책, 또는 특정 엔티티(예: world, cluster)에 대한 전역 접근 제어를 구현할 수 있습니다. 일반 CiliumNetworkPolicy는 특정 네임스페이스에만 적용되지만, CCNP는 모든 네임스페이스에 적용됩니다.
</details>

## 단답형 문제

9. Cilium에서 패킷이 네트워크 인터페이스에 도착하자마자 커널 공간에서 초기 처리(DDoS 방어, 부하 분산 등)를 수행하는 eBPF 프로그램 유형은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: XDP (eXpress Data Path)**

**설명:**
XDP(eXpress Data Path)는 네트워크 인터페이스 드라이버 수준에서 패킷을 처리하는 eBPF 프로그램 유형입니다. 패킷이 커널 네트워킹 스택에 도달하기 전에 처리되므로 매우 낮은 지연 시간과 높은 처리량을 제공합니다. Cilium은 XDP를 사용하여 DDoS 공격 방어, 고속 부하 분산, 패킷 필터링 등을 수행합니다. XDP 가속을 활성화하려면 `--set loadBalancer.acceleration=native` 설정을 사용합니다.
</details>

10. Cilium에서 여러 Kubernetes 클러스터를 연결하여 파드 간 직접 통신을 가능하게 하는 기능은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Cluster Mesh (클러스터 메시)**

**설명:**
Cluster Mesh는 여러 Kubernetes 클러스터를 연결하여 클러스터 간 파드-투-파드 통신, 서비스 검색, 네트워크 정책 적용을 가능하게 하는 Cilium의 멀티 클러스터 기능입니다. 각 클러스터에서 `cilium clustermesh enable` 명령으로 활성화하고, `cilium clustermesh connect`로 클러스터를 연결합니다. 이를 통해 하이브리드 클라우드 또는 멀티 리전 환경에서 일관된 네트워킹 경험을 제공합니다.
</details>

11. Cilium 설치 및 상태 확인, 연결성 테스트를 수행하기 위한 공식 명령줄 도구의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Cilium CLI (cilium 명령어)**

**설명:**
Cilium CLI는 Cilium의 공식 명령줄 도구로, `cilium install`, `cilium status`, `cilium connectivity test` 등의 명령을 제공합니다. 설치, 업그레이드, 상태 확인, 연결성 테스트, Hubble 관리 등 Cilium 운영에 필요한 모든 작업을 수행할 수 있습니다. 예를 들어 `cilium status --verbose`로 상세한 상태 정보를 확인하고, `cilium connectivity test`로 네트워크 연결성을 검증할 수 있습니다.
</details>

12. Cilium이 사이드카 프록시 없이 L7 트래픽 관리(트래픽 분할, 카나리 배포 등)를 제공하는 기능은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: Cilium Service Mesh (사이드카 없는 서비스 메시)**

**설명:**
Cilium Service Mesh는 eBPF를 활용하여 기존 Istio, Linkerd와 같은 서비스 메시 솔루션과 달리 사이드카 프록시 없이 L7 트래픽 관리를 제공합니다. 이를 통해 HTTP 라우팅, 트래픽 분할, 카나리 배포, mTLS 등의 서비스 메시 기능을 더 낮은 리소스 오버헤드와 지연 시간으로 구현할 수 있습니다. `--set serviceMesh.enabled=true` 설정으로 활성화합니다.
</details>

## 실습 문제

13. Cilium을 사용하여 frontend 레이블을 가진 파드에서 backend 레이블을 가진 파드의 8080 포트로 GET /api/v1/products 요청만 허용하는 L7 네트워크 정책을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend-api
  namespace: app
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
      rules:
        http:
        - method: "GET"
          path: "/api/v1/products"
```

**설명:**
CiliumNetworkPolicy를 사용하여 L7 HTTP 트래픽을 제어합니다. `endpointSelector`는 정책이 적용될 대상 파드(backend)를 선택합니다. `fromEndpoints`로 소스 파드(frontend)를 지정하고, `toPorts`에서 포트와 HTTP 규칙을 정의합니다. `rules.http`에서 허용할 HTTP 메서드와 경로를 지정합니다. 이 정책은 frontend 파드가 backend 파드의 /api/v1/products 경로에 GET 요청만 할 수 있도록 제한합니다.
</details>

14. Hubble을 활성화하고, 특정 네임스페이스에서 거부된 트래픽을 실시간으로 관찰하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. Hubble UI와 함께 Hubble 활성화
cilium hubble enable --ui

# 2. Hubble 상태 확인
cilium hubble status

# 3. Hubble 포트 포워딩 (별도 터미널에서)
cilium hubble port-forward &

# 4. 특정 네임스페이스에서 거부된 트래픽 관찰
hubble observe --namespace app --verdict DROPPED

# 5. 더 자세한 정보와 함께 실시간 관찰
hubble observe --namespace app --verdict DROPPED --follow

# 6. HTTP 프로토콜 트래픽만 필터링하여 관찰
hubble observe --namespace app --verdict DROPPED --protocol http

# 7. 특정 파드에서 나가는 거부된 트래픽 관찰
hubble observe --from-pod app/frontend --verdict DROPPED
```

**설명:**
Hubble을 활성화하면 Cilium이 처리하는 모든 네트워크 흐름을 관찰할 수 있습니다. `--verdict DROPPED` 플래그는 네트워크 정책에 의해 거부된 트래픽만 필터링합니다. `--follow` 플래그로 실시간 스트리밍을 활성화하고, `--namespace`, `--protocol`, `--from-pod` 등으로 세부적인 필터링이 가능합니다. 이를 통해 네트워크 정책이 예상대로 작동하는지, 어떤 트래픽이 차단되는지 디버깅할 수 있습니다.
</details>

15. Amazon EKS 클러스터에서 기존 AWS VPC CNI를 제거하고 Cilium을 ENI 모드로 설치하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
# 1. 기존 AWS VPC CNI DaemonSet 제거
kubectl delete daemonset -n kube-system aws-node

# 2. Cilium CLI 설치 (아직 설치하지 않은 경우)
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin

# 3. Cilium을 ENI 모드로 설치
cilium install \
  --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set tunnel=disabled \
  --set kubeProxyReplacement=strict

# 4. 설치 상태 확인
cilium status --wait

# 5. 연결성 테스트 실행
cilium connectivity test
```

**설명:**
먼저 기존 AWS VPC CNI(aws-node DaemonSet)를 제거합니다. 그 다음 Cilium을 ENI 모드로 설치하는데, `eni.enabled=true`로 ENI 통합을 활성화하고, `ipam.mode=eni`로 AWS ENI IPAM을 사용합니다. `tunnel=disabled`로 오버레이 네트워킹을 비활성화하여 네이티브 AWS 라우팅을 사용합니다. `kubeProxyReplacement=strict`로 kube-proxy도 대체할 수 있습니다. 설치 후 `cilium connectivity test`로 네트워크 연결성을 검증합니다.
</details>

---

**점수 계산:**
- 13-15개 정답: 우수 (Cilium 전문가 수준)
- 10-12개 정답: 양호 (실무 적용 가능)
- 7-9개 정답: 보통 (추가 학습 권장)
- 0-6개 정답: 미흡 (기본 개념 복습 필요)

[학습 자료로 돌아가기](../../tools/04-cilium.md)
