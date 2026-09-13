# Landing Zone, OUs, and Organizational Control

> **Last Updated**: September 13, 2026

## 1. Control Tower Landing Zone 4.0's Baseline Dependency Chain

When standardizing a multi-account environment, AWS Control Tower is usually the first tool you reach for. Control Tower provides managed Account creation and organizational baselines/controls, but **Landing Zone 4.0 enforces an activation order dependency across several baselines**. If you finalize OU and IAM design without knowing this dependency chain, you'll end up redoing the work.

### The activation dependency chain

```
CentralConfigBaseline
  └─▶ CentralSecurityRolesBaseline
        ├─▶ IdentityCenterBaseline
        ├─▶ BackupAdminBaseline
        └─▶ BackupCentralVaultBaseline
```

To use `IdentityCenterBaseline` (Identity Center integration), `CentralSecurityRolesBaseline` must already be active, which in turn requires `CentralConfigBaseline` (AWS Config). **Deactivation must happen in reverse order** — you must turn off all three on the right (IdentityCenter/BackupAdmin/BackupCentralVault) before you can turn off SecurityRoles, and only then can you turn off Config.

> **Scope**: This chain applies to the IdentityCenterBaseline managed by Control Tower 4.0. IAM Identity Center itself does not require AWS Config. Distinguish independently managed Identity Center from its Control Tower integration.

Landing-zone Config integration deploys Config resources into service-integration Accounts. Member Accounts need the OU-level AWSControlTowerBaseline or ConfigBaseline; these two are mutually exclusive on an OU. This managed path requires landing-zone Config integration. For independently deployed Config, separately design ownership, conflict handling, and detective-control coverage.

<span id="the-security-ou-is-no-longer-freely-designable"></span>

### Security OU placement and baseline scope

In Control Tower 3.x, administrators manually created a designated Security OU. **In 4.0, the OU containing the service integration Accounts is automatically designated as the Security OU.** Three constraints follow from this.

1. `AWSControlTowerBaseline` and the Config Baseline cannot be applied to this OU (shown as `Not Applicable`, which is normal). `BackupBaseline` can be applied.
2. If a non-service-integration Account is placed in this OU, it won't receive baseline resources.
3. Control Tower only auto-creates Identity Center permission sets for the Logging Account and SecurityRoles Account. **You must create the permission sets for the Config Account and Backup Account yourself.**

Moving a general Account into the same OU as service-integration Accounts can drift enabled controls, independently of auto-enrollment. This constraint concerns that OU. Consider a separate managed OU for general security tools and Accounts awaiting migration.

> **Design proposal**: Separate service-integration Accounts from general security-operations Accounts to clarify baseline scope. AWS does not mandate particular OU names.

### CentralizedLogging deactivation behavior changed

In Control Tower 3.3 and earlier, disabling CentralizedLogging integration only turned off the Organization CloudTrail and kept already-deployed resources. **In 4.0, disabling it actually deletes the Config Recorder, Delivery Channel, and CloudTrail-related stack instances in the logging Account.** After that, Control Tower no longer manages that Account.

Before disabling, inventory affected stacks, recording gaps, and retained S3 logs separately. Management can be restored by re-enabling the integration or moving the Account to a managed OU, but recovery of collection gaps requires validation. This behavior does not establish that every historical log is deleted.

### Splitting responsibility between Control Tower and the internal pipeline

Based on which service integrations and OU baselines you activate, you need to decide between two directions first.

| Direction | Configuration | Trade-offs |
|---|---|---|
| A. Control Tower managed | Enable required integrations in dependency order; select baselines per OU | Central operations, with recording scope and cost managed together |
| B. Explicit ownership split | Define independently managed Identity Center/Config and Control Tower scopes | Internal lifecycle, conflict, and coverage validation |

## 2. Auto-Enrollment

With Landing Zone 3.1+, moving an Account into a registered OU automatically applies that OU's baselines and controls (auto-enrollment). Still, there are things it doesn't do for you.

- **It doesn't resolve pre-existing configuration conflicts or failure recovery automatically.** Pre-checks (Config, CloudTrail, SCP, IAM conflicts) need to be done separately.
- Unenrollment can remove managed baseline resources. Verify retention of existing logs and evidence separately. Keeping governance while restricting changes is an operational option for retiring Accounts, not an AWS requirement that every OU remain enrolled.
- Enrollment follows an eventually-consistent model, so it can take anywhere from minutes to hours depending on how many Accounts are moved.
- **Auto-enrollment does not create, modify, or terminate Service Catalog provisioned products.** If you unenroll an Account created via Account Factory, its provisioned product becomes an orphan in the management Account.

If your internal pipeline automates "Account move → auto-enrollment → workload bootstrap," the trigger condition should be **"baseline application confirmed complete,"** not the move event itself.

## 3. Quotas per Organizational Policy Type

The policy types Organizations supports serve different roles and have different default quotas.

| Policy type | Max attachments per entity | Max document size | Max org-wide |
|---|---|---|---|
| SCP | 10 | 10,240 chars | 10,000 |
| RCP | 5 (including `RCPFullAWSAccess`; 4 usable) | 5,120 chars | 2,000 |
| Declarative policy | 10 | 10,000 chars | 1,000 |
| Tag policy | 10 | 10,000 chars | 1,000 |
| Backup policy | 10 | 10,000 chars | 1,000 |
| Security Hub policy | 10 | 10,000 chars | 1,000 |

The key fact is that **inherited policies don't consume the per-entity attachment limit.** This heavily shapes SCP placement strategy.

### SCP attachment location strategies

