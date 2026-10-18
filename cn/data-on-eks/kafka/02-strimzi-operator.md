# 第 2 部分：Strimzi Operator

> **最后更新**：2026 年 10 月 16 日。Strimzi 1.3.0，Kafka 4.3.1。Strimzi 要求 Kubernetes 1.32 或更高版本；本地架构验证使用了 1.36.2。
> **验证**：通过 Kafka 原生 JAAS 解析器验证了两种 Helm 配置、67 个 Kubernetes/CRD 对象和五种凭证文件情况。未执行实时 EKS 安装、TLS 连接、broker ACL 强制执行、EBS 或 NLB 预置。

## 1. 范围和先决条件

这是一个包含三个专用控制器和三个 broker 的全新安装示例。它要求三个 AZ 中都有可调度容量，并且有合适的 StorageClass。升级现有集群是单独的操作。

Strimzi 是一个 CNCF 孵化项目，通过 Kubernetes Operators 协调 Kafka 资源。当前的 Cluster Operator 管理 StrimziPodSets、Pods、Services 和 PVC。启用后，Entity Operator 会运行 Topic Operator 和 User Operator，以协调 KafkaTopic 和 KafkaUser 资源。安装 Operator 并不会自动完成所有重新平衡、恢复或可用性策略。

先决条件：

- Kubernetes 1.32 或更高版本，以及受该集群支持的 kubectl 版本。“任何高于 1.28 的 kubectl 版本”并不适用于所有较新的集群。
- Helm 3；此处渲染使用 Helm 3.21.3。
- 适用于标准 EBS CSI 或 EKS Auto Mode 的卷预置程序和 IAM 设置。
- 三个 AZ 中均有可调度节点/容量，并且能够访问所需的镜像注册表。

Strimzi 1.0 及更高版本仅支持 `kafka.strimzi.io/v1`。请先转换旧版 beta 资源，并按照官方流程升级 CRD。CRD 的作用范围是整个集群：新建命名空间无法避免与现有定义冲突。Helm 的 `crds/` 目录在初始安装和升级现有 CRD 时的行为不同。以下 helm install 命令不是升级现有 0.45 集群的流程。

## 2. 安装 Cluster Operator

这些命令会更改实际集群。请确认上下文/命名空间，并仅将其用于全新安装。

**`operator-values.yaml`**

```yaml
watchNamespaces: []
watchAnyNamespace: false
replicas: 1
```

```bash
kubectl config current-context
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.3.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl wait --for=condition=Established --timeout=120s \
  crd/kafkas.kafka.strimzi.io crd/kafkanodepools.kafka.strimzi.io \
  crd/kafkatopics.kafka.strimzi.io crd/kafkausers.kafka.strimzi.io
```

默认情况下，chart 会监视其自身的命名空间。如需监视其他命名空间，请先创建这些命名空间，然后设置诸如 `watchNamespaces: [kafka-staging]` 的值。Chart 1.3 会添加/去重 release 命名空间，并渲染相应的 RoleBindings。仅使用 kubectl set env 更改监视环境变量，可能导致缺少 RBAC 并造成 Helm 漂移。

不要让 Helm、OLM 和手动管理同时接管同一安装。`watchAnyNamespace: true` 是显式的全集群范围选择，本示例中已禁用。

## 3. 存储和放置

### 标准 EBS CSI

此 StorageClass 使用标准 EBS CSI provisioner。应用前请检查是否存在同名资源。更改 provisioner 不会自动将现有卷迁移到其他驱动程序。

**`storageclass.yaml`**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

gp3 的基准性能为 3,000 IOPS 和 125 MiB/s。之前的 `throughput: "250"` 示例预置了额外吞吐量；它并非基准值。实例的 EBS/网络限制、分区复制和读取模式也会产生影响。JBOD 不会自动平衡数据，也不会消除实例级限制。

### EKS Auto Mode 替代方案

