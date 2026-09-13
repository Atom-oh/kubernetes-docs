# Container Image Security

> **Last Updated**: September 13, 2026
> **Validation baseline**: Trivy 0.74.0, Trivy Operator 0.34.0/chart 0.36.0, Cosign 3.1.3, Kyverno 1.19.1, Connaisseur 3.12.0/chart 2.12.0. These are CLI/configuration baselines, not a claim of deployment testing across all Kubernetes versions.

Image security starts by confirming that **the built, scanned, and deployed artifact is the same**. Scanning identifies known vulnerabilities and configuration issues; signatures connect a signer to a digest. Neither guarantees application safety.

## Table of Contents

1. [Image Scanning Overview](#image-scanning-overview)
2. [Trivy](#trivy)
3. [Amazon ECR Image Scanning](#amazon-ecr-image-scanning)
4. [Image Signing with Cosign/Sigstore](#image-signing-with-cosignsigstore)
5. [Image Verification in Admission Control](#image-verification-in-admission-control)
6. [Supply Chain Security](#supply-chain-security)
7. [Base Image Selection](#base-image-selection)
8. [Image Registry Best Practices](#image-registry-best-practices)
9. [CI/CD Pipeline Integration](#cicd-pipeline-integration)

<span id="shift-left-security"></span>
<span id="scan-targets"></span>

## Image Scanning Overview

Shift-left introduces checks in the IDE, PR, and build. New CVEs appear after release, so registry rescanning and runtime detection remain separate requirements.

| Target | Check | Example tools |
|---|---|---|
| OS/language packages | Identification, database age, fixed versions, VEX decisions | Trivy, Grype |
| IaC/Dockerfiles | Non-root execution, permissions, configuration | Trivy misconfig, Checkov |
| Secrets | Credentials in image layers or source | Trivy secret, TruffleHog |
| Licenses/SBOM | Component and license detection coverage | Syft, Trivy |
| Runtime behavior | Live syscalls, processes, networking | Separate tools such as Falco |

The flow is `source checks → build once → scan that artifact → push → sign/verify digest → admission checks → rescan`. Organizations define severity gates and give exceptions an owner, rationale, and expiry.

<span id="trivy-installation"></span>
<span id="image-scanning"></span>
<span id="filesystem-scanning"></span>
<span id="trivy-configuration-file"></span>
<span id="trivy-operator-kubernetes-integration"></span>

## Trivy

### Installation and scanning

Verify the official release package for the operating system/CPU architecture and its checksum. Do not install an amd64 binary on Linux ARM64 or use retired apt-key instructions. Pin CLI/action versions in automation.

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

`IMAGE_REF` is an intentional placeholder requiring a real digest. Use `misconfig`, not `--scanners config`. `--ignore-unfixed` hides vulnerabilities without fixes, so do not enable it indiscriminately in the default gate. Check network/cache requirements for registries, vulnerability/Java databases, and check bundles. `trivy config` has no `--offline-scan` option.

### Configuration and exceptions

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

This is an image/filesystem scanning baseline. Do not add unsupported vulnerability.type or a top-level ignore list. Manage exceptions through .trivyignore/supported ignore-policy formats, distinguishing secret and vulnerability exceptions. The example .trivyignore has no default exclusions.

<span id="trivy-overview"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

Chart 0.36.0 deploys application 0.34.0. The [values file](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml) explicitly sets ignoreUnfixed:false. Reports are operator-generated results; do not apply a fabricated CVE/package-version manifest as scan evidence. Check the actual report schema, watched namespaces, registry credentials, scan-Job privileges, and resources. This audit rendered the chart only.

<span id="basic-scanning-vs-enhanced-scanning"></span>
<span id="enabling-enhanced-scanning"></span>
<span id="retrieving-scan-results"></span>
<span id="notifications-via-eventbridge"></span>

## Amazon ECR Image Scanning

| Property | Basic | Enhanced |
|---|---|---|
| Current engine | AWS native scanner | Amazon Inspector |
| Coverage | OS package vulnerabilities | OS and supported language packages |
| Frequency | Manual or scan-on-push | Scan-on-push or continuous |
| Results | imageScanFindings.findings | imageScanFindings.enhancedFindings |
| Events | ECR basic-scan completion | Inspector2 scan/finding events |

Distinguish older Clair descriptions from the current Basic engine. Switching scanning modes can change the visibility of established results. Enhanced coverage depends on repository filters, rescan duration, and supported-image criteria; not every image is scanned forever. Archived images must be restored before scanning.

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced results. For Basic, query findings instead of enhancedFindings.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

The configuration command writes registry settings and was not executed by this audit. Use DescribeImageScanFindings instead of relying on the legacy Basic summary in DescribeImages. Enabling ECR scanning does not automatically block vulnerable images from being pushed, pulled, or deployed.

### Inspector alerts and permissions

Filter Enhanced findings using source aws.inspector2, detail-type Inspector2 Finding, and detail.severity/status/resources[].type. Do not mix this with Basic ECR Image Scan and finding-severity-counts. A field whose numeric value is zero still exists; exists:true does not mean a positive vulnerability count.

The [complete CloudFormation example](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml) connects an encrypted SNS topic to an EventBridge execution role. It requires an existing same-account/Region symmetric customer-managed KMS key whose policy permits IAM delegation; approved SNS consumer subscriptions are separate. Current EventBridge supports execution roles for SNS targets. Do not copy event-bus KMS SourceArn/SourceAccount conditions into the direct service-principal-to-encrypted-SNS path. The template passed cfn-lint; actual delivery, KMS authorization, and retries require deployment-environment testing.

<span id="cosign-overview"></span>
<span id="cosign-installation"></span>
<span id="key-based-signing"></span>
<span id="keyless-signing-oidc-based"></span>
<span id="github-actions-integration"></span>

## Image Signing with Cosign/Sigstore

### Signing order and trust

For the usual registry flow, push the image, obtain its digest, and sign that digest. Verify a trusted key or exact OIDC issuer/identity, the digest, and required transparency/timestamp evidence. A signature alone does not establish an approved signer or absence of vulnerabilities.

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

Do not commit private keys. Manage their lifecycle through credential managers/KMS or equivalent controls. Keyless GitHub Actions uses id-token:write and the Actions OIDC environment. GITHUB_TOKEN is a registry/API credential, not the OIDC ID token itself.

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

Replace the identity with the approved workflow. --certificate-identity-regexp accepts a regular expression, not a glob. Prefer an exact identity or anchored regexp over permissive expressions such as https://github.com/org/repo/*. Check Cosign 3 bundle/OCI-referrer compatibility with downstream verifiers.

<span id="kyverno-imageverify"></span>

## Image Verification in Admission Control

Kyverno 1.19.1 warns that ClusterPolicy is deprecated. New examples use policies.kyverno.io/v1 ValidatingPolicy and ImageValidatingPolicy. The legacy verifyImages rule is not the name of the new policy kind.

### Registry and digest policy

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

This covers ordinary, init, and ephemeral containers, including pods/ephemeralcontainers updates. Replace example-org with approved repositories. A digest format pins a content address; it does not perform signature or vulnerability verification.

### Workflow signature policy

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

Images outside matchImageReferences can be skipped by image verification, so apply the registry policy as well. Design namespace exceptions, PolicyException access, webhook availability/timeouts, registry credentials, and TLS trust, then test actual admission requests. The signature policy was checked against the CRD schema; this is not evidence of live registry/Fulcio/Rekor verification. Production examples do not disable transparency checks.

<span id="connaisseur"></span>

### Connaisseur alternative

Connaisseur 3.12.0/chart 2.12.0 is another option. In the [values example](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml), validators and policy belong under application, and deny is an explicitly defined static validator. The included public key is a synthetic test key that must be replaced with the real trust key.

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

The example uses namespaced-validation validate mode and only checks namespaces with that label. An identity allowed to change namespace labels can bypass this selection, so govern those permissions. Kyverno and Connaisseur are alternatives, not a requirement to install both. Helm rendering does not replace real signature allow/deny testing.

<span id="sbom-software-bill-of-materials-generation"></span>
<span id="sbom-based-vulnerability-scanning"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## Supply Chain Security

### SBOM and attestations

```bash
syft "$IMAGE_REF" -o spdx-json=sbom.spdx.json
trivy image --format spdx-json --output sbom.spdx.json "$IMAGE_REF"
trivy sbom sbom.spdx.json
# Alternatively, Grype:
# grype sbom:sbom.spdx.json
cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
cosign verify-attestation --type spdxjson   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' "$IMAGE_REF"
```

The Syft/Trivy generation commands are alternatives. An SBOM inventories what the tool detects; completeness and safety are not guaranteed. cosign attach sbom is deprecated, and a plain attachment differs from a signed attestation. Validate predicate content, subject digest, signer, verification time, and policy together.

### SLSA provenance

Provenance records relationships among build inputs, builder, and artifact. Invoking a generation action does not automatically satisfy SLSA Build Level 3. Evaluate the relevant isolation, provenance-forgery resistance, and source-policy requirements separately.

For existing slsa-github-generator reusable workflows, check the supported toolchain and caller requirements. The new workflow below uses current actions/attest. Version 4 of attest-build-provenance is a wrapper; new implementations are directed to actions/attest. Check GitHub-plan and Sigstore-trust-root differences for public versus private repositories.

<span id="image-type-comparison"></span>
<span id="using-distroless-images"></span>
<span id="using-chainguard-images"></span>
<span id="alpine-security-hardening"></span>

## Base Image Selection

| Image | Characteristics | Check |
|---|---|---|
| Distroless | Standard runtimes omit shell/package manager | Debug variants, libraries, and app dependencies differ |
| Alpine | Small musl-based distribution | glibc compatibility, maintenance lifetime, actual digest |
| Chainguard | Distinct minimal runtime and dev variants | Do not assume runtime images contain shell/pip |
| Ubuntu/Debian | Broader package/tool selection | Size alone does not determine vulnerability count |
| Scratch | Empty base image | Copied binaries, CA files, and app dependencies may still be vulnerable |

Do not mistake the old Go 1.22/Alpine 3.19 examples for current supported baselines. Check maintenance, OS EOL, CPU ABI, digests, and scan findings when updating. Distroless receives binaries from a build stage; follow the Chainguard Python pattern of preparing dependencies/venv in a dev stage and copying them into the runtime. This document did not execute Dockerfile builds or compare vulnerability counts.

### Minimal base-image build examples

The [complete build context](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images) contains Go/Python programs that print a fixed message and three Dockerfiles. Select a Dockerfile to compare the patterns; these are not web-server examples. Base-index digests and amd64/arm64 availability were checked, but container builds/runtimes were not executed.

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

The apps ran directly with Go 1.27.1 and Python 3.12, and all three Dockerfiles passed HIGH/CRITICAL configuration checks. Python requirements are empty in this fixture. Adding real dependencies requires locks/hashes, builder/runtime ABI checks, and vulnerability scanning. Manage Alpine apk repositories and base-digest updates separately.

<span id="using-private-registries"></span>
<span id="image-pull-policies"></span>
<span id="immutable-tag-policy-kyverno"></span>

## Image Registry Best Practices

- Private images need approved pull identities. ECR kubelet/node/Fargate execution roles differ from application Pod Identity.
- External registries can use a valid kubernetes.io/dockerconfigjson Secret and ServiceAccount imagePullSecrets. Base64 is not encryption.
- imagePullPolicy:Always controls registry-reference checking, not signature verification. Configure digest pinning, admission verification, and scan gates separately.
- A pattern banning latest alone may miss omitted tags and init/ephemeral images. Test scope with the registry/digest policy above.
- Anonymous pulling of intentionally public images is not inherently a vulnerability. Separate confidentiality, push permission, provenance, rate limits, and licensing requirements.
- Ensure retention/garbage collection does not remove active digests or needed signature/attestation referrers; test recovery.

<span id="complete-image-security-pipeline"></span>

## CI/CD Pipeline Integration

Review the [complete workflow file](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml) before placing it at .github/workflows/secure-build.yaml in the application repository. A real Dockerfile and build context are prerequisites. Its intended properties are:

1. PR scanning uses a read-only job with no registry publishing/OIDC signing.
2. The main-push release job builds once and scans that local image.
3. It pushes without rebuilding and captures the RepoDigest.
4. Signing, verification, SBOM attestation, and provenance use that same digest.
5. Actions are pinned to reviewed commit SHAs; separate artifact-storage records are disabled.

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
          cosign verify --certificate-identity "$GITHUB_WORKFLOW_REF"             --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMAGE_REF"
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
          cosign verify-attestation --type spdxjson             --certificate-identity "$GITHUB_WORKFLOW_REF"             --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMAGE_REF"
      - name: Publish build provenance
        uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2
        with:
          subject-name: ${{ steps.image.outputs.repository }}
          subject-digest: ${{ steps.published.outputs.digest }}
          push-to-registry: true
          create-storage-record: false
```

Configure GHCR package permissions, Actions OIDC, attestation-plan support, and network access. Workflow YAML/action inputs and shell syntax were checked, but no GitHub-runner build/push/sign/attest workflow was executed. Do not ignore SBOM/signature failures or pass empty digests onward. If adding SARIF uploads, separately handle fork-PR security-events permissions and preserving results after scan failure.

## Checks Performed and Limits

- Trivy 0.74: two synthetic secret cases and two Dockerfile non-root checks. No actual CVE database or remote-image scan.
- Cosign 3.1.3: valid/tampered synthetic local key/blob verification. Omitting transparency in that private fixture is not evidence of production registry/OIDC verification.
- Kyverno 1.19.1: six CEL registry/digest object cases including init/ephemeral containers, plus two pinned CRD schemas. No live admission or network signature verification.
- Trivy Operator/Connaisseur Helm rendering, synthetic ECR API-model/JMESPath fixtures, CloudFormation lint, and actionlint were run. No AWS resources, notifications, or registry pushes were executed.

<span id="summary"></span>
<span id="recommendations"></span>

## References

- [Trivy releases](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Trivy documentation](https://aquasecurity.github.io/trivy/)
- [Trivy Operator chart](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [ECR scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Inspector event schemas](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [EventBridge target authorization](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [SNS KMS compatibility](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign 3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Sigstore verification](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Kyverno CEL migration](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Connaisseur namespaced validation](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [SLSA requirements](https://slsa.dev/spec/v1.2/build-requirements)
- [GitHub attest action](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
