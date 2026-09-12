# Strimzi Operator Quiz

> **Reviewed**: 2026-09-12, Strimzi 1.2.0 / Kafka 4.3.1.

This quiz tests your understanding of Strimzi Operator fundamentals, installation methods, core CRDs, KRaft node roles, and EKS deployment considerations.

## Multiple Choice Questions

1. What kind of CNCF project is Strimzi?
   - A) A service mesh
   - B) An Operator for running Apache Kafka on Kubernetes
   - C) A container runtime
   - D) A CI/CD pipeline tool

<details>

<summary>Show Answer</summary>

**Answer: B) An Operator for running Apache Kafka on Kubernetes**

**Explanation:**
Strimzi 1.2 is a CNCF incubating project that reconciles desired state in custom resources. Current Kafka Pod management uses StrimziPodSet. An Operator does not automatically complete every operating policy or availability guarantee.
</details>

2. Which of the following is LEAST accurate as a challenge of running Kafka directly as a StatefulSet without Strimzi?
   - A) Handling sequential rolling upgrades
   - B) Issuing and rotating TLS certificates
   - C) Building container images becomes impossible
   - D) Managing data movement during partition rebalancing

<details>

<summary>Show Answer</summary>

**Answer: C) Building container images becomes impossible**

**Explanation:**
Direct operation is possible but requires implementing upgrade, certificate, storage and reassignment procedures. Strimzi reconciles repetitive work; data recovery and availability policies still need validation.
</details>

3. What command adds the Strimzi Helm repository before installing the Cluster Operator?
   - A) `helm repo add strimzi https://strimzi.io/charts/`
   - B) `helm repo add kafka https://kafka.apache.org/charts/`
   - C) `helm repo add strimzi https://github.com/strimzi/charts/`
   - D) `helm install strimzi https://strimzi.io/`

<details>

<summary>Show Answer</summary>

**Answer: A) `helm repo add strimzi https://strimzi.io/charts/`**

**Explanation:**
Add the official chart repository and pin 1.2.0 for a new installation. Existing beta APIs/CRDs require the official migration procedure first; a new namespace does not avoid cluster-scoped CRD conflicts.
</details>

4. What namespace scope does the Strimzi Cluster Operator watch by default?
   - A) Every namespace in the cluster
   - B) All `kube-system` namespaces
   - C) Only the namespace it is deployed into
   - D) Only the `default` namespace

<details>

<summary>Show Answer</summary>

**Answer: C) Only the namespace it is deployed into**

**Explanation:**
The default chart watches its release namespace. Chart 1.2 includes/deduplicates that namespace alongside additional watchNamespaces and creates RoleBindings. Changing the environment variable alone can leave missing RBAC.
</details>

5. Which block is unsupported in current Strimzi 1.2 KRaft deployments?
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>Show Answer</summary>

**Answer: B) `Kafka.spec.zookeeper`**

**Explanation:**
Current Strimzi 1.2 uses KRaft and does not support the ZooKeeper block. KafkaNodePool defines controller and broker roles; legacy activation annotations are not needed.
</details>

6. Which value is NOT a valid entry for `KafkaNodePool.spec.roles`?
   - A) `controller`
   - B) `broker`
   - C) A dual-role combining `controller` and `broker`
   - D) `zookeeper`

<details>

<summary>Show Answer</summary>

**Answer: D) `zookeeper`**

**Explanation:**
Actual enum values are controller and broker. Both can be listed as [controller, broker]; dual-role is not a separate string value.
</details>

7. Why choose three controller voters?
   - A) It must always match the broker count
   - B) A majority of two remains after one voter failure
   - C) Kafka client libraries require at least 3 controllers
   - D) EBS volume limits require it

<details>

<summary>Show Answer</summary>

**Answer: B) A majority of two remains after one voter failure**

**Explanation:**
Three voters retain a majority of two after one failure. Even-sized groups also have a majority; odd sizes are efficient for the same fault tolerance. Controller count is independent of broker count and still depends on connectivity and other conditions.
</details>

8. What is the StorageClass provisioner for the standard Amazon EBS CSI driver path?
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>Show Answer</summary>

**Answer: B) `ebs.csi.aws.com`**

**Explanation:**
Standard EBS CSI uses ebs.csi.aws.com. EKS Auto Mode uses ebs.csi.eks.amazonaws.com. Changing a StorageClass provisioner does not migrate existing PVCs.
</details>

9. What field is added to `KafkaNodePool.spec.template.pod` to spread broker Pods evenly across AZs?
   - A) `nodeSelector`
   - B) `topologySpreadConstraints`
   - C) `tolerations`
   - D) `priorityClassName`

<details>

<summary>Show Answer</summary>

**Answer: B) `topologySpreadConstraints`**

