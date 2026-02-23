# EKS Auto Mode 운영자 교육 커리큘럼 (2시간)

> **대상**: EKS 클러스터를 운영하는 인프라/플랫폼 엔지니어
> **전제 조건**: Kubernetes 기본 개념, EKS 운영 경험
> **마지막 업데이트**: 2026년 2월 23일

---

## 교육 목표

1. EKS Auto Mode의 Karpenter 기반 내부 아키텍처를 이해한다
2. NodePool/NodeClass 설계로 워크로드별 리소스 최적화 전략을 수립할 수 있다
3. Spot + Graviton 조합으로 비용을 60~90% 절감하는 방법을 습득한다
4. Observability 스택(Prometheus/Loki/Tempo/Grafana)을 활용한 운영 모니터링 방법을 익힌다

---

## 커버리지 분석 — 기존 가이드 평가

교육 요청 주제별로 기존 kubernetes-docs 가이드의 커버리지를 평가했습니다.

| 주제 | 커버리지 | 평가 | 참조 문서 |
|------|---------|------|----------|
| Terraform / Terragrunt | Terraform 충분, Terragrunt 부족 | Terraform 3-Layer 아키텍처 상세 문서 있음. Terragrunt는 5회 간략 언급만 | [ops/01-infrastructure-setup.md](../ops/01-infrastructure-setup.md) |
| ArgoCD | 매우 충분 | 9개 파일 멀티파일 구조 (설치~모범사례) | [gitops/argocd/](../gitops/argocd/README.md) |
| EKS Auto Mode 내부 구조 | 충분 | Karpenter 기반 아키텍처, NodePool, NodeClass 상세 | [eks-auto-mode/](../eks-auto-mode/README.md) (10개 문서) |
| EKS Auto Mode 리소스 최적화 | 충분 | 비용 관리, Spot 전략, VPA, bin-packing | [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) |
| Grafana Loki | 충분 | ~1,344줄 상세 문서 (아키텍처, LogQL, 성능 튜닝) | [observability/logging/01-loki.md](../observability/logging/01-loki.md) |
| Prometheus / Grafana | 충분 | Prometheus ~1,446줄, Grafana ~1,026줄 | [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md), [observability/grafana/README.md](../observability/grafana/README.md) |
| Amazon Managed Prometheus | 양호 | Prometheus 문서 내 Remote Write + AMP 연동 섹션 | [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) |
| Grafana Tempo | 충분 | ~1,051줄 상세 문서 (TraceQL, S3 백엔드, 상관관계) | [observability/tracing/01-tempo.md](../observability/tracing/01-tempo.md) |
| 노드 가용성/Termination 모니터링 | 부분적 | 여러 문서에 분산, 통합 트러블슈팅 가이드 부재 | [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md) |
| Logs/Metrics/Traces 데이터 연결 | 충분 | 3대 축 상관관계, Exemplars, TraceID 연결 | [observability/09-observability-optimization.md](../observability/09-observability-optimization.md) |

### 갭 요약

| 갭 | 영향도 | 대응 방안 |
|----|--------|----------|
| Terragrunt 전용 가이드 없음 | 중 | 운영팀이 Terragrunt 사용 중이면 별도 문서 작성 검토 |
| 노드 Termination 통합 모니터링 가이드 부재 | 중 | Spot 중단 감지 → CloudWatch → Prometheus Alert → Grafana 흐름을 슬라이드로 정리 |
| eks-auto-mode 실습 Lab 없음 | 하 | NodePool 변경 → Consolidation 관찰 실습 시나리오 추가 검토 |

---

## 전체 구성 (120분)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Part 1: Auto Mode 내부 구조 이해                          (40분)  │
├─────────────────────────────────────────────────────────────────────┤
│  Part 2: 리소스 최적화 전략                                (35분)  │
├─────────────────────────────────────────────────────────────────────┤
│  Break: 휴식                                               (10분)  │
├─────────────────────────────────────────────────────────────────────┤
│  Part 3: 운영 모니터링 — Observability 스택 연계           (25분)  │
├─────────────────────────────────────────────────────────────────────┤
│  Part 4: IaC + GitOps 운영 워크플로우                      (10분)  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Auto Mode 내부 구조 이해 (40분)

**학습 목표**: Karpenter 기반 Auto Mode가 노드를 어떻게 프로비저닝하고 관리하는지 내부 동작을 이해한다.

### 1-1. 아키텍처 개요 (10분)

**참조 문서**: [eks-auto-mode/README.md](../eks-auto-mode/README.md), [01-getting-started.md](../eks-auto-mode/01-getting-started.md)

