# Amazon EKS Security Quiz

> **Last Updated**: September 11, 2026

This quiz tests your understanding of Amazon EKS security features, best practices, and configurations.

## Quiz Overview
- EKS Authentication and Authorization
- Network Security
- Container Security
- Data Security
- Compliance and Auditing
- Security Best Practices

## Multiple Choice Questions

### 1. For an IAM user or role, which EKS setup correctly combines identity authentication and Kubernetes authorization?

- A) Use only IAM management permissions
- B) Create RBAC rules without configuring the identity’s authentication path
- C) Configure IAM cluster access plus appropriate RBAC and/or EKS access policies
- D) Use only API endpoint network restrictions

<details>
<summary>Show Answer</summary>

**Answer: C) Configure IAM cluster access plus appropriate RBAC and/or EKS access policies**

**Explanation:**

IAM authenticates the intended human/automation identity through the configured EKS access path. Kubernetes RBAC and EKS access policies authorize Kubernetes operations; their grants are additive. Network restrictions are another layer and do not replace authorization. Pod-to-Kubernetes authentication normally uses its ServiceAccount token; IRSA/Pod Identity instead supplies workload AWS credentials.

An EKS cluster service role and a human developer role have different purposes. Attaching AmazonEKSClusterPolicy to the developer does not grant Kubernetes access, and DescribeCluster/ListClusters permissions or a kubeconfig file do not grant workload permissions.

**Scoped implementation:** an authorized platform operator prepares the namespace and RBAC below for an existing approved developer IAM role. The cluster must already support access entries. Preserve existing administrator/node mappings and review authentication-mode migration; do not overwrite aws-auth with a sample ConfigMap.

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

The group name in the access entry must match the RoleBinding subject. This role permits the listed operations only in security-demo; other existing grants can broaden access. Creating Deployments/Jobs can indirectly use Secrets, PVCs and ServiceAccounts in that namespace, so absence of a direct Secret-read rule is not a tenant security boundary. Separate tenants and constrain workload identity/resource use through admission and ownership controls.

A separately reviewed viewer can instead use a namespace-scoped AmazonEKSViewPolicy association. Inspect existing access policies before adding it; it does not revoke broader RBAC or other access-policy grants. `eks:namespaces` filters access-policy association requests, not general kubectl requests.

**Validate the actual login:** the caller must be able to discover the cluster and assume the approved role. This creates a temporary kubeconfig rather than replacing the default context:

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

Inspect the results against the intended grants and investigate unexpected cross-namespace permission. `--as` tests impersonation/RBAC and does not establish that the IAM access-policy path works. No live IAM login or Kubernetes authorization test was executed for this quiz; schema/shell checks and mocked access-entry flows are the local evidence.

References: [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

</details>

### 2. Which Kubernetes mechanism expresses label-based Pod traffic rules on an EKS network that supports policy enforcement?

- A) Only instance security groups
- B) NetworkPolicy resources with an enforcing network implementation
- C) Only VPC endpoint policies
- D) Only host firewall commands

<details>
<summary>Show Answer</summary>

**Answer: B) NetworkPolicy resources with an enforcing network implementation**

**Explanation:**

NetworkPolicy selects Pods and permitted traffic using Kubernetes labels and namespaces. It requires an enforcing network implementation. Security groups, including supported security groups for Pods, remain useful AWS controls; they are not limited to whole instances. VPC endpoint policies govern supported AWS service access, not arbitrary label-based Pod traffic.

**Complete policy example:** these manifests describe an isolated demonstration namespace, not an installation of applications or a replacement CNI. They assume standard Linux EC2 nodes with a supported enforcing CNI and the usual CoreDNS Deployment/Pod labels. Auto Mode or node-local DNS requires rules for the resolver path actually used. If CoreDNS ingress is restricted, its owner must also permit these queries.

Save and apply through the namespace owner. Default deny isolates both directions; client egress and destination ingress are explicitly allowed for frontend → API and API → database. DNS needs both UDP and TCP:

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

The monitoring peer uses namespaceSelector **and** podSelector in one peer, so only matching Prometheus Pods in security-monitoring-demo are selected. Its outgoing connection also needs permission when that client is egress-isolated:

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

