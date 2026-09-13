# Data and Security Boundaries

> **Last Updated**: September 13, 2026

## 1. Data Ownership Options

| Option | Configuration |
|---|---|
| Centralized DB operations Account | The platform team owns and operates every database in a single Account |
| Workload-owned data | Each workload team owns and operates its own database |
| **Hybrid** | Operational DBs are chosen per workload; shared assets like a data lake/warehouse/streaming backbone are owned by a separate Data Platform |

Hybrid is a realistic starting point for most organizations. But this choice matters less than the **technical constraints of cross-account backup/restore**, covered in the next section.

<span id="_2-cross-account-data-recovery-constraints-—-the-conditions-that-actually-change-your-decision"></span>

## 2. Validate Cross-Account Recovery by Resource and Vault Type

Choose data ownership and recovery location together. A restriction in one snapshot API does not make every recovery path impossible.

<span id="rds-snapshots"></span>

### Sharing RDS snapshots

- For RDS DB instances, copy an automated snapshot to a manual snapshot before sharing. The RDS sharing procedure also discusses AWS Backup-generated snapshots; it does not define every AWS Backup restore workflow.
- A recipient copies an encrypted shared DB-instance snapshot before restoring. Snapshots encrypted with the default AWS-managed KMS key cannot be shared as-is; assess a copy encrypted with an approved customer-managed key.
- A manual snapshot can be shared with up to 20 Accounts. Oracle/SQL Server permanent/persistent options add restrictions.
- **Multi-AZ DB cluster snapshots cannot use this RDS snapshot-sharing path.** This does not rule out every logical-backup or validated replication/recovery path, and does not mandate workload-owned databases. Check engine, snapshot type, Region support, and alternative recovery RTO/RPO.

<span id="aws-backup-cross-account-copy"></span>

### Standard AWS Backup vault: copy, then restore

- Source and destination must belong to one Organization, with cross-account backup enabled by its management Account.
- The source role needs `backup:CopyFromBackupVault` and `backup:CopyIntoBackupVault`; the destination vault needs a resource policy allowing the latter. Service-specific backup/copy and KMS permissions also apply.
- Encryption depends on resource type. Destinations for fully managed AWS Backup resources support `aws/backup` or customer-managed keys; other resource types require a customer-managed key. The official copy page also warns against default vaults. This guide therefore uses a **dedicated destination vault with explicit key/policy configuration**; a vault name alone does not establish encryption/copy suitability.
- Standard-vault cross-account recovery copies first, then restores in the destination. Prepare the resource’s service-linked role, restore role, subnets, and SGs.
- Cross-account copy from cold tiers is unsupported. Check the resource and Region feature matrices.

### Logically air-gapped vault: restore directly from a shared Account

A logically air-gapped vault can be shared through AWS RAM with individual Accounts, **including Accounts in another Organization**. The recipient can restore supported recovery points directly, without first copying them into a recipient vault. Thus “AWS Backup never supports direct cross-account restore” is inaccurate.

Distinguish standard-vault copy permissions from air-gapped-vault RAM sharing. Validate resource/Region support, restore IAM, encryption-key type, sharing authorization, and recovery when the source Account is inaccessible. Do not assume this supports every database type.

<span id="summary"></span>

### Restrict unapproved copy and sharing

A destination leaving the Organization may retain existing copies. Assess source `backup:CopyTargets`/`backup:CopyTargetOrgPaths` conditions, destination-vault policies, KMS, RAM sharing permissions, and organizational exit procedures together. Enabling cross-account backup does not grant copy permission to every user or bypass IAM, vault, or KMS denies.

RTO includes copy, restore, and application validation actually performed after an incident. Pre-existing copies shift copy cadence into RPO considerations. Record resource-specific recovery tests and objectives in the [Decision Framework](./06-decision-framework-and-poc.md).

## 3. Isolating the PII Data Tier

