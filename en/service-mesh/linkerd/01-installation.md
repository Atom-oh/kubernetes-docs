# Linkerd Installation and Setup

> **Last Updated**: September 11, 2026 · Public CLI: edge-26.9.1 · Matching charts: 2026.9.1

This guide covers a controlled Kubernetes installation, Helm/CLI ownership, HA, optional extensions, EKS considerations, upgrades and removal. The upstream project publishes edge artifacts; stable distributions have vendor-specific installation/support guidance. A milestone such as 2.20 is not an upstream stable-2.20.0 download.

Commands below use Bash unless marked PowerShell. Use the intended kubeconfig/context and installation owner. CLI and Helm installation procedures are **alternatives**: do not apply CLI-generated resources over a Helm-owned release. Offline checks do not establish production sizing, storage, network enforcement or application compatibility.

## Prerequisites

### Kubernetes and Gateway API

| Track/version | Kubernetes evidence | Gateway API evidence |
|---|---|---|
| Linkerd 2.20 milestone/distribution | Published matrix 1.31–1.35; confirm vendor support | Published matrix 1.2.1–1.5.1 |
| Public edge-26.9.1 used here | Released CLI minimum 1.31.0; edge-26.8.2 raised tested maximum to 1.36 | Released support for 1.5.1; this guide uses its standard bundle |
| Historical 2.16 | Published matrix 1.22–1.29 | Not a current-install recommendation |
| Historical 2.15 / 2.14 | Published ranges 1.22–1.29 / 1.21–1.28 | Check the corresponding release; do not infer “and every later Kubernetes version” |

The CLI's minimum-version check is not a maximum-support check. Passing check --pre does not prove compatibility with a newly released Kubernetes or Gateway API version. For EKS, also check which versions and support periods are available there. The Helm validation in this audit used Kubernetes 1.35 capabilities.

### Capacity and platform

Do not size the entire control plane from a universal 100m CPU/200Mi claim. Inspect rendered requests/limits for controllers, policy containers, proxies, init containers and extensions; measure actual traffic and connection load. HA expects at least three eligible nodes for its required node anti-affinity, plus sufficient capacity during rollout. Zone spreading is a preference, not a guarantee of three distinct zones.

The walkthrough targets Linux Kubernetes nodes. A Windows CLI download does not establish support for a Windows workload configuration. Check the selected release's workload/platform support separately. For Cilium kube-proxy replacement, review socketLB.hostNamespaceOnly; when chaining Linkerd CNI with Cilium, cni.exclusive must allow other plugins.

### Network paths and pre-flight checks

Verify source/destination paths, not just a list of ports to open everywhere:

| Path | Default examples in the pinned render |
|---|---|
| API server to admission services | Service 443 to injector/SP-validator 8443 and policy-validator 9443 |
| Proxy to control plane | Identity 8080, destination 8086, policy 8090 |
| Meshed application traffic | Proxy inbound 4143, plus actual application/service paths |
| Viz if installed | Tap API server 8089, tap gRPC 8088, metrics API 8085, Prometheus 9090 |
| Diagnostics | Proxy metrics 4191; web UI 8084 and separate web admin/readiness 9994 |

These are component ports, not an unrestricted security-group rule set. Include DNS, Kubernetes API and the selected CNI/network-policy behavior. Inspect actual Service targetPorts and webhook configurations.

```bash
LINKERD_CHART_VERSION=2026.9.1
CNI_ENABLED=false  # Set true only after installing/verifying Linkerd CNI.
kubectl config current-context
kubectl version
kubectl get nodes -L kubernetes.io/os,kubernetes.io/arch,topology.kubernetes.io/zone
kubectl get crd httproutes.gateway.networking.k8s.io \
  -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
# For a new lab without a conflicting installed bundle, after ownership review:
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
linkerd check --pre --linkerd-cni-enabled="$CNI_ENABLED"
```

Only apply the Gateway API bundle when needed after reviewing existing CRD ownership and all consuming controllers. If Linkerd CNI is selected, install/verify it before the control plane and use the CNI-aware check described below. Read the actual check output and exit status; the old example's long “all green” transcript was not a result for your cluster.

