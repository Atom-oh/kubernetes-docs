# 运行时安全

> **最后更新**: September 13, 2026
> **验证基线**: Falco 0.44.1 / chart 9.1.0, Falcosidekick 2.35.0 / chart 0.14.0, Tetragon 1.7.1。请验证实际 kernel、OS 和节点类型是否受支持。

运行时安全会观察进程、文件和网络活动，并通过经过测试的策略限制选定操作。**告警并非遭入侵的证据；检测和防护需要分别测试。** 本指南已使用本地 CLI、schema、Helm 和合成事件进行检查。未使用真实集群、kernel BPF 程序或通知渠道。

<span id="container-runtime-threats"></span>
<span id="detection-technologies"></span>

## 运行时威胁态势

| 观测点 | 可展示的内容 | 局限性 |
|---|---|---|
| Syscall/kernel hook | 进程执行、文件访问、连接尝试 | 检查丢弃的事件、权限、kernel 支持和过滤器 |
| Kubernetes audit | API 请求者、动词、对象、响应状态 | 不显示 Pod 内的每项进程/文件操作 |
| 网络流 | 连接、丢弃、策略判定 | 仅凭端口或加密连接无法证明具有恶意意图 |
| 镜像/admission policy | 漏洞、签名、Pod 设置 | 无法检测每一种部署后的行为 |

eBPF 本身不能保证低开销或安全性。应在实际节点上测量 hooks、事件量、过滤、输出开销、CPU 和内存。不要仅因生产进程的命令名与某个指标匹配就自动终止它。

<span id="default-rule-examples"></span>

## Falco

### Falco 概述

Falco 根据规则评估事件。典型的 syscall 路径为 `Linux event → modern eBPF/kmod capture → Falco filter/rule → JSON output → Falcosidekick → notification/storage`。Slack 和 PagerDuty 是下游集成，而非 Falco rule engine 内置的 Slack 客户端。

0.44.1 发行版捆绑 container plugin 0.7.1。它提供 container.id 等字段，因此禁用所有 plugin 会使使用这些字段的规则无法编译/运行。请验证 runtime socket、Kubernetes metadata 收集和访问权限。

### Falco 安装（EKS）

本示例面向由你管理主机访问权限的 Linux EC2 节点。不要假设 DaemonSet 可以在 Fargate 或其他受限主机上运行。请验证 modern eBPF 的 kernel/BTF/capability 要求。Chart 9.1.0 支持显式 driver kind `modern_ebpf` 和 `kmod`；请勿保留旧的 `ebpf` 设置。

下载[示例目录](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/runtime-security)，并在 `examples/security/runtime-security` 中运行以下命令。[示例 README](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/runtime-security/README.md) 说明了三个 values 文件和规则。

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

Sidekick chart 的 appVersion 与其默认 image tag 不同，因此示例将 image.tag 显式固定为 2.35.0。请先准备其输出凭证 Secret 和 Prometheus Operator CRD。缺少 Secret 可能会阻止 Pod 启动。在最小实验环境中禁用未使用的 notification/metrics 选项。

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
  documentation-rules.yaml: |-
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


该配置将 HTTP 发送至单独安装的 falcosidekick ClusterIP Service。共享 namespace 不会对流量进行认证或加密。请根据实际信任边界配置 access policy 和 TLS/mTLS，并验证节点/Falco 连通性。Falco 使用 json_output 和 http_output 等 snake_case 字段。旧的 jsonOutput/httpOutput 以及已移除的 grpc 设置无法通过 0.44.1 schema。

### Falco 规则结构

这些规则定义了自身所需的 macros，且避免替换默认规则名。有意更改现有规则时，请使用固定 ruleset 的 override 语法。

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


在移除 enter events 后，Falco 0.44.1 会警告 evt.dir 已弃用。这些示例直接选择成功的 exec 和 read events。合法的 Kubernetes 客户端会读取 service account token，因此仅凭读取信号并非“未授权访问”。请将其与 workload baseline、获准 binary 和 Pod identity 结合使用。

### 编写自定义规则

| 模式 | 可能的信号 | 所需限定 |
|---|---|---|
| 疑似挖矿 | 进程名、pool/stratum 字符串、异常资源使用 | 重命名和合法计算可能规避或触发 heuristic |
| 疑似反向 shell | shell argv 中的连接字符串以及异常出站流 | exec event 的 fd.name 并非网络连接的证据 |
| 权限提升 | 凭证变更、SUID 设置、capabilities | 检查 user.uid/proc.uid/proc.suid 的含义以及操作是否成功 |
| 疑似逃逸 | Namespace/host-path 访问和异常挂载 | nsenter 或 /.dockerenv 字符串不能证明逃逸成功 |

规则编译不会衡量检测有效性。在分阶段发布之前，测试合成/已授权的实验事件、正常 workload、缺失的 metadata 和丢弃计数器。参数、路径和日志可能包含 secret；请限制事件字段、保留期限和访问权限。

### Falco 告警配置

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


