# ConfigMap 和 Secret 实验指南

> **难度**：初级
> **预计时间**：35 分钟
> **最后更新**：2026 年 9 月 11 日

## 学习目标
- 创建 ConfigMap 并在 Pod 中使用
- 创建 Secret 并安全地注入
- 比较环境变量和卷挂载方式

## 先决条件
- [ ] kubectl、Kubernetes 集群
- [ ] 已完成[配置](../../core/05-configuration-secrets.md)学习

使用 Bash 和现有的临时 kind/minikube 集群。在同一个 shell 中运行这些步骤，如果某个先决命令失败，就停止操作。在创建命名空间之前，确认已选择预期的实验集群。以下凭据均为公开的虚构数据；本实验不会连接数据库。

```bash
CONFIG_LAB_DIR=$(mktemp -d /tmp/k8s-docs-config.XXXXXX)
: "${CONFIG_LAB_DIR:?mktemp failed}"
CONFIG_LAB_CONTEXT=$(kubectl config current-context)
: "${CONFIG_LAB_CONTEXT:?No context selected}"
printf 'Selected context: %s\n' "$CONFIG_LAB_CONTEXT"
unset CONFIG_LAB_NAMESPACE CONFIG_LAB_UID
CONFIG_LAB_CANDIDATE=$(basename "$CONFIG_LAB_DIR" | tr '[:upper:].' '[:lower:]-')
if CONFIG_LAB_UID=$(kubectl --context "$CONFIG_LAB_CONTEXT" create namespace "$CONFIG_LAB_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  CONFIG_LAB_NAMESPACE=$CONFIG_LAB_CANDIDATE
fi
: "${CONFIG_LAB_NAMESPACE:?Namespace creation failed}"
: "${CONFIG_LAB_UID:?Namespace UID missing}"
config_kubectl() {
  kubectl --context "${CONFIG_LAB_CONTEXT:?}" --namespace "${CONFIG_LAB_NAMESPACE:?}" "$@"
}
```

---

## 练习 1：创建和使用 ConfigMap

### 步骤

**步骤 1.1：创建 ConfigMap**
```bash
# Create from literal values
config_kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

config_kubectl get configmap app-config -o yaml
```

**步骤 1.2：从文件创建 ConfigMap**
```bash
cat > "${CONFIG_LAB_DIR:?}/app.properties" << 'EOF'
database.host=mysql
database.port=3306
database.name=myapp
EOF

config_kubectl create configmap app-properties --from-file="${CONFIG_LAB_DIR:?}/app.properties"
config_kubectl describe configmap app-properties
```

这些属性是示例配置文本。此操作不会创建或验证 MySQL Service、数据库或身份验证流程。

**步骤 1.3：将 ConfigMap 注入为环境变量**
```bash
cat > "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-env-demo
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.38.0
    command: ["sh", "-ec", "echo APP_ENV=$APP_ENV LOG_LEVEL=$LOG_LEVEL; exec sleep 3600"]
    envFrom:
    - configMapRef:
        name: app-config
EOF

config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml"
config_kubectl wait --for=condition=ready pod/config-env-demo --timeout=120s
config_kubectl logs config-env-demo
```

预期输出：
```
APP_ENV=production LOG_LEVEL=info
```

**步骤 1.4：将 ConfigMap 挂载为卷**
```bash
cat > "${CONFIG_LAB_DIR:?}/configmap-vol-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: config-vol-demo
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: busybox:1.38.0
    command: ["sh", "-ec", "cat /config/app.properties; exec sleep 3600"]
    volumeMounts:
    - name: config-volume
      mountPath: /config
      readOnly: true
  volumes:
  - name: config-volume
    configMap:
      name: app-properties
EOF

config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-vol-pod.yaml"
config_kubectl wait --for=condition=ready pod/config-vol-demo --timeout=120s
config_kubectl logs config-vol-demo
```

<details>
<summary>需要提示吗？</summary>

- `envFrom` 会将此处使用的 ConfigMap 键导入为环境变量。
- 每个挂载的键都会变成一个文件。更新会通过 kubelet 同步/缓存机制最终传播，但不会立即生效。
- `subPath` 挂载不会接收更新。环境变量在容器启动时固定；替换 Pod 才能加载新值。只读取一次文件的进程也需要显式重新加载或重启。
</details>

---

## 练习 2：Secret 管理

### 步骤

**步骤 2.1：创建 Secret**
```bash
# Public dummy values only. Do not substitute real credentials in shell history.
(
  umask 077
  printf '%s' 'lab-user' > "${CONFIG_LAB_DIR:?}/DB_USER"
  printf '%s' 'not-a-real-password' > "${CONFIG_LAB_DIR:?}/DB_PASSWORD"
)
config_kubectl create secret generic db-secret \
  --from-file=DB_USER="${CONFIG_LAB_DIR:?}/DB_USER" \
  --from-file=DB_PASSWORD="${CONFIG_LAB_DIR:?}/DB_PASSWORD"
# Show key names only, never their values or encoded contents.
config_kubectl get secret db-secret \
  -o go-template='{{range $key, $value := .data}}{{printf "%s\n" $key}}{{end}}'
```

只应显示键名。使用文件输入可避免将真实凭据嵌入命令参数；这些本地私有文件仍包含明文，实验结束后必须删除。Secret API 响应中的 Base64 是编码，不是加密。静态加密、最小权限 RBAC 和轮换需要单独配置。拥有在此命名空间中创建 Pod 的权限，也可能暴露其中的 Secret。

