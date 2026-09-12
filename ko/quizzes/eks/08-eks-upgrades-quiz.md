# Amazon EKS 업그레이드 퀴즈

> **마지막 업데이트**: 2026년 9월 12일

이 퀴즈는 Amazon EKS 클러스터 업그레이드 프로세스, 모범 사례, 문제 해결 및 관련 고려 사항에 대한 이해를 테스트합니다.

## 퀴즈 개요

- EKS 클러스터 업그레이드 계획
- 컨트롤 플레인 업그레이드
- 노드 그룹 업그레이드
- 애드온 및 구성 요소 업그레이드
- 업그레이드 테스트 및 검증
- 업그레이드 문제 해결

## 객관식 문제

### 1. Amazon EKS 클러스터 업그레이드를 계획할 때 가장 중요한 첫 번째 단계는 무엇인가요?

- A. 즉시 컨트롤 플레인 업그레이드
- B. 모든 워크로드를 한 번에 업그레이드
- C. 호환성을 검토하고 테스트·복구 계획 수립
- D. 모든 노드 그룹 동시 업그레이드

<details>
<summary>정답 보기</summary>

**정답: C. 호환성을 검토하고 테스트·복구 계획 수립**

변경 순서를 정하기 전에 대상 EKS 버전, API 변경 사항과 워크로드 의존성을 검토합니다. 호환성 인벤토리는 판단 근거이며 가용성 인증이 아닙니다.

**호환성 검토**

- 매니페스트, Helm 릴리스, API 클라이언트, CRD, 변환·어드미션 웹훅, 오퍼레이터를 확인합니다. CNI/DNS, 로드 밸런서, 서비스 메시, 스토리지, 모니터링, 로깅, 백업도 포함합니다.
- 지원 클러스터 버전은 EKS 클러스터 버전 카탈로그에서 확인합니다. `describe-addon-versions`는 특정 Kubernetes 버전과 호환되는 애드온 버전을 조회합니다.
- EKS Upgrade Insights와 접근 가능한 감사 로그·메트릭을 대표성 있는 기간에 걸쳐 검토합니다. API 서버가 노출하는 관련 메트릭은 `apiserver_requested_deprecated_apis`입니다. 시계열 부재, 조회 거부, 빈 스캔 결과가 오래된 API 클라이언트의 부재를 증명하지 않습니다. Insights에는 관찰 기간 내 과거 사용이 남을 수 있습니다.
- 객체의 현재 `.apiVersion`은 응답 표현의 버전이며, 클라이언트가 원래 요청한 버전과 다를 수 있습니다. 배포 설정·소스와 실제 호출자를 함께 검토합니다.

[본문](../../eks/08-eks-upgrades.md)의 `eks-upgrade-preflight.py`를 저장하고 전제 조건을 확인한 다음 읽기 전용 계정·컨텍스트·대상 버전 인벤토리를 실행합니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

이 도우미는 조회 오류를 실패로 처리합니다. `preflight.json`의 모든 결과를 검토해야 하며, 도우미가 업그레이드를 실행하거나 호환성을 인증하지는 않습니다. 현재 AWS 카탈로그에서 현재 버전보다 한 마이너 높은 지원 버전을 선택합니다.

검토한 Pluto 릴리스로 렌더링한 매니페스트, Helm 메타데이터와 last-applied 설정을 검사합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"; : "${MANIFEST_DIR:?}"
pluto detect-files --directory "$MANIFEST_DIR" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-helm --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-api-resources --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
```

앞 명령이 0이 아닌 종료 코드를 반환하면 블록이 중단되므로 결과를 처리한 뒤 나머지 검사도 완료합니다. API 리소스 검사는 저장된 어노테이션에 의존하며 모든 런타임 요청을 관찰하지 못합니다. kube-no-trouble 프로젝트의 실행 파일은 `kubent`이며 `kubectl-no-trouble`이 아닙니다.

**과거 API 제거 사례** — 마이그레이션 이력이며 현재 EKS 업그레이드 대상이 아닙니다.

| Kubernetes 릴리스 | 제거된 서빙 API / 마이그레이션 |
| --- | --- |
| 1.22 | `networking.k8s.io/v1beta1` Ingress 등 여러 베타 API. 안정 API와 변경된 필드 스키마로 이전 |
| 1.25 | `policy/v1beta1` PodSecurityPolicy 제거: 정책 집행 방식 이전. `batch/v1beta1` CronJob → `batch/v1` |
| 1.26 | `autoscaling/v2beta2` HPA → `autoscaling/v2`; 흐름 제어 `v1beta1` 제거 |
| 1.27 | `storage.k8s.io/v1beta1` CSIStorageCapacity → `storage.k8s.io/v1` |
| 1.29 / 1.32 | FlowSchema / PriorityLevelConfiguration의 `v1beta2` / `v1beta3` 각각 제거. 필드·기본값 변경을 반영하여 `flowcontrol.apiserver.k8s.io/v1` 사용 |

kubelet 1.25 이상은 업스트림 정책상 API 서버보다 최대 세 마이너 이전까지 허용되며 API 서버보다 최신일 수 없습니다. 1.25 미만 kubelet은 두 마이너 제한입니다. HA 업그레이드 중 API 서버 버전이 섞이면 허용 범위가 좁아집니다. 이는 지원 범위이지 모든 애드온·애플리케이션의 동작 보장이 아닙니다. 보수적인 EKS 준비 절차는 다음 컨트롤 플레인 업그레이드 전에 노드를 **현재** 컨트롤 플레인 버전으로 맞추는 것입니다.

**리허설과 계획 템플릿**

검토한 인프라 정의로 네트워크, IAM, 컴퓨팅 유형, 데이터와 컨트롤러를 대표하는 별도 환경을 준비합니다. 운영 환경과의 차이, 비용과 정리 담당자를 기록합니다. 개발·스테이징부터 비즈니스 기능, 확장, 복구, 알림을 검증하며 운영 환경에 사전 점검의 일부로 장애를 주입하지 않습니다. 기존 1.27→1.28 예시는 과거 사례이며 현재 프로비저닝 권고가 아닙니다.

```markdown
# EKS upgrade plan — fill from evidence, not assumed results

- Account / Region / cluster ARN / kube context: TBD
- Current / target minor and EKS support status: TBD
- Node groups, Fargate, Auto Mode, hybrid nodes: inventory required
- Add-on / controller / CRD / webhook versions and owner: TBD
- Compatibility evidence, observation window and unresolved findings: TBD
- Backup coverage, application consistency, restore test and RPO/RTO: TBD
- Subnet IPs, EC2 quotas, placement, surge capacity and cost: TBD
- Rehearsal environment and differences from production: TBD

