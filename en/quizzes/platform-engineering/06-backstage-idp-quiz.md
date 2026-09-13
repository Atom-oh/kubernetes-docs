# Backstage IDP Quiz

[Backstage](../../platform-engineering/06-backstage-idp.md)

The original eight topics have been updated to the Backstage 1.54.7 review.

## 1. Which catalog kind represents a microservice?

<details>
<summary>Show answer</summary>

Component, with spec.type such as service. A catalog Resource describes infrastructure; it is not a controller provisioning AWS resources.

</details>

## 2. What does a Software Template actually create?

<details>
<summary>Show answer</summary>

Only the files and external operations implemented by registered actions and supplied skeletons. The guide's small example creates three catalog/TechDocs files, not an application runtime or database. Golden paths do not replace authorization or mandatory policies.

</details>

## 3. How are Kubernetes workloads matched to catalog entities?

<details>
<summary>Show answer</summary>

Match backstage.io/kubernetes-id or supported label-selector annotations to actual workload labels. Namespace/cluster selection, credentials and RBAC are also required. Metadata matching is not per-user authorization.

</details>

## 4. How should PostgreSQL and secrets be prepared on EKS?

<details>
<summary>Show answer</summary>

When selecting external PostgreSQL such as RDS, disable the bundled database and configure TLS, networking, schemas, migrations and backups. Use approved secret-file mounts with matching $file paths. A managed database alone does not complete HA/recovery verification.

</details>

## 5. How is TechDocs built and served?

<details>
<summary>Show answer</summary>

Use MkDocs and techdocs-core. With external builders, CI publishes to storage such as S3 and the Backstage backend reads it for the UI. Align entity keys/root paths and separate publisher/reader permissions; public bucket access is unnecessary.

</details>

## 6. What should be established during incremental adoption?

<details>
<summary>Show answer</summary>

Start with a small, accurate catalog and trusted ownership/sources, then expand templates and TechDocs. Establish authentication, authorization and trust boundaries from the outset.

</details>

## 7. What connects GitHub publication and ArgoCD actions?

<details>
<summary>Show answer</summary>

Register action modules and configure credentials, permissions and real input/output schemas. Roadie 1.8.1's argocd:create-resources takes the deployment namespace and has no revision input. Do not register a main-branch catalog file immediately after opening its unmerged PR.

</details>

## 8. How can catalog deletion be restricted by ownership?

<details>
<summary>Show answer</summary>

Register a real PermissionPolicy module, return an IS_ENTITY_OWNER condition for catalog deletion and let the catalog backend evaluate it. The example denies actions without explicit grants. Catalog ownership, GitHub writes and ArgoCD deployment permissions are distinct; protect Group/User sources too.

</details>
