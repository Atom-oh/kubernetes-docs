# EKS Advanced Debugging and Incident Response

> **Supported Versions**: EKS 1.28+, kubectl 1.28+
> **Last Updated**: September 9, 2026

For stable operation of Amazon EKS clusters, a systematic incident response framework and advanced debugging skills are essential. This document provides a practical guide for quickly diagnosing and resolving complex issues that occur in production environments.

## Table of Contents

1. [Incident Response Framework](#1-incident-response-framework)
2. [Control Plane Debugging](#2-control-plane-debugging)
3. [Node-Level Troubleshooting](#3-node-level-troubleshooting)
4. [Workload Debugging](#4-workload-debugging)
5. [Networking Diagnostics](#5-networking-diagnostics)
6. [Storage Troubleshooting](#6-storage-troubleshooting)
7. [Observability Architecture](#7-observability-architecture)
8. [Failure Detection Architecture](#8-failure-detection-architecture)
9. [Quick Reference](#9-quick-reference)
10. [Next Steps](#10-next-steps)

---

## 1. Incident Response Framework

### First 5-Minute Checklist (Initial Triage)

Treat the original 30-second steps, two-minute scope check and five-minute total as planning targets, not measured completion times. First establish the customer impact and the exact account, cluster/context, namespace and recent change. An unavailable API client can reflect credentials, authorization, DNS/network or control-plane issues; it does not alone prove that all running applications are down.

Inspect node conditions, Pod/container state, controller rollout status, recent events and resource samples together. `phase!=Running` misses Running-but-NotReady/CrashLooping Pods and includes successfully completed Jobs. A Pod's Running phase does not prove readiness. For Deployments compare desired, updated, ready/available replicas and observed generation, rather than grepping display strings such as `1/1`.

The standard VPC CNI `aws-node` DaemonSet normally runs in `kube-system`; a namespace named `amazon-vpc-cni-system` is not an EKS prerequisite. Pure Auto Mode manages networking and node-system DNS differently, so absence of standard add-on Pods must be interpreted against the node/controller mode. Metrics Server data is a sampled resource view, not a customer-availability signal.

### Initial Diagnostic Script

This script performs bounded API requests and saves private evidence for one selected workload namespace plus cluster nodes/system Pod status. It does not collect Secret data or dump every Pod environment/configuration. Logs, events and error messages can still contain sensitive application data: inspect/redact evidence before sharing it. Review the account/context inputs and existing private evidence directory before running.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended account ID}"
: "${KUBE_CONTEXT:?Set the explicit kubectl context}"
: "${NAMESPACE:?Set the owned workload namespace}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
test -d "$EVIDENCE_PARENT"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
test "$ACTUAL_ACCOUNT_ID" = "$EXPECTED_ACCOUNT_ID" || { echo "Account mismatch" >&2; exit 1; }
CLUSTER_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.endpoint --output text)
KUBE_ENDPOINT=$(kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
test "$CLUSTER_ENDPOINT" = "$KUBE_ENDPOINT" || { echo "Context/cluster mismatch" >&2; exit 1; }

umask 077
TRIAGE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-triage.XXXXXXXX")
TRIAGE_FAILED=0
k() { kubectl --context "$KUBE_CONTEXT" --request-timeout=15s "$@"; }
collect() {
  local name=$1
  shift
  if "$@" > "$TRIAGE_DIR/$name.txt" 2> "$TRIAGE_DIR/$name.stderr"; then
    printf '%s\tok\n' "$name" >> "$TRIAGE_DIR/status.tsv"
  else
    local rc=$?
    TRIAGE_FAILED=$((TRIAGE_FAILED + 1))
    printf '%s\tfailed:%s\n' "$name" "$rc" >> "$TRIAGE_DIR/status.tsv"
  fi
}
node_health() {
  k get nodes -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
    unschedulable:.spec.unschedulable,taints:.spec.taints,conditions:.status.conditions
  }]'
}
pod_health() {
  k -n "$NAMESPACE" get pods -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,owners:.metadata.ownerReferences,
    deleting:.metadata.deletionTimestamp,phase:.status.phase,conditions:.status.conditions,
    containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
    initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
  }]'
}
deployment_health() {
  k -n "$NAMESPACE" get deployments -o json | jq '[.items[] | {
    name:.metadata.name,generation:.metadata.generation,observed:.status.observedGeneration,
    desired:(.spec.replicas // 1),updated:(.status.updatedReplicas // 0),
    ready:(.status.readyReplicas // 0),available:(.status.availableReplicas // 0),
    conditions:.status.conditions
  }]'
}
load_balancers() {
  k -n "$NAMESPACE" get services -o json | jq '[.items[] | select(.spec.type=="LoadBalancer") | {
    name:.metadata.name,class:.spec.loadBalancerClass,selector:.spec.selector,
    ports:.spec.ports,status:.status.loadBalancer
  }]'
}
collect nodes node_health
collect pods pod_health
collect deployments deployment_health
collect load-balancers load_balancers
collect events k -n "$NAMESPACE" get events --sort-by='.metadata.creationTimestamp'
collect system-pods k -n kube-system get pods -o wide
collect node-resources k top nodes
collect pod-resources k -n "$NAMESPACE" top pods --sort-by=memory
printf 'Private evidence: %s; failed collections: %s\n' "$TRIAGE_DIR" "$TRIAGE_FAILED"
test "$TRIAGE_FAILED" -eq 0
```

Inspect `status.tsv` and each failure output. Missing permissions, unavailable metrics and API timeouts remain failed collections; the script exits nonzero if any collection failed and does not claim the incident is resolved. It deliberately leaves completed, pending and Running Pod states visible for interpretation. Selective follow-up logs should use an exact namespace, Pod UID and container, with a bounded time/line range.

The LoadBalancer list filters the Service JSON locally: `spec.type` is not a supported built-in Service field selector. No broad `cluster-info dump`, automatic archive upload, resource restart or deletion is part of this initial collection.

### Severity Matrix

| Severity | Classification | Impact Scope | Response Time | Examples |
|----------|---------------|--------------|---------------|----------|
| **P1** | Critical | Complete service outage | Within 15 minutes | Control plane failure, all nodes NotReady |
| **P2** | High | Major functionality failure | Within 1 hour | Specific workload complete failure, network connectivity issues |
| **P3** | Medium | Partial impact | Within 4 hours | Some pod restarts, performance degradation |
| **P4** | Low | Minor issues | Within 24 hours | Log collection delay, non-critical monitoring alerts |

Response times in this severity table are example organizational targets. Classify actual customer impact; a control-plane-only outage can leave existing workload traffic running.

### Decision Tree for Rapid Problem Identification

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![Decision-tree workflow for the first minutes of EKS incident triage: after an incident is detected it asks whether the service is accessible, then walks kubectl connectivity, node readiness, and pod status toward control-plane, node, scheduling, or app/config causes, or response delay and intermittent errors toward workload, cluster-wide, or network/DNS causes.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-0.html)
-->

---

## 2. Control Plane Debugging

### EKS Control Plane Log Types

EKS offers five control-plane log types. They are sent to the regional CloudWatch log group only when enabled; enabling logging does not reconstruct missing historical logs. Scope log access and retention and account for CloudWatch ingestion/storage/query charges. A missing group/stream can reflect disabled logging, no delivered data, the wrong region or denied access—not necessarily a control-plane failure.

| Type | Evidence |
| --- | --- |
| api | API server operation and error messages |
| audit | API request identity, verb, resource and response status |
| authenticator | IAM-to-Kubernetes authentication evidence |
| controllerManager | Controller reconciliation messages |
| scheduler | Scheduling decisions/errors |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
LOG_GROUP="/aws/eks/$CLUSTER_NAME/cluster"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
aws logs describe-log-streams --region "$AWS_REGION" --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime --descending --max-items 10 \
  --query 'logStreams[].{Name:logStreamName,LastEvent:lastEventTimestamp}'
```
```bash
# MUTATION: review cost, retention, access and available subnet IPs first.
set -euo pipefail
UPDATE_ID=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --update-id "$UPDATE_ID" --query update
```
The change is asynchronous. Track the returned update ID until Successful; Failed/Cancelled or a client timeout is not success. Then verify describe-cluster and new log delivery. Cluster ACTIVE alone does not identify completion of this update. The update can require up to five available IPs in each configured cluster subnet; review the current EKS logging prerequisites.

### CloudWatch Logs Insights Queries

Run each block as a **separate Logs Insights QL query**, not as Bash or SQL. Select the exact log group and time window in the console or StartQuery request. These use EKS JSON audit fields when discovered by CloudWatch; inspect representative records and nested-log parsing if your pipeline changes the format. A query matching no events does not prove that the service was healthy or that logs were delivered.

#### API error messages

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 100
```

#### Error counts within the selected time window

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| stats count(*) as error_count by bin(5m)
```

#### Authenticator messages requiring inspection

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /access denied|Unauthorized|unauthorized/
| sort @timestamp desc
| limit 50
```

#### Structured audit authentication/authorization denials

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 100
```

#### Structured audit activity for one reviewed identity

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_OBSERVED_KUBERNETES_USERNAME"
| sort @timestamp desc
| limit 50
```

#### Audit 429 events by identity and resource

```text
fields user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 429
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

#### API request volume, not necessarily throttling

```text
fields user.username, verb, objectRef.resource
| filter @logStream like /kube-apiserver-audit/
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

Audit 401/403 distinguishes request-level denials from authenticator-message searches. A count of API calls is not a count of throttled calls, and an aggregated time-bin result no longer has each event’s @timestamp to sort by. StartQuery returns a query ID: poll GetQueryResults to Complete and preserve Failed/Cancelled/Timeout/missing-data states. The [monitoring chapter](06-eks-monitoring-logging.md) includes the bounded query/polling workflow. No live CloudWatch query was run in this audit.

[EKS control-plane logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html) · [AWS audit-field examples](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)

### IAM Authentication Troubleshooting

Run the account/context guard from the initial triage first. Distinguish the human/automation IAM identity used by kubectl, node bootstrap identity, and the AWS identity used inside an application Pod. Successful token generation is not proof of Kubernetes authentication or authorization.

The EKS IAM token beginning k8s-aws-v1 is a base64url-encoded presigned STS request, **not a three-part JWT**. Do not decode/print it as JSON or paste it into logs. Kubernetes projected ServiceAccount tokens are a different JWT credential.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
aws sts get-caller-identity
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,AuthenticationMode:accessConfig.authenticationMode}'
# Print only the credential expiry, not the bearer token.
aws eks get-token --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --query status.expirationTimestamp --output text
kubectl --context "$KUBE_CONTEXT" auth whoami
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" auth can-i get pods
```
AuthenticationMode determines where to inspect access. In API/API_AND_CONFIG_MAP mode, inspect the principal’s access entry, associated policy scope and RBAC bindings; in CONFIG_MAP mode inspect the existing legacy mapping. Do not switch authentication mode or replace aws-auth to fix an unclassified 401/403. Access-mode migration has its own prerequisites and irreversible transitions. IAM role paths and STS session ARNs must not be guessed from string substitutions.

```bash
# Run for API or API_AND_CONFIG_MAP authentication mode.
aws eks list-access-entries --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
: "${PRINCIPAL_ARN:?Use a reviewed IAM role/user ARN, not an STS assumed-role session ARN}"
aws eks describe-access-entry --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
aws eks list-associated-access-policies --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
```
```bash
# Read-only legacy mapping inspection for CONFIG_MAP/API_AND_CONFIG_MAP clusters.
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap aws-auth -o yaml
```
Preserve existing node bootstrap mappings. A group name alone grants no permissions without the relevant binding; use reviewed least-privilege access rather than adding system:masters as a diagnostic step. A 403 indicates an authorization denial, while a 401 can indicate invalid/expired credentials. Network/TLS failures are separate evidence.

### IRSA Troubleshooting

IRSA needs the correct OIDC issuer/provider, role trust policy matching the namespace/ServiceAccount subject and sts.amazonaws.com audience, and a workload SDK that uses and refreshes web-identity credentials. The annotation below is only one part of that configuration. Its namespace/role are placeholders; no role, provider or bucket permission is created by this YAML.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: diagnostics-example
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/owned-s3-access-role
```
```bash
set -euo pipefail
: "${SERVICE_ACCOUNT:?Set the actual ServiceAccount on the Pod}"
: "${POD_NAME:?Set an owned Pod}"; : "${CONTAINER_NAME:?Set its application container}"
: "${IRSA_ROLE_NAME:?Set the reviewed IAM role name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get serviceaccount "$SERVICE_ACCOUNT" \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text
aws iam get-role --role-name "$IRSA_ROLE_NAME" --query Role.AssumeRolePolicyDocument
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid,serviceAccount:.spec.serviceAccountName,
  envNames:[.spec.containers[] | {name,envNames:[.env[]?.name]}],
  projectedVolumes:[.spec.volumes[]? | select(.projected) | {name,projected}]
}'
```
Inspect environment **names**, token-file path/mount metadata and the SDK credential chain without printing secret values or token bytes. Static credentials or another provider earlier in the SDK chain can override the intended identity. Use the actual application container; a newly created debug Pod or container can have different identity/configuration.

```bash
# Optional read-only identity request, only if AWS CLI is already in this container.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- aws sts get-caller-identity
```
An STS identity response identifies the role in use; it does not prove authorization to list all buckets or access a particular object. Do not run aws s3 ls across the account merely to test identity.

### Pod Identity Troubleshooting

```bash
aws eks list-pod-identity-associations --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --namespace "$NAMESPACE" --service-account "$SERVICE_ACCOUNT"
: "${ASSOCIATION_ID:?Use the exact matching association ID}"
aws eks describe-pod-identity-association --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --association-id "$ASSOCIATION_ID"
# Standard EC2-node setup only; Auto Mode provides the integration itself.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods \
  -l app.kubernetes.io/name=eks-pod-identity-agent
```
Check the association, role trust/permissions, supported SDK credential provider and agent/node reachability. Auto Mode has built-in support and does not require installing a duplicate agent; Fargate does not support EKS Pod Identity. Keep association creation/change separate from these diagnostics. IRSA and Pod Identity have different token audiences and credential delivery paths; the operator’s AWS CLI identity is neither by default.

### ServiceAccount Token Lifetime and Rotation

There is no universal “maximum 24 hours” for projected tokens: requested duration and the API server’s configured limit are distinct. Kubelet requests rotation when a token is older than 80% of its TTL or older than 24 hours, and the application must reload the rotated file. EKS documents a 90-day compatibility extension for its Kubernetes API ServiceAccount-token migration and stale-token audit annotations; that is not a safe cache duration or a lifetime promise for IRSA, Pod Identity or arbitrary relying parties.

The following example requests a one-hour custom token for an STS audience. It does not extend the default API token or automatically configure IRSA. The existing namespace/ServiceAccount, reviewed image, role trust and application SDK/token-file configuration must be prepared separately. An STS-audience token must not be assumed valid for the Kubernetes API.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: audience-token-example
  namespace: diagnostics-example
spec:
  serviceAccountName: owned-app
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
      readOnly: true
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600
          audience: sts.amazonaws.com
```
[EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html) · [EKS token migration/rotation](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) · [Kubernetes projected tokens](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/) · [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) · [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)

### EKS Add-on Error Patterns

Read the installed version, ownership, configuration/identity settings and health.issues before changing an add-on. ACTIVE is an add-on status, not proof of all customer traffic working; DEGRADED denotes health issues and does not merely mean slower performance. CREATE_FAILED/UPDATE_FAILED/DELETE_FAILED require the actual issue details. An absent standard add-on can be expected for features managed by Auto Mode.

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${ADDON_NAME:?Set the existing owned add-on}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" \
  --query 'addon.{Version:addonVersion,Status:status,Issues:health.issues,Configuration:configurationValues,Role:serviceAccountRoleArn,PodIdentity:podIdentityAssociations}'
CLUSTER_VERSION=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version "$CLUSTER_VERSION" \
  --query 'addons[].addonVersions[].{Version:addonVersion,Architectures:architecture,ComputeTypes:computeTypes,Compatibility:compatibilities}'
```
Do not treat the first version in the response as “latest” or automatically compatible with every node type. Review architecture, compute type, default-version markers, configuration schema, IAM/Pod Identity and the component’s migration sequence. Configuration output may be sensitive; keep it private. A version update is an intentional change, not an initial diagnostic.

```bash
# MUTATION: use a reviewed compatible version and configuration/identity plan.
set -euo pipefail
: "${REVIEWED_ADDON_VERSION:?Choose from the compatible versions after review}"
: "${REVIEWED_ADDON_CONFIG:?Set the path to the reviewed JSON configuration file}"
test -f "$REVIEWED_ADDON_CONFIG"
aws eks describe-addon-configuration --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --addon-version "$REVIEWED_ADDON_VERSION" --query configurationSchema --output text
# The configuration file must be checked against this version's schema before this request.
UPDATE_ID=$(aws eks update-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --addon-version "$REVIEWED_ADDON_VERSION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG" \
  --resolve-conflicts PRESERVE --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --update-id "$UPDATE_ID" --query update
```
PRESERVE asks EKS to retain existing custom settings when resolving conflicts; it is not a backup or a guarantee that arbitrary old settings work with the new release. OVERWRITE can reset conflicting customization and must be separately reviewed. Follow this exact update ID to completion, inspect update errors and verify resulting add-on health. Review configurationValues and identity changes explicitly instead of silently omitting or overwriting them.

[Update an EKS add-on](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)

---

## 3. Node-Level Troubleshooting

### Node Join Failure Diagnosis

These are hypotheses to test against the instance/NodeClaim, bootstrap logs, endpoint reachability and authentication mode—not eight guaranteed root causes.

| Area | What to verify |
| --- | --- |
| Bootstrap and AMI | Correct cluster name/endpoint/CA, OS-specific bootstrap, architecture and compatible kubelet/AMI; not a universal exact-version-equality rule |
| Network/security | Node→API TCP 443, API→kubelet TCP 10250, DNS and workload-specific paths; validate direction, security-group membership and routing |
| VPC DNS | DNS support/hostnames, DHCP resolver/domain configuration and the endpoint actually used |
| Identity | Node IAM role and Kubernetes node access entry/legacy mapping, using a role ARN rather than an instance-profile ARN |
| Ownership/discovery tags | Provisioner-specific node ownership tags; do not confuse them with subnet tags for load-balancer discovery |
| Private access | Required EKS/ECR/S3/STS and other service paths via reviewed endpoints or egress; a NAT gateway is not mandatory in every private-cluster design |
| Launch configuration | Correct role/profile handling for the actual provisioner, launch-template version, capacity and subnet IP availability |
| Initialization | Inspect nodeadm/cloud-init/bootstrap evidence appropriate to the selected AMI; paths are not universal across AL2023, Bottlerocket, Windows or Auto Mode |

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?Set the exact owned node name}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
  os:.status.nodeInfo.osImage,kernel:.status.nodeInfo.kernelVersion,
  kubelet:.status.nodeInfo.kubeletVersion,runtime:.status.nodeInfo.containerRuntimeVersion,
  labels:.metadata.labels,taints:.spec.taints,conditions:.status.conditions
}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.uid=$NODE_UID" --sort-by='.metadata.creationTimestamp'
```
```bash
# EC2-backed nodes only: map the Node providerID to an inspected instance ID/Region.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the verified EC2 ID, not a guessed node-name conversion}"
aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,AZ:Placement.AvailabilityZone,Subnet:SubnetId,Profile:IamInstanceProfile,Groups:SecurityGroups,Image:ImageId}'
aws ec2 describe-instance-status --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --include-all-instances
```
A not-yet-registered instance has no Node object: use the owned managed-node-group/NodeClaim/instance evidence instead. Ready=False and missing heartbeats leading to Ready=Unknown require different evidence. Node pressure can coexist with Ready; do not infer its cause from one display string. New Auto Mode EC2 managed instances can be hidden from generic EC2 list views by default; direct instance-ID queries or explicitly including managed resources are different from changing account-wide visibility settings.

### NotReady Node Decision Tree

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![Decision-tree flowchart for diagnosing a NotReady EKS node, walking down through EC2 instance status, kubelet health, network connectivity, and disk/memory pressure to containerd runtime health, with the matching remediation command at each branch.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-1.html)
-->

### Host and Managed-Node Diagnostics

For customer-accessible Linux nodes, SSM requires the node agent, role/network prerequisites and authorized access to that exact instance. It opens a session. EKS Auto Mode managed instances do not support direct SSH access; use its documented NodeDiagnostic/console-output path or the supported kubectl debug node workflow. The current Auto Mode guide explicitly supports an **explicit sysadmin debug profile** for live logs; this is a privileged Pod creation, not an SSH session or a default debug privilege. NodeDiagnostic collection can upload sensitive logs/captures to S3 and needs its own reviewed scope/storage permissions.

```bash
# Interactive host access: an operational session, not an automatic triage step.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the reviewed self-managed or managed-node-group instance}"
aws ssm start-session --region "$AWS_REGION" --target "$INSTANCE_ID"
```
```bash
# Read-only Linux/systemd host checks after authorized access.
sudo systemctl show kubelet containerd --no-pager \
  -p Id -p LoadState -p ActiveState -p SubState -p ExecMainStatus
sudo journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
sudo journalctl -u containerd --since "15 minutes ago" -n 100 --no-pager
sudo crictl info
sudo crictl ps
sudo crictl ps -a
sudo crictl images
df -h
df -i
sudo journalctl --disk-usage
```
```bash
# Exact container ID only; log content may be sensitive.
: "${CONTAINER_ID:?Use an inspected CRI container ID}"
sudo crictl logs --tail=100 "$CONTAINER_ID"
```
These systemd/CRI commands assume those components/tools exist on the selected host. Configure the correct CRI endpoint for crictl. Use bounded journal reads; journalctl -f piped into tail may never finish. Avoid printing kubeconfig/client keys or indiscriminately deleting logs, exited containers or image caches. They can contain needed evidence or be managed by kubelet garbage collection. A restart, drain, replacement or retention change requires a diagnosed condition and a separate reviewed recovery step.

### Resource Pressure

DiskPressure concerns available bytes/inodes and configured eviction thresholds, not only df capacity. Inspect both df -h and df -i, mount identity and kubelet events. If retention cleanup is approved, the old journalctl --vacuum-size=500M value is only an example policy; collect required evidence first and do not delete /var/log globs. MemoryPressure and a container OOM are distinct signals: correlate memory limits, node availability, working set, logs and pressure metrics. Increasing a limit or adding a node does not prove the root cause is fixed.

```bash
# Read-only host evidence, not remediation.
free -h
awk '/MemTotal|MemFree|MemAvailable|Buffers|Cached/ {print}' /proc/meminfo
cat /proc/sys/kernel/pid_max
cat /proc/sys/kernel/threads-max
ps -eLf --no-headers | wc -l
ps -eo pid,comm,nlwp --sort=-nlwp | head -20
if [ -r /proc/pressure/memory ]; then cat /proc/pressure/memory; fi
if [ -r /proc/pressure/cpu ]; then cat /proc/pressure/cpu; fi
```
The process directory count is not a count of all threads/tasks. ps NLWP and kernel limits are clues; kubelet PID-pressure calculations and cgroup PID limits require their own interpretation. Do not label a generic high-memory percentage as the Kubernetes MemoryPressure condition. Treat missing metrics as unavailable evidence.

### Karpenter Provisioning Issues

```bash
# Self-managed Karpenter; use the actual release namespace and selected objects.
: "${KARPENTER_NAMESPACE:?Set the existing controller namespace}"
: "${NODEPOOL_NAME:?}"; : "${NODECLAIM_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$KARPENTER_NAMESPACE" logs \
  -l app.kubernetes.io/name=karpenter -c controller --since=15m --tail=200 --prefix
kubectl --context "$KUBE_CONTEXT" get nodepool "$NODEPOOL_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get nodeclaim "$NODECLAIM_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.name=$NODECLAIM_NAME" --sort-by='.metadata.creationTimestamp'
```
Inspect NodePool/NodeClass readiness, NodeClaim conditions/events, constraints, limits, subnet IPs, IAM and EC2 capacity. For Auto Mode, use the included controller’s NodeClaim/NodeClass/events and audit-log evidence; do not expect a self-managed karpenter Deployment/namespace. The following self-managed Karpenter v1 schema pattern is illustrative and requires a compatible release and a reviewed existing EC2NodeClass. It is not a command to replace the cluster’s default pool. CPU/memory limits are ceilings, not reserved capacity; the capacity-type list does not prove Spot-only behavior or AZ balance.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-capacity-example
spec:
  template:
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      - key: karpenter.k8s.aws/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-existing-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
```
### Managed Node Group Error Codes

| Issue | Meaning and evidence |
| --- | --- |
| AccessDenied | Kubernetes API authentication/authorization failure; inspect node access and EKS node-manager RBAC as well as IAM |
| AsgInstanceLaunchFailures | ASG launch failure; inspect the actual activity message, template, capacity and permissions |
| ClusterUnreachable | Kubernetes API connectivity or request-processing timeouts, not automatically a missing VPC endpoint |
| InsufficientFreeAddresses | Selected node subnets lack available IPs; existing subnet IPv4 CIDR cannot be expanded in place |
| NodeCreationFailure | Launched instances failed to register; bootstrap, access and required network paths are common checks |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${NODEGROUP_NAME:?Set the exact managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Issues:health.issues,Version:version,Release:releaseVersion,Subnets:subnets,Role:nodeRole,LaunchTemplate:launchTemplate,Repair:nodeRepairConfig}'
# For a Kubernetes authorization issue, inspect rather than blindly replace EKS-managed RBAC.
kubectl --context "$KUBE_CONTEXT" get clusterrole eks:node-manager -o yaml
kubectl --context "$KUBE_CONTEXT" get clusterrolebinding eks:node-manager -o yaml
```
Use each issue’s message/resourceIds and the current AWS repair procedure. The troubleshooting guide describes NodeCreationFailure after managed nodes fail to join within 15 minutes; this is not a guarantee that every boot completes within that time. If subnets need more space, plan new address space/subnets and the provisioner-specific migration instead of editing an existing CIDR. EKS-managed RBAC shapes can evolve: do not paste an old replacement ClusterRole merely because AccessDenied appeared. Node repair/eviction is separate from inspection and must account for workloads, budgets, data and the active node-management mode.

[EKS troubleshooting](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html) · [Auto Mode diagnostic paths](https://docs.aws.amazon.com/eks/latest/userguide/auto-troubleshoot.html) · [Security group paths](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html) · [Private clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html) · [Karpenter compatibility](https://karpenter.sh/docs/upgrading/compatibility/)

### Node Readiness Controller (Staged Boot Verification)

The Kubernetes SIGs Node Readiness Controller is a real out-of-band controller. The reviewed v0.5.0 release uses the cluster-scoped `readiness.node.x-k8s.io/v1alpha1` `NodeReadinessRule`; it is not a built-in EKS ConfigMap processor or a GA field on the Node API.

The controller reads Node conditions and manages taints. It does **not** execute arbitrary `checks[].probe.exec` entries in a ConfigMap. The original file-existence/containerd checks need a separately implemented, authorized reporter or NPD custom monitor that publishes the corresponding conditions. A CNI configuration file existing does not by itself prove CNI readiness. The project's bundled reporter polls an HTTP endpoint using `CHECK_ENDPOINT`, `CONDITION_TYPE` and `NODE_NAME`; its configuration is not the former exec-probe format.

This rule is an explicit test-scope **taint preview**. Applying it still creates a cluster resource and the controller updates status, but `dryRun: true` does not add/remove node taints. The example condition names and node label are custom prerequisites, not labels/conditions automatically supplied by EKS.

```yaml
apiVersion: readiness.node.x-k8s.io/v1alpha1
kind: NodeReadinessRule
metadata:
  name: reviewed-bootstrap-readiness
spec:
  dryRun: true
  enforcementMode: bootstrap-only
  nodeSelector:
    matchLabels:
      audit.example.com/readiness-demo: 'true'
  conditions:
  - type: audit.example.com/CNIReady
    requiredStatus: 'True'
  - type: audit.example.com/ContainerRuntimeReady
    requiredStatus: 'True'
  taint:
    key: readiness.k8s.io/bootstrap-not-ready
    value: pending
    effect: NoSchedule
```

Inspect `status.dryRunResults`, `status.nodeEvaluations`, failed nodes and the actual selected Node conditions before enabling enforcement.

```bash
# Read-only: the controller and released CRD must already be installed.
: "${KUBE_CONTEXT:?Set the verified context}"
kubectl --context "$KUBE_CONTEXT" get nodereadinessrule reviewed-bootstrap-readiness -o yaml
kubectl --context "$KUBE_CONTEXT" get nodes \
  -l audit.example.com/readiness-demo=true -o json
```

For a bootstrap gate, register new nodes with the matching startup taint before scheduling can race the controller. The reporter and required system DaemonSets must tolerate that taint and be able to reach the API. When all requirements pass, bootstrap-only mode removes the taint and records completion; it does not reapply the gate if those conditions later fail. Continuous mode is a separate policy choice.

`NoSchedule` blocks new Pods that do not tolerate the taint; it does not evict existing Pods. Do not set `defaultStatus` on bootstrap-only rules: the release rejects that combination. Native CRD validation here does not prove reporter health, admission-webhook behavior or operation on every EKS node type. No node labels, taints, controllers or conditions were changed during this audit.

[Release v0.5.0](https://github.com/kubernetes-sigs/node-readiness-controller/releases/tag/v0.5.0) · [Enforcement and dry-run semantics](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/user-guide/concepts.md) · [Reporter configuration](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/reference/reporter-configuration.md)

---

## 4. Workload Debugging

### Pod and Container State

Pod phases are Pending, Running, Succeeded, Failed and Unknown. Container states are Waiting, Running and Terminated; ContainerCreating and CrashLoopBackOff are reasons/display information rather than extra Pod phases. Running is not equivalent to Ready. A restart policy can restart a container within a Pod; it does not turn a terminal Failed Pod back into Pending. A controller replacement is a new Pod with a new UID.

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![State machine showing a Kubernetes Pod's lifecycle -- Pending to ContainerCreating to Running to Succeeded on the happy path, with ContainerCreating and Running able to fail into Failed, and Failed pods returning to Pending under the restart policy -- annotated with the major failure causes at each state.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-2.html)
-->

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,node:.spec.nodeName,
  phase:.status.phase,reason:.status.reason,conditions:.status.conditions,
  containers:.status.containerStatuses,initContainers:.status.initContainerStatuses,
  ephemeralContainers:.status.ephemeralContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=200
```
```bash
# Separate read: this can fail when no previous container log exists.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --previous --tail=200
```
The previous log is for the most recent terminated instance of the selected container, not a complete restart history. Rotation or Pod deletion can make logs unavailable. Record Pod UID/time and check for replacement during collection; init/sidecar/ephemeral containers can have different failures. Logs and state messages can contain sensitive data, so keep collected evidence private. Do not print every environment variable or application config file as a diagnostic shortcut.

### kubectl debug: Three Different Operations

An ephemeral container modifies the existing Pod; --copy-to creates another Pod; node/ creates a diagnostic Pod on a node. All are mutations and need the relevant RBAC/admission permissions. In the checked kubectl 1.36.2, the default profile is general. It does not automatically mean privileged, and host namespace/filesystem access is distinct from privileged=true.

#### Ephemeral container

```bash
# MUTATION: adds a permanent-to-this-Pod-spec ephemeral-container entry.
: "${DEBUG_IMAGE:?Use a reviewed non-root diagnostic image with a compatible shell}"
: "${DEBUG_CONTAINER_NAME:?Choose an unused container name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" -it \
  --container="$DEBUG_CONTAINER_NAME" --target="$CONTAINER_NAME" \
  --image="$DEBUG_IMAGE" --profile=restricted -- sh
```
The restricted profile drops capabilities, prevents privilege escalation and requests non-root execution/RuntimeDefault seccomp. The image/user/shell must support this; an arbitrary root-only BusyBox image is not guaranteed to start. --target requests the target process namespace only if the runtime supports it. It does not copy the application’s filesystem/env or bypass permissions. Exiting ends the debug process, but the ephemeral-container entry cannot be removed from the existing Pod spec.

#### Pod copy

```bash
# MUTATION: copy only a reviewed reproduction Pod; inspect all side effects first.
: "${DEBUG_POD_NAME:?Choose a new owned Pod name in the same namespace}"
: "${DEBUG_IMAGE:?Use a reviewed diagnostic image that provides sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --keep-labels=false --keep-annotations=false \
  --share-processes=true --profile=general -- sleep 3600
```
The native CLI check confirmed that this replaces the selected container’s image/command and removes init containers, while retaining the ServiceAccount and enabling shared process namespace. Other regular containers, environment/Secret references and volumes can remain and execute or access the same data. A copy stays in the same namespace, can schedule on another node and is not an isolated data clone. Review admission mutation, side effects, identity, persistent volumes and cleanup before using it. General profile capabilities may be rejected by namespace policy; do not relax policy silently.

#### Node diagnostics

```bash
# MUTATION: privileged host diagnostic Pod, only where this access is authorized.
: "${NODE_NAME:?Use the exact reviewed Node}"
: "${NODE_DEBUG_IMAGE:?Use a reviewed image with nsenter}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" -it \
  --image="$NODE_DEBUG_IMAGE" --profile=sysadmin \
  -- nsenter -t 1 -m -- journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
```
Node debug mounts the host root at /host and uses host namespaces; the explicit sysadmin profile adds privileged execution. This gives broad host access even when the chosen command only reads logs. The image must already contain the needed diagnostic tools. The Auto Mode user guide documents this path; ordinary SSH access remains unavailable there. Other OS/node classes require their supported access method. A new debug Pod cannot be assumed to start if kubelet/runtime/networking is broken.

Record the created debug Pod name/UID from the actual operation. Remove only that separate Pod after evidence review; do not delete the application Pod to “clean up” an ephemeral container.

```bash
# MUTATION: remove only the separately created debug Pod after checking its identity.
: "${DEBUG_POD_NAME:?}"; : "${EXPECTED_DEBUG_UID:?Use the UID recorded at creation}"
ACTUAL_DEBUG_UID=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$DEBUG_POD_NAME" \
  -o jsonpath='{.metadata.uid}')
test "$ACTUAL_DEBUG_UID" = "$EXPECTED_DEBUG_UID" || { echo "Debug Pod changed; stop" >&2; exit 1; }
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" delete pod "$DEBUG_POD_NAME" --timeout=2m
```
The UID check is a safety check, not an atomic delete precondition; coordinate the operation so the name cannot be reused between check and delete. No debug containers, privileged workloads or node commands were run in this audit. The native CLI tests used only synthetic loopback API responses.

### Deployment Rollout Management

```bash
# Read-only rollout evidence.
: "${DEPLOYMENT_NAME:?Set the owned Deployment}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=2m
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout history "deployment/$DEPLOYMENT_NAME"
```
```bash
# MUTATION: workload revision rollback, not database/PVC/control-plane rollback.
set -euo pipefail
: "${REVIEWED_REVISION:?Set an inspected compatible revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout undo \
  "deployment/$DEPLOYMENT_NAME" --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=5m
```
A timeout/failure is evidence to inspect, not success. Coordinate GitOps and other reconcilers; rollback does not restore a database or undo schema changes. Deployment pause/resume controls rollout progression, not HPA or all Pod creation. Rollout restart intentionally changes the Pod template and creates replacements even with the same image reference; an unpinned image can resolve differently. Use exact namespace/Deployment and a reviewed update plan rather than combining restart/undo/scale commands into triage.

### HPA/VPA Scaling Issues

```bash
# Read-only: use the actual scaler names and workload namespace.
: "${HPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa "$HPA_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe hpa "$HPA_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: diagnostics-example
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```
```bash
# VPA is a separately installed controller/CRD, not built into EKS.
: "${VPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get vpa "$VPA_NAME" -o json | jq '{
  target:.spec.targetRef,updatePolicy:.spec.updatePolicy,resourcePolicy:.spec.resourcePolicy,
  recommendation:.status.recommendation,conditions:.status.conditions
}'
```
The HPA example requires an existing Deployment and resource-metrics provider, with relevant CPU/memory requests on the target containers. Utilization targets are relative to requests, not limits. Multiple metrics choose the largest recommended replica count, with missing/error metrics affecting decisions; memory utilization is not a universal leak/OOM fix. Scale-down stabilization and rate policies are not a pause switch.

VPA is separately installed. Inspect its actual recommendation, conditions, update mode and supported release. The legacy Auto update-mode name is deprecated in current guidance; choose a documented mode such as recommendations-only Off or a reviewed update mode. Avoid allowing VPA to change the same request denominator that HPA uses without coordination.

### Probe Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-probe-example
  namespace: diagnostics-example
spec:
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    ports:
    - name: http
      containerPort: 8080
    startupProbe:
      httpGet:
        path: /healthz
        port: http
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 30
    livenessProbe:
      httpGet:
        path: /healthz
        port: http
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: http
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
```
Replace the placeholder image and implement the actual health endpoints; this standalone Pod is a schema example, not a replicated production workload. Startup gates liveness/readiness until it succeeds. Thirty attempts at a five-second period plus initial delay form an approximate startup budget, not a strict 150-second deadline. Readiness failure removes readiness for service routing; it does not restart the container. Liveness should not restart healthy processes simply because an external dependency is slow. Validate shutdown, resource pressure and actual response timing separately.

[Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) · [Debug running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) · [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [VPA modes](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)

---

## 5. Networking Diagnostics

### VPC CNI and IP Allocation

Identify the node/network implementation first. The following aws-node settings apply to the standard Amazon VPC CNI path. Auto Mode has its own managed networking/NodeClass controls; changing an aws-node DaemonSet does not configure Auto Mode nodes. Windows, Fargate and Hybrid Nodes have different applicability and diagnostic paths. Keep the initial account/context guard and exact node/namespace scope.

```bash
# Standard Amazon VPC CNI on applicable nodes, not an Auto Mode control interface.
: "${KUBE_CONTEXT:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the inspected EC2 node ID}"
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset aws-node -o json | jq '{
  containers:[.spec.template.spec.containers[] | {name,image,settings:[
    .env[]? | select(.name | IN("ENABLE_PREFIX_DELEGATION","WARM_PREFIX_TARGET","WARM_IP_TARGET",
      "MINIMUM_IP_TARGET","AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG","ENI_CONFIG_LABEL_DEF"))
  ]}]
}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=aws-node -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=aws-node \
  -c aws-node --since=15m --tail=100 --prefix
aws ec2 describe-network-interfaces --region "$AWS_REGION" \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,Subnet:SubnetId,Description:Description,IPv4:PrivateIpAddresses[].PrivateIpAddress,IPv4Prefixes:Ipv4Prefixes,IPv6Prefixes:Ipv6Prefixes,Groups:Groups}'
```
```bash
# Read-only: use subnets actually selected by the node/provisioner, not all account subnets.
: "${SUBNET_ID:?Set an inspected subnet ID}"
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{ID:SubnetId,VPC:VpcId,AZ:AvailabilityZone,CIDR:CidrBlock,AvailableIPv4:AvailableIpAddressCount}'
```
ENI descriptions are not an ownership boundary. Use the inspected instance/subnet IDs and include relevant custom-networking or Pod ENIs. A subnet’s free-address count does not prove there is a contiguous prefix available, and adding a VPC CIDR does not by itself configure Pod networking.

### Prefix Delegation

On a supported Linux/Nitro/CNI setup, prefix delegation can improve IP density and allocation behavior. Verify contiguous prefix space/reservations, ENI/prefix limits, node maxPods/allocatable Pods and migration readiness. Do not enable it blindly on running nodes or infer usable capacity solely from free IPv4 count.

The following is a **configuration fragment for review**, to merge with the actual supported add-on/chart configuration—not a complete replacement of existing settings:

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
Configured WARM_IP_TARGET/MINIMUM_IP_TARGET override WARM_PREFIX_TARGET. A warm target keeps spare addresses/prefixes; it does not reserve node capacity or fix an exhausted/fragmented subnet. Review stored configuration and ownership before a controlled rollout; verify new Pods and actual IPAM state afterwards.

### Custom Networking

Prepare non-overlapping VPC address space, the actual per-AZ Pod subnets, routing/egress, security groups and enough migration capacity before changing CNI mode. The original two-line CIDR/subnet creation plus environment toggle was not a complete operational recipe. Existing subnet IPv4 CIDR cannot be enlarged in place. The standard ENIConfig approach below is distinct from Auto Mode networking controls.

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```
```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
```
The ENIConfig example covers only one AZ and uses placeholder IDs. With zone-based selection, create the correct configuration for every eligible zone and ensure the node has the matching label. Multiple Pod subnets per AZ need a deliberate custom selection scheme. Security-group-for-Pod settings can change which groups apply; check the installed CNI’s precedence. Validate controller configuration, new-node rollout and Pod placement before retiring old capacity. See the [networking guide](03-eks-networking-part1.md) for the broader setup.

### CoreDNS and Resolver Context

Pure Auto Mode nodes run CoreDNS as a node system service. Mixed clusters must retain the Deployment for non-Auto nodes. Absence of that Deployment on a pure Auto cluster is not itself a DNS outage. For Deployment-based DNS:

```bash
# CoreDNS Deployment on standard/mixed clusters; Auto Mode node-system DNS differs.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --since=15m --tail=100 --prefix
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
# Inspect the actual resolver context in an owned application container with these tools.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- cat /etc/resolv.conf
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```
CoreDNS does not log every DNS query unless the relevant logging configuration is enabled. A new test Pod can use a different namespace/node/DNS/identity/policy path than the failing workload. Use the workload’s actual resolver context and a trailing-dot FQDN when testing absolute resolution.

The following ndots=2 value is an experiment, not a universal fix for latency. It changes search behavior and can affect partially qualified names. libc, language resolver and application caching behavior differ; glibc-specific options such as single-request-reopen are not portable assumptions.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-options-example
  namespace: diagnostics-example
spec:
  dnsPolicy: ClusterFirst
  dnsConfig:
    options:
    - name: ndots
      value: '2'
    - name: timeout
      value: '2'
    - name: attempts
      value: '3'
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
```
An illustrative Corefile follows. Compare it with the installed version, required plugins, custom zones/forwarders and managed add-on configuration; do not overwrite a live ConfigMap wholesale. cache, max_concurrent and lameduck values require traffic/health validation. pods insecure is the Kubernetes plugin’s Pod-record mode, not a switch to disable Kubernetes API TLS/authentication.

```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
        max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
```
### Service and EndpointSlice Verification

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json | jq '{
  name:.metadata.name,type:.spec.type,clusterIP:.spec.clusterIP,ipFamilies:.spec.ipFamilies,
  externalName:.spec.externalName,selector:.spec.selector,ports:.spec.ports,
  trafficDistribution:.spec.trafficDistribution,externalTrafficPolicy:.spec.externalTrafficPolicy
}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o json | jq '[.items[] | {
    name:.metadata.name,addressType,ports,
    endpoints:[.endpoints[]? | {addresses,conditions,nodeName,zone,targetRef}]
  }]'
```
Use EndpointSlices for current endpoint inspection; the older Endpoints API is deprecated. Check Service selector/port/targetPort, address family and endpoint ready/serving/terminating conditions. Headless, ExternalName and selectorless Services have different behavior. An endpoint address existing is not proof it can receive the intended traffic, and Service port is not always the application’s container port.

### NetworkPolicy AND/OR Logic

Within one peer, namespaceSelector and podSelector are ANDed; separate peers/rules are alternatives. A podSelector-only peer selects Pods in the policy’s namespace. All applicable NetworkPolicies contribute additive allows; one restrictive policy does not override a broader allow in another. Confirm enforcement support and mode for the actual CNI/node type before treating a manifest as a firewall.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reviewed-api-policy
  namespace: diagnostics-example
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app.kubernetes.io/name: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context "$KUBE_CONTEXT" get namespaces --show-labels
```
This example adds TCP/UDP DNS for matching CoreDNS Pods; database-only egress would otherwise omit DNS. Node-local/Auto Mode DNS has a different path and requires mode-specific verification. Match the actual monitoring/database labels and ports, and add only reviewed external dependencies. The policy is an illustrative change, not a proven production allowlist.

### Bounded Network Tests

```bash
# An intentional, bounded request from the actual workload context with curl installed.
: "${HEALTH_URL:?Set the owned safe health-check URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```
```bash
# In an approved diagnostic context with the named tools.
: "${SERVICE_FQDN:?Set the exact owned service DNS name}"
dig +time=2 +tries=1 "$SERVICE_FQDN"
# Packet capture needs the appropriate capabilities/privileges and an owned target.
: "${TARGET_IP:?Set one reviewed peer IP}"
umask 077
timeout 30 tcpdump -i any -nn -c 100 -s 96 "host $TARGET_IP and port 443" -w owned-capture.pcap
# Separate deliberate load test: only against an agreed iperf3 server.
: "${IPERF_SERVER:?Set the owned test server}"
iperf3 -c "$IPERF_SERVER" -p 5201 -t 10 -P 1 -b 10M
```
Choose a reviewed diagnostic image/tool implementation using the preceding debug workflow; creating a netshoot Pod is a mutation, not passive observation. Packet capture needs capabilities/privilege, not merely a root username, and even bounded captures can contain sensitive headers/data. Store them privately and review before sharing. dig +trace tests direct iterative DNS paths rather than only the workload’s configured resolver. iperf3 is deliberate traffic generation: its throughput is not network latency and is not a measured result from this audit.

[Prefix mode](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html) · [Custom networking](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html) · [NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/) · [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)

---

## 6. Storage Troubleshooting

### Identify the Driver and Permissions

Read the bound PV’s spec.csi.driver and volumeHandle and the StorageClass provisioner. The standard EBS driver is ebs.csi.aws.com; Auto Mode uses ebs.csi.eks.amazonaws.com and its managed controller, so an absent standard controller Deployment can be expected. Standard-driver log commands below require that driver to be installed. EBS cannot be mounted by Fargate Pods or EKS Hybrid Nodes; placing the standard controller on Fargate does not change the data-plane restriction.

```bash
# Read-only: identify the actual installed driver and workload owner first.
kubectl --context "$KUBE_CONTEXT" get csidrivers
: "${CSI_NAMESPACE:?Set the namespace of the installed standard CSI controller}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" get deployments,daemonsets,pods -o wide
: "${CSI_CONTROLLER_NAME:?Use an observed controller Deployment name}"
: "${CSI_CONTAINER_NAME:?Use the CSI plugin container name}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" logs "deployment/$CSI_CONTROLLER_NAME" \
  -c "$CSI_CONTAINER_NAME" --since=15m --tail=100
```
```bash
# Inspect only the role actually used by the standard EBS CSI controller.
: "${CSI_ROLE_NAME:?Set the reviewed role name}"
aws iam get-role --role-name "$CSI_ROLE_NAME" --query Role.AssumeRolePolicyDocument
aws iam list-attached-role-policies --role-name "$CSI_ROLE_NAME"
aws iam list-role-policies --role-name "$CSI_ROLE_NAME"
```
The current EKS guide recommends reviewing AmazonEBSCSIDriverPolicyV2 for standard-driver permissions. It scopes volume/snapshot management using driver ownership tags, with support for CSI-migrated volume tags. Review migration and existing resource tags before replacing an older policy; do not attach an unrestricted Resource:* policy containing every mutation as a generic fix. Some AWS read/list operations require wildcard resources, which is distinct from broad mutation permissions.

Use the actual Pod Identity or IRSA role/trust policy, not an assumed node identity. Customer KMS keys require the relevant key policy/grant/encrypt/decrypt permissions; the documented CreateGrant condition includes kms:GrantIsForAWSResource. Permission to provision a volume does not alone prove permission to use the selected KMS key or attach it to the intended node. No IAM changes are performed by these diagnostic commands.

### EFS Mount Targets and Access Points

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${FILE_SYSTEM_ID:?Use the owned EFS filesystem}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-mount-targets --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
: "${MOUNT_TARGET_ID:?Use the relevant mount target}"
aws efs describe-mount-target-security-groups --region "$AWS_REGION" --mount-target-id "$MOUNT_TARGET_ID"
: "${EFS_SECURITY_GROUP_ID:?Use an observed mount-target security group}"
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$EFS_SECURITY_GROUP_ID"
```
Check filesystem type/Region, reachable mount targets, DNS, TCP 2049 rules and both network directions. Regional EFS and One Zone have different failure-domain behavior. IAM authorization, access-point POSIX identity/directory permissions and Pod security context are separate layers. The following is an existing-filesystem configuration example with placeholder IDs, not a complete filesystem/role/network provisioning recipe.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  gidRangeStart: '1000'
  gidRangeEnd: '2000'
  basePath: /diagnostics-example
mountOptions:
- tls
reclaimPolicy: Retain
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: diagnostics-example
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: reviewed-efs
  resources:
    requests:
      storage: 5Gi
```
A 5Gi PVC request is not an enforced EFS capacity quota. Access points can enforce server-side POSIX identity; do not infer access solely from the client Pod UID or fix it with blanket chmod. TLS mount encryption and filesystem at-rest encryption are distinct. Retain requires an explicit access-point/data cleanup plan and may leave billable resources. Fargate EFS has its own static-provisioning path; do not assume this dynamic example applies to every node type.

### PVC/PV State and Deletion Protection

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?Set the owned claim name}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{
  name:.metadata.name,namespace:.metadata.namespace,uid:.metadata.uid,
  deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
  phase:.status.phase,conditions:.status.conditions,volumeName:.spec.volumeName,
  hasStorageClassName:(.spec | has("storageClassName")),
  storageClassName:.spec.storageClassName,accessModes:.spec.accessModes,resources:.spec.resources
}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json | jq --arg claim "$PVC_NAME" '[
  .items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName? == $claim)) |
  {name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
   node:.spec.nodeName,phase:.status.phase,deleting:.metadata.deletionTimestamp}
]'
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -z "$PV_NAME" ]; then
  echo "No bound PV: inspect StorageClass, consumer scheduling and provisioning events."
