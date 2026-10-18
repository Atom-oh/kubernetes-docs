# インフラストラクチャセットアップクイズ

> **関連ドキュメント**: [インフラストラクチャセットアップ](../../ops/01-infrastructure-setup.md)

## 多肢選択問題

### 1. このガイドで使う3つの運用レイヤーは何ですか？

- A) Network → Cluster → Platform
- B) Foundation → Workload → Database
- C) VPC → Pod → Container
- D) すべてのリソースを1つのstateで管理する

<details>
<summary>回答を表示</summary>

**回答: A) Network → Cluster → Platform**

00-sharedは別のブートストラップレイヤーです。NetworkはVPC、ClusterはEKS、PlatformはCoreDNS、Pod Identity、チームのアクセス権を管理します。stateを分離しても、VPCやDNSの障害が他のレイヤーに影響することはあります。

</details>

### 2. Terraform 1.10以降でS3バックエンドのネイティブロックを有効にする設定はどれですか？

- A) use_lockfile = true
- B) 常にDynamoDBテーブルを作成する
- C) バケットのバージョニングだけを有効にする
- D) すべてのレイヤーで同じkeyを使う

<details>
<summary>回答を表示</summary>

**回答: A) use_lockfile = true**

ネイティブロックにはS3の条件付き書き込みを使います。DynamoDBロックは既存構成からの移行などで関係しますが、S3のネイティブロックには不要です。ロック方式だけを変えても、stateの保存場所は移動しません。

</details>

### 3. terraform_remote_state のセキュリティについて、正しい説明はどれですか？

- A) 読み取り側はoutputsにしかアクセスできない
- B) バックエンドへのアクセスでstate全体を取得できる場合があるため、信頼境界を考慮する
- C) sensitive=true にするとIAMの読み取り権限が取り消される
- D) stateに機密値が含まれることはない

<details>
<summary>回答を表示</summary>

**回答: B) バックエンドへのアクセスでstate全体を取得できる場合があるため、信頼境界を考慮する**

式を通じて公開するのはroot outputsですが、元のstateにはそれ以外の情報も含まれます。信頼境界を越えて値を共有する場合は、必要な値だけを別途公開する方法も検討してください。

</details>

### 4. 標準的なリージョンEKSクラスターと組み込みAuto Modeプールについて、正しい説明はどれですか？

- A) コントロールプレーン用のサブネットは1つのAZだけでよい
- B) クラスター名をblueにするとワーカーがAZ-aに固定される
- C) EKSのサブネットは異なるAZを少なくとも2つ含む必要があり、ワーカーの配置制約は別に設計する
- D) サブネットにCluster=blueタグを付けるとノードが固定される

<details>
<summary>回答を表示</summary>

**回答: C) EKSのサブネットは異なるAZを少なくとも2つ含む必要があり、ワーカーの配置制約は別に設計する**

組み込みプールは、設定された複数のAZを利用できます。ワーカーを単一AZのセルに限定する場合は、NodePool/NodeClassで配置を設計し、他のセルに復旧用の容量を確保してください。

</details>

### 5. 組み込み compute_config.node_pools にgpuを追加するとどうなりますか？

- A) 正式な組み込みGPUプールが作成される
- B) gpuは組み込みプール名ではないため、適切なカスタムNodePoolを設定する
- C) 既存のノードがすぐGPUノードになる
- D) すべてのクラスターがGPU専用になる

<details>
<summary>回答を表示</summary>

**回答: B) gpuは組み込みプール名ではないため、適切なカスタムNodePoolを設定する**

組み込み名はgeneral-purposeとsystemです。この入力はプール名のリストであり、GPUプールを定義する任意のmapではありません。このガイドでは、カスタムNodePoolはGitOps側で管理します。

</details>

### 6. EKS Pod Identityの目的と必要条件について、正しい説明はどれですか？

