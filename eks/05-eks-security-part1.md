# EKS 보안 - 1부

## 소개

Amazon EKS의 보안은 클러스터와 워크로드를 보호하는 데 중요한 역할을 합니다. 이 장에서는 EKS 보안의 기본 개념, 구성 요소 및 모범 사례를 알아보겠습니다.

## EKS 보안 아키텍처

### 공동 책임 모델

AWS와 고객 간의 보안 책임은 다음과 같이 나뉩니다:

**AWS의 책임**:
- EKS 컨트롤 플레인 보안
- 기본 인프라 보안
- 네트워크 격리
- 물리적 보안

**고객의 책임**:
- IAM 구성
- 네트워크 보안 그룹 및 ACL
- 데이터 암호화
- 워크로드 보안
- 컨테이너 이미지 보안
- 보안 모니터링 및 감사

### 보안 계층

EKS 보안은 다음과 같은 여러 계층으로 구성됩니다:

1. **인프라 보안**: VPC, 서브넷, 보안 그룹, 네트워크 ACL
2. **클러스터 보안**: IAM, RBAC, 포드 보안 정책
3. **컨테이너 보안**: 이미지 스캐닝, 런타임 보안
4. **애플리케이션 보안**: 네트워크 정책, 암호화, 시크릿 관리
5. **데이터 보안**: 저장 데이터 및 전송 중 데이터 암호화

## IAM 및 인증

### EKS IAM 인증자

EKS는 AWS IAM을 사용하여 Kubernetes API 서버에 대한 인증을 제공합니다. 이를 통해 AWS IAM 자격 증명을 사용하여 Kubernetes 클러스터에 액세스할 수 있습니다.

#### 작동 방식

1. 사용자가 `kubectl` 명령을 실행합니다.
2. AWS IAM 인증자는 AWS STS(Security Token Service)를 호출하여 사용자의 자격 증명을 확인합니다.
3. 인증이 성공하면 Kubernetes API 서버에 요청이 전달됩니다.
4. Kubernetes RBAC 시스템이 요청을 승인합니다.

#### aws-auth ConfigMap

EKS는 `aws-auth` ConfigMap을 사용하여 IAM 사용자 및 역할을 Kubernetes 사용자 및 그룹에 매핑합니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSNodeRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
    - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
      username: admin
      groups:
        - system:masters
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/developer
      username: developer
      groups:
        - developers
```

#### aws-auth ConfigMap 관리

aws-auth ConfigMap을 관리하는 방법:

```bash
# aws-auth ConfigMap 가져오기
kubectl get configmap aws-auth -n kube-system -o yaml > aws-auth.yaml

# aws-auth ConfigMap 편집
kubectl edit configmap aws-auth -n kube-system

# aws-auth ConfigMap 적용
kubectl apply -f aws-auth.yaml
```

### IAM 역할 서비스 계정(IRSA)

IAM 역할 서비스 계정(IRSA)을 사용하면 Kubernetes 서비스 계정을 AWS IAM 역할과 연결할 수 있습니다. 이를 통해 포드는 AWS 서비스에 안전하게 액세스할 수 있습니다.

#### IRSA 설정

1. **OIDC 제공자 생성**:

```bash
# OIDC 제공자 URL 가져오기
aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text

# OIDC 제공자 생성
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

2. **IAM 역할 및 정책 생성**:

```bash
# IAM 정책 생성
cat <<EOF > s3-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name S3ReadOnlyPolicy \
  --policy-document file://s3-policy.json
```

3. **서비스 계정 생성**:

```bash
# eksctl을 사용한 서비스 계정 생성
eksctl create iamserviceaccount \
  --name s3-reader \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadOnlyPolicy \
  --approve \
  --override-existing-serviceaccounts
```

4. **포드에서 서비스 계정 사용**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
spec:
  serviceAccountName: s3-reader
  containers:
  - name: app
    image: amazon/aws-cli:latest
    command: ['sleep', '3600']
