# Table of contents

## 소개

* [소개](README.md)

## 기초 개념

* [Linux 기초](basics/01-linux-basics.md)
* [컨테이너 기술](basics/02-container-technology.md)
* [Kubernetes 소개](basics/03-kubernetes-introduction.md)

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

## 고급 주제

* [Kyverno를 사용한 정책 관리](advanced/01-kyverno-policy-management.md)
* [커스텀 스케줄러](advanced/02-custom-scheduler-part1.md)
    * [Part 1: 기본 개념](advanced/02-custom-scheduler-part1.md)
    * [Part 2: 구현](advanced/02-custom-scheduler-part2.md)
    * [Part 3: 고급 기능](advanced/02-custom-scheduler-part3.md)
* [AI/ML 워크로드](advanced/03-ai-ml-workloads.md)
* [vLLM 배포](advanced/04-vllm-deployment.md)

## Cilium

* [Cilium 소개](cilium/README.md)
* [Day 1: 소개](cilium/day1-introduction.md)
* [Day 2: eBPF](cilium/day2-ebpf.md)
* [Day 3: 네트워킹](cilium/day3-networking.md)
* [Day 4: IPAM 및 정책](cilium/day4-ipam-policy.md)
* [Day 5: L2-L7 네트워킹](cilium/day5-l2-l7-networking.md)
* [Day 6: 보안 및 가시성](cilium/day6-security-visibility.md)
* [Day 7: 고급 주제](cilium/day7-advanced-topics.md)
* [네트워킹 개념](cilium/networking-concepts.md)
* [용어집](cilium/glossary.md)

## 도구 및 통합

* [ArgoCD](tools/01-argocd.md)
* [Istio](tools/02-istio.md)
* [AWS Controllers for Kubernetes (ACK)](tools/03-ack.md)
* [Cilium](tools/04-cilium.md)
* [KEDA](tools/05-keda.md)
* [Karpenter](tools/06-karpenter.md)
* [모니터링 스택 (VictoriaMetrics, Prometheus, Grafana)](tools/07-monitoring-stack.md)
* [로깅 스택 (Loki, Tempo)](tools/08-logging-stack.md)
* [VPC Lattice](tools/09-vpc-lattice.md)

## Quiz 모음
* [퀴즈 모음 - 주제별 퀴즈](quizzes/README.md)