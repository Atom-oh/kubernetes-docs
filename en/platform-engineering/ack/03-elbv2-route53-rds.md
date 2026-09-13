# ELBv2, Route 53 and Aurora (ACK)

[ACK](../02-ack.md)

These are separate schema examples for ELBv2 1.7.0 / Route 53 1.6.0 / RDS 1.12.0. They do not place NLB in front of Aurora. The internal NLB/DNS serves an application, while Aurora is a separate application dependency. An end-to-end connected deployment was not tested.

Prepare infra and authentication/permissions for all three controllers. Replace VPC, private subnets, security groups and hosted-zone IDs with approved values. NLB and database security groups should allow only required sources/ports. An internal NLB does not replace authorization or network controls.

Creating a TargetGroup does not register targets. ACK targets can manage fixed IPs; changing Kubernetes Pod IPs require an appropriate AWS Load Balancer Controller binding and ownership plan. Avoid two controllers competing for the same AWS object.

NLB and TargetGroup ARNs are at status.ackResourceMetadata.arn. Listener uses supported references. Route 53 uses recordType, not type. Populate alias DNS and canonicalHostedZoneID from actual NLB status. The record's hosted zone and the NLB alias target's hosted-zone ID are different values.

Aurora PostgreSQL 17.10 was announced in August 2026. Verify the engine/class combination and upgrade path for the actual account/region with describe-db-engine-versions and describe-orderable-db-instance-options. The former 15.4 is not a new default. Prepare database subnets across at least two supported AZs and verify placement/availability.

manageMasterUserPassword=true requests RDS Secrets Manager integration without a plaintext password example. Prepare required KMS/Secrets Manager permissions, costs and approved file delivery to applications. deletionProtection and retain protect different lifecycle layers.

DBInstance names or Role tags do not fix writer/reader roles. Inspect actual cluster membership; failover can change the writer. promotionTier is promotion priority, not permanent role assignment. A custom READER endpoint only uses the selected instances that are currently readers. Check available members and reconnect behavior after failover. An AZ-looking endpoint name does not implement AZ filtering.

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

## Verification and Operational Prerequisites

Fields were checked against official versioned CRDs. Schema success does not establish IAM permissions, AWS service constraints, creation, connectivity or recovery. Assign ownership, costs, cleanup and backup responsibilities for retained resources before applying.

- [elbv2 v1.7.0 CRDs](https://github.com/aws-controllers-k8s/elbv2-controller/tree/v1.7.0/config/crd/bases)
- [route53 v1.6.0 CRDs](https://github.com/aws-controllers-k8s/route53-controller/tree/v1.6.0/config/crd/bases)
- [rds v1.12.0 CRDs](https://github.com/aws-controllers-k8s/rds-controller/tree/v1.12.0/config/crd/bases)
- [Aurora PostgreSQL minor versions](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-aurora-postgresql-18-4-17-10-16-14-15-18-14-23/)
- [Aurora custom endpoints](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.html)