else
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o json | jq '{
    name:.metadata.name,uid:.metadata.uid,claimRef:.spec.claimRef,
    deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
    reclaimPolicy:.spec.persistentVolumeReclaimPolicy,csi:.spec.csi,nodeAffinity:.spec.nodeAffinity
  }'
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json | jq --arg pv "$PV_NAME" '[
    .items[] | select(.spec.source.persistentVolumeName == $pv) |
    {name:.metadata.name,driver:.spec.attacher,node:.spec.nodeName,status:.status}
  ]'
fi
```
PVC names are namespace-local; the consumer search must use the claim’s namespace. Inspect claim/PV UIDs, controller owners, VolumeAttachments and finalizers. A deletion timestamp produces a Terminating display state; it is not an additional PVC status.phase. Pending can be expected with WaitForFirstConsumer until a schedulable consumer exists. An omitted storageClassName differs from an explicit empty string, which requests no class.

Do not null every PVC/PV finalizer to make deletion finish. PVC protection, CSI detach/delete work and reclaim policy protect different parts of the lifecycle. First identify consumers—including controllers that may recreate them—attachment state, controller errors, backups and data ownership. A last-resort orphan repair requires the driver-specific recovery procedure and verified data/attachment state; removing metadata does not perform a safe detach or restore data. Delete can remove the backing storage, and Retain is not a backup.

### WaitForFirstConsumer, Topology and Encryption

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-ebs-wffc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: 'true'
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```
This is the standard EBS CSI provisioner. WaitForFirstConsumer makes initial provisioning/binding aware of scheduler constraints; it does not make EBS cross-AZ or repair a volume trapped in an impaired AZ. If restricting workloads to zones such as ap-northeast-2a/2c, align their scheduling constraints with actual CSI topology/available capacity. Do not assume the first PV affinity expression is always the zone or that a Pod’s requested affinity is its actual location.

