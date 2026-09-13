# EKS Hybrid Nodes Operations Quiz

> **Last Updated**: September 13, 2026

> **Related Document**: [Operations](../../eks-hybrid-nodes/08-operations.md)

## Multiple Choice Questions

<span id="_1-what-is-the-recommended-tool-combination-for-node-monitoring-in-hybrid-nodes-environments"></span>

### 1. Which combination can provide host metrics and dashboards for Hybrid Nodes?

- A) Notepad and manual recording
- B) Prometheus, Grafana and a correctly configured Node Exporter
- C) Email notifications only
- D) Manual log review only

<details>
<summary>Show Answer</summary>

**Answer: B) Prometheus, Grafana and a correctly configured Node Exporter**

**Explanation:**

Prometheus collects metrics, Grafana displays them, Node Exporter exposes host metrics, DCGM Exporter exposes supported GPU metrics, and Alertmanager routes alerts. This is one valid stack, not the only supported option. Install reviewed charts/add-ons and verify host mounts, identity, placement, TLS, authentication and actual scrape targets. A partial DaemonSet without matching selectors/template labels is not a working installation. Container Insights does not provide Hybrid host-level metrics through unavailable EC2 IMDS.


</details>

<span id="_2-how-do-you-check-when-kubelet-certificate-renewal-is-needed"></span>

### 2. How should you check the expiration of a configured node or service certificate?

- A) Assume certificates never expire
- B) Inspect the actual certificate with OpenSSL and identify its issuer/renewal owner
- C) Wait for Node NotReady
- D) Renew every certificate manually every day

<details>
<summary>Show Answer</summary>

**Answer: B) Inspect the actual certificate with OpenSSL and identify its issuer/renewal owner**

**Explanation:**

First distinguish kubelet serving/client certificates, the EKS control-plane CA, Harbor TLS and IAM Roles Anywhere host certificates. Hybrid IAM authentication does not imply a kubelet-client-current.pem file exists. kubeadm renewal commands do not manage the EKS control plane. An expiration check is separate from chain, hostname, revocation and live authentication checks. serverTLSBootstrap alone does not approve serving CSRs or renew an IAM Roles Anywhere certificate.

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file}"
openssl x509 -in "$CERT_PATH" -checkend 604800 -noout
```

This example warns within seven days; choose the threshold for the certificate lifetime and renewal policy. Missing or invalid files fail.

</details>

<span id="_3-what-is-the-first-troubleshooting-step-when-kubelet-is-not-responding-on-a-hybrid-node"></span>

### 3. What should you inspect first when kubelet stops responding on a Hybrid Node?

- A) Restart the entire cluster
- B) Inspect the mapped host service status, recent logs and supporting dependencies
- C) Create a replacement without investigation
- D) Delete all Pods

<details>
<summary>Show Answer</summary>

**Answer: B) Inspect the mapped host service status, recent logs and supporting dependencies**

**Explanation:**

Identify the registered Node and its actual host, then inspect kubelet/containerd status, finite recent journal output, disk/memory and the verified network/credential path. Do not disable TLS, dump registry credentials, or run nodeadm reset: that subcommand is absent from the reviewed Hybrid CLI. A restart or re-registration is a separate recovery decision; preserve diagnostics and follow the lifecycle guide.

```bash
# On the verified host, not a hostname guessed from its Kubernetes Node name:
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' --no-pager -n 200
```

</details>

<span id="_4-what-command-is-used-to-safely-move-workloads-for-node-maintenance"></span>

### 4. Which command requests workload eviction for planned node maintenance?

- A) kubectl delete node
- B) kubectl drain
- C) kubectl cordon alone
- D) kubectl delete pods --all

<details>
<summary>Show Answer</summary>

**Answer: B) kubectl drain**

**Explanation:**

drain marks the Node unschedulable and normally uses the Eviction API, respecting applicable PDBs. Controllers may create replacement Pods; the command does not transfer memory or guarantee application continuity. Check spare capacity, placement, storage and local data before draining. Do not routinely bypass eviction, discard emptyDir data or override every Pod termination period. Uncordon only after successful host/workload validation and only if the Node was originally schedulable.

| Command | Scope |
| --- | --- |
| cordon | Prevent normal new scheduling |
| drain | Cordon and request eviction, with exemptions/constraints |
| uncordon | Restore scheduling; not a health test |

A PDB with minAvailable: 2 permits one voluntary disruption only when three matching healthy replicas are available. A PDB does not prevent node loss or all application errors.

</details>

<span id="_5-what-is-the-recommended-solution-for-centralizing-logs-from-hybrid-nodes"></span>

### 5. Which option can centralize Hybrid workload logs?

- A) Copy every log manually
- B) Use a configured Fluent Bit/Fluentd collector and a protected central backend
- C) Collect no logs
- D) Read console output only

<details>
<summary>Show Answer</summary>

**Answer: B) Use a configured Fluent Bit/Fluentd collector and a protected central backend**

**Explanation:**

Configure the actual container runtime log path and parser, Kubernetes metadata permissions, buffers/checkpoints, retries and authenticated TLS output. Containerd commonly uses /var/log/containers symlinks into /var/log/pods; do not copy an old Docker-only /var/lib/docker/containers manifest. The collector needs the appropriate read-only host mounts and a deliberate state-storage policy. Collection is not a guarantee of zero log loss.

```text
Hybrid Nodes → configured collectors → CloudWatch Logs / Loki / Elasticsearch
                       ↓
              protected buffers and checkpoints
