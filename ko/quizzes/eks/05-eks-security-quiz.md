# Amazon EKS 보안 퀴즈

> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 Amazon EKS의 보안 기능, 모범 사례 및 구성에 대한 이해를 테스트합니다.

## 퀴즈 개요
- EKS 인증 및 권한 부여
- 네트워크 보안
- 컨테이너 보안
- 데이터 보안
- 규정 준수 및 감사
- 보안 모범 사례

## 객관식 문제

### 1. IAM 사용자·역할에 대해 신원 인증과 Kubernetes 권한 부여를 올바르게 결합하는 EKS 구성은 무엇인가요?

- A) IAM 관리 권한만 사용
- B) 신원 인증 경로 없이 RBAC 규칙만 생성
- C) IAM 클러스터 접근과 적절한 RBAC·EKS access policy 구성
- D) API endpoint 네트워크 제한만 사용

<details>
<summary>정답 보기</summary>

**정답: C) IAM 클러스터 접근과 적절한 RBAC·EKS access policy 구성**

**설명:**

IAM은 구성한 EKS 접근 경로에서 의도한 사람·자동화 신원을 인증합니다. Kubernetes RBAC와 EKS access policy는 Kubernetes 작업 권한을 부여하며 grant는 합산됩니다. 네트워크 제한은 별도 계층이며 권한 부여를 대체하지 않습니다. Pod의 Kubernetes 인증은 일반적으로 ServiceAccount token을 사용하고 IRSA·Pod Identity는 워크로드 AWS 자격 증명을 제공합니다.

EKS cluster 서비스 역할과 개발자 역할의 목적은 다릅니다. 개발자에게 AmazonEKSClusterPolicy를 붙여도 Kubernetes 접근 권한이 생기지 않으며 DescribeCluster·ListClusters나 kubeconfig 파일만으로 workload 작업이 허용되지는 않습니다.

**범위가 있는 구현:** 권한 있는 플랫폼 운영자가 승인된 기존 개발자 IAM 역할을 위해 아래 namespace·RBAC를 준비합니다. 클러스터는 access entry를 이미 지원해야 합니다. 관리자·노드 매핑을 보존하고 authentication mode migration을 검토하며 sample ConfigMap으로 aws-auth를 덮어쓰지 않습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${DEVELOPER_ROLE_ARN:?Set a prepared IAM role ARN, not an STS session ARN}"
MODE=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.accessConfig.authenticationMode --output text)
case "$MODE" in
  API|API_AND_CONFIG_MAP) ;;
  *) echo "Access entries are not enabled; review the migration first"; exit 1 ;;
esac
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > security-access-entries.json
python3 - "$DEVELOPER_ROLE_ARN" <<'PY'
import json, sys
with open("security-access-entries.json") as stream:
    existing = json.load(stream)["accessEntries"]
if sys.argv[1] in existing:
    raise SystemExit("Entry already exists; inspect its groups/policies instead of overwriting")
PY
aws eks create-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$DEVELOPER_ROLE_ARN" --type STANDARD \
  --kubernetes-groups security-demo-developers
```



```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: security-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
- apiGroups:
  - batch
  resources:
  - jobs
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer
  namespace: security-demo
subjects:
- kind: Group
  name: security-demo-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

Access entry의 그룹 이름과 RoleBinding subject가 일치해야 합니다. 이 Role은 security-demo 안에서 표시한 작업을 허용하지만 기존 다른 grant가 접근 범위를 넓힐 수 있습니다. Deployment·Job 생성자는 namespace의 Secret·PVC·ServiceAccount를 간접 사용할 수 있으므로 Secret 직접 읽기 규칙이 없다는 사실만으로 tenant 경계가 되지는 않습니다. Tenant를 분리하고 admission·소유권 제어로 workload 신원·리소스 사용을 제한합니다.

별도 검토한 viewer는 namespace 범위 AmazonEKSViewPolicy association을 사용할 수도 있습니다. 추가 전에 기존 access policy를 확인하며 이 grant가 더 넓은 RBAC·다른 access policy 권한을 취소하지는 않습니다. `eks:namespaces`는 일반 kubectl 요청이 아닌 access policy association 요청을 필터링합니다.

**실제 로그인 검증:** 호출자는 cluster 조회와 승인된 역할 assume 권한이 있어야 합니다. 다음은 기본 context를 대체하지 않고 임시 kubeconfig를 만듭니다:

```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${DEVELOPER_ROLE_ARN:?Set the intended IAM role ARN}"
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/eks-login-check.XXXXXXXX")
trap 'rm -rf -- "$review_dir"' EXIT
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --role-arn "$DEVELOPER_ROLE_ARN" --kubeconfig "$review_dir/config"
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i create jobs -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n another-team
```

의도한 grant와 결과를 비교하고 예상하지 못한 다른 namespace 권한을 조사합니다. `--as`는 impersonation·RBAC를 검사하며 IAM access policy 경로의 동작 증명이 아닙니다. 이 퀴즈에서 실제 IAM 로그인·Kubernetes 권한 시험은 실행하지 않았으며 로컬 증거는 schema·shell 검사와 mocked access entry 흐름입니다.

참고: [EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [EKS access policy](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

</details>

### 2. 정책 시행을 지원하는 EKS 네트워크에서 label 기반 Pod 트래픽 규칙을 표현하는 Kubernetes 기능은 무엇인가요?

- A) 인스턴스 security group만 사용
- B) 시행 가능한 네트워크 구현과 NetworkPolicy resource
- C) VPC endpoint policy만 사용
- D) 호스트 firewall 명령만 사용

