# 配置测验

本测验用于检验你对 Kubernetes 配置概念的理解，包括 ConfigMap、Secret、环境变量、resource requests 和 limits。

## 多项选择题

1. Kubernetes 中用于存储敏感信息的资源是什么？
   - A) ConfigMap
   - B) Secret
   - C) Volume
   - D) Deployment
   
<details>

<summary>显示答案</summary>

**答案：B) Secret**

**解释：**
Secret 是 Kubernetes 中用于存储密码、OAuth token 和 SSH key 等敏感信息的资源。Secrets 默认以 base64 编码形式存储，并且可以作为文件或环境变量挂载到 Pod。ConfigMap 用于存储非敏感配置数据。
</details>

2. Kubernetes 中 ConfigMap 的主要用途是什么？
   - A) 存储容器镜像
   - B) 存储应用程序配置数据
   - C) 定义网络策略
   - D) 控制 Pod 调度
   
<details>

<summary>显示答案</summary>

**答案：B) 存储应用程序配置数据**

**解释：**
ConfigMap 是一种 Kubernetes 资源，用于以键值对形式存储配置数据。这使你能够将应用程序代码与配置分离，从而为不同环境启用不同配置。ConfigMaps 可以作为环境变量、命令行参数或配置文件挂载到容器。
</details>

3. Kubernetes Pod 中 resource requests 和 limits 的区别是什么？
   - A) Requests 用于指导调度和资源分配；limits 用于限制运行时用量
   - B) Requests 是 Pod 可以使用的最大资源，limits 是最小资源
   - C) Requests 仅用于调度，limits 仅在运行时应用
   - D) Requests 仅适用于 CPU，limits 仅适用于内存
   
<details>

<summary>显示答案</summary>

**答案：A) Requests 用于指导调度和资源分配；limits 用于限制运行时用量**

**解释：**
Requests 会预留调度容量，并影响运行时资源分配；进程实际用量可以低于 request。CPU limits 通过节流强制执行；内存 limits 则在超限后通过 OOM 终止进程来响应。设置了 requests 并不意味着 Pod 不受节点资源压力影响。
</details>

4. 以下哪项不是在 Kubernetes 中向 Pod 提供 Secret 数据的方法？
   - A) 作为环境变量
   - B) 作为挂载的 Volume
   - C) 作为镜像仓库凭证
   - D) 作为网络接口
   
<details>

<summary>显示答案</summary>

**答案：D) 作为网络接口**

**解释：**
在 Kubernetes 中向 Pod 提供 Secret 数据的方法包括：作为环境变量、作为挂载的 Volume，以及作为镜像仓库凭证。Kubernetes 不支持通过网络接口提供 Secrets。
</details>

5. `kubectl create configmap` 不支持以下哪项输入方式？
   - A) 从字面值创建
   - B) 从文件创建
   - C) 从目录创建
   - D) 使用 `--from-url`
   
<details>

<summary>显示答案</summary>

**答案：D) `--from-url`**

**解释：**
创建 ConfigMap 时，可以使用字面值（`--from-literal`）、文件（`--from-file`）或目录（`--from-file=<directory>`），但此命令没有 `--from-url` 参数。当然，也可以通过 Kubernetes REST API 请求创建 ConfigMap，或先从 URL 获取 manifest 再应用。
</details>

6. Kubernetes 中用于指定 Pod 的 service account 的字段是什么？
   - A) spec.serviceAccount
   - B) spec.serviceAccountName
   - C) metadata.serviceAccount
   - D) spec.account
   
<details>

<summary>显示答案</summary>

**答案：B) spec.serviceAccountName**

**解释：**
在 Kubernetes 中，Pod 的 service account 通过 `spec.serviceAccountName` 字段指定。此字段允许你指定 Pod 应使用哪个 service account。如果未指定，则会使用 namespace 的默认 service account。
</details>

7. Kubernetes 中 Secret 数据的默认编码方式是什么？
   - A) AES-256
   - B) Base64
   - C) SHA-256
   - D) 不编码
   
<details>

<summary>显示答案</summary>

**答案：B) Base64**

**解释：**
Kubernetes 中的 Secret 数据默认以 Base64 编码形式存储。这只是编码，不是加密，因此需要额外的安全措施。自 Kubernetes 1.13 起，可以对存储在 etcd 中的 Secret 数据进行加密。
</details>

8. 在 Pod manifest 中设置真实密码时，应避免采用哪种做法？
   - A) 引用 Secret key
   - B) 使用受保护的 Secret volume
   - C) 直接在 Pod spec 中硬编码
   - D) 使用 workload identity 从外部密钥管理器获取
   
