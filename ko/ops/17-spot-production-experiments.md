# EKS Spot 운영 적용 실험과 결과 판정

> **마지막 업데이트**: 2026년 9월 12일
> **실측 상태**: 부분 실측 완료 — 정상 부하, drain, 단일 Spot 회수, PDB 차단, 수동 On-Demand 전환. 7절에 원시 기록과 결과를 정리했습니다.
> **적용 범위**: EKS Auto Mode, 자체 운영 Karpenter, EKS Managed Node Group의 중단 허용 워크로드

Spot 도입은 할인율보다 **노드가 회수되는 동안 서비스 SLO와 데이터 정합성을 유지하는지**로 판단합니다. On-Demand 기준선을 먼저 측정하고, 같은 부하에서 Spot 혼합 구성의 장애 대응과 실효 비용을 비교합니다. 1–6절의 제안 수치와 기간은 **실험 설계 예시**입니다. 7절의 수치는 별도로 표시한 실제 측정값이며 AWS 보장값이 아닙니다.

현재 판정은 **운영 확대 보류 — 회수·전환 구간의 오류와 버전 호환성·중단 처리 보완이 필요**입니다. 합성 HTTP 워크로드로 현재 구성을 측정했으며, 실제 업무 서비스나 지원 버전 구성의 무중단 운영을 입증한 결과는 아닙니다.

## 1. 먼저 확인할 동작과 한계

| 항목 | 공식 동작 또는 제약 | 실험에서 확인할 내용 |
|---|---|---|
| Spot 중단 통지 | EC2의 terminate/stop 통지는 일반적으로 2분 전이며 best effort입니다. hibernate는 즉시 시작합니다. [S1] | 이벤트 전달 지연과 통지를 처리하지 못한 경우를 각각 측정 |
| Pod 종료 시간 | 2분은 애플리케이션 전용 시간이 아닙니다. 탐지·eviction·종료 훅·LB 전파가 시간을 소비합니다. 특히 MNG에서는 일부 Pod가 종료 신호를 받지 못할 수 있습니다. [S2] | 실제 SIGTERM 수신부터 종료까지의 시간, 강제 종료, 유실 요청 |
| PDB | Eviction API를 통한 자발적 중단을 제한합니다. 인스턴스 상실을 막지 못하며 Deployment 롤링 업데이트의 동시성을 제어하지도 않습니다. [S3] | drain 성공 여부와 강제 노드 상실 시 가용성을 별도로 평가 |
| 대체 용량 | 새 노드가 Ready가 되는 시점과 애플리케이션이 트래픽을 처리하는 시점은 다릅니다. [S2], [S4] | Node Ready → 이미지 pull → Pod Ready → LB target healthy → SLO 회복 |
| Spot 비중 | NodePool 우선순위나 허용 capacity type만으로 고정 비율을 보장하지 않습니다. [S5] | 실제 노드·vCPU·Pod·요청 비중을 각각 수집 |

### 운영 방식별 실험 경로

| 운영 방식 | 노드 capacity label | 중단 처리 확인 | On-Demand 전환 확인 |
|---|---|---|---|
| EKS Auto Mode | `karpenter.sh/capacity-type: spot` / `on-demand` | AWS 관리 기능과 Kubernetes 이벤트, NodeClaim 상태를 관찰. OSS Karpenter 설치 절차를 그대로 적용하지 않음. [S6] | NodePool과 Pod가 On-Demand를 허용하는지 확인 |
| 자체 운영 Karpenter | `karpenter.sh/capacity-type: spot` / `on-demand` | EventBridge → SQS → Karpenter `--interruption-queue`, IAM, 이벤트·컨트롤러 로그 확인. Rebalance recommendation 자체의 drain은 Spot interruption 처리와 다름. [S4] | NodePool의 `spot`·`on-demand` 허용과 Pod의 selector/affinity/taint 호환성 확인. [S5] |
| EKS Managed Node Group (MNG) | `eks.amazonaws.com/capacityType: SPOT` / `ON_DEMAND` | 관리형 Capacity Rebalancing과 실제 ASG 설정 확인. 교체 노드가 Ready일 때까지 항상 기다리는 것은 아님. [S2] | Spot MNG는 Spot 전용. 별도 On-Demand MNG와 Cluster Autoscaler 설정·스케줄 가능성을 검증. [S2] |

NodePool disruption budget을 `0`으로 설정해도 EC2 회수를 중지시키지 못합니다. 자체 Karpenter의 자발적 consolidation/drift와 Spot interruption을 서로 다른 실험으로 기록합니다. [S4] Auto Mode에 별도 Node Termination Handler를 추가하는 것을 실험의 전제로 삼지 않습니다.

## 2. 실험 환경과 대조군

실제 운영 클러스터를 기본 대상으로 사용하지 않습니다. 운영과 같은 배포물·네트워크·LB 경로를 가진 **지정된 테스트 클러스터**에서 시작합니다. 부하 발생기와 관측성 수집기는 회수 대상 밖에 둡니다.

### 실행 전에 고정할 기록

