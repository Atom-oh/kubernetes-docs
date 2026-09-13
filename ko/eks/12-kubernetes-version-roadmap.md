# Kubernetes 버전별 신규 기능과 로드맵

> **기능 이력 범위**: Kubernetes 1.29~1.36; 현재 EKS 지원 범위는 별도 표 참고
> **마지막 업데이트**: 2026년 9월 12일

Kubernetes는 연 3회 릴리스 주기를 통해 빠르게 진화하고 있으며, 각 버전마다 중요한 기능이 추가되거나 졸업(GA)합니다. 기업 환경에서 EKS 클러스터를 운영하는 팀에게 버전별 변경 사항을 체계적으로 파악하는 것은 안정적인 업그레이드 계획 수립과 새로운 기능의 적시 채택을 위해 필수적입니다.

이 문서에서는 Kubernetes 1.29부터 1.36까지의 주요 기능, 졸업 타임라인, Deprecation 정책, Amazon EKS의 버전 지원 체계, 그리고 향후 로드맵을 종합적으로 다룹니다.

## 목차

1. [개요 및 학습 목표](#1-개요-및-학습-목표)
2. [Kubernetes 릴리스 사이클](#2-kubernetes-릴리스-사이클)
3. [EKS 버전 지원 매트릭스](#3-eks-버전-지원-매트릭스)
4. [버전별 주요 기능 가이드](#4-버전별-주요-기능-가이드)
5. [주요 기능 졸업 타임라인](#5-주요-기능-졸업-타임라인)
6. [Deprecation 및 제거 사항](#6-deprecation-및-제거-사항)
7. [EKS 특화 고려사항](#7-eks-특화-고려사항)
8. [버전 업그레이드 계획](#8-버전-업그레이드-계획)
9. [향후 전망](#9-향후-전망)
10. [참고 자료](#10-참고-자료)

---

## 1. 개요 및 학습 목표

### 이 문서의 목적

Kubernetes 생태계는 빠르게 변화하고 있으며, 매 릴리스마다 수십 개의 Enhancement가 포함됩니다. 기업 운영 환경에서는 다음과 같은 질문에 대한 명확한 답이 필요합니다.

- 현재 사용 중인 버전에서 어떤 기능이 GA(Generally Available)인가?
- 다음 업그레이드 시 활용할 수 있는 새로운 기능은 무엇인가?
- 어떤 API나 기능이 Deprecated/Removed 되었는가?
- EKS에서 해당 버전과 기능을 언제부터 사용할 수 있는가?
- 장기적으로 어떤 방향으로 발전하고 있는가?

### 학습 목표

이 문서를 통해 다음을 이해할 수 있습니다.

| 목표 | 설명 |
|------|------|
| 릴리스 사이클 이해 | Kubernetes의 연 3회 릴리스 주기와 alpha/beta/GA 성숙도 모델 |
| 버전별 핵심 기능 파악 | 1.29~1.36 각 버전의 주요 Enhancement와 그 실무 영향 |
| 졸업 타임라인 추적 | 핵심 기능의 alpha → beta → GA 진행 경로 |
| EKS 지원 매트릭스 | Standard/Extended Support 체계와 비용 구조 |
| Deprecation 대응 | 제거 예정 기능에 대한 선제적 마이그레이션 계획 |
| 업그레이드 전략 수립 | Feature Gate 테스트, 호환성 검증, 롤백 계획 |

### 대상 독자

- EKS 클러스터를 운영하는 플랫폼 엔지니어링 팀
- Kubernetes 업그레이드 계획을 수립하는 인프라 아키텍트
- 새로운 기능 채택 시점을 결정하는 DevOps 리드
- 버전 지원 정책을 관리하는 운영팀

![Kubernetes 버전 관리를 중심으로 릴리스 사이클, 버전별 기능, EKS 지원, 업그레이드 전략의 네 가지 관리 축이 뻗어나가는 마인드맵 구조를 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-0.html)

---

## 2. Kubernetes 릴리스 사이클

### 릴리스 주기와 단계

Kubernetes는 보통 약 4개월 간격으로 연 3회 **마이너** 버전을 릴리스합니다. Patch release는 별도로 보통 월 단위로 진행됩니다. Upstream patch branch는 약 14개월 동안 지원되며, 일반 유지보수 약 12개월과 CVE·중대한 오류를 위한 maintenance 약 2개월로 나뉩니다. EKS 출시일부터 계산하는 EKS의 14개월 standard support와는 별개의 기간입니다.

Release team은 enhancement 포함, code freeze, 안정화, release candidate의 일정을 공지합니다. 기존 그림의 “Week 15”는 개략적인 주기이며 고정 일정이나 모든 릴리스에 공통인 주차표가 아닙니다. 대상 릴리스의 일정과 예외 승인 절차를 따릅니다.

![Kubernetes 연간 릴리스 사이클이 Enhancement Freeze, Code Freeze, 테스트 및 안정화 단계를 거쳐 약 4개월마다 세 차례 릴리스되는 반복 주기를 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-1.html)

### 기능 성숙도·API 안정성·Feature Gate

| 단계 | 해석 |
|---|---|
| Alpha | 보통 기본 비활성화이며 동작·API가 바뀌거나 제거될 수 있습니다. 실제 gate와 전제 조건을 확인합니다. |
| Beta | 검증 범위가 넓어지지만 기본값·호환성은 기능과 버전에 따릅니다. 비활성화 상태로 남는 beta gate도 있습니다. |
| Stable / GA | API 안정성 정책을 적용합니다. 특정 workload·driver·OS·배포의 안전성을 인증하는 것은 아닙니다. |

1.24부터 **새 beta API**는 기본 비활성화되지만, 기존에 활성화된 beta API와 그 새 버전은 다르게 취급합니다. API serving 설정과 feature gate는 관련되어 있지만 같은 개념은 아닙니다. 모든 beta 기능에 opt-in이 필요하거나 stable 기능은 workload 설정 없이 사용할 수 있다고 가정하지 않습니다.

GA API version은 같은 Kubernetes major version 안에서 제거할 수 없습니다. Feature gate 제거 규칙은 별개이며 beta→GA gate의 최소 유예 기간은 6개월 또는 2회 릴리스 중 더 긴 쪽입니다. 실제 제거 버전은 따로 확인해야 합니다. 잠기거나 제거된 gate를 지원되는 비활성화 수단으로 보지 않습니다. 예를 들어 출시된 1.36.2 소스에도 잠긴 `SidecarContainers` gate가 남아 있으므로 1.33 GA가 1.35 제거를 증명하지는 않습니다.

다음은 **과거 버전의 설정 조각**으로, 완전한 KubeletConfiguration이나 EKS 컨트롤 플레인 변경이 아닙니다. 현재 노드에는 해당 버전이 지원하는 설정을 사용하며 제거된 gate를 새 bootstrap 파일에 복사하지 않습니다.

```yaml
# Historical fragment for a self-managed Kubernetes 1.33 test node.
# Merge through the supported node bootstrap/configuration mechanism.
featureGates:
  InPlacePodVerticalScaling: true
  UserNamespacesSupport: true
```

EKS 컨트롤 플레인 설정은 AWS가 관리하므로 고객이 kube-apiserver static Pod를 편집하거나 임의 server flag를 넣을 수 없습니다. EKS version FAQ는 alpha 기능을 지원하지 않는다고 명시합니다. Self-managed node의 gate를 바꿔도 제공되지 않는 컨트롤 플레인 API가 활성화되지는 않습니다. AWS의 기능별 안내와 node runtime·OS 조건을 확인합니다.

Node `configz`는 선택한 kubelet의 설정을 보여 주며 생략된 기본값이나 컨트롤 플레인의 동작을 입증하지 않습니다. `/metrics`에는 적절한 non-resource URL 인가가 필요하고 feature metric이 제공되지 않거나 추가 label을 가질 수 있습니다. 출력 부재·접근 오류를 “비활성화”로 해석하지 않습니다.

```bash
# Authorized, read-only diagnostics; these endpoints may be restricted.
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?Choose the actual node}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get --raw="/api/v1/nodes/$NODE_NAME/proxy/configz" | jq '.kubeletconfig.featureGates'
```

```bash
# Run separately; absence of a metric is not proof that a feature is disabled.
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get --raw='/metrics' \
  | awk '/^kubernetes_feature_enabled/ { print }'
```

### SIG와 Enhancement Proposal

SIG는 관련 영역을 담당합니다. Node는 runtime·lifecycle, Auth는 인증·인가, Network는 Service routing, Storage는 CSI·volume을 맡으며 Scheduling·Apps·API Machinery·Instrumentation·Autoscaling 등의 SIG가 있습니다. 주요 enhancement의 KEP에는 동기·설계·졸업 기준·테스트·production-readiness 검토가 포함됩니다. 계획한 milestone은 출시 확약이 아니므로 실제 릴리스 API와 gate 이력을 확인합니다.

[Upstream patch policy](https://kubernetes.io/releases/patch-releases/) · [Feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/) · [Deprecation policy](https://kubernetes.io/docs/reference/deprecation-policy/) · [Kubernetes 1.36.2 gate implementation](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go)

---

## 3. EKS 버전 지원 매트릭스

### 지원 기간과 비용 기준

| 구분 | EKS 출시일부터의 기간 | 버전 지원 요금 |
|---|---|---|
| Standard | 첫 14개월 | 클러스터 시간당 $0.10 |
| Extended | 이후 12개월 | 클러스터 시간당 총 $0.60 ($0.10 + $0.50) |

이는 공시된 버전 지원 요금이며 전체 클러스터 운영 비용이 아닙니다. Provisioned Control Plane tier·compute·Auto Mode/Hybrid Nodes·다른 capability·storage·network 비용이 추가될 수 있습니다. 동일 요율로 365일 운영하면 클러스터당 $876과 $5,256이며 차액은 $4,380입니다. 월 730시간 예시에서는 $73과 $438입니다. 실제 청구 측정값이 아닌 산술 예시입니다.

### 확인한 지원 일정 — 2026년 9월 12일 기준 (UTC)

| 버전 | Upstream 출시 | EKS 출시 | Standard 종료 | Extended 종료 | 검토일 상태 |
|---|---|---|---|---|---|
| 1.31 | 2024-08-13 | 2024-09-26 | 2025-11-26 | 2026-11-26 | Extended |
| 1.32 | 2024-12-11 | 2025-01-23 | 2026-03-23 | 2027-03-23 | Extended |
| 1.33 | 2025-04-23 | 2025-05-29 | 2026-07-29 | 2027-07-29 | Extended |
| 1.34 | 2025-08-27 | 2025-10-02 | 2026-12-02 | 2027-12-02 | Standard |
| 1.35 | 2025-12-17 | 2026-01-27 | 2027-03-27 | 2028-03-27 | Standard |
| 1.36 | 2026-04-22 | 2026-06-02 | 2027-08-02 | 2028-08-02 | Standard |

현재 AWS 일정은 1.31~1.36을 제공합니다. 본문의 1.29·1.30은 과거 기능 이력이며 지원되는 배포 대상이 아닙니다. Upstream 1.37 출시만으로 EKS 지원을 추론하지 않습니다. Extended 요금은 표의 standard 종료일 UTC 0시부터 적용됩니다. 변경 전에 실제 일정·API를 다시 확인하며 AWS가 월 단위로만 공지한 향후 날짜는 추정입니다.

일정상 EKS 1.35 출시는 **2026년 1월 27일**, 1.36은 **2026년 6월 2일**입니다. EKS Distro 발표일은 별개의 출시 이벤트이므로 기존의 1월 28일 통합 표기로 EKS 일정을 대신하지 않습니다. 기능별 runtime·admission 조건은 아래 해당 버전 섹션을 참고합니다. EKS 버전 롤백과 컨트롤 플레인 scaling·SLA는 [EKS 업그레이드](08-eks-upgrades.md)에서 다룹니다.

```bash
# Read-only when executed with your normal authorized AWS identity.
: "${AWS_REGION:?Choose the intended Region}"
aws eks describe-cluster-versions --region "$AWS_REGION" --no-cli-pager \
  --query clusterVersions --output json
```

첫 배열 원소를 최신 버전으로 가정하거나 과거 예시의 status를 재사용하지 않고 서비스가 반환하는 버전 기록을 조회합니다. 감사에서는 AWS query를 실행하지 않았습니다.

### Upgrade policy와 자동 업그레이드

기본 cluster upgrade policy는 `EXTENDED`입니다. `STANDARD`를 선택하면 standard support 종료 후 자동 업그레이드될 수 있으므로 extended까지 유지할지는 비용·수명주기 관점에서 결정합니다. Extended 종료 후 EKS는 남은 컨트롤 플레인을 지원 버전으로 점진적으로 업그레이드합니다. AWS는 정확한 실행 시점을 약속하지 않으며 해당 자동 업데이트 직전 알림도 제공하지 않는다고 명시합니다. 최소 60일 전 고지는 **standard support 종료일**에 대한 고지이지 extended 종료 후 새 60일 유예나 60/30/7일 순차 알림 보장이 아닙니다.

Managed node group·self-managed node·Fargate Pod·Hybrid Node는 각각의 업데이트·교체 절차가 필요합니다. Auto Mode node는 자동 갱신될 수 있으며 일반적으로 설치한 add-on은 호환성과 소유권을 별도로 검토합니다. 지원 가능한 최대 skew를 목표로 삼지 말고 가능한 한 node와 컨트롤 플레인 버전을 맞춥니다. 컨트롤 플레인 버전 문자열뿐 아니라 실제 update 상태와 workload readiness를 확인합니다. Extended 종료로 자동 업그레이드된 클러스터에는 EKS의 7일 native rollback을 사용할 수 없습니다. 자격 조건과 node-first rollback 순서는 업그레이드 문서를 따릅니다.

[EKS support calendar and FAQ](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) · [EKS pricing](https://aws.amazon.com/eks/pricing/)

<!-- Parent diagram repair pending: stage/default guarantees and support status/notification timing are stale.
![KEP(Kubernetes Enhancement Proposal)가 아이디어에서 초안 작성, SIG 리뷰, 승인 심사를 거쳐 Alpha에서 Beta, GA로 졸업하고 최종적으로 Feature Gate가 제거되기까지의 절차를 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-2.html)

![EKS 버전 지원 체계가 Standard Support(14개월, $0.10/cluster/hour)에서 Extended Support(+12개월, $0.60/cluster/hour)를 거쳐 지원 종료(End of Life)로 이어지는 3단계 흐름과, Extended 진입 전 업그레이드 계획 수립, 종료 60일 전 AWS 사전 알림, 종료일 컨트롤 플레인 자동 업그레이드(노드 그룹은 수동)를 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-3.html)

![Kubernetes 1.29부터 1.36까지 EKS 각 버전의 Standard Support와 Extended Support 종료 시점, 그리고 2026년 9월 기준 지원 상태를 버전 순서대로 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-4.html)

![Extended Support 종료 시점이 다가오면 AWS EKS가 관리자에게 단계적으로 알림을 보내고, 종료일에 컨트롤 플레인만 자동 업그레이드되며 노드 그룹은 관리자가 수동으로 업그레이드해야 함을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-5.html)

-->

---

## 4. 버전별 주요 기능 가이드

이 섹션은 Kubernetes 1.29부터 1.36까지 각 버전의 핵심 Enhancement를 상세히 다룹니다. 각 기능에 대해 실무적 관점에서의 영향과 활용법을 함께 설명합니다.

### 4.1 Kubernetes 1.29 "Mandala" (2023년 12월)

2023년 12월 13일 릴리스 발표의 수치는 **49개 enhancement: stable 11개, beta 19개, alpha 19개**입니다. 과거 릴리스 통계이며 EKS 1.29가 현재 지원된다는 뜻이 아닙니다. 그림의 기본값·production 표기는 일반화된 설명이므로 위의 기능별 gate 이력과 runtime 조건을 함께 확인합니다.

![Kubernetes 1.29 "Mandala" 릴리스의 전체 49개 Enhancement가 Stable(GA) 11개, Beta 19개, Alpha 19개로 나뉘어 성숙도 단계별로 분포하고 각 단계의 대표 기능이 무엇인지 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-6.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-6.html)

#### KMS v2 저장 시 암호화 — GA

KMS v2는 secret seed에서 일회용 data encryption key를 파생하고 seed 보호·교체 시 KMS plugin을 사용하여 매 object 쓰기마다 원격 암호화를 요구하지 않도록 envelope encryption 성능을 개선합니다. Envelope encryption의 data-encryption·key-encryption 계층은 v1에도 있으므로 v1을 “단일 계층”으로 설명하면 안 됩니다. 개선이 일정한 latency를 보장하지는 않습니다.

KMS v1은 1.28에서 deprecated, 1.29에서 기본 비활성화되었습니다. 현재 upstream KMS 문서에도 legacy 구현이 설명되어 있으므로 기존의 “1.31에서 제거”는 잘못된 설명입니다. 지원되는 v2 마이그레이션 경로를 우선합니다.

아래는 관리자가 운영하는 upstream API server에 검토한 v2 plugin을 지정한 socket으로 설치한 경우의 설정이며 **EKS 컨트롤 플레인 매니페스트가 아닙니다**. V2는 `cachesize`를 받지 않습니다. 마지막 `identity` provider는 마이그레이션 중 기존 평문을 읽기 위한 것으로, 첫 provider의 쓰기 암호화 실패 시 평문 fallback이 아닙니다. 암호화 마이그레이션을 검토하고 완료를 검증한 뒤 평문 읽기 허용을 제거합니다.

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources:
  - secrets
  providers:
  - kms:
      apiVersion: v2
      name: reviewed-kms-provider
      endpoint: unix:///var/run/kmsplugin/socket.sock
      timeout: 3s
  - identity: {}
```

**EKS 구분:** 현재 AWS 안내는 EKS 1.28 이상에서 모든 Kubernetes API data에 KMS v2 envelope encryption을 기본 제공하며 customer-managed key를 설정하지 않으면 AWS-owned key를 사용합니다. Secrets·ConfigMaps 같은 API data에 적용되고 node나 EBS volume의 임의 data까지 암호화하는 것은 아닙니다. EKS 1.29부터 시작한다고 추론하거나 위 upstream 설정을 EKS에 적용하지 않습니다.

#### ReadWriteOncePod — GA

`ReadWriteOncePod`는 클러스터 전체에서 PVC를 한 Pod로 제한합니다. `ReadWriteOnce`는 한 node의 여러 Pod가 접근할 수 있습니다. RWOP에는 호환되는 CSI volume·driver가 필요하며 upstream 최소 sidecar는 csi-provisioner 3.0.0, csi-attacher 3.3.0, csi-resizer 1.3.0입니다. 이는 기능 최소 조건이지 현재 권장 release가 아닙니다. 실제 클러스터와 provisioner가 지원하는 버전을 선택합니다.

예시는 기존 `version-lab` namespace와 적합한 `reviewed-csi-class`를 필요로 합니다. Access mode 조정은 privileged host 접근을 막는 kernel 보안 경계나 DB leader election이 아니며 앱 fencing·backup을 대신하지 않습니다.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-pvc
  namespace: version-lab
spec:
  accessModes:
  - ReadWriteOncePod
  storageClassName: reviewed-csi-class
  resources:
    requests:
      storage: 100Gi
```

#### 주요 beta·alpha 기능

| 기능 | 1.29 상태 | 의미 |
|---|---|---|
| SidecarContainers | Beta, 기본 활성화 | 재시작 가능한 init container. Alpha는 1.28, GA는 1.33 |
| NFTablesProxyMode | Alpha, 기본 비활성화 | Linux Service proxy backend. Kernel·CNI·NodePort 동작 확인 필요 |
| LoadBalancerIPMode | Alpha | Controller가 보고하는 LoadBalancer ingress status mode이며 임의 Pod 필드가 아님 |
| PodSchedulingReadiness | Beta | Scheduling gate로 scheduler의 검토를 보류 |
| NodeLogQuery | Alpha | 해당 kubelet 설정·접근 권한 필요 |
| KubeletTracing | Beta | 1.29 GA가 아니며 GA는 1.34 |
| MinDomainsInPodTopologySpread | Beta | 1.30에서 GA |

Native sidecar는 아래 **Pod spec 조각**처럼 정의합니다. 예시 image를 검토한 구현으로 바꾸고 실제 log pipeline을 설정해야 합니다. 설치된 Fluent Bit 배포가 아닙니다. Sidecar 시작과, 있을 경우 startup probe 성공 후 다음 시작 단계로 진행합니다. Readiness·정상 종료에는 적절한 probe·앱 동작·충분한 termination budget이 필요합니다.

```yaml
initContainers:
- name: log-helper
  image: example.invalid/version-lab/log-helper:reviewed
  restartPolicy: Always
```

이 릴리스에서 CSI `NodeExpandSecret`도 GA가 되어 driver의 node-side 확장 요청에 적절한 credential을 전달할 수 있습니다. Deprecated `flowcontrol.apiserver.k8s.io/v1beta2` endpoint는 1.29에서 serving이 중단되었으므로 stable `v1` API와 필드 변경을 검토합니다. `SecurityContextDeny`는 그 전에 deprecated되었고 1.30에서 제거되었으며 1.29에서 새로 deprecated된 것이 아닙니다. 여기서 모든 환경에 공통인 “Service 5,000개” 성능 경계나 proxy benchmark를 측정하지 않았습니다.

[Kubernetes 1.29 release](https://kubernetes.io/blog/2023/12/13/kubernetes-v1-29-release/) · [KMS provider](https://kubernetes.io/docs/tasks/administer-cluster/kms-provider/) · [EKS envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html) · [Persistent volumes and RWOP](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) · [API migration guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)

---

### 4.2 Kubernetes 1.30 "Uwubernetes" (2024년 4월)

4월 17일 릴리스의 수치는 **45개 enhancement: stable 17개, beta 18개, alpha 10개**입니다. 성숙도 표기가 기능별 설정과 runtime 검증을 대신하지는 않습니다.

<!-- Parent repair: this diagram incorrectly says58total/23alpha; official counts45total/10alpha.
![Kubernetes 1.30 Uwubernetes 릴리스의 Enhancement가 Stable(GA), Beta, Alpha 성숙도 단계로 나뉘고, ValidatingAdmissionPolicy와 Pod Scheduling Readiness 등 핵심 GA 기능이 Stable 아래에 묶인 구조를 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-7.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-7.html)
-->

#### ValidatingAdmissionPolicy — GA

ValidatingAdmissionPolicy는 API server 안에서 CEL을 평가합니다. 여러 validation webhook과 network·인증서·server 의존성을 줄일 수 있지만 잘못된 정책·평가 오류·fail-closed 설정은 여전히 요청을 거부할 수 있습니다. Policy·binding·선택적 parameter object는 역할이 다르며 parameter는 built-in resource나 custom resource가 될 수 있습니다. 필수인 세 번째 CRD 타입이 아닙니다.

아래는 현재 stable `v1` API 예시입니다. Binding은 **Audit-only**이고 `version-lab-policy=enabled` label이 있는 namespace만 선택합니다. 위반 시 audit annotation을 추가하고 거부하지는 않으며, 관찰하려면 audit-log 수집을 구성해야 합니다. 해당 namespace label 설정 권한을 통제합니다. 정상·오류 입력을 먼저 검증하고 강제 적용이 목적이면 의도적으로 `Deny`를 선택합니다. 예시가 production admission 동작의 검증 결과는 아닙니다.

Resource policy는 일반·init container에 CPU/memory limit key가 선언되었는지 확인합니다. 적절한 양수 크기까지 검증하지 않으며 값 0의 존재가 유용한 hard limit는 아닙니다. 용량 조건에는 적합한 LimitRange·resource policy를 사용합니다. Ephemeral container에는 이 limit를 지정할 수 없어 제외합니다. `pods/resize`는 현재 클러스터를 위한 항목으로, 원래 1.30의 VAP GA 이후에 도입된 subresource입니다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: version-lab-resource-limits
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/resize
  validations:
  - expression: "object.spec.containers.all(c,\n  has(c.resources) && has(c.resources.limits)\
      \ &&\n  has(c.resources.limits.cpu) && has(c.resources.limits.memory)\n) &&\n\
      (!has(object.spec.initContainers) || object.spec.initContainers.all(c,\n  has(c.resources)\
      \ && has(c.resources.limits) &&\n  has(c.resources.limits.cpu) && has(c.resources.limits.memory)\n\
      ))"
    message: Regular and init containers must declare CPU and memory limits.
    reason: Invalid
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: version-lab-resource-limits
spec:
  policyName: version-lab-resource-limits
  validationActions:
  - Audit
  matchResources:
    namespaceSelector:
      matchLabels:
        version-lab-policy: enabled
```

Image policy는 `/` 경계까지 포함한 전체 registry/repository prefix를 사용합니다. 기존 `123456789012.dkr.ecr.` prefix는 유사 도메인도 허용했습니다. 예시 계정·Region·public alias를 승인한 소스로 바꿉니다. Image 참조 검사이지 서명·취약점·digest 불변성 검사는 아닙니다. 선택적인 init/ephemeral 목록에는 존재 확인을 넣고 ephemeral-container subresource도 명시적으로 매칭합니다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: version-lab-image-registries
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  validations:
  - expression: object.spec.containers.all(c, c.image.startsWith('123456789012.dkr.ecr.us-west-2.amazonaws.com/')
      || c.image.startsWith('public.ecr.aws/approved-alias/'))
    message: Regular container images must use an approved registry/repository prefix.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c,
      c.image.startsWith(''123456789012.dkr.ecr.us-west-2.amazonaws.com/'') || c.image.startsWith(''public.ecr.aws/approved-alias/''))'
    message: Init container images must use an approved registry/repository prefix.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c,
      c.image.startsWith(''123456789012.dkr.ecr.us-west-2.amazonaws.com/'') || c.image.startsWith(''public.ecr.aws/approved-alias/''))'
    message: Ephemeral container images must use an approved registry/repository prefix.
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: version-lab-image-registries
spec:
  policyName: version-lab-image-registries
  validationActions:
  - Audit
  matchResources:
    namespaceSelector:
      matchLabels:
        version-lab-policy: enabled
```

추가 **validation 목록 조각**은 일반 container의 유효 `runAsNonRoot` 상속과 비어 있지 않은 앱 label을 검사합니다. Container 설정이 Pod 설정을 재정의합니다. 별도 policy·binding이 필요하며 모든 Pod Security Standard·init/ephemeral container·image user를 검증하지는 않습니다. `/`가 들어간 map key는 membership으로 확인하며 `has(map["key"])`는 올바른 CEL macro 구문이 아닙니다.

```yaml
- expression: "object.spec.containers.all(c,\n  has(c.securityContext) && has(c.securityContext.runAsNonRoot)\n\
    \    ? c.securityContext.runAsNonRoot\n    : (has(object.spec.securityContext)\
    \ &&\n       has(object.spec.securityContext.runAsNonRoot) &&\n       object.spec.securityContext.runAsNonRoot)\n\
    )"
  message: Regular containers must effectively set runAsNonRoot.
- expression: 'has(object.metadata.labels) &&

    ''app.kubernetes.io/name'' in object.metadata.labels &&

    ''app.kubernetes.io/version'' in object.metadata.labels &&

    object.metadata.labels[''app.kubernetes.io/name''] != '''' &&

    object.metadata.labels[''app.kubernetes.io/version''] != '''' '
  message: Nonempty application name and version labels are required.
```

#### Pod Scheduling Readiness — GA

Scheduling gate는 Pod를 scheduling 검토에서 제외합니다. 생성·admission 시 설정하고 이후 제거할 수 있지만 생성 뒤 새 gate를 추가할 수는 없습니다. Gated Pod만으로 일반적인 unschedulable-Pod 기반 node provisioning이 시작되지는 않으므로 외부 승인·provisioning 절차에서 조건을 충족해야 합니다. Gate만으로 atomic gang scheduling이 구현되지 않습니다.

아래에는 소유 namespace, 예시 image를 대체할 검토된 image, 적절한 GPU 용량·driver가 필요합니다. Gate 이름은 외부 quota 승인·보안 scan을 나타낼 뿐 이름을 붙였다고 Kubernetes가 해당 작업을 실행하지는 않습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gated-training
  namespace: version-lab
spec:
  schedulingGates:
  - name: example.com/gpu-quota-approved
  - name: example.com/security-scan-passed
  containers:
  - name: trainer
    image: example.invalid/version-lab/training:reviewed
    resources:
      limits:
        nvidia.com/gpu: 4
```

이름으로 지정한 조건을 별도로 검증한 뒤 아래 변경으로 해당 gate만 제거합니다. JSON Patch test가 UID·resourceVersion·선택한 gate 이름을 확인하므로 동시 변경이나 Pod 교체 시 실패합니다. 실패하면 다시 읽고 판단하며 추측한 index를 제거하지 않습니다. 모든 gate가 제거된 뒤에야 scheduling 대상이 되고 일반 placement·용량 제약은 계속 적용됩니다.

```bash
# MUTATION: remove only the named gate after independently verifying its condition.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${GATE_NAME:?}"
gate_patch=$(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq -ce --arg gate "$GATE_NAME" '
    .metadata as $m |
    [(.spec.schedulingGates // []) | to_entries[] | select(.value.name == $gate)] as $matches |
    if ($matches | length) != 1 then error("Expected exactly one matching gate")
    else ($matches[0].key | tostring) as $i | [
      {op:"test", path:"/metadata/uid", value:$m.uid},
      {op:"test", path:"/metadata/resourceVersion", value:$m.resourceVersion},
      {op:"test", path:("/spec/schedulingGates/" + $i + "/name"), value:$gate},
      {op:"remove", path:("/spec/schedulingGates/" + $i)}
    ] end')
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  patch pod "$POD_NAME" --type=json --patch "$gate_patch"
```

#### HPA ContainerResource metric — GA (KEP-2702)

ContainerResource는 지정한 container를 대상으로 하므로 log/proxy sidecar 사용량이 앱 utilization 신호를 왜곡하는 것을 줄일 수 있습니다. `version-lab`에 대상 Deployment가 존재하고 적절한 request를 설정한 `app` container가 있어야 합니다. 정상 resource-metrics provider도 필요합니다. Utilization의 분모는 limit가 아닌 request입니다. Metric이 여러 개면 HPA는 가장 큰 replica 권고를 선택하며 metric 누락·readiness·stabilization이 동작에 영향을 줍니다. Replica 2~50은 측정된 최적값이 아닌 용량 예시입니다.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: version-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: ContainerResource
    containerResource:
      name: cpu
      container: app
      target:
        type: Utilization
        averageUtilization: 70
  - type: ContainerResource
    containerResource:
      name: memory
      container: app
      target:
        type: Utilization
        averageUtilization: 80
```

#### 기타 주요 변경

| 기능 | 1.30 상태 |
|---|---|
| MinDomainsInPodTopologySpread | GA |
| StableLoadBalancerNodeSet | GA |
| PodDisruptionConditions | Beta; GA는 1.31 |
| NodeLogQuery | Beta, 기본 비활성화; GA는 1.36 |
| UserNamespacesSupport | Beta, 기본 비활성화 |
| ContextualLogging | Beta; 코드가 contextual logger를 사용해야 하며 모든 메시지에 Pod/node 필드가 자동 추가되지는 않음 |
| RecursiveReadOnlyMounts | Alpha; 적합한 kernel/runtime 지원 필요 |
| RelaxedEnvironmentVariableValidation | Alpha; 값이 아닌 환경변수 **이름**의 허용 범위 변경 |
| ServiceAccountTokenJTI | Beta; 추적용 식별자 제공 |

`SecurityContextDeny`는 1.30에서 제거되었습니다. Pod Security Admission과 환경에 필요한 정책을 검토하며 기능 성숙도를 마이그레이션 검증으로 대신하지 않습니다.

[Kubernetes 1.30 release](https://kubernetes.io/blog/2024/04/17/kubernetes-v1-30-release/) · [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/) · [Scheduling readiness](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-scheduling-readiness/) · [HPA container metrics](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#container-resource-metrics)

---

### 4.3 Kubernetes 1.31 "Elli" (2024년 8월)

8월 13일 릴리스의 수치는 **45개 enhancement: stable 11개, beta 22개, alpha 12개**입니다.

<!-- Parent repair: DRA structured parameters remained alpha in1.31, not beta as drawn.
![Kubernetes 1.31 릴리스의 전체 45개 Enhancement가 Stable(GA) 11개, Beta 22개, Alpha 12개로 나뉘고 각 성숙도 단계 아래에 페이지에서 다루는 대표 기능이 배치된 것을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-8.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-8.html)
-->

#### AppArmor native 필드 — GA

AppArmor native 필드는 1.30에 도입되고 1.31에서 GA가 되었으며 기존 container별 beta annotation 방식을 대체합니다. Host에서 AppArmor가 실제 활성화되어 있고 runtime이 지원해야 하며 `Localhost` profile은 배치 가능한 각 node에 로드되어 있어야 합니다. Custom node label은 운영자가 검증한 조건의 표시일 뿐 profile 설치·강제 적용 수단이 아닙니다.

첫 예시는 사전 설치한 profile을 사용하고 두 번째는 기존 Deployment 예시에 빠진 selector·Pod label을 갖춥니다. 예시 image를 교체하고 namespace를 준비합니다. `RuntimeDefault`는 runtime의 profile이고 `Unconfined`는 AppArmor 제약을 해제합니다. 모든 EKS OS·compute 유형이 지정한 profile을 지원하는 것은 아닙니다. AppArmor·seccomp·SELinux는 서로 다른 제어 방식이며 같은 보호의 다른 이름이 아닙니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: apparmor-local-profile
  namespace: version-lab
spec:
  nodeSelector:
    version-lab.example.com/apparmor-profile: reviewed
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    securityContext:
      appArmorProfile:
        type: Localhost
        localhostProfile: reviewed-app-profile
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apparmor-runtime-default
  namespace: version-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apparmor-runtime-default
  template:
    metadata:
      labels:
        app: apparmor-runtime-default
    spec:
      containers:
      - name: app
        image: example.invalid/version-lab/app:reviewed
        securityContext:
          appArmorProfile:
            type: RuntimeDefault
```

#### PersistentVolume 마지막 phase 전환 시각 — GA

PV status의 `.status.lastPhaseTransitionTime`은 최근 phase 전환을 기록합니다. Event·backend 근거와 함께 수명주기를 진단하며 완전한 전환 이력이나 누락된 과거 이벤트의 복원으로 보지 않습니다. 아래 명령은 volume을 변경·삭제하지 않습니다.

```bash
# Read-only, for one owned cluster-scoped PV.
: "${KUBE_CONTEXT:?}"; : "${PV_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pv "$PV_NAME" -o json | jq '{
  name:.metadata.name,phase:.status.phase,lastPhaseTransitionTime:.status.lastPhaseTransitionTime
}'
```

#### DRA structured parameters — 1.31에서는 아직 alpha

DRA 재설계는 structured API·ResourceSlice로 device 정보와 요청을 Kubernetes가 볼 수 있게 하여 scheduler 측 할당을 가능하게 했습니다. **1.31에도 classic DRA가 남아 있었으며**, 별도의 기본 비활성 `DRAControlPlaneController` gate로 제어했습니다. 출시된 1.31 소스에는 이 gate가 있고 1.32 소스에서는 제거됩니다. 따라서 기존 퀴즈의 “1.31에서 classic DRA 제거”는 잘못된 설명입니다.

DRA는 1.31에서 alpha, 1.32에서 beta, core API는 1.34에서 stable이 되었습니다. 기존 `resource.k8s.io/v1beta1` 예시는 1.31 당시 API 세대를 올바르게 표현하지 못했습니다. 현재 구문은 1.34 절의 stable DRA 예시를 사용하고 설치한 driver의 DeviceClass·ResourceSlice·attribute·기능을 확인합니다. Kubernetes API 자체가 GPU driver를 설치하거나 time-slicing/MIG를 구현하지는 않습니다.

#### Service traffic distribution — beta

Core `v1` Service의 `trafficDistribution: PreferClose`는 같은 zone endpoint를 선호하도록 요청합니다. 엄격한 locality 규칙·지리적 거리 계산·cross-AZ 요금 제거 보장이 아닌 routing 선호입니다. Endpoint 가용성·구현 proxy·traffic policy 우선순위가 영향을 줍니다. Selector가 실제 workload Pod와 일치해야 하며 예시가 endpoint를 생성하지는 않습니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: zone-preference
  namespace: version-lab
spec:
  trafficDistribution: PreferClose
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

#### 기타 주요 변경

| 기능 | 1.31 상태 |
|---|---|
| NFTablesProxyMode | Beta, 기본 활성화. Proxy mode 선택과 Linux·kernel·CNI 호환성 확인은 별도 단계 |
| MultiCIDRServiceAllocator | Beta, 기본 비활성화 |
| VolumeAttributesClass | Beta, 기본 비활성화. Driver·controller·API 지원 필요 |
| ImageVolume | Alpha, 기본 비활성화 |
| PodDisruptionConditions | GA |
| JobPodReplacementPolicy | Beta; GA는 1.34 |
| SidecarContainers | 1.29부터 이미 beta이며 1.31에서 새로 beta가 된 것이 아님 |

Nftables backend 지원은 자동 network 마이그레이션이 아닙니다. NodePort·firewall 동작이 iptables와 다를 수 있으므로 production proxy mode 변경 전에 실제 구현을 평가합니다.

[Kubernetes 1.31 release](https://kubernetes.io/blog/2024/08/13/kubernetes-v1-31-release/) · [AppArmor prerequisites](https://kubernetes.io/docs/tutorials/security/apparmor/) · [1.31 feature source](https://github.com/kubernetes/kubernetes/blob/v1.31.0/pkg/features/kube_features.go) · [1.32 feature source](https://github.com/kubernetes/kubernetes/blob/v1.32.0/pkg/features/kube_features.go)

---

### 4.4 Kubernetes 1.32 "Penelope" (2024년 12월)

12월 11일 릴리스의 수치는 **44개 enhancement: stable 13개, beta 12개, alpha 19개**입니다. 그림의 기본 활성화 표기는 단순화한 성숙도 범례이며 아래 beta 기능 중에는 비활성화 상태로 남는 기능도 있습니다.

![Kubernetes 1.32 릴리스의 전체 44개 Enhancement가 Stable(GA) 13개, Beta 12개, Alpha 19개로 나뉘어 성숙도 단계별로 분포한 것을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-9.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-9.html)

#### Structured authorization configuration — GA

Stable 설정은 `apiserver.config.k8s.io/v1`의 `AuthorizationConfiguration`을 사용합니다. 기존 authorization mode flag의 대안이지 `--authorization-mode`가 제거되었다는 뜻이 아닙니다. Flag 방식과 설정 파일 방식을 혼용하지 않습니다. EKS는 이 컨트롤 플레인 설정을 관리하므로 아래 파일은 관리자가 운영하는 API server용이며 kubectl로 적용하는 resource나 EKS 설정 인터페이스가 아닙니다.

Authorizer는 순서대로 평가하고 명시적인 allow/deny가 나오면 chain이 끝납니다. 아래 webhook은 Node·RBAC가 이미 결정하지 않은 `version-lab` resource 요청만 처리하므로 **RBAC가 이미 허용한 요청에 추가 deny filter를 적용하지 않습니다**. CEL match condition은 webhook 호출을 선택하며 CEL 자체가 별도 authorizer 타입은 아닙니다. Request는 SubjectAccessReview spec이므로 namespace는 `request.resourceAttributes` 아래에 있고 non-resource 요청에는 존재 확인이 필요합니다.

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: AuthorizationConfiguration
authorizers:
- type: Node
  name: node
- type: RBAC
  name: rbac
- type: Webhook
  name: reviewed-webhook
  webhook:
    authorizedTTL: 5m
    unauthorizedTTL: 30s
    timeout: 3s
    subjectAccessReviewVersion: v1
    matchConditionSubjectAccessReviewVersion: v1
    failurePolicy: Deny
    connectionInfo:
      type: KubeConfigFile
      kubeConfigFile: /etc/kubernetes/reviewed-authz-webhook.kubeconfig
    matchConditions:
    - expression: has(request.resourceAttributes) && request.resourceAttributes.namespace
        == 'version-lab'
```

사용 전에 실제 webhook·TLS trust·보호된 kubeconfig를 준비합니다. `failurePolicy: Deny`는 해당 webhook·조건 평가 실패에 적용되며 캐시된 결정은 backend policy 변경 효과를 지연시킬 수 있습니다. 모든 API server에 일관된 설정을 사용합니다. 설정 reload를 지원하지만 Node/RBAC authorizer를 추가·제거할 수는 없으므로 비프로덕션에서 전체 정책과 복구 절차를 검증합니다.

#### StatefulSet PVC retention policy — GA

1.32에서 GA가 된 관련 기능은 **StatefulSet volume claim template으로 생성한 PVC의 자동 삭제·보존 정책**입니다. 모든 미사용 PVC의 보호 finalizer가 즉시 제거된다는 새 보장이 아닙니다. `whenDeleted`는 StatefulSet 삭제, `whenScaled`는 scale-down 동작을 제어하며 각각 `Retain` 또는 `Delete`를 지원합니다. 기본값은 data 보존입니다. 아래는 기존 StatefulSet에서 검토할 설정 조각입니다.

```yaml
spec:
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
```

`Delete` 선택은 data 수명주기 변경이며 PV reclaim policy에 따라 PVC 삭제가 backend storage 삭제로 이어질 수 있습니다. Pod ownership·garbage collection·CSI 작업·finalizer가 완료 시점에 영향을 줍니다. PVC 사용 중 보호는 1.32 전부터 있었으므로 멈춘 claim은 consumer·UID·attachment·controller를 조사해야 합니다. Finalizer 일괄 제거 또는 업그레이드만으로 해결된다고 가정하지 않습니다.

#### VolumeAttributesClass — 1.32에서는 아직 beta

VAC는 1.31에서 beta, 1.34에서 GA가 되었습니다. Beta API는 `storage.k8s.io/v1beta1`이며 현재 예시는 cluster·CSI driver가 지원할 때 1.34 절의 stable API를 사용합니다. Class parameter는 불변이고 PVC의 class 참조를 바꿔 EBS IOPS·throughput 같은 driver 지원 속성 변경을 요청합니다.

비동기 storage 변경이며 보편적인 무중단 보장이 아닙니다. Driver·controller 버전, API 제공 여부, IAM/KMS 권한, volume type 제한, 변경 cooldown과 상태를 확인합니다. 불완전한 PVC object를 완전한 생성 manifest처럼 적용하지 않습니다. 아래 조회로 원하는 class와 보고된 진행 상태를 비교합니다.

```bash
# Read-only: inspect one existing owned PVC and the CSI modification state.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pvc "$PVC_NAME" -o json | jq '{
    requestedClass:.spec.volumeAttributesClassName,
    currentClass:.status.currentVolumeAttributesClassName,
    modification:.status.modifyVolumeStatus,
    conditions:.status.conditions
  }'
```

AWS의 1.34 안내도 stable VAC API와 이전 beta sidecar 지원을 구분합니다. EKS 컨트롤 플레인 버전만으로 임의 EBS CSI release의 VAC API 호환성이 입증되지는 않습니다.

#### User namespace — 1.32에서는 beta, 기본 비활성화

User namespace는 1.30에서 beta, 1.33에서 기본 활성화되었으며 GA는 1.36입니다. Pod는 `hostUsers: false`로 opt-in합니다. Container의 UID 0은 구현이 선택한 non-root host UID로 매핑되며 모든 환경에 공통인 `65534 + offset` 공식이 아닙니다. 호환 kernel·filesystem·CRI/runtime이 필요하고 모든 workload·host 접근 방식이 호환되는 것은 아닙니다.

아래는 매핑을 설명하기 위해 container UID 0을 의도적으로 사용합니다. 예시 image를 바꾸고 지원되는 테스트 환경에서 사용합니다. 심층 방어이지 모든 kernel·container escape 취약점 방지 보장이나 다른 보안 제어의 대체재가 아닙니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: userns-example
  namespace: version-lab
spec:
  hostUsers: false
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    securityContext:
      runAsUser: 0
```

#### 기타 주요 변경

| 기능 | 1.32 상태 |
|---|---|
| CustomResourceFieldSelectors | GA; CRD 작성자가 지원 selectable field를 선언해야 함 |
| RetryGenerateName | GA; 이름 충돌을 재시도하지만 생성 성공을 보장하지는 않음 |
| SizeMemoryBackedVolumes | GA; memory-backed emptyDir 제한은 Pod·node memory와 함께 고려 |
| ServiceAccountTokenJTI | GA; token 식별자이며 새 인가 권한이 아님 |
| JobManagedBy | Beta; GA는 1.35 |
| DynamicResourceAllocation | Beta, 기본 비활성화; core API stable은 1.34 |
| MultiCIDRServiceAllocator | 아직 beta, 기본 비활성화 |
| NFTablesProxyMode | 아직 beta; GA는 1.33 |
| MutatingAdmissionPolicy | Alpha; beta는 1.34, GA는 1.36 |

`StableLoadBalancerNodeSet`은 1.30에서 이미 GA가 되었습니다. 이 과거 단계와 특정 EKS 클러스터에서 현재 활성화된 기능을 구분합니다.

[Kubernetes 1.32 release](https://kubernetes.io/blog/2024/12/11/kubernetes-v1-32-release/) · [Authorization configuration](https://kubernetes.io/docs/reference/access-authn-authz/authorization/) · [StatefulSet PVC retention](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#persistentvolumeclaim-retention) · [EKS version notes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)

---

### 4.5 Kubernetes 1.33 "Octarine" (2025년 4월)

4월 23일 릴리스의 수치는 **64개 enhancement: stable 18개, beta 20개, alpha 24개, deprecated 또는 withdrawn 2개**입니다. 그림은 세 성숙도 그룹의 62개를 전체 64개 대비 비율로 표시하며 나머지 2개는 그려져 있지 않습니다. 2025년의 대형 릴리스이지만 모든 workload의 성능·준비 상태가 더 좋다는 증거는 아닙니다.

![Kubernetes 1.33 릴리스의 전체 64개 Enhancement가 Stable(GA) 18개, Beta 20개, Alpha 24개로 나뉘어 성숙도 단계별로 분포한 것을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-10.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-10.html)

#### Native sidecar — GA

Alpha 1.28 → beta 1.29 → GA 1.33 순서로 진행했습니다. 재시작 가능한 init container에 `restartPolicy: Always`를 지정합니다. Sidecar의 `started`가 true가 되면 kubelet이 다음 init container로 진행합니다. Startup probe가 없으면 프로세스 실행, 있으면 해당 probe 성공을 의미하며 readiness는 별도 신호입니다. 아래 일반 init container는 **두 sidecar가 시작한 뒤** 실행되고, 완료 후 앱이 시작합니다.

이는 구조 예시입니다. 모든 `example.invalid` image를 검토한 구현으로 바꾸고 proxy는 선언한 readiness endpoint를 제공하며 log agent는 실제 pipeline을 설정해야 합니다. Envoy/Istio/Fluent Bit image만 지정한다고 service mesh나 log destination이 구성되지는 않습니다. 실제 DB migration에는 조정·멱등성이 필요하며 replica마다 실행해도 안전하다고 가정하지 않습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sidecar-lifecycle
  namespace: version-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sidecar-lifecycle
  template:
    metadata:
      labels:
        app: sidecar-lifecycle
    spec:
      terminationGracePeriodSeconds: 60
      initContainers:
      - name: proxy-helper
        image: example.invalid/version-lab/reviewed-proxy:reviewed
        restartPolicy: Always
        startupProbe:
          httpGet:
            path: /ready
            port: 15021
          periodSeconds: 2
          failureThreshold: 30
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
      - name: log-helper
        image: example.invalid/version-lab/reviewed-log-agent:reviewed
        restartPolicy: Always
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
      - name: initialize-app
        image: example.invalid/version-lab/reviewed-init:reviewed
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
      containers:
      - name: app
        image: example.invalid/version-lab/reviewed-app:reviewed
        volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
      volumes:
      - name: app-logs
        emptyDir: {}
```

일반적인 graceful termination에서는 main container 이후 sidecar를 역순으로 종료합니다. Pod의 공통 grace-period budget이 적용되므로 main 종료가 오래 걸리면 sidecar의 정상 종료 시간이 거의 남지 않을 수 있습니다. Native sidecar는 main container 완료 후 Job 완료를 막지 않으며 GA에서 처음 생긴 동작도 아닙니다. 용량 산정에는 동시에 실행하는 init·sidecar·app resource와 Pod overhead를 고려합니다. 여기서 수명주기 시간이나 앱 가용성을 측정하지 않았습니다.

#### 컨테이너 리소스 in-place resize — 1.33에서 beta

In-place resize는 Pod를 재생성하지 않고 원하는 CPU/memory 할당을 변경하지만 `resizePolicy`에 따라 container 재시작이 필요할 수 있습니다. 1.35에서 stable이 되었습니다. 아래 현재 schema 예시는 `Burstable` QoS를 유지하고 CPU는 `NotRequired`, memory는 `RestartContainer`로 설정합니다. 따라서 memory 변경은 정책상 container 재시작을 요청하며 모든 memory 변경의 본질적 제약이라는 뜻은 아닙니다.

호환 Linux runtime·node policy, 지원되는 kubectl skew, 소유 namespace와 검토한 image를 사용합니다. 1.36 문서의 일반 지원 범위에는 Windows와 기본 static CPU/Memory-manager 사례가 제외되며 별도 gate 기능은 버전별로 평가합니다. 이 API가 Deployment/StatefulSet template을 자동 변경하거나 HPA/VPA/GitOps의 resource 소유권을 조정하지는 않습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resizable-app
  namespace: version-lab
spec:
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    resources:
      requests:
        cpu: 500m
        memory: 256Mi
      limits:
        cpu: '1'
        memory: 512Mi
    resizePolicy:
    - resourceName: cpu
      restartPolicy: NotRequired
    - resourceName: memory
      restartPolicy: RestartContainer
```

용량·소유권을 검토한 뒤 아래 CPU-only 예시로 request 1 core, limit 2 core를 요청합니다. 이름으로 container를 선택하고 기존 Burstable class를 유지하며 CPU 재시작 정책이면 거부하고 Pod UID·resourceVersion을 확인한 뒤 patch합니다. Memory는 변경하지 않습니다. 충돌 시 강제 적용하지 말고 대상을 다시 읽어 판단합니다.

```bash
# MUTATION: reviewed CPU-only resize; desired request=1 core and limit=2 cores.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
resize_patch=$(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq -ce --arg container "$CONTAINER_NAME" '
    . as $pod |
    [(.spec.containers | to_entries[]) | select(.value.name == $container)] as $matches |
    if .status.phase != "Running" or .metadata.deletionTimestamp != null
       or ($matches | length) != 1
    then error("Expected one target container in a non-deleting Running Pod")
    elif .status.qosClass != "Burstable"
    then error("This example preserves an existing Burstable QoS class")
    elif $matches[0].value.resources.requests.cpu == null
         or $matches[0].value.resources.limits.cpu == null
    then error("This example requires existing CPU request and limit keys")
    elif any($matches[0].value.resizePolicy[]?; .resourceName == "cpu" and .restartPolicy == "RestartContainer")
    then error("This example requires CPU resize policy NotRequired")
    elif ([.status.containerStatuses[]? | select(.name == $container and .state.running != null)] | length) != 1
    then error("Target container is not reported running")
    else ($matches[0].key | tostring) as $i | [
      {op:"test",path:"/metadata/uid",value:$pod.metadata.uid},
      {op:"test",path:"/metadata/resourceVersion",value:$pod.metadata.resourceVersion},
      {op:"test",path:("/spec/containers/" + $i + "/name"),value:$container},
      {op:"replace",path:("/spec/containers/" + $i + "/resources/requests/cpu"),value:"1"},
      {op:"replace",path:("/spec/containers/" + $i + "/resources/limits/cpu"),value:"2"}
    ] end')
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  patch pod "$POD_NAME" --subresource=resize --type=json --patch "$resize_patch"
```

이전 `.status.resize` 문자열 대신 현재 status 필드를 사용합니다. `PodResizePending=True`는 `Deferred`·`Infeasible` 등을 보고하고 `PodResizeInProgress=True`는 적용 진행 중을 나타냅니다. 원하는 spec·확인된 generation·대상 container의 `status.containerStatuses[].resources`를 비교합니다. `allocatedResources`는 내부 할당 확인용 필드이며 runtime limit 적용의 단독 증거가 아닙니다. Condition 부재나 patch 수락만으로 workload 정상 여부를 판단하지 않습니다.

```bash
# Read-only observation; an accepted patch is not proof of completed actuation.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq --arg container "$CONTAINER_NAME" '{
    uid:.metadata.uid,generation:.metadata.generation,
    observedGeneration:.status.observedGeneration,qosClass:.status.qosClass,
    resizeConditions:[.status.conditions[]? | select(.type == "PodResizePending" or .type == "PodResizeInProgress")],
    desired:[.spec.containers[] | select(.name == $container) | .resources],
    reported:[.status.containerStatuses[]? | select(.name == $container) |
      {name,resources,allocatedResources,containerID,restartCount,ready}]
  }'
```

Resize로 Pod QoS class를 바꿀 수 없습니다. Guaranteed Pod는 CPU·memory request/limit 동등성을 유지해야 하며 위 예시는 의도적으로 Burstable입니다. `NotRequired` memory 축소는 best effort이고 사용량이 새 limit보다 크면 진행 상태에 머물 수 있으며 race로 OOM kill이 발생할 수도 있습니다. 재시작 불가능한 init·ephemeral container는 resize할 수 없습니다. 성숙도만으로 무중단·latency·resize 성공을 보장하지 않습니다.

#### 현재 VPA 연동은 별도의 버전 결정

다음은 **2026년 companion component 예시**이며 Kubernetes 1.33 출시 당시 VPA 1.7이 있었다는 뜻이 아닙니다. 출시된 VPA **1.7.1** API는 1.7.0에서 alpha로 도입한 `InPlace`를 지원합니다. Admission-controller·updater 양쪽의 VPA `InPlace` gate와 Kubernetes 1.33+ in-place-resize 지원이 필요합니다. VPA의 Pod eviction fallback을 피하지만 resize 완료나 모든 container policy의 무재시작을 보장하지 않습니다. 권고만 관찰하려면 먼저 `Off`를 사용합니다.

아래 CPU-only policy는 기존 Deployment/container의 예시 범위입니다. 변경 활성화 전에 controller 배포 flag와 용량을 검토합니다. `InPlaceOrRecreate`는 재생성으로 fallback할 수 있는 별도 모드이며 VPA 1.6에서 GA, 기존 gate는 1.7에서 제거되었습니다. 제거된 gate를 설정하거나 Kubernetes GA만으로 VPA 동작을 추론하지 않습니다.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: current-in-place-example
  namespace: version-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  updatePolicy:
    updateMode: InPlace
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 100m
      maxAllowed:
        cpu: '4'
      controlledResources:
      - cpu
      controlledValues: RequestsAndLimits
```

#### ServiceCIDR·IPAddress — GA

Upstream Kubernetes는 allocator·API가 활성화되어 있을 때 추가 `networking.k8s.io/v1` ServiceCIDR object로 사용 가능한 Service 주소를 확장할 수 있습니다. 기본 `kubernetes` object는 API server의 초기 범위를 나타냅니다. 추가 전에 IPAM·address family·routing 중복을 검토하며 할당된 Service IP가 고아가 되는 삭제는 finalizer로 보호됩니다. ServiceCIDR는 VPC subnet이나 Pod 주소 CIDR가 아닙니다.

아래 IPv4 manifest는 upstream 예시이며 실행·검증된 EKS 범위 확장이 아닙니다. EKS 생성 parameter `serviceIpv4Cidr`는 생성 후 불변입니다. 추가 Kubernetes ServiceCIDR 생성은 별도 작업이며 이번에 확인한 AWS 자료만으로 검증된 EKS 절차가 확립되지는 않습니다. EKS에 사용하기 전에 provider 지원·admission policy·대상 network를 확인합니다. API discovery만으로 검증을 대신하지 않습니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: ServiceCIDR
metadata:
  name: reviewed-extra-service-range
spec:
  cidrs:
  - 10.200.0.0/16
```

```bash
# Read-only discovery; do not interpret availability alone as an approved EKS change.
set -euo pipefail
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s api-resources --api-group=networking.k8s.io
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get servicecidrs
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get ipaddresses
```

#### Topology-aware routing·traffic distribution — GA

Topology-aware endpoint hint와 Service `trafficDistribution` 선호는 관련되지만 다른 메커니즘입니다. 아래 `PreferClose`는 같은 zone 선호이며 엄격한 same-zone 보장·region 간 거리 계산·기존 annotation의 일괄 deprecated 선언이 아닙니다. Ready endpoint 분포·proxy 구현·`internalTrafficPolicy`/`externalTrafficPolicy`가 경로에 영향을 줍니다.

Cross-AZ traffic에는 요금이 생길 수 있지만 기존의 고정 `$0.01/GB` 설명만으로 전체 비용을 계산할 수는 없습니다. Service·경로·계량되는 inbound/outbound 측에 따라 요금이 달라지고 일부 in-Region traffic에는 예외가 있습니다. 고정 절감 효과를 약속하지 말고 실제 traffic과 청구 data를 비교합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: same-zone-preference
  namespace: version-lab
spec:
  trafficDistribution: PreferClose
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

#### Job success policy — GA

Success policy는 Indexed Job에 적용합니다. 아래는 index 0 성공을 요구하며 앱이 해당 프로토콜을 구현해야만 이를 leader로 해석할 수 있습니다. Kubernetes가 분산 작업 결과의 완결성·내구성을 추론하지는 않습니다. Failure policy와 나머지 Pod 종료도 고려해야 합니다. 기존 예시에 빠진 Job template의 `restartPolicy: Never`를 명시했습니다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-success-example
  namespace: version-lab
spec:
  completionMode: Indexed
  completions: 8
  parallelism: 8
  backoffLimit: 2
  successPolicy:
    rules:
    - succeededIndexes: '0'
      succeededCount: 1
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: trainer
        image: example.invalid/version-lab/training:reviewed
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
```

#### OCI image volume — 1.33에서 beta, 기본 비활성화

Image volume은 모델 data 같은 OCI image 내용을 앱 image에 포함하지 않고 Pod에 제공합니다. 지원 runtime·기능 설정·registry pull identity가 필요합니다. 읽기 전용 mount이며 쓰기 가능한 PVC가 아닙니다. 앱·data image를 모두 검토하고 고정합니다. ImageVolume은 1.35에서 기본 활성화되고 1.36에서 stable이 되었으며 1.34 GA가 아닙니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: image-volume-example
  namespace: version-lab
spec:
  containers:
  - name: inference
    image: example.invalid/version-lab/inference:reviewed
    volumeMounts:
    - name: model
      mountPath: /models
      readOnly: true
  volumes:
  - name: model
    image:
      reference: example.invalid/version-lab/model:reviewed
      pullPolicy: IfNotPresent
```

#### 1.33의 기타 주요 단계

| 기능 | 상태 |
|---|---|
| NFTablesProxyMode·RecursiveReadOnlyMounts | GA |
| CRDValidationRatcheting | GA; 변경한 잘못된 필드의 검증을 우회하는 권한은 아님 |
| MatchLabelKeysInPodAffinity·NodeInclusionPolicyInPodTopologySpread | GA |
| PV reclaim-policy 삭제 보호 | GA; PVC 사용 중 보호와는 별개 |
| UserNamespacesSupport | Beta, 이제 기본 활성화 |
| PodLevelResources | 아직 alpha; beta는 1.34 |
| StructuredAuthenticationConfiguration | Beta; GA는 1.34 |
| MutatingAdmissionPolicy | 아직 alpha; beta는 1.34 |
| PodLifecycleSleepAction | Beta; GA는 1.34 |
| JobManagedBy | Beta; GA는 1.35 |

LoadBalancerIPMode·RetryGenerateName은 1.32에서 이미 GA였습니다. KYAML 도입은 1.33이 아닌 1.34입니다.

[Kubernetes 1.33 release](https://kubernetes.io/blog/2025/04/23/kubernetes-v1-33-release/) · [Versioned 1.36 resize guide](https://github.com/kubernetes/website/blob/release-1.36/content/en/docs/tasks/configure-pod-container/resize-container-resources.md) · [VPA 1.7.1 features](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/features.md) · [Service range extension](https://kubernetes.io/docs/tasks/network/extend-service-ip-ranges/) · [EKS network configuration API](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigRequest.html) · [Data-transfer charge interpretation](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html)

---

### 4.6 Kubernetes 1.34 "Of Wind & Will" (2025년 8월)

8월 27일 릴리스의 수치는 **58개 enhancement: stable 23개, beta 22개, alpha 13개**입니다. Beta의 기본값은 기능마다 다르며 그림의 일반적인 기본 활성화 표기를 실제 enablement matrix로 보지 않습니다.

<!-- Parent repair: DRA beta is1.32, VAC beta is1.31; current diagram reverses/misdates them.
![Kubernetes 1.34 릴리스의 전체 58개 Enhancement가 Stable(GA) 23개, Beta 22개, Alpha 13개로 나뉘고, GA 단계에서 DRA Core APIs와 VolumeAttributesClass가 졸업한 것을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-11.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-11.html)
-->

#### DRA core API — GA

DeviceClass·ResourceClaim·ResourceClaimTemplate·ResourceSlice는 built-in `resource.k8s.io/v1` API이며 설치해야 하는 DRA core CRD가 아닙니다. Driver가 ResourceSlice로 device inventory를 제공하고 scheduler가 자원을 할당하며 kubelet이 driver와 device 준비를 조정합니다. 아키텍처 그림은 논리 흐름이며 API server·ResourceSlice 전달 경로를 생략합니다.

DRA가 기존 device plugin 모델을 제거하거나 모든 vendor의 time-slicing·MPS·MIG·NUMA·network 기능을 자동 제공하지는 않습니다. 고급 DRA 기능은 별도 gate와 단계가 있으며 지원되는 조정 모델 없이 동일 device를 독립 allocator 두 개에 맡기지 않습니다.

아래는 **명시적인 가상 driver 계약**을 사용합니다. `gpu.example.com`이 문자열 `model`과 `numa` attribute를 제공한다고 가정하며 실제 NVIDIA driver의 attribute 이름·설정을 주장하지 않습니다. 설치한 driver의 ResourceSlice를 확인한 뒤 driver·attribute를 바꿉니다. Stable request의 `deviceClassName`·`allocationMode`·`count`는 `exactly` 아래에 있어야 하며 기존 root-level 형태는 잘못되었습니다. `matchAttribute`는 요청한 device 간 값 일치를 요구하는 강한 제약이지 NUMA 선호가 아닙니다.

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: example-a100
spec:
  selectors:
  - cel:
      expression: 'device.driver == "gpu.example.com" &&

        "gpu.example.com" in device.attributes &&

        "model" in device.attributes["gpu.example.com"] &&

        device.attributes["gpu.example.com"].model == "A100"'
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaim
metadata:
  name: training-gpus
  namespace: version-lab
spec:
  devices:
    requests:
    - name: gpu
      exactly:
        deviceClassName: example-a100
        allocationMode: ExactCount
        count: 4
    constraints:
    - requests:
      - gpu
      matchAttribute: gpu.example.com/numa
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: four-gpu-template
  namespace: version-lab
spec:
  spec:
    devices:
      requests:
      - name: gpu
        exactly:
          deviceClassName: example-a100
          allocationMode: ExactCount
          count: 4
      constraints:
      - requests:
        - gpu
        matchAttribute: gpu.example.com/numa
```

의도한 수명주기에 따라 명시적으로 관리하는 claim 또는 template의 Pod별 claim을 선택합니다. 아래는 두 대안을 보여 줍니다. Template도 device 4개를 요청하여 `--tensor-parallel-size 4`와 맞추며, 기존 1개 요청은 맞지 않았습니다. Inference image는 해당 인자를 구현해야 하고 모든 image는 placeholder입니다. Replica 1개에 적합한 device 4개가 필요하며 replica 3개면 12개가 필요합니다. GPU 할당이나 모델 서빙 benchmark를 실행하지 않았습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: direct-gpu-claim
  namespace: version-lab
spec:
  resourceClaims:
  - name: accelerators
    resourceClaimName: training-gpus
  containers:
  - name: trainer
    image: example.invalid/version-lab/trainer:reviewed
    resources:
      claims:
      - name: accelerators
        request: gpu
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: four-gpu-serving
  namespace: version-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: four-gpu-serving
  template:
    metadata:
      labels:
        app: four-gpu-serving
    spec:
      resourceClaims:
      - name: accelerators
        resourceClaimTemplateName: four-gpu-template
      containers:
      - name: inference
        image: example.invalid/version-lab/inference:reviewed
        args:
        - --tensor-parallel-size
        - '4'
        resources:
          claims:
          - name: accelerators
            request: gpu
```

#### VolumeAttributesClass — GA

VAC는 1.34부터 `storage.k8s.io/v1`을 사용합니다. 아래 class는 표준 `ebs.csi.aws.com` driver와 기존의 호환 regional gp3 volume용이며 자동으로 Auto Mode storage 절차가 되는 것은 아닙니다. PVC class 변경 전에 driver·sidecar·API 버전·권한·volume 크기/종류·변경 cooldown·instance EBS 제한을 확인합니다.

현재 regional gp3 상한은 **80,000 IOPS·2,000 MiB/s**이며 기본 3,000 IOPS 초과분에는 GiB당 500 IOPS, throughput에는 provisioned IOPS당 0.25 MiB/s 비율이 적용됩니다. 따라서 기존 64,000 IOPS는 최소 128 GiB에서 유효할 수 있지만 4,000 MiB/s는 gp3의 유효 값이 아닙니다. 예시는 이를 2,000으로 고치고 검증한 500-GiB volume을 전제로 합니다. Outposts 상한은 더 낮은 16,000 IOPS·1,000 MiB/s입니다. Volume 설정 상한이 앱·instance의 지속 성능을 보장하지는 않습니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: high-iops
driverName: ebs.csi.aws.com
parameters:
  iops: '16000'
  throughput: '1000'
---
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: standard
driverName: ebs.csi.aws.com
parameters:
  iops: '3000'
  throughput: '125'
---
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: io-intensive
driverName: ebs.csi.aws.com
parameters:
  iops: '64000'
  throughput: '2000'
---
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: throughput-optimized
driverName: ebs.csi.aws.com
parameters:
  iops: '3000'
  throughput: '750'
```

Class parameter는 불변이므로 class를 직접 수정하거나 불완전한 PVC를 생성하지 말고 기존 PVC에서 다른 class를 선택합니다. `.status.currentVolumeAttributesClassName`·`.status.modifyVolumeStatus`·event·실제 EBS 상태를 확인하며 요청 수락을 성능 변경 완료로 보지 않습니다.

기존 business-hours CronJob에는 identity/RBAC와 timezone·중복 처리 조건이 빠져 있었습니다. 아래의 완전한 **suspended 구성 예시**도 실제 실행된 운영 절차는 아닙니다. `version-lab`, 소유한 `database-pvc`, 호환 class, kubectl/jq와 신뢰할 수 있는 client 설정을 갖춘 image를 준비합니다. ServiceAccount는 namespace의 해당 이름 PVC만 get/patch할 수 있지만 RBAC가 patch할 PVC 필드까지 제한하지는 않습니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vac-scheduler
  namespace: version-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: vac-scheduler
  namespace: version-lab
rules:
- apiGroups:
  - ''
  resources:
  - persistentvolumeclaims
  resourceNames:
  - database-pvc
  verbs:
  - get
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: vac-scheduler
  namespace: version-lab
subjects:
- kind: ServiceAccount
  name: vac-scheduler
  namespace: version-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: vac-scheduler
```

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vac-business-hours
  namespace: version-lab
spec:
  schedule: 0 8 * * 1-5
  timeZone: Asia/Seoul
  suspend: true
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: vac-scheduler
          restartPolicy: Never
          containers:
          - name: request-class
            image: example.invalid/version-lab/kubectl-jq:reviewed
            command:
            - /bin/sh
            - -c
            - "set -eu\n: \"${POD_NAMESPACE:?}\"; : \"${TARGET_CLASS:?}\"\ncase \"\
              $TARGET_CLASS\" in high-iops|standard|io-intensive|throughput-optimized)\
              \ ;; *) exit 2 ;; esac\nstate=$(kubectl --request-timeout=15s -n \"\
              $POD_NAMESPACE\" get pvc database-pvc -o json)\npatch=$(printf '%s\\\
              n' \"$state\" | jq -ce --arg class \"$TARGET_CLASS\" '\n  if .metadata.deletionTimestamp\
              \ != null or .status.phase != \"Bound\"\n  then error(\"Expected an\
              \ existing non-deleting Bound PVC\")\n  elif .status.modifyVolumeStatus\
              \ != null\n  then error(\"Existing modification needs review before\
              \ another request\")\n  elif .spec.volumeAttributesClassName == $class\n\
              \  then []\n  else [\n    {op:\"test\",path:\"/metadata/uid\",value:.metadata.uid},\n\
              \    {op:\"test\",path:\"/metadata/resourceVersion\",value:.metadata.resourceVersion},\n\
              \    {op:\"add\",path:\"/spec/volumeAttributesClassName\",value:$class}\n\
              \  ] end')\nif [ \"$patch\" = '[]' ]; then\n  printf '%s\\n' 'Class\
              \ already requested; verify actual modification status separately.'\n\
              else\n  kubectl --request-timeout=15s -n \"$POD_NAMESPACE\" patch pvc\
              \ database-pvc --type=json --patch \"$patch\"\n  printf '%s\\n' 'Class\
              \ change requested; this is not proof of completed EBS modification.'\n\
              fi\n"
            env:
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: TARGET_CLASS
              value: io-intensive
            resources:
              requests:
                cpu: 50m
                memory: 64Mi
              limits:
                cpu: 200m
                memory: 128Mi
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vac-off-hours
  namespace: version-lab
spec:
  schedule: 0 22 * * 1-5
  timeZone: Asia/Seoul
  suspend: true
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: vac-scheduler
          restartPolicy: Never
          containers:
          - name: request-class
            image: example.invalid/version-lab/kubectl-jq:reviewed
            command:
            - /bin/sh
            - -c
            - "set -eu\n: \"${POD_NAMESPACE:?}\"; : \"${TARGET_CLASS:?}\"\ncase \"\
              $TARGET_CLASS\" in high-iops|standard|io-intensive|throughput-optimized)\
              \ ;; *) exit 2 ;; esac\nstate=$(kubectl --request-timeout=15s -n \"\
              $POD_NAMESPACE\" get pvc database-pvc -o json)\npatch=$(printf '%s\\\
              n' \"$state\" | jq -ce --arg class \"$TARGET_CLASS\" '\n  if .metadata.deletionTimestamp\
              \ != null or .status.phase != \"Bound\"\n  then error(\"Expected an\
              \ existing non-deleting Bound PVC\")\n  elif .status.modifyVolumeStatus\
              \ != null\n  then error(\"Existing modification needs review before\
              \ another request\")\n  elif .spec.volumeAttributesClassName == $class\n\
              \  then []\n  else [\n    {op:\"test\",path:\"/metadata/uid\",value:.metadata.uid},\n\
              \    {op:\"test\",path:\"/metadata/resourceVersion\",value:.metadata.resourceVersion},\n\
              \    {op:\"add\",path:\"/spec/volumeAttributesClassName\",value:$class}\n\
              \  ] end')\nif [ \"$patch\" = '[]' ]; then\n  printf '%s\\n' 'Class\
              \ already requested; verify actual modification status separately.'\n\
              else\n  kubectl --request-timeout=15s -n \"$POD_NAMESPACE\" patch pvc\
              \ database-pvc --type=json --patch \"$patch\"\n  printf '%s\\n' 'Class\
              \ change requested; this is not proof of completed EBS modification.'\n\
              fi\n"
            env:
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: TARGET_CLASS
              value: throughput-optimized
            resources:
              requests:
                cpu: 50m
                memory: 64Mi
              limits:
                cpu: 200m
                memory: 128Mi
```

시간대는 Asia/Seoul로 명시했습니다. `Forbid`는 CronJob별 제어이지 두 schedule·다른 운영자 사이의 공유 lock이 아닙니다. UID·resourceVersion test는 API patch를 보호할 뿐 비동기 EBS 작업 전체를 직렬화하지 않습니다. 명령은 기존 변경 상태가 있으면 거부하고 class 요청 사실만 출력합니다. Workload 영향·backend 상태 확인·조정·복구를 확립할 때까지 schedule을 suspended로 유지하며 production 준비 완료를 주장하지 않습니다.

#### Ordered namespace deletion — GA

Pod를 다른 namespaced resource보다 먼저 삭제하여 Pod가 살아 있는데 NetworkPolicy 같은 보안 제어가 먼저 사라지는 문제를 줄입니다. 임의 dependency graph를 계산하거나 모든 namespace 삭제 완료를 보장하지는 않습니다. 사용할 수 없는 API·controller·finalizer 때문에 여전히 멈출 수 있으므로 실제 condition을 조사합니다. Finalizer 강제 제거 또는 예시 transcript를 실측 해결 결과로 취급하지 않습니다.

#### KYAML — client 출력 형식, 1.34에서 alpha

KYAML은 **KEP-5295**이며 KEP-4222가 아닙니다. 명시적 구분자와 인용된 문자열 값을 사용하는 YAML-compatible 출력 형식입니다. API server admission validator·전체 YAML 1.2 마이그레이션이 아니며 모든 manifest에서 anchor를 제거해야 하는 이유도 아닙니다. Kubectl 1.35에서 beta/기본 활성화, 1.36에서도 beta였고 1.37에서 stable이 되었습니다.

아래 일반 YAML을 `format-example.yaml`로 저장합니다. Kubectl 1.36.2로 실제 확인한 로컬 예시는 anchor를 받아들이고 두 `"no"` 문자열을 유지하며 클러스터에 접속하지 않습니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kyaml-local-example
data:
  first: &string_value "no"
  norway: *string_value
```

```bash
# Local formatting example, checked with kubectl 1.36.2; no cluster request.
kubectl --kubeconfig=/dev/null --server=https://127.0.0.1:1 --request-timeout=1s \
  label --local --dry-run=client -f format-example.yaml \
  audit.example.com/checked=true -o kyaml
```

Kubectl 1.36.2의 `KUBECTL_KYAML=false`는 `-o kyaml` printer를 비활성화하지만 KYAML input은 다른 출력 형식에서도 YAML로 읽힙니다. EKS 컨트롤 플레인 설정을 바꾸지 않습니다. Schema/admission 검증과 formatting은 별개이며 기존 KYAML 경고·거부 transcript는 서버 기능의 유효한 시연이 아니었습니다.

#### MutatingAdmissionPolicy — 1.34에서 beta

MAP는 1.32 alpha, 1.34 beta(기본 비활성화), 1.36 GA 순서입니다. 아래는 **현재 1.36+ stable 형식**이며 1.34에 그대로 적용하는 manifest가 아닙니다. 과거 beta API는 `v1beta1`이고 적절한 serving·gate 설정이 필요했습니다. EKS 컨트롤 플레인 gate는 AWS가 관리합니다.

이 정책은 명시된 기존 값을 유지하면서 Deployment의 기본 label을 추가합니다. Namespace 기반 cost label은 예시이며 검증된 재무 배분 규칙이 아닙니다. Binding은 opt-in namespace만 선택하고 `failurePolicy: Fail`은 평가 오류 시 여전히 해당 요청을 막을 수 있습니다. Kubernetes 1.36.2의 실제 mutation compiler/patcher와 가상 Deployment로 표현식을 검사했지만 전체 admission chain·production 환경을 실행하지는 않았습니다. CEL의 결정성이 모든 조합 정책의 멱등성이나 reinvocation·순서 문제 해소를 보장하지 않습니다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata:
  name: version-lab-default-labels
spec:
  failurePolicy: Fail
  reinvocationPolicy: IfNeeded
  matchConstraints:
    resourceRules:
    - apiGroups:
      - apps
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - deployments
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: "Object{\n  metadata: Object.metadata{\n    labels: {\n      \"\
        app.kubernetes.io/managed-by\":\n        has(object.metadata.labels) && \"\
        app.kubernetes.io/managed-by\" in object.metadata.labels\n        ? object.metadata.labels[\"\
        app.kubernetes.io/managed-by\"] : \"platform-team\",\n      \"cost-center\"\
        :\n        has(object.metadata.labels) && \"cost-center\" in object.metadata.labels\n\
        \        ? object.metadata.labels[\"cost-center\"] : request.namespace\n \
        \   }\n  }\n}"
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata:
  name: version-lab-default-labels
spec:
  policyName: version-lab-default-labels
  matchResources:
    namespaceSelector:
      matchLabels:
        version-lab-policy: enabled
```

#### 1.34의 기타 주요 단계

| 기능 | 상태 |
|---|---|
| PodLevelResources | Beta, 기본 활성화; GA 아님 |
| ImageVolume | Beta, 1.35 전까지 기본 비활성화 |
| UserNamespacesSupport | Beta, 기본 활성화; GA는 1.36 |
| NFTablesProxyMode·MatchLabelKeysInPodAffinity·CRDValidationRatcheting | 1.33에서 이미 GA |
| KubeletTracing·PodLifecycleSleepAction | GA; 후자는 PreStop sleep action |
| JobPodReplacementPolicy·RecoverVolumeExpansionFailure | GA |
| StructuredAuthenticationConfiguration·AnonymousAuthConfigurableEndpoints | GA |
| NodeLogQuery | 아직 beta; GA는 1.36 |

이 예시의 표준 image pull policy에 `IfNotPresentOrNewer`는 없습니다. 지원되는 `Always`·`IfNotPresent`·`Never` 의미를 사용하고 image 불변성은 별도 검토합니다.

[Kubernetes 1.34 release](https://kubernetes.io/blog/2025/08/27/kubernetes-v1-34-release/) · [DRA](https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/) · [EBS gp3 limits](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html) · [KYAML KEP-5295](https://github.com/kubernetes/enhancements/tree/master/keps/sig-cli/5295-kyaml) · [Kubernetes 1.37 changelog](https://github.com/kubernetes/kubernetes/blob/v1.37.0/CHANGELOG/CHANGELOG-1.37.md) · [MutatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/)

---

### 4.7 Kubernetes 1.35 "Timbernetes" (2025년 12월)

12월 17일 발표는 **enhancement 60개**, 주요 단계별 **stable 17개·beta 19개·alpha 22개**를 보고합니다. 세 수의 합은 58이며 해당 분포가 나머지 2개를 별도로 설명하지는 않습니다. 다른 분류를 지어내거나 성능 측정치로 해석하지 않고 발표된 원 수치를 보존합니다.

![Kubernetes 1.35 릴리스의 전체 60개 Enhancement가 Stable(GA) 17개, Beta 19개, Alpha 22개로 나뉘어 성숙도 단계별로 분포한 것을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-12.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-12.html)

#### 컨테이너 리소스 in-place resize — GA

Alpha 1.27 → beta 1.33 → stable 1.35 순서입니다. 초기 alpha가 단순히 “1.33 전에는 CPU-only”였다는 설명은 맞지 않습니다. GA는 API 안정화이며 모든 memory resize·runtime·node policy·앱이 중단을 피한다는 보장이 아닙니다. 앞 절의 UID·resourceVersion 확인과 현재 status 필드를 사용하고 버전별 제약을 검토합니다.

일반적인 Deployment template 변경은 여전히 rollout을 일으킵니다. Pod API가 GA라고 자동 “Deployment rolling in-place resize”가 생기는 것은 아닙니다. 관리되는 Pod의 resize와 controller template 변경은 별개이며 교체 Pod는 template·admission 경로를 따릅니다. HPA·VPA·GitOps·custom resizer의 resource 소유권을 조정합니다.

아래 Deployment는 앞 VPA 예시의 `web-app`/`app` 대상을 제공합니다. Image·resource 값은 검토할 입력이며 앱은 port 8080 같은 Service endpoint를 실제로 구현해야 합니다. EKS에서 rollout·resize·서비스 가용성 검사를 실행하지 않았습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: version-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: app
        image: example.invalid/version-lab/app:reviewed
        resources:
          requests:
            cpu: 500m
            memory: 256Mi
          limits:
            cpu: '1'
            memory: 512Mi
        resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: RestartContainer
```

VPA는 별도 버전 체계를 따릅니다. `InPlaceOrRecreate`는 VPA 1.6에서 GA가 되었으며 in-place 실패 시 Pod를 재생성할 수 있습니다. `InPlace`는 별도 gate가 필요한 VPA 1.7 alpha 모드입니다. Eviction을 하지 않는다는 것이 모든 container resize policy의 무재시작이나 모든 권고의 적용 가능성을 보장하지는 않습니다. 앞의 현재 VPA 예시 조건을 따르며 Kubernetes 1.35만으로 해당 VPA 모드가 활성화되지는 않습니다.

#### PreferSameNode traffic distribution — GA

`PreferSameTrafficDistribution`은 1.35에서 stable이 되었습니다. `PreferSameNode`는 가능한 경우 같은 node endpoint를 선호하고 fallback을 허용하므로 엄격한 `internalTrafficPolicy: Local`과 다릅니다. 실제 Service 구현·ready endpoint·traffic policy 우선순위를 확인합니다. 모든 ALB/NLB routing을 제어하거나 cross-zone traffic을 없애는 보장이 아닙니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: prefer-same-node
  namespace: version-lab
spec:
  trafficDistribution: PreferSameNode
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

#### KYAML — beta, kubectl에서 기본 활성화

1.35의 beta·기본 활성화는 `-o kyaml` 출력 형식에 대한 것입니다. 모든 API server 입력을 새 strict parser로 바꾸거나 모든 YAML anchor에 경고하거나 서버 gate 변경을 위해 EKS 지원 티켓을 요구하지 않습니다. 앞의 로컬 예시와 실제 1.36.2 검사가 동작을 보여 줍니다. KYAML stable은 1.36이 아닌 1.37입니다.

#### Native gang scheduling — alpha, KEP-4671

Kubernetes 1.35에 native workload-aware/gang scheduling 개념이 도입되었습니다. 1.36에도 alpha이며 `GenericWorkload`·`GangScheduling`과 적절한 API·scheduler 활성화가 필요합니다. EKS version FAQ는 alpha 기능을 지원하지 않으며 self-managed node gate로 없는 EKS 컨트롤 플레인 API를 켤 수는 없습니다.

아래는 **upstream 실험 환경용 1.36 `v1alpha2` schema 예시**이지 이전 1.35 schema나 GA EKS 절차가 아닙니다. `spec.schedulingPolicy.gang.minCount`와 Pod의 `spec.schedulingGroup.podGroupName`을 사용합니다. 기존 `minMember`·`scheduleTimeoutSeconds`, Pod label·schedulingGate만으로 이 native API를 구성할 수 없습니다. 외부 PodGroup CRD는 별도 계약을 따릅니다.

```yaml
apiVersion: scheduling.k8s.io/v1alpha2
kind: PodGroup
metadata:
  name: experimental-training
  namespace: version-lab
spec:
  schedulingPolicy:
    gang:
      minCount: 8
```

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: experimental-training
  namespace: version-lab
spec:
  completionMode: Indexed
  completions: 8
  parallelism: 8
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      schedulingGroup:
        podGroupName: experimental-training
      containers:
      - name: worker
        image: example.invalid/version-lab/worker:reviewed
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: '1'
            memory: 256Mi
```

최소 group 크기와 Job parallelism·completions를 모두 8로 맞췄습니다. Standalone group 예시이므로 소유자·controller가 group 수명주기를 관리하고 Pod scheduling 중 연결 관계를 안정적으로 유지해야 합니다. Scheduling 결정은 프로세스 동시 시작·readiness·분산 계산 성공·모든 deadlock 방지를 보장하지 않습니다. 앱에는 barrier·timeout/복구 로직·호환 용량이 필요합니다. Object schema만 확인했으며 group placement 실험은 실행하지 않았습니다.

#### 주요 버전·업그레이드 고려사항

| 항목 | 올바른 해석 |
|---|---|
| JobManagedBy | 1.35에서 GA |
| ImageVolume | Beta, 이제 기본 활성화; GA는 1.36 |
| PodLevelResources | 1.34 beta 이후 여전히 beta |
| UserNamespacesSupport | 아직 beta; GA는 1.36 |
| ContextualLogging | 여전히 beta이며 1.35 GA 아님 |
| CRDValidationRatcheting | 1.33에서 이미 GA |
| NodeInclusionPolicyInPodTopologySpread | 1.33에서 이미 GA |
| RecoverVolumeExpansionFailure·익명 인증 endpoint 설정 | 1.34에서 이미 GA |

Node 업그레이드에서는 “GA이므로 production 안전”을 가정하지 말고 cgroup·runtime 조건을 확인합니다. EKS 1.35 안내는 kubelet의 기본 cgroup v1 거부와 Fargate 같은 provider별 사례를 구분하므로 관리되는 Fargate host 설정을 직접 편집하지 않습니다. 해당 안내에서 Kubernetes 1.35는 containerd 1.x를 지원하는 마지막 릴리스이며 kubelet의 `--pod-infra-container-image` flag도 제거되었습니다. 현재 EKS node·AMI 절차와 업그레이드 문서를 따르고 bootstrap flag를 일괄 덮어쓰지 않습니다.

[Kubernetes 1.35 release](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/) · [Versioned 1.36 feature gates](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go) · [Kubernetes 1.36.2 API schema](https://github.com/kubernetes/kubernetes/blob/v1.36.2/api/openapi-spec/swagger.json) · [EKS version notes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)

---

### 4.8 Kubernetes 1.36 "Haru" (2026년 4월)

4월 22일 발표의 전체 수치는 **enhancement 70개**이며 단계별 분포에 **stable 18개·beta 25개·alpha 25개**를 제시합니다. 세 그룹의 합은 68이며 기존 문서는 이 부분합을 전체 수치로 잘못 사용했습니다. EKS 출시일은 별도 지원 일정 표에 기록합니다.

<!-- Parent repair: release total is70, not68; verify stage/default/provider labels before restoring.
![Kubernetes 1.36 "Haru" 릴리스의 전체 68개 Enhancement가 Stable(GA) 18개, Beta 25개, Alpha 25개로 성숙도 단계별로 나뉘고, GA 졸업 경로가 강조되며 Beta는 기본 활성화, Alpha는 Feature Gate가 필요함을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-13.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-13.html)
-->

#### MutatingAdmissionPolicy — GA

Stable resource는 `admissionregistration.k8s.io/v1`의 `MutatingAdmissionPolicy`·`MutatingAdmissionPolicyBinding`입니다. 지원되는 mutation에 별도 webhook이 필요 없어지지만 정책 실패·비용 제한·순서·재호출 고려사항이 사라지지는 않습니다. 결정성이 모든 정책의 멱등성을 보장하지 않습니다.

아래 resize-policy 예시는 명시적 opt-in이며 값이 있는 `resizePolicy`가 없는 container에만 기본값을 추가해 기존 명시적 정책을 보존합니다. Kubernetes CEL은 `indexOf()`를 지원합니다. 기존 표현식도 유효했지만 기존 정책을 덮어썼으며, 실제 Kubernetes 1.36.2 compiler/patcher 검사로 이전 동작과 수정 동작을 확인했습니다. `resizePolicy`는 atomic list이므로 ApplyConfiguration patcher로 수정하면 거부되고 여기에는 JSONPatch가 적절합니다. 이 구현에서 MAP 내부 JSONPatch의 `test` 실패는 자동 admission 거부가 아닌 no-op으로 처리됩니다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicy
metadata:
  name: inject-resizepolicy
spec:
  failurePolicy: Fail
  reinvocationPolicy: Never
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: only-resize-enabled
    expression: has(object.metadata.annotations) && ("resize.example.com/enabled"
      in object.metadata.annotations) && object.metadata.annotations["resize.example.com/enabled"]
      == "true"
  mutations:
  - patchType: JSONPatch
    jsonPatch:
      expression: "object.spec.containers.filter(c, !has(c.resizePolicy)).map(c, JSONPatch{\n\
        \  op: \"add\",\n  path: \"/spec/containers/\" + string(object.spec.containers.indexOf(c))\
        \ + \"/resizePolicy\",\n  value: [\n    {\"resourceName\": \"cpu\",    \"\
        restartPolicy\": \"NotRequired\"},\n    {\"resourceName\": \"memory\", \"\
        restartPolicy\": \"RestartContainer\"}\n  ]\n})"
---
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingAdmissionPolicyBinding
metadata:
  name: inject-resizepolicy-binding
spec:
  policyName: inject-resizepolicy
  matchResources:
    namespaceSelector:
      matchLabels:
        map-demo: 'true'
```

이 binding에는 소유한 테스트 namespace만 label로 연결합니다. `failurePolicy: Fail`은 평가 실패 시 해당 Pod 생성을 여전히 막을 수 있습니다. Workload에 적용하기 전에 정책 준비 상태·실패 사례·전체 admission chain을 확인하며 정책 생성 후 고정 시간 sleep을 readiness 보장으로 보지 않습니다. 주입된 필드 관찰만으로 어느 admission component가 만들었는지 확정할 수는 없습니다.

#### In-place resize와 Pod-level budget

Container별 resize는 1.35에서 이미 GA였습니다. 별도 `InPlacePodLevelResourcesVerticalScaling`은 1.36에서 beta/기본 활성화되며 PodLevelResources 자체는 여전히 beta입니다. Pod-level budget과 container limit는 별도 계량·정책 검토가 필요합니다. 아래 예시는 Pod-level budget을 의도적으로 거부하는 뒤의 CPU-downscale prototype 대상이 아닙니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-budget-example
  namespace: version-lab
spec:
  os:
    name: linux
  nodeSelector:
    kubernetes.io/os: linux
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      cpu: '4'
      memory: 8Gi
  containers:
  - name: app
    image: example.invalid/version-lab/app:reviewed
    resources:
      requests:
        cpu: '1'
        memory: 2Gi
  - name: helper
    image: example.invalid/version-lab/helper:reviewed
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
```

CPUManager checkpoint 개선이 모든 static CPU/Memory-manager workload의 resize나 특정 NUMA 배치 보존을 입증하지는 않습니다. 해당 경로에는 별도 기능·지원 조건이 있습니다. `NotRequired`는 정책상 재시작을 요구하지 않는다는 뜻이지 모든 중단 방지가 아닙니다. `RestartContainer`는 해당 resource 변경 시 재시작을 요청하며 `NotRequired` memory 축소도 best effort라 지연되거나 OOM race가 생길 수 있습니다. 실제 container resource와 앱 동작을 확인합니다.

#### User namespace·kubelet 인가·device health

UserNamespacesSupport의 GA는 **1.36**이며 출시된 1.36.2 소스에도 잠긴 gate가 남아 있습니다. Pod는 `hostUsers: false`로 opt-in하고 호환 kernel·filesystem·runtime 조건을 만족해야 합니다. UID 매핑은 심층 방어이지 모든 escape가 무해하거나 모든 앱을 수정 없이 실행한다는 증명이 아닙니다.

KubeletFineGrainedAuthz도 GA가 됩니다. `/pods`·`/runningPods`·`/configz`·`/healthz`에 더 세밀한 검사를 수행한 뒤 넓은 `nodes/proxy` 권한으로 fallback합니다. `/metrics`·`/stats`·`/logs`에는 이미 별도 subresource 구분이 있었습니다. Kubelet의 API server 접근을 제어하는 Node authorizer와 혼동하지 말고 호출자의 실제 권한을 검토하며 더 좁은 권한으로 충분하면 넓은 proxy 권한을 피합니다.

ResourceHealthStatus는 1.36에서 beta가 되어 device plugin·DRA의 device별 health를 보고할 수 있습니다. `status.containerStatuses[].allocatedResourcesStatus`를 확인하며 `status.resourceClaimStatuses`는 claim 참조·생성된 이름의 매핑입니다. 누락·Unknown·Unhealthy 상태는 driver·node·앱과 대조해야 하며 단독으로 원인을 확정하거나 device reset을 허가하지 않습니다.

```bash
# Read-only per-container resource health; no device reset or Pod deletion.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" get pod "$POD_NAME" -o json |
  jq '{uid:.metadata.uid,containers:[.status.containerStatuses[]? |
       {name,allocatedResourcesStatus}]}'
```

LegacyServiceAccountTokenCleanUp은 **1.30**에서 이미 GA였으며 1.36의 새 GA가 아닙니다. Cleanup은 ServiceAccount 참조와 사용·mount 조건 등으로 자동 생성된 legacy token Secret을 구분합니다. 기본 미사용 기간은 무효화 전 1년이며 이후에도 미사용이면 삭제됩니다. 모든 과거 token이나 수동 생성 token이 제거된다는 뜻은 아닙니다. 유효기간이 제한된 TokenRequest token을 우선하고 감사 편의를 위해 token 값을 출력하지 않습니다.

#### SELinux·networking·기타 호환성 변경

출시된 1.36.2 gate 정의는 **SELinuxMountReadWriteOncePod**·**SELinuxChangePolicy**(GA)와 **SELinuxMount**(여전히 beta/기본 false)를 구분합니다. 일부 요약 문서는 이를 더 넓게 표현합니다. 모든 volume의 mount-label 동작이 같아졌다고 단정하지 말고 실제 node·provider 설정, CSI 지원, volume 공유 방식을 확인합니다. 서로 다른 SELinux label로 volume을 공유하면 명시적인 검토가 필요할 수 있습니다.

`StrictIPCIDRValidation`은 1.36에서 beta/기본 활성화입니다. 검사 대상 built-in 필드를 생성·변경할 때 canonical IP/CIDR을 사용합니다. 기존 저장 값에는 validation ratcheting 호환성이 적용될 수 있으며 모든 CRD를 자동 정규화하는 기능은 아닙니다. `gitRepo` volume driver는 1.36에서 영구 비활성화됩니다. API schema에 필드가 남아 있어도 kubelet이 해당 volume 실행을 거부하므로 업그레이드 전에 workload 패턴을 변경합니다.

Service `externalIPs`는 1.36에서 deprecated되며 발표된 제거 목표는 향후 계획이지 이 릴리스의 제거가 아닙니다. Upstream 1.36.2에는 IPVS proxier 코드와 생성 경로가 남아 있습니다. AWS version 요약의 제거 표현은 이 upstream 코드와 다르므로 보편적인 upstream 제거 사실로 바꾸거나 특정 EKS add-on image의 지원을 추정하지 않습니다. 선택한 EKS add-on과 마이그레이션 경로를 별도 확인합니다. 여기서는 EKS IPVS runtime을 검사하지 않았습니다.

ImageVolume·NodeLogQuery는 1.36 GA입니다. DRA partitionable device·consumable capacity·device binding condition은 각각의 beta gate를 따릅니다. KYAML은 1.36에서도 kubectl beta(1.37 stable)이고 GenericWorkload/GangScheduling은 1.36에서도 alpha입니다. 이전 버전의 GA를 새 1.36 GA로 다시 분류하지 않습니다.

#### 단계별 CPU downscale prototype

시작 부하가 큰 앱은 steady-state CPU 할당을 달리할 수 있지만 적절한 하한은 해당 앱에서 측정해야 합니다. Kubernetes의 `Running`은 warmup 완료 신호가 아닙니다. 아래는 실제 startupProbe 신호를 기본으로 사용하는 좁은 CPU-only 계약의 **실험용 컨트롤러이며 클러스터에서 실행하지 않았습니다**. Production-ready 컨트롤러나 가용성 보장이 아닙니다.

필수 입력은 하나의 `WATCH_NAMESPACE`와 검토한 양수 `MIN_STEADY_CPU`입니다. 해당 namespace에서 `resize.example.com/managed=true` label의 Pod만 watch하고 opt-in annotation도 요구합니다. Label·annotation 선택은 인가 경계가 아니므로 namespace의 workload 작성자를 신뢰해야 합니다. 명시적으로 선택한 Linux·container-level Guaranteed Pod만 허용하며 app/init의 CPU·memory request와 limit가 같아야 합니다. Memory 변경·upscale·잘못된 target·CPU 재시작 정책·진행 중 resize·확인되지 않거나 서로 다른 관측 resource는 거부합니다.

StartupProbePassed는 모든 target의 실제 startupProbe와 `started=true`를 요구합니다. Ready·Delay는 명시적인 대안이며 Ready에는 의미 있는 readiness 신호가 필요하고 Delay는 타이머일 뿐 warmup 완료의 증거가 아닙니다. 30초 resync와 API·reconciliation 지연 때문에 정확한 시점 보장도 아닙니다.

호환 dependency를 사용합니다. 감사에서는 Go 1.27.1·Kubernetes library v0.36.2를 사용했습니다.

```text
module example.com/pod-resizer

go 1.26.0

require (
    k8s.io/api v0.36.2
    k8s.io/apimachinery v0.36.2
    k8s.io/client-go v0.36.2
)
```

```go
// Experimental CPU-downscale controller for Kubernetes 1.36.
// Not a production-readiness or zero-downtime guarantee.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/validation"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/util/workqueue"
)

const (
	managedLabel = "resize.example.com/managed"
	annEnabled   = "resize.example.com/enabled"
	annTrigger   = "resize.example.com/trigger"
	annDelay     = "resize.example.com/delay-seconds"
	annSteady    = "resize.example.com/steady-resources"
)

type config struct {
	namespace string
	minCPU    resource.Quantity
}

type resourceValues struct {
	Requests map[string]string `json:"requests"`
	Limits   map[string]string `json:"limits"`
}

type patchOperation struct {
	Op    string `json:"op"`
	Path  string `json:"path"`
	Value any    `json:"value"`
}

func main() {
	namespace := os.Getenv("WATCH_NAMESPACE")
	minCPU, err := resource.ParseQuantity(os.Getenv("MIN_STEADY_CPU"))
	if len(validation.IsDNS1123Label(namespace)) != 0 || err != nil || minCPU.Sign() <= 0 {
		log.Fatal("Set one valid WATCH_NAMESPACE and a reviewed positive MIN_STEADY_CPU")
	}
	cfg := config{namespace: namespace, minCPU: minCPU}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	clientConfig, err := rest.InClusterConfig()
	if err != nil {
		log.Fatal("In-cluster client configuration unavailable")
	}
	clientConfig.QPS, clientConfig.Burst = 5, 10
	client, err := kubernetes.NewForConfig(clientConfig)
	if err != nil {
		log.Fatal("Client initialization failed")
	}
	factory := informers.NewSharedInformerFactoryWithOptions(client, 30*time.Second,
		informers.WithNamespace(namespace),
		informers.WithTweakListOptions(func(options *metav1.ListOptions) {
			options.LabelSelector = managedLabel + "=true"
		}))
	informer := factory.Core().V1().Pods().Informer()
	queue := workqueue.NewTypedRateLimitingQueue(workqueue.DefaultTypedControllerRateLimiter[string]())
	enqueue := func(obj any) {
		key, err := cache.MetaNamespaceKeyFunc(obj)
		if err == nil {
			queue.Add(key)
		}
	}
	_, err = informer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: enqueue, UpdateFunc: func(_, current any) { enqueue(current) },
	})
	if err != nil {
		log.Fatal("Informer handler registration failed")
	}
	factory.Start(ctx.Done())
	if !cache.WaitForCacheSync(ctx.Done(), informer.HasSynced) {
		queue.ShutDown()
		return
	}
	log.Printf("Cache synchronized; watching one namespace: %s", namespace)
	var workers sync.WaitGroup
	workers.Add(1)
	go func() {
		defer workers.Done()
		for {
			key, shutdown := queue.Get()
			if shutdown {
				return
			}
			obj, exists, err := informer.GetIndexer().GetByKey(key)
			if err == nil && exists {
				pod, ok := obj.(*corev1.Pod)
				if ok {
					err = requestResize(ctx, client, pod, cfg, time.Now())
				}
			}
			if err != nil && ctx.Err() == nil && queue.NumRequeues(key) < 5 {
				queue.AddRateLimited(key)
			} else {
				queue.Forget(key)
				if err != nil {
					log.Printf("Request failed for %s (%s); later events/resync may retry", key, apierrors.ReasonForError(err))
				}
			}
			queue.Done(key)
		}
	}()
	<-ctx.Done()
	queue.ShutDown()
	workers.Wait()
}

func requestResize(ctx context.Context, client kubernetes.Interface, pod *corev1.Pod, cfg config, now time.Time) error {
	patch, err := buildResizePatch(pod, cfg, now)
	if err != nil {
		// Do not log annotation values, credentials or entire Pod objects.
		log.Printf("Configuration needs review for %s/%s: %v", pod.Namespace, pod.Name, err)
		return nil // Retry only on a later event/resync, not a tight error loop.
	}
	if len(patch) == 0 {
		return nil
	}
	requestCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	_, err = client.CoreV1().Pods(pod.Namespace).Patch(requestCtx, pod.Name,
		types.JSONPatchType, patch, metav1.PatchOptions{}, "resize")
	if err == nil {
		log.Printf("RESIZE_REQUESTED %s/%s uid=%s; verify kubelet status separately",
			pod.Namespace, pod.Name, pod.UID)
	}
	return err
}

func buildResizePatch(pod *corev1.Pod, cfg config, now time.Time) ([]byte, error) {
	if pod == nil || pod.Namespace != cfg.namespace || pod.Labels[managedLabel] != "true" ||
		pod.Annotations[annEnabled] != "true" || pod.DeletionTimestamp != nil ||
		pod.Status.Phase != corev1.PodRunning {
		return nil, nil
	}
	if pod.UID == "" || pod.ResourceVersion == "" {
		return nil, errors.New("missing Pod identity/version")
	}
	// This prototype deliberately handles only container-level Guaranteed Linux Pods.
	if pod.Spec.OS == nil || pod.Spec.OS.Name != corev1.Linux ||
		pod.Spec.NodeSelector[corev1.LabelOSStable] != "linux" ||
		pod.Spec.Resources != nil || pod.Status.QOSClass != corev1.PodQOSGuaranteed {
		return nil, errors.New("prototype requires declared Linux, container-level Guaranteed resources")
	}
	for _, c := range append(append([]corev1.Container{}, pod.Spec.Containers...), pod.Spec.InitContainers...) {
		for _, name := range []corev1.ResourceName{corev1.ResourceCPU, corev1.ResourceMemory} {
			request, hasRequest := c.Resources.Requests[name]
			limit, hasLimit := c.Resources.Limits[name]
			if !hasRequest || !hasLimit || request.Sign() <= 0 || request.Cmp(limit) != 0 {
				return nil, errors.New("all app/init resources must satisfy the Guaranteed contract")
			}
		}
	}
	if pod.Status.ObservedGeneration < pod.Generation {
		return nil, nil
	}
	for _, condition := range pod.Status.Conditions {
		if condition.Status == corev1.ConditionTrue &&
			(condition.Type == corev1.PodResizePending || condition.Type == corev1.PodResizeInProgress) {
			return nil, nil
		}
	}
	raw := pod.Annotations[annSteady]
	if len(raw) == 0 || len(raw) > 4096 {
		return nil, errors.New("missing or oversized steady-resources annotation")
	}
	var desired map[string]resourceValues
	decoder := json.NewDecoder(strings.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&desired); err != nil {
		return nil, errors.New("invalid steady-resources JSON shape")
	}
	if err := decoder.Decode(new(any)); err != io.EOF || len(desired) == 0 {
		return nil, errors.New("expected one nonempty steady-resources object")
	}
	trigger := pod.Annotations[annTrigger]
	if trigger == "" {
		trigger = "StartupProbePassed"
	}
	delay := 0
	switch trigger {
	case "StartupProbePassed", "Ready":
	case "Delay":
		var err error
		delay, err = strconv.Atoi(pod.Annotations[annDelay])
		if err != nil || delay < 1 || delay > 3600 {
			return nil, errors.New("Delay requires an integer from1 to3600 seconds")
		}
	default:
		return nil, errors.New("unknown trigger")
	}
	podReady := false
	for _, condition := range pod.Status.Conditions {
		if condition.Type == corev1.PodReady && condition.Status == corev1.ConditionTrue {
			podReady = true
		}
	}
	statuses := make(map[string]corev1.ContainerStatus, len(pod.Status.ContainerStatuses))
	for _, status := range pod.Status.ContainerStatuses {
		statuses[status.Name] = status
	}
	ops := []patchOperation{
		{Op: "test", Path: "/metadata/uid", Value: string(pod.UID)},
		{Op: "test", Path: "/metadata/resourceVersion", Value: pod.ResourceVersion},
	}
	matched := 0
	for i, container := range pod.Spec.Containers {
		values, selected := desired[container.Name]
		if !selected {
			continue
		}
		matched++
		if len(values.Requests) != 1 || len(values.Limits) != 1 ||
			values.Requests["cpu"] == "" || values.Limits["cpu"] == "" {
			return nil, errors.New("only explicit CPU request and limit are supported")
		}
		request, errRequest := resource.ParseQuantity(values.Requests["cpu"])
		limit, errLimit := resource.ParseQuantity(values.Limits["cpu"])
		current := container.Resources.Requests[corev1.ResourceCPU]
		if errRequest != nil || errLimit != nil || request.Sign() <= 0 ||
			request.Cmp(limit) != 0 || request.Cmp(cfg.minCPU) < 0 || request.Cmp(current) > 0 {
			return nil, errors.New("CPU target must be equal, positive, above the floor and no larger than current")
		}
		for _, policy := range container.ResizePolicy {
			if policy.ResourceName == corev1.ResourceCPU && policy.RestartPolicy == corev1.RestartContainer {
				return nil, errors.New("CPU restart policy is incompatible with this prototype")
			}
		}
		status, exists := statuses[container.Name]
		if !exists || status.State.Running == nil || status.Resources == nil {
			return nil, nil
		}
		observedRequest, rqOK := status.Resources.Requests[corev1.ResourceCPU]
		observedLimit, lmOK := status.Resources.Limits[corev1.ResourceCPU]
		if !rqOK || !lmOK || observedRequest.Cmp(current) != 0 || observedLimit.Cmp(current) != 0 {
			return nil, nil
		}
		switch trigger {
		case "StartupProbePassed":
			if container.StartupProbe == nil {
				return nil, errors.New("StartupProbePassed requires a real startupProbe on every target")
			}
			if status.Started == nil || !*status.Started {
				return nil, nil
			}
		case "Ready":
			if !podReady {
				return nil, nil
			}
		case "Delay":
			if status.State.Running.StartedAt.IsZero() ||
				now.Sub(status.State.Running.StartedAt.Time) < time.Duration(delay)*time.Second {
				return nil, nil
			}
		}
		if request.Cmp(current) == 0 {
			continue
		}
		base := fmt.Sprintf("/spec/containers/%d", i)
		ops = append(ops,
			patchOperation{Op: "test", Path: base + "/name", Value: container.Name},
			patchOperation{Op: "replace", Path: base + "/resources/requests/cpu", Value: request.String()},
			patchOperation{Op: "replace", Path: base + "/resources/limits/cpu", Value: request.String()})
	}
	if matched != len(desired) {
		return nil, errors.New("steady-resources contains an unknown regular container")
	}
	if len(ops) == 2 {
		return nil, nil
	}
	return json.Marshal(ops)
}
```

PATCH 성공은 `RESIZE_REQUESTED`로 기록하며 완료 처리하지 않습니다. UID·resourceVersion test가 오래된 이름·변경된 object를 거부하고 work queue로 재시도를 제한하며 취소를 처리합니다. 기존의 계속 증가하는 processed-UID map도 사용하지 않습니다. Prototype은 같은 Pod 안의 container 재시작에 startup CPU를 복원하거나 다른 HPA/VPA/GitOps writer와 조정하거나 배포 packaging·readiness·HA 정책·앱 SLO를 입증하지 않습니다. 여러 workload controller가 대상 Pod를 만들 수 있지만 rollout·교체·storage 동작은 별도 통합 검증이 필요합니다.

ServiceAccount는 namespace 범위의 Pod 읽기와 resize subresource 쓰기만 가지며 일반 Pod patch·Secret-read 권한은 없습니다. 기존 namespace·label을 준비하고 controller image를 빌드·검토해 해당 ServiceAccount로 실행하며 필수 환경변수 두 개를 지정합니다. Demo 하한 `50m`는 예시이지 일반 production 권장값이 아닙니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: version-lab
  labels:
    map-demo: 'true'
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pod-resizer
  namespace: version-lab
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-resizer
  namespace: version-lab
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ''
  resources:
  - pods/resize
  verbs:
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pod-resizer
  namespace: version-lab
subjects:
- kind: ServiceAccount
  name: pod-resizer
  namespace: version-lab
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-resizer
```

아래 workload는 controller 계약에 맞춥니다. 실제 CPU 작업이 아닌 sleep으로 warmup을 모사하며 기존 200m→50m·64Mi demo 입력을 보존합니다. 사용 전에 image를 검토·고정합니다. 시작 프로세스가 readiness 파일을 만들고 probe는 확인만 합니다. 기본 timeout 1초인데 probe가 8초 sleep하고 main이 파일을 만들지 않던 기존 문제를 고쳤습니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phase-aware-demo
  namespace: version-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: phase-aware-demo
  template:
    metadata:
      labels:
        app: phase-aware-demo
        resize.example.com/managed: 'true'
      annotations:
        resize.example.com/enabled: 'true'
        resize.example.com/trigger: StartupProbePassed
        resize.example.com/steady-resources: '{"app":{"requests":{"cpu":"50m"},"limits":{"cpu":"50m"}}}'
    spec:
      os:
        name: linux
      nodeSelector:
        kubernetes.io/os: linux
      automountServiceAccountToken: false
      containers:
      - name: app
        image: busybox:1.36
        command:
        - sh
        - -ec
        - 'echo ''starting illustrative warmup''

          sleep 10

          touch "$READY_FILE"

          echo ''readiness file created''

          exec sleep 86400'
        env:
        - name: READY_FILE
          value: /tmp/ready
        resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: RestartContainer
        resources:
          requests:
            cpu: 200m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 64Mi
        startupProbe:
          exec:
            command:
            - sh
            - -ec
            - test -f "$READY_FILE"
          initialDelaySeconds: 1
          periodSeconds: 2
          timeoutSeconds: 1
          failureThreshold: 30
```

```bash
# Read-only observation for the owned example.
set -euo pipefail
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n version-lab \
  get pods -l app=phase-aware-demo -o json | jq '.items[] | {
    name:.metadata.name,uid:.metadata.uid,generation:.metadata.generation,
    observedGeneration:.status.observedGeneration,qosClass:.status.qosClass,
    desired:[.spec.containers[] | {name,resources}],
    reported:[.status.containerStatuses[]? | {name,started,ready,resources,restartCount,containerID}],
    conditions:.status.conditions
  }'
```

로컬 감사에서는 fake Kubernetes/RFC6902 기반 leaf 단위 검사 50개와 schema·host-shell probe fixture를 실행했습니다. EKS에서 informer loop·BusyBox를 실행하거나 warmup 시간·cgroup·앱 성능을 측정하지 않았습니다. VPA 1.7에도 alpha CPUStartupBoost가 있지만 trigger는 Pod Ready와 선택적 지속 시간이며 이 StartupProbePassed 계약과 다르고 별도 flag·운영 조건을 가집니다.

#### 기존 EKS 결과 기록 — 출처 검증되지 않음

기존 문서는 EKS 1.36.1·containerd 2.2.3·AL2023·cgroup v2·arm64/Graviton 환경을 주장했습니다. 원본 실행 artifact·출처가 제공되지 않았습니다. 아래 원래 표·log는 **검증되지 않은 기존 보고 결과**로 보존하며 재실행·현재 controller 출력·무중단의 독립적 증거가 아닙니다. MAP 표 두 개는 같은 기존 주장을 반복하며 독립 측정 두 건이 아닙니다.

| 케이스 | annotation | 주입된 resizePolicy | 판정 |
|--------|-----------|-------------------|------|
| with-annotation | 有 | `[{cpu:NotRequired},{memory:RestartContainer}]` | ✅ 주입됨 (webhook 없이) |
| without-annotation | 無 | `[]` (없음) | ✅ 주입 안 됨 (matchCondition 동작) |

```text
RESIZED resize-demo/demo-deploy-xxxxx-aaaaa [ReplicaSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"app","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
RESIZED resize-demo/demo-deploy-xxxxx-bbbbb [ReplicaSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"app","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
RESIZED resize-demo/demo-ds-yyyyy [DaemonSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"app","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
RESIZED resize-demo/demo-sts-0 [StatefulSet] trigger=StartupProbePassed patch={"spec":{"containers":[{"name":"app","resources":{"limits":{"cpu":"50m"},"requests":{"cpu":"50m"}}}]}}
```

| 워크로드 | QoS | CPU (req/lim) | restartCount | containerID |
|----------|-----|---------------|--------------|-------------|
| Deployment (x2) | Guaranteed → **Guaranteed** | 200m → **50m** | 0 → **0** | **동일(IDENTICAL)** |
| DaemonSet | Guaranteed → **Guaranteed** | 200m → **50m** | 0 → **0** | **동일(IDENTICAL)** |
| StatefulSet | Guaranteed → **Guaranteed** | 200m → **50m** | 0 → **0** | **동일(IDENTICAL)** |

| 케이스 | annotation | 주입된 resizePolicy | 판정 |
|--------|-----------|-------------------|------|
| with-annotation | 有 | `[{cpu:NotRequired},{memory:RestartContainer}]` | ✅ 주입됨 (webhook 없이) |
| without-annotation | 無 | `[]` (없음) | ✅ 주입 안 됨 (matchCondition 동작) |

이전 `RESIZED` log는 API PATCH 성공 뒤 출력했습니다. ContainerID·restartCount 유지와 원하는 spec 변경만으로 cgroup 적용·앱 latency·요청 손실 부재를 증명할 수는 없습니다. 같은 Pod UID·시간 범위, kubelet의 실제 resource·generation, 적절한 runtime·앱 관측을 함께 확인해야 합니다. 과거 수치를 새 Kubernetes 버전으로 바꾸거나 새 실측으로 제시하지 않았습니다.

[Kubernetes 1.36 release](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/) · [1.36.2 feature definitions](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go) · [Kubelet authorization](https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/) · [ServiceAccount administration](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/) · [SELinux security context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) · [Released IPVS selection path](https://github.com/kubernetes/kubernetes/blob/v1.36.2/cmd/kube-proxy/app/server_linux.go) · [VPA 1.7.1 features](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/features.md)

---

## 5. 주요 기능 졸업 타임라인

출시된 1.36.2 gate 정의와 공식 제거된 gate 이력을 중심으로 **Kubernetes 1.36까지**의 주요 upstream 이력을 정리합니다. Beta는 첫 beta 릴리스이며 기본 활성화를 의미하지 않습니다. 대시는 향후 일정을 약속하지 않으며 API 제공 여부·runtime/driver 조건·EKS 지원은 별도 확인합니다.

| 기능 | 첫 alpha | 첫 beta | 1.36까지 stable |
|---|---|---|---|
| Sidecar container | 1.28 | 1.29 | 1.33 |
| Container in-place resize | 1.27 | 1.33 | 1.35 |
| Pod scheduling readiness | 1.26 | 1.27 | 1.30 |
| Job success policy | 1.30 | 1.31 | 1.33 |
| Pod-level resource | 1.32 | 1.34 | — |
| ValidatingAdmissionPolicy | 1.26 | 1.28 | 1.30 |
| MutatingAdmissionPolicy | 1.32 | 1.34 | 1.36 |
| 구조화된 인가 | 1.29 | 1.30 | 1.32 |
| AppArmor native 필드 | — | 1.30 | 1.31 |
| User namespace | 1.25 | 1.30 | 1.36 |
| ServiceCIDR/IPAddress | 1.27 | 1.31 | 1.33 |
| Topology-aware hint | 1.21 | 1.23 | 1.33 |
| nftables proxy | 1.29 | 1.31 | 1.33 |
| Service traffic distribution | 1.30 | 1.31 | 1.33 |
| 같은 node/zone 선호 | 1.33 | 1.34 | 1.35 |
| ReadWriteOncePod | 1.22 | 1.27 | 1.29 |
| VolumeAttributesClass | 1.29 | 1.31 | 1.34 |
| PV 마지막 phase 전환 | 1.28 | 1.29 | 1.31 |
| Volume 확장 실패 복구 | 1.23 | 1.32 | 1.34 |
| Gang scheduling | 1.35 | — | — |
| 최소 topology domain | 1.24 | 1.25 | 1.30 |
| DRA core | 1.26 | 1.32 | 1.34 |
| HPA container metric | 1.20 | 1.27 | 1.30 |
| Image volume | 1.31 | 1.33 | 1.36 |
| Node log query | 1.27 | 1.30 | 1.36 |
| KMS v2 | 1.25 | 1.27 | 1.29 |
| Kubelet tracing | 1.25 | 1.27 | 1.34 |
| KYAML | 1.34 | 1.35 | — |

이력 해석 시 구분할 사항:

- AppArmor annotation은 1.4부터 beta였으며 표는 새 native 필드(beta 1.30, GA 1.31)를 다룹니다.
- User namespace는 이전의 제한적/stateless 지원부터 발전했습니다. 출시된 gate 이력은 alpha 1.25·beta 1.30·기본 활성화 1.33·GA 1.36을 기록하며 GA 날짜로 gate 제거를 추론하지 않습니다.
- DRA의 alpha 1.26은 원래 설계의 이력입니다. 이후 structured-parameter 재설계(KEP-4381)는 같은 API가 그대로 발전한 것이 아니며 classic DRA는 1.31에 별도 gate로 남았다가 1.32에서 제거되었습니다. 현재 stable request 구문은 `exactly`를 사용합니다.
- Native gang scheduling은 KEP-4671이며 1.36까지 alpha입니다. KYAML은 KEP-5295이며 표 범위 밖의 upstream 1.37에서 stable이 됩니다. 둘 다 1.36 GA가 아닙니다.
- Beta 기본값은 별도로 바뀝니다. UserNamespacesSupport는 1.33, ImageVolume은 1.35에서 기본 활성화되었고 PodLevelResources의 beta 시작은 1.34입니다.

Gateway API는 별도 버전의 API/CRD 프로젝트입니다. 해당 channel·kind version·conformance를 Kubernetes “alpha 1.18 / GA 1.26”에 대응시키지 않습니다. VPA update mode·Karpenter·CSI driver도 별도 release/support matrix를 따릅니다. Core API 졸업이 해당 component나 모든 예시의 production 준비 상태를 인증하지는 않습니다.

<!-- Parent repair: graduation diagram has stale DRA/Gang and other milestone assertions.
![ValidatingAdmissionPolicy, Sidecar Containers, DRA Core APIs, In-Place Pod Resize, MutatingAdmissionPolicy, Gang Scheduling 여섯 기능이 Alpha·Beta·GA에 도달한 Kubernetes 버전을 GA 졸업 순서대로 비교해서 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-14.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-14.html)
-->

[Released Kubernetes 1.36.2 feature history](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/features/kube_features.go) · [Feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/) · [Removed gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates-removed/) · [KYAML history](https://github.com/kubernetes/enhancements/tree/master/keps/sig-cli/5295-kyaml)

---

## 6. Deprecation 및 제거 사항

### API version·필드·구현·gate를 구분합니다

GA **API version**은 같은 Kubernetes major version에서 제거할 수 없습니다. CLI flag·feature gate·개별 필드·volume 구현과는 다른 규칙입니다. Beta API 제거에는 deprecation 이후 9개월 또는 3회 minor release 중 더 긴 최소 기간이 적용되며 alpha API에는 같은 보장이 없습니다. 기존의 “GA API도 12개월/3회 릴리스 뒤 제거 가능”은 잘못된 설명입니다.

Gate deprecation·제거 규칙도 별개이며 실제 릴리스를 확인해야 합니다. GA 버전 번호에 2를 더해 gate 제거·비활성화를 결정하지 않습니다. 앞의 버전별 설명과 출시된 코드는 기본 활성화·잠금·실제 제거를 구분합니다.

### 주요 API 제거 시점

| API와 kind | Serving 중단 버전 | 현재 대체 API / 주의점 |
|---|---|---|
| `autoscaling/v2beta1` HPA | 1.25 | `autoscaling/v2`; metric schema 확인 |
| `autoscaling/v2beta2` HPA | 1.26 | `autoscaling/v2` |
| `batch/v1beta1` CronJob | 1.25 | `batch/v1` |
| `policy/v1beta1` PDB | 1.25 | `policy/v1`; 빈 selector 의미가 다름 |
| `flowcontrol.apiserver.k8s.io/v1beta2` FlowSchema/PriorityLevelConfiguration | 1.29 | `v1`; concurrency-share 필드·기본값 변경 확인 |
| `flowcontrol.apiserver.k8s.io/v1beta3` FlowSchema/PriorityLevelConfiguration | 1.32 | `v1` |
| `admissionregistration.k8s.io/v1beta1` ValidatingAdmissionPolicy/Binding | 1.34 | `v1`; 같은 group/version의 MutatingAdmissionPolicy와 구분 |
| `resource.k8s.io/v1alpha3` ResourceClaim/Template·DeviceClass·ResourceSlice | 1.34 | 현재는 stable `v1`; 이전 저장 표현은 릴리스별 마이그레이션 필요 |
| `storage.k8s.io/v1beta1` CSIDriver·CSINode·StorageClass·VolumeAttachment | 1.22 | `storage.k8s.io/v1` |
| `storage.k8s.io/v1beta1` CSIStorageCapacity | 1.27 | `storage.k8s.io/v1` |
| Beta Ingress·CRD·admission-webhook configuration API | 1.22 | Stable `v1`; schema·필드 변경도 포함 |

Resource group에는 다른 `v1alpha3` kind가 남아 있으므로 core DRA 네 kind 제거를 group/version 전체 제거로 일반화하지 않습니다. 1.34 changelog는 과거 DRA 저장 표현도 경고합니다. Backup·workload/claim 소유권·지정된 마이그레이션/재생성 절차를 조정하며 claim 전체 삭제나 `apiVersion` 문자열 변경만으로 해결하지 않습니다.

### 1.36 구현에 여전히 구분되어 있는 beta API

출시된 1.36.2 lifecycle metadata와 REST storage는 아래 버전을 구분합니다. 향후 제거 값은 기록된 목표이며 이후 릴리스에서 변경되지 않거나 managed service가 모든 API를 기본 활성화한다는 보장이 아닙니다.

| API와 kind | Metadata의 deprecation | 기록된 제거 목표 |
|---|---|---|
| DRA core `resource.k8s.io/v1beta1` | 1.35 | 1.38 |
| DRA core `resource.k8s.io/v1beta2` | 1.36 | 1.39 |
| VAC `storage.k8s.io/v1beta1` | 1.34 | 1.37 |
| MutatingAdmissionPolicy/Binding `admissionregistration.k8s.io/v1beta1` | 1.37 | 1.40 |

GA 졸업과 동시에 해당 beta API가 제거된 것이 아닙니다. 반대로 과거 alpha 제거 예상일도 이후 실제 changelog에서 구현이 바뀌면 최종 근거가 아닙니다.

추가 정정: KMS v1은 deprecated·기본 비활성화이며 1.31 제거가 아닙니다. `--authorization-mode`는 구조화 인가 설정의 대안으로 남아 있습니다. Iptables proxy mode는 1.34에서 제거되지 않았고 IPVS는 deprecated지만 upstream 1.36.2에 구현이 남아 있습니다. Legacy ServiceAccount Secret 자동 생성 변경은 1.33이 아닌 1.24입니다. 과거 `kubectl --export` 제거를 새 1.35 변화로 제시하지 않습니다. In-tree storage는 일괄 날짜표 대신 해당 plugin·release·CSI migration 상태·volume 식별자·driver 준비 상태를 확인합니다.

### 저장된 manifest와 실제 client 사용을 별도로 조사합니다

GET 응답은 요청한/선호 API 표현으로 변환되어 원래 client가 사용한 version을 숨길 수 있습니다. `kubectl get flowschemas -o json`, API discovery, CRD conversion webhook 목록만으로 deprecated API 사용을 입증하지 못하며 모든 `v1beta1`이 deprecated인 것도 아닙니다. Rendered Git/Helm manifest, 있을 경우 원래 적용 설정, API 사용 metric·audit log, EKS Insights, 대상 버전 검사를 함께 사용합니다. CRD의 served/storage version과 conversion 동작은 별도 확인합니다.

아래 metric은 응답한 API process가 관측한 deprecated 요청을 보여 줄 수 있지만 완전한 과거 요청 수나 모든 API server replica의 수집 범위는 아닙니다. Metric 부재·권한 오류를 정상 결과로 보지 않습니다.

```bash
# Read-only, explicitly selected cluster; metrics access may be restricted.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${EVIDENCE_PARENT:?Existing private directory}"
umask 077
evidence_dir=$(mktemp -d "$EVIDENCE_PARENT/api-usage.XXXXXXXX")
kubectl --context "$KUBE_CONTEXT" --request-timeout=20s get --raw='/metrics' > "$evidence_dir/metrics.prom"
awk '/^apiserver_requested_deprecated_apis/ {print}' "$evidence_dir/metrics.prom"
```

### 제한된 오프라인 lifecycle 검사기

아래 예시는 Python/PyYAML과 소유한 rendered YAML/JSON manifest 디렉터리를 필요로 합니다. 유한한 catalog를 1.36.2 검토 기준으로 고정하고 target 1.29~1.36만 받습니다. 같은 API version의 kind를 구분하고 parse 오류·빈 디렉터리를 거부하며 resource body를 출력하지 않습니다. **완전한 schema·client 사용·runtime 호환성 감사가 아닙니다.** 모든 deprecated API·의미 변경·YAML/schema 문제를 찾지는 못하므로 실제 CRD를 포함한 버전별 schema validator도 사용하고 `notInCatalog`를 검토합니다.

Exit1은 lifecycle 지적, exit2는 입력·parse 문제이며 exit0도 parse된 입력에 알려진 catalog 지적이 없다는 뜻만 가집니다. 실패를 숨기거나 일부 scan을 “호환됨”으로 표시하지 않습니다.

```python
"""Limited offline GVK lifecycle audit, snapshot: Kubernetes 1.36.2.
Requires PyYAML. This is not a schema, runtime or complete client-usage audit.
"""
import argparse
import json
import re
from pathlib import Path

import yaml


CATALOG = {}


def add(api, kinds, deprecated, removed, replacement):
    for kind in kinds.split(","):
        CATALOG[(api, kind)] = (deprecated, removed, replacement)


add("autoscaling/v2beta1", "HorizontalPodAutoscaler", 22, 25, "autoscaling/v2")
add("autoscaling/v2beta2", "HorizontalPodAutoscaler", 23, 26, "autoscaling/v2")
add("batch/v1beta1", "CronJob", 21, 25, "batch/v1")
add("policy/v1beta1", "PodDisruptionBudget", 21, 25, "policy/v1")
add("networking.k8s.io/v1beta1", "Ingress", 19, 22, "networking.k8s.io/v1")
add("extensions/v1beta1", "Ingress", 14, 22, "networking.k8s.io/v1")
add("apiextensions.k8s.io/v1beta1", "CustomResourceDefinition", 16, 22, "apiextensions.k8s.io/v1")
add("admissionregistration.k8s.io/v1beta1", "MutatingWebhookConfiguration,ValidatingWebhookConfiguration", 16, 22, "admissionregistration.k8s.io/v1")
add("admissionregistration.k8s.io/v1beta1", "ValidatingAdmissionPolicy,ValidatingAdmissionPolicyBinding", 31, 34, "admissionregistration.k8s.io/v1")
add("admissionregistration.k8s.io/v1beta1", "MutatingAdmissionPolicy,MutatingAdmissionPolicyBinding", 37, 40, "admissionregistration.k8s.io/v1")
add("flowcontrol.apiserver.k8s.io/v1beta1", "FlowSchema,PriorityLevelConfiguration", 23, 26, "flowcontrol.apiserver.k8s.io/v1")
add("flowcontrol.apiserver.k8s.io/v1beta2", "FlowSchema,PriorityLevelConfiguration", 26, 29, "flowcontrol.apiserver.k8s.io/v1")
add("flowcontrol.apiserver.k8s.io/v1beta3", "FlowSchema,PriorityLevelConfiguration", 29, 32, "flowcontrol.apiserver.k8s.io/v1")
add("storage.k8s.io/v1beta1", "CSIDriver", 19, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "CSINode", 17, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "StorageClass", 19, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "VolumeAttachment", 19, 22, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "CSIStorageCapacity", 24, 27, "storage.k8s.io/v1")
add("storage.k8s.io/v1beta1", "VolumeAttributesClass", 34, 37, "storage.k8s.io/v1")
# Alpha core DRA kinds were actually removed in 1.34, overriding older plans.
add("resource.k8s.io/v1alpha3", "ResourceClaim,ResourceClaimTemplate,DeviceClass,ResourceSlice", 34, 34, "resource.k8s.io/v1")
add("resource.k8s.io/v1beta1", "ResourceClaim,ResourceClaimTemplate,DeviceClass,ResourceSlice", 35, 38, "resource.k8s.io/v1")
add("resource.k8s.io/v1beta2", "ResourceClaim,ResourceClaimTemplate,DeviceClass,ResourceSlice", 36, 39, "resource.k8s.io/v1")


def resources(obj, seen=None):
    seen = set() if seen is None else seen
    if obj is None:
        return
    if not isinstance(obj, dict):
        raise ValueError("expected a resource mapping")
    if id(obj) in seen:
        raise ValueError("recursive resource List")
    if len(seen) >= 32:
        raise ValueError("resource List nesting exceeds32")
    seen.add(id(obj))
    try:
        if obj.get("kind") == "List":
            for item in obj.get("items", []):
                yield from resources(item, seen)
        else:
            yield obj
    finally:
        seen.remove(id(obj))


def audit(directory, target_minor):
    findings, errors, skipped = [], [], 0
    files = sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in {".yaml", ".yml", ".json"})
    if len(files) > 5000:
        raise ValueError("limit exceeded: 5000 rendered files")
    if not files:
        errors.append({"path": str(directory), "errorType": "NoManifestFiles", "line": None})
    for path in files:
        try:
            if path.is_symlink() or path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("symlink or file exceeds16MiB")
            for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
                for obj in resources(document):
                    key = (obj.get("apiVersion"), obj.get("kind"))
                    entry = CATALOG.get(key)
                    if entry is None:
                        skipped += 1
                        continue
                    deprecated, removed, replacement = entry
                    if target_minor < deprecated:
                        continue
                    metadata = obj.get("metadata") or {}
                    if not isinstance(metadata, dict) or any(
                        metadata.get(k) is not None and not isinstance(metadata[k], str)
                        for k in ("name", "namespace")
                    ):
                        raise ValueError("invalid metadata identity fields")
                    findings.append({
                        "path": str(path), "apiVersion": key[0], "kind": key[1],
                        "namespace": metadata.get("namespace"), "name": metadata.get("name"),
                        "state": "removed" if target_minor >= removed else "deprecated",
                        "replacement": replacement,
                    })
        except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as exc:
            # Do not print parser snippets or resource/Secret bodies.
            mark = getattr(exc, "problem_mark", None)
            errors.append({"path": str(path), "errorType": type(exc).__name__,
                           "line": mark.line + 1 if mark is not None else None})
    return {"snapshot": "Kubernetes1.36.2", "files": len(files), "findings": findings,
            "errors": errors, "notInCatalog": skipped,
            "limit": "Selected GVK lifecycle checks only; no matches do not certify compatibility."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--target-version", required=True)
    args = parser.parse_args()
    match = re.fullmatch(r"1\.(\d+)(?:\.\d+)?", args.target_version)
    if not match or not 29 <= int(match[1]) <= 36 or not args.directory.is_dir():
        parser.error("provide a rendered directory and a reviewed target from1.29 through1.36")
    try:
        result = audit(args.directory, int(match[1]))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result["errors"] else 1 if result["findings"] else 0)
```

```bash
# Save the Python example as api-version-audit.py; requires PyYAML.
: "${MANIFEST_DIR:?Directory containing owned rendered manifests}"
python3 api-version-audit.py --directory "$MANIFEST_DIR" --target-version 1.36.0
```

### Pluto·kubent·Helm의 범위

Pluto는 보조 탐지기로 유용하지만 최신 tool/rule이 정확성을 증명하지는 않습니다. 이번 native **Pluto5.24.3** fixture는 제거된 VAP beta API를 놓치고, 잘못된 YAML에도 exit0을 반환했으며, 위 1.36.2 lifecycle/storage 근거와 달리 DRA beta1을 1.36에서 제거된 것으로 표시했습니다. 결과는 공식 근거와 대조할 조사 단서로 취급합니다. 기본 exit2/3/4는 deprecation·removal·대체 API 미제공 지적이며 다른 실패도 조사해야 합니다. `--components k8s`로 무관한 번들 component version 기본값을 조용히 사용하는 일을 피합니다.

```bash
# Advisory only: record the reviewed Pluto version and its rule coverage.
: "${MANIFEST_DIR:?Directory containing owned rendered manifests}"
pluto detect-files --directory "$MANIFEST_DIR" \
  --target-versions k8s=v1.36.0 --components k8s --output json
```

```bash
# Read-only cluster/Helm inspection can require access to release Secrets.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?Owned namespace}"
pluto detect-all-in-cluster --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  --target-versions k8s=v1.36.0 --components k8s --output json
```

```bash
# Inspect names with their namespaces; a Helm release name is not globally unique.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${RELEASE_NAME:?}"
helm list --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" --output json
# If exporting manifests, use a private file: they can contain Secret values.
: "${PRIVATE_MANIFEST_FILE:?Choose a private destination}"
umask 077
helm get manifest --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  "$RELEASE_NAME" > "$PRIVATE_MANIFEST_FILE"
```

Kubent도 원래 manifest를 활용하는 탐지기이며 API server의 모든 사용 이력을 알려 주지는 않습니다. 여기서 확인한 최신 tag는 0.7.3(2024년 8월)이므로 새 target API의 rule 수집 범위를 확인합니다. 문서의 `--context`·`--target-version`·`--exit-error` flag를 확인하고 Helm 수집에는 release Secret/ConfigMap 읽기 권한이 필요합니다. `kubectl convert`는 지원하는 object 표현을 변환하며 deprecated client 사용을 조사하는 도구가 아닙니다. CRD conversion webhook이 있다는 이유만으로 deprecated라고 판단하지 않습니다.

<!-- Parent repair: plugin-removal timeline requires exact release/plugin reconciliation.
![AWS EBS, GCE PD, CephFS/RBD, Azure File/Disk, vSphere 등 인트리 볼륨 플러그인이 CSI로 마이그레이션되어 Deprecated, Removed 단계로 이어지는 일정을 스토리지 드라이버별로 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-15.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-15.html)
-->

[Kubernetes deprecation policy](https://kubernetes.io/docs/reference/deprecation-policy/) · [API migration guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/) · [1.34 changelog](https://github.com/kubernetes/kubernetes/blob/v1.34.0/CHANGELOG/CHANGELOG-1.34.md) · [1.36.2 DRA REST storage](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/registry/resource/rest/storage_resource.go) · [Pluto](https://github.com/FairwindsOps/pluto) · [Kubent](https://github.com/doitintl/kube-no-trouble)

---

## 7. EKS 특화 고려사항

### 릴리스와 기능 제공 여부

EKS는 자체 검증·지원 일정을 따릅니다. 3절의 날짜는 확인한 출시 기록이지 모든 향후 릴리스가 고정 지연 후 나온다는 보장이 아닙니다. Upstream API 성숙도·EKS API 제공 여부·node/runtime 기능은 별개의 질문입니다. EKS 컨트롤 플레인 flag는 AWS가 관리하며 kube-apiserver Pod 편집, kubeadm 설정 적용, node gate 하나 변경으로 조정할 수 없습니다.

EKS FAQ는 GA Kubernetes API 지원, 새 beta API의 기본 비활성화, alpha 기능 미지원을 명시합니다. 기존 beta API와 그 새 버전은 다르게 취급합니다. 모든 beta 필드가 제공되거나 GA 기능이 driver·설정·호환 node 없이 작동한다고 가정하지 말고 해당 EKS release note와 compute 구현을 확인합니다.

### 추정 최소 버전 표 대신 호환성 기록을 조회합니다

기존 `v1.x+` add-on matrix는 EKS build·platform·architecture·compute 호환성을 입증하지 못하고 collector·chart·add-on 버전 체계를 섞었습니다. 먼저 소유 계정·Region·cluster 버전·설치 component를 기록합니다. IRSA role 필드가 null이라고 AWS 권한이 없다는 뜻은 아니며 Pod Identity·provider-managed identity를 사용할 수 있습니다. Auto Mode 내장 component는 일반 설치 add-on 목록에 나타나지 않을 수 있습니다.

```bash
# Read-only inventory in the explicitly selected account/Region/cluster.
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
actual_account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)
test "$actual_account" = "$EXPECTED_ACCOUNT_ID" || { printf '%s\n' 'Account mismatch' >&2; exit 1; }
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --no-cli-pager \
  --query 'cluster.{version:version,platform:platformVersion,compute:computeConfig,upgradePolicy:upgradePolicy}' --output json
aws eks list-addons --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" --no-cli-pager --output json
```

```bash
# Inspect one addon, not a guessed first element or a bare component version.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${ADDON_NAME:?}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --no-cli-pager \
  --query 'addon.{name:addonName,version:addonVersion,status:status,issues:health.issues,role:serviceAccountRoleArn,podIdentityAssociations:podIdentityAssociations}' --output json
```

아래 후보 조회는 각 compatibility 기록 안의 **요청한 Kubernetes 버전**을 매칭합니다. Architecture·compute type·platform version·default 선택·configuration/IAM 조건을 유지합니다. 배열 첫 원소나 문자열 정렬의 최대 버전이 “최신 호환 버전”은 아닙니다. AWS default flag도 해당 compatibility 기록의 값이지 전역 순위가 아닙니다.

```bash
# Read-only candidates; no addon is installed or changed.
set -euo pipefail
: "${AWS_REGION:?}"; : "${TARGET_K8S_VERSION:?For example1.36}"; : "${ADDON_NAME:?}"
aws eks describe-addon-versions --region "$AWS_REGION" --no-cli-pager \
  --kubernetes-version "$TARGET_K8S_VERSION" --addon-name "$ADDON_NAME" --output json |
  jq -e --arg target "$TARGET_K8S_VERSION" --arg name "$ADDON_NAME" '
    [.addons[]? | select(.addonName == $name) | . as $addon |
      .addonVersions[]? as $release | $release.compatibilities[]? |
      select(.clusterVersion == $target) |
      {addon:$addon.addonName,version:$release.addonVersion,
       architecture:$release.architecture,computeTypes:$release.computeTypes,
       requiresConfiguration:$release.requiresConfiguration,requiresIamPermissions:$release.requiresIamPermissions,
       platformVersions:.platformVersions,defaultForThisCompatibility:.defaultVersion}] |
    if length == 0 then error("No matching compatibility record; do not infer support")
    else . end'
```

결과는 배포 결정이 아닌 후보입니다. 대상 platform·node architecture/compute 구성·release note·필수 설정·AWS 권한을 확인합니다. 빈 결과·CLI 실패 시 선택을 중단합니다. 별도 검토한 update 전에 정확한 add-on configuration schema를 읽고 의도한 기존 값을 보존합니다. OVERWRITE 일괄 사용, 임의 과거 버전으로 downgrade, 컨트롤 플레인 update가 모든 add-on을 갱신한다는 가정을 피합니다. 감사에서는 live AWS catalog 대신 fake 응답·현재 CLI model로 명령을 검사했습니다.

### Auto Mode와 혼합 클러스터

Auto Mode는 내장 compute/network/storage component를 관리하지만 node 버전을 항상 `n−1`로 유지하거나 모든 외부 add-on을 자동 관리한다는 뜻은 아닙니다. Workload 제약·disruption 제어로 교체가 늦어질 수 있으므로 실제 update 상태·node 버전·custom NodePool 호환성을 확인합니다. Managed node group·self-managed/Hybrid node·Fargate Pod는 각각의 update·교체 절차를 따릅니다.

현재 Auto Mode node는 CoreDNS를 **node system service**로 실행합니다. 해당 workload를 모두 Auto Mode node로 옮긴 순수 Auto Mode 클러스터는 기존 CoreDNS Deployment를 제거할 수 있습니다. Auto/non-Auto 혼합 클러스터는 non-Auto node를 위해 Deployment를 유지해야 합니다. 일반 CoreDNS/VPC CNI/kube-proxy Pod 부재를 Auto Mode 장애로 단정하지 않으며, 존재 자체도 정상 동작의 증명은 아닙니다.

```bash
# Read-only node inventory; the label is evidence, not an availability check.
set -euo pipefail
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes -o json | jq '[
  .items[] | {name:.metadata.name,kubelet:.status.nodeInfo.kubeletVersion,
             computeType:.metadata.labels["eks.amazonaws.com/compute-type"]}]'
```

새 `metadata.version`을 넣은 eksctl ClusterConfig만으로 upgrade가 실행되지는 않습니다. 검토한 update 절차와 반환된 update ID를 따릅니다. PDB는 가용성 보장이 아니므로 어떤 교체 작업이 이를 준수하고 어떤 scaling·삭제 경로가 다른지 이해합니다. 앱 readiness·storage·rollback 준비도 계획에 포함합니다.

### Extended support 비용의 맥락

확인한 버전 지원 요금 차이는 클러스터 시간당 $0.50입니다. 365일 예시의 추가 요금은 1개 $4,380·5개 $21,900·10개 $43,800·25개 $109,500·50개 $219,000이며 compute·provisioned control-plane tier·network 등은 제외합니다. 월 730시간도 모든 달의 실제 시간이 아닌 계획 가정입니다.

Fleet 수는 계획 기준 하나입니다. 중요한 클러스터 하나가 단순한 여러 클러스터보다 운영 위험이 클 수 있습니다. Standard 종료가 다가오면 계획 우선순위를 높여야지 staging 검증을 생략하거나 최소 검사로 production을 직접 업그레이드할 근거가 되지는 않습니다. 통제된 upgrade와 해당되는 경우 명시적으로 수용한 extended-support 비용을 비교합니다.

<!-- Parent repair: imminent-support-end path must not recommend direct production upgrade with minimal validation.
![Standard Support 종료까지 남은 기간에 따라 계획적 업그레이드, 즉시 업그레이드, 또는 Extended Support 비용 검토 경로로 분기해 최종적으로 프로덕션 업그레이드 또는 Extended 유지로 이어지는 의사결정 흐름을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-16.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-16.html)
-->

[EKS support policy](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) · [DescribeAddonVersions](https://docs.aws.amazon.com/eks/latest/APIReference/API_DescribeAddonVersions.html) · [Auto Mode networking and DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) · [EKS pricing](https://aws.amazon.com/eks/pricing/) · [Reviewed EKS upgrade guide](08-eks-upgrades.md)

---

## 8. 버전 업그레이드 계획

### 한 번의 minor-version 단계에 대한 실행 계획

EKS는 한 번에 한 minor version씩 업그레이드합니다. 확인한 release/support 일정·대상별 호환성 기록·현재 EKS upgrade 안내를 사용하며 upstream 최신 tag만으로 자격을 추론하지 않습니다. 기존의 준비 1~2주·실행 1~2일은 계획 예시이지 실측 소요 시간이나 기한이 아닙니다.

1. 소유 계정·Region·cluster, 컨트롤 플레인/node 버전, compute mode, add-on build, API 사용, operator·workload 소유자를 기록합니다. 다음 컨트롤 플레인 upgrade 전에 node를 안전한 현재 버전으로 맞춥니다. 지원 skew는 호환 범위이지 node를 3개 minor 뒤에 유지하라는 권고나 모든 API 강제 조건에 대한 보편적 주장이 아닙니다.
2. 대상 릴리스 변경, deprecated/removed API·저장 version 마이그레이션, runtime·OS·AMI, CRD·admission policy를 검토합니다. 도구 exit0·변환된 GET 응답·GA 표기가 전체 호환성 검사는 아닙니다.
3. 앱 상태·Kubernetes 설정을 적절히 backup하고 복원을 검증합니다. EKS의 etcd는 AWS가 관리하므로 고객이 backup 일정을 직접 조회하거나 소유한 컨트롤 플레인처럼 etcd snapshot 명령을 실행할 수 없습니다. Git은 DB·PVC backup을 대체하지 않습니다.
4. 대표성 있는 비프로덕션에서 실제 버전 단계와 component 순서를 연습합니다. 앱 readiness·network/DNS·storage·autoscaling·identity·observability를 확인하고 production 전에 rollback·data recovery 기준을 정합니다.
5. 승인된 컨트롤 플레인 update의 반환된 update ID를 성공한 terminal 상태까지 추적합니다. Node·해당 component는 문서화된 순서를 따릅니다. 일부 호환성·마이그레이션 작업은 컨트롤 플레인 이전에 필요하며 모든 버전·compute mode에 공통인 “kube-proxy → CoreDNS → VPC CNI → CSI” 순서는 없습니다.
6. 각 단계 후 고객이 보는 동작·replica readiness·API/update 상태·component health를 검증합니다. Pod의 Running만으로 readiness를 판단하지 말고 근거를 보존하며 runbook을 갱신합니다.

검토 시점 EKS update 문서는 특정 **upgrade** insight 문제에 `--force`를 요구하는 enforcement가 일시 rollback되었다고 명시합니다. Rollback-readiness 검사와는 별개이며 insight는 계속 계획에 필요합니다. 강제 조건 관련 안내가 호환성 문제를 무시할 근거는 아닙니다.

### 기능 검사와 compute 소유권

제거된 gate 이름이나 지원되지 않는 `managedNodeGroups[].kubelet.featureGates` 구조를 eksctl에 복사하지 않습니다. [클러스터 생성 안내](02-eks-cluster-creation.md)의 현재 schema와 node OS·provisioner가 지원하는 bootstrap 경로를 사용합니다. Managed EKS 컨트롤 플레인 flag는 AWS가 관리합니다. 호환 client를 사용하고 오프라인 schema·server-side dry-run·실제 runtime 검사를 구분합니다.

Auto Mode는 node 교체를 관리하지만 workload readiness·disruption 제약으로 지연될 수 있습니다. 혼합 클러스터는 non-Auto DNS/add-on 조건을 유지합니다. Managed node group rolling update와 desired/min/max scaling은 다른 작업이며 PDB가 scaling·직접 삭제·모든 복구 경로를 보편적으로 보호하지는 않습니다. Fargate·Hybrid Nodes는 각각의 수명주기 절차가 필요합니다.

### EKS native rollback과 복구 대안

버전 rollback은 실제 EKS 기능입니다. **In-place upgrade 완료 후** 7일 안에 시작하고 바로 이전 minor version만 대상으로 하며 지원 version·cluster 자격 조건을 만족해야 합니다. 현재 버전으로 생성된 cluster, 이후 추가 upgrade, 기간 만료, 호환되지 않는 EKS 기능 등은 rollback을 막을 수 있습니다. Extended 종료로 자동 upgrade된 경우도 대상이 아니며 extended-support version으로 돌아가면 upgrade policy·요금도 고려합니다.

운영자가 rollback을 시작하면 Auto Mode가 node를 먼저 되돌린 뒤 컨트롤 플레인을 처리합니다. Managed node group은 별도 UpdateNodegroupVersion rollback을 먼저 수행하고 self-managed/Hybrid node도 각각 준비합니다. Fargate worker version은 in-place rollback할 수 없어 공식 절차의 컨트롤 플레인 rollback 전후 계획된 제거·재배포 조정이 필요합니다. Force로 kubelet skew 검사를 우회한 상태를 지원 구성으로 보거나 live Fargate workload를 일괄 삭제하지 않습니다.

`--force`는 ERROR/WARNING/UNKNOWN rollback insight를 우회할 수 있지만 자격·사전 조건 검증이나 Auto Mode disruption 제어는 우회하지 않습니다. 안전한 기본값이 아닙니다. 정확한 update 상태 추적과 Auto Mode phase·timeout·취소 제약을 포함한 [EKS 업그레이드](08-eks-upgrades.md) 절차를 따릅니다. 컨트롤 플레인 rollback은 앱·DB rollback이 아니며 EKS는 모든 앱을 과거 상태로 복원하는 대신 etcd/customer data를 보존합니다.

| 계층 | 복구 계획 |
|---|---|
| 컨트롤 플레인 | 자격을 만족하는 native rollback 또는 불가능할 때 준비된 병렬 cluster 복구 |
| Node | 호환 version·통제된 교체/drain. Taint 추가만으로 기존 Pod·traffic이 이동하지 않음 |
| Workload | 검토한 GitOps/Helm revision rollback과 앱·data 호환성 확인 |
| Add-on | 정확한 호환 build·설정/IAM·지원 downgrade 검토. OVERWRITE 일괄 적용 금지 |
| 영속 data | Cluster version과 별개인 검증된 backup·앱 일관성 복구 |

### 기존 Terraform 프로젝트에서의 upgrade 수정

아래는 **기존 state 관리 resource의 attribute 조각**이며 독립적인 Terraform 배포가 아닙니다. 프로젝트의 IAM·network·access·encryption·launch template·scaling 설정을 유지합니다. 실제 inventory로 검토한 변수를 정의하고 plan을 확인합니다. 최소 resource 정의로 덮으면 설정을 초기화하거나 다른 cluster를 만들 수 있습니다.

기존 cluster resource에서 한 minor 단계의 target과 support policy를 의도적으로 선택합니다. STANDARD는 standard 종료 후 자동 upgrade될 수 있고 EXTENDED는 이후 유료 지원 기간을 수용합니다.

```hcl
# Edit these arguments inside the existing aws_eks_cluster.main resource.
version = var.reviewed_target_version

upgrade_policy {
  support_type = var.reviewed_support_type
}
```

완전한 managed node-group resource에는 `node_role_arn`·`subnet_ids`·`scaling_config`가 필요하며 기존 예시는 앞 두 항목을 빠뜨렸습니다. 기존 값을 유지합니다. 이전의 desired3/min2/max10과 update budget 33%는 예시 입력이지 upgrade 기본값·가용성 보장이 아닙니다.

```hcl
# Relevant arguments inside the existing aws_eks_node_group.main resource.
# Retain the rest of the existing resource, including its scaling_config.
node_role_arn = var.existing_node_role_arn
subnet_ids    = var.existing_node_subnet_ids
version       = aws_eks_cluster.main.version

update_config {
  max_unavailable_percentage = 33
}
```

기존 add-on마다 검토한 EKS build와 명시적인 update conflict policy를 사용합니다. PRESERVE는 update 옵션이며 CreateAddon conflict 옵션이 아닙니다. Configuration schema·identity·rollback 검토를 대신하지 않습니다.

```hcl
# Edit one already-managed aws_eks_addon resource after compatibility review.
addon_version               = var.reviewed_addon_version
resolve_conflicts_on_update = "PRESERVE"
```

그림의 단계 기간은 추정이며 component 순서는 대상 release·compute mode의 절차를 따라야 합니다.

![EKS 버전 업그레이드가 사전 준비, 비프로덕션 테스트, 프로덕션 업그레이드, 검증 및 안정화의 4단계를 순서대로 거치며 각 단계의 세부 작업을 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-17.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-17.html)

[EKS update procedure](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [EKS rollback prerequisites and sequencing](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html) · [Terraform EKS node-group reference](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group) · [Terraform EKS add-on reference](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon)

---

## 9. 향후 전망

### 출시된 upstream 변화와 EKS 제공 여부를 구분합니다

2026년 9월 12일 기준 upstream Kubernetes **1.37.0은 이미 8월 26일 출시**되었습니다. 향후 1.37 약속이 아니며 upstream 출시로 EKS 제공 여부를 추론하지 않습니다. EKS 계획에는 3절의 확인된 일정을 사용합니다. 본문 예시는 주로 1.36.2로 검사했으며 조용히 1.37로 일괄 변경하지 않았습니다.

| 확인한 upstream 1.37 항목 | 해석 |
|---|---|
| KYAML | Stable kubectl 출력 형식이며 새 API server YAML validator가 아님 |
| GenericWorkload | Beta, 기본 비활성화. 별도 GangScheduling gate 변경이 native group scheduling의 GA를 뜻하지 않음 |
| DRADeviceTaints·DRAResourceClaimDeviceStatus | Stable로 승격. Driver·reporting 조건은 계속 필요 |
| PodLevelResources·Pod-level in-place resize | 출시된 gate 이력에서도 beta이며 기존 예상 GA가 아님 |
| DRAPartitionableDevices | 여전히 beta. 모든 GPU 공유 구현을 보장하지 않음 |

검증되지 않은 “다음 버전 예정” 대신 출시 코드·changelog·해당 KEP를 확인합니다. Stable 기능도 gate 기본값/잠금·API/driver 제공 여부가 다를 수 있습니다.

### 생태계 방향은 Kubernetes 릴리스 확약이 아닙니다

DRA driver·device sharing·topology-aware 배치·batch 조정은 계속 발전합니다. GPU time-slicing/MIG/RDMA 동작은 core API version만이 아니라 실제 hardware·driver에 달려 있습니다. Supply-chain 서명/검증·confidential container·GitOps·platform engineering·OpenTelemetry·Wasm은 별도 프로젝트와 릴리스 정책을 가진 생태계 연동 주제이며 Kubernetes에 자동 내장되거나 특정 미래 연도에 모두 제공된다는 보장이 아닙니다.

지원 기한·호환성·사업 위험에 맞는 반복 upgrade/연습 주기를 유지합니다. 분기별 일정과 upstream의 약 4개월 주기는 서로 다릅니다. 적절한 standard-supported EKS 버전은 추가 버전 요금을 피할 수 있지만 `최신−1`이라는 보편 규칙이 앱 검증을 대신하거나 모든 GA 기능을 즉시 무위험하게 도입해야 한다는 뜻은 아닙니다.

![CNCF 트렌드를 중심으로 AI/ML 네이티브, 플랫폼 엔지니어링, 보안 강화, eBPF 확산, Gateway API, 서버리스/Edge 여섯 갈래의 기술 흐름이 뻗어나가는 구조를 보여준다.](../.gitbook/assets/ko-eks-12-kubernetes-version-roadmap-18.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-12-kubernetes-version-roadmap-18.html)

### 과거 계획 템플릿 — 현재 배포 권고가 아님

이전 한글 문서의 예시 inventory와 계획 월을 보존합니다. Version·수량·월 값은 과거 예시 입력이지 실제 발견한 fleet·수행한 upgrade·검증된 component 조합이 아닙니다. 특히 이전 Istio/Argo CD/chart 버전을 새 Kubernetes와 호환된다고 취급하지 않습니다. 새 계획에서는 실제 inventory와 현재 호환성 근거로 바꿉니다. 아래 검토 항목은 재실행을 지어내지 않고 기존의 nftables 자동 전환·DRA CRD·KYAML 가정을 바로잡았습니다.

```yaml
historical_planning_example:
  provenance: Illustrative prior chapter inputs; no executed upgrade or verified component
    compatibility.
  starting_state:
    cluster_version: '1.33'
    node_count: 50
    workload_count: 200
    component_versions:
    - name: istio
      version: '1.22'
    - name: argocd
      version: '2.11'
    - name: prometheus-stack
      version: '60.0'
  target_version: '1.36'
  upgrade_path:
  - '1.33'
  - '1.34'
  - '1.35'
  - '1.36'
  phases:
  - target: '1.34'
    historical_planned_month: 2025-11
    review:
    - DRA API/driver and VAC compatibility
    - Proxy backend migration only if deliberately selected; not automatic
  - target: '1.35'
    historical_planned_month: 2026-03
    review:
    - In-place resize and the actual VPA release/mode
    - KYAML is a client output format, not a server parsing migration
  - target: '1.36'
    historical_planned_month: 2026-07
    review:
    - Pod-level resource policies and supported compute/runtime
    - Gang scheduling is still alpha in1.36; not a GA EKS prerequisite
```

---

## 10. 참고 자료

과거 요약 표나 도구의 번들 가정보다 릴리스별 소스·vendor API 문서를 우선합니다. 실제 변경 시에는 대상 version·provider·component release·기능 설정을 다시 확인합니다.

- [Kubernetes releases](https://kubernetes.io/releases/)
- [Patch support policy](https://kubernetes.io/releases/patch-releases/)
- [Feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
- [Removed feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates-removed/)
- [API deprecation policy](https://kubernetes.io/docs/reference/deprecation-policy/)
- [API migration guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- [Kubernetes 1.36.2 source](https://github.com/kubernetes/kubernetes/tree/v1.36.2)
- [Kubernetes 1.37 changelog](https://github.com/kubernetes/kubernetes/blob/v1.37.0/CHANGELOG/CHANGELOG-1.37.md)
- [EKS support calendar](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS version notes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)
- [EKS upgrades](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [EKS add-on compatibility API](https://docs.aws.amazon.com/eks/latest/APIReference/API_DescribeAddonVersions.html)
- [EKS Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS best practices](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [VPA 1.7.1 features](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/features.md)
- [Pluto](https://github.com/FairwindsOps/pluto)
- [Kubent](https://github.com/doitintl/kube-no-trouble)

### 공식 릴리스 발표

- [Kubernetes 1.29](https://kubernetes.io/blog/2023/12/13/kubernetes-v1-29-release/)
- [Kubernetes 1.30](https://kubernetes.io/blog/2024/04/17/kubernetes-v1-30-release/)
- [Kubernetes 1.31](https://kubernetes.io/blog/2024/08/13/kubernetes-v1-31-release/)
- [Kubernetes 1.32](https://kubernetes.io/blog/2024/12/11/kubernetes-v1-32-release/)
- [Kubernetes 1.33](https://kubernetes.io/blog/2025/04/23/kubernetes-v1-33-release/)
- [Kubernetes 1.34](https://kubernetes.io/blog/2025/08/27/kubernetes-v1-34-release/)
- [Kubernetes 1.35](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/)
- [Kubernetes 1.36](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/)

## 퀴즈와 다음 단계

- [버전별 기능과 로드맵 퀴즈](../quizzes/eks/12-kubernetes-version-roadmap-quiz.md)
- [EKS 업그레이드](08-eks-upgrades.md)
- [EKS 고급 디버깅](11-eks-advanced-debugging.md)
- [EKS 클러스터 생성 실습](../labs/eks/01-eks-cluster-creation-lab.md)
- [EKS Auto Mode](../eks-auto-mode/README.md)

< [이전: EKS 고급 디버깅](11-eks-advanced-debugging.md) | [목차](../README.md) >
