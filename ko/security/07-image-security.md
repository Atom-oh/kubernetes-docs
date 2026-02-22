# 컨테이너 이미지 보안

> **지원 버전**: Trivy 0.56+, Kubernetes 1.31, 1.32, 1.33
> **마지막 업데이트**: 2025년 2월 21일

컨테이너 이미지 보안은 Kubernetes 보안의 첫 번째 방어선입니다. 이 문서에서는 이미지 스캐닝, 서명, 검증, 그리고 공급망 보안에 대해 다룹니다.

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

---

## 이미지 스캐닝 개요

### Shift-Left 보안

이미지 보안은 개발 프로세스 초기 단계에서 시작해야 합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Shift-Left 이미지 보안                                │
│                                                                         │
│  개발 단계                   빌드 단계                    런타임 단계    │
│  ┌─────────┐               ┌─────────┐               ┌─────────┐       │
│  │ IDE     │               │ CI/CD   │               │ K8s     │       │
│  │ 스캐닝  │──────────────▶│ 스캐닝  │──────────────▶│ 스캐닝  │       │
│  │         │               │         │               │         │       │
│  │ • 로컬  │               │ • 빌드  │               │ • 런타임│       │
│  │   스캔  │               │   게이트│               │   모니터│       │
│  │ • 의존성│               │ • 레지  │               │ • 정책  │       │
│  │   검사  │               │   스트리│               │   적용  │       │
│  └─────────┘               └─────────┘               └─────────┘       │
│                                                                         │
│  ◀─────────────────── 비용 및 수정 용이성 ─────────────────────▶        │
│     낮음                                                  높음          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 스캐닝 대상

| 대상 | 설명 | 도구 |
|------|------|------|
| **OS 패키지** | 운영체제 패키지 취약점 | Trivy, Grype, Clair |
| **언어별 의존성** | npm, pip, go modules 등 | Trivy, Snyk |
| **설정 오류** | Dockerfile, K8s 매니페스트 | Trivy, Checkov |
| **시크릿** | 하드코딩된 비밀 정보 | Trivy, Trufflehog |
| **라이선스** | 오픈소스 라이선스 | Trivy, FOSSA |

---

## Trivy

### Trivy 개요

Trivy는 컨테이너, 파일시스템, Git 저장소 등을 스캔하는 종합 보안 스캐너입니다.

### Trivy 설치

```bash
# macOS
brew install trivy

# Linux (Debian/Ubuntu)
sudo apt-get install wget apt-transport-https gnupg
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy

# Docker
docker pull aquasec/trivy:latest
```

### 이미지 스캐닝

```bash
# 기본 이미지 스캔
trivy image nginx:latest

# 심각도 필터링
trivy image --severity HIGH,CRITICAL nginx:latest

# JSON 출력
trivy image --format json --output results.json nginx:latest

# SARIF 형식 (GitHub Security에 통합)
trivy image --format sarif --output results.sarif nginx:latest

# 특정 취약점 무시
trivy image --ignore-unfixed nginx:latest

# 시크릿 스캔 포함
trivy image --scanners vuln,secret nginx:latest
```

### 파일시스템 스캔

```bash
# 프로젝트 디렉토리 스캔
trivy fs --scanners vuln,secret,config .

# Dockerfile 스캔
trivy config Dockerfile

# Kubernetes 매니페스트 스캔
trivy config ./k8s/

# Helm 차트 스캔
trivy config ./charts/my-app/
```

### Trivy 설정 파일

```yaml
# trivy.yaml
severity:
  - HIGH
  - CRITICAL

scan:
  scanners:
    - vuln
    - secret
    - config

vulnerability:
  ignore-unfixed: true
  type:
    - os
    - library

secret:
  config: /path/to/secret-config.yaml

misconfiguration:
  helm:
    values:
      - values.yaml

ignore:
  - CVE-2023-12345  # 특정 CVE 무시
  - secret-rule-id  # 특정 시크릿 규칙 무시
```

### Trivy Operator (Kubernetes 통합)

```bash
# Trivy Operator 설치
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update

helm install trivy-operator aqua/trivy-operator \
    --namespace trivy-system \
    --create-namespace \
    --set trivy.ignoreUnfixed=true
```

```yaml
# VulnerabilityReport 확인
apiVersion: aquasecurity.github.io/v1alpha1
kind: VulnerabilityReport
metadata:
  name: deployment-nginx-nginx
  namespace: default
spec:
  # Trivy Operator가 자동 생성
report:
  scanner:
    name: Trivy
    version: 0.56.0
  summary:
    criticalCount: 2
    highCount: 5
    mediumCount: 10
    lowCount: 15
  vulnerabilities:
    - vulnerabilityID: CVE-2024-12345
      severity: CRITICAL
      title: "Buffer overflow in libssl"
      installedVersion: "1.1.1"
      fixedVersion: "1.1.2"
```

