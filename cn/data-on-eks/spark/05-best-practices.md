# 第 5 部分：最佳实践与安全

> **审查基线**：2026 年 9 月 12 日 · 上游 Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4

## 范围

本章以第 1 部分的直接 Kubernetes 提交方式为基础，介绍临时 S3 凭证、指标/事件日志、History Server、网络和 RBAC。Spark 4.2 要求 Kubernetes 1.34 或更高版本，以及兼容的 kubectl；同时需准备好 spark-jobs 命名空间和 EKS 访问权限。Operator 和 EMR 有各自的配置和权限路径。

应准备 IRSA 或 Pod Identity 的管理员访问权限、已有的 S3 存储桶和角色、容器镜像仓库及镜像构建工具。只有在安装了 Prometheus Operator 的环境中，才应用 PodMonitor 示例。以下账户、存储桶、镜像和区域值均为**需要替换的示例**。只有一份配置检查清单，并不能证明运行安全、可恢复或具备所需性能。

## 1. 构建版本兼容的 S3A 镜像

经审查的 Spark 4.2 发行版包含 Hadoop 客户端 3.5.0，但不包含 S3A 所需的所有额外依赖。hadoop-aws 必须与 **Hadoop 版本完全一致**。Maven 为 3.5.0 解析出的运行时依赖如下：

| 构件 | 版本 |
| --- | --- |
| org.apache.hadoop:hadoop-aws | 3.5.0 |
| software.amazon.awssdk:bundle | 2.35.4 |
| software.amazon.s3.analyticsaccelerator:analyticsaccelerator-s3 | 1.3.1 |
| org.wildfly.openssl:wildfly-openssl | 2.2.5.Final |

不要混用任意旧版 AWS SDK JAR，也不要只复制 hadoop-aws。此 POM 会解析运行时依赖，而无需重新复制 Hadoop common。使用其他 Spark 镜像或 EMR 运行时前，请重新核实其中包含的版本。

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>docs.review</groupId>
  <artifactId>spark-s3a-runtime</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.apache.hadoop</groupId>
      <artifactId>hadoop-aws</artifactId>
      <version>3.5.0</version>
    </dependency>
  </dependencies>
</project>
```

将以上内容保存为 Dockerfile。所选镜像的平台必须与工作负载和 History Server 节点匹配。

```dockerfile
FROM spark:4.2.0-scala2.13-java21-ubuntu
COPY --chown=185:185 s3a-jars/ /opt/spark/jars/
USER 185
```

```bash
# Save the XML below as s3a-pom.xml.
mvn -f s3a-pom.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies \
  -DincludeScope=runtime -DoutputDirectory="$PWD/s3a-jars"
: "${SPARK_S3_IMAGE:?Set a registry/repository/tag you can publish}"
: "${SPARK_IMAGE_PLATFORM:?Set a platform matching the target nodes, for example linux/amd64}"
docker build --platform "$SPARK_IMAGE_PLATFORM" --tag "$SPARK_S3_IMAGE" .
# Authenticate to your registry through your normal procedure, then publish the tested image.
docker push "$SPARK_S3_IMAGE"
```

驱动程序、执行器和 History Server 都应使用包含完整依赖的镜像。`--packages` 会由提交方解析依赖；它不会自动将依赖安装到使用 `spark-class` 启动的 History Server 中。应验证镜像仓库访问、镜像检查、兼容性以及实际 S3 读写操作，然后为运维固定已测试镜像的摘要。

## 2. 区分 IRSA 与 Pod Identity

对于这一 Hadoop 3.5.0 / SDK v2 组合，应使用：

| 身份路径 | fs.s3a.aws.credentials.provider |
| --- | --- |
| IRSA | software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider |
| EKS Pod Identity | software.amazon.awssdk.auth.credentials.ContainerCredentialsProvider |

IRSA 使用 OIDC 信任关系、ServiceAccount 注解和投影的 Web 身份令牌。Pod Identity 使用关联配置和 Agent 的容器凭证路径；IRSA 注解无法配置 Pod Identity。不要盲目组合两种路径。

默认的 S3A 凭证链包含容器/实例凭证包装器，但不包含 Web 身份提供程序。在这个仅使用 SDK v2 的组合中，旧类 `com.amazonaws.auth.WebIdentityTokenCredentialsProvider` 不会自动映射。其他一些旧别名可以映射，因此这并不意味着所有旧名称总是失效。明确指定身份路径也可减少意外回退到其他凭证来源的可能性。临时凭证仍要求信任关系、权限和网络配置正确。

将以下内容保存为 `serviceaccounts.yaml`，作为 **IRSA 示例**。替换角色，并首先针对集群 OIDC 提供程序、audience 以及准确的命名空间/ServiceAccount subject 配置信任关系。执行器和 History Server 不会获得驱动程序的 Kubernetes 管理权限。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-driver
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-driver
automountServiceAccountToken: true
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-executor
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-executor
automountServiceAccountToken: false
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spark-data-history
  namespace: spark-jobs
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/docs-spark-history
automountServiceAccountToken: false
```

