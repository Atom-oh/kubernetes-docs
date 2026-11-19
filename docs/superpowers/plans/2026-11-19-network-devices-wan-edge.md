# Network Devices, WAN and Edge Curriculum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four gaps in the beginner→expert networking path (devices/LAN, WAN/hybrid, CDN, WAF/DDoS), each with ko/en text, an explained quiz and line-art animated SVGs showing where and how packets move.

**Architecture:** One new foundations part (`basics/06-network-fundamentals-part5.md`) and three new expert workbooks (`networking/expert/07-09`). Existing file numbers stay as they are. Each flow is a line-art animated SVG (SMIL, no JS) embedded as an image, so it animates in both GitBook and VitePress.

**Tech Stack:** Markdown (GitBook/VitePress), hand-authored animated SVG, playwright-core frame capture for verification, existing `npm run docs:validate`.

**Spec:** Agreed in conversation on 2026-11-19 (no separate spec file, per repo CLAUDE.md):
- Audience: engineers who must become network experts.
- Placement: "난이도별 분산". Gap ① goes to basics Part 5; gaps ②③④ go to expert 07/08/09.
- Animations: line-art animated SVGs (chosen over interactive TS scenes and HyperFrames videos because they play inline in both GitBook and VitePress).
- External baselines: CCNA 200-301 v1.1, CCNP ENCOR v1.2, CompTIA Network+ N10-009, AWS ANS-C01 (Design 30 / Implementation 26 / Operations 20 / Security 24).

## Global Constraints

