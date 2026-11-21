# EKS 노드 IAM 권한을 IRSA와 Pod Identity로 이전하기

> **마지막 업데이트**: 2026년 11월 21일

애플리케이션의 S3 권한을 EC2 노드의 인스턴스 프로파일, 즉 노드 IAM 역할에 붙이면 그 노드에서 인스턴스 메타데이터 서비스(IMDS)에 접근할 수 있는 모든 Pod가 같은 권한을 씁니다. 결제 Pod 하나를 위해 추가한 권한이 같은 노드의 로그 수집기와 배치 Job에도 열립니다. CloudTrail에는 모두 노드 인스턴스 ID 세션으로만 남아서 어느 워크로드가 호출했는지 구분하기도 어렵습니다.

이 문서는 그 권한을 워크로드 단위로 옮기는 두 방법인 IRSA(IAM Roles for Service Accounts)와 EKS Pod Identity가 각각 어떻게 동작하는지 비교합니다. 그런 다음 운영 클러스터에서 이전하는 순서를 정리하고, 같은 앱 세 벌로 이전 과정을 직접 실행한 라이브 데모 결과를 보여 줍니다.

## 자격 증명은 어디서 오는가

![세 Pod가 자격 증명을 받는 경로. 노드 역할 Pod는 IMDSv2에서, IRSA Pod는 STS AssumeRoleWithWebIdentity에서, Pod Identity Pod는 같은 노드의 Pod Identity Agent와 EKS Auth를 거쳐 임시 자격 증명을 받고, 각자 받은 자격 증명으로 S3 요청에 서명한다.](../.gitbook/assets/ko-security-17-eks-workload-identity-migration-anim-0.svg)

Pod 안의 AWS SDK와 AWS CLI는 [기본 자격 증명 공급자 체인](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)을 위에서부터 차례로 확인합니다. 환경 변수의 정적 키, 웹 ID 토큰(IRSA), 컨테이너 자격 증명 공급자(Pod Identity)가 IMDS보다 앞에 있습니다. 그래서 EKS가 IRSA나 Pod Identity용 환경 변수를 주입한 새 Pod는 코드를 바꾸지 않아도 새 역할을 사용합니다. 반대로 아무것도 주입되지 않은 Pod는 마지막 단계인 IMDS까지 내려가 노드 역할을 받습니다.

| 경로 | Pod에 주입되는 것 | SDK가 호출하는 곳 | 결과 역할 |
| --- | --- | --- | --- |
| 노드 인스턴스 프로파일 | 없음 | IMDSv2 `169.254.169.254` | 노드 IAM 역할 (노드의 모든 Pod가 공유) |
| IRSA | `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`, 토큰 볼륨 | 리전 STS(Security Token Service) `AssumeRoleWithWebIdentity` | ServiceAccount 주석의 역할 |
| EKS Pod Identity | `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`, 토큰 볼륨 | 같은 노드의 Pod Identity Agent `169.254.170.23` | association에 지정한 역할 |

IMDS 응답 hop limit이 2 이상이면 hostNetwork를 쓰지 않는 일반 Pod도 IMDSv2 토큰을 받아 노드 역할 자격 증명을 가져갈 수 있습니다. 관리형 노드 그룹의 launch template이 이 값을 2로 두는 경우가 많습니다. 이전을 마친 뒤 hop limit을 1로 내려 이 경로를 닫는 이유입니다.

<a id="irsa-flow"></a>
## IRSA 동작 원리

![IRSA 흐름. ServiceAccount 주석을 본 웹훅이 환경 변수와 projected 토큰(aud sts.amazonaws.com)을 Pod에 넣고, SDK가 토큰을 STS AssumeRoleWithWebIdentity로 보내면 STS가 IAM OIDC provider로 서명을 검증하고 신뢰 정책의 aud와 sub를 확인한 뒤 임시 자격 증명을 돌려준다.](../.gitbook/assets/ko-security-17-eks-workload-identity-migration-anim-1.svg)