按用途分开配置数据权限：

- Driver：访问所需输入/输出数据，并在 spark-events 下写入事件日志。应检查 S3A rename/分段上传要求及任何 KMS 权限。
- Executors：仅访问实际数据处理所需的存储桶/前缀。
- History Server：列出/读取事件日志前缀，并具备所需的 KMS 解密权限。此示例禁用了清理器，因此不需要删除权限。

使用 Pod Identity 时，应移除 IRSA 注解，并为这三个 ServiceAccount 配置身份关联、角色信任关系，以及 Agent/节点所需的 EKS Auth 权限。还要将下方属性改为 `ContainerCredentialsProvider`。IAM OIDC 提供程序是 IRSA 的前提，但不是所有身份路径的普遍前提。

## 3. Driver RBAC 和作业配置

将以下内容保存为 `driver-rbac.yaml`。此基线不会创建 PVC，也不会启用其他需要额外权限的功能；添加权限前，应先审查相关功能。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: spark-data-driver
  namespace: spark-jobs
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - services
  - configmaps
  verbs:
  - create
  - get
  - list
  - watch
  - delete
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spark-data-driver
  namespace: spark-jobs
subjects:
- kind: ServiceAccount
  name: spark-data-driver
  namespace: spark-jobs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: spark-data-driver
```

Role 会授予其列出的命名空间级资源权限，并不只针对“该 Driver 自己的执行器”。Kubernetes RBAC 不会为这些规则增加 Pod 标签条件。由 RoleBinding 绑定的 ClusterRole 也可以将命名空间级资源权限限制在该命名空间内。评估时应查看**规则和绑定范围**，而不仅仅看对象名称。

创建 Pod 的权限可能与其他 ServiceAccount 或主机访问权限结合，因此命名空间级 Role 并不是完整的安全边界。应隔离信任域，并使用 Pod Security/准入控制、危险 Pod 规格限制、IAM 和网络控制。禁用自动挂载 API 令牌与另行注入 IRSA 令牌是两回事。

替换存储桶和区域后，将以下内容保存为 `job.properties`。

```properties
spark.kubernetes.namespace=spark-jobs
spark.kubernetes.authenticate.driver.serviceAccountName=spark-data-driver
spark.kubernetes.authenticate.executor.serviceAccountName=spark-data-executor
spark.hadoop.fs.s3a.aws.credentials.provider=software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider
spark.hadoop.fs.s3a.endpoint.region=ap-northeast-2
spark.eventLog.enabled=true
spark.eventLog.dir=s3a://my-spark-bucket/spark-events/
spark.eventLog.logStageExecutorMetrics=true
spark.metrics.conf.*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet
spark.metrics.conf.*.sink.prometheusServlet.path=/metrics/prometheus
spark.ui.prometheus.enabled=true
spark.ui.port=4040
spark.driver.port=7078
spark.driver.blockManager.port=7079
spark.blockManager.port=7079
spark.port.maxRetries=0
spark.authenticate=true
spark.network.crypto.enabled=true
spark.network.crypto.cipher=AES/GCM/NoPadding
spark.network.crypto.authEngineVersion=2
spark.network.crypto.saslFallback=false
spark.io.encryption.enabled=true
```

`spark.authenticate` 用于验证内部连接，而不是 UI 用户。在 Kubernetes 模式下，每个应用生成的密钥会传播到执行器环境中；有权限读取 Pod 的身份可能看到这些密钥。应审查 Pod 读取权限，并考虑另一种方案：安全生成并挂载 Secret 文件。不要将固定的认证密钥提交到 properties 文件或 Git。

此处的 RPC 加密设置面向相互匹配的当前 Spark 版本；与其他客户端/shuffle 服务组合时应验证兼容性。IO 加密仅覆盖受支持的 Spark 临时本地数据，不覆盖 S3/EBS/KMS，也不提供 UI TLS。UI 需要单独配置身份验证、授权和 TLS 访问路径。

## 4. 每次运行的入站策略和提交

只选择 role 标签也会允许**同一命名空间中其他作业的执行器**。将以下内容保存为 `make-network-policy.py`。脚本会在提交前创建唯一的运行 ID，并将该 ID 同时写入 Pod 标签和策略中。请将 Prometheus 命名空间/Pod 标签替换为实际安装值。

```python
import json
import os
import re
from pathlib import Path

