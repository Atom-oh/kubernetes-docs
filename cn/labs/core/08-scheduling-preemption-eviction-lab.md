# 调度器评分策略实验：LeastAllocated 与 MostAllocated

> **难度**：中级
> **预计时间**：30 分钟
> **最后更新**：2026 年 9 月 17 日

## 学习目标
- 搭建一个专用于本实验、可随时销毁的多节点 `kind` 集群
- 使用通过 `nodeName` 固定到节点的 Pod，在各节点上制造不均衡的基线 CPU 利用率
- 观察默认调度器在该基线下采用 `LeastAllocated` 的放置行为
- 部署一个配置了 `NodeResourcesFit` 的 `MostAllocated` 评分策略的第二调度器，并比较放置决策
- 解释为什么 `MostAllocated` 的装箱策略有利于与 Karpenter / Cluster Autoscaler 并行运行的批处理工作负载

## 前提条件
- [ ] `kubectl`、`docker`（或其他 kind 支持的容器运行时）
- [ ] `kind` v0.20+（如果本地缺少，本实验会安装）
- [ ] 已完成[调度、抢占与驱逐](../../core/08-scheduling-preemption-eviction.md)，尤其是 [NodeResourcesFit 评分策略](../../core/08-scheduling-preemption-eviction.md#noderesourcesfit-scoring-strategy-leastallocated-vs-mostallocated)一节

本实验会创建自己的临时多节点 `kind` 集群，不会复用现有集群，因为实验需要至少 3 个工作节点，并且要能分别观察各节点上的 CPU 分配。实验结束时会删除所有资源。请在同一个 shell 中按顺序运行命令；任何步骤失败时都应停止。

```bash
SCHED_LAB_DIR=$(mktemp -d /tmp/k8s-docs-sched.XXXXXX)
: "${SCHED_LAB_DIR:?mktemp failed}"
cd "$SCHED_LAB_DIR"

if ! command -v kind >/dev/null 2>&1; then
  KIND_ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
  curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-${KIND_ARCH}"
  chmod +x ./kind
  SCHED_LAB_KIND=./kind
else
  SCHED_LAB_KIND=kind
fi
"$SCHED_LAB_KIND" version
```

---

## 实验 1：创建测试集群并设置不均衡基线

### 步骤

**步骤 1.1：创建包含 3 个工作节点的 kind 集群**
```bash
cat > "$SCHED_LAB_DIR/kind-config.yaml" << 'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: scheduler-strategy-lab
nodes:
- role: control-plane
- role: worker
- role: worker
- role: worker
EOF

export KUBECONFIG="$SCHED_LAB_DIR/kubeconfig"
"$SCHED_LAB_KIND" create cluster --config "$SCHED_LAB_DIR/kind-config.yaml"
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"  cpu="}{.status.allocatable.cpu}{"\n"}{end}'
```
所有四个节点报告的可分配 CPU 都相同（kind 节点是共享主机的容器，因此可分配资源反映主机规格，而非真实的逐节点硬件划分；每个节点可能显示类似 `cpu=16` 的值；具体数字取决于你的机器）。

**步骤 1.2：记录工作节点名称**
```bash
mapfile -t SCHED_LAB_WORKERS < <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep -v control-plane)
printf 'Workers: %s\n' "${SCHED_LAB_WORKERS[*]}"
kubectl create namespace sched-lab
```

**步骤 1.3：固定填充 Pod，制造不均衡的 CPU 利用率**

我们使用 `spec.nodeName`（它会完全绕过调度器），将三个工作节点的起始利用率设置为不同水平：第一个工作节点为 75%，第二个约为 37%，第三个为 0%。

```bash
{
  for i in $(seq 1 12); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-busy-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[0]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
  for i in $(seq 1 6); do
cat << EOF
apiVersion: v1
kind: Pod
metadata:
  name: filler-medium-${i}
  namespace: sched-lab
  labels: { role: filler }
spec:
  nodeName: ${SCHED_LAB_WORKERS[1]}
  containers:
  - name: filler
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
---
EOF
  done
} > "$SCHED_LAB_DIR/filler-pods.yaml"

kubectl apply -f "$SCHED_LAB_DIR/filler-pods.yaml"
kubectl -n sched-lab wait --for=condition=Ready pod -l role=filler --timeout=120s
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 预期结果
你应该看到大致如下的情况：
- `${SCHED_LAB_WORKERS[0]}`（记作 **A**）：请求 12000m，约 75%
- `${SCHED_LAB_WORKERS[1]}`（记作 **B**）：请求 6000m，约 37%
- `${SCHED_LAB_WORKERS[2]}`（记作 **C**）：约 0m，0%

确切百分比取决于 kind 报告的主机 CPU 数量；关键是顺序为 A > B > C。

---

## 实验 2：观察默认调度器（`LeastAllocated`）

### 步骤

**步骤 2.1：使用默认调度器调度 6 个新 Pod**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-default-${i}
  namespace: sched-lab
  labels: { role: batch-default }
spec:
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-default --timeout=60s
```

**步骤 2.2：记录 Pod 被放置的位置**
```bash
kubectl -n sched-lab get pods -l role=batch-default -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 预期结果
6 个 Pod 都会落在节点 **C**（最空闲的节点）上，使其利用率大致达到与 B 相同的水平。这就是 `LeastAllocated` 的效果：默认调度器会不断选择空闲容量最多的节点来放置每个新 Pod，因此各节点利用率会趋于一致，而不是将负载集中在少数节点上。完成此步骤后，三个工作节点都会承载一定负载，不再有完全空闲、适合缩容的节点。

---

## 实验 3：部署采用 `MostAllocated` 的第二个调度器并进行比较

### 步骤

**步骤 3.1：重置（删除实验 2 中调度的 Pod，保留填充基线）**
```bash
kubectl -n sched-lab delete pod -l role=batch-default --wait=true
```

**步骤 3.2：部署配置为采用 `MostAllocated` 的第二个 kube-scheduler**
```bash
cat > "$SCHED_LAB_DIR/most-allocated-scheduler.yaml" << 'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-kube-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:kube-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: most-allocated-scheduler-as-volume-scheduler
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:volume-scheduler }
subjects:
- kind: ServiceAccount
  name: most-allocated-scheduler
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: most-allocated-scheduler-config
  namespace: kube-system
