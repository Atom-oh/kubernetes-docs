# ELBv2, Route 53 y Aurora (ACK)

[ACK](../02-ack.md)

Estos son ejemplos de esquemas independientes para ELBv2 1.8.2 / Route 53 1.7.1 / RDS 1.13.3. No colocan NLB delante de Aurora. El NLB/DNS interno sirve a una aplicación, mientras que Aurora es una dependencia de aplicación independiente. No se probó un despliegue conectado de extremo a extremo.

Prepare la infraestructura y configure la autenticación y los permisos necesarios para los tres controladores. Sustituya la VPC, las subredes privadas, los grupos de seguridad y los ID de las zonas alojadas por valores aprobados. Los grupos de seguridad del NLB y de la base de datos deben permitir solo los orígenes y puertos necesarios. Un NLB interno no sustituye la autorización ni los controles de red.

La creación de un TargetGroup no registra destinos. ACK puede administrar destinos con direcciones IP fijas; los cambios en las IP de los Pods de Kubernetes requieren una vinculación adecuada mediante AWS Load Balancer Controller y un plan de titularidad del recurso. Evite que dos controladores compitan por el mismo objeto de AWS.

Los ARN del NLB y del TargetGroup están disponibles en status.ackResourceMetadata.arn. El Listener usa referencias compatibles. Route 53 usa recordType, no type. Complete el DNS del alias y canonicalHostedZoneID con datos del estado real del NLB. La zona alojada del registro y el ID de zona alojada del destino de alias del NLB son valores distintos.

Aurora PostgreSQL 17.10 se anunció en agosto de 2026. Verifique la combinación de motor y clase de instancia, así como la ruta de actualización, para la cuenta y región reales mediante describe-db-engine-versions y describe-orderable-db-instance-options. La versión anterior, 15.4, no es un nuevo valor predeterminado. Configure un grupo de subredes de base de datos distribuido entre al menos dos AZ compatibles y verifique la ubicación y la disponibilidad.

manageMasterUserPassword=true solicita la integración de RDS con Secrets Manager sin incluir un ejemplo de contraseña en texto sin formato. Prepare los permisos necesarios de KMS/Secrets Manager, contemple los costos y use un mecanismo aprobado para entregar archivos a las aplicaciones. deletionProtection y retain protegen capas distintas del ciclo de vida.

Los nombres de DBInstance o las etiquetas Role no determinan quién es writer o reader. Inspeccione la pertenencia real al clúster; un failover puede cambiar el writer. promotionTier indica la prioridad de promoción, no asigna un rol de forma permanente. Un endpoint READER personalizado solo usa las instancias seleccionadas que sean readers en ese momento. Compruebe qué miembros están disponibles y cómo se reconectan las aplicaciones tras un failover. Un nombre de endpoint que parece indicar una AZ no aplica un filtro por AZ.

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

Los campos se comprobaron con los CRD oficiales de las versiones indicadas. Que el esquema sea válido no demuestra que haya permisos de IAM ni que se cumplan las restricciones del servicio de AWS, ni que los recursos se creen, haya conectividad o sea posible recuperarse. Antes de aplicar los manifiestos, asigne las responsabilidades de los recursos retenidos, sus costos, limpieza y copias de seguridad.

- [CRD de elbv2 v1.8.2](https://github.com/aws-controllers-k8s/elbv2-controller/tree/v1.8.2/config/crd/bases)
- [CRD de route53 v1.7.1](https://github.com/aws-controllers-k8s/route53-controller/tree/v1.7.1/config/crd/bases)
- [CRD de rds v1.13.3](https://github.com/aws-controllers-k8s/rds-controller/tree/v1.13.3/config/crd/bases)
- [Versiones menores de Aurora PostgreSQL](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-aurora-postgresql-18-4-17-10-16-14-15-18-14-23/)
- [Endpoints personalizados de Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.html)
