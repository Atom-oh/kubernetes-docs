# 컨테이너 레지스트리 모범 사례

> **마지막 업데이트**: 2026년 9월 11일

## 개요

이 문서는 Docker Hub, Amazon ECR, Harbor 등 컨테이너 레지스트리를 운영할 때 적용해야 할 모범 사례를 다룹니다. 태그 전략, 보안, 비용 최적화, CI/CD 통합 패턴을 포함합니다.

---

API·CLI 예제의 계정·리전·호스트·repository는 예시입니다. 대상 리소스와 자격 증명을 먼저 준비합니다. Harbor API 예제는 `HARBOR_USER` 사용자 이름을 설정하고 `curl --user`의 비밀번호 프롬프트를 사용합니다. Endpoint ID는 생성 응답에서 확인합니다.

## 태그 관리 전략

### Immutable Tags 사용

**배포는 검증한 digest로 고정하고 릴리스 태그에는 Registry의 불변성 정책을 적용합니다.** `v1.2.3`처럼 이름만 붙인 태그도 정책이 없으면 덮어쓸 수 있습니다:

```text
# ❌ 문제: Mutable 태그
image: myapp:latest
# - 배포 간 이미지가 다를 수 있음
# - 롤백 시 어떤 버전인지 불명확
# - 감사 추적 불가

# ✅ 해결: Immutable 태그
image: myapp:v1.2.3
# - Registry 불변성 정책을 적용해야 동일한 대상 유지
# - 명확한 버전 추적
# - 재현 가능한 배포
```

**ECR Immutable Tags 설정:**

```bash
aws ecr put-image-tag-mutability \
  --repository-name myapp-prod \
  --image-tag-mutability IMMUTABLE
```

### Semantic Versioning

SemVer의 `+build` 메타데이터는 이미지 태그 문법에 그대로 사용할 수 없습니다. OCI label에 원본 SemVer를 보관하고 태그는 허용 문자(영숫자·`_`·`.`·`-`)로 매핑합니다.

```
MAJOR.MINOR.PATCH

예시:
1.0.0  - 초기 릴리스
1.1.0  - 하위 호환 기능 추가
1.1.1  - 버그 수정
2.0.0  - 하위 호환성 깨지는 변경
```

**버전 태그 자동화 (Git Tag 기반):**

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${ECR_REPO:?Set the complete registry/repository URI}"
VERSION=$(git describe --tags --exact-match --match 'v[0-9]*' HEAD)
[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo 'Expected an exact release tag such as v1.2.3' >&2; exit 1;
}
docker tag myapp:build "${ECR_REPO}:${VERSION}"
docker push "${ECR_REPO}:${VERSION}"
```

`docker tag`는 원본 1개와 목적지 1개만 받습니다. `v1`·`v1.2` 같은 이동 별칭을 함께 쓰려면 태그별로 호출하고, 릴리스 불변성 정책의 예외 및 배포 digest 고정을 따로 설계합니다.

### :latest 태그 금지

```text
# ❌ 프로덕션에서 절대 사용 금지
image: nginx:latest
image: myapp:latest

# ✅ 명시적 버전 사용
image: nginx:1.30.4
image: myapp:v1.2.3

# ✅ 또는 다이제스트 사용
image: nginx@sha256:<검증한 64자리 digest>
```

**Kubernetes Admission Controller로 :latest 검사:**

다음은 공식 Kyverno 예제의 Audit 정책입니다. 일반·init·ephemeral 컨테이너를 검사합니다. 설치한 Kyverno에서 태그 생략·Registry 포트·digest 사례를 시험한 뒤 Enforce로 전환합니다. 이 검사는 불변성이나 신뢰한 서명자를 증명하지 않습니다.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest-tag
  annotations:
    policies.kyverno.io/title: Disallow Latest Tag
    policies.kyverno.io/category: Best Practices
    policies.kyverno.io/minversion: 1.6.0
    policies.kyverno.io/severity: medium
    policies.kyverno.io/subject: Pod
    policies.kyverno.io/description: >-
      The ':latest' tag is mutable and can lead to unexpected errors if the
      image changes. A best practice is to use an immutable tag that maps to
      a specific version of an application Pod. This policy validates that the image
      specifies a tag and that it is not called `latest`.
spec:
  validationFailureAction: Audit
  background: true
  rules:
  - name: require-image-tag
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "An image tag is required."
      foreach:
        - list: "request.object.spec.containers"
          pattern:
            image: "*:*"
        - list: "request.object.spec.initContainers"
          pattern:
            image: "*:*"
        - list: "request.object.spec.ephemeralContainers"
          pattern:
            image: "*:*"
  - name: validate-image-tag
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "Using a mutable image tag e.g. 'latest' is not allowed."
      foreach:
        - list: "request.object.spec.containers"
          pattern:
            image: "!*:latest"
        - list: "request.object.spec.initContainers"
          pattern:
            image: "!*:latest"
        - list: "request.object.spec.ephemeralContainers"
          pattern:
            image: "!*:latest"
```

