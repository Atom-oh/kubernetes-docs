# EKS 워크로드 IAM 이전 실습: 노드 역할에서 IRSA와 Pod Identity로

> **난이도**: 고급
> **예상 소요 시간**: 40–60분 (`harden`까지 하면 30분 정도 더 걸림)
> **지원 버전**: Amazon EKS 1.36에서 검증, AWS CLI 2.35.11 (Pod 안)
> **마지막 업데이트**: 2026년 11월 21일

## 학습 목표

- 같은 orders 앱 세 벌이 모두 노드 IAM 역할을 쓰는 상태에서 출발해, 한 벌은 IRSA로, 다른 한 벌은 EKS Pod Identity로 옮깁니다.
- 웹훅이 새 Pod에 넣는 환경 변수, 토큰, 역할 신뢰 정책이 두 방식에서 어떻게 다른지 직접 확인합니다.
- 노드 역할에서 S3 권한을 회수하면 이전하지 않은 Pod만 거부되는 것을 보고, IAM과 association의 eventual consistency를 관찰합니다.
- (선택) IMDS hop limit을 1로 내려 일반 Pod의 노드 자격 증명 경로를 닫습니다.
- 한 ServiceAccount에 IRSA 주석과 Pod Identity association이 함께 있을 때 새 Pod에 무엇이 주입되는지 server-side dry run으로 확인합니다.

