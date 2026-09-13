# EKS Hybrid Nodes

> **지원 버전**: 현재 EKS 지원 버전; 예제 검토 기준 EKS 1.36 / nodeadm 1.0.20
> **마지막 업데이트**: 2026년 9월 13일

Amazon EKS Hybrid Nodes는 고객이 운영하는 온프레미스·엣지 노드를 AWS 관리형 EKS control plane에 연결합니다. Host·OS·연결·workload 운영은 계속 사용자 책임입니다. 이 가이드는 지원 인터페이스와 예제 구성을 구분하며 특정 온프레미스 프로덕션 배포를 검증했다는 증거가 아닙니다.

## 목차

1. [사전 요구 사항 및 시스템 요구 사항](01-prerequisites.md)
2. [네트워크 구성](02-network-configuration.md)
3. [에어갭 환경 구성 (S3 + VPC 엔드포인트)](03-airgap-setup.md)
4. [노드 부트스트랩](04-node-bootstrap.md)
5. [GPU 서버 통합](05-gpu-integration.md)
6. [워크로드 배치 전략](06-workload-placement.md)
7. [노드 라이프사이클 관리](07-node-lifecycle.md)
8. [운영 및 유지보수](08-operations.md)
9. [베어메탈 서버 OS 설치 및 마이그레이션 가이드](09-bare-metal-os-setup.md)
10. [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)

## Hybrid Nodes 개요

Hybrid Nodes와 일반 AWS compute node는 같은 cluster에 있을 수 있습니다. 반면 cloud machine을 **hybrid** node로 등록하는 것은 별개입니다. AWS Region·Local Zone·Outposts·다른 cloud를 hybrid-node 인프라로 사용하는 것은 지원하지 않으며 EC2에서도 hybrid 요금이 발생합니다.

![온프레미스 라우터와 게이트웨이를 거쳐 AWS VPC의 컨트롤 플레인 ENI까지 이어지는 EKS 하이브리드 노드 네트워크 개요 다이어그램.](../.gitbook/assets/ko-eks-hybrid-nodes-highlevel-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-hybrid-nodes-highlevel-0.html)

아래 다이어그램은 VPC, 서브넷, Transit Gateway/Virtual Private Gateway, 원격 노드/파드 CIDR 연결을 포함한 네트워크 사전 요구 사항을 보여줍니다.

![EKS 클러스터의 RemoteNodeNetwork·RemotePodNetwork 설정과 VPC·온프레미스 양쪽 라우팅 테이블이 맞물리는 하이브리드 노드 사전 요구 사항 다이어그램.](../.gitbook/assets/ko-eks-hybrid-nodes-prereq-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-hybrid-nodes-prereq-0.html)

그림은 private 연결·라우팅 구조이며 모든 on-prem route/firewall/AWS service endpoint의 자동 생성을 뜻하지 않습니다.

## 사용 사례와 데이터 경계

온프레미스 GPU, 대규모 로컬 데이터, edge 처리와 기존 하드웨어는 Hybrid Nodes를 선택하는 이유가 될 수 있습니다. Data locality에는 애플리케이션·스토리지·egress·logging 제어도 필요합니다. Kubernetes API 객체와 control-plane metadata는 AWS에서 관리되므로 node selector만으로 데이터 주권·규정 준수가 입증되지는 않습니다.

`on-premises`라는 AWS zone이 있다고 가정하지 말고 실제 hybrid compute label과 명시적으로 관리하는 조직 label로 배치합니다.

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

이 조각은 label, 완전한 앱, 보안 경계나 데이터 보존 정책을 만들지 않습니다. Image/runtime 호환성과 실제 데이터 경로를 검증하세요.

## 아키텍처와 운영 책임

| 구성 요소 | 위치 | 책임 |
|-----------|------|------|
| EKS API server·etcd·controller·scheduler | AWS | AWS 관리형 control plane |
| nodeadm | 지원되는 온프레미스 Linux host | 설치/bootstrap/upgrade CLI; 상시 node agent가 아님 |
| kubelet/containerd | 온프레미스 | Node agent/CRI runtime; host owner가 운영 |
| Cilium 또는 Calico | 온프레미스·cluster | 호환 CNI 구성; VPC CNI는 hybrid node를 관리하지 않음 |
| SSM Agent 또는 Roles Anywhere signing helper | 온프레미스 | 해당 AWS 서비스에서 임시 자격 증명 획득 |
| SSM/IAM Roles Anywhere 서비스 | AWS | 자격 증명 서비스이며 로컬 offline CA 대체물이 아님 |
| VPN/Direct Connect·routing | 양쪽 환경 | 양방향 연결; Direct Connect만으로 암호화가 보장되지 않음 |

지원 Bottlerocket VMware 변형은 자체 bootstrap 경로를 사용하며 nodeadm을 사용하지 않습니다. 다른 지원 host에서는 `nodeadm install`이 의존성을 설치하고 `nodeadm init`이 구성·join합니다. SSM signing key 변경 때문에 SSM 신규 설치/upgrade에는 **nodeadm 1.0.19 이상**이 필요하며, 확인한 현재 릴리스는 **1.0.20**입니다.

## 계획에 반영할 제약