| 필드 | 기록할 값 |
|---|---|
| 실행 식별 | run ID, 담당자, UTC 시작/종료, 변경 Git SHA, FIS experiment ID |
| 플랫폼 | AWS 계정 별칭·리전, 테스트 클러스터, Kubernetes/플랫폼 버전, Auto Mode 또는 Karpenter/CA 버전 |
| 노드 | AMI/OS, 아키텍처, 인스턴스 타입·AZ 목록, NodePool/MNG 설정, limits·quota·서브넷 IP 여유 |
| 애플리케이션 | 이미지 digest, replicas, requests/limits, HPA, PDB, 배치 제약, 종료 훅, 재시도·타임아웃 |
| 트래픽 | endpoint/요청 종류, 입력 크기, 요청률·동시성, keep-alive, 재시도, 데이터 seed |
| 관측성 | 수집 간격, 대시보드·로그 쿼리, 클라이언트 원시 결과, clock 동기화, 보존 위치 |
| 비용 | 노드별 실제 사용 시간·요금 기준, 약정 할인 적용 방식, 부대 비용의 배분 규칙 |

계정 ID·내부 endpoint·고객 데이터는 공개 결과에 넣지 않고 별도 접근 통제된 원본에서 추적합니다. 모든 그룹에 같은 이미지 아키텍처를 사용합니다. 여러 인스턴스 타입을 허용할 때 MNG+CA는 유사한 vCPU·메모리 크기로 묶고, 아키텍처나 크기 변경의 효과를 Spot 효과와 섞지 않습니다. [S2]

### 비교 그룹

| 그룹 | 구성 | 목적 |
|---|---|---|
| A | On-Demand만 사용 | 같은 요청량에서 오류율·지연·처리량·비용 기준선 |
| B | On-Demand 최소 서비스 용량 + Spot 확장 용량 | 운영 도입 후보, 서비스 연속성과 비용 비교 |
| C | Spot만 사용 | 중단·용량 부족의 취약점 확인용 대조군. 운영 권장안이 아님 |

B의 예시는 **On-Demand 전용 Deployment 3 replicas + Spot 전용 Deployment 3 replicas**가 공통 Service의 선택 대상이 되는 구성입니다. 각각의 Deployment selector는 서로 겹치지 않는 고유 label을 사용하고, 공통 Service label만 공유합니다. 노드 수 50%, 비용 50%, 요청 50%를 뜻하지 않습니다.

이 고정 비중 실험과 **Spot 우선·On-Demand 허용 Deployment**의 폴백 실험은 구분합니다. Spot 전용 selector를 가진 Pod는 On-Demand 노드가 있어도 이동하지 못합니다. NodePool 하나가 양쪽 capacity type을 허용해도 On-Demand 최소 실행 용량은 보장되지 않습니다. [S5]

On-Demand 최소 용량은 임의 비율 대신 다음 가정으로 산정합니다.

```text
필요 생존 replicas = ceil(장애 중 유지할 요청률 / Pod당 SLO 만족 처리량)
장애 후 생존 replicas = 전체 replicas - 회수 대상 노드의 replicas
조건: 장애 후 생존 replicas >= 필요 생존 replicas
```

예를 들어 Pod당 100 RPS가 SLO를 만족하고 장애 중 300 RPS를 유지해야 한다는 **가정**이면 최소 3 replicas가 살아 있어야 합니다. 이는 CPU·메모리·연결 풀·다운스트림 용량까지 충족한다는 가정의 계산일 뿐, 3 replicas가 실제로 충분하다는 실험 결과가 아닙니다. AZ 장애까지 범위에 넣으면 해당 AZ의 On-Demand도 생존 용량에서 제외합니다.

처음에는 HPA와 자발적 consolidation 설정을 고정해 변수를 줄이고, 이후 운영 설정을 복원해 상호작용을 별도로 시험합니다. hostname/AZ topology spread, `DoNotSchedule`, `minDomains`, PV의 AZ 제약은 복구를 막을 수 있으므로 실제 노드 배치를 저장합니다. [S8]

## 3. 실험 목록과 합격 기준

**예시 공통 기준**: 준비 부하 10분, 안정 구간 15분, 주입·복구 구간, 회복 후 15분을 분리합니다. 장애 시나리오는 독립 실행 5회 이상을 출발점으로 삼고 시간대·대상 타입을 바꿉니다. 이 표본 수가 운영 신뢰도를 입증하지는 않습니다.

**예시 SLO**: 요청 오류율 0.1% 이하, 1분 구간 p99 500ms 이하, 복구 120초 이내, 확정된 작업 유실 0건. 실제 서비스의 기존 SLO와 error budget으로 교체한 뒤 실험을 시작합니다. 모든 HTTP 오류 외에 timeout, 연결 실패, 잘못된 응답 내용도 실패에 포함하고 원시 요청과 재시도 후 사용자 작업 성공을 따로 집계합니다.

