# SQS and SNS (ACK)

[ACK](../02-ack.md)

Examples use SQS 1.7.0 / SNS 1.10.1 schemas. Queue uses queueName and string attributes, with tags as a map. SNS tags are key/value lists; displayName, filterPolicy and rawMessageDelivery are dedicated fields.

Change account, region, queue/topic names and policy ARNs together. An SNS→SQS subscription alone does not grant delivery permission. The Queue policy restricts the exact topic ARN and SourceAccount. Apply subscriptions after topic/queue readiness, then test delivery and retries.

The email endpoint is illustrative and requires recipient confirmation. This audit sent no email or messages. filterPolicy defaults to message attributes, so publishers must supply event_type accordingly. FIFO content-based deduplication uses the message body and does not prevent every business-level duplicate.

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

## Verification and Operational Prerequisites

Fields were checked against official versioned CRDs. Schema success does not establish IAM permissions, AWS service constraints, creation, connectivity or recovery. Assign ownership, costs, cleanup and backup responsibilities for retained resources before applying.

- [sqs v1.7.0 CRDs](https://github.com/aws-controllers-k8s/sqs-controller/tree/v1.7.0/config/crd/bases)
- [sns v1.10.1 CRDs](https://github.com/aws-controllers-k8s/sns-controller/tree/v1.10.1/config/crd/bases)
