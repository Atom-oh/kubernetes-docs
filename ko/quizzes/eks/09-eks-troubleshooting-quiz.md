# Amazon EKS 문제 해결 퀴즈

> **마지막 업데이트**: 2026년 9월 12일

이 퀴즈는 Amazon EKS 클러스터에서 발생할 수 있는 다양한 문제를 진단하고 해결하는 능력을 테스트합니다.

## 퀴즈 개요

- 클러스터 생성 및 구성 문제
- 네트워킹 문제
- 노드 및 파드 문제
- 스토리지 문제
- 보안 및 액세스 문제
- 성능 및 확장성 문제

## 객관식 문제

### 1. EKS 컨트롤 플레인 생성 실패 직후 가장 유용한 대응은 무엇인가요?

- A. 클러스터 이름 중복만 확인
- B. 정확한 오류·요청을 확인하고 호출자·서비스 역할 IAM, VPC·서브넷과 관련 quota 검토
- C. 즉시 다른 리전에 새 클러스터 생성
- D. 더 큰 worker instance type 선택

<details>
<summary>정답 보기</summary>

**정답: B. 정확한 오류·요청을 확인하고 호출자·서비스 역할 IAM, VPC·서브넷과 관련 quota 검토**

실패한 요청이나 CloudFormation event부터 확인합니다. IAM·network·quota·name conflict는 유용한 가설이며 오류를 읽기 전 통계적 진단이 아닙니다.

**확인 항목**

| 영역 | 근거 |
| --- | --- |
| 호출자 | account·region·profile, 필요한 EKS 동작·iam:PassRole, boundary·session·SCP, 필요 시 service-linked-role 권한 |
| Cluster service role | 정확한 ARN, EKS trust·필수 policy. caller·worker role과 구분 |
| Cluster subnet | 지원 AZ, 최소 2개 AZ와 여유 주소. node·Pod·LB는 별도 용량 예산 |
| Endpoint·의존성 | 의도한 private·public mode, DNS·route·SG·NACL과 필요한 AWS 서비스 접근 |
| Quota | 실제 service·quota·현재 region/account 한도. node 생성이 포함되면 EC2 vCPU도 확인 |
| 인프라 소유자 | 원래 Terraform·CloudFormation·eksctl config, state와 실패 작업 |

현재 EKS는 선택한 cluster subnet마다 **최소 6개 IP 주소**, **16개 이상 권장**, 최소 2개 AZ를 요구합니다. CIDR 크기만으로 해당 주소가 남아 있는지 알 수 없습니다. 기존의 일반적인 “최소 /28, 권장 /24”는 control-plane·workload sizing을 혼동합니다. private 환경은 필요한 endpoint를 사용할 수 있으므로 NAT·일반 인터넷이 보편적으로 필수는 아닙니다.

AmazonEKSClusterPolicy는 cluster service role용이며 사용자에게 붙여도 creation·PassRole·Kubernetes RBAC 전체가 부여되지 않습니다. cluster ownership subnet tag도 보편적 생성 해결책이 아닙니다.

**읽기 전용 조사**

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"; : "${CLUSTER_NAME:?}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch" >&2; exit 1
fi
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateCluster \
  --max-items 20 --output json
aws service-quotas list-service-quotas --service-code eks --region "$AWS_REGION"
: "${VPC_ID:?Set the VPC from the original request}"
aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,AZId:AvailabilityZoneId,AvailableIPs:AvailableIpAddressCount}'
# For an eksctl-owned creation attempt, inspect its existing stacks:
eksctl utils describe-stacks --cluster "$CLUSTER_NAME" --region "$AWS_REGION"
```

사용할 cluster가 이미 있으면 describe-cluster로 확인합니다. 없으면 ResourceNotFound를 두 번째 근본 원인으로 취급하지 말고 원래 생성 오류를 보존합니다. 다른 CloudFormation 소유자는 정확한 stack event를 확인합니다. eksctl create cluster --verbose와 CLI debug mode도 실제 provisioning이며 읽기 전용 진단이 아닙니다.

**예시 메시지**

- eks:CreateCluster 거부는 caller 권한을 조사하며 service-role 문제와 별도입니다.
- 기존 us-west-2a capacity 부족 메시지는 AZ·capacity 응답 예시이지 현재 리전 가용성 정보가 아닙니다.
- 기존 “Current limit is 5”는 역사적 예시로 보존합니다. 증가 값을 정하기 전 현재 quota를 조회합니다.
- UnsupportedAvailabilityZoneException은 해당 계정의 미지원 EKS cluster AZ이며 EC2 instance 제공 목록만의 문제가 아닙니다.

**인프라 설정 검토**

원래 owner config를 확인·수정합니다. 다음 Terraform은 version·network 의도와 status output 발췌이며 완전한 새 cluster module이나 진단 중 apply할 명령이 아닙니다.

```hcl
# Excerpt of the original state-owned configuration, not a diagnostic apply.
# Preserve its other settings and role/policy dependencies.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.cluster_version
  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = var.cluster_security_group_ids
    endpoint_private_access = true
    endpoint_public_access  = false
  }
}

output "cluster_status" {
  value = aws_eks_cluster.main.status
}
```

검증한 기존 role·subnet·SG, 필요한 role-policy dependency와 다른 설정을 유지하고 private endpoint 접근을 검토합니다. output은 Terraform state에서 평가하므로 생성 실패 시 출력되거나 최신 실패 정보가 포함된다는 보장이 없습니다. provider 진단과 AWS request·stack 근거를 사용합니다. 이번 검토에서 Terraform apply·cluster 생성을 실행하지 않았습니다.

원인을 찾은 뒤 표적 permission·network·quota 변경과 owner를 통한 재시도를 검토합니다. A는 유용하지만 좁은 검사입니다. C는 원인을 고치지 못한 채 placement·data·network·비용을 바꿀 수 있고 D는 worker 변경이며 control-plane 생성 문제를 해결하지 않습니다.

출처: [EKS 네트워크 요구](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html), [EKS 문제 해결](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html), [Terraform EKS cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 2. EKS node가 NotReady일 때 가장 효과적인 첫 조사는 무엇인가요?

- A. 즉시 node 종료
- B. node condition·event, log·resource와 실제 network·identity 경로 확인
- C. 관리형 EKS API server를 직접 재시작
- D. cluster의 모든 Pod 삭제

<details>
<summary>정답 보기</summary>

**정답: B. node condition·event, log·resource와 실제 network·identity 경로 확인**

condition reason·시각과 실제 node identity로 조사합니다. Ready=False, heartbeat 부재·Ready=Unknown, disk·memory pressure는 서로 다른 근거이며 그 자체가 원인을 확정하지 않습니다.

**Node·workload 인벤토리**

다음 읽기 전용 예시는 name·UID와 spec.nodeName으로 정확한 node·Pod를 선택하며 IP·grep 매칭을 사용하지 않습니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,labels:.metadata.labels,providerID:.spec.providerID,taints:.spec.taints,unschedulable:.spec.unschedulable,nodeInfo:.status.nodeInfo,conditions:.status.conditions,capacity:.status.capacity,allocatable:.status.allocatable}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A --field-selector "involvedObject.uid=$NODE_UID" \
  --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" get pods -A --field-selector "spec.nodeName=$NODE_NAME" -o wide
```

