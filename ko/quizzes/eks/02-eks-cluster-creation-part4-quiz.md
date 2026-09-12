# EKS 클러스터 생성 퀴즈 - Part 4

> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 Terraform 클러스터 가이드와 확장·신원·수명주기 운영을 연결합니다. 마지막 절은 Terraform 자체 개념을 확인합니다. 예제에는 검토된 계정·리전·kubeconfig와 IAM·네트워크 선행조건이 필요하며 이번 감사에서 배포하지 않았습니다.

## 기본 개념 문제

1. Cluster Autoscaler와 Karpenter의 주요 프로비저닝 차이는 무엇인가요?
   * A) CA는 AWS 관리형 서비스
   * B) CA는 기존 그룹을 확장하고 Karpenter는 선택한 개별 용량을 프로비저닝
   * C) CA는 CPU만, Karpenter는 Pod 수만 측정
   * D) Karpenter가 Kubernetes 스케줄러를 대체

<details>
<summary>정답 보기</summary>

**정답: B) CA는 기존 그룹을 확장하고 Karpenter는 선택한 개별 용량을 프로비저닝**

Cluster Autoscaler는 검색된 기존 노드 그룹·ASG의 크기를 조절합니다. Karpenter는 NodePool·EC2NodeClass를 통해 NodeClaim과 EC2 용량을 생성합니다. Pod 스케줄링은 Kubernetes가 담당하며 Karpenter가 Kubernetes 스케줄러를 대체하지는 않습니다.

둘 다 스케줄할 수 없는 워크로드의 요청과 배치 제약을 고려합니다. 단순히 “CPU 비율 대 Pod 수”로 구분할 수 없고 실행 중인 EC2 인스턴스를 제자리에서 리사이즈하지도 않습니다. Karpenter는 다른 크기의 인스턴스로 교체할 수 있으며 VPA는 별도로 Pod 리소스 요청을 관리합니다.

**Cluster Autoscaler 예제:** EKS 1.36과 같은 마이너 버전, 검토된 IAM·검색 태그와 전용 ServiceAccount를 사용합니다. 차트 9.59.0은 v1.36.1 이미지 재정의가 필요합니다. 설치 전에 RBAC·이미지·인수를 렌더링해 확인하세요:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
검토된 워크로드·데이터 정책이 달리 요구하지 않는 한 로컬 스토리지·시스템 Pod 보호를 유지합니다. CA가 관리하는 한 그룹의 혼합 인스턴스는 CPU·메모리·GPU 크기를 맞춰야 합니다.

**Karpenter 예제:** 호환 컨트롤러·CRD를 설치하고 IAM, 노드 인증, 검색 태그, 중단 처리와 용량 제한을 별도로 구성합니다. 두 AMI 자리표시자는 클러스터 버전과 각 아키텍처에 맞는 검토된 AL2023 이미지로 바꾸세요. 두 아키텍처를 모두 허용한다면 워크로드 이미지도 둘 다 지원해야 합니다:

