# Runtime Security

> **最終更新**: September 13, 2026
> **検証ベースライン**: Falco 0.44.1 / chart 9.1.0、Falcosidekick 2.35.0 / chart 0.14.0、Tetragon 1.7.1。実際の kernel、OS、node type のサポートを確認してください。

Runtime security は process、file、network のアクティビティを監視し、検証済みの policy を通じて選択した操作を制限します。**alert は侵害の証明ではありません。検知と防止には別々のテストが必要です。**このガイドは、ローカル CLI、schema、Helm、および synthetic event で確認しました。実際の cluster、kernel BPF program、notification channel は使用していません。

<span id="container-runtime-threats"></span>
<span id="detection-technologies"></span>

## Runtime Threat の状況

| 観測ポイント | 確認できる内容 | 制限事項 |
|---|---|---|
| Syscall/kernel hook | Process 実行、file access、connection attempt | drop event、privilege、kernel support、filter を確認する |
| Kubernetes audit | API requester、verb、object、response status | Pod 内のすべての process/file 操作は表示しない |
| Network flow | Connection、drop、policy verdict | port または暗号化された connection だけでは悪意を立証できない |
| Image/admission policy | Vulnerability、signature、Pod setting | deployment 後のすべての挙動を検知するわけではない |

eBPF だけでは低 overhead や安全性は保証されません。実際の node で hook、event volume、filtering、output cost、CPU、memory を測定してください。command name が indicator と一致するという理由だけで、production process を自動的に kill してはいけません。

<span id="default-rule-examples"></span>

## Falco

### Falco の概要

Falco は event を rule と照合して評価します。一般的な syscall path は `Linux event → modern eBPF/kmod capture → Falco filter/rule → JSON output → Falcosidekick → notification/storage` です。Slack と PagerDuty は downstream integration であり、Falco rule engine 内の native Slack client ではありません。

0.44.1 distribution には container plugin 0.7.1 が同梱されています。これは container.id などの field を提供するため、すべての plugin を無効にすると、それらの field を使用する rule は compile/run できなくなります。runtime socket、Kubernetes metadata collection、access permission を確認してください。

### Falco Installation (EKS)

この例は、host access を管理している Linux EC2 node を対象としています。DaemonSet が Fargate やその他の制限された host 上で実行できると想定しないでください。modern eBPF の kernel/BTF/capability 要件を確認してください。chart 9.1.0 は明示的な driver kind `modern_ebpf` と `kmod` をサポートしています。古い `ebpf` 設定を残さないでください。

[example directory](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/runtime-security)を download し、`examples/security/runtime-security` からこれらの command を実行します。[example README](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/runtime-security/README.md)には、3 つの values file と rule が説明されています。

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

Sidekick chart の appVersion は default image tag と異なるため、この例では image.tag を 2.35.0 に明示的に固定しています。まず output credential Secret と Prometheus Operator CRD を準備してください。Secret がないと Pod の起動を妨げる可能性があります。最小限の lab では、使用しない notification/metrics option を無効にしてください。

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


この設定は、個別に install した falcosidekick ClusterIP Service に HTTP を送信します。namespace を共有しても traffic の authentication や encryption は行われません。実際の trust boundary に従って access policy と TLS/mTLS を設定し、node/Falco connectivity を確認してください。Falco は json_output や http_output のような snake_case field を使用します。古い jsonOutput/httpOutput と削除された grpc 設定は 0.44.1 schema で失敗します。

### Falco Rule の構造

これらの rule は必要な macro を独自に定義し、default rule name を置き換えません。既存の rule を意図的に変更する場合は、固定した ruleset の override syntax を使用してください。

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


enter event の削除後、Falco 0.44.1 は evt.dir が deprecated であると warning を出します。これらの例では、successful exec event と read event を直接選択しています。正当な Kubernetes client も service account token を読み取るため、read signal だけでは「unauthorized access」ではありません。workload baseline、承認済み binary、Pod identity と組み合わせてください。

### Custom Rule の作成

| Pattern | 考えられる signal | 必要な考慮事項 |
|---|---|---|
| 疑わしい mining | Process name、pool/stratum string、通常と異なる resource use | rename と正当な computation により heuristic が回避または発動される可能性がある |
| 疑わしい reverse shell | shell argv 内の connection string と通常と異なる outbound flow | exec event の fd.name は network connection の証明ではない |
| Privilege escalation | credential change、SUID setting、capability | user.uid/proc.uid/proc.suid の意味と操作の成功を確認する |
| 疑わしい escape | Namespace/host-path access と通常と異なる mount | nsenter または /.dockerenv string は escape の成功を立証しない |

