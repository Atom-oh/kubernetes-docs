# Kubernetes 버전별 신규 기능과 로드맵

> **지원 버전**: Kubernetes 1.29 - 1.36
> **마지막 업데이트**: 2026년 6월 28일

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

```mermaid
mindmap
  root((Kubernetes<br>버전 관리))
    릴리스 사이클
      연 3회 릴리스
      alpha/beta/GA 모델
      Feature Gate
      SIG 거버넌스
    버전별 기능
      1.29 Mandala
      1.30 Uwubernetes
      1.31 Elli
      1.32 Penelope
      1.33 Octarine
      1.34 Of Wind & Will
      1.35 Timbernetes
      1.36 ハル Haru
    EKS 지원
      Standard Support
      Extended Support
      매니지드 애드온
      Auto Mode
    업그레이드 전략
      호환성 검증
      Feature Gate 테스트
      롤백 계획
      애드온 정렬
```

---

## 2. Kubernetes 릴리스 사이클

### 2.1 릴리스 개요

Kubernetes는 매년 3회 메이저 릴리스를 발행합니다. 각 릴리스 주기는 약 15주(약 4개월)이며, 체계적인 개발-테스트-릴리스 파이프라인을 통해 진행됩니다.

```mermaid
gantt
    title Kubernetes 연간 릴리스 사이클 (예시)
    dateFormat  YYYY-MM
    axisFormat  %Y-%m

    section 릴리스 1
    Enhancement Freeze     :a1, 2025-01, 1M
    Code Freeze            :a2, 2025-02, 1M
    테스트 및 안정화          :a3, 2025-03, 1M
    릴리스                  :milestone, 2025-04, 0d

    section 릴리스 2
    Enhancement Freeze     :b1, 2025-05, 1M
    Code Freeze            :b2, 2025-06, 1M
    테스트 및 안정화          :b3, 2025-07, 1M
    릴리스                  :milestone, 2025-08, 0d

    section 릴리스 3
    Enhancement Freeze     :c1, 2025-09, 1M
    Code Freeze            :c2, 2025-10, 1M
    테스트 및 안정화          :c3, 2025-11, 1M
    릴리스                  :milestone, 2025-12, 0d
```

### 2.2 릴리스 주기 상세

각 릴리스 주기는 다음 단계를 거칩니다.

| 단계 | 기간 | 설명 |
|------|------|------|
| **Enhancements Freeze** | Week 5~6 | 해당 릴리스에 포함될 Enhancement 확정. KEP(Kubernetes Enhancement Proposal)가 승인 상태여야 함 |
| **Code Freeze** | Week 10~11 | 새로운 기능 코드 병합 중단. 버그 수정만 허용 |
| **Test Freeze** | Week 12 | 테스트 코드 변경 중단 |
| **Release Candidate** | Week 13~14 | RC 빌드 생성 및 최종 검증 |
| **Release** | Week 15 | 공식 릴리스 |

### 2.3 Alpha / Beta / GA 성숙도 모델

Kubernetes의 모든 새 기능은 단계적 성숙도 모델을 통해 진행됩니다. 이 모델은 안정성과 하위 호환성에 대한 보증 수준을 나타냅니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                     기능 성숙도 모델                               │
├──────────┬──────────────┬──────────────┬───────────────────────┤
│ 단계      │ Feature Gate │ 기본 활성화     │ 보증                   │
├──────────┼──────────────┼──────────────┼───────────────────────┤
│ Alpha    │ 비활성 (Off)   │ ✗            │ 없음, 언제든 변경/제거 가능 │
│ Beta     │ 활성 (On)     │ ✓            │ 최소 1 릴리스 유지       │
│ GA       │ 잠금 (Locked) │ ✓ (항상)      │ 하위 호환성 보장         │
├──────────┴──────────────┴──────────────┴───────────────────────┤
│ GA 후 2 릴리스: Feature Gate 제거 (코드에서 삭제)                     │
└─────────────────────────────────────────────────────────────────┘
```

#### Alpha 단계

- Feature Gate를 명시적으로 활성화해야 사용 가능
- API 스키마나 동작이 예고 없이 변경될 수 있음
- 프로덕션 환경에서 사용 비권장
- 주로 개발/테스트 클러스터에서 검증 목적으로 활용

```yaml
# Feature Gate 활성화 예시 (kube-apiserver)
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - command:
    - kube-apiserver
    - --feature-gates=InPlacePodVerticalScaling=true
    # Alpha 기능을 명시적으로 활성화
```

#### Beta 단계

- 기본적으로 활성화되어 있음
- API가 안정화되어 있으나 세부 사항이 변경될 수 있음
- 최소 1개 릴리스 동안 유지 보장
- 프로덕션 환경에서 신중하게 사용 가능 (단, 변경 가능성 인지 필요)

#### GA (Generally Available) 단계

- Feature Gate가 잠금 상태 (항상 활성화)
- API의 하위 호환성이 보장됨
- Kubernetes API Deprecation 정책에 따라 관리
- 프로덕션 환경에서 안심하고 사용 가능

### 2.4 Feature Gate 관리

Feature Gate는 Kubernetes에서 기능의 활성화/비활성화를 제어하는 핵심 메커니즘입니다.

```bash
# 현재 클러스터에서 활성화된 Feature Gate 확인
kubectl get --raw /metrics | grep kubernetes_feature_enabled

# 특정 Feature Gate 상태 확인
kubectl get --raw /metrics | grep "kubernetes_feature_enabled" | grep "InPlacePodVerticalScaling"

# kube-apiserver의 Feature Gate 설정 확인
kubectl -n kube-system get pod kube-apiserver-<node> -o yaml | grep feature-gates
```

> **참고**: EKS에서는 컨트롤 플레인의 Feature Gate를 직접 설정할 수 없습니다. AWS가 각 EKS 버전에 적합한 Feature Gate를 관리합니다. Beta 이상의 기본 활성화 Feature Gate만 사용할 수 있으며, Alpha 기능은 일반적으로 사용할 수 없습니다.

### 2.5 SIG (Special Interest Group) 거버넌스

Kubernetes의 개발은 약 30개 이상의 SIG(Special Interest Group)에 의해 분산적으로 이루어집니다. 각 SIG는 특정 영역의 기능 개발, 유지보수, 문서화를 담당합니다.

| SIG | 담당 영역 | 주요 기능 (1.29-1.36) |
|-----|----------|----------------------|
| SIG Node | 노드, 컨테이너 런타임, Pod 라이프사이클 | Sidecar Containers, In-Place Pod Resize |
| SIG Network | 네트워킹, Service, DNS | ServiceCIDR, Topology Aware Routing |
| SIG Auth | 인증, 인가, 보안 정책 | StructuredAuthorizationConfiguration, ValidatingAdmissionPolicy |
| SIG Storage | 스토리지, CSI, 볼륨 | VolumeAttributesClass, ReadWriteOncePod |
| SIG Scheduling | 스케줄링, 리소스 관리 | Pod Scheduling Readiness, Gang Scheduling |
| SIG Apps | 워크로드 API (Deployment, StatefulSet 등) | Job Success Policy |
| SIG API Machinery | API 서버, API 확장, CRD | KYAML, CEL Admission |
| SIG Instrumentation | 메트릭, 로깅, 트레이싱 | Component Health SLI |
| SIG Autoscaling | HPA, VPA, Cluster Autoscaler | HPA Container Resource Metrics |
| SIG Cloud Provider | 클라우드 프로바이더 통합 | External Cloud Provider (Out-of-tree) |

### 2.6 KEP (Kubernetes Enhancement Proposal) 프로세스

모든 주요 기능 변경은 KEP를 통해 제안, 검토, 승인됩니다.

```mermaid
flowchart LR
    A[아이디어] --> B[KEP 초안 작성]
    B --> C[SIG 리뷰]
    C --> D{승인?}
    D -->|Yes| E[Implementable]
    D -->|No| F[수정 요청]
    F --> C
    E --> G[Alpha 구현]
    G --> H[Beta 승격]
    H --> I[GA 졸업]
    I --> J[Feature Gate 제거]
    
    style E fill:#4CAF50,color:white
    style G fill:#FFC107,color:black
    style H fill:#2196F3,color:white
    style I fill:#9C27B0,color:white
```

KEP 문서에는 다음이 포함됩니다:

- **동기(Motivation)**: 왜 이 기능이 필요한가
- **제안(Proposal)**: 기능의 설계와 구현 방법
- **졸업 기준(Graduation Criteria)**: alpha → beta → GA 각 단계의 요구사항
- **테스트 계획(Test Plan)**: 기능 검증을 위한 테스트 전략
- **프로덕션 준비(Production Readiness Review)**: 운영 환경 적합성 검토

---

## 3. EKS 버전 지원 매트릭스

### 3.1 EKS 버전 지원 정책 개요

Amazon EKS는 Kubernetes 업스트림 릴리스를 기반으로 매니지드 환경을 제공하며, 자체적인 버전 지원 정책을 운영합니다.

```mermaid
flowchart TB
    subgraph support["EKS 버전 지원 체계"]
        direction TB
        
        subgraph standard["Standard Support (14개월)"]
            S1["$0.10/cluster/hour"]
            S2["정규 보안 패치"]
            S3["매니지드 애드온 업데이트"]
            S4["AWS 기술 지원"]
        end
        
        subgraph extended["Extended Support (추가 12개월)"]
            E1["$0.60/cluster/hour"]
            E2["중요 보안 패치만"]
            E3["제한된 애드온 업데이트"]
            E4["업그레이드 유예 기간"]
        end
        
        standard --> extended
    end
    
    subgraph eol["지원 종료 (End of Life)"]
        EOL1["자동 업그레이드 시작"]
        EOL2["60일 사전 알림"]
        EOL3["컨트롤 플레인 먼저"]
    end
    
    extended --> eol
    
    classDef stdClass fill:#4CAF50,stroke:#333,color:white;
    classDef extClass fill:#FF9800,stroke:#333,color:white;
    classDef eolClass fill:#F44336,stroke:#333,color:white;
    
    class S1,S2,S3,S4 stdClass;
    class E1,E2,E3,E4 extClass;
    class EOL1,EOL2,EOL3 eolClass;
```

### 3.2 현재 지원 버전 상태 (2026년 6월 기준)

| Kubernetes 버전 | EKS 릴리스 날짜 | Standard Support 종료 | Extended Support 종료 | 현재 상태 |
|:---:|:---:|:---:|:---:|:---:|
| 1.29 | 2024년 3월 | 2025년 3월 | 2026년 3월 | **Extended 종료** |
| 1.30 | 2024년 7월 | 2025년 7월 | 2026년 7월 | **Extended Support** |
| 1.31 | 2024년 10월 | 2025년 10월 | 2026년 10월 | **Extended Support** |
| 1.32 | 2025년 1월 | 2026년 1월 | 2027년 1월 | **Extended Support** |
| 1.33 | 2025년 6월 | 2026년 8월 | 2027년 8월 | **Standard Support** |
| 1.34 | 2025년 10월 | 2026년 12월 | 2027년 12월 | **Standard Support** |
| 1.35 | 2026년 2월 | 2027년 4월 | 2028년 4월 | **Standard Support** |
| 1.36 | 2026년 6월 | 2027년 8월 | 2028년 8월 | **Standard Support (최신)** |

> **참고**: 위 날짜는 대략적인 예상이며, 실제 날짜는 AWS 공식 문서를 확인하세요. EKS 릴리스는 upstream Kubernetes 릴리스 후 통상 2~8주 후에 이루어집니다.

### 3.3 버전 라이프사이클 다이어그램

```mermaid
gantt
    title EKS 버전 라이프사이클 (2024-2028)
    dateFormat  YYYY-MM
    axisFormat  %Y-%m

    section 1.29
    Standard Support    :active, v29s, 2024-03, 2025-03
    Extended Support    :crit,   v29e, 2025-03, 2026-03
    
    section 1.30
    Standard Support    :active, v30s, 2024-07, 2025-07
    Extended Support    :crit,   v30e, 2025-07, 2026-07

    section 1.31
    Standard Support    :active, v31s, 2024-10, 2025-10
    Extended Support    :crit,   v31e, 2025-10, 2026-10

    section 1.32
    Standard Support    :active, v32s, 2025-01, 2026-01
    Extended Support    :crit,   v32e, 2026-01, 2027-01

    section 1.33
    Standard Support    :active, v33s, 2025-06, 2026-08
    Extended Support    :crit,   v33e, 2026-08, 2027-08

    section 1.34
    Standard Support    :active, v34s, 2025-10, 2026-12
    Extended Support    :crit,   v34e, 2026-12, 2027-12

    section 1.35
    Standard Support    :active, v35s, 2026-02, 2027-04
    Extended Support    :crit,   v35e, 2027-04, 2028-04

    section 1.36
    Standard Support    :active, v36s, 2026-06, 2027-08
    Extended Support    :crit,   v36e, 2027-08, 2028-08
