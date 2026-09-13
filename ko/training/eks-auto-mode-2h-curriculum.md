# EKS Auto Mode 운영자 교육 커리큘럼 (2시간)

> **대상**: EKS를 운영하는 인프라·플랫폼 엔지니어
> **전제 조건**: Kubernetes 기본 개념과 EKS 운영 경험
> **마지막 업데이트**: 2026년 9월 12일

## 교육 목표

AWS 관리 범위와 운영자 책임을 구분하고, Auto Mode의 NodePool/NodeClass를 설계합니다. 실제 workload와 비용·가용성 지표로 개선 여부를 판단하고 node 중단을 증거로 조사하는 방법을 익힙니다. 고정된 비용 절감률이나 node 준비 시간을 교육 성과로 약속하지 않습니다.

## 시간표와 사전 준비

| 구간 | 시간 | 세부 구성 |
| --- | --- | --- |
| Part1: 구조와 배치 |40분 | 아키텍처10 + NodePool/NodeClass15 + scaling15 |
| Part2: 최적화와 수명 |35분 | Spot10 + 비용10 + workload10 + lifecycle5 |
| 휴식 |10분 | |
| Part3: 관측과 장애 분석 |25분 | node8 + signal연계8 + 시나리오9 |
| Part4: IaC/GitOps |10분 | IaC5 + ArgoCD5 |

합계120분입니다. 강사는 [Auto Mode 가이드](../eks-auto-mode/README.md)의 최신 API와 준비된 실습 환경, 계정·region·kubeconfig·권한·비용 한도를 먼저 확인합니다. 실습 없이 강의만 할 경우에는 사전 수집한 events/NodeClaim/metrics 자료로 분석합니다. 실제 FIS 장애 주입과 node 삭제는 이 커리큘럼의 자동 실행 대상이 아닙니다.

기존 문서의 줄 수나 언급 횟수는 품질·충분한 coverage의 증거가 아니므로 이전 평가표에서 제거했습니다. Terraform/ArgoCD·observability는 아래 참조 자료를 사용하고, Terragrunt와 조직별 운영 절차는 사용하는 버전에 맞게 보완합니다.

## Part1: 구조와 배치 (40분)

### 1-1. 관리 경계 (10분)

[시작 가이드](../eks-auto-mode/01-getting-started.md)로 Auto Mode, managed node group과 자체 Karpenter의 책임 차이를 비교합니다. Auto Mode는 Karpenter 기반의 AWS 관리형 compute 기능이지만 운영자가 NodePool만 관리하면 되는 것은 아닙니다. workload requests·PDB·NodeClass의 지원 네트워크/스토리지/identity 설정도 책임 범위입니다.

Auto Mode는 관리형 Bottlerocket 변형을 사용하며 AL2023/Bottlerocket AMI 선택, 임의 userData·SSH·SSM 접근을 제공하지 않습니다. 기본 general-purpose/system pool도 실제 enablement 설정과 존재 여부를 확인합니다. 내부 controller가 일반 Pod처럼 클러스터에 보인다고 가정하지 않습니다.

### 1-2. NodePool/NodeClass (15분)

[구성 가이드](../eks-auto-mode/02-nodepool-configuration.md)의 `eks.amazonaws.com` label과 NodeClass API를 사용합니다. 자체 Karpenter의 `karpenter.k8s.aws` instance label/EC2NodeClass와 혼합하지 않습니다. 사용자 정의 NodeClass도 가능하며 AWS가 모든 설정을 대신 결정하는 객체가 아닙니다.

다음은 기존 default NodeClass와 Arm image를 전제로 하는 **스키마 예제**입니다. CPU·memory limits는 절대 청구 상한이 아니며 동시 provisioning의 일시적 초과 등을 별도로 평가해야 합니다. 원래 예제의 GPU·Spot workload 전체를 이 풀에 적용하지 않습니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: kubernetes.io/arch
        operator: In
        values:
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '16'
    memory: 64Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

수강자는 Pod의 nodeSelector/affinity, requests, taint/toleration과 NodePool constraints를 대조합니다. Arm 전환은 image manifest·native dependency·성능을 함께 검증합니다.

### 1-3. Scaling (15분)

[스케일링 가이드](../eks-auto-mode/03-scaling-behavior.md)를 사용해 unschedulable Pod→pool 제약 평가→node 공급→Pod readiness를 추적합니다.40~90초는 보장값이 아니며 image pull, IP·quota·capacity·volume 조건을 포함해 측정합니다.