```bash
# Use the actual consumer node, not the Pod's requested node-affinity text.
: "${NODE_NAME:?Set an observed consumer node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  name:.metadata.name,providerID:.spec.providerID,
  topologyLabels:(.metadata.labels | with_entries(select(.key | contains("topology"))))
}'
kubectl --context "$KUBE_CONTEXT" get csinode "$NODE_NAME" -o json | jq '.spec.drivers'
# For an actual EBS-backed PV, inspect the volume handle and Region before this lookup.
: "${AWS_REGION:?}"; : "${EBS_VOLUME_ID:?Set the inspected EBS volume ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[].{ID:VolumeId,AZ:AvailabilityZone,State:State,Encrypted:Encrypted,KMS:KmsKeyId,Attachments:Attachments}'
```
For Auto Mode, use its separate provisioner and node compatibility requirements. **Set encrypted: "true" explicitly and inspect the resulting volume/KMS key.** The current Auto Mode StorageClass parameter table defaults encrypted to false; encryption of Auto Mode node root/data disks does not prove encryption of every workload PVC. Changing a StorageClass does not retroactively change an existing volume.

An existing EBS volume cannot attach across AZs simply because the class uses WaitForFirstConsumer. A migration/recovery needs the documented snapshot or controlled static-volume procedure, correct ownership tags/IAM and application-consistent data handling; it is not a driver-name edit. Snapshot controllers/CRDs are separate prerequisites, and a created snapshot is not proof a restore works. ReadWriteOnce permits access from one node and is not universally “one Pod”; Auto Mode SELinux isolation can add further cross-Pod restrictions. Preserve data and review the intended access/consistency model before changing it.

