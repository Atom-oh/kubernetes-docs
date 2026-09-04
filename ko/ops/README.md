# 운영 가이드

> **마지막 업데이트**: 2026년 2월 23일

이 섹션은 EKS Auto Mode 기반 프로덕션 환경의 실전 운영 가이드입니다. Terraform을 사용한 인프라 프로비저닝부터 CI/CD 파이프라인, GitOps 기반 배포, 스케일링, 관측성, 리소스 최적화, 업그레이드까지 포괄합니다.

---

## 대상 독자

- EKS Auto Mode를 사용하여 프로덕션 환경을 구축하는 **플랫폼 엔지니어**
- Terraform/Terragrunt 기반 IaC를 운영하는 **인프라 엔지니어**
- GitLab CI, ArgoCD를 활용한 CI/CD 파이프라인을 구축하는 **DevOps 엔지니어**
- Prometheus, Grafana, Loki 기반 관측성 스택을 운영하는 **SRE**

---

## 전제 조건

- [EKS Auto Mode 시작하기](../eks-auto-mode/01-getting-started.md) 학습 완료
- Terraform 기본 문법 이해
- Kubernetes 핵심 개념 이해 ([핵심 개념](../core/01-cluster-architecture.md))
- kubectl, helm CLI 사용 경험

---

## 목차

| # | 문서 | 주요 내용 |
|---|------|----------|
| 01 | [Terraform 3-Layer 인프라 구축](./01-infrastructure-setup.md) | VPC, EKS Auto Mode, Pod Identity를 3-Layer Terraform으로 구성 |
| 02 | [NLB 가중치 라우팅과 블루/그린](./02-infrastructure-advanced.md) | 듀얼 클러스터 아키텍처, NLB 가중치, DNS 라우팅 |
| 03 | [CI 파이프라인](./03-ci-pipelines.md) | ECR, GitLab Runner, GitHub ARC, 멀티 플랫폼 빌드 |
| 04 | [ArgoCD 멀티클러스터](./04-gitops-multi-cluster.md) | Hub-spoke, ApplicationSet, IAM Identity Center SSO |
| 05 | [GitOps 자동화](./05-gitops-automation.md) | Atlantis, FluxCD, Terraform Cloud, AIOps |
| 06 | [스케일링 전략](./06-scaling-strategies.md) | HPA 커스텀 메트릭, KEDA, VPA, Spot 활용 |
| 07 | [운영 알림 구성](./07-observability-alerts.md) | 네트워크/CPU/디스크/Auto Mode 노드 종료 알림 |
| 08 | [관측성 분석](./08-observability-analysis.md) | Logs/Metrics/Traces 상관 분석, PromQL, LogQL, TraceQL |
| 09 | [관측성 스택 운영](./09-observability-stack.md) | Loki, Tempo, Prometheus/AMP 설치 및 운영 |
| 10 | [리소스 최적화](./10-resource-optimization.md) | Requests/Limits, JVM 튜닝, 프레임워크별 가이드 |
| 11 | [EKS 업그레이드](./11-upgrade-operations.md) | Auto Mode 무중단 업그레이드, 블루/그린 전략 |
| 15 | [Zonal 클러스터 운영 전략](./15-zonal-operations-guide.md) | TargetGroupBinding weight 전환, 네이티브 롤백, Kafka/Redis/Aurora AZ 친화 read |
| 16 | [트러블슈팅 플레이북](./16-troubleshooting-playbook.md) | 증상 → 진단 → 원인 → 조치: Pending/ImagePull/CrashLoop/NotReady/PVC, IRSA·VPC CNI·Karpenter, kubectl 치트시트 |

---

## 학습 경로