**핵심 내용**:

- **Karpenter가 EKS 제어 플레인에 내장** — 별도 설치/관리 불필요
- 기존 관리 방식(MNG, Self-managed)과의 아키텍처 비교

```
EKS Control Plane (AWS 관리)
├── API Server
├── etcd
├── Controller Manager
└── Karpenter Controller  ← Auto Mode 핵심

NodePool 리소스
├── general-purpose (기본 제공)
├── system (기본 제공)
└── custom-pool (사용자 정의)

EC2 인스턴스 (자동 관리)
├── m6i.2xl (On-Demand)
├── c7g.xl (Spot)
└── r6i.4xl (On-Demand)
```

**강조 포인트**:
- Auto Mode = "Karpenter as a Service" — 운영자는 NodePool CRD만 관리
- 기본 NodePool 2개(general-purpose, system)가 자동 생성됨
- eksctl, Terraform, AWS CDK 모두 활성화 가능

---

### 1-2. NodePool & NodeClass 심층분석 (15분)

**참조 문서**: [02-nodepool-configuration.md](../eks-auto-mode/02-nodepool-configuration.md)

**핵심 내용**:

- **기본 NodePool** 구성 이해 (general-purpose, system)
- **커스텀 NodePool 설계** 전략
- AMI 패밀리 선택: AL2023 vs Bottlerocket
- `requirements` 구문으로 인스턴스 타입 제어

**실습 예시** — 커스텀 NodePool 정의:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]           # 범용/컴퓨팅 최적화
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]                # 6세대 이상만
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

**강조 포인트**:
- `requirements` 문법이 인스턴스 선택의 핵심 — `In`, `NotIn`, `Gt`, `Lt` 연산자
- NodeClass는 Auto Mode에서 AWS 관리 (`eks.amazonaws.com` 그룹)
- 워크로드 특성별 NodePool 분리가 최적화의 첫걸음

---

### 1-3. 스케일링 동작 원리 (15분)

**참조 문서**: [03-scaling-behavior.md](../eks-auto-mode/03-scaling-behavior.md)

**핵심 내용**:

- **Pod→Node 프로비저닝 흐름**: Pending 감지 → NodePool 평가 → 인스턴스 선택 → 프로비저닝 (40~90초)
- **Consolidation 정책**: 비용 최적화의 핵심 메커니즘
- **Drift 감지**: 설정 변경 시 자동 노드 교체

**Consolidation 정책 비교**:

| 정책 | 동작 | 적합한 환경 |
|------|------|------------|
| `WhenEmpty` | 빈 노드만 제거 | 안정성 우선 (프로덕션) |
| `WhenEmptyOrUnderutilized` | 빈 노드 + 저활용 노드 통합 | 비용 우선 (개발/스테이징) |

**강조 포인트**:
- Consolidation이 자동으로 bin-packing 수행 → 수동 최적화 불필요
- `consolidateAfter`로 민감도 조절 (1m = 공격적, 30m = 보수적)
- Drift 감지로 NodePool 변경 시 점진적 롤링 교체 자동화

---

## Part 2: 리소스 최적화 전략 (35분)

**학습 목표**: 실무에서 바로 적용할 수 있는 비용 절감 및 리소스 효율화 전략을 습득한다.

### 2-1. Spot 인스턴스 전략 (10분)

**참조 문서**: [04-spot-strategies.md](../eks-auto-mode/04-spot-strategies.md)

**핵심 내용**:

- **다양화 전략**: 인스턴스 패밀리/세대/사이즈를 넓게 지정하여 Spot 가용성 확보
- **중단 처리**: Karpenter가 자동으로 대체 노드 프로비저닝
- **On-Demand 혼합**: 핵심 워크로드는 On-Demand, 비핵심은 Spot

```yaml
# Spot 전용 NodePool 예시
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]      # 다양한 패밀리
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]                # 다양한 세대
```

**강조 포인트**:
- Spot은 On-Demand 대비 **60~90% 절감** 가능
- 다양화가 핵심 — 특정 인스턴스 타입에 의존하면 가용성 문제 발생
- `do-not-disrupt` 어노테이션으로 특정 Pod 보호 가능

---

### 2-2. 비용 관리 (10분)

**참조 문서**: [06-cost-management.md](../eks-auto-mode/06-cost-management.md)

**핵심 내용**:

- **Graviton/ARM**: 동일 성능 대비 **~20% 비용 절감**
- **Savings Plans**: Compute Savings Plans으로 Auto Mode와 연동
- **비용 귀속**: Kubecost + 태그 기반 팀별 비용 할당
- **최적화 체크리스트**: 즉시 적용 가능한 항목 목록

