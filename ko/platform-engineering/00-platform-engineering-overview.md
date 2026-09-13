# Platform Engineering 개요

> **마지막 업데이트**: 2026년 9월 12일

## 1. Platform Engineering이란?

### 정의

Platform Engineering은 **개발자 셀프서비스를 위한 도구, 워크플로우, 인프라를 설계하고 구축하며 운영하는 분야**입니다. 플랫폼 엔지니어링 팀은 개발자가 인프라의 복잡성을 직접 다루지 않고도 애플리케이션을 빠르고 안전하게 배포할 수 있도록 **Internal Developer Platform(IDP)**을 구축합니다.

### Internal Developer Platform (IDP)

IDP는 개발자가 코드 작성에 집중할 수 있도록 인프라 프로비저닝, 배포, 모니터링 등의 운영 작업을 추상화한 셀프서비스 플랫폼입니다.

**IDP의 핵심 가치:**

- **셀프서비스**: 승인된 범위의 리소스와 작업을 API·CLI·포털에서 요청
- **가드레일**: 보안 정책과 승인·감사 경로를 구현하고 적용 여부를 검증
- **표준화**: Golden Path를 통한 일관된 배포 패턴
- **자동화**: 반복 작업의 제거를 통한 인지 부하 감소

### Platform Engineering vs DevOps vs SRE

| 구분 | Platform Engineering | DevOps | SRE |
|------|---------------------|--------|-----|
| **초점** | 개발자 경험과 셀프서비스 플랫폼 구축 | 개발과 운영의 문화적 통합 | 서비스 신뢰성과 운영 자동화 |
| **핵심 산출물** | Internal Developer Platform | CI/CD 파이프라인, 자동화 스크립트 | SLO/SLI, 에러 버짓, 토일 자동화 |
| **주요 메트릭** | 개발자 생산성, 온보딩 시간 | 배포 빈도, 리드 타임 | 가용성, 에러 버짓 소비율 |
| **팀 구조** | 전담 플랫폼 팀 | 크로스 펑셔널 팀 | SRE 팀 또는 임베디드 SRE |
| **관계** | DevOps·SRE와 협력하는 제품 중심의 플랫폼 접근 | 문화와 방법론 | 운영 엔지니어링 실천 |

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