### Tag Promotion Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Build    │────▶│     Dev     │────▶│   Staging   │────▶│ Production  │
│             │     │             │     │             │     │             │
│ sha-abc123  │     │ dev-abc123  │     │stage-1.2.3  │     │   v1.2.3    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**프로모션 스크립트:**

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_REGION:?Set the registry region}"
: "${ECR_REGISTRY:?Set account.dkr.ecr.region.amazonaws.com}"
: "${SOURCE_REPO:?Set the source repository}"
: "${SOURCE_DIGEST:?Set the scanned sha256 digest}"
: "${TARGET_REPO:?Set the pre-created destination repository}"
: "${TARGET_TAG:?Set a new immutable release tag}"
aws ecr get-login-password --region "$AWS_REGION" \
  | skopeo login --username AWS --password-stdin "$ECR_REGISTRY"
skopeo copy --all --preserve-digests \
  "docker://${ECR_REGISTRY}/${SOURCE_REPO}@${SOURCE_DIGEST}" \
  "docker://${ECR_REGISTRY}/${TARGET_REPO}:${TARGET_TAG}"
```

---

## 이미지 네이밍 컨벤션

### 표준 형식

```
[registry/]organization/application:tag

예시:
docker.io/myorg/backend:v1.2.3
123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.2.3
harbor.example.com/platform/api-gateway:2.0.0
```

### 환경 접두사

```yaml
# 개발 환경
image: myapp-dev:abc123
image: myapp:dev-abc123

# 스테이징 환경
image: myapp-stage:1.2.3
image: myapp:stage-1.2.3

# 프로덕션 환경
image: myapp-prod:1.2.3
image: myapp:v1.2.3  # SemVer만 (환경 접두사 없음)
```

### Multi-arch 태그

```bash
# 멀티 아키텍처 이미지 빌드
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag myapp:v1.2.3 \
  --push .

```

아키텍처별 태그 예시:

```text
myapp:v1.2.3          # 멀티 아키텍처 매니페스트
myapp:v1.2.3-amd64    # x86_64 전용
myapp:v1.2.3-arm64    # ARM64 전용
```

### 메타데이터 태그

```dockerfile
# Existing Dockerfile stage, after FROM
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/myorg/myapp"
```

```bash
# 빌드 시 인자 전달
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.2.3 \
  -t myapp:v1.2.3 .
