# Table of contents

## 소개

* [소개](README.md)

## Basic

* [Linux 기초](basics/01-linux-basics.md)
* [Linux 운영 기술](basics/02-linux-advanced.md)
* [컨테이너 기술](basics/03-container-technology.md)
* [Kubernetes 소개](basics/04-kubernetes-introduction.md)
* [eBPF 기초와 실무 활용](basics/05-ebpf-fundamentals.md)

## Kubernetes 핵심 개념

* [클러스터 아키텍처](core/01-cluster-architecture.md)
* [파드와 워크로드](core/02-pods-and-workloads.md)
* [서비스와 네트워킹](core/03-services-networking.md)
* [스토리지](core/04-storage.md)
* [구성](core/05-configuration-secrets.md)
* [보안](core/06-security.md)
* [정책](core/07-policies.md)
* [스케줄링, 선점 및 축출](core/08-scheduling-preemption-eviction.md)
* [클러스터 관리](core/09-cluster-administration.md)
* [Windows in Kubernetes](core/10-windows-in-kubernetes.md)
* [Kubernetes 확장](core/11-extending-kubernetes.md)

## Amazon EKS

* [EKS 소개](eks/01-eks-introduction.md)
* [EKS 클러스터 생성](eks/02-eks-cluster-creation.md)
    * [Part 1: 사전 요구 사항](eks/02-eks-cluster-creation-part1.md)
    * [Part 2: eksctl을 사용한 클러스터 생성](eks/02-eks-cluster-creation-part2.md)
    * [Part 3: AWS Management Console 및 CLI를 사용한 클러스터 생성](eks/02-eks-cluster-creation-part3.md)
    * [Part 4: Terraform 및 CDK를 사용한 클러스터 생성](eks/02-eks-cluster-creation-part4.md)
    * [Part 5: 클러스터 액세스, 검증, 업그레이드 및 삭제](eks/02-eks-cluster-creation-part5.md)
    * [결론](eks/02-eks-cluster-creation-conclusion.md)
* [EKS 네트워킹](eks/03-eks-networking-part1.md)
    * [Part 1: 기본 개념](eks/03-eks-networking-part1.md)
    * [Part 2: 고급 구성](eks/03-eks-networking-part2.md)
    * [Part 3: 문제 해결](eks/03-eks-networking-part3.md)
* [EKS 스토리지](eks/04-eks-storage-part1.md)
    * [Part 1: 기본 개념](eks/04-eks-storage-part1.md)
    * [Part 2: 스토리지 클래스](eks/04-eks-storage-part2.md)
    * [Part 3: 고급 구성](eks/04-eks-storage-part3.md)
* [EKS 보안](eks/05-eks-security.md)
* [EKS 모니터링 및 로깅](eks/06-eks-monitoring-logging.md)
* [EKS 비용 최적화](eks/07-eks-cost-optimization.md)
* [EKS 업그레이드](eks/08-eks-upgrades.md)
* [EKS 문제 해결](eks/09-eks-troubleshooting.md)
* [EKS 복원력과 고가용성](eks/10-eks-resiliency.md)
* [EKS 고급 디버깅](eks/11-eks-advanced-debugging.md)

## EKS Hybrid Nodes

* [EKS Hybrid Nodes](eks-hybrid-nodes/README.md)
    * [사전 요구 사항](eks-hybrid-nodes/01-prerequisites.md)
    * [네트워크 구성](eks-hybrid-nodes/02-network-configuration.md)
    * [에어갭 환경 구성](eks-hybrid-nodes/03-airgap-setup.md)
    * [노드 부트스트랩](eks-hybrid-nodes/04-node-bootstrap.md)
    * [GPU 서버 통합](eks-hybrid-nodes/05-gpu-integration.md)
    * [워크로드 배치 전략](eks-hybrid-nodes/06-workload-placement.md)
    * [비용 최적화](eks-hybrid-nodes/07-cost-optimization.md)
    * [운영 및 유지보수](eks-hybrid-nodes/08-operations.md)

