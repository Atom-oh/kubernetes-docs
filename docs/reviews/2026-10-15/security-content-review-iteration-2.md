# Content Review Report: Security & Policy Chapters 13–16 (ko/en), Re-review

## Review Metadata
| Field | Value |
|-------|-------|
| **Review Type** | GitBook/VitePress bilingual Markdown, batch re-review: 4 chapters × 2 locales, their quizzes, the nav bridges, the news map and the research ledger |
| **Review Date** | October 15, 2026 |
| **Iteration** | #2 (previous: #1 scored 80.5/90, REVIEW, 0 Critical / 4 Warning) |
| **Current Score** | **90.0 / 90** (Visual Testing exempt; 100 when scaled to 100) |
| **Verdict** | **PASS** |
| **Developer deployment gate** (raw ≥85/90, 0 Critical, ≤3 Warning, PASS) | **MET.** 90.0 ≥ 85, 0 Critical, 0 Warning, verdict PASS |
| **Intended report path** | `docs/reviews/2026-10-15/security-content-review-iteration-2.md` (not written; this review was read-only) |

## Quality Gate Result
### Verdict: PASS
Each band is judged separately:
- **Score:** 90.0 ≥ 77, so PASS.
- **Critical:** 0, so PASS.
- **Warning:** 0 (≤3), so PASS.

The worst of the three bands is PASS, so the verdict is **PASS**.

### Batch summary (each chapter = en+ko page plus its en/ko quiz)
| Artifact | Score /90 | Critical | Warning | Change from #1 | Rubric verdict | Meets raw-85 gate |
|---|---|---|---|---|---|---|
| Ch13 Defense in depth / incident response | 90.0 | 0 | 0 | I-6 fixed | PASS | Yes |
| Ch14 WAF / edge / origin | 90.0 | 0 | 0 | W-1, I-1(a) and I-3 fixed | PASS | Yes |
| Ch15 Palo Alto / Fortinet NGFW | 90.0 | 0 | 0 | W-3(a)(c), I-1(b), I-4, I-5 and I-7 fixed | PASS | Yes |
| Ch16 GWLB / GENEVE | 90.0 | 0 | 0 | W-2, W-3(b) and W-4 fixed | PASS | Yes |
| Nav, bridges, news map, research ledger | 90.0 | 0 | 0 | W-3(d), I-2 and I-9 fixed | PASS | Yes |
| **Batch (findings counted once)** | **90.0** | **0** | **0** | 4 of 4 Warnings fixed | **PASS** | **Yes** |

### Category scores (batch, 90-point scale)
The deduction procedure is the same as in iteration #1: each defect costs ¼ of its category's points, the deductions are summed, the total is rounded once to the nearest 0.5, and midpoints round toward the larger deduction. No defects remain, so every category gets full marks. The Info items below carry no deduction.

| Category | Max | Score | Critical | Warning | Info |
|---|---|---|---|---|---|
| Layout | 8 | 8 | 0 | 0 | 0 |
| Terminology | 8 | 8 | 0 | 0 | 0 |
| No Hallucination / accuracy | 12 | 12 | 0 | 0 | 0 |
| Language Consistency | 8 | 8 | 0 | 0 | 2 (R2-I3, R2-I4) |
| No Sensitive Data | 12 | 12 | 0 | 0 | 0 |
| Content-Type Quality (GitBook nav/components) | 2 | 2 | 0 | 0 | 1 (R2-I5) |
| Icon Usage (not applicable to Markdown/Mermaid) | 5 | 5 | 0 | 0 | 0 |
| Visual Testing | — | exempt | — | — | — |
| Readability | 5 | 5 | 0 | 0 | 0 |
| Accessibility | 5 | 5 | 0 | 0 | 0 |
| Structural Completeness | 5 | 5 | 0 | 0 | 0 |
| Data Accuracy & External References | 5 | 5 | 0 | 0 | 3 (R2-I1, R2-I2, R2-I6) |
| Legal Compliance | 5 | 5 | 0 | 0 | 0 |
| Message Clarity | 5 | 5 | 0 | 0 | 0 |
| Duplication / Gaps | 5 | 5 | 0 | 0 | 0 |
| **Total** | **90** | **90.0** | **0** | **0** | **6** |

