#!/usr/bin/env bash
# Live demo: move an app's S3 permission off the EKS node instance profile
# onto IRSA and EKS Pod Identity, side by side, on an existing cluster.
#
# Everything this script creates carries the tags Lab=eks-workload-identity-demo
# and LabRun=<RUN_ID>; every mutation and deletion checks those tags first.
# It never creates a VPC, subnet, security group, cluster, add-on or OIDC
# provider, and never touches other node groups or Pod Identity associations.
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./demo.sh <command> RUN_ID

Setup / teardown (before and after the talk):
  up             Create node group, roles, bucket and the three app copies
  down           Delete everything tagged with RUN_ID
  status         Show what exists for RUN_ID

Live steps (seconds each):
  watch          Live table: credential source, role and S3 result per copy
  migrate-irsa   Annotate the ServiceAccount and roll out (IRSA)
  migrate-podid  Create a Pod Identity association and roll out
  diff           Compare what IRSA and Pod Identity inject and trust
  revoke         Remove the S3 policy from the node role, wait for propagation
  harden         (optional, ~15 min) IMDS hop limit 1 on the demo node group
  restore        Return to the starting state (another ~15 min if harden ran)

RUN_ID: 4–12 lowercase letters or digits.
Environment: AWS_REGION (ap-northeast-2), CLUSTER (fsi-demo-cluster),
VPC_NAME (fsi-demo-vpc), SUBNET_NAMES (comma-separated private subnet Name tags).
USAGE
}

if [[ "$#" != 2 || ! "$2" =~ ^[a-z0-9]{4,12}$ ]]; then
  usage >&2
  exit 2
fi

action=$1
run_id=$2
export AWS_REGION=${AWS_REGION:-ap-northeast-2}
export AWS_PAGER=""
cluster=${CLUSTER:-fsi-demo-cluster}
vpc_name=${VPC_NAME:-fsi-demo-vpc}
subnet_names=${SUBNET_NAMES:-FsiDemoNetworkStack/FsiDemoVpc/PrivateSubnet1,FsiDemoNetworkStack/FsiDemoVpc/PrivateSubnet2}

owner=eks-workload-identity-demo
prefix="wid-${run_id}"
namespace="$prefix"
nodegroup="$prefix"
node_role="${prefix}-node"
irsa_role="${prefix}-irsa"
podid_role="${prefix}-podid"
launch_template="${prefix}-node"
policy_name=OrdersReadInvoices
object=invoices/2026-11.txt
image=public.ecr.aws/aws-cli/aws-cli:2.35.11
tracks=(legacy irsa podid)

state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/eks-workload-identity-demo"
mkdir -p "$state_dir"
export KUBECONFIG="$state_dir/kubeconfig-${run_id}"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scratch=$(mktemp -d "${TMPDIR:-$HOME/.tmp}/wid-XXXXXX" 2>/dev/null || mktemp -d)
trap 'rm -rf "$scratch"' EXIT

if [[ -t 1 ]]; then
  B=$'\e[1m' DIM=$'\e[2m' G=$'\e[32m' R=$'\e[31m' Y=$'\e[33m' C=$'\e[36m' N=$'\e[0m'
else
  B="" DIM="" G="" R="" Y="" C="" N=""
fi

log() { printf '%s==>%s %s\n' "$C" "$N" "$*" >&2; }
die() { printf '%serror:%s %s\n' "$R" "$N" "$*" >&2; exit 1; }

# --- identity, masking -------------------------------------------------------

caller=$(aws sts get-caller-identity --output json)
account=$(jq -r .Account <<< "$caller")
partition=$(jq -r '.Arn | split(":")[1]' <<< "$caller")
bucket="${prefix}-${account}-${AWS_REGION}"

# Public repos and screens: hide the account ID and the OIDC issuer ID.
mask() { sed -E -e "s/${account}/<ACCOUNT_ID>/g" -e 's#(/id/)[0-9A-F]{32}#\1<OIDC_ID>#g'; }

# Print a command the audience should see, then run it.
show() {
  printf '%s$%s %s\n' "$Y" "$N" "$(printf '%q ' "$@" | mask)" >&2
  "$@"
}

