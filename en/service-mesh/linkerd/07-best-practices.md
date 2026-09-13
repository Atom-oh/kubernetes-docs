# Linkerd Best Practices

> **Last Updated**: September 11, 2026 · Linkerd edge-26.9.1 / charts 2026.9.1

Use the [installation](01-installation.md), [security](04-security.md), [observability](05-observability.md) and [multicluster](06-multi-cluster.md) guides for the selected versions and prerequisites. This chapter connects those procedures into an operational review; it does not certify an environment as production-ready.

Select and verify the intended Kubernetes context, API endpoint and resource owner before any change. Commands below use the current context and example namespace/workload names. No live upgrade, rollback, migration or load test was performed for this audit.

## Readiness Review

- [ ] Verify the Kubernetes/Linkerd/Gateway API compatibility and the chosen distribution's release notes.
- [ ] Confirm actual replicas, placement, capacity, disruption behavior and admission policy.
- [ ] Separate root, issuer and workload-certificate lifetimes; verify their renewal and recovery procedures.
- [ ] Test required identity/authorization behavior, including denied callers and unmeshed paths.
- [ ] Confirm metrics, logs, trace requirements, alert delivery and missing-data detection.
- [ ] Record resource ownership, protected backups, version-specific upgrade/recovery steps and operational responsibility.

Shared trust is required for the intended linked mesh relationships, not every unrelated cluster. ServiceProfiles are not a universal readiness requirement: current Gateway API policies and compatibility profiles have different roles and precedence.

```bash
linkerd version
linkerd check
linkerd check --proxy
kubectl -n linkerd get deployments,pods,poddisruptionbudgets
kubectl -n my-app get pods -o wide
```

Keep full check output and its exit status. A grep for “valid” can match “invalid” and can hide a failed command behind grep's successful exit:

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
if linkerd check --proxy > linkerd-check.log 2>&1; then
  cat linkerd-check.log
else
  check_status=$?
  cat linkerd-check.log >&2
  exit "$check_status"
fi
```

Review warnings even when the command exits successfully. A healthy control-plane check does not establish the application's SLO or regional failover behavior.

## Resource Allocation

Size from measured workload behavior: request/connection concurrency, protocol, payload/stream size, discovery size, telemetry cardinality, memory pressure and CPU throttling. RPS alone does not determine proxy resources.

This is an **illustrative starting configuration**, not a capacity guarantee:

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
```

Use one coherent YAML mapping. Repeating `proxy:` three times in the same mapping is invalid; permissive loaders can silently retain only the last profile.

For an existing workload, save this **merge patch** as `proxy-resources-patch.yaml`:

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/proxy-cpu-request: 500m
        config.linkerd.io/proxy-cpu-limit: 2000m
        config.linkerd.io/proxy-memory-request: 128Mi
        config.linkerd.io/proxy-memory-limit: 500Mi
```

```bash
# A merge patch for one existing, reviewed workload; this starts a rollout.
kubectl -n my-app patch deployment/api --type merge --patch-file proxy-resources-patch.yaml
kubectl -n my-app rollout status deployment/api --timeout=5m
kubectl -n my-app top pod --containers
```

`kubectl top pod --containers` requests per-container data; there is no `-c linkerd-proxy` filter for that command. Confirm that the metrics pipeline reports the native init sidecar as expected. Use the Pod's spec/status and resource metrics together rather than inferring absence from one view.

### Runtime workers versus CPU quota

CPU requests/limits configure scheduling and CPU allocation. A limit of 4 does not directly request four proxy worker threads. The selected chart has separate runtime worker bounds:

```yaml
proxy:
  runtime:
    workers:
      minimum: 1
      maximum: 4
      maximumCPURatio: 1
```

This is an independent values excerpt; merge its nested fields rather than duplicating a top-level YAML key. The released chart emits worker minimum/maximum/CPU-ratio settings separately from Kubernetes CPU limits. Runtime behavior also depends on available CPU and demand; increasing a bound alone is not a performance improvement. The older fixed `proxy.cores` configuration is deprecated in the template.

## High Availability

### Core control plane

Start with the **HA profile from the same chart release** and layer it with the installation's reviewed values, including its certificate configuration:

```bash
set -euo pipefail
umask 077
# Use the same reviewed chart version for the profile and render.
curl --fail --show-error --location \
  https://raw.githubusercontent.com/linkerd/linkerd2/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml \
  -o values-ha.yaml
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd \
  -f reviewed-core-values.yaml -f values-ha.yaml > reviewed-ha.yaml
