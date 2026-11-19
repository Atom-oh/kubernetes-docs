# Node Instance Profile에서 IRSA·EKS Pod Identity로: 동작 원리와 마이그레이션

> **지원 버전**: Amazon EKS 표준 지원 버전, EC2 Linux 노드 (Pod Identity는 Fargate 미지원)
> **마지막 업데이트**: 2026년 11월 19일

많은 EKS 클러스터가 처음에는 **노드 IAM Role(instance profile)** 에 S3·DynamoDB·SQS 권한을 붙여서 시작합니다. 동작은 하지만, 그 노드에 뜬 **모든 Pod가 같은 권한을 공유**합니다. 이 글은 그 상태에서 Pod 단위 권한인 **IRSA(IAM Roles for Service Accounts)** 와 **EKS Pod Identity** 로 옮기는 절차를 다룹니다. 세 방식이 자격 증명을 어떻게 얻는지 그림으로 먼저 보고, 실제로 배포해 비교하는 데모와 단계별 마이그레이션 runbook을 이어서 설명합니다.

데모 코드: [`examples/security/pod-iam-migration`](../../examples/security/pod-iam-migration/README.md)

## 1. 왜 옮겨야 하나: 노드 Role은 "노드에 있는 모두"의 Role

AWS SDK는 코드에 키가 없으면 **default credential provider chain** 을 순서대로 확인합니다. 환경 변수, web identity 토큰, 컨테이너 자격 증명 엔드포인트를 모두 못 찾으면 마지막으로 **IMDS(169.254.169.254)** 에 묻습니다. IMDS가 돌려주는 것은 그 EC2의 instance profile, 즉 노드 Role의 임시 자격 증명입니다.

```text
                    EC2 Worker Node  (instance profile = NodeInstanceRole)
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                                                                          │
 │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                 │
 │   │ payments-api │   │  batch-job   │   │ compromised  │                 │
 │   │ (needs S3)   │   │ (needs SQS)  │   │ (needs none) │                 │
 │   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                 │
 │          │ SDK chain: env? ✗ web identity? ✗ container creds? ✗           │
 │          └──────────────────┼──────────────────┘                         │
 │                             ▼                                            │
 │          ┌────────────────────────────────────┐                          │
 │          │ IMDS  169.254.169.254              │  with hop limit 2 the    │
 │          │ /latest/meta-data/iam/             │  response also reaches   │
 │          │   security-credentials/NodeRole    │  the Pod network         │
 │          └─────────────────┬──────────────────┘                          │
 └────────────────────────────┼─────────────────────────────────────────────┘
                              ▼
          All three Pods get the same credentials:
          arn:aws:sts::111122223333:assumed-role/NodeInstanceRole/i-0abc...
          = union of S3 + SQS + ECR + EC2 (ENI) permissions
```

문제는 세 가지입니다.

| 문제 | 결과 |
|---|---|
| 권한 합집합 | 노드에 스케줄될 수 있는 모든 워크로드의 권한을 노드 Role이 갖게 됨 |
| 폭발 반경 | 권한이 전혀 필요 없는 Pod 하나가 침해돼도 노드 Role 전체가 노출됨 |
| 감사 불가 | CloudTrail에는 `NodeInstanceRole/i-0abc...` 만 남아 어느 Pod가 호출했는지 알 수 없음 |

IMDSv2의 PUT 토큰 응답은 IP TTL(`HttpPutResponseHopLimit`)만큼만 이동합니다. Pod가 자체 network namespace에 있으면 노드를 한 번 더 거치므로 hop limit이 **1** 이면 응답이 Pod에 닿지 못하고, **2** 이면 닿습니다. 노드 그룹을 만든 도구와 launch template에 따라 기본값이 다르니 직접 확인합니다.

```bash
aws ec2 describe-instances --filters "Name=tag:eks:cluster-name,Values=$CLUSTER_NAME" \
  --query 'Reservations[].Instances[].[InstanceId,MetadataOptions.HttpTokens,MetadataOptions.HttpPutResponseHopLimit]' \
  --output table
```

