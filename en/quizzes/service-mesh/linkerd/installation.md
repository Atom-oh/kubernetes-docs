# Linkerd Installation Quiz

Reviewed September 11, 2026 against edge-26.9.1 and charts 2026.9.1. See the [installation guide](../../../service-mesh/linkerd/01-installation.md) for complete prerequisites and validation boundaries.

### 1. How should you obtain the exact public CLI used in this guide?

A. Assume any package named linkerd is the same version

B. Select the official edge-26.9.1 asset for the OS/architecture, verify its checksum and client version

C. Use kubectl install linkerd

D. Pass --version stable-2.16.0 to an installer that does not parse that flag

<details>
<summary>Answer and explanation</summary>

**Answer: B**

The guide pins an official release asset. The installer alternative uses LINKERD2_VERSION, and the old install script is deprecated and now defaults to edge. Stable distributions use vendor guidance. Windows has a windows.exe release asset; do not invent a windows-amd64.exe filename.

</details>

### 2. Which command is the new-install preflight?

A. linkerd check

B. linkerd check --pre

C. linkerd verify

D. linkerd install --dry-run

<details>
<summary>Answer and explanation</summary>

**Answer: B**

check --pre checks API access, minimum Kubernetes version, Gateway API prerequisites and installation permissions/setup. It is not proof of compatibility with every later Kubernetes version. Review the exact version matrix and use the CNI-aware flag if that installation path is selected.

</details>

### 3. What identity material does the manual Helm path require?

A. An Envoy image

B. The public trust anchor and issuer certificate/private key, or a supported configured issuer-secret integration

C. The root CA private key in every proxy Pod

D. A Prometheus configuration file

<details>
<summary>Answer and explanation</summary>

**Answer: B**

The control-plane Helm chart does not generate the workload identity CA material for this path. Provide the public trust anchor and the issuer signing credential. Keep the root private key outside Kubernetes. External issuer-secret integrations need their corresponding scheme/owner configuration.

</details>

### 4. How many replicas does the packaged HA profile select for critical control-plane components?

A. 1

B. 2

C. 3

D. 5

<details>
<summary>Answer and explanation</summary>

**Answer: C**

The packaged profile selects three critical-component replicas with node anti-affinity, PDBs and a Fail injection-webhook policy. These are redundant serving instances, not quorum voters. Sufficient eligible nodes, resources and working credentials/network paths are still required; replica count alone does not guarantee availability.

</details>

### 5. Which is not a main Viz feature?

A. Web dashboard

B. Prometheus-based metrics

C. Automatic canary promotion

D. HTTP traffic tap

<details>
<summary>Answer and explanation</summary>

**Answer: C**

Viz provides metrics/dashboard/tap functions. Canary progression needs a separate delivery controller and analysis policy. The current Viz chart offers links to an external Grafana; grafana.enabled does not deploy or disable a bundled Grafana.

</details>

### 6. Which AWS load balancer can preserve the gateway’s raw TCP transport without terminating Linkerd mTLS?

A. An ALB HTTP listener

B. A dashboard Ingress resource

C. An NLB TCP listener

D. A Gateway Load Balancer GENEVE appliance path

<details>
<summary>Answer and explanation</summary>

**Answer: C**

Use TCP passthrough for the Linkerd gateway transport. NLB internal versus internet-facing is a scheme choice governed by network requirements, not a separate load balancer product. The guide’s internal NLB example assumes AWS Load Balancer Controller ownership and reachable remote networks/probe paths.

</details>

### 7. Which upgrade ordering matches the documented workflow?

A. Data plane, then control plane and CRDs

B. Target CLI, CRDs, control plane, installed extensions, then data plane

C. CRDs, data plane, then control plane

D. Delete the CA, then install everything again

<details>
<summary>Answer and explanation</summary>

**Answer: B**

Review target compatibility/release notes and current health first. Preserve trust credentials, update through each resource owner, then recreate the intended application Pods to receive the new proxy. CLI extensions render updates with install; viz upgrade is not a subcommand. Observe supported skew and inspect prune output before deleting resources.

</details>

### 8. What does linkerd install --crds itself do?

A. Installs the CLI binary

B. Generates Linkerd CRD manifests

C. Applies all cluster resources immediately

D. Injects every existing application Pod

<details>
<summary>Answer and explanation</summary>

**Answer: B**

The command outputs manifests. kubectl apply or the chosen deployment owner performs installation. Gateway API prerequisites are separate from the default Linkerd CRD output, and the control plane is installed afterwards.

</details>

### 9. Which tracing approach applies to edge-26.9.1?

A. Run linkerd jaeger install because every extension still ships in the CLI

B. Configure a supported collector/backend and proxy tracing with application context propagation

C. Install Viz and assume it stores every distributed trace

D. Ignore trace headers because proxies can reconstruct all application spans

<details>
<summary>Answer and explanation</summary>

**Answer: B**

This CLI has no jaeger subcommand, and the public linkerd-jaeger chart history is older than the selected release. Use the current tracing data path and verify receiver/export compatibility. Metrics/topology graphs are not equivalent to collected distributed traces.

</details>

### 10. What must a complete removal plan do first?

A. Delete the CRDs while applications remain injected

B. Remove application injection/manual proxies and verify recreated workloads before extensions and the control plane

C. Delete every namespace immediately

D. Force uninstall to ignore remaining injected workloads

<details>
<summary>Answer and explanation</summary>

**Answer: B**

Remove all injection sources through workload owners, recreate and verify the application Pods, then remove installed extensions and the control plane/CRDs through their respective owners. CRD deletion removes its custom resources. Review CNI cleanup and namespace ownership separately, including the loss of mesh security/routing.

</details>

### 11. What does linkerd check not validate?

A. Kubernetes API access

B. Control-plane certificate validity

C. Application business logic

D. Control-plane Pod health

<details>
<summary>Answer and explanation</summary>

**Answer: C**

Core health checks do not validate business outcomes or every traffic/security path. check --proxy adds the relevant data-plane checks; installed extensions have their own checks. Keep application tests and real traffic verification separate.

</details>

### 12. Which namespace annotation requests automatic proxy injection?

A. linkerd.io/inject: enabled

B. linkerd.io/proxy: true

C. sidecar.linkerd.io/inject: true

D. linkerd/auto-inject: yes

<details>
<summary>Answer and explanation</summary>

**Answer: A**

The annotation requests injection for eligible newly created Pods. Pod-level overrides, webhook exclusions and platform conditions can change the result; it is not a guarantee that every new Pod is injected. Existing Pods must be recreated, and native sidecars may appear in initContainers.

</details>
