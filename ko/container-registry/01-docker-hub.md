# Docker Hub

> **마지막 업데이트**: 2026년 9월 11일

## 개요

Docker Hub는 Docker CLI에서 레지스트리를 생략할 때 사용하는 기본 이미지 레지스트리입니다. Docker Official Images, Verified Publishers, 커뮤니티 이미지를 제공하며, 개인 및 팀을 위한 프라이빗 저장소 기능도 지원합니다.

![Docker Hub의 세 가지 이미지 신뢰 등급인 Official Images, Verified Publishers, Community Images를 나란히 배치하여 각 등급의 검증 주체와 nginx, bitnami/, user/myapp 같은 예시 이미지를 보여준다.](../.gitbook/assets/ko-container-registry-01-docker-hub-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-01-docker-hub-0.html)

---

## Docker Hub 플랜 비교

### 플랜별 기능

| 기능 | Personal | Pro | Team | Business |
|------|------|-----|------|----------|
| **가격** | 기본 무료 할당 | 월간 $11 / 연간 약정 월 $9 | 월간 $16 / 연간 약정 월 $15, 사용자당 | 현재 요금표·계약 확인 |
| **공개 저장소** | 무제한 | 무제한 | 무제한 | 무제한 |
| **프라이빗 저장소** | 1개 | 무제한 | 무제한 | 무제한 |
| **팀 기능** | ❌ | ❌ | ✅ | ✅ |
| **보안·관리 기능** | 플랜별 범위 확인 | 플랜별 범위 확인 | 조직 기능 확인 | SSO·감사 등 계약 범위 확인 |
| **기존 Automated Builds 병렬 수** | 미지원 | 5 | 15 | 15 |

