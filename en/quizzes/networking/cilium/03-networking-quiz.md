# Cilium Networking Validation Exercises

This chapter provides eight guided exercises with expected outcomes. The baseline is Cilium 1.20.1, CLI 0.20.0 and a supported Kubernetes version (1.33–1.36), reviewed September 12, 2026. It does not claim compatibility with every version “1.30 and above.”

## Prerequisites

Use a disposable cluster prepared through the [networking guide](../../../networking/cilium/03-networking.md) and [installation profiles](../../../networking/cilium/README.md), with two schedulable Linux nodes. Use architecture-appropriate tools and image pulls. Keep kubectl within the documented version skew. These exercises do not migrate an existing CNI or change provider-managed networking.

The manual policy lab needs permission to create a new namespace, Pods, a Deployment, Service and namespaced CiliumNetworkPolicy. Review existing cluster-wide policy/admission constraints: a separate namespace does not override them. Run shell blocks in the same shell so variables persist.

## 1. Installation and Basic Testing

Use the installation guide's verified CLI download procedure and one chosen Cilium profile. Do not run both Helm and CLI installers against the same release or use an unverified `latest` AMD64 archive.

```bash
set -euo pipefail
kubectl config current-context
kubectl version -o yaml
cilium version
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

Optionally run the maintained connectivity suite on the disposable cluster. It creates workloads/policies and can contact external targets; examine its selected tests and prerequisites.

```bash
cilium connectivity test --test-namespace cilium-net-smoke \
  --namespace-labels docs-audit-lab=cilium-networking-03
