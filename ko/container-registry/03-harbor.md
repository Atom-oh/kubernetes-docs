# Harbor

> **마지막 업데이트**: 2026년 9월 11일

## 개요

Harbor는 CNCF Graduated 프로젝트로, 오픈소스 컨테이너 레지스트리입니다. 보안, 정책, 역할 기반 접근 제어를 제공하며, 에어갭(폐쇄망) 환경의 내부 이미지 저장소로도 사용할 수 있습니다.

### 아키텍처

![Portal이 Core에 연결되고 Core가 Registry, Job Service, PostgreSQL, Redis로 뻗어나가며, Job Service가 Trivy 스캐너와 연결되는 Harbor 내부 구조를 보여준다.](../.gitbook/assets/ko-container-registry-03-harbor-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-03-harbor-0.html)

다이어그램 내용은 한국어이며 뷰어의 고정 조작 버튼은 영어로 표시됩니다.

### 주요 컴포넌트

| 컴포넌트 | 역할 | 설명 |
|----------|------|------|
| **Core** | API 및 인증 | 사용자 인증, 프로젝트 관리, API 제공 |
| **Registry** | 이미지 저장 | OCI Distribution API 기반 |
| **Job Service** | 비동기 작업 | 복제, GC, 스캐닝 작업 처리 |
| **Portal** | Web UI | 관리 대시보드 |
| **Trivy** | 취약점 스캐닝 | 이미지 보안 스캔 |
| **PostgreSQL** | 메타데이터 | 프로젝트, 사용자, 정책 저장 |
| **Redis** | 캐시 | 세션, 작업 큐 |

---

## Helm을 사용한 설치

2026-09-11 검토 기준은 **Harbor 2.15.2 / Helm Chart 1.19.2**입니다. 앱 버전과 Chart 버전은 다릅니다. 다음은 외부 HA 데이터베이스·Redis·공유 스토리지를 준비한 환경의 구성 예시이며, 값 파일만으로 이 의존성을 생성하지 않습니다.

### 사전 요구사항

- 지원되는 Kubernetes·Helm 버전, DNS, 유지보수 중인 Ingress Controller와 해당 `IngressClass`를 준비합니다. Controller별 업로드 크기·타임아웃·TLS 설정을 확인합니다.
- `harbor` 네임스페이스의 `harbor-tls` Secret에 도메인과 일치하는 인증서·키를 준비합니다. 내부 CA라면 클라이언트와 노드도 신뢰하도록 설정합니다.
- Registry 2개가 서로 다른 노드에서 사용할 수 있는 **RWX PVC 또는 객체 스토리지**가 필요합니다. EBS `gp3`의 RWO PVC를 2개 노드가 공유하는 구성은 HA가 아닙니다.
- 외부 PostgreSQL의 `registry` 데이터베이스와 사용자, `harbor-database` Secret의 `password` 키를 준비합니다. `sslmode: require`는 암호화만 요구하므로 CA·호스트 검증이 필요한 환경은 CA 신뢰 설정과 `verify-full`을 함께 검증합니다.
- Redis는 Harbor가 사용하는 여러 논리 DB를 지원해야 합니다. Redis Cluster처럼 DB 0만 지원하는 모드를 선택하지 않습니다. `harbor-redis` Secret에 `REDIS_PASSWORD`를 준비하고 TLS 연결을 검증합니다. 사설 CA는 Chart의 `caBundleSecretName`으로 제공합니다.

```bash
helm repo add harbor https://helm.goharbor.io
helm repo update
helm show chart harbor/harbor --version 1.19.2
kubectl create namespace harbor
kubectl get ingressclass
kubectl get storageclass
```

### 초기 자격 증명

```bash
# Initial installation only: preserve this encryption key during upgrades.
umask 077
HARBOR_SETUP_DIR=$(mktemp -d)
python3 - "$HARBOR_SETUP_DIR" <<'PYTHON'
import getpass
import pathlib
import secrets
import sys
root = pathlib.Path(sys.argv[1])
(root / "admin-password").write_text(getpass.getpass("Initial Harbor admin password: "))
(root / "secretKey").write_text(secrets.token_hex(8))  # exactly 16 characters
PYTHON
kubectl create secret generic harbor-admin -n harbor \
  --from-file=HARBOR_ADMIN_PASSWORD="$HARBOR_SETUP_DIR/admin-password"
kubectl create secret generic harbor-encryption-key -n harbor \
  --from-file=secretKey="$HARBOR_SETUP_DIR/secretKey"
rm -rf -- "$HARBOR_SETUP_DIR"
```

