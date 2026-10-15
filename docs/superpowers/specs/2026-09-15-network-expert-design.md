# Expert networking study and practice path

## Goal and audience

Extend the beginner networking course into an evidence-driven expert study path. The user approved proceeding with the researched CS168, BGP Labs, Bootlin, netlab EVPN, Cisco and AWS learning direction. Readers should connect protocol mechanics, routing policy, Linux internals and cloud design, then demonstrate diagnosis and recovery rather than merely recognize terminology.

This is a documentation change. It does not enroll anyone in training, reproduce third-party course solutions, or create infrastructure.

## Course structure

Add mirrored `ko/networking/expert/` and `en/networking/expert/` trees:

1. `01-protocol-projects.md`: CS168 reading/project mapping; protocol invariants, traceroute/ICMP evidence, TCP/HTTP/DNS/TLS/QUIC distinctions, own project deliverables and negative cases. CS144 is an optional C/C++ implementation continuation, without claiming a working public lab link or open enrollment.
2. `02-routing-policy-convergence.md`: IGP/OSPF and BGP roles, eBGP/iBGP, next-hop reachability, RIB versus FIB, filters/attributes/RR, BGP Labs progression, a scoped policy/failure/convergence workbook.
3. `03-datacenter-evpn.md`: VLAN/underlay/overlay prerequisites, VXLAN/VTEP/VNI, RD versus RT, EVPN route roles, VRFs and IRB, a provider-compatible lab selection and isolation/failure workbook.
4. `04-linux-performance.md`: packet-path and Linux measurement workbook; socket queues/windows, NAPI/RSS/offloads/qdisc, latency/throughput/loss, eBPF/XDP observation, bounded experiment design and rollback.
5. `05-cloud-cni-design.md`: cloud/hybrid design and Kubernetes packet-path workbook; AWS study-domain mapping, DNS and routing boundaries, CNI/LB/control-plane distinctions, scoped read-only inventory and design/fault-analysis exercises.
6. `06-automation-capstone.md`: intent and negative assertions, normalized evidence contract, automation/review workflow, failure/recovery capstones, reproducibility and assessment rubric.

Each chapter has a paired quiz with at least eight explained questions. Add a course README with entry criteria, a common progression, cloud/SRE versus enterprise/data-center specializations, public-material and paid/hardware-dependent resource distinctions, and an evidence portfolio checklist.

## Lab and accuracy contract

- New content is a study/workbook layer over existing protocol, kernel, Calico/Cilium, EKS and benchmark guides; link to those guides instead of duplicating them wholesale.
- Core host baseline is the beginner course's disposable Ubuntu Server 24.04 LTS or Rocky Linux 9 VM. A netlab/containerlab experiment uses its own disposable Linux lab VM and the upstream tool/provider requirements; neither that environment nor cloud configuration is assumed to exist.
- Every active experiment identifies its environment, tools/packages, version or immutable upstream revision, privilege, owned resources, traffic scope, baseline, success/failure observations and exact restoration.
- Use public upstream installation/project instructions as declared prerequisites when they own the environment. Explain how to verify readiness and record the tool version/revision. Never invent a universal compatible image/version matrix.
- Keep routing/fabric labs local to owned disposable environments; preserve management connectivity. Never use global Docker prune, all-lab teardown, unscoped route/firewall flushes, global sysctl/qdisc changes, or cloud failure injection as a default.
- No network/cloud configuration is executed by the authoring agent. Safe local syntax checks and isolated sample-data validation may be run. Do not claim native routing, EVPN, kernel, cloud or hardware experiments passed unless actually observed.
- Cloud commands are read-only and explicitly scoped by context, namespace, region/profile and resource identifiers. Do not dump secrets or require elevated access merely to complete an observation.
- Distinguish proposed, illustrative, recorded and newly measured evidence. Empty output, missing telemetry and an established BGP session are not proof that all intended traffic works.
- Source factual claims from primary project/university/vendor documentation. Date resource availability checks; avoid promising all course recordings, graders, enrollment, hardware labs or router images are freely available.
- Keep Korean/English substance and commands aligned. Do not hand-edit `cn/`, `jp/`, or `es/`.

## Integration

Register all new pages and quizzes in both SUMMARY/README pairs. Link the expert course from both networking overviews and from the beginner README and capstone. Preserve every existing route.

The published course must make its next action clear: what to read, what to reproduce, what evidence to save, what a failure means, and which condition permits moving on.

## Acceptance

Run repository documentation validation, static snippet and bilingual checks, and the existing network-example tests. Build both locales and test actual built pages, anchors, course/lesson/quiz navigation and answer disclosures on desktop/mobile. Use document-ready state rather than network-idle alone for SPA navigation.

Require independent full changed-file content coverage and at least 85/100 quality before deployment. Resolve Critical/Major issues and re-review the actual latest HEAD, require all CI and protection conditions, check the intended main/predecessor path, merge under standing user authorization, then verify deployment and live pages.
