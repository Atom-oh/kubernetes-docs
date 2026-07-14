# ELBv2, Route 53, RDS Resource Creation Examples (ACK)

> **注記**: このドキュメントには、[ACK の概念ドキュメント](../02-ack.md)のハンズオン例が含まれています。

## ELBv2, Route 53, RDS Resource Creation Examples

この例では、ACK を使用して、一般的な本番環境のインフラストラクチャパターンである NLB (Network Load Balancer)、Route 53 DNS、Aurora PostgreSQL をプロビジョニングする方法を示します。これは本番ワークロードで最も広く使用されているインフラストラクチャの組み合わせの 1 つです。

### Controller Installation

ELBv2、Route 53、RDS controller をインストールします。

```bash
# Install 3 controllers
for SERVICE in elbv2 route53 rds; do
  helm install -n ack-system ack-${SERVICE}-controller \
    oci://public.ecr.aws/aws-controllers-k8s/${SERVICE}-chart \
    --create-namespace \
    --set aws.region=ap-northeast-2
done
```

### Creating NLB (ACK ELBv2)

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: LoadBalancer
metadata:
  name: my-app-nlb
  namespace: infra
spec:
  name: my-app-nlb
  scheme: internal
  type: network
  subnetMappings:
    - subnetID: subnet-0123456789abcdef0
    - subnetID: subnet-0123456789abcdef1
    - subnetID: subnet-0123456789abcdef2
  tags:
    - key: Environment
      value: Production
    - key: Team
      value: platform
```

作成後、`.status.dnsName` から NLB の DNS 名を確認できます。

### Creating Target Group

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: TargetGroup
metadata:
  name: my-app-tg
  namespace: infra
spec:
  name: my-app-tg
  protocol: TCP
  port: 8080
  targetType: ip
  vpcID: vpc-0123456789abcdef0
  healthCheckProtocol: TCP
  healthCheckPort: "8080"
  healthyThresholdCount: 3
  unhealthyThresholdCount: 3
  tags:
    - key: Environment
      value: Production
```

作成後、`.status.targetGroupARN` から Target Group ARN を確認できます。

### Creating Listener

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: Listener
metadata:
  name: my-app-listener
  namespace: infra
spec:
  loadBalancerARN: <NLB's .status.loadBalancerARN>
  port: 80
  protocol: TCP
  defaultActions:
    - type: forward
      targetGroupARN: <TargetGroup's .status.targetGroupARN>
```

### Registering Route 53 DNS Record

```yaml
apiVersion: route53.services.k8s.aws/v1alpha1
kind: RecordSet
metadata:
  name: my-app-dns
  namespace: infra
spec:
  hostedZoneID: Z0123456789ABCDEFGHIJ
  name: app.example.com
  type: A
  aliasTarget:
    dnsName: <NLB's .status.dnsName>
    hostedZoneID: <NLB's Hosted Zone ID>
    evaluateTargetHealth: true
```

### Creating Aurora PostgreSQL Cluster

#### DBSubnetGroup

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBSubnetGroup
metadata:
  name: my-aurora-subnet-group
  namespace: infra
spec:
  name: my-aurora-subnet-group
  description: "Subnet group for Aurora PostgreSQL"
  subnetIDs:
    - subnet-0123456789abcdef0
    - subnet-0123456789abcdef1
    - subnet-0123456789abcdef2
  tags:
    - key: Environment
      value: Production
```

#### DBCluster

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBCluster
metadata:
  name: my-aurora-cluster
  namespace: infra
spec:
  dbClusterIdentifier: my-aurora-cluster
  engine: aurora-postgresql
  engineVersion: "15.4"
  masterUsername: dbadmin
  masterUserPassword:
    name: aurora-master-password
    key: password
  vpcSecurityGroupIDs:
    - sg-0123456789abcdef0
  dbSubnetGroupName: my-aurora-subnet-group
  storageEncrypted: true
  tags:
    - key: Environment
      value: Production
```

作成後、`.status.endpoint` (Writer endpoint) と `.status.readerEndpoint` (Reader endpoint) を確認できます。

#### DBInstance (Writer)

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-aurora-writer
  namespace: infra
spec:
  dbInstanceIdentifier: my-aurora-writer
  dbClusterIdentifier: my-aurora-cluster
  dbInstanceClass: db.r6g.xlarge
  engine: aurora-postgresql
  availabilityZone: ap-northeast-2a
  tags:
    - key: Role
      value: Writer
```

#### DBInstance (Reader 1)

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-aurora-reader-1
  namespace: infra
spec:
  dbInstanceIdentifier: my-aurora-reader-2b
  dbClusterIdentifier: my-aurora-cluster
  dbInstanceClass: db.r6g.xlarge
  engine: aurora-postgresql
  availabilityZone: ap-northeast-2b
  tags:
    - key: Role
      value: Reader
```

#### DBInstance (Reader 2)

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-aurora-reader-2
  namespace: infra
spec:
  dbInstanceIdentifier: my-aurora-reader-2c
  dbClusterIdentifier: my-aurora-cluster
  dbInstanceClass: db.r6g.xlarge
  engine: aurora-postgresql
  availabilityZone: ap-northeast-2c
  tags:
    - key: Role
      value: Reader
```

### Custom Endpoint (Per-AZ Read Replica)

特定の Availability Zones の Reader instances のみを使用する custom endpoints を作成できます。

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBClusterEndpoint
metadata:
  name: my-aurora-reader-2a-endpoint
  namespace: infra
spec:
  dbClusterIdentifier: my-aurora-cluster
  dbClusterEndpointIdentifier: my-aurora-reader-2a
  endpointType: READER
  staticMembers:
    - my-aurora-reader-2b
---
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBClusterEndpoint
metadata:
  name: my-aurora-reader-2b-endpoint
  namespace: infra
spec:
  dbClusterIdentifier: my-aurora-cluster
  dbClusterEndpointIdentifier: my-aurora-reader-2b
  endpointType: READER
  staticMembers:
    - my-aurora-reader-2c
```

### Checking Resource Status

```bash
# Check NLB, Target Group, Listener status
kubectl get loadbalancers,targetgroups,listeners -n infra

# Check Aurora cluster and instance status
kubectl get dbclusters,dbinstances,dbclusterendpoints -n infra

# Check Route 53 record status
kubectl get recordsets -n infra
```
