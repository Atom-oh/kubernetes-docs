# Kubescape クイズ

以下の問題で、Kubescape の security posture management（セキュリティ態勢管理）に関する理解を確認しましょう。

---

## 問題

### 1. CNCF における Kubescape の project status は何ですか？

- A) Graduated project
- B) Incubating project
- C) Sandbox project
- D) CNCF project ではない

<details>
<summary>答えを表示</summary>

**回答: C) Sandbox project**

**解説:**
Kubescape は 2022 年に CNCF Sandbox project として受け入れられました。もともとは ARMO によって開発され、CNCF に寄贈されました。Sandbox project として、CNCF が成長の可能性があると考える初期段階の project です。

</details>

---

### 2. Kubescape は compliance scanning のためにどの security frameworks をサポートしていますか？

- A) NSA-CISA のみ
- B) CIS Benchmarks のみ
- C) NSA-CISA、CIS Benchmarks、MITRE ATT&CK
- D) OWASP と PCI-DSS のみ

<details>
<summary>答えを表示</summary>

**回答: C) NSA-CISA、CIS Benchmarks、MITRE ATT&CK**

**解説:**
Kubescape は複数の security frameworks をサポートしています。

```bash
# Scan with NSA-CISA framework
kubescape scan framework nsa

# Scan with CIS Kubernetes Benchmark
kubescape scan framework cis-v1.23-t1.0.1

# Scan with MITRE ATT&CK
kubescape scan framework mitre
```

- **NSA-CISA**: 米国政府機関による Kubernetes Hardening Guide
- **CIS**: Center for Internet Security Kubernetes Benchmarks
- **MITRE ATT&CK**: 攻撃手法を mapping する threat-based security framework

</details>

---

### 3. Kubescape で Kubernetes cluster を scan する正しい CLI syntax は何ですか？

- A) kubescape check cluster
- B) kubescape scan
- C) kubescape audit cluster
- D) kubescape analyze

<details>
<summary>答えを表示</summary>

**回答: B) kubescape scan**

**解説:**
Kubescape CLI の scan commands は次のとおりです。

```bash
# Scan current cluster
kubescape scan

# Scan specific namespace
kubescape scan --include-namespaces production

# Scan YAML files before deployment
kubescape scan *.yaml

# Scan with specific framework
kubescape scan framework nsa

# Scan specific control
kubescape scan control C-0034
```

`scan` subcommand は、すべての scanning operations に対する主要な interface です。

</details>

---

### 4. Kubescape Operator mode と CLI mode の主な違いは何ですか？

- A) Operator mode は nodes のみを scan する
- B) CLI mode は continuous monitoring を提供し、Operator は one-time
- C) Operator は in-cluster components による continuous monitoring を提供し、CLI は one-time scans
- D) 違いはない

<details>
<summary>答えを表示</summary>

**回答: C) Operator は in-cluster components による continuous monitoring を提供し、CLI は one-time scans**

**解説:**
Kubescape の deployment modes は次のとおりです。

**CLI Mode:**
```bash
# One-time scan from local machine
kubescape scan
```
- Ad-hoc scanning
- CI/CD integration
- Local development

**Operator Mode:**
```bash
# Install in-cluster operator
helm repo add kubescape https://kubescape.github.io/helm-charts
helm install kubescape kubescape/kubescape-operator
```
- Continuous monitoring
- Scheduled scans
- In-cluster vulnerability scanning
- 可視化のための ARMO platform との integration

</details>

---

### 5. Kubescape は controls の risk scores をどのように計算しますか？

- A) Binary pass/fail のみ
- B) severity に affected resources count を掛けた値に基づく
- C) Random assignment
- D) namespace priority に基づく

<details>
<summary>答えを表示</summary>

**回答: B) severity に affected resources count を掛けた値に基づく**

**解説:**
Kubescape の risk scoring は次のとおりです。

```
Risk Score = Severity Score x (Failed Resources / Total Resources)
```

出力例:
```
┌──────────────────────────────────────────────────┬────────────────┬───────┐
│ Control Name                                      │ Failed Resources│ Score │
├──────────────────────────────────────────────────┼────────────────┼───────┤
│ Privileged container                              │ 3/50           │ 18%   │
│ Resource limits                                   │ 25/50          │ 35%   │
│ Non-root containers                               │ 10/50          │ 42%   │
└──────────────────────────────────────────────────┴────────────────┴───────┘
```

高い scores は、即時対応が必要なより大きな risk を示します。

</details>

---

### 6. CI/CD pipelines で compliance threshold を強制する flag はどれですか？

- A) --min-score
- B) --compliance-threshold
- C) --fail-threshold
- D) --severity-threshold

<details>
<summary>答えを表示</summary>

**回答: B) --compliance-threshold**

**解説:**
CI/CD pipelines で Kubescape を使用する例です。

