# Harbor

> **最終更新日**: 2026年10月16日

## 概要

Harbor は、コンテナイメージの保存、署名、スキャンにエンタープライズ向け機能を提供する、クラウドネイティブなオープンソースのコンテナレジストリです。CNCF の Graduated プロジェクトとして、業界で成熟度、セキュリティ、採用実績が認められています。

### 主な機能

| 機能 | 説明 |
|---------|-------------|
| **マルチテナンシー** | プロジェクト単位の RBAC による分離 |
| **脆弱性スキャン** | Trivy スキャナーを内蔵 |
| **イメージ署名** | Cosign と Notation に対応 |
| **レプリケーション** | レジストリ間で push/pull を複製 |
| **ガベージコレクション** | 未使用レイヤーを自動クリーンアップ |
| **プロキシキャッシュ** | リモートレジストリ (Docker Hub など) をキャッシュ |
| **監査ログ** | 操作履歴をすべて記録 |
| **OIDC/LDAP** | エンタープライズ ID と統合 |
| **クォータ管理** | プロジェクトごとのストレージ上限 |
| **Robot アカウント** | 自動化用のサービスアカウント |

### アーキテクチャ

![Harbor の内部構造。Portal が Core API のフロントエンドとなり、Core API は Registry、Job Service、PostgreSQL、Redis に処理を振り分けます。Job Service は Trivy スキャナーを実行します。](../.gitbook/assets/en-container-registry-03-harbor-0.png)

[🔍 対話型図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-0.html)

### コンポーネントの役割

| コンポーネント | 目的 |
|-----------|---------|
| **Core** | API サーバー、認証、認可、プロジェクト管理 |
| **Registry** | Docker Distribution v2 API の実装、イメージ保存 |
| **Job Service** | 非同期タスク実行 (レプリケーション、スキャン、GC) |
| **Trivy** | 脆弱性スキャンエンジン |
| **Portal** | 管理用 Web UI |
| **PostgreSQL** | メタデータ、ユーザーデータ、監査ログ |
| **Redis** | ジョブキュー、セッションキャッシュ、レジストリキャッシュ |

## Helm でインストールする

2026-10-16 にレビューしたベースラインは **Harbor 2.15.4 / Helm chart 1.19.2** です。アプリケーションと chart のバージョンは異なります。最新の chart 1.19.2 でもデフォルトの appVersion は 2.15.2 のため、デフォルトの Helm インストールでは 2.15.3 のセキュリティ修正 (例: GHSA-2phj-cp9f-qq6w) が含まれません。この例では、外部の HA PostgreSQL、Redis、共有ストレージが既にあることを前提とします。この values ファイルはそれらをプロビジョニングしません。

### 前提条件

- 対応する Kubernetes/Helm バージョン、DNS、保守されている Ingress コントローラーとその `IngressClass` を準備します。そのコントローラーのアップロード上限、タイムアウト、TLS を設定します。
- namespace `harbor` に `harbor-tls` 証明書/鍵 Secret を作成します。証明書のホスト名が一致し、クライアントとノードがその CA を信頼する必要があります。
- Registry レプリカを別々のノードに2つ配置するには、**共有 RWX PVC またはオブジェクトストレージ**が必要です。1つの EBS `gp3` RWO PVC を複数ノードで共有しても HA 構成にはなりません。
- PostgreSQL データベース `registry`、そのユーザー、Secret `harbor-database` 内の `password` キーを準備します。`sslmode: require` が要求するのは暗号化だけです。証明書とホスト名の検証も必要なら CA 信頼と `verify-full` を検証してください。
- Redis は Harbor が使用する複数の論理データベースに対応する必要があります。DB 0 だけに制限される Redis Cluster モードは使わないでください。Secret `harbor-redis` に `REDIS_PASSWORD` を準備し、TLS 接続を検証します。プライベート CA には chart の `caBundleSecretName` を使います。

```bash
helm repo add harbor https://helm.goharbor.io
helm repo update
helm show chart harbor/harbor --version 1.19.2
kubectl create namespace harbor
kubectl get ingressclass
kubectl get storageclass
```

### 初期認証情報