## Critical Issues (Must Fix)
None. No corrected statement names a non-existent AWS feature or attribute, and the corrected text contains no credentials or PII. The `0.0.0.0/0` values are route-table destinations in a design example, not security-group ingress.

## Warning Issues (Should Fix)
None open.

## Iteration-1 Warnings: Re-verification
I checked each correction against the cached primary sources, not against the brief. For each finding I grepped its keywords across `{en,ko}/security/*`, `{en,ko}/quizzes/security/*`, `{en,ko}/networking/README.md`, security/04 and 06, the news map and both research files. That is how a partial fix (page fixed, quiz not) would show up.

### W-1 (forwarded-IP address selection): RESOLVED
| Location | Current text (en; ko matches) | Source |
|---|---|---|
| `{en,ko}/security/14-waf-edge-api-security.md:89` | `Geo match, ASN match and rate-based statements use the first address. IP set match uses the configured FIRST, LAST or ANY position; ANY checks up to 10 addresses, using the last 10 when more are present.` | S13:86–92 |
| `{en,ko}/security/14-…:91` | `A missing header produces no match for the direct statement and does not invoke malformed-value fallback. An enclosing NOT can invert no match into a match…` | S13:38–41 ("No match… NOT… converts the evaluation to Match… Missing headers don't trigger fallback"); S13:96–102 |
| `{en,ko}/quizzes/security/14-…-quiz.md:87–99` (Q6) | The question is now limited to a direct statement without an enclosing NOT. Answer B: "no match; absence differs from malformed fallback". The explanation repeats the NOT and FIRST/LAST/ANY rules. | Consistent with the page |
| `docs/research/2026-10-15-security-deep-research.md:52` | Row matches the page | — |

The grep for `first address|첫 주소|fallback|forwarded.?IP|NOT` in ch13–16 and their quizzes found no remaining "always first address" wording. Old I-3 (the NOT caveat) is resolved by the same edit.

### W-2 (all-unhealthy documented behavior): RESOLVED
| Location | Current text | Source |
|---|---|---|
| `{en,ko}/security/16-gwlb-geneve-inspection.md:117` | `GWLB randomly selects an unhealthy target per flow and keeps it until reset/timeout; AWS documents drops until it becomes healthy` / Operational column: `…a health-only fault that still forwards is a PoC hypothesis` | S26:139–142 |
| `{en,ko}/security/16-…:124` | No direct bypass; random per-flow selection and drops; "Decisions are independent among zones"; cross-zone widens the set of eligible targets | S26:146–153 |
| `{en,ko}/security/16-…:126` | "fail-open mode" is attributed to the older blog, for existing flows staying on failed targets; the health-only case is an experiment | S32:191 |
| `{en,ko}/security/16-…:180` | Experiment row: "no assumption of direct bypass" | Consistent |
| `{en,ko}/quizzes/security/16-…-quiz.md:7–19` (Q1) | Question scoped to "all eligible targets". The explanation states the documented drop, the PoC hypothesis, and the per-AZ and cross-zone checks. | S26:139–153 |
| `{en,ko}/networking/README.md:404` | "per-flow target selection and drops until recovery, with no direct appliance bypass" | S26:139–142 |
| Ledger S26 `purpose` (`sources.json:582`); research note `:63` | Updated to match | — |

The grep for `broken health endpoint|health endpoint만|coexist|might still inspect|검사할 수 있|Fail open delivers` in the security subtree, its quizzes and the networking README found 0 hits. The `검사할 수 있` hits are in unrelated chapters 01, 06 and 11. The heading "Health, failover and fail open" (16:109) stays; the section now explains the term correctly.