| Flow | Intended result with these policies |
|---|---|
| frontend → api TCP 8080 | Allow |
| api → database TCP 5432 | Allow |
| frontend → database TCP 5432 | Deny |
| unrelated Pod → api TCP 8080 | Deny |
| selected Prometheus → api TCP 9090 | Allow |
| another Pod in the monitoring namespace → api TCP 9090 | Deny |
| workload → matching CoreDNS Pod UDP/TCP 53 | Allow, subject to resolver-side controls |
| arbitrary external destination | Deny unless an explicit egress rule is added |

Policies are additive and unordered. Another broad allow can widen the result; default deny does not override it. Test the complete installed policy set, DNS resolution and new allowed/denied connections on the target CNI. Established connections, hostNetwork/node traffic and NAT behavior have implementation-specific limits; a simple NetworkPolicy is not a universal IMDS or host-firewall boundary.

For external services, scope actual destination addresses/ports or use the chosen implementation’s supported DNS-aware controls. Allowing every destination on port 443 or the entire 10.0.0.0/8 range is not a service allowlist. An arbitrary replacement Calico/Cilium manifest or partial kube-proxy-replacement flag is not a safe way to enable policy on an existing EKS network.

The paired source’s 18 synthetic selector/port cases were checked locally; no packet/CNI test was executed. Reference: [Kubernetes NetworkPolicy behavior](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

</details>

### 3. Which approach combines complementary controls for container image security on EKS?

- A) Rely only on manual image inspection
- B) Assume every official image is free of vulnerabilities
- C) Combine scanning, signing/verification and admission controls
- D) Rely only on antivirus inside the container

<details>
<summary>Show Answer</summary>

**Answer: C) Combine scanning, signing/verification and admission controls**

**Explanation:**

A scanner identifies the issues covered by its rules and vulnerability database; it does not prove that every backdoor or future vulnerability is absent. A signature proves integrity and an identity relationship under the configured trust policy, not that the signed software is safe. Admission controls enforce the selected deployment policy. Use maintained minimal base images, rebuild for patches, track exceptions and select the appropriate ECR basic/enhanced or other scanning mode.

**AWS Signer and Notation:** the container signing platform is `Notation-OCI-SHA384-ECDSA`. Use the Notation AWS Signer plugin to sign an image that has already been pushed, by digest. An `Aws::ECR::Image` platform or `start-signing-job --source-image` is not the supported workflow. The reviewed AWS CLI rejects that option.

Current ECR managed signing is also a supported push-triggered alternative with registry signing rules. If choosing it, configure the correct profile/permissions and wait for the actual signing status before promotion. Do not assume the presence of a pushed image proves that asynchronous signing completed.

**Trust configuration:** prepare a verified Notation/Signer plugin installation, the correct partition’s AWS Signer root trust store, and a reviewed strict trust policy. This commercial-Region example limits trust to one repository and an approved profile. Replace every account/Region/repository/profile consistently; do not trust any signer merely because its certificate chains to the AWS root.

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

Import that policy into the build environment’s owned Notation configuration with `notation policy import notation-trust-policy.json`. Review any existing policy before replacement; do not overwrite a developer’s shared trust configuration from an unreviewed script. The build role needs repository-scoped ECR pull/push operations, ECR authentication and the required SignPayload/GetRevocationStatus permissions. Creating the signing profile is a separate provisioning responsibility; the build does not need PutSigningProfile merely to use an existing approved profile.

**CodeBuild example:** this is a buildspec, not a CodePipeline definition. It requires an owned Linux build image with Bash, Python, Docker/daemon access, AWS CLI, Trivy, Notation and the AWS Signer plugin already installed and version-pinned. Configure the project’s required runtime privilege, network access, scanner databases, IAM role, trust store/policy and existing ECR repository separately. The Dockerfile and source are trusted inputs to that build role. This example uses a resolved Git commit and one commercial AWS account/Region; it does not implement a cross-account signing design.

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

Set `AWS_ACCOUNT_ID`, `AWS_REGION`, `ECR_REPOSITORY` (for example `team/app`) and `SIGNING_PROFILE_ARN` through reviewed project configuration. The command authenticates to the registry hostname, retains nested repository paths, scans the locally built image before push, and selects the matching pushed RepoDigest instead of an arbitrary first entry or a mutable tag. Trivy here gates HIGH/CRITICAL vulnerability findings; add other explicitly designed checks for secrets, configuration and provenance.

