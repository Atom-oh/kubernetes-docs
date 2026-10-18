# ワークショップクイズ: PII抽出のためのQLoRAファインチューニング

> **最終更新日**: 2026年9月15日

## 多肢選択問題

1. `load_in_4bit=True`、`bnb_4bit_quant_type="nf4"`、`bnb_4bit_compute_dtype=torch.bfloat16`を使うQLoRAを正しく説明しているものはどれですか？
   - A) 基本重みとともに、活性化とオプティマイザー状態も4ビットになる
   - B) 対応する基本重みを4ビット形式で保存して凍結し、量子化linear経路ではBF16計算を使い、adapterを学習する
   - C) BF16計算によってNF4が相殺され、すべての基本重みが16ビット形式で保存される
   - D) Double quantizationとは基本重みを2回学習すること

<details>
<summary>回答を表示</summary>

**回答: B**

重みの保存形式、計算dtype、学習対象のパラメーターはそれぞれ別の選択です。NF4は基本重みの保存量を減らし、BF16はその経路で使う計算dtypeを指定します。Double quantizationは量子化定数を量子化します。adapter、勾配、オプティマイザー状態、活性化、高精度モジュール用のメモリは別途考慮する必要があります。
</details>

2. 入力幅が2,048、出力幅が768のlinear layerがあります。標準LoRAでrankは16、alphaは32、学習可能なbiasや追加モジュールはない場合、adapterパラメーター数と`alpha/r`スケールはいくつですか？
   - A) 1,572,864パラメーター、スケール2
   - B) 45,056パラメーター、スケール32
   - C) 45,056パラメーター、スケール2
   - D) 32,768パラメーター、スケール0.5

<details>
<summary>回答を表示</summary>

**回答: C**

`A`の形状は`(16, 2048)`、`B`の形状は`(768, 16)`です。そのため、パラメーター数は`16 × (2048 + 768) = 45,056`です。標準LoRAでは更新値を`32 / 16 = 2`でスケーリングします。`2048 × 768 = 1,572,864`は基本行列のパラメーター数であり、adapterの数ではありません。rank-stabilized LoRAでは別のスケーリング規則を使います。
</details>

3. 学習メモリを計画するとき、Qwenの「合計30.5B / アクティブ3.3Bパラメーター」はどのように解釈すべきですか？
   - A) アクティブ数は1トークンの疎な計算経路を示す。総重み、adapter、勾配、オプティマイザー状態、活性化を別途考慮する必要がある
   - B) 常に読み込まれるのは3.3Bパラメーターだけなので、他のexpertはメモリを消費しない
   - C) `30.5B × 4 bits = 15.25GB`なので、学習メモリは正確に15.25GBになる
   - D) 1トークンにつき8つのexpertを選ぶため、モデル全体では8つのexpertだけにLoRAが挿入される

<details>
<summary>回答を表示</summary>

**回答: A**

アクティブなパラメーター数は1トークンの計算経路に関するもので、モデル全体を保存する予算の代わりにはなりません。15.25 decimal GBという計算は理想化した4ビット重みの見積もりであり、量子化メタデータや学習に必要な他のメモリは含みません。adapterを挿入する対象と、特定のバッチで実際に選択されるexpertも別の概念です。
</details>

4. 学習レコードは1,600件、microbatchは1、勾配累積は8、data-parallel workerは1、オプティマイザー更新は80回です。packingや不完全な最終バッチがない場合、有効バッチサイズ、サンプル提示回数、epochの割合はいくつですか？
   - A) 有効バッチ1、提示80回、0.05 epoch
   - B) 有効バッチ8、提示1,280回、0.8 epoch
   - C) 有効バッチ80、提示6,400回、4 epoch
   - D) 有効バッチ8、提示640回、0.4 epoch

<details>
<summary>回答を表示</summary>

**回答: D**

有効バッチは`1 × 8 × 1 = 8`で、サンプル提示回数は`80 × 8 = 640`です。1 epochには`1600 / 8 = 200`回の更新が必要なため、80回の更新は0.4 epochです。現在の「full」というラベルは実行モードを表し、epochの完了や収束を意味しません。同じサンプル数でも、シーケンス長が異なれば学習トークン数も変わることがあります。
</details>

