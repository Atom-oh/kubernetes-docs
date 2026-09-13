# Strimzi Operator 测验

> **最后更新**：2026 年 9 月 12 日，Strimzi 1.2.0 / Kafka 4.3.1。

本测验检验您对 Strimzi Operator 基础、安装方法、核心 CRD、KRaft 节点角色和 EKS 部署注意事项的理解。

## 选择题

1. Strimzi 是哪类 CNCF 项目？
   - A) 服务网格
   - B) 在 Kubernetes 上运行 Apache Kafka 的 Operator
   - C) 容器运行时
   - D) CI/CD 流水线工具

<details>

<summary>显示答案</summary>

**答案：B) 在 Kubernetes 上运行 Apache Kafka 的 Operator**

**解释：**
Strimzi 1.2 是 CNCF 孵化项目，协调自定义资源中的期望状态。当前 Kafka Pod 管理使用 StrimziPodSet。Operator 不会自动完成所有运维策略或可用性保证。
</details>

2. 以下哪项最不能准确描述不使用 Strimzi、直接以 StatefulSet 运行 Kafka 的挑战？
   - A) 处理顺序滚动升级
   - B) 签发和轮换 TLS 证书
   - C) 无法构建容器镜像
   - D) 管理分区再平衡期间的数据移动

<details>

<summary>显示答案</summary>

**答案：C) 无法构建容器镜像**

**解释：**
可以直接运维，但需要实现升级、证书、存储和重新分配流程。Strimzi 协调重复工作；数据恢复和可用性策略仍需验证。
</details>

3. 安装 Cluster Operator 前，哪个命令添加 Strimzi Helm 仓库？
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>显示答案</summary>

**答案：A) `helm repo add strimzi https://strimzi.io/charts/`**

**解释：**
添加官方 chart 仓库，并为全新安装固定 1.2.0。现有 beta API/CRD 需要先执行官方迁移流程；新命名空间不能避免集群作用域 CRD 冲突。
</details>

4. Strimzi Cluster Operator 默认监视哪个命名空间范围？
   - A) 集群中的每个命名空间
   - B) 所有 `kube-system` 命名空间
   - C) 仅其部署所在命名空间
   - D) 仅 `default` 命名空间

<details>

<summary>显示答案</summary>

**答案：C) 仅其部署所在命名空间**

**解释：**
默认 chart 监视其发布命名空间。Chart 1.2 将该命名空间与额外 watchNamespaces 一起包含并去重，同时创建 RoleBinding。仅更改环境变量可能导致 RBAC 缺失。
</details>

5. 当前 Strimzi 1.2 KRaft 部署不支持哪个配置块？
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>显示答案</summary>

**答案：B) `Kafka.spec.zookeeper`**

**解释：**
当前 Strimzi 1.2 使用 KRaft，不支持 ZooKeeper 配置块。KafkaNodePool 定义 controller 和 broker 角色；无需旧版激活注解。
</details>

6. 哪个值不是 `KafkaNodePool.spec.roles` 的有效条目？
   - A) `controller`
   - B) `broker`
   - C) 结合 `controller` 和 `broker` 的双角色
   - D) `zookeeper`

<details>

<summary>显示答案</summary>

**答案：D) `zookeeper`**

**解释：**
实际枚举值为 controller 和 broker。两者可列为 [controller, broker]；dual-role 不是独立字符串值。
</details>

7. 为什么选择三个控制器投票成员？
   - A) 必须始终匹配代理数
   - B) 一个投票成员故障后仍保留两个成员的多数派
   - C) Kafka 客户端库要求至少 3 个控制器
   - D) EBS 卷限制要求如此

<details>

<summary>显示答案</summary>

**答案：B) 一个投票成员故障后仍保留两个成员的多数派**

**解释：**
三个投票成员在一个故障后仍保有两个成员的多数派。偶数组也存在多数派；相同容错能力下，奇数规模更高效。控制器数独立于代理数，且仍取决于连通性和其他条件。
</details>

8. 标准 Amazon EBS CSI 驱动路径的 StorageClass 预置器是什么？
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>显示答案</summary>

**答案：B) `ebs.csi.aws.com`**

**解释：**
标准 EBS CSI 使用 ebs.csi.aws.com。EKS Auto Mode 使用 ebs.csi.eks.amazonaws.com。更改 StorageClass 预置器不会迁移现有 PVC。
</details>

9. 在 `KafkaNodePool.spec.template.pod` 添加哪个字段，可将代理 Pod 均匀分散到可用区？
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>显示答案</summary>

**答案：B) `topologySpreadConstraints`**

**解释：**
选择器必须匹配实际 Pod 标签。要求三个符合条件可用区还需要 minDomains: 3 等条件；maxSkew: 1 不会创建三个可用区。分别检查调度和 Kafka 副本机架放置。
</details>

10. 外部客户端需从集群外访问 Kafka 代理时，可在 `Kafka.spec.kafka.listeners` 添加哪些监听器类型？
    - A) `internal` 和 `clusterip`
    - B) `loadbalancer` 或 `nodeport`
    - C) 仅 `ingress`
    - D) 不支持外部暴露

<details>

<summary>显示答案</summary>

**答案：B) `loadbalancer` 或 `nodeport`**

**解释：**
Strimzi 创建 LoadBalancer Service 或 NodePort。生成的云负载均衡器取决于控制器/类。正文固定 AWS Load Balancer Controller 类，并将内部/IP 目标设置应用到引导和每个代理 Service。
</details>

