# Linux 基礎ラボガイド

> **難易度**: 初級
> **所要時間の目安**: 45 分
> **最終更新日**: 2026年10月16日

## 学習目標
- Linux のプロセス管理コマンドを練習する
- Linux namespace による分離の効果を直接確認する
- cgroups によるリソース制限を理解する
- ファイルの権限と所有者を管理する

## 前提条件
- [ ] 演習 3 用に Bash、systemd、cgroup v2 を備えた保守対象の Linux VM
- [ ] ツール: coreutils、procps/procps-ng、util-linux、iproute2/iproute、Python 3
- [ ] sudo 権限
- [ ] [Linux 基礎](../../basics/01-linux-basics.md)の学習を完了していること

ラボ変数を保持できるよう、同じ Bash ターミナルで各ブロックを順番に実行してください。sudo を使う namespace／cgroup 演習には分離された VM を使用します。コンテナや制限付き環境では、sudo があっても必要な機能が使えないことがあります。以下の出力は例示です。この監査では特権を要する演習を実行していません。

---

## 演習 1: プロセス管理

### 目標
プロセス一覧、バックグラウンド実行、シグナル送信を練習します。

### 手順

**手順 1.1: 実行中のプロセスを確認する**
```bash
# Snapshot of processes visible in the current PID namespace
ps aux | head -20

# View process relationships in tree format
ps auxf | head -30
```

**手順 1.2: バックグラウンドプロセスを実行する**
```bash
sleep 300 &
LINUX_LAB_SLEEP_PID=$!
printf 'Lab child PID: %s\n' "$LINUX_LAB_SLEEP_PID"
jobs -l
```

**手順 1.3: プロセスにシグナルを送信する**
```bash
# Run in the same Bash session as Step 1.2.
: "${LINUX_LAB_SLEEP_PID:?Run Step 1.2 first}"
if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
  kill -TERM "$LINUX_LAB_SLEEP_PID"
fi
if wait "$LINUX_LAB_SLEEP_PID"; then
  LINUX_LAB_EXIT_STATUS=0
else
  LINUX_LAB_EXIT_STATUS=$?
fi
printf 'Lab child exit status: %s\n' "$LINUX_LAB_EXIT_STATUS"
unset LINUX_LAB_SLEEP_PID
```

<details>
<summary>ヒントを見る</summary>

- 利用可能なシグナルの一覧は `kill -l` で確認できます。
- `kill -9 PID` は SIGKILL で強制終了します。
- `$!` で取得した PID を使ってください。名前パターンは無関係なジョブにも一致する可能性があります。
</details>

### 確認
```bash
printf 'Recorded lab child exit status: %s\n' "${LINUX_LAB_EXIT_STATUS:?Complete Step 1.3}"
jobs -l
```

---

## 演習 2: Linux namespace による分離

### 目標
namespace を作成し、プロセスとネットワークの分離を確認します。

### 手順

**手順 2.1: PID namespace の分離を確認する**
```bash
# Run bash in a new PID namespace
sudo unshare --mount --pid --fork --mount-proc bash -c '
echo "PID list inside the new namespace:"
ps aux
echo "Current process PID: $$"
'
```

期待される出力:
```
PID list inside the new namespace:
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0   ...   ...  ...      S    ...    0:00 bash -c ...
root         2  0.0  0.0   ...   ...  ...      R    ...    0:00 ps aux
Current process PID: 1
```

**手順 2.2: network namespace による分離**
```bash
LINUX_LAB_NETNS="k8s-docs-netns-${UID}-$$"
(
  # Install cleanup only after creating this namespace successfully.
  sudo ip netns add "$LINUX_LAB_NETNS" || exit 1
  trap 'sudo ip netns delete "$LINUX_LAB_NETNS"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  sudo ip netns exec "$LINUX_LAB_NETNS" ip addr
)
```

<details>
<summary>ヒントを見る</summary>