<details>
<summary>정답 보기</summary>

**정답: B) 시행 가능한 네트워크 구현과 NetworkPolicy resource**

**설명:**

NetworkPolicy는 Kubernetes label·namespace로 Pod와 허용 트래픽을 선택하며 정책을 시행하는 네트워크 구현이 필요합니다. 지원되는 Pod용 보안 그룹을 포함한 security group도 유용한 AWS 제어이며 전체 인스턴스에만 한정되지 않습니다. VPC endpoint policy는 지원 AWS 서비스 접근을 제어하며 임의 label 기반 Pod 트래픽 정책이 아닙니다.

**완전한 정책 예제:** 아래 manifest는 격리된 데모 namespace의 정책이며 앱 설치나 CNI 교체 절차가 아닙니다. 지원되는 enforcing CNI가 있는 일반 Linux EC2 노드와 통상적인 CoreDNS Deployment·Pod label을 전제로 합니다. Auto Mode·node-local DNS는 실제 resolver 경로에 맞는 규칙이 필요합니다. CoreDNS ingress가 제한되어 있다면 그 소유자도 질의를 허용해야 합니다.

Namespace 소유자를 통해 저장·적용합니다. Default deny는 양방향을 격리하며 frontend → API, API → database에는 송신 egress와 수신 ingress를 각각 허용합니다. DNS에는 UDP·TCP가 모두 필요합니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-network-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: security-monitoring-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: security-network-demo
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-ingress
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: monitor-api
  namespace: security-network-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-monitoring-demo
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
```

Monitoring peer의 namespaceSelector와 podSelector를 같은 peer에 두어 **AND**로 평가하므로 security-monitoring-demo의 matching Prometheus Pod만 선택합니다. 이 client가 egress 격리 상태라면 송신 연결도 허용해야 합니다:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: prometheus-to-demo-api
  namespace: security-monitoring-demo
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: security-network-demo
      podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

| 흐름 | 이 정책에서 의도한 결과 |
|---|---|
| frontend → api TCP 8080 | 허용 |
| api → database TCP 5432 | 허용 |
| frontend → database TCP 5432 | 거부 |
| 무관한 Pod → api TCP 8080 | 거부 |
| 선택한 Prometheus → api TCP 9090 | 허용 |
| monitoring namespace의 다른 Pod → api TCP 9090 | 거부 |
| workload → matching CoreDNS Pod UDP·TCP 53 | Resolver 측 제어를 충족하면 허용 |
| 임의 외부 목적지 | 명시적 egress 규칙 추가 전 거부 |

정책은 순서 없이 합산되므로 다른 광범위한 allow가 결과를 넓힐 수 있고 default deny가 이를 덮어쓰지 않습니다. 대상 CNI에서 실제 전체 정책·DNS·새 허용·거부 연결을 시험합니다. 기존 연결, hostNetwork·node 트래픽과 NAT에는 구현별 제약이 있으며 단순 NetworkPolicy를 보편적인 IMDS·host firewall 경계로 볼 수 없습니다.

외부 서비스에는 실제 목적지 주소·port 또는 선택한 구현이 지원하는 DNS 기반 제어를 사용합니다. 모든 목적지의 443 port나 전체 10.0.0.0/8 허용은 서비스 allowlist가 아닙니다. 임의 Calico·Cilium 교체 manifest나 일부 kube-proxy replacement flag를 기존 EKS 네트워크에 적용하는 것은 안전한 정책 활성화 절차가 아닙니다.

대응 본문의 selector·port 합성 사례 18개를 로컬에서 확인했으며 실제 packet·CNI 시험은 실행하지 않았습니다. 참고: [Kubernetes NetworkPolicy 동작](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 3. EKS 컨테이너 이미지 보안에 상호 보완적인 제어를 결합하는 방법은 무엇인가요?

- A) 수동 이미지 검사에만 의존
- B) 모든 공식 이미지에 취약점이 없다고 가정
- C) 스캔·서명·검증·admission 제어 결합
- D) 컨테이너 내부 antivirus에만 의존

<details>
<summary>정답 보기</summary>

**정답: C) 스캔·서명·검증·admission 제어 결합**

**설명:**

Scanner는 규칙·취약점 DB가 다루는 문제를 식별하며 모든 backdoor·미래 취약점 부재를 증명하지는 않습니다. 서명은 구성한 trust policy 아래의 무결성·신원을 확인하며 서명한 소프트웨어가 안전하다는 보장은 아닙니다. Admission 제어는 선택한 배포 정책을 시행합니다. 유지 관리되는 작은 base image를 사용하고 패치 시 rebuild하며 예외와 적절한 ECR basic·enhanced 또는 다른 scan 방식을 관리합니다.

**AWS Signer와 Notation:** 컨테이너 서명 platform은 `Notation-OCI-SHA384-ECDSA`입니다. 먼저 push된 이미지의 digest를 Notation AWS Signer plugin으로 서명합니다. `Aws::ECR::Image` platform이나 `start-signing-job --source-image`는 지원 절차가 아니며 검토한 AWS CLI도 해당 옵션을 거부합니다.

현재 ECR managed signing도 registry signing rule에 따라 push 시 서명하는 지원 대안입니다. 이를 선택한다면 profile·권한을 구성하고 실제 signing status를 확인한 뒤 승격합니다. 이미지가 push되었다는 사실만으로 비동기 서명이 완료되었다고 가정하지 않습니다.

**Trust 구성:** 검증한 Notation·Signer plugin 설치, 올바른 partition의 AWS Signer root trust store와 검토한 strict trust policy를 준비합니다. 아래 commercial Region 예제는 repository 하나와 승인 profile로 trust를 제한합니다. 계정·Region·repository·profile을 일관되게 바꾸며 인증서가 AWS root로 연결된다는 이유만으로 모든 서명자를 신뢰하지 않습니다.

```json
{
  "version": "1.0",
  "trustPolicies": [
    {
      "name": "reviewed-eks-repository",
      "registryScopes": [
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/team/app"
      ],
      "signatureVerification": {
        "level": "strict"
      },
      "trustStores": [
        "signingAuthority:aws-signer-ts"
      ],
      "trustedIdentities": [
        "arn:aws:signer:us-west-2:123456789012:/signing-profiles/eks_images"
      ]
    }
  ]
}
```

`notation policy import notation-trust-policy.json`으로 build 환경이 소유한 Notation 구성에 policy를 import합니다. 기존 policy를 대체하기 전에 검토하며 검토하지 않은 script로 개발자의 공유 trust 구성을 덮어쓰지 않습니다. Build 역할에는 repository 범위 ECR pull·push, ECR 인증과 필요한 SignPayload·GetRevocationStatus 권한이 필요합니다. Signing profile 생성은 별도 provisioning 책임이며 기존 승인 profile 사용만을 위해 build에 PutSigningProfile을 줄 필요는 없습니다.

**CodeBuild 예제:** 다음은 CodePipeline 정의가 아닌 buildspec입니다. Bash·Python·Docker와 daemon 접근·AWS CLI·Trivy·Notation·AWS Signer plugin을 설치하고 버전을 고정한 소유 Linux build image가 필요합니다. Project runtime 권한, 네트워크·scanner DB, IAM 역할·trust store·policy와 기존 ECR repository는 별도로 구성합니다. Dockerfile·source는 이 build 역할에 대해 신뢰하는 입력입니다. 예제는 Git commit과 commercial AWS 계정·Region 하나를 전제로 하며 cross-account 서명 설계가 아닙니다.

```yaml
version: 0.2
env:
  shell: bash
