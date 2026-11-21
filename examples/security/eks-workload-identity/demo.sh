#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./demo.sh config|create|compare|delete RUN_ID
RUN_ID: 6–16 lowercase ASCII letters or digits, unique per lab.
Set AWS_REGION (default ap-northeast-2) and optionally API_CIDR (an IPv4 /32).
Run compare from the same egress IP as create. Run delete after the lab.
USAGE
}

if [[ "$#" != 2 || ! "$2" =~ ^[a-z0-9]{6,16}$ ]]; then
  usage >&2
  exit 2
fi

action=$1
run_id=$2
export AWS_REGION=${AWS_REGION:-ap-northeast-2}
export AWS_PAGER=""
export AWS_MAX_ATTEMPTS=${AWS_MAX_ATTEMPTS:-6}
cluster="wid-${run_id}"
namespace=identity-demo
nodegroup=workers
owner=eks-workload-identity-demo
object=probe.txt
policy_name=IdentityDemoReadProbe
image=public.ecr.aws/aws-cli/aws-cli:2.35.11

cluster_config() {
  local cidr=${API_CIDR:-}
  if [[ -z "$cidr" ]]; then
    cidr="$(curl -fsS --max-time 10 https://checkip.amazonaws.com)/32"
  fi
  python3 -c 'import ipaddress, sys; sys.exit(ipaddress.IPv4Network(sys.argv[1]).prefixlen != 32)' "$cidr"
  cat <<YAML
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${cluster}
  region: ${AWS_REGION}
  version: "1.35"
  tags:
    Lab: ${owner}
    LabRun: "${run_id}"
vpc:
  nat:
    gateway: Single
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs: ["${cidr}"]
iam:
  withOIDC: true
managedNodeGroups:
  - name: ${nodegroup}
    instanceType: t3.medium
    amiFamily: AmazonLinux2023
    desiredCapacity: 1
    minSize: 1
    maxSize: 1
    privateNetworking: true
    disableIMDSv1: true
    disablePodIMDS: true
    volumeEncrypted: true
    volumeSize: 20
addons:
  - name: eks-pod-identity-agent
YAML
}

if [[ "$action" == config ]]; then
  cluster_config
  exit
fi

case "$action" in
  create|compare|delete) ;;
  *) usage >&2; exit 2 ;;
esac

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
export KUBECONFIG="$scratch/kubeconfig"

if [[ "$action" == create ]]; then
  cluster_config > "$scratch/cluster.yaml"
  eksctl create cluster -f "$scratch/cluster.yaml" --write-kubeconfig=false
  exit
fi

caller=$(aws sts get-caller-identity --output json)
account=$(jq -r .Account <<< "$caller")
partition=$(jq -r '.Arn | split(":")[1]' <<< "$caller")
bucket="${cluster}-${account}-${AWS_REGION}"
irsa_role="${cluster}-irsa"
pod_role="${cluster}-pod"
stack="eksctl-${cluster}-cluster"

require_owned_cluster() {
  jq -e --arg owner "$owner" --arg run "$run_id" \
    '.tags.Lab == $owner and .tags.LabRun == $run' <<< "$cluster_info" >/dev/null
}

retry() {
  local attempt
  for ((attempt=1; attempt<=12; attempt++)); do
    if "$@"; then return 0; fi
    sleep 5
  done
  return 1
}

setup_bucket() {
  local args=(--bucket "$bucket" --object-ownership BucketOwnerEnforced)
  if aws s3api head-bucket --bucket "$bucket" 2>"$scratch/error"; then
    printf 'Bucket already exists. Use a fresh run ID.\n' >&2
    return 1
  elif ! rg -q '\(404\)' "$scratch/error"; then
    cat "$scratch/error" >&2
    return 1
  fi
  if [[ "$AWS_REGION" != us-east-1 ]]; then
    args+=(--create-bucket-configuration "LocationConstraint=$AWS_REGION")
  fi
  aws s3api create-bucket "${args[@]}" >/dev/null
  aws s3api put-bucket-tagging --bucket "$bucket" --expected-bucket-owner "$account" \
    --tagging "TagSet=[{Key=Lab,Value=$owner},{Key=LabRun,Value=$run_id}]"
  aws s3api put-public-access-block --bucket "$bucket" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption --bucket "$bucket" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  printf '%s\n' eks-workload-identity > "$scratch/probe.txt"
  aws s3api put-object --bucket "$bucket" --key "$object" --body "$scratch/probe.txt" >/dev/null
  jq -n --arg arn "arn:${partition}:s3:::${bucket}/${object}" \
    '{Version:"2012-10-17",Statement:[{Effect:"Allow",Action:"s3:GetObject",Resource:$arn}]}' \
    > "$scratch/permissions.json"
}