**비용 절감 누적 효과**:

```
기준 비용 (On-Demand x86)          : $1,000/월
├── Spot 적용 (60% 절감)           : $400/월
├── Graviton 전환 (20% 추가 절감)  : $320/월
└── Consolidation 최적화 (15% 절감): $272/월
                                     ─────────
                                     ~73% 절감
```

**강조 포인트**:
- Graviton 인스턴스는 `kubernetes.io/arch: arm64` requirement로 지정
- 비용 모니터링 없이 최적화는 불가능 — Kubecost 또는 AWS Cost Explorer 필수
- Savings Plans은 인스턴스 타입이 아닌 Compute 단위로 구매해야 Auto Mode와 호환

---

### 2-3. 워크로드별 최적화 (10분)

**참조 문서**: [08-workload-optimization.md](../eks-auto-mode/08-workload-optimization.md)

**핵심 내용**:

- **웹 서비스**: HPA + Spot 혼합, 가용영역 분산
- **배치 처리**: Spot 전용 NodePool, 큰 인스턴스 선호
- **GPU/AI/ML**: 전용 NodePool, 인스턴스 타입 고정(p/g 패밀리)
- **VPA 연동**: 리소스 요청값 자동 Right-sizing

**워크로드 티어별 NodePool 분리 패턴**:

| 워크로드 | NodePool | Capacity Type | 인스턴스 카테고리 |
|---------|----------|---------------|----------------|
| 시스템 (CoreDNS 등) | system | On-Demand | m, c |
| 웹 서비스 | web-tier | On-Demand + Spot | m, c, r |
| 배치 처리 | batch | Spot 전용 | m, c, r (큰 사이즈) |
| GPU 워크로드 | gpu | On-Demand | p, g |

**강조 포인트**:
- NodePool을 워크로드 티어별로 분리하는 것이 최적화의 기본
- Pod의 `nodeSelector` 또는 `nodeAffinity`로 NodePool 매핑
- VPA의 `updateMode: Off`로 권장값만 확인 후 수동 적용 권장 (프로덕션)

---

### 2-4. 노드 라이프사이클 (5분)

**참조 문서**: [07-node-lifecycle.md](../eks-auto-mode/07-node-lifecycle.md)

**핵심 내용**:

- `expireAfter` 정책으로 노드 최대 수명 제한
- AMI 업데이트 자동화 — Drift 감지로 새 AMI 자동 적용
- Disruption Budget으로 동시 교체 노드 수 제한

**강조 포인트**:
- `expireAfter: 720h` (30일)이 일반적인 프로덕션 설정
- Disruption Budget: `nodes: "10%"` → 전체 노드의 10%만 동시 중단 허용
- 유지보수 윈도우 설정으로 업무 시간 외에만 노드 교체 가능

---

## 휴식 (10분)

---

## Part 3: 운영 모니터링 — Observability 스택 연계 (25분)

**학습 목표**: Auto Mode 환경에서 노드 가용성 모니터링과 Logs/Metrics/Traces 연계 방법을 익힌다.

### 3-1. 노드 모니터링 (8분)

**참조 문서**: [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md), [observability/09-observability-optimization.md](../observability/09-observability-optimization.md)

**핵심 내용**:

- Auto Mode 노드 상태 확인 방법 (`kubectl get nodeclaims`)
- Spot 중단 감지: CloudWatch Events → EventBridge → SNS/Lambda
- Prometheus 알림 규칙:

```yaml
# 핵심 노드 알림 규칙
groups:
  - name: node-health
    rules:
      - alert: NodeNotReady
        expr: kube_node_status_condition{condition="Ready",status="true"} == 0
        for: 5m
      - alert: NodeMemoryPressure
        expr: kube_node_status_condition{condition="MemoryPressure",status="true"} == 1
        for: 2m
      - alert: NodePoolNearCapacity
        expr: |
          count(karpenter_nodeclaims_state{state="launched"})
          / karpenter_nodepool_usage_limit > 0.8
        for: 10m
```

**강조 포인트**:
- Auto Mode에서는 **노드 SSH 접근 불가** → Observability 스택 의존도 높음
- `karpenter_*` 메트릭으로 NodePool 상태, 프로비저닝 지연, Consolidation 활동 모니터링
- Disruption Budget 설정이 Spot 중단 시 안전망 역할

---

### 3-2. 3 Pillars 연계 활용법 (8분)

