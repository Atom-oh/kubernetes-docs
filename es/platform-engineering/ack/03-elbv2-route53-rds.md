# ELBv2, Route 53 y Aurora (ACK)

[ACK](../02-ack.md)

Estos son ejemplos de esquemas independientes para ELBv2 1.7.0 / Route 53 1.6.0 / RDS 1.12.0. No colocan NLB delante de Aurora. El NLB/DNS interno sirve a una aplicación, mientras que Aurora es una dependencia de aplicación independiente. No se probó un despliegue conectado de extremo a extremo.

Prepare la infraestructura y la autenticación/permisos para los tres controllers. Sustituya VPC, subnets privadas, security groups e IDs de hosted zone por valores aprobados. Los security groups de NLB y de la base de datos deben permitir únicamente los orígenes/puertos necesarios. Un NLB interno no reemplaza la autorización ni los controles de red.

La creación de un TargetGroup no registra targets. Los targets de ACK pueden gestionar IPs fijas; los cambios en las IP de los Pod de Kubernetes requieren una vinculación y un plan de propiedad adecuados de AWS Load Balancer Controller. Evite que dos controllers compitan por el mismo objeto de AWS.

Los ARN de NLB y TargetGroup se encuentran en status.ackResourceMetadata.arn. Listener usa referencias compatibles. Route 53 usa recordType, no type. Complete el DNS de alias y canonicalHostedZoneID a partir del estado real de NLB. La hosted zone del registro y el ID de hosted zone del alias target de NLB son valores diferentes.

Aurora PostgreSQL 17.10 se anunció en agosto de 2026. Verifique la combinación de engine/class y la ruta de actualización para la cuenta/región real con describe-db-engine-versions y describe-orderable-db-instance-options. La anterior 15.4 no es un nuevo valor predeterminado. Prepare subnets de base de datos en al menos dos AZ compatibles y verifique la ubicación/disponibilidad.

manageMasterUserPassword=true solicita la integración de RDS Secrets Manager sin un ejemplo de contraseña en texto sin formato. Prepare los permisos necesarios de KMS/Secrets Manager, los costos y la entrega aprobada de archivos a las aplicaciones. deletionProtection y retain protegen capas diferentes del ciclo de vida.

Los nombres de DBInstance o las etiquetas Role no determinan los roles de writer/reader. Inspeccione la pertenencia real al Cluster; el failover puede cambiar el writer. promotionTier es la prioridad de promoción, no una asignación de rol permanente. Un endpoint READER personalizado solo usa las instancias seleccionadas que actualmente son readers. Compruebe los miembros disponibles y el comportamiento de reconexión después de un failover. Un nombre de endpoint que parece una AZ no implementa el filtrado por AZ.

## LoadBalancer — loadbalancer-app-nlb

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: LoadBalancer
metadata:
  name: app-nlb
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: app-nlb
  scheme: internal
  type: network
  subnets:
  - subnet-0123456789abcdef0
  - subnet-0123456789abcdef1
  securityGroups:
  - sg-0123456789abcdef0
```

## TargetGroup — targetgroup-app-tg

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: TargetGroup
metadata:
  name: app-tg
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: app-tg
  protocol: TCP
  port: 8080
  targetType: ip
  vpcID: vpc-0123456789abcdef0
  healthCheckProtocol: TCP
  healthCheckPort: '8080'
```

## Listener — listener-app-listener

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: Listener
metadata:
  name: app-listener
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  loadBalancerRef:
    from:
      name: app-nlb
  port: 8080
  protocol: TCP
  defaultActions:
  - type: forward
    targetGroupRef:
      from:
        name: app-tg
```

## RecordSet — recordset-app-dns

```yaml
apiVersion: route53.services.k8s.aws/v1alpha1
kind: RecordSet
metadata:
  name: app-dns
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  hostedZoneID: REPLACE_WITH_PRIVATE_ZONE_ID
  name: app.example.com
  recordType: A
  aliasTarget:
    dnsName: REPLACE_WITH_NLB_STATUS_DNS_NAME
    hostedZoneID: REPLACE_WITH_NLB_CANONICAL_HOSTED_ZONE_ID
    evaluateTargetHealth: true
```

## DBSubnetGroup — dbsubnetgroup-app-db-subnets

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBSubnetGroup
metadata:
  name: app-db-subnets
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: app-db-subnets
  description: Private subnets in distinct supported AZs
  subnetIDs:
  - subnet-0123456789abcdef0
  - subnet-0123456789abcdef1
```

## DBCluster — dbcluster-app-aurora

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBCluster
metadata:
  name: app-aurora
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbClusterIdentifier: app-aurora
  engine: aurora-postgresql
  engineVersion: '17.10'
  masterUsername: dbadmin
  manageMasterUserPassword: true
  dbSubnetGroupRef:
    from:
      name: app-db-subnets
  vpcSecurityGroupIDs:
  - sg-0123456789abcdef1
  storageEncrypted: true
  backupRetentionPeriod: 7
  deletionProtection: true
```

## DBInstance — dbinstance-app-db-1

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: app-db-1
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbInstanceIdentifier: app-db-1
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  dbInstanceClass: db.r6g.large
  engine: aurora-postgresql
  publiclyAccessible: false
  promotionTier: 0
```

## DBInstance — dbinstance-app-db-2

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: app-db-2
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbInstanceIdentifier: app-db-2
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  dbInstanceClass: db.r6g.large
  engine: aurora-postgresql
  publiclyAccessible: false
  promotionTier: 1
```

## DBInstance — dbinstance-app-db-3

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: app-db-3
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbInstanceIdentifier: app-db-3
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  dbInstanceClass: db.r6g.large
  engine: aurora-postgresql
  publiclyAccessible: false
  promotionTier: 2
```

## DBClusterEndpoint — dbclusterendpoint-app-selected-readers

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBClusterEndpoint
metadata:
  name: app-selected-readers
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  dbClusterEndpointIdentifier: app-selected-readers
  dbClusterIdentifierRef:
    from:
      name: app-aurora
  endpointType: READER
  staticMemberRefs:
  - from:
      name: app-db-2
  - from:
      name: app-db-3
```

## Verificación y requisitos operativos

Los campos se comprobaron con los CRD oficiales versionados. El éxito del esquema no establece permisos de IAM, restricciones de servicios de AWS, creación, conectividad ni recuperación. Asigne las responsabilidades de propiedad, costos, limpieza y respaldo de los recursos retenidos antes de aplicar.

- [elbv2 v1.7.0 CRDs](https://github.com/aws-controllers-k8s/elbv2-controller/tree/v1.7.0/config/crd/bases)
- [route53 v1.6.0 CRDs](https://github.com/aws-controllers-k8s/route53-controller/tree/v1.6.0/config/crd/bases)
- [rds v1.12.0 CRDs](https://github.com/aws-controllers-k8s/rds-controller/tree/v1.12.0/config/crd/bases)
- [Aurora PostgreSQL minor versions](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-aurora-postgresql-18-4-17-10-16-14-15-18-14-23/)
- [Aurora custom endpoints](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.html)
