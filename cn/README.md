> [韩语版本](https://atomoh.gitbook.io/kubernetes-docs/)

# Kubernetes 和 Amazon EKS 培训内容
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

本仓库提供关于 Kubernetes 和 Amazon EKS 的全面培训材料。内容涵盖从 Linux 基础到容器化、Kubernetes 编排，以及 Amazon EKS 的高级功能。

## 学习材料和测验

本培训内容为每个主题提供学习材料和对应测验。你可以通过测验来检验并巩固所学内容。每个测验都采用可展开/折叠的答案样式，答案默认隐藏，让你可以先尝试回答问题，再查看答案。

- [学习材料目录](#table-of-contents) - 按主题组织的学习材料
- [测验集合](./quizzes/README.md) - 按主题组织的测验

## 目录

### 新闻
- [每周新闻](./news/README.md) - 最新 Kubernetes/EKS 生态系统新闻摘要

### 基本概念
1. [Linux 基础](./basics/01-linux-basics.md) | [测验](./quizzes/basics/01-linux-basics-quiz.md) | [实验](./labs/basics/01-linux-basics-lab.md)
2. [Linux 运维技能](./basics/02-linux-advanced.md) | [测验](./quizzes/basics/02-linux-advanced-quiz.md) | [实验](./labs/basics/02-linux-advanced-lab.md)
3. [容器技术](./basics/03-container-technology.md) | [测验](./quizzes/basics/03-container-technology-quiz.md) | [实验](./labs/basics/03-container-technology-lab.md)
4. [Kubernetes 简介](./basics/04-kubernetes-introduction.md) | [测验](./quizzes/basics/04-kubernetes-introduction-quiz.md)
5. [eBPF 基础和实际应用](./basics/05-ebpf-fundamentals.md) | [测验](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Kubernetes 核心概念
1. [Cluster 架构](./core/01-cluster-architecture.md) | [测验](./quizzes/core/01-cluster-architecture-quiz.md)
2. [Pod 和 Workload](./core/02-pods-and-workloads.md) | [测验](./quizzes/core/02-pods-and-workloads-quiz.md)
3. [Service 和网络](./core/03-services-networking.md) | [测验](./quizzes/core/03-services-networking-quiz.md)
4. [存储](./core/04-storage.md) | [测验](./quizzes/core/04-storage-quiz.md)
5. [配置](./core/05-configuration-secrets.md) | [测验](./quizzes/core/05-configuration-secrets-quiz.md)
6. [安全](./core/06-security.md) | [测验](./quizzes/core/06-security-quiz.md)
7. [策略](./core/07-policies.md) | [测验](./quizzes/core/07-policies-quiz.md)
8. [调度、抢占和驱逐](./core/08-scheduling-preemption-eviction.md) | [测验](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
9. [Cluster 管理](./core/09-cluster-administration.md) | [测验](./quizzes/core/09-cluster-administration-quiz.md)
10. [Kubernetes 中的 Windows](./core/10-windows-in-kubernetes.md) | [测验](./quizzes/core/10-windows-in-kubernetes-quiz.md)
11. [扩展 Kubernetes](./core/11-extending-kubernetes.md) | [测验](./quizzes/core/11-extending-kubernetes-quiz.md)

### 调度
1. 自定义 Scheduler
   - [第 1 部分：自定义 Scheduler 基础](./scheduling/01-custom-scheduler-part1.md) | [测验](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [第 2 部分：Scheduler 扩展和框架](./scheduling/02-custom-scheduler-part2.md) | [测验](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [第 3 部分：自定义 Scheduler 实现示例和监控](./scheduling/03-custom-scheduler-part3.md) | [测验](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### Autoscaling
1. [KEDA](./autoscaling/01-keda.md) | [测验](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [测验](./quizzes/autoscaling/06-karpenter-quiz.md)
3. [Knative](./autoscaling/03-knative.md) | [测验](./quizzes/autoscaling/03-knative-quiz.md)

### Amazon EKS
1. [EKS 简介](./eks/01-eks-introduction.md) | [测验](./quizzes/eks/01-eks-introduction-quiz.md)
2. EKS Cluster 创建
   - [第 1 部分：先决条件](./eks/02-eks-cluster-creation-part1.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [第 2 部分：使用 eksctl 创建 Cluster](./eks/02-eks-cluster-creation-part2.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [第 3 部分：使用 AWS Management Console 和 CLI 创建 Cluster](./eks/02-eks-cluster-creation-part3.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [第 4 部分：使用 Terraform 和 CDK 创建 Cluster](./eks/02-eks-cluster-creation-part4.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [第 5 部分：Cluster 访问、验证、升级和删除](./eks/02-eks-cluster-creation-part5.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. EKS 网络
   - [第 1 部分：基本概念和 VPC 配置](./eks/03-eks-networking-part1.md) | [测验](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [第 2 部分：Service 和负载均衡、Network Policy](./eks/03-eks-networking-part2.md) | [测验](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [第 3 部分：性能优化、故障排查、高级用例](./eks/03-eks-networking-part3.md) | [测验](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. EKS 存储
   - [第 1 部分：基本概念、EBS、EFS](./eks/04-eks-storage-part1.md) | [测验](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [第 2 部分：FSx for Lustre、S3、Snapshot、Volume Expansion、性能优化](./eks/04-eks-storage-part2.md) | [测验](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [第 3 部分：监控、故障排查、成本优化、安全](./eks/04-eks-storage-part3.md) | [测验](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [EKS 安全](./eks/05-eks-security.md) | [测验](./quizzes/eks/05-eks-security-quiz.md)
6. [EKS 监控和日志](./eks/06-eks-monitoring-logging.md) | [测验](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [EKS 成本优化](./eks/07-eks-cost-optimization.md) | [测验](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [EKS 升级](./eks/08-eks-upgrades.md) | [测验](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [EKS 故障排查](./eks/09-eks-troubleshooting.md) | [测验](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [EKS 韧性和高可用性](./eks/10-eks-resiliency.md) | [测验](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [EKS 高级调试](./eks/11-eks-advanced-debugging.md) | [测验](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [Kubernetes 版本功能和路线图](./eks/12-kubernetes-version-roadmap.md) | [测验](./quizzes/eks/12-kubernetes-version-roadmap-quiz.md)

### EKS Hybrid Nodes
1. [EKS Hybrid Nodes 简介](./eks-hybrid-nodes/README.md)
2. [先决条件](./eks-hybrid-nodes/01-prerequisites.md) | [测验](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [网络配置](./eks-hybrid-nodes/02-network-configuration.md) | [测验](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [Air-Gap 环境设置](./eks-hybrid-nodes/03-airgap-setup.md) | [测验](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [Node Bootstrap](./eks-hybrid-nodes/04-node-bootstrap.md) | [测验](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [GPU Server 集成](./eks-hybrid-nodes/05-gpu-integration.md) | [测验](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [Workload 放置策略](./eks-hybrid-nodes/06-workload-placement.md) | [测验](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [Node 生命周期管理](./eks-hybrid-nodes/07-node-lifecycle.md) | [测验](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [运维和维护](./eks-hybrid-nodes/08-operations.md) | [测验](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [Bare Metal OS 设置](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [测验](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Hybrid Nodes Gateway](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [测验](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

### EKS Auto Mode
1. [EKS Auto Mode 简介](./eks-auto-mode/README.md)
2. [入门](./eks-auto-mode/01-getting-started.md) | [测验](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [NodePool 配置](./eks-auto-mode/02-nodepool-configuration.md) | [测验](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [扩缩容行为](./eks-auto-mode/03-scaling-behavior.md) | [测验](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Spot Instance 策略](./eks-auto-mode/04-spot-strategies.md) | [测验](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [运维和管理](./eks-auto-mode/05-operations.md) | [测验](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [成本管理](./eks-auto-mode/06-cost-management.md) | [测验](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [Node 生命周期](./eks-auto-mode/07-node-lifecycle.md) | [测验](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [Workload 优化](./eks-auto-mode/08-workload-optimization.md) | [测验](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [迁移指南](./eks-auto-mode/09-migration-guide.md) | [测验](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### AI/ML
1. [AI/ML Workload](./ai-ml/01-ai-ml-workloads.md) | [测验](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [AI 基础设施](./ai-ml/06-ai-infrastructure.md) | [测验](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [在 EKS 上进行模型训练](./ai-ml/05-model-training.md) | [测验](./quizzes/ai-ml/05-model-training-quiz.md)
4. [推理框架](./ai-ml/04-inference-frameworks.md) | [测验](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [vLLM 部署和优化](./ai-ml/02-vllm-deployment.md) | [测验](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [EKS 上的 Agentic AI 平台](./ai-ml/03-agentic-ai-platform.md) | [测验](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [AI/ML 最佳实践](./ai-ml/07-ai-ml-best-practices.md) | [测验](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
8. **EKS 上的 Ray 深入解析**
   - [EKS 上的 Ray 简介](./ai-ml/ray/README.md)
   - [第 1 部分：Ray 架构](./ai-ml/ray/01-architecture.md) | [测验](./quizzes/ai-ml/ray/01-architecture-quiz.md)
   - [第 2 部分：KubeRay Operator](./ai-ml/ray/02-kuberay-operator.md) | [测验](./quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
   - [第 3 部分：Ray Train 和 Ray Tune](./ai-ml/ray/03-ray-train-tune.md) | [测验](./quizzes/ai-ml/ray/03-ray-train-tune-quiz.md)
   - [第 4 部分：Ray Serve](./ai-ml/ray/04-ray-serve.md) | [测验](./quizzes/ai-ml/ray/04-ray-serve-quiz.md)
9. **EKS 上的 Kubeflow 深入解析**
   - [EKS 上的 Kubeflow 简介](./ai-ml/kubeflow/README.md)
   - [第 1 部分：Kubeflow 架构及在 EKS 上的安装](./ai-ml/kubeflow/01-architecture-installation.md) | [测验](./quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md)
   - [第 2 部分：Kubeflow Pipelines](./ai-ml/kubeflow/02-pipelines.md) | [测验](./quizzes/ai-ml/kubeflow/02-pipelines-quiz.md)
   - [第 3 部分：Kubeflow Notebooks](./ai-ml/kubeflow/03-notebooks.md) | [测验](./quizzes/ai-ml/kubeflow/03-notebooks-quiz.md)
   - [第 4 部分：Katib — 超参数调优和自动化机器学习](./ai-ml/kubeflow/04-katib.md) | [测验](./quizzes/ai-ml/kubeflow/04-katib-quiz.md)
   - [第 5 部分：Kubeflow Trainer 和分布式训练](./ai-ml/kubeflow/05-training-operator.md) | [测验](./quizzes/ai-ml/kubeflow/05-training-operator-quiz.md)
   - [第 6 部分：KServe — 在 Kubernetes 上提供模型服务](./ai-ml/kubeflow/06-kserve.md) | [测验](./quizzes/ai-ml/kubeflow/06-kserve-quiz.md)
10. **EKS 上的 MLflow 深入解析**
    - [EKS 上的 MLflow 简介](./ai-ml/mlflow/README.md)
    - [第 1 部分：MLflow 跟踪](./ai-ml/mlflow/01-tracking.md) | [测验](./quizzes/ai-ml/mlflow/01-tracking-quiz.md)
    - [第 2 部分：MLflow 模型注册表](./ai-ml/mlflow/02-model-registry.md) | [测验](./quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
    - [第 3 部分：在 EKS 上部署 MLflow](./ai-ml/mlflow/03-eks-deployment.md) | [测验](./quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)

### Data on EKS
1. [Data on EKS 概览](./data-on-eks/README.md)
2. **Kafka on EKS 深入解析**
   - [Kafka on EKS 简介](./data-on-eks/kafka/README.md)
   - [第 1 部分：Kafka 基础](./data-on-eks/kafka/01-kafka-fundamentals.md) | [测验](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [第 2 部分：Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [测验](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [第 3 部分：Kafka 运维](./data-on-eks/kafka/03-kafka-operations.md) | [测验](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [第 4 部分：Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [测验](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [第 5 部分：Kafka Connect 和 MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [测验](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [第 6 部分：MSK 集成](./data-on-eks/kafka/06-msk-integration.md) | [测验](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [第 7 部分：监控](./data-on-eks/kafka/07-monitoring.md) | [测验](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [第 8 部分：最佳实践](./data-on-eks/kafka/08-best-practices.md) | [测验](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)

### 网络
1. [网络概览](./networking/README.md) | [测验](./quizzes/networking/00-networking-overview-quiz.md)
2. [VPC CNI](./networking/01-vpc-cni.md) | [测验](./quizzes/networking/01-vpc-cni-quiz.md)
3. **Cilium 深入解析**
   - [Cilium 简介](./networking/cilium/README.md)
   - [第 1 部分：简介](./networking/cilium/01-introduction.md) | [测验](./quizzes/networking/cilium/01-introduction-quiz.md)
   - [第 2 部分：eBPF](./networking/cilium/02-ebpf.md) | [测验](./quizzes/networking/cilium/02-ebpf-quiz.md)
   - [第 3 部分：网络](./networking/cilium/03-networking.md) | [测验](./quizzes/networking/cilium/03-networking-quiz.md)
   - [第 4 部分：IPAM 和策略](./networking/cilium/04-ipam-policy.md) | [测验](./quizzes/networking/cilium/04-ipam-policy-quiz.md)
   - [第 5 部分：L2-L7 网络](./networking/cilium/05-l2-l7-networking.md) | [测验](./quizzes/networking/cilium/05-l2-l7-networking-quiz.md)
   - [第 6 部分：安全和可见性](./networking/cilium/06-security-visibility.md) | [测验](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [第 7 部分：高级主题](./networking/cilium/07-advanced-topics.md) | [测验](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [网络概念](./networking/cilium/networking-concepts.md) | [测验](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [术语表](./networking/cilium/glossary.md) | [测验](./quizzes/networking/cilium/glossary-quiz.md)
4. **Calico 深入解析**
   - [Calico 简介](./networking/calico/README.md)
   - [第 1 部分：简介](./networking/calico/01-introduction.md) | [测验](./quizzes/networking/calico/01-introduction-quiz.md)
   - [第 2 部分：架构](./networking/calico/02-architecture.md) | [测验](./quizzes/networking/calico/02-architecture-quiz.md)
   - [第 3 部分：网络模式](./networking/calico/03-networking-modes.md) | [测验](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [第 4 部分：BGP 深入解析](./networking/calico/04-bgp-deep-dive.md) | [测验](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [第 5 部分：Network Policy](./networking/calico/05-network-policy.md) | [测验](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [第 6 部分：eBPF Dataplane](./networking/calico/06-ebpf-dataplane.md) | [测验](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [第 7 部分：高级主题](./networking/calico/07-advanced-topics.md) | [测验](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [第 8 部分：EKS 集成](./networking/calico/08-eks-integration.md) | [测验](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [第 9 部分：运维](./networking/calico/09-operations.md) | [测验](./quizzes/networking/calico/09-operations-quiz.md)
   - [术语表](./networking/calico/glossary.md) | [测验](./quizzes/networking/calico/glossary-quiz.md)
5. [VPC Lattice](./networking/02-vpc-lattice.md) | [测验](./quizzes/networking/02-vpc-lattice-quiz.md)
6. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [测验](./quizzes/networking/03-aws-lb-controller-quiz.md)
7. [Gateway API](./networking/04-gateway-api.md) | [测验](./quizzes/networking/04-gateway-api-quiz.md)
8. [跨组织 VPC 连接](./networking/05-cross-org-vpc-connectivity.md) | [测验](./quizzes/networking/05-cross-org-vpc-connectivity-quiz.md)
9. [Pod 网络基准测试](./networking/06-pod-network-benchmark.md) | [测验](./quizzes/networking/06-pod-network-benchmark-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [测验](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Linkerd 简介](./service-mesh/linkerd/README.md)
   - [安装](./service-mesh/linkerd/01-installation.md) | [测验](./quizzes/service-mesh/linkerd/installation.md)
   - [架构](./service-mesh/linkerd/02-architecture.md) | [测验](./quizzes/service-mesh/linkerd/architecture.md)
   - [流量管理](./service-mesh/linkerd/03-traffic-management.md) | [测验](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [安全](./service-mesh/linkerd/04-security.md) | [测验](./quizzes/service-mesh/linkerd/security.md)
   - [可观测性](./service-mesh/linkerd/05-observability.md) | [测验](./quizzes/service-mesh/linkerd/observability.md)
   - [Multi-cluster](./service-mesh/linkerd/06-multi-cluster.md) | [测验](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [最佳实践](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Cilium Service Mesh 简介](./service-mesh/cilium-service-mesh/README.md)
   - [架构](./service-mesh/cilium-service-mesh/01-architecture.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [流量管理](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [安全](./service-mesh/cilium-service-mesh/03-security.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [可观测性](./service-mesh/cilium-service-mesh/04-observability.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [最佳实践](./service-mesh/cilium-service-mesh/06-best-practices.md)

### 安全与策略
1. [使用 Kyverno 进行策略管理](./security/01-kyverno-policy-management.md) | [测验](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Kubernetes 认证和授权](./security/02-kubernetes-auth-authz.md) | [测验](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Pod 安全标准](./security/03-pod-security-standards.md) | [测验](./quizzes/security/03-pod-security-standards-quiz.md)
4. [Network Policy](./security/04-network-policies.md) | [测验](./quizzes/security/04-network-policies-quiz.md)
5. [Secrets 管理](./security/05-secrets-management.md) | [测验](./quizzes/security/05-secrets-management-quiz.md)
6. [EKS 安全最佳实践](./security/06-eks-security-best-practices.md) | [测验](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [Image 安全](./security/07-image-security.md) | [测验](./quizzes/security/07-image-security-quiz.md)
8. [Runtime 安全](./security/08-runtime-security.md) | [测验](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [测验](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [测验](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [测验](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [测验](./quizzes/security/12-spiffe-spire-quiz.md)

### Container Registry
1. [Container Registry 概览](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [测验](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [测验](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [测验](./quizzes/container-registry/03-harbor-quiz.md)
5. [Container Registry 最佳实践](./container-registry/04-best-practices.md) | [测验](./quizzes/container-registry/04-best-practices-quiz.md)

### Platform Engineering
0. [Platform Engineering 概览](./platform-engineering/00-platform-engineering-overview.md) | [测验](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
1. [Helm](./platform-engineering/01-helm.md) | [测验](./quizzes/platform-engineering/01-helm-quiz.md)
2. [AWS Controllers for Kubernetes (ACK)](./platform-engineering/02-ack.md) | [测验](./quizzes/platform-engineering/02-ack-quiz.md)
3. [Kubernetes Resource Operator (KRO)](./platform-engineering/03-kro.md) | [测验](./quizzes/platform-engineering/03-kro-quiz.md)
4. [Kubernetes 扩展机制](./platform-engineering/04-kubernetes-extensions.md) | [测验](./quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)
5. [ExampleCorp：ACK + KRO 集成示例](./platform-engineering/05-example-corp-app.md)
6. [Backstage IDP](./platform-engineering/06-backstage-idp.md) | [测验](./quizzes/platform-engineering/06-backstage-idp-quiz.md)
7. [Crossplane](./platform-engineering/07-crossplane.md) | [测验](./quizzes/platform-engineering/07-crossplane-quiz.md)
8. [vCluster](./platform-engineering/08-vcluster.md) | [测验](./quizzes/platform-engineering/08-vcluster-quiz.md)

### GitOps
1. [GitOps 概览](./gitops/README.md)
2. **ArgoCD**
   - [ArgoCD 简介](./gitops/argocd/README.md) | [测验](./quizzes/gitops/01-argocd-quiz.md)
   - [安装](./gitops/argocd/01-installation.md) | [测验](./quizzes/gitops/argocd/01-installation-quiz.md)
   - [Application](./gitops/argocd/02-applications.md) | [测验](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [同步策略](./gitops/argocd/03-sync-strategies.md) | [测验](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSet](./gitops/argocd/04-applicationsets.md) | [测验](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [流量管理](./gitops/argocd/05-traffic-management.md) | [测验](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [Project 和 RBAC](./gitops/argocd/06-projects-rbac.md) | [测验](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [安全](./gitops/argocd/07-security.md) | [测验](./quizzes/gitops/argocd/07-security-quiz.md)
   - [通知](./gitops/argocd/08-notifications.md) | [测验](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [最佳实践](./gitops/argocd/09-best-practices.md) | [测验](./quizzes/gitops/argocd/09-best-practices-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [测验](./quizzes/gitops/02-fluxcd-quiz.md)
4. [GitOps 工具比较](./gitops/03-gitops-comparison.md) | [测验](./quizzes/gitops/03-gitops-comparison-quiz.md)
5. [Flagger 渐进式交付](./gitops/04-flagger.md) | [测验](./quizzes/gitops/04-flagger-quiz.md)
6. [Feature Flag 和 OpenFeature](./gitops/05-feature-flags.md) | [测验](./quizzes/gitops/05-feature-flags-quiz.md)

### 运维指南
1. [基础设施设置](./ops/01-infrastructure-setup.md) | [测验](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [基础设施进阶](./ops/02-infrastructure-advanced.md) | [测验](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [CI Pipeline](./ops/03-ci-pipelines.md) | [测验](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps Multi-Cluster](./ops/04-gitops-multi-cluster.md) | [测验](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [GitOps 自动化](./ops/05-gitops-automation.md) | [测验](./quizzes/ops/05-gitops-automation-quiz.md)
6. [扩缩容策略](./ops/06-scaling-strategies.md) | [测验](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [可观测性告警](./ops/07-observability-alerts.md) | [测验](./quizzes/ops/07-observability-alerts-quiz.md)
8. [可观测性分析](./ops/08-observability-analysis.md) | [测验](./quizzes/ops/08-observability-analysis-quiz.md)
9. [可观测性栈](./ops/09-observability-stack.md) | [测验](./quizzes/ops/09-observability-stack-quiz.md)
10. [资源优化](./ops/10-resource-optimization.md) | [测验](./quizzes/ops/10-resource-optimization-quiz.md)
11. [升级运维](./ops/11-upgrade-operations.md) | [测验](./quizzes/ops/11-upgrade-operations-quiz.md)
12. [事件容量规划手册](./ops/12-event-capacity-planning.md) | [测验](./quizzes/ops/12-event-capacity-planning-quiz.md)
13. [FinOps 成本可见性平台](./ops/13-finops-cost-platform.md) | [测验](./quizzes/ops/13-finops-cost-platform-quiz.md)
14. [Tekton Pipelines](./ops/14-tekton-pipelines.md) | [测验](./quizzes/ops/14-tekton-pipelines-quiz.md)

### 可观测性
1. [可观测性概览](./observability/README.md)
2. **Metrics**
   - [Metrics 概览](./observability/metrics/README.md) | [测验](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [测验](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [测验](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [测验](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [测验](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [测验](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **Logging**
   - [Logging 概览](./observability/logging/README.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [测验](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [测验](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [测验](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [测验](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [Log Collector](./observability/logging/05-collectors.md) | [测验](./quizzes/observability/logging/05-collectors-quiz.md)
4. **Tracing**
   - [Tracing 概览](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [测验](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [测验](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [测验](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [测验](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **Alerting**
   - [Alerting 概览](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [测验](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [测验](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [测验](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [测验](./quizzes/observability/grafana/grafana-quiz.md)
7. [可观测性优化指南](./observability/09-observability-optimization.md) | [测验](./quizzes/observability/09-observability-optimization-quiz.md)

### 存储
1. [存储概述](./storage/README.md)
2. [EBS gp2 与 gp3 实测基准测试](./storage/01-ebs-gp2-gp3-benchmark.md) | [Quiz](./quizzes/storage/01-ebs-gp2-gp3-benchmark-quiz.md)

## 实验指南

我们提供动手实验指南，帮助你在学习理论后在真实环境中练习。

- [实验指南列表](./labs/README.md)
- 基础：Linux 基础、Linux 运维、容器实验
- 核心：Pod、Service、存储、ConfigMap 实验
- EKS：Cluster 创建实验

### 可观测性端到端实验
1. [实验系列简介](./labs/observability/README.md)
2. [第 1 部分：基础设施设置](./labs/observability/01-infrastructure-setup-lab.md) | [测验](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [第 2 部分：可观测性栈](./labs/observability/02-observability-stack-lab.md) | [测验](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [第 3 部分：MSA 部署和 Canary](./labs/observability/03-msa-deployment-lab.md) | [测验](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [第 4 部分：负载测试和 Autoscaling](./labs/observability/04-load-testing-scaling-lab.md) | [测验](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [第 5 部分：告警和 AIOps](./labs/observability/05-alerting-aiops-lab.md) | [测验](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [第 6 部分：分布式追踪分析](./labs/observability/06-distributed-tracing-lab.md) | [测验](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

## 学习指南

### 初学者学习路径
1. 按以下顺序学习：**基本概念** -> **Kubernetes 核心概念** -> **Amazon EKS**
2. 阅读每一章后，完成对应测验来检查你的理解
3. 在练习环境中动手执行命令和示例代码

### 高级用户学习路径
1. 按以下顺序学习：**Amazon EKS** -> **AI/ML** -> **Service Mesh** -> **安全与策略**
2. 通过 **Cilium** 部分深入学习网络
3. 聚焦特定工具或技术进行深入学习

### 如何使用测验
- 点击每个文档末尾的测验链接来检查你的学习情况
- 在展开答案前，先思考可折叠样式答案中的内容
- 回顾对应文档，复习答错的问题

## 贡献

如果你想为此项目做贡献：
1. 发现错别字或内容错误时提交 issue
2. 建议新主题或改进
3. 建议新增或改进测验问题

## 许可证

本培训材料可免费用于学习目的。