Storage that's placed directly inside a VPC (RDS, etc.) fits well in a separate VPC from the general serving tier. The purpose is to separate the scope of routing, inspection, direct access, and incident containment. **A separate VPC alone isn't sufficient** — you also need IAM, SG, KMS key policy, logging, and approved access paths working together.

> **Shared VPC audit access**: Participants cannot describe owner NAT gateways, but owner-provided route/NAT inventories, Config, Flow Logs, and delegated read access can provide evidence. Dedicated VPCs can simplify ownership; Shared VPC is not inherently unauditable.

S3 isn't a VPC-placed resource. Control it through bucket/Account ownership, VPC endpoints + endpoint policy, bucket/access point policy, KMS key policy, and org-approved paths.

### Blocking Dev/QA access to Production's original PII data

Turning "block direct access" into concrete API-level paths yields a coverage matrix like this.

| Path | Control mechanism |
|---|---|
| AWS Backup cross-account copy | `backup:CopyTargets`/`CopyTargetOrgPaths` SCP conditions, destination vault access policy |
| RDS DB-instance snapshot sharing | Restrict `rds:ModifyDBSnapshotAttribute` to approved automation; audit recipients with `DescribeDBSnapshotAttributes` |
| Aurora DB-cluster snapshot sharing | Restrict `rds:ModifyDBClusterSnapshotAttribute` to approved automation; audit recipients with `DescribeDBClusterSnapshotAttributes` |
| RDS/Aurora public snapshot sharing | Validate recipient allowlists and rejection of `restore=all` for both sharing APIs; retain KMS, detection, and remediation controls |
| Outbound EBS snapshot sharing | Restrict/audit `ec2:ModifySnapshotAttribute` and recipient createVolumePermission |
| EC2 Allowed AMIs(consumption) | Account/Region settings or declarative policy limit discovery/use of public/shared AMIs; Account-owned AMIs are excluded |
| S3 Batch Replication / cross-account replication | Bucket policy, restrict replication roles, RCP |
| Movement via DMS/Glue | That service's network/IAM path |
| CDC streams (MSK/Kinesis/DMS) | Resource policy + restrict cross-account consumers |
| Cross-account Athena/Redshift queries, Lake Formation | Audit Lake Formation cross-account grants |

Choose KMS key type and recovery permissions for the selected copy/restore path and organizational requirements. AWS does not universally mandate customer-managed keys for all PII storage. Test destination keys, pre-existing copies, permitted key policies/grants, and air-gapped-vault sharing when the source Account is unavailable.

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

- Distinguish Security Hub CSPM standards, controls, and ASFF findings from other Security Hub capabilities. Names alone do not establish identical feature scope or Config dependencies.
- Most Security Hub CSPM controls require AWS Config recording. Review this alongside Control Tower 4.0 managed-baseline dependencies, without turning it into a Config prerequisite for the IAM Identity Center service itself.
- **Security Hub CSPM doesn't retroactively collect findings generated before activation, and only processes findings in Regions where it's enabled.** For full coverage of the documented CIS AWS Foundations Benchmark security checks, you need to enable it in every supported Region. GuardDuty is also enabled per Region.
- GuardDuty and Security Hub are both available in the Seoul Region, but the finding types/control coverage differ by Region — comparisons should be based on actual Seoul Region coverage.

## 6. Services Confirmed to Support Resource Creation in a Shared Subnet

The table summarizes the official Shared VPC support list. That list explicitly permits omissions: consult service-specific documentation for unlisted services and distinguish explicit lack of support from absence in a list.

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

For engines explicitly excluded by the official list, such as Amazon MQ RabbitMQ, assess separate placement. Before excluding an entire CUJ from Shared VPC, consider connecting only that dependency through another VPC or API path.

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
- [Logically air-gapped vault sharing and restore](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)

- [Aurora snapshot sharing API](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBClusterSnapshotAttribute.html)
- [EC2 Allowed AMIs scope](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-allowed-amis.html)
