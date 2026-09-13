# EKS observability credential profiles

Reviewed September 13, 2026 for Linux EC2-backed EKS, kube-prometheus-stack
**90.0.0** (Grafana chart 13.2.2 / application 13.2.1), and Datadog chart
**3.244.0** / Agent and Cluster Agent **7.83.1**. These are installation examples
with offline contract tests, not evidence of live authentication or deployment.

Resolved password/key/token values must never enter container environments.
Grafana receives a literal `$__file{...}` expression. Datadog receives literal
`ENC[...]` handles. Applications resolve them into their in-memory configuration;
these strings are references, not credentials. Do not replace them with actual
values, `__FILE` entrypoint exports, shell substitutions or Kubernetes Secret
environment references.

## Prerequisites and identity

Use an owned release and the documented namespaces. Prepare these resources through
your existing IAM and secret-management process before installation:

| Service account | Namespace | AWS Secrets Manager secret in `ap-northeast-2` |
|---|---|---|
| `metrics-demo-grafana` | `monitoring` | `observability/grafana-admin`: JSON string key `admin-password` |
| `datadog` | `datadog` | `observability/datadog`: JSON string keys `api-key` and `cluster-token` |
| `datadog-cluster-agent` | `datadog` | The same `observability/datadog` secret |

The API key must belong to the configured Datadog site. Generate a cryptographically
random cluster token of at least 32 characters through the approved secret workflow;
all node agents and Cluster Agents must use the same token. Do not put real values
in these files, command arguments or terminal output.

Replace the three example `111122223333` IAM role ARNs in the values files. Each
role's IRSA trust must bind the cluster's actual OIDC provider, audience
`sts.amazonaws.com`, and the exact `system:serviceaccount:<namespace>:<name>` subject
above. The roles need `secretsmanager:GetSecretValue` and, for ASCP,
`secretsmanager:DescribeSecret`, restricted to the corresponding full secret ARN.
If using a customer-managed KMS key, scope `kms:Decrypt` to that key and the intended
Secrets Manager encryption context/service. Do not grant wildcard resources or
static AWS keys. Validate the trust, KMS policy and workload identity separately;
a local STS check does not prove Pod identity.

IRSA webhook/token projection, regional STS and Secrets Manager connectivity must
work on each relevant node/Pod. Datadog sets `AWS_EC2_METADATA_DISABLED=true` in
node, trace, init and Cluster Agent containers to prevent node-role fallback.
Only non-secret role/token-file metadata is injected by IRSA. These profiles do
not configure the separate Datadog SaaS AWS account integration.

Grafana also requires the **Secrets Store CSI driver and AWS provider (ASCP)**
installed on its Linux EC2 nodes, with CSI `fsGroup` support. Apply
`grafana-secret-provider.yaml` in the existing `monitoring` namespace first.
ASCP fetches the password using the Grafana service account's IRSA role. The file
is mounted read-only at `/mnt/grafana-secrets/admin-password`, with mode `0440`
and Pod `fsGroup: 472`. Do not use a `subPath` mount or enable `secretObjects`
syncing. Verify actual ownership/readability in the target distribution; an
unavailable mount or unreadable file must prevent successful startup.

## Grafana

`prometheus-values.yaml` retains the original storage, scrape selectors, kubelet
TLS verification and EKS monitor exclusions. It adds the CSI mount and file
provider. The literal `GF_SECURITY_ADMIN_PASSWORD` expression is also required
to suppress the chart's automatic password Secret/environment injection.
`grafana.ini` records the same expression. Grafana 13.2.1 applies environment
overrides before evaluating configuration providers; it reads the file into the
configuration, without an entrypoint exporting its contents.

Dashboard and datasource sidecars have `skipReload: true`; neither receives
credentials or access to the CSI password volume. Initial listing containers
populate provisioning files before Grafana starts. Dashboard file updates are
polled every 30 seconds by Grafana's dashboard provider. Datasource file updates
require a controlled Grafana Pod restart because the authenticated reload call
is disabled. The example retains dashboard/data-source provisioning; it does not
promise immediate datasource reloads.

Grafana's `admin_password` setting initializes a **new database only**. Updating
the AWS secret, CSI rotation, or restarting a Pod does **not** change an existing
database administrator password. For an existing PVC/database, use the approved
authenticated password-change/SSO procedure and reconcile the stored secret.
Never delete the PVC to “rotate” a password. CSI's rotation reconciler, when
enabled, updates mounted content, not Grafana's database credentials.

From the repository root, after prerequisites:

```sh
PROFILE=examples/observability/secret-profiles
kubectl apply -f "$PROFILE/grafana-secret-provider.yaml"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm template kube-prom prometheus-community/kube-prometheus-stack \
  --version 90.0.0 --namespace monitoring -f "$PROFILE/prometheus-values.yaml" \
  > grafana-reviewed-render.yaml
# Inspect resources, storage, identity and ownership before this cluster-changing command.
helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack \
  --version 90.0.0 --namespace monitoring -f "$PROFILE/prometheus-values.yaml" \
  --wait --timeout 15m
```