## EKS Auto Mode

* [EKS Auto Mode](eks-auto-mode/README.md)
    * [Auto Mode 시작하기](eks-auto-mode/01-getting-started.md)
    * [NodePool 구성](eks-auto-mode/02-nodepool-configuration.md)
    * [스케일링 동작](eks-auto-mode/03-scaling-behavior.md)
    * [Spot 인스턴스 전략](eks-auto-mode/04-spot-strategies.md)
    * [운영 및 관리](eks-auto-mode/05-operations.md)
    * [비용 관리](eks-auto-mode/06-cost-management.md)
    * [노드 생명주기](eks-auto-mode/07-node-lifecycle.md)
    * [워크로드별 최적화](eks-auto-mode/08-workload-optimization.md)
    * [마이그레이션 가이드](eks-auto-mode/09-migration-guide.md)

## AI/ML

* [AI/ML 워크로드](ai-ml/01-ai-ml-workloads.md)
* [vLLM 배포](ai-ml/02-vllm-deployment.md)
* [Agentic AI 플랫폼](ai-ml/03-agentic-ai-platform.md)

## Networking

* [Cilium](networking/01-cilium.md)
* [VPC Lattice](networking/02-vpc-lattice.md)

## Service Mesh

* [Istio](service-mesh/istio/README.md)
    * [설치 및 초기 설정](service-mesh/istio/01-installation.md)
    * [기본 개념](service-mesh/istio/02-basic-concepts.md)
    * [아키텍처](service-mesh/istio/03-architecture.md)
    * [AWS 통합](service-mesh/istio/04-aws-integration.md)
    * [용어집](service-mesh/istio/glossary.md)
    * [Traffic Management](service-mesh/istio/traffic-management/README.md)
        * [Gateway와 VirtualService](service-mesh/istio/traffic-management/01-gateway-virtualservice.md)
        * [라우팅](service-mesh/istio/traffic-management/02-routing.md)
        * [DestinationRule](service-mesh/istio/traffic-management/03-destination-rule.md)
        * [트래픽 분할](service-mesh/istio/traffic-management/04-traffic-splitting.md)
        * [Retry 및 Timeout](service-mesh/istio/traffic-management/05-retry-timeout.md)
        * [로드 밸런싱](service-mesh/istio/traffic-management/06-load-balancing.md)
        * [Circuit Breaker](service-mesh/istio/traffic-management/07-circuit-breaker.md)
        * [Fault Injection](service-mesh/istio/traffic-management/08-fault-injection.md)
        * [Traffic Mirroring](service-mesh/istio/traffic-management/09-traffic-mirror.md)
        * [Session Affinity](service-mesh/istio/traffic-management/10-session-affinity.md)
        * [Egress 제어](service-mesh/istio/traffic-management/11-egress-control.md)
        * [ServiceEntry](service-mesh/istio/traffic-management/12-service-entry.md)
        * [WorkloadEntry](service-mesh/istio/traffic-management/13-workload-entry.md)
    * [Security](service-mesh/istio/security/README.md)
        * [mTLS](service-mesh/istio/security/01-mtls.md)
        * [인증](service-mesh/istio/security/02-authentication.md)
        * [권한 부여](service-mesh/istio/security/03-authorization.md)
    * [Observability](service-mesh/istio/observability/README.md)
        * [메트릭](service-mesh/istio/observability/01-metrics.md)
        * [분산 추적](service-mesh/istio/observability/02-tracing.md)
        * [로깅](service-mesh/istio/observability/03-logging.md)
        * [대시보드](service-mesh/istio/observability/04-dashboards.md)
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
        * [Argo Rollouts 통합](service-mesh/istio/advanced/08-argo-rollouts.md)
        * [Zone-Aware Argo Rollouts](service-mesh/istio/advanced/09-zone-aware-argo-rollouts.md)
        * [AutoScaling using istio metrics](service-mesh/istio/advanced/10-keda-autoscaling.md)
    * [비교 가이드](service-mesh/istio/comparison/README.md)
        * [Service Mesh 솔루션 비교](service-mesh/istio/comparison/01-service-mesh-comparison.md)
        * [Istio vs VPC Lattice](service-mesh/istio/comparison/02-istio-vs-lattice.md)
    * [Troubleshooting](service-mesh/istio/troubleshooting/common-errors.md)
    * [모범 사례](service-mesh/istio/best-practices.md)
