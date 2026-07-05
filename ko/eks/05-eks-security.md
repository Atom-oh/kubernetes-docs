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

```mermaid
flowchart TD
    subgraph AWS["AWS 책임"]
        CP[EKS 컨트롤 플레인] --> |암호화된 통신| ETCD[etcd]
        CP --> |관리| KMS[AWS KMS]
    end
    
    subgraph Customer["고객 책임"]
        WN[워커 노드] --> |실행| Pods[파드/컨테이너]
        Pods --> |사용| SA[서비스 계정]
        WN --> |적용| SG[보안 그룹]
        Pods --> |적용| NP[네트워크 정책]
        Pods --> |사용| Secrets[Kubernetes Secrets]
    end
    
    CP <--> |인증/인가| IAM[AWS IAM]
    CP <--> |암호화된 통신| WN
    
    style AWS fill:#FFCC99,stroke:#FF9900,stroke-width:2px
    style Customer fill:#CCFFCC,stroke:#009900,stroke-width:2px
```

## 최신 보안 트렌드 (2023)

Kubernetes 및 EKS 보안 영역에서의 최신 트렌드와 권장사항은 다음과 같습니다:

### 1. 제로 트러스트 아키텍처 (Zero Trust Architecture)

전통적인 경계 기반 보안 모델에서 벗어나, 모든 접근을 기본적으로 신뢰하지 않고 지속적으로 검증하는 접근 방식입니다.

```mermaid
flowchart LR
    subgraph ZTA["제로 트러스트 원칙"]
        P1["모든 통신 암호화"]
        P2["최소 권한 원칙"]
        P3["지속적인 검증"]
        P4["세분화된 접근 제어"]
        P5["모든 트래픽 검사"]
    end
    
    subgraph Implementation["EKS 구현 방법"]
        I1["서비스 메시 (Istio)"]
        I2["IAM Roles for Service Accounts"]
        I3["네트워크 정책"]
        I4["OPA/Gatekeeper"]
        I5["AWS Security Hub"]
    end
    
    P1 --> I1
    P2 --> I2
    P3 --> I5
    P4 --> I4
    P5 --> I3
    
    classDef principle fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef implementation fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    class P1,P2,P3,P4,P5 principle;
    class I1,I2,I3,I4,I5 implementation;
    class ZTA,Implementation default;
```

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

```mermaid
flowchart TD
    subgraph Authentication_Methods ["EKS 인증 메커니즘"]
        IAM_Auth[AWS IAM 인증자]
        OIDC[OIDC 제공자 통합]
        IRSA["서비스 계정 IAM 역할
                IRSA"]
    end
    
    subgraph Users_and_Services ["사용자 및 서비스"]
        DevOps[DevOps 팀]
        Developers[개발자]
        CI_CD[CI/CD 파이프라인]
        Pods[Kubernetes 파드]
    end
    
    subgraph AWS_Resources ["AWS 리소스"]
        S3[Amazon S3]
        DynamoDB[Amazon DynamoDB]
        SQS[Amazon SQS]
        SNS[Amazon SNS]
    end
    
    subgraph K8s_Resources ["Kubernetes 리소스"]
        API_Server[API 서버]
        ServiceAccounts[서비스 계정]
        RBAC[RBAC 권한]
    end
    
    DevOps --> IAM_Auth
    Developers --> IAM_Auth
    Developers --> OIDC
    CI_CD --> OIDC
    Pods --> IRSA
    
    IAM_Auth --> API_Server
    OIDC --> API_Server
    IRSA --> ServiceAccounts
    
    ServiceAccounts --> RBAC
    RBAC --> API_Server
    
    IRSA --> AWS_Resources
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class S3,DynamoDB,SQS,SNS,IAM_Auth awsService;
    class API_Server,ServiceAccounts,RBAC k8sComponent;
    class DevOps,Developers,CI_CD,Pods userApp;
    class OIDC,IRSA default;
```

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

```mermaid
sequenceDiagram
    participant Pod as 파드
    participant SA as 서비스 계정
    participant OIDC as EKS OIDC Provider
    participant STS as AWS STS
    participant IAM as IAM 역할

    Pod->>SA: 1. 토큰 요청
    SA->>Pod: 2. JWT 토큰 발급<br/>(projected volume)

    Pod->>STS: 3. AssumeRoleWithWebIdentity<br/>(JWT 토큰 + 역할 ARN)

    STS->>OIDC: 4. 토큰 검증 요청
    OIDC->>STS: 5. JWKS로 서명 검증

    STS->>IAM: 6. 신뢰 정책 확인
    IAM->>STS: 7. 정책 승인

    STS->>Pod: 8. 임시 자격 증명<br/>(AccessKey, SecretKey, SessionToken)

    Pod->>Pod: 9. AWS API 호출
```

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

