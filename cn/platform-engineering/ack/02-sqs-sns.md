# SQS 和 SNS (ACK)

[ACK](../02-ack.md)

示例使用 SQS 1.7.0 / SNS 1.10.1 schemas。Queue 使用 queueName 和字符串属性，tags 为 map。SNS tags 是键/值列表；displayName、filterPolicy 和 rawMessageDelivery 是专用字段。

请同时修改 account、region、queue/topic 名称和 policy ARN。仅创建 SNS→SQS subscription 并不会授予投递权限。Queue policy 限制了准确的 topic ARN 和 SourceAccount。在 topic/queue 就绪后应用 subscriptions，然后测试投递和重试。

email endpoint 仅用于说明，且需要收件人确认。本次审计未发送 email 或消息。filterPolicy 默认基于 message attributes，因此发布者必须相应提供 event_type。FIFO 基于内容的去重使用 message body，无法避免所有业务层面的重复。

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

## 验证和运维前提条件

已根据官方的版本化 CRDs 检查字段。Schema 验证成功并不代表 IAM 权限、AWS 服务限制、创建、连接性或恢复已就绪。在应用前，为保留资源分配所有权、成本、清理和备份职责。

- [sqs v1.7.0 CRDs](https://github.com/aws-controllers-k8s/sqs-controller/tree/v1.7.0/config/crd/bases)
- [sns v1.10.1 CRDs](https://github.com/aws-controllers-k8s/sns-controller/tree/v1.10.1/config/crd/bases)