```

### 클러스터 액세스 관리

#### EKS 클러스터 엔드포인트 액세스

EKS 클러스터 엔드포인트에 대한 액세스를 제어하는 방법:

1. **퍼블릭 액세스만 허용**:
   - 인터넷에서 API 서버에 액세스할 수 있습니다.
   - 보안 그룹을 사용하여 액세스를 제한할 수 있습니다.

2. **프라이빗 액세스만 허용**:
   - VPC 내에서만 API 서버에 액세스할 수 있습니다.
   - VPN 또는 Direct Connect를 통해 온프레미스 네트워크에서 액세스할 수 있습니다.

3. **퍼블릭 및 프라이빗 액세스 모두 허용**:
   - 인터넷과 VPC 내에서 모두 API 서버에 액세스할 수 있습니다.
   - 보안 그룹을 사용하여 퍼블릭 액세스를 제한할 수 있습니다.

```bash
# 클러스터 엔드포인트 액세스 구성
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","192.168.0.0/16"]
```

#### 클러스터 인증 관리

클러스터 인증을 관리하는 방법:

1. **kubeconfig 생성**:

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

2. **역할 기반 kubeconfig 생성**:

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EKSAdminRole
```

3. **임시 자격 증명 사용**:

```bash
# AWS STS를 사용하여 임시 자격 증명 가져오기
aws sts assume-role --role-arn arn:aws:iam::123456789012:role/EKSAdminRole --role-session-name eks-session

# 환경 변수 설정
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...

# kubeconfig 업데이트
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

## Kubernetes RBAC

### RBAC 개요

Kubernetes 역할 기반 액세스 제어(RBAC)는 사용자가 Kubernetes API에서 수행할 수 있는 작업을 제어합니다. RBAC는 다음과 같은 구성 요소로 이루어져 있습니다:

1. **Role**: 네임스페이스 내에서 권한을 정의합니다.
2. **ClusterRole**: 클러스터 전체에서 권한을 정의합니다.
3. **RoleBinding**: 역할을 사용자, 그룹 또는 서비스 계정에 바인딩합니다.
4. **ClusterRoleBinding**: 클러스터 역할을 사용자, 그룹 또는 서비스 계정에 바인딩합니다.

### 역할 및 클러스터 역할

#### 역할 생성

특정 네임스페이스 내에서 권한을 정의하는 역할을 생성합니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

#### 클러스터 역할 생성

클러스터 전체에서 권한을 정의하는 클러스터 역할을 생성합니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

### 역할 바인딩 및 클러스터 역할 바인딩

#### 역할 바인딩 생성

역할을 사용자, 그룹 또는 서비스 계정에 바인딩합니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: developer
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

#### 클러스터 역할 바인딩 생성

클러스터 역할을 사용자, 그룹 또는 서비스 계정에 바인딩합니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-pods-global
subjects:
- kind: Group
  name: developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### 일반적인 RBAC 구성

#### 네임스페이스 관리자

특정 네임스페이스에 대한 관리자 권한을 부여합니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: team-a
  name: namespace-admin
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: team-a-admin
  namespace: team-a
subjects:
- kind: User
  name: team-a-lead
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: namespace-admin
  apiGroup: rbac.authorization.k8s.io
```

#### 읽기 전용 액세스

클러스터에 대한 읽기 전용 액세스를 부여합니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: view-only
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: view-only-binding
subjects:
- kind: Group
  name: viewers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: view-only
  apiGroup: rbac.authorization.k8s.io
```

#### 서비스 계정 권한

특정 서비스 계정에 권한을 부여합니다:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: configmap-updater
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-configmap-updater
  namespace: default
subjects:
- kind: ServiceAccount
  name: app-service-account
roleRef:
  kind: Role
  name: configmap-updater
  apiGroup: rbac.authorization.k8s.io
```

### RBAC 검증

RBAC 구성을 검증하는 방법:

```bash
# 사용자 권한 확인
kubectl auth can-i get pods --namespace default --as developer

# 서비스 계정 권한 확인
kubectl auth can-i update configmaps --namespace default --as system:serviceaccount:default:app-service-account
```
