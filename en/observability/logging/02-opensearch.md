# Amazon OpenSearch Service

> **Last Updated**: September 13, 2026
> **Example baseline**: provisioned OpenSearch Service 3.5; Terraform 1.15.7/AWS provider 6.64.0; AWS for Fluent Bit 3.4.15 (Fluent Bit 5.0.9). Local configuration checks only; no domain, collector, SAML session or data-delivery test was deployed.

Amazon OpenSearch Service manages search clusters and supports selected OpenSearch and legacy Elasticsearch OSS versions. This chapter covers a VPC domain and the traditional hot/UltraWarm/cold tiers. Serverless collections and newer optimized-instance storage options have separate configuration, API and availability requirements.

<span id="table-of-contents"></span>
<span id="opensearch-vs-elasticsearch"></span>
<span id="amazon-opensearch-service-features"></span>
<span id="key-use-cases"></span>

## Overview

OpenSearch is an Apache-2.0-licensed search project. Its Elasticsearch 7.10 lineage does not imply compatibility with every current Elasticsearch client, plugin or API. Elastic's current source-license choices include AGPLv3 for eligible source portions alongside SSPL/Elastic License 2.0; check the exact component and distribution rather than treating Elasticsearch as a single unchanged licensing model.

The AWS support table currently lists OpenSearch 3.5 among supported versions. The earlier 2.11 example is **still under standard support through November 7, 2027**; it is not unsupported simply because a newer version exists. For an existing domain, check supported upgrade paths, breaking changes, snapshots and client compatibility before requesting a version upgrade.

OpenSearch Service can support log analytics, full-text search, aggregations and security-analysis workflows. Enabling a service or retaining audit logs does not itself satisfy a compliance requirement.

<span id="node-types"></span>

## Architecture

### OpenSearch Cluster Architecture

![Conceptual provisioned-domain ingestion and traditional hot/UltraWarm/cold storage flow.](../../.gitbook/assets/en-observability-logging-02-opensearch-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-logging-02-opensearch-0.html)

The diagram is schematic, not an exact replica/AZ layout or a sizing recommendation. Its “Master” label means the dedicated cluster-management role; AWS configuration fields still use `dedicated_master_*`. “Kinesis Data Firehose” is the former name of **Amazon Data Firehose**. Both UltraWarm and cold storage use S3-backed storage; cold data must be attached to UltraWarm before querying.

| Role or tier | Function |
|---|---|
| Dedicated cluster-manager nodes | Cluster state, metadata and shard-allocation management. Three is the conventional dedicated-manager configuration; these are not data replicas. |
| Data nodes / hot storage | Indexing and querying. EBS availability and limits depend on the selected instance family. |
| UltraWarm | Read-only indexes backed by S3, with warm-node caching/compute. Check engine, instance and dedicated-manager prerequisites. |
| Cold storage | Detached index storage with a separate lifecycle. Reattach selected indexes to UltraWarm to query them. |

Multi-AZ with Standby has additional topology and replica requirements. Merely enabling zone awareness does not enable Standby or establish its availability guarantees. Review current instance restrictions, including VPC Encryption Controls and storage compatibility. The original r6g/m6g sizes are example inputs, not a benchmark.

Supplementary resource: [AWS Instance Benchmark](https://benchmark.aws.atomai.click/). Service capacity still requires a representative OpenSearch workload test.

### Data Flow

![Illustrative daily-index lifecycle: ingestion to hot storage, then an ISM transition to UltraWarm and cold storage.](../../.gitbook/assets/en-observability-logging-02-opensearch-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-logging-02-opensearch-1.html)

The 7/30-day labels are example **index-age conditions**, not automatic defaults or exact event-age retention. ISM runs periodically and migration is asynchronous. Late or replayed events can target an older read-only index with date-based indexing; decide how to route or archive them before enabling migration.

<span id="creation-via-aws-console"></span>

## Domain Creation

### Prerequisites

Prepare three private subnets in distinct AZs of the same VPC, reachable client security groups, an existing service-linked role, and approved administrator/writer/reader IAM roles. The example validates distinct subnet IDs, but does not remotely verify their AZs, routes, capacity or ownership.

The Terraform profile uses **IAM-signed API requests** and an IAM master role. It avoids an internal master password in Terraform state. Configure FGAC role mappings before sending logs. Browser SSO is a separate access profile discussed below; an IAM-principal domain policy requires SigV4 and does not automatically accept unsigned SAML browser requests.

### Creation via Terraform

The example uses the commercial AWS partition and Seoul Region. Replace inputs consistently and check regional availability. It creates resources if applied; the audit ran local validation only.

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the owning AWS account ID."
  }
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
  validation {
    condition     = length(var.subnet_ids) == 3 && length(distinct(var.subnet_ids)) == 3
    error_message = "Provide three distinct subnet IDs, one in each intended AZ."
  }
}

