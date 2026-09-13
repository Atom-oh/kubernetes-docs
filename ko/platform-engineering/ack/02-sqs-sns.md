# SQS 및 SNS (ACK)

[ACK](../02-ack.md)

SQS 1.7.0 / SNS 1.10.1의 schema 예제입니다. Queue는 queueName과 문자열 attribute를 사용하고 tags는 map입니다. SNS tags는 key/value 목록이며 displayName, filterPolicy, rawMessageDelivery는 전용 필드입니다.

계정·region·queue/topic 이름과 policy ARN을 함께 변경하세요. SNS→SQS 구독만 생성해서는 전달 권한이 생기지 않습니다. Queue policy에서 정확한 topic ARN과 SourceAccount를 제한했습니다. topic과 queue가 준비된 후 구독을 적용하고 실제 전달·재시도를 검증합니다.

email endpoint는 예시 주소입니다. 실제 수신자의 확인이 필요하며 이 검토에서 이메일이나 메시지를 보내지 않았습니다. filterPolicy의 기본 대상은 message attributes이므로 발행자도 event_type을 맞춰야 합니다. content-based deduplication은 FIFO message body를 기준으로 하며 업무 중복 처리를 모두 방지하는 기능이 아닙니다.

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

## 검증과 운영 전 확인

표시한 필드는 공식 versioned CRD로 검사했습니다. 스키마 통과는 IAM, AWS 서비스 제약, 실제 생성·연결·복구를 증명하지 않습니다. retain으로 남긴 리소스의 운영·비용·삭제 책임과 백업 계획을 정한 뒤 적용하세요.

- [sqs v1.7.0 CRDs](https://github.com/aws-controllers-k8s/sqs-controller/tree/v1.7.0/config/crd/bases)
- [sns v1.10.1 CRDs](https://github.com/aws-controllers-k8s/sns-controller/tree/v1.10.1/config/crd/bases)
