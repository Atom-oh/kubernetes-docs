# SageMaker Unified Studio Governance

> Documentation reviewed: 2026-09-12. Experiment outcomes refer to the 2026-09-01 record and the historical September 2 documentation.

Amazon SageMaker Unified Studio manages collaboration, tools and catalog assets
for data/AI teams. This section explains domain/project boundaries for EKS
pipeline assets, users and execution permissions.
The **Unified Studio/DataZone project** here is not the same API object as a
SageMaker AI MLOps Project or SageMaker AI Studio domain.

## Boundaries covered

| Topic | What to verify |
| --- | --- |
| Domain type | IAM-based versus IAM Identity Center-based login/administration |
| Project profile / blueprint | Tools provisioned at creation versus enabled on demand |
| Member / execution role | Portal/project access identity versus AWS resource execution identity |
| Membership / data access | Administrative designations versus IAM, Lake Formation and catalog data permissions |
| Lifecycle | Project existence, environment readiness, actual tool access and owned-resource cleanup |

[Part 4: Domain, project and membership](01-domains-projects-governance.md) explains
the Qwen experiment's recorded failures through these boundaries. A Unified Studio
project is this guide's governance choice, not a mandatory technical dependency
for every SageMaker Training Job or EKS training workload.

## Distinguish historical evidence from current state

The stored 2026-09-01 validation JSON records a stop before training, cleanup of
experiment App/S3/IAM resources and one remaining Unified Studio project.
September 2 documentation records an ACTIVE recheck at that time.
**This documentation review did not query the AWS account again and does not
assert that one project still remains today.**

Before resuming that experiment, an authorized operator must verify current
inventory, membership and cleanup state. Do not generalize the old failure into
an automatic grant of new privileges or deletion of shared resources.

Related guides:

- [SageMaker Qwen PII guidebook](../../ai-ml/sagemaker-ai/README.md)
- [Part 3: SageMaker AI and MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
- [Part 5: Factual validation results](../../ai-ml/sagemaker-ai/04-validation-results.md)

## References

- [IAM-based domains](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [Project member and execution roles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [User and group profiles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject request and deployment status](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [All capabilities profiles and on-demand provisioning](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [Project deletion and external resources](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Recorded Qwen provisioning validation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