```

### 3.4 Standard Support vs Extended Support 비용 비교

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EKS 버전 지원 비용 구조                                 │
├───────────────────┬────────────────────┬────────────────────────────────┤
│                   │ Standard Support   │ Extended Support               │
├───────────────────┼────────────────────┼────────────────────────────────┤
│ 시간당 비용         │ $0.10/cluster      │ $0.60/cluster                  │
│ 월간 비용 (1클러스터)│ ~$73               │ ~$438                          │
│ 연간 비용 (1클러스터)│ ~$876              │ ~$5,256                        │
│ 월간 비용 (10클러스터)│ ~$730             │ ~$4,380                        │
│ 연간 비용 (10클러스터)│ ~$8,760           │ ~$52,560                       │
├───────────────────┼────────────────────┼────────────────────────────────┤
│ 비용 대비 6배       │ 기본               │ Standard 대비 6배 비용           │
├───────────────────┴────────────────────┴────────────────────────────────┤
│ 권장: Extended Support에 진입하기 전에 업그레이드 계획 수립                    │
│       10개 클러스터 운영 시 Extended 1년 = 추가 $43,800                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.5 EOL(End of Life) 시 자동 업그레이드 동작

Extended Support 기간이 종료되면 EKS는 자동으로 클러스터를 다음 지원 버전으로 업그레이드합니다.

```mermaid
sequenceDiagram
    participant AWS as AWS EKS
    participant Admin as 클러스터 관리자
    participant CP as 컨트롤 플레인
    participant NG as 노드 그룹
    
    AWS->>Admin: 60일 전 이메일 알림<br>"Extended Support 종료 예정"
    AWS->>Admin: 30일 전 추가 알림
    AWS->>Admin: 7일 전 최종 경고
    
    Note over AWS,NG: Extended Support 종료일 도달
    
    AWS->>CP: 컨트롤 플레인 자동 업그레이드 시작
    CP-->>AWS: 업그레이드 완료
    
    Note over NG: ⚠️ 노드 그룹은 자동 업그레이드되지 않음
    Note over NG: 관리자가 수동으로 업데이트 필요
    
    AWS->>Admin: 컨트롤 플레인 업그레이드 완료 알림
    Admin->>NG: 노드 그룹 수동 업그레이드
```

**자동 업그레이드의 위험성:**

- 컨트롤 플레인만 자동 업그레이드되며, 노드 그룹은 그대로 유지됨
- 버전 스큐(skew) 정책에 따라 노드는 컨트롤 플레인보다 최대 3개 마이너 버전 낮을 수 있음
- Deprecated API를 사용하는 매니페스트가 갑자기 동작하지 않을 수 있음
- 애드온 호환성 문제 발생 가능
- **권장**: 자동 업그레이드에 의존하지 말고, 반드시 사전에 계획된 업그레이드를 수행

---

## 4. 버전별 주요 기능 가이드

이 섹션은 Kubernetes 1.29부터 1.36까지 각 버전의 핵심 Enhancement를 상세히 다룹니다. 각 기능에 대해 실무적 관점에서의 영향과 활용법을 함께 설명합니다.

### 4.1 Kubernetes 1.29 "Mandala" (2023년 12월)

Kubernetes 1.29는 코드네임 "Mandala"(Universe)로, 49개의 Enhancement를 포함합니다. 이 중 11개가 Stable(GA), 19개가 Beta, 19개가 Alpha로 졸업했습니다.

```mermaid
pie title "Kubernetes 1.29 Enhancement 분포"
    "Stable (GA)" : 11
    "Beta" : 19
    "Alpha" : 19
```

#### 핵심 GA 기능

##### KMS v2 GA (KEP-3299)

Kubernetes Secrets의 저장 시 암호화(Encryption at Rest)를 위한 KMS(Key Management Service) v2 프로바이더가 GA로 졸업했습니다.

**변경 사항:**
- KMS v2 API가 안정화되어 프로덕션 사용에 적합
- v1 대비 성능 향상: DEK(Data Encryption Key) 캐싱으로 KMS 호출 횟수 대폭 감소
- Health check 및 Status API 추가
- v1 API는 Deprecated (1.31에서 제거 예정)

```yaml
# KMS v2 암호화 설정 예시
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - kms:
          apiVersion: v2       # v2 사용
          name: aws-encryption-provider
          endpoint: unix:///var/run/kmsplugin/socket.sock
          cachesize: 1000       # DEK 캐시 크기
          timeout: 3s
      - identity: {}           # 암호화 실패 시 평문 폴백
```

**EKS 영향:** EKS는 기본적으로 AWS KMS를 사용한 envelope encryption을 지원하며, EKS 1.29부터 KMS v2 프로바이더가 기본으로 활성화됩니다.

##### ReadWriteOncePod PV Access Mode GA (KEP-2485)

PersistentVolume에 대해 단일 Pod 전용 접근 모드(ReadWriteOncePod)가 GA로 졸업했습니다.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-pvc
spec:
  accessModes:
    - ReadWriteOncePod    # 단일 Pod에서만 읽기/쓰기 가능
  resources:
    requests:
      storage: 100Gi
  storageClassName: gp3-csi
```

**기존 ReadWriteOnce와의 차이:**

| 접근 모드 | 범위 | 사용 사례 |
|----------|------|----------|
| ReadWriteOnce (RWO) | 단일 노드의 여러 Pod | 일반적인 단일 쓰기 워크로드 |
| ReadWriteOncePod (RWOP) | 단일 Pod 전용 | 데이터베이스, 리더 선출이 필요한 워크로드 |

**실무 활용:** 데이터베이스처럼 반드시 단일 인스턴스만 볼륨에 접근해야 하는 워크로드에서 RWOP를 사용하면, 동일 노드 내 다른 Pod의 볼륨 접근을 커널 레벨에서 차단할 수 있습니다.

##### Sidecar Containers Beta 도입 (KEP-753)

Native Sidecar Containers가 beta로 처음 도입되었습니다. `restartPolicy: Always`를 가진 init container로 정의하며, Pod의 전체 수명 동안 실행됩니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
spec:
  initContainers:
    - name: log-collector
      image: fluent-bit:latest
      restartPolicy: Always    # 이 설정이 sidecar를 만듦
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
  containers:
    - name: main-app
      image: my-app:v1.0
```

> **참고**: Sidecar Containers는 1.28에서 Alpha, 1.29에서 Beta로 승격되었으며, 이후 1.33에서 GA로 졸업합니다. 상세 내용은 1.33 섹션을 참조하세요.

#### 기타 주요 변경 사항 (1.29)

| 기능 | 단계 | 설명 |
|------|------|------|
| nftables kube-proxy 모드 | Alpha | iptables 대신 nftables 사용 |
| Node Log Query | Alpha | kubelet API를 통한 노드 로그 조회 |
| Pod Scheduling Readiness | Beta | Pod가 스케줄링 준비 완료를 명시적으로 표시 |
| Load Balancer IP Mode | Beta | LoadBalancer Service의 IP 모드 설정 |

---

### 4.2 Kubernetes 1.30 "Uwubernetes" (2024년 4월)

Kubernetes 1.30은 커뮤니티 문화를 반영한 유머러스한 코드네임 "Uwubernetes"로 릴리스되었습니다. 58개의 Enhancement가 포함되며, 특히 보안과 스케줄링 영역에서 중요한 기능들이 GA로 졸업했습니다.

```mermaid
pie title "Kubernetes 1.30 Enhancement 분포"
    "Stable (GA)" : 17
    "Beta" : 18
    "Alpha" : 23
```

#### 핵심 GA 기능

##### ValidatingAdmissionPolicy (CEL 기반) GA (KEP-3488)

OPA/Gatekeeper 같은 외부 webhook 없이도 CEL(Common Expression Language)을 사용해 API 서버 내에서 직접 Admission 검증을 수행할 수 있습니다.

```yaml
# 1. ValidatingAdmissionPolicy 정의
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: "require-resource-limits"
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["pods"]
  validations:
    - expression: >-
        object.spec.containers.all(c,
          has(c.resources) &&
          has(c.resources.limits) &&
          has(c.resources.limits.cpu) &&
          has(c.resources.limits.memory)
        )
      message: "모든 컨테이너에 CPU와 메모리 limits를 설정해야 합니다."
      reason: Invalid
---
# 2. ValidatingAdmissionPolicyBinding으로 정책 적용
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata:
  name: "require-resource-limits-binding"
spec:
  policyName: "require-resource-limits"
  validationActions: [Deny]
  matchResources:
    namespaceSelector:
      matchLabels:
        env: production
```

**ValidatingAdmissionPolicy vs Webhook 기반 솔루션 비교:**

| 항목 | ValidatingAdmissionPolicy | Webhook (OPA/Kyverno) |
|------|--------------------------|----------------------|
| 런타임 의존성 | 없음 (API 서버 내장) | 외부 서비스 필요 |
| 지연시간 | 매우 낮음 | 네트워크 호출 오버헤드 |
| 장애 영향 | 없음 | webhook 서비스 장애 시 영향 |
| 표현력 | CEL (제한적이나 대부분 충분) | Rego/CEL/YAML (더 풍부) |
| 외부 데이터 참조 | 제한적 | 가능 |
| 뮤테이션 지원 | 미지원 (검증만) | 지원 |

**CEL 표현식 예시 모음:**

```yaml
# 이미지 레지스트리 제한
- expression: >-
    object.spec.containers.all(c,
      c.image.startsWith('123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/')
    )
  message: "ECR 레지스트리의 이미지만 사용할 수 있습니다."

# 루트 실행 금지
- expression: >-
    object.spec.containers.all(c,
      has(c.securityContext) &&
      has(c.securityContext.runAsNonRoot) &&
      c.securityContext.runAsNonRoot == true
    )
  message: "컨테이너는 root가 아닌 사용자로 실행해야 합니다."

# 레이블 필수
- expression: >-
    has(object.metadata.labels) &&
    has(object.metadata.labels['app.kubernetes.io/name']) &&
    has(object.metadata.labels['app.kubernetes.io/version'])
  message: "app.kubernetes.io/name 및 version 레이블이 필수입니다."
```

##### Pod Scheduling Readiness GA (KEP-3521)

Pod에 `schedulingGates`를 설정하여 특정 조건이 충족될 때까지 스케줄링을 보류할 수 있습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gated-pod
spec:
  schedulingGates:
    - name: "example.com/gpu-quota-approved"
    - name: "example.com/security-scan-passed"
  containers:
    - name: ml-training
      image: training:v1.0
      resources:
        limits:
          nvidia.com/gpu: 4
```

```bash
# 스케줄링 게이트 제거 (외부 컨트롤러 또는 수동)
kubectl patch pod gated-pod --type='json' \
  -p='[{"op": "remove", "path": "/spec/schedulingGates/0"}]'
```

**활용 시나리오:**
- GPU 쿼터 승인 프로세스 연동
- 보안 스캔 완료 후 배포
- 외부 리소스(라이센스, 외부 서비스) 준비 대기
- 배치 작업의 동시 스케줄링 조율

##### HPA Container Resource Metrics GA (KEP-2702)

HPA(Horizontal Pod Autoscaler)에서 Pod 전체가 아닌 특정 컨테이너의 리소스 사용량을 기준으로 스케일링할 수 있습니다.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: ContainerResource
      containerResource:
        name: cpu
        container: web-server    # 특정 컨테이너 지정
        target:
          type: Utilization
          averageUtilization: 70
    # Sidecar 컨테이너의 리소스는 무시하고
    # main 컨테이너 기준으로만 스케일링
```

**실무 중요성:** Sidecar 패턴(Envoy proxy, log collector 등)이 보편화됨에 따라, sidecar의 리소스 사용이 HPA 결정에 왜곡을 줄 수 있습니다. Container Resource Metrics를 사용하면 실제 애플리케이션 컨테이너의 부하만을 기준으로 정확한 스케일링이 가능합니다.

#### 기타 주요 변경 사항 (1.30)

| 기능 | 단계 | 설명 |
|------|------|------|
| Bound Service Account Token Improvements | GA | SA 토큰의 audience, expiration 세분화 |
| Min Domains in PodTopologySpread | GA | TopologySpreadConstraints의 최소 도메인 수 |
| Go Workspaces | 내부 | Kubernetes 코드 베이스가 Go workspaces로 전환 |
| contextual logging | Beta | 구조화된 컨텍스트 로깅 |
| Recursive Read-only Mounts | Alpha | 마운트 포인트의 재귀적 읽기 전용 설정 |

---

### 4.3 Kubernetes 1.31 "Elli" (2024년 8월)

Kubernetes 1.31 "Elli"는 보안 강화에 중점을 둔 릴리스로, 45개의 Enhancement를 포함합니다.

```mermaid
pie title "Kubernetes 1.31 Enhancement 분포"
    "Stable (GA)" : 11
    "Beta" : 22
    "Alpha" : 12