- A) ECRからのPodイメージ取得を自動的に解決する
- B) 常にOIDCプロバイダーが必要である
- C) 対応するSDK呼び出しにロール認証情報を提供するため、association、trust、ノードのサポートが必要である
- D) associationによってServiceAccountとESOがインストールされる

<details>
<summary>回答を表示</summary>

**回答: C) 対応するSDK呼び出しにロール認証情報を提供するため、association、trust、ノードのサポートが必要である**

Auto Modeにはエージェント機能が含まれます。通常のEKSノードでは別途エージェントが必要な場合があります。対応するnamespace/ServiceAccountを設定し、kubeletがイメージをpullする権限と、アプリケーションがSDKで使う権限を区別してください。

</details>

### 7. 環境とクラスターのblue/greenごとにstateを分けるにはどうしますか？

- A) TF_DATA_DIRだけで、共有S3 keyを分離する
- B) バックエンドのbucket/keyと、それに対応する初期化ディレクトリをそれぞれ選ぶ
- C) 環境変数を変えるとprodのstateがdevへ移動する
- D) S3のバージョニングを無効にする

<details>
<summary>回答を表示</summary>

**回答: B) バックエンドのbucket/keyと、それに対応する初期化ディレクトリをそれぞれ選ぶ**

実際のstateの保存場所はバックエンド設定で決まります。TF_DATA_DIRは初期化メタデータ、モジュール、プロバイダーキャッシュを分けるもので、state keyの代わりにはなりません。ブートストラップ用のローカルstateも、アカウントと環境ごとに分離してください。

</details>

### 8. このAuto Modeの例では、CoreDNSとStorageClassをどのように扱いますか？

- A) どちらも設定なしで常に作成される
- B) Auto Modeのみの構成ではnode-local DNSを使い、混在ノードではCoreDNS Deploymentが必要で、StorageClassは別途作成する
- C) EBS CSIとPod Identityのエージェントを常に重複してインストールする
- D) CoreDNSのバージョンをlatestという文字列に固定する

<details>
<summary>回答を表示</summary>

**回答: B) Auto Modeのみの構成ではnode-local DNSを使い、混在ノードではCoreDNS Deploymentが必要で、StorageClassは別途作成する**

Auto Modeのみの構成では、CoreDNSはノードのシステムサービスとして動作します。ノードが混在するクラスターではDeploymentが残るため、Kubernetesとリージョンの互換性を確認し、アドオンのバージョンを固定してください。Auto ModeのStorageClassではebs.csi.eks.amazonaws.comを使います。

</details>

### 9. 管理者用のaccess entryを作るだけでkubectlアクセスは完了しますか？

- A) IAMのDescribeCluster権限とネットワークアクセスも自動的に付与される
- B) いいえ。該当principalとして認証し、IAM権限とプライベートAPIへの接続も準備する
- C) Terraformの呼び出し元は常に自動で管理者になる
- D) Platformレイヤーでも同じaccess entryを再作成する必要がある

<details>
<summary>回答を表示</summary>

**回答: B) いいえ。該当principalとして認証し、IAM権限とプライベートAPIへの接続も準備する**

この例では、クラスター作成者への自動管理者権限付与を無効にしています。EKS access policyが制御するKubernetes権限は、IAM権限とは別です。各principalのaccess entryは、いずれか1つのレイヤーで管理してください。

</details>

### 10. スモークテスト失敗時の処理として正しいものはどれですか？

- A) Pod作成エラーを `|| true` で隠す
- B) 既存のスモークテスト用namespaceを必ず削除する
- C) 失敗時はゼロ以外を返し、検証済みの一時namespaceだけをクリーンアップする
- D) PodがRunningなら常に正常とみなす

<details>
<summary>回答を表示</summary>

**回答: C) 失敗時はゼロ以外を返し、検証済みの一時namespaceだけをクリーンアップする**

このテストで確認するのはワークロードのスケジューリングとクラスターDNSであり、外部ロードバランサーの通信やすべてのアプリケーション依存関係ではありません。コンテナのREADY数とPodのReady conditionも別の状態です。

</details>
