# 가이드북 로드맵

> **마지막 업데이트**: 2026년 9월 1일

이 가이드북은 Linux 커널에서 시작해 컨테이너, Kubernetes, Amazon EKS, 네트워킹, 서비스 메시, 스토리지, 데이터베이스, 데이터 파이프라인, AI/ML, 그리고 보안·GitOps·플랫폼 엔지니어링·컨테이너 레지스트리·옵저버빌리티·운영까지 — 클라우드 네이티브 스택 전체를 하나의 서사로 다룹니다. 이 페이지는 전체 지도이자 추천 학습 경로입니다.

![클라우드 네이티브 가이드북의 15개 도메인이 기초(Linux/Container) → 오케스트레이션(Kubernetes/EKS) → 연결(Networking/Service Mesh) → 상태(Storage/Database) → 데이터·AI(Data Pipeline/AI-ML) → 횡단 관심사(Security/GitOps/Platform/Container Registry/Observability/Operations)로 이어지는 학습 흐름 지도.](.gitbook/assets/ko-roadmap-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-roadmap-0.html)

## 도메인 지도

| 계층 | 도메인 | 시작점 | 한 줄 요약 |
|------|--------|--------|-----------|
| 기초 | Linux & Container | [Linux 기초](basics/01-linux-basics.md) | 커널, 네임스페이스, cgroup — 컨테이너의 실체 |
| 오케스트레이션 | Kubernetes 핵심 개념 | [Kubernetes 소개](basics/04-kubernetes-introduction.md) | 워크로드·스케줄링·오토스케일링까지 K8s 그 자체 |
| 오케스트레이션 | Amazon EKS | [EKS 소개](eks/01-eks-introduction.md) | 클러스터 생성부터 하이브리드/Auto Mode까지 |
| 연결 | Networking | [네트워크 기초](basics/06-network-fundamentals-part1.md) | 프로토콜 25개부터 CNI(Cilium/Calico)까지 |
| 연결 | Service Mesh | [Istio](service-mesh/istio/README.md) | Istio/Linkerd/Cilium Mesh — mTLS 레이턴시 실측 포함 |
| 상태 | Storage | [Storage 개요](storage/README.md) | EBS gp2 vs gp3 fio 실측 벤치마크 |
| 상태 | Database | [Database 개요](database/README.md) | Operator 지형과 ClickHouse 1억 행 실측 |
| 데이터·AI | Data Pipeline | [Data on EKS 개요](data-on-eks/README.md) | Kafka·Spark·Airflow·Flink 딥다이브 |
| 데이터·AI | AI/ML | [AI/ML 워크로드](ai-ml/01-ai-ml-workloads.md) | vLLM·Ray·Kubeflow·MLflow on EKS |
| 횡단 | Security & Policy | [Kyverno](security/01-kyverno-policy-management.md) | 인증/인가, 정책, 런타임 보안, 공급망 |
| 횡단 | GitOps | [GitOps](gitops/README.md) | ArgoCD·Flux·Progressive Delivery |
| 횡단 | Platform Engineering | [개요](platform-engineering/00-platform-engineering-overview.md) | ACK·KRO·Crossplane·Backstage |
| 횡단 | Container Registry | [개요](container-registry/README.md) | ECR·Harbor·이미지 공급망 |
| 횡단 | Observability | [개요](observability/README.md) | 메트릭·로그·트레이싱·알림 스택 |
| 횡단 | Operations Guide | [운영 가이드](ops/README.md) | 용량 계획·FinOps·업그레이드 등 실전 플레이북 |

## 실측 벤치마크 시리즈

스펙 시트가 아니라 실제 AWS 리소스에서 직접 측정한 숫자를 담은 문서들입니다:

- [Istio sidecar vs ambient 실측](service-mesh/istio/comparison/03-sidecar-vs-ambient.md) — mTLS 데이터플레인별 P50/P99 레이턴시와 rollout 중 503 비율
- [EBS gp2 vs gp3 실측 벤치마크](storage/01-ebs-gp2-gp3-benchmark.md) — 같은 100GiB에서 IOPS 10배 차이와 gp2 버스트 크레딧 절벽
- [ClickHouse on EKS 실측 벤치마크](database/01-clickhouse-on-eks.md) — 1억 행 ingest 처리량, 압축률, 쿼리 레이턴시

## 추천 학습 경로

### ① 인프라 입문 — "컨테이너부터 EKS까지"

Linux 기초 → 컨테이너 기술 → Kubernetes 소개 → 핵심 개념(파드/서비스/스토리지/구성) → EKS 클러스터 생성 → 네트워크 기초. 각 문서의 퀴즈로 이해를 점검하고, [실습 랩](labs/README.md)을 병행하세요.

### ② 플랫폼/SRE — "운영 가능한 클러스터"

EKS 운영(업그레이드/문제 해결/복원력) → Networking(VPC CNI, Cilium) → Service Mesh 비교 가이드 → Security & Policy → Observability 스택 → GitOps → Operations Guide의 용량 계획/FinOps. 실측 벤치마크 시리즈가 이 경로의 판단 근거를 제공합니다.

### ③ 데이터·AI 플랫폼 — "상태와 데이터의 세계"

Storage → Database → Data Pipeline(Kafka → Spark → Airflow → Flink) → AI/ML(vLLM → Ray → Kubeflow). GPU/스케줄링이 필요하면 Kubernetes 핵심 개념의 Custom Scheduler 파트를 함께 보세요.

## AI와 함께 읽기

이 가이드북 전체는 [llms.txt 표준](llm-guide.md)으로도 제공됩니다 — LLM에게 URL 하나로 전체 콘텐츠를 읽힐 수 있습니다.
