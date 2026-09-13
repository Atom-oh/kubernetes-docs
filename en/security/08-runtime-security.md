# Runtime Security

> **Last Updated**: September 13, 2026
> **Validation baseline**: Falco 0.44.1 / chart 9.1.0, Falcosidekick 2.35.0 / chart 0.14.0, Tetragon 1.7.1. Verify support for the actual kernel, OS, and node type.

Runtime security observes process, file, and network activity and restricts selected operations through tested policies. **An alert is not proof of compromise; detection and prevention require separate tests.** This guide was checked with local CLIs, schemas, Helm, and synthetic events. No real cluster, kernel BPF program, or notification channel was used.

<span id="container-runtime-threats"></span>
<span id="detection-technologies"></span>

## Runtime Threat Landscape

| Observation point | What it can show | Limits |
|---|---|---|
| Syscall/kernel hook | Process execution, file access, connection attempts | Check dropped events, privileges, kernel support, and filters |
| Kubernetes audit | API requester, verb, object, response status | Does not show every process/file operation inside a Pod |
| Network flow | Connections, drops, policy verdicts | A port or encrypted connection alone does not establish malicious intent |
| Image/admission policy | Vulnerabilities, signatures, Pod settings | Does not detect every post-deployment behavior |

eBPF alone does not guarantee low overhead or safety. Measure hooks, event volume, filtering, output cost, CPU, and memory on the actual nodes. Do not automatically kill a production process merely because its command name matches an indicator.

<span id="default-rule-examples"></span>

## Falco

### Falco Overview

Falco evaluates events against rules. A typical syscall path is `Linux event → modern eBPF/kmod capture → Falco filter/rule → JSON output → Falcosidekick → notification/storage`. Slack and PagerDuty are downstream integrations, not native Slack clients inside the Falco rule engine.

The 0.44.1 distribution bundles container plugin 0.7.1. It supplies fields such as container.id, so disabling every plugin prevents rules using those fields from compiling/running. Verify runtime sockets, Kubernetes metadata collection, and access permissions.

### Falco Installation (EKS)

This example targets Linux EC2 nodes whose host access you manage. Do not assume that a DaemonSet can run on Fargate or other restricted hosts. Verify modern eBPF kernel/BTF/capability requirements. Chart 9.1.0 supports explicit driver kinds `modern_ebpf` and `kmod`; do not retain the old `ebpf` setting.

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update falcosecurity
helm upgrade --install falcosidekick falcosecurity/falcosidekick \
  --version 0.14.0 --namespace falco --create-namespace \
  --values falcosidekick-values.yaml
helm upgrade --install falco falcosecurity/falco \
  --version 9.1.0 --namespace falco \
  --values falco-values.yaml
```

The Sidekick chart's appVersion differs from its default image tag, so the example explicitly pins image.tag to 2.35.0. Prepare its output credential Secret and Prometheus Operator CRDs first. A missing Secret can prevent Pod startup. Disable unused notification/metrics options in a minimal lab.

```yaml
driver:
  kind: modern_ebpf
metrics:
  enabled: true
serviceMonitor:
  create: true
falcosidekick:
  enabled: false
falco:
  json_output: true
  json_include_output_property: true
  http_output:
    enabled: true
    url: http://falcosidekick.falco.svc:2801
customRules:
  documentation-rules.yaml: "- macro: doc_spawned\n  condition: evt.type in (execve,\
    \ execveat) and evt.res = SUCCESS\n- macro: doc_container\n  condition: container.id\
    \ != host\n- rule: Documentation shell execution\n  desc: Observe successful shell\
    \ process execution in a container; not proof of compromise.\n  condition: doc_spawned\
    \ and doc_container and proc.name in (bash, sh, dash, zsh)\n  output: Shell process\
    \ observed (proc=%proc.name command=%proc.cmdline container=%container.id)\n \
    \ priority: NOTICE\n  tags:\n  - documentation\n  - process\n- rule: Documentation\
    \ service account token read\n  desc: Observe read access to the default projected\
    \ service account token path; legitimate\n    clients also read it.\n  condition:\
    \ evt.type in (open, openat, openat2) and evt.is_open_read\n    = true and fd.num\
    \ >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/\n\
    \  output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)\n\
    \  priority: NOTICE\n  tags:\n  - documentation\n  - credential_access\n"
