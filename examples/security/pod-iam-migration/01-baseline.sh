#!/usr/bin/env bash
# Step 1 - Reproduce the "legacy" state: S3 access granted to the NODE role.
source "$(dirname "$0")/00-env.sh"
cd "$(dirname "$0")"

NODE_ROLE="$(node_role_name)"
echo "Node role: ${NODE_ROLE}"

# Demo bucket with one object per namespace prefix (used by the ABAC bonus).
if ! aws s3api head-bucket --bucket "$DEMO_BUCKET" 2>/dev/null; then
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$DEMO_BUCKET" --region "$AWS_REGION"
  else
    aws s3api create-bucket --bucket "$DEMO_BUCKET" --region "$AWS_REGION" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION"
  fi
fi
for p in demo-node demo-irsa demo-podid; do
  echo "hello from ${p}" | aws s3 cp - "s3://${DEMO_BUCKET}/${p}/hello.txt"
done

# Legacy anti-pattern: application permission on the node instance role.
aws iam put-role-policy --role-name "$NODE_ROLE" --policy-name "$LEGACY_POLICY_NAME" \
  --policy-document "$(render policies/s3-read.json.tpl)"

for ns in demo-node demo-irsa demo-podid; do
  render manifests/workload.yaml.tpl | sed "s/NAMESPACE/${ns}/g" | kubectl apply -f -
done
render manifests/neighbor.yaml.tpl | kubectl apply -f -

kubectl -n demo-node rollout status deploy/whoami --timeout=180s
echo
echo "Expected: every pod - including default/neighbor - is the NODE role:"
echo "  arn:aws:sts::${ACCOUNT_ID}:assumed-role/${NODE_ROLE}/i-xxxxxxxx"
echo "Run ./04-verify.sh"
