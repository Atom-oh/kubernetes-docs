# Runtime Security クイズ

このクイズでは、Falco、Seccomp、AppArmor、eBPF ベースの security、EKS runtime security についての理解を確認します。

## クイズ問題

### 1. Falco は runtime threat を検出するためにどの technology を使用しますか？

A. network packet の分析
B. system call (syscall) の監視
C. log analysis
D. memory scanning

<details>
<summary>答えを表示</summary>

**答え: B. system call (syscall) の監視**

**解説:**
Falco は eBPF または kernel module を使用して、kernel level で system call を監視します。process execution、file access、network connection などの activity を real-time で検出します。

</details>

### 2. Seccomp の主な機能は何ですか？

A. network traffic filtering
B. process が実行できる system call を制限する
C. file system encryption
D. user authentication

<details>
<summary>答えを表示</summary>

**答え: B. process が実行できる system call を制限する**

**解説:**
Seccomp (Secure Computing Mode) は、whitelist approach を使用して process が実行できる system call を制限します。許可されていない syscall を試行すると、process は終了します。

</details>

### 3. Kubernetes 1.27+ で推奨される default Seccomp profile はどれですか？

A. Unconfined
B. RuntimeDefault
C. Localhost
D. Docker/default

<details>
<summary>答えを表示</summary>

**答え: B. RuntimeDefault**

**解説:**
RuntimeDefault は container runtime (containerd, CRI-O) によって提供される default Seccomp profile です。
```yaml
securityContext:
  seccompProfile:
    type: RuntimeDefault
```

ほとんどの workload に対して適切な security level を提供します。

</details>

### 4. Falco rule における priority field の役割は何ですか？

A. rule の実行順序を決定する
B. alert の severity level を指定する
C. resource quota を設定する
D. log retention period を設定する

<details>
<summary>答えを表示</summary>

**答え: B. alert の severity level を指定する**

**解説:**
Falco rule の priority は、検出された event の severity を指定します。
- EMERGENCY, ALERT, CRITICAL, ERROR
- WARNING, NOTICE, INFORMATIONAL, DEBUG

```yaml
- rule: Shell in Container
  priority: WARNING
```

</details>

### 5. AppArmor の complain mode では何が起こりますか？

A. すべての access を block する
B. policy violation のみを log に記録する
C. profile を無効にする
D. alert のみを送信する

<details>
<summary>答えを表示</summary>

**答え: B. policy violation のみを log に記録する**

**解説:**
AppArmor mode:
- **enforce**: policy violation 時に block して log に記録する
- **complain**: policy violation 時に log に記録するのみ（debug 用）
- **unconfined**: profile は適用されない

Complain mode は新しい profile の test に役立ちます。

</details>

### 6. Amazon GuardDuty EKS Runtime Monitoring で検出される threat ではないものはどれですか？

A. cryptocurrency mining
B. privilege escalation
C. code quality issue
D. container escape attempt

<details>
<summary>答えを表示</summary>

**答え: C. code quality issue**

**解説:**
GuardDuty EKS Runtime Monitoring の検出 type:
- PrivilegeEscalation
- Execution (malicious code)
- CryptoCurrency (mining)
- CredentialAccess
- DefenseEvasion

Code quality は development quality issue であり、security threat ではありません。

</details>

### 7. Cilium Tetragon の主な機能は何ですか？

A. container image scanning
B. eBPF ベースの security observability
C. network policy management
D. Secrets management

<details>
<summary>答えを表示</summary>

**答え: B. eBPF ベースの security observability**

**解説:**
Tetragon は Cilium の eBPF ベースの security observability tool です。
- process execution monitoring
- network activity tracking
- file access monitoring
- policy ベースの real-time response（例: process termination）

</details>

### 8. Falco で container 内の shell execution を検出する condition はどれですか？

A. container and shell_procs
B. spawned_process and container and shell_procs
C. exec and shell
D. process.name = bash

<details>
<summary>答えを表示</summary>

**答え: B. spawned_process and container and shell_procs**

**解説:**
Falco rule の例:
```yaml
- rule: Shell in Container
  condition: >
    spawned_process and
    container and
    shell_procs
  output: "Shell spawned in container"
  priority: WARNING
```

`spawned_process` は新しい process creation を意味し、`container` は container environment を意味し、`shell_procs` は shell process（bash、sh など）を意味します。

</details>

### 9. Pod に read-only root filesystem を設定するにはどうしますか？

A. readOnlyRootFilesystem: true
B. rootfs: readonly
C. filesystem.readonly: true
D. immutableRoot: true

<details>
<summary>答えを表示</summary>

**答え: A. readOnlyRootFilesystem: true**

**解説:**
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

この設定により、container の root filesystem が read-only になり、malicious code による file の変更を防ぎます。write access が必要な path には emptyDir volume を mount します。

</details>

### 10. runtime security における「Defense in Depth」strategy とは何を意味しますか？

A. 単一の security layer に依存する
B. 複数の重なり合う security layer を適用する
C. defense のみに focus する
D. external boundary のみを保護する

<details>
<summary>答えを表示</summary>

**答え: B. 複数の重なり合う security layer を適用する**

**解説:**
Defense in Depth は複数の security layer を使用します。
1. Build time: Image scanning、vulnerability analysis
2. Deploy time: Admission Control、PSS/PSA
3. Runtime: Falco、Seccomp、AppArmor

1つの layer が突破された場合でも、他の layer が保護を提供します。

</details>

### 11. Hubble で policy によって block された traffic を表示する command はどれですか？

A. hubble observe --blocked
B. hubble observe --verdict DROPPED
C. hubble observe --denied
D. hubble observe --policy-violation

<details>
<summary>答えを表示</summary>

**答え: B. hubble observe --verdict DROPPED**

**解説:**
```bash
hubble observe --verdict DROPPED
```

`--verdict DROPPED` は network policy によって拒否された traffic を filter します。policy violation を real-time で monitor および分析できます。

</details>

### 12. runtime security の best practice ではないものはどれですか？

A. すべての workload に RuntimeDefault Seccomp を適用する
B. すべての node に Falco を DaemonSet として deploy する
C. container を root として実行する
D. read-only root filesystem を使用する

<details>
<summary>答えを表示</summary>

**答え: C. container を root として実行する**

**解説:**
runtime security の best practice:
- RuntimeDefault Seccomp を適用する
- Falco を deploy する
- Read-only root filesystem
- **non-root user として実行する** (runAsNonRoot: true)
- 不要な capability を削除する
- GuardDuty runtime monitoring を有効にする

root として実行することは危険です。container escape により host 上で昇格された privilege が得られるためです。

</details>
