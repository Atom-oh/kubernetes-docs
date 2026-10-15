# Content Review Report — Security & Policy Chapters 13–16 (ko/en) + nav/bridge/research updates

## Review Metadata
| Field | Value |
|-------|-------|
| **Review Type** | GitBook/VitePress bilingual Markdown (Batch Review: 4 chapters × 2 locales, 8 quizzes, nav/bridge/config/research files per `/tmp/security-release-files.json`) |
| **Review Date** | October 15, 2026 |
| **Iteration** | #1 |
| **Current Score** | **80.5 / 90** (Visual Testing exempt; 89.4 when scaled to 100) |
| **Verdict** | **REVIEW** |
| **Developer deployment gate** (raw ≥85, 0 Critical, ≤3 Warning, PASS) | **NOT MET.** Raw 80.5 < 85, 4 Warnings > 3, verdict is not PASS |

## Quality Gate Result
### Verdict: REVIEW
Each band is judged separately. Score: 80.5 ≥ 77, so PASS. Critical: 0, so PASS. Warning: 4, so REVIEW. The worst band sets the verdict, so the result is **REVIEW**.

### Batch summary (per chapter = en+ko page + its en/ko quiz)
| Artifact | Score /90 | Critical | Warning | Rubric verdict | Meets raw-85 gate |
|---|---|---|---|---|---|
| Ch13 Defense in depth / incident response | 90.0 | 0 | 0 | PASS | Yes |
| Ch14 WAF / edge / origin | 87.0 | 0 | 1 (W-1) | PASS | Yes |
| Ch15 Palo Alto / Fortinet NGFW | 88.5 | 0 | 1 (W-3) | PASS | Yes |
| Ch16 GWLB / GENEVE | 83.5 | 0 | 3 (W-2, W-3, W-4) | PASS | **No** |
| Nav, bridges (04/06/networking README), news map, research ledger | 88.5 | 0 | 1 (W-3, ledger) | PASS | Yes |
| **Batch (findings counted once)** | **80.5** | **0** | **4** | **REVIEW** | **No** |

### Category scores (batch, 90-point scale)
Deduction procedure: each defect costs ¼ of its category's points. Defects are summed, the total is rounded once to the nearest 0.5, and midpoints round toward a lower score.

| Category | Max | Score | Critical | Warning | Info |
|---|---|---|---|---|---|
| Layout | 8 | 8 | 0 | 0 | 0 |
| Terminology | 8 | 6 | 0 | 1 (W-4) | 0 |
| No Hallucination / accuracy | 12 | 6 | 0 | 2 (W-1, W-2) | 1 (I-3) |
| Language Consistency | 8 | 8 | 0 | 0 | 1 (I-1) |
| No Sensitive Data | 12 | 12 | 0 | 0 | 0 |
| Content-Type Quality (GitBook nav/components) | 2 | 2 | 0 | 0 | 1 (I-8) |
| Icon Usage (not applicable to Markdown/Mermaid) | 5 | 5 | 0 | 0 | 0 |
| Visual Testing | — | exempt | — | — | — |
| Readability | 5 | 5 | 0 | 0 | 0 |
| Accessibility | 5 | 5 | 0 | 0 | 0 |
| Structural Completeness | 5 | 5 | 0 | 0 | 0 |
| Data Accuracy & External References | 5 | 3.5 | 0 | 1 (W-3) | 3 (I-5, I-6, I-9) |
| Legal Compliance | 5 | 5 | 0 | 0 | 0 |
| Message Clarity | 5 | 5 | 0 | 0 | 0 |
| Duplication / Gaps | 5 | 5 | 0 | 0 | 3 (I-2, I-4, I-7) |
| **Total** | **90** | **80.5** | **0** | **4** | **10** |

## Critical Issues (Must Fix)
None. All AWS features, attributes and API fields named in the chapters exist in the cached primary sources. These include `waf.fail_open.enabled`, `send_tcp_reset.*`, `target_failover.*`, `TcpEstablishedTimeout`, the WAF log fields, CloudFront VPC origins and `ApplianceModeSupport`. No credentials or PII were found.

## Warning Issues (Should Fix)

