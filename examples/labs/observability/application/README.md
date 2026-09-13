# Synthetic observability application

Five separately deployed Python roles share the API and telemetry contracts used
by the six-part lab. Orders and payments are synthetic. Notification/analytics
consumers persist a synthetic result; they do not send email or charge money.

| Role | Behavior |
|---|---|
| `api-gateway` | Proxies order/payment requests and propagates W3C trace context |
| `order-service` | Commits an order and outbox event in one database transaction |
| `payment-service` | Checks the order over HTTP, persists an idempotent synthetic payment and outbox event |
| `notification` | Consumes its own SNS-subscribed SQS queue and deduplicates event IDs |
| `analytics` | Consumes a separate queue and independently deduplicates event IDs |

`POST /orders` returns 201 and `id`; `POST /payments` returns 200 and
`status: completed`; `GET /orders/{id}` returns the same ID. Repeated order POSTs
create new orders. The example does not implement general HTTP idempotency keys.
Repeated identical payment requests reuse the stored result; conflicting payment
values return 409. Outbox publishing is at least once: publication can succeed
before the DB mark, so consumers must deduplicate. External side effects would
require their own idempotency contract.

Telemetry uses `lab_http_requests_total` and
`lab_http_request_duration_seconds` with bounded `service`, `route`, `status`
and `revision` labels. Logs include `service`, `level`, `trace_id` and `span_id`;
customer/payment payloads are excluded. `/health` is liveness; `/ready` additionally
checks DB connectivity and schema for DB-backed roles. It does not prove IAM or
SQS delivery. Inspect actual background work and queues separately.

HTTP/database spans disable automatic exception text, stacktraces and status
descriptions. Failed operations retain an error status and bounded HTTP metrics;
unexpected request failures return a generic 500 response. SQLAlchemy also hides
bound parameters in its error strings. Failure-path tests check exported spans,
logs and responses using synthetic sentinel inputs.

## Infrastructure and credentials

`infra.yaml` creates a private Aurora PostgreSQL cluster/writer, an encrypted SNS
event topic, separate notification/analytics queues and DLQs, a log group, scoped
policies and six IRSA roles. It requires existing private subnets/client SG and
matching service/management EKS OIDC providers. It creates no EKS cluster, route,
DNS record, load balancer controller or OIDC provider.

Use dedicated lab resources. Verify account/Region, at least two private subnets
in different AZs, available `aurora-postgresql`/`db.serverless` engine version and
connectivity before reviewing a CloudFormation change set. The writer is a
single-instance lab profile, not HA. Database snapshots are retained on deletion;
include them in the cleanup inventory. Roles trust exact namespace/ServiceAccount
subjects and `aud=sts.amazonaws.com`.

Save the stack outputs privately:

```bash
umask 077
aws cloudformation describe-stacks --stack-name "$LAB_STACK" \
  --query 'Stacks[0].Outputs' --output json > "$LAB_STATE/infra-outputs.json"
```

Do not run the application as the database master. Obtain the generated admin
secret through an authorized session and prepare a **private JSON connection
file** with this structure. Values below describe fields, not usable credentials:

```json
{
  "drivername": "postgresql+psycopg",
  "host": "ACTUAL_PRIVATE_AURORA_ENDPOINT",
  "port": 5432,
  "database": "observability",
  "username": "labadmin",
  "password": "RAW_SECRET_VALUE",
  "query": {
    "sslmode": "verify-full",
    "sslrootcert": "/private/path/global-bundle.pem"
  }
}
```

Use the AWS RDS trust bundle and a DNS endpoint matching its certificate.
`URL.create` receives the raw password; do not interpolate it into a DSN or
pre-encode it. Keep admin material out of chart values, environment variables,
logs and source control.

From a machine with private DB connectivity:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt PyYAML==6.0.3
.venv/bin/python bootstrap_db.py \
  --admin-connection-file "$LAB_STATE/admin-connection.json" \
  --runtime-connection-file "$LAB_STATE/runtime-connection.json"
```

Bootstrap initializes only the lab tables and creates `lab_runtime` with DML
access to those tables; it is not a production per-service database isolation
scheme. Existing roles/passwords are never silently changed. On failure, the
output can be a candidate credential: verify the DB transaction before using it.
Keep the file private for recovery; do not blindly rerun or drop a role.

Copy the runtime JSON to a private deployment file and set its `sslrootcert` to
`/run/database-ca/global-bundle.pem`, the path used inside Pods. Mount it and the
public CA separately:

```bash
kubectl --context service create namespace msa --dry-run=client -o yaml |
  kubectl --context service apply -f -
