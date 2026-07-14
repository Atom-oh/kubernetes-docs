# Ejemplos de creación de SQS y SNS (ACK)

> **Nota**: Este documento contiene ejemplos prácticos del [documento de conceptos de ACK](../02-ack.md).

## Ejemplos de creación de SQS y SNS

### Creación de una cola SQS

```yaml
apiVersion: sqs.services.k8s.aws/v1alpha1
kind: Queue
metadata:
  name: my-standard-queue
spec:
  name: my-standard-queue
  queueAttributes:
    - key: DelaySeconds
      value: "0"
    - key: MaximumMessageSize
      value: "262144"
    - key: MessageRetentionPeriod
      value: "345600"
    - key: VisibilityTimeout
      value: "30"
  tags:
    - key: Environment
      value: Development
```

### Creación de una cola FIFO de SQS

```yaml
apiVersion: sqs.services.k8s.aws/v1alpha1
kind: Queue
metadata:
  name: my-fifo-queue
spec:
  name: my-fifo-queue.fifo
  queueAttributes:
    - key: FifoQueue
      value: "true"
    - key: ContentBasedDeduplication
      value: "true"
  tags:
    - key: Environment
      value: Development
```

### Creación de un tema SNS

```yaml
apiVersion: sns.services.k8s.aws/v1alpha1
kind: Topic
metadata:
  name: my-notification-topic
spec:
  name: my-notification-topic
  attributes:
    - key: DisplayName
      value: "My Notification Topic"
  tags:
    - key: Environment
      value: Development
```

### Creación de una suscripción SNS

```yaml
apiVersion: sns.services.k8s.aws/v1alpha1
kind: Subscription
metadata:
  name: my-email-subscription
spec:
  topicARN: arn:aws:sns:us-west-2:123456789012:my-notification-topic
  protocol: email
  endpoint: user@example.com
  attributes:
    - key: FilterPolicy
      value: |
        {
          "event_type": ["order_placed", "order_shipped"]
        }
```

### Integración de SQS y SNS

```yaml
apiVersion: sns.services.k8s.aws/v1alpha1
kind: Subscription
metadata:
  name: my-sqs-subscription
spec:
  topicARN: arn:aws:sns:us-west-2:123456789012:my-notification-topic
  protocol: sqs
  endpoint: arn:aws:sqs:us-west-2:123456789012:my-standard-queue
  attributes:
    - key: RawMessageDelivery
      value: "true"
```