## Linkerd CLI Installation

### Pinned Linux/macOS binaries

The following selects the exact published asset and compares its SHA256 with the official release metadata. It changes PATH only in the current shell:

```bash
set -euo pipefail
LINKERD_VERSION=edge-26.9.1
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) suffix=linux-amd64; expected=094e1de06215fbe76fc011cf62c96214f8dae0cd5a58135fb40307be88b6b176 ;;
  Linux/aarch64|Linux/arm64) suffix=linux-arm64; expected=f92eddc52dc1f3089b65fd16014cdb1bc6b07c3fd177091c365cf3d8c0ea1a8b ;;
  Darwin/x86_64) suffix=darwin; expected=acff9471f26552dd0ebb9560925a98d5ca1213a13dfc81464a2b815c9201664d ;;
  Darwin/arm64) suffix=darwin-arm64; expected=5050da9d974e0c2f548a2e9f145540ec035582cfd67f47c58c37411ae3008913 ;;
  *) echo "No verified asset for this OS/architecture in this example" >&2; exit 1 ;;
esac
CLI_DIR="$PWD/linkerd-cli/$LINKERD_VERSION"
mkdir -p "$CLI_DIR"
curl --proto '=https' --tlsv1.2 -fsSL \
  "https://github.com/linkerd/linkerd2/releases/download/$LINKERD_VERSION/linkerd2-cli-$LINKERD_VERSION-$suffix" \
  -o "$CLI_DIR/linkerd.download"
if command -v sha256sum >/dev/null; then
  actual=$(sha256sum "$CLI_DIR/linkerd.download" | awk '{print $1}')
else
  actual=$(shasum -a 256 "$CLI_DIR/linkerd.download" | awk '{print $1}')
fi
test "$actual" = "$expected"
chmod 755 "$CLI_DIR/linkerd.download"
mv "$CLI_DIR/linkerd.download" "$CLI_DIR/linkerd"
export PATH="$CLI_DIR:$PATH"
linkerd version --client
```

The listed assets cover Linux amd64/arm64 and macOS Intel/Apple Silicon. Do not assume the installer script's generic ARM branch means this release publishes a 32-bit ARM binary. The native Linux arm64 CLI was executed in this audit; the other platform binaries were identified in the official release metadata.

### Official installer alternative

The old run.linkerd.io/install script is deprecated and installs edge, not stable. The current installer accepts LINKERD2_VERSION as an environment variable; the old sh --version stable-2.16.0 command does not select a supported upstream stable artifact.

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://run.linkerd.io/install-edge -o install-linkerd.sh
# Inspect the downloaded script before execution.
LINKERD2_VERSION=edge-26.9.1 INSTALLROOT="$PWD/linkerd-installer" sh ./install-linkerd.sh
export PATH="$PWD/linkerd-installer/bin:$PATH"
linkerd version --client
```

Select the Gateway API bundle from the release compatibility matrix. The installer completion message contains its own example version; this guide pins 1.5.1 after checking the selected release. Package-manager and vendor distributions may select different versions; verify their artifact provenance and version instead of assuming Homebrew/Chocolatey means the pinned release here. No shell-profile edits are required for this walkthrough.

### Windows binary

The release asset is named windows.exe, not windows-amd64.exe:

```powershell
$ErrorActionPreference = "Stop"
$LinkerdVersion = "edge-26.9.1"
$ExpectedSha256 = "d50119c635a0052bfcc7e0b96dcc985676b237ebc87464380677c413344d99a9"
$Download = Join-Path (Get-Location) "linkerd.download.exe"
$Url = "https://github.com/linkerd/linkerd2/releases/download/$LinkerdVersion/linkerd2-cli-$LinkerdVersion-windows.exe"
Invoke-WebRequest -Uri $Url -OutFile $Download
if ((Get-FileHash -Algorithm SHA256 $Download).Hash.ToLowerInvariant() -ne $ExpectedSha256) {
    throw "Linkerd release checksum mismatch"
}
Move-Item $Download (Join-Path (Get-Location) "linkerd.exe") -Force
.\linkerd.exe version --client
```

The remaining Bash examples require an appropriate shell, such as a configured WSL environment, or translation into native PowerShell commands. This audit did not execute PowerShell or test Windows workloads.

## Control Plane Installation

### CLI installation

For a new CLI-owned installation, apply Linkerd CRDs before generating/installing the control plane:

```bash
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-control-plane.yaml
# Review the generated resources and trust credentials before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

