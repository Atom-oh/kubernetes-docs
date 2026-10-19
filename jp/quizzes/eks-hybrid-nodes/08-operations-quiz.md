# EKS Hybrid Nodes の運用クイズ

> **最終更新**: 2026年9月13日

> **関連ドキュメント**: [運用](../../eks-hybrid-nodes/08-operations.md)

## 選択式問題

<span id="_1-what-is-the-recommended-tool-combination-for-node-monitoring-in-hybrid-nodes-environments"></span>

### 1. Hybrid Nodes 環境で、ホストのメトリクスとダッシュボードを提供できる組み合わせはどれですか？

- A) メモ帳と手作業での記録
- B) Prometheus、Grafana、適切に構成した Node Exporter
- C) メール通知だけ
- D) ログの手作業での確認だけ

<details>
<summary>回答を表示</summary>

**回答: B) Prometheus、Grafana、適切に構成した Node Exporter**

**解説:**
Prometheus はメトリクスを収集し、Grafana は表示します。Node Exporter はホストのメトリクスを公開し、DCGM Exporter は対応する GPU メトリクスを公開します。Alertmanager はアラートを振り分けます。これは利用可能な構成の一例であり、唯一の選択肢ではありません。確認済みの chart／add-on を導入し、ホストの mount、ID、配置、TLS、認証、実際の scrape target を検証してください。対応する selector と template label が一致しない部分的な DaemonSet は、機能する構成ではありません。利用できない EC2 IMDS を通じて Container Insights が Hybrid ホストのメトリクスを提供するわけではありません。

</details>

<span id="_2-how-do-you-check-when-kubelet-certificate-renewal-is-needed"></span>

### 2. 構成済みのノード証明書またはサービス証明書の有効期限は、どのように確認すべきですか？

- A) 証明書は期限切れにならないと想定する
- B) OpenSSL で実際の証明書を調べ、発行者と更新の担当主体を確認する
- C) Node が NotReady になるまで待つ
- D) すべての証明書を毎日手動で更新する

<details>
<summary>回答を表示</summary>

**回答: B) OpenSSL で実際の証明書を調べ、発行者と更新の担当主体を確認する**

**解説:**
まず、kubelet の serving/client 証明書、EKS コントロールプレーン CA、Harbor TLS、IAM Roles Anywhere のホスト証明書を区別してください。Hybrid IAM 認証を使っていても、`kubelet-client-current.pem` が存在するとは限りません。kubeadm の更新コマンドは EKS コントロールプレーンを管理しません。有効期限の確認は、証明書チェーン、ホスト名、失効状態、実際の認証確認とは別です。`serverTLSBootstrap` だけでは serving CSR は承認されず、IAM Roles Anywhere 証明書も更新されません。
```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file}"
openssl x509 -in "$CERT_PATH" -checkend 604800 -noout
```
この例は、有効期限まで 7 日以内になると警告します。証明書の有効期間と更新ポリシーに応じてしきい値を選んでください。ファイルがない場合や無効な場合は失敗します。

</details>

<span id="_3-what-is-the-first-troubleshooting-step-when-kubelet-is-not-responding-on-a-hybrid-node"></span>

### 3. Hybrid Node で kubelet が応答しなくなった場合、最初に何を調べるべきですか？

- A) クラスター全体を再起動する
- B) 対応するホスト上の service の状態、直近のログ、関連する依存先を調べる
- C) 調査せずに代替ノードを作成する
- D) すべての Pod を削除する

<details>
<summary>回答を表示</summary>

**回答: B) 対応するホスト上の service の状態、直近のログ、関連する依存先を調べる**

**解説:**
登録された Node と実際のホストを特定し、kubelet/containerd の状態、直近の限られた範囲の journal、ディスク／メモリ、検証済みのネットワーク／認証情報経路を調べてください。TLS を無効化したり、レジストリの認証情報を出力したりしないでください。確認対象の Hybrid CLI に存在しない `nodeadm reset` も実行しないでください。再起動や再登録は別途判断する復旧手順です。診断情報を保持し、ライフサイクルガイドに従ってください。
```bash
# On the verified host, not a hostname guessed from its Kubernetes Node name:
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' --no-pager -n 200
```

</details>

<span id="_4-what-command-is-used-to-safely-move-workloads-for-node-maintenance"></span>

### 4. 計画的なノード保守で、ワークロードの退避を要求するコマンドはどれですか？

- A) `kubectl delete node`
- B) `kubectl drain`
- C) `kubectl cordon` だけ
- D) `kubectl delete pods --all`

<details>
<summary>回答を表示</summary>

**回答: B) `kubectl drain`**