has_run_tags() { # JSON with .Tags (list) or .tags (map) on stdin
  jq -e --arg o "$owner" --arg r "$run_id" '
    ((.tags // {}) | (.Lab == $o and .LabRun == $r))
    or ([(.Tags // .TagSet // [])[] | {(.Key): .Value}] | add // {} | (.Lab == $o and .LabRun == $r))
  ' >/dev/null
}

aws_tags=("Key=Lab,Value=$owner" "Key=LabRun,Value=$run_id")

# --- cluster checks ----------------------------------------------------------

cluster_info=""
load_cluster() {
  cluster_info=$(aws eks describe-cluster --name "$cluster" --query cluster --output json)
  [[ "$(jq -r .status <<< "$cluster_info")" == ACTIVE ]] || die "cluster $cluster is not ACTIVE"
  aws eks update-kubeconfig --name "$cluster" --kubeconfig "$KUBECONFIG" >/dev/null
}

oidc_issuer() { jq -r '.identity.oidc.issuer | sub("^https://"; "")' <<< "$cluster_info"; }

preflight() {
  load_cluster
  local vpc_id expected
  vpc_id=$(jq -r .resourcesVpcConfig.vpcId <<< "$cluster_info")
  expected=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$vpc_name" --query 'Vpcs[0].VpcId' --output text)
  [[ "$expected" != None && "$vpc_id" == "$expected" ]] || die "cluster VPC is not $vpc_name"

  subnets=()
  local name id
  IFS=, read -r -a names <<< "$subnet_names"
  for name in "${names[@]}"; do
    id=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" "Name=tag:Name,Values=$name" \
      --query 'Subnets[?MapPublicIpOnLaunch==`false`].SubnetId | [0]' --output text)
    [[ "$id" != None && -n "$id" ]] || die "private subnet '$name' not found in $vpc_name"
    subnets+=("$id")
  done

  aws eks describe-addon --cluster-name "$cluster" --addon-name eks-pod-identity-agent >/dev/null \
    || die "eks-pod-identity-agent add-on is required (this script does not install it)"
  aws iam get-open-id-connect-provider --open-id-connect-provider-arn \
    "arn:${partition}:iam::${account}:oidc-provider/$(oidc_issuer)" >/dev/null \
    || die "IAM OIDC provider for the cluster is required (this script does not create it)"
}

# --- IAM ----------------------------------------------------------------------

role_exists() { aws iam get-role --role-name "$1" >/dev/null 2>&1; }

require_owned_role() {
  aws iam get-role --role-name "$1" --query Role --output json | has_run_tags \
    || die "role $1 is not tagged for run $run_id; refusing to modify it"
}

read_policy() {
  jq -n --arg arn "arn:${partition}:s3:::${bucket}/${object}" \
    '{Version:"2012-10-17",Statement:[{Effect:"Allow",Action:"s3:GetObject",Resource:$arn}]}'
}

put_read_policy() {
  require_owned_role "$1"
  read_policy > "$scratch/read.json"
  aws iam put-role-policy --role-name "$1" --policy-name "$policy_name" \
    --policy-document "file://$scratch/read.json"
}

delete_read_policy() {
  require_owned_role "$1"
  if aws iam list-role-policies --role-name "$1" --query PolicyNames --output json |
      jq -e --arg p "$policy_name" 'index($p) != null' >/dev/null; then
    aws iam delete-role-policy --role-name "$1" --policy-name "$policy_name"
  fi
}

create_role() { # name trust-file
  aws iam create-role --role-name "$1" --assume-role-policy-document "file://$2" \
    --tags "${aws_tags[@]}" --max-session-duration 3600 >/dev/null
}

setup_node_role() {
  role_exists "$node_role" && { log "node role exists"; return; }
  jq -n '{Version:"2012-10-17",Statement:[{Effect:"Allow",Principal:{Service:"ec2.amazonaws.com"},Action:"sts:AssumeRole"}]}' \
    > "$scratch/ec2.json"
  create_role "$node_role" "$scratch/ec2.json"
  local p
  # vpc-cni on this cluster runs on the node role, so the demo node needs the CNI policy too.
  for p in AmazonEKSWorkerNodePolicy AmazonEC2ContainerRegistryPullOnly AmazonEKS_CNI_Policy; do
    aws iam attach-role-policy --role-name "$node_role" --policy-arn "arn:${partition}:iam::aws:policy/$p"
  done
  put_read_policy "$node_role"   # the "legacy" state: app permission on the instance profile
}

setup_workload_roles() {
  local issuer provider
  issuer=$(oidc_issuer)
  provider="arn:${partition}:iam::${account}:oidc-provider/${issuer}"
  if ! role_exists "$irsa_role"; then
    jq -n --arg i "$issuer" --arg p "$provider" --arg s "system:serviceaccount:${namespace}:orders-irsa" \
      '{Version:"2012-10-17",Statement:[{Effect:"Allow",Principal:{Federated:$p},
        Action:"sts:AssumeRoleWithWebIdentity",
        Condition:{StringEquals:{($i+":aud"):"sts.amazonaws.com",($i+":sub"):$s}}}]}' > "$scratch/irsa.json"
    create_role "$irsa_role" "$scratch/irsa.json"
  fi
  put_read_policy "$irsa_role"
  if ! role_exists "$podid_role"; then
    jq -n --arg c "$(jq -r .arn <<< "$cluster_info")" --arg n "$namespace" \
      '{Version:"2012-10-17",Statement:[{Effect:"Allow",Principal:{Service:"pods.eks.amazonaws.com"},
        Action:["sts:AssumeRole","sts:TagSession"],
        Condition:{StringEquals:{"aws:RequestTag/eks-cluster-arn":$c,
          "aws:RequestTag/kubernetes-namespace":$n,
          "aws:RequestTag/kubernetes-service-account":"orders-podid"}}}]}' > "$scratch/podid.json"
    create_role "$podid_role" "$scratch/podid.json"
  fi
  put_read_policy "$podid_role"
}

