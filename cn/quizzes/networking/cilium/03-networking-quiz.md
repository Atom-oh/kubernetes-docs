# Cilium 网络验证练习

本章提供八个带指导的练习及预期结果。基线为 Cilium 1.20.3、CLI 0.20.1 和受支持的 Kubernetes 版本（1.33–1.36），审核日期为 2026 年 10 月 16 日。本章不声称兼容所有“1.30 及以上”版本。

## 前提条件

使用通过[网络指南](../../../networking/cilium/03-networking.md)和[安装配置](../../../networking/cilium/README.md)准备的临时集群，其中有两个可调度的 Linux 节点。使用适合相应架构的工具并拉取镜像。确保 kubectl 版本处于文档所述的版本偏差范围内。这些练习不会迁移现有 CNI，也不会更改由云服务提供商管理的网络。

手动策略实验需要有权限创建新命名空间、Pod、Deployment、Service 和命名空间范围的 CiliumNetworkPolicy。检查现有的集群范围策略和准入限制：单独使用一个命名空间并不能绕过这些限制。在同一个 shell 中运行各个 shell 代码块，以便变量能够保留。

## 1. 安装和基本测试

按照安装指南中经过验证的 CLI 下载步骤，并选择一种 Cilium 配置。不要在同一发行版本上同时运行 Helm 和 CLI 安装程序，也不要使用未经验证的 `latest` AMD64 压缩包。

```bash
set -euo pipefail
kubectl config current-context
kubectl version -o yaml
cilium version
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
```

也可以在临时集群上运行维护中的连通性测试套件。该套件会创建工作负载/策略，并可能访问外部目标；请检查所选测试及其前提条件。

```bash
cilium connectivity test --test-namespace cilium-net-smoke \
  --namespace-labels docs-audit-lab=cilium-networking-03
```

CLI 0.20.1 会附加序号后缀：默认的单个测试套件使用 `cilium-net-smoke-1`。检查失败和跳过的用例；命令执行完成并不能证明未经测试的云环境或功能组合可正常工作。

<details>
<summary>预期结果和自我检查</summary>

安装的版本符合文档中的兼容矩阵，代理变为就绪状态，所选连通性测试用例通过。说明为什么 DaemonSet 就绪本身不能证明跨节点路由正常，以及为什么“kubectl 1.31+”不足以支持较新的 API 服务器。

</details>

## 2. 网络策略测试

### 创建隔离的测试命名空间和工作负载

```bash
kubectl create namespace cilium-net-lab
kubectl label namespace cilium-net-lab docs-audit-lab=cilium-networking-03
```

如果创建命名空间时提示该命名空间已存在，请停止操作并选择一个全新的名称，在所有文件/命令中统一使用。不要重新标记或复用他人的命名空间。

以下镜像摘要来自官方 CLI 0.20.1 测试默认值。其 Deployment 源码为 curl 镜像使用 `/usr/bin/pause`，为 JSON mock 服务器使用 TCP 8080，并以 `/` 作为就绪检查路径。这些是测试镜像，并非生产应用建议。后端的反亲和性会使其与前端调度到不同节点。

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

后端处于 Pending 状态可能表示满足反亲和性条件的节点不足。不要将其判定为网络策略故障。首先确认在不应用新策略时，**两个**客户端都能访问正常运行的后端。使用 Service IP，以便在此入口测试中排除 DNS 故障。

```bash
kubectl -n cilium-net-lab exec frontend -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
kubectl -n cilium-net-lab exec outsider -- \
  curl --fail --silent --show-error --connect-timeout 3 --max-time 5 "http://$BACKEND_IP:8080/"
```

### 应用并检查策略

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

等待相关端点上的策略完成生效，然后重新检查允许的请求。先前连接返回了允许结果，并不能证明新策略已经就绪；此处的每条命令都会启动一个新的 curl 进程。

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

非零退出代码**并不**自动表示拒绝测试通过。它也可能意味着 exec/RBAC、缺少 curl、路由、后端或其他故障。curl 超时通常返回退出代码 28，但在判定策略测试通过前，应结合成功的基线测试和仍可正常工作的前端，核对源/目标/端口以及被策略拒绝的流量。命名空间范围的规则并不能阻止其他策略独立允许流量。