```bash
# Initial installation only: preserve this encryption key during upgrades.
umask 077
HARBOR_SETUP_DIR=$(mktemp -d)
python3 - "$HARBOR_SETUP_DIR" <<'PYTHON'
import getpass
import pathlib
import secrets
import sys
root = pathlib.Path(sys.argv[1])
(root / "admin-password").write_text(getpass.getpass("Initial Harbor admin password: "))
(root / "secretKey").write_text(secrets.token_hex(8))  # exactly 16 characters
PYTHON
kubectl create secret generic harbor-admin -n harbor \
  --from-file=HARBOR_ADMIN_PASSWORD="$HARBOR_SETUP_DIR/admin-password"
kubectl create secret generic harbor-encryption-key -n harbor \
  --from-file=secretKey="$HARBOR_SETUP_DIR/secretKey"
rm -rf -- "$HARBOR_SETUP_DIR"
```

### 本番向け values.yaml

`harbor-values.yaml` として保存し、例示のホスト名と StorageClass をすべて置き換えます。計測した負荷と利用可能なノードに応じて、リソース要求/上限と Pod の分散配置を追加します。Prometheus Operator の CRD をインストールしてから `serviceMonitor.enabled` を有効にしてください。

```yaml
expose:
  type: ingress
  tls:
    enabled: true
    certSource: secret
    secret:
      secretName: harbor-tls
  ingress:
    hosts:
      core: harbor.example.com
    className: your-ingress-class
    annotations: {}
externalURL: https://harbor.example.com
existingSecretAdminPassword: harbor-admin
existingSecretSecretKey: harbor-encryption-key
internalTLS:
  enabled: true
  certSource: auto
persistence:
  enabled: true
  resourcePolicy: keep
  persistentVolumeClaim:
    registry:
      storageClass: your-rwx-storage-class
      accessMode: ReadWriteMany
      size: 100Gi
    trivy:
      storageClass: your-storage-class
      size: 10Gi
core:
  replicas: 2
portal:
  replicas: 2
registry:
  replicas: 2
jobservice:
  replicas: 2
  jobLoggers: [database]
database:
  type: external
  external:
    host: harbor-db.internal
    port: "5432"
    username: harbor
    coreDatabase: registry
    existingSecret: harbor-database
    sslmode: require
redis:
  type: external
  external:
    addr: harbor-redis.internal:6379
    existingSecret: harbor-redis
    tlsOptions:
      enable: true
trivy:
  enabled: true
  skipUpdate: false
  skipJavaDBUpdate: false
  offlineScan: false
metrics:
  enabled: true
  serviceMonitor:
    enabled: false
```

### カスタム値を使ったインストール

```bash
helm template harbor harbor/harbor --version 1.19.2   --namespace harbor --values harbor-values.yaml > harbor-rendered.yaml
helm install harbor harbor/harbor --version 1.19.2   --namespace harbor --values harbor-values.yaml --wait --timeout 15m
kubectl get pods,svc,ingress,pvc -n harbor
docker login harbor.example.com --username admin
```

### Harbor のアップグレード

アップグレード前に、リリースノートで対応するアップグレード経路を確認します。メタデータ、レジストリデータ、構成、暗号化キーを同一の復旧時点でバックアップし、復元をテストします。旧 chart と新 chart の値を比較し、ステージングでレンダリングとマイグレーションをテストします。`helm upgrade` では対象 chart のバージョンを固定してください。Helm のロールバックだけではデータベースのマイグレーションを元に戻せない場合があります。

Notary v1 は Harbor 2.9 で削除されました。Cosign と Notation は外部の署名ツールであり、署名はレジストリ内に OCI artifact として保存されます。

## プロジェクトと RBAC

API の例では、`curl` と `jq` を使って HTTPS 経由でアクセスできるテスト用 Harbor インスタンスがあることを前提とします。必要な権限を持つユーザーを `HARBOR_USER` に設定してください。`curl --user "$HARBOR_USER"` はパスワードの入力を求めます。自動化では、スコープを限定した robot 認証情報をシークレット管理ツールから渡し、ログに出力しないでください。

```bash
export HARBOR_USER=admin
```

### プロジェクトの種類

| 種類 | 説明 | 用途 |
|------|-------------|----------|
| **パブリック** | 誰でもイメージを pull できる | オープンソース、共有ベースイメージ |
| **プライベート** | メンバーのみアクセス可能 | アプリケーションイメージ、内部ツール |

### プロジェクトを作成する

```bash
# Create project via API
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "project_name": "myapp",
    "metadata": {
      "public": "false",
      "prevent_vul": "true",
      "auto_scan": "true",
      "severity": "high"
    },
    "storage_limit": 107374182400
  }'
```

