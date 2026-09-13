# 第2部: Strimzi Operator

> **最終更新**: September 12, 2026。Strimzi 1.2.0、Kafka 4.3.1。StrimziにはKubernetes 1.30以降が必要です。ローカルでのスキーマ検証には1.36.2を使用しました。
> **検証**: 2つのHelm設定、67個のKubernetes/CRDオブジェクト、およびKafkaネイティブのJAASパーサーによる5つの認証情報ファイルのケースを検証しました。実際のEKSへのインストール、TLS接続、ブローカーでのACL適用、EBSまたはNLBのプロビジョニングは行っていません。

## 1. 対象範囲と前提条件

これは専用コントローラー3台とブローカー3台による新規インストールの例です。3つのAZにスケジュール可能な容量と、適切なStorageClassが必要です。既存クラスターのアップグレードは別の操作です。

Strimziは、Kubernetes Operatorを通じてKafkaリソースを調整するCNCFのインキュベーションプロジェクトです。現在のCluster OperatorはStrimziPodSet、Pod、Service、PVCを管理します。有効にすると、Entity OperatorがTopic OperatorとUser Operatorを実行し、KafkaTopicとKafkaUserリソースを調整します。Operatorをインストールしても、すべてのリバランス、復旧、可用性の方針が自動的に整うわけではありません。

前提条件:

- Kubernetes 1.30以降と、そのクラスターでサポートされるkubectlバージョン。「1.28より新しい任意のkubectlバージョン」では、すべての新しいクラスターに対して十分とは限りません。
- Helm 3。ここでのレンダリングにはHelm 3.21.3を使用しました。
- 標準のEBS CSIまたはEKS Auto Modeに適したボリュームプロビジョナーとIAM設定。
- 3つのAZにまたがるスケジュール可能なノード/容量と、必要なイメージレジストリへのアクセス。

Strimzi 1.0以降は`kafka.strimzi.io/v1`のみをサポートします。まず公式手順に従って古いベータリソースを変換し、CRDをアップグレードしてください。CRDはクラスターをスコープとするため、新しい名前空間を作成しても既存定義との競合は避けられません。Helmの`crds/`ディレクトリは、新規インストール時と既存CRDのアップグレード時で動作が異なります。次のhelm installコマンドは、既存の0.45クラスターをアップグレードする手順ではありません。

## 2. Cluster Operatorのインストール

これらのコマンドは実際のクラスターを変更します。コンテキスト/名前空間を確認し、新規インストールに使用してください。

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

デフォルトのチャートは自身の名前空間を監視します。追加の名前空間については、先に作成してから`watchNamespaces: [kafka-staging]`などの値を設定します。チャート1.2はリリースの名前空間を追加/重複排除し、対応するRoleBindingをレンダリングします。kubectl set envで監視用の環境変数だけを変更すると、RBACの不足やHelmとの差異が残る可能性があります。

同じインストールの所有権をHelm、OLM、手動管理で重複させないでください。`watchAnyNamespace: true`はクラスター全体を対象とする明示的な選択であり、この例では無効です。

## 3. ストレージと配置

### 標準のEBS CSI

このStorageClassは標準のEBS CSIプロビジョナーを使用します。適用する前に、同名の既存リソースを確認してください。プロビジョナーを変更しても、既存ボリュームは別のドライバーへ自動移行されません。

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

gp3のベースライン性能は3,000 IOPSと125 MiB/sです。以前の`throughput: "250"`の例は追加のスループットをプロビジョニングしており、ベースラインではありませんでした。インスタンスのEBS/ネットワーク制限、パーティションのレプリケーション、読み取りパターンも重要です。JBODはデータを自動的に均等配置したり、インスタンスレベルの制限を取り除いたりしません。

### EKS Auto Modeの代替設定

この別のStorageClassはAuto Modeでのみ選択し、**新しいNodePoolのボリュームクラス**を`gp3-kafka-auto`に設定してください。クラスターに適したプロビジョナーのパスを使用します。既存PVCの移行には別の手順が必要です。

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

### コントローラーとブローカーのプール

これらのファイルは標準の`gp3-kafka`を参照します。実際のロールは`controller`と`broker`です。両方を一緒に指定できますが、`dual-role`という独立した列挙値はありません。

両方のプールで3つのAZが必要です。セレクターは実際のカスタムPodラベル`docs.example.com/kafka-role`とクラスターラベルに一致し、`minDomains: 3`を設定しています。適格なノードが2つのAZにしかない場合、PodがPendingのままになることがあります。この厳格な制約は、障害時に残りのAZで代替Podを作成することも妨げる可能性があります。

プールを分離するとPodのロール/リソース設定を分離できますが、物理ワーカーノードまで分離されるとは限りません。物理的な分離が必要ならノードアフィニティを使用してください。Kafkaのラック認識とPodスケジューリングは異なるレイヤーで動作します。

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

`kraftMetadata: shared`はKRaftメタデータに使用するボリュームを選択します。1つのプールで指定できるボリュームは最大1つです。`deleteClaim: false`とStorageClassのRetainは保持設定であり、バックアップではありません。他のリソースを削除した後もPVC/PV/EBSボリュームが残り、料金が発生し続ける場合があります。

