# Table of contents

## Introduction

* [Introduction](README.md)

## Basic

* [Linux Basics](basics/01-linux-basics.md)
* [Linux Operations Skills](basics/02-linux-advanced.md)
* [Container Technology](basics/03-container-technology.md)
* [Introduction to Kubernetes](basics/04-kubernetes-introduction.md)

## Kubernetes Core Concepts

* [Cluster Architecture](core/01-cluster-architecture.md)
* [Pods and Workloads](core/02-pods-and-workloads.md)
* [Services and Networking](core/03-services-networking.md)
* [Storage](core/04-storage.md)
* [Configuration](core/05-configuration-secrets.md)
* [Security](core/06-security.md)
* [Policies](core/07-policies.md)
* [Scheduling, Preemption and Eviction](core/08-scheduling-preemption-eviction.md)
* [Cluster Administration](core/09-cluster-administration.md)
* [Windows in Kubernetes](core/10-windows-in-kubernetes.md)
* [Extending Kubernetes](core/11-extending-kubernetes.md)

## Amazon EKS

* [Introduction to EKS](eks/01-eks-introduction.md)
* [EKS Cluster Creation](eks/02-eks-cluster-creation.md)
    * [Part 1: Prerequisites](eks/02-eks-cluster-creation-part1.md)
    * [Part 2: Creating Clusters with eksctl](eks/02-eks-cluster-creation-part2.md)
    * [Part 3: Creating Clusters with AWS Management Console and CLI](eks/02-eks-cluster-creation-part3.md)
    * [Part 4: Creating Clusters with Terraform and CDK](eks/02-eks-cluster-creation-part4.md)
    * [Part 5: Cluster Access, Validation, Upgrade and Deletion](eks/02-eks-cluster-creation-part5.md)
    * [Conclusion](eks/02-eks-cluster-creation-conclusion.md)
* [EKS Networking](eks/03-eks-networking-part1.md)
    * [Part 1: Basic Concepts](eks/03-eks-networking-part1.md)
    * [Part 2: Advanced Configuration](eks/03-eks-networking-part2.md)
    * [Part 3: Troubleshooting](eks/03-eks-networking-part3.md)
* [EKS Storage](eks/04-eks-storage-part1.md)
    * [Part 1: Basic Concepts](eks/04-eks-storage-part1.md)
    * [Part 2: Storage Classes](eks/04-eks-storage-part2.md)
    * [Part 3: Advanced Configuration](eks/04-eks-storage-part3.md)
* [EKS Security](eks/05-eks-security.md)
* [EKS Monitoring and Logging](eks/06-eks-monitoring-logging.md)
* [EKS Cost Optimization](eks/07-eks-cost-optimization.md)
* [EKS Upgrades](eks/08-eks-upgrades.md)
* [EKS Troubleshooting](eks/09-eks-troubleshooting.md)
* [EKS Resiliency and High Availability](eks/10-eks-resiliency.md)
* [EKS Advanced Debugging](eks/11-eks-advanced-debugging.md)
* [EKS Hybrid Nodes](eks/12-eks-hybrid-nodes.md)

## AI/ML

* [AI/ML Workloads](ai-ml/01-ai-ml-workloads.md)
* [vLLM Deployment](ai-ml/02-vllm-deployment.md)
* [Agentic AI Platform on EKS](ai-ml/03-agentic-ai-platform.md)

## Networking

* [Cilium](networking/01-cilium.md)
* [VPC Lattice](networking/02-vpc-lattice.md)

## Service Mesh