```

</details>

<span id="_6-what-is-the-default-wait-time-before-automatically-rescheduling-pods-to-other-nodes-when-a-node-fails"></span>

### 6. With the default admission behavior and no explicit override, what NoExecute toleration duration is added for not-ready and unreachable to ordinary Pods?

- A) 0 seconds
- B) 30 seconds
- C) 300 seconds
- D) 1 hour

<details>
<summary>Show Answer</summary>

**Answer: C) 300 seconds**

**Explanation:**

Kubernetes normally adds tolerationSeconds: 300 for both taints unless explicitly set. This is a taint-toleration duration, not a guarantee that replacement workloads become Ready exactly five minutes after node failure. Detection, tainting, controller behavior, capacity, volumes and startup add constraints. DaemonSet Pods normally tolerate these taints indefinitely. Shortening the duration does not prove the old process has stopped during a partition; stateful writers may require fencing.

```yaml
# Fragment under Pod spec or a workload's PodTemplate.spec, not a complete Pod:
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
```

The explicit 60-second example requires a tested availability/data-safety decision; it does not define a 60-second recovery SLO.

</details>

<span id="_7-what-is-the-recommended-strategy-for-eks-hybrid-nodes-upgrades"></span>

### 7. Which approach follows the AWS Hybrid Nodes upgrade guidance?

- A) Upgrade every node simultaneously
- B) Prefer new hosts and a controlled cutover; otherwise use validated in-place steps one node at a time
- C) Delete the cluster and recreate it for every upgrade
- D) Never upgrade

<details>
<summary>Show Answer</summary>

**Answer: B) Prefer new hosts and a controlled cutover; otherwise use validated in-place steps one node at a time**

**Explanation:**

AWS prefers replacement hosts and migration when spare capacity exists. In-place nodeadm upgrade is disruptive and takes a Kubernetes major.minor argument. Follow the lifecycle guide for skew, drain/data review, the actual host operation, Node UID/full version/new Lease and workload checks. A fixed sleep or an old Ready condition is not acceptance evidence. Do not claim a rolling sequence guarantees zero service interruption.

Before each wave, check backups, PDBs, available capacity, version compatibility, credential identity and the recovery plan. Stop on errors and retain evidence; do not automatically uncordon a failed node.

</details>

