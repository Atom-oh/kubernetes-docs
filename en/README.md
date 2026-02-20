> [한국어 버전](https://atomoh.gitbook.io/kubernetes-docs/)

# Kubernetes and Amazon EKS Training Content
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

This repository provides comprehensive training materials on Kubernetes and Amazon EKS. It covers everything from Linux basics to containerization, Kubernetes orchestration, and advanced features of Amazon EKS.

## Learning Materials and Quizzes

This training content provides quizzes for each topic along with the learning materials. You can test and reinforce what you've learned through the quizzes. Each quiz is designed with toggle-style answers that are hidden, allowing you to attempt the questions first before revealing the answers.

- [Learning Materials Table of Contents](#table-of-contents) - Learning materials by topic
- [Quiz Collection](./quizzes/README.md) - Quizzes by topic

## Table of Contents

### Basic Concepts
1. [Linux Basics](./basics/01-linux-basics.md) | [Quiz](./quizzes/basics/01-linux-basics-quiz.md) | [Lab](./labs/basics/01-linux-basics-lab.md)
2. [Linux Operations Skills](./basics/02-linux-advanced.md) | [Quiz](./quizzes/basics/02-linux-advanced-quiz.md) | [Lab](./labs/basics/02-linux-advanced-lab.md)
3. [Container Technology](./basics/03-container-technology.md) | [Quiz](./quizzes/basics/03-container-technology-quiz.md) | [Lab](./labs/basics/03-container-technology-lab.md)
4. [Introduction to Kubernetes](./basics/04-kubernetes-introduction.md) | [Quiz](./quizzes/basics/04-kubernetes-introduction-quiz.md)
5. [eBPF Fundamentals and Practical Applications](./basics/05-ebpf-fundamentals.md) | [Quiz](./quizzes/basics/05-ebpf-fundamentals-quiz.md)

### Kubernetes Core Concepts
1. [Cluster Architecture](./core/01-cluster-architecture.md) | [Quiz](./quizzes/core/01-cluster-architecture-quiz.md)
2. [Pods and Workloads](./core/02-pods-and-workloads.md) | [Quiz](./quizzes/core/02-pods-and-workloads-quiz.md)
3. [Services and Networking](./core/03-services-networking.md) | [Quiz](./quizzes/core/03-services-networking-quiz.md)
4. [Storage](./core/04-storage.md) | [Quiz](./quizzes/core/04-storage-quiz.md)
5. [Configuration](./core/05-configuration-secrets.md) | [Quiz](./quizzes/core/05-configuration-secrets-quiz.md)
6. [Security](./core/06-security.md) | [Quiz](./quizzes/core/06-security-quiz.md)
7. [Policies](./core/07-policies.md) | [Quiz](./quizzes/core/07-policies-quiz.md)
8. [Scheduling, Preemption and Eviction](./core/08-scheduling-preemption-eviction.md) | [Quiz](./quizzes/core/08-scheduling-preemption-eviction-quiz.md)
9. [Cluster Administration](./core/09-cluster-administration.md) | [Quiz](./quizzes/core/09-cluster-administration-quiz.md)
10. [Windows in Kubernetes](./core/10-windows-in-kubernetes.md) | [Quiz](./quizzes/core/10-windows-in-kubernetes-quiz.md)
11. [Extending Kubernetes](./core/11-extending-kubernetes.md) | [Quiz](./quizzes/core/11-extending-kubernetes-quiz.md)

### Amazon EKS
1. [Introduction to EKS](./eks/01-eks-introduction.md) | [Quiz](./quizzes/eks/01-eks-introduction-quiz.md)
2. EKS Cluster Creation
   - [Part 1: Prerequisites](./eks/02-eks-cluster-creation-part1.md) | [Quiz](./quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
   - [Part 2: Creating Clusters with eksctl](./eks/02-eks-cluster-creation-part2.md) | [Quiz](./quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
   - [Part 3: Creating Clusters with AWS Management Console and CLI](./eks/02-eks-cluster-creation-part3.md) | [Quiz](./quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
   - [Part 4: Creating Clusters with Terraform and CDK](./eks/02-eks-cluster-creation-part4.md) | [Quiz](./quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
   - [Part 5: Cluster Access, Validation, Upgrade and Deletion](./eks/02-eks-cluster-creation-part5.md) | [Quiz](./quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
3. EKS Networking
   - [Part 1: Basic Concepts and VPC Configuration](./eks/03-eks-networking-part1.md) | [Quiz](./quizzes/eks/03-eks-networking-part1-quiz.md)
   - [Part 2: Services and Load Balancing, Network Policies](./eks/03-eks-networking-part2.md) | [Quiz](./quizzes/eks/03-eks-networking-part2-quiz.md)
   - [Part 3: Performance Optimization, Troubleshooting, Advanced Use Cases](./eks/03-eks-networking-part3.md) | [Quiz](./quizzes/eks/03-eks-networking-part3-quiz.md)
4. EKS Storage
   - [Part 1: Basic Concepts, EBS, EFS](./eks/04-eks-storage-part1.md) | [Quiz](./quizzes/eks/04-eks-storage-part1-quiz.md)
   - [Part 2: FSx for Lustre, S3, Snapshots, Volume Expansion, Performance Optimization](./eks/04-eks-storage-part2.md) | [Quiz](./quizzes/eks/04-eks-storage-part2-quiz.md)
   - [Part 3: Monitoring, Troubleshooting, Cost Optimization, Security](./eks/04-eks-storage-part3.md) | [Quiz](./quizzes/eks/04-eks-storage-part3-quiz.md)
5. [EKS Security](./eks/05-eks-security.md) | [Quiz](./quizzes/eks/05-eks-security-quiz.md)
6. [EKS Monitoring and Logging](./eks/06-eks-monitoring-logging.md) | [Quiz](./quizzes/eks/06-eks-monitoring-logging-quiz.md)
7. [EKS Cost Optimization](./eks/07-eks-cost-optimization.md) | [Quiz](./quizzes/eks/07-eks-cost-optimization-quiz.md)
8. [EKS Upgrades](./eks/08-eks-upgrades.md) | [Quiz](./quizzes/eks/08-eks-upgrades-quiz.md)
9. [EKS Troubleshooting](./eks/09-eks-troubleshooting.md) | [Quiz](./quizzes/eks/09-eks-troubleshooting-quiz.md)
10. [EKS Resiliency and High Availability](./eks/10-eks-resiliency.md) | [Quiz](./quizzes/eks/10-eks-resiliency-quiz.md)
11. [EKS Advanced Debugging](./eks/11-eks-advanced-debugging.md) | [Quiz](./quizzes/eks/11-eks-advanced-debugging-quiz.md)

### EKS Hybrid Nodes
1. [EKS Hybrid Nodes Introduction](./eks-hybrid-nodes/README.md)
2. [Prerequisites](./eks-hybrid-nodes/01-prerequisites.md) | [Quiz](./quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
3. [Network Configuration](./eks-hybrid-nodes/02-network-configuration.md) | [Quiz](./quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
4. [Air-Gap Environment Setup](./eks-hybrid-nodes/03-airgap-setup.md) | [Quiz](./quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
5. [Node Bootstrap](./eks-hybrid-nodes/04-node-bootstrap.md) | [Quiz](./quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
6. [GPU Server Integration](./eks-hybrid-nodes/05-gpu-integration.md) | [Quiz](./quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
7. [Workload Placement Strategies](./eks-hybrid-nodes/06-workload-placement.md) | [Quiz](./quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
8. [Cost Optimization](./eks-hybrid-nodes/07-cost-optimization.md) | [Quiz](./quizzes/eks-hybrid-nodes/07-cost-optimization-quiz.md)
9. [Operations and Maintenance](./eks-hybrid-nodes/08-operations.md) | [Quiz](./quizzes/eks-hybrid-nodes/08-operations-quiz.md)

### EKS Auto Mode
1. [EKS Auto Mode Introduction](./eks-auto-mode/README.md)
2. [Getting Started](./eks-auto-mode/01-getting-started.md) | [Quiz](./quizzes/eks-auto-mode/01-getting-started-quiz.md)
3. [NodePool Configuration](./eks-auto-mode/02-nodepool-configuration.md) | [Quiz](./quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
4. [Scaling Behavior](./eks-auto-mode/03-scaling-behavior.md) | [Quiz](./quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
5. [Spot Instance Strategies](./eks-auto-mode/04-spot-strategies.md) | [Quiz](./quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
6. [Operations and Management](./eks-auto-mode/05-operations.md) | [Quiz](./quizzes/eks-auto-mode/05-operations-quiz.md)
7. [Cost Management](./eks-auto-mode/06-cost-management.md) | [Quiz](./quizzes/eks-auto-mode/06-cost-management-quiz.md)
8. [Node Lifecycle](./eks-auto-mode/07-node-lifecycle.md) | [Quiz](./quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
9. [Workload Optimization](./eks-auto-mode/08-workload-optimization.md) | [Quiz](./quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
10. [Migration Guide](./eks-auto-mode/09-migration-guide.md) | [Quiz](./quizzes/eks-auto-mode/09-migration-guide-quiz.md)

### Cilium
1. [Introduction to Cilium](./cilium/README.md)
2. [Part 1: Introduction](./cilium/01-introduction.md) | [Quiz](./quizzes/cilium/01-introduction-quiz.md)
3. [Part 2: eBPF](./cilium/02-ebpf.md) | [Quiz](./quizzes/cilium/02-ebpf-quiz.md)
4. [Part 3: Networking](./cilium/03-networking.md) | [Quiz](./quizzes/cilium/03-networking-quiz.md)
5. [Part 4: IPAM and Policies](./cilium/04-ipam-policy.md) | [Quiz](./quizzes/cilium/04-ipam-policy-quiz.md)
6. [Part 5: L2-L7 Networking](./cilium/05-l2-l7-networking.md) | [Quiz](./quizzes/cilium/05-l2-l7-networking-quiz.md)
7. [Part 6: Security and Visibility](./cilium/06-security-visibility.md) | [Quiz](./quizzes/cilium/06-security-visibility-quiz.md)
8. [Part 7: Advanced Topics](./cilium/07-advanced-topics.md) | [Quiz](./quizzes/cilium/07-advanced-topics-quiz.md)
9. [Networking Concepts](./cilium/networking-concepts.md) | [Quiz](./quizzes/cilium/networking-concepts-quiz.md)
10. [Glossary](./cilium/glossary.md) | [Quiz](./quizzes/cilium/glossary-quiz.md)

### AI/ML
1. [AI/ML Workloads](./ai-ml/01-ai-ml-workloads.md) | [Quiz](./quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
2. [vLLM Deployment](./ai-ml/02-vllm-deployment.md) | [Quiz](./quizzes/ai-ml/04-vllm-deployment-quiz.md)
3. [Agentic AI Platform on EKS](./ai-ml/03-agentic-ai-platform.md) | [Quiz](./quizzes/ai-ml/08-agentic-ai-platform-quiz.md)

### Networking
1. [Cilium](./networking/01-cilium.md) | [Quiz](./quizzes/networking/04-cilium-quiz.md)
2. [VPC Lattice](./networking/02-vpc-lattice.md) | [Quiz](./quizzes/networking/09-vpc-lattice-quiz.md)

### Service Mesh
1. [Istio](./service-mesh/02-istio.md) | [Quiz](./quizzes/service-mesh/02-istio-quiz.md)
2. [Linkerd](./service-mesh/03-linkerd.md) | [Quiz](./quizzes/service-mesh/03-linkerd-quiz.md)
3. [Cilium Service Mesh](./service-mesh/04-cilium-service-mesh.md) | [Quiz](./quizzes/service-mesh/04-cilium-service-mesh-quiz.md)

### Security & Policy
1. [Policy Management with Kyverno](./security/01-kyverno-policy-management.md) | [Quiz](./quizzes/security/01-kyverno-policy-management-quiz.md)
2. [Kubernetes Authentication and Authorization](./security/02-kubernetes-auth-authz.md) | [Quiz](./quizzes/security/06-kubernetes-auth-authz-quiz.md)

### GitOps
1. [ArgoCD](./gitops/01-argocd.md) | [Quiz](./quizzes/gitops/01-argocd-quiz.md)

### Autoscaling
1. [KEDA](./autoscaling/01-keda.md) | [Quiz](./quizzes/autoscaling/05-keda-quiz.md)
2. [Karpenter](./autoscaling/02-karpenter.md) | [Quiz](./quizzes/autoscaling/06-karpenter-quiz.md)

### Observability
1. [Observability Overview](./observability/README.md)
2. **Metrics**
   - [Metrics Overview](./observability/metrics/README.md) | [Quiz](./quizzes/observability/metrics/00-metrics-overview-quiz.md)
   - [Prometheus](./observability/metrics/01-prometheus.md) | [Quiz](./quizzes/observability/metrics/01-prometheus-quiz.md)
   - [VictoriaMetrics](./observability/metrics/02-victoriametrics.md) | [Quiz](./quizzes/observability/metrics/02-victoriametrics-quiz.md)
   - [Grafana Mimir](./observability/metrics/03-mimir.md) | [Quiz](./quizzes/observability/metrics/03-mimir-quiz.md)
   - [CloudWatch Metrics](./observability/metrics/04-cloudwatch-metrics.md) | [Quiz](./quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
   - [Datadog](./observability/metrics/05-datadog.md) | [Quiz](./quizzes/observability/metrics/05-datadog-quiz.md)
3. **Logging**
   - [Logging Overview](./observability/logging/README.md)
   - [Grafana Loki](./observability/logging/01-loki.md) | [Quiz](./quizzes/observability/logging/01-loki-quiz.md)
   - [OpenSearch](./observability/logging/02-opensearch.md) | [Quiz](./quizzes/observability/logging/02-opensearch-quiz.md)
   - [CloudWatch Logs](./observability/logging/03-cloudwatch-logs.md) | [Quiz](./quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
   - [ClickHouse](./observability/logging/04-clickhouse.md) | [Quiz](./quizzes/observability/logging/04-clickhouse-quiz.md)
   - [Log Collectors](./observability/logging/05-collectors.md) | [Quiz](./quizzes/observability/logging/05-collectors-quiz.md)
4. **Tracing**
   - [Tracing Overview](./observability/tracing/README.md)
   - [Grafana Tempo](./observability/tracing/01-tempo.md) | [Quiz](./quizzes/observability/tracing/01-tempo-quiz.md)
   - [AWS X-Ray](./observability/tracing/02-xray.md) | [Quiz](./quizzes/observability/tracing/02-xray-quiz.md)
   - [OpenTelemetry](./observability/tracing/03-opentelemetry.md) | [Quiz](./quizzes/observability/tracing/03-opentelemetry-quiz.md)
   - [Dynatrace](./observability/tracing/04-dynatrace.md) | [Quiz](./quizzes/observability/tracing/04-dynatrace-quiz.md)
5. **Alerting**
   - [Alerting Overview](./observability/alerting/README.md)
   - [Alertmanager](./observability/alerting/01-alertmanager.md) | [Quiz](./quizzes/observability/alerting/01-alertmanager-quiz.md)
   - [CloudWatch Alarms](./observability/alerting/02-cloudwatch-alarms.md) | [Quiz](./quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
   - [Grafana OnCall](./observability/alerting/03-grafana-oncall.md) | [Quiz](./quizzes/observability/alerting/03-grafana-oncall-quiz.md)
6. [Grafana](./observability/grafana/README.md) | [Quiz](./quizzes/observability/grafana/grafana-quiz.md)
7. [Observability Optimization Guide](./advanced/09-observability-optimization.md) | [Quiz](./quizzes/advanced/09-observability-optimization-quiz.md)

### Scheduling
1. Custom Scheduler
   - [Part 1: Custom Scheduler Basics](./scheduling/01-custom-scheduler-part1.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
   - [Part 2: Scheduler Extensions and Framework](./scheduling/02-custom-scheduler-part2.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
   - [Part 3: Custom Scheduler Implementation Examples and Monitoring](./scheduling/03-custom-scheduler-part3.md) | [Quiz](./quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

### Package Management
1. [Helm](./package-management/01-helm.md) | [Quiz](./quizzes/package-management/10-helm-quiz.md)
2. [Helm Chart Migration with KRO](./package-management/02-kro-helm-migration.md) | [Quiz](./quizzes/package-management/05-kro-helm-migration-quiz.md)

### Platform & AWS Integration
1. [AWS Controllers for Kubernetes (ACK)](./platform/01-ack.md) | [Quiz](./quizzes/platform/03-ack-quiz.md)
2. [Kubernetes Extension Mechanisms](./platform/02-kubernetes-extensions.md) | [Quiz](./quizzes/platform/07-kubernetes-extensions-quiz.md)

### Operations Guide
1. [Infrastructure Setup](./ops/01-infrastructure-setup.md) | [Quiz](./quizzes/ops/01-infrastructure-setup-quiz.md)
2. [Infrastructure Advanced](./ops/02-infrastructure-advanced.md) | [Quiz](./quizzes/ops/02-infrastructure-advanced-quiz.md)
3. [CI Pipelines](./ops/03-ci-pipelines.md) | [Quiz](./quizzes/ops/03-ci-pipelines-quiz.md)
4. [GitOps Multi-Cluster](./ops/04-gitops-multi-cluster.md) | [Quiz](./quizzes/ops/04-gitops-multi-cluster-quiz.md)
5. [GitOps Automation](./ops/05-gitops-automation.md) | [Quiz](./quizzes/ops/05-gitops-automation-quiz.md)
6. [Scaling Strategies](./ops/06-scaling-strategies.md) | [Quiz](./quizzes/ops/06-scaling-strategies-quiz.md)
7. [Observability Alerts](./ops/07-observability-alerts.md) | [Quiz](./quizzes/ops/07-observability-alerts-quiz.md)
8. [Observability Analysis](./ops/08-observability-analysis.md) | [Quiz](./quizzes/ops/08-observability-analysis-quiz.md)
9. [Observability Stack](./ops/09-observability-stack.md) | [Quiz](./quizzes/ops/09-observability-stack-quiz.md)
10. [Resource Optimization](./ops/10-resource-optimization.md) | [Quiz](./quizzes/ops/10-resource-optimization-quiz.md)
11. [Upgrade Operations](./ops/11-upgrade-operations.md) | [Quiz](./quizzes/ops/11-upgrade-operations-quiz.md)

## Lab Guides

We provide hands-on lab guides for practicing in real environments after learning the theory.

- [Lab Guides List](./labs/README.md)
- Basics: Linux Basics, Linux Operations, Container Labs
- Core: Pod, Service, Storage, ConfigMap Labs
- EKS: Cluster Creation Lab

## Learning Guide

### Learning Path for Beginners
1. Study in this order: **Basic Concepts** -> **Kubernetes Core Concepts** -> **Amazon EKS**
2. After reading each chapter, take the corresponding quiz to check your understanding
3. Execute commands and example code hands-on in a practice environment

### Learning Path for Advanced Users
1. Study in this order: **Amazon EKS** -> **AI/ML** -> **Service Mesh** -> **Security & Policy**
2. Deep dive into networking with the **Cilium** section
3. Focus on specific tools or technologies for in-depth learning

### How to Use Quizzes
- Click the quiz link at the end of each document to check your learning
- Think about the toggle-style answers first before revealing them
- Review the corresponding document for any questions you got wrong

## Contributing

If you'd like to contribute to this project:
1. Submit an issue when you find typos or content errors
2. Suggest new topics or improvements
3. Suggest additions or improvements to quiz questions

## License

This training material is free to use for learning purposes.
