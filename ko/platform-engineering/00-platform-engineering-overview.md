# Platform Engineering 개요

> **마지막 업데이트**: 2025년 2월

## 1. Platform Engineering이란?

### 정의

Platform Engineering은 **개발자 셀프서비스를 위한 도구, 워크플로우, 인프라를 설계하고 구축하며 운영하는 분야**입니다. 플랫폼 엔지니어링 팀은 개발자가 인프라의 복잡성을 직접 다루지 않고도 애플리케이션을 빠르고 안전하게 배포할 수 있도록 **Internal Developer Platform(IDP)**을 구축합니다.

### Internal Developer Platform (IDP)

IDP는 개발자가 코드 작성에 집중할 수 있도록 인프라 프로비저닝, 배포, 모니터링 등의 운영 작업을 추상화한 셀프서비스 플랫폼입니다.

**IDP의 핵심 가치:**

- **셀프서비스**: 개발자가 티켓 없이 직접 인프라를 프로비저닝
- **가드레일**: 보안과 규정 준수를 기본으로 내장
- **표준화**: Golden Path를 통한 일관된 배포 패턴
- **자동화**: 반복 작업의 제거를 통한 인지 부하 감소

### Platform Engineering vs DevOps vs SRE

| 구분 | Platform Engineering | DevOps | SRE |
|------|---------------------|--------|-----|
| **초점** | 개발자 경험과 셀프서비스 플랫폼 구축 | 개발과 운영의 문화적 통합 | 서비스 신뢰성과 운영 자동화 |
| **핵심 산출물** | Internal Developer Platform | CI/CD 파이프라인, 자동화 스크립트 | SLO/SLI, 에러 버짓, 토일 자동화 |
| **주요 메트릭** | 개발자 생산성, 온보딩 시간 | 배포 빈도, 리드 타임 | 가용성, 에러 버짓 소비율 |
| **팀 구조** | 전담 플랫폼 팀 | 크로스 펑셔널 팀 | SRE 팀 또는 임베디드 SRE |
| **관계** | DevOps + SRE 위에 제품화 계층 | 문화와 방법론 | 운영 엔지니어링 실천 |

> **참고**: 세 가지 접근법은 상호 배타적이 아니라 보완적입니다. Platform Engineering은 DevOps 원칙과 SRE 관행을 **제품으로 패키징**하는 것입니다.

### 플랫폼 팀의 역할과 구성

**핵심 역할:**

| 역할 | 책임 |
|------|------|
| **플랫폼 프로덕트 매니저** | 개발자 요구 분석, IDP 로드맵 관리, 성공 메트릭 정의 |
| **플랫폼 엔지니어** | IDP 핵심 인프라 구축, Kubernetes/클라우드 자동화 |
| **플랫폼 SRE** | 플랫폼 자체의 신뢰성, 모니터링, 인시던트 대응 |
| **개발자 경험(DX) 엔지니어** | CLI 도구, 문서화, 온보딩 워크플로우 |

---

## 2. AWS CAF 플랫폼 관점 (Platform Perspective)

### AWS Cloud Adoption Framework 소개

[AWS Cloud Adoption Framework(CAF)](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)은 클라우드 도입을 위한 조직적 가이드라인을 제공합니다. **플랫폼 관점(Platform Perspective)**은 세 가지 핵심 영역을 다룹니다:

1. **Platform Engineering** -- 이 섹션의 초점
2. **Platform Architecture** -- 클라우드 아키텍처 설계 원칙
3. **Data Architecture** -- 데이터 관리 및 분석 전략

### 성숙도 모델: START → ADVANCE → EXCEL

AWS CAF는 클라우드 플랫폼 성숙도를 세 단계로 정의합니다. 각 단계에서 Kubernetes 생태계의 도구가 어떻게 매핑되는지 살펴봅니다.

#### START: 기반 구축

기초 인프라를 수립하고 보안 가드레일을 설정하는 단계입니다.