- Edit `ko/` and `en/` only. Never hand-edit `cn/`, `jp/` or `es/`, since translate-sync handles them.
- ko/en must convey the same content but need not be literal translations. Headers carry `마지막 업데이트: 2026년 11월 19일` and `Last Updated: November 19, 2026`.
- Do not use em dashes (repo style since #353). Use colons, commas or parentheses.
- Quizzes use `<details><summary>정답 보기</summary>` / `Show Answer`, `**정답: X) …**` / `**Answer: X) …**`, and `**설명:**` / `**Explanation:**`. Each quiz needs at least 8 explained questions.
- Every factual claim (quota, default, limit, protocol number, product behavior) must be verified against an official source (AWS docs, RFC, vendor docs) and cited in a closing "참고 자료/References" section. Third-party exam summaries may frame scope only, never facts.
- The AWS edge reference design must match the house rule: CloudFront → **internal** ALB via CloudFront VPC origin → target group. Never show an internet-facing LB, and never show 0.0.0.0/0 ingress on the origin.
- Animations (user choice 2026-11-19: line-art animated SVG, modeled on the line-art-animation skill's look):
  - One self-contained SVG per animation with no JS or external fonts/images, so it plays inline in both GitBook (`<img>`) and VitePress.
  - Look: warm paper background, one thin ink pen (`stroke-linecap/linejoin: round`), slightly curved hand-drawn lines (no ruler-straight cables), one or two flat accents (packet = vermilion, change/highlight = blue). A dark palette via `@media (prefers-color-scheme: dark)` uses pale ink on indigo.
  - Motion: SMIL (`animateMotion` with keyPoints/keyTimes along one combined cable path, `animate` on opacity for captions/tags/notes), all on one shared clock (`dur` = loop length, `repeatCount="indefinite"`). CSS only handles the palette and reduced motion. The packet travels along the cable and carries a small header tag that changes in place at each device (field before→after); numbered step captions highlight as the packet reaches each device. The loop is 10–14 s.
  - `@media (prefers-reduced-motion: reduce)` hides the `.motion` layer and shows a `.static` layer with every step caption.
  - **Approved prototype (user, 2026-11-19): `scripts/line-art/gen_basics_06_part5_anim0.py`.** Every other animation copies its palette tokens, pen filter, stroke classes, font stack, caption layout, tag style and ko/en COPY-dict structure. Each animation gets its own generator `scripts/line-art/gen_<doc-stem-with-underscores>_anim<n>.py` that writes both languages straight into the asset paths; the SVGs are generated output (never hand-edit, regenerate). Import nothing outside the Python stdlib.
  - Files: `<lang>/.gitbook/assets/<lang>-<doc-stem>-anim-<n>.svg` (captions are language-specific). Each has `<title>`/`<desc>` and viewBox `0 0 960 500` (height may grow to 560 if the topology needs it). Font stack as in the prototype.
  - Embed: `![<alt sentence describing the full flow>](../.gitbook/assets/<file>.svg)`, adjusting `../` per depth. The alt text must state every step so the content survives without animation.
  - Verify: `node scripts/line-art/frames.mjs <svg> <outPrefix> <t1,t2,...> [dark] [reduced]` writes PNGs (put them in the SDD workspace, never in the repo); inspect light frames at each device dwell, one dark frame and one reduced-motion frame. `xmllint --noout` must pass.
  - Gate: the first animation (Part 5 anim-0) was approved by the user on 2026-11-19; it is already generated into the asset paths.
- No new test code. Gates are `npm run docs:validate`, animation frame captures, and content review ≥85/100.

## Review Focus

1. **Asset path depth**: expert pages live two levels below the locale (`networking/expert/`), so the PNG link is `../../.gitbook/assets/…`. Check with `node scripts/validate-image-assets.mjs` (part of docs:validate).
2. **Quiz–body drift**: every quiz answer must be stated in its chapter. During self-review, grep each answer's key term in the chapter for both languages.
3. **Cross-chapter duplication**: Part 1 already covers L2 switching/ARP/routing basics, Part 4 covers the cloud mapping, and expert 02 covers BGP policy. Part 5 and 07 must link to those, not re-teach them. Reviewers check that each new section adds device/WAN/edge depth.
4. **Edge reference topology accuracy**: Shield Standard is automatic. WAF on CloudFront is a global web ACL in us-east-1. A VPC origin needs an internal ALB/NLB or EC2 in private subnets. Origin access is restricted by the CloudFront VPC origin security group or the managed prefix list. Each statement is checked against AWS docs at writing time.
5. **Navigation completeness**: each new page needs entries in ko/en `SUMMARY.md` (content and quiz sections), ko/en `README.md`, the expert `README.md` course map and the networking `README.md` learning path. docs:validate parity and coverage checks catch omissions.

---

### Task 1: Foundations Part 5: network devices, LAN and WAN basics

**Files:**
- Create: `ko/basics/06-network-fundamentals-part5.md`, `en/basics/06-network-fundamentals-part5.md`
- Create: `ko/quizzes/basics/06-network-fundamentals-part5-quiz.md`, `en/quizzes/basics/06-network-fundamentals-part5-quiz.md`
- Create: `{ko,en}/.gitbook/assets/{ko,en}-basics-06-network-fundamentals-part5-anim-{0,1}.svg`
- Modify: `{ko,en}/basics/06-network-fundamentals-part4.md` "다음 문서/Next" section → link Part 5

**Interfaces:** Produces anchors `#device-roles`, `#vlan-trunk`, `#stp-lacp-fhrp`, `#lan-topologies`, `#nat-pat-cgnat` and `#wan-types`, which Tasks 2–4 link to.

- [ ] Outline the sections, aligned to CCNA "Network Fundamentals / Network Access / IP Services" and N10-009 domain 1:
  - Device roles: hub, L2 switch, L3 switch, router, firewall/NGFW, load balancer and AP, with the forwarding decision each makes (MAC table, FIB, state table, L7 rules).
  - Collision vs broadcast domains.
  - VLAN and 802.1Q trunk/native VLAN.
  - STP/RSTP purpose, root bridge and blocking.
  - LACP/EtherChannel.
  - First-hop redundancy (VRRP/HSRP).
  - LAN topologies: 2/3-tier vs spine-leaf, linking expert 03 for EVPN.
  - NAT/SNAT/PAT/CGNAT and port exhaustion.
  - WAN types: leased line, MPLS L3VPN, broadband internet, LTE/5G, SD-WAN overview; details deferred to expert 07.
  - A "클라우드에서는" closing table: VPC route table, IGW/NAT GW, TGW, security group vs NACL.
- [ ] Diagram 0 : one frame from PC-A in VLAN 10 crossing an access switch (MAC learning, 802.1Q tag on trunk) to an L3 switch/router (TTL−1, new L2 header) to PC-B in VLAN 20. Diagram 1 : PAT translation table for two inside hosts sharing one public IP, then a return packet.
- [ ] Write the ko and en bodies with verified references (IEEE 802.1Q, RFC 5798 VRRPv3, RFC 3022 NAT, RFC 6598 shared address space, AWS VPC docs).
- [ ] Write the quizzes (≥8 each, explained). Cover at least: switch vs router decision, broadcast domain count, native VLAN, STP purpose, PAT port exhaustion, CGNAT 100.64.0.0/10, SG stateful vs NACL stateless, spine-leaf hop count.
- [ ] anim-0 is done (approved prototype). Build anim-1 with its own generator, the ko/en caption variants, frame captures and embeds.
- [ ] Run `npm run docs:validate > $LOG 2>&1` and grep `# fail 0`. Commit.

### Task 2: Expert 07: WAN and hybrid connectivity design

**Files:**
- Create: `{ko,en}/networking/expert/07-wan-hybrid-connectivity.md`
- Create: `{ko,en}/quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md`
- Create: `{ko,en}/.gitbook/assets/{ko,en}-networking-expert-07-wan-hybrid-connectivity-anim-0.svg`

**Interfaces:** Consumes Part 5 `#wan-types` and `#nat-pat-cgnat`, and expert 02 (BGP policy). Produces `#failover-design`, which expert 05 and 06 can reference.

- [ ] Follow the expert workbook shape (`02-routing-policy-convergence.md`): purpose and entry conditions → readings mapped to ENCOR (architecture/SD-WAN) and ANS-C01 Domain 1/2 → concepts → design exercise → failure/recovery observation → deliverables and completion criteria.
- [ ] Content:
  - Underlay/overlay WAN; MPLS vs internet vs SD-WAN control/data plane.
  - IPsec site-to-site (IKEv2, two tunnels per AWS VPN connection, BGP vs static).
  - Direct Connect (dedicated/hosted, private/transit/public VIF, LAG, MACsec where supported).
  - Transit Gateway attachments and route tables.
  - Failover: DX primary with VPN backup, BGP path selection (AS_PATH prepend, local preference, longest prefix), BFD.
  - MTU/MSS across tunnels.
  - Bandwidth/latency/cost trade-off table.
  - Design exercise: two-site + one-region hybrid with stated SLO; candidate records the expected path and failover time and verifies with a desk check. No real infrastructure is created; the readiness note says lab cost is the learner's own.
- [ ] Animation: on-prem router → DX location → DX gateway/TGW → VPC (primary), plus a dashed IPsec VPN backup over the internet; the packet reroutes to the VPN when the DX link is cut.
- [ ] Write the ko/en bodies and quizzes (≥8). Verify every AWS limit/behavior against the DX, Site-to-Site VPN and TGW user guides.
- [ ] Build the animations (ko/en), verify the frame captures, run docs:validate, and commit.

### Task 3: Expert 08: CDN and edge delivery

**Files:**
- Create: `{ko,en}/networking/expert/08-cdn-edge-delivery.md`
- Create: `{ko,en}/quizzes/networking/expert/08-cdn-edge-delivery-quiz.md`
- Create: `{ko,en}/.gitbook/assets/{ko,en}-networking-expert-08-cdn-edge-delivery-anim-{0,1}.svg`

**Interfaces:** Consumes Part 3 (HTTP/DNS caching) and Part 2 (TLS). Produces `#edge-origin-path`, used by Task 4.

- [ ] Content:
  - Why CDN: RTT, offload, absorption.
  - Request steering: DNS-based vs Anycast (BGP).
  - Cache hierarchy: edge POP → regional edge cache → origin shield → origin.
  - Cache key design (path, query, headers, cookies) and hit ratio.
  - TTL and `Cache-Control`/`s-maxage`/`stale-while-revalidate`, plus invalidation vs versioned URLs.
  - TLS at edge and to origin.
  - Dynamic acceleration, HTTP/2 and HTTP/3 at the edge.
  - CloudFront mapping: cache/origin request policies, OAC for S3, VPC origin to an internal ALB.
  - Observability: hit ratio, `x-cache`, `Age`, origin latency.
  - Exercise: read `curl -sI` headers twice against a public CDN-served asset and explain miss→hit/`Age`. Use a public site, so no resource creation is needed.
- [ ] Animation: client → DNS/Anycast edge → edge cache MISS → regional cache → origin (internal ALB via VPC origin) → response cached; second request HIT returns from the edge.
- [ ] Write the ko/en bodies and quizzes (≥8). Verify against the CloudFront developer guide and RFC 9111.
- [ ] Build the animations (ko/en), verify the frame captures, run docs:validate, and commit.

### Task 4: Expert 09: Edge security (WAF and DDoS)

**Files:**
- Create: `{ko,en}/networking/expert/09-edge-security-waf-ddos.md`
- Create: `{ko,en}/quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md`
- Create: `{ko,en}/.gitbook/assets/{ko,en}-networking-expert-09-edge-security-waf-ddos-anim-0.svg`

**Interfaces:** Consumes Task 3 `#edge-origin-path` and beginner 06 (host firewalls). Links to `security/` and `networking/03-aws-lb-controller.md` for the Ingress side.

- [ ] Content:
  - Threat layers: volumetric L3/4 (UDP reflection, SYN flood) vs L7 (HTTP flood, OWASP Top 10, bots, credential stuffing).
  - Where each is stopped: Anycast absorption/scrubbing, SYN cookies, WAF, application auth.
  - WAF model: web ACL, rule groups (managed/custom), actions (allow/block/count/CAPTCHA/challenge), rate-based rules, labels, count-mode rollout and false-positive tuning.
  - AWS Shield Standard vs Advanced.
  - Defense-in-depth reference: CloudFront (+Shield, WAF global web ACL) → VPC origin → internal ALB (SG allows only the CloudFront VPC-origin SG/prefix list) → Ingress/Pod with NetworkPolicy.
  - Origin cloaking (why a publicly reachable origin bypasses edge controls).
  - Logging and metrics (WAF logs, sampled requests).
  - Exercise: write a rule plan in count mode with expected matches and a rollback trigger (desk exercise, no deployment).
- [ ] Animation: requests from internet clients and a botnet hit the edge. A volumetric flow is absorbed at Shield/edge, an L7 attack is blocked by a WAF rate/managed rule, and legitimate traffic flows through VPC origin → internal ALB → Ingress → Pod.
- [ ] Write the ko/en bodies and quizzes (≥8). Verify against the AWS WAF/Shield developer guides, CloudFront VPC origins docs and the OWASP Top 10 2021 page.
- [ ] Build the animations (ko/en), verify the frame captures, run docs:validate, and commit.

### Task 5: Course integration

**Files:**
- Modify: `{ko,en}/SUMMARY.md` (Part 5 under the network fundamentals parent; expert 7–9 under 네트워크 전문가 과정; four quiz entries in the quiz tree)
- Modify: `{ko,en}/README.md` (TOC lines with quiz links)
- Modify: `{ko,en}/networking/expert/README.md` (course map rows 7–9, entry-check bullet for Part 5)
- Modify: `{ko,en}/networking/README.md` (learning-path rows for devices/LAN and edge/WAN)
- Modify: `.github/news-topic-map.yml` (keywords → docs): `[cloudfront, cdn, edge cache, origin shield]` → expert 08; `[aws waf, aws shield, ddos, bot control]` → expert 09; `[direct connect, site-to-site vpn, transit gateway, sd-wan]` → expert 07

- [ ] Add all entries following the neighboring lines' exact format.
- [ ] Run `npm run docs:validate > $LOG 2>&1`; expect `# fail 0` and exit 0. Commit.

### Task 6: Review and publication

- [ ] Run the content-review-agent on all changed ko/en pages and quizzes (target ≥85/100). Fix Critical/Major findings and re-review.
- [ ] Before building, check `free -g`/`df -h /home`. Then run `NODE_OPTIONS=--max-old-space-size=8192 npm run docs:build > $LOG 2>&1` and grep for errors. Open the new pages and confirm the SVGs animate inline (light/dark) in the built site.
- [ ] Push branch `docs/network-devices-wan-edge`, open the PR with validation evidence, and wait for CI green. Do not merge without the user.
