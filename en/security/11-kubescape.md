# Security Posture Management with Kubescape

> **Supported Versions**: Kubescape 3.0+, Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 25, 2026

Kubescape is an open-source Kubernetes security platform that provides comprehensive security posture management, vulnerability scanning, and compliance checking. As a CNCF Sandbox project, it helps organizations identify misconfigurations, vulnerabilities, and compliance violations across their Kubernetes environments.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Security Frameworks](#security-frameworks)
4. [CLI Scanning](#cli-scanning)
5. [Operator Mode (In-Cluster)](#operator-mode-in-cluster)
6. [Risk Scoring](#risk-scoring)
7. [CI/CD Integration](#cicd-integration)
8. [EKS-Specific Guide](#eks-specific-guide)
9. [Control Exception Handling](#control-exception-handling)
10. [Best Practices](#best-practices)
11. [Summary and References](#summary-and-references)

---

## Overview

### What Kubescape Solves

Kubescape addresses critical security challenges in Kubernetes environments:

- **Misconfiguration Detection**: Identifies security misconfigurations in workloads, RBAC, network policies, and cluster settings
- **Compliance Verification**: Validates clusters against industry frameworks (NSA-CISA, CIS, MITRE ATT&CK)
- **Vulnerability Scanning**: Detects vulnerabilities in container images and Kubernetes components
- **RBAC Analysis**: Visualizes and analyzes role-based access control configurations
- **Shift-Left Security**: Scans manifests and Helm charts before deployment

### CNCF Sandbox Project

Kubescape joined the CNCF Sandbox in 2022, demonstrating its commitment to open-source principles and community-driven development. The project is actively maintained by ARMO and the open-source community.

### Comparison with Similar Tools

| Feature | Kubescape | kube-bench | Polaris | Trivy |
|---------|-----------|------------|---------|-------|
| **CIS Benchmark** | Yes | Yes | No | Yes |
| **NSA-CISA Framework** | Yes | No | No | No |
| **MITRE ATT&CK** | Yes | No | No | No |
| **Image Scanning** | Yes | No | No | Yes |
| **RBAC Analysis** | Yes | No | No | No |
| **Helm/YAML Scanning** | Yes | No | Yes | Yes |
| **In-Cluster Operator** | Yes | Limited | Yes | Yes |
| **Risk Scoring** | Yes | No | Yes | Yes |
| **Custom Frameworks** | Yes | No | Yes | No |
| **CI/CD Integration** | Native | Manual | Native | Native |
| **Runtime Detection** | Yes (with Node Agent) | No | No | No |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 |

### Kubescape Architecture

![Kubescape architecture: CLI, Operator, and CI/CD scan requests pass through framework-based control evaluation, vulnerability scanning, and RBAC analysis into a Risk Calculator, whose report goes to JSON/SARIF, Kubescape Cloud, and alerts.](../.gitbook/assets/en-security-11-kubescape-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-0.html)

---

## Installation

### CLI Installation

#### Linux and macOS

```bash
# Using curl (recommended)
curl -s https://raw.githubusercontent.com/kubescape/kubescape/master/install.sh | /bin/bash

# Using Homebrew (macOS/Linux)
brew install kubescape

# Using Krew (kubectl plugin manager)
kubectl krew install kubescape

# Verify installation
kubescape version
```

#### Windows

```powershell
# Using PowerShell
iwr -useb https://raw.githubusercontent.com/kubescape/kubescape/master/install.ps1 | iex

# Using Chocolatey
choco install kubescape

# Using Scoop
scoop install kubescape
```

#### Container Image

```bash
# Run Kubescape as a container
docker run -v ~/.kube:/root/.kube quay.io/kubescape/kubescape:latest scan framework nsa

# With specific kubeconfig
docker run -v /path/to/kubeconfig:/root/.kube/config \
    quay.io/kubescape/kubescape:latest scan framework cis
```

### Helm Operator Installation (In-Cluster)

The Kubescape Operator provides continuous scanning and monitoring capabilities within your cluster.

```bash
# Add Kubescape Helm repository
helm repo add kubescape https://kubescape.github.io/helm-charts/
helm repo update

# Install Kubescape Operator with default settings
helm install kubescape kubescape/kubescape-operator \
    -n kubescape \
    --create-namespace

# Install with custom configuration
helm install kubescape kubescape/kubescape-operator \
    -n kubescape \
    --create-namespace \
    --set clusterName=my-eks-cluster \
    --set capabilities.continuousScan=enable \
    --set capabilities.vulnerabilityScan=enable \
    --set capabilities.nodeScan=enable \
    --set capabilities.runtimeDetection=enable
```

#### Operator Configuration Values

```yaml
# values.yaml
clusterName: "production-eks-cluster"

capabilities:
  continuousScan: enable
  vulnerabilityScan: enable
  nodeScan: enable
  runtimeDetection: enable
  networkPolicyService: enable

kubescape:
  serviceMonitor:
    enabled: true
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

storage:
  enabled: true
  storageClassName: gp3
  size: 10Gi

nodeAgent:
  enabled: true
  resources:
    requests:
      cpu: 50m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

gateway:
  enabled: true
  service:
    type: ClusterIP
```

### Kubescape Cloud (SaaS)

Kubescape Cloud provides a centralized dashboard for managing security across multiple clusters.

```bash
# Connect to Kubescape Cloud
kubescape scan framework nsa --account <ACCOUNT_ID> --submit

# Generate account ID
kubescape config set accountID <YOUR_ACCOUNT_ID>

# Verify cloud connectivity
kubescape config view
```

---

## Security Frameworks

Kubescape supports multiple security frameworks for comprehensive compliance checking.

### NSA-CISA Kubernetes Hardening Guide

The NSA-CISA framework provides security recommendations from the U.S. National Security Agency and Cybersecurity & Infrastructure Security Agency.

```bash
# Scan against NSA-CISA framework
kubescape scan framework nsa

# Scan specific namespaces
kubescape scan framework nsa --include-namespaces production,staging
```

Key control categories:
- Pod Security
- Network Separation
- Authentication and Authorization
- Audit Logging
- Upgrade and Patching

### CIS Kubernetes Benchmark

The Center for Internet Security (CIS) Benchmark provides prescriptive security configuration guidelines.

```bash
# Scan against CIS Benchmark
kubescape scan framework cis

# CIS v1.8 for Kubernetes 1.27+
kubescape scan framework cis-v1.8

# EKS-specific CIS benchmark
kubescape scan framework cis-eks
```

CIS Benchmark sections:
- Control Plane Components
- etcd Configuration
- Control Plane Configuration
- Worker Node Security
- Policies

### MITRE ATT&CK Framework

The MITRE ATT&CK framework maps security controls to known attack techniques.

```bash
# Scan against MITRE ATT&CK
kubescape scan framework mitre

# View specific attack techniques
kubescape scan framework mitre --verbose
```

Attack categories covered:
- Initial Access
- Execution
- Persistence
- Privilege Escalation
- Defense Evasion
- Credential Access
- Discovery
- Lateral Movement
- Impact

### Custom Frameworks

Create custom frameworks for organization-specific requirements.

```yaml
# custom-framework.yaml
name: "Organization Security Standards"
description: "Custom security framework for internal compliance"
controls:
  - controlID: C-0001
  - controlID: C-0002
  - controlID: C-0009
  - controlID: C-0034
  - controlID: C-0038
  - controlID: C-0041
  - controlID: C-0044
  - controlID: C-0055
  - controlID: C-0057
```

```bash
# Scan with custom framework
kubescape scan framework --custom-framework custom-framework.yaml

# List available controls
kubescape list controls
```

### Framework Comparison

| Framework | Focus Area | Controls | Best For |
|-----------|------------|----------|----------|
| **NSA-CISA** | Government hardening | 30+ | Federal/Government compliance |
| **CIS** | Configuration baseline | 100+ | General security baseline |
| **MITRE ATT&CK** | Threat mapping | 40+ | Threat modeling, red team |
| **CIS-EKS** | AWS EKS specific | 50+ | EKS deployments |
| **SOC2** | Compliance | 20+ | SOC 2 audits |
| **Custom** | Organization-specific | Variable | Internal standards |

---

## CLI Scanning

### Scanning Pipeline Flow

![Sequential workflow diagram showing a Kubescape scan traveling from the CLI through framework selection, resource collection, control checks, and severity assessment to risk scoring and report generation.](../.gitbook/assets/en-security-11-kubescape-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-1.html)

### Cluster Scanning

```bash
# Full cluster scan with NSA-CISA framework
kubescape scan framework nsa

# Scan with verbose output
kubescape scan framework nsa --verbose

# Scan specific namespaces
kubescape scan framework nsa \
    --include-namespaces production,staging \
    --exclude-namespaces kube-system,monitoring

# Scan with severity threshold
kubescape scan framework nsa --severity-threshold high

# Output to JSON
kubescape scan framework nsa --format json --output results.json

# Output to SARIF (for GitHub integration)
kubescape scan framework nsa --format sarif --output results.sarif

# Generate HTML report
kubescape scan framework nsa --format html --output report.html
```

### Specific Control Scanning

```bash
# List all available controls
kubescape list controls

# Scan for a specific control
kubescape scan control C-0034

# Scan multiple controls
kubescape scan control C-0034,C-0038,C-0041

# Get control details
kubescape describe control C-0034
```

Common security controls:

| Control ID | Name | Description |
|------------|------|-------------|
| C-0001 | Forbidden Container Registries | Detect images from untrusted registries |
| C-0002 | Exec into Container | Detect exec permissions |
| C-0009 | Resource Limits | Check for missing resource limits |
| C-0016 | Allow Privilege Escalation | Detect privilege escalation risk |
| C-0017 | Immutable Container Filesystem | Check for read-only root filesystem |
| C-0034 | Automatic Mapping of SA | Detect automatic service account mounting |
| C-0038 | Host PID/IPC Privileges | Detect host namespace sharing |
| C-0041 | HostNetwork Access | Detect host network usage |
| C-0044 | Container Hostport | Detect hostPort usage |
| C-0046 | Insecure Capabilities | Detect dangerous capabilities |
| C-0055 | Linux Hardening | Check seccomp/AppArmor profiles |
| C-0057 | Privileged Container | Detect privileged containers |

### YAML and Helm Manifest Scanning (Shift-Left)

Scan manifests before deployment to catch issues early.

```bash
# Scan YAML files
kubescape scan *.yaml

# Scan a directory
kubescape scan ./manifests/

# Scan Helm chart
kubescape scan ./my-chart/

# Scan Helm chart with values
kubescape scan ./my-chart/ --helm-set key=value

# Scan from URL
kubescape scan https://raw.githubusercontent.com/org/repo/main/deployment.yaml

# Scan with specific framework
kubescape scan framework nsa ./manifests/

# Fail on high severity findings
kubescape scan ./manifests/ --severity-threshold high --fail-threshold 0
```

Example manifest scan output:

```
Controls: 25 (Failed: 3, Excluded: 0, Skipped: 0)
Failed Resources: 5
Compliance Score: 88%

┌──────────────┬────────────────────────────────────────┬──────────────┬────────┐
│ SEVERITY     │ CONTROL NAME                           │ FAILED       │ STATUS │
├──────────────┼────────────────────────────────────────┼──────────────┼────────┤
│ High         │ Privileged container                   │ 1            │ failed │
│ High         │ Allow privilege escalation             │ 2            │ failed │
│ Medium       │ Resource limits                        │ 2            │ failed │
└──────────────┴────────────────────────────────────────┴──────────────┴────────┘
```

### Image Vulnerability Scanning

```bash
# Scan a specific image
kubescape scan image nginx:latest

# Scan all images in cluster
kubescape scan image --cluster

# Scan images in specific namespace
kubescape scan image --namespace production

# Filter by severity
kubescape scan image nginx:latest --severity critical,high

# Output vulnerabilities as JSON
kubescape scan image nginx:latest --format json --output vulns.json
```

Example vulnerability output:

```
Image: nginx:1.21.0
Vulnerabilities Found: 12 (Critical: 2, High: 4, Medium: 6)

┌─────────────────┬──────────────┬──────────┬─────────────────────────────────┐
│ CVE             │ SEVERITY     │ PACKAGE  │ FIX VERSION                     │
├─────────────────┼──────────────┼──────────┼─────────────────────────────────┤
│ CVE-2023-44487  │ Critical     │ openssl  │ 1.1.1w                          │
│ CVE-2023-38545  │ Critical     │ curl     │ 8.4.0                           │
│ CVE-2023-4911   │ High         │ glibc    │ 2.38-1                          │
└─────────────────┴──────────────┴──────────┴─────────────────────────────────┘

Recommendation: Update to nginx:1.25.3 or later
```

### RBAC Visualization and Analysis

```bash
# Scan RBAC configuration
kubescape scan rbac

# Analyze specific service account
kubescape scan rbac --service-account default:default

# Analyze specific user
kubescape scan rbac --user admin@example.com

# List subjects with cluster-admin equivalent
kubescape scan rbac --list-cluster-admins

# Export RBAC graph
kubescape scan rbac --format json --output rbac.json
```

RBAC analysis capabilities:
- Identify over-privileged service accounts
- Detect cluster-admin equivalent permissions
- Visualize role bindings and their scope
- Find unused roles and bindings
- Highlight risky permission combinations

---

## Operator Mode (In-Cluster)

### Continuous Scanning Architecture

![Inside the cluster a CronJob triggers the Operator Controller, which runs the Configuration, Vulnerability and RBAC scanners against Deployments, Pods, Services, Secrets and ServiceAccounts while Node Agent eBPF events also flow into the Controller. The Controller stores scan results as CRDs and compares them with the Baseline; results are published to Kubescape Cloud and detected changes go to external Alerting and SIEM/SOAR.](../.gitbook/assets/en-security-11-kubescape-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-2.html)

### Operator Components

```bash
# Verify operator installation
kubectl get pods -n kubescape

# Expected output:
# NAME                                    READY   STATUS    RESTARTS   AGE
# kubescape-operator-7d8f9c6b4d-x2h8k    1/1     Running   0          2h
# kubescape-storage-6b9d4f5c8a-m3n7p     1/1     Running   0          2h
# kubescape-gateway-5c7e8d9f6b-q4w2r     1/1     Running   0          2h
# node-agent-abcd1                        1/1     Running   0          2h
# node-agent-efgh2                        1/1     Running   0          2h

# Check CRDs
kubectl get crd | grep kubescape
```

### Scheduled Scanning Configuration

```yaml
# scanning-schedule.yaml
apiVersion: kubescape.io/v1alpha1
kind: ScanSchedule
metadata:
  name: daily-compliance-scan
  namespace: kubescape
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  scanType: framework
  framework: nsa
  namespaces:
    include:
      - production
      - staging
    exclude:
      - kube-system
  severityThreshold: medium
  notifications:
    slack:
      enabled: true
      channel: "#security-alerts"
    email:
      enabled: true
      recipients:
        - security-team@example.com
```

```bash
# Apply scanning schedule
kubectl apply -f scanning-schedule.yaml

# View scan results
kubectl get vulnerabilitymanifests -n kubescape
kubectl get configurationscans -n kubescape
```

### Vulnerability Scanning Integration

```yaml
# vulnerability-scan-config.yaml
apiVersion: kubescape.io/v1alpha1
kind: VulnerabilityScanConfig
metadata:
  name: image-scanning
  namespace: kubescape
spec:
  enabled: true
  scanNewImages: true
  scanInterval: "24h"
  registries:
    - url: "123456789012.dkr.ecr.us-west-2.amazonaws.com"
      credentials:
        secretRef: ecr-credentials
  severityThreshold: high
  ignoredCVEs:
    - CVE-2023-12345  # Known false positive
```

### Runtime Threat Detection (Node Agent with eBPF)

The Node Agent uses eBPF for low-overhead runtime monitoring.

```yaml
# node-agent configuration
nodeAgent:
  enabled: true

  config:
    applicationProfile:
      enabled: true
      interval: "1m"

    networkPolicy:
      enabled: true

    runtimeDetection:
      enabled: true
      rules:
        - name: "Crypto Mining Detection"
          enabled: true
        - name: "Reverse Shell Detection"
          enabled: true
        - name: "Privilege Escalation"
          enabled: true
        - name: "Container Escape"
          enabled: true

    alertThreshold: warning
```

Runtime detection capabilities:
- Process execution anomalies
- File system access monitoring
- Network connection tracking
- Capability usage detection
- Syscall monitoring

### Kubernetes API Attack Detection

```yaml
# api-threat-detection.yaml
apiVersion: kubescape.io/v1alpha1
kind: ThreatDetectionConfig
metadata:
  name: api-monitoring
  namespace: kubescape
spec:
  apiServer:
    enabled: true
    detectionRules:
      - name: "Suspicious kubectl exec"
        severity: high
        pattern:
          verb: create
          resource: pods/exec

      - name: "Secret Enumeration"
        severity: medium
        pattern:
          verb: list
          resource: secrets

      - name: "RBAC Modification"
        severity: high
        pattern:
          verb: ["create", "update", "patch", "delete"]
          resource: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]

      - name: "Service Account Token Access"
        severity: medium
        pattern:
          verb: create
          resource: serviceaccounts/token
```

---

## Risk Scoring

### Risk Score Calculation

Kubescape calculates risk scores based on multiple factors:

```
Risk Score = Σ (Control Severity × Resource Count × Exposure Factor)
           ─────────────────────────────────────────────────────────
                          Total Controls × Max Severity
```

Components:
- **Control Severity**: Critical (10), High (7), Medium (4), Low (1)
- **Resource Count**: Number of affected resources
- **Exposure Factor**: Network exposure, privilege level, data sensitivity

### Severity Levels

| Level | Score Range | Description | Action Required |
|-------|-------------|-------------|-----------------|
| **Critical** | 9-10 | Immediate exploitation risk | Immediate remediation |
| **High** | 7-8 | Significant security risk | Remediate within 24 hours |
| **Medium** | 4-6 | Moderate security concern | Remediate within 7 days |
| **Low** | 1-3 | Minor security improvement | Remediate within 30 days |
| **Negligible** | 0 | Informational | No action required |

### Viewing Risk Scores

```bash
# Scan with detailed risk scoring
kubescape scan framework nsa --verbose

# Get risk score summary
kubescape scan framework nsa --format json | jq '.riskScore'

# Sort results by risk score
kubescape scan framework nsa --format pretty-printer
```

Example risk score output:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Risk Assessment Summary                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Overall Risk Score: 34/100                                                 │
│  Compliance Score: 76%                                                      │
│                                                                             │
│  ┌─────────────┬──────────┬───────────────────────────────────────────┐   │
│  │ Severity    │ Controls │ Progress                                  │   │
│  ├─────────────┼──────────┼───────────────────────────────────────────┤   │
│  │ Critical    │ 0/2      │ ████████████████████ 100%                │   │
│  │ High        │ 3/8      │ ██████████████░░░░░░ 62%                 │   │
│  │ Medium      │ 5/15     │ ████████████████░░░░ 67%                 │   │
│  │ Low         │ 2/10     │ ████████████████████ 80%                 │   │
│  └─────────────┴──────────┴───────────────────────────────────────────┘   │
│                                                                             │
│  Top 5 Risks:                                                               │
│  1. Privileged containers in production (Score: 9.2)                        │
│  2. Missing network policies (Score: 7.8)                                   │
│  3. Containers with CAP_SYS_ADMIN (Score: 7.5)                             │
│  4. Service accounts with cluster-admin (Score: 6.9)                        │
│  5. Images from untrusted registries (Score: 6.2)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Prioritization Strategy

```bash
# Focus on critical and high severity first
kubescape scan framework nsa --severity-threshold high

# Get prioritized remediation list
kubescape scan framework nsa --format json | \
    jq '[.results[].controls[] | select(.status == "failed")] |
        sort_by(.severity) | reverse'
```

---

## CI/CD Integration

### CI/CD Integration Workflow

![Kubescape CI/CD integration workflow: a code change and Git commit fire the CI trigger, then the image build and a Kubescape scan (framework nsa, mitre); the security gate's gate check compares the risk score with the threshold — at or below it the run passes and deploys to the cluster, above it the run fails, deployment is blocked (exit 1), and a PR comment or alert is sent.](../.gitbook/assets/en-security-11-kubescape-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-3.html)

### GitHub Actions Workflow

```yaml
# .github/workflows/security-scan.yaml
name: Kubernetes Security Scan

on:
  push:
    branches: [main, develop]
    paths:
      - 'k8s/**'
      - 'helm/**'
  pull_request:
    branches: [main]
    paths:
      - 'k8s/**'
      - 'helm/**'

jobs:
  kubescape-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install Kubescape
        run: |
          curl -s https://raw.githubusercontent.com/kubescape/kubescape/master/install.sh | /bin/bash

      - name: Scan Kubernetes manifests
        id: scan
        run: |
          kubescape scan framework nsa ./k8s/ \
            --format sarif \
            --output results.sarif \
            --severity-threshold high \
            --compliance-threshold 75

      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: results.sarif

      - name: Scan Helm charts
        run: |
          kubescape scan framework cis ./helm/my-app/ \
            --format json \
            --output helm-results.json

      - name: Check compliance score
        run: |
          SCORE=$(cat helm-results.json | jq -r '.complianceScore')
          echo "Compliance Score: $SCORE%"
          if [ $(echo "$SCORE < 75" | bc) -eq 1 ]; then
            echo "Compliance score below threshold!"
            exit 1
          fi

      - name: Upload scan artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: kubescape-results
          path: |
            results.sarif
            helm-results.json

  image-scan:
    runs-on: ubuntu-latest
    needs: kubescape-scan
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install Kubescape
        run: |
          curl -s https://raw.githubusercontent.com/kubescape/kubescape/master/install.sh | /bin/bash

      - name: Scan container images
        run: |
          # Extract image names from manifests
          IMAGES=$(grep -r "image:" ./k8s/ | awk '{print $2}' | sort -u)

          for IMAGE in $IMAGES; do
            echo "Scanning: $IMAGE"
            kubescape scan image "$IMAGE" \
              --format json \
              --output "image-scan-$(echo $IMAGE | tr '/:' '-').json" \
              --severity critical,high || true
          done

      - name: Check for critical vulnerabilities
        run: |
          CRITICAL=$(find . -name "image-scan-*.json" -exec cat {} \; | \
            jq -s '[.[].vulnerabilities[] | select(.severity == "Critical")] | length')

          if [ "$CRITICAL" -gt 0 ]; then
            echo "Critical vulnerabilities found: $CRITICAL"
            exit 1
          fi
```

### GitLab CI/CD Integration

```yaml
# .gitlab-ci.yml
stages:
  - security-scan
  - deploy

variables:
  KUBESCAPE_VERSION: "latest"
  COMPLIANCE_THRESHOLD: 75
  SEVERITY_THRESHOLD: "high"

kubescape-scan:
  stage: security-scan
  image: quay.io/kubescape/kubescape:${KUBESCAPE_VERSION}
  script:
    - kubescape scan framework nsa ./manifests/
        --format json
        --output gl-security-report.json
        --severity-threshold ${SEVERITY_THRESHOLD}
    - |
      SCORE=$(cat gl-security-report.json | jq -r '.complianceScore')
      echo "Compliance Score: $SCORE%"
      if [ $(echo "$SCORE < ${COMPLIANCE_THRESHOLD}" | bc) -eq 1 ]; then
        echo "Security scan failed: compliance below threshold"
        exit 1
      fi
  artifacts:
    reports:
      sast: gl-security-report.json
    paths:
      - gl-security-report.json
    when: always
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### Jenkins Pipeline Integration

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        KUBESCAPE_ACCOUNT = credentials('kubescape-account-id')
    }

    stages {
        stage('Install Kubescape') {
            steps {
                sh '''
                    curl -s https://raw.githubusercontent.com/kubescape/kubescape/master/install.sh | /bin/bash
                '''
            }
        }

        stage('Security Scan') {
            steps {
                sh '''
                    kubescape scan framework nsa ./k8s/ \
                        --format json \
                        --output kubescape-results.json \
                        --severity-threshold high \
                        --account ${KUBESCAPE_ACCOUNT} \
                        --submit
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'kubescape-results.json'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'kubescape-results.html',
                        reportName: 'Kubescape Security Report'
                    ])
                }
            }
        }

        stage('Gate Check') {
            steps {
                script {
                    def results = readJSON file: 'kubescape-results.json'
                    def score = results.complianceScore

                    if (score < 75) {
                        error "Security compliance score (${score}%) below threshold (75%)"
                    }
                    echo "Security scan passed with score: ${score}%"
                }
            }
        }
    }
}
```

### Threshold-Based Gates

```bash
# Set compliance threshold
kubescape scan framework nsa ./manifests/ \
    --compliance-threshold 80 \
    --fail-threshold 5

# Fail on any high/critical findings
kubescape scan framework nsa ./manifests/ \
    --severity-threshold high \
    --fail-threshold 0

# Custom exit codes
kubescape scan framework nsa ./manifests/ \
    --format json \
    --output results.json

# Check results and set exit code
CRITICAL=$(jq '[.results[].controls[] | select(.status == "failed" and .severity == "Critical")] | length' results.json)
HIGH=$(jq '[.results[].controls[] | select(.status == "failed" and .severity == "High")] | length' results.json)

if [ "$CRITICAL" -gt 0 ]; then
    echo "Critical findings: $CRITICAL"
    exit 2
elif [ "$HIGH" -gt 3 ]; then
    echo "Too many high findings: $HIGH"
    exit 1
fi
```

---

## EKS-Specific Guide

### EKS-Specific Controls

```bash
# Scan with EKS-specific CIS benchmark
kubescape scan framework cis-eks

# Scan for EKS-specific controls
kubescape scan control \
    C-0001,C-0034,C-0035,C-0036,C-0037 \
    --verbose
```

### aws-auth ConfigMap Analysis

```bash
# Analyze aws-auth ConfigMap permissions
kubectl get configmap aws-auth -n kube-system -o yaml

# Kubescape RBAC scan includes aws-auth analysis
kubescape scan rbac --verbose | grep -A 20 "aws-auth"
```

Common aws-auth issues:
- Overly permissive mapRoles entries
- Direct root account mappings
- Missing group restrictions

Example secure aws-auth configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSNodeRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
    - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
      username: eks-admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/EKSDeveloperRole
      username: eks-developer
      groups:
        - eks-developers  # Custom group with limited permissions
```

### IRSA (IAM Roles for Service Accounts) Validation

```bash
# Check service accounts with IRSA annotations
kubectl get sa -A -o json | jq '.items[] |
    select(.metadata.annotations["eks.amazonaws.com/role-arn"] != null) |
    {namespace: .metadata.namespace, name: .metadata.name, role: .metadata.annotations["eks.amazonaws.com/role-arn"]}'

# Kubescape validates IRSA configuration
kubescape scan control C-0034 --verbose  # Automatic SA token mounting
```

IRSA security checklist:
- Disable automatic service account token mounting when not needed
- Use dedicated service accounts per workload
- Apply least-privilege IAM policies
- Enable OIDC provider conditions in IAM trust policies

```yaml
# Secure IRSA service account configuration
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/MyAppRole
automountServiceAccountToken: false  # Disable unless needed
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
spec:
  template:
    spec:
      serviceAccountName: my-app
      automountServiceAccountToken: true  # Enable only where needed
      containers:
        - name: app
          image: my-app:latest
```

### EKS Security Best Practices Scan

```bash
# Comprehensive EKS security scan
kubescape scan framework nsa,cis-eks \
    --verbose \
    --format json \
    --output eks-security-report.json

# Check for EKS-specific misconfigurations
kubescape scan control \
    C-0001 \  # Container registries
    C-0002 \  # Exec permissions
    C-0034 \  # SA token mounting
    C-0035 \  # Cluster admin binding
    C-0038 \  # Host namespaces
    C-0041 \  # Host network
    C-0044 \  # Host ports
    C-0046 \  # Insecure capabilities
    C-0055 \  # Linux hardening
    C-0057    # Privileged containers
```

---

## Control Exception Handling

### Exception Policies

Create exceptions for known acceptable risks or false positives.

```yaml
# exceptions.yaml
apiVersion: kubescape.io/v1alpha1
kind: ControlException
metadata:
  name: allow-privileged-monitoring
  namespace: kubescape
spec:
  controlID: C-0057  # Privileged Container
  resources:
    - namespace: monitoring
      kind: DaemonSet
      name: node-exporter
    - namespace: monitoring
      kind: DaemonSet
      name: fluent-bit
  reason: "Required for host metrics collection"
  approvedBy: "security-team@example.com"
  expiresAt: "2027-02-25T00:00:00Z"
---
apiVersion: kubescape.io/v1alpha1
kind: ControlException
metadata:
  name: allow-hostnetwork-ingress
  namespace: kubescape
spec:
  controlID: C-0041  # HostNetwork access
  resources:
    - namespace: ingress-nginx
      kind: DaemonSet
      name: ingress-nginx-controller
  reason: "Ingress controller requires host network for port 80/443"
  approvedBy: "platform-team@example.com"
  expiresAt: "2027-02-25T00:00:00Z"
```

### Applying Exceptions via CLI

```bash
# Apply exceptions file
kubescape scan framework nsa --exceptions exceptions.yaml

# Exclude specific namespaces
kubescape scan framework nsa \
    --exclude-namespaces kube-system,monitoring,ingress-nginx

# Exclude by label
kubescape scan framework nsa \
    --exclude-label "kubescape.io/ignore=true"

# Skip specific controls
kubescape scan framework nsa \
    --skip-controls C-0057,C-0041
```

### Accepted Risks Documentation

```yaml
# accepted-risks.yaml
apiVersion: kubescape.io/v1alpha1
kind: AcceptedRisk
metadata:
  name: legacy-app-privileges
  namespace: kubescape
spec:
  description: "Legacy application requires elevated privileges pending migration"

  affectedControls:
    - controlID: C-0057
      severity: high
      justification: "Application binary requires CAP_NET_ADMIN for network management"
    - controlID: C-0016
      severity: high
      justification: "Required for privilege escalation within container"

  affectedResources:
    - namespace: legacy
      kind: Deployment
      name: legacy-network-app

  mitigations:
    - "Network policies restrict communication to essential services only"
    - "Pod security context limits other capabilities"
    - "Runtime monitoring enabled via Falco"

  riskOwner: "legacy-team@example.com"
  approvedBy: "ciso@example.com"
  approvalDate: "2026-02-01"
  reviewDate: "2026-08-01"
  status: "accepted"
```

### Inline Resource Exceptions

```yaml
# Annotate resources to skip specific controls
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  annotations:
    kubescape.io/ignore: "true"  # Skip all controls
    kubescape.io/ignore-controls: "C-0057,C-0038"  # Skip specific controls
    kubescape.io/exception-reason: "Required for host metrics collection"
spec:
  template:
    spec:
      containers:
        - name: node-exporter
          image: prom/node-exporter:latest
          securityContext:
            privileged: true  # Required for host access
```

---

## Best Practices

### Periodic Scanning Schedule

| Environment | Framework | Frequency | Threshold |
|-------------|-----------|-----------|-----------|
| Production | NSA-CISA + CIS | Daily | Critical: 0, High: 0 |
| Staging | NSA-CISA | Daily | Critical: 0, High: 5 |
| Development | Custom (core controls) | Weekly | Critical: 0 |
| Pre-production | Full (all frameworks) | Per deployment | Critical: 0, High: 0 |
| CI/CD | NSA-CISA | Per commit | Critical: 0 |

### Scanning Configuration

```yaml
# production-scan-config.yaml
apiVersion: kubescape.io/v1alpha1
kind: ScanConfiguration
metadata:
  name: production-compliance
spec:
  frameworks:
    - nsa
    - cis

  schedule:
    continuous:
      enabled: true
      interval: "1h"
    full:
      enabled: true
      cron: "0 2 * * *"

  namespaces:
    include:
      - production
      - production-*
    exclude:
      - kube-system

  thresholds:
    compliance: 90
    severities:
      critical: 0
      high: 0
      medium: 10

  notifications:
    onFailure:
      slack:
        channel: "#security-alerts"
        priority: immediate
      pagerduty:
        enabled: true
    onSuccess:
      slack:
        channel: "#security-daily"
        priority: low
```

### Compliance Reporting

```bash
# Generate compliance report
kubescape scan framework nsa,cis \
    --format html \
    --output compliance-report-$(date +%Y%m%d).html

# Generate executive summary
kubescape scan framework nsa \
    --format json \
    --output results.json

# Extract key metrics
jq '{
  date: now | strftime("%Y-%m-%d"),
  overallScore: .complianceScore,
  criticalFindings: [.results[].controls[] | select(.status == "failed" and .severity == "Critical")] | length,
  highFindings: [.results[].controls[] | select(.status == "failed" and .severity == "High")] | length,
  totalControls: .results[].controls | length,
  passedControls: [.results[].controls[] | select(.status == "passed")] | length
}' results.json > executive-summary.json
```

### Remediation Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Remediation Workflow                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Scan & Identify                                                         │
│     └─▶ kubescape scan framework nsa --format json --output findings.json  │
│                                                                             │
│  2. Prioritize by Risk                                                      │
│     └─▶ Sort findings by severity and exposure                             │
│     └─▶ Critical → High → Medium → Low                                     │
│                                                                             │
│  3. Assign & Track                                                          │
│     └─▶ Create tickets for each finding                                    │
│     └─▶ Assign to appropriate team                                         │
│     └─▶ Set SLA based on severity                                          │
│                                                                             │
│  4. Remediate                                                               │
│     └─▶ Apply fixes to manifests                                           │
│     └─▶ Validate in dev/staging                                            │
│     └─▶ Deploy to production                                               │
│                                                                             │
│  5. Verify                                                                  │
│     └─▶ Re-scan to confirm remediation                                     │
│     └─▶ Update ticket status                                               │
│     └─▶ Document exceptions if needed                                      │
│                                                                             │
│  6. Monitor                                                                 │
│     └─▶ Set up alerts for regression                                       │
│     └─▶ Track compliance trends                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Integration with Other Security Tools

```yaml
# Multi-tool security pipeline
apiVersion: batch/v1
kind: CronJob
metadata:
  name: security-scan-pipeline
  namespace: security
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            # Kubescape for configuration scanning
            - name: kubescape
              image: quay.io/kubescape/kubescape:latest
              command:
                - /bin/sh
                - -c
                - |
                  kubescape scan framework nsa,cis \
                    --format json \
                    --output /reports/kubescape-$(date +%Y%m%d).json \
                    --submit
              volumeMounts:
                - name: reports
                  mountPath: /reports

            # Trivy for image scanning
            - name: trivy
              image: aquasec/trivy:latest
              command:
                - /bin/sh
                - -c
                - |
                  trivy k8s --report summary \
                    --output /reports/trivy-$(date +%Y%m%d).json \
                    --format json
              volumeMounts:
                - name: reports
                  mountPath: /reports

          volumes:
            - name: reports
              persistentVolumeClaim:
                claimName: security-reports
          restartPolicy: OnFailure
```

### Prometheus Metrics Integration

```yaml
# ServiceMonitor for Kubescape metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kubescape
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: kubescape
  endpoints:
    - port: metrics
      interval: 60s
      path: /metrics
```

Key metrics to monitor:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `kubescape_compliance_score` | Overall compliance percentage | < 80% |
| `kubescape_critical_findings` | Number of critical findings | > 0 |
| `kubescape_high_findings` | Number of high findings | > 5 |
| `kubescape_scan_duration_seconds` | Scan execution time | > 600 |
| `kubescape_last_scan_timestamp` | Last successful scan time | > 24h ago |

---

## Summary and References

### Key Takeaways

1. **Multi-Framework Support**: Kubescape supports NSA-CISA, CIS, MITRE ATT&CK, and custom frameworks for comprehensive compliance coverage.

2. **Shift-Left Security**: Scan manifests and Helm charts in CI/CD pipelines before deployment to catch issues early.

3. **Continuous Monitoring**: Deploy the operator for ongoing security posture monitoring with scheduled scans.

4. **Risk-Based Prioritization**: Use risk scoring to prioritize remediation efforts on the most impactful findings.

5. **Exception Management**: Document and track accepted risks with proper approval workflows.

6. **EKS Integration**: Leverage EKS-specific controls and IRSA validation for AWS deployments.

### Quick Reference Commands

```bash
# Basic cluster scan
kubescape scan framework nsa

# Scan with multiple frameworks
kubescape scan framework nsa,cis,mitre

# Scan manifests before deployment
kubescape scan ./manifests/

# Image vulnerability scan
kubescape scan image nginx:latest

# RBAC analysis
kubescape scan rbac

# CI/CD integration (fail on high severity)
kubescape scan framework nsa \
    --severity-threshold high \
    --compliance-threshold 80 \
    --format sarif \
    --output results.sarif

# Generate HTML report
kubescape scan framework nsa --format html --output report.html
```

### References

- [Kubescape Official Documentation](https://kubescape.io/docs/)
- [Kubescape GitHub Repository](https://github.com/kubescape/kubescape)
- [NSA-CISA Kubernetes Hardening Guide](https://media.defense.gov/2022/Aug/29/2003066362/-1/-1/0/CTR_KUBERNETES_HARDENING_GUIDANCE_1.2_20220829.PDF)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [MITRE ATT&CK for Containers](https://attack.mitre.org/matrices/enterprise/containers/)
- [Kubescape Cloud Platform](https://cloud.armosec.io/)
- [CNCF Sandbox Projects](https://www.cncf.io/sandbox-projects/)

---

## Related Documentation

- [Kyverno Policy Management](./01-kyverno-policy-management.md)
- [Pod Security Standards](./03-pod-security-standards.md)
- [EKS Security Best Practices](./06-eks-security-best-practices.md)
- [Image Security](./07-image-security.md)
- [Runtime Security](./08-runtime-security.md)
- [OPA Gatekeeper](./09-opa-gatekeeper.md)
