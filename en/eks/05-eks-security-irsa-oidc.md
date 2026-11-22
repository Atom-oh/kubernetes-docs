# IRSA and the OIDC Provider

> **Last Updated**: November 21, 2026

This page is the detailed split-out of the "OIDC Provider Deep Dive" section of [Amazon EKS Security](./05-eks-security.md). It covers how the cluster OIDC issuer relates to an IAM OIDC provider, how an IRSA token becomes temporary credentials through STS, discovery/JWKS inspection, and a scoped IRSA role and Job example. The examples use the `security-demo` namespace prepared on the [cluster access](./05-eks-security-cluster-access.md#access-entries-and-namespace-authorization) page. A step-by-step IRSA flow diagram is also in [How IRSA works](../security/17-eks-workload-identity-migration.md#irsa-flow).

## Table of Contents

1. [OIDC Issuer and IAM OIDC Provider](#oidc-issuer-and-iam-oidc-provider)
2. [IRSA Token and Role Exchange](#irsa-token-and-role-exchange)
3. [Discovery and JWKS Inspection](#discovery-and-jwks-inspection)
4. [A Scoped IRSA Example](#a-scoped-irsa-example)

## OIDC Issuer and IAM OIDC Provider

EKS publishes a cluster OIDC issuer and public signing keys. That endpoint alone does not create an IAM OIDC provider or authorize role assumption. For IRSA, the role account must have the intended IAM OIDC provider, the role must trust it with the correct issuer/subject/audience conditions, and the workload must use a compatible SDK.

![Sequence diagram showing a pod exchanging its projected Kubernetes service account JWT with AWS STS via AssumeRoleWithWebIdentity, STS validating the token against the EKS OIDC provider's JWKS and the IAM role trust policy, then returning temporary credentials the pod uses to call an AWS service.](../.gitbook/assets/en-eks-05-eks-security-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-3.html)

## IRSA Token and Role Exchange

The IRSA webhook adds a projected token/role configuration to an eligible Pod. The SDK exchanges the web-identity token with STS using AssumeRoleWithWebIdentity. STS validates the issuer/signature/token and role trust, then returns temporary AWS credentials. The application uses those credentials for its permitted AWS operations. Kubernetes rotates the projected token; the SDK refreshes AWS credentials. These are different lifetimes.

This is an illustrative **decoded payload shape**, with deliberately old/expired timestamps and placeholder identities. It is not a signed token or an authentication test. The STS audience is for the IRSA path; Pod Identity uses a different audience:

```json
{
  "aud": [
    "sts.amazonaws.com"
  ],
  "exp": 1234567890,
  "iat": 1234567800,
  "iss": "https://oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID",
  "kubernetes.io": {
    "namespace": "security-demo",
    "pod": {
      "name": "irsa-read-check-example",
      "uid": "example-pod-uid"
    },
    "serviceaccount": {
      "name": "irsa-reader",
      "uid": "example-serviceaccount-uid"
    }
  },
  "sub": "system:serviceaccount:security-demo:irsa-reader"
}
```

Validate issuer, audience, expiration and the expected subject, not only whether JSON can be decoded. Keep raw tokens, AWS secret access keys and session tokens out of examples/logs. A role can trust multiple explicitly permitted service accounts or issuers; IRSA does not require exactly one role per ServiceAccount.

## Discovery and JWKS Inspection

Use the issuer returned for the actual cluster. This diagnostic retrieves public discovery/JWKS documents and checks the discovery issuer/HTTPS scheme. It does not validate a workload token or IAM permissions:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster}"
: "${AWS_REGION:?Set its Region}"
OIDC_URL=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text)
case "$OIDC_URL" in https://*) ;; *) echo "Unexpected issuer URL"; exit 1 ;; esac
curl --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 20 \
  "${OIDC_URL%/}/.well-known/openid-configuration" > oidc-discovery.json
JWKS_URI=$(python3 - "$OIDC_URL" <<'PY'
import json, sys, urllib.parse
with open("oidc-discovery.json") as stream:
    doc = json.load(stream)
if doc["issuer"] != sys.argv[1]:
    raise SystemExit("Discovery issuer does not match the cluster issuer")
uri = doc["jwks_uri"]
parsed = urllib.parse.urlparse(uri)
if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
    raise SystemExit("JWKS must be an HTTPS URL without embedded credentials")
print(uri)
PY
)
curl --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 20 \
  "$JWKS_URI" > oidc-jwks.json
python3 - <<'PY'
import json
with open("oidc-jwks.json") as stream:
    keys = json.load(stream).get("keys")
if not isinstance(keys, list) or not keys or not all(isinstance(k, dict) and "kty" in k for k in keys):
    raise SystemExit("Unexpected JWKS response")
print("Fetched", len(keys), "public keys; no token signature was validated")
PY
```

Automated validators must cache keys according to Cache-Control and handle signing-key rotation/unknown kid using a reviewed JWT library. EKS rotates its OIDC signing key every seven days. Current EKS also supports a PrivateLink interface endpoint for cluster OIDC discovery/JWKS, `com.amazonaws.region-code.oidc-eks`, for validators without internet egress. Verify that endpoint’s region/DNS requirements; an EKS management API endpoint is a different service.

## A Scoped IRSA Example

Prepare the IAM OIDC provider, role and bucket through their owners. Replace the account, complete issuer hostname/path and role ARN consistently; IPv6 clusters can use the dual-stack issuer hostname. This example binds only security-demo/irsa-reader and the STS audience; it is a new role trust example, not a replacement for an existing role’s other trust statements:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID:sub": "system:serviceaccount:security-demo:irsa-reader",
          "oidc.eks.us-west-2.amazonaws.com/id/REPLACE_WITH_CLUSTER_ISSUER_ID:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

The read policy allows a specific bucket prefix. Add only the required KMS permissions when objects use a customer managed encryption key, and review bucket/endpoint policies. No account-wide AmazonS3ReadOnlyAccess policy is required for this one-prefix example:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-security-bucket",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "security-demo/",
            "security-demo/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-security-bucket/security-demo/*"
    }
  ]
}
```

After preparing the [security-demo namespace](./05-eks-security-cluster-access.md#access-entries-and-namespace-authorization) and role, create the ServiceAccount and bounded listing Job below. The official AWS CLI image includes the client; an arbitrary amazonlinux:2 image does not guarantee that. Replace bucket/Region/role values. The Job lists a prefix without printing secret values; success of this operation is not proof of every application GetObject/KMS permission.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: irsa-reader
  namespace: security-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/SecurityDemoIRSAReader
---
apiVersion: batch/v1
kind: Job
metadata:
  name: irsa-read-check
  namespace: security-demo
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: irsa-reader
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: reader
        image: public.ecr.aws/aws-cli/aws-cli:2.36.43
        command:
        - aws
        args:
        - s3api
        - list-objects-v2
        - --bucket
        - replace-with-owned-security-bucket
        - --prefix
        - security-demo/
        - --max-items
        - '5'
        env:
        - name: AWS_REGION
          value: us-west-2
        - name: AWS_EC2_METADATA_DISABLED
          value: 'true'
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        volumeMounts:
        - name: private-home
          mountPath: /root
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: private-home
        emptyDir: {}
      - name: tmp
        emptyDir: {}
      nodeSelector:
        kubernetes.io/os: linux
```

## References

- [EKS IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [IRSA minimum SDK versions](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html)
- [Migrate EKS node IAM permissions to IRSA and Pod Identity](../security/17-eks-workload-identity-migration.md)

## Next Steps

- Previous: [EKS Cluster Access Authentication: IAM and Access Entries](./05-eks-security-cluster-access.md)
- Next: [EKS Pod Identity](./05-eks-security-pod-identity.md)
- Back to the overview: [Amazon EKS Security](./05-eks-security.md)

## Quiz

To test what you learned in this chapter, try the [topic quiz](../quizzes/eks/05-eks-security-irsa-oidc-quiz.md).
