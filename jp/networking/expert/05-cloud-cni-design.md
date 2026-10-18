# 5. クラウドと CNI のネットワーク設計ワークブック

> **最終更新日**: 2026年9月15日

**前提条件:** [プロトコル](01-protocol-projects.md)、[ルーティング](02-routing-policy-convergence.md)、[Linux の観測](04-linux-performance.md)、Kubernetes の Pod／Service／EndpointSlice の概念を理解していること。実環境を観測するには、承認済みの既存ラボアカウント／クラスターと、必要な読み取り権限が必要です。

**目標:** DNS からバックエンド、戻り経路まで、設計、観測、ポリシーを関連付けます。この章のコマンドは既存リソースを照会します。リソースを作成したり、障害を注入したりはしません。アカウントがない場合は、設計演習を完了し、結果を**設計レビュー**と明記してください。

AWS CLI と、クラスターに対応するバージョンの kubectl を準備し、ラボ用プロファイル／コンテキストを確認します。ツールがなければ、プラットフォーム固有の [AWS CLI のインストール手順](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)と [kubectl のインストール手順](https://kubernetes.io/docs/tasks/tools/)に従ってください。このワークブックでは、ツールのインストールや認証情報の発行が自動的に成功するとは想定しません。

## 1. AWS の範囲を質問に落とし込む {#design-questions}

[AWS Advanced Networking の公式試験範囲](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)は、クラウド／ハイブリッドの設計、実装、運用、セキュリティ、自動化を扱います。各領域を自分の設計に関する問いとして適用します。

| 領域 | 問い | 根拠 |
|---|---|---|
| アドレス指定／ルーティング | どの宛先プレフィックスと次ホップが適用され、戻り経路はあるか | VPC／サブネット／TGW ルートと実際の送信元／宛先アドレス |
| 名前解決 | どのリゾルバー、ゾーン、転送ルールが応答するか | クエリ名／種類、リゾルバー、応答、TTL、時刻 |
| エントリーポイント | DNS がどのフロントエンドを選択し、どのバックエンドが登録されているか | リスナー、ターゲットタイプ／ポート、ヘルスチェック、実際のターゲット |
| 分離 | 許可／禁止するフローをどの層が強制するか | SG／NACL／CNI ポリシーの範囲と、観測された適用状況 |
| 耐障害性 | コンポーネントが1つ故障したとき、どのフローに影響するか | 障害境界、代替経路、状態／復旧計画 |
| パフォーマンス／コスト | レイテンシ、スループット、アドレス容量、データ転送を左右する条件は何か | 測定間隔／方向／リソースと現在のコスト入力 |

試験範囲は学習項目を示すものであり、デプロイ手順の正解集でも、特定の設計におけるパフォーマンス保証でもありません。

## 2. 環境と権限を確認する {#inventory}

以下の名前を、**実際に承認されたラボの値**に置き換えてください。ここにある文字列は実際のアカウント情報ではありません。

```bash
LAB_AWS_PROFILE='REPLACE_WITH_LAB_PROFILE'
LAB_AWS_REGION='REPLACE_WITH_LAB_REGION'
LAB_CONTEXT='REPLACE_WITH_LAB_KUBERNETES_CONTEXT'
LAB_NAMESPACE='REPLACE_WITH_LAB_NAMESPACE'
LAB_SERVICE='REPLACE_WITH_LAB_SERVICE'
```

**オペレーターが承認した照会用ターミナル:**

```bash
aws --version
kubectl version --client
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  sts get-caller-identity
kubectl --context "$LAB_CONTEXT" auth can-i get services -n "$LAB_NAMESPACE"
kubectl --context "$LAB_CONTEXT" auth can-i list endpointslices.discovery.k8s.io \
  -n "$LAB_NAMESPACE"
```

アカウント、ロール、コンテキストがラボの対象と異なる場合は停止します。`no`、`AccessDenied`、期限切れの認証情報は、観測アクセスが利用できないことを示します。自動的に管理者権限を付与したり、別のアカウントを試したりしないでください。許可されたオペレーターに、必要最小限の根拠を依頼します。

実際のアカウント ID、ARN、IP、リソース名は承認済みのメモに保持してください。公開レポートでは一貫した別名を使います。設定の認証情報、シークレット、トークンを収集する必要はありません。

## 3. リクエストを実際のリソースに対応付ける {#request-path}

1件のリクエストを選び、ホスト名、プロトコル、ポート、時刻を特定します。次の項目は確認する関係を示しており、必ずしも個別の物理ホップではありません。

| 観測対象 | 関係 | よくある誤り |
|---|---|---|
| DNS | 選択されたリゾルバーが返すフロントエンドのアドレス | 名前解決を TCP／HTTP の成功とみなす |
| LB リスナー／ターゲットグループ | フロントエンドのプロトコル／ルールとターゲットの種類／ポート | リスナーとバックエンドのポートが同じだと決めつける |
| Service | セレクターまたは別途管理されたエンドポイント、port／targetPort | Service オブジェクトがあればエンドポイントもあると決めつける |
| EndpointSlice／Pod | 実際のアドレス／ポート、準備状態、ノード、タイムスタンプ | エンドポイントの準備状態を LB のヘルスと同じとみなす |
| CNI／ノード／VPC | アドレス指定、ルート、ポリシー、転送の実装 | すべての EKS コンピュートモードが同じ DaemonSet と経路を使うと決めつける |
| 戻り経路 | 応答の宛先、SNAT、状態追跡、ルーティング | 片方向の到達性から双方向の成功を結論付ける |

AWS Load Balancer Controller は AWS API を使う**コントロールプレーン**の調整役です。アプリケーションのリクエストが、このコントローラーの Pod を通るわけではありません。

通常の `ip` ターゲットは、登録済みのバックエンド IP に接続します。`instance` ターゲットでは、ノード／NodePort の経路を使います。サポートされるコンピュート／CNI の組み合わせ、実際の登録、プロキシの実装、トラフィックポリシーを確認してください。Service が表すのは論理的なエンドポイント選択です。ClusterIP を常に追加のパケットホップとして図示しないでください。[AWS のターゲットタイプの説明](https://docs.aws.amazon.com/eks/latest/best-practices/load-balancing.html)と[Kubernetes 仮想 IP の実装](https://kubernetes.io/docs/reference/networking/virtual-ips/)を合わせて確認してください。

### Service と EndpointSlice を観測する

```bash
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get service "$LAB_SERVICE" \
  -o jsonpath='{.spec.type}{"\n"}{.spec.selector}{"\n"}{.spec.ports}{"\n"}{.spec.externalTrafficPolicy}{"\n"}'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get endpointslices.discovery.k8s.io \
  -l "kubernetes.io/service-name=$LAB_SERVICE" -o json
```

**同じエンドポイントオブジェクト内で**アドレスと Condition を関連付けてください。アドレスと `ready` の配列を別々に平坦化し、根拠なく対応関係を作らないでください。`items: []` は、その選択条件でエンドポイントが観測されなかったことを意味します。DNS やファイアウォールが原因だと特定するものではありません。セレクターがない Service や、手動管理のエンドポイントも検討してください。

実際のセレクターを確認した後、関係する Pod だけを照会します。

```bash
LAB_SELECTOR='REPLACE_WITH_VERIFIED_KEY=VALUE'
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" \
  get pods -l "$LAB_SELECTOR" -o wide
kubectl --context "$LAB_CONTEXT" -n "$LAB_NAMESPACE" get networkpolicies
```

NetworkPolicy オブジェクトの一覧があっても、ポリシーエンジンが有効であることや、適用が機能していることは証明されません。CNI、コンピュートモード、サポート対象 API、選択された Pod、方向、ポート、実際のトラフィックをそれぞれ確認してください。他のポリシー CRD やマネージドポリシーについては、それぞれの所有者から根拠を得る必要があります。

### AWS ターゲットとルートを観測する

オペレーターが確認したターゲットグループと VPC を指定します。そのターゲットグループが選択した Service に対応することを示す根拠も記録してください。

```bash
LAB_TARGET_GROUP_ARN='REPLACE_WITH_VERIFIED_TARGET_GROUP_ARN'
LAB_VPC_ID='REPLACE_WITH_LAB_VPC_ID'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-groups --target-group-arns "$LAB_TARGET_GROUP_ARN" \
  --query 'TargetGroups[].{Type:TargetType,Port:Port,Protocol:Protocol,Vpc:VpcId,HealthPath:HealthCheckPath}'
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  elbv2 describe-target-health --target-group-arn "$LAB_TARGET_GROUP_ARN"
aws --profile "$LAB_AWS_PROFILE" --region "$LAB_AWS_REGION" \
  ec2 describe-route-tables --filters "Name=vpc-id,Values=$LAB_VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
```

`healthy` は設定されたヘルスチェックの結果であり、エンドユーザーから見た DNS／TLS／認可／リクエスト全体の経路を示すものではありません。フィールドが `null` の場合、まずそのプロトコル／設定でフィールドが必要かどうかを確認します。このワークブックの `ip`／`instance` モデルに含まれないターゲットタイプの場合は、経路モデルを改訂してください。

明示的なサブネットのルートテーブル関連付けがない場合は、メインテーブルが適用されているか確認します。宛先、ターゲット、ルートの状態を実際の送信元サブネットに関連付け、続いて宛先の戻り経路を調べてください。不足する権限やテレメトリを推測で埋めないでください。

## 4. ハイブリッド設計の演習 {#hybrid-design}

**設計シナリオ:** 本番 VPC A には共有 DNS／サービスが必要です。開発 VPC B から A のデータサービスへ直接アクセスしてはいけません。オンプレミスクライアントは指定された共有サービスだけにアクセスできます。実際のアドレス／アカウントが分からない場合は、別名を使ってください。

1. 送信元、宛先、プロトコル、許可／拒否の意図、戻り経路を記録します。
2. VPC／サブネット／TGW のルートテーブルとアタッチメントを区別します。
3. アタッチメントが検索に使うテーブルを選択する TGW の **association**（関連付け）と、学習したルートを追加する **propagation**（伝播）を区別します。アタッチメントは1つのテーブルに関連付けられ、複数のテーブルへルートを伝播できます。伝播しただけでは、アタッチメントがそのテーブルを使うことにはなりません。
4. ルーティング分離と SG／NACL／ワークロードポリシーの責務を説明します。
5. プライベートゾーン、リゾルバー、転送ルール、双方向の DNS 経路を特定します。
6. CIDR の重複、戻りルートの欠落、誤った伝播を一度に1つずつ検討し、影響を受けるフローを説明します。

[TGW の関連付け／伝播の説明](https://repost.aws/knowledge-center/transit-gateway-connect-vpcs-from-vpn)を確認し、実環境を[組織横断 VPC 接続](../05-cross-org-vpc-connectivity.md)と照らし合わせます。BGP ポリシーの知識は意図の表現に役立ちますが、オンプレミス機器のコマンドを TGW に直接適用するわけではありません。

## 5. 観測結果から推論する {#failure-workbook}

**提供された根拠、または承認を得て収集した根拠**を使います。これは分析演習であり、本番アカウントのポリシーを変更する手順ではありません。

| 観測結果 | 次に確認する項目 | 根拠のない結論 |
|---|---|---|
| DNS は応答するが TCP 接続に失敗する | ターゲット、ポート、ルート、アクセス制御、リスナー | DNS が正常なのでバックエンドも正常だとする |
| EndpointSlice は準備完了だがターゲットは unhealthy | 登録された IP／ポート、ヘルスチェック設定、経路 | 準備完了状態を LB のヘルスと同じとする |
| 同じノードでは成功し、ノード間では失敗する | 実際の CNI／ノード／VPC 経路、ポリシー、MTU、戻りルート | 「CNI の不具合」という1つの原因に決めつける |
| 小さいリクエストだけ成功する | パケットサイズ、PMTU 通知、再送、アプリケーションの条件 | あらゆる失敗を MTU の問題とする |
| TGW の片方向だけが機能する | 両側の関連付けとルートテーブル | 伝播だけで戻り経路も必ず成立するとする |

パケット／ホストの観測には、適切な権限と観測地点が別途必要です。リソースの `get` 出力を、測定済みのカーネル転送経路として説明しないでください。認可されたオペレーターからノード／Pod の名前空間における観測結果を得るか、別途準備されたラボガイドを使います。

## 6. 成果物と完了条件 {#completion}

- 許可／禁止フローのマトリクスと、順方向／戻り経路の図。
- 各コンポーネントの実際の役割: コントロールプレーン、ルーティング、ポリシー、アプリケーション。
- コンテキスト、ターゲット、タイムスタンプに紐付く Service／EndpointSlice／ターゲット／ルートの根拠。
- 少なくとも2つの仮説と、確定、否定、不明とした理由。
- デプロイ前チェック、観測範囲、復旧担当者、復旧後のチェック。

実環境の根拠がない場合は、**設計レビュー完了**と記録してください。クラウド運用の検証完了とはしません。この章の照会ではリソースを変更しないため、ネットワーク復元コマンドは必要ありません。保存した元データは、承認済みの保持／廃棄規則に従って管理してください。

## 関連資料

- [EKS ネットワーキング](../../eks/03-eks-networking-part1.md)、[VPC CNI](../01-vpc-cni.md)、[AWS Load Balancer Controller](../03-aws-lb-controller.md)
- [Pod ベンチマークの条件](../06-pod-network-benchmark.md)、[Cilium の可視性](../cilium/06-security-visibility.md)
- [EKS ネットワークポリシー](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [NLB／EKS のサポート条件](https://docs.aws.amazon.com/eks/latest/userguide/network-load-balancing.html)
- [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [AWS CLI のターゲットヘルス](https://docs.aws.amazon.com/cli/latest/reference/elbv2/describe-target-health.html)

[前へ: Linux パフォーマンス](04-linux-performance.md) · [クイズ](../../quizzes/networking/expert/05-cloud-cni-design-quiz.md) · [次へ: 自動化と評価](06-automation-capstone.md)
