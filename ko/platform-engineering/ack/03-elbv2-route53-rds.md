# ELBv2, Route 53 및 Aurora (ACK)

[ACK](../02-ack.md)

ELBv2 1.7.0 / Route 53 1.6.0 / RDS 1.12.0의 독립된 schema 예제입니다. NLB가 Aurora 앞단에 놓인다는 뜻은 아닙니다. app용 내부 NLB/DNS와 app이 연결할 Aurora를 별도로 준비하는 구성입니다. 전체 서비스가 연결된 실습으로 검증하지 않았습니다.

infra namespace와 세 controller의 인증·권한을 준비하고 승인된 VPC, private subnet, security group, hosted zone으로 치환하세요. NLB용과 DB용 security group은 필요한 source/port만 허용해야 합니다. 내부 NLB라고 IAM/RBAC 또는 네트워크 접근 제어가 대체되지는 않습니다.

TargetGroup만 생성하면 target이 등록되지 않습니다. 고정 IP target은 ACK targets로 관리할 수 있지만 Kubernetes Pod의 변동 IP 연결에는 AWS Load Balancer Controller의 적절한 binding/소유권 계획이 필요합니다. 같은 AWS 객체를 두 controller가 경쟁 관리하지 않게 하세요.

NLB와 TargetGroup ARN은 status.ackResourceMetadata.arn에서 읽습니다. Listener는 지원되는 Ref를 사용합니다. Route 53은 type이 아니라 recordType이며 NLB DNS와 canonicalHostedZoneID를 실제 status에서 복사해야 합니다. record가 속한 hosted zone과 alias 대상 NLB zone ID는 다른 값입니다.

Aurora PostgreSQL 17.10은 2026년 8월 발표 버전입니다. 실제 계정·region의 engine/class 조합과 upgrade 경로는 describe-db-engine-versions 및 describe-orderable-db-instance-options로 확인하세요. 예전 15.4를 새 기본값으로 사용하지 않습니다. DB subnet은 최소 두 개의 지원 AZ에 걸쳐 준비하고 실제 배치·가용성을 확인합니다.

manageMasterUserPassword=true로 RDS의 Secrets Manager 통합을 요청하며 별도의 plaintext password 예제를 만들지 않았습니다. 필요한 KMS/Secrets Manager 권한과 비용, app의 승인된 파일 전달 경로를 준비합니다. deletionProtection과 retain은 서로 다른 계층의 보존 설정입니다.

DBInstance 이름이나 Role tag가 writer/reader를 고정하지 않습니다. 실제 writer는 cluster membership 상태로 확인하며 failover로 바뀔 수 있습니다. promotionTier는 승격 우선순위이며 고정 역할 보장이 아닙니다. custom READER endpoint는 지정 인스턴스가 현재 reader인 경우에만 대상으로 사용하므로 failover 후 가용 대상과 연결 재시도를 확인합니다. AZ 이름처럼 보이는 endpoint 이름만으로 AZ 제한이 구현되지 않습니다.

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

## 검증과 운영 전 확인

표시한 필드는 공식 versioned CRD로 검사했습니다. 스키마 통과는 IAM, AWS 서비스 제약, 실제 생성·연결·복구를 증명하지 않습니다. retain으로 남긴 리소스의 운영·비용·삭제 책임과 백업 계획을 정한 뒤 적용하세요.

- [elbv2 v1.7.0 CRDs](https://github.com/aws-controllers-k8s/elbv2-controller/tree/v1.7.0/config/crd/bases)
- [route53 v1.6.0 CRDs](https://github.com/aws-controllers-k8s/route53-controller/tree/v1.6.0/config/crd/bases)
- [rds v1.12.0 CRDs](https://github.com/aws-controllers-k8s/rds-controller/tree/v1.12.0/config/crd/bases)
- [Aurora PostgreSQL minor versions](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-aurora-postgresql-18-4-17-10-16-14-15-18-14-23/)
- [Aurora custom endpoints](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.html)
