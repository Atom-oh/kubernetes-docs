# Linux 高度なスキル ラボガイド

> **難易度**: 初級
> **目安時間**: 40分
> **最終更新**: February 11, 2026

## 学習目標
- jq を使用した JSON データ解析を練習する
- シンプルなシェルスクリプトを書く
- パイプラインで kubectl 出力を処理する

## 前提条件
- [ ] Linux ターミナルへのアクセス
- [ ] jq がインストール済み（`sudo apt-get install jq` または `sudo yum install jq`）
- [ ] [Linux 操作スキル](../../basics/02-linux-advanced.md) の学習を完了済み

---

## 演習 1: jq による JSON 解析

### 目標
jq を使用して、Kubernetes kubectl 出力に似た JSON データを処理します。

### 手順

**ステップ 1.1: サンプル JSON の作成**
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

**ステップ 1.2: 基本的な jq クエリ**
```bash
# Extract only Pod names
jq '.items[].metadata.name' /tmp/pods.json

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' /tmp/pods.json

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' /tmp/pods.json
```

期待される出力:
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**ステップ 1.3: 高度な jq パイプライン**
```bash
# Count Pods by namespace
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' /tmp/pods.json

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' /tmp/pods.json
```

<details>
<summary>ヒントが必要ですか?</summary>

- `jq -r` は文字列から引用符を取り除きます
- `select(condition)` は条件に一致する項目だけをフィルタします
- `@tsv` はタブ区切り形式で出力します
- 実際の K8s では、`kubectl get pods -o json | jq '...'` のように使用します
</details>

### 検証
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' /tmp/pods.json)
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## 演習 2: シェルスクリプトの作成

### 目標
K8s 操作に役立つシンプルなシェルスクリプトを書きます。

### 手順

**ステップ 2.1: Health Check スクリプト**
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

**ステップ 2.2: ログ分析スクリプト**
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
<summary>ヒントが必要ですか?</summary>

- `$((RANDOM % N))` は 0 から N-1 までのランダムな数値を生成します
- `grep -oP` は Perl 正規表現を使用して一致した部分だけを抽出します
- `sort | uniq -c | sort -rn` は頻度カウントの基本パターンです
</details>

### 検証
```bash
# Verify scripts are executable
[ -x /tmp/health-check.sh ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x /tmp/log-analyzer.sh ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## 演習 3: テキスト処理パイプライン

### 目標
grep、awk、sed を組み合わせてデータを処理します。

### 手順

**ステップ 3.1: grep パターン検索**
```bash
# Extract ERROR lines from sample log
grep "ERROR" /tmp/sample.log | head -5

# Extract errors by time period (using regex)
grep -P "T\d{2}:" /tmp/sample.log | grep ERROR | head -5
```

**ステップ 3.2: awk フィールド抽出**
```bash
# Extract only time and level from log
awk '{print $1, $2}' /tmp/sample.log | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count}' /tmp/sample.log
```

**ステップ 3.3: sed テキスト変換**
```bash
# Convert log levels to different text
sed 's/INFO/info/g; s/WARN/warning/g; s/ERROR/error/g' /tmp/sample.log | head -5

# Change K8s YAML values (ConfigMap update simulation)
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**ステップ 3.4: パイプラインの組み合わせ**
```bash
# Frequency analysis by error message
grep "ERROR" /tmp/sample.log | awk '{$1=$2=""; print $0}' | sort | uniq -c | sort -rn
```

### 検証
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## クリーンアップ
```bash
rm -f /tmp/pods.json /tmp/health-check.sh /tmp/log-analyzer.sh /tmp/sample.log
```

## 次のステップ
- [Linux 高度なスキル クイズ](../../quizzes/basics/02-linux-advanced-quiz.md)
- [コンテナ技術ラボ](./03-container-technology-lab.md)