data:
  config.yaml: |
    apiVersion: kubescheduler.config.k8s.io/v1
    kind: KubeSchedulerConfiguration
    leaderElection:
      leaderElect: false
    profiles:
    - schedulerName: most-allocated-scheduler
      pluginConfig:
      - name: NodeResourcesFit
        args:
          scoringStrategy:
            type: MostAllocated
            resources:
            - { name: cpu, weight: 1 }
            - { name: memory, weight: 1 }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: most-allocated-scheduler
  namespace: kube-system
spec:
  replicas: 1
  selector: { matchLabels: { app: most-allocated-scheduler } }
  template:
    metadata: { labels: { app: most-allocated-scheduler } }
    spec:
      serviceAccountName: most-allocated-scheduler
      containers:
      - name: kube-scheduler
        image: registry.k8s.io/kube-scheduler:v1.37.0
        command: ["kube-scheduler", "--config=/etc/kubernetes/scheduler-config/config.yaml", "-v=2"]
        volumeMounts:
        - { name: config, mountPath: /etc/kubernetes/scheduler-config }
      volumes:
      - name: config
        configMap: { name: most-allocated-scheduler-config }
EOF

kubectl apply -f "$SCHED_LAB_DIR/most-allocated-scheduler.yaml"
kubectl -n kube-system rollout status deployment/most-allocated-scheduler --timeout=120s
```
将 `image: registry.k8s.io/kube-scheduler:v1.37.0` 与集群的实际次要版本保持一致；使用 `kubectl version` 检查。与 API 服务器相差超过一个次要版本的调度器二进制文件可能无法启动，或出现不可预测的行为。

**步骤 3.3：通过 `schedulerName` 使用同样的 6 个 Pod 进行调度**
```bash
for i in $(seq 1 6); do
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: batch-mostalloc-${i}
  namespace: sched-lab
  labels: { role: batch-mostalloc }
spec:
  schedulerName: most-allocated-scheduler
  containers:
  - name: batch
    image: registry.k8s.io/pause:3.10
    resources:
      requests: { cpu: "1000m", memory: "64Mi" }
      limits: { cpu: "1000m", memory: "64Mi" }
EOF
done
kubectl -n sched-lab wait --for=condition=Ready pod -l role=batch-mostalloc --timeout=60s
```

**步骤 3.4：记录放置位置并进行比较**
```bash
kubectl -n sched-lab get pods -l role=batch-mostalloc -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName
kubectl describe nodes "${SCHED_LAB_WORKERS[@]}" | grep -E "^Name:|cpu\s+[0-9]"
```

### 预期结果和参考数据

编写本实验时，曾在一个每个节点有 16 个可分配 CPU 的 3 工作节点 kind 集群上完整执行过以下流程一次（`kubectl version` 报告 `v1.37.0`）：

| 调度器 / 策略 | 6 个新 Pod 的落点 | 最终 CPU 利用率（A / B / C） |
|---|---|---|
| 默认（`LeastAllocated`） | 6 个全部位于节点 C | 75% / 37% / 37%（三个节点均有负载） |
| `MostAllocated` | 节点 A 上 3 个，节点 B 上 3 个 | 93% / 56% / 0%（节点 C 完全空闲） |

绝对百分比会因主机 CPU 数量不同而变化，但应能复现这种**模式**：`LeastAllocated` 会填充空闲节点，直到其利用率接近其他节点；`MostAllocated` 则会继续向已较繁忙的节点添加 Pod，并让空闲节点保持不动。接下来，Cluster Autoscaler 或 Karpenter 整合流程恰好会终止这个空闲节点。因此，对于与自动扩缩器并行运行的批处理 / 短时作业工作负载，`MostAllocated` 更合适；对于希望每个节点都保留余量的长时间运行、对延迟敏感的服务，`LeastAllocated` 仍是更安全的默认选择。

---

## 清理
```bash
unset KUBECONFIG
"$SCHED_LAB_KIND" delete cluster --name scheduler-strategy-lab --kubeconfig "$SCHED_LAB_DIR/kubeconfig"
rm -rf -- "$SCHED_LAB_DIR"
unset SCHED_LAB_DIR SCHED_LAB_KIND SCHED_LAB_WORKERS
```

## 参考资料和验证范围

- [调度器配置：Kubernetes 文档](https://kubernetes.io/docs/reference/scheduling/config/)
- [NodeResourcesFit 评分策略](https://kubernetes.io/docs/reference/config-api/kube-scheduler-config.v1/)
- [配置多个调度器](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-multiple-schedulers/)

编写本实验时，已在隔离且可随时销毁的 `kind` 集群上端到端执行了全部步骤（创建集群、部署填充 Pod、分别运行两种调度器流程以及清理）；没有触及共享集群或云资源。上方结果表记录的是实际运行中观察到的输出，并非假设性预测。

## 后续步骤
- [调度、抢占与驱逐测验](../../quizzes/core/08-scheduling-preemption-eviction-quiz.md)
- [构建自定义调度器](../../scheduling/01-custom-scheduler-part1.md)