All promotion steps are in one Bash build block with `set -euo pipefail`. A failed login/build/scan/push/sign/verify stops before a new artifact is written. CodeBuild post_build can run after a failed build, so a separate unguarded post_build push/sign step is unsafe. The reserved artifact path is cleared first to prevent reuse of a previous output. Downstream deployment must also require a successful build and validate the artifact; the JSON file alone is not an authorization or a signed attestation.

`verified-image.json` contains the exact digest reference for an EKS deployment/GitOps consumer. It is not ECS `imagedefinitions.json` and does not itself deploy anything. Successful signing/verification still depends on actual registry access, trust, revocation checks and AWS Signer availability.

**Admission:** a production signature verifier must understand the chosen Notation/Signer signature and trust policy. AWS documents Gatekeeper with Ratify and Kyverno with an AWS Signer/Notation integration. Installing a generic policy engine, a bare Gatekeeper constraint without its ConstraintTemplate, or a public-key field for a different signature scheme does not establish that integration. Validate trusted/untrusted profiles, unsigned images, digest mismatches, revoked/expired signatures, verifier outages and admission failure policy before enforcement.

The following separate Kyverno 1.19.1 rule only restricts **image reference syntax and repository** in security-demo. It checks regular, init and ephemeral containers. It deliberately does **not** claim to verify a signature:

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

Validation: 20 mocked pipeline failure/order/artifact cases and nine actual Kyverno CLI string-policy cases. Buildspec/Bash/Python/JSON and the released policy CRD were checked. No image was built/scanned/pushed, no real AWS signature was produced or verified, and no admission webhook was deployed. This is a reviewed teaching workflow with explicit environment assumptions, not tested production readiness.

References: [Signer signing](https://docs.aws.amazon.com/signer/latest/developerguide/image-signing-steps.html), [Signer verification](https://docs.aws.amazon.com/signer/latest/developerguide/image-verification.html), [ECR managed signing](https://docs.aws.amazon.com/AmazonECR/latest/userguide/managed-signing.html), [EKS admission verification](https://docs.aws.amazon.com/eks/latest/userguide/image-verification.html), [CodeBuild buildspec](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html), [Trivy image flags](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/).

</details>

### 4. Which approach applies a coherent, current Pod security baseline on EKS?

- A) Only disable privileged mode
- B) Use versioned PSS profiles through PSA, with reviewed admission policies where needed
- C) Only set a non-root UID
- D) Only make the root filesystem read-only

<details>
<summary>Show Answer</summary>

**Answer: B) Use versioned PSS profiles through PSA, with reviewed admission policies where needed**

**Explanation:**

Pod Security Standards define Privileged, Baseline and Restricted profiles. Pod Security Admission enforces namespace-selected profiles. PSA is stable since Kubernetes 1.25; PodSecurityPolicy was deprecated in 1.21 and **removed in 1.25**. A current cluster cannot deploy that removed API. Kyverno/Gatekeeper policies are separate resources, even if an older example uses “PSP” in a constraint name.

An isolated Linux demonstration with a reviewed v1.36 profile is:

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

Namespace enforce applies to Pod admission. Audit/warn can report controller-template violations, but successful Deployment/Job apply does not prove its Pods pass enforcement. Changing labels does not retroactively evict existing Pods. Select a policy version for the actual cluster and review existing workloads before enforcement.

runAsNonRoot/runAsUser and seccomp are distinct from allowPrivilegeEscalation and capabilities. fsGroup is a Pod-level volume ownership setting, not a container capability. Read-only root is useful application-compatible hardening but is not a universal PSS Restricted requirement and does not make mounted PVCs read-only. Real applications need compatible UID/GID and writable temporary/cache/socket paths; a generic root-oriented nginx image is not made functional by merely adding these fields.

**An additional scoped admission rule:** this Kyverno 1.19.1 ValidatingPolicy checks all regular, init and ephemeral containers in security-demo. Missing privileged is accepted as false; true is denied. It uses the current v1 policy API rather than an obsolete installation manifest:

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

This one rule does not replace the entire PSS profile or image verification. Keep privileged CSI/monitoring agents and deliberate exceptions under their platform owner; do not blanket-apply a demo policy to kube-system. A Gatekeeper alternative needs its actual ConstraintTemplate, matching constraint and validated behavior.