```

#### 핵심 GA 기능

##### AppArmor 지원 GA (KEP-24)

Pod 스펙에서 직접 AppArmor 프로필을 지정할 수 있게 되었습니다. 기존의 어노테이션 기반 방식이 GA 필드로 전환되었습니다.

```yaml
# 기존 방식 (어노테이션 기반 - Deprecated)
# metadata:
#   annotations:
#     container.apparmor.security.beta.kubernetes.io/app: runtime/default

# 새로운 방식 (GA 필드)
apiVersion: v1
kind: Pod
metadata:
  name: secured-pod
spec:
  containers:
    - name: app
      image: my-app:v1.0
      securityContext:
        appArmorProfile:
          type: RuntimeDefault   # 또는 Localhost, Unconfined
          # type: Localhost
          # localhostProfile: "my-custom-profile"
```

**AppArmor 프로필 유형:**

| 유형 | 설명 | 사용 사례 |
|------|------|----------|
| `RuntimeDefault` | 컨테이너 런타임의 기본 프로필 | 대부분의 워크로드에 적합 |
| `Localhost` | 노드에 설치된 커스텀 프로필 | 특수 보안 요구사항 |
| `Unconfined` | AppArmor 제한 없음 | 디버깅, 특권 워크로드 |

##### PersistentVolume Last Phase Transition Time GA (KEP-3762)

PV의 마지막 phase 전환 시간을 추적하여 스토리지 모니터링과 디버깅을 개선합니다.

```bash
# PV phase 전환 시간 확인
kubectl get pv my-pv -o jsonpath='{.status.lastPhaseTransitionTime}'
# 출력: 2024-08-15T10:30:00Z
```

#### 핵심 Beta 기능

##### DRA (Dynamic Resource Allocation) Structured Parameters Beta (KEP-4381)

DRA의 구조화된 파라미터 모델이 beta로 승격되었습니다. 이를 통해 GPU, FPGA 등 특수 하드웨어 리소스를 보다 체계적으로 요청하고 할당할 수 있습니다.

```yaml
# ResourceClaim 정의 (DRA 구조화 파라미터)
apiVersion: resource.k8s.io/v1beta1
kind: ResourceClaim
metadata:
  name: gpu-claim
spec:
  devices:
    requests:
      - name: gpu-request
        deviceClassName: gpu.nvidia.com
        selectors:
          - cel:
              expression: >-
                device.attributes["gpu.nvidia.com"].model == "A100" &&
                device.capacity["gpu.nvidia.com"].memory.compareTo(quantity("80Gi")) >= 0
---
apiVersion: v1
kind: Pod
metadata:
  name: ml-training
spec:
  containers:
    - name: trainer
      image: ml-training:v1.0
      resources:
        claims:
          - name: gpu-claim
  resourceClaims:
    - name: gpu-claim
      resourceClaimName: gpu-claim
```

#### 기타 주요 변경 사항 (1.31)

| 기능 | 단계 | 설명 |
|------|------|------|
| nftables kube-proxy | Beta | nftables 기반 프록시 모드 |
| Traffic Distribution for Services | Beta | Service 트래픽 분배 제어 |
| Multiple Service CIDRs | Beta | 서비스 IP 범위 동적 관리 |
| Image Volume Source | Alpha | OCI 이미지를 볼륨으로 마운트 |
| Auto-remove PVC protection finalizer | Beta | PVC 삭제 보호 자동 해제 |

---

### 4.4 Kubernetes 1.32 "Penelope" (2024년 12월)

Kubernetes 1.32 "Penelope"는 인가(Authorization)와 스토리지 관리에 중요한 발전이 있었습니다. 44개의 Enhancement가 포함됩니다.

```mermaid
pie title "Kubernetes 1.32 Enhancement 분포"
    "Stable (GA)" : 13
    "Beta" : 12
    "Alpha" : 19
```

#### 핵심 GA 기능

##### StructuredAuthorizationConfiguration GA (KEP-3221)

API 서버의 인가 체인(authorization chain)을 구조화된 설정 파일로 관리할 수 있게 되었습니다. 기존의 --authorization-mode 플래그를 대체합니다.

```yaml
# AuthorizationConfiguration 예시
apiVersion: apiserver.config.k8s.io/v1
kind: AuthorizationConfiguration
authorizers:
  # 1순위: 커스텀 Webhook 인가
  - type: Webhook
    name: custom-authorizer
    webhook:
      timeout: 3s
      failurePolicy: Deny
      subjectAccessReviewVersion: v1
      matchConditionSubjectAccessReviewVersion: v1
      authorizedTTL: 5m
      unauthorizedTTL: 30s
      connectionInfo:
        type: KubeConfigFile
        kubeConfigFile: /etc/kubernetes/webhook-config.yaml
      matchConditions:
        # GPU 네임스페이스 접근만 이 webhook으로 라우팅
        - expression: >-
            has(request.namespace) &&
            request.namespace.startsWith('gpu-')
  
  # 2순위: RBAC
  - type: RBAC
    name: rbac
  
  # 3순위: Node 인가
  - type: Node
    name: node
```

**기존 방식과의 비교:**

```bash
# 기존 (플래그 기반)
kube-apiserver --authorization-mode=Node,RBAC,Webhook \
               --authorization-webhook-config-file=...

# 새로운 방식 (구조화된 설정 파일)
kube-apiserver --authorization-config=/etc/kubernetes/auth-config.yaml
```

**장점:**
- 인가 체인의 순서와 조건을 세밀하게 제어
- CEL 기반 matchConditions로 특정 요청만 webhook으로 라우팅
- TTL 설정으로 인가 캐싱 최적화
- Hot-reload 지원 (API 서버 재시작 불필요)

##### Volume Attribute Class GA (KEP-3751)

VolumeAttributesClass를 통해 볼륨의 성능 속성(IOPS, throughput 등)을 동적으로 변경할 수 있습니다.

```yaml
# VolumeAttributesClass 정의
apiVersion: storage.k8s.io/v1beta1
kind: VolumeAttributesClass
metadata:
  name: high-performance
driverName: ebs.csi.aws.com
parameters:
  iops: "16000"
  throughput: "1000"
---
apiVersion: storage.k8s.io/v1beta1
kind: VolumeAttributesClass
metadata:
  name: standard
driverName: ebs.csi.aws.com
parameters:
  iops: "3000"
  throughput: "125"
---
# PVC에서 VolumeAttributesClass 참조
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 500Gi
  storageClassName: gp3-csi
  volumeAttributesClassName: high-performance  # 성능 클래스 지정
```

```bash
# 볼륨 성능 클래스 동적 변경 (다운타임 없이)
kubectl patch pvc database-pvc \
  -p '{"spec":{"volumeAttributesClassName":"standard"}}'
```

**EKS에서의 활용:** EBS gp3 볼륨의 IOPS/throughput을 PVC 수정만으로 동적 변경 가능. 피크 시간에 성능을 올리고, 비피크 시간에 낮추는 비용 최적화 패턴 구현 가능.

#### 기타 주요 변경 사항 (1.32)

| 기능 | 단계 | 설명 |
|------|------|------|
| Recursive Read-only Mounts | Beta | 재귀적 읽기 전용 마운트 |
| Automatic Retry of Failed Pod Disruption | Beta | PDB 준수 실패 시 자동 재시도 |
| Job Managed-by Field | GA | 외부 컨트롤러에 의한 Job 관리 |
| Custom Resource Field Selectors | GA | CRD에 대한 필드 셀렉터 지원 |
| StableLoadBalancerNodeSet | GA | LoadBalancer의 안정적 노드 세트 |

---

### 4.5 Kubernetes 1.33 "Octarine" (2025년 4월)

Kubernetes 1.33 "Octarine"은 Terry Pratchett의 Discworld에서 영감을 받은 코드네임으로, **64개의 Enhancement**를 포함하는 대형 릴리스입니다. Sidecar Containers GA, In-Place Pod Resize beta 등 오랫동안 기다려온 기능들이 포함되어 있습니다.

```mermaid
pie title "Kubernetes 1.33 Enhancement 분포 (64개)"
    "Stable (GA)" : 18
    "Beta" : 20
    "Alpha" : 24
```

> **중요**: 1.33은 2024-2025년 릴리스 중 가장 많은 Enhancement를 포함하며, 운영 환경에 미치는 영향이 큰 릴리스입니다.

#### 핵심 GA 기능

##### Sidecar Containers GA (KEP-753)

**졸업 경로: Alpha 1.28 → Beta 1.29 → GA 1.33**

Native Sidecar Containers가 드디어 GA로 졸업했습니다. Init container에 `restartPolicy: Always`를 설정하여 Pod 수명 동안 지속적으로 실행되는 sidecar를 정의할 수 있습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: production-app
spec:
  initContainers:
    # Sidecar 1: Istio Envoy 프록시
    - name: istio-proxy
      image: istio/proxyv2:1.22.0
      restartPolicy: Always
      ports:
        - containerPort: 15090
          name: http-envoy-prom
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: 500m
          memory: 512Mi
      securityContext:
        runAsNonRoot: true
    
    # Sidecar 2: 로그 수집기
    - name: fluent-bit
      image: fluent/fluent-bit:3.0
      restartPolicy: Always
      volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
      resources:
        requests:
          cpu: 50m
          memory: 64Mi
    
    # 일반 init container (한 번 실행 후 종료)
    - name: db-migration
      image: migration-tool:v2.0
      command: ["migrate", "--target", "latest"]
  
  containers:
    - name: web-app
      image: my-app:v3.0
      volumeMounts:
        - name: app-logs
          mountPath: /var/log/app
  
  volumes:
    - name: app-logs
      emptyDir: {}
```

**Sidecar Container의 수명 주기:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Pod 수명 주기                                    │
│                                                                      │
│  시작 ──────────────────────────────────────────────────────── 종료   │
│                                                                      │
│  ┌─ Sidecar (restartPolicy: Always) ─────────────────────────────┐  │
│  │  istio-proxy: ████████████████████████████████████████████████ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ Sidecar (restartPolicy: Always) ─────────────────────────────┐  │
│  │  fluent-bit:  ████████████████████████████████████████████████ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─ Init Container ──┐                                              │
│  │  db-migration: ███ │                                              │
│  └───────────────────┘                                              │
│                                                                      │
│                        ┌─ Main Container ────────────────────────┐  │
│                        │  web-app: ██████████████████████████████ │  │
│                        └─────────────────────────────────────────┘  │
│                                                                      │
│  실행 순서:                                                           │
│  1. Sidecar 시작 → 2. Init 실행/완료 → 3. Main 시작                   │
│  종료 순서:                                                           │
│  1. Main 종료 → 2. Sidecar 종료 (역순)                                │
└──────────────────────────────────────────────────────────────────────┘
```

**GA 이전 대비 해결된 문제점:**
- Job 완료 문제: 기존에는 sidecar가 종료되지 않아 Job이 완료 상태로 전환되지 않음 → GA에서는 main container 종료 시 sidecar도 정상 종료
- 시작 순서 보장: Sidecar가 먼저 시작된 후 main container가 실행됨
- 리소스 계산: Sidecar 리소스가 Pod의 리소스 요청/제한에 올바르게 포함
- Probe 지원: Sidecar에 대한 liveness, readiness, startup probe 지원

##### In-Place Pod Vertical Scaling Beta (KEP-1287)

**졸업 경로: Alpha 1.27 → Beta 1.33**

Pod를 재시작하지 않고 CPU/메모리 리소스를 동적으로 변경할 수 있습니다. VPA(Vertical Pod Autoscaler)와의 연동을 통해 자동 수직 스케일링이 가능해집니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resizable-app
spec:
  containers:
    - name: app
      image: my-app:v1.0
      resources:
        requests:
          cpu: 500m
          memory: 256Mi
        limits:
          cpu: "1"
          memory: 512Mi
      # 리사이즈 정책: CPU는 재시작 없이, 메모리는 재시작 필요
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired   # CPU 변경 시 재시작 불필요
        - resourceName: memory
          restartPolicy: RestartContainer  # 메모리 변경 시 재시작 필요
```

```bash
# Pod 리소스 동적 변경 (kubectl patch)
kubectl patch pod resizable-app --subresource resize --patch \
  '{"spec":{"containers":[{"name":"app","resources":{"requests":{"cpu":"1"},"limits":{"cpu":"2"}}}]}}'

# 리사이즈 상태 확인
kubectl get pod resizable-app -o jsonpath='{.status.resize}'
# 가능한 값: Proposed, InProgress, Deferred, Infeasible
```

