# Strimzi Operator 测验

> **最后更新**: 2026年10月16日，Strimzi 1.3.0 / Kafka 4.3.1.

本测验将考查你对 Strimzi Operator 基础知识、安装方法、核心 CRD、KRaft 节点角色以及 EKS 部署注意事项的理解。

## 选择题

1. Strimzi 属于哪种 CNCF 项目？
   - A) 服务网格
   - B) 用于在 Kubernetes 上运行 Apache Kafka 的 Operator
   - C) 容器运行时
   - D) CI/CD 流水线工具

<details>

<summary>显示答案</summary>

**答案：B) 用于在 Kubernetes 上运行 Apache Kafka 的 Operator**

**说明：**
Strimzi 1.3 是一个 CNCF 孵化项目，可协调自定义资源中的期望状态。目前，Kafka Pod 由 StrimziPodSet 管理。Operator 不会自动满足所有运维策略或可用性保证。
</details>

2. 以下哪一项作为不使用 Strimzi、直接以 StatefulSet 运行 Kafka 时面临的挑战，是最不准确的？
   - A) 处理顺序滚动升级
   - B) 签发和轮换 TLS 证书
   - C) 无法构建容器镜像
   - D) 在分区重新平衡期间管理数据迁移

<details>

<summary>显示答案</summary>

**答案：C) 无法构建容器镜像**

**说明：**
直接运行是可行的，但需要自行实现升级、证书、存储和重新分配流程。Strimzi 可协调重复性工作；数据恢复和可用性策略仍需验证。
</details>

3. 安装 Cluster Operator 之前，使用什么命令添加 Strimzi Helm 仓库？
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>显示答案</summary>

**答案：A) `helm repo add strimzi https://strimzi.io/charts/`**

**说明：**
添加官方 chart 仓库，并在全新安装时固定使用 1.3.0。现有 beta API/CRD 必须先按官方迁移流程处理；使用新 namespace 并不能避免集群范围 CRD 冲突。
</details>

4. 默认情况下，Strimzi Cluster Operator 会监视什么范围的 namespace？
   - A) 集群中的每个 namespace
   - B) 所有 `kube-system` namespace
   - C) 仅部署它的 namespace
   - D) 仅 `default` namespace

<details>

<summary>显示答案</summary>

**答案：C) 仅部署它的 namespace**

**说明：**
默认 chart 会监视其 release 所在的 namespace。Chart 1.3 会将该 namespace 与其他 watchNamespaces 一并包含并去重，同时创建 RoleBinding。仅更改环境变量可能会导致缺少 RBAC。
</details>

5. 在当前 Strimzi 1.3 KRaft 部署中，以下哪个区块不受支持？
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>显示答案</summary>

**答案：B) `Kafka.spec.zookeeper`**

**说明：**
当前 Strimzi 1.3 使用 KRaft，不支持 ZooKeeper 区块。KafkaNodePool 用于定义 controller 和 broker 角色；不需要使用旧版激活注解。
</details>

6. 以下哪个值不是 `KafkaNodePool.spec.roles` 的有效项？
   - A) `controller`
   - B) `broker`
   - C) 同时包含 `controller` 和 `broker` 的双重角色
   - D) `zookeeper`

<details>

<summary>显示答案</summary>

**答案：D) `zookeeper`**

**说明：**
实际的枚举值是 controller 和 broker。两者可以同时列出为 [controller, broker]；双重角色不是单独的字符串值。
</details>

7. 为什么选择三个 controller 投票者？
   - A) 它必须始终与 broker 数量相同
   - B) 一个投票者故障后，仍有两个投票者构成多数
   - C) Kafka 客户端库要求至少有 3 个 controller
   - D) EBS 卷数量限制要求如此

<details>

<summary>显示答案</summary>

**答案：B) 一个投票者故障后，仍有两个投票者构成多数**

**说明：**
三个投票者在一个发生故障后，仍有两个投票者构成多数。偶数规模的组也能形成多数；在相同容错能力下，奇数规模更高效。Controller 数量与 broker 数量无关，且仍取决于连接情况和其他条件。
</details>

8. 标准 Amazon EBS CSI 驱动路径使用的 StorageClass provisioner 是什么？
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>显示答案</summary>

**答案：B) `ebs.csi.aws.com`**

**说明：**
标准 EBS CSI 使用 ebs.csi.aws.com。EKS Auto Mode 使用 ebs.csi.eks.amazonaws.com。更改 StorageClass provisioner 不会迁移现有 PVC。
</details>

9. 为了让 broker Pod 均匀分布到各 AZ，应在 `KafkaNodePool.spec.template.pod` 中添加哪个字段？
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>显示答案</summary>

**答案：B) `topologySpreadConstraints`**

**说明：**
选择器必须与实际 Pod 标签匹配。要确保三个 AZ 均符合条件，还需要 minDomains: 3 等设置；maxSkew: 1 并不会创建三个 AZ。应分别检查调度情况和 Kafka 副本的机架放置情况。
</details>

