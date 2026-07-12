# Linux 操作スキルクイズ

このクイズでは、Kubernetes 環境で使用される Linux 操作スキルの理解度を確認します。

## 多肢選択問題

1. どのコマンドが環境変数を子プロセスで利用できるようにしますか？
   - A) set
   - B) export
   - C) declare
   - D) env

<details>
<summary>解答を表示</summary>

**解答: B) export**

</details>

2. `.bashrc` はいつ実行されますか？
   - A) ログインシェルの場合のみ
   - B) すべてのシェルセッション
   - C) 非ログインのインタラクティブシェル
   - D) 常に .bash_profile と一緒に

<details>
<summary>解答を表示</summary>

**解答: C) 非ログインのインタラクティブシェル**

</details>

3. `${REPLICAS:-3}` は何を意味しますか？
   - A) REPLICAS を 3 に設定する
   - B) REPLICAS が設定されていない場合は 3 を使用する
   - C) REPLICAS から 3 を引く
   - D) エラー

<details>
<summary>解答を表示</summary>

**解答: B) REPLICAS が設定されていない場合は 3 を使用する**

</details>

4. `awk 'NR>1 {print $1}'` は何をしますか？
   - A) すべての行の最初のフィールドを出力する
   - B) 最初の行のみを出力する
   - C) ヘッダーを除外して最初のフィールドを出力する
   - D) 最初のフィールドを持つ行を出力する

<details>
<summary>解答を表示</summary>

**解答: C) ヘッダーを除外して最初のフィールドを出力する**

</details>

5. `sed -i 's/old/new/g'` における `g` の役割は何ですか？
   - A) 大文字小文字を区別しない
   - B) 行内のすべての一致箇所を置換する
   - C) 1 回だけ置換する
   - D) 正規表現を有効にする

<details>
<summary>解答を表示</summary>

**解答: B) 行内のすべての一致箇所を置換する**

</details>

6. `jq -r` の `-r` は何をしますか？
   - A) 再帰検索
   - B) 逆順
   - C) クォートなしの raw string 出力
   - D) 読み取り専用

<details>
<summary>解答を表示</summary>

**解答: C) クォートなしの raw string 出力**

</details>

7. `ssh -L 8080:localhost:80 user@server` は何を意味しますか？
   - A) server の 8080 を local の 80 に転送する
   - B) local の 8080 を server の 80 に転送する
   - C) server の 80 を local の 8080 に転送する
   - D) local の 80 を server の 8080 に転送する

<details>
<summary>解答を表示</summary>

**解答: B) local の 8080 を server の 80 に転送する**

</details>

8. vmstat における `wa` は何を表しますか？
   - A) Web application CPU
   - B) I/O wait time の割合
   - C) 警告数
   - D) アクティブなプロセス

<details>
<summary>解答を表示</summary>

**解答: B) I/O wait time の割合**

</details>

9. どのコマンドが LVM Physical Volume を作成しますか？
   - A) lvcreate
   - B) vgcreate
   - C) pvcreate
   - D) fscreate

<details>
<summary>解答を表示</summary>

**解答: C) pvcreate**

</details>

10. `curl -s -o /dev/null -w "%{http_code}" URL` は何を出力しますか？
    - A) レスポンスボディ
    - B) レスポンスヘッダー
    - C) HTTP ステータスコード
    - D) レスポンスタイム

<details>
<summary>解答を表示</summary>

**解答: C) HTTP ステータスコード**

</details>

## 短答問題

11. 現在のシェルでファイルの内容を実行するコマンドは何ですか？

<details>
<summary>解答を表示</summary>

**解答: source (or .)**

</details>

12. JSON を解析するツールは何ですか？

<details>
<summary>解答を表示</summary>

**解答: jq**

</details>

13. bastion jump に使用される SSH オプションは何ですか？

<details>
<summary>解答を表示</summary>

**解答: ProxyJump (or -J)**

</details>

14. disk I/O を監視するコマンドは何ですか？

<details>
<summary>解答を表示</summary>

**解答: iostat**

</details>

15. Pod service account token のパスは何ですか？

<details>
<summary>解答を表示</summary>

**解答: /var/run/secrets/kubernetes.io/serviceaccount/token**

</details>

## 実践問題

16. 必須の DATABASE_URL とデフォルト値 30 の TIMEOUT を持つスクリプトを書いてください。

<details>
<summary>解答を表示</summary>

```bash
#!/bin/bash
: ${DATABASE_URL:?"DATABASE_URL required"}
TIMEOUT=${TIMEOUT:-30}
```

</details>

17. 3 回以上再起動した Pods を JSON として出力するコマンドを書いてください。

<details>
<summary>解答を表示</summary>

```bash
kubectl get pods -A -o json | jq '[.items[] | select([.status.containerStatuses[]?.restartCount] | add >= 3)]'
```

</details>

18. bastion 経由で yaml ファイルを同期する rsync コマンドを書いてください。

<details>
<summary>解答を表示</summary>

```bash
rsync -avzP --include='*.yaml' --exclude='*' -e "ssh -J bastion" /src/ user@host:/dest/
```

</details>

## 応用問題

19. node diagnostic script を書いてください。

<details>
<summary>解答を表示</summary>

```bash
#!/bin/bash
echo "=== System ===" && uptime && free -h && df -h
echo "=== kubelet ===" && systemctl status kubelet --no-pager
```

</details>

20. ConfigMap の環境変数と volume mount の違いを説明してください。

<details>
<summary>解答を表示</summary>

- Environment Variables: Pod 起動時に読み込まれ、変更には再起動が必要です
- Volume Mount: 自動更新され（約 1 分）、再起動は不要です

</details>

---

[学習資料に戻る](../../basics/02-linux-advanced.md)