WhenEmpty와 WhenEmptyOrUnderutilized, consolidateAfter를 비교하고, requests가 실제 부하와 다른 경우를 분석합니다. consolidation이 수동 최적화나 부하 검증을 모두 대체하지 않습니다. drift도 모든 설정 변경을 즉시 한 대씩 교체한다는 보장이 아닙니다.

## Part2: 최적화와 수명 (35분)

### 2-1. Spot (10분)

[Spot 전략](../eks-auto-mode/04-spot-strategies.md)에서 호환되는 instance 선택 폭, critical workload의 용량, interruption과 복구를 검토합니다. Spot-only는 선호가 아니라 필수 조건이며 on-demand fallback은 별도 허용·용량 구성이 필요합니다. do-not-disrupt/PDB가 Spot 회수·node 장애를 막지는 않습니다.

### 2-2. 비용 (10분)

[비용 관리](../eks-auto-mode/06-cost-management.md)를 이용해 EC2, 별도 Auto Mode 요금, EBS, load balancer/NAT/전송과 관측 비용을 분리합니다. Graviton·Spot·consolidation의 고정 절감률을 곱한 가상 계산을 실제 결과로 제시하지 않습니다.

Compute Savings Plans뿐 아니라 적격 EC2 Instance Savings Plans/RI도 조건에 따라 EC2 사용량에 적용됩니다. 별도 Auto Mode 요금이나 Spot에 동일 할인이 추가 적용된다고 가정하지 않습니다. Savings Plans는 capacity reservation이 아닙니다. 구매 결정은 시간별 eligible baseline과 이미 적용된 coverage를 확인한 뒤 별도로 수행합니다.

### 2-3. Workload 설계 (10분)

[workload 최적화](../eks-auto-mode/08-workload-optimization.md)에서 웹·배치·GPU·시스템 workload의 requests, image·architecture, storage와 SLO를 비교합니다. HPA는 replica, VPA는 CPU/memory recommendation/update, Auto Mode는 node 공급으로 역할을 나눕니다. GPU 자원은 모델·driver 조건이 필요하며 VPA가 GPU instance를 자동 선택하지 않습니다.

생산 환경의 VPA Off는 추천값 검토용입니다. node pool 분리는 팀·가용성·권한·capacity 요구에 따라 선택하며 taint나 label을 tenant 보안 경계로 사용하지 않습니다.

### 2-4. Node lifecycle (5분)

[수명 가이드](../eks-auto-mode/07-node-lifecycle.md)와 AWS 문서의 **기본 expiry336h(14일), 기본 NodeClaim termination grace24h, 관리형 instance 최대21일**을 구분합니다. 원래720h(30일) 예제는 Auto Mode 기준이 아닙니다. 특정 수명까지 node가 살아 있다는 보장도 아닙니다.

budget은 drift/emptiness/consolidation 등의 자발적 중단 속도를 제한합니다. expiration·interruption·repair를 모두 업무 시간 밖으로 미룰 수는 없습니다. 실제 NodeClaim에 저장된 값, PDB·종료 시간과 application 복구를 확인합니다.

## 휴식 (10분)

## Part3: 관측과 장애 분석 (25분)

### 3-1. Node 관측 (8분)

[운영 가이드](../eks-auto-mode/05-operations.md)의 NodePool/NodeClass/NodeClaim conditions, Kubernetes events, node와 workload 지표를 봅니다. AWS 관리 controller의 일반 Karpenter scrape endpoint나 Deployment log를 임의로 가정하지 않습니다. 지원되는 managed-component log delivery와 실제 CloudWatch/Prometheus publisher를 확인합니다.

다음은 kube-state-metrics가 제공하는 기본 node 경보입니다. cluster 전체에 적용되므로 Auto Mode만 볼 때는 허용한 compute-type label과 정확한 join을 추가해야 합니다. node가 삭제되거나 수집이 중단돼 series가 사라지는 상황은 별도 no-data/이력 조사 대상입니다.

```yaml
groups:
- name: node-health
  rules:
  - alert: NodeNotReady
    expr: kube_node_status_condition{condition="Ready",status="true"} == 0
    for: 5m
  - alert: NodeMemoryPressure
    expr: kube_node_status_condition{condition="MemoryPressure",status="true"} ==
      1
    for: 2m
```

NodePool capacity는 실제 status.resources와 spec.limits를 같은 단위로 비교합니다. 이전의 가상 karpenter_nodeclaims_state/karpenter_nodepool_usage_limit 비율은 제거했습니다. CloudWatch Events와 EventBridge를 별도 서비스 단계처럼 이어 붙이지 말고 실제 수집 source·rule·target·지연을 확인합니다.