**참조 문서**: [observability/09-observability-optimization.md](../observability/09-observability-optimization.md), [observability/grafana/README.md](../observability/grafana/README.md)

**핵심 내용**:

- **TraceID 기반 Logs↔Traces 연결**: Loki에서 TraceID로 Tempo 트레이스 조회
- **Exemplars로 Metrics→Traces 연결**: Prometheus 메트릭에서 관련 트레이스로 직접 이동
- **Grafana 통합 대시보드**: 하나의 대시보드에서 세 데이터 소스를 연결

```
문제 분석 흐름:

  Metrics (알람 발생)
      │
      ▼
  Logs (원인 파악)
      │
      ▼
  Traces (영향 범위 확인)
```

**Grafana 데이터 소스 연결 설정**:

```yaml
# Grafana datasource 설정 (핵심)
datasources:
  - name: Tempo
    type: tempo
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        tags: ['service.name']
      tracesToMetrics:
        datasourceUid: prometheus
```

**강조 포인트**:
- `tracesToLogs`, `tracesToMetrics` 설정이 데이터 소스 간 연결의 핵심
- Loki label에 `traceID`를 포함해야 역방향 조회(Logs→Traces) 가능
- Exemplars 활성화: Prometheus `--enable-feature=exemplar-storage`

---

### 3-3. 실전 트러블슈팅 시나리오 (9분)

**참조 문서**: [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md) (트러블슈팅 섹션)

#### 시나리오 1: "Pod가 Pending인데 노드가 안 생긴다"

```
확인 순서:
1. kubectl get nodeclaims → NodeClaim 상태 확인
2. kubectl describe nodepool → NodePool limits 확인
3. Karpenter 메트릭 → karpenter_provisioner_scheduling_duration
4. CloudTrail → EC2 RunInstances 호출 실패 여부
5. 원인: 보통 인스턴스 용량 부족 또는 서브넷 IP 고갈
```

#### 시나리오 2: "노드가 갑자기 사라졌다"

```
확인 순서:
1. kubectl get events → NodeClaim 삭제 이벤트
2. Karpenter 로그 → Consolidation/Drift/Expiry 중 어떤 이유인지
3. CloudWatch Events → Spot 중단 알림 확인
4. Grafana 대시보드 → 해당 시점 노드 수 변화 그래프
5. 원인: Consolidation, Spot 중단, expireAfter 만료 중 하나
```

#### 시나리오 3: "응답 지연이 발생한다"

```
확인 순서:
1. Prometheus → RED 메트릭 (Rate, Errors, Duration) 확인
2. Grafana 대시보드 → 해당 서비스 p99 레이턴시 그래프
3. Tempo → 느린 트레이스 조회 (duration > 1s)
4. Loki → 해당 TraceID로 관련 로그 조회
5. 노드 메트릭 → CPU/Memory 압박 여부 확인
```

**강조 포인트**:
- 문제 유형에 따라 **시작점이 다름**: 인프라 문제는 Metrics부터, 애플리케이션 문제는 Traces부터
- `kubectl get nodeclaims`가 Auto Mode 환경의 첫 번째 디버깅 도구
- CloudTrail 로그가 "왜 노드가 안 생기는지"의 최종 답을 줌

---

## Part 4: IaC + GitOps 운영 워크플로우 (10분)

**학습 목표**: Auto Mode 클러스터의 인프라 관리 및 배포 파이프라인 운영 방법을 이해한다.

### 4-1. Terraform 3-Layer 아키텍처 (5분)

**참조 문서**: [ops/01-infrastructure-setup.md](../ops/01-infrastructure-setup.md)

**핵심 내용**:

```
Terraform 3-Layer 구조:

Layer 0: 00-shared     → 공통 설정 (backend.tf, variables.tf)
Layer 1: 01-network    → VPC, 서브넷, NAT Gateway
Layer 2: 02-cluster    → EKS Auto Mode 클러스터 + NodePool
Layer 3: 03-platform   → Add-ons, Pod Identity, IRSA
```

**강조 포인트**:
- Layer 분리 → Blast radius 최소화 (네트워크 변경이 클러스터에 영향 안 줌)
- Auto Mode 활성화는 `02-cluster` Layer에서 `compute_config` 블록으로 설정
- Layer별 독립적 `terraform apply` 가능 → 팀 간 병렬 작업

---

### 4-2. ArgoCD 운영 (5분)

**참조 문서**: [gitops/argocd/02-applications.md](../gitops/argocd/02-applications.md), [gitops/argocd/04-applicationsets.md](../gitops/argocd/04-applicationsets.md)