The commands generate manifests; kubectl performs the installation. Default CLI-generated trust anchor and issuer credentials have finite lifetimes and require rotation planning. Shared-trust multicluster needs deliberately provided credentials, not independently generated roots on each cluster.

### Helm installation

Helm provides a repeatable release/values workflow. Pin the chart version separately from the CLI tag:

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
helm show chart linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
```

The matching public charts are linkerd-crds, linkerd-control-plane, linkerd-viz, linkerd-multicluster and linkerd2-cni at 2026.9.1. The current core chart appVersion is edge-26.9.1. Do not install an unpinned old stable-repository chart while assuming it matches this CLI.

#### Trust anchor and issuer

Helm requires the trust anchor certificate plus issuer certificate/private key, or a deliberately configured supported external issuer-secret integration. It does not require uploading the root CA private key.

Use an installed [Smallstep CLI](https://smallstep.com/docs/step-cli/installation/) with the published certificate-create interface. This ECDSA P-256 example preserves the original demonstration lifetimes but fixes the broken continuation after --not-after:

```bash
umask 077
mkdir linkerd-pki
(
  cd linkerd-pki
  # Demonstration lifetimes, not a universal certificate policy.
  step certificate create root.linkerd.cluster.local ca.crt ca.key \
    --profile root-ca --kty EC --curve P-256 \
    --not-after 87600h --no-password --insecure
  step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
    --profile intermediate-ca --kty EC --curve P-256 \
    --not-after 8760h --no-password --insecure \
    --ca ca.crt --ca-key ca.key
  openssl verify -CAfile ca.crt issuer.crt
  openssl x509 -in issuer.crt -noout -text
)
```

Inspect the chain, algorithm and validity before installation. The root private key stays outside Kubernetes; only the public trust anchor and issuer signing credential are supplied below. --no-password/--insecure creates unencrypted local keys, so the example uses a restricted directory/umask. Production PKI needs an approved key-storage and rotation process. The audit checked these flags against official documentation; it did not execute Smallstep certificate generation.

#### Custom values

Save the following as linkerd-values.yaml. These are sizing examples, not workload guarantees:

```yaml
proxy:
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 64Mi
      limit: 250Mi
  logLevel: warn,linkerd=info
  logFormat: plain
identity:
  issuer:
    clockSkewAllowance: 20s
    issuanceLifetime: 24h0m0s
controllerResources: &id001
  cpu:
    request: 100m
    limit: 1000m
  memory:
    request: 50Mi
    limit: 250Mi
destinationResources: *id001
identityResources: *id001
proxyInjectorResources: *id001
```

proxy.logLevel and proxy.logFormat are the actual nested keys. destinationResources, identityResources and proxyInjectorResources are supported even though they are not all present in the base values file; the packaged HA file and templates use them. The old namespace.labels map and top-level proxyLogLevel/proxyLogFormat were not consumed. The chart appends header/request logging suppression rules to the configured proxy log selector by default; inspect the final environment value.

```bash
helm install linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --create-namespace --wait

helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  > linkerd-rendered.yaml
# Review the render, then install through Helm (do not apply the render as another owner).
helm install linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd -f linkerd-values.yaml \
  --set "cniEnabled=$CNI_ENABLED" \
  --set-file identityTrustAnchorsPEM=linkerd-pki/ca.crt \
  --set-file identity.issuer.tls.crtPEM=linkerd-pki/issuer.crt \
  --set-file identity.issuer.tls.keyPEM=linkerd-pki/issuer.key \
  --wait --timeout 10m
