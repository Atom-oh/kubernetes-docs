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
5. [eBPF 기초와 실무 활용](./basics/05-ebpf-fundamentals.md) | [퀴즈](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

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

### EKS Hybrid Nodes
1. [EKS Hybrid Nodes 소개](./eks-hybrid-nodes/README.md)
2. [사전 요구 사항](./eks-hybrid-nodes/01-prerequisites.md) | [퀴즈](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [네트워크 구성](./eks-hybrid-nodes/02-network-configuration.md) | [퀴즈](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [에어갭 환경 구성](./eks-hybrid-nodes/03-airgap-setup.md) | [퀴즈](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [노드 부트스트랩](./eks-hybrid-nodes/04-node-bootstrap.md) | [퀴즈](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [GPU 서버 통합](./eks-hybrid-nodes/05-gpu-integration.md) | [퀴즈](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [워크로드 배치 전략](./eks-hybrid-nodes/06-workload-placement.md) | [퀴즈](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [운영 및 유지보수](./eks-hybrid-nodes/08-operations.md) | [퀴즈](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)

### EKS Auto Mode
1. [EKS Auto Mode 소개](./eks-auto-mode/README.md)
2. [Auto Mode 시작하기](./eks-auto-mode/01-getting-started.md) | [퀴즈](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [NodePool 구성](./eks-auto-mode/02-nodepool-configuration.md) | [퀴즈](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [스케일링 동작](./eks-auto-mode/03-scaling-behavior.md) | [퀴즈](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Spot 인스턴스 전략](./eks-auto-mode/04-spot-strategies.md) | [퀴즈](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [운영 및 관리](./eks-auto-mode/05-operations.md) | [퀴즈](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [비용 관리](./eks-auto-mode/06-cost-management.md) | [퀴즈](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [노드 생명주기](./eks-auto-mode/07-node-lifecycle.md) | [퀴즈](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [워크로드별 최적화](./eks-auto-mode/08-workload-optimization.md) | [퀴즈](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [마이그레이션 가이드](./eks-auto-mode/09-migration-guide.md) | [퀴즈](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### AI/ML
1. [AI/ML 워크로드](./ai-ml/01-ai-ml-workloads.md) | [퀴즈](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [vLLM 배포](./ai-ml/02-vllm-deployment.md) | [퀴즈](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
3. [Agentic AI 플랫폼](./ai-ml/03-agentic-ai-platform.md) | [퀴즈](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)

### Networking
1. [Networking 개요](./networking/README.md) | [퀴즈](./quizzes/networking/00-networking-overview-quiz.md)
2. [VPC CNI](./networking/01-vpc-cni.md) | [퀴즈](./quizzes/networking/01-vpc-cni-quiz.md)
3. **Cilium 딥다이브**
   - [Cilium 소개](./networking/cilium/README.md)
   - [Part 1: 소개](./networking/cilium/01-introduction.md) | [퀴즈](./quizzes/networking/cilium/01-introduction-quiz.md)
   - [Part 2: eBPF](./networking/cilium/02-ebpf.md) | [퀴즈](./quizzes/networking/cilium/02-ebpf-quiz.md)
   - [Part 3: 네트워킹](./networking/cilium/03-networking.md) | [퀴즈](./quizzes/networking/cilium/03-networking-quiz.md)
   - [Part 4: IPAM 및 정책](./networking/cilium/04-ipam-policy.md) | [퀴즈](./quizzes/networking/cilium/04-ipam-policy-quiz.md)
   - [Part 5: L2-L7 네트워킹](./networking/cilium/05-l2-l7-networking.md) | [퀴즈](./quizzes/networking/cilium/05-l2-l7-networking-quiz.md)
   - [Part 6: 보안 및 가시성](./networking/cilium/06-security-visibility.md) | [퀴즈](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [Part 7: 고급 주제](./networking/cilium/07-advanced-topics.md) | [퀴즈](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [네트워킹 개념](./networking/cilium/networking-concepts.md) | [퀴즈](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [용어집](./networking/cilium/glossary.md) | [퀴즈](./quizzes/networking/cilium/glossary-quiz.md)
4. **Calico 딥다이브**
   - [Calico 소개](./networking/calico/README.md)
   - [Part 1: 소개](./networking/calico/01-introduction.md) | [퀴즈](./quizzes/networking/calico/01-introduction-quiz.md)
   - [Part 2: 아키텍처](./networking/calico/02-architecture.md) | [퀴즈](./quizzes/networking/calico/02-architecture-quiz.md)
   - [Part 3: 네트워킹 모드](./networking/calico/03-networking-modes.md) | [퀴즈](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [Part 4: BGP 심화](./networking/calico/04-bgp-deep-dive.md) | [퀴즈](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [Part 5: Network Policy](./networking/calico/05-network-policy.md) | [퀴즈](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [Part 6: eBPF 데이터플레인](./networking/calico/06-ebpf-dataplane.md) | [퀴즈](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [Part 7: 고급 주제](./networking/calico/07-advanced-topics.md) | [퀴즈](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [Part 8: EKS 통합](./networking/calico/08-eks-integration.md) | [퀴즈](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [Part 9: 운영](./networking/calico/09-operations.md) | [퀴즈](./quizzes/networking/calico/09-operations-quiz.md)
   - [용어집](./networking/calico/glossary.md) | [퀴즈](./quizzes/networking/calico/glossary-quiz.md)
5. [VPC Lattice](./networking/02-vpc-lattice.md) | [퀴즈](./quizzes/networking/02-vpc-lattice-quiz.md)
6. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [퀴즈](./quizzes/networking/03-aws-lb-controller-quiz.md)
7. [Gateway API](./networking/04-gateway-api.md) | [퀴즈](./quizzes/networking/04-gateway-api-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [퀴즈](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Linkerd 소개](./service-mesh/linkerd/README.md)
   - [설치](./service-mesh/linkerd/01-installation.md) | [퀴즈](./quizzes/service-mesh/linkerd/installation.md)
   - [아키텍처](./service-mesh/linkerd/02-architecture.md) | [퀴즈](./quizzes/service-mesh/linkerd/architecture.md)
   - [트래픽 관리](./service-mesh/linkerd/03-traffic-management.md) | [퀴즈](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [보안](./service-mesh/linkerd/04-security.md) | [퀴즈](./quizzes/service-mesh/linkerd/security.md)
   - [관측성](./service-mesh/linkerd/05-observability.md) | [퀴즈](./quizzes/service-mesh/linkerd/observability.md)
   - [멀티클러스터](./service-mesh/linkerd/06-multi-cluster.md) | [퀴즈](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [모범 사례](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Cilium Service Mesh 소개](./service-mesh/cilium-service-mesh/README.md)
   - [아키텍처](./service-mesh/cilium-service-mesh/01-architecture.md) | [퀴즈](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [트래픽 관리](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [퀴즈](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [보안](./service-mesh/cilium-service-mesh/03-security.md) | [퀴즈](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [관측성](./service-mesh/cilium-service-mesh/04-observability.md) | [퀴즈](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [퀴즈](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [모범 사례](./service-mesh/cilium-service-mesh/06-best-practices.md)

### Security & Policy
1. [Kyverno를 사용한 정책 관리](./security/01-kyverno-policy-management.md) | [퀴즈](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Kubernetes 인증 및 권한 부여](./security/02-kubernetes-auth-authz.md) | [퀴즈](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Pod Security Standards](./security/03-pod-security-standards.md) | [퀴즈](./quizzes/security/03-pod-security-standards-quiz.md)
4. [네트워크 정책](./security/04-network-policies.md) | [퀴즈](./quizzes/security/04-network-policies-quiz.md)
5. [시크릿 관리](./security/05-secrets-management.md) | [퀴즈](./quizzes/security/05-secrets-management-quiz.md)
6. [EKS 보안 모범 사례](./security/06-eks-security-best-practices.md) | [퀴즈](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [이미지 보안](./security/07-image-security.md) | [퀴즈](./quizzes/security/07-image-security-quiz.md)
8. [런타임 보안](./security/08-runtime-security.md) | [퀴즈](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [퀴즈](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [퀴즈](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [퀴즈](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [퀴즈](./quizzes/security/12-spiffe-spire-quiz.md)

### Container Registry
1. [컨테이너 레지스트리 개요](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [퀴즈](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [퀴즈](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [퀴즈](./quizzes/container-registry/03-harbor-quiz.md)
5. [컨테이너 레지스트리 모범 사례](./container-registry/04-best-practices.md) | [퀴즈](./quizzes/container-registry/04-best-practices-quiz.md)

### GitOps
1. [GitOps 개요](./gitops/README.md)
2. **ArgoCD**
   - [ArgoCD 소개](./gitops/argocd/README.md) | [퀴즈](./quizzes/gitops/01-argocd-quiz.md)
   - [설치](./gitops/argocd/01-installation.md) | [퀴즈](./quizzes/gitops/argocd/01-installation-quiz.md)
   - [애플리케이션](./gitops/argocd/02-applications.md) | [퀴즈](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [동기화 전략](./gitops/argocd/03-sync-strategies.md) | [퀴즈](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSets](./gitops/argocd/04-applicationsets.md) | [퀴즈](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [트래픽 관리](./gitops/argocd/05-traffic-management.md) | [퀴즈](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [프로젝트 및 RBAC](./gitops/argocd/06-projects-rbac.md) | [퀴즈](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [보안](./gitops/argocd/07-security.md) | [퀴즈](./quizzes/gitops/argocd/07-security-quiz.md)
   - [알림](./gitops/argocd/08-notifications.md) | [퀴즈](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [모범 사례](./gitops/argocd/09-best-practices.md) | [퀴즈](./quizzes/gitops/argocd/09-best-practices-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [퀴즈](./quizzes/gitops/02-fluxcd-quiz.md)
4. [GitOps 도구 비교](./gitops/03-gitops-comparison.md) | [퀴즈](./quizzes/gitops/03-gitops-comparison-quiz.md)

### Autoscaling
1. [KEDA](./autoscaling/01-keda.md) | [퀴즈](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [퀴즈](./quizzes/autoscaling/06-karpenter-quiz.md)

### Observability
1. [Observability 개요](./observability/README.md)
2. **Metrics**
   - [메트릭 개요](./observability/metrics/README.md) | [퀴즈](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [퀴즈](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [퀴즈](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [퀴즈](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [퀴즈](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [퀴즈](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **Logging**
   - [로깅 개요](./observability/logging/README.md) | [퀴즈](./quizzes/observability/logging/README-quiz.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [퀴즈](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [퀴즈](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [퀴즈](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [퀴즈](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [Log Collectors](./observability/logging/05-collectors.md) | [퀴즈](./quizzes/observability/logging/05-collectors-quiz.md)
4. **Tracing**
   - [트레이싱 개요](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [퀴즈](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [퀴즈](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [퀴즈](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [퀴즈](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **Alerting**
   - [알림 개요](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [퀴즈](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [퀴즈](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [퀴즈](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [퀴즈](./quizzes/observability/grafana/grafana-quiz.md)
7. [관측성 최적화 가이드](./observability/09-observability-optimization.md) | [퀴즈](./quizzes/observability/09-observability-optimization-quiz.md)

### Scheduling
1. Custom Scheduler
   - [Part 1: Custom Scheduler 기초](./scheduling/01-custom-scheduler-part1.md) | [퀴즈](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [Part 2: 스케줄러 확장 및 프레임워크](./scheduling/02-custom-scheduler-part2.md) | [퀴즈](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [Part 3: 커스텀 스케줄러 구현 사례 및 모니터링](./scheduling/03-custom-scheduler-part3.md) | [퀴즈](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### Platform Engineering
0. [Platform Engineering 개요](./platform-engineering/00-platform-engineering-overview.md) | [퀴즈](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
1. [Helm](./platform-engineering/01-helm.md) | [퀴즈](./quizzes/platform-engineering/01-helm-quiz.md)
2. [AWS Controllers for Kubernetes (ACK)](./platform-engineering/02-ack.md) | [퀴즈](./quizzes/platform-engineering/02-ack-quiz.md)
3. [Kubernetes Resource Operator (KRO)](./platform-engineering/03-kro.md) | [퀴즈](./quizzes/platform-engineering/03-kro-quiz.md)
4. [Kubernetes 확장 메커니즘](./platform-engineering/04-kubernetes-extensions.md) | [퀴즈](./quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
5. [ExampleCorp: ACK + KRO 통합 예제](./platform-engineering/05-example-corp-app.md)

### 운영 가이드
1. [인프라 구성 기초](./ops/01-infrastructure-setup.md) | [퀴즈](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [인프라 구성 고급](./ops/02-infrastructure-advanced.md) | [퀴즈](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [CI 파이프라인 구성](./ops/03-ci-pipelines.md) | [퀴즈](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps 멀티 클러스터](./ops/04-gitops-multi-cluster.md) | [퀴즈](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [GitOps 자동화](./ops/05-gitops-automation.md) | [퀴즈](./quizzes/ops/05-gitops-automation-quiz.md)
6. [스케일링 전략](./ops/06-scaling-strategies.md) | [퀴즈](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [Observability 알림 설정](./ops/07-observability-alerts.md) | [퀴즈](./quizzes/ops/07-observability-alerts-quiz.md)
8. [Observability 분석 방법](./ops/08-observability-analysis.md) | [퀴즈](./quizzes/ops/08-observability-analysis-quiz.md)
9. [Observability 스택 구성](./ops/09-observability-stack.md) | [퀴즈](./quizzes/ops/09-observability-stack-quiz.md)
10. [리소스 최적화](./ops/10-resource-optimization.md) | [퀴즈](./quizzes/ops/10-resource-optimization-quiz.md)
11. [EKS 업그레이드 운영](./ops/11-upgrade-operations.md) | [퀴즈](./quizzes/ops/11-upgrade-operations-quiz.md)

## 실습 가이드

이론 학습 후 실제 환경에서 실습할 수 있는 가이드를 제공합니다.

- [실습 가이드 목록](./labs/README.md)
- 기초: Linux 기초, Linux 실무, 컨테이너 실습
- 핵심: Pod, Service, Storage, ConfigMap 실습
- EKS: 클러스터 생성 실습

### Observability End-to-End 실습
1. [실습 시리즈 소개](./labs/observability/README.md)
2. [Part 1: 인프라 구성](./labs/observability/01-infrastructure-setup-lab.md) | [퀴즈](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [Part 2: Observability 스택](./labs/observability/02-observability-stack-lab.md) | [퀴즈](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [Part 3: MSA 배포 및 카나리](./labs/observability/03-msa-deployment-lab.md) | [퀴즈](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [Part 4: 부하 테스트 및 스케일링](./labs/observability/04-load-testing-scaling-lab.md) | [퀴즈](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [Part 5: 알림 및 AIOps](./labs/observability/05-alerting-aiops-lab.md) | [퀴즈](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [Part 6: 분산 추적 분석](./labs/observability/06-distributed-tracing-lab.md) | [퀴즈](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

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