```

---

## 레지스트리 미러링 및 캐싱

![레이트 리밋 문제인지 가용성/성능 문제인지, 그리고 AWS/EKS 환경인지 자체 인프라인지에 따라 ECR Pull-through Cache, Harbor Proxy Cache, containerd 미러 설정, Harbor 전체 미러링, ECR 멀티 리전 복제, Harbor Pull Replication 중 적합한 캐싱/미러링 전략을 고르는 의사결정 트리를 보여준다.](../.gitbook/assets/ko-container-registry-04-best-practices-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-04-best-practices-0.html)

### containerd 레지스트리 미러 설정

다음은 동일한 Docker Hub repository 경로를 제공하는 신뢰한 mirror 예제입니다. containerd 2.x는 images 플러그인의 config_path, 1.x는 CRI 플러그인의 config_path를 사용합니다. `resolve`는 태그→digest 결정을 mirror에 신뢰하므로 신뢰한 mirror에만 부여합니다. ECR/Harbor의 프로젝트 prefix와 인증을 이 설정이 자동 변환하지는 않습니다.

```toml
# containerd 2.x: /etc/containerd/config.toml
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
# For containerd 1.x, use plugins."io.containerd.grpc.v1.cri".registry.
```

```toml
# /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"
[host."https://mirror.example.com"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/docker.io/mirror-ca.crt"
```

위 `server`는 Docker Hub fallback을 허용하므로 폐쇄망 전용 구성이 아닙니다. 폐쇄망과 인증 있는 ECR/Harbor cache에는 문서의 내부 URI를 직접 사용하고 노드 CA·imagePullSecrets·실제 pull을 검증합니다.

### ECR Pull-through Cache

Docker Hub 자격 증명은 같은 계정·리전의 Secrets Manager에 `ecr-pullthroughcache/` 접두사로 저장합니다. 필수 키는 `username`과 `accessToken`이며, 예제 ARN을 조립하지 말고 실제 ARN을 조회합니다. Repository 생성·import 권한과 서비스 연결 역할 조건은 [Amazon ECR](02-amazon-ecr.md)을 참고합니다.

```bash
# The upstream secret must already exist in this account and region.
: "${AWS_REGION:?Set the target AWS region}"
SECRET_ARN=$(aws secretsmanager describe-secret --region "$AWS_REGION" \
  --secret-id ecr-pullthroughcache/docker-hub --query ARN --output text)
aws ecr create-pull-through-cache-rule --region "$AWS_REGION" \
  --ecr-repository-prefix docker-hub \
  --upstream-registry-url registry-1.docker.io \
  --credential-arn "$SECRET_ARN"
```

사용 URI: `ACCOUNT.dkr.ecr.REGION.amazonaws.com/docker-hub/library/nginx:1.30.4`. 캐시 미스와 갱신은 업스트림에 의존합니다.

### Harbor Proxy Cache

Harbor에 upstream endpoint와 Proxy Cache 프로젝트를 만들고 `harbor.example.com/docker-hub-cache/library/nginx:1.30.4`처럼 프로젝트가 포함된 URI를 사용합니다. [Harbor](03-harbor.md)의 TLS·Robot·캐시 설정 절차를 따릅니다. 임의의 `/v2/<project>` endpoint를 containerd mirror로 넣는 것만으로는 경로·인증이 올바르게 변환되지 않습니다.

### 외부 의존성 최소화

```yaml
# 외부 레지스트리 직접 참조 (비권장)
containers:
- name: app
  image: docker.io/library/nginx:1.30.4
- name: sidecar
  image: quay.io/prometheus/prometheus:v3.14.0

---
# 내부 캐시/미러 사용 (권장)
containers:
- name: app
  image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/docker-hub/library/nginx:1.30.4
- name: sidecar
  image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/quay/prometheus/prometheus:v3.14.0
```

---

## 재해 복구

### 멀티 리전 복제

**ECR 복제:**

```bash
# AWS CLI로 복제 구성
aws ecr put-replication-configuration \
  --replication-configuration '{
    "rules": [
      {
        "destinations": [
          {"region": "us-west-2", "registryId": "123456789012"},
          {"region": "eu-west-1", "registryId": "123456789012"}
        ],
        "repositoryFilters": [
          {"filter": "prod-", "filterType": "PREFIX_MATCH"}
        ]
      }
    ]
  }'
```

**Harbor 복제:**

```bash
# Push-based 복제 (Primary -> DR)
curl --fail-with-body -X POST "https://harbor-primary.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "dr-replication",
    "src_registry": null,
    "dest_registry": {"id": 1},
    "dest_namespace": "mirror",
    "filters": [{"type": "name", "value": "prod/**"}],
    "trigger": {"type": "event_based"},
    "enabled": true
  }'