### 프로덕션 values.yaml

`harbor-values.yaml`로 저장하고 모든 예시 호스트·StorageClass를 실제 값으로 바꿉니다. 리소스 requests/limits와 Pod 분산은 실제 부하·노드 수에 맞춰 추가합니다. `serviceMonitor.enabled`는 Prometheus Operator CRD가 설치된 경우에만 켭니다.

```yaml
expose:
  type: ingress
  tls:
    enabled: true
    certSource: secret
    secret:
      secretName: harbor-tls
  ingress:
    hosts:
      core: harbor.example.com
    className: your-ingress-class
    annotations: {}
externalURL: https://harbor.example.com
existingSecretAdminPassword: harbor-admin
existingSecretSecretKey: harbor-encryption-key
internalTLS:
  enabled: true
  certSource: auto
persistence:
  enabled: true
  resourcePolicy: keep
  persistentVolumeClaim:
    registry:
      storageClass: your-rwx-storage-class
      accessMode: ReadWriteMany
      size: 100Gi
    trivy:
      storageClass: your-storage-class
      size: 10Gi
core:
  replicas: 2
portal:
  replicas: 2
registry:
  replicas: 2
jobservice:
  replicas: 2
  jobLoggers: [database]
database:
  type: external
  external:
    host: harbor-db.internal
    port: "5432"
    username: harbor
    coreDatabase: registry
    existingSecret: harbor-database
    sslmode: require
redis:
  type: external
  external:
    addr: harbor-redis.internal:6379
    existingSecret: harbor-redis
    tlsOptions:
      enable: true
trivy:
  enabled: true
  skipUpdate: false
  skipJavaDBUpdate: false
  offlineScan: false
metrics:
  enabled: true
  serviceMonitor:
    enabled: false
```

### 설치 확인

```bash
helm template harbor harbor/harbor --version 1.19.2   --namespace harbor --values harbor-values.yaml > harbor-rendered.yaml
helm install harbor harbor/harbor --version 1.19.2   --namespace harbor --values harbor-values.yaml --wait --timeout 15m
kubectl get pods,svc,ingress,pvc -n harbor
docker login harbor.example.com --username admin
```

### 업그레이드

업그레이드 전 지원되는 버전 간 경로를 릴리스 노트에서 확인하고, 메타데이터 DB·Registry 데이터·설정·암호화 키를 일관된 시점으로 백업한 뒤 복구를 시험합니다. 새 Chart 값을 기존 값과 비교하고 검증 환경에서 `helm template` 및 마이그레이션을 확인합니다. 대상 Chart 버전을 명시해 `helm upgrade`하며, DB 마이그레이션 후 `helm rollback`만으로 복구된다고 가정하지 않습니다.

Harbor 2.9부터 Notary v1 서버는 제거되었습니다. Cosign·Notation은 외부 서명 도구이며, 생성된 서명은 Registry에 OCI 아티팩트로 저장됩니다.

## 프로젝트 및 RBAC

API 예시는 HTTPS로 접근 가능한 테스트 Harbor와 `curl`, `jq`를 전제로 합니다. `HARBOR_USER`에 필요한 권한을 가진 사용자 이름을 설정합니다. `curl --user "$HARBOR_USER"`는 비밀번호를 대화식으로 묻습니다. 자동화에서는 Secret 관리 도구로 제한된 Robot 자격 증명을 공급하고 로그에 기록하지 않습니다.

```bash
export HARBOR_USER=admin
```

### 프로젝트 유형

| 유형 | 설명 | 사용 사례 |
|------|------|----------|
| **Public** | 인증 없이 pull 가능 | 공개 이미지, 베이스 이미지 |
| **Private** | 인증 필요 | 내부 애플리케이션 |

### 프로젝트 생성

```bash
# Harbor API로 프로젝트 생성
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "project_name": "myapp",
    "metadata": {
      "public": "false",
      "prevent_vul": "true",
      "auto_scan": "true",
      "severity": "high"
    },
    "storage_limit": 10737418240
  }'
```

### 멤버 역할

| 역할 | 권한 | 설명 |
|------|------|------|
| **Project Admin** | 전체 | 프로젝트 설정, 멤버 관리 |
| **Maintainer** | Push/Pull/Delete | 이미지 관리 |
| **Developer** | Push/Pull | 이미지 업로드/다운로드 |
| **Guest** | Pull | 읽기 전용 |
| **Limited Guest** | Pull | 이미지 읽기 가능, 멤버·로그 목록 등은 제한 |

