#!/usr/bin/env bash
source "$(dirname "$0")/00-env.sh"
NODE_ROLE="$(node_role_name)"

kubectl delete ns demo-node demo-irsa demo-podid --ignore-not-found
kubectl -n default delete pod neighbor --ignore-not-found

for id in $(aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
            --query 'associations[?starts_with(namespace, `demo-`)].associationId' --output text); do
  aws eks delete-pod-identity-association --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" --association-id "$id"
done
for r in "$IRSA_ROLE_NAME" "$PODID_ROLE_NAME"; do
  for p in $(aws iam list-role-policies --role-name "$r" --query 'PolicyNames' --output text 2>/dev/null); do
    aws iam delete-role-policy --role-name "$r" --policy-name "$p"
  done
  aws iam delete-role --role-name "$r" 2>/dev/null || true
done
aws iam delete-role-policy --role-name "$NODE_ROLE" --policy-name "$LEGACY_POLICY_NAME" 2>/dev/null || true
aws s3 rm "s3://${DEMO_BUCKET}" --recursive && aws s3api delete-bucket --bucket "$DEMO_BUCKET"
echo "Left in place: OIDC provider, eks-pod-identity-agent add-on, node IMDS settings."
