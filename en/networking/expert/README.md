# Expert Networking Study Path

> **Resources checked**: September 15, 2026
>
> **Environment**: Disposable Ubuntu Server 24.04 LTS or Rocky Linux 9 VMs for host exercises. Routing/EVPN tools and cloud environments have separate chapter prerequisites.

These advanced workbooks follow the [beginner course](../beginner/README.md). Connect protocol principles to code and packets, then evaluate routing policy, Linux performance and cloud designs using evidence.

The expert-level objective is to **define what should be true, test hypotheses with observations, and explain a change's impact and recovery**. A fixed period of study or a certification alone does not guarantee that ability.

## Entry check {#entry-check}

Proceed to chapter 1 when you can explain and reproduce the following:

- Distinguish IP, subnet, gateway and DNS roles from MAC/ARP.
- Read `ip route get`, `ss` and a bounded `tcpdump` capture, identifying the observation point.
- Verify SSH key access and the lab firewall policy, then restore the previous state.
- Distinguish an HTTP error, connection failure and name-resolution failure.
- Separate management and experiment paths and identify your own files, VMs and containers.

Use the [beginner capstone](../beginner/08-container-cloud-capstone.md) to revisit missing skills. Complete [guest tool preparation](../beginner/README.md#guest-tools) when a host command is unavailable.

## Six workbooks {#course-map}

Each row follows **reading → experiment or design validation → evidence → explained quiz**. External courses supply reading scope; these workbooks supply a way to assess your own results.

| Order | Workbook | Deliverable |
|---|---|---|
| 1 | [Protocol and implementation projects](01-protocol-projects.md) · [Quiz](../../quizzes/networking/expert/01-protocol-projects-quiz.md) | Request path, probe/response correlation, protocol boundaries and edge cases |
| 2 | [Routing policy and convergence](02-routing-policy-convergence.md) · [Quiz](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md) | Intended advertisements/selection, RIB/FIB and forwarding evidence, failure/recovery timeline |
| 3 | [Data-center EVPN/VXLAN](03-datacenter-evpn.md) · [Quiz](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md) | Underlay/overlay mapping, allowed/forbidden VRF flows, routes and encapsulation evidence |
| 4 | [Linux packet paths and performance](04-linux-performance.md) · [Quiz](../../quizzes/networking/expert/04-linux-performance-quiz.md) | Time-correlated queues, counters and packets; measurement limits and recovery |
| 5 | [Cloud and CNI design](05-cloud-cni-design.md) · [Quiz](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) | Design and evidence from DNS to backend and return path |
| 6 | [Automation and final assessment](06-automation-capstone.md) · [Quiz](../../quizzes/networking/expert/06-automation-capstone-quiz.md) | Evidence and change review covering normal, forbidden, failed and recovered states |

Existing references remain useful: [protocol foundations](../../basics/06-network-fundamentals-part1.md), [kernel networking](../../kernel/02-network-stack.md), [Calico BGP](../calico/04-bgp-deep-dive.md), [Cilium](../cilium/README.md), and [VPC CNI](../01-vpc-cni.md).

## Choose a specialization {#tracks}

| Direction | Priority order | Further depth |
|---|---|---|
| Cloud networking/SRE | 1 → 2 → 4 → 5 → 6 | Performance and failures across CNI, DNS, load balancers and hybrid boundaries |
| Enterprise/data center | 1 → 2 → 4 → 3 → 6 | Check remaining L2/L3, security, virtualization and automation topics against Cisco's official scope |
| Protocol/network software | 1 → 2 → 4 → 6 | Transport and kernel implementation projects after establishing C/C++ foundations |

Chapters 1, 2 and 4 are common prerequisites. Add chapter 3 for the data-center path or chapter 5 for cloud. The protocol/Linux path can use chapter 4's host experiment for the corresponding chapter 6 assessment. Complete the assessment in the selected scope, then add another specialization. Allocate time for environment preparation, failed attempts, reproduction and reporting as well as reading.

## Lab boundaries and ownership {#lab-contract}

Do not execute every chapter sequentially in one environment.

| Environment | Preparation and boundary | Check before completion |
|---|---|---|
| Host observation | Disposable beginner-course VM, installed tools, your own traffic | Interface/process/capture scope, duration, cleanup of your files |
| Routing/EVPN | Separate Linux lab VM and selected netlab/provider installation/image requirements | Upstream revision, tool/image versions, owned lab ID/resources and recovery commands |
| Cloud | Approved existing lab account/cluster and read permissions | Account, region, context, namespace, resource owner, cost/permission/validation scope |
| Design/supplied evidence | Stated assumptions and input evidence without necessarily having the equipment | Distinguish design review from live traffic validation and mark unobserved items |

Do not copy a netlab/containerlab device's addresses or names onto a beginner VM's NIC. Some exercises require commercial NOS images, virtualization support or additional boards: **check each chapter and upstream prerequisites first**. Global Docker prune, teardown of other labs and production failure injection are not default steps in this course.

Create this record before every experiment. Recording versions and revisions means capturing the actual inputs; it does not guarantee compatibility between arbitrary combinations.

| Record | Example form |
|---|---|
| Experiment ID and owner | An ID you can distinguish and the responsible role |
| Environment/permission | Local VM, lab container, or approved cloud read-only access |
| Topology | Nodes, interfaces, addresses, VRFs, observation and management paths |
| Tools/inputs | OS, kernel, tool and image versions; upstream commit; input-file hashes |
| Traffic scope | Source, destination, protocol, ports and maximum duration |
| Baseline | Routes, policy, service state and recovery configuration |
| Hypothesis/change | Expected outcome and the single item to change |
| Stop/recovery criteria | Management failure, unexpected resources, restoration and recheck |

## Selecting official resources {#resources}

These are learning directions checked on September 15, 2026. Confirm access to semester materials, enrollment, graders and scheduled training separately.

| Resource | Role in this course | Before using it |
|---|---|---|
| [Berkeley CS168](https://www.cs168.io/) | Structure for Internet architecture, routing, transport, data centers and projects | Select a populated public semester and check access to descriptions, code and grading separately |
| [BGP Labs](https://bgplabs.net/) | Progressive BGP configuration, policy and failure practice | Check [installation](https://bgplabs.net/install/), lab revision and provider/image requirements |
| [netlab EVPN](https://netlab.tools/module/evpn/) | EVPN/VRF/IRB design and feature-support validation | Verify the selected devices support the required feature and data-plane setup |
| [Bootlin Linux Networking](https://bootlin.com/training/networking/) | Kernel, driver, user-space and performance depth | Separate public material from paid training; check C/kernel and board requirements |
| [Cisco Enterprise Infrastructure](https://www.cisco.com/site/us/en/learn/training-certifications/certifications/enterprise/ccie-enterprise-infrastructure/index.html) | Check enterprise design, operations and automation coverage | Select the current official blueprint; FRR does not reproduce every commercial device or ASIC behavior |
| [AWS Advanced Networking](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html) | Scope for cloud/hybrid design, implementation, operations and security | Separate exam preparation from deployment; establish account, access, cost and cleanup conditions |
| [Stanford CS144](https://online.stanford.edu/courses/cs144-introduction-computer-networking) | Optional C/C++ direction for protocol implementation | Verify current enrollment, public assignments and repository availability |

This repository does not supply private course materials or solutions. Read the project requirements and produce your own implementation, tests and design justification.

## Interpreting evidence {#evidence-rules}

- **Measured:** Observed in your stated environment, time window and traffic.
- **Supplied:** Collected by someone else; record provenance, scope and relation to the original.
- **Illustrative/synthetic:** Inputs explaining a calculation or validator. Do not report them as successful real traffic.
- **Design assumption:** An untested design condition. Keep it marked unverified.

Absent observations are `unknown`. Empty routing output, missing packets and a `ping` timeout alone do not establish policy denial or an end-to-end root cause. An established BGP session does not establish the intended prefixes or forwarding behavior.

## Final portfolio {#portfolio}

Connect these deliverables in your own environment:

1. Forward and return paths for one request, including observation points.
2. Evidence for both normal traffic and **traffic that must be forbidden**.
3. Before/during/after records for one fault or policy change.
4. Measurement conditions, missing evidence and rejected hypotheses.
5. A narrow change and post-recovery verification.
6. [Final-assessment](06-automation-capstone.md) automation results and their human-review limits.

Keep original evidence in an approved location and use consistent aliases in public notes. Do not publish raw packets, logs, accounts or topology inventories indiscriminately.

**Next:** [Chapter 1 — Protocol and implementation projects](01-protocol-projects.md)
