# Kubernetes 및 Amazon EKS 교육 컨텐츠
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

이 저장소는 Kubernetes와 Amazon EKS에 대한 포괄적인 교육 자료를 제공합니다. Linux 기초부터 컨테이너화, Kubernetes 오케스트레이션, 그리고 Amazon EKS의 고급 기능까지 다룹니다.

## 학습 자료 및 퀴즈

이 교육 컨텐츠는 학습 자료와 함께 각 주제에 대한 퀴즈를 제공합니다. 퀴즈를 통해 학습한 내용을 테스트하고 강화할 수 있습니다. 각 퀴즈는 토글 형태로 답변을 가려서 보여주는 방식으로 구성되어 있어, 먼저 문제를 풀어본 후 답변을 확인할 수 있습니다.

- [학습 자료 목차](#목차) - 주제별 학습 자료
- [퀴즈 모음](./quizzes/README.md) - 주제별 퀴즈

## 목차

### 기초 개념
1. [Linux 기초](./basics/01-linux-basics.md)
2. [컨테이너 기술](./basics/02-container-technology.md)
3. [Kubernetes 소개](./basics/03-kubernetes-introduction.md)

### Kubernetes 핵심 개념
1. [클러스터 아키텍처](./core/01-cluster-architecture.md)
2. [파드와 워크로드](./core/02-pods-and-workloads.md)
3. [서비스와 네트워킹](./core/03-services-and-networking.md)
4. [스토리지](./core/04-storage.md)
5. [구성](./core/05-configuration-secrets.md)
6. [보안](./core/06-security.md)
7. [정책](./core/07-policies.md)
8. [스케줄링, 선점 및 축출](./core/08-scheduling-preemption-eviction.md)
9. [클러스터 관리](./core/09-cluster-administration.md)
10. [Windows in Kubernetes](./core/10-windows-in-kubernetes.md)
11. [Kubernetes 확장](./core/11-extending-kubernetes.md)

### Amazon EKS
1. [EKS 소개](./eks/01-eks-introduction.md)
2. [EKS 클러스터 생성](./eks/02-eks-cluster-creation-part1.md)
   - [Part 1: 사전 요구 사항](./eks/02-eks-cluster-creation-part1.md)
   - [Part 2: eksctl을 사용한 클러스터 생성](./eks/02-eks-cluster-creation-part2.md)
   - [Part 3: AWS Management Console 및 CLI를 사용한 클러스터 생성](./eks/02-eks-cluster-creation-part3.md)
   - [Part 4: Terraform 및 CDK를 사용한 클러스터 생성](./eks/02-eks-cluster-creation-part4.md)
   - [Part 5: 클러스터 액세스, 검증, 업그레이드 및 삭제](./eks/02-eks-cluster-creation-part5.md)
3. EKS 네트워킹
   - [Part 1: 기본 개념 및 VPC 구성](./eks/03-eks-networking-part1.md)
   - [Part 2: 서비스 및 로드 밸런싱, 네트워크 정책](./eks/03-eks-networking-part2.md)
   - [Part 3: 성능 최적화, 문제 해결, 고급 사용 사례](./eks/03-eks-networking-part3.md)
4. EKS 스토리지
   - [Part 1: 기본 개념, EBS, EFS](./eks/04-eks-storage-part1.md)
   - [Part 2: FSx for Lustre, S3, 스냅샷, 볼륨 확장, 성능 최적화](./eks/04-eks-storage-part2.md)
   - [Part 3: 모니터링, 문제 해결, 비용 최적화, 보안](./eks/04-eks-storage-part3.md)
5. [EKS 보안](./eks/05-eks-security.md)
6. [EKS 모니터링 및 로깅](./eks/06-eks-monitoring-logging.md)
7. [EKS 비용 최적화](./eks/07-eks-cost-optimization.md)
8. [EKS 업그레이드](./eks/08-eks-upgrades.md)
9. [EKS 문제 해결](./eks/09-eks-troubleshooting.md)

## Cilium
* [Cilium 소개](./cilium/README.md)
   * [Part 1: 소개](./cilium/01-introduction.md)
   * [Part 2: eBPF](./cilium/02-ebpf.md)
   * [Part 3: 네트워킹](./cilium/03-networking.md)
   * [Part 4: IPAM 및 정책](./cilium/04-ipam-policy.md)
   * [Part 5: L2-L7 네트워킹](./cilium/05-l2-l7-networking.md)
   * [Part 6: 보안 및 가시성](./cilium/06-security-visibility.md)
   * [Part 7: 고급 주제](./cilium/07-advanced-topics.md)
* [네트워킹 개념](./cilium/networking-concepts.md)
* [용어집](./cilium/glossary.md)

### 고급 주제
1. [Kyverno를 사용한 정책 관리](./advanced/01-kyverno-policy-management.md)
2. [커스텀 스케줄러](./advanced/02-custom-scheduler.md)
3. [AI/ML 워크로드](./advanced/03-ai-ml-workloads.md)
4. [vLLM 배포](./advanced/04-vllm-deployment.md)

### 도구 및 통합
1. [ArgoCD](./tools/01-argocd.md)
2. [Istio](./tools/02-istio.md)
3. [AWS Controllers for Kubernetes (ACK)](./tools/03-ack.md)
4. [Cilium](./tools/04-cilium.md)
5. [KEDA](./tools/05-keda.md)
6. [Karpenter](./tools/06-karpenter.md)
7. [모니터링 스택 (VictoriaMetrics, Prometheus, Grafana)](./tools/07-monitoring-stack.md)
8. [로깅 스택 (Loki, Tempo)](./tools/08-logging-stack.md)
9. [VPC Lattice](./tools/09-vpc-lattice.md)