### 멤버 추가

```bash
# 사용자 멤버 추가
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/projects/myapp/members" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "role_id": 2,
    "member_user": {
      "username": "developer1"
    }
  }'

# role_id: 1=Admin, 2=Developer, 3=Guest, 4=Maintainer, 5=Limited Guest
```

### Robot Accounts

CI/CD 파이프라인용 서비스 계정:

```bash
# Robot Account 생성
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/robots" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "ci-pipeline",
    "description": "CI/CD pipeline robot",
    "duration": 90,
    "level": "project",
    "permissions": [
      {
        "kind": "project",
        "namespace": "myapp",
        "access": [
          {"resource": "repository", "action": "push"},
          {"resource": "repository", "action": "pull"}
        ]
      }
    ]
  }'

# 응답에서 name과 secret 저장
# name: robot$myapp+ci-pipeline
# secret: <generated-token>
```

```bash
# Robot Account로 Docker 로그인
read -r -p 'Robot name returned by Harbor: ' ROBOT_NAME
read -r -s -p 'Robot secret: ' ROBOT_SECRET
printf '\n'
printf '%s' "$ROBOT_SECRET" | docker login harbor.example.com \
  --username "$ROBOT_NAME" --password-stdin
unset ROBOT_SECRET
```

---

## 이미지 복제

![외부 레지스트리에서 로컬 Harbor로 이미지를 가져오는 Pull 복제와, 소스 Harbor에서 원격 레지스트리로 내보내는 Push 복제의 방향 차이를 위아래 두 패널로 비교해 보여준다.](../.gitbook/assets/ko-container-registry-03-harbor-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-03-harbor-1.html)

API의 endpoint ID `1`, `3`은 예시입니다. 생성 응답의 `Location` 또는 endpoint 목록에서 실제 ID를 확인해 대입합니다. 스케줄 cron은 초 필드를 포함한 6개 필드(`0 0 0 * * *`)이며 Job Service의 시간대도 확인합니다. Pull 복제는 업스트림에 연결되어야 하며 완전한 폐쇄망의 반입 수단이 아닙니다. 이벤트 복제는 Harbor에서 발생한 push·retag·삭제를 기준으로 하므로 외부 레지스트리 변경을 자동 감지한다고 가정하지 않습니다.

### 복제 모드

| 모드 | 방향 | 설명 | 사용 사례 |
|------|------|------|----------|
| **Pull** | 외부 → Harbor | 외부 이미지를 Harbor로 복제 | 미러링, 캐싱 |
| **Push** | Harbor → 외부 | Harbor 이미지를 외부로 복제 | 배포, DR |

### Pull Replication (미러링)

Docker Hub 이미지를 Harbor로 미러링:

```bash
# 1. Registry Endpoint 생성 (Docker Hub)
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "docker-hub",
    "type": "docker-hub",
    "url": "https://hub.docker.com",
    "credential": {
      "type": "basic",
      "access_key": "<dockerhub-username>",
      "access_secret": "<dockerhub-PAT>"
    }
  }'

# 2. Replication Rule 생성
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "mirror-nginx",
    "src_registry": {
      "id": 1
    },
    "dest_namespace": "docker-cache",
    "filters": [
      {"type": "name", "value": "library/nginx"},
      {"type": "tag", "value": "1.*"}
    ],
    "trigger": {
      "type": "scheduled",
      "trigger_settings": {
        "cron": "0 0 0 * * *"
      }
    },
    "enabled": true,
    "replicate_deletion": false
  }'
```

### Push Replication (DR/배포)

Harbor에서 다른 레지스트리로 복제:

```yaml
# Web UI에서 설정하는 경우:
# 1. Administration > Registries > + New Endpoint
#    - Provider: AWS ECR / Harbor / etc.
#    - Endpoint URL: https://123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
#    - Credential: AWS Access Key

# 2. Projects > myapp > Replication > + New Rule
#    - Name: push-to-ecr
#    - Replication mode: Push-based
#    - Source: myapp/**
#    - Destination: ECR endpoint
#    - Trigger: Event Based (on push)
```

### 스케줄된 복제

```bash
# 매일 자정 복제
curl --fail-with-body -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  --user "$HARBOR_USER" \
  -d '{
    "name": "daily-sync",
    "src_registry": {"id": 1},
    "dest_namespace": "mirror",
    "filters": [
      {"type": "name", "value": "**"},
      {"type": "tag", "value": "v*"}
    ],
    "trigger": {
      "type": "scheduled",
      "trigger_settings": {
        "cron": "0 0 0 * * *"
      }
    },
    "enabled": true
  }'
```

