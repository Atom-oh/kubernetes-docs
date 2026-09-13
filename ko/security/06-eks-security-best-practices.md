# EKS 보안 모범 사례

> **검토 기준**: 현재 AWS 문서, Kubernetes 1.35 API 스키마, Terraform 1.15.7 / AWS provider 6.64.0. 실제 클러스터 배포는 실행하지 않았습니다.
> **마지막 업데이트**: 2026년 9월 13일

Amazon EKS 환경에서의 보안 모범 사례를 다룹니다. IAM 통합부터 네트워크 보안, 런타임 보호까지 EKS 클러스터를 안전하게 운영하는 방법을 상세히 알아봅니다.

## 목차

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Security Groups for Pods](#security-groups-for-pods)
4. [VPC 엔드포인트](#vpc-엔드포인트)
5. [컨트롤 플레인 로깅](#컨트롤-플레인-로깅)
6. [GuardDuty EKS Protection](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [클러스터 암호화](#클러스터-암호화)
10. [노드 보안](#노드-보안)
11. [프라이빗 클러스터](#프라이빗-클러스터)
12. [멀티테넌시 패턴](#멀티테넌시-패턴)

---

## IRSA (IAM Roles for Service Accounts)

### IRSA 개요

IRSA(IAM Roles for Service Accounts)는 Kubernetes ServiceAccount에 IAM 역할을 연결하여 Pod가 AWS 서비스에 안전하게 접근할 수 있게 합니다.

Kubernetes API 서버가 projected ServiceAccount 토큰을 발급합니다. SDK는 이를 STS AssumeRoleWithWebIdentity로 교환하고, STS가 IAM OIDC provider에 연결된 issuer/JWKS와 역할 신뢰 조건을 검증한 뒤 임시 자격 증명을 제공합니다. IAM에 등록한 OIDC provider 오브젝트 자체가 토큰을 발급하는 실행 프록시는 아닙니다.


### IRSA 설정

다음은 운영자용 예시이며 실행하지 않았습니다. 실제 Region·클러스터·버킷 소유 계정·경로·정책 ARN을 일치시키고 애플리케이션 이미지를 검토한 버전/digest로 교체합니다. 지역이 다른 OIDC issuer나 추측한 eksctl 생성 역할 ARN을 섞지 않습니다.



```bash
# 1. OIDC Provider 생성 (클러스터당 한 번)
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. IAM 정책 생성
cat <<'EOF' > s3-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        },
        "StringLike": {
          "s3:prefix": [
            "app-data",
            "app-data/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket/app-data/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        }
      }
    }
  ]
}
EOF

aws iam create-policy \
    --policy-name S3ReadPolicy \
    --policy-document file://s3-policy.json

# 3. IAM ServiceAccount 생성
eksctl create iamserviceaccount \
    --name s3-reader-sa \
    --namespace production \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy \
    --approve
```

### IRSA 사용

```yaml
# eksctl이 만든 ServiceAccount를 재사용하며 생성된 역할 ARN을 추측하지 않습니다.
# Pod에서 ServiceAccount 사용
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
  namespace: production
spec:
  serviceAccountName: s3-reader-sa
  containers:
  - name: app
    image: public.ecr.aws/aws-cli/aws-cli:replace-with-reviewed-version
    command: ["aws", "s3", "ls", "s3://replace-with-owned-bucket/app-data/"]
    # AWS SDK가 자동으로 IRSA 토큰 사용
```

### IRSA 트러스트 정책

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:production:s3-reader-sa",
                    "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

### IRSA 모범 사례

```yaml
# 1. 최소 권한 원칙
# 각 ServiceAccount에 필요한 최소 권한만 부여

# 2. 네임스페이스별 ServiceAccount 분리
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dynamodb-reader
  namespace: orders-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/orders-dynamodb-role
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-uploader
  namespace: media-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/media-s3-role
```

---

## EKS Pod Identity

### Pod Identity 개요

EKS Pod Identity는 별도의 자격 증명 전달 방식입니다. 실제 플랫폼·SDK 지원, 신뢰 경계, 운영 요구에 따라 IRSA와 선택하며 IRSA를 폐기하거나 모든 워크로드의 보안을 자동 향상시키는 것은 아닙니다.

Pod의 지원 SDK가 로컬 agent 경로를 이용하고 agent는 EKS Auth API를 통해 association·역할에 맞는 임시 자격 증명을 가져옵니다. 역할이 다른 계정에 있거나 역할 체인을 사용하면 현재 지원 방식·신뢰·세션 태그 조건을 별도로 검증합니다.


### Pod Identity 설정

EKS Auto Mode에는 agent가 내장됩니다. 그 외 지원 플랫폼은 클러스터와 호환되는 현재 애드온 버전을 확인하고 기존 설치 소유자를 통해 관리합니다. 다음 명령의 계정·클러스터·namespace·ServiceAccount를 실제 값으로 바꾸며, IAM 역할 신뢰에는 의도한 namespace/ServiceAccount 세션 태그 조건을 추가합니다. 애드온 설치와 association만으로 SDK 호환성·자격 증명 우선순위·네트워크 접근까지 검증되지는 않습니다.



```bash
# 1. Pod Identity Agent 애드온 설치
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent

# 2. IAM 역할 생성 (Pod Identity용 트러스트 정책)
cat <<'EOF' > trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/kubernetes-namespace": "production",
          "aws:RequestTag/kubernetes-service-account": "my-app-sa"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
    --role-name my-pod-role \
    --assume-role-policy-document file://trust-policy.json

# 3. 정책 연결
aws iam attach-role-policy \
    --role-name my-pod-role \
    --policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy

# 4. Pod Identity Association 생성
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/my-pod-role
```

### Pod Identity 사용

```yaml
# ServiceAccount (어노테이션 불필요)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
---
# Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: production
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
    # AWS SDK가 자동으로 Pod Identity 사용
```

### IRSA vs Pod Identity 비교

| 특성 | IRSA | EKS Pod Identity |
|------|------|------------------|
| **설정 복잡도** | OIDC Provider 필요 | 간단 (API 호출) |
| **트러스트 정책** | 정확한 OIDC issuer·audience·subject | 서비스 주체와 제한 조건 |
| **역할 재사용** | 클러스터별 수정 필요 | 여러 클러스터에서 재사용 |
| **감사 로깅** | CloudTrail (SA 수준) | CloudTrail (Pod 수준) |
| **세션 태그** | EKS Pod Identity와 동일한 자동 태그 동작으로 가정하지 않음 | 문서화된 태그 지원; 비활성화·역할 연결 동작 확인 |
| **선택** | 지원 플랫폼·OIDC 신뢰·운영 방식 | 지원 플랫폼·association·agent/SDK 방식 |

---

## Security Groups for Pods

### 개요

Security Groups for Pods는 Pod에 직접 VPC Security Group을 적용하여 네트워크 수준의 격리를 제공합니다.

### 사전 요구사항

```bash
# 설치된 CNI와 현재 플랫폼·버전 요구사항 확인
kubectl describe daemonset aws-node -n kube-system | grep Image

# Security Groups for Pods 활성화
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# 실제 이름을 확인한 EKS 클러스터 역할에 연결
aws iam attach-role-policy \
    --role-name "$EKS_CLUSTER_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

Security Groups for Pods는 trunking을 지원하는 인스턴스와 CNI 모드가 필요합니다. 현재 문서는 Windows와 EKS Auto Mode를 제외하며 모든 Nitro 인스턴스가 지원되는 것도 아닙니다. VPC Resource Controller 정책은 클러스터 역할에 연결합니다. 여러 보안 그룹의 허용 규칙은 교집합이 아니라 합쳐지므로 strict/standard 모드, DNS, probe, Load Balancer 동작을 확인합니다.

### SecurityGroupPolicy 설정

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  # 대상 Pod 선택
  podSelector:
    matchLabels:
      app: database
  # 적용할 Security Group
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0  # 데이터베이스 SG
      - sg-0987654321fedcba0  # 공통 모니터링 SG
```

### Terraform으로 Security Group 구성

허용할 DB·복제·모니터링 포트와 실제 source SG를 정하고, 여러 SG의 규칙이 합쳐진다는 점을 고려합니다. SecurityGroupPolicy와 source/target SG, VPC, Pod 선택자가 일치해야 합니다. 기존 선언은 정의되지 않은 module/SG 참조와 무제한 egress를 포함해 완전한 배포 구성이 아니었습니다.

SG의 응답 트래픽은 stateful 처리되지만 앱이 새로 시작하는 DNS·DB·외부 연결의 egress는 별도 요구입니다. 필요한 대상을 제한하고 CNI enforcing mode 및 NetworkPolicy와 함께 연결을 시험합니다. 이 감사에서는 SG·Pod ENI를 생성하거나 네트워크 차단을 시험하지 않았습니다.

---

## VPC 엔드포인트

### 프라이빗 EKS를 위한 VPC 엔드포인트

Kubernetes API의 private endpoint와 AWS 서비스 API의 PrivateLink endpoint는 서로 다릅니다. `eks` VPC endpoint가 kubectl의 Kubernetes API 연결을 대체하지 않습니다. 실제 노드·워크로드·운영자 경로별로 필요한 서비스만 선택하고 Region 지원·DNS·보안 그룹·라우팅·endpoint policy·IAM을 함께 확인합니다.

| 용도 | 경로 |
|---|---|
| Kubernetes API | 클러스터의 private API endpoint와 연결된 네트워크 |
| EKS 관리 API | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| IRSA STS 교환 | `com.amazonaws.<region>.sts`; SDK도 regional STS를 사용 |
| OIDC discovery/JWKS | 현재 문서의 `com.amazonaws.<region>.oidc-eks`; STS endpoint와 별도 |
| ECR 이미지 | `ecr.api`, `ecr.dkr` interface와 이미지 레이어용 S3 경로 |
| 추가 서비스 | 실제 사용하는 EC2, Logs, ELB, Auto Scaling, SSM 등의 지원 endpoint |

현재 EKS private-cluster 문서는 Route 53 API의 `com.amazonaws.route53`도 나열합니다. DNS 조회와 Route 53 관리 API 호출을 구분하고 지원 Region·서비스 이름을 확인합니다. 기존 `ec2messages`를 모든 Region에 무조건 생성하지 않으며 사용하는 SSM Agent와 메시징 endpoint 요구를 확인합니다.

### Terraform VPC 엔드포인트 설정

[완전한 Terraform 예제](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints)는 `논리 이름 → 정확한 서비스 이름` 맵을 받습니다. 기존 `split(...)[4]`는 이름 길이에 따라 범위를 벗어나거나 잘못된 태그를 만들었습니다. 이제 `each.key`로 태그를 만듭니다.

기존 subnet·route table·허용 client SG와 검토한 S3 endpoint policy를 입력합니다. HTTPS는 명시한 client SG에서만 허용합니다. S3 정책은 ECR 레이어 버킷과 필요한 버킷을 허용해야 하며 endpoint policy 자체가 IAM 접근 권한을 부여하지 않습니다. Terraform 1.15.7/AWS provider 6.64.0으로 schema validate만 수행했고 plan/apply나 리소스 생성은 하지 않았습니다.

---

## 컨트롤 플레인 로깅

### EKS 컨트롤 플레인 로그 유형

지원 유형은 `api`, `audit`, `authenticator`, `controllerManager`, `scheduler`입니다. kubelet·컨테이너 로그는 별도 수집 경로입니다. 로그 그룹은 `/aws/eks/<cluster-name>/cluster`이며 Region·보존·접근·암호화·민감 정보 처리·수집 비용을 운영 정책에 맞게 정합니다.

### 로깅 활성화

기존 클러스터의 IaC 소유자와 변경을 조정합니다. 다음은 소유한 클러스터에 적용하는 예시이며 감사 중 실행하지 않았습니다. 변경은 비동기이므로 반환된 update ID로 `describe-update`의 성공/실패를 확인하고 실제 로그 유입도 별도로 확인합니다. 로그를 켜기 위해 새 클러스터 리소스를 선언하거나 API 공개 범위를 바꿀 필요는 없습니다.

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### CloudWatch Logs Insights 쿼리

다음은 **서로 별개의 Logs Insights QL 쿼리**입니다. 선택한 로그 그룹에서 실제 필드·시간 범위를 확인합니다. 첫 쿼리는 문자열 탐색이며 모든 인증 실패를 증명하는 완전한 탐지 규칙은 아닙니다. 이번 검토에서 관리형 쿼리 엔진은 실행하지 않았습니다.

인증 로그 오류 탐색

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

선택한 주체의 호출

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "REPLACE_WITH_REVIEWED_USERNAME"
| sort @timestamp desc
| limit 50
```

권한 거부

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

Secret API 접근

```text
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.name, responseStatus.code
| filter @logStream like /audit/
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

---

## GuardDuty EKS Protection

### GuardDuty EKS Protection 개요

GuardDuty의 EKS 감사 로그 분석, Runtime Monitoring, 기본 데이터 소스를 구분합니다. EKS 감사 분석은 Kubernetes API 활동을 다루며 사용자가 CloudWatch 컨트롤 플레인 로깅을 켜야만 활성화되는 기능이 아닙니다. Runtime Monitoring은 보안 agent와 실제 coverage가 필요합니다.

현재 Runtime Monitoring 문서는 EC2 기반 EKS와 EKS Auto Mode를 지원하고 EKS Hybrid Nodes·EKS Fargate는 제외합니다. ECS Fargate 지원을 EKS Fargate 지원으로 해석하지 않습니다. 조직 위임 관리자·Region별 detector·플랫폼·비용·agent 관리 소유자를 확인합니다.

### GuardDuty 활성화

다음은 기존 detector에 적용할 **설정 페이로드 예시**입니다. 실제 계정에서 실행하지 않았습니다. `RUNTIME_MONITORING`은 EKS를 포함하므로 `EKS_RUNTIME_MONITORING`과 동시에 지정하면 오류입니다. 이미 구성한 detector를 확인하며 무조건 create-detector 후 첫 번째 ID를 선택하지 않습니다. 자동 agent 관리가 만드는 리소스·권한과 수집 coverage도 확인해야 합니다.

```json
[
  {"Name": "EKS_AUDIT_LOGS", "Status": "ENABLED"},
  {
    "Name": "RUNTIME_MONITORING",
    "Status": "ENABLED",
    "AdditionalConfiguration": [
      {"Name": "EKS_ADDON_MANAGEMENT", "Status": "ENABLED"}
    ]
  }
]
```

### GuardDuty EKS Finding 유형

실제 type은 전술 접두사를 포함합니다. 고정된 임의 심각도 표 대신 Finding의 `severity`, 리소스, 계정·Region, 수집 범위와 공식 설명을 함께 확인합니다.

| 실제 type 예시 | 범위 |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Kubernetes API 활동 |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | Kubernetes 권한 조회 이상 |
| `Execution:Runtime/ReverseShell` | agent가 관측한 런타임 동작 |
| `CryptoCurrency:Runtime/BitcoinTool.B` | 런타임 채굴 관련 탐지 |

### Finding 대응 자동화

다음 EventBridge 패턴은 Kubernetes/Runtime type을 라우팅합니다. 기존 `prefix: Kubernetes`와 `prefix: Runtime`은 실제 전술 접두사 때문에 일치하지 않았습니다. 공식 AWS Event Ruler 2.2.0으로 6개 일치/비일치 사례와 기존 실패를 검증했습니다.

패턴에는 통보·격리 target이 없습니다. Runtime Finding은 EKS 외 리소스일 수도 있으므로 실제 리소스 메타데이터를 확인한 뒤 승인된 대응 경로로 전달합니다. target 역할·권한·재시도·DLQ·중복 처리를 별도로 구성해야 합니다. `boto3.client("eks")`를 만드는 것만으로 Pod가 격리되지 않으며 네트워크 격리는 CNI 정책, 호스트·클라우드 통제와 권한 있는 Kubernetes 작업의 설계가 필요합니다.

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "type": [
      {"wildcard": "*:Kubernetes/*"},
      {"wildcard": "*:Runtime/*"}
    ]
  }
}
```

---

## Amazon Inspector

### Inspector 컨테이너 이미지 스캔

ECR enhanced scanning은 Amazon Inspector와 연동해 지원하는 이미지의 패키지 취약점을 검사합니다. 실행 중인 이미지 사용 정보와 런타임 동작 탐지는 서로 다릅니다. Inspector가 임의의 Kubernetes 매니페스트·IAM 정책·실시간 네트워크를 같은 이미지 스캔으로 검사하는 것은 아닙니다.

레지스트리 스캔 설정 변경은 계정·Region과 저장소 필터 범위에 영향을 주므로 기존 소유자와 적용 범위를 확인합니다. `latest` 대신 실제 배포할 digest를 선택합니다. 새 CVE·지원 이미지·재스캔 적격성·스캔 실패를 계속 관리해야 하며 첫 스캔 통과가 이후 안전을 보장하지 않습니다.

### Inspector와 CI/CD 통합

[전체 스캔 게이트와 테스트](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security)는 정확한 registry/repository/digest, 완료 timestamp, 명시적 severity-count map을 확인합니다. continuous scan의 `ACTIVE` 상태만으로 초기 결과가 준비됐다고 판단하지 않습니다. 결과 없음·타임아웃·접근 거부·실패·알 수 없는 상태를 0건으로 처리하지 않습니다.

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST`는 빌드·푸시 후 레지스트리에서 확인한 `sha256:...` 값이어야 합니다. 예시 계정·저장소를 바꾸고 boto3를 설치합니다. 테스트는 실제 boto3/botocore Stubber와 가짜 시계로 수행해 AWS 요청·실제 대기 없이 12개 회귀 사례를 통과했습니다.

GitHub Actions에서는 승인한 OIDC trust의 역할 ARN, `permissions: id-token: write`, 읽기 최소 권한, ECR 로그인 출력의 registry 주소, 빌드한 digest 전달이 필요합니다. 정의되지 않은 `$ECR_REGISTRY`, 자격 증명 역할 없는 configure-aws-credentials, 고정 sleep 60초는 완전한 워크플로우가 아닙니다. 멀티 아키텍처 인덱스는 배포 대상 child digest별 스캔 정책을 정합니다. 예외 임계값·만료·재검토 책임과 결과의 신선도 기준은 별도로 관리합니다.

Enhanced finding 이벤트는 `aws.inspector2` / `Inspector2 Finding`입니다. Basic ECR 스캔 이벤트와 혼동하지 않습니다. [검증한 알림 CloudFormation 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)는 별도 문서의 키·권한·수신자 요건을 따릅니다.

---

## CIS Kubernetes Benchmark

### kube-bench 실행

검토한 upstream은 kube-bench **0.16.0**입니다. 이 릴리스에는 `eks-1.5.0`, `eks-1.7.0`, `eks-1.8.0` 등이 있고 기존 예제의 `eks-1.4.0` 디렉터리는 없습니다. 가장 큰 번호를 무조건 선택하지 말고 조직이 요구하는 CIS EKS 판·클러스터/노드 OS·도구 지원을 일치시킵니다. upstream job 예제도 `latest`와 1.5.0을 사용하므로 그대로 적용하지 말고 검토한 이미지 digest·프로필·호스트 마운트·권한을 고정합니다.

검사는 호스트 PID/파일 접근이 필요한 경우가 있으며 일반 앱 네임스페이스의 Restricted 정책과 충돌할 수 있습니다. 승인된 스캐너 전용 운영 경로에서 실행하고, 실제 검사한 노드와 제외/경고 항목을 기록합니다. 이 감사는 실제 노드에 kube-bench를 실행하지 않았습니다.

### CIS 벤치마크 주요 항목

CIS EKS 프로필의 실제 controlplane·node·policies·managedservices 항목을 확인합니다. 관리형 컨트롤 플레인의 내부 파일을 사용자가 직접 읽을 수 있다고 가정하지 않습니다. 노드 설정·RBAC·네트워크 정책·감사 같은 항목에도 자동/수동/해당 없음 구분이 필요합니다. 도구 통과율은 보안 인증서나 전체 침해 가능성 평가가 아닙니다.

### 자동화된 준수 검사

Job 하나는 스케줄된 노드 한 곳만 검사할 수 있습니다. 노드 그룹·OS·아키텍처·설정 차이를 포함하는 범위를 설계하고 결과에 cluster/node/image/profile/time을 남깁니다. 정기 실행은 host mount, service account, 필요한 읽기 권한, 중복 실행 제한, 완료/실패 상태와 결과 보존을 포함해야 합니다.

기존 CronJob은 호스트 마운트가 빠졌고 kube-bench 이미지에 AWS CLI가 있다고 가정했습니다. 결과 업로드가 필요하면 검토한 별도 uploader 또는 로그 수집 경로와 제한된 workload identity를 구성합니다. 스캔 실패 후 업로드 성공만으로 전체 Job을 성공 처리하지 않습니다.

---

## 클러스터 암호화

### EKS Secrets 암호화 (KMS)

EKS **1.28 이상은 모든 Kubernetes API 데이터에 AWS 소유 KMS 키를 사용하는 envelope encryption을 기본 제공**합니다. 고객 관리 키는 별도 요구에 따라 선택합니다. 고객 관리 키가 없다는 이유만으로 현재 EKS Secret이 평문 저장이라고 설명하지 않습니다.

고객 관리 키를 선택할 때는 클러스터 역할·KMS grant·키 정책·계정/Region·키 가용성·변경 절차를 함께 검토합니다. 키 비활성화·삭제는 가용성과 복구에 영향을 줄 수 있으며 단순 예시의 7일 삭제 창을 운영 표준으로 복사하지 않습니다. 키 정책의 `Resource: "*"`는 해당 키 정책 문맥의 의미가 있지만 이를 무조건 넓은 IAM 권한으로 재사용하지 않습니다. 실제 키 소유자·관리/사용 역할·조건과 IAM 위임 방식을 확인합니다.

저장 암호화는 허용된 API 조회나 침해된 앱의 값 사용을 차단하지 않습니다. 애플리케이션 자격 증명 교체·Secret 전달·재로딩은 별도의 [시크릿 관리](./05-secrets-management.md) 절차입니다. 이 장은 새 KMS 키·클러스터를 생성하거나 기존 키 연결을 변경하지 않았습니다.

---

## 노드 보안

### Bottlerocket OS

Bottlerocket는 컨테이너 호스트용 OS 선택지이며 OS 선택만으로 모든 워크로드의 보안이 완성되지는 않습니다. 클러스터 Kubernetes 버전·CPU 아키텍처·관리형 노드 그룹/Auto Mode·CNI·스토리지·agent의 지원 조합을 확인합니다. 관리형 노드 그룹의 bootstrap 병합 규칙을 따르고 기존 cluster/API/CA 설정을 임의로 덮어쓰지 않습니다.

업데이트·재시작·노드 교체, control/admin container 접근, SSM 권한, 이미지 출처와 복구 절차를 운영합니다. 기존 예제의 네트워크 버퍼 sysctl 변경은 그 자체로 보안 강화 근거가 아니었습니다. Terraform AMI 타입과 인스턴스 아키텍처가 맞아야 하며 이 장은 노드 그룹을 생성하거나 OS를 실행하지 않았습니다.

### 노드 보안 강화

제한된 노드 역할과 워크로드별 IRSA/Pod Identity를 분리합니다. IMDSv2와 메타데이터 접근 통제를 검토하되 hostNetwork·특권 Pod·노드 침해의 영향을 포함해야 합니다. IRSA를 사용한다는 사실만으로 노드 역할 접근이 자동 차단되지는 않습니다.

Pod에는 적합한 비루트 UID, 권한 상승 금지, capability drop, seccomp, 필요한 쓰기 볼륨을 포함한 읽기 전용 root filesystem을 적용하고 실제 앱 동작을 시험합니다. label selector나 toleration은 스케줄링 조건이며 OS 검증·권한 부여 자체가 아닙니다. `node.kubernetes.io/os: bottlerocket` 같은 사용자 라벨을 신뢰 경계로 취급하지 말고, 보안 배치 정책에는 관리자가 통제하는 라벨과 NodeRestriction 등 실제 보호를 검토합니다.

---

## 프라이빗 클러스터

### 완전 프라이빗 EKS 구성

private Kubernetes API는 VPC 또는 연결된 관리 네트워크의 DNS·라우팅·보안 그룹과 IAM 인증/Kubernetes 권한이 모두 필요합니다. 인터넷에서 직접 접근할 수 없다는 사실이 연결된 네트워크의 모든 사용자에게 접근 권한을 주는 것은 아닙니다.

API 공개 범위를 바꾸기 전에 현재 운영자·CI·복구 경로에서 private API 접근을 시험합니다. 기존 IaC 소유자를 통해 `endpoint_private_access`/`endpoint_public_access`를 관리하고 무심코 새 클러스터 리소스를 선언하지 않습니다. 워커 bootstrap과 필요한 AWS API·이미지·패키지 접근 경로도 별도로 설계합니다. 외부 인터넷이 없는 구성과 private API 설정은 동일한 개념이 아닙니다.

### Bastion 또는 VPN 접근

VPN·Direct Connect·적절히 연결된 네트워크 또는 제한된 관리 호스트를 사용할 수 있습니다. Client VPN의 subnet association만으로 연결이 완성되지는 않습니다. 서버/클라이언트 인증서, 클라이언트 CIDR 비중복, authorization rule, 경로와 반환 경로, DNS, SG, 연결 로그, IAM/Kubernetes 권한을 함께 구성해야 합니다.

Bastion은 별도 보안·패치·접근·감사 책임이 있는 선택지입니다. 넓은 SSH 인바운드나 API 전체 관리자 권한을 기본값으로 두지 않습니다. 이 장은 VPN·bastion·인증서를 배포하지 않았습니다.

---

## 멀티테넌시 패턴

### 네임스페이스 기반 멀티테넌시

namespace는 공유 클러스터에서의 관리 범위이며 상호 적대적 테넌트의 완전한 격리 경계가 아닙니다. PSS·RBAC·quota·NetworkPolicy·스토리지·workload identity·노드/관리자 경계를 함께 설계합니다. 아래 예시는 Kubernetes 1.35 정책 기준이며 실제 클러스터 버전과 정책 호환성을 검토해야 합니다.

같은 namespace Pod만 기본 허용하고 DNS는 kube-system **및** kube-dns Pod selector를 같은 peer에 넣어 제한합니다. UDP와 TCP 53을 모두 고려합니다. 실제 DNS 라벨·NodeLocal DNS·CNI enforcement·다른 가산 정책·hostNetwork/노드 트래픽은 따로 확인합니다. 온라인 연결 시험은 실행하지 않았습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
    services.loadbalancers: "2"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-a-limits
  namespace: tenant-a
spec:
  limits:
    - type: Container
      default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      min:
        cpu: 50m
        memory: 64Mi
      max:
        cpu: "2"
        memory: 4Gi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-a-isolation
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector: {}
  egress:
    - to:
        - podSelector: {}
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
---
# Workload administration is sensitive, even when namespace-scoped.
# The group cannot change Namespace labels, RoleBindings or this NetworkPolicy.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workload-admin
  namespace: tenant-a
rules:
  - apiGroups: [""]
    resources: [pods, services, configmaps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [apps]
    resources: [deployments, statefulsets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-workload-admins
  namespace: tenant-a
subjects:
  - kind: Group
    name: tenant-a-workload-admins
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-admin
  apiGroup: rbac.authorization.k8s.io
```

### RBAC 멀티테넌시

예제 workload admin은 Namespace 레이블·RoleBinding·NetworkPolicy·Secret API 권한을 직접 변경하지 못합니다. 하지만 Pod/Deployment 생성 권한은 namespace의 Secret·ServiceAccount·볼륨을 간접 사용하게 할 수 있습니다. “Secret get을 제외했으므로 시크릿에 접근 불가”라고 판단하지 않습니다. 강한 격리가 필요하면 별도 클러스터/계정 등 더 넓은 경계를 검토합니다.

EKS 사용자 접근은 현재 access entry와 namespace 범위 access policy 또는 Kubernetes 그룹/RBAC를 검토합니다. `aws-auth` ConfigMap은 기존 호환 경로이며 항상 유일한 통합 방법이 아닙니다. API 인증 mode 변경에는 되돌릴 수 없는 전환 제약이 있으므로 기존 관리자·노드 매핑·복구 경로를 검증한 뒤 이전합니다. EKS access policy와 Kubernetes RBAC는 각각 허용할 수 있으므로 한쪽의 권한 부재가 다른 쪽 허용을 거부하는 것은 아닙니다. 일반 개발자에게 `system:masters`를 예시 기본값으로 부여하지 않습니다.

---

## 요약

EKS 보안 모범 사례의 핵심:

1. **IAM 통합**: IRSA 또는 Pod Identity로 AWS 서비스 접근
2. **네트워크 보안**: Security Groups for Pods, VPC 엔드포인트
3. **로깅 및 모니터링**: 컨트롤 플레인 로그, GuardDuty
4. **이미지 보안**: Amazon Inspector, ECR 스캐닝
5. **규정 준수**: CIS Benchmark, kube-bench
6. **암호화**: KMS를 사용한 Secrets 암호화
7. **노드 보안**: Bottlerocket OS, 최소 권한
8. **멀티테넌시**: 네임스페이스 격리, RBAC, ResourceQuota

---

## 참고 자료

- [EKS Security Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/security.html)
- [Amazon EKS User Guide - Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [AWS Security Blog - EKS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
- [CIS Amazon EKS Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

- [security-groups-for-pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [sgpp](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [private-clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [configure-sts-endpoint](https://docs.aws.amazon.com/eks/latest/userguide/configure-sts-endpoint.html)
- [how-runtime-monitoring-works-eks](https://docs.aws.amazon.com/guardduty/latest/ug/how-runtime-monitoring-works-eks.html)
- [kubernetes-protection](https://docs.aws.amazon.com/guardduty/latest/ug/kubernetes-protection.html)
- [API_DescribeImageScanFindings](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_DescribeImageScanFindings.html)
- [image-scanning-enhanced](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning-enhanced.html)
- [eventbridge-integration](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [access-entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [guardduty_finding-types-kubernetes](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-kubernetes.html)
- [findings-runtime-monitoring](https://docs.aws.amazon.com/guardduty/latest/ug/findings-runtime-monitoring.html)
- [API_UpdateDetector](https://docs.aws.amazon.com/guardduty/latest/APIReference/API_UpdateDetector.html)
- [guardduty_findings_eventbridge](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html)