delete_role() {
  local role=$1 p
  role_exists "$role" || return 0
  require_owned_role "$role"
  for p in $(aws iam list-role-policies --role-name "$role" --query 'PolicyNames[]' --output text); do
    aws iam delete-role-policy --role-name "$role" --policy-name "$p"
  done
  for p in $(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[].PolicyArn' --output text); do
    aws iam detach-role-policy --role-name "$role" --policy-arn "$p"
  done
  for p in $(aws iam list-instance-profiles-for-role --role-name "$role" --query 'InstanceProfiles[].InstanceProfileName' --output text); do
    aws iam remove-role-from-instance-profile --instance-profile-name "$p" --role-name "$role"
  done
  aws iam delete-role --role-name "$role"
  log "deleted role $role"
}

# --- S3 -----------------------------------------------------------------------

setup_bucket() {
  if aws s3api head-bucket --bucket "$bucket" --expected-bucket-owner "$account" 2>/dev/null; then
    log "bucket exists"; return
  fi
  local args=(--bucket "$bucket" --object-ownership BucketOwnerEnforced)
  [[ "$AWS_REGION" == us-east-1 ]] || args+=(--create-bucket-configuration "LocationConstraint=$AWS_REGION")
  aws s3api create-bucket "${args[@]}" >/dev/null
  aws s3api put-public-access-block --bucket "$bucket" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-tagging --bucket "$bucket" --expected-bucket-owner "$account" \
    --tagging "TagSet=[{Key=Lab,Value=$owner},{Key=LabRun,Value=$run_id}]"
  printf 'invoice batch 2026-11\n' > "$scratch/object.txt"
  aws s3api put-object --bucket "$bucket" --key "$object" --body "$scratch/object.txt" >/dev/null
}

delete_bucket() {
  aws s3api head-bucket --bucket "$bucket" --expected-bucket-owner "$account" 2>/dev/null || return 0
  aws s3api get-bucket-tagging --bucket "$bucket" --expected-bucket-owner "$account" | has_run_tags \
    || die "bucket is not tagged for run $run_id"
  aws s3 rm "s3://$bucket" --recursive >/dev/null
  aws s3api delete-bucket --bucket "$bucket" --expected-bucket-owner "$account"
  log "deleted bucket"
}

# --- node group -----------------------------------------------------------------

lt_data() { # hop-limit
  jq -n --argjson hop "$1" --arg o "$owner" --arg r "$run_id" --arg n "$prefix" '{
    MetadataOptions:{HttpTokens:"required",HttpPutResponseHopLimit:$hop,HttpEndpoint:"enabled"},
    BlockDeviceMappings:[{DeviceName:"/dev/xvda",Ebs:{VolumeSize:20,VolumeType:"gp3",Encrypted:true}}],
    TagSpecifications:[
      {ResourceType:"instance",Tags:[{Key:"Name",Value:$n},{Key:"Lab",Value:$o},{Key:"LabRun",Value:$r}]},
      {ResourceType:"volume",Tags:[{Key:"Lab",Value:$o},{Key:"LabRun",Value:$r}]}]}'
}