[AWS CAF](https://docs.aws.amazon.com/whitepapers/latest/overview-aws-cloud-adoption-framework/platform-perspective.html)의 Platform 관점에는 일곱 역량이 있습니다: platform architecture, data architecture, platform engineering, data engineering, provisioning and orchestration, modern application development, continuous integration and continuous delivery. 이 문서는 그중 platform engineering을 중심으로 설명합니다.

### 성숙도 모델: START → ADVANCE → EXCEL

AWS의 platform engineering 상세 가이드는 Start·Advance·Excel로 개선 과제를 설명합니다. 아래 Kubernetes 도구 매핑과 체크리스트는 이 문서의 학습 예시이며 AWS의 공식 인증 점수표나 모든 조직의 필수 도입 순서가 아닙니다.

#### START: 기반 구축

기초 인프라를 수립하고 보안 가드레일을 설정하는 단계입니다.

| 역량 | 설명 | Kubernetes 생태계 매핑 |
|------|------|----------------------|
| **랜딩 존 & 가드레일** | 멀티 어카운트 환경, 예방적/탐지적 통제 | EKS 클러스터 구성, [OPA Gatekeeper](../security/09-opa-gatekeeper.md) / [Kyverno](../security/01-kyverno-policy-management.md) |
| **인증** | 중앙 집중식 ID 관리, IdP 연동 | [K8s 인증 및 권한 부여](../security/02-kubernetes-auth-authz.md), OIDC, IRSA |
| **네트워크** | 중앙 집중식 네트워크 관리 | VPC CNI, [Calico](../networking/calico/README.md), [Cilium](../networking/cilium/README.md) |
| **관측성** | 로그·메트릭·트레이스 수집과 보호 | [Prometheus](../observability/metrics/01-prometheus.md), [Loki](../observability/logging/01-loki.md), [OpenTelemetry](../observability/tracing/03-opentelemetry.md) |
| **통제** | 프로그래밍 방식의 보안 통제 | [Pod Security Standards](../security/03-pod-security-standards.md), [네트워크 정책](../security/04-network-policies.md) |
| **비용 관리** | 태깅 전략, 비용 할당 | 청구 태그·사용량·비용 배분, [EKS 비용 최적화](../eks/07-eks-cost-optimization.md) |

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
| **개발자 인터페이스** | 개발자가 상호작용하는 UI/CLI | Backstage, Port, Argo Workflows UI | [Backstage](./06-backstage-idp.md) |
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

위 WebApplication은 **플랫폼이 사전에 정의해야 하는 사용자 API 예시**입니다. Kubernetes나 kro의 내장 kind가 아니며, 대응하는 RGD/생성 CRD가 없으면 적용할 수 없습니다. 이 개요에서는 완전한 RGD를 제공하거나 실제 리소스를 생성하지 않습니다.

RGD가 Deployment·Service·ACK의 RDS/IAM 리소스를 명시했을 때 kro는 Kubernetes 리소스와 의존성을 관리하고, ACK의 해당 service controller가 AWS API를 호출합니다. 생성되는 조합은 RGD 내용에 따라 달라집니다. controller 설치·CRD·RBAC/IAM, quota, readiness·오류 처리, credential 전달과 삭제/보존 정책을 별도로 검증해야 합니다. 단일 CR 생성이 AWS 리소스의 즉시 준비나 transaction을 보장하지는 않습니다. [ExampleCorp 예제](./05-example-corp-app.md)와 [kro 가이드](./03-kro.md)를 함께 확인하세요.

### Golden Path 개념

Golden Path(골든 패스)는 플랫폼 팀이 제공하는 **권장 배포 경로**입니다:

- **목적**: 개발자가 검증된 방법으로 빠르게 시작할 수 있도록 가이드
- **특징**: 지원되는 권장 경로 -- 예외는 조직의 승인 절차를 따르며 필수 보안·데이터 정책을 우회하지 않음
- **예시**:
  - "신규 마이크로서비스 배포" Golden Path: 검증한 Helm template → ArgoCD 연동 → 실제 metrics publisher/수집 구성
  - "데이터베이스 프로비저닝" Golden Path: 검증한 RGD → ACK의 RDS lifecycle → 승인된 credential 전달

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
| [ ] | DORA 메트릭을 적절한 서비스 범위에서 측정하고 개선하는가? | [현재 DORA 정의](https://dora.dev/guides/dora-metrics/) |
| [ ] | 런타임 보안 모니터링이 운영되는가? | [런타임 보안](../security/08-runtime-security.md) |
| [ ] | 오토스케일링이 워크로드에 최적화되는가? | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) |
| [ ] | 플랫폼 SLO가 정의되고 추적되는가? | [Observability 분석](../ops/08-observability-analysis.md) |
| [ ] | Golden Path가 정의되고 문서화되는가? | 이 문서 (3절) |

---

### 지표와 플랫폼 제품의 성공

현재 DORA 안내는 change lead time, deployment frequency, failed deployment recovery time, change fail rate, deployment rework rate의 다섯 지표를 설명합니다. 예전 네 지표나 일반 MTTR을 현재 정의와 혼용하지 마세요. 개인 성과 순위를 매기기보다 같은 서비스·팀의 개선과 안정성을 함께 보며, 플랫폼 온보딩 시간·작업 성공률·사용자 만족도·채택률도 측정합니다. 측정은 Excel에 도달한 뒤에만 시작하는 활동이 아닙니다.

IDP는 포털 하나와 동일하지 않습니다. API·CLI·template·문서·지원과 운영 책임을 포함하는 내부 제품이며, 개발팀이 모든 application 보안 책임을 넘기는 구조도 아닙니다. Golden Path와 guardrail은 실제 적용·예외·변경·복구를 검증해야 합니다.

## 6. 참고 자료

- [AWS CAF Platform Perspective - Platform Engineering](https://docs.aws.amazon.com/prescriptive-guidance/latest/aws-caf-platform-perspective/platform-eng.html)
- [CNCF Platform White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)
- [Backstage.io - Open Source IDP Framework](https://backstage.io/)
- [Internal Developer Platform](https://internaldeveloperplatform.org/)

- [DORA 현재 지표](https://dora.dev/guides/dora-metrics/)