The manifest/schema and six actual Kyverno CLI cases cover omitted/false, privileged regular/init/ephemeral containers and another namespace. Ephemeral-container testing uses a synthetic UPDATE object, not Pod creation. No live admission webhook or Pod deployment was executed.

References: [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/), [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/).

</details>

### 5. Which approach gives complementary security evidence for an EKS workload?

- A) Use only occasional manual reviews
- B) Use only AWS Config checks
- C) Use only GuardDuty
- D) Combine posture findings, audit logs, runtime coverage and a verified response path

<details>
<summary>Show Answer</summary>

**Answer: D) Combine posture findings, audit logs, runtime coverage and a verified response path**

**Explanation:**

| Evidence/control | What it contributes and does not prove |
|---|---|
| Security Hub CSPM / AWS Config | Supported configuration controls and findings; not complete Kubernetes or regulatory certification |
| GuardDuty EKS Protection | Kubernetes audit-based threat analysis through an independent stream |
| GuardDuty Runtime Monitoring | Agent-based runtime events on supported nodes; enabled status alone is not coverage |
| CloudTrail | AWS API activity; it does not replace Kubernetes audit or application data-access logs |
| Kubernetes audit logs | Requests selected by the audit policy/level, not every workload action/body |
| CloudWatch / incident routing | Log analysis and delivery to operators; delivery, retention and response must be verified |

Security Hub CSPM’s FSBP standard is not the CIS Kubernetes Benchmark. Supported CIS AWS Foundations controls are also not a complete CIS Kubernetes audit. Record the applicable benchmark/version, manual checks, managed-service exceptions and the evidence required for the workload’s actual obligations.

Use the existing organization/Region ownership for detectors, CSPM standards, Config recorders and CloudTrail. Do not create another regional detector, overwrite centralized configuration or start a trail without its prepared bucket policy, encryption, event selectors and retention. CloudTrail data events are separate from default management-event coverage. No account-level monitoring resources were provisioned in this review.

**EKS-specific checks:** enable and confirm the intended control plane log types, update completion and log arrival as shown in the source chapter. Both `eks-cluster-logging-enabled` (all types, periodic) and `eks-cluster-log-enabled` (optional selected types, configuration changes) are valid Config rules. Maintain the `oldestVersionSupported` parameter instead of assuming an automatic current-version catalog. An explicit encryptionConfig control finding does not mean EKS 1.28+ API data lacks default envelope encryption.

GuardDuty audit analysis does not require your separate CloudWatch audit export. Runtime Monitoring needs the supported security agent/data endpoint and actual coverage; current EKS support includes EC2 and Auto Mode, not Fargate or Hybrid Nodes. Use the current RUNTIME_MONITORING feature and review legacy EKS_RUNTIME_MONITORING migration. Do not mistake EKS_AUDIT_LOGS for runtime monitoring.

**CSPM event routing example:** save this as `security-event-pattern.json`. It selects active HIGH/CRITICAL ASFF findings with NEW/NOTIFIED workflow status. It intentionally does not match the different `Findings Imported V2` OCSF event schema:

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

This synthetic event is for pattern checking only; it is not a real finding or a complete ASFF import payload. Save as `synthetic-security-event.json`:

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

In an authorized AWS test, `aws events test-event-pattern --event-pattern file://security-event-pattern.json --event file://synthetic-security-event.json --region us-west-2` should match. Also test LOW severity, RESOLVED/SUPPRESSED workflow, ARCHIVED state, missing fields and the V2 event type; those should not match this pattern. This review checked the JSON/source schema, not the EventBridge service’s matcher or live event delivery.

A target configuration can use an **existing reviewed EventBridge execution role** with publish permission on the owned SNS topic, as supported by the current EventBridge guide. Save as `security-event-targets.json` after substituting owned ARNs:

```json
[
  {
    "Id": "SecurityAlerts",
    "Arn": "arn:aws:sns:us-west-2:123456789012:eks-security-alerts",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSecurityAlerts"
  }
]
```

The role needs the correct EventBridge trust and least-privilege sns:Publish permission; inspect applicable topic/key policies and any explicit denies. Alternatively, a target without an execution role needs its supported resource-based permission path. The target JSON alone grants no permission and does not create the rule, topic, role or subscription.

