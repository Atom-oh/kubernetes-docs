# Amazon EKS 보안

> **지원 버전**: Amazon EKS 1.31, 1.32, 1.33  
> **마지막 업데이트**: 2026년 7월 3일

Amazon EKS(Elastic Kubernetes Service)에서 워크로드를 안전하게 실행하기 위해서는 다양한 보안 계층과 모범 사례를 이해하고 구현해야 합니다. 이 문서에서는 EKS 클러스터의 보안을 강화하기 위한 주요 개념, 구성 요소 및 모범 사례를 다룹니다.

## 목차

1. [EKS 보안 개요](#eks-보안-개요)
2. [최신 보안 트렌드 (2023)](#최신-보안-트렌드-2023)
3. [IAM 및 인증](#iam-및-인증)
4. [OIDC Provider 심화](#oidc-provider-심화)
5. [EKS Pod Identity](#eks-pod-identity)
6. [Cluster Endpoint 접근 제어](#cluster-endpoint-접근-제어)
7. [네트워크 보안](#네트워크-보안)
8. [포드 보안](#포드-보안)
9. [Bottlerocket 및 읽기 전용 OS](#bottlerocket-및-읽기-전용-os)
10. [IAM 권한 경계](#iam-권한-경계)
11. [암호화 및 비밀 관리](#암호화-및-비밀-관리)
12. [컴플라이언스 및 감사](#컴플라이언스-및-감사)
13. [보안 모니터링 및 탐지](#보안-모니터링-및-탐지)
14. [EKS 보안 모범 사례](#eks-보안-모범-사례)
15. [금융 서비스를 위한 EKS 보안 고려사항](#금융-서비스를-위한-eks-보안-고려사항)

## EKS 보안 개요

Amazon EKS는 AWS와 Kubernetes의 보안 기능을 결합하여 다층적인 보안 아키텍처를 제공합니다. EKS 보안은 다음과 같은 주요 영역으로 구성됩니다:

- **공동 책임 모델**: AWS는 EKS 컨트롤 플레인의 보안을 관리하고, 고객은 워커 노드, 컨테이너, 애플리케이션의 보안을 책임집니다.
- **인프라 보안**: VPC, 서브넷, 보안 그룹 등의 네트워크 인프라 보안
- **클러스터 보안**: Kubernetes API 서버 접근 제어, RBAC, 서비스 계정
- **워크로드 보안**: 컨테이너 이미지 보안, 런타임 보안, 네트워크 정책

### EKS 보안 아키텍처

![AWS가 책임지는 컨트롤 플레인·etcd·KMS·IAM 영역과 고객이 책임지는 워커 노드·파드·보안 그룹·서비스 계정·네트워크 정책·Secrets 영역이 IAM 인증과 암호화된 통신으로 연결되는 EKS 공동 책임 모델을 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-0.html)

## 최신 보안 트렌드 (2023)

Kubernetes 및 EKS 보안 영역에서의 최신 트렌드와 권장사항은 다음과 같습니다:

### 1. 제로 트러스트 아키텍처 (Zero Trust Architecture)

전통적인 경계 기반 보안 모델에서 벗어나, 모든 접근을 기본적으로 신뢰하지 않고 지속적으로 검증하는 접근 방식입니다.

![암호화, 최소 권한, 지속적 검증, 접근 제어, 트래픽 검사라는 다섯 가지 제로 트러스트 원칙이 서비스 메시(Istio) mTLS·IRSA·AWS Security Hub·OPA/Gatekeeper·네트워크 정책이라는 EKS 구현 방법으로 각각 연결된다.](../.gitbook/assets/ko-eks-05-eks-security-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-1.html)

EKS에서 제로 트러스트 구현:
- **서비스 메시**: Istio 또는 AWS App Mesh를 사용한 서비스 간 mTLS 통신
- **IAM Roles for Service Accounts (IRSA)**: 세분화된 권한 관리
- **네트워크 정책**: 필요한 통신만 허용하는 기본 거부 정책
- **OPA/Gatekeeper**: 정책 기반 접근 제어
- **AWS Security Hub**: 지속적인 보안 상태 모니터링

### 2. 공급망 보안 (Supply Chain Security)

소프트웨어 공급망 공격이 증가함에 따라, 컨테이너 이미지부터 배포까지 전체 파이프라인의 보안이 중요해졌습니다.

주요 구현 방법:
- **SLSA (Supply-chain Levels for Software Artifacts)** 프레임워크 채택
- **이미지 서명 및 검증**: Cosign, Notary v2
- **SBOM (Software Bill of Materials)** 생성 및 관리: Syft, Grype
- **이미지 스캐닝**: Amazon ECR 이미지 스캐닝, Trivy, Clair
- **GitOps 보안**: 서명된 커밋, 보안 파이프라인

### 3. 런타임 보안 및 위협 탐지

컨테이너 런타임 보안이 중요해지면서 다음과 같은 기술이 주목받고 있습니다:

- **eBPF 기반 보안 모니터링**: Cilium, Falco
- **AWS GuardDuty EKS Protection**: 런타임 위협 탐지
- **Kubernetes Audit 로그 분석**: CloudWatch Logs Insights
- **이상 행동 탐지**: Amazon Detective
- **컨테이너 이스케이프 방지**: gVisor, Kata Containers

### 4. 정책 기반 보안 (Policy as Code)

보안 정책을 코드로 관리하여 일관성과 자동화를 향상시키는 접근 방식입니다:

- **OPA (Open Policy Agent)**: 범용 정책 엔진
- **Kyverno**: Kubernetes 네이티브 정책 관리
- **AWS Config**: 규정 준수 모니터링
- **Terraform Sentinel**: IaC 정책 적용
- **AWS CloudFormation Guard**: IaC 정책 검증

## IAM 및 인증

### EKS의 인증 메커니즘

Amazon EKS는 다음과 같은 인증 메커니즘을 제공합니다:

1. **AWS IAM 인증자**: AWS IAM 자격 증명을 사용하여 Kubernetes API 서버에 인증합니다.
2. **OIDC 제공자 통합**: 외부 OIDC 제공자(예: Active Directory, Okta, Auth0)와 통합하여 사용자 인증을 관리합니다.
3. **서비스 계정 IAM 역할**: Kubernetes 서비스 계정에 AWS IAM 역할을 연결하여 파드가 AWS 서비스에 안전하게 액세스할 수 있게 합니다.

![DevOps·개발자·CI/CD·파드가 IAM 인증자, OIDC 제공자, IRSA를 거쳐 Kubernetes API 서버와 AWS 리소스에 접근하는 EKS의 세 가지 인증 경로를 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-2.html)

### IAM 역할 및 정책 구성

#### EKS 클러스터 역할

EKS 클러스터를 생성할 때 필요한 최소 권한:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:CreateCluster",
        "eks:DescribeCluster",
        "eks:UpdateClusterConfig",
        "eks:DeleteCluster"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "eks.amazonaws.com"
        }
      }
    }
  ]
}
```

#### EKS Access Entry

EKS Access Entry는 aws-auth ConfigMap을 대체하는 새로운 방식으로, EKS 클러스터에 대한 IAM 사용자 및 역할 액세스를 관리합니다. Access Entry는 다음과 같은 장점을 제공합니다:

- AWS 관리형 솔루션으로 안정성 향상
- 선언적 API를 통한 관리
- 버전 관리 및 감사 기능
- 노드 IAM 역할과 사용자/역할 액세스 관리 분리

```bash
# 클러스터에 대한 Access Entry 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --access-config authenticationMode=API_AND_CONFIG_MAP

# IAM 역할에 대한 Access Entry 생성
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/DevTeamRole \
  --username dev-team \
  --kubernetes-groups dev-team

# IAM 사용자에 대한 Access Entry 생성
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/admin \
  --username admin \
  --kubernetes-groups system:masters

# Access Entry 목록 조회
aws eks list-access-entries --cluster-name my-cluster
```

> **참고**: EKS Access Entry는 2023년에 도입된 기능으로, aws-auth ConfigMap보다 더 안정적이고 관리하기 쉬운 방법을 제공합니다. 기존 클러스터는 두 방식을 모두 지원하는 하이브리드 모드로 마이그레이션할 수 있습니다.

### IRSA(IAM Roles for Service Accounts)

IRSA를 사용하면 Kubernetes 서비스 계정에 AWS IAM 역할을 연결하여 파드가 AWS 서비스에 안전하게 액세스할 수 있습니다.

#### IRSA 설정 단계

1. EKS 클러스터에 OIDC 제공자 생성:

```bash
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

2. IAM 역할 및 정책 생성:

```bash
eksctl create iamserviceaccount \
  --name s3-reader \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

3. 서비스 계정을 파드에 연결:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
spec:
  serviceAccountName: s3-reader
  containers:
  - name: app
    image: amazonlinux:2
    command: ['sh', '-c', 'aws s3 ls']
```

## OIDC Provider 심화

EKS에서 OIDC(OpenID Connect) Provider는 Kubernetes 서비스 계정과 AWS IAM 역할을 연결하는 핵심 메커니즘입니다. 이 섹션에서는 OIDC 신뢰 관계의 동작 원리와 토큰 교환 메커니즘을 심층적으로 살펴봅니다.

### OIDC 신뢰 관계 동작 원리

EKS 클러스터를 생성하면 AWS는 클러스터별로 고유한 OIDC 발급자(Issuer) URL을 생성합니다. 이 URL은 IAM Identity Provider로 등록되어 Kubernetes 서비스 계정 토큰을 AWS IAM 자격 증명으로 교환할 수 있게 합니다.

![파드가 Kubernetes API 서버에서 받은 서비스 계정 JWT를 AWS STS에 AssumeRoleWithWebIdentity로 제시하면 STS가 EKS OIDC Provider의 JWKS로 서명을 검증하고 IAM 역할의 신뢰 정책을 확인한 뒤 임시 자격 증명을 발급하고, 파드가 그 자격 증명으로 AWS 서비스 API를 호출하는 순서를 보여주는 시퀀스 다이어그램이다.](../.gitbook/assets/ko-eks-05-eks-security-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-3.html)

### STS AssumeRoleWithWebIdentity 흐름

IRSA의 핵심은 `AssumeRoleWithWebIdentity` API 호출입니다. 이 API는 다음 단계로 동작합니다:

1. **토큰 발급**: Kubernetes API 서버가 서비스 계정에 대한 JWT 토큰 발급
2. **토큰 전달**: 파드 내 애플리케이션이 projected volume에서 토큰 읽기
3. **역할 전환**: AWS SDK가 STS에 토큰과 함께 역할 전환 요청
4. **토큰 검증**: STS가 OIDC Provider의 JWKS(JSON Web Key Set)로 토큰 서명 검증
5. **정책 평가**: IAM 역할의 신뢰 정책에서 OIDC 조건 확인
6. **자격 증명 반환**: 임시 자격 증명(Access Key, Secret Key, Session Token) 발급

### 토큰 교환 메커니즘

서비스 계정 토큰은 다음 정보를 포함합니다:

```json
{
  "aud": ["sts.amazonaws.com"],
  "exp": 1234567890,
  "iat": 1234567800,
  "iss": "https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE",
  "kubernetes.io": {
    "namespace": "default",
    "pod": {
      "name": "my-pod",
      "uid": "xxx-xxx-xxx"
    },
    "serviceaccount": {
      "name": "my-service-account",
      "uid": "xxx-xxx-xxx"
    }
  },
  "sub": "system:serviceaccount:default:my-service-account"
}
```

### OIDC 엔드포인트 확인

클러스터의 OIDC Provider 정보를 확인하는 방법:

```bash
# OIDC 발급자 URL 확인
aws eks describe-cluster \
  --name my-cluster \
  --query "cluster.identity.oidc.issuer" \
  --output text

# 출력: https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE

# IAM OIDC Provider 상태 확인
aws iam list-open-id-connect-providers | \
  jq '.OpenIDConnectProviderList[] | select(.Arn | contains("EXAMPLED539D4633E53DE1B71EXAMPLE"))'

# OIDC Provider 상세 정보
aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE
```

### JWKS URI와 토큰 검증

JWKS(JSON Web Key Set)는 토큰 서명을 검증하는 데 사용되는 공개 키 집합입니다:

```bash
# JWKS URI 확인 (OIDC 발급자 URL + /.well-known/openid-configuration)
OIDC_URL=$(aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text)

# OpenID Configuration 조회
curl -s "${OIDC_URL}/.well-known/openid-configuration" | jq '.'

# JWKS 직접 조회
curl -s "${OIDC_URL}/keys" | jq '.'
```

JWKS 응답 예시:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "xxx-xxx-xxx",
      "use": "sig",
      "alg": "RS256",
      "n": "...(base64 encoded modulus)...",
      "e": "AQAB"
    }
  ]
}
```

### IAM 역할 신뢰 정책 설정

OIDC를 사용하는 IAM 역할의 신뢰 정책:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account",
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

## EKS Pod Identity

EKS Pod Identity는 2023년에 도입된 새로운 방식으로, IRSA의 복잡성을 줄이고 더 간단하게 파드에 AWS IAM 권한을 부여합니다.

### IRSA 대비 장점

| 특성 | IRSA | EKS Pod Identity |
|------|------|------------------|
| **설정 복잡도** | OIDC Provider, IAM 역할 신뢰 정책 필요 | Pod Identity Association만 필요 |
| **IAM 역할 재사용** | 클러스터별 역할 필요 | 여러 클러스터에서 역할 재사용 가능 |
| **세션 태그** | 미지원 | 지원 (리소스 태깅 자동화) |
| **자격 증명 위치** | Projected Volume | EKS Auth API |
| **토큰 갱신** | 파드 내 SDK 담당 | Pod Identity Agent 담당 |

### Pod Identity Agent 동작 원리

![각 노드에서 DaemonSet으로 실행되는 Pod Identity Agent가 파드의 자격 증명 요청을 가로채 Pod Identity Association의 역할 매핑을 확인하고 AWS STS에서 임시 자격 증명을 받아 파드에 전달하는 과정을 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-4.html)

Pod Identity Agent는 각 노드에서 DaemonSet으로 실행되며:
1. 파드의 자격 증명 요청을 가로챕니다
2. Pod Identity Association을 확인합니다
3. 연결된 IAM 역할의 임시 자격 증명을 획득합니다
4. 파드에 자격 증명을 전달합니다

### Pod Identity Association 설정

#### eksctl 사용

```bash
# Pod Identity Association 생성
eksctl create podidentityassociation \
  --cluster my-cluster \
  --namespace default \
  --service-account-name s3-reader \
  --role-arn arn:aws:iam::123456789012:role/S3ReaderRole

# 연결 확인
eksctl get podidentityassociation --cluster my-cluster
```

#### AWS CLI 사용

```bash
# Pod Identity Association 생성
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace default \
  --service-account s3-reader \
  --role-arn arn:aws:iam::123456789012:role/S3ReaderRole

# 연결 목록 조회
aws eks list-pod-identity-associations --cluster-name my-cluster

# 특정 연결 상세 정보
aws eks describe-pod-identity-association \
  --cluster-name my-cluster \
  --association-id a-xxxxxxxxxxxxx
```

### IRSA에서 Pod Identity로 마이그레이션

기존 IRSA 설정을 Pod Identity로 마이그레이션하는 절차:

```bash
# 1. Pod Identity Agent 애드온 설치 확인
aws eks describe-addon \
  --cluster-name my-cluster \
  --addon-name eks-pod-identity-agent

# 애드온 미설치 시 설치
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-pod-identity-agent

# 2. 기존 IRSA IAM 역할의 신뢰 정책 업데이트
# Pod Identity도 허용하도록 Principal 추가
cat > trust-policy.json << 'EOF'
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
      ]
    }
  ]
}
EOF

aws iam update-assume-role-policy \
  --role-name S3ReaderRole \
  --policy-document file://trust-policy.json

# 3. Pod Identity Association 생성
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace default \
  --service-account s3-reader \
  --role-arn arn:aws:iam::123456789012:role/S3ReaderRole

# 4. 서비스 계정에서 IRSA 어노테이션 제거 (선택적)
kubectl annotate serviceaccount s3-reader \
  eks.amazonaws.com/role-arn- \
  -n default

# 5. 파드 재시작하여 Pod Identity 사용 확인
kubectl rollout restart deployment my-app -n default
```

### Pod Identity 사용 예제

```yaml
# 1. 서비스 계정 생성 (IRSA 어노테이션 불필요)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  namespace: default
---
# 2. 파드에서 서비스 계정 사용
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader-pod
spec:
  serviceAccountName: s3-reader
  containers:
  - name: app
    image: amazonlinux:2
    command:
    - /bin/sh
    - -c
    - |
      # AWS SDK가 자동으로 Pod Identity Agent에서 자격 증명 획득
      aws s3 ls
      aws sts get-caller-identity
```

## Cluster Endpoint 접근 제어

EKS 클러스터의 Kubernetes API 서버 엔드포인트에 대한 접근을 제어하는 것은 보안의 기본입니다.

### 엔드포인트 구성 옵션

EKS는 세 가지 엔드포인트 구성을 지원합니다:

![EKS API 서버를 Public Only, Private Only, Public+Private 세 가지 방식으로 구성했을 때 인터넷과 VPC 내부 노드가 각각 어떤 경로로 컨트롤 플레인에 도달하는지 비교한다.](../../assets/diagrams/rendered/ko-eks-05-eks-security-5.svg)

| 구성 | Public | Private | 사용 사례 |
|------|--------|---------|-----------|
| **Public Only** | ✅ | ❌ | 개발/테스트 환경, 빠른 시작 |
| **Private Only** | ❌ | ✅ | 프로덕션, 금융/의료 워크로드 |
| **Public + Private** | ✅ | ✅ | 하이브리드 접근, CI/CD 통합 |

### Public/Private/Public+Private 엔드포인트 구성

```bash
# 현재 엔드포인트 설정 확인
aws eks describe-cluster \
  --name my-cluster \
  --query "cluster.resourcesVpcConfig.{PublicAccess:endpointPublicAccess, PrivateAccess:endpointPrivateAccess, PublicCIDRs:publicAccessCidrs}"

# Public + Private 설정 (권장)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true

# Private Only 설정 (최고 보안)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

### CIDR 제한 설정

퍼블릭 엔드포인트에 접근 가능한 IP 범위를 제한합니다:

```bash
# 특정 CIDR 범위만 허용
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config publicAccessCidrs="203.0.113.0/24","198.51.100.0/24"

# 회사 VPN IP 대역만 허용
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config publicAccessCidrs="10.0.0.0/8"
```

> **권장사항**: 프로덕션 환경에서는 CIDR 제한과 함께 Public + Private 구성을 사용하거나, 보안이 중요한 환경에서는 Private Only 구성을 사용하세요.

### Private 클러스터 운영 패턴

Private 엔드포인트만 활성화된 클러스터에 접근하는 방법:

#### VPN 연결

![관리자가 AWS VPN 터널을 거쳐 EKS VPC에 진입한 뒤 Private Endpoint를 통해서만 컨트롤 플레인의 Kubernetes API 서버에 kubectl로 접근하는 경로를 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-6.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-6.html)

```bash
# Site-to-Site VPN 설정 후 kubectl 사용
kubectl --kubeconfig ~/.kube/config get nodes
```

#### Transit Gateway

![온프레미스 관리자가 Direct Connect(또는 Site-to-Site VPN)와 Transit Gateway를 거쳐 EKS VPC 안의 클러스터 Private Endpoint까지 도달하는 하이브리드 접근 경로를 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-7.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-7.html)

#### Bastion Host / Session Manager

```bash
# Systems Manager Session Manager를 통한 접근
aws ssm start-session \
  --target i-xxxxxxxxxxxxx \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["443"],"localPortNumber":["6443"]}'

# 로컬에서 kubectl 사용
kubectl --server=https://localhost:6443 get nodes
```

### 엔드포인트 접근 제어 설정 예제

eksctl을 사용한 완전한 클러스터 구성:

```yaml
# cluster-config.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: secure-cluster
  region: us-west-2

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.0/24  # 회사 VPN IP 대역
    - 198.51.100.0/24 # CI/CD 서버 IP 대역

managedNodeGroups:
  - name: ng-private
    instanceType: m5.large
    desiredCapacity: 3
    privateNetworking: true  # 노드를 프라이빗 서브넷에 배치
```

```bash
# 클러스터 생성
eksctl create cluster -f cluster-config.yaml

# 엔드포인트 설정 확인
kubectl cluster-info
```

### Customer-Routed Control Plane Egress (2026년 6월)

> **발표일**: 2026년 6월 18일 · [출처](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-eks-customer-routed-control-plane-egress/)

기존에는 EKS Kubernetes API 서버가 외부(Admission Webhook, Private OIDC Provider, Aggregated API Server 등)와 통신할 때 AWS가 관리하는 경로로 egress 트래픽이 나갔습니다. Customer-Routed Control Plane Egress를 사용하면 이 egress 트래픽을 AWS 대신 고객의 VPC로 직접 라우팅할 수 있습니다.

**지원 대상 트래픽**:
- OPA/Gatekeeper, Kyverno 등 Admission Webhook 호출
- Private OIDC Provider 접근
- Aggregated API Server(예: Metrics Server, 커스텀 API) 접근

**핵심 특징**:
- 컨트롤 플레인 egress가 고객 VPC를 경유하므로 데이터 경계(Data Perimeter)를 구현하고 트래픽을 VPC 내에서 모니터링/검사할 수 있음
- `eks:controlPlaneEgressMode` IAM 조건 키를 SCP에 사용하여 조직 전체에 강제 적용 가능
- 기존 클러스터에도 적용 가능하며 추가 비용 없음, 모든 리전에서 사용 가능

```bash
# 클러스터에 고객 라우팅 컨트롤 플레인 egress 활성화
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config controlPlaneEgressMode=CUSTOMER_ROUTED
```

```json
// SCP 예시: 고객 라우팅 egress 모드를 강제 적용
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireCustomerRoutedControlPlaneEgress",
      "Effect": "Deny",
      "Action": [
        "eks:CreateCluster",
        "eks:UpdateClusterConfig"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "eks:controlPlaneEgressMode": "CUSTOMER_ROUTED"
        }
      }
    }
  ]
}
```

## 네트워크 보안

### 보안 그룹

EKS 클러스터의 노드와 파드에 대한 네트워크 트래픽을 제어하기 위해 AWS 보안 그룹을 사용할 수 있습니다.

![퍼블릭 서브넷의 ALB와 Bastion 호스트가 인터넷 트래픽을 받아 프라이빗 서브넷의 EKS 워커 노드로 전달하고, 각 구성 요소가 보안 그룹으로 감싸이며 네트워크 정책이 파드 통신을 제어하고 워커 노드가 VPC 엔드포인트로 ECR, S3, STS에 프라이빗하게 접근하는 EKS 네트워크 보안 아키텍처를 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-8.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-8.html)

#### 클러스터 보안 그룹

EKS 클러스터 보안 그룹은 컨트롤 플레인과 워커 노드 간의 통신을 허용합니다:

- 포트 443(HTTPS): 클러스터 API 서버 통신
- 포트 10250: kubelet API
- 포트 범위 1025-65535: 노드 간 통신

#### 노드 보안 그룹

워커 노드에 대한 보안 그룹 권장 구성:

- 인바운드: 클러스터 보안 그룹으로부터의 트래픽 허용
- 아웃바운드: 모든 트래픽 허용(필요에 따라 제한 가능)

### 네트워크 정책

Kubernetes 네트워크 정책을 사용하여 파드 간 통신을 제어할 수 있습니다. EKS에서는 Amazon VPC CNI, Calico, Cilium 등의 네트워크 플러그인을 통해 네트워크 정책을 구현할 수 있습니다.

#### 기본 거부 정책 예시

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

#### 특정 애플리케이션 간 통신 허용 정책 예시

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

### VPC 엔드포인트

AWS 서비스에 대한 프라이빗 액세스를 위해 VPC 엔드포인트를 사용하여 인터넷 게이트웨이를 통하지 않고 AWS 서비스에 안전하게 액세스할 수 있습니다.

EKS 클러스터에 권장되는 VPC 엔드포인트:

- com.amazonaws.region.ecr.api
- com.amazonaws.region.ecr.dkr
- com.amazonaws.region.s3
- com.amazonaws.region.logs
- com.amazonaws.region.sts

## 포드 보안

### 포드 보안 표준(PSS)

Kubernetes 1.23부터 도입된 포드 보안 표준은 파드의 보안 컨텍스트를 제한하는 내장 메커니즘을 제공합니다. EKS에서는 다음과 같은 수준의 PSS를 적용할 수 있습니다:

- **Privileged**: 제한 없음
- **Baseline**: 알려진 권한 에스컬레이션 방지
- **Restricted**: 강력한 보안 제한 적용

![네임스페이스 레이블(enforce·audit·warn)로 지정한 Privileged·Baseline·Restricted 포드 보안 표준, securityContext 설정, OPA Gatekeeper와 Kyverno가 어드미션 웹훅으로 적용하는 정책이 권한 있는 파드·애플리케이션 파드·시스템 파드에 각각 어떻게 반영되는지 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-9.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-9.html)

네임스페이스에 PSS 적용 예시:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 보안 컨텍스트

파드 및 컨테이너 수준에서 보안 컨텍스트를 구성하여 권한을 제한할 수 있습니다:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: secure-container
    image: nginx
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

### OPA Gatekeeper 및 Kyverno

OPA Gatekeeper 또는 Kyverno와 같은 정책 엔진을 사용하여 클러스터 전체에 보안 정책을 적용할 수 있습니다.

#### Kyverno 정책 예시 - 권한 있는 컨테이너 방지

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed"
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              privileged: false
```

## Bottlerocket 및 읽기 전용 OS

Bottlerocket은 AWS에서 개발한 컨테이너 워크로드 전용 Linux 운영 체제입니다. 보안을 최우선으로 설계되어 불변 인프라 전략에 적합합니다.

### Bottlerocket 특성

![Bottlerocket 운영체제가 API 기반 구성·SELinux·dm-verity·읽기 전용 루트로 구성된 보안 특성, 자동 업데이트/롤백/A-B 파티션 방식의 업데이트 전략, SSH·패키지 관리자·불필요 서비스를 제거한 최소화 전략으로 불변 인프라를 구현함을 보여준다.](../../assets/diagrams/rendered/ko-eks-05-eks-security-10.svg)

#### API 기반 구성

Bottlerocket은 SSH 대신 API 서버를 통해 구성됩니다:

```bash
# Bottlerocket 설정 확인 (컨트롤 컨테이너에서)
apiclient get settings

# 설정 변경
apiclient set kubernetes.node-labels.environment=production

# 커밋 및 적용
apiclient commit
```

#### 자동 업데이트

```yaml
# 자동 업데이트 설정 (eksctl)
managedNodeGroups:
  - name: bottlerocket-ng
    amiFamily: Bottlerocket
    bottlerocket:
      settings:
        # 업데이트 설정
        motd: "EKS Production Node"
        kubernetes:
          node-labels:
            environment: production
```

### SELinux 적용

Bottlerocket은 SELinux가 기본 활성화되어 있어 컨테이너 간 격리를 강화합니다:

```yaml
# SELinux 상태 확인 (파드 내에서)
apiVersion: v1
kind: Pod
metadata:
  name: selinux-check
spec:
  containers:
  - name: check
    image: amazonlinux:2
    command:
    - /bin/sh
    - -c
    - |
      getenforce
      cat /proc/self/attr/current
```

### dm-verity (루트 파일시스템 무결성)

dm-verity는 블록 레벨에서 루트 파일시스템의 무결성을 검증합니다:

![루트 파일시스템에서 블록을 읽고 해시를 계산해 Merkle Tree에 저장된 해시와 대조하는 dm-verity 검증 과정에서 해시가 일치하면 접근을 허용하고 불일치하면 접근을 차단하는 흐름을 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-11.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-11.html)

- 부팅 시 루트 파일시스템의 무결성 검증
- 런타임에 수정 시도 감지 및 차단
- 악성 코드 주입 방지

### 불변 인프라 전략

Bottlerocket을 사용한 불변 인프라 구현:

```yaml
# 1. 새 버전의 노드 그룹 생성
managedNodeGroups:
  - name: bottlerocket-v2
    amiFamily: Bottlerocket
    instanceType: m5.xlarge
    desiredCapacity: 3
    labels:
      version: v2

# 2. 기존 노드 드레인 및 삭제
# kubectl cordon/drain 사용
```

```bash
# 노드 교체 전략
# 1. 새 노드 그룹 생성
eksctl create nodegroup -f new-nodegroup.yaml

# 2. 기존 노드 cordon
kubectl cordon -l eks.amazonaws.com/nodegroup=bottlerocket-v1

# 3. 기존 노드 drain
kubectl drain -l eks.amazonaws.com/nodegroup=bottlerocket-v1 \
  --ignore-daemonsets \
  --delete-emptydir-data

# 4. 기존 노드 그룹 삭제
eksctl delete nodegroup \
  --cluster my-cluster \
  --name bottlerocket-v1
```

### EKS 관리형 노드 그룹에서 Bottlerocket 사용

```yaml
# eksctl 설정
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: secure-cluster
  region: us-west-2

managedNodeGroups:
  - name: bottlerocket-ng
    amiFamily: Bottlerocket
    instanceType: m5.large
    desiredCapacity: 3
    privateNetworking: true

    # Bottlerocket 특화 설정
    bottlerocket:
      settings:
        motd: "Production EKS Node"
        kubernetes:
          allowed-unsafe-sysctls:
            - net.core.somaxconn
          cluster-dns-ip: 10.100.0.10
          max-pods: 110
        # 호스트 컨테이너 설정
        host-containers:
          admin:
            enabled: false  # 프로덕션에서는 비활성화 권장
          control:
            enabled: true
```

```bash
# AWS CLI로 Bottlerocket 노드 그룹 생성
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name bottlerocket-ng \
  --ami-type BOTTLEROCKET_x86_64 \
  --instance-types m5.large \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --subnets subnet-xxx subnet-yyy \
  --node-role arn:aws:iam::123456789012:role/EKSNodeRole
```

## IAM 권한 경계

IAM 권한 경계(Permission Boundary)는 IAM 역할이나 사용자에게 부여할 수 있는 최대 권한을 정의합니다. EKS 환경에서 권한 경계를 적절히 활용하면 보안을 강화할 수 있습니다.

### Permission Boundary 개념

권한 경계는 "유효 권한 = 정책 ∩ 경계"의 원칙을 따릅니다:

![IAM 정책과 권한 경계의 교집합이 유효 권한이 되는 원리를, S3·DynamoDB·EC2 권한을 부여한 정책이 S3·DynamoDB만 허용하는 경계와 만나 최종적으로 S3·DynamoDB만 사용 가능해지는 예시로 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-12.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-12.html)

### SCP (Service Control Policy) 활용

AWS Organizations의 SCP와 IAM 권한 경계를 함께 사용하여 다층 방어:

```json
// 조직 수준 SCP - EKS 관련 서비스만 허용
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEKSServices",
      "Effect": "Allow",
      "Action": [
        "eks:*",
        "ec2:*",
        "ecr:*",
        "s3:*",
        "logs:*",
        "cloudwatch:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyDangerousActions",
      "Effect": "Deny",
      "Action": [
        "eks:DeleteCluster",
        "ec2:TerminateInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalTag/Role": "admin"
        }
      }
    }
  ]
}
```

### 최소 권한 IAM 정책 패턴

EKS 워크로드에 대한 최소 권한 정책 예시:

```json
// S3 접근만 허용하는 최소 권한 정책
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3BucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-app-bucket",
        "arn:aws:s3:::my-app-bucket/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Environment": "${aws:PrincipalTag/Environment}"
        }
      }
    }
  ]
}
```

### EKS 노드 역할 권한 경계 예제

```json
// EKS 노드 역할에 적용할 권한 경계
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEKSNodeActions",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumesModifications",
        "ec2:DescribeVpcs",
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:ModifyNetworkInterfaceAttribute",
        "ec2:AssignPrivateIpAddresses",
        "ec2:UnassignPrivateIpAddresses"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowECRPull",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowCloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/eks/*"
    },
    {
      "Sid": "DenyDangerousActions",
      "Effect": "Deny",
      "Action": [
        "iam:*",
        "organizations:*",
        "account:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 권한 경계 적용

```bash
# 권한 경계 생성
aws iam create-policy \
  --policy-name EKSNodePermissionBoundary \
  --policy-document file://permission-boundary.json

# IAM 역할에 권한 경계 적용
aws iam put-role-permissions-boundary \
  --role-name EKSNodeRole \
  --permissions-boundary arn:aws:iam::123456789012:policy/EKSNodePermissionBoundary

# 권한 경계 확인
aws iam get-role --role-name EKSNodeRole --query "Role.PermissionsBoundary"
```

### 파드 IAM 역할에 권한 경계 적용

IRSA 또는 Pod Identity에서 사용하는 IAM 역할에도 권한 경계를 적용할 수 있습니다:

```bash
# 파드용 IAM 역할 생성 시 권한 경계 포함
aws iam create-role \
  --role-name PodS3ReaderRole \
  --assume-role-policy-document file://trust-policy.json \
  --permissions-boundary arn:aws:iam::123456789012:policy/PodPermissionBoundary

# 기존 역할에 권한 경계 추가
aws iam put-role-permissions-boundary \
  --role-name PodS3ReaderRole \
  --permissions-boundary arn:aws:iam::123456789012:policy/PodPermissionBoundary
```

### 신규 IAM Condition Key 7종을 통한 사전 통제 (2026년 4월)

> **발표일**: 2026년 4월 20일 · [출처](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-iam-condition-keys/)

Amazon EKS는 클러스터를 생성하거나 업데이트하는 시점에 정책 기반으로 사전에 통제(Proactive Governance)할 수 있는 IAM 조건 키 7종을 새롭게 제공합니다. `CreateCluster`, `UpdateClusterConfig`, `UpdateClusterVersion`, `AssociateEncryptionConfig` API에 조건을 걸어 AWS Organizations SCP와 통합할 수 있습니다.

| 조건 키 | 용도 |
|---------|------|
| `eks:endpointPublicAccess` / `eks:endpointPrivateAccess` | Private Endpoint 사용을 강제 |
| `eks:encryptionConfigProviderKeyArns` | KMS를 통한 시크릿 암호화를 필수화 |
| `eks:kubernetesVersion` | 허용된 Kubernetes 버전으로 클러스터 생성/업그레이드 제한 |
| `eks:controlPlaneScalingTier` | 컨트롤 플레인 스케일링 티어 제한 |
| `eks:deletionProtection` | 클러스터 삭제 보호 강제 |
| `eks:zonalShiftEnabled` | Zonal Shift 활성화 여부 통제 |

```json
// SCP 예시: Private Endpoint와 KMS 암호화를 강제
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequirePrivateEndpointAndKmsEncryption",
      "Effect": "Deny",
      "Action": [
        "eks:CreateCluster",
        "eks:UpdateClusterConfig"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "eks:endpointPublicAccess": "true"
        }
      }
    },
    {
      "Sid": "RequireEncryptionConfig",
      "Effect": "Deny",
      "Action": "eks:CreateCluster",
      "Resource": "*",
      "Condition": {
        "Null": {
          "eks:encryptionConfigProviderKeyArns": "true"
        }
      }
    },
    {
      "Sid": "RestrictKubernetesVersion",
      "Effect": "Deny",
      "Action": [
        "eks:CreateCluster",
        "eks:UpdateClusterVersion"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "eks:kubernetesVersion": ["1.32", "1.33"]
        }
      }
    }
  ]
}
```

## 암호화 및 비밀 관리

### EKS 암호화 옵션

#### etcd 암호화

EKS는 기본적으로 etcd에 저장된 Kubernetes 비밀을 암호화합니다. 추가적인 암호화 계층을 위해 AWS KMS를 사용할 수 있습니다:

![EKS 암호화 옵션을 보여주는 다이어그램으로, AWS KMS가 etcd 기본 암호화 위에 추가 암호화 계층을 더하고, AWS Secrets Manager·Parameter Store·HashiCorp Vault·Mozilla SOPS 같은 비밀 관리 솔루션이 External Secrets Operator·ASCP·Secrets Store CSI Driver 통합 도구를 거쳐 Kubernetes Secrets로 동기화된 뒤 마운트·환경 변수·init 컨테이너로 파드에 주입되는 흐름을 나타낸다.](../.gitbook/assets/ko-eks-05-eks-security-13.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-13.html)

```bash
eksctl create cluster --name my-cluster --region us-west-2 --encryption-provider-config-key arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

### AWS Secrets Manager 및 Parameter Store 통합

AWS Secrets Manager 또는 Parameter Store에 저장된 비밀을 Kubernetes 파드에 마운트하기 위해 External Secrets Operator 또는 AWS Secrets and Configuration Provider(ASCP)를 사용할 수 있습니다.

#### External Secrets Operator 설치

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace
```

#### SecretStore 및 ExternalSecret 정의

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: db-credentials
  data:
  - secretKey: username
    remoteRef:
      key: db-credentials
      property: username
  - secretKey: password
    remoteRef:
      key: db-credentials
      property: password
```

### SOPS(Secrets OPerationS)

Mozilla SOPS를 사용하여 Git 저장소에 암호화된 비밀을 안전하게 저장하고 관리할 수 있습니다.

#### SOPS 설치 및 사용

```bash
# SOPS 설치
brew install sops

# AWS KMS 키를 사용하여 비밀 암호화
sops --encrypt --aws-profile default --kms arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab secrets.yaml > secrets.enc.yaml

# 암호화된 비밀 복호화
sops --decrypt secrets.enc.yaml
```

## 컴플라이언스 및 감사

### EKS 감사 로깅

EKS 컨트롤 플레인 감사 로그를 활성화하여 클러스터에서 수행된 모든 API 호출을 기록할 수 있습니다:

![컨트롤 플레인 로그·감사 로그·CloudTrail·Fluent Bit 로그가 Amazon CloudWatch에 수집되어 저장·분석된 뒤 AWS Security Hub를 거쳐 알림과 보고로 이어지고, AWS Config와 Amazon Inspector 결과를 CIS Kubernetes Benchmark로 평가해 PCI DSS·HIPAA·GDPR·SOC 2·ISO 27001 등 규제 표준 준수 여부를 확인하는 컴플라이언스 및 감사 흐름을 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-14.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-14.html)

```bash
aws eks update-cluster-config \
  --region us-west-2 \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

### AWS Config 규칙

AWS Config를 사용하여 EKS 클러스터의 규정 준수 상태를 모니터링할 수 있습니다:

- eks-cluster-logging-enabled
- eks-cluster-oldest-supported-version
- eks-endpoint-no-public-access
- eks-secrets-encrypted

### AWS Security Hub 통합

AWS Security Hub를 사용하여 EKS 클러스터의 보안 상태를 중앙에서 관리하고 모니터링할 수 있습니다. Security Hub는 CIS Kubernetes Benchmark와 같은 업계 표준에 대한 규정 준수를 확인합니다.

## 보안 모니터링 및 탐지

### GuardDuty EKS Protection

Amazon GuardDuty EKS Protection을 활성화하여 EKS 클러스터에서 잠재적인 보안 위협을 탐지할 수 있습니다:

![GuardDuty, Security Hub, CloudWatch 같은 AWS 보안 서비스와 Falco, kube-audit 같은 Kubernetes 보안 도구가 런타임·네트워크·ID 보안과 구성 보안을 탐지하고, 수집한 데이터가 수집→분석→탐지→대응→해결의 위협 탐지 워크플로우로 흐르며 탐지 결과는 Security Hub로 다시 전달되는 구조를 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-15.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-15.html)

```bash
aws guardduty update-detector \
  --detector-id 12abc34d567e8fa901bc2d34e56789f0 \
  --features '[{"Name": "EKS_RUNTIME_MONITORING", "Status": "ENABLED"}]'
```

### AWS Security Hub

AWS Security Hub를 사용하여 EKS 클러스터의 보안 상태를 중앙에서 관리하고 모니터링할 수 있습니다:

```bash
aws securityhub enable-security-hub
aws securityhub batch-enable-standards --standards-subscription-requests '[{"StandardsArn":"arn:aws:securityhub:us-west-2::standards/aws-foundational-security-best-practices/v/1.0.0"}]'
```

### Falco

Falco를 사용하여 런타임 보안 모니터링 및 이상 탐지를 수행할 수 있습니다:

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco --namespace falco --create-namespace
```

Falco 규칙 예시:

```yaml
- rule: Terminal shell in container
  desc: A shell was spawned by a pod in the container
  condition: container and shell_procs and not container_entrypoint
  output: Shell spawned in a container (user=%user.name pod=%k8s.pod.name container=%container.name shell=%proc.name parent=%proc.pname cmdline=%proc.cmdline)
  priority: WARNING
```

## EKS 보안 모범 사례

### 클러스터 보안 강화

1. **최신 Kubernetes 버전 유지**: 정기적으로 EKS 클러스터를 최신 버전으로 업그레이드하여 보안 패치 적용
2. **프라이빗 API 엔드포인트 사용**: 퍼블릭 인터넷에서 API 서버에 대한 액세스 제한
3. **최소 권한 원칙 적용**: IAM 역할 및 RBAC에 최소 권한 원칙 적용
4. **보안 그룹 제한**: 필요한 포트만 허용하도록 보안 그룹 구성
5. **네트워크 정책 구현**: 파드 간 통신을 제한하는 네트워크 정책 적용

### 노드 및 컨테이너 보안

1. **최신 AMI 사용**: 최신 보안 패치가 적용된 EKS 최적화 AMI 사용
2. **컨테이너 이미지 스캔**: ECR 이미지 스캔 또는 Trivy와 같은 도구를 사용하여 취약점 스캔
3. **불변 인프라 사용**: 노드 업데이트 시 새 노드 그룹 생성 및 이전 노드 그룹 삭제
4. **비 루트 사용자로 컨테이너 실행**: 컨테이너를 비 루트 사용자로 실행하여 권한 제한
5. **읽기 전용 파일 시스템 사용**: 가능한 경우 컨테이너의 루트 파일 시스템을 읽기 전용으로 마운트

### 지속적인 보안 모니터링

1. **감사 로깅 활성화**: EKS 컨트롤 플레인 감사 로그 활성화
2. **GuardDuty EKS Protection 활성화**: 런타임 보안 모니터링을 위한 GuardDuty EKS Protection 활성화
3. **Security Hub 통합**: AWS Security Hub를 사용하여 보안 상태 중앙 관리
4. **정기적인 보안 평가**: CIS Kubernetes Benchmark를 기준으로 정기적인 보안 평가 수행
5. **인시던트 대응 계획 수립**: EKS 클러스터에 대한 보안 인시던트 대응 계획 수립 및 테스트

## 금융 서비스를 위한 EKS 보안 고려사항

금융 서비스 산업에서 EKS를 사용할 때 고려해야 할 추가 보안 요구사항:

### 규제 준수

1. **PCI DSS**: 카드 결제 데이터를 처리하는 워크로드에 대한 PCI DSS 요구사항 준수
2. **GDPR/CCPA**: 개인 식별 정보(PII)에 대한 데이터 보호 규정 준수
3. **금융 규제**: 국내 금융 규제 기관의 요구사항 준수(예: 금융감독원 지침)

### 데이터 보안

1. **전송 중 암호화**: TLS 1.2 이상을 사용하여 모든 네트워크 통신 암호화
2. **저장 데이터 암호화**: AWS KMS를 사용하여 저장 데이터 암호화
3. **데이터 분류**: 민감도에 따른 데이터 분류 및 적절한 보안 제어 적용
4. **데이터 액세스 로깅**: 모든 민감한 데이터 액세스에 대한 상세 로깅 및 모니터링

### 고가용성 및 재해 복구

1. **다중 가용 영역 배포**: 여러 가용 영역에 걸쳐 EKS 클러스터 배포
2. **재해 복구 계획**: 정기적인 백업 및 복구 테스트를 포함한 재해 복구 계획 수립
3. **비즈니스 연속성**: 금융 서비스에 적합한 RTO(Recovery Time Objective) 및 RPO(Recovery Point Objective) 정의

### 금융 서비스를 위한 EKS 보안 아키텍처 예시

![인터넷 트래픽이 AWS WAF와 Application Load Balancer를 거쳐 프라이빗 서브넷의 애플리케이션 파드와 보안 사이드카에 도달하고, 파드는 AWS KMS 키로 암호화된 RDS·S3·DynamoDB 데이터 서비스에 접근하며, GuardDuty·Security Hub·Config·CloudTrail이 EKS 클러스터를 모니터링하는 금융 서비스 VPC 보안 아키텍처를 보여준다.](../.gitbook/assets/ko-eks-05-eks-security-16.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-eks-05-eks-security-16.html)

## 결론

Amazon EKS의 보안은 여러 계층에 걸친 방어 전략을 통해 구현됩니다. IAM 및 RBAC를 통한 강력한 인증 및 권한 부여, 네트워크 정책 및 보안 그룹을 통한 네트워크 보안, 포드 보안 표준 및 보안 컨텍스트를 통한 워크로드 보안, 그리고 AWS의 다양한 보안 서비스와의 통합을 통해 EKS 클러스터를 안전하게 운영할 수 있습니다.

특히 금융 서비스와 같은 규제가 엄격한 산업에서는 추가적인 보안 제어 및 규정 준수 요구사항을 고려해야 합니다. 정기적인 보안 평가, 취약점 스캔, 그리고 지속적인 모니터링을 통해 EKS 환경의 보안 상태를 유지하는 것이 중요합니다.

## 참고 자료

- [Amazon EKS 보안 모범 사례](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [Kubernetes 보안 모범 사례](https://kubernetes.io/docs/concepts/security/overview/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [AWS Security Hub](https://aws.amazon.com/security-hub/)
- [Amazon GuardDuty](https://aws.amazon.com/guardduty/)
- [Amazon EKS Customer-Routed Control Plane Egress (2026-06-18)](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-eks-customer-routed-control-plane-egress/)
- [Amazon EKS 신규 IAM Condition Key 7종 (2026-04-20)](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-iam-condition-keys/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../quizzes/eks/05-eks-security-quiz.md)를 풀어보세요.