phases:
  build:
    commands:
      - |
        set -euo pipefail
        umask 077
        # Reserve this generated artifact name; remove stale output before any build step.
        rm -f -- verified-image.json
        : "${AWS_REGION:?Set the commercial AWS Region}"
        : "${AWS_ACCOUNT_ID:?Set the expected ECR/signing account ID}"
        : "${ECR_REPOSITORY:?Set the complete repository name, including any path}"
        : "${SIGNING_PROFILE_ARN:?Set the approved AWS Signer profile ARN}"
        : "${CODEBUILD_RESOLVED_SOURCE_VERSION:?This example requires a resolved Git commit}"
        python3 - <<'PY'
        import os, re
        checks = {
            "AWS_ACCOUNT_ID": r"[0-9]{12}",
            "AWS_REGION": r"[a-z0-9-]+",
            "ECR_REPOSITORY": r"[a-z0-9]+(?:[._/-][a-z0-9]+)*",
            "CODEBUILD_RESOLVED_SOURCE_VERSION": r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
        }
        for name, pattern in checks.items():
            if not re.fullmatch(pattern, os.environ[name]):
                raise SystemExit("Invalid example input: " + name)
        prefix = f"arn:aws:signer:{os.environ['AWS_REGION']}:{os.environ['AWS_ACCOUNT_ID']}:/signing-profiles/"
        profile = os.environ["SIGNING_PROFILE_ARN"]
        if not profile.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9_/]+", profile[len(prefix):]):
            raise SystemExit("Use an approved signing profile in this example's account/Region")
        PY
        REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${CODEBUILD_RESOLVED_SOURCE_VERSION}"
        ACTUAL_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
        if [[ "$ACTUAL_ACCOUNT" != "$AWS_ACCOUNT_ID" ]]; then
          printf '%s\n' 'Unexpected build-role account' >&2
          exit 1
        fi
        aws ecr get-login-password --region "$AWS_REGION" |
          docker login --username AWS --password-stdin "$REGISTRY"
        docker build --tag "$IMAGE_URI" .
        trivy image --image-src docker --scanners vuln --severity HIGH,CRITICAL \
          --exit-code 1 --no-progress "$IMAGE_URI"
        docker push "$IMAGE_URI"
        DIGESTS_JSON=$(docker image inspect --format '{{json .RepoDigests}}' "$IMAGE_URI")
        IMAGE_REFERENCE=$(python3 - "$REGISTRY/$ECR_REPOSITORY" "$DIGESTS_JSON" <<'PY'
        import json, re, sys
        digests = json.loads(sys.argv[2])
        if not isinstance(digests, list):
            raise SystemExit("Expected Docker RepoDigests array")
        pattern = re.escape(sys.argv[1]) + r"@sha256:[0-9a-f]{64}"
        matching = {d for d in digests if isinstance(d, str) and re.fullmatch(pattern, d)}
        if len(matching) != 1:
            raise SystemExit("Expected exactly one pushed digest for this repository")
        print(matching.pop())
        PY
        )
        notation sign --plugin com.amazonaws.signer.notation.plugin \
          --id "$SIGNING_PROFILE_ARN" "$IMAGE_REFERENCE"
        notation verify "$IMAGE_REFERENCE"
        python3 - "$IMAGE_REFERENCE" "$CODEBUILD_RESOLVED_SOURCE_VERSION" <<'PY'
        import json, sys
        with open("verified-image.json", "x") as stream:
            json.dump({"image": sys.argv[1], "sourceCommit": sys.argv[2]}, stream)
            stream.write("\n")
        PY
