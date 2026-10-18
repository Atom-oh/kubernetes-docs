# EKS 上の Agent Sandbox クイズ

このクイズでは、Agent Sandbox v1.0.6 API（`v1beta1`）と、Amazon EKS 上での既定の動作を確認します。関連する章: [EKS 上の Agent Sandbox](../../ai-ml/09-agent-sandbox.md)。

## 選択問題

### 1. 信頼できないコードを分離するために、Agent Sandbox 自体が提供するものは何ですか？

- A. すべての Sandbox に組み込みの microVM ハイパーバイザーを提供する
- B. Pod のオーケストレーションを行う。分離は Pod の `RuntimeClass`（gVisor や Kata Containers など）で実現する
- C. 信頼できないコードを実行しても `runc` を安全にする seccomp プロファイル
- D. 専用 EC2 インスタンスへの配置を自動で行う

<details>
<summary>解答を表示</summary>

**解答: B. Pod のオーケストレーションを行う。分離は Pod の `RuntimeClass`（gVisor や Kata Containers など）で実現する**

**解説:**
このプロジェクトは、自らを sandbox orchestrator と説明しています。コンテナエスケープの脅威を軽減するには、`runtimeClassName` でセキュアなランタイムを選択し、ユーザーが削除できないよう `SandboxTemplate` で設定することを推奨しています。既定の `runc` では、sandbox 内のコードがノードカーネルを共有します。

</details>

### 2. Template で `networkPolicy` を省略し、`networkPolicyManagement: Managed` のままにすると、生成されるポリシーについて正しい説明はどれですか？

- A. CoreDNS を含め、すべての送信トラフィックを許可する
- B. `agent-sandbox-system` 内の `sandbox-router` Pod からの受信だけを許可し、プライベートではない IPv4/IPv6 範囲への送信を許可する。CoreDNS は許可しない
- C. 同じ namespace のすべての Pod からの受信を許可する
- D. VPC CIDR への送信だけを許可する

<details>
<summary>解答を表示</summary>

**解答: B. `agent-sandbox-system` 内の `sandbox-router` Pod からの受信だけを許可し、プライベートではない IPv4/IPv6 範囲への送信を許可する。CoreDNS は許可しない**

**解説:**
既定の設定では、`0.0.0.0/0` から `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16` を除外し、`::/0` から `fc00::/7` と `fe80::/10` を除外します。内部サービスの探索を防ぐため、CoreDNS は意図的にブロックされます。そのため、ポリシーまたは Pod のリゾルバーを変更するまで、パブリックホスト名を名前解決できません。

</details>

### 3. IPv4 の EKS クラスタでは、例外を追加しない限り、既定の Managed ポリシーでも sandbox から到達できるアドレスはどれですか？

- A. `169.254.169.254` の IMDS
- B. `169.254.170.23` の EKS Pod Identity Agent
- C. VPC CNI のカスタムネットワーキングで使うセカンダリ CIDR `100.64.0.0/10` 内の Pod
- D. `10.0.12.34` の Pod

<details>
<summary>解答を表示</summary>

**解答: C. VPC CNI のカスタムネットワーキングで使うセカンダリ CIDR `100.64.0.0/10` 内の Pod**

**解説:**
既定の例外リストが対象とするのは、RFC1918 とリンクローカルの範囲だけです。`100.64.0.0/10` は RFC1918 ではないため、この範囲内の内部アドレスは許可される `0.0.0.0/0` ルールに含まれます。IMDS と Pod Identity Agent は `169.254.0.0/16` 内にあり、`10.0.12.34` は `10.0.0.0/8` 内にあるため、残りの 3 つはすべてブロックされます。IPv6 クラスタでは状況が異なります。IPv4 ルールは無視され、VPC のグローバルユニキャストアドレスは除外されず、`ENABLE_V4_EGRESS` 経由の IPv4 送信はフィルターされません。

</details>