### 권장 순서

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           학습 경로                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 인프라 구축 (01-02)                                                  │
│     └── Terraform으로 VPC/EKS 프로비저닝                                 │
│                    │                                                    │
│                    ▼                                                    │
│  2. CI/CD (03-05)                                                       │
│     └── 빌드 파이프라인과 GitOps 배포 구축                               │
│                    │                                                    │
│                    ▼                                                    │
│  3. 스케일링 (06)                                                       │
│     └── 워크로드에 맞는 스케일링 전략 수립                               │
│                    │                                                    │
│                    ▼                                                    │
│  4. 관측성 (07-09)                                                      │
│     └── 모니터링, 알림, 분석 체계 구축                                   │
│                    │                                                    │
│                    ▼                                                    │
│  5. 최적화 (10)                                                         │
│     └── 리소스 효율화 및 비용 최적화                                     │
│                    │                                                    │
│                    ▼                                                    │
│  6. 업그레이드 (11)                                                     │
│     └── 무중단 업그레이드 절차 수립                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 역할별 권장 문서

| 역할 | 필수 | 권장 |
|------|------|------|
| **플랫폼 엔지니어** | 01, 02, 04, 11 | 06, 07 |
| **인프라 엔지니어** | 01, 02, 05 | 09, 11 |
| **DevOps 엔지니어** | 03, 04, 05 | 06, 07 |
| **SRE** | 07, 08, 09 | 10, 11 |
| **애플리케이션 개발자** | 06, 10 | 03, 08 |

---

## 기존 문서와의 관계

이 운영 가이드는 기존 개념 문서를 보완하는 **실전 코드 중심 가이드**입니다:

| 카테고리 | 개념 이해 | 실전 운영 (이 가이드) |
|----------|----------|---------------------|
| **EKS** | [EKS Auto Mode](../eks-auto-mode/README.md) | Terraform HCL, 업그레이드 스크립트 |
| **GitOps** | [ArgoCD](../gitops/argocd/README.md) | ApplicationSet, 멀티클러스터 설정 |
| **스케일링** | [KEDA](../autoscaling/01-keda.md), [Karpenter](../autoscaling/02-karpenter.md) | HPA 커스텀 메트릭, VPA 통합 |
| **관측성** | [관측성 스택](../observability/README.md) | PromQL, LogQL, TraceQL 쿼리 |
| **보안** | [Kyverno](../security/01-kyverno-policy-management.md) | Policy 운영 가이드 |

### 문서 간 연계

```
개념 문서                          운영 가이드
──────────────────────────────────────────────────────────────
eks-auto-mode/01-getting-started.md
         │
         └──────────────────────► ops/01-infrastructure-setup.md
                                 ops/02-infrastructure-advanced.md
                                 ops/11-upgrade-operations.md

gitops/01-argocd.md
         │
         └──────────────────────► ops/04-gitops-multi-cluster.md
                                 ops/05-gitops-automation.md

autoscaling/01-keda.md
autoscaling/02-karpenter.md
         │
         └──────────────────────► ops/06-scaling-strategies.md

observability/01-monitoring-stack.md
observability/02-logging-stack.md
         │
         └──────────────────────► ops/07-observability-alerts.md
                                 ops/08-observability-analysis.md
                                 ops/09-observability-stack.md
```

---

## 빠른 시작

### 1. 인프라 프로비저닝

```bash
# 1. VPC 생성
cd terraform/01-network
terraform init && terraform apply

# 2. EKS Auto Mode 클러스터 생성
cd ../02-cluster
terraform init && terraform apply

# 3. Platform 컴포넌트 배포
cd ../03-platform
terraform init && terraform apply
```

### 2. 애플리케이션 배포

```bash
# ArgoCD 접속
kubectl port-forward svc/argocd-server -n argocd 8080:443

# 애플리케이션 동기화
argocd app sync my-app
```

### 3. 모니터링 확인

```bash
# Grafana 접속
kubectl port-forward svc/grafana -n monitoring 3000:80

# 로그 확인
kubectl logs -n default -l app=my-app --tail=100
```

---

## 지원 및 피드백

- **이슈 리포트**: GitHub Issues
- **문서 기여**: Pull Request 환영
- **질문**: Slack #kubernetes-docs 채널