### W-3 (citation provenance and ledger): RESOLVED
| Sub-item | Current state | Source support |
|---|---|---|
| (a) ch15 TLV | `{en,ko}/15:27` Fortinet cell `…AWS TLV handling [S42]`; `:32` "AWS defines the GWLB GENEVE TLV format and Option Class 0x0108 separately in its target-group documentation [S42]" | S42:31–33 |
| (b) ch16 TLV | `{en,ko}/16:32` `…GWLB uses that metadata to select the return GWLBE… [S31] [S42] [S29]` | S42:31–33; S29:193, 205 |
| (c) SNAT | `{en,ko}/15:107` default VPC CNI IPv4 traffic leaving the VPC CIDRs is translated to the node's primary address, with an instruction to check the actual setup `[S44]`; `:109` Pod-address churn `[S33]`; `16:99` `[S33] [S34] [S44]` | S44:11–12, 20, 24; S33:189–194 |
| Reference lists | S42 and S44 appear in both locales of ch15 (`:187–188`, `:209–210`) and ch16 (`:215–216`, `:231–232`) | — |
| (d) Ledger | S33 `purpose` = "NetworkPolicy and Flow Logs, including Pod-address attribution limits" (`:743`); S42 `purpose`/`used_by` now list ch15 and ch16 in both locales (`:917`, `:928–934`); S44 added (`:958–979`); `source_count: 43` (`:5`); grep finds exactly 43 IDs (S01–S40, S42–S44); `navigation_only_source_ids: ["S41"]` (`:981–983`); research note `:68`, `:73` | Consistent with validation.json "43 source IDs" |

Quiz 15 Q6 (`{en,ko}/quizzes/security/15-…:87–99`, node address after SNAT) is consistent with the corrected §5.

### W-4 (TGW "AZ affinity" terminology): RESOLVED
| Location | Current text | Source |
|---|---|---|
| `{en,ko}/security/16-…:17` | `One inspection-attachment ENI/AZ per flow, used for both directions` | S29:225 ("selects a single Transit Gateway ENI… For return traffic… the same selected Transit Gateway ENI") |
| `{en,ko}/security/16-…:80` | "…replacing TGW's default origin-AZ preference and allowing cross-AZ routing. It does not replicate firewall sessions." | S29:215; S32:177, 184 ("no longer maintains the AZ affinity, and lets traffic cross AZ") |
| `{en,ko}/quizzes/security/16-…:55–67` (Q4) | Answer D "Consistent inspection-attachment AZ selection for both directions"; the explanation uses symmetric per-flow selection and the origin-AZ note | Same |
| Research note `:69` | Matches | — |

The grep for `AZ affinity|affinity` in ch13–16, their quizzes and the networking README found 0 hits. The only matches were unrelated SPIFFE anti-affinity text in ch12.

## Iteration-1 Info items: status
| Item | Status | Evidence |
|---|---|---|
| I-1 ko precision | Resolved | ko 14:56 "종료 action으로 결정되지 않은 요청에는…"; ko 15:42 "모든 트래픽을 허용" (S20:228–230). See R2-I3 for a reverse drift in en. |
| I-2 news keywords | Resolved | `.github/news-topic-map.yml:108–115`: bare `geneve`, `palo alto`, `security incident` and `incident response` replaced with `gateway load balancer`, `gwlb geneve`, `transit gateway appliance mode`, `palo alto networks`, `pan-os`, `cloud security incident response` and `eks incident response` |
| I-3 NOT caveat | Resolved (with W-1) | 14:91 |
| I-4 TLS 1.3 health | Resolved | `{en,ko}/15:40` [S26]; S26:143–145 |
| I-5 symlink versions | Resolved | `{en,ko}/15:141`, labeled "historical remediation references, not 2026 version recommendations"; S07:41, 44–45 |
| I-6 ch13 date column | Resolved | `{en,ko}/13:10` "Case and publication/retirement date" / "사례와 공개·종료 시점" |
| I-7 management EIP | Resolved | `{en,ko}/15:76`, a sample step reconciled with the advisories' trusted-source restriction; S20:153–154 |
| I-8 answer rotation | Carried as R2-I5 | Acceptable under repo convention |
| I-9 S41 gap | Resolved | `sources.json:981–983`; research note `:73` |

