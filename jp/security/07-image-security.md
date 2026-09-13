# コンテナイメージセキュリティ

> **最終更新**: September 13, 2026
> **検証ベースライン**: Trivy 0.74.0、Trivy Operator 0.34.0/chart 0.36.0、Cosign 3.1.3、Kyverno 1.19.1、Connaisseur 3.12.0/chart 2.12.0。これらは CLI/設定のベースラインであり、すべての Kubernetes バージョンにわたるデプロイテストを主張するものではありません。

イメージセキュリティは、**ビルド、スキャン、デプロイされた成果物が同一であること**を確認することから始まります。スキャンは既知の脆弱性と設定上の問題を特定し、署名は署名者を digest に結び付けます。いずれもアプリケーションの安全性を保証するものではありません。

## 目次

1. [イメージスキャンの概要](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Amazon ECR イメージスキャン](#amazon-ecr-image-scanning)
4. [Cosign/Sigstore によるイメージ署名](#image-signing-with-cosignsigstore)
5. [Admission Control におけるイメージ検証](#image-verification-in-admission-control)
6. [サプライチェーンセキュリティ](#supply-chain-security)
7. [ベースイメージの選択](#base-image-selection)
8. [イメージレジストリのベストプラクティス](#image-registry-best-practices)
9. [CI/CD パイプライン統合](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## イメージスキャンの概要

Shift-left は IDE、PR、ビルドでチェックを導入します。新しい CVE はリリース後に出現するため、レジストリの再スキャンとランタイム検出は引き続き別個の要件です。

| 対象 | チェック | ツール例 |
|---|---|---|
| OS/言語パッケージ | 識別、データベースの鮮度、修正済みバージョン、VEX の判断 | Trivy、Grype |
| IaC/Dockerfile | 非 root 実行、権限、設定 | Trivy misconfig、Checkov |
| シークレット | イメージレイヤーまたはソース内の認証情報 | Trivy secret、TruffleHog |
| ライセンス/SBOM | コンポーネントおよびライセンス検出の網羅性 | Syft、Trivy |
| ランタイムの動作 | 実行中の syscall、プロセス、ネットワーク | Falco などの別ツール |

フローは `source checks → build once → scan that artifact → push → sign/verify digest → admission checks → rescan` です。組織は重大度ゲートを定義し、例外には所有者、根拠、有効期限を付与します。

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy

### インストールとスキャン

オペレーティングシステム/CPU アーキテクチャ向けの公式リリースパッケージと、その checksum を検証してください。Linux ARM64 に amd64 バイナリをインストールしたり、廃止された apt-key 手順を使用したりしないでください。自動化では CLI/action のバージョンを固定してください。

```bash
trivy --version
# Replace with an immutable reference that you actually own.
IMAGE_REF='registry.example.com/team/app@sha256:REPLACE_WITH_64_HEX_DIGEST'
trivy image --severity HIGH,CRITICAL --exit-code 1 "$IMAGE_REF"
trivy image --format json --output results.json "$IMAGE_REF"
trivy image --format sarif --output results.sarif "$IMAGE_REF"
trivy image --scanners vuln,secret "$IMAGE_REF"
trivy fs --scanners vuln,secret,misconfig .
trivy config ./k8s/
trivy config ./charts/my-app/ --helm-values ./charts/my-app/values.yaml
```

`IMAGE_REF` は実際の digest を必要とする意図的なプレースホルダーです。`--scanners config` ではなく `misconfig` を使用してください。`--ignore-unfixed` は修正のない脆弱性を隠すため、デフォルトゲートで無差別に有効にしないでください。レジストリ、脆弱性/Java データベース、チェックバンドルのネットワーク/キャッシュ要件を確認してください。`trivy config` には `--offline-scan` オプションはありません。

### 設定と例外

```yaml
# Baseline for image/filesystem scans; explicitly review exceptions in .trivyignore.
severity:
  - HIGH
  - CRITICAL
exit-code: 1
ignorefile: .trivyignore
scan:
  scanners:
    - vuln
    - secret
    - misconfig
  parallel: 2
  disable-telemetry: true
vulnerability:
  ignore-unfixed: false
```

これはイメージ/ファイルシステムスキャンのベースラインです。サポートされない vulnerability.type やトップレベルの ignore リストを追加しないでください。シークレットと脆弱性の例外を区別し、.trivyignore/サポート対象の ignore-policy 形式で例外を管理してください。例の .trivyignore にはデフォルト除外はありません。

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

Chart 0.36.0 は application 0.34.0 をデプロイします。[values ファイル](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml)では ignoreUnfixed:false を明示的に設定しています。レポートは Operator が生成した結果です。スキャンの証拠として、捏造した CVE/package-version manifest を適用しないでください。実際のレポートスキーマ、監視対象の namespace、レジストリ認証情報、scan-Job 権限、リソースを確認してください。この監査では Chart のレンダリングのみを実行しました。

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Amazon ECR イメージスキャン

| プロパティ | Basic | Enhanced |
|---|---|---|
| 現在のエンジン | AWS ネイティブスキャナー | Amazon Inspector |
| 対象範囲 | OS パッケージの脆弱性 | OS およびサポート対象の言語パッケージ |
| 頻度 | 手動または push 時スキャン | push 時スキャンまたは継続的 |
| 結果 | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| イベント | ECR Basic スキャン完了 | Inspector2 スキャン/検出イベント |

古い Clair の説明と現在の Basic エンジンを区別してください。スキャンモードを切り替えると、既存の結果の可視性が変わることがあります。Enhanced の対象範囲はリポジトリフィルター、再スキャン期間、サポート対象イメージの条件に依存します。すべてのイメージが永久にスキャンされるわけではありません。アーカイブ済みイメージは、スキャン前に復元する必要があります。

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

この設定コマンドはレジストリ設定を書き込みますが、この監査では実行していません。DescribeImages の古い Basic サマリーに依存せず、DescribeImageScanFindings を使用してください。ECR スキャンを有効にしても、脆弱なイメージの push、pull、デプロイが自動的にブロックされるわけではありません。

### Inspector アラートと権限

Enhanced の検出結果は、source aws.inspector2、detail-type Inspector2 Finding、detail.severity/status/resources[].type でフィルタリングしてください。これを Basic ECR Image Scan および finding-severity-counts と混在させないでください。数値がゼロのフィールドも存在します。exists:true は脆弱性数が正であることを意味しません。

[完全な CloudFormation の例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)は、暗号化された SNS topic を EventBridge 実行ロールに接続します。これは、IAM 委任を許可するポリシーを持つ、同一アカウント/Region の既存の対称 customer-managed KMS key を必要とします。承認済み SNS コンシューマーの subscription は別途必要です。現在の EventBridge は SNS target の実行ロールをサポートしています。event-bus KMS の SourceArn/SourceAccount 条件を、暗号化された SNS への直接のサービスプリンシパル経路にコピーしないでください。この template は cfn-lint に合格しましたが、実際の配信、KMS 認可、再試行にはデプロイ環境でのテストが必要です。

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>

## Cosign/Sigstore によるイメージ署名

### 署名順序と信頼

通常のレジストリフローでは、イメージを push し、その digest を取得して、その digest に署名します。信頼できる key または厳密な OIDC issuer/identity、digest、および必要な透明性/timestamp の証拠を検証してください。署名だけでは、承認済みの署名者や脆弱性がないことを確立できません。

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

private key を commit しないでください。credential manager/KMS または同等の管理を通じて、そのライフサイクルを管理してください。keyless GitHub Actions は id-token:write と Actions OIDC 環境を使用します。GITHUB_TOKEN はレジストリ/API 認証情報であり、OIDC ID token 自体ではありません。

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

identity を承認済み workflow に置き換えてください。--certificate-identity-regexp は glob ではなく正規表現を受け取ります。`https://github.com/org/repo/*` のような寛容な式より、厳密な identity またはアンカー付き regexp を優先してください。Cosign 3 の bundle/OCI-referrer の下流 verifier との互換性を確認してください。

<span id="kyverno-imageverify"></span>

## Admission Control におけるイメージ検証

Kyverno 1.19.1 は ClusterPolicy が非推奨であると警告します。新しい例では policies.kyverno.io/v1 の ValidatingPolicy および ImageValidatingPolicy を使用します。従来の verifyImages rule は、新しい policy kind の名前ではありません。

### レジストリと digest のポリシー

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: approved-registry-and-digest
spec:
  failurePolicy: Fail
  validationActions: [Deny]
  evaluation:
    background:
      enabled: false
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods, pods/ephemeralcontainers]
  variables:
    - name: containers
      expression: >-
        object.spec.containers +
        (has(object.spec.initContainers) ? object.spec.initContainers : []) +
        (has(object.spec.ephemeralContainers) ? object.spec.ephemeralContainers : [])
  validations:
    - expression: >-
        variables.containers.all(c,
          c.image.matches('^ghcr[.]io/example-org/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$'))
      message: All container images must use the approved repository and a SHA-256 digest.
```

これは通常のコンテナ、init コンテナ、ephemeral コンテナ、および pods/ephemeralcontainers の更新を対象にします。example-org を承認済みのリポジトリに置き換えてください。digest 形式はコンテンツアドレスを固定します。署名または脆弱性の検証を実行するものではありません。

### Workflow 署名ポリシー

```yaml
apiVersion: policies.kyverno.io/v1
kind: ImageValidatingPolicy
metadata:
  name: verify-approved-workflow
spec:
  failurePolicy: Fail
  validationActions: [Deny]
  evaluation:
    background:
      enabled: false
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods, pods/ephemeralcontainers]
  matchImageReferences:
    - glob: ghcr.io/example-org/*
  validationConfigurations:
    mutateDigest: false
    verifyDigest: true
    required: true
  images:
    - name: workloadImages
      expression: >-
        (object.spec.containers +
        (has(object.spec.initContainers) ? object.spec.initContainers : []) +
        (has(object.spec.ephemeralContainers) ? object.spec.ephemeralContainers : []))
        .map(c, c.image)
  attestors:
    - name: githubRelease
      cosign:
        keyless:
          identities:
            - issuer: https://token.actions.githubusercontent.com
              subject: https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main
        ctlog:
          url: https://rekor.sigstore.dev
          insecureIgnoreTlog: false
          insecureIgnoreSCT: false
  validations:
    - expression: >-
        images.workloadImages.map(image,
          verifyImageSignatures(image, [attestors.githubRelease]))
          .all(result, result > 0)
      message: Image signature must match the approved workflow and transparency proof.
```

matchImageReferences 外のイメージはイメージ検証でスキップされる可能性があるため、レジストリポリシーも適用してください。namespace の例外、PolicyException へのアクセス、webhook の可用性/timeouts、レジストリ認証情報、TLS trust を設計してから、実際の admission request をテストしてください。署名ポリシーは CRD schema に対してチェックされました。これは、実際のレジストリ/Fulcio/Rekor 検証の証拠ではありません。本番の例では透明性チェックを無効にしません。

<span id="connaisseur"></span>

### Connaisseur の代替手段 — 従来の署名パス

**Connaisseur 3.12.0 はデフォルトの Cosign 3 bundle のコンシューマーではありません。**これは legacy signature tag および SimpleSigning payload を伴う cosign/v2 検証パスを使用します。別の互換性 producer を使用してください。[従来の署名スクリプト](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh)は、透明性の upload/verification を維持しながら、Cosign 3.1.3 の `--new-bundle-format=false --registry-referrers-mode=legacy` を明示的に設定します。付属の signing config は、従来の verifier の log format 用に Rekor v1 を明示的に選択します。実際に承認された key と digest を指定してください。このパスは secure-build.yaml のデフォルト bundle format とは別です。その workflow のデフォルト出力を Connaisseur に直接渡さないでください。従来の flag は非推奨であるため、producer/verifier を協調して移行する計画を立ててください。CLI オプションと両方の source contract はチェック済みですが、レジストリ/署名統合は実行していません。

Connaisseur 3.12.0/chart 2.12.0 も別の選択肢です。[values の例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml)では、validator と policy は application 配下にあり、deny は明示的に定義された static validator です。含まれる public key は実際の trust key に置き換える必要がある合成テスト key です。

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

この例は namespaced-validation の validate mode を使用し、その label を持つ namespace のみをチェックします。namespace label を変更できる identity はこの選択を迂回できるため、その権限を管理してください。Kyverno と Connaisseur は代替手段であり、両方をインストールする要件ではありません。Helm rendering は実際の署名 allow/deny テストの代わりにはなりません。

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## サプライチェーンセキュリティ

### SBOM と attestation

```bash
syft "$IMAGE_REF" -o spdx-json=sbom.spdx.json
trivy image --format spdx-json --output sbom.spdx.json "$IMAGE_REF"
trivy sbom sbom.spdx.json
# Alternatively, Grype:
# grype sbom:sbom.spdx.json
cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
cosign verify-attestation --type spdxjson   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' "$IMAGE_REF"
```

Syft/Trivy の生成コマンドは代替手段です。SBOM はツールが検出したものを棚卸しします。完全性と安全性は保証されません。cosign attach sbom は非推奨であり、プレーンな attachment は署名付き attestation とは異なります。predicate の内容、subject digest、署名者、検証時刻、ポリシーをまとめて検証してください。

### SLSA provenance

provenance は、ビルド入力、builder、成果物間の関係を記録します。生成 action を呼び出しても、SLSA Build Level 3 を自動的に満たすわけではありません。関連する isolation、provenance 偽造耐性、source-policy の要件を別途評価してください。

既存の slsa-github-generator reusable workflow では、サポート対象の toolchain と caller 要件を確認してください。以下の新しい workflow では現在の actions/attest を使用します。attest-build-provenance の version 4 は wrapper です。新しい実装は actions/attest に移行するよう案内されています。public repository と private repository で異なる GitHub-plan および Sigstore-trust-root を確認してください。

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## ベースイメージの選択

| イメージ | 特性 | 確認事項 |
|---|---|---|
| Distroless | 標準 runtime では shell/package manager を省略 | debug variant、library、アプリケーション依存関係は異なる |
| Alpine | 小さな musl ベースのディストリビューション | glibc 互換性、保守期間、実際の digest |
| Chainguard | 異なる最小 runtime と dev variant | runtime イメージに shell/pip が含まれると想定しない |
| Ubuntu/Debian | より幅広いパッケージ/ツールの選択肢 | サイズだけでは脆弱性数は決まらない |
| Scratch | 空のベースイメージ | コピーされた binary、CA file、アプリケーション依存関係にも脆弱性があり得る |

古い Go 1.22/Alpine 3.19 の例を、現在サポートされているベースラインと誤認しないでください。更新時には保守状況、OS EOL、CPU ABI、digest、スキャン結果を確認してください。Distroless は build stage から binary を受け取ります。Chainguard Python パターンに従い、dev stage で dependency/venv を準備し、それらを runtime にコピーしてください。このドキュメントでは Dockerfile のビルドや脆弱性数の比較を実行していません。

### 最小ベースイメージのビルド例

[完全なビルドコンテキスト](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images)には、固定メッセージを出力する Go/Python プログラムと 3 つの Dockerfile が含まれます。パターンを比較する Dockerfile を選択してください。これらは web-server の例ではありません。base-index digest と amd64/arm64 の可用性は確認しましたが、コンテナのビルド/ランタイムは実行していません。

**Dockerfile.distroless**

```dockerfile
FROM golang:1.27.1@sha256:f44f6e88636cfb311f9ebace870ded69d943f227bb3cb27d32ffd84ea18c43ea AS builder
WORKDIR /src
COPY go.mod main.go ./
RUN CGO_ENABLED=0 go build -trimpath -o /out/app .
FROM gcr.io/distroless/static-debian13:nonroot@sha256:1c2c046bc09ed40fad370b599a0b1ae7987f55b01e247cf27a7c27cd97e5bbc7
COPY --from=builder /out/app /app
USER 65532:65532
ENTRYPOINT ["/app"]
```

**Dockerfile.chainguard**

```dockerfile
FROM cgr.dev/chainguard/python:latest-dev@sha256:b0bc807f4334fea6adaac0f4dfbde255b9938ca957facb26eaed8bb448fce473 AS builder
WORKDIR /app
COPY requirements.txt ./
RUN python -m venv /app/venv && /app/venv/bin/pip install --no-cache-dir -r requirements.txt
FROM cgr.dev/chainguard/python:latest@sha256:b5decb00aa1cb65ab71bb3f6632a44bb8e6fd8d661de1f0342fd513a06837b9a
WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY app.py /app/app.py
USER 65532:65532
ENTRYPOINT ["/app/venv/bin/python", "/app/app.py"]
```

**Dockerfile.alpine**

```dockerfile
FROM alpine:3.24.1@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b
RUN apk add --no-cache python3 && addgroup -g 10001 app && adduser -D -u 10001 -G app app
WORKDIR /app
COPY --chown=10001:10001 app.py /app/app.py
USER 10001:10001
ENTRYPOINT ["python3", "/app/app.py"]
```

アプリケーションは Go 1.27.1 と Python 3.12 で直接実行され、3 つの Dockerfile はすべて HIGH/CRITICAL の設定チェックに合格しました。この fixture の Python requirements は空です。実際の dependency を追加するには、lock/hash、builder/runtime ABI チェック、脆弱性スキャンが必要です。Alpine apk リポジトリとベース digest の更新は別途管理してください。

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## イメージレジストリのベストプラクティス

- Private イメージには承認済みの pull identity が必要です。ECR kubelet/node/Fargate 実行ロールはアプリケーションの Pod Identity とは異なります。
- 外部レジストリでは、有効な kubernetes.io/dockerconfigjson Secret と ServiceAccount imagePullSecrets を使用できます。Base64 は暗号化ではありません。
- imagePullPolicy:Always はレジストリ参照のチェックを制御するものであり、署名検証を行うものではありません。digest pinning、admission 検証、スキャンゲートを別途設定してください。
- latest のみを禁止するパターンでは、タグの省略や init/ephemeral イメージを見逃す可能性があります。上記のレジストリ/digest ポリシーでスコープをテストしてください。
- 意図的に public とされたイメージの anonymous pull は、必ずしも脆弱性ではありません。機密性、push 権限、provenance、rate limit、ライセンス要件を分けて扱ってください。
- retention/garbage collection によってアクティブな digest や必要な署名/attestation referrer が削除されないようにし、復旧をテストしてください。

<span id="complete-image-security-pipeline"></span>

## CI/CD パイプライン統合

アプリケーションリポジトリの .github/workflows/secure-build.yaml に配置する前に、[完全な workflow ファイル](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml)を確認してください。実際の Dockerfile と build context が前提条件です。想定される特性は次のとおりです。

1. PR スキャンでは、レジストリ公開/OIDC 署名を行わない read-only Job を使用します。
2. main-push release Job は一度だけビルドし、そのローカルイメージをスキャンします。
3. 再ビルドせずに push し、RepoDigest を取得します。
4. 署名、検証、SBOM attestation、provenance は同じ digest を使用します。
5. Actions はレビュー済みの commit SHA に固定され、別の artifact-storage record は無効化されます。

```yaml
name: Secure Image Build
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  pull-request-scan:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          load: true
          tags: local/audit-app:${{ github.sha }}
      - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          version: v0.74.0
          scan-type: image
          image-ref: local/audit-app:${{ github.sha }}
          scanners: vuln,secret
          severity: HIGH,CRITICAL
          exit-code: '1'
          ignore-unfixed: 'false'
  release:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Normalize the registry image name
        id: image
        shell: bash
        run: |
          set -euo pipefail
          repository="ghcr.io/${GITHUB_REPOSITORY,,}"
          printf 'repository=%s\ntag=%s:%s\n' "$repository" "$repository" "$GITHUB_SHA" >> "$GITHUB_OUTPUT"
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - name: Build once into the local image store
        uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          load: true
          tags: ${{ steps.image.outputs.tag }}
      - name: Scan the exact local artifact that will be pushed
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          version: v0.74.0
          scan-type: image
          image-ref: ${{ steps.image.outputs.tag }}
          scanners: vuln,secret
          severity: HIGH,CRITICAL
          exit-code: '1'
          ignore-unfixed: 'false'
      - uses: docker/login-action@dbcb813823bdd20940b903addbd779551569679f # v4.6.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Push without rebuilding and capture the registry digest
        id: published
        env:
          IMAGE_TAG: ${{ steps.image.outputs.tag }}
          IMAGE_REPOSITORY: ${{ steps.image.outputs.repository }}
        shell: bash
        run: |
          set -euo pipefail
          docker push "$IMAGE_TAG"
          ref=$(docker image inspect "$IMAGE_TAG" --format '{{index .RepoDigests 0}}')
          digest="${ref##*@}"
          [[ "$ref" == "$IMAGE_REPOSITORY"@* ]]
          [[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]
          printf 'ref=%s\ndigest=%s\n' "$ref" "$digest" >> "$GITHUB_OUTPUT"
      - uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2
        with:
          cosign-release: v3.1.3
      - name: Sign and verify the immutable image
        env:
          IMAGE_REF: ${{ steps.published.outputs.ref }}
        shell: bash
        run: |
          set -euo pipefail
          cosign sign --yes "$IMAGE_REF"
          cosign verify --certificate-identity "${GITHUB_SERVER_URL}/${GITHUB_WORKFLOW_REF}"             --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMAGE_REF"
      - name: Generate SBOM for the pushed digest
        uses: anchore/sbom-action@3ad7283483fc7af8ff2b4ea19663c2d5ca935e26 # v0.24.2
        with:
          image: ${{ steps.published.outputs.ref }}
          syft-version: v1.51.1
          format: spdx-json
          output-file: sbom.spdx.json
          upload-artifact: false
      - name: Sign the SBOM as an attestation
        env:
          IMAGE_REF: ${{ steps.published.outputs.ref }}
        shell: bash
        run: |
          set -euo pipefail
          cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
          cosign verify-attestation --type spdxjson             --certificate-identity "${GITHUB_SERVER_URL}/${GITHUB_WORKFLOW_REF}"             --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMAGE_REF"
      - name: Publish build provenance
        uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2
        with:
          subject-name: ${{ steps.image.outputs.repository }}
          subject-digest: ${{ steps.published.outputs.digest }}
          push-to-registry: true
          create-storage-record: false
```

GHCR package permissions、Actions OIDC、attestation-plan のサポート、ネットワークアクセスを設定してください。Workflow YAML/action input と shell 構文はチェックしましたが、GitHub-runner での build/push/sign/attest workflow は実行していません。SBOM/署名の失敗を無視したり、空の digest を後続に渡したりしないでください。SARIF upload を追加する場合は、fork PR の security-events 権限と、スキャン失敗後も結果を保持する方法を別途扱ってください。

## 実施したチェックと制限

- Trivy 0.74: 2 つの合成シークレットケースと、2 つの Dockerfile 非 root チェック。実際の CVE データベースまたはリモートイメージスキャンは未実施です。
- Cosign 3.1.3: 有効/改ざん済みの合成ローカル key/blob の検証。private fixture で透明性を省略したことは、本番のレジストリ/OIDC 検証の証拠ではありません。
- Kyverno 1.19.1: init/ephemeral コンテナを含む 6 つの CEL レジストリ/digest object ケースと、2 つの固定 CRD schema。実際の admission またはネットワーク署名検証は未実施です。
- Trivy Operator/Connaisseur の Helm rendering、合成 ECR API-model/JMESPath fixture、CloudFormation lint、actionlint を実行しました。AWS リソース、通知、レジストリ push は実行していません。

<span id="summary"></span>
<span id="recommendations"></span>

## 参考資料

- [Trivy リリース](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Trivy ドキュメント](https://aquasecurity.github.io/trivy/)
- [Trivy Operator Chart](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [ECR スキャン](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Inspector イベントスキーマ](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [EventBridge target 認可](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [SNS KMS 互換性](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Sigstore 検証](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Kyverno CEL 移行](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Connaisseur の namespaced validation](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [SLSA 要件](https://slsa.dev/spec/v1.2/build-requirements)
- [GitHub attest action](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