### 4. namespace `agent-orchestrator` 内の Agent Pod が SDK のクラスタ内モードを使い、Managed ポリシーの Template から作成された sandbox Pod に直接接続します。どうなりますか？

- A. クラスタ内のトラフィックはフィルターされないため、接続できる
- B. CNI がポリシーを適用する構成では、Template のポリシーにその namespace からの受信ルールを追加するまでブロックされる
- C. IPv6 経由でのみ接続できる
- D. SDK が自動的にパブリック Gateway にフォールバックする

<details>
<summary>解答を表示</summary>

**解答: B. CNI がポリシーを適用する構成では、Template のポリシーにその namespace からの受信ルールを追加するまでブロックされる**

**解説:**
既定の受信ルールで許可されるのは router だけです。Service DNS または Pod IP を使った直接接続は router を経由しないため、明示的な受信ルールが必要です。EKS では、VPC CNI でネットワークポリシーの適用が有効になっていることが前提です。有効でなければ、ポリシーは何もブロックしません。

</details>

### 5. warm Sandbox を再利用せず、コールドスタートを強制する `SandboxClaim` フィールドはどれですか？

- A. `warmPoolRef`
- B. `lifecycle.shutdownTime`
- C. `env` または `volumeClaimTemplates`
- D. `lifecycle.ttlSecondsAfterFinished`

<details>
<summary>解答を表示</summary>

**解答: C. `env` または `volumeClaimTemplates`**

**解説:**
環境変数とボリュームは Pod の作成前に存在している必要がありますが、warm Pod はすでに作成済みです。どちらかを指定する Claim は、pool の Template から新たにコールド作成されます。また、Template で利用が許可されている必要があります。`envVarsInjectionPolicy` と `volumeClaimTemplatesPolicy` は、どちらも既定で `Disallowed` です。

</details>

### 6. ベアメタルインスタンスを使わずに EKS 上で Kata Containers を動かしたい場合、ドキュメントに記載された機能に合致する方法はどれですか？

- A. カスタム containerd ランタイムを使う EKS Auto Mode
- B. Fargate。各 Pod がすでに VM で実行され、Managed NetworkPolicy もそこで適用されるため
- C. Karpenter v1.13.0 以降で、M8i、C8i、R8i などのサポート対象ファミリーに `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled` を設定し、そのノードに紐付けた RuntimeClass を使う
- D. すべての Graviton インスタンスが nested virtualization を提供するため、任意のインスタンスを使う

<details>
<summary>解答を表示</summary>

**解答: C. Karpenter v1.13.0 以降で、M8i、C8i、R8i などのサポート対象ファミリーに `EC2NodeClass.spec.cpuOptions.nestedVirtualization: enabled` を設定し、そのノードに紐付けた RuntimeClass を使う**

**解説:**
EC2 は、一部の Intel ファミリー（M7i/C7i/R7i、M8i/C8i/R8i など）で nested virtualization をサポートします。Karpenter は `nested-virtualization` を報告するインスタンスタイプを選別します。Auto Mode では AMI とコンテナランタイムが管理されているため、Kata を追加できません。VPC CNI は Fargate Pod にネットワークポリシーを適用できません。RuntimeClass に `scheduling` を設定し、準備済みノードだけに Pod が配置されるようにしてください。

</details>

### 7. `operatingMode` を `Running` から `Suspended` に変更すると、Sandbox はどうなりますか？

- A. Sandbox オブジェクト、Pod、PVC がすべて削除される
- B. Pod は削除されるが、Sandbox オブジェクトと PVC は残る。`Suspended` 条件は `PodTerminating` から `PodTerminated` に遷移する
- C. 同じノード上で Pod がメモリ内に保持される
- D. headless Service だけが削除される

<details>
<summary>解答を表示</summary>

**解答: B. Pod は削除されるが、Sandbox オブジェクトと PVC は残る。`Suspended` 条件は `PodTerminating` から `PodTerminated` に遷移する**