put_probe_policy() {
  aws iam put-role-policy --role-name "$1" --policy-name "$policy_name" \
    --policy-document "file://$scratch/permissions.json"
}

remove_probe_policy() {
  local role=$1 policies
  policies=$(aws iam list-role-policies --role-name "$role" --output json)
  if jq -e --arg name "$policy_name" '.PolicyNames | index($name) != null' <<< "$policies" >/dev/null; then
    aws iam delete-role-policy --role-name "$role" --policy-name "$policy_name"
  fi
}

create_role() {
  local role=$1 trust=$2
  aws iam create-role --role-name "$role" --assume-role-policy-document "file://$trust" \
    --tags "Key=Lab,Value=$owner" "Key=LabRun,Value=$run_id" --query Role.Arn --output text
}

setup_roles() {
  local issuer provider
  issuer=$(jq -r '.identity.oidc.issuer | sub("^https://"; "")' <<< "$cluster_info")
  provider="arn:${partition}:iam::${account}:oidc-provider/${issuer}"
  aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$provider" >/dev/null

  jq -n --arg issuer "$issuer" --arg provider "$provider" --arg subject "system:serviceaccount:${namespace}:irsa" \
    '{Version:"2012-10-17",Statement:[{Effect:"Allow",Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",($issuer+":sub"):$subject}}}]}' \
    > "$scratch/irsa.json"
  irsa_arn=$(create_role "$irsa_role" "$scratch/irsa.json")
  put_probe_policy "$irsa_role"

  jq -n --arg cluster_arn "$(jq -r .arn <<< "$cluster_info")" --arg namespace "$namespace" \
    '{Version:"2012-10-17",Statement:[{Effect:"Allow",Principal:{Service:"pods.eks.amazonaws.com"},
      Action:["sts:AssumeRole","sts:TagSession"],Condition:{StringEquals:{
        "aws:RequestTag/eks-cluster-arn":$cluster_arn,"aws:RequestTag/kubernetes-namespace":$namespace,
        "aws:RequestTag/kubernetes-service-account":"pod-identity"}}}]}' > "$scratch/pod.json"
  pod_arn=$(create_role "$pod_role" "$scratch/pod.json")
  put_probe_policy "$pod_role"
}

wait_for_injection() {
  local identity
  kubectl -n "$namespace" delete pod injection-check --ignore-not-found --wait=true >/dev/null || return 1
  kubectl -n "$namespace" run injection-check --image="$image" --restart=Never \
    --overrides='{"spec":{"serviceAccountName":"pod-identity"}}' --command -- /bin/sh -c 'exit 0' >/dev/null || return 1
  identity=$(kubectl -n "$namespace" get pod injection-check -o json) || return 1
  jq -e '.spec.containers[0].env // [] | any(.name == "AWS_CONTAINER_CREDENTIALS_FULL_URI")' \
    <<< "$identity" >/dev/null
}

