#!/usr/bin/env bash
# Step 2 - Move demo-irsa/s3-reader to IRSA.
source "$(dirname "$0")/00-env.sh"
cd "$(dirname "$0")"

ISSUER="$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.identity.oidc.issuer' --output text)"
OIDC_PROVIDER="${ISSUER#https://}"
echo "OIDC issuer: ${ISSUER}"

# 2-1. Register the cluster's OIDC issuer as an IAM identity provider (once per cluster).
if ! aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[].Arn' --output text \
     | tr '\t' '\n' | grep -q "${OIDC_PROVIDER}$"; then
  eksctl utils associate-iam-oidc-provider --cluster "$CLUSTER_NAME" --region "$AWS_REGION" --approve
fi

# 2-2. Role whose trust policy only accepts tokens for system:serviceaccount:demo-irsa:s3-reader.
TRUST="$(sed -e "s|ACCOUNT_ID|${ACCOUNT_ID}|g" -e "s|OIDC_PROVIDER|${OIDC_PROVIDER}|g" policies/irsa-trust.json.tpl)"
aws iam create-role --role-name "$IRSA_ROLE_NAME" --assume-role-policy-document "$TRUST" >/dev/null 2>&1 \
  || aws iam update-assume-role-policy --role-name "$IRSA_ROLE_NAME" --policy-document "$TRUST"
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" --policy-name s3-read \
  --policy-document "$(render policies/s3-read.json.tpl)"
IRSA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${IRSA_ROLE_NAME}"

# 2-3. Annotate the ServiceAccount. The webhook only mutates NEW pods -> restart.
kubectl -n demo-irsa annotate sa s3-reader "eks.amazonaws.com/role-arn=${IRSA_ROLE_ARN}" --overwrite
kubectl -n demo-irsa rollout restart deploy/whoami
kubectl -n demo-irsa rollout status deploy/whoami --timeout=180s

echo
echo "Injected by the webhook:"
kubectl -n demo-irsa exec deploy/whoami -- sh -c 'env | grep -E "^AWS_(ROLE_ARN|WEB_IDENTITY_TOKEN_FILE|STS_REGIONAL_ENDPOINTS)" | sort'
echo "Expected identity: arn:aws:sts::${ACCOUNT_ID}:assumed-role/${IRSA_ROLE_NAME}/botocore-session-..."