### Issue W-1: Forwarded-IP address selection misstated for IP set match
| Field | Value |
|-------|-------|
| **Severity** | Warning |
| **Category** | No Hallucination / accuracy |
| **Location** | `en/security/14-waf-edge-api-security.md:89`; `ko/security/14-waf-edge-api-security.md:89` |
| **Original** | en: `WAF uses the first address for forwarded-IP IP matches/rate rules; a missing header means the rule does not apply.` / ko: `AWS WAF는 IP match·rate rule에서 전달 header의 첫 주소를 사용하고, header가 없으면 해당 규칙이 적용되지 않습니다.` |
| **Problem** | S13 lines 86–92: "For geo match, ASN match, and rate-based rules, AWS WAF uses the first address in the header… For IP set match, you indicate whether to match against the first, last, or any address in the header… [any] up to 10 addresses… If the header contains more than 10 addresses, AWS WAF inspects the last 10." IP set match is configurable and does not always use the first address. The missing-header half of the sentence is correct (S13:100–102). |
| **Action** | Split the rule types: geo, ASN and rate-based rules use the first address; IP set match uses the configured FIRST, LAST or ANY position (ANY checks up to 10 addresses, and the last 10 when more are present). Apply the same change in ko. Quiz 14 Q6 can stay as it is ("always uses the last address" remains a valid distractor). |
| **Expected** | `For geo match, ASN match and rate-based rules, WAF uses the first address in the header; IP set match uses the configured position (FIRST, LAST or ANY—ANY inspects up to 10 addresses). A missing header means the rule does not apply.` |
| **Points** | −3 from No Hallucination |

### Issue W-2: The all-unhealthy "Documented AWS behavior" omits AWS's documented outcome and teaches an inference that contradicts it
| Field | Value |
|-------|-------|
| **Severity** | Warning |
| **Category** | No Hallucination / accuracy (health versus inspection, all-unhealthy versus empty fleet) |
| **Location** | `en/security/16-gwlb-geneve-inspection.md:117, :124`; `ko/security/16-gwlb-geneve-inspection.md:117, :124`; `en/quizzes/security/16-gwlb-geneve-inspection-quiz.md:19`; `ko/quizzes/security/16-gwlb-geneve-inspection-quiz.md:19` |
| **Original** | en 16:117 `\| All targets unhealthy \| Fail open delivers to unhealthy targets \|…`; en 16:124 `A stopped appliance cannot forward; an appliance with only a broken health endpoint might still inspect.`; ko 16:124 `…health endpoint만 고장 난 장비는 검사할 수 있습니다.` (a stronger claim than en: "can" instead of "might"); en quiz 16:19 `an unhealthy health endpoint can coexist with working inspection.` |
| **Problem** | S26:139–142 says: "When all targets are unhealthy, the Gateway Load Balancer picks a target at random and forwards traffic to it for the life of the flow, until it is either reset or has timed out. Because traffic is being forwarded to an unhealthy target, traffic is dropped until that target becomes healthy again." S26:150–152 adds that health and load-balancing decisions are independent per zone. S32's table (lines 205–208) gives "dropped until at least one target is restored" for an all-failed AZ when cross-zone is disabled. The column labeled "Documented AWS behavior" leaves out three documented facts: random per-flow target selection, the documented drop outcome, and per-zone scope. The page and quiz then present the opposite expectation (inspection may keep working) as the lesson. S26 does not use the term "fail open". S32 uses "fail-open mode" for a different case, where existing flows stay on a failed target. The central point, that there is no direct bypass of the appliances, is correct and should be kept. |
| **Action** | Rewrite the cell as AWS documents it. Keep "no direct bypass". Move "a health-only fault might still pass traffic" into the Operational check column as a hypothesis to test, not a lesson. Note that the scope is per zone when cross-zone is disabled. Attribute "fail open" as common or blog terminology. Rewrite the second sentence of the quiz explanation in both locales. |
| **Expected** | Cell: `Per flow, GWLB picks an unhealthy target at random and keeps the flow there until reset/timeout; AWS documents traffic as dropped until that target is healthy. No direct bypass. Evaluated per zone unless cross-zone is enabled.` Quiz: `GWLB does not bypass appliances; AWS documents drops until the chosen target recovers. Whether a health-only fault still forwards traffic is something to test, not documented behavior.` |
| **Points** | −3 from No Hallucination |