| ID | 가설·자극 | 실행 방법 | 관찰·판정 |
|---|---|---|---|
| E0 | 정상 상태에서 B가 A와 같은 SLO를 만족 | A/B/C에 동일한 대표 부하; warm-up 제외 | 오류율, 지연 분포, 성공 처리량, 실제 Spot 비중 |
| E1 | drain과 앱 종료가 정상 | 테스트 노드 1개를 Eviction API 기반 drain; 끝나면 복구 | PDB 대기, 종료 훅, 진행 요청 완료. **실제 Spot 회수 시험을 대체하지 않음** |
| E2 | Spot 1대 회수 중 SLO 유지 | 아래 FIS 절차로 실제 Spot 인스턴스 1대 회수 | 통지→drain→교체→서비스 회복, 요청 실패·강제 종료 |
| E3 | 같은 pool의 동시 회수에도 생존 용량 유지 | E2 통과 후 동일 AZ·타입의 명시적 Spot 인스턴스 2대 동시 대상 지정 | 최대 동시 unavailable, PDB 차단, surviving replicas, 손실. 대상 없으면 N/A |
| E4 | Spot 공급이 없을 때 On-Demand로 복구 | 먼저 테스트용 배포를 On-Demand 전용으로 변경하는 전환 훈련. 별도로 아래 공급 부족 실험 | 전환 훈련과 실제 capacity-error 폴백 결과를 별도 판정 |
| E5 | 통지 처리가 없어도 서비스가 복구 | 전용 테스트 구성에서 interruption 경로 장애 또는 지정 Spot VM의 예고 없는 종료를 각각 시험 | 정상 통지 실험과 분리. 감지·재스케줄 지연, 신호 없는 작업 정합성 |
| E6 | 제약과 종료 지연이 실패로 드러남 | 별도 실행마다 PDB 차단, 긴 preStop, Spot-only affinity, AZ 제약 중 하나만 변경 | 예상된 실패를 탐지하는지, 원인과 운영 설정 수정 후 재실험 |
| E7 | 확장·축소와 회수가 겹쳐도 SLO 유지 | 실제 HPA/CA/Karpenter 설정 복원 후 대표 피크 부하 중 E2 | Pending, quota/IP, 이미지 pull, 신규 노드에서 SLO까지 걸리는 시간 |
| E8 | 작업 재처리가 정합성을 지킴 | 테스트 작업 ID 목록을 고정하고 처리 중 E2 | 제출·ack·영속 결과 대조. 중복 실행과 중복 부작용을 분리, 멱등성 검증 |
| E9 | 운영 비용 절감이 지속 | A/B의 비교 가능한 기간을 교차 배치하거나 동일 부하로 충분히 관측 | 성공 작업당 비용, 재시도·중복 용량·운영비 포함, 성능 회귀 없음 |

E3의 두 노드 종료는 **동시 Spot 회수**의 시험입니다. 네트워크·스토리지·On-Demand까지 상실하는 전체 AZ 장애를 재현한 것으로 보고하지 않습니다.

### E4: 전환 훈련과 공급 부족을 구분

NodePool을 On-Demand 전용으로 바꾸는 것은 구성 변경·스케줄링·이미지 기동 경로를 검증합니다. **EC2가 Spot 용량 부족을 반환했을 때의 자동 폴백을 검증하지는 않습니다.**

실제 부족 응답을 제어하려면 AWS FIS의 EC2 API insufficient-capacity 또는 ASG insufficient-capacity action이 해당 공급 경로에 맞는지 [공식 action reference][S9]와 현재 `get-action` 결과로 확인합니다. Karpenter가 호출하는 Fleet 경로, MNG의 ASG 경로, AWS가 관리하는 Auto Mode를 같은 방식으로 취급하지 않습니다. 전용 테스트 역할/ASG와 가용영역에 한정하고 On-Demand 공급 경로까지 막고 있지 않은지 검증합니다.

재현 가능한 부족 주입 경로가 없으면 E4의 **자동 폴백은 미검증**으로 남깁니다. Spot 시장에서 자연적으로 부족이 발생한 기록은 보조 증거로 사용하며, 일부러 좁은 타입·AZ를 선택했다고 반드시 부족이 발생한다고 가정하지 않습니다.

## 4. E2 재현: AWS FIS로 Spot 한 대 회수

### 사전 준비

실행 도구는 Bash, AWS CLI, kubectl, jq입니다.

1. 테스트 클러스터와 전용 실험 NodePool/MNG를 지정합니다. 대상 노드의 **모든 Pod**를 확인하여 업무 Pod나 공유 컨트롤러가 없도록 합니다. 필수 노드 DaemonSet은 목록과 리소스 사용량을 기록합니다.
2. 기존에 검토한 FIS 실행 역할과, 실제 서비스 오류율/지연을 감시하는 CloudWatch stop alarm을 준비합니다. 역할은 지정 실험 인스턴스/태그에만 action을 허용하며 `fis.amazonaws.com` 신뢰 관계, `SourceAccount`/`SourceArn` 제한과 호출자의 `iam:PassRole` 범위를 확인합니다. [S10]
3. alarm이 실제 지표를 받고 `OK`인지 확인하고, 오류 주입 전 alarm 전환 시험을 끝냅니다. 임계값·평가 주기·누락 데이터 처리 정책을 기록합니다.
4. UTC 타임스탬프가 있는 client 부하 로그와 Kubernetes/컨트롤러/LB 관측을 **주입 전에** 시작합니다.

다음은 실행할 셸에 직접 설정할 입력입니다. 테스트 대상이 확정되기 전에는 빈 값을 채우지 않습니다.

```bash
export SPOT_PROFILE=''
export SPOT_REGION=''
export SPOT_CLUSTER=''
export SPOT_NODE=''
export SPOT_INSTANCE_ID=''
export SPOT_RUN_ID=''
export SPOT_FIS_ROLE_ARN=''
export SPOT_STOP_ALARM_ARN=''
```