**리사이즈 상태 설명:**

| 상태 | 설명 |
|------|------|
| `Proposed` | 리사이즈 요청이 제출됨 |
| `InProgress` | 리사이즈가 진행 중 |
| `Deferred` | 노드 리소스 부족으로 연기됨 |
| `Infeasible` | 현재 노드에서 리사이즈 불가능 |
| (비어 있음) | 리사이즈 완료 |

**실무 활용 시나리오:**

```yaml
# VPA와 연동한 자동 수직 스케일링 (1.33+)
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  updatePolicy:
    updateMode: "InPlace"    # In-Place 업데이트 모드 (재시작 없이)
  resourcePolicy:
    containerPolicies:
      - containerName: app
        minAllowed:
          cpu: 250m
          memory: 128Mi
        maxAllowed:
          cpu: "4"
          memory: 4Gi
```

##### ServiceCIDR 및 IPAddress API GA (KEP-1880)

서비스 IP 범위를 동적으로 관리할 수 있는 ServiceCIDR과 IPAddress API가 GA로 졸업했습니다.

```yaml
# 추가 ServiceCIDR 정의
apiVersion: networking.k8s.io/v1
kind: ServiceCIDR
metadata:
  name: secondary-service-cidr
spec:
  cidrs:
    - "10.200.0.0/16"    # 추가 서비스 IP 범위
```

```bash
# 현재 ServiceCIDR 확인
kubectl get servicecidr
# NAME                    CIDRS            AGE
# kubernetes              10.96.0.0/12     365d
# secondary-service-cidr  10.200.0.0/16    1d

# 할당된 IP 주소 확인
kubectl get ipaddress
```

**실무 영향:** 대규모 클러스터에서 서비스 IP 주소가 부족해지는 문제를 해결할 수 있습니다. 기존 클러스터를 중단하지 않고 서비스 CIDR 범위를 확장할 수 있습니다.

##### Topology Aware Routing GA (KEP-2433)

서비스 트래픽을 동일 토폴로지(존, 리전) 내의 엔드포인트로 우선 라우팅하여 네트워크 비용을 절감하고 지연시간을 줄입니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-service
  annotations:
    service.kubernetes.io/topology-mode: Auto    # GA에서의 설정 방법
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 8080
```

**Topology Aware Routing 동작 원리:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    ap-northeast-2 리전                            │
│                                                                   │
│  ┌─── AZ-a ──────────┐  ┌─── AZ-b ──────────┐  ┌─── AZ-c ───┐ │
│  │                    │  │                    │  │              │ │
│  │  Client Pod ───────┼──┼───── 크로스존 ──────┼──┼── Pod C     │ │
│  │       │            │  │     트래픽 (비용↑)   │  │              │ │
│  │       │ 동일 존    │  │                    │  │              │ │
│  │       │ 트래픽 우선  │  │  Pod B             │  │              │ │
│  │       ↓            │  │                    │  │              │ │
│  │  Pod A ✓           │  │                    │  │              │ │
│  │                    │  │                    │  │              │ │
│  └────────────────────┘  └────────────────────┘  └──────────────┘│
│                                                                   │
│  topology-mode: Auto 설정 시:                                      │
│  1. 동일 AZ 엔드포인트가 충분하면 → 동일 AZ로 라우팅                    │
│  2. 동일 AZ가 부족하면 → 크로스 AZ도 포함                             │
└─────────────────────────────────────────────────────────────────┘
```

**EKS 비용 영향:** AWS에서 크로스-AZ 트래픽은 GB당 $0.01이 부과됩니다. Topology Aware Routing을 활성화하면 대부분의 서비스 트래픽이 동일 AZ 내에서 처리되어 상당한 비용 절감이 가능합니다.

##### Job Success Policy GA (KEP-3998)

Job의 성공 조건을 세밀하게 제어할 수 있습니다. 특정 인덱스의 Pod가 성공하면 전체 Job을 성공으로 처리할 수 있습니다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: distributed-training
spec:
  completionMode: Indexed
  completions: 10
  parallelism: 10
  # 리더 Pod(인덱스 0)가 성공하면 전체 Job 성공
  successPolicy:
    rules:
      - succeededIndexes: "0"     # 리더 인덱스
        succeededCount: 1
  template:
    spec:
      containers:
        - name: trainer
          image: ml-training:v2.0
          env:
            - name: JOB_COMPLETION_INDEX
              valueFrom:
                fieldRef:
                  fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
```

**활용 시나리오:**
- 분산 학습: 리더 워커가 완료되면 나머지 워커도 종료
- 맵리듀스: 리듀서가 완료되면 Job 성공
- 헬스체크 Job: 특정 수의 체크가 성공하면 전체 성공

#### 기타 주요 변경 사항 (1.33)

| 기능 | 단계 | 설명 |
|------|------|------|
| PodLifecycleSleepAction | GA | Pod 라이프사이클 훅에 sleep 액션 추가 |
| Node Log Query API | Beta | kubelet을 통한 노드 로그 조회 |
| DRA: Scalable Device Configuration | Beta | DRA 디바이스 설정 확장성 개선 |
| User Namespaces | Beta | Linux user namespace를 사용한 Pod 격리 |
| CBORSerializer | Alpha | CBOR 직렬화 포맷 지원 |
| Streaming List | Alpha | 대규모 리스트의 스트리밍 응답 |
| In-Place Pod Resize for StatefulSets | Alpha | StatefulSet의 In-Place 리사이즈 지원 |
| Pod-level cgroups | Alpha | Pod 레벨 cgroup 리소스 관리 |

---

### 4.6 Kubernetes 1.34 "Of Wind & Will" (2025년 8월)

Kubernetes 1.34는 DRA(Dynamic Resource Allocation)의 Core API가 GA로 졸업한 중요한 릴리스입니다. AI/ML 워크로드를 위한 GPU 자원 관리의 기반이 완성됩니다.

```mermaid
pie title "Kubernetes 1.34 Enhancement 분포"
    "Stable (GA)" : 15
    "Beta" : 17
    "Alpha" : 20
```

#### 핵심 GA 기능

##### DRA (Dynamic Resource Allocation) Core APIs GA (KEP-4381)

**졸업 경로: Alpha 1.26 → Beta 1.31 → GA 1.34**

GPU, FPGA, 네트워크 디바이스 등 특수 하드웨어 리소스를 Kubernetes 네이티브 방식으로 요청하고 할당할 수 있는 DRA Core API가 GA로 졸업했습니다.

```yaml
# DeviceClass 정의 (클러스터 관리자)
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: gpu-nvidia-a100
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].productName == "A100"
  config:
    - opaque:
        driver: gpu.nvidia.com
        parameters:
          raw: '{"sharing": {"timeSlicing": {"replicas": 2}}}'
---
# ResourceClaim (사용자/개발자)
apiVersion: resource.k8s.io/v1
kind: ResourceClaim
metadata:
  name: training-gpus
spec:
  devices:
    requests:
      - name: gpu
        deviceClassName: gpu-nvidia-a100
        count: 4    # A100 GPU 4장 요청
    constraints:
      - requests: ["gpu"]
        matchAttribute: "gpu.nvidia.com/numa-node"
        # 동일 NUMA 노드의 GPU를 선호
---
# ResourceClaimTemplate (Deployment에서 사용)
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: gpu-claim-template
spec:
  spec:
    devices:
      requests:
        - name: gpu
          deviceClassName: gpu-nvidia-a100
          count: 1
---
# Pod에서 ResourceClaim 사용
apiVersion: v1
kind: Pod
metadata:
  name: ml-inference
spec:
  containers:
    - name: inference
      image: vllm:v0.5.0
      resources:
        claims:
          - name: model-gpu
  resourceClaims:
    - name: model-gpu
      resourceClaimTemplateName: gpu-claim-template
```

**DRA vs Device Plugin 비교:**

| 항목 | DRA (1.34 GA) | Device Plugin (기존) |
|------|--------------|---------------------|
| 디바이스 선택 | CEL 표현식으로 세밀한 선택 | 단순 수량 기반 |
| 디바이스 공유 | 네이티브 지원 (time-slicing, MPS, MIG) | 플러그인별 구현 |
| 토폴로지 인식 | NUMA, PCIe 토폴로지 지원 | 제한적 |
| 디바이스 속성 조회 | 표준화된 attribute/capacity API | 비표준 |
| 다중 디바이스 조합 | 단일 claim에서 여러 디바이스 조합 | 불가 |
| 스케줄러 통합 | 네이티브 통합 | 제한적 |

**EKS에서의 AI/ML 활용:**

```yaml
# EKS에서 DRA를 활용한 GPU 워크로드 예시
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-serving
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
        - name: vllm
          image: vllm/vllm-openai:latest
          args:
            - "--model"
            - "meta-llama/Llama-3.1-70B"
            - "--tensor-parallel-size"
            - "4"
          resources:
            claims:
              - name: training-gpus
      resourceClaims:
        - name: training-gpus
          resourceClaimTemplateName: gpu-claim-template
```

##### VolumeAttributesClass GA (KEP-3751)

1.32에서 beta였던 VolumeAttributesClass가 GA로 졸업했습니다.

```yaml
# GA 버전 API
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: io-intensive
driverName: ebs.csi.aws.com
parameters:
  iops: "64000"
  throughput: "4000"
---
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: throughput-optimized
driverName: ebs.csi.aws.com
parameters:
  iops: "3000"
  throughput: "750"
```

**자동 성능 조절 패턴 (CronJob 활용):**

```yaml
# 피크 시간 전 성능 상향
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-up-iops
spec:
  schedule: "0 8 * * 1-5"    # 평일 오전 8시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: scaler
              image: bitnami/kubectl:latest
              command:
                - /bin/sh
                - -c
                - |
                  kubectl patch pvc database-pvc \
                    -p '{"spec":{"volumeAttributesClassName":"io-intensive"}}'
          restartPolicy: OnFailure
---
# 비피크 시간 성능 하향
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-down-iops
spec:
  schedule: "0 22 * * 1-5"   # 평일 오후 10시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: scaler
              image: bitnami/kubectl:latest
              command:
                - /bin/sh
                - -c
                - |
                  kubectl patch pvc database-pvc \
                    -p '{"spec":{"volumeAttributesClassName":"throughput-optimized"}}'
          restartPolicy: OnFailure
```

#### 핵심 Alpha 기능

##### KYAML Alpha (KEP-4222)

Kubernetes에 내장된 새로운 YAML/JSON 처리 라이브러리인 KYAML이 Alpha로 도입되었습니다. 기존의 go-yaml/yaml.v2 라이브러리를 대체하여 YAML 처리의 정확성과 보안성을 향상시킵니다.

**KYAML의 목표:**
- YAML 1.2 스펙 완전 준수 (기존은 YAML 1.1 기반)
- 일관된 에러 메시지와 위치 정보
- 보안 강화: YAML bomb 등 악의적 입력 방어
- kubectl, API 서버, CRD 처리 등 전반에 걸쳐 통일된 YAML 처리

```yaml
# YAML 1.1 vs 1.2 차이점 예시
# YAML 1.1: "yes", "no", "on", "off"가 boolean으로 해석
# YAML 1.2: "true", "false"만 boolean

# 기존 (YAML 1.1 - 주의 필요)
data:
  norway: no     # boolean false로 해석될 수 있음!
  
# KYAML (YAML 1.2 - 명확)
data:
  norway: "no"   # 문자열로 명확히 처리
```

#### 기타 주요 변경 사항 (1.34)

| 기능 | 단계 | 설명 |
|------|------|------|
| nftables kube-proxy | GA | nftables 기반 프록시 모드 GA 졸업 |
| User Namespaces | GA | Pod의 Linux user namespace 격리 |
| Node Log Query | GA | kubelet API를 통한 노드 로그 조회 |
| Traffic Distribution (preferClose) | GA | Service의 근접 트래픽 분배 |
| PodHealthyPolicy for PDB | GA | PDB의 unhealthy pod 처리 정책 |
| Recursive Read-only Mounts | GA | 재귀적 읽기 전용 마운트 |
| Image Pull Policy: IfNotPresentOrNewer | Alpha | 이미지가 없거나 새 버전이면 pull |
| Portforward over WebSocket | GA | WebSocket을 통한 포트 포워딩 |

---

### 4.7 Kubernetes 1.35 "Timbernetes" (2025년 12월)

Kubernetes 1.35 "Timbernetes"는 In-Place Pod Resize GA를 포함하여 워크로드 관리의 큰 진전을 이룬 릴리스입니다.

```mermaid
pie title "Kubernetes 1.35 Enhancement 분포"
    "Stable (GA)" : 16
    "Beta" : 18
    "Alpha" : 22
