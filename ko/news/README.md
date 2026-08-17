# 소식
> **마지막 업데이트**: 2026년 8월 17일

Kubernetes, Amazon EKS, CNCF 생태계의 뉴스는 별도 다이제스트 문서로 쌓이지 않습니다. 매주 GitHub Actions가 관련 뉴스를 관련된 기존 문서에 직접 반영하고, 아래 갱신 로그에 어떤 문서가 왜 바뀌었는지만 남깁니다. 매칭되는 문서가 없는 뉴스는 원문 링크만 기록됩니다.

## 갱신 로그

- 2026-W34: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.5.0 정식 릴리스 및 v3.5.1/v3.4.7/v3.3.14 패치 릴리스 반영
- 2026-W34: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.31.0-beta.1 릴리스(1.31 베타 단계 진입) 반영
- 2026-W34: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.8.2(Gateway API 1.5.1 지원, 테스트 최대 k8s 1.36) 반영
- 2026-W34: 매칭 문서 없음 — Amazon EKS, Kubernetes 컨트롤 플레인 구성 파라미터(스케줄러/컨트롤러 매니저/API 서버 튜닝) 지원 ([원문](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-eks-control-plane-configuration-parameters))
- 2026-W34: 매칭 문서 없음 — Cloud Native Buildpacks, CNCF 졸업(graduated) 프로젝트 승격 ([원문](https://www.cncf.io/announcements/2026/08/11/cncf-announces-graduation-of-cloud-native-buildpacks-advancing-the-standard-for-container-builds/))
- 2026-W34: 매칭 문서 없음 — KubeCon + CloudNativeCon North America 2026 일정 공개, AI Inference + Agentic 트랙 신설 ([원문](https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/))
- 2026-W34: 매칭 문서 없음 — Kubernetes YAML을 KYAML로 예쁘게 출력하기, Kubernetes 블로그 ([원문](https://kubernetes.io/blog/2026/08/11/how-to-pretty-print-kubernetes-yaml-as-kyaml/))
- 2026-W31: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.36.3/v1.35.7/v1.34.10 패치 릴리스 및 v1.37 코드 프리즈 발효 반영
- 2026-W31: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode 노드 풀의 EFA·EC2 배치 그룹 지원 반영
- 2026-W31: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter 노드 풀의 EFA·EC2 배치 그룹 지원 반영
- 2026-W31: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — AMP 워크스페이스 한도 상향(활성 시계열 15억 개, 규칙 20만 개) 반영
- 2026-W31: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — OpenTelemetry CNCF 졸업(graduation) 반영
- 2026-W31: [networking/calico/README.md](../networking/calico/README.md) — Tigera의 Calico for VMs on Kubernetes 출시(eBPF 기반 VM+컨테이너 통합 네트워킹) 반영
- 2026-W31: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.20.0-rc.1 릴리스 후보 반영
- 2026-W31: 매칭 문서 없음 — Confidential Containers, CNCF 인큐베이팅 프로젝트 승격 ([원문](https://www.cncf.io/blog/2026/07/22/confidential-containers-becomes-a-cncf-incubating-project/))
- 2026-W31: 매칭 문서 없음 — Kubernetes CSI 드라이버 경로 순회(path traversal) CVE 2건 (CVE-2026-3864 NFS / CVE-2026-3865 SMB; csi-driver-nfs v4.13.1, csi-driver-smb v1.20.1에서 수정) ([원문](https://www.sentinelone.com/blog/mount-here-read-there-twin-path-traversal-cves-in-kubernetes-storage/))
- 2026-W30: [networking/cilium/README.md](../networking/cilium/README.md) — Cilium 1.19.6/1.18.12/1.17.18 패치 릴리스 및 CVE-2026-56743(ipBlock NetworkPolicy 이슈) 반영
- 2026-W30: [service-mesh/istio/README.md](../service-mesh/istio/README.md) — Istio 1.30.3/1.29.6 패치 릴리스 반영
- 2026-W30: [service-mesh/linkerd/README.md](../service-mesh/linkerd/README.md) — Linkerd edge-26.7.1(미정의 서비스 포트 요청 차단, breaking) 반영
- 2026-W30: [eks-auto-mode/README.md](../eks-auto-mode/README.md) — EKS Auto Mode의 ARC zonal shift/autoshift 지원 반영
- 2026-W30: [ops/15-zonal-operations-guide.md](../ops/15-zonal-operations-guide.md) — EKS Auto Mode의 ARC zonal shift 지원 반영
- 2026-W30: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter 전 유지 라인 일괄 패치 릴리스(v1.3.8~v1.11.3) 반영
- 2026-W30: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — Kubernetes v1.37.0-beta.0 및 v1.37 릴리스 일정 반영
- 2026-W30: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCon Japan 2026과 Argo CD 3.5 로드맵 공유 예정 소식 반영
- 2026-W30: [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) — Kubernetes 블로그의 커스텀 메트릭 익스포터 작성 가이드 반영
- 2026-W30: 매칭 문서 없음 — HAMi, CNCF 인큐베이팅 프로젝트로 승격 ([원문](https://www.cncf.io/blog/2026/07/15/hami-becomes-a-cncf-incubating-project/))
- 2026-W30: 매칭 문서 없음 — Kubernetes에서 vLLM으로 셀프 호스팅 LLM 운영하기, CNCF 블로그 ([원문](https://www.cncf.io/blog/2026/07/16/running-a-self-hosted-llm-in-kubernetes-with-vllm/))
- 2026-W29: [security/10-cert-manager.md](../security/10-cert-manager.md) — ACM의 ACME 프로토콜 지원(cert-manager에서 ACM 퍼블릭 인증서 발급 가능) 반영
- 2026-W29: [observability/tracing/03-opentelemetry.md](../observability/tracing/03-opentelemetry.md) — NGINX + OpenTelemetry 기반 AI 에이전트 네트워크 경계 관측 패턴 반영
- 2026-W29: 매칭 문서 없음 — AI 네이티브 워크로드를 위한 플랫폼 엔지니어링의 진화, CNCF 블로그 ([원문](https://www.cncf.io/blog/2026/07/06/evolving-platform-engineering-for-ai-native-workloads/))
- 2026-07-11: [core/01-cluster-architecture.md](../core/01-cluster-architecture.md) — etcd v3.7.0 릴리스(RangeStream 등) 반영
- 2026-07-11: [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) — EKS Auto Mode GPU 관리 요금 최대 60% 인하 반영
- 2026-07-11: [autoscaling/02-karpenter.md](../autoscaling/02-karpenter.md) — Karpenter v1.14.0 릴리스(CapacityBuffers API 등) 반영
- 2026-07-11: [observability/metrics/04-cloudwatch-metrics.md](../observability/metrics/04-cloudwatch-metrics.md) — CloudWatch Application Signals Service Events 반영
- 2026-07-11: [gitops/argocd/README.md](../gitops/argocd/README.md) — ArgoCD v3.4.5 패치 릴리스 반영
- 2026-07-11: 매칭 문서 없음 — ingress-nginx 컨트롤러 은퇴(2026년 3월) 이후 대응 가이드, CNCF 블로그 ([원문](https://www.cncf.io/blog/2026/07/09/navigating-the-ingress-nginx-retirement/))
- 2026-07-11: 매칭 문서 없음 — CNCF 클라우드 네이티브 AI 데이터 스토리지 백서 공개 ([원문](https://www.cncf.io/report-whitepaper/2026/07/08/the-cncf-data-storage-in-cloud-native-ai-white-paper/))
- 2026-07-11: 매칭 문서 없음 — Amazon EMR on EKS, Apache Spark 트러블슈팅 에이전트 지원 ([원문](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-emr-eks-spark-troubleshooting/))
- 2026-07-11: 매칭 문서 없음 — AWS Systems Manager 하이브리드/멀티클라우드 노드 요금제 개편(Advanced Instances Tier 폐지) ([원문](https://aws.amazon.com/about-aws/whats-new/2026/06/aws-systems-manager-multicloud-vm/))
