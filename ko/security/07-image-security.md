# 컨테이너 이미지 보안

> **마지막 업데이트**: 2026년 9월 13일
> **검증 기준**: Trivy 0.74.0, Trivy Operator 0.34.0/chart 0.36.0, Cosign 3.1.3, Kyverno 1.19.1, Connaisseur 3.12.0/chart 2.12.0. CLI·설정 검증 기준이며 모든 Kubernetes 버전에서 배포를 시험했다는 뜻은 아닙니다.

이미지 보안은 **빌드한 이미지, 검사한 이미지, 배포하는 이미지가 같은 artifact인지** 확인하는 데서 시작합니다. 스캔은 알려진 취약점과 구성 문제를 찾고, 서명은 서명자와 digest의 연결을 검증합니다. 어느 하나도 애플리케이션이 안전하다는 보증은 아닙니다.

## 목차

1. [이미지 스캐닝 개요](#이미지-스캐닝-개요)
2. [Trivy](#trivy)
3. [Amazon ECR 이미지 스캐닝](#amazon-ecr-이미지-스캐닝)
4. [Cosign/Sigstore를 사용한 이미지 서명](#cosignsigstore를-사용한-이미지-서명)
5. [Admission Control에서 이미지 검증](#admission-control에서-이미지-검증)
6. [공급망 보안](#공급망-보안)
7. [기본 이미지 선택](#기본-이미지-선택)
8. [이미지 레지스트리 모범 사례](#이미지-레지스트리-모범-사례)
9. [CI/CD 파이프라인 통합](#cicd-파이프라인-통합)

<span id="shift-left-보안"></span>
<span id="스캐닝-대상"></span>

## 이미지 스캐닝 개요

Shift-left는 IDE·PR·빌드에서 문제를 일찍 찾는 방식입니다. 운영 중 새 CVE가 발표되므로 registry 재검사와 런타임 탐지도 별도로 필요합니다.

| 대상 | 확인할 것 | 예시 도구 |
|---|---|---|
| OS·언어 패키지 | 패키지 식별, DB 갱신 시점, 수정 버전, VEX 판단 | Trivy, Grype |
| IaC·Dockerfile | 비루트 실행, 권한, 설정 | Trivy misconfig, Checkov |
| 시크릿 | 이미지 layer·소스에 포함된 credential | Trivy secret, TruffleHog |
| 라이선스·SBOM | 구성요소·라이선스 식별의 coverage | Syft, Trivy |
| 런타임 행위 | 실행 중 syscall·process·network | Falco 등 별도 도구 |

흐름은 `소스 검사 → 한 번 빌드 → 같은 artifact 검사 → push → digest 서명/검증 → admission 검사 → 재검사`입니다. CI의 severity gate는 조직이 정하고, 예외에는 소유자·근거·만료일을 둡니다.

<span id="trivy-개요"></span>
<span id="trivy-설치"></span>
<span id="이미지-스캐닝"></span>
<span id="파일시스템-스캔"></span>
<span id="trivy-설정-파일"></span>

## Trivy

### 설치와 스캔 명령

공식 릴리스의 OS/CPU 아키텍처별 패키지와 checksum을 함께 확인합니다. Linux ARM64에 amd64 바이너리를 설치하거나 폐기된 `apt-key` 절차를 사용하지 않습니다. 운영 자동화에서는 CLI와 action 버전을 고정합니다.

```bash
trivy --version
# 실제 보유한 immutable reference로 설정합니다.
IMAGE_REF='registry.example.com/team/app@sha256:REPLACE_WITH_64_HEX_DIGEST'
trivy image --severity HIGH,CRITICAL --exit-code 1 "$IMAGE_REF"
trivy image --format json --output results.json "$IMAGE_REF"
trivy image --format sarif --output results.sarif "$IMAGE_REF"
trivy image --scanners vuln,secret "$IMAGE_REF"
trivy fs --scanners vuln,secret,misconfig .
trivy config ./k8s/
trivy config ./charts/my-app/ --helm-values ./charts/my-app/values.yaml
```

`IMAGE_REF`는 의도적인 대체값입니다. 실제 이미지 digest를 넣어야 실행됩니다. `--scanners config`가 아니라 `misconfig`를 사용합니다. `--ignore-unfixed`는 아직 수정 버전이 없는 취약점을 숨기므로 기본 gate에서 무조건 켜지 않습니다. registry 접근·취약점 DB·Java DB·check bundle의 네트워크와 cache 요구를 확인하세요. `trivy config`에는 `--offline-scan` 옵션이 없습니다.

### 설정 파일과 예외

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

이 파일은 image/fs 스캔용 기준입니다. 사용하지 않는 `vulnerability.type`이나 최상위 `ignore` 목록을 넣지 않습니다. 예외는 `.trivyignore`/지원 ignore-policy 형식으로 관리하고 secret 예외와 vulnerability 예외를 구분합니다. 예제 `.trivyignore`는 비어 있습니다.

<span id="trivy-operator-kubernetes-통합"></span>

### Trivy Operator

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update aqua
helm upgrade --install trivy-operator aqua/trivy-operator   --version 0.36.0 --namespace trivy-system --create-namespace   --values trivy-operator-values.yaml
kubectl get vulnerabilityreports -A
```

chart 0.36.0의 application 버전은 0.34.0입니다. [values 파일](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/trivy-operator-values.yaml)은 `ignoreUnfixed: false`를 명시합니다. Report는 operator가 생성하는 결과이며 가짜 CVE·package version을 넣은 매니페스트를 배포하지 않습니다. 실제 report schema, 대상 namespace, registry credential, scan Job 권한과 자원을 확인하세요. 이 감사에서는 Helm 렌더링만 수행했습니다.

<span id="기본-스캐닝-vs-향상된-스캐닝"></span>
<span id="향상된-스캐닝-활성화"></span>
<span id="스캔-결과-조회"></span>
<span id="eventbridge를-통한-알림"></span>

## Amazon ECR 이미지 스캐닝

| 구분 | Basic | Enhanced |
|---|---|---|
| 현재 엔진 | AWS native scanner | Amazon Inspector |
| 대상 | OS package 취약점 | OS 및 지원 언어 package 취약점 |
| 주기 | Manual 또는 scan-on-push | Scan-on-push 또는 continuous |
| 결과 | `imageScanFindings.findings` | `imageScanFindings.enhancedFindings` |
| 이벤트 | ECR basic scan 완료 이벤트 | Inspector2 scan/finding 이벤트 |

Basic을 Clair 기반이라고 설명한 과거 문서와 현재 엔진을 구분합니다. scan 설정 전환 시 기존 결과의 표시가 달라질 수 있습니다. Enhanced도 repository filter·재검사 기간·지원 image 조건에 따라 coverage가 달라지며 모든 이미지를 무기한 검사하지 않습니다. 보관(archived) 이미지는 restore 후 검사해야 합니다.

```bash
aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules '[
  {"repositoryFilters":[{"filter":"production/*","filterType":"WILDCARD"}],"scanFrequency":"CONTINUOUS_SCAN"},
  {"repositoryFilters":[{"filter":"development/*","filterType":"WILDCARD"}],"scanFrequency":"SCAN_ON_PUSH"}
]'
# Enhanced 결과. Basic이면 enhancedFindings 대신 findings를 조회합니다.
aws ecr describe-image-scan-findings --repository-name production/my-app   --image-id imageDigest=sha256:REPLACE_WITH_64_HEX_DIGEST   --query 'imageScanFindings.enhancedFindings[?severity==`CRITICAL`]'
```

위 설정은 registry에 쓰는 명령이며 이 감사에서 실행하지 않았습니다. Basic의 `DescribeImages` summary만으로 현재 스캔 결과를 판정하지 말고 `DescribeImageScanFindings`를 사용합니다. ECR 스캔 활성화 자체가 취약한 이미지의 push/pull/deploy를 자동 차단하지는 않습니다.

### Inspector 알림과 권한

Enhanced findings는 `source: aws.inspector2`, `detail-type: Inspector2 Finding`의 `detail.severity`, `detail.status`, `detail.resources[].type`을 기준으로 필터링합니다. Basic의 `ECR Image Scan` 및 `finding-severity-counts`와 혼용하지 않습니다. 숫자0도 field 존재 조건을 만족할 수 있으므로 단순 `exists: true`를 양수 취약점 수로 해석하지 않습니다.

[완전한 CloudFormation 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)는 encrypted SNS topic과 EventBridge 실행 role을 연결합니다. 기존의 동일 Account/Region symmetric customer-managed KMS key와 IAM delegation을 허용하는 key policy가 필요하며, 승인된 SNS consumer 구독은 별도입니다. 현재 EventBridge는 SNS target에 execution role을 지원합니다. 직접 service principal이 encrypted SNS를 호출하는 경로에 event-bus용 KMS SourceArn/SourceAccount 조건을 그대로 복사하면 안 됩니다. 예제는 cfn-lint를 통과했지만 실제 알림·KMS 권한·retry 후 전달은 배포 환경에서 확인해야 합니다.

<span id="cosign-개요"></span>
<span id="cosign-설치"></span>
<span id="키-기반-서명"></span>
<span id="키리스-서명-oidc-기반"></span>
<span id="github-actions-통합"></span>

<span id="cosignsigstore를-사용한-이미지-서명"></span>

## Cosign/Sigstore를 사용한 이미지 서명

### 서명 순서와 신뢰 기준

일반 registry 흐름에서는 이미지를 push해 digest를 얻은 다음 그 digest에 서명합니다. 서명 검증은 신뢰할 key 또는 정확한 OIDC issuer/identity, digest, 필요한 transparency/timestamp 증거를 함께 확인합니다. 서명이 있다고 signer가 승인되었거나 CVE가 없다는 뜻은 아닙니다.

```bash
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$IMAGE_REF"
cosign verify --key cosign.pub "$IMAGE_REF"
```

private key는 예제 저장소에 커밋하지 않고 credential manager/KMS 등의 수명주기로 관리합니다. 키리스 GitHub Actions는 `id-token: write`와 Actions OIDC 환경을 사용합니다. `GITHUB_TOKEN`은 registry/API credential이며 OIDC ID token 자체가 아닙니다.

```bash
cosign sign --yes "$IMAGE_REF"
cosign verify   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'   "$IMAGE_REF"
```

Identity 값은 실제 승인된 workflow로 바꿉니다. `--certificate-identity-regexp`는 glob이 아닌 정규식입니다. ``https://github.com/org/repo/*`` 같은 느슨한 식으로 모든 workflow를 승인하지 말고 정확한 identity 또는 경계를 고정한 regexp를 사용합니다. Cosign 3의 bundle/OCI referrer와 소비하는 verifier의 지원도 함께 확인합니다.

<span id="kyverno-imageverify"></span>

## Admission Control에서 이미지 검증

Kyverno 1.19.1은 기존 `ClusterPolicy`에 deprecation 경고를 냅니다. 신규 예제는 `policies.kyverno.io/v1`의 `ValidatingPolicy`와 `ImageValidatingPolicy`를 사용합니다. 기존 `verifyImages` 규칙을 신규 policy kind와 같은 것으로 취급하지 않습니다.

### Registry·digest 정책

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

일반·init·ephemeral container를 모두 검사하며 `pods/ephemeralcontainers` update 경로를 포함합니다. `example-org`는 실제 승인 repository로 교체합니다. digest 형식은 내용 주소를 고정하지만 서명이나 취약점 판정을 대신하지 않습니다.

### Workflow 서명 정책

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

`matchImageReferences`와 맞지 않는 이미지는 image-verification에서 건너뛸 수 있으므로 registry 정책을 함께 적용합니다. namespace 예외·PolicyException·webhook availability·timeout·registry pull credential·TLS trust를 설계하고 실제 admission request를 시험하세요. 위 서명 정책은 CRD schema를 확인했으며 실제 registry/Fulcio/Rekor 검증을 실행한 결과는 아닙니다. Transparency 검사를 끄는 옵션은 production 예제에 넣지 않았습니다.

<span id="connaisseur"></span>

### Connaisseur 대안 — legacy 서명 경로

**Connaisseur 3.12.0은 기본 Cosign 3 bundle을 소비하는 대안이 아닙니다.** 이 버전은 cosign/v2 검증 경로와 legacy signature tag·SimpleSigning payload를 사용합니다. 별도 compatibility producer가 필요합니다. [legacy 서명 스크립트](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-sign-legacy.sh)는 Cosign 3.1.3에 `--new-bundle-format=false --registry-referrers-mode=legacy`를 명시하고 transparency upload/검증을 유지합니다. 동봉한 signing config는 Rekor v1을 명시하며 legacy verifier가 소비하는 로그 형식을 유지합니다. 실제 승인 key와 digest를 제공해야 합니다. 이 경로는 아래 secure-build.yaml의 기본 bundle 경로와 별도이며, 해당 기본 workflow의 결과를 그대로 Connaisseur에 넣으면 안 됩니다. Legacy 옵션은 deprecated이므로 verifier와 producer를 함께 업그레이드하는 마이그레이션 계획이 필요합니다. CLI 옵션과 양쪽 소스 계약은 확인했지만 실제 registry/signature 연동을 실행하지 않았습니다.

Connaisseur 3.12.0/chart 2.12.0을 사용할 수도 있습니다. [values 예제](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/connaisseur-values.yaml)에서 `validators`와 `policy`는 `application` 아래에 있고, `deny`는 명시적으로 정의한 static validator입니다. 포함된 public key는 합성 검사 key이므로 실제 신뢰 key로 교체해야 합니다.

```bash
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm upgrade --install connaisseur connaisseur/connaisseur   --version 2.12.0 --namespace connaisseur --create-namespace   --values connaisseur-values.yaml
kubectl label namespace production securesystemsengineering.connaisseur/webhook=validate
```

예제는 namespaced validation의 `validate` mode이며 위 label이 있는 namespace만 검사합니다. namespace label을 수정할 수 있는 주체는 검사를 회피할 수 있으므로 그 권한도 통제합니다. Kyverno와 Connaisseur는 대안이며 두 admission controller를 무조건 중복 설치하는 절차가 아닙니다. Helm 렌더링 검증은 실제 서명 승인/거부 시험을 대체하지 않습니다.

<span id="sbom-software-bill-of-materials-생성"></span>
<span id="sbom-기반-취약점-검사"></span>
<span id="slsa-supply-chain-levels-for-software-artifacts"></span>

## 공급망 보안

### SBOM과 attestation

```bash
syft "$IMAGE_REF" -o spdx-json=sbom.spdx.json
trivy image --format spdx-json --output sbom.spdx.json "$IMAGE_REF"
trivy sbom sbom.spdx.json
# 또는 Grype
# grype sbom:sbom.spdx.json
cosign attest --yes --type spdxjson --predicate sbom.spdx.json "$IMAGE_REF"
cosign verify-attestation --type spdxjson   --certificate-identity 'https://github.com/example-org/example-app/.github/workflows/secure-build.yaml@refs/heads/main'   --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' "$IMAGE_REF"
```

Syft/Trivy 생성 명령은 대안입니다. SBOM은 도구가 발견한 구성요소 inventory이며 완전성이나 안전성을 보장하지 않습니다. `cosign attach sbom`은 deprecated이며 단순 첨부는 서명된 attestation과 다릅니다. Predicate 내용, subject digest, signer, 검증 시점과 policy를 함께 확인합니다.

### SLSA provenance

SLSA provenance는 build 입력·builder·artifact 사이의 관계를 기록합니다. 생성 action 하나를 호출했다고 SLSA Build Level3가 자동 충족되지는 않습니다. builder 격리·provenance 위조 저항·source policy 등 해당 수준의 요구사항을 별도로 평가합니다.

`slsa-github-generator`의 기존 reusable workflow를 쓰는 경우 지원 toolchain과 호출 요건을 확인합니다. 아래 신규 workflow는 current `actions/attest`를 사용합니다. `attest-build-provenance` v4는 wrapper이며 신규 구현은 `actions/attest`가 권장됩니다. public/private repository의 GitHub plan과 Sigstore trust root 차이도 확인합니다.

<span id="이미지-유형-비교"></span>
<span id="distroless-이미지-사용"></span>
<span id="chainguard-이미지-사용"></span>
<span id="alpine-보안-강화"></span>

## 기본 이미지 선택

| 이미지 | 특성 | 확인할 위험 |
|---|---|---|
| Distroless | 일반 runtime에 shell/package manager가 없음 | debug variant·라이브러리·앱 dependency는 별도 |
| Alpine | 작은 musl 기반 배포판 | glibc 호환성, package 지원기간, 실제 digest |
| Chainguard | 최소 runtime과 dev variant 구분 | runtime에 shell/pip가 있다고 가정하지 않음 |
| Ubuntu/Debian | 도구·package 선택 폭이 넓음 | 크기만으로 취약점 수를 단정하지 않음 |
| Scratch | 빈 base image | 복사한 binary·CA·앱 dependency에는 취약점이 있을 수 있음 |

기존 예제의 Go1.22·Alpine3.19를 현재 지원 버전으로 오인하지 않습니다. 기반 이미지의 유지보수·OS EOL·CPU ABI·digest와 스캔 결과를 확인하고 업데이트합니다. Distroless는 build stage에서 만든 바이너리를 복사하며, Chainguard Python은 dev stage에서 venv/dependency를 구성하고 runtime으로 복사하는 공식 패턴을 따릅니다. 이 문서는 Dockerfile을 실제 빌드하거나 취약점 개수를 비교하지 않았습니다.

### 최소 base-image 빌드 예제

[전체 build context](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/image-security/base-images)에는 고정 문자열을 출력하는 Go/Python 앱과 세 Dockerfile이 있습니다. Dockerfile 선택만 바꾸어 패턴을 비교할 수 있으며 웹 서버 예제가 아닙니다. Base index digest와 amd64/arm64 지원은 확인했지만 Docker image build/runtime은 실행하지 않았습니다.

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

Go1.27.1과 Python3.12에서 앱을 직접 실행했고, 세 Dockerfile의 HIGH/CRITICAL 구성 검사를 통과했습니다. Python requirements는 이 fixture에서 비어 있습니다. 실제 dependency를 추가하면 hash/lock·builder/runtime ABI와 취약점 검사를 확장해야 합니다. Alpine apk 저장소와 base digest의 갱신 절차도 별도로 관리합니다.

<span id="프라이빗-레지스트리-사용"></span>
<span id="이미지-풀-정책"></span>
<span id="불변-태그-정책-kyverno"></span>

## 이미지 레지스트리 모범 사례

- Private 이미지에는 승인된 pull identity를 사용합니다. ECR의 kubelet/node/Fargate 실행 role과 애플리케이션의 Pod Identity는 역할이 다릅니다.
- 외부 registry는 유효한 `kubernetes.io/dockerconfigjson` Secret과 ServiceAccount의 imagePullSecrets를 사용하되, base64를 암호화로 취급하지 않습니다.
- `imagePullPolicy: Always`는 registry의 image reference 확인 동작이며 서명 검사 옵션이 아닙니다. digest pinning·admission 검증·scan gate를 따로 구성합니다.
- `latest`를 금지하는 pattern만으로 tag 생략이나 init/ephemeral 이미지를 모두 막지 못합니다. 위 registry/digest 정책으로 범위를 시험합니다.
- 공개 배포용 이미지의 anonymous pull 자체가 항상 취약점은 아닙니다. 비공개 정보·push 권한·출처 검증·rate limit·license 정책을 구분합니다.
- Retention/garbage collection이 실행 중인 digest와 서명·attestation/referrer를 삭제하지 않도록 복구 경로를 확인합니다.

<span id="완전한-이미지-보안-파이프라인"></span>

<span id="cicd-파이프라인-통합"></span>

## CI/CD 파이프라인 통합

[완전한 workflow 파일](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/secure-build.yaml)을 repository의 `.github/workflows/secure-build.yaml`로 검토 후 사용합니다. 원본 repository에 Dockerfile과 실제 애플리케이션 build context가 있어야 합니다. 예제는 아래 속성을 갖습니다.

1. PR scan은 read-only job이며 registry push·OIDC signing을 수행하지 않습니다.
2. main push의 release job에서 한 번 빌드하고 같은 로컬 image를 스캔합니다.
3. 스캔 후 다시 빌드하지 않고 push하며 RepoDigest를 얻습니다.
4. 같은 digest를 서명·검증하고 SBOM attestation과 provenance에 사용합니다.
5. Actions는 검토한 commit SHA로 고정하며, 별도 artifact storage record는 생성하지 않습니다.

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

GHCR package 권한, Actions OIDC, attestation plan, registry connectivity를 설정해야 합니다. Workflow YAML/action inputs와 shell 구문은 검증했지만 GitHub runner에서 build·push·sign·attest를 실행하지 않았습니다. SBOM 생성 실패·signature 실패를 무시하거나 비어 있는 digest를 다음 단계로 전달하지 않습니다. SARIF upload를 추가할 경우 fork PR의 security-events 권한과 scan 실패 시 결과 보존을 별도로 설계하세요.

## 수행한 검증과 한계

- Trivy0.74: 합성 시크릿 탐지/비탐지2건, Dockerfile 비루트 검사2건. 실제 CVE DB 또는 원격 이미지는 스캔하지 않았습니다.
- Cosign3.1.3: 로컬 합성 key/blob의 정상 서명과 변조 거부. private fixture의 transparency 생략은 registry/OIDC production 검증의 증거가 아닙니다.
- Kyverno1.19.1: CEL registry/digest 정책6건(일반·init·ephemeral 포함), 두 정책의 pinned CRD schema. Live admission과 image signature network verification은 미실행입니다.
- Trivy Operator/Connaisseur Helm 렌더링, ECR API model/JMESPath 합성 fixture, CloudFormation lint, actionlint를 수행했습니다. 실제 AWS 리소스·알림·registry push는 실행하지 않았습니다.

<span id="요약"></span>
<span id="권장-사항"></span>

## 참고 자료

- [Trivy releases](https://github.com/aquasecurity/trivy/releases/tag/v0.74.0)
- [Trivy documentation](https://aquasecurity.github.io/trivy/)
- [Trivy Operator chart](https://github.com/aquasecurity/trivy-operator/tree/v0.34.0/deploy/helm)
- [ECR scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Inspector event schemas](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [EventBridge target authorization](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)
- [SNS KMS compatibility](https://docs.aws.amazon.com/sns/latest/dg/sns-key-management.html)
- [Cosign3.1.3](https://github.com/sigstore/cosign/releases/tag/v3.1.3)
- [Sigstore verification](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Kyverno CEL migration](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ImageValidatingPolicy](https://kyverno.io/docs/policy-types/image-validating-policy/)
- [Connaisseur namespaced validation](https://github.com/sse-secure-systems/connaisseur/blob/v3.12.0/docs/features/namespaced_validation.md)
- [SLSA requirements](https://slsa.dev/spec/v1.2/build-requirements)
- [GitHub attest action](https://github.com/actions/attest/tree/v4.2.2)
- [Distroless](https://github.com/GoogleContainerTools/distroless)
- [Chainguard Python](https://images.chainguard.dev/directory/image/python/overview)