### RBAC ロール

| ロール | 権限 |
|------|-------------|
| **Project Admin** | 全権限: メンバー、ポリシー、イメージの管理 |
| **Maintainer** | イメージの push/pull、スキャン、タグ削除 |
| **Developer** | イメージの push/pull。メンバー管理は含まない |
| **Guest** | イメージの pull のみ |
| **Limited Guest** | artifact の pull/読み取り。プロジェクトメンバーやログの一覧表示は不可 |

### メンバーを追加する

```bash
# Add user to project
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects/myapp/members" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "role_id": 2,
    "member_user": {
      "username": "developer1"
    }
  }'

# Role IDs: 1=Admin, 2=Developer, 3=Guest, 4=Maintainer, 5=Limited Guest
```

### Robot アカウント

Robot アカウントは CI/CD 自動化用のサービスアカウントです。

```bash
# Create robot account
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/robots" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "ci-robot",
    "description": "Robot account for CI/CD pipelines",
    "duration": 90,
    "level": "project",
    "permissions": [
      {
        "kind": "project",
        "namespace": "myapp",
        "access": [
          {"resource": "repository", "action": "push"},
          {"resource": "repository", "action": "pull"}
        ]
      }
    ]
  }'

# Response includes robot name and secret
# {
#   "name": "robot$myapp+ci-robot",
#   "secret": "xxxxxxxxxxxxxxxxxxxx",
#   ...
# }
```

CI/CD で robot アカウントを使う例:

```bash
# Docker login with robot account
read -r -p 'Robot name returned by Harbor: ' ROBOT_NAME
read -r -s -p 'Robot secret: ' ROBOT_SECRET
printf '\n'
printf '%s' "$ROBOT_SECRET" | docker login harbor.example.com \
  --username "$ROBOT_NAME" --password-stdin
unset ROBOT_SECRET

# Push image
docker push harbor.example.com/myapp/app:v1.0.0
```

## イメージのレプリケーション

![Harbor は2方向のレプリケーションに対応します。外部レジストリからイメージを pull してローカルにミラーする方向と、ソース Harbor からリモートレジストリへイメージを push して配布する方向です。](../.gitbook/assets/en-container-registry-03-harbor-1.png)

[🔍 対話型図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-1.html)

Harbor はレジストリ間の双方向レプリケーションに対応します。

以下の endpoint ID `1` と `3` は例です。作成レスポンスの `Location` または endpoint 一覧から実際の ID を取得してください。スケジュール用 cron 式は秒を含む6フィールドです (`0 0 0 * * *`)。Job Service のタイムゾーンを確認してください。Pull レプリケーションには上流への接続性が必要です。完全に切断されたネットワークには取り込めません。イベントレプリケーションが追跡するのは、ローカル Harbor の push/retag/削除イベントであり、リモートレジストリの任意の変更ではありません。

### レプリケーションモード

| モード | 説明 | 用途 |
|------|-------------|----------|
| **Push** | Harbor がリモートに push | エッジ拠点への配布 |
| **Pull** | Harbor がリモートから pull | Docker Hub のミラー、ECR との同期 |

### レプリケーション endpoint を設定する

```bash
# Create registry endpoint (e.g., Docker Hub)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "docker-hub",
    "type": "docker-hub",
    "url": "https://hub.docker.com",
    "credential": {
      "type": "basic",
      "access_key": "dockerhub-username",
      "access_secret": "<dockerhub-PAT>"
    }
  }'

# Create registry endpoint (ECR)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "aws-ecr",
    "type": "aws-ecr",
    "url": "https://123456789012.dkr.ecr.us-east-1.amazonaws.com",
    "credential": {
      "type": "basic",
      "access_key": "AKIAIOSFODNN7EXAMPLE",
      "access_secret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    }
  }'

# Create registry endpoint (another Harbor)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "harbor-dr",
    "type": "harbor",
    "url": "https://harbor-dr.example.com",
    "credential": {
      "type": "basic",
      "access_key": "<replication-user>",
      "access_secret": "<replication-secret>"
    }
  }'
```

### レプリケーションルールを作成する

