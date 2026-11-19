#!/usr/bin/env bash
# Common settings for every step. Edit, then `source 00-env.sh`.
set -euo pipefail

export CLUSTER_NAME="${CLUSTER_NAME:-pod-iam-demo}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
export NODEGROUP_NAME="${NODEGROUP_NAME:-ng-default}"
export ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
export DEMO_BUCKET="${DEMO_BUCKET:-pod-iam-demo-${ACCOUNT_ID}-${AWS_REGION}}"

# One IAM role per mechanism so CloudTrail shows who used what.
export IRSA_ROLE_NAME="${IRSA_ROLE_NAME:-pod-iam-demo-irsa-s3-reader}"
export PODID_ROLE_NAME="${PODID_ROLE_NAME:-pod-iam-demo-podid-s3-reader}"
export LEGACY_POLICY_NAME="legacy-node-s3-read"   # inline policy added to the node role

node_role_name() {
  aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
    --region "$AWS_REGION" --query 'nodegroup.nodeRole' --output text | awk -F/ '{print $NF}'
}

render() { # render <template> : substitutes ${DEMO_BUCKET} and ${AWS_REGION} only
  sed -e "s|\${DEMO_BUCKET}|${DEMO_BUCKET}|g" -e "s|\${AWS_REGION}|${AWS_REGION}|g" "$1"
}
