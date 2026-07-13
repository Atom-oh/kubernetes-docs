# Ejemplos de creación de recursos ELBv2, Route 53, RDS (ACK)

> **Nota**: Este documento contiene ejemplos prácticos del [documento de conceptos de ACK](../02-ack.md).

## Ejemplos de creación de recursos ELBv2, Route 53, RDS

Este ejemplo demuestra el aprovisionamiento de un patrón común de infraestructura de producción — NLB (Network Load Balancer), DNS de Route 53 y Aurora PostgreSQL — usando ACK. Esta es una de las combinaciones de infraestructura más utilizadas en cargas de trabajo de producción.

### Instalación de Controllers

Instale los controllers de ELBv2, Route 53 y RDS:

```bash
# Install 3 controllers
for SERVICE in elbv2 route53 rds; do
  helm install -n ack-system ack-${SERVICE}-controller \
    oci://public.ecr.aws/aws-controllers-k8s/${SERVICE}-chart \
    --create-namespace \
    --set aws.region=ap-northeast-2
done
```

### Creación de NLB (ACK ELBv2)

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

Después de la creación, puede comprobar el nombre DNS del NLB desde `.status.dnsName`.

### Creación de Target Group

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

Después de la creación, puede comprobar el ARN del Target Group desde `.status.targetGroupARN`.

### Creación de Listener

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

### Registro de registro DNS de Route 53

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

### Creación de cluster Aurora PostgreSQL

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

Después de la creación, puede comprobar `.status.endpoint` (endpoint Writer) y `.status.readerEndpoint` (endpoint Reader).

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

### Endpoint personalizado (Read Replica por AZ)

Puede crear endpoints personalizados que usen solo instancias Reader en Availability Zones específicas:

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

### Comprobación del estado de los recursos

```bash
# Check NLB, Target Group, Listener status
kubectl get loadbalancers,targetgroups,listeners -n infra

# Check Aurora cluster and instance status
kubectl get dbclusters,dbinstances,dbclusterendpoints -n infra

# Check Route 53 record status
kubectl get recordsets -n infra
```