コントローラーが3台あれば、投票者1台の障害後も2台の過半数を維持できます。ブローカー3台は、これとは別のデータレプリケーション目標を満たします。奇数台なら自動的に安全になるわけではなく、過半数の可用性と接続性が依然として重要です。

## 4. 認証付きKafkaクラスター

内部TLS/SCRAMリスナーとACLオーソライザーを一緒に有効にします。KafkaUserを作成しても、認証なしの平文リスナーでテストしたのでは、そのユーザーの認証を検証したことにはなりません。

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

Strimzi 1.2はKRaftとノードプールを使用します。従来の有効化アノテーションやZooKeeperブロックは追加しないでください。`rack.topologyKey`はレプリカ配置用のAZ情報を提供しますが、既存の全パーティションを自動的に再割り当てするわけではありません。

KafkaのバージョンとmetadataVersionの互換性を保ってください。この例は4.3.1 / 4.3-IV0を使用します。古いイメージのオーバーライドを残したままversionフィールドを変更しないでください。ノードIDはクラスター全体で割り当てられます。すべてのプールに末尾が-0のPodがあるとは想定しないでください。

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

Ready=TrueはOperatorが観測した調整結果です。observedGenerationと現在のgenerationを比較し、Podの準備状態、クォーラム、クライアントの接続性を確認してください。古いReady条件やRunningフェーズだけでは、現在すべてのコンポーネントが正常であることは証明できません。

## 5. トピックとユーザー

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

スモークテストでは、このユーザーはordersへの書き込み/読み取りとorder-processorグループの読み取りができます。トピックACLはグループACLを付与しません。クラスターのIdempotentWriteは冪等なプロデューサー操作をサポートしますが、他のトピックのWrite権限を代替しません。実際のサービスでは、プロデューサーとコンシューマーに別々のIDを使用することを検討してください。

User Operatorは、ユーザーと同名のSecretを作成し、passwordとsasl.jaas.configのエントリを格納します。クラスターのオーソライザーとリスナー認証も有効にする必要があります。KafkaConnect/KafkaConnectorは別のワーカー/コネクターを定義します。これらの設定は第5部で扱います。

```bash
kubectl apply -f orders-topic.yaml -f order-service-user.yaml
kubectl -n kafka wait kafkatopic/orders --for=condition=Ready --timeout=5m
kubectl -n kafka wait kafkauser/order-service --for=condition=Ready --timeout=5m
```

## 6. TLS/SCRAM接続のテスト

このファイルには、一時的なクライアントPodと設定生成コードが含まれます。認証情報はSecretボリュームから読み取り、Java properties用にエスケープしてファイルへ書き込みます。パスワードをコマンド引数、環境変数、ログには配置しません。Python initコンテナとKafkaコンテナは同じUIDを使用します。

クライアントはPEMトラストストアを通じて公開CAを信頼し、ホスト名検証を維持します。Kafkaイメージは4.3.1リリースのダイジェストに固定されています。実行時のパッケージインストールや、KafkaイメージにPythonが存在するという想定は不要です。

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

これは新しい演習用トピックに対する接続性のスモークテストです。既存トピックには古いレコードが含まれる可能性があるため、最初のレコードが直前に送信したものだと決めつけず、出力を確認してください。実際の検証では、未許可のトピック/グループへのアクセス拒否、認証失敗、CAローテーション、ブローカーエンドポイントへのアクセス、復旧も扱う必要があります。この章のローカル検証ではKafkaメッセージを送信していません。

## 7. オプション: Kubernetes外のVPCクライアント

このマージパッチは、**AWS Load Balancer Controller**を通じて内部NLBを作成します。JSON merge patchはlisteners配列全体を置き換えるため、既存のTLSリスナーも含んでいます。使用前に10.0.0.0/16を、実際に承認されたクライアントCIDRに置き換えてください。

configuration.classは、生成されるServiceのloadBalancerClassになります。対応する内部/IPターゲットのアノテーションは、ブローカーIDを0/1/2と決めつけることなく、bootstrapと各ブローカーのServiceに適用されます。Auto Modeの負荷分散では、コントローラークラスとサポートされるオプションを別途確認する必要があります。

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

このオプションはbootstrap用とブローカーごとのLoadBalancer Serviceを作成し、対応する料金が発生します。クライアントはbootstrapだけでなく、メタデータで返されるすべてのブローカーエンドポイントに到達できる必要があります。DNSレコードの追加やNodePortへの切り替えだけで、ルーティング、TLS、ノードライフサイクルの要件が自動的に解決されるわけではありません。

## 次のステップと参考資料

- [Kafkaの運用](./03-kafka-operations.md)
- [Kafkaの概要](./README.md)
- [クイズ](../../quizzes/data-on-eks/kafka/02-strimzi-operator-quiz.md)
- [Strimzi 1.2.0のデプロイ](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Strimzi v1 APIへの変換](https://strimzi.io/docs/operators/1.0.0/deploying.html#assembly-api-conversion-str)
- [Strimzi 1.2.0のリリース](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.2.0)
- [EBS gp3の性能](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