- **연결된 환경:** AWS와 안정적인 private 양방향 연결이 필요합니다. Disconnected/intermittent DDIL용이 아닙니다. 이 가이드의 “에어갭”은 필요한 AWS 연결을 유지하면서 인터넷 접근을 제한하는 환경이지 AWS로부터의 완전 격리가 아닙니다.
- **주소:** IPv4 RFC1918 또는 CGNAT이며 remote node/Pod·VPC·service CIDR이 겹치면 안 됩니다. Cluster당 **node CIDR 15개·Pod CIDR 15개**까지 지원합니다.
- **인증:** `API` 또는 `API_AND_CONFIG_MAP`과 Hybrid Nodes IAM role/access entry를 준비합니다.
- **API endpoint:** AWS는 public-only 또는 private-only를 권장합니다. 둘 다 켜면 VPC 밖 노드는 public endpoint 주소를 해석하므로 기대한 private 경로·접근 규칙에 따라 join이 **실패할 수 있습니다**. 보편적인 API 금지는 아닙니다. Public API endpoint를 써도 control-plane→node private 연결 요구는 없어지지 않습니다.
- **리전:** 현재 overview 기준 AWS GovCloud (US)·AWS China를 제외한 리전에서 지원합니다.
- **Host 지원:** OS·아키텍처·CNI·kernel을 함께 검토합니다. AL2023은 on-prem 가상화 환경용이며 일반적인 bare-metal 권장이 아닙니다.
- **요금:** Node가 연결된 동안 보고된 vCPU-hours로 과금합니다. Hyperthreading한 bare-metal core는 vCPU 2개로 보고될 수 있습니다. Workload가 idle이어도 node 요금이 자동 종료되지 않으며 cluster·다른 서비스 요금은 별도입니다.

## 자격 증명 프로바이더

두 방식 모두 갱신을 위해 AWS service endpoint 접근이 필요합니다. 로컬 CA가 IAM Roles Anywhere의 AWS 자격 증명 offline 발급을 가능하게 하지는 않습니다. 검토한 혼합 이유가 없다면 fleet에서 한 provider를 일관되게 사용하는 것을 권장합니다.

| 항목 | SSM hybrid activation | IAM Roles Anywhere |
|------|-----------------------|--------------------|
| Bootstrap | Activation ID/code와 준비한 SSM-trusting role | PKI·node별 cert/key·trust anchor·profile·role |
| 이름 | SSM 생성 `mi-...` 이름 | 인증서 identity에 연결된 custom node name |
| Session 수명 | 고정 1시간, SSM이 갱신 | 기본 1시간; request/profile은 15분–12시간 범위, effective duration·role maximum 적용 |
| 단절 | 갱신 불가; 복구 후 retry backoff로 재연결이 지연될 수 있음 | Offline에서 새 자격 증명 획득 불가; 연결 복구 후 credential-process가 필요 시 획득 |
| 규모/비용 | SSM node 등록·node 수 기준 관리 요금 없음; 기능별 사용 요금 조건은 별도 | IAM Roles Anywhere quota와 PKI 운영 요건 확인 |
| 일반적인 선택 | 기존 PKI가 없고 간단한 등록이 필요할 때 | 기존 PKI·인증서 수명 관리가 있을 때 |

**요금 확인일: 2026년 9월 13일.** SSM은 2026년 6월 30일부로 Advanced Instances Tier를 폐지했습니다. Session Manager·Run Command 사용 요금 조건은 [현재 SSM 요금표](https://aws.amazon.com/systems-manager/pricing/)를 확인하며, [EKS Hybrid Nodes vCPU 요금](https://aws.amazon.com/eks/pricing/)은 별도입니다.

Roles Anywhere profile은 custom role session name을 허용해야 하며 trust policy가 그 이름을 선택한 인증서 속성에 연결해야 합니다. Effective session duration은 IAM role maximum을 **초과하면 안 되며**, CreateSession API상 같은 값도 허용됩니다. [사전 요구 사항](01-prerequisites.md)에서 이 계약과 안전한 준비를 설명합니다.

## 워크로드 예시

1. 검증한 runtime·복구 계획을 사용하는 local GPU training/inference.
2. AWS metadata/telemetry/egress 경로를 별도로 검토한 local data processing.
3. 안정적인 연결·단절 동작 검증이 있는 factory/edge 앱.
4. 기존 대규모 데이터 가까이에서 수행하는 media processing.

## 다음 단계

EKS Hybrid Nodes에 대한 이해를 더욱 깊이 하고 실습을 진행하려면 다음 리소스를 참고하세요:

### 퀴즈

이 문서의 내용을 테스트하려면 다음 퀴즈를 풀어보세요:

* [EKS Hybrid Nodes 사전 요구사항 퀴즈](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [EKS Hybrid Nodes 네트워크 구성 퀴즈](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [EKS Hybrid Nodes 에어갭 환경 구성 퀴즈](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [EKS Hybrid Nodes 노드 부트스트래핑 퀴즈](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [EKS Hybrid Nodes GPU 통합 퀴즈](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [EKS Hybrid Nodes 워크로드 배치 퀴즈](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [노드 라이프사이클 관리 퀴즈](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [EKS Hybrid Nodes 운영 퀴즈](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [베어메탈 서버 OS 설치 퀴즈](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [EKS Hybrid Nodes Gateway 퀴즈](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)

### 관련 문서

* [EKS 복원력 가이드](../eks/10-eks-resiliency.md) - 하이브리드 환경에서의 고가용성 구성
* [EKS 비용 최적화](../eks/07-eks-cost-optimization.md) - 비용 관리 전략
* [EKS 모니터링 및 로깅](../eks/06-eks-monitoring-logging.md) - 통합 모니터링 구성

### 공식 문서

* [AWS EKS Hybrid Nodes 공식 문서](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [nodeadm 사용자 가이드](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Harbor 공식 문서](https://goharbor.io/docs/)
* [NVIDIA GPU Operator 문서](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [하이브리드 노드 네트워킹 가이드](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [하이브리드 노드 CNI 구성](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [하이브리드 노드 트러블슈팅](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [Hybrid operating-system compatibility](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Hybrid credentials and IAM role](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [Host credentials during network disconnection](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [IAM Roles Anywhere CreateSession semantics](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [EKS pricing](https://aws.amazon.com/eks/pricing/)
