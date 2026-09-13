# ArgoCD 보안

> **검토 기준**: Argo CD 3.5.2, Sealed Secrets 0.40.0/chart 2.20.0, ESO 2.10.0, AVP 1.18.1, KSOPS 4.5.1, SOPS 3.13.3
> **마지막 업데이트**: 2026년 9월 11일

## 목차

- [SSO 통합](#sso-통합)
- [시크릿 관리](#시크릿-관리)
- [TLS 구성](#tls-구성)
- [감사 로깅](#감사-로깅)
- [네트워크 보안](#네트워크-보안)
- [저장소 자격 증명](#저장소-자격-증명)
- [GPG 서명 검증](#gpg-서명-검증)

## SSO 통합

각 SSO 예제는 대안이며 기존 ConfigMap/Secret에 필요한 필드를 병합합니다. argocd-secret의 서버 서명키·다른 자격 증명을 덮어쓰지 않습니다. 예시 placeholder를 실제 IdP 설정으로 교체하고, 비밀값은 외부 Secret 관리 또는 보호된 파일 입력으로 전달합니다. 본문의 Secret YAML은 구조 설명이며 평문 상태로 Git에 커밋하지 않습니다.

Argo CD는 direct OIDC 또는 Dex identity broker를 통해 SSO를 구성합니다. direct OIDC의 callback은 /auth/callback이며 Dex SAML/LDAP 구성과 구분합니다.

### OIDC (OpenID Connect)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  oidc.config: |
    name: Okta
    issuer: https://myorg.okta.com
    clientID: 0oaxxxxxxxxxx
    clientSecret: $oidc.okta.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
    requestedIDTokenClaims:
      groups:
        essential: true
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-secret
  namespace: argocd
type: Opaque
stringData:
  oidc.okta.clientSecret: your-client-secret
```

### SAML

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  dex.config: |
    connectors:
    - type: saml
      id: okta
      name: Okta SAML
      config:
        ssoURL: https://myorg.okta.com/app/xxx/sso/saml
        caData: BASE64_OF_THE_COMPLETE_IDP_SIGNING_CERTIFICATE_PEM
        redirectURI: https://argocd.example.com/api/dex/callback
        usernameAttr: email
        emailAttr: email
        groupsAttr: groups
```

### LDAP / Active Directory

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  dex.config: |
    connectors:
    - type: ldap
      id: ldap
      name: LDAP
      config:
        host: ldap.example.com:636
        insecureNoSSL: false
        insecureSkipVerify: false
        rootCA: /etc/dex/ldap-ca/ca.crt
        bindDN: cn=argocd-reader,ou=Service Accounts,dc=example,dc=com
        bindPW: $dex.ldap.bindPW
        usernamePrompt: Username
        userSearch:
          baseDN: ou=users,dc=example,dc=com
          filter: (objectClass=person)
          username: uid
          idAttr: uid
          emailAttr: mail
          nameAttr: cn
        groupSearch:
          baseDN: ou=groups,dc=example,dc=com
          filter: (objectClass=groupOfNames)
          userMatchers:
          - userAttr: DN
            groupAttr: member
          nameAttr: cn
```

ldap-ca ConfigMap에 검증한 ca.crt를 준비하고 다음 Helm values를 병합합니다. bindPW는 argocd-secret의 dex.ldap.bindPW 키에 안전하게 공급하며 bindDN은 검색에 필요한 최소 권한 계정을 사용합니다.

```yaml
dex:
  volumes:
  - name: ldap-ca
    configMap:
      name: ldap-ca
  volumeMounts:
  - name: ldap-ca
    mountPath: /etc/dex/ldap-ca
    readOnly: true
```

### Microsoft Entra ID

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  oidc.config: |
    name: Microsoft Entra ID
    issuer: https://login.microsoftonline.com/TENANT_ID/v2.0
    clientID: APPLICATION_ID
    clientSecret: $oidc.azure.clientSecret
    requestedScopes:
    - openid
    - profile
    - email
    requestedIDTokenClaims:
      groups:
        essential: true
```

### AWS IAM Identity Center (SSO)

IAM Identity Center에서는 지원되는 custom SAML 앱을 만들고 앱 할당, ACS URL 및 audience를 /api/dex/callback에 맞춥니다. issuer를 임의의 identitycenter.amazonaws.com 주소로 만든 generic OIDC 설정은 사용할 수 없습니다. email attribute를 명시적으로 매핑하고 Metadata의 sign-on URL/서명 인증서를 사용합니다. 동적 그룹 attribute mapping은 공식 지원을 가정하지 않으며 실제 assertion을 확인합니다. 아래는 email claim을 사용하는 경로입니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  dex.config: |
    connectors:
    - type: saml
      id: identity-center
      name: AWS IAM Identity Center
      config:
        ssoURL: https://portal.sso.ap-northeast-2.amazonaws.com/saml/assertion/APP_ID
        caData: BASE64_OF_THE_COMPLETE_IDP_SIGNING_CERTIFICATE_PEM
        entityIssuer: https://argocd.example.com/api/dex/callback
        redirectURI: https://argocd.example.com/api/dex/callback
        usernameAttr: email
        emailAttr: email
```

실제 승인된 사용자 email을 제한된 viewer 역할에 연결하는 RBAC data 조각입니다. 역할 정의는 프로젝트/RBAC 장을 참고합니다.

```yaml
data:
  scopes: '[groups, email]'
  policy.identity-center.csv: |
    g, approved.user@example.com, role:viewer
```

### admin 계정 비활성화

별도 SSO 세션에서 필요한 관리자 역할과 복구 경로를 검증한 뒤 로컬 admin을 비활성화합니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  admin.enabled: "false"
```

## 시크릿 관리

Git의 data 필드 base64는 암호화가 아닙니다. 새 구성에서는 ESO·Sealed Secrets처럼 대상 클러스터에서 Secret을 만드는 방식을 우선 검토합니다. AVP/KSOPS로 생성 시 주입하면 평문 값이 repo-server 및 Redis의 생성 매니페스트에 존재할 수 있으므로 같은 보안 모델로 취급하지 않습니다.

암호문 또는 외부 시크릿 참조를 Git에서 관리하는 방법입니다.

### Sealed Secrets

검토 기준은 controller 0.40.0/chart2.20.0입니다. 이전 bitnami-labs Helm 주소는 현재 404이므로 bitnami 저장소를 사용합니다. [공식 릴리스](https://github.com/bitnami/sealed-secrets/releases/tag/v0.40.0)에서 운영체제·아키텍처에 맞는 kubeseal을 설치하고 체크섬을 확인합니다. 대상 Namespace는 플랫폼 관리자가 미리 준비합니다.

```bash
helm repo add sealed-secrets https://bitnami.github.io/sealed-secrets
helm repo update sealed-secrets
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --version 2.20.0 --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller --wait --timeout 5m
kubeseal --version  # use 0.40.0 for this example
```

현재 kubeconfig가 대상 클러스터인지 확인하고, 그 컨트롤러의 공개 인증서로 봉인합니다. 기본 strict 범위는 Secret 이름과 Namespace에 묶이므로 암호화 이후 이름·Namespace만 바꿔 재사용하지 않습니다. 아래 절차는 평문 비밀번호를 Git 파일이나 명령 인자에 넣지 않습니다.

```bash
set -euo pipefail
umask 077
: "${SECRET_INPUT_FILE:?Provide a protected password file outside Git}"
seal_dir="$(mktemp -d)"
trap 'rm -rf "$seal_dir"' EXIT
kubeseal --controller-name sealed-secrets-controller \
  --controller-namespace kube-system --fetch-cert > "$seal_dir/controller.pem"
kubectl create secret generic my-secret --namespace production \
  --from-file=password="$SECRET_INPUT_FILE" --dry-run=client -o yaml \
  | kubeseal --format yaml --cert "$seal_dir/controller.pem" > sealed-secret.yaml
test -s sealed-secret.yaml
```

생성된 SealedSecret만 검토 후 커밋합니다. 예시의 생략된 Ag... 문자열은 유효한 암호문이 아닙니다. 컨트롤러의 복호화 키 백업·복구는 관리자 절차로 보호하고, 봉인 키 갱신과 애플리케이션 시크릿 자체의 회전은 별개임을 구분합니다.

### External Secrets Operator

ESO는 Git의 시크릿을 암호화하는 도구가 아니라 외부 저장소의 값을 대상 클러스터 Secret으로 동기화합니다. 2.10.0 예제는 external-secrets.io/v1을 사용합니다. 아래 AWS jwt.serviceAccountRef는 IRSA 방식이며, 해당 Namespace의 ServiceAccount에 IAM 역할 주석과 OIDC trust를 준비해야 합니다. Pod Identity를 쓰면 컨트롤러 SA 연결과 SDK credential chain을 사용하며 이 jwt 설정과 혼동하지 않습니다.

외부 시크릿 관리 시스템과 통합합니다:

**설치:**

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.10.0 --namespace external-secrets --create-namespace --wait --timeout 5m
```

IRSA용 ServiceAccount 예시입니다. 실제 role ARN/OIDC trust를 설정하고 필요한 secret ARN의 GetSecretValue/DescribeSecret 및 해당 시 KMS Decrypt만 허용합니다. Vault 예제에서는 해당 SA/Namespace와 audience=vault에 바인딩한 Vault 역할, 제한된 KV 경로 및 적절한 reviewer 구성을 준비합니다. Vault 1.21+는 역할 audience 설정을 요구합니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: external-secrets-sa
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/eso-production-reader
automountServiceAccountToken: false
```

**AWS Secrets Manager 연동:**

```yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
  - secretKey: username
    remoteRef:
      key: production/database
      property: username
  - secretKey: password
    remoteRef:
      key: production/database
      property: password
```

### HashiCorp Vault

기존 AVP 통합은 3.5.2에서 CMP sidecar로 구성합니다. 메인 repo-server에 바이너리만 복사하거나 ConfigMap만 만드는 것으로 등록되지 않습니다. ConfigManagementPlugin은 Kubernetes CRD가 아니라 sidecar가 읽을 설정 파일입니다. 생성된 Secret 값은 Redis/repo-server에 평문으로 존재할 수 있으므로 신뢰하는 저장소와 격리된 운영 범위에서 사용합니다.

AVP 1.18.1의 대상 노드 아키텍처 바이너리와 공식 checksums 파일을 검증한 뒤 argocd-vault-plugin이라는 이름으로 빌드 컨텍스트에 둡니다. 아래 이미지를 빌드·검증하고 자신의 레지스트리에 게시한 주소로 Helm values의 image를 교체합니다.

```dockerfile
FROM quay.io/argoproj/argocd:v3.5.2
COPY --chmod=0755 --chown=999:999 argocd-vault-plugin /usr/local/bin/argocd-vault-plugin
USER 999
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: avp-plugin-config
  namespace: argocd
data:
  plugin.yaml: |
    apiVersion: argoproj.io/v1alpha1
    kind: ConfigManagementPlugin
    metadata:
      name: argocd-vault-plugin
    spec:
      generate:
        command:
        - argocd-vault-plugin
        - generate
        - .
```

다음은 argo-cd chart 10.8.4용 values 조각입니다. 기존 values와 합쳐 적용하고 다른 sidecar/volume 배열을 덮어쓰지 않도록 검토합니다. var-files/plugins는 차트가 제공하는 볼륨이며 tmp는 별도입니다.

```yaml
repoServer:
  automountServiceAccountToken: false
  serviceAccount:
    create: true
    name: argocd-repo-server
  extraContainers:
  - name: avp
    image: registry.example.com/argocd-avp:3.5.2-avp1.18.1
    command:
    - /var/run/argocd/argocd-cmp-server
    securityContext:
      runAsNonRoot: true
      runAsUser: 999
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
    env:
    - name: AVP_TYPE
      value: vault
    - name: AVP_AUTH_TYPE
      value: k8s
    - name: AVP_K8S_ROLE
      value: argocd-readonly
    - name: AVP_K8S_MOUNT_PATH
      value: auth/kubernetes
    - name: AVP_K8S_TOKEN_PATH
      value: /var/run/secrets/avp/token
    - name: VAULT_ADDR
      value: https://vault.example.com
    - name: VAULT_CACERT
      value: /etc/vault/ca.crt
    volumeMounts:
    - name: var-files
      mountPath: /var/run/argocd
    - name: plugins
      mountPath: /home/argocd/cmp-server/plugins
    - name: avp-config
      mountPath: /home/argocd/cmp-server/config/plugin.yaml
      subPath: plugin.yaml
      readOnly: true
    - name: avp-tmp
      mountPath: /tmp
    - name: avp-cache
      mountPath: /home/argocd/.avp
    - name: avp-token
      mountPath: /var/run/secrets/avp
      readOnly: true
    - name: vault-ca
      mountPath: /etc/vault
      readOnly: true
  volumes:
  - name: avp-config
    configMap:
      name: avp-plugin-config
  - name: avp-tmp
    emptyDir: {}
  - name: avp-cache
    emptyDir:
      medium: Memory
  - name: avp-token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          audience: vault
          expirationSeconds: 600
  - name: vault-ca
    configMap:
      name: vault-ca
```

Vault에 argocd/argocd-repo-server SA와 audience=vault를 승인한 argocd-readonly 역할, 허용된 경로만 읽는 정책, 적절한 token reviewer를 설정합니다. vault-ca ConfigMap의 ca.crt와 신뢰할 수 있는 TLS 인증서도 필요합니다. 일반 repo-server에 Kubernetes API 권한을 추가하는 것으로 대체하지 않습니다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myapp.git
    targetRevision: main
    path: manifests
    plugin:
      name: argocd-vault-plugin
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: production
  annotations:
    avp.kubernetes.io/path: secret/data/production/database
type: Opaque
stringData:
  username: <username>
  password: <password>
```

Application/project/repository와 Vault KV 경로를 실제 환경에 맞게 제한합니다. 동일한 sidecar의 자격 증명을 서로 신뢰하지 않는 프로젝트 간의 보안 경계로 간주하지 않습니다.

### SOPS (Secrets OPerationS)

SOPS 3.13.3과 KSOPS 4.5.1을 사용하는 예제입니다. age 공개 수신자와 비공개 identity는 분리해 관리합니다. 아래 공개 수신자를 실제 값으로 교체하고 비공개 키는 Git에 넣지 않습니다.

```yaml
creation_rules:
- path_regex: ^secrets/.*\.enc\.yaml$
  encrypted_regex: ^(data|stringData)$
  age: age1_REPLACE_WITH_YOUR_PUBLIC_RECIPIENT
```

```bash
set -euo pipefail
umask 077
: "${KUBERNETES_SECRET_FILE:?Provide a protected Secret YAML file outside Git}"
mkdir -p secrets
sops --encrypt --filename-override secrets/db-secret.enc.yaml \
  "$KUBERNETES_SECRET_FILE" > secrets/db-secret.enc.yaml
test -s secrets/db-secret.enc.yaml
```

creation_rules는 리다이렉션 출력명이 아니라 입력/filename-override 경로를 기준으로 선택됩니다. Argo CD는 SOPS를 기본으로 자동 복호화하지 않습니다. KSOPS 실행 파일, Kustomize의 alpha/exec 기능과 복호화 키가 모두 필요합니다.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: production
generators:
- secret-generator.yaml
```

```yaml
apiVersion: viaduct.ai/v1
kind: ksops
metadata:
  name: secret-generator
  annotations:
    config.kubernetes.io/function: |
      exec:
        path: ksops
files:
- secrets/db-secret.enc.yaml
```

다음은 신뢰하는 저장소 전용 기존 Argo CD 인스턴스에 필요한 Helm values입니다. 전역 exec 허용은 저장소의 실행 코드를 신뢰한다는 의미이므로, 서로 신뢰하지 않는 프로젝트를 공유하지 않습니다. 새 환경은 대상 클러스터 Secret 관리를 우선 검토합니다.

```yaml
configs:
  cm:
    kustomize.buildOptions: --enable-alpha-plugins --enable-exec
repoServer:
  env:
  - name: SOPS_AGE_KEY_FILE
    value: /etc/sops-age/key.txt
  volumes:
  - name: ksops-tools
    emptyDir: {}
  - name: sops-age
    secret:
      secretName: sops-age
  initContainers:
  - name: install-ksops
    image: viaductoss/ksops:v4.5.1
    command:
    - /usr/local/bin/ksops
    - install
    - --with-kustomize
    - /custom-tools
    volumeMounts:
    - name: ksops-tools
      mountPath: /custom-tools
  volumeMounts:
  - name: ksops-tools
    mountPath: /usr/local/bin/kustomize
    subPath: kustomize
  - name: ksops-tools
    mountPath: /usr/local/bin/ksops
    subPath: ksops
  - name: sops-age
    mountPath: /etc/sops-age
    readOnly: true
```

```bash
# Create the Secret from an existing protected age identity file.
kubectl create secret generic sops-age -n argocd \
  --from-file=key.txt=./age-identity.txt
# Validate in a protected local environment; generated output contains plaintext.
umask 077
render_dir="$(mktemp -d)"
trap 'rm -rf "$render_dir"' EXIT
kustomize build --enable-alpha-plugins --enable-exec . > "$render_dir/rendered.yaml"
```

복호화된 출력과 비공개 identity는 커밋하지 않습니다. 위 두 플러그인 설치 예시는 대안이며, 함께 쓰려면 values의 배열/권한/키 범위를 명시적으로 통합해야 합니다.

## TLS 구성

### 서버 인증서

운영 인증서는 신뢰되는 CA와 올바른 SAN을 사용합니다. 외부에서 제공한 인증서는 보호된 파일로 Secret에 넣고 private key를 Git에 저장하지 않습니다.

```bash
: "${TLS_CERT_FILE:?Provide the certificate chain file}"
: "${TLS_KEY_FILE:?Provide the protected private-key file}"
kubectl create secret tls argocd-server-tls -n argocd \
  --cert="$TLS_CERT_FILE" --key="$TLS_KEY_FILE" --dry-run=client -o yaml \
  | kubectl apply --server-side -f -
```

테스트용 자체 서명 인증서도 CN만으로는 충분하지 않습니다. 예를 들어 openssl req에 `-addext "subjectAltName=DNS:argocd.example.com"`을 넣고 클라이언트에 공개 인증서를 신뢰시킵니다. --insecure로 검증을 끄는 방법을 운영 기본값으로 사용하지 않습니다.

### cert-manager 예시

cert-manager와 신뢰된 letsencrypt-prod ClusterIssuer가 이미 준비된 경우입니다. private 서비스는 DNS01 등 적절한 solver를 먼저 설정합니다. 유지보수가 종료된 ingress-nginx HTTP01 설정을 새 설치의 기본값으로 사용하지 않습니다.

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: argocd-server-tls
  namespace: argocd
spec:
  secretName: argocd-server-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - argocd.example.com
  privateKey:
    algorithm: RSA
    size: 4096
```

### Gateway API의 TLS

아래 예제는 Envoy Gateway 1.9.1의 GatewayClass eg와 Gateway API CRD(v1 BackendTLSPolicy 포함)가 준비되어 있고 위 Certificate가 Ready인 경우입니다. Gateway와 argocd-server가 같은 공개 CA 인증서를 사용하며 server.insecure는 false로 유지합니다. 도메인/DNS와 접근 경계는 환경에 맞게 구성하고 CLI는 --grpc-web을 사용합니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: argocd-gateway
  namespace: argocd
spec:
  gatewayClassName: eg
  listeners:
  - name: https
    hostname: argocd.example.com
    port: 443
    protocol: HTTPS
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: argocd-server-tls
    allowedRoutes:
      namespaces:
        from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: argocd-server
  namespace: argocd
spec:
  parentRefs:
  - name: argocd-gateway
    sectionName: https
  hostnames:
  - argocd.example.com
  rules:
  - backendRefs:
    - name: argocd-server
      port: 443
---
apiVersion: gateway.networking.k8s.io/v1
kind: BackendTLSPolicy
metadata:
  name: argocd-server
  namespace: argocd
spec:
  targetRefs:
  - group: ''
    kind: Service
    name: argocd-server
    sectionName: https
  validation:
    hostname: argocd.example.com
    wellKnownCACertificates: System
```

wellKnownCACertificates:System은 공개 CA 인증서용입니다. 내부 CA/자체 서명 인증서는 해당 신뢰 CA의 caCertificateRefs를 구성해야 합니다. Gateway listener와 Route의 Accepted/ResolvedRefs 및 backend TLS 검증을 확인합니다.

### Git 서버 CA와 내부 RPC TLS

argocd-tls-certs-cm은 private Git/Helm HTTPS 서버를 신뢰하는 용도이며 repo-server 자체의 서버 인증서가 아닙니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-tls-certs-cm
  namespace: argocd
data:
  git.example.com: REPLACE_WITH_VERIFIED_PUBLIC_CA_PEM
```

repo-server RPC는 기본적으로 암호화되지만 서버 인증서를 검증하지 않는 연결일 수 있습니다. 지속적인 argocd-repo-server-tls Secret에 서비스 DNS SAN을 가진 인증서를 준비하고 repo-server를 재시작합니다. server/application-controller/applicationset-controller에는 CA 파일을 마운트하고 --repo-server-ca-cert-path를, notifications-controller에는 --argocd-repo-server-ca-cert-path를 설정합니다. legacy strict-tls 플래그 대신 이 CA 경로 방식을 사용합니다. 이것만으로 상호 TLS가 되는 것은 아니며 클라이언트 인증서는 [공식 mTLS 구성](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/mtls.md)을 따릅니다.

## 감사 로깅

server.audit.enabled/path는 3.5.2에서 지원하는 설정이 아닙니다. 구성요소의 stdout 로그 형식을 설정하고 기존 argocd-cmd-params-cm에 병합한 후 관련 워크로드를 재시작합니다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.log.format: json
  server.log.level: info
  controller.log.format: json
  controller.log.level: info
  reposerver.log.format: json
  reposerver.log.level: info
```

```bash
kubectl logs -n argocd deployment/argocd-server --tail=100
```

로그의 실제 필드/이벤트는 버전·구성요소에 따라 다릅니다. 운영 로그 한 종류를 완전한 감사 추적으로 가정하지 말고 Argo CD/Kubernetes 이벤트, Kubernetes 또는 EKS API audit 로그, Git 변경 기록을 보관 정책에 맞게 연계합니다. debug 로그·생성 매니페스트에 Secret 값을 노출하지 않습니다.

### CloudWatch 수집 예시

기존 노드 수준 Fluent Bit/관측성 배포의 입력·출력에 병합할 설정입니다. /var/log/containers와 DB 디렉터리 마운트, parsers.conf, CloudWatch 권한과 네트워크를 별도로 준비합니다. stdout은 비어 있는 공유 audit.log 볼륨으로 수집할 수 없습니다.

```ini
[SERVICE]
    Parsers_File      /fluent-bit/etc/parsers.conf
[INPUT]
    Name              tail
    Tag               argocd.*
    Path              /var/log/containers/argocd-server-*_argocd_*.log
    multiline.parser  docker, cri
    DB                /var/log/fluent-bit/argocd.db
    Mem_Buf_Limit     10MB
    Skip_Long_Lines   On
[OUTPUT]
    Name              cloudwatch_logs
    Match             argocd.*
    region            ap-northeast-2
    log_group_name    /aws/eks/example-cluster/argocd
    log_stream_prefix argocd-
    auto_create_group false
    log_key           log
```

로그 그룹은 보존·암호화 정책과 함께 미리 생성하고 이름/리전을 교체합니다. 수집기의 자격 증명에는 해당 그룹의 필요한 로그 스트림/이벤트 권한만 부여합니다. containerd의 CRI 형식과 앱 JSON 형식은 서로 다른 계층입니다.

## 네트워크 보안

아래는 기본 비-HA 구성의 정책 템플릿입니다. CNI의 NetworkPolicy 지원·활성화가 전제입니다. 동일 Pod를 선택하는 정책은 허용 규칙이 합산되므로 기존 광범위 정책을 함께 검토해야 합니다. Gateway 데이터플레인 Namespace/Pod 레이블, DNS, API·Git·IdP 주소를 실제 환경에 맞게 바꿉니다.

192.0.2.10(API),198.51.100.10(Git),198.51.100.20(IdP)는 문서용 주소이므로 그대로 적용하지 않습니다. 표준 NetworkPolicy는 FQDN을 선택하지 못합니다. 동적 외부 주소는 CNI FQDN 정책이나 관리되는 egress proxy 등으로 설계하고 NAT 전후의 IP 판정도 확인합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-server-restricted
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: envoy-gateway-system
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-repo-server
    ports:
    - protocol: TCP
      port: 8081
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-dex-server
    ports:
    - protocol: TCP
      port: 5556
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
  - to:
    - ipBlock:
        cidr: 192.0.2.10/32
    ports:
    - protocol: TCP
      port: 443
  - to:
    - ipBlock:
        cidr: 198.51.100.20/32
    ports:
    - protocol: TCP
      port: 443
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-repo-server-restricted
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-repo-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-server
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-application-controller
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-applicationset-controller
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-notifications-controller
    ports:
    - protocol: TCP
      port: 8081
  egress:
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
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - ipBlock:
        cidr: 198.51.100.10/32
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 22
```

Redis HA/프록시, NodeLocal DNS, metrics 수집, Dex의 LDAP/SAML/OIDC, AVP Vault/KMS, 추가 컴포넌트 등은 별도 흐름을 추가해야 합니다. 이 두 정책만으로 전체 Argo CD 네트워크 구성이 완성되는 것은 아닙니다. Pod Security는 먼저 audit/warn으로 현재 워크로드 호환성을 확인한 뒤 단계적으로 enforce합니다.

## 저장소 자격 증명

다음 Secret은 구조 예시입니다. PAT는 선택한 저장소의 읽기 권한으로 제한하고 GitHub App은 해당 설치/Contents 읽기 권한을 사용합니다. private key·token 값은 외부 Secret 관리 또는 보호된 파일로 공급합니다. SSH는 검증된 host key를 argocd-ssh-known-hosts-cm에 준비하며 검증 없이 ssh-keyscan 결과를 신뢰하지 않습니다. repo-creds.url은 glob이 아니라 URL prefix이며 가장 긴 매칭이 우선하고, 자체 자격 증명이 있는 repository Secret에는 템플릿이 적용되지 않습니다.

### HTTPS (사용자명/비밀번호)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/myrepo.git
  username: git
  password: ghp_xxxxxxxxxxxxxxxxxxxx  # Personal Access Token
```

### SSH 키

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-ssh
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: git@github.com:myorg/myrepo.git
  sshPrivateKey: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
    ...
    -----END OPENSSH PRIVATE KEY-----
```

### GitHub Apps

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github-app
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/
  githubAppID: '123456'
  githubAppInstallationID: '12345678'
  githubAppPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA...
    -----END RSA PRIVATE KEY-----
```

### 자격 증명 템플릿

여러 저장소에 동일한 자격 증명을 사용할 때:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: creds-template-github
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/
  username: git
  password: ghp_xxxxxxxxxxxxxxxxxxxx
```

## GPG 서명 검증

Argo CD 3.5의 새 sourceIntegrity 구성을 사용합니다. 서명 검증은 Git commit/annotated tag에 적용되며 Helm·OCI·이미지 서명 검증과 다릅니다. 임의 Secret이나 developer1.asc라는 ConfigMap 키를 만드는 것으로 keyring에 등록되지 않습니다.

```bash
gpg --armor --export YOUR_VERIFIED_KEY_ID > public-key.asc
argocd gpg add --from public-key.asc
argocd gpg list
```

공개키 fingerprint를 별도 경로로 검증한 뒤 가져옵니다. 선언적 keyring은 argocd-gpg-keys-cm의 키가 실제 GPG key ID이고 값이 공개키여야 합니다. 아래 0123456789ABCDEF는 형식용 가짜 값이므로 등록한 조직 키 ID로 교체합니다. 기존 signatureKeys를 제거한 뒤 sourceIntegrity로 이동합니다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/production-*
  destinations:
  - namespace: prod-*
    server: https://prod-cluster.example.com
  clusterResourceWhitelist: []
  sourceIntegrity:
    git:
      policies:
      - repos:
        - url: '*'
        gpg:
          mode: head
          keys:
          - 0123456789ABCDEF
```

head는 대상 commit 또는 annotated tag의 서명을 검증하며 전체 이력 보장은 strict의 별도 정책입니다. 정책에 매칭되지 않는 소스는 검증되지 않습니다. sourceNamespaces는 GPG 키 목록이 아니라 Application CR을 허용할 Namespace 목록입니다.

```bash
# Repository-local configuration; replace the key ID first.
git config user.signingkey YOUR_VERIFIED_KEY_ID
git config commit.gpgsign true
git commit -S -m "Signed change"
git log --show-signature -1
```



## 다음 단계

1. **[알림](08-notifications.md)**: 보안 이벤트에 대한 알림을 구성하세요.

2. **[모범 사례](09-best-practices.md)**: 보안 모범 사례를 학습하세요.

3. **[프로젝트와 RBAC](06-projects-rbac.md)**: RBAC과 함께 보안을 강화하세요.

## 참고 자료

- [Argo CD 3.5.2 secret management](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/secret-management.md)
- [CMP sidecar configuration](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/config-management-plugins.md)
- [TLS trust boundaries](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/tls.md)
- [IAM Identity Center SAML](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/user-management/identity-center.md)
- [KSOPS 4.5.1](https://github.com/viaduct-ai/kustomize-sops/tree/v4.5.1)

- [ArgoCD 보안 문서](https://argo-cd.readthedocs.io/en/stable/operator-manual/security/)
- [SSO 구성](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/)
- [시크릿 관리](https://argo-cd.readthedocs.io/en/stable/operator-manual/secret-management/)
- [GPG 서명](https://argo-cd.readthedocs.io/en/stable/user-guide/gpg-verification/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [보안 퀴즈](../../quizzes/gitops/argocd/07-security-quiz.md)를 풀어보세요.