요금은 2026-09-11 [공식 요금표](https://www.docker.com/pricing/)의 USD 표시 기준이며 세금·결제 조건을 별도로 확인합니다. Automated Builds는 폐기 예정 기능이며 2027-04-01 종료가 공지돼 있습니다. 새 빌드는 아래 외부 CI/CD 예제를 사용합니다.

### Rate Limits (Pull 제한)

아래는 [공식 사용량 문서](https://docs.docker.com/docker-hub/usage/)의 6시간 기준 표입니다. 실제 계정의 조건과 응답 헤더를 확인하고, 별도의 abuse/fair-use 제한도 고려합니다:

| 인증 상태 | Rate Limit | 기준 |
|----------|------------|------|
| **익명** | 100 pulls / 6시간 | IPv4 주소 또는 IPv6 /64 대역당 |
| **Personal (인증됨)** | 200 pulls / 6시간 | 계정에 귀속되는 사용량 |
| **Pro** | 무제한 | - |
| **Team** | 무제한 | - |
| **Business** | 무제한 | - |

**Rate Limit 확인 방법:**

```bash
# 현재 rate limit 상태 확인
TOKEN=$(curl -fsS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" | jq -er .token)

curl -s -H "Authorization: Bearer $TOKEN" \
  -I "https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest" 2>&1 | \
  grep -i ratelimit

# 출력 예시:
# ratelimit-limit: 100;w=21600
# ratelimit-remaining: 95;w=21600
```

---

## Kubernetes에서 Docker Hub 사용

### imagePullSecrets 설정

**1. Docker Hub 자격 증명으로 Secret 생성:**

Secret과 이를 사용하는 Pod/ServiceAccount는 같은 namespace에 있어야 합니다. 운영에서는 읽기 전용 PAT를 사용하고 셸 히스토리나 CI 로그에 값을 직접 적지 않습니다.

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<username> \
  --docker-password=<password-or-access-token> \
  --docker-email=<email> \
  -n default
```

**2. Pod에서 Secret 참조:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  namespace: default
spec:
  containers:
  - name: myapp
    image: username/myapp:v1.0.0
  imagePullSecrets:
  - name: dockerhub-secret
```

**3. ServiceAccount에 기본 imagePullSecrets 설정:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: default
imagePullSecrets:
- name: dockerhub-secret
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: myapp-sa
      containers:
      - name: myapp
        image: username/myapp:v1.0.0
        # imagePullSecrets 자동 적용
```

### Access Token 사용 (권장)

비밀번호 대신 Access Token 사용을 권장합니다:

```bash
# Docker Hub > Account Settings > Security > Access Tokens

# Access Token으로 Secret 생성
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<username> \
  --docker-password=<access-token> \
  -n default
```

**Access Token 권한 범위:**
- **Read-only**: 이미지 pull만 허용
- **Read & Write**: pull + push 허용
- **Read, Write & Delete**: 전체 권한

---

## Docker Hub Rate Limit 대응 전략

![Docker Hub Rate Limit 발생 여부를 확인한 뒤 환경에 따라 ECR Pull-through Cache, Harbor Pull Replication, containerd 미러 중 하나를 적용하거나 인증된 Pull로 사전에 예방하여 최종적으로 Rate Limit을 해소하는 의사결정 흐름을 보여준다.](../.gitbook/assets/ko-container-registry-01-docker-hub-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-01-docker-hub-1.html)

### 전략 1: Pull-through Cache (containerd)

containerd 자체를 캐시 서버로 만드는 설정은 아닙니다. 별도로 구성한 레지스트리 미러를 가리키도록 설정합니다. 폐기된 `registry.mirrors` 대신 현재 [hosts.toml 설정](https://github.com/containerd/containerd/blob/main/docs/hosts.md)을 사용합니다.

```toml
# containerd 1.x: /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
```

```toml
# containerd 2.x: 위의 1.x 플러그인 설정 대신 사용
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
```

```toml
# /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"
[host."https://mirror.gcr.io"]
  capabilities = ["pull"]
```

공개 미러는 모든 이미지나 프라이빗 이미지를 보장하지 않습니다. 태그→digest 해석(`resolve`) 권한은 신뢰할 수 있는 미러에만 부여합니다. 관리형 노드에서는 지원되는 부트스트랩/노드 설정 경로를 사용합니다.

### 전략 2: Amazon ECR Pull-through Cache

ECR을 Docker Hub의 프록시 캐시로 사용합니다. Docker Hub 자격 증명은 동일 계정·리전의 `ecr-pullthroughcache/` 접두어를 가진 Secrets Manager secret에 먼저 저장하고 실제 ARN을 사용합니다.

```bash
# 이름이 ecr-pullthroughcache/dockerhub인 secret을 먼저 생성한 예
PTC_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id ecr-pullthroughcache/dockerhub --region ap-northeast-2 \
  --query ARN --output text)
# ECR pull-through cache 규칙 생성
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub \
  --upstream-registry-url registry-1.docker.io \
  --credential-arn "$PTC_SECRET_ARN" \
  --region ap-northeast-2

# 사용 예시 (원본 -> 캐시)
# docker.io/library/nginx:latest
# -> 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/docker-hub/library/nginx:latest
```

**Kubernetes에서 사용:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        # ECR pull-through cache 사용
        image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/docker-hub/library/nginx:1.30.4
```

### 전략 3: Harbor Pull Replication

Harbor에서 Docker Hub registry endpoint와 대상 프로젝트를 만든 뒤 필요한 이미지를 주기적으로 복제합니다. 아래는 UI에 설정할 조건을 설명하는 표기이며, 실제 Harbor API payload나 Kubernetes 매니페스트가 아닙니다:

```yaml
# Harbor replication rule
Source: docker.io
Destination: harbor.internal/docker-cache
Filter:
  - library/nginx
  - library/redis
  - bitnami/**
Trigger: Scheduled (every 6 hours)
```

### 전략 4: 인증된 Pull 사용

각 namespace에서 실제 사용하는 ServiceAccount에 pull 자격 증명을 설정합니다. `kube-system`의 default ServiceAccount를 수정해도 다른 namespace나 다른 ServiceAccount에 전파되지 않으며 이미 생성된 Pod도 갱신하지 않습니다.

```yaml
# default namespace의 default ServiceAccount를 쓰는 새 Pod에 적용
apiVersion: v1
kind: ServiceAccount
metadata:
  name: default
  namespace: default
imagePullSecrets:
- name: dockerhub-secret
```

---

## 자동화된 빌드 (Automated Builds)

Docker Hub Automated Builds는 **폐기 예정**이며 2027-04-01에 종료됩니다. 아래 설정·훅은 기존 GitHub/Bitbucket 연동을 이해하기 위한 레거시 참고입니다. GitLab은 GitLab CI로 이미지를 빌드해 push하며, 새 파이프라인은 [공식 마이그레이션 안내](https://docs.docker.com/docker-hub/repos/manage/builds/)를 따릅니다.

### GitHub 연동 설정

**1. Docker Hub에서 GitHub 계정 연결:**
- Docker Hub > Account Settings > Linked Accounts > GitHub

**2. Automated Build 저장소 생성:**
- Create Repository > GitHub에서 저장소 선택
- Build Rules 설정

**Build Rules 예시:**

| Source Type | Source | Docker Tag | Dockerfile Location |
|-------------|--------|------------|---------------------|
| Branch | main | latest | /Dockerfile |
| Branch | develop | dev | /Dockerfile |
| Tag | /^v([0-9.]+)$/ | {\1} | /Dockerfile |

### 빌드 훅 (Build Hooks)

빌드 프로세스를 커스터마이징하는 훅 스크립트:

```bash
# hooks/build
#!/bin/bash
# 커스텀 빌드 명령
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  -t $IMAGE_NAME .
```

```bash
# hooks/post_push
#!/bin/bash
# 추가 태그 푸시
docker tag $IMAGE_NAME $DOCKER_REPO:$SOURCE_COMMIT
docker push $DOCKER_REPO:$SOURCE_COMMIT
```

### GitHub Actions 대안 (권장)

Docker Hub Automated Builds 대신 GitHub Actions 사용:

```yaml
# .github/workflows/docker-publish.yml
name: Docker Build and Push

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  REGISTRY: docker.io
  IMAGE_NAME: my-dockerhub-org/myapp # 미리 생성한 Docker Hub 리포지터리로 변경

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: docker/setup-buildx-action@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=semver,pattern={{version}}
          type=sha,prefix=

    - name: Build and push
      uses: docker/build-push-action@v6
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
```

---

## 공개 이미지 보안 사례

### Supply Chain Attack 사례

**사례 1: Typosquatting (가상의 이름 비교이며 실제 게시자 평가가 아님)**
```text
approved-vendor/myapp
approved-vend0r/myapp   # 문자 o와 숫자 0의 차이
```

**사례 2: 계정 탈취**
- 인기 이미지 메인테이너 계정 탈취
- 악성 코드가 포함된 새 버전 푸시

**사례 3: Base Image 오염**
```dockerfile
# 검증되지 않은 base image
FROM some-random-user/python:3.11  # 위험!
```

### 안전한 이미지 선택 가이드

**1. Official Images 우선:**

```text
공식 이미지 이름 예: docker.io/library/nginx, docker.io/library/postgres
실제 배포: 현재 유지보수 중인 버전과 검증한 전체 digest를 선택
```

**2. Verified Publishers:**

```bash
# 게시자의 현재 카탈로그에서 선택한 실제 태그/digest를 먼저 확인
docker buildx imagetools inspect "$VERIFIED_VENDOR_IMAGE"
docker pull "$VERIFIED_VENDOR_IMAGE"
```

게시자 배지가 특정 태그의 현재 존재 여부나 취약점 부재를 보장하지는 않습니다. 예전 Bitnami/Grafana 태그나 카탈로그 접근 조건을 그대로 가정하지 않습니다.

**3. 이미지 검증:**

```bash
# 이미지 다이제스트 확인
docker pull nginx:1.30.4
docker image inspect nginx:1.30.4 --format='{{index .RepoDigests 0}}'
# 출력된 전체 repository@sha256:... 값을 workload의 image에 사용
```

**4. Content Trust의 적용 범위 확인:**

```bash
# Docker Content Trust 활성화
DOCKER_CONTENT_TRUST=1 docker pull "$DCT_SIGNED_IMAGE"
# DCT/Notary 메타데이터가 구성된 이미지에만 적용
```

Docker Official/Verified 배지는 특정 태그가 DCT로 서명됐거나 취약점이 없다는 보장이 아닙니다. `DOCKER_CONTENT_TRUST`는 Docker CLI 동작을 바꾸며 Kubernetes/containerd의 pull이나 admission에 자동으로 적용되지 않습니다.

### Kubernetes Admission Control

다음은 **허용한 이미지 출처를 점검하는 정책**이며 서명이나 스캔 결과를 검증하지 않습니다. Kyverno가 설치된 환경의 `registry-demo` namespace에서 Audit 결과를 먼저 확인한 뒤 정책을 운영 요건에 맞게 조정합니다.

```yaml
# Kyverno 출처 제한 예시 (서명 검증 정책이 아님)
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: allowed-image-sources
spec:
  validationFailureAction: Audit
  rules:
  - name: verify-image-source
    match:
      any:
      - resources:
          kinds:
          - Pod
          namespaces:
          - registry-demo
    validate:
      message: "Use an approved, fully qualified image reference."
      pattern:
        spec:
          =(initContainers):
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
          =(ephemeralContainers):
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
          containers:
          - image: "docker.io/library/* | docker.io/my-approved-org/*"
```

서명 검증에는 신뢰할 공개키/서명자와 digest 검증이 필요하며, 취약점 attestation 검증에는 신뢰할 스캐너 서명과 허용 기준이 추가로 필요합니다. [이미지 보안](../security/07-image-security.md)과 [Kyverno 출처 제한 예제](https://github.com/kyverno/policies/tree/main/best-practices/restrict-image-registries)를 구분해 읽습니다.

---

## Docker Hub API 활용

### 인증

기존 `/v2/users/login`은 deprecated입니다. [공식 Hub API](https://docs.docker.com/reference/api/hub/latest/)의 `/v2/auth/token`은 `identifier`와 `secret`을 받고 `access_token`을 반환합니다. 이 토큰은 10분 후 만료되며 Registry pull용 `auth.docker.io` 토큰과 별개입니다. 비밀번호 대신 필요한 권한만 가진 PAT를 사용합니다.

```bash
set -euo pipefail
# Load these from secure shell input or CI secrets; do not commit their values.
: "${DOCKER_USER:?Set Docker Hub username}"
: "${DOCKER_PAT:?Load a Docker Hub personal access token}"
export DOCKER_USER DOCKER_PAT
HUB_TOKEN=$(jq -n '{identifier: env.DOCKER_USER, secret: env.DOCKER_PAT}' | \
  curl -fsS -X POST https://hub.docker.com/v2/auth/token \
    -H 'Content-Type: application/json' --data-binary @- | jq -er '.access_token')
HUB_NAMESPACE=${HUB_NAMESPACE:-$DOCKER_USER}
export HUB_TOKEN HUB_NAMESPACE
```

### 리포지터리와 태그 조회

`HUB_NAMESPACE`는 기본적으로 로그인 사용자이며 조직을 조회하려면 해당 조직명과 권한을 설정합니다. 아래 명령은 권한 범위 내 첫 페이지만 조회합니다. `page_size` 최댓값은 100이며 전체 결과에는 응답의 `next`를 따라가야 합니다.

```bash
: "${DOCKER_REPO:?Set repository name}"
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" \
  "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories?page_size=100" | \
  jq '.results[] | {name, is_private}'

curl -fsS -H "Authorization: Bearer $HUB_TOKEN" \
  "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories/$DOCKER_REPO/tags?page_size=100" | \
  jq '.results[] | {name, last_updated}'
```

### 정리 대상 검토용 전체 태그 목록

첫 100개 태그만 보고 나머지를 삭제하거나, 서버가 특정 정렬을 보장한다고 가정하지 않습니다. 다음 독립 Bash 스크립트는 모든 페이지를 모아 갱신일로 정렬할 뿐 삭제하지 않습니다. 삭제 전에는 실행 중인 workload의 digest, 롤백 보존 기간과 보호 태그를 별도로 확인하고 Hub 관리 화면이나 현재 공식 API에 문서화된 기능을 사용합니다.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${HUB_TOKEN:?Create a current Hub API access token}"
: "${HUB_NAMESPACE:?Set namespace}"
: "${DOCKER_REPO:?Set repository}"
registry_tag_index=$(mktemp)
trap 'rm -f "$registry_tag_index"' EXIT
registry_next="https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories/$DOCKER_REPO/tags?page_size=100"
while [ -n "$registry_next" ]; do
  case "$registry_next" in
    https://hub.docker.com/*) ;;
    *) printf '%s\n' 'Unexpected pagination host' >&2; exit 1 ;;
  esac
  registry_page=$(curl -fsS -H "Authorization: Bearer $HUB_TOKEN" "$registry_next")
  printf '%s' "$registry_page" | jq -c '.results[]' >> "$registry_tag_index"
  registry_next=$(printf '%s' "$registry_page" | jq -r '.next // empty')
done
# Read-only inventory. No DELETE request is made.
jq -s 'sort_by(.last_updated // "") | reverse | .[] | {name, last_updated}' "$registry_tag_index"
```

### 취약점 확인

```bash
# Docker Scout 사용 가능 범위는 계정/플랜/리포지터리 설정을 확인
# 이 예제는 문서화된 CLI를 사용하며 임의의 /tags/TAG/vulnerabilities API를 가정하지 않음
docker scout cves nginx:1.30.4
```

### 프라이빗 리포지터리 생성

조직 namespace를 관리할 권한과 플랜의 리포지터리 허용량을 먼저 확인합니다.

```bash
jq -n --arg ns "$HUB_NAMESPACE" \
  '{namespace:$ns, name:"myapp", description:"My application", is_private:true}' | \
  curl -fsS -X POST "https://hub.docker.com/v2/namespaces/$HUB_NAMESPACE/repositories" \
    -H "Authorization: Bearer $HUB_TOKEN" \
    -H 'Content-Type: application/json' --data-binary @-
```

---

## CI/CD 통합

### GitLab CI 예시

아래는 Docker executor 러너의 privileged DinD 및 `/certs/client` 공유가 준비됐다는 전제입니다. [GitLab의 TLS DinD 설정](https://docs.gitlab.com/ci/docker/using_docker_build/)을 먼저 적용합니다. 스캔은 Docker socket 마운트 대신 빌드 산출물 tar를 읽습니다. 운영에서는 CI 이미지도 검증한 digest로 고정합니다.

```yaml
# .gitlab-ci.yml
stages:
  - build
  - scan
  - push

variables:
  DOCKER_IMAGE: myapp:$CI_COMMIT_SHA
  DOCKER_HOST: tcp://docker:2376
  DOCKER_TLS_CERTDIR: "/certs"
  DOCKER_TLS_VERIFY: "1"
  DOCKER_CERT_PATH: "/certs/client"

build:
  stage: build
  image: docker:29.8.0-cli
  services:
    - name: docker:29.8.0-dind
      alias: docker
  script:
    - docker build -t "$DOCKER_IMAGE" .
    - docker save "$DOCKER_IMAGE" > image.tar
  artifacts:
    paths:
      - image.tar

scan:
  stage: scan
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy image --input image.tar --exit-code 1 --severity HIGH,CRITICAL

push:
  stage: push
  image: docker:29.8.0-cli
  services:
    - name: docker:29.8.0-dind
      alias: docker
  script:
    - docker load < image.tar
    - printf '%s' "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
    - docker tag "$DOCKER_IMAGE" "$DOCKERHUB_USERNAME/myapp:$CI_COMMIT_TAG"
    - docker push "$DOCKERHUB_USERNAME/myapp:$CI_COMMIT_TAG"
  only:
    - tags
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-creds')
        IMAGE_NAME = 'username/myapp'
    }

    stages {
        stage('Build') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
            }
        }

        stage('Scan') {
            steps {
                sh "trivy image --exit-code 1 --severity HIGH,CRITICAL ${IMAGE_NAME}:${BUILD_NUMBER}"
            }
        }

        stage('Push') {
            steps {
                sh 'printf "%s" "$DOCKERHUB_CREDENTIALS_PSW" | docker login -u "$DOCKERHUB_CREDENTIALS_USR" --password-stdin'
                sh "docker push ${IMAGE_NAME}:${BUILD_NUMBER}"
                sh "docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest"
                sh "docker push ${IMAGE_NAME}:latest"
            }
        }
    }

    post {
        always {
            sh "docker logout"
        }
    }
}
```

---

## 모범 사례

### 1. 보안

```yaml
# ✅ 권장
- Official Images 또는 Verified Publishers 사용
- 이미지 다이제스트로 고정
- 런타임에 맞는 서명·attestation 검증 정책 구성
- 정기적인 취약점 스캐닝