variable "client_security_group_ids" {
  type = set(string)
}

variable "admin_role_arn" {
  type = string
}

variable "writer_role_arns" {
  type = set(string)
}

variable "reader_role_arns" {
  type    = set(string)
  default = []
}

provider "aws" {
  region = var.region
}

locals {
  domain_name = "logs-production"
  domain_arn  = "arn:aws:es:${var.region}:${var.account_id}:domain/${local.domain_name}"
  log_types   = toset(["INDEX_SLOW_LOGS", "SEARCH_SLOW_LOGS", "ES_APPLICATION_LOGS", "AUDIT_LOGS"])
  callers     = setunion(toset([var.admin_role_arn]), var.writer_role_arns, var.reader_role_arns)
}

resource "aws_security_group" "search" {
  name_prefix = "logs-search-"
  description = "OpenSearch HTTPS from approved client security groups"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "clients" {
  for_each                     = var.client_security_group_ids
  security_group_id            = aws_security_group.search.id
  referenced_security_group_id = each.value
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "outbound" {
  security_group_id = aws_security_group.search.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_cloudwatch_log_group" "search" {
  for_each          = local.log_types
  name              = "/aws/opensearch/${local.domain_name}/${lower(each.value)}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_resource_policy" "search" {
  policy_name = "logs-production-opensearch"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "es.amazonaws.com" }
      Action    = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource  = [for group in aws_cloudwatch_log_group.search : "${group.arn}:*"]
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.account_id }
        ArnEquals    = { "aws:SourceArn" = local.domain_arn }
      }
    }]
  })
}

resource "aws_opensearch_domain" "logs" {
  domain_name    = local.domain_name
  engine_version = "OpenSearch_3.5"

  cluster_config {
    instance_type                 = "r6g.xlarge.search"
    instance_count                = 3
    dedicated_master_enabled      = true
    dedicated_master_type         = "m6g.large.search"
    dedicated_master_count        = 3
    zone_awareness_enabled        = true
    multi_az_with_standby_enabled = false
    zone_awareness_config {
      availability_zone_count = 3
    }
    warm_enabled = true
    warm_type    = "ultrawarm1.medium.search"
    warm_count   = 2
    cold_storage_options {
      enabled = true
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 500
  }

  vpc_options {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.search.id]
  }

  encrypt_at_rest {
    enabled = true
  }
  node_to_node_encryption {
    enabled = true
  }
  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-PFS-2023-10"
  }
  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = false
    master_user_options {
      master_user_arn = var.admin_role_arn
    }
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = sort(tolist(local.callers)) }
      Action    = ["es:ESHttp*"]
      Resource  = "${local.domain_arn}/*"
    }]
  })

  dynamic "log_publishing_options" {
    for_each = aws_cloudwatch_log_group.search
    content {
      cloudwatch_log_group_arn = log_publishing_options.value.arn
      log_type                 = log_publishing_options.key
      enabled                  = true
    }
  }

  depends_on = [aws_cloudwatch_log_resource_policy.search]
}

output "domain_endpoint" {
  value = aws_opensearch_domain.logs.endpoint
}

