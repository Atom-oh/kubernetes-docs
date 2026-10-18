# SQS and SNS (ACK)

[ACK](../02-ack.md)

示例使用 SQS 1.8.2 / SNS 1.11.1 架构。队列使用 queueName 和字符串属性，标签采用映射形式。SNS 标签采用键/值列表；displayName、filterPolicy 和 rawMessageDelivery 是专用字段。

请同时修改账户、区域、队列/主题名称和策略 ARN。仅创建 SNS→SQS 订阅并不会授予投递权限。队列策略会将权限限制为确切的主题 ARN 和 SourceAccount。等待主题/队列就绪后再应用订阅，然后测试消息投递和重试。

电子邮件端点仅用于示例，需要收件人确认。本次审计未发送任何电子邮件或消息。filterPolicy 默认使用消息属性，因此发布者必须相应地提供 event_type。FIFO 基于内容的去重会使用消息正文，但无法避免所有业务层面的重复。

## 队列：queue-app-events

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

## 队列：queue-app-events-fifo

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

## 主题：topic-app-events

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

## 订阅：subscription-app-email

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

## 订阅：subscription-app-queue

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

## 验证和运行前提

已根据官方版本化 CRD 检查字段。架构验证成功并不能证明 IAM 权限、AWS 服务约束、资源创建、连通性或恢复能力。在应用配置之前，请明确保留资源的所有权、费用、清理和备份责任。

- [sqs v1.8.2 CRDs](https://github.com/aws-controllers-k8s/sqs-controller/tree/v1.8.2/config/crd/bases)
- [sns v1.11.1 CRDs](https://github.com/aws-controllers-k8s/sns-controller/tree/v1.11.1/config/crd/bases)
