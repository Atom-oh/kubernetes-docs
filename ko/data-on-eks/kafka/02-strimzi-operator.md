# Part 2: Strimzi Operator

> **검토 기준**: 2026-09-12. Strimzi 1.2.0, Kafka 4.3.1. Strimzi의 최소 Kubernetes 버전은 1.30이며 로컬 스키마 검증은 1.36.2를 사용했습니다.
> **검증 범위**: Helm 두 구성, Kubernetes/CRD 객체 67개, Kafka의 실제 JAAS 파서를 사용한 인증 파일 5개 사례. 실제 EKS 설치·TLS 접속·ACL 집행·EBS/NLB 생성을 수행한 결과는 아닙니다.

## 1. 범위와 준비

이 장은 새 환경에서 controller 3개와 broker 3개를 분리해 배포하는 예제입니다. 세 AZ에 스케줄 가능한 용량과 올바른 StorageClass가 필요합니다. 기존 클러스터 업그레이드는 별도 작업입니다.

Strimzi는 CNCF incubating 프로젝트이며 Kubernetes Operator로 Kafka 리소스를 조정합니다. Cluster Operator는 현재 `StrimziPodSet`과 Pod·Service·PVC 등을 관리합니다. Topic Operator와 User Operator는 선택한 경우 Entity Operator에 배포되어 `KafkaTopic`과 `KafkaUser`를 조정합니다. Operator가 있다고 자동으로 모든 리밸런싱·복구·가용성 정책이 완성되지는 않습니다.

필요한 환경은 다음과 같습니다.

- Kubernetes 1.30 이상과 해당 클러스터에 지원되는 kubectl 버전. “kubectl 1.28 이상이면 모든 새 클러스터에 충분”한 것은 아닙니다.
- Helm 3. 이 예제는 Helm 3.21.3으로 렌더링했습니다.
- 표준 EBS CSI 경로 또는 EKS Auto Mode에 맞는 볼륨 프로비저너와 IAM 구성.
- 세 AZ의 스케줄 가능한 노드·용량, ECR/Quay/Docker Hub 등 필요한 이미지 저장소 접근.

Strimzi 1.0 이상은 `kafka.strimzi.io/v1`만 지원합니다. 이전 beta API 리소스는 공식 변환 절차와 CRD 업그레이드를 먼저 완료해야 합니다. CRD는 cluster-scoped이므로 namespace만 새로 만들어도 기존 CRD와의 충돌을 피할 수는 없습니다. Helm의 `crds/` 디렉터리는 새 설치와 기존 CRD 업그레이드의 동작이 다르므로, 아래 `helm install`을 기존 0.45 환경의 업그레이드 명령으로 사용하지 않습니다.

## 2. Cluster Operator 설치

다음 명령은 실제 클러스터를 변경합니다. 대상 context와 namespace를 확인하고 새 설치 환경에서 사용합니다.

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

기본 chart는 배포된 namespace를 감시합니다. 추가 namespace가 필요하면 먼저 namespace를 만들고 Helm values에 `watchNamespaces: [kafka-staging]`처럼 지정합니다. 1.2 chart는 이 목록에 release namespace를 추가·중복 제거하고 대응 RoleBinding도 렌더링합니다. `kubectl set env`로 감시 범위만 바꾸는 방식은 RBAC 누락과 Helm drift를 만들 수 있습니다.

다른 배포 도구가 관리하는 설치에 Helm·OLM·수동 YAML을 중복 적용하지 않습니다. `watchAnyNamespace: true`는 명시적인 cluster-wide 선택이며 이 예제에서는 사용하지 않습니다.

## 3. 스토리지와 배치

### 표준 EBS CSI 경로

다음 StorageClass는 표준 EBS CSI provisioner를 사용합니다. 기존 같은 이름의 StorageClass가 있다면 속성과 소유권을 먼저 확인합니다. provisioner 변경으로 기존 볼륨을 다른 드라이버로 자동 이관할 수 없습니다.

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