output "dashboards_endpoint" {
  value = aws_opensearch_domain.logs.dashboard_endpoint
}
```

The initial sizes, 500GiB EBS volumes and 30-day CloudWatch retention are illustrative. The profile explicitly uses Multi-AZ **without Standby**. Outbound security-group access remains broad in this reference; design egress restrictions for the actual supported connections before production.

The domain access policy admits the named IAM roles to HTTP operations; **FGAC** must restrict their index/cluster permissions. URI-based IAM permissions alone do not constrain index names embedded in bulk request bodies. Give the collector role only the intended writer mapping.

The platform's service-linked role is an account-level dependency. Reuse or import it through its owning infrastructure state rather than trying to create the same role on every deployment.

OpenSearch domains receive hourly automated snapshots retained for 14 days (up to 336). The old `automated_snapshot_start_hour` example applies to much older Elasticsearch versions, not this OpenSearch profile. Snapshots are recovery mechanisms, not a substitute for a tested retention/restore plan. Red cluster status can prevent snapshots.

CloudWatch publishing needs the scoped resource policy before domain configuration. Publishing slow-log destinations does not enable all slow-log thresholds, and audit-log publishing does not configure every audit event. Configure the corresponding engine/audit settings deliberately; queries and document contents in logs also need access and retention controls.

<span id="index-aliases"></span>

## Index Management

The main collector below writes **daily indexes** named `logs-production-YYYY.MM.DD`. The template, ISM pattern and query examples use that pattern. A separate rollover exercise follows; do not silently combine the two writer strategies.

The following request blocks use OpenSearch Dashboards Dev Tools syntax. They are not standalone JSON files or commands executed by the audit. Use an authorized data-plane client and the intended domain.

### Index Templates

```http
PUT _index_template/logs-template
{
  "index_patterns": [
    "logs-production-*"
  ],
  "priority": 100,
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "5s",
      "index.codec": "best_compression",
      "index.translog.durability": "request"
    },
    "mappings": {
      "dynamic": false,
      "properties": {
        "@timestamp": {
          "type": "date"
        },
        "cluster_name": {
          "type": "keyword"
        },
        "environment": {
          "type": "keyword"
        },
        "stream": {
          "type": "keyword"
        },
        "log": {
          "type": "text",
          "index": false
        },
        "kubernetes": {
          "properties": {
            "namespace_name": {
              "type": "keyword"
            },
            "pod_name": {
              "type": "keyword"
            },
            "container_name": {
              "type": "keyword"
            },
            "host": {
              "type": "keyword"
            }
          }
        },
        "app": {
          "properties": {
            "level": {
              "type": "keyword"
            },
            "message": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "error_type": {
              "type": "keyword"
            },
            "trace_id": {
              "type": "keyword"
            },
            "span_id": {
              "type": "keyword"
            },
            "request_id": {
              "type": "keyword"
            },
            "http": {
              "properties": {
                "method": {
                  "type": "keyword"
                },
                "status_code": {
                  "type": "integer"
                },
                "path": {
                  "type": "keyword"
                },
                "response_time_ms": {
                  "type": "float"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

The Kubernetes filter produces `kubernetes.namespace_name`, not `kubernetes.namespace`. Application JSON is nested under `app` to keep it separate from collector metadata. Applications must emit the documented fields and units; examples use lowercase `app.level` and milliseconds in `app.http.response_time_ms`.

An illustrative one-line application record before collector enrichment is:

```json
{"level":"error","message":"request failed","error_type":"upstream_timeout","http":{"method":"GET","path":"/orders","status_code":503,"response_time_ms":1250}}
```

The `message.keyword` subfield is explicitly defined as `app.message.keyword`; a `text` mapping alone does not create it automatically. Values above its `ignore_above` limit are not indexed in that subfield. Consider a bounded `error_type` taxonomy for aggregations instead of arbitrary messages.

`dynamic: false` limits new mapped fields but **does not remove unknown fields from `_source`**. The raw `log` field is stored without a search index. Review duplication, redaction and access to raw data. `translog.durability: request` is a safer baseline than an unexplained async/30s durability tradeoff; neither setting guarantees recovery from every storage or replica failure.

### ISM (Index State Management) Policies

```http
PUT _plugins/_ism/policies/logs-lifecycle
{
  "policy": {
    "description": "Illustrative daily-index hot/warm/cold retention; confirm ownership and late-arrival handling.",
    "schema_version": 1,
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
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
            "warm_migration": {}
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
            "cold_delete": {}
          }
        ],
        "transitions": []
      }
    ],
    "ism_template": [
      {
        "index_patterns": [
          "logs-production-*"
        ],
        "priority": 100
      }
    ]
  }
}
```

This policy attaches to newly created matching indexes. Existing indexes need a deliberate policy-attachment operation; inspect `_plugins/_ism/explain/INDEX` and policy versions before changing them.

Each action object has one action (with its supported retry/timeout metadata). Managed `warm_migration`, `cold_migration` and **`cold_delete`** differ from self-managed ISM operations. Cold indexes require `cold_delete`, and ISM cold migration needs an explicit timestamp field. Do not combine warm migration, replica changes and force merge into one action object.

ISM normally evaluates jobs every 5–8 minutes and does not run them while cluster status is red. Index age is measured from index creation. The example 90-day deletion is an organizational choice, not a universal legal requirement or an exact per-record expiry. Verify late-data behavior, snapshots and recovery before enabling deletion.

### Index Aliases and Rollover

This independent exercise uses the prefix `rollover-logs-*` and a writer alias. It does not change the daily collector configuration.

```http
PUT _index_template/rollover-logs
{
  "index_patterns": [
    "rollover-logs-*"
  ],
  "priority": 100,
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "plugins.index_state_management.rollover_alias": "rollover-logs-write"
    },
    "mappings": {
      "properties": {
        "@timestamp": {
          "type": "date"
        },
        "message": {
          "type": "text"
        }
      }
    }
  }
}

PUT _plugins/_ism/policies/rollover-logs
{
  "policy": {
    "description": "Independent rollover example; not attached to date-based collector indexes.",
    "schema_version": 1,
    "default_state": "write",
    "states": [
      {
        "name": "write",
        "actions": [
          {
            "rollover": {
              "min_index_age": "1d",
              "min_primary_shard_size": "30gb"
            }
          }
        ],
        "transitions": []
      }
    ],
    "ism_template": [
      {
        "index_patterns": [
          "rollover-logs-*"
        ],
        "priority": 100
      }
    ]
  }
}

PUT rollover-logs-000001
{
  "aliases": {
    "rollover-logs-write": {
      "is_write_index": true
    }
  }
}

POST rollover-logs-write/_doc
{
  "@timestamp": "2026-09-13T00:00:00Z",
  "message": "synthetic rollover example"
}

GET _plugins/_ism/explain/rollover-logs-000001

POST rollover-logs-write/_rollover
{
  "conditions": {
    "max_age": "1d",
    "max_size": "90gb"
  }
}
```

Automatic ISM rollover needs the rollover alias setting, a suitable numbered index and the write alias. A daily-date writer will not use that alias merely because an alias exists.

ISM's `min_primary_shard_size: 30gb` concerns a single primary shard. OpenSearch 3.5's rollover REST parser accepts `max_age`, `max_docs` and `max_size`; `max_size` measures **total primary-shard storage**, excluding replicas. The 90GB REST example is therefore not the same condition as a 30GB per-primary-shard threshold. Rollover conditions are alternatives, not a requirement to satisfy every threshold simultaneously.

<span id="direct-ingestion-from-fluentbit-to-opensearch"></span>
<span id="fluentbit-daemonset-using-irsa"></span>

## Data Ingestion

### Direct Ingestion from Fluent Bit

The following six resources form a reference collector configuration for eligible **Linux EC2 nodes**. Fargate uses its platform log router; Windows and other node platforms require their own paths and deployment model. Confirm host paths, admission-policy exceptions and resource needs before deploying a node log reader.

Set the real domain hostname, Region and IRSA role. The role's OIDC trust must match `system:serviceaccount:logging:fluent-bit`; also authorize its IAM/data-plane access and FGAC writer role. Pod Identity is an alternative only with compatible node/agent/SDK support.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: logging
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: fluent-bit
  namespace: logging
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/FluentBitOpenSearchRole
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: fluent-bit-metadata
rules:
- apiGroups:
  - ''
  resources:
  - namespaces
  - pods
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: fluent-bit-metadata
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: fluent-bit-metadata
subjects:
- kind: ServiceAccount
  name: fluent-bit
  namespace: logging
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush          5
        Log_Level      info
        HTTP_Server    Off
        storage.path   /buffers/storage
        storage.sync   normal

    [INPUT]
        Name               tail
        Tag                kube.*
        Path               /var/log/containers/*.log
        Exclude_Path       /var/log/containers/fluent-bit-*_logging_fluent-bit-*.log
        multiline.parser   docker, cri
        DB                 /buffers/tail.db
        Mem_Buf_Limit      50MB
        Skip_Long_Lines    On
        Refresh_Interval   10
        storage.type       filesystem

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       app
        Keep_Log            On
        Labels              Off
        Annotations         Off
        K8S-Logging.Parser  Off
        K8S-Logging.Exclude Off

    [FILTER]
        Name    modify
        Match   kube.*
        Set     cluster_name example-eks
        Set     environment example

    [OUTPUT]
        Name                    opensearch
        Match                   kube.*
        Host                    REPLACE_WITH_DOMAIN_ENDPOINT
        Port                    443
        tls                     On
        tls.verify              On
        AWS_Auth                On
        AWS_Region              ap-northeast-2
        Suppress_Type_Name      On
        Logstash_Format         On
        Logstash_Prefix         logs-production
        Time_Key                @timestamp
        Generate_ID             On
        Retry_Limit             5
        Buffer_Size             5MB
        Compress                gzip
        storage.total_limit_size 1G
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
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
      nodeSelector:
        kubernetes.io/os: linux
      tolerations:
      - operator: Exists
        effect: NoSchedule
      containers:
      - name: fluent-bit
        image: public.ecr.aws/aws-observability/aws-for-fluent-bit:3.4.15@sha256:88e1b56cedb230486afeca6eeb26c5f6bd59c48879d0054d1674d5a58838c607
        args:
        - -c
        - /fluent-bit/custom/fluent-bit.conf
        securityContext:
          runAsUser: 0
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 512Mi
        volumeMounts:
        - name: logs
          mountPath: /var/log
          readOnly: true
        - name: buffers
          mountPath: /buffers
        - name: config
          mountPath: /fluent-bit/custom
          readOnly: true
        - name: tmp
          mountPath: /tmp
        command:
        - /fluent-bit/bin/fluent-bit
      volumes:
      - name: logs
        hostPath:
          path: /var/log
          type: Directory
      - name: buffers
        hostPath:
          path: /var/lib/fluent-bit-opensearch
          type: DirectoryOrCreate
      - name: config
        configMap:
          name: fluent-bit-config
      - name: tmp
        emptyDir: {}
```

The image index is pinned and its Linux amd64/arm64 metadata was checked. This image's default CMD is an entrypoint script; the example explicitly invokes `/fluent-bit/bin/fluent-bit` with the **native OpenSearch output**. It does not load the legacy Go output plugins or test the image at runtime.

Important configuration relationships:

- `multiline.parser docker, cri` handles supported container framing; the Kubernetes filter then merges application JSON under `app`.
- The read-only `/var/log` mount is for log input. The Tail DB and filesystem buffers use a separate writable node path. They survive a Pod restart only while that node/path survives; they are not cross-node durable storage.
- Metadata RBAC is limited to read operations on Pods/namespaces. The agent itself reads node logs, so protect its namespace, role and configuration.
- Application annotations cannot silently override parsing or exclude logs in this example. Collector-generated cluster/environment values are set deliberately. Exclude the collector's own logs from this pipeline to reduce feedback loops.
- `Suppress_Type_Name On` is required for the typeless OpenSearch 2.x/3.x API. `Type _doc` is not a compatible substitute.
- `Logstash_Format On` creates date-based index names and the `@timestamp` field. It does not write to the optional rollover alias.
- Retries, `Generate_ID`, memory buffers and the output's storage cap are not an exactly-once or lossless-delivery guarantee. Test partial bulk errors, oversize lines, restart offsets, the retry limit, disk pressure and late records. The output cap does not cap all node disk usage.

The retained raw log can contain data also present under `app`. Redact prohibited content before storage and monitor rejected records. Do not enable request-body tracing as a permanent diagnostic setting.

<span id="ingestion-via-kinesis-data-firehose"></span>

### Ingestion via Amazon Data Firehose

Data Firehose is an alternative managed delivery path with buffering, retry and backup controls; it is not automatically the cheapest or simplest choice for every workload. Its Terraform resource remains named `aws_kinesis_firehose_delivery_stream`.

This optional resource file uses the domain above and existing approved delivery-role, subnet, security-group and private backup-bucket inputs:

```hcl
variable "firehose_role_arn" {
  type = string
}

variable "firehose_subnet_ids" {
  type = list(string)
}

variable "firehose_security_group_ids" {
  type = list(string)
}

variable "backup_bucket_arn" {
  type = string
}

resource "aws_cloudwatch_log_group" "firehose" {
  name              = "/aws/kinesisfirehose/logs-to-opensearch"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_stream" "firehose" {
  name           = "opensearch-delivery"
  log_group_name = aws_cloudwatch_log_group.firehose.name
}

resource "aws_kinesis_firehose_delivery_stream" "logs" {
  name        = "logs-to-opensearch"
  destination = "opensearch"

  opensearch_configuration {
    domain_arn            = aws_opensearch_domain.logs.arn
    role_arn              = var.firehose_role_arn
    index_name            = "logs-production-firehose"
    index_rotation_period = "OneDay"
    buffering_interval    = 60
    buffering_size        = 5
    retry_duration        = 300
    s3_backup_mode        = "FailedDocumentsOnly"

    vpc_config {
      subnet_ids         = var.firehose_subnet_ids
      security_group_ids = var.firehose_security_group_ids
      role_arn           = var.firehose_role_arn
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = aws_cloudwatch_log_stream.firehose.name
    }

    s3_configuration {
      role_arn           = var.firehose_role_arn
      bucket_arn         = var.backup_bucket_arn
      prefix             = "opensearch-failed/"
      buffering_size     = 10
      buffering_interval = 400
      compression_format = "GZIP"
    }
  }
}
```

The delivery role needs the relevant OpenSearch/FGAC, S3, CloudWatch and VPC/ENI permissions, plus any required KMS permissions; its trust and the deployer's `iam:PassRole` permissions are separate. Include the delivery role in the domain's caller inputs and writer mapping, and permit its VPC connections to port 443.

`FailedDocumentsOnly` chooses the backup mode; naming an S3 prefix `failed/` alone does not do that. Test failures and replay from the private backup bucket. Firehose records need a schema compatible with the index mapping, including timestamps; the service does not automatically create the Kubernetes metadata/application envelope shown here.

<span id="dashboard-access-setup"></span>
<span id="create-index-pattern"></span>
<span id="visualization-creation"></span>

## OpenSearch Dashboards

### Access and Index Patterns

Use approved VPC connectivity and an authentication method compatible with the domain access policy. A plain SSH tunnel does not by itself preserve the original TLS hostname, SSO redirects or SigV4 signing. Do not disable certificate verification to make `https://localhost:9200` appear to work. An ALB is not a complete native domain/Dashboards integration recipe.

After configuring authenticated access, create a data view/index pattern for `logs-production-*` and select `@timestamp`. Menu names vary by the Dashboards version and enabled experience.

### Search Query Examples

```http
GET logs-production-*/_search
{
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "app.level": "error"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "now-1h"
            }
          }
        },
        {
          "term": {
            "kubernetes.namespace_name": "production"
          }
        }
      ]
    }
  },
  "sort": [
    {
      "@timestamp": {
        "order": "desc"
      }
    }
  ],
  "size": 100
}

GET logs-production-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "app.level": "error"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "now-24h"
            }
          }
        }
      ]
    }
  },
  "aggs": {
    "by_namespace": {
      "terms": {
        "field": "kubernetes.namespace_name",
        "size": 20
      },
      "aggs": {
        "by_type": {
          "terms": {
            "field": "app.error_type",
            "size": 10
          }
        }
      }
    }
  }
}