---

## 취약점 스캐닝

### Trivy 통합

Harbor Helm Chart는 Trivy 어댑터를 제공합니다. OCI 이미지의 OS 패키지와 애플리케이션 의존성 취약점을 검사하며, Trivy CLI의 모든 스캔 기능이 Harbor에서 자동 활성화되는 것은 아닙니다. 현재 DB는 OCI 레지스트리에서 내려받으므로 GitHub PAT를 설정하면 모든 DB 제한이 해결된다고 가정하지 않습니다.

```yaml
trivy:
  enabled: true
  skipUpdate: false
  skipJavaDBUpdate: false
  offlineScan: false
  timeout: 5m0s
```

프로젝트의 Auto scan on push는 스캔 시작 설정입니다. 취약한 이미지 pull 차단은 별도의 `prevent_vul` 설정입니다.

### 수동 스캐닝

```bash
# Use the digest of an existing artifact from the Harbor UI/API.
: "${HARBOR_DIGEST:?Set the complete sha256 digest}"
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/${HARBOR_DIGEST}/scan"
curl --fail-with-body --user "$HARBOR_USER" \
  "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/${HARBOR_DIGEST}?with_scan_overview=true"
```

스캔은 비동기 작업입니다. 완료 상태·스캐너 DB 업데이트 시각을 확인하며, 빈 결과를 취약점 0개로 처리하지 않습니다. 위 예제의 단일 경로 `app`과 달리 `team/app`처럼 중첩된 repository 이름은 Harbor API가 요구하는 이중 URL 인코딩을 적용합니다.

### CVE Allowlist

예외는 근거·담당자·만료일을 정해 승인한 CVE에만 적용합니다. 아래 PUT은 프로젝트 allowlist 전체를 바꾸므로 기존 항목과 먼저 병합합니다. 시스템 allowlist 재사용을 끄고, 승인한 식별자와 미래 만료 시각을 입력합니다.

```bash
# Review the existing project allowlist before replacing it.
: "${APPROVED_CVE:?Set an approved CVE identifier}"
: "${ALLOWLIST_EXPIRES_AT:?Set a future Unix timestamp in seconds}"
jq -n --arg cve "$APPROVED_CVE" --argjson expires "$ALLOWLIST_EXPIRES_AT" \
  '{metadata:{reuse_sys_cve_allowlist:"false"},
    cve_allowlist:{items:[{cve_id:$cve}],expires_at:$expires}}' > cve-allowlist.json
curl --fail-with-body --user "$HARBOR_USER" -X PUT \
  -H 'Content-Type: application/json' \
  --data-binary @cve-allowlist.json \
  'https://harbor.example.com/api/v2.0/projects/myapp'
```

### 스캔 정책 적용

특정 심각도 이상의 취약점이 있으면 pull을 차단합니다. 실행 중이거나 이미 캐시된 이미지를 자동 중지하는 정책은 아닙니다:

```yaml
# 프로젝트 설정
# Web UI: Projects > Configuration
# - Prevent vulnerable images from running: Yes
# - Severity threshold: High (High and Critical)
```

---

## 이미지 서명

서명은 digest의 무결성과 신뢰한 서명자를 확인하는 수단입니다. 취약점을 자동 수정하거나 실행 중인 Pod를 검사하지 않습니다. Cosign·Notation은 공식 설치 가이드로 설치하고, Harbor·정책 엔진과의 서명 포맷 호환성을 검증합니다.

### Cosign 통합 (권장)

```bash
# HARBOR_IMAGE must include an existing image digest, not a mutable tag.
: "${HARBOR_IMAGE:?Set harbor.example.com/myapp/app@sha256:<actual-digest>}"
cosign version
cosign generate-key-pair
cosign sign --key cosign.key "$HARBOR_IMAGE"
cosign verify --key cosign.pub "$HARBOR_IMAGE"
```

Keyless 서명은 OIDC 신원과 투명성 로그를 이용하며, 검증 정책에 신뢰할 issuer·identity를 지정해야 합니다. 위 키 기반 예제에서도 키 암호와 개인키를 CI 로그·저장소에 남기지 않습니다. 완전한 폐쇄망에서는 공개 Sigstore 서비스 접근을 전제로 한 흐름을 그대로 사용할 수 없습니다.