* [Linkerd](service-mesh/03-linkerd.md)
* [Cilium Service Mesh](service-mesh/04-cilium-service-mesh.md)

## Security & Policy

* [Kyverno를 사용한 정책 관리](security/01-kyverno-policy-management.md)
* [Kubernetes 인증 및 권한 부여](security/02-kubernetes-auth-authz.md)

## GitOps

* [ArgoCD](gitops/01-argocd.md)

## Autoscaling

* [KEDA](autoscaling/01-keda.md)
* [Karpenter](autoscaling/02-karpenter.md)

## Observability

* [Observability 개요](observability/README.md)
* [Metrics](observability/metrics/README.md)
    * [Prometheus](observability/metrics/01-prometheus.md)
    * [VictoriaMetrics](observability/metrics/02-victoriametrics.md)
    * [Grafana Mimir](observability/metrics/03-mimir.md)
    * [CloudWatch Metrics](observability/metrics/04-cloudwatch-metrics.md)
    * [Datadog](observability/metrics/05-datadog.md)
* [Logging](observability/logging/README.md)
    * [Grafana Loki](observability/logging/01-loki.md)
    * [OpenSearch](observability/logging/02-opensearch.md)
    * [CloudWatch Logs](observability/logging/03-cloudwatch-logs.md)
    * [ClickHouse](observability/logging/04-clickhouse.md)
    * [Log Collectors](observability/logging/05-collectors.md)
* [Tracing](observability/tracing/README.md)
    * [Grafana Tempo](observability/tracing/01-tempo.md)
    * [AWS X-Ray](observability/tracing/02-xray.md)
    * [OpenTelemetry](observability/tracing/03-opentelemetry.md)
    * [Dynatrace](observability/tracing/04-dynatrace.md)
* [Alerting](observability/alerting/README.md)
    * [Alertmanager](observability/alerting/01-alertmanager.md)
    * [CloudWatch Alarms](observability/alerting/02-cloudwatch-alarms.md)
    * [Grafana OnCall](observability/alerting/03-grafana-oncall.md)
* [Grafana](observability/grafana/README.md)
* [관측성 최적화 가이드](advanced/09-observability-optimization.md)

## Scheduling

* [Custom Scheduler](scheduling/01-custom-scheduler-part1.md)
    * [Part 1: 기본 개념](scheduling/01-custom-scheduler-part1.md)
    * [Part 2: 구현](scheduling/02-custom-scheduler-part2.md)
    * [Part 3: 고급 기능](scheduling/03-custom-scheduler-part3.md)

## Platform Engineering

* [Helm](platform-engineering/01-helm.md)
* [AWS Controllers for Kubernetes (ACK)](platform-engineering/02-ack.md)
  * [S3 및 IAM 예제](platform-engineering/ack/01-s3-iam.md)
  * [SQS 및 SNS 예제](platform-engineering/ack/02-sqs-sns.md)
  * [ELBv2, Route 53, RDS 예제](platform-engineering/ack/03-elbv2-route53-rds.md)
* [Kubernetes Resource Operator (KRO)](platform-engineering/03-kro.md)
* [Kubernetes 확장 메커니즘](platform-engineering/04-kubernetes-extensions.md)
* [ExampleCorp: ACK + KRO 통합 예제](platform-engineering/05-example-corp-app.md)

