#!/usr/bin/env bash
# Step 6 (optional) - Move an IRSA workload to Pod Identity without downtime.
# Order matters: make the new path work BEFORE removing the old one.
source "$(dirname "$0")/00-env.sh"
cd "$(dirname "$0")"
IRSA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${IRSA_ROLE_NAME}"

# 6-1. Dual trust: keep the OIDC statement, add the pods.eks.amazonaws.com statement.
CURRENT="$(aws iam get-role --role-name "$IRSA_ROLE_NAME" --query 'Role.AssumeRolePolicyDocument' --output json)"
MERGED="$(echo "$CURRENT" | python3 -c '
import json,sys
doc=json.load(sys.stdin)
podid={"Sid":"AllowEksPodIdentity","Effect":"Allow","Principal":{"Service":"pods.eks.amazonaws.com"},
       "Action":["sts:AssumeRole","sts:TagSession"]}
if not any(s.get("Sid")=="AllowEksPodIdentity" for s in doc["Statement"]):
    doc["Statement"].append(podid)
print(json.dumps(doc))')"
aws iam update-assume-role-policy --role-name "$IRSA_ROLE_NAME" --policy-document "$MERGED"

# 6-2. Association for the same SA (agent add-on must already be installed - see step 3).
aws eks create-pod-identity-association --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace demo-irsa --service-account s3-reader --role-arn "$IRSA_ROLE_ARN" || true

# 6-3. Remove the IRSA annotation. While both are configured, check which env vars the pod
#      actually received: AWS SDK default chains evaluate web identity (IRSA) BEFORE
#      container credentials (Pod Identity), so a leftover annotation keeps IRSA in use.
kubectl -n demo-irsa annotate sa s3-reader eks.amazonaws.com/role-arn-
kubectl -n demo-irsa rollout restart deploy/whoami
kubectl -n demo-irsa rollout status deploy/whoami --timeout=180s
kubectl -n demo-irsa exec deploy/whoami -- sh -c 'env | grep -E "^AWS_(ROLE_ARN|WEB_IDENTITY|CONTAINER_)" | sort'

# 6-4. After the bake period, delete the OIDC statement from the trust policy
#      (and the OIDC provider once no role references it).
echo "Bake, then remove the Federated statement from ${IRSA_ROLE_NAME}'s trust policy."
