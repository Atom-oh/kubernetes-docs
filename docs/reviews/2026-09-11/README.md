# Full content review — in progress

This is a progress report, not a claim that the full corpus has been semantically reviewed.

- Initial inventory: 2701 Markdown documents across five languages; current inventory includes 2707 after restoring deleted translations.
- Fully read source/quiz/lab files recorded so far: 364 (354 fixed, 0 verified, 10 with follow-up).
- Source files are maintained in Korean and English; translations are checked structurally and repaired through automation.

| Batch | Files recorded | Fixed | Verified | Follow-up |
|---|---:|---:|---:|---:|
| [argocd-applications](batches/argocd-applications.json) | 4 | 4 | 0 | 0 |
| [argocd-appsets](batches/argocd-appsets.json) | 4 | 4 | 0 | 0 |
| [argocd-best-practices](batches/argocd-best-practices.json) | 4 | 4 | 0 | 0 |
| [argocd-experiment](batches/argocd-experiment.json) | 4 | 4 | 0 | 0 |
| [argocd-foundation](batches/argocd-foundation.json) | 8 | 8 | 0 | 0 |
| [argocd-notifications](batches/argocd-notifications.json) | 4 | 4 | 0 | 0 |
| [argocd-projects-rbac](batches/argocd-projects-rbac.json) | 4 | 4 | 0 | 0 |
| [argocd-security](batches/argocd-security.json) | 4 | 4 | 0 | 0 |
| [argocd-sync](batches/argocd-sync.json) | 4 | 4 | 0 | 0 |
| [argocd-traffic](batches/argocd-traffic.json) | 4 | 4 | 0 | 0 |
| [autoscaling-scheduling](batches/autoscaling-scheduling.json) | 24 | 24 | 0 | 0 |
| [basics](batches/basics.json) | 36 | 36 | 0 | 0 |
| [container-registry](batches/container-registry.json) | 18 | 18 | 0 | 0 |
| [core-foundation](batches/core-foundation.json) | 24 | 24 | 0 | 0 |
| [core-rest](batches/core-rest.json) | 20 | 20 | 0 | 0 |
| [eks-creation-overview](batches/eks-creation-overview.json) | 2 | 2 | 0 | 0 |
| [eks-creation-part1](batches/eks-creation-part1.json) | 4 | 4 | 0 | 0 |
| [eks-creation-part2](batches/eks-creation-part2.json) | 4 | 4 | 0 | 0 |
| [eks-creation-part3](batches/eks-creation-part3.json) | 2 | 0 | 0 | 2 |
| [eks-introduction](batches/eks-introduction.json) | 4 | 4 | 0 | 0 |
| [feature-flags](batches/feature-flags.json) | 4 | 0 | 0 | 4 |
| [flagger](batches/flagger.json) | 4 | 4 | 0 | 0 |
| [flux](batches/flux.json) | 4 | 4 | 0 | 0 |
| [gitops-overviews](batches/gitops-overviews.json) | 6 | 6 | 0 | 0 |
| [intro-guides](batches/intro-guides.json) | 10 | 10 | 0 | 0 |
| [istio-advanced](batches/istio-advanced.json) | 24 | 24 | 0 | 0 |
| [istio-comparison](batches/istio-comparison.json) | 10 | 10 | 0 | 0 |
| [istio-foundation](batches/istio-foundation.json) | 16 | 16 | 0 | 0 |
| [istio-observability](batches/istio-observability.json) | 12 | 12 | 0 | 0 |
| [istio-resilience](batches/istio-resilience.json) | 10 | 10 | 0 | 0 |
| [istio-security](batches/istio-security.json) | 10 | 10 | 0 | 0 |
| [istio-traffic](batches/istio-traffic.json) | 30 | 30 | 0 | 0 |
| [istio-troubleshooting](batches/istio-troubleshooting.json) | 2 | 2 | 0 | 0 |
| [labs-foundations](batches/labs-foundations.json) | 14 | 14 | 0 | 0 |
| [mesh-linkerd](batches/mesh-linkerd.json) | 10 | 6 | 0 | 4 |
| [mesh-other-istio-overview](batches/mesh-other-istio-overview.json) | 4 | 4 | 0 | 0 |
| [storage-database](batches/storage-database.json) | 12 | 12 | 0 | 0 |

## Mechanical findings

- All 2,075 initially referenced local image files decoded or parsed successfully.
- Initial translated sources referenced 514 missing local images. The latest whole-corpus inventory reports zero missing local image references after exact original restores and English-owned asset synchronization; translated prose has not been manually rewritten.
- 30 unique external image URLs checked: 19 returned 404.
- 1,118 unique external documentation URLs checked: 128 returned 404/410 and 30 were unverified (access/network restrictions). These need contextual disposition.
- Same-repository absolute GitHub links are now included in local link checks.
- Korean manual TOC fragment normalization is corrected at rendering time.
- Translation sync now restores failed destination files rather than committing deletions.

## Scope limits

- Infrastructure examples have not been executed against AWS accounts.
- Historical benchmark results must retain the versions actually measured.
- A reachable URL or valid image file does not prove the surrounding technical claims; those remain pending until their per-document review row is complete.
