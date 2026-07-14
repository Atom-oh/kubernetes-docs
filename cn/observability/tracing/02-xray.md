# AWS X-Ray

> **最后更新**: February 20, 2026

## 简介

AWS X-Ray 是一项 AWS 原生服务，用于跟踪和分析分布式应用程序中的请求。在 EKS 环境中使用 X-Ray，可让您可视化微服务之间的请求流，识别性能瓶颈，并确定错误的根本原因。

## 主要功能

| 功能 | 描述 |
|---------|-------------|
| **Service Map** | 自动可视化服务依赖关系 |
| **Request Tracing** | 端到端请求路径跟踪 |
| **Analysis Tools** | 响应时间分布、错误率分析 |
| **AWS Integration** | 原生支持 Lambda、API Gateway、ECS、EKS |
| **Sampling Rules** | 集中式采样配置 |
| **Groups and Alerts** | 基于筛选条件的分组和 CloudWatch 告警 |

## 架构

```mermaid
flowchart TD
    subgraph EKS["Amazon EKS Cluster"]
        subgraph Apps["Application Pods"]
            APP1[Service A<br/>X-Ray SDK]
            APP2[Service B<br/>X-Ray SDK]
            APP3[Service C<br/>X-Ray SDK]
        end

        subgraph Collector["Data Collection"]
            DAEMON[X-Ray Daemon<br/>DaemonSet]
            ADOT[ADOT Collector<br/>Sidecar/DaemonSet]
        end
    end

    subgraph AWS["AWS Services"]
        XRAY[AWS X-Ray]
        CW[CloudWatch]
        LENS[ServiceLens]
        INSIGHTS[X-Ray Insights]
    end

    subgraph Other["Other AWS Services"]
        LAMBDA[Lambda]
        APIGW[API Gateway]
        SQS[SQS]
        SNS[SNS]
    end

    APP1 & APP2 & APP3 -->|Segments| DAEMON
    APP1 & APP2 & APP3 -->|OTLP| ADOT
    DAEMON -->|UDP/TCP| XRAY
    ADOT -->|OTLP| XRAY

    LAMBDA & APIGW & SQS & SNS -->|Auto instrumentation| XRAY

    XRAY --> CW
    XRAY --> LENS
    XRAY --> INSIGHTS

    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef collector fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef aws fill:#FF9900,stroke:#333,stroke-width:1px,color:black
    classDef other fill:#3B48CC,stroke:#333,stroke-width:1px,color:white

    class APP1,APP2,APP3 app
    class DAEMON,ADOT collector
    class XRAY,CW,LENS,INSIGHTS aws
    class LAMBDA,APIGW,SQS,SNS other
```

## X-Ray Daemon 部署

### 以 DaemonSet 部署

```yaml
# xray-daemon.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: xray-daemon
  namespace: amazon-cloudwatch
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/xray-daemon-role
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: xray-daemon
  namespace: amazon-cloudwatch
spec:
  selector:
    matchLabels:
      app: xray-daemon
  updateStrategy:
    type: RollingUpdate
  template:
    metadata:
      labels:
        app: xray-daemon
    spec:
      serviceAccountName: xray-daemon
      containers:
        - name: xray-daemon
          image: public.ecr.aws/xray/aws-xray-daemon:3.3.7
          command:
            - /usr/bin/xray
            - --bind=0.0.0.0:2000
            - --bind-tcp=0.0.0.0:2000
            - --region=ap-northeast-2
            - --log-level=info
          ports:
            - name: xray-udp
              containerPort: 2000
              hostPort: 2000
              protocol: UDP
            - name: xray-tcp
              containerPort: 2000
              hostPort: 2000
              protocol: TCP
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 100m
              memory: 128Mi
          env:
            - name: AWS_REGION
              value: ap-northeast-2
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
---
apiVersion: v1
kind: Service
metadata:
  name: xray-daemon
  namespace: amazon-cloudwatch
spec:
  selector:
    app: xray-daemon
  ports:
    - name: xray-udp
      port: 2000
      protocol: UDP
    - name: xray-tcp
      port: 2000
      protocol: TCP
  clusterIP: None
```

### IRSA 配置

