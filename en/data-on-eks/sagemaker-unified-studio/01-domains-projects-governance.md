# Part 4: Domain, Project, and Membership Governance

> **Last Updated**: September 2, 2026

## Why This Chapter Exists

The Qwen PII validation stopped at Unified Studio project membership, not at GPU or model code. On the third provisioning attempt, the project was created without adding the caller role's group profile as a project member, so project reads and deletion were denied.

The incident demonstrates that IAM authorization and Unified Studio authorization are separate layers.

## Object Model

| Object | Role | Operational Question |
|---|---|---|
| **SageMaker unified domain** | top-level governance boundary for users, project profiles, catalog, and policies | which organization, accounts, and Regions operate it? |
| **Domain unit** | organizational hierarchy within a domain | where should projects and policies be attached? |
| **Blueprint** | configuration that provisions tools and resources | which services and Regions may receive resources? |
| **Project profile** | project template composed of blueprints | who may create a project from it? |
| **Project** | collaboration, file, tool, and resource-sharing boundary for one use case | who owns it, who is a member, and who deletes it? |
| **Catalog asset** | metadata used to describe, discover, publish, and subscribe to data | what metadata is published instead of raw data? |
| **User/group profile** | internal profile for an SSO user/group or IAM role | is the automation role's group profile a member? |
| **Membership** | owner/member association between a profile and project | who may create, inspect, manage members, and delete? |

A project is a collaboration boundary. When strong isolation is required, use separate AWS accounts plus explicit data and network boundaries rather than relying on a project alone.

## Project Profiles and All Capabilities

A project profile is an upper-level template built from blueprints. The `All capabilities` template starts with the Tooling blueprint, and an administrator can configure capabilities including:

- `MLExperiments`
- `Workflows`
- `LakehouseCatalog`
- `EmrOnEc2`
- `RedshiftServerless`
- `LakeHouseDatabase`
- `EmrServerless`
- `AmazonBedrockGenerativeAI`

Do not assume the name `All capabilities` means every blueprint is immediately ready. Verify that the profile is enabled, required blueprints are enabled in the target Region, and the intended identities are authorized to create projects from it.

The Qwen example locates an enabled `All capabilities` profile, but the training job does not need every capability. A smaller custom profile containing Tooling and ML experiment capabilities may better match least privilege.

## IAM Permission vs. DataZone Authorization

Treat the layers separately:

| Layer | What It Allows | What It Does Not Supply |
|---|---|---|
| IAM | attempts to call APIs such as `CreateProject`, `ListProjects`, and `DeleteProject` | owner/member association for a specific project |
| Unified Studio/DataZone authorization | context-specific domain owner, project owner, and project member actions | IAM permission to reach AWS APIs |

When an IAM role is added to a domain, Unified Studio creates a group profile. Project membership and access policies are managed through that group profile.

Assign the execution role's group profile as an owner in the project-creation request:

```json
[
  {
    "member": {
      "groupIdentifier": "<execution-role-group-profile>"
    },
    "designation": "PROJECT_OWNER"
  }
]
```

A project owner can add or remove members and manage project-level activities such as asset publication.

## Safe Creation Order

1. Identify the target domain from organizational configuration.
2. Verify an enabled project profile and required blueprint/Region readiness.
3. Resolve the group profile for the caller IAM role.
4. Include owner membership atomically in the project-creation request.
5. Wait for project status `ACTIVE`.
6. Verify project reads and member management under the owner context.
7. Only then approve the MLflow App and GPU execution path.

Adding membership in a later step can leave a project that exists but is inaccessible to the automation role when an intermediate operation fails.

## Tag Policy and Project Creation

The second provisioning attempt was rejected because the domain did not accept custom project resource tags. Do not automatically copy general experiment tags into Unified Studio project creation.

- Use only tags permitted by the domain and project-profile policy.
- Supplement lifecycle tracking with a local inventory and a safe resource-name prefix.
- On tag rejection, correct only the project request and tear down the already-created App, S3, and IAM resources.

## Catalog Asset Design

Apply minimum-disclosure rules even though the training data is synthetic.

Appropriate catalog metadata:

- split record counts and language ratio;
- schema and nine entity types;
- generator version, seed, and SHA-256;
- owning team, retention, and approved purpose.

Do not publish:

- complete source text;
- entity original values;
- raw model completions;
- token mappings;
- presigned URLs or internal storage identifiers.

## Deletion and Absence Verification

Safe deletion does not end when a delete API returns successfully:

1. block new GPU execution;
2. verify owner membership;
3. remove project environments and resources;
4. request project deletion;
5. poll `ListProjects` until the target disappears;
6. independently inspect Apps, S3, IAM, EKS, EC2, and the tag inventory;
7. close the inventory only when the remaining count is zero.

An authorization error from `GetProject` must not be interpreted as absence. Use an authorized list operation for existence and teardown verification, and never publish the returned identifiers.

## September 2, 2026 State

Read-only recheck:

| Item | State |
|---|---|
| `qwen-pii-*` Unified Studio project | 1 |
| project status | `ACTIVE` |
| SageMaker MLflow App | none remaining |
| experiment S3/IAM resources | none remaining |
| required action | domain-owner deletion, or grant owner membership to the execution role and then delete |

Preflight must continue blocking new execution until this project is removed.

Previous: [Part 3 — SageMaker AI and MLflow execution](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)

Next: [Part 5 — Factual validation results](../../ai-ml/sagemaker-ai/04-validation-results.md)