```

The packaged profile configures three controller replicas, three control-plane PDBs, per-component required node anti-affinity, preferred zone separation and fail-closed injection. It also supplies resources and rollout settings. Confirm the rendered Deployment/PDB/webhook objects and actual eligible nodes. Values files merge in order, so the HA profile can override earlier resource settings; inspect the final result and preserve essential HA controls when layering additional overrides.

The previous nested `destination.replicas/resources`, `identity.replicas/resources` and `proxyInjector.replicas/resources` examples were ignored by this chart. Supported controller resource values include `destinationResources`, `identityResources`, `proxyInjectorResources` and the other fields in the packaged profile. Arbitrary `podAntiAffinity`, `topologySpreadConstraints` or `podDisruptionBudget` keys are not automatically converted into Pod fields.

Three replicas are not a quorum guarantee. Required placement can leave replicas Pending if too few suitable nodes exist; preferred zone rules do not guarantee one replica per zone. PDBs constrain supported voluntary evictions, not every outage or every controller-driven rollout.

### Viz and metrics availability

For a separately prepared Prometheus/query endpoint with the intended retention, authentication and HA behavior, these values scale the stateless Viz components:

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
tap:
  replicas: 2
metricsAPI:
  replicas: 2
tapInjector:
  replicas: 2
dashboard:
  replicas: 2
```

Replica counts alone do not establish fault-domain separation, disruption protection or metrics availability. Verify actual placement and the external query architecture, including any replica deduplication.

Alternatively, a **single local Prometheus** can persist its data:

```yaml
prometheus:
  enabled: true
  persistence:
    accessMode: ReadWriteOnce
    size: 50Gi
```

This needs a working default StorageClass, or the appropriate explicit chart storage-class setting. The selected Viz chart keeps Prometheus at one replica and uses a Recreate strategy with its PVC. The old `prometheus.replicas:2` was ignored, and `persistence.enabled:true` without an accessMode produced an invalid PVC. Persistence helps data survive restarts; it is not Prometheus HA.

## Upgrade and Recovery

### Select the path before changing versions

Public Linkerd artifacts use the edge track; a vendor's stable distribution can have different supported upgrade instructions. The public installer is not a generic stable-version/downgrade installer. Acquire and verify the selected CLI as described in the installation guide.

Edge version numbers are not semantic-version compatibility guarantees. Review release-specific changes and allowed control/data-plane skew, using intermediary releases where required. `check --pre` is a pre-installation check, not an upgrade-eligibility test for an existing mesh.

Back up desired values and the necessary credentials through their owners, protect stored key material, and test restoration. `helm get values` can expose issuer material; do not publish its output. Prepare reviewed target values rather than blindly applying old computed defaults to a new chart.

### CLI-owned installation

After approving a supported path and retaining the current configuration/credentials:

```bash
set -euo pipefail
# The selected, verified target CLI must already be on PATH.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds | kubectl apply -f -
linkerd upgrade | kubectl apply -f -
linkerd check
# CLI-owned Viz only; preserve its complete reviewed configuration.
linkerd viz install -f reviewed-viz-values.yaml | kubectl apply -f -
linkerd viz check
```

Upgrade CRDs before the core, then compatible extensions, then workload proxies. The current extension CLI uses `install` with the complete configuration; `linkerd viz upgrade` does not exist. Review release-specific pruning/migration instructions and inspect stale-resource candidates before deleting anything.

For multicluster, retain the desired Helm `controllers` list and current Link/credential ownership from the multicluster guide. Do not recreate deprecated legacy link-managed controllers as an automatic upgrade step.

### Helm-owned installation

The example target below is 2026.9.1; it is usable only after verifying the path from the actual installed release:

```bash
set -euo pipefail
umask 077
helm get values linkerd-control-plane -n linkerd > current-core-values.yaml
helm get values linkerd-viz -n linkerd-viz > current-viz-values.yaml
# Prepare reviewed target values and approved migration steps before these changes.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version 2026.9.1 -n linkerd --wait --timeout 10m
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd -f reviewed-core-values.yaml \
  --wait --timeout 10m
linkerd check
helm upgrade linkerd-viz linkerd-edge/linkerd-viz \
  --version 2026.9.1 -n linkerd-viz -f reviewed-viz-values.yaml \
  --wait --timeout 10m
linkerd viz check
```

Keep CRDs, core, CNI and extensions under their established owners. Do not mix a CLI apply workflow into a Helm-owned release merely because the manifests look similar.

### Workload rollout

Select actual meshed workload controllers, including relevant StatefulSets/DaemonSets/jobs, and coordinate their application-specific rollout behavior. A namespace-wide loop restarts unrelated workloads and a fixed 30-second sleep is not a stabilization test.

```bash
# One explicitly selected meshed Deployment, after checking disruption/capacity.
kubectl -n my-app rollout restart deployment/api
kubectl -n my-app rollout status deployment/api --timeout=5m
linkerd check --proxy -n my-app
linkerd viz stat deployment/api -n my-app
```

Verify readiness, identity/policy and representative application traffic before continuing to another workload. Namespace annotations affect new Pods; they do not update running sidecars in place.

### Recovery and multiple control planes

Define a tested recovery plan for the specific versions and CRDs. Rolling back only a core Helm release does not also revert separately managed CRDs, all credential changes or already running workload proxies. Downloading an arbitrary old CLI and running upgrade is not a universal downgrade procedure.

The former “blue-green” example installed a second namespace and changed `proxy-version`. That annotation selects a proxy image, not a control plane. Default chart renders for the two namespaces also share cluster-scoped names, including admission webhooks. A second namespace therefore does not establish isolated coexistence or safe workload migration. Use a distribution-supported design with explicit resource ownership and traffic/identity selection, and retain recovery capability until it is verified.


## Enrollment and Protocol Handling

Namespace enrollment for new Pods:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
```

An opt-out for an existing workload is a Pod-template merge patch, not a complete Deployment:

```yaml
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: disabled
```

Changing annotations alone does not remove a running or manually embedded proxy. Reconcile the workload's actual manifests and recreate it through its owner when appropriate. Inspect both `containers` and `initContainers`; native sidecars are not missing merely because the regular-container list does not show them.

Opaque ports skip HTTP protocol detection while retaining the relevant TCP proxy path, mTLS and policy. For a prepared MySQL workload, use the Pod-template patch and a consistent Service annotation:

```yaml
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/opaque-ports: '3306'
---
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: my-app
  annotations:
    config.linkerd.io/opaque-ports: '3306'