lt_id() {
  aws ec2 describe-launch-templates --filters "Name=launch-template-name,Values=$launch_template" \
    "Name=tag:LabRun,Values=$run_id" --query 'LaunchTemplates[0].LaunchTemplateId' --output text
}

nodegroup_json() {
  aws eks describe-nodegroup --cluster-name "$cluster" --nodegroup-name "$nodegroup" --query nodegroup --output json 2>/dev/null
}

setup_nodegroup() {
  if nodegroup_json >/dev/null; then log "node group exists"; return; fi
  if [[ "$(lt_id)" == None ]]; then
    # Hop limit 2 matches the cluster's existing node group: ordinary Pods can reach
    # IMDSv2 and therefore the node role. `harden` lowers it to 1.
    aws ec2 create-launch-template --launch-template-name "$launch_template" \
      --launch-template-data "$(lt_data 2)" \
      --tag-specifications "ResourceType=launch-template,Tags=[{Key=Lab,Value=$owner},{Key=LabRun,Value=$run_id}]" >/dev/null
  fi
  log "creating node group $nodegroup (3–5 min)"
  aws eks create-nodegroup --cluster-name "$cluster" --nodegroup-name "$nodegroup" \
    --node-role "arn:${partition}:iam::${account}:role/${node_role}" \
    --subnets "${subnets[@]}" --launch-template "name=$launch_template,version=1" \
    --ami-type AL2023_x86_64_STANDARD --instance-types t3.medium --capacity-type ON_DEMAND \
    --scaling-config minSize=1,maxSize=1,desiredSize=1 \
    --labels "wid-demo=$run_id" --taints "key=wid-demo,value=$run_id,effect=NO_SCHEDULE" \
    --tags "Lab=$owner,LabRun=$run_id" >/dev/null
  aws eks wait nodegroup-active --cluster-name "$cluster" --nodegroup-name "$nodegroup"
}

require_owned_nodegroup() {
  nodegroup_json | has_run_tags || die "node group $nodegroup is not tagged for run $run_id"
}