| 역량 | 설명 | Kubernetes 생태계 매핑 |
|------|------|----------------------|
| **랜딩 존 & 가드레일** | 멀티 어카운트 환경, 예방적/탐지적 통제 | EKS 클러스터 구성, [OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **인증** | 중앙 집중식 ID 관리, IdP 연동 | [K8s 인증 및 권한 부여](../security/02-kubernetes-auth-authz.md), OIDC, IRSA |
| **네트워크** | 중앙 집중식 네트워크 관리 | VPC CNI, [Calico](../networking/03-calico.md), [Cilium](../networking/01-cilium.md) |
| **로깅** | 크로스 어카운트 관측성 | [Prometheus](../observability/metrics/01-prometheus.md), [Loki](../observability/logging/01-loki.md), [OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **통제** | 프로그래밍 방식의 보안 통제 | [Pod Security Standards](../security/03-pod-security-standards.md), [네트워크 정책](../security/04-network-policies.md) |
| **비용 관리** | 태깅 전략, 비용 할당 | 리소스 쿼터, LimitRange, [EKS 비용 최적화](../eks/07-eks-cost-optimization.md) |

#### ADVANCE: 운영 확장

자동화를 확대하고 중앙 관측성을 구축하는 단계입니다.

| 역량 | 설명 | Kubernetes 생태계 매핑 |
|------|------|----------------------|
| **인프라 자동화** | IaC, 셀프서비스 제품 | [ACK](./02-ack.md), [KRO](./03-kro.md), Crossplane, [Helm](./01-helm.md) |
| **중앙 관측성** | 로그/메트릭/트레이스 상관관계 | [Grafana](../observability/grafana/README.md) 스택, [CloudWatch](../observability/metrics/04-cloudwatch-metrics.md) |
| **시스템 관리** | 이미지 표준화, 패치 관리 | [이미지 보안](../security/07-image-security.md), [Kyverno](../security/01-kyverno-policy-management.md) |
| **자격 증명 관리** | 임시 자격 증명, 자동 교체 | [시크릿 관리](../security/05-secrets-management.md), IRSA |
| **보안 도구** | XDR, 세분화된 모니터링 | [런타임 보안](../security/08-runtime-security.md), Trivy, GuardDuty |

#### EXCEL: 지속적 최적화

자동화된 거버넌스와 지속적 개선을 달성하는 단계입니다.

| 역량 | 설명 | Kubernetes 생태계 매핑 |
|------|------|----------------------|
| **자동화된 ID 관리** | IaC로 역할/정책 버전 관리 | [GitOps](../gitops/README.md) 기반 RBAC 관리 |
| **이상 탐지** | 취약점 사전 평가, 이상 패턴 감지 | [런타임 보안](../security/08-runtime-security.md) (Falco), 감사 로그 분석 |
| **위협 분석** | 산업 벤치마크 대비 지속적 모니터링 | CIS Benchmark, kube-bench |
| **권한 정제** | 최소 권한 원칙 자동화 | K8s audit log 기반 RBAC 최적화 |
| **플랫폼 메트릭** | 조직 목표 정렬 메트릭 | DORA 메트릭, SLI/SLO |

---

## 3. IDP 참조 아키텍처

### Kubernetes 기반 IDP 계층 구조

```
┌─────────────────────────────────────────────────────┐
│              개발자 인터페이스 계층                    │
│      (Backstage, Port, CLI, GitOps UI)               │
├─────────────────────────────────────────────────────┤
│            통합/오케스트레이션 계층                    │
│      (ArgoCD, FluxCD, Crossplane, KRO)               │
├─────────────────────────────────────────────────────┤
│                리소스 계층                            │
│      (ACK, Helm Charts, Operators, CRDs)             │
├─────────────────────────────────────────────────────┤
│                인프라 계층                            │
│      (EKS, VPC, IAM, S3, RDS, ...)                   │
└─────────────────────────────────────────────────────┘
```

### 각 계층의 역할과 도구 매핑

| 계층 | 역할 | 주요 도구 | 이 레포 문서 |
|------|------|----------|------------|
| **개발자 인터페이스** | 개발자가 상호작용하는 UI/CLI | Backstage, Port, Argo Workflows UI | - |
| **통합/오케스트레이션** | 선언적 상태 관리, 배포 자동화 | ArgoCD, FluxCD, KRO | [GitOps](../gitops/README.md), [KRO](./03-kro.md) |
| **리소스** | 클라우드/K8s 리소스의 추상화 | ACK, Helm, Operator | [ACK](./02-ack.md), [Helm](./01-helm.md), [K8s 확장](./04-kubernetes-extensions.md) |
| **인프라** | 실제 컴퓨팅/네트워크/스토리지 | EKS, VPC, IAM | [EKS](../eks/01-eks-introduction.md) |

### 셀프서비스 카탈로그 패턴 (KRO RGD + ACK)

[KRO](./03-kro.md)의 ResourceGraphDefinition(RGD)과 [ACK](./02-ack.md)를 결합하면 강력한 셀프서비스 패턴을 구현할 수 있습니다:

```yaml
# 개발자가 작성하는 단일 매니페스트
apiVersion: kro.run/v1alpha1
kind: WebApplication
metadata:
  name: my-app
spec:
  name: my-app
  image: my-app:v1.0
  replicas: 3
  database:
    engine: postgresql
    instanceClass: db.t3.medium
```

이 단일 매니페스트를 통해 KRO가 내부적으로:
1. **Deployment + Service** (Kubernetes 네이티브)
2. **RDS 인스턴스** (ACK를 통한 AWS 리소스)
3. **IAM Role** (ACK를 통한 권한 설정)

을 자동 생성합니다. 자세한 예제는 [ExampleCorp 통합 예제](./05-example-corp-app.md)를 참조하세요.

### Golden Path 개념

Golden Path(골든 패스)는 플랫폼 팀이 제공하는 **권장 배포 경로**입니다:

- **목적**: 개발자가 검증된 방법으로 빠르게 시작할 수 있도록 가이드
- **특징**: 강제가 아닌 권장 -- 필요시 벗어날 수 있지만 대부분의 경우 최적의 선택
- **예시**:
  - "신규 마이크로서비스 배포" Golden Path: Helm Chart 템플릿 → ArgoCD 연동 → Prometheus 메트릭 자동 수집
  - "데이터베이스 프로비저닝" Golden Path: KRO RGD 매니페스트 → ACK를 통한 RDS 생성 → Secret 자동 주입

---

## 4. 플랫폼 엔지니어링 도구 생태계

이 레포지토리에서 다루는 도구들이 플랫폼 엔지니어링 관점에서 어디에 위치하는지 매핑합니다.

| 카테고리 | 도구 | 이 레포 문서 링크 |
|----------|------|-----------------|
| **패키지 관리** | Helm, Kustomize | [Helm](./01-helm.md) |
| **AWS IaC** | ACK, CloudFormation | [ACK](./02-ack.md) |
| **리소스 오케스트레이션** | KRO, Crossplane | [KRO](./03-kro.md) |
| **확장 메커니즘** | CRD, Operator | [Kubernetes 확장 메커니즘](./04-kubernetes-extensions.md) |
| **GitOps** | ArgoCD, FluxCD | [GitOps 섹션](../gitops/README.md) |
| **정책/거버넌스** | Kyverno, OPA Gatekeeper | [Kyverno](../security/01-kyverno-policy-management.md), [OPA Gatekeeper](../security/09-opa-gatekeeper.md) |
| **관측성** | Prometheus, Grafana, OTel | [Observability 섹션](../observability/README.md) |
| **오토스케일링** | KEDA, Karpenter | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| **서비스 메시** | Istio, Cilium | [Istio](../service-mesh/istio/README.md), [Cilium Service Mesh](../service-mesh/cilium-service-mesh/README.md) |
| **보안** | Falco, Trivy, PSS | [런타임 보안](../security/08-runtime-security.md), [이미지 보안](../security/07-image-security.md), [PSS](../security/03-pod-security-standards.md) |

---

## 5. 플랫폼 성숙도 자가진단 체크리스트

조직의 플랫폼 엔지니어링 성숙도를 진단해보세요. 각 항목은 이 레포의 관련 문서와 연결됩니다.

### START 단계

| 체크 | 항목 | 관련 문서 |
|------|------|----------|
| [ ] | EKS 클러스터가 표준화된 방식으로 생성되는가? | [EKS 클러스터 생성](../eks/02-eks-cluster-creation-part1.md) |
| [ ] | RBAC 정책이 정의되고 적용되는가? | [인증 및 권한 부여](../security/02-kubernetes-auth-authz.md) |
| [ ] | 네트워크 정책이 적용되는가? | [네트워크 정책](../security/04-network-policies.md) |
| [ ] | 기본적인 모니터링과 로깅이 구성되는가? | [EKS 모니터링](../eks/06-eks-monitoring-logging.md) |
| [ ] | Pod Security Standards가 적용되는가? | [PSS](../security/03-pod-security-standards.md) |
| [ ] | 리소스 쿼터와 제한이 설정되는가? | [EKS 비용 최적화](../eks/07-eks-cost-optimization.md) |

### ADVANCE 단계

| 체크 | 항목 | 관련 문서 |
|------|------|----------|
| [ ] | IaC로 인프라가 관리되는가? (ACK, Terraform 등) | [ACK](./02-ack.md) |
| [ ] | GitOps 워크플로우가 적용되는가? | [GitOps](../gitops/README.md) |
| [ ] | 중앙 집중식 관측성 스택이 운영되는가? | [Observability](../observability/README.md) |
| [ ] | 정책 엔진으로 거버넌스가 자동화되는가? | [Kyverno](../security/01-kyverno-policy-management.md) |
| [ ] | 시크릿이 외부 저장소에서 자동 관리되는가? | [시크릿 관리](../security/05-secrets-management.md) |
| [ ] | 컨테이너 이미지 스캔이 자동화되는가? | [이미지 보안](../security/07-image-security.md) |

### EXCEL 단계

| 체크 | 항목 | 관련 문서 |
|------|------|----------|
| [ ] | 셀프서비스 카탈로그가 개발자에게 제공되는가? | [KRO](./03-kro.md), [ExampleCorp](./05-example-corp-app.md) |
| [ ] | DORA 메트릭을 측정하고 개선하는가? | - |
| [ ] | 런타임 보안 모니터링이 운영되는가? | [런타임 보안](../security/08-runtime-security.md) |
| [ ] | 오토스케일링이 워크로드에 최적화되는가? | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | 플랫폼 SLO가 정의되고 추적되는가? | [Observability 분석](../ops/08-observability-analysis.md) |
| [ ] | Golden Path가 정의되고 문서화되는가? | 이 문서 (3절) |

---

## 6. 참고 자료

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Platform Engineering on Kubernetes (O'Reilly)](https://www.oreilly.com/library/view/platform-engineering-on/9781617299322/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)