```

### 백업 전략과 RTO/RPO

ECR 복제는 비동기이며 복제 설정 이후 push/restore된 이미지부터 대상이 됩니다. 기존 이미지는 별도 backfill이 필요합니다. 목적지의 정책·권한·스캔·암호화·Lifecycle 설정과 실제 pull을 확인합니다. 복제 규칙을 바꾸는 API는 기존 설정 전체를 대체하므로 현재 규칙과 병합합니다.

RPO/RTO는 복제 지연, 장애 감지, 이미지·서명 준비, 클러스터 및 DNS 전환을 포함해 장애 훈련으로 측정합니다. 이벤트 복제라는 이유만으로 RPO 0이나 RTO 5분이 보장되지 않습니다. 삭제 복제는 DR 복사본도 지울 수 있으므로 백업과 분리해서 설계합니다.

이미지 백업은 태그 몇 개를 Docker로 pull/save하는 방식만으로 완성되지 않습니다. 검증한 digest 목록, 모든 CPU 플랫폼, OCI manifest, 서명·SBOM 및 복구 순서를 보관합니다. [Harbor의 Skopeo 반출·반입](03-harbor.md) 절차처럼 명시적인 목록과 체크섬을 사용하고, Harbor는 메타데이터 DB·blob·설정·키를 일관되게 백업합니다. S3의 tar 파일은 Kubernetes가 직접 pull할 수 있는 Registry가 아니므로 복구용 Registry로 import해야 합니다.

## 비용 최적화

### 비용 산정

스토리지, 리전/AZ/인터넷 전송, 스캐닝·서명, PrivateLink/NAT, Registry 컴퓨트·DB·백업 및 운영 인력을 따로 산정합니다. ECR의 특정 리전 스토리지 단가 예시 `$0.10/GB-month`는 전체 청구액이 아닙니다. `imageSizeInBytes` 합계도 공유 레이어 중복 제거를 반영한 청구 스토리지와 같지 않습니다. 500GB 같은 하나의 기준만으로 ECR/Harbor 비용 우위를 단정하지 않습니다.

### Lifecycle Policies

아래 ECR 정책은 개발 전용 repository에서 30일 지난 각 태그 접두사를 정리하는 예제입니다. 같은 `tagPatternList`의 여러 패턴은 OR가 아닌 **AND**이므로 접두사별로 규칙을 나눕니다. 한 digest에 릴리스·개발 태그를 섞지 않고 실행 중·롤백용 digest가 삭제되지 않는지 Lifecycle Preview로 확인합니다. untagged도 digest로 사용 중일 수 있어 자동 삭제를 기본값으로 넣지 않습니다.

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire dev-* development artifacts after 30 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "dev-*"
        ],
        "countType": "sinceImagePushed",
        "countNumber": 30,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Expire feature-* development artifacts after 30 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "feature-*"
        ],
        "countType": "sinceImagePushed",
        "countNumber": 30,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 3,
      "description": "Expire pr-* development artifacts after 30 days",
      "selection": {
        "tagStatus": "tagged",
        "tagPatternList": [
          "pr-*"
        ],
        "countType": "sinceImagePushed",
        "countNumber": 30,
        "countUnit": "days"
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

Harbor 보존 정책은 보존 조건의 OR 합집합이며 ECR과 다른 문법을 사용합니다. [Harbor](03-harbor.md)의 정책 UI·API dry run 절차를 따르고 삭제 후 GC까지 확인합니다.

### 이미지 크기 최적화

다음 Node.js 예제는 빌드에 필요한 devDependencies를 builder에 설치하고 런타임에는 production 의존성만 복사합니다. `npm ci --omit=dev`를 빌드 전에 실행하면 TypeScript·번들러 등이 없어 빌드가 실패할 수 있습니다. 소스의 build 스크립트, lockfile, dist 경로를 확인하고 `.dockerignore`에 node_modules·비밀 파일을 제외합니다.

```dockerfile
FROM node:24.21.0-alpine3.23 AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:24.21.0-alpine3.23 AS production-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

