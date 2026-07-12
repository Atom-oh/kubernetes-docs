# Strimzi Operator 测验

本测验用于检验你对 Strimzi Operator 基础知识、安装方法、核心 CRDs、KRaft 节点角色以及 EKS 部署注意事项的理解。

## 选择题

1. Strimzi 是哪种 CNCF 项目？
   - A) 一个 service mesh
   - B) 一个用于在 Kubernetes 上运行 Apache Kafka 的 Operator
   - C) 一个 container runtime
   - D) 一个 CI/CD pipeline 工具

<details>

<summary>显示答案</summary>

**答案：B) 一个用于在 Kubernetes 上运行 Apache Kafka 的 Operator**

**解析：**
Strimzi 是一个 CNCF Incubating 项目，它使用 Kubernetes Operator 模式来管理 Apache Kafka 集群的部署和完整生命周期，包括安装、升级、扩缩容和证书管理。你无需手动将 Kafka brokers 编写为 StatefulSet，而是通过 CRDs 声明期望状态，Operator 会协调实际集群状态使其与期望状态一致。
</details>

2. 以下哪一项作为不使用 Strimzi、直接以 StatefulSet 运行 Kafka 的挑战，最不准确？
   - A) 处理顺序滚动升级
   - B) 签发和轮换 TLS 证书
   - C) 构建 container images 变得不可能
   - D) 在 partition 重新平衡期间管理数据移动

<details>

<summary>显示答案</summary>

**答案：C) 构建 container images 变得不可能**

**解析：**
直接以 StatefulSet 运行 Kafka 本身并不是不可能。真正的问题在于运维复杂性和脆弱性：顺序升级、证书轮换以及重新平衡期间的数据移动都很难手动管理，并且容易出错。Strimzi 通过 CRDs 和 Operator 逻辑自动化处理所有这些工作。
</details>

3. 在安装 Cluster Operator 之前，哪个命令会添加 Strimzi Helm repository？
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>显示答案</summary>

**答案：A) `helm repo add strimzi https://strimzi.io/charts/`**

**解析：**
Strimzi 的官方 Helm repository 是 `https://strimzi.io/charts/`。添加后，可使用 `helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator --namespace kafka --create-namespace` 安装 Cluster Operator。
</details>

4. Strimzi Cluster Operator 默认 watch 的 namespace 范围是什么？
   - A) 集群中的每个 namespace
   - B) 所有 `kube-system` namespaces
   - C) 只有它部署到的 namespace
   - D) 只有 `default` namespace

<details>

<summary>显示答案</summary>

**答案：C) 只有它部署到的 namespace**

**解析：**
默认情况下，Cluster Operator 只 watch 自身 namespace 中的 resources。若要 watch 多个 namespaces，请在 Operator Deployment 上将 `STRIMZI_NAMESPACE` environment variable 设置为逗号分隔的 namespace 列表，或设置为 `*` 以将 watch 范围扩展到整个集群。
</details>

5. Strimzi 0.45+ 将 KRaft mode 设为默认后，哪个字段变得不再需要？
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>显示答案</summary>

**答案：B) `Kafka.spec.zookeeper`**

**解析：**
由于 KRaft mode 已成为默认模式，controller quorum 可以在没有 ZooKeeper 的情况下直接管理 metadata，因此以前必需的 `Kafka.spec.zookeeper` block 不再需要。Broker 和 controller 角色改为通过单独的 `KafkaNodePool` resources 定义。
</details>

6. 哪个值不是 `KafkaNodePool.spec.roles` 的有效条目？
   - A) `controller`
   - B) `broker`
   - C) 同时组合 `controller` 和 `broker` 的双角色
   - D) `zookeeper`

<details>

<summary>显示答案</summary>

**答案：D) `zookeeper`**

**解析：**
基于 KRaft 的 `KafkaNodePool` 上的 `roles` 字段只支持 `controller`、`broker`，或双角色组合（`[controller, broker]`）。`zookeeper` 不是有效角色 — ZooKeeper 在 KRaft mode 中完全不存在。
</details>

7. 以 3 个节点运行 controller node pool 的主要原因是什么？
   - A) 它必须始终与 broker 数量一致
   - B) controller quorum 需要多数票，因此奇数数量更安全
   - C) Kafka client libraries 至少需要 3 个 controllers
   - D) EBS volume limits 要求如此

<details>

<summary>显示答案</summary>

**答案：B) controller quorum 需要多数票，因此奇数数量更安全**

**解析：**
KRaft controller quorum 使用类似 Raft 的 consensus protocol 运行，该协议在 leader election 和 metadata commits 时需要多数票。偶数数量的 controllers 可能导致影响可用性的分票场景，因此通常使用 3 或 5 这样的奇数数量。这一决定与 broker 数量无关。
</details>

