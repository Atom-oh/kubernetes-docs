# S3 and IAM (ACK)

[ACK](../02-ack.md)

Los ejemplos usan los CRD de S3 1.12.1 / IAM 1.9.0. Primero prepare la infraestructura, los controllers, los ServiceAccounts y los permisos de IAM. Reemplace el nombre del bucket, la cuenta, la región y los ARN por valores aprobados. Sincronice la Policy y el Role de IAM antes de aplicar la policy del bucket que hace referencia a ese Role; S3 puede rechazar principals inexistentes.

Estas versiones no usan CRD de BucketPolicy o RolePolicyAttachment independientes. Use Bucket.spec.policy y Role.spec.policyRefs. Las cuatro configuraciones de S3 Block Public Access están habilitadas y AES256 se especifica explícitamente. Haga coincidir los ARN de objetos/bucket con las acciones de la policy.

Este Role confía en EC2. No es un role de IRSA/Pod Identity; el uso de EC2 también requiere una asociación de InstanceProfile. Su policy de lectura de datos no es una policy completa para el controller de ACK.

## Bucket — bucket-app-data

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: replace-with-globally-unique-bucket-name
  createBucketConfiguration:
    locationConstraint: us-west-2
  publicAccessBlock:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  encryption:
    rules:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  tagging:
    tagSet:
    - key: Environment
      value: Development
  policy: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"\
    Effect\": \"Allow\",\n      \"Principal\": {\n        \"AWS\": \"arn:aws:iam::123456789012:role/MyApplicationRole\"\
    \n      },\n      \"Action\": \"s3:GetObject\",\n      \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

## Policy — policy-app-data-read

```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Policy
metadata:
  name: app-data-read
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: AppDataRead
  policyDocument: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n\
    \      \"Effect\": \"Allow\",\n      \"Action\": \"s3:ListBucket\",\n      \"\
    Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name\"\n    },\n\
    \    {\n      \"Effect\": \"Allow\",\n      \"Action\": \"s3:GetObject\",\n  \
    \    \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

## Role — role-app-role

```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Role
metadata:
  name: app-role
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: MyApplicationRole
  assumeRolePolicyDocument: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n\
    \    {\n      \"Effect\": \"Allow\",\n      \"Principal\": {\n        \"Service\"\
    : \"ec2.amazonaws.com\"\n      },\n      \"Action\": \"sts:AssumeRole\"\n    }\n\
    \  ]\n}"
  policyRefs:
  - from:
      name: app-data-read
  maxSessionDuration: 3600
```

## Verificación y requisitos operativos

Los campos se comprobaron con los CRD oficiales versionados. El éxito del schema no establece los permisos de IAM, las restricciones del servicio de AWS, la creación, la conectividad ni la recuperación. Asigne responsabilidades de propiedad, costes, limpieza y backups para los recursos retenidos antes de aplicar.

- [CRD de s3 v1.12.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/config/crd/bases)
- [CRD de iam v1.9.0](https://github.com/aws-controllers-k8s/iam-controller/tree/v1.9.0/config/crd/bases)