**解説:**
Suspended は PVC を使う方式です。コンピューティングは停止し、ストレージは残ります。`Ready` は reason `SandboxSuspended` で False になります。EKS では EBS ボリュームは AZ に紐付くため、再開する Pod もそのボリュームがある Availability Zone にスケジュールする必要があります。

</details>

### 8. Agent Sandbox v0.4.x を実行しているクラスタを v1.0.6 にアップグレードする前に、何を行う必要がありますか？

- A. 何もしなくてよい。v1.0.6 の `kubectl apply` がオブジェクトを自動変換する
- B. v0.5.2 以降にアップグレードし、保存済みオブジェクトを `v1beta1` に移行して、各 CRD の `status.storedVersions` に `v1beta1` だけが記載されていることを確認する
- C. すべての CRD を削除して作り直す
- D. v1.0.6 で conversion webhook を再度有効にする

<details>
<summary>解答を表示</summary>

**解答: B. v0.5.2 以降にアップグレードし、保存済みオブジェクトを `v1beta1` に移行して、各 CRD の `status.storedVersions` に `v1beta1` だけが記載されていることを確認する**

**解説:**
v1.0.0 では `v1alpha1` と conversion webhook が削除され、v0.5.0 より前からの直接アップグレードはサポートされません。`storedVersions` に `v1alpha1` が残っていると、API server がアップグレードを拒否します。CRD を削除すると、すべての Sandbox、Claim、Template、Pool が連鎖削除されます。

</details>

### 9. `sandbox-router` を通じて sandbox にブラウザーからアクセスさせたい場合、章の EKS ガイダンスに沿う設計はどれですか？

- A. インターネット向け NLB を持つ `LoadBalancer` 型の `Service` を使い、router の既定の `AllowAll` authorizer を使う
- B. CloudFront → CloudFront VPC origin → 内部 ALB → `sandbox-router-svc` の経路を使い、scope を限定した token v2 認可を設定し、ALB または Envoy 層でレート制限を行う
- C. 各 sandbox Pod にパブリック IP を付ける
- D. 本番環境で、すべてのユーザーのノート PC から port-forward する

<details>
<summary>解答を表示</summary>

**解答: B. CloudFront → CloudFront VPC origin → 内部 ALB → `sandbox-router-svc` の経路を使い、scope を限定した token v2 認可を設定し、ALB または Envoy 層でレート制限を行う**

**解説:**
パブリックなのは CloudFront だけです。ALB は内部向けで、そのセキュリティグループでは CloudFront VPC origin のセキュリティグループまたはマネージドプレフィックスリストからの通信だけを許可します。router の既定の authorizer は `AllowAll` で、WebSocket などアップグレードされた接続の接続数を制限しません。そのため、公開する前に認可と制限を構成する必要があります。

</details>

### 10. v1.0.6 で、名前が 70 文字の Sandbox に `spec.service: true` を設定するとどうなりますか？

- A. 何も変わらず、以前と同様に動作する
- B. CEL ルールによってアドミッション時に拒否される。既存オブジェクトも、`spec.service` を解除するか、63 文字以下の名前で Sandbox を作り直すまで、すべての更新に失敗する
- C. コントローラーが Service 名を自動的に切り詰める
- D. Sandbox が `v1alpha1` に変換される

<details>
<summary>解答を表示</summary>

**解答: B. CEL ルールによってアドミッション時に拒否される。既存オブジェクトも、`spec.service` を解除するか、63 文字以下の名前で Sandbox を作り直すまで、すべての更新に失敗する**

**解説:**
headless Service の名前は Sandbox の名前と同じです。Service 名は最大 63 文字の DNS-1035 ラベルであるため、このような Sandbox は Ready になりませんでした。v1.0.6 ではアドミッション時に失敗が報告されます。このルールはオブジェクト全体を対象にし、既存オブジェクトは除外されないため、状態の更新も失敗します。

</details>