```bash
# Fail pipeline if compliance drops below 80%
kubescape scan --compliance-threshold 80

# Example GitLab CI
kubescape-scan:
  script:
    - kubescape scan framework nsa --compliance-threshold 75
    - kubescape scan framework cis --compliance-threshold 80
```

threshold は percentage (0-100) です。全体の compliance score が threshold を下回ると、scan は失敗します（non-zero exit）。

```bash
# Exit codes
# 0: Passed threshold
# 1: Failed threshold
# 2: Error during scan
```

</details>

---

### 7. Kubescape は kube-bench とどのように異なりますか？

- A) kube-bench は applications のみを scan し、Kubescape は infrastructure を scan する
- B) Kubescape は workload configurations を scan し、kube-bench は node-level CIS benchmarks に重点を置く
- C) これらは同一の tools
- D) kube-bench は cloud providers 専用

<details>
<summary>答えを表示</summary>

**回答: B) Kubescape は workload configurations を scan し、kube-bench は node-level CIS benchmarks に重点を置く**

**解説:**
Kubescape と kube-bench の比較:

| Feature | Kubescape | kube-bench |
|---------|-----------|------------|
| Focus | Workload/config security | Node/control plane security |
| Scope | Deployments, Pods, RBAC | kubelet, API server, etcd |
| Frameworks | NSA, CIS, MITRE | CIS Benchmarks only |
| Run Location | Outside cluster (CLI) or in-cluster | Must run on each node |
| Image Scanning | Yes (with Grype) | No |
| RBAC Analysis | Yes | No |

包括的な security のために両方を併用してください。
- kube-bench: Cluster infrastructure hardening
- Kubescape: Workload and configuration security

</details>

---

### 8. Kubescape は RBAC security analysis のためにどの機能を提供しますか？

- A) RBAC policy generation
- B) permissions と risks を示す RBAC visualization
- C) Automatic RBAC remediation
- D) RBAC migration tools

<details>
<summary>答えを表示</summary>

**回答: B) permissions と risks を示す RBAC visualization**

**解説:**
Kubescape の RBAC analysis capabilities は次のとおりです。

```bash
# Scan RBAC configurations
kubescape scan control C-0035  # Cluster-admin binding
kubescape scan control C-0036  # Wildcard permissions
kubescape scan control C-0039  # Risky service accounts
```

RBAC visualization の features:
- ServiceAccounts を Roles/ClusterRoles に mapping する
- 過度に permissive な bindings を特定する
- 危険な permissions（secrets access、pod exec）を強調表示する
- RBAC を通じた attack paths を表示する

検出例:
```
ServiceAccount 'default' in namespace 'production' has:
- Cluster-admin binding (CRITICAL)
- Secrets list/get permissions (HIGH)
- Pod exec permissions (HIGH)
```

</details>

---

### 9. Kubescape は image scanning のためにどの vulnerability scanner と統合されていますか？

- A) Trivy
- B) Clair
- C) Grype
- D) Anchore

<details>
<summary>答えを表示</summary>

**回答: C) Grype**

**解説:**
Kubescape は container image vulnerability scanning のために Grype（Anchore による）と統合されています。

```bash
# Enable image scanning
kubescape scan --enable-host-scan

# Operator mode includes automatic image scanning
helm install kubescape kubescape/kubescape-operator \
  --set capabilities.vulnerabilityScan=enable
```

Grype integration は次を提供します。
- container images 内の CVE detection
- SBOM (Software Bill of Materials) generation
- severity-based prioritization
- security findings との integration

結果は、comprehensive risk assessment のために configuration issues と vulnerability data を組み合わせます。

</details>

---

### 10. Kubescape は control exceptions をどのように扱いますか？

- A) Exceptions はサポートされていない
- B) 除外する controls と resources を指定する exception YAML files を使用する
- C) command-line flags のみを通じて
- D) source code を変更することで

<details>
<summary>答えを表示</summary>

**回答: B) 除外する controls と resources を指定する exception YAML files を使用する**

**解説:**
Kubescape は configuration files による exceptions をサポートしています。

```yaml
# exceptions.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubescape-exceptions
data:
  exceptions: |
    - name: "Allow privileged kube-system pods"
      policyType: postureExceptionPolicy
      actions:
        - alertOnly
      resources:
        - designatorType: Attributes
          attributes:
            namespace: kube-system
      posturePolicies:
        - controlID: C-0057  # Privileged container
```

exceptions を適用します。
```bash
kubescape scan --exceptions exceptions.yaml
```

これにより次が可能になります。
- 既知の false positives を抑制する
- 特定の resources について risk を受け入れる
- クリーンな scan reports を維持する

</details>

---

## スコア計算

- **9-10 correct**: 優秀 - Kubescape について深く理解しています。
- **7-8 correct**: 良好 - 主要な概念をしっかり把握しています。
- **5-6 correct**: 可 - 追加学習が必要な領域があります。
- **4 or fewer**: ドキュメントをもう一度確認してください。

## 関連ドキュメント

- [Kubescape による Security Posture Management](../../security/11-kubescape.md)