**步骤 2.2：将 Secret 注入 Pod**
非 root 容器会检查值是否存在，但不会打印用户名、密码或长度。Secret 卷为只读；`0440` 是 YAML 中的八进制模式（在 JSON 中为十进制 `288`），`fsGroup` 会授予此容器组读取权限。此处展示两种注入方式以供比较，并不意味着应用需要重复保存凭据。

```bash
cat > "${CONFIG_LAB_DIR:?}/secret-pod.yaml" << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: secret-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 2000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -ec
    - |
      test -n "$DB_USER"
      test -n "$DB_PASSWORD"
      test -s /run/credentials/DB_USER
      test -s /run/credentials/DB_PASSWORD
      printf 'Dummy credentials available through environment and files\n'
      exec sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
    env:
    - name: DB_USER
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_USER
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: DB_PASSWORD
    volumeMounts:
    - name: credentials
      mountPath: /run/credentials
      readOnly: true
  volumes:
  - name: credentials
    secret:
      secretName: db-secret
      defaultMode: 0440
EOF
config_kubectl apply -f "${CONFIG_LAB_DIR:?}/secret-pod.yaml"
config_kubectl wait --for=condition=Ready pod/secret-demo --timeout=120s
config_kubectl logs secret-demo
```

预期输出：
```
Dummy credentials available through environment and files
```

**步骤 2.3：使用离线虚构文本演示 Base64**
```bash
printf '%s' 'lab-only' | base64 | base64 -d
printf '\n'
```

<details>
<summary>需要提示吗？</summary>

- 此离线示例只会打印公开字符串 `lab-only`；切勿在共享终端或日志中解码真实 Secret。
- 更新 Secret 不会更改现有容器中的环境变量。常规 Secret 卷投影最终会更新，但应用必须重新读取文件；`subPath` 不会更新。
- 外部 Secret 存储/控制器需要单独配置身份、授权和轮换。安装工具本身并不能建立这些保障。
</details>

---

## 练习 3：比较环境变量和卷挂载

### 步骤

**步骤 3.1：更新 ConfigMap 并比较正在运行的 Pod**
```bash
config_kubectl patch configmap app-config --type=merge \
  -p '{"data":{"LOG_LEVEL":"debug"}}'
config_kubectl patch configmap app-properties --type=merge \
  -p '{"data":{"app.properties":"database.host=mysql\ndatabase.port=3306\ndatabase.name=myapp_v2\n"}}'

# The existing container still has LOG_LEVEL=info.
config_kubectl exec config-env-demo -- sh -c 'printf "LOG_LEVEL=%s\n" "$LOG_LEVEL"'

# Reopen the file up to 60 times, with five seconds between attempts.
CONFIG_LAB_PROJECTED=false
for ((attempt=1; attempt<=60; attempt++)); do
  if config_kubectl exec config-vol-demo -- sh -c 'grep -qx "database.name=myapp_v2" /config/app.properties'; then
    CONFIG_LAB_PROJECTED=true
    break
  fi
  sleep 5
done
if [ "$CONFIG_LAB_PROJECTED" = true ]; then
  config_kubectl exec config-vol-demo -- cat /config/app.properties
else
  printf 'Update not observed: inspect Pod events, kubelet connectivity and sync/cache settings\n' >&2
fi

# Replace this bare Pod to read the current environment values.
config_kubectl delete pod config-env-demo --wait=true --timeout=120s &&
  config_kubectl apply -f "${CONFIG_LAB_DIR:?}/configmap-env-pod.yaml" &&
  config_kubectl wait --for=condition=Ready pod/config-env-demo --timeout=120s &&
  config_kubectl logs config-env-demo
```

原始的 `config-vol-demo` 日志只包含启动时读取的内容。再次检查挂载的文件可以展示投影效果，但不代表应用会自动重新加载。重试次数和间隔是本练习中用于观察的设置；命令执行时间会增加总耗时，而且 Kubernetes 不保证在此时间窗口内完成更新。替换后的 Pod 成功启动后，其日志应显示 `LOG_LEVEL=debug`。

---

## 清理
```bash
if [[ -n ${CONFIG_LAB_NAMESPACE:-} && -n ${CONFIG_LAB_UID:-} ]]; then
  current_uid=$(kubectl --context "${CONFIG_LAB_CONTEXT:?}" get namespace "$CONFIG_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [ "$current_uid" = "$CONFIG_LAB_UID" ]; then
    kubectl --context "$CONFIG_LAB_CONTEXT" delete namespace "$CONFIG_LAB_NAMESPACE" --timeout=120s
  fi
fi
if [[ -n ${CONFIG_LAB_DIR:-} ]]; then
  rm -f -- "$CONFIG_LAB_DIR/app.properties" "$CONFIG_LAB_DIR/configmap-env-pod.yaml" \
    "$CONFIG_LAB_DIR/configmap-vol-pod.yaml" "$CONFIG_LAB_DIR/secret-pod.yaml" \
    "$CONFIG_LAB_DIR/DB_USER" "$CONFIG_LAB_DIR/DB_PASSWORD"
  rmdir -- "$CONFIG_LAB_DIR"
fi
unset -f config_kubectl
```

## 参考资料和验证范围

- [ConfigMap 投影和更新](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secret 安全性和更新](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Secret 文件权限和环境变量](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)

验证涵盖 shell 语法、清单和本地测试文件。本次审计期间未创建或访问 Kubernetes Secret、Pod、命名空间或外部 Secret 存储。

## 后续步骤
- [配置测验](../../quizzes/core/05-configuration-secrets-quiz.md)
- [EKS 集群创建实验](../eks/01-eks-cluster-creation-lab.md)
