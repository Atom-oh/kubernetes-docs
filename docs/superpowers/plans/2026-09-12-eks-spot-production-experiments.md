# EKS Spot Production Experiments Plan and Execution Record

> **For agentic workers:** Preserve measured evidence, use the repository's validation suite, and obtain independent review of the final committed HEAD before integration.

**Goal:** Run isolated EKS Spot experiments and document production-adoption criteria, observed results, limitations, and recovery procedures in Korean and English.

**Architecture:** Dedicated test namespace, two Karpenter NodePools, and an EC2NodeClass; synthetic HTTP control, mixed-capacity, and shared Spot-cohort paths. FIS targets one newly created Spot instance. All experiment resources are removed after evidence export.

**Tech Stack:** Kubernetes, Karpenter, AWS FIS, CloudWatch, EventBridge/SQS, Python standard-library probes, Markdown, VitePress, and an optional Matplotlib chart.

**Spec:** User requested EKS Spot experiments/results for production use, then designated the current EC2's `default` profile, `ap-northeast-2`, and `fsi-demo-cluster`. The user separately authorized disk-space cleanup.

## Constraints

- Preserve the existing checkout's work; changes are isolated in `/home/atomoh/kubernetes-docs-eks-spot`.
- Existing workloads, shared Karpenter configuration, node IAM role, subnets, and security group are not modified.
- Inject faults only into the tagged experiment instance after validating its node, Pod ownership, capacity type, and stop alarm.
- Publish synthetic request evidence and sanitized metadata; keep infrastructure identifiers and detailed originals in access-controlled local records.
- Distinguish actual measurements from example thresholds, price snapshots, and untested scenarios.
- Edit Korean/English sources; do not hand-edit translated mirrors.
- Require independent current-HEAD review, content quality gate, and passing CI before merge.

## Executed work

- [x] Add paired operations chapter 17, quizzes, navigation, and scaling crosslinks.
- [x] Validate source claims against AWS, Kubernetes, and Karpenter documentation.
- [x] Create and test bounded, rate-scheduled HTTP probes and deterministic offline analysis.
- [x] Run E0 steady load, E1 drain, E2 single Spot interruption, E6 blocking-PDB control, and E4 explicit On-Demand transition.
- [x] Preserve raw requests, summaries, timing evidence, and the scope of every observation.
- [x] Record unsupported Karpenter/Kubernetes pairing and missing interruption-queue configuration without upgrading the shared controller.
- [x] Export evidence and verify zero remaining live experiment instances, volumes, or Kubernetes resources; remove the experiment role/profile/template/alarm/rule/queue.
- [x] Reclaim inactive generated documentation builds and Go/pip caches; preserve in-use uv environments.

## Deliberately unvalidated production criteria

Concurrent reclamation, full AZ failure, abrupt loss/notice-delivery failure variants, real capacity-error automatic fallback, peak/HPA behavior, business correctness, repeated samples, external load balancers, and actual billing were not validated. Each measured scenario ran once. These limitations support a hold on production expansion; they are not passing results.

## Integration verification

Run `npm run docs:validate`, the Python `test_*.py` suite, raw-data integrity/recomputation checks, and `npm run docs:build`. Review the resulting pages/chart and final patch, fix material findings, then create and merge the PR only after current-HEAD review and CI pass. The PR and final report record the integration outcome.