kubectl --context service -n msa create secret generic lab-database \
  --from-file=connection.json="$LAB_STATE/runtime-pod-connection.json"
kubectl --context service -n msa create configmap lab-database-ca \
  --from-file=global-bundle.pem="$LAB_STATE/global-bundle.pem"
```

## Build and deployment inputs

Build and push an immutable image tag to the approved registry. The Dockerfile
pins the Python multi-platform base digest and runs as UID/GID 10001. No private
state is part of the build context.

The generated `m6i.large` node groups require **linux/amd64**. Use an AMD64 builder
or a Buildx builder configured for that target; an ARM64-only image cannot run on
these nodes. Inspect the pushed manifest before deploying. The audit's local
ARM64 smoke test is separate evidence, not an AMD64 build validation.

```bash
docker buildx build --platform linux/amd64 \
  --tag "$IMAGE_REPOSITORY:$IMAGE_TAG" --push .
docker buildx imagetools inspect "$IMAGE_REPOSITORY:$IMAGE_TAG"
.venv/bin/python prepare_values.py \
  --outputs-file "$LAB_STATE/infra-outputs.json" --region "$AWS_REGION" \
  --image-repository "$IMAGE_REPOSITORY" --image-tag "$IMAGE_TAG" \
  --output-directory "$LAB_STATE/helm-inputs"
```

Install the pinned controllers before the chart. KEDA uses its own IRSA role
with queue-attribute permissions; consumer roles have only their own queue's
receive/delete permissions. The chart uses IRSA, not a second Pod Identity setup.

```bash
helm upgrade --install keda kedacore/keda --version 2.20.2 \
  --kube-context service -n keda --create-namespace \
  -f "$LAB_STATE/helm-inputs/keda.yaml"
helm upgrade --install argo-rollouts argo/argo-rollouts --version 2.43.1 \
  --kube-context service -n argo-rollouts --create-namespace
helm upgrade --install observability-lab ./chart \
  --kube-context service -n msa --create-namespace \
  -f "$LAB_STATE/helm-inputs/application.yaml"
```

Prometheus Operator/ServiceMonitor CRDs and the service Collector must already be
installed using the stack examples. The app chart deliberately requires namespace
`msa`, matching IRSA subjects and service URLs. `/metrics` scraping honors the
application's `service` label and groups dynamic IDs under a fixed route name.

## Canary and scaling

Only the payment workload is a Rollout. There is no competing Deployment or KEDA
controller for it. The basic canary approximates traffic through replica counts;
it does not promise an exact 20% request split. The initial five replicas allow a
one-of-five replica step, but client connection reuse and routing still matter.

A canary pauses for operator inspection, then checks only the new pod-template
revision: at least five recent requests and at least 99% non-5xx responses. Empty,
NaN, infinite or multi-series results fail the success condition. Generate test
traffic before continuing. Aborting a rollout is not a Git revert or restoration
of the desired image; restore the desired version in the actual source of truth.

KEDA scales the two queue consumers, not the producer API. Its SQS scaler reads
queue attributes; it does not consume messages. `cooldownPeriod` applies to
scaling to zero, while HPA behavior controls scaling among positive replicas.
Observe queue age/depth, actual processing, desired/ready replicas and failures.

Karpenter is an optional node-capacity layer configured through the audited
Karpenter guide. Configure its IAM, NodePool/EC2NodeClass, discovery tags, taints
and AMI before relying on it. More Pods do not guarantee that nodes will be
provisioned, and controller limits are not absolute spending caps.

## Local tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

These portable tests use disposable SQLite and synthetic clients. They do not
create cloud resources or send notifications.

## Validation limits

Native checks covered SQLite and ephemeral PostgreSQL 17.11 transactions,
password handling and runtime-role DML/denied DDL; three actual Uvicorn services;
OTel propagation/log/exemplar IDs; SNS/SQS SDK Stubber calls; image build and
network-isolated container smoke; Helm/CRD schemas; PromQL and Argo condition
logic. No Aurora connection/TLS handshake, actual EKS admission, IRSA exchange,
SNS fanout, KEDA scaling, canary traffic split or Karpenter provisioning was
executed during the audit.