仅当使用 Auto Mode 时才选择这个单独的 StorageClass，并将**新 NodePool 的卷类别**设置为 `gp3-kafka-auto`。请使用适用于集群的 provisioner 路径。迁移现有 PVC 需要单独的流程。

**`storageclass-auto.yaml`**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka-auto
provisioner: ebs.csi.eks.amazonaws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
allowedTopologies:
  - matchLabelExpressions:
      - key: eks.amazonaws.com/compute-type
        values: [auto]
```

### 控制器和 broker 池

这些文件引用标准的 `gp3-kafka`。实际角色为 `controller` 和 `broker`；可以同时列出这两者，但 `dual-role` 不是单独的枚举值。

两个池都需要三个 AZ。选择器会匹配实际的自定义 Pod 标签 `docs.example.com/kafka-role` 以及集群标签，并设置 `minDomains: 3`。如果只有两个 AZ 有符合条件的节点，Pods 可能会保持 Pending 状态。在发生故障时，严格的约束也可能阻止在剩余 AZ 中创建替代 Pods。

单独的池可以隔离 Pod 角色/资源设置，但不一定会隔离物理工作节点。如果需要物理隔离，请使用节点亲和性。Kafka rack 感知和 Pod 调度属于不同层级。

**`controller-pool.yaml`**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: controller
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
  - controller
  storage:
    type: jbod
    volumes:
    - id: 0
      type: persistent-claim
      size: 20Gi
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
  resources:
    requests:
      cpu: '1'
      memory: 2Gi
    limits:
      memory: 2Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: controller
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
            docs.example.com/kafka-role: controller
```

**`broker-pool.yaml`**

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

`kraftMetadata: shared` 用于选择存放 KRaft 元数据的卷；每个池最多只能有一个卷使用它。`deleteClaim: false` 和 StorageClass Retain 是保留设置，不是备份。删除其他资源后，PVC/PV/EBS 卷仍可能保留并继续产生费用。

三个控制器在一个投票者发生故障后仍可保有两票的多数派。三个 broker 则满足单独的数据复制目标。奇数数量并不会自动保证安全；多数派可用性和连接状况仍然重要。

## 4. 已启用身份验证的 Kafka 集群

同时启用内部 TLS/SCRAM listener 和 ACL authorizer。若通过未经身份验证的明文 listener 进行测试，即使创建了 KafkaUser，也无法验证该用户的身份验证。

**`kafka-cluster.yaml`**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.3-IV0
    rack:
      topologyKey: topology.kubernetes.io/zone
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
    authorization:
      type: simple
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      share.coordinator.state.topic.replication.factor: 3
      share.coordinator.state.topic.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

Strimzi 1.3 使用 KRaft 和 node pools；不要添加旧版激活注解或 ZooKeeper 配置块。`rack.topologyKey` 会为副本放置提供 AZ 信息；它不会自动重新分配所有现有分区。

保持 Kafka 版本和 metadataVersion 兼容：此示例使用 4.3.1 / 4.3-IV0。不要在保留旧镜像覆盖设置的同时更改版本字段。节点 ID 会在整个集群中分配；不要假定每个池都有以 -0 结尾的 Pod。