```yaml
# Karpenter NodePool (karpenter.sh/v1) + EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole-my-cluster
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_REVIEWED_AMD64_IMAGE
    - id: ami-REPLACE_WITH_REVIEWED_ARM64_IMAGE
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
| 비교 | Cluster Autoscaler | Karpenter |
| --- | --- | --- |
| 확장 단위 | 기존 노드 그룹·ASG 용량 | NodeClaim과 선택한 EC2 용량 |
| 구성 | 그룹·검색·IAM·컨트롤러 | NodePool·EC2NodeClass·IAM·컨트롤러 |
| 제거 | 스케줄링·중단 조건 확인 필요 | 통합·예산·중단 제어의 영향을 받음 |
| 기존 가이드의 과거 시간 주장 | 2–10분, 미검증 | 1분 이내, 미검증 |

기존 시간 수치는 **검증되지 않은 과거 주장**으로 보존했으며 이번 감사에서 재현한 벤치마크나 현재 성능 보장이 아닙니다. 노드 시작·이미지·쿼터·워크로드 제약이 두 도구 모두에 영향을 줍니다. 표에서 보편적인 비용·단순성·지연 순위를 추론하면 안 됩니다.

</details>

2. 현재 EKS CreateNodegroup API의 용량 유형은 무엇인가요?
   * A) Reserved, On-Demand, Spot
   * B) On-Demand, Spot, Dedicated
   * C) ON_DEMAND, SPOT, CAPACITY_BLOCK
   * D) Standard, Burstable, Compute-Optimized

<details>
<summary>정답 보기</summary>

**정답: C) ON_DEMAND, SPOT, CAPACITY_BLOCK**

현재 EKS CreateNodegroup API에는 **ON_DEMAND·SPOT·CAPACITY_BLOCK**이 있습니다. 관리형 노드 그룹 하나는 용량 유형 하나를 사용하며 용량 풀별로 그룹을 분리합니다.

On-Demand는 Spot 회수 대상이 아니지만 중단이나 가용성을 보장하지 않습니다. Spot은 여유 용량을 사용하므로 중단을 허용하는 워크로드가 필요하며 광고된 할인율이 절감액을 보장하지는 않습니다. Reserved Instances·Savings Plans는 결제 방식이며 CreateNodegroup enum을 추가하지 않습니다.

Capacity Blocks는 지원 인스턴스·리전의 시간 제한 예약을 위한 별도 절차입니다. 예약을 가리키는 커스텀 Launch Template, 일치하는 AZ·서브넷과 예약 시점을 고려한 확장이 필요합니다. EKS는 예약 종료 40분 전의 예약 축소 작업을 만들며 이를 수정·삭제하면 안 됩니다. 아래는 일반 On-Demand·Spot 대안이며 Capacity Block 프로비저닝 예제가 아닙니다.

**AWS CLI:** 미사용 노드 그룹 이름, 기존 프라이빗 서브넷과 승인된 EC2 노드 역할(CNI에 필요한 신원 경로 포함)을 사용합니다. 그룹 활성화를 기다린 뒤 실제 Node·워크로드 준비 상태를 확인하세요:

```bash
set -euo pipefail
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types t3.medium t3a.medium --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}"
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$NEW_NODEGROUP_NAME"
```
**eksctl 대안:** 기존 클러스터와 미사용 그룹 이름의 구성을 저장한 뒤 `eksctl create nodegroup -f nodegroups.yaml`을 사용합니다. 기존 예제의 미지원 `capacityType` 대신 `managedNodeGroups`와 `spot`을 사용하세요:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: ng-on-demand
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 5
  spot: false
- name: ng-spot
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large]
  privateNetworking: true
  desiredCapacity: 2
  minSize: 0
  maxSize: 5
  spot: true
```
어피니티·선택기·톨러레이션으로 적절한 워크로드를 배치합니다. 관리형 노드 그룹에는 Spot 재분배·드레인 처리가 내장되며 Node Termination Handler가 항상 추가로 필요한 것은 아닙니다. PDB는 EC2의 Spot 회수를 막지 못하고 모든 Pod가 전체 중단 알림 시간을 받는 것도 아닙니다. 체크포인트·여유 용량·중단 복구를 설계하세요.

</details>

3. 각 Fargate 프로필 선택기에서 필수인 필드는 무엇인가요?
   * A) 인스턴스 유형
   * B) 네임스페이스; 레이블은 선택 사항
   * C) 보안 그룹 ID
   * D) 최대 Pod 수

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스; 레이블은 선택 사항**

프로필의 각 선택기는 **네임스페이스**가 필수이며 레이블은 선택 사항입니다. 프로필 이름·Pod 실행 역할도 필요하고 적격한 프라이빗 서브넷을 사용합니다. 프로필에는 보안 그룹 파라미터가 없습니다. Pod 보안 그룹은 별도의 지원 정책 기능이며 Fargate 프로필 필드가 아닙니다.