linkerd check
```

Generated manifests and Helm value backups can contain issuer private keys. Keep them restricted and do not paste them into diagnostic reports. Maintain the same release/credential owner on subsequent upgrades.

## High Availability (HA) Installation

Use the pinned chart's packaged values-ha.yaml:

```bash
helm pull linkerd-edge/linkerd-control-plane --version "$LINKERD_CHART_VERSION"
tar -xOf "linkerd-control-plane-$LINKERD_CHART_VERSION.tgz" \
  linkerd-control-plane/values-ha.yaml > linkerd-ha.yaml
# For the Helm render/install above, use:
# -f linkerd-ha.yaml -f linkerd-values.yaml
# For a new CLI-owned installation, render with:
linkerd install --ha --linkerd-cni-enabled="$CNI_ENABLED" > linkerd-ha-rendered.yaml
```

For Helm, use the indicated HA file **before** your custom values in both render and install. Check that later overrides do not disable required HA settings.

The packaged profile enables three replicas of critical components, required separation by node, preferred separation by zone, PDBs and a Fail admission-webhook policy. These are redundant serving instances, not a three-member consensus quorum. Availability also depends on API-server/network access, credentials, capacity and the application.

The former hand-written destination.replicas/identity.resources/proxyInjector.resources fields did not configure the intended containers. A root podDisruptionBudget map did not create any PDB, and root topologySpreadConstraints was not consumed. Offline rendering of that old example showed three replicas but missing controller resource settings and no PDBs. Use the actual packaged profile and inspect the result.

```bash
kubectl -n linkerd get pods -o wide
kubectl -n linkerd get pdb
kubectl -n linkerd get deployments -o yaml
```

If fewer than three eligible nodes exist, required anti-affinity can leave replicas Pending. Check admission Fail behavior and disruptions before relying on HA; do not weaken the webhook policy as a generic availability fix.


## Extension Installation

### Viz: dashboard and metrics

For a CLI-owned extension:

```bash
linkerd viz install > linkerd-viz.yaml
# Review the optional extension and its metrics backend.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

For Helm, save the following as viz-values.yaml and inspect the rendered PVC, Deployment and resource settings:

```yaml
prometheus:
  enabled: true
  resources:
    cpu:
      request: 300m
      limit: 1000m
    memory:
      request: 300Mi
      limit: 1Gi
  persistence:
    storageClass: gp3
    size: 10Gi
    accessMode: ReadWriteOnce
dashboard:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
tap:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 1000m
    memory:
      request: 50Mi
      limit: 250Mi
metricsAPI:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 50Mi
      limit: 250Mi
```

```bash
helm install linkerd-viz linkerd-edge/linkerd-viz \
  --version "$LINKERD_CHART_VERSION" -n linkerd-viz --create-namespace \
  -f viz-values.yaml --wait --timeout 10m
linkerd viz check
```

The selected chart supports persistence when the persistence **map is present**. It does not use persistence.enabled as the switch. accessMode is required by its PVC template; the old example omitted it and rendered a null access mode. Omitting the map uses emptyDir. A gp3 StorageClass is an example prerequisite, not something Viz creates; verify the EBS CSI driver, permissions and volume topology on EKS.

The bundled Prometheus is a single replica; persistence selects a Recreate deployment strategy. A PVC preserves data across suitable Pod replacement but does not make metrics storage HA or guarantee uninterrupted availability. Chart 2026.9.1 defaults to Prometheus v2.55.1 and six-hour retention. Choose backend maintenance, retention and availability requirements explicitly.

For an already configured external Prometheus, this is an **alternative** values file:

```yaml
prometheus:
  enabled: false
prometheusUrl: http://prometheus.monitoring.svc.cluster.local:9090
```

Configure the external server's Linkerd scrape/relabeling and access policies before switching. Verify real Viz queries and metrics, not only an HTTP-ready endpoint. dashboard, tap and metricsAPI resource settings are supported. grafana.enabled is not a deployment switch: this chart exposes Grafana link settings for a separately managed Grafana.

