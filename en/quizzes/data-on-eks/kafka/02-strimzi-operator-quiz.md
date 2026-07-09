# Strimzi Operator Quiz

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
Strimzi is a CNCF Incubating project that uses the Kubernetes Operator pattern to manage the deployment and full lifecycle of Apache Kafka clusters, including installation, upgrades, scaling, and certificate management. Instead of hand-writing Kafka brokers as a StatefulSet, you declare the desired state through CRDs and the Operator reconciles the actual cluster state to match it.
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
Running Kafka directly as a StatefulSet is not impossible in itself. The real problem is operational complexity and fragility: sequential upgrades, certificate rotation, and data movement during rebalancing are hard to manage by hand and error-prone. Strimzi automates all of this through CRDs and Operator logic.
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
Strimzi's official Helm repository is `https://strimzi.io/charts/`. After adding it, the Cluster Operator is installed with `helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator --namespace kafka --create-namespace`.
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
By default, the Cluster Operator only watches resources in its own namespace. To watch multiple namespaces, set the `STRIMZI_NAMESPACE` environment variable on the Operator Deployment to a comma-separated list of namespaces, or `*` to expand the watch scope to the entire cluster.
</details>

5. Which field became unnecessary once Strimzi 0.45+ made KRaft mode the default?
   - A) `Kafka.spec.kafka.listeners`
   - B) `Kafka.spec.zookeeper`
   - C) `Kafka.spec.entityOperator`
   - D) `KafkaNodePool.spec.storage`

<details>

<summary>Show Answer</summary>

**Answer: B) `Kafka.spec.zookeeper`**

**Explanation:**
With KRaft mode as the default, the controller quorum manages metadata directly without ZooKeeper, so the previously required `Kafka.spec.zookeeper` block is no longer needed. Broker and controller roles are instead defined through separate `KafkaNodePool` resources.
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
The `roles` field on a KRaft-based `KafkaNodePool` only supports `controller`, `broker`, or a dual-role combination (`[controller, broker]`). `zookeeper` is not a valid role — ZooKeeper does not exist at all in KRaft mode.
</details>

7. What is the main reason for running the controller node pool with 3 nodes?
   - A) It must always match the broker count
   - B) The controller quorum requires a majority vote, so an odd number is safer
   - C) Kafka client libraries require at least 3 controllers
   - D) EBS volume limits require it

<details>

<summary>Show Answer</summary>

**Answer: B) The controller quorum requires a majority vote, so an odd number is safer**

**Explanation:**
The KRaft controller quorum operates using a Raft-like consensus protocol that requires a majority vote for leader election and metadata commits. An even number of controllers can lead to split-vote scenarios that hurt availability, so odd counts like 3 or 5 are typical. This is decided independently of the broker count.
</details>

8. What is the name of the CSI provisioner used when defining an EBS StorageClass for Kafka brokers on Amazon EKS?
   - A) `kubernetes.io/aws-ebs`
   - B) `ebs.csi.aws.com`
   - C) `efs.csi.aws.com`
   - D) `aws.amazon.com/ebs`

<details>

<summary>Show Answer</summary>

**Answer: B) `ebs.csi.aws.com`**

**Explanation:**
The Amazon EBS CSI driver uses the provisioner name `ebs.csi.aws.com`. `kubernetes.io/aws-ebs` is the deprecated in-tree provisioner. `persistent-claim` volumes under `KafkaNodePool.spec.storage` reference a StorageClass backed by this provisioner to dynamically provision EBS gp3 volumes.
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
`topologySpreadConstraints` is a scheduling constraint that spreads Pods evenly based on a `topologyKey` (for example, `topology.kubernetes.io/zone`). Spreading Kafka brokers across AZs means a single AZ outage doesn't take down the whole cluster's availability. Setting `whenUnsatisfiable: DoNotSchedule` enforces the constraint strictly by blocking scheduling that would violate it.
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
Strimzi listeners support `internal`, `route`, `ingress`, `loadbalancer`, and `nodeport` types. On EKS, external access is typically provided through `loadbalancer` (auto-provisions an AWS NLB per bootstrap/broker) or `nodeport` (worker node ports plus an external load balancer). The `loadbalancer` type can be tuned via annotations that control the AWS Load Balancer Controller's NLB settings, such as internal vs. internet-facing scheme.
</details>

## Short Answer Questions

11. Name the two internal Strimzi components responsible for synchronizing `KafkaTopic` and `KafkaUser` custom resources with actual Kafka resources.

<details>

<summary>Show Answer</summary>

**Answer: Topic Operator, User Operator**