```

#### 핵심 GA 기능

##### In-Place Pod Vertical Scaling GA (KEP-1287)

**졸업 경로: Alpha 1.27 → Beta 1.33 → GA 1.35**

Pod를 재시작하지 않고 CPU/메모리 리소스를 변경하는 기능이 드디어 GA로 졸업했습니다. VPA(Vertical Pod Autoscaler)의 실질적인 활용도가 크게 향상됩니다.

```yaml
# GA 버전에서의 In-Place Pod Resize
apiVersion: v1
kind: Pod
metadata:
  name: production-api
spec:
  containers:
    - name: api-server
      image: api:v4.0
      resources:
        requests:
          cpu: "1"
          memory: 1Gi
        limits:
          cpu: "2"
          memory: 2Gi
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: NotRequired    # GA에서는 메모리도 재시작 없이 가능한 케이스 확대
```

**Deployment에서의 In-Place Resize 전략:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-service
spec:
  replicas: 10
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: web:v5.0
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 2Gi
          resizePolicy:
            - resourceName: cpu
              restartPolicy: NotRequired
            - resourceName: memory
              restartPolicy: NotRequired
---
# VPA 연동 (In-Place 모드)
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: web-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-service
  updatePolicy:
    updateMode: "InPlace"
  resourcePolicy:
    containerPolicies:
      - containerName: web
        minAllowed:
          cpu: 250m
          memory: 256Mi
        maxAllowed:
          cpu: "4"
          memory: 8Gi
        controlledResources: ["cpu", "memory"]
```

**GA에서 해결된 제약 사항:**

| 항목 | Beta (1.33) | GA (1.35) |
|------|-------------|-----------|
| CPU 리사이즈 | 재시작 불필요 | 재시작 불필요 |
| 메모리 리사이즈 | 대부분 재시작 필요 | 재시작 없이 가능한 케이스 확대 |
| StatefulSet 지원 | Alpha (1.33) | Beta (1.35) |
| Deployment 롤링 리사이즈 | 미지원 | 지원 |
| VPA In-Place 모드 | 실험적 | 안정적 |
| QoS 클래스 변경 | 불가 | 불가 (설계상 제한) |

**In-Place Resize 모니터링:**

```bash
# Pod 리사이즈 이벤트 모니터링
kubectl get events --field-selector reason=PodResizeSucceeded -w

# Pod 현재 리소스 할당 상태 확인
kubectl get pod production-api -o jsonpath='{
  .status.containerStatuses[*].allocatedResources}'

# 리사이즈 조건 확인
kubectl get pod production-api -o jsonpath='{.status.conditions}' | jq '.[] | select(.type=="PodResizeInProgress")'
```

##### KYAML Beta (KEP-4222)

KYAML이 Beta로 승격되어 기본 활성화됩니다.

**마이그레이션 고려사항:**
- YAML 1.1에서 1.2로의 전환으로 인해 일부 매니페스트의 동작이 변경될 수 있음
- 특히 `yes/no`, `on/off`, `y/n` 같은 값이 boolean이 아닌 문자열로 처리됨
- 0으로 시작하는 숫자가 더 이상 8진수로 해석되지 않음

```bash
# KYAML 호환성 검증 도구
kubectl apply --dry-run=server --validate=strict -f my-manifest.yaml

# KYAML Feature Gate 비활성화 (호환성 문제 발생 시)
# EKS에서는 직접 설정 불가 - AWS 지원 티켓 필요
```

#### 핵심 Alpha 기능

##### Gang Scheduling Alpha (KEP-4832)

여러 Pod가 동시에 스케줄링되어야 하는 "all-or-nothing" 스케줄링을 지원합니다. 분산 학습, 빅데이터 처리 등에서 필수적인 기능입니다.

```yaml
# Gang Scheduling 예시 (1.35 Alpha)
apiVersion: batch/v1
kind: Job
metadata:
  name: distributed-training
spec:
  completionMode: Indexed
  completions: 8
  parallelism: 8
  template:
    metadata:
      labels:
        gang: training-group-1
    spec:
      schedulingGates:
        - name: "scheduling.k8s.io/gang-scheduling"
      # 8개 Pod가 모두 스케줄 가능해야만 배치 시작
      containers:
        - name: worker
          image: horovod-training:v1.0
          resources:
            limits:
              nvidia.com/gpu: 4
```

**Gang Scheduling의 필요성:**

```
┌─────────────────────────────────────────────────────────────┐
│                  Gang Scheduling 없이                        │
│                                                               │
│  Worker 0: ████ (GPU 할당됨, 대기 중)                         │
│  Worker 1: ████ (GPU 할당됨, 대기 중)                         │
│  Worker 2: ████ (GPU 할당됨, 대기 중)                         │
│  Worker 3: .... (GPU 부족으로 Pending)                        │
│                                                               │
│  → 3개 Worker의 GPU가 낭비됨 (데드락 위험)                      │
├─────────────────────────────────────────────────────────────┤
│                  Gang Scheduling 사용 시                      │
│                                                               │
│  4개 GPU 모두 사용 가능? → Yes → 4개 Worker 동시 배치          │
│                          → No  → 모든 Worker Pending (리소스 미점유) │
│                                                               │
│  → 데드락 방지, 리소스 효율성 향상                               │
└─────────────────────────────────────────────────────────────┘
```

#### 기타 주요 변경 사항 (1.35)

| 기능 | 단계 | 설명 |
|------|------|------|
| CBORSerializer | Beta | CBOR 직렬화 포맷 지원 (더 작고 빠름) |
| Streaming List | Beta | 대규모 리스트의 스트리밍 응답 |
| Pod-level Resource Limits | Beta | Pod 레벨에서의 리소스 제한 |
| Image Pull Policy IfNotPresentOrNewer | Beta | 새 이미지 자동 감지 pull |
| DRA: Device Taints | Alpha | DRA 디바이스에 taint 설정 |
| Node Maintenance Mode | Alpha | 노드 유지보수 모드 |

---

### 4.8 Kubernetes 1.36 "ハル (Haru)" (2026년 4월)

Kubernetes 1.36은 일본어 "ハル"(봄, Haru)을 코드네임으로 사용한 최신 릴리스입니다. Pod-level 리소스 관리와 KYAML의 안정화가 진행되고 있습니다.

```mermaid
pie title "Kubernetes 1.36 Enhancement 분포"
    "Stable (GA)" : 14
    "Beta" : 19
    "Alpha" : 21
```

#### 핵심 기능

##### Pod-level In-Place Scaling Beta (KEP-2837)

개별 컨테이너가 아닌 Pod 레벨에서의 리소스 제한을 설정하고 동적으로 변경할 수 있습니다. 이를 통해 Pod 내 컨테이너 간 리소스 공유가 더욱 유연해집니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: shared-resource-pod
spec:
  # Pod 레벨 리소스 (컨테이너 간 공유)
  resources:
    limits:
      cpu: "4"
      memory: 8Gi
    requests:
      cpu: "2"
      memory: 4Gi
  containers:
    - name: main-app
      image: app:v6.0
      resources:
        requests:
          cpu: "1"
          memory: 2Gi
        # limits는 Pod 레벨에서 관리
    - name: sidecar
      image: envoy:v1.30
      restartPolicy: Always
      resources:
        requests:
          cpu: 250m
          memory: 256Mi
```

**Pod-level vs Container-level 리소스의 차이:**

```
┌─────────────────────────────────────────────────────────────────┐
│                  Container-level 리소스 (기존)                    │
│                                                                   │
│  Pod Total = Container A limits + Container B limits              │
│  ┌──────────────┐ ┌──────────────┐                               │
│  │ Container A  │ │ Container B  │                               │
│  │ CPU: 2 core  │ │ CPU: 1 core  │  Pod Total: 3 cores          │
│  │ Mem: 4Gi     │ │ Mem: 2Gi     │  Pod Total: 6Gi              │
│  └──────────────┘ └──────────────┘                               │
│  → 각 컨테이너가 자신의 한도 내에서만 사용 가능                       │
├─────────────────────────────────────────────────────────────────┤
│                  Pod-level 리소스 (1.36)                          │
│                                                                   │
│  Pod-level limits: CPU 4 cores, Memory 8Gi                       │
│  ┌──────────────────────────────────────────┐                    │
│  │              Pod Resource Pool            │                    │
│  │  ┌──────────┐ ┌──────────┐               │                    │
│  │  │ Cont. A  │ │ Cont. B  │  유휴 리소스    │                    │
│  │  │ ~2.5 core│ │ ~1.5 core│  공유 가능      │                    │
│  │  └──────────┘ └──────────┘               │                    │
│  └──────────────────────────────────────────┘                    │
│  → Pod 한도 내에서 컨테이너 간 유연한 리소스 사용                     │
└─────────────────────────────────────────────────────────────────┘
```

##### KYAML 안정화 진행

KYAML이 지속적으로 안정화되며, 1.36에서는 대부분의 매니페스트 처리에 KYAML이 기본으로 사용됩니다.

```bash
# KYAML 관련 매니페스트 검증
# 기존 매니페스트가 KYAML 호환인지 사전 확인
kubectl apply --dry-run=server -f manifests/ --validate=strict 2>&1 | grep -i "yaml"
```

##### Gang Scheduling Beta

1.35에서 Alpha로 도입된 Gang Scheduling이 Beta로 승격되어 기본 활성화됩니다.

```yaml
# Gang Scheduling을 활용한 MPI 분산 학습
apiVersion: batch/v1
kind: Job
metadata:
  name: mpi-training
  annotations:
    scheduling.k8s.io/gang-min-size: "4"     # 최소 4개 Pod 동시 배치 필요
spec:
  completionMode: Indexed
  completions: 8
  parallelism: 8
  template:
    spec:
      containers:
        - name: mpi-worker
          image: horovod:v0.30
          resources:
            limits:
              nvidia.com/gpu: 2
            claims:
              - name: gpu
      resourceClaims:
        - name: gpu
          resourceClaimTemplateName: a100-claim
