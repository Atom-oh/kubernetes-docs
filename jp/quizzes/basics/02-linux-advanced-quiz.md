# Linux 運用スキルクイズ

このクイズでは、Kubernetes 環境で使用される Linux 運用スキルについての理解を確認します。

## 選択問題

1. どのコマンドが環境変数を子プロセスで利用可能にしますか？
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>回答を表示</summary>

**回答: B) export**

</details>

2. `.bashrc` はいつ実行されますか？
   - A) ログインシェルの場合のみ
   - B) すべてのシェルセッションで
   - C) 非ログインの対話型シェルで
   - D) 常に .bash_profile とともに

<details>
<summary>回答を表示</summary>

**回答: C) 非ログインの対話型シェルで**

</details>

3. `${REPLICAS:-3}` は何を意味しますか？
   - A) REPLICAS を 3 に設定する
   - B) REPLICAS が設定されていない場合は 3 を使用する
   - C) REPLICAS から 3 を減算する
   - D) エラー

<details>
<summary>回答を表示</summary>

**回答: B) REPLICAS が設定されていない場合は 3 を使用する**

</details>

4. `awk 'NR>1 {print $1}'` は何をしますか？
   - A) すべての行の最初のフィールドを出力する
   - B) 最初の行のみを出力する
   - C) ヘッダーを除外して最初のフィールドを出力する
   - D) 最初のフィールドを含む行を出力する

<details>
<summary>回答を表示</summary>

**回答: C) ヘッダーを除外して最初のフィールドを出力する**

</details>

5. `sed -i 's/old/new/g'` における `g` の役割は何ですか？
   - A) 大文字と小文字を区別しない
   - B) 行内のすべての一致を置換する
   - C) 1 回だけ置換する
   - D) 正規表現を有効にする

<details>
<summary>回答を表示</summary>

**回答: B) 行内のすべての一致を置換する**

</details>

6. `jq -r` の `-r` は何をしますか？
   - A) 再帰検索
   - B) 逆順
   - C) 引用符なしの生文字列出力
   - D) 読み取り専用

<details>
<summary>回答を表示</summary>

**回答: C) 引用符なしの生文字列出力**

</details>

7. `ssh -L 8080:localhost:80 user@server` は何を意味しますか？
   - A) サーバーの 8080 をローカルの 80 に転送する
   - B) ローカルの 8080 をサーバーの 80 に転送する
   - C) サーバーの 80 をローカルの 8080 に転送する
   - D) ローカルの 80 をサーバーの 8080 に転送する

<details>
<summary>回答を表示</summary>

**回答: B) ローカルの 8080 をサーバーの 80 に転送する**

</details>

8. vmstat における `wa` は何を表しますか？
   - A) Web application の CPU
   - B) I/O 待ち時間の割合
   - C) 警告数
   - D) アクティブプロセス

<details>
<summary>回答を表示</summary>

**回答: B) I/O 待ち時間の割合**

</details>

9. LVM Physical Volume を作成するコマンドはどれですか？
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>回答を表示</summary>

**回答: C) pvcreate**

</details>

10. `curl -s -o /dev/null -w "%{http_code}" URL` は何を出力しますか？
    - A) レスポンスボディ
    - B) レスポンスヘッダー
    - C) HTTP ステータスコード
    - D) レスポンスタイム

<details>
<summary>回答を表示</summary>

**回答: C) HTTP ステータスコード**

</details>

## 短答問題

11. 現在のシェルでファイルの内容を実行するコマンドは何ですか？

<details>
<summary>回答を表示</summary>

**回答: source (または .)**

</details>

12. JSON 解析ツールは何ですか？

<details>
<summary>回答を表示</summary>

**回答: jq**

</details>

13. bastion jump に使用される SSH オプションは何ですか？

<details>
<summary>回答を表示</summary>

**回答: ProxyJump (または -J)**

</details>

14. ディスク I/O を監視するコマンドは何ですか？

<details>
<summary>回答を表示</summary>

**回答: iostat**

</details>

15. Pod service account token へのパスは何ですか？

<details>
<summary>回答を表示</summary>

**回答: /var/run/secrets/kubernetes.io/serviceaccount/token**

</details>

## 実践問題

16. 必須の DATABASE_URL とデフォルト 30 の TIMEOUT を持つスクリプトを書いてください。

<details>
<summary>回答を表示</summary>

```bash
#!/bin/bash
: ${DATABASE_URL:?"DATABASE_URL required"}
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. 3 回以上再起動した Pods を JSON として出力するコマンドを書いてください。

<details>
<summary>回答を表示</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select([.status.containerStatuses[]?.restartCount] | add >= 3)]'
```

</details>

18. bastion 経由で yaml ファイルを同期する rsync コマンドを書いてください。

<details>
<summary>回答を表示</summary>

```bash
rsync -avzP --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## 応用問題

19. Node 診断スクリプトを書いてください。

<details>
<summary>回答を表示</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. ConfigMap env vars と volume mount の違いを説明してください。

<details>
<summary>回答を表示</summary>

- Environment Variables: Pod 起動時に読み込まれ、変更には再起動が必要
- Volume Mount: 自動更新（約 1 分）、再起動は不要

</details>

---

[学習資料に戻る](../../basics/02-linux-advanced.md)