8. 在 Amazon EKS 上为 Kafka brokers 定义 EBS StorageClass 时使用的 CSI provisioner 名称是什么？
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>显示答案</summary>

**答案：B) `ebs.csi.aws.com`**

**解析：**
Amazon EBS CSI driver 使用 provisioner 名称 `ebs.csi.aws.com`。`kubernetes.io/aws-ebs` 是已弃用的 in-tree provisioner。`KafkaNodePool.spec.storage` 下的 `persistent-claim` volumes 引用由该 provisioner 支持的 StorageClass，以动态配置 EBS gp3 volumes。
</details>

9. 要将 broker Pods 均匀分布到各 AZ，需要向 `KafkaNodePool.spec.template.pod` 添加哪个字段？
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>显示答案</summary>

**答案：B) `topologySpreadConstraints`**

**解析：**
`topologySpreadConstraints` 是一种 scheduling constraint，它会基于 `topologyKey`（例如 `topology.kubernetes.io/zone`）均匀分布 Pods。将 Kafka brokers 分布到多个 AZ 意味着单个 AZ 故障不会导致整个集群的可用性中断。设置 `whenUnsatisfiable: DoNotSchedule` 会通过阻止违反约束的调度来严格执行该约束。
</details>

10. 当 external clients 需要从集群外访问 Kafka brokers 时，可以向 `Kafka.spec.kafka.listeners` 添加哪些 listener types？
    - A) `internal` 和 `clusterip`
    - B) `loadbalancer` 或 `nodeport`
    - C) 只有 `ingress`
    - D) 不支持 external exposure

<details>

<summary>显示答案</summary>

**答案：B) `loadbalancer` 或 `nodeport`**

**解析：**
Strimzi listeners 支持 `internal`、`route`、`ingress`、`loadbalancer` 和 `nodeport` 类型。在 EKS 上，external access 通常通过 `loadbalancer`（为 bootstrap/broker 自动配置一个 AWS NLB）或 `nodeport`（worker node ports 加外部 load balancer）提供。`loadbalancer` 类型可以通过 annotations 进行调优，以控制 AWS Load Balancer Controller 的 NLB 设置，例如 internal 与 internet-facing scheme。
</details>

## 简答题

11. 请说出两个内部 Strimzi components，它们负责将 `KafkaTopic` 和 `KafkaUser` custom resources 与实际 Kafka resources 同步。

<details>

<summary>显示答案</summary>

**答案：Topic Operator, User Operator**

**解析：**
Topic Operator 会将 `KafkaTopic` custom resources 单向同步到实际 Kafka topics（CR 是真相来源），而 User Operator 会基于 `KafkaUser` custom resources 管理 SCRAM-SHA-512 或 TLS authentication credentials 和 ACLs。两者作为 Entity Operator 的一部分，打包到每个 Kafka 集群的单个 Pod 中。
</details>

12. 哪个 environment variable 用于配置 Cluster Operator watch 多个 namespaces？

<details>

<summary>显示答案</summary>

**答案：`STRIMZI_NAMESPACE`**

**解析：**
在 Cluster Operator Deployment 上设置 `STRIMZI_NAMESPACE` 可控制其 watch 的 namespace 范围。你可以指定逗号分隔的 namespace 列表，或指定 `*` 以将 watch 范围扩展到整个集群。
</details>

13. `KafkaNodePool.spec.storage` 中哪种 storage type 允许你为每个 broker 挂载多个 EBS volumes 以分散 I/O？

<details>

<summary>显示答案</summary>

**答案：JBOD (type: jbod)**

**解析：**
JBOD (Just a Bunch Of Disks) storage 允许单个 broker 使用多个 `persistent-claim` volumes，每个 volume 都由不同的 `id` 标识。这样可以将 I/O 分布到多个 volumes，而不是受限于单个 EBS volume 的 throughput ceiling。
</details>

14. `Kafka` resource 上的哪个 status condition 表示 brokers/controllers 已形成健康的 quorum 且 listeners 处于活动状态？

<details>

<summary>显示答案</summary>

**答案：`Ready: True`**

**解析：**
当你使用 `kubectl get kafka -n kafka` 检查 `Kafka` resource 的 status 时，`Ready` condition 设置为 `True` 表示所有集群 components（brokers、controllers、listeners、Entity Operator）都在正常工作。
</details>

15. 定义用于运行 source/sink connectors（例如 Debezium）的独立 worker cluster 的 Strimzi CRD 名称是什么？

<details>