**Explanation:**
Selectors must match actual Pod labels. Requiring three eligible AZs also needs conditions such as minDomains: 3; maxSkew: 1 does not create three AZs. Check scheduling and Kafka replica rack placement separately.
</details>

10. What listener types can be added to `Kafka.spec.kafka.listeners` when external clients need to reach the Kafka brokers from outside the cluster?
    - A) `internal` and `clusterip`
    - B) `loadbalancer` or `nodeport`
    - C) Only `ingress`
    - D) External exposure is not supported

<details>

<summary>Show Answer</summary>

**Answer: B) `loadbalancer` or `nodeport`**

**Explanation:**
Strimzi creates LoadBalancer Services or NodePorts. The resulting cloud load balancer depends on controller/class. The article pins AWS Load Balancer Controller class and applies internal/IP-target settings to bootstrap and every broker Service.
</details>

## Short Answer Questions

11. Name the two internal Strimzi components responsible for synchronizing `KafkaTopic` and `KafkaUser` custom resources with actual Kafka resources.

<details>

<summary>Show Answer</summary>

**Answer: Topic Operator, User Operator**

**Explanation:**
Topic and User Operators can run in the enabled Entity Operator; standalone installations also exist. Topic/user CRs need the appropriate namespace and cluster label.
</details>

12. What environment variable configures the Cluster Operator to watch multiple namespaces?

<details>

<summary>Show Answer</summary>

**Answer: `STRIMZI_NAMESPACE`**

**Explanation:**
The variable is STRIMZI_NAMESPACE. For Helm-managed installations, use watchNamespaces/watchAnyNamespace values and matching RBAC rather than creating drift through kubectl set env.
</details>

13. What storage type in `KafkaNodePool.spec.storage` lets you attach multiple EBS volumes per broker to spread out I/O?

<details>

<summary>Show Answer</summary>

**Answer: JBOD (type: jbod)**

**Explanation:**
JBOD supports multiple volume IDs. It does not guarantee automatic data balancing or remove instance EBS/network limits. At most one volume can select kraftMetadata: shared.
</details>

14. Which condition indicates the Operator's last successful Kafka reconciliation?

<details>

<summary>Show Answer</summary>

**Answer: `Ready: True`**

**Explanation:**
Ready=True is the Operator's last reconciliation observation. Compare observedGeneration with current generation and check Pod readiness, quorum and actual authenticated client connectivity.
</details>

15. What is the name of the Strimzi CRD that defines a separate worker cluster for running source/sink connectors, such as Debezium?

<details>

<summary>Show Answer</summary>

**Answer: `KafkaConnect`**

**Explanation:**
KafkaConnect defines Connect workers and KafkaConnector represents individual connectors. Configure connector-resource management and worker authentication/authorization separately.
</details>

## Hands-on Questions

16. Using the article's operator-values.yaml, install Strimzi 1.2.0 into a new kafka namespace.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --version 1.2.0 --namespace kafka --create-namespace \
  -f operator-values.yaml --wait --timeout 10m
kubectl -n kafka rollout status deployment/strimzi-cluster-operator --timeout=300s
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io
```

**Explanation:**
These commands are for a new installation. Pin the chart and verify Operator availability/CRDs. Existing installations need v1 conversion and CRD ownership/upgrade review first.
</details>

17. Write a three-broker KafkaNodePool with the article's namespace, storage and three-AZ constraints.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
This uses the article's standard gp3-kafka StorageClass and three-AZ requirement. Match namespace/cluster labels and retain PVCs with deleteClaim: false. Auto Mode uses a separate StorageClass; pools do not guarantee physical-node separation.
</details>

18. Assuming the authenticated kafka-client Pod is ready, create orders and test it with TLS/SCRAM producer/consumer commands.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
The article's KafkaUser, CA Secret and authenticated kafka-client Pod must already exist. Use TLS/SCRAM client properties, not the plaintext endpoint. Inspect whether the first record in an existing topic is actually the one just sent.
</details>

19. Define a SCRAM user for producing/consuming orders, the order-processor group and idempotent producer operations.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Enable listener authentication and the cluster authorizer too. Besides topic ACLs, this grants order-processor group Read and idempotent-producer capability. Consider distinct producer/consumer identities in real services.
</details>

20. Write a template excerpt under broker KafkaNodePool spec that matches actual labels and requires three eligible AZs.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Merge this excerpt under spec in the broker KafkaNodePool. Metadata labels match selectors; minDomains=3 can leave Pods Pending without three eligible AZs. Strict constraints can block replacement Pods after an AZ loss; Kafka rack awareness is separate.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/02-strimzi-operator.md) | [Next Quiz: Kafka Operations](./03-kafka-operations-quiz.md)