- ホストのネットワークインターフェイスは network namespace 内からは見えません。
- `lo`（loopback）インターフェイスだけが存在し、デフォルトでは DOWN です。
- これはコンテナのネットワーク分離の基本原理です。
</details>

### 確認
```bash
if LINUX_LAB_NS_LIST=$(sudo ip netns list); then
  if printf '%s\n' "$LINUX_LAB_NS_LIST" | awk '{print $1}' | grep -Fxq -- "$LINUX_LAB_NETNS"; then
    printf 'Named handle still exists: %s\n' "$LINUX_LAB_NETNS"
  else
    printf 'Named handle is not listed: %s\n' "$LINUX_LAB_NETNS"
  fi
else
  printf 'Could not verify namespace handles\n' >&2
fi
```

---

名前付き netns ハンドルを削除しても、プロセスやファイル記述子が保持している namespace と、その中のプロセスは破棄されません。この例では `ip addr` コマンドの終了を待ってからクリーンアップします。

## 演習 3: cgroup によるリソース制限

### 目標
cgroups を使ってプロセスのメモリ使用量を制限します。

### 手順

**手順 3.1: cgroup の情報を確認する**
```bash
# cgroup2fs identifies a cgroup v2 mount.
stat -fc '%T' /sys/fs/cgroup
cat /proc/self/cgroup
if [ -r /sys/fs/cgroup/cgroup.controllers ]; then
  cat /sys/fs/cgroup/cgroup.controllers
else
  printf 'Controllers are not readable here; inspect the mount and permissions\n'
fi
```

**手順 3.2: メモリ使用量を確認する**
```bash
# System memory information
free -h

# Memory usage of specific processes
ps aux --sort=-%mem | head -10
```

**手順 3.3: 一時的な service に制限を適用する**

systemd と cgroup v2 の memory controller を利用できる VM で実行してください。これは自動命名される service を作成し、メモリ上限を 128 MiB、swap の使用量を 0 に設定します。意図的に OOM を起こすのではなく 16 MiB を使用し、`--wait --collect` により処理の完了を待って一時 unit をアンロードします。親階層の上限が、さらに厳しい場合があります。

```bash
sudo systemd-run --wait --collect --pipe \
  --property=MemoryMax=128M --property=MemorySwapMax=0 \
  python3 -c '
from pathlib import Path
entry = next(line for line in Path("/proc/self/cgroup").read_text().splitlines()
             if line.startswith("0::"))
group = Path("/sys/fs/cgroup") / entry.split(":", 2)[2].lstrip("/")
print("Configured memory.max:", (group / "memory.max").read_text().strip())
data = bytearray(16 * 1024 * 1024)
for offset in range(0, len(data), 4096):
    data[offset] = 1
print("Touched allocation bytes:", len(data))
'
```

128M の場合、設定される `memory.max` は 134217728 バイト、割り当てるメモリは 16777216 バイトであることを確認します。これらは設定と算術上の想定値であり、この監査で測定した結果ではありません。次の manifest は表示するだけで、Kubernetes Pod は作成しません。

**手順 3.4: Kubernetes のリソース制限との関係**
```bash
# Linux container memory-limit example; this block only prints YAML
# Let's look at a Pod manifest example
cat << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: memory-demo
spec:
  containers:
  - name: memory-demo
    image: nginx:1.30.6
    resources:
      requests:
        memory: "64Mi"
      limits:
        memory: "128Mi"
EOF
```

<details>
<summary>ヒントを見る</summary>

- Linux コンテナでは、runtime／kubelet がメモリ cgroup の上限を設定します。
- メモリ圧迫時の挙動は、割り当て状況と OOM group のポリシーにより、reclaim、割り当て失敗、OOM kill などになります。OOM で終了したコンテナは `OOMKilled` と報告される場合がありますが、割り当て失敗がすべてその状態になるわけではありません。
- `kubectl describe pod` では要求された上限と記録済みのコンテナ終了状態を確認できますが、カーネルのメモリイベントすべてが証明されるわけではありません。
</details>