### Notation 통합

다음은 테스트 전용 자체 서명 인증서 예제입니다. `generate-test`가 만든 인증서 저장소와 trust policy를 가져온 다음 검증합니다. 운영에서는 조직의 CA·서명 키 관리와 명시적인 서명자 신원 제한을 사용합니다.

```bash
notation version
notation login harbor.example.com
notation cert generate-test --default harbor-demo
notation sign "$HARBOR_IMAGE"
cat > trustpolicy.json <<'JSON'
{
  "version": "1.0",
  "trustPolicies": [{
    "name": "harbor-demo",
    "registryScopes": ["harbor.example.com/myapp/app"],
    "signatureVerification": {"level": "strict"},
    "trustStores": ["ca:harbor-demo"],
    "trustedIdentities": ["*"]
  }]
}
JSON
notation policy import trustpolicy.json
notation verify "$HARBOR_IMAGE"
```

### Harbor에서 서명 강제

프로젝트 Configuration에서 Cosign 또는 Notation 정책을 선택합니다. 둘 다 켜면 두 종류의 서명이 모두 필요합니다. Chart에 `core.cosignKeyFile`을 추가해 공개키를 검증하도록 하는 옵션은 없습니다. Registry의 서명 액세서리 존재 검사와 조직이 신뢰하는 키·신원을 검증하는 정책을 구분합니다.

### Kubernetes 정책 적용

배포 시 강제 검증은 [이미지 보안](../security/07-image-security.md)의 Kyverno 등 Admission 정책에서 설정합니다. 유효한 공개키 또는 OIDC issuer·identity, 정확한 이미지 경로, 비공개 Registry 인증, init/ephemeral container 적용 범위를 확인하고 Audit에서 검증한 뒤 Enforce로 전환합니다. 잘못된 키·서명 없음·태그 재지정에 대한 실패도 시험합니다.

## 에어갭 환경에서의 Harbor

Docker Compose용 offline installer와 Kubernetes용 Helm 설치는 서로 다른 배포 방식입니다. Offline installer에 Harbor 이미지가 포함되어 있지만 Docker/Compose 패키지, Kubernetes Chart, CNI, 애플리케이션 이미지와 Trivy DB까지 모두 포함되는 것은 아닙니다.

### 오프라인 설치

```bash
HARBOR_VERSION=2.15.2
curl --fail --location --remote-name \
  "https://github.com/goharbor/harbor/releases/download/v${HARBOR_VERSION}/harbor-offline-installer-v${HARBOR_VERSION}.tgz"
# Verify the release checksum/signature before transporting the bundle.
sha256sum "harbor-offline-installer-v${HARBOR_VERSION}.tgz" > harbor-bundle.sha256
# Transfer both files through the approved offline transport.
```

폐쇄망 호스트에서 다음을 실행합니다. 로컬에서 생성한 SHA-256은 전송 무결성 확인용이며 배포자의 신뢰성을 입증하는 공식 서명을 대체하지 않습니다.

```bash
sha256sum -c harbor-bundle.sha256
tar xzf harbor-offline-installer-v2.15.2.tgz
cd harbor
cp harbor.yml.tmpl harbor.yml
# Set hostname, HTTPS certificate/key, strong admin/DB passwords and data_volume.
# For Trivy: preload DBs, set skip_update, skip_java_db_update and offline_scan.
# Install Docker Engine/Compose and other prerequisites from offline packages first.
./install.sh --with-trivy
```

### Kubernetes용 에어갭 이미지 준비

지원할 정확한 Kubernetes 버전과 동일한 kubeadm 바이너리로 필요한 제어 평면 이미지를 조회합니다. CNI·CSI·Ingress·모니터링 이미지와 설치 Chart/CRD는 별도로 준비합니다. kubeadm 관리가 아닌 클러스터는 해당 배포 도구의 목록을 사용합니다.

```bash
: "${K8S_VERSION:?Set the exact supported Kubernetes patch version}"
kubeadm config images list --kubernetes-version "$K8S_VERSION" > kubeadm-images.txt
```

### 이미지 반출·반입

각 원본과 목적지의 경로를 TSV로 명시합니다. basename만 사용하면 서로 다른 Registry·네임스페이스의 이미지가 충돌할 수 있습니다. 다음은 Skopeo가 설치된 Bash 환경에서 모든 플랫폼을 OCI archive로 옮기는 예제입니다. 서명·SBOM 같은 referrer는 도구 지원에 따라 별도 반입·검증해야 합니다.