GET logs-production-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        {
          "exists": {
            "field": "app.http.response_time_ms"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "now-1h"
            }
          }
        }
      ]
    }
  },
  "aggs": {
    "response_time_percentiles": {
      "percentiles": {
        "field": "app.http.response_time_ms",
        "percents": [
          50,
          75,
          90,
          95,
          99
        ]
      }
    }
  }
}
```

These examples use filter context for exact keyword/time conditions. The second query really filters errors before aggregating namespaces. Terms aggregation returns a selected top-N set and can have distributed approximation/omitted buckets; it is not a complete count of every namespace. Percentiles are approximate and use the mapped millisecond field.

For visualizations, choose `app.level`, a time histogram on `@timestamp`, or the explicitly mapped `app.message.keyword`/`app.error_type` fields. A field name mentioned in a dashboard does not create its mapping.

<span id="fine-grained-access-control-fgac"></span>
<span id="document-level-security-dls"></span>
<span id="field-level-security-fls"></span>

## Security Configuration

### Fine-Grained Access Control

Network access, the domain resource policy and FGAC are separate layers. The Terraform IAM-principal policy requires SigV4. Neither a security-group rule nor a successful IAM request automatically grants index access.

An administrator can define a writer role for the collector and a namespace-restricted reader:

```http
PUT _plugins/_security/api/roles/logs-writer
{
  "cluster_permissions": [
    "cluster_composite_ops"
  ],
  "index_permissions": [
    {
      "index_patterns": [
        "logs-production-*"
      ],
      "allowed_actions": [
        "create_index",
        "write"
      ]
    }
  ]
}

