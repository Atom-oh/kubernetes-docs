# EKS Hybrid Nodes の前提条件クイズ

> **関連ドキュメント**: [前提条件](../../eks-hybrid-nodes/01-prerequisites.md)
> **最終更新日**: 2026 年 9 月 12 日

## 多肢選択問題

### 1. EKS Hybrid Node として machine を登録する理由として、サポートされないものはどれですか？

- A) 互換性のあるオンプレミス GPU server を使う
- B) アプリケーションの処理をローカルデータの近くで行う
- C) 通常の EC2／cloud machine を Hybrid Node のインフラとして登録する
- D) 接続性と復旧方法をテストした edge workload を運用する

<details>
<summary>回答を表示</summary>

**回答: C) 通常の EC2／cloud machine を Hybrid Node のインフラとして登録する**

**解説:**
AWS が Hybrid Node のインフラとしてサポートするのは、顧客が運用するオンプレミスまたは edge の物理／仮想 host であり、cloud infrastructure ではありません。EC2 を Hybrid Node として登録しても Hybrid の料金が発生します。cloud 上の node には通常の AWS compute type を使ってください。Hybrid Node には安定した接続性が必要です。配置 label だけでは、規制への適合やオフライン運用は証明できません。

</details>

### 2. 現行の AWS Hybrid 統合互換性 matrix に一致する OS の説明はどれですか？

- A) Windows Server のみ
- B) Ubuntu 20.04／22.04／24.04、RHEL 8／9、仮想化環境の AL2023、サポート対象の Bottlerocket VMware variant
- C) あらゆる macOS release
- D) どの Linux image も自動的に AWS の OS support を受ける

<details>
<summary>回答を表示</summary>

**回答: B) Ubuntu 20.04／22.04／24.04、RHEL 8／9、仮想化環境の AL2023、サポート対象の Bottlerocket VMware variant**

**解説:**
vendor による security maintenance、architecture、選択した CNI と kernel を確認してください。Bottlerocket VMware v1.37.0 以降は x86_64 のみで、専用の bootstrap 手順を使います。AL2023 はオンプレミスの仮想化環境向けであり、EC2 外では AWS の OS support 対象になりません。ARM 上の EKS kube-proxy 1.31 以降には ARMv8.2+crypto が必要です。kernel 5.4 以降という一般的な条件や CPU model 名だけでは、十分な検証になりません。

</details>

### 3. GPU workload の互換性を評価する際、誤っている説明はどれですか？

- A) driver と CUDA／framework image の互換性が重要である
- B) 必要な memory は workload によって異なる
- C) サポート対象の OS／kernel と container runtime が重要である
- D) GPU を搭載すれば CPU architecture は無視できる

<details>
<summary>回答を表示</summary>

**回答: D) GPU を搭載すれば CPU architecture は無視できる**

**解説:**
CPU architecture、GPU variant、driver、OS／kernel、container toolkit／runtime、アプリケーション image のすべてに互換性が必要です。Hybrid Node に一律適用できる 4 GB の GPU memory 下限や、固定の 525／550 driver 要件はありません。適切に package 化された container を実行するだけなら、host の `nvcc` compiler は必須ではありません。`nvidia-smi` と `nvcc` が示す情報は異なります。

</details>

### 4. host resource に関する基本的な推奨を、どう解釈すべきですか？

- A) 1 core と 512 MB で十分だと保証される
- B) AWS は少なくとも 1 vCPU と 1 GiB RAM を推奨するが、全環境に適用される厳密な最小値はない
- C) すべての workload に正確に 4 core と 8 GB が必要である
- D) 50 GB の disk があれば readiness が保証される

<details>
<summary>回答を表示</summary>

**回答: B) AWS は少なくとも 1 vCPU と 1 GiB RAM を推奨するが、全環境に適用される厳密な最小値はない**

**解説:**
OS、kubelet／runtime、CNI／agent、image／log、実際の workload に必要な容量をそれぞれ見積もってください。以前示されていた 2 core／2 GB や 20／50／100 GB の disk 推奨は、検証済みの workload 最小要件ではなく、互いに整合しない計画例でした。同様に、AWS の 100 Mbps／200 ms という network guidance も一般的な目安であり、全環境共通の受け入れ基準ではありません。

</details>

### 5. host を EKS Hybrid Node にすることだけを理由に、必須とはならない component はどれですか？

- A) `containerd` などの互換性のある CRI runtime
- B) kubelet
- C) Docker Engine
- D) 選択した AWS credential／authentication helper

<details>
<summary>回答を表示</summary>

**回答: C) Docker Engine**

**解説:**
Docker の `containerd` package source は、Docker Engine を実行するための要件ではありません。Bottlerocket 以外の host では、`nodeadm install` が依存関係をインストールし、`config check` が入力を検証し、`init` が node を構成して cluster に参加させます。signing key の変更後、SSM のインストール／upgrade には nodeadm 1.0.19 以降が必要です。確認対象の release は 1.0.20 です。RHEL では `docker` または事前にインストールした runtime を指定し、`none` は distro ではありません。

</details>

### 6. H100 を使う Hybrid Node deployment では、どのように進めるべきですか？

- A) すべての host に 450.x をインストールする
- B) 過去の 525.x の例が常に十分だとみなす
- C) framework にかかわらず、必ず 535.x を使う
- D) サポート対象の GPU／OS／driver／CUDA／runtime の組み合わせを選び、アプリケーションを検証する

<details>
<summary>回答を表示</summary>

**回答: D) サポート対象の GPU／OS／driver／CUDA／runtime の組み合わせを選び、アプリケーションを検証する**

**解説:**
以前の表は最低 driver version と推奨 version を混同し、回答とも矛盾していました。450／525／535／545／550 という値は、現在の deployment 全般に適用される要件ではありません。正確な H100 variant、サポート対象の driver branch、framework image、必要な feature を確認し、退避させたテスト host で変更を試してください。この監査では GPU を実行せず、model benchmark も行っていません。

</details>

## 参考資料

- [Hybrid Node の前提条件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [Hybrid Node の OS 互換性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm リファレンス](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