```mermaid
flowchart TD
    subgraph EKS_Cluster["EKS 클러스터"]
        subgraph Node["노드"]
            PIA["Pod Identity Agent
            (DaemonSet)"]
            Pod["애플리케이션 파드"]
        end

        SA[서비스 계정]
        PodIdentity["Pod Identity
        Association"]
    end

    IAM["IAM 역할"]
    STS["AWS STS"]

    Pod -->|1. 자격 증명 요청| PIA
    PIA -->|2. 연결 확인| PodIdentity
    PodIdentity -->|3. 역할 매핑| IAM
    PIA -->|4. AssumeRoleForPodIdentity| STS
    STS -->|5. 임시 자격 증명| PIA
    PIA -->|6. 자격 증명 전달| Pod

    SA -.->|연결| Pod
    SA -.->|참조| PodIdentity

    style EKS_Cluster fill:#e6f7ff,stroke:#0099cc
    style Node fill:#fff3e6,stroke:#ff9900
```

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

```mermaid
flowchart TB
    subgraph Option1["Public Only"]
        Internet1((인터넷)) --> Public1[Public Endpoint]
        Public1 --> CP1[컨트롤 플레인]
        VPC1[VPC 내 노드] --> |인터넷 경유| Public1
    end

    subgraph Option2["Private Only"]
        VPC2[VPC 내 노드] --> Private2[Private Endpoint]
        Private2 --> CP2[컨트롤 플레인]
        VPN2[VPN/Direct Connect] --> VPC2
    end

    subgraph Option3["Public + Private"]
        Internet3((인터넷)) --> |CIDR 제한| Public3[Public Endpoint]
        VPC3[VPC 내 노드] --> Private3[Private Endpoint]
        Public3 --> CP3[컨트롤 플레인]
        Private3 --> CP3
    end

    style Option1 fill:#ffe6e6,stroke:#cc0000
    style Option2 fill:#e6ffe6,stroke:#009900
    style Option3 fill:#e6f7ff,stroke:#0099cc
```

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

```mermaid
flowchart LR
    Admin[관리자] --> VPN[AWS VPN]
    VPN --> VPC[EKS VPC]
    VPC --> Private[Private Endpoint]
    Private --> CP[컨트롤 플레인]
```

```bash
# Site-to-Site VPN 설정 후 kubectl 사용
kubectl --kubeconfig ~/.kube/config get nodes
```

#### Transit Gateway

```mermaid
flowchart LR
    subgraph OnPrem["온프레미스"]
        Admin[관리자]
    end

    subgraph AWS["AWS"]
        DX[Direct Connect]
        TGW[Transit Gateway]
        VPC[EKS VPC]
        EKS[EKS Cluster]
    end

    Admin --> DX
    DX --> TGW
    TGW --> VPC
    VPC --> EKS
```

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

```mermaid
flowchart TD
    subgraph VPC ["Amazon VPC"]
        subgraph Public_Subnets ["퍼블릭 서브넷"]
            ALB["Application
                Load Balancer"]
            NAT[NAT 게이트웨이]
            Bastion[Bastion 호스트]
        end
        
        subgraph Private_Subnets ["프라이빗 서브넷"]
            subgraph EKS_Cluster ["EKS 클러스터"]
                CP[EKS 컨트롤 플레인]
                
                subgraph Worker_Nodes ["워커 노드"]
                    Node1[노드 1]
                    Node2[노드 2]
                    Node3[노드 3]
                end
                
                subgraph Network_Policies ["네트워크 정책"]
                    Default_Deny[기본 거부 정책]
                    App_Allow[앱 허용 정책]
                end
            end
        end
        
        subgraph Security_Groups ["보안 그룹"]
            CP_SG["컨트롤 플레인
                보안 그룹"]
            Node_SG["노드
                보안 그룹"]
            ALB_SG["ALB
                보안 그룹"]
            Bastion_SG["Bastion
                보안 그룹"]
        end
        
        subgraph VPC_Endpoints ["VPC 엔드포인트"]
            ECR_API["ECR API
                엔드포인트"]
            ECR_DKR["ECR DKR
                엔드포인트"]
            S3_EP[S3 엔드포인트]
            STS_EP[STS 엔드포인트]
        end
    end
    
    Internet((인터넷)) --> ALB
    Internet --> Bastion
    
    ALB --> Node1
    ALB --> Node2
    ALB --> Node3
    
    Bastion --> Node1
    Bastion --> Node2
    Bastion --> Node3
    
    CP --> Node1
    CP --> Node2
    CP --> Node3
    
    Node1 --> ECR_API
    Node1 --> ECR_DKR
    Node1 --> S3_EP
    Node1 --> STS_EP
    
    CP_SG --> CP
    Node_SG --> Worker_Nodes
    ALB_SG --> ALB
    Bastion_SG --> Bastion
    
    Network_Policies --> Node1
    Network_Policies --> Node2
    Network_Policies --> Node3
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class CP,ALB,NAT,Bastion,CP_SG,Node_SG,ALB_SG,Bastion_SG,ECR_API,ECR_DKR,S3_EP,STS_EP awsService;
    class Node1,Node2,Node3,Default_Deny,App_Allow k8sComponent;
```

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