falcosidekick-output-credentials 是一个通过 envFrom 读取的同 namespace 现有 Secret。请仅通过你的 secret-management 流程提供经批准输出所需的变量，例如 SLACK_WEBHOOKURL、PAGERDUTY_ROUTINGKEY 和 ELASTICSEARCH_HOSTPORT/USERNAME/PASSWORD。在 Helm values 内写入 `${ELASTIC_PASSWORD}` 不会执行 shell substitution。不要在 Git、命令行或审查日志中暴露凭证。

AWS 设置属于 config.aws。请验证 workload identity，并将 IAM actions/resources 限定在预期 log groups/streams 内。minimumpriority 使用 emergency/alert/critical/error/warning/notice/informational/debug，而非 `high`。检查每个输出的激活条件、重试和失败 metrics。该示例禁用了 Web UI。

<span id="tetragon-installation"></span>
<span id="tracingpolicy-basic-structure"></span>
<span id="process-monitoring"></span>

## Tetragon

### Tetragon 概述

Tetragon 可以独立于 Cilium CNI 运行。请区分内置的 process_exec/exit events 与附加的 TracingPolicy hooks。流程为 `kernel hook → selector → Post/supported action → JSON/gRPC/metrics`；Kubernetes CRD 本身并不在 kernel 内执行。

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


检查 operator/CRD 就绪状态以及每个节点的 kernel、BTF 和 capabilities。Helm rendering 不代表 hook 已附加。带 namespace 的示例面向 demo-app workload；请确认所选策略类型和 hook 的有效作用域。

### 文件访问监控

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


`security_file_permission(struct file *, int mask)` 的第二个参数是 permission mask：MAY_READ=4，MAY_WRITE=2。将“index 1 = open flags”赋给单参数的 security_file_open 函数是错误的。Open flags O_WRONLY=1/O_RDWR=2 也不同于该 permission mask。仅凭此 hook 无法覆盖每一次 mmap/truncate/file mutation。

### 网络监控

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


tcp_connect 观察 TCP 连接尝试。仅凭目标端口并不意味着流量恶意或策略拒绝。UDP 端口 53 活动无法提供完整的 DNS 问题/答案分析；请使用适当的 DNS telemetry 路径。

### 运行时强制执行

从 Post/monitor 行为开始，并检查正常操作和 false positive。Sigkill 会发送信号；取决于 hook 和 kernel 行为，它无法撤销已经发生的影响。返回值 override 需要受支持的 syscall/security function、kernel 设置和适当的错误结果。并非所有任意 kprobes 都支持它。

不要根据文件名或 argv strings 声称可通用防范挖矿/反向 shell。execve argv 是指针数组，而不是单个 string 参数。将其作为单个 string 读取，无法按预期检查完整 command line。请区分 process-event 参数过滤和 kernel actions，并在获批准、范围严格限定的实验环境中验证强制执行。

### Tetragon CLI 用法

```bash
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents -o json
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact --namespace production --process curl
# Filter stored synthetic events locally:
tetra getevents -o json --namespace demo-app < events.jsonl
```

针对 DaemonSet 执行会选择一个 Pod/node 的 agent；这不是 cluster-wide aggregation。此处仅测试了 stdin filtering path。tetra tracingpolicy modify 的 1.7.1 实现也会创建 gRPC client，因此未将其用作 offline validator。

<span id="feature-comparison-table"></span>
<span id="use-case-recommendations"></span>

## Falco 与 Tetragon 对比

| 标准 | Falco | Tetragon |
|---|---|---|
| 策略 | Event conditions 和 rulesets | Kernel hooks、selectors、actions |
| 常见用途 | 具有 notification/storage 集成的检测 | 进程可见性和显式 hook enforcement |
| 运行检查 | Driver/plugin/runtime metadata 和丢弃事件 | BTF/hook 支持、策略作用域、side effects |
| 性能 | 在实际负载下测量 CPU/memory/event loss | 使用相同 workload；eBPF 本身不能证明其更优 |

部署两者并不一定是最佳选择。请考虑重复采集、节点权限、成本、运维复杂度和所需的 enforcement。

## Kubernetes 审计日志

### 审计策略配置

此策略适用于**自主管理的 Kubernetes API server**。应用此 YAML 不会替换 EKS 的托管审计策略。请启用 EKS control-plane audit logs，并配置 CloudWatch 访问、保留和加密。

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


Secrets 和 serviceaccounts/token 的 Request/RequestResponse logging 可能持久化凭证正文，因此请使用 Metadata。Audit rules 按首次匹配处理；请将敏感资源规则放在前面。仅 system:anonymous 并不能捕获每次 authentication failure。请检查 audit stages、responseStatus 和 authentication logs。一条 exec audit record 并非 terminal session 内每条命令的记录。

### EKS 审计日志分析

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name, responseStatus.code
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

这是 CloudWatch Logs Insights query，不是 Bash。403 表示被拒绝的响应；请单独分类成功读取。启用 logging 后请验证 collection，并配置 retention。