Before using `aws events put-targets --rule eks-security-alerts --targets file://security-event-targets.json --region us-west-2`, inspect existing rule/target ownership. Check FailedEntryCount and FailedEntries, not only the command’s exit status. Confirm SNS subscriptions, encryption permissions, retry/dead-letter behavior and an end-to-end controlled delivery test. No notification was sent during this audit.

**Audit investigation:** in the actual EKS log group, this Logs Insights example assumes JSON field discovery for Kubernetes audit records. It focuses on RBAC mutation requests; inspect responseStatus.code to distinguish successful and rejected requests:

```text
fields @timestamp, verb, user.username, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter verb in ["create", "update", "patch", "delete", "deletecollection"]
| filter objectRef.resource in ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
| sort @timestamp desc
| limit 100
```

Verify a sampled record’s fields and the stream name before relying on the query. Preserve relevant evidence, define ownership/severity/escalation and test the response process. Finding dashboards and enabled services are not evidence that remediation completed or a compliance obligation was met.

References: [CSPM standards](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-view-manage.html), [ASFF events](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-cwe-event-formats.html), [V2 events](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-v2-cwe-event-formats.html), [EventBridge target permissions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html), [EKS audit logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html).

</details>

### 6. For application credentials requiring centrally governed AWS access and lifecycle management, which approach fits?

- A) Store values without an access, rotation or reload plan
- B) Treat environment variables as an encryption mechanism
- C) Use an appropriate AWS secret/parameter backend with scoped identity and an explicit delivery/lifecycle design
- D) Hardcode production credentials in the image

<details>
<summary>Show Answer</summary>

**Answer: C) Use an appropriate AWS secret/parameter backend with scoped identity and an explicit delivery/lifecycle design**

**Explanation:**

Secrets Manager and Parameter Store can centralize AWS access controls and auditing, but an external backend is not automatically secure without workload identity, least privilege, delivery and reload controls. Secrets Manager supports configured rotation for supported credentials; Parameter Store does not provide the same built-in credential-rotation workflow. A SecureString parameter’s KMS encryption and versioning are different from changing the credential in the target database/service.

EKS 1.28+ already encrypts all Kubernetes API data with default KMS v2 envelope encryption. Base64 in a Secret manifest is still only encoding, and API/Pod access can expose the value. Environment variables are a delivery mechanism, not encryption; existing process environments do not update when a Secret changes.

**Choose ownership and delivery deliberately:** ESO writes a Kubernetes Secret. ASCP with Secrets Store CSI Driver mounts files, and can optionally synchronize a Kubernetes Secret. Do not let both controllers manage the same target Secret. A file-only CSI design still needs workload/node access controls; optional synchronization also introduces a Kubernetes API copy of the value.

**ASCP example:** this is a new owned Linux EC2 installation for the reviewed EKS 1.36 example, not a rollout into an unknown existing cluster. First inspect existing releases/CSIDriver ownership, node compatibility, privileged platform-agent admission, network access and scheduling. Fargate cannot run the CSI node DaemonSet. Hybrid/Auto Mode use requires their current provider/node prerequisites; it is not verified by the following local render.

Use these `secrets-csi-values.yaml` settings for a separately managed CSI 1.6.1 driver. They explicitly configure both AWS token audiences, optional Secret synchronization and rotation:

```yaml
tokenRequests:
- audience: sts.amazonaws.com
- audience: pods.eks.amazonaws.com
syncSecret:
  enabled: true
enableSecretRotation: true
rotationPollInterval: 2m
```

ASCP chart 3.1.3 normally includes the driver as a dependency and configures its token audiences. Because this example installs the driver separately, save the following as `ascp-values.yaml` to avoid a second driver:

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

Existing installations need their owner’s version/CRD upgrade procedure; do not run these fresh-install commands or a partial `helm upgrade` over unrelated values. Chart pinning and successful rendering do not prove node plugin compatibility, connectivity or secret access.

Prepare an owned Secrets Manager JSON secret with username/password fields and a role `ASCPSecretReader` scoped to that exact secret, plus the appropriate customer-key decrypt permission if needed. This IRSA trust uses the precise ServiceAccount subject; replace the complete OIDC issuer/provider and account consistently:

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