이 실습은 [EKS 노드 IAM 권한을 IRSA와 Pod Identity로 이전하기](../../security/17-eks-workload-identity-migration.md)의 [라이브 데모](../../security/17-eks-workload-identity-migration.md#live-demo)를 한 단계씩 따라 하는 가이드입니다. 동작 원리는 워크북의 [IRSA 동작 원리](../../security/17-eks-workload-identity-migration.md#irsa-flow)와 [Pod Identity 동작 원리](../../security/17-eks-workload-identity-migration.md#pod-identity-flow)를 먼저 읽으세요.

## 소요 시간과 비용

| 단계 | 실측 시간 | 비고 |
| --- | --- | --- |
| `up` | 174초 (run `t1121`) | 노드 그룹 생성이 대부분. 환경에 따라 3–5분 |
| `migrate-irsa` | 6초 | |
| `migrate-podid` | 11초 | association이 주입에 반영되기까지 5초 포함 |
| `diff` | 8초 | 읽기 전용 |
| `revoke` | 처음 `denied`까지 13초 | 명령은 17–18초 뒤 끝남 |
| `harden` (선택) | 878초 | 노드 그룹 롤링 교체 |
| `restore` | 15초, `harden` 뒤에는 578초 | 반복 실습용 |
| `down` | 323초 (run `t1121`) | 노드 그룹 삭제가 대부분 |

비용은 t3.medium On-Demand 인스턴스 한 대(서울 리전 시간당 US$0.052)와 20 GiB gp3 볼륨이 대부분입니다. 한 시간 실습하면 US$0.06 안팎이고, S3 요청과 API 호출 비용은 무시할 만합니다. 선택 단계인 공개 데모 페이지를 띄우면 ALB 비용이 하루 약 US$0.55 더 듭니다. 실습이 끝나면 반드시 `down`으로 정리합니다.

## 사전 요구 사항

- [ ] **기존 EKS 클러스터** (1.36에서 검증). 기본 데모는 클러스터, VPC, 서브넷, 보안 그룹을 만들지 않습니다(선택 단계인 `page-up`만 internal ALB용 보안 그룹 하나와 `PAGE_DOMAIN` DNS 레코드를 만듭니다). 클러스터의 vpc-cni가 노드 역할로 동작하는 일반적인 구성을 가정합니다.
- [ ] **`eks-pod-identity-agent` 애드온**이 설치되어 있어야 합니다. 스크립트는 설치하지 않고 확인만 합니다.
- [ ] 클러스터 issuer가 **IAM OIDC provider**로 등록되어 있어야 합니다. 이것도 스크립트가 만들지 않습니다.
- [ ] 클러스터 VPC 안의 **Private 서브넷**과 그 Name 태그. `MapPublicIpOnLaunch=false`인 서브넷만 받아들이며, 노드는 VPC의 기존 NAT 경로로 `public.ecr.aws/aws-cli/aws-cli` 이미지를 받습니다.
- [ ] 도구: AWS CLI v2, kubectl, jq, bash, git.
- [ ] 권한: EKS, EC2(launch template), IAM, S3 권한이 있는 자격 증명과 클러스터 cluster-admin 접근. 장기 액세스 키 대신 임시 자격 증명을 쓰세요.

### 사전 확인 명령

```bash
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER> VPC_NAME=<클러스터 VPC의 Name 태그> \
  SUBNET_NAMES=<Private 서브넷 Name 태그 1>,<Private 서브넷 Name 태그 2>

aws sts get-caller-identity --query Arn --output text
aws eks describe-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent \
  --query addon.status --output text                       # ACTIVE
ISSUER=$(aws eks describe-cluster --name "$CLUSTER" \
  --query cluster.identity.oidc.issuer --output text | sed 's#^https://##')
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam get-open-id-connect-provider --open-id-connect-provider-arn \
  "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${ISSUER}" --query ClientIDList   # ["sts.amazonaws.com"]
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$VPC_NAME" \
  --query 'Vpcs[0].VpcId' --output text)
aws eks describe-cluster --name "$CLUSTER" --query cluster.resourcesVpcConfig.vpcId --output text  # $VPC_ID와 같아야 함
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$SUBNET_NAMES" \
  --query 'Subnets[].[Tags[?Key==`Name`]|[0].Value,SubnetId,MapPublicIpOnLaunch]' --output table
```

확인 포인트는 애드온 `ACTIVE`, OIDC provider 조회 성공, 클러스터 VPC ID와 `VPC_NAME`으로 찾은 VPC ID 일치, 서브넷마다 `MapPublicIpOnLaunch`가 `False`인 것입니다. 하나라도 어긋나면 `up`이 리소스를 만들기 전에 멈춥니다.

### 코드와 환경 파일

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs/examples/security/eks-workload-identity

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/eks-workload-identity-demo"
mkdir -p "$STATE_DIR"
cat > "$STATE_DIR/env" <<'EOF'
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER>
export VPC_NAME=<클러스터 VPC의 Name 태그>
export SUBNET_NAMES=<Private 서브넷 Name 태그 1>,<Private 서브넷 Name 태그 2>
EOF

export RUN_ID=lab01     # 소문자·숫자 4–12자. 리소스 이름 wid-<RUN_ID>-* 에 들어감
export NS="wid-$RUN_ID"
export KUBECONFIG="$STATE_DIR/kubeconfig-$RUN_ID"   # demo.sh가 만드는 전용 kubeconfig
```

`demo.sh`는 실행할 때마다 이 env 파일을 읽으므로, 두 번째 터미널의 `watch`도 같은 값을 씁니다. env 파일은 셸 변수보다 나중에 읽혀서 같은 이름이면 파일 값이 이깁니다. 아래에서 `kubectl`을 직접 실행할 때는 위의 `KUBECONFIG`를 쓰세요. 다른 클러스터 컨텍스트에 명령이 가지 않게 하기 위해서입니다. 이 파일은 `up`을 처음 실행할 때 생깁니다.

스크립트가 화면에 출력하는 명령과 결과는 계정 ID, OIDC issuer ID, 클러스터 이름, launch template ID를 `<ACCOUNT_ID>`, `<OIDC_ID>`, `<CLUSTER>`, `<LAUNCH_TEMPLATE_ID>`로 가립니다. 아래 예상 출력도 같은 방식으로 가렸습니다. 실측 출력은 2026년 11월 21일 서울 리전 리허설 기록이고, run ID(`d1124` 또는 `t1121`)를 블록마다 밝혔습니다. 여러분의 화면에는 `RUN_ID`와 시각이 다르게 나옵니다.

## 단계 0: 실습 환경 배포 (`up`)

**명령** (터미널 A)

```bash
./demo.sh up "$RUN_ID"
```

**예상 출력** (실측, run `t1121`, 174초)

```text
==> bucket and test object
==> node role (with the app's S3 permission, the legacy pattern)
==> IRSA and Pod Identity roles
==> creating node group wid-t1121 (3–5 min)
==> namespace, ServiceAccounts and three copies of the orders app
Waiting for deployment "orders-legacy" rollout to finish: 0 of 1 updated replicas are available...
deployment "orders-legacy" successfully rolled out
deployment "orders-irsa" successfully rolled out
deployment "orders-podid" successfully rolled out
==> ready. In a second terminal run: ./demo.sh watch t1121
```

**확인 포인트**

```bash
./demo.sh status "$RUN_ID"
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `status`에서 노드 그룹이 `ACTIVE t3.medium lt-version=1`, 세 역할(`wid-<RUN_ID>-node`, `-irsa`, `-podid`)에 인라인 정책 `OrdersReadInvoices`, 버킷 `present`, `pod-id 0 association(s)`, `irsa SA (not annotated)`, Pod 세 개 `Running`이 보여야 합니다.
- launch template의 `MetadataOptions`는 `HttpTokens: required`, `HttpPutResponseHopLimit: 2`, `HttpEndpoint: enabled`입니다.

**왜 그렇게 되나.** `up`은 운영 노드 그룹과 같은 출발점을 만듭니다. IMDSv2는 필수지만 hop limit이 2라서 hostNetwork를 쓰지 않는 일반 Pod도 IMDS 토큰을 받아 노드 역할 자격 증명을 가져갈 수 있고, 그 노드 역할에 앱의 `s3:GetObject`가 붙어 있습니다. IRSA 역할과 Pod Identity 역할도 미리 만들지만, 아직 어떤 ServiceAccount에도 연결하지 않았습니다.

## 단계 1: 시작 상태 확인 (`watch`)

**명령** (터미널 B, 같은 디렉터리)

```bash
export RUN_ID=lab01
./demo.sh watch "$RUN_ID"     # 2초마다 갱신, Ctrl-C로 종료
```

**예상 화면** (실측, run `d1124`)

```text
04:11:37 EKS workload identity — <CLUSTER>/wid-d1124  (Ctrl-C to stop)

COPY            CREDENTIALS    ROLE                           S3        AT
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36
orders-irsa     node (IMDS)    wid-d1124-node  ← node       allowed   04:11:35
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36

node role: wid-d1124-node   bucket object: invoices/2026-11.txt
```

**확인 포인트.** 세 줄 모두 `node (IMDS)`, `wid-<RUN_ID>-node ← node`, `allowed`이고 `AT` 시각이 3초 간격으로 바뀝니다. 화면은 각 복사본의 최신 Pod 로그 한 줄을 읽어 그립니다. 원본 JSON은 터미널 A에서 직접 볼 수 있습니다.

```bash
kubectl -n "$NS" logs deploy/orders-legacy --tail=3
# 형식: {"t":"HH:MM:SS","src":"imds","role":"wid-<RUN_ID>-node","s3":"allowed"}
```

**왜 그렇게 되나.** 세 Pod 모두 주입된 자격 증명 환경 변수가 없으므로, AWS CLI의 기본 공급자 체인이 마지막 단계인 IMDS까지 내려가 노드 역할을 받습니다. `app.sh`는 `AWS_WEB_IDENTITY_TOKEN_FILE`이나 `AWS_CONTAINER_CREDENTIALS_FULL_URI`가 있는지로 `src`를 정하고, `sts get-caller-identity`의 ARN에서 역할 이름을 뽑습니다. 토큰이나 키는 출력하지 않습니다.

## 단계 2: IRSA로 이전 (`migrate-irsa`)

**명령** (터미널 A)

```bash
./demo.sh migrate-irsa "$RUN_ID"
```

**예상 출력** (실측, run `t1121`, 6초)

```text
==> IRSA: point the ServiceAccount at its own role, then restart the copy
$ kubectl -n wid-t1121 annotate serviceaccount orders-irsa --overwrite eks.amazonaws.com/role-arn=arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-irsa
$ kubectl -n wid-t1121 rollout restart deployment/orders-irsa
$ kubectl -n wid-t1121 rollout status deployment/orders-irsa --timeout=180s
Waiting for deployment "orders-irsa" rollout to finish: 1 old replicas are pending termination...
deployment "orders-irsa" successfully rolled out
```

터미널 B의 `orders-irsa` 줄은 `IRSA (STS)`, `wid-<RUN_ID>-irsa`, `allowed`로 바뀌고 나머지 두 줄은 그대로입니다 (실측, run `d1124`).

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:59
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:01
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:12:00
```

**직접 확인.** 무엇이 바뀌었는지 Kubernetes 객체에서 봅니다.

```bash
# 1) ServiceAccount 주석
kubectl -n "$NS" get sa orders-irsa \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# 2) 새 Pod에 웹훅이 넣은 환경 변수 이름 (값은 출력하지 않음)
POD=$(kubectl -n "$NS" get pod -l app=orders,track=irsa \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'

# 3) projected 토큰 마운트 경로
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].volumeMounts[*]}{.mountPath}{"\n"}{end}'
```

**확인 포인트**

- 주석 값이 `arn:aws:iam::<ACCOUNT_ID>:role/wid-<RUN_ID>-irsa`입니다.
- 환경 변수 목록에 매니페스트의 `BUCKET`, `KEY`, `AWS_REGION` 등과 함께 웹훅이 넣은 `AWS_STS_REGIONAL_ENDPOINTS`, `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`이 보입니다.
- 마운트 경로에 `/var/run/secrets/eks.amazonaws.com/serviceaccount`가 추가되어 있습니다.
- `orders-legacy`와 `orders-podid` Pod에는 이 변수가 없습니다.

**왜 그렇게 되나.** EKS의 mutating 웹훅은 Pod가 **생성될 때** ServiceAccount의 `eks.amazonaws.com/role-arn` 주석을 보고 변수와 토큰 볼륨을 넣습니다. 이미 실행 중인 Pod는 바뀌지 않으므로 스크립트가 주석 직후 `rollout restart`를 합니다. 새 Pod의 AWS CLI는 체인에서 IMDS보다 앞에 있는 웹 ID 토큰 공급자를 먼저 찾아 STS `AssumeRoleWithWebIdentity`로 IRSA 역할을 받습니다.

## 단계 3: Pod Identity로 이전 (`migrate-podid`)

**명령** (터미널 A)

```bash
./demo.sh migrate-podid "$RUN_ID"
```

**예상 출력** (실측, run `t1121`, 11초)

```text
==> Pod Identity: associate the ServiceAccount with its role in the EKS API, then restart
$ aws eks create-pod-identity-association --cluster-name <CLUSTER> --namespace wid-t1121 --service-account orders-podid --role-arn arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-podid --tags Lab=eks-workload-identity-demo\,LabRun=t1121 --query association.associationId --output text
==> waiting for the association change to reach Pod admission (eventually consistent)
    2s  not yet   injected after 5s
$ kubectl -n wid-t1121 rollout restart deployment/orders-podid
$ kubectl -n wid-t1121 rollout status deployment/orders-podid --timeout=180s
Waiting for deployment "orders-podid" rollout to finish: 1 old replicas are pending termination...
deployment "orders-podid" successfully rolled out
```

터미널 B의 `orders-podid` 줄이 `Pod Identity`, `wid-<RUN_ID>-podid`, `allowed`로 바뀝니다 (실측, run `d1124`).

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:12:27
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:29
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:27
```

**직접 확인**

```bash
# association은 EKS API에 있고 ServiceAccount에는 주석이 없음
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "$NS" \
  --query 'associations[].[serviceAccount,associationId]' --output text
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'

POD=$(kubectl -n "$NS" get pod -l app=orders,track=podid \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'
```

**확인 포인트**

- association이 `orders-podid` 하나 있고, ServiceAccount 주석은 비어 있습니다.
- 새 Pod에 `AWS_STS_REGIONAL_ENDPOINTS`, `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`이 있습니다.
- 출력의 `injected after Ns`가 association 생성부터 주입이 보이기까지 걸린 시간입니다. 실측은 두 리허설 모두 5초였습니다.

**왜 주입을 기다리나.** association은 eventual consistency로 반영됩니다. 첫 리허설에서 association을 만든 직후 rollout하자 새 Pod에 Pod Identity 변수가 들어가지 않았고, 그 Pod는 계속 노드 역할을 썼습니다. 그래서 스크립트는 Deployment의 Pod 템플릿을 `kubectl create --dry-run=server`로 보내 mutating 웹훅이 실제로 변수를 넣는 것을 확인한 다음에 rollout합니다. server-side dry run은 객체를 저장하지 않지만 실제 Pod와 같은 admission 단계를 거치므로 이 확인에 맞습니다.

## 단계 4: 두 방식 비교 (`diff`)

**명령**

```bash
./demo.sh diff "$RUN_ID"
```

**예상 출력** (실측, run `t1121`)

```text
1. What EKS injected into each new Pod (env var names)
  irsa   AWS_STS_REGIONAL_ENDPOINTS, AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
  podid  AWS_STS_REGIONAL_ENDPOINTS, AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE

2. The projected ServiceAccount token (claims only)
  irsa   {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["sts.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-irsa","lifetime_s":86400}
  podid  {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["pods.eks.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-podid","lifetime_s":79636}

3. Who each role trusts
  irsa             {"principal":{"Federated":"arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>"},"action":"sts:AssumeRoleWithWebIdentity","conditions":["<issuer>:aud","<issuer>:sub"]}
  podid            {"principal":{"Service":"pods.eks.amazonaws.com"},"action":["sts:AssumeRole","sts:TagSession"],"conditions":["aws:RequestTag/eks-cluster-arn","aws:RequestTag/kubernetes-namespace","aws:RequestTag/kubernetes-service-account"]}

4. Where the SDK goes for credentials
  irsa   Pod → STS AssumeRoleWithWebIdentity (regional endpoint) → temporary credentials
  podid  Pod → Pod Identity Agent 169.254.170.23 on the node → EKS Auth AssumeRoleForPodIdentity → credentials
  legacy Pod → IMDSv2 169.254.169.254 → node role credentials

5. Wiring lives in
  irsa   ServiceAccount annotation + IAM OIDC provider + per-role trust on issuer/sub
  podid  EKS association (1 found) + one service principal trust, reusable across clusters
```

**출력 해석**

- **1번**: 두 방식 모두 새 Pod에 변수를 넣지만 이름이 다릅니다. IRSA는 역할 ARN과 토큰 파일을 주고 SDK가 STS를 직접 부르게 합니다. Pod Identity는 역할 ARN 없이 자격 증명 URI와 인증 토큰 파일만 줍니다. 어떤 역할을 받을지는 association이 정합니다.
- **2번**: 두 토큰 모두 같은 클러스터 issuer가 서명한 ServiceAccount 토큰이고 `sub`도 같은 형식입니다. 차이는 `aud`입니다. `sts.amazonaws.com` 토큰은 STS만, `pods.eks.amazonaws.com` 토큰은 EKS Auth만 받습니다. Pod Identity 토큰 수명은 웹훅이 무작위 편차를 줘서 실행마다 다릅니다 (실측 79,636초와 86,171초).
- **3번**: IRSA 역할은 클러스터별 OIDC provider와 `aud`·`sub` 조건을 신뢰하므로 클러스터가 늘면 신뢰 정책 문장도 늘어납니다. Pod Identity 역할은 서비스 principal 하나와 세션 태그 조건만 있어서 다른 클러스터에서도 신뢰 정책을 고치지 않습니다.
- **4–5번**은 스크립트가 고정 문구로 출력하는 요약입니다. 5번의 `1 found`만 실제 association 수입니다.

**왜 그렇게 되나.** 두 방식의 차이는 "누가 토큰을 받아 역할로 바꿔 주는가"입니다. IRSA는 Pod가 STS에 직접 가고 STS가 OIDC provider로 서명을 검증합니다. Pod Identity는 같은 노드의 Agent가 EKS Auth에 묻고 EKS Auth가 association을 찾아 세션 태그가 붙은 자격 증명을 돌려줍니다.

## 단계 5: 노드 역할 권한 회수 (`revoke`)

**명령**

```bash
./demo.sh revoke "$RUN_ID"
```

**예상 출력** (실측, run `t1121`, 처음 `denied`까지 13초)

```text
==> remove the app's S3 permission from the node role
$ aws iam delete-role-policy --role-name wid-t1121-node --policy-name OrdersReadInvoices
==> waiting for IAM to propagate: legacy copy should flip to denied
    1s  legacy still: allowed     5s  legacy still: allowed     9s  legacy still: allowed   legacy denied after 13s
  orders-irsa   allowed via wid-t1121-irsa
  orders-podid  allowed via wid-t1121-podid
```

터미널 B (실측, run `d1124`, `revoke` 직후와 60초 뒤 모두 같은 결과):

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       denied    04:12:56
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:58
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:58
```

**확인 포인트**

- `orders-legacy`만 `denied`가 되고, 역할은 여전히 노드 역할입니다. 자격 증명은 받지만 그 역할에 권한이 없다는 뜻입니다.
- IRSA와 Pod Identity 복사본은 계속 `allowed`입니다. 노드 역할의 업무 권한에 의존하지 않는다는 증거입니다.
- 회수 뒤 몇 분 동안 늦게 나온 `allowed`가 있는지 로그로 확인합니다.

```bash
kubectl -n "$NS" logs deploy/orders-legacy --since=10m | jq -r 'select(.s3=="allowed") | .t' | tail -n 3
```

**왜 그렇게 되나.** IAM 정책 변경도 eventual consistency로 전파됩니다. 리허설 두 번 모두 13초 만에 처음 거부됐지만, 첫 리허설에서는 약 4분 30초 뒤에 `allowed`가 두 번 더 나왔습니다. `revoke`는 첫 `denied`에서 끝나므로, 운영에서 노드 정책을 회수한 뒤에는 수 분 이상 관찰하고 판단합니다.

## 단계 6 (선택): IMDS 경로 닫기 (`harden`)

약 15분(실측 878초) 걸리므로 `revoke` 직후에 시작해 두고 단계 7을 진행해도 됩니다.

**명령**

```bash
./demo.sh harden "$RUN_ID"
./demo.sh status "$RUN_ID"      # 다른 터미널에서: nodegroup UPDATING → ACTIVE
```

**예상 출력** (실측, run `d1124`, 878초). 스크립트가 새 launch template 버전으로 노드 그룹을 갱신하고, 끝날 때까지 15초마다 점을 찍습니다.

```text
==> block Pod access to IMDS on the demo node group (hop limit 1)
$ aws eks update-nodegroup-version --cluster-name <CLUSTER> --nodegroup-name wid-d1124 --launch-template id=<LAUNCH_TEMPLATE_ID>\,version=2 --query update.id --output text
...
deployment "orders-legacy" successfully rolled out
==> legacy copy now has no credentials at all; IRSA and Pod Identity are unaffected
```

교체가 끝난 뒤 각 복사본의 마지막 로그 (실측, run `d1124`):

```text
legacy: {"t":"04:00:27","src":"imds","role":"no-credentials","s3":"no-creds"}
irsa: {"t":"04:00:26","src":"irsa","role":"wid-d1124-irsa","s3":"allowed"}
podid: {"t":"04:00:27","src":"pod-identity","role":"wid-d1124-podid","s3":"allowed"}
```

**확인 포인트**

```bash
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `HttpPutResponseHopLimit`이 `1`, `HttpEndpoint`는 여전히 `enabled`입니다.
- `orders-legacy`는 자격 증명 자체를 받지 못해 `no-credentials` / `no-creds`가 되고, 나머지 두 복사본은 새 노드에서도 `allowed`입니다.

**왜 그렇게 되나.** hop limit 1이면 IMDSv2 토큰 응답이 노드의 네트워크 네임스페이스를 넘어 Pod까지 가지 못하므로, 일반 Pod는 노드 역할 자격 증명을 받을 수 없습니다. **IMDS 자체를 끄면(`HttpEndpoint=disabled`) 안 됩니다.** Pod Identity Agent는 hostNetwork에서 IMDS로 노드 역할 자격 증명을 받아 EKS Auth를 호출하기 때문에, IMDS를 끄면 `orders-podid`도 자격 증명을 잃습니다. hostNetwork Pod는 hop limit과 관계없이 IMDS에 닿으므로 별도로 통제해야 합니다.

`harden` 뒤에 `restore`나 `down`을 하려면 노드 그룹이 다시 `ACTIVE`가 될 때까지 기다립니다. `harden` 뒤의 `restore`는 hop limit 2로 다시 롤링하므로 약 10분(실측 578초) 걸립니다.

## 단계 7: 직접 실험 — IRSA 주석과 association이 함께 있을 때

워크북은 같은 ServiceAccount에 IRSA 주석과 association이 모두 있으면 EKS 웹훅이 새 Pod에 Pod Identity 변수만 넣는다고 설명합니다. 단계 3까지 마친 상태에서 직접 확인합니다. `orders-irsa`에는 association을 만들지 마세요. 스크립트의 `restore`와 `down`은 `orders-podid`의 association만 지우므로 정리되지 않은 association이 남습니다. 대신 association이 이미 있는 `orders-podid`에 IRSA 주석을 잠시 붙입니다.

**7.1 주입 결과를 보는 함수** — `demo.sh`의 `podid_injected()`와 같은 방식으로 Deployment의 Pod 템플릿을 server-side dry run으로 보냅니다.

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

injected() { # deployment 이름
  kubectl -n "$NS" get deployment "$1" -o json |
    jq --arg n "probe-$RUN_ID" '{apiVersion:"v1",kind:"Pod",metadata:{name:$n},spec:.spec.template.spec}' |
    kubectl -n "$NS" create --dry-run=server -o json -f - |
    jq -r '[.spec.containers[0].env[]?.name
            | select(test("^AWS_(ROLE_ARN|WEB_IDENTITY_TOKEN_FILE|CONTAINER_)"))] | join(", ")'
}
```

**7.2 기준선: 주석만 있는 ServiceAccount와 association만 있는 ServiceAccount**

```bash
injected orders-irsa     # 예상 (diff 출력과 coexistence.log 기준): AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
injected orders-podid    # 예상 (diff 출력과 coexistence.log 기준): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.3 association이 있는 `orders-podid`에 IRSA 주석을 더한 뒤 다시 dry run**