## 简答题

11. 写出负责将 `KafkaTopic` 和 `KafkaUser` 自定义资源与实际 Kafka 资源同步的两个 Strimzi 内部组件。

<details>

<summary>显示答案</summary>

**答案：Topic Operator、User Operator**

**解释：**
Topic Operator 和 User Operator 可在启用的 Entity Operator 中运行；也有独立安装。主题/用户 CR 需要适当命名空间和集群标签。
</details>

12. 哪个环境变量配置 Cluster Operator 监视多个命名空间？

<details>

<summary>显示答案</summary>

**答案：`STRIMZI_NAMESPACE`**

**解释：**
变量是 STRIMZI_NAMESPACE。对于 Helm 管理安装，使用 watchNamespaces/watchAnyNamespace values 和匹配 RBAC，不要通过 kubectl set env 造成漂移。
</details>

13. `KafkaNodePool.spec.storage` 中哪种存储类型允许每代理附加多个 EBS 卷，以分散 I/O？

<details>

<summary>显示答案</summary>

**答案：JBOD（type: jbod）**

**解释：**
JBOD 支持多个卷 ID。它不保证自动均衡数据，也不消除实例 EBS/网络限制。最多一个卷可选择 kraftMetadata: shared。
</details>

14. 哪个条件表示 Operator 最近一次成功的 Kafka 协调？

<details>

<summary>显示答案</summary>

**答案：`Ready: True`**

**解释：**
Ready=True 是 Operator 最近一次协调观测。比较 observedGeneration 与当前 generation，并检查 Pod 就绪状态、法定人数及实际经过身份验证的客户端连通性。
</details>

15. 哪个 Strimzi CRD 定义用于运行 Debezium 等源/接收器连接器的独立工作进程集群？

<details>

<summary>显示答案</summary>

**答案：`KafkaConnect`**

**解释：**
KafkaConnect 定义 Connect 工作进程，KafkaConnector 表示单个连接器。分别配置连接器资源管理和工作进程身份验证/授权。
</details>

## 实践题

16. 使用正文的 operator-values.yaml，将 Strimzi 1.2.0 安装到新的 kafka 命名空间。

<details>

<summary>显示答案</summary>

**答案：**
```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.2.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io
```

**解释：**
这些命令用于全新安装。固定 chart 并验证 Operator 可用性/CRD。现有安装需要先完成 v1 转换及 CRD 所有权/升级审核。
</details>

17. 编写包含三个代理的 KafkaNodePool，使用正文的命名空间、存储和三个可用区约束。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: broker
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
  - broker
  storage:
    type: jbod
    volumes:
    - id: 0
      type: persistent-claim
      size: 100Gi
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      memory: 4Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: broker
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 3
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            strimzi.io/cluster: my-cluster
            docs.example.com/kafka-role: broker
```

**解释：**
此处使用正文标准 gp3-kafka StorageClass 和三个可用区要求。匹配命名空间/集群标签，并以 deleteClaim: false 保留 PVC。Auto Mode 使用独立 StorageClass；池不保证物理节点分离。
</details>

18. 假定已启用身份验证的 kafka-client Pod 就绪，创建 orders 并用 TLS/SCRAM 生产者/消费者命令测试。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: orders
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 12
  replicas: 3
  config:
    retention.ms: 604800000
    min.insync.replicas: 2
```

```bash
kubectl apply -f orders-topic.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
printf 'strimzi-auth-smoke-test\n' |
  kubectl -n kafka exec -i kafka-client -- \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
    --producer.config /client/client.properties --topic orders
kubectl -n kafka exec kafka-client -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
  --consumer.config /client/client.properties --group order-processor \
  --topic orders --from-beginning --max-messages 1 --timeout-ms 10000
```

**解释：**
正文的 KafkaUser、CA Secret 和启用身份验证的 kafka-client Pod 必须已存在。使用 TLS/SCRAM 客户端属性，不使用明文端点。检查现有主题第一条记录是否真是刚发送的记录。
</details>

19. 定义 SCRAM 用户，使其可对 orders 生产/消费、访问 order-processor 组并执行幂等生产者操作。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
          patternType: literal
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: order-processor
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

**解释：**
还要启用监听器身份验证和集群授权器。除主题 ACL 外，此处授予 order-processor 组 Read 和幂等生产者能力。实际服务应考虑不同的生产者/消费者身份。
</details>

20. 在代理 KafkaNodePool spec 下编写模板片段，匹配实际标签并要求三个符合条件可用区。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
# Merge under KafkaNodePool.spec
template:
  pod:
    metadata:
      labels:
        docs.example.com/kafka-role: broker
    topologySpreadConstraints:
    - maxSkew: 1
      minDomains: 3
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      nodeAffinityPolicy: Honor
      nodeTaintsPolicy: Honor
      labelSelector:
        matchLabels:
          strimzi.io/cluster: my-cluster
          docs.example.com/kafka-role: broker
```

**解释：**
将片段合并到代理 KafkaNodePool 的 spec 下。元数据标签匹配选择器；没有三个符合条件可用区时，minDomains=3 可能使 Pod 保持 Pending。可用区丢失后，严格约束可能阻止替代 Pod；Kafka 机架感知是独立机制。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/02-strimzi-operator.md) | [下一测验：Kafka 运维](./03-kafka-operations-quiz.md)
