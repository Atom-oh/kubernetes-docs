# SQS y SNS (ACK)

[ACK](../02-ack.md)

Los ejemplos utilizan los esquemas de SQS 1.7.0 / SNS 1.10.1. Queue utiliza queueName y atributos de tipo cadena, con tags como un mapa. En SNS, tags es una lista de pares clave/valor; displayName, filterPolicy y rawMessageDelivery son campos específicos.

Cambie conjuntamente la cuenta, la región, los nombres de queue/topic y los ARN de las políticas. Una suscripción SNS→SQS no concede por sí sola permiso de entrega. La política de Queue restringe la entrega al ARN exacto del topic y a SourceAccount. Aplique las suscripciones cuando el topic y la queue estén listos y, después, pruebe la entrega y los reintentos.

El endpoint de correo electrónico es ilustrativo y requiere la confirmación del destinatario. Esta auditoría no envió correos ni mensajes. filterPolicy utiliza los atributos del mensaje de forma predeterminada, por lo que los publicadores deben proporcionar event_type según corresponda. La deduplicación basada en contenido de FIFO utiliza el cuerpo del mensaje y no evita todos los duplicados a nivel de negocio.

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

## Verificación y requisitos operativos

Los campos se comprobaron con las CRD oficiales de las versiones indicadas. Que el esquema sea válido no demuestra que se cumplan los permisos de IAM ni las restricciones de los servicios de AWS, ni que funcionen la creación, la conectividad o la recuperación. Antes de aplicar los recursos, asigne las responsabilidades de propiedad, costes, limpieza y copias de seguridad de los recursos retenidos.

- [sqs v1.7.0 CRDs](https://github.com/aws-controllers-k8s/sqs-controller/tree/v1.7.0/config/crd/bases)
- [sns v1.10.1 CRDs](https://github.com/aws-controllers-k8s/sns-controller/tree/v1.10.1/config/crd/bases)
