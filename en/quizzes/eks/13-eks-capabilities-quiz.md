# Amazon EKS Capabilities Quiz

> **Last Updated**: October 23, 2026

Use the [source chapter](../../eks/13-eks-capabilities.md) to separate measured results from documentation-only statements.

1. Where do the Argo CD, kro and ACK controllers of EKS Capabilities run?

   - A) As a DaemonSet on each worker node
   - B) As Deployments in the `kube-system` namespace
   - C) On AWS-owned infrastructure, with no Pods on worker nodes
   - D) On a Fargate profile created automatically in your VPC

<details>
<summary>Show Answer</summary>

**Answer: C) On AWS-owned infrastructure, with no Pods on worker nodes**

All three capabilities created zero Pods on worker nodes. The controllers call the API server through the capability role and an EKS access entry, so they work even with a private-only API endpoint. For the same reason, logs are not available through `kubectl logs`; use Vended Logs.

</details>

---

2. What is needed to sync an Application to the local cluster right after creating managed Argo CD?

   - A) Nothing; the local cluster registers automatically
   - B) A cluster Secret using the EKS ARN, plus deploy permissions on the capability role's access entry
   - C) Running `argocd cluster add`
   - D) `system:masters` is always required

<details>
<summary>Show Answer</summary>

**Answer: B) A cluster Secret using the EKS ARN, plus deploy permissions on the capability role's access entry**

The auto-created access entry alone failed with `podtemplates is forbidden`. Argo CD lists every resource type to build its cache, so `AmazonEKSEditPolicy` alone was not enough; adding `AmazonEKSAdminViewPolicy` made syncing work. cluster-admin was not needed.

</details>

---

3. How do you remove the minutes-long delay from commit to Synced on managed Argo CD?

   - A) Lower `timeout.reconciliation` in `argocd-cm` to 30 seconds
   - B) Re-create the capability every time
   - C) Register a GitHub webhook at `/api/webhook` on the capability server URL
   - D) Add more nodes

<details>
<summary>Show Answer</summary>

**Answer: C) Register a GitHub webhook at `/api/webhook` on the capability server URL**

Default polling measured 342–697 seconds, and the polling interval is not a configurable key on the managed capability. With a webhook, syncs took 7.0–7.3 seconds. The server URL is AWS-hosted, so no separate public endpoint is needed.

</details>

---

4. After applying an RGD to managed kro you see `ControllerReady=False` with "cache sync timeout". What is the most likely cause?

   - A) A controller outage on the AWS side
   - B) `AmazonEKSKROPolicy` lacks permissions for the RGD-generated API and its child resources
   - C) A CEL syntax error in the RGD
   - D) Node memory pressure

<details>
<summary>Show Answer</summary>

**Answer: B) `AmazonEKSKROPolicy` lacks permissions for the RGD-generated API and its child resources**

The default policy covers only the `kro.run` group and CRDs. Because the message is not "forbidden", it is easy to mistake for a controller fault. Add a Kubernetes group to the access entry, bind a ClusterRole per RGD, and apply it before the RGD; doing so avoided the wait (228 seconds measured, presumably the controller retry interval).

</details>

---

5. In testing, what happened when an ACK Table CR already existed with the same name as a kro instance's child resource?

   - A) kro refused to create the instance
   - B) kro took over the existing CR and changed `spec.tableName`, leaving the original table unmanaged
   - C) It happens only on managed kro and does not reproduce on OSS
   - D) ACK merged the two CRs automatically

<details>
<summary>Show Answer</summary>

**Answer: B) kro took over the existing CR and changed `spec.tableName`, leaving the original table unmanaged**

kro overwrote the CR with server-side apply and labeled it `kro.run/owned=true`. Deleting the instance deleted the taken-over CR too. OSS 0.9.4 behaved the same, so this is upstream behavior. Mitigate it with RGD-specific name suffixes and separate namespaces.