```


The configuration sends HTTP to the separately installed falcosidekick ClusterIP Service. Sharing a namespace does not authenticate or encrypt traffic. Configure access policy and TLS/mTLS according to the actual trust boundary and verify node/Falco connectivity. Falco uses snake_case fields such as json_output and http_output. Old jsonOutput/httpOutput and removed grpc settings fail the 0.44.1 schema.

### Falco Rule Structure

These rules define their own required macros and avoid replacing default rule names. Use the pinned ruleset's override syntax when intentionally changing an existing rule.

```yaml
- macro: doc_spawned
  condition: evt.type in (execve, execveat) and evt.res = SUCCESS
- macro: doc_container
  condition: container.id != host
- rule: Documentation shell execution
  desc: Observe successful shell process execution in a container; not proof of compromise.
  condition: doc_spawned and doc_container and proc.name in (bash, sh, dash, zsh)
  output: Shell process observed (proc=%proc.name command=%proc.cmdline container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - process
- rule: Documentation service account token read
  desc: Observe read access to the default projected service account token path; legitimate
    clients also read it.
  condition: evt.type in (open, openat, openat2) and evt.is_open_read
    = true and fd.num >= 0 and doc_container and fd.name startswith /var/run/secrets/kubernetes.io/serviceaccount/
  output: Service account path read (proc=%proc.name file=%fd.name container=%container.id)
  priority: NOTICE
  tags:
  - documentation
  - credential_access
```


After removal of enter events, Falco 0.44.1 warns that evt.dir is deprecated. These examples select successful exec and read events directly. Legitimate Kubernetes clients read service account tokens, so the read signal alone is not “unauthorized access.” Combine it with workload baselines, approved binaries, and Pod identity.

### Writing Custom Rules

| Pattern | Possible signal | Required qualification |
|---|---|---|
| Suspected mining | Process names, pool/stratum strings, unusual resource use | Renaming and legitimate computation can defeat or trigger heuristics |
| Suspected reverse shell | Connection strings in shell argv and unusual outbound flows | An exec event's fd.name is not proof of a network connection |
| Privilege escalation | Credential changes, SUID settings, capabilities | Check user.uid/proc.uid/proc.suid meaning and successful operation |
| Suspected escape | Namespace/host-path access and unusual mounts | nsenter or /.dockerenv strings do not establish successful escape |

Rule compilation does not measure detection effectiveness. Test synthetic/authorized lab events, normal workloads, missing metadata, and drop counters before staged rollout. Arguments, paths, and logs may contain secrets; restrict event fields, retention, and access.

### Falco Alert Configuration

```yaml
config:
  existingSecret: falcosidekick-output-credentials
  slack:
    minimumpriority: warning
  pagerduty:
    minimumpriority: critical
  aws:
    region: ap-northeast-2
    cloudwatchlogs:
      loggroup: /falco/alerts
      logstream: documentation
      minimumpriority: warning
  elasticsearch:
    minimumpriority: warning
    checkcert: true
webui:
  enabled: false
serviceMonitor:
  enabled: true
image:
  tag: 2.35.0
```


falcosidekick-output-credentials is an existing same-namespace Secret read through envFrom. Supply only the approved outputs' variables, such as SLACK_WEBHOOKURL, PAGERDUTY_ROUTINGKEY, and ELASTICSEARCH_HOSTPORT/USERNAME/PASSWORD, through your secret-management process. Writing `${ELASTIC_PASSWORD}` inside Helm values does not perform shell substitution. Do not expose credentials in Git, command lines, or review logs.

AWS settings belong under config.aws. Verify workload identity and scope IAM actions/resources to the intended log groups/streams. minimumpriority uses emergency/alert/critical/error/warning/notice/informational/debug, not `high`. Check each output's activation conditions, retries, and failure metrics. The example disables the Web UI.

<span id="tetragon-installation"></span>
<span id="tracingpolicy-basic-structure"></span>
<span id="process-monitoring"></span>

## Tetragon

### Tetragon Overview

Tetragon can run independently of the Cilium CNI. Distinguish built-in process_exec/exit events from additional TracingPolicy hooks. The flow is `kernel hook → selector → Post/supported action → JSON/gRPC/metrics`; the Kubernetes CRD itself does not execute inside the kernel.

```bash
helm repo add cilium https://helm.cilium.io
helm repo update cilium
helm upgrade --install tetragon cilium/tetragon \
  --version 1.7.1 --namespace kube-system --values tetragon-values.yaml
```

```yaml
tetragon:
  enableProcessCred: true
  enableProcessNs: true
```


Check operator/CRD readiness and each node's kernel, BTF, and capabilities. Helm rendering does not establish hook attachment. The namespaced examples target demo-app workloads; confirm effective scope for the chosen policy type and hook.

### File Access Monitoring

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-file-observe
  namespace: demo-app
spec:
  kprobes:
  - call: security_file_permission
    syscall: false
    args:
    - index: 0
      type: file
    - index: 1
      type: int
    selectors:
    - matchArgs:
      - index: 0
        operator: Prefix
        values:
        - /etc/shadow
        - /root/.ssh/
      - index: 1
        operator: Mask
        values:
        - '4'
      matchActions:
      - action: Post
```


The second argument of `security_file_permission(struct file *, int mask)` is a permission mask: MAY_READ=4, MAY_WRITE=2. Assigning “index 1 = open flags” to the single-argument security_file_open function is incorrect. Open flags O_WRONLY=1/O_RDWR=2 also differ from this permission mask. This hook alone does not cover every mmap/truncate/file mutation.

### Network Monitoring

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicyNamespaced
metadata:
  name: documentation-outbound-observe
  namespace: demo-app
spec:
  kprobes:
  - call: tcp_connect
    syscall: false
    args:
    - index: 0
      type: sock
    selectors:
    - matchArgs:
      - index: 0
        operator: DPort
        values:
        - '22'
        - '4444'
        - '5555'
      matchActions:
      - action: Post
```


tcp_connect observes TCP connection attempts. A destination port alone does not imply malicious traffic or policy rejection. UDP port 53 activity does not provide a complete DNS question/answer analysis; use the appropriate DNS telemetry path.

### Runtime Enforcement

Begin with Post/monitor behavior and check normal operations and false positives. Sigkill sends a signal; depending on the hook and kernel behavior, it cannot undo effects that already happened. Return-value override requires a supported syscall/security function, kernel settings, and an appropriate error result. Arbitrary kprobes do not all support it.

Do not claim universal mining/reverse-shell prevention from filenames or argv strings. execve argv is an array of pointers, not one string argument. Reading it as a single string does not inspect the complete command line as intended. Distinguish process-event argument filtering from kernel actions and validate enforcement in an approved, narrowly scoped lab.

### Tetragon CLI Usage

```bash
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents -o json
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact --namespace production --process curl
# Filter stored synthetic events locally:
tetra getevents -o json --namespace demo-app < events.jsonl
```

Executing against a DaemonSet selects a Pod/node's agent; this is not cluster-wide aggregation. Only the stdin filtering path was exercised here. The 1.7.1 implementation of tetra tracingpolicy modify also creates a gRPC client, so it was not used as an offline validator.

<span id="feature-comparison-table"></span>
<span id="use-case-recommendations"></span>

## Falco vs Tetragon Comparison

| Criterion | Falco | Tetragon |
|---|---|---|
| Policy | Event conditions and rulesets | Kernel hooks, selectors, actions |
| Common use | Detection with notification/storage integration | Process visibility and explicit hook enforcement |
| Operational checks | Driver/plugin/runtime metadata and dropped events | BTF/hook support, policy scope, side effects |
| Performance | Measure CPU/memory/event loss under actual load | Use the same workload; eBPF alone does not establish superiority |

Deploying both is not automatically the best choice. Consider duplicate collection, node privileges, cost, operational complexity, and required enforcement.

## Kubernetes Audit Logging

### Audit Policy Configuration

This policy is for a **self-managed Kubernetes API server**. EKS's managed audit policy is not replaced by applying this YAML. Enable EKS control-plane audit logs and configure CloudWatch access, retention, and encryption.

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages:
- RequestReceived
rules:
- level: Metadata
  resources:
  - group: ''
    resources:
    - secrets
    - serviceaccounts/token
- level: Metadata
  resources:
  - group: ''
    resources:
    - pods/exec
    - pods/attach
    - pods/portforward
- level: Request
  resources:
  - group: rbac.authorization.k8s.io
    resources:
    - roles
    - rolebindings
    - clusterroles
    - clusterrolebindings
  verbs:
  - create
  - update
  - patch
  - delete
- level: Metadata
```


Request/RequestResponse logging of Secrets and serviceaccounts/token can persist credential bodies, so use Metadata. Audit rules are first-match; put sensitive-resource rules first. system:anonymous alone does not capture every authentication failure. Examine audit stages, responseStatus, and authentication logs. An exec audit record is not a recording of every command inside the terminal session.

### EKS Audit Log Analysis

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name, responseStatus.code
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

This is a CloudWatch Logs Insights query, not Bash. A 403 is a rejected response; classify successful reads separately. Verify collection after logging is enabled and configure retention.

<span id="cryptocurrency-mining-detection"></span>
<span id="reverse-shell-detection"></span>
<span id="privilege-escalation-detection"></span>

## Runtime Threat Detection Patterns

Seccomp restricts syscalls, but rejection does not always terminate a process. Actions can return ERRNO, kill, or notify. RuntimeDefault means the runtime's profile; set it explicitly or verify kubelet seccompDefault. Kubernetes 1.27+ alone does not automatically apply it to every Pod.

AppArmor needs node support and loaded profiles. Complain mode records ordinary violations, while explicit deny rules can still block. readOnlyRootFilesystem is a container securityContext field; it does not prevent malicious use of writable volumes, network access, or memory.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: runtime-security-demo
  namespace: demo-app
  labels:
    app: runtime-security-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_APPROVED_VERSION
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 64Mi
```


Current GuardDuty Runtime Monitoring supports EKS EC2 nodes and EKS Auto Mode, but not EKS Hybrid Nodes or EKS Fargate. Check the official OS/kernel/architecture/agent-version matrix and coverage health. Enabling the feature does not establish healthy coverage for every node.

Hubble `--verdict DROPPED` shows drops; not every drop is a NetworkPolicy denial. Inspect the drop reason and policy verdict together.

<span id="forensics-container"></span>

## Incident Response

### Pod Isolation Procedure

Standard NetworkPolicy allows combine as a union. Adding a policy with empty ingress/egress lists does not override connections allowed by another policy. An app label can select multiple Pods belonging to the application.

1. Identify namespace, Pod UID, node, owner, and existing network policies.
2. Choose an approved isolation mechanism. For a CNI-specific explicit deny or changes to existing allows, review exact targets, impact, and recovery.
3. Test established and new connections; account for hostNetwork, node traffic, and CNI limitations.
4. Protect evidence and record isolation, interruption, and recovery decisions.

### Evidence Collection and Forensics

```bash
#!/usr/bin/env bash
# Authorized read-only Kubernetes API collection. Sensitive output stays in a private directory.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  printf 'Usage: %s NAMESPACE POD OUTPUT_DIRECTORY\n' "$0" >&2
  exit 2
fi
namespace=$1
pod_name=$2
evidence_dir=$3
if [[ ! $namespace =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || [[ ! $pod_name =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]]; then
  printf 'Invalid namespace or pod name\n' >&2
  exit 2
fi
umask 077
mkdir -- "$evidence_dir"
kubectl get pod "$pod_name" -n "$namespace" -o json > "$evidence_dir/pod.json"
kubectl describe pod "$pod_name" -n "$namespace" > "$evidence_dir/describe.txt"
kubectl logs "$pod_name" -n "$namespace" --all-containers=true --timestamps=true > "$evidence_dir/logs.txt"
# Previous logs may not exist. Record this separately instead of calling collection complete silently.
if ! kubectl logs "$pod_name" -n "$namespace" --all-containers=true --previous=true --timestamps=true > "$evidence_dir/previous-logs.txt" 2> "$evidence_dir/previous-logs-error.txt"; then
  printf 'Previous logs unavailable; inspect previous-logs-error.txt\n' >&2
fi
(
  cd -- "$evidence_dir"
  sha256sum -- pod.json describe.txt logs.txt previous-logs.txt previous-logs-error.txt > SHA256SUMS
)
printf 'API evidence written to %s. This is not a memory or filesystem snapshot.\n' "$evidence_dir"
```


This script collects Pod metadata/logs through the API and records checksums. It was tested with a subprocess double, including failures and private 0700 output directories, not against a real cluster. Pod specs and logs can contain secrets/personal information; use approved storage and access controls.

A new forensic Pod does not automatically run on the target node or share the target process namespace. hostPath /proc, SYS_PTRACE, and NET_ADMIN grant substantial access; use an approved procedure when required. emptyDir is not durable evidence storage. Archiving an ephemeral container's `/` is not automatically a snapshot of the target container filesystem.

<span id="falco-to-elasticsearch"></span>
<span id="prometheus-grafana-dashboard"></span>

## SIEM/SOAR Integration

Compare ServiceMonitor namespaces, selectors, and ports with actual Services. The Falco chart has a metrics Service; Falcosidekick exposes metrics on its HTTP port. The Sidekick chart renders a ServiceMonitor only when monitoring.coreos.com/v1 is available.

```promql
sum by (priority) (rate(falcosecurity_falcosidekick_falco_events_total[5m]))
```

This is the Falcosidekick 2.35.0 received-event counter. Do not treat the original falco_events_total as a universal metric name. Distinguish cumulative counts from interval rates; check actual labels, resets, output failures, and missing scrapes. Coordinate even synthetic Slack/PagerDuty/SIEM notification tests with the recipients and operational process.

<span id="table-of-contents"></span>
<span id="recommendations"></span>

## Summary

Local checks covered two Falco rules, four configuration-schema cases, three Tetragon JSON filters and two CRDs, three Helm charts, and four evidence-script success/failure cases. Kernel attachment, detection efficacy, actual enforcement, GuardDuty coverage, audit/CloudWatch collection, and external notifications were not executed.

## References

- [Falco Kubernetes installation](https://falco.org/docs/setup/kubernetes/)
- [Falco 0.44.1 configuration](https://github.com/falcosecurity/falco/blob/0.44.1/falco.yaml)
- [Falcosidekick 2.35.0 configuration](https://github.com/falcosecurity/falcosidekick/blob/2.35.0/config_example.yaml)
- [Tetragon tracing policies](https://tetragon.io/docs/concepts/tracing-policy/)
- [Tetragon enforcement](https://tetragon.io/docs/concepts/enforcement/)
- [Tetragon 1.7.1 file monitoring](https://github.com/cilium/tetragon/blob/v1.7.1/examples/quickstart/file_monitoring.yaml)
- [Kubernetes audit](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [AppArmor](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [EKS control-plane logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [GuardDuty EKS runtime requirements](https://docs.aws.amazon.com/guardduty/latest/ug/prereq-runtime-monitoring-eks-support.html)
- [MITRE ATT&CK Containers](https://attack.mitre.org/matrices/enterprise/containers/)
