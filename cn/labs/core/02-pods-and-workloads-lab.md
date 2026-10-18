# Pod 和工作负载实验指南

> **难度**：初级
> **预计用时**：50 分钟
> **最后更新**：September 11, 2026

## 学习目标
- 使用 YAML 创建和管理 Pod
- 部署和扩缩 Deployment
- 执行滚动更新和回滚

## 先决条件
- [ ] 已安装 kubectl 并可访问集群（minikube 或 kind）
- [ ] 已完成 [Pod 和工作负载](../../core/02-pods-and-workloads.md)学习

使用已有的临时 kind/minikube 集群，并确保你有权限创建实验命名空间和拉取示例镜像。运行设置命令前，请确认所选上下文。整个过程请保持在同一个 Bash 会话中；此包装函数会固定上下文和命名空间。运行这些步骤会对集群进行实际更改；本次审计未执行任何集群操作。

```bash
WORKLOADS_LAB_DIR=$(mktemp -d /tmp/k8s-docs-workloads.XXXXXX)
: "${WORKLOADS_LAB_DIR:?mktemp failed}"
WORKLOADS_LAB_CONTEXT=$(kubectl config current-context)
: "${WORKLOADS_LAB_CONTEXT:?No current context selected}"
printf 'Selected context: %s\n' "$WORKLOADS_LAB_CONTEXT"
WORKLOADS_LAB_CANDIDATE=$(basename "$WORKLOADS_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
unset WORKLOADS_LAB_NAMESPACE WORKLOADS_LAB_GOOD_REVISION
if WORKLOADS_LAB_UID=$(kubectl --context "$WORKLOADS_LAB_CONTEXT" create namespace "$WORKLOADS_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  WORKLOADS_LAB_NAMESPACE=$WORKLOADS_LAB_CANDIDATE
else
  printf 'Namespace creation failed; do not continue with workload commands\n' >&2
fi
workload_kubectl() {
  kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" \
    --namespace "${WORKLOADS_LAB_NAMESPACE:?Create the lab namespace first}" "$@"
}
```

---

## 练习 1：创建和管理 Pod

### 步骤

**步骤 1.1：编写 Pod YAML**
```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: nginx-lab
  labels:
    app: nginx
    env: lab
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
        memory: 64Mi
        cpu: 100m
      limits:
        memory: 128Mi
        cpu: 200m
    readinessProbe:
      httpGet:
        path: /
        port: http
      periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-pod.yaml"
```

**步骤 1.2：检查 Pod 状态**
仅处于 Running 阶段并不代表已就绪。在查看日志或执行命令之前，请等待已配置的 HTTP 就绪探针通过；如果失败，应检查原因，而不要将超时视为成功。

```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
workload_kubectl describe pod nginx-lab
workload_kubectl logs nginx-lab
```

**步骤 1.3：访问 Pod 内部**
```bash
workload_kubectl exec -it nginx-lab -- sh
# Inside the container:
nginx -v
ls /usr/share/nginx/html/
exit
```

### 验证
```bash
workload_kubectl wait --for=condition=Ready pod/nginx-lab --timeout=120s
workload_kubectl get pod nginx-lab -o wide
```

---

## 练习 2：Deployment

### 步骤

**步骤 2.1：创建 Deployment**
在故意使用错误镜像进行滚动更新时，Deployment 会通过 maxUnavailable0 和 maxSurge1 保留旧的就绪副本。需要预留容量来容纳 surge 和正在终止的 Pod，以及独立的 Pod。但这并不能保证在其他故障发生时仍可用。

```bash
cat > "${WORKLOADS_LAB_DIR:?}/nginx-deployment.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
  replicas: 3
  revisionHistoryLimit: 5
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: nginx-deploy
  template:
    metadata:
      labels:
        app: nginx-deploy
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
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
        readinessProbe:
          httpGet:
            path: /
            port: http
          periodSeconds: 3
EOF
workload_kubectl apply -f "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
```

**步骤 2.2：检查 Deployment 状态**
```bash
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get deployment nginx-deploy
workload_kubectl get replicasets,pods -l app=nginx-deploy
```

**步骤 2.3：扩缩**
```bash
workload_kubectl scale deployment nginx-deploy --replicas=5
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
workload_kubectl get pods -l app=nginx-deploy
```

<details>
<summary>需要提示吗？</summary>

- `kubectl get pods -w` 可实时监控变化
- ReplicaSet 由 Deployment 自动管理
- 使用 `-l` 选项按标签筛选
</details>