---

## Amazon ECR 이미지 스캐닝

### 기본 스캐닝 vs 향상된 스캐닝

| 기능 | 기본 스캐닝 | 향상된 스캐닝 (Inspector) |
|------|-----------|-------------------------|
| **스캔 엔진** | Clair | Amazon Inspector |
| **스캔 빈도** | 푸시 시 | 지속적 스캔 |
| **취약점 DB** | CVE | CVE + Amazon 위협 인텔리전스 |
| **비용** | 무료 | Inspector 요금 |
| **언어 패키지** | 제한적 | 광범위 지원 |
| **AWS 통합** | 기본 | Security Hub, EventBridge |

### 향상된 스캐닝 활성화

```bash
# 레지스트리 스캐닝 설정
aws ecr put-registry-scanning-configuration \
    --scan-type ENHANCED \
    --rules '[
        {
            "repositoryFilters": [
                {"filter": "production/*", "filterType": "WILDCARD"}
            ],
            "scanFrequency": "CONTINUOUS_SCAN"
        },
        {
            "repositoryFilters": [
                {"filter": "development/*", "filterType": "WILDCARD"}
            ],
            "scanFrequency": "SCAN_ON_PUSH"
        }
    ]'
```

### 스캔 결과 조회

```bash
# 스캔 결과 확인
aws ecr describe-image-scan-findings \
    --repository-name my-app \
    --image-id imageTag=latest \
    --query 'imageScanFindings.findings[?severity==`CRITICAL`]'

# 취약점 요약
aws ecr describe-image-scan-findings \
    --repository-name my-app \
    --image-id imageTag=latest \
    --query 'imageScanFindings.findingSeverityCounts'
```

### EventBridge를 통한 알림

```yaml
# CloudFormation/SAM 템플릿
Resources:
  ECRScanRule:
    Type: AWS::Events::Rule
    Properties:
      Name: ecr-scan-findings
      EventPattern:
        source:
          - aws.ecr
        detail-type:
          - ECR Image Scan
        detail:
          scan-status:
            - COMPLETE
          finding-severity-counts:
            CRITICAL:
              - exists: true
      Targets:
        - Id: SNSTarget
          Arn: !Ref AlertTopic
          InputTransformer:
            InputPathsMap:
              repo: "$.detail.repository-name"
              tag: "$.detail.image-tags[0]"
              critical: "$.detail.finding-severity-counts.CRITICAL"
            InputTemplate: |
              "ECR 스캔 경고: 저장소 <repo>:<tag>에서 CRITICAL 취약점 <critical>개 발견"
```

---

## Cosign/Sigstore를 사용한 이미지 서명

### Cosign 개요

Cosign은 Sigstore 프로젝트의 일부로, 컨테이너 이미지에 서명하고 검증하는 도구입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Cosign 이미지 서명 워크플로우                          │
│                                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐  │
│  │   Build     │────▶│   Sign      │────▶│   Push to Registry      │  │
│  │   Image     │     │   (Cosign)  │     │   (Image + Signature)   │  │
│  └─────────────┘     └─────────────┘     └───────────┬─────────────┘  │
│                                                       │                │
│                                                       ▼                │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      Container Registry                          │  │
│  │                                                                  │  │
│  │  ┌─────────────────┐    ┌─────────────────┐                    │  │
│  │  │   Image         │    │   Signature     │                    │  │
│  │  │   sha256:abc... │    │   sha256:xyz... │                    │  │
│  │  └─────────────────┘    └─────────────────┘                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                          │                             │
│                                          ▼                             │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Kubernetes Cluster                            │  │
│  │                                                                  │  │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │  │
│  │  │  Admission  │────▶│   Verify    │────▶│   Deploy    │       │  │
│  │  │  Controller │     │  Signature  │     │    Pod      │       │  │
│  │  │  (Kyverno)  │     │             │     │             │       │  │
│  │  └─────────────┘     └─────────────┘     └─────────────┘       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Cosign 설치

```bash
# macOS
brew install cosign

# Linux
curl -LO https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign

# 버전 확인
cosign version
```

### 키 기반 서명

```bash
# 키 쌍 생성
cosign generate-key-pair

# 이미지 서명
cosign sign --key cosign.key myregistry.io/myapp:v1.0.0

# 서명 검증
cosign verify --key cosign.pub myregistry.io/myapp:v1.0.0
```

### 키리스 서명 (OIDC 기반)