Use the localhost dashboard command for the initial workflow. dashboard.enforcedHostRegexp validates Host values; it is not user authentication, and an empty value selects the chart's default host restriction. An organizational ingress needs separate authentication/authorization, approved network exposure and an allowed host.

### Distributed tracing

edge-26.9.1 has no linkerd jaeger subcommand. The public linkerd-jaeger chart history stops at 2025.9.4; it is not a matching 2026.9.1 extension. Replace the obsolete install/check/upgrade/uninstall instructions with a separately managed collector/backend and the selected proxy tracing configuration.

Tracing requires incoming trace context, application propagation and compatible collector/export protocols. A Viz topology or metric graph is not a distributed trace. See the [observability guide](05-observability.md) and [official tracing documentation](https://linkerd.io/docs/features/distributed-tracing/) for the complete data path. This installation audit does not claim an untested collector/Jaeger deployment works end to end. If an older installation already has a linkerd-jaeger release, inventory and migrate its data, then retire it through its original owner; the current CLI cannot manage that removed extension.

### Multicluster

The CLI can render a base extension:

```bash
linkerd multicluster install > linkerd-multicluster.yaml
# Review network exposure, shared trust and actual gateway configuration first.
kubectl apply -f linkerd-multicluster.yaml
linkerd multicluster check
```

Before applying, choose the gateway exposure appropriate to the network. Installing the extension alone does not link clusters, create shared trust or grant remote Kubernetes API access.

For an EKS deployment using **AWS Load Balancer Controller**, this example selects an internal NLB and preserves TCP transport to the Linkerd gateway:

```yaml
gateway:
  replicas: 1
  serviceType: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
remoteMirrorServiceAccountName: linkerd-service-mirror-remote-access-default
```

Save as multicluster-values.yaml, then use the Helm alternative:

```bash
helm install linkerd-multicluster linkerd-edge/linkerd-multicluster \
  --version "$LINKERD_CHART_VERSION" -n linkerd-multicluster --create-namespace \
  -f multicluster-values.yaml --wait --timeout 10m
```

loadBalancerClass selects the intended controller. EKS Auto Mode uses a different class/configuration contract; do not combine those assumptions or change an existing Service's ownership casually. Ensure remote networks can resolve/reach the internal gateway and its probe path. Do not terminate Linkerd's transport mTLS at an unrelated ACM listener.

gateway.resources is not consumed by the pinned chart. Gateway proxy resources come from injection configuration; inspect the resulting Pod rather than assuming an ignored values block changed its limits. The HA override shipped with this chart uses gateway.replicas and anti-affinity.

Current edge remote credentials reject exec auth providers. Use the credential flow supported by the [multicluster guide](06-multi-cluster.md), and verify the resulting service-mirror controller/version and least-privilege API access.

## CNI and Amazon EKS Configuration

### Optional Linkerd CNI

Linkerd CNI chains with the primary CNI; it does not replace Amazon VPC CNI or Cilium. It must be ready on applicable nodes **before** the control plane and meshed workloads use the CNI-enabled configuration:

```bash
# Optional branch, before control-plane installation.
helm install linkerd-cni linkerd-edge/linkerd2-cni \
  --version "$LINKERD_CHART_VERSION" -n linkerd-cni --create-namespace --wait
kubectl -n linkerd-cni rollout status daemonset/linkerd-cni --timeout=180s
CNI_ENABLED=true
linkerd check --pre --linkerd-cni-enabled
# Use --linkerd-cni-enabled=true for CLI control-plane installation,
# or --set cniEnabled=true for the control-plane Helm chart.
```

Verify the node's CNI configuration/binary directories and installed plugin behavior. The defaults are /etc/cni/net.d and /opt/cni/bin, not universal platform paths. The selected control-plane chart consumes cniEnabled; rendering must show the expected omission of linkerd-init.

Without Linkerd CNI, the normal init-container redirect path needs NET_ADMIN capability. With CNI, that work moves to the node plugin. Native sidecars are enabled by default in this release, so inspect both containers and initContainers when diagnosing proxy injection. The released Identity Deployment deliberately uses a regular proxy and disables its startup wait; do not classify that bootstrap exception as a failed injection. Disabling native sidecars changes init-container network/startup ordering; a bypass UID is not a generic security fix.

For Cilium kube-proxy replacement, Linkerd's documented setup uses socketLB.hostNamespaceOnly=true so Pod traffic retains Service addresses for discovery. Chaining Linkerd CNI also needs cni.exclusive=false. Review these changes with the primary CNI owner rather than blindly replacing its configuration.

### Existing EKS cluster

Use an existing supported cluster and verify its version against both the Linkerd track and EKS availability. The former EKS 1.28 creation command is obsolete current guidance. This Linux-node procedure assumes compatible EC2-backed nodes; Fargate cannot run the Linkerd CNI DaemonSet shown here, so it is not an interchangeable target for this procedure.

If preparing a dedicated kubeconfig:

```bash
: "${EKS_CLUSTER_NAME:?Set the intended existing cluster}"
: "${EKS_REGION:?Set its region}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --query 'cluster.{version:version,endpoint:endpoint}' --output json
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"   --kubeconfig "$PWD/linkerd.kubeconfig" --alias linkerd-lab
export KUBECONFIG="$PWD/linkerd.kubeconfig"
kubectl config current-context
kubectl -n kube-system get daemonset aws-node   -o jsonpath='{.spec.template.spec.containers[*].image}'
```

Verify the intended endpoint/context before cluster mutations. Standard Linkerd controllers use Kubernetes API credentials; an IAM role is not required merely for linkerd-destination to discover Services. AWS API permissions belong to the actual caller, such as Load Balancer Controller, EBS CSI or a telemetry collector, with its supported IRSA/Pod Identity setup.

### EKS dashboard and network considerations

The old internet-facing ALB example published the administrative dashboard without an authentication design. Use localhost administration until an authenticated organizational ingress is configured and tested.

The web Service's 8084 port is valid. Its separate admin/readiness port is 9994, with the chart's readiness probe at /ready on that port. Do not assume the same health semantics on the UI listener. An ALB design must align target health, security groups, host validation, certificate ownership and authentication; a TLS certificate alone does not authenticate dashboard users.

Scope security-group and NetworkPolicy rules to the actual source/destination roles. The component-port table is diagnostic information, not a request to expose proxy metrics or webhook ports to every source. Validate CNI startup, DNS, admission, identity and cross-node paths in the actual cluster.

## Installation Verification

```bash
linkerd check
linkerd check --proxy -n my-app
linkerd viz check
linkerd multicluster check
kubectl -n linkerd get pods,services,pdb -o wide
kubectl -n linkerd-viz get pods,services -o wide
```

Run extension checks only for installed extensions. check --proxy checks the data plane; it does not mean “include every extension.” These checks do not validate application business logic.

For a sample application, review a pinned application manifest before applying it, annotate only its selected namespace and recreate the intended workloads. A mutable emojivoto URL plus a round-trip of every live Deployment is not a reproducible application input. Confirm images/architecture, Service ports, readiness and actual HTTP/TCP outcomes.

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
linkerd viz stat deploy/my-app -n my-app
linkerd viz top deploy/my-app -n my-app
```

Replace my-app with the actual namespace and Deployment. Metrics/tap/top depend on the configured extension and supported protocol; they do not prove all traffic is encrypted or all business operations succeed.

## Linkerd Upgrade

### Upgrade planning

Select the exact target CLI/chart, review release notes, compatibility, supported version skew and current health. The target shown here is not a direct-upgrade promise from every historical 2.14/2.16 installation; follow required intermediate upgrades and vendor guidance. Edge tags are not semantic-version guarantees. Upgrade the CLI, CRDs/control plane, installed extensions and finally data-plane proxies through their respective owners.

Use check and check --proxy for an existing installation. check --pre is a new-install preflight that includes namespace/setup assumptions, not a substitute for upgrade planning. Preserve current trust credentials and review removed CRD versions before any upgrade.

### CLI-owned installation

```bash
# First install/verify the selected target CLI and review the supported upgrade path.
linkerd version --client
linkerd check
linkerd check --proxy
linkerd upgrade --crds > linkerd-crds-upgrade.yaml
kubectl apply -f linkerd-crds-upgrade.yaml
linkerd upgrade > linkerd-upgrade.yaml
# Review retained configuration and credentials before applying.
kubectl apply -f linkerd-upgrade.yaml
linkerd check
linkerd viz install > linkerd-viz-upgrade.yaml
kubectl apply -f linkerd-viz-upgrade.yaml
linkerd viz check
# Likewise review/install the selected multicluster extension if present.
linkerd prune > linkerd-obsolete.yaml
# Review ownership and contents before any kubectl delete -f linkerd-obsolete.yaml.
```

Extensions have install commands for rendering updates, not a viz upgrade subcommand. A help command returning exit 0 can still be parent-command help; inspect the available command list and generated resource content. Review prune output before deleting anything. Multicluster controller updates may require re-linking through the supported workflow.

### Helm-owned installation

```bash
umask 077
helm get values linkerd-control-plane -n linkerd > current-values.yaml
helm get manifest linkerd-control-plane -n linkerd > current-manifest.yaml
# Migrate intentional overrides to reviewed-values.yaml; preserve current trust credentials.
helm upgrade linkerd-crds linkerd-edge/linkerd-crds \
  --version "$LINKERD_CHART_VERSION" -n linkerd --wait
helm upgrade linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version "$LINKERD_CHART_VERSION" -n linkerd \
  --reset-values -f reviewed-values.yaml --wait --timeout 10m
# Upgrade each installed extension with its own reviewed values and pinned chart.
linkerd check
```

The reviewed values must include intentional HA/CNI settings and the **existing** trust/issuer configuration or supported external-secret references. --reset-values without preserving those inputs can change behavior or fail; --reuse-values can retain obsolete settings. Compare target defaults and overrides, and never regenerate the CA merely as part of a routine upgrade.

### Data-plane update

Update one intended workload at a time according to its availability policy:

```bash
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, proxies: ([.spec.containers[]?, .spec.initContainers[]?] | map(select(.name == "linkerd-proxy") | {image, restartPolicy}))}'
```

stat is a traffic-statistics command, not a proxy-image version inventory. Both regular and native sidecar locations are inspected above. Check the relevant version-skew guidance and actual readiness/traffic after recreation.

## Troubleshooting

### Admission and resources

```bash
kubectl -n linkerd get service linkerd-proxy-injector
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config -o yaml
kubectl -n linkerd get networkpolicy
kubectl -n linkerd get events --sort-by='.lastTimestamp'
: "${LINKERD_POD:?Set a control-plane Pod name}"
kubectl -n linkerd describe pod "$LINKERD_POD"
```

Injection failure can involve CA bundles, webhook selection/networking, rejected configuration or Pod security; it is not always a Service connectivity issue. Pending can reflect anti-affinity, taints, volumes, quota or resources. Inspect the actual event before changing resource limits or security settings.

### Certificates

In the default installation, trust roots are in a **ConfigMap**, while the issuer signing key/certificate are in a Secret:

```bash
set -euo pipefail
kubectl -n linkerd get configmap linkerd-identity-trust-roots \
  -o jsonpath='{.data.ca-bundle\.crt}' > trust-bundle.pem