```

#### 기타 주요 변경 사항 (1.36)

| 기능 | 단계 | 설명 |
|------|------|------|
| KYAML | GA 진행 중 | YAML 1.2 기반 처리 안정화 |
| DRA: Device Health Monitoring | Beta | DRA 디바이스 상태 모니터링 |
| Node Maintenance Mode | Beta | 노드 유지보수 모드 |
| Streaming List | GA | 대규모 리스트의 스트리밍 응답 |
| CBORSerializer | GA 진행 중 | CBOR 직렬화 안정화 |
| Pod Disruption Conditions | GA | Pod 중단 조건 세분화 |
| Aggregated Discovery | GA | API Discovery 성능 최적화 |
| StatefulSet In-Place Resize | Beta | StatefulSet의 In-Place 리사이즈 |

---

## 5. 주요 기능 졸업 타임라인

이 섹션은 Kubernetes 1.29~1.36에서 주요 기능들의 성숙도 변화를 종합적으로 보여줍니다. 업그레이드 계획 수립 시 핵심 참고 자료로 활용하세요.

### 5.1 핵심 기능 졸업 추적표

| 기능 | KEP | Alpha | Beta | GA | 영향 범위 |
|:-----|:---:|:-----:|:----:|:--:|:---------|
| **Sidecar Containers** | 753 | 1.28 | 1.29 | **1.33** | 모든 sidecar 패턴 워크로드 |
| **In-Place Pod Resize** | 1287 | 1.27 | 1.33 | **1.35** | VPA, 리소스 최적화 |
| **DRA Core APIs** | 4381 | 1.26 | 1.31 | **1.34** | GPU/특수 하드웨어 워크로드 |
| **ValidatingAdmissionPolicy** | 3488 | 1.26 | 1.28 | **1.30** | 보안 정책 관리 |
| **KMS v2** | 3299 | 1.25 | 1.27 | **1.29** | Secrets 암호화 |
| **ReadWriteOncePod** | 2485 | 1.22 | 1.27 | **1.29** | 데이터베이스 워크로드 |
| **Pod Scheduling Readiness** | 3521 | 1.26 | 1.27 | **1.30** | 배치 스케줄링, GPU 쿼터 |
| **AppArmor GA** | 24 | - | 1.4 | **1.31** | 보안 프로필 관리 |
| **ServiceCIDR/IPAddress** | 1880 | 1.27 | 1.31 | **1.33** | 대규모 클러스터 네트워킹 |
| **Topology Aware Routing** | 2433 | 1.21 | 1.23 | **1.33** | 네트워크 비용 최적화 |
| **Job Success Policy** | 3998 | 1.28 | 1.31 | **1.33** | 분산 배치 작업 |
| **StructuredAuthzConfig** | 3221 | 1.29 | 1.30 | **1.32** | 인가 체계 고도화 |
| **VolumeAttributesClass** | 3751 | 1.29 | 1.31 | **1.34** | 스토리지 성능 관리 |
| **HPA Container Resource** | 2702 | 1.20 | 1.27 | **1.30** | Sidecar 환경의 HPA |
| **User Namespaces** | 127 | 1.25 | 1.28 | **1.34** | Pod 보안 격리 |
| **KYAML** | 4222 | 1.34 | 1.35 | 진행 중 | 매니페스트 처리 |
| **Gang Scheduling** | 4832 | 1.35 | 1.36 | 예정 | 분산 학습, 빅데이터 |
| **nftables kube-proxy** | 3866 | 1.29 | 1.31 | **1.34** | 네트워크 성능 |
| **Node Log Query** | 2258 | 1.27 | 1.33 | **1.34** | 노드 디버깅 |
| **Pod-level Resources** | 2837 | 1.32 | 1.36 | 예정 | 리소스 공유 최적화 |

### 5.2 버전별 GA 기능 요약

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    버전별 주요 GA 졸업 기능                                   │
├───────┬────────────────────────────────────────────────────────────────────┤
│ 1.29  │ KMS v2, ReadWriteOncePod                                         │
├───────┼────────────────────────────────────────────────────────────────────┤
│ 1.30  │ ValidatingAdmissionPolicy, Pod Scheduling Readiness,             │
│       │ HPA Container Resource Metrics                                    │
├───────┼────────────────────────────────────────────────────────────────────┤
│ 1.31  │ AppArmor                                                         │
├───────┼────────────────────────────────────────────────────────────────────┤
│ 1.32  │ StructuredAuthorizationConfiguration                              │
├───────┼────────────────────────────────────────────────────────────────────┤
│ 1.33  │ ★ Sidecar Containers, ServiceCIDR/IPAddress,                     │
│       │   Topology Aware Routing, Job Success Policy                      │
├───────┼────────────────────────────────────────────────────────────────────┤
│ 1.34  │ ★ DRA Core APIs, VolumeAttributesClass, User Namespaces,         │
│       │   nftables kube-proxy, Node Log Query                             │
├───────┼────────────────────────────────────────────────────────────────────┤
│ 1.35  │ ★ In-Place Pod Resize                                            │
├───────┼────────────────────────────────────────────────────────────────────┤
│ 1.36  │ Streaming List, Pod Disruption Conditions                         │
├───────┴────────────────────────────────────────────────────────────────────┤
│ ★ = 특히 운영 영향이 큰 기능                                                │
└────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 기능 성숙도 진행 시각화

```mermaid
gantt
    title 주요 기능 성숙도 타임라인
    dateFormat  YYYY-MM
    axisFormat  %Y-%m

    section Sidecar Containers
    Alpha (1.28)     :a_sc, 2023-08, 2023-12
    Beta (1.29)      :active, b_sc, 2023-12, 2025-04
    GA (1.33)        :crit, g_sc, 2025-04, 2025-08

    section In-Place Pod Resize
    Alpha (1.27)     :a_ip, 2023-04, 2025-04
    Beta (1.33)      :active, b_ip, 2025-04, 2025-12
    GA (1.35)        :crit, g_ip, 2025-12, 2026-04

    section DRA Core APIs
    Alpha (1.26)     :a_dra, 2022-12, 2024-08
    Beta (1.31)      :active, b_dra, 2024-08, 2025-08
    GA (1.34)        :crit, g_dra, 2025-08, 2025-12

    section ValidatingAdmissionPolicy
    Alpha (1.26)     :a_vap, 2022-12, 2024-04
    Beta (1.28)      :active, b_vap, 2023-08, 2024-04
    GA (1.30)        :crit, g_vap, 2024-04, 2024-08

    section Gang Scheduling
    Alpha (1.35)     :a_gs, 2025-12, 2026-04
    Beta (1.36)      :active, b_gs, 2026-04, 2026-08
```

---

## 6. Deprecation 및 제거 사항

### 6.1 Kubernetes API Deprecation 정책

Kubernetes는 명확한 Deprecation 정책을 따릅니다.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   API Deprecation 정책 요약                          │
├────────────────┬────────────────────────────────────────────────────┤
│ API 안정성       │ 최소 지원 기간                                      │
├────────────────┼────────────────────────────────────────────────────┤
│ GA (v1)        │ 12개월 또는 3회 릴리스 (더 긴 쪽)                     │
│ Beta (v1beta1) │ 9개월 또는 3회 릴리스 (더 긴 쪽)                      │
│ Alpha (v1alpha1)│ 즉시 제거 가능                                     │
├────────────────┴────────────────────────────────────────────────────┤
│ ※ Deprecated API는 해당 버전의 지원이 끝날 때까지 작동하지만,            │
│   마이그레이션을 강력히 권장합니다.                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 버전별 주요 Deprecation 및 제거 사항

#### 1.29에서의 변경

| 항목 | 상태 | 마이그레이션 |
|------|------|------------|
| KMS v1 API | Deprecated | KMS v2로 마이그레이션 |
| flowcontrol.apiserver.k8s.io/v1beta2 | Deprecated | v1beta3 또는 v1 사용 |
| `in-tree` cloud provider 코드 | 진행 중 Deprecated | external cloud provider 사용 |

#### 1.30에서의 변경

| 항목 | 상태 | 마이그레이션 |
|------|------|------------|
| SecurityContextDeny admission plugin | Removed | Pod Security Admission 사용 |
| v1beta2 FlowSchema/PriorityLevelConfiguration | Removed | v1 API 사용 |
| CephFS 인트리 볼륨 플러그인 | Deprecated | CSI 드라이버 사용 |
| RBD 인트리 볼륨 플러그인 | Deprecated | CSI 드라이버 사용 |

#### 1.31에서의 변경

| 항목 | 상태 | 마이그레이션 |
|------|------|------------|
| KMS v1 | Removed | KMS v2 필수 |
| AppArmor 어노테이션 기반 설정 | Deprecated | `securityContext.appArmorProfile` 필드 사용 |
| CephFS/RBD 인트리 플러그인 | Removed | CSI 드라이버 필수 |
| `status.nodeInfo.kubeProxyVersion` | Removed | 별도 조회 방법 사용 |

#### 1.32에서의 변경

| 항목 | 상태 | 마이그레이션 |
|------|------|------------|
| flowcontrol.apiserver.k8s.io/v1beta3 | Removed | v1 API 사용 |
| Azure File/Disk 인트리 플러그인 | Removed | CSI 드라이버 필수 |
| `host` 네트워크 기반 kube-proxy | Deprecated | nftables 또는 eBPF 기반 권장 |

#### 1.33에서의 변경

| 항목 | 상태 | 마이그레이션 |
|------|------|------------|
| 레거시 ServiceAccount 토큰 자동 생성 | Removed | Bound ServiceAccount Token 사용 |
| iptables kube-proxy 모드 | Deprecated | nftables 모드 마이그레이션 권장 |
| `kubectl run --restart=Never` 기본 동작 변경 | 변경 | 명시적으로 지정 필요 |

#### 1.34에서의 변경

| 항목 | 상태 | 마이그레이션 |
|------|------|------------|
| iptables kube-proxy 모드 | Removed | nftables 모드 필수 (EKS에서는 유예) |
| DRA v1alpha2 API | Removed | v1 API 사용 |
| resource.k8s.io/v1beta1 일부 | Deprecated | v1 API 사용 |

#### 1.35~1.36에서의 변경

| 항목 | 버전 | 상태 | 마이그레이션 |
|------|------|------|------------|
| YAML 1.1 호환 모드 | 1.35 | Deprecated | YAML 1.2 준수 매니페스트로 전환 |
| 레거시 Feature Gate 다수 | 1.35 | Removed | GA된 Feature Gate 코드 제거 |
| `kubectl get --export` | 1.35 | Removed | `kubectl get -o yaml`에서 수동 정리 |

### 6.3 인트리 볼륨 플러그인 제거 타임라인

인트리(in-tree) 볼륨 플러그인의 CSI 마이그레이션은 오랫동안 진행되어 왔으며, 1.29~1.36 사이에 대부분이 완료됩니다.

```mermaid
gantt
    title 인트리 볼륨 플러그인 → CSI 마이그레이션 타임라인
    dateFormat  YYYY-MM
    axisFormat  %Y-%m

    section AWS EBS
    CSI Migration GA    :done, ebs, 2022-12, 2023-04
    In-tree Removed     :done, ebs_r, 2023-04, 2023-08

    section GCE PD
    CSI Migration GA    :done, gce, 2022-12, 2023-04
    In-tree Removed     :done, gce_r, 2023-08, 2024-04

    section CephFS/RBD
    Deprecated          :active, ceph_d, 2024-04, 2024-08
    Removed (1.31)      :crit, ceph_r, 2024-08, 2024-12

    section Azure File/Disk
    Deprecated          :active, az_d, 2024-04, 2024-12
    Removed (1.32)      :crit, az_r, 2024-12, 2025-04

    section vSphere
    CSI Migration GA    :done, vs, 2024-04, 2024-08
    In-tree Deprecated  :active, vs_d, 2024-08, 2025-08
```

### 6.4 Deprecation 대응 체크리스트

```bash
# 1. 현재 클러스터에서 사용 중인 Deprecated API 확인
kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis

# 2. API 사용 현황 상세 확인
kubectl get apiservices | grep -v "v1\." | sort

# 3. 제거 예정 API를 사용하는 리소스 검색
# pluto: Kubernetes deprecated API 스캐너
# 설치: brew install FairwindsOps/tap/pluto
pluto detect-all-in-cluster

# 4. Helm 차트에서 Deprecated API 검색
pluto detect-helm -o wide

# 5. 매니페스트 파일에서 Deprecated API 검색
pluto detect-files -d ./manifests/ -o wide

# 출력 예시:
# NAME                KIND                VERSION          REPLACEMENT              REMOVED   DEPRECATED
# my-ingress          Ingress   networking.k8s.io/v1beta1   networking.k8s.io/v1     true      true
```

---

## 7. EKS 특화 고려사항

### 7.1 EKS vs Upstream Kubernetes 버전 차이

Amazon EKS는 upstream Kubernetes를 기반으로 하지만, 매니지드 서비스 특성상 몇 가지 차이가 있습니다.

| 항목 | Upstream Kubernetes | Amazon EKS |
|------|-------------------|------------|
| **릴리스 시점** | upstream 릴리스 즉시 | 2~8주 후 (검증 후) |
| **Feature Gate 제어** | 자유롭게 설정 가능 | AWS가 관리 (Alpha 기능 대부분 비활성) |
| **컨트롤 플레인 접근** | 완전한 접근 | 제한된 접근 (API 서버 endpoint만) |
| **etcd 관리** | 직접 관리 | AWS 관리 (접근 불가) |
| **Cloud Provider 통합** | 별도 설정 필요 | 기본 통합 |
| **CNI** | 선택 가능 | VPC CNI 기본 (다른 CNI 사용 가능) |
| **IAM 통합** | 미지원 | IRSA, EKS Pod Identity |
| **패치 적용** | 수동 | AWS 자동 (컨트롤 플레인) |

### 7.2 EKS에서의 Feature Gate 사용 가능 여부

```
┌──────────────────────────────────────────────────────────────────────┐
│                  EKS Feature Gate 정책                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ✅ GA 기능: 항상 활성화 (Feature Gate locked)                        │
│  ✅ Beta 기능: 기본 활성화 (대부분 사용 가능)                           │
│  ⚠️ Beta (일부): AWS 검증 후 활성화 (upstream보다 늦을 수 있음)         │
│  ❌ Alpha 기능: 일반적으로 비활성화 (사용 불가)                         │
│                                                                      │
│  ※ Alpha 기능이 필요한 경우:                                          │
│     - self-managed 노드에서 kubelet Feature Gate 설정 가능              │
│     - API 서버 Feature Gate는 변경 불가                                │
│     - 테스트 목적이라면 kOps/kubeadm 클러스터 권장                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.3 매니지드 애드온 호환성 매트릭스

EKS 매니지드 애드온은 각 Kubernetes 버전에 대해 지원되는 버전이 정해져 있습니다.

| 애드온 | 1.29 | 1.30 | 1.31 | 1.32 | 1.33 | 1.34 | 1.35 | 1.36 |
|:------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
| **VPC CNI** | 1.16+ | 1.17+ | 1.18+ | 1.19+ | 1.19+ | 1.20+ | 1.20+ | 1.21+ |
| **CoreDNS** | 1.11.1+ | 1.11.1+ | 1.11.3+ | 1.11.3+ | 1.12+ | 1.12+ | 1.12+ | 1.13+ |
| **kube-proxy** | 1.29.x | 1.30.x | 1.31.x | 1.32.x | 1.33.x | 1.34.x | 1.35.x | 1.36.x |
| **EBS CSI** | 1.28+ | 1.30+ | 1.32+ | 1.33+ | 1.34+ | 1.35+ | 1.36+ | 1.37+ |
| **EFS CSI** | 2.0+ | 2.0+ | 2.0+ | 2.1+ | 2.1+ | 2.2+ | 2.2+ | 2.3+ |
| **Mountpoint S3** | 1.4+ | 1.5+ | 1.6+ | 1.7+ | 1.7+ | 1.8+ | 1.8+ | 1.9+ |

