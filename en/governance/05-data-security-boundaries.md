# Data and Security Boundaries

> **Last Updated**: September 9, 2026

## 1. Data Ownership Options

| Option | Configuration |
|---|---|
| Centralized DB operations Account | The platform team owns and operates every database in a single Account |
| Workload-owned data | Each workload team owns and operates its own database |
| **Hybrid** | Operational DBs are chosen per workload; shared assets like a data lake/warehouse/streaming backbone are owned by a separate Data Platform |

Hybrid is a realistic starting point for most organizations. But this choice matters less than the **technical constraints of cross-account backup/restore**, covered in the next section.

## 2. Cross-Account Data Recovery Constraints — The Conditions That Actually Change Your Decision

Before deciding who owns the data, you need to check what constraints exist on the actual cross-account data movement/recovery path. These constraints apply equally regardless of whether you centralize or distribute ownership, so it's more accurate to treat them as **common guardrails both approaches must implement.**

### RDS snapshots

- **RDS automated backups cannot be shared.** To move them cross-account, you must first copy the automated snapshot into a manual snapshot, then share that copy (AWS Backup resources have the same constraint). Either direction requires a "copy" step, which needs time, storage cost, and someone to own the automation.
- **An encrypted shared snapshot cannot be restored directly.** The Account it was shared with must first copy it into their own Account, then restore from that copy.
  - **A snapshot encrypted with the AWS default KMS key can't be shared at all.** For any storage holding PII, a customer-managed key (CMK) is mandatory from the start — not a preference, but a prerequisite for any possibility of cross-account recovery.
  - A manual snapshot can be shared with at most 20 Accounts.
  - **Multi-AZ DB cluster snapshots cannot be shared.** If you use this configuration, that database has no cross-account recovery path at all. In that case, workload-owned data — keeping the DB and recovery responsibility in the same Account — becomes effectively mandatory.
  - Instances using Oracle/SQL Server permanent/persistent options (TDE, etc.) carry additional sharing restrictions.

### AWS Backup cross-account copy

All of the following prerequisites must be met.