artifacts:
  files:
    - verified-image.json
```

검토한 project 구성에 `AWS_ACCOUNT_ID`, `AWS_REGION`, `ECR_REPOSITORY`(예: `team/app`), `SIGNING_PROFILE_ARN`을 설정합니다. Registry hostname으로 인증하고 중첩 repository 경로를 유지하며 로컬 build 이미지를 push 전에 scan합니다. 임의의 첫 RepoDigest나 mutable tag 대신 해당 repository의 push digest를 선택합니다. Trivy 예제는 HIGH·CRITICAL 취약점 finding을 gate하며 secret·구성·provenance에는 별도로 설계한 검사를 추가합니다.

승격 단계는 모두 `set -euo pipefail`을 적용한 Bash build block 하나에 있습니다. Login·build·scan·push·sign·verify 실패는 새 artifact 작성 전에 중단됩니다. CodeBuild post_build는 build 실패 후에도 실행될 수 있으므로 별도 post_build의 무조건적인 push·sign은 안전하지 않습니다. 예약한 artifact 경로를 먼저 지워 이전 결과 재사용을 막습니다. 후속 배포도 build 성공과 artifact 검증을 요구해야 하며 JSON 파일 자체가 권한 부여나 서명된 attestation은 아닙니다.

`verified-image.json`은 EKS 배포·GitOps consumer가 사용할 정확한 digest reference를 담습니다. ECS의 `imagedefinitions.json`이 아니며 그 자체로 배포하지 않습니다. 실제 서명·검증은 registry 접근, trust, revocation 검사와 AWS Signer 가용성에 의존합니다.

**Admission:** 운영 signature verifier는 선택한 Notation·Signer 서명과 trust policy를 이해해야 합니다. AWS는 Gatekeeper+Ratify와 AWS Signer·Notation 통합을 사용하는 Kyverno 방식을 문서화합니다. 일반 policy engine 설치, ConstraintTemplate이 없는 Gatekeeper constraint, 다른 서명 방식의 public-key 필드만으로 해당 통합이 완성되지는 않습니다. 시행 전에 승인·비승인 profile, unsigned image, digest 불일치, revoke·expiry, verifier 장애와 admission failure policy를 검증합니다.

다음 별도 Kyverno 1.19.1 규칙은 security-demo의 **image reference 문법과 repository**만 제한하며 일반·init·ephemeral container를 모두 검사합니다. 서명 검증을 수행한다는 주장이 아닙니다:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-approved-image-reference
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$'))
      && (!has(object.spec.initContainers) || object.spec.initContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
      && (!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, c.image.matches('^123456789012[.]dkr[.]ecr[.]us-west-2[.]amazonaws[.]com/team/app@sha256:[0-9a-f]{64}$')))
    message: Use a sha256 digest from the approved team/app repository in security-demo.
```

검증: pipeline 실패·순서·artifact mocked 사례 20개와 실제 Kyverno CLI 문자열 정책 사례 9개를 확인했습니다. Buildspec·Bash·Python·JSON과 배포 policy CRD도 검사했습니다. 이미지를 build·scan·push하거나 실제 AWS 서명을 생성·검증하지 않았고 admission webhook도 배포하지 않았습니다. 환경 전제를 명시하고 검토한 교육용 흐름이며 운영 준비 완료 검증이 아닙니다.

참고: [Signer 서명](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html), [Signer 검증](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html), [ECR managed signing](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html), [EKS admission 검증](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html), [CodeBuild buildspec](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html), [Trivy image flag](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/).

</details>

### 4. EKS에서 일관된 현재 Pod 보안 기준을 적용하는 방법은 무엇인가요?

- A) privileged mode만 비활성화
- B) PSA로 버전이 있는 PSS profile을 시행하고 필요한 admission policy 검토
- C) non-root UID만 설정
- D) root filesystem만 읽기 전용으로 설정

<details>
<summary>정답 보기</summary>

**정답: B) PSA로 버전이 있는 PSS profile을 시행하고 필요한 admission policy 검토**

**설명:**

Pod Security Standards는 Privileged·Baseline·Restricted profile을 정의하고 Pod Security Admission은 namespace에서 선택한 profile을 시행합니다. PSA는 Kubernetes 1.25부터 stable이며 PodSecurityPolicy는 1.21에서 deprecated, **1.25에서 제거**되었습니다. 현재 클러스터에 제거된 API를 배포할 수 없습니다. 과거 constraint 이름에 “PSP”가 있더라도 Kyverno·Gatekeeper 정책은 별도 resource입니다.

검토한 v1.36 profile을 사용하는 격리된 Linux 데모는 다음과 같습니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
---
apiVersion: v1
kind: Pod
metadata:
  name: security-context-demo
  namespace: security-demo
spec:
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.37.0
    command:
    - sh
    - -c
    args:
    - id && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
