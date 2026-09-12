# Part 2: Strimzi Operator

> **Reviewed**: 2026-09-12. Strimzi 1.2.0, Kafka 4.3.1. Strimzi requires Kubernetes 1.30 or later; local schema validation used 1.36.2.
> **Validation**: Two Helm configurations, 67 Kubernetes/CRD objects and five credential-file cases through Kafka's native JAAS parser. No live EKS installation, TLS connection, broker ACL enforcement, EBS or NLB provisioning was performed.

## 1. Scope and Prerequisites

This is a new-installation example with three dedicated controllers and three brokers. It requires schedulable capacity in three AZs and an appropriate StorageClass. Upgrading an existing cluster is a separate operation.

Strimzi is a CNCF incubating project that reconciles Kafka resources through Kubernetes Operators. The current Cluster Operator manages StrimziPodSets, Pods, Services and PVCs. When enabled, the Entity Operator runs the Topic and User Operators to reconcile KafkaTopic and KafkaUser resources. Installing an Operator does not automatically complete every rebalancing, recovery or availability policy.

Prerequisites:

- Kubernetes 1.30 or later and a kubectl version supported for that cluster. “Any kubectl version above 1.28” is not sufficient for every newer cluster.
- Helm 3; rendering here used Helm 3.21.3.
- The volume provisioner and IAM setup appropriate to standard EBS CSI or EKS Auto Mode.
- Schedulable nodes/capacity across three AZs and access to required image registries.

Strimzi 1.0 and later only support `kafka.strimzi.io/v1`. Convert older beta resources and upgrade CRDs through the official procedure first. CRDs are cluster-scoped: a new namespace does not avoid conflicts with existing definitions. Helm's `crds/` directory behaves differently for initial installation and existing CRD upgrades. The following helm install command is not an upgrade procedure for an existing 0.45 cluster.

## 2. Install the Cluster Operator

These commands change a real cluster. Confirm context/namespace and use them for a new installation.

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

The default chart watches its own namespace. For additional namespaces, create them first and set values such as `watchNamespaces: [kafka-staging]`. Chart 1.2 adds/deduplicates the release namespace and renders corresponding RoleBindings. Changing only the watch environment variable with kubectl set env can leave missing RBAC and Helm drift.

Do not overlap Helm, OLM and manual ownership of the same installation. `watchAnyNamespace: true` is an explicit cluster-wide choice, disabled in this example.

## 3. Storage and Placement

### Standard EBS CSI

This StorageClass uses the standard EBS CSI provisioner. Check existing resources with the same name before applying it. Changing a provisioner does not automatically migrate existing volumes to another driver.

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

gp3 baseline performance is 3,000 IOPS and 125 MiB/s. The previous `throughput: "250"` example provisioned additional throughput; it was not the baseline. Instance EBS/network limits, partition replication and read patterns also matter. JBOD does not automatically balance data or remove instance-level limits.

### EKS Auto Mode alternative

Choose this separate StorageClass only for Auto Mode and set **new NodePool volume classes** to `gp3-kafka-auto`. Use the provisioner path appropriate to the cluster. Existing PVC migration requires a separate procedure.

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

### Controller and broker pools

These files reference standard `gp3-kafka`. Actual roles are `controller` and `broker`; both may be listed together, but `dual-role` is not a separate enum value.

Both pools require three AZs. Selectors match the actual custom Pod label `docs.example.com/kafka-role` plus the cluster label, with `minDomains: 3`. Pods can remain Pending when only two AZs have eligible nodes. The strict constraint can also prevent replacement Pods in the remaining AZs during an outage.

Separate pools isolate Pod roles/resource settings, not necessarily physical worker nodes. Use node affinity if physical separation is required. Kafka rack awareness and Pod scheduling operate at different layers.

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

`kraftMetadata: shared` selects the volume used for KRaft metadata; at most one volume in a pool may have it. `deleteClaim: false` and StorageClass Retain are retention settings, not backups. PVCs/PVs/EBS volumes can remain and continue incurring costs after other resources are deleted.

Three controllers retain a majority of two after one voter failure. Three brokers meet a separate data-replication objective. Odd counts are not automatically safe; majority availability and connectivity still matter.

## 4. Authenticated Kafka Cluster

Enable an internal TLS/SCRAM listener and the ACL authorizer together. Creating KafkaUser while testing through an unauthenticated plaintext listener does not validate that user's authentication.

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

Strimzi 1.2 uses KRaft and node pools; do not add legacy activation annotations or ZooKeeper blocks. `rack.topologyKey` supplies AZ information for replica placement; it does not automatically reassign all existing partitions.

Keep Kafka version and metadataVersion compatible: this example uses 4.3.1 / 4.3-IV0. Do not change the version field while retaining an old image override. Node IDs are allocated across the cluster; do not assume every pool has a Pod ending in -0.

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

Ready=True is the Operator's observed reconciliation result. Compare observedGeneration with current generation and check Pod readiness, quorum and client connectivity. An old Ready condition or Running phase alone does not prove every component is healthy now.

## 5. Topic and User

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

For the smoke test, this user can produce/consume orders and read the order-processor group. Topic ACLs do not grant group ACLs. Cluster IdempotentWrite supports idempotent producer operations; it does not replace Write permission on other topics. Consider separate producer/consumer identities for real services.

The User Operator creates a Secret named after the user with password and sasl.jaas.config entries. The cluster authorizer and listener authentication must also be enabled. KafkaConnect/KafkaConnector define separate workers/connectors; Part 5 covers those configurations.

```bash
kubectl apply -f orders-topic.yaml -f order-service-user.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
kubectl -n kafka wait kafkauser/order-service --for=condition=Ready --timeout=5m
```

## 6. Test TLS/SCRAM Connectivity

This file includes a temporary client Pod and configuration-generation code. Credentials are read from a Secret volume, escaped for Java properties and written to a file, without placing passwords in command arguments, environment variables or logs. The Python init container and Kafka container use the same UID.

The client trusts the public CA through a PEM truststore and retains hostname verification. The Kafka image is pinned to the 4.3.1 release digest. No runtime package installation or assumption that Python exists in the Kafka image is needed.

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

This is a connectivity smoke test for a new lab topic. An existing topic can contain older records, so inspect the output rather than assuming the first record is the one just sent. Real validation should also cover unauthorized topic/group rejection, authentication failures, CA rotation, broker endpoint access and recovery. Local validation for this chapter sent no Kafka messages.

## 7. Optional: VPC Clients Outside Kubernetes

This merge patch creates internal NLBs through **AWS Load Balancer Controller**. It includes the existing TLS listener because JSON merge patch replaces the entire listeners array. Replace 10.0.0.0/16 with the actual approved client CIDRs before using it.

configuration.class becomes the generated Service loadBalancerClass. Matching internal/IP-target annotations apply to bootstrap and every broker Service without assuming broker IDs 0/1/2. Auto Mode load balancing requires separate confirmation of controller class and supported options.

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

This option creates bootstrap and per-broker LoadBalancer Services with corresponding costs. Clients must reach every broker endpoint returned in metadata, not just bootstrap. Adding DNS records or switching to NodePort does not automatically solve routing, TLS or node-lifecycle requirements.

## Next Steps and References

- [Kafka operations](./03-kafka-operations.md)
- [Kafka overview](./README.md)
- [Quiz](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
- [Strimzi 1.2.0 deployment](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Strimzi v1 API conversion](https://strimzi.io/docs/operators/1.0.0/deploying.html#assembly-api-conversion-str)
- [Strimzi 1.2.0 release](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.2.0)
- [EBS gp3 performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