* [Istio](service-mesh/istio/README.md)
    * [Installation and Initial Setup](service-mesh/istio/01-installation.md)
    * [Basic Concepts](service-mesh/istio/02-basic-concepts.md)
    * [Architecture](service-mesh/istio/03-architecture.md)
    * [AWS Integration](service-mesh/istio/04-aws-integration.md)
    * [Glossary](service-mesh/istio/glossary.md)
    * [Traffic Management](service-mesh/istio/traffic-management/README.md)
        * [Gateway and VirtualService](service-mesh/istio/traffic-management/01-gateway-virtualservice.md)
        * [Routing](service-mesh/istio/traffic-management/02-routing.md)
        * [DestinationRule](service-mesh/istio/traffic-management/03-destination-rule.md)
        * [Traffic Splitting](service-mesh/istio/traffic-management/04-traffic-splitting.md)
        * [Retry and Timeout](service-mesh/istio/traffic-management/05-retry-timeout.md)
        * [Load Balancing](service-mesh/istio/traffic-management/06-load-balancing.md)
        * [Circuit Breaker](service-mesh/istio/traffic-management/07-circuit-breaker.md)
        * [Fault Injection](service-mesh/istio/traffic-management/08-fault-injection.md)
        * [Traffic Mirroring](service-mesh/istio/traffic-management/09-traffic-mirror.md)
        * [Session Affinity](service-mesh/istio/traffic-management/10-session-affinity.md)
        * [Egress Control](service-mesh/istio/traffic-management/11-egress-control.md)
        * [ServiceEntry](service-mesh/istio/traffic-management/12-service-entry.md)
        * [WorkloadEntry](service-mesh/istio/traffic-management/13-workload-entry.md)
    * [Security](service-mesh/istio/security/README.md)
        * [mTLS](service-mesh/istio/security/01-mtls.md)
        * [Authentication](service-mesh/istio/security/02-authentication.md)
        * [Authorization](service-mesh/istio/security/03-authorization.md)
    * [Observability](service-mesh/istio/observability/README.md)
        * [Metrics](service-mesh/istio/observability/01-metrics.md)
        * [Distributed Tracing](service-mesh/istio/observability/02-tracing.md)
        * [Logging](service-mesh/istio/observability/03-logging.md)
        * [Dashboards](service-mesh/istio/observability/04-dashboards.md)
    * [Resilience](service-mesh/istio/resilience/README.md)
        * [Outlier Detection](service-mesh/istio/resilience/01-outlier-detection.md)
        * [Rate Limiting](service-mesh/istio/resilience/02-rate-limiting.md)
        * [Zone Aware Routing](service-mesh/istio/resilience/03-zone-aware-routing.md)
    * [Advanced](service-mesh/istio/advanced/README.md)
        * [Ambient Mode](service-mesh/istio/advanced/01-ambient-mode.md)
        * [Multi-cluster](service-mesh/istio/advanced/02-multi-cluster.md)
        * [EnvoyFilter](service-mesh/istio/advanced/03-envoy-filter.md)
        * [DNS Caching](service-mesh/istio/advanced/04-dns-cache.md)
        * [gRPC](service-mesh/istio/advanced/05-grpc.md)
        * [WebSocket](service-mesh/istio/advanced/06-websocket.md)
        * [Sidecar Injection](service-mesh/istio/advanced/07-sidecar-injection.md)
        * [Argo Rollouts Integration](service-mesh/istio/advanced/08-argo-rollouts.md)
        * [Zone-Aware Argo Rollouts](service-mesh/istio/advanced/09-zone-aware-argo-rollouts.md)
        * [AutoScaling using istio metrics](service-mesh/istio/advanced/10-keda-autoscaling.md)
    * [Comparison Guide](service-mesh/istio/comparison/README.md)
        * [Service Mesh Solution Comparison](service-mesh/istio/comparison/01-service-mesh-comparison.md)
        * [Istio vs VPC Lattice](service-mesh/istio/comparison/02-istio-vs-lattice.md)
    * [Troubleshooting](service-mesh/istio/troubleshooting/common-errors.md)
    * [Best Practices](service-mesh/istio/best-practices.md)

## Security & Policy

* [Policy Management with Kyverno](security/01-kyverno-policy-management.md)
* [Kubernetes Authentication and Authorization](security/02-kubernetes-auth-authz.md)

## GitOps

* [ArgoCD](gitops/01-argocd.md)

## Autoscaling

* [KEDA](autoscaling/01-keda.md)
* [Karpenter](autoscaling/02-karpenter.md)

## Observability

* [Monitoring Stack (VictoriaMetrics, Prometheus, Grafana)](observability/01-monitoring-stack.md)
* [Logging Stack (Loki, Tempo)](observability/02-logging-stack.md)

## Scheduling

* [Custom Scheduler](scheduling/01-custom-scheduler-part1.md)
    * [Part 1: Basic Concepts](scheduling/01-custom-scheduler-part1.md)
    * [Part 2: Implementation](scheduling/02-custom-scheduler-part2.md)
    * [Part 3: Advanced Features](scheduling/03-custom-scheduler-part3.md)

## Package Management

* [Helm](package-management/01-helm.md)
* [Helm Chart Migration with KRO](package-management/02-kro-helm-migration.md)