```text
# images.tsv: two columns separated by a TAB; replace the internal hostname.
docker.io/library/nginx:1.30.4	harbor.airgap.local/k8s-system/dockerhub/library/nginx:1.30.4
```

온라인 환경에서:

```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p image-bundle
: > image-bundle/import.tsv
index=0
while IFS=$'\t' read -r source target || [[ -n "$source" ]]; do
  [[ -z "$source" || "$source" == \#* ]] && continue
  [[ -n "$target" ]] || { echo 'Missing target image' >&2; exit 1; }
  index=$((index + 1))
  file="image-${index}.tar"
  skopeo copy --all "docker://${source}" "oci-archive:image-bundle/${file}"
  printf '%s\t%s\n' "$file" "$target" >> image-bundle/import.tsv
done < images.tsv
(cd image-bundle && sha256sum image-*.tar import.tsv > SHA256SUMS)
```

`image-bundle` 디렉터리를 전달한 뒤 폐쇄망에서:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd image-bundle
sha256sum -c SHA256SUMS
# Pre-create the target Harbor projects and trust its TLS CA.
skopeo login harbor.airgap.local
while IFS=$'\t' read -r file target; do
  skopeo copy --all "oci-archive:${file}" "docker://${target}"
done < import.tsv
```

매핑한 내부 이미지 URI를 실제 Pod·Helm 값·kubeadm 설정에 반영하고 digest·플랫폼·pull을 검증합니다. `--all`은 CPU 아키텍처별 manifest 보존을 요청하지만 대상 형식 변환 시 digest가 바뀔 수 있으므로 원본과 목적지의 결과를 비교합니다.

### Trivy 데이터베이스 반입

```bash
# Use a Trivy version compatible with the deployed Harbor scanner adapter.
trivy image --cache-dir ./trivy-cache --download-db-only
trivy image --cache-dir ./trivy-cache --download-java-db-only
tar -C trivy-cache -czf trivy-db-bundle.tgz db java-db
```

번들을 각 Trivy replica의 영구 캐시 루트 `/home/scanner/.cache/trivy`에 풀어 `db/trivy.db`, `db/metadata.json`, `java-db/trivy-java.db` 및 Java DB 메타데이터가 올바른 소유권으로 존재하게 합니다. 실행 중인 DB 파일에 덮어쓰지 말고 스캐너를 정지하거나 새 PVC/초기화 Job으로 교체합니다. `tar`에 홈 경로를 포함하면 잘못된 하위 디렉터리에 풀리므로 위처럼 `-C`를 사용합니다.

```yaml
trivy:
  skipUpdate: true
  skipJavaDBUpdate: true
  offlineScan: true
