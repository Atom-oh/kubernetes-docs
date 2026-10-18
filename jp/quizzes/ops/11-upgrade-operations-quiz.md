# EKS アップグレード運用クイズ

> **関連ドキュメント**: [EKS upgrades](../../ops/11-upgrade-operations.md)

## 1. EKS control plane のアップグレードでは、中間の minor version をいくつスキップできますか？

- A) 0。毎回、次の minor version に進む
- B) 1
- C) 2
- D) 無制限

<details>
<summary>回答を表示</summary>

**回答: A**

たとえば、1.34 から 1.36 へ進むには、1.35 を経由する必要があります。kubelet の skew 許容範囲は、control plane のアップグレード手順とは別のものです。

</details>

## 2. Auto Mode のみのクラスターで CoreDNS Deployment が見当たらない場合、どう解釈すべきですか？

- A) 常に DNS が壊れていることを意味する
- B) node のシステムサービスによる DNS と実際の動作を確認する
- C) 常にセルフマネージドの Karpenter をインストールする
- D) すべてのクラスターから CoreDNS Deployment を削除する

<details>
<summary>回答を表示</summary>

**回答: B**

Auto Mode 以外の node が混在するクラスターでは、それらの node が必要とする DNS Deployment と add-on を残してください。

</details>

## 3. Velero 1.18.4 の `restore create -o json` について、正しい説明はどれですか？

- A) 実際の restore を完了する
- B) 完全にオフラインで実行される
- C) オブジェクトは作成しないが、リソースの検出や Backup の読み取りを行う場合がある
- D) `--dry-run` と組み合わせた場合にのみ有効である

<details>
<summary>回答を表示</summary>

**回答: C**

`restore create` に `--dry-run` フラグはありません。出力だけを確認することと、隔離した環境で実際の restore をテストすることは別です。

</details>

## 4. API エラーが発生した場合や kubecontext が想定と異なる場合、preflight ツールはどう動作すべきですか？

- A) 結果が空なら正常とみなす
- B) 不明または context の不一致として失敗し、調査する
- C) context を自動で切り替えてアップグレードする
- D) PDB を削除する

<details>
<summary>回答を表示</summary>

**回答: B**

preflight が単独で実行できても、Pod の readiness が確認できたことにはなりません。Deployment の generation と rollout status も確認してください。

</details>

## 5. EKS ネイティブの rollback を実行する基本的な適格条件はどれですか？

- A) 現在の version で新規作成されたクラスターであること
- B) アップグレード完了から 7 日以内に開始するなど、適格条件を満たすこと
- C) 以前の任意の version に、いつでも戻せること
- D) etcd backup があれば、すべての制限を回避できること

<details>
<summary>回答を表示</summary>

**回答: B**

戻し先 version のサポート状況、EXTENDED policy、クラスターの ACTIVE 状態、互換性のない EKS 機能も確認してください。

</details>

## 6. Auto Mode の node rollback 中にクラスターの status が ACTIVE の場合、何を意味しますか？

- A) rollback が完全に完了した
- B) control plane はまだ現在の version で動作している可能性があるため、update ID を確認する
- C) node rollback は実行できない
- D) 直ちに以前のクラスターを削除する

<details>
<summary>回答を表示</summary>

**回答: B**

Auto Mode は最初に node を調整します。node の timeout のデフォルトは 720 分です。クライアント側の待機 timeout が発生しても、AWS 側の処理はキャンセルされません。

</details>

## 7. rollback の `--force` は何を回避しますか？

- A) 7 日間の期限とすべての PDB
- B) あらゆる中断とデータ互換性の問題
- C) Insight のチェック。適格条件や Auto Mode の中断制御は回避しない
- D) etcd データの保持

<details>
<summary>回答を表示</summary>

**回答: C**

ERROR または UNKNOWN の Insight は rollback をブロックしますが、WARNING は参考情報です。`--force` は標準的な復旧手順の代わりにはなりません。

</details>

## 8. ネイティブの version rollback で、過去の状態に自動復元されないものはどれですか？

- A) API server の minor version
- B) Auto Mode による node version の調整
- C) add-on、アプリケーション、etcd 内のオブジェクト、PV データ
- D) control plane コンポーネントの version

<details>
<summary>回答を表示</summary>

**回答: C**

通常の managed node group では、`UpdateNodegroupVersion` を別途処理する必要があります。version rollback は snapshot の復元とは異なります。

</details>

## 9. NLB の target group weight を 0 に設定した場合、正しい説明はどれですか？

- A) 既存の接続は常に最後まで維持される
- B) 既存の接続が短時間で閉じることがあるため、retry と session の動作をテストする
- C) weight の合計は 100 でなければならない
- D) NLB は weight 付き target group をサポートしない

<details>
<summary>回答を表示</summary>

**回答: B**

weight は 0〜999 の相対値です。通常の変更と weight を 0 にする変更を区別してください。また、TLS listener では target group stickiness はサポートされません。

</details>

## 10. Blue を廃止する前に、何を確認すべきですか？

- A) weight が 0 になったら直ちに削除する
- B) 共有リソースと target group の参照、データ互換性、復旧期間、所有関係を確認する
- C) HTTP 200 が 1 回返れば、すべてのデータ整合性が証明される
- D) EFS を共有していれば、同時書き込みを確認する必要はない

<details>
<summary>回答を表示</summary>

**回答: B**

Auto Mode の TGB またはクラスターを削除する際の target group のライフサイクルと、listener の共有を考慮してください。namespace を変更しても、consumer、DB、DNS が分離されるとは限りません。

</details>
