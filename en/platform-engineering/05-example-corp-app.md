# ExampleCorp Order System: ACK + KRO Integrated Deployment

> **Last Updated**: November 24, 2025

## Scenario Overview

An end-to-end example of deploying ExampleCorp's Order API to Kubernetes. ACK provisions AWS infrastructure (NLB, Aurora PostgreSQL, Route 53), while KRO manages application resources (Deployment, Service, TargetGroupBinding, ConfigMap) as a single Custom Resource.

```
ACK (AWS Infrastructure)    KRO (App Deployment)
─────────────────────     ─────────────────────
NLB + TargetGroup    ←──  TargetGroupBinding
Aurora PostgreSQL    ←──  ConfigMap (endpoints)
Route 53 Record           Deployment + Service
```

ACK uses the ELBv2, Route 53, and RDS controllers described in the [ACK document](./02-ack.md) to create infrastructure, and KRO manages the application resources referencing this infrastructure as a single CR.

## Architecture Diagram

```mermaid
graph LR
    subgraph ack["ACK (AWS Infrastructure)"]
        NLB[NLB] --> TG[Target Group]
        R53[Route 53 Record] --> NLB
        Aurora[Aurora PostgreSQL]
    end

    subgraph kro["KRO (Application)"]
        CR[WebApp CR] --> D[Deployment]
        CR --> S[Service]
        CR --> TGB[TargetGroupBinding]
        CR --> CM[ConfigMap]
    end

    TGB -.->|targetGroupARN| TG
    CM -.->|endpoints| Aurora
    D -.->|envFrom| CM
    S -.->|serviceRef| TGB
```

## Step 1: Infrastructure Provisioning with ACK

Use ACK controllers (elbv2, route53, rds) to provision the following infrastructure. For detailed YAML for each resource, see [ACK Resource Examples](./ack/03-elbv2-route53-rds.md).

- **NLB + TargetGroup + Listener**: Application traffic ingress
- **Route 53 DNS Record**: `app.example.com` → NLB mapping
- **Aurora PostgreSQL**: DBSubnetGroup + DBCluster + Writer + 2 Readers + Custom Endpoint

## Step 2: KRO ResourceGraphDefinition

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: webapp-graph
spec:
  resourceKind:
    group: kro.example.com
    kind: WebApp
    version: v1
  childResources:
    # 1. ConfigMap — Aurora connection info
    - apiVersion: v1
      kind: ConfigMap
      nameTemplate: "{{.parent.metadata.name}}-db-config"
      template: |
        data:
          DB_WRITER_HOST: "{{.parent.spec.aurora.writerEndpoint}}"
          DB_READER_HOST: "{{.parent.spec.aurora.readerEndpoint}}"
          DB_PORT: "{{.parent.spec.aurora.port}}"
          DB_NAME: "{{.parent.spec.aurora.dbName}}"

    # 2. Deployment — App container
    - apiVersion: apps/v1
      kind: Deployment
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          replicas: {{.parent.spec.replicas}}
          selector:
            matchLabels:
              app: {{.parent.spec.appName}}
          template:
            metadata:
              labels:
                app: {{.parent.spec.appName}}
            spec:
              containers:
              - name: {{.parent.spec.appName}}
                image: {{.parent.spec.image}}
                ports:
                - containerPort: {{.parent.spec.port}}
                envFrom:
                - configMapRef:
                    name: {{.children.configmap.metadata.name}}

    # 3. Service — ClusterIP
    - apiVersion: v1
      kind: Service
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          selector:
            app: {{.parent.spec.appName}}
          ports:
          - port: {{.parent.spec.port}}
            targetPort: {{.parent.spec.port}}
          type: ClusterIP

    # 4. TargetGroupBinding — ACK Target Group connection
    - apiVersion: elbv2.k8s.aws/v1beta1
      kind: TargetGroupBinding
      nameTemplate: "{{.parent.metadata.name}}-tgb"
      template: |
        spec:
          targetGroupARN: {{.parent.spec.targetGroupARN}}
          serviceRef:
            name: {{.children.service.metadata.name}}
            port: {{.parent.spec.port}}
          targetType: ip

  statusMappings:
    - childResource:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      conditions:
        - type: Available
          mapping:
            type: Ready
    - childResource:
        kind: Service
        name: "{{.parent.metadata.name}}"
      fieldMappings:
        - child: "spec.clusterIP"
          parent: "status.serviceIP"
```

### Input Field Description

| Field | Description |
|-------|-------------|
| `appName` | Application name (used in labels, selectors) |
| `image` | Container image URI |
| `replicas` | Deployment replica count |
| `port` | Container and service port |
| `targetGroupARN` | Target Group ARN created by ACK |
| `aurora.writerEndpoint` | ACK DBCluster Writer endpoint |
| `aurora.readerEndpoint` | ACK DBCluster Reader endpoint |
| `aurora.port` | Aurora port (default 5432) |
| `aurora.dbName` | Database name |

## Step 3: Application Deployment

```yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: order-api
  namespace: production
spec:
  appName: order-api
  image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/order-api:v1.2.0
  replicas: 3
  port: 8080
  targetGroupARN: <ACK TargetGroup's .status.targetGroupARN>
  aurora:
    writerEndpoint: <ACK DBCluster's .status.endpoint>
    readerEndpoint: <ACK DBCluster's .status.readerEndpoint>
    port: "5432"
    dbName: orders
```

Inject the output values from ACK-created infrastructure (Target Group ARN, Aurora endpoints) into the KRO CR spec.

## Step 4: Verification

```bash
# Check WebApp CR status
kubectl get webapp order-api -n production -o yaml

# Check created resources
kubectl get deploy,svc,targetgroupbinding,configmap -n production -l app=order-api
```

## Operational Patterns

### Adding New Services

Reuse existing infrastructure by simply adding a new WebApp CR:

```yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: payment-api
  namespace: production
spec:
  appName: payment-api
  image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/payment-api:v1.0.0
  replicas: 2
  port: 8080
  targetGroupARN: <new Target Group ARN>
  aurora:
    writerEndpoint: <existing Aurora Writer Endpoint>
    readerEndpoint: <existing Aurora Reader Endpoint>
    port: "5432"
    dbName: payments
```

### Aurora Scaling

Add ACK DBInstances to horizontally scale Read Replicas:

```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-aurora-reader-3
  namespace: infra
spec:
  dbInstanceIdentifier: my-aurora-reader-3
  dbClusterIdentifier: my-aurora-cluster
  dbInstanceClass: db.r6g.xlarge
  engine: aurora-postgresql
```

### Blue/Green Deployment

Perform zero-downtime deployment by replacing the KRO CR. Applying a new version of the CR causes KRO to automatically update the Deployment.

## Reference Documents

- [ACK Concepts and Installation](./02-ack.md)
- [ACK Resource Examples: ELBv2, Route 53, RDS](./ack/03-elbv2-route53-rds.md)
- [KRO Concepts and RGD](./03-kro.md)
