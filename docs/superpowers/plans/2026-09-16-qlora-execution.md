# Budgeted SageMaker QLoRA execution

The user authorized real training on September 16, 2026 with a total budget of
USD 500. The existing model remains Qwen/Qwen3-30B-A3B-Instruct-2507.
This is an execution and bounded migration of the existing experiment.

- [x] Verify samples-atomoh resolves to account 061525506239 and role atomoh.
- [x] Isolate changes from the concurrent Hybrid Nodes documentation branch.
- [x] Retrieve current training quota, price, model revision, and supported DLC.
- [ ] Build a separate reproducible synthetic dataset with family separation,
      training-only augmentation, exact-source disjointness and nine PII labels.
- [ ] Add a separate supported execution path. Keep the historical PyTorch 2.8
      example blocked and its previous results intact.
- [ ] Run CPU contracts and independent review of cloud permissions, budget
      reservation, test isolation, response masking and artifact persistence.
- [ ] Provision only an experiment-owned private S3 bucket and a least-privilege
      SageMaker execution role. Use Training Jobs directly.
- [ ] Run a bounded GPU smoke job. Verify CUDA/BF16, NF4 loading, finite loss,
      response-only supervision, changed LoRA weights and adapter save/reload.
- [ ] Freeze full training settings after smoke speed/memory measurements. Use
      validation loss for checkpoint selection; access test only after selection.
- [ ] Run full training and paired baseline/tuned PII evaluation, preserve final
      adapter, dependency versions, aggregate metrics and cost evidence.
- [ ] Verify all training jobs terminal, export artifacts, remove owned temporary
      resources, document any intentionally retained private adapter storage.
- [ ] Review latest commit, pass CI, merge PR and publish truthful ko/en results.

## Runtime and measurement boundaries

The new path uses the AWS PyTorch 2.11.0 / CUDA 13.0 / Python 3.12 / AL2023
SageMaker image, pinned to its September 14 image digest. The upstream catalog
lists patch support through April 30, 2027. Its GPU behavior is unverified until
the smoke job succeeds. No model weights are downloaded to this documentation host.

Attention projection LoRA (q/k/v/o, rank 16, alpha 32) is the initial configuration
for one 48GB GPU. This is explicitly different from the historical seven-module
configuration. It keeps the same base model and quantization while reducing
optimizer memory. No claim of production privacy or unseen-domain generalization
will be inferred from synthetic evaluation.

## Spending controls

Every job reserves its maximum configured runtime plus two hours of launch/upload
overhead and USD 5 incidental allowance before submission. Total reservations
must stay below USD 300, leaving USD 200 of the user's limit unallocated.
Server-enforced MaxRuntimeInSeconds remains present even if this host disconnects.
One job runs at a time. Ambiguous submissions are reconciled by their unique name
before any new job is considered. No endpoint, warm pool, Studio domain, EKS
cluster, or managed MLflow service is part of this execution.

The recorded Seoul on-demand Training rate is USD 4.6169375/hour for
ml.g6e.4xlarge. Final costs will distinguish estimates based on AWS billable seconds
from delayed billing data; unused budget is not a spending target.
