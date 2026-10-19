# 运行时安全

> **最后更新**：2026 年 10 月 16 日
> **验证基线**：Falco 0.45.0 / chart 9.2.0、Falcosidekick 2.35.0 / chart 0.14.0、Tetragon 1.7.1。请验证对实际内核、操作系统和节点类型的支持情况。

运行时安全会观察进程、文件和网络活动，并通过经过测试的策略限制特定操作。**告警不等于已遭入侵的证明；检测和预防需要分别测试**。本指南使用本地 CLI、schema、Helm 和合成事件进行了检查。未使用真实集群、内核 BPF 程序或通知渠道。

<span id="container-runtime-threats"></span>
<span id="detection-technologies"></span>

## 运行时威胁态势

| 观察点 | 可以显示的内容 | 局限性 |
|---|---|---|
| 系统调用/内核 hook | 进程执行、文件访问、连接尝试 | 检查事件丢失、权限、内核支持和过滤器 |
| Kubernetes 审计 | API 请求者、动词、对象、响应状态 | 不会显示 Pod 内的每项进程/文件操作 |
| 网络流 | 连接、丢弃、策略判定 | 仅凭端口或加密连接无法确定恶意意图 |
| 镜像/准入策略 | 漏洞、签名、Pod 设置 | 无法检测所有部署后的行为 |

仅使用 eBPF 并不能保证开销低或安全。请在实际节点上测量 hook、事件量、过滤、输出开销、CPU 和内存。不要仅仅因为生产进程的命令名称与某个指标匹配，就自动将其终止。

<span id="default-rule-examples"></span>

## Falco

### Falco 概述

Falco 会根据规则评估事件。典型的系统调用路径是 `Linux event → modern eBPF/kmod capture → Falco filter/rule → JSON output → Falcosidekick → notification/storage`。Slack 和 PagerDuty 是下游集成，并非 Falco 规则引擎内置的 Slack 客户端。

0.45.0 发行版捆绑了 container plugin 0.7.4。该插件提供 container.id 等字段，因此停用所有插件会导致使用这些字段的规则无法编译/运行。请验证运行时 socket、Kubernetes 元数据收集和访问权限。

### Falco 安装（EKS）

此示例面向由你管理主机访问权限的 Linux EC2 节点。不要假设 DaemonSet 可以在 Fargate 或其他受限主机上运行。请验证 modern eBPF 内核/BTF/能力要求。Chart 9.2.0 支持显式的驱动类型 `modern_ebpf` 和 `kmod`；不要保留旧的 `ebpf` 设置。

下载[示例目录](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/runtime-security)，并在 `examples/security/runtime-security` 目录下运行以下命令。[示例 README](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/runtime-security/README.md)介绍了三个 values 文件和规则。

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update falcosecurity
helm upgrade --install falcosidekick falcosecurity/falcosidekick \
  --version 0.14.0 --namespace falco --create-namespace \
  --values falcosidekick-values.yaml
helm upgrade --install falco falcosecurity/falco \
  --version 9.2.0 --namespace falco \
  --values falco-values.yaml