probe() {
  local name=$1 sa=$2 expected_role=$3 expected_result=$4
  local pod host_network report role_label
  host_network=false
  role_label="$sa-role"
  if [[ "$sa" == legacy ]]; then
    host_network=true
    role_label=node-role
  fi

  # Host networking lets the baseline reach IMDSv2 with the same cluster/node.
  # Both workload identities run as regular Pods with SDK IMDS fallback disabled.
  jq -n --arg name "$name" --arg ns "$namespace" --arg sa "$sa" --arg image "$image" \
    --arg bucket "$bucket" --arg key "$object" --arg region "$AWS_REGION" --argjson host "$host_network" \
    --rawfile script "$script_dir/probe.sh" '
    {apiVersion:"batch/v1",kind:"Job",metadata:{name:$name,namespace:$ns},spec:{
      backoffLimit:0, activeDeadlineSeconds:240, template:{spec:{
        serviceAccountName:$sa, restartPolicy:"Never", hostNetwork:$host,
        dnsPolicy:(if $host then "ClusterFirstWithHostNet" else "ClusterFirst" end),
        containers:[{name:"probe",image:$image,command:["/bin/sh","-c",$script],args:["probe",$bucket,$key],
          env:[{name:"AWS_REGION",value:$region},{name:"AWS_MAX_ATTEMPTS",value:"2"},
            {name:"AWS_EC2_METADATA_DISABLED",value:($host|not|tostring)}],
          securityContext:{allowPrivilegeEscalation:false,capabilities:{drop:["ALL"]},
            seccompProfile:{type:"RuntimeDefault"}}}]
      }}}}' | kubectl create -f - >/dev/null || return 1
  local status="" attempt
  for ((attempt=1; attempt<=120; attempt++)); do
    status=$(kubectl -n "$namespace" get "job/$name" -o json |
      jq -r '.status.conditions[]? | select(.status=="True" and (.type=="Complete" or .type=="Failed")) | .type') \
      || return 1
    case "$status" in
      Complete|Failed) break ;;
    esac
    sleep 2
  done
  if [[ "$status" != Complete ]]; then
    kubectl -n "$namespace" logs "job/$name" >&2 || true
    kubectl -n "$namespace" get "job/$name" -o json |
      jq -r '.status.conditions[]? | "\(.type): \(.message)"' >&2 || true
    kubectl -n "$namespace" get pods -l "batch.kubernetes.io/job-name=$name" >&2 || true
    return 1
  fi
  pod=$(kubectl -n "$namespace" get pods -l "batch.kubernetes.io/job-name=$name" -o json) || return 1
  case "$sa" in
    irsa)
      jq -e '.items[0].spec.containers[0].env // [] | any(.name == "AWS_WEB_IDENTITY_TOKEN_FILE")' \
        <<< "$pod" >/dev/null || return 1 ;;
    pod-identity)
      jq -e '.items[0].spec.containers[0].env // [] | any(.name == "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE")' \
        <<< "$pod" >/dev/null || return 1 ;;
  esac
  report=$(kubectl -n "$namespace" logs "job/$name") || return 1
  if ! awk -v partition="$partition" -v account="$account" -v role="$expected_role" -v result="$expected_result" '
      index($0, "arn=arn:" partition ":sts::" account ":assumed-role/" role "/") == 1 {identity=1}
      $0 == "s3=" result {access=1}
      END {exit !(identity && access)}
    ' <<< "$report"; then
    printf '%s\n' "$report" >&2
    return 1
  fi
  printf '%s role=%s s3=%s\n' "$name" "$role_label" "$expected_result"
}

wait_for_access() {
  local name=$1 sa=$2 role=$3 expected=$4 attempt report
  for ((attempt=1; attempt<=8; attempt++)); do
    if report=$(probe "$name-$attempt" "$sa" "$role" "$expected" 2>"$scratch/probe.err"); then
      printf '%s\n' "$report"
      return 0
    fi
    cat "$scratch/probe.err" >&2
    # IAM permissions and trust changes can take time to propagate.
    case "$expected" in
      denied) rg -qx 's3=allowed' "$scratch/probe.err" || return 1 ;;
      allowed) rg -q '^(s3=denied)$|InvalidIdentityToken|AccessDenied|Unable to locate credentials' \
        "$scratch/probe.err" || return 1 ;;
    esac
    sleep 10
  done
  return 1
}

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