```

`offlineScan`만으로 DB 다운로드가 꺼지거나 DB가 생성되지는 않습니다. DB 반입 주기와 만료 감시를 운영 절차로 정하고 업데이트 후 재스캔합니다. Compose의 `harbor.yml`에서는 해당 키가 `skip_update`, `skip_java_db_update`, `offline_scan`입니다.

### 에어갭 클러스터 containerd 설정

폐쇄망에서는 manifest에 내부 Harbor 주소를 명시합니다. 모든 외부 Registry를 임의의 `/v2/<project>` 경로로 치환하는 설정은 저장소 경로·인증을 자동 변환하지 않습니다. 노드별로 CA를 설치하고 런타임 버전에 맞게 설정합니다.

```toml
# containerd 2.x: /etc/containerd/config.toml
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
# containerd 1.x uses plugins."io.containerd.grpc.v1.cri".registry instead.
```

```toml
# /etc/containerd/certs.d/harbor.airgap.local/hosts.toml
server = "https://harbor.airgap.local"
[host."https://harbor.airgap.local"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/harbor.airgap.local/ca.crt"
```

config_path 변경 시 노드 유지보수 절차에 따라 containerd를 재시작하고 실제 CRI pull을 확인합니다. 인증은 namespace별 pull 전용 `imagePullSecrets`를 사용합니다.

## Harbor + Kubernetes 통합

### imagePullSecrets 설정

```bash
# Create pull credentials in the same namespace as the consuming Pod.
umask 077
HARBOR_AUTH_DIR=$(mktemp -d)
python3 - "$HARBOR_AUTH_DIR/config.json" <<'PYTHON'
import base64
import getpass
import json
import pathlib
import sys
name = input("Pull robot name returned by Harbor: ")
password = getpass.getpass("Pull robot secret: ")
auth = base64.b64encode(f"{name}:{password}".encode()).decode()
pathlib.Path(sys.argv[1]).write_text(json.dumps({
    "auths": {"harbor.example.com": {"auth": auth}}
}))
PYTHON
kubectl create secret generic harbor-secret -n default \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=.dockerconfigjson="$HARBOR_AUTH_DIR/config.json" \
  --dry-run=client -o yaml \
  | kubectl apply --server-side --field-manager=harbor-pull-secret -f -
rm -rf -- "$HARBOR_AUTH_DIR"
kubectl get secret harbor-secret -n default -o jsonpath='{.type}'
```

```yaml
# Pod에서 사용
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: myapp
    image: harbor.example.com/myapp/backend:v1.0.0
  imagePullSecrets:
  - name: harbor-secret
```

### Proxy Cache

![Docker/containerd 요청이 Harbor 프록시 캐시를 거쳐 캐시 적중 시 즉시 반환되고, 캐시 미스 시 업스트림 레지스트리에서 가져와 캐시에 저장한 뒤 반환되는 흐름을 보여준다.](../.gitbook/assets/ko-container-registry-03-harbor-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-container-registry-03-harbor-2.html)

Harbor를 외부 레지스트리의 프록시 캐시로 사용:

```yaml
# Harbor 프록시 캐시 프로젝트 생성
# Web UI: Projects > + New Project
# - Project Name: docker-hub-cache
# - Access Level: Public (또는 Private)
# - Proxy Cache: Enable
# - Registry: docker-hub (사전 등록된 endpoint)

# 사용 예시
# 원본: docker.io/library/nginx:1.30.4
# 캐시: harbor.example.com/docker-hub-cache/library/nginx:1.30.4
```

Proxy Cache의 cache miss는 업스트림 연결이 필요합니다. 캐시 신선도·업스트림 삭제 처리·인증은 프로젝트 설정에 따라 달라지며, 완전한 폐쇄망에는 사전 반입한 일반 프로젝트 이미지를 사용합니다.

### Garbage Collection

GC는 참조되지 않는 blob을 회수합니다. `delete_untagged`는 단순 blob 정리 외에 untagged artifact도 삭제하므로, digest로 배포 중인 이미지를 보호해야 합니다. 아래 예제는 삭제하지 않는 dry run입니다.

```bash
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  'https://harbor.example.com/api/v2.0/system/gc/schedule' \
  -H 'Content-Type: application/json' \
  -d '{"schedule":{"type":"Manual"},
       "parameters":{"delete_untagged":false,"dry_run":true}}'
curl --fail-with-body --user "$HARBOR_USER"   'https://harbor.example.com/api/v2.0/system/gc'
```

실행 결과를 확인한 뒤 UI에서 실제 실행과 일정을 설정합니다. Harbor는 GC 중 push/pull을 계속 지원하지만 I/O 부하가 생길 수 있고 최근 업로드 보호 시간 때문에 즉시 모든 공간이 반환되지는 않습니다.

### Tag Retention Policy

프로젝트의 Policy → Tag Retention에서 **보존할** 조건을 설정합니다. 예를 들어 최근 push 10개와 최근 30일 조건을 추가하면 **OR(합집합)**으로 보존하므로 10개보다 많이 남을 수 있습니다. 규칙에 맞지 않는 태그·아티팩트와 서명 관계, 실행 중인 digest·롤백 버전에 미치는 영향을 Dry Run으로 확인합니다.

API 생성 경로는 `/api/v2.0/retentions`이며 프로젝트별 가상의 `/tag-retention` 경로가 아닙니다. 운영 정책을 임의의 프로젝트 ID로 만들지 말고 UI에서 구성한 정책을 조회·시험할 수 있습니다.

```bash
curl --fail-with-body --user "$HARBOR_USER" \
  'https://harbor.example.com/api/v2.0/projects/myapp' \
  | jq '{project_id, retention_id: .metadata.retention_id}'
# Use the actual non-empty policy ID returned above.
: "${RETENTION_ID:?Set an existing retention policy ID}"
curl --fail-with-body --user "$HARBOR_USER"   "https://harbor.example.com/api/v2.0/retentions/${RETENTION_ID}"
curl --fail-with-body --user "$HARBOR_USER" -X POST \
  "https://harbor.example.com/api/v2.0/retentions/${RETENTION_ID}/executions" \
  -H 'Content-Type: application/json' -d '{"dry_run":true}'
