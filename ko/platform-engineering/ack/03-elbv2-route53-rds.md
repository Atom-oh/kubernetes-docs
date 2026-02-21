# ELBv2, Route 53, RDS 리소스 생성 예제 (ACK)

> **참고**: 이 문서는 [ACK 개념 문서](../02-ack.md)의 실습 예제입니다.

실무에서 자주 사용하는 NLB(Network Load Balancer), Route 53 DNS, Aurora PostgreSQL 조합을 ACK로 프로비저닝하는 예제입니다. 이 패턴은 프로덕션 워크로드에서 가장 일반적인 인프라 구성 중 하나입니다.

## 컨트롤러 설치

ELBv2, Route 53, RDS 컨트롤러를 설치합니다:

```bash
# 3개 컨트롤러 설치
for SERVICE in elbv2 route53 rds; do
  helm install -n ack-system ack-${SERVICE}-controller \
    oci://public.ecr.aws/aws-controllers-k8s/${SERVICE}-chart \
    --create-namespace \
    --set aws.region=ap-northeast-2
done
```

## NLB 생성 (ACK ELBv2)

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

생성 후 `.status.dnsName`에서 NLB의 DNS 이름을 확인할 수 있습니다.

## Target Group 생성

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

생성 후 `.status.targetGroupARN`에서 Target Group ARN을 확인할 수 있습니다.

## Listener 생성

```yaml
apiVersion: elbv2.services.k8s.aws/v1alpha1
kind: Listener
metadata:
  name: my-app-listener
  namespace: infra
spec:
  loadBalancerARN: <NLB의 .status.loadBalancerARN>
  port: 80
  protocol: TCP
  defaultActions:
    - type: forward
      targetGroupARN: <TargetGroup의 .status.targetGroupARN>
```

## Route 53 DNS 레코드 등록

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
    dnsName: <NLB의 .status.dnsName>
    hostedZoneID: <NLB의 Hosted Zone ID>
    evaluateTargetHealth: true
```

## Aurora PostgreSQL 클러스터 생성

### DBSubnetGroup

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

### DBCluster

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

생성 후 `.status.endpoint`(Writer 엔드포인트)와 `.status.readerEndpoint`(Reader 엔드포인트)를 확인할 수 있습니다.

### DBInstance (Writer)

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

### DBInstance (Reader 1)

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

### DBInstance (Reader 2)

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

## Custom Endpoint (AZ별 Read Replica)

특정 AZ의 Reader 인스턴스만 사용하는 커스텀 엔드포인트를 생성할 수 있습니다:

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

## 리소스 상태 확인

```bash
# NLB, Target Group, Listener 상태 확인
kubectl get loadbalancers,targetgroups,listeners -n infra

# Aurora 클러스터 및 인스턴스 상태 확인
kubectl get dbclusters,dbinstances,dbclusterendpoints -n infra

# Route 53 레코드 상태 확인
kubectl get recordsets -n infra
```