```bash
# Pull replication from Docker Hub (mirror official images)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "mirror-dockerhub-nginx",
    "src_registry": {"id": 1},
    "dest_namespace": "dockerhub-mirror",
    "filters": [
      {"type": "name", "value": "library/nginx"},
      {"type": "tag", "value": "1.*"}
    ],
    "trigger": {
      "type": "scheduled",
      "trigger_settings": {
        "cron": "0 0 0 * * *"
      }
    },
    "enabled": true,
    "replicate_deletion": false,
    "override": true,
    "speed": -1
  }'

# Push replication to DR site
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "replicate-to-dr",
    "dest_registry": {"id": 3},
    "filters": [
      {"type": "name", "value": "production/**"},
      {"type": "tag", "value": "v*"}
    ],
    "trigger": {
      "type": "event_based"
    },
    "enabled": true,
    "replicate_deletion": false,
    "override": true,
    "speed": 102400
  }'
```

### レプリケーションフィルター

| フィルターの種類 | 説明 | 例 |
|-------------|-------------|---------|
| `name` | リポジトリ名のパターン | `library/**`、`myapp/*` |
| `tag` | タグのパターン | `v*`、`latest` |
| `label` | Harbor のラベル | `production`、`approved` |
| `resource` | リソースの種類 | `image`、`chart` |

## 脆弱性スキャン

### Trivy の統合

Harbor はデフォルトの脆弱性スキャナーとして Trivy を使用します。Trivy は以下をスキャンします。

- OS パッケージの脆弱性 (Alpine、Debian、Ubuntu、RHEL など)
- アプリケーションの依存関係 (npm、pip、gem、maven、go modules)

### Push 時のスキャンを設定する

```bash
# Enable automatic scanning for a project
curl --fail-with-body -X PUT "https://harbor.example.com/api/v2.0/projects/myapp" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "metadata": {
      "auto_scan": "true"
    }
  }'
```

### 手動スキャン

```bash
# Use the digest of an existing artifact from the Harbor UI/API.
: "${HARBOR_DIGEST:?Set the complete sha256 digest}"
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/${HARBOR_DIGEST}/scan"
curl --fail-with-body --user "$HARBOR_USER" \
  "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/${HARBOR_DIGEST}?with_scan_overview=true"
```

スキャンは非同期で実行されます。完了状態とデータベースの鮮度を確認してください。レポートが空または不完全でも、脆弱性がないとは限りません。リポジトリ名が単一コンポーネントの `app` である例と異なり、`team/app` のようなネストした名前には Harbor API 用の二重 URL エンコードが必要です。

### CVE の許可リスト

例外は、所有者、理由、有効期限を伴う承認済み CVE に限定します。以下の PUT はプロジェクトの許可リストを置き換えるため、先に既存エントリーをマージしてください。システムリストの再利用を無効にするため、承認済み識別子と将来の日付である有効期限が必要です。

```bash
# Review the existing project allowlist before replacing it.
: "${APPROVED_CVE:?Set an approved CVE identifier}"
: "${ALLOWLIST_EXPIRES_AT:?Set a future Unix timestamp in seconds}"
jq -n --arg cve "$APPROVED_CVE" --argjson expires "$ALLOWLIST_EXPIRES_AT" \
  '{metadata:{reuse_sys_cve_allowlist:"false"},
    cve_allowlist:{items:[{cve_id:$cve}],expires_at:$expires}}' > cve-allowlist.json
curl --fail-with-body --user "$HARBOR_USER" -X PUT \
  -H 'Content-Type: application/json' \
  --data-binary @cve-allowlist.json \
  'https://harbor.example.com/api/v2.0/projects/myapp'
```

### 脆弱なイメージのデプロイを防ぐ

脆弱なイメージの pull をブロックするよう Harbor を設定します。

```bash
# Set vulnerability prevention policy
curl --fail-with-body -X PUT "https://harbor.example.com/api/v2.0/projects/myapp" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "metadata": {
      "prevent_vul": "true",
      "severity": "high"
    }
  }'

# Severity options: none, low, medium, high, critical
```

このポリシーが制御するのはレジストリからの pull です。既に実行中、またはキャッシュ済みイメージを使っているコンテナを検査したり停止したりはしません。自動スキャンを有効にしただけでは、pull の防止は有効になりません。

## イメージ署名

署名は artifact の完全性と信頼できる署名者を検証します。脆弱性を修正したり、稼働中の Pod を検査したりするものではありません。Cosign/Notation は公式ガイドに従ってインストールし、署名形式が Harbor とポリシーエンジンに対応するかを検証してください。

### Cosign の統合