```

## 모범 사례

### 1. 고가용성 구성

앞의 예제처럼 portal/core/jobservice/registry를 2개 이상으로 분산하고, 외부 DB·Redis 및 RWX/객체 스토리지 자체의 장애 복구도 검증합니다. S3를 선택하면 `persistence.imageChartStorage.type: s3`와 bucket/region을 설정하고 Registry Pod의 IAM 역할 또는 `existingSecret`을 명시합니다. 장기 access key를 values 파일에 넣지 않습니다. IRSA/Pod Identity를 쓴다면 해당 Registry 이미지 SDK의 지원·ServiceAccount·최소 S3 권한을 검증해야 합니다. 단순히 키를 생략하는 것만으로 역할이 연결되지 않습니다.

### 2. 보안 강화

외부·내부 TLS, OIDC/LDAP, 만료 있는 최소 권한 Robot, 감사 로그와 패치 관리를 적용합니다. NetworkPolicy는 실제 생성된 Pod 라벨·컨테이너 포트와 DNS, core↔registry/jobservice, PostgreSQL·Redis, DB 다운로드 및 복제 트래픽을 기준으로 작성합니다. 모든 Pod에 443만 허용하는 정책은 내부 통신과 DNS를 차단할 수 있습니다. 인증 제공자에서 비밀번호·MFA 정책을 관리하고, Harbor UI에 없는 임의의 비밀번호 정책 항목을 가정하지 않습니다.

### 3. 백업 전략

쓰기 작업·복제·GC를 제어한 일관된 시점을 정해 PostgreSQL, Registry blob 저장소, 설정, TLS 및 암호화 키를 함께 보관합니다. Helm values만으로 DB·이미지가 백업되지 않고, S3 Versioning이나 `aws s3 sync`만으로 시점 일관성이 보장되지 않습니다. Secret YAML은 base64일 뿐 암호화된 백업이 아니므로 암호화·접근 통제된 저장소에 보관합니다. 복구 시험에는 프로젝트·로봇 인증, 이미지 digest pull, 서명 검증, 정책과 스캔 결과를 포함합니다.

### 4. 모니터링

Chart의 `metrics.enabled`와, Operator CRD가 있는 경우 `metrics.serviceMonitor.enabled`를 사용합니다. 손으로 추측한 `http-metrics` 포트 대신 Chart가 생성한 ServiceMonitor·Service 포트를 확인합니다. Prometheus의 ServiceMonitor selector와 namespace 선택에도 맞춰야 합니다. 저장소·DB 용량, 복제/스캔/GC 실패와 큐 지연, Trivy DB 신선도, TLS·Robot 만료를 감시합니다.

## 요약

| 항목 | 권장 사항 |
|------|----------|
| **설치** | Helm + 외부 DB/Redis (프로덕션) |
| **접근 제어** | RBAC + Robot Accounts (CI/CD) |
| **스캐닝** | Trivy 자동 스캔 활성화 |
| **서명** | Cosign (권장) |
| **복제** | Pull (미러링) + Push (DR) |
| **에어갭** | Offline installer + 이미지 preload |
| **HA** | 2+ replicas + 외부 DB/Redis + S3 |
| **백업** | DB·blob·설정·키의 일관된 백업 및 복구 시험 |

---

## 참고 자료

- [Harbor 공식 문서](https://goharbor.io/docs/)
- [Harbor Helm Chart](https://github.com/goharbor/harbor-helm)
- [Harbor API Reference](https://editor.swagger.io/?url=https://raw.githubusercontent.com/goharbor/harbor/main/api/v2.0/swagger.yaml)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Cosign Documentation](https://docs.sigstore.dev/quickstart/quickstart-cosign/)
- [Harbor in Air-gapped Environment](https://goharbor.io/docs/main/install-config/configure-yml-file/)

### 검토한 버전별 근거

- [Harbor 2.15.2 release](https://github.com/goharbor/harbor/releases/tag/v2.15.2)
- [Helm chart 1.19.2 values](https://github.com/goharbor/harbor-helm/blob/v1.19.2/values.yaml)
- [Harbor 2.15.2 API schema](https://github.com/goharbor/harbor/blob/v2.15.2/api/v2.0/swagger.yaml)
- [Project role permissions](https://goharbor.io/docs/main/administration/managing-users/user-permissions-by-role/)
- [Cosign and Notation](https://goharbor.io/docs/main/working-with-projects/working-with-images/sign-images/)
- [Containerd registry hosts](https://github.com/containerd/containerd/blob/main/docs/hosts.md)