update_hop_limit() { # 1|2
  require_owned_nodegroup
  local id current cur_hop version update
  id=$(lt_id)
  [[ "$id" != None ]] || die "launch template not found"
  current=$(nodegroup_json | jq -r .launchTemplate.version)
  cur_hop=$(aws ec2 describe-launch-template-versions --launch-template-id "$id" --versions "$current" \
    --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions.HttpPutResponseHopLimit' --output text)
  if [[ "$cur_hop" == "$1" ]]; then log "hop limit already $1"; return; fi
  version=$(aws ec2 create-launch-template-version --launch-template-id "$id" \
    --launch-template-data "$(lt_data "$1")" --query LaunchTemplateVersion.VersionNumber --output text)
  update=$(show aws eks update-nodegroup-version --cluster-name "$cluster" --nodegroup-name "$nodegroup" \
    --launch-template "id=$id,version=$version" --query update.id --output text)
  log "rolling the node group to hop limit $1 (about 15 min: new node, drain, terminate)"
  local s
  while :; do
    s=$(aws eks describe-update --name "$cluster" --nodegroup-name "$nodegroup" --update-id "$update" \
      --query update.status --output text)
    [[ "$s" == InProgress ]] || break
    printf '.' >&2; sleep 15
  done
  printf '\n' >&2
  [[ "$s" == Successful ]] || die "node group update $s"
}

# --- Kubernetes -----------------------------------------------------------------

k() { kubectl -n "$namespace" "$@"; }

manifests() {
  local t script
  script=$(cat "$script_dir/app.sh")
  jq -n --arg ns "$namespace" --arg run "$run_id" '{apiVersion:"v1",kind:"Namespace",
    metadata:{name:$ns,labels:{"wid-demo":$run,"pod-security.kubernetes.io/enforce":"restricted"}}}'
  for t in "${tracks[@]}"; do
    jq -n --arg ns "$namespace" --arg t "$t" '{apiVersion:"v1",kind:"ServiceAccount",
      metadata:{name:("orders-"+$t),namespace:$ns}}'
    jq -n --arg ns "$namespace" --arg t "$t" --arg run "$run_id" --arg image "$image" \
      --arg bucket "$bucket" --arg key "$object" --arg region "$AWS_REGION" --arg script "$script" '
      {apiVersion:"apps/v1",kind:"Deployment",metadata:{name:("orders-"+$t),namespace:$ns},
       spec:{replicas:1,selector:{matchLabels:{app:"orders",track:$t}},
        strategy:{type:"RollingUpdate",rollingUpdate:{maxUnavailable:0,maxSurge:1}},
        template:{metadata:{labels:{app:"orders",track:$t}},spec:{
          serviceAccountName:("orders-"+$t),
          nodeSelector:{"wid-demo":$run},
          tolerations:[{key:"wid-demo",operator:"Equal",value:$run,effect:"NoSchedule"}],
          terminationGracePeriodSeconds:2,
          securityContext:{runAsNonRoot:true,runAsUser:1000,runAsGroup:1000,fsGroup:1000,seccompProfile:{type:"RuntimeDefault"}},
          containers:[{name:"orders",image:$image,command:["/bin/sh","-c",$script],
            env:[{name:"BUCKET",value:$bucket},{name:"KEY",value:$key},{name:"AWS_REGION",value:$region},
                 {name:"HOME",value:"/tmp"},{name:"AWS_MAX_ATTEMPTS",value:"1"},
                 {name:"AWS_METADATA_SERVICE_TIMEOUT",value:"2"},{name:"AWS_METADATA_SERVICE_NUM_ATTEMPTS",value:"1"}],
            resources:{requests:{cpu:"20m",memory:"64Mi"},limits:{memory:"192Mi"}},
            securityContext:{allowPrivilegeEscalation:false,readOnlyRootFilesystem:true,capabilities:{drop:["ALL"]}},
            volumeMounts:[{name:"tmp",mountPath:"/tmp"}]}],
          volumes:[{name:"tmp",emptyDir:{}}]}}}}'
  done
}

newest_pod() { # track
  k get pods -l "app=orders,track=$1" --sort-by=.metadata.creationTimestamp \
    -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.phase}{"\n"}{end}' 2>/dev/null |
    awk '$2=="Running"{p=$1} END{print p}'
}

rollout() { # track
  show kubectl -n "$namespace" rollout restart "deployment/orders-$1" >/dev/null
  show kubectl -n "$namespace" rollout status "deployment/orders-$1" --timeout=180s >&2
}

association_ids() {
  aws eks list-pod-identity-associations --cluster-name "$cluster" --namespace "$namespace" \
    --service-account orders-podid --query 'associations[].associationId' --output text | sed 's/^None$//'
}

# --- commands -------------------------------------------------------------------

cmd_up() {
  preflight
  log "bucket and test object";             setup_bucket
  log "node role (with the app's S3 permission, the legacy pattern)"; setup_node_role
  log "IRSA and Pod Identity roles";         setup_workload_roles
  setup_nodegroup
  log "namespace, ServiceAccounts and three copies of the orders app"
  manifests | kubectl apply -f - >/dev/null
  local t
  for t in "${tracks[@]}"; do k rollout status "deployment/orders-$t" --timeout=300s >&2; done
  log "ready. In a second terminal run: ./demo.sh watch $run_id"
}