```bash
# HARBOR_IMAGE must include an existing image digest, not a mutable tag.
: "${HARBOR_IMAGE:?Set harbor.example.com/myapp/app@sha256:<actual-digest>}"
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$HARBOR_IMAGE"
cosign verify --key cosign.pub "$HARBOR_IMAGE"
```

Keyless 署名では OIDC ID と透過性ログを使います。検証時には、信頼する issuer と ID を制限する必要があります。鍵を使う例では、秘密鍵とそのパスワードを保護してください。完全に切断された環境では、Sigstore のパブリックサービスに依存するワークフローを直接使えません。

### Notation (Notary v2) の統合

以下ではテスト専用の自己署名証明書を使います。検証前に `generate-test` が作成した trust store に trust policy をインポートします。本番ポリシーでは、組織の CA/鍵管理と、署名者 ID の明示的な制限を使ってください。

```bash
notation version
notation login harbor.example.com
notation cert generate-test --default harbor-demo
notation sign "$HARBOR_IMAGE"
cat > trustpolicy.json <<'JSON'
{
  "version": "1.0",
  "trustPolicies": [{
    "name": "harbor-demo",
    "registryScopes": ["harbor.example.com/myapp/app"],
    "signatureVerification": {"level": "strict"},
    "trustStores": ["ca:harbor-demo"],
    "trustedIdentities": ["*"]
  }]
}
JSON
notation policy import trustpolicy.json
notation verify "$HARBOR_IMAGE"
```

### Harbor で Cosign を設定する

プロジェクトの Configuration で Cosign または Notation のポリシーを選択します。両方を有効にすると、両方の署名形式が必要です。chart に公開鍵検証用の `core.cosignKeyFile` オプションはありません。レジストリによる署名付属物のチェックと、組織が信頼する鍵/ID に対する検証を区別してください。

### Kubernetes でポリシーを適用する

デプロイ時の適用には、[イメージセキュリティ](../security/07-image-security.md)で説明する Kyverno などの admission policy を設定します。有効な鍵または信頼する OIDC issuer/ID、正確なイメージ範囲、プライベートレジストリ認証情報を指定し、init/ephemeral container も対象にします。Audit で検証してから Enforce に進み、誤った鍵、未署名イメージ、タグの再割り当てによる失敗も確認してください。

## エアギャップ環境

Docker Compose のオフラインインストーラーと Kubernetes Helm デプロイは別々のインストール経路です。オフラインインストーラーに Harbor イメージは同梱されていますが、すべての Docker/Compose パッケージ、Kubernetes chart、CNI、アプリケーションイメージ、Trivy データベースが含まれるわけではありません。

### オフラインインストーラー

```bash
HARBOR_VERSION=2.15.4
curl --fail --location --remote-name \
  "https://github.com/goharbor/harbor/releases/download/v${HARBOR_VERSION}/harbor-offline-installer-v${HARBOR_VERSION}.tgz"
# Verify the release checksum/signature before transporting the bundle.
sha256sum "harbor-offline-installer-v${HARBOR_VERSION}.tgz" > harbor-bundle.sha256
# Transfer both files through the approved offline transport.
```

切断されたホストで次を実行します。ローカルで計算した SHA-256 は転送時の完全性を検証しますが、発行元のリリース署名検証の代わりにはなりません。

```bash
sha256sum -c harbor-bundle.sha256
tar xzf harbor-offline-installer-v2.15.4.tgz
cd harbor
cp harbor.yml.tmpl harbor.yml
# Set hostname, HTTPS certificate/key, strong admin/DB passwords and data_volume.
# For Trivy: preload DBs, set skip_update, skip_java_db_update and offline_scan.
# Install Docker Engine/Compose and other prerequisites from offline packages first.
./install.sh --with-trivy
```

### エアギャップ Kubernetes 用にイメージを事前ロードする

対応する Kubernetes バージョンを指定できる kubeadm バイナリを使い、正確なバージョンのコントロールプレーンイメージ一覧を取得します。CNI、CSI、Ingress、監視のイメージに加えて、chart/CRD を別途追加します。kubeadm で管理していないクラスターでは、ディストリビューション独自のイメージ一覧を使います。

```bash
: "${K8S_VERSION:?Set the exact supported Kubernetes patch version}"
kubeadm config images list --kubernetes-version "$K8S_VERSION" > kubeadm-images.txt
```

### イメージ同期スクリプトを自動化する