**解説:**
`drain` は Node をスケジュール不可にし、通常は Eviction API を使って、該当する PDB を尊重しながら退避を要求します。コントローラーが代替 Pod を作成することはありますが、メモリを移動するコマンドではなく、アプリケーションの継続稼働を保証するものでもありません。drain の前に、余力容量、配置、ストレージ、ローカルデータを確認してください。Eviction を常態的に回避したり、`emptyDir` のデータを破棄したり、すべての Pod termination period を上書きしたりしないでください。ホスト／ワークロードの検証に成功し、かつ元々スケジュール可能だった Node だけを uncordon してください。

| コマンド | 範囲 |
| --- | --- |
| `cordon` | 通常の新規スケジューリングを防ぐ |
| `drain` | cordon を行い、例外／制約の範囲で Eviction を要求する |
| `uncordon` | スケジューリングを再開する。正常性の確認にはならない |

`minAvailable: 2` の PDB で自発的な中断を 1 つ許可するには、該当する正常なレプリカが 3 つ必要です。PDB はノード障害や、あらゆるアプリケーションエラーを防ぐものではありません。

</details>

<span id="_5-what-is-the-recommended-solution-for-centralizing-logs-from-hybrid-nodes"></span>

### 5. Hybrid ワークロードのログを集約できる方法はどれですか？

- A) すべてのログを手作業でコピーする
- B) 設定済みの Fluent Bit/Fluentd collector と、保護された中央 backend を使う
- C) ログを収集しない
- D) コンソール出力だけを読む

<details>
<summary>回答を表示</summary>

**回答: B) 設定済みの Fluent Bit/Fluentd collector と、保護された中央 backend を使う**

**解説:**
実際のコンテナランタイムのログパスと parser、Kubernetes metadata の権限、buffer/checkpoint、retry、認証済み TLS 出力を構成してください。containerd は一般に `/var/log/containers` の symlink から `/var/log/pods` を参照します。古い Docker 専用の `/var/lib/docker/containers` manifest をそのまま使わないでください。collector には適切な読み取り専用ホスト mount と、意図した状態保存ポリシーが必要です。ログ収集によって損失がゼロになる保証はありません。
```text
Hybrid Nodes → configured collectors → CloudWatch Logs / Loki / Elasticsearch
                       ↓
              protected buffers and checkpoints
```

</details>

<span id="_6-what-is-the-default-wait-time-before-automatically-rescheduling-pods-to-other-nodes-when-a-node-fails"></span>

### 6. デフォルトの Admission 動作で、明示的な上書きがない場合、通常の Pod に not-ready と unreachable 用として追加される NoExecute toleration の期間はどれですか？

- A) 0 秒
- B) 30 秒
- C) 300 秒
- D) 1 時間

<details>
<summary>回答を表示</summary>

**回答: C) 300 秒**

**解説:**
明示的に設定されていない限り、Kubernetes は通常、両方の taint に `tolerationSeconds: 300` を追加します。これは taint を許容する期間であり、ノード障害から正確に 5 分後に代替ワークロードが Ready になる保証ではありません。障害検出、taint の付与、コントローラーの動作、容量、volume、起動処理にも制約があります。DaemonSet の Pod は通常、これらの taint を無期限に許容します。期間を短くしても、ネットワーク分断中に古いプロセスが停止した証拠にはなりません。stateful writer には fencing が必要な場合があります。
```yaml
# Fragment under Pod spec or a workload's PodTemplate.spec, not a complete Pod:
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 60
```
指定例の 60 秒への短縮は、可用性とデータ安全性を検証したうえで判断してください。60 秒の復旧 SLO を定義するものではありません。

</details>

<span id="_7-what-is-the-recommended-strategy-for-eks-hybrid-nodes-upgrades"></span>

### 7. AWS の Hybrid Nodes アップグレードガイダンスに沿う方法はどれですか？

- A) すべてのノードを同時にアップグレードする
- B) 新しいホストへの移行と計画的な切り替えを優先し、それができない場合は検証済みの手順で 1 ノードずつインプレース更新する
- C) アップグレードのたびにクラスターを削除して再作成する
- D) アップグレードしない

<details>
<summary>回答を表示</summary>

**回答: B) 新しいホストへの移行と計画的な切り替えを優先し、それができない場合は検証済みの手順で 1 ノードずつインプレース更新する**

**解説:**
余剰容量がある場合、AWS は新しいホストへの置き換えと移行を推奨しています。インプレースでの `nodeadm upgrade` はサービスに影響する操作であり、Kubernetes の major.minor バージョンを引数に取ります。バージョンの skew、drain とデータの確認、実際のホスト操作、Node UID／完全なバージョン／新しい Lease／ワークロードの確認について、ライフサイクルガイドに従ってください。一定時間待つだけ、または以前の Ready 状態だけでは、受け入れ確認になりません。ローリング手順でサービス中断がゼロになると主張しないでください。

各 wave の前に、バックアップ、PDB、利用可能容量、バージョン互換性、認証情報の ID、復旧計画を確認してください。エラーがあれば停止して証拠を保持し、失敗したノードを自動的に uncordon しないでください。

</details>
