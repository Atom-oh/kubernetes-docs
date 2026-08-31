# ArgoCD 설치 및 구성

> **지원 버전**: ArgoCD v2.9+
> **마지막 업데이트**: 2026년 2월 22일

## 목차

- [사전 요구 사항](#사전-요구-사항)
- [설치 방법](#설치-방법)
- [CLI 설치](#cli-설치)
- [초기 접근](#초기-접근)
- [고가용성 설정](#고가용성-설정)
- [Amazon EKS 통합](#amazon-eks-통합)
- [선언적 설정](#선언적-설정)

## 사전 요구 사항

### Kubernetes 클러스터

| ArgoCD 버전 | 최소 K8s 버전 | 권장 K8s 버전 |
|-------------|---------------|---------------|
| v2.13 | 1.27 | 1.29+ |
| v2.12 | 1.26 | 1.28+ |
| v2.11 | 1.26 | 1.28+ |
| v2.10 | 1.25 | 1.27+ |

### 필수 도구

```bash
# kubectl 버전 확인
kubectl version --client

# 클러스터 연결 확인
kubectl cluster-info

# 권한 확인 (cluster-admin 필요)
kubectl auth can-i create namespace --all-namespaces
```

### 리소스 요구 사항

**최소 요구 사항 (개발/테스트):**
- CPU: 2 cores
- Memory: 4GB
- Storage: 10GB (Redis 캐시용)

**권장 요구 사항 (프로덕션):**
- CPU: 4+ cores
- Memory: 8GB+
- Storage: 50GB+ SSD

## 설치 방법

### 방법 1: 일반 매니페스트 (권장)

가장 간단한 설치 방법입니다:

```bash
# 네임스페이스 생성
kubectl create namespace argocd

# ArgoCD 설치 (일반)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 또는 특정 버전 설치
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml
```

**HA 모드 설치:**

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/ha/install.yaml
```

**설치 확인:**

```bash
# Pod 상태 확인
kubectl get pods -n argocd

# 예상 출력:
# NAME                                               READY   STATUS    RESTARTS   AGE
# argocd-application-controller-0                   1/1     Running   0          2m
# argocd-applicationset-controller-xxx              1/1     Running   0          2m
# argocd-dex-server-xxx                             1/1     Running   0          2m
# argocd-notifications-controller-xxx              1/1     Running   0          2m
# argocd-redis-xxx                                  1/1     Running   0          2m
# argocd-repo-server-xxx                            1/1     Running   0          2m
# argocd-server-xxx                                 1/1     Running   0          2m

# 서비스 확인
kubectl get svc -n argocd
```

### 방법 2: Helm 차트

Helm을 통한 설치는 커스터마이징이 용이합니다:

```bash
# Helm 저장소 추가
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# 기본 설치
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace

# 커스텀 values 파일로 설치
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  -f values.yaml
```

**values.yaml 예시:**

```yaml
# values.yaml
global:
  image:
    tag: v2.13.0

server:
  replicas: 2

  ingress:
    enabled: true
    ingressClassName: alb
    hosts:
      - argocd.example.com
    annotations:
      alb.ingress.kubernetes.io/scheme: internet-facing
      alb.ingress.kubernetes.io/target-type: ip
      alb.ingress.kubernetes.io/backend-protocol: HTTPS
      alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
      alb.ingress.kubernetes.io/ssl-redirect: '443'

  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi

controller:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 2Gi

repoServer:
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 1Gi

redis:
  enabled: true
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

applicationSet:
  enabled: true
  replicas: 2

notifications:
  enabled: true
```

### 방법 3: Kustomize

Kustomize를 사용하면 기본 매니페스트를 패치할 수 있습니다:

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: argocd

resources:
  - https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

patches:
  # API Server 레플리카 증가
  - target:
      kind: Deployment
      name: argocd-server
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 2

  # Repo Server 리소스 조정
  - target:
      kind: Deployment
      name: argocd-repo-server
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources
        value:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi

configMapGenerator:
  - name: argocd-cmd-params-cm
    behavior: merge
    literals:
      - server.insecure=true
```

**적용:**

```bash
kubectl apply -k .
```

## CLI 설치

### macOS

```bash
# Homebrew
brew install argocd

# 또는 직접 다운로드
VERSION=$(curl -L -s https://raw.githubusercontent.com/argoproj/argo-cd/stable/VERSION)
curl -sSL -o argocd-darwin-amd64 https://github.com/argoproj/argo-cd/releases/download/v${VERSION}/argocd-darwin-amd64
sudo install -m 555 argocd-darwin-amd64 /usr/local/bin/argocd
rm argocd-darwin-amd64
```

### Linux

```bash
# 최신 버전 다운로드
VERSION=$(curl -L -s https://raw.githubusercontent.com/argoproj/argo-cd/stable/VERSION)
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/download/v${VERSION}/argocd-linux-amd64

# 설치
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64

# 버전 확인
argocd version --client
```

### Windows

```powershell
# PowerShell로 다운로드
$version = (Invoke-RestMethod https://raw.githubusercontent.com/argoproj/argo-cd/stable/VERSION)
$url = "https://github.com/argoproj/argo-cd/releases/download/v$version/argocd-windows-amd64.exe"
Invoke-WebRequest -Uri $url -OutFile argocd.exe

# PATH에 추가하거나 원하는 위치로 이동
Move-Item argocd.exe C:\Windows\System32\
```

### CLI 자동 완성

```bash
# Bash
echo "source <(argocd completion bash)" >> ~/.bashrc
source ~/.bashrc

# Zsh
echo "source <(argocd completion zsh)" >> ~/.zshrc
source ~/.zshrc
```

## 초기 접근

### 포트 포워딩 (개발/테스트)

```bash
# 백그라운드에서 포트 포워딩
kubectl port-forward svc/argocd-server -n argocd 8080:443 &

# 웹 UI 접근: https://localhost:8080
```

### LoadBalancer 서비스

```bash
# 서비스 타입 변경
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# External IP 확인
kubectl get svc argocd-server -n argocd

# AWS EKS에서는 ELB DNS 이름 사용
```

### Ingress 설정

**NGINX Ingress:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server-ingress
  namespace: argocd
  annotations:
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  rules:
    - host: argocd.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 443
  tls:
    - hosts:
        - argocd.example.com
      secretName: argocd-server-tls
```

**AWS ALB Ingress:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server-ingress
  namespace: argocd
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxx
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS
spec:
  rules:
    - host: argocd.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 443
```

### 초기 비밀번호 가져오기

```bash
# 초기 admin 비밀번호 가져오기
argocd admin initial-password -n argocd

# 또는 직접 Secret에서 가져오기
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

### 로그인

```bash
# CLI 로그인
argocd login localhost:8080

# 또는 도메인으로 로그인
argocd login argocd.example.com

# 비밀번호 변경 (권장)
argocd account update-password
```

### 초기 비밀번호 Secret 삭제

보안을 위해 초기 비밀번호를 변경한 후 Secret을 삭제합니다:

```bash
kubectl -n argocd delete secret argocd-initial-admin-secret
```

## 고가용성 설정

### HA 아키텍처

![로드밸런서가 API 서버로 요청을 분산하고, API 서버는 Redis에 캐시를 저장하며, 애플리케이션 컨트롤러는 리포지토리 서버에서 매니페스트를 가져오고, Redis는 마스터·리플리카·센티널로 구성된 HA 클러스터를 이루는 ArgoCD 고가용성 구성을 보여준다.](../../../assets/diagrams/rendered/ko-gitops-argocd-01-installation-0.svg)

### 컨트롤러 레플리카 설정

Application Controller는 리더 선출 방식으로 동작합니다:

```yaml
# argocd-cmd-params-cm ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # 컨트롤러 샤딩 (대규모 클러스터용)
  controller.sharding.algorithm: round-robin
  controller.sharding.replicas: "3"
```

```yaml
# Controller StatefulSet 패치
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: argocd-application-controller
  namespace: argocd
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: argocd-application-controller
          env:
            - name: ARGOCD_CONTROLLER_REPLICAS
              value: "3"
```

### Redis HA 설정

```yaml
# Helm values for Redis HA
redis-ha:
  enabled: true
  exporter:
    enabled: true
  haproxy:
    enabled: true
    replicas: 3
  redis:
    replicas: 3
  sentinel:
    replicas: 3

redis:
  enabled: false
```

### 저장소 서버 스케일링

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-repo-server
  namespace: argocd
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: argocd-repo-server
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2000m
              memory: 4Gi
          # 병렬 매니페스트 생성
          env:
            - name: ARGOCD_REPO_SERVER_PARALLELISM_LIMIT
              value: "50"
```

### PodDisruptionBudget

```yaml
# API Server PDB
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: argocd-server-pdb
  namespace: argocd
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
---
# Repo Server PDB
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: argocd-repo-server-pdb
  namespace: argocd
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-repo-server
---
# Controller PDB
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: argocd-application-controller-pdb
  namespace: argocd
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-application-controller
```

## Amazon EKS 통합

### IRSA (IAM Roles for Service Accounts) 설정

EKS에서 ArgoCD가 AWS 리소스에 접근하려면 IRSA를 구성합니다:

**1. IAM 정책 생성:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:argocd/*"
    }
  ]
}
```

**2. IAM 역할 생성:**

```bash
# OIDC Provider 확인
aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text

# IAM 역할 생성 (eksctl 사용)
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=argocd \
  --name=argocd-application-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/ArgoCD-Policy \
  --approve
```

**3. ServiceAccount 어노테이션:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-application-controller
  namespace: argocd
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Role
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Role
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-repo-server
  namespace: argocd
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ArgoCD-Role
```

### ALB Ingress 전체 예시

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:123456789012:certificate/xxx
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
    # WAF 연동 (선택)
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:ap-northeast-2:123456789012:regional/webacl/argocd-waf/xxx
    # 액세스 로그 (선택)
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-logs-bucket,access_logs.s3.prefix=argocd
spec:
  rules:
    - host: argocd.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 443
```

### EKS 클러스터 등록

```bash
# 다른 EKS 클러스터 컨텍스트 가져오기
aws eks update-kubeconfig --name target-cluster --region ap-northeast-2 --alias target-cluster

# ArgoCD에 클러스터 등록
argocd cluster add target-cluster

# 등록된 클러스터 확인
argocd cluster list
```

**선언적 클러스터 등록:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: target-cluster-secret
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: target-cluster
  server: https://xxx.eks.amazonaws.com
  config: |
    {
      "awsAuthConfig": {
        "clusterName": "target-cluster",
        "roleARN": "arn:aws:iam::123456789012:role/ArgoCD-Cluster-Role"
      }
    }
```

## 선언적 설정

### argocd-cm ConfigMap

ArgoCD의 주요 설정을 관리합니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  # 서버 URL
  url: https://argocd.example.com

  # 익명 접근 비활성화
  users.anonymous.enabled: "false"

  # 관리자 비활성화 (SSO 사용 시)
  admin.enabled: "false"

  # 리소스 상태 커스터마이징
  resource.customizations: |
    argoproj.io/Rollout:
      health.lua: |
        hs = {}
        if obj.status ~= nil then
          if obj.status.phase == "Healthy" then
            hs.status = "Healthy"
            hs.message = "Rollout is healthy"
          elseif obj.status.phase == "Paused" then
            hs.status = "Suspended"
            hs.message = "Rollout is paused"
          elseif obj.status.phase == "Progressing" then
            hs.status = "Progressing"
            hs.message = "Rollout is progressing"
          else
            hs.status = "Degraded"
            hs.message = "Rollout is degraded"
          end
        end
        return hs

  # Kustomize 버전 설정
  kustomize.version.v5.0.0: /custom-tools/kustomize_5.0.0

  # 저장소 자격 증명 템플릿
  repository.credentials: |
    - url: https://github.com/myorg
      passwordSecret:
        name: github-creds
        key: password
      usernameSecret:
        name: github-creds
        key: username
```

### argocd-cmd-params-cm ConfigMap

컴포넌트별 매개변수를 설정합니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # API Server
  server.insecure: "true"  # TLS 종료가 LB에서 처리될 때
  server.basehref: /argocd  # 서브 경로 사용 시
  server.rootpath: /argocd

  # Application Controller
  controller.operation.processors: "25"
  controller.status.processors: "50"
  controller.repo.server.timeout.seconds: "180"
  controller.self.heal.timeout.seconds: "5"

  # Repo Server
  reposerver.parallelism.limit: "50"

  # ApplicationSet Controller
  applicationsetcontroller.policy: sync
  applicationsetcontroller.enable.progressive.syncs: "true"
```

### 저장소 자격 증명 설정

**HTTPS (사용자명/비밀번호):**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: private-repo-creds
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/private-repo
  username: my-username
  password: ghp_xxxxxxxxxxxx  # GitHub Personal Access Token
```

**SSH 키:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: private-repo-ssh
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: git@github.com:myorg/private-repo.git
  sshPrivateKey: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    ...
    -----END OPENSSH PRIVATE KEY-----
```

**GitHub App:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: github-app-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg
  githubAppID: "123456"
  githubAppInstallationID: "12345678"
  githubAppPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
```

## 설치 검증

```bash
# 모든 컴포넌트 상태 확인
kubectl get all -n argocd

# ArgoCD 버전 확인
argocd version

# 클러스터 연결 확인
argocd cluster list

# 저장소 연결 확인
argocd repo list

# 헬스 체크
kubectl get pods -n argocd -o wide
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
```

## 다음 단계

1. **[Application 심층 분석](02-applications.md)**: Application CRD를 사용하여 첫 번째 애플리케이션을 배포하세요.

2. **[동기화 전략](03-sync-strategies.md)**: 자동 동기화와 동기화 정책을 구성하세요.

3. **[보안](07-security.md)**: SSO를 설정하고 비밀번호 기반 인증에서 전환하세요.

## 참고 자료

- [ArgoCD 설치 문서](https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/)
- [ArgoCD HA 가이드](https://argo-cd.readthedocs.io/en/stable/operator-manual/high_availability/)
- [EKS Blueprints - ArgoCD](https://aws-ia.github.io/terraform-aws-eks-blueprints/add-ons/argocd/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [설치 및 구성 퀴즈](../../quizzes/gitops/argocd/01-installation-quiz.md)를 풀어보세요.