| Strategy | Configuration | Quota-perspective evaluation |
|---|---|---|
| Root-heavy | Attach org-wide common SCPs at Root, OUs inherit | New Accounts inherit controls immediately, but hard to carve out per-OU exceptions |
| Fully-specified per-OU direct attachment | Attach every SCP each OU needs directly, minimizing dependency on parent OUs | Doesn't use inheritance, so a single OU can consume the entire 10-attachment limit — at the limit, policies must be merged |
| **Layered bundle** | Root carries only a minimal, exception-free SCP; the rest is versioned per-OU policy bundles + expiring exceptions | Actively leverages inheritance to conserve the direct-attach limit per OU — **the most scalable option from a quota perspective** |

Version policy documents and attachment inventories through Git revisions, deployment manifests, and CloudTrail changes. A version in Sid is optional. Inherited SCPs/RCPs, resource policies, and permission boundaries have distinct evaluation scopes; one simulation does not establish complete effective authorization.

A few more confirmed constraints:

- **If an entity has any SCP enabled, the last remaining SCP cannot be removed.** A design of "the exception OU has no controls at all" doesn't hold — even exception OUs need a minimal baseline SCP.
- OU nesting goes up to **5 levels** below Root, and the org can have up to **2,000 OUs** total. Flat or shallow-functional-hybrid structures aren't affected by this ceiling.
- RCPFullAWSAccess consumes one of five RCP attachments per entity. Four available direct attachments do not prohibit inheritance. Place controls across Root, OU, and Account levels while checking supported services, service-principal exceptions, and explicit denies. RCPs can protect sensitive-data paths but do not replace IAM, KMS, or resource policies.
- Organizations also has a **Security Hub policy type** — a means of centrally deploying Security Hub configuration as an org policy, worth reviewing alongside SCP/RCP/declarative policy/Tag Policy.

### Role separation by policy type (confirmed facts)

| Policy type | Role |
|---|---|
| SCP | Limits a principal's maximum permissions (doesn't grant permissions) |
| RCP | Limits the maximum scope a supported resource's resource policy can grant (doesn't directly grant permissions) |
| Declarative policy | Maintains org-wide common baseline settings for supported services |
| Tag Policy | Checks and enforces tag standard compliance |
| Control Tower control | Preventive/proactive/detective control at the OU level |

One SCP evaluation principle worth keeping in mind: an allow-list approach requires an explicit Allow at **every** level from Root down to the target Account, and an explicit Deny at any level cannot be overridden by an Allow further down.

## 4. Allow-List vs. Deny-List

| Approach | Suits | Operational overhead |
|---|---|---|
| Allow-list-centric | Sandbox, regulated zones where the set of usable services can be pre-restricted | Every new service/API must be explicitly allowed before use |
| **Deny-list-centric** | General Workload OU (default) | Requires ongoing detection of new service/API risk and maintaining a Deny catalog |

Compare regional describe-vpc-endpoint-services results with service documentation. The API inventory alone does not establish complete endpoint-policy, feature, or private-DNS support.

## 5. OU Design Options

| Option | Configuration | Pros | Cons |
|---|---|---|---|
| Deep hierarchical | Multiple nested levels below Root, parent controls inherited by children | Easy to represent classification and shared controls in the hierarchy | A Deny at a higher level has broad blast radius. Real ceiling is 5 levels |
| Flat under Root | Most OUs sit directly under Root, controls attached directly | Easy to reason about the blast radius of each OU | Risk of duplicated/missing shared policies; consumes the 10-attachment limit without inheritance |
| **Shallow functional hybrid** | Combine rarely-changing functional OUs (`Security`, `Infrastructure`) with lifecycle/procedural OUs (`Workloads/Production`, `Workloads/Non-production`, `Sandbox`, `PolicyStaging`, `Transitional`, `Suspended`) shallowly | Reduces the blast radius of org-chart changes while still expressing operational state | Functional classification, lifecycle, inheritance, and policy bundles must all be validated together. Because of the Security OU 4.0 constraint above, consider separate placement for service-integration and general operations Accounts |

`Transitional` can stage Accounts for migration checks; `Suspended` can restrict changes before retirement. Decide enrollment, evidence retention, and recovery access per lifecycle. Use a separate `Quarantine` when incident-investigation procedures differ.

It's worth distinguishing a persistent `Production-Exception` OU from time-boxed exception policies. If a particular API or policy only needs to be allowed for a limited window, handle it as an approval-scoped, expiring exception inside the standard Production OU; only create a separate OU when an Account needs a fundamentally different, long-term control set that's technically incompatible with the standard baseline.

## Next

Once Landing Zone and OU structure are settled, the next decision is how to partition Accounts and what IAM paths to give humans and workloads → [Account Structure and IAM Boundaries](./02-account-and-iam.md)

## References

- [Organizations quotas](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_reference_limits.html)
- [Control Tower landing zone 4.0 key changes](https://docs.aws.amazon.com/controltower/latest/userguide/key-changes-lz-v4.html)
- [Control Tower AWS Config updates (4.0)](https://docs.aws.amazon.com/controltower/latest/userguide/config-updates-v4.html)
- [Control Tower account auto-enrollment](https://docs.aws.amazon.com/controltower/latest/userguide/account-auto-enrollment.html)
- [Baseline types](https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html)
- [Enrolling an existing account](https://docs.aws.amazon.com/controltower/latest/userguide/enroll-account.html)
- [SCP evaluation](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_evaluation.html)
- [RCPs](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_rcps.html)
- [Declarative policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_declarative_policies.html)
- [Tag Policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)
- [Control Tower controls reference](https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html)
- [AWS multi-account design principles](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/design-principles-for-your-multi-account-strategy.html)
- [AWS recommended OUs and Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/recommended-ous-and-accounts.html)
