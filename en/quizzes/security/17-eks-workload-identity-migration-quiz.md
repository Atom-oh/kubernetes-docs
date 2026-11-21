# EKS workload IAM migration quiz

1. After removing the node's S3 read policy, `GetCallerIdentity` succeeds from the legacy Pod and `GetObject` is denied. What happened?

   <details>
   <summary>Show Answer</summary>

   The credentials obtained through IMDSv2 still identify the node role. S3 denies the read because the role lost permission to access the object.

   </details>

2. Which paths deliver temporary role credentials for IRSA and Pod Identity?

   <details>
   <summary>Show Answer</summary>

   IRSA exchanges the projected ServiceAccount token with STS using `AssumeRoleWithWebIdentity`. The Pod Identity SDK sends a token to the node's Agent, which retrieves role credentials through EKS Auth and returns them to the SDK.

   </details>

3. What canary evidence do you need before removing application permissions from the node role?

   <details>
   <summary>Show Answer</summary>

   Verify that a new Pod uses the expected workload role and succeeds on its required AWS APIs. Check other dependencies including scheduled jobs and controllers, credential refresh, and the IAM policy needed for rollback.

   </details>

[Migration guide and demo](../../security/17-eks-workload-identity-migration.md)
