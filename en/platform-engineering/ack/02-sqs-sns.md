# SQS and SNS Creation Examples (ACK)

> **Note**: This document contains hands-on examples from the [ACK Concepts document](../02-ack.md).

## SQS and SNS Creation Examples

### Creating SQS Queue

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

### Creating SQS FIFO Queue

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

### Creating SNS Topic

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

### Creating SNS Subscription

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

### Integrating SQS and SNS

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