## Datadog

Use Python 3 with PyYAML **6.0.3** and an executable `datadog_postrender.py`.
The chart unconditionally creates credential environment references, so every
template/install/upgrade must use the postrenderer. It validates the fixed chart,
images, namespace, service accounts, native backend and all regular/init consumers,
then replaces exactly seven references with native `ENC[...]` handles. It does not
call AWS, retrieve secrets, change commands/mounts, or export resolved credentials.
Unexpected input fails with no partial manifest on stdout.

The `must-use-secret-postrenderer` Secret is deliberately **not created**.
If the renderer is omitted, required Secret references stop node-agent startup.
Never create a placeholder Secret to bypass that failure.

The pinned init `01-check-apikey.sh` requires a nonempty `DD_API_KEY`; it cannot
be satisfied by simply deleting the environment variable in favor of a config
file. The literal handle satisfies this bootstrap check. The node Agent, trace
Agent and Cluster Agent subsequently resolve their effective configuration through
the native `aws.secrets` backend. Both the API key and cluster token use that path:

| Consumer | Literal references retained in environment |
|---|---|
| Node `agent` and `trace-agent` | `ENC[observability/datadog;api-key]`, `ENC[observability/datadog;cluster-token]` |
| Node `init-config` | `ENC[observability/datadog;api-key]` (bootstrap check only) |
| `cluster-agent` | Both handles |
| Both `init-volume` containers | None; they only copy image configuration |

The public backend configuration is
`{"aws_session":{"aws_region":"ap-northeast-2"}}`. Static AWS credential fields
are rejected. The native resolver merges decrypted settings into memory, not the
process environment. `init-config` does not need to fetch the real API key.
An existing native backend failure, wrong IAM trust, missing JSON key, invalid
API key/site or token mismatch is still an installation failure; rendering cannot
prove those runtime conditions.

This example explicitly disables scheduled/API-failure secret refresh. Plan
rotation as a **coordinated restart** of node/trace and Cluster Agent Pods after
updating the approved secret. Keep an old Datadog API key valid until all agents
use the replacement. Cluster-token changes can interrupt node/Cluster Agent
authentication while old and new Pods coexist; plan a maintenance window or a
separately validated transition. No token-overlap or zero-downtime rotation is
claimed.

```sh
PROFILE=examples/observability/secret-profiles
helm repo add datadog https://helm.datadoghq.com
helm repo update datadog
helm template datadog datadog/datadog --version 3.244.0 \
  --namespace datadog --include-crds -f "$PROFILE/datadog-values.yaml" \
  --post-renderer "$PROFILE/datadog_postrender.py" > datadog-reviewed-render.yaml
# Inspect resources and ownership first. Keep this renderer on every future upgrade.
helm upgrade --install datadog datadog/datadog --version 3.244.0 \
  --namespace datadog -f "$PROFILE/datadog-values.yaml" \
  --post-renderer "$PROFILE/datadog_postrender.py"
```

The renderer is intentionally limited to this release, namespace, region, secret
name and image set. Review and test changes to those contracts together. Preserve
logs opt-in, UDS APM/DogStatsD, metadata collection and admission settings when
adapting the profile; enabling additional containers requires explicit review.

## Offline regression checks

Use existing Helm/Python/PyYAML tools and the two pinned chart archives. Tests
verify archive checksums and never contact a cluster, AWS or Datadog:

```sh
export PROMETHEUS_CHART=/path/to/kube-prometheus-stack-90.0.0.tgz
export DATADOG_CHART=/path/to/datadog-3.244.0.tgz
python3 -B -m unittest discover \
  -s examples/observability/secret-profiles -p 'test_*.py' -v
```

The tests exercise real chart renders and the executable postrenderer, credential
coverage in every regular/init container, CSI mount/config paths, sidecar startup,
and rejection of missing/duplicate references, missing backend/identity, static
AWS credentials, version/image drift and unreviewed consumers. They do not run
Grafana/Agent containers or validate live AWS authorization, CSI ownership,
credential rotation, Grafana login, Datadog ingestion, or webhook admission.

Primary contracts:

- [Grafana configuration providers and initial admin password](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/)
- [Grafana 13.2.1 configuration evaluation](https://github.com/grafana/grafana/blob/v13.2.1/pkg/setting/setting.go)
- [AWS ASCP configuration and IRSA](https://github.com/aws/secrets-store-csi-driver-provider-aws/blob/main/README.md)
- [Datadog native secret backends](https://docs.datadoghq.com/agent/guide/secrets-management/)
- [Datadog 7.83.1 bootstrap requirement](https://github.com/DataDog/datadog-agent/blob/7.83.1/Dockerfiles/agent/cont-init.d/01-check-apikey.sh)
- [Datadog 7.83.1 in-memory secret resolution](https://github.com/DataDog/datadog-agent/blob/7.83.1/pkg/config/setup/config.go)
