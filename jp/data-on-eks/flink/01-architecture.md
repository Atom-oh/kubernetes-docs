# パート 1: Kubernetes 上の Flink アーキテクチャ

> **最終更新日**: 2026 年 9 月 12 日。統合例: Flink 2.2.1 / Java 17 / Operator 1.15.0。

この章では、クラスタ内の各ロールとリソースのサイジングについて説明します。現在サポートされている EKS/Kubernetes バージョン、互換性のある kubectl、Flink ディストリビューション、クライアントからのアクセスを準備してください。パート 2 では、インストール、サービスアカウント、RBAC、Operator リソースを扱います。過去の Kubernetes 最小バージョンは、現在のサポート対象バージョンを示すものではありません。

## 1. JobManager、TaskManager、クライアント

| ロール | 責務 |
| --- | --- |
| クライアント | 提出方法に応じて、アプリケーションの `main()` を実行してジョブグラフを構築するか、クラスタでのアプリケーション実行を要求する |
| JobManager | Dispatcher、ResourceManager、ジョブごとの JobMaster が連携し、ジョブの提出、スロット、実行、チェックポイント、リカバリを調整する |
| TaskManager | タスクスレッドを実行し、データを交換・バッファリングして状態を処理する |
| Kubernetes ResourceManager | Native モードで Kubernetes API を通じて TaskManager Pod の作成・解放を要求する |

すべてのデプロイモードで JobManager が初期グラフを構築するわけではありません。Application モードでは JobManager 上で `main()` を実行します。通常の 2.2 Session CLI 提出では、クライアントがグラフを構築します。TaskManager は通常のオペレーターによるレコード処理を担いますが、アプリケーションの `main()` はユーザーコードです。JobManager が常に軽量であるとは限らない点に注意してください。

### スロット、オペレーターのチェーン化、スロット共有

タスクスロットは、TaskManager のリソース割り当て単位です。従来の固定スロット構成はマネージドメモリを分割しますが、**それだけで CPU が分離されるわけではありません**。各 TaskManager は、複数のタスクスレッドを実行できる JVM です。

Flink では、オペレーターのサブタスクを**チェーン化**して 1 つのタスク／スレッドにまとめられます。また、同じジョブの異なるタスクが**スロット共有グループ**を通じてスロットを共有することもできます。そのため、スロットが 4 つあってもオペレーターのサブタスク数が最大 4 つになるとは限りません。

| 前提の例 | 簡単なスロット計算 |
| --- | --- |
| source(4) → map(4) → sink(2)、すべて同じ共有グループ | 最大並列度にあたる 4 スロットで実行できる |
| source/map がグループ A、sink がグループ B | 両グループを同時に実行するには 4 + 2 = 6 スロットが必要 |

これらは、互換性のあるグループ／リソース要件を持つ単純なストリーミングの例です。バッチスケジューリング、きめ細かいリソースプロファイル、他のジョブ、チェーン化は別途考慮してください。1 TaskManager あたり 2 スロットの場合、4 スロットには少なくとも 2 台、6 スロットには少なくとも 3 台の TaskManager が必要です。CPU、ネットワーク、状態サイズ、余裕容量も満たす必要があります。

![オペレータータスクを共有できる、Native Flink の各ロール、チェックポイント調整、タスクスロット。](../../.gitbook/assets/en-data-on-eks-flink-01-architecture-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-flink-01-architecture-0.html)

## 2. Application/Session によるクラスタのライフサイクルと共有の選択

| モード | `main()` とクラスタのライフサイクル | 運用上の境界 |
| --- | --- | --- |
| Application | アプリケーション専用クラスタで `main()` を実行し、そのアプリケーションに合わせてクラスタを稼働させる | 1 回の `main()` で複数のジョブを作成できるため、常に 1 ジョブにつき 1 クラスタになるわけではない |
| Session | 既存クラスタにアプリケーション／ジョブを提出する。通常の 2.2 CLI ではクライアント上で `main()` を実行する | ジョブ間で JM/TM の容量を共有する。1 台の TM の障害が複数ジョブに影響する場合がある |

Application モードでは、アプリケーション間の JVM とライフサイクルを分けられますが、EKS ノード、ネットワーク、ストレージ、API クォータを完全に分離するわけではありません。同じアプリケーション内の複数ジョブもクラスタを共有します。2.2 のベースラインで説明されている Application HA は、単一の `execute` を実行するアプリケーションが対象です。複数ジョブのアプリケーションに 2.3 の改善を遡って適用せず、バージョンごとの制限を確認してください。

Session モードでは、割り当て済みのリソースを再利用してクラスタの起動コストを抑えられます。ただし、空きスロットがなくてもすぐに実行できる保証はなく、共有リソースの障害や競合も起こり得ます。

