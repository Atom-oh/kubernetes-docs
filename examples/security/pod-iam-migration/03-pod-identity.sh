#!/usr/bin/env bash
# Step 3 - Move demo-podid/s3-reader to EKS Pod Identity.
source "$(dirname "$0")/00-env.sh"
cd "$(dirname "$0")"

# 3-1. Pod Identity Agent add-on (DaemonSet, hostNetwork, 169.254.170.23:80).
if ! aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name eks-pod-identity-agent \
     --region "$AWS_REGION" >/dev/null 2>&1; then
  aws eks create-addon --cluster-name "$CLUSTER_NAME" --addon-name eks-pod-identity-agent --region "$AWS_REGION"
fi
aws eks wait addon-active --cluster-name "$CLUSTER_NAME" --addon-name eks-pod-identity-agent --region "$AWS_REGION"
kubectl -n kube-system rollout status ds/eks-pod-identity-agent --timeout=180s

# 3-2. Role trusted by the pods.eks.amazonaws.com service principal - no cluster-specific values.
aws iam create-role --role-name "$PODID_ROLE_NAME" \
  --assume-role-policy-document file://policies/podid-trust.json >/dev/null 2>&1 || true
aws iam put-role-policy --role-name "$PODID_ROLE_NAME" --policy-name s3-read \
  --policy-document "$(render policies/s3-read.json.tpl)"
PODID_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${PODID_ROLE_NAME}"

# 3-3. Association = (cluster, namespace, serviceaccount) -> role, stored in the EKS API.
#      Nothing is written to the ServiceAccount itself.
EXISTING="$(aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace demo-podid --service-account s3-reader --query 'associations[0].associationId' --output text)"
if [ "$EXISTING" = "None" ] || [ -z "$EXISTING" ]; then
  aws eks create-pod-identity-association --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
    --namespace demo-podid --service-account s3-reader --role-arn "$PODID_ROLE_ARN"
fi

# 3-4. Restart so the webhook injects the env vars + projected token.
kubectl -n demo-podid rollout restart deploy/whoami
kubectl -n demo-podid rollout status deploy/whoami --timeout=180s

echo
echo "Injected by the webhook:"
kubectl -n demo-podid exec deploy/whoami -- sh -c 'env | grep -E "^AWS_CONTAINER_" | sort'
echo "Expected identity: arn:aws:sts::${ACCOUNT_ID}:assumed-role/${PODID_ROLE_NAME}/eks-${CLUSTER_NAME}-whoami-..."