```

Namespace enforce는 Pod admission에 적용됩니다. Audit·warn이 controller template 위반을 보고할 수 있지만 Deployment·Job apply 성공이 Pod의 enforce 통과를 의미하지는 않습니다. Label 변경이 기존 Pod를 소급 eviction하지도 않습니다. 실제 클러스터에 맞는 policy version을 선택하고 기존 워크로드를 검토한 뒤 enforce합니다.

runAsNonRoot·runAsUser와 seccomp는 allowPrivilegeEscalation·capability와 별개입니다. fsGroup은 Pod 수준 volume 소유권 설정이며 container capability가 아닙니다. Read-only root는 앱과 호환되어야 하는 유용한 추가 강화지만 PSS Restricted의 보편적 필수 요건이 아니고 mounted PVC까지 읽기 전용으로 만들지 않습니다. 실제 앱에는 호환 UID·GID와 쓰기 가능한 임시·cache·socket 경로가 필요하며 일반적인 root 중심 nginx에 필드만 추가하면 동작하는 것은 아닙니다.

**추가하는 제한된 admission 규칙:** 아래 Kyverno 1.19.1 ValidatingPolicy는 security-demo의 일반·init·ephemeral container를 모두 검사합니다. privileged 생략은 false로 허용하고 true를 거부합니다. 오래된 설치 manifest 대신 현재 v1 policy API를 사용합니다:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: demo-disallow-privileged
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      - pods/ephemeralcontainers
      operations:
      - CREATE
      - UPDATE
      scope: Namespaced
  matchConditions:
  - name: demo-namespace
    expression: has(object.metadata.namespace) && object.metadata.namespace == 'security-demo'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false) && (!has(object.spec.initContainers)
      || object.spec.initContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false)) && (!has(object.spec.ephemeralContainers)
      || object.spec.ephemeralContainers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged)
      || c.securityContext.privileged == false))
    message: Privileged containers, including init and ephemeral containers, are not
      allowed in security-demo.
```

이 규칙 하나가 전체 PSS profile이나 이미지 검증을 대체하지는 않습니다. Privileged CSI·monitoring agent와 의도한 예외는 플랫폼 소유자가 관리하며 kube-system에 데모 정책을 일괄 적용하지 않습니다. Gatekeeper 대안도 실제 ConstraintTemplate·대응 constraint·동작 검증이 필요합니다.

Manifest·schema와 실제 Kyverno CLI 사례 6개로 생략·false, 일반·init·ephemeral privileged와 다른 namespace를 검사했습니다. Ephemeral container는 Pod 생성이 아닌 합성 UPDATE 객체로 시험했습니다. 실제 admission webhook·Pod 배포는 실행하지 않았습니다.

참고: [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

### 5. EKS 워크로드에 상호 보완적인 보안 증거를 제공하는 접근 방식은 무엇인가요?

- A) 가끔 수행하는 수동 검토만 사용
- B) AWS Config 검사만 사용
- C) GuardDuty만 사용
- D) Posture finding·audit log·runtime coverage·검증한 대응 경로 결합

<details>
<summary>정답 보기</summary>

**정답: D) Posture finding·audit log·runtime coverage·검증한 대응 경로 결합**

**설명:**

| 증거·제어 | 제공 범위와 한계 |
|---|---|
| Security Hub CSPM·AWS Config | 지원하는 구성 control·finding이며 전체 Kubernetes·규제 인증이 아님 |
| GuardDuty EKS Protection | 독립된 stream을 이용하는 Kubernetes audit 기반 위협 분석 |
| GuardDuty Runtime Monitoring | 지원 노드의 agent 기반 runtime event이며 enabled 상태만으로 coverage가 증명되지 않음 |
| CloudTrail | AWS API 활동이며 Kubernetes audit·앱 데이터 접근 log를 대체하지 않음 |
| Kubernetes audit log | Audit policy·level이 선택한 요청이며 모든 앱 작업·본문이 아님 |
| CloudWatch·인시던트 전달 | Log 분석·담당자 전달이며 전달·보존·대응 검증 필요 |

Security Hub CSPM의 FSBP는 CIS Kubernetes Benchmark가 아닙니다. 지원 CIS AWS Foundations control도 전체 CIS Kubernetes 감사가 아닙니다. 적용 benchmark·버전, 수동 검사, 관리형 서비스 예외와 실제 워크로드 요건에 필요한 증거를 기록합니다.

Detector·CSPM standard·Config recorder·CloudTrail은 기존 조직·Region 소유권 아래 관리합니다. 준비된 bucket policy·암호화·event selector·보존 기간 없이 새 regional detector를 만들거나 중앙 구성을 덮어쓰고 trail을 시작하지 않습니다. CloudTrail data event는 기본 management event 범위와 별개입니다. 이번 검토에서 계정 수준 모니터링 리소스는 provisioning하지 않았습니다.

**EKS별 검사:** 본문처럼 필요한 control plane log type·update 완료·log 도착을 확인합니다. `eks-cluster-logging-enabled`(모든 유형·주기 검사)와 `eks-cluster-log-enabled`(선택 유형·구성 변경 검사)는 모두 유효한 Config 규칙입니다. 자동 현재 버전 catalog라고 가정하지 말고 `oldestVersionSupported` parameter를 관리합니다. 명시적 encryptionConfig control의 finding이 EKS 1.28+ API 데이터의 기본 envelope encryption 부재를 의미하지는 않습니다.