run_id = os.environ["SPARK_RUN_ID"]
if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", run_id):
    raise ValueError("SPARK_RUN_ID must be a lowercase DNS label, at most 40 characters")
monitor_ns = os.environ.get("PROMETHEUS_NAMESPACE", "monitoring")
def peer(role):
    return {"podSelector": {"matchLabels": {"docs-job": run_id, "spark-role": role}}}
def policy(role, ingress):
    return {
        "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
        "metadata": {"name": run_id + "-" + role, "namespace": "spark-jobs"},
        "spec": {"podSelector": {"matchLabels": {"docs-job": run_id, "spark-role": role}},
                 "policyTypes": ["Ingress"], "ingress": ingress}}
driver = policy("driver", [
    {"from": [peer("executor")], "ports": [{"protocol": "TCP", "port": 7078}, {"protocol": "TCP", "port": 7079}]},
    {"from": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": monitor_ns}},
               "podSelector": {"matchLabels": {"app.kubernetes.io/name": "prometheus"}}}],
     "ports": [{"protocol": "TCP", "port": 4040}]},
])
executor = policy("executor", [
    {"from": [peer("driver"), peer("executor")], "ports": [{"protocol": "TCP", "port": 7079}]},
])
Path("job-networkpolicy.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": [driver, executor]}, indent=2) + "\n")
```

审查/应用 ServiceAccount 和 RBAC 后，使用相同的运行 ID 提交策略和作业。

```bash
kubectl apply -f serviceaccounts.yaml
kubectl apply -f driver-rbac.yaml
```

```bash
# Set SPARK_S3_IMAGE to the built/published image accessible to your EKS nodes.
: "${SPARK_S3_IMAGE:?Set the tested Spark S3 image reference}"
export SPARK_RUN_ID="spark-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
# Set this to the actual namespace/Pod labels of the Prometheus collector.
export PROMETHEUS_NAMESPACE=monitoring
python3 make-network-policy.py
kubectl apply -f job-networkpolicy.json

K8S_API_SERVER="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
: "${K8S_API_SERVER:?Select the intended context}"
spark-submit \
  --master "k8s://${K8S_API_SERVER}" --deploy-mode cluster \
  --name "$SPARK_RUN_ID" --properties-file job.properties \
  --conf "spark.kubernetes.container.image=$SPARK_S3_IMAGE" \
  --conf "spark.kubernetes.driver.label.docs-job=$SPARK_RUN_ID" \
  --conf "spark.kubernetes.executor.label.docs-job=$SPARK_RUN_ID" \
  --conf spark.executor.instances=2 \
  --conf spark.driver.memory=1g --conf spark.executor.memory=1g \
  --class org.apache.spark.examples.SparkPi \
  local:///opt/spark/examples/jars/spark-examples.jar 10