미사용 프로필 이름과 검토된 프라이빗 서브넷 ID를 사용합니다. 이 선택기는 애플리케이션 Pod만 대상으로 하므로 기존 CoreDNS 배치를 변경하지 않습니다:

```bash
set -euo pipefail
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"fargate-lab","labels":{"app":"nginx"}}]'
aws eks describe-fargate-profile --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --fargate-profile-name "$NEW_FARGATE_PROFILE" \
  --query 'fargateProfile.{status:status,subnets:subnets,selectors:selectors}'
```
`ACTIVE` 상태를 확인한 뒤 일치하는 Pod를 시작합니다. 다음은 eksctl 프로필 정의 대안이며 생성 전에 클러스터의 프라이빗 서브넷 검색과 실행 역할 설정을 확인하세요:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: fp-application
  selectors:
  - namespace: fargate-lab
    labels:
      app: nginx
```
네임스페이스와 레이블이 있는 워크로드는 별도로 만들어야 합니다. 여러 프로필과 일치하면 `eks.amazonaws.com/fargate-profile`로 일치하는 프로필을 지정하지 않는 한 이름의 영숫자 순서를 사용합니다. 프로필은 변경 불가능하며 교체·삭제가 해당 Pod에 영향을 줍니다.

Pod 실행 역할은 Fargate 인프라용이며 애플리케이션의 AWS 접근 권한이 아닙니다. IRSA 등 호환 워크로드 신원을 사용하세요. EKS Pod Identity는 Fargate에서 지원되지 않습니다. CoreDNS를 Fargate로 옮기려면 `kube-system` 선택기 추가뿐 아니라 CoreDNS 컴퓨팅 설정과 일치하는 프로필도 필요합니다.

Fargate는 요청 리소스와 오버헤드·크기 조정을 반영한 **프로비저닝 용량**에 요금을 부과하며 관측된 CPU·메모리 사용량만 과금하지 않습니다. `CapacityProvisioned`를 확인하세요. EKS Fargate는 Spot·DaemonSet·특권 컨테이너·호스트 네트워킹·워크로드의 EBS 볼륨 마운트를 지원하지 않습니다. 영속 EFS는 정적 프로비저닝을 사용하며 프로필 매칭만으로 파일 시스템·PV·PVC가 생성되지는 않습니다. DNS·이미지 pull·STS 등 필요한 네트워크 경로도 검토하세요.

</details>

4. NodegroupUpdateConfig 필드가 아닌 것은 무엇인가요?
   * A) maxUnavailable
   * B) maxUnavailablePercentage
   * C) updateStrategy
   * D) 노드 그룹 작업 타임아웃

<details>
<summary>정답 보기</summary>

**정답: D) 노드 그룹 작업 타임아웃**

`NodegroupUpdateConfig`는 정수 `maxUnavailable`, 정수 `maxUnavailablePercentage`와 `updateStrategy`(`DEFAULT` 또는 `MINIMAL`)를 지원합니다. 개수와 비율 중 하나만 지정하세요. `maxUnavailable` 자체에 비율을 넣을 수는 없습니다.

작업 타임아웃은 NodegroupUpdateConfig 필드가 아닙니다. `--force`는 버전 업데이트 요청의 옵션으로 Pod 축출 보호를 우회할 수 있으며 저장되는 update-config 설정이 아닙니다. CLI·IaC 대기 타임아웃도 서비스 작업과 별개입니다.

```bash
set -euo pipefail
UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":2,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
비율 설정 대안은 `{"maxUnavailablePercentage":20,"updateStrategy":"DEFAULT"}`입니다. 반환된 업데이트 ID가 `Successful`이 된 뒤 버전 업데이트를 시작합니다. `DEFAULT`는 대체 용량을 먼저 시작하고 `MINIMAL`은 일시적인 추가 용량을 줄이기 위해 선택한 기존 노드를 먼저 종료합니다.

