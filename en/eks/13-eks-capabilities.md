# Amazon EKS Capabilities: Managed Argo CD, kro and ACK

> **Supported Versions**: EKS 1.36–1.37, Argo CD `3.4.6-eks-2` and `3.4.7-eks-1`, kro `0.9.4-eks-1`, ACK `46.186.1-eks-1`, AWS CLI 2.38.3
> **Last Updated**: October 23, 2026

EKS Capabilities run Argo CD, kro (Kube Resource Orchestrator) and ACK (AWS Controllers for Kubernetes) as AWS-operated controllers outside your cluster. The feature became generally available on November 30, 2025. Controller log delivery (Vended Logs) followed in June 2026, and custom `argocd-cm` configuration for Argo CD in August 2026.

The numbers in this chapter were measured in October 2026 on test clusters in ap-northeast-2. The main cluster used private subnets, authenticationMode `API` and two m7g.large nodes (the hub and spoke used for upgrade and multi-cluster tests had one node each). The same scenarios were repeated against self-managed (OSS) controllers installed on the same cluster. Each scenario ran only 1–5 times, so read the numbers as ranges and re-check them in your own environment before making operational decisions. Anything verified only against documentation, not measured, is marked "per the docs". The measurement write-up and raw results are in the [EKS Capabilities blog series](https://blog.atomai.click/eks-capabilities-argocd/) (Korean).

## Table of Contents

1. [Common Model](#common)
2. [Creation and Day-to-Day Operation](#create)
3. [Argo CD Capability](#argocd)
4. [kro Capability](#kro)
5. [ACK Capability](#ack)
6. [Using the Three Together](#together)
7. [Cluster Upgrades and Capability Versions](#upgrade)
8. [Multi-Cluster and Blue/Green Replacement](#multicluster)
9. [Comparison with Self-Managed and When to Choose](#compare)
10. [Pricing](#pricing)
11. [Verification Scope and References](#refs)

---

<span id="common"></span>

## 1. Common Model

| Item | Behavior |
|---|---|
| Controller location | AWS-owned infrastructure. No Pods on worker nodes (measured zero for all three) |
| Cluster access | The capability role (trusted principal `capabilities.eks.amazonaws.com`) calls the API server through an EKS access entry. Works even with a private-only API endpoint |
| Count | One per capability type per cluster |
| Version | Chosen and rolled by AWS. The create/update APIs have no version argument, so you cannot pin or select one |
| Deletion | Only `--delete-propagation-policy RETAIN`. CRDs, CRs, deployed resources and the access entry remain |
| Logs | Not available through `kubectl logs`. Delivered with CloudWatch Vended Logs to CloudWatch Logs, S3 or Amazon Data Firehose (see [EKS Monitoring and Logging](./06-eks-monitoring-logging.md)) |
| Pricing | Hourly capability charge plus a charge per managed object (Applications for Argo CD, instances for kro, resources for ACK) |

The common trait across all three is narrow default permissions. With only the automatically created access entry policies, Argo CD cannot deploy, kro cannot start the RGD controller, and ACK cannot create AWS resources without per-service IAM permissions. By contrast, the OSS Helm chart defaults for both Argo CD and kro grant the controller `apiGroups: ["*"], resources: ["*"], verbs: ["*"]`.

<span id="create"></span>

## 2. Creation and Day-to-Day Operation

### Capability role and create command

Trust `capabilities.eks.amazonaws.com` in the capability role and allow `sts:AssumeRole` and `sts:TagSession`. kro never calls AWS APIs, so it needs no permission policy. Argo CD against public Git repositories also worked without one.

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| Capability | `CREATING` → `ACTIVE` | Delete | Auto-created access entry policies | CRDs installed |
|---|---|---|---|---|
| Argo CD | 349 s (385 s for a new capability with `endpointPrefix` on another cluster, 338 s re-creating with the same prefix) | 100.5 s | `AmazonEKSArgoCDClusterPolicy` (cluster), `AmazonEKSArgoCDPolicy` (`argocd` namespace) | `applications`, `applicationsets`, `appprojects` |
| kro | 70.1–70.4 s | 46.9 s | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`, `graphrevisions.internal.kro.run` |
| ACK | 385.7 s (77 s when CRDs already exist) | 67.3 s | `AmazonEKSACKPolicy` | 267 (66 service API groups plus `IAMRoleSelector` in `services.k8s.aws`) |

### Operational notes

- **Keep the AWS CLI current.** CLI 2.35.11 knew only `namespace`, `awsIdc`, `rbacRoleMappings` and `networkAccess` under `argoCd` (no `endpointPrefix`), and rejected ACK settings with `Unknown parameter in configuration: "ack", must be one of: argoCd`; 2.38.3 accepted both. Check the CLI version before concluding something is unsupported.
- **Apply capability changes one at a time.** Each added log delivery source put the capability in `UPDATING` for about 6.6–7 seconds, and the next change failed with `ConflictException: ... currently in UPDATING state`. Wait for `ACTIVE` between changes.
- **Enable log delivery from day one.** With the controller outside the cluster, logs are the only view into its internal behavior later (CloudTrail still shows AWS API call times). Logs are structured JSON; Argo CD records per-phase timings for each reconcile (`compare_app_state_ms`, `patch_ms` and so on).
- **RETAIN leaves "everything except the controller".** While a capability is deleted, CR changes are not reconciled (verified by changing kro instance replicas). An OSS controller using the same CRDs picks up the pending changes once installed.

<span id="argocd"></span>

## 3. Argo CD Capability

### Registering the local cluster and deploy permissions

Managed Argo CD does not add even its own cluster as a destination. Create a cluster Secret using the EKS ARN rather than an API URL.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: in-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
stringData:
  name: in-cluster
  server: arn:aws:eks:ap-northeast-2:111122223333:cluster/example-cluster
  project: default
```

The auto-created access entry alone does not allow syncing, because Argo CD lists every resource type in the cluster to build its cache, not only the resources it deploys.

| Capability role cluster permissions | Result |
|---|---|
| Auto-created access entry only | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| + `AmazonEKSEditPolicy` | Still failing after 141 s; list denied on `securitygrouppolicies.vpcresources.k8s.aws` |
| + `AmazonEKSAdminViewPolicy` | Synced and Healthy in 11.6 s |
| Deploying CRs of kro/ACK APIs (a NginxApp instance, an ACK Queue) | `nginxapps.platform.example.com is forbidden`. Adding a Kubernetes group to the access entry and binding a ClusterRole for that API group fixed it in 16 s |

The AWS docs use `AmazonEKSClusterAdminPolicy` (equivalent to `system:masters`) to get started, and describe a production least-privilege setup with cluster-wide read access plus namespace-scoped `AmazonEKSEditPolicy`. In testing, cluster-scoped Edit plus AdminView, with a ClusterRole per platform CRD, worked; that is broader than the documented production setup. To narrow further, `resource.respectRBAC`, which the managed capability supports, limits watching to permitted resources (not tested).

### Git polling and webhooks

| Method | Commit → Synced (3 runs) |
|---|---|
| Managed, default polling (6 minutes per the docs) | 341.8 s, 619.3 s, 697.1 s |
| Managed, GitHub webhook | 7.0–7.3 s |
| Self-managed 3.4.6, default polling (120 s + 60 s jitter) | 115.7–171.4 s |

The managed polling interval (`timeout.reconciliation`) is not a configurable key and the jitter is not published. If deployment delay must not swing by minutes, webhooks are effectively required. Put a random string in `webhook.github.secret` of the capability-created `argocd-webhook-creds-secret` and register `<server URL>/api/webhook` with the same secret in the Git repository. The server URL is an AWS-hosted public address, so no separate webhook endpoint has to be exposed. Restricting public access with a VPC endpoint would likely also block GitHub webhooks (not tested).

Drift self-heal matched: 2.08–2.32 s managed, 1.05–3.06 s self-managed. However, repeated self-heals on the same app without a new commit hit the upstream backoff (2 s, ×3 each time, capped at 300 s) and recovery slowed to almost 5 minutes (measured 251–254 s). Self-managed tunes this with the `--self-heal-backoff-*` flags. Managed exposes only three `argocd-cmd-params-cm` keys (`hydrator.enabled`, `application.namespaces`, `applicationsetcontroller.namespaces`), and the AWS docs direct self-heal timing requests to AWS Support. Trigger a manual sync when it is urgent.

### Settings, health checks and CLI

Create the `argocd-cm` ConfigMap in the capability namespace with the label `app.kubernetes.io/part-of: argocd`. Unsupported keys are ignored silently.

| Item | Result |
|---|---|
| `ui.bannercontent` | Shown in the UI |
| Lua health check for a kro instance | Applied; script edits took effect in about 12 s |
| Lua `string.upper()`, `os.time()` | `attempt to index a non-table object(nil)`, health `Unknown`. Same as the upstream default (`useOpenLibs` off), but managed cannot turn it on |
| `argocd login --username admin` or `--sso` | Both fail |
| Token from the UI + `ARGOCD_SERVER`, `ARGOCD_AUTH_TOKEN`, `ARGOCD_OPTS=--grpc-web` | `app list/get/sync`, `cluster list`, `proj list` work |
| PreSync hook sleeping 150 s | `Succeeded` in 161 s despite the documented 120 s sync timeout; which phase the limit applies to is unknown |

Argo CD 3.x does not store resource health in the Application status by default, so an empty `.status.resources[].health` from `kubectl get application -o json` is normal. Check health with `argocd app get` or the UI.

Per the docs, Config Management Plugins (CMP), the Notifications controller, custom SSO, UI extensions and `argocd admin`, among others, are not supported. If you send deployment notifications with Notifications or generate manifests through a CMP, you cannot move to the managed capability as is.

### Sign-in: IAM Identity Center only

Authentication is IAM Identity Center only, with no local users. `rbacRoleMappings` in the capability configuration maps Identity Center users (`SSO_USER`) or groups (`SSO_GROUP`) to ADMIN, EDITOR or VIEWER. Okta or Microsoft Entra ID do not connect to Argo CD directly; set the external IdP as the Identity Center identity source, using SAML for sign-in and SCIM for user and group sync (per the docs).

- An Identity Center instance has a single identity source. If the organization instance already uses another IdP, giving only Argo CD a different IdP requires an account instance (not tested).
- The linked Identity Center instance cannot be changed after creation (per the EKS console help). Mappings are stored as user and group IDs; switching the identity source to Active Directory deletes users and groups, so the mappings must be rewritten.
- A capability accepts up to 1,000 mapped identities, so map groups rather than users. There are only three global roles, so fine-grained `argocd-rbac-cm` policies must move to AppProject roles.

<span id="kro"></span>

## 4. kro Capability

The AWS docs state that managed kro uses the same upstream controller and is fully compatible. In testing, the reported version `0.9.4-eks-1` matched the latest OSS release, and the same RGDs and CEL expressions behaved identically. The differences are in permissions and operations. For kro concepts and examples, see the [kro chapter](../platform-engineering/03-kro.md).

### The default permissions do not let the controller start

`AmazonEKSKROPolicy` covers only the `kro.run` group and CRDs. It grants neither watch on the API generated from the RGD schema group (for example `platform.example.com`) nor permission to create the child Deployments and Services. The failure shows up as a cache sync timeout, not as forbidden.

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

The eksctl guide attaches `AmazonEKSClusterAdminPolicy` to get started. A least-privilege alternative is to add a Kubernetes group to the access entry and bind a ClusterRole per RGD.

```bash
aws eks update-access-entry --cluster-name "$CLUSTER_NAME" \
  --principal-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --kubernetes-groups kro-workloads
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kro-workloads-reviewed-nginxapps
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kro:controller:reviewed-nginxapps
subjects:
  - kind: Group
    name: kro-workloads
    apiGroup: rbac.authorization.k8s.io
```

When permissions were granted after the RGD, it became `Active` only 228 s later (presumably the controller retry interval; not confirmed in logs). A second RGD whose ClusterRole was applied first became `Active` immediately. Keep the RGD and its ClusterRole in the same Git path and apply RBAC first with sync waves (sync waves not tested). OSS `rbac.mode: aggregation` also merges only labeled ClusterRoles into controller permissions, so it needs similar work (per the chart, not tested).

### Lifecycle performance and migration

| Phase (5 runs each) | Managed | OSS 0.9.4 |
|---|---|---|
| Create → `ACTIVE` | 2.49–3.73 s | 2.43–3.44 s |
| Spec change → Deployment updated | 0.50–0.52 s (one 51.6 s outlier, cause unknown) | 0.49–0.56 s |
| Delete → Deployment and Service gone | 1.02–3.02 s | 1.01–4.38 s |

Switching managed → OSS → managed kept two RGDs and four instances intact (one controller removed before the other was installed). For zero-downtime migration, follow the AWS procedure for moving the leader-election lease (not tested), but note that its chart path and value key are outdated: the current chart is `oci://registry.k8s.io/kro/charts/kro`, and the 0.9.4 key is `config.leaderElectionNamespace`.

### Pitfall: kro takes over existing CRs with the same name

If a CR with the same name as a child resource already exists in the namespace, kro does not refuse; it overwrites it with server-side apply. In testing, an existing ACK Table CR received `kro.run/owned=true` and a changed `spec.tableName`; ACK created a new table and the original table was left unmanaged. Deleting the instance deleted the taken-over CR as well. OSS 0.9.4 reproduced the same behavior, so this is upstream.

- Add an RGD-specific suffix to child resource names (`${schema.metadata.name + "-os"}`).
- Separate namespaces managed by kro from namespaces where people create CRs directly.
- Set `services.k8s.aws/deletion-policy: retain` on ACK resources that hold data. It does not prevent a rename from moving to a new resource, so name separation is the real fix (retain combined with this case was not tested).
- In multi-tenant clusters, do not let instances choose `ingressClassName` and host names freely; fix them in the RGD or derive them from the instance name.

<span id="ack"></span>

## 5. ACK Capability

Managed ACK bundles every service controller that is GA upstream in one capability; preview controllers are added automatically when they reach GA (per the docs). For the ACK resource model, adoption and retention, see the [ACK chapter](../platform-engineering/02-ack.md).

### Per-team IAM with IAMRoleSelector

Give the capability role only permission to assume team roles, and map namespaces to roles with a cluster-scoped `IAMRoleSelector`. Each team role trusts the capability role and allows `sts:AssumeRole` and `sts:TagSession`.

```json
{"Effect": "Allow", "Action": ["sts:AssumeRole", "sts:TagSession"],
 "Resource": ["arn:aws:iam::111122223333:role/ack-team-a",
              "arn:aws:iam::111122223333:role/ack-team-b"]}
```

```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: IAMRoleSelector
metadata:
  name: team-b
spec:
  arn: arn:aws:iam::111122223333:role/ack-team-b
  namespaceSelector:
    names: [team-b]
```

An S3 Bucket created in team-b, whose role allows only SQS, failed with `AccessDenied`, and the message named the role actually used (`assumed-role/ack-team-b/...`). The CR condition `ACK.IAMRoleSelected=True` also shows that a selector matched. Details confirmed:

- The S3 Bucket controller calls `s3:ListAllMyBuckets` first. Even when bucket resources are narrowed by name pattern, this permission (resource `*`) appears to be needed separately (not tested without it).
- Namespaces without a matching selector use the capability role (per the docs). Without service permissions on the capability role, the default becomes deny.
- For the same separation with OSS controllers, set both `featureGates.IAMRoleSelector=true` and `enableCARM=false`. With the chart default `enableCARM: true`, the controller crash-loops with `cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true`.

### Resource creation, tags and drift

| Resource | Managed (3 runs) | OSS (2 runs) |
|---|---|---|
| SQS Queue | 1.04–1.06 s | 1.10–1.16 s |
| S3 Bucket | 3.10–3.14 s | 3.20–3.32 s |
| DynamoDB Table | 11.28–11.53 s | 10.15–11.54 s |

Only the first creation right after the capability was first created was slower: Queue 7.3 s, Bucket 10.9 s, Table 16.5 s.

Managed ACK adds five tags to AWS resources: `eks:controller-version`, `eks:kubernetes-namespace`, `eks:kubernetes-resource-name`, `eks:kubernetes-api-group` and `eks:eks-capability-arn`. Every AWS API call carries the session tags `eks:eks-capability-arn`, `eks:kubernetes-namespace` and `eks:kubernetes-api-group`. OSS adds two tags, `services.k8s.aws/controller-version` and `services.k8s.aws/namespace`. Migrating from OSS changes the tag prefix, so update cost allocation tags and tag-based IAM conditions at the same time.

ACK does not watch AWS-side changes in real time. An SQS `VisibilityTimeout` changed outside ACK (with the CLI) was not reverted periodically within 25 minutes by either managed (2 runs) or OSS (1 run). The two reverts seen on managed came 86 s after the capability went through `UPDATING` for a log configuration change, and right after the capability was re-created (call times from CloudTrail). A controller restart appears to be the trigger, but this was not confirmed in logs. The OSS default resync is 10 hours (`reconcile.defaultResyncPeriod: 36000`) and is tunable; the managed interval is not published and cannot be changed. If fast recovery matters, prevent out-of-band changes with SCPs or IAM conditions, for example allowing changes to resources tagged `aws:ResourceTag/eks:eks-capability-arn` only from calls with a matching `aws:PrincipalTag/eks:eks-capability-arn` (not tested).

### Managed differences and migration

- There is no `FieldExport` CRD. To export status values into a ConfigMap or Secret, use another approach such as kro writing status into a ConfigMap.
- Disabling services with `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'` took effect in 12.5 s on CLI 2.38.3, but the already-installed CRDs for that service were still present after 350 s. Specify unused services at creation time instead (creation-time setting not tested).
- Controller versions were one step behind the latest OSS releases (s3 1.12.2 vs 1.13.1, sqs 1.7.1 vs 1.8.2).
- Adoption (`services.k8s.aws/adoption-policy: adopt-or-create`) and retain annotations work on the managed capability: adoption took 4.7 s, and a Queue deleted with retain remained in AWS (measured on managed). After the capability was deleted, an OSS controller adopted the 12 remaining CRs as they were.

<span id="together"></span>

## 6. Using the Three Together

The natural split is: Argo CD syncs manifests from Git, kro composes several resources into one API, and ACK creates the AWS resources among them. The tested `OrderService` RGD created an ACK Queue and Table, copied their status values (queue URL, table ARN) into a ConfigMap and started a Deployment.

| Combination | Result | Extra configuration needed |
|---|---|---|
| Argo CD → ACK Queue | Queue CR from Git Synced in 6.5 s | RBAC for `queues.sqs.services.k8s.aws` on the Argo CD capability role |
| kro → ACK Queue and Table + ConfigMap + Deployment | Instance `ACTIVE` in 13.2–34.3 s (mostly DynamoDB table creation) | RBAC for ACK resources on the kro capability role; IAMRoleSelector on the ACK side |

ACK CRDs are not covered by the default EKS access policies (such as `AmazonEKSEditPolicy`), so whichever component creates ACK resources, Argo CD or kro, needs permissions for those API groups. The two measurements were taken separately; the full three-step chain was not run end to end.

<span id="upgrade"></span>

## 7. Cluster Upgrades and Capability Versions

### Behavior during an in-place upgrade

A cluster with all three capabilities was upgraded in place from 1.36 to 1.37. The control plane upgrade took about 7 minutes, and all three capabilities stayed `ACTIVE` with unchanged version, health and `modifiedAt`.

| Phase | Argo CD self-heal | kro propagation | ACK Queue sync |
|---|---|---|---|
| Before (3 runs) | 2.1–14.6 s | 1.02–1.04 s | 1.49–3.53 s |
| During (4 runs) | 2.1 s, 6.1 s, 112.9 s, 254.5 s | 1.02–1.07 s | 1.52–1.58 s |
| After (5 runs) | 2.3 s, then 251–252 s | 1.01–1.15 s | 1.47–1.57 s |

For kro and ACK, one of the four "during" runs was taken right after the upgrade completed. The self-heal delay during the upgrade reproduced identically after the upgrade, so it came from the self-heal backoff described above, not from the upgrade. kro and ACK were not measured during the roughly 3 minutes when the API server version alternated between 1.36.4 and 1.37.0. Node groups were not upgraded.

The in-place upgrade required no capability-specific steps. Self-managed controllers have to be checked for support of the new Kubernetes version and possibly upgraded first; the managed model leaves that compatibility check to AWS. Note that none of the EKS upgrade insights checks covered capabilities.

### You cannot choose the version

`create-capability` and `update-capability` have no version argument, and the AWS docs only say "automatic updates and security patches". No update schedule, advance notice, maintenance window, per-version release notes or rollback path for capability versions could be found in the documentation. The [cluster version rollback](./08-eks-upgrades.md) added in July 2026 rolls back the Kubernetes minor version, and the rollback documentation does not cover capabilities. Since capabilities have no version argument, do not treat it as a way to roll back a capability version (inference). In testing, an Argo CD capability created on October 21 reported `3.4.6-eks-2`, and one created a day later on another cluster reported `3.4.7-eks-1`. Controller versions can change independently of cluster upgrades.

Prepare for a buggy release as follows.

| Preparation | How | Basis |
|---|---|---|
| Record version changes | Poll `capability.version` from `describe-capability` and correlate it with incidents | Measured (field confirmed) |
| Validation cluster | Run production RGDs, Applications and ACK CRs on a cluster with the same capabilities first. You cannot control rollout order, so it is not guaranteed to update before production | Inference |
| Pin behavior in Git | Keep health checks (`resource.customizations`), sync options and RBAC in Git so re-creation or migration reproduces the same behavior | Measured (settings applied) |
| AWS Support | No user-side rollback exists, so open a case. The AWS docs route self-heal timing adjustments to Support | Inference (self-heal timing per the docs) |
| Temporary fallback to self-managed | Deleting a capability with RETAIN keeps CRDs and resources, and an OSS controller on the same CRDs takes over (measured for kro, ACK and Argo CD). Argo CD required changing the cluster Secret `server` from the EKS ARN to an API URL (`https://kubernetes.default.svc` locally), and remote or private spokes registered by ARN need their own network path and auth under OSS. Returning to managed requires re-creation (about 6 minutes for Argo CD) | Measured |
| Per-service ACK rollback | Add only the affected service to `disabledServices` and install or scale up its self-managed controller. The OSS controller needs its own IAM wiring, plus `featureGates.IAMRoleSelector=true` and `enableCARM=false` when using IAMRoleSelector. Running the OSS chart over capability-installed CRDs was not tested. Already-installed CRDs remain (measured) | Per the docs |

If you clearly need pinned versions, the AWS docs themselves point to self-managed ("require specific Kubernetes resource API versions, custom controller builds").

<span id="multicluster"></span>

## 8. Multi-Cluster and Blue/Green Replacement

### Argo CD hub and a private spoke

The Argo CD capability on a hub cluster registered a spoke in the same account and VPC whose API endpoint was private-only, with no network configuration (endpoints, security groups, routes). A workstation in another VPC could not reach the spoke, so the connection apparently uses an AWS-provided path. The spoke needs an access entry for the hub's capability role, created manually.

| Spoke access entry permissions | Result |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | Connection and auth succeeded, but `CreateNamespace=true` failed with `namespaces is forbidden`; five automatic retries (about 303 s) were exhausted |
| + `AmazonEKSArgoCDClusterPolicy`, then manual sync | Synced and Healthy in 11.1 s |

- Cluster Secrets accept only EKS ARNs, so non-EKS clusters cannot be destinations (per the docs).
- Application charges count Applications per destination cluster, so a hub and per-cluster placement cost the same; only the capability charge grows with the number of Argo CD instances. The hub's capability role, however, holds write access to every spoke, so consider restricting AppProject destinations or splitting capabilities by team.
- Clusters in other accounts only need an access entry for the hub capability role, per the docs (not tested). Managed limits are 100 remote clusters and 3,000 Applications.

### Where to place kro and ACK

kro and ACK capabilities manage only their own cluster. For a hub Argo CD to deploy RGD instances or ACK CRs to a spoke, the spoke needs kro or ACK too (managed or OSS).

| Layout | Fits when | Concerns |
|---|---|---|
| kro on every cluster, RGDs rolled out with an ApplicationSet | App teams use the same API on each cluster | Capability charges and RBAC work scale with cluster count; the docs do not guarantee identical kro versions across clusters (not tested) |
| kro only on the hub, RGDs create ACK resources and Argo CD Applications for spokes | Platform abstractions defined in one place | Permissions and blast radius concentrate on the hub; spoke app teams cannot use the kro API directly (not tested) |
| Central ACK (hub) | Platform-owned resources such as databases, IAM, VPCs | The hub capability role holds permissions for all accounts and resources |
| Distributed ACK (per cluster) | Queues and buckets declared next to workloads | IAMRoleSelector configuration scales with cluster count |
| Hybrid ACK | Administrator-scope resources on the hub, workload-scope resources on spokes | Needs scope rules so one resource is never declared in two places |

In every layout, set scope rules so that no two clusters declare the same AWS resource at the same time.

### Blue/green replacement

- **Argo CD**: The capability belongs to its cluster, so replacing the cluster that hosts Argo CD means re-creating the capability. The default address `argocd-<ID>-<account ID>.eks-capabilities.<region>.amazonaws.com` differs per cluster, so the UI and webhook URLs change. With `endpointPrefix` set at creation, deleting and re-creating with the same prefix kept the address (tested on the same cluster only). The address contains nothing cluster-specific, so it should also work after moving to another cluster. If a prefix is unique within an account and Region (not tested), old and new clusters cannot hold it at once; replacement becomes delete-and-recreate, and UI, webhooks and syncing stop meanwhile (100 s plus 338 s measured). If that pause is unacceptable, bring up a new capability with a new prefix first and change the Git webhook URL; disable the old auto-sync or delete its Applications non-cascading before enabling the new one, and create the new capability role's access entries on target clusters in advance (not tested). The prefix cannot be changed after creation. Place Argo CD on a dedicated hub rather than on frequently replaced workload clusters.
- **kro**: ClusterRoles and bindings move through Git, but adding a Kubernetes group to the access entry is an EKS API call. Put it in the IaC that creates clusters (eksctl, Terraform and so on).
- **ACK**: One possible sequence is deleting the old cluster's CRs with `deletion-policy: retain`, then adopting the same resources on the new cluster with `adoption-policy: adopt-or-create` (each step measured; the full cross-cluster sequence was not tested). If an SCP blocks changes based on the `eks:eks-capability-arn` tag, the new capability has a different ARN and adoption may be blocked; relax the condition during the switch or condition on environment or team tags instead.

<span id="compare"></span>

## 9. Comparison with Self-Managed and When to Choose

| Item | Managed capability | Self-managed (OSS) |
|---|---|---|
| Install time | Argo CD 349 s, kro 70 s, ACK 386 s | Argo CD 43.4 s, kro 15.6 s, three ACK controllers 46 s |
| Node resources | None | Argo CD 7 Pods (339–624Mi memory), kro 1 Pod (requests 256m, 128Mi), ACK 3 Pods (each requests 50m, 64Mi) |
| Version | Chosen by AWS, cannot pin | Your choice (Argo CD v3.5.5 and ACK s3 1.13.1 were latest at test time) |
| Default permissions | Narrow; grant deploy, child-resource and IAM permissions yourself | Argo CD and kro chart defaults are `*/*/*` |
| Performance | kro, ACK and Argo CD self-heal match OSS; Argo CD default polling is slower | Baseline (Argo CD 3.4.6 and kro 0.9.4 measured at the same versions; ACK OSS ran one version newer) |
| SSO | Identity Center only, two configuration fields | Dex, OIDC and others, configured yourself |
| Remote clusters | EKS ARN + access entry; private clusters without network setup | API URL, auth and network path per cluster |
| Missing features | Argo CD Notifications, CMP, `argocd admin`, Lua standard libraries; ACK FieldExport | None |
| Not directly tunable | Argo CD polling, ACK resync interval, controller flags and resource limits; Argo CD self-heal backoff only through AWS Support | All tunable |
| Logs | Vended Logs | `kubectl logs`, your own collection |

Managed fits when:

- You are building a hub that deploys to multiple EKS clusters, especially private clusters or clusters in other accounts
- Your AWS sign-in is already centralized in Identity Center and you do not want to operate Argo CD SSO yourself
- You manage several AWS services from Kubernetes, running one ACK controller per service is a burden, and you need per-team IAM separation
- You want platform controller permissions narrow by default and explicit in access entries and RBAC

Stay self-managed when:

- You depend on Notifications, CMP, FieldExport or Lua standard libraries
- Non-EKS clusters are among your deployment destinations
- Only Argo CD must use an IdP different from the organization's Identity Center and an account instance is not an option
- You must control controller versions, upgrade timing and polling or resync intervals yourself

A good time to evaluate is before you grow past one cluster: the hub location, Identity Center instance and `endpointPrefix` are fixed or awkward to change after creation. Another is when a self-managed Argo CD needs an HA rebuild or a major upgrade. The AWS migration procedure scales the existing controller to zero, moves Applications and Secrets, and changes `destination.server` to the ARN; syncing stops in the meantime (not tested).

<span id="pricing"></span>

## 10. Pricing

Prices are for Seoul (ap-northeast-2), queried with the AWS Pricing API on October 21, 2026, using 730 hours per month.

| Capability | Capability charge | Per-object charge | Example (per month) |
|---|---|---|---|
| Argo CD | $0.034799 per hour (about $25.4/month) | $0.001726 per Application-hour (counted per destination cluster) | 9 apps about $36.7, 100 apps about $151 |
| kro | $0.006038 per hour (about $4.4/month) | $0.000061 per instance-hour | 100 instances about $8.9 |
| ACK | $0.006038 per hour (about $4.4/month) | $0.000061 per resource-hour | 200 resources about $13.3 |

For comparison, apportioning m7g.large cost (Seoul $0.1003 per hour) to the default self-managed installs gives about $5.6 for Argo CD (624Mi memory), $9.4 for kro (256m CPU request) and $5.5 for three ACK controllers (150m CPU request). HA setups and more apps or services raise the OSS side as well. Managed Argo CD becomes more expensive as the app count grows; for kro and ACK the difference is small, so operational burden and feature gaps decide.

<span id="refs"></span>

## 11. Verification Scope and References

Measurements used a single account in ap-northeast-2: one EKS 1.36.4 cluster, plus two clusters for the upgrade and multi-cluster tests (hub 1.36 → 1.37, private spoke 1.37). Scenarios ran 1–5 times, with at most 9 Argo CD apps, 6 kro instances and about 20 ACK resources. ACK was tested only with S3, SQS and DynamoDB. The following were not tested and rely on documentation: Okta or Entra ID integration and Identity Center account instances, private access through a VPC endpoint, registering clusters in other accounts or VPCs, Notifications and CMP, cross-account ACK, zero-downtime migration with managed and OSS running simultaneously, and the full cross-cluster ACK retain-then-adopt sequence. Test clusters and AWS resources were deleted after measurement.

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [EKS Capabilities considerations](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Capability Kubernetes resources](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Argo CD considerations](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [Comparing EKS Capability for Argo CD to self-managed Argo CD](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [Register target clusters](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [Configure Argo CD settings](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [Configure kro permissions](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [Comparing EKS Capability for kro to self-managed kro](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [Configure ACK permissions](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [Comparing EKS Capability for ACK to self-managed ACK](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [Access EKS Capabilities controller logs](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [Roll back a cluster to a previous Kubernetes version](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Amazon EKS pricing](https://aws.amazon.com/eks/pricing/)
- Measurement blog (Korean): [Managed Argo CD](https://blog.atomai.click/eks-capabilities-argocd/), [Managed kro](https://blog.atomai.click/eks-capabilities-kro/), [Managed ACK](https://blog.atomai.click/eks-capabilities-ack/)
- Test manifests: [Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[EKS Capabilities Quiz](../quizzes/eks/13-eks-capabilities-quiz.md)
