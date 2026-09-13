# ELBv2、Route 53 和 Aurora (ACK)

[ACK](../02-ack.md)

以下是 ELBv2 1.7.0 / Route 53 1.6.0 / RDS 1.12.0 的独立 schema 示例。它们不会将 NLB 部署在 Aurora 前方。内部 NLB/DNS 为应用程序提供服务，而 Aurora 是独立的应用程序依赖项。尚未测试端到端连接的部署。

为全部三个 controller 准备基础设施以及认证/权限。请将 VPC、私有子网、安全组和托管区域 ID 替换为已批准的值。NLB 和数据库安全组应仅允许所需的来源/端口。内部 NLB 不能替代授权或网络控制。

创建 TargetGroup 不会注册目标。ACK 目标可以管理固定 IP；不断变化的 Kubernetes Pod IP 需要适当的 AWS Load Balancer Controller 绑定和所有权计划。避免两个 controller 争用同一个 AWS 对象。

NLB 和 TargetGroup ARN 位于 status.ackResourceMetadata.arn。Listener 使用受支持的引用。Route 53 使用 recordType，而不是 type。请从实际 NLB status 中填充 alias DNS 和 canonicalHostedZoneID。记录的托管区域与 NLB 别名目标的托管区域 ID 是不同的值。

Aurora PostgreSQL 17.10 于 2026 年 8 月发布。请使用 describe-db-engine-versions 和 describe-orderable-db-instance-options，针对实际账户/区域验证引擎/实例类组合和升级路径。之前的 15.4 并非新的默认值。准备跨至少两个受支持 AZ 的数据库子网，并验证放置/可用性。

manageMasterUserPassword=true 请求 RDS Secrets Manager 集成，不提供明文密码示例。请为应用程序准备所需的 KMS/Secrets Manager 权限、成本以及经批准的文件交付方式。deletionProtection 和 retain 保护的是不同的生命周期层。

DBInstance 名称或 Role 标签无法固定 writer/reader 角色。请检查实际集群成员资格；故障转移可能会更改 writer。promotionTier 是提升优先级，而非永久角色分配。自定义 READER endpoint 仅使用当前为 reader 的所选实例。请检查可用成员，以及故障转移后的重连行为。看似包含 AZ 的 endpoint 名称并不能实现 AZ 筛选。

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

## 验证和运维前提条件

字段已根据官方带版本的 CRD 进行检查。schema 成功并不代表 IAM 权限、AWS 服务约束、创建、连接性或恢复已得到保证。在应用前，请为保留的资源明确所有权、成本、清理和备份责任。

- [elbv2 v1.7.0 CRD](https://github.com/aws-controllers-k8s/elbv2-controller/tree/v1.7.0/config/crd/bases)
- [route53 v1.6.0 CRD](https://github.com/aws-controllers-k8s/route53-controller/tree/v1.6.0/config/crd/bases)
- [rds v1.12.0 CRD](https://github.com/aws-controllers-k8s/rds-controller/tree/v1.12.0/config/crd/bases)
- [Aurora PostgreSQL 次要版本](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-aurora-postgresql-18-4-17-10-16-14-15-18-14-23/)
- [Aurora 自定义 endpoint](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.html)