1. **신뢰 준비.** 클러스터마다 OIDC(OpenID Connect) issuer URL이 있습니다. 이 issuer를 계정의 IAM OIDC provider로 한 번 등록합니다. 역할의 신뢰 정책은 이 provider를 `Federated` principal로 두고 `aud`(`sts.amazonaws.com`)와 `sub`(`system:serviceaccount:<namespace>:<serviceaccount>`)를 조건으로 겁니다.
2. **Pod 생성 시 주입.** ServiceAccount에 `eks.amazonaws.com/role-arn` 주석이 있으면 EKS의 mutating 웹훅이 새 Pod에 `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`과 `/var/run/secrets/eks.amazonaws.com/serviceaccount/token` projected 토큰 볼륨을 추가합니다. 이미 실행 중인 Pod는 바뀌지 않으므로 rollout이 필요합니다.
3. **토큰 발급과 갱신.** kubelet이 대상(audience) `sts.amazonaws.com`으로 ServiceAccount 토큰을 발급받아 파일로 두고 만료 전에 갱신합니다.
4. **토큰 교환.** SDK가 토큰을 리전 STS `AssumeRoleWithWebIdentity`로 보냅니다. STS는 IAM OIDC provider에 등록된 issuer의 공개 키로 서명을 검증하고, 신뢰 정책의 `aud`·`sub` 조건을 확인한 뒤 임시 자격 증명을 돌려줍니다. Pod가 STS와 직접 통신하므로 Pod에서 STS로 가는 경로가 필요합니다. [AWS IRSA 문서](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

<a id="pod-identity-flow"></a>
## EKS Pod Identity 동작 원리

![Pod Identity 흐름. EKS API의 association이 ServiceAccount를 역할에 연결하고, EKS가 컨테이너 자격 증명 환경 변수와 projected 토큰(aud pods.eks.amazonaws.com)을 Pod에 넣는다. SDK는 같은 노드의 Pod Identity Agent를 호출하고, Agent가 노드 역할의 eks-auth 권한으로 EKS Auth AssumeRoleForPodIdentity를 호출하면 EKS가 세션 태그를 붙여 역할을 맡은 자격 증명을 돌려준다.](../.gitbook/assets/ko-security-17-eks-workload-identity-migration-anim-2.svg)

1. **에이전트 준비.** 클러스터마다 한 번 `eks-pod-identity-agent` 애드온을 설치합니다. 에이전트는 노드의 hostNetwork에서 링크 로컬 주소 `169.254.170.23`(IPv6 `[fd00:ec2::23]`)의 포트 80과 2703을 사용하는 DaemonSet입니다. EKS Auto Mode에는 이 기능이 내장되어 있습니다.
2. **역할과 association.** 역할의 신뢰 정책은 서비스 principal `pods.eks.amazonaws.com`에 `sts:AssumeRole`과 `sts:TagSession`을 허용합니다. 클러스터별 provider가 없으므로 같은 역할을 다른 클러스터에서 써도 신뢰 정책을 고치지 않습니다. 연결은 EKS API의 association(클러스터·namespace·ServiceAccount → 역할)으로 만들며 Kubernetes 객체에는 주석을 달지 않습니다.
3. **Pod 생성 시 주입.** association이 있는 ServiceAccount의 새 Pod에 EKS가 `AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`과 대상이 `pods.eks.amazonaws.com`인 projected 토큰을 넣습니다.
4. **자격 증명 조회.** SDK가 토큰을 같은 노드의 에이전트로 보냅니다. 에이전트는 노드 역할의 `eks-auth:AssumeRoleForPodIdentity` 권한(`AmazonEKSWorkerNodePolicy`에 포함)으로 EKS Auth를 호출합니다. EKS Auth는 토큰과 association을 확인하고 역할을 맡아 `eks-cluster-arn`, `kubernetes-namespace`, `kubernetes-service-account` 같은 세션 태그를 붙인 자격 증명을 돌려줍니다. 노드 역할에 남는 것은 에이전트가 EKS Auth를 부를 권한뿐이고, 앱의 업무 권한은 Pod Identity 역할에 있습니다. [Pod Identity 동작 원리](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)

## IRSA와 Pod Identity 비교

AWS는 가능한 경우 EKS Pod Identity를 권장합니다. 다만 실행 환경과 조직 구조에 따라 IRSA가 맞는 경우가 있습니다. [AWS 비교 문서](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)

| 항목 | IRSA | EKS Pod Identity |
| --- | --- | --- |
| 클러스터 쪽 준비 | 클러스터마다 IAM OIDC provider 등록 | 클러스터마다 Pod Identity Agent 애드온 (Auto Mode는 내장) |
| 연결 위치 | Kubernetes ServiceAccount 주석 | EKS API association (Kubernetes 객체 변경 없음) |
| 신뢰 정책 | `Federated` OIDC provider + `aud`/`sub` 조건. 클러스터마다 문장 추가 | `pods.eks.amazonaws.com` 하나. 새 클러스터에서도 수정 없음 |
| 확장 한도 | 계정당 OIDC provider 기본 100개. 신뢰 정책 기본 2,048자라 보통 역할당 4개 안팎의 연결 | 클러스터당 association 5,000개. 역할 신뢰 정책은 늘지 않음 |
| 자격 증명 경로 | Pod → 리전 STS (Pod가 STS API 할당량 사용) | Pod → 노드 에이전트 → EKS Auth (Pod가 STS를 직접 호출하지 않음) |
| 세션 정보 | 역할 세션 이름. 세션 태그 없음 | 클러스터·namespace·ServiceAccount 세션 태그로 ABAC(속성 기반 접근 제어) 가능 |
| 실행 환경 | EKS의 EC2·Fargate, EKS Anywhere, ROSA, EC2의 자체 관리 Kubernetes | EKS의 Linux EC2 노드만. Fargate, Windows, Outposts, EKS Anywhere 미지원 |
| 교차 계정 | 대상 계정 역할이 이 클러스터의 OIDC provider를 신뢰 | association 역할은 클러스터와 같은 계정. 대상 역할을 지정하거나 역할 체이닝으로 위임 |
| 권한 분리 | OIDC provider 생성은 IAM 관리자, 주석은 클러스터 운영자 | IAM은 역할만, 연결은 EKS API에서. 팀 간 책임 분리가 명확 |

정리하면 신규 EKS EC2 워크로드에는 Pod Identity가 단순하고 확장에 유리합니다. Fargate나 Windows 노드, EKS 밖의 Kubernetes와 같은 구성을 공유해야 하는 워크로드에는 IRSA를 씁니다. 두 방식은 한 클러스터에서 함께 쓸 수 있습니다. 같은 ServiceAccount에 IRSA 주석과 association이 모두 있으면 EKS 웹훅은 새 Pod에 Pod Identity 변수만 넣고 IRSA 변수는 넣지 않습니다. 데모 클러스터에서 `kubectl create --dry-run=server`로 확인해 보니, 주석만 있을 때는 `AWS_ROLE_ARN`·`AWS_WEB_IDENTITY_TOKEN_FILE`이, association을 더하자 `AWS_CONTAINER_CREDENTIALS_FULL_URI`·`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`만 주입됐습니다. 이미 실행 중인 Pod는 다시 만들기 전까지 IRSA 변수를 그대로 갖고 있으므로, 방식을 바꿀 때는 rollout으로 Pod를 새로 만들고 쓰지 않는 주석은 지웁니다.

프라이빗 클러스터에서는 IRSA Pod가 쓰는 리전 STS와 Pod Identity Agent가 쓰는 EKS Auth(`eks-auth`)의 경로를 각각 확보합니다. 인터넷 경로가 없으면 해당 VPC 인터페이스 엔드포인트와 DNS, 보안 그룹을 확인합니다. 프록시를 쓰면 `169.254.170.23`과 `[fd00:ec2::23]`을 `NO_PROXY`에 넣습니다. [Pod Identity 고려 사항](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [프라이빗 클러스터 요구 사항](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## 운영 클러스터의 이전 순서

1. **의존성을 조사합니다.** 노드 역할의 정책과 CloudTrail의 실제 IAM 세션을 비교하고, Deployment·StatefulSet·DaemonSet·CronJob·컨트롤러가 쓰는 AWS API를 파악합니다. S3 객체 접근을 CloudTrail에서 보려면 해당 버킷의 데이터 이벤트가 필요합니다. 노드 등록과 Pod Identity Agent에 필요한 `AmazonEKSWorkerNodePolicy`, Amazon ECR(Elastic Container Registry) 이미지 pull용 `AmazonEC2ContainerRegistryPullOnly` 또는 동등한 권한은 유지합니다. VPC CNI(Container Network Interface)의 `AmazonEKS_CNI_Policy`는 `aws-node` 전용 역할로 옮길 수 있습니다. CNI 자격 증명과 새 Pod의 IP 할당을 검증한 뒤 노드 역할에서 회수합니다. [EKS 노드 IAM 역할](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3 CloudTrail 이벤트](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **워크로드별 역할과 전용 ServiceAccount를 준비합니다.** 리소스 단위로 IAM 권한을 제한합니다. IRSA는 클러스터 issuer를 IAM OIDC provider로 등록하고 `aud`와 정확한 `sub`가 포함된 역할을 만든 뒤 `eks.amazonaws.com/role-arn`을 붙입니다. Pod Identity는 Agent 준비 상태와 노드의 EKS Auth 권한을 확인한 뒤, 요청 태그를 제한한 역할로 association을 생성합니다. 배포 플랫폼과 AWS SDK 지원 버전도 확인합니다. [IRSA 최소 SDK 버전](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod Identity 최소 SDK 버전](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **카나리 Pod를 새로 생성합니다.** Pod 템플릿의 `serviceAccountName`을 변경하거나 rollout으로 Pod를 새로 만들고, 새 Pod에서 주입된 환경 변수의 이름, 실행 프로세스의 AWS 호출자 ARN, 필요한 AWS API의 성공 여부를 확인합니다. 토큰이나 키를 로그에 출력하지 않습니다. SDK의 기본 체인에서 명시적 자격 증명이나 이전 공급자가 우선할 수 있습니다. [기본 자격 증명 공급자 체인](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **워크로드를 순차적으로 전환합니다.** 오류율, `AccessDenied`, 토큰 및 임시 자격 증명 갱신, 크론 실행까지 관찰합니다. 워크로드가 노드 역할의 업무 권한에 의존하지 않는 것을 확인한 뒤, 해당 정책 문장만 회수합니다. 롤백 창에는 이전 Pod 템플릿과 노드 정책의 정확한 복원본을 준비합니다. 권한 회수 후 원복이 필요하면 해당 최소 정책을 먼저 복구하고 전파를 확인한 뒤 이전 Pod를 배포합니다.
5. **노드 자격 증명 접근을 제한합니다.** 호환성을 검증한 노드 그룹부터 IMDSv2를 강제하고 일반 Pod의 IMDS 접근을 제한합니다. 사용자 지정 launch template을 쓰는 관리형 노드 그룹은 새 버전에 `HttpTokens=required`, `HttpPutResponseHopLimit=1`을 지정하고 롤링 교체합니다. Karpenter는 `EC2NodeClass.spec.metadataOptions`에서 정하며 EKS Auto Mode는 IMDSv2와 hop limit 1을 기본 적용합니다. `hostNetwork` Pod는 hop limit과 관계없이 IMDS에 접근하므로 별도로 통제합니다. IMDS 자체를 끄지는(`HttpEndpoint=disabled`) 않습니다. Pod Identity Agent도 hostNetwork에서 IMDS로 노드 역할 자격 증명을 받아 EKS Auth를 호출하기 때문입니다. [관리형 노드 그룹 launch template](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [EKS IAM 보안 모범 사례](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>신뢰 정책과 카나리 전환 명령</summary>

IRSA 역할의 신뢰 정책은 클러스터 issuer와 ServiceAccount를 제한합니다. `<OIDC_ISSUER>`에 `https://`를 뺀 issuer를 넣습니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/<OIDC_ISSUER>"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "<OIDC_ISSUER>:aud": "sts.amazonaws.com",
      "<OIDC_ISSUER>:sub": "system:serviceaccount:<NAMESPACE>:<IRSA_SA>"
    }}
  }]
}
```

Pod Identity 역할은 EKS 서비스 principal을 신뢰합니다. 아래 조건은 세션 태그로 클러스터·namespace·ServiceAccount를 제한하므로 association의 세션 태그를 켠 상태로 둡니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"],
    "Condition": {"StringEquals": {
      "aws:RequestTag/eks-cluster-arn": "<CLUSTER_ARN>",
      "aws:RequestTag/kubernetes-namespace": "<NAMESPACE>",
      "aws:RequestTag/kubernetes-service-account": "<POD_IDENTITY_SA>"
    }}
  }]
}
```

```bash
# IRSA를 선택한 경우
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" annotate sa "$IRSA_SA" \
  "eks.amazonaws.com/role-arn=$IRSA_ROLE_ARN"

# Pod Identity를 선택하고 Agent가 준비된 경우
aws eks create-pod-identity-association --region "$AWS_REGION" --cluster-name "$CLUSTER" \
  --namespace "$NAMESPACE" --service-account "$POD_IDENTITY_SA" --role-arn "$POD_IDENTITY_ROLE_ARN"

# 위에서 선택한 ServiceAccount로 카나리를 새로 배포
SA="$IRSA_SA"   # 또는 "$POD_IDENTITY_SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set serviceaccount \
  deployment "$CANARY_DEPLOYMENT" "$SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$CANARY_DEPLOYMENT" --timeout=5m
```

</details>

<a id="live-demo"></a>
## 라이브 데모: 같은 앱 세 벌로 이전하기

![데모 흐름. 처음에는 orders 앱 세 벌이 모두 IMDS에서 노드 역할을 받아 S3를 읽는다. migrate-irsa 뒤 한 벌은 STS로 IRSA 역할을, migrate-podid 뒤 다른 한 벌은 Pod Identity Agent로 Pod Identity 역할을 받는다. revoke로 노드 역할의 S3 권한을 지우면 레거시 한 벌만 AccessDenied가 된다.](../.gitbook/assets/ko-security-17-eks-workload-identity-migration-anim-3.svg)

데모는 기존 EKS 1.36 클러스터에 전용 관리형 노드 그룹 한 대(t3.medium, Private 서브넷, taint 적용)를 추가하고 그 위에 같은 orders 앱을 세 벌 띄웁니다. 세 벌은 3초마다 STS `GetCallerIdentity`와 S3 `GetObject`를 호출하고, 자격 증명 출처·역할 이름·S3 결과를 JSON 한 줄로 남깁니다. 출발점은 운영 노드 그룹과 같은 IMDSv2 필수·hop limit 2이고, 노드 역할에 앱의 `s3:GetObject`가 붙어 있는 상태입니다. 레거시 Pod도 hostNetwork 없는 일반 Pod입니다. [데모 코드와 발표 런북](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity) · [발표 자료](https://presentation.atomai.click/eks-workload-identity/)

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
export CLUSTER=<클러스터 이름> VPC_NAME=<클러스터 VPC의 Name 태그> \
  SUBNET_NAMES=<Private 서브넷 Name 태그 1>,<Private 서브넷 Name 태그 2>
./demo.sh up d1124            # 발표 전: 노드 그룹, 역할, 버킷, 앱 세 벌
./demo.sh watch d1124         # 두 번째 터미널: 실시간 표
./demo.sh migrate-irsa d1124  # ServiceAccount 주석 + rollout
./demo.sh migrate-podid d1124 # association 생성 + 주입 확인 + rollout
./demo.sh diff d1124          # 주입 변수·토큰·신뢰 정책 비교
./demo.sh revoke d1124        # 노드 역할에서 S3 권한 삭제
./demo.sh harden d1124        # (선택, 약 15분) hop limit 1로 노드 교체
./demo.sh restore d1124       # 처음 상태로 (리허설 반복)
./demo.sh down d1124          # 정리
```

청중에게는 `page-up`으로 읽기 전용 실시간 페이지를 공유할 수 있습니다. 경로는 CloudFront → VPC origin → internal ALB → 대시보드 Pod이고, ALB 보안 그룹은 CloudFront VPC origin만 받습니다. 대시보드 Pod에는 IAM 역할이 없고, 이 namespace의 Pod와 로그를 읽는 Role만 있습니다. 데모 노드는 hop limit 2라서 NetworkPolicy로 이 Pod가 IMDS와 Pod Identity Agent에 닿지 못하게 막습니다. 이 격리는 VPC CNI 네트워크 정책(`enableNetworkPolicy`)이 켜져 있어야 동작하므로 `page-up`이 먼저 확인합니다.

스크립트가 만드는 리소스는 이름에 run ID가 들어가거나 `LabRun` 태그가 붙고, 스크립트는 그 이름이나 태그에 해당하는 리소스만 수정하고 삭제합니다. VPC·서브넷·애드온·OIDC provider는 만들지 않고 있는지만 확인합니다. 보안 그룹은 선택 단계인 `page-up`이 internal ALB용으로 하나만 만듭니다. 단계별 명령과 예상 출력, 확인 포인트는 [실습 가이드](../labs/security/17-eks-workload-identity-migration-lab.md)에 있습니다.

### 서울 리전 실측 결과

2026년 11월 21일, 서울 리전(`ap-northeast-2`)의 EKS 1.36 클러스터에서 Pod 안의 AWS CLI 2.35.11로 두 번 리허설했습니다. 첫 리허설에서 Pod Identity 주입이 실패해(아래 참고) 스크립트를 고쳤고, 표는 고친 스크립트로 처음부터 끝까지 이어서 실행한 두 번째 리허설의 값입니다. `harden`만 첫 리허설에서 측정했습니다.

| 단계 | orders-legacy | orders-irsa | orders-podid | 걸린 시간 |
| --- | --- | --- | --- | --- |
| 시작 | IMDS · 노드 역할 · 읽기 성공 | IMDS · 노드 역할 · 읽기 성공 | IMDS · 노드 역할 · 읽기 성공 | — |
| `migrate-irsa` | 변화 없음 | STS · IRSA 역할 · 읽기 성공 | 변화 없음 | 6초 |
| `migrate-podid` | 변화 없음 | 변화 없음 | Agent · Pod Identity 역할 · 읽기 성공 | 11초 (association 생성 후 주입 확인까지 5초 포함) |
| `revoke` | 노드 역할 · **읽기 거부** | 읽기 성공 | 읽기 성공 | 13초 후 거부 |
| `harden` (선택, 첫 리허설) | **자격 증명 없음** (IMDS 응답 차단) | 읽기 성공 | 읽기 성공 | 노드 교체 878초 |

`diff`로 본 두 방식의 차이는 다음과 같습니다. 같은 클러스터 issuer가 서명한 ServiceAccount 토큰이지만 대상(audience)과 받는 쪽이 다릅니다.

| 비교 | IRSA Pod | Pod Identity Pod |
| --- | --- | --- |
| 주입된 환경 변수 | `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`, `AWS_STS_REGIONAL_ENDPOINTS` | `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`, `AWS_STS_REGIONAL_ENDPOINTS` |
| 토큰 `aud` | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| 토큰 `sub` | `system:serviceaccount:wid-d1124:orders-irsa` | `system:serviceaccount:wid-d1124:orders-podid` |
| 토큰 수명 | 86,400초 (24시간) | 약 22~24시간 (웹훅이 수명에 무작위 편차를 줌. 실측 79,636초와 86,171초) |
| 역할 신뢰 principal | `Federated`: 클러스터 OIDC provider, 조건 `aud`·`sub` | `Service`: `pods.eks.amazonaws.com`, 조건 요청 태그 3개 |

리허설에서 두 가지 eventual consistency를 확인했습니다. 첫째, 첫 리허설에서 association을 만든 직후 rollout한 Pod에는 Pod Identity 변수가 주입되지 않아 노드 역할을 계속 썼고, 이어서 노드 정책을 회수하자 이 복사본도 거부됐습니다. 그래서 `migrate-podid`는 Deployment의 Pod 템플릿을 `kubectl create --dry-run=server`로 보내 mutating 웹훅의 주입 결과를 확인한 뒤에 rollout합니다. 두 번째 리허설에서는 association을 만들고 5초가 지나서야 주입이 확인됐습니다. 둘째, 첫 리허설의 `revoke` 뒤 레거시 Pod는 13초 만에 거부됐지만 약 4분 30초 뒤에 허용 응답이 두 번 더 나왔습니다. 그 직후 다시 확인한 1분 동안(로그 11건)은 모두 거부였습니다. 운영에서 노드 정책을 회수한 뒤에는 수 분 이상 관찰하고 판단합니다.

## 문제 해결

- **노드 역할이 표시됨**. 새 Pod를 생성했는지, 올바른 ServiceAccount를 참조하는지, IRSA 주석 또는 정확한 association이 있는지 확인합니다. SDK 버전, 기본 공급자 체인, Pod에 주입된 환경 변수 이름을 점검합니다.
- **IRSA에서 토큰 교환 실패**. 토큰의 issuer에 대응하는 IAM provider, `aud`·`sub` 신뢰 조건, STS 도달 가능성을 확인합니다.
- **Pod Identity에서 자격 증명 조회 실패**. 해당 노드의 Agent, EKS Auth 통신, 노드 IAM 권한, association 전파, 요청 태그에 대한 역할 신뢰 정책을 확인합니다. association은 생성 후 몇 초 동안 반영되지 않을 수 있습니다.
- **기대 역할인데 S3에서 거부됨**. 역할 신원과 리소스 접근은 별개입니다. 객체 ARN, 버킷 정책, SCP(Service Control Policy), 권한 경계, VPC 엔드포인트 정책을 확인합니다. AWS KMS(Key Management Service) 키로 서버 측 암호화(SSE-KMS)한 객체라면 키에 대한 권한도 확인합니다.