```

CLI 0.20.0 appends a sequence suffix: the default single suite uses `cilium-net-smoke-1`. Read failures and skipped cases; a completed command is not proof that untested cloud or feature combinations work.

<details>
<summary>Expected result and self-check</summary>

Installed versions fit the documented matrix, agents become ready, and the selected connectivity cases pass. Explain why a ready DaemonSet alone does not prove cross-node routing, and why “kubectl 1.31+” is insufficient for a newer API server.

</details>

## 2. Network Policy Testing

### Create an Isolated Test Namespace and Workloads

```bash
kubectl create namespace cilium-net-lab
kubectl label namespace cilium-net-lab docs-audit-lab=cilium-networking-03
```

If namespace creation reports that it already exists, stop and choose a fresh name consistently throughout the files/commands. Do not relabel or reuse someone else's namespace.

The following image digests come from the official CLI 0.20.0 test defaults. Its deployment source uses `/usr/bin/pause` for the curl image and the JSON mock server on TCP 8080 with `/` readiness. These are test images, not production application recommendations. The backend's anti-affinity separates it from the frontend across nodes.

**`lab-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-net-lab
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-net-lab
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: cilium-net-lab
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lab-app.yaml
kubectl -n cilium-net-lab wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
kubectl -n cilium-net-lab rollout status deployment/backend --timeout=120s
kubectl -n cilium-net-lab get pods -o wide
kubectl -n cilium-net-lab get endpointslices -l kubernetes.io/service-name=backend
BACKEND_IP=$(kubectl -n cilium-net-lab get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
```

A Pending backend can indicate insufficient eligible nodes for anti-affinity. Do not interpret it as a network-policy failure. First establish that **both** clients can reach the healthy backend without the new policy. Use the Service IP to keep DNS failures out of this ingress test.

```bash
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

### Apply and Check the Policy

**`allow-frontend.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-net-lab
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-net-lab
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


```bash
kubectl apply -f allow-frontend.yaml
kubectl -n cilium-net-lab get ciliumnetworkpolicy allow-frontend-to-backend -o yaml
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

Wait for policy realization on the relevant endpoints and recheck the positive request. An allowed result from a previous connection does not establish that a new policy is ready; each command here starts a fresh curl process.

```bash
if kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"; then
  echo "Unexpected allowed request: inspect combined policy and realization" >&2
  exit 1
else
  denied_rc=$?
  printf 'Outsider request failed with exit %s; correlate the flow before declaring a policy pass.\n' "$denied_rc"
fi
```

Nonzero exit is **not** automatically a passing denial test. It can also mean exec/RBAC, missing curl, routing, backend or other failures. A curl timeout is often exit 28, but correlate the source/destination/port and policy-denied flow with the successful baseline and still-working frontend. The namespace-scoped rule does not prevent other policies from independently allowing traffic.

<details>
<summary>Expected result and self-check</summary>

Before the policy, both clients reach the backend. After realization, frontend still succeeds and outsider is denied with corroborating policy evidence. Explain why missing EndpointSlices, DNS errors or any arbitrary nonzero command exit cannot prove isolation. This L3/L4 policy does not add HTTP parsing.

</details>

## 3. Hubble Visibility Testing

Use the profile's enabled Hubble Relay/UI and an appropriate Hubble CLI. Keep this port-forward in a separate terminal, then run the observer in another:

```bash
cilium hubble port-forward
```

```bash
hubble status
hubble observe --namespace cilium-net-lab --last 50
hubble observe --from-pod cilium-net-lab/outsider --verdict DROPPED --last 20
cilium hubble ui
```

Generate fresh requests while observing. Event loss/aggregation and filters affect what is visible. HTTP flows require a supported L7 proxy/visibility setup; the L4 rule above does not create it. A configured L7 rejection may return HTTP 403 rather than a packet DROPPED event.

<details>
<summary>Expected result and self-check</summary>

Relay is reachable, flows identify the intended endpoints, and the negative test's evidence matches its request. Explain why no HTTP records in this L4-only lab is not proof that Hubble is broken.

</details>

## 4. Performance Testing

Run the [guide's maintained `cilium connectivity perf` example](../../../networking/cilium/03-networking.md), which provisions matching client/server workloads. Keep same-node and cross-node results separate and record node placement, versions, route MTUs and policy/encryption settings.

The former test combined unrelated `netperf-*` Pod names with an iperf3 image and a TCP-only Service. For an independently supplied iperf3 setup, a UDP test requires **TCP control plus UDP data** on the configured ports. Merely requesting `-b 1G` does not prove 1 Gbit/s delivered.

<details>
<summary>Expected result and self-check</summary>

All selected test workloads are ready and results are labeled by scenario. Explain the difference between TCP request/response, connection creation, stream throughput and UDP offered rate/loss. A benchmark result applies to the recorded setup, not every Cilium mode or cloud.

</details>

## 5. Optional Advanced Feature Checks

Configure each feature through a separately prepared, documented profile. **Do not uninstall the cluster CNI between checks.** A Helm flag alone does not supply missing keys, routes, API reachability or BGP peers.

| Feature | Preparation | Observe |
|---|---|---|
| kube-proxy replacement | `kubeProxyReplacement: true`, reachable `k8sServiceHost`/`k8sServicePort`, supported datapath and migration plan | Actual agent state plus Service traffic; `strict` is not a current value |
| IPsec/WireGuard | Correct encryption mode, key handling, ports/MTU and supported traffic scope | Agent encryption status and the actual node-to-node path |
| BGP Control Plane | `bgpControlPlane.enabled: true`, versioned BGP resources and reachable configured peers | Sessions and advertised routes; not assumed local forwarding-table programming |

Choose the agent on the relevant node:

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
cilium bgp peers
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
```

Only interpret the optional feature commands when that feature is configured. Disabled/unconfigured state in the base profile is expected. The standalone `cilium bgp peers` command reports cluster node states; the older agent-local BGP commands are deprecated. BGP requires the applicable `cilium.io/v2` configuration resources; the removed `bgp.enabled` and `bgp.announce.loadbalancerIP` settings do not establish a session.

<details>
<summary>Expected result and self-check</summary>

The observed state matches the selected profile, and the relevant traffic/route evidence supports the result. Explain why “BGP established” does not prove internal Pod routing, or why encryption status alone does not prove every traffic path is encrypted.

</details>

## 6. Compatibility Checks

```bash
kubectl version -o yaml
cilium version
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.kernelVersion}{"\n"}{end}'
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl -n kube-system get daemonset cilium -o yaml
```

Compare versions/features with the support matrix, including documented kernel backports. Inspect actual CNI settings and volume mounts before reading a host configuration file: `/etc/cni/net.d/05-cilium.conf` is not a universal container path or filename. Chaining/custom configurations differ. A file's existence alone does not demonstrate runtime compatibility.

<details>
<summary>Expected result and self-check</summary>

Version and kernel requirements match the platform, Pods receive addresses through the intended CNI, and traffic tests succeed. Explain the distinction between CNI installation, IPAM allocation and end-to-end forwarding.

</details>

## 7. Troubleshooting

```bash
cilium status --verbose
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
kubectl -n kube-system logs deployment/cilium-operator --tail=100
kubectl -n kube-system logs deployment/hubble-relay --tail=100
```

For a frontend endpoint, select the agent on the frontend's node before inspecting:

```bash
kubectl -n cilium-net-lab get pod frontend -o wide
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get pod-name:cilium-net-lab:frontend
```

For ingress denial, also inspect the backend's agent/endpoint. Compare desired policy, realized state, route/backend health and observed flows. Do not use removed `policy trace` commands or parse human tables with an unquoted `<pod-name>` shell placeholder.

If needed, `cilium sysdump` collects diagnostics; review the archive's logs/resource information before sharing. `cilium clustermesh status` applies only to configured Cluster Mesh, and Relay status is obtained with `hubble status` after connection setup.

<details>
<summary>Expected result and self-check</summary>

Evidence identifies the correct node and endpoint, rather than whichever DaemonSet Pod kubectl happened to select. Explain which evidence separates an unready backend, route failure, policy denial and missing observation.

</details>

## 8. Cleanup

Review which namespaces this run created and preserve results first:

```bash
kubectl get namespaces -l docs-audit-lab=cilium-networking-03
LAB_OWNER=$(kubectl get namespace cilium-net-lab -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-networking-03
kubectl delete namespace cilium-net-lab
```

If you ran the CLI suites, independently verify ownership before removing their generated `cilium-net-smoke-1` / `cilium-net-perf-1` namespaces. Do not bulk-delete unrelated namespaces or uninstall Cilium as application cleanup. Stop local port-forwards with Ctrl-C.

<details>
<summary>Expected result and self-check</summary>

Only this run's test resources are removed; the installed CNI and other workloads remain operational. Explain why repeated CNI uninstallation was not a valid way to compare features.

</details>

## Validation Limits and References

The published YAML/Helm values, shell syntax and CLI/API contracts were checked without deploying these workloads. No live cluster, image execution, Helm render or throughput result is claimed after the host restart. Admission, image architecture/pull policy, capacity, actual datapath and expected results must be verified in the prepared environment.

- [CLI 0.20.0 image defaults](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/defaults/defaults.go), [test deployments](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/connectivity/check/deployment.go), [connectivity/perf flags](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go)
- [Cilium 1.20.1 policy API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml), [L7 behavior](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst), [BGP configuration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst), [BGP CLI](https://github.com/cilium/cilium-cli/blob/v0.20.0/vendor/github.com/cilium/cilium/cilium-cli/cli/bgp.go), [agent commands](https://github.com/cilium/cilium/tree/v1.20.1/Documentation/cmdref)
- [Kubernetes version skew](https://kubernetes.io/releases/version-skew-policy/), [iperf3 invocation](https://software.es.net/iperf/invoking.html), [networking guide](../../../networking/cilium/03-networking.md)