GuardDuty audit 분석은 별도의 고객 CloudWatch audit export를 요구하지 않습니다. Runtime Monitoring에는 지원 security agent·data endpoint와 실제 coverage가 필요하며 현재 EKS에서는 EC2·Auto Mode를 지원하고 Fargate·Hybrid Nodes는 지원하지 않습니다. 현재 RUNTIME_MONITORING feature를 사용하고 이전 EKS_RUNTIME_MONITORING migration을 검토합니다. EKS_AUDIT_LOGS를 runtime monitoring으로 혼동하지 마세요.

**CSPM 이벤트 전달 예제:** 다음을 `security-event-pattern.json`으로 저장합니다. NEW·NOTIFIED workflow 상태의 ACTIVE HIGH·CRITICAL ASFF finding을 선택하며 다른 schema인 `Findings Imported V2` OCSF 이벤트는 선택하지 않습니다:

```json
{
  "source": [
    "aws.securityhub"
  ],
  "detail-type": [
    "Security Hub Findings - Imported"
  ],
  "detail": {
    "findings": {
      "Severity": {
        "Label": [
          "HIGH",
          "CRITICAL"
        ]
      },
      "Workflow": {
        "Status": [
          "NEW",
          "NOTIFIED"
        ]
      },
      "RecordState": [
        "ACTIVE"
      ]
    }
  }
}
```

다음 합성 이벤트는 pattern 검사 전용이며 실제 finding이나 완전한 ASFF import payload가 아닙니다. `synthetic-security-event.json`으로 저장합니다:

```json
{
  "version": "0",
  "id": "00000000-0000-0000-0000-000000000001",
  "account": "123456789012",
  "region": "us-west-2",
  "time": "2026-09-11T00:00:00Z",
  "source": "aws.securityhub",
  "detail-type": "Security Hub Findings - Imported",
  "resources": [],
  "detail": {
    "findings": [
      {
        "Id": "synthetic-example-not-a-real-finding",
        "Severity": {
          "Label": "HIGH"
        },
        "Workflow": {
          "Status": "NEW"
        },
        "RecordState": "ACTIVE"
      }
    ]
  }
}
```

승인된 AWS 시험에서 `aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2`는 matching되어야 합니다. LOW severity, RESOLVED·SUPPRESSED workflow, ARCHIVED 상태, 필드 누락과 V2 type은 이 pattern에 matching되지 않는지도 확인합니다. 이번 검토는 JSON·출처 schema를 확인했으며 EventBridge 서비스 matcher·실제 이벤트 전달을 실행한 것은 아닙니다.

현재 EventBridge 문서가 지원하는 방식으로, 소유한 SNS topic의 publish 권한이 있는 **기존 검토된 EventBridge 실행 역할**을 target에 사용할 수 있습니다. 소유 ARN으로 바꾼 뒤 `security-event-targets.json`으로 저장합니다:

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

역할에는 올바른 EventBridge trust와 최소 범위 sns:Publish 권한이 필요하며 해당 topic·key policy와 명시적 Deny도 확인합니다. 실행 역할을 쓰지 않는 target은 지원 resource-based 권한 경로가 필요합니다. Target JSON 자체가 권한을 주거나 rule·topic·role·subscription을 생성하지는 않습니다.

`aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2` 사용 전에 기존 rule·target 소유권을 확인합니다. 명령 종료 상태뿐 아니라 FailedEntryCount·FailedEntries를 검사합니다. SNS subscription, 암호화 권한, retry·dead-letter 동작과 통제된 전체 전달 시험을 확인합니다. 이번 감사에서 알림은 전송하지 않았습니다.

**감사 조사:** 실제 EKS log group에서 다음 Logs Insights 예제는 Kubernetes audit JSON field discovery를 전제로 합니다. RBAC 변경 요청을 찾아 responseStatus.code로 성공·거부 요청을 구분합니다:

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

Query에 의존하기 전에 표본 record의 필드·stream 이름을 확인합니다. 필요한 증거를 보존하고 소유권·severity·escalation을 정하여 대응 절차를 시험합니다. Finding dashboard와 서비스 enabled 상태만으로 조치 완료·규제 요건 충족이 증명되지는 않습니다.

참고: [CSPM 표준](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html), [ASFF 이벤트](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html), [V2 이벤트](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html), [EventBridge target 권한](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html), [EKS audit log](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

### 6. 중앙에서 통제하는 AWS 접근·수명 주기 관리가 필요한 앱 credential에 적합한 접근 방식은 무엇인가요?

- A) 접근·rotation·reload 계획 없이 값 저장
- B) 환경 변수를 암호화 수단으로 간주
- C) 범위를 제한한 신원과 명시적인 전달·수명 주기 설계로 적절한 AWS secret·parameter backend 사용
- D) 운영 credential을 이미지에 하드코딩

<details>
<summary>정답 보기</summary>

**정답: C) 범위를 제한한 신원과 명시적인 전달·수명 주기 설계로 적절한 AWS secret·parameter backend 사용**

**설명:**

Secrets Manager·Parameter Store는 AWS 접근 제어·감사를 중앙화할 수 있지만 workload identity·최소 권한·전달·reload 제어 없이 외부 backend만 사용한다고 자동으로 안전해지지는 않습니다. Secrets Manager는 지원 credential에 구성한 rotation을 제공하지만 Parameter Store는 같은 내장 credential rotation 절차를 제공하지 않습니다. SecureString의 KMS 암호화·version 관리는 대상 database·서비스의 credential 변경과 다릅니다.