TSV ファイル内でソースと宛先の参照を明示的に対応付けます。basename だけでタグを付け直すと、レジストリ/名前空間をまたいで名前が衝突する可能性があります。以下の Bash/Skopeo の例は、すべてのプラットフォームを OCI archive 経由で転送します。署名/SBOM の referrer は、ツールの対応状況に応じて別途転送・検証する必要があります。

```text
# images.tsv: two columns separated by a TAB; replace the internal hostname.
docker.io/library/nginx:1.30.6	harbor.airgap.local/k8s-system/dockerhub/library/nginx:1.30.6
```

接続されている側で次を実行します。

```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p image-bundle
: > image-bundle/import.tsv
index=0
while IFS=$'\t' read -r source target || [[ -n "$source" ]]; do
  [[ -z "$source" || "$source" == \#* ]] && continue
  [[ -n "$target" ]] || { echo 'Missing target image' >&2; exit 1; }
  index=$((index + 1))
  file="image-${index}.tar"
  skopeo copy --all "docker://${source}" "oci-archive:image-bundle/${file}"
  printf '%s\t%s\n' "$file" "$target" >> image-bundle/import.tsv
done < images.tsv
(cd image-bundle && sha256sum image-*.tar import.tsv > SHA256SUMS)
```

`image-bundle` を転送した後、切断された側で次を実行します。

```bash
#!/usr/bin/env bash
set -euo pipefail
cd image-bundle
sha256sum -c SHA256SUMS
# Pre-create the target Harbor projects and trust its TLS CA.
skopeo login harbor.airgap.local
while IFS=$'\t' read -r file target; do
  skopeo copy --all "oci-archive:${file}" "docker://${target}"
done < import.tsv
```

マッピングした内部イメージ URI を Pod/Helm/kubeadm の構成に適用し、digest、プラットフォーム、pull を確認します。`--all` はすべてのプラットフォームマニフェストを要求します。表現形式の変換で digest が変わる場合があるため、変換前後の結果を比較してください。

### エアギャップ用 Trivy データベースの更新

```bash
# Use a Trivy version compatible with the deployed Harbor scanner adapter.
trivy image --cache-dir ./trivy-cache --download-db-only
trivy image --cache-dir ./trivy-cache --download-java-db-only
tar -C trivy-cache -czf trivy-db-bundle.tgz db java-db
```

バンドルを各 Trivy レプリカの永続キャッシュルート `/home/scanner/.cache/trivy` に展開し、`db/trivy.db`、`db/metadata.json`、`java-db/trivy-java.db` とそのメタデータの所有者を正しく設定します。開いているデータベースを上書きせず、スキャナーを停止するか、代わりに新しい PVC/init job を使います。上記の `tar -C` 形式なら、ホームディレクトリのパスがキャッシュ内に誤ってネストするのを防げます。

```yaml
trivy:
  skipUpdate: true
  skipJavaDBUpdate: true
  offlineScan: true
```

`offlineScan` だけでは、すべてのデータベース更新が無効になるわけでも、存在しないデータベースが作成されるわけでもありません。データベースのインポート/鮮度のスケジュールを定め、更新後に再スキャンします。Compose の `harbor.yml` で相当するキーは `skip_update`、`skip_java_db_update`、`offline_scan` です。

### containerd の信頼設定

オフラインマニフェストでは内部 Harbor のイメージ参照を明示します。任意の外部レジストリを `/v2/<project>` にリダイレクトしても、リポジトリパスや認証情報は自動的に書き換わりません。各ノードに CA をインストールし、ランタイムのバージョンに合った設定を使います。

```toml
# containerd 2.x: /etc/containerd/config.toml
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
# containerd 1.x uses plugins."io.containerd.grpc.v1.cri".registry instead.
```

```toml
# /etc/containerd/certs.d/harbor.airgap.local/hosts.toml
server = "https://harbor.airgap.local"
[host."https://harbor.airgap.local"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/harbor.airgap.local/ca.crt"
```

`config_path` を変更する場合は、ノードの保守手順に従って containerd を再起動し、実際の CRI pull を確認します。namespace 単位で pull のみ許可する認証情報を `imagePullSecrets` で渡します。

## Harbor と Kubernetes の統合

### imagePullSecrets を作成する

