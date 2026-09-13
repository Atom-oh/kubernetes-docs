# Crossplane Quiz

[Crossplane](../../platform-engineering/07-crossplane.md)

The original eight topics have been reviewed against Crossplane 2.4.

## 1. What does a Composition provide?

<details>
<summary>Show answer</summary>

A Function pipeline maps XR inputs to desired resources. It does not make several AWS operations atomic or guarantee that they are ready.

</details>

## 2. How do v2 XRs differ from legacy Claims?

<details>
<summary>Show answer</summary>

XRD v2 defaults to Namespaced and users can create XRs directly. Legacy v1 LegacyCluster XRDs retain cluster XRs and namespaced Claims. Not all current XRs/MRs are cluster-scoped.

</details>

## 3. Does selecting IRSA or Pod Identity complete least privilege?

<details>
<summary>Show answer</summary>

No. Configure ServiceAccounts, OIDC audience/subject or associations and role policies. Also constrain runtime ownership, ProviderConfig access and AssumeRole boundaries.

</details>

## 4. What primarily differs between Terraform and Crossplane?

<details>
<summary>Show answer</summary>

Both work with declarative state; Terraform centers on plan/apply workflows and Crossplane on continuous reconciliation. Terraform can be automated, and Crossplane remains subject to provider support, policies, quotas and errors.

</details>

## 5. How can ACK and Crossplane coexist?

<details>
<summary>Show answer</summary>

Separate ownership of external resources. ACK also provides namespaced CRs/references and can be composed with kro. Do not let several controllers compete to mutate the same AWS resource.

</details>

## 6. How are connection secrets provided in v2?

<details>
<summary>Show answer</summary>

MR writeConnectionSecretToRef remains, but core-native XR publication was removed. Compose a Secret or use supported Function aggregation. The example aggregates only endpoint/username and uses a separately prepared password Secret.

</details>

## 7. What is the Backstage/GitOps workflow?

<details>
<summary>Show answer</summary>

Render XR YAML with prepared skeletons/actions, merge a reviewed PR, reconcile through ArgoCD and Crossplane/Providers, then verify actual readiness. PR creation, catalog registration and completed AWS provisioning are different states.

</details>

## 8. What controls drift correction and retention?

<details>
<summary>Show answer</summary>

Check provider-supported fields, managementPolicies and polling. These v2 namespace MRs retain external resources by excluding Delete, distinct from legacy deletionPolicy: Orphan. Retention leaves backup, credential, cost and ownership responsibilities.

</details>
