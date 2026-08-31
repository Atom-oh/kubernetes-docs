# Security and Visibility

> **Supported Versions**: Cilium 1.18
> **Last Updated**: February 22, 2026

## Lab Environment Setup

To follow along with the examples in this document, you need the following tools and environment:

### Required Tools
- kubectl v1.31 or higher
- A working Kubernetes cluster (EKS, minikube, kind, etc.)
- Cilium CLI
- Hubble CLI

### Hubble Installation and Setup

```bash
# Enable Hubble
cilium hubble enable --ui

# Install Hubble CLI
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Set up Hubble port forwarding
cilium hubble port-forward &

# Verify Hubble connection
hubble status
```

## Cilium's Security Features

Cilium leverages eBPF to provide powerful security features for containerized environments. These features provide comprehensive security from network layer to application layer.

### Cilium Security Architecture

![Traffic flows down through Cilium's four defense-in-depth security layers — Network Security, Application Security, Threat Detection, and Runtime Security — with Hubble's eBPF-native observability in the Threat Detection layer highlighted as the visibility foundation underlying the others.](../../../assets/diagrams/rendered/en-networking-cilium-06-security-visibility-0.svg)

### Network Security Features:

1. **Microsegmentation**:
   - Prevents lateral movement with granular network policies
   - Applies least privilege principle
   - Restricts inter-service communication

2. **Encryption**:
   - Inter-node IPsec or WireGuard encryption
   - Data protection in transit
   - Transparent encryption implementation

3. **Threat Detection**:
   - Detection of abnormal network activity
   - Identification of known attack patterns
   - Real-time alerts and response

4. **DNS Security**:
   - DNS-based network policies
   - Malicious domain blocking
   - DNS request monitoring

### Application Security Features:

1. **API-aware Security**:
   - HTTP method, path, header-based filtering
   - gRPC method and metadata-based filtering
   - Kafka topic and operation-based filtering

2. **Identity-based Security**:
   - Service identity-based policies
   - Mutual TLS (mTLS) integration
   - SPIFFE/SPIRE integration

3. **Runtime Security**:
   - Process and system call monitoring
   - Container escape detection
   - Privilege escalation prevention

### Security Policy Example:

```yaml
# comprehensive-security-policy.yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "comprehensive-security"
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/data"
  egress:
  - toEndpoints:
    - matchLabels:
        app: database
    toPorts:
    - ports:
      - port: "3306"
        protocol: TCP
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

## Network Visibility with Hubble

> **Key Concept**: Hubble is Cilium's observability layer that leverages eBPF to monitor and analyze network flows in real-time.

Hubble is Cilium's observability layer that leverages eBPF to monitor and analyze network flows in real-time. It can be used for various purposes including network troubleshooting, security monitoring, and performance analysis.

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "comprehensive-security"
spec:
  endpointSelector:
    matchLabels:
      app: secure-app
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: authorized-client
        io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: "8443"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/secure"
          headers:
          - "Authorization: Bearer [a-zA-Z0-9\\.]*"
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
  - toFQDNs:
    - matchName: "api.internal.secure"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
  - toCIDR:
    - 10.0.0.0/8
    toPorts:
    - ports:
      - port: "5432"
        protocol: TCP
```

### Encryption Configuration:

```yaml
# encryption-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  # Enable IPsec encryption
  enable-ipsec: "true"
  ipsec-key-file: /etc/ipsec/keys

  # Or enable WireGuard encryption
  enable-wireguard: "true"

  # Encryption node selection
  encrypt-node: "true"

  # Encryption interface
  encrypt-interface: "eth0"
```

## Network Visibility and Monitoring

Cilium provides comprehensive network visibility and monitoring capabilities in containerized environments through Hubble. This enables real-time observation and troubleshooting of network flows.

### Hubble Architecture:

```
+-------------------+        +-------------------+
| Hubble UI         |        | Grafana           |
+--------+----------+        +--------+----------+
         |                            |
         v                            v
+-------------------+        +-------------------+
| Hubble Relay      |        | Prometheus        |
+--------+----------+        +--------+----------+
         |                            |
         v                            v
+-------------------+        +-------------------+
| Hubble            |<-------| Cilium            |
+-------------------+        +-------------------+
         |                            |
         v                            v
+-------------------+        +-------------------+
| eBPF Maps         |        | Kernel            |
+-------------------+        +-------------------+
```

### Hubble Components:

1. **Hubble Server**:
   - Integrated with Cilium agent
   - Collects network flow data from eBPF maps
   - Provides local API endpoint

2. **Hubble Relay**:
   - Aggregates data from multiple Hubble servers
   - Provides cluster-wide visibility
   - Provides gRPC API endpoint

3. **Hubble UI**:
   - Network flow visualization
   - Service dependency maps
   - Interactive query interface

4. **Hubble CLI**:
   - Command-line interface
   - Network flow querying and filtering
   - Troubleshooting tool

### Hubble Installation:

```bash
# Enable Hubble
cilium hubble enable --ui

# Check Hubble status
cilium hubble status

# Hubble UI port forwarding
cilium hubble ui

# Install Hubble CLI
curl -L --remote-name-all https://github.com/cilium/hubble/releases/latest/download/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
```

### Hubble CLI Usage Examples:

```bash
# Observe all network flows
hubble observe

# Filter flows for a specific namespace
hubble observe --namespace default

# Filter HTTP requests
hubble observe --protocol http

# Filter dropped packets
hubble observe --verdict DROPPED

# Filter communication between specific pods
hubble observe --pod app1/pod-1 --to-pod app2/pod-2

# Filter traffic to a specific service
hubble observe --to-service kube-system/kube-dns

# Output in JSON format
hubble observe -o json
```