## 2. IRSA 동작 원리

IRSA는 **클러스터의 OIDC issuer를 IAM이 신뢰**하게 만드는 방식입니다. Kubernetes가 서명한 ServiceAccount 토큰(JWT)을 STS에 제출하고, STS가 그 서명을 OIDC discovery 문서의 공개키(JWKS)로 검증한 뒤 Role을 넘겨줍니다.

### 2.1 구성 요소

| 구성 요소 | 위치 | 역할 |
|---|---|---|
| OIDC issuer | EKS control plane | SA 토큰 서명, `/.well-known/openid-configuration`·JWKS 공개 |
| IAM OIDC identity provider | 각 AWS 계정 | 그 issuer를 IAM의 federated principal로 등록 |
| IAM Role trust policy | IAM | `sub`(`system:serviceaccount:<ns>:<sa>`)·`aud`(`sts.amazonaws.com`) 조건 |
| SA annotation | Kubernetes | `eks.amazonaws.com/role-arn: <role arn>` |
| Pod Identity Webhook | EKS control plane (mutating webhook) | Pod 생성 시 env·projected token volume 주입 |
| AWS SDK | 컨테이너 | `AssumeRoleWithWebIdentity` 호출과 갱신 |

### 2.2 자격 증명 흐름

```text
 ① kubectl apply (Pod, serviceAccountName: s3-reader)
        │
        ▼
 ┌────────────────────────── EKS Control Plane ──────────────────────────┐
 │  kube-apiserver ──admission──▶ Pod Identity Webhook                   │
 │        │                       SA has role-arn annotation?            │
 │        │                       └─ yes → mutate Pod spec:              │
 │        │                          env  AWS_ROLE_ARN=arn:...:role/X     │
 │        │                          env  AWS_WEB_IDENTITY_TOKEN_FILE=    │
 │        │                               /var/run/secrets/eks.amazonaws.com/serviceaccount/token
 │        │                          vol  projected SA token              │
 │        │                               (audience: sts.amazonaws.com)   │
 │  OIDC issuer  https://oidc.eks.<region>.amazonaws.com/id/<ID>          │
 │     └─ /.well-known/openid-configuration , /keys (JWKS)  ◀────┐        │
 └────────┼──────────────────────────────────────────────────────┼────────┘
          │ ② kubelet requests the token, mounts it, rotates it   │
          ▼                                                      │
 ┌──────── Worker Node ────────┐                                 │
 │ Pod                          │                                │
 │  SDK: token file in env      │                                │
 │  → web identity provider     │                                │
 └──────────────┬───────────────┘                                │
                │ ③ sts:AssumeRoleWithWebIdentity                │
                │    RoleArn=X, WebIdentityToken=<JWT>            │
                ▼                                                 │
 ┌─────────────── AWS STS ─────────────────┐  ④ fetch JWKS to verify signature
 │ - iss matches the account OIDC provider? │──────────────────────┘
 │ - verify JWT signature and expiry        │
 │ - evaluate sub/aud in role X trust policy│
 └──────────────┬──────────────────────────┘
                │ ⑤ temporary credentials (AccessKey/Secret/SessionToken, expiry)
                ▼
            Pod → S3 (CloudTrail: assumed-role/X/<session>)
```

### 2.3 핵심 설정

```json
{
  "Effect": "Allow",
  "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE" },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:demo-irsa:s3-reader",
      "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
    }
  }
}
```

- trust policy에 **클러스터별 OIDC provider ARN이 박힙니다.** 같은 Role을 여러 클러스터에서 쓰려면 statement를 클러스터 수만큼 늘려야 하고, trust policy 크기 한도에 걸립니다.
- 계정마다 OIDC provider를 등록해야 하고, 계정당 OIDC provider 수에도 quota가 있습니다.
- `sub` 조건을 `StringLike`와 `*`로 넓히면 그 클러스터의 다른 ServiceAccount도 Role을 가져갈 수 있습니다. 항상 `StringEquals`로 namespace와 SA를 고정합니다.
- STS 호출은 Pod에서 직접 나가므로 private 클러스터라면 STS VPC endpoint가 필요합니다.