```yaml
# IAM Policy for X-Ray
# xray-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets",
        "xray:GetSamplingStatisticSummaries"
      ],
      "Resource": "*"
    }
  ]
}
```

```bash
# Create IRSA role
eksctl create iamserviceaccount \
  --name xray-daemon \
  --namespace amazon-cloudwatch \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess \
  --approve \
  --override-existing-serviceaccounts
```

## ADOT Collector 部署

使用 AWS Distro for OpenTelemetry (ADOT) 与 X-Ray 集成：

### ADOT Collector DaemonSet

```yaml
# adot-collector.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: adot-collector-config
  namespace: amazon-cloudwatch
data:
  collector.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
      # X-Ray SDK compatibility
      awsxray:
        endpoint: 0.0.0.0:2000
        transport: udp
      # Prometheus metrics (optional)
      prometheus:
        config:
          scrape_configs:
            - job_name: 'otel-collector'
              scrape_interval: 10s
              static_configs:
                - targets: ['localhost:8888']

    processors:
      batch:
        timeout: 5s
        send_batch_size: 256

      memory_limiter:
        limit_mib: 512
        spike_limit_mib: 128
        check_interval: 5s

      # Add resource attributes
      resource:
        attributes:
          - key: cloud.provider
            value: aws
            action: upsert
          - key: k8s.cluster.name
            from_attribute: CLUSTER_NAME
            action: upsert

      # AWS attribute detection
      resourcedetection:
        detectors: [env, eks, ec2]
        timeout: 2s
        override: false

    exporters:
      awsxray:
        region: ap-northeast-2
        index_all_attributes: true
        indexed_attributes:
          - otel.resource.service.name
          - otel.resource.service.namespace
          - aws.local.service

      # CloudWatch Logs (trace logs)
      awscloudwatchlogs:
        log_group_name: "/aws/xray/traces"
        log_stream_name: "otel-traces"
        region: ap-northeast-2

      # Prometheus Remote Write (optional)
      prometheusremotewrite:
        endpoint: http://prometheus:9090/api/v1/write

    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
      pprof:
        endpoint: 0.0.0.0:1777

    service:
      extensions: [health_check, pprof]
      pipelines:
        traces:
          receivers: [otlp, awsxray]
          processors: [memory_limiter, resourcedetection, resource, batch]
          exporters: [awsxray]
        metrics:
          receivers: [otlp, prometheus]
          processors: [memory_limiter, batch]
          exporters: [prometheusremotewrite]
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: adot-collector
  namespace: amazon-cloudwatch
spec:
  selector:
    matchLabels:
      app: adot-collector
  template:
    metadata:
      labels:
        app: adot-collector
    spec:
      serviceAccountName: adot-collector
      containers:
        - name: collector
          image: public.ecr.aws/aws-observability/aws-otel-collector:v0.36.0
          command:
            - /awscollector
            - --config=/conf/collector.yaml
          ports:
            - containerPort: 4317  # OTLP gRPC
              hostPort: 4317
              protocol: TCP
            - containerPort: 4318  # OTLP HTTP
              hostPort: 4318
              protocol: TCP
            - containerPort: 2000  # X-Ray
              hostPort: 2000
              protocol: UDP
            - containerPort: 13133 # Health check
              protocol: TCP
          env:
            - name: CLUSTER_NAME
              value: my-eks-cluster
            - name: AWS_REGION
              value: ap-northeast-2
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: config
              mountPath: /conf
          livenessProbe:
            httpGet:
              path: /
              port: 13133
            initialDelaySeconds: 15
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 13133
            initialDelaySeconds: 5
            periodSeconds: 10
      volumes:
        - name: config
          configMap:
            name: adot-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: adot-collector
  namespace: amazon-cloudwatch
spec:
  selector:
    app: adot-collector
  ports:
    - name: otlp-grpc
      port: 4317
      protocol: TCP
    - name: otlp-http
      port: 4318
      protocol: TCP
    - name: xray
      port: 2000
      protocol: UDP
```

## 采样规则

### 集中式采样配置