<details>

<summary>显示答案</summary>

**答案：C) 直接在 Pod spec 中硬编码**

**解释：**
不要在 manifest 或日志中写入明文密码。对非敏感常量而言，直接设置 `env.value` 是有效做法；机密值应使用 Secret 或外部密钥存储。ConfigMap 和 Downward API 都不是密码存储方式。
</details>

9. 当一个 Pod 中的所有容器都设置了 resource requests 和 limits，并且 requests 等于 limits 时，会分配哪个 QoS（Quality of Service）类别？
   - A) Guaranteed
   - B) Burstable
   - C) BestEffort
   - D) Critical
   
<details>

<summary>显示答案</summary>

**答案：A) Guaranteed**

**解释：**
当 Pod 中每个容器都设置了 CPU 和内存 requests 与 limits，且两者相等（并且没有 Pod 级资源设置）时，会分配 Guaranteed QoS 类别。驱逐还会考虑 Pod 优先级和相对于 requests 的资源用量；Guaranteed 并非无条件保证 Pod 存活。只有部分容器设置了 requests/limits，或 requests 与 limits 不同时，会分配 Burstable。任何容器都未设置 requests 或 limits 时，会分配 BestEffort。
</details>

10. ConfigMap 或 Secret 的更改何时会自动反映到 Pod 中？
    - A) 总是自动反映
    - B) 最终会反映到完整的 volume 挂载中（`subPath` 除外）
    - C) 仅在作为环境变量使用时
    - D) 永远不会自动反映；必须重启 Pod
    
<details>

<summary>显示答案</summary>

**答案：B) 最终会反映到完整的 volume 挂载中（`subPath` 除外）**

**解释：**
可变 ConfigMap/Secret 的完整 volume 投影最终会更新；延迟取决于 kubelet 同步和缓存/变更检测设置。`subPath` 挂载不会更新。应用程序必须重新读取文件；环境变量则需要替换或重启应用容器，或重新创建 Pod。
</details>

## 实践题

1. 说明如何创建 ConfigMaps 和 Secrets，并将它们作为环境变量和 volumes 挂载到 Pod。

<details>

<summary>显示答案</summary>

**答案：**

1. 创建 ConfigMap：
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
   name: app-config
data:
  app.name: MyApp
  app.properties: |
    app.name=MyApp
    app.version=1.0.0
  database.properties: |
    db.host=mysql
    db.port=3306
    db.name=mydb
```

2. 创建 Secret：
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  db.user: YWRtaW4=  # admin (base64 encoded)
  db.password: cGFzc3dvcmQxMjM=  # password123 (base64 encoded)
```

3. 创建一个将其作为环境变量和 volumes 挂载的 Pod：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: myapp:1.0
      env:
        # Get environment variable from ConfigMap
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: app.name
        # Get environment variables from Secret
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db.user
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db.password
      volumeMounts:
        # Mount ConfigMap as volume
        - name: config-volume
          mountPath: /etc/config
        # Mount Secret as volume
        - name: secret-volume
          mountPath: /etc/secrets
          readOnly: true
  volumes:
    # Define ConfigMap volume
    - name: config-volume
      configMap:
        name: app-config
    # Define Secret volume
    - name: secret-volume
      secret:
        secretName: app-secrets
```

4. 应用资源：
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f pod.yaml
```

5. 验证环境变量：
```bash
kubectl exec app-pod -- sh -c 'test -n "$APP_NAME" && test -n "$DB_PASSWORD" && echo "Configuration available"'
```

6. 验证挂载的 volumes：
```bash
kubectl exec app-pod -- ls -la /etc/config
kubectl exec app-pod -- ls -la /etc/secrets
```

7. 验证文件内容：
```bash
kubectl exec app-pod -- cat /etc/config/app.properties
kubectl exec app-pod -- test -s /etc/secrets/db.user
```
</details>

2. 说明如何为 Pod 设置 resource requests 和 limits，并验证 QoS 类别。

<details>

<summary>显示答案</summary>

**答案：**

1. 创建具有不同 QoS 类别的 Pods：

**Guaranteed QoS Pod**：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed-pod
spec:
  containers:
    - name: nginx
      image: nginx
      resources:
        requests:
          memory: "100Mi"
          cpu: "100m"
        limits:
          memory: "100Mi"
          cpu: "100m"
```

**Burstable QoS Pod**：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: burstable-pod
spec:
  containers:
    - name: nginx
      image: nginx
      resources:
        requests:
          memory: "100Mi"
          cpu: "100m"
        limits:
          memory: "200Mi"
          cpu: "200m"
```