gp3의 기본 성능은 3,000 IOPS와 125 MiB/s입니다. 이전 예제의 `throughput: "250"`은 기본값이 아니라 추가로 프로비저닝한 처리량입니다. 성능에는 볼륨 설정 외에도 인스턴스의 EBS·네트워크 한계, 파티션/복제와 읽기 패턴이 영향을 줍니다. JBOD도 데이터를 자동으로 균등 분산하거나 인스턴스 한계를 제거하지 않습니다.

### EKS Auto Mode 대안

Auto Mode를 사용할 때만 다음 별도 StorageClass를 선택하고, **새 NodePool의 volume class**를 `gp3-kafka-auto`로 맞춥니다. 표준 CSI 예제와 둘 중 맞는 경로를 선택합니다. 이미 만들어진 PVC의 스토리지 이관은 별도로 설계해야 합니다.

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

### Controller와 broker 풀

다음 두 파일은 표준 `gp3-kafka`를 참조합니다. `roles`의 실제 값은 `controller`와 `broker`이며, 둘을 함께 넣을 수 있지만 `dual-role`이라는 별도 문자열 값은 아닙니다.

두 풀 모두 세 AZ를 요구합니다. 실제 Pod에 추가하는 `docs.example.com/kafka-role` label과 cluster label을 selector에 사용하고 `minDomains: 3`을 지정합니다. 노드가 두 AZ에만 있으면 이 요구를 충족하지 못해 Pod가 Pending이 될 수 있습니다. AZ 장애 후 엄격한 제약 때문에 대체 Pod가 다른 두 AZ에 배치되지 못할 수도 있습니다.

풀 분리는 Pod 역할·자원 설정의 분리이지 물리 노드 전용 배치 보장은 아닙니다. 필요하면 node affinity 등으로 실제 노드도 분리합니다. Kafka rack awareness와 Pod 스케줄링은 서로 다른 계층의 설정입니다.

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

`kraftMetadata: shared`는 해당 볼륨에 KRaft 메타데이터를 함께 저장한다는 의미이며, 한 풀에서 최대 한 볼륨에 지정합니다. `deleteClaim: false`와 StorageClass `Retain`은 보존 정책입니다. 백업·복구 검증을 대신하지 않으며 리소스를 삭제한 뒤에도 PVC/PV/EBS가 남아 비용이 계속될 수 있습니다.

controller 3개는 한 voter 손실에도 과반수 2개를 유지하기 위한 선택입니다. broker 3개는 별도 데이터 복제 요구입니다. 홀수라는 사실만으로 안전해지는 것은 아니며, voter의 과반수와 연결성이 필요합니다.

## 4. 인증된 Kafka 클러스터

단일 내부 TLS/SCRAM 리스너와 ACL authorizer를 함께 켭니다. KafkaUser만 만들고 평문/무인증 리스너로 접속하는 방식은 사용자 인증 검증이 아닙니다.

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

Strimzi 1.2는 KRaft와 node pool을 사용하므로 예전 KRaft/node-pools 활성화 annotation이나 ZooKeeper 블록을 추가하지 않습니다. `rack.topologyKey`는 새 replica 배치 시 AZ 정보를 제공하지만 기존 파티션 배치를 자동으로 모두 재배치하는 명령은 아닙니다.

버전과 metadataVersion은 호환되는 값을 사용합니다. 이 예제는 4.3.1 / 4.3-IV0이며, 과거 이미지 override를 남겨둔 채 버전 필드만 바꾸지 않습니다. node ID는 클러스터 전체에서 할당되므로 모든 풀에 `-0` Pod가 존재한다고 가정하지 않습니다.

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

`Ready=True`는 Operator가 관찰한 조정 결과입니다. `observedGeneration`과 현재 generation을 비교하고 Pod readiness·quorum·클라이언트 연결도 확인합니다. 오래된 Ready condition이나 Pod의 Running 표시만으로 모든 구성 요소가 지금 정상이라고 단정하지 않습니다.

