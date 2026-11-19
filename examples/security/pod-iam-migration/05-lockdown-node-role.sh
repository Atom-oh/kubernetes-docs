#!/usr/bin/env bash
# Step 5 - After every workload is migrated: strip app permissions from the node
# role and stop pods from reaching IMDS.
source "$(dirname "$0")/00-env.sh"
cd "$(dirname "$0")"
NODE_ROLE="$(node_role_name)"

# 5-1. Remove the legacy application permission from the node role.
aws iam delete-role-policy --role-name "$NODE_ROLE" --policy-name "$LEGACY_POLICY_NAME" || true
echo "Remaining managed policies on ${NODE_ROLE}:"
aws iam list-attached-role-policies --role-name "$NODE_ROLE" --query 'AttachedPolicies[].PolicyName' --output text | tr '\t' '\n'

# 5-2. IMDSv2 required + hop limit 1 on the running nodes.
#      DEMO SHORTCUT: this only changes current instances. For a persistent setting,
#      put MetadataOptions in the node group's launch template (or
#      eksctl `disableIMDSv1: true` + `disablePodIMDS: true`) and roll the node group.
IDS="$(aws ec2 describe-instances --region "$AWS_REGION" \
  --filters "Name=tag:eks:cluster-name,Values=${CLUSTER_NAME}" "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' --output text)"
for id in $IDS; do
  aws ec2 modify-instance-metadata-options --region "$AWS_REGION" --instance-id "$id" \
    --http-tokens required --http-put-response-hop-limit 1 --http-endpoint enabled >/dev/null
  echo "hop-limit=1 : $id"
done

# 5-3. (optional) Defence in depth for namespaces with NetworkPolicy enforcement.
# kubectl -n demo-node apply -f manifests/deny-imds-networkpolicy.yaml

echo
echo "IAM is eventually consistent - wait ~1 min, then ./04-verify.sh"
echo "Expected: demo-node and default/neighbor -> DENIED; demo-irsa and demo-podid -> ALLOWED"
