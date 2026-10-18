# Services 和网络实验指南

> **难度**：中级
> **预计时间**：45 分钟
> **最后更新**：September 11, 2026

## 学习目标
- 创建 ClusterIP 和 NodePort Services
- 练习通过 Services 访问 Pods
- 验证基于 DNS 的服务发现

## 先决条件
- [ ] kubectl、Kubernetes 集群（minikube/kind）
- [ ] 已完成 [Services 和网络](../../core/03-services-networking.md)学习

请使用一次性 kind/minikube 集群、相匹配的 kubectl context、创建 namespaces 的权限，以及可用的集群 DNS/CNI/registry 访问。网络策略必须允许这些测试流量。NodePort 可能会向外暴露节点网络接口，因此请使用预期的测试网络。在同一个 Bash 会话中运行；本次审查未执行集群/流量测试。

```bash
SERVICE_LAB_DIR=$(mktemp -d /tmp/k8s-docs-services.XXXXXX)
: "${SERVICE_LAB_DIR:?mktemp failed}"
SERVICE_LAB_CONTEXT=$(kubectl config current-context)
: "${SERVICE_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$SERVICE_LAB_CONTEXT"
SERVICE_LAB_CANDIDATE=$(basename "$SERVICE_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset SERVICE_LAB_NAMESPACE SERVICE_LAB_CLIENT_NAMESPACE SERVICE_LAB_CLIENT_UID
if SERVICE_LAB_UID=$(kubectl --context "$SERVICE_LAB_CONTEXT" create namespace "$SERVICE_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_NAMESPACE=$SERVICE_LAB_CANDIDATE
else
  printf 'Namespace creation failed; stop before resource operations\n' >&2
fi
service_kubectl() {
  kubectl --context "${SERVICE_LAB_CONTEXT:?}" --namespace "${SERVICE_LAB_NAMESPACE:?}" "$@"
}
```

---

## 练习 1：ClusterIP Service

### 步骤

**步骤 1.1：创建后端 Deployment**
```bash
cat > "${SERVICE_LAB_DIR:?}/web-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/web-deployment.yaml"
service_kubectl rollout status deployment/web --timeout=120s
```

**步骤 1.2：创建 ClusterIP Service**
```bash
cat > "${SERVICE_LAB_DIR:?}/clusterip-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-clusterip
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/clusterip-svc.yaml"
service_kubectl get service web-clusterip
```

**步骤 1.3：测试从集群内部访问**
```bash
service_kubectl run http-check --image=busybox:1.38.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- sh -c '
for attempt in 1 2 3 4 5; do
  wget -T 5 -qO- "$1" && exit 0
  sleep 1
done
exit 1
' sh http://web-clusterip/
```
<details>
<summary>需要提示吗？</summary>

- ClusterIP 提供内部虚拟地址；它不是安全边界，路由可达性取决于网络。
- 完整 DNS 格式为 `<service>.<namespace>.svc.<cluster-domain>`；`cluster.local` 只是常见默认值。
- 使用常规 Pod DNS 搜索设置时，同一 namespace 中可以使用 `<service>`，其他 namespace 中可以使用 `<service>.<namespace>`。
</details>

### 验证
EndpointSlices 已取代弃用的 Endpoints 视图。确认就绪后端地址；更新是异步的，且切片/地址族可能会拆分结果。三个就绪副本并不意味着每种输出格式中都恰好有三行。

```bash
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip -o wide
service_kubectl get endpointslices -l kubernetes.io/service-name=web-clusterip \
  -o jsonpath='{range .items[*].endpoints[*]}{.addresses}{" ready="}{.conditions.ready}{"\n"}{end}'
```

---

## 练习 2：NodePort Service

### 步骤

**步骤 2.1：创建 NodePort Service**
```bash
cat > "${SERVICE_LAB_DIR:?}/nodeport-svc.yaml" << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web-nodeport
spec:
  type: NodePort
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: http
EOF
service_kubectl apply -f "$SERVICE_LAB_DIR/nodeport-svc.yaml"
SERVICE_LAB_NODE_PORT=$(service_kubectl get service web-nodeport -o jsonpath='{.spec.ports[0].nodePort}')
: "${SERVICE_LAB_NODE_PORT:?No allocated NodePort}"
service_kubectl get service web-nodeport
```

**步骤 2.2：从外部访问**
NodePort 会自动分配，而不是假设 30080 未被占用。Service 类型/端口列表只能证明配置情况，不能证明客户端可以访问。只有在路由、nodePortAddresses 和防火墙策略允许的情况下，才使用直接访问节点地址的命令。

```bash
printf 'Allocated NodePort: %s\n' "${SERVICE_LAB_NODE_PORT:?}"
kubectl --context "${SERVICE_LAB_CONTEXT:?}" get nodes -o wide

# Use only an address reachable from this client and permitted by node/firewall policy.
: "${SERVICE_LAB_NODE_ADDRESS:?Set a reachable node address}"
case "$SERVICE_LAB_NODE_ADDRESS" in
  *:*) SERVICE_LAB_NODE_URL_HOST="[$SERVICE_LAB_NODE_ADDRESS]" ;;
  *) SERVICE_LAB_NODE_URL_HOST=$SERVICE_LAB_NODE_ADDRESS ;;
esac
curl --disable --noproxy '*' --fail --show-error --silent --max-time 5 \
  "http://$SERVICE_LAB_NODE_URL_HOST:$SERVICE_LAB_NODE_PORT/"
```