```bash
# Create pull credentials in the same namespace as the consuming Pod.
umask 077
HARBOR_AUTH_DIR=$(mktemp -d)
python3 - "$HARBOR_AUTH_DIR/config.json" <<'PYTHON'
import base64
import getpass
import json
import pathlib
import sys
name = input("Pull robot name returned by Harbor: ")
password = getpass.getpass("Pull robot secret: ")
auth = base64.b64encode(f"{name}:{password}".encode()).decode()
pathlib.Path(sys.argv[1]).write_text(json.dumps({
    "auths": {"harbor.example.com": {"auth": auth}}
}))
PYTHON
kubectl create secret generic harbor-secret -n default \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=.dockerconfigjson="$HARBOR_AUTH_DIR/config.json" \
  --dry-run=client -o yaml \
  | kubectl apply --server-side --field-manager=harbor-pull-secret -f -
rm -rf -- "$HARBOR_AUTH_DIR"
kubectl get secret harbor-secret -n default -o jsonpath='{.type}'
```

### ServiceAccount を設定する

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
imagePullSecrets:
- name: harbor-secret
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: app-sa
      containers:
      - name: app
        image: harbor.example.com/myapp/app:v1.0.0
```

### プロキシキャッシュを設定する

![クライアントの pull 要求は Harbor のプロキシキャッシュに到達します。キャッシュヒットでは保存済みイメージをそのまま返し、キャッシュミスでは上流レジストリから取得して Harbor に保存した後、クライアントに返します。](../.gitbook/assets/en-container-registry-03-harbor-2.png)

[🔍 対話型図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-container-registry-03-harbor-2.html)

外部レジストリ向けのプロキシキャッシュとして Harbor を設定します。

```bash
# Create proxy cache project via API
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "project_name": "dockerhub-proxy",
    "registry_id": 1,
    "metadata": {
      "public": "true"
    }
  }'
```

例として、`harbor.example.com/dockerhub-proxy/library/nginx:1.30.6` のように、プロキシ用パスを明示して pull します。キャッシュミスには上流へのアクセスが必要です。キャッシュ内容の鮮度、上流で削除された場合の動作、認証の扱いはプロキシプロジェクトの設定によって異なります。オフライン環境で必要なイメージがすべて揃う保証ではありません。

### ガベージコレクション

GC は参照されていない blob を回収します。`delete_untagged` を有効にすると、タグなし artifact も削除されます。これらは digest 指定でデプロイされている場合があります。デプロイ済み/ロールバック用のイメージを先に保護してください。以下の例は削除しない dry run です。

```bash
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  'https://harbor.example.com/api/v2.0/system/gc/schedule' \
  -H 'Content-Type: application/json' \
  -d '{"schedule":{"type":"Manual"},
       "parameters":{"delete_untagged":false,"dry_run":true}}'
curl --fail-with-body --user "$HARBOR_USER"   'https://harbor.example.com/api/v2.0/system/gc'
```

UI で実際の実行/スケジュールを設定する前に、結果を確認します。Harbor では GC 中も push/pull が可能ですが、I/O 負荷と最近アップロードしたデータを保護する期間により、容量回収が遅れることがあります。

### タグ保持ポリシー

プロジェクトの Policy → Tag Retention で、**保持する**対象を定義します。直近10回の push と過去30日間を組み合わせると、両方の**OR/和集合**が保持され、artifact 数が10個を超える場合があります。Dry Run で除外されるタグ/artifact、署名との関連、デプロイ済み/ロールバック用 digest を確認します。

ポリシー作成の endpoint は `/api/v2.0/retentions` であり、プロジェクトの `/tag-retention` endpoint ではありません。推測したプロジェクト ID を使ってポリシーを作成せず、UI で設定済みの既存ポリシーを調べ、dry-run します。

```bash
curl --fail-with-body --user "$HARBOR_USER" \
  'https://harbor.example.com/api/v2.0/projects/myapp' \
  | jq '{project_id, retention_id: .metadata.retention_id}'
# Use the actual non-empty policy ID returned above.
: "${RETENTION_ID:?Set an existing retention policy ID}"
curl --fail-with-body --user "$HARBOR_USER"   "https://harbor.example.com/api/v2.0/retentions/${RETENTION_ID}"
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  "https://harbor.example.com/api/v2.0/retentions/${RETENTION_ID}/executions" \
  -H 'Content-Type: application/json' -d '{"dry_run":true}'
