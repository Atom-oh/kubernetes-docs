# SQS 및 SNS 생성 예제 (ACK)

> **참고**: 이 문서는 [ACK 개념 문서](../02-ack.md)의 실습 예제입니다.

## SQS 대기열 생성

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

## SQS FIFO 대기열 생성

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

## SNS 주제 생성

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

## SNS 구독 생성

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

## SQS와 SNS 통합

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