在 minikube 上，请选择匹配的 profile。某些 Docker 驱动平台需要在另一个终端中运行 service 命令以保持隧道开启；请使用该命令打印的 URL。不要隐藏错误，也不要用硬编码端口替代。如果要从主机访问 kind，预先配置的 extraPortMappings 必须与 Service 的 nodePort 相匹配。如果无法访问节点 IP，可以另行选择 `service_kubectl port-forward --address=127.0.0.1 service/web-nodeport 18080:80` 来测试应用，但这**不会**验证 NodePort 数据路径。

```bash
# Only for minikube: the profile must correspond to SERVICE_LAB_CONTEXT.
: "${SERVICE_LAB_MINIKUBE_PROFILE:?Set the matching minikube profile}"
minikube --profile "$SERVICE_LAB_MINIKUBE_PROFILE" \
  service web-nodeport --namespace "${SERVICE_LAB_NAMESPACE:?}" --url
```
### 验证
```bash
service_kubectl get service web-nodeport -o jsonpath='{.spec.type}{"\n"}{.spec.ports[0].nodePort}{"\n"}'
```

---

## 练习 3：DNS 服务发现

### 步骤

**步骤 3.1：DNS 查询测试**
```bash
service_kubectl run dns-check --image=busybox:1.38.0 \
  --overrides='{"spec":{"automountServiceAccountToken":false}}' \
  --rm -i --restart=Never --pod-running-timeout=120s --command -- nslookup web-clusterip
service_kubectl get service web-clusterip -o jsonpath='{.spec.clusterIP}{"\n"}'
```

解析器 IP、应答 IP 和集群域名取决于集群。对于这个常规 ClusterIP Service，DNS 应解析为上方显示的 Service 虚拟 IP，而不是各个后端 Pod IP。完整名称包含本实验的 namespace，而不是硬编码的默认 namespace。

**步骤 3.2：从不同 namespace 访问**
```bash
SERVICE_LAB_CLIENT_CANDIDATE="${SERVICE_LAB_NAMESPACE:?}-client"
unset SERVICE_LAB_CLIENT_NAMESPACE
if SERVICE_LAB_CLIENT_UID=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" create namespace "$SERVICE_LAB_CLIENT_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  SERVICE_LAB_CLIENT_NAMESPACE=$SERVICE_LAB_CLIENT_CANDIDATE
  kubectl --context "$SERVICE_LAB_CONTEXT" --namespace "$SERVICE_LAB_CLIENT_NAMESPACE" \
    run cross-ns-check --image=busybox:1.38.0 \
    --overrides='{"spec":{"automountServiceAccountToken":false}}' \
    --rm -i --restart=Never --pod-running-timeout=120s --command -- \
    wget -T 5 -qO- "http://web-clusterip.$SERVICE_LAB_NAMESPACE/"
else
  printf 'Client namespace was not created; no cross-namespace test was run\n' >&2
fi
```

<details>
<summary>需要提示吗？</summary>

- 使用标准 DNS 搜索路径时，跨 namespace 访问只需 `service.namespace`；也可以使用完整集群域名。
- CoreDNS 或配置的集群 DNS 实现会发布 Service 记录。
- 使用 `kubectl get pods -n kube-system -l k8s-app=kube-dns` 检查 DNS Pods
</details>

---

## 清理
```bash
delete_service_lab_namespace() {
  local name="$1" expected_uid="$2" current_uid
  [[ -n "$name" && -n "$expected_uid" ]] || return 0
  current_uid=$(kubectl --context "${SERVICE_LAB_CONTEXT:?}" get namespace "$name" -o jsonpath='{.metadata.uid}') || return 0
  if [ "$current_uid" = "$expected_uid" ]; then
    kubectl --context "$SERVICE_LAB_CONTEXT" delete namespace "$name" --timeout=120s
  else
    printf 'Namespace identity changed; deletion skipped: %s\n' "$name"
  fi
}
delete_service_lab_namespace "${SERVICE_LAB_CLIENT_NAMESPACE:-}" "${SERVICE_LAB_CLIENT_UID:-}"
delete_service_lab_namespace "${SERVICE_LAB_NAMESPACE:-}" "${SERVICE_LAB_UID:-}"
if [[ -n ${SERVICE_LAB_DIR:-} ]]; then
  rm -f -- "$SERVICE_LAB_DIR/web-deployment.yaml" "$SERVICE_LAB_DIR/clusterip-svc.yaml" "$SERVICE_LAB_DIR/nodeport-svc.yaml"
  rmdir -- "$SERVICE_LAB_DIR"
fi
unset -f service_kubectl delete_service_lab_namespace
```


## 参考资料和验证范围

* [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
* [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
* [Services 和 Pods 的 DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
* [minikube 访问](https://minikube.sigs.k8s.io/docs/handbook/accessing/)
* [kind 端口映射](https://kind.sigs.k8s.io/docs/user/configuration/#extra-port-mappings)

验证仅包括本地 manifest/命令检查，并非有记录的 CNI、DNS 或 NodePort 测试。临时客户端使用显式命令，无需 service-account tokens。

## 后续步骤
- [Services 和网络测验](../../quizzes/core/03-services-networking-quiz.md)
- [存储实验](./04-storage-lab.md)