EKS 1.28+는 이미 모든 Kubernetes API 데이터를 기본 KMS v2 envelope encryption으로 암호화합니다. Secret manifest의 Base64는 여전히 encoding일 뿐이며 API·Pod 접근으로 값이 노출될 수 있습니다. 환경 변수는 전달 방식이지 암호화가 아니며 Secret 변경 시 기존 process 환경이 갱신되지는 않습니다.

**소유권·전달 방식을 선택합니다:** ESO는 Kubernetes Secret을 기록합니다. ASCP+Secrets Store CSI Driver는 파일을 mount하고 선택적으로 Kubernetes Secret과 동기화할 수 있습니다. 두 controller가 같은 target Secret을 관리하지 않도록 합니다. 파일 전용 CSI도 workload·node 접근 제어가 필요하며 선택적 동기화는 값을 Kubernetes API에도 복제합니다.

**ASCP 예제:** 검토한 EKS 1.36용 신규 소유 Linux EC2 설치이며 알 수 없는 기존 클러스터로의 rollout이 아닙니다. 먼저 기존 release·CSIDriver 소유권, 노드 호환성, privileged 플랫폼 agent admission, 네트워크·scheduling을 확인합니다. Fargate는 CSI node DaemonSet을 실행할 수 없습니다. Hybrid·Auto Mode에는 현재 provider·node 선행 요건이 필요하며 아래 로컬 render로 검증된 것이 아닙니다.

별도로 관리하는 CSI 1.6.1 driver의 `secrets-csi-values.yaml`은 두 AWS token audience와 선택적 Secret 동기화·rotation을 명시합니다:

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

ASCP chart 3.1.3은 기본적으로 driver를 dependency로 설치하고 token audience를 구성합니다. 이 예제에서는 driver를 별도 설치하므로 두 번째 driver를 만들지 않도록 다음을 `ascp-values.yaml`로 저장합니다:

```yaml
secrets-store-csi-driver:
  install: false
```



```bash
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo add aws-secrets-manager https://aws.github.io/secrets-store-csi-driver-provider-aws
helm repo update secrets-store-csi-driver aws-secrets-manager
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --version 1.6.1 --namespace kube-system -f secrets-csi-values.yaml --wait --timeout 5m
helm install secrets-provider-aws aws-secrets-manager/secrets-store-csi-driver-provider-aws \
  --version 3.1.3 --namespace kube-system -f ascp-values.yaml --wait --timeout 5m
```

기존 설치에는 소유자의 버전·CRD upgrade 절차가 필요하며 신규 설치 명령이나 일부 값만 지정한 `helm upgrade`로 기존 구성을 덮어쓰지 않습니다. Chart 고정·render 성공만으로 node plugin 호환성·연결·secret 접근이 증명되지는 않습니다.

username·password 필드가 있는 소유 Secrets Manager JSON secret과 해당 secret으로 권한을 제한한 `ASCPSecretReader` 역할을 준비하고 필요한 경우 customer key decrypt 권한도 부여합니다. 아래 IRSA trust는 정확한 ServiceAccount subject를 사용하며 OIDC issuer·provider 전체와 계정을 일관되게 바꿔야 합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:aud": "sts.amazonaws.com",
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLEOIDCID:sub": "system:serviceaccount:security-secrets-demo:ascp-reader"
        }
      }
    }
  ]
}
```

아래 Namespace·ServiceAccount·SecretProviderClass·Pod는 파일 전달 예제입니다. 실제 클러스터에 맞는 PSS 버전을 선택합니다. JMESPath로 필드를 alias에 추출하고 `secretObjects.data.objectName`에는 해당 mounted alias를 지정합니다. secretObjects.data 안의 `property` 필드는 지원하지 않습니다. 0444 권한은 이 non-root 데모 process가 파일을 읽게 합니다. Mount·Pod 생성 권한을 제한하고 실제 앱에는 호환 UID·GID·파일 권한을 선택하세요.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ascp-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ASCPSecretReader
automountServiceAccountToken: false
---
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: db-secrets-files
  namespace: security-secrets-demo
spec:
  provider: aws
  parameters:
    region: us-west-2
    usePodIdentity: 'false'
    objects: |
      - objectName: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        objectType: secretsmanager
        objectAlias: credentials
        filePermission: '0444'
        jmesPath:
        - path: username
          objectAlias: db_username
        - path: password
          objectAlias: db_password
  secretObjects:
  - secretName: csi-db-credentials
    type: Opaque
    data:
    - objectName: db_username
      key: username
    - objectName: db_password
      key: password
---
apiVersion: v1
kind: Pod
metadata:
  name: secret-file-check
  namespace: security-secrets-demo
spec:
  serviceAccountName: ascp-reader
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: check
    image: busybox:1.37
    command:
    - sh
    - -c
    - test -s /mnt/secrets/db_username && test -s /mnt/secrets/db_password && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: secrets
      mountPath: /mnt/secrets
      readOnly: true
  volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: db-secrets-files
```

Pod는 파일 내용을 출력하지 않고 존재 여부만 검사합니다. `automountServiceAccountToken: false`는 자동 Kubernetes API token mount를 끄며 CSI driver의 명시적 token 요청을 끄는 설정은 아닙니다. 이 IRSA 예제 대신 Pod Identity를 사용하려면 workload ServiceAccount의 지원 agent·association과 `usePodIdentity: "true"`를 구성합니다. IRSA annotation이 association을 제공한다고 가정하지 않습니다.