## 3. EKS Pod Identity 동작 원리

Pod Identity는 OIDC 연동을 IAM에서 걷어 내고, **EKS가 "어느 SA가 어떤 Role을 쓰는지"를 직접 관리**합니다. 매핑은 SA annotation이 아니라 EKS API의 **Pod Identity association** 에 저장됩니다. 노드에서는 **Pod Identity Agent** 가 SDK를 대신해 자격 증명을 받아 옵니다.

### 3.1 구성 요소

| 구성 요소 | 위치 | 역할 |
|---|---|---|
| `eks-pod-identity-agent` add-on | 각 노드 DaemonSet, hostNetwork | `169.254.170.23:80`(IPv6 `[fd00:ec2::23]:80`)에서 자격 증명 제공 |
| Pod Identity association | EKS API | (cluster, namespace, serviceaccount) → Role ARN |
| IAM Role trust policy | IAM | `Principal: { Service: pods.eks.amazonaws.com }`, `sts:AssumeRole` + `sts:TagSession` |
| Pod Identity Webhook | EKS control plane | association이 있는 SA의 Pod에 env·projected token 주입 |
| 노드 Role | IAM | Agent가 `eks-auth:AssumeRoleForPodIdentity`를 호출할 권한 (`AmazonEKSWorkerNodePolicy`에 포함) |

### 3.2 자격 증명 흐름

```text
 ⓪ aws eks create-pod-identity-association
       --namespace demo-podid --service-account s3-reader --role-arn arn:...:role/Y
        │  (stored in the EKS API, the SA object is unchanged)
        ▼
 ┌────────────────────────── EKS Control Plane ──────────────────────────┐
 │  kube-apiserver ──admission──▶ Pod Identity Webhook                   │
 │                                association exists?                    │
 │                                └─ yes → mutate Pod spec:              │
 │                                   env AWS_CONTAINER_CREDENTIALS_FULL_URI=
 │                                       http://169.254.170.23/v1/credentials
 │                                   env AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE=
 │                                       /var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token
 │                                   vol projected SA token               │
 │                                       (audience: pods.eks.amazonaws.com)
 └──────────────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌──────────────────────────── Worker Node ──────────────────────────────┐
 │  Pod                                   eks-pod-identity-agent         │
 │  ┌─────────────────────────┐           (hostNetwork DaemonSet)        │
 │  │ SDK: container          │  ①  GET /v1/credentials                  │
 │  │ credential provider     │ ────────────────────────▶ 169.254.170.23 │
 │  │ Authorization: <token>  │                          │               │
 │  └─────────────────────────┘                          │ ② request     │
 │            ▲                                          │   signed with │
 │            │ ④ AccessKey/Secret/SessionToken          │   node role   │
 │            └──────────────────────────────────────────┤               │
 └───────────────────────────────────────────────────────┼───────────────┘
                                                         ▼
 ┌──────────────────── EKS Auth API ─────────────────────────────────────┐
 │ eks-auth:AssumeRoleForPodIdentity(clusterName, token)                 │
 │  - validate SA token → namespace / serviceaccount                     │
 │  - look up association → role Y                                       │
 │  - AssumeRole on role Y + attach session tags ────────────▶ AWS STS    │
 │      eks-cluster-arn, eks-cluster-name, kubernetes-namespace,          │
 │      kubernetes-service-account, kubernetes-pod-name, kubernetes-pod-uid
 └──────────────────────────────────────┬────────────────────────────────┘
                                        │ ③ temporary credentials
                                        ▼
                                  Agent → Pod (④)
```

Pod는 STS에 직접 가지 않습니다. 링크 로컬 주소의 Agent에게 토큰을 보여 주고, Agent가 노드 Role로 EKS Auth API를 호출합니다. 노드 Role은 "중개 권한"만 갖고, 실제 앱 권한은 association에 연결된 Role Y에만 있습니다.

