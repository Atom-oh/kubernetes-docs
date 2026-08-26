# Amazon OpenSearch Service

> **Last Updated**: June 30, 2026

Amazon OpenSearch Service is a fully managed search and analytics service used for real-time application monitoring, log analytics, and website search. It's based on OpenSearch, a fork of Elasticsearch, and provides powerful full-text search capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Domain Creation](#domain-creation)
4. [Index Management](#index-management)
5. [Data Ingestion](#data-ingestion)
6. [OpenSearch Dashboards](#opensearch-dashboards)
7. [Security Configuration](#security-configuration)
8. [Cost Optimization](#cost-optimization)
9. [Limitations in Large-scale Log Environments](#limitations-in-large-scale-log-environments)
10. [Comparison with Loki](#comparison-with-loki)

---

## Overview

### OpenSearch vs Elasticsearch

OpenSearch is an open-source project created by AWS in 2021 by forking Elasticsearch 7.10.

| Characteristic | OpenSearch | Elasticsearch |
|----------------|-----------|---------------|
| License | Apache 2.0 | SSPL/Elastic License |
| Managed Service | Amazon OpenSearch Service | Elastic Cloud |
| Compatibility | ES 7.10 API compatible | Latest version |
| Plugins | OpenSearch plugins | Elastic plugins |
| Dashboard | OpenSearch Dashboards | Kibana |

### Amazon OpenSearch Service Features

```
+-------------------------------------------------------------+
|               Amazon OpenSearch Service                      |
+-------------------------------------------------------------+
|  Fully managed        |  Multi-AZ deployment  |  Auto snapshots |
|  Auto patching        |  Encryption (rest/transit) |  VPC integration |
|  Fine-grained Access  |  SAML authentication  |  CloudWatch      |
|  UltraWarm/Cold storage |  Serverless option  |  Cross-cluster   |
+-------------------------------------------------------------+
```

### Key Use Cases

1. **Log Analytics**: Application, infrastructure, and security log analysis
2. **Full-text Search**: Website, document, and product search
3. **Security Analytics**: SIEM, threat detection, compliance
4. **Real-time Monitoring**: Application performance monitoring
5. **Business Analytics**: Clickstream, user behavior analysis

---

## Architecture

### OpenSearch Cluster Architecture

![Application, FluentBit, and Kinesis Data Firehose feed logs into the data nodes of a multi-AZ OpenSearch cluster coordinated by dedicated master nodes; data nodes write hot data to EBS and roll aging data into UltraWarm, which migrates it on to S3-backed cold storage.](../../.gitbook/assets/en-observability-logging-02-opensearch-0.png)

### Node Types

> **Reference**: For AWS instance type performance benchmarks, see [AWS Instance Benchmark](https://benchmark.aws.atomai.click/).

| Node Type | Role | Recommended Instance |
|-----------|------|---------------------|
| **Master** | Cluster management, index metadata | m6g.large.search (3) |
| **Data** | Data storage, search/indexing | r6g.xlarge.search |
| **UltraWarm** | Read-only, cost-effective storage | ultrawarm1.medium |
| **Cold** | S3-based archive | - |

### Data Flow

![An application sends logs through FluentBit into OpenSearch, which indexes them to EBS as hot data, then an ISM policy moves data older than 7 days to UltraWarm and data older than 30 days on to S3-backed cold storage.](../../.gitbook/assets/en-observability-logging-02-opensearch-1.png)

---

## Domain Creation

### Creation via AWS Console

```
1. Access OpenSearch Service console
2. Click "Create domain"
3. Settings:
   - Deployment type: Production
   - Version: OpenSearch 2.x
   - Data nodes: r6g.xlarge.search x 3
   - Master nodes: m6g.large.search x 3
   - EBS: gp3, 500GB per node
   - Network: VPC access
   - Encryption: Enable at-rest and in-transit encryption
   - Enable Fine-grained access control
```

### Creation via Terraform

```hcl
# opensearch.tf

# VPC and subnet data
data "aws_vpc" "main" {
  tags = {
    Name = "main-vpc"
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "tag:Type"
    values = ["private"]
  }
}

# Security group
resource "aws_security_group" "opensearch" {
  name        = "opensearch-sg"
  description = "Security group for OpenSearch domain"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "opensearch-sg"
  }
}

# OpenSearch domain
resource "aws_opensearch_domain" "main" {
  domain_name    = "logs-production"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type            = "r6g.xlarge.search"
    instance_count           = 3
    zone_awareness_enabled   = true
    dedicated_master_enabled = true
    dedicated_master_type    = "m6g.large.search"
    dedicated_master_count   = 3

    zone_awareness_config {
      availability_zone_count = 3
    }

    # UltraWarm settings
    warm_enabled = true
    warm_type    = "ultrawarm1.medium.search"
    warm_count   = 2

    # Cold Storage settings
    cold_storage_options {
      enabled = true
    }
  }

  # EBS settings
  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 500
    iops        = 3000
    throughput  = 250
  }

  # VPC settings
  vpc_options {
    subnet_ids         = slice(data.aws_subnets.private.ids, 0, 3)
    security_group_ids = [aws_security_group.opensearch.id]
  }

  # Encryption settings
  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  # Fine-grained Access Control
  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = "admin"
      master_user_password = var.opensearch_master_password
    }
  }

  # Advanced settings
  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
    "indices.fielddata.cache.size"           = "20"
    "indices.query.bool.max_clause_count"    = "1024"
  }

  # Auto snapshots
  snapshot_options {
    automated_snapshot_start_hour = 23
  }

  # Logging
  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_index_slow.arn
    log_type                 = "INDEX_SLOW_LOGS"
    enabled                  = true
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_search_slow.arn
    log_type                 = "SEARCH_SLOW_LOGS"
    enabled                  = true
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_error.arn
    log_type                 = "ES_APPLICATION_LOGS"
    enabled                  = true
  }

  tags = {
    Environment = "production"
    Application = "logging"
  }

  depends_on = [aws_iam_service_linked_role.opensearch]
}

# CloudWatch log groups
resource "aws_cloudwatch_log_group" "opensearch_index_slow" {
  name              = "/aws/opensearch/logs-production/index-slow-logs"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "opensearch_search_slow" {
  name              = "/aws/opensearch/logs-production/search-slow-logs"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "opensearch_error" {
  name              = "/aws/opensearch/logs-production/error-logs"
  retention_in_days = 30
}

# Service-linked role
resource "aws_iam_service_linked_role" "opensearch" {
  aws_service_name = "opensearchservice.amazonaws.com"
}

# CloudWatch log resource policy
resource "aws_cloudwatch_log_resource_policy" "opensearch" {
  policy_name = "opensearch-log-policy"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "es.amazonaws.com"
        }
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.opensearch_index_slow.arn}:*",
          "${aws_cloudwatch_log_group.opensearch_search_slow.arn}:*",
          "${aws_cloudwatch_log_group.opensearch_error.arn}:*"
        ]
      }
    ]
  })
}

# Outputs
output "opensearch_endpoint" {
  value = aws_opensearch_domain.main.endpoint
}

output "opensearch_dashboard_endpoint" {
  value = aws_opensearch_domain.main.dashboard_endpoint
}
```

---

## Index Management

### Index Templates

```json
PUT _index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "priority": 100,
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "5s",
      "index.codec": "best_compression",
      "index.mapping.total_fields.limit": 2000,
      "index.translog.durability": "async",
      "index.translog.sync_interval": "30s"
    },
    "mappings": {
      "properties": {
        "@timestamp": {
          "type": "date"
        },
        "level": {
          "type": "keyword"
        },
        "message": {
          "type": "text",
          "analyzer": "standard"
        },
        "kubernetes": {
          "properties": {
            "namespace": { "type": "keyword" },
            "pod_name": { "type": "keyword" },
            "container_name": { "type": "keyword" },
            "labels": { "type": "object" }
          }
        },
        "trace_id": {
          "type": "keyword"
        },
        "span_id": {
          "type": "keyword"
        },
        "http": {
          "properties": {
            "method": { "type": "keyword" },
            "status_code": { "type": "integer" },
            "path": { "type": "keyword" },
            "response_time_ms": { "type": "float" }
          }
        }
      },
      "dynamic_templates": [
        {
          "strings_as_keywords": {
            "match_mapping_type": "string",
            "mapping": {
              "type": "keyword",
              "ignore_above": 1024
            }
          }
        }
      ]
    }
  }
}
```

### ISM (Index State Management) Policies

ISM policies automatically manage index lifecycle.

```json
PUT _plugins/_ism/policies/logs-lifecycle
{
  "policy": {
    "description": "Log index lifecycle management",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [
          {
            "rollover": {
              "min_index_age": "1d",
              "min_primary_shard_size": "30gb"
            }
          }
        ],
        "transitions": [
          {
            "state_name": "warm",
            "conditions": {
              "min_index_age": "7d"
            }
          }
        ]
      },
      {
        "name": "warm",
        "actions": [
          {
            "warm_migration": {},
            "replica_count": {
              "number_of_replicas": 0
            },
            "force_merge": {
              "max_num_segments": 1
            }
          }
        ],
        "transitions": [
          {
            "state_name": "cold",
            "conditions": {
              "min_index_age": "30d"
            }
          }
        ]
      },
      {
        "name": "cold",
        "actions": [
          {
            "cold_migration": {
              "timestamp_field": "@timestamp"
            }
          }
        ],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": {
              "min_index_age": "90d"
            }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [
          {
            "delete": {}
          }
        ]
      }
    ],
    "ism_template": [
      {
        "index_patterns": ["logs-*"],
        "priority": 100
      }
    ]
  }
}
```

### Index Aliases

```json
# Create alias for rollover
PUT logs-production-000001
{
  "aliases": {
    "logs-production": {
      "is_write_index": true
    },
    "logs-production-read": {}
  }
}

# Query alias
GET _alias/logs-production

# Manual rollover (for testing)
POST logs-production/_rollover
{
  "conditions": {
    "max_age": "1d",
    "max_primary_shard_size": "30gb"
  }
}
```

---

## Data Ingestion

### Direct Ingestion from FluentBit to OpenSearch

```yaml
# fluent-bit-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf
        HTTP_Server   On
        HTTP_Listen   0.0.0.0
        HTTP_Port     2020

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On
        K8S-Logging.Parser  On
        K8S-Logging.Exclude On

    [FILTER]
        Name    modify
        Match   *
        Add     cluster_name eks-production
        Add     environment production

    [OUTPUT]
        Name            opensearch
        Match           *
        Host            vpc-logs-production-xxxxx.ap-northeast-2.es.amazonaws.com
        Port            443
        TLS             On
        AWS_Auth        On
        AWS_Region      ap-northeast-2
        Index           logs-production
        Type            _doc
        Logstash_Format On
        Logstash_Prefix logs-production
        Retry_Limit     5
        Buffer_Size     5MB
        Generate_ID     On
        # Compression saves network costs
        Compress        gzip

  parsers.conf: |
    [PARSER]
        Name        docker
        Format      json
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L
        Time_Keep   On

    [PARSER]
        Name        json
        Format      json
        Time_Key    timestamp
        Time_Format %Y-%m-%dT%H:%M:%S.%LZ
```

### FluentBit DaemonSet (Using IRSA)

```yaml
# fluent-bit-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
  labels:
    app: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      serviceAccountName: fluent-bit
      tolerations:
        - key: node-role.kubernetes.io/master
          operator: Exists
          effect: NoSchedule
        - operator: Exists
          effect: NoExecute
        - operator: Exists
          effect: NoSchedule
      containers:
        - name: fluent-bit
          image: public.ecr.aws/aws-observability/aws-for-fluent-bit:2.31.12
          resources:
            limits:
              cpu: 500m
              memory: 500Mi
            requests:
              cpu: 100m
              memory: 100Mi
          volumeMounts:
            - name: varlog
              mountPath: /var/log
              readOnly: true
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
              readOnly: true
            - name: fluent-bit-config
              mountPath: /fluent-bit/etc/
          env:
            - name: AWS_REGION
              value: ap-northeast-2
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
        - name: fluent-bit-config
          configMap:
            name: fluent-bit-config
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: fluent-bit
  namespace: logging
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/FluentBitOpenSearchRole
```

### Ingestion via Kinesis Data Firehose

```hcl
# firehose.tf
resource "aws_kinesis_firehose_delivery_stream" "opensearch" {
  name        = "logs-to-opensearch"
  destination = "opensearch"

  opensearch_configuration {
    domain_arn            = aws_opensearch_domain.main.arn
    role_arn              = aws_iam_role.firehose.arn
    index_name            = "logs"
    index_rotation_period = "OneDay"
    buffering_interval    = 60
    buffering_size        = 5
    retry_duration        = 300

    vpc_config {
      subnet_ids         = data.aws_subnets.private.ids
      security_group_ids = [aws_security_group.firehose.id]
      role_arn           = aws_iam_role.firehose_vpc.arn
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = "opensearch-delivery"
    }

    s3_configuration {
      role_arn           = aws_iam_role.firehose.arn
      bucket_arn         = aws_s3_bucket.backup.arn
      prefix             = "failed/"
      buffering_size     = 10
      buffering_interval = 400
      compression_format = "GZIP"
    }
  }
}
```

---

## OpenSearch Dashboards

### Dashboard Access Setup

```bash
# SSH tunnel (for dev/test)
ssh -i key.pem -L 9200:vpc-logs-production-xxx.ap-northeast-2.es.amazonaws.com:443 ec2-user@bastion

# Or access via ALB (recommended for production)
```

### Create Index Pattern

```
1. Access OpenSearch Dashboards
2. Management > Stack Management > Index Patterns
3. Click "Create index pattern"
4. Index pattern: logs-*
5. Time field: @timestamp
6. Click "Create index pattern"
```

### Search Query Examples

```json
# Search error logs
GET logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "error" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ],
      "filter": [
        { "term": { "kubernetes.namespace": "production" } }
      ]
    }
  },
  "sort": [
    { "@timestamp": { "order": "desc" } }
  ],
  "size": 100
}

# Aggregation query - errors by namespace
GET logs-*/_search
{
  "size": 0,
  "query": {
    "range": {
      "@timestamp": { "gte": "now-24h" }
    }
  },
  "aggs": {
    "by_namespace": {
      "terms": {
        "field": "kubernetes.namespace",
        "size": 20
      },
      "aggs": {
        "by_level": {
          "terms": {
            "field": "level",
            "size": 5
          }
        }
      }
    }
  }
}

# Response time percentiles
GET logs-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        { "exists": { "field": "http.response_time_ms" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "aggs": {
    "response_time_percentiles": {
      "percentiles": {
        "field": "http.response_time_ms",
        "percents": [50, 75, 90, 95, 99]
      }
    }
  }
}
```

### Visualization Creation

```
# Pie Chart: Log level distribution
1. Visualize > Create visualization > Pie
2. Index pattern: logs-*
3. Buckets > Split slices > Terms > level
4. Save

# Line Chart: Errors over time
1. Visualize > Create visualization > Line
2. Index pattern: logs-*
3. Y-axis: Count
4. X-axis: Date Histogram > @timestamp
5. Add filter: level: error
6. Save

# Data Table: Top error messages
1. Visualize > Create visualization > Data table
2. Index pattern: logs-*
3. Bucket: Terms > message.keyword (Top 10)
4. Add filter: level: error
5. Save
```

---

## Security Configuration

### Fine-Grained Access Control (FGAC)

```json
# Create role
PUT _plugins/_security/api/roles/logs-reader
{
  "cluster_permissions": [
    "cluster_composite_ops_ro"
  ],
  "index_permissions": [
    {
      "index_patterns": ["logs-*"],
      "allowed_actions": [
        "read",
        "search"
      ]
    }
  ]
}

# Role mapping (IAM role)
PUT _plugins/_security/api/rolesmapping/logs-reader
{
  "backend_roles": [
    "arn:aws:iam::123456789012:role/DeveloperRole"
  ],
  "users": [
    "developer@example.com"
  ]
}

# Admin role
PUT _plugins/_security/api/roles/logs-admin
{
  "cluster_permissions": [
    "cluster_all"
  ],
  "index_permissions": [
    {
      "index_patterns": ["logs-*"],
      "allowed_actions": ["indices_all"]
    }
  ]
}
```

### Document-Level Security (DLS)

```json
# Role that can only access specific namespace
PUT _plugins/_security/api/roles/team-a-logs
{
  "cluster_permissions": [
    "cluster_composite_ops_ro"
  ],
  "index_permissions": [
    {
      "index_patterns": ["logs-*"],
      "dls": "{\"bool\": {\"must\": [{\"term\": {\"kubernetes.namespace\": \"team-a\"}}]}}",
      "allowed_actions": ["read", "search"]
    }
  ]
}
```

### Field-Level Security (FLS)

```json
# Hide sensitive fields
PUT _plugins/_security/api/roles/logs-restricted
{
  "cluster_permissions": [
    "cluster_composite_ops_ro"
  ],
  "index_permissions": [
    {
      "index_patterns": ["logs-*"],
      "fls": ["~user_id", "~ip_address", "~session_token"],
      "allowed_actions": ["read", "search"]
    }
  ]
}
```

### SAML Authentication Setup

```yaml
# opensearch-security-config.yaml
config:
  dynamic:
    authc:
      saml_auth_domain:
        enabled: true
        order: 1
        http_authenticator:
          type: saml
          challenge: true
          config:
            idp:
              metadata_url: https://example.okta.com/app/xxx/sso/saml/metadata
              entity_id: http://www.okta.com/xxx
            sp:
              entity_id: https://vpc-logs-production-xxx.ap-northeast-2.es.amazonaws.com
            kibana_url: https://vpc-logs-production-xxx.ap-northeast-2.es.amazonaws.com/_dashboards
            roles_key: Role
            exchange_key: your-exchange-key
        authentication_backend:
          type: noop
```

---

## Cost Optimization

### Storage Tiering

```
Hot (EBS gp3)    ->    UltraWarm    ->    Cold Storage (S3)
     |                    |                    |
  Day 0-7            Day 7-30            Day 30-90
     |                    |                    |
 Fast queries        Read-only            Archive
 High cost          Medium cost          Low cost
```

### Cost Comparison (Based on 100GB/day)

```
+-----------------+--------------+--------------+--------------+
|  Storage Tier   |  Retention   | Monthly Cost |  Cost per GB |
+-----------------+--------------+--------------+--------------+
| Hot (EBS gp3)   |    7 days    |   ~$500      |   $0.10/GB   |
| UltraWarm       |   23 days    |   ~$350      |   $0.024/GB  |
| Cold Storage    |   60 days    |   ~$120      |   $0.01/GB   |
+-----------------+--------------+--------------+--------------+
| Total (90-day)  |              |   ~$970/mo   |              |
| Hot only        |   90 days    |  ~$2,700/mo  |              |
| Savings         |              |  ~$1,730/mo  |    64% saved |
+-----------------+--------------+--------------+--------------+
```

### Index Optimization

```json
# Compression settings
PUT logs-*/_settings
{
  "index": {
    "codec": "best_compression"
  }
}

# Adjust refresh interval (during ingestion)
PUT logs-*/_settings
{
  "index": {
    "refresh_interval": "30s"
  }
}

# Disable unnecessary fields
PUT _index_template/logs-optimized
{
  "index_patterns": ["logs-*"],
  "template": {
    "mappings": {
      "_source": {
        "enabled": true
      },
      "properties": {
        "message": {
          "type": "text",
          "norms": false,
          "index_options": "docs"
        }
      }
    }
  }
}
```

### Reserved Instances

```bash
# RI purchase recommendations
# - Purchase RI if planning to use for 1+ years
# - All Upfront option is cheapest (up to 36% savings)
# - Partial Upfront: 24% savings
# - No Upfront: 21% savings
```

---

## Limitations in Large-scale Log Environments

OpenSearch excels at full-text search, but structural limitations emerge when log volume grows rapidly.

### Inverted Index Inefficiency

| Aspect | OpenSearch (Inverted Index) | ClickHouse (Columnar) |
|--------|---------------------------|---------------------|
| **Compression ratio** | 1.5-2x size increase (including index) | 5-10x compression vs original |
| **Aggregation queries** | Requires full document scan | Fast column-level scan |
| **Storage cost** | High (index + original) | Low (columnar compression) |
| **INSERT cost** | High indexing CPU overhead | Lightweight columnar append |

### Aggregation Query Performance Degradation

For frequently used aggregation queries in log analytics (ERROR count in last hour, error rate by service, etc.), OpenSearch must read all matching documents, causing performance to degrade sharply as data grows.

```
Query: "Aggregate ERROR log count by service for the last hour"

OpenSearch: Look up document IDs from index → Read each document → Aggregate
           100GB scale: ~2s / 1TB scale: ~25s / 10TB scale: timeout

ClickHouse: Scan only timestamp, level, service columns → Aggregate
           100GB scale: ~0.3s / 1TB scale: ~1s / 10TB scale: ~8s
```

### Scaling Cost Issues

| Daily Log Volume | OpenSearch Monthly Cost (est.) | ClickHouse Monthly Cost (est.) | Ratio |
|-----------------|-------------------------------|-------------------------------|-------|
| 100GB | ~$970 | ~$400 | 2.4x |
| 500GB | ~$4,500 | ~$1,200 | 3.8x |
| 1TB | ~$9,000 | ~$2,000 | 4.5x |
| 10TB | ~$80,000+ | ~$10,000 | 8x+ |

> **Key Insight**: When analyzing log query patterns, over 90% of queries in most environments are "time range + field condition" based. This pattern is far more efficient with columnar storage than inverted indexes.

### ClickHouse Migration Decision Criteria

Use the following criteria to determine whether to keep OpenSearch or consider migrating to ClickHouse.

| Criteria | Keep OpenSearch | Consider ClickHouse |
|----------|----------------|-------------------|
| **Daily log volume** | Under 100GB | Over 100GB |
| **Primary query pattern** | Full-text search (keyword-based) | Time range + field conditions |
| **Aggregation query ratio** | Low (under 20% of total) | High (over 50% of total) |
| **Cost sensitivity** | Low | High |
| **Full-text search need** | Essential (core feature) | Optional (nice to have) |
| **Team SQL proficiency** | Low | High |

**Migration Considerations:**

```
Phase 1: Query Pattern Analysis (2 weeks)
  └── Analyze actual query logs for full-text search vs field-condition query ratio

Phase 2: Parallel Operation (1-2 months)
  └── Dual-write same logs to both OpenSearch + ClickHouse
  └── Compare query performance and costs

Phase 3: Gradual Migration
  └── Aggregation/dashboard queries → Migrate to ClickHouse first
  └── Queries requiring full-text search → Keep OpenSearch or use ClickHouse tokenbf index
```

---

## Comparison with Loki

### Feature Comparison

| Feature | OpenSearch | Loki |
|---------|-----------|------|
| **Full-text search** | Excellent (Lucene-based) | Limited (labels+grep) |
| **Query language** | Query DSL, SQL | LogQL |
| **Indexing** | Full-text | Labels only |
| **Storage cost** | High | Low (object storage) |
| **Complex aggregations** | Excellent | Basic |
| **Dashboard** | OpenSearch Dashboards | Grafana |
| **Operational complexity** | High | Low |
| **Scalability** | Horizontal | Horizontal |
| **Multi-tenancy** | FGAC | Native |

### Recommendations by Use Case

```
OpenSearch recommended:
+-- Full-text search is required
+-- Complex analytics/aggregation queries needed
+-- Compliance requirements (audit logs)
+-- Security analytics (SIEM)
+-- Migrating from existing ELK stack

Loki recommended:
+-- Cost is top priority
+-- Already using Grafana
+-- Simple log search/filtering
+-- Need Prometheus integration
+-- Want to reduce operational burden
```

### Migration Considerations

```yaml
# Migrating from Loki to OpenSearch
considerations:
  - Query rewriting needed (LogQL -> Query DSL)
  - Dashboard rebuild (Grafana -> OpenSearch Dashboards)
  - Index template/mapping design
  - Expected cost increase (3-5x)
  - Increased operational complexity

# Migrating from OpenSearch to Loki
considerations:
  - Loss of full-text search capabilities
  - Limited complex aggregation queries
  - Existing dashboard/alert rebuild
  - Cost savings (60-80%)
  - Operational simplification
```

---

## Quiz

Test your knowledge with the [OpenSearch Quiz](../../quizzes/observability/logging/02-opensearch-quiz.md).
