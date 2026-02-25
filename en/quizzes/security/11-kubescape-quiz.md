# Kubescape Quiz

Test your understanding of Kubescape security posture management with the following questions.

---

## Questions

### 1. What is Kubescape's project status in the CNCF?

- A) Graduated project
- B) Incubating project
- C) Sandbox project
- D) Not a CNCF project

<details>
<summary>Show Answer</summary>

**Answer: C) Sandbox project**

**Explanation:**
Kubescape was accepted as a CNCF Sandbox project in 2022. It was originally developed by ARMO and donated to the CNCF. As a Sandbox project, it is an early-stage project that the CNCF believes has potential for growth.

</details>

---

### 2. Which security frameworks does Kubescape support for compliance scanning?

- A) NSA-CISA only
- B) CIS Benchmarks only
- C) NSA-CISA, CIS Benchmarks, and MITRE ATT&CK
- D) OWASP and PCI-DSS only

<details>
<summary>Show Answer</summary>

**Answer: C) NSA-CISA, CIS Benchmarks, and MITRE ATT&CK**

**Explanation:**
Kubescape supports multiple security frameworks:

```bash
# Scan with NSA-CISA framework
kubescape scan framework nsa

# Scan with CIS Kubernetes Benchmark
kubescape scan framework cis-v1.23-t1.0.1

# Scan with MITRE ATT&CK
kubescape scan framework mitre
```

- **NSA-CISA**: Kubernetes Hardening Guide from US government agencies
- **CIS**: Center for Internet Security Kubernetes Benchmarks
- **MITRE ATT&CK**: Threat-based security framework mapping attack techniques

</details>

---

### 3. What is the correct CLI syntax to scan a Kubernetes cluster with Kubescape?

- A) kubescape check cluster
- B) kubescape scan
- C) kubescape audit cluster
- D) kubescape analyze

<details>
<summary>Show Answer</summary>

**Answer: B) kubescape scan**

**Explanation:**
Kubescape CLI scan commands:

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

The `scan` subcommand is the primary interface for all scanning operations.

</details>

---

### 4. What is the key difference between Kubescape Operator and CLI modes?

- A) Operator mode only scans nodes
- B) CLI mode provides continuous monitoring, Operator is one-time
- C) Operator provides continuous monitoring with in-cluster components, CLI is one-time scans
- D) There is no difference

<details>
<summary>Show Answer</summary>

**Answer: C) Operator provides continuous monitoring with in-cluster components, CLI is one-time scans**

**Explanation:**
Kubescape deployment modes:

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
- Integration with ARMO platform for visualization

</details>

---

### 5. How does Kubescape calculate risk scores for controls?

- A) Binary pass/fail only
- B) Based on severity multiplied by affected resources count
- C) Random assignment
- D) Based on namespace priority

<details>
<summary>Show Answer</summary>

**Answer: B) Based on severity multiplied by affected resources count**

**Explanation:**
Kubescape risk scoring:

```
Risk Score = Severity Score x (Failed Resources / Total Resources)
```

Example output:
```
┌──────────────────────────────────────────────────┬────────────────┬───────┐
│ Control Name                                      │ Failed Resources│ Score │
├──────────────────────────────────────────────────┼────────────────┼───────┤
│ Privileged container                              │ 3/50           │ 18%   │
│ Resource limits                                   │ 25/50          │ 35%   │
│ Non-root containers                               │ 10/50          │ 42%   │
└──────────────────────────────────────────────────┴────────────────┴───────┘
```

Higher scores indicate greater risk requiring immediate attention.

</details>

---

### 6. Which flag enforces a compliance threshold in CI/CD pipelines?

- A) --min-score
- B) --compliance-threshold
- C) --fail-threshold
- D) --severity-threshold

<details>
<summary>Show Answer</summary>

**Answer: B) --compliance-threshold**

**Explanation:**
Using Kubescape in CI/CD pipelines:

```bash
# Fail pipeline if compliance drops below 80%
kubescape scan --compliance-threshold 80

# Example GitLab CI
kubescape-scan:
  script:
    - kubescape scan framework nsa --compliance-threshold 75
    - kubescape scan framework cis --compliance-threshold 80
```