openssl crl2pkcs7 -nocrl -certfile trust-bundle.pem |
  openssl pkcs7 -print_certs -text -noout
kubectl -n linkerd get secret linkerd-identity-issuer -o json |
  jq -er '.data["crt.pem"] // .data["tls.crt"]' |
  base64 -d | openssl x509 -noout -dates
```

The default issuer format uses crt.pem; a configured kubernetes.io/tls integration uses tls.crt. Check the configured scheme rather than assuming every issuer Secret has the same fields. Custom trust integrations can change the storage owner. Inspect all trust certificates, clock/validity, issuer availability and identity errors; avoid unplanned root replacement.

### Component and proxy logs

```bash
kubectl -n linkerd logs deployment/linkerd-destination -c destination
kubectl -n linkerd logs deployment/linkerd-destination -c policy
kubectl -n linkerd logs deployment/linkerd-identity -c identity
kubectl -n linkerd logs deployment/linkerd-proxy-injector -c proxy-injector
: "${APP_POD:?Set an application Pod name}"
kubectl -n my-app logs "$APP_POD" -c linkerd-proxy
linkerd diagnostics proxy-metrics "$APP_POD" -n my-app
```

Use actual component/container names from the installed version. Retain relevant logs before deleting or replacing Pods.

## Uninstallation

### Remove application proxies first

Plan for the loss of mesh transport policy, routing and observability. Remove injection sources and manual proxy configuration through the workload's owner, recreate the workloads, and verify both container locations before removing the control plane:

```bash
# Choose the actual application namespace/Deployment and review all injection sources.
kubectl annotate namespace my-app linkerd.io/inject-
# Also remove any Pod-template injection override/manual proxy using its manifest owner.
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
kubectl -n my-app get pods -o json |
  jq '.items[] | {pod: .metadata.name, containers: ([.spec.containers[]?, .spec.initContainers[]?] | map(.name))}'