### Issue W-3: Inline citations do not support the claims they are attached to, and the ledger misstates S33
| Field | Value |
|-------|-------|
| **Severity** | Warning |
| **Category** | Data Accuracy & External References |
| **Location** | (a) `en/security/15-ngfw-paloalto-fortinet.md:27, :32` and `ko/…/15…:27, :32`; (b) `en/security/16-gwlb-geneve-inspection.md:32` and `ko/…/16…:32`; (c) `en/security/15-ngfw-paloalto-fortinet.md:103` and `ko/…/15…:103`; (d) `docs/research/2026-10-15-security-sources.json:745` (S33 `purpose`) and `:930` (S42 `used_by`) |
| **Original** | (a) `UDP 6081, GWLB-node GENEVE configuration and AWS TLV handling` (Fortinet column, sourced to S19–S23); (b) `Use supported AWS/vendor integration to preserve and return required metadata. … [S31] [S19] [S22]`; (c) `After node SNAT the appliance may see a node address rather than a Pod address. … [S33]`; (d) `"purpose": "NetworkPolicy, SNAT and Flow Logs"` with `used_claims_checked_against_retrieved_primary_source` |
| **Problem** | All of these claims are true, but they point to the wrong evidence. The cached S19, S22 and S23 contain no TLV or AWS-metadata text. The fact is in S42:31–33 ("GENEVE header uses a TLV format… Option Class 0x0108. Appliances must decapsulate the TLV pairs") and S29:193 ("GWLB, based on GENEVE TLV, selects GWLBE"). S42 is not cited in either chapter: the ledger records `used_by` as the research note only. S33 contains no SNAT or NAT text (searching for `\bNAT\b`, `translat` and `external.?snat` returns 0 matches), yet the ledger says SNAT claims were checked against it. This release presents itself as primary-source grounded, so wrong-source citations weaken that provenance. |
| **Action** | Cite S42 (and S29) for TLV/metadata in ch15 §2 and ch16 §2, and add S42 to both reference lists in both locales. For SNAT, cite a verified EKS primary source; the repo already uses `security-groups-for-pods.html` for this behavior at `en/networking/calico/08-eks-integration.md:273`. Alternatively, keep [S33] only on the Pod-address-churn sentence. Correct S33's `purpose` and S42's `used_by` in the ledger. |
| **Expected** | `… AWS TLV handling [S42]`; `…preserve and return required metadata. [S31] [S42] [S29]`; the SNAT sentence cites an EKS SNAT source; ledger S33 purpose: `NetworkPolicy and Flow Logs`. |
| **Points** | −1.5 from Data Accuracy & External References (¼ of 5 = 1.25, rounded toward a lower score) |

### Issue W-4: "AZ affinity" used for TGW appliance mode, the opposite of the cited source's wording
| Field | Value |
|-------|-------|
| **Severity** | Warning |
| **Category** | Terminology |
| **Location** | `en/security/16-gwlb-geneve-inspection.md:17`; `ko/security/16-gwlb-geneve-inspection.md:17`; `en/quizzes/security/16-gwlb-geneve-inspection-quiz.md:67`; `ko/quizzes/security/16-gwlb-geneve-inspection-quiz.md:67` |
| **Original** | `\| TGW appliance mode \| Bidirectional AZ affinity for inspection attachment \|…`; quiz: `AZ affinity differs from GWLB target stickiness…` / `AZ affinity는 …` |
| **Problem** | S32:184, which ch16 cites: "when you enable Appliance Mode, AWS Transit Gateway no longer maintains the AZ affinity, and lets traffic cross AZ." AWS uses "AZ affinity" for the default behavior that appliance mode turns off. A learner who checks the cited source will find the opposite wording. ch16:80 and the Q4 answer text ("consistent … AZ selection for both directions") are correct. |
| **Action** | Replace "AZ affinity" with "symmetric per-flow attachment/AZ selection" in all four places. Optionally add a short note that appliance mode replaces TGW's default origin-AZ affinity. |
| **Expected** | `\| TGW appliance mode \| One inspection-VPC attachment ENI/AZ per flow, used for both directions \|…`; quiz: `Symmetric per-flow AZ selection differs from GWLB target stickiness and vendor session sharing.` |
| **Points** | −2 from Terminology |