[EBS CSI/IAM](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Managed-policy scopes](https://docs.aws.amazon.com/eks/latest/userguide/security-iam-awsmanpol.html) · [Auto Mode parameters](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [PV lifecycle](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

---

## 7. Observability Architecture

### Container Insights Setup

```bash
# Install CloudWatch Agent and Fluent Bit
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v1.0.0-eksbuild.1

# Or install with Helm
helm repo add aws-observability https://aws-observability.github.io/helm-charts
helm install amazon-cloudwatch-observability \
  aws-observability/amazon-cloudwatch-observability \
  --namespace amazon-cloudwatch --create-namespace \
  --set clusterName=my-cluster \
  --set region=ap-northeast-2
```

### PromQL Query Examples

#### CPU Throttling Detection

```promql
# CPU throttling ratio
sum(rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m])) by (pod, namespace)
/
sum(rate(container_cpu_cfs_periods_total{container!=""}[5m])) by (pod, namespace)
> 0.5

# Top 10 pods with high CPU throttling
topk(10,
  sum(rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m])) by (pod, namespace)
  /
  sum(rate(container_cpu_cfs_periods_total{container!=""}[5m])) by (pod, namespace)
)
```

#### OOMKilled Event Detection

```promql
# Pods with OOMKilled
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1

# OOMKilled count in last hour
sum(changes(kube_pod_container_status_restarts_total[1h])) by (pod, namespace)
* on (pod, namespace) group_left
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}

# Pods with high memory usage (OOM risk)
(
  sum(container_memory_working_set_bytes{container!=""}) by (pod, namespace)
  /
  sum(kube_pod_container_resource_limits{resource="memory"}) by (pod, namespace)
) > 0.9
```

#### Pod Restart Rate

```promql
# Restart count in last hour
sum(increase(kube_pod_container_status_restarts_total[1h])) by (pod, namespace) > 3

# Top 10 pods with most restarts
topk(10, sum(increase(kube_pod_container_status_restarts_total[1h])) by (pod, namespace))

# Pods in CrashLoopBackOff state
kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} == 1
```

### CloudWatch Logs Insights Search Patterns

```sql
-- Error log search
fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name
| filter @message like /error|Error|ERROR|exception|Exception|EXCEPTION/
| sort @timestamp desc
| limit 100

-- Specific pod logs
fields @timestamp, @message
| filter kubernetes.pod_name = "my-pod-name"
| sort @timestamp desc
| limit 500

-- Response time analysis (when app logs include response time)
fields @timestamp, @message
| parse @message /response_time=(?<response_time>\d+)ms/
| stats avg(response_time) as avg_response, max(response_time) as max_response by bin(5m)

-- OOMKilled event tracking
fields @timestamp, @message
| filter @message like /OOMKilled|Out of memory|oom-kill/
| sort @timestamp desc
| limit 50
```

### PrometheusRule Example

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-alerts
  namespace: monitoring
spec:
  groups:
  - name: eks-node-alerts
    rules:
    - alert: NodeNotReady
      expr: kube_node_status_condition{condition="Ready",status="true"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Node {{ $labels.node }} is in NotReady state"
        description: "Node has been in NotReady state for more than 5 minutes. Immediate attention required."

    - alert: NodeMemoryPressure
      expr: kube_node_status_condition{condition="MemoryPressure",status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Memory pressure on node {{ $labels.node }}"

    - alert: NodeDiskPressure
      expr: kube_node_status_condition{condition="DiskPressure",status="true"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Disk pressure on node {{ $labels.node }}"

  - name: eks-pod-alerts
    rules:
    - alert: PodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[15m]) * 60 * 15 > 3
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"

    - alert: PodNotReady
      expr: |
        sum by (namespace, pod) (
          max by(namespace, pod) (kube_pod_status_phase{phase=~"Pending|Unknown"}) *
          on(namespace, pod) group_left(owner_kind)
          topk by(namespace, pod) (1, max by(namespace, pod, owner_kind) (kube_pod_owner{owner_kind!="Job"}))
        ) > 0
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} has not been Ready for more than 15 minutes"

    - alert: ContainerOOMKilled
      expr: kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
      for: 0m
      labels:
        severity: warning
      annotations:
        summary: "Container {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container }} was OOMKilled"

  - name: eks-resource-alerts
    rules:
    - alert: HighCPUThrottling
      expr: |
        sum(rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m])) by (pod, namespace)
        /
        sum(rate(container_cpu_cfs_periods_total{container!=""}[5m])) by (pod, namespace)
        > 0.5
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "CPU throttling for pod {{ $labels.namespace }}/{{ $labels.pod }} exceeds 50%"
```

### ADOT (AWS Distro for OpenTelemetry) Configuration

```yaml
# ADOT Collector configuration
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: adot-collector
  namespace: opentelemetry
