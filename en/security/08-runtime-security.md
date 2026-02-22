# Runtime Security

> **Supported Versions**: Falco 0.39+, Tetragon 1.2+, Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 21, 2026

Runtime security involves detecting and responding to malicious activity and anomalous behavior while containers are running. This document covers runtime security strategies centered on Falco and Tetragon.

## Table of Contents

1. [Runtime Threat Landscape](#runtime-threat-landscape)
2. [Falco](#falco)
3. [Tetragon](#tetragon)
4. [Falco vs Tetragon Comparison](#falco-vs-tetragon-comparison)
5. [Kubernetes Audit Logging](#kubernetes-audit-logging)
6. [Runtime Threat Detection Patterns](#runtime-threat-detection-patterns)
7. [Incident Response](#incident-response)
8. [SIEM/SOAR Integration](#siemsoar-integration)

---

## Runtime Threat Landscape

### Container Runtime Threats

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Container Runtime Threat Types                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Attack Vectors                              │   │
│  │                                                                  │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │  │Vulnerability│ │  Miscon-  │  │ Malicious │  │  Supply   │   │   │
│  │  │  Exploit   │  │figuration │  │   Image   │  │  Chain    │   │   │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘   │   │
│  │        │              │              │              │          │   │
│  │        └──────────────┴──────────────┴──────────────┘          │   │
│  │                              │                                  │   │
│  │                              ▼                                  │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                    Runtime Threats                       │   │   │
│  │  │                                                          │   │   │
│  │  │  • Cryptocurrency Mining                                 │   │   │
│  │  │  • Reverse Shell                                         │   │   │
│  │  │  • Privilege Escalation                                  │   │   │
│  │  │  • Container Escape                                      │   │   │
│  │  │  • Data Exfiltration                                     │   │   │
│  │  │  • Lateral Movement                                      │   │   │
│  │  │  • Persistence                                           │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detection Technologies

| Technology | Description | Pros | Cons |
|------------|-------------|------|------|
| **Syscall Monitoring** | Kernel system call tracing | Detailed visibility | Overhead |
| **eBPF** | Kernel-level programming | High performance, safe | Complex implementation |
| **Audit Logs** | K8s API call recording | Compliance | Limited runtime visibility |
| **Network Monitoring** | Traffic pattern analysis | Lateral movement detection | Encrypted traffic |

---

## Falco

### Falco Overview

Falco is a cloud-native runtime security tool that analyzes system calls to detect anomalous behavior.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Falco Architecture                               │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Kubernetes Node                             │   │
│  │                                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Container A │  │ Container B │  │ Container C │             │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │   │
│  │         │                │                │                     │   │
│  │         └────────────────┼────────────────┘                     │   │
│  │                          │ System Calls                         │   │
│  │                          ▼                                      │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                    Linux Kernel                          │   │   │
│  │  │  ┌─────────────────────────────────────────────────┐    │   │   │
│  │  │  │         Falco eBPF/Kernel Module               │    │   │   │
│  │  │  │         (System Call Capture)                  │    │   │   │
│  │  │  └─────────────────────────────────────────────────┘    │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                          │                                      │   │
│  │                          ▼                                      │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                    Falco Engine                          │   │   │
│  │  │  ┌───────────┐  ┌───────────┐  ┌───────────────────┐   │   │   │
│  │  │  │   Rules   │  │ Filtering │  │  Output Channels  │   │   │   │
│  │  │  │  Engine   │──▶│  Engine   │──▶│ • stdout         │   │   │   │
│  │  │  │           │  │           │  │ • file            │   │   │   │
│  │  │  │           │  │           │  │ • Slack           │   │   │   │
│  │  │  │           │  │           │  │ • PagerDuty       │   │   │   │
│  │  │  └───────────┘  └───────────┘  └───────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Falco Installation (EKS)

```bash
# Install Falco using Helm
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

# Use eBPF driver (recommended)
helm install falco falcosecurity/falco \
    --namespace falco \
    --create-namespace \
    --set driver.kind=ebpf \
    --set falcosidekick.enabled=true \
    --set falcosidekick.webui.enabled=true
```

```yaml
# values.yaml (detailed configuration)
driver:
  kind: ebpf

falco:
  jsonOutput: true
  jsonIncludeOutputProperty: true
  httpOutput:
    enabled: true
    url: http://falcosidekick:2801

customRules:
  custom-rules.yaml: |-
    # Add custom rules here

falcosidekick:
  enabled: true
  config:
    slack:
      webhookurl: "https://hooks.slack.com/services/xxx"
      outputformat: "all"
      minimumpriority: "warning"
    pagerduty:
      apikey: "xxx"
      minimumpriority: "critical"

  webui:
    enabled: true
    service:
      type: ClusterIP
```

### Falco Rule Structure

```yaml
# Rule structure
- rule: <rule name>
  desc: <description>
  condition: <condition expression>
  output: <output message>
  priority: <severity: EMERGENCY|ALERT|CRITICAL|ERROR|WARNING|NOTICE|INFO|DEBUG>
  tags: [<tag list>]
  enabled: true|false
```

### Default Rule Examples

```yaml
# /etc/falco/falco_rules.yaml

# Detect shell execution in container
- rule: Terminal shell in container
  desc: A shell was spawned in a container
  condition: >
    spawned_process and
    container and
    shell_procs and
    proc.tty != 0
  output: >
    Shell spawned in a container
    (user=%user.name user_loginuid=%user.loginuid container=%container.name
    shell=%proc.name parent=%proc.pname cmdline=%proc.cmdline
    terminal=%proc.tty exe_flags=%evt.arg.flags)
  priority: WARNING
  tags: [shell, container, mitre_execution]

# Detect sensitive file reads
- rule: Read sensitive file untrusted
  desc: An untrusted program read a sensitive file
  condition: >
    sensitive_files and
    open_read and
    proc_name_exists and
    not user_trusted_containers
  output: >
    Sensitive file read by untrusted program
    (user=%user.name name=%proc.name command=%proc.cmdline
    file=%fd.name parent=%proc.pname gparent=%proc.aname[2]
    container=%container.name image=%container.image.repository)
  priority: WARNING
  tags: [filesystem, mitre_credential_access]

# Detect privilege escalation
- rule: Detect su or sudo
  desc: Detect su or sudo execution
  condition: >
    spawned_process and
    (proc.name in (su, sudo))
  output: >
    Privilege escalation via su/sudo
    (user=%user.name command=%proc.cmdline container=%container.name)
  priority: WARNING
  tags: [privilege_escalation]
```

### Writing Custom Rules

```yaml
# Cryptocurrency mining detection
- rule: Detect Cryptocurrency Mining
  desc: Detect cryptocurrency mining processes
  condition: >
    spawned_process and
    container and
    (
      proc.name in (xmrig, minerd, cgminer, cpuminer, bfgminer) or
      proc.cmdline contains "stratum+tcp://" or
      proc.cmdline contains "pool.minexmr.com" or
      proc.cmdline contains "cryptonight"
    )
  output: >
    Cryptocurrency mining detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository)
  priority: CRITICAL
  tags: [cryptomining, mitre_resource_hijacking]

# Reverse shell detection
- rule: Reverse Shell Detection
  desc: Detect reverse shell connections
  condition: >
    spawned_process and
    container and
    (
      (proc.name = bash and proc.cmdline contains "/dev/tcp/") or
      (proc.name = nc and proc.args contains "-e") or
      (proc.name = python and proc.cmdline contains "socket" and
       proc.cmdline contains "subprocess") or
      (proc.name = perl and proc.cmdline contains "socket") or
      (proc.name = ruby and proc.cmdline contains "TCPSocket")
    )
  output: >
    Reverse shell detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository connection=%fd.name)
  priority: CRITICAL
  tags: [reverse_shell, mitre_execution]

# Kubernetes Secret access detection
- rule: Unauthorized K8s Secret Access
  desc: Detect unauthorized access to mounted Kubernetes secrets
  condition: >
    open_read and
    container and
    fd.name startswith "/var/run/secrets/kubernetes.io" and
    not proc.name in (kubelet, kube-proxy)
  output: >
    Kubernetes secret accessed
    (user=%user.name command=%proc.cmdline file=%fd.name
    container=%container.name image=%container.image.repository)
  priority: WARNING
  tags: [k8s, secrets, mitre_credential_access]

# Container escape attempt detection
- rule: Container Escape Attempt
  desc: Detect potential container escape attempts
  condition: >
    spawned_process and
    container and
    (
      proc.cmdline contains "nsenter" or
      proc.cmdline contains "/proc/1/root" or
      proc.cmdline contains "/.dockerenv" or
      (proc.name = mount and proc.args contains "cgroup")
    )
  output: >
    Container escape attempt detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository)
  priority: CRITICAL
  tags: [container_escape, mitre_privilege_escalation]
```

### Falco Alert Configuration

```yaml
# Falcosidekick configuration for various alert channels
falcosidekick:
  config:
    # Slack
    slack:
      webhookurl: "https://hooks.slack.com/services/xxx/yyy/zzz"
      channel: "#security-alerts"
      username: "Falco"
      outputformat: "all"
      minimumpriority: "warning"

    # PagerDuty
    pagerduty:
      routingkey: "xxx"
      minimumpriority: "critical"

    # AWS CloudWatch
    cloudwatchlogs:
      region: "us-east-1"
      loggroup: "/falco/alerts"
      logstream: "eks-cluster"

    # AWS Security Hub
    securityhub:
      region: "us-east-1"
      minimumpriority: "high"

    # Prometheus
    prometheus:
      extralabels: "cluster:production"

    # Elasticsearch
    elasticsearch:
      hostport: "https://elasticsearch:9200"
      index: "falco"
      type: "_doc"
```

---

## Tetragon

### Tetragon Overview

Tetragon is an eBPF-based security observability and runtime enforcement tool from the Cilium project.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Tetragon Architecture                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Kubernetes Cluster                            │   │
│  │                                                                  │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │                    Tetragon DaemonSet                      │  │   │
│  │  │                                                            │  │   │
│  │  │  ┌─────────────────────────────────────────────────────┐  │  │   │
│  │  │  │                   eBPF Programs                      │  │  │   │
│  │  │  │                                                      │  │  │   │
│  │  │  │  • Process Execution   • File Access                │  │  │   │
│  │  │  │  • Network Activity    • Capability Usage           │  │  │   │
│  │  │  │  • Namespace Changes   • Syscall Tracing            │  │  │   │
│  │  │  └─────────────────────────────────────────────────────┘  │  │   │
│  │  │                           │                                │  │   │
│  │  │                           ▼                                │  │   │
│  │  │  ┌─────────────────────────────────────────────────────┐  │  │   │
│  │  │  │               TracingPolicy CRD                      │  │  │   │
│  │  │  │                                                      │  │  │   │
│  │  │  │  • kprobes    • tracepoints    • uprobes            │  │  │   │
│  │  │  │  • Selectors  • Actions        • Filters            │  │  │   │
│  │  │  └─────────────────────────────────────────────────────┘  │  │   │
│  │  │                           │                                │  │   │
│  │  │                           ▼                                │  │   │
│  │  │  ┌─────────────────────────────────────────────────────┐  │  │   │
│  │  │  │                    Outputs                           │  │  │   │
│  │  │  │                                                      │  │  │   │
│  │  │  │  • JSON Events  • gRPC API  • Prometheus Metrics    │  │  │   │
│  │  │  └─────────────────────────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tetragon Installation

```bash
# Install Tetragon using Helm
helm repo add cilium https://helm.cilium.io
helm repo update

helm install tetragon cilium/tetragon \
    -n kube-system \
    --set tetragon.enableProcessCred=true \
    --set tetragon.enableProcessNs=true
```

### TracingPolicy Basic Structure

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: example-policy
spec:
  # kprobes: kernel function tracing
  kprobes:
    - call: "security_file_open"
      syscall: false
      args:
        - index: 0
          type: "file"
      selectors:
        - matchArgs:
            - index: 0
              operator: "Prefix"
              values:
                - "/etc/shadow"
          matchActions:
            - action: Sigkill  # Kill process
```

### Process Monitoring

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: process-monitoring
spec:
  kprobes:
    # Monitor execve system call
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"  # Executable path
      selectors:
        - matchBinaries:
            - operator: "In"
              values:
                - "/bin/bash"
                - "/bin/sh"
                - "/usr/bin/python"
          matchNamespaces:
            - namespace: Pid
              operator: NotIn
              values:
                - "host_ns"  # Exclude host namespace
```

### File Access Monitoring

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: sensitive-file-access
spec:
  kprobes:
    - call: "security_file_open"
      syscall: false
      args:
        - index: 0
          type: "file"
      selectors:
        # Monitor sensitive file access
        - matchArgs:
            - index: 0
              operator: "Prefix"
              values:
                - "/etc/shadow"
                - "/etc/passwd"
                - "/etc/sudoers"
                - "/root/.ssh"
                - "/var/run/secrets/kubernetes.io"
          matchActions:
            - action: Post  # Log event
---
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-sensitive-file-write
spec:
  kprobes:
    - call: "security_file_open"
      syscall: false
      args:
        - index: 0
          type: "file"
        - index: 1
          type: "int"  # flags
      selectors:
        # Block write access to sensitive files
        - matchArgs:
            - index: 0
              operator: "Prefix"
              values:
                - "/etc/passwd"
                - "/etc/shadow"
            - index: 1
              operator: "Mask"
              values:
                - "2"  # O_WRONLY or O_RDWR
          matchActions:
            - action: Sigkill  # Kill process
```

### Network Monitoring

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: network-monitoring
spec:
  kprobes:
    # Monitor outbound connections
    - call: "tcp_connect"
      syscall: false
      args:
        - index: 0
          type: "sock"
      selectors:
        - matchArgs:
            - index: 0
              operator: "DPort"
              values:
                - "22"    # SSH
                - "4444"  # Common reverse shell port
                - "5555"  # Common reverse shell port
          matchActions:
            - action: Post

    # Monitor DNS queries
    - call: "udp_sendmsg"
      syscall: false
      args:
        - index: 0
          type: "sock"
      selectors:
        - matchArgs:
            - index: 0
              operator: "DPort"
              values:
                - "53"
          matchActions:
            - action: Post
```

### Runtime Enforcement

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-crypto-miners
spec:
  kprobes:
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"
      selectors:
        # Block cryptocurrency mining processes
        - matchArgs:
            - index: 0
              operator: "Postfix"
              values:
                - "xmrig"
                - "minerd"
                - "cgminer"
          matchActions:
            - action: Sigkill
---
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-reverse-shells
spec:
  kprobes:
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"
        - index: 1
          type: "string"  # argv
      selectors:
        # Block reverse shell patterns
        - matchArgs:
            - index: 1
              operator: "Contains"
              values:
                - "/dev/tcp/"
                - "bash -i"
                - "nc -e"
          matchActions:
            - action: Sigkill
```

### Tetragon CLI Usage

```bash
# View event stream
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents

# Filter process events
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
    tetra getevents -o compact --process curl

# JSON format output
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
    tetra getevents -o json

# Filter by namespace
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
    tetra getevents --namespace production
```

---

## Falco vs Tetragon Comparison

### Feature Comparison Table

| Feature | Falco | Tetragon |
|---------|-------|----------|
| **Technology Base** | Kernel module/eBPF | eBPF only |
| **Performance** | Good | Excellent |
| **Rule Language** | YAML + conditions | CRD (TracingPolicy) |
| **Runtime Enforcement** | Limited | Native support |
| **Kubernetes Integration** | Good | Excellent (Cilium) |
| **Process Tracing** | ✓ | ✓ |
| **File Monitoring** | ✓ | ✓ |
| **Network Monitoring** | Limited | ✓ (Cilium integration) |
| **Community** | Large and mature | Growing |
| **Learning Curve** | Medium | High |
| **Alert Integration** | Falcosidekick | Prometheus, gRPC |

### Use Case Recommendations

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Recommended Tools by Use Case                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Detection-focused Monitoring                                           │
│  └─▶ Falco (mature ruleset, diverse alert integration)                 │
│                                                                         │
│  Runtime Enforcement Needed                                             │
│  └─▶ Tetragon (process termination, network blocking)                  │
│                                                                         │
│  Cilium CNI Environment                                                 │
│  └─▶ Tetragon (native integration)                                     │
│                                                                         │
│  Compliance/Auditing                                                    │
│  └─▶ Falco + Tetragon (complementary)                                  │
│                                                                         │
│  Minimal Overhead Required                                              │
│  └─▶ Tetragon (pure eBPF)                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Kubernetes Audit Logging

### Audit Policy Configuration

```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # Log authentication failures
  - level: Metadata
    users: ["system:anonymous"]
    verbs: ["*"]

  # Detailed Secret access logging
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["secrets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

  # Pod exec/attach logging
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["pods/exec", "pods/attach", "pods/portforward"]
    verbs: ["create"]

  # RBAC change logging
  - level: RequestResponse
    resources:
      - group: "rbac.authorization.k8s.io"
        resources: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
    verbs: ["create", "update", "patch", "delete"]

  # Minimal logging for read operations
  - level: Metadata
    verbs: ["get", "list", "watch"]

  # All other requests
  - level: Request
    verbs: ["*"]
```

### EKS Audit Log Analysis

```bash
# CloudWatch Logs Insights queries

# Secret access events
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100

# Permission denied events
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter responseStatus.code = 403
| sort @timestamp desc

# exec/attach events
fields @timestamp, user.username, objectRef.name, requestURI
| filter objectRef.subresource in ["exec", "attach"]
| sort @timestamp desc
```

---

## Runtime Threat Detection Patterns

### Cryptocurrency Mining Detection

```yaml
# Falco rule
- rule: Cryptocurrency Mining Activity
  desc: Detect processes commonly used for cryptocurrency mining
  condition: >
    spawned_process and container and
    (
      proc.name in (xmrig, minerd, cpuminer, cgminer) or
      proc.cmdline contains "stratum+tcp" or
      proc.cmdline contains "pool." and proc.cmdline contains ":" or
      proc.cmdline contains "--algo=cryptonight"
    )
  output: >
    Cryptocurrency mining activity detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository pod=%k8s.pod.name)
  priority: CRITICAL
  tags: [cryptomining, mitre_resource_hijacking]
```

### Reverse Shell Detection

```yaml
- rule: Reverse Shell Activity
  desc: Detect outbound network connections that may be reverse shells
  condition: >
    spawned_process and container and
    (
      (proc.name = bash and proc.cmdline contains "/dev/tcp/") or
      (proc.name = nc and (proc.args contains "-e" or proc.args contains "-c")) or
      (proc.name = ncat and proc.args contains "--sh-exec") or
      (proc.name = python and proc.cmdline contains "socket" and
       proc.cmdline contains "subprocess") or
      (proc.name = perl and proc.cmdline contains "socket" and
       proc.cmdline contains "exec") or
      (proc.name = php and proc.cmdline contains "fsockopen")
    )
  output: >
    Reverse shell detected
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository pod=%k8s.pod.name)
  priority: CRITICAL
  tags: [reverse_shell, mitre_command_and_control]
```

### Privilege Escalation Detection

```yaml
- rule: Privilege Escalation via SUID
  desc: Detect execution of SUID binaries
  condition: >
    spawned_process and container and
    proc.is_exe_upper_layer=false and
    user.uid != 0 and
    proc.suid != 0 and
    proc.suid != proc.uid
  output: >
    SUID binary executed
    (user=%user.name uid=%user.uid suid=%proc.suid command=%proc.cmdline
    container=%container.name)
  priority: WARNING
  tags: [privilege_escalation, mitre_privilege_escalation]

- rule: Setuid/Setgid Binary Created
  desc: Detect creation of setuid/setgid binaries
  condition: >
    evt.type = chmod and container and
    (evt.arg.mode contains "S_ISUID" or evt.arg.mode contains "S_ISGID")
  output: >
    Setuid/setgid binary created
    (user=%user.name file=%fd.name mode=%evt.arg.mode container=%container.name)
  priority: CRITICAL
  tags: [privilege_escalation, persistence]
```

---

## Incident Response

### Pod Isolation Procedure

```bash
#!/bin/bash
# incident-response.sh

POD_NAME=$1
NAMESPACE=$2

# 1. Apply isolation network policy
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-${POD_NAME}
  namespace: ${NAMESPACE}
spec:
  podSelector:
    matchLabels:
      app: $(kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o jsonpath='{.metadata.labels.app}')
  policyTypes:
    - Ingress
    - Egress
  # Block all traffic
EOF

# 2. Collect pod information
echo "=== Collecting Pod Information ==="
kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o yaml > pod-${POD_NAME}-spec.yaml
kubectl describe pod ${POD_NAME} -n ${NAMESPACE} > pod-${POD_NAME}-describe.txt
kubectl logs ${POD_NAME} -n ${NAMESPACE} --all-containers > pod-${POD_NAME}-logs.txt

# 3. Collect process list (if possible)
kubectl exec ${POD_NAME} -n ${NAMESPACE} -- ps aux > pod-${POD_NAME}-processes.txt 2>/dev/null

# 4. Collect network connections
kubectl exec ${POD_NAME} -n ${NAMESPACE} -- netstat -an > pod-${POD_NAME}-network.txt 2>/dev/null

# 5. Filesystem snapshot (if needed)
# kubectl debug ${POD_NAME} -n ${NAMESPACE} --image=busybox -- tar -cvf /tmp/fs.tar /

echo "=== Evidence Collection Complete ==="
echo "Collected files: pod-${POD_NAME}-*.txt"
```

### Forensics Container

```yaml
# Debug container for forensics
apiVersion: v1
kind: Pod
metadata:
  name: forensics-pod
  namespace: security
spec:
  containers:
  - name: forensics
    image: nicolaka/netshoot:latest
    command: ["sleep", "3600"]
    securityContext:
      capabilities:
        add:
          - SYS_PTRACE
          - NET_ADMIN
    volumeMounts:
      - name: host-proc
        mountPath: /host/proc
        readOnly: true
      - name: evidence
        mountPath: /evidence
  volumes:
    - name: host-proc
      hostPath:
        path: /proc
    - name: evidence
      emptyDir: {}
```

---

## SIEM/SOAR Integration

### Falco to Elasticsearch

```yaml
# Falcosidekick Elasticsearch configuration
falcosidekick:
  config:
    elasticsearch:
      hostport: "https://elasticsearch.logging:9200"
      index: "falco"
      type: "_doc"
      minimumpriority: "warning"
      mutualtls: false
      checkcert: true
      username: "elastic"
      password: "${ELASTIC_PASSWORD}"
```

### Prometheus + Grafana Dashboard

```yaml
# ServiceMonitor for Falco metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: falco
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: falco
  endpoints:
    - port: metrics
      interval: 30s
```

```yaml
# Grafana dashboard ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: falco-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  falco-dashboard.json: |
    {
      "title": "Falco Security Alerts",
      "panels": [
        {
          "title": "Alerts by Priority",
          "type": "piechart",
          "targets": [
            {
              "expr": "sum by (priority) (falco_events_total)"
            }
          ]
        },
        {
          "title": "Alerts Over Time",
          "type": "timeseries",
          "targets": [
            {
              "expr": "rate(falco_events_total[5m])"
            }
          ]
        }
      ]
    }
```

---

## Summary

Key aspects of runtime security:

1. **Falco**: Mature ruleset, diverse alert integration, detection-focused
2. **Tetragon**: eBPF-based high performance, runtime enforcement support
3. **Audit Logging**: Kubernetes API activity tracking, compliance
4. **Threat Detection**: Cryptocurrency mining, reverse shells, privilege escalation
5. **Incident Response**: Isolation, evidence collection, forensics

### Recommendations

- Use Falco + Tetragon combination for detection and enforcement
- Write custom rules for critical systems
- Integrate with SIEM for centralized monitoring
- Prepare incident response playbooks

---

## References

- [Falco Official Documentation](https://falco.org/docs/)
- [Tetragon Documentation](https://tetragon.io/docs/)
- [MITRE ATT&CK for Containers](https://attack.mitre.org/matrices/enterprise/containers/)
- [Kubernetes Audit Logging](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