> **참고**: 위 버전은 예시이며 실제 지원 버전은 AWS 공식 문서를 참조하세요.

```bash
# 현재 클러스터의 애드온 호환 버전 확인
aws eks describe-addon-versions \
  --kubernetes-version 1.36 \
  --addon-name vpc-cni \
  --query 'addons[].addonVersions[].addonVersion' \
  --output table

# 모든 매니지드 애드온 현재 버전 확인
aws eks list-addons --cluster-name my-cluster --output table
aws eks describe-addon --cluster-name my-cluster --addon-name vpc-cni \
  --query 'addon.{name:addonName,version:addonVersion,status:status}'

# 매니지드 애드온 업데이트
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.21.0-eksbuild.1 \
  --resolve-conflicts OVERWRITE
```

### 7.4 EKS Auto Mode와 버전 관리

EKS Auto Mode는 노드 그룹 관리를 자동화하므로, 버전 업그레이드에서도 특별한 고려가 필요합니다.

```yaml
# EKS Auto Mode 클러스터 업그레이드 설정
# Auto Mode에서는 노드 업그레이드가 자동으로 처리됨
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: auto-mode-cluster
  region: ap-northeast-2
  version: "1.36"         # 대상 버전

autoModeConfig:
  enabled: true

# Auto Mode 클러스터의 업그레이드 프로세스:
# 1. 컨트롤 플레인 업그레이드: aws eks update-cluster-version
# 2. 노드 자동 교체: Auto Mode가 자동으로 새 버전 노드로 교체
# 3. PDB 준수: 워크로드의 PDB를 준수하면서 점진적 교체
```

**Auto Mode 업그레이드 시 주의사항:**

| 항목 | 설명 |
|------|------|
| 컨트롤 플레인 | 수동으로 버전 업그레이드 요청 필요 |
| 노드 | Auto Mode가 자동으로 새 버전 노드로 교체 |
| PDB | PodDisruptionBudget 설정 필수 (안전한 교체 보장) |
| 애드온 | 매니지드 애드온 호환 버전 확인 필요 |
| 커스텀 AMI | Auto Mode에서는 커스텀 AMI 사용 불가 |
| 교체 속도 | NodePool의 `disruption.budgets` 설정으로 제어 |

### 7.5 Extended Support 비용 최적화 전략

Extended Support는 Standard 대비 6배의 비용이 발생하므로, 체계적인 업그레이드 계획이 필수입니다.

```mermaid
flowchart TD
    Start[현재 버전 확인] --> Check{Standard Support<br>종료까지 남은 기간?}
    
    Check -->|6개월 이상| Plan[업그레이드 계획 수립]
    Check -->|3-6개월| Urgent[긴급 업그레이드 계획]
    Check -->|3개월 미만| Critical[⚠️ 즉시 업그레이드 필요]
    Check -->|이미 Extended| Extended[Extended Support 중]
    
    Plan --> Test[비프로덕션 환경 테스트]
    Urgent --> Test
    Critical --> DirectUpgrade[프로덕션 직접 업그레이드]
    
    Extended --> CostCalc[월간 추가 비용 계산]
    CostCalc --> Decision{비용 vs<br>업그레이드 리스크}
    Decision -->|업그레이드| Test
    Decision -->|유지| ExtendedStay[Extended 유지<br>비용 수용]
    
    Test --> Staging[스테이징 업그레이드]
    Staging --> Validate[호환성 검증]
    Validate --> Production[프로덕션 업그레이드]
    DirectUpgrade --> Production
    
    classDef critical fill:#F44336,color:white;
    classDef warning fill:#FF9800,color:white;
    classDef good fill:#4CAF50,color:white;
    
    class Critical critical;
    class Urgent,CostCalc warning;
    class Plan,Production good;
```

**월간 비용 계산 예시:**

```bash
# Extended Support 비용 계산
# Standard: $0.10/cluster/hour
# Extended: $0.60/cluster/hour
# 차이: $0.50/cluster/hour

# 클러스터 수별 월간 추가 비용
# 1 클러스터:  $0.50 × 730시간 = $365/월
# 5 클러스터:  $0.50 × 730시간 × 5 = $1,825/월
# 10 클러스터: $0.50 × 730시간 × 10 = $3,650/월
# 50 클러스터: $0.50 × 730시간 × 50 = $18,250/월

# 1년 Extended Support 유지 시 추가 비용
# 10 클러스터: $3,650 × 12 = $43,800/년
# 50 클러스터: $18,250 × 12 = $219,000/년
```

---

## 8. 버전 업그레이드 계획

### 8.1 업그레이드 사전 점검 체크리스트

```yaml
# 업그레이드 사전 점검 체크리스트
pre_upgrade_checklist:
  
  api_compatibility:
    - name: "Deprecated API 스캔"
      command: "pluto detect-all-in-cluster --target-versions k8s=v1.XX"
      severity: critical
    
    - name: "Helm 차트 Deprecated API 스캔"
      command: "pluto detect-helm --target-versions k8s=v1.XX"
      severity: critical
    
    - name: "CRD apiVersion 확인"
      command: "kubectl get crd -o jsonpath='{range .items[*]}{.metadata.name}: {.spec.versions[*].name}{\"\\n\"}{end}'"
      severity: high
    
    - name: "Admission Webhook 호환성"
      command: "kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations -o yaml"
      severity: high

  feature_gate_impact:
    - name: "새 버전 기본 활성화 Feature Gate 확인"
      description: "Beta에서 GA로 졸업하는 기능은 동작 변경을 유발할 수 있음"
      severity: medium
    
    - name: "제거되는 Feature Gate 확인"
      description: "GA 후 2 릴리스 지나면 Feature Gate가 코드에서 제거됨"
      severity: low

  addon_compatibility:
    - name: "매니지드 애드온 호환 버전 확인"
      command: "aws eks describe-addon-versions --kubernetes-version 1.XX"
      severity: critical
    
    - name: "자체 설치 애드온 호환성"
      items:
        - "Istio/Linkerd 서비스 메시"
        - "Prometheus/Grafana 모니터링 스택"
        - "ArgoCD/Flux GitOps"
        - "Cert-manager"
        - "External DNS"
        - "Ingress Controller (ALB/Nginx)"
      severity: critical

  workload_readiness:
    - name: "PodDisruptionBudget 설정 확인"
      command: "kubectl get pdb --all-namespaces"
      severity: high
    
    - name: "Pod Anti-Affinity 규칙 확인"
      description: "단일 노드에 모든 복제본이 배치되어 있지 않은지 확인"
      severity: medium
    
    - name: "리소스 requests/limits 설정 확인"
      description: "새 버전에서 스케줄링 동작 변경 가능"
      severity: medium

  infrastructure:
    - name: "노드 그룹 AMI 호환성"
      command: "aws ssm get-parameter --name /aws/service/eks/optimized-ami/1.XX/amazon-linux-2023/recommended/image_id"
      severity: critical
    
    - name: "클러스터 오토스케일러 / Karpenter 호환성"
      severity: high
    
    - name: "백업 및 복구 계획"
      items:
        - "etcd 스냅샷 (self-managed인 경우)"
        - "Velero 백업"
        - "GitOps 리포지토리 상태 확인"
      severity: critical
```

### 8.2 단계별 업그레이드 프로세스

```mermaid
flowchart TD
    A[1단계: 사전 준비] --> B[2단계: 비프로덕션 테스트]
    B --> C[3단계: 프로덕션 업그레이드]
    C --> D[4단계: 검증 및 안정화]
    
    subgraph prep["1단계: 사전 준비 (1~2주)"]
        A1[릴리스 노트 검토]
        A2[Deprecated API 스캔]
        A3[애드온 호환성 확인]
        A4[업그레이드 런북 작성]
        A5[롤백 계획 수립]
    end
    
    subgraph test["2단계: 비프로덕션 테스트 (1~2주)"]
        B1[개발 환경 업그레이드]
        B2[기능 테스트 실행]
        B3[성능 테스트 실행]
        B4[카오스 테스트]
        B5[스테이징 환경 업그레이드]
    end
    
    subgraph prod["3단계: 프로덕션 업그레이드 (1~2일)"]
        C1[컨트롤 플레인 업그레이드]
        C2[매니지드 애드온 업데이트]
        C3[노드 그룹 업그레이드]
        C4[자체 관리 애드온 업데이트]
    end
    
    subgraph verify["4단계: 검증 및 안정화 (1주)"]
        D1[워크로드 상태 확인]
        D2[메트릭/알림 모니터링]
        D3[사용자 피드백 수집]
        D4[문서 업데이트]
    end
    
    A --> A1 & A2 & A3 & A4 & A5
    B --> B1 --> B2 --> B3 --> B4 --> B5
    C --> C1 --> C2 --> C3 --> C4
    D --> D1 & D2 & D3 & D4
```

### 8.3 Feature Gate 테스트 방법

새 버전에서 기본 활성화되는 Feature Gate의 영향을 사전에 테스트하는 방법입니다.

```bash
# 1. 현재 버전에서 다음 버전의 기본 활성화 기능 목록 확인
# Kubernetes 릴리스 노트의 Feature Gate 변경 사항 확인
# https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/

# 2. kubelet Feature Gate 테스트 (self-managed 노드)
# /etc/kubernetes/kubelet-config.yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
featureGates:
  InPlacePodVerticalScaling: true    # 사전 테스트할 기능
  SidecarContainers: true

# 3. 테스트 워크로드 배포 후 동작 확인
kubectl apply -f test-workloads/
kubectl get events --watch

# 4. Feature Gate 비활성화 테스트 (특정 기능 문제 시)
# kubelet-config.yaml에서 해당 Feature Gate를 false로 설정
# 주의: EKS에서 API 서버 Feature Gate는 변경 불가
```

### 8.4 API 호환성 검증 스크립트

```bash
#!/bin/bash
# api-compatibility-check.sh
# Kubernetes 업그레이드 전 API 호환성 검증 스크립트

TARGET_VERSION="${1:-1.36}"
echo "=== Kubernetes ${TARGET_VERSION} 업그레이드 API 호환성 검증 ==="

# 1. Deprecated API 스캔
echo ""
echo "--- [1/5] Deprecated API 스캔 ---"
if command -v pluto &> /dev/null; then
    pluto detect-all-in-cluster --target-versions "k8s=v${TARGET_VERSION}" -o wide
else
    echo "pluto가 설치되어 있지 않습니다. 설치: brew install FairwindsOps/tap/pluto"
fi

# 2. 클러스터 내 API 사용 현황
echo ""
echo "--- [2/5] API 사용 현황 ---"
kubectl get --raw /metrics 2>/dev/null | grep apiserver_requested_deprecated_apis | head -20

# 3. Webhook 호환성 확인
echo ""
echo "--- [3/5] Admission Webhook 확인 ---"
echo "ValidatingWebhookConfigurations:"
kubectl get validatingwebhookconfigurations -o custom-columns=NAME:.metadata.name,WEBHOOKS:.webhooks[*].name
echo ""
echo "MutatingWebhookConfigurations:"
kubectl get mutatingwebhookconfigurations -o custom-columns=NAME:.metadata.name,WEBHOOKS:.webhooks[*].name

# 4. CRD API 버전 확인
echo ""
echo "--- [4/5] CRD API 버전 ---"
kubectl get crd -o custom-columns=NAME:.metadata.name,VERSIONS:.spec.versions[*].name | head -30

# 5. 매니지드 애드온 상태
echo ""
echo "--- [5/5] 매니지드 애드온 상태 ---"
CLUSTER_NAME=$(kubectl config current-context | sed 's/.*:cluster\///')
if [ -n "$CLUSTER_NAME" ]; then
    aws eks list-addons --cluster-name "$CLUSTER_NAME" --output text | while read addon; do
        version=$(aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$addon" --query 'addon.addonVersion' --output text 2>/dev/null)
        echo "  $addon: $version"
    done
fi

echo ""
echo "=== 검증 완료 ==="
```

### 8.5 애드온 업그레이드 순서

버전 업그레이드 시 애드온의 올바른 업데이트 순서입니다.

