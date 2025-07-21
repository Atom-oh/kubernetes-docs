# Cilium 퀴즈

## 기본 개념

1. **Cilium의 핵심 기술은 무엇인가요?**
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec
   
   **정답**: B) eBPF

2. **Cilium 1.17 버전이 지원하는 최소 Kubernetes 버전은 무엇인가요?**
   - A) 1.28
   - B) 1.29
   - C) 1.30
   - D) 1.31
   
   **정답**: C) 1.30

3. **Cilium이 제공하는 네트워크 정책은 어떤 계층까지 지원하나요?**
   - A) L3 (네트워크 계층)
   - B) L3-L4 (네트워크 및 전송 계층)
   - C) L3-L7 (네트워크부터 애플리케이션 계층)
   - D) L2-L3 (데이터 링크 및 네트워크 계층)
   
   **정답**: C) L3-L7 (네트워크부터 애플리케이션 계층)

## 네트워킹 및 아키텍처

4. **Cilium에서 네트워크 가시성을 제공하는 도구는 무엇인가요?**
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger
   
   **정답**: B) Hubble

5. **Cilium의 분산 로드 밸런싱 기능은 무엇을 대체할 수 있나요?**
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet
   
   **정답**: B) kube-proxy

6. **Cilium에서 지원하는 네트워크 암호화 방식은 무엇인가요? (여러 개 선택 가능)**
   - A) IPsec
   - B) WireGuard
   - C) TLS
   - D) SSH
   
   **정답**: A) IPsec, B) WireGuard

## 고급 기능 및 통합

7. **Cilium의 멀티 클러스터 기능을 무엇이라고 부르나요?**
   - A) Cluster Federation
   - B) Cluster Mesh
   - C) Multi-Cluster Network
   - D) Global Cluster
   
   **정답**: B) Cluster Mesh

8. **Cilium에서 IP 주소 관리(IPAM)에 사용할 수 있는 방식이 아닌 것은?**
   - A) Cluster Scope
   - B) Kubernetes Host Scope
   - C) CRD 기반 IPAM
   - D) DNS 기반 IPAM
   
   **정답**: D) DNS 기반 IPAM

9. **Cilium이 AWS EKS에서 사용할 수 있는 네트워킹 통합 방식은 무엇인가요?**
   - A) AWS VPC CNI
   - B) AWS ENI 통합
   - C) AWS Transit Gateway
   - D) AWS PrivateLink
   
   **정답**: B) AWS ENI 통합

## 문제 해결 및 성능

10. **Cilium의 연결성 문제를 진단하는 명령어는 무엇인가요?**
    - A) `cilium status`
    - B) `cilium connectivity test`
    - C) `cilium diagnose`
    - D) `cilium troubleshoot`
    
    **정답**: B) `cilium connectivity test`

11. **Cilium에서 패킷 처리 성능을 최적화하기 위해 사용하는 기술은 무엇인가요?**
    - A) DPDK
    - B) XDP (eXpress Data Path)
    - C) RDMA
    - D) SR-IOV
    
    **정답**: B) XDP (eXpress Data Path)

12. **Cilium 1.17에서 지원하는 최소 Linux 커널 버전은 무엇인가요?**
    - A) 3.10
    - B) 4.9
    - C) 4.19
    - D) 5.10
    
    **정답**: C) 4.19

## 실제 사용 사례

13. **다음 중 Cilium이 특히 유용한 사용 사례는 무엇인가요? (여러 개 선택 가능)**
    - A) 마이크로서비스 아키텍처
    - B) 멀티 클러스터 환경
    - C) 보안 중심 환경
    - D) 단일 모놀리식 애플리케이션
    
    **정답**: A) 마이크로서비스 아키텍처, B) 멀티 클러스터 환경, C) 보안 중심 환경

14. **Cilium의 서비스 메시 기능은 어떤 기존 서비스 메시 솔루션과 통합될 수 있나요?**
    - A) Istio
    - B) Linkerd
    - C) Consul
    - D) 모두 다
    
    **정답**: A) Istio

15. **Cilium을 사용하여 구현할 수 있는 보안 기능이 아닌 것은?**
    - A) 네트워크 정책 적용
    - B) 암호화된 통신
    - C) API 인식 보안
    - D) 사용자 인증 및 권한 부여
    
    **정답**: D) 사용자 인증 및 권한 부여

## 호환성 및 업그레이드

16. **Cilium 1.17은 어떤 EKS 버전과 호환되나요?**
    - A) 1.29 이상
    - B) 1.30 이상
    - C) 1.31 이상
    - D) 1.32 이상
    
    **정답**: B) 1.30 이상

17. **Cilium을 업그레이드할 때 권장되는 방식은 무엇인가요?**
    - A) 한 번에 여러 메이저 버전 건너뛰기
    - B) 마이너 버전 단위로 순차적 업그레이드
    - C) 항상 최신 버전으로 직접 업그레이드
    - D) 업그레이드 전 모든 네트워크 정책 삭제
    
    **정답**: B) 마이너 버전 단위로 순차적 업그레이드

18. **Cilium의 Windows 노드 지원 상태는 어떻게 되나요?**
    - A) 완전히 지원됨
    - B) 지원되지 않음
    - C) 제한적으로 지원됨
    - D) 베타 단계에서 지원됨
    
    **정답**: C) 제한적으로 지원됨

## 실습 및 구성

19. **Cilium CLI를 사용하여 Cilium을 설치하는 명령어는 무엇인가요?**
    - A) `cilium install`
    - B) `cilium deploy`
    - C) `cilium setup`
    - D) `cilium create`
    
    **정답**: A) `cilium install`

20. **Cilium 네트워크 정책의 API 버전은 무엇인가요?**
    - A) `networking.k8s.io/v1`
    - B) `cilium.io/v1`
    - C) `cilium.io/v2`
    - D) `policy.cilium.io/v1`
    
    **정답**: C) `cilium.io/v2`
