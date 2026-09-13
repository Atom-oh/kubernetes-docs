# コンテナイメージセキュリティ

> **最終更新**: September 13, 2026
> **検証基準**: Trivy 0.74.0、Trivy Operator 0.34.0/chart 0.36.0、Cosign 3.1.3、Kyverno 1.19.1、Connaisseur 3.12.0/chart 2.12.0。CLI/設定の基準で、全Kubernetes版にまたがるデプロイテストの主張ではありません。

イメージセキュリティは**ビルド、スキャン、デプロイした成果物が同一である**ことの確認から始まります。スキャンは既知脆弱性/設定問題を見つけ、署名は署名者とdigestを結び付けます。どちらもアプリの安全性は保証しません。

## 目次

1. [イメージスキャン概要](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Amazon ECRイメージスキャン](#amazon-ecr-image-scanning)
4. [Cosign/Sigstoreでの署名](#image-signing-with-cosignsigstore)
5. [Admission Controlでの検証](#image-verification-in-admission-control)
6. [サプライチェーンセキュリティ](#supply-chain-security)
7. [ベースイメージ選択](#base-image-selection)
8. [イメージregistryのベストプラクティス](#image-registry-best-practices)
9. [CI/CDパイプライン統合](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## イメージスキャン概要 {#image-scanning-overview}

シフトレフトはIDE、PR、buildへ確認を導入します。release後にも新CVEが現れるためregistry再スキャンとruntime検出は別要件として残ります。

| 対象 | 確認 | ツール例 |
|---|---|---|
| OS/言語package | 識別、DB経過時間、修正版、VEX判断 | Trivy、Grype |
| IaC/Dockerfile | 非root実行、権限、設定 | Trivy misconfig、Checkov |
| Secret | image layerやsource内認証情報 | Trivy secret、TruffleHog |
| License/SBOM | component/license検出範囲 | Syft、Trivy |
| Runtime動作 | 稼働syscall、process、network | Falcoなど別ツール |

流れは`source checks → build once → scan that artifact → push → sign/verify digest → admission checks → rescan`です。組織が重大度の判定条件を定め、例外に所有者、理由、期限を付けます。

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy {#trivy}

### インストールとスキャン

OS/CPU architectureに合う公式packageとchecksumを確認します。Linux ARM64にamd64を入れたり廃止apt-key手順を使ったりしないでください。自動化ではCLI/action版を固定します。

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

`IMAGE_REF`は実digestが必要な意図的placeholderです。`--scanners config`でなく`misconfig`を使います。`--ignore-unfixed`は修正なし脆弱性を隠すのでdefault gateで無差別に使いません。registry、脆弱性/Java DB、check bundleのnetwork/cache要件を確認します。`trivy config`に`--offline-scan`はありません。

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

image/filesystemスキャンの基準です。未対応vulnerability.typeやtop-level ignore一覧を加えません。.trivyignore/対応ignore-policy形式でsecretと脆弱性の例外を区別して管理します。例の.trivyignoreにdefault除外はありません。

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

chart 0.36.0はapp 0.34.0を導入します。[values](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml)はignoreUnfixed:falseを明示します。reportはoperator生成結果です。架空CVE/package版manifestをscan証拠として適用しないでください。実report schema、監視namespace、registry認証情報、scan-Job権限、resourceを確認します。監査はchart renderだけです。

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Amazon ECRイメージスキャン {#amazon-ecr-image-scanning}

| 特性 | Basic | Enhanced |
|---|---|---|
| 現エンジン | AWSネイティブscanner | Amazon Inspector |
| 範囲 | OS package脆弱性 | OSと対応言語package |
| 頻度 | 手動またはscan-on-push | scan-on-pushまたはcontinuous |
| 結果 | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| イベント | ECR basic-scan完了 | Inspector2 scan/finding |

旧Clair説明と現Basicを区別します。mode切り替えで既存結果の可視性が変わり得ます。Enhanced範囲はrepository filter、再scan期間、対応image基準に依存し、全imageを永久scanしません。アーカイブimageは復元後にscanします。

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

設定コマンドはregistryを書き換え、監査では実行していません。DescribeImagesの旧Basic要約に頼らずDescribeImageScanFindingsを使います。ECR scan有効化は脆弱imageのpush/pull/deployを自動ブロックしません。

### Inspectorアラートと権限

Enhanced findingはsource aws.inspector2、detail-type Inspector2 Finding、detail.severity/status/resources[].typeで絞ります。Basic ECR Image Scan/finding-severity-countsと混ぜません。数値0のfieldも存在するためexists:trueは正の脆弱性数を意味しません。

[完全CloudFormation例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)は暗号化SNSとEventBridge実行roleを接続します。IAM委任を許すpolicyを持つ同account/Regionの既存対称customer-managed KMSが必要で、承認SNS購読は別です。現EventBridgeはSNS targetの実行roleをサポートします。event-bus KMSのSourceArn/SourceAccount条件を、service principalから暗号化SNSへの直接経路へコピーしません。templateはcfn-lint通過済みですが、実配信、KMS認可、retryは環境でのテストが必要です。

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>



## Cosign/Sigstoreによるイメージ署名 {#image-signing-with-cosignsigstore}

### 署名順序と信頼

通常registryフローはimageをpushしdigestを取得して署名します。信頼鍵または正確なOIDC issuer/identity、digest、必要な透明性/時刻証拠を検証します。署名だけでは承認署名者や脆弱性不在は成立しません。

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

秘密鍵をcommitしません。認証情報管理/KMSなどでlifecycleを管理します。Keyless GitHub Actionsはid-token:writeとActions OIDC環境を使います。GITHUB_TOKENはregistry/API認証情報で、OIDC ID token自身ではありません。

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

identityを承認workflowへ置換します。--certificate-identity-regexpはglobでなく正規表現です。`https://github.com/org/repo/*`など寛容式より正確IDかアンカー付きregexを優先します。Cosign 3 bundle/OCI-referrerと下流verifierの互換性を確認します。

<span id="kyverno-imageverify"></span>

## Admission Controlでのイメージ検証 {#image-verification-in-admission-control}

Kyverno 1.19.1はClusterPolicy非推奨を警告します。新例はpolicies.kyverno.io/v1のValidatingPolicyとImageValidatingPolicyです。旧verifyImages ruleは新policy kind名ではありません。

### Registryとdigestのポリシー

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

pods/ephemeralcontainers更新を含み、通常/init/ephemeral containerを対象にします。example-orgを承認repositoryへ置換します。digest形式は内容アドレスを固定し、署名/脆弱性を検証しません。

### Workflow署名ポリシー

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

matchImageReferences外は検証をskipされ得るためregistry policyも適用します。namespace例外、PolicyException権限、Webhook可用性/timeout、registry認証情報、TLS信頼を設計し、実admissionをテストします。署名policyはCRD schema確認で、実registry/Fulcio/Rekor検証の証拠ではありません。本番例は透明性確認を無効にしません。

<span id="connaisseur"></span>

### Connaisseurという代替 — 旧署名経路

**Connaisseur 3.12.0は既定Cosign 3 bundleを利用しません。** 旧署名tagとSimpleSigning payloadのcosign/v2検証を使います。別の互換producerを使用します。[旧方式署名スクリプト](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh)はCosign 3.1.3で`--new-bundle-format=false --registry-referrers-mode=legacy`を明示し、透明性upload/検証を維持します。付属署名設定は旧verifierのlog形式にRekor v1を明示選択します。実承認鍵とdigestを渡します。secure-build.yamlの既定bundleとは別で、その出力を直接Connaisseurへ渡しません。legacy flagは非推奨なのでproducer/verifier協調移行を計画します。CLI optionと両source契約は確認しましたがregistry/署名統合は実行していません。

Connaisseur 3.12.0/chart 2.12.0も選択肢です。[values例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml)ではvalidators/policyはapplication下、denyは明示static validatorです。同梱公開鍵は合成test keyで、実信頼鍵へ置換が必要です。

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

例はnamespaced-validationのvalidateを使い、そのlabelがあるnamespaceだけ確認します。namespace label変更権限があるIDは選択を迂回できるため管理します。KyvernoとConnaisseurは代替で両方必須ではありません。Helm renderは実署名allow/denyテストを代替しません。

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## サプライチェーンセキュリティ {#supply-chain-security}

### SBOMとアテステーション

```bash
syft "$IMAGE_REF" -o spdx-json=sbom.spdx.json
trivy image --format spdx-json --output sbom.spdx.json "$IMAGE_REF"
trivy sbom sbom.spdx.json
# Alternatively, Grype:
# grype sbom:sbom.spdx.json
cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
cosign verify-attestation --type spdxjson   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' "$IMAGE_REF"
```

Syft/Trivy生成コマンドは選択肢です。SBOMは検出内容の一覧で、完全性/安全性は保証しません。cosign attach sbomは非推奨で、単純添付と署名attestationは異なります。predicate内容、subject digest、署名者、検証時刻、policyを一緒に検証します。

### SLSA来歴情報

来歴はbuild入力、builder、成果物の関係を記録します。生成action実行だけでSLSA Build Level 3は満たされません。関連分離、来歴偽造耐性、source policy要件を別評価します。

既存slsa-github-generator再利用workflowでは対応toolchainとcaller要件を確認します。下の新workflowは現actions/attestを使います。attest-build-provenance v4はwrapperで、新実装はactions/attestが案内されています。public/private repositoryのGitHub planとSigstore trust rootの違いを確認します。

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## ベースイメージ選択 {#base-image-selection}

| イメージ | 特性 | 確認 |
|---|---|---|
| Distroless | 標準runtimeはshell/package managerなし | debug版、library、アプリ依存は異なる |
| Alpine | 小さなmuslベース配布 | glibc互換性、保守寿命、実digest |
| Chainguard | 最小runtimeとdev版が別 | runtimeにshell/pipがあると思わない |
| Ubuntu/Debian | 広いpackage/tool選択 | サイズだけで脆弱性数は決まらない |
| Scratch | 空のbase | コピーbinary、CAファイル、アプリ依存に脆弱性が残り得る |

旧Go 1.22/Alpine 3.19例を現在の対応基準と誤解しないでください。更新時は保守、OS EOL、CPU ABI、digest、scan結果を確認します。Distrolessにはbuild段階からbinaryを渡し、Chainguard Pythonはdevで依存/venvを準備してruntimeへコピーします。本文ではDockerfile buildや脆弱性数比較を実行していません。

### 最小ベースイメージのビルド例

[完全build context](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images)は固定メッセージを出すGo/Pythonと3 Dockerfileです。1つ選んでパターンを比較します。web server例ではありません。base-index digestとamd64/arm64提供は確認し、container build/runtimeは実行していません。

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

アプリはGo 1.27.1/Python 3.12で直接実行し、全3 DockerfileがHIGH/CRITICAL設定確認を通過しました。このfixtureのPython requirementsは空です。実依存追加にはlock/hash、builder/runtime ABI確認、脆弱性scanが必要です。Alpine apk repositoryとbase digest更新は別管理します。

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## イメージregistryのベストプラクティス {#image-registry-best-practices}

- private imageは承認pull IDが必要。ECR kubelet/node/Fargate実行roleはアプリPod Identityと異なる。
- 外部registryは有効なkubernetes.io/dockerconfigjson SecretとServiceAccount imagePullSecretsを使える。Base64は暗号化ではない。
- imagePullPolicy:Alwaysはregistry参照確認で、署名検証ではない。digest固定、admission検証、scan gateを別設定。
- latest禁止だけでは省略tagやinit/ephemeralを見逃し得る。上のregistry/digest policyで範囲をテスト。
- 意図的public imageの匿名pullは本質的脆弱性ではない。機密性、push権限、来歴、rate limit、licenseを分ける。
- 保持/GCで使用中digestや必要署名/attestation referrerを消さないようにし、復旧をテスト。

<span id="complete-image-security-pipeline"></span>



## CI/CDパイプライン統合 {#cicd-pipeline-integration}

アプリrepositoryの.github/workflows/secure-build.yamlへ置く前に[完全workflow](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml)を確認します。実Dockerfileとcontextが前提です。意図する特性:

1. PR scanはregistry公開/OIDC署名なしのread-only job。
2. main-push release jobは1度だけbuildし、そのlocal imageをscan。
3. 再buildせずpushしRepoDigestを取得。
4. 署名、検証、SBOM attestation、来歴に同じdigestを使用。
5. Actionはreview済みcommit SHA固定。別artifact-storage記録は無効。

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

GHCR package権限、Actions OIDC、attestation plan対応、networkを設定します。YAML/action入力とshell構文は確認しましたがGitHub runnerのbuild/push/sign/attestは実行していません。SBOM/署名失敗を無視したり空digestを渡したりしません。SARIF追加時はfork PRのsecurity-events権限とscan失敗後の結果保持を別対応します。

## 実施した確認と限界

- Trivy 0.74: 合成secret 2ケースとDockerfile非root確認2件。実CVE DB/remote image scanなし。
- Cosign 3.1.3: 合成local key/blobの正常/改変検証。private fixtureで透明性を省略しても本番registry/OIDC検証の証拠ではない。
- Kyverno 1.19.1: init/ephemeralを含むCEL registry/digest 6ケースと固定CRD schema 2つ。実admission/network署名検証なし。
- Trivy Operator/Connaisseur render、合成ECR API-model/JMESPath fixture、CloudFormation lint、actionlintを実行。AWS resource、通知、registry pushは実行していない。

<span id="summary"></span>
<span id="recommendations"></span>

## 参考資料

- [Trivyリリース](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Trivyドキュメント](https://aquasecurity.github.io/trivy/)
- [Trivy Operatorチャート](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [ECRスキャン](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Inspectorイベントschema](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [EventBridge target認可](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [SNS KMS互換性](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Sigstore検証](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Kyverno CEL移行](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Connaisseur名前空間検証](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [SLSA要件](https://slsa.dev/spec/v1.2/build-requirements)
- [GitHub attest action](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