cmd_watch() {
  load_cluster >/dev/null
  local t pod line src role s3 at label colour
  while :; do
    {
      printf '%s%s EKS workload identity — %s/%s  %s%s\n\n' "$B" "$(date +%H:%M:%S)" "$cluster" "$namespace" "(Ctrl-C to stop)" "$N"
      printf '%s%-15s %-14s %-30s %-9s %s%s\n' "$B" COPY CREDENTIALS ROLE S3 AT "$N"
      for t in "${tracks[@]}"; do
        pod=$(newest_pod "$t")
        line=$( [[ -n "$pod" ]] && k logs "$pod" --tail=1 2>/dev/null || true)
        jq -e . <<< "$line" >/dev/null 2>&1 || line='{}'
        IFS=$'\t' read -r src role s3 at < <(jq -r '[.src // "starting", .role // "-", .s3 // "-", .t // "-"] | @tsv' <<< "$line")
        case "$src" in
          imds) label="node (IMDS)";; irsa) label="IRSA (STS)";; pod-identity) label="Pod Identity";; *) label=$src;;
        esac
        [[ "$role" == "$node_role" ]] && role="$role  ← node"
        case "$s3" in allowed) colour=$G;; denied) colour=$R;; *) colour=$Y;; esac
        printf '%-15s %-14s %-30s %s%-9s%s %s\n' "orders-$t" "$label" "$role" "$colour" "$s3" "$N" "$at"
      done
      printf '\n%snode role: %s   bucket object: %s%s\n' "$DIM" "$node_role" "$object" "$N"
    } > "$scratch/frame"
    clear 2>/dev/null || printf '\033[H\033[2J'
    cat "$scratch/frame"
    sleep 2
  done
}

cmd_migrate_irsa() {
  load_cluster
  log "IRSA: point the ServiceAccount at its own role, then restart the copy"
  show kubectl -n "$namespace" annotate serviceaccount orders-irsa --overwrite \
    "eks.amazonaws.com/role-arn=arn:${partition}:iam::${account}:role/${irsa_role}" >/dev/null
  rollout irsa
}

cmd_migrate_podid() {
  load_cluster
  log "Pod Identity: associate the ServiceAccount with its role in the EKS API, then restart"
  if [[ -z "$(association_ids)" ]]; then
    show aws eks create-pod-identity-association --cluster-name "$cluster" --namespace "$namespace" \
      --service-account orders-podid --role-arn "arn:${partition}:iam::${account}:role/${podid_role}" \
      --tags "Lab=$owner,LabRun=$run_id" --query association.associationId --output text >/dev/null
  fi
  wait_for_injection
  rollout podid
}

# Associations are eventually consistent. A server-side dry run goes through the
# same mutating admission as a real Pod, so poll it until EKS injects the
# container-credentials variables, then restart the copy.
wait_for_injection() {
  log "waiting for the association to reach Pod admission (eventually consistent)"
  local start=$SECONDS
  while (( SECONDS - start < 120 )); do
    if k get deployment orders-podid -o json |
        jq --arg n "probe-${run_id}" '{apiVersion:"v1",kind:"Pod",metadata:{name:$n},spec:.spec.template.spec}' |
        k create --dry-run=server -o json -f - 2>/dev/null |
        jq -e '.spec.containers[0].env // [] | any(.name == "AWS_CONTAINER_CREDENTIALS_FULL_URI")' >/dev/null; then
      printf '  injected after %ss\n' "$((SECONDS - start))" >&2
      return
    fi
    printf '\r  %3ss  not yet ' "$((SECONDS - start))" >&2
    sleep 2
  done
  die "association not visible to admission within 120s"
}

jwt_claims() { # pod path
  k exec "$1" -- cat "$2" | cut -d. -f2 | tr '_-' '/+' | awk '{n=length($0)%4; if(n) $0=$0 substr("===",1,4-n); print}' |
    base64 -d 2>/dev/null | jq -c '{iss, aud, sub, lifetime_s: (.exp - .iat)}' | mask
}