선택적인 csi-db-credentials Secret은 Pod가 volume을 mount한 후에만 동기화됩니다. 수명 주기는 소비 Pod를 따르며 모든 소비자가 삭제되면 제거될 수 있습니다. SecretProviderClass 생성만으로 독립적인 Secret 생성기가 되지는 않습니다. 값을 출력하지 말고 SecretProviderClassPodStatus와 controller·node 이벤트를 확인합니다.

Parameter Store라면 objects 값에 다음 항목을 사용할 수 있습니다. 소유 parameter의 provider 필수 SSM 읽기 권한과 SecureString의 적절한 KMS 권한이 필요합니다. 이는 전체 SecretProviderClass가 아닌 objects 조각입니다:

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**ESO 대안:** 본문처럼 정확한 eso-reader ServiceAccount에 맞는 EKSSecretReader IRSA 역할·trust를 준비합니다. 소유자가 ESO 2.10.0·v1 CRD를 설치한 상태에서 다음은 다른 target인 eso-db-credentials를 기록합니다. Backend ARN·namespace·role·JSON 속성은 실제 준비한 secret을 가리켜야 합니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-secrets-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: eso-reader
  namespace: security-secrets-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSSecretReader
automountServiceAccountToken: false
---
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: security-secrets-demo
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: eso-reader
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: security-secrets-demo
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: eso-db-credentials
    creationPolicy: Owner
    deletionPolicy: Retain
  data:
    - secretKey: username
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: username
    - secretKey: password
      remoteRef:
        key: arn:aws:secretsmanager:us-west-2:123456789012:secret:training/db-credentials-ABC123
        property: password
```

Owner는 target Secret을 ExternalSecret에 연결하므로 owner 삭제 시 garbage collection될 수 있습니다. Retain은 backend 소실에 관한 설정이며 owner 삭제 방지가 아닙니다. ESO의 serviceAccountRef JWT 방식은 IRSA입니다. Controller Pod Identity는 controller ServiceAccount를 연결하고 store auth block을 생략하는 별도 설계이며 ESO가 serviceAccountRef로 다른 Pod Identity account를 impersonate할 수는 없습니다.

**Rotation·reload:** CSI 1.6+는 kubelet의 RequiresRepublish 요청을 rotation에 사용합니다. requiresRepublish만으로 rotation이 켜지지 않으며 driver의 enableSecretRotation도 필요합니다. 예제의 rotationPollInterval 2분은 최소 cache 유지 기간이지 전체 갱신이 2분 내 완료된다는 보장이 아닙니다. 실제 시점은 kubelet republish에 영향을 받으며 ESO refresh interval도 별도 reconciliation 일정입니다. 앱은 갱신 파일을 다시 열거나 감시하고 통제된 rollout을 수행해야 합니다. subPath mount와 기존 환경 변수는 자동 갱신되지 않습니다.

Secrets Manager rotate-secret은 기본적으로 즉시 rotation합니다. --no-rotate-immediately도 Lambda rotation 함수를 시험하며 AWSPENDING을 생성·제거할 수 있고 기존 rate·day 기반 일정이 실행될 수도 있습니다. 단순 일정 변경 전용·읽기 전용 검사가 아닙니다. 실행 전에 대상 credential 변경, 중첩 유효 기간, 앱 reload와 복구를 검토하세요.

**Secret 값이 없는 Terraform 예제:** Terraform sensitive는 일부 표시를 숨길 뿐 일반적인 secret_string·random_password 값은 state에 남을 수 있습니다. 아래는 승인된 기존 KMS key를 사용해 secret metadata만 관리합니다. 이미 존재하는 secret은 소유자를 통해 state·소유권을 조정하거나 import한 뒤 이 구성으로 관리합니다:

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "kms_key_arn" {
  type        = string
  description = "Existing approved Secrets Manager encryption key ARN in this Region"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_secretsmanager_secret" "credentials" {
  name                    = "training/db-credentials"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = 30
  lifecycle {
    prevent_destroy = true
  }
}

output "secret_arn" {
  value = aws_secretsmanager_secret.credentials.arn
}
```

이 구성은 secret version·값을 생성하거나 rotation을 활성화하지 않습니다. 초기 값은 하드코딩한 Terraform 문자열·평문 명령 인수 대신 승인한 secret 입력 경로로 전달합니다. Metadata만 예상하더라도 state·plan을 보호하세요. prevent_destroy는 Terraform 구성의 제어이며 되돌릴 수 없는 서비스 보호가 아닙니다. Resource 구성을 제거하거나 Terraform 밖에서 작업하면 보호 맥락이 달라집니다.

Kubernetes 기본·배포 SecretProviderClass·ESO CRD, 공개 chart checksum, CSI·ASCP render 객체 22개와 합성 데이터의 실제 JMESPath 추출을 검증했습니다. 생성된 null creationTimestamp는 Swagger schema 검사에서만 생략했습니다. Terraform fmt는 통과했으며 init·plan·apply는 실행하지 않았습니다. 실제 AWS secret 조회·mount·동기화·rotation·앱 reload는 시험하지 않았습니다.

참고: [ASCP 구성](https://github.com/aws/secrets-store-csi-driver-provider-aws), [CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1), [CSI Secret 동기화](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret), [CSI rotation](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation), [ESO AWS 인증](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md), [EKS envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [Secrets Manager rotation](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html).

</details>