The Namespace, ServiceAccount, SecretProviderClass and Pod below form the file-delivery example. Select the PSS version appropriate to the actual cluster. JMESPath extracts fields into aliases; `secretObjects.data.objectName` names those mounted aliases. A `property` field inside secretObjects.data is not supported. Permissions 0444 make these files readable to this non-root demonstration process; limit who can mount/create Pods and choose compatible UID/GID/file permissions for a real application.

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

The Pod checks that files exist without printing their contents. `automountServiceAccountToken: false` disables the automatic Kubernetes API token mount, not the CSI driver’s explicit token requests. For Pod Identity instead of this IRSA example, use a supported agent/association for the workload ServiceAccount and `usePodIdentity: "true"`; do not assume an IRSA annotation supplies that association.

The optional csi-db-credentials Secret is synchronized only after a Pod mounts the volume. Its lifecycle follows consuming Pods and it can be removed when all consumers are deleted. Creating SecretProviderClass alone is not a standalone Secret generator. Inspect SecretProviderClassPodStatus and controller/node events without dumping values.

For Parameter Store, the objects value can instead contain the following entry, with the provider’s required SSM read permission on the owned parameter and appropriate KMS access for SecureString. This is an objects fragment, not a complete SecretProviderClass:

```yaml
- objectName: /training/app/config
  objectType: ssmparameter
  objectAlias: app_config
  filePermission: "0444"
```

**ESO alternative:** use the source chapter’s prepared EKSSecretReader IRSA role/trust for the exact eso-reader ServiceAccount. With ESO 2.10.0 and its v1 CRDs installed under their owner, the following writes a different target, eso-db-credentials. The backend ARN, namespace, role and JSON properties must refer to the actual prepared secret:

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

Here Owner ties the target Secret to the ExternalSecret; deleting the owner can trigger garbage collection. Retain concerns backend disappearance, not immunity from owner deletion. ESO’s serviceAccountRef JWT method is IRSA. Controller Pod Identity is a different design: associate the controller ServiceAccount and omit the store auth block; ESO cannot use serviceAccountRef to impersonate another Pod Identity-associated account.

**Rotation and reload:** CSI 1.6+ uses kubelet RequiresRepublish calls for rotation. requiresRepublish alone does not enable rotation: the driver’s enableSecretRotation flag is also required. The two-minute rotationPollInterval here is a minimum cache duration, not a guaranteed two-minute end-to-end update interval; actual timing depends on kubelet republish. ESO’s refresh interval is another independent reconciliation schedule. Applications must reopen/watch updated files or perform a controlled rollout; subPath mounts and existing environment variables do not automatically refresh.

Secrets Manager rotate-secret defaults to immediate rotation. Even --no-rotate-immediately can test a Lambda rotation function and create/remove AWSPENDING, while an older rate/day-based schedule may still run. It is not a harmless schedule-only or read-only check. Review target credential changes, overlapping validity, application reload and rollback before invoking rotation.

**Terraform example without secret values:** Terraform sensitive only suppresses selected display output; ordinary secret_string/random_password values can still be stored in state. The following manages only secret metadata, using an existing approved KMS key. For an already existing secret, reconcile/import it through the owner before managing it in this configuration:

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

This creates no secret version/value and enables no rotation. Supply the initial value through the approved secret-input process, not a hardcoded Terraform string or plaintext command argument. Protect state and plans even when only metadata is expected. prevent_destroy is a Terraform configuration guard, not an irreversible service protection; removing the resource configuration or operating outside Terraform changes the protection context.

Validation covered native Kubernetes and the released SecretProviderClass/ESO CRDs, published chart checksums, 22 rendered CSI/ASCP objects and actual JMESPath projection of synthetic data. Generated null creationTimestamp fields were omitted only for the Swagger schema check. Terraform fmt passed; no init/plan/apply was run. No AWS secret was fetched, mounted, synchronized or rotated, and no application reload was tested.

References: [ASCP configuration](https://github.com/aws/secrets-store-csi-driver-provider-aws), [CSI 1.6.1](https://github.com/kubernetes-sigs/secrets-store-csi-driver/releases/tag/v1.6.1), [CSI Secret synchronization](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret), [CSI rotation](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation), [ESO AWS authentication](https://github.com/external-secrets/external-secrets/blob/v2.10.0/docs/provider/aws-access.md), [EKS envelope encryption](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html), [Secrets Manager rotation](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/rotate-secret.html).

</details>
