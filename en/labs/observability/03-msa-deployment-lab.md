# Part 3: MSA deployment and canary

<span id="application-structure"></span>
<span id="architecture-overview"></span>
<span id="canary-state-diagram"></span>
<span id="cleanup"></span>
<span id="exercise-1-msa-application-overview"></span>
<span id="exercise-2-karpenter-nodepool-configuration"></span>
<span id="exercise-3-keda-scaledobject-configuration"></span>
<span id="exercise-4-argocd-application-deployment"></span>
<span id="exercise-5-opentelemetry-auto-instrumentation"></span>
<span id="exercise-6-argo-rollouts-canary-deployment"></span>
<span id="exercise-7-intentional-failure-and-automatic-rollback"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="prerequisites"></span>
<span id="references"></span>
<span id="repository-structure"></span>
<span id="sample-code-snippets"></span>
<span id="service-call-flow"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="summary"></span>
<span id="troubleshooting"></span>
<span id="verification"></span>
<span id="verification-1"></span>
<span id="verification-2"></span>
<span id="verification-3"></span>
<span id="verification-4"></span>
<span id="verification-5"></span>

> **Difficulty**: Advanced
> **Last Updated**: September 13, 2026
Deploy five runnable Python roles as separate workloads. The [application README](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application) defines code, DB, image and chart inputs. Payments and notifications are synthetic; no actual charge or email/SMS is sent.

![Separate workloads, transactional outbox, SNS fanout and consumers](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-10.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-10.html)

## 1. Shared API and persistence contracts {#contracts}

| Request/role | Contract |
|---|---|
| `POST /orders` | 201 + `id`; order and outbox commit together |
| `POST /payments` | 200 + `status: completed`; same order/amount/method is idempotent |
| `GET /orders/{id}` | 200 + same ID, or404 |
| `notification` | Own SQS queue, persisted synthetic notification |
| `analytics` | Separate SQS queue, independent persisted result |

W3C context crosses gateway/service HTTP and producer/consumer boundaries. A crash after outbox publication but before the DB mark causes redelivery, so consumers deduplicate event IDs transactionally. This does not make external email/payment effects exactly once. General Idempotency-Key handling for order POST is not included.

App metrics are `lab_http_requests_total` and `lab_http_request_duration_seconds`, labeled by service/route/status/revision. JSON logs carry service/level/trace_id/span_id; customer/payment payloads are not metric labels.

## 2. Database file and image {#image-database}

Use Part1’s dedicated runtime account/private connection file. Pod paths are `/run/database-ca/global-bundle.pem` and `/run/database/connection.json`; mount the connection file and public RDS CA separately as Secret/ConfigMap.

```bash
cd examples/labs/observability/application
kubectl --context service create namespace msa --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context service -n msa create secret generic lab-database --from-file=connection.json="$LAB_STATE/runtime-pod-connection.json"
kubectl --context service -n msa create configmap lab-database-ca --from-file=global-bundle.pem="$LAB_STATE/global-bundle.pem"
docker build -t "$IMAGE_REPOSITORY:$IMAGE_TAG" .
docker push "$IMAGE_REPOSITORY:$IMAGE_TAG"
```
Use the immutable version selected in Part1. Update existing Secrets through the organization’s rotation procedure without printing values or placing them in chart files. The Dockerfile pins a base digest, UID10001 and a bounded build context.

## 3. Install controllers and chart {#deployment}

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install keda kedacore/keda --version 2.20.2   --kube-context service -n keda --create-namespace -f "$LAB_STATE/helm-inputs/keda.yaml"
helm upgrade --install argo-rollouts argo/argo-rollouts --version 2.43.1   --kube-context service -n argo-rollouts --create-namespace
helm upgrade --install observability-lab ./chart --kube-context service -n msa   -f "$LAB_STATE/helm-inputs/application.yaml"
kubectl --context service -n msa get deployment,rollout,pods,svc,scaledobject
```
Verify all five ServiceAccounts and IRSA subjects. Gateway has no AWS role; publishers access SNS, consumers their own queues, and KEDA only queue attributes. Do not configure duplicate Pod Identity/IRSA paths on a workload. Readiness checks DB/schema, not successful SQS/IAM delivery.

ServiceMonitor labels match the service Prometheus release and `honorLabels` preserves the app service label. Managed node groups can run the baseline; add Karpenter only after its [separate guide](../../autoscaling/02-karpenter.md) verifies IAM/discovery/EC2NodeClass/AMI/taints.

![Deployment and observability across management/service scopes](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-0.html)

## 4. Verify HTTP and asynchronous processing {#verify}

```bash
kubectl --context service -n msa port-forward svc/api-gateway 8080:8080
# Run in another terminal from the repository root:
BASE_URL=http://127.0.0.1:8080 LOAD_PROFILE=smoke   k6 run --no-usage-report examples/labs/observability/load-test/k6-scenario.js
```
Read only created IDs and validate the synthetic payment state. Verify independent queue delivery and increasing consumer `/stats`/DB counts/logs. Notification and analytics use separate queues; competing consumers on one queue would not provide fanout. Failed/poison messages remain unacknowledged for the DLQ policy.

Compare CloudWatch/Loki JSON trace_id, actual Tempo spans and Prometheus exemplar IDs. Installing a collector is not end-to-end verification.

## 5. Canary and GitOps ownership {#canary}


![Manual inspection, canary-only analysis, promotion or abort](../../.gitbook/assets/en-labs-observability-03-msa-deployment-lab-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-03-msa-deployment-lab-1.html)
A single Rollout owns payment-service. With five replicas, the20% step is replica-based and does not guarantee20% of actual requests. Generate traffic to the new revision during the manual pause before analysis. Queries select `rollouts-pod-template-hash`, require at least five recent requests and99% success, and reject empty/NaN/Inf/multi-series results.

Actual Rollouts1.10.0 condition evaluation and PromQL were tested, but cluster promotion was not executed. Abort is not a Git revert or desired-image restoration. For optional ArgoCD, follow its [installation guide](../../gitops/argocd/01-installation.md), point to this repository’s real chart path/reviewed revision, and avoid simultaneous direct-Helm ownership. Reference existing Secrets rather than committing them. App-of-apps sync waves alone do not guarantee child readiness.

Continue to [Part4](./04-load-testing-scaling-lab.md). Follow [Part6](./06-distributed-tracing-lab.md#cleanup) for ownership/dependency-aware cleanup.

## Validation scope

Checks covered local SQLite/PostgreSQL, three HTTP services, OTel correlation, SNS/SQS SDK stubs, container smoke, Helm/CRD and PromQL/Argo conditions. Actual AuroraTLS, EKS/IRSA, SNS fanout, KEDA/Karpenter and canary traffic splits were not exercised.