### 3-2. Logs/Metrics/Traces 연결 (8분)

[관측성 가이드](../observability/09-observability-optimization.md)와 [Grafana](../observability/grafana/README.md)에서 trace-to-logs, derived fields와 exemplars를 구분합니다. TraceID를 Loki의 index label에 반드시 넣을 필요는 없으며 높은 cardinality를 피하도록 log field/structured metadata와 query를 사용합니다.

선택한 Grafana/Tempo 버전의 tracesToLogsV2 등 실제 설정과 datasource UID·URL·label mapping, sampling·보존 기간을 확인합니다. exemplars는 metric publisher/수집/storage/UI가 모두 맞아야 하며 flag 하나로 기존 데이터에 trace 링크가 생기지 않습니다. 강사는 실제로 같은 request ID로 연결되는 예제를 준비합니다.

### 3-3. 증거 기반 시나리오 (9분)

| 증상 | 확인할 증거 | 성급히 확정하지 않을 결론 |
| --- | --- | --- |
| Pending인데 node가 없음 | Pod event·PVC·affinity·taint·NodeClass/Pool condition·quota/IP/capacity·API error | 항상 capacity 부족 |
| node가 사라짐 | 삭제/중단 events, NodeClaim 상태, managed logs, EC2/CloudTrail 기록과 application 복구 | 항상 consolidation 또는 OOM |
| 응답 지연 | 오류·latency 분포·queue·trace·관련 log와 CPU/RAM/network/storage | trace나 온도 한 개로 원인 확정 |

CloudTrail은 기록된 API 행위를 보여주며 모든 scheduling 실패의 최종 답은 아닙니다. 아직 EC2 호출까지 진행되지 않은 경우 Kubernetes events/conditions부터 확인합니다. 수집하지 않은 과거 데이터는 임의로 복원된 것처럼 설명하지 않습니다.

## Part4: IaC/GitOps (10분)

### 4-1. IaC 경계 (5분)

[인프라 구성](../ops/01-infrastructure-setup.md)에서 공통 backend 설정과 network/cluster/platform 배포 layer의 dependency를 구분합니다. 파일 또는 state를 분리해도 network 변경이 cluster에 영향을 주지 않는다는 보장은 없습니다. provider/module의 실제 Auto Mode 설정, state locking, 출력 dependency와 apply 순서를 확인합니다.

### 4-2. GitOps 운영 (5분)

[ArgoCD Application](../gitops/argocd/02-applications.md), [ApplicationSet](../gitops/argocd/04-applicationsets.md)의 권한·generator·sync policy를 비교합니다. Auto Sync/self-heal/prune은 자동으로 안전한 rollout이 아니며 NodePool/NodeClass 삭제 영향과 drift ownership을 검토해야 합니다. Progressive Sync의 활성화·지원 범위도 선택한 버전에서 확인합니다.

## 강의 후 평가와 실습 준비

- [시작과 관리 경계](../quizzes/eks-auto-mode/01-getting-started-quiz.md)
- [NodePool/NodeClass](../quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
- [스케일링](../quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
- [Spot](../quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
- [비용](../quizzes/eks-auto-mode/06-cost-management-quiz.md)
- [워크로드](../quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
- [노드 수명](../quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
- [운영](../quizzes/eks-auto-mode/05-operations-quiz.md)

강사는 계정·cluster 확인, 지원 API·image, metrics/log 수집과 정리 절차를 준비하고 실제 실행한 범위를 표시합니다. [마이그레이션](../eks-auto-mode/09-migration-guide.md)과 [Spot 운영 실험](../ops/17-spot-production-experiments.md)도 참고하되, 장애 주입은 전용 환경·명시적 범위·중지 조건·복구 증거를 갖춘 별도 실습으로 다룹니다.

## 검토 근거

120분 시간 구성과 참조 링크, NodePool 구조 스키마 및 node alert 규칙을 검사했습니다. 실제 cluster 생성·node 교체·FIS 실험·비용 절감 측정·observability backend 배포는 수행하지 않았습니다.

- [Auto Mode NodePool defaults](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Managed instance maximum lifetime](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Auto Mode responsibilities and OS](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Managed component logs](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Grafana Tempo configuration](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/)
- [Loki label cardinality](https://grafana.com/docs/loki/latest/get-started/labels/)