```bash
# GitHub Actions에서 키리스 서명
# GITHUB_TOKEN이 자동으로 OIDC 토큰 제공
cosign sign myregistry.io/myapp:v1.0.0

# 키리스 서명 검증
cosign verify \
    --certificate-identity=https://github.com/myorg/myrepo/.github/workflows/build.yaml@refs/heads/main \
    --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
    myregistry.io/myapp:v1.0.0
```

### GitHub Actions 통합

```yaml
name: Build, Sign and Push

on:
  push:
    branches: [main]

jobs:
  build-sign-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write  # 키리스 서명에 필요

    steps:
      - uses: actions/checkout@v4

      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push
        uses: docker/build-push-action@v5
        id: build
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

      - name: Sign Image (Keyless)
        env:
          DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          cosign sign --yes ghcr.io/${{ github.repository }}@${DIGEST}

      - name: Verify Signature
        run: |
          cosign verify \
            --certificate-identity-regexp="https://github.com/${{ github.repository }}/*" \
            --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
            ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## Admission Control에서 이미지 검증

### Kyverno imageVerify

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: verify-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
      verifyImages:
        - imageReferences:
            - "ghcr.io/myorg/*"
          attestors:
            - count: 1
              entries:
                - keyless:
                    subject: "https://github.com/myorg/*/.github/workflows/*@refs/heads/main"
                    issuer: "https://token.actions.githubusercontent.com"
                    rekor:
                      url: https://rekor.sigstore.dev
---
# 키 기반 검증
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-key
spec:
  validationFailureAction: Enforce
  rules:
    - name: verify-key-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
      verifyImages:
        - imageReferences:
            - "myregistry.io/*"
          attestors:
            - count: 1
              entries:
                - keys:
                    publicKeys: |
                      -----BEGIN PUBLIC KEY-----
                      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                      -----END PUBLIC KEY-----
```

### Connaisseur

```yaml
# Connaisseur 설치
helm repo add connaisseur https://sse-secure-systems.github.io/connaisseur/charts
helm install connaisseur connaisseur/connaisseur \
    -n connaisseur \
    --create-namespace
```

```yaml
# Connaisseur 설정
# values.yaml
validators:
  - name: cosign
    type: cosign
    trustRoots:
      - name: production
        key: |
          -----BEGIN PUBLIC KEY-----
          MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
          -----END PUBLIC KEY-----

policy:
  - pattern: "ghcr.io/myorg/*"
    validator: cosign
    with:
      trustRoot: production
  - pattern: "*"
    validator: deny  # 기타 이미지 거부
```

---

## 공급망 보안

### SBOM (Software Bill of Materials) 생성

```bash
# Syft로 SBOM 생성
syft myregistry.io/myapp:latest -o spdx-json > sbom.spdx.json
syft myregistry.io/myapp:latest -o cyclonedx-json > sbom.cyclonedx.json

# Trivy로 SBOM 생성
trivy image --format spdx-json --output sbom.json myregistry.io/myapp:latest

# SBOM을 이미지에 첨부 (Cosign)
cosign attach sbom --sbom sbom.spdx.json myregistry.io/myapp:latest
```

### SBOM 기반 취약점 검사

```bash
# SBOM에서 취약점 스캔
trivy sbom sbom.spdx.json

# Grype로 SBOM 스캔
grype sbom:sbom.spdx.json
```

### SLSA (Supply chain Levels for Software Artifacts)

```yaml
# GitHub Actions에서 SLSA Provenance 생성
name: SLSA Build

on:
  push:
    branches: [main]

jobs:
  build:
    outputs:
      digest: ${{ steps.build.outputs.digest }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and Push
        id: build
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

  provenance:
    needs: build
    permissions:
      actions: read
      id-token: write
      packages: write
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v1.9.0
    with:
      image: ghcr.io/${{ github.repository }}
      digest: ${{ needs.build.outputs.digest }}
    secrets:
      registry-username: ${{ github.actor }}
      registry-password: ${{ secrets.GITHUB_TOKEN }}
```

---

## 기본 이미지 선택

### 이미지 유형 비교

| 이미지 유형 | 크기 | 취약점 | 디버깅 | 사용 사례 |
|------------|------|--------|--------|----------|
| **distroless** | 매우 작음 | 매우 적음 | 어려움 | 프로덕션 |
| **Alpine** | 작음 (~5MB) | 적음 | 가능 | 경량 앱 |
| **Chainguard** | 작음 | 매우 적음 | 제한적 | 보안 중심 |
| **Ubuntu/Debian** | 큼 | 많음 | 쉬움 | 개발/레거시 |
| **Scratch** | 최소 | 없음 | 불가 | 정적 바이너리 |

### Distroless 이미지 사용