FROM node:24.21.0-alpine3.23
ENV NODE_ENV=production
WORKDIR /app
COPY --from=production-deps --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/dist ./dist
COPY --chown=node:node package.json ./
USER node
CMD ["node", "dist/main.js"]
```

이미지 크기는 애플리케이션·아키텍처·압축·의존성에 따라 달라집니다. Distroless는 자동 취약점 제거 수단이 아니며 builder/runtime ABI·CA 인증서·사용자·디버깅 절차를 검증해야 합니다. 운영에서는 검증한 base digest와 lockfile을 고정하고 업데이트를 주기적으로 반영합니다.

### 전송 비용 절감

클러스터와 같은 리전의 이미지 URI를 사용하고 필요한 이미지가 미리 복제됐는지 확인합니다. VPC Endpoint는 NAT 경로를 줄일 수 있지만 interface endpoint의 시간·처리 비용과 필요한 ECR API/DKR·S3 경로를 함께 계산합니다. Kustomize 지역별 오버레이는 [Amazon ECR](02-amazon-ecr.md)의 전체 예제를 참고합니다.

## 보안 체크리스트

### 1. 이미지 스캐닝

Docker Hub는 Docker Scout, ECR은 AWS 네이티브 Basic 또는 Inspector 기반 Enhanced Scanning, Harbor는 구성한 Trivy/외부 스캐너를 사용합니다. 스캔 비용·지원 이미지·재스캔 주기·DB 신선도를 확인합니다. `auto_scan`과 배포 차단은 별개이고, 스캔 실패·미완료를 취약점 0개로 해석하지 않습니다. [ECR](02-amazon-ecr.md)과 [Harbor](03-harbor.md)의 현재 스캔 설정을 따릅니다.

### 2. Admission Controller (서명된 이미지만 허용)

[이미지 보안](../security/07-image-security.md)의 서명 검증과 [Kyverno](../security/01-kyverno-policy-management.md)의 Registry 제한 정책을 조합합니다. Registry allowlist는 서명 검증이나 취약점 스캔을 대신하지 않습니다. 취약점 attestation을 검사하려면 신뢰할 서명자, 실제 predicate 스키마·필드, 스캔 시각/신선도까지 명시합니다. 존재하지 않는 `criticalCount` 필드를 추측하거나 잘린 공개키를 그대로 적용하지 않습니다.

일반·init·ephemeral container와 CREATE/UPDATE 범위를 시험하고 Audit에서 결과를 확인한 뒤 Enforce로 전환합니다. Gatekeeper constraint는 해당 ConstraintTemplate이 먼저 설치되어야 합니다.

### 3. 최소 권한 원칙

다음은 지정된 ECR repository의 이미지 풀 정책입니다. `GetAuthorizationToken`은 repository 리소스 권한을 지원하지 않아 `Resource: "*"`가 필요하지만 실제 pull 작업은 ARN으로 제한합니다. EKS에서는 노드 역할 또는 Fargate Pod execution role에 적용합니다. 애플리케이션의 IRSA/Pod Identity 역할은 자신의 초기 이미지 풀 권한을 대신하지 않습니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RegistryToken",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "PullApprovedRepositories",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": [
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/myapp-prod",
        "arn:aws:ecr:ap-northeast-2:123456789012:repository/base-images/*"
      ]
    }
  ]
}
```

Harbor에는 프로젝트 범위의 pull 전용 Robot을 사용하고 만료·회전을 관리합니다. [Harbor](03-harbor.md)의 현재 `/api/v2.0/robots` 스키마와 namespace별 imagePullSecrets 절차를 사용합니다.

### 4. 네트워크 정책

Kubernetes NetworkPolicy는 선택한 Pod의 네트워크 트래픽을 제어합니다. 노드 kubelet/containerd의 이미지 풀을 Pod egress 정책으로 제한할 수 있다고 가정하지 않습니다. 허용 Registry는 Admission에서 검사하고, 노드의 Registry·DNS·ECR API/DKR·S3 접근은 노드/네트워크 계층에서 제어합니다. 애플리케이션 Pod의 egress 정책에는 실제 업무·DNS 통신도 반영합니다.

### 5. 자격 증명 관리

다음은 External Secrets Operator v1 API를 지원하는 CRD와 구성된 ClusterSecretStore를 전제로 합니다. 원격 Secret에는 유효한 Docker config JSON 전체를 저장하며, 문자열을 직접 조립하지 않아 비밀번호의 따옴표·역슬래시도 보존합니다. 생성된 Secret은 같은 namespace의 Pod/ServiceAccount에서 참조합니다.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: registry-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: registry-pull-secret
    creationPolicy: Owner
    template:
      engineVersion: v2
      type: kubernetes.io/dockerconfigjson
      data:
        .dockerconfigjson: "{{ .dockerconfigjson | toString }}"
  data:
  - secretKey: dockerconfigjson
    remoteRef:
      key: harbor-pull-dockerconfigjson
```

ECR의 12시간 토큰을 고정 문자열로 보관해 주기적으로 복사하는 것만으로는 재발급되지 않습니다. EKS의 네이티브 이미지 풀 역할이나 명시적으로 구성한 ECR 토큰 생성기를 사용합니다. Secret 관리 계층의 접근 권한·암호화·회전 실패도 감시합니다.

## CI/CD 통합 패턴

### GitHub Actions + ECR

다음은 Linux/amd64 단일 플랫폼을 로컬 Docker에 빌드하고 **그 이미지**를 Trivy로 검사한 뒤 ECR에 push·서명하는 예제입니다. 실제 ECR repository, OIDC IAM 역할의 `aud`/`sub` 제한, push 권한, 지원되는 Runner를 먼저 준비합니다. 액션은 검토한 릴리스 commit으로 고정했습니다. 같은 commit 태그를 재빌드해 불변 태그와 충돌하면 기존 검증 digest를 재사용하거나 새 build ID를 부여합니다.

```yaml
name: Build scan and publish to ECR
on:
  push:
    branches: [main]
    tags: ['v*']