<span id="cryptocurrency-mining-detection"></span>
<span id="reverse-shell-detection"></span>
<span id="privilege-escalation-detection"></span>

## 运行时威胁检测模式

Seccomp 限制 syscalls，但拒绝并不总会终止进程。Actions 可以返回 ERRNO、kill 或 notify。RuntimeDefault 表示 runtime 的 profile；请显式设置它或验证 kubelet seccompDefault。仅 Kubernetes 1.27+ 并不会自动将其应用到每个 Pod。

AppArmor 需要节点支持和已加载的 profiles。Complain mode 会记录普通违规，而显式 deny rules 仍可阻止操作。readOnlyRootFilesystem 是 container securityContext 字段；它不能阻止对可写 volumes 的恶意使用、网络访问或内存访问。

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


当前 GuardDuty Runtime Monitoring 支持 EKS EC2 nodes 和 EKS Auto Mode，但不支持 EKS Hybrid Nodes 或 EKS Fargate。请检查官方 OS/kernel/architecture/agent-version matrix 和 coverage health。启用此功能不代表每个节点都具有健康覆盖。

Hubble `--verdict DROPPED` 显示丢弃；并非每次丢弃都是 NetworkPolicy denial。请同时检查 drop reason 和 policy verdict。

<span id="forensics-container"></span>

## 事件响应

### Pod 隔离流程

标准 NetworkPolicy 允许规则以并集方式组合。添加 ingress/egress lists 为空的策略不会覆盖另一策略允许的连接。一个 app label 可以选择属于该应用的多个 Pods。

1. 确认 namespace、Pod UID、node、owner 和现有 network policies。
2. 选择获批准的 isolation mechanism。对于 CNI-specific explicit deny 或对现有允许规则的更改，请审查确切 targets、影响和恢复方式。
3. 测试已建立和新建的连接；考虑 hostNetwork、node traffic 和 CNI limitations。
4. 保护证据，并记录 isolation、中断和恢复决策。

### 证据收集与取证

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


此脚本通过 API 收集 Pod metadata/logs 并记录 checksums。它已使用 subprocess double 进行测试，包括失败情形和私有 0700 output directories，但未针对真实集群测试。Pod specs 和 logs 可能包含 secrets/personal information；请使用获批准的 storage 和 access controls。

新的 forensic Pod 不会自动运行在目标 node 上，也不会共享目标 process namespace。hostPath /proc、SYS_PTRACE 和 NET_ADMIN 会授予大量访问权限；需要时请使用获批准的流程。emptyDir 不是持久性 evidence storage。归档 ephemeral container 的 `/` 并不自动成为目标 container filesystem 的快照。

<span id="falco-to-elasticsearch"></span>
<span id="prometheus-grafana-dashboard"></span>

<span id="siemsoar-integration"></span>

## SIEM/SOAR 集成

请将 ServiceMonitor namespaces、selectors 和 ports 与实际 Services 对比。Falco chart 有一个 metrics Service；Falcosidekick 在其 HTTP port 上公开 metrics。仅当 monitoring.coreos.com/v1 可用时，Sidekick chart 才会渲染 ServiceMonitor。

```promql
sum by (priority) (rate(falcosecurity_falcosidekick_falco_events_total[5m]))
```

这是 Falcosidekick 2.35.0 的 received-event counter。不要将原始 falco_events_total 视为通用 metric name。请区分 cumulative counts 与 interval rates；检查实际 labels、resets、output failures 和 missing scrapes。即使是合成 Slack/PagerDuty/SIEM notification tests，也应与收件人和运维流程协调。

<span id="table-of-contents"></span>
<span id="recommendations"></span>

## 摘要

本地检查涵盖两条 Falco 规则、四个 configuration-schema 情形、三个 Tetragon JSON filters 和两个 CRDs、三个 Helm charts，以及四个 evidence-script 成功/失败情形。未执行 kernel attachment、detection efficacy、实际 enforcement、GuardDuty coverage、audit/CloudWatch collection 和外部通知。

## 参考资料

- [Falco Kubernetes 安装](https://falco.org/docs/setup/kubernetes/)
- [Falco 0.44.1 配置](https://github.com/falcosecurity/falco/blob/0.44.1/falco.yaml)
- [Falcosidekick 2.35.0 配置](https://github.com/falcosecurity/falcosidekick/blob/2.35.0/config_example.yaml)
- [Tetragon tracing policies](https://tetragon.io/docs/concepts/tracing-policy/)
- [Tetragon enforcement](https://tetragon.io/docs/concepts/enforcement/)
- [Tetragon 1.7.1 文件监控](https://github.com/cilium/tetragon/blob/v1.7.1/examples/quickstart/file_monitoring.yaml)
- [Kubernetes 审计](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [NetworkPolicy 语义](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [AppArmor](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [EKS control-plane logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [GuardDuty EKS runtime requirements](https://docs.aws.amazon.com/guardduty/latest/ug/prereq-runtime-monitoring-eks-support.html)
- [MITRE ATT&CK Containers](https://attack.mitre.org/matrices/enterprise/containers/)