## Info (no deduction)
- **I-1 (Language).** Two ko sentences are less precise than en or the source. ko 14:56 `규칙 불일치 시 Web ACL default action이 적용됩니다` versus en "when no terminating rule decides" (a Count match still falls through to the default action). ko 15:40 `기본 intrazone 규칙이 허용할 수 있다고` versus S20:228–230 "a default intrazone rule allows all traffic". Align both with en.
- **I-2 (Gaps/automation).** In `.github/news-topic-map.yml:114`, the keyword `geneve` overlaps the Cilium GitHub-release feed that `weekly-news-digest.yml:100–101` ingests, where Geneve tunneling is routine. The matching step at `:115` is case-insensitive, so Cilium items could trigger in-place edits to ch16, which itself says Cilium overlay and GWLB GENEVE are unrelated. `security incident`/`incident response` (:108) and `palo alto` (:112) are similarly broad. Consider `gwlb geneve`/`gateway load balancer` and `pan-os`/`palo alto networks`.
- **I-3 (Accuracy nuance).** S13:38–41 also says a missing header evaluates as "No match", which a `NOT` statement converts to "Match". Ch14 §5 states only "rule does not apply" (S13:100–102). Add the NOT caveat.
- **I-4 (Gap).** S26:143–145: HTTPS health checks fail for targets that support only TLS 1.3. This is directly relevant to ch15's "use HTTPS/TCP" Palo Alto guidance.
- **I-5 (Accuracy nuance).** S07:41–44 names the fixed releases that remove the symlink on upgrade (7.6.2/7.4.7/7.2.11/7.0.17/6.4.16) and also requires configuration review. Ch13/15's "version numbers do not prove removal" remains correct; adding the vendor's specifics would help.
- **I-6 (Data).** The ch13:10 column header "Case and publication date" holds the retirement effective date (`2026-03`) for the ingress-nginx row; the statement was published 2026-01-29. Rename the column or swap the dates.
- **I-7 (Gap).** The vendor manual guide itself assigns an EIP to the management ENI (S20:152–162), while S03 and S04 advise trusted internal IPs only. Ch15 §3 could call this out explicitly.
- **I-8 (Quiz).** Answer keys rotate strictly: ch14 and ch16 are A-B-C-D-A-B-C-D, and ch15 is the same pattern shifted. This is acceptable under repo convention.
- **I-9 (Ledger).** IDs skip S41 (a Fortinet blog index used only for navigation, recorded in `retrieval.json`). This is harmless; a note in the research record would explain it.
- **Not penalized, by design:** ch14 Option A "Public ALB origin" is a documented AWS pattern for third-party learners. If your own no-internet-facing-LB policy should apply to readers, present Option B (VPC origin) as the preferred option.

## Verified-correct focus items (independent evidence)
| Focus item | Result | Evidence |
|---|---|---|
| WAF association targets/scope, terminating actions, CAPTCHA/Challenge | Correct | S09:10–21; S10:14–59 |
| Body limits (ALB/AppSync 8 KB; others 16→64 KB; gRPC excluded), CONTINUE/MATCH/NO_MATCH | Correct | S11:13–22; S12:35–51 |
| Rate rules (approximate, 60/120/300/600 s, reset + up to 1 min pause) | Correct | S37:13; S43:13–28 |
| Logging redaction ≠ sampling/Security Lake; `waf.fail_open.enabled` default false; ALB doesn't validate target certs | Correct | S15:17–20; S18:269–273; S38:52–54 |
| PAN-OS CVE-2026-0322: authenticated mgmt RCE as root, PA/VM-Series/Panorama, Cloud NGFW/Prisma Access excluded, ETA ≠ release, KEV 2026-10-14 | Correct | S03:57–66, 80; S06:57–61 |
| FortiCloud CVE-2026-24858: Jan 28 correction (third-party SAML IdP/FortiAuthenticator not impacted), KEV 2026-01-27, recovery guidance | Correct | S05:31, 36, 96–99; S06:3935–3939 |
| Palo Alto HTTP-health contradiction; default intrazone allows all | Correct (contradiction faithfully represented) | S20:87–89 vs 210–212; 228–231 |
| FortiGate same-AZ GWLB IPv4 as `remote-ip`; egress back via Geneve interface | Correct | S22:1132, 1161, 1187–1195 |
| 2/3-tuple unsupported with TGW appliance mode; RST needs 5-tuple + no_rebalance, TCP only, default false | Correct | S25:87–98, 138–140 |
| Idle timeouts 350 (60–6000, 5-tuple only), UDP 120 fixed, ENI `TcpEstablishedTimeout`; MTU 8500/+68, no fragmentation/PMTUD | Correct | S24:63–99, 122–133 |
| Empty fleet: new flows have no target; draining existing flows distinguished | Supported (hedged "verify drops") | S42:63–67; S25:101–109; S32:205–208 |
| NAT request/return routes, TGW route tables | Correct | S29:172–208 |
| Patching ≠ eradication | Correct | S05:96–99; S07:28–31, 43–46 |
| Nav: SUMMARY/README entries for 4 chapters + 8 quizzes in both locales; bridge sections in 04/06/networking README | Present, links resolve, labels match quiz H1s | `{en,ko}/SUMMARY.md:330–333, 692–695`; `README.md:294–297` |