**BestEffort QoS Pod**：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: besteffort-pod
spec:
  containers:
    - name: nginx
      image: nginx
# No resource requests or limits
```

2. 创建 Pods：
```bash
kubectl apply -f guaranteed-pod.yaml
kubectl apply -f burstable-pod.yaml
kubectl apply -f besteffort-pod.yaml
```

3. 检查 QoS 类别：
```bash
kubectl get pods guaranteed-pod -o jsonpath='{.status.qosClass}'
# Output: Guaranteed

kubectl get pods burstable-pod -o jsonpath='{.status.qosClass}'
# Output: Burstable

kubectl get pods besteffort-pod -o jsonpath='{.status.qosClass}'
# Output: BestEffort
```

4. 检查 Pod 详细信息：
```bash
kubectl describe pod guaranteed-pod | grep QoS
kubectl describe pod burstable-pod | grep QoS
kubectl describe pod besteffort-pod | grep QoS
```

5. 监控资源使用情况：
```bash
kubectl top pod guaranteed-pod
kubectl top pod burstable-pod
kubectl top pod besteffort-pod
```

**QoS 类别判定规则**：
  - **Guaranteed**：所有容器都设置了 resource requests 和 limits，并且 requests 等于 limits
  - **Burstable**：至少一个容器设置了 resource requests，但不满足 Guaranteed 条件
  - **BestEffort**：任何容器都未设置 resource requests 或 limits
</details>

3. 说明如何使用 Downward API 向容器提供 Pod 元数据和资源信息。

<details>

<summary>显示答案</summary>

**答案：**

1. 创建使用 Downward API 的 Pod：
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: downward-api-pod
  labels:
    app: myapp
    environment: production
spec:
  containers:
    - name: main
      image: busybox
      command: ["sh", "-c", "while true; do echo Downward API Demo; sleep 10; done"]
      resources:
        requests:
          memory: "64Mi"
          cpu: "250m"
        limits:
          memory: "128Mi"
          cpu: "500m"
      env:
        # Provide pod metadata as environment variables
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: POD_SERVICE_ACCOUNT
          valueFrom:
            fieldRef:
              fieldPath: spec.serviceAccountName
        - name: POD_LABEL_APP
          valueFrom:
            fieldRef:
              fieldPath: metadata.labels['app']
        # Provide container resource information as environment variables
        - name: CPU_REQUEST
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: requests.cpu
              divisor: "1m"
        - name: CPU_LIMIT
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: limits.cpu
              divisor: "1m"
        - name: MEM_REQUEST
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: requests.memory
              divisor: "1Mi"
        - name: MEM_LIMIT
          valueFrom:
            resourceFieldRef:
              containerName: main
              resource: limits.memory
              divisor: "1Mi"
      volumeMounts:
        - name: podinfo
          mountPath: /etc/podinfo
  volumes:
    # Provide Downward API as volume
    - name: podinfo
      downwardAPI:
        items:
          - path: "labels"
            fieldRef:
              fieldPath: metadata.labels
          - path: "annotations"
            fieldRef:
              fieldPath: metadata.annotations
          - path: "cpu-request"
            resourceFieldRef:
              containerName: main
              resource: requests.cpu
              divisor: "1m"
          - path: "cpu-limit"
            resourceFieldRef:
              containerName: main
              resource: limits.cpu
              divisor: "1m"
```

2. 创建 Pod：
```bash
kubectl apply -f downward-api-pod.yaml
```

3. 验证环境变量：
```bash
kubectl exec downward-api-pod -- env | sort
```

4. 验证 volume 文件：
```bash
kubectl exec downward-api-pod -- ls -la /etc/podinfo
kubectl exec downward-api-pod -- cat /etc/podinfo/labels
kubectl exec downward-api-pod -- cat /etc/podinfo/cpu-request
```

**Downward API 可提供的字段**：

**可作为环境变量提供的字段**：
  - `metadata.name` - Pod 名称
  - `metadata.namespace` - Pod namespace
  - `metadata.uid` - Pod UID
  - `metadata.labels['<KEY>']` - Pod label 值
  - `metadata.annotations['<KEY>']` - Pod annotation 值
  - `status.podIP` - Pod IP 地址
  - `spec.nodeName` - Pod 正在运行的 node 名称
  - `spec.serviceAccountName` - Pod 的 service account 名称
  - `status.hostIP` - Pod 正在运行的 node 的 IP 地址

**资源字段**：
  - `requests.cpu` - CPU request
  - `limits.cpu` - CPU limit
  - `requests.memory` - Memory request
  - `limits.memory` - Memory limit
</details>