## Ordered change gates

- [ ] Align nodes to the current control-plane version; verify supported skew
- [ ] Complete API migrations and any required bridge add-on versions
- [ ] Complete a representative non-production rehearsal
- [ ] Upgrade the control plane by one minor; verify the exact update ID
- [ ] Upgrade nodes/add-ons in their reviewed dependency order
- [ ] Verify workloads and monitor agreed SLOs before retiring old capacity

## Test coverage and evidence

- [ ] Deployments: create, readiness, rollout and scaling
- [ ] StatefulSets / PVCs: write, reschedule, read and restore
- [ ] Services, DNS, Ingress / Gateway and external dependencies
- [ ] Jobs / CronJobs, operators, CRDs and admission webhooks
- [ ] API latency, Pod startup, network and resource baselines
- [ ] Controlled node/network/resource-pressure recovery in a test environment
- [ ] Alert delivery and incident ownership
- Result / timestamp / environment / evidence location: NOT RUN

## Recovery decision

- Stop criteria and incident owner: TBD
- Previous minor, upgrade completion time and 7-day rollback deadline: TBD
- Rollback eligibility, compute-type order and add-on compatibility: TBD
- Data restore or forward-fix procedure when version rollback is unsuitable: TBD
```

실제 관찰을 기록하고 “모두 호환됨” 또는 “CRD 변경 없음”을 미리 채우지 않습니다. 버전 롤백은 애플리케이션 데이터를 복원하지 않습니다. 5번에서 자격 조건과 컴퓨팅 유형별 순서를 다룹니다. A, B, D는 근거를 생략하거나 너무 많은 변경을 묶어 진단·복구를 어렵게 합니다.

출처: [API 마이그레이션](https://kubernetes.io/docs/reference/using-api/deprecation-guide/), [버전 차이 정책](https://kubernetes.io/releases/version-skew-policy/), [EKS 업그레이드](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [Pluto](https://pluto.docs.fairwinds.com/), [kube-no-trouble](https://github.com/doitintl/kube-no-trouble).

</details>

### 2. 사전 노드 버전 정렬을 마친 뒤 다음 마이너 버전으로 인플레이스 업그레이드하는 올바른 순서는 무엇인가요?

- A. API 서버가 이전 버전인 동안 kubelet을 대상 마이너 버전으로 올림
- B. 컨트롤 플레인을 대상 마이너 버전으로 올린 뒤 노드 그룹을 검토한 단계에 따라 업그레이드
- C. 컨트롤 플레인과 대상 버전 노드 변경을 모두 동시에 시작
- D. 마이너 업그레이드마다 반드시 새 클러스터 생성

<details>
<summary>정답 보기</summary>

**정답: B. 컨트롤 플레인을 대상 마이너 버전으로 올린 뒤 노드 그룹을 검토한 단계에 따라 업그레이드**

노드를 **현재** 컨트롤 플레인 마이너 버전으로 맞추는 작업은 준비 단계입니다. **대상** 마이너 버전으로 올리는 것은 컨트롤 플레인이 해당 버전을 지원한 뒤입니다. EKS는 한 번에 한 마이너씩 업그레이드합니다. 지원되는 버전 차이가 애플리케이션 호환성을 보장하지는 않습니다. 컨트롤 플레인 변경 전에 필요할 수 있는 중간 애드온 버전을 포함하여 구성 요소별 의존성을 따릅니다.

**준비와 실행**

1. 계정, 컨텍스트, 현재·대상 지원 상태, 클러스터·노드 상태, Insights, 서브넷 IP 여유와 접근을 확인합니다. 교체 용량과 워크로드 중단 제어를 계획합니다.
2. 백업과 복원을 검증합니다. EKS 사용자는 관리형 컨트롤 플레인의 etcd에 `etcdctl`을 실행할 수 없습니다. `kubectl get all`은 여러 리소스와 영구 데이터를 누락합니다. 적절히 구성한 AWS Backup EKS 또는 Velero·애플리케이션 백업의 범위와 복원을 테스트합니다.
3. 1번 사전 점검을 검토합니다. 아래 별도 변경 단계 전에 [본문](../../eks/08-eks-upgrades.md)의 `eks-wait-update.py`를 저장합니다. 검토한 대상에 충돌하는 업데이트가 없어야 합니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${AWS_REGION:?Set the reviewed Region}"
: "${TARGET_VERSION:?Set the next supported EKS minor version}"
umask 077
aws eks update-cluster-version \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --output json --no-cli-pager \
  > control-plane-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' control-plane-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

폴러는 해당 요청을 추적합니다. `Successful`만 성공이며 실패, 취소, 알 수 없는 상태와 API 오류는 절차를 중단합니다. 클라이언트 타임아웃이 AWS 작업을 취소하지는 않습니다. `ACTIVE`만으로 해당 요청의 성공을 판단할 수 없으며, `aws eks wait update-successful`이라는 EKS CLI waiter는 없습니다.

대안인 `eksctl upgrade cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --version "$TARGET_VERSION"`은 미리보기이며 `--approve`를 추가하면 변경을 시작합니다. CLI와 Terraform을 모두 제출하지 말고 한 소유자·실행 경로를 선택합니다.

**요청 성공 후 확인**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,platformVersion:platformVersion}'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl --context "$KUBE_CONTEXT" get --raw='/readyz'
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -n kube-system
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp'
```

API readiness 엔드포인트에는 권한이 필요하며 여러 신호 중 하나일 뿐입니다. 폐기된 `ComponentStatus` 객체나 존재한다고 가정한 관리형 etcd Pod 대신 실제 워크로드, DNS와 컨트롤러를 확인합니다. 순수 Auto Mode는 노드 수준 CoreDNS를 사용하며 혼합 클러스터는 비 Auto 노드용 DNS를 유지합니다. 표준 `aws-node`, kube-proxy 또는 CoreDNS Deployment가 없다는 이유만으로 Auto Mode 장애라고 판단하지 않습니다. `kubectl top`에는 Metrics Server가 필요하며 메트릭 가용성과 요청 성공은 별도입니다.

검토한 노드 그룹·카나리 하나와 필요한 애드온 순서부터 진행하고 단계마다 검증합니다. Auto Mode는 컨트롤 플레인 업그레이드 후 노드를 관리합니다. 기존 Fargate Pod의 kubelet 버전은 유지되므로 소유 컨트롤러를 통한 교체와 가용성을 조율합니다.