## Cilium

* [Cilium 소개](cilium/README.md)
    * [Part 1: 소개](cilium/01-introduction.md)
    * [Part 2: eBPF](cilium/02-ebpf.md)
    * [Part 3: 네트워킹](cilium/03-networking.md)
    * [Part 4: IPAM 및 정책](cilium/04-ipam-policy.md)
    * [Part 5: L2-L7 네트워킹](cilium/05-l2-l7-networking.md)
    * [Part 6: 보안 및 가시성](cilium/06-security-visibility.md)
    * [Part 7: 고급 주제](cilium/07-advanced-topics.md)
    * [네트워킹 개념](cilium/networking-concepts.md)
* [용어집](cilium/glossary.md)

## 운영 가이드

* [운영 가이드 소개](ops/README.md)
    * [인프라 구성 기초](ops/01-infrastructure-setup.md)
    * [인프라 구성 고급](ops/02-infrastructure-advanced.md)
    * [CI 파이프라인 구성](ops/03-ci-pipelines.md)
    * [GitOps 멀티 클러스터](ops/04-gitops-multi-cluster.md)
    * [GitOps 자동화](ops/05-gitops-automation.md)
    * [스케일링 전략](ops/06-scaling-strategies.md)
    * [Observability 알림 설정](ops/07-observability-alerts.md)
    * [Observability 분석 방법](ops/08-observability-analysis.md)
    * [Observability 스택 구성](ops/09-observability-stack.md)
    * [리소스 최적화](ops/10-resource-optimization.md)
    * [EKS 업그레이드 운영](ops/11-upgrade-operations.md)

## 실습 가이드

* [실습 가이드 소개](labs/README.md)
    * [Linux 기초 실습](labs/basics/01-linux-basics-lab.md)
    * [Linux 실무 기술 실습](labs/basics/02-linux-advanced-lab.md)
    * [컨테이너 기술 실습](labs/basics/03-container-technology-lab.md)
    * [파드와 워크로드 실습](labs/core/02-pods-and-workloads-lab.md)
    * [서비스와 네트워킹 실습](labs/core/03-services-networking-lab.md)
    * [스토리지 실습](labs/core/04-storage-lab.md)
    * [ConfigMap과 Secret 실습](labs/core/05-configuration-secrets-lab.md)
    * [EKS 클러스터 생성 실습](labs/eks/01-eks-cluster-creation-lab.md)

## Quiz 모음
* [퀴즈 모음 - 주제별 퀴즈](quizzes/README.md)
    * [Linux 기초 퀴즈](quizzes/basics/01-linux-basics-quiz.md)
    * [Linux 운영 기술 퀴즈](quizzes/basics/02-linux-advanced-quiz.md)
    * [컨테이너 기술 퀴즈](quizzes/basics/03-container-technology-quiz.md)
    * [Kubernetes 소개 퀴즈](quizzes/basics/04-kubernetes-introduction-quiz.md)
    * [eBPF 기초와 실무 활용 퀴즈](quizzes/basics/05-ebpf-fundamentals-quiz.md)
* [클러스터 아키텍처 퀴즈](quizzes/core/01-cluster-architecture-quiz.md)
    * [파드와 워크로드 퀴즈](quizzes/core/02-pods-and-workloads-quiz.md)
    * [서비스와 네트워킹 퀴즈](quizzes/core/03-services-networking-quiz.md)
    * [스토리지 퀴즈](quizzes/core/04-storage-quiz.md)
    * [구성 퀴즈](quizzes/core/05-configuration-secrets-quiz.md)
    * [보안 퀴즈](quizzes/core/06-security-quiz.md)
    * [정책 퀴즈](quizzes/core/07-policies-quiz.md)
    * [스케줄링, 선점 및 축출 퀴즈](quizzes/core/08-scheduling-preemption-eviction-quiz.md)
    * [클러스터 관리 퀴즈](quizzes/core/09-cluster-administration-quiz.md)
    * [Windows in Kubernetes 퀴즈](quizzes/core/10-windows-in-kubernetes-quiz.md)
    * [Kubernetes 확장 퀴즈](quizzes/core/11-extending-kubernetes-quiz.md)