```mermaid
flowchart TD
    subgraph Pod_Security ["포드 보안 계층"]
        subgraph PSS ["포드 보안 표준"]
            Privileged["Privileged
                제한 없음"]
            Baseline["Baseline
                권한 에스컬레이션 방지"]
            Restricted["Restricted
                강력한 제한"]
        end
        
        subgraph Security_Context ["보안 컨텍스트"]
            RunAsUser["비루트 사용자
                runAsUser"]
            ReadOnlyFS["읽기 전용 파일 시스템
                readOnlyRootFilesystem"]
            NoPrivEsc["권한 에스컬레이션 방지
                allowPrivilegeEscalation"]
            DropCaps["기능 제한
                capabilities.drop"]
        end
        
        subgraph Policy_Engines ["정책 엔진"]
            OPA[OPA Gatekeeper]
            Kyverno[Kyverno]
            AdmissionControllers[어드미션 컨트롤러]
        end
    end
    
    subgraph Enforcement ["적용 방법"]
        NS_Labels[네임스페이스 레이블]
        Webhook[웹훅]
        Audit[감사]
    end
    
    subgraph Pod_Types ["파드 유형별 보안"]
        App_Pod[애플리케이션 파드]
        System_Pod[시스템 파드]
        Privileged_Pod[권한 있는 파드]
    end
    
    Privileged --> Privileged_Pod
    Baseline --> App_Pod
    Restricted --> App_Pod
    
    Security_Context --> App_Pod
    Security_Context --> System_Pod
    
    OPA --> Webhook
    Kyverno --> Webhook
    AdmissionControllers --> Webhook
    
    NS_Labels --> PSS
    Webhook --> Policy_Engines
    Audit --> PSS
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class Privileged,Baseline,Restricted,RunAsUser,ReadOnlyFS,NoPrivEsc,DropCaps k8sComponent;
    class OPA,Kyverno,AdmissionControllers k8sComponent;
    class NS_Labels,Webhook,Audit default;
    class App_Pod,System_Pod,Privileged_Pod userApp;
```

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

```mermaid
flowchart TD
    subgraph Bottlerocket["Bottlerocket OS"]
        subgraph Security["보안 특성"]
            API["API 기반 구성"]
            SELinux["SELinux 적용"]
            DMVerity["dm-verity 무결성"]
            ReadOnly["읽기 전용 루트"]
        end

        subgraph Updates["업데이트"]
            AutoUpdate["자동 업데이트"]
            Rollback["자동 롤백"]
            AB["A/B 파티션"]
        end

        subgraph Minimal["최소화"]
            NoShell["SSH/셸 기본 비활성화"]
            NoPkgMgr["패키지 관리자 없음"]
            MinServices["최소 서비스"]
        end
    end

    style Bottlerocket fill:#e6f7ff,stroke:#0099cc
    style Security fill:#e6ffe6,stroke:#009900
```

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

```mermaid
flowchart LR
    subgraph DM_Verity["dm-verity 동작"]
        Read[블록 읽기] --> Hash[해시 계산]
        Hash --> Verify[해시 검증]
        Verify -->|일치| Allow[접근 허용]
        Verify -->|불일치| Deny[접근 차단]
    end

    MerkleTree[Merkle Tree
    해시 저장소] --> Verify

    style DM_Verity fill:#e6ffe6,stroke:#009900
```

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

