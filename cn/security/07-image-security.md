# 容器镜像安全

> **最后更新**：October 16, 2026
> **验证基线**：Trivy 0.76.0、Trivy Operator 0.35.0/chart 0.37.0、Cosign 3.1.3、Kyverno 1.19.1、Connaisseur 3.13.0/chart 2.13.0。这些是 CLI/配置基线，不代表已在所有 Kubernetes 版本上完成部署测试。

镜像安全首先要确认**构建、扫描和部署的是同一个制品**。扫描可识别已知漏洞和配置问题；签名可将签名者与摘要关联起来。但两者都不能保证应用安全。

## 目录

1. [镜像扫描概览](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Amazon ECR 镜像扫描](#amazon-ecr-image-scanning)
4. [使用 Cosign/Sigstore 进行镜像签名](#image-signing-with-cosignsigstore)
5. [准入控制中的镜像验证](#image-verification-in-admission-control)
6. [供应链安全](#supply-chain-security)
7. [基础镜像选择](#base-image-selection)
8. [镜像仓库最佳实践](#image-registry-best-practices)
9. [CI/CD 流水线集成](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## 镜像扫描概览 {#image-scanning-overview}

左移安全检查会在 IDE、PR 和构建阶段引入检查。发布后仍会出现新的 CVE，因此仍需单独执行仓库重新扫描和运行时检测。

| 目标 | 检查项 | 工具示例 |
|---|---|---|
| OS/语言包 | 识别、数据库时效性、修复版本、VEX 决策 | Trivy、Grype |
| IaC/Dockerfile | 非 root 执行、权限、配置 | Trivy misconfig、Checkov |
| 密钥 | 镜像层或源代码中的凭据 | Trivy secret、TruffleHog |
| 许可证/SBOM | 组件和许可证检测覆盖范围 | Syft、Trivy |
| 运行时行为 | 实时系统调用、进程、网络活动 | Falco 等独立工具 |

流程为 `源代码检查 → 仅构建一次 → 扫描该制品 → 推送 → 对摘要签名/验证 → 准入检查 → 重新扫描`。组织应定义严重性门槛，并为例外指定负责人、理由和到期时间。

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy

### 安装与扫描

验证适用于相应操作系统/CPU 架构的官方发布包及其校验和。不要在 Linux ARM64 上安装 amd64 二进制文件，也不要使用已弃用的 apt-key 操作说明。在自动化流程中固定 CLI/action 版本。

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

`IMAGE_REF` 是有意设置的占位符，必须替换为真实摘要。使用 `misconfig`，不要使用 `--scanners config`。`--ignore-unfixed` 会隐藏尚无修复方案的漏洞，因此不要在默认门禁中不加区分地启用它。检查对仓库、漏洞/Java 数据库和检查包的网络/缓存要求。`trivy config` 没有 `--offline-scan` 选项。

### 配置与例外

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

这是镜像/文件系统扫描基线。不要添加不受支持的 vulnerability.type，也不要添加顶层忽略列表。通过 .trivyignore/受支持的忽略策略格式管理例外，并区分密钥例外和漏洞例外。示例 .trivyignore 不包含默认排除项。

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.37.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

Chart 0.37.0 部署的应用版本为 0.35.0。[values 文件](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml)明确设置了 ignoreUnfixed:false。报告是 Operator 生成的结果；不要将伪造的 CVE/软件包版本清单作为扫描证据。检查实际报告架构、被监视的命名空间、仓库凭据、扫描 Job 权限和资源。本次审计仅渲染了 chart。

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Amazon ECR 镜像扫描 {#amazon-ecr-image-scanning}

| 属性 | Basic | Enhanced |
|---|---|---|
| 当前引擎 | AWS 原生扫描器 | Amazon Inspector |
| 覆盖范围 | OS 软件包漏洞 | OS 和受支持的语言软件包 |
| 频率 | 手动或推送时扫描 | 推送时扫描或持续扫描 |
| 结果 | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| 事件 | ECR Basic 扫描完成事件 | Inspector2 扫描/发现事件 |

要区分旧版 Clair 介绍与当前的 Basic 引擎。切换扫描模式可能会改变已有结果的可见性。Enhanced 的覆盖范围取决于仓库筛选条件、重新扫描时长和受支持镜像的判定标准；并非所有镜像都会被永久扫描。归档镜像必须先恢复，才能进行扫描。

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

配置命令会写入仓库设置，本次审计未执行该命令。使用 DescribeImageScanFindings，不要依赖 DescribeImages 中的旧版 Basic 摘要。启用 ECR 扫描不会自动阻止存在漏洞的镜像被推送、拉取或部署。

### Inspector 警报与权限

使用 source aws.inspector2、detail-type Inspector2 Finding 以及 detail.severity/status/resources[].type 筛选 Enhanced 发现项。不要将其与 Basic ECR Image Scan 和 finding-severity-counts 混用。数值为零的字段仍然存在；exists:true 并不表示漏洞计数大于零。

[完整的 CloudFormation 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)将加密 SNS 主题连接到 EventBridge 执行角色。它要求存在一个同账户/Region 的对称客户管理 KMS 密钥，且密钥策略允许 IAM 委派；已批准的 SNS 消费者订阅需单独配置。当前的 EventBridge 支持为 SNS 目标配置执行角色。不要将事件总线的 KMS SourceArn/SourceAccount 条件复制到直接由服务主体向加密 SNS 发送消息的路径中。该模板通过了 cfn-lint；实际投递、KMS 授权和重试情况仍需在部署环境中测试。

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>

<span id="image-signing-with-cosignsigstore"></span>

## 使用 Cosign/Sigstore 进行镜像签名

### 签名顺序与信任

对于常见的仓库流程，应先推送镜像、获取其摘要，再对该摘要签名。验证受信任的密钥或精确的 OIDC issuer/identity、摘要以及所需的透明日志/时间戳证据。单独的签名无法证明签名者已获批准，也无法证明镜像不存在漏洞。

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

不要提交私钥。通过凭据管理器/KMS 或同等控制措施管理密钥生命周期。无密钥 GitHub Actions 使用 id-token:write 和 Actions OIDC 环境。GITHUB_TOKEN 是仓库/API 凭据，不是 OIDC ID token 本身。

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

将 identity 替换为获批准的工作流。--certificate-identity-regexp 接受正则表达式，而不是 glob。优先使用精确 identity 或带锚点的正则表达式，避免使用 `https://github.com/org/repo/*` 这类宽松表达式。检查 Cosign 3 的 bundle/OCI referrer 与下游验证器的兼容性。

<span id="kyverno-imageverify"></span>

## 准入控制中的镜像验证 {#image-verification-in-admission-control}

Kyverno 1.19.1 会警告 ClusterPolicy 已弃用。新示例使用 policies.kyverno.io/v1 的 ValidatingPolicy 和 ImageValidatingPolicy。旧版 verifyImages 规则不是新策略类型的名称。

### 仓库与摘要策略

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

此策略涵盖常规容器、init 容器和临时容器，包括对 pods/ephemeralcontainers 的更新。将 example-org 替换为获批准的仓库。摘要格式可以固定内容地址，但不会执行签名验证或漏洞验证。

### 工作流签名策略

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

不在 matchImageReferences 范围内的镜像可能会跳过镜像验证，因此还应同时应用仓库策略。设计命名空间例外、PolicyException 访问权限、webhook 可用性/超时、仓库凭据和 TLS 信任，然后测试实际准入请求。签名策略已对照 CRD 架构进行检查；这并不代表已在实时环境中验证 registry/Fulcio/Rekor。生产示例不会禁用透明日志检查。

<span id="connaisseur"></span>

### Connaisseur 替代方案：旧版签名路径

**Connaisseur 3.13.0 不支持使用默认 Cosign 3 bundles**。它使用 cosign/v2 验证路径，以及旧版签名标签和 SimpleSigning 负载。请使用独立的兼容性签名生成器。[旧版签名脚本](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh)明确设置 Cosign 3.1.3 的 `--new-bundle-format=false --registry-referrers-mode=legacy`，同时保留透明日志上传/验证。配套签名配置明确为旧版验证器的日志格式选择 Rekor v1。请提供真实的获批准密钥和摘要。此路径独立于 secure-build.yaml 的默认 bundle 格式；不要将该工作流的默认输出直接传给 Connaisseur。旧版标志已弃用，因此应规划签名生成器/验证器的协调迁移。已检查 CLI 选项和双方的源格式约定；未执行仓库/签名集成。

Connaisseur 3.13.0/chart 2.13.0 是另一种选择。在 [values 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml)中，validators 和 policy 应置于 application 下，而 deny 是显式定义的静态 validator。其中包含的公钥是合成测试密钥，必须替换为真实的信任密钥。

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.13.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

此示例使用 namespaced-validation validate 模式，并且只检查带有该标签的命名空间。能够更改命名空间标签的身份可能绕过此选择机制，因此应对相关权限进行治理。Kyverno 和 Connaisseur 是替代方案，而不是必须同时安装的组件。Helm 渲染不能替代真实的签名允许/拒绝测试。

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## 供应链安全 {#supply-chain-security}

### SBOM 与证明

```bash
syft "$IMAGE_REF" -o spdx-json=sbom.spdx.json
trivy image --format spdx-json --output sbom.spdx.json "$IMAGE_REF"
trivy sbom sbom.spdx.json
# Alternatively, Grype:
# grype sbom:sbom.spdx.json
cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
cosign verify-attestation --type spdxjson   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' "$IMAGE_REF"
```

Syft/Trivy 生成命令是可选方案。SBOM 会列出工具检测到的内容；但无法保证完整性和安全性。cosign attach sbom 已弃用，普通附件与签名证明并不相同。应一并验证谓词内容、主体摘要、签名者、验证时间和策略。

### SLSA 来源证明

来源证明记录构建输入、构建器和制品之间的关系。调用生成 action 并不会自动满足 SLSA Build Level 3。应分别评估相关的隔离要求、防止来源证明伪造的要求以及源代码策略要求。

对于现有的 slsa-github-generator 可复用工作流，请检查其支持的工具链和调用方要求。下面的新工作流使用当前版本的 actions/attest。attest-build-provenance 的版本 4 是一个封装；新实现应改用 actions/attest。请检查公开和私有仓库在 GitHub 计划支持和 Sigstore 信任根方面的差异。

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## 基础镜像选择 {#base-image-selection}

| 镜像 | 特征 | 检查项 |
|---|---|---|
| Distroless | 标准运行时不包含 shell/package manager | 调试变体、库和应用依赖可能不同 |
| Alpine | 基于 musl 的小型发行版 | glibc 兼容性、维护期限、实际摘要 |
| Chainguard | 精简运行时和开发变体各不相同 | 不要假设运行时镜像包含 shell/pip |
| Ubuntu/Debian | 软件包/工具选择范围更广 | 镜像大小不能单独决定漏洞数量 |
| Scratch | 空基础镜像 | 复制进去的二进制文件、CA 文件和应用依赖仍可能存在漏洞 |

不要将旧版 Go 1.22/Alpine 3.19 示例误认为当前受支持的基线。更新时应检查维护状态、OS EOL、CPU ABI、摘要和扫描结果。Distroless 从构建阶段获取二进制文件；使用 Chainguard Python 模式，在 dev 阶段准备依赖/venv，再复制到运行时镜像中。本文未执行 Dockerfile 构建，也未比较漏洞数量。

### 精简基础镜像构建示例

[完整构建上下文](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images)包含 Go/Python 程序，它们会输出固定消息，以及三个 Dockerfile。选择一个 Dockerfile 来比较这些模式；它们不是 Web 服务器示例。已检查基础镜像索引摘要和 amd64/arm64 的可用性，但未执行容器构建/运行。

**Dockerfile.distroless**

```dockerfile
FROM golang:1.27.2@sha256:820153096fda4de6ac1b7194d12e416b7dd8f4e9a33d17e0345b111b945162d8 AS builder
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

这些应用分别使用 Go 1.27.1 和 Python 3.12 直接运行，三个 Dockerfile 均通过了 HIGH/CRITICAL 配置检查。本测试样例中的 Python requirements 为空。添加实际依赖需要锁定版本/哈希、检查构建器/运行时 ABI，并执行漏洞扫描。应单独管理 Alpine apk 软件源和基础镜像摘要更新。

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## 镜像仓库最佳实践 {#image-registry-best-practices}

- 私有镜像需要获批准的拉取身份。ECR kubelet/node/Fargate 执行角色与应用程序 Pod Identity 不同。
- 外部仓库可以使用有效的 kubernetes.io/dockerconfigjson Secret 和 ServiceAccount imagePullSecrets。Base64 并非加密。
- imagePullPolicy:Always 控制的是对仓库引用的检查，不是签名验证。应单独配置摘要固定、准入验证和扫描门禁。
- 仅禁止 latest 的模式可能会漏掉未指定标签的镜像以及 init/临时容器。使用上面的仓库/摘要策略测试覆盖范围。
- 有意公开的镜像允许匿名拉取，本身并不构成漏洞。应分别考虑机密性、推送权限、来源证明、速率限制和许可要求。
- 确保保留策略/垃圾回收不会删除正在使用的摘要或所需的签名/证明 referrer；并测试恢复流程。

<span id="complete-image-security-pipeline"></span>

<span id="cicd-pipeline-integration"></span>

## CI/CD 流水线集成

将[完整工作流文件](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml)放入应用仓库的 .github/workflows/secure-build.yaml 之前，请先进行审查。实际的 Dockerfile 和构建上下文是前提条件。其设计目标如下：

1. PR 扫描使用只读 Job，不执行仓库发布/OIDC 签名。
2. main 分支推送的发布 Job 只构建一次，并扫描该本地镜像。
3. 推送时不重新构建，并捕获 RepoDigest。
4. 签名、验证、SBOM 证明和来源证明都使用同一摘要。
5. Actions 固定到经过审查的 commit SHA；禁用单独的制品存储记录。

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
          version: v0.76.0
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
          version: v0.76.0
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

配置 GHCR 软件包权限、Actions OIDC、证明计划支持和网络访问。已检查工作流 YAML/action 输入和 shell 语法，但未在 GitHub runner 上执行构建/推送/签名/证明工作流。不要忽略 SBOM/签名失败，也不要将空摘要传递给后续步骤。如果添加 SARIF 上传，应单独处理 fork PR 的 security-events 权限，并确保扫描失败后仍能保留结果。

## 已执行的检查与限制

- Trivy 0.76：两个合成密钥案例和两个 Dockerfile 非 root 检查。未使用真实 CVE 数据库，也未扫描远程镜像。
- Cosign 3.1.3：对有效/已篡改的合成私钥/数据块进行验证。该私有测试样例中未启用透明日志，并不代表生产环境中的仓库/OIDC 验证。
- Kyverno 1.19.1：六个 CEL 仓库/摘要对象案例（包括 init/临时容器），以及两个固定版本的 CRD 架构。未执行实时准入或网络签名验证。
- 已运行 Trivy Operator/Connaisseur Helm 渲染、合成 ECR API 模型/JMESPath 测试样例、CloudFormation lint 和 actionlint。未创建 AWS 资源、发送通知或推送镜像。

<span id="summary"></span>
<span id="recommendations"></span>

## 参考资料

- [Trivy 发布版本](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0)
- [Trivy 文档](https://aquasecurity.github.io/trivy/)
- [Trivy Operator chart](https://github.com/aquasecurity/trivy-operator/tree/v0.35.0/deploy/helm)
- [ECR 扫描](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Inspector 事件架构](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [EventBridge 目标授权](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [SNS KMS 兼容性](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Sigstore 验证](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Kyverno CEL 迁移](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Connaisseur 命名空间范围验证](https://github.com/sse-secure-systems/connaisseur/blob/v3.13.0/docs/features/namespaced_validation.md)
- [SLSA 要求](https://slsa.dev/spec/v1.2/build-requirements)
- [GitHub attest action](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