```dockerfile
# 멀티 스테이지 빌드로 distroless 사용
FROM golang:1.22 AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server

# Distroless 런타임 이미지
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /app/server /server
USER nonroot:nonroot
ENTRYPOINT ["/server"]
```

### Chainguard 이미지 사용

```dockerfile
# Chainguard Python 이미지
FROM cgr.dev/chainguard/python:latest
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER nonroot
CMD ["python", "app.py"]
```

### Alpine 보안 강화

```dockerfile
FROM alpine:3.19

# 최소 패키지만 설치
RUN apk add --no-cache \
    python3 \
    py3-pip \
    && rm -rf /var/cache/apk/*

# 비루트 사용자 생성
RUN addgroup -g 1000 app && \
    adduser -u 1000 -G app -s /bin/sh -D app

WORKDIR /app
COPY --chown=app:app . .

USER app
CMD ["python3", "app.py"]
```

---

## 이미지 레지스트리 모범 사례

### 프라이빗 레지스트리 사용

```yaml
# ImagePullSecrets 설정
apiVersion: v1
kind: Secret
metadata:
  name: registry-credentials
  namespace: production
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: <base64-encoded-docker-config>
---
# ServiceAccount에 기본 ImagePullSecret 설정
apiVersion: v1
kind: ServiceAccount
metadata:
  name: default
  namespace: production
imagePullSecrets:
  - name: registry-credentials
```

### 이미지 풀 정책

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: app
    image: myregistry.io/myapp@sha256:abc123...  # 다이제스트 사용
    imagePullPolicy: Always  # 항상 최신 검증
```

### 불변 태그 정책 (Kyverno)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-digest
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-digest
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Images must use digest instead of tags"
        pattern:
          spec:
            containers:
              - image: "*@sha256:*"
---
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest-tag
spec:
  validationFailureAction: Enforce
  rules:
    - name: disallow-latest
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Using 'latest' tag is not allowed"
        pattern:
          spec:
            containers:
              - image: "!*:latest"
```

---

## CI/CD 파이프라인 통합

### 완전한 이미지 보안 파이프라인

```yaml
# .github/workflows/secure-build.yaml
name: Secure Image Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # 1. 코드 스캔
  code-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner (fs mode)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  # 2. 빌드 및 스캔
  build-scan:
    needs: code-scan
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      security-events: write
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image for scanning
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: ${{ env.IMAGE_NAME }}:scan

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ env.IMAGE_NAME }}:scan'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Check for critical vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ env.IMAGE_NAME }}:scan'
          exit-code: '1'
          severity: 'CRITICAL'

  # 3. 푸시 및 서명
  push-sign:
    needs: build-scan
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write

    outputs:
      digest: ${{ steps.push.outputs.digest }}

    steps:
      - uses: actions/checkout@v4

      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        id: push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Sign image with Cosign
        run: |
          cosign sign --yes ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.push.outputs.digest }}

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.push.outputs.digest }}
          format: spdx-json
          output-file: sbom.spdx.json

      - name: Attach SBOM to image
        run: |
          cosign attach sbom --sbom sbom.spdx.json ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.push.outputs.digest }}

  # 4. SLSA Provenance 생성
  provenance:
    needs: push-sign
    permissions:
      actions: read
      id-token: write
      packages: write
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v1.9.0
    with:
      image: ghcr.io/${{ github.repository }}
      digest: ${{ needs.push-sign.outputs.digest }}
    secrets:
      registry-username: ${{ github.actor }}
      registry-password: ${{ secrets.GITHUB_TOKEN }}
```

---

## 요약

컨테이너 이미지 보안의 핵심:

1. **스캐닝**: Trivy, ECR 향상된 스캔으로 취약점 탐지
2. **서명**: Cosign/Sigstore로 이미지 무결성 보장
3. **검증**: Kyverno로 서명된 이미지만 배포 허용
4. **공급망**: SBOM, SLSA로 투명성 확보
5. **기본 이미지**: distroless, Chainguard 사용
6. **CI/CD 통합**: 자동화된 보안 파이프라인 구축

### 권장 사항

- 모든 이미지에 취약점 스캔 적용
- 프로덕션 이미지는 반드시 서명
- `latest` 태그 대신 다이제스트 사용
- distroless 또는 최소 기본 이미지 사용
- SBOM 생성 및 관리 자동화

---

## 참고 자료

- [Trivy 공식 문서](https://aquasecurity.github.io/trivy/)
- [Cosign/Sigstore 문서](https://docs.sigstore.dev/)
- [Kyverno 이미지 검증](https://kyverno.io/docs/writing-policies/verify-images/)
- [SLSA 프레임워크](https://slsa.dev/)
- [Chainguard 이미지](https://www.chainguard.dev/chainguard-images)