cmd_diff() {
  load_cluster
  local pi pp
  pi=$(newest_pod irsa); pp=$(newest_pod podid)
  [[ -n "$pi" && -n "$pp" ]] || die "app pods are not running"
  printf '\n%s1. What EKS injected into each new Pod (env var names)%s\n' "$B" "$N"
  for p in "irsa:$pi" "podid:$pp"; do
    printf '  %-6s %s\n' "${p%%:*}" "$(k get pod "${p#*:}" -o json |
      jq -r '[.spec.containers[0].env[]?.name | select(startswith("AWS_") and . != "AWS_REGION" and . != "AWS_MAX_ATTEMPTS" and (startswith("AWS_METADATA") | not))] | join(", ") | if . == "" then "(none: falls back to IMDS)" else . end')"
  done
  printf '\n%s2. The projected ServiceAccount token (claims only)%s\n' "$B" "$N"
  printf '  irsa   %s\n' "$(jwt_claims "$pi" /var/run/secrets/eks.amazonaws.com/serviceaccount/token 2>/dev/null || echo '(no IRSA token yet: run migrate-irsa)')"
  printf '  podid  %s\n' "$(jwt_claims "$pp" /var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token 2>/dev/null || echo '(no Pod Identity token yet: run migrate-podid)')"
  printf '\n%s3. Who each role trusts%s\n' "$B" "$N"
  for r in "$irsa_role" "$podid_role"; do
    printf '  %-16s %s\n' "${r#"$prefix"-}" "$(aws iam get-role --role-name "$r" --query Role.AssumeRolePolicyDocument --output json |
      jq -c '.Statement[0] | {principal: .Principal, action: .Action, conditions: (.Condition.StringEquals | keys | map(sub("^.*/id/[^:]+"; "<issuer>")))}' | mask)"
  done
  printf '\n%s4. Where the SDK goes for credentials%s\n' "$B" "$N"
  printf '  irsa   Pod → STS AssumeRoleWithWebIdentity (regional endpoint) → temporary credentials\n'
  printf '  podid  Pod → Pod Identity Agent 169.254.170.23 on the node → EKS Auth AssumeRoleForPodIdentity → credentials\n'
  printf '  legacy Pod → IMDSv2 169.254.169.254 → node role credentials\n'
  printf '\n%s5. Wiring lives in%s\n' "$B" "$N"
  printf '  irsa   ServiceAccount annotation + IAM OIDC provider + per-role trust on issuer/sub\n'
  printf '  podid  EKS association (%s) + one service principal trust, reusable across clusters\n\n' "$(association_ids | wc -w | tr -d ' ') found"
}

cmd_revoke() {
  load_cluster
  log "remove the app's S3 permission from the node role"
  require_owned_role "$node_role"
  show aws iam delete-role-policy --role-name "$node_role" --policy-name "$policy_name" \
    || log "(policy already removed)"
  log "waiting for IAM to propagate: legacy copy should flip to denied"
  local start=$SECONDS pod line
  while (( SECONDS - start < 180 )); do
    pod=$(newest_pod legacy)
    line=$(k logs "$pod" --tail=1 2>/dev/null || true)
    jq -e . <<< "$line" >/dev/null 2>&1 || line='{}'
    if [[ "$(jq -r '.s3 // ""' <<< "$line")" == denied ]]; then
      printf '%s  legacy denied after %ss — IRSA and Pod Identity copies keep reading%s\n' "$G" "$((SECONDS - start))" "$N" >&2
      return
    fi
    printf '\r  %3ss  legacy still: %s ' "$((SECONDS - start))" "$(jq -r '.s3 // "-"' <<< "$line")" >&2
    sleep 3
  done
  printf '\n' >&2
  die "legacy copy did not flip within 180s"
}

cmd_harden() {
  load_cluster
  log "block Pod access to IMDS on the demo node group (hop limit 1)"
  update_hop_limit 1
  k rollout status deployment/orders-legacy --timeout=300s >&2 || true
  log "legacy copy now has no credentials at all; IRSA and Pod Identity are unaffected"
}

