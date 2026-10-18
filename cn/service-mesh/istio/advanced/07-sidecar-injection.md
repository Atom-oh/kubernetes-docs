# Sidecar 注入

> **验证基线**：Istio 1.31.0，Kubernetes 1.32–1.37
> **最后审阅**：2026 年 10 月 16 日

自动注入是一种准入 Webhook，会修改新创建的 Pod。它不会向现有 Pod 添加正在运行的 sidecar，也不会编辑 Deployment 模板本身。手动执行 `istioctl kube-inject` 会生成包含代理配置的应用清单。

## 自动注入配置

### 命名空间级别

为现有应用命名空间选择一种注入模式。更改前，记录命名空间标签和已安装的修订版本。命名空间的修订版本标签必须指向有匹配注入器的修订版本或修订版本别名（revision tag）。

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

如果命名空间同时具有 `istio-injection` 和 `istio.io/rev`，旧版 `istio-injection` 标签优先级更高。命名空间上的 `istio-injection=disabled` 或 Pod 上的 `sidecar.istio.io/inject="false"` 会禁用注入，即使其他注入标签请求启用注入也是如此。如果没有显式标签，通常不会启用注入，除非安装程序启用了 `enableNamespacesByDefault`。

检查可用性/PDB/容量后，只重新创建需要采用所选注入器的工作负载。仅更改命名空间标签不会改变现有 Pod。请单独处理加入 ambient 网格的操作；使用 [ambient 迁移指南](01-ambient-mode.md)，不要混用数据平面模式。

### Pod 级别

注入**标签**应设置在 Pod 上，或者在 Deployment 中设置于 `spec.template.metadata` 下。名称相同的旧版注解已弃用。

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "true"
```

此设置会选择符合条件的 Pod 进行注入，但不会覆盖命名空间的禁用设置，也不会部署应用。保留现有应用标签、修订版本和工作负载配置；这些只是配置片段，并不是随意填入 `myapp:latest` 镜像即可运行的 Pod。

## 手动注入

使用与目标控制平面匹配的 `istioctl` 版本和完整配置。默认情况下，kube-inject 可以读取所选集群配置；如需可重复的本地渲染，请导出该修订版本对应的实际注入器/网格 ConfigMap，并先检查它们。

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

在 Istio 1.31 中，即使使用本地文件，省略 `--revision` 也可能触发默认修订版本的集群监视器，导致命令一直等待。请指定与导出配置匹配的实际修订版本；对于未使用修订版本的安装，请指定 `default`。已验证可使用显式修订版本和全部三个本地配置文件进行渲染，而无需进行集群配置探测。

`deployment.yaml` 必须包含原始应用资源。请将其与生成的输出文件分开保存，并在配置/版本更改后从该源文件重新生成。请明确由自动注入还是手动注入负责，并检查准入结果；不要在生成的代理容器上叠加临时修改。`kubectl diff` 退出码为 1 通常表示发现差异，并不表示已批准或验证应用这些差异。

## Sidecar 资源配置

以下是原始示例中的资源请求/限制，保留为针对特定工作负载的调优输入，不作为生产环境的容量配置：

```yaml
# Existing Deployment: spec.template fragment
metadata:
  annotations:
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
```

请审慎设置资源请求和对应的限制：只指定 proxyCPU/proxyMemory 而不指定对应的限制，可能会移除该限制。请验证渲染后的代理资源、命名空间的 LimitRange/ResourceQuota、CPU 节流和内存使用情况。Pod 模板更改会影响新创建的 Pod。

## 从注入中排除

```yaml
# Existing Deployment: spec.template fragment
metadata:
  labels:
    sidecar.istio.io/inject: "false"
```

此标签会阻止未来的 sidecar 注入；它不会移除现有的注入代理，也不会让 Pod 退出 ambient 捕获。请检查并统一现有标签/注解的设置，仅通过正常的发布流程重新创建选定的工作负载。

## 故障排查

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

原生 sidecar 使用 `spec.initContainers`，并设置 `restartPolicy: Always`；经典 sidecar 使用 `spec.containers`。Kubernetes 原生 sidecar 从 1.33 版本起为稳定功能，在 1.32 版本中默认启用；而 Istio 的 `sidecar.istio.io/nativeSidecar` 注解仍标记为 Alpha。请确认已安装的注入器行为，不要假定所有环境都会统一显示 2/2 READY。

如果 Pod 未创建，请检查控制器事件、Webhook 连通性/证书、命名空间/对象选择器、修订版本可用性和资源准入限制。如果代理已存在，请分别检查就绪状态、日志和 xDS 同步情况。仅凭代理名称无法证明已正确加入网格。

## 参考资料

- [Istio sidecar 注入](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Istio 注入注解](https://istio.io/latest/docs/reference/config/annotations/)
- [Istio 修订版本升级](https://istio.io/latest/docs/setup/upgrade/canary/)
- [Kubernetes 原生 sidecar 容器](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Istio 1.31 注入模板](https://raw.githubusercontent.com/istio/istio/1.31.0/manifests/charts/istio-control/istio-discovery/files/injection-template.yaml)
- [Istio 1.31 本地注入命令](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/kubeinject/kubeinject.go)
- [Istio 1.31 默认修订版本解析](https://raw.githubusercontent.com/istio/istio/1.31.0/istioctl/pkg/cli/context.go)