`update-lab`의 검토된 복제본 3개 Deployment에 다음 PDB를 적용하면 자발적인 축출을 제한합니다:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
PDB는 일반적인 가용성 보장이 아닙니다. 직접 삭제·장애·워크로드 컨트롤러 자체 롤아웃은 축출과 다릅니다. 여유 용량·준비 상태·볼륨을 확인하세요. 진행 중인 EKS 업데이트를 간단히 일시 중지·롤백할 수 있다고 약속하지 말고 후속 변경을 중단한 뒤 해당 복구 절차를 따릅니다.

</details>

5. 일반적인 EKS 버전 절차가 지원하는 제어 플레인 업그레이드 단계는 무엇인가요?
   * A) 마이너 두 개를 바로 건너뜀
   * B) 임의 업스트림 릴리스로 이동
   * C) 준비 상태 확인 후 EKS 지원 다음 마이너로 이동
   * D) 제어 플레인보다 높은 버전으로 노드를 먼저 업그레이드

<details>
<summary>정답 보기</summary>

**정답: C) 준비 상태 확인 후 EKS 지원 다음 마이너로 이동**

EKS 제어 플레인은 1.34 → 1.35 → 1.36처럼 **마이너 버전을 하나씩** 업그레이드합니다. 각 대상이 EKS에 제공되는지 확인하세요. 업스트림 Kubernetes 릴리스만으로 EKS 가용성을 판단할 수 없습니다. 현재 Kubernetes 1.x 절차에서 미래 메이저 버전 정책을 추정하면 안 됩니다.

제어 플레인 업그레이드 전에 EKS 절차가 요구하는 대로 관리형·Fargate 노드를 현재 제어 플레인 마이너에 맞추고 자체 관리·Hybrid 노드도 권장에 따라 갱신합니다. kubelet은 API 서버보다 최신 버전일 수 없습니다. Kubernetes 1.28 이상의 일반 스큐 상한은 kubelet이 최대 3개 마이너 뒤에 있는 것을 허용하지만 EKS 업그레이드 선행조건을 무시하라는 권장은 아닙니다.

먼저 인사이트·제거된 API·애드온 호환성·용량·애플리케이션 및 데이터 백업을 검토하세요. EKS 관리형 etcd에 일반 관리자 셸로 접속해 직접 스냅샷을 만드는 방식은 제공되지 않습니다. 지원되는 클러스터·리소스·영속 데이터 백업·복원 절차를 사용하세요. 다음 명령은 마이너 한 단계만 확인하며 위 검토를 대체하지 않습니다:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${NEXT_KUBERNETES_VERSION:?Confirm the next supported EKS minor}"
CURRENT_KUBERNETES_VERSION=$(aws eks describe-cluster \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --query cluster.version --output text)
if [[ "$CURRENT_KUBERNETES_VERSION" =~ ^1\.([0-9]+)$ ]]; then
  CURRENT_MINOR="${BASH_REMATCH[1]}"
else
  printf '%s\n' 'Unexpected cluster version; stop and inspect.' >&2
  exit 1