별도 kubeconfig를 사용해 워크스테이션의 기본 current-context를 변경하지 않습니다. 아래 조회 결과의 cluster ARN·인스턴스 lifecycle·providerID·배치 Pod를 대조합니다. node label만으로 EC2 Spot 여부를 판정하지 않습니다.

```bash
set -euo pipefail
: "${SPOT_PROFILE:?}" "${SPOT_REGION:?}" "${SPOT_CLUSTER:?}"
: "${SPOT_NODE:?}" "${SPOT_INSTANCE_ID:?}" "${SPOT_RUN_ID:?}"
: "${SPOT_FIS_ROLE_ARN:?}" "${SPOT_STOP_ALARM_ARN:?}"
umask 077
SPOT_RESULT_DIR=$(mktemp -d "$PWD/eks-spot-run.XXXXXX")
SPOT_KUBECONFIG="$SPOT_RESULT_DIR/kubeconfig"
spot_aws() { aws --profile "$SPOT_PROFILE" --region "$SPOT_REGION" --output json "$@"; }
spot_kubectl() { kubectl --kubeconfig "$SPOT_KUBECONFIG" "$@"; }

spot_aws eks update-kubeconfig --name "$SPOT_CLUSTER" \
  --kubeconfig "$SPOT_KUBECONFIG" --alias "$SPOT_CLUSTER"
spot_aws sts get-caller-identity > "$SPOT_RESULT_DIR/caller.json"
spot_aws eks describe-cluster --name "$SPOT_CLUSTER" \
  > "$SPOT_RESULT_DIR/cluster.json"
spot_kubectl get node "$SPOT_NODE" -o json \
  > "$SPOT_RESULT_DIR/node-before.json"
spot_kubectl get pods -A --field-selector "spec.nodeName=$SPOT_NODE" -o json \
  > "$SPOT_RESULT_DIR/pods-on-target.json"
spot_aws ec2 describe-instances --instance-ids "$SPOT_INSTANCE_ID" \
  > "$SPOT_RESULT_DIR/instance-before.json"

jq -e --arg id "$SPOT_INSTANCE_ID" \
  '.spec.providerID | endswith("/" + $id)' \
  "$SPOT_RESULT_DIR/node-before.json"
jq -e '[.Reservations[].Instances[]] |
  length == 1 and .[0].InstanceLifecycle == "spot" and .[0].State.Name == "running"' \
  "$SPOT_RESULT_DIR/instance-before.json"
```

`caller.json`, `cluster.json`의 계정·리전·클러스터가 지정한 테스트 환경과 일치하는지, 대상 노드가 실험 전용인지 확인한 다음 템플릿을 작성합니다. 다음 JSON을 `$SPOT_RESULT_DIR/fis-template.example.json`에 저장합니다. 실행 전 아래 명령이 예시 ARN을 검증한 입력값으로 교체합니다. **명시적 ARN 1개와 COUNT(1)**을 유지합니다.

```json
{
  "description": "E2: interrupt one isolated EKS Spot test node",
  "roleArn": "arn:aws:iam::111122223333:role/eks-spot-test-fis",
  "targets": {
    "oneSpotNode": {
      "resourceType": "aws:ec2:spot-instance",
      "resourceArns": ["arn:aws:ec2:ap-northeast-2:111122223333:instance/i-0123456789abcdef0"],
      "selectionMode": "COUNT(1)"
    }
  },
  "actions": {
    "interrupt": {
      "actionId": "aws:ec2:send-spot-instance-interruptions",
      "parameters": {"durationBeforeInterruption": "PT2M"},
      "targets": {"SpotInstances": "oneSpotNode"}
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:111122223333:alarm:eks-spot-test-slo"
    }
  ]
}
```

FIS는 이 action에서 실제 인스턴스를 중단시킵니다. 시작 시 rebalance recommendation도 발생하므로 E2는 interruption notice만 독립적으로 검증하는 시험이 아닙니다. `durationBeforeInterruption`을 애플리케이션의 종료 유예 시간으로 해석하지 말고 실제 이벤트 시각을 기록합니다. [S7], [S9]

템플릿의 대상을 다시 읽어 확인한 후 실행합니다. alarm stop이나 `stop-experiment`가 이미 전달된 회수 요청을 취소하거나 종료된 인스턴스를 복구한다고 가정하지 않습니다. 후속 주입 중단과 서비스 복구는 별도입니다. [S11]