```

这只是一个**入站流量示例**。额外限制出站流量时，还需考虑 DNS、Kubernetes API、S3/STS 或 EKS Auth/凭证端点，以及实际数据源路径。必须使用会强制实施策略的 CNI，且多项策略是叠加生效的。还应考虑其他允许策略、节点/hostNetwork 行为，以及能够伪造标签的 Pod 创建者。标签不是经过加密验证的作业身份，也无法保证防止所有绕过方式。

端口 7078/7079 是固定值，`port.maxRetries=0` 可避免端口冲突后切换到其他端口。端口被占用时启动会失败。如使用 Spark Connect、其他插件或 JMX exporter，应另行设计相应访问路径。

## 5. Prometheus：不同的端点

第 2 部分的 chart 指标描述 Operator 本身；它不会自动在每个 Spark JVM 中安装 JMX agent。Java agent 运行在它所附加的 JVM 内部，而不是作为独立的额外进程运行。

| 采集路径 | 含义 |
| --- | --- |
| Driver `/metrics/prometheus/` | PrometheusServlet 的 Dropwizard 注册表；文档称其为实验性功能 |
| Driver `/metrics/executors/prometheus/` | Driver 收集的执行器聚合指标 |
| JmxSink + JMX exporter | 选定的 JVM MBean/exporter 映射；需要相应 JAR 和配置 |

每个执行器不会各自运行 Spark UI。这些 servlet/JMX 路径提供的时间序列、名称、标签和单位不保证一致。`spark.ui.prometheus.enabled` 控制执行器聚合端点，默认值为 true。Driver 的 Dropwizard 端点则使用上文单独列出的 sink 配置。

将以下内容保存为 `podmonitor.yaml`。其元数据标签和命名空间必须与实际 Prometheus 的 `podMonitorSelector`/`podMonitorNamespaceSelector` 匹配。采集器发现资源所需的 RBAC 也必须与前面的入站规则相符。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: spark-drivers
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
    - spark-jobs
  selector:
    matchLabels:
      spark-role: driver
    matchExpressions:
    - key: docs-job
      operator: Exists
  podMetricsEndpoints:
  - port: spark-ui
    path: /metrics/prometheus/
    interval: 30s
  - port: spark-ui
    path: /metrics/executors/prometheus/
    interval: 30s
```

应确认实际目标状态为 UP，并且两个路径都返回预期时间序列。短时作业可能会在两次抓取之间完成。指标保留和事件日志可以互为补充；复用 Grafana dashboard 前，应先检查实际的时间序列、标签和单位。

## 6. 作业完成后检查

Driver JVM 停止后，即使 Pod 对象仍然存在，其实时 UI 也会消失。History Server 根据**持久化的事件日志**重建 UI，而不是根据 stdout/stderr、Structured Streaming 检查点、输出数据或恢复备份重建。事件缺失、被删除、损坏、不完整或未刷新，都会限制重建能力。重放成本取决于日志量和并发量；压缩可能丢弃事件。不要假设一个小型副本就总是足够。

替换镜像、存储桶和区域后，将以下内容保存为 `history-server.yaml`。仅仅挂载一个文件不会让应用读取它：命令会通过 **`--properties-file`** 显式读取该文件。`spark-class` 会在前台运行，以便容器管理其生命周期。S3 身份应使用上文准备的独立只读 History Server 账户。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: spark-history-config
  namespace: spark-jobs
data:
  history.properties: 'spark.history.fs.logDirectory=s3a://my-spark-bucket/spark-events/

    spark.hadoop.fs.s3a.aws.credentials.provider=software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider

    spark.hadoop.fs.s3a.endpoint.region=ap-northeast-2

    spark.history.ui.port=18080

    spark.history.fs.cleaner.enabled=false

    '
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spark-history
  namespace: spark-jobs
