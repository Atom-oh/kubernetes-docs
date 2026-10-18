# Linux 上級スキルラボガイド

> **難易度**: 初級
> **目安時間**: 40分
> **最終更新日**: 2026年9月11日

## 学習目標
- jq を使った JSON データの解析を練習する
- 基本的なシェルスクリプトを書く
- パイプラインで kubectl の出力を処理する

## 前提条件
- [ ] Bash と Linux 標準のテキスト処理ツール（awk、grep、sed、coreutils）
- [ ] jq と curl がインストール済み（`sudo apt-get install jq curl` または `sudo dnf install jq curl`）
- [ ] [Linux 操作スキル](../../basics/02-linux-advanced.md)の学習を完了している

手順は同じ Bash ターミナルで実行してください。ファイルは自分専用の一時ディレクトリに作成します。縮小版の PodList は JSON 解析用のテストデータであり、適用するマニフェストではありません。Kubernetes クラスターは不要です。Pod の `phase` が `Running` でも、Pod が Ready であるとは限りません。

---

## 演習 1: jq による JSON 解析

### 目標
kubectl の出力に似た JSON データを jq で処理します。

### 手順

**ステップ 1.1: サンプル JSON を作成する**
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

**ステップ 1.2: 基本的な jq クエリ**
```bash
# Extract only Pod names
jq '.items[].metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter only Pods in Running state
jq '.items[] | select(.status.phase == "Running") | .metadata.name' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Output in table format
jq -r '.items[] | [.metadata.name, .metadata.namespace, .status.phase] | @tsv' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

出力例:
```
nginx-7d4f8b    default    Running
redis-abc123    cache      Running
api-server-xyz  default    Pending
```

**ステップ 1.3: jq の応用パイプライン**
```bash
# Count Pods by namespace
jq '[.items[].metadata.namespace] | group_by(.) | map({namespace: .[0], count: length})' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"

# Filter based on labels
jq '.items[] | select(.metadata.labels.app == "nginx") | {name: .metadata.name, ip: .status.podIP}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json"
```

<details>
<summary>ヒントを見る</summary>

- `jq -r` は文字列を囲む引用符を取り除きます。
- `select(condition)` は条件に一致する項目だけを抽出します。
- `@tsv` はタブ区切り形式で出力します。
- 実際の Kubernetes では、`kubectl get pods -A -o json | jq '...'` のように使います。
</details>

### 検証
```bash
# Verify that the number of Running Pods is 2
COUNT=$(jq '[.items[] | select(.status.phase == "Running")] | length' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/pods.json")
[ "$COUNT" -eq 2 ] && echo "Correct! Running Pod count: $COUNT" || echo "Please check again"
```

---

## 演習 2: シェルスクリプトを書く

### 目標
Kubernetes の運用に役立つ基本的なシェルスクリプトを書きます。

### 手順

**ステップ 2.1: ヘルスチェック用スクリプト**
スクリプトは HTTP 200 の場合だけを成功とします。タイムアウト値を検証し、HTTP 200 のヘッダーを受信していても curl の転送が失敗した場合は失敗として扱います。curlrc やプロキシの設定を読み込まず、宛先へ直接リクエストを送ります。アプリケーション側に実際のエンドポイントが必要です。このスクリプトがエンドポイントを作成するわけではありません。Kubernetes では、可能な場合はネイティブの httpGet probe を優先してください。その成功条件は 200～399 であり、このスクリプトとは異なります。exec probe を使う場合は、コンテナイメージに Bash と curl が必要で、probe のタイムアウトがスクリプトの実行時間の上限を許容する必要があります。

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

**ステップ 2.2: ログ分析スクリプト**
次の 6 行の合成テストデータを明示的に作成してください。分析スクリプトは指定された通常ファイルを読み込み、パスが誤っている場合にデータをでっち上げることはありません。静的なスナップショットを対象とし、1 列目を時刻、2 列目をレベルとして扱います。メッセージに ERROR という語を含む INFO レコードは、エラーとして数えてはいけません。

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
<summary>ヒントを見る</summary>

- `awk` でレベル列を完全一致で判定できます。メッセージ内に同じ語がある場合とは区別してください。
- `grep -E` は拡張正規表現を使います。この例に Perl 正規表現は必要ありません。
- テストデータは 6 レコードで、INFO が 3 件、WARN が 1 件、ERROR が 2 件です。これらは合成データの件数であり、実際のサービスログを集計したものではありません。
</details>

### 検証
```bash
# Verify scripts are executable
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/health-check.sh" ] && echo "health-check.sh is executable" || echo "No execute permission"
[ -x "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/log-analyzer.sh" ] && echo "log-analyzer.sh is executable" || echo "No execute permission"
```

---

## 演習 3: テキスト処理パイプライン

### 目標
grep、awk、sed を組み合わせてデータを処理します。

### 手順

**ステップ 3.1: grep でパターンを検索する**
```bash
# Match the level field, not the word ERROR inside a message.
grep -E '^[^[:space:]]+[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Sample UTC window: 10:00:02 through 10:00:04 on the fixture date.
grep -E '^2026-01-01T10:00:0[2-4]Z[[:space:]]+ERROR([[:space:]]|$)' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**ステップ 3.2: awk でフィールドを抽出する**
```bash
# Extract only time and level from log
awk '{print $1, $2}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -10

# Filter only ERROR level and count
awk '$2 == "ERROR" {count++} END {print "Error count:", count+0}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log"
```

**ステップ 3.3: sed でテキストを変換する**
```bash
# Convert log levels to different text
sed -E 's/^([^[:space:]]+[[:space:]]+)INFO([[:space:]]|$)/\1info\2/; s/^([^[:space:]]+[[:space:]]+)WARN([[:space:]]|$)/\1warning\2/; s/^([^[:space:]]+[[:space:]]+)ERROR([[:space:]]|$)/\1error\2/' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | head -5

# Text-only Deployment replica-field example; not a ConfigMap or API update
echo "replicas: 3" | sed 's/replicas: [0-9]*/replicas: 5/'
```

**ステップ 3.4: パイプラインを組み合わせる**
```bash
awk '$2 == "ERROR" {sub(/^[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+/, ""); print}' "${LINUX_ADVANCED_LAB_DIR:?Run Step 1.1 first}/sample.log" | sort | uniq -c | sort -rn
```

### 検証
```bash
echo "Exercise complete! Feel free to experiment with pipeline combinations."
```

---

## クリーンアップ
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

## 参考資料と検証範囲

* [jq マニュアル](https://jqlang.org/manual/)
* [curl マニュアル](https://curl.se/docs/manpage.html)
* [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

検証では、ローカルの合成 JSON／ログファイルと、シミュレートした curl のステータス／終了コードを使用します。稼働中のヘルスエンドポイント、本番ログ、Kubernetes API にはアクセスしません。

## 次のステップ
- [Linux 上級スキルクイズ](../../quizzes/basics/02-linux-advanced-quiz.md)
- [コンテナ技術ラボ](./03-container-technology-lab.md)