Per-Job は、クライアントがグラフを構築し、ジョブごとにクラスタを作成する旧来のモデルでした。Native Kubernetes の選択肢ではありません。ここで扱う Kubernetes の選択肢は、3 つのサポート対象モードではなく Application と Session です。

## 3. Native/Standalone は別のリソース管理軸

Application/Session と Native/Standalone は、異なる分類です。Operator 1.15.0 は Application/Session クラスタと、**Native/Standalone デプロイ**をサポートします。

| 項目 | Native | Standalone |
| --- | --- | --- |
| TM Pod の管理 | JM の Kubernetes ResourceManager が API を通じて Pod の作成・解放を要求する | Operator などの外部マネージャーが Kubernetes リソースを調整する |
| ランタイムの権限 | Native のリソース管理には Kubernetes API 権限が必要 | 外部管理を利用できる。HA などの追加機能で必要となる API 権限は個別に確認する |
| レプリカ数の変更 | Flink のスロット需要、アイドルポリシー、上限に基づいて制御される | Operator などのコントローラーで管理でき、YAML の手動編集だけに限られない |

通常は Native が既定の経路ですが、Standalone も単に廃止された旧モードではありません。`CR spec.mode` で選択し、リソース作成権限をどこに持たせるか、どの機能制限が適用されるかを評価してください。これによって Kubernetes API とのやり取りがすべてなくなったり、信頼できないコードが完全に分離されたりするわけではありません。

Native の TaskManager 割り当ては、リソースプロファイル、上限、アイドルタイムアウトにも依存します。2.2.1 の `resourcemanager.taskmanager-timeout` の既定値は 30 秒です。ジョブ完了や並列度の低下によって、Pod／ノードが厳密に比例した数だけすぐに削除されるわけではありません。Karpenter/Cluster Autoscaler は別のレイヤーでノード容量を管理します。

### 現行の CLI 提出形式

これは Operator を使わない Native Application の提出例です。パート 2 に従って namespace と Flink のサービスアカウント／RBAC を準備した後に実行してください。
同じクラスタ ID を Operator CR と CLI の両方に管理させないでください。組み込みのステートマシン例は長時間実行されるため、終了するバッチのスモークテストではありません。

```bash
# Illustration after namespace/ServiceAccount/RBAC preparation from Part 2.
# Use the Flink 2.2.1 distribution and a cluster ID not owned by an Operator CR.
./bin/flink run \
  --target kubernetes-application \
  -Dkubernetes.cluster-id=flink-cli-example \
  -Dkubernetes.container.image.ref=flink:2.2.1-java17 \
  -Dkubernetes.namespace=data-processing \
  -Dkubernetes.jobmanager.service-account=flink \
  -Dtaskmanager.numberOfTaskSlots=2 \
  -p 2 \
  local:///opt/flink/examples/streaming/StateMachineExample.jar
```

2.2.1 CLI では `run --target kubernetes-application` を使います。古い `run-application` アクションを使わないでください。現在のキーは `image.ref` であり、`container.image` は非推奨のエイリアスです。`local://` URI は、この例のイメージ内にある JAR を指定します。クライアント／JM の権限、イメージの取得、DNS、容量、実際の REST／ログの結果を確認してください。

## 4. ランタイムと検証の範囲

このベースラインでは Java 17 を推奨／既定のイメージとして使います。公式イメージのメタデータには Java 11 のバリアントも記載されているため、すべての 2.x Java 11 イメージが削除されたとするのは誤りです。2.2 のドキュメントでは Java 21 のサポートは実験的とされています。17 より新しい任意の JDK が同等にサポートされるわけではありません。アプリケーションのバイトコード、コネクター、リフレクションの設定も適合させてください。

アーキテクチャ、CLI のディスパッチと設定キー、Operator のソース、イメージタグのメタデータを確認しました。ここではクラスタの作成、CLI によるジョブの提出、HA、スループットのテストは実施していません。

## 参考資料

- [Flink のリリースとコネクターの互換性](https://flink.apache.org/downloads/)
- [Flink 2.2 のアーキテクチャ](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/concepts/flink-architecture/)
- [Flink 2.2 のデプロイモード](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/overview/)
- [Native Kubernetes デプロイ](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/resource-providers/native_kubernetes/)
- [Java の互換性](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/deployment/java_compatibility/)
- [Operator 1.15.0 のデプロイモード](https://github.com/apache/flink-kubernetes-operator/blob/release-1.15.0/docs/content/docs/custom-resource/overview.md)

[パート 2: Operator](02-flink-kubernetes-operator.md)

[README](README.md)

[クイズ](../../quizzes/data-on-eks/flink/01-architecture-quiz.md)
