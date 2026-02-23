# Linux Advanced Skills Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 40 minutes
> **Last Updated**: February 11, 2026

## Learning Objectives
- Practice JSON data parsing using jq
- Write simple shell scripts
- Process kubectl output with pipelines

## Prerequisites
- [ ] Linux terminal access
- [ ] jq installed (`sudo apt-get install jq` or `sudo yum install jq`)
- [ ] Completed [Linux Operations Skills](../../basics/02-linux-advanced.md) learning

---

## Exercise 1: JSON Parsing with jq

### Goal
Process JSON data similar to Kubernetes kubectl output using jq.

### Steps

**Step 1.1: Create sample JSON**
```bash
cat > /tmp/pods.json << 'EOF'
{
  "apiVersion": "v1",
  "kind": "PodList",
  "items": [
    {
      "metadata": {"name": "nginx-7d4f8b", "namespace": "default", "labels": {"app": "nginx"}},
      "status": {"phase": "Running", "podIP": "10.244.0.5"}
    },
    {
      "metadata": {"name": "redis-abc123", "namespace": "cache", "labels": {"app": "redis"}},
      "status": {"phase": "Running", "podIP": "10.244.1.3"}
    },
    {
      "metadata": {"name": "api-server-xyz", "namespace": "default", "labels": {"app": "api"}},
      "status": {"phase": "Pending", "podIP": null}
    }
  ]
}
EOF
```

**Step 1.2: Basic jq queries**
```bash
# Extract only Pod names
jq '.items[].metadata.name' /tmp/pods.json

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' /tmp/pods.json

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' /tmp/pods.json
```

Expected output:
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**Step 1.3: Advanced jq pipelines**
```bash
# Count Pods by namespace
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' /tmp/pods.json

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' /tmp/pods.json
```

<details>
<summary>Need a hint?</summary>

- `jq -r` removes quotes from strings
- `select(condition)` filters only items matching the condition
- `@tsv` outputs in tab-separated format
- In real K8s, use it like `kubectl get pods -o json | jq '...'`
</details>

### Verification
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' /tmp/pods.json)
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## Exercise 2: Shell Script Writing

### Goal
Write simple shell scripts useful for K8s operations.

### Steps

**Step 2.1: Health Check script**
```bash
cat > /tmp/health-check.sh << 'SCRIPT'
#!/bin/bash
# Health check script that can be used in K8s liveness probes

ENDPOINT="${1:-http://localhost:8080/health}"
TIMEOUT="${2:-5}"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$ENDPOINT" 2>/dev/null)

if [ "$response" = "200" ]; then
    echo "OK: Health check passed (HTTP $response)"
    exit 0
else
    echo "FAIL: Health check failed (HTTP $response)"
    exit 1
fi
SCRIPT

chmod +x /tmp/health-check.sh
cat /tmp/health-check.sh
```

**Step 2.2: Log analysis script**
```bash
cat > /tmp/log-analyzer.sh << 'SCRIPT'
#!/bin/bash
# Script to analyze error patterns in log files

LOG_FILE="${1:-/tmp/sample.log}"

# Generate sample logs
if [ ! -f "$LOG_FILE" ]; then
    for i in $(seq 1 100); do
        level=$((RANDOM % 4))
        case $level in
            0) echo "$(date -Iseconds) INFO  Request processed successfully" ;;
            1) echo "$(date -Iseconds) WARN  High memory usage detected" ;;
            2) echo "$(date -Iseconds) ERROR Connection timeout to database" ;;
            3) echo "$(date -Iseconds) INFO  Health check passed" ;;
        esac
    done > "$LOG_FILE"
fi

echo "=== Log Analysis Results ==="
echo "Total lines: $(wc -l < "$LOG_FILE")"
echo ""
echo "Statistics by level:"
grep -oP '(INFO|WARN|ERROR)' "$LOG_FILE" | sort | uniq -c | sort -rn
echo ""
echo "Recent errors (last 5):"
grep "ERROR" "$LOG_FILE" | tail -5
SCRIPT

chmod +x /tmp/log-analyzer.sh
bash /tmp/log-analyzer.sh
```

<details>
<summary>Need a hint?</summary>

- `$((RANDOM % N))` generates a random number from 0 to N-1
- `grep -oP` extracts only the matched portion using Perl regex
- `sort | uniq -c | sort -rn` is the basic pattern for frequency counting
</details>

### Verification
```bash
# Verify scripts are executable
[ -x /tmp/health-check.sh ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x /tmp/log-analyzer.sh ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## Exercise 3: Text Processing Pipeline

### Goal
Process data by combining grep, awk, and sed.

### Steps

**Step 3.1: grep pattern search**
```bash
# Extract ERROR lines from sample log
grep "ERROR" /tmp/sample.log | head -5

# Extract errors by time period (using regex)
grep -P "T\d{2}:" /tmp/sample.log | grep ERROR | head -5
```

**Step 3.2: awk field extraction**
```bash
# Extract only time and level from log
awk '{print $1, $2}' /tmp/sample.log | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count}' /tmp/sample.log
```

**Step 3.3: sed text transformation**
```bash
# Convert log levels to different text
sed 's/INFO/info/g; s/WARN/warning/g; s/ERROR/error/g' /tmp/sample.log | head -5

# Change K8s YAML values (ConfigMap update simulation)
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**Step 3.4: Pipeline combination**
```bash
# Frequency analysis by error message
grep "ERROR" /tmp/sample.log | awk '{$1=$2=""; print $0}' | sort | uniq -c | sort -rn
```

### Verification
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## Cleanup
```bash
rm -f /tmp/pods.json /tmp/health-check.sh /tmp/log-analyzer.sh /tmp/sample.log
```

## Next Steps
- [Linux Advanced Skills Quiz](../../quizzes/basics/02-linux-advanced-quiz.md)
- [Container Technology Lab](./03-container-technology-lab.md)
