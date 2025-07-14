# Kubernetes 및 Amazon EKS 교육 컨텐츠

이 저장소는 Kubernetes와 Amazon EKS에 대한 포괄적인 교육 자료를 제공합니다. Linux 기초부터 컨테이너화, Kubernetes 오케스트레이션, 그리고 Amazon EKS의 고급 기능까지 다룹니다.

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
3. [EKS 네트워킹](./eks/03-eks-networking.md)
4. [EKS 스토리지](./eks/04-eks-storage.md)
5. [EKS 보안](./eks/05-eks-security.md)
6. [EKS 모니터링 및 로깅](./eks/06-eks-monitoring-logging.md)
7. [EKS 비용 최적화](./eks/07-eks-cost-optimization.md)
8. [EKS 업그레이드](./eks/08-eks-upgrades.md)
9. [EKS 문제 해결](./eks/09-eks-troubleshooting.md)

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