```
┌──────────────────────────────────────────────────────────────────────┐
│                   애드온 업그레이드 순서                                │
│                                                                      │
│  ┌─── Phase 1: 컨트롤 플레인 ────────────────────────────────────┐  │
│  │ 1. EKS 컨트롤 플레인 업그레이드                                  │  │
│  │    aws eks update-cluster-version --name my-cluster              │  │
│  │    --kubernetes-version 1.36                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                          ↓                                          │
│  ┌─── Phase 2: 매니지드 애드온 (순서 중요) ────────────────────────┐  │
│  │ 2. kube-proxy (먼저)                                            │  │
│  │ 3. CoreDNS                                                       │  │
│  │ 4. VPC CNI                                                       │  │
│  │ 5. EBS CSI Driver                                                │  │
│  │ 6. 기타 CSI 드라이버 (EFS, S3)                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                          ↓                                          │
│  ┌─── Phase 3: 노드 그룹 ──────────────────────────────────────┐  │
│  │ 7. Managed Node Group 업그레이드                                │  │
│  │    또는 새 노드 그룹 생성 후 마이그레이션                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                          ↓                                          │
│  ┌─── Phase 4: 자체 관리 애드온 ────────────────────────────────┐  │
│  │ 8. Ingress Controller                                            │  │
│  │ 9. Service Mesh (Istio/Linkerd)                                  │  │
│  │ 10. GitOps (ArgoCD/Flux)                                         │  │
│  │ 11. Monitoring (Prometheus/Grafana)                               │  │
│  │ 12. 기타 (cert-manager, external-dns 등)                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                          ↓                                          │
│  ┌─── Phase 5: 검증 ───────────────────────────────────────────┐  │
│  │ 13. 워크로드 상태 확인                                          │  │
│  │ 14. 네트워킹 연결성 테스트                                       │  │
│  │ 15. 모니터링 대시보드 확인                                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.6 롤백 전략

```yaml
# 업그레이드 롤백 전략
rollback_strategy:
  
  control_plane:
    note: "EKS 컨트롤 플레인은 롤백 불가"
    mitigation:
      - "업그레이드 전 Blue/Green 클러스터 전략 사용"
      - "Route 53 가중치 기반 라우팅으로 트래픽 전환"
      - "새 클러스터로 워크로드 마이그레이션"
    
  node_groups:
    strategy: "새 노드 그룹 생성 + 이전 노드 그룹 유지"
    steps:
      - "이전 버전 노드 그룹을 즉시 삭제하지 않음"
      - "문제 발생 시 이전 노드 그룹에 taint 제거"
      - "새 노드 그룹에 taint 추가하여 트래픽 전환"
    
  workloads:
    strategy: "GitOps 기반 롤백"
    steps:
      - "ArgoCD/Flux에서 이전 커밋으로 롤백"
      - "Helm rollback 실행"
    
  addons:
    strategy: "이전 버전으로 다운그레이드"
    command: |
      aws eks update-addon \
        --cluster-name my-cluster \
        --addon-name vpc-cni \
        --addon-version <previous-version> \
        --resolve-conflicts OVERWRITE
```

### 8.7 업그레이드 자동화 (Terraform 예시)

```hcl
# EKS 클러스터 버전 업그레이드 (Terraform)
resource "aws_eks_cluster" "main" {
  name     = "production-cluster"
  version  = "1.36"    # 대상 버전
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids = var.subnet_ids
  }

  # 업그레이드 정책
  upgrade_policy {
    support_type = "STANDARD"    # 또는 "EXTENDED"
  }
}

# 매니지드 노드 그룹 (버전 자동 추적)
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-ng"
  version         = aws_eks_cluster.main.version    # 클러스터 버전 추적

  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 2
  }

  update_config {
    max_unavailable_percentage = 33    # 한 번에 33%까지만 업데이트
  }
}

# 매니지드 애드온 (버전 호환성 관리)
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  addon_version               = "v1.21.0-eksbuild.1"
  resolve_conflicts_on_update = "OVERWRITE"
  
  # 클러스터 업그레이드 후 애드온 업데이트
  depends_on = [aws_eks_cluster.main]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "kube-proxy"
  addon_version               = "v1.36.0-eksbuild.1"
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_cluster.main]
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "coredns"
  addon_version               = "v1.13.0-eksbuild.1"
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_cluster.main]
}
```

---

## 9. 향후 전망

### 9.1 개발 중인 주요 기능

다음은 현재 개발 중이거나 초기 단계에 있는 기능들로, 향후 릴리스에서 등장할 것으로 예상됩니다.

| 기능 | 현재 상태 | 예상 영향 | 대상 SIG |
|------|----------|----------|----------|
| **Gang Scheduling** | Beta (1.36) | AI/ML 분산 학습의 효율성 대폭 향상 | SIG Scheduling |
| **Pod-level Resources GA** | Beta (1.36) | Sidecar 패턴의 리소스 효율성 향상 | SIG Node |
| **KYAML GA** | Beta (1.35) | YAML 처리 통일 및 보안 강화 | SIG API Machinery |
| **In-Place Resize for DaemonSet** | 논의 중 | DaemonSet 업데이트 시 재시작 감소 | SIG Apps |
| **Multi-Cluster Services** | Alpha | 클러스터 간 서비스 디스커버리 표준화 | SIG Multicluster |
| **Gateway API 1.2+** | GA (별도 CRD) | Ingress를 대체하는 차세대 API | SIG Network |
| **Device Taints/Tolerations** | Alpha (1.35) | DRA 디바이스의 상태 기반 스케줄링 | SIG Node |
| **Mutable Pod Scheduling Directives** | 논의 중 | Pod의 nodeSelector/affinity 동적 변경 | SIG Scheduling |

### 9.2 CNCF 생태계 트렌드

```mermaid
mindmap
  root((CNCF<br>트렌드))
    AI/ML 네이티브
      DRA를 통한 GPU 관리
      Gang Scheduling
      LLM 추론 오토스케일링
      KubeRay/Kueue
    플랫폼 엔지니어링
      Internal Developer Platform
      Backstage
      Crossplane
      Score
    보안 강화
      Supply Chain Security
      Sigstore
      SPIFFE/SPIRE
      VEX/SBOM
    eBPF 확산
      Cilium CNI
      Tetragon 보안
      Falco
      L4/L7 관찰성
    Gateway API
      Ingress 대체
      GAMMA (Mesh)
      gRPC 라우팅
      정책 첨부
    서버리스/Edge
      WASM on Kubernetes
      Spin/Fermyon
      KWasm
      Edge 워크로드
```

### 9.3 AI/ML 워크로드를 위한 Kubernetes 진화 방향

AI/ML 워크로드가 Kubernetes의 핵심 사용 사례로 부상하면서, 관련 기능 개발이 가속화되고 있습니다.

```
┌──────────────────────────────────────────────────────────────────────┐
│              AI/ML을 위한 Kubernetes 진화 로드맵                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  2024-2025: 기반 구축                                                │
│  ├─ DRA Core APIs GA (1.34): GPU 할당 표준화                         │
│  ├─ Gang Scheduling Alpha/Beta (1.35-1.36): 분산 학습 지원            │
│  └─ In-Place Pod Resize GA (1.35): 추론 서버 동적 스케일링            │
│                                                                      │
│  2026: 성숙 단계                                                      │
│  ├─ Gang Scheduling GA (예상 1.37)                                   │
│  ├─ Device Taints GA: GPU 장애 자동 감지 및 회피                      │
│  ├─ Multi-NIC 지원 강화: RDMA/InfiniBand 네이티브 지원               │
│  └─ Topology-Aware Scheduling 고도화: GPU-GPU 토폴로지 최적화         │
│                                                                      │
│  2027+: 전망                                                          │
│  ├─ ML-Aware Scheduler: 학습/추론 워크로드 전용 스케줄러               │
│  ├─ Federated Training: 멀티 클러스터 분산 학습                        │
│  └─ LLM-Native Autoscaling: 토큰/요청 기반 자동 스케일링              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 9.4 업그레이드 로드맵 계획 템플릿

현재 운영 중인 클러스터의 업그레이드 계획을 수립하기 위한 템플릿입니다.

```yaml
# 업그레이드 로드맵 계획 템플릿
upgrade_roadmap:
  current_state:
    cluster_version: "1.33"
    node_count: 50
    workload_count: 200
    critical_addons:
      - name: "istio"
        version: "1.22"
      - name: "argocd"
        version: "2.11"
      - name: "prometheus-stack"
        version: "60.0"
  
  target_version: "1.36"
  upgrade_path: "1.33 → 1.34 → 1.35 → 1.36"
  # 주의: 건너뛰기 업그레이드(skip version)는 지원되지 않음
  
  phase_1:  # 1.33 → 1.34
    target: "1.34"
    timeline: "2025년 11월"
    key_changes:
      - "DRA Core APIs GA 활용 시작"
      - "VolumeAttributesClass GA 활용"
      - "nftables kube-proxy 기본 전환"
    risks:
      - "iptables → nftables 전환 시 네트워크 정책 검증 필요"
      - "DRA 관련 CRD 설치/업데이트 필요"
    
  phase_2:  # 1.34 → 1.35
    target: "1.35"
    timeline: "2026년 3월"
    key_changes:
      - "In-Place Pod Resize GA 활용"
      - "VPA In-Place 모드 도입"
      - "KYAML Beta 영향 검증"
    risks:
      - "KYAML로 인한 매니페스트 파싱 변경 확인"
      - "In-Place Resize가 기존 리소스 관리와 충돌하지 않는지 확인"
    
  phase_3:  # 1.35 → 1.36
    target: "1.36"
    timeline: "2026년 7월"
    key_changes:
      - "Pod-level Resources Beta 테스트"
      - "Gang Scheduling Beta 활용"
    risks:
      - "Pod-level Resources와 기존 LimitRange/ResourceQuota 상호작용 검증"
```

---

## 10. 참고 자료

### 공식 문서

| 자료 | URL | 설명 |
|------|-----|------|
| Kubernetes 릴리스 | https://kubernetes.io/releases/ | 릴리스 일정 및 이력 |
| 변경 로그 | https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/ | 상세 변경 로그 |
| Feature Gates | https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/ | Feature Gate 전체 목록 |
| API Deprecation 정책 | https://kubernetes.io/docs/reference/using-api/deprecation-policy/ | Deprecation 규칙 |
| KEP 목록 | https://github.com/kubernetes/enhancements/tree/master/keps | Enhancement 제안 |

### Amazon EKS 문서

| 자료 | URL | 설명 |
|------|-----|------|
| EKS 버전 정책 | https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html | EKS 지원 버전 |
| EKS 릴리스 노트 | https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-release-notes.html | 버전별 릴리스 노트 |
| EKS 업그레이드 | https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html | 업그레이드 가이드 |
| Extended Support | https://docs.aws.amazon.com/eks/latest/userguide/extended-support.html | Extended Support 상세 |
| 매니지드 애드온 | https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html | 애드온 관리 |

### 커뮤니티 도구

| 도구 | URL | 용도 |
|------|-----|------|
| pluto | https://github.com/FairwindsOps/pluto | Deprecated API 스캐너 |
| kubent | https://github.com/doitintl/kube-no-trouble | Deprecated API 탐지 |
| kube-score | https://github.com/zegl/kube-score | 매니페스트 품질 검사 |
| nova | https://github.com/FairwindsOps/nova | Helm 차트 업데이트 감지 |
| kubectl-convert | https://kubernetes.io/docs/tasks/tools/install-kubectl/ | API 버전 변환 |

### 버전별 블로그 포스트

| 버전 | 공식 블로그 |
|------|-----------|
| 1.29 | https://kubernetes.io/blog/2023/12/13/kubernetes-v1-29-release/ |
| 1.30 | https://kubernetes.io/blog/2024/04/17/kubernetes-v1-30-release/ |
| 1.31 | https://kubernetes.io/blog/2024/08/13/kubernetes-v1-31-release/ |
| 1.32 | https://kubernetes.io/blog/2024/12/11/kubernetes-v1-32-release/ |
| 1.33 | https://kubernetes.io/blog/2025/04/23/kubernetes-v1-33-release/ |
| 1.34 | https://kubernetes.io/blog/2025/08/kubernetes-v1-34-release/ |
| 1.35 | https://kubernetes.io/blog/2025/12/kubernetes-v1-35-release/ |
| 1.36 | https://kubernetes.io/blog/2026/04/kubernetes-v1-36-release/ |

---

## 다음 단계

- [EKS 업그레이드](08-eks-upgrades.md): EKS 클러스터 업그레이드 실전 가이드
- [EKS 문제 해결](09-eks-troubleshooting.md): 업그레이드 중 발생하는 문제 해결
- [EKS 고급 디버깅](11-eks-advanced-debugging.md): 업그레이드 후 디버깅 기법
- [EKS 비용 최적화](07-eks-cost-optimization.md): Extended Support 비용 관리 전략