**Explanation:**
The Topic Operator unidirectionally synchronizes `KafkaTopic` custom resources onto actual Kafka topics (the CR is the source of truth), while the User Operator manages SCRAM-SHA-512 or TLS authentication credentials and ACLs based on `KafkaUser` custom resources. Both are bundled into a single Pod per Kafka cluster as part of the Entity Operator.
</details>

12. What environment variable configures the Cluster Operator to watch multiple namespaces?

<details>

<summary>Show Answer</summary>

**Answer: `STRIMZI_NAMESPACE`**

**Explanation:**
Setting `STRIMZI_NAMESPACE` on the Cluster Operator Deployment controls the namespace scope it watches. You can specify a comma-separated list of namespaces, or `*` to expand the watch scope to the entire cluster.
</details>

13. What storage type in `KafkaNodePool.spec.storage` lets you attach multiple EBS volumes per broker to spread out I/O?

<details>

<summary>Show Answer</summary>

**Answer: JBOD (type: jbod)**

**Explanation:**
JBOD (Just a Bunch Of Disks) storage lets a single broker use multiple `persistent-claim` volumes, each identified by a distinct `id`. This distributes I/O across several volumes rather than being limited by a single EBS volume's throughput ceiling.
</details>

14. What status condition on the `Kafka` resource indicates that brokers/controllers have formed a healthy quorum and listeners are active?

<details>

<summary>Show Answer</summary>

**Answer: `Ready: True`**

**Explanation:**
When you check the `Kafka` resource's status with `kubectl get kafka -n kafka`, a `Ready` condition set to `True` means all cluster components (brokers, controllers, listeners, Entity Operator) are functioning correctly.
</details>

15. What is the name of the Strimzi CRD that defines a separate worker cluster for running source/sink connectors, such as Debezium?

<details>

<summary>Show Answer</summary>

**Answer: `KafkaConnect`**

**Explanation:**
`KafkaConnect` is the CRD that defines a Kafka Connect worker cluster. Individual connector instances are managed declaratively through `KafkaConnector` custom resources, which are deployed onto a `KafkaConnect` cluster.
</details>

## Hands-on Questions

16. Write the full command sequence to install the Strimzi Cluster Operator via Helm into the `kafka` namespace.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
`helm repo add` registers the Strimzi repository, and `helm repo update` fetches the latest chart metadata. Adding `--create-namespace` to `helm install` automatically creates the `kafka` namespace if it doesn't already exist. After installing, use `kubectl get pods -n kafka` to confirm the Cluster Operator Pod is `Running`, and `kubectl get crd | grep strimzi` to confirm CRDs like `Kafka` and `KafkaNodePool` are registered.
</details>

17. Write a `KafkaNodePool` consisting of 3 broker-only nodes, each using a 100Gi gp3-based `persistent-claim` volume.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
The `strimzi.io/cluster` label must match the name of the `Kafka` resource this node pool belongs to. `roles: [broker]` designates broker-only nodes, and the `persistent-claim` volume under `storage.type: jbod` provisions a 100Gi EBS-backed persistent volume. `class` references a StorageClass backed by the `ebs.csi.aws.com` provisioner.
</details>

18. Create a `KafkaTopic` named `orders` with 12 partitions and 3 replicas, then write the commands to test it with the console producer and consumer.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
The `strimzi.io/cluster` label tells the Topic Operator which `Kafka` cluster this `KafkaTopic` belongs to. After applying, `kubectl get kafkatopic -n kafka` confirms the topic was actually created. The producer/consumer test runs Strimzi's Kafka image as a throwaway Pod that connects to the bootstrap Service (`my-cluster-kafka-bootstrap:9092`).
</details>

19. Write a `KafkaUser` with SCRAM-SHA-512 authentication that is only authorized to Read, Write, and Describe the `orders` topic.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
`authentication.type: scram-sha-512` instructs the User Operator to generate SCRAM credentials and store them in a Secret. `authorization.type: simple` uses Kafka's built-in ACL-based authorization, and the `acls` list restricts this user to only `Read`, `Write`, and `Describe` operations on the `orders` topic — implementing least privilege declaratively at the CR level.
</details>

20. Add a `topologySpreadConstraints` to a `KafkaNodePool`'s `spec.template.pod` to spread broker Pods evenly across AZs.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
`topologyKey: topology.kubernetes.io/zone` spreads Pods based on the AZ label on EKS worker nodes. `maxSkew: 1` allows at most a 1-Pod difference in count between AZs, and `whenUnsatisfiable: DoNotSchedule` blocks scheduling outright when the constraint can't be satisfied, guaranteeing even distribution. `labelSelector` determines which set of Pods (the same broker node pool) the skew is calculated against.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/02-strimzi-operator.md) | [Next Quiz: Kafka Operations](./03-kafka-operations-quiz.md)