10. 外部客户端需要从集群外部连接 Kafka broker 时，可以向 `Kafka.spec.kafka.listeners` 添加哪种 listener 类型？
    - A) `internal` 和 `clusterip`
    - B) `loadbalancer` 或 `nodeport`
    - C) 仅 `ingress`
    - D) 不支持外部暴露

<details>

<summary>显示答案</summary>

**答案：B) `loadbalancer` 或 `nodeport`**

**说明：**
Strimzi 会创建 LoadBalancer Service 或 NodePort。最终使用的云负载均衡器取决于 controller/class。本文为 bootstrap 和每个 broker Service 固定指定 AWS Load Balancer Controller class，并设置 internal/IP-target 相关配置。
</details>

## 简答题

11. 写出负责将 `KafkaTopic` 和 `KafkaUser` 自定义资源与实际 Kafka 资源同步的两个 Strimzi 内部组件。

<details>

<summary>显示答案</summary>

**答案：Topic Operator、User Operator**

**说明：**
Topic 和 User Operator 可以运行在已启用的 Entity Operator 中，也可以独立安装。Topic/user CR 需要位于合适的 namespace，并带有集群标签。
</details>

12. 使用什么环境变量配置 Cluster Operator 以监视多个 namespace？

<details>

<summary>显示答案</summary>

**答案：`STRIMZI_NAMESPACE`**

**说明：**
该变量为 STRIMZI_NAMESPACE。对于由 Helm 管理的安装，应使用 watchNamespaces/watchAnyNamespace values 和匹配的 RBAC，而不是通过 kubectl set env 引入配置漂移。
</details>

13. `KafkaNodePool.spec.storage` 中的哪种存储类型允许每个 broker 挂载多个 EBS 卷，以分散 I/O？

<details>

<summary>显示答案</summary>

**答案：JBOD（type: jbod）**

**说明：**
JBOD 支持多个卷 ID。它不能保证自动平衡数据，也不能消除实例的 EBS/网络限制。最多只能有一个卷设置 kraftMetadata: shared。
</details>

14. 哪个状态表示 Operator 最近一次成功协调 Kafka？

<details>

<summary>显示答案</summary>

**答案：`Ready: True`**

**说明：**
Ready=True 是 Operator 最近一次协调时观察到的状态。应将 observedGeneration 与当前 generation 比较，并检查 Pod 就绪情况、quorum 以及客户端实际的身份验证连接情况。
</details>

15. 用于定义独立 worker 集群以运行源/接收连接器（例如 Debezium）的 Strimzi CRD 名称是什么？

<details>

<summary>显示答案</summary>

**答案：`KafkaConnect`**

**说明：**
KafkaConnect 用于定义 Connect worker，KafkaConnector 则表示单个连接器。应分别配置连接器资源管理以及 worker 身份验证/授权。
</details>

## 实操题

16. 使用本文的 operator-values.yaml，在新的 kafka namespace 中安装 Strimzi 1.3.0。

<details>

<summary>显示答案</summary>

**答案：**
```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.3.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io
```

**说明：**
这些命令适用于全新安装。固定 chart 版本，并验证 Operator 是否可用以及 CRD 是否就绪。现有安装则需要先审查 v1 转换、CRD 所有权和升级流程。
</details>

17. 编写一个包含三个 broker 的 KafkaNodePool，并使用本文中的 namespace、存储和三 AZ 约束。

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

**说明：**
此配置使用本文的标准 gp3-kafka StorageClass，并要求三个 AZ。确保 namespace/集群标签匹配，并通过 deleteClaim: false 保留 PVC。Auto Mode 使用单独的 StorageClass；节点池无法保证物理节点分离。
</details>

18. 假设经过身份验证的 kafka-client Pod 已就绪，创建 orders 并使用 TLS/SCRAM 生产者/消费者命令进行测试。

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

**说明：**
本文中的 KafkaUser、CA Secret 和经过身份验证的 kafka-client Pod 必须已存在。应使用 TLS/SCRAM 客户端属性，而非明文端点。检查现有 topic 中的第一条记录是否确实是刚刚发送的消息。
</details>

19. 定义一个 SCRAM 用户，使其能够生产/消费 orders、使用 order-processor group，并执行幂等生产者操作。

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

**说明：**
同时启用 listener 身份验证和集群 authorizer。除了 topic ACL 外，此配置还授予 order-processor group Read 权限和幂等生产者能力。在实际服务中，可考虑为生产者和消费者使用不同的身份。
</details>

20. 编写 broker KafkaNodePool spec 下的模板片段，使其与实际标签匹配并要求三个符合条件的 AZ。

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

**说明：**
将此片段合并到 broker KafkaNodePool 的 spec 下。Metadata 标签与选择器匹配；如果没有三个符合条件的 AZ，minDomains=3 可能会导致 Pod 处于 Pending 状态。严格约束可能会在某个 AZ 故障后阻止替换 Pod；Kafka 机架感知是另一项独立配置。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/02-strimzi-operator.md) | [下一项测验：Kafka 运维](./03-kafka-operations-quiz.md)