spec:
  replicas: 1
  selector:
    matchLabels:
      app: spark-history
  template:
    metadata:
      labels:
        app: spark-history
    spec:
      serviceAccountName: spark-data-history
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 185
        fsGroup: 185
      containers:
      - name: history
        image: registry.example.com/team/spark-s3:4.2.0
        command:
        - /opt/spark/bin/spark-class
        args:
        - org.apache.spark.deploy.history.HistoryServer
        - --properties-file
        - /etc/spark/history.properties
        ports:
        - name: http
          containerPort: 18080
        env:
        - name: SPARK_DAEMON_MEMORY
          value: 1g
        resources:
          requests:
            cpu: 250m
            memory: 1536Mi
          limits:
            cpu: '1'
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
        volumeMounts:
        - name: config
          mountPath: /etc/spark
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: spark-history-config
---
apiVersion: v1
kind: Service
metadata:
  name: spark-history
  namespace: spark-jobs
spec:
  type: ClusterIP
  selector:
    app: spark-history
  ports:
  - name: http
    port: 18080
    targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: spark-history-ingress
  namespace: spark-jobs
spec:
  podSelector:
    matchLabels:
      app: spark-history
  policyTypes:
  - Ingress
  ingress: []
```

```bash
# Replace the image, bucket, region and IAM role examples before applying.
kubectl apply -f history-server.yaml
kubectl -n spark-jobs rollout status deployment/spark-history --timeout=180s
kubectl -n spark-jobs logs deployment/spark-history
kubectl -n spark-jobs port-forward --address 127.0.0.1 service/spark-history 18080:18080
```

使用本地端口 18080 查看应用。端口转发会持续到命令结束，只适用于诊断。运维访问应使用单独经过身份验证的 TLS 路径。ClusterIP 和 Spark RPC 身份验证都不会验证 UI 用户身份。

此示例禁用了 History Server 清理器。S3 生命周期、保留期限和成本策略应单独设计；启用清理器时，需审查删除权限、保留期限和其他使用方。清理已完成的作业及其 NetworkPolicy 时，应只选择预期的运行 ID。

## 运维验证

应在实际 Pod 中验证生效的 AWS 身份，以及允许/拒绝访问的 S3 前缀。测试 Driver 终止后的 History Server 访问、权限/网络故障、中断/重试行为和数据恢复。根据第 4 部分的请求/限制和开销模型设置 Driver/执行器容量。选择经过验证的直接提交、Operator 或 EMR 生命周期，以及合适的 client/cluster 模式；Operator 或 cluster 模式本身并非所有生产环境的普遍前提。

本次审查验证了原生提供程序的构造方式、Spark 本地运行时的两个指标端点、作业终止后的事件日志重放，以及 YAML/策略语义。本次没有进行 EKS 部署、S3 权限测试、镜像构建/发布或远程执行器通信测试。

- [Hadoop 3.5.0 S3A 依赖和凭证](https://hadoop.apache.org/docs/r3.5.0/hadoop-aws/tools/hadoop-aws/index.html)
- [Hadoop 3.5.0 凭证提供程序工厂](https://github.com/apache/hadoop/blob/rel/release-3.5.0/hadoop-tools/hadoop-aws/src/main/java/org/apache/hadoop/fs/s3a/auth/CredentialProviderListFactory.java)
- [EKS IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Spark 4.2 监控与 History Server](https://spark.apache.org/docs/4.2.0/monitoring.html)
- [Spark 执行器 Prometheus 配置](https://github.com/apache/spark/blob/v4.2.0/core/src/main/scala/org/apache/spark/internal/config/UI.scala)
- [Spark 安全](https://spark.apache.org/docs/4.2.0/security.html)
- [Kubernetes NetworkPolicy 语义](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes RBAC 与 RoleBinding 范围](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

[README](./README.md)

[测验](../../quizzes/data-on-eks/spark/05-best-practices-quiz.md)