Rule compile は検知の有効性を測定しません。段階的 rollout の前に、synthetic/authorized lab event、正常な workload、欠落した metadata、drop counter をテストしてください。argument、path、log には secret が含まれる可能性があります。event field、retention、access を制限してください。

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


falcosidekick-output-credentials は、envFrom を通じて読み取る同一 namespace の既存 Secret です。secret-management process を通じて、SLACK_WEBHOOKURL、PAGERDUTY_ROUTINGKEY、ELASTICSEARCH_HOSTPORT/USERNAME/PASSWORD など、承認済み output の variable だけを指定してください。Helm values 内に `${ELASTIC_PASSWORD}` と記述しても shell substitution は実行されません。credential を Git、command line、review log に公開しないでください。

AWS setting は config.aws 配下に配置します。workload identity を確認し、IAM action/resource の scope を対象の log group/stream に限定してください。minimumpriority には `high` ではなく emergency/alert/critical/error/warning/notice/informational/debug を使用します。各 output の activation condition、retry、failure metrics を確認してください。この例では Web UI を無効にしています。

<span id="tetragon-installation"></span>
<span id="tracingpolicy-basic-structure"></span>
<span id="process-monitoring"></span>

## Tetragon

### Tetragon の概要

Tetragon は Cilium CNI とは独立して実行できます。built-in の process_exec/exit event と追加の TracingPolicy hook を区別してください。flow は `kernel hook → selector → Post/supported action → JSON/gRPC/metrics` です。Kubernetes CRD 自体は kernel 内で実行されません。

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


operator/CRD の readiness と、各 node の kernel、BTF、capability を確認してください。Helm rendering は hook attachment を保証しません。namespaced example は demo-app workload を対象とします。選択した policy type と hook の有効な scope を確認してください。

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


`security_file_permission(struct file *, int mask)` の第 2 argument は permission mask です。MAY_READ=4、MAY_WRITE=2 です。単一 argument の security_file_open function に「index 1 = open flag」を割り当てるのは誤りです。open flag の O_WRONLY=1/O_RDWR=2 もこの permission mask とは異なります。この hook だけでは、すべての mmap/truncate/file mutation を対象にできません。

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


tcp_connect は TCP connection attempt を観測します。destination port だけでは malicious traffic や policy rejection を意味しません。UDP port 53 のアクティビティは完全な DNS question/answer analysis を提供しません。適切な DNS telemetry path を使用してください。

### Runtime Enforcement

Post/monitor の挙動から開始し、正常な操作と false positive を確認してください。Sigkill は signal を送信します。hook と kernel の挙動によっては、すでに発生した effect を取り消せません。return-value override には、support される syscall/security function、kernel setting、適切な error result が必要です。任意の kprobe がすべてこれを support するわけではありません。

filename や argv string から universal な mining/reverse-shell prevention を主張しないでください。execve argv は pointer の配列であり、単一の string argument ではありません。これを単一 string として読み取っても、意図した完全な command line は検査できません。process-event argument filtering と kernel action を区別し、承認された狭い scope の lab で enforcement を検証してください。

### Tetragon CLI の使用

```bash
kubectl exec -n kube-system ds/tetragon -c tetragon -- tetra getevents -o json
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact --namespace production --process curl
# Filter stored synthetic events locally:
tetra getevents -o json --namespace demo-app < events.jsonl
```

DaemonSet に対する実行では Pod/node の agent が選択されます。これは cluster-wide aggregation ではありません。ここでは stdin filtering path のみを実行しました。tetra tracingpolicy modify の 1.7.1 implementation も gRPC client を作成するため、offline validator としては使用しませんでした。

<span id="feature-comparison-table"></span>
<span id="use-case-recommendations"></span>

## Falco と Tetragon の比較

| 基準 | Falco | Tetragon |
|---|---|---|
| Policy | Event condition と ruleset | Kernel hook、selector、action |
| 一般的な用途 | notification/storage integration を伴う検知 | Process visibility と明示的な hook enforcement |
| 運用上の確認事項 | Driver/plugin/runtime metadata と drop event | BTF/hook support、policy scope、side effect |
| Performance | 実際の load で CPU/memory/event loss を測定 | 同じ workload を使用する。eBPF だけで優位性は立証されない |

両方を deploy することが自動的に最善の選択となるわけではありません。重複収集、node privilege、cost、operational complexity、必要な enforcement を考慮してください。

## Kubernetes Audit Logging

### Audit Policy Configuration

この policy は **self-managed Kubernetes API server** 用です。この YAML を適用しても、EKS の managed audit policy は置き換えられません。EKS control-plane audit log を有効にし、CloudWatch の access、retention、encryption を設定してください。

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


