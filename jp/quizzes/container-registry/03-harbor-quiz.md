# Harborクイズ
> **最終更新日**: 2026年9月11日

1. Cloud Native Computing Foundation（CNCF）におけるHarborのステータスは何ですか？
   - A) Sandboxプロジェクト
   - B) Incubatingプロジェクト
   - C) Graduatedプロジェクト
   - D) Archivedプロジェクト

<details>
<summary>回答を表示</summary>

**回答: C) Graduatedプロジェクト**

**解説:**
HarborはCNCFのGraduatedプロジェクトであり、CNCFにおける最も高い成熟度です。このステータスは、採用の拡大、オープンなガバナンスプロセス、コミュニティの持続可能性とセキュリティに対する強い取り組みが示されたことを表します。Harborは2020年にGraduatedとなりました。

</details>

2. Harborのデフォルトの脆弱性スキャナーはどれですか？
   - A) Clair
   - B) Trivy
   - C) Anchore
   - D) Snyk

<details>
<summary>回答を表示</summary>

**回答: B) Trivy**

**解説:**
Harbor 2.2以降、デフォルトの脆弱性スキャナーはClairからTrivyに置き換わりました。TrivyはAqua Securityのオープンソーススキャナーで、OSパッケージとアプリケーション依存関係を含め、コンテナイメージの脆弱性を幅広く検出します。別のスキャナーを使いたい場合は、Harborのプラグイン方式にも対応しています。

</details>

3. Kubernetes環境にHarborをインストールする推奨方法はどれですか？
   - A) Docker Compose
   - B) YAMLマニフェストを手動で適用する
   - C) Helm chart
   - D) Operatorパターン

<details>
<summary>回答を表示</summary>

**回答: C) Helm chart**

**解説:**
公式のHarbor Helm chartは、Kubernetes環境への推奨インストール方法です。データベース、Redis、ストレージなど複雑な依存関係を管理し、幅広い設定項目を提供します。Docker ComposeはKubernetes以外へのデプロイや簡易テストには適していますが、本番のKubernetesデプロイには推奨されません。

</details>

4. HarborのRBACモデルでは、Project MaintainerはDeveloperと比べてどのような権限を持ちますか？
   - A) MaintainerはイメージをpushできるがDeveloperはできない
   - B) Maintainerはイメージをスキャン/削除でき、Developerはpush/pullできるがプロジェクトメンバーを管理できない
   - C) MaintainerとDeveloperの権限は同じ
   - D) Developerの方がMaintainerより多くの権限を持つ

<details>
<summary>回答を表示</summary>

**回答: B) Maintainerはイメージをスキャン/削除でき、Developerはpush/pullできるがプロジェクトメンバーを管理できない**

**解説:**
Harborのプロジェクト単位RBACには、Project Admin、Maintainer、Developer、Guestなどのロールがあります。Maintainerはイメージのスキャン/削除やラベル管理ができますが、プロジェクト設定の編集やメンバー管理はできません。Developerは管理者権限なしでイメージをpush/pullできます。Project Adminはメンバー管理を含め、すべての操作を実行できます。

</details>

5. Harborのrobot accountは何に使いますか？
   - A) 管理タスクを自動化する
   - B) CI/CDシステムに、限定されたスコープの認証情報を持つ非人間サービスアカウントを提供する
   - C) Harbor内部のコンポーネントを管理する
   - D) Harborインスタンス間でイメージを複製する

<details>
<summary>回答を表示</summary>

**回答: B) CI/CDシステムに、限定されたスコープの認証情報を持つ非人間サービスアカウントを提供する**

**解説:**
Robot accountは、CI/CDパイプラインなどの自動ワークフローでシステム間認証を行います。有効期限を設定でき、リポジトリのpush/pullなどのプロジェクトスコープ権限を持たせられます。人間ユーザーの認証情報は不要です。共有認証情報を避け、認証情報をローテーションしやすくするセキュリティのベストプラクティスに沿っています。

</details>

