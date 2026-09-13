# Linux Advanced Skills Lab Guide

> **Difficulty**: Beginner
> **Estimated Time**: 40 minutes
> **Last Updated**: September 11, 2026

## Learning Objectives
- Practice JSON data parsing using jq
- Write simple shell scripts
- Process kubectl output with pipelines

## Prerequisites
- [ ] Bash and standard Linux text tools (awk, grep, sed, coreutils)
- [ ] jq and curl installed (`sudo apt-get install jq curl` or `sudo dnf install jq curl`)
- [ ] Completed [Linux Operations Skills](../../basics/02-linux-advanced.md) learning

Use the same Bash terminal for the steps. Files are created in a private temporary directory. The reduced PodList is a JSON parsing fixture, not a manifest to apply; no Kubernetes cluster is required. Running phase alone does not mean a Pod is Ready.

---

## Exercise 1: JSON Parsing with jq

### Goal
Process JSON data similar to Kubernetes kubectl output using jq.

### Steps

**Step 1.1: Create sample JSON**
```bash
LINUX_ADVANCED_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-advanced.XXXXXX)
: "${LINUX_ADVANCED_LAB_DIR:?mktemp failed}"
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json" << 'EOF'
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
jq '.items[].metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
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
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

<details>
<summary>Need a hint?</summary>

- `jq -r` removes quotes from strings
- `select(condition)` filters only items matching the condition
- `@tsv` outputs in tab-separated format
- In real K8s, use it like `kubectl get pods -A -o json | jq '...'`
</details>

### Verification
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json")
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## Exercise 2: Shell Script Writing

### Goal
Write simple shell scripts useful for K8s operations.

### Steps

**Step 2.1: Health Check script**
The script intentionally requires HTTP 200. It validates the timeout and treats a failed curl transfer as failure even if a 200 header was received. It makes direct requests without curlrc/proxy settings. An application must actually provide the endpoint; do not assume the script creates one. For Kubernetes, prefer a native httpGet probe where possible. Its 200–399 success rule differs from this script; an exec probe also needs Bash/curl in the image and a probe timeout that accommodates the script budget.

```bash
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" << 'SCRIPT'
#!/bin/bash
set -u

ENDPOINT="${1:-http://127.0.0.1:8080/health}"
TIMEOUT="${2:-5}"
if (( $# > 2 )) || ! [[ "$TIMEOUT" =~ ^[1-9][0-9]?$ ]] || (( TIMEOUT > 60 )); then
    printf 'Usage: health-check.sh [http(s) URL] [timeout integer 1..60]\n' >&2
    exit 2
fi
case "$ENDPOINT" in
    http://*|https://*) ;;
    *) printf 'Only HTTP(S) endpoints are supported\n' >&2; exit 2 ;;
esac

# Ignore curlrc and proxies for this direct health-endpoint check.
if ! response=$(curl --disable --noproxy '*' --silent --show-error \
    --output /dev/null --write-out '%{http_code}' \
    --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" -- "$ENDPOINT"); then
    printf 'FAIL: transport error or timeout\n' >&2
    exit 1
fi
if [[ "$response" == "200" ]]; then
    printf 'OK: health endpoint returned HTTP 200\n'
    exit 0
fi
printf 'FAIL: health endpoint returned HTTP %s\n' "$response" >&2
exit 1
SCRIPT
chmod +x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh"
```

**Step 2.2: Log analysis script**
Create the following six-line synthetic fixture explicitly. The analyzer reads a supplied regular file and never invents data when the path is wrong. It assumes a static snapshot with timestamp and level in fields 1/2. The INFO record containing the word ERROR must not be counted as an error.

```bash
# Explicit synthetic fixture, not a copy of production logs.
cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" << 'LOG'
2026-01-01T10:00:00Z INFO Application started
2026-01-01T10:00:01Z WARN Cache warming
2026-01-01T10:00:02Z ERROR Database connection timeout
2026-01-01T10:00:03Z INFO The word ERROR appears in this message
2026-01-01T10:00:04Z ERROR Upstream request timeout
2026-01-01T10:00:05Z INFO Health check passed
LOG

cat > "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" << 'SCRIPT'
#!/bin/bash
set -euo pipefail

if (( $# != 1 )) || [[ ! -f "$1" || ! -r "$1" ]]; then
    printf 'Usage: log-analyzer.sh readable-regular-log-file\n' >&2
    exit 2
fi
LOG_FILE="$1"

# Assumes a static snapshot: first field UTC timestamp, second field log level.
printf 'Total lines: %s\n' "$(wc -l < "$LOG_FILE")"
printf 'Counts by level:\n'
awk '$2 ~ /^(INFO|WARN|ERROR)$/ {count[$2]++}
     END {for (level in count) print count[level], level}' "$LOG_FILE" | sort -rn
printf 'Recent ERROR records (last 5):\n'
awk '$2 == "ERROR"' "$LOG_FILE" | tail -5
SCRIPT
chmod +x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh"
bash "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

<details>
<summary>Need a hint?</summary>

- `awk` can match the level field exactly; a word elsewhere in the message is different.
- `grep -E` uses extended regular expressions; these examples do not need Perl regex support.
- The fixture has 6 records: INFO 3, WARN 1, ERROR 2. These are synthetic counts, not observed service logs.
</details>

### Verification
```bash
# Verify scripts are executable
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## Exercise 3: Text Processing Pipeline

### Goal
Process data by combining grep, awk, and sed.

### Steps

**Step 3.1: grep pattern search**
```bash
# Match the level field, not the word ERROR inside a message.
grep -E '^[^[:space:]]+[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Sample UTC window: 10:00:02 through 10:00:04 on the fixture date.
grep -E '^2026-01-01T10:00:0[2-4]Z[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**Step 3.2: awk field extraction**
```bash
# Extract only time and level from log
awk '{print $1, $2}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count+0}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**Step 3.3: sed text transformation**
```bash
# Convert log levels to different text
sed -E 's/^([^[:space:]]+[[:space:]]+)INFO([[:space:]]|$)/\1info\2/; s/^([^[:space:]]+[[:space:]]+)WARN([[:space:]]|$)/\1warning\2/; s/^([^[:space:]]+[[:space:]]+)ERROR([[:space:]]|$)/\1error\2/' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Text-only Deployment replica-field example; not a ConfigMap or API update
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**Step 3.4: Pipeline combination**
```bash
awk '$2 == "ERROR" {sub(/^[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+/, ""); print}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | sort | uniq -c | sort -rn
```

### Verification
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## Cleanup
```bash
if [[ -n ${LINUX_ADVANCED_LAB_DIR:-} ]]; then
  rm -f -- "$LINUX_ADVANCED_LAB_DIR/pods.json" \
    "$LINUX_ADVANCED_LAB_DIR/health-check.sh" \
    "$LINUX_ADVANCED_LAB_DIR/log-analyzer.sh" \
    "$LINUX_ADVANCED_LAB_DIR/sample.log"
  if rmdir -- "$LINUX_ADVANCED_LAB_DIR"; then
    unset LINUX_ADVANCED_LAB_DIR
  fi
fi
```


## References and validation scope

* [jq manual](https://jqlang.org/manual/)
* [curl manual](https://curl.se/docs/manpage.html)
* [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

Validation uses local synthetic JSON/log files and simulated curl status/exit codes. No live health endpoint, production log or Kubernetes API is accessed.

## Next Steps
- [Linux Advanced Skills Quiz](../../quizzes/basics/02-linux-advanced-quiz.md)
- [Container Technology Lab](./03-container-technology-lab.md)