### 验证
```bash
READY=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.status.readyReplicas}')
printf 'Ready replicas: %s\n' "$READY"
[ "$READY" = "5" ]
```

---

## 练习 3：滚动更新

### 步骤

**步骤 3.1：更新镜像**
此操作更换的是同一受维护 NGINX 版本的基础镜像变体，而不是旧的不受支持的 NGINX 版本。`kubernetes.io/change-cause` 用于记录操作意图，不必使用已弃用的 --record 标志。请记录已完成的修订版本，以便在回滚练习中使用。

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="NGINX 1.30.6 Debian to Alpine variant" --overwrite
unset WORKLOADS_LAB_GOOD_REVISION
if workload_kubectl set image deployment/nginx-deploy nginx=nginx:1.30.6-alpine &&
   workload_kubectl rollout status deployment/nginx-deploy --timeout=120s; then
  WORKLOADS_LAB_GOOD_REVISION=$(workload_kubectl get deployment nginx-deploy \
    -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')
  : "${WORKLOADS_LAB_GOOD_REVISION:?No completed revision recorded}"
else
  printf 'Healthy rollout not confirmed; stop before the failure/rollback exercise\n' >&2
fi
```

**步骤 3.2：检查更新历史**
```bash
workload_kubectl rollout history deployment/nginx-deploy
workload_kubectl get replicasets -l app=nginx-deploy -o wide
```

### 验证
```bash
workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
# Expected configured image: nginx:1.30.6-alpine
```

---

## 练习 4：回滚

### 步骤

**步骤 4.1：使用无效镜像更新（故意制造错误）**
保留的 .invalid 注册表用于在这个隔离实验中故意触发失败。滚动更新超时也可能是由调度、配额或 API 问题造成的，因此请确认 Pod 事件和状态。回滚会恢复保留的 Pod 模板，但不会恢复外部数据、ConfigMap/Secret 内容或数据库迁移。

```bash
workload_kubectl annotate deployment/nginx-deploy \
  kubernetes.io/change-cause="Intentional lab image-pull failure" --overwrite
workload_kubectl set image deployment/nginx-deploy nginx=registry.invalid/training/nginx:unavailable
if workload_kubectl rollout status deployment/nginx-deploy --timeout=30s; then
  printf 'Unexpected completion; inspect which image is running\n'
else
  printf 'Rollout did not complete; inspect Pod status/events to identify the cause\n'
fi
```

**步骤 4.2：检查错误并回滚**
```bash
workload_kubectl get pods -l app=nginx-deploy
workload_kubectl describe deployment nginx-deploy
workload_kubectl get events --sort-by=.metadata.creationTimestamp
workload_kubectl rollout undo deployment/nginx-deploy \
  --to-revision="${WORKLOADS_LAB_GOOD_REVISION:?Complete Step 3.1 first}"
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

### 验证
```bash
IMAGE=$(workload_kubectl get deployment nginx-deploy -o jsonpath='{.spec.template.spec.containers[0].image}')
printf 'Current image: %s\n' "$IMAGE"
[ "$IMAGE" = "nginx:1.30.6-alpine" ]
workload_kubectl rollout status deployment/nginx-deploy --timeout=120s
```

---

## 清理
```bash
# Delete the isolated lab namespace only if its recorded identity still matches.
if [[ -n ${WORKLOADS_LAB_NAMESPACE:-} && -n ${WORKLOADS_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${WORKLOADS_LAB_CONTEXT:?}" get namespace "$WORKLOADS_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$WORKLOADS_LAB_UID" ]; then
    kubectl --context "$WORKLOADS_LAB_CONTEXT" delete namespace "$WORKLOADS_LAB_NAMESPACE" --timeout=120s
  else
    printf 'Namespace missing or identity changed; automatic deletion skipped\n'
  fi
fi
if [[ -n ${WORKLOADS_LAB_DIR:-} ]]; then
  rm -f -- "$WORKLOADS_LAB_DIR/nginx-pod.yaml" "$WORKLOADS_LAB_DIR/nginx-deployment.yaml"
  rmdir -- "$WORKLOADS_LAB_DIR"
fi
unset -f workload_kubectl
```


## 参考资料和验证范围

* [Deployment、滚动更新和回滚](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
* [kubectl rollout undo](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_undo/)
* [就绪探针和存活探针](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

清单和命令已在本地检查。本次审计未执行集群部署、镜像拉取、扩缩、回滚或命名空间删除。

## 后续步骤
- [Pod 和工作负载测验](../../quizzes/core/02-pods-and-workloads-quiz.md)
- [Service 和网络实验](./03-services-networking-lab.md)