```bash
kubectl -n "$NS" annotate sa orders-podid \
  "eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/wid-${RUN_ID}-irsa"
injected orders-podid    # 예상 (diff 출력과 coexistence.log 기준): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.4 정리: 주석을 지우고 rollout은 하지 않습니다**

```bash
kubectl -n "$NS" annotate sa orders-podid eks.amazonaws.com/role-arn-
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'   # 비어 있어야 함
```

**확인 포인트.** 7.3에서 `AWS_ROLE_ARN`이 나오지 않고 Pod Identity 변수만 나오면 워크북의 설명과 같습니다. 2026년 11월 21일 run `d1124`에서 측정한 결과는 주석만 있을 때 `AWS_ROLE_ARN`·`AWS_WEB_IDENTITY_TOKEN_FILE`, association을 더하고 5초 뒤부터 `AWS_CONTAINER_CREDENTIALS_FULL_URI`·`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`만, 둘 다 지우고 2초 뒤에는 아무것도 주입되지 않았습니다. dry run은 Pod를 만들지 않으므로 실행 중인 `orders-podid`에는 영향이 없습니다.

**왜 그렇게 되나.** EKS의 웹훅은 association이 있는 ServiceAccount라면 IRSA 주석이 있어도 Pod Identity 변수를 우선하고 IRSA 변수는 넣지 않습니다. 반대로 association을 나중에 추가해도 **이미 실행 중인** Pod는 다시 만들기 전까지 IRSA 변수를 그대로 갖고 있습니다. 그래서 방식을 바꿀 때는 rollout으로 Pod를 새로 만들고, 쓰지 않는 주석은 지워 두 설정이 섞이지 않게 합니다.

## 공개 데모 페이지 (선택)

청중이 각자 브라우저로 볼 수 있는 읽기 전용 실시간 페이지를 띄웁니다. 카드 세 장이 각 복사본의 자격 증명 출처, 역할, S3 결과, EKS가 주입한 `AWS_*` 변수 이름, 최근 읽기 기록을 보여 주며 바꾸는 기능은 없습니다. **URL을 아는 사람은 누구나 볼 수 있으므로** 역할 이름 외의 정보는 내보내지 않습니다.

경로는 CloudFront(HTTPS, GET/HEAD만, HTTP는 HTTPS로 리다이렉트) → CloudFront VPC origin → **internal** ALB(HTTP 80) → 대시보드 Pod입니다. ALB 보안 그룹은 VPC의 `CloudFront-VPCOrigins-Service-SG`만 받아들이고, 그 보안 그룹이 아직 없으면 CloudFront managed prefix list(`com.amazonaws.global.cloudfront.origin-facing`)로 제한합니다. 인터넷에 직접 열린 로드 밸런서나 공인 IP, 공인 CIDR 규칙은 만들지 않습니다. 대시보드 Pod에는 IAM 역할이 없고, Role은 이 namespace의 Pod 목록과 로그 읽기만 허용합니다. 데모 노드는 hop limit 2라서 NetworkPolicy로 Pod의 egress를 DNS와 TCP 443(Kubernetes API)으로 제한해 IMDS와 Pod Identity Agent에 닿지 못하게 합니다.

**추가 사전 요구 사항**: AWS Load Balancer Controller, VPC CNI 네트워크 정책 활성화(`enableNetworkPolicy`), CloudFront VPC origin을 지원하는 최신 AWS CLI v2, CloudFront·ELB·Route 53·ACM 읽기 권한. env 파일에 다음 세 값을 추가합니다.

```bash
export PAGE_DOMAIN=<페이지 호스트 이름>
export PAGE_CERT_ARN=<us-east-1의 ACM 인증서 ARN, PAGE_DOMAIN 포함>
export PAGE_ZONE_ID=<PAGE_DOMAIN의 공개 호스팅 영역 ID>
```

**명령**

```bash
./demo.sh page-up "$RUN_ID"     # 실측 446초 (VPC origin과 배포 반영이 대부분)
./demo.sh status "$RUN_ID"      # page https://<PAGE_DOMAIN>/ (Deployed)
```

`PAGE_DOMAIN`에 이 run의 배포를 가리키지 않는 기존 레코드가 있으면 스크립트는 DNS를 건드리지 않고 멈춥니다. `page-down` 뒤에 다시 `page-up`하면, 그 사이에 주소를 조회한 리졸버가 "없음" 응답을 최대 15분(호스팅 영역 SOA의 negative TTL) 동안 캐시할 수 있습니다. 실측에서도 다시 만든 직후 이 서버의 VPC 리졸버만 NXDOMAIN을 돌려줬고, 권한 서버와 공용 리졸버는 정상이었습니다. 발표 직전에는 페이지를 다시 만들지 않습니다.

**예상 화면** (실측, run `d1124`, 단계마다 캡처로 확인): 제목 줄의 단계가 데모 진행에 따라 바뀝니다. 시작에는 "0 · 시작: 세 벌 모두 노드 역할"과 노드 (IMDS) 카드 세 장, `migrate-irsa` 뒤에는 orders-irsa 카드가 IRSA로, `migrate-podid` 뒤에는 orders-podid 카드가 Pod Identity로 바뀌고 주입된 변수 이름이 나타납니다. `revoke` 뒤에는 orders-legacy 카드만 빨간 테두리와 `denied`가 됩니다.

**확인 포인트.** 카드의 상태는 터미널 `watch`와 같아야 하고, 페이지 상단의 UTC 시각이 2초마다 바뀌어야 합니다. 대시보드 Pod에서 IMDS가 막혔는지는 다음으로 확인합니다.

```bash
P=$(kubectl -n "wid-$RUN_ID" get pod -l app=wid-dashboard -o name | head -1)
kubectl -n "wid-$RUN_ID" exec "$P" -- python3 -c "import urllib.request as u; u.urlopen(u.Request('http://169.254.169.254/latest/api/token', method='PUT', headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}), timeout=3)"
# 실측: urllib.error.URLError (timed out) — 막혀 있음
```

**왜 그렇게 되나.** 대시보드는 2초마다 Kubernetes API에서 상태를 모아 메모리에 두고, 응답에 `Cache-Control: max-age=1`을 붙입니다. CloudFront가 이 헤더를 따라 캐시하므로 청중이 많아도 클러스터 API 호출은 늘지 않습니다.

**비용과 정리.** 띄워 둔 동안 ALB 비용이 하루 약 US$0.55 더 듭니다. `./demo.sh page-down "$RUN_ID"`(실측 546초)로 지우며, `down`도 먼저 이것을 실행합니다. 남은 것이 없는지는 다음으로 확인합니다.

```bash
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='wid-$RUN_ID-page'].Id" --output text   # 빈 출력
aws cloudfront list-vpc-origins --query "VpcOriginList.Items[?Name=='wid-$RUN_ID-page'].Id" --output text         # 빈 출력
aws elbv2 describe-load-balancers --names "wid-$RUN_ID-page" 2>&1 | grep -c LoadBalancerNotFound                   # 1
aws route53 list-resource-record-sets --hosted-zone-id "$PAGE_ZONE_ID" \
  --query "ResourceRecordSets[?Name=='$PAGE_DOMAIN.'].Type" --output text                                          # 빈 출력