**가용성과 시간**

기존 “20–30분”에는 제공된 측정 출처가 없으므로 과거 계획 예시로만 보존하며 소요 시간 보장이 아닙니다. 리허설을 바탕으로 유지 관리 시간을 확보합니다. API 서버 교체 시 클라이언트가 다시 연결해야 합니다. 기존 컨테이너는 계속 동작할 수 있지만 API 의존 컨트롤러·애플리케이션은 영향을 받을 수 있습니다. 시작한 일반 컨트롤 플레인 업그레이드는 일시 중지·취소할 수 없습니다. 업데이트 ID·오류를 보존하고 필요하면 AWS Support에 문의합니다. 이후 버전 롤백에는 별도 자격 조건이 있습니다.

**Terraform 소유권 예시**

기존 리소스·모듈의 다른 설정과 의존성을 유지하며 수정합니다. 아래는 완전한 정의가 아니며 기존 클러스터용 두 번째 리소스를 생성하라는 의미도 아닙니다.

```hcl
# Fragment of the existing, state-managed cluster resource.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.target_version

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.cluster_security_group_id]
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

기존 IAM, 서브넷, 보안 그룹과 검토한 대상을 전달하고 provider plan에서 의도하지 않은 교체·변경을 확인합니다. `prevent_destroy`는 Terraform 삭제를 막을 뿐 서비스 중단을 막지 않습니다. 빈 `ignore_changes = []`는 대기·검증을 하지 않으며 provider에는 자체 waiter·타임아웃이 있습니다. IaC 타임아웃은 서비스 취소가 아니고 Git revert도 EKS 버전 롤백이 아닙니다. 변경 후 6번의 제한된 검증을 수행합니다. 이번 검토에서는 실제 클러스터에 실행하지 않았습니다.

A는 kubelet을 API 서버보다 최신으로 만듭니다. C는 검증 단계를 없앱니다. D는 틀렸습니다. 새 클러스터 마이그레이션은 트래픽·데이터 이전 비용이 있는 선택지입니다.

출처: [EKS 업데이트](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [EKS 백업](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html), [Terraform EKS 리소스](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 3. EKS 노드 그룹을 통제된 단계로 업그레이드하는 접근은 무엇인가요?

- A. 모든 노드를 동시에 종료
- B. 단계적 관리형 노드 그룹 업데이트 또는 검증한 블루/그린 마이그레이션
- C. 노드 버전을 계속 그대로 유지
- D. 관리형 노드의 kubelet 바이너리를 개별 교체

<details>
<summary>정답 보기</summary>

**정답: B. 단계적 관리형 노드 그룹 업데이트 또는 검증한 블루/그린 마이그레이션**

워크로드의 중단 허용 범위, 용량, 영구 스토리지와 컴퓨팅 소유자를 고려해 전략을 선택합니다. 관리형 업데이트와 블루/그린 모두 무중단을 보장하지는 않습니다.

**관리형 노드 그룹**

`DEFAULT` 업데이트 전략은 기존 노드를 제거하기 전에 교체 용량을 생성하고, `MINIMAL`은 기존 용량을 먼저 제거합니다. `maxUnavailable`은 동시 비가용 범위를 제한합니다. 일반 롤링 eviction 경로는 PDB를 따르지만 강제 업데이트는 우회할 수 있습니다. 이 전략과 콘솔의 rolling/force 선택은 별개입니다. 업데이트 실패가 자동 fleet 롤백을 뜻하지는 않습니다.

본문의 `eks-wait-update.py`를 저장하고 1번 계정·컨텍스트·용량 검토를 마칩니다. EKS 최적화 AMI를 사용하는 기존 그룹은 Kubernetes 버전과 호환 AMI 릴리스를 명시적으로 선택합니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${TARGET_VERSION:?Set the reviewed target, no newer than the control plane}"
: "${TARGET_AMI_RELEASE:?Set the reviewed EKS-optimized AMI release}"
umask 077
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" --output json > nodegroup-before.json
if jq -e '.nodegroup.amiType == "CUSTOM"' nodegroup-before.json >/dev/null; then
  echo "Use the custom launch-template path for this node group" >&2
  exit 1
fi
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --release-version "$TARGET_AMI_RELEASE" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

요청·폴링 실패 시 중단합니다. 다음 그룹 전에 실제 노드 버전·Ready 상태, Pod 배치, 이벤트와 애플리케이션 SLO를 확인합니다. 사용자 지정 AMI라면 **처음 사용한 동일 launch template**의 검토한 새 버전을 사용하고 `--kubernetes-version`, `--release-version`은 생략합니다. 본문의 별도 custom-AMI 경로를 따릅니다. kubelet 패키지만 교체하고 AMI·런타임·bootstrap까지 업그레이드됐다고 가정하지 않습니다.

`eksctl upgrade nodegroup`은 `--kubernetes-version`, `eksctl create nodegroup`은 `--version`을 사용합니다. 생성 시 지원되지 않는 `--taints`나 불완전한 단일 명령 대신 기존 클러스터 설정 파일에 검토한 서브넷, IAM, AMI, 레이블과 taint를 유지합니다.

**블루/그린 순서**

1. blue 용량을 유지합니다. 인프라 소유자를 통해 컨트롤 플레인보다 최신이 아닌 green 버전, 호환 AMI·아키텍처, 사설 네트워크, 충분한 quota·IP·AZ 용량을 준비합니다.
2. green 노드 Ready와 DNS·네트워크·스토리지·워크로드 의존성을 확인합니다. 적합한 워크로드가 toleration을 갖출 때까지 green에 카나리용 taint를 둡니다.
3. 워크로드 Pod template을 단계적으로 이전합니다. preferred affinity는 선호도일 뿐 기존 Pod를 이동시키지 않습니다. 배치가 필수이면 명시적 선택 조건과 소유자를 통한 통제된 rollout을 사용합니다.
4. 기존 노드의 워크로드를 확인하며 하나씩 drain합니다. eviction 실패 시 중단하고 노드 종료로 진행하지 않습니다.
5. 워크로드·데이터·트래픽 근거와 복구 기간을 검토한 뒤 blue를 제거합니다. “yes” 응답이나 Ready 노드 목록은 마이그레이션 완료 증거가 아닙니다.

아래는 기존 앱을 대체하는 매니페스트가 아닌 완전한 **독립 카나리 fixture**입니다. 네임스페이스를 의도적으로 준비합니다. 필수 hostname anti-affinity 때문에 적격 Linux green 노드가 최소 3개 필요합니다. toleration은 taint를 허용하고 node selector가 green을 선택합니다. 실제 앱 이미지·설정, 중단 정책과 rollout 매개변수는 별도로 조정합니다.

```yaml
# Independent fixture in an explicitly prepared test namespace.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  replicas: 3
  selector:
    matchLabels:
      app: upgrade-canary
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
        example.com/upgrade: green
      tolerations:
        - key: example.com/upgrade
          operator: Equal
          value: green
          effect: NoSchedule
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: upgrade-canary
              topologyKey: kubernetes.io/hostname
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: http
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - mkdir -p /tmp/www; printf 'ok\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 5
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: upgrade-canary
```

Deployment 자체 롤링 업데이트는 PDB가 아닌 해당 strategy로 제어됩니다. PDB는 자발적 eviction을 제어하며 일반 Deployment·ReplicaSet 축소나 모든 인프라 종료를 막지 않습니다. 적격 용량이 없어지면 필수 anti-affinity가 스케줄링을 막을 수 있습니다. 이 fixture의 이미지·클러스터 실행은 검증하지 않았습니다.

검토한 기존 노드 하나에 본문의 제한된 drain을 사용하면 unmanaged Pod와 `emptyDir` 데이터 보호를 유지합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

drain 실패 후 노드가 cordon 상태이거나 일부만 비워졌을 수 있으므로 의도적으로 조사·복구합니다. 마이그레이션을 끝내기 위해 `--force`, `--delete-emptydir-data`, `--disable-eviction`을 무조건 추가하지 않습니다.

**Terraform 블루/그린 예시**

기존 리소스 주소·설정을 유지합니다. EKS 최적화 AMI용 아래 발췌는 **두 그룹 모두** 양의 용량을 유지하며 green taint는 위 카나리와 일치합니다.

```hcl
# Existing blue resource address is retained; green is separate capacity.
# Inputs describe reviewed EKS-optimized AMIs, not a custom launch template.
variable "capacity" {
  type    = object({ desired = number, min = number, max = number })
  default = { desired = 3, min = 3, max = 6 }
  validation {
    condition = (
      var.capacity.min >= 1 &&
      var.capacity.desired >= var.capacity.min &&
      var.capacity.max >= var.capacity.desired &&
      alltrue([for n in values(var.capacity) : floor(n) == n])
    )
    error_message = "Retain positive integer capacity: 1 <= min <= desired <= max."
  }
}

