# Gatekeeper policy examples

Validated with Gatekeeper/Gator3.23.1. The templates apply to a dedicated
`policy-lab` namespace, and the example Constraints start in `dryrun` mode.
They are synthetic policy examples, not a complete Pod Security Standards suite.
The `registry.example.com` images are test inputs, not deployable application images.

Four local templates explicitly select Rego v1 using
`targets[].code[].source.version: v1`. The upstream resource-limits template
retains supported Rego v0; see `UPSTREAM.md` and `LICENSE.gatekeeper-library`.

```bash
gator verify tests/suite.yaml --verbose
gator test -f templates/docsnoprivileged.yaml \
  -f constraints/no-privileged.yaml \
  -f tests/fixtures/tenant-skip-label-no-bypass.yaml --output=json
```

The suite must run five tests and33 cases. `gator verify` can ignore a directory
containing no Suite files; a successful exit without the expected cases is not
coverage. `gator test` returns violation data for dryrun/warn but those modes do
not make its exit status nonzero. A deny Constraint does. Gator is local policy
execution and does not prove webhook reachability, Kubernetes admission order,
RBAC or live audit/cache consistency.

`values.yaml` pins chart3.23.1's supported fields, three webhook replicas and a
60-second audit interval. It explicitly retains the chart's validating webhook
`Ignore` failure policy for a staged rollout. That means webhook availability
failures can allow requests, regardless of a Constraint's `deny` setting. Evaluate
`Fail` against your availability and recovery requirements before enforcing it.

Install templates first and wait for each generated Constraint CRD before applying
Constraints. Create the policy-lab namespace, review image prefixes/parameters,
and use the single corresponding Constraint when moving dryrun→warn→deny.
Do not apply every test fixture to a live cluster.

`sync.yaml` selects Ingress inventory for the referential policy; cache races mean
this is not an atomic cluster-wide uniqueness guarantee. The policy compares exact
hosts and does not resolve wildcard host overlap. `mutations/add-toleration.yaml`
merges a dedicated lab toleration without replacing unrelated entries; it does not
select a Spot node or authorize access to arbitrary tainted node pools.

`podmonitor.yaml` matches both audit and webhook Pods' actual named `metrics` port.
Install Prometheus Operator and configure its PodMonitor label/namespace selectors
before applying it. The webhook Service has no metrics port, so a ServiceMonitor
pointing to that Service cannot scrape the metrics.
