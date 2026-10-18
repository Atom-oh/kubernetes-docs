# Docker Hub

> **最終更新日**: 2026年9月11日

## 概要

Docker Hubは、レジストリを指定しないときのDocker CLI既定レジストリです。Docker Official Images、Verified Publisherイメージ、コミュニティ提供コンテンツなど、公開／非公開コンテナイメージをホストします。

### プランと機能

| 機能 | Personal | Pro | Team | Business |
|---|---|---|---|---|
| **料金** | 基本無料枠 | 月額11 USD／年払いで月9 USD | 月額16 USD／年払いで1ユーザー月15 USD | 現行料金と契約を確認 |
| **Private Repository** | 1 | 無制限 | 無制限 | 無制限 |
| **Team機能** | 個人利用 | 個人利用 | 組織で共同作業 | 組織ガバナンス |
| **旧Automated Buildsの同時実行数** | 利用不可 | 5 | 15 | 15 |
| **セキュリティと管理** | プラン範囲を確認 | プラン範囲を確認 | 組織機能を確認 | SSO、監査、契約範囲を確認 |

料金は2026年9月11日に確認した[公式料金ページ](https://www.docker.com/pricing/)のUSD表示です。請求条件と税を確認してください。Automated Buildsは非推奨で、2027年4月1日に廃止予定です。

### Rate limit

[使用状況のドキュメント](https://docs.docker.com/docker-hub/usage/)には、次の6時間ごとの上限が記載されています。実際のアカウント条件と応答headerを確認してください。公正利用／不正利用の制限は別途適用されます。

| ユーザー種別 | Rate limit | リセット間隔 |
|---|---:|---|
| Anonymous | 100 pull | 6時間 |
| 認証済み（Free） | 200 pull | 6時間 |
| 認証済み（Pro） | 公正利用範囲で無制限 | - |
| 認証済み（Team） | 公正利用範囲で無制限 | - |
| 認証済み（Business） | 無制限 | - |

Anonymousの上限はIPv4アドレスまたはIPv6 /64 subnetごとに適用されます。認証済みpullはアカウント／組織の規則に従って計上されます。NATアドレスを共有するnodeは**anonymous**枠を共有しますが、認証済みアカウントの枠まで必ず共有するわけではありません。

## KubernetesでDocker Hubを使う

### Image Pull Secretを作成する

Docker Hubの非公開イメージをpullするには、Kubernetes Secretを作成します。

Secret、Pod、ServiceAccountは同じnamespaceに置く必要があります。pullには読み取り専用PATを使い、実credentialをshell historyやCI logに直接残さないでください。

```bash
# Create docker-registry secret
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<your-username> \
  --docker-password=<your-password-or-token> \
  --docker-email=<your-email> \
  -n <namespace>
```

パスワードではなくPersonal Access Tokenを使うことを推奨します。

```bash
# Generate a Personal Access Token at https://hub.docker.com/settings/security
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=myuser \
  --docker-password=dckr_pat_xxxxxxxxxxxx \
  -n default
```

### PodでSecretを使う

Pod仕様からSecretを参照します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: private-app
  namespace: default
spec:
  containers:
  - name: app
    image: myusername/private-app:v1.0.0
  imagePullSecrets:
  - name: dockerhub-secret
```

### ServiceAccountとの統合

ServiceAccountにimage pull secretを設定して自動注入します。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: default
imagePullSecrets:
- name: dockerhub-secret
```

これでこのServiceAccountを使うPodは、自動的にDocker Hub credentialを使用します。ただし、既定では独自の`imagePullSecrets`を指定していない、**新たにadmissionされるPod**が対象です。既存PodやほかのServiceAccountには遡って反映されません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: app-service-account
      containers:
      - name: app
        image: myusername/private-app:v1.0.0
```

### namespace全体へのSecret配布

複数namespaceのクラスターではSecret配布を自動化します。

```yaml
# Using Kubernetes Replicator or similar controller
apiVersion: v1
kind: Secret
metadata:
  name: dockerhub-secret
  namespace: default
  annotations:
    replicator.v1.mittwald.de/replicate-to: "staging,production,dev-*"
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: <base64-encoded-config>
```

## Rate limitの緩和策

![Docker Hub rate limitへの対応フロー。制限に達した場合は環境に応じてECR Pull-through Cache（AWS／EKS）、Harbor Proxy Cache（セルフホスト）、containerd mirror／Distribution registryを選択。未到達なら認証済みpullを使う。いずれも制限緩和につながる。](../.gitbook/assets/en-container-registry-01-docker-hub-0.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-01-docker-hub-0.html)

### 戦略1: Harborを使ったPull-through Cache

Docker Hub pullを減らすproxy cacheとしてHarborをデプロイします。

```yaml
# Harbor values.yaml excerpt
proxy:
  httpProxy: ""
  httpsProxy: ""
  noProxy: 127.0.0.1,localhost,.local,.internal

# After Harbor deployment, configure a Docker Hub registry endpoint
# and select that endpoint when creating a proxy cache project.
```

`harbor.internal.example.com/dockerhub-cache/library/nginx:TAG`のような明示的なproxy-projectイメージ名を使います。上記のHarbor outgoing HTTP proxy設定をレジストリcache設定として扱わないでください。containerd mirrorにも、互換性のあるレジストリURL配置と信頼済みTLS設定が必要です。

```toml
# containerd 2.x: /etc/containerd/config.toml
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
```

```toml
# containerd 1.x uses this plugin name instead
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
```

```toml
# /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"
[host."https://mirror.gcr.io"]
  capabilities = ["pull"]
```

旧`registry.mirrors`設定は非推奨です。[containerd hostsドキュメント](https://github.com/containerd/containerd/blob/main/docs/hosts.md)に従い、信頼済みmirrorだけに`resolve`を許可してください。公開mirrorにすべての公開／非公開イメージがあるとは限りません。

### 戦略2: Distributionを使ったRegistry Mirror

CNCF Distribution registryをpull-through cacheとしてデプロイします。

参照されているPVCと`dockerhub-creds` Secretを先に作成してください。この抜粋は制御されたラボ用にHTTP registryを公開します。本番ではTLS、認証、アクセス制御が必要です。upstreamの特権credentialを使うproxyで、非公開イメージのcacheを許可されていない利用者に公開してはいけません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registry-mirror
spec:
  replicas: 1
  selector:
    matchLabels:
      app: registry-mirror
  template:
    metadata:
      labels:
        app: registry-mirror
    spec:
      containers:
      - name: registry
        image: registry:2
        ports:
        - containerPort: 5000
        env:
        - name: REGISTRY_PROXY_REMOTEURL
          value: "https://registry-1.docker.io"
        - name: REGISTRY_PROXY_USERNAME
          valueFrom:
            secretKeyRef:
              name: dockerhub-creds
              key: username
        - name: REGISTRY_PROXY_PASSWORD
          valueFrom:
            secretKeyRef:
              name: dockerhub-creds
              key: password
        volumeMounts:
        - name: cache-storage
          mountPath: /var/lib/registry
      volumes:
      - name: cache-storage
        persistentVolumeClaim:
          claimName: registry-cache-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: registry-mirror
spec:
  selector:
    app: registry-mirror
  ports:
  - port: 5000
    targetPort: 5000
```

### 戦略3: Amazon ECR Pull-through Cache

AWS上で実行する場合、ECRのpull-through cache機能を使います。まずupstream credential secretを同じアカウント／Region内に作成し、`ecr-pullthroughcache/`という名前prefixを付けます。実際の完全なARNを指定してください。

```bash
# Example after creating a secret named ecr-pullthroughcache/dockerhub
PTC_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id ecr-pullthroughcache/dockerhub --region us-east-1 \
  --query ARN --output text)
# Create pull-through cache rule for Docker Hub
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub \
  --upstream-registry-url registry-1.docker.io \
  --credential-arn "$PTC_SECRET_ARN" \
  --region us-east-1

# Pull images through ECR
# Original: docker.io/library/nginx:latest
# Via ECR: 123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/nginx:latest
```

### 戦略4: nodeにイメージを事前pullする

予測可能なワークロードではDaemonSetでイメージを事前pullします。

事前pullはダウンロード時期を前倒しするだけであり、upstream pullをなくしたり、kubeletのimage garbage collection後もcacheが残ることを保証したりしません。credentialはDaemonSetのnamespaceに置き、保守されているtagまたは検証済みdigestを使ってください。

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: image-prepuller
spec:
  selector:
    matchLabels:
      app: image-prepuller
  template:
    metadata:
      labels:
        app: image-prepuller
    spec:
      initContainers:
      - name: prepull-nginx
        image: nginx:1.30.6
        command: ['sh', '-c', 'echo Image pulled']
      - name: prepull-redis
        image: redis:7
        command: ['sh', '-c', 'echo Image pulled']
      containers:
      - name: pause
        image: registry.k8s.io/pause:3.10
      imagePullSecrets:
      - name: dockerhub-secret
```

## Automated Builds

Docker Hub Automated Buildsは**非推奨**で、2027年4月1日に廃止予定です。以下は旧GitHub／Bitbucket統合の説明です。GitLabのbuildはGitLab CIで実行して結果をpushしてください。新しいpipelineには[移行ガイダンス](https://docs.docker.com/docker-hub/repos/manage/builds/)に従います。

### Automated Buildsを設定する

1. 既存autobuild設定では、リンクされたGitHub／Bitbucketアカウントを確認します。
2. repositoryを作成し、source repositoryに接続します。
3. build ruleを設定します。

```yaml
# Example build rules configuration
Source Type: Branch
Source: main
Docker Tag: latest
Dockerfile location: /Dockerfile
Build Context: /

Source Type: Tag
Source: /^v[0-9.]+$/
Docker Tag: {sourceref}
Dockerfile location: /Dockerfile
Build Context: /
```

### Build hook

repository内のhook scriptでbuildをカスタマイズします。

```bash
# hooks/build - Custom build script
#!/bin/bash
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  -t $IMAGE_NAME .
```

```bash
# hooks/post_push - Run after successful push
#!/bin/bash
# Tag with additional tags
docker tag $IMAGE_NAME $DOCKER_REPO:$SOURCE_COMMIT
docker push $DOCKER_REPO:$SOURCE_COMMIT
```

### Docker Hub Automated Buildsの制約

- サービスは非推奨です。2027年4月1日より前に移行を計画してください。
- 文書に記載された同時build数はProで5、Team／Businessで15です。
- multi-platform、cache、credential、retentionの挙動が外部CI runnerと同じとは限りません。実際の旧設定を確認してください。

**推奨:** buildには`docker/build-push-action`を使うGitHub Actions、またはDocker／BuildKit commandを使うGitLab CIを選びます。GitHub ActionsのactionはGitLab CI jobとして直接実行できません。

## 公開イメージのセキュリティ上の考慮事項

### サプライチェーン攻撃の経路

Docker Hubの公開イメージはセキュリティリスクを持ち込む可能性があります。

1. **Typosquatting**: 人気イメージに似た名前の悪意あるイメージ
2. **Maintainer accountの侵害**: 正規イメージが攻撃者に乗っ取られる
3. **マルウェアの埋め込み**: cryptominer、backdoor、データ持ち出しコード
4. **脆弱なbase image**: 既知CVEがある古いイメージ
5. **肥大化したイメージ**: 不要なpackageが攻撃対象領域を広げる

### 信頼できるイメージを識別する

| イメージ種別 | 指標 | 信頼性の確認 |
|---|---|---|
| Docker Official Images | upstream imageの選定プログラム | 個別tag、digest、脆弱性を検証する |
| Verified Publisher | publisherの身元確認 | 個別artifactと保守ポリシーを検証する |
| Sponsored OSS | 支援対象projectプログラム | 支援されているから脆弱性がないとは限らない |
| Community Images | badgeなし | 手動で検証する |

### Docker Official Images

Official ImagesはDockerとupstream／community maintainerが選定します。すべてのイメージをDocker Inc.が直接保守しているわけではありません。

```bash
# Official images use the library/ namespace (often omitted)
docker pull nginx          # Same as docker.io/library/nginx
docker pull postgres:15    # Same as docker.io/library/postgres:15
```

Official Imagesの特徴:
- 明確なドキュメントとDockerfileの透明性
- 定期的なセキュリティ更新
- Dockerfileのベストプラクティス
- architecture対応はイメージ／tagにより異なる
- base sizeと同梱packageはvariantにより異なる

### Verified Publisher

Verified PublisherはDockerが組織を確認したpublisherです。

```bash
# Select an actual maintained tag/digest from the publisher's current catalog
docker buildx imagetools inspect "$VERIFIED_VENDOR_IMAGE"
docker pull "$VERIFIED_VENDOR_IMAGE"
```

publisher badgeを見て、現行tagの提供状況や脆弱性状況を推測しないでください。vendor catalogとaccess policyは変わります。古いBitnamiやGrafanaのtag例を、現在の推奨とみなさないでください。

### セキュリティスキャンのベストプラクティス

デプロイ前に公開イメージを必ずscanします。

```bash
# Using Trivy (recommended)
trivy image nginx:latest

# Using Docker Scout (Docker Desktop)
docker scout cves nginx:latest

# Using Grype
grype nginx:latest
```

source allowlistは有用ですが、**署名や脆弱性スキャンを強制しません**。以下は専用の`registry-demo` namespaceでKyverno Audit modeを使います。強制ポリシーを選ぶ前に結果を確認してください。

```yaml
# Source allowlist only; Kyverno must already be installed
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: allowed-image-sources
spec:
  validationFailureAction: Audit
  rules:
  - name: check-image-source
    match:
      any:
      - resources:
          kinds:
          - Pod
          namespaces:
          - registry-demo
    validate:
      message: "Use an approved, fully qualified image reference."
      pattern:
        spec:
          =(initContainers):
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
          =(ephemeralContainers):
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
          containers:
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
```

署名ポリシーには、信頼する鍵／identityとdigest検証が必要です。脆弱性attestationポリシーには、信頼するsignerと明示的な受け入れ基準も必要です。署名されていない`scanner`文字列の確認だけでは不十分です。[イメージセキュリティ](../security/07-image-security.md)と[upstreamのsource allowlist例](https://github.com/kyverno/policies/tree/main/best-practices/restrict-image-registries)を参照してください。Docker CLIのContent Trust設定が、Kubernetes／containerdのadmissionを自動的に強制するわけではありません。

### 公開イメージの推奨事項

1. **tagだけでなくdigestを固定する:**

   ```yaml
   # Avoid
   image: nginx:latest

   # Better
   image: nginx:1.30.6

   ```

pull後に`docker image inspect nginx:1.30.6 --format='{{index .RepoDigests 0}}'`を実行して完全な値を取得し、workloadでは出力された`repository@sha256:...`を使います。省略された例示hashは、そのまま使えるimage referenceではありません。

2. **Private registryにmirrorする:**

   ```bash
   # Pull, scan, and push to your private registry
   docker pull nginx:1.30.6
   trivy image nginx:1.30.6 --exit-code 1
   docker tag nginx:1.30.6 myregistry.com/library/nginx:1.30.6
   docker push myregistry.com/library/nginx:1.30.6
   ```

3. **Distrolessまたは最小base imageを使う:**

   ```dockerfile
   # Instead of full OS base images
   FROM gcr.io/distroless/static-debian12
   # or
   FROM cgr.dev/chainguard/static:latest
   ```

## Docker Hub APIの利用

### 認証

旧`/v2/users/login`経路は非推奨です。[公式Hub API](https://docs.docker.com/reference/api/hub/latest/)では`/v2/auth/token`に`identifier`と`secret`を渡し、`access_token`を取得します。このtokenは10分で期限切れになり、Registry pullで使う`auth.docker.io` tokenとは別です。パスワードではなく、必要なscopeを持つPATを推奨します。

```bash
set -euo pipefail
# Load these from secure shell input or CI secrets; do not commit their values.
: "${DOCKER_USER:?Set Docker Hub username}"
: "${DOCKER_PAT:?Load a Docker Hub personal access token}"
export DOCKER_USER DOCKER_PAT
HUB_TOKEN=$(jq -n '{identifier: env.DOCKER_USER, secret: env.DOCKER_PAT}' | \
  curl -fsS -X POST https://hub.docker.com/v2/auth/token \
    -H 'Content-Type: application/json' --data-binary @- | jq -er '.access_token')
HUB_NAMESPACE=${HUB_NAMESPACE:-$DOCKER_USER}
export HUB_TOKEN HUB_NAMESPACE
```

### Repositoryとtagの一覧

`HUB_NAMESPACE`の既定値はログインユーザーです。必要に応じて権限のあるorganization namespaceを設定してください。以下の例は表示可能な最初のpageだけを要求します。`page_size`の最大値は100です。完全な一覧にするには応答の`next` URLをたどります。

```bash
: "${DOCKER_REPO:?Set repository name}"
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" \
  "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories?page_size=100" | \
  jq '.results[] | {name, is_private}'

curl -fsS -H "Authorization: Bearer $HUB_TOKEN" \
  "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories/$DOCKER_REPO/tags?page_size=100" | \
  jq '.results[] | {name, last_updated}'
```

### 削除前にtagを確認する

最初の100件だけを見てtagを削除したり、文書化されていないserver-side順序を仮定したりしないでください。この単独Bash scriptは全pageを収集し、inventoryをローカルでsortします。削除操作は行いません。削除前に、稼働中workloadのdigest、rollback保持、保護tagを確認し、Hub管理UIまたは現行ドキュメントにあるAPI機能を使ってください。

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${HUB_TOKEN:?Create a current Hub API access token}"
: "${HUB_NAMESPACE:?Set namespace}"
: "${DOCKER_REPO:?Set repository}"
registry_tag_index=$(mktemp)
trap 'rm -f "$registry_tag_index"' EXIT
registry_next="https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories/$DOCKER_REPO/tags?page_size=100"
while [ -n "$registry_next" ]; do
  case "$registry_next" in
    https://hub.docker.com/*) ;;
    *) printf '%s\n' 'Unexpected pagination host' >&2; exit 1 ;;
  esac
  registry_page=$(curl -fsS -H "Authorization: Bearer $HUB_TOKEN" "$registry_next")
  printf '%s' "$registry_page" | jq -c '.results[]' >> "$registry_tag_index"
  registry_next=$(printf '%s' "$registry_page" | jq -r '.next // empty')
done
# Read-only inventory. No DELETE request is made.
jq -s 'sort_by(.last_updated // "") | reverse | .[] | {name, last_updated}' "$registry_tag_index"
```

### 脆弱性分析

```bash
# Check Scout access against the account, plan and repository configuration.
# Use the documented CLI instead of assuming a /tags/TAG/vulnerabilities endpoint.
docker scout cves nginx:1.30.6
```

### Private Repositoryを作成する

まずnamespace権限とプラン上の利用条件を確認します。

```bash
jq -n --arg ns "$HUB_NAMESPACE" \
  '{namespace:$ns, name:"myapp", description:"My application", is_private:true}' | \
  curl -fsS -X POST "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories" \
    -H "Authorization: Bearer $HUB_TOKEN" \
    -H 'Content-Type: application/json' --data-binary @-
```

## ベストプラクティス

### 1. 認証とアクセス

- パスワードではなくPersonal Access Tokenを使う。
- tokenを定期的にローテーションする（90日ごとを推奨）。
- CI/CDのpull処理には読み取り専用tokenを使う。
- Docker Hub accountで2FAを有効にする。
- teamではorganizationレベルのアクセス管理を使う。

### 2. イメージ管理

- `latest`を本番で使わず、具体的なtagを使う。
- 一貫したtag戦略を導入する（SemVerを推奨）。
- 古い／未使用tagを定期的に整理する。
- imageの依存関係と更新手順を文書化する。

### 3. セキュリティ

- すべてのイメージをデプロイ前にscanする。
- 可能な限りOfficial ImagesとVerified Publisherを選ぶ。
- 重要なイメージをPrivate registryにmirrorする。
- ポリシーを強制するadmission controllerを導入する。
- Dockerfileのセキュリティ問題を確認する。

### 4. パフォーマンスと信頼性

- 本番クラスターにはregistry mirror／cacheを導入する。
- rate limitの使用状況を監視する。
- 公開イメージでも、上限の高い認証済みpullを使う。
- 予測可能なデプロイではイメージを事前pullする。

### 5. CI/CD統合

- Docker Hub Automated Buildsより機能が多いGitHub ActionsまたはGitLab CIでbuildする。
- 小さなイメージにはmulti-stage buildを使う。
- buildを速めるためlayerを効果的にcacheする。
- サプライチェーンセキュリティのためイメージに署名する。

## まとめ

Docker Hubは、Docker CLIの既定公開イメージエコシステムとPrivate Repositoryを提供します。Kubernetes基盤で信頼性を持って利用するには、認証、cache、artifact検証、明示的な保守ポリシーが必要です。

信頼性の向上や厳格なセキュリティ制御が必要な本番workloadでは、次を検討してください。

- AWSネイティブ環境では**Amazon ECR**
- セルフホスト、air-gap、multi-cloud環境では**Harbor**
- SaaSの利便性とenterprise機能が必要なら**Docker Hub Business**

主なポイント:
- 適切な認証を使い、実際のrate／公正利用上限を確認する。
- 本番クラスターにはpull-through cacheを導入する。
- 信頼しつつ検証する: 公開イメージをすべてscanする。
- 可能ならOfficial ImagesとVerified Publisherを使う。
- Docker Hubをbase imageに、アプリケーションをPrivate registryに置くなど、併用方式を検討する。

## 参考資料

- [Docker Hubの使用状況とpull制限](https://docs.docker.com/docker-hub/usage/pulls/)
- [Docker Hub API](https://docs.docker.com/reference/api/hub/latest/)
- [Automated Buildsの非推奨化](https://docs.docker.com/docker-hub/repos/manage/builds/)
- [containerd registry host設定](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
- [ECR pull-through cache rule](https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache-creating-rule.html)