```bash
# Use the appropriate StorageClass file for the cluster.
kubectl apply -f storageclass.yaml
kubectl apply -f controller-pool.yaml -f broker-pool.yaml -f kafka-cluster.yaml
kubectl -n kafka wait kafka/my-cluster --for=condition=Ready --timeout=20m
kubectl -n kafka get kafka my-cluster \
  -o custom-columns=NAME:.metadata.name,GENERATION:.metadata.generation,OBSERVED:.status.observedGeneration
kubectl -n kafka get kafkanodepools
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

Ready=True 表示 Operator 观察到的协调结果。请将 observedGeneration 与当前 generation 进行比较，并检查 Pod 就绪状态、quorum 和客户端连接情况。较早的 Ready 条件或单独的 Running 阶段，都不能证明当前所有组件均正常。

## 5. Topic 和用户

**`orders-topic.yaml`**

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

**`order-service-user.yaml`**

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

在冒烟测试中，此用户可以向 orders 写入数据/从中读取数据，并读取 order-processor group。Topic ACL 不会授予 group ACL。Cluster IdempotentWrite 支持幂等 producer 操作；它不能替代其他 topic 上的 Write 权限。对于实际服务，请考虑使用单独的 producer/consumer 身份。

User Operator 会创建一个以用户命名的 Secret，其中包含 password 和 sasl.jaas.config 条目。还必须启用集群 authorizer 和 listener 身份验证。KafkaConnect/KafkaConnector 用于定义单独的 workers/connectors；第 5 部分介绍这些配置。

```bash
kubectl apply -f orders-topic.yaml -f order-service-user.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
kubectl -n kafka wait kafkauser/order-service --for=condition=Ready --timeout=5m
```

## 6. 测试 TLS/SCRAM 连接

此文件包含一个临时客户端 Pod 和配置生成代码。凭证从 Secret 卷中读取，经过转义以适用于 Java properties，然后写入文件，不会将密码放入命令参数、环境变量或日志中。Python init container 和 Kafka container 使用相同的 UID。

客户端通过 PEM truststore 信任公有 CA，并保留主机名验证。Kafka 镜像固定为 4.3.1 版本的 digest。不需要在运行时安装软件包，也不假定 Kafka 镜像中存在 Python。

**`client.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-client-config
  namespace: kafka
