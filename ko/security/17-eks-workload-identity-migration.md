# EKS 노드 IAM 권한을 IRSA와 Pod Identity로 이전하기

> **마지막 업데이트**: 2026년 11월 20일

EC2 노드의 인스턴스 프로파일에 연결된 IAM 역할에 애플리케이션의 S3 권한을 붙이면, 해당 노드의 인스턴스 메타데이터 서비스(IMDS)에 접근하는 워크로드가 같은 역할을 사용할 수 있습니다. 이번 실습은 같은 S3 객체 읽기를 노드 역할, IRSA(IAM Roles for Service Accounts), EKS Pod Identity로 각각 실행합니다. 노드에서 객체 읽기 권한을 회수한 뒤 어떤 요청이 계속 성공하는지 확인합니다.

## 자격 증명은 어디서 오는가

![노드 역할은 IMDSv2에서, IRSA는 웹 자격 증명 토큰을 교환하는 STS에서, Pod Identity는 노드의 Pod Identity Agent와 EKS Auth를 거쳐 임시 자격 증명을 받는다. 세 Pod는 받은 자격 증명으로 S3 요청에 서명한다.](../.gitbook/assets/ko-security-17-eks-workload-identity-migration-anim-0.svg)

1. **인스턴스 프로파일**. EC2에 연결된 프로파일은 노드 IAM 역할을 담습니다. Pod가 IMDS에 접근할 수 있고 AWS SDK가 EC2 메타데이터 공급자를 선택하면, SDK는 IMDSv2 세션 토큰으로 노드 역할의 임시 자격 증명을 가져옵니다. 같은 역할을 사용한 요청은 노드 역할 세션으로 나타납니다.
2. **IRSA**. EKS는 역할 ARN이 주석으로 지정된 ServiceAccount를 사용하는 새 Pod에 `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`과 projected ServiceAccount 토큰을 주입합니다. SDK는 대상이 `sts.amazonaws.com`인 토큰을 AWS STS(Security Token Service) `AssumeRoleWithWebIdentity`로 교환합니다. IAM은 클러스터의 OIDC(OpenID Connect) issuer를 신뢰하고, 역할의 신뢰 정책에서 `aud`와 `sub`를 확인합니다. `sub`는 `system:serviceaccount:<namespace>:<serviceaccount>`입니다. [AWS IRSA 문서](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
3. **EKS Pod Identity**. EKS에 등록한 association은 클러스터·namespace·ServiceAccount를 역할에 연결합니다. EKS가 새 Pod에 `AWS_CONTAINER_CREDENTIALS_FULL_URI`, `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`과 대상이 `pods.eks.amazonaws.com`인 토큰을 주입합니다. SDK는 같은 노드의 Pod Identity Agent(`169.254.170.23`)에 토큰을 보냅니다. Pod Identity Agent는 노드 역할의 `eks-auth:AssumeRoleForPodIdentity` 권한으로 EKS Auth를 호출하고, EKS가 맡은 워크로드 역할의 임시 자격 증명을 Pod에 전달합니다. 역할은 `pods.eks.amazonaws.com`에 `sts:AssumeRole`과 `sts:TagSession`을 허용합니다. [Pod Identity 동작 원리](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html) · [역할 신뢰 정책](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html)

IRSA와 Pod Identity에서 EKS는 Pod 생성 시 토큰 볼륨과 환경 변수를 지정하고, kubelet이 해당 볼륨에 ServiceAccount 토큰을 발급받아 갱신합니다. AWS SDK는 임시 AWS 자격 증명을 캐시하고 만료에 맞춰 다시 조회합니다. 세 경우 모두 AWS CLI가 받은 자격 증명으로 S3 API 요청을 서명합니다. S3 권한은 IAM 권한 정책이 결정합니다. ServiceAccount 연결과 역할 신뢰 정책은 자격 증명을 발급받을 주체를 결정합니다.

## IRSA와 Pod Identity 선택

| 항목 | IRSA | EKS Pod Identity |
| --- | --- | --- |
| 연결 | ServiceAccount 역할 ARN 주석 + IAM OIDC provider | EKS association |
| 자격 증명 요청 경로 | Pod → 리전 STS | Pod → 노드 Agent → EKS Auth |
| 역할 신뢰 범위 | OIDC issuer + `aud` + `sub` | EKS 서비스 principal + 클러스터·namespace·ServiceAccount 요청 태그 |
| 실행 환경 | EKS의 EC2 및 Fargate 등에서 사용 가능 | 지원되는 EKS Linux EC2 노드. Auto Mode에는 에이전트 기능 내장 |
| 교차 계정 | 대상 계정의 OIDC 신뢰 또는 역할 체이닝 | association의 기본 역할은 클러스터 계정. 대상 역할이나 체이닝을 통해 교차 계정 접근 구성 |
| 작업 주체 구분 | 워크로드별 역할과 서비스 로그 | 워크로드별 역할과 EKS 세션 태그 |

프라이빗 클러스터에서는 IRSA Pod의 리전 STS 통신과 Pod Identity Agent의 EKS Auth 통신을 각각 확보합니다. 인터넷 경로가 없으면 해당 VPC 인터페이스 엔드포인트와 DNS, 보안 그룹을 확인합니다. 애플리케이션이 호출하는 S3 등 서비스 자체의 경로도 확보해야 합니다. 프록시가 있다면 Pod Identity의 링크 로컬 주소를 `NO_PROXY`에 포함합니다. [Pod Identity 지원 범위](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [프라이빗 클러스터의 요구사항](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## 운영 클러스터의 이전 순서

1. **의존성을 조사합니다.** 노드 역할의 정책과 CloudTrail의 실제 IAM 세션을 비교하고, Deployment·StatefulSet·DaemonSet·CronJob·컨트롤러가 쓰는 AWS API를 파악합니다. S3 객체 접근을 CloudTrail에서 보려면 해당 버킷의 데이터 이벤트가 필요합니다. 노드 등록과 Pod Identity Agent에 필요한 `AmazonEKSWorkerNodePolicy`, Amazon ECR(Elastic Container Registry) 이미지 pull용 `AmazonEC2ContainerRegistryPullOnly` 또는 동등한 권한은 유지합니다. VPC CNI(Container Network Interface)의 `AmazonEKS_CNI_Policy`는 `aws-node` 전용 역할로 옮길 수 있습니다. CNI 자격 증명과 새 Pod의 IP 할당을 검증한 뒤 노드 역할에서 회수합니다. [EKS 노드 IAM 역할](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3 CloudTrail 이벤트](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **워크로드별 역할과 전용 ServiceAccount를 준비합니다.** 리소스 단위로 IAM 권한을 제한합니다. IRSA는 클러스터 issuer를 IAM OIDC provider로 등록하고 `aud`와 정확한 `sub`가 포함된 역할을 만든 뒤 `eks.amazonaws.com/role-arn`을 붙입니다. Pod Identity는 Agent 준비 상태와 노드의 EKS Auth 권한을 확인한 뒤, 요청 태그를 제한한 역할로 association을 생성합니다. 배포 플랫폼·AWS SDK 지원 버전도 확인합니다. [IRSA 최소 SDK 버전](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod Identity 최소 SDK 버전](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **카나리 Pod를 새로 생성합니다.** Pod 템플릿의 `serviceAccountName`을 변경하고, 새 Pod에서 주입된 환경 변수의 이름, 실행 프로세스의 AWS 호출자 ARN, 필요한 AWS API의 성공 여부를 확인합니다. 토큰이나 키를 로그에 출력하지 않습니다. SDK의 기본 체인에서 명시적 자격 증명이나 이전 공급자가 우선할 수 있습니다. IRSA 주석이 붙어 있으면 일반적인 SDK에서 웹 자격 증명 공급자가 컨테이너 공급자보다 앞서므로 Pod Identity 검증에 별도 ServiceAccount를 사용합니다. [기본 자격 증명 공급자 체인](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **워크로드를 순차적으로 전환합니다.** 오류율, `AccessDenied`, 토큰 및 임시 자격 증명 갱신, 크론 실행까지 관찰합니다. 워크로드가 노드 역할의 업무 권한에 의존하지 않는 것을 확인한 뒤, 해당 정책 문장만 회수합니다. 운영의 롤백 창에는 이전 Pod 템플릿과 노드 정책의 정확한 복원본을 준비합니다. 권한 회수 후 원복이 필요하면 해당 최소 정책을 먼저 복구하고 전파를 확인한 뒤 이전 Pod를 배포합니다.
5. **노드 자격 증명 접근을 제한합니다.** 호환성을 검증한 노드 그룹부터 IMDSv2를 강제하고 일반 Pod의 IMDS 접근을 제한합니다. 사용자 지정 launch template을 쓰는 관리형 노드 그룹은 새 버전에 `HttpTokens=required`, `HttpPutResponseHopLimit=1`을 지정하고 롤링 교체합니다. 기존 그룹에 사용자 지정 template이 없다면 새 그룹에서 검증하고 워크로드를 옮깁니다. Karpenter는 `EC2NodeClass.spec.metadataOptions`에서 정하며 EKS Auto Mode는 IMDSv2와 hop limit 1을 기본 적용합니다. `hostNetwork` Pod, privileged Pod와 노드 수준 접근은 별도로 통제합니다. `AWS_EC2_METADATA_DISABLED=true`는 SDK의 메타데이터 공급자를 끄는 설정입니다. [관리형 노드 그룹 launch template](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [Auto Mode IMDS 설정](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html) · [EKS IAM 보안 모범 사례](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>카나리 전환 명령</summary>

아래 명령은 역할의 신뢰 정책과 전용 ServiceAccount를 준비한 뒤 카나리 Deployment에 적용하는 예입니다. `KUBE_CONTEXT`를 대상 클러스터의 컨텍스트로 지정합니다. GitOps 환경에서는 같은 ServiceAccount 변경을 선언 소스에 반영합니다.

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

Pod Identity 역할은 EKS 서비스에 연결하며 기본 설정으로 전달하는 요청 태그를 확인합니다. 이 조건을 쓰면 association의 세션 태그를 활성화한 상태로 유지합니다.

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

# 위에서 선택한 ServiceAccount를 지정
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set serviceaccount \
  deployment "$CANARY_DEPLOYMENT" "$SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$CANARY_DEPLOYMENT" --timeout=5m
```

</details>

## 같은 S3 객체로 직접 비교

데모는 전용 EKS 클러스터, Linux EC2 노드 한 대와 한 개의 S3 객체를 사용합니다. 노드와 두 워크로드 역할에 같은 객체의 `s3:GetObject`를 허용합니다. 레거시 Pod는 비교를 위해 host networking으로 IMDSv2에 접근합니다. IRSA와 Pod Identity Pod는 일반 Pod 네트워크를 쓰며 SDK의 IMDS 폴백을 끕니다. [재현용 코드와 환경 요구사항](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity)

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
RUN_ID="$(date -u +%y%m%d%H%M%S)"
./demo.sh create "$RUN_ID"
./demo.sh compare "$RUN_ID"
./demo.sh delete "$RUN_ID"
```

클러스터 생성에는 AWS 비용이 발생합니다. 생성이나 비교가 중단되어도 같은 run ID로 `delete`를 실행합니다. 비교 스크립트는 호출자 ARN과 실제 객체 본문을 대조합니다.

### 서울 리전 실측 결과

2026년 11월 20일, 서울 리전(`ap-northeast-2`)의 전용 EKS 1.35 클러스터에서 비교했습니다. Amazon Linux 2023 노드에서 IMDSv2 필수 및 응답 hop limit 1을 확인했습니다. 각 Job은 AWS CLI 2.35.11로 STS `GetCallerIdentity`와 S3 `GetObject`를 실행했습니다.

| Pod | 노드 정책 회수 전 | 노드 정책 회수 후 |
| --- | --- | --- |
| 레거시 | 노드 역할 · 읽기 성공 | 노드 역할 · 읽기 거부 |
| IRSA | IRSA 역할 · 읽기 성공 | IRSA 역할 · 읽기 성공 |
| Pod Identity | Pod Identity 역할 · 읽기 성공 | Pod Identity 역할 · 읽기 성공 |

레거시 Job은 회수 후에도 `GetCallerIdentity`에서 노드 역할로 식별됩니다. 노드 자격 증명은 계속 발급되지만, 그 자격 증명으로 보낸 객체 읽기 요청은 더 이상 허용되지 않습니다. 두 워크로드 Job은 자체 IAM 정책으로 같은 객체를 계속 읽었습니다. IAM 변경 전파 중에는 레거시 결과가 즉시 바뀌지 않아 새 Job에서 다시 확인했습니다.

## 문제 해결

- **노드 역할이 표시됨**. 새 Pod를 생성했는지, 올바른 ServiceAccount를 참조하는지, IRSA 주석 또는 정확한 association이 있는지 확인합니다. SDK 버전, 기본 공급자 체인, Pod에 주입된 환경 변수 이름을 점검합니다.
- **IRSA에서 토큰 교환 실패**. 토큰의 issuer에 대응하는 IAM provider, `aud`·`sub` 신뢰 조건, STS 도달 가능성을 확인합니다.
- **Pod Identity에서 자격 증명 조회 실패**. 해당 노드의 Agent, EKS Auth 통신, 노드 IAM 권한, association 전파, 요청 태그에 대한 역할 신뢰 정책을 확인합니다.
- **기대 역할인데 S3에서 거부됨**. 역할 신원과 리소스 접근은 별개입니다. 객체 ARN, 버킷 정책, SCP(Service Control Policy), 권한 경계, VPC 엔드포인트 정책을 확인합니다. AWS KMS(Key Management Service) 키로 서버 측 암호화(SSE-KMS)한 객체라면 키에 대한 권한을 확인합니다.
