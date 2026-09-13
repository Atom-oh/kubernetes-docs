# 第 2 部分：Strimzi Operator

> **最后更新**：2026 年 9 月 12 日。Strimzi 1.2.0，Kafka 4.3.1。Strimzi 要求 Kubernetes 1.30 或更高版本；本地模式验证使用了 1.36.2。
> **验证**：验证了两种 Helm 配置、67 个 Kubernetes/CRD 对象，以及通过 Kafka 原生 JAAS 解析器验证的五种凭证文件场景。未执行实际 EKS 安装、TLS 连接、代理 ACL 强制实施、EBS 或 NLB 预置。

## 1. 范围和前提条件

这是一个全新安装示例，包含三个专用控制器和三个代理。它要求三个可用区中都有可调度容量，并具有合适的 StorageClass。升级现有集群是单独的操作。

Strimzi 是 CNCF 孵化项目，通过 Kubernetes Operator 协调 Kafka 资源。当前的 Cluster Operator 管理 StrimziPodSet、Pod、Service 和 PVC。启用 Entity Operator 后，它会运行 Topic Operator 和 User Operator，以协调 KafkaTopic 和 KafkaUser 资源。安装 Operator 并不会自动完成所有再平衡、恢复或可用性策略。

前提条件：

- Kubernetes 1.30 或更高版本，以及该集群支持的 kubectl 版本。“任何高于 1.28 的 kubectl 版本”并不适用于所有更新的集群。
- Helm 3；此处渲染使用了 Helm 3.21.3。
- 适用于标准 EBS CSI 或 EKS Auto Mode 的卷预置器和 IAM 配置。
- 三个可用区中均有可调度的节点/容量，并能访问所需的镜像仓库。

Strimzi 1.0 及更高版本仅支持 `kafka.strimzi.io/v1`。请先按照官方流程转换旧版 beta 资源并升级 CRD。CRD 属于集群作用域：新建命名空间无法避免与现有定义冲突。Helm 的 `crds/` 目录在首次安装和升级现有 CRD 时的行为不同。以下 helm install 命令不是现有 0.45 集群的升级流程。

## 2. 安装 Cluster Operator

这些命令会更改真实集群。请确认上下文/命名空间，并将其用于全新安装。

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
  --version 1.2.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl wait --for=condition=Established --timeout=120s \
  crd/kafkas.kafka.strimzi.io crd/kafkanodepools.kafka.strimzi.io \
  crd/kafkatopics.kafka.strimzi.io crd/kafkausers.kafka.strimzi.io