EC2·host 접근 전에 ProviderID, account·region과 compute type을 확인합니다. 관리형 그룹은 health·repair·update 설정을 조회합니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,release:releaseVersion,nodeRole:nodeRole,repair:nodeRepairConfig,update:updateConfig}'
```

접근 가능한 표준 Linux node는 [본문의 원격 세션 절차](../../eks/09-eks-troubleshooting.md)로 kubelet·containerd journal, byte·inode, memory·route를 확인합니다. 실제 이미지에 Docker daemon·/var/log/syslog가 없을 수 있습니다. node DNS는 Pod cluster DNS와 다를 수 있으며 endpoint TLS에는 cluster CA를 사용합니다. curl -k는 certificate 오류를 숨깁니다.

image·journal 정리·reboot 전에 근거를 보존합니다. kubectl top은 정상 metrics 경로가 필요하여 비정상 node에서는 실패할 수 있습니다. private key를 노출하지 않고 실제 certificate 경로를 확인합니다. kubeadm alpha certs renew all은 현재 일반 명령도 EKS node 복구 절차도 아니며 eksctl replace nodegroup도 지원되지 않습니다.

**복구와 자동 repair 구분**

원인을 확인한 뒤 capacity·PDB·data·node owner와 restart·replacement를 조율합니다. 제한된 drain이 실패하면 중단하며 termination이나 비동기 reboot 직후 uncordon으로 진행하지 않습니다.

자동 node repair는 실제 EKS 기능입니다. update_config.max_unavailable은 version update 중단 범위이며 repair 활성화가 아닙니다. health_check { type = "EKS" }는 aws_eks_node_group 블록이 아니고 현재 provider는 node_repair_config를 제공합니다.

```hcl
# Fragment of a reviewed EKS-optimized-AMI managed node group.
resource "aws_eks_node_group" "self_healing" {
  cluster_name    = var.cluster_name
  node_group_name = var.node_group_name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.node_kubernetes_version
  ami_type        = var.ami_type
  release_version = var.ami_release
  instance_types  = var.instance_types

  scaling_config {
    desired_size = 3
    min_size     = 3
    max_size     = 6
  }
  update_config {
    max_unavailable = 1
  }
  node_repair_config {
    enabled                           = true
    max_parallel_nodes_repaired_count = 1
  }
}
```

검증된 production module이 아닌 설정 발췌입니다. 호환 Kubernetes·AMI·instance와 기존 소유권을 확인하고 autoscaler가 관리한다면 desired capacity를 조율합니다. node-group tag만으로 실제 ASG의 CA discovery tag가 있다고 판단하지 않습니다.

repair 기본값·threshold는 compute owner에 따라 다릅니다. Auto Mode는 기본 활성화, MNG는 명시적 활성화, Karpenter는 자체 feature 요구가 있습니다. monitoring은 repair 활성화 없이도 문제를 보고할 수 있습니다. 현재 기본 표는 **MemoryPressure·DiskPressure를 자동 repair하지 않습니다**. fleet health·parallelism·ARC 제어가 작업을 제한할 수 있으며 무조건 교체·PDB 보호를 약속하지 않습니다.

**모니터링 예시**

AWS/EKS namespace의 NodeNotReady라는 내장 metric이 있다고 가정할 수 없습니다. 기존 kube-state-metrics·Prometheus Operator에서는 실제 node condition을 평가할 수 있습니다.

```yaml
# Existing single-cluster Prometheus Operator/KSM installation required.
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-readiness-example
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
    - name: node-readiness-example
      rules:
        - alert: NodeNotReady
          expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="Ready",status="true"}) == 0
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Node {{ $labels.node }} is not Ready"
            description: "Investigate node conditions, reachability and workload impact before recovery."
```

namespace·release·job selector를 실제 설치에 맞춥니다. 10분은 예시입니다. scrape·condition data 부재는 별도 telemetry-health monitoring이 필요하며 정상 node로 취급하지 않습니다. 이 rule은 notification 연결·recovery를 수행하지 않으므로 따로 검증합니다. 정의되지 않은 node-recovery.zip Lambda 생성만으로 안전한 자동 복구가 생기지 않습니다.

C는 사용자가 관리형 EKS API server를 재시작하는 경로가 아니며 API 연결은 실제로 readiness 문제의 원인이 될 수 있습니다. A·D는 원인을 해결하지 못한 채 중단을 넓히고 근거를 없앨 수 있습니다.

출처: [EKS node repair](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html), [Terraform node resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group), [node metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md).

</details>

### 3. EKS의 ImagePullBackOff를 적절히 조사하는 방법은 무엇인가요?

- A. 모든 container memory limit 증가
- B. 실제 pull 오류, image·platform과 pull identity·network 경로 확인
- C. 오류 확인 없이 새 이미지 download 강제
- D. 모든 NetworkPolicy 삭제

<details>
<summary>정답 보기</summary>

**정답: B. 실제 pull 오류, image·platform과 pull identity·network 경로 확인**

ImagePullBackOff는 재시도·backoff 상태이며 하나의 “가장 가능성 높은” 원인을 증명하지 않습니다. 영향받는 일반·init container와 정확한 kubelet event를 확인합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
  node:.spec.nodeName,serviceAccount:.spec.serviceAccountName,
  imagePullSecrets:.spec.imagePullSecrets,
  containers:[.spec.containers[] | {name,image,imagePullPolicy,resources}],
  initContainers:[.spec.initContainers[]? | {name,image,resources}],
  phase:.status.phase,reason:.status.reason,message:.status.message,
  conditions:.status.conditions,containerStatuses:.status.containerStatuses,
  initContainerStatuses:.status.initContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
```

repository·tag·digest 부재, architecture 불일치, credential·authorization, rate limit, node DNS·TLS·egress, local disk·runtime 실패를 구분합니다. 로컬 Docker pull은 identity·path가 다르므로 node pull 성공을 증명하지 못합니다.

**ECR identity와 network**

EC2 node는 일반적으로 node pull-credential 경로, Fargate는 Pod execution role을 사용합니다. 앱 IRSA·Pod Identity는 앱 시작 전 이미지를 내려받는 주체가 아닙니다. repository policy·cross-account를 확인합니다. role을 새로 만들기만 하고 compute에 연결하지 않으면 image pull이 바뀌지 않습니다.

임의 image 문자열을 cut으로 나누지 말고 repository·account·region과 tag **또는** digest를 명시합니다.

```bash
set -euo pipefail
: "${REGISTRY_REGION:?Set the image registry Region}"
: "${REGISTRY_ACCOUNT_ID:?Set its account ID}"
: "${REPOSITORY_NAME:?Set the exact repository path}"
: "${ECR_IMAGE_ID:?Set imageTag=... or imageDigest=sha256:...}"
aws ecr describe-images --region "$REGISTRY_REGION" \
  --registry-id "$REGISTRY_ACCOUNT_ID" --repository-name "$REPOSITORY_NAME" \
  --image-ids "$ECR_IMAGE_ID" \
  --query 'imageDetails[].{digest:imageDigest,tags:imageTags,pushedAt:imagePushedAt,mediaType:imageManifestMediaType}'
```

운영자의 AWS credentials로 image metadata를 확인할 뿐 kubelet 권한 검증은 아닙니다. private ECR에는 API·DKR·S3 경로, endpoint policy·SG·DNS가 필요할 수 있습니다. ecr.dkr은 임의 private registry용 endpoint가 아닙니다. 일반 Pod NetworkPolicy 변경으로 node runtime의 registry 인증이 고쳐지는 것은 아닙니다.

**권한 예시**

검토한 기존 EC2 node role에 한 repository pull을 설명하는 예시입니다. GetAuthorizationToken은 repository resource scope가 없어 Region 조건의 별도 `*` statement를 사용하고 image read는 repository로 제한합니다.

```hcl
# Permission example for a reviewed existing EC2 node role.
# This does not create/associate a new role or create an image-pull Secret.
data "aws_iam_role" "node" {
  name = var.existing_node_role_name
}

resource "aws_iam_policy" "ecr_pull" {
  name = var.pull_policy_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:RequestedRegion" = var.registry_region }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = var.repository_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = data.aws_iam_role.node.name
  policy_arn = aws_iam_policy.ecr_pull.arn
}
```

실제 repository ARN·region, 기존 grant·boundary·SCP와 cross-account repository policy를 확인합니다. 좁은 policy 추가가 기존의 넓은 policy를 제거하지 않습니다. Fargate는 자체 execution-role 구성이 필요합니다. 이 EC2 role 예시는 Kubernetes Secret·Fargate profile을 만들지 않으며 이번 검토에서 IAM 변경도 실행하지 않았습니다.

**Image-pull Secret**

Secret이 필요한 registry는 보호된 완전한 Docker auth file과 [본문의 namespaced Secret·Pod-template 절차](../../eks/09-eks-troubleshooting.md)를 사용합니다. Secret data·token을 출력하거나 진단 명령 인자로 password를 전달하지 않습니다. desktop credential-helper 참조만으로 kubelet auth data가 제공되지는 않습니다.

기존 Pod의 imagePullSecrets는 일반적으로 직접 patch할 수 없습니다. 기존 목록을 유지하며 소유 Deployment·StatefulSet template을 바꾸고 통제된 rollout을 수행합니다. ServiceAccount 변경은 새 Pod에 적용되므로 무관한 앱의 default SA를 바꾸지 않습니다.

**Credential 갱신 설계**

표준 EKS ECR pull에는 기존 token-renewal CronJob이 필요하지 않습니다. ECR authorization token은 12시간 유효합니다. non-native consumer가 실제로 수동 ECR pull Secret을 필요로 한다면 지원 credential 방식이나 명시적으로 설계한 갱신 workflow를 사용합니다.

기존 `*/6 * * * *`는 6시간이 아닌 **6분마다**입니다. 6시간 예시는 `0 */6 * * *`이며 controller timezone 또는 지원되는 명시적 spec.timeZone을 고려합니다. schedule만으로 renewer가 완성되지는 않습니다. 필요한 도구가 있는 검토한 image, AWS identity, 제한한 Kubernetes 권한, 정확한 namespace, 중복·실패 처리와 rotation 검증이 필요합니다. 검증 전에는 suspend를 유지합니다. 미리 준비한 named Secret을 갱신하고 삭제·재생성으로 credential 공백을 만들지 않습니다. AWS CLI 기본 이미지에 kubectl이 있다고 가정하지 않습니다.

의도한 digest를 고정하고 registry 가용성을 유지하며 pull policy 변경 전에 실제 오류를 조사합니다. Always는 없는 이미지·권한 부족을 고치지 못합니다. A·C·D는 실패 경로를 식별하지 않습니다.

