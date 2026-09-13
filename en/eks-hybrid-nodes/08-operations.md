# Operations and Maintenance

< [Previous: Node Lifecycle Management](./07-node-lifecycle.md) | [Table of Contents](./README.md) | [Next: Bare Metal OS Setup](./09-bare-metal-os-setup.md) >

> **Validation baseline**: nodeadm 1.0.20; Cilium 1.18.3 CRDs; Prometheus Operator 0.93.1; kube-prometheus-stack 90.0.0; Harbor 2.15.2. These are reviewed references, not a universal supported-version matrix.
> **Last Updated**: September 13, 2026

This document covers day-to-day operations and maintenance tasks for EKS Hybrid Nodes environments, including monitoring, backup procedures, and troubleshooting.

## Harbor Vulnerability Scan Automation

Use Harbor's built-in scan-all scheduler instead of a CronJob carrying an admin password and enumerating only the latest tag. In the system-administrator UI, open **Administration → Interrogation Services → Vulnerability → Schedule to scan all**. Hourly/Daily/Weekly/Custom schedules are supported; Daily means midnight in the documented UI. For a 02:00 maintenance window, verify the Custom schedule syntax, time zone and next execution for the deployed version.

Harbor 2.15.2 exposes GET/POST/PUT `/api/v2.0/system/scanAll/schedule`. Use the UI or an approved API integration with trusted CA validation, protected credentials and the required system-level permissions. Project robot permissions do not imply authority to configure global scans. Do not place an admin password in Pod environment/command arguments or disable TLS verification.

Record scanner availability, vulnerability-database freshness, actual scan completion and failures. Request submission or an empty API response is not a successful vulnerability assessment. Unsupported artifacts need separate handling, and global scans consume resources. Selected-artifact automation must enumerate all required pages and digests, encode repository paths correctly and check every response; a latest-only loop does not cover the registry.

