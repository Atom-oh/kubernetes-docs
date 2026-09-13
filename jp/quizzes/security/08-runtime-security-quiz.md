# Runtime Security クイズ

> **最終更新**: September 13, 2026

このクイズでは、Falco、Seccomp、AppArmor、eBPF ベースのセキュリティ、および EKS の Runtime Security に関する理解を確認します。

## クイズ問題

### 1. Falco は Runtime 脅威を検出するためにどの技術を使用しますか？

- A. Network パケット分析
- B. System call (syscall) の監視
- C. Log 分析
- D. Memory スキャン

<details>
<summary>回答を表示</summary>

**回答: B. System call (syscall) の監視**

**解説:**
Falco は一般に Linux の syscall event をルールと照合して評価します。plugin は他の event source を提供できます。0.44.1 では、container field は container plugin から取得されます。modern_ebpf の kernel/BTF 要件と metadata collection を確認してください。

</details>

### 2. Seccomp の主な機能は何ですか？

- A. Network traffic filtering
- B. Process が実行できる System call を制限する
- C. File system encryption
- D. User authentication

<details>
<summary>回答を表示</summary>

**回答: B. Process が実行できる System call を制限する**

**解説:**
Seccomp は System call を filter します。拒否時には、profile action に応じて ERRNO を返す、terminate する、または notify することがあり、常に process を kill するわけではありません。

</details>

### 3. Kubernetes 1.27+ で推奨されるデフォルトの Seccomp profile は何ですか？

- A. Unconfined
- B. RuntimeDefault
- C. Localhost
- D. Docker/default

<details>
<summary>回答を表示</summary>

**回答: B. RuntimeDefault**

**解説:**
RuntimeDefault は container runtime によって提供される profile です。seccompProfile を明示的に設定するか、kubelet の seccompDefault を確認してください。Kubernetes 1.27+ だけでは、すべての Pod に自動的に適用されません。

</details>

### 4. Falco rule の priority field の役割は何ですか？

- A. Rule の実行順序を決定する
- B. Alert の severity level を指定する
- C. Resource quota を設定する
- D. Log retention period を設定する

<details>
<summary>回答を表示</summary>

**回答: B. Alert の severity level を指定する**

**解説:**
priority は評価順序ではなく event severity です。標準 level は EMERGENCY、ALERT、CRITICAL、ERROR、WARNING、NOTICE、INFORMATIONAL、DEBUG です。完全な rule には、desc、condition、output などの field も必要です。

</details>

### 5. AppArmor の complain mode では何が起こりますか？

- A. すべての access を block する
- B. 通常の violation を Log に記録する。明示的な deny は引き続き block できる
- C. Profile を無効化する
- D. Alert のみを送信する

<details>
<summary>回答を表示</summary>

**回答: B. 通常の violation を Log に記録する。明示的な deny は引き続き block できる**

**解説:**
Complain mode は通常、policy violation を許可しながら Log に記録しますが、明示的な deny rule は引き続き access を block できます。すべての access を無条件に許可するものではありません。kernel support と load 済みの profile を確認してください。

</details>

### 6. Amazon GuardDuty EKS Runtime Monitoring が検出する脅威ではないものはどれですか？

- A. Cryptocurrency mining
- B. Privilege escalation
- C. Code quality issue
- D. Container escape attempt

<details>
<summary>回答を表示</summary>

**回答: C. Code quality issue**

**解説:**
GuardDuty Runtime Monitoring は security threat を検出し、code-quality defect は検出しません。現在の EKS support は EC2 と Auto Mode を対象としますが、EKS Hybrid Nodes と EKS Fargate は対象外です。OS/kernel/agent 要件と coverage health を確認してください。

</details>

### 7. Cilium Tetragon の主な機能は何ですか？

- A. Container image scanning
- B. eBPF ベースの security observability
- C. Network policy management
- D. Secrets management

<details>
<summary>回答を表示</summary>

**回答: B. eBPF ベースの security observability**

**解説:**
Tetragon は process event、file/network hook、対応する action を提供します。Cilium CNI の installation は必要ありません。hook support、selector scope、false positive を確認し、enforcement の前に Post/monitor behavior を test してください。

</details>

### 8. Falco で container 内の shell 実行を検出する condition は何ですか？

- A. container and shell_procs
- B. spawned_process and container and shell_procs
- C. exec and shell
- D. process.name = bash

<details>
<summary>回答を表示</summary>

**回答: B. spawned_process and container and shell_procs**

**解説:**
この expression は、ruleset から load された spawned_process、container、shell_procs macro に依存します。shell が正当な場合もあり、compromise の証明にはなりません。このガイドでは、独立した macro と一意の rule name を定義しています。

</details>

### 9. Pod に read-only root filesystem を設定するにはどうしますか？

- A. readOnlyRootFilesystem: true
- B. rootfs: readonly
- C. filesystem.readonly: true
- D. immutableRoot: true

<details>
<summary>回答を表示</summary>

**回答: A. readOnlyRootFilesystem: true**

**解説:**
readOnlyRootFilesystem は container の securityContext に属します。書き込み可能な volume または /tmp は別途提供できます。書き込み可能な volume の悪意ある使用、network access、memory を防ぐものではありません。

</details>

### 10. Runtime Security における「Defense in Depth」strategy とは何を意味しますか？

- A. 単一の security layer に依存する
- B. 複数の重なり合う security layer を適用する
- C. Defense のみに焦点を当てる
- D. 外部 boundary のみを保護する

<details>
<summary>回答を表示</summary>

**回答: B. 複数の重なり合う security layer を適用する**

**解説:**
各 layer の scope と failure mode を確認しながら control を組み合わせます。Image/signature check、admission/permission、seccomp/AppArmor、runtime detection、networking、recovery は相互に補完します。より多くの tool を install するだけでは保証になりません。

</details>

<span id="_11-what-command-shows-traffic-blocked-by-policies-in-hubble"></span>

### 11. Dropped flow を filter する Hubble command はどれですか？

- A. hubble observe --blocked
- B. hubble observe --verdict DROPPED
- C. hubble observe --denied
- D. hubble observe --policy-violation

<details>
<summary>回答を表示</summary>

**回答: B. hubble observe --verdict DROPPED**

**解説:**
--verdict DROPPED は dropped flow を選択します。すべての drop が NetworkPolicy の denial であるとは限りません。drop reason と policy verdict を調べてください。この option だけでは、元の質問で示唆される policy 固有の原因を確定できません。

</details>

### 12. Runtime Security の best practice ではないものはどれですか？

- A. Workload compatibility を確認した後に RuntimeDefault を使用する
- B. 対応する node で Falco collection を確認する
- C. Container を root として実行する
- D. Read-only root filesystem を使用する

<details>
<summary>回答を表示</summary>

**回答: C. Container を root として実行する**

**解説:**
不要な root privilege を削減してください。RuntimeDefault と readOnlyRootFilesystem には、引き続き workload/node compatibility が必要です。Falco DaemonSet は Fargate など、すべての node type で実行できるわけではありません。Feature enablement と正常な GuardDuty coverage は別個に確認すべき項目です。

</details>