## Platform & AWS Integration

* [AWS Controllers for Kubernetes (ACK)](platform/01-ack.md)
* [Kubernetes Extension Mechanisms](platform/02-kubernetes-extensions.md)

## Cilium

* [Introduction to Cilium](cilium/README.md)
    * [Part 1: Introduction](cilium/01-introduction.md)
    * [Part 2: eBPF](cilium/02-ebpf.md)
    * [Part 3: Networking](cilium/03-networking.md)
    * [Part 4: IPAM and Policies](cilium/04-ipam-policy.md)
    * [Part 5: L2-L7 Networking](cilium/05-l2-l7-networking.md)
    * [Part 6: Security and Visibility](cilium/06-security-visibility.md)
    * [Part 7: Advanced Topics](cilium/07-advanced-topics.md)
    * [Networking Concepts](cilium/networking-concepts.md)
* [Glossary](cilium/glossary.md)

## Lab Guides

* [Lab Guides Introduction](labs/README.md)
    * [Linux Basics Lab](labs/basics/01-linux-basics-lab.md)
    * [Linux Operations Skills Lab](labs/basics/02-linux-advanced-lab.md)
    * [Container Technology Lab](labs/basics/03-container-technology-lab.md)
    * [Pods and Workloads Lab](labs/core/02-pods-and-workloads-lab.md)
    * [Services and Networking Lab](labs/core/03-services-networking-lab.md)
    * [Storage Lab](labs/core/04-storage-lab.md)
    * [ConfigMap and Secret Lab](labs/core/05-configuration-secrets-lab.md)
    * [EKS Cluster Creation Lab](labs/eks/01-eks-cluster-creation-lab.md)

## Quiz Collection
* [Quiz Collection - Quizzes by Topic](quizzes/README.md)
    * [Linux Basics Quiz](quizzes/basics/01-linux-basics-quiz.md)
    * [Linux Operations Skills Quiz](quizzes/basics/02-linux-advanced-quiz.md)
    * [Container Technology Quiz](quizzes/basics/03-container-technology-quiz.md)
    * [Introduction to Kubernetes Quiz](quizzes/basics/04-kubernetes-introduction-quiz.md)
* [Cluster Architecture Quiz](quizzes/core/01-cluster-architecture-quiz.md)
    * [Pods and Workloads Quiz](quizzes/core/02-pods-and-workloads-quiz.md)
    * [Services and Networking Quiz](quizzes/core/03-services-networking-quiz.md)
    * [Storage Quiz](quizzes/core/04-storage-quiz.md)
    * [Configuration Quiz](quizzes/core/05-configuration-secrets-quiz.md)
    * [Security Quiz](quizzes/core/06-security-quiz.md)
    * [Policies Quiz](quizzes/core/07-policies-quiz.md)
    * [Scheduling, Preemption and Eviction Quiz](quizzes/core/08-scheduling-preemption-eviction-quiz.md)
    * [Cluster Administration Quiz](quizzes/core/09-cluster-administration-quiz.md)
    * [Windows in Kubernetes Quiz](quizzes/core/10-windows-in-kubernetes-quiz.md)
    * [Extending Kubernetes Quiz](quizzes/core/11-extending-kubernetes-quiz.md)
