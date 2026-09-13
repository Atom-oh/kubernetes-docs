# SQS and SNS (ACK)

[ACK](../02-ack.md)

例では SQS 1.7.0 / SNS 1.10.1 のスキーマを使用します。Queue では queueName と文字列属性を使用し、tags はマップとして指定します。SNS の tags はキー/値のリストであり、displayName、filterPolicy、rawMessageDelivery は専用フィールドです。

account、region、queue/topic 名、および policy ARN はまとめて変更してください。SNS→SQS Subscription だけでは配信権限は付与されません。Queue policy は厳密な topic ARN と SourceAccount に制限します。topic/queue の準備完了後に Subscription を適用し、その後、配信とリトライをテストしてください。

email endpoint は説明用であり、受信者による確認が必要です。この監査では email やメッセージは送信していません。filterPolicy はデフォルトで message attributes を対象とするため、publisher は event_type を適切に指定する必要があります。FIFO の content-based deduplication は message body を使用し、ビジネスレベルのすべての重複を防ぐものではありません。

## Queue — queue-app-events

```yaml
apiVersion: sqs.services.k8s.aws/v1alpha1
kind: Queue
metadata:
  name: app-events
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  queueName: app-events
  delaySeconds: '0'
  maximumMessageSize: '262144'
  messageRetentionPeriod: '345600'
  visibilityTimeout: '30'
  sqsManagedSSEEnabled: 'true'
  tags:
    Environment: Development
  policy: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"\
    Effect\": \"Allow\",\n      \"Principal\": {\n        \"Service\": \"sns.amazonaws.com\"\
    \n      },\n      \"Action\": \"sqs:SendMessage\",\n      \"Resource\": \"arn:aws:sqs:us-west-2:123456789012:app-events\"\
    ,\n      \"Condition\": {\n        \"ArnEquals\": {\n          \"aws:SourceArn\"\
    : \"arn:aws:sns:us-west-2:123456789012:app-events\"\n        },\n        \"StringEquals\"\
    : {\n          \"aws:SourceAccount\": \"123456789012\"\n        }\n      }\n \
    \   }\n  ]\n}"
```

## Queue — queue-app-events-fifo

```yaml
apiVersion: sqs.services.k8s.aws/v1alpha1
kind: Queue
metadata:
  name: app-events-fifo
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  queueName: app-events.fifo
  fifoQueue: 'true'
  contentBasedDeduplication: 'true'
  sqsManagedSSEEnabled: 'true'
  tags:
    Environment: Development
```

## Topic — topic-app-events

```yaml
apiVersion: sns.services.k8s.aws/v1alpha1
kind: Topic
metadata:
  name: app-events
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: app-events
  displayName: Application events
  tags:
  - key: Environment
    value: Development
```

## Subscription — subscription-app-email

```yaml
apiVersion: sns.services.k8s.aws/v1alpha1
kind: Subscription
metadata:
  name: app-email
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  topicRef:
    from:
      name: app-events
  protocol: email
  endpoint: user@example.com
  filterPolicy: '{"event_type":["order_placed","order_shipped"]}'
```

## Subscription — subscription-app-queue

```yaml
apiVersion: sns.services.k8s.aws/v1alpha1
kind: Subscription
metadata:
  name: app-queue
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  topicRef:
    from:
      name: app-events
  protocol: sqs
  endpoint: arn:aws:sqs:us-west-2:123456789012:app-events
  rawMessageDelivery: 'true'
```

## 検証と運用上の前提条件 {#verification-and-operational-prerequisites}

フィールドは公式のバージョン指定 CRD と照合済みです。スキーマの成功は、IAM 権限、AWS サービスの制約、作成、接続性、または復旧を保証するものではありません。適用前に、保持されるリソースの所有権、コスト、クリーンアップ、およびバックアップの責任を割り当ててください。

- [sqs v1.7.0 CRDs](https://github.com/aws-controllers-k8s/sqs-controller/tree/v1.7.0/config/crd/bases)
- [sns v1.10.1 CRDs](https://github.com/aws-controllers-k8s/sns-controller/tree/v1.10.1/config/crd/bases)