<details>
<summary>预期结果和自我检查</summary>

应用策略前，两个客户端都能访问后端。策略生效后，前端仍可成功访问，而 outsider 被拒绝，并有相应的策略证据佐证。说明为什么缺少 EndpointSlices、DNS 错误或任意非零命令退出代码都不能证明隔离有效。此 L3/L4 策略不会添加 HTTP 解析。

</details>

## 3. Hubble 可见性测试

使用配置中已启用的 Hubble Relay/UI 和适当的 Hubble CLI。在单独的终端中运行此端口转发，然后在另一个终端中运行观察命令：

```bash
cilium hubble port-forward
```

```bash
hubble status
hubble observe --namespace cilium-net-lab --last 50
hubble observe --from-pod cilium-net-lab/outsider --verdict DROPPED --last 20
cilium hubble ui
```

观察期间生成新的请求。事件丢失/聚合和过滤条件都会影响可见内容。HTTP 流量需要受支持的 L7 代理/可见性配置；上述 L4 规则不会启用该配置。配置为拒绝的 L7 请求可能返回 HTTP 403，而不是产生数据包 DROPPED 事件。

<details>
<summary>预期结果和自我检查</summary>

Relay 可访问，流量显示出预期端点，负向测试的证据与其请求相符。说明为什么此仅包含 L4 的实验中没有 HTTP 记录，并不能证明 Hubble 出现故障。

</details>

## 4. 性能测试

运行[指南中维护的 `cilium connectivity perf` 示例](../../../networking/cilium/03-networking.md)，该示例会部署匹配的客户端/服务器工作负载。将同节点和跨节点结果分开记录，并记录节点位置、版本、路由 MTU 以及策略/加密设置。

之前的测试将互不相关的 `netperf-*` Pod 名称与 iperf3 镜像以及仅支持 TCP 的 Service 组合在一起。对于单独提供的 iperf3 配置，UDP 测试需要在配置的端口上同时使用 **TCP 控制流量和 UDP 数据流量**。仅仅指定 `-b 1G` 并不能证明实际传输速率达到 1 Gbit/s。

<details>
<summary>预期结果和自我检查</summary>

所有选定的测试工作负载都已就绪，且结果按场景标注。说明 TCP 请求/响应、连接创建、流吞吐量和 UDP 发送速率/丢包之间的区别。基准测试结果只适用于记录的配置，并不适用于所有 Cilium 模式或云环境。

</details>

## 5. 可选高级功能检查

分别通过单独准备且有文档说明的配置来启用各项功能。**检查期间不要卸载集群 CNI。** 单独一个 Helm 标志无法提供缺失的密钥、路由、API 可达性或 BGP 对等体。

| 功能 | 准备工作 | 观察内容 |
|---|---|---|
| kube-proxy replacement | `kubeProxyReplacement: true`、可访问的 `k8sServiceHost`/`k8sServicePort`、受支持的数据路径以及迁移计划 | 实际代理状态和 Service 流量；`strict` 不是当前有效值 |
| IPsec/WireGuard | 正确的加密模式、密钥处理方式、端口/MTU 以及受支持的流量范围 | 代理加密状态和实际的节点间路径 |
| BGP Control Plane | `bgpControlPlane.enabled: true`、版本匹配的 BGP 资源以及可访问的已配置对等体 | 会话和通告的路由；不能假定本地转发表已配置 |