```

## ベストプラクティス

### 高可用性

少なくとも2つの Portal/Core/Job Service/Registry レプリカを分散配置し、PostgreSQL、Redis、共有ストレージ自体のフェイルオーバーも検証します。S3 では `persistence.imageChartStorage.type: s3`、バケット/リージョン、および明示的な Registry Pod の IAM ID または `existingSecret` を設定します。長期利用の鍵を values に埋め込まないでください。IRSA/Pod Identity には、Registry イメージで対応する SDK、正しい ServiceAccount、範囲を限定した S3 権限が必要です。静的鍵を省略しただけでは IAM ロールは設定されません。

### セキュリティ強化

外部/内部 TLS、OIDC/LDAP、有効期限付きの範囲限定 robot、監査ログ、パッチ管理を使います。レンダリング後の Pod ラベル/コンテナーポートと、必要な DNS、Core/Registry/Job Service、PostgreSQL/Redis、スキャナーデータベース、レプリケーションの通信から NetworkPolicy を作成します。ポート443だけを許可する包括的なポリシーでは、内部通信や DNS が壊れる場合があります。文書化されていない Harbor UI の制御を前提とせず、パスワード/MFA 要件は ID プロバイダーで管理します。

### バックアップ戦略

書き込み、レプリケーション、GC を調整し、PostgreSQL、Registry blob、構成、TLS、暗号化キーを一貫性のある復旧時点で取得します。Helm values はデータベース/イメージをバックアップしません。S3 バージョニングや `aws s3 sync` だけでも、一貫性のあるスナップショットは保証されません。Secret の YAML は単に Base64 エンコードされているだけなので、暗号化されアクセス制御されたバックアップに保管します。プロジェクト/robot 認証、digest pull、署名、ポリシー、スキャン結果の復元をテストしてください。

### 監視

chart の `metrics.enabled` を使い、Operator の CRD がある場合は `metrics.serviceMonitor.enabled` も使います。`http-metrics` ポートを推測せず、生成された ServiceMonitor/Service のポートを確認します。Prometheus の ServiceMonitor セレクターと namespace セレクターを一致させます。ストレージ/データベース容量、レプリケーション/スキャン/GC の失敗、キュー遅延、Trivy DB の鮮度、証明書/robot の有効期限を監視します。

## まとめ

Harbor は包括的でエンタープライズ向けのコンテナレジストリを提供し、次の点に優れています。

- **セキュリティ**: 脆弱性スキャン、イメージ署名、RBAC を内蔵
- **柔軟性**: データとインフラストラクチャを完全に管理できるセルフホスト型
- **エアギャップ対応**: 切断された環境を想定した設計
- **マルチテナンシー**: きめ細かなアクセス制御を備えたプロジェクト単位の分離
- **統合**: 対応するレジストリアダプターと artifact 形式によるレプリケーション

### Harbor を選ぶ場面

| シナリオ | 推奨 |
|----------|----------------|
| エアギャップ環境 | Harbor または対応する別のセルフホスト型レジストリ |
| 厳格なデータ主権 | Harbor |
| マルチクラウドデプロイ | Harbor |
| EKS を使う AWS ネイティブ構成 | まず ECR を検討し、高度な機能には Harbor を検討 |
| 運用要員が限られる小規模チーム | Docker Hub または ECR |
| コンプライアンス要件を持つエンタープライズ | Harbor または ECR |

### 主なポイント

1. **ストレージを慎重に計画する**: 本番では S3 互換ストレージを使う
2. **レプリケーションを設定する**: 最初から DR レプリケーションを構成する
3. **スキャンを有効にする**: 重要度のしきい値を設定し、push 時に自動スキャンする
4. **robot アカウントを使う**: CI/CD で個人の認証情報を決して使わない
5. **保持ポリシーを実装する**: ガベージコレクションと保持ポリシーを設定する
6. **監視とアラートを行う**: Prometheus のメトリクスとアラートを使う
7. **定期的にバックアップする**: データベースのバックアップは災害復旧に不可欠

## 参考資料

- [Harbor 2.15.4 release](https://github.com/goharbor/harbor/releases/tag/v2.15.4)
- [Helm chart 1.19.2 values](https://github.com/goharbor/harbor-helm/blob/v1.19.2/values.yaml)
- [Harbor 2.15.4 API schema](https://github.com/goharbor/harbor/blob/v2.15.4/api/v2.0/swagger.yaml)
- [Project role permissions](https://goharbor.io/docs/main/administration/managing-users/user-permissions-by-role/)
- [Cosign and Notation](https://goharbor.io/docs/main/working-with-projects/working-with-images/sign-images/)
- [Containerd registry hosts](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