```bash
SPOT_ACCOUNT_ID=$(jq -r '.Account' "$SPOT_RESULT_DIR/caller.json")
SPOT_PARTITION=$(jq -r '.Arn | split(":")[1]' "$SPOT_RESULT_DIR/caller.json")
SPOT_INSTANCE_ARN="arn:$SPOT_PARTITION:ec2:$SPOT_REGION:$SPOT_ACCOUNT_ID:instance/$SPOT_INSTANCE_ID"
jq --arg instance "$SPOT_INSTANCE_ARN" \
  --arg role "$SPOT_FIS_ROLE_ARN" --arg alarm "$SPOT_STOP_ALARM_ARN" \
  '.roleArn = $role |
   .targets.oneSpotNode.resourceArns = [$instance] |
   .stopConditions[0].value = $alarm' \
  "$SPOT_RESULT_DIR/fis-template.example.json" > "$SPOT_RESULT_DIR/fis-template.json"

SPOT_TEMPLATE_ID=$(spot_aws fis create-experiment-template \
  --cli-input-json "file://$SPOT_RESULT_DIR/fis-template.json" \
  --query experimentTemplate.id --output text)
spot_aws fis get-experiment-template --id "$SPOT_TEMPLATE_ID" \
  > "$SPOT_RESULT_DIR/template-resolved.json"

# 대상 검토와 관측 시작 후 실행: 실제 테스트 인스턴스가 회수됩니다.
SPOT_EXPERIMENT_ID=$(spot_aws fis start-experiment \
  --experiment-template-id "$SPOT_TEMPLATE_ID" \
  --tags "RunId=$SPOT_RUN_ID" \
  --query experiment.id --output text)
spot_aws fis get-experiment --id "$SPOT_EXPERIMENT_ID" \
  > "$SPOT_RESULT_DIR/experiment-start.json"
spot_aws fis list-experiment-resolved-targets \
  --experiment-id "$SPOT_EXPERIMENT_ID" \
  > "$SPOT_RESULT_DIR/targets.json"
```

상태가 terminal이 될 때까지 `get-experiment`를 조회하고, resolved target이 의도한 인스턴스 1개인지 확인합니다. `completed`는 fault action의 완료이며 **서비스 SLO 통과를 의미하지 않습니다**. `failed`/`stopped`/대상 없음은 통과 처리하지 않습니다. [S7]

## 5. 측정과 결과 기록

### 관측 시각

| 시각 | 증거 |
|---|---|
| T0 | FIS action 시작, 실제 resolved target |
| T1 | EventBridge 이벤트의 `time`, 관측자의 수신·처리 시각. 중단 예정 시각은 IMDS `spot/instance-action` 또는 출처를 명시한 컨트롤러 기록에서 확인할 수 있을 때만 별도 기록 |
| T2 | cordon/taint, eviction 시작, Pod의 SIGTERM/종료 로그 |
| T3 | 대상 EC2 상태 변화, 대체 인스턴스 생성, Node Ready |
| T4 | 대체 Pod Ready, EndpointSlice 상태, LB target healthy |
| T5 | 서비스 오류율·지연·처리량이 정한 기준을 연속 5분 충족하기 시작한 시각 |

복구 시간은 **T0부터 T5까지**를 기본으로 보고하고, 첫 SLO 위반부터 회복까지도 별도로 보고합니다. 전체 시간 동안 기준을 지켰다면 서비스 중단 시간은 0초이고, 노드/Pod 교체 시간은 별도 측정값입니다. 계측이 누락된 경우 0초로 기록하지 않습니다.

EventBridge 이벤트에는 별도의 중단 예정 시각 필드가 없습니다. IMDS의 예정 시각도 근사값이며, 수집할 수 없으면 측정값 없음으로 남깁니다. 이를 채우기 위해 Auto Mode 노드 접근을 요구하지 않습니다. 추론한 시각은 추정으로 표시하고 실제 EC2 상태 변화는 T3에 기록합니다. [S1]

실험 전·중·후에 Node/Pod JSON, events, PDB, EndpointSlice, NodePool/MNG 설정을 보존합니다. events의 TTL과 로그 수집 지연 때문에 종료 후 한 번 조회하는 것만으로는 충분하지 않습니다. 자체 Karpenter는 컨트롤러·SQS 지표, MNG는 ASG activity, Auto Mode는 관리 기능이 제공하는 이벤트를 추가합니다.

LB의 5xx 지표만으로 성공 여부를 판단하지 않습니다. client의 connection reset/timeout/DNS 실패와 응답 검증을 포함하고, 클라이언트의 재시도가 장애를 가렸는지도 확인합니다. p99는 각 구간의 원시 표본 또는 합친 histogram으로 계산하며 **여러 p99의 평균을 전체 p99로 보고하지 않습니다**.

### 실험 진행 현황

실측 세부 수치는 7절과 원시 데이터에서 확인합니다. 미실행·미검증은 통과가 아닙니다. 모든 측정은 합성 HTTP 요청에 한정하며 업무 데이터 유실·중복 부작용은 측정하지 않았습니다.

| 실험 | 실제 실행 범위 | 상태 |
|---|---|---|
| E0 | 정상 부하 120초, 세 관측 경로 | 1회 측정, 각 경로 2,400건 성공 |
| E1 | 전용 Spot 노드 drain, 180초 관측 | 1회 측정, 혼합 경로 8건 실패 |
| E2 | FIS로 Spot 1대 회수, 900초 관측 | 1회 측정, 혼합 경로 10건 실패 |
| E3 | 동시 회수 | 미실행 |
| E4 | Pod selector를 On-Demand로 바꾸는 전환, 240초 관측 | 1회 측정. 실제 capacity-error 자동 폴백은 미검증 |
| E5 | 예고 없는 상실·통지 전달 장애 | 미실행 |
| E6 | PDB `minAvailable: 2`로 eviction 거부 확인 후 1로 복원 | 일부 실행. 종료 훅·AZ 제약 시험은 미실행 |
| E7 | 피크 부하·HPA 상호작용 | 미실행 |
| E8 | 업무 작업 정합성 | 미실행 |
| E9 | 인스턴스 시간당 가격 조회 | 단가 스냅샷만 확보. 실제 청구·성공 작업당 절감률은 미측정 |