fi
EXPECTED_NEXT_VERSION="1.$((CURRENT_MINOR + 1))"
[ "$NEXT_KUBERNETES_VERSION" = "$EXPECTED_NEXT_VERSION" ] || {
  printf '%s\n' 'Only the next minor version is allowed in this upgrade example.' >&2
  exit 1
}
CLUSTER_UPDATE_ID=$(aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --kubernetes-version "$NEXT_KUBERNETES_VERSION" \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$CLUSTER_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
해당 업데이트 ID의 성공을 확인한 뒤 노드와 호환 클러스터 구성 요소를 문서화된 순서로 갱신합니다. Cluster Autoscaler 마이너를 클러스터와 맞추고 kubectl도 지원 스큐를 따릅니다.

현재 EKS는 in-place 업그레이드 완료 후 7일 이내에 조건부로 직전 마이너로 롤백할 수 있습니다. 처음부터 그 버전으로 만든 클러스터나 연장 지원 종료에 따른 자동 업그레이드는 대상이 아닙니다. 먼저 호환 노드·애드온을 준비하며 Auto Mode 노드 롤백은 EKS가 관리합니다. 롤백은 etcd·워크로드·영속 데이터를 이전 시점으로 되돌리지 않습니다. 무조건적인 실행 취소로 취급하지 말고 공식 롤백 준비 조건을 확인하세요.

</details>

## 단답형 문제

6. EKS 관리형 노드 그룹의 인스턴스 유형을 어떻게 변경할 수 있나요?

<details>
<summary>정답 및 설명</summary>

인스턴스 유형을 어디에 설정했는지에 따라 다릅니다:

* 관리형 노드 그룹의 `instanceTypes`는 `UpdateNodegroupConfig` 필드가 아닙니다. 교체 그룹을 만들고 용량을 검증한 뒤 워크로드를 이전하고 기존 그룹을 제거합니다.
* 그룹을 처음부터 **직접 만든 커스텀 Launch Template**으로 생성했고 EKS 그룹 필드가 아닌 템플릿에 유형을 지정했다면 **같은 템플릿의 새 버전**으로 갱신할 수 있습니다. EKS가 노드를 교체합니다. EKS 자동 생성 템플릿을 수정하거나 임의 템플릿 ID로 전환할 수 있다고 가정하면 안 됩니다.
* 자체 관리 ASG의 Launch Template 업데이트·instance refresh에도 Kubernetes를 고려한 드레인·수명주기 설계가 필요합니다. EC2 교체만으로 PDB를 고려한 마이그레이션이 되지는 않습니다.

AMI 아키텍처·드라이버·Pod IP 한도·레이블·테인트·스토리지 토폴로지·쿼터·PDB를 검토하세요. Terraform 소유 리소스는 담당 상태를 통해 변경하고 교체 계획을 확인합니다. 별도 CLI 변경 후 상태가 일치한다고 가정하면 안 됩니다.

</details>

7. Kubernetes API 엔드포인트에 프라이빗 접근만 허용하려면 어떻게 하나요?

<details>
<summary>정답 및 설명</summary>

프라이빗 접근을 true, 퍼블릭 접근을 false로 설정합니다. 모듈 v21에서는 `endpoint_private_access`·`endpoint_public_access`이며 Terraform 소유 클러스터라면 해당 상태를 통해 변경합니다.

퍼블릭 접근을 끄기 전에 관리자 연결 네트워크의 DNS·라우팅·보안 규칙으로 프라이빗 엔드포인트에 도달하는지 확인하세요. VPC **또는 적절히 연결된 다른 네트워크**에서 접근할 수 있으며 반드시 VPC 안에 있어야 하는 것은 아닙니다. Kubernetes API 엔드포인트 설정이며 별도의 AWS EKS 서비스 API 접근 설정은 아닙니다.

API로 관리하는 클러스터의 동등한 CLI 작업은 다음과 같습니다:

```bash
set -euo pipefail
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config \
  --region "${EXAMPLE_REGION:?}" --name "${EXAMPLE_CLUSTER:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
aws eks describe-update --region "$EXAMPLE_REGION" --name "$EXAMPLE_CLUSTER" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
해당 업데이트 ID가 `Successful`이 될 때까지 확인하고 의도한 관리 경로에서 인증된 kubectl 접근을 테스트합니다. `InProgress` 응답 한 번으로 완료를 판단하면 안 됩니다.

</details>

8. EKS Kubernetes 버전의 지원 수명주기는 어떻게 되나요?

<details>
<summary>정답 및 설명</summary>

EKS 마이너 버전은 **표준 지원 14개월** 후 추가 클러스터 시간당 요금이 있는 **연장 지원 12개월**을 받습니다. 기준은 업스트림이 아닌 EKS 출시일입니다.

2026년 9월 11일 기준 EKS는 1.34–1.36을 표준 지원, 1.31–1.33을 연장 지원으로 안내합니다. 배포·업그레이드 대상을 고르기 전에 현재 EKS 일정을 확인하세요. 업스트림 1.37 출시만으로 EKS 대상 버전이 되는 것은 아닙니다.

연장 지원은 기본 활성화되며 클러스터 업그레이드 정책이 표준 지원 종료 시 동작을 정합니다. 연장 지원이 끝나면 EKS가 제어 플레인을 지원 중인 가장 오래된 연장 버전으로 자동 업그레이드하므로 이전 버전이 갱신 없이 무기한 실행되지는 않습니다. 관리형·자체 관리·Hybrid 노드와 애드온은 별도 수명주기 작업이 필요하며 Auto Mode는 자체 기능과 노드를 관리합니다.

기존 퀴즈의 “항상 4개 버전”, “60일 전 공지”, “출시 지연 2–3개월”을 고정 규칙으로 사용하지 마세요. 실제 클러스터의 공개 일정과 정책을 확인합니다. 업스트림 Kubernetes의 지원 일정도 별도이며 기존의 9개월 비교는 현재 안내가 아닙니다.

</details>

## 실습 문제

9. CPU 75%·메모리 80% 사용률 목표의 Pod 오토스케일링과 초기 3개·최소 2개·최대 10개의 노드 그룹을 설계하세요.

<details>
<summary>정답 및 설명</summary>

**Pod 수요 확장**과 **노드 용량 확장**을 분리합니다. Metrics Server와 유효한 컨테이너 requests를 갖추고 HPA 리소스 사용률 목표를 CPU 75%·메모리 80%로 설정하세요. HPA는 메트릭별 복제본 권장값 중 큰 값을 선택하며 허용 오차·상한·안정화의 영향을 받습니다. 즉각적인 “임계값 초과” 경보와 같지는 않습니다.

이후 최소 2·최대 10·초기 원하는 수 3인 관리형 노드 그룹에 Cluster Autoscaler를 사용합니다. Terraform 모듈의 대응 필드는 `min_size`·`max_size`·`desired_size`이며 담당 구성을 검토하세요. 아래는 검토한 기존 클러스터에 새 그룹을 만드는 완전한 eksctl 대안입니다:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: autoscaling-workers
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  minSize: 2
  maxSize: 10
  desiredCapacity: 3
```
문제 1의 전용 권한을 구성한 Cluster Autoscaler를 사용합니다. 상한·하한만으로 오토스케일러가 실행되지는 않습니다. CA는 스케줄할 수 없는 Pod 요청과 제거 제약에 반응하며 CPU·메모리 비율 목표를 직접 구현하지 않습니다.

새 `autoscaling-lab` 네임스페이스에서 아래 Deployment·HPA로 requests와 두 메트릭을 구성합니다. Pod 복제본 범위 2–20과 노드 범위 2–10은 별개입니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: autoscaling-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: my-app}
  template:
    metadata:
      labels: {app: my-app}
    spec:
      automountServiceAccountToken: false
      containers:
      - name: web
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```
승인된 부하 테스트에서 HPA 조건·메트릭 가용성·Pending 원인·오토스케일러 판단을 확인하세요. 복제본이 늘어도 메모리가 비례해서 줄지 않을 수 있으므로 애플리케이션에 적절한 메트릭인지 검증해야 합니다. requests·limits 값은 실측 사이징이 아닌 예제입니다.

같은 desired capacity에 독립적인 ASG CPU·메모리 대상 추적 정책을 추가하면 CA와 경쟁하고 드레인 동작도 달라질 수 있습니다. EC2는 일반적인 메모리 사용률을 기본 제공하지 않습니다. CA를 쓰지 않는 별도 설계에는 올바르게 게시한 사용자 지정 메트릭·네임스페이스가 필요하며 `AWS/EC2` 메모리 메트릭을 가정하면 안 됩니다. 이 HPA+CA 해법에는 그러한 ASG 정책이 필요하지 않습니다.

</details>

## 고급 문제

10. 노드 그룹의 blue/green 업그레이드와 위험·보호 절차를 설명하세요.

<details>
<summary>정답 및 설명</summary>

교체 용량을 만든 후 테스트·점진적 이전을 수행하고 애플리케이션·데이터 검증이 끝난 뒤 기존 그룹을 제거합니다. 롤백이 필요할 동안 기존 용량과 호환 상태를 유지하세요. 같은 클러스터의 두 그룹은 완전한 격리나 무중단 보장이 아닙니다.

쿼터·서브넷 IP·이미지·아키텍처·레이블·테인트·데몬 부담·PDB·로컬 데이터·볼륨 AZ 및 연결 제약을 검토합니다. StatefulSet만으로 볼륨 이동성이 생기지는 않습니다. TTL을 바꾸거나 서비스 메시를 추가하기 전에 DNS 실패 원인을 조사하세요. 모니터링·로그 수집기가 새 노드를 실제로 포함하는지도 확인합니다.

다음 CLI 예제는 **API 소유 그룹**과 미사용 green 그룹 이름을 사용합니다. Terraform 또는 eksctl·CloudFormation 소유 그룹은 상태 불일치나 남은 스택을 피하도록 해당 소유자를 통해 동등한 변경을 수행하세요.

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${OLD_NODEGROUP_NAME:?}" "${GREEN_NODEGROUP_NAME:?}"
[ "$OLD_NODEGROUP_NAME" != "$GREEN_NODEGROUP_NAME" ]
OLD_NODEGROUP_ARN=$(aws eks describe-nodegroup --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$OLD_NODEGROUP_NAME" \
  --query nodegroup.nodegroupArn --output text)
aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME" --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --instance-types t3.large \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}" \
  --labels audit.example.com/pool=green
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME"
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l "eks.amazonaws.com/nodegroup=$GREEN_NODEGROUP_NAME" -o wide
```
노드 그룹 태그만으로 기반 ASG에 Cluster Autoscaler 검색 태그가 있다고 판단할 수는 없습니다. CA를 사용한다면 실제 ASG 태그·IAM을 확인하세요. 주 워크로드 이전 전에 새 Node 준비 상태와 별도 범위의 카나리아 워크로드를 검증합니다.