spec:
  mode: deployment
  serviceAccount: adot-collector
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
      prometheus:
        config:
          scrape_configs:
            - job_name: 'kubernetes-pods'
              kubernetes_sd_configs:
                - role: pod
              relabel_configs:
                - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
                  action: keep
                  regex: true

    processors:
      batch:
        timeout: 30s
        send_batch_size: 8192
      memory_limiter:
        limit_mib: 500
        spike_limit_mib: 100
        check_interval: 5s

    exporters:
      awsxray:
        region: ap-northeast-2
      awsemf:
        region: ap-northeast-2
        namespace: ContainerInsights
        log_group_name: '/aws/containerinsights/{ClusterName}/performance'
      prometheusremotewrite:
        endpoint: "https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/ws-xxxxx/api/v1/remote_write"
        auth:
          authenticator: sigv4auth
        resource_to_telemetry_conversion:
          enabled: true

    extensions:
      sigv4auth:
        region: ap-northeast-2
        service: "aps"

    service:
      extensions: [sigv4auth]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch, memory_limiter]
          exporters: [awsxray]
        metrics:
          receivers: [otlp, prometheus]
          processors: [batch, memory_limiter]
          exporters: [awsemf, prometheusremotewrite]
```

---

## 8. Failure Detection Architecture

### 4-Layer Detection Pipeline

![Four-stage EKS failure detection pipeline showing metrics, logs, traces, and events flowing from data sources through collection tools (CloudWatch Agent, Fluent Bit, ADOT Collector, Prometheus) into an analysis layer (CloudWatch Logs Insights, metric alarms, anomaly detection, composite alarms) and out to alerting channels (SNS, Slack, PagerDuty, EventBridge).](../.gitbook/assets/en-eks-11-eks-advanced-debugging-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-3.html)

### Reference Architecture 1: AWS Native

```yaml
# Fluent Bit ConfigMap for CloudWatch
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: amazon-cloudwatch
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Grace         30
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/fluent-bit/state/flb_kube.db
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       log_processed
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name                cloudwatch_logs
        Match               kube.*
        region              ap-northeast-2
        log_group_name      /aws/eks/my-cluster/containers
        log_stream_prefix   fluentbit-
        auto_create_group   true
