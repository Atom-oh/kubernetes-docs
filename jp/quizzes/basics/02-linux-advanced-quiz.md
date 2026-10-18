# Linux 運用スキルクイズ

このクイズでは、Kubernetes 環境で使われる Linux 運用スキルについて理解度を確認します。

## 選択問題

1. 環境変数を子プロセスから利用できるようにするコマンドはどれですか？
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>解答を表示</summary>

**解答: B) export**

</details>

2. `.bashrc` が実行されるのはいつですか？
   - A) ログインシェルの場合のみ
   - B) すべてのシェルセッション
   - C) 非ログインの対話型シェル
   - D) 常に `.bash_profile` と一緒

<details>
<summary>解答を表示</summary>

**解答: C) 非ログインの対話型シェル**

</details>

3. `${REPLICAS:-3}` は何を意味しますか？
   - A) REPLICAS を 3 に設定する
   - B) REPLICAS が未設定または空の場合に 3 を使う
   - C) REPLICAS から 3 を減算する
   - D) エラーにする

<details>
<summary>解答を表示</summary>

**解答: B) REPLICAS が未設定または空の場合に 3 を使う**

</details>

4. `awk 'NR>1 {print $1}'` は何をしますか？
   - A) すべての行の最初のフィールドを出力する
   - B) 最初の行だけを出力する
   - C) ヘッダーを除き、各行の最初のフィールドを出力する
   - D) 最初のフィールドを含む行を出力する

<details>
<summary>解答を表示</summary>

**解答: C) ヘッダーを除き、各行の最初のフィールドを出力する**

</details>

5. `sed -i 's/old/new/g'` の `g` は何をしますか？
   - A) 大文字と小文字を区別しない
   - B) 行内の一致をすべて置換する
   - C) 1 回だけ置換する
   - D) 正規表現を有効にする

<details>
<summary>解答を表示</summary>

**解答: B) 行内の一致をすべて置換する**

</details>

6. `jq -r` の `-r` は何をしますか？
   - A) 再帰検索
   - B) 逆順
   - C) 引用符なしで文字列を出力する
   - D) 読み取り専用

<details>
<summary>解答を表示</summary>

**解答: C) 引用符なしで文字列を出力する**

</details>

7. `ssh -L 8080:localhost:80 user@server` は何を意味しますか？
   - A) サーバーの 8080 をローカルの 80 に転送する
   - B) ローカルの 8080 をサーバーの 80 に転送する
   - C) サーバーの 80 をローカルの 8080 に転送する
   - D) ローカルの 80 をサーバーの 8080 に転送する

<details>
<summary>解答を表示</summary>

**解答: B) ローカルの 8080 をサーバーの 80 に転送する**

</details>

8. vmstat の `wa` は何を表しますか？
   - A) Web アプリケーションの CPU 使用率
   - B) I/O 待ち時間の割合
   - C) 警告数
   - D) アクティブなプロセス数

<details>
<summary>解答を表示</summary>

**解答: B) I/O 待ち時間の割合**

</details>

9. LVM の Physical Volume を作成するコマンドはどれですか？
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>解答を表示</summary>

**解答: C) pvcreate**

</details>

10. `curl -s -o /dev/null -w "%{http_code}" URL` は何を出力しますか？
    - A) レスポンス本文
    - B) レスポンスヘッダー
    - C) HTTP ステータスコード
    - D) 応答時間

<details>
<summary>解答を表示</summary>

**解答: C) HTTP ステータスコード**

</details>

## 短答問題

11. ファイルの内容を現在のシェルで実行するコマンドは何ですか？

<details>
<summary>解答を表示</summary>

**解答: source (または .)**

</details>

12. JSON の解析に使うツールは何ですか？

<details>
<summary>解答を表示</summary>

**解答: jq**

</details>

13. bastion 経由の接続に使う SSH オプションは何ですか？

<details>
<summary>解答を表示</summary>

**解答: ProxyJump (または -J)**

</details>

14. ディスク I/O を監視するコマンドは何ですか？

<details>
<summary>解答を表示</summary>

**解答: iostat**

</details>

15. Pod の ServiceAccount トークンのパスは何ですか？

<details>
<summary>解答を表示</summary>

**解答: /var/run/secrets/kubernetes.io/serviceaccount/token**

これは投影トークンの既定パスです。automount が無効な場合は存在しないことがあります。トークンはローテーションされます。

</details>

## 実践問題

16. 必須の `DATABASE_URL` と、既定値 30 の `TIMEOUT` を使うスクリプトを書いてください。

<details>
<summary>解答を表示</summary>

```bash
#!/bin/bash
: "${DATABASE_URL:?DATABASE_URL required}"
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. 通常コンテナと init container の再起動回数を合計して 3 回以上になる Pod を JSON で出力するコマンドを書いてください。

<details>
<summary>解答を表示</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select(([(.status.containerStatuses[]?, .status.initContainerStatuses[]?) | .restartCount] | add // 0) >= 3)]'
```

</details>

18. bastion host 経由で YAML ファイルを同期する rsync コマンドを書いてください。

<details>
<summary>解答を表示</summary>

```bash
rsync -avzP --prune-empty-dirs --include='*/' --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## 応用問題

19. ノード診断スクリプトを書いてください。

<details>
<summary>解答を表示</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. ConfigMap の環境変数とボリュームマウントの違いを説明してください。

<details>
<summary>解答を表示</summary>

- 環境変数: Pod の起動時に読み込まれ、変更を反映するには Pod の再起動が必要です。
- ボリュームマウント: kubelet の同期周期とキャッシュ／watch の遅延後に更新が反映されます。アプリケーション側でファイルを再読み込みする必要があります。`subPath` マウントには更新が反映されません。

</details>

---

[学習資料に戻る](../../basics/02-linux-advanced.md)

## 検証用リファレンス

- https://kubernetes.io/docs/concepts/storage/volumes/#local
- https://kubernetes.io/docs/concepts/storage/storage-classes/#local
- https://kubernetes.io/docs/tasks/run-application/access-api-from-pod/
- https://kubernetes.io/docs/concepts/configuration/configmap/
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_wait/
- https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
- https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html
- https://download.samba.org/pub/rsync/rsync.1
- https://github.com/mikefarah/yq
- https://busybox.net/downloads/BusyBox.html
- https://github.com/docker-library/official-images/blob/master/library/busybox