5. エンティティを含まず、assistantのcontentターゲットが空のドキュメントでは、completion-only lossで何を確認すべきですか？
   - A) すべてのラベルが`-100`なので、レコードは学習に一切寄与しない
   - B) promptとpaddingの位置は無視されるが、assistantのEOSなど、有効なcompletion tokenは教師信号として残る
   - C) EOSだけが無視され、抽出回答としてsource prompt全体が学習される
   - D) NF4によってEOSとloss maskが不要になるため確認は必要ない

<details>
<summary>回答を表示</summary>

**回答: B**

否定例では、モデルがエンティティを抽出せずに回答を完了するよう学習させます。このモデルでは`<|im_end|>`をEOSとして使います。実際のchat templateとtruncationの適用後に、教師信号として残るラベルがあることを確認してください。実際のcompletionには改行などの追加トークンが含まれる場合があります。すべて無視対象のラベルになったシーケンスを通常の否定例学習として扱ってはいけません。
</details>

6. rankとaugmentationの選択を比較するとき、評価用データセットはどのように使うべきですか？
   - A) 一貫したvalidation条件で候補を選び、設定を固定してから、ロックしたtestデータで最終的なbaseline/候補比較を行う
   - B) 各候補のtestスコアを確認して最も高いものを選ぶ
   - C) augmentationによる派生データをすべて作成してから、train、validation、testにランダム分割する
   - D) 小さな過学習用サブセットでlossが下がれば、汎化を確認せずデプロイする

<details>
<summary>回答を表示</summary>

**回答: A**

調整にはvalidationを使い、最終比較までtestセットはロックしておきます。現在のtrainerはsmoke runを含め、実行前後に毎回testセットを評価するため、そのまま安全なHPOループとして使うことはできません。教材用のチューニング手順には別途変更が必要です。augmentation前に元データを分割し、trainデータの派生データだけをaugmentationしてください。小さな過学習チェックは学習経路の診断用であり、汎化の証明ではありません。
</details>

7. Transformers 4.57.6のQwen3 MoE実装で、現在の7つのLoRA target suffixを確認する正しい方法は何ですか？
   - A) 選択されるモジュールは同じなので、確認を省いて`"all-linear"`に置き換える
   - B) すべてのMoEはraw parameterを使うので、必ず`target_parameters`へ変更する
   - C) 実際のモジュール名/数を調べ、別個のrouter `gate`を除外しつつ、attention projectionとexpertの`gate_proj`/`up_proj`/`down_proj`をカバーしていることを確認する
   - D) 7つのtarget名しかないため、モデル全体のlinear moduleは7つと予想する

<details>
<summary>回答を表示</summary>

**回答: C**

このバージョンでは、expertを`ModuleList`内の`nn.Linear` projectionとして実装しています。suffixはレイヤーやexpertごとに繰り返されるため、suffix数とmodule数は一致しません。公開されている設定では、想定される`48 × (4 + 3 × 128) = 18,624`個のlinear targetと実際の一覧を比較してください。`"all-linear"`ではrouterなどのモジュールが追加される可能性があります。`target_parameters`はraw parameterを使う別の実装に対応します。
</details>

8. 現在サポートされているAL2023 PyTorch DLCがカタログにあります。過去の例でGPU実行を再度有効にする前に、次に何をすべきですか？
   - A) イメージタグだけを変更し、`torch==2.8.0`を含む古いlockをインストールする
   - B) 日付ガードを削除し、イメージがECRにあるのでfull runを送信する
   - C) CPU演習に合格したため、GPUの量子化ロードとbackwardも成功と記録する
   - D) イメージのrepository/tag/digest、Python/CUDA/driver、依存関係、toolkitとMLflow cohortを検証し、承認されたGPU smoke testを実行する。代替構成が未検証の間は既存のガードを維持する

<details>
<summary>回答を表示</summary>

**回答: D**

PyTorch 2.8 DLCは2026年8月6日にパッチサポートの終了を迎えました。新しいカタログ項目があっても、このパッケージ用の検証済み代替cohortであるとは限りません。新しいファミリーは`pytorch-training`とは別のrepositoryを使うこともあり、古いtorch pinを入れると移行が元に戻る可能性があります。GPUの事前確認は今後のテスト手順です。CPUチェックやイメージ検索だけでは、GPU実行の成功を証明できません。
</details>

---

[学習教材に戻る](../../../ai-ml/sagemaker-ai/05-qlora-finetuning-workshop.md)
