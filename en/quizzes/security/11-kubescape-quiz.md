# Kubescape Quiz

> **Last Updated**: September 13, 2026

## Questions

<span id="_1-what-is-kubescape-s-project-status-in-the-cncf"></span>

### 1. What is Kubescape’s current CNCF maturity level?

- A) Graduated
- B) Incubating
- C) Sandbox
- D) Archived

<details>
<summary>Show Answer</summary>

**Answer: B) Incubating**

Kubescape joined CNCF on December 13, 2022 and became Incubating on January 13, 2025. This does not guarantee an individual installation’s security or availability.

</details>

<span id="_2-which-security-frameworks-does-kubescape-support-for-compliance-scanning"></span>

### 2. How should framework names and control counts be verified?

- A) Always use old CIS aliases
- B) Record binary/policy versions and inspect the actual list
- C) NSA control counts never change
- D) Passing a SOC2 scan completes certification

<details>
<summary>Show Answer</summary>

**Answer: B) Record binary/policy versions and inspect the actual list**

Use kubescape list frameworks and list controls --framework NSA. The reviewed NSA snapshot contains 26 controls, with applicability determined by input. Preserve policy hashes when comparing scores.

</details>

<span id="_3-what-is-the-correct-cli-syntax-to-scan-a-kubernetes-cluster-with-kubescape"></span>

### 3. What happens when a local file target is omitted from kubescape scan?

- A) It always fails
- B) It can scan the current kubeconfig cluster
- C) It always scans only local files
- D) It always performs a dry run

<details>
<summary>Show Answer</summary>

**Answer: B) It can scan the current kubeconfig cluster**

CI should pass an existing explicit local file and reject empty/missing targets. --keep-local, an isolated cache, and pinned policy do not replace checking input scope.

</details>

<span id="_4-what-is-the-key-difference-between-kubescape-operator-and-cli-modes"></span>

### 4. Which statement correctly distinguishes Operator and CLI operation?

- A) The Operator only provides a GUI
- B) CLI handles explicit/ad-hoc scans; the Operator runs enabled continuous/scheduled capabilities
- C) Installing the Operator proves all runtime features work
- D) CLI and Operator images always have the same version

<details>
<summary>Show Answer</summary>

**Answer: B) CLI handles explicit/ad-hoc scans; the Operator runs enabled continuous/scheduled capabilities**

Chart 1.40.4 renders scanner image 4.0.13, while the tested local CLI is 4.0.14. Node/image/runtime/remediation scope and permissions require separate choices and validation.

</details>

<span id="_5-how-does-kubescape-calculate-risk-scores-for-controls"></span>

### 5. How are score and complianceScore related?

- A) They are always equal
- B) They always sum to 100
- C) They are separate aggregates in the result schema
- D) Both are average CVSS values

<details>
<summary>Show Answer</summary>

**Answer: C) They are separate aggregates in the result schema**

The synthetic insecure Pod produced compliance 55 and score 62.5. Read summaryDetails.complianceScore and summaryDetails.score. These local values do not measure a real cluster’s security.

</details>

<span id="_6-which-flag-enforces-a-compliance-threshold-in-ci-cd-pipelines"></span>

### 6. What happens with compliance 55 and --compliance-threshold 56?

- A) It passes because this is a maximum-risk limit
- B) It exits 1 because minimum compliance is unmet
- C) It always exits 2
- D) It is equivalent to the current --fail-threshold 0 gate

<details>
<summary>Show Answer</summary>

**Answer: B) It exits 1 because minimum compliance is unmet**

The same fixture returned exit 0 at threshold 55 and exit 1 at 56. Version 4.0.14 accepts deprecated --fail-threshold but ignores its value; do not use it as a gate.

</details>

<span id="_7-how-does-kubescape-differ-from-kube-bench"></span>

### 7. What is a sound basis for comparing kube-bench and Kubescape?

- A) Assume one replaces every check based on its name
- B) Compare actual node/CIS versus workload/config scope and access
- C) Both can inspect every control-plane setting without access
- D) A Kubescape pass is a CIS certificate

<details>
<summary>Show Answer</summary>

**Answer: B) Compare actual node/CIS versus workload/config scope and access**

Managed EKS control planes, local manifests, and node-file access offer different visibility. Distinguish unavailable/unevaluated checks from passes and select tools accordingly.

</details>

<span id="_8-what-feature-does-kubescape-provide-for-rbac-security-analysis"></span>

### 8. Which statement about RBAC controls is correct?

- A) C-0036 always checks wildcard RBAC
- B) A RoleBinding grants access in all namespaces
- C) Verify current control IDs/names and collection scope
- D) scan rbac is a separate subcommand in the reviewed CLI

<details>
<summary>Show Answer</summary>

**Answer: C) Verify current control IDs/names and collection scope**

The reviewed bundle maps C-0035 to Administrative Roles and C-0036/0039 to validating/mutating admission checks. RoleBindings are namespaced; static analysis does not automatically validate external IAM.

</details>

<span id="_9-which-vulnerability-scanner-does-kubescape-integrate-with-for-image-scanning"></span>

### 9. Which statement correctly distinguishes image and host scans?

- A) Host scanning only checks image CVEs
- B) Explicit image scans need registry/DB access; host scans have a separate scope
- C) Grype only generates SBOMs
- D) Image/platform/database versions do not matter

<details>
<summary>Show Answer</summary>

**Answer: B) Explicit image scans need registry/DB access; host scans have a separate scope**

The CLI uses Grype and Syft; Operator kubevuln is separately versioned. Host scans can need additional resources/permissions. No image pulls or host scans were run in this audit.

</details>

<span id="_10-how-does-kubescape-handle-control-exceptions"></span>

### 10. What are the correct CLI and in-cluster exception formats?

- A) The CLI consumes an arbitrary ConfigMap directly
- B) Distinguish alertOnly in a CLI JSON array from alert_only in v1beta1 SecurityException
- C) Every ignore annotation is automatically an exception
- D) Recording an exception remediates the issue

<details>
<summary>Show Answer</summary>

**Answer: B) Distinguish alertOnly in a CLI JSON array from alert_only in v1beta1 SecurityException**

In the test, alertOnly acknowledged a failure without changing compliance. exclude-controls changes the evaluation denominator. Track ownership, scope, expiry, and re-review separately from remediation.

</details>

## Score Calculation

- 9–10: Strong understanding
- 7–8: Revisit missed scope/gate concepts
- 6 or fewer: Review the guide and tested examples

## Related Documentation

- [Kubescape](../../security/11-kubescape.md)