spec:
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
```

Pod and Service port mappings must agree. A selected Server's `proxyProtocol` also affects protocol handling. Opaque mode does not provide HTTP route metrics for that stream.

By contrast, skip-inbound/outbound-ports bypass the proxy path and can remove mesh encryption, policy and telemetry. Do not prescribe skipping Redis, Memcached or database ports as a generic latency optimization.

A ServiceProfile route timeout is a deadline, not connection-pool configuration. Likewise, protocol handling does not guarantee that every application's HTTP/1 connection becomes HTTP/2 end to end. Measure actual connection reuse, buffering and protocol behavior before tuning.

## Certificate Operations

Treat public roots, issuer credentials, proxy leaves and webhook certificates as separate lifecycles with their own owners. Default short-lived proxy leaves cannot satisfy a generic 60-day remaining-lifetime checklist. Choose thresholds from configured lifetimes and renewal lead time.

Use the validated credential inspection, issuer reload/events and cert-manager ownership examples in the security guide. Setting `isCA:true` alone does not install an Issuer, distribute trust roots, rotate every consumer or configure alert delivery.

The previous certificate CronJob used an unverified old CLI image, lacked required RBAC and hid check failures behind grep. A scheduled check needs a supported runtime, scoped credentials, explicit failure handling and a tested delivery path. The check/log example above preserves exit status; the security guide provides metrics-based alerts. Neither is a completed notification service without that integration.

## Troubleshooting from Evidence

For injection problems, inspect namespace and actual Pod-template/Pod metadata, both container types, webhook configuration and injector logs:

```bash
kubectl get namespace my-app -o yaml
kubectl -n my-app get deployment api -o yaml
# Set this to an actual API Pod.
api_pod=api-example-pod
kubectl -n my-app get pod "$api_pod" -o json | jq '{
  annotations: .metadata.annotations,
  containers: [.spec.containers[]? | {name,image,resources}],
  initContainers: [.spec.initContainers[]? | {name,image,restartPolicy,resources}],
  status: .status
}'
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector --tail=100
```

For latency or instability, compare application behavior, resource pressure, pending Pods, endpoints, DNS, protocol detection and certificate/policy errors. Raising timeouts or restarting the entire control plane is not a diagnosis.

```bash
linkerd check
linkerd check --proxy
linkerd viz stat deploy -n my-app
linkerd viz tap deployment/api -n my-app --max-rps 20
linkerd viz edges deploy -n my-app
linkerd identity -n my-app -l app=api
kubectl -n my-app top pod --containers
kubectl -n my-app logs deployment/api -c linkerd-proxy --tail=100
kubectl -n linkerd logs deployment/linkerd-destination -c destination --tail=100
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
kubectl -n linkerd get events --sort-by=.lastTimestamp
```

`linkerd identity` retrieves public leaf certificates; do not assume a fixed `end-entity.crt` file exists in the proxy image. Use ServiceProfile `viz routes` or current policy diagnostics only for the resources actually configured. Keep the relevant controller container explicit when reading logs.

After a targeted fix, verify the original failing path, not only a command's successful completion.

## Migration from Istio

Inventory the features and security properties used by each workload before designing a transition. These are **partial capability comparisons**, not a mechanical manifest conversion:

| Istio concept | Linkerd consideration |
|---|---|
| VirtualService | Supported Gateway API routing features; ServiceProfile is a compatibility interface, not a full equivalent |
| DestinationRule | Reassess load balancing, failure accrual, connection behavior and TLS requirements individually |
| PeerAuthentication STRICT | Automatic mTLS alone is insufficient because default Linkerd policy can accept unmeshed plaintext; require appropriate authorization |
| AuthorizationPolicy | Different Linkerd target/authentication model; JWT/user claims and other conditions need separate design |
| Sidecar traffic scope | No blanket equivalence to injection annotations or a network firewall |
| Gateway | Choose and configure an appropriate ingress/gateway implementation and its Linkerd integration |

Classic injection labels, revision labels/tags, Pod annotations, manually injected manifests and ambient enrollment are distinct. Removing only `istio-injection` does not account for all of them. Inspect actual Istio/Linkerd CNI and proxy enrollment before changing workloads.

Do not assume Istio and Linkerd mesh mTLS automatically interoperate. Mixed migration stages need explicit traffic/security boundaries and verified application behavior; avoid accidentally enrolling the same workload in both interception paths. Namespaces alone are not a safe unit of migration if dependencies cross those boundaries.

A practical review sequence is to inventory dependencies/policies, reproduce them in an isolated environment, test permitted and denied flows plus recovery, then move a deliberately selected workload group. Reconcile the correct enrollment controls, verify exactly the intended proxy path, and measure representative traffic before expanding the transition. Remove old control-plane/resources only after no required consumers remain and the chosen recovery plan is viable.

This replaces the unconditional namespace-label/restart/uninstall recipe and the diagram's incorrect one-to-one feature mappings. Application compatibility and production migration remain environment-specific work to verify.

## References

- [Selected HA profile](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/linkerd-control-plane/values-ha.yaml)
- [Proxy configuration](https://linkerd.io/docs/reference/proxy-configuration/)
- [Released proxy runtime template](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/partials/templates/_proxy.tpl)
- [Upgrade guidance](https://linkerd.io/docs/tasks/upgrade/)
- [Authorization policy](https://linkerd.io/docs/reference/authorization-policy/)
- [Istio injection](../istio/advanced/07-sidecar-injection.md) and [ambient mode](../istio/advanced/01-ambient-mode.md)
