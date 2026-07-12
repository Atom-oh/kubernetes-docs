# Linux 高级技能实验指南

> **难度**: 初级
> **预计时间**: 40 分钟
> **最后更新**: February 11, 2026

## 学习目标
- 使用 jq 练习 JSON 数据解析
- 编写简单的 shell 脚本
- 使用管道处理 kubectl 输出

## 前提条件
- [ ] Linux 终端访问权限
- [ ] 已安装 jq（`sudo apt-get install jq` 或 `sudo yum install jq`）
- [ ] 已完成 [Linux 操作技能](../../basics/02-linux-advanced.md) 学习

---

## 练习 1: 使用 jq 进行 JSON 解析

### 目标
使用 jq 处理类似 Kubernetes kubectl 输出的 JSON 数据。

### 步骤

**步骤 1.1: 创建示例 JSON**
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

**步骤 1.2: 基础 jq 查询**
```bash
# 仅提取 Pod 名称
jq '.items[].metadata.name' /tmp/pods.json

# 仅筛选运行状态的 Pod
jq '.items[] | select(.status.phase == "Running") | .metadata.name' /tmp/pods.json

# 以表格格式输出
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' /tmp/pods.json
```

预期输出:
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**步骤 1.3: 高级 jq 管道**
```bash
# 按命名空间统计 Pod 数量
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' /tmp/pods.json

# 基于标签筛选
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' /tmp/pods.json
```

<details>
<summary>需要提示吗？</summary>

- `jq -r` 从字符串中移除引号
- `select(condition)` 仅筛选符合条件的项目
- `@tsv` 以制表符分隔格式输出
- 在真实 K8s 中，使用 `kubectl get pods -o json | jq '...'`
</details>

### 验证
```bash
# 验证运行状态的 Pod 数量为 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' /tmp/pods.json)
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## 练习 2: Shell 脚本编写

### 目标
编写对 K8s 操作有用的简单 shell 脚本。

### 步骤

**步骤 2.1: 健康检查脚本**
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

**步骤 2.2: 日志分析脚本**
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

- `$((RANDOM % N))` 生成 0 到 N-1 的随机数
- `grep -oP` 使用 Perl 正则表达式仅提取匹配部分
- `sort | uniq -c | sort -rn` 是频率统计的基本模式
</details>

### 验证
```bash
# 验证脚本是否可执行
[ -x /tmp/health-check.sh ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x /tmp/log-analyzer.sh ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## 练习 3: 文本处理管道

### 目标
通过结合 grep、awk 和 sed 来处理数据。

### 步骤

**步骤 3.1: grep 模式搜索**
```bash
# 从示例日志中提取 ERROR 行
grep "ERROR" /tmp/sample.log | head -5

# 按时间段提取错误（使用正则表达式）
grep -P "T\d{2}:" /tmp/sample.log | grep ERROR | head -5
```

**步骤 3.2: awk 字段提取**
```bash
# 仅从日志中提取时间和级别
awk '{print $1, $2}' /tmp/sample.log | head -10

# 仅筛选 ERROR 级别并计数
awk '$2 == "ERROR" {count++} END {print "Error count:", count}' /tmp/sample.log
```

**步骤 3.3: sed 文本转换**
```bash
# 将日志级别转换为不同文本
sed 's/INFO/info/g; s/WARN/warning/g; s/ERROR/error/g' /tmp/sample.log | head -5

# 更改 K8s YAML 值（ConfigMap 更新模拟）
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**步骤 3.4: 管道组合**
```bash
# 按错误消息进行频率分析
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
