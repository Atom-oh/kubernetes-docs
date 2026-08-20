> [韩语版本](https://atomoh.gitbook.io/kubernetes-docs/)

# Kubernetes 和 Amazon EKS 培训内容
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

此仓库提供有关 Kubernetes 和 Amazon EKS 的综合培训材料，涵盖从 Linux 基础、容器化、Kubernetes 编排到 Amazon EKS 高级功能的全部内容。

## 学习材料和测验

此培训内容为每个主题提供学习材料及配套测验。您可以通过测验检验并巩固所学知识。每个测验均采用隐藏答案的折叠式设计，让您可以先尝试回答问题，再查看答案。

- [学习材料目录](#table-of-contents) - 按主题分类的学习材料
- [测验集](./quizzes/README.md) - 按主题分类的测验

## 目录

### 新闻
- [每周新闻](./news/README.md) - 最新 Kubernetes/EKS 生态系统新闻摘要

### 基础概念
1. [Linux 基础](./basics/01-linux-basics.md) | [测验](./quizzes/basics/01-linux-basics-quiz.md) | [实验](./labs/basics/01-linux-basics-lab.md)
2. [Linux 运维技能](./basics/02-linux-advanced.md) | [测验](./quizzes/basics/02-linux-advanced-quiz.md) | [实验](./labs/basics/02-linux-advanced-lab.md)
3. [容器技术](./basics/03-container-technology.md) | [测验](./quizzes/basics/03-container-technology-quiz.md) | [实验](./labs/basics/03-container-technology-lab.md)
4. [Kubernetes 简介](./basics/04-kubernetes-introduction.md) | [测验](./quizzes/basics/04-kubernetes-introduction-quiz.md)
5. [eBPF 基础与实践应用](./basics/05-ebpf-fundamentals.md) | [测验](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Kubernetes 核心概念
1. [集群架构](./core/01-cluster-architecture.md) | [测验](./quizzes/core/01-cluster-architecture-quiz.md)
2. [Pod 和工作负载](./core/02-pods-and-workloads.md) | [测验](./quizzes/core/02-pods-and-workloads-quiz.md)
3. [Service 和网络](./core/03-services-networking.md) | [测验](./quizzes/core/03-services-networking-quiz.md)
4. [存储](./core/04-storage.md) | [测验](./quizzes/core/04-storage-quiz.md)
5. [配置](./core/05-configuration-secrets.md) | [测验](./quizzes/core/05-configuration-secrets-quiz.md)
6. [安全](./core/06-security.md) | [测验](./quizzes/core/06-security-quiz.md)
7. [策略](./core/07-policies.md) | [测验](./quizzes/core/07-policies-quiz.md)
8. [调度、抢占和驱逐](./core/08-scheduling-preemption-eviction.md) | [测验](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
9. [集群管理](./core/09-cluster-administration.md) | [测验](./quizzes/core/09-cluster-administration-quiz.md)
10. [Kubernetes 中的 Windows](./core/10-windows-in-kubernetes.md) | [测验](./quizzes/core/10-windows-in-kubernetes-quiz.md)
11. [扩展 Kubernetes](./core/11-extending-kubernetes.md) | [测验](./quizzes/core/11-extending-kubernetes-quiz.md)

### 调度
1. 自定义 Scheduler
   - [第 1 部分：自定义 Scheduler 基础](./scheduling/01-custom-scheduler-part1.md) | [测验](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [第 2 部分：Scheduler 扩展和框架](./scheduling/02-custom-scheduler-part2.md) | [测验](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [第 3 部分：自定义 Scheduler 实现示例和监控](./scheduling/03-custom-scheduler-part3.md) | [测验](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### 自动扩缩容
1. [KEDA](./autoscaling/01-keda.md) | [测验](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [测验](./quizzes/autoscaling/06-karpenter-quiz.md)
3. [Knative](./autoscaling/03-knative.md) | [测验](./quizzes/autoscaling/03-knative-quiz.md)

### Amazon EKS
1. [EKS 简介](./eks/01-eks-introduction.md) | [测验](./quizzes/eks/01-eks-introduction-quiz.md)
2. EKS 集群创建
   - [第 1 部分：前提条件](./eks/02-eks-cluster-creation-part1.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [第 2 部分：使用 eksctl 创建集群](./eks/02-eks-cluster-creation-part2.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [第 3 部分：使用 AWS Management Console 和 CLI 创建集群](./eks/02-eks-cluster-creation-part3.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [第 4 部分：使用 Terraform 和 CDK 创建集群](./eks/02-eks-cluster-creation-part4.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [第 5 部分：集群访问、验证、升级和删除](./eks/02-eks-cluster-creation-part5.md) | [测验](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. EKS 网络
   - [第 1 部分：基础概念和 VPC 配置](./eks/03-eks-networking-part1.md) | [测验](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [第 2 部分：Service、负载均衡和网络策略](./eks/03-eks-networking-part2.md) | [测验](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [第 3 部分：性能优化、故障排除和高级使用场景](./eks/03-eks-networking-part3.md) | [测验](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. EKS 存储
   - [第 1 部分：基础概念、EBS、EFS](./eks/04-eks-storage-part1.md) | [测验](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [第 2 部分：FSx for Lustre、S3、快照、卷扩展和性能优化](./eks/04-eks-storage-part2.md) | [测验](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [第 3 部分：监控、故障排除、成本优化和安全](./eks/04-eks-storage-part3.md) | [测验](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [EKS 安全](./eks/05-eks-security.md) | [测验](./quizzes/eks/05-eks-security-quiz.md)
6. [EKS 监控和日志](./eks/06-eks-monitoring-logging.md) | [测验](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [EKS 成本优化](./eks/07-eks-cost-optimization.md) | [测验](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [EKS 升级](./eks/08-eks-upgrades.md) | [测验](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [EKS 故障排除](./eks/09-eks-troubleshooting.md) | [测验](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [EKS 弹性和高可用性](./eks/10-eks-resiliency.md) | [测验](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [EKS 高级调试](./eks/11-eks-advanced-debugging.md) | [测验](./quizzes/eks/11-eks-advanced-debugging-quiz.md)
12. [Kubernetes 版本功能和路线图](./eks/12-kubernetes-version-roadmap.md) | [测验](./quizzes/eks/12-kubernetes-version-roadmap-quiz.md)

### EKS Hybrid Nodes
1. [EKS Hybrid Nodes 简介](./eks-hybrid-nodes/README.md)
2. [前提条件](./eks-hybrid-nodes/01-prerequisites.md) | [测验](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [网络配置](./eks-hybrid-nodes/02-network-configuration.md) | [测验](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [Air-Gap 环境设置](./eks-hybrid-nodes/03-airgap-setup.md) | [测验](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [节点引导](./eks-hybrid-nodes/04-node-bootstrap.md) | [测验](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [GPU 服务器集成](./eks-hybrid-nodes/05-gpu-integration.md) | [测验](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [工作负载放置策略](./eks-hybrid-nodes/06-workload-placement.md) | [测验](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [节点生命周期管理](./eks-hybrid-nodes/07-node-lifecycle.md) | [测验](./quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
9. [运维](./eks-hybrid-nodes/08-operations.md) | [测验](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)
10. [裸机 OS 设置](./eks-hybrid-nodes/09-bare-metal-os-setup.md) | [测验](./quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
11. [Hybrid Nodes Gateway](./eks-hybrid-nodes/10-hybrid-nodes-gateway.md) | [测验](./quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

### EKS Auto Mode
1. [EKS Auto Mode 简介](./eks-auto-mode/README.md)
2. [入门](./eks-auto-mode/01-getting-started.md) | [测验](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [NodePool 配置](./eks-auto-mode/02-nodepool-configuration.md) | [测验](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [扩缩容行为](./eks-auto-mode/03-scaling-behavior.md) | [测验](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Spot Instance 策略](./eks-auto-mode/04-spot-strategies.md) | [测验](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [运维和管理](./eks-auto-mode/05-operations.md) | [测验](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [成本管理](./eks-auto-mode/06-cost-management.md) | [测验](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [节点生命周期](./eks-auto-mode/07-node-lifecycle.md) | [测验](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [工作负载优化](./eks-auto-mode/08-workload-optimization.md) | [测验](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [迁移指南](./eks-auto-mode/09-migration-guide.md) | [测验](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### AI/ML
1. [AI/ML 工作负载](./ai-ml/01-ai-ml-workloads.md) | [测验](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [AI 基础设施](./ai-ml/06-ai-infrastructure.md) | [测验](./quizzes/ai-ml/06-ai-infrastructure-quiz.md)
3. [在 EKS 上训练模型](./ai-ml/05-model-training.md) | [测验](./quizzes/ai-ml/05-model-training-quiz.md)
4. [推理框架](./ai-ml/04-inference-frameworks.md) | [测验](./quizzes/ai-ml/04-inference-frameworks-quiz.md)
5. [vLLM 部署和优化](./ai-ml/02-vllm-deployment.md) | [测验](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
6. [EKS 上的 Agentic AI 平台](./ai-ml/03-agentic-ai-platform.md) | [测验](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)
7. [AI/ML 最佳实践](./ai-ml/07-ai-ml-best-practices.md) | [测验](./quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
8. **EKS 上的 Kubeflow 深入解析**
   - [EKS 上的 Kubeflow 简介](./ai-ml/kubeflow/README.md)
   - [第 1 部分：Kubeflow 架构及在 EKS 上安装](./ai-ml/kubeflow/01-architecture-installation.md) | [测验](./quizzes/ai-ml/kubeflow/01-architecture-installation-quiz.md)
   - [第 2 部分：Kubeflow Pipelines](./ai-ml/kubeflow/02-pipelines.md) | [测验](./quizzes/ai-ml/kubeflow/02-pipelines-quiz.md)
   - [第 3 部分：Kubeflow Notebooks](./ai-ml/kubeflow/03-notebooks.md) | [测验](./quizzes/ai-ml/kubeflow/03-notebooks-quiz.md)
   - [第 4 部分：Katib — 超参数调优和 AutoML](./ai-ml/kubeflow/04-katib.md) | [测验](./quizzes/ai-ml/kubeflow/04-katib-quiz.md)
   - [第 5 部分：Kubeflow Trainer 和分布式训练](./ai-ml/kubeflow/05-training-operator.md) | [测验](./quizzes/ai-ml/kubeflow/05-training-operator-quiz.md)
   - [第 6 部分：KServe — Kubernetes 上的模型服务](./ai-ml/kubeflow/06-kserve.md) | [测验](./quizzes/ai-ml/kubeflow/06-kserve-quiz.md)
9. **EKS 上的 MLflow 深入解析**
   - [EKS 上的 MLflow 简介](./ai-ml/mlflow/README.md)
   - [第 1 部分：MLflow Tracking](./ai-ml/mlflow/01-tracking.md) | [测验](./quizzes/ai-ml/mlflow/01-tracking-quiz.md)
   - [第 2 部分：MLflow Model Registry](./ai-ml/mlflow/02-model-registry.md) | [测验](./quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
   - [第 3 部分：在 EKS 上部署 MLflow](./ai-ml/mlflow/03-eks-deployment.md) | [测验](./quizzes/ai-ml/mlflow/03-eks-deployment-quiz.md)

### EKS 上的数据
1. [EKS 上的数据概览](./data-on-eks/README.md)
2. **EKS 上的 Kafka 深入解析**
   - [EKS 上的 Kafka 简介](./data-on-eks/kafka/README.md)
   - [第 1 部分：Kafka 基础](./data-on-eks/kafka/01-kafka-fundamentals.md) | [测验](./quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
   - [第 2 部分：Strimzi Operator](./data-on-eks/kafka/02-strimzi-operator.md) | [测验](./quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
   - [第 3 部分：Kafka 运维](./data-on-eks/kafka/03-kafka-operations.md) | [测验](./quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
   - [第 4 部分：Schema Registry](./data-on-eks/kafka/04-schema-registry.md) | [测验](./quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
   - [第 5 部分：Kafka Connect 和 MirrorMaker](./data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [测验](./quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
   - [第 6 部分：MSK 集成](./data-on-eks/kafka/06-msk-integration.md) | [测验](./quizzes/data-on-eks/kafka/06-msk-integration-quiz.md)
   - [第 7 部分：监控](./data-on-eks/kafka/07-monitoring.md) | [测验](./quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
   - [第 8 部分：最佳实践](./data-on-eks/kafka/08-best-practices.md) | [测验](./quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
3. **EKS 上的 Spark 深入解析**
   - [EKS 上的 Spark 简介](./data-on-eks/spark/README.md)
   - [第 1 部分：Kubernetes 上的 Spark 基础](./data-on-eks/spark/01-spark-fundamentals.md) | [测验](./quizzes/data-on-eks/spark/01-spark-fundamentals-quiz.md)
   - [第 2 部分：Spark Operator](./data-on-eks/spark/02-spark-operator.md) | [测验](./quizzes/data-on-eks/spark/02-spark-operator-quiz.md)
   - [第 3 部分：EKS 上的 Amazon EMR](./data-on-eks/spark/03-emr-on-eks.md) | [测验](./quizzes/data-on-eks/spark/03-emr-on-eks-quiz.md)
   - [第 4 部分：性能和成本调优](./data-on-eks/spark/04-performance-tuning.md) | [测验](./quizzes/data-on-eks/spark/04-performance-tuning-quiz.md)
   - [第 5 部分：最佳实践和安全](./data-on-eks/spark/05-best-practices.md) | [测验](./quizzes/data-on-eks/spark/05-best-practices-quiz.md)
4. **EKS 上的 Airflow 深入解析**
   - [EKS 上的 Airflow 简介](./data-on-eks/airflow/README.md)
   - [第 1 部分：Kubernetes 上的 Airflow 架构](./data-on-eks/airflow/01-architecture.md) | [测验](./quizzes/data-on-eks/airflow/01-architecture-quiz.md)
   - [第 2 部分：Helm 部署和 Executor 选择](./data-on-eks/airflow/02-helm-deployment.md) | [测验](./quizzes/data-on-eks/airflow/02-helm-deployment-quiz.md)
   - [第 3 部分：DAG 模式和 KubernetesPodOperator](./data-on-eks/airflow/03-dag-patterns.md) | [测验](./quizzes/data-on-eks/airflow/03-dag-patterns-quiz.md)
   - [第 4 部分：Amazon MWAA 集成](./data-on-eks/airflow/04-mwaa-integration.md) | [测验](./quizzes/data-on-eks/airflow/04-mwaa-integration-quiz.md)
   - [第 5 部分：运维和安全](./data-on-eks/airflow/05-operations.md) | [测验](./quizzes/data-on-eks/airflow/05-operations-quiz.md)
5. **EKS 上的 Flink 深入解析**
   - [EKS 上的 Flink 简介](./data-on-eks/flink/README.md)
   - [第 1 部分：Kubernetes 上的 Flink 架构](./data-on-eks/flink/01-architecture.md) | [测验](./quizzes/data-on-eks/flink/01-architecture-quiz.md)
   - [第 2 部分：Flink Kubernetes Operator](./data-on-eks/flink/02-flink-kubernetes-operator.md) | [测验](./quizzes/data-on-eks/flink/02-flink-kubernetes-operator-quiz.md)
   - [第 3 部分：状态、检查点和流处理模式](./data-on-eks/flink/03-state-checkpointing-streaming.md) | [测验](./quizzes/data-on-eks/flink/03-state-checkpointing-streaming-quiz.md)
   - [第 4 部分：运维、高可用性和 Managed Flink](./data-on-eks/flink/04-operations-ha.md) | [测验](./quizzes/data-on-eks/flink/04-operations-ha-quiz.md)

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
   - [第 6 部分：安全和可观测性](./networking/cilium/06-security-visibility.md) | [测验](./quizzes/networking/cilium/06-security-visibility-quiz.md)
   - [第 7 部分：高级主题](./networking/cilium/07-advanced-topics.md) | [测验](./quizzes/networking/cilium/07-advanced-topics-quiz.md)
   - [网络概念](./networking/cilium/networking-concepts.md) | [测验](./quizzes/networking/cilium/networking-concepts-quiz.md)
   - [术语表](./networking/cilium/glossary.md) | [测验](./quizzes/networking/cilium/glossary-quiz.md)
4. **Calico 深入解析**
   - [Calico 简介](./networking/calico/README.md)
   - [第 1 部分：简介](./networking/calico/01-introduction.md) | [测验](./quizzes/networking/calico/01-introduction-quiz.md)
   - [第 2 部分：架构](./networking/calico/02-architecture.md) | [测验](./quizzes/networking/calico/02-architecture-quiz.md)
   - [第 3 部分：网络模式](./networking/calico/03-networking-modes.md) | [测验](./quizzes/networking/calico/03-networking-modes-quiz.md)
   - [第 4 部分：BGP 深入解析](./networking/calico/04-bgp-deep-dive.md) | [测验](./quizzes/networking/calico/04-bgp-deep-dive-quiz.md)
   - [第 5 部分：网络策略](./networking/calico/05-network-policy.md) | [测验](./quizzes/networking/calico/05-network-policy-quiz.md)
   - [第 6 部分：eBPF 数据平面](./networking/calico/06-ebpf-dataplane.md) | [测验](./quizzes/networking/calico/06-ebpf-dataplane-quiz.md)
   - [第 7 部分：高级主题](./networking/calico/07-advanced-topics.md) | [测验](./quizzes/networking/calico/07-advanced-topics-quiz.md)
   - [第 8 部分：EKS 集成](./networking/calico/08-eks-integration.md) | [测验](./quizzes/networking/calico/08-eks-integration-quiz.md)
   - [第 9 部分：运维](./networking/calico/09-operations.md) | [测验](./quizzes/networking/calico/09-operations-quiz.md)
   - [术语表](./networking/calico/glossary.md) | [测验](./quizzes/networking/calico/glossary-quiz.md)
5. [VPC Lattice](./networking/02-vpc-lattice.md) | [测验](./quizzes/networking/02-vpc-lattice-quiz.md)
6. [AWS Load Balancer Controller](./networking/03-aws-lb-controller.md) | [测验](./quizzes/networking/03-aws-lb-controller-quiz.md)
7. [Gateway API](./networking/04-gateway-api.md) | [测验](./quizzes/networking/04-gateway-api-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/istio/README.md) | [测验](./quizzes/service-mesh/02-istio-quiz.md)
2. **Linkerd**
   - [Linkerd 简介](./service-mesh/linkerd/README.md)
   - [安装](./service-mesh/linkerd/01-installation.md) | [测验](./quizzes/service-mesh/linkerd/installation.md)
   - [架构](./service-mesh/linkerd/02-architecture.md) | [测验](./quizzes/service-mesh/linkerd/architecture.md)
   - [流量管理](./service-mesh/linkerd/03-traffic-management.md) | [测验](./quizzes/service-mesh/linkerd/traffic-management.md)
   - [安全](./service-mesh/linkerd/04-security.md) | [测验](./quizzes/service-mesh/linkerd/security.md)
   - [可观测性](./service-mesh/linkerd/05-observability.md) | [测验](./quizzes/service-mesh/linkerd/observability.md)
   - [多集群](./service-mesh/linkerd/06-multi-cluster.md) | [测验](./quizzes/service-mesh/linkerd/multi-cluster.md)
   - [最佳实践](./service-mesh/linkerd/07-best-practices.md)
3. **Cilium Service Mesh**
   - [Cilium Service Mesh 简介](./service-mesh/cilium-service-mesh/README.md)
   - [架构](./service-mesh/cilium-service-mesh/01-architecture.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/architecture.md)
   - [流量管理](./service-mesh/cilium-service-mesh/02-traffic-management.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/traffic-management.md)
   - [安全](./service-mesh/cilium-service-mesh/03-security.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/security.md)
   - [可观测性](./service-mesh/cilium-service-mesh/04-observability.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/observability.md)
   - [Ingress Gateway](./service-mesh/cilium-service-mesh/05-ingress-gateway.md) | [测验](./quizzes/service-mesh/cilium-service-mesh/ingress-gateway.md)
   - [最佳实践](./service-mesh/cilium-service-mesh/06-best-practices.md)

### 安全和策略
1. [使用 Kyverno 进行策略管理](./security/01-kyverno-policy-management.md) | [测验](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Kubernetes 身份验证和授权](./security/02-kubernetes-auth-authz.md) | [测验](./quizzes/security/02-kubernetes-auth-authz-quiz.md)
3. [Pod 安全标准](./security/03-pod-security-standards.md) | [测验](./quizzes/security/03-pod-security-standards-quiz.md)
4. [网络策略](./security/04-network-policies.md) | [测验](./quizzes/security/04-network-policies-quiz.md)
5. [Secrets 管理](./security/05-secrets-management.md) | [测验](./quizzes/security/05-secrets-management-quiz.md)
6. [EKS 安全最佳实践](./security/06-eks-security-best-practices.md) | [测验](./quizzes/security/06-eks-security-best-practices-quiz.md)
7. [镜像安全](./security/07-image-security.md) | [测验](./quizzes/security/07-image-security-quiz.md)
8. [运行时安全](./security/08-runtime-security.md) | [测验](./quizzes/security/08-runtime-security-quiz.md)
9. [OPA Gatekeeper](./security/09-opa-gatekeeper.md) | [测验](./quizzes/security/09-opa-gatekeeper-quiz.md)
10. [cert-manager](./security/10-cert-manager.md) | [测验](./quizzes/security/10-cert-manager-quiz.md)
11. [Kubescape](./security/11-kubescape.md) | [测验](./quizzes/security/11-kubescape-quiz.md)
12. [SPIFFE/SPIRE](./security/12-spiffe-spire.md) | [测验](./quizzes/security/12-spiffe-spire-quiz.md)

### 容器镜像仓库
1. [容器镜像仓库概览](./container-registry/README.md)
2. [Docker Hub](./container-registry/01-docker-hub.md) | [测验](./quizzes/container-registry/01-docker-hub-quiz.md)
3. [Amazon ECR](./container-registry/02-amazon-ecr.md) | [测验](./quizzes/container-registry/02-amazon-ecr-quiz.md)
4. [Harbor](./container-registry/03-harbor.md) | [测验](./quizzes/container-registry/03-harbor-quiz.md)
5. [容器镜像仓库最佳实践](./container-registry/04-best-practices.md) | [测验](./quizzes/container-registry/04-best-practices-quiz.md)

### 平台工程
0. [平台工程概览](./platform-engineering/00-platform-engineering-overview.md) | [测验](./quizzes/platform-engineering/00-platform-engineering-overview-quiz.md)
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
   - [应用程序](./gitops/argocd/02-applications.md) | [测验](./quizzes/gitops/argocd/02-applications-quiz.md)
   - [同步策略](./gitops/argocd/03-sync-strategies.md) | [测验](./quizzes/gitops/argocd/03-sync-strategies-quiz.md)
   - [ApplicationSets](./gitops/argocd/04-applicationsets.md) | [测验](./quizzes/gitops/argocd/04-applicationsets-quiz.md)
   - [流量管理](./gitops/argocd/05-traffic-management.md) | [测验](./quizzes/gitops/argocd/05-traffic-management-quiz.md)
   - [项目和 RBAC](./gitops/argocd/06-projects-rbac.md) | [测验](./quizzes/gitops/argocd/06-projects-rbac-quiz.md)
   - [安全](./gitops/argocd/07-security.md) | [测验](./quizzes/gitops/argocd/07-security-quiz.md)
   - [通知](./gitops/argocd/08-notifications.md) | [测验](./quizzes/gitops/argocd/08-notifications-quiz.md)
   - [最佳实践](./gitops/argocd/09-best-practices.md) | [测验](./quizzes/gitops/argocd/09-best-practices-quiz.md)
   - [Rollouts 实验深入解析](./gitops/argocd/10-rollouts-experiment.md) | [测验](./quizzes/gitops/argocd/10-rollouts-experiment-quiz.md)
3. [FluxCD](./gitops/02-fluxcd.md) | [测验](./quizzes/gitops/02-fluxcd-quiz.md)
4. [GitOps 工具对比](./gitops/03-gitops-comparison.md) | [测验](./quizzes/gitops/03-gitops-comparison-quiz.md)
5. [Flagger 渐进式交付](./gitops/04-flagger.md) | [测验](./quizzes/gitops/04-flagger-quiz.md)
6. [功能标志和 OpenFeature](./gitops/05-feature-flags.md) | [测验](./quizzes/gitops/05-feature-flags-quiz.md)

### 运维指南
1. [基础设施设置](./ops/01-infrastructure-setup.md) | [测验](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [高级基础设施](./ops/02-infrastructure-advanced.md) | [测验](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [CI Pipelines](./ops/03-ci-pipelines.md) | [测验](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps 多集群](./ops/04-gitops-multi-cluster.md) | [测验](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [GitOps 自动化](./ops/05-gitops-automation.md) | [测验](./quizzes/ops/05-gitops-automation-quiz.md)
6. [扩缩容策略](./ops/06-scaling-strategies.md) | [测验](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [可观测性告警](./ops/07-observability-alerts.md) | [测验](./quizzes/ops/07-observability-alerts-quiz.md)
8. [可观测性分析](./ops/08-observability-analysis.md) | [测验](./quizzes/ops/08-observability-analysis-quiz.md)
9. [可观测性技术栈](./ops/09-observability-stack.md) | [测验](./quizzes/ops/09-observability-stack-quiz.md)
10. [资源优化](./ops/10-resource-optimization.md) | [测验](./quizzes/ops/10-resource-optimization-quiz.md)
11. [升级运维](./ops/11-upgrade-operations.md) | [测验](./quizzes/ops/11-upgrade-operations-quiz.md)
12. [活动容量规划手册](./ops/12-event-capacity-planning.md) | [测验](./quizzes/ops/12-event-capacity-planning-quiz.md)
13. [FinOps 成本可视化平台](./ops/13-finops-cost-platform.md) | [测验](./quizzes/ops/13-finops-cost-platform-quiz.md)
14. [Tekton Pipelines](./ops/14-tekton-pipelines.md) | [测验](./quizzes/ops/14-tekton-pipelines-quiz.md)
15. [可用区集群运维](./ops/15-zonal-operations-guide.md) | [测验](./quizzes/ops/15-zonal-operations-guide.md)

### 可观测性
1. [可观测性概览](./observability/README.md)
2. **指标**
   - [指标概览](./observability/metrics/README.md) | [测验](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [测验](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [测验](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [测验](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [测验](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [测验](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **日志**
   - [日志概览](./observability/logging/README.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [测验](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [测验](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [测验](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [测验](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [日志收集器](./observability/logging/05-collectors.md) | [测验](./quizzes/observability/logging/05-collectors-quiz.md)
4. **追踪**
   - [追踪概览](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [测验](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [测验](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [测验](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [测验](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **告警**
   - [告警概览](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [测验](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [测验](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [测验](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [测验](./quizzes/observability/grafana/grafana-quiz.md)
7. [可观测性优化指南](./observability/09-observability-optimization.md) | [测验](./quizzes/observability/09-observability-optimization-quiz.md)

## 实验指南

我们提供实践实验指南，帮助您在学习理论后于真实环境中进行练习。

- [实验指南列表](./labs/README.md)
- 基础：Linux 基础、Linux 运维、容器实验
- 核心：Pod、Service、Storage、ConfigMap 实验
- EKS：集群创建实验

### 可观测性端到端实验
1. [实验系列简介](./labs/observability/README.md)
2. [第 1 部分：基础设施设置](./labs/observability/01-infrastructure-setup-lab.md) | [测验](./quizzes/observability/labs/01-infrastructure-setup-quiz.md)
3. [第 2 部分：可观测性技术栈](./labs/observability/02-observability-stack-lab.md) | [测验](./quizzes/observability/labs/02-observability-stack-quiz.md)
4. [第 3 部分：MSA 部署和 Canary](./labs/observability/03-msa-deployment-lab.md) | [测验](./quizzes/observability/labs/03-msa-deployment-quiz.md)
5. [第 4 部分：负载测试和自动扩缩容](./labs/observability/04-load-testing-scaling-lab.md) | [测验](./quizzes/observability/labs/04-load-testing-scaling-quiz.md)
6. [第 5 部分：告警和 AIOps](./labs/observability/05-alerting-aiops-lab.md) | [测验](./quizzes/observability/labs/05-alerting-aiops-quiz.md)
7. [第 6 部分：分布式追踪分析](./labs/observability/06-distributed-tracing-lab.md) | [测验](./quizzes/observability/labs/06-distributed-tracing-quiz.md)

## 学习指南

### 初学者学习路径
1. 按以下顺序学习：**基础概念** -> **Kubernetes 核心概念** -> **Amazon EKS**
2. 阅读每章后，完成相应测验以检查您的理解程度
3. 在练习环境中亲自执行命令和示例代码

### 高级用户学习路径
1. 按以下顺序学习：**Amazon EKS** -> **AI/ML** -> **Service Mesh** -> **安全和策略**
2. 通过 **Cilium** 部分深入学习网络
3. 聚焦特定工具或技术，进行深入学习

### 如何使用测验
- 点击每份文档末尾的测验链接以检查学习效果
- 在查看折叠式答案前先自行思考
- 针对答错的问题复习相应文档

## 贡献

如果您希望为此项目做出贡献：
1. 发现拼写错误或内容错误时，请提交 issue
2. 建议新主题或改进内容
3. 建议增加或改进测验题目

## 许可证

本培训材料可免费用于学习目的。
