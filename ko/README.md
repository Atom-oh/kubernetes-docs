> [English Version](https://atomoh.gitbook.io/kubernetes-docs-en/)

# Kubernetes 및 Amazon EKS 교육 컨텐츠
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

이 저장소는 Kubernetes와 Amazon EKS에 대한 포괄적인 교육 자료를 제공합니다. Linux 기초부터 컨테이너화, Kubernetes 오케스트레이션, 그리고 Amazon EKS의 고급 기능까지 다룹니다.

## 학습 자료 및 퀴즈

이 교육 컨텐츠는 학습 자료와 함께 각 주제에 대한 퀴즈를 제공합니다. 퀴즈를 통해 학습한 내용을 테스트하고 강화할 수 있습니다. 각 퀴즈는 토글 형태로 답변을 가려서 보여주는 방식으로 구성되어 있어, 먼저 문제를 풀어본 후 답변을 확인할 수 있습니다.

- [학습 자료 목차](#목차) - 주제별 학습 자료
- [퀴즈 모음](./quizzes/README.md) - 주제별 퀴즈

## 목차

### 기초 개념
1. [Linux 기초](./basics/01-linux-basics.md) | [퀴즈](./quizzes/basics/01-linux-basics-quiz.md) | [실습](./labs/basics/01-linux-basics-lab.md)
2. [Linux 운영 기술](./basics/02-linux-advanced.md) | [퀴즈](./quizzes/basics/02-linux-advanced-quiz.md) | [실습](./labs/basics/02-linux-advanced-lab.md)
3. [컨테이너 기술](./basics/03-container-technology.md) | [퀴즈](./quizzes/basics/03-container-technology-quiz.md) | [실습](./labs/basics/03-container-technology-lab.md)
4. [Kubernetes 소개](./basics/04-kubernetes-introduction.md) | [퀴즈](./quizzes/basics/04-kubernetes-introduction-quiz.md)

### Kubernetes 핵심 개념
1. [클러스터 아키텍처](./core/01-cluster-architecture.md) | [퀴즈](./quizzes/core/01-cluster-architecture-quiz.md)
2. [파드와 워크로드](./core/02-pods-and-workloads.md) | [퀴즈](./quizzes/core/02-pods-and-workloads-quiz.md)
3. [서비스와 네트워킹](./core/03-services-networking.md) | [퀴즈](./quizzes/core/03-services-networking-quiz.md)
4. [스토리지](./core/04-storage.md) | [퀴즈](./quizzes/core/04-storage-quiz.md)
5. [구성](./core/05-configuration-secrets.md) | [퀴즈](./quizzes/core/05-configuration-secrets-quiz.md)
6. [보안](./core/06-security.md) | [퀴즈](./quizzes/core/06-security-quiz.md)
7. [정책](./core/07-policies.md) | [퀴즈](./quizzes/core/07-policies-quiz.md)
8. [스케줄링, 선점 및 축출](./core/08-scheduling-preemption-eviction.md) | [퀴즈](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
9. [클러스터 관리](./core/09-cluster-administration.md) | [퀴즈](./quizzes/core/09-cluster-administration-quiz.md)
10. [Windows in Kubernetes](./core/10-windows-in-kubernetes.md) | [퀴즈](./quizzes/core/10-windows-in-kubernetes-quiz.md)
11. [Kubernetes 확장](./core/11-extending-kubernetes.md) | [퀴즈](./quizzes/core/11-extending-kubernetes-quiz.md)

### Amazon EKS
1. [EKS 소개](./eks/01-eks-introduction.md) | [퀴즈](./quizzes/eks/01-eks-introduction-quiz.md)
2. EKS 클러스터 생성
   - [Part 1: 사전 요구 사항](./eks/02-eks-cluster-creation-part1.md) | [퀴즈](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [Part 2: eksctl을 사용한 클러스터 생성](./eks/02-eks-cluster-creation-part2.md) | [퀴즈](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [Part 3: AWS Management Console 및 CLI를 사용한 클러스터 생성](./eks/02-eks-cluster-creation-part3.md) | [퀴즈](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [Part 4: Terraform 및 CDK를 사용한 클러스터 생성](./eks/02-eks-cluster-creation-part4.md) | [퀴즈](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [Part 5: 클러스터 액세스, 검증, 업그레이드 및 삭제](./eks/02-eks-cluster-creation-part5.md) | [퀴즈](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. EKS 네트워킹
   - [Part 1: 기본 개념 및 VPC 구성](./eks/03-eks-networking-part1.md) | [퀴즈](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [Part 2: 서비스 및 로드 밸런싱, 네트워크 정책](./eks/03-eks-networking-part2.md) | [퀴즈](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [Part 3: 성능 최적화, 문제 해결, 고급 사용 사례](./eks/03-eks-networking-part3.md) | [퀴즈](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. EKS 스토리지
   - [Part 1: 기본 개념, EBS, EFS](./eks/04-eks-storage-part1.md) | [퀴즈](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [Part 2: FSx for Lustre, S3, 스냅샷, 볼륨 확장, 성능 최적화](./eks/04-eks-storage-part2.md) | [퀴즈](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [Part 3: 모니터링, 문제 해결, 비용 최적화, 보안](./eks/04-eks-storage-part3.md) | [퀴즈](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [EKS 보안](./eks/05-eks-security.md) | [퀴즈](./quizzes/eks/05-eks-security-quiz.md)
6. [EKS 모니터링 및 로깅](./eks/06-eks-monitoring-logging.md) | [퀴즈](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [EKS 비용 최적화](./eks/07-eks-cost-optimization.md) | [퀴즈](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [EKS 업그레이드](./eks/08-eks-upgrades.md) | [퀴즈](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [EKS 문제 해결](./eks/09-eks-troubleshooting.md) | [퀴즈](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [EKS 복원력과 고가용성](./eks/10-eks-resiliency.md) | [퀴즈](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [EKS 고급 디버깅](./eks/11-eks-advanced-debugging.md) | [퀴즈](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [EKS Hybrid Nodes](./eks/12-eks-hybrid-nodes.md) | [퀴즈](./quizzes/eks/12-eks-hybrid-nodes-quiz.md)

### Cilium
1. [Cilium 소개](./cilium/README.md)
2. [Part 1: 소개](./cilium/01-introduction.md) | [퀴즈](./quizzes/cilium/01-introduction-quiz.md)
3. [Part 2: eBPF](./cilium/02-ebpf.md) | [퀴즈](./quizzes/cilium/02-ebpf-quiz.md)
4. [Part 3: 네트워킹](./cilium/03-networking.md) | [퀴즈](./quizzes/cilium/03-networking-quiz.md)
5. [Part 4: IPAM 및 정책](./cilium/04-ipam-policy.md) | [퀴즈](./quizzes/cilium/04-ipam-policy-quiz.md)
6. [Part 5: L2-L7 네트워킹](./cilium/05-l2-l7-networking.md) | [퀴즈](./quizzes/cilium/05-l2-l7-networking-quiz.md)
7. [Part 6: 보안 및 가시성](./cilium/06-security-visibility.md) | [퀴즈](./quizzes/cilium/06-security-visibility-quiz.md)
8. [Part 7: 고급 주제](./cilium/07-advanced-topics.md) | [퀴즈](./quizzes/cilium/07-advanced-topics-quiz.md)
9. [네트워킹 개념](./cilium/networking-concepts.md) | [퀴즈](./quizzes/cilium/networking-concepts-quiz.md)
10. [용어집](./cilium/glossary.md) | [퀴즈](./quizzes/cilium/glossary-quiz.md)

### AI/ML
1. [AI/ML 워크로드](./ai-ml/01-ai-ml-workloads.md) | [퀴즈](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [vLLM 배포](./ai-ml/02-vllm-deployment.md) | [퀴즈](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
3. [Agentic AI 플랫폼](./ai-ml/03-agentic-ai-platform.md) | [퀴즈](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)

### Networking
1. [Cilium](./networking/01-cilium.md) | [퀴즈](./quizzes/networking/04-cilium-quiz.md)
2. [VPC Lattice](./networking/02-vpc-lattice.md) | [퀴즈](./quizzes/networking/09-vpc-lattice-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/02-istio.md) | [퀴즈](./quizzes/service-mesh/02-istio-quiz.md)

### Security & Policy
1. [Kyverno를 사용한 정책 관리](./security/01-kyverno-policy-management.md) | [퀴즈](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Kubernetes 인증 및 권한 부여](./security/02-kubernetes-auth-authz.md) | [퀴즈](./quizzes/security/06-kubernetes-auth-authz-quiz.md)

### GitOps
1. [ArgoCD](./gitops/01-argocd.md) | [퀴즈](./quizzes/gitops/01-argocd-quiz.md)

### Autoscaling
1. [KEDA](./autoscaling/01-keda.md) | [퀴즈](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [퀴즈](./quizzes/autoscaling/06-karpenter-quiz.md)

### Observability
1. [모니터링 스택 (VictoriaMetrics, Prometheus, Grafana)](./observability/01-monitoring-stack.md) | [퀴즈](./quizzes/observability/07-monitoring-stack-quiz.md)
2. [로깅 스택 (Loki, Tempo)](./observability/02-logging-stack.md) | [퀴즈](./quizzes/observability/08-logging-stack-quiz.md)

### Scheduling
1. Custom Scheduler
   - [Part 1: Custom Scheduler 기초](./scheduling/01-custom-scheduler-part1.md) | [퀴즈](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [Part 2: 스케줄러 확장 및 프레임워크](./scheduling/02-custom-scheduler-part2.md) | [퀴즈](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [Part 3: 커스텀 스케줄러 구현 사례 및 모니터링](./scheduling/03-custom-scheduler-part3.md) | [퀴즈](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### Package Management
1. [Helm](./package-management/01-helm.md) | [퀴즈](./quizzes/package-management/10-helm-quiz.md)
2. [KRO를 활용한 Helm 차트 마이그레이션](./package-management/02-kro-helm-migration.md) | [퀴즈](./quizzes/package-management/05-kro-helm-migration-quiz.md)

### Platform & AWS Integration
1. [AWS Controllers for Kubernetes (ACK)](./platform/01-ack.md) | [퀴즈](./quizzes/platform/03-ack-quiz.md)
2. [Kubernetes 확장 메커니즘](./platform/02-kubernetes-extensions.md) | [퀴즈](./quizzes/platform/07-kubernetes-extensions-quiz.md)

## 실습 가이드

이론 학습 후 실제 환경에서 실습할 수 있는 가이드를 제공합니다.

- [실습 가이드 목록](./labs/README.md)
- 기초: Linux 기초, Linux 실무, 컨테이너 실습
- 핵심: Pod, Service, Storage, ConfigMap 실습
- EKS: 클러스터 생성 실습

## 학습 가이드

### 초보자를 위한 학습 순서
1. **기초 개념** → **Kubernetes 핵심 개념** → **Amazon EKS** 순서로 학습
2. 각 장을 읽은 후 해당 퀴즈를 풀어 이해도 확인
3. 실습 환경에서 직접 명령어와 예제 코드 실행

### 고급 사용자를 위한 학습 순서
1. **Amazon EKS** → **AI/ML** → **Service Mesh** → **Security & Policy** 순서로 학습
2. **Cilium** 섹션으로 네트워킹 심화 학습
3. 특정 도구나 기술에 집중하여 심화 학습

### 퀴즈 활용법
- 각 문서 마지막에 있는 퀴즈 링크를 클릭하여 학습 내용 확인
- 토글 형태로 구성된 답변을 먼저 생각해본 후 확인
- 틀린 문제는 해당 문서를 다시 읽어 복습

## 기여하기

이 프로젝트에 기여하고 싶으시다면:
1. 오타나 내용 오류 발견 시 이슈 등록
2. 새로운 주제나 개선사항 제안
3. 퀴즈 문제 추가나 개선 제안

## 라이선스

이 교육 자료는 학습 목적으로 자유롭게 사용할 수 있습니다.