---

## 演習 4: ファイル権限の管理

### 目標
ファイルの権限と所有者を管理します。

### 手順

**手順 4.1: ファイルを作成して権限を確認する**
```bash
LINUX_LAB_DIR=$(mktemp -d /tmp/k8s-docs-linux-basics.XXXXXX)
: "${LINUX_LAB_DIR:?mktemp failed}"
printf 'Hello Linux\n' > "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -ld "$LINUX_LAB_DIR"
ls -l "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

**手順 4.2: 権限を変更する**
```bash
# Add execute permission
chmod +x "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# Set with numeric mode (read/write - read - none)
chmod 640 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
ls -la "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"

# Set the same permissions as K8s Secret volume defaults
chmod 0644 "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

実行権限を追加しても、任意のテキストが有効なプログラムになるわけではありません。mode 0644 は、ディレクトリをたどれる場合に group／other にも読み取りを許可します。このラボでは、非公開の mktemp ディレクトリによりアクセスを制限します。Kubernetes Secret volume の既定権限は 0644 ですが、実際の Secret では利用する user／group と必要なアクセスに合わせて権限を設定してください。

**手順 4.3: 所有者を変更する**
```bash
id
# Demonstrate an owner change only on the private lab file, then restore it.
sudo chown "root:$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
stat -c '%a %U %G' "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
sudo chown "$(id -u):$(id -g)" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

### 確認
```bash
# Expect mode644 and the restored user/group
stat -c "%a %U %G" "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
```

---

## クリーンアップ
```bash
# Delete only the file created by this lab; keep an unexpected nonempty directory.
if [[ -n ${LINUX_LAB_DIR:-} ]]; then
  rm -f -- "${LINUX_LAB_DIR:?Run Step 4.1 first}/test.txt"
  if rmdir -- "$LINUX_LAB_DIR"; then
    unset LINUX_LAB_DIR
  fi
fi

# Only an unfinished job created in this Bash session may be terminated.
if [[ -n ${LINUX_LAB_SLEEP_PID:-} ]]; then
  if jobs -pr | grep -Fxq -- "$LINUX_LAB_SLEEP_PID"; then
    kill -TERM "$LINUX_LAB_SLEEP_PID"
  fi
  wait "$LINUX_LAB_SLEEP_PID" 2>/dev/null || true
  unset LINUX_LAB_SLEEP_PID
fi
```

## トラブルシューティング

<details>
<summary>unshare コマンドが見つからない</summary>

`util-linux` パッケージをインストールします。
```bash
sudo apt-get install util-linux   # Ubuntu/Debian
sudo dnf install util-linux       # Fedora/RHEL
```
</details>

<details>
<summary>ip netns コマンドが動作しない</summary>

`iproute2` パッケージが必要です。
```bash
sudo apt-get install iproute2     # Ubuntu/Debian
sudo dnf install iproute          # Fedora/RHEL
```
</details>

## 参考資料と検証範囲

* [systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)
* [systemd memory resource control](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)
* [Kernel cgroup v2 memory controller](https://docs.kernel.org/admin-guide/cgroup-v2.html)
* [unshare](https://man7.org/linux/man-pages/man1/unshare.1.html)
* [ip netns](https://man7.org/linux/man-pages/man8/ip-netns.8.html)
* [GNU mktemp manual](https://man7.org/linux/man-pages/man1/mktemp.1.html)

監査では分離された環境で、特権を要しないプロセス／ファイルの確認と構文チェックのみ実行しました。namespace の作成、所有者の変更、cgroup／systemd 操作は実行していません。

## 次のステップ
- [Linux 基礎クイズ](../../quizzes/basics/01-linux-basics-quiz.md)
- [Linux 応用スキルラボ](./02-linux-advanced-lab.md)