选择相关节点上的代理：

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
cilium bgp peers
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
```

仅在配置了相应可选功能时，才解读这些功能的命令输出。在基础配置中，功能处于禁用/未配置状态是预期结果。独立的 `cilium bgp peers` 命令会报告集群节点状态；较旧的代理本地 BGP 命令已弃用。BGP 需要适用的 `cilium.io/v2` 配置资源；已移除的 `bgp.enabled` 和 `bgp.announce.loadbalancerIP` 设置不能证明会话已建立。

<details>
<summary>预期结果和自我检查</summary>

观察到的状态与所选配置一致，相关流量/路由证据也支持该结果。说明为什么“BGP 已建立”不能证明内部 Pod 路由正常，或者为什么仅凭加密状态不能证明所有流量路径都已加密。

</details>

## 6. 兼容性检查

```bash
kubectl version -o yaml
cilium version
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.kernelVersion}{"\n"}{end}'
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl -n kube-system get daemonset cilium -o yaml
```

将版本/功能与兼容矩阵进行比较，包括有文档说明的内核回补。在读取主机配置文件之前，先检查实际 CNI 设置和卷挂载：`/etc/cni/net.d/05-cilium.conf` 并非通用的容器路径或文件名。链式/自定义配置各不相同。仅仅存在某个文件并不能证明运行时兼容。

<details>
<summary>预期结果和自我检查</summary>

版本和内核要求符合平台要求，Pod 通过预期的 CNI 获得地址，且流量测试成功。说明 CNI 安装、IPAM 分配和端到端转发之间的区别。

</details>

## 7. 故障排查

```bash
cilium status --verbose
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
kubectl -n kube-system logs deployment/cilium-operator --tail=100
kubectl -n kube-system logs deployment/hubble-relay --tail=100
```

要检查前端端点，请先选择运行在前端所在节点上的代理：

```bash
kubectl -n cilium-net-lab get pod frontend -o wide
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get pod-name:cilium-net-lab:frontend
```

对于入口流量拒绝，还要检查后端代理/端点。对比预期策略、已生效状态、路由/后端健康状况和观察到的流量。不要使用已移除的 `policy trace` 命令，也不要使用未加引号的 `<pod-name>` shell 占位符解析人类可读表格。

如有需要，`cilium sysdump` 会收集诊断信息；分享前请检查归档中的日志/资源信息。`cilium clustermesh status` 仅适用于已配置的 Cluster Mesh；连接设置完成后，使用 `hubble status` 获取 Relay 状态。

<details>
<summary>预期结果和自我检查</summary>

证据对应正确的节点和端点，而不是 kubectl 碰巧选中的某个 DaemonSet Pod。说明哪些证据可以区分后端未就绪、路由故障、策略拒绝和缺少观察数据。

</details>

## 8. 清理

检查本次运行创建了哪些命名空间，并先保留结果：

```bash
kubectl get namespaces -l docs-audit-lab=cilium-networking-03
LAB_OWNER=$(kubectl get namespace cilium-net-lab -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-networking-03
kubectl delete namespace cilium-net-lab
```

如果运行了 CLI 测试套件，请单独验证所有权，再删除其生成的 `cilium-net-smoke-1` / `cilium-net-perf-1` 命名空间。不要批量删除无关命名空间，也不要将卸载 Cilium 作为应用清理步骤。按 Ctrl-C 停止本地端口转发。

<details>
<summary>预期结果和自我检查</summary>

仅删除本次运行的测试资源；已安装的 CNI 和其他工作负载仍正常运行。说明为什么反复卸载 CNI 并不是比较功能的有效方法。

</details>

## 验证限制和参考资料

已检查发布的 YAML/Helm 值、shell 语法以及 CLI/API 契约，但并未部署这些工作负载。主机重启后，没有声称执行过实时集群、镜像运行、Helm 渲染或吞吐量测试。必须在准备好的环境中验证准入控制、镜像架构/拉取策略、容量、实际数据路径和预期结果。

- [CLI 0.20.1 镜像默认值](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/defaults/defaults.go)、[测试 Deployment](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/connectivity/check/deployment.go)、[connectivity/perf 标志](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go)
- [Cilium 1.20.3 策略 API](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)、[L7 行为](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)、[BGP 配置](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)、[BGP CLI](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/bgp.go)、[代理命令](https://github.com/cilium/cilium/tree/v1.20.3/Documentation/cmdref)
- [Kubernetes 版本偏差](https://kubernetes.io/releases/version-skew-policy/)、[iperf3 调用方式](https://software.es.net/iperf/invoking.html)、[网络指南](../../../networking/cilium/03-networking.md)