resource "aws_eks_node_group" "blue" {
  cluster_name    = var.cluster_name
  node_group_name = "blue-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.blue_version
  release_version = var.blue_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "blue" }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "green" {
  cluster_name    = var.cluster_name
  node_group_name = "green-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.green_version
  release_version = var.green_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "green" }
  taint {
    key    = "example.com/upgrade"
    value  = "green"
    effect = "NO_SCHEDULE"
  }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}
```

기존 클러스터·역할·서브넷, 호환 인스턴스 유형·AMI 계열, 개별 검토한 blue/green 버전·릴리스를 전달합니다. 컨트롤 플레인이 green 버전을 이미 지원해야 합니다. `desired_size` 무시 규칙은 autoscaler가 해당 필드를 소유한다는 가정이며 Terraform 소유라면 제거합니다. min/max 변경은 여전히 적용되며 관리형 노드 그룹의 scaling 설정 변경은 PDB를 따르지 않습니다. green 생성과 동시에 Boolean 스위치로 blue를 0으로 줄이거나 유효하지 않은 `max_size = 0`을 사용하지 않습니다. 노드 생성, 워크로드 이전과 제거는 별도 변경이며 Terraform 의존성만으로 워크로드 준비를 증명하지 못합니다.

복구 기준을 미리 정합니다. blue가 유지되어도 워크로드 배치를 되돌리려면 API·데이터 호환성이 필요합니다. 컨트롤 플레인·MNG 버전 롤백에는 5번의 추가 조건이 있습니다. A, C, D는 중단 범위를 넓히거나 지원되지 않는 버전 차이를 쌓거나 관리형 교체 생명주기를 우회합니다.

출처: [관리형 노드 업데이트](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html), [업데이트 동작](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [PDB](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/), [Terraform 노드 그룹](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group).

</details>

### 4. EKS 업그레이드 중 애드온 관리의 올바른 접근은 무엇인가요?

- A. 애드온 업그레이드 무시
- B. 호환성과 관계없이 모든 애드온을 컨트롤 플레인보다 먼저 업그레이드
- C. 호환 버전을 선택하고 구성 요소별 의존성·중간 버전 순서를 따름
- D. 모든 애드온 제거 후 재설치

<details>
<summary>정답 보기</summary>

**정답: C. 호환 버전을 선택하고 구성 요소별 의존성·중간 버전 순서를 따름**

“모든 애드온을 컨트롤 플레인 이후에”라는 보편적 규칙은 없습니다. 일부는 변경 전에 두 컨트롤 플레인 버전에 호환되는 중간 버전이 필요하고, 일부는 변경 후에 진행합니다. 각 릴리스의 지원 Kubernetes, 아키텍처, 컴퓨팅 유형, API와 업그레이드 경로를 확인합니다. EKS 관리형 애드온 버전은 컨트롤 플레인과 함께 자동 업그레이드되지 않으며, “관리형”이 모든 보안 릴리스의 자동 설치를 보장하지도 않습니다.

**검사·선택·설정 보존**

설치되어 있고 소유권이 확인된 관리형 애드온 하나의 현재 상태, 호환 후보와 검토한 후보의 스키마를 확인합니다. 배열의 첫 요소가 “최신 호환 버전”이라는 계약은 없습니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"
: "${TARGET_VERSION:?Set the Kubernetes version for this stage}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json > addon-before.json
aws eks describe-addon-versions --addon-name "$ADDON_NAME" \
  --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json > addon-candidates.json
# Select ADDON_VERSION after reviewing compatibility, architecture, compute type, and upgrade path.
: "${ADDON_VERSION:?Set the reviewed add-on version}"
aws eks describe-addon-configuration --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --output json > addon-schema.json
jq -r '.addon.configurationValues // "{}"' addon-before.json > addon-config-candidate.json
```

