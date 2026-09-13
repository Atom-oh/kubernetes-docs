# 容器镜像安全

> **最后更新**: September 13, 2026
> **验证基线**: Trivy 0.74.0, Trivy Operator 0.34.0/chart 0.36.0, Cosign 3.1.3, Kyverno 1.19.1, Connaisseur 3.12.0/chart 2.12.0。这些是 CLI/配置基线，并不代表已在所有 Kubernetes 版本上完成部署测试。

镜像安全始于确认**构建、扫描和部署的制品相同**。扫描可识别已知漏洞和配置问题；签名可将签名者关联到摘要。二者都不能保证应用程序安全。

## 目录

1. [镜像扫描概览](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Amazon ECR 镜像扫描](#amazon-ecr-image-scanning)
4. [使用 Cosign/Sigstore 对镜像签名](#image-signing-with-cosignsigstore)
5. [在准入控制中验证镜像](#image-verification-in-admission-control)
6. [供应链安全](#supply-chain-security)
7. [基础镜像选择](#base-image-selection)
8. [镜像注册表最佳实践](#image-registry-best-practices)
9. [CI/CD 流水线集成](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## 镜像扫描概览

左移（Shift-left）会在 IDE、PR 和构建阶段引入检查。新的 CVE 会在发布后出现，因此注册表重新扫描和运行时检测仍是独立的要求。

| 目标 | 检查项 | 示例工具 |
|---|---|---|
| OS/语言包 | 识别、数据库时效、已修复版本、VEX 决策 | Trivy, Grype |
| IaC/Dockerfile | 非 root 执行、权限、配置 | Trivy misconfig, Checkov |
| Secret | 镜像层或源代码中的凭证 | Trivy secret, TruffleHog |
| 许可证/SBOM | 组件和许可证检测覆盖范围 | Syft, Trivy |
| 运行时行为 | 实时系统调用、进程、网络 | Falco 等独立工具 |

流程为 `source checks → build once → scan that artifact → push → sign/verify digest → admission checks → rescan`。组织应定义严重性门禁，并为例外指定负责人、理由和到期时间。

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy

### 安装和扫描

验证适用于操作系统/CPU 架构的官方发行包及其校验和。不要在 Linux ARM64 上安装 amd64 二进制文件，也不要使用已废弃的 apt-key 指令。在自动化中固定 CLI/action 版本。

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

`IMAGE_REF` 是一个有意设置的占位符，需要替换为真实摘要。使用 `misconfig`，而不是 `--scanners config`。`--ignore-unfixed` 会隐藏尚未修复的漏洞，因此不要在默认门禁中不加区分地启用它。检查注册表、漏洞/Java 数据库和检查包的网络/缓存要求。`trivy config` 没有 `--offline-scan` 选项。

### 配置和例外

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

这是镜像/文件系统扫描基线。不要添加不受支持的 vulnerability.type 或顶层忽略列表。通过 .trivyignore/受支持的忽略策略格式管理例外，并区分 Secret 和漏洞例外。示例 .trivyignore 不含默认排除项。

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

Chart 0.36.0 部署应用程序 0.34.0。[values 文件](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml)明确设置了 ignoreUnfixed:false。报告是 Operator 生成的结果；不要将虚构的 CVE/包版本清单作为扫描证据应用。检查实际报告架构、被监视的 namespace、注册表凭证、扫描 Job 权限和资源。本审计仅渲染了 Chart。

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Amazon ECR 镜像扫描

| 属性 | 基础 | 增强 |
|---|---|---|
| 当前引擎 | AWS 原生扫描器 | Amazon Inspector |
| 覆盖范围 | OS 包漏洞 | OS 和受支持的语言包 |
| 频率 | 手动或推送时扫描 | 推送时扫描或持续扫描 |
| 结果 | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| 事件 | ECR 基础扫描完成 | Inspector2 扫描/发现事件 |

应将较早的 Clair 描述与当前的 Basic 引擎区分开来。切换扫描模式可能改变既有结果的可见性。增强扫描覆盖范围取决于存储库筛选器、重新扫描时长和受支持镜像条件；并非每个镜像都会被永久扫描。归档镜像必须先恢复才能扫描。

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

该配置命令会写入注册表设置，本审计未执行它。使用 DescribeImageScanFindings，而不要依赖 DescribeImages 中旧版 Basic 摘要。启用 ECR 扫描不会自动阻止有漏洞的镜像被推送、拉取或部署。

### Inspector 警报和权限

使用 source aws.inspector2、detail-type Inspector2 Finding 和 detail.severity/status/resources[].type 筛选 Enhanced 发现。不要将其与 Basic ECR Image Scan 和 finding-severity-counts 混用。数值为零的字段仍然存在；exists:true 并不意味着存在正数漏洞计数。

[完整的 CloudFormation 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)将加密的 SNS topic 连接到 EventBridge 执行角色。它需要一个现有的、同一账户/Region 的对称客户托管 KMS key，其策略允许 IAM 委派；经批准的 SNS 消费者订阅需单独配置。当前 EventBridge 支持为 SNS target 使用执行角色。不要将 event-bus KMS SourceArn/SourceAccount 条件复制到直接 service-principal-to-encrypted-SNS 路径中。该模板已通过 cfn-lint；实际投递、KMS 授权和重试需要在部署环境中测试。

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>

## 使用 Cosign/Sigstore 对镜像签名

### 签名顺序和信任

对于常见的注册表流程，推送镜像、获取其摘要，然后对该摘要签名。验证受信任的 key 或精确的 OIDC issuer/identity、摘要以及所需的透明度/时间戳证据。单独的签名并不能证明签名者已获批准或不存在漏洞。

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

不要提交私钥。通过凭证管理器/KMS 或等效控制措施管理其生命周期。无密钥 GitHub Actions 使用 id-token:write 和 Actions OIDC 环境。GITHUB_TOKEN 是注册表/API 凭证，而不是 OIDC ID token 本身。

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

将 identity 替换为获批准的 workflow。--certificate-identity-regexp 接受正则表达式，而非 glob。优先使用精确 identity 或锚定的 regexp，而不是 `https://github.com/org/repo/*` 等宽松表达式。检查 Cosign 3 bundle/OCI-referrer 与下游验证器的兼容性。

<span id="kyverno-imageverify"></span>

## 在准入控制中验证镜像

Kyverno 1.19.1 警告 ClusterPolicy 已弃用。新示例使用 policies.kyverno.io/v1 ValidatingPolicy 和 ImageValidatingPolicy。旧版 verifyImages rule 并不是新 policy kind 的名称。

### 注册表和摘要策略

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

此策略覆盖普通、init 和 ephemeral container，包括 pods/ephemeralcontainers 更新。将 example-org 替换为获批准的存储库。摘要格式会固定内容地址；它不会执行签名或漏洞验证。

### Workflow 签名策略

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

matchImageReferences 之外的镜像可能被镜像验证跳过，因此也应应用注册表策略。设计 namespace 例外、PolicyException 访问权限、webhook 可用性/超时、注册表凭证和 TLS 信任，然后测试实际准入请求。签名策略已根据 CRD schema 检查；这并非实时注册表/Fulcio/Rekor 验证的证据。生产示例不会禁用透明度检查。

<span id="connaisseur"></span>

### Connaisseur 替代方案 — 旧版签名路径

**Connaisseur 3.12.0 不使用默认 Cosign 3 bundle。**它使用带有旧版 signature tag 和 SimpleSigning payload 的 cosign/v2 验证路径。请使用独立的兼容性生产者。[旧版签名脚本](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh)明确设置 Cosign 3.1.3 `--new-bundle-format=false --registry-referrers-mode=legacy`，同时保留透明度上传/验证。随附的签名配置为旧版验证器的日志格式明确选择 Rekor v1。提供真实获批准的 key 和摘要。此路径独立于 secure-build.yaml 的默认 bundle 格式；不要将该 workflow 的默认输出直接提供给 Connaisseur。旧版 flag 已弃用，因此应规划协调的生产者/验证器迁移。CLI 选项和两个源合同均已检查；未执行注册表/签名集成。

Connaisseur 3.12.0/chart 2.12.0 是另一种选择。在 [values 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml)中，validator 和 policy 位于 application 下，deny 是明确定义的静态 validator。附带的公钥是合成测试 key，必须替换为真实信任 key。

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

该示例使用 namespaced-validation validate 模式，并且只检查带有该 label 的 namespace。允许更改 namespace label 的 identity 可以绕过此选择，因此应治理这些权限。Kyverno 和 Connaisseur 是替代方案，而不是要求同时安装两者。Helm 渲染不能替代实际签名允许/拒绝测试。

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## 供应链安全

### SBOM 和证明

```bash
syft "$IMAGE_REF" -o spdx-json=sbom.spdx.json
trivy image --format spdx-json --output sbom.spdx.json "$IMAGE_REF"
trivy sbom sbom.spdx.json
# Alternatively, Grype:
# grype sbom:sbom.spdx.json
cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
cosign verify-attestation --type spdxjson   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' "$IMAGE_REF"
```

Syft/Trivy 生成命令是替代方案。SBOM 会清点工具检测到的内容；完整性和安全性无法保证。cosign attach sbom 已弃用，普通附件与已签名证明不同。应一起验证 predicate 内容、subject 摘要、签名者、验证时间和策略。

### SLSA 溯源

溯源记录构建输入、构建器和制品之间的关系。调用生成 action 并不会自动满足 SLSA Build Level 3。请单独评估相关的隔离性、溯源伪造抵抗能力和源策略要求。

对于现有的 slsa-github-generator 可复用 workflow，请检查受支持的工具链和调用方要求。以下新 workflow 使用当前的 actions/attest。对于公共与私有存储库，请检查 GitHub plan 和 Sigstore trust root 的差异。

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## 基础镜像选择

| 镜像 | 特性 | 检查项 |
|---|---|---|
| Distroless | 标准运行时不含 shell/package manager | Debug 变体、库和应用依赖不同 |
| Alpine | 小型基于 musl 的发行版 | glibc 兼容性、维护生命周期、实际摘要 |
| Chainguard | 不同的最小运行时和 dev 变体 | 不要假定运行时镜像包含 shell/pip |
| Ubuntu/Debian | 更广泛的包/工具选择 | 单靠大小不能决定漏洞数量 |
| Scratch | 空的基础镜像 | 复制的二进制文件、CA 文件和应用依赖仍可能存在漏洞 |

不要将旧的 Go 1.22/Alpine 3.19 示例误认为当前受支持的基线。更新时检查维护状态、OS EOL、CPU ABI、摘要和扫描发现。Distroless 从构建阶段获取二进制文件；遵循 Chainguard Python 模式，在 dev 阶段准备依赖/venv，并将它们复制到运行时。本文件未执行 Dockerfile 构建或比较漏洞数量。

### 最小基础镜像构建示例

[完整构建上下文](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images)包含打印固定消息的 Go/Python 程序和三个 Dockerfile。选择一个 Dockerfile 以比较这些模式；它们不是 web-server 示例。已检查基础索引摘要和 amd64/arm64 可用性，但未执行容器构建/运行时。

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

应用已使用 Go 1.27.1 和 Python 3.12 直接运行，且三个 Dockerfile 均通过了 HIGH/CRITICAL 配置检查。此 fixture 中的 Python requirements 为空。添加真实依赖时需要锁定文件/哈希、构建器/运行时 ABI 检查和漏洞扫描。请单独管理 Alpine apk 存储库和基础摘要更新。

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## 镜像注册表最佳实践

- 私有镜像需要获批准的拉取 identity。ECR kubelet/node/Fargate 执行角色不同于应用程序 Pod Identity。
- 外部注册表可以使用有效的 kubernetes.io/dockerconfigjson Secret 和 ServiceAccount imagePullSecrets。Base64 不是加密。
- imagePullPolicy:Always 控制注册表引用检查，而非签名验证。请分别配置摘要固定、准入验证和扫描门禁。
- 仅禁止 latest 的模式可能遗漏省略 tag 的镜像以及 init/ephemeral 镜像。使用上面的注册表/摘要策略测试范围。
- 有意公开的镜像允许匿名拉取并非天生漏洞。应区分机密性、推送权限、溯源、速率限制和许可证要求。
- 确保保留/垃圾回收不会删除活跃摘要或所需的签名/证明 referrer；测试恢复过程。

<span id="complete-image-security-pipeline"></span>

## CI/CD 流水线集成

在应用程序存储库中将其放置于 .github/workflows/secure-build.yaml 前，请审查[完整 workflow 文件](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml)。真实的 Dockerfile 和构建上下文是先决条件。其预期属性如下：

1. PR 扫描使用没有注册表发布/OIDC 签名权限的只读 job。
2. main-push 发布 job 只构建一次并扫描该本地镜像。
3. 它在不重新构建的情况下推送，并捕获 RepoDigest。
4. 签名、验证、SBOM 证明和溯源使用相同的摘要。
5. Actions 固定到经过审查的 commit SHA；独立的 artifact-storage record 已禁用。

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

配置 GHCR package 权限、Actions OIDC、attestation-plan 支持和网络访问。已检查 workflow YAML/action input 和 shell 语法，但未执行 GitHub runner 构建/推送/签名/证明 workflow。不要忽略 SBOM/签名失败，也不要将空摘要继续传递下去。如果添加 SARIF 上传，请单独处理 fork-PR security-events 权限以及扫描失败后保留结果的问题。

## 已执行的检查和限制

- Trivy 0.74：两个合成 Secret case 和两个 Dockerfile 非 root 检查。未进行实际 CVE 数据库或远程镜像扫描。
- Cosign 3.1.3：有效/篡改的合成本地 key/blob 验证。在该私有 fixture 中省略透明度，并不代表生产注册表/OIDC 验证的证据。
- Kyverno 1.19.1：六个 CEL 注册表/摘要 object case，包括 init/ephemeral container，以及两个固定的 CRD schema。未进行实时准入或网络签名验证。
- 已运行 Trivy Operator/Connaisseur Helm 渲染、合成 ECR API-model/JMESPath fixture、CloudFormation lint 和 actionlint。未执行 AWS 资源、通知或注册表推送。

<span id="summary"></span>
<span id="recommendations"></span>

## 参考资料

- [Trivy 发行版](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Trivy 文档](https://aquasecurity.github.io/trivy/)
- [Trivy Operator Chart](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [ECR 扫描](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Inspector 事件架构](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [EventBridge target 授权](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [SNS KMS 兼容性](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Sigstore 验证](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Kyverno CEL 迁移](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Connaisseur namespaced validation](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [SLSA 要求](https://slsa.dev/spec/v1.2/build-requirements)
- [GitHub attest action](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
