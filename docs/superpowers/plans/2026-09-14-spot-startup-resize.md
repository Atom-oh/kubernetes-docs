# Spot startup CPU and Guaranteed QoS documentation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Connect the existing phase-aware CPU resize design to the Spot experiment guide without changing historical results or claiming an unmeasured performance improvement.

**Architecture:** The workload template supplies startup CPU with equal requests and limits. The existing opt-in MutatingAdmissionPolicy supplies missing resize policies; the namespace-scoped prototype requests CPU downscale after a real startupProbe succeeds. The guide distinguishes admission, resize requests, kubelet application, and application SLO evidence.

**Tech Stack:** Markdown, Kubernetes 1.36 MAP, container-level in-place resize, the existing Go resizer prototype, standard-library Spot measurement tools.

**Spec:** User request for `ko/ops/17-spot-production-experiments.md`; existing implementation contract in section 4.8 of `ko/eks/12-kubernetes-version-roadmap.md`.

## Global constraints

- Preserve all E0–E9 IDs, measured request counts, latencies, error rates, timelines, images, and raw result artifacts.
- Container-level in-place resize became stable in 1.35; MutatingAdmissionPolicy became stable in 1.36. MAP is an in-process alternative to an external mutating webhook.
- The scoped design starts Guaranteed and stays Guaranteed; CPU and memory requests equal limits for every applicable container. Resizing cannot change the original QoS class.
- The existing prototype changes regular-container CPU only. Require its Linux, namespace, opt-in, startupProbe, resource-policy, and steady-floor conditions.
- A Running Pod, a successful PATCH, unchanged containerID, or Guaranteed QoS alone does not prove application initialization, resize completion, or an SLO.
- Treat 200m → 50m with fixed 64Mi memory as illustrative values inherited from the roadmap. Do not publish a startup-speedup number.
- Add E10 for the combined startup/resize/Spot test and mark it NOT RUN.
- Preserve the distinction between the old EKS 1.36.1 report, the locally tested prototype, and the 2026-09-12 Spot dataset.
- No cloud provisioning, fault injection, or controller deployment is part of this documentation repair.
- Keep Korean and English content and quiz answers aligned. Existing cn/jp/es counterparts do not exist for these two pages, so translate-sync has no corresponding files to update.

## Task 1: Explain the design and the missing experiment

**Files:**
- Modify: `ko/ops/17-spot-production-experiments.md`
- Modify: `en/ops/17-spot-production-experiments.md`
- Modify: `examples/eks/spot-production/README.md`
- Modify: `ko/quizzes/ops/17-spot-production-experiments-quiz.md`
- Modify: `en/quizzes/ops/17-spot-production-experiments-quiz.md`

- [x] Add an early link to `#phase-aware-resizing` and a dedicated section covering template → MAP → startupProbe → pods/resize → observed resources.
- [x] Use three illustrative Guaranteed profiles: G-steady 50m→50m, G-phase 200m→50m, and G-high 200m→200m; all retain 64Mi request=limit.
- [x] Specify the existing namespace-scoped label/annotation contract, the CPU-only scope, and startupProbe requirements without duplicating or changing the controller.
- [x] Add E10 acceptance criteria and desired-versus-observed resource, generation, identity, restart, readiness, throttling, and request-SLO evidence.
- [x] Explain that the old public Spot template uses requests 50m/64Mi and limits 500m/256Mi, with no phase-aware opt-in or startupProbe. Do not infer a new runtime observation from that initial template.
- [x] Link the roadmap and primary resize, QoS, MAP, and probe references.
- [x] Add three matching quiz questions: QoS preservation, startup/resize completion, and the limits of the existing measurement.

## Task 2: Verify, review, and publish

- [x] Compare all pre-existing experiment-result artifacts against the base Git tree.
- [x] Check new links/anchors, the 10 paired quiz answers, and the read-only observation command's Bash syntax.
- [x] Run `npm run docs:validate`.
- [x] Run `python3 -B -m unittest discover -s examples/eks/spot-production -p 'test_*.py'`.
- [x] Record source receipts and bounded verification in `docs/reviews/2026-09-14/spot-startup-resize-validation.json`.
- [ ] Obtain complete latest-HEAD independent content review with score at least 85 and no unresolved Critical/Major findings.
- [ ] Create the PR, inspect latest-HEAD inline feedback and all five required CI jobs, and merge when the user's standing conditions pass.
- [ ] Verify deployment of the changed page and synchronize the original clean main checkout.
