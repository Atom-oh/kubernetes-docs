# Linux 高级技能实验指南

> **难度**: 初级
> **预计时间**: 40 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 练习使用 jq 解析 JSON 数据
- 编写简单的 shell 脚本
- 使用管道处理 kubectl 输出

## 前提条件
- [ ] 可访问 Linux 终端
- [ ] 已安装 jq（`sudo apt-get install jq` 或 `sudo yum install jq`）
- [ ] 已完成 [Linux 操作技能](../../basics/02-linux-advanced.md) 学习

---

## 练习 1：使用 jq 解析 JSON

### 目标
使用 jq 处理类似 Kubernetes kubectl 输出的 JSON 数据。

### 步骤

**步骤 1.1：创建示例 JSON**
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

**步骤 1.2：基础 jq 查询**
```bash
# Extract only Pod names
jq '.items[].metadata.name' /tmp/pods.json

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' /tmp/pods.json

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' /tmp/pods.json
```

预期输出:
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**步骤 1.3：高级 jq 管道**
```bash
# Count Pods by namespace
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' /tmp/pods.json

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' /tmp/pods.json
```

<details>
<summary>需要提示吗？</summary>

- `jq -r` 会去掉字符串中的引号
- `select(condition)` 只筛选匹配条件的项目
- `@tsv` 以制表符分隔格式输出
- 在实际 K8s 中，像这样使用：`kubectl get pods -o json | jq '...'`
</details>

### 验证
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' /tmp/pods.json)
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## 练习 2：编写 Shell 脚本

### 目标
编写对 K8s 操作有用的简单 shell 脚本。

### 步骤

**步骤 2.1：Health Check 脚本**
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

**步骤 2.2：日志分析脚本**
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
<summary>需要提示吗？</summary>

- `$((RANDOM % N))` 会生成从 0 到 N-1 的随机数
- `grep -oP` 使用 Perl 正则表达式仅提取匹配的部分
- `sort | uniq -c | sort -rn` 是频率计数的基本模式
</details>

### 验证
```bash
# Verify scripts are executable
[ -x /tmp/health-check.sh ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x /tmp/log-analyzer.sh ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## 练习 3：文本处理管道

### 目标
通过组合 grep、awk 和 sed 处理数据。

### 步骤

**步骤 3.1：grep 模式搜索**
```bash
# Extract ERROR lines from sample log
grep "ERROR" /tmp/sample.log | head -5

# Extract errors by time period (using regex)
grep -P "T\d{2}:" /tmp/sample.log | grep ERROR | head -5
```

**步骤 3.2：awk 字段提取**
```bash
# Extract only time and level from log
awk '{print $1, $2}' /tmp/sample.log | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count}' /tmp/sample.log
```

**步骤 3.3：sed 文本转换**
```bash
# Convert log levels to different text
sed 's/INFO/info/g; s/WARN/warning/g; s/ERROR/error/g' /tmp/sample.log | head -5

# Change K8s YAML values (ConfigMap update simulation)
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**步骤 3.4：管道组合**
```bash
# Frequency analysis by error message
grep "ERROR" /tmp/sample.log | awk '{$1=$2=""; print $0}' | sort | uniq -c | sort -rn
```

### 验证
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## 清理
```bash
rm -f /tmp/pods.json /tmp/health-check.sh /tmp/log-analyzer.sh /tmp/sample.log
```

## 后续步骤
- [Linux 高级技能测验](../../quizzes/basics/02-linux-advanced-quiz.md)
- [容器技术实验](./03-container-technology-lab.md)