# ❌ 비권장
- 검증되지 않은 커뮤니티 이미지
- :latest 태그 사용
- 비밀번호 직접 사용 (Access Token 사용)
```

### 2. Rate Limit 관리

```yaml
# ✅ 권장
- Pro/Team 플랜 (프로덕션)
- Pull-through cache 구성
- 인증된 pull 사용

# ❌ 비권장
- 익명 pull (프로덕션)
- 캐시 없이 직접 pull
```

### 3. 저장소 관리

```yaml
# ✅ 권장
- 의미 있는 저장소/태그 명명
- README 및 설명 작성
- 불필요한 태그 정리

# ❌ 비권장
- 개인 정보 포함 저장소 이름
- 설명 없는 저장소
- 태그 무분별한 누적
```

### 4. 자격 증명 관리

```bash
# Access Token 생성 (권장)
# Docker Hub > Account Settings > Security > New Access Token

# 범위 최소화
# - CI/CD push: Read & Write
# - Kubernetes pull: Read-only

# 정기적 로테이션
# - 90일마다 토큰 갱신
```

---

## 요약

| 항목 | 권장 사항 |
|------|----------|
| **플랜** | 사용량·팀 권한·지원 요구에 맞는 플랜 선택 |
| **이미지** | Official Images, Verified Publishers |
| **태그** | 버전 고정, 다이제스트 사용 |
| **인증** | Access Token (비밀번호 대신) |
| **Rate Limit** | Pull-through cache, 인증된 pull |
| **보안** | 서명·attestation 검증, 취약점 스캐닝 |
| **CI/CD** | GitHub Actions 권장 |

---

## 참고 자료

- [Docker Hub 공식 문서](https://docs.docker.com/docker-hub/)
- [Docker Hub Rate Limits](https://docs.docker.com/docker-hub/usage/pulls/)
- [Docker Official Images](https://hub.docker.com/search?q=&type=image&image_filter=official)
- [Docker Content Trust](https://docs.docker.com/engine/security/trust/)
- [Docker Scout](https://docs.docker.com/scout/)
- [Docker Hub API](https://docs.docker.com/reference/api/hub/latest/)
- [containerd 레지스트리 호스트 설정](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
- [ECR Pull-through Cache 규칙](https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache-creating-rule.html)