```

## 정리 (`down`)

`harden`을 실행했다면 노드 그룹이 `ACTIVE`인지 먼저 확인합니다. 같은 RUN_ID로 다시 연습하려면 `down` 대신 `./demo.sh restore "$RUN_ID"`로 시작 상태로 돌아갈 수 있습니다.

**명령**

```bash
./demo.sh down "$RUN_ID"
```

**예상 출력** (실측, run `t1121`, 323초)

```text
==> deleted namespace
==> deleting node group (3–5 min)
==> deleted launch template
==> deleted role wid-t1121-node
==> deleted role wid-t1121-irsa
==> deleted role wid-t1121-podid
==> deleted bucket
==> done
```

**남은 리소스 확인.** `down`은 전용 kubeconfig를 지우므로 AWS CLI로 확인합니다.

```bash
aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" 2>&1 | grep -c ResourceNotFound   # 1
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "wid-$RUN_ID" \
  --query 'length(associations)'                                                             # 0
for r in node irsa podid; do
  aws iam get-role --role-name "wid-$RUN_ID-$r" >/dev/null 2>&1 && echo "left: wid-$RUN_ID-$r"
done                                                                                          # 출력 없음
aws ec2 describe-launch-templates --filters "Name=tag:LabRun,Values=$RUN_ID" \
  --query 'LaunchTemplates[].LaunchTemplateName' --output text                               # 빈 출력