<summary>显示答案</summary>

**答案：`KafkaConnect`**

**解析：**
`KafkaConnect` 是定义 Kafka Connect worker cluster 的 CRD。各个 connector instances 通过 `KafkaConnector` custom resources 以 declarative 方式管理，并部署到 `KafkaConnect` cluster 上。
</details>

## 实操题

16. 写出通过 Helm 将 Strimzi Cluster Operator 安装到 `kafka` namespace 的完整命令序列。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# Add the Strimzi Helm repository
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# Install the Cluster Operator into the kafka namespace
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --namespace kafka \
  --create-namespace \
  --version 0.45.0

# Verify the installation
kubectl get pods -n kafka
kubectl get crd | grep strimzi
```

**解析：**
`helm repo add` 会注册 Strimzi repository，`helm repo update` 会获取最新的 chart metadata。向 `helm install` 添加 `--create-namespace` 会在 `kafka` namespace 尚不存在时自动创建它。安装后，使用 `kubectl get pods -n kafka` 确认 Cluster Operator Pod 为 `Running`，并使用 `kubectl get crd | grep strimzi` 确认 `Kafka` 和 `KafkaNodePool` 等 CRDs 已注册。
</details>

17. 编写一个由 3 个仅 broker 节点组成的 `KafkaNodePool`，每个节点使用一个基于 gp3 的 100Gi `persistent-claim` volume。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: broker
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
  resources:
    requests:
      cpu: "2"
      memory: 4Gi
    limits:
      cpu: "4"
      memory: 4Gi
```

**解析：**
`strimzi.io/cluster` label 必须与此 node pool 所属的 `Kafka` resource 名称匹配。`roles: [broker]` 指定仅 broker 节点，而 `storage.type: jbod` 下的 `persistent-claim` volume 会配置一个 100Gi、由 EBS 支持的 persistent volume。`class` 引用由 `ebs.csi.aws.com` provisioner 支持的 StorageClass。
</details>

18. 创建一个名为 `orders`、具有 12 个 partitions 和 3 个 replicas 的 `KafkaTopic`，然后写出使用 console producer 和 consumer 测试它的命令。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
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
    min.insync.replicas: 2
```

```bash
# Apply the topic
kubectl apply -f orders-topic.yaml -n kafka
kubectl get kafkatopic -n kafka

# Producer test
kubectl run kafka-producer -n kafka -ti \
  --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders

# Consumer test
kubectl run kafka-consumer -n kafka -ti \
  --image=quay.io/strimzi/kafka:0.45.0-kafka-3.9.0 --rm=true --restart=Never -- \
  bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic orders --from-beginning
```

**解析：**
`strimzi.io/cluster` label 告诉 Topic Operator 此 `KafkaTopic` 属于哪个 `Kafka` cluster。应用后，`kubectl get kafkatopic -n kafka` 会确认 topic 已实际创建。producer/consumer 测试会将 Strimzi 的 Kafka image 作为一次性 Pod 运行，并连接到 bootstrap Service（`my-cluster-kafka-bootstrap:9092`）。
</details>

19. 编写一个使用 SCRAM-SHA-512 authentication 的 `KafkaUser`，并且只授权其对 `orders` topic 执行 Read、Write 和 Describe 操作。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
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
        operations: [Read, Write, Describe]
```

**解析：**
`authentication.type: scram-sha-512` 会指示 User Operator 生成 SCRAM credentials 并将其存储在 Secret 中。`authorization.type: simple` 使用 Kafka 内置的基于 ACL 的 authorization，`acls` 列表将该用户限制为仅能对 `orders` topic 执行 `Read`、`Write` 和 `Describe` 操作 — 在 CR 级别以 declarative 方式实现 least privilege。
</details>

20. 向 `KafkaNodePool` 的 `spec.template.pod` 添加 `topologySpreadConstraints`，以将 broker Pods 均匀分布到各 AZ。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: broker
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles: [broker]
  template:
    pod:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              strimzi.io/cluster: my-cluster
              strimzi.io/name: my-cluster-broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 100Gi
        class: gp3-kafka
```

**解析：**
`topologyKey: topology.kubernetes.io/zone` 会根据 EKS worker nodes 上的 AZ label 分布 Pods。`maxSkew: 1` 允许 AZ 之间的 Pod 数量最多相差 1，`whenUnsatisfiable: DoNotSchedule` 会在无法满足约束时直接阻止调度，从而保证均匀分布。`labelSelector` 决定用于计算 skew 的 Pods 集合（同一个 broker node pool）。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/02-strimzi-operator.md) | [下一测验：Kafka Operations](./03-kafka-operations-quiz.md)