### 3.3 핵심 설정

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "pods.eks.amazonaws.com" },
  "Action": ["sts:AssumeRole", "sts:TagSession"]
}
```

- trust policy에 **클러스터 정보가 없습니다.** 어느 클러스터·어느 SA가 Role을 쓸지는 association이 결정합니다. 같은 Role을 여러 클러스터에서 재사용해도 trust policy는 변하지 않습니다.
- 반대로 "이 Role은 특정 클러스터만 쓸 수 있다"를 IAM에서 강제하려면 trust policy에 `aws:RequestTag/eks-cluster-arn` 등의 조건을 추가하거나, association 생성 권한(`eks:CreatePodIdentityAssociation`, `iam:PassRole`)을 통제합니다.
- **session tags** 로 ABAC를 쓸 수 있습니다. 예를 들어 하나의 Role로 각 namespace가 자기 S3 prefix만 읽게 만들 수 있습니다.

```json
{
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/${aws:PrincipalTag/kubernetes-namespace}/*"
}
```

- 다른 계정 Role은 association의 target role(role chaining) 기능이나 앱 코드에서의 2차 AssumeRole로 처리합니다. 사용 중인 SDK·add-on 버전에서 지원 여부를 확인합니다.
- **SDK 최소 버전** 이 있습니다. `AWS_CONTAINER_CREDENTIALS_FULL_URI` + 토큰 파일을 지원하지 않는 오래된 SDK는 Pod Identity를 건너뛰고 IMDS로 떨어집니다. 이 경우 노드 Role이 사용되므로 마이그레이션 전에 반드시 확인합니다.

## 4. 세 방식 비교

| 항목 | Node instance profile | IRSA | EKS Pod Identity |
|---|---|---|---|
| 권한 단위 | 노드 (모든 Pod 공유) | ServiceAccount | ServiceAccount |
| 매핑 저장 위치 | instance profile | SA annotation + Role trust | EKS API association |
| IAM 신뢰 대상 | `ec2.amazonaws.com` | 클러스터별 OIDC provider | `pods.eks.amazonaws.com` (공통) |
| 계정별 사전 작업 | 없음 | OIDC provider 등록 (클러스터마다) | 없음 (add-on 설치만) |
| 여러 클러스터에서 Role 재사용 | — | trust statement 추가 필요, 크기 한도 | trust 변경 없음, association만 추가 |
| 자격 증명 경로 | Pod → IMDS | Pod → STS (`AssumeRoleWithWebIdentity`) | Pod → Agent → EKS Auth → STS |
| 노드 컴포넌트 | 없음 | 없음 | Pod Identity Agent DaemonSet |
| CloudTrail 주체 | `NodeRole/i-xxx` | `RoleX/<session>` | `RoleY/eks-<cluster>-<pod>-...` + session tags |
| ABAC | 불가 | 제한적 (`sub` 기반) | session tags로 namespace·SA·pod 기반 |
| Fargate | 해당 없음 (Pod execution role) | 지원 | 미지원 |
| EKS 밖 Kubernetes (self-managed, 다른 클라우드) | — | OIDC만 있으면 가능 | EKS 전용 |
| 적합한 경우 | 노드 자체 기능 (kubelet, ECR pull) | Fargate, 비 EKS 클러스터, 기존 IRSA 자산 | 신규 EKS 워크로드, 다수 클러스터·계정 운영 |

선택 기준은 간단합니다. **EKS on EC2에서 새로 붙이는 권한은 Pod Identity를 기본으로**, Fargate나 EKS 밖 클러스터처럼 Pod Identity가 안 되는 곳은 IRSA를 씁니다. 두 방식은 한 클러스터에 공존할 수 있습니다.

### 4.1 둘 다 설정돼 있으면 무엇이 쓰이나

Webhook이 env를 주입한 뒤의 선택은 SDK의 credential chain이 합니다. AWS SDK들의 기본 chain은 대체로 다음 순서입니다.

```text
 1. Static env keys          AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
 2. Shared config/credentials ~/.aws/...  (profile)
 3. Web identity (IRSA)      AWS_WEB_IDENTITY_TOKEN_FILE + AWS_ROLE_ARN
 4. Container credentials    AWS_CONTAINER_CREDENTIALS_FULL_URI (Pod Identity)
 5. IMDS                     169.254.169.254  → node role
```

그래서 annotation과 association을 동시에 두면 **IRSA가 이깁니다.** IRSA → Pod Identity 전환 시 annotation을 제거하고 Pod를 재시작해야 실제로 바뀝니다. 또한 **1번의 정적 키가 Secret으로 주입돼 있으면 둘 다 무시** 되므로 인벤토리 단계에서 함께 찾아냅니다. 언어별 SDK의 정확한 순서는 각 SDK 문서를 확인합니다.

## 5. 실제 배포 비교 데모

같은 워크로드를 세 namespace에 배포하고 SA 연결 방식만 다르게 합니다. `default/neighbor` Pod는 아무 권한도 받지 않은 "이웃 Pod"입니다.

```text
 S3 bucket pod-iam-demo-<acct>-<region>
        ▲             ▲                 ▲                  ▲
        │ NodeRole    │ IRSA role       │ Pod Identity role│ NodeRole (!)
 ┌──────┴─────┐ ┌─────┴──────┐  ┌───────┴──────┐   ┌───────┴───────┐
 │ demo-node  │ │ demo-irsa  │  │ demo-podid   │   │ default/      │
 │ whoami     │ │ whoami     │  │ whoami       │   │ neighbor      │
 │ SA: as-is  │ │ SA+annot.  │  │ SA+assoc.    │   │ no grants     │
 └────────────┘ └────────────┘  └──────────────┘   └───────────────┘
```

```bash
cd examples/security/pod-iam-migration
export CLUSTER_NAME=pod-iam-demo AWS_REGION=ap-northeast-2 NODEGROUP_NAME=ng-default

./01-baseline.sh             # 노드 Role에 S3 읽기 권한 부여 (레거시 상태 재현)
./04-verify.sh               # 모든 Pod가 NodeRole, neighbor도 S3를 읽음
./02-irsa.sh                 # demo-irsa → IRSA
./03-pod-identity.sh         # demo-podid → Pod Identity
./04-verify.sh
./05-lockdown-node-role.sh   # 노드 Role에서 앱 권한 제거 + IMDS hop limit 1
./04-verify.sh
```

단계별 기대 결과입니다. `04-verify.sh`는 각 Pod에서 주입된 env, `sts get-caller-identity`, `s3 ls`, IMDS 도달 여부를 출력합니다.

| Pod | 01 이후 | 02·03 이후 | 05 이후 |
|---|---|---|---|
| `demo-node` | NodeRole, S3 ALLOWED | NodeRole, ALLOWED | 자격 증명 없음, DENIED |
| `demo-irsa` | NodeRole, ALLOWED | `pod-iam-demo-irsa-s3-reader`, ALLOWED | IRSA, ALLOWED |
| `demo-podid` | NodeRole, ALLOWED | `pod-iam-demo-podid-s3-reader`, ALLOWED | Pod Identity, ALLOWED |
| `default/neighbor` | **NodeRole, ALLOWED** | **NodeRole, ALLOWED** | DENIED, IMDS BLOCKED |

`neighbor` 줄이 이 마이그레이션의 핵심입니다. IRSA·Pod Identity를 **추가하는 것만으로는** 노드 Role 노출이 사라지지 않습니다. 5단계의 노드 Role 정리와 IMDS 차단까지 끝나야 효과가 생깁니다.

주입된 env를 직접 확인하는 방법입니다.

```bash
kubectl -n demo-irsa  exec deploy/whoami -- env | grep ^AWS_
# AWS_ROLE_ARN=arn:aws:iam::111122223333:role/pod-iam-demo-irsa-s3-reader
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
# AWS_STS_REGIONAL_ENDPOINTS=regional

kubectl -n demo-podid exec deploy/whoami -- env | grep ^AWS_CONTAINER
# AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials
# AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE=/var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token
```

토큰 내용(JWT payload)을 보면 audience 차이가 드러납니다.

```bash
kubectl -n demo-podid exec deploy/whoami -- sh -c \
  'cut -d. -f2 "$AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE" | tr "_-" "/+" | base64 -d 2>/dev/null; echo'
# {"aud":["pods.eks.amazonaws.com"],"sub":"system:serviceaccount:demo-podid:s3-reader", ...}
# IRSA 토큰은 "aud":["sts.amazonaws.com"]
```

> 이 데모 스크립트는 작성 세션에서 문법 검사만 했고 실제 계정에서 실행하지 않았습니다. 위 출력은 공식 문서의 형식에 따른 기대값이므로 샌드박스 계정에서 먼저 실행해 확인합니다.

## 6. 마이그레이션 runbook

```text
 Phase 0        Phase 1         Phase 2            Phase 3          Phase 4
 Inventory ──▶  Role design ──▶ Switch workload ──▶ Verify, bake ──▶ Lock node role
 (who uses      (least privilege (IRSA or           (CloudTrail      (remove policies,
  the node role)  per workload)   Pod Identity)      principal)       block IMDS)
      ▲                                                               │
      └──────────── new workloads start with the Phase 2 method ◀─────┘
```

### Phase 0. 인벤토리: 노드 Role을 실제로 누가 쓰나

1. **노드 Role 정책 목록**: 기본 정책 외에 붙은 것이 마이그레이션 대상입니다.

   ```bash
   NODE_ROLE=$(aws eks describe-nodegroup --cluster-name $CLUSTER_NAME --nodegroup-name $NG \
     --query nodegroup.nodeRole --output text | awk -F/ '{print $NF}')
   aws iam list-attached-role-policies --role-name $NODE_ROLE
   aws iam list-role-policies --role-name $NODE_ROLE
   ```

   노드 자체에 필요한 것은 `AmazonEKSWorkerNodePolicy`, ECR pull(`AmazonEC2ContainerRegistryPullOnly` 또는 `ReadOnly`), 그리고 VPC CNI가 노드 Role을 쓰는 경우 `AmazonEKS_CNI_Policy`입니다. SSM 접속을 쓰면 `AmazonSSMManagedInstanceCore`도 남깁니다.

2. **실제 호출 확인**: IAM Access Advisor(서비스별 마지막 접근)와 CloudTrail로 노드 Role이 호출하는 API를 봅니다. EC2·ECR·EKS·STS 외의 서비스는 거의 확실히 Pod가 노드 Role을 빌려 쓰는 것입니다. 쿼리 예시는 [`queries/cloudtrail-node-role-usage.sql`](../../examples/security/pod-iam-migration/queries/cloudtrail-node-role-usage.sql)에 있습니다.

3. **호출한 Pod 찾기**: CloudTrail에는 Pod 이름이 없으므로 서비스 이름과 클러스터의 워크로드를 대조합니다. 각 워크로드의 SDK 버전과 정적 키 Secret 사용 여부도 함께 기록합니다.

   ```bash
   # 정적 키를 env로 받는 워크로드
   kubectl get deploy,sts,ds -A -o json | jq -r '.items[] | select(
     [.spec.template.spec.containers[].env[]?.name] | index("AWS_ACCESS_KEY_ID"))
     | "\(.metadata.namespace)/\(.metadata.name)"'
   # 이미 IRSA를 쓰는 SA
   kubectl get sa -A -o json | jq -r '.items[] | select(.metadata.annotations["eks.amazonaws.com/role-arn"])
     | "\(.metadata.namespace)/\(.metadata.name) -> \(.metadata.annotations["eks.amazonaws.com/role-arn"])"'
   ```

4. **hostNetwork Pod 확인**: hostNetwork Pod는 노드와 같은 network namespace라서 hop limit 1로 막히지 않습니다. 이런 Pod는 별도 판단이 필요합니다.

### Phase 1. 워크로드별 Role 설계

- 워크로드(= ServiceAccount)당 Role 하나를 기본으로 합니다. 노드 Role의 정책을 그대로 복사하지 말고, IAM Access Analyzer의 CloudTrail 기반 정책 생성으로 실제 사용한 action만 남깁니다.
- 워크로드마다 **전용 ServiceAccount** 를 만듭니다. `default` SA에 Role을 붙이면 그 namespace의 모든 Pod가 권한을 갖습니다.
- 방식 선택: EC2 노드면 Pod Identity, Fargate·비 EKS면 IRSA. 여러 namespace가 같은 패턴으로 다른 리소스를 쓴다면 Pod Identity session tag ABAC로 Role 수를 줄일 수 있습니다.

### Phase 2-A. IRSA로 전환

```bash
# 1) 클러스터 OIDC provider 등록 (클러스터·계정당 1회)
eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --approve

# 2) Role 생성: trust policy의 sub = system:serviceaccount:<ns>:<sa>
aws iam create-role --role-name app-x --assume-role-policy-document file://irsa-trust.json
aws iam put-role-policy --role-name app-x --policy-name app --policy-document file://app.json

# 3) SA annotation
kubectl -n app annotate sa app-x eks.amazonaws.com/role-arn=arn:aws:iam::<acct>:role/app-x

# 4) 재시작: webhook은 새 Pod만 변경함
kubectl -n app rollout restart deploy/app-x
```

### Phase 2-B. Pod Identity로 전환

```bash
# 1) Agent add-on (클러스터당 1회)
aws eks create-addon --cluster-name $CLUSTER_NAME --addon-name eks-pod-identity-agent

# 2) Role 생성: trust = pods.eks.amazonaws.com
aws iam create-role --role-name app-x --assume-role-policy-document file://podid-trust.json
aws iam put-role-policy --role-name app-x --policy-name app --policy-document file://app.json

# 3) association
aws eks create-pod-identity-association --cluster-name $CLUSTER_NAME \
  --namespace app --service-account app-x --role-arn arn:aws:iam::<acct>:role/app-x

# 4) 재시작
kubectl -n app rollout restart deploy/app-x
```

Terraform이나 eksctl을 쓰면 `aws_eks_pod_identity_association` 리소스, eksctl `iam.podIdentityAssociations`로 같은 일을 선언적으로 관리합니다. AWS 관리형 add-on(VPC CNI, EBS CSI 등)은 add-on 설정의 pod identity association으로 연결할 수 있습니다.

Phase 2의 원칙은 **새 경로가 동작한 뒤에 옛 경로를 지운다** 입니다. 워크로드를 전환하는 동안 노드 Role의 권한은 그대로 두므로, 새 Role의 권한이 부족해도 장애가 나지 않습니다. 대신 앱이 실제로 새 Role을 쓰는지 Phase 3에서 반드시 확인합니다.

### Phase 3. 검증과 bake

| 확인 | 방법 | 기대값 |
|---|---|---|
| 주입 | `kubectl exec ... env \| grep ^AWS_` | IRSA: `AWS_WEB_IDENTITY_TOKEN_FILE`, Pod Identity: `AWS_CONTAINER_CREDENTIALS_FULL_URI` |
| 실제 주체 | `aws sts get-caller-identity` (또는 앱 로그) | 새 Role ARN |
| 감사 | CloudTrail에서 해당 서비스 호출의 `userIdentity.arn` | 노드 Role 호출이 0으로 수렴 |
| 오류 | 앱 로그의 `AccessDenied` | 없음 (있으면 새 Role 권한 보강) |

SDK가 오래돼 Pod Identity를 인식하지 못하면 env가 주입돼도 **조용히 IMDS로 떨어져 노드 Role을 씁니다.** "env가 보인다"가 아니라 "CloudTrail 주체가 바뀌었다"로 판단합니다.

### Phase 4. 노드 Role 잠금

모든 워크로드의 CloudTrail 주체가 바뀐 것을 확인한 뒤에 진행합니다.

1. 노드 Role에서 앱 정책을 제거합니다. 노드 기본 정책만 남깁니다.
2. IMDS를 Pod에서 막습니다.
   - launch template: `HttpTokens=required`, `HttpPutResponseHopLimit=1` 후 노드 그룹 롤링
   - eksctl: `disableIMDSv1: true`, `disablePodIMDS: true`
   - 추가로 NetworkPolicy로 `169.254.169.254/32` egress 차단 (hostNetwork Pod에는 적용 안 됨)
3. VPC CNI(`aws-node`)도 IRSA나 Pod Identity로 옮기면 노드 Role에서 `AmazonEKS_CNI_Policy`까지 뺄 수 있습니다.
4. 이후 새 워크로드가 노드 Role에 권한을 다시 붙이지 못하게 IAM 변경 권한과 IaC 리뷰로 통제합니다.

IMDS를 막으면 메타데이터로 **region·VPC ID를 자동 탐지** 하던 컨트롤러가 실패할 수 있습니다. 예를 들어 AWS Load Balancer Controller는 `--aws-region`, `--aws-vpc-id`를 명시해야 합니다. Phase 0에서 IMDS에 의존하는 Pod를 함께 찾아 둡니다.

### 롤백

| 단계 | 롤백 |
|---|---|
| Phase 2 | annotation 제거 또는 association 삭제 → 재시작. 노드 Role 권한이 아직 있으므로 즉시 복구 |
| Phase 4 정책 제거 | 노드 Role에 정책 재부착 (IAM 전파 지연 고려) |
| Phase 4 IMDS | launch template 이전 버전으로 노드 그룹 롤백 또는 `modify-instance-metadata-options` |

## 7. IRSA에서 Pod Identity로 옮기기

이미 IRSA를 쓰는 워크로드도 같은 원칙으로 무중단 전환합니다.

```text
 t0  IRSA only       trust: [OIDC]                SA: annotation      Pod env: WEB_IDENTITY
 t1  dual trust      trust: [OIDC, pods.eks]      SA: annotation      (no change)
 t2  association     + create-pod-identity-association                (no change: IRSA wins)
 t3  remove annot.   + rollout restart                                Pod env: CONTAINER_CREDENTIALS
 t4  after bake      trust: [pods.eks]  delete OIDC statement, clean up unused OIDC provider
```

t2에서는 association을 만들어도 annotation이 남아 있어 SDK가 계속 IRSA를 쓰므로, t3의 annotation 제거와 재시작이 실제 전환 시점입니다. 데모의 `06-irsa-to-pod-identity.sh`가 이 순서를 그대로 수행합니다.

## 8. 체크리스트

- [ ] 노드 Role에 붙은 앱 정책과 실제 호출 서비스를 CloudTrail로 목록화했다
- [ ] 정적 키 Secret·기존 IRSA SA·hostNetwork Pod를 따로 표시했다
- [ ] 워크로드별 전용 ServiceAccount와 최소 권한 Role을 만들었다
- [ ] SDK 버전이 선택한 방식(web identity / container credentials)을 지원한다
- [ ] 전환 후 CloudTrail 주체가 새 Role로 바뀐 것을 확인했다
- [ ] 노드 Role을 기본 정책만 남기고 정리했다
- [ ] IMDSv2 required + hop limit 1을 launch template에 반영하고 노드를 롤링했다
- [ ] IMDS 의존 컨트롤러에 region·VPC ID를 명시했다
- [ ] 노드 Role 권한 추가를 막는 IAM·IaC 리뷰 규칙을 만들었다

## 참고 자료

- [Amazon EKS: IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Amazon EKS: Learn how EKS Pod Identity grants pods access to AWS services](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Amazon EKS: Understand how EKS Pod Identity works](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [Amazon EKS: Set up the EKS Pod Identity Agent](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-agent-setup.html)
- [Amazon EKS: Use pod identity with the AWS SDK (minimum SDK versions)](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
- [Amazon EKS: Grant pods access to AWS resources based on tags](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-abac.html)
- [EKS Best Practices Guide: Identity and Access Management](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)
- [Amazon EC2: Configure the instance metadata options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html)
- [AWS SDKs and Tools: Standardized credential providers](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
- 관련 장: [EKS 보안 모범 사례](./06-eks-security-best-practices.md), [Kubernetes 인증 및 권한 부여](./02-kubernetes-auth-authz.md)
