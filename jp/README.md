> [韓国語版](https://atomoh.gitbook.io/kubernetes-docs/)

# Kubernetes と Amazon EKS のトレーニングコンテンツ
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

このリポジトリは、Kubernetes と Amazon EKS に関する包括的なトレーニング教材を提供します。Linux の基礎からコンテナ化、Kubernetes オーケストレーション、Amazon EKS の高度な機能までを扱います。

## 学習教材とクイズ

このトレーニングコンテンツでは、学習教材とあわせて各トピックのクイズを提供します。クイズを通じて、学んだ内容を確認し定着させることができます。各クイズは、答えが隠されたトグル形式で設計されており、答えを表示する前にまず問題に取り組めます。

- [学習教材の目次](#table-of-contents) - トピック別の学習教材
- [クイズ集](./quizzes/README.md) - トピック別のクイズ

## 目次

### ニュース
- [週刊ニュース](./news/README.md) - 最新の Kubernetes/EKS エコシステムニュースダイジェスト

### 基本概念
1. [Linux の基礎](./basics/01-linux-basics.md) | [クイズ](./quizzes/basics/01-linux-basics-quiz.md) | [ラボ](./labs/basics/01-linux-basics-lab.md)
2. [Linux 運用スキル](./basics/02-linux-advanced.md) | [クイズ](./quizzes/basics/02-linux-advanced-quiz.md) | [ラボ](./labs/basics/02-linux-advanced-lab.md)
3. [Container 技術](./basics/03-container-technology.md) | [クイズ](./quizzes/basics/03-container-technology-quiz.md) | [ラボ](./labs/basics/03-container-technology-lab.md)
4. [Kubernetes 入門](./basics/04-kubernetes-introduction.md) | [クイズ](./quizzes/basics/04-kubernetes-introduction-quiz.md)
5. [eBPF の基礎と実践的な適用](./basics/05-ebpf-fundamentals.md) | [クイズ](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Kubernetes コア概念
1. [Cluster Architecture](./core/01-cluster-architecture.md) | [クイズ](./quizzes/core/01-cluster-architecture-quiz.md)
2. [Pod と Workload](./core/02-pods-and-workloads.md) | [クイズ](./quizzes/core/02-pods-and-workloads-quiz.md)
3. [Service と Networking](./core/03-services-networking.md) | [クイズ](./quizzes/core/03-services-networking-quiz.md)
4. [Storage](./core/04-storage.md) | [クイズ](./quizzes/core/04-storage-quiz.md)
5. [Configuration](./core/05-configuration-secrets.md) | [クイズ](./quizzes/core/05-configuration-secrets-quiz.md)
6. [Security](./core/06-security.md) | [クイズ](./quizzes/core/06-security-quiz.md)
7. [Policies](./core/07-policies.md) | [クイズ](./quizzes/core/07-policies-quiz.md)
8. [Scheduling、Preemption、Eviction](./core/08-scheduling-preemption-eviction.md) | [クイズ](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
9. [Cluster Administration](./core/09-cluster-administration.md) | [クイズ](./quizzes/core/09-cluster-administration-quiz.md)
10. [Kubernetes における Windows](./core/10-windows-in-kubernetes.md) | [クイズ](./quizzes/core/10-windows-in-kubernetes-quiz.md)
11. [Kubernetes の拡張](./core/11-extending-kubernetes.md) | [クイズ](./quizzes/core/11-extending-kubernetes-quiz.md)

### Scheduling
1. Custom Scheduler
   - [パート 1: Custom Scheduler の基礎](./scheduling/01-custom-scheduler-part1.md) | [クイズ](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [パート 2: Scheduler Extensions と Framework](./scheduling/02-custom-scheduler-part2.md) | [クイズ](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [パート 3: Custom Scheduler の実装例と Monitoring](./scheduling/03-custom-scheduler-part3.md) | [クイズ](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### Autoscaling
1. [KEDA](./autoscaling/01-keda.md) | [クイズ](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [クイズ](./quizzes/autoscaling/06-karpenter-quiz.md)
3. [Knative](./autoscaling/03-knative.md) | [クイズ](./quizzes/autoscaling/03-knative-quiz.md)

### Amazon EKS
1. [EKS 入門](./eks/01-eks-introduction.md) | [クイズ](./quizzes/eks/01-eks-introduction-quiz.md)
2. EKS Cluster 作成
   - [パート 1: 前提条件](./eks/02-eks-cluster-creation-part1.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [パート 2: eksctl による Cluster 作成](./eks/02-eks-cluster-creation-part2.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [パート 3: AWS Management Console と CLI による Cluster 作成](./eks/02-eks-cluster-creation-part3.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [パート 4: Terraform と CDK による Cluster 作成](./eks/02-eks-cluster-creation-part4.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [パート 5: Cluster アクセス、検証、アップグレード、削除](./eks/02-eks-cluster-creation-part5.md) | [クイズ](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. EKS Networking
   - [パート 1: 基本概念と VPC Configuration](./eks/03-eks-networking-part1.md) | [クイズ](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [パート 2: Service と Load Balancing、Network Policies](./eks/03-eks-networking-part2.md) | [クイズ](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [パート 3: Performance Optimization、Troubleshooting、高度なユースケース](./eks/03-eks-networking-part3.md) | [クイズ](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. EKS Storage
   - [パート 1: 基本概念、EBS、EFS](./eks/04-eks-storage-part1.md) | [クイズ](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [パート 2: FSx for Lustre、S3、Snapshots、Volume Expansion、Performance Optimization](./eks/04-eks-storage-part2.md) | [クイズ](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [パート 3: Monitoring、Troubleshooting、Cost Optimization、Security](./eks/04-eks-storage-part3.md) | [クイズ](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [EKS Security](./eks/05-eks-security.md) | [クイズ](./quizzes/eks/05-eks-security-quiz.md)
6. [EKS Monitoring と Logging](./eks/06-eks-monitoring-logging.md) | [クイズ](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [EKS Cost Optimization](./eks/07-eks-cost-optimization.md) | [クイズ](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [EKS Upgrades](./eks/08-eks-upgrades.md) | [クイズ](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [EKS Troubleshooting](./eks/09-eks-troubleshooting.md) | [クイズ](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [EKS Resiliency と High Availability](./eks/10-eks-resiliency.md) | [クイズ](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [EKS Advanced Debugging](./eks/11-eks-advanced-debugging.md) | [クイズ](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [Kubernetes Version の機能と Roadmap](./eks/12-kubernetes-version-roadmap.md) | [クイズ](./quizzes/eks/12-kubernetes-version-roadmap-quiz.md)

### EKS Hybrid Nodes
1. [EKS Hybrid Nodes 入門](./eks-hybrid-nodes/README.md)
2. [前提条件](./eks-hybrid-nodes/01-prerequisites.md) | [クイズ](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [Network Configuration](./eks-hybrid-nodes/02-network-configuration.md) | [クイズ](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [Air-Gap Environment Setup](./eks-hybrid-nodes/03-airgap-setup.md) | [クイズ](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [Node Bootstrap](./eks-hybrid-nodes/04-node-bootstrap.md) | [クイズ](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [GPU Server Integration](./eks-hybrid-nodes/05-gpu-integration.md) | [クイズ](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [Workload Placement Strategies](./eks-hybrid-nodes/06-workload-placement.md) | [クイズ](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [Node Lifecycle Management](./eks-hybrid-nodes/07-node-lifecycle.md) | [クイズ](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [Operations と Maintenance](./eks-hybrid-nodes/08-operations.md) | [クイズ](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [Bare Metal OS Setup](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [クイズ](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Hybrid Nodes Gateway](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [クイズ](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

### EKS Auto Mode
1. [EKS Auto Mode 入門](./eks-auto-mode/README.md)
2. [はじめに](./eks-auto-mode/01-getting-started.md) | [クイズ](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [NodePool Configuration](./eks-auto-mode/02-nodepool-configuration.md) | [クイズ](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [Scaling Behavior](./eks-auto-mode/03-scaling-behavior.md) | [クイズ](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Spot Instance Strategies](./eks-auto-mode/04-spot-strategies.md) | [クイズ](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [Operations と Management](./eks-auto-mode/05-operations.md) | [クイズ](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [Cost Management](./eks-auto-mode/06-cost-management.md) | [クイズ](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [Node Lifecycle](./eks-auto-mode/07-node-lifecycle.md) | [クイズ](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [Workload Optimization](./eks-auto-mode/08-workload-optimization.md) | [クイズ](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [移行ガイド](./eks-auto-mode/09-migration-guide.md) | [クイズ](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### AI/ML
1. [AI/ML Workloads](./ai-ml/01-ai-ml-workloads.md) | [クイズ](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [AI Infrastructure](./ai-ml/06-ai-infrastructure.md) | [クイズ](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [EKS での Model Training](./ai-ml/05-model-training.md) | [クイズ](./quizzes/ai-ml/05-model-training-quiz.md)
4. [Inference Frameworks](./ai-ml/04-inference-frameworks.md) | [クイズ](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [vLLM Deployment と Optimization](./ai-ml/02-vllm-deployment.md) | [クイズ](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [EKS 上の Agentic AI Platform](./ai-ml/03-agentic-ai-platform.md) | [クイズ](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [AI/ML Best Practices](./ai-ml/07-ai-ml-best-practices.md) | [クイズ](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)

### Data on EKS
1. [Data on EKS 概要](./data-on-eks/README.md)
2. **Kafka on EKS 詳細解説**
   - [Kafka on EKS 入門](./data-on-eks/kafka/README.md)
   - [パート 1: Kafka Fundamentals](./data-on-eks/kafka/01-kafka-fundamentals.md) | [クイズ](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [パート 2: Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [クイズ](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [パート 3: Kafka Operations](./data-on-eks/kafka/03-kafka-operations.md) | [クイズ](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [パート 4: Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [クイズ](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [パート 5: Kafka Connect と MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [クイズ](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [パート 6: MSK Integration](./data-on-eks/kafka/06-msk-integration.md) | [クイズ](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [パート 7: Monitoring](./data-on-eks/kafka/07-monitoring.md) | [クイズ](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [パート 8: Best Practices](./data-on-eks/kafka/08-best-practices.md) | [クイズ](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)

### Networking
1. [Networking 概要](./networking/README.md) | [クイズ](./quizzes/networking/00-networking-overview-quiz.md)
2. [VPC CNI](./networking/01-vpc-cni.md) | [クイズ](./quizzes/networking/01-vpc-cni-quiz.md)
3. **Cilium 詳細解説**
   - [Cilium 入門](./networking/cilium/README.md)
   - [パート 1: 入門](./networking/cilium/01-introduction.md) | [クイズ](./quizzes/networking/cilium/01-introduction-quiz.md)
   - [パート 2: eBPF](./networking/cilium/02-ebpf.md) | [クイズ](./quizzes/networking/cilium/02-ebpf-quiz.md)
   - [パート 3: Networking](./networking/cilium/03-networking.md) | [クイズ](./quizzes/networking/cilium/03-networking-quiz.md)
   - [パート 4: IPAM と Policies](./networking/cilium/04-ipam-policy.md) | [クイズ](./quizzes/networking/cilium/04-ipam-policy-quiz.md)
   - [パート 5: L2-L7 Networking](./networking/cilium/05-l2-l7-networking.md) | [クイズ](./quizzes/networking/cilium/05-l2-l7-networking-quiz.md)
   - [パート 6: Security と Visibility](./networking/cilium/06-security-visibility.md) | [クイズ](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [パート 7: Advanced Topics](./networking/cilium/07-advanced-topics.md) | [クイズ](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [Networking Concepts](./networking/cilium/networking-concepts.md) | [クイズ](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [用語集](./networking/cilium/glossary.md) | [クイズ](./quizzes/networking/cilium/glossary-quiz.md)
4. **Calico 詳細解説**
   - [Calico 入門](./networking/calico/README.md)
   - [パート 1: 入門](./networking/calico/01-introduction.md) | [クイズ](./quizzes/networking/calico/01-introduction-quiz.md)
   - [パート 2: Architecture](./networking/calico/02-architecture.md) | [クイズ](./quizzes/networking/calico/02-architecture-quiz.md)
   - [パート 3: Networking Modes](./networking/calico/03-networking-modes.md) | [クイズ](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [パート 4: BGP 詳細解説](./networking/calico/04-bgp-deep-dive.md) | [クイズ](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [パート 5: Network Policy](./networking/calico/05-network-policy.md) | [クイズ](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [パート 6: eBPF Dataplane](./networking/calico/06-ebpf-dataplane.md) | [クイズ](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [パート 7: Advanced Topics](./networking/calico/07-advanced-topics.md) | [クイズ](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [パート 8: EKS Integration](./networking/calico/08-eks-integration.md) | [クイズ](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [パート 9: Operations](./networking/calico/09-operations.md) | [クイズ](./quizzes/networking/calico/09-operations-quiz.md)
   - [用語集](./networking/calico/glossary.md) | [クイズ](./quizzes/networking/calico/glossary-quiz.md)
5. [VPC Lattice](./networking/02-vpc-lattice.md) | [クイズ](./quizzes/networking/02-vpc-lattice-quiz.md)
6. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [クイズ](./quizzes/networking/03-aws-lb-controller-quiz.md)
7. [Gateway API](./networking/04-gateway-api.md) | [クイズ](./quizzes/networking/04-gateway-api-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [クイズ](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Linkerd 入門](./service-mesh/linkerd/README.md)
   - [インストール](./service-mesh/linkerd/01-installation.md) | [クイズ](./quizzes/service-mesh/linkerd/installation.md)
   - [Architecture](./service-mesh/linkerd/02-architecture.md) | [クイズ](./quizzes/service-mesh/linkerd/architecture.md)
   - [Traffic Management](./service-mesh/linkerd/03-traffic-management.md) | [クイズ](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [Security](./service-mesh/linkerd/04-security.md) | [クイズ](./quizzes/service-mesh/linkerd/security.md)
   - [Observability](./service-mesh/linkerd/05-observability.md) | [クイズ](./quizzes/service-mesh/linkerd/observability.md)
   - [Multi-cluster](./service-mesh/linkerd/06-multi-cluster.md) | [クイズ](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [Best Practices](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Cilium Service Mesh 入門](./service-mesh/cilium-service-mesh/README.md)
   - [Architecture](./service-mesh/cilium-service-mesh/01-architecture.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [Traffic Management](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [Security](./service-mesh/cilium-service-mesh/03-security.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [Observability](./service-mesh/cilium-service-mesh/04-observability.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [クイズ](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [Best Practices](./service-mesh/cilium-service-mesh/06-best-practices.md)

### Security & Policy
1. [Kyverno による Policy Management](./security/01-kyverno-policy-management.md) | [クイズ](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Kubernetes Authentication と Authorization](./security/02-kubernetes-auth-authz.md) | [クイズ](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Pod Security Standards](./security/03-pod-security-standards.md) | [クイズ](./quizzes/security/03-pod-security-standards-quiz.md)
4. [Network Policies](./security/04-network-policies.md) | [クイズ](./quizzes/security/04-network-policies-quiz.md)
5. [Secrets Management](./security/05-secrets-management.md) | [クイズ](./quizzes/security/05-secrets-management-quiz.md)
6. [EKS Security Best Practices](./security/06-eks-security-best-practices.md) | [クイズ](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [Image Security](./security/07-image-security.md) | [クイズ](./quizzes/security/07-image-security-quiz.md)
8. [Runtime Security](./security/08-runtime-security.md) | [クイズ](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [クイズ](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [クイズ](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [クイズ](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [クイズ](./quizzes/security/12-spiffe-spire-quiz.md)

### Container Registry
1. [Container Registry 概要](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [クイズ](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [クイズ](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [クイズ](./quizzes/container-registry/03-harbor-quiz.md)
5. [Container Registry Best Practices](./container-registry/04-best-practices.md) | [クイズ](./quizzes/container-registry/04-best-practices-quiz.md)

### Platform Engineering
0. [Platform Engineering 概要](./platform-engineering/00-platform-engineering-overview.md) | [クイズ](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
1. [Helm](./platform-engineering/01-helm.md) | [クイズ](./quizzes/platform-engineering/01-helm-quiz.md)
2. [AWS Controllers for Kubernetes (ACK)](./platform-engineering/02-ack.md) | [クイズ](./quizzes/platform-engineering/02-ack-quiz.md)
3. [Kubernetes Resource Operator (KRO)](./platform-engineering/03-kro.md) | [クイズ](./quizzes/platform-engineering/03-kro-quiz.md)
4. [Kubernetes Extension Mechanisms](./platform-engineering/04-kubernetes-extensions.md) | [クイズ](./quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
5. [ExampleCorp: ACK + KRO Integration Example](./platform-engineering/05-example-corp-app.md)
6. [Backstage IDP](./platform-engineering/06-backstage-idp.md) | [クイズ](./quizzes/platform-engineering/06-backstage-idp-quiz.md)
7. [Crossplane](./platform-engineering/07-crossplane.md) | [クイズ](./quizzes/platform-engineering/07-crossplane-quiz.md)
8. [vCluster](./platform-engineering/08-vcluster.md) | [クイズ](./quizzes/platform-engineering/08-vcluster-quiz.md)

### GitOps
1. [GitOps 概要](./gitops/README.md)
2. **ArgoCD**
   - [ArgoCD 入門](./gitops/argocd/README.md) | [クイズ](./quizzes/gitops/01-argocd-quiz.md)
   - [インストール](./gitops/argocd/01-installation.md) | [クイズ](./quizzes/gitops/argocd/01-installation-quiz.md)
   - [Applications](./gitops/argocd/02-applications.md) | [クイズ](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [Sync Strategies](./gitops/argocd/03-sync-strategies.md) | [クイズ](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSets](./gitops/argocd/04-applicationsets.md) | [クイズ](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [Traffic Management](./gitops/argocd/05-traffic-management.md) | [クイズ](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [Projects & RBAC](./gitops/argocd/06-projects-rbac.md) | [クイズ](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [Security](./gitops/argocd/07-security.md) | [クイズ](./quizzes/gitops/argocd/07-security-quiz.md)
   - [Notifications](./gitops/argocd/08-notifications.md) | [クイズ](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [Best Practices](./gitops/argocd/09-best-practices.md) | [クイズ](./quizzes/gitops/argocd/09-best-practices-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [クイズ](./quizzes/gitops/02-fluxcd-quiz.md)
4. [GitOps Tools Comparison](./gitops/03-gitops-comparison.md) | [クイズ](./quizzes/gitops/03-gitops-comparison-quiz.md)
5. [Flagger Progressive Delivery](./gitops/04-flagger.md) | [クイズ](./quizzes/gitops/04-flagger-quiz.md)
6. [Feature Flags と OpenFeature](./gitops/05-feature-flags.md) | [クイズ](./quizzes/gitops/05-feature-flags-quiz.md)

### Operations Guide
1. [Infrastructure Setup](./ops/01-infrastructure-setup.md) | [クイズ](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [Infrastructure Advanced](./ops/02-infrastructure-advanced.md) | [クイズ](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [CI Pipelines](./ops/03-ci-pipelines.md) | [クイズ](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps Multi-Cluster](./ops/04-gitops-multi-cluster.md) | [クイズ](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [GitOps Automation](./ops/05-gitops-automation.md) | [クイズ](./quizzes/ops/05-gitops-automation-quiz.md)
6. [Scaling Strategies](./ops/06-scaling-strategies.md) | [クイズ](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [Observability Alerts](./ops/07-observability-alerts.md) | [クイズ](./quizzes/ops/07-observability-alerts-quiz.md)
8. [Observability Analysis](./ops/08-observability-analysis.md) | [クイズ](./quizzes/ops/08-observability-analysis-quiz.md)
9. [Observability Stack](./ops/09-observability-stack.md) | [クイズ](./quizzes/ops/09-observability-stack-quiz.md)
10. [Resource Optimization](./ops/10-resource-optimization.md) | [クイズ](./quizzes/ops/10-resource-optimization-quiz.md)
11. [Upgrade Operations](./ops/11-upgrade-operations.md) | [クイズ](./quizzes/ops/11-upgrade-operations-quiz.md)
12. [Event Capacity Planning Playbook](./ops/12-event-capacity-planning.md) | [クイズ](./quizzes/ops/12-event-capacity-planning-quiz.md)
13. [FinOps Cost Visibility Platform](./ops/13-finops-cost-platform.md) | [クイズ](./quizzes/ops/13-finops-cost-platform-quiz.md)
14. [Tekton Pipelines](./ops/14-tekton-pipelines.md) | [クイズ](./quizzes/ops/14-tekton-pipelines-quiz.md)

### Observability
1. [Observability 概要](./observability/README.md)
2. **Metrics**
   - [Metrics 概要](./observability/metrics/README.md) | [クイズ](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [クイズ](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [クイズ](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [クイズ](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [クイズ](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [クイズ](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **Logging**
   - [Logging 概要](./observability/logging/README.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [クイズ](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [クイズ](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [クイズ](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [クイズ](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [Log Collectors](./observability/logging/05-collectors.md) | [クイズ](./quizzes/observability/logging/05-collectors-quiz.md)
4. **Tracing**
   - [Tracing 概要](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [クイズ](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [クイズ](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [クイズ](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [クイズ](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **Alerting**
   - [Alerting 概要](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [クイズ](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [クイズ](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [クイズ](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [クイズ](./quizzes/observability/grafana/grafana-quiz.md)
7. [Observability Optimization Guide](./observability/09-observability-optimization.md) | [クイズ](./quizzes/observability/09-observability-optimization-quiz.md)

## ラボガイド

理論を学んだ後、実際の環境で練習するためのハンズオンラボガイドを提供します。

- [ラボガイド一覧](./labs/README.md)
- Basics: Linux Basics、Linux Operations、Container Labs
- Core: Pod、Service、Storage、ConfigMap Labs
- EKS: Cluster Creation Lab

### Observability End-to-End Labs
1. [ラボシリーズ入門](./labs/observability/README.md)
2. [パート 1: Infrastructure Setup](./labs/observability/01-infrastructure-setup-lab.md) | [クイズ](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [パート 2: Observability Stack](./labs/observability/02-observability-stack-lab.md) | [クイズ](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [パート 3: MSA Deployment と Canary](./labs/observability/03-msa-deployment-lab.md) | [クイズ](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [パート 4: Load Testing と Autoscaling](./labs/observability/04-load-testing-scaling-lab.md) | [クイズ](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [パート 5: Alerting と AIOps](./labs/observability/05-alerting-aiops-lab.md) | [クイズ](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [パート 6: Distributed Tracing Analysis](./labs/observability/06-distributed-tracing-lab.md) | [クイズ](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

## 学習ガイド

### 初心者向け学習パス
1. 次の順序で学習してください: **基本概念** -> **Kubernetes コア概念** -> **Amazon EKS**
2. 各章を読んだ後、対応するクイズに取り組み、理解度を確認してください
3. 練習環境でコマンドとサンプルコードをハンズオンで実行してください

### 上級ユーザー向け学習パス
1. 次の順序で学習してください: **Amazon EKS** -> **AI/ML** -> **Service Mesh** -> **Security & Policy**
2. **Cilium** セクションで Networking を深掘りしてください
3. 特定のツールや技術に焦点を当て、深く学習してください

### クイズの使い方
- 各ドキュメント末尾のクイズリンクをクリックして学習内容を確認します
- 答えを表示する前に、まずトグル形式の答えについて考えてください
- 間違えた問題があれば、対応するドキュメントを復習してください

## コントリビューション

このプロジェクトに貢献したい場合:
1. 誤字やコンテンツの誤りを見つけたら issue を送信してください
2. 新しいトピックや改善を提案してください
3. クイズ問題への追加や改善を提案してください

## ライセンス

このトレーニング教材は、学習目的で自由に使用できます。
### スケジューリング
1. Custom Scheduler
   - [パート 1: カスタムスケジューラーの基礎](./scheduling/01-custom-scheduler-part1.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [パート 2: スケジューラー拡張機能とフレームワーク](./scheduling/02-custom-scheduler-part2.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [パート 3: カスタムスケジューラーの実装例と監視](./scheduling/03-custom-scheduler-part3.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### EKS Hybrid Nodes
1. [EKS ハイブリッドノードの概要](./eks-hybrid-nodes/README.md)
2. [前提条件](./eks-hybrid-nodes/01-prerequisites.md) | [Quiz](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [ネットワーク設定](./eks-hybrid-nodes/02-network-configuration.md) | [Quiz](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [エアギャップ環境のセットアップ](./eks-hybrid-nodes/03-airgap-setup.md) | [Quiz](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [Nodeの初期化](./eks-hybrid-nodes/04-node-bootstrap.md) | [Quiz](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [GPUサーバーの統合](./eks-hybrid-nodes/05-gpu-integration.md) | [Quiz](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [ワークロード配置戦略](./eks-hybrid-nodes/06-workload-placement.md) | [Quiz](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [Nodeライフサイクル管理](./eks-hybrid-nodes/07-node-lifecycle.md) | [Quiz](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [運用と保守](./eks-hybrid-nodes/08-operations.md) | [Quiz](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [ベアメタルOSのセットアップ](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [Quiz](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Hybrid Nodesゲートウェイ](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [Quiz](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
### Kubernetes の中核概念
1. [クラスターアーキテクチャ](./core/01-cluster-architecture.md) | [Quiz](./quizzes/core/01-cluster-architecture-quiz.md)
2. [Pod とワークロード](./core/02-pods-and-workloads.md) | [Quiz](./quizzes/core/02-pods-and-workloads-quiz.md)
3. [サービスとネットワーキング](./core/03-services-networking.md) | [Quiz](./quizzes/core/03-services-networking-quiz.md)
4. [ストレージ](./core/04-storage.md) | [Quiz](./quizzes/core/04-storage-quiz.md)
5. [構成](./core/05-configuration-secrets.md) | [Quiz](./quizzes/core/05-configuration-secrets-quiz.md)
6. [セキュリティ](./core/06-security.md) | [Quiz](./quizzes/core/06-security-quiz.md)
7. [ポリシー](./core/07-policies.md) | [Quiz](./quizzes/core/07-policies-quiz.md)
8. [スケジューリング、プリエンプション、退避](./core/08-scheduling-preemption-eviction.md) | [Quiz](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
9. [クラスター管理](./core/09-cluster-administration.md) | [Quiz](./quizzes/core/09-cluster-administration-quiz.md)
10. [Kubernetes における Windows](./core/10-windows-in-kubernetes.md) | [Quiz](./quizzes/core/10-windows-in-kubernetes-quiz.md)
11. [Kubernetes の拡張](./core/11-extending-kubernetes.md) | [Quiz](./quizzes/core/11-extending-kubernetes-quiz.md)

### EKS 上のデータ
1. [EKS上のデータ概要](./data-on-eks/README.md)
2. **Kafka on EKS Deep Dive**
   - [EKS 上の Kafka 入門](./data-on-eks/kafka/README.md)
   - [パート1: Kafkaの基礎](./data-on-eks/kafka/01-kafka-fundamentals.md) | [Quiz](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [パート2: Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [Quiz](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [パート3: Kafkaの運用](./data-on-eks/kafka/03-kafka-operations.md) | [Quiz](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [パート4: Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [Quiz](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [パート5: Kafka ConnectとMirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Quiz](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [パート6: MSK統合](./data-on-eks/kafka/06-msk-integration.md) | [Quiz](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [パート7: 監視](./data-on-eks/kafka/07-monitoring.md) | [Quiz](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [パート8: ベストプラクティス](./data-on-eks/kafka/08-best-practices.md) | [Quiz](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)

### 人工知能／機械学習
1. [AI/ML ワークロード](./ai-ml/01-ai-ml-workloads.md) | [Quiz](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [AI インフラストラクチャ](./ai-ml/06-ai-infrastructure.md) | [Quiz](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [EKS でのモデル学習](./ai-ml/05-model-training.md) | [Quiz](./quizzes/ai-ml/05-model-training-quiz.md)
4. [推論フレームワーク](./ai-ml/04-inference-frameworks.md) | [Quiz](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [vLLM のデプロイと最適化](./ai-ml/02-vllm-deployment.md) | [Quiz](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [EKS 上のエージェント型 AI プラットフォーム](./ai-ml/03-agentic-ai-platform.md) | [Quiz](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [AI/ML のベストプラクティス](./ai-ml/07-ai-ml-best-practices.md) | [Quiz](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)