The threshold is a percentage (0-100). The scan fails (non-zero exit) if the overall compliance score falls below the threshold.

```bash
# Exit codes
# 0: Passed threshold
# 1: Failed threshold
# 2: Error during scan
```

</details>

---

### 7. How does Kubescape differ from kube-bench?

- A) kube-bench only scans applications, Kubescape scans infrastructure
- B) Kubescape scans workload configurations, kube-bench focuses on node-level CIS benchmarks
- C) They are identical tools
- D) kube-bench is for cloud providers only

<details>
<summary>Show Answer</summary>

**Answer: B) Kubescape scans workload configurations, kube-bench focuses on node-level CIS benchmarks**

**Explanation:**
Kubescape vs kube-bench comparison:

| Feature | Kubescape | kube-bench |
|---------|-----------|------------|
| Focus | Workload/config security | Node/control plane security |
| Scope | Deployments, Pods, RBAC | kubelet, API server, etcd |
| Frameworks | NSA, CIS, MITRE | CIS Benchmarks only |
| Run Location | Outside cluster (CLI) or in-cluster | Must run on each node |
| Image Scanning | Yes (with Grype) | No |
| RBAC Analysis | Yes | No |

Use both together for comprehensive security:
- kube-bench: Cluster infrastructure hardening
- Kubescape: Workload and configuration security

</details>

---

### 8. What feature does Kubescape provide for RBAC security analysis?

- A) RBAC policy generation
- B) RBAC visualization showing permissions and risks
- C) Automatic RBAC remediation
- D) RBAC migration tools

<details>
<summary>Show Answer</summary>

**Answer: B) RBAC visualization showing permissions and risks**

**Explanation:**
Kubescape RBAC analysis capabilities:

```bash
# Scan RBAC configurations
kubescape scan control C-0035  # Cluster-admin binding
kubescape scan control C-0036  # Wildcard permissions
kubescape scan control C-0039  # Risky service accounts
```

RBAC visualization features:
- Maps ServiceAccounts to Roles/ClusterRoles
- Identifies overly permissive bindings
- Highlights dangerous permissions (secrets access, pod exec)
- Shows attack paths through RBAC

Example finding:
```
ServiceAccount 'default' in namespace 'production' has:
- Cluster-admin binding (CRITICAL)
- Secrets list/get permissions (HIGH)
- Pod exec permissions (HIGH)
```

</details>

---

### 9. Which vulnerability scanner does Kubescape integrate with for image scanning?

- A) Trivy
- B) Clair
- C) Grype
- D) Anchore

<details>
<summary>Show Answer</summary>

**Answer: C) Grype**

**Explanation:**
Kubescape integrates with Grype (by Anchore) for container image vulnerability scanning:

```bash
# Enable image scanning
kubescape scan --enable-host-scan

# Operator mode includes automatic image scanning
helm install kubescape kubescape/kubescape-operator \
  --set capabilities.vulnerabilityScan=enable
```

Grype integration provides:
- CVE detection in container images
- SBOM (Software Bill of Materials) generation
- Severity-based prioritization
- Integration with security findings

The results combine configuration issues with vulnerability data for comprehensive risk assessment.

</details>

---

### 10. How does Kubescape handle control exceptions?

- A) Exceptions are not supported
- B) Using exception YAML files that specify controls and resources to exclude
- C) Through command-line flags only
- D) By modifying source code

<details>
<summary>Show Answer</summary>

**Answer: B) Using exception YAML files that specify controls and resources to exclude**

**Explanation:**
Kubescape supports exceptions via configuration files:

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

Apply exceptions:
```bash
kubescape scan --exceptions exceptions.yaml
```

This allows:
- Suppressing known false positives
- Accepting risk for specific resources
- Maintaining clean scan reports

</details>

---

## Score Calculation

- **9-10 correct**: Excellent - You have a deep understanding of Kubescape.
- **7-8 correct**: Good - You have a solid grasp of the key concepts.
- **5-6 correct**: Fair - There are areas that need additional study.
- **4 or fewer**: Please review the documentation again.

## Related Documentation

- [Security Posture Management with Kubescape](../../security/11-kubescape.md)