```mermaid
flowchart TD
    subgraph EffectivePermissions["유효 권한 계산"]
        Policy[IAM 정책]
        Boundary[권한 경계]
        Effective[유효 권한]

        Policy --> |AND| Effective
        Boundary --> |AND| Effective
    end

    subgraph Example["예시"]
        PolS3["정책: S3, DynamoDB,
        EC2 권한 부여"]
        BoundS3["경계: S3, DynamoDB만
        허용"]
        EffS3["유효: S3, DynamoDB만
        사용 가능"]

        PolS3 --> |교집합| EffS3
        BoundS3 --> |교집합| EffS3
    end

    style EffectivePermissions fill:#e6f7ff,stroke:#0099cc
    style Example fill:#e6ffe6,stroke:#009900
```

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

```mermaid
flowchart TD
    subgraph Encryption_Options ["EKS 암호화 옵션"]
        subgraph ETCD_Encryption ["etcd 암호화"]
            Default[기본 암호화]
            KMS_Encryption[AWS KMS 암호화]
        end
        
        subgraph Secret_Management ["비밀 관리 솔루션"]
            K8s_Secrets[Kubernetes Secrets]
            AWS_SM[AWS Secrets Manager]
            AWS_PS[AWS Parameter Store]
            Vault[HashiCorp Vault]
            SOPS[Mozilla SOPS]
        end
        
        subgraph Integration_Tools ["통합 도구"]
            ESO["External Secrets
                Operator"]
            ASCP["AWS Secrets and
                Configuration Provider"]
            CSI_Driver["Secrets Store
                CSI Driver"]
        end
    end
    
    subgraph Usage_Patterns ["사용 패턴"]
        subgraph Storage ["저장"]
            Encrypted_Storage[암호화된 저장]
            Version_Control[버전 관리]
            Access_Control[액세스 제어]
        end
        
        subgraph Retrieval ["검색"]
            Pod_Mount[파드 마운트]
            Env_Vars[환경 변수]
            Init_Container[초기화 컨테이너]
        end
    end
    
    KMS_Encryption --> Default
    
    AWS_SM --> ESO
    AWS_PS --> ESO
    AWS_SM --> ASCP
    AWS_PS --> ASCP
    Vault --> CSI_Driver
    
    ESO --> K8s_Secrets
    ASCP --> K8s_Secrets
    CSI_Driver --> K8s_Secrets
    
    K8s_Secrets --> Encrypted_Storage
    AWS_SM --> Encrypted_Storage
    AWS_PS --> Encrypted_Storage
    Vault --> Encrypted_Storage
    SOPS --> Encrypted_Storage
    
    AWS_SM --> Version_Control
    Vault --> Version_Control
    
    AWS_SM --> Access_Control
    AWS_PS --> Access_Control
    Vault --> Access_Control
    
    K8s_Secrets --> Pod_Mount
    K8s_Secrets --> Env_Vars
    K8s_Secrets --> Init_Container
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class KMS_Encryption,AWS_SM,AWS_PS,ASCP awsService;
    class K8s_Secrets,ESO,CSI_Driver k8sComponent;
    class Vault,SOPS userApp;
    class Default,Encrypted_Storage,Version_Control,Access_Control,Pod_Mount,Env_Vars,Init_Container default;
```

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

```mermaid
flowchart TD
    subgraph Compliance_Audit ["컴플라이언스 및 감사"]
        subgraph Logging ["로깅 및 모니터링"]
            CP_Logs[컨트롤 플레인 로그]
            Audit_Logs[감사 로그]
            CloudTrail[AWS CloudTrail]
            CloudWatch[Amazon CloudWatch]
            FluentBit[Fluent Bit]
        end
        
        subgraph Compliance_Tools ["컴플라이언스 도구"]
            Config[AWS Config]
            SecurityHub[AWS Security Hub]
            Inspector[Amazon Inspector]
            CIS_Benchmark["CIS Kubernetes
                Benchmark"]
        end
        
        subgraph Compliance_Standards ["컴플라이언스 표준"]
            PCI_DSS[PCI DSS]
            HIPAA[HIPAA]
            GDPR[GDPR]
            SOC2[SOC 2]
            ISO27001[ISO 27001]
        end
    end
    
    subgraph Audit_Flow ["감사 워크플로우"]
        Log_Collection[로그 수집]
        Log_Storage[로그 저장]
        Log_Analysis[로그 분석]
        Alerting[알림]
        Reporting[보고]
    end
    
    CP_Logs --> Log_Collection
    Audit_Logs --> Log_Collection
    CloudTrail --> Log_Collection
    FluentBit --> Log_Collection
    
    Log_Collection --> CloudWatch
    CloudWatch --> Log_Storage
    
    Log_Storage --> Log_Analysis
    Log_Analysis --> SecurityHub
    
    SecurityHub --> Alerting
    SecurityHub --> Reporting
    
    Config --> CIS_Benchmark
    Inspector --> CIS_Benchmark
    
    CIS_Benchmark --> PCI_DSS
    CIS_Benchmark --> HIPAA
    CIS_Benchmark --> GDPR
    CIS_Benchmark --> SOC2
    CIS_Benchmark --> ISO27001
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class CloudTrail,CloudWatch,Config,SecurityHub,Inspector awsService;
    class CP_Logs,Audit_Logs k8sComponent;
    class FluentBit,CIS_Benchmark userApp;
    class PCI_DSS,HIPAA,GDPR,SOC2,ISO27001,Log_Collection,Log_Storage,Log_Analysis,Alerting,Reporting default;
```

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