if [[ "$action" == compare ]]; then
  cluster_info=$(aws eks describe-cluster --name "$cluster" --query cluster --output json)
  require_owned_cluster
  node_role=$(aws eks describe-nodegroup --cluster-name "$cluster" --nodegroup-name "$nodegroup" \
    --query 'nodegroup.nodeRole' --output text)
  node_role=${node_role##*/}
  aws eks update-kubeconfig --name "$cluster" --kubeconfig "$KUBECONFIG" >/dev/null
  kubectl -n kube-system rollout status daemonset/eks-pod-identity-agent --timeout=180s
  kubectl create namespace "$namespace"
  for sa in legacy irsa pod-identity; do
    kubectl -n "$namespace" create serviceaccount "$sa"
  done
  setup_bucket
  put_probe_policy "$node_role"
  wait_for_access legacy-before legacy "$node_role" allowed
  setup_roles
  kubectl -n "$namespace" annotate sa irsa "eks.amazonaws.com/role-arn=$irsa_arn"
  association_token=$(python3 -c 'import uuid; print(uuid.uuid4())')
  retry aws eks create-pod-identity-association --cluster-name "$cluster" --namespace "$namespace" \
    --service-account pod-identity --role-arn "$pod_arn" --client-request-token "$association_token" \
    --query association.associationId --output text >/dev/null
  retry wait_for_injection
  kubectl -n "$namespace" delete pod injection-check --wait=true >/dev/null

  wait_for_access irsa-before irsa "$irsa_role" allowed
  wait_for_access pod-identity-before pod-identity "$pod_role" allowed
  aws iam delete-role-policy --role-name "$node_role" --policy-name "$policy_name"
  wait_for_access legacy-after legacy "$node_role" denied
  probe irsa-after irsa "$irsa_role" allowed
  probe pod-identity-after pod-identity "$pod_role" allowed
  exit
fi

# eksctl owns the node role, node group, network, add-on and OIDC provider.
# Delete the cluster before IAM role/bucket cleanup. A deleted cluster can be retried.
if cluster_info=$(aws eks describe-cluster --name "$cluster" --query cluster --output json 2>"$scratch/error"); then
  require_owned_cluster
  if node_role=$(aws eks describe-nodegroup --cluster-name "$cluster" --nodegroup-name "$nodegroup" \
    --query 'nodegroup.nodeRole' --output text 2>"$scratch/error"); then
    remove_probe_policy "${node_role##*/}"
  elif ! rg -q ResourceNotFoundException "$scratch/error"; then
    cat "$scratch/error" >&2
    exit 1
  fi
  eksctl delete cluster --name "$cluster" --region "$AWS_REGION" --wait
elif rg -q ResourceNotFoundException "$scratch/error"; then
  if metadata=$(aws cloudformation describe-stacks --stack-name "$stack" --query 'Stacks[0]' \
    --output json 2>"$scratch/error"); then
    jq -e --arg owner "$owner" --arg run "$run_id" \
      'any(.Tags[]?; .Key=="Lab" and .Value==$owner) and any(.Tags[]?; .Key=="LabRun" and .Value==$run)' \
      <<< "$metadata" >/dev/null
    eksctl delete cluster --name "$cluster" --region "$AWS_REGION" --wait
  elif ! rg -q 'does not exist' "$scratch/error"; then
    cat "$scratch/error" >&2
    exit 1
  fi
else
  cat "$scratch/error" >&2
  exit 1
fi

for role in "$irsa_role" "$pod_role"; do
  if metadata=$(aws iam get-role --role-name "$role" --query Role --output json 2>"$scratch/error"); then
    jq -e --arg owner "$owner" --arg run "$run_id" \
      'any(.Tags[]?; .Key=="Lab" and .Value==$owner) and any(.Tags[]?; .Key=="LabRun" and .Value==$run)' \
      <<< "$metadata" >/dev/null
    remove_probe_policy "$role"
    aws iam delete-role --role-name "$role"
  elif ! rg -q NoSuchEntity "$scratch/error"; then
    cat "$scratch/error" >&2
    exit 1
  fi
done

if aws s3api head-bucket --bucket "$bucket" --expected-bucket-owner "$account" 2>"$scratch/error"; then
  tags=$(aws s3api get-bucket-tagging --bucket "$bucket" --expected-bucket-owner "$account")
  jq -e --arg owner "$owner" --arg run "$run_id" \
    'any(.TagSet[]?; .Key=="Lab" and .Value==$owner) and any(.TagSet[]?; .Key=="LabRun" and .Value==$run)' \
    <<< "$tags" >/dev/null
  aws s3api delete-object --bucket "$bucket" --key "$object" --expected-bucket-owner "$account" >/dev/null
  aws s3api delete-bucket --bucket "$bucket" --expected-bucket-owner "$account"
elif ! rg -q '\(404\)' "$scratch/error"; then
  cat "$scratch/error" >&2
  exit 1
fi
