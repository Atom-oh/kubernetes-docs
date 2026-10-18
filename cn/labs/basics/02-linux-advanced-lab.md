# Linux 高级技能实验指南

> **难度**：初级
> **预计时间**：40 分钟
> **最后更新**：2026 年 9 月 11 日

## 学习目标
- 练习使用 jq 解析 JSON 数据
- 编写简单的 shell 脚本
- 使用管道处理 kubectl 输出

## 前提条件
- [ ] Bash 和常用 Linux 文本处理工具（awk、grep、sed、coreutils）
- [ ] 已安装 jq 和 curl（`sudo apt-get install jq curl` 或 `sudo dnf install jq curl`）
- [ ] 已完成[Linux 运维技能](../../basics/02-linux-advanced.md)学习

以下步骤请在同一个 Bash 终端中执行。文件会创建在私有临时目录中。这里精简后的 PodList 仅用于 JSON 解析练习，不能作为 manifest 应用；无需 Kubernetes 集群。单独处于 Running 阶段不代表 Pod 已 Ready。

---

## 练习 1：使用 jq 解析 JSON

### 目标
使用 jq 处理类似 Kubernetes kubectl 输出的 JSON 数据。

### 步骤

**步骤 1.1：创建示例 JSON**
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

**步骤 1.2：基础 jq 查询**
```bash
# Extract only Pod names
jq '.items[].metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

预期输出：
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**步骤 1.3：高级 jq 管道**
```bash
# Count Pods by namespace
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

<details>
<summary>需要提示吗？</summary>

- `jq -r` 会去掉字符串两侧的引号
- `select(condition)` 只筛选符合条件的条目
- `@tsv` 会以制表符分隔的格式输出
- 在实际 K8s 环境中，可以这样使用：`kubectl get pods -A -o json | jq '...'`
</details>

### 验证
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json")
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## 练习 2：编写 Shell 脚本

### 目标
编写适用于 K8s 运维的简单 shell 脚本。

### 步骤

**步骤 2.1：健康检查脚本**
此脚本有意要求 HTTP 200。它会校验 timeout；即使已经收到 200 响应头，只要 curl 传输失败仍会判定为失败。脚本绕过 curlrc 和代理设置，直接发送请求。应用必须实际提供该 endpoint；不要认为此脚本会创建 endpoint。在 Kubernetes 中，条件允许时优先使用原生 `httpGet` probe。它的成功状态范围是 200–399，与本脚本不同；`exec` probe 还要求镜像中有 Bash 和 curl，并且 probe timeout 必须能够覆盖脚本的时间预算。

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

**步骤 2.2：日志分析脚本**
请明确创建下面的六行合成 fixture。分析器读取指定的常规文件；如果路径不正确，它不会自行生成数据。它假设静态快照的第 1、2 个字段分别是时间戳和级别。包含单词 ERROR 的 INFO 记录不能计入错误数。

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
<summary>需要提示吗？</summary>

- `awk` 可以精确匹配级别字段；消息其他位置出现的单词不算级别
- `grep -E` 使用扩展正则表达式；这些示例不需要 Perl 正则表达式支持
- fixture 共 6 条记录：INFO 3 条、WARN 1 条、ERROR 2 条。这些是合成计数，不是从实际服务日志中观测到的数据
</details>

### 验证
```bash
# Verify scripts are executable
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## 练习 3：文本处理管道

### 目标
组合使用 grep、awk 和 sed 来处理数据。

### 步骤

**步骤 3.1：使用 grep 搜索模式**
```bash
# Match the level field, not the word ERROR inside a message.
grep -E '^[^[:space:]]+[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Sample UTC window: 10:00:02 through 10:00:04 on the fixture date.
grep -E '^2026-01-01T10:00:0[2-4]Z[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**步骤 3.2：使用 awk 提取字段**
```bash
# Extract only time and level from log
awk '{print $1, $2}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count+0}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**步骤 3.3：使用 sed 转换文本**
```bash
# Convert log levels to different text
sed -E 's/^([^[:space:]]+[[:space:]]+)INFO([[:space:]]|$)/\1info\2/; s/^([^[:space:]]+[[:space:]]+)WARN([[:space:]]|$)/\1warning\2/; s/^([^[:space:]]+[[:space:]]+)ERROR([[:space:]]|$)/\1error\2/' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Text-only Deployment replica-field example; not a ConfigMap or API update
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**步骤 3.4：组合管道**
```bash
awk '$2 == "ERROR" {sub(/^[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+/, ""); print}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | sort | uniq -c | sort -rn
```

### 验证
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## 清理
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


## 参考资料与验证范围

* [jq 手册](https://jqlang.org/manual/)
* [curl 手册](https://curl.se/docs/manpage.html)
* [Kubernetes 探针](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

验证使用本地合成 JSON/日志文件，以及模拟的 curl 状态码和退出码。不会访问实际健康检查 endpoint、生产日志或 Kubernetes API。

## 后续步骤
- [Linux 高级技能测验](../../quizzes/basics/02-linux-advanced-quiz.md)
- [容器技术实验](./03-container-technology-lab.md)