## Source-omission Findings
| Source section | Output status | Note |
|---|---|---|
| S26 all-unhealthy behavior | PARTIAL | Random per-flow target, "dropped until healthy" and per-zone scope omitted (W-2); TLS 1.3-only health-check failure omitted (I-4) |
| S13 forwarded-IP position rules | PARTIAL | FIRST/LAST/ANY for IP set misstated (W-1); NOT conversion (I-3) |
| S42 GWLB target groups | OMITTED from chapters | TLV option class 0x0108 (W-3); "≥1 registered target per enabled AZ" not stated near the empty-fleet row |
| S27 GWLBE considerations | PARTIAL | "Egress-only IGW drops IPv6 with GWLB" and "endpoint returns only responses to consumer-initiated traffic" not used in §5 IPv6 row / ingress section |
| S20 VM-Series manual | PARTIAL | Vendor's own EIP on management ENI (I-7) |
| S07 Fortinet persistence | PARTIAL | Release-specific symlink removal (I-5) |
| S24 / S25 / S29 / S30 / S32 | INCLUDED | Appliance MTU ≥ 8,568 covered as "headroom" |
| S03 / S04 / S05 / S06 | INCLUDED | Threat ID 510046/510047 limited coverage (requires decryption) omitted; acceptable |
| S10 / S11 / S43 | INCLUDED | Monetize action, ALB HTTP/2 inspection-timing attribute and multi-minute rate-detection lag omitted; acceptable (lists are not claimed to be exhaustive) |

## Revision Checklist
### Critical (Must Fix)
- [ ] None

### Warnings (Should Fix). Grep the keyword across both locales; do not rely on line numbers.
- [ ] W-1: Forwarded-IP selection. Grep `first address|첫 주소` in `{en,ko}/security/14-*`. Split geo/ASN/rate (first) from IP set (FIRST/LAST/ANY).
- [ ] W-2: All-unhealthy. Grep `broken health endpoint|health endpoint만|coexist with working inspection|검사할 수` in `{en,ko}/security/16-*` and `{en,ko}/quizzes/security/16-*`. State the S26 documented behavior and turn the inference into a test.
- [ ] W-3: Citations. Grep `TLV|metadata` in `{en,ko}/security/1[56]-*` and add [S42]/[S29]; fix the SNAT citation at `{en,ko}/security/15-*:103`; fix S33 `purpose` and S42 `used_by` in `sources.json`.
- [ ] W-4: Grep `AZ affinity` in `{en,ko}/security/16-*` and `{en,ko}/quizzes/security/16-*`, and reword.

### Score Impact Summary
| If Fixed | Critical | Warnings | Projected Score | Verdict / raw-85 gate |
|---|---|---|---|---|
| Nothing | 0 | 4 | 80.5 | REVIEW / not met |
| W-1 + W-2 only | 0 | 2 | 86.5 | PASS / met (minimum) |
| All warnings | 0 | 0 | 90.0 | PASS / met |

## Scope and Limitations
- In "don't ask" mode, Bash, Playwright, Chrome DevTools and the AWS documentation MCP were denied. Playwright availability was checked once (`browser_navigate` was denied), so Visual Testing is **exempt** and the 90-point rubric applies. The 8 rendered pages exist under `/home/atomoh/kubernetes-docs/.vitepress/dist/{en,ko}/security/`, but they were not opened or compared with this worktree.
- I could not run `git diff`, the validators, markdown-it or the build. Markdown/Vue compilation, the 6 Mermaid parses and the full build rest on `validation.json` and your brief. I found the changed nav/bridge hunks by grep, so unrelated edits elsewhere in those files were not reviewed. Manual checks found no CommonMark bold-flanking traps and no undefined `[Sxx]` references.
- External grounding used the cached primary sources in `/tmp/security-research-2026-10-15` (retrieved 2026-10-15, 13:27–13:36 UTC). Nothing was fetched live. The brief's asserted facts (CVE scopes and dates, the Fortinet correction, KEV dates) were checked independently against those caches and are correct.
- No cloud or appliance operations, git changes, memory writes or source edits were made.

## Next Steps
**REVIEW.** Fix W-1 through W-4 in both locales (fixing W-1 and W-2 is the minimum to meet your raw-85 / ≤3-Warning gate), then re-review. The re-review will grep each finding's keywords across the whole subtree, including quizzes, because a page and its own quiz disagreeing is the most common way a partial fix fails. Ch13 is clean, and ch14/ch15 pass individually.