각 실행에는 `가설 → 주입 사실 → 관측 → 판정 → 원인 → 수정 → 재실험 run ID`를 연결합니다. 실패와 제외 표본도 남기고, run별 결과·중앙값·최악값을 함께 보고합니다. 통지 미수신, 수집 실패, 부하 발생기 포화는 결과에서 숨기지 않습니다.

### 비용 계산

```text
실효 비용 =
  실제 Spot/On-Demand 사용 비용
  + 교체 중 중복 노드·재시도에 소비된 추가 용량 비용
  + 해당 워크로드에 배분한 EBS·LB·전송·관측성·EKS/Auto Mode 비용

성공 작업당 비용 = 실효 비용 / 정합성 검증을 통과한 고유 성공 작업 수
절감률 = 1 - (B의 성공 작업당 비용 / A의 성공 작업당 비용)
```

실제 EC2 청구 금액에 중복 노드·재시도 비용이 이미 포함되어 있다면 **다시 더하지 않습니다**. 식의 두 번째 항은 누락을 막기 위한 귀속 항목입니다. 고정 EKS 비용은 공유 배분 규칙을 명시하고, FIS 실험 비용은 운영 지속 비용과 분리합니다.

단기 실행 시간을 월 사용량으로 확장한 값에는 **추정**이라고 표시합니다. Spot 할인율 하나로 절감률을 확정하지 않고, A에 적용되는 Savings Plans/RI의 실제 할인·미사용 약정 영향을 같은 기준으로 반영합니다. 금액은 리전·시점별 billing export로 확인합니다. [S12]

## 6. 운영 도입과 롤백

### 도입 판정

| 판정 | 조건 |
|---|---|
| 도입 가능 | 합의한 필수 시나리오 통과, 대표 부하·정합성 증거 확보, 비용 개선 확인, On-Demand 복구 훈련 완료 |
| 조건부 도입 | 제한을 구체적으로 적고 해당 워크로드·Spot 상한·기간·담당자 범위에서만 canary |
| 확대 보류 | 필수 실험 미실행, 증거 누락, SLO 위반, 유실·중복 부작용, 복구 용량 부족, 자동 폴백 미검증 |

상태를 외부 영속 저장소에 두는 stateless API, 재시도·멱등성을 검증한 worker부터 후보로 삼습니다. quorum이나 로컬 데이터·종료 유예에 의존하는 워크로드는 별도의 복제·복구 검증 없이 같은 결론을 적용하지 않습니다. 시스템 제어·관측 기능의 생존 용량도 유지합니다.

예시 확대 순서는 **테스트 → 특정 서비스 canary → 검증된 범위 내 확대**입니다. 각 단계에서 실제 Spot vCPU·Pod·트래픽 비중과 error budget을 다시 확인합니다. “전체의 70% Spot” 같은 비율을 기본 정답으로 두지 않습니다.

### 롤백 절차

1. 새로운 fault 주입과 Spot 확대를 중단합니다. 진행 중 FIS는 `stop-experiment`를 요청하고 이미 예약된 회수의 후속 영향을 계속 관찰합니다.
2. 검증한 On-Demand 구성을 GitOps 원본에 적용합니다. controller와 ad-hoc patch가 서로 덮어쓰지 않도록 변경 소유자를 명확히 합니다.
3. On-Demand 공급 한도·서브넷 IP·Pod 스케줄 제약을 확인하고 대체 Deployment를 확장합니다. 새 Pod Ready와 LB target healthy, 서비스 SLO를 확인합니다.
4. 필요 생존 용량을 확보한 뒤 Spot 전용 Deployment를 단계적으로 축소합니다. 기존 Pod는 NodePool 허용 타입만 바꿔도 즉시 이동하지 않습니다.
5. 오류율·지연·작업 정합성을 재확인하고 실행 기록을 보존합니다. 원인 수정과 재실험을 통과하기 전에는 Spot 비중을 다시 확대하지 않습니다.

### 정리

결과를 접근 통제된 영속 저장소로 먼저 내보냅니다. 실험 전후 manifest를 비교해 HPA/PDB/스케줄링/중단 처리 설정을 복원하고, E1에서 cordon한 생존 노드는 의도에 맞게 uncordon합니다. 본 실험에서 만든 FIS 템플릿·alarm·테스트 workload·전용 노드만 삭제합니다. 노드 관리자가 다시 생성하지 않도록 원하는 용량을 먼저 조정하고, EBS·LB 등 잔존 비용도 확인합니다. `/tmp` 기록은 영구 보관소가 아닙니다.

## 7. 2026-09-12 실측 결과

### 환경과 해석 범위

기존 EKS 테스트 클러스터에 전용 namespace·NodePool·EC2NodeClass를 만들고, 새로 만든 Spot 인스턴스 한 대만 FIS 대상으로 지정했습니다. 기존 Karpenter Pod 설정은 실험 전후 동일했으며, 실험 자원은 결과 내보내기 후 삭제·검증했습니다.