확인된 기존 노드를 하나씩 드레인합니다. 아래는 emptyDir 자동 삭제나 강제 축출을 포함하지 않습니다:

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
단계마다 준비 상태·애플리케이션 상태·영속 데이터를 확인합니다. 드레인 실패 시 중단하고 원인을 해결하세요. 모든 워크로드 검증을 마치고 기존 그룹을 더 보존할 필요가 없을 때, 별도의 최종 삭제 전에 원래 ARN과 비교합니다:

```bash
# A separate final step for API-owned groups only.
: "${OLD_NODEGROUP_ARN:?Use the ARN captured before migration}"
if [ "${MIGRATION_VERIFIED:?Set yes only after application/data checks}" = yes ]; then
  CURRENT_OLD_GROUP_ARN=$(aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --nodegroup-name "${OLD_NODEGROUP_NAME:?}" \
    --query nodegroup.nodegroupArn --output text) || exit 1
  [ "$CURRENT_OLD_GROUP_ARN" = "$OLD_NODEGROUP_ARN" ] || {
    printf '%s\n' 'Node-group identity changed; no deletion attempted.' >&2
    exit 1
  }
  aws eks delete-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME" || exit 1
  aws eks wait nodegroup-deleted --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME"
fi
```

</details>


## Terraform 확인 문제