출처: [Fargate execution role](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html), [ECR token 명령](https://docs.aws.amazon.com/cli/latest/reference/ecr/get-authorization-token.html), [private registry Secret](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/).

</details>

### 4. Service가 Pod에 접근하지 못할 때 가장 유용한 첫 조사는 무엇인가요?

- A. 즉시 Service 재생성
- B. selector·type, Pod readiness, EndpointSlice·port와 실제 허용 경로 확인
- C. 모든 Pod 재시작
- D. 관리형 API server 직접 재시작

<details>
<summary>정답 보기</summary>

**정답: B. selector·type, Pod readiness, EndpointSlice·port와 실제 허용 경로 확인**

리소스를 바꾸기 전에 discovery·routing 경로를 추적합니다. 실제 namespace·source client에서 Service와 앱 listener·readiness를 비교합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
SERVICE_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json)
printf '%s\n' "$SERVICE_JSON" | jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace}, spec: .spec, status: .status}'
SELECTOR=$(printf '%s\n' "$SERVICE_JSON" | jq -r '(.spec.selector // {}) | to_entries | map("\(.key)=\(.value)") | join(",")')
if [ -n "$SELECTOR" ]; then
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o json \
    | jq '.items[] | {name:.metadata.name,phase:.status.phase,ready:[.status.conditions[]? | select(.type=="Ready")],containers:.status.containerStatuses}'
else
  printf 'No selector: inspect ExternalName or explicitly managed EndpointSlices as applicable.\n'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
