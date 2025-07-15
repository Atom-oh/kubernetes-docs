# 아키텍처 다이어그램 개선 작업계획서

이 문서는 Kubernetes 및 Amazon EKS 교육 컨텐츠의 아키텍처 다이어그램을 개선하기 위한 작업계획서입니다. 주요 개선 사항은 다음과 같습니다:
현재 디렉토리에 README.md 파일에 블로그 시작이며 하위 폴더에 세부 문서들이 있습니다.

1. 일반 텍스트나 다른 형식으로 되어있는 아키텍처 다이어그램을 mermaid로 변환
2. 기존 mermaid 다이어그램에 CSS 스타일 적용하여 가독성 향상
3. 다이어그램 구성 요소 간의 관계를 명확히 표현
4. 폰트 색상을 배경과 대비되도록 설정 (주로 black 또는 white)

## 작업 방식
1. 각 문서 파일을 검토하여 아키텍처 다이어그램 식별
2. 다이어그램이 mermaid로 되어있지 않은 경우 변환
3. 기존 mermaid 다이어그램에 CSS 스타일 적용
4. subgraph에는 style 적용 불가
5. 폰트 색상을 배경과 대비되도록 설정
6. 변경사항 적용 및 확인
7. 파일을 수정할때마다 git commit을 하여 history를 관리
8. git root는 현재 디렉토리
   
## CSS 스타일 가이드라인

mermaid 다이어그램에 적용할 CSS 스타일 가이드라인:

```
classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
classDef prometheusComponent fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
classDef victoriaMetrics fill:#4285F4,stroke:#333,stroke-width:1px,color:white;
classDef grafana fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
classDef alerting fill:#EB6E85,stroke:#333,stroke-width:1px,color:white;
classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
```

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
- [x] 1. EKS 소개 (`./eks/01-eks-introduction.md`)
- [x] 2. EKS 클러스터 생성
  - [x] Part 1: 사전 요구 사항 (`./eks/02-eks-cluster-creation-part1.md`)
  - [x] Part 2: eksctl을 사용한 클러스터 생성 (`./eks/02-eks-cluster-creation-part2.md`)
  - [x] Part 3: AWS Management Console 및 CLI를 사용한 클러스터 생성 (`./eks/02-eks-cluster-creation-part3.md`)
  - [x] Part 4: Terraform 및 CDK를 사용한 클러스터 생성 (`./eks/02-eks-cluster-creation-part4.md`)
  - [x] Part 5: 클러스터 액세스, 검증, 업그레이드 및 삭제 (`./eks/02-eks-cluster-creation-part5.md`)
- [x] 3. EKS 네트워킹
  - [x] Part 1: 기본 개념 및 VPC 구성 (`./eks/03-eks-networking-part1.md`)
  - [x] Part 2: 서비스 및 로드 밸런싱, 네트워크 정책 (`./eks/03-eks-networking-part2.md`)
  - [x] Part 3: 성능 최적화, 문제 해결, 고급 사용 사례 (`./eks/03-eks-networking-part3.md`)
- [ ] 4. EKS 스토리지
  - [x] Part 1: 기본 개념, EBS, EFS (`./eks/04-eks-storage-part1.md`)
  - [x] Part 2: FSx for Lustre, S3, 스냅샷, 볼륨 확장, 성능 최적화 (`./eks/04-eks-storage-part2.md`)
  - [x] Part 3: 모니터링, 문제 해결, 비용 최적화, 보안 (`./eks/04-eks-storage-part3.md`)
- [x] 5. EKS 보안 (`./eks/05-eks-security.md`)
- [x] 6. EKS 모니터링 및 로깅 (`./eks/06-eks-monitoring-logging.md`)
- [x] 7. EKS 비용 최적화 (`./eks/07-eks-cost-optimization.md`)
- [ ] 8. EKS 업그레이드 (`./eks/08-eks-upgrades.md`)
- [ ] 9. EKS 문제 해결 (`./eks/09-eks-troubleshooting.md`)

### 고급 주제
- [ ] 1. Kyverno를 사용한 정책 관리 (`./advanced/01-kyverno-policy-management.md`)
- [ ] 2. 커스텀 스케줄러
  - [ ] Part 1: 스케줄링 개요 및 다중 스케줄러 접근 방식 (`./advanced/02-custom-scheduler-part1.md`)
  - [ ] Part 2: 스케줄러 확장 및 스케줄러 프레임워크 플러그인 (`./advanced/02-custom-scheduler-part2.md`)
  - [ ] Part 3: EKS에서의 구현 사례 및 모니터링 (`./advanced/02-custom-scheduler-part3.md`)
- [ ] 3. AI/ML 워크로드 (`./advanced/03-ai-ml-workloads.md`)
- [ ] 4. vLLM 배포 (`./advanced/04-vllm-deployment.md`)

### 도구 및 통합
- [x] 1. ArgoCD (`./tools/01-argocd.md`) - 완료
- [x] 2. Istio (`./tools/02-istio.md`) - 완료
- [x] 3. AWS Controllers for Kubernetes (ACK) (`./tools/03-ack.md`) - 완료
- [x] 4. Cilium (`./tools/04-cilium.md`) - 완료
- [x] 5. KEDA (`./tools/05-keda.md`) - 완료
- [ ] 6. Karpenter (`./tools/06-karpenter.md`)
- [x] 7. 모니터링 스택 (VictoriaMetrics, Prometheus, Grafana) (`./tools/07-monitoring-stack.md`) - 완료
- [ ] 8. 로깅 스택 (Loki, Tempo) (`./tools/08-logging-stack.md`)
- [ ] 9. VPC Lattice (`./tools/09-vpc-lattice.md`)

## 작업 우선순위

1. 핵심 아키텍처 다이어그램부터 개선 (클러스터 아키텍처, EKS 소개 등)
2. 도구 및 통합 섹션의 다이어그램 개선
3. 나머지 문서의 다이어그램 개선

## 현재 작업 중인 문서
- EKS 업그레이드 (`./eks/08-eks-upgrades.md`)