```

A namespace annotation removal alone does not override a Pod-template annotation or remove a manually injected proxy. Validate application connectivity and security after unmeshing. Do not use force to bypass remaining injected workloads.

### CLI-owned removal

```bash
# Only after applications are unmeshed and extension dependencies are removed.
linkerd viz uninstall > remove-viz.yaml
linkerd multicluster uninstall > remove-multicluster.yaml
# Inspect each manifest and remove only the extensions actually installed via CLI.
kubectl delete -f remove-viz.yaml
kubectl delete -f remove-multicluster.yaml
linkerd uninstall > remove-linkerd.yaml
# This includes namespace-scoped resources and cluster-wide CRDs.
kubectl delete -f remove-linkerd.yaml
```

Only remove installed extensions. The generated control-plane removal includes CRDs; deleting them deletes their custom-resource instances. Inventory and back up what must be retained. This is not merely a Deployment deletion.

### Helm-owned removal

```bash
# Only the releases actually installed through Helm, after unmeshing applications.
helm uninstall linkerd-viz -n linkerd-viz
helm uninstall linkerd-multicluster -n linkerd-multicluster
helm uninstall linkerd-control-plane -n linkerd
# Inventory/back up CR instances before removing the CRDs.
helm uninstall linkerd-crds -n linkerd
```

If Linkerd CNI was installed, separately follow its node-plugin cleanup after no workloads depend on it and verify the primary CNI remains intact. Delete namespaces only after verifying ownership and remaining contents, not as an unconditional four-namespace cleanup.

## Next Steps

- [Architecture](02-architecture.md)
- [Traffic Management](03-traffic-management.md)
- [Security and certificate lifecycle](04-security.md)
- [Observability](05-observability.md)
- [Multicluster](06-multi-cluster.md)
- [Installation Quiz](../../quizzes/service-mesh/linkerd/installation.md)

## References

- [Release model](https://linkerd.io/releases/) and [edge-26.9.1 artifacts](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)
- [Kubernetes matrix](https://linkerd.io/docs/reference/k8s-versions/) and [Gateway API compatibility](https://linkerd.io/docs/features/gateway-api/)
- [Helm installation](https://linkerd.io/docs/tasks/install-helm/) and [official edge chart index](https://helm.linkerd.io/edge/index.yaml)
- [HA behavior](https://linkerd.io/docs/features/ha/) and [cluster/Cilium configuration](https://linkerd.io/docs/reference/cluster-configuration/)
- [Certificate generation](https://linkerd.io/docs/tasks/generate-certificates/) and [Smallstep create reference](https://smallstep.com/docs/step-cli/reference/certificate/create/)
- [CNI](https://linkerd.io/docs/features/cni/), [upgrade](https://linkerd.io/docs/tasks/upgrade/) and [uninstall](https://linkerd.io/docs/tasks/uninstall/)
- [AWS Load Balancer Controller Service settings](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/) and [EKS Fargate constraints](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