```

默认 chart 监视自身所在的命名空间。若要添加命名空间，请先创建它们，再设置诸如 `watchNamespaces: [kafka-staging]` 的值。Chart 1.2 会添加发布所在的命名空间并去重，同时渲染相应的 RoleBinding。仅使用 kubectl set env 更改监视环境变量可能导致 RBAC 缺失和 Helm 配置漂移。

不要让 Helm、OLM 和手动管理同时拥有同一安装的管理权。`watchAnyNamespace: true` 是显式的集群范围选择，本示例未启用。

## 3. 存储和放置

### 标准 EBS CSI

此 StorageClass 使用标准 EBS CSI 预置器。应用前请检查同名现有资源。更改预置器不会自动将现有卷迁移到另一个驱动。

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

gp3 的基准性能为 3,000 IOPS 和 125 MiB/s。之前的 `throughput: "250"` 示例预置了额外吞吐量，并非基准值。实例的 EBS/网络限制、分区复制和读取模式也很重要。JBOD 不会自动均衡数据，也不会消除实例级别的限制。

### EKS Auto Mode 备选方案

仅在使用 Auto Mode 时选择此独立的 StorageClass，并将**新 NodePool 的卷类**设为 `gp3-kafka-auto`。请使用适用于集群的预置器路径。迁移现有 PVC 需要单独的流程。

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

### 控制器池和代理池

这些文件引用标准的 `gp3-kafka`。实际角色为 `controller` 和 `broker`；两者可以同时列出，但 `dual-role` 不是独立的枚举值。

两个池都需要三个可用区。选择器匹配实际的自定义 Pod 标签 `docs.example.com/kafka-role` 和集群标签，并设置 `minDomains: 3`。当只有两个可用区具有符合条件的节点时，Pod 可能保持 Pending 状态。在发生故障时，这种严格约束也可能阻止在剩余可用区中调度替代 Pod。

独立的池隔离的是 Pod 角色/资源设置，并不一定隔离物理工作节点。若需要物理隔离，请使用节点亲和性。Kafka 机架感知和 Pod 调度运行在不同层面。

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

`kraftMetadata: shared` 选择用于存储 KRaft 元数据的卷；每个池最多只能有一个卷设置此项。`deleteClaim: false` 和 StorageClass Retain 是保留设置，并非备份。删除其他资源后，PVC/PV/EBS 卷可能仍然保留并持续产生费用。

三个控制器在一个投票成员故障后仍保有两个成员的多数派。三个代理满足的是另一项数据复制目标。奇数数量并不自动意味着安全；多数派可用性和连通性仍然重要。

## 4. 启用身份验证的 Kafka 集群

同时启用内部 TLS/SCRAM 监听器和 ACL 授权器。创建 KafkaUser 后通过未经身份验证的明文监听器进行测试，并不能验证该用户的身份验证。

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

Strimzi 1.2 使用 KRaft 和节点池；不要添加旧版启用注解或 ZooKeeper 配置块。`rack.topologyKey` 为副本放置提供可用区信息；它不会自动重新分配所有现有分区。

保持 Kafka 版本与 metadataVersion 兼容：本示例使用 4.3.1 / 4.3-IV0。不要在保留旧镜像覆盖设置的同时更改版本字段。节点 ID 在整个集群中分配；不要假定每个池都有名称以 -0 结尾的 Pod。

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

Ready=True 是 Operator 观察到的协调结果。请将 observedGeneration 与当前 generation 比较，并检查 Pod 就绪状态、法定人数和客户端连通性。旧的 Ready 条件或仅处于 Running 阶段，并不能证明当前所有组件都健康。

## 5. 主题和用户

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

在冒烟测试中，此用户可以向 orders 生产消息/从中消费消息，并读取 order-processor 消费者组。主题 ACL 不会授予消费者组 ACL。集群级 IdempotentWrite 支持幂等生产者操作；它不能替代对其他主题的 Write 权限。对于实际服务，请考虑使用独立的生产者/消费者身份。

User Operator 会创建一个以用户名命名的 Secret，包含 password 和 sasl.jaas.config 条目。同时还必须启用集群授权器和监听器身份验证。KafkaConnect/KafkaConnector 定义独立的工作进程/连接器；第 5 部分介绍这些配置。

```bash
kubectl apply -f orders-topic.yaml -f order-service-user.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
kubectl -n kafka wait kafkauser/order-service --for=condition=Ready --timeout=5m
```

## 6. 测试 TLS/SCRAM 连通性

此文件包含一个临时客户端 Pod 和配置生成代码。凭证从 Secret 卷读取，按 Java properties 格式转义并写入文件，不会将密码放入命令参数、环境变量或日志。Python 初始化容器与 Kafka 容器使用相同的 UID。

客户端通过 PEM 信任库信任公共 CA，并保留主机名验证。Kafka 镜像固定到 4.3.1 发布版本的摘要。无需在运行时安装软件包，也无需假定 Kafka 镜像中存在 Python。

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

这是针对新实验主题的连通性冒烟测试。现有主题可能包含较早的记录，因此应检查输出，而不是假定第一条记录就是刚发送的记录。实际验证还应涵盖拒绝未经授权的主题/消费者组访问、身份验证失败、CA 轮换、代理端点访问和恢复。本章的本地验证未发送任何 Kafka 消息。

## 7. 可选：Kubernetes 外部的 VPC 客户端

此合并补丁通过 **AWS Load Balancer Controller** 创建内部 NLB。由于 JSON 合并补丁会替换整个 listeners 数组，因此它包含现有 TLS 监听器。使用前，请将 10.0.0.0/16 替换为实际获准的客户端 CIDR。

configuration.class 会成为所生成 Service 的 loadBalancerClass。匹配的内部/IP 目标注解应用于引导 Service 和每个代理 Service，不假定代理 ID 为 0/1/2。Auto Mode 负载均衡需要单独确认控制器类及支持的选项。

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

此选项创建引导 LoadBalancer Service 和每个代理的 LoadBalancer Service，并产生相应费用。客户端必须能够访问元数据返回的每个代理端点，而不只是引导端点。添加 DNS 记录或切换到 NodePort 并不会自动解决路由、TLS 或节点生命周期要求。

## 后续步骤和参考资料

- [Kafka 运维](./03-kafka-operations.md)
- [Kafka 概述](./README.md)
- [测验](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
- [Strimzi 1.2.0 部署](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Strimzi v1 API 转换](https://strimzi.io/docs/operators/1.0.0/deploying.html#assembly-api-conversion-str)
- [Strimzi 1.2.0 发布](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.2.0)
- [EBS gp3 性能](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