```

### Reference Architecture 2: Open Source Stack

```yaml
# Prometheus + Alertmanager + Grafana
---
# Alertmanager configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'

    route:
      group_by: ['alertname', 'namespace', 'severity']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'default-receiver'
      routes:
        - match:
            severity: critical
          receiver: 'pagerduty-critical'
          continue: true
        - match:
            severity: warning
          receiver: 'slack-warnings'

    receivers:
      - name: 'default-receiver'
        slack_configs:
          - channel: '#alerts-default'
            send_resolved: true

      - name: 'pagerduty-critical'
        pagerduty_configs:
          - service_key: '<pagerduty-service-key>'
            severity: critical

      - name: 'slack-warnings'
        slack_configs:
          - channel: '#alerts-warnings'
            send_resolved: true
            title: '{{ .Status | toUpper }}: {{ .CommonAnnotations.summary }}'
            text: '{{ .CommonAnnotations.description }}'

    inhibit_rules:
      - source_match:
          severity: 'critical'
        target_match:
          severity: 'warning'
        equal: ['alertname', 'namespace']
```

### Detection Patterns

#### Threshold-based Detection

```yaml
# CloudWatch Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-High-CPU-Usage" \
  --alarm-description "EKS node CPU usage exceeds 80%" \
  --metric-name node_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=my-cluster \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-alerts