```

helper는 selector 없는 Service에서 전체 Pod를 잘못 선택하지 않습니다. ExternalName은 alias, headless의 clusterIP None은 의도된 값이며 수동 EndpointSlice도 유효한 경우입니다. endpoint Ready·serving·terminating과 traffic policy를 확인합니다. sidecar 하나가 ready이거나 Running이어도 Pod Ready와 같지는 않습니다.

**관찰한 문제 수정**

- Selector 불일치: 교체될 Pod 하나가 아니라 소유 Service·Pod template을 수정합니다.
- Port 불일치: Service port·named targetPort·실제 listener를 맞춥니다. containerPort 선언은 listener를 만들지 않습니다.
- Policy 제한: source egress·destination ingress, label과 구현 범위를 확인합니다. policy 삭제·모든 namespace 모든 port 허용으로 해결하지 않습니다.
- DNS·data plane: 이름 해석과 전송을 구분하고 kube-proxy·대안 구현·Auto Mode를 식별합니다. 순수 Auto는 node DNS, 혼합은 비 Auto node용 DNS를 유지합니다.

아래 **독립 policy 예시**는 검토한 peer·port만 허용합니다. 실제 사용 전에 label·namespace와 전체 필요한 흐름에 맞춥니다.

```yaml
# Example ingress policy only: review both peers and the complete allowed-flow matrix.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-web
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
```

다른 policy가 허용하지 않는 backend ingress를 격리할 수 있으며 client egress를 만들지 않습니다. 허용·거부 테스트가 모두 필요합니다.

**Terraform Service·Deployment fixture**

원래 Service·Pod 예시를 실제 listener·일치 label·readiness·제한된 resources가 있는 임시 Linux fixture로 유지합니다. 검토한 test context에 provider를 구성하고 새 namespace를 선택하며 기존 앱 namespace를 import하지 않습니다.

```hcl
# Disposable example; configure the Kubernetes provider/context externally.
variable "test_namespace" {
  type = string
  validation {
    condition     = can(regex("^docs-service-check-[a-z0-9]{8,16}$", var.test_namespace))
    error_message = "Supply a new unique namespace with the test prefix."
  }
}
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.test_namespace
  }
}
resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = "app-deployment"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    replicas = 2
    selector {
      match_labels = { app = "service-demo" }
    }
    template {
      metadata {
        labels = { app = "service-demo" }
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
          name    = "app"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args    = ["mkdir -p /tmp/www; printf 'ok\\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www"]
          port {
            name           = "http"
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "http"
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
            name       = "tmp"
            mount_path = "/tmp"
          }
        }
        volume {
          name = "tmp"
          empty_dir {}
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "app" {
  metadata {
    name      = "app-service"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    selector = { app = "service-demo" }
    type     = "ClusterIP"
    port {
      name        = "http"
      port        = 80
      target_port = "http"
    }
  }
}
```

운영 앱이나 측정 기반 resource 권고가 아닙니다. 앱 API·RBAC가 필요하지 않습니다. provider field를 검토했지만 실제 Terraform apply·image 실행을 주장하지 않습니다.

**제한된 연결 Job**

Service·Pod가 Ready인 뒤 아래 Job을 저장하고 namespace를 준비한 값으로 바꿉니다. probe에는 kubectl binary·Kubernetes API token이 필요하지 않습니다.

```yaml
# Use kubectl create; replace namespace with the prepared fixture namespace.
apiVersion: batch/v1
kind: Job
metadata:
  generateName: service-probe-
  namespace: docs-service-check-12345678
spec:
  activeDeadlineSeconds: 60
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: probe
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - nslookup app-service; wget -T 5 -q -O- http://app-service:80
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
```

공통 이름을 재사용하지 말고 새 이름이 생성되는 Job을 만듭니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TEST_NAMESPACE:?}"; : "${SERVICE_PROBE_FILE:?}"
JOB_NAME=$(kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" create \
  -f "$SERVICE_PROBE_FILE" -o jsonpath='{.metadata.name}')
: "${JOB_NAME:?Job creation did not return a name}"
printf 'Created probe: %s/%s\n' "$TEST_NAMESPACE" "$JOB_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" wait \
  --for=condition=complete "job/$JOB_NAME" --timeout=90s
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" logs "job/$JOB_NAME"
```

wait 실패 시 생성한 Job과 Pod·event·log를 보존·조사하고 무조건 성공을 출력하거나 기존 namespace를 삭제하지 않습니다. UID를 기록하고 근거 검토 뒤 소유 test resource만 정리합니다. 이 검사는 DNS·HTTP 1회이며 모든 client identity·direct Pod path·LB·SLO를 검증하지 않습니다. 필요하면 같은 허용 source에서 Pod·Service 접근을 따로 비교합니다.

A·C는 진단 전에 근거를 잃거나 중단을 추가합니다. D는 사용자가 운영하는 EKS control-plane 동작이 아니며 근거가 가리킬 때 API·controller 상태를 조사합니다.

출처: [Service](https://kubernetes.io/docs/concepts/services-networking/service/), [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 5. PVC가 Pending일 때 먼저 조사할 사항은 무엇인가요?

- A. 항상 더 큰 node 추가
- B. claim·class·binding mode·consumer scheduling·driver·provisioning identity 확인
- C. 항상 Pod priority 증가
- D. 항상 Cluster Autoscaler 설치

<details>
<summary>정답 보기</summary>

**정답: B. claim·class·binding mode·consumer scheduling·driver·provisioning identity 확인**

Pending 자체가 storage 실패는 아닙니다. WaitForFirstConsumer는 적합한 소비 Pod가 스케줄될 때까지 정상적으로 기다릴 수 있습니다. EBS·IAM 오류라고 가정하기 전에 실제 driver·compute 경로를 식별합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,status:.status,spec:.spec,storageClassFieldPresent:(.spec | has("storageClassName"))}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
SC_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.storageClassName // empty')
if [ -n "$SC_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get storageclass "$SC_NAME" -o yaml
else
  printf 'Inspect absent versus explicitly empty storageClassName and default/static binding intent.\n'
fi
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -n "$PV_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o yaml
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json \
    | jq --arg pv "$PV_NAME" '.items[] | select(.spec.source.persistentVolumeName == $pv) | {name:.metadata.name,spec,status}'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json \
  | jq --arg pvc "$PVC_NAME" '.items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName == $pvc)) | {name:.metadata.name,node:.spec.nodeName,phase:.status.phase,conditions:.status.conditions}'
```

helper는 storageClassName 부재·빈 문자열을 구분하고 JSON으로 소비자를 찾습니다. 기존 spec.volumes.persistentVolumeClaim.claimName Pod field selector는 지원되지 않습니다. Bound라면 binding 완료를 앱 검증으로 취급하지 말고 mount·read를 조사합니다.

**관찰한 상태 확인**

- Class·provisioner: 실제 class와 표준 EBS·Auto Mode·EFS 등 driver를 확인합니다. 명시적 빈 class와 default 생략은 binding 의도가 다릅니다.
- 지연 binding: 소비자의 requests·taint·affinity·zone·capacity를 확인합니다. node 공급·priority·autoscaling이 소비자를 통해 PVC에 간접 영향을 줄 수 있으므로 A·C·D를 보편적 해결책으로 단정하지 않습니다.
- Identity: node role만 보지 말고 실제 controller IRSA·Pod Identity·KMS 권한을 확인합니다. Fargate는 EBS mount 불가이며 Auto Mode는 별도 provisioner입니다.
- CSI: controller·node health, event, 현재 호환 add-on·owner를 확인합니다. 원인을 찾기 전에 force 재설치하지 않습니다.

**Class와 데이터 생명주기**

claim 하나를 고치려고 기존 StorageClass의 immutable binding mode를 patch하거나 cluster default를 바꾸지 않습니다. 새로 명시적으로 선택할 표준 class 예시입니다.

```yaml
# New, explicitly selected StorageClass for standard EBS CSI, not an in-place edit.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

기존 class에 바로 적용하는 명령이 아닌 설정 예시입니다. Retain은 별도 처리를 위해 storage를 남겨 비용이 계속될 수 있습니다. PVC YAML은 데이터 백업이 아니며 삭제·재생성은 데이터를 잃거나 retained volume의 재바인딩을 필요로 할 수 있습니다.

Auto Mode는 위 표준 provisioner가 아닌 ebs.csi.eks.amazonaws.com을 사용합니다. node root·data 암호화가 모든 dynamic PVC의 암호화를 뜻하지 않습니다. encrypted true를 명시하고 실제 EBS volume·key를 확인합니다. bound claim의 provisioner·class 변경 대신 문서화된 snapshot 또는 해당 Retain·static migration을 사용합니다.

**Terraform 소유권 예시**

기존 표준 EBS CSI add-on의 검토한 version, 전체 schema-validated config와 controller identity를 선택합니다. 아래 IRSA 예시는 Pod Identity를 함께 설정하지 않습니다.

```hcl
# Existing standard EBS CSI add-on with a reviewed IRSA identity.
# Preserve/import its existing resource ownership; do not create a duplicate add-on.
resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = var.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.reviewed_ebs_addon_version
  service_account_role_arn    = var.controller_irsa_role_arn
  configuration_values        = file(var.reviewed_configuration_file)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

기존 소유권을 유지·import합니다. controller에는 현재 EBS 권한·tag 조건과 필요 시 customer key 권한이 필요합니다. 과거 IAM module·add-on version 조합은 현재 호환성 보장이 아니며 role-only가 add-on role을 연결하지도 않습니다. [스토리지 본문](../../eks/04-eks-storage-part1.md)과 현재 catalog를 따릅니다.

같은 새 class를 현재 Kubernetes resource로 관리할 수도 있습니다.

```hcl
# New standard-driver class, explicitly selected by test PVCs.
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "diagnostic-ebs-gp3"
  }
  storage_provisioner    = "ebs.csi.aws.com"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Retain"
  parameters = {
    type                        = "gp3"
    encrypted                   = "true"
    "csi.storage.k8s.io/fstype" = "ext4"
  }
}
```

class 소유권은 YAML 또는 Terraform 중 하나를 선택합니다. provider field·syntax의 로컬 검토가 대상 환경의 IAM·CSI provisioning·데이터 복구를 증명하지는 않습니다.

**분리된 프로비저닝 검사**

검토한 Linux EC2 경로는 [EKS 업그레이드](../../eks/08-eks-upgrades.md)의 완전한 eks-upgrade-smoke.py를 저장하고 test context·class를 명시합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test context}"
: "${TEST_STORAGE_CLASS:?Set the reviewed compatible test class}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
# Save the complete helper from the EKS upgrades source guide first.
python3 eks-upgrade-smoke.py
```

고유 namespace와 PVC writer를 지연 binding 대기 전에 생성하고 별도 consumer로 marker를 읽습니다. 근거·실패 리소스를 보존하며 실제 실행 시 storage 비용·Retain 정리를 고려합니다. 이번 감사에서는 cloud provisioning·volume 생성·mount·benchmark를 실행하지 않았습니다. 무관한 과금 volume을 만들던 AWS CLI Job을 PVC 진단으로 사용하지 않습니다.

출처: [StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/), [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html), [Auto Mode class](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html).

</details>

### 6. 자동 확장이 기대대로 동작하지 않을 때 가장 효과적인 조사는 무엇인가요?

- A. 모든 Pod에 resource 추가
- B. 수동 node 추가 후 조사 종료
- C. replica·resource·node 소유자를 식별하고 metrics·condition·limit·identity·event 확인
- D. cluster 재생성

<details>
<summary>정답 보기</summary>

**정답: C. replica·resource·node 소유자를 식별하고 metrics·condition·limit·identity·event 확인**

HPA replica 확장, VPA resource 추천·갱신, CA·Karpenter·Auto Mode node provisioning을 구분합니다. 제어 대상·신호가 다르며 모두 설치해야 하는 것은 아닙니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa -o json \
  | jq '.items[] | {name:.metadata.name,target:.spec.scaleTargetRef,min:.spec.minReplicas,max:.spec.maxReplicas,current:.status.currentReplicas,desired:.status.desiredReplicas,metrics:.status.currentMetrics,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

HPA condition·현재 metrics·requests·min/max·behavior를 확인합니다. desired/current 차이는 정상 수렴일 수 있고 metric 부재·오류는 scale-down을 막을 수 있습니다. CPU·memory resource metrics는 Metrics Server, custom·external metrics는 별도 adapter·integration을 사용합니다. 조회 실패가 API·CRD 부재를 증명하지 않습니다.

기존 관리형 그룹은 추정 tag로 계정 전체를 찾지 말고 실제 ASG를 조회합니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{scaling:scalingConfig,health:health,autoScalingGroups:resources.autoScalingGroups}'
: "${ASG_NAME:?Select the actual group returned above}"
aws autoscaling describe-auto-scaling-groups --region "$AWS_REGION" \
  --auto-scaling-group-names "$ASG_NAME" \
  --query 'AutoScalingGroups[].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:Instances,Tags:Tags}'
```

CA는 평균 node CPU가 높아서가 아니라 unschedulable Pod·제약에 반응합니다. 지원 minor, 실제 Pod identity, 최소 discovery·scaling 권한, ASG tag, max size, EC2·IP quota와 launch 실패를 확인합니다. node-group tag가 ASG discovery tag를 증명하지 않습니다. 관리형 limit은 EKS·인프라 owner를 우선하며 직접 ASG 변경은 drift, scaling config 변경은 PDB 미준수로 이어질 수 있습니다.

Karpenter·Auto Mode는 해당 NodePool·NodeClaim·provider limit·event를 확인합니다. 고정 CA label 조회가 비었다고 CA 설치를 권하지 않습니다. VPA Off·Initial은 의도적일 수 있습니다. Auto는 Recreate로 대체되어 deprecated이며 mode 변경은 중단과 같은 CPU·memory 신호의 HPA 상호작용을 일으킬 수 있습니다.

**Helm·Terraform 설정 예시**

기존 Helm 소유 CA·Metrics Server에만 사용합니다. 검토한 chart version과 cluster minor에 호환되는 CA image version을 전달합니다. chart 기본 image가 대상보다 늦을 수 있습니다. 구성 요소별 owner를 하나로 유지합니다.

```hcl
# Existing Helm-owned installations only; supply reviewed compatible versions.
# The IRSA trust subject must match kube-system:cluster-autoscaler.
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  version    = var.ca_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  values = [yamlencode({
    autoDiscovery = { clusterName = var.cluster_name }
    awsRegion     = var.aws_region
    image         = { tag = var.ca_image_tag }
    rbac = {
      serviceAccount = {
        create = true
        name   = "cluster-autoscaler"
        annotations = {
          "eks.amazonaws.com/role-arn" = var.ca_irsa_role_arn
        }
      }
    }
  })]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  # Retain/migrate the existing owner's reviewed values.
  values = [file(var.metrics_server_values_file)]
}
```

반복 set 블록 대신 Helm provider 3.x의 values 문서를 사용합니다. CA ServiceAccount 이름과 IRSA trust subject를 맞추며 Pod Identity는 별도 owner 설정입니다. role은 [비용·확장 본문](../../eks/07-eks-cost-optimization.md)의 제한한 권한이 필요하고 AutoScalingFullAccess를 일반 처방으로 붙이지 않습니다.

Metrics Server의 실제 검토한 values를 병합합니다. 현재 upstream default는 secure kubelet 경로이며 kubelet-insecure-tls를 기본 가정하지 않습니다. lab 한정 우회책 선택 전에 certificate·trust·address를 진단합니다. EKS add-on 소유 구성 요소에 Helm release를 중복 생성하지 않습니다. 대상 환경의 chart·identity·network·runtime 호환성을 시험해야 하며 여기서는 Helm 설치를 실행하지 않았습니다.

**HPA metrics와 behavior**

CPU·memory와 scale-up/down 정책 개념을 보존한 resource-metrics 예시입니다.

```yaml
# Example resource metrics and behavior; requires an existing target with requests.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: applications
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      selectPolicy: Max
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      selectPolicy: Min
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

utilization target에는 requests가 필요합니다. HPA는 metrics 중 가장 큰 desired-replica 추천을 선택하며 누락·오류 metric은 downscale을 막을 수 있습니다. policy Max·Min은 허용 변화율 선택이며 stabilization은 보편적 고정 cooldown이 아닙니다. 퍼센트·범위·기간은 예시이고 memory scaling은 CPU와 다를 수 있습니다. Terraform·GitOps·다른 autoscaler가 같은 replica 값을 서로 덮어쓰지 않게 합니다.

**대시보드 예시**