cmd_restore() {
  load_cluster
  log "restore the starting state"
  put_read_policy "$node_role"
  k annotate serviceaccount orders-irsa eks.amazonaws.com/role-arn- >/dev/null 2>&1 || true
  local id
  for id in $(association_ids); do
    aws eks delete-pod-identity-association --cluster-name "$cluster" --association-id "$id" >/dev/null
  done
  local hop
  hop=$(aws ec2 describe-launch-template-versions --launch-template-id "$(lt_id)" \
    --versions "$(nodegroup_json | jq -r .launchTemplate.version)" \
    --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions.HttpPutResponseHopLimit' --output text)
  [[ "$hop" == 2 ]] || update_hop_limit 2
  local t
  for t in "${tracks[@]}"; do k rollout restart "deployment/orders-$t" >/dev/null; done
  for t in "${tracks[@]}"; do k rollout status "deployment/orders-$t" --timeout=300s >&2; done
  log "restored: all three copies use the node role again (IAM may take a few seconds)"
}

cmd_status() {
  load_cluster
  printf 'cluster    %s (%s)\n' "$cluster" "$(jq -r .version <<< "$cluster_info")"
  printf 'nodegroup  %s\n' "$(nodegroup_json | jq -r '"\(.status) \(.instanceTypes|join(",")) lt-version=\(.launchTemplate.version)"' 2>/dev/null || echo absent)"
  local r
  for r in "$node_role" "$irsa_role" "$podid_role"; do
    printf 'role       %-20s %s\n' "$r" "$(role_exists "$r" && aws iam list-role-policies --role-name "$r" --query 'PolicyNames' --output text | sed 's/^$/(no inline policy)/' || echo absent)"
  done
  printf 'bucket     %s\n' "$(aws s3api head-bucket --bucket "$bucket" --expected-bucket-owner "$account" >/dev/null 2>&1 && echo present || echo absent)"
  printf 'pod-id     %s association(s)\n' "$(association_ids | wc -w | tr -d ' ')"
  local ann
  ann=$(k get sa orders-irsa -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}' 2>/dev/null | mask || true)
  printf 'irsa SA    %s\n' "${ann:-(not annotated)}"
  k get pods -o wide 2>/dev/null || true
}

cmd_down() {
  load_cluster
  local id
  for id in $(association_ids 2>/dev/null); do
    aws eks delete-pod-identity-association --cluster-name "$cluster" --association-id "$id" >/dev/null
  done
  if kubectl get namespace "$namespace" -o json 2>/dev/null | jq -e --arg r "$run_id" '.metadata.labels["wid-demo"] == $r' >/dev/null; then
    kubectl delete namespace "$namespace" --wait=true >/dev/null
    log "deleted namespace"
  fi
  if nodegroup_json >/dev/null; then
    require_owned_nodegroup
    log "deleting node group (3–5 min)"
    aws eks delete-nodegroup --cluster-name "$cluster" --nodegroup-name "$nodegroup" >/dev/null
    aws eks wait nodegroup-deleted --cluster-name "$cluster" --nodegroup-name "$nodegroup"
  fi
  id=$(lt_id)
  [[ "$id" == None ]] || { aws ec2 delete-launch-template --launch-template-id "$id" >/dev/null; log "deleted launch template"; }
  local node_arn="arn:${partition}:iam::${account}:role/${node_role}"
  if aws eks describe-access-entry --cluster-name "$cluster" --principal-arn "$node_arn" >/dev/null 2>&1; then
    aws eks delete-access-entry --cluster-name "$cluster" --principal-arn "$node_arn"
  fi
  delete_role "$node_role"
  delete_role "$irsa_role"
  delete_role "$podid_role"
  delete_bucket
  rm -f "$KUBECONFIG"
  log "done"
}

case "$action" in
  up) cmd_up ;;
  down) cmd_down ;;
  status) cmd_status ;;
  watch) cmd_watch ;;
  migrate-irsa) cmd_migrate_irsa ;;
  migrate-podid) cmd_migrate_podid ;;
  diff) cmd_diff ;;
  revoke) cmd_revoke ;;
  harden) cmd_harden ;;
  restore) cmd_restore ;;
  *) usage >&2; exit 2 ;;
esac
