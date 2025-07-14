# Kubernetes 및 Amazon EKS 교육 컨텐츠 작업 계획서

이 문서는 Kubernetes 및 Amazon EKS 교육 컨텐츠 개발을 위한 작업 계획서입니다. README.md의 목차에 있는 링크들을 확인하고, 누락된 문서를 작성하는 작업을 체계적으로 진행하기 위한 계획을 담고 있습니다.

## 작업 방식
1. README.md의 목차에 있는 링크들을 순차적으로 확인
2. 링크된 문서가 존재하는지 확인
3. 문서가 없는 경우 해당 문서 작성
4. 작업 진행 상황을 이 계획서에 기록

## 작업 진행 상황

### 기초 개념
- [x] 1. Linux 기초 (`./basics/01-linux-basics.md`)
- [x] 2. 컨테이너 기술 (`./basics/02-container-technology.md`)
- [x] 3. Kubernetes 소개 (`./basics/03-kubernetes-introduction.md`)

### Kubernetes 핵심 개념
- [x] 1. 클러스터 아키텍처 (`./core/01-cluster-architecture.md`)
- [x] 2. 파드와 워크로드 (`./core/02-pods-and-workloads.md`)
- [x] 3. 서비스와 네트워킹 (`./core/03-services-networking.md`)
- [x] 4. 스토리지 (`./core/04-storage.md`)
- [x] 5. 구성 (`./core/05-configuration-secrets.md`)
- [x] 6. 보안 (`./core/06-security.md`)
- [x] 7. 정책 (`./core/07-policies.md`)
- [x] 8. 스케줄링, 선점 및 축출 (`./core/08-scheduling-preemption-eviction.md`)
- [x] 9. 클러스터 관리 (`./core/09-cluster-administration.md`)
- [x] 10. Windows in Kubernetes (`./core/10-windows-in-kubernetes.md`)
- [x] 11. Kubernetes 확장 (`./core/11-extending-kubernetes.md`)

### Amazon EKS
- [x] 1. EKS 소개 (`./eks/01-eks-introduction.md`) - 이미 작성됨
- [x] 2. EKS 클러스터 생성 - 이미 작성됨
  - [x] Part 1: 사전 요구 사항 (`./eks/02-eks-cluster-creation-part1.md`)
  - [x] Part 2: eksctl을 사용한 클러스터 생성 (`./eks/02-eks-cluster-creation-part2.md`)
  - [x] Part 3: AWS Management Console 및 CLI를 사용한 클러스터 생성 (`./eks/02-eks-cluster-creation-part3.md`)
  - [x] Part 4: Terraform 및 CDK를 사용한 클러스터 생성 (`./eks/02-eks-cluster-creation-part4.md`)
  - [x] Part 5: 클러스터 액세스, 검증, 업그레이드 및 삭제 (`./eks/02-eks-cluster-creation-part5.md`)
  - [x] 결론 및 모범 사례 (`./eks/02-eks-cluster-creation-conclusion.md`)
- [x] 3. EKS 네트워킹
  - [x] Part 1: 기본 개념 및 VPC 구성 (`./eks/03-eks-networking-part1.md`)
  - [x] Part 2: 서비스 및 로드 밸런싱, 네트워크 정책 (`./eks/03-eks-networking-part2.md`)
  - [x] Part 3: 성능 최적화, 문제 해결, 고급 사용 사례 (`./eks/03-eks-networking-part3.md`)
- [x] 4. EKS 스토리지
  - [x] Part 1: 기본 개념, EBS, EFS (`./eks/04-eks-storage-part1.md`)
  - [x] Part 2: FSx for Lustre, S3, 스냅샷, 볼륨 확장, 성능 최적화 (`./eks/04-eks-storage-part2.md`)
  - [x] Part 3: 모니터링, 문제 해결, 비용 최적화, 보안 (`./eks/04-eks-storage-part3.md`)
- [x] 5. EKS 보안 (`./eks/05-eks-security.md`)
- [x] 6. EKS 모니터링 및 로깅 (`./eks/06-eks-monitoring-logging.md`)
- [x] 7. EKS 비용 최적화 (`./eks/07-eks-cost-optimization.md`)
- [x] 8. EKS 업그레이드 (`./eks/08-eks-upgrades.md`)
- [x] 9. EKS 문제 해결 (`./eks/09-eks-troubleshooting.md`)

### 고급 주제
- [x] 1. Kyverno를 사용한 정책 관리 (`./advanced/01-kyverno-policy-management.md`)
- [x] 2. 커스텀 스케줄러
  - [x] Part 1: 스케줄링 개요 및 다중 스케줄러 접근 방식 (`./advanced/02-custom-scheduler-part1.md`)
  - [x] Part 2: 스케줄러 확장 및 스케줄러 프레임워크 플러그인 (`./advanced/02-custom-scheduler-part2.md`)
  - [x] Part 3: EKS에서의 구현 사례 및 모니터링 (`./advanced/02-custom-scheduler-part3.md`)
- [x] 3. AI/ML 워크로드 (`./advanced/03-ai-ml-workloads.md`)
- [x] 4. vLLM 배포 (`./advanced/04-vllm-deployment.md`)

### 도구 및 통합
- [x] 1. ArgoCD (`./tools/01-argocd.md`)
- [x] 2. Istio (`./tools/02-istio.md`)
- [x] 3. AWS Controllers for Kubernetes (ACK) (`./tools/03-ack.md`)
- [x] 4. Cilium (`./tools/04-cilium.md`)
- [x] 5. KEDA (`./tools/05-keda.md`)
- [x] 6. Karpenter (`./tools/06-karpenter.md`)
- [x] 7. 모니터링 스택 (VictoriaMetrics, Prometheus, Grafana) (`./tools/07-monitoring-stack.md`)
- [x] 8. 로깅 스택 (Loki, Tempo) (`./tools/08-logging-stack.md`)
- [x] 9. VPC Lattice (`./tools/09-vpc-lattice.md`)

## 작업 우선순위

1. 기초 개념 문서 작성 (Linux 기초, 컨테이너 기술, Kubernetes 소개) ✅
2. Kubernetes 핵심 개념 문서 작성 ✅
3. Amazon EKS 관련 문서 작성 (클러스터 생성 파트 2부터) ✅
4. 고급 주제 문서 작성 ✅
5. 도구 및 통합 문서 작성 (진행 중)

## 작업 일정

- 1주차: 기초 개념 및 Kubernetes 핵심 개념 (1-5) ✅
- 2주차: Kubernetes 핵심 개념 (6-11) ✅
- 3주차: Amazon EKS (클러스터 생성 파트 2-5, 네트워킹) ✅
- 4주차: Amazon EKS (스토리지, 보안, 모니터링) ✅
- 5주차: Amazon EKS (비용 최적화, 업그레이드, 문제 해결) 및 고급 주제 (Kyverno, 커스텀 스케줄러) ✅
- 6주차: 고급 주제 (AI/ML 워크로드, vLLM 배포) 및 도구 및 통합 (1-5) ✅
- 7주차: 도구 및 통합 (6-9) 및 전체 검토 (진행 중)

## 현재 작업 중인 문서
- 모든 문서 작성 완료! 전체 검토 단계로 진행 가능합니다.