## Info (no deduction)
- **R2-I1 (Ledger: S32 `purpose` is out of date).** `sources.json:721` gives S32's purpose as "GWLB deployment, all-deregistered behavior and traffic considerations". The S32 cache has 0 matches for `deregist`. After W-2 and W-4, S32 now backs appliance-mode AZ behavior (S32:177, 184), the fail-open terminology for existing flows (S32:191), MTU and the historical RST/timeout context. This is Info rather than a W-3(d)-class Warning because no chapter or research-note claim cites S32 for deregistration (the empty-fleet row cites S25·S42, research note `:64`). Its `review_status` therefore remains true for every claim actually attributed to it. Fix: reword the purpose, e.g. "TGW appliance-mode AZ behavior, fail-open terminology for existing flows, MTU, historical RST/timeout context".
- **R2-I2 (Ledger metadata).** The top-level `recorded_at` is `2026-10-15T13:36:37` (`sources.json:3`), which predates S44's `accessed_at` of `14:19:25` (`:962`). Separately, the pre-review snapshot `/tmp/security-research-2026-10-15/S44-record.json:14` still says `retrieved_not_yet_content_reviewed`, while the ledger (`:971`) says `used_claims_checked…`. I confirmed S44 supports both claims that cite it, so the ledger status is accurate and the `/tmp` record sits outside the release. Fix: bump `recorded_at`.
- **R2-I3 (Language parity, I-1 in reverse).** en 15:42 says "the default intrazone rule allows traffic". S20:229–230 says "allows **all** traffic", and ko 15:42 now says "모든 트래픽", so en is now the less precise locale. Fix: "allows all traffic".
- **R2-I4 (ko phrasing).** `ko/networking/README.md:404` reads "all-unhealthy에는 flow별 target 선택과 회복 전 drop을 설명하며 장비를 직접 우회하지 않습니다." The unstated subject changes partway through, from AWS (설명) to GWLB (우회하지 않음). Suggest: "all-unhealthy일 때 AWS는 … drop을 설명하며, GWLB는 장비를 직접 우회하지 않습니다."
- **R2-I5 (Quiz, carried from I-8).** Answer keys still rotate A-B-C-D. This is acceptable under repo convention.
- **R2-I6 (Citation precision).** `{en,ko}/15:109` says "Even preserved Pod addresses are **reused** and change during scaling [S33]". S33:193–194 supports "frequently change as they are replaced" but does not say "reused". The fact is general and harmless; optionally drop "reused" or keep it as unsourced framing.
- **Not penalized, by design (carried):** ch14 Option A "Public ALB origin" remains a documented AWS pattern. If the owner's no-internet-facing-LB policy should apply to readers, present Option B as the preferred option.