See the [Harbor guide](../container-registry/03-harbor.md) and [official schedule procedure](https://github.com/goharbor/website/blob/main/docs/administration/vulnerability-scanning/schedule-scans.md).

## Database Backup Procedure

Define the recovery objective and inventory before copying data. Harbor recovery needs compatible database metadata, registry blobs/object storage, configuration and protected secrets/encryption keys. A PostgreSQL dump alone is not a full backup. Modern Harbor no longer includes Notary v1; do not assume notarysigner/notaryserver databases exist.

The [official Harbor Velero procedure](https://github.com/goharbor/website/blob/main/docs/administration/backup-restore/_index.md) uses repository read-only mode and selected Kubernetes resources/PVs. Its backup is **crash-consistent, not application-consistent**, excludes Redis, can lose unsynced metadata/sessions, and may leave tasks requiring repair. It covers the internal database, not an external managed database. Select supported snapshot/file-backup/data-movement plugins and verify recovery-site access to all needed volume/object data; a snapshot reference alone is not necessarily a portable copy.

The following is only a **database-component dump example** for the verified internal PostgreSQL Pod, with pg_dump/pg_restore and local authentication already configured. External databases use their own authenticated backup/restore process. Credentials are not passed in command arguments. Stop on errors and keep partial output private; do not publish it as a completed dump.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${HARBOR_NAMESPACE:?Set the Harbor namespace}"
: "${HARBOR_DB_POD:?Set the verified internal PostgreSQL Pod}"
: "${HARBOR_DB_USER:?Set the approved backup database user}"
: "${HARBOR_DB_NAME:?Set the actual Harbor database name}"
: "${PRIVATE_BACKUP_ROOT:?Set an existing protected durable directory}"
BACKUP_DIR=$(mktemp -d "$PRIVATE_BACKUP_ROOT/harbor-db.XXXXXX")
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec "$HARBOR_DB_POD" -- \
  pg_dump --format=custom --username "$HARBOR_DB_USER" --dbname "$HARBOR_DB_NAME" \
  > "$BACKUP_DIR/registry.dump.partial"
test -s "$BACKUP_DIR/registry.dump.partial"
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec -i "$HARBOR_DB_POD" -- \
  pg_restore --list < "$BACKUP_DIR/registry.dump.partial" > "$BACKUP_DIR/archive-toc.private.txt"
mv "$BACKUP_DIR/registry.dump.partial" "$BACKUP_DIR/registry.dump"
printf 'Database archive created: %s; full Harbor recovery requires separate evidence.\n' "$BACKUP_DIR"
```

An archive listing does not prove a successful restore. Test restoration with compatible PostgreSQL/Harbor versions and validate artifact pulls, metadata, permissions and integrations. Protect/checksum the full backup inventory and coordinate read-only mode, jobs and upload/GC activity. Do not automatically lift read-only mode after a failed operation without assessing its state.

Redis BGSAVE is asynchronous; immediately copying dump.rdb can capture an older generation. If a separate design includes Redis persistence, verify completion, status and generation with its operator. Do not silently mix that custom design with the official tutorial that excludes Redis. No backup or restore was executed for this chapter.

## Prometheus Metrics Collection

Keep host, kubelet/container and GPU metrics separate. `node_cpu_seconds_total` and `node_memory_*` come from Node Exporter, not a kubelet endpoint. Use an installed, reviewed Node Exporter/DCGM profile and verify actual host mounts, privileges, node placement and metric availability. Container Insights does not supply Hybrid host-level metrics through EC2 IMDS.

The following discovery example uses the Node Exporter Service labels/port from kube-prometheus-stack 90.0.0 with release `kube-prom` in `monitoring`. The DCGM portion assumes verified Pods labeled `app: nvidia-dcgm-exporter` in `gpu-operator` with a named `metrics` container port; adjust it to the installed exporter. Neither resource installs an exporter. Match the Prometheus resource's monitor/namespace selectors, and avoid scraping the same exporter twice through an existing monitor.

`attachMetadata.node` makes Node discovery metadata available; it does not automatically copy labels to metrics. It requires Prometheus >=2.37 for ServiceMonitor or >=2.35 for PodMonitor and `list`/`watch` Node permission for Prometheus. The relabeling keeps actual `eks.amazonaws.com/compute-type=hybrid` nodes and creates stable `node`/`compute_type` target labels. Do not infer Hybrid placement from an SSM Node name prefix.

These examples use exporters' protected HTTP metrics endpoints, not the kubelet HTTPS endpoint. Restrict collector connectivity. If traffic crosses an untrusted boundary, configure exporter TLS/authentication or a reviewed proxy and the matching CA/authorization settings; do not use `insecureSkipVerify`. Keep kubelet scraping in its separately authenticated, CA-verified configuration.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-node-exporter
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app.kubernetes.io/name: prometheus-node-exporter
      app.kubernetes.io/instance: kube-prom
  namespaceSelector:
    matchNames: [monitoring]
  endpoints:
  - port: http-metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: hybrid-gpu-metrics
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames: [gpu-operator]
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
```

### Grafana Dashboard Query Examples

These queries require the target labels above and compatible exporter metrics. Verify units, GPU/MIG identity, unsupported-value/error sentinels, missing scrapes and duplicate series. GPU framebuffer usage divides by total capacity (`used + free`), not free capacity; zero-capacity series are excluded. The queries are locally testable expressions, not measurements from this environment.

```promql
# Host CPU utilization percent
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",compute_type="hybrid"}[5m])))

# Host memory utilization percent
100 * (1 - node_memory_MemAvailable_bytes{compute_type="hybrid"} / node_memory_MemTotal_bytes{compute_type="hybrid"})

# GPU utilization: this metric is already a percentage
DCGM_FI_DEV_GPU_UTIL{compute_type="hybrid"}

# GPU framebuffer usage: used / (used + free), excluding zero capacity
(100 * DCGM_FI_DEV_FB_USED{compute_type="hybrid"} /
 (DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}))
and
((DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}) > 0)
```

## Direct Connect Performance Validation

Separate a test plan from an AWS service guarantee. The former examples of RTT <5ms, variation <2ms, loss <0.01% and throughput >1Gbps are illustrative planning targets, not measured results or universal Direct Connect promises. Pick targets for the actual location, circuit, endpoint, workload and contracted capacity; confirm that the measured route uses Direct Connect rather than VPN or another path.

`ping` reports ICMP RTT and, on Linux iputils, RTT mdev. That dispersion is not the same statistic as one-way delay variation or iperf3's UDP jitter. ICMP filtering/deprioritization can differ from application traffic. A 1,000-packet test has 0.1% loss increments; observing zero losses does not prove a long-term loss rate below 0.01%.

Use an approved private test server with iperf3 already running, a coordinated window, a deliberate traffic cap and protected result storage. Do not run iperf3 against an EKS API endpoint. The bounded sample below requires Bash, Python3, iputils ping, GNU timeout and iperf3 with the shown options. Failure stops the sequence; missing tools, invalid JSON or an iperf3 error are not a passed performance test.

```bash
set -euo pipefail
umask 077
: "${PROBE_HOST:?Set the approved private test host}"
: "${TEST_BITRATE:?Set an approved traffic cap, for example 10M}"
: "${PRIVATE_RESULTS_ROOT:?Set an existing protected results directory}"
if [[ ! "$TEST_BITRATE" =~ ^[1-9][0-9]*[KMGT]?$ ]]; then
  printf 'TEST_BITRATE must be a positive integer with an optional K/M/G/T suffix.\n' >&2
  exit 2
fi
RUN_DIR=$(mktemp -d "$PRIVATE_RESULTS_ROOT/dx-check.XXXXXX")
date -u +%FT%TZ > "$RUN_DIR/started-at.txt"
LC_ALL=C ping -n -c 100 -W 2 "$PROBE_HOST" > "$RUN_DIR/ping.txt"
timeout 45s iperf3 --client "$PROBE_HOST" --connect-timeout 3000 \
  --time 10 --bitrate "$TEST_BITRATE" --json > "$RUN_DIR/iperf-tcp.json"
python3 - "$RUN_DIR/iperf-tcp.json" <<'PY'
import json, math, sys
with open(sys.argv[1]) as stream:
    result = json.load(stream)
if result.get("error") or not isinstance(result.get("end"), dict):
    raise SystemExit("iperf3 result is incomplete or reports an error")
received = result["end"].get("sum_received", {})
for field in ("bits_per_second", "bytes", "seconds"):
    value = received.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise SystemExit("Missing or invalid TCP receiver statistics")
if received["seconds"] <= 0:
    raise SystemExit("Invalid TCP test duration")
print("Saved a completed iperf3 result; compare receiver statistics with the approved test plan.")
PY
printf 'Private observations: %s; this does not establish an AWS latency/throughput guarantee.\n' "$RUN_DIR"
```

This capped TCP test does not establish maximum link capacity. Inspect receiver throughput, retransmissions, direction, duration and congestion. For a separately approved UDP test, use `--udp` and an explicit bitrate, then retain and interpret receiver loss/jitter from that version's JSON. Record failed/skipped probes as such. No network load test was executed during this audit.

## Certificate Renewal Management

Identify which certificate is being checked: the Harbor TLS server certificate, its CA chain, a kubelet serving certificate, the EKS control-plane CA, or the IAM Roles Anywhere host certificate. A valid CA certificate does not establish that the server leaf is valid, and a Node Ready heartbeat is not certificate-expiration evidence. EKS control-plane certificates are AWS-managed; do not run kubeadm renewal commands as an EKS repair procedure.

This local expiry check fails for a missing/unreadable/invalid certificate or one expiring within the example 30-day warning window. It does not validate the chain, hostname, revocation, or whether the service actually presents that certificate. Use the verified TLS connection below for the served endpoint and the [credential lifecycle procedure](./07-node-lifecycle.md) for host-certificate renewal.

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file to inspect}"
test -r "$CERT_PATH"
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
```

Track the actual issuer/owner, configured certificate path, expiration and alert delivery. Kubelet serving/client credential paths depend on configuration; enabling serverTLSBootstrap alone does not approve serving CSRs or rotate an IAM Roles Anywhere certificate.

## Ingress Configuration

### ALB Ingress (ip target mode)

The self-managed AWS Load Balancer Controller can register routable Hybrid Pod IPs using `alb.ingress.kubernetes.io/target-type: ip`. Routes, return traffic, security groups/firewalls and EKS remote Pod network configuration must agree.

AWS's mixed-mode webhook recipe places the controller on cloud nodes. This is a placement recommendation for that design, not a universal inability to run a webhook on Hybrid Nodes: the add-on guidance permits Hybrid placement when the control plane can reach the configured remote Pod CIDR. Prefer positive administrative placement labels over `compute-type NotIn [hybrid]`, which also matches nodes with no such label. The example label below must be assigned only to verified eligible cloud nodes.

```yaml
# Fragment under the controller Deployment's spec.template.spec:
nodeSelector:
  infrastructure.example.com/location: aws
```

### Cilium Ingress Controller

The Cilium Ingress and Gateway API examples in this section require an L7-enabled Cilium configuration. They do not apply to the same Cilium installation configured for [EKS Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md): its [AWS-required VTEP configuration](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html) sets `vtep.enabled=true` and `l7Proxy=false`. Choose the network design before enabling these features. This restriction concerns Cilium's L7 proxy features; it does not prohibit HTTP applications from using the gateway's routed network path.

Cilium 1.18.3's upstream Ingress prerequisites include NodePort support (or kube-proxy replacement), L7 proxy support and an available load-balancer exposure path. The fragment below is not permission to change the CNI of cloud nodes in a mixed cluster. Preserve the reviewed Hybrid Cilium configuration and confirm the AWS support boundary for additional features. Changing dedicated/shared mode can change addresses and interrupt existing connections.

```yaml
# Merge into the reviewed Cilium release values, not a full installation:
nodePort:
  enabled: true
l7Proxy: true
ingressController:
  enabled: true
  loadbalancerMode: dedicated
```

### Cilium Gateway API

Install the Gateway API CRDs and resource versions supported by the chosen controller release, verify its NodePort/kube-proxy replacement and L7 prerequisites, and check GatewayClass/Gateway/Route conditions. Setting one Helm flag alone does not install those CRDs or establish external reachability.

```yaml
# Required Gateway API CRDs and controller prerequisites must already be met:
gatewayAPI:
  enabled: true
```

### LoadBalancer IPAM (Cilium)

The following pool uses the `cilium.io/v2` API verified against the 1.18.3 CRD and selects only explicitly labeled Services. Replace the illustrative CIDR with a reserved, non-overlapping address range from the network inventory. IP allocation does not advertise the address to routers or guarantee a working data path.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: on-prem-pool
spec:
  blocks:
  - cidr: "10.80.100.0/24"
  serviceSelector:
    matchLabels:
      exposure: onprem-bgp
```

## Load Balancing

### NLB (ip target mode)

For the self-managed AWS Load Balancer Controller, use an owned `LoadBalancer` Service with `spec.loadBalancerClass: service.k8s.aws/nlb` and `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`, or the documented `aws-load-balancer-type: external` ownership path for the chosen controller. A target-type annotation alone does not select the controller. Hybrid Pod targets and return routes must be reachable from AWS; select internal/public exposure, subnets and access controls deliberately.

This is not an EKS Auto Mode ownership recipe. Do not switch the class/controller of an existing Service as an in-place migration without reviewing replacement and traffic effects.

### Cilium LB + BGP

Use the installed `cilium.io/v2` schemas. Service address types belong under `advertisements[].service.addresses`. The example advertises only LoadBalancer IPs for Services labeled `exposure: onprem-bgp`; it does not use a `NotIn` selector that effectively selects every Service.

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: hybrid-service-advertisement
  labels:
    advertise: hybrid-services
spec:
  advertisements:
  - advertisementType: Service
    service:
      addresses: [LoadBalancerIP]
    selector:
      matchLabels:
        exposure: onprem-bgp
```

Configure CiliumBGPClusterConfig node/peer selection and CiliumBGPPeerConfig families. The peer configuration's advertisement selector must match `advertise: hybrid-services`; the Service selector must match the actual Service labels. Enable the reviewed BGP control plane, establish router sessions and validate accepted routes, next hops, return paths and traffic policy. An IPPool/Advertisement alone is incomplete. See the [networking foundation](./02-network-configuration.md) and the installed version's BGP documentation before applying changes.

## Add-on Detailed Settings

### CloudWatch Observability Agent

Use the supported Pod Identity configuration and verify the workload's actual IAM association and permissions. The Hybrid compatibility variable `RUN_WITH_IRSA` is still required by the current AWS procedure despite its name. Add it to the existing `AmazonCloudWatchAgent` resource's **spec.env list**, preserving entries such as `K8S_NODE_NAME`; it is not an arbitrary top-level `env` in EKS add-on configurationValues.

```yaml
# Add this item to the existing AmazonCloudWatchAgent.spec.env list:
- name: RUN_WITH_IRSA
  value: "True"
```

Inspect `amazoncloudwatchagents/cloudwatch-agent` in namespace `amazon-cloudwatch` before editing and review how the add-on/operator reconciles that configuration. Confirm agent rollout and collection afterward. Hybrid cluster/workload/Pod/container metrics are available, but node-level Container Insights metrics are unavailable because their EC2 IMDS dependency is absent. If its operator runs on Hybrid Nodes, satisfy control-plane webhook reachability.

### EKS Pod Identity Agent

| Host OS | Documented minimum | Hybrid DaemonSet / credential path |
| --- | --- | --- |
| Ubuntu, RHEL, AL2023 | Add-on 1.3.3-eksbuild.1 | `hybrid`; `/eks-hybrid/.aws/credentials` |
| Bottlerocket (supported VMware variants) | Add-on 1.3.7-eksbuild.2 and OS 1.39.0 | `hybrid-bottlerocket`; `/var/eks-hybrid/.aws/credentials` |

These are feature floors, not a recommendation to install an old release. Select a currently compatible add-on version and inspect its configuration schema. On Ubuntu/RHEL/AL2023, merge this fragment into each host's existing complete NodeConfig:

```yaml
# Merge this fragment into each host's complete, protected NodeConfig:
spec:
  hybrid:
    enableCredentialsFile: true
```

AWS requires a planned `nodeadm init -c file:///path/to/nodeconfig.yaml` reconciliation on each affected host, including already joined nodes. Do not blindly reinitialize every production node: preserve identity/configuration, follow the lifecycle procedure, and validate one host at a time. Bottlerocket uses its documented settings path rather than this nodeadm fragment. These temporary credential files are sensitive; do not print them.

For the non-Bottlerocket Hybrid DaemonSet, the add-on configuration includes:

```json
{
  "daemonsets": {
    "hybrid": {
      "create": true
    }
  }
}
```

For Bottlerocket use the documented `hybrid-bottlerocket` configuration for the selected version. Inspect and merge existing settings. Create an add-on only if absent; update an existing one with reviewed conflict handling rather than blindly using create or OVERWRITE. The agent and credentials file do not create every application's Pod Identity association: verify namespace, ServiceAccount, IAM role trust/permissions, SDK credential resolution and successful authorization.

## Mixed-Mode Webhook Operations

In AWS's supported mixed-mode pattern, VPC CNI runs on cloud nodes and Cilium/Calico on Hybrid Nodes. AWS recommends cloud placement for webhooks in that pattern. A Hybrid-hosted webhook additionally needs a routable remote Pod CIDR and control-plane reachability; inspect the actual endpoint rather than assuming every webhook must or can run anywhere.

### CoreDNS Placement

AWS recommends at least one CoreDNS replica on cloud nodes and one on Hybrid Nodes for this mixed-mode design. Verify at least two desired replicas, eligible capacity, selectors, tolerations and real endpoints. `maxSkew: 1` alone does not create two domains or guarantee one Pod per domain, and cloud nodes may lack the `eks.amazonaws.com/compute-type` label.

For clusters supporting `minDomains`, this Pod-spec fragment uses an explicit administrative two-domain label. Label only the intended DNS nodes and give every eligible node a verified `location` value of exactly `aws` or `onprem`. Keep existing affinity/tolerations compatible, verify the CoreDNS Pod labels, and reconcile changes through the add-on's supported configuration mechanism.

```yaml
# Fragment under CoreDNS Deployment.spec.template.spec.
# Label eligible nodes with exactly aws or onprem in this administrative domain.
nodeSelector:
  infrastructure.example.com/dns-eligible: "true"
topologySpreadConstraints:
- maxSkew: 1
  minDomains: 2
  topologyKey: infrastructure.example.com/location
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      k8s-app: kube-dns
```

With two eligible domains and at least two replicas, strict spreading constrains scheduling across them. If a domain has no capacity, new replicas can remain Pending; this is an availability tradeoff, not guaranteed failover. Test the actual DNS Service/EndpointSlices and local/remote resolution. In clusters containing Auto Mode, distinguish its node-local DNS system service from the Deployment still needed for non-Auto nodes.

<span id="per-add-on-nodeaffinity-settings-guide"></span>

### Per-Add-On Placement Guide

| Add-on | Placement in this design | Required check |
| --- | --- | --- |
| AWS Load Balancer Controller | Cloud nodes in AWS's mixed-mode recipe | Webhook reachability, positive labels, routable Hybrid IP targets |
| CloudWatch agent/operator | Agent on supported target nodes; operator webhooks preferably cloud | IAM/agent health; Hybrid node-level metrics excluded |
| cert-manager | Webhook preferably cloud; routable Hybrid placement is possible | Control-plane access and remote Pod network |
| Metrics Server | Cloud placement or a reachable Hybrid Pod endpoint | Control-plane-to-Pod and Metrics-Server-to-kubelet paths |
| CoreDNS | Verify replicas on cloud and Hybrid nodes | Eligible domains, capacity and actual DNS traffic |
| Cilium/Calico | Hybrid nodes in the AWS-supported mixed-CNI design | Preserve VPC CNI on cloud nodes |

## Common Troubleshooting

### ImagePullBackOff Diagnosis

Read Pod events and inspect the referenced Secret name/type without decoding or printing registry credentials. The Secret must be in the Pod's namespace. Confirm the registry hostname, required repository permission and credential expiry through the credential owner; metadata alone cannot prove authentication succeeds.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${NAMESPACE:?Set the workload namespace}" "${POD:?Set the affected Pod}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe pod "$POD"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{.spec.imagePullSecrets[*].name}{"\n"}'
: "${PULL_SECRET:?Set a referenced imagePullSecret in that namespace}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$PULL_SECRET" \
  -o jsonpath='{.type}{"\n"}'
```

Run a TLS check from the actual host/network path with the trusted CA and hostname verification enabled. Do not use curl -k or interpret an unauthenticated registry 401 response as a TLS failure. Bash, OpenSSL and GNU timeout are required by this example.

```bash
set -euo pipefail
: "${HARBOR_HOST:?Set the registry DNS name, without scheme or port}"
: "${HARBOR_CA_FILE:?Set the approved CA bundle file}"
timeout 10s openssl s_client -connect "$HARBOR_HOST:443" \
  -servername "$HARBOR_HOST" -verify_hostname "$HARBOR_HOST" \
  -verify_return_error -CAfile "$HARBOR_CA_FILE" </dev/null
```

For DNS/network testing inside a Pod, use an approved diagnostic image pinned by digest, a dedicated namespace and explicit placement on the affected Hybrid Node. An arbitrary unpinned debug Pod can run on a cloud node and test the wrong path. Review Pod creation/deletion separately and retain the scoped results.

### DNS Resolution Issues

Inspect the actual CoreDNS Deployment/Pods, Service and EndpointSlices, their cloud/on-premises placement, DNS configuration and network reachability. Test the registry name and kubernetes.default.svc.cluster.local from the affected workload environment. API, DNS or log-access failures are unknown observations, not successful checks.

Do not restart every CoreDNS Pod as the default diagnostic action. Determine the failing layer first and coordinate any restart with redundancy and recovery checks. Mixed clusters with Auto Mode may have node-local DNS behavior; identify which resolver path the failing Pod actually uses.

### Node Connectivity Issues

Use the inventory's actual Node name and mapped host. SSM-backed Node names need not start with hybrid- or resolve as hostnames.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}" "${NODE:?Set the actual registered Node name}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" describe node "$NODE"
```

```bash
# Run on the mapped host, not a hostname guessed from the Node name.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' \
  --no-pager -n 200
```

Check the credential provider and OS-specific agent unit (including the Ubuntu snap-based SSM installation when applicable). For network/authentication diagnosis, use the verified `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` procedure with root privileges and private output retention. It contacts AWS and the cluster; do not log issued credentials or disable TLS verification.

There is no `nodeadm reset` subcommand in the reviewed 1.0.20 CLI. NotReady is not a reason to blindly deregister/reinitialize a host. Follow [recovery and identity reconciliation](./07-node-lifecycle.md) after determining the fault, preserving mounts/data and recording node/SSM identities.

## Validation Scope and References

Local checks cover pinned resource schemas, four PromQL expressions with synthetic samples and eleven backup/network command-double cases. No AWS/Kubernetes changes, actual backup/restore, network load test, BGP session, exporter scrape or production rollout was executed. Select EKS/OS/CNI/add-on combinations from current AWS support documentation before deployment.

- [AWS Hybrid add-ons](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [AWS Hybrid webhooks](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [AWS Hybrid upgrades](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [Cilium 1.18.3 Ingress prerequisites](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/servicemesh/ingress.rst)
- [Cilium 1.18.3 LoadBalancer IPPool CRD](https://github.com/cilium/cilium/blob/v1.18.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumloadbalancerippools.yaml)
- [iperf3 invocation](https://software.es.net/iperf/invoking.html)
- [Kubernetes taint tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)


---

< [Previous: Node Lifecycle Management](./07-node-lifecycle.md) | [Table of Contents](./README.md) | [Next: Bare Metal OS Setup](./09-bare-metal-os-setup.md) >
