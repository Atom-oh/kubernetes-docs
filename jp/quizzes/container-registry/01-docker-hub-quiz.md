# Docker Hubクイズ
> **最終更新日**: 2026年9月11日

1. NAT配下のノードからDocker Hubへ匿名でイメージをpullする場合、利用量はどの単位で計上されますか？
   - A) 各Kubernetes Pod
   - B) 送信元IPv4アドレス、またはIPv6の/64サブネット
   - C) Kubernetes Namespace
   - D) 無制限のpull

<details>
<summary>回答を表示</summary>

**回答: B) 送信元IPv4アドレス、またはIPv6の/64サブネット**

**解説:**
同じNATアドレスを共有するノードは、匿名利用枠を共有する場合があります。現在のポリシーとレスポンスヘッダーで実際の上限とリセット期間を確認してください。認証済みアカウントの利用量計上と不正利用対策は別の仕組みです。

</details>

2. Kubernetesで非公開イメージをpullするためのDocker Hub認証情報は、どのリソースに保存しますか？
   - A) ConfigMap
   - B) `kubernetes.io/dockerconfigjson`型のSecret
   - C) ServiceAccount
   - D) PersistentVolumeClaim

<details>
<summary>回答を表示</summary>

**回答: B) `kubernetes.io/dockerconfigjson`型のSecret**

**解説:**
Kubernetesでは、レジストリの認証情報を`kubernetes.io/dockerconfigjson`型のSecretに保存します。このSecretをPod仕様の`imagePullSecrets`から参照するか、ServiceAccountに関連付けて自動的に注入します。

</details>

3. KubernetesクラスターでDocker Hubのレート制限を緩和するために推奨される方法は何ですか？
   - A) IPアドレスを増やす
   - B) プルスルーキャッシュまたはレジストリミラーを設定する
   - C) イメージのpullを無効にする
   - D) ローカルイメージだけを使う

<details>
<summary>回答を表示</summary>

**回答: B) プルスルーキャッシュまたはレジストリミラーを設定する**

**解説:**
プルスルーキャッシュにより、同じレイヤーのダウンロードを繰り返す回数を減らせます。ただし、キャッシュミス、変更可能なタグの確認、更新では引き続きアップストリームにアクセスするため、レート制限がなくなるわけではありません。

</details>

4. Namespaceのdefault ServiceAccountを使う新しいPodに、デフォルトのpull認証情報を設定するにはどうしますか？
   - A) kube-system NamespaceにSecretを追加する
   - B) Namespace内のdefault ServiceAccountに`imagePullSecrets`を設定する
   - C) クラスター全体のConfigMapを設定する
   - D) kubeletの設定を変更する

<details>
<summary>回答を表示</summary>

**回答: B) Namespace内のdefault ServiceAccountに`imagePullSecrets`を設定する**

**解説:**
そのServiceAccountに`imagePullSecrets`を追加します。そのServiceAccountを使って新たに作成されるPodは、個別のpull Secretリストを持っていなければ、このリストを引き継ぎます。既存のPod、別のServiceAccount、他のNamespaceには遡って反映されません。

</details>

5. Docker Official Imagesは、Docker Hub上の他のイメージと何が異なりますか？
   - A) 上流のイメージとドキュメントがレビューされる、厳選されたプログラムの対象である
   - B) 常に無料で使える
   - C) レート制限がない
   - D) 毎日自動で更新される

<details>
<summary>回答を表示</summary>

**回答: A) 上流のイメージとドキュメントがレビューされる、厳選されたプログラムの対象である**

**解説:**
Docker Official Imagesは、上流やコミュニティのメンテナーと連携して選定され、プログラムの基準に照らしてレビューされます。バッジが付いていても、特定のタグに脆弱性がないことは保証されません。選択したダイジェストとメンテナンス状況を確認してください。

</details>

6. Docker Verified Publisherイメージの目的は何ですか？
   - A) 無関係な投稿者が提供する無料イメージ
   - B) Dockerが検証した商用ソフトウェアベンダーのイメージ
   - C) 非推奨になったレガシーイメージ
   - D) セキュリティスキャンを回避するイメージ

<details>
<summary>回答を表示</summary>

**回答: B) Dockerが検証した商用ソフトウェアベンダーのイメージ**

**解説:**
Docker Verified Publisherイメージは、Dockerと提携して検証プロセスを受けた商用ソフトウェアベンダーが提供します。実際のソフトウェアベンダーがイメージを提供し、保守していることの確認につながり、サプライチェーンのセキュリティリスクを軽減できます。

</details>

7. 非公開リポジトリを無制限に利用できるDocker Hubのサブスクリプションはどれですか？
   - A) Freeプラン
   - B) Proのみ
   - C) Teamのみ
   - D) 各プランのポリシーに基づくPro、Team、Business

<details>
<summary>回答を表示</summary>

**回答: D) 各プランのポリシーに基づくPro、Team、Business**

**解説:**
利用量の表では、Pro、Team、Businessで非公開リポジトリが無制限とされていますが、各プランの条件と公正利用の条件が適用されます。Personalでは1つ利用できます。

</details>

8. Docker Hubの公開イメージを利用する際、どのようなサプライチェーンセキュリティ上のリスクがありますか？
   - A) イメージに脆弱性や悪意のあるコードが含まれる可能性がある
   - B) イメージは常に古い
   - C) イメージをスキャンできない
   - D) イメージのサイズが大きすぎる

<details>
<summary>回答を表示</summary>

**回答: A) イメージに脆弱性や悪意のあるコードが含まれる可能性がある**

**解説:**
Docker Hubの公開イメージには、既知の脆弱性や古い依存関係が含まれている場合があります。また、まれにタイポスクワッティング攻撃やメンテナーアカウントの侵害を通じて、悪意のあるコードが含まれることもあります。組織では使用前にイメージをスキャンし、Official ImagesやVerified Publishersを優先して、独自に厳選したベースイメージの保守も検討してください。

</details>

9. Docker Hubのイメージpull用Secretを作成する正しいkubectlコマンドはどれですか？
   - A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`
   - B) `kubectl create configmap my-secret --docker-server=docker.io`
   - C) `kubectl apply secret docker my-secret`
   - D) `kubectl set image secret my-secret`

<details>
<summary>回答を表示</summary>

**回答: A) `kubectl create secret docker-registry my-secret --docker-server=https://index.docker.io/v1/ --docker-username=USER --docker-password=TOKEN`**

**解説:**
このコマンドは`kubernetes.io/dockerconfigjson`型のSecretを作成します。例では、Docker Hubの標準的な認証情報キー`https://index.docker.io/v1/`を使っています。USERとTOKENは適切な認証情報に置き換え、コミットせずに、Secretを利用するPodと同じNamespaceに作成してください。

</details>

10. 2026年9月時点で、Docker Hub Automated Buildsについて適切な案内はどれですか？
    - A) すべての新しいCIパイプラインでデフォルトとして使う
    - B) 提供終了の発表はない
    - C) 非推奨機能のため、2027年4月1日より前に移行する
    - D) すべての無料アカウントで利用できる

<details>
<summary>回答を表示</summary>

**回答: C) 非推奨機能のため、2027年4月1日より前に移行する**

**解説:**
公式ドキュメントではAutomated Buildsは非推奨とされ、2027年4月1日の提供終了日が示されています。従来のネイティブ統合はGitHub/Bitbucketを使います。GitLab CIから独立してイメージをビルドし、pushすることもできます。

</details>
