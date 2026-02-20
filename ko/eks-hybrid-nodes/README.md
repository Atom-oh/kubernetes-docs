# EKS Hybrid Nodes 가이드

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

Amazon EKS Hybrid Nodes는 온프레미스 서버를 AWS EKS 컨트롤 플레인에서 관리할 수 있게 해주는 기능입니다. 이 문서에서는 EKS Hybrid Nodes의 개념, 설정 방법, 그리고 실제 운영 환경에서의 활용 방법을 상세히 다룹니다.

## 목차

1. [사전 요구 사항 및 시스템 요구 사항](./01-prerequisites.md)
2. [네트워크 구성](./02-network-configuration.md)
3. [에어갭 환경 구성 및 Harbor 레지스트리](./03-airgap-setup.md)
4. [노드 부트스트랩](./04-node-bootstrap.md)
5. [GPU 서버 통합](./05-gpu-integration.md)
6. [워크로드 배치 전략](./06-workload-placement.md)
7. [비용 최적화](./07-cost-optimization.md)
8. [운영 및 유지보수](./08-operations.md)

## EKS Hybrid Nodes 개요

### Hybrid Nodes란?

EKS Hybrid Nodes는 온프레미스 데이터센터나 엣지 환경에 있는 서버를 AWS EKS 컨트롤 플레인에서 관리되는 Kubernetes 노드로 등록할 수 있게 해주는 기능입니다. 이를 통해 클라우드와 온프레미스 인프라를 단일 Kubernetes 클러스터로 통합 관리할 수 있습니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    EKS Control Plane                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │ API Server  │  │    etcd     │  │ Controller  │               │   │
│  │  │             │  │             │  │  Manager    │               │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                    VPN / Direct Connect                                  │
│                              │                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────────┐
│         On-Premises          │        Data Center                        │
│  ┌───────────────────────────┴────────────────────────────────────────┐ │
│  │                     Hybrid Nodes                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │ │
│  │  │   Node 1    │  │   Node 2    │  │  GPU Node   │                 │ │
│  │  │  (Worker)   │  │  (Worker)   │  │   (H100)    │                 │ │
│  │  │  nodeadm    │  │  nodeadm    │  │  nodeadm    │                 │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 왜 Hybrid Nodes를 사용하는가?

#### 1. 규제 준수 및 데이터 주권

특정 산업(금융, 의료, 공공기관)에서는 데이터가 특정 지역이나 시설을 벗어나지 못하도록 규정하고 있습니다. Hybrid Nodes를 사용하면 민감한 데이터를 온프레미스에 유지하면서도 EKS의 관리 기능을 활용할 수 있습니다.

```yaml
# 규제 준수 워크로드 배치 예시
apiVersion: v1
kind: Pod
metadata:
  name: financial-data-processor
spec:
  nodeSelector:
    topology.kubernetes.io/zone: "on-premises"
    compliance.company.io/data-sovereignty: "required"
  containers:
  - name: processor
    image: harbor.internal.company.io/finance/data-processor:v1.2.0
```

#### 2. 데이터 중력 (Data Gravity)

대용량 데이터셋이 온프레미스에 존재하는 경우, 데이터를 클라우드로 이동하는 것보다 컴퓨팅을 데이터 가까이로 가져오는 것이 더 효율적입니다.

#### 3. 기존 하드웨어 활용

이미 투자한 고성능 서버(특히 GPU 서버)를 계속 활용하면서 Kubernetes 기반의 현대적인 워크로드 관리 방식을 적용할 수 있습니다.

#### 4. 통합 관리

클라우드와 온프레미스의 Kubernetes 워크로드를 단일 컨트롤 플레인에서 관리함으로써 운영 복잡성을 줄일 수 있습니다.

### 아키텍처 구성 요소

EKS Hybrid Nodes 아키텍처는 다음 구성 요소로 이루어집니다:

| 구성 요소 | 위치 | 역할 |
|-----------|------|------|
| EKS Control Plane | AWS | API 서버, etcd, 컨트롤러 매니저, 스케줄러 |
| nodeadm | On-Premises | 노드 부트스트랩 및 관리 에이전트 |
| kubelet | On-Premises | 파드 실행 및 노드 상태 보고 |
| containerd | On-Premises | 컨테이너 런타임 |
| VPN/Direct Connect | 네트워크 | AWS와 온프레미스 간 보안 연결 |
| SSM Agent 또는 IAM Roles Anywhere | On-Premises | 자격 증명 관리 |

### 주요 사용 사례

1. **AI/ML 워크로드**: 온프레미스 GPU 서버에서 모델 학습, 클라우드에서 추론 서비스
2. **금융 서비스**: 거래 데이터 처리는 온프레미스, 분석은 클라우드
3. **제조업**: 공장 내 엣지 컴퓨팅과 중앙 클라우드 통합
4. **미디어 처리**: 대용량 미디어 파일 처리는 데이터가 있는 곳에서 수행

## 다음 단계

EKS Hybrid Nodes에 대한 이해를 더욱 깊이 하고 실습을 진행하려면 다음 리소스를 참고하세요:

### 퀴즈

이 문서의 내용을 테스트하려면 다음 퀴즈를 풀어보세요:
- [EKS Hybrid Nodes 퀴즈](../quizzes/eks/12-eks-hybrid-nodes-quiz.md)

### 관련 문서

- [EKS 복원력 가이드](../eks/10-eks-resiliency.md) - 하이브리드 환경에서의 고가용성 구성
- [EKS 비용 최적화](../eks/07-eks-cost-optimization.md) - 비용 관리 전략
- [EKS 모니터링 및 로깅](../eks/06-eks-monitoring-logging.md) - 통합 모니터링 구성

### 공식 문서

- [AWS EKS Hybrid Nodes 공식 문서](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes.html)
- [nodeadm 사용자 가이드](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Harbor 공식 문서](https://goharbor.io/docs/)
- [NVIDIA GPU Operator 문서](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
