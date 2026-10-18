# S3 and IAM (ACK)

[ACK](../02-ack.md)

Los ejemplos usan los CRD de S3 1.13.1 / IAM 1.10.1. Primero prepare la infraestructura, los controladores y las cuentas de servicio (ServiceAccounts) y los permisos de IAM. Reemplace el nombre del bucket, la cuenta, la región y los ARN por valores aprobados. Sincronice la política y el rol de IAM antes de aplicar la política del bucket que hace referencia a ese Role; S3 puede rechazar principales inexistentes.

Estas versiones no usan CRD independientes de BucketPolicy ni RolePolicyAttachment. Use Bucket.spec.policy y Role.spec.policyRefs. Están habilitados los cuatro ajustes de S3 Block Public Access y AES256 se especifica explícitamente. Haga coincidir los ARN de objetos y buckets con las acciones de la política.

Este rol confía en EC2. No es un rol de IRSA ni de Pod Identity; el uso de EC2 también requiere asociar un InstanceProfile. Su política de lectura de datos no es una política completa para el controlador de ACK.

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

Los campos se comprobaron con los CRD oficiales versionados. La validación del esquema no demuestra que los permisos de IAM sean suficientes, que se cumplan las restricciones del servicio de AWS, ni que se hayan completado la creación, la conectividad o la recuperación. Antes de aplicar, asigne responsables y confirme las responsabilidades de propiedad, costos, limpieza y copias de seguridad de los recursos retenidos.

- [CRD de s3 v1.13.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.13.1/config/crd/bases)
- [CRD de iam v1.10.1](https://github.com/aws-controllers-k8s/iam-controller/tree/v1.10.1/config/crd/bases)