* Amazon EKS
    * [EKS 소개 퀴즈](quizzes/eks/01-eks-introduction-quiz.md)
    * [EKS 클러스터 생성 퀴즈 - Part 1](quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
    * [EKS 클러스터 생성 퀴즈 - Part 2](quizzes/eks/02-eks-cluster-creation-part2-quiz.md)
    * [EKS 클러스터 생성 퀴즈 - Part 3](quizzes/eks/02-eks-cluster-creation-part3-quiz.md)
    * [EKS 클러스터 생성 퀴즈 - Part 4](quizzes/eks/02-eks-cluster-creation-part4-quiz.md)
    * [EKS 클러스터 생성 퀴즈 - Part 5](quizzes/eks/02-eks-cluster-creation-part5-quiz.md)
    * [EKS 네트워킹 퀴즈 - Part 1](quizzes/eks/03-eks-networking-part1-quiz.md)
    * [EKS 네트워킹 퀴즈 - Part 2](quizzes/eks/03-eks-networking-part2-quiz.md)
    * [EKS 네트워킹 퀴즈 - Part 3](quizzes/eks/03-eks-networking-part3-quiz.md)
    * [EKS 스토리지 퀴즈 - Part 1](quizzes/eks/04-eks-storage-part1-quiz.md)
    * [EKS 스토리지 퀴즈 - Part 2](quizzes/eks/04-eks-storage-part2-quiz.md)
    * [EKS 스토리지 퀴즈 - Part 3](quizzes/eks/04-eks-storage-part3-quiz.md)
    * [EKS 보안 퀴즈](quizzes/eks/05-eks-security-quiz.md)
    * [EKS 모니터링 및 로깅 퀴즈](quizzes/eks/06-eks-monitoring-logging-quiz.md)
    * [EKS 비용 최적화 퀴즈](quizzes/eks/07-eks-cost-optimization-quiz.md)
    * [EKS 업그레이드 퀴즈](quizzes/eks/08-eks-upgrades-quiz.md)
    * [EKS 문제 해결 퀴즈](quizzes/eks/09-eks-troubleshooting-quiz.md)
    * [EKS 복원력과 고가용성 퀴즈](quizzes/eks/10-eks-resiliency-quiz.md)
    * [EKS 고급 디버깅 퀴즈](quizzes/eks/11-eks-advanced-debugging-quiz.md)

* EKS Hybrid Nodes
    * [사전 요구 사항 퀴즈](quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
    * [네트워크 구성 퀴즈](quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
    * [에어갭 환경 구성 퀴즈](quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
    * [노드 부트스트랩 퀴즈](quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
    * [GPU 서버 통합 퀴즈](quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
    * [워크로드 배치 전략 퀴즈](quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
    * [비용 최적화 퀴즈](quizzes/eks-hybrid-nodes/07-cost-optimization-quiz.md)
    * [운영 및 유지보수 퀴즈](quizzes/eks-hybrid-nodes/08-operations-quiz.md)

* EKS Auto Mode
    * [Auto Mode 시작하기 퀴즈](quizzes/eks-auto-mode/01-getting-started-quiz.md)
    * [NodePool 구성 퀴즈](quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
    * [스케일링 동작 퀴즈](quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
    * [Spot 인스턴스 전략 퀴즈](quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
    * [운영 및 관리 퀴즈](quizzes/eks-auto-mode/05-operations-quiz.md)
    * [비용 관리 퀴즈](quizzes/eks-auto-mode/06-cost-management-quiz.md)
    * [노드 생명주기 퀴즈](quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
    * [워크로드별 최적화 퀴즈](quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
    * [마이그레이션 가이드 퀴즈](quizzes/eks-auto-mode/09-migration-guide-quiz.md)

* Cilium
    * [Part 1: 소개 퀴즈](quizzes/cilium/01-introduction-quiz.md)
    * [Part 2: eBPF 퀴즈](quizzes/cilium/02-ebpf-quiz.md)
    * [Part 3: 네트워킹 퀴즈](quizzes/cilium/03-networking-quiz.md)
    * [Part 4: IPAM 및 정책 퀴즈](quizzes/cilium/04-ipam-policy-quiz.md)
    * [Part 5: L2-L7 네트워킹 퀴즈](quizzes/cilium/05-l2-l7-networking-quiz.md)
    * [Part 6: 보안 및 가시성 퀴즈](quizzes/cilium/06-security-visibility-quiz.md)
    * [Part 7: 고급 주제 퀴즈](quizzes/cilium/07-advanced-topics-quiz.md)
    * [네트워킹 개념 퀴즈](quizzes/cilium/networking-concepts-quiz.md)
    * [용어집 퀴즈](quizzes/cilium/glossary-quiz.md)

* AI/ML
    * [AI/ML 워크로드 퀴즈](quizzes/ai-ml/03-ai-ml-workloads-quiz.md)
    * [vLLM 배포 퀴즈](quizzes/ai-ml/04-vllm-deployment-quiz.md)
    * [Agentic AI 플랫폼 퀴즈](quizzes/ai-ml/08-agentic-ai-platform-quiz.md)

* Networking
    * [Cilium 퀴즈](quizzes/networking/04-cilium-quiz.md)
    * [VPC Lattice 퀴즈](quizzes/networking/09-vpc-lattice-quiz.md)

* Service Mesh
    * [Istio 퀴즈](quizzes/service-mesh/02-istio-quiz.md)
    * Istio 상세 퀴즈
        * [Traffic Management 퀴즈](quizzes/service-mesh/istio/traffic-management.md)
        * [Security 퀴즈](quizzes/service-mesh/istio/security.md)
        * [Observability 퀴즈](quizzes/service-mesh/istio/observability.md)
        * [Resilience 퀴즈](quizzes/service-mesh/istio/resilience.md)
        * [Advanced 퀴즈](quizzes/service-mesh/istio/advanced.md)
        * [Basic 퀴즈](quizzes/service-mesh/istio/basic.md)
    * [Linkerd 퀴즈](quizzes/service-mesh/03-linkerd-quiz.md)
    * [Cilium Service Mesh 퀴즈](quizzes/service-mesh/04-cilium-service-mesh-quiz.md)

* Security & Policy
    * [Kyverno를 사용한 정책 관리 퀴즈](quizzes/security/01-kyverno-policy-management-quiz.md)
    * [Kubernetes 인증 및 권한 부여 퀴즈](quizzes/security/06-kubernetes-auth-authz-quiz.md)

* GitOps
    * [ArgoCD 퀴즈](quizzes/gitops/01-argocd-quiz.md)

* Autoscaling
    * [KEDA 퀴즈](quizzes/autoscaling/05-keda-quiz.md)
    * [Karpenter 퀴즈](quizzes/autoscaling/06-karpenter-quiz.md)

* Observability
    * Metrics
        * [메트릭 개요 퀴즈](quizzes/observability/metrics/00-metrics-overview-quiz.md)
        * [Prometheus 퀴즈](quizzes/observability/metrics/01-prometheus-quiz.md)
        * [VictoriaMetrics 퀴즈](quizzes/observability/metrics/02-victoriametrics-quiz.md)
        * [Grafana Mimir 퀴즈](quizzes/observability/metrics/03-mimir-quiz.md)
        * [CloudWatch Metrics 퀴즈](quizzes/observability/metrics/04-cloudwatch-metrics-quiz.md)
        * [Datadog 퀴즈](quizzes/observability/metrics/05-datadog-quiz.md)
    * Logging
        * [로깅 개요 퀴즈](quizzes/observability/logging/README-quiz.md)
        * [Grafana Loki 퀴즈](quizzes/observability/logging/01-loki-quiz.md)
        * [OpenSearch 퀴즈](quizzes/observability/logging/02-opensearch-quiz.md)
        * [CloudWatch Logs 퀴즈](quizzes/observability/logging/03-cloudwatch-logs-quiz.md)
        * [ClickHouse 퀴즈](quizzes/observability/logging/04-clickhouse-quiz.md)
        * [Log Collectors 퀴즈](quizzes/observability/logging/05-collectors-quiz.md)
    * Tracing
        * [Grafana Tempo 퀴즈](quizzes/observability/tracing/01-tempo-quiz.md)
        * [AWS X-Ray 퀴즈](quizzes/observability/tracing/02-xray-quiz.md)
        * [OpenTelemetry 퀴즈](quizzes/observability/tracing/03-opentelemetry-quiz.md)
        * [Dynatrace 퀴즈](quizzes/observability/tracing/04-dynatrace-quiz.md)
    * Alerting
        * [Alertmanager 퀴즈](quizzes/observability/alerting/01-alertmanager-quiz.md)
        * [CloudWatch Alarms 퀴즈](quizzes/observability/alerting/02-cloudwatch-alarms-quiz.md)
        * [Grafana OnCall 퀴즈](quizzes/observability/alerting/03-grafana-oncall-quiz.md)
    * [Grafana 퀴즈](quizzes/observability/grafana/grafana-quiz.md)
    * [관측성 최적화 가이드 퀴즈](quizzes/advanced/09-observability-optimization-quiz.md)

* Scheduling
    * [Custom Scheduler 퀴즈 - Part 1](quizzes/scheduling/02-custom-scheduler-part1-quiz.md)
    * [Custom Scheduler 퀴즈 - Part 2](quizzes/scheduling/02-custom-scheduler-part2-quiz.md)
    * [Custom Scheduler 퀴즈 - Part 3](quizzes/scheduling/02-custom-scheduler-part3-quiz.md)

* Platform Engineering
    * [Helm 퀴즈](quizzes/platform-engineering/01-helm-quiz.md)
    * [ACK 퀴즈](quizzes/platform-engineering/02-ack-quiz.md)
    * [KRO 퀴즈](quizzes/platform-engineering/03-kro-quiz.md)
    * [Kubernetes 확장 메커니즘 퀴즈](quizzes/platform-engineering/04-kubernetes-extensions-quiz.md)

* 운영 가이드
    * [인프라 구성 기초 퀴즈](quizzes/ops/01-infrastructure-setup-quiz.md)
    * [인프라 구성 고급 퀴즈](quizzes/ops/02-infrastructure-advanced-quiz.md)
    * [CI 파이프라인 구성 퀴즈](quizzes/ops/03-ci-pipelines-quiz.md)
    * [GitOps 멀티 클러스터 퀴즈](quizzes/ops/04-gitops-multi-cluster-quiz.md)
    * [GitOps 자동화 퀴즈](quizzes/ops/05-gitops-automation-quiz.md)
    * [스케일링 전략 퀴즈](quizzes/ops/06-scaling-strategies-quiz.md)
    * [Observability 알림 설정 퀴즈](quizzes/ops/07-observability-alerts-quiz.md)
    * [Observability 분석 방법 퀴즈](quizzes/ops/08-observability-analysis-quiz.md)
    * [Observability 스택 구성 퀴즈](quizzes/ops/09-observability-stack-quiz.md)
    * [리소스 최적화 퀴즈](quizzes/ops/10-resource-optimization-quiz.md)
    * [EKS 업그레이드 운영 퀴즈](quizzes/ops/11-upgrade-operations-quiz.md)