permissions:
  contents: read
  id-token: write
env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: myapp
jobs:
  publish:
    runs-on: ubuntu-24.04
    steps:
    - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
    - uses: aws-actions/configure-aws-credentials@cbe3b392738ccf3f987d68400dafcf4b0624a56c # v6.2.4
      with:
        role-to-assume: arn:aws:iam::123456789012:role/github-actions-ecr
        aws-region: ${{ env.AWS_REGION }}
    - uses: aws-actions/amazon-ecr-login@03f1aad4c6c7ffd436567f42f9384779290529bd # v2.1.7
      id: login
    - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
    - uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
      with:
        context: .
        platforms: linux/amd64
        load: true
        push: false
        tags: ${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
      with:
        version: v0.74.0
        image-ref: ${{ steps.login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
        scan-type: image
        scanners: vuln
        exit-code: '1'
        severity: HIGH,CRITICAL
    - name: Publish scanned image and record digest
      id: publish
      env:
        REGISTRY: ${{ steps.login.outputs.registry }}
      run: |
        set -euo pipefail
        IMAGE="$REGISTRY/$ECR_REPOSITORY"
        docker push "$IMAGE:$GITHUB_SHA"
        DIGEST=$(aws ecr describe-images --repository-name "$ECR_REPOSITORY" \
          --image-ids "imageTag=$GITHUB_SHA" --query 'imageDetails[0].imageDigest' --output text)
        [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
        printf 'image=%s@%s\n' "$IMAGE" "$DIGEST" >> "$GITHUB_OUTPUT"
    - uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2
    - name: Sign the published digest with the job OIDC identity
      env:
        SIGNED_IMAGE: ${{ steps.publish.outputs.image }}
      run: cosign sign --yes "$SIGNED_IMAGE"
```

멀티 아키텍처 릴리스는 모든 플랫폼을 스캔하고 최종 index digest를 승격합니다. `publish.outputs.image`의 digest를 배포와 서명 검증에 사용하며, 단순 SemVer 태그 검색만으로 승인되지 않은 이미지를 자동 배포하지 않습니다. Keyless 검증에는 해당 workflow의 OIDC issuer·identity를 제한한 Admission 정책이 필요합니다. SARIF를 추가하면 Code Scanning 사용 조건과 `security-events: write` 권한도 설정합니다.

### GitLab CI + Harbor

이 Docker executor 예제는 TLS를 사용하는 DinD를 전제로 합니다. 격리된 전용 Runner에서 필요한 privileged 설정과 `/certs/client` 공유 볼륨을 준비합니다. `HARBOR_USERNAME`·`HARBOR_PASSWORD`는 보호된 마스킹 변수의 프로젝트 Robot이며, 모든 Runner가 Harbor CA를 신뢰해야 합니다. 빌드 tar가 scan과 publish에 같은 artifact로 전달되고 publish는 scan 성공 후에만 실행됩니다.

```yaml
stages: [build, scan, publish]
workflow:
  rules:
    - if: '$CI_COMMIT_BRANCH == "main" || $CI_COMMIT_TAG'
variables:
  HARBOR_HOST: harbor.example.com
  IMAGE_NAME: harbor.example.com/myapp/app
  DOCKER_HOST: tcp://docker:2376
  DOCKER_TLS_CERTDIR: /certs
  DOCKER_TLS_VERIFY: "1"
  DOCKER_CERT_PATH: /certs/client
.docker:
  image: docker:29.8.0-cli
  services:
    - name: docker:29.8.0-dind
      alias: docker
build:
  extends: .docker
  stage: build
  script:
    - docker build -t "$IMAGE_NAME:$CI_COMMIT_SHA" .
    - docker save "$IMAGE_NAME:$CI_COMMIT_SHA" -o image.tar
  artifacts:
    paths: [image.tar]
    expire_in: 1 day
scan:
  stage: scan
  image:
    name: aquasec/trivy:0.74.0
    entrypoint: [""]
  needs:
    - job: build
      artifacts: true
  script:
    - trivy image --input image.tar --exit-code 1 --severity HIGH,CRITICAL
publish:
  extends: .docker
  stage: publish
  needs:
    - job: build
      artifacts: true
    - job: scan
      artifacts: false
  script:
    - printf '%s' "$HARBOR_PASSWORD" | docker login "$HARBOR_HOST" --username "$HARBOR_USERNAME" --password-stdin
    - docker load -i image.tar
    - docker push "$IMAGE_NAME:$CI_COMMIT_SHA"
```

### 배포와 이미지 업데이트

스캔·서명 통과 후 GitOps repository에 검증한 digest를 반영하고 승인·서명 검증·롤아웃 상태 확인을 거쳐 배포합니다. Argo CD Image Updater 1.x는 `ImageUpdater` CR을 사용하므로 오래된 Application annotation만 복사하지 않습니다. 해당 버전의 CRD와 Argo CD 접근 권한, Registry 인증, Git write-back 자격 증명을 준비하고 환경의 승인 정책에 맞게 구성합니다.

![이미지를 빌드·검사하고 통과한 아티팩트만 게시·배포하는 파이프라인. Registry 기반 스캐너를 사용하는 경우 격리된 staging repository에 먼저 push할 수도 있다.](../.gitbook/assets/ko-container-registry-04-best-practices-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-04-best-practices-1.html)

## skopeo를 활용한 이미지 관리

[skopeo](https://github.com/containers/skopeo)는 컨테이너 이미지를 검사, 복사, 동기화할 수 있는 CLI 도구입니다. Docker 데몬 없이 동작하며, root 권한이 필요하지 않아 CI/CD 파이프라인과 에어갭 환경에서 특히 유용합니다.

### skopeo 설치

```bash
# RHEL/CentOS/Amazon Linux
sudo yum install -y skopeo

# Ubuntu/Debian
sudo apt-get install -y skopeo

# macOS
brew install skopeo
```

### skopeo inspect — 원격 이미지 검사

이미지를 pull하지 않고 메타데이터를 확인할 수 있습니다:

```bash
# Docker Hub 이미지 검사
skopeo inspect docker://docker.io/library/nginx:1.30.4

# ECR 이미지 검사 (AWS 인증 필요)
skopeo inspect docker://123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.0.0

# 원시 매니페스트 확인
skopeo inspect --raw docker://docker.io/library/nginx:1.30.4 | jq .

# 특정 아키텍처 매니페스트 확인
skopeo --override-arch arm64 inspect docker://docker.io/library/nginx:1.30.4
```

### skopeo copy — 레지스트리 간 이미지 복사

이미지를 로컬에 pull하지 않고 레지스트리 간 직접 복사합니다:

```bash
# Docker Hub → ECR 복사
skopeo copy --all \
  docker://docker.io/library/nginx:1.30.4 \
  docker://123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/nginx:1.30.4

# ECR → Harbor 복사
skopeo copy --all \
  docker://123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.0.0 \
  docker://harbor.example.com/myapp/backend:v1.0.0

# 포맷 변환 (Docker → OCI)
skopeo copy --all \
  docker://docker.io/library/nginx:1.30.4 \
  oci:nginx-oci:1.30.4

# OCI archive로 저장
skopeo copy --all \
  docker://docker.io/library/nginx:1.30.4 \
  oci-archive:nginx-1.30.4.tar
```

### skopeo sync — 대량 레지스트리 동기화

명시한 태그만 dry run으로 확인한 뒤 동기화합니다. 태그 없이 repository 전체를 지정하면 모든 태그가 복사될 수 있습니다. `images-by-tag-regex` 값은 목록이 아닌 문자열입니다. `--scoped`는 원본 Registry·경로를 보존해 이름 충돌을 줄이며, 목적지 프로젝트/repository 생성·인증은 별도 준비합니다.

```bash
cat > sync-manifest.yaml <<'YAML'
docker.io:
  images:
    library/nginx:
      - "1.30.4"
  images-by-tag-regex:
    library/busybox: '^1\.37\.0$'
YAML
# Preview exact source/destination paths before creating target repositories.
skopeo sync --all --scoped --dry-run --src yaml --dest docker \
  sync-manifest.yaml harbor.internal/mirror
# After reviewing the preview and preparing destinations, remove --dry-run.
```

### 에어갭 환경 이미지 전송

skopeo는 에어갭 환경으로의 이미지 전송에 최적화되어 있습니다:

```bash
# 1단계: 온라인 환경에서 이미지를 tar로 내보내기
skopeo copy --all docker://docker.io/library/nginx:1.30.4 oci-archive:nginx-1.30.4.tar
skopeo copy --all docker://docker.io/library/redis:7-alpine oci-archive:redis-7.tar
skopeo copy --all docker://registry.k8s.io/pause:3.10 oci-archive:pause-3.10.tar

# 2단계: USB/보안 전송으로 에어갭 환경에 전달

# 3단계: 에어갭 환경에서 Harbor로 import
skopeo copy --all oci-archive:nginx-1.30.4.tar \
  docker://harbor.internal/library/nginx:1.30.4
skopeo copy --all oci-archive:redis-7.tar \
  docker://harbor.internal/library/redis:7-alpine
skopeo copy --all oci-archive:pause-3.10.tar \
  docker://harbor.internal/k8s/pause:3.10
```

> **팁:** `docker save/load`와 달리 skopeo는 Docker 데몬 없이 동작하므로, 서버에 Docker가 설치되지 않은 에어갭 환경에서도 사용할 수 있습니다.

### 도구 비교

| 도구 | 이 문서에서의 용도 | 확인할 조건 |
|---|---|---|
| Skopeo | 원격 inspect, copy/sync, OCI archive | 인증, manifest 변환, `--all`, referrer 지원 |
| Docker/Buildx | 빌드, manifest 검사, push | Docker daemon 또는 builder 구성; rootless도 지원 |
| crane | 원격 이미지 조회·복사 | 설치 버전의 copy/export 및 서명 지원 |
| ctr | containerd 이미지 저장소·import/export | 런타임 socket 권한, namespace, 플랫폼 선택 |

`--all`은 플랫폼 manifest 선택 옵션이며 서명·SBOM 등 referrer 전체 복사의 보장이 아닙니다. digest 보존이 필요하면 `--preserve-digests`를 사용하고 실패를 무시하지 않습니다. 에어갭 반입은 [Harbor](03-harbor.md)의 매핑·체크섬·DB·CA·복구 검증 절차와 함께 수행합니다.

## 요약

| 카테고리 | 권장 사항 |
|----------|----------|
| **태그** | Immutable, SemVer, :latest 금지 |
| **네이밍** | org/app:tag, 환경 접두사 |
| **미러링** | Pull-through cache, 내부 미러 |
| **DR** | 멀티 리전 복제, 일간 백업 |
| **비용** | Lifecycle policy, 멀티스테이지 빌드 |
| **보안** | 스캐닝, 서명, Admission Controller |
| **CI/CD** | GitHub Actions/GitLab CI + Trivy |

---

## 참고 자료

- [OCI Image Spec](https://github.com/opencontainers/image-spec)
- [Semantic Versioning](https://semver.org/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Cosign Documentation](https://docs.sigstore.dev/quickstart/quickstart-cosign/)
- [Kyverno Image Verification](https://kyverno.io/docs/policy-types/cluster-policy/verify-images/overview/)
- [ArgoCD Image Updater](https://argocd-image-updater.readthedocs.io/)

### 검토 근거

- [Docker Hub immutable tags](https://docs.docker.com/docker-hub/repos/manage/hub-images/immutable-tags/)
- [Image tag grammar](https://github.com/distribution/reference/blob/main/regexp.go)
- [Containerd registry configuration](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
- [Skopeo copy](https://github.com/containers/skopeo/blob/main/docs/skopeo-copy.1.md)
- [Skopeo sync](https://github.com/containers/skopeo/blob/main/docs/skopeo-sync.1.md)
- [External Secrets Docker config](https://external-secrets.io/latest/guides/common-k8s-secret-types/)
- [Argo CD Image Updater 1.3 image configuration](https://github.com/argoproj-labs/argocd-image-updater/blob/v1.3.0/docs/configuration/images.md)
- [Docker build-push action](https://github.com/docker/build-push-action/tree/v7.3.0)
- [Trivy action](https://github.com/aquasecurity/trivy-action/tree/v0.36.0)
- [GitLab Docker-in-Docker TLS](https://docs.gitlab.com/ci/docker/using_docker_build/)
