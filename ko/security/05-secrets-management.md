# 시크릿 관리 (Secrets Management)

> **지원 버전**: Kubernetes 1.31, 1.32, 1.33
> **마지막 업데이트**: 2025년 2월 21일

Kubernetes 시크릿 관리는 애플리케이션 보안의 핵심입니다. 이 문서에서는 네이티브 Secrets부터 External Secrets Operator, Sealed Secrets, HashiCorp Vault, SOPS까지 다양한 시크릿 관리 도구를 상세히 다룹니다.

## 목차

1. [Kubernetes 네이티브 Secrets](#kubernetes-네이티브-secrets)
2. [External Secrets Operator (ESO)](#external-secrets-operator-eso)
3. [AWS Secrets Manager 통합](#aws-secrets-manager-통합)
4. [AWS Systems Manager Parameter Store 통합](#aws-systems-manager-parameter-store-통합)
5. [Sealed Secrets](#sealed-secrets)
6. [HashiCorp Vault 통합](#hashicorp-vault-통합)
7. [SOPS (Secrets OPerationS)](#sops-secrets-operations)
8. [EKS Pod Identity와 IRSA](#eks-pod-identity와-irsa)
9. [도구 비교](#도구-비교)
10. [모범 사례](#모범-사례)

---

## Kubernetes 네이티브 Secrets

### Secret 개요

Kubernetes Secret은 암호, 토큰, 키와 같은 민감한 정보를 저장하는 오브젝트입니다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  namespace: default
type: Opaque
data:
  # Base64 인코딩된 값
  username: YWRtaW4=          # admin
  password: cGFzc3dvcmQxMjM=  # password123
```

### Secret 유형

| Type | 설명 | 사용 사례 |
|------|------|----------|
| `Opaque` | 기본 타입, 임의의 데이터 저장 | 일반적인 시크릿 |
| `kubernetes.io/service-account-token` | 서비스 어카운트 토큰 | 자동 생성 |
| `kubernetes.io/dockerconfigjson` | Docker 레지스트리 인증 | 이미지 풀 시크릿 |
| `kubernetes.io/basic-auth` | 기본 인증 정보 | 사용자명/비밀번호 |
| `kubernetes.io/ssh-auth` | SSH 인증 | SSH 키 |
| `kubernetes.io/tls` | TLS 인증서 | HTTPS 인증서 |

### Secret 생성 방법

```bash
# 리터럴에서 생성
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=secret123

# 파일에서 생성
kubectl create secret generic ssh-key \
  --from-file=id_rsa=/path/to/id_rsa \
  --from-file=id_rsa.pub=/path/to/id_rsa.pub

# TLS Secret 생성
kubectl create secret tls my-tls-secret \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem

# Docker 레지스트리 Secret
kubectl create secret docker-registry regcred \
  --docker-server=myregistry.io \
  --docker-username=user \
  --docker-password=password
```

### Secret 사용 방법

```yaml
# 환경 변수로 사용
apiVersion: v1
kind: Pod
metadata:
  name: secret-env-pod
spec:
  containers:
  - name: app
    image: myapp:latest
    env:
      # 개별 키 참조
      - name: DB_USERNAME
        valueFrom:
          secretKeyRef:
            name: db-credentials
            key: username
      - name: DB_PASSWORD
        valueFrom:
          secretKeyRef:
            name: db-credentials
            key: password
    # 전체 Secret을 환경 변수로
    envFrom:
      - secretRef:
          name: app-config
---
# 볼륨으로 마운트
apiVersion: v1
kind: Pod
metadata:
  name: secret-volume-pod
spec:
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
      - name: secret-volume
        mountPath: /etc/secrets
        readOnly: true
  volumes:
    - name: secret-volume
      secret:
        secretName: db-credentials
        # 특정 키만 마운트
        items:
          - key: username
            path: db-user
          - key: password
            path: db-pass
            mode: 0400  # 파일 권한
```

### Secret의 한계

```
┌─────────────────────────────────────────────────────────────────┐
│                  Kubernetes Native Secrets 한계                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Base64 인코딩 ≠ 암호화                                       │
│     - Base64는 쉽게 디코딩 가능                                  │
│     - 실제 보안을 제공하지 않음                                   │
│                                                                 │
│  2. etcd에 평문 저장 (기본 설정)                                  │
│     - etcd 접근 권한이 있으면 Secret 노출                        │
│     - 암호화 at rest 별도 구성 필요                              │
│                                                                 │
│  3. Git에 커밋 불가                                              │
│     - YAML에 민감한 정보 포함                                    │
│     - GitOps 워크플로우와 충돌                                   │
│                                                                 │
│  4. 로테이션 어려움                                              │
│     - 수동으로 Secret 업데이트 필요                              │
│     - 자동 로테이션 미지원                                       │
│                                                                 │
│  5. 감사 추적 제한                                               │
│     - Secret 접근 로깅 제한적                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### etcd 암호화 구성

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      # AES-CBC 암호화 (권장)
      - aescbc:
          keys:
            - name: key1
              secret: <32-byte-base64-encoded-key>
      # AWS KMS 사용 (EKS)
      - kms:
          name: aws-kms
          endpoint: unix:///var/run/kmsplugin/socket.sock
          cachesize: 100
          timeout: 3s
      # 평문 (폴백)
      - identity: {}
```

---

## External Secrets Operator (ESO)

### ESO 개요

External Secrets Operator는 외부 시크릿 관리 시스템과 Kubernetes를 연결하여 Secret을 자동으로 동기화합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    External Secrets Operator 아키텍처                    │
│                                                                         │
│  ┌─────────────────┐         ┌─────────────────┐                       │
│  │  ExternalSecret │────────▶│ ESO Controller  │                       │
│  │     (CRD)       │         │                 │                       │
│  └─────────────────┘         └────────┬────────┘                       │
│                                       │                                 │
│  ┌─────────────────┐                  │                                 │
│  │   SecretStore   │◀─────────────────┤                                 │
│  │     (CRD)       │                  │                                 │
│  └────────┬────────┘                  │                                 │
│           │                           │                                 │
│           ▼                           ▼                                 │
│  ┌─────────────────┐         ┌─────────────────┐                       │
│  │ External Secret │         │   Kubernetes    │                       │
│  │    Provider     │         │     Secret      │                       │
│  │ (AWS, Vault, )  │         │   (자동 생성)    │                       │
│  └─────────────────┘         └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### ESO 설치

```bash
# Helm을 사용한 설치
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets \
  --create-namespace \
  --set installCRDs=true
```

### SecretStore 구성

```yaml
# 네임스페이스 범위 SecretStore
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        # IRSA 사용 (권장)
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
# 클러스터 범위 ClusterSecretStore
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secretsmanager-cluster
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
```

### ExternalSecret 정의

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  # 새로고침 간격
  refreshInterval: 1h

  # SecretStore 참조
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore

  # 생성될 Kubernetes Secret
  target:
    name: db-secret
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        # 템플릿 사용
        connection-string: "postgresql://{{ .username }}:{{ .password }}@db.example.com:5432/mydb"

  # 외부 시크릿에서 데이터 가져오기
  data:
    - secretKey: username
      remoteRef:
        key: production/database
        property: username

    - secretKey: password
      remoteRef:
        key: production/database
        property: password
---
# 전체 시크릿 동기화
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: full-secret-sync
  namespace: production
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: app-secrets
  dataFrom:
    - extract:
        key: production/app-config
```

### PushSecret (역방향 동기화)

```yaml
# Kubernetes Secret을 외부 시스템으로 푸시
apiVersion: external-secrets.io/v1alpha1
kind: PushSecret
metadata:
  name: push-to-aws
  namespace: production
spec:
  # 새로고침 간격
  refreshInterval: 10m

  # SecretStore 참조
  secretStoreRefs:
    - name: aws-secretsmanager
      kind: SecretStore

  # 소스 Kubernetes Secret
  selector:
    secret:
      name: local-secret

  # 푸시 대상
  data:
    - match:
        secretKey: api-key
        remoteRef:
          remoteKey: production/api-keys
          property: api-key
```

---

## AWS Secrets Manager 통합

### IRSA 설정

```bash
# IAM 정책 생성
cat <<EOF > secrets-manager-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecrets"
            ],
            "Resource": [
                "arn:aws:secretsmanager:ap-northeast-2:*:secret:production/*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name EKSSecretsManagerPolicy \
    --policy-document file://secrets-manager-policy.json

# IRSA 설정
eksctl create iamserviceaccount \
    --name external-secrets-sa \
    --namespace external-secrets \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/EKSSecretsManagerPolicy \
    --approve
```

### AWS Secrets Manager에 시크릿 생성

```bash
# 시크릿 생성
aws secretsmanager create-secret \
    --name production/database \
    --secret-string '{"username":"admin","password":"supersecret123","host":"db.example.com"}'

# 시크릿 업데이트
aws secretsmanager update-secret \
    --secret-id production/database \
    --secret-string '{"username":"admin","password":"newsecret456","host":"db.example.com"}'

# 자동 로테이션 설정
aws secretsmanager rotate-secret \
    --secret-id production/database \
    --rotation-lambda-arn arn:aws:lambda:ap-northeast-2:123456789012:function:SecretsManagerRotation \
    --rotation-rules AutomaticallyAfterDays=30
```

### 완전한 AWS ESO 예시

```yaml
---
# 1. Service Account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: external-secrets-sa
  namespace: external-secrets
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSSecretsManagerRole
---
# 2. ClusterSecretStore
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
# 3. ExternalSecret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: production-db
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
    - secretKey: DB_HOST
      remoteRef:
        key: production/database
        property: host
    - secretKey: DB_USER
      remoteRef:
        key: production/database
        property: username
    - secretKey: DB_PASS
      remoteRef:
        key: production/database
        property: password
---
# 4. Application Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api
        image: myapi:latest
        envFrom:
          - secretRef:
              name: db-credentials
```

---

## AWS Systems Manager Parameter Store 통합

### Parameter Store 설정

```bash
# 파라미터 생성
aws ssm put-parameter \
    --name "/production/api/key" \
    --value "api-key-value" \
    --type "SecureString" \
    --key-id "alias/aws/ssm"

aws ssm put-parameter \
    --name "/production/database/password" \
    --value "db-password" \
    --type "SecureString"

# 파라미터 조회
aws ssm get-parameter \
    --name "/production/api/key" \
    --with-decryption
```

### ESO Parameter Store 구성

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-parameter-store
spec:
  provider:
    aws:
      service: ParameterStore
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ssm-parameters
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-parameter-store
    kind: ClusterSecretStore
  target:
    name: app-config
  data:
    - secretKey: API_KEY
      remoteRef:
        key: /production/api/key
    - secretKey: DB_PASSWORD
      remoteRef:
        key: /production/database/password
```

---

## Sealed Secrets

### Sealed Secrets 개요

Sealed Secrets는 암호화된 Secret을 Git에 안전하게 저장할 수 있게 해주는 도구입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Sealed Secrets 워크플로우                             │
│                                                                         │
│  개발자 워크스테이션                          Kubernetes 클러스터         │
│  ┌─────────────────┐                        ┌─────────────────────┐    │
│  │  Secret YAML    │                        │  Sealed Secrets     │    │
│  │  (평문)         │                        │  Controller         │    │
│  └────────┬────────┘                        └──────────┬──────────┘    │
│           │                                            │               │
│           ▼                                            │               │
│  ┌─────────────────┐                                   │               │
│  │   kubeseal      │◀──── 공개 키 ────────────────────┘               │
│  │   (암호화)      │                                                   │
│  └────────┬────────┘                                   │               │
│           │                                            │               │
│           ▼                                            ▼               │
│  ┌─────────────────┐     ┌───────┐          ┌─────────────────────┐   │
│  │  SealedSecret   │────▶│  Git  │─────────▶│    복호화 후         │   │
│  │  (암호화됨)     │     └───────┘          │  Kubernetes Secret   │   │
│  └─────────────────┘                        │       생성           │   │
│                                             └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Sealed Secrets 설치

```bash
# Controller 설치
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo update

helm install sealed-secrets sealed-secrets/sealed-secrets \
    -n kube-system \
    --set fullnameOverride=sealed-secrets-controller

# kubeseal CLI 설치
KUBESEAL_VERSION=$(curl -s https://api.github.com/repos/bitnami-labs/sealed-secrets/releases/latest | jq -r .tag_name | cut -c2-)
curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
tar -xvzf kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

### SealedSecret 생성

```bash
# 공개 키 가져오기 (오프라인 사용)
kubeseal --fetch-cert \
    --controller-name=sealed-secrets-controller \
    --controller-namespace=kube-system \
    > sealed-secrets-pub.pem

# Secret YAML 생성
cat <<EOF > secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  namespace: production
type: Opaque
stringData:
  username: admin
  password: supersecret123
EOF

# SealedSecret으로 변환
kubeseal --format yaml < secret.yaml > sealed-secret.yaml

# 또는 공개 키 파일 사용
kubeseal --cert sealed-secrets-pub.pem --format yaml < secret.yaml > sealed-secret.yaml
```

### SealedSecret YAML

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: my-secret
  namespace: production
spec:
  encryptedData:
    username: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEq...
    password: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEq...
  template:
    type: Opaque
    metadata:
      name: my-secret
      namespace: production
      labels:
        app: my-app
```

### 스코프 설정

```bash
# strict (기본): namespace + name 모두 바인딩
kubeseal --scope strict

# namespace-wide: 같은 namespace 내 다른 이름으로 사용 가능
kubeseal --scope namespace-wide

# cluster-wide: 어떤 namespace에서든 사용 가능
kubeseal --scope cluster-wide
```

### 키 로테이션

```bash
# 현재 키 백업
kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key=active -o yaml > sealed-secrets-key.yaml

# 새 키 생성 (자동으로 30일마다)
# Controller가 자동으로 새 키 생성

# 기존 SealedSecret 재암호화
kubeseal --re-encrypt < sealed-secret.yaml > sealed-secret-new.yaml
```

---

## HashiCorp Vault 통합

### Vault 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HashiCorp Vault + Kubernetes                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Vault Server                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Secrets   │  │    Auth     │  │   Audit     │             │   │
│  │  │   Engine    │  │   Methods   │  │    Log      │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────┬───────────────────────────────────────┘   │
│                            │                                            │
│         ┌──────────────────┼──────────────────┐                        │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │
│  │ CSI Driver  │    │   Agent     │    │  ArgoCD     │                │
│  │             │    │  Injector   │    │  Vault      │                │
│  │             │    │             │    │  Plugin     │                │
│  └─────────────┘    └─────────────┘    └─────────────┘                │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Kubernetes Pods                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Vault 설치 (Helm)

```bash
# Vault Helm 차트 설치
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# 개발 모드 설치 (테스트용)
helm install vault hashicorp/vault \
    -n vault \
    --create-namespace \
    --set "server.dev.enabled=true"

# 프로덕션 설치
helm install vault hashicorp/vault \
    -n vault \
    --create-namespace \
    -f vault-values.yaml
```

```yaml
# vault-values.yaml
server:
  ha:
    enabled: true
    replicas: 3
    raft:
      enabled: true

  dataStorage:
    enabled: true
    size: 10Gi
    storageClass: gp3

  auditStorage:
    enabled: true
    size: 10Gi

injector:
  enabled: true
  replicas: 2

csi:
  enabled: true
```

### Kubernetes 인증 설정

```bash
# Vault에 Kubernetes 인증 활성화
vault auth enable kubernetes

# Kubernetes 인증 구성
vault write auth/kubernetes/config \
    kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
    token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# 정책 생성
vault policy write app-policy - <<EOF
path "secret/data/production/*" {
  capabilities = ["read"]
}
EOF

# Role 생성 (ServiceAccount 바인딩)
vault write auth/kubernetes/role/app-role \
    bound_service_account_names=app-sa \
    bound_service_account_namespaces=production \
    policies=app-policy \
    ttl=24h
```

### Vault Agent Injector

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: production
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
      annotations:
        # Vault Agent Injector 어노테이션
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "app-role"

        # 시크릿 주입
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/production/config"
        vault.hashicorp.com/agent-inject-template-config: |
          {{- with secret "secret/data/production/config" -}}
          export DB_HOST="{{ .Data.data.db_host }}"
          export DB_USER="{{ .Data.data.db_user }}"
          export DB_PASS="{{ .Data.data.db_pass }}"
          {{- end }}
    spec:
      serviceAccountName: app-sa
      containers:
      - name: app
        image: myapp:latest
        command: ["/bin/sh", "-c"]
        args:
          - source /vault/secrets/config && /app/start.sh
```

### Vault CSI Driver

```yaml
# SecretProviderClass 정의
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: vault-database
  namespace: production
spec:
  provider: vault
  parameters:
    vaultAddress: "http://vault.vault:8200"
    roleName: "app-role"
    objects: |
      - objectName: "db-password"
        secretPath: "secret/data/production/database"
        secretKey: "password"
      - objectName: "db-username"
        secretPath: "secret/data/production/database"
        secretKey: "username"
  # Kubernetes Secret으로 동기화 (선택)
  secretObjects:
    - secretName: vault-db-creds
      type: Opaque
      data:
        - objectName: db-password
          key: password
        - objectName: db-username
          key: username
---
# Pod에서 사용
apiVersion: v1
kind: Pod
metadata:
  name: app-csi
  namespace: production
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
    - name: secrets-store
      mountPath: "/mnt/secrets"
      readOnly: true
    env:
      - name: DB_PASSWORD
        valueFrom:
          secretKeyRef:
            name: vault-db-creds
            key: password
  volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: vault-database
```

### ArgoCD Vault Plugin (AVP)

```yaml
# ArgoCD ConfigMap에 AVP 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  configManagementPlugins: |
    - name: argocd-vault-plugin
      generate:
        command: ["argocd-vault-plugin"]
        args: ["generate", "./"]
---
# Application에서 AVP 사용
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
spec:
  source:
    repoURL: https://github.com/myorg/my-app
    path: k8s
    plugin:
      name: argocd-vault-plugin
---
# AVP 플레이스홀더가 있는 Secret
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  annotations:
    avp.kubernetes.io/path: "secret/data/production/database"
type: Opaque
stringData:
  username: <username>
  password: <password>
```

---

## SOPS (Secrets OPerationS)

### SOPS 개요

SOPS는 암호화된 파일을 관리하는 도구로, Age, PGP, AWS KMS 등 다양한 암호화 백엔드를 지원합니다.

### SOPS 설치 및 설정

```bash
# SOPS 설치
brew install sops  # macOS
# 또는
curl -LO https://github.com/getsops/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64
chmod +x sops-v3.8.1.linux.amd64
sudo mv sops-v3.8.1.linux.amd64 /usr/local/bin/sops

# Age 키 생성
age-keygen -o key.txt
# Public key: age1...
# Secret key: AGE-SECRET-KEY-...

# .sops.yaml 설정
cat <<EOF > .sops.yaml
creation_rules:
  - path_regex: .*secrets.*\.yaml$
    age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
  - path_regex: .*\.enc\.yaml$
    aws_kms: arn:aws:kms:ap-northeast-2:123456789012:key/abc-123
EOF
```

### SOPS로 Secret 암호화

```bash
# Secret 파일 생성
cat <<EOF > secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  api-key: my-secret-api-key
  db-password: super-secret-password
EOF

# 암호화
sops -e secrets.yaml > secrets.enc.yaml

# 복호화
sops -d secrets.enc.yaml > secrets.yaml

# 직접 편집 (복호화 → 편집 → 재암호화)
sops secrets.enc.yaml
```

### 암호화된 파일 형식

```yaml
# secrets.enc.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  api-key: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
  db-password: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
sops:
  kms: []
  gcp_kms: []
  azure_kv: []
  hc_vault: []
  age:
    - recipient: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
      enc: |
        -----BEGIN AGE ENCRYPTED FILE-----
        ...
        -----END AGE ENCRYPTED FILE-----
  lastmodified: "2026-02-21T10:00:00Z"
  mac: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
  version: 3.8.1
```

### FluxCD SOPS 통합

```yaml
# FluxCD Kustomization with SOPS
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app
  namespace: flux-system
spec:
  interval: 10m
  path: ./k8s
  prune: true
  sourceRef:
    kind: GitRepository
    name: my-repo
  # SOPS 복호화 활성화
  decryption:
    provider: sops
    secretRef:
      name: sops-age
---
# Age 키를 담은 Secret
apiVersion: v1
kind: Secret
metadata:
  name: sops-age
  namespace: flux-system
type: Opaque
stringData:
  age.agekey: |
    AGE-SECRET-KEY-1QFPJKM...
```

### AWS KMS with SOPS

```bash
# KMS 키로 암호화
sops --kms arn:aws:kms:ap-northeast-2:123456789012:key/abc-123 \
     -e secrets.yaml > secrets.enc.yaml

# 여러 키 사용 (키 로테이션 대비)
sops --kms "arn:aws:kms:ap-northeast-2:123456789012:key/abc-123,arn:aws:kms:us-east-1:123456789012:key/def-456" \
     -e secrets.yaml > secrets.enc.yaml
```

---

## EKS Pod Identity와 IRSA

### IRSA (IAM Roles for Service Accounts)

```yaml
# 1. IAM 정책 및 역할 생성
# eksctl을 사용한 IRSA 설정
# eksctl create iamserviceaccount \
#   --name my-app-sa \
#   --namespace production \
#   --cluster my-cluster \
#   --attach-policy-arn arn:aws:iam::123456789012:policy/MyAppPolicy \
#   --approve

# 2. ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/MyAppRole
---
# 3. Pod에서 ServiceAccount 사용
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
    # AWS SDK가 자동으로 IAM Role 자격 증명 사용
```

### EKS Pod Identity (신규)

```bash
# EKS Pod Identity Agent 설치
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent

# Pod Identity 연결 생성
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

```yaml
# Pod Identity를 사용하는 ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
  # 어노테이션 불필요 (Pod Identity Association으로 관리)
---
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
```

### IRSA vs Pod Identity 비교

| 특성 | IRSA | EKS Pod Identity |
|------|------|------------------|
| **설정 방식** | ServiceAccount 어노테이션 | API/콘솔에서 연결 |
| **IAM 역할 관리** | OIDC 트러스트 정책 필요 | EKS 관리형 |
| **토큰 형식** | OIDC 토큰 | EKS Pod Identity 토큰 |
| **역할 재사용** | 클러스터별 설정 필요 | 여러 클러스터에서 재사용 |
| **감사** | CloudTrail + ServiceAccount | CloudTrail + Pod 수준 |
| **권장 사용** | 기존 클러스터 | 신규 클러스터 |

---

## 도구 비교

### 시크릿 관리 도구 비교표

| 특성 | Native Secrets | ESO | Sealed Secrets | Vault | SOPS |
|------|---------------|-----|----------------|-------|------|
| **Git 저장** | ✗ | ✗ (외부 저장) | ✓ | ✗ | ✓ |
| **자동 로테이션** | ✗ | ✓ | ✗ | ✓ | ✗ |
| **중앙 집중 관리** | ✗ | ✓ | ✗ | ✓ | ✗ |
| **감사 로그** | 제한적 | 제공자 의존 | ✗ | ✓ | ✗ |
| **복잡성** | 낮음 | 중간 | 낮음 | 높음 | 낮음 |
| **외부 의존성** | 없음 | 외부 저장소 | Controller | Vault 서버 | 없음 |
| **암호화** | etcd 암호화 | 제공자 암호화 | 비대칭 암호화 | 자체 암호화 | 다양한 백엔드 |
| **GitOps 친화** | ✗ | ✓ | ✓ | Plugin 필요 | ✓ |
| **EKS 통합** | 기본 | 우수 | 보통 | 우수 | 보통 |

### 사용 사례별 권장

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        사용 사례별 권장 도구                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  소규모/단순 환경                                                        │
│  └─▶ Sealed Secrets + GitOps                                           │
│                                                                         │
│  AWS 중심 환경                                                          │
│  └─▶ ESO + AWS Secrets Manager + IRSA/Pod Identity                     │
│                                                                         │
│  멀티 클라우드/하이브리드                                                 │
│  └─▶ HashiCorp Vault                                                   │
│                                                                         │
│  GitOps 우선                                                            │
│  └─▶ SOPS + FluxCD 또는 Sealed Secrets + ArgoCD                        │
│                                                                         │
│  엔터프라이즈 (감사/규정 준수)                                            │
│  └─▶ HashiCorp Vault + ESO                                             │
│                                                                         │
│  개발/테스트 환경                                                        │
│  └─▶ Kubernetes Native Secrets + etcd 암호화                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 모범 사례

### 1. 시크릿 생성 및 저장

```yaml
# 절대 하지 말 것
apiVersion: v1
kind: Secret
metadata:
  name: bad-practice
stringData:
  password: "hardcoded-password"  # Git에 커밋됨!

# 권장: External Secrets 또는 Sealed Secrets 사용
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: good-practice
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: my-secret
  data:
    - secretKey: password
      remoteRef:
        key: production/database
        property: password
```

### 2. 최소 권한 원칙

```yaml
# RBAC으로 Secret 접근 제한
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["app-config"]  # 특정 Secret만
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-secret-reader
  namespace: production
subjects:
  - kind: ServiceAccount
    name: app-sa
    namespace: production
roleRef:
  kind: Role
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### 3. 시크릿 로테이션

```bash
#!/bin/bash
# secret-rotation.sh

# AWS Secrets Manager에서 자동 로테이션 설정
aws secretsmanager rotate-secret \
    --secret-id production/database \
    --rotation-lambda-arn arn:aws:lambda:ap-northeast-2:123456789012:function:RotateSecret \
    --rotation-rules '{"ScheduleExpression": "rate(30 days)"}'

# ESO가 자동으로 새 값 동기화 (refreshInterval 설정)
```

### 4. 감사 및 모니터링

```yaml
# Falco 규칙으로 Secret 접근 모니터링
- rule: Unauthorized Secret Access
  desc: Detect unauthorized access to secrets
  condition: >
    kevt and
    ka.verb in (get, list) and
    ka.target.resource = secrets and
    not ka.user.name in (system:serviceaccount:kube-system:*)
  output: >
    Unauthorized secret access
    (user=%ka.user.name verb=%ka.verb secret=%ka.target.name
    namespace=%ka.target.namespace)
  priority: WARNING
  tags: [k8s, secrets]
```

### 5. 개발 환경 분리

```yaml
# 환경별 SecretStore 분리
---
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: dev-secrets
  namespace: development
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: dev-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: prod-secrets
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: prod-secrets-sa
```

---

## 요약

Kubernetes 시크릿 관리는 보안의 핵심입니다:

1. **Native Secrets**: 간단하지만 Base64 인코딩만 제공
2. **External Secrets Operator**: 외부 시크릿 저장소와 동기화
3. **Sealed Secrets**: Git에 안전하게 암호화된 시크릿 저장
4. **HashiCorp Vault**: 엔터프라이즈급 중앙 집중 시크릿 관리
5. **SOPS**: 파일 기반 암호화로 GitOps 친화적

### 핵심 권장사항

- 프로덕션에서는 Native Secrets만 사용하지 않기
- 시크릿을 절대 Git에 평문으로 커밋하지 않기
- 자동 로테이션 구현
- 최소 권한 원칙 적용
- 시크릿 접근 감사 활성화

---

## 참고 자료

- [Kubernetes Secrets 공식 문서](https://kubernetes.io/docs/concepts/configuration/secret/)
- [External Secrets Operator](https://external-secrets.io/)
- [Sealed Secrets](https://sealed-secrets.netlify.app/)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [SOPS](https://github.com/getsops/sops)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