11. terraform_remote_state 읽기 주체가 접근할 수 있는 것은 무엇인가요?
   * A) 저장 계층에서도 선언된 출력만
   * B) HCL에는 출력만 제공되어도 전체 상태 스냅샷
   * C) 어떤 경우에도 민감한 값에는 접근 불가
   * D) 자기 모듈 리소스만

<details>
<summary>정답 보기</summary>

**정답: B) HCL에는 출력만 제공되어도 전체 상태 스냅샷**

상태 접근은 권한 경계입니다. 소비자에게 전체 스냅샷을 공개하면 안 된다면 필요한 값만 별도 게시하세요.

</details>

12. EKS 모듈 v21 예제에 맞는 입력 이름은 무엇인가요?
   * A) cluster_name과 cluster_version
   * B) name과 kubernetes_version
   * C) clusterId와 versionNumber
   * D) cluster_addons와 cluster_compute_config

<details>
<summary>정답 보기</summary>

**정답: B) name과 kubernetes_version**

모듈 v21에서 입력 이름이 바뀌었습니다. aws_eks_addon.cluster_name 같은 AWS 리소스 필드와 cluster_name 같은 모듈 출력은 각자의 이름을 유지하므로 모든 문자열을 일괄 변경하면 안 됩니다.

</details>

