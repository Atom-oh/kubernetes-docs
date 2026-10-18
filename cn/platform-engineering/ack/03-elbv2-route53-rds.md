# ELBv2、Route 53 和 Aurora (ACK)

[ACK](../02-ack.md)

以下是 ELBv2 1.8.2 / Route 53 1.7.1 / RDS 1.13.3 的独立架构示例。它们不会将 NLB 放在 Aurora 前面。内部 NLB/DNS 为应用程序提供服务，而 Aurora 是一个独立的应用程序依赖项。尚未测试端到端的连通部署。

为这三个控制器准备基础设施和身份验证/权限。将 VPC、私有子网、安全组和托管区域 ID 替换为已批准的值。NLB 和数据库安全组应仅允许必需的来源/端口。内部 NLB 不能替代授权或网络控制。

创建 TargetGroup 不会注册目标。ACK 目标可以管理固定 IP；Kubernetes Pod IP 发生变化时，需要适当的 AWS Load Balancer Controller 绑定和所有权方案。避免两个控制器争用同一个 AWS 对象。

NLB 和 TargetGroup ARN 位于 status.ackResourceMetadata.arn。Listener 使用受支持的引用。Route 53 使用 recordType，而不是 type。请根据 NLB 的实际状态填写别名 DNS 和 canonicalHostedZoneID。记录的托管区域与 NLB 别名目标的托管区域 ID 是不同的值。

Aurora PostgreSQL 17.10 于 2026 年 8 月发布。请使用 describe-db-engine-versions 和 describe-orderable-db-instance-options，针对实际账户/区域验证引擎/实例类组合和升级路径。之前的 15.4 不是新的默认版本。准备分布在至少两个受支持 AZ 中的数据库子网，并验证放置/可用性。

manageMasterUserPassword=true 会请求 RDS Secrets Manager 集成，不需要提供明文密码示例。请准备所需的 KMS/Secrets Manager 权限、成本，以及向应用程序交付文件的批准流程。deletionProtection 和 retain 保护的是不同的生命周期层。

DBInstance 名称或 Role 标签无法确定写入器/读取器角色。请检查实际的集群成员；故障转移可能会更改写入器。promotionTier 是提升优先级，而不是永久角色分配。自定义 READER 端点只会使用所选的、当前为读取器的实例。请检查可用成员以及故障转移后的重新连接行为。看起来像 AZ 的端点名称并不会实现 AZ 筛选。

## LoadBalancer: loadbalancer-app-nlb

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

## TargetGroup: targetgroup-app-tg

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

## Listener: listener-app-listener

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

## RecordSet: recordset-app-dns

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

## DBSubnetGroup: dbsubnetgroup-app-db-subnets

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

## DBCluster: dbcluster-app-aurora

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

## DBInstance: dbinstance-app-db-1

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

## DBInstance: dbinstance-app-db-2

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

## DBInstance: dbinstance-app-db-3

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

## DBClusterEndpoint: dbclusterendpoint-app-selected-readers

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

## 验证和运维前提

已根据官方的版本化 CRD 检查字段。架构验证成功并不代表 IAM 权限、AWS 服务约束、资源创建、连通性或恢复能力均已得到确认。应用配置前，请明确保留资源的所有权、成本、清理和备份责任。

- [elbv2 v1.8.2 CRD](https://github.com/aws-controllers-k8s/elbv2-controller/tree/v1.8.2/config/crd/bases)
- [route53 v1.7.1 CRD](https://github.com/aws-controllers-k8s/route53-controller/tree/v1.7.1/config/crd/bases)
- [rds v1.13.3 CRD](https://github.com/aws-controllers-k8s/rds-controller/tree/v1.13.3/config/crd/bases)
- [Aurora PostgreSQL 次要版本](https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-aurora-postgresql-18-4-17-10-16-14-15-18-14-23/)
- [Aurora 自定义端点](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Custom.html)