```

Sidekick chart 的 appVersion 与其默认镜像标签不同，因此示例会显式固定 image.tag 为 2.35.0。请预先准备其输出凭据 Secret 和 Prometheus Operator CRD。缺少 Secret 可能导致 Pod 无法启动。在最小化实验环境中停用未使用的通知/指标选项。

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


此配置会向单独安装的 falcosidekick ClusterIP Service 发送 HTTP 请求。处于同一命名空间并不能实现身份验证或流量加密。请根据实际信任边界配置访问策略和 TLS/mTLS，并验证节点与 Falco 之间的连通性。Falco 使用 snake_case 字段，例如 json_output 和 http_output。旧版 jsonOutput/httpOutput 以及已移除的 grpc 设置无法通过 0.45.0 schema 验证。

### Falco 规则结构

这些规则定义了自身所需的宏，并避免替换默认规则名称。若要有意更改现有规则，请使用固定版本规则集的 override 语法。

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


移除 enter 事件后，Falco 0.45.0 会警告 evt.dir 已弃用。这些示例会直接选择成功的 exec 和读取事件。合法的 Kubernetes 客户端也会读取 Service Account token，因此仅凭读取信号并不代表“未经授权的访问”。应结合工作负载基线、批准使用的二进制文件和 Pod 身份进行判断。

### 编写自定义规则

| 模式 | 可能的信号 | 必要的限定条件 |
|---|---|---|
| 疑似挖矿 | 进程名称、矿池/stratum 字符串、异常资源使用 | 改名和合法计算活动都可能导致启发式检测失效或误报 |
| 疑似反向 shell | shell argv 中的连接字符串和异常出站流量 | exec 事件的 fd.name 不能证明存在网络连接 |
| 权限提升 | 凭据更改、SUID 设置、能力 | 检查 user.uid/proc.uid/proc.suid 的含义及操作是否成功 |
| 疑似逃逸 | 命名空间/主机路径访问和异常挂载 | nsenter 或 /.dockerenv 字符串不能证明逃逸成功 |

规则编译并不能衡量检测效果。在分阶段推出之前，请测试合成/授权的实验室事件、正常工作负载、缺失的元数据和丢弃计数器。参数、路径和日志可能包含机密信息；请限制事件字段、保留期限和访问权限。

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


falcosidekick-output-credentials 是通过 envFrom 读取的同命名空间现有 Secret。请通过你的密钥管理流程，仅提供已批准输出所需的变量，例如 SLACK_WEBHOOKURL、PAGERDUTY_ROUTINGKEY 和 ELASTICSEARCH_HOSTPORT/USERNAME/PASSWORD。在 Helm values 中写入 `${ELASTIC_PASSWORD}` 并不会执行 shell 替换。不要在 Git、命令行或审查日志中暴露凭据。

AWS 设置应放在 config.aws 下。请验证工作负载身份，并将 IAM 操作/资源的范围限制在预期的日志组/流。minimumpriority 接受 emergency/alert/critical/error/warning/notice/informational/debug，不接受 `high`。请检查每个输出的启用条件、重试和故障指标。此示例停用了 Web UI。

<span id="tetragon-installation"></span>
<span id="tracingpolicy-basic-structure"></span>
<span id="process-monitoring"></span>

## Tetragon

### Tetragon 概述

Tetragon 可以独立于 Cilium CNI 运行。请区分内置的 process_exec/exit 事件与额外的 TracingPolicy hook。其流程是 `kernel hook → selector → Post/supported action → JSON/gRPC/metrics`；Kubernetes CRD 本身不会在内核中执行。

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


请检查 operator/CRD 是否就绪，以及每个节点的内核、BTF 和能力。Helm 渲染无法证明 hook 已附加。命名空间级示例面向 demo-app 工作负载；请确认所选策略类型和 hook 的实际作用范围。

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


`security_file_permission(struct file *, int mask)` 的第二个参数是权限掩码：MAY_READ=4、MAY_WRITE=2。将“index 1 = open flags”分配给只有一个参数的 security_file_open 函数是不正确的。打开标志 O_WRONLY=1/O_RDWR=2 也不同于此权限掩码。仅靠此 hook 无法覆盖所有 mmap/truncate/文件修改操作。

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


tcp_connect 会观察 TCP 连接尝试。仅凭目标端口不能说明流量是恶意的，也不能说明策略已拒绝该流量。UDP 53 端口活动无法提供完整的 DNS 问题/答案分析；请使用适当的 DNS 遥测路径。

### 运行时强制执行

先使用 Post/监控行为，并检查正常操作和误报。Sigkill 会发送信号；根据 hook 和内核行为，它无法撤销已经发生的影响。返回值覆盖需要使用受支持的系统调用/安全函数、内核设置和适当的错误结果。并非所有 kprobe 都支持此功能。

不要声称可以根据文件名或 argv 字符串普遍防止挖矿/反向 shell。execve argv 是一个指针数组，而不是一个字符串参数。将其作为单个字符串读取，无法按预期检查完整命令行。请区分进程事件参数过滤与内核操作，并在经过批准且范围严格限定的实验室中验证强制执行效果。

### Tetragon CLI 用法

```bash
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents -o json
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact --namespace production --process curl
# Filter stored synthetic events locally:
tetra getevents -o json --namespace demo-app < events.jsonl
```

对 DaemonSet 执行操作会选择某个 Pod/节点上的 agent；这并不代表进行了集群范围的聚合。此处仅测试了 stdin 过滤路径。1.7.1 版本的 tetra tracingpolicy modify 实现也会创建 gRPC 客户端，因此未将其用作离线验证器。

<span id="feature-comparison-table"></span>
<span id="use-case-recommendations"></span>

## Falco 与 Tetragon 对比

| 标准 | Falco | Tetragon |
|---|---|---|
| 策略 | 事件条件和规则集 | 内核 hook、选择器、操作 |
| 常见用途 | 集成通知/存储的检测 | 进程可见性和显式 hook 强制执行 |
| 运行检查 | 驱动/插件/运行时元数据和事件丢失 | BTF/hook 支持、策略范围、副作用 |
| 性能 | 在实际负载下测量 CPU/内存/事件丢失 | 使用相同的工作负载；仅使用 eBPF 并不能证明其更优 |

同时部署二者并不总是最佳选择。请考虑重复收集、节点权限、成本、运维复杂性和所需的强制执行能力。

## Kubernetes 审计日志

### 审计策略配置

此策略适用于**自托管的 Kubernetes API server**。在 EKS 上应用此 YAML 不会替换其托管审计策略。请启用 EKS 控制平面审计日志，并配置 CloudWatch 访问权限、保留期限和加密。

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


对 Secrets 和 serviceaccounts/token 使用 Request/RequestResponse 级别的日志记录可能会持久保存凭据正文，因此应使用 Metadata。审计规则按首次匹配执行；请将敏感资源规则放在前面。仅指定 system:anonymous 并不能捕获所有身份验证失败。请检查审计阶段、responseStatus 和身份验证日志。exec 审计记录并不代表记录了终端会话中的每条命令。

### EKS 审计日志分析

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name, responseStatus.code
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

这是 CloudWatch Logs Insights 查询，不是 Bash。403 表示响应已拒绝；请单独分类成功的读取操作。启用日志记录后，请验证日志是否已收集，并配置保留期限。

<span id="cryptocurrency-mining-detection"></span>
<span id="reverse-shell-detection"></span>
<span id="privilege-escalation-detection"></span>

## 运行时威胁检测模式

Seccomp 会限制系统调用，但拒绝调用并不总会终止进程。操作可以返回 ERRNO、kill 或 notify。RuntimeDefault 表示运行时的配置文件；应显式设置，或验证 kubelet 的 seccompDefault。仅使用 Kubernetes 1.27+ 并不会自动将其应用于每个 Pod。

AppArmor 需要节点支持并加载配置文件。Complain 模式会记录常规违规，但显式 deny 规则仍然可以阻止操作。readOnlyRootFilesystem 是容器 securityContext 字段；它无法阻止恶意使用可写卷、网络访问或内存。

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


当前 GuardDuty Runtime Monitoring 支持 EKS EC2 节点和 EKS Auto Mode，但不支持 EKS Hybrid Nodes 或 EKS Fargate。请检查官方 OS/内核/架构/agent 版本矩阵和覆盖状态。启用该功能并不能证明每个节点都已获得正常覆盖。

Hubble `--verdict DROPPED` 会显示流量丢弃；但并非每次丢弃都是由 NetworkPolicy 导致的。请结合丢弃原因和策略判定进行检查。

<span id="forensics-container"></span>

## 事件响应

### Pod 隔离流程

标准 NetworkPolicy 的允许规则会合并为并集。添加一个 ingress/egress 列表为空的策略，并不会覆盖另一项策略允许的连接。应用标签可能会选中属于该应用的多个 Pod。

1. 确认命名空间、Pod UID、节点、所属控制器和现有网络策略。
2. 选择经过批准的隔离机制。对于 CNI 特定的显式拒绝或对现有允许规则的更改，请审查确切的目标、影响和恢复方案。
3. 测试已建立和新建的连接；考虑 hostNetwork、节点流量和 CNI 限制。
4. 保护证据，并记录隔离、中断和恢复决策。

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


此脚本通过 API 收集 Pod 元数据/日志，并记录校验和。它使用子进程模拟程序进行了测试，包括失败情况和权限为 0700 的私有输出目录；未在真实集群上测试。Pod spec 和日志可能包含机密/个人信息；请使用经过批准的存储和访问控制。

新的取证 Pod 不会自动在目标节点上运行，也不会自动共享目标进程命名空间。hostPath /proc、SYS_PTRACE 和 NET_ADMIN 会授予大量访问权限；如有需要，请使用经过批准的流程。emptyDir 不是持久的证据存储。归档临时容器的 `/` 并不自动等同于目标容器文件系统的快照。

<span id="falco-to-elasticsearch"></span>
<span id="prometheus-grafana-dashboard"></span>

<span id="siemsoar-integration"></span>

## SIEM/SOAR 集成

请将 ServiceMonitor 的命名空间、选择器和端口与实际的 Service 进行比较。Falco chart 提供 metrics Service；Falcosidekick 在其 HTTP 端口上公开指标。只有 monitoring.coreos.com/v1 可用时，Sidekick chart 才会渲染 ServiceMonitor。

```promql
sum by (priority) (rate(falcosecurity_falcosidekick_falco_events_total[5m]))
```

这是 Falcosidekick 2.35.0 的已接收事件计数器。不要将原始 falco_events_total 当作通用指标名称。请区分累计计数和区间速率；检查实际标签、重置、输出故障和缺失的抓取数据。即使是合成 Slack/PagerDuty/SIEM 通知测试，也应与接收者和运维流程协调。

<span id="table-of-contents"></span>
<span id="recommendations"></span>

## 总结

本地检查覆盖了两条 Falco 规则、四种配置 schema 情况、三个 Tetragon JSON 过滤器和两个 CRD、三个 Helm chart，以及四种证据脚本成功/失败情况。未执行内核附加、检测效果、实际强制执行、GuardDuty 覆盖、审计/CloudWatch 收集或外部通知。

## 参考资料

- [Falco Kubernetes 安装](https://falco.org/docs/setup/kubernetes/)
- [Falco 0.45.0 配置](https://github.com/falcosecurity/falco/blob/0.45.0/falco.yaml)
- [Falcosidekick 2.35.0 配置](https://github.com/falcosecurity/falcosidekick/blob/2.35.0/config_example.yaml)
- [Tetragon 跟踪策略](https://tetragon.io/docs/concepts/tracing-policy/)
- [Tetragon 强制执行](https://tetragon.io/docs/concepts/enforcement/)
- [Tetragon 1.7.1 文件监控](https://github.com/cilium/tetragon/blob/v1.7.1/examples/quickstart/file_monitoring.yaml)
- [Kubernetes 审计](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [NetworkPolicy 语义](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [AppArmor](https://kubernetes.io/docs/tutorials/security/apparmor/)
- [EKS 控制平面日志](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [GuardDuty EKS 运行时要求](https://docs.aws.amazon.com/guardduty/latest/ug/prereq-runtime-monitoring-eks-support.html)
- [MITRE ATT&CK 容器](https://attack.mitre.org/matrices/enterprise/containers/)
