# Kubernetes 및 EKS 교육 컨텐츠 퀴즈

이 디렉토리는 Kubernetes 및 Amazon EKS 교육 컨텐츠에 대한 퀴즈를 포함하고 있습니다. 각 퀴즈는 해당 주제에 대한 이해도를 테스트하고 핵심 개념을 강화하는 데 도움이 됩니다.

## 퀴즈 구성

각 퀴즈는 다음과 같은 구조로 구성되어 있습니다:
- 객관식 문제
- 단답형 문제
- 실습 문제 (해당되는 경우)
- 심화 문제 (해당되는 경우)

모든 퀴즈 문제에는 토글 형태로 답변이 포함되어 있어, 먼저 문제를 풀어본 후 답변을 확인할 수 있습니다.

## 퀴즈 목록

### 기초 개념
- [Linux 기초 퀴즈](./basics/01-linux-basics-quiz.md)
- [컨테이너 기술 퀴즈](./basics/02-container-technology-quiz.md)
- [Kubernetes 소개 퀴즈](./basics/03-kubernetes-introduction-quiz.md)

### Kubernetes 핵심 개념
- [클러스터 아키텍처 퀴즈](./core/01-cluster-architecture-quiz.md)
- [파드와 워크로드 퀴즈](./core/02-pods-and-workloads-quiz.md)
- [서비스와 네트워킹 퀴즈](./core/03-services-and-networking-quiz.md)
- [스토리지 퀴즈](./core/04-storage-quiz.md)
- [구성 퀴즈](./core/05-configuration-secrets-quiz.md)
- [보안 퀴즈](./core/06-security-quiz.md)
- [정책 퀴즈](./core/07-policies-quiz.md)
- [스케줄링, 선점 및 축출 퀴즈](./core/08-scheduling-preemption-eviction-quiz.md)
- [클러스터 관리 퀴즈](./core/09-cluster-administration-quiz.md)
- [Windows in Kubernetes 퀴즈](./core/10-windows-in-kubernetes-quiz.md)
- [Kubernetes 확장 퀴즈](./core/11-extending-kubernetes-quiz.md)

### Amazon EKS
- [EKS 소개 퀴즈](./eks/01-eks-introduction-quiz.md)
- [EKS 클러스터 생성 퀴즈 - Part 1](./eks/02-eks-cluster-creation-part1-quiz.md)
- [EKS 클러스터 생성 퀴즈 - Part 2](./eks/02-eks-cluster-creation-part2-quiz.md)
- [EKS 클러스터 생성 퀴즈 - Part 3](./eks/02-eks-cluster-creation-part3-quiz.md)
- [EKS 클러스터 생성 퀴즈 - Part 4](./eks/02-eks-cluster-creation-part4-quiz.md)
- [EKS 클러스터 생성 퀴즈 - Part 5](./eks/02-eks-cluster-creation-part5-quiz.md)
- [EKS 네트워킹 퀴즈](./eks/03-eks-networking-quiz.md)
- [EKS 스토리지 퀴즈](./eks/04-eks-storage-quiz.md)
- [EKS 보안 퀴즈](./eks/05-eks-security-quiz.md)
- [EKS 모니터링 및 로깅 퀴즈](./eks/06-eks-monitoring-logging-quiz.md)
- [EKS 비용 최적화 퀴즈](./eks/07-eks-cost-optimization-quiz.md)
- [EKS 업그레이드 퀴즈](./eks/08-eks-upgrades-quiz.md)
- [EKS 문제 해결 퀴즈](./eks/09-eks-troubleshooting-quiz.md)

### Cilium
- [Cilium 소개 퀴즈](./cilium/00-cilium-introduction-quiz.md)
- [Day 1: 소개 퀴즈](./cilium/01-day1-introduction-quiz.md)
- [Day 2: eBPF 퀴즈](./cilium/02-day2-ebpf-quiz.md)
- [Day 3: 네트워킹 퀴즈](./cilium/03-day3-networking-quiz.md)
- [Day 4: IPAM 및 정책 퀴즈](./cilium/04-day4-ipam-policy-quiz.md)
- [Day 5: L2-L7 네트워킹 퀴즈](./cilium/05-day5-l2-l7-networking-quiz.md)
- [Day 6: 보안 및 가시성 퀴즈](./cilium/06-day6-security-visibility-quiz.md)
- [Day 7: 고급 주제 퀴즈](./cilium/07-day7-advanced-topics-quiz.md)
- [네트워킹 개념 퀴즈](./cilium/08-networking-concepts-quiz.md)

### 고급 주제
- [Kyverno를 사용한 정책 관리 퀴즈](./advanced/01-kyverno-policy-management-quiz.md)
- [Custom Scheduler 퀴즈](./advanced/02-custom-scheduler-quiz.md)
- [AI/ML 워크로드 퀴즈](./advanced/03-ai-ml-workloads-quiz.md)
- [vLLM 배포 퀴즈](./advanced/04-vllm-deployment-quiz.md)

### 도구 및 통합
- [ArgoCD 퀴즈](./tools/01-argocd-quiz.md)
- [Istio 퀴즈](./tools/02-istio-quiz.md)
- [AWS Controllers for Kubernetes (ACK) 퀴즈](./tools/03-ack-quiz.md)
- [Cilium 퀴즈](./tools/04-cilium-quiz.md)
- [KEDA 퀴즈](./tools/05-keda-quiz.md)
- [Karpenter 퀴즈](./tools/06-karpenter-quiz.md)
- [모니터링 스택 퀴즈](./tools/07-monitoring-stack-quiz.md)
- [로깅 스택 퀴즈](./tools/08-logging-stack-quiz.md)
- [VPC Lattice 퀴즈](./tools/09-vpc-lattice-quiz.md)

## 퀴즈 사용 방법

1. 해당 주제의 학습 자료를 먼저 읽습니다.
2. 퀴즈를 풀어 이해도를 테스트합니다.
3. 답변을 확인하려면 각 문제 아래의 "정답 보기" 토글을 클릭합니다.
4. 필요한 경우 학습 자료로 돌아가 개념을 복습합니다.