**핵심 내용**:

- **App of Apps 패턴**: 하나의 루트 Application이 하위 Application들을 관리
- **ApplicationSet**: Generator를 사용한 멀티 클러스터 자동 배포
- **Sync Strategy**: Auto Sync + Self-Heal + Prune으로 GitOps 자동화

**강조 포인트**:
- NodePool 정의도 Git에서 관리 → ArgoCD로 자동 배포 가능
- ApplicationSet의 `Git Generator`로 디렉토리 구조 기반 자동 Application 생성
- Progressive Sync로 클러스터별 단계적 롤아웃

---

## 강의 후 평가

각 파트에 대응하는 퀴즈가 준비되어 있습니다:

| 파트 | 퀴즈 파일 |
|------|----------|
| Part 1-1 | [quizzes/eks-auto-mode/01-getting-started-quiz.md](../quizzes/eks-auto-mode/01-getting-started-quiz.md) |
| Part 1-2 | [quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md](../quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md) |
| Part 1-3 | [quizzes/eks-auto-mode/03-scaling-behavior-quiz.md](../quizzes/eks-auto-mode/03-scaling-behavior-quiz.md) |
| Part 2-1 | [quizzes/eks-auto-mode/04-spot-strategies-quiz.md](../quizzes/eks-auto-mode/04-spot-strategies-quiz.md) |
| Part 2-2 | [quizzes/eks-auto-mode/06-cost-management-quiz.md](../quizzes/eks-auto-mode/06-cost-management-quiz.md) |
| Part 2-3 | [quizzes/eks-auto-mode/08-workload-optimization-quiz.md](../quizzes/eks-auto-mode/08-workload-optimization-quiz.md) |
| Part 2-4 | [quizzes/eks-auto-mode/07-node-lifecycle-quiz.md](../quizzes/eks-auto-mode/07-node-lifecycle-quiz.md) |
| Part 3 | [quizzes/eks-auto-mode/05-operations-quiz.md](../quizzes/eks-auto-mode/05-operations-quiz.md) |

---

## 강의 준비 시 보완 권장 사항

### 반드시 준비 (강의 전)

1. **Auto Mode 노드 모니터링 통합 슬라이드** — Spot Termination 감지 → CloudWatch Event → Prometheus Alert → Grafana Dashboard 순서를 하나의 흐름으로 정리
   - 소스: [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md) 모니터링 섹션
   - 소스: [observability/09-observability-optimization.md](../observability/09-observability-optimization.md)

### 선택적 보완

2. **Terragrunt 전용 가이드** — 운영팀이 Terragrunt를 사용 중이라면 별도 문서 작성 검토 (현재 5회 간략 언급만 존재)
3. **실습 Lab** — `eks-auto-mode/` 관련 hands-on lab이 현재 없음:
   - NodePool 변경 → Consolidation 관찰
   - Spot 중단 시뮬레이션 (`aws fis` 활용)
   - Karpenter 메트릭 대시보드 구축

---

## 추가 학습 자료

이 커리큘럼에서 다루지 못한 심화 주제:

| 주제 | 참조 문서 |
|------|----------|
| MNG에서 Auto Mode 마이그레이션 | [eks-auto-mode/09-migration-guide.md](../eks-auto-mode/09-migration-guide.md) |
| FluxCD 비교 | [gitops/02-fluxcd.md](../gitops/02-fluxcd.md) |
| Prometheus Operator (ServiceMonitor/PodMonitor) | [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) |
| Loki LogQL 심화 | [observability/logging/01-loki.md](../observability/logging/01-loki.md) |
| Tempo TraceQL 심화 | [observability/tracing/01-tempo.md](../observability/tracing/01-tempo.md) |
| Alertmanager 설정 | [observability/alerting/01-alertmanager.md](../observability/alerting/01-alertmanager.md) |

---

## 검증 체크리스트

- [x] `ko/eks-auto-mode/` 디렉토리 — 10개 문서 확인 (9개 + 09-migration-guide.md)
- [x] `ko/observability/09-observability-optimization.md` — 3 Pillars 연계 섹션 확인
- [x] `ko/ops/01-infrastructure-setup.md` — Terraform 3-Layer + Auto Mode 설정 확인
- [x] `ko/quizzes/eks-auto-mode/` — 9개 퀴즈 파일로 강의 후 평가 가능
- [x] `ko/observability/grafana/README.md` — 데이터 소스 연결 설정 확인
- [x] `ko/gitops/argocd/` — 10개 문서 (README + 01~09) 확인
