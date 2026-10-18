# App Mesh と VPC Lattice のアーキテクチャクイズ

このクイズでは、サイドカー型とマネージドデータプレーン型の構造上の違い、リソースの対応付け、機能上の不足について理解度を確認します。

## 選択問題

1. 移行時の機能上の不足は、どのように評価すべきですか？
   - A) AWS はまだ実装していないだけで、すぐに追加される
   - B) App Mesh と Lattice の実際の API を比較する。プロキシの配置だけでは、機能が実現不可能とは証明できない
   - C) それらの機能は HTTP/2 では動作しない
   - D) IAM ポリシーで置き換えられるので不要である

<details>

<summary>回答を表示</summary>

**回答: B) App Mesh と Lattice の実際の API を比較する。プロキシの配置だけでは、機能が実現不可能とは証明できない**

**解説:**
一般的な Envoy/Istio の機能が、自動的に App Mesh の機能になるわけではありません。構成されている制御をすべて洗い出し、現行製品 API に不足があれば、アプリケーション/プロキシで代替する方法を選択してください。
</details>

2. App Mesh の VirtualNode は、VPC Lattice の Target Group に 1 対 1 で対応しないと言われるのはなぜですか？
   - A) VirtualNode はいくつも作成できますが、Target Group は 1 つしか作れない
   - B) VirtualNode が持つ ID、バックエンド、接続プール、異常検出の属性は、複数の場所に分散するか、対応先がなくなる
   - C) Target Group は Lambda をサポートしない
   - D) VirtualNode は Cloud Map に依存するため変換できない

<details>

<summary>回答を表示</summary>

**回答: B) VirtualNode が持つ ID、バックエンド、接続プール、異常検出の属性は、複数の場所に分散するか、対応先がなくなる**

**解説:**
VirtualNode には「このワークロードが何者か (ID)、どこに送るか (バックエンド)、どこでトラフィックを受信するか (リスナー、ヘルスチェック、接続プール、異常検出)」が 1 つのリソースにまとめられていました。Lattice ではターゲットの集合とヘルスチェックだけが Target Group になり、「どこに送るか」は認証ポリシーと IAM 権限、「誰であるか」は IAM ロールの問題になります。接続プールと異常検出に対応するリソースはありません。対応付けの表はリソース名を対応させるものであり、機能を対応させるものではありません。
</details>

3. 適切なオブザーバビリティ移行作業はどれですか？
   - A) サーキットブレーカー。実装が最も難しいから
   - B) アプリケーションのトレースを維持し、旧プロキシが実際に提供していたテレメトリを置き換える
   - C) トラフィックミラーリング。代替手段がまったくないから
   - D) フォールトインジェクション。本番のインシデント対応に不可欠だから

<details>

<summary>回答を表示</summary>

**回答: B) アプリケーションのトレースを維持し、旧プロキシが実際に提供していたテレメトリを置き換える**

**解説:**
Lattice にはネイティブのトレーススパンはありませんが、アプリケーションスパンは引き続き利用できます。Lattice のリクエスト ID、アクセスログのタイミング、クライアント/サーバーでの観測と関連付けてください。
</details>

4. AWS Gateway API Controller が停止するとどうなりますか？
   - A) すべてのトラフィックが直ちにブロックされる
   - B) トラフィックは流れ続けるが、新しく起動した Pod は Target に登録されず、停止した Pod も登録解除されない
   - C) Lattice Service が自動的に削除される
   - D) IAM 認証が無効になる

<details>

<summary>回答を表示</summary>

**回答: B) トラフィックは流れ続けるが、新しく起動した Pod は Target に登録されず、停止した Pod も登録解除されない**

**解説:**
Controller の主な役割は、Kubernetes の宣言状態と Lattice の実ターゲット一覧を同期させることです。`backendRefs` が参照する Service のエンドポイント変更を監視し、Target を登録/登録解除します。停止すると、Lattice は最後に認識したターゲット一覧を使ってトラフィックの転送を続けますが、一覧が古くなります。そのため Controller Deployment の可用性と IAM 権限は、データパスの信頼性に直接関係します。
</details>

5. ingress-nginx も実行している環境では、移行範囲について正しい説明はどれですか？
   - A) ingress-nginx も必ず Lattice に置き換える必要がある
   - B) 現在の AWS Gateway API Controller は Lattice 経由の East-West トラフィックだけを対象としているため、ingress-nginx が扱う North-South のイングレスは範囲外であり、両経路が共存するのが通常の結果である
   - C) ingress-nginx と Lattice は同時に使用できない
   - D) Gateway API Controller も North-South トラフィックを扱うため、ingress-nginx をすぐに削除すべきである

<details>

<summary>回答を表示</summary>

**回答: B) 現在の AWS Gateway API Controller は Lattice 経由の East-West トラフィックだけを対象としているため、ingress-nginx が扱う North-South のイングレスは範囲外であり、両経路が共存するのが通常の結果である**

**解説:**
Kubernetes Gateway API は North-South (Ingress) と East-West (Mesh) の両方を扱うように設計されていますが、現在の AWS Gateway API Controller は East-West のみを対象とします。ALB/NLB 型の North-South 機能は AWS Load Balancer Controller の対象です。そのため、ingress-nginx が提供しているイングレス経路はこの移行範囲に含まれません。East-West トラフィックだけが Lattice に移行し、両方の経路が共存する構成が想定されます。
</details>

6. Lattice 環境で Pod readiness gate を使うのはなぜですか？
   - A) Pod の CPU 使用量を上限設定するため
   - B) Lattice Target Group のヘルス状態が Healthy になるまで Pod を Ready にせず、新しい Pod が正常になる前にローリングアップデートで古い Pod が終了されるのを防ぐため
   - C) IAM 認証情報の準備ができるまでトラフィックを遮断するため
   - D) Envoy サイドカーのインジェクションを待つため

<details>

<summary>回答を表示</summary>

**回答: B) Lattice Target Group のヘルス状態が Healthy になるまで Pod を Ready にせず、新しい Pod が正常になる前にローリングアップデートで古い Pod が終了されるのを防ぐため**

**解説:**
Lattice Target Group がまだ Healthy と判断していなくても、Kubernetes は Pod を Ready とみなす場合があります。その状態でローリングアップデートにより古い Pod が終了すると、正常な Target が 1 つもない時間が生じます。Pod readiness gate は Lattice のヘルス判定を Pod の Ready 条件に結び付けてこれを防ぐ、移行中のダウンタイムをゼロに近づける重要な仕組みです。
</details>