```bash
# Create sampling rule
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "production-api",
    "Priority": 1000,
    "FixedRate": 0.05,
    "ReservoirSize": 10,
    "ServiceName": "*",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "/api/*",
    "Version": 1,
    "Attributes": {}
  }
}'

# 100% sampling for error requests
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "error-requests",
    "Priority": 100,
    "FixedRate": 1.0,
    "ReservoirSize": 50,
    "ServiceName": "*",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "Version": 1,
    "Attributes": {
      "http.status_code": "5*"
    }
  }
}'
```

### 筛选表达式示例

```bash
# Specific service calls
service("order-service")

# HTTP status code filter
http.status >= 400

# Response time filter
responsetime > 2

# Annotation-based filter
annotation.user_id = "user123"

# Compound filter
service("api-gateway") AND responsetime > 1 AND NOT fault

# Edge filter (inter-service calls)
edge("api-gateway", "order-service")
```

## CloudWatch ServiceLens 集成

ServiceLens 集成 X-Ray 跟踪、CloudWatch 指标和日志：

```yaml
# CloudWatch Agent configuration (EKS)
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudwatch-agent-config
  namespace: amazon-cloudwatch
data:
  cwagentconfig.json: |
    {
      "logs": {
        "metrics_collected": {
          "kubernetes": {
            "cluster_name": "my-eks-cluster",
            "metrics_collection_interval": 60
          }
        },
        "force_flush_interval": 5
      },
      "traces": {
        "traces_collected": {
          "xray": {
            "tcp_proxy": {
              "bind_address": "0.0.0.0:2000"
            }
          },
          "otlp": {
            "grpc_endpoint": "0.0.0.0:4317"
          }
        }
      }
    }
```

## 组和筛选器

### 创建 X-Ray 组

```bash
# Production services group
aws xray create-group \
  --group-name "production-services" \
  --filter-expression 'annotation.environment = "production"'

# Error requests group
aws xray create-group \
  --group-name "error-traces" \
  --filter-expression 'fault = true OR error = true'

# Slow requests group
aws xray create-group \
  --group-name "slow-requests" \
  --filter-expression 'responsetime > 1'

# Specific service group
aws xray create-group \
  --group-name "payment-traces" \
  --filter-expression 'service("payment-service")'
```

## 最佳实践

### 1. Segment 和 Subsegment 设计

```java
// Good example: Meaningful subsegments
try (Segment segment = AWSXRay.beginSegment("ProcessOrder")) {
    segment.putAnnotation("order_id", orderId);
    segment.putAnnotation("customer_id", customerId);

    // Database call
    try (Subsegment dbSubsegment = AWSXRay.beginSubsegment("DynamoDB-GetOrder")) {
        dbSubsegment.putMetadata("query", "GetItem");
        Order order = dynamoDb.getItem(orderId);
    }

    // External API call
    try (Subsegment apiSubsegment = AWSXRay.beginSubsegment("PaymentAPI-Charge")) {
        apiSubsegment.putAnnotation("payment_method", "credit_card");
        PaymentResult result = paymentService.charge(order);
    }

    // Async operation
    try (Subsegment sqsSubsegment = AWSXRay.beginSubsegment("SQS-SendNotification")) {
        sqsSubsegment.setNamespace("aws");
        sqs.sendMessage(notificationQueue, message);
    }
}
```

### 2. 使用 Annotations 和 Metadata

```java
// Annotation: Indexed, filterable (limit: 50)
segment.putAnnotation("environment", "production");
segment.putAnnotation("user_tier", "premium");
segment.putAnnotation("feature_flag", "new_checkout");

// Metadata: Not indexed, store detailed info
segment.putMetadata("request", requestBody);
segment.putMetadata("response", responseBody);
segment.putMetadata("database", Map.of(
    "query", sqlQuery,
    "parameters", queryParams,
    "rows_affected", rowCount
));
```

### 3. 成本优化

```yaml
# Cost reduction through sampling
sampling:
  # Default 5% sampling
  default:
    fixed_rate: 0.05
    reservoir_size: 10

  # 100% sampling for errors
  errors:
    fixed_rate: 1.0
    reservoir_size: 50

  # Exclude health checks
  health_checks:
    fixed_rate: 0
    url_path: "/health*"
```

## 测验

通过 [X-Ray 测验](../../quizzes/observability/tracing/02-xray-quiz.md) 测试您的知识。