## Source-omission Findings
| Source section | Output status | Note |
|---|---|---|
| S26 all-unhealthy behavior | INCLUDED (was PARTIAL) | Random per-flow target, drop until healthy, per-zone scope, cross-zone distinction |
| S26 TLS 1.3-only health failure | INCLUDED (was omitted) | ch15:40 |
| S13 forwarded-IP position, missing header and NOT | INCLUDED (was PARTIAL) | ch14:89–91 |
| S42 GWLB target groups | PARTIAL (was OMITTED) | TLV and Option Class 0x0108 now cited. "≥1 registered target per enabled AZ" (S42:57–58) is still not stated near the empty-fleet row; acceptable |
| S44 EKS external SNAT (new) | INCLUDED | Windows and `hostNetwork` exceptions are summarized as "verify actual external-SNAT, OS and routing configuration"; acceptable |
| S29 / S32 appliance mode and fail-open | INCLUDED | Symmetric ENI selection; default same-AZ behavior; blog terminology attributed |
| S20 VM-Series manual | INCLUDED (was PARTIAL) | Management-ENI EIP called out (ch15:76) |
| S07 Fortinet persistence | INCLUDED (was PARTIAL) | Release-specific symlink removal (ch15:141) |
| S27 GWLBE considerations | PARTIAL (unchanged, not re-reviewed) | Egress-only IGW/IPv6 and consumer-initiated-response notes still unused; acceptable |
| S03–S06, S10–S12, S24, S25, S30, S43 | Unchanged from #1 (not re-reviewed) | Previously INCLUDED or acceptable |

## Revision Checklist
### Critical (Must Fix)
- [ ] None

### Warnings (Should Fix)
- [ ] None

### Optional (Info)
- [ ] R2-I1: Reword S32 `purpose` in `sources.json:721`.
- [ ] R2-I2: Bump `recorded_at` in `sources.json:3`.
- [ ] R2-I3: en 15:42, "allows all traffic".
- [ ] R2-I4: Make the subjects explicit in the ko networking README:404 sentence.
- [ ] R2-I6: Optionally drop "reused" at `{en,ko}/15:109`.

### Score Impact Summary
| If Fixed | Critical | Warnings | Projected Score | Verdict / raw-85 gate |
|---|---|---|---|---|
| Nothing (current) | 0 | 0 | 90.0 | PASS / met |
| All Info items | 0 | 0 | 90.0 | PASS / met (no score change) |

## Scope and Limitations
- **Tools.** Only Read, Grep and Glob were used; as instructed, Bash and Playwright were not retried. Visual Testing is therefore **exempt** and the 90-point rubric applies.
- **Scope.** This was a correction-focused re-review. I read ch14 and ch16 in full in both locales, ch15 in full in both locales, and the full ch14 and ch16 quizzes in both locales. For quiz 15 I read Q6 and grepped the rest; for ch13 I grepped citations and the date column. I also checked the networking README, security/04 and 06 bridges, the news map, the research note §1–§7, and the S26–S44 ledger entries plus its header and footer.
- **Not repeated.** CVE scopes and dates, KEV dates, WAF body/rate limits and other unchanged claims verified in #1 were not re-researched.
- **No git diff.** I could not run `git diff`, so I can't prove that only the listed hunks changed. Hunks outside the files and keywords above were not reviewed.
- **Grounding.** All grounding used the cached S07, S13, S20, S26, S29, S32, S33, S42 and S44 in `/tmp/security-research-2026-10-15`, treated as data. Nothing was fetched live. I checked every correction claim in the brief against these caches and all of them held: 43 sources, S41 navigation-only, S42 and S33 ledger fixes, and S44 content.
- **Host evidence, not executed by me.** `docs/research/2026-10-15-security-validation.json` (`verified_at` 14:24:21Z: 126 docs tests, 16 Markdown/Vue pages compiled, 6 diagrams parsed, full build passed) and `/tmp/security-release-render-check.json` (status passed). I did not recompute the sha256 values in validation.json. Its `deployment.content_review_gate_passed: false` still reflects iteration #1.
- **No changes made.** I wrote no files, memory or git state. The iteration-1 report keeps its historical quotes; I did not treat them as current defects.

## Next Steps
**PASS. The deployment gate is met** (90.0/90 raw, 0 Critical, 0 Warning). Before deploying, the host should save this report to the intended path and record iteration #2 in `security-validation.json` (`content_review_gate_passed: true`, score 90.0/90). The R2-I1 to R2-I6 items are optional polish and don't block deployment. After merge, cn/jp/es mirrors need `translate-backfill.yml` for the `security` section, per CLAUDE.md. Do not hand-edit them.