* Amazon EKS
    * [Introduction to EKS Quiz](quizzes/eks/01-eks-introduction-quiz.md)
    * [EKS Cluster Creation Quiz - Part 1](quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
    * [EKS Cluster Creation Quiz - Part 2](quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
    * [EKS Cluster Creation Quiz - Part 3](quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
    * [EKS Cluster Creation Quiz - Part 4](quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
    * [EKS Cluster Creation Quiz - Part 5](quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
    * [EKS Networking Quiz - Part 1](quizzes/eks/03-eks-networking-part1-quiz.md)
    * [EKS Networking Quiz - Part 2](quizzes/eks/03-eks-networking-part2-quiz.md)
    * [EKS Networking Quiz - Part 3](quizzes/eks/03-eks-networking-part3-quiz.md)
    * [EKS Storage Quiz - Part 1](quizzes/eks/04-eks-storage-part1-quiz.md)
    * [EKS Storage Quiz - Part 2](quizzes/eks/04-eks-storage-part2-quiz.md)
    * [EKS Storage Quiz - Part 3](quizzes/eks/04-eks-storage-part3-quiz.md)
    * [EKS Security Quiz](quizzes/eks/05-eks-security-quiz.md)
    * [EKS Monitoring and Logging Quiz](quizzes/eks/06-eks-monitoring-logging-quiz.md)
    * [EKS Cost Optimization Quiz](quizzes/eks/07-eks-cost-optimization-quiz.md)
    * [EKS Upgrades Quiz](quizzes/eks/08-eks-upgrades-quiz.md)
    * [EKS Troubleshooting Quiz](quizzes/eks/09-eks-troubleshooting-quiz.md)
    * [EKS Resiliency and High Availability Quiz](quizzes/eks/10-eks-resiliency-quiz.md)
    * [EKS Advanced Debugging Quiz](quizzes/eks/11-eks-advanced-debugging-quiz.md)
    * [EKS Hybrid Nodes Quiz](quizzes/eks/12-eks-hybrid-nodes-quiz.md)
* Cilium
    * [Part 1: Introduction Quiz](quizzes/cilium/01-introduction-quiz.md)
    * [Part 2: eBPF Quiz](quizzes/cilium/02-ebpf-quiz.md)
    * [Part 3: Networking Quiz](quizzes/cilium/03-networking-quiz.md)
    * [Part 4: IPAM and Policies Quiz](quizzes/cilium/04-ipam-policy-quiz.md)
    * [Part 5: L2-L7 Networking Quiz](quizzes/cilium/05-l2-l7-networking-quiz.md)
    * [Part 6: Security and Visibility Quiz](quizzes/cilium/06-security-visibility-quiz.md)
    * [Part 7: Advanced Topics Quiz](quizzes/cilium/07-advanced-topics-quiz.md)
    * [Networking Concepts Quiz](quizzes/cilium/networking-concepts-quiz.md)
    * [Glossary Quiz](quizzes/cilium/glossary-quiz.md)

* AI/ML
    * [AI/ML Workloads Quiz](quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
    * [vLLM Deployment Quiz](quizzes/ai-ml/04-vllm-deployment-quiz.md)
    * [Agentic AI Platform on EKS Quiz](quizzes/ai-ml/08-agentic-ai-platform-quiz.md)

* Networking
    * [Cilium Quiz](quizzes/networking/04-cilium-quiz.md)
    * [VPC Lattice Quiz](quizzes/networking/09-vpc-lattice-quiz.md)

* Service Mesh
    * [Istio Quiz](quizzes/service-mesh/02-istio-quiz.md)
    * Istio Detailed Quiz
        * [Traffic Management Quiz](quizzes/service-mesh/istio/traffic-management.md)
        * [Security Quiz](quizzes/service-mesh/istio/security.md)
        * [Observability Quiz](quizzes/service-mesh/istio/observability.md)
        * [Resilience Quiz](quizzes/service-mesh/istio/resilience.md)
        * [Advanced Quiz](quizzes/service-mesh/istio/advanced.md)
        * [Basic Quiz](quizzes/service-mesh/istio/basic.md)

* Security & Policy
    * [Policy Management with Kyverno Quiz](quizzes/security/01-kyverno-policy-management-quiz.md)
    * [Kubernetes Authentication and Authorization Quiz](quizzes/security/06-kubernetes-auth-authz-quiz.md)

* GitOps
    * [ArgoCD Quiz](quizzes/gitops/01-argocd-quiz.md)

* Autoscaling
    * [KEDA Quiz](quizzes/autoscaling/05-keda-quiz.md)
    * [Karpenter Quiz](quizzes/autoscaling/06-karpenter-quiz.md)

* Observability
    * [Monitoring Stack Quiz](quizzes/observability/07-monitoring-stack-quiz.md)
    * [Logging Stack Quiz](quizzes/observability/08-logging-stack-quiz.md)

* Scheduling
    * [Custom Scheduler Quiz - Part 1](quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
    * [Custom Scheduler Quiz - Part 2](quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
    * [Custom Scheduler Quiz - Part 3](quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

* Package Management
    * [Helm Quiz](quizzes/package-management/10-helm-quiz.md)
    * [Helm Chart Migration with KRO Quiz](quizzes/package-management/05-kro-helm-migration-quiz.md)

* Platform & AWS Integration
    * [AWS Controllers for Kubernetes (ACK) Quiz](quizzes/platform/03-ack-quiz.md)
    * [Kubernetes Extension Mechanisms Quiz](quizzes/platform/07-kubernetes-extensions-quiz.md)