```

#### Anomaly Detection

```yaml
# CloudWatch Anomaly Detection Alarm
aws cloudwatch put-anomaly-detector \
  --namespace ContainerInsights \
  --metric-name pod_cpu_utilization \
  --stat Average \
  --dimensions Name=ClusterName,Value=my-cluster

aws cloudwatch put-metric-alarm \
  --alarm-name "EKS-Anomaly-CPU" \
  --alarm-description "Abnormal CPU usage pattern detected" \
  --metrics '[
    {
      "Id": "m1",
      "MetricStat": {
        "Metric": {
          "Namespace": "ContainerInsights",
          "MetricName": "pod_cpu_utilization",
          "Dimensions": [{"Name": "ClusterName", "Value": "my-cluster"}]
        },
        "Period": 300,
        "Stat": "Average"
      }
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)"
    }
  ]' \
  --threshold-metric-id ad1 \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-anomaly-alerts
```

#### Composite Alarm

```bash
# Create composite alarm
aws cloudwatch put-composite-alarm \
  --alarm-name "EKS-Critical-State" \
  --alarm-description "Cluster critical state" \
  --alarm-rule "ALARM(EKS-High-CPU-Usage) AND ALARM(EKS-High-Memory-Usage)" \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:eks-critical-alerts \
  --ok-actions arn:aws:sns:ap-northeast-2:123456789012:eks-resolved
