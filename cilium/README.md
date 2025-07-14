# Cilium 딥다이브: 클라우드 네이티브 네트워킹의 미래

## 강의 개요

이 강의는 Cilium의 핵심 개념과 기술에 대한 포괄적인 이해를 제공합니다. 일주일 동안 Cilium의 아키텍처, eBPF 기술, 네트워킹 모델, 보안 기능 등을 심층적으로 탐구할 것입니다.

### 강의 일정

**1일차: [Cilium 소개 및 기본 개념](day1-introduction.md)**
- Cilium 개요 및 역사
- 컨테이너 네트워킹 기초
- CNI(Container Network Interface) 이해하기
- Cilium의 차별화 포인트

**2일차: [eBPF 기술 심층 분석](day2-ebpf.md)**
- eBPF 기술 소개 및 역사
- 커널 내 eBPF 작동 방식
- eBPF 프로그램 유형 및 맵
- Cilium에서의 eBPF 활용

**3일차: [네트워킹 모델 및 VXLAN](day3-networking.md)**
- 컨테이너 네트워킹 모델 비교
- VXLAN 기술 심층 분석
- Cilium의 오버레이 네트워킹
- 성능 최적화 기법
- 라우팅 메커니즘 (Encapsulation vs Native-Routing)
- 클라우드 제공업체별 네트워킹 (AWS ENI, Google Cloud)

**4일차: [IPAM 및 네트워크 정책](day4-ipam-policy.md)**
- IP 주소 관리(IPAM) 전략
- Kubernetes와 Cilium IPAM 통합
- 네트워크 정책 설계 및 구현
- 멀티 클러스터 시나리오
- IPAM 모드 심층 분석 (Cluster Scope, Kubernetes Host Scope, Multi-Pool)
- 클라우드 제공업체별 IPAM (Azure IPAM, AWS ENI, GKE)
- CRD 기반 IPAM

**5일차: [L2-L7 네트워킹 및 로드 밸런싱](day5-l2-l7-networking.md)**
- OSI 모델 계층 이해 (L2, L3, L4, L7)
- Cilium의 계층별 기능
- 서비스 메시 통합
- 로드 밸런싱 아키텍처
- 마스커레이딩 구성 및 구현 모드
- IPv4 프래그먼트 처리

**6일차: [보안 및 가시성](day6-security-visibility.md)**
- Cilium의 보안 기능
- 네트워크 가시성 및 모니터링
- Hubble 아키텍처 및 활용
- 실시간 위협 탐지

**7일차: [고급 주제 및 실제 사례](day7-advanced-topics.md)**
- 성능 튜닝 및 문제 해결
- 대규모 배포 전략
- 실제 사용 사례 연구
- 미래 로드맵 및 발전 방향

## 추가 자료

- [네트워킹 개념 심층 분석](networking-concepts.md)
- [용어 및 약어](glossary.md)