6. Harborのpushベースとpullベースのレプリケーションモードの違いは何ですか？
   - A) pushベースは速く、pullベースは信頼性が高い
   - B) pushベースはリモートレジストリへイメージを送り、pullベースはリモートレジストリから取得する
   - C) pushベースは手動実行が必要で、pullベースは自動実行される
   - D) 違いはなく、同じ機能の別名である

<details>
<summary>回答を表示</summary>

**回答: B) pushベースはリモートレジストリへイメージを送り、pullベースはリモートレジストリから取得する**

**解説:**
pushベースのレプリケーションはHarborからリモートレジストリへイメージを積極的に送ります（エッジ拠点への配布などに便利です）。pullベースはリモートレジストリからHarborへイメージを取得します（外部レジストリのミラーや災害復旧などに便利です）。手動およびスケジュール実行はpullワークフローにも対応します。イベントベースのレプリケーションはローカルHarborのアーティファクトイベントに従うもので、任意の外部レジストリの変更を監視するわけではありません。

</details>

7. Harborがイメージの署名と検証に連携するツールはどれですか？
   - A) GPG
   - B) CosignとNotation
   - C) OpenSSL
   - D) HashiCorp Vault

<details>
<summary>回答を表示</summary>

**回答: B) CosignとNotation**

**解説:**
HarborはCosignとNotationが生成した署名を保存します。Notary v1はHarbor 2.9で削除されました。レジストリ上で署名の有無を確認するポリシーは、Admission時に信頼できる署名鍵やIDに照らして検証することの代わりにはなりません。

</details>

8. Harborのproxy cache機能は何に使いますか？
   - A) DNS問い合わせをキャッシュする
   - B) Docker Hubなどのリモートレジストリのプルスルーキャッシュとして動作する
   - C) Helm chartの依存関係をキャッシュする
   - D) Harbor内部の処理を高速化する

<details>
<summary>回答を表示</summary>

**回答: B) Docker Hubなどのリモートレジストリのプルスルーキャッシュとして動作する**

**解説:**
Harborのproxy cacheは外部レジストリ用のキャッシュプロキシを作成します。ユーザーがHarbor経由でイメージをpullすると、ローカルにキャッシュされます。同じイメージへの以降のpullはHarborのキャッシュから提供されるため、外部帯域の利用とpull時間、アップストリームへのリクエストを減らせます。キャッシュミス、鮮度の確認、アップストリームアカウントの利用上限は引き続き適用されます。

</details>

9. エアギャップ環境にHarborをデプロイする場合、脆弱性データベースの更新に特別な配慮が必要なコンポーネントはどれですか？
   - A) Harbor coreサービス
   - B) データベース（PostgreSQL）
   - C) 脆弱性スキャナー（Trivy）
   - D) Redisキャッシュ

<details>
<summary>回答を表示</summary>

**回答: C) 脆弱性スキャナー（Trivy）**

**解説:**
エアギャップ環境ではTrivyがインターネットから脆弱性データベースをダウンロードできません。接続可能なマシンでTrivyデータベースを手動でダウンロードし、エアギャップ環境へ転送して、Trivyがオフラインデータベースを使うよう設定します。設定しないと古いデータを使ったスキャンになるか、スキャンが完全に失敗します。

</details>

10. Harborのガベージコレクションは何によって実行されますか？
    - A) 1時間ごとに自動で実行される
    - B) HarborのUI/APIから手動で実行するか、スケジュールを設定する
    - C) イメージを削除するたびに実行される
    - D) ストレージ使用量が80%に達すると実行される

<details>
<summary>回答を表示</summary>

**回答: B) HarborのUI/APIから手動で実行するか、スケジュールを設定する**

**解説:**
Harborのガベージコレクション（GC）は自動ではありません。Harbor管理者UIまたはAPIから手動で起動するか、スケジュール済みジョブとして設定する必要があります。GCは、どのマニフェストからも参照されなくなったイメージレイヤー（blob）を削除します。ストレージを解放できますが、レジストリ性能に影響する場合があるため、利用が少ない時間帯にスケジュールしてください。

</details>
