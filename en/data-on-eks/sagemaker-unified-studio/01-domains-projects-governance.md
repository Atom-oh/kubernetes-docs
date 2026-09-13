# Part 4: Domain, Project and Membership Governance

> Documentation reviewed: 2026-09-12. Qwen provisioning results are historical; current account state was not rechecked.

The third recorded Qwen provisioning attempt reports a created project followed by
read/delete denial because of caller membership. Training did not start.
Do not generalize that record to every domain's current state or to every
authorization failure.

## 1. Distinguish objects and identities

| Object/role | Meaning |
| --- | --- |
| Unified domain / domain unit | Governance boundary and organizational hierarchy |
| Project profile / blueprint | Tool/environment provisioning and allowed accounts/regions |
| Project | Collaboration, tools and shared resources |
| User/group profile | Service representation of SSO identities or registered IAM roles |
| Membership designation | Project-level roles such as PROJECT_OWNER and PROJECT_CONTRIBUTOR |
| Project execution role | Identity accessing AWS data/compute for the project |
| Catalog asset | Governed metadata such as descriptions, schemas and locations |

First identify IAM-based versus Identity Center-based configuration and login.
Member and execution roles have different purposes, even when their ARN is the
same. IAM-based project members share data/compute access through the project
execution role; owner designation does not automatically isolate per-user data
permissions. Verify identity-based authorization/Trusted Identity Propagation
separately when used.

AWS user-management documentation distinguishes the group profile of a registered
IAM role from the session user profile created for someone logging in through it.
Membership can use the role group profile. CreateGroupProfile with rolePrincipalARN
**registers a profile; it does not create the IAM role itself**.
Automatic treatment of a project's execution role is not necessarily the same
as authorization of the automation caller.

## 2. A profile name does not prove tool readiness

All capabilities names a template of blueprints. Profiles can provision a blueprint
at project creation or make it available later on demand. Check required services,
accounts, regions, networks and permission to use the profile.

Select the intended profile ID/configuration rather than blindly choosing the
first name match. A smaller capability set may suit the Qwen experiment, subject
to organizational approval and real dependencies. Distinguish this workflow from
ordinary SageMaker/EKS training paths without Unified Studio projects.

## 3. IAM, membership and data authorization

An allowed IAM action does not supply project ownership. Project ownership also
does not bypass IAM, SCP, resource-policy or data-permission restrictions.
An ordinary member/contributor is not automatically authorized to delete.
Verify the project-owner or administrative authority required by the deletion path.

The current CreateProject API accepts membershipAssignments.
This is a **request-structure example**: replace domain/profile/group identifiers
with actual values resolved under authorized access.

```json
{
  "domainIdentifier": "dzd-1111111111111111",
  "name": "docs-governance-example",
  "projectProfileId": "c1111111111111",
  "membershipAssignments": [
    {
      "member": {
        "groupIdentifier": "11111111-1111-1111-1111-111111111111"
      },
      "designation": "PROJECT_OWNER"
    }
  ]
}
```


member is a tagged union: set **only one** of groupIdentifier or userIdentifier.
Including membership in the same request reduces the gap of a separate follow-up
request, but does not promise transactional rollback of all project/environment
provisioning. Read back the project and membership. After a timeout, reconcile the
original request and inventory rather than repeatedly creating projects by name.

## 4. Project and tool readiness sequence

1. Verify the intended account/region, domain type and profile ID.
2. Distinguish caller login/profile, required owner/admin authority and execution-role permissions.
3. Identify on-create versus on-demand blueprints and prepare approved dependencies.
4. Store and read back CreateProject and membership results.
5. Check projectStatus separately from environmentDeploymentDetails.
6. Verify required environment/tool readiness and real read/write access before the next compute step.

projectStatus=ACTIVE does not mean every environment/tool is ready.
overallDeploymentStatus includes PENDING_DEPLOYMENT, IN_PROGRESS, SUCCESSFUL,
FAILED_VALIDATION and FAILED_DEPLOYMENT. Do not treat intentionally unprovisioned
on-demand tools as failures; verify **what this workload actually requires**.

## 5. Tag failures and catalog disclosure

The current API supports resourceTags. The old experiment's rejection was a
domain/request-specific observation, not proof that Unified Studio has no tag
support. Inspect actual policy, values and errors. Limit compensation to resources
created by this run and authorized for cleanup; a prefix is not sufficient reason
to delete shared buckets or roles.

Public documentation can include necessary experiment counts, synthetic-data
schema/record counts, generator version/seed/hash and ownership/retention principles.
Keep actual PII, credentials, presigned URLs and reidentification mappings out of
public artifacts.

An access-controlled **internal catalog** may need storage locations and resource
identifiers for discovery/access. Public-document redaction is not a blanket ban on
internal location metadata. Metadata publication, subscription approval and actual
data authorization are separate steps.

## 6. Deletion and absence verification

1. Identify data to retain and this run's owned resources/dependencies.
2. Use authorized owner/admin context to stop the project's work and establish cleanup scope.
3. Delete according to project, environment and managed-resource lifecycle.
4. Inspect DELETING/DELETE_FAILED states/errors and verify completion.
5. Reconcile remaining external Apps, S3, IAM and compute with inventory across relevant accounts/regions.

GetProject AccessDenied is not evidence of absence.
An empty ListProjects response is also insufficient when visibility, filters or
pagination restrict it. Verify domain/identity and every page, combining authorized
get/list evidence with external-resource inventory. Project deletion does not
guarantee removal of every external service resource; verify ownership and retention
separately.

## 7. Historical scope of the Qwen validation

The stored validation JSON is dated **2026-09-01**.
It records trainingStarted=false for all three attempts, one remaining project after
the third, and cleanup of experiment App/S3/IAM resources. September 2 documentation
reports an ACTIVE recheck at that time. This review compares those records with
current public API documentation; it does not establish whether the project exists
or has been deleted in the current account.

Before resuming, verify current inventory and ownership.
No project, membership, IAM or GPU resource was created/deleted during this review.
The request example passed **local AWS CLI output-skeleton input validation**;
the variant setting both member identity types was rejected by ParameterValidation.
This does not demonstrate live authorization or environment provisioning success.

## References

- [IAM-based domains](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [Project member and execution roles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [User and group profiles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject request and deployment status](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [All capabilities profiles and on-demand provisioning](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [Project deletion and external resources](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Recorded Qwen provisioning validation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[Previous: SageMaker AI / MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)

[Next: Validation results](../../ai-ml/sagemaker-ai/04-validation-results.md)

[Quiz](../../quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