Secrets および serviceaccounts/token の Request/RequestResponse logging は credential body を永続化する可能性があるため、Metadata を使用してください。audit rule は first-match です。sensitive-resource rule を先頭に配置してください。system:anonymous だけでは、すべての authentication failure を捕捉できません。audit stage、responseStatus、authentication log を確認してください。exec audit record は terminal session 内のすべての command の記録ではありません。

### EKS Audit Log Analysis

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.name, responseStatus.code
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

これは CloudWatch Logs Insights query であり、Bash ではありません。403 は拒否された response です。successful read は別に分類してください。logging を有効にした後に collection を確認し、retention を設定してください。

<span id="cryptocurrency-mining-detection"></span>
<span id="reverse-shell-detection"></span>
<span id="privilege-escalation-detection"></span>

## Runtime Threat Detection Pattern

Seccomp は syscall を制限しますが、rejection が必ず process を terminate するとは限りません。action は ERRNO を返す、kill する、または notify できます。RuntimeDefault は runtime の profile を意味します。明示的に設定するか、kubelet seccompDefault を確認してください。Kubernetes 1.27+ だけでは、すべての Pod に自動的に適用されません。

AppArmor には node support と loaded profile が必要です。Complain mode は通常の violation を記録しますが、明示的な deny rule は引き続き block できます。readOnlyRootFilesystem は container securityContext field です。writable volume の悪意ある使用、network access、memory は防止しません。

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


現在の GuardDuty Runtime Monitoring は EKS EC2 node と EKS Auto Mode を support していますが、EKS Hybrid Nodes と EKS Fargate は support していません。公式の OS/kernel/architecture/agent-version matrix と coverage health を確認してください。この feature を有効にしても、すべての node の正常な coverage が確立されるわけではありません。

Hubble `--verdict DROPPED` は drop を表示します。すべての drop が NetworkPolicy denial というわけではありません。drop reason と policy verdict を合わせて確認してください。

<span id="forensics-container"></span>

## Incident Response

### Pod Isolation Procedure

標準の NetworkPolicy は union として組み合わされます。empty ingress/egress list を持つ policy を追加しても、別の policy が許可している connection は override されません。app label は application に属する複数の Pod を選択できます。

1. namespace、Pod UID、node、owner、既存の network policy を特定します。
2. 承認済みの isolation mechanism を選択します。CNI 固有の明示的な deny や既存 allow の変更では、正確な target、impact、recovery を確認します。
3. established connection と new connection をテストし、hostNetwork、node traffic、CNI limitation を考慮します。
4. evidence を保護し、isolation、interruption、recovery の判断を記録します。

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


この script は API を通じて Pod metadata/log を収集し、checksum を記録します。これは real cluster ではなく、subprocess double を使用して failure と private 0700 output directory を含めてテストされました。Pod spec と log には secret/personal information が含まれる可能性があります。承認済みの storage と access control を使用してください。

新しい forensic Pod が、target node で実行されたり、target process namespace を共有したりするとは限りません。hostPath /proc、SYS_PTRACE、NET_ADMIN は大きな access を付与します。必要な場合は承認済み procedure を使用してください。emptyDir は durable evidence storage ではありません。ephemeral container の `/` を archive しても、target container filesystem の snapshot になるとは限りません。

<span id="falco-to-elasticsearch"></span>
<span id="prometheus-grafana-dashboard"></span>

<span id="siemsoar-integration"></span>

## SIEM/SOAR Integration

ServiceMonitor namespace、selector、port を実際の Service と比較してください。Falco chart には metrics Service があり、Falcosidekick は HTTP port で metrics を公開します。Sidekick chart が ServiceMonitor を render するのは、monitoring.coreos.com/v1 が利用可能な場合のみです。

```promql
sum by (priority) (rate(falcosecurity_falcosidekick_falco_events_total[5m]))
```

これは Falcosidekick 2.35.0 の received-event counter です。元の falco_events_total を universal metric name として扱わないでください。cumulative count と interval rate を区別し、実際の label、reset、output failure、欠落した scrape を確認してください。synthetic な Slack/PagerDuty/SIEM notification test であっても、recipient と operational process と調整してください。

<span id="table-of-contents"></span>
<span id="recommendations"></span>

## まとめ

ローカル検証では、2 つの Falco rule、4 つの configuration-schema case、3 つの Tetragon JSON filter と 2 つの CRD、3 つの Helm chart、4 つの evidence-script success/failure case を対象にしました。kernel attachment、detection efficacy、実際の enforcement、GuardDuty coverage、audit/CloudWatch collection、external notification は実行していません。

## 参考資料

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