</details>

---

6. How do you give teams different IAM permissions with managed ACK?

   - A) Attach IRSA to each service controller's ServiceAccount
   - B) Give the capability role only AssumeRole permission and map namespaces to team roles with `IAMRoleSelector`
   - C) Enable CARM and set the account with a namespace annotation
   - D) Per-team separation is impossible on the managed capability

<details>
<summary>Show Answer</summary>

**Answer: B) Give the capability role only AssumeRole permission and map namespaces to team roles with `IAMRoleSelector`**

A Bucket in team-b, whose role allowed only SQS, failed with `AccessDenied`, and the message named the role used. The same setup on OSS controllers needs both `featureGates.IAMRoleSelector=true` and `enableCARM=false`; leaving CARM on causes CrashLoopBackOff.

</details>

---

7. What did testing show about an SQS attribute changed outside ACK (with the CLI)?

   - A) Managed ACK always reverts it within a minute
   - B) Neither managed nor OSS reverted it periodically within 25 minutes; managed reverts were seen only at what appear to be controller restarts
   - C) OSS reverts it immediately via real-time events
   - D) The managed resync interval is set with `disabledServices`

<details>
<summary>Show Answer</summary>

**Answer: B) Neither managed nor OSS reverted it periodically within 25 minutes; managed reverts were seen only at what appear to be controller restarts**

ACK does not watch AWS-side changes in real time. The OSS default resync is 10 hours and is tunable; the managed interval is unpublished and fixed. If fast recovery matters, block out-of-band changes with SCPs or IAM conditions.

</details>

---

8. Which statement about managed capability controller versions is correct?

   - A) You can pin one with `create-capability --version`
   - B) Cluster version rollback also rolls back the capability version
   - C) AWS chooses and rolls the version, which can change independently of cluster upgrades; read it from `version` in `describe-capability`
   - D) It changes only when you upgrade the cluster's Kubernetes version

<details>
<summary>Show Answer</summary>

**Answer: C) AWS chooses and rolls the version, which can change independently of cluster upgrades; read it from `version` in `describe-capability`**

The create and update APIs have no version argument, and Argo CD capabilities created a day apart reported `3.4.6-eks-2` and `3.4.7-eks-1`. Record version changes, keep a validation cluster, and be ready for a RETAIN-based temporary fallback to self-managed. If pinned versions are a hard requirement, choose self-managed.

</details>

---

9. What did a private-only spoke cluster need so that the hub's Argo CD capability could deploy an app with `CreateNamespace=true`?

   - A) A Transit Gateway and inbound security group rules
   - B) An access entry for the hub capability role with Edit, AdminView and `AmazonEKSArgoCDClusterPolicy`
   - C) Its own Argo CD capability
   - D) A public API endpoint

<details>
<summary>Show Answer</summary>

**Answer: B) An access entry for the hub capability role with Edit, AdminView and `AmazonEKSArgoCDClusterPolicy`**

Connection and authentication succeeded with no network setup, but Edit and AdminView alone failed with `namespaces is forbidden`. The hub gets this policy automatically; remote clusters need it attached manually. After automatic retries were exhausted, a manual sync was required.

</details>

---

10. In which case is self-managed a better fit than the managed capability?

   - A) Building a hub that deploys to several private EKS clusters
   - B) The organization's sign-in is already centralized in Identity Center
   - C) You depend on Argo CD Notifications or CMP or on ACK FieldExport, and also deploy to non-EKS clusters
   - D) You manage several AWS services but running per-service controllers is a burden

<details>
<summary>Show Answer</summary>

**Answer: C) You depend on Argo CD Notifications or CMP or on ACK FieldExport, and also deploy to non-EKS clusters**

The managed capability lacks Notifications, CMP, `argocd admin`, Lua standard libraries and FieldExport, and cluster Secrets accept only EKS ARNs. The other options are cases where the managed capability fits well.

</details>