## Hubble Architecture and Usage

Hubble is Cilium's eBPF-based observability layer that provides deep visibility into container networks. Hubble provides real-time information about network flows, application protocols, security events, and more.

### Hubble Data Flow:

1. **Data Collection**:
   - eBPF programs capture network events
   - Extract packet metadata
   - Collect connection tracking information

2. **Data Processing**:
   - Generate flow records
   - L7 protocol parsing
   - Metric aggregation

3. **Data Storage**:
   - Temporary storage in ring buffer
   - Optional persistent storage support
   - Metric export

4. **Data Query**:
   - Real-time flow observation
   - Filtering and aggregation
   - Visualization and analysis

### Hubble Metrics:

Hubble collects various metrics to monitor network performance and security status:

- **TCP/IP Metrics**: Connection count, retransmissions, RTT
- **HTTP Metrics**: Request count, response codes, latency
- **DNS Metrics**: Query count, response codes, latency
- **Security Metrics**: Policy decisions, dropped packets, security events
- **Service Metrics**: Inter-service communication, load balancing decisions

### Prometheus Integration:

Hubble integrates with Prometheus to collect and monitor network metrics:

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'cilium-hubble'
        static_configs:
          - targets: ['hubble-metrics.cilium.io:9091']
        metrics_path: '/metrics'
```

### Grafana Dashboards:

Hubble integrates with Grafana to visualize network metrics:

1. **Network Overview Dashboard**:
   - Total network traffic volume
   - Protocol distribution
   - Top communicating endpoints

2. **Service Map Dashboard**:
   - Service dependency visualization
   - Communication pattern analysis
   - Service status monitoring

3. **Security Dashboard**:
   - Policy decision visualization
   - Dropped packet analysis
   - Security event tracking

4. **HTTP Dashboard**:
   - Request volume by endpoint
   - Response code distribution
   - Latency distribution

## Real-time Threat Detection

Cilium and Hubble leverage eBPF to provide real-time threat detection capabilities. This enables detection and response to network-based attacks.

### Detectable Threat Types:

1. **Network Scans**:
   - Port scan detection
   - Service enumeration attempts
   - Brute force attacks

2. **Abnormal Traffic Patterns**:
   - Sudden traffic increases
   - Abnormal protocol usage
   - Abnormal connection patterns

3. **Policy Violations**:
   - Unauthorized inter-service communication
   - Unauthorized external connections
   - Unauthorized protocol usage

4. **Known Attack Patterns**:
   - SQL injection attempts
   - XSS (Cross-Site Scripting) attempts
   - Command injection attempts

### Threat Detection Configuration:

```yaml
# threat-detection-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  # Enable threat detection
  enable-threat-detection: "true"

  # Enable anomaly detection
  enable-anomaly-detection: "true"

  # Alert configuration
  alert-to-slack: "true"
  slack-webhook-url: "https://hooks.slack.com/services/..."

  # Logging configuration
  log-level: "info"
  enable-flow-logs: "true"
```

### Threat Response Automation:

Cilium can configure automatic responses to detected threats:

1. **Automatic Blocking**:
   - Malicious IP address blocking
   - Abnormal pod isolation
   - Malicious domain blocking

2. **Rate Limiting**:
   - Excessive request limiting
   - Connection count limiting
   - Bandwidth limiting

3. **Alerts and Logging**:
   - Alerts to Slack, PagerDuty, etc.
   - Log forwarding to central logging systems
   - Security Information and Event Management (SIEM) integration

### Threat Detection Monitoring:

```bash
# Monitor dropped packets
hubble observe --verdict DROPPED

# Monitor policy violations
hubble observe --verdict POLICY_DENIED

# Monitor HTTP errors
hubble observe --protocol http --http-status 4.. --http-status 5..

# Monitor traffic from specific IP
hubble observe --ip 10.0.0.1

# Set up real-time threat alerts
hubble observe --verdict DROPPED --output json | jq -c 'select(.verdict.reason == "Policy denied")' | webhook-forwarder
```

## Lab: Hubble Installation and Usage

### 1. Hubble Installation and Configuration:

```bash
# Enable Hubble
cilium hubble enable --ui

# Check Hubble status
cilium hubble status

# Access Hubble UI
cilium hubble ui
```

### 2. Network Policy Application and Monitoring:

```bash
# Apply default deny policy
kubectl apply -f - <<EOF
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "deny-all"
spec:
  endpointSelector: {}
  ingress:
  - {}
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
EOF

# Monitor policy violations
hubble observe --verdict DROPPED
```

### 3. Service Dependency Map Creation:

```bash
# Deploy test application
kubectl apply -f https://raw.githubusercontent.com/cilium/cilium/master/examples/minikube/http-sw-app.yaml

# Generate traffic
kubectl exec -ti deployment/xwing -- curl -s -XPOST deathstar.default.svc.cluster.local/v1/request-landing

# View service map
cilium hubble ui
```

### 4. Security Event Monitoring:

```bash
# Monitor security events
hubble observe --type drop --output json

# Monitor security events for specific pod
hubble observe --pod app=deathstar --verdict DROPPED

# Security event statistics
hubble observe --verdict DROPPED --output json | jq -c '.verdict.reason' | sort | uniq -c
```

[Return to Main Page](README.md)

## Quiz

To test what you learned in this chapter, try the [Topic Quiz](../../quizzes/networking/cilium/06-security-visibility-quiz.md).
