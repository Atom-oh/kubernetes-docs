# Landing Zone, OUs, and Organizational Control

> **Last Updated**: September 9, 2026

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

> **Why this matters**: A design that defers Config as an independent decision — "we'll adopt Identity Center now but decide on Config later after comparing CNAPP tools" — doesn't hold. **Whether Config is enabled directly determines whether the Identity Center baseline can be used.**

Landing Zone-level Config integration only deploys central resources into the service integration Account. To deploy a Config Recorder to a general member Account, you still need to enable the Config baseline per OU — but **if you disable Config integration at the Landing Zone level, you can't turn on the OU baseline either.** If you want "Config is owned by the internal platform pipeline," Landing Zone-level integration must stay on, with only the OU baseline applied selectively.

### The Security OU is no longer freely designable

In Control Tower 3.x, administrators manually created a designated Security OU. **In 4.0, the OU containing the service integration Accounts is automatically designated as the Security OU.** Three constraints follow from this.

1. `AWSControlTowerBaseline` and the Config Baseline cannot be applied to this OU (shown as `Not Applicable`, which is normal). `BackupBaseline` can be applied.
2. If a non-service-integration Account is placed in this OU, it won't receive baseline resources.
3. Control Tower only auto-creates Identity Center permission sets for the Logging Account and SecurityRoles Account. **You must create the permission sets for the Config Account and Backup Account yourself.**

Also, **moving a general Account into the Security OU family puts that OU's enabled controls into a drift state**, regardless of the auto-enrollment setting. Don't place a `Transitional` OU (used for inspecting inherited/migrated Accounts) under the Security OU family.

> **Design recommendation**: Separate `Security` (reserved exclusively for 4.0's service integration Accounts — never place a general Account there) from `SecurityOperations` (general Accounts your security team actually uses, e.g., SIEM/CNAPP integration accounts). Merging these two into one OU will always require rework later.

### CentralizedLogging deactivation behavior changed

In Control Tower 3.3 and earlier, disabling CentralizedLogging integration only turned off the Organization CloudTrail and kept already-deployed resources. **In 4.0, disabling it actually deletes the Config Recorder, Delivery Channel, and CloudTrail-related stack instances in the logging Account.** After that, Control Tower no longer manages that Account.

During a phased migration, you cannot use "disable now, re-enable later" as a rollback mechanism — this is a teardown, not a toggle.

### Splitting responsibility between Control Tower and the internal pipeline

Based on which service integrations and OU baselines you activate, you need to decide between two directions first.

| Direction | Configuration | Trade-offs |
|---|---|---|
| A. Maximize Control Tower | Enable all of Config/CloudTrail/SecurityRoles/Backup integration + per-OU Config baseline | Identity Center baseline usable. Config costs apply organization-wide |
| B. Minimize | Enable only Config integration, apply the OU baseline selectively, manage Identity Center directly via the internal pipeline | Config cost is controllable per OU, but you must operate Permission Set lifecycle yourself |

## 2. Auto-Enrollment

With Landing Zone 3.1+, moving an Account into a registered OU automatically applies that OU's baselines and controls (auto-enrollment). Still, there are things it doesn't do for you.

- **It doesn't resolve pre-existing configuration conflicts or failure recovery automatically.** Pre-checks (Config, CloudTrail, SCP, IAM conflicts) need to be done separately.
- **Unenrollment automatically deletes baseline resources.** If you unenroll an Account because it's slated for decommissioning, the baseline resources kept as audit evidence disappear with it. It's safer to **keep decommissioned Accounts enrolled and block changes with a Deny-focused SCP** instead.
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

Organizations itself has no policy versioning feature, so to run "versioned policy bundles" you need to embed a version string directly in the policy document's `Sid` and build your own tooling to determine which version applied from effective policy simulation results.

A few more confirmed constraints:

- **If an entity has any SCP enabled, the last remaining SCP cannot be removed.** A design of "the exception OU has no controls at all" doesn't hold — even exception OUs need a minimal baseline SCP.
- OU nesting goes up to **5 levels** below Root, and the org can have up to **2,000 OUs** total. Flat or shallow-functional-hybrid structures aren't affected by this ceiling.
- **RCP only has 4 usable slots and its document size is half that of SCP (5,120 chars)**. You don't have room for a layered-bundle-style strategy with RCP. It's better reserved for a small number of absolute organization-wide rules (fully blocking external principal access to S3/KMS, confused-deputy defense via enforcing `aws:SourceOrgID`), leaving fine-grained control to SCPs and individual resource policies. In particular, reserving RCP as the **last line of defense for PII storage** is an effective strategy.
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

For information that changes constantly, such as whether a new service supports VPC endpoints, we recommend periodically dumping `aws ec2 describe-vpc-endpoint-services` and diffing it automatically instead of relying on manual research.

## 5. OU Design Options

| Option | Configuration | Pros | Cons |
|---|---|---|---|
| Deep hierarchical | Multiple nested levels below Root, parent controls inherited by children | Easy to represent classification and shared controls in the hierarchy | A Deny at a higher level has broad blast radius. Real ceiling is 5 levels |
| Flat under Root | Most OUs sit directly under Root, controls attached directly | Easy to reason about the blast radius of each OU | Risk of duplicated/missing shared policies; consumes the 10-attachment limit without inheritance |
| **Shallow functional hybrid** | Combine rarely-changing functional OUs (`Security`, `Infrastructure`) with lifecycle/procedural OUs (`Workloads/Production`, `Workloads/Non-production`, `Sandbox`, `PolicyStaging`, `Transitional`, `Suspended`) shallowly | Reduces the blast radius of org-chart changes while still expressing operational state | Functional classification, lifecycle, inheritance, and policy bundles must all be validated together. Because of the Security OU 4.0 constraint above, `Security` and `SecurityOperations` must be separated |

`Transitional` is a temporary staging spot for inspecting acquired/migrated Accounts before placing them in a standard OU; `Suspended` blocks general changes to Accounts slated for decommissioning. Both must **stay enrolled** (see Section 2). A `Quarantine` OU for suspected breach Accounts should only be split out separately when its investigation authority, evidence preservation, and recovery process genuinely differ from `Suspended`.

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