```mermaid
flowchart TD
    subgraph Security_Monitoring ["보안 모니터링 및 탐지"]
        subgraph AWS_Services ["AWS 보안 서비스"]
            GuardDuty[Amazon GuardDuty]
            SecurityHub[AWS Security Hub]
            Detective[Amazon Detective]
            CloudWatch[Amazon CloudWatch]
        end
        
        subgraph K8s_Tools ["Kubernetes 보안 도구"]
            Falco[Falco]
            KubeAudit[kube-audit]
            TriageParty[Triage Party]
            Starboard[Starboard]
        end
        
        subgraph Detection_Types ["탐지 유형"]
            Runtime[런타임 보안]
            Network[네트워크 보안]
            Config[구성 보안]
            Identity[ID 및 액세스 보안]
        end
    end
    
    subgraph Threat_Detection ["위협 탐지 워크플로우"]
        Collection[데이터 수집]
        Analysis[데이터 분석]
        Detection[위협 탐지]
        Response[대응]
        Remediation[문제 해결]
    end
    
    GuardDuty --> Runtime
    GuardDuty --> Network
    GuardDuty --> Identity
    
    SecurityHub --> Config
    SecurityHub --> Identity
    
    Falco --> Runtime
    KubeAudit --> Config
    
    CloudWatch --> Collection
    GuardDuty --> Collection
    Falco --> Collection
    
    Collection --> Analysis
    Analysis --> Detection
    Detection --> Response
    Response --> Remediation
    
    Detection --> SecurityHub
    
    %% 클래스 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    
    %% 클래스 적용
    class GuardDuty,SecurityHub,Detective,CloudWatch awsService;
    class Falco,KubeAudit,TriageParty,Starboard k8sComponent;
    class Runtime,Network,Config,Identity,Collection,Analysis,Detection,Response,Remediation default;
```

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

```mermaid
flowchart TD
    subgraph VPC["금융 서비스 VPC"]
        subgraph PrivateSubnets["프라이빗 서브넷"]
            EKS[EKS 클러스터]
            EKS --> AppPods[애플리케이션 파드]
            AppPods --> SecPods[보안 사이드카]
        end
        
        subgraph SecurityTools["보안 도구"]
            WAF[AWS WAF]
            GuardDuty[GuardDuty]
            SecurityHub[Security Hub]
            Config[AWS Config]
            CloudTrail[CloudTrail]
        end
        
        subgraph DataServices["데이터 서비스"]
            RDS["(Amazon RDS
                암호화됨)"]
            S3["(S3 버킷
                암호화됨)"]
            DynamoDB["(DynamoDB
                암호화됨)"]
        end
    end
    
    Internet((인터넷)) --> WAF
    WAF --> ALB["Application
                Load Balancer"]
    ALB --> AppPods
    
    AppPods --> RDS
    AppPods --> S3
    AppPods --> DynamoDB
    
    SecurityTools --> |모니터링| EKS
    
    KMS[AWS KMS] --> |암호화 키 관리| DataServices
    
    style VPC fill:#f9f9f9,stroke:#333,stroke-width:1px
    style PrivateSubnets fill:#e6f7ff,stroke:#0099cc,stroke-width:1px
    style SecurityTools fill:#ffe6e6,stroke:#cc0000,stroke-width:1px
    style DataServices fill:#e6ffe6,stroke:#009900,stroke-width:1px
```

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