13. S3 백엔드 예제의 올바른 설명은 무엇인가요?
   * A) encrypt=true가 잠금도 활성화
   * B) DynamoDB만 잠금 가능
   * C) use_lockfile=true로 S3 잠금 활성화; 클라이언트·잠금 파일 IAM 준비 필요
   * D) 하나의 잠금이 모든 상태 키 조율

<details>
<summary>정답 보기</summary>

**정답: C) use_lockfile=true로 S3 잠금 활성화; 클라이언트·잠금 파일 IAM 준비 필요**

S3 잠금 파일에는 Terraform 1.10 이상을 사용합니다. DynamoDB 잠금은 폐기 예정이므로 기존 클라이언트가 사용하는 테이블을 바로 삭제하지 말고 조율해 전환하세요.

</details>

14. aws_eks_pod_identity_association이 Kubernetes ServiceAccount를 생성하나요?
   * A) 예, cluster-admin으로 생성
   * B) 아니요; 네임스페이스·ServiceAccount와 지원 에이전트·SDK 경로는 별도 선행조건
   * C) 예, Metrics Server도 설치
   * D) Fargate에서만 생성

<details>
<summary>정답 보기</summary>

**정답: B) 아니요; 네임스페이스·ServiceAccount와 지원 에이전트·SDK 경로는 별도 선행조건**

연결은 AWS 신원을 기존 Kubernetes 신원에 매핑합니다. 신뢰·권한을 제한하고 필요한 세션 태그를 유지하며 전파를 고려해 실제 assumed role을 확인하세요.

</details>

15. 모듈 버전 제약 ~> 21.0은 무엇을 허용하나요?
   * A) 21.0.0만
   * B) 21.0.x 패치만
   * C) 동작 보장 없이 22.0 미만의 21.x 마이너·패치 범위
   * D) 모든 미래 메이저 버전

<details>
<summary>정답 보기</summary>

**정답: C) 동작 보장 없이 22.0 미만의 21.x 마이너·패치 범위**

~> 21.0.0은 21.0.x로 제한합니다. 가이드는 모듈 버전을 명시적으로 고정하며 .terraform.lock.hcl은 원격 모듈이 아닌 프로바이더 선택을 기록합니다. 저장한 계획을 검토한 후 적용하세요.

</details>

## 참고 자료

- [API_CreateNodegroup.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)
- [ml-node-groups.html](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-groups.html)
- [fargate-profile.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)
- [fargate-pod-configuration.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-pod-configuration.html)
- [API_NodegroupUpdateConfig.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_NodegroupUpdateConfig.html)
- [launch-templates.html](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)
- [kubernetes-versions.html](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [update-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [rollback-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [cas.html](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [horizontal-pod-autoscale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [s3](https://developer.hashicorp.com/terraform/language/backend/s3)
- [remote-state-data](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