| 항목 | 실제 조건 |
|---|---|
| 플랫폼 | EKS 1.36 / kubelet `1.36.3-eks-cb19647`, Karpenter `1.4.0` |
| 노드 | arm64 `c6g.large`, 실제 배치 AZ ID `apne2-az1`, 초기 On-Demand 1대 + Spot 2대 |
| 허용 범위와 실제 배치 | 인스턴스 타입 4개·AZ 2개를 허용했지만 초기 노드는 같은 타입·같은 AZ에 배치됨 |
| 애플리케이션 | Fortio `1.69.4`, 이미지 digest 고정, Pod requests `50m` / `64Mi`, 종료 유예 30초, readiness 주기 2초 |
| 배치 | Spot Pod 2개에 hostname anti-affinity, PDB `minAvailable: 1` |
| 요청 | 경로별 20 RPS, HTTP GET `/`, 응답 본문 0바이트, 요청마다 새 연결, 재시도 없음 |
| 계측 | 전용 On-Demand Pod의 Python 3.12 probe, 요청별 JSONL, Kubernetes 약 5초 간격 관측, 별도 EventBridge 관측 큐 |
| 보호 알람 | 관측한 혼합 경로 오류율 5% 초과 또는 누락 데이터, 10초 주기·2개 중 2개. 설계 예시의 합격 기준 0.1%와 구분 |

**지원 버전 구성의 검증 결과가 아닙니다.** 확인한 공식 호환성 표는 Kubernetes 1.36에 Karpenter **1.13 이상**을 요구합니다. 설치된 1.4.0은 이 하한보다 낮습니다. 버전 변경의 효과는 이번에 측정하지 않았습니다. [S13]

Karpenter에는 interruption queue가 설정되어 있지 않았습니다. 새로 만든 큐는 이벤트를 기록하는 **관측용 큐**였으며 Karpenter에 연결하지 않았습니다. 따라서 이 결과를 중단 처리가 구성된 Karpenter의 일반 동작으로 확대 해석하지 않습니다.

On-Demand 기준선은 3개 Pod이고, 혼합 경로는 On-Demand 1개 + Spot 2개 Pod입니다. Spot 관측 경로는 혼합 경로의 동일한 Spot Pod 2개를 선택합니다. 기준선·혼합의 안정 Pod·부하 발생기는 On-Demand 노드를 공유하므로 세 경로는 독립적인 비용·처리량 비교군이 아닙니다. E4의 원시 파일 이름 `spot-only`는 전환 대상 Service 이름이며, 전환 후에는 On-Demand Pod를 선택합니다.

### 요청 결과

각 실험은 **1회** 실행했습니다. 모든 경로에서 계획한 요청을 전부 전송했고 generator skip은 0건이었습니다. 실패에는 HTTP 응답 오류뿐 아니라 연결 오류와 socket timeout을 포함합니다. p99는 실패 요청의 지연까지 포함한 원시 표본의 nearest-rank 값입니다.

| 실험 / 경로 | 요청 수 | 실패 | 전체 오류율 | 전체 p99 | 최악 60초 오류율 |
|---|---:|---:|---:|---:|---:|
| E0 / On-Demand 기준선 | 2,400 | 0 | 0% | 3.41 ms | 0% |
| E0 / 혼합 | 2,400 | 0 | 0% | 4.90 ms | 0% |
| E0 / Spot 관측 경로 | 2,400 | 0 | 0% | 3.91 ms | 0% |
| E1 / On-Demand 기준선 | 3,600 | 0 | 0% | 5.93 ms | 0% |
| E1 / 혼합 | 3,600 | 8 | 0.2222% | 3.30 ms | 0.5833% |
| E1 / Spot 관측 경로 | 3,600 | 1 | 0.0278% | 5.11 ms | 0.0833% |
| E2 / On-Demand 기준선 | 18,000 | 0 | 0% | 5.17 ms | 0% |
| E2 / 혼합 | 18,000 | 10 | 0.0556% | 5.63 ms | 0.8333% |
| E2 / Spot 관측 경로 | 18,000 | 5 | 0.0278% | 5.09 ms | 0.4167% |
| E4 / On-Demand 기준선 | 4,800 | 0 | 0% | 5.60 ms | 0% |
| E4 / 혼합 | 4,800 | 9 | 0.1875% | 6.20 ms | 0.5833% |
| E4 / 전환 대상 코호트 | 4,800 | 16 | 0.3333% | 6.99 ms | 1.3333% |

60초 오류율은 **완전히 관측한 60초 창을 1초씩 이동**해 구한 최댓값입니다. 마지막의 불완전한 창은 제외합니다. E2 혼합 경로는 전체 오류율 0.0556%·p99 5.63ms만 보면 안정적으로 보이지만, 최악 60초 오류율은 0.8333%로 사전에 작성한 설계 예시 기준 0.1%를 초과했습니다. 실제 서비스의 SLO가 합의된 것은 아니며 이 기준은 실험 진단용입니다.

E1·E4에서도 요청 실패를 관측했습니다. 노드 drain이나 Deployment rollout의 완료를 무오류 전환으로 간주하지 않습니다. 실패 시작부터 마지막 실패 완료까지의 간격은 **연속 장애 시간이나 서비스 복구 시간**이 아닙니다. 원시 기록을 보존했으며 다른 시점에 발생한 실패도 제외하지 않았습니다.

![Spot 회수 전후 요청 오류, 요청 지연, Ready Pod 수의 실측 시계열](../../assets/experiments/eks-spot/2026-09-12-interruption.png)