aws ec2 describe-instances --filters "Name=tag:LabRun,Values=$RUN_ID" \
  "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text                              # 빈 출력
aws s3api head-bucket --bucket "wid-$RUN_ID-$(aws sts get-caller-identity --query Account --output text)-$AWS_REGION" \
  2>&1 | grep -c 404                                                                         # 1
```

평소 쓰는 kubeconfig로 `kubectl get namespace wid-$RUN_ID`가 `NotFound`인지도 확인합니다. 공개 데모 페이지를 띄웠다면 CloudFront 배포와 internal ALB가 남지 않았는지도 확인합니다. env 파일은 다음 실습에 다시 쓸 수 있으며, 필요 없으면 `$STATE_DIR`를 지웁니다.

## 문제 해결

| 증상 | 원인과 조치 |
| --- | --- |
| 사용법(`Usage: ./demo.sh <command> RUN_ID`)만 출력됨 | RUN_ID는 소문자와 숫자 4–12자여야 합니다. 하이픈과 대문자는 쓸 수 없습니다. |
| `set CLUSTER to an existing EKS cluster name` 등 | `CLUSTER`, `VPC_NAME`, `SUBNET_NAMES`가 비었습니다. env 파일 경로와 내용을 확인합니다. env 파일 값이 셸 변수보다 우선합니다. |
| `cluster VPC is not <VPC_NAME>` | `VPC_NAME`으로 찾은 VPC가 클러스터 VPC와 다릅니다. 클러스터 VPC의 Name 태그를 다시 확인합니다. |
| `private subnet '<name>' not found in <VPC_NAME>` | 서브넷이 클러스터 VPC에 없거나 `MapPublicIpOnLaunch=true`인 Public 서브넷입니다. Private 서브넷 Name 태그를 넣습니다. |
| `eks-pod-identity-agent add-on is required` | `aws eks create-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent`로 애드온을 설치하고 `ACTIVE`를 기다립니다. 클러스터 관리자와 협의하세요. |
| `IAM OIDC provider for the cluster is required` | 클러스터 issuer를 IAM OIDC provider로 등록합니다 (예: `eksctl utils associate-iam-oidc-provider --cluster "$CLUSTER" --approve`). |
| `role ... is not tagged for run ...; refusing to modify it` | 같은 이름의 역할이 이미 있고 이 실습의 태그가 없습니다. 다른 RUN_ID를 씁니다. |
| `up`이 노드 그룹 생성에서 오래 멈춤 | `aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" --query nodegroup.health`로 원인을 봅니다. Private 서브넷의 NAT 경로가 없으면 노드가 조인하거나 이미지를 받지 못합니다. |
| `watch`에 `starting`이 계속 보임 | Pod가 아직 `Running`이 아니거나 로그가 없습니다. `kubectl -n "$NS" get pods`, `kubectl -n "$NS" describe pod`로 확인합니다. |
| `association change not visible to admission within 120s` | `aws eks list-pod-identity-associations`로 association이 있는지 확인하고 `migrate-podid`를 다시 실행합니다. 이미 있으면 생성은 건너뛰고 주입 확인부터 합니다. |
| `migrate-podid` 뒤에도 `orders-podid`가 노드 역할 | 주입 전에 만들어진 Pod입니다. 단계 3의 env 확인 명령으로 변수를 보고, 없으면 `kubectl -n "$NS" rollout restart deploy/orders-podid`를 다시 합니다. |
| `legacy copy did not flip within 180s` | IAM 전파가 느린 경우입니다. `watch`를 계속 보며 기다립니다. 다시 실행하면 정책이 이미 지워졌다고 표시하고 대기만 다시 합니다. |
| S3 결과가 `error` | `AccessDenied`나 자격 증명 없음이 아닌 오류입니다. Pod에서 STS·S3 엔드포인트로 가는 경로(NAT, VPC 엔드포인트, DNS)를 확인합니다. |
| 기대한 역할인데 `denied` | 역할 신원과 리소스 접근은 별개입니다. 버킷 정책, SCP, 권한 경계, VPC 엔드포인트 정책을 확인합니다. |

## 참고 자료

- [EKS 노드 IAM 권한을 IRSA와 Pod Identity로 이전하기](../../security/17-eks-workload-identity-migration.md) — 이 실습의 워크북
- [데모 코드와 발표 런북](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity)
- [IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity 동작 원리](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [관리형 노드 그룹 launch template](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)

## 다음 단계

- [EKS 워크로드 IAM 이전 퀴즈](../../quizzes/security/17-eks-workload-identity-migration-quiz.md)로 이해도를 확인합니다.
- 워크북의 [운영 클러스터의 이전 순서](../../security/17-eks-workload-identity-migration.md)를 참고해 실제 워크로드의 의존성 조사와 카나리 전환 계획을 세웁니다.
