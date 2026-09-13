# 容器镜像安全

> **最后更新**：2026 年 9 月 13 日
> **验证基线**：Trivy 0.74.0、Trivy Operator 0.34.0/chart 0.36.0、Cosign 3.1.3、Kyverno 1.19.1、Connaisseur 3.12.0/chart 2.12.0。这些是 CLI/配置基线，不代表已对全部 Kubernetes 版本进行部署测试。

镜像安全首先确认**构建、扫描和部署的是同一制品**。扫描识别已知漏洞和配置问题；签名将签名者与摘要关联。两者都不保证应用安全。

## 目录

1. [镜像扫描概述](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Amazon ECR 镜像扫描](#amazon-ecr-image-scanning)
4. [使用 Cosign/Sigstore 签名镜像](#image-signing-with-cosignsigstore)
5. [准入控制中的镜像验证](#image-verification-in-admission-control)
6. [供应链安全](#supply-chain-security)
7. [基础镜像选择](#base-image-selection)
8. [镜像仓库最佳实践](#image-registry-best-practices)
9. [CI/CD 流水线集成](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## 镜像扫描概述 {#image-scanning-overview}

安全左移在 IDE、PR 和构建中引入检查。发布后会出现新 CVE，因此仓库重新扫描和运行时检测仍是独立要求。

| 目标 | 检查 | 工具示例 |
|---|---|---|
| 操作系统/语言软件包 | 识别、数据库年龄、修复版本、VEX 决策 | Trivy、Grype |
| IaC/Dockerfile | 非 root 执行、权限、配置 | Trivy misconfig、Checkov |
| 密钥 | 镜像层或源码中的凭证 | Trivy secret、TruffleHog |
| 许可证/SBOM | 组件和许可证检测覆盖 | Syft、Trivy |
| 运行时行为 | 实时系统调用、进程、网络 | Falco 等独立工具 |

流程为 `source checks → build once → scan that artifact → push → sign/verify digest → admission checks → rescan`。组织定义严重性门禁，并为例外指定所有者、理由和到期。

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy {#trivy}

### 安装和扫描

验证对应操作系统/CPU 架构的官方发布包和校验和。不要在 Linux ARM64 安装 amd64 二进制，也不要使用退役的 apt-key 说明。自动化中固定 CLI/action 版本。

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

`IMAGE_REF` 是需真实摘要替换的有意占位符。使用 `misconfig`，不是 `--scanners config`。`--ignore-unfixed` 隐藏尚无修复的漏洞，因此默认门禁不要无差别启用。检查仓库、漏洞/Java 数据库和检查包的网络/缓存要求。`trivy config` 没有 `--offline-scan` 选项。

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

这是镜像/文件系统扫描基线。不要添加不支持的 vulnerability.type 或顶层忽略列表。通过 .trivyignore/受支持 ignore-policy 格式管理例外，区分密钥与漏洞例外。示例 .trivyignore 没有默认排除项。

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

Chart 0.36.0 部署应用 0.34.0。[Values 文件](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml)显式设置 ignoreUnfixed:false。报告是 Operator 生成结果；不要应用虚构 CVE/软件包版本清单作为扫描证据。检查实际报告模式、监视命名空间、仓库凭证、扫描 Job 权限和资源。本审计仅渲染 chart。

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Amazon ECR 镜像扫描 {#amazon-ecr-image-scanning}

| 属性 | Basic | Enhanced |
|---|---|---|
| 当前引擎 | AWS 原生扫描器 | Amazon Inspector |
| 覆盖 | 操作系统软件包漏洞 | 操作系统和受支持语言软件包 |
| 频率 | 手动或推送时扫描 | 推送时或持续扫描 |
| 结果 | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| 事件 | ECR Basic 扫描完成 | Inspector2 扫描/发现事件 |

区分旧 Clair 描述和当前 Basic 引擎。切换扫描模式可改变已有结果可见性。Enhanced 覆盖取决于仓库过滤器、重扫时长和支持镜像条件；不是每个镜像永久扫描。归档镜像必须先还原才能扫描。

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

配置命令写入仓库设置，本审计未执行。使用 DescribeImageScanFindings，不依赖 DescribeImages 中旧 Basic 摘要。启用 ECR 扫描不会自动阻止漏洞镜像推送、拉取或部署。

### Inspector 警报和权限

使用 source aws.inspector2、detail-type Inspector2 Finding 和 detail.severity/status/resources[].type 过滤 Enhanced 发现。不要与 Basic ECR Image Scan 及 finding-severity-counts 混用。数值为零的字段仍存在；exists:true 不表示漏洞数为正。

[完整 CloudFormation 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)将加密 SNS 主题连接到 EventBridge 执行角色。要求现有同账户/区域对称客户托管 KMS 密钥，其策略允许 IAM 委托；获准 SNS 使用方订阅独立配置。当前 EventBridge 支持 SNS 目标执行角色。不要将事件总线 KMS SourceArn/SourceAccount 条件复制到服务主体直接访问加密 SNS 的路径。模板通过 cfn-lint；实际交付、KMS 授权和重试需要部署环境测试。

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>



## 使用 Cosign/Sigstore 签名镜像 {#image-signing-with-cosignsigstore}

### 签名顺序和信任

常规仓库流程中，先推送镜像、获取摘要，再签署该摘要。验证可信密钥或确切 OIDC 签发者/身份、摘要和必需透明性/时间戳证据。仅签名不确立签名者已获准，也不证明无漏洞。

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

不要提交私钥。通过凭证管理器/KMS 或等效控制管理生命周期。无密钥 GitHub Actions 使用 id-token:write 和 Actions OIDC 环境。GITHUB_TOKEN 是仓库/API 凭证，不是 OIDC ID 令牌本身。

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

将身份替换为获准工作流。--certificate-identity-regexp 接受正则表达式，不是 glob。优先精确身份或锚定正则，不使用 `https://github.com/org/repo/*` 等宽松表达式。检查 Cosign 3 bundle/OCI referrer 与下游验证器兼容性。

<span id="kyverno-imageverify"></span>

## 准入控制中的镜像验证 {#image-verification-in-admission-control}

Kyverno 1.19.1 警告 ClusterPolicy 已弃用。新示例使用 policies.kyverno.io/v1 ValidatingPolicy 和 ImageValidatingPolicy。旧 verifyImages 规则不是新策略种类名称。

### 仓库和摘要策略

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

覆盖普通、初始化和临时容器，包括 pods/ephemeralcontainers 更新。将 example-org 替换为获准仓库。摘要格式固定内容地址；不执行签名或漏洞验证。

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

matchImageReferences 外的镜像可能被镜像验证跳过，因此也应用仓库策略。设计命名空间例外、PolicyException 访问、webhook 可用性/超时、仓库凭证和 TLS 信任，再测试实际准入请求。签名策略已对照 CRD 模式检查；不是实际仓库/Fulcio/Rekor 验证证据。生产示例不禁用透明性检查。

<span id="connaisseur"></span>

### Connaisseur 替代方案——旧签名路径

**Connaisseur 3.12.0 无法使用默认 Cosign 3 bundle。** 它采用 cosign/v2 验证路径，使用旧签名标签和 SimpleSigning 载荷。使用独立兼容生成方。[旧签名脚本](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh)显式设置 Cosign 3.1.3 `--new-bundle-format=false --registry-referrers-mode=legacy`，同时保留透明性上传/验证。配套签名配置为旧验证器日志格式显式选择 Rekor v1。提供真实获准密钥和摘要。此路径独立于 secure-build.yaml 默认 bundle 格式；不要将该工作流默认输出直接交给 Connaisseur。旧标志已弃用，应规划协调的生成方/验证器迁移。CLI 选项及两端源码约定已检查；未执行仓库/签名集成。

Connaisseur 3.12.0/chart 2.12.0 是另一选项。[Values 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml)中，validators 和 policy 位于 application 下，deny 是显式定义的静态验证器。所含公钥是合成测试密钥，必须替换为真实信任密钥。

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

示例使用 namespaced-validation validate 模式，仅检查带该标签的命名空间。有权改变命名空间标签的身份可绕过选择，因此需治理权限。Kyverno 和 Connaisseur 是备选，不要求同时安装。Helm 渲染不替代真实签名允许/拒绝测试。

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## 供应链安全 {#supply-chain-security}

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

Syft/Trivy 生成命令是备选。SBOM 清点工具检测到的内容；不保证完整或安全。cosign attach sbom 已弃用，普通附件不同于签名证明。一起验证 predicate 内容、subject 摘要、签名者、验证时间和策略。

### SLSA 来源证明

来源证明记录构建输入、构建器和制品之间关系。调用生成 action 不自动满足 SLSA Build Level 3。单独评估相关隔离、抗来源证明伪造和源策略要求。

现有 slsa-github-generator 可复用工作流应检查受支持工具链和调用方要求。下方新工作流使用当前 actions/attest。attest-build-provenance 第 4 版是包装器；新实现被指引使用 actions/attest。检查公共与私有仓库的 GitHub 计划及 Sigstore 信任根差异。

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## 基础镜像选择 {#base-image-selection}

| 镜像 | 特点 | 检查 |
|---|---|---|
| Distroless | 标准运行时不含 shell/软件包管理器 | 调试变体、库和应用依赖不同 |
| Alpine | 基于 musl 的小型发行版 | glibc 兼容性、维护寿命、实际摘要 |
| Chainguard | 独立最小运行时和开发变体 | 不要假定运行时镜像包含 shell/pip |
| Ubuntu/Debian | 更广软件包/工具选择 | 仅大小不决定漏洞数 |
| Scratch | 空基础镜像 | 复制的二进制、CA 文件和应用依赖仍可能有漏洞 |

不要将旧 Go 1.22/Alpine 3.19 示例误当当前受支持基线。更新时检查维护、操作系统生命周期、CPU ABI、摘要和扫描发现。Distroless 从构建阶段接收二进制；遵循 Chainguard Python 模式，在开发阶段准备依赖/venv，再复制到运行时。本文未执行 Dockerfile 构建或比较漏洞数。

### 最小基础镜像构建示例

[完整构建上下文](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images)包含打印固定消息的 Go/Python 程序和三个 Dockerfile。选择 Dockerfile 比较模式；它们不是 Web 服务器示例。基础索引摘要和 amd64/arm64 可用性已检查，但未执行容器构建/运行。

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

应用直接使用 Go 1.27.1 和 Python 3.12 运行，三个 Dockerfile 均通过 HIGH/CRITICAL 配置检查。此测试样例 Python requirements 为空。添加真实依赖需要锁定/哈希、构建器/运行时 ABI 检查和漏洞扫描。单独管理 Alpine apk 仓库及基础摘要更新。

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## 镜像仓库最佳实践 {#image-registry-best-practices}

- 私有镜像需要获准拉取身份。ECR kubelet/节点/Fargate 执行角色不同于应用 Pod Identity。
- 外部仓库可使用有效 kubernetes.io/dockerconfigjson Secret 和 ServiceAccount imagePullSecrets。Base64 不是加密。
- imagePullPolicy:Always 控制仓库引用检查，不验证签名。单独配置摘要固定、准入验证和扫描门禁。
- 仅禁止 latest 的模式可能遗漏省略标签及初始化/临时镜像。用上方仓库/摘要策略测试范围。
- 有意公开镜像的匿名拉取本身不是漏洞。区分保密性、推送权限、来源、限速和许可要求。
- 确保保留/垃圾回收不移除活动摘要或所需签名/证明 referrer；测试恢复。

<span id="complete-image-security-pipeline"></span>



## CI/CD 流水线集成 {#cicd-pipeline-integration}

将[完整工作流文件](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml)放到应用仓库 .github/workflows/secure-build.yaml 前先审核。真实 Dockerfile 和构建上下文是前提。预期属性如下：

1. PR 扫描使用只读任务，不发布仓库镜像或执行 OIDC 签名。
2. main 推送发布任务只构建一次，并扫描该本地镜像。
3. 不重建就推送，并捕获 RepoDigest。
4. 签名、验证、SBOM 证明和来源证明使用同一摘要。
5. Action 固定到已审核提交 SHA；禁用独立制品存储记录。

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

配置 GHCR 包权限、Actions OIDC、证明计划支持和网络访问。工作流 YAML/action 输入及 shell 语法已检查，但未执行 GitHub runner 构建/推送/签名/证明工作流。不要忽略 SBOM/签名失败或向下游传空摘要。添加 SARIF 上传时，单独处理 fork PR 的 security-events 权限，以及扫描失败后保留结果。

## 已执行检查和限制

- Trivy 0.74：两个合成密钥用例和两个 Dockerfile 非 root 检查。未实际扫描 CVE 数据库或远程镜像。
- Cosign 3.1.3：有效/被篡改的合成本地密钥/blob 验证。私有测试样例省略透明性，不是生产仓库/OIDC 验证证据。
- Kyverno 1.19.1：六个 CEL 仓库/摘要对象用例，含初始化/临时容器，另加两个固定 CRD 模式。无实际准入或网络签名验证。
- 执行了 Trivy Operator/Connaisseur Helm 渲染、合成 ECR API 模型/JMESPath 样例、CloudFormation lint 和 actionlint。未执行 AWS 资源、通知或仓库推送。

<span id="summary"></span>
<span id="recommendations"></span>

## 参考资料

- [Trivy 发布](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Trivy 文档](https://aquasecurity.github.io/trivy/)
- [Trivy Operator chart](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [ECR 扫描](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Inspector 事件模式](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [EventBridge 目标授权](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [SNS KMS 兼容性](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Sigstore 验证](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Kyverno CEL 迁移](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Connaisseur 命名空间验证](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [SLSA 要求](https://slsa.dev/spec/v1.2/build-requirements)
- [GitHub attest action](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
