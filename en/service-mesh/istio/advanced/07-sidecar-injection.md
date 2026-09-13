# Sidecar Injection

> **Verification baseline**: Istio 1.31.0, Kubernetes 1.32–1.36
> **Last reviewed**: September 11, 2026

Automatic injection is an admission webhook that modifies newly created Pods. It does not add a running sidecar to existing Pods or edit the Deployment template itself. Manual `istioctl kube-inject` renders an application manifest with the proxy configuration included.

## Automatic Injection Configuration

### Namespace Level

Use one injection mode for the existing application namespace. Record its labels and installed revision before changing them; do not use a revision label for a revision/tag that has no matching injector.

```bash
# Existing, reviewed application namespace; inspect before choosing one mode.
INJECTION_NAMESPACE=injection-demo
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode

# Legacy/default injection alternative, only when no revision/ambient mode is selected.
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection=enabled --overwrite
```

```bash
# Alternative: choose an already installed revision or existing revision tag.
istioctl tag list
kubectl get mutatingwebhookconfigurations -l istio.io/rev
kubectl label namespace "$INJECTION_NAMESPACE" istio-injection-
kubectl label namespace "$INJECTION_NAMESPACE" istio.io/rev=<installed-revision-or-tag> --overwrite
```

When a namespace has both `istio-injection` and `istio.io/rev`, the legacy `istio-injection` label takes precedence. A namespace `istio-injection=disabled` or Pod `sidecar.istio.io/inject="false"` disables injection even when another injection label requests it. Without explicit labels, injection is normally off unless the installer enables `enableNamespacesByDefault`.

After reviewing availability/PDB/capacity, recreate only the intended workloads to adopt the chosen injector. A namespace label change alone does not alter existing Pods. Keep ambient enrollment separate; use the [ambient migration guide](01-ambient-mode.md) rather than mixing dataplane modes.

### Pod Level

The injection **label** belongs on the Pod, or on `spec.template.metadata` for a Deployment. The older annotation with the same name is deprecated.

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "true"
```

This selects eligible Pods for injection but does not override a namespace disable or deploy an application. Preserve existing app labels, revision and workload configuration; these are fragments, not runnable Pods with a guessed `myapp:latest` image.

## Manual Injection

Use the `istioctl` version and complete configuration matching the intended control plane. By default, kube-inject can read the selected cluster configuration; for reproducible local rendering, export the actual injector/mesh ConfigMaps for that revision and inspect them first.

```bash
# Obtain all three files from the same installed revision/configuration.
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.config}' > inject-config.yaml
kubectl -n istio-system get configmap <injector-configmap> -o jsonpath='{.data.values}' > inject-values.yaml
kubectl -n istio-system get configmap <mesh-configmap> -o jsonpath='{.data.mesh}' > mesh-config.yaml

# Render from the reviewed original application manifest with matching istioctl.
istioctl kube-inject --revision <actual-revision-or-default> --injectConfigFile inject-config.yaml --meshConfigFile mesh-config.yaml --valuesFile inject-values.yaml --filename deployment.yaml --output deployment-injected.yaml

# Review the generated file and deployment diff before the planned rollout.
kubectl diff -f deployment-injected.yaml
kubectl apply -f deployment-injected.yaml
```

In Istio1.31, omitting `--revision` can trigger a default-revision cluster watcher even with local files and leave the command waiting. Specify the actual revision matching the exported configuration, or `default` for a non-revisioned installation. Rendering with an explicit revision and all three local configuration files was verified without cluster discovery.

`deployment.yaml` must contain the original application resources. Keep it separate from generated output and regenerate from that source after configuration/version changes. Choose automatic or manual injection ownership deliberately and inspect admission results; do not stack ad hoc edits onto generated proxy containers. A `kubectl diff` exit 1 normally means a difference was found, not that applying it has been approved or validated.

## Sidecar Resource Configuration

These are the original example requests/limits, retained as workload-specific tuning inputs rather than production sizing:

```yaml
# Existing Deployment: spec.template fragment
metadata:
  annotations:
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
```

Set request and corresponding limit deliberately: specifying proxyCPU/proxyMemory without the corresponding limit can remove that limit. Verify the rendered proxy resources, namespace LimitRange/ResourceQuota, CPU throttling and memory use. Pod-template changes affect newly created Pods.

## Excluding from Injection

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "false"
```

The label prevents future sidecar injection; it does not remove an existing injected proxy or opt a Pod out of ambient capture. Reconcile existing labels/annotations and recreate only the selected workload through its normal rollout process.

## Troubleshooting

```bash
kubectl get namespace "$INJECTION_NAMESPACE" -L istio-injection,istio.io/rev,istio.io/dataplane-mode
kubectl get mutatingwebhookconfigurations
kubectl get events -n "$INJECTION_NAMESPACE" --sort-by=.lastTimestamp

kubectl get pods -n "$INJECTION_NAMESPACE" -o json |
  jq '.items[] | {
    pod:.metadata.name,
    revision:.metadata.annotations["istio.io/rev"],
    proxies: ([.spec.containers[]?, .spec.initContainers[]?] |
      map(select(.name == "istio-proxy") | {name,image,restartPolicy}))
  }'
istioctl proxy-status
```

Native sidecars use `spec.initContainers` with `restartPolicy: Always`; classic sidecars use `spec.containers`. Kubernetes native sidecars are stable from 1.33 and default-enabled in 1.32, while Istio's `sidecar.istio.io/nativeSidecar` annotation is still documented Alpha. Confirm the installed injector behavior instead of assuming a universal 2/2 READY display.

If Pods are not created, inspect controller events, webhook reachability/certificates, namespace/object selectors, revision availability and resource admission limits. If a proxy is present, inspect readiness, logs and xDS synchronization separately. A proxy name alone does not prove correct mesh enrollment.

## References

- [Istio sidecar injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Istio injection annotations](https://istio.io/latest/docs/reference/config/annotations/)
- [Istio revision upgrades](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Kubernetes native sidecar containers](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Istio 1.31 injection template](https://raw.githubusercontent.com/istio/istio/1.31.0/manifests/charts/istio-control/istio-discovery/files/injection-template.yaml)
- [Istio 1.31 local injection command](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/kubeinject/kubeinject.go)
- [Istio 1.31 default revision resolution](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/cli/context.go)