- Source and destination Accounts must be in the same Organization.
- Must be explicitly enabled at the Management Account (`UpdateGlobalSettings`).
- **The destination vault cannot be the default vault** (the default vault's key can't be shared).
- The destination vault needs a resource policy allowing `backup:CopyIntoBackupVault`, and the source role needs both `backup:CopyFromBackupVault` and `backup:CopyIntoBackupVault`.
- Resource types not fully managed by AWS Backup require a CMK (an AWS-managed key can't be shared cross-account).
- **AWS Backup doesn't support direct cross-account restore.** This is also a two-step "copy, then restore from the copy" process. The destination Account needs the relevant service-linked role for that resource type already in place (missing if that service has never been used there).
- Backups moved to cold tier don't support cross-account copy.

A few of these have direct security design implications.

- **If the destination Account later leaves the Organization, it keeps whatever backups were already copied there.** This can be a PII exfiltration path, so we recommend denying `organizations:LeaveOrganization` via SCP.
- **Once cross-account backup is enabled, any member Account user in the org can set their own Account as a destination.** This creates a risk of PII backups being copied to unauthorized Accounts — enforce `backup:CopyTargets`/`backup:CopyTargetOrgPaths` conditions on `backup:CopyFromBackupVault` to require approved vaults/OUs. Note that even if IAM, KMS, resource policies, and VPC endpoint policies are all locked down, the backup copy path exists as a separate channel and needs its own check.

### Summary

None of the constraints above favor centralized ownership over workload-owned data, or vice versa — neither side has an advantage. The one exception: **"Multi-AZ DB cluster snapshots can't be shared" is the only constraint that actually forces a choice.** A legitimate recovery path (production → an isolated recovery Account) is subject to the same restrictions as blocking Dev/QA access, so your **RTO calculation must include snapshot copy time** — non-trivial for a terabyte-scale database. **Without defined RTO/RPO targets, this judgment can't be made at all** — see [Decision Framework and PoC Design](./06-decision-framework-and-poc.md).

## 3. Isolating the PII Data Tier

Storage that's placed directly inside a VPC (RDS, etc.) fits well in a separate VPC from the general serving tier. The purpose is to separate the scope of routing, inspection, direct access, and incident containment. **A separate VPC alone isn't sufficient** — you also need IAM, SG, KMS key policy, logging, and approved access paths working together.

> **A pitfall when using a Shared VPC for the PII tier**: a participant can't even describe a NAT Gateway (see [Chapter 4](./04-shared-vpc-and-connectivity.md)). If your PII tier sits in a participant Account with a centrally-owned VPC, the data-owning team can't verify their own data's egress path — making it hard to prove "where can this data leave to" during a regulatory response. This argument is more accurately framed not as "isolation strength" but as **"the owning team's ability to prove their egress path."** That's why a dedicated VPC (workload-owned) has the advantage from an auditability standpoint for the PII tier.

S3 isn't a VPC-placed resource. Control it through bucket/Account ownership, VPC endpoints + endpoint policy, bucket/access point policy, KMS key policy, and org-approved paths.

### Blocking Dev/QA access to Production's original PII data

Turning "block direct access" into concrete API-level paths yields a coverage matrix like this.

| Path | Control mechanism |
|---|---|
| AWS Backup cross-account copy | `backup:CopyTargets`/`CopyTargetOrgPaths` SCP conditions, destination vault access policy |
| RDS manual snapshot sharing | `rds:ModifyDBSnapshotAttribute` SCP Deny, or restrict target Accounts |
| RDS snapshot public sharing | Block the `restore` attribute from being set to `all` via SCP |
| EBS snapshot sharing / EC2 Allowed AMIs | Restrict `ec2:ModifySnapshotAttribute`, allowlist source Accounts |
| S3 Batch Replication / cross-account replication | Bucket policy, restrict replication roles, RCP |
| Movement via DMS/Glue | That service's network/IAM path |
| CDC streams (MSK/Kinesis/DMS) | Resource policy + restrict cross-account consumers |
| Cross-account Athena/Redshift queries, Lake Formation | Audit Lake Formation cross-account grants |

For KMS keys, even if the PII storage is workload-owned, you should **mandate a CMK** and **pre-include a recovery Account as a principal in the key policy.** Trying to change the key policy after an incident requires access to the key owner's Account — but if that Account is the one that's been breached, recovery is blocked. Also restrict via SCP which Accounts can be set as a backup vault's destination.

## 4. Secrets Manager / KMS Cross-Account

Both the secret's resource policy and the caller's identity policy are required. Cross-account secrets need a customer-managed KMS key, and that key requires both the owner's key policy and the caller's IAM policy. In other words, centralized secret/key management needs more than just policy and rotation — it requires **jointly operating permissions and recovery responsibility across both Accounts.**

## 5. AWS-Native Security Telemetry vs. Existing CNAPP

If your organization already has a CNAPP (Cloud-Native Application Protection Platform) and is adopting AWS-native capabilities, the safer approach isn't "replace the product" — it's to **compare current coverage against AWS-native capabilities by security purpose, and fill only confirmed gaps.** Purposes can be grouped as:

- Organizational preventive controls
- Configuration posture
- Data security posture
- Workload runtime protection
- Threat detection
- Finding workflow
- Workload-context detection

Some confirmed facts:

- **"AWS Security Hub" was renamed "Security Hub CSPM."** CSPM features (standards, controls, finding aggregation, automation rules) are distinct from other Security Hub features — if a comparison table doesn't clarify which one it's referring to, the overlap judgment against CNAPP will be off.
- **Security Hub CSPM requires AWS Config for most controls.** If Config is disabled, most control findings won't be generated. Combined with the [Landing Zone baseline dependency chain](./01-landing-zone-and-ou.md), **whether Config is enabled becomes the common prerequisite for three decisions: Landing Zone, Identity Center, and Security Hub CSPM.**
- **Security Hub CSPM doesn't retroactively collect findings generated before activation, and only processes findings in Regions where it's enabled.** For full CIS benchmark compliance, you need to enable it in every supported Region. GuardDuty is also enabled per Region.
- GuardDuty and Security Hub are both available in the Seoul Region, but the finding types/control coverage differ by Region — comparisons should be based on actual Seoul Region coverage.

## 6. Services Confirmed to Support Resource Creation in a Shared Subnet

AWS explicitly maintains the list of services that can create resources in a Shared VPC subnet, and any workload using a service outside this list needs to be treated as an exception to the Shared VPC strategy.

| Supported service | Notes |
|---|---|
| Amazon RDS, Aurora | Primary target |
| ElastiCache (Redis OSS) | |
| Redshift, EMR, Glue | Common Data Platform target |
| OpenSearch Service, MSK | |
| EC2, ECS, EKS, Lambda, EFS | |
| ALB/NLB/GWLB | |
| PrivateLink (interface endpoint) | |
| VPC Lattice, TGW, VPC Peering, Traffic Mirroring | |
| Route 53 (PHZ cross-account association) | |
| DMS, Verified Access, SageMaker Unified Studio | |
| **Amazon MQ** | **ActiveMQ only. RabbitMQ is not supported** |

AWS itself notes that "this list may have omissions" — cross-reference your actual service inventory against this list, and if any service on a CUJ's path is unsupported, exclude that workload from the Shared VPC locality strategy. In particular, **check RabbitMQ usage specifically.**

## Next

For a way to make all decisions across boundaries, accounts, IAM, network, and data reproducible → [Decision Framework and PoC Design](./06-decision-framework-and-poc.md)

## References

- [RDS snapshot sharing](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html)
- [RDS encrypted snapshot sharing](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/share-encrypted-snapshot.html)
- [AWS Backup cross-account copy](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)
- [Secrets Manager cross-account](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html)
- [KMS external account key policy](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html)
- [Security Hub CSPM introduction](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [Security Hub CSPM controls by Region](https://docs.aws.amazon.com/securityhub/latest/userguide/regions-controls.html)
- [GuardDuty differences by Region](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_regions.html)
- [AWS SRA Security Tooling](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/security-tooling.html)
- [Supported services for shared subnets](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-service-behavior.html)