PUT _plugins/_security/api/rolesmapping/logs-writer
{
  "backend_roles": [
    "arn:aws:iam::123456789012:role/FluentBitOpenSearchRole"
  ]
}

PUT _plugins/_security/api/roles/team-a-logs
{
  "cluster_permissions": [
    "cluster_composite_ops_ro"
  ],
  "index_permissions": [
    {
      "index_patterns": [
        "logs-production-*"
      ],
      "dls": "{\"term\":{\"kubernetes.namespace_name\":\"team-a\"}}",
      "allowed_actions": [
        "read"
      ]
    }
  ]
}

PUT _plugins/_security/api/rolesmapping/team-a-logs
{
  "backend_roles": [
    "arn:aws:iam::123456789012:role/TeamAReaderRole"
  ]
}
```

Replace role ARNs with the approved identities. The writer mapping must also include a Firehose delivery role if that path is used. Do not grant routine readers `cluster_all` or the master role. IAM backend-role mappings and internal/SAML usernames are different identity mechanisms.

### Document-Level Security and Field-Level Security

DLS filters documents by stored fields. In this example, namespace metadata must come from the trusted collector; application-supplied strings are not proof of tenant identity.

For a more restricted reader, the following **combined** role keeps the namespace restriction and includes only selected response fields:

```http
PUT _plugins/_security/api/roles/team-a-limited
{
  "cluster_permissions": [
    "cluster_composite_ops_ro"
  ],
  "index_permissions": [
    {
      "index_patterns": [
        "logs-production-*"
      ],
      "fls": [
        "@timestamp",
        "kubernetes.namespace_name",
        "app.level",
        "app.message"
      ],
      "allowed_actions": [
        "read"
      ],
      "dls": "{\"term\":{\"kubernetes.namespace_name\":\"team-a\"}}"
    }
  ]
}
```

Use the intended role mapping rather than adding a restricted role to an identity that already has broader access. Evaluate the complete set of effective roles. The raw `log` field is intentionally absent from this allowlist because it may duplicate otherwise hidden JSON fields.

FLS controls returned fields, not the contents of an allowed message string. It does not delete information from `_source`, snapshots or log archives. Test search, get, multi-search and aggregation access, and prevent prohibited data from being logged in the first place.

### SAML Authentication Setup

Managed OpenSearch Service SAML is configured through the **AWS domain configuration API**, not by uploading a self-managed `opensearch-security/config.yml`.

The following local helper serializes approved IdP XML without hand-escaping it. Replace the example administrative group and role-attribute key with the IdP configuration you reviewed:

```python
from pathlib import Path
import json
import xml.etree.ElementTree as ET

