# Log Collectors Comparison

> **Last Updated**: February 20, 2026

Various tools exist for collecting logs in Kubernetes environments. This document provides an in-depth comparison of FluentBit, Promtail, Grafana Alloy, and OpenTelemetry Collector, explaining configuration methods and optimization strategies for each tool.

## Table of Contents

1. [Overview](#overview)
2. [FluentBit](#fluentbit)
3. [Promtail](#promtail)
4. [Grafana Alloy](#grafana-alloy)
5. [OpenTelemetry Collector](#opentelemetry-collector)
6. [Comparison and Selection Guide](#comparison-and-selection-guide)

---

## Overview

### Log Collector Role

```mermaid
flowchart LR
    subgraph Sources["Log Sources"]
        STDOUT[Container stdout]
        FILE[Log Files]
        JOURNAL[Systemd Journal]
    end

    subgraph Collector["Log Collector"]
        INPUT[Input/Source]
        PROCESS[Processing/Transform]
        OUTPUT[Output/Sink]
    end

    subgraph Destinations["Destinations"]
        LOKI[Loki]
        OS[OpenSearch]
        CW[CloudWatch]
        S3[S3]
    end

    STDOUT --> INPUT
    FILE --> INPUT
    JOURNAL --> INPUT

    INPUT --> PROCESS
    PROCESS --> OUTPUT

    OUTPUT --> LOKI
    OUTPUT --> OS
    OUTPUT --> CW
    OUTPUT --> S3

    classDef source fill:#4CAF50,stroke:#333,color:white
    classDef collector fill:#2196F3,stroke:#333,color:white
    classDef dest fill:#9C27B0,stroke:#333,color:white

    class STDOUT,FILE,JOURNAL source
    class INPUT,PROCESS,OUTPUT collector
    class LOKI,OS,CW,S3 dest
```

### Core Functions

| Function | Description |
|----------|-------------|
| **Input** | Read logs from various sources |
| **Parsing** | Interpret and structure log formats |
| **Filtering** | Remove unnecessary logs |
| **Transform** | Add/modify/delete fields |
| **Buffering** | Temporary storage for reliability |
| **Output** | Send logs to destinations |

---

## FluentBit

### Overview

FluentBit is a CNCF project, a lightweight log processor written in C. It started as a lightweight version of Fluentd but has evolved into an independent project.

```
+---------------------------------------------------------+
|                      FluentBit                           |
+---------------------------------------------------------+
|  Language: C                  Memory: ~10MB             |
|  Performance: 100K+ events/s  Plugins: 100+ built-in    |
|  License: Apache 2.0          CNCF: Graduated           |
+---------------------------------------------------------+
```

### Architecture

```mermaid
flowchart LR
    subgraph Input["Input Plugins"]
        TAIL[tail]
        SYSLOG[syslog]
        TCP[tcp]
        SYSTEMD[systemd]
    end

    subgraph Parser["Parser"]
        JSON[json]
        REGEX[regex]
        DOCKER[docker]
        CRI[cri]
    end

    subgraph Filter["Filter Plugins"]
        K8S[kubernetes]
        MODIFY[modify]
        GREP[grep]
        LUA[lua]
        MULTILINE[multiline]
    end

    subgraph Buffer["Buffer"]
        MEM[Memory]
        FS[Filesystem]
    end

    subgraph Output["Output Plugins"]
        LOKI[loki]
        ES[opensearch]
        CW[cloudwatch_logs]
        S3[s3]
        KAFKA[kafka]
    end

    Input --> Parser
    Parser --> Filter
    Filter --> Buffer
    Buffer --> Output
```

### Complete Configuration Example

```ini
# /fluent-bit/etc/fluent-bit.conf

[SERVICE]
    # Basic settings
    Flush                     5
    Grace                     30
    Daemon                    off
    Log_Level                 info

    # Parser file
    Parsers_File              parsers.conf

    # HTTP server (metrics/healthcheck)
    HTTP_Server               On
    HTTP_Listen               0.0.0.0
    HTTP_Port                 2020

    # Storage (buffering)
    storage.path              /var/log/flb-storage/
    storage.sync              normal
    storage.checksum          off
    storage.backlog.mem_limit 50M
    storage.metrics           on

#---------------------------------------------
# INPUT: Container log collection
#---------------------------------------------
[INPUT]
    Name                      tail
    Tag                       kube.*
    Path                      /var/log/containers/*.log
    # Exclude kube-system
    Exclude_Path              /var/log/containers/*_kube-system_*.log,/var/log/containers/*_kube-public_*.log
    # Parser
    multiline.parser          docker, cri
    # State DB
    DB                        /var/log/flb_kube.db
    DB.locking                true
    # Memory limit
    Mem_Buf_Limit             50MB
    # Skip long lines
    Skip_Long_Lines           On
    # Refresh interval
    Refresh_Interval          10
    # Rotation wait
    Rotate_Wait               30
    # Filesystem buffer
    storage.type              filesystem
    # Handle existing files
    Read_from_Head            Off

#---------------------------------------------
# INPUT: System logs
#---------------------------------------------
[INPUT]
    Name                      systemd
    Tag                       host.systemd
    Systemd_Filter            _SYSTEMD_UNIT=kubelet.service
    Systemd_Filter            _SYSTEMD_UNIT=containerd.service
    Systemd_Filter            _SYSTEMD_UNIT=docker.service
    DB                        /var/log/flb_systemd.db
    Read_From_Tail            On
    Strip_Underscores         On

#---------------------------------------------
# FILTER: Add Kubernetes metadata
#---------------------------------------------
[FILTER]
    Name                      kubernetes
    Match                     kube.*
    # API server settings
    Kube_URL                  https://kubernetes.default.svc:443
    Kube_CA_File              /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File           /var/run/secrets/kubernetes.io/serviceaccount/token
    Kube_Tag_Prefix           kube.var.log.containers.
    # Log merge
    Merge_Log                 On
    Merge_Log_Key             log_processed
    # Auto-detect parser
    K8S-Logging.Parser        On
    K8S-Logging.Exclude       Off
    # Use Kubelet (reduce API server load)
    Use_Kubelet               On
    Kubelet_Port              10250
    # Labels/Annotations
    Labels                    On
    Annotations               Off
    # Buffer
    Buffer_Size               0

#---------------------------------------------
# FILTER: Add/modify fields
#---------------------------------------------
[FILTER]
    Name                      modify
    Match                     *
    # Add cluster info
    Add                       cluster_name eks-production
    Add                       environment production
    Add                       region ap-northeast-2
    # Remove unnecessary fields
    Remove                    stream
    Remove                    _p

#---------------------------------------------
# FILTER: Remove noise
#---------------------------------------------
[FILTER]
    Name                      grep
    Match                     kube.*
    # Exclude health check logs
    Exclude                   log healthcheck
    Exclude                   log readiness
    Exclude                   log liveness
    Exclude                   log health
    Exclude                   log /health
    Exclude                   log /ready
    Exclude                   log /live

#---------------------------------------------
# FILTER: Extract log level (for non-JSON)
#---------------------------------------------
[FILTER]
    Name                      parser
    Match                     kube.*
    Key_Name                  log
    Parser                    extract_level
    Reserve_Data              True
    Preserve_Key              True

#---------------------------------------------
# FILTER: Multiline handling
#---------------------------------------------
[FILTER]
    Name                      multiline
    Match                     kube.*
    multiline.key_content     log
    multiline.parser          java_multiline, python_multiline, go_multiline

#---------------------------------------------
# FILTER: Lua script (advanced processing)
#---------------------------------------------
[FILTER]
    Name                      lua
    Match                     kube.*
    script                    /fluent-bit/scripts/process.lua
    call                      process_log

#---------------------------------------------
# OUTPUT: Loki
#---------------------------------------------
[OUTPUT]
    Name                      loki
    Match                     kube.*
    Host                      loki-gateway.loki.svc.cluster.local
    Port                      80
    Labels                    job=fluentbit, namespace=$kubernetes['namespace_name'], app=$kubernetes['labels']['app'], pod=$kubernetes['pod_name']
    # Batch settings
    BatchWait                 1
    BatchSize                 1048576
    # Line format
    LineFormat                json
    # Auto label extraction
    AutoKubernetesLabels      off
    # Retry
    Retry_Limit               5
    # Tenant (multi-tenancy)
    TenantID                  default

#---------------------------------------------
# OUTPUT: CloudWatch Logs
#---------------------------------------------
[OUTPUT]
    Name                      cloudwatch_logs
    Match                     kube.*
    region                    ap-northeast-2
    log_group_name            /aws/containerinsights/${CLUSTER_NAME}/application
    log_stream_prefix         ${HOST_NAME}-
    auto_create_group         true
    log_retention_days        30
    # Compression
    compress                  gzip
    # Retry
    retry_limit               5

#---------------------------------------------
# OUTPUT: S3 (backup/archive)
#---------------------------------------------
[OUTPUT]
    Name                      s3
    Match                     kube.*
    region                    ap-northeast-2
    bucket                    my-logs-backup
    total_file_size           100M
    upload_timeout            10m
    s3_key_format             /logs/$TAG/%Y/%m/%d/%H/%M/%S
    compression               gzip
    content_type              application/gzip
```

### Parser Configuration

```ini
# /fluent-bit/etc/parsers.conf

[PARSER]
    Name        docker
    Format      json
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%L
    Time_Keep   On

[PARSER]
    Name        cri
    Format      regex
    Regex       ^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%L%z
    Time_Keep   On

[PARSER]
    Name        json
    Format      json
    Time_Key    timestamp
    Time_Format %Y-%m-%dT%H:%M:%S.%LZ

[PARSER]
    Name        extract_level
    Format      regex
    Regex       (?<level>(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL))

[PARSER]
    Name        nginx
    Format      regex
    Regex       ^(?<remote>[^ ]*) (?<host>[^ ]*) (?<user>[^ ]*) \[(?<time>[^\]]*)\] "(?<method>\S+)(?: +(?<path>[^\"]*?)(?: +\S*)?)?" (?<code>[^ ]*) (?<size>[^ ]*)(?: "(?<referer>[^\"]*)" "(?<agent>[^\"]*)")
    Time_Key    time
    Time_Format %d/%b/%Y:%H:%M:%S %z

[MULTILINE_PARSER]
    Name          java_multiline
    Type          regex
    Flush_timeout 1000
    Rule          "start_state"  "/^\d{4}-\d{2}-\d{2}|^\[?\d{4}[-\/]\d{2}[-\/]\d{2}/"  "cont"
    Rule          "cont"         "/^[\s\t]+|^Caused by:|^[\w\.]+(Exception|Error)/"    "cont"

[MULTILINE_PARSER]
    Name          python_multiline
    Type          regex
    Flush_timeout 1000
    Rule          "start_state"  "/^Traceback|^\d{4}-\d{2}-\d{2}/"  "cont"
    Rule          "cont"         "/^\s+|^[A-Za-z]+Error:/"          "cont"

[MULTILINE_PARSER]
    Name          go_multiline
    Type          regex
    Flush_timeout 1000
    Rule          "start_state"  "/^panic:|^goroutine \d+/"  "cont"
    Rule          "cont"         "/^\s+/"                    "cont"
```

### Lua Script Example

```lua
-- /fluent-bit/scripts/process.lua

function process_log(tag, timestamp, record)
    -- Normalize log level
    if record["level"] then
        record["level"] = string.upper(record["level"])
    elseif record["log"] then
        if string.match(record["log"], "ERROR") then
            record["level"] = "ERROR"
        elseif string.match(record["log"], "WARN") then
            record["level"] = "WARN"
        elseif string.match(record["log"], "DEBUG") then
            record["level"] = "DEBUG"
        else
            record["level"] = "INFO"
        end
    end

    -- Mask sensitive information
    if record["log"] then
        record["log"] = string.gsub(record["log"], "password[=:][^%s]+", "password=***")
        record["log"] = string.gsub(record["log"], "api[_-]?key[=:][^%s]+", "api_key=***")
        record["log"] = string.gsub(record["log"], "token[=:][^%s]+", "token=***")
    end

    -- Limit message length
    if record["log"] and string.len(record["log"]) > 10000 then
        record["log"] = string.sub(record["log"], 1, 10000) .. "...[TRUNCATED]"
    end

    return 1, timestamp, record
end
```

### DaemonSet Deployment

```yaml
# fluent-bit-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
  labels:
    app.kubernetes.io/name: fluent-bit
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: fluent-bit
  template:
    metadata:
      labels:
        app.kubernetes.io/name: fluent-bit
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "2020"
        prometheus.io/path: "/api/v1/metrics/prometheus"
    spec:
      serviceAccountName: fluent-bit
      priorityClassName: system-node-critical
      tolerations:
        - operator: Exists
      containers:
        - name: fluent-bit
          image: public.ecr.aws/aws-observability/aws-for-fluent-bit:2.31.12
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 2020
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 30
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          env:
            - name: HOST_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            - name: CLUSTER_NAME
              value: "eks-production"
          volumeMounts:
            - name: varlog
              mountPath: /var/log
              readOnly: true
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
              readOnly: true
            - name: fluent-bit-config
              mountPath: /fluent-bit/etc/
            - name: fluent-bit-scripts
              mountPath: /fluent-bit/scripts/
            - name: flb-storage
              mountPath: /var/log/flb-storage/
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
        - name: fluent-bit-scripts
          configMap:
            name: fluent-bit-scripts
        - name: flb-storage
          hostPath:
            path: /var/log/flb-storage
            type: DirectoryOrCreate
```

---

## Promtail

### Overview

Promtail is a log collection agent developed by Grafana Labs specifically for Loki. It's optimized for use with Loki.

```
+---------------------------------------------------------+
|                       Promtail                           |
+---------------------------------------------------------+
|  Language: Go                  Memory: ~50MB            |
|  Destination: Loki only        K8s integration: Native  |
|  License: AGPL-3.0             Developer: Grafana Labs  |
+---------------------------------------------------------+
```

### Architecture

```mermaid
flowchart LR
    subgraph Discovery["Service Discovery"]
        K8S_SD[kubernetes_sd]
        FILE_SD[file_sd]
        STATIC[static]
    end

    subgraph Scrape["Scrape Targets"]
        PODS[Pod Logs]
        JOURNAL[Journal]
        SYSLOG[Syslog]
    end

    subgraph Pipeline["Pipeline Stages"]
        DOCKER[docker]
        CRI[cri]
        JSON[json]
        REGEX[regex]
        MULTILINE[multiline]
        LABELS[labels]
        TIMESTAMP[timestamp]
        OUTPUT[output]
    end

    subgraph Push["Push to Loki"]
        LOKI[Loki API]
    end

    Discovery --> Scrape
    Scrape --> Pipeline
    Pipeline --> Push
```

### Complete Configuration Example

```yaml
# promtail-config.yaml
server:
  http_listen_port: 3101
  grpc_listen_port: 0
  log_level: info

# Position file (offset tracking)
positions:
  filename: /tmp/positions.yaml
  sync_period: 10s
  ignore_invalid_yaml: true

# Loki client settings
clients:
  - url: http://loki-gateway.loki.svc.cluster.local/loki/api/v1/push
    tenant_id: default
    batchwait: 1s
    batchsize: 1048576
    timeout: 10s
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10
    # External labels (added to all logs)
    external_labels:
      cluster: eks-production
      environment: production

# Scrape configs
scrape_configs:
  #-----------------------------------------
  # Kubernetes pod logs
  #-----------------------------------------
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: []  # All namespaces

    # Label rewriting
    relabel_configs:
      # Namespace
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace

      # Pod name
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod

      # Container name
      - source_labels: [__meta_kubernetes_pod_container_name]
        target_label: container

      # App label
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app

      # App name (app.kubernetes.io/name)
      - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_name]
        target_label: app
        regex: (.+)

      # Component
      - source_labels: [__meta_kubernetes_pod_label_component]
        target_label: component

      # Node name
      - source_labels: [__meta_kubernetes_pod_node_name]
        target_label: node

      # Set log file path
      - source_labels: [__meta_kubernetes_pod_uid, __meta_kubernetes_pod_container_name]
        target_label: __path__
        separator: /
        replacement: /var/log/pods/*$1/*.log

      # Exclude kube-system namespace
      - source_labels: [__meta_kubernetes_namespace]
        action: drop
        regex: kube-system|kube-public

      # Exclude by specific annotation
      - source_labels: [__meta_kubernetes_pod_annotation_promtail_io_scrape]
        action: drop
        regex: "false"

    # Pipeline stages
    pipeline_stages:
      # Docker/CRI log parsing
      - cri: {}

      # JSON parsing (if possible)
      - json:
          expressions:
            level: level
            message: message
            timestamp: timestamp
            trace_id: trace_id

      # Extract labels
      - labels:
          level:

      # Set timestamp
      - timestamp:
          source: timestamp
          format: RFC3339Nano
          fallback_formats:
            - RFC3339
            - "2006-01-02T15:04:05.999999999Z07:00"

      # Normalize log level
      - template:
          source: level
          template: '{{ ToUpper .Value }}'

      # Output settings
      - output:
          source: message

  #-----------------------------------------
  # System journal logs
  #-----------------------------------------
  - job_name: journal
    journal:
      max_age: 12h
      path: /var/log/journal
      labels:
        job: systemd-journal
    relabel_configs:
      - source_labels: [__journal__systemd_unit]
        target_label: unit
      - source_labels: [__journal__hostname]
        target_label: hostname
    pipeline_stages:
      - labels:
          unit:
          hostname:

  #-----------------------------------------
  # Audit logs (special handling)
  #-----------------------------------------
  - job_name: audit-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: audit
          __path__: /var/log/audit/audit.log
    pipeline_stages:
      - regex:
          expression: 'type=(?P<type>\w+).*msg=audit\((?P<timestamp>\d+\.\d+):(?P<id>\d+)\)'
      - labels:
          type:
      - timestamp:
          source: timestamp
          format: Unix

# Resource limits
limits_config:
  readline_rate: 100
  readline_burst: 1000
  readline_rate_enabled: true
  max_streams: 10000
```

### DaemonSet Deployment

```yaml
# promtail-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: promtail
  namespace: loki
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: promtail
  template:
    metadata:
      labels:
        app.kubernetes.io/name: promtail
    spec:
      serviceAccountName: promtail
      tolerations:
        - operator: Exists
      containers:
        - name: promtail
          image: grafana/promtail:2.9.4
          args:
            - -config.file=/etc/promtail/promtail.yaml
            - -config.expand-env=true
          ports:
            - name: http-metrics
              containerPort: 3101
              protocol: TCP
          env:
            - name: HOSTNAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
            readOnlyRootFilesystem: true
          volumeMounts:
            - name: config
              mountPath: /etc/promtail
            - name: run
              mountPath: /run/promtail
            - name: containers
              mountPath: /var/lib/docker/containers
              readOnly: true
            - name: pods
              mountPath: /var/log/pods
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: promtail-config
        - name: run
          hostPath:
            path: /run/promtail
        - name: containers
          hostPath:
            path: /var/lib/docker/containers
        - name: pods
          hostPath:
            path: /var/log/pods
```

---

## Grafana Alloy

### Overview

Grafana Alloy is the successor to Grafana Agent, based on the OpenTelemetry Collector distribution. It uses the River configuration language for more flexible configuration.

```
+---------------------------------------------------------+
|                     Grafana Alloy                        |
+---------------------------------------------------------+
|  Language: Go                  Based on: OTEL Collector |
|  Config: River (HCL-like)      Destinations: Multiple   |
|  License: Apache 2.0           Developer: Grafana Labs  |
+---------------------------------------------------------+
```

### River Configuration

```river
// alloy-config.river

// Logging settings
logging {
  level  = "info"
  format = "logfmt"
}

//--------------------------------------------
// Local file source
//--------------------------------------------
local.file_match "pods" {
  path_targets = [{
    __address__ = "localhost",
    __path__    = "/var/log/pods/*/*/*.log",
    job         = "kubernetes-pods",
  }]
}

//--------------------------------------------
// Loki source (file reading)
//--------------------------------------------
loki.source.file "pods" {
  targets    = local.file_match.pods.targets
  forward_to = [loki.process.pods.receiver]

  tail_from_end = true
}

//--------------------------------------------
// Kubernetes discovery
//--------------------------------------------
discovery.kubernetes "pods" {
  role = "pod"
}

//--------------------------------------------
// Label rewriting
//--------------------------------------------
discovery.relabel "pods" {
  targets = discovery.kubernetes.pods.targets

  // Namespace
  rule {
    source_labels = ["__meta_kubernetes_namespace"]
    target_label  = "namespace"
  }

  // Pod name
  rule {
    source_labels = ["__meta_kubernetes_pod_name"]
    target_label  = "pod"
  }

  // Container name
  rule {
    source_labels = ["__meta_kubernetes_pod_container_name"]
    target_label  = "container"
  }

  // App label
  rule {
    source_labels = ["__meta_kubernetes_pod_label_app"]
    target_label  = "app"
  }

  // Exclude kube-system
  rule {
    source_labels = ["__meta_kubernetes_namespace"]
    regex         = "kube-system"
    action        = "drop"
  }

  // Set log path
  rule {
    source_labels = ["__meta_kubernetes_pod_uid", "__meta_kubernetes_pod_container_name"]
    separator     = "/"
    target_label  = "__path__"
    replacement   = "/var/log/pods/*$1/*.log"
  }
}

//--------------------------------------------
// Loki source (Kubernetes)
//--------------------------------------------
loki.source.kubernetes "pods" {
  targets    = discovery.relabel.pods.output
  forward_to = [loki.process.pods.receiver]
}

//--------------------------------------------
// Log processing pipeline
//--------------------------------------------
loki.process "pods" {
  forward_to = [loki.write.default.receiver]

  // CRI parsing
  stage.cri {}

  // Attempt JSON parsing
  stage.json {
    expressions = {
      level     = "level",
      message   = "message",
      timestamp = "timestamp",
      trace_id  = "trace_id",
    }
    drop_malformed = true
  }

  // Extract labels
  stage.labels {
    values = {
      level = null,
    }
  }

  // Normalize level
  stage.template {
    source   = "level"
    template = "{{ ToUpper .Value }}"
  }

  // Set timestamp
  stage.timestamp {
    source = "timestamp"
    format = "RFC3339Nano"
    fallback_formats = [
      "RFC3339",
      "2006-01-02T15:04:05.999999999Z07:00",
    ]
  }

  // Noise filtering
  stage.drop {
    expression = "healthcheck|readiness|liveness"
    drop_counter_reason = "health_check"
  }

  // Output settings
  stage.output {
    source = "message"
  }
}

//--------------------------------------------
// Loki output
//--------------------------------------------
loki.write "default" {
  endpoint {
    url = "http://loki-gateway.loki.svc.cluster.local/loki/api/v1/push"

    tenant_id = "default"

    basic_auth {
      username = env("LOKI_USERNAME")
      password = env("LOKI_PASSWORD")
    }
  }

  external_labels = {
    cluster     = "eks-production",
    environment = "production",
  }
}

//--------------------------------------------
// Metrics export
//--------------------------------------------
prometheus.exporter.self "alloy" {}

prometheus.scrape "alloy" {
  targets    = prometheus.exporter.self.alloy.targets
  forward_to = [prometheus.remote_write.default.receiver]
}

prometheus.remote_write "default" {
  endpoint {
    url = "http://prometheus.monitoring.svc.cluster.local/api/v1/write"
  }
}
```

---

## OpenTelemetry Collector

### Overview

OpenTelemetry Collector is a vendor-neutral telemetry data collection, processing, and export pipeline.

```
+---------------------------------------------------------+
|               OpenTelemetry Collector                    |
+---------------------------------------------------------+
|  Language: Go                  Destinations: Multiple   |
|  Signals: Logs, Metrics, Traces                         |
|  License: Apache 2.0           CNCF: Incubating         |
+---------------------------------------------------------+
```

### Architecture

```mermaid
flowchart LR
    subgraph Receivers["Receivers"]
        OTLP[otlp]
        FILELOG[filelog]
        K8SEVENTS[k8sevents]
        SYSLOG[syslog]
    end

    subgraph Processors["Processors"]
        BATCH[batch]
        MEMORY[memory_limiter]
        K8SATTR[k8sattributes]
        FILTER[filter]
        TRANSFORM[transform]
    end

    subgraph Exporters["Exporters"]
        LOKI_EXP[loki]
        OTLP_EXP[otlphttp]
        DEBUG[debug]
    end

    Receivers --> Processors
    Processors --> Exporters
```

### Complete Configuration Example

```yaml
# otel-collector-config.yaml
receivers:
  #-----------------------------------------
  # OTLP receiver (gRPC/HTTP)
  #-----------------------------------------
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  #-----------------------------------------
  # File log receiver
  #-----------------------------------------
  filelog:
    include:
      - /var/log/pods/*/*/*.log
    exclude:
      - /var/log/pods/*/otel-collector/*.log
    start_at: end
    include_file_path: true
    include_file_name: false
    operators:
      # CRI log parsing
      - type: router
        id: get-format
        routes:
          - output: parser-docker
            expr: 'body matches "^\\{"'
          - output: parser-cri
            expr: 'body matches "^[^ Z]+ "'
          - output: parser-containerd
            expr: 'body matches "^[^ Z]+Z"'

      - type: json_parser
        id: parser-docker
        output: extract-metadata

      - type: regex_parser
        id: parser-cri
        regex: '^(?P<time>[^ Z]+) (?P<stream>stdout|stderr) (?P<logtag>[^ ]*) ?(?P<log>.*)$'
        output: extract-metadata
        timestamp:
          parse_from: attributes.time
          layout_type: gotime
          layout: '2006-01-02T15:04:05.999999999Z07:00'

      - type: regex_parser
        id: parser-containerd
        regex: '^(?P<time>[^ ^Z]+Z) (?P<stream>stdout|stderr) (?P<logtag>[^ ]*) ?(?P<log>.*)$'
        output: extract-metadata
        timestamp:
          parse_from: attributes.time
          layout: '%Y-%m-%dT%H:%M:%S.%LZ'

      # Extract metadata from file path
      - type: regex_parser
        id: extract-metadata
        regex: '^.*\/(?P<namespace>[^_]+)_(?P<pod_name>[^_]+)_(?P<uid>[a-f0-9\-]+)\/(?P<container_name>[^\._]+)\/(?P<restart_count>\d+)\.log$'
        parse_from: attributes["log.file.path"]
        cache:
          size: 128

      # Move body
      - type: move
        from: attributes.log
        to: body

      # Stream attribute
      - type: move
        from: attributes.stream
        to: attributes["log.iostream"]

  #-----------------------------------------
  # Kubernetes events receiver
  #-----------------------------------------
  k8s_events:
    auth_type: serviceAccount
    namespaces: [default, production, staging]

processors:
  #-----------------------------------------
  # Memory limiter
  #-----------------------------------------
  memory_limiter:
    check_interval: 1s
    limit_mib: 400
    spike_limit_mib: 100

  #-----------------------------------------
  # Batch processing
  #-----------------------------------------
  batch:
    send_batch_size: 10000
    send_batch_max_size: 11000
    timeout: 5s

  #-----------------------------------------
  # Kubernetes attributes
  #-----------------------------------------
  k8sattributes:
    auth_type: serviceAccount
    passthrough: false
    extract:
      metadata:
        - k8s.namespace.name
        - k8s.pod.name
        - k8s.pod.uid
        - k8s.deployment.name
        - k8s.node.name
        - k8s.container.name
      labels:
        - tag_name: app
          key: app
          from: pod
        - tag_name: component
          key: component
          from: pod
    pod_association:
      - sources:
          - from: resource_attribute
            name: k8s.pod.uid

  #-----------------------------------------
  # Resource addition
  #-----------------------------------------
  resource:
    attributes:
      - key: cluster
        value: eks-production
        action: insert
      - key: environment
        value: production
        action: insert

  #-----------------------------------------
  # Filtering
  #-----------------------------------------
  filter:
    logs:
      exclude:
        match_type: regexp
        bodies:
          - "healthcheck"
          - "readiness"
          - "liveness"
        resource_attributes:
          - key: k8s.namespace.name
            value: "kube-system"

  #-----------------------------------------
  # Transform
  #-----------------------------------------
  transform:
    log_statements:
      - context: log
        statements:
          # Extract log level
          - set(severity_text, "INFO") where severity_text == ""
          - set(severity_text, ConvertCase(severity_text, "upper"))

          # Attempt JSON parsing
          - merge_maps(cache, ParseJSON(body), "insert") where IsMatch(body, "^\\{")
          - set(body, cache["message"]) where cache["message"] != nil
          - set(attributes["level"], cache["level"]) where cache["level"] != nil

exporters:
  #-----------------------------------------
  # Loki output
  #-----------------------------------------
  loki:
    endpoint: http://loki-gateway.loki.svc.cluster.local/loki/api/v1/push
    tenant_id: default
    labels:
      attributes:
        k8s.namespace.name: namespace
        k8s.pod.name: pod
        k8s.container.name: container
        app: app
        level: level
      resource:
        cluster: cluster
        environment: environment

  #-----------------------------------------
  # OTLP HTTP output (to other systems)
  #-----------------------------------------
  otlphttp:
    endpoint: http://other-collector:4318
    tls:
      insecure: true

  #-----------------------------------------
  # Debug output
  #-----------------------------------------
  debug:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

service:
  telemetry:
    logs:
      level: info
    metrics:
      address: 0.0.0.0:8888

  pipelines:
    logs:
      receivers: [filelog, otlp, k8s_events]
      processors: [memory_limiter, k8sattributes, resource, filter, transform, batch]
      exporters: [loki]

    logs/debug:
      receivers: [filelog]
      processors: [memory_limiter]
      exporters: [debug]
```

---

## Comparison and Selection Guide

### Feature Comparison Table

| Feature | FluentBit | Promtail | Grafana Alloy | OTEL Collector |
|---------|-----------|----------|---------------|----------------|
| **Memory usage** | ~10-50MB | ~50-100MB | ~50-100MB | ~50-100MB |
| **CPU usage** | Low | Medium | Medium | Medium |
| **Config language** | INI | YAML | River (HCL) | YAML |
| **Kubernetes integration** | Excellent | Excellent | Excellent | Excellent |
| **Multiline handling** | Excellent | Excellent | Excellent | Good |
| **JSON parsing** | Excellent | Excellent | Excellent | Excellent |
| **Lua scripting** | Supported | Not supported | Not supported | Not supported |
| **WASM plugins** | Supported | Not supported | Not supported | Not supported |
| **Loki support** | Excellent | Native | Native | Good |
| **OpenSearch support** | Native | Not supported | Not supported | Good |
| **CloudWatch support** | Native | Not supported | Not supported | Good |
| **Metrics collection** | Supported | Limited | Excellent | Excellent |
| **Traces collection** | Not supported | Not supported | Excellent | Native |
| **Buffering** | Memory/File | Memory | Memory | Memory |

### Recommendations by Use Case

```
FluentBit recommended:
+-- AWS environments (CloudWatch, OpenSearch)
+-- Multiple destinations needed
+-- Minimal resource usage required
+-- Complex processing with Lua scripts
+-- Legacy system integration

Promtail recommended:
+-- Loki-only environments
+-- Simple configuration
+-- Grafana stack standardization
+-- Quick start

Grafana Alloy recommended:
+-- Grafana integrated environments (Loki + Prometheus + Tempo)
+-- New projects (Promtail replacement)
+-- River config language preference
+-- Metrics + Logs + Traces integration

OTEL Collector recommended:
+-- Multi-vendor environments
+-- Standardized telemetry pipeline
+-- Existing OTEL instrumented code
+-- Trace-centric environments
```

### Decision Flow

```mermaid
flowchart TD
    START[Choose Log Collector] --> Q1{Loki-only<br/>destination?}

    Q1 -->|Yes| Q2{Existing<br/>Promtail?}
    Q1 -->|No| Q3{AWS<br/>environment?}

    Q2 -->|Yes| PROMTAIL[Keep Promtail]
    Q2 -->|No| ALLOY[Grafana Alloy]

    Q3 -->|Yes| FLUENTBIT[FluentBit]
    Q3 -->|No| Q4{Need OTEL<br/>standard?}

    Q4 -->|Yes| OTEL[OTEL Collector]
    Q4 -->|No| FLUENTBIT

    classDef decision fill:#FFE082,stroke:#333
    classDef solution fill:#81C784,stroke:#333,color:white

    class Q1,Q2,Q3,Q4 decision
    class PROMTAIL,ALLOY,FLUENTBIT,OTEL solution
```

---

## Quiz

Test your knowledge with the [Log Collectors Quiz](../../quizzes/observability/logging/05-collectors-quiz.md).