단일 cluster kube-prometheus-stack, prometheus datasource UID, monitoring namespace에서 grafana_dashboard=1을 감시하는 기존 sidecar를 가정합니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoscaling-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  autoscaling-dashboard.json: |
    {
      "uid": "eks-autoscaling-diagnostics",
      "title": "EKS Autoscaling Diagnostics",
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
          "title": "HPA replicas",
          "type": "timeseries",
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
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_current_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Current {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "B",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_desired_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Desired {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "C",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_min_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Min {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "D",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_max_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Max {{namespace}}/{{horizontalpodautoscaler}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Observed node count",
          "type": "timeseries",
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
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count(max by (node) (kube_node_info{job=\"kube-state-metrics\"}))",
              "legendFormat": "Nodes"
            }
          ]
        },
        {
          "id": 3,
          "title": "Pod CPU usage (cores)",
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
              "unit": "cores"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        },
        {
          "id": 4,
          "title": "Pod working set (bytes)",
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
              "unit": "bytes"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (container_memory_working_set_bytes{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        }
      ]
    }
```

selector·UID·namespace를 실제 설치에 맞춥니다. HPA는 namespace identity를 유지하며 exporter 중복을 제거한 뒤 합칩니다. CPU는 cores, memory는 working-set bytes이며 퍼센트가 아닙니다. 다중 cluster는 cluster 차원·필터를 추가합니다. scrape 부재는 no-data·unknown으로 두며 정상 0으로 바꾸지 않습니다. dashboard는 scaling 성공·alert·automation pipeline 증명이 아닙니다.

A·B는 임시 용량 변화일 수 있지만 controller·metric 실패를 식별하지 못합니다. D는 진단 없이 migration 위험을 추가합니다. 기대·관찰 동작과 복구시킨 정확한 변경을 기록합니다.

출처: [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/), [CA AWS](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md), [CA chart](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler), [Metrics Server](https://github.com/kubernetes-sigs/metrics-server), [VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler).

</details>

### 7. NetworkPolicy가 예상과 다르게 동작할 때 가장 효과적인 조사는 무엇인가요?

- A. 모든 NetworkPolicy 삭제
- B. 실제 집행 구현, selector·policy 의미, log와 실패 flow 확인
- C. 모든 Pod에 hostNetwork 설정
- D. VPC 재생성

<details>
<summary>정답 보기</summary>

**정답: B. 실제 집행 구현, selector·policy 의미, log와 실패 flow 확인**

선언한 policy와 실제 집행 구현을 함께 확인합니다. NetworkPolicy 객체 생성만으로 enforcement engine이 설치되지는 않습니다.

**인벤토리와 의미**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,labels:.metadata.labels,owners:.metadata.ownerReferences,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,status:.status.phase}'
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" --show-labels
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" get daemonsets -A -o json \
  | jq '.items[] | {namespace:.metadata.namespace,name:.metadata.name,containers:[.spec.template.spec.containers[] | {name,image}]}'
```

빈 Pod 목록도 kubectl 종료 코드는 성공입니다. if kubectl get pods -l 결과만으로 VPC CNI·Calico·Cilium 설치를 판단하지 않습니다. 실제 owner·object·image, policy-agent 상태와 compute·kernel·version 지원을 확인합니다. Auto Mode는 NodeClass 기반 내장 network를 사용하며 임의 alternate CNI 설치를 지원하지 않습니다.

VPC CNI는 native policy를 지원합니다. 현재 AWS는 새 Pod 규칙을 구성하는 동안 처음 허용하는 standard mode와, 처음 거부하여 필요한 DNS·의존 경로가 필요한 strict mode를 구분합니다. 실제 agent container와 event logging을 확인하며 과거 “VPC CNI는 정책 미지원” 설명을 적용하지 않습니다.

**표준 networking.k8s.io/v1 NetworkPolicy**는 허용 트래픽의 합집합이며 rule priority·last-wins 충돌 해결이 없습니다. 격리된 source egress·destination ingress가 모두 연결을 허용해야 합니다. Admin·cluster-wide·vendor API는 의미가 달라 따로 확인합니다. hostNetwork 동작도 구현에 따라 다르며 모든 Pod에 설정하는 것은 안전한 해결책이 아닙니다.

**범위를 제한한 policy 예시**

아래 두 문서는 ---로 구분합니다. 기존 backend namespace, frontend web Pod, database Pod와 기존 CoreDNS Pod endpoint를 가정합니다.

```yaml
# Independent example for a reviewed backend namespace and traditional CoreDNS Pods.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: backend
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: database
          podSelector:
            matchLabels:
              app: db
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

namespace·Pod selector가 **같은 peer**에 있으므로 둘 다 일치해야 합니다. 별도 peer이면 OR입니다. namespace는 표준 kubernetes.io/metadata.name label을 사용하며 custom name label이 있다고 가정하지 않습니다.

default deny는 backend 전체를 선택하며 API Pod만 예외를 받습니다. 다른 backend workload·API 의존성은 별도 허용을 검토해야 합니다. frontend egress·database ingress는 구성하지 않습니다. DNS 규칙은 CoreDNS Pod용이며 보편적인 Auto Mode·NodeLocal resolver 경로가 아닙니다.

적합한 소유 test workload로 frontend web→API:8080 허용, 다른 namespace·label·port 거부, API→database:5432와 실제 DNS를 확인합니다. label 없는 새 debug Pod는 실제 Pod와 정책이 다를 수 있고 ping만으로 TCP·UDP를 검증하지 못합니다. 허용된 capture도 대상 network namespace·traffic·시간을 제한합니다. 별도 tcpdump Pod가 다른 모든 Pod를 관찰하지 못합니다.

**Terraform 대안**

```hcl
# Alternative owner for the same policy intent; do not also apply duplicate YAML.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}
resource "kubernetes_network_policy_v1" "api" {
  metadata {
    name      = "api-allow"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {
      match_labels = { app = "api" }
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "frontend" }
        }
        pod_selector {
          match_labels = { app = "web" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "8080"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "database" }
        }
        pod_selector {
          match_labels = { app = "db" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "5432"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
      ports {
        protocol = "TCP"
        port     = "53"
      }
    }
  }
}
```

소유자를 하나로 유지하며 전체 flow matrix를 분리된 환경에서 검토·적용합니다. 현재 provider field를 확인했지만 감사 중 policy 적용·트래픽 집행을 테스트하지 않았습니다. 미고정 Calico·Cilium 설치나 aws-node image 하나 교체는 일반 해결책이 아닙니다. 현재 구현의 지원 upgrade·migration 절차를 따릅니다.

**인벤토리는 집행 근거가 아님**

기존 kube_networkpolicy_info·calico_denied_packets 예시는 가정한 label의 실제 metric 존재를 확인하지 않았습니다. 현재 KSM은 experimental created·ingress-rule·egress-rule gauge를 문서화합니다. 기존 단일-cluster scrape·Grafana sidecar에서 다음은 선언 인벤토리를 표시합니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: network-policy-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  network-policy-dashboard.json: |
    {
      "uid": "eks-network-policy-inventory",
      "title": "Declared NetworkPolicy Inventory",
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
          "title": "Declared policies by namespace",
          "type": "timeseries",
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
              "expr": "count by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_created{job=\"kube-state-metrics\"}))",
              "legendFormat": "{{namespace}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Declared ingress/egress rule counts",
          "type": "timeseries",
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
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_ingress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Ingress {{namespace}}"
            },
            {
              "refId": "B",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_egress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Egress {{namespace}}"
            }
          ]
        }
      ]
    }
```

실제 experimental metric 노출과 job·UID·namespace를 확인합니다. rule 0은 deny-all일 수 있고 policy·rule 개수는 dropped connection이나 집행 증명이 아닙니다. telemetry 부재는 정상 0이 아닌 unknown입니다. allow·deny는 실제 구현에서 활성화한 decision log·flow 관찰의 label·schema를 검증하여 사용하며 counter를 만들거나 policy 문자열이 있는 모든 log를 거부로 해석하지 않습니다.

policy 삭제, 전체 hostNetwork, VPC 재생성은 원인 확인 없이 노출을 넓힐 수 있습니다. 실패 flow 근거를 보존하고 검증한 policy·config만 수정합니다.

출처: [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [VPC CNI policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html), [Auto Mode network](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [KSM policy metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/policy/networkpolicy-metrics.md).

</details>

### 8. Helm 배포 문제의 가장 효과적인 해결 접근은 무엇인가요?

- A. 모든 Helm release 삭제
- B. EKS cluster 재생성
- C. client·chart·dependency, release owner·permission·event·workload 동작 확인
- D. 모든 release 관리를 수동 객체로 교체

<details>
<summary>정답 보기</summary>

**정답: C. client·chart·dependency, release owner·permission·event·workload 동작 확인**

client·chart 오류, Kubernetes admission·permission, workload readiness와 앱 동작을 구분합니다. Helm 2·Tiller는 과거 migration 맥락이며 현재 Helm 3·4에는 Tiller deployment가 필요하지 않습니다.

**실제 release 조사**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${RELEASE_NAME:?}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
HELM_EVIDENCE=$(mktemp -d "$EVIDENCE_PARENT/helm-diagnosis.XXXXXXXX")
helm version --short
helm status "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm history "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm get values "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > "$HELM_EVIDENCE/values.yaml"
helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  > "$HELM_EVIDENCE/manifest.yaml"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp' > "$HELM_EVIDENCE/events.txt"
printf 'Review protected evidence in %s\n' "$HELM_EVIDENCE"
```

조회 실패는 permission·network·context 문제일 수 있으며 release 부재의 증거가 아닙니다. values·rendered manifest에는 credentials·Secret data가 있을 수 있으므로 보호하고 공유 전 가립니다. app.kubernetes.io/instance 같은 label은 관례이며 전체 소유권 인벤토리가 아닙니다. release manifest에서 실제 resource를 식별하고 condition·event를 확인합니다.

Helm client의 Kubernetes identity와 chart values의 workload ServiceAccount는 다릅니다. 현재 helm install --service-account option은 없습니다. chart가 문서화한 values와 실제 actor의 RBAC를 확인합니다. impersonation에는 권한이 필요하며 EKS access-policy grant 전체를 재현하지 못합니다.

**변경 전 설정 검증**

```bash
set -euo pipefail
: "${CHART_DIR:?}"; : "${VALUES_FILE:?}"; : "${KUBE_VERSION:?Set the target capability version}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
RENDER_DIR=$(mktemp -d "$EVIDENCE_PARENT/helm-render.XXXXXXXX")
# For charts with dependencies, first review/commit Chart.lock and build from that lock.
helm lint "$CHART_DIR" --values "$VALUES_FILE"
helm template review "$CHART_DIR" --namespace review \
  --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
  > "$RENDER_DIR/rendered.yaml"
```

render·lint는 server API·admission, CRD 설치, image·readiness·앱 테스트 성공을 증명하지 않습니다. install의 debug도 실제 설치입니다. dependency update는 lock·선택 버전을 바꿀 수 있으므로 검토한 Chart.lock과 dependency build를 사용합니다. lock이 없으면 build도 의존성을 해결할 수 있어 고정 검증이라고 설명하면 안 됩니다.

충돌은 기존 owner와 의도한 migration을 먼저 확인합니다. 자동 uninstall·남은 resource 삭제·force·take-ownership·새 release 이름으로 해결하지 않습니다. data 영향·중복 controller가 생길 수 있습니다. owned upgrade 전에 현재 values·schema·CRD·stateful 의존성을 보존합니다.

**Terraform Helm provider 의미**

로컬 확인한 provider 3.3 schema, 이미 준비한 namespace와 release owner 예시입니다. 긴 apply에 단발성 short-lived token을 저장하기보다 검토한 exec-credential kubeconfig를 사용합니다.

```hcl
# Choose the existing release/configuration owner and reviewed chart artifact.
variable "verify_chart_provenance" {
  type = bool
}
provider "helm" {
  debug = false
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}
resource "helm_release" "example" {
  name              = var.release_name
  repository        = var.chart_repository
  chart             = var.chart_name
  version           = var.chart_version
  namespace         = var.release_namespace
  create_namespace  = false
  values            = [file(var.reviewed_values_file)]
  dependency_update = false
  lint              = true
  wait              = true
  wait_for_jobs     = true
  timeout           = 600
  atomic            = true
  verify            = var.verify_chart_provenance
  keyring           = var.chart_keyring
}
```

lint는 **유효한** release field이며 plan에서 Helm lint를 실행합니다. debug는 helm_release가 아닌 provider 설정입니다. provider 3.x는 set = [...] 같은 nested attribute를 쓰며 위 values-file 방식은 과거 반복 set block을 사용하지 않습니다.

verify는 trusted keyring으로 chart package provenance를 확인하며 Helm test hook을 실행하지 않습니다. 실제 artifact·배포 방식의 provenance·trust 구성을 확인한 경우 사용합니다. wait_for_jobs·wait는 job·readiness 대기이지 모든 앱 테스트가 아닙니다. atomic은 Helm의 install 실패 정리·upgrade rollback이며 DB·PVC 데이터 복원이나 모든 hook·CRD·external side effect 복구가 아닙니다.

set_sensitive는 표시를 가리지만 일반 state·release에 저장된 값을 공개해도 되게 만들지는 않습니다. 별도 관리 secret 참조를 우선하고 Terraform state·Helm release storage를 보호합니다. 이번 검토에서는 provider apply·release 설치를 하지 않았습니다.

**Chart test hook**

chart에 my-chart.fullname helper, 같은 Service 이름과 설정한 HTTP path가 있어야 합니다. 아래는 values 발췌와 **별도 template 파일 두 개**입니다.

```yaml
# Relevant values fragment for the chart that owns the Service.
service:
  port: 80
tests:
  enabled: true
  image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
  apiPath: /api/health
```

templates/tests/test-connection.yaml로 저장합니다.

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-connection" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v/" (include "my-chart.fullname" .) .Values.service.port | quote }}
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
{{- end }}
```

templates/tests/test-api.yaml로 저장합니다.

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-api" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v%s" (include "my-chart.fullname" .) .Values.service.port .Values.tests.apiPath | quote }}
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
{{- end }}
```

test label은 앱 selector label을 복사하지 않습니다. probe는 stdout으로 응답을 출력하고 Kubernetes API token 없이 request·Pod 수명을 제한합니다. before-hook-creation은 다음 실행·소유 cleanup 전까지 로그용 결과를 유지하면서 반복 테스트를 허용합니다. HTTP 확인만으로 모든 비즈니스 동작이 검증되지는 않으며 /api/health가 실제로 있어야 합니다.

이미 준비한 분리된 test cluster에서는 release·namespace를 명시합니다.

```bash
set -euo pipefail
: "${TEST_CONTEXT:?Set the owned disposable cluster context}"
: "${TEST_NAMESPACE:?Choose a new unique namespace}"
: "${TEST_RELEASE:?}"; : "${CHART_DIR:?}"; : "${VALUES_FILE:?}"
# Fails on an existing namespace rather than adopting it.
TEST_NAMESPACE_UID=$(kubectl --context "$TEST_CONTEXT" create namespace "$TEST_NAMESPACE" \
  -o jsonpath='{.metadata.uid}')
printf 'Test namespace: %s UID: %s\n' "$TEST_NAMESPACE" "$TEST_NAMESPACE_UID"
helm install "$TEST_RELEASE" "$CHART_DIR" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --values "$VALUES_FILE" --wait --timeout 5m
helm test "$TEST_RELEASE" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --logs --timeout 90s
```

실패하면 resource·hook·workload log를 보존합니다. namespace UID를 기록하고 정리 전에 확인하며 기존 namespace를 삭제하지 않습니다. change trigger가 없던 null_resource는 release 변경마다 재검증을 보장하지 않았습니다.

**정적 CI 예시**

committed dependency·Chart.lock과 secret-free ci/values.yaml이 있는 chart를 검사합니다. path·target capability version을 맞춥니다. dependency가 없는 chart는 lock·build 단계를 생략합니다. cluster를 만들거나 runtime test 통과를 주장하지 않습니다.

```yaml
name: Static Helm chart validation
on:
  pull_request:
    paths:
      - charts/**
      - ci/values.yaml
      - .github/workflows/helm-validate.yml
permissions:
  contents: read
jobs:
  lint-render:
    runs-on: ubuntu-24.04
    env:
      CHART_DIR: charts/my-chart
      VALUES_FILE: ci/values.yaml
      KUBE_VERSION: "1.36.0"
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: Azure/setup-helm@9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310 # v5.0.1
        with:
          version: v3.21.3
      - name: Build reviewed dependencies, lint and render
        shell: bash
        run: |
          set -euo pipefail
          umask 077
          test -f "$CHART_DIR/Chart.lock"
          helm dependency build "$CHART_DIR"
          helm lint "$CHART_DIR" --values "$VALUES_FILE"
          helm template chart-ci "$CHART_DIR" --namespace chart-ci \
            --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
            > "$RUNNER_TEMP/chart-rendered.yaml"
```

setup action·release pin은 공식 metadata로 확인했습니다. 필요하면 소유 disposable 환경에서 integration·hook 단계를 별도로 실행합니다. chart-testing을 사용한다면 보고된 release·namespace·test option을 사용하며 chart directory 이름으로 뒤의 helm test 대상을 추정하지 않습니다.

모든 chart 삭제, EKS 재생성, release manager 포기는 원래 chart·permission·runtime 문제를 진단하지 못합니다.

출처: [Helm debugging](https://helm.sh/docs/chart_template_guide/debugging/), [chart tests](https://helm.sh/docs/topics/chart_tests/), [Helm provider release](https://registry.terraform.io/providers/hashicorp/helm/latest/docs/resources/release), [setup-helm release](https://github.com/Azure/setup-helm/releases/tag/v5.0.1), [Helm 3.21.3](https://github.com/helm/helm/releases/tag/v3.21.3).

</details>

### 9. 메모리 누수와 다른 pressure 원인을 구분하는 접근은 무엇인가요?

- A. 모든 Pod 재시작
- B. node 크기만 증가
- C. memory·process 근거, limit·runtime profile·앱 code를 연결해 분석
- D. node 수만 증가

<details>
<summary>정답 보기</summary>

**정답: C. memory·process 근거, limit·runtime profile·앱 code를 연결해 분석**

working set 증가, OOMKilled 또는 Node MemoryPressure만으로 누수를 확정하지 않습니다. 부하·process lifetime·UID, heap·native memory, cache·limit를 비교한 뒤 수정합니다.

**비교 가능한 근거 수집**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${APP_SELECTOR:?Set an explicit label selector}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
MEMORY_DIR=$(mktemp -d "$EVIDENCE_PARENT/memory-observation.XXXXXXXX")
for sample in {1..10}; do
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$MEMORY_DIR/sample-$sample.time"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$APP_SELECTOR" -o json \
    | jq '[.items[] | {
        name:.metadata.name,uid:.metadata.uid,created:.metadata.creationTimestamp,
        node:.spec.nodeName,phase:.status.phase,
        resources:[.spec.containers[] | {name,resources}],
        containers:((.status.initContainerStatuses // []) + (.status.containerStatuses // []))
      }]' > "$MEMORY_DIR/sample-$sample.pods.json"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods \
    -l "$APP_SELECTOR" --containers > "$MEMORY_DIR/sample-$sample.usage.txt"
  if [ "$sample" -lt 10 ]; then sleep 30; fi
done
printf 'Observations saved to %s; these samples do not establish a leak.\n' "$MEMORY_DIR"
```

30초 간격으로 10회 관찰하며 원래 약 5분 수집 계획에 command 시간이 더해지는 예시입니다. 감사 중 실행하지 않았고 짧은 기간으로 장기 누수를 증명하지 못합니다. 조회 실패 시 중단하고 부분 근거를 남깁니다. metric 부재를 0으로 바꾸지 않습니다.

Pod-name prefix를 label 값으로 혼동하지 않고 명시적 selector를 사용합니다. 없는 네 번째 column을 sort하지 않습니다. snapshot은 UID와 일반·init container 상태를 기록합니다. Pod 교체 후 이름이 재사용될 수 있고 metric·status 조회는 atomic snapshot이 아닙니다. current·last termination, restart를 보되 status에는 제한된 이력만 남음을 고려합니다.

**Memory pressure 해석**

- Working set·RSS·managed heap·native allocation은 다른 측정입니다. cache·traffic 증가도 누수처럼 보일 수 있습니다.
- node에 여유가 있어도 container cgroup limit으로 OOM이 발생합니다. request·limit 차이만으로 원인이 결정되지는 않습니다.
- kubelet은 node process이며 kube-system의 일반 kubelet-pod가 아닙니다. 지원 node·monitoring 경로를 사용합니다.
- fragmentation은 근거가 필요한 가설이며 주기적 reboot·강제 GC는 보편적인 해결책이 아닙니다.

**현재 metric과 단위 예시**

기존 단일-cluster kube-prometheus-stack에서 현재 container limit metric을 사용하고 exporter 중복·누락·0 limit를 처리합니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: memory-observation
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
  - name: memory-observation
    rules:
    - alert: ContainerWorkingSetHigh
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Container working set is above 85% of its declared limit
        description: Inspect {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container
          }} and actual termination/pressure evidence.
    - alert: ContainerWorkingSetCritical
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Container working set is above 95% of its declared limit
        description: This is an observation threshold, not proof of a leak or guaranteed
          OOM prediction.
    - alert: ContainerWorkingSetGrowth
      expr: max by (namespace, pod, container) (deriv(container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""}[30m]))
        > 5 * 1024 * 1024 / 60
      for: 30m
      labels:
        severity: warning
      annotations:
        summary: Estimated working-set slope exceeds 5 MiB/min
        description: The rolling 30-minute regression has stayed above the threshold;
          correlate with load and process lifetime.
    - alert: NodeMemoryPressure
      expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"})
        == 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Node {{ $labels.node }} reports MemoryPressure
        description: Investigate node resources and workloads; this is distinct from
          a container limit OOM.
```

namespace·release·job selector를 실제 설치에 맞춥니다. 일반 container limit 기준이며 init-container·Pod-level budget은 별도로 확인합니다. 양의 limit가 보고되지 않는 container는 ratio가 없으므로 별도 coverage를 확인하고 정상으로 간주하지 않습니다. working-set/limit threshold는 관찰 예시이며 heap-leak detector가 아닙니다.

deriv 결과는 여기서 **bytes/second**입니다. 5 * 1024 * 1024를 60으로 나누어 **5 MiB/min**으로 맞춥니다. 기존 식은 5 MiB/s였지만 설명은 분당이었습니다. 30분 regression과 for 30m 조건은 매 순간 단조 증가의 증명이 아닙니다. scrape 부재·restart·workload 변화도 고려합니다.

**Runtime profiling 전제**

| Runtime | 올바른 조사 범위 |
| --- | --- |
| JVM | 맞는 JDK 도구·권한으로 실제 PID를 조사. jcmd PID GC.heap_info 지원. native-memory 보고에는 적절한 startup tracking 필요. heap dump는 pause·secret 포함 가능 |
| Node.js | 실제 process의 지원 inspector·profiling 사용. node --inspect는 새 process 시작이며 debugger 접근을 제한 |
| Python | 실제 앱·통제된 재현에 profiling·tracemalloc 구성. 별도 interpreter는 기존 process allocation을 보지 못하며 Python 추적이 모든 native RSS는 아님 |
| Go | 실제 보호된 heap profile, 맞는 binary·symbol로 pprof 사용. 인증 없는 endpoint나 /tmp/profile이 이미 있다고 가정하지 않음 |

운영 사용 전 tool·runtime version·overhead를 확인합니다. 기본 조치로 실행 중 앱에 임의 profiling package를 설치하지 않습니다. 여기서는 JVM·profiler·heap dump·실측 memory 실험을 실행하지 않았습니다.

**애플리케이션 설정 예시**

원래 256m·768m heap, 1Gi container 값은 측정한 최적값이 아닌 예시로 유지합니다. OpenJDK 21은 JAVA_TOOL_OPTIONS를 읽으며 JAVA_OPTS는 entrypoint가 전달해야 적용됩니다. command-line·_JAVA_OPTIONS가 덮어쓸 수 있으므로 실제 적용 option을 확인합니다. JVM 시작 시 option이 출력될 수 있어 secret을 넣지 않습니다.

```yaml
# Pod-template fragment for an existing reviewed OpenJDK 21 application container.
# Merge through its owner; this is not a standalone Deployment manifest.
spec:
  template:
    spec:
      containers:
        - name: java-app
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
              ephemeral-storage: 2Gi
            limits:
              cpu: "1"
              memory: 1Gi
              ephemeral-storage: 4Gi
          env:
            - name: JAVA_TOOL_OPTIONS
              value: >-
                -XX:+UseG1GC -XX:MaxGCPauseMillis=200
                -Xms256m -Xmx768m
                -XX:+HeapDumpOnOutOfMemoryError
                -XX:HeapDumpPath=/diagnostics
                -XX:+ExitOnOutOfMemoryError
          volumeMounts:
            - name: heap-diagnostics
              mountPath: /diagnostics
      volumes:
        - name: heap-diagnostics
          emptyDir:
            sizeLimit: 2Gi
```

실제 image·startup·다른 env·volume·security context를 유지하고 앱 UID의 diagnostic mount 쓰기 권한을 확인합니다. MaxGCPauseMillis는 soft target입니다. heap 외 native allocation·thread·code·metaspace 등의 overhead 공간도 측정해 확보합니다.

disk-backed emptyDir는 제한되어 있지만 Pod 삭제 후 보존되지 않습니다. artifact를 의도적으로 수집·보호하고 PID 재사용 시 파일명 충돌을 고려합니다. kernel·cgroup SIGKILL이면 JVM dump 처리가 실행되지 못할 수 있습니다. ExitOnOutOfMemoryError는 JVM이 던진 OOM을 처리할 뿐 dump·원인 해결을 보장하지 않습니다.

기존 MEMORY_MONITOR_*는 JVM·Kubernetes 내장 기능이 아닙니다. Spring Actuator probe path는 앱이 실제로 활성화·노출한 경우에만 맞으므로 실제 health contract를 사용합니다.

**기존 monitoring 관리**

```hcl
# Prometheus Operator CRD must already exist before planning this resource.
# Save the reviewed PrometheusRule YAML above as the supplied file.
resource "kubernetes_manifest" "memory_alerts" {
  manifest = yamldecode(file(var.memory_rules_file))
}
```

manifest provider는 plan 중 PrometheusRule CRD가 필요합니다. 같은 apply의 Helm 설치에 depends_on만 걸어 schema discovery를 일반적으로 해결할 수 없습니다. 기존 stack과 6번 working-set panel을 재사용하고 stack을 중복 설치하거나 설명 없는 dashboard file을 참조하지 않습니다. 실제 rule selection·alert routing·telemetry health를 검증합니다.

A·B·D는 임시 완화일 수 있지만 allocation 결함을 증명·수정하지 않습니다. 입증한 원인을 기록하고 대표 부하에서 실제 code·config 수정을 검증합니다.

출처: [Prometheus deriv](https://prometheus.io/docs/prometheus/latest/querying/functions/#deriv), [현재 Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md), [OpenJDK 21 option 처리](https://github.com/openjdk/jdk21u/blob/master/src/hotspot/share/runtime/arguments.cpp), [Java 21 options](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html), [jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html).

</details>

### 10. EKS DNS 해석 실패의 가장 효과적인 조사는 무엇인가요?

- A. 모든 Pod에 고정 IP
- B. 실제 Pod resolver·DNS 구현·policy·전송·upstream 경로 추적
- C. 모든 Service에 ExternalName 사용
- D. VPC 재생성

<details>
<summary>정답 보기</summary>

**정답: B. 실제 Pod resolver·DNS 구현·policy·전송·upstream 경로 추적**

문제 Pod의 실제 resolver와 실패한 이름부터 확인합니다. 도구 부재, DNS 응답, UDP·TCP 전송, upstream·private-zone 설정과 앱 cache를 구분합니다.

**실제 Pod 경로 확인**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,dnsPolicy:.spec.dnsPolicy,dnsConfig:.spec.dnsConfig}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- cat /etc/resolv.conf
# Run only where the selected container actually has this diagnostic tool.
: "${DNS_TEST_NAME:?Set the actual Service FQDN or reviewed external name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- nslookup "$DNS_TEST_NAME"
```

image에 cat·nslookup이 없으면 도구 제한이지 DNS 실패가 아닙니다. 실제 network·identity context를 유지하는 준비된 진단 방법을 사용합니다. 새 debug Pod는 label·policy·DNS가 다를 수 있습니다. DNS 서버의 Service 이름을 DNS로 먼저 해석하는 순환 검사 대신 실제 nameserver IP로 전송을 확인합니다. 필요한 UDP·TCP 53을 검사하며 TCP 연결만으로 DNS 응답을 검증하지 못합니다.

기존 CoreDNS는 Deployment readiness, Service·EndpointSlice, config·log를 확인합니다.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"
# Traditional CoreDNS path only; pure Auto Mode node DNS is different.
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get service kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get endpointslices \
  -l kubernetes.io/service-name=kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --all-containers=true --prefix=true --since=15m --tail=100
```

**Auto Mode node의 CoreDNS는 node system service입니다.** 순수 Auto는 기존 Deployment가 없을 수 있고 혼합은 비 Auto node용 Deployment를 유지해야 합니다. 모든 cluster에서 Deployment 부재를 장애로 보거나 Auto Mode에 두 번째 node-local DNS를 설치하지 않습니다.

**Resolver 설정과 policy**

cluster DNS가 필요한 일반 Pod는 ClusterFirst 경로입니다. 의도한 hostNetwork Pod는 보통 ClusterFirstWithHostNet이 필요합니다. DNS를 고치려고 hostNetwork를 켜면 격리가 바뀌므로 보편적 해결책이 아닙니다. DNSPolicy None은 완전하고 의도적인 resolver 설정이 필요합니다.

기존 169.254.20.10은 선택한 NodeLocal DNSCache 주소이지 보편적 VPC resolver가 아닙니다. 8.8.8.8 같은 public resolver는 Kubernetes Service zone·AWS private name을 제공하지 않고 nameserver 목록도 zone-aware fallback을 보장하지 않습니다. 172.20.0.10·public backup을 고정하지 말고 실제 upstream·cluster domain을 확인합니다.

표준 CoreDNS Pod 경로의 DNS 허용 예시입니다. 적용 전에 나머지 앱 egress를 검토합니다.

```yaml
# Example for application Pods using traditional CoreDNS Pod endpoints.
# This selects applications and isolates other egress unless another policy allows it.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-dns-egress
  namespace: applications
spec:
  podSelector:
    matchLabels:
      app: example
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

source egress·destination ingress가 모두 허용해야 할 수 있습니다. 같은 peer의 namespace·Pod selector는 AND입니다. Auto Mode·NodeLocal은 구현별 경로를 확인하며 Pod label로 host cache를 선택한다고 가정하지 않습니다. 별도 tcpdump Pod가 다른 workload의 질의를 관찰하지 못하므로 실제 context에서 허용된 제한적 capture를 사용합니다.

**올바른 VPC DNS 조회**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
VPC_ID=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsHostnames
DHCP_OPTIONS_ID=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$AWS_REGION" \
  --query 'Vpcs[0].DhcpOptionsId' --output text)
aws ec2 describe-dhcp-options --dhcp-options-ids "$DHCP_OPTIONS_ID" --region "$AWS_REGION"
```

DNS 속성은 DescribeVpcs field가 아니라 DescribeVpcAttribute입니다. cluster name·region을 명시하고 임의 kubeconfig alias를 나누어 이름을 추정하지 않습니다. 먼저 account·context를 확인합니다. 공유 설정 변경 전에 DHCP·routing·forwarding·private zone을 확인하며 새 DHCP option set 생성·연결을 일반 복구로 사용하지 않습니다.

**CoreDNS 설정과 owner**

설치된 EKS 관리형 add-on은 version·config와 검토한 후보의 schema를 확인합니다.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name coredns --output json
: "${COREDNS_ADDON_VERSION:?Select a reviewed compatible candidate}"
aws eks describe-addon-configuration --addon-name coredns \
  --addon-version "$COREDNS_ADDON_VERSION" --region "$AWS_REGION" --output json
```

custom zone·forwarder를 보존하고 probe와 health·ready plugin을 맞춥니다. replica·CPU·memory·PDB·placement·autoscaling은 workload별 검토가 필요합니다. 기존 3 replicas·70Mi·170Mi는 보편적 최적 설정이 아닙니다. 소유 Deployment를 과거 EKS-Distro 1.8.7 image로 교체하거나 generic Corefile로 전체 customization을 덮어쓰지 않습니다.

Terraform owner는 기존 add-on과 VPC 조회를 관리할 수 있습니다.

```hcl
# Existing EKS-managed CoreDNS for standard/mixed clusters only.
# Preserve/import the existing resource; do not duplicate its ownership.
resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.reviewed_coredns_version
  configuration_values        = file(var.complete_reviewed_coredns_config)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

# Read an existing VPC; do not add a second aws_vpc resource to repair DNS.
data "aws_vpc" "cluster" {
  id = var.cluster_vpc_id
}
output "vpc_dns_attributes" {
  value = {
    enable_dns_support   = data.aws_vpc.cluster.enable_dns_support
    enable_dns_hostnames = data.aws_vpc.cluster.enable_dns_hostnames
  }
}
```

전체 config file을 선택한 schema·현재 설정과 검증합니다. PRESERVE는 명시적 payload의 전체 병합을 보장하지 않습니다. [EKS 업그레이드](../../eks/08-eks-upgrades.md)의 exact-update 절차와 실제 DNS 검증을 수행합니다. 이 예시는 Auto node DNS 설정·공유 VPC 교체가 아닙니다.

**지원 표준 node 환경의 선택적 NodeLocal DNSCache**

[공식 설치 가이드](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)와 검토한 release manifest를 사용합니다. 기존 수동 DaemonSet은 불완전하여 image만 교체해도 interface·filter rule·mount·upstream Service·kubelet 연결이 생기지 않습니다.

| 결정 | 준비 |
| --- | --- |
| Local address | 충돌 없는 local IP, 실제 cluster domain·CoreDNS Service IP와 IPv6 IP:port 구문 확인 |
| 기존 data plane | 문서의 iptables 경로는 local·CoreDNS Service IP 모두 listen. 지원 IPVS 환경은 local만 listen하여 kubelet cluster-DNS 변경 필요. 다른 mode는 해당 현재 통합 안내 확인 |
| Manifest·config | 문서화된 placeholder를 처리하고 privilege·interface·filter·lock mount·probe·upstream 유지. 과거 partial DaemonSet으로 대체하지 않음 |
| Workload 이전 | node·kubelet 설정과 신규·기존 Pod resolver를 맞추고 cache·kubelet 변경 모두의 단계적 rollout·복구 계획 |
| Memory·운영 | query·cache·concurrency 관찰로 sizing, failure 감시와 restart·rollout 중 DNS 유지 |

NodeLocal은 cache miss를 적절한 upstream으로 전달하며 모든 요청이 local cache hit가 되지는 않습니다. 공식 안내는 OOM 종료 후 packet-filtering rule이 재시작 전까지 비정상 cache를 가리켜 DNS 중단이 생길 수 있다고 설명합니다. 작은 고정 memory request·cache 추가가 성능을 자동 보장하지 않습니다.

이번 검토에서 DNS 질의·capture·CoreDNS update·NodeLocal 설치·Terraform apply는 실행하지 않았습니다. 선택한 topology·가정을 통제된 환경에서 검증합니다.

고정 Pod IP, 모든 Service의 ExternalName, VPC 재생성은 실패 resolver 경로를 식별하지 않습니다. 실제 질의·응답, source context·설정 변경과 복구 근거를 기록합니다.

출처: [EKS CoreDNS](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html), [Auto Mode DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [Pod DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [VPC DNS](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html), [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/).

</details>