그래프는 E2의 전체 관측 구간입니다. 지연 축은 로그 스케일이며 1초당 표본은 약 20개입니다. 짧은 구간 p99와 전체 p99를 혼동하지 않습니다. 색 영역은 node shutdown 보고부터 대체 Pod Ready까지로, 서비스 전체의 중단 시간을 뜻하지 않습니다.

### 회수 시간선

| 관측 | UTC 시각 | 근거 |
|---|---|---|
| FIS action 시작 | 14:06:40.998 | FIS `startTime` |
| 중단 통지 | 14:06:41 | EventBridge event `time` |
| FIS `completed` | 14:06:41.755 | FIS `endTime` — 실제 서비스 회복과 다름 |
| kubelet node shutdown / 기존 Pod 종료 | 14:08:45 | `KubeletNotReady`, `TerminationByKubelet` |
| 대체 NodeClaim 생성 | 14:08:48.212 | Karpenter 컨트롤러 로그 |
| 대체 Node Ready | 14:09:23 | Node condition |
| 대체 Pod Ready | 14:09:29 | Pod condition |

중단 통지 후에도 대상 노드는 회수 전까지 스케줄 가능한 상태로 관측됐고, 대체 NodeClaim은 node shutdown 이후 생성됐습니다. **node shutdown 보고부터 대체 Pod Ready까지 44초**였습니다. 이는 서비스 복구 시간이나 44초의 연속 중단을 의미하지 않습니다. Pod 종료는 kubelet 상태 기록으로 확인했으며 애플리케이션의 SIGTERM 수신 시각은 별도 계측하지 않았습니다. API 관측 간격과 이벤트 시각의 초 단위 정밀도도 고려해야 합니다.

### 전환·비용·판정

수동 On-Demand 전환은 **47.05초**에 rollout을 완료했고, 전환 대상 Pod의 실제 노드 label도 On-Demand로 확인했습니다. EC2 용량 부족 응답은 주입하지 않았으므로 **자동 폴백은 미검증**입니다.

2026-09-12 14:08:41 UTC 가격 조회에서 `c6g.large` Linux의 On-Demand 공개 단가는 **$0.077/시간**, 해당 AZ의 Spot 단가는 **$0.0248/시간**이었습니다. 단가 차이는 **67.79%**이지만, 이는 실제 청구나 서비스 절감률이 아닙니다. EBS·EKS·FIS·관측성·약정 할인·재시도·대체 용량의 비용과 동일한 가용성 조건을 함께 비교해야 합니다.

운영 확대 전에는 다음 검증이 필요합니다.

1. Kubernetes와 호환되는 Karpenter 버전으로 맞추고 CRD·IAM·업그레이드 경로를 검증합니다.
2. 실제 Karpenter interruption queue와 EventBridge·IAM 경로를 구성한 후 같은 회수 시험을 반복합니다. 관측용 큐의 통지 수신만으로 완료 처리하지 않습니다.
3. 실제 애플리케이션의 종료 처리, readiness 전파, 클라이언트 재시도와 외부 LB 경로에서 요청 SLO를 검증합니다.
4. On-Demand 최소 생존 용량, AZ 배치, 실제 공급 부족 폴백과 동시 회수를 검증합니다.
5. 대표 업무 부하·정합성·여러 시간대의 반복 실행·실효 비용 증거를 확보합니다.

실험용 namespace, NodePool 2개, EC2NodeClass, 신규 인스턴스 프로파일, FIS 템플릿·역할, 알람, EventBridge rule, SQS 큐를 삭제했습니다. **실험의 실행 중 EC2 인스턴스·잔존 EBS 볼륨·Kubernetes 자원은 0개**로 확인했습니다. AWS가 보존하는 FIS 실행 이력과 metric 데이터는 남습니다.

[측정 도구와 테스트](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/eks/spot-production), [요청별 원시 데이터·집계·시계열](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/eks/spot-production/results/2026-09-12)을 제공합니다. 공개 데이터에서 계정·노드·네트워크 식별자는 제외했으며, 상세 인프라 원본은 별도 보관했습니다.

## 8. 관련 문서와 근거

- [스케일링 전략](./06-scaling-strategies.md)
- [이벤트 용량 계획](./12-event-capacity-planning.md)
- [FinOps 비용 관리](./13-finops-cost-platform.md)
- [트러블슈팅 플레이북](./16-troubleshooting-playbook.md)
- [이 문서의 퀴즈](../quizzes/ops/17-spot-production-experiments-quiz.md)

공식 문서는 서비스 동작의 근거이며 이 저장소에서 실험을 수행했다는 증거가 아닙니다. 링크 확인일: 2026-09-12.

[S1]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html
[S2]: https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
[S3]: https://kubernetes.io/docs/concepts/workloads/pods/disruptions/
[S4]: https://karpenter.sh/docs/concepts/disruption/
[S5]: https://karpenter.sh/docs/concepts/nodepools/
[S6]: https://docs.aws.amazon.com/eks/latest/userguide/automode.html
[S7]: https://docs.aws.amazon.com/fis/latest/userguide/fis-tutorial-spot-interruptions.html
[S8]: https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/
[S9]: https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html
[S10]: https://docs.aws.amazon.com/fis/latest/userguide/getting-started-iam-service-role.html
[S11]: https://docs.aws.amazon.com/fis/latest/userguide/stop-experiment.html
[S12]: https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html

[S13]: https://karpenter.sh/docs/upgrading/compatibility/