```

#### Log-based Metrics

```bash
# Extract metrics from logs
aws logs put-metric-filter \
  --log-group-name "/aws/eks/my-cluster/containers" \
  --filter-name "ErrorCount" \
  --filter-pattern "[..., level=\"ERROR\", ...]" \
  --metric-transformations \
    metricName=ApplicationErrors,metricNamespace=EKS/Application,metricValue=1
```

### Maturity Model

| Level | Description | MTTD Target | Key Capabilities |
|-------|-------------|-------------|------------------|
| **Level 1** | Basic | 30 minutes | Basic metric alerts, manual log search |
| **Level 2** | Reactive | 15 minutes | Threshold alerts, log-based alerts, basic dashboards |
| **Level 3** | Proactive | 5 minutes | Anomaly detection, composite alarms, automated runbooks |
| **Level 4** | Predictive | 2 minutes | ML-based prediction, auto-remediation, chaos engineering |

### EventBridge + Lambda Auto-Remediation

```yaml
# EventBridge Rule
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "alarmName": ["EKS-Pod-CrashLooping"],
    "state": {
      "value": ["ALARM"]
    }
  }
}
```

```python
# Lambda auto-remediation function
import boto3
import json
from kubernetes import client, config

def lambda_handler(event, context):
    alarm_name = event['detail']['alarmName']

    # Get EKS cluster credentials
    eks = boto3.client('eks')
    cluster_info = eks.describe_cluster(name='my-cluster')

    # Configure Kubernetes client
    # ... (kubeconfig setup)

    # Restart CrashLooping pod
    if 'CrashLooping' in alarm_name:
        v1 = client.CoreV1Api()
        # Delete problem pod (Deployment will recreate)
        v1.delete_namespaced_pod(
            name=extract_pod_name(event),
            namespace=extract_namespace(event),
            body=client.V1DeleteOptions()
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Auto-remediation executed')
    }
```

### Alert Channel Matrix by Severity

| Severity | Slack | PagerDuty | Email | SMS | Auto-Remediation |
|----------|-------|-----------|-------|-----|------------------|
| **P1 Critical** | #incidents | Immediate | Team Lead | On-call | Yes |
| **P2 High** | #alerts-high | 15min delay | Team | - | Conditional |
| **P3 Medium** | #alerts | - | Team | - | No |
| **P4 Low** | #alerts-low | - | Daily digest | - | No |

---

## 9. Quick Reference

### Error Pattern Lookup Table

| Symptom | Cause | Resolution |
|---------|-------|------------|
| **CrashLoopBackOff** | Application crash, invalid command, missing dependencies | `kubectl logs --previous`, review application code/config |
| **ImagePullBackOff** | Image not found, wrong tag, authentication failure | Verify image name, review `imagePullSecrets` |
| **OOMKilled** | Memory limit exceeded | Increase memory limit, fix memory leak |
| **CreateContainerConfigError** | Missing ConfigMap/Secret, invalid reference | `kubectl describe pod`, verify referenced resources exist |
| **Pending (resources)** | No node with sufficient CPU/memory | Scale up nodes, adjust resource requests |
| **Pending (scheduling)** | nodeSelector, affinity, taint mismatch | Check Events section in `kubectl describe pod` |
| **ContainerCreating (delayed)** | Volume mount failure, network plugin issue | Check PVC status, CNI pod status |
| **ErrImagePull** | Cannot connect to image registry | Check network connectivity, ECR endpoints |
| **RunContainerError** | Invalid container config, securityContext issue | `kubectl describe pod`, review securityContext |
| **PostStartHookError** | postStart hook failed | Review hook command, adjust timeout |
| **PreStopHookError** | preStop hook failed | Review hook command, adjust terminationGracePeriodSeconds |
| **FailedScheduling** | Resource shortage, PVC binding pending | Check node resources, PVC status |
| **FailedMount** | Volume mount failed, CSI driver issue | Check CSI driver logs, PV/PVC status |
| **NetworkNotReady** | CNI plugin not ready | Check aws-node pod status, CNI logs |
| **NodeNotReady** | kubelet issue, network disconnection | Check kubelet logs, node status |
| **Evicted** | Node resource pressure (disk, memory) | Clean node resources, adjust resource limits |
| **BackOff** | Retry backoff state | Check previous error logs, resolve root cause |
| **InvalidImageName** | Invalid image name format | Verify image name syntax |

### Essential kubectl Commands Cheatsheet

```bash
# Cluster status
kubectl cluster-info
kubectl get nodes -o wide
kubectl top nodes

# Pod debugging
kubectl get pods -A -o wide
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns> --tail=100 -f
kubectl logs <pod> -n <ns> --previous
kubectl exec -it <pod> -n <ns> -- /bin/sh

# Events
kubectl get events -A --sort-by='.lastTimestamp'
kubectl get events -n <ns> --field-selector type=Warning

# Resource usage
kubectl top pods -A --sort-by=memory
kubectl top pods -A --sort-by=cpu

# Debug containers
kubectl debug -it <pod> --image=busybox --target=<container>
kubectl debug node/<node> -it --image=ubuntu

# Network test
kubectl run test --image=nicolaka/netshoot -it --rm -- /bin/bash

# Force delete
kubectl delete pod <pod> -n <ns> --grace-period=0 --force

# Rollout
kubectl rollout status deployment/<deploy> -n <ns>
kubectl rollout undo deployment/<deploy> -n <ns>
kubectl rollout restart deployment/<deploy> -n <ns>

# Scaling
kubectl scale deployment <deploy> -n <ns> --replicas=3

# ConfigMap/Secret
kubectl get configmap -n <ns> -o yaml
kubectl get secret -n <ns> -o yaml

# Service endpoints
kubectl get endpoints -n <ns>
kubectl describe svc <service> -n <ns>
```

### Tool Recommendations

| Tool | Purpose | Installation/Usage |
|------|---------|-------------------|
| **netshoot** | Network debugging | `kubectl run net --image=nicolaka/netshoot -it --rm` |
| **eks-node-viewer** | Node resource visualization | `go install github.com/awslabs/eks-node-viewer/cmd/eks-node-viewer@latest` |
| **crictl** | Container runtime debugging | On node: `sudo crictl ps`, `sudo crictl logs` |
| **kubeval** | YAML validation | `kubeval deployment.yaml` |
| **stern** | Multi-pod logging | `stern <pod-pattern> -n <namespace>` |
| **k9s** | TUI cluster management | `k9s -n <namespace>` |
| **kubectx/kubens** | Context/namespace switching | `kubectx <context>`, `kubens <namespace>` |

### EKS Log Collector (For AWS Support)

```bash
# Download and run EKS Log Collector
curl -O https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/log-collector-script/linux/eks-log-collector.sh
chmod +x eks-log-collector.sh

# Run log collection
sudo ./eks-log-collector.sh

# Collected logs are saved to /var/log/eks_i-xxxx_$(date +%Y-%m-%d_%H-%M-%S).tar.gz
# Attach to AWS Support case for submission
```

Information collected:
- System information (OS, kernel, memory, CPU)
- kubelet logs and configuration
- containerd logs and configuration
- CNI plugin logs
- Network configuration (iptables, routing)
- Disk usage

---

## 10. Next Steps

### Quiz

To test your understanding of the content covered in this document, try the [EKS Advanced Debugging Quiz](../quizzes/eks/11-eks-advanced-debugging-quiz.md).

### Next Document

To learn how to integrate EKS clusters with on-premises environments, see [EKS Hybrid Nodes](../eks-hybrid-nodes/README.md).

### Additional Learning Resources

- [AWS EKS Official Documentation - Troubleshooting](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)
- [Kubernetes Official Documentation - Debugging](https://kubernetes.io/docs/tasks/debug/)
- [AWS Well-Architected Framework - EKS Lens](https://docs.aws.amazon.com/wellarchitected/latest/eks-lens/welcome.html)