## 5. 토픽과 사용자

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

이 사용자는 테스트를 위해 orders의 생산·소비와 `order-processor` 그룹 읽기를 함께 허용합니다. Topic 권한만으로 consumer group 권한이 생기지는 않습니다. `IdempotentWrite`는 idempotent producer 동작을 위한 cluster 작업이며 다른 토픽의 Write 권한을 대신하지 않습니다. 실제 서비스에서는 생산·소비 주체별 분리를 검토합니다.

User Operator는 사용자와 같은 이름의 Secret을 만들고 `password`, `sasl.jaas.config`를 제공합니다. Kafka 설정의 authorizer와 listener 인증이 함께 있어야 이 권한이 의미를 갖습니다. KafkaConnect/KafkaConnector는 별도 워커·커넥터 리소스이며 상세 구성은 Part 5에서 다룹니다.

```bash
kubectl apply -f orders-topic.yaml -f order-service-user.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
kubectl -n kafka wait kafkauser/order-service --for=condition=Ready --timeout=5m
```

## 6. TLS/SCRAM 연결 확인

다음 파일은 일시적인 테스트 Pod와 client 설정 생성 코드를 포함합니다. 자격 증명은 Secret volume에서 읽고 Java properties 형식으로 escape하여 파일에 저장합니다. 비밀번호를 명령줄·환경 변수·로그로 출력하지 않습니다. Python init container와 Kafka container는 같은 UID를 사용합니다.

클라이언트는 공개 CA 인증서를 PEM truststore로 사용하고 hostname 검증을 유지합니다. 이미지의 Kafka 버전은 4.3.1로 맞췄습니다. 별도 패키지를 설치하거나 Kafka 이미지에 Python이 있다고 가정하지 않습니다.

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

이 테스트는 새 실습 토픽의 연결 확인입니다. 기존 토픽에는 예전 레코드가 있을 수 있으므로 첫 레코드가 방금 보낸 값이라고 단정하지 말고 출력 내용을 확인합니다. 실제 검증에는 허용되지 않은 토픽/그룹 거부, 인증 실패, CA rotation, broker endpoint 접근과 장애 복구도 포함해야 합니다. 이 장의 로컬 검사는 실제 Kafka 메시지를 보내지 않았습니다.

## 7. 선택 사항: 클러스터 밖의 VPC 클라이언트

아래는 **AWS Load Balancer Controller 경로**에서 내부 NLB를 만드는 merge patch입니다. 원래 TLS listener를 포함하는 이유는 JSON merge patch가 listeners 배열 전체를 교체하기 때문입니다. 실제 승인된 client CIDR로 `10.0.0.0/16`을 교체한 뒤 사용합니다.

`configuration.class`는 생성된 Service의 loadBalancerClass가 됩니다. bootstrap과 각 broker Service에 같은 internal/IP target annotation을 적용하며, broker ID를 0·1·2로 가정하지 않습니다. Auto Mode의 LB 경로는 controller class와 지원 옵션을 별도로 확인해야 합니다.

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

이 선택은 bootstrap과 broker별 LoadBalancer Service를 생성하며 비용이 발생합니다. 클라이언트는 bootstrap뿐 아니라 metadata로 받은 모든 broker endpoint에도 도달해야 합니다. DNS만 추가하거나 NodePort로 바꾼다고 routing·TLS·노드 수명 주기 문제가 자동 해결되지는 않습니다.

## 다음 단계와 참고

- [Kafka operations](./03-kafka-operations.md)
- [Kafka overview](./README.md)
- [Quiz](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
- [Strimzi 1.2.0 deployment](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Strimzi v1 API conversion](https://strimzi.io/docs/operators/1.0.0/deploying.html#assembly-api-conversion-str)
- [Strimzi 1.2.0 release](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.2.0)
- [EBS gp3 performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