data:
  client_config.py: |
    """Build Kafka client properties from mounted files without printing credentials."""
    import argparse
    from pathlib import Path


    def property_value(value):
        encoded = []
        escapes = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t", "\f": "\\f"}
        for index, character in enumerate(value):
            if character in escapes:
                encoded.append(escapes[character])
            elif character == " " and index == 0:
                encoded.append("\\ ")
            elif 0x20 <= ord(character) <= 0x7e:
                encoded.append(character)
            else:
                units = character.encode("utf-16-be")
                encoded.extend(f"\\u{int.from_bytes(units[i:i+2], 'big'):04x}" for i in range(0, len(units), 2))
        return "".join(encoded)


    def make_config(jaas, bootstrap, ca_file):
        if not jaas.strip():
            raise ValueError("The mounted JAAS configuration is empty")
        values = {
            "bootstrap.servers": bootstrap,
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.jaas.config": jaas.strip(),
            "ssl.truststore.type": "PEM",
            "ssl.truststore.location": ca_file,
            "ssl.endpoint.identification.algorithm": "https",
        }
        return "".join(f"{key}={property_value(value)}\n" for key, value in values.items())


    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("--jaas-file", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--ca-file", required=True)
        parser.add_argument("--bootstrap", required=True)
        args = parser.parse_args()
        args.output.write_text(make_config(args.jaas_file.read_text(), args.bootstrap, args.ca_file), encoding="ascii")
        args.output.chmod(0o600)
---
apiVersion: v1
kind: Pod
metadata:
  name: kafka-client
  namespace: kafka
  labels:
    app: kafka-client
spec:
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    runAsGroup: 1001
    fsGroup: 1001
    seccompProfile:
      type: RuntimeDefault
  initContainers:
  - name: client-config
    image: python:3.12.13-slim
    command:
    - python3
    - /bootstrap/client_config.py
    args:
    - --jaas-file
    - /user/sasl.jaas.config
    - --output
    - /client/client.properties
    - --ca-file
    - /ca/ca.crt
    - --bootstrap
    - my-cluster-kafka-bootstrap.kafka.svc:9093
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        memory: 128Mi
    volumeMounts:
    - name: bootstrap
      mountPath: /bootstrap
      readOnly: true
    - name: user
      mountPath: /user
      readOnly: true
    - name: client
      mountPath: /client
  containers:
  - name: client
    image: quay.io/strimzi/kafka@sha256:e90a1a74af4226f3ca4d1ebef3ab13bdb09754ae17ca4c1444f7fcbb0ca8ea9a
    command:
    - /bin/sh
    - -c
    args:
    - sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    env:
    - name: LOG_DIR
      value: /tmp/kafka-client-logs
    - name: KAFKA_HEAP_OPTS
      value: -Xms128m -Xmx512m
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        memory: 1Gi
    volumeMounts:
    - name: client
      mountPath: /client
      readOnly: true
    - name: ca
      mountPath: /ca
      readOnly: true
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: bootstrap
    configMap:
      name: kafka-client-config
  - name: user
    secret:
      secretName: order-service
      items:
      - key: sasl.jaas.config
        path: sasl.jaas.config
  - name: ca
    secret:
      secretName: my-cluster-cluster-ca-cert
      items:
      - key: ca.crt
        path: ca.crt
  - name: client
    emptyDir: {}
  - name: tmp
    emptyDir: {}
```

```bash
kubectl apply -f client.yaml
kubectl -n kafka wait pod/kafka-client --for=condition=Ready --timeout=5m
printf 'strimzi-auth-smoke-test\n' |
  kubectl -n kafka exec -i kafka-client -- \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
    --producer.config /client/client.properties \
    --producer-property acks=all --producer-property enable.idempotence=true \
    --topic orders
kubectl -n kafka exec kafka-client -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server my-cluster-kafka-bootstrap.kafka.svc:9093 \
  --consumer.config /client/client.properties --group order-processor \
  --topic orders --from-beginning --max-messages 1 --timeout-ms 10000
kubectl -n kafka delete pod kafka-client
```

这是针对新建实验 topic 的连接冒烟测试。现有 topic 可能包含较早的记录，因此请检查输出，不要假定第一条记录就是刚发送的记录。实际验证还应涵盖对未授权 topic/group 的拒绝、身份验证失败、CA 轮换、broker endpoint 访问和恢复。本章的本地验证没有发送任何 Kafka 消息。

## 7. 可选：Kubernetes 外部的 VPC 客户端

此合并补丁通过 **AWS Load Balancer Controller** 创建内部 NLB。它包含现有 TLS listener，因为 JSON merge patch 会替换整个 listeners 数组。使用前，请将 10.0.0.0/16 替换为实际获批的客户端 CIDR。

configuration.class 会成为生成的 Service loadBalancerClass。匹配的 internal/IP-target 注解会应用于 bootstrap 和每个 broker Service，不会假定 broker ID 为 0/1/2。Auto Mode 负载均衡需要单独确认 controller class 和受支持的选项。

**`external-listener.patch.yaml`**

```yaml
spec:
  kafka:
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
      - name: external
        port: 9094
        type: loadbalancer
        tls: true
        authentication:
          type: scram-sha-512
        configuration:
          class: service.k8s.aws/nlb
          allocateLoadBalancerNodePorts: false
          loadBalancerSourceRanges: ["10.0.0.0/16"]
          bootstrap:
            annotations:
              service.beta.kubernetes.io/aws-load-balancer-scheme: internal
              service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
          perBrokerAnnotationsTemplate:
            service.beta.kubernetes.io/aws-load-balancer-scheme: internal
            service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file external-listener.patch.yaml
kubectl -n kafka get services -l strimzi.io/cluster=my-cluster
kubectl -n kafka get kafka my-cluster -o jsonpath='{.status.listeners}'
```

此选项会创建 bootstrap 和每个 broker 对应的 LoadBalancer Services，并产生相应费用。客户端必须能够访问元数据中返回的每个 broker endpoint，而不仅仅是 bootstrap。添加 DNS 记录或切换到 NodePort 并不能自动解决路由、TLS 或节点生命周期方面的要求。

## 后续步骤和参考资料

- [Kafka 运维](./03-kafka-operations.md)
- [Kafka 概览](./README.md)
- [测验](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
- [Strimzi 1.3.0 部署](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Strimzi v1 API 转换](https://strimzi.io/docs/operators/1.0.0/deploying.html#assembly-api-conversion-str)
- [Strimzi 1.3.0 发布版本](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.3.0)
- [EBS gp3 性能](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