`addon-before.json`에는 버전·설정·identity 정보가 있습니다. `aws-node` ConfigMap 하나는 완전한 CNI 백업이 아니며 DaemonSet 설정, 사용자 지정 리소스, IAM·Pod Identity도 중요할 수 있습니다. 근거 파일을 보호합니다. `addon-config-candidate.json`은 검토 입력이지 자동으로 유효한 대상 설정이 아닙니다. 새 스키마에 맞춰 의도한 설정을 병합하고 제거·기본값 필드와 릴리스 노트를 확인합니다.

검토 후 본문의 요청별 폴러와 완전한 대상 설정 파일을 사용합니다.

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"; : "${ADDON_VERSION:?}"
: "${REVIEWED_ADDON_CONFIG_FILE:?Provide the complete reviewed target configuration JSON}"
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG_FILE" \
  --resolve-conflicts PRESERVE --output json > addon-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' addon-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID ADDON_NAME
unset NODEGROUP_NAME
python3 eks-wait-update.py
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json
```

`PRESERVE`는 기존 필드 충돌을 처리하며 명시적 설정 payload의 전체 병합·수락·정상 동작을 보장하지 않습니다. `NONE`은 충돌 시 실패하고 `OVERWRITE`는 사용자 설정을 EKS 기본값으로 바꿀 수 있습니다. 덮어쓰기를 자동 복구 지름길로 사용하지 않습니다. 다음 의존성 전에 요청 성공과 애드온·워크로드 동작을 모두 확인합니다. 30초 sleep은 완료 확인이 아닙니다.

**구성 요소별 확인**

| 구성 요소 | 다음 단계 전 확인 |
| --- | --- |
| VPC CNI | 지원 업그레이드 경로, IP 할당, 노드·Pod 네트워크, custom networking과 IAM |
| CoreDNS | DNS 해석, Corefile·스키마 변경, 스케줄링·readiness·PDB |
| kube-proxy | Kubernetes 버전 차이, Service 접근과 실제 데이터 플레인 |
| Cluster Autoscaler | 지원 Kubernetes 마이너, discovery·IAM·확장 소유권 |
| Metrics Server | 지원 버전, APIService 가용성과 kubelet TLS·접근 |
| Load Balancer Controller / ExternalDNS / mesh | 컨트롤러·차트·CRD·API 호환성, IAM, 웹훅과 트래픽 동작 |

순수 Auto Mode는 노드 수준 DNS·네트워크를 제공하여 표준 노드 애드온과 요구 사항이 다릅니다. 혼합 클러스터는 CoreDNS Deployment를 포함하여 비 Auto 노드가 필요로 하는 구성 요소를 유지해야 합니다. 업그레이드·제거 전에 소유자를 확인합니다.

**Terraform 관리 애드온**

기존 state 소유 리소스에 검토한 버전·설정 맵을 사용하고 IAM·Pod Identity를 유지합니다. 아래 발췌는 표준 노드용이며 모든 Auto Mode에 설치하라는 의미가 아닙니다.

```hcl
# Fragments of existing, imported/state-managed standard-node add-ons.
# Preserve each resource's existing IAM/Pod Identity settings as applicable.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = var.cluster_name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions["vpc-cni"]
  configuration_values        = file(var.addon_config_files["vpc-cni"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions["coredns"]
  configuration_values        = file(var.addon_config_files["coredns"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = var.cluster_name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions["kube-proxy"]
  configuration_values        = file(var.addon_config_files["kube-proxy"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

현재 provider는 `resolve_conflicts_on_create`와 `resolve_conflicts_on_update`를 구분합니다. 생성은 `PRESERVE`를 받지 않으며 `NONE`은 마이그레이션 충돌을 드러내도록 선택한 값입니다. 애드온 업데이트를 위해 중복 클러스터 리소스를 추가하지 않습니다. 현재 단계에 예정된 구성 요소만 변경합니다. 독립 리소스 3개를 나열해도 안전한 업데이트 순서가 정해지지는 않습니다. 리소스 삭제·설정 변경에는 별도 검토가 필요합니다.

**자체 관리 Helm 릴리스**

기존 릴리스 소유자, 검토한 차트 참조·버전과 이전한 values를 사용합니다. 설치, 소유권 마이그레이션과 업그레이드는 별개입니다. CRD, identity, ServiceAccount, 리소스·스케줄링과 기존 동작을 보존합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${RELEASE:?}"; : "${ADDON_NAMESPACE:?}"
: "${CHART_REF:?Set the verified repository/chart or OCI reference}"
: "${CHART_VERSION:?Set a reviewed compatible chart version}"
: "${REVIEWED_VALUES_FILE:?Set the complete reviewed target values file}"
umask 077
helm get values "$RELEASE" --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > addon-values-before.yaml
helm show values "$CHART_REF" --version "$CHART_VERSION" > addon-values-defaults.yaml
# Merge/migrate values and handle CRDs/IAM through the owner before this step.
helm upgrade "$RELEASE" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  -f "$REVIEWED_VALUES_FILE" --wait --timeout 15m
```

마지막 명령 전에 검토한 values를 준비합니다. `--wait`가 애플리케이션 SLO나 모든 CRD 마이그레이션을 확인하지는 않습니다. 업그레이드 중 중복 컨트롤러를 일괄 설치하거나 무관한 autoscaler 플래그를 변경하지 않습니다. 각 릴리스의 Pod·이벤트·대표 기능을 검증하고, 무조건 완료를 출력하지 말고 실패를 기록합니다.

A는 보안·호환성 유지 관리를 무시합니다. B는 아직 이전 버전인 컨트롤 플레인과 호환되지 않는 버전을 설치할 수 있습니다. D는 불필요하게 소유권·설정을 잃고 네트워크·DNS를 중단할 수 있습니다.

출처: [EKS 애드온 업데이트](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html), [Auto Mode 네트워크](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [Terraform 애드온](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon), [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/).

</details>

### 5. EKS 업그레이드 중 문제를 해결하는 가장 효과적인 접근은 무엇인가요?

- A. 즉시 새 클러스터 생성
- B. 근거 수집 없이 AWS Support에만 의존
- C. 체계적 문제 해결, 로그 분석과 가설 검증
- D. 업그레이드 문제 무시

<details>
<summary>정답 보기</summary>

**정답: C. 체계적 문제 해결, 로그 분석과 가설 검증**

증상, 시작 시각, 영향받는 워크로드와 비즈니스 영향을 정의하고 구체적 변경과 연결합니다. 근거를 수집한 뒤 가설을 검증합니다. 예상 영향을 검토한 표적 수정 후 복구를 확인하고 예방책을 기록합니다. 가능한 원인은 확정된 근본 원인이 아닙니다.

**읽기 전용 진단**

계정·컨텍스트와 정확한 작업 ID를 확인합니다. 다음 수집기는 조회 전에 작업 유형을 검증하고 새 비공개 근거 디렉터리를 사용합니다. 조회 실패 시 중단하며 이미 기록한 파일은 부분 근거이지 진단 성공이 아닙니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${UPDATE_ID:?Set the exact affected update ID}"
: "${ISSUE_KIND:?Set control-plane, nodegroup, or addon}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
args=(--name "$CLUSTER_NAME" --region "$AWS_REGION" --update-id "$UPDATE_ID")
case "$ISSUE_KIND" in
  control-plane) ;;
  nodegroup) : "${NODEGROUP_NAME:?}"; args+=(--nodegroup-name "$NODEGROUP_NAME") ;;
  addon) : "${ADDON_NAME:?}"; args+=(--addon-name "$ADDON_NAME") ;;
  *) echo "Unknown ISSUE_KIND" >&2; exit 2 ;;
esac
umask 077
EVIDENCE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-upgrade-diagnosis.XXXXXXXX")
printf 'Evidence directory: %s\n' "$EVIDENCE_DIR"
aws eks describe-update "${args[@]}" --output json --no-cli-pager \
  > "$EVIDENCE_DIR/update.json" 2> "$EVIDENCE_DIR/update.stderr"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,health:health,logging:logging}' \
  --output json --no-cli-pager > "$EVIDENCE_DIR/cluster.json"
kubectl --context "$KUBE_CONTEXT" get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl --context "$KUBE_CONTEXT" get pods -A -o wide > "$EVIDENCE_DIR/pods.txt"
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp' \
  > "$EVIDENCE_DIR/events.txt"
printf 'Snapshots collected; review errors and workload evidence before changing anything.\n'
```

노드 그룹·애드온 작업은 `describe-nodegroup`·`describe-addon`으로 해당 리소스의 `health.issues`, 버전·설정도 확인합니다. 상황에 따라 노드 ProviderID, EC2 상태, IAM·bootstrap·AMI·네트워크와 스케줄링 제약을 조사합니다. 업데이트 `Failed`만으로 원인을 추정해 확정하지 않습니다.

제한된 시간 범위에서 기존 컨트롤 플레인 로그를 읽습니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${START_TIME_MS:?Set the reviewed start timestamp in epoch milliseconds}"
: "${END_TIME_MS:?Set the reviewed analysis-window end timestamp}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.logging' --output json --no-cli-pager
# Read existing logs; enabling logging is a separate change and does not backfill history.
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
```

로깅 활성화는 별도 클러스터 변경이며 과거 이벤트를 소급 수집하지 않습니다. 로그 그룹 부재, 권한 오류, 빈 결과는 관찰 한계입니다. 관련 Pod가 있으면 명시적으로 검사합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${AFFECTED_NAMESPACE:?}"; : "${AFFECTED_POD:?}"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" describe pod "$AFFECTED_POD"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" logs "$AFFECTED_POD" \
  --all-containers=true --prefix=true --since=15m --tail=100
```

Pod 에이전트 로그가 호스트 kubelet·런타임 journal 전체는 아닙니다. Auto Mode, Fargate, 표준 EC2의 진단 접근은 다릅니다. 스냅샷을 보호하고 AWS Support에 공유하기 전 민감 설정을 가립니다. 무차별 클러스터 dump는 피합니다.

| 증상 | 근거로 검증할 가설 |
| --- | --- |
| 컨트롤 플레인 요청 실패 | 정확한 업데이트 오류, 전제 조건, 서브넷 IP·보안 그룹, AWS 서비스 측 실패 |
| 노드 NotReady / Pod Pending | AMI·bootstrap, EC2 용량, IAM·네트워크·CNI, taint·affinity·PVC topology·리소스 |
| 애드온 CrashLoopBackOff | 설정·스키마, identity, 이미지·시작, 리소스 또는 버전 호환성 |
| 앱 API 오류 | 제거된 API 호출자, 어드미션·변환 웹훅, 권한 또는 앱 회귀 |

재시도, 노드 그룹 삭제, 애드온 설정 덮어쓰기는 진단이 아닙니다. 애드온 복구에는 호환 버전과 검토한 설정·identity가 모두 필요하며 4번처럼 정확한 요청을 추적합니다.

**현재 EKS 롤백 조건**

현재 EKS 가이드는 조건부 인플레이스 컨트롤 플레인 롤백을 지원합니다. 애플리케이션 데이터 복원이나 실패 노드 교체와 별개입니다.

- 완료된 인플레이스 업그레이드 후 7일 안에 바로 이전 마이너로 시작합니다. 현재 버전으로 생성한 클러스터는 대상이 아니며 여러 번 연속으로 더 이전 마이너까지 되돌릴 수 없습니다.
- 대상 버전이 계속 지원되어야 합니다. 연장 지원 대상에는 `EXTENDED` 정책과 요금이 필요합니다. 연장 지원 종료 시 자동 업그레이드는 롤백할 수 없으며 표준 지원 종료 사례에는 문서의 정책 조건이 적용됩니다.
- `ACTIVE`, 충돌 업데이트, 하위 호환되지 않는 기능과 다른 전제 조건을 확인합니다. `ROLLBACK_READINESS`의 `ERROR`·`UNKNOWN`은 차단하고 `WARNING`은 권고입니다. `--force`는 insight 검사를 우회할 뿐 자격·전제 조건이나 Auto Mode 중단 제어는 우회하지 않습니다. 일반 업그레이드 insight의 `--force` 강제가 일시 철회된 것과 구분합니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

개별 항목은 `describe-insight --id "$INSIGHT_ID"`로 검사합니다. 빈 insight 목록을 모든 전제 조건 충족의 증거로 취급하지 않습니다.

| 컴퓨팅 유형 | 순서와 제한 |
| --- | --- |
| 관리형 노드 그룹 | 본문과 custom-AMI 조건에 따라 해당 그룹에 `UpdateNodegroupVersion`을 먼저 수행하고 실제 노드를 확인한 뒤 컨트롤 플레인 롤백 |
| 자체 관리 / hybrid | 소유자가 컨트롤 플레인 이전에 호환 노드와 워크로드 이전을 조율 |
| Auto Mode | 서비스가 노드부터, 이후 컨트롤 플레인을 롤백. 노드 단계에서 클러스터가 `ACTIVE`여도 Update ID 추적 |
| Fargate | kubelet 인플레이스 롤백 없음. 컨트롤 플레인 롤백 전에 새 버전 Pod가 즉시 다시 생성되지 않도록 Pod·컨트롤러·HPA·GitOps·Job 동작과 가용성을 조율 |

해당 노드 순서와 모든 전제 조건을 검증한 뒤 컨트롤 플레인은 `rollback-cluster`가 아닌 `update-cluster-version`을 사용합니다. 먼저 본문 폴러를 저장합니다.

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ROLLBACK_VERSION:?}"
: "${WAIT_TIMEOUT_SECONDS:?Set an explicit client wait for the approved rollback}"
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID WAIT_TIMEOUT_SECONDS
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

Auto Mode는 본문의 대안 `--rollback-config timeoutMinutes=...` 요청을 사용하며 두 요청을 동시에 제출하지 않습니다. 기본값 720분, 범위 120–10080분이고 정확한 완료 시한은 아닙니다. 0 drift budget이나 노드 disruption 제외가 진행을 막을 수 있습니다. PDB·Pod disruption 제외는 termination grace period와 상호작용하므로 무기한 보호를 뜻하지 않습니다. `--force`로 이 제어를 우회하지 못합니다.

컨트롤 플레인 롤백 전 Auto Mode 노드 단계만 best-effort `CancelUpdate`를 지원하며 진행 중 disruption은 끝날 수 있습니다. 타임아웃·취소 시 컨트롤 플레인은 그대로이고 노드는 해당 버전으로 다시 조정됩니다. 클라이언트 타임아웃 자체는 작업 취소가 아닙니다. 재시도도 원래 자격 기간 안이어야 합니다.

롤백은 etcd·워크로드·PV 데이터를 보존하며 백업으로 복원하지 않습니다. 애드온은 자동으로 되돌리지 않습니다. 이전 마이너의 최신 플랫폼 버전으로 돌아가므로 과거 플랫폼과 정확히 같지 않을 수 있습니다. CloudFormation 롤백이나 Git revert가 이 서비스 작업은 아닙니다. 본문의 전체 판단 절차를 따릅니다. 이번 검토에서 AWS에 해당 명령을 실행하지 않았습니다.

**장애 기록**

원래 시각을 아래에 보존합니다. 시나리오와 주장된 원인에는 제공된 장애 근거가 없으므로 가설을 담은 예시로 유지합니다.

```markdown
# Upgrade troubleshooting report — illustrative, not a verified incident

## Problem description

- Example symptom: CoreDNS Pods in CrashLoopBackOff after a node-group update
- Example impact: service discovery and application connections affected
- Original illustrative timestamp: 2023-07-15 14:30 UTC
- Provenance: no incident logs or measurement evidence supplied

## Investigation

1. Record the exact update ID, versions, changes and affected workloads.
2. Inspect CoreDNS logs/events, node conditions and resource availability.
3. Compare the owned Corefile/configuration with the reviewed baseline.
4. Check connectivity, network policies, scheduling and dependency changes.

## Hypotheses, not established findings

- A configuration parsing error is one possible explanation.
- A ConfigMap modification requires a diff/audit record and relevant log evidence.
- Record evidence that supports or rejects each hypothesis.

## Conditional remediation

1. If a configuration regression is demonstrated, restore compatible reviewed settings.
2. Coordinate any restart with replicas, readiness, PDB and DNS availability.
3. Verify service discovery and application SLOs, not just Pod phase.

## Prevention and record

- Version and back up owned configuration; rehearse restoration.
- Add regression checks and staged rollout gates.
- Actual actions, results and evidence: NOT RUN / TO BE RECORDED.
```

정확한 Update ID, 제한된 로그·오류, 영향과 시도한 조치를 AWS Support에 제공합니다. A는 원인 해결 없이 미계획 마이그레이션을 추가할 수 있고 B는 유용한 근거를 생략하며 D는 신뢰성·보안 문제를 방치합니다.

출처: [EKS 롤백](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), [Auto Mode 롤백](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html), [EKS 문제 해결](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html).

</details>

### 6. 업그레이드 후 가장 포괄적인 검증 접근은 무엇인가요?

- A. 노드 수만 확인
- B. 클러스터 버전만 확인
- C. 요청 상태·구성 요소·워크로드 기능·대표 성능을 단계별 검증
- D. 검증 없이 운영 트래픽 전체를 즉시 전달

<details>
<summary>정답 보기</summary>

**정답: C. 요청 상태·구성 요소·워크로드 기능·대표 성능을 단계별 검증**

먼저 정확한 업데이트 요청, 버전과 노드·애드온 상태를 확인하고 기능을 실행하여 기록한 기준선과 앱 메트릭을 비교합니다. smoke test 통과는 운영 준비나 SLO 증명보다 좁은 결과입니다.

| 영역 | 근거 |
| --- | --- |
| 컨트롤 플레인 | 요청 결과, API readiness·응답과 지원 메트릭·로그. 관리형 etcd 직접 접근 불가 |
| 노드 | Ready 조건, 예상 kubelet·AMI·런타임, 스케줄링과 컴퓨팅 유형별 상태 |
| 네트워크 | Pod·Service·DNS, Ingress·Gateway, egress와 의존성 접근 |
| 스토리지 | 프로비저닝, 소비자 간 쓰기·읽기, topology, 재스케줄링과 앱 일관성 복원 |
| 보안 | 의도한 인증·인가, Pod 보안, NetworkPolicy와 암호화 동작 |
| 워크로드 | Deployment rollout·확장, StatefulSet, Job·CronJob, CRD·오퍼레이터·웹훅 |
| 성능 | 비교 가능한 요청률, 지연·오류 분포, 시작 시간과 대표 기간의 리소스 사용 |

컨텍스트, 호환 StorageClass, CSI driver·IAM, 스케줄링, admission·네트워크 정책과 비용을 확인한 뒤 본문의 `eks-upgrade-smoke.py`로 제한된 Linux EC2 테스트를 수행합니다. 제공된 구현을 로컬에 저장합니다. 정의되지 않은 검증 이미지·스크립트를 참조하는 예제가 아닙니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test cluster context}"
: "${TEST_STORAGE_CLASS:?Set an existing compatible test StorageClass}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
python3 eks-upgrade-smoke.py
```

도우미는 고유 namespace와 UID를 만들고 Deployment rollout·확장, 20회 HTTP 요청, 별도 Job을 통한 PVC marker 쓰기·읽기를 수행합니다. binding 대기 전에 writer를 생성하여 `WaitForFirstConsumer`가 소비자를 스케줄링할 수 있고 reader 전에 writer를 제거합니다. 실패하면 근거·리소스를 보존합니다. 선택적 성공 정리는 동일 namespace UID를 확인하며 `Retain` PV에는 비용이 남을 수 있습니다. 모든 워크로드·복원 절차·Fargate·Auto 구성·성능 한계·보안 제어를 테스트하지는 않습니다.

표에서 추가 기능·부하 검사를 소유자와 검토합니다. `kubectl top`은 Metrics Server에 의존하는 현재 사용량이며 처리량·지연 증명이 아닙니다. 운영에 무제한 wget 루프를 사용하지 않습니다. 대상 트래픽, 기간, 성공·오류 기준, 기준선, 환경 차이와 실제 결과를 기록하며 합성 fixture로 벤치마크를 추정하지 않습니다.

**선택적 Terraform fixture**

네임스페이스·Deployment·Service·PVC 학습 예제를 별도 fixture로 유지합니다. 검토한 컨텍스트에 provider를 구성하고 새 namespace·호환 StorageClass를 전달하여 plan을 확인합니다. 기존 namespace를 인수·삭제하지 않습니다. 이 코드는 fixture이지 자동 검증 판정이 아닙니다.

```hcl
# Separate disposable fixture; configure the Kubernetes provider/context externally.
variable "validation_namespace" {
  type = string
  validation {
    condition     = can(regex("^eks-upgrade-validation-[a-z0-9]{8,16}$", var.validation_namespace))
    error_message = "Supply a new, unique namespace with the required validation prefix."
  }
}
variable "test_storage_class" {
  type = string
  validation {
    condition     = length(trimspace(var.test_storage_class)) > 0
    error_message = "Select an existing compatible test StorageClass."
  }
}

resource "kubernetes_namespace_v1" "validation" {
  metadata {
    name = var.validation_namespace
  }
}

resource "kubernetes_persistent_volume_claim_v1" "validation_pvc" {
  metadata {
    name      = "validation-pvc"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_until_bound = false
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = var.test_storage_class
    resources {
      requests = { storage = "1Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "validation_app" {
  metadata {
    name      = "validation-app"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_for_rollout = true
  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "validation-app" }
    }
    template {
      metadata {
        labels = { app = "validation-app" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "http"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args = [
            "test -f /data/index.html || printf 'fixture\\n' > /data/index.html; exec httpd -f -p 8080 -h /data"
          ]
          port {
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "8080"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "data"
            mount_path = "/data"
          }
        }
        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.validation_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "validation_service" {
  metadata {
    name      = "validation-service"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  spec {
    selector = { app = "validation-app" }
    type     = "ClusterIP"
    port {
      port        = 80
      target_port = "8080"
    }
  }
}
```

`wait_until_bound = false`로 `WaitForFirstConsumer` PVC binding 전에 소비자를 생성할 수 있습니다. Deployment는 rollout·readiness를 기다립니다. 1 replica와 `Recreate`는 RWO 볼륨의 롤링 다중 노드 연결을 가정하지 않으며 의도적으로 중단이 있습니다. PVC를 실제 마운트해도 파일 응답만으로 교체 후 영속성이나 백업 복원을 증명하지 못합니다. 독립 쓰기·재생성·읽기와 복원 근거가 필요합니다. 정리 전에 PV reclaim policy를 확인합니다. `_v1` 필드는 provider 문서로 확인했지만 Kubernetes provider apply나 실제 fixture 실행은 하지 않았습니다.

**검증 대시보드**

다음 ConfigMap은 `monitoring`에서 `grafana_dashboard=1` 레이블을 감시하는 기존 Grafana sidecar, `prometheus` datasource UID, 단일 클러스터 kube-prometheus-stack scrape 구성을 가정합니다. 실제 설치의 설정·job 레이블에 맞춥니다. 이를 위해 모니터링 스택을 중복 설치하지 않습니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-validation-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  cluster-validation.json: |
    {
      "uid": "eks-upgrade-validation",
      "title": "EKS Upgrade Validation",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Ready nodes",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum(max by (node) (kube_node_status_condition{job=\"kube-state-metrics\",condition=\"Ready\",status=\"true\"}))"
            }
          ]
        },
        {
          "id": 2,
          "title": "Ready active Pods (%)",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * sum(max by (namespace, pod, uid) (kube_pod_status_ready{job=\"kube-state-metrics\",condition=\"true\"}) and on (namespace, pod, uid) (max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}) == 1)) / sum(max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}))"
            }
          ]
        },
        {
          "id": 3,
          "title": "API requests / second",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "reqps"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (code) (rate(apiserver_request_total{job=\"apiserver\"}[5m]))"
            }
          ]
        },
        {
          "id": 4,
          "title": "Node CPU busy (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - avg by (instance) (max by (instance, cpu) (rate(node_cpu_seconds_total{job=\"node-exporter\",mode=\"idle\"}[5m]))))"
            }
          ]
        },
        {
          "id": 5,
          "title": "Node memory used (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 16
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - max by (instance) (node_memory_MemAvailable_bytes{job=\"node-exporter\"}) / max by (instance) (node_memory_MemTotal_bytes{job=\"node-exporter\"}))"
            }
          ]
        }
      ]
    }
```

“Ready active Pods”는 readiness를 사용하며 완료·실패 생명주기 단계를 제외합니다. `Running`만으로 Ready를 판단하지 않습니다. CPU는 idle counter의 rate를 사용하고 메모리는 별도 퍼센트 패널입니다. 명시한 단일 클러스터 범위에서 중복 exporter 샘플을 줄입니다. 다중 클러스터 소스라면 결합 전에 cluster 레이블로 필터·그룹화합니다. 메트릭 부재나 활성 Pod 분모 0은 unknown/no data로 유지하며 정상 0으로 대체하지 않습니다. 대시보드 자체가 업그레이드를 검증하거나 릴리스 gate를 강제하지 않습니다.

비공개 결과 디렉터리에 Update ID, smoke 근거, 환경·시각, 메트릭 쿼리·기간, 실패와 미검증 범위를 저장합니다. 운영 트래픽을 늘리기 전에 카나리 트래픽과 복구 기준을 관찰합니다. A, B는 유용한 부분 검사이지만 기능을 검증하지 못합니다. D는 그 전에 사용자를 노출합니다.

출처: [영구 볼륨](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Pod 생명주기](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [Terraform PVC](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume_claim_v1), [Prometheus 함수](https://prometheus.io/docs/prometheus/latest/querying/functions/).

</details>
