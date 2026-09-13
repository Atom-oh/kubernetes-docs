# Observability Lab 02 クイズ

<span id="observability-lab-part-2-observability-stack-quiz"></span>

> **最終更新**: September 13, 2026

1. クロスクラスター収集ではどの endpoint を使用すべきですか？
   - A) 他方のクラスターの Service DNS のみ。
   - B) 実際のルーティング、DNS、TLS を備えたプライベート endpoint。
   - C) TLS 検証を常に無効にする。
   - D) kubeconfig ファイルを URL として使用する。

<details>
<summary>回答を表示</summary>

**解答: B) 実際のルーティング、DNS、TLS を備えたプライベート endpoint。**

NLB は TCP を転送し、サーバーはクライアント証明書を検証します。

</details>

---

2. CRI ログの解析順序は何ですか？
   - A) Docker JSON パーサーのみ。
   - B) Container/CRI パーサーの後に JSON 解析。
   - C) プレフィックス全体を JSON フィールドとして扱う。
   - D) すべての trace ID をストリームラベルにする。

<details>
<summary>回答を表示</summary>

**解答: B) Container/CRI パーサーの後に JSON 解析。**

アプリケーション本文から service/level/trace_id が保持されていることを確認します。

</details>

---

3. mTLS Prometheus はどのように probe すべきですか？
   - A) 証明書なしのデフォルト HTTPS probe は常に成功する。
   - B) クライアント証明書設定を使用する promtool exec probe。
   - C) すべての probe を削除する。
   - D) readiness を常に true で返す。

<details>
<summary>回答を表示</summary>

**解答: B) クライアント証明書設定を使用する promtool exec probe。**

実際の Operator マージと Prometheus の TLS ready/healthy 動作がテストされました。

</details>

---

4. 重要な Tempo3 設定変更はどれですか？
   - A) 古い Tempo2 の ingester 値のみをコピーする。
   - B) live-store/backend scheduler/worker と現在の chart 値を使用する。
   - C) Loki 設定をコピーする。
   - D) chart とアプリケーションのバージョンは常に同一である。

<details>
<summary>回答を表示</summary>

**解答: B) live-store/backend scheduler/worker と現在の chart 値を使用する。**

chart のレンダリングは、実際のバイナリ設定および起動とは別に確認します。

</details>

---

5. 単一インスタンスの Loki/Tempo ベースラインは何を意味しますか？
   - A) 本番 HA は自動的に実現される。
   - B) 永続性のあるラボインスタンスであり、HA/容量を保証するものではない。
   - C) ストレージコストは発生しない。
   - D) バックアップは自動的に保証される。

<details>
<summary>回答を表示</summary>

**解答: B) 永続性のあるラボインスタンスであり、HA/容量を保証するものではない。**

retention、PVC、クリーンアップ、障害の影響を確認します。

</details>

---

6. AIOps CloudWatch パスにはどの JSON が必要ですか？
   - A) クエリ文字列のみ。
   - B) service/level/trace_id を保持する構造化ログ。
   - C) すべての平文パスワード。
   - D) trace は自動的にログを作成する。

<details>
<summary>回答を表示</summary>

**解答: B) service/level/trace_id を保持する構造化ログ。**

raw_log の動作と実際の exporter の PutLogEvents メッセージがローカルで確認されました。

</details>

---

7. Grafana の correlation に必要なものは何ですか？
   - A) UI オプションを有効にするだけ。
   - B) 一致する UID、フィールド名、実際のデータ、retention。
   - C) 表示名を一致させるだけ。
   - D) trace_id を常に大文字にする。

<details>
<summary>回答を表示</summary>

**解答: B) 一致する UID、フィールド名、実際のデータ、retention。**

prometheus/loki/tempo の UID とエスケープされた derived-field 式を整合させます。

</details>

---

8. service Prometheus remote-write では exemplar はどのように扱われますか？
   - A) 常に自動的に保持される。
   - B) sendExemplars、受信/ストレージ、datasource リンクを確認する。
   - C) ラベルは自動的に trace を作成する。
   - D) すべてのリクエストが必ず保存される。

<details>
<summary>回答を表示</summary>

**解答: B) sendExemplars、受信/ストレージ、datasource リンクを確認する。**

転送オプションだけでなく、代表的な trace が存在することを確認します。

</details>

---

9. node-log DaemonSet の権限はどのように扱うべきですか？
   - A) hostPID とすべての capability を常に有効にする。
   - B) スコープを限定した読み取り専用 host mount、読み取り RBAC、明示的な root 例外のみを許可する。
   - C) 完全な cluster-admin。
   - D) host-log パスには権限上の影響がない。

<details>
<summary>回答を表示</summary>

**解答: B) スコープを限定した読み取り専用 host mount、読み取り RBAC、明示的な root 例外のみを許可する。**

namespace admission と実際のファイル権限を併せて検証します。

</details>

---

10. オプションの backend と永続キューはどのように記述すべきですか？
   - A) すべての backend はすでにデプロイされている。
   - B) 個別の検証が必要であり、ベースラインは永続的な offset/queue を保証しない。
   - C) 再起動時に損失/重複が発生することはない。
   - D) 24 時間の retention は 30 日間の SLO を証明する。

<details>
<summary>回答を表示</summary>

**解答: B) 個別の検証が必要であり、ベースラインは永続的な offset/queue を保証しない。**

成功として記録するのは、実際の設定と検証のみです。

</details>

---

[ガイドに戻る](../../../labs/observability/02-observability-stack-lab.md)