metadata = Path("idp-metadata.xml").read_text(encoding="utf-8")
root = ET.fromstring(metadata)
if root.tag.rsplit("}", 1)[-1] != "EntityDescriptor" or not root.get("entityID"):
    raise ValueError("Provide approved metadata for one IdP EntityDescriptor")
options = {
    "SAMLOptions": {
        "Enabled": True,
        "Idp": {"EntityId": root.get("entityID"), "MetadataContent": metadata},
        "MasterBackendRole": "opensearch-admin",
        "RolesKey": "Role",
        "SessionTimeoutMinutes": 60,
    }
}
Path("advanced-security-saml.json").write_text(json.dumps(options, indent=2) + "\n")
```

```bash
aws opensearch update-domain-config \
  --domain-name logs-production --region ap-northeast-2 \
  --advanced-security-options file://advanced-security-saml.json
```

This is a payload example, not an end-to-end SSO deployment. Validate metadata trust, entity ID, certificates, ACS/Dashboards URLs and mappings. SAML browser traffic needs a matching domain access-policy design; enabling `SAMLOptions` does not turn that traffic into SigV4 for the IAM-only policy above. Follow one coherent authentication profile and test administrator recovery before changing an existing domain.

<span id="storage-tiering"></span>
<span id="cost-comparison-based-on-100gb-day"></span>
<span id="index-optimization"></span>
<span id="reserved-instances"></span>

## Cost Optimization

### Storage and Index Settings

Price the selected Region, node families/counts, replicas, EBS, warm-node compute/storage, cold storage and data-transfer/ingestion paths. The earlier 100GB/day dollar totals and fixed savings percentages lacked enough assumptions to reproduce; they are not a current budget or measured comparison.

Index compression, refresh interval, shard counts and field mappings trade storage/CPU, search freshness, query capability and recovery cost. Set static options such as `index.codec` in the creation template; do not blindly send static-setting changes to every open production index. Dropping text positions or disabling fields can break queries.

Reserved Instance savings depend on eligible usage, Region, term and payment choice. A one-year horizon alone does not justify a purchase, and a node discount does not make all storage/delivery charges disappear. Use current pricing and measured demand rather than the old fixed 21/24/36% figures.

<span id="inverted-index-inefficiency"></span>
<span id="aggregation-query-performance-degradation"></span>
<span id="scaling-cost-issues"></span>
<span id="clickhouse-migration-decision-criteria"></span>

## Limitations in Large-scale Log Environments

OpenSearch combines inverted indexes with **column-oriented doc values** for many aggregations and sorts. It does not universally reread every full `_source` document for an aggregation. Mapping, selectivity, shards, caches, segment layout and concurrent work affect performance.

The original OpenSearch/ClickHouse latency and compression figures had no reproducible hardware, versions, data or queries. Do not turn them into a universal 100GB migration threshold or an assertion that 90% of all organizations' queries have one pattern.

Compare representative full-text, filter, aggregation and investigative queries on the same data, retention, durability and concurrency requirements. Evaluate ingest/backfill cost, schema evolution, permissions, dashboards, operational skills and rollback. A dual-write experiment needs reconciliation and cost controls; a fixed two-week or two-month schedule is not a guarantee.

<span id="feature-comparison"></span>
<span id="recommendations-by-use-case"></span>
<span id="migration-considerations"></span>

## Comparison with Loki

| Area | OpenSearch | Loki |
|---|---|---|
| Index/query model | Mapped fields, inverted indexes and doc values; Query DSL and supported SQL/PPL features | Stream-label index, chunk scanning and LogQL pipelines/metrics |
| Text search | Analyzers, relevance and full-text query capabilities | Text filtering/search within selected streams and time ranges |
| Access control | Network/IAM/FGAC and configured document/field controls | Authenticating gateway, tenant authorization and policy/operational controls |
| Cost and operations | Depend on the provisioned/managed model and workload | Depend on deployment mode, streams, object storage, caches and queries |
| Migration | Rebuild mappings/queries and validate permissions/data correctness | Redesign labels/metadata/queries and validate permissions/data correctness |

Neither product is automatically the compliance choice, the cheapest choice or operationally simple. Loki still supports text search and derived metrics; a migration changes semantics and capabilities rather than fitting a fixed 3–5× cost or 60–80% savings rule.

## Validation and References

Local checks cover the Terraform resource configuration and published data/configuration contracts. They do not prove live AWS authorization, supported SKU capacity in a Region, collector delivery, ISM transitions/deletion, SAML authentication or query performance. The image index/configuration metadata was inspected without pulling executable layers or running a container.

- [Service/version support](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/what-is.html)
- [Supported instance types](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/supported-instance-types.html) and [Multi-AZ](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-multiaz.html)
- [VPC access](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html), [access policies](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html) and [FGAC](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html)
- [UltraWarm](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ultrawarm.html), [cold storage](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/cold-storage.html), [managed ISM](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ism.html) and [ISM policy reference](https://docs.opensearch.org/latest/im-plugin/ism/policies/)
- [Rollover API](https://docs.opensearch.org/latest/api-reference/index-apis/rollover/) and [doc values](https://docs.opensearch.org/latest/field-types/mapping-parameters/doc-values/)
- [Snapshots](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html), [CloudWatch logs](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/createdomain-configure-slow-logs.html) and [SAML](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/saml.html)
- [AWS for Fluent Bit release history](https://github.com/aws/aws-for-fluent-bit/blob/mainline/CHANGELOG.md) and [OpenSearch output configuration](https://raw.githubusercontent.com/fluent/fluent-bit-docs/master/pipeline/outputs/opensearch.md)
- [Data Firehose destination configuration](https://docs.aws.amazon.com/firehose/latest/dev/create-destination.html)
- [Current service pricing](https://aws.amazon.com/opensearch-service/pricing/)
- [Elastic licensing FAQ](https://www.elastic.co/pricing/faq/licensing)

## Quiz

Test the distinctions in the [OpenSearch quiz](../../quizzes/observability/logging/02-opensearch-quiz.md).
