# ワークショップ: PII 抽出のための QLoRA ファインチューニング

> **最終更新日**: 2026年9月16日

主な情報源は2026年9月15日に確認しました。

このワークショップの目的は、何をモデルが予測するのか、どのパラメーターが変化するのか、学習ステップが何を意味するのか、生成されたアダプターを保持する根拠となる証拠は何かを考察できる実験として説明することです。Training Job の完了は、その実験の一部に過ぎません。

合成ドキュメントを使い、リポジトリの [Qwen PII trainer](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/train.py) に沿って進めます。この章とあわせて、[Part 3 の送信、所有権、エクスポート、クリーンアップに関する契約](03-sagemaker-mlflow-execution.md)を参照してください。[データ拡張ワークショップ](06-data-augmentation-workshop.md)と[PII 評価/リリースワークショップ](07-pii-evaluation-release.md)へ続きます。

**実行状況:** この章で説明する過去の `src/train.py` 経路は、PyTorch 2.8.0 DLC のパッチ提供が2026年8月6日に終了したため、意図的に停止します。`src/runtime_contract.py` はそのまま維持してください。以下の CPU 演習ではモデルウェイトを読み込まず、学習コードの抜粋は固定された実装を説明します。別の PyTorch 2.11 経路では、2026年9月16日に実際の GPU スモーク学習と保存/再読み込み検証を完了しました。[学習パスの実行記録](README.md#sagemaker-execution-readiness)には、小規模な検証サンプルとフルジョブの送信について説明があります。以下の過去の実行経路を示す抜粋を、新しい実行経路の成功を示す証拠と解釈しないでください。

## 1. 学習方法を選ぶ前に予測対象を定義する

次の、すべて架空のドキュメントを考えます。

```text
Synthetic contact Alex Example; email alex@example.com.
```

モデルに期待する応答は、ドキュメントからコピーしたエンティティのリストです。

```text
PERSON	Alex Example
EMAIL	alex@example.com
```

モデルが学習するのは、ドキュメント全体の書き換えではなく、**構造化された抽出**です。出力契約は `TYPE<TAB>ORIGINAL` の行が0個以上並ぶ形式です。使用できる type は `PERSON`、`RRN`、`DOB`、`REL`、`ADDRESS`、`PHONE`、`EMAIL`、`ACCOUNT`、`CARD` です。「人物とメールアドレスが見つかりました」のような応答は、意味が正しくても指定された出力ではありません。

抽出後の決定的なコードで type と入力元との一致を検証し、選択した範囲を `[PERSON_1]` のような token に置き換えます。この分離によりエラーを観測しやすくなります。見逃したエンティティは抽出エラー、誤った置換境界は置換エラー、形式の不正は形式エラーです。これらをすべて「LLM がドキュメントをマスキングする」にまとめると、違いが見えなくなります。

### CPU 演習: 抽出結果から元に戻せる token へ

パッケージの Python 3.12 環境を使い、`examples/ai-ml/qwen-pii-finetuning` から実行します。既存のローカルヘルパーと合成文字列を使用します。モデルや AWS は呼び出しません。

```python
from src.pii_tokens import parse_tsv, pseudonymize_text, reassemble_text

source = "Synthetic contact Alex Example; email alex@example.com."
completion = "PERSON\tAlex Example\nEMAIL\talex@example.com"

entities = parse_tsv(completion, source)
result = pseudonymize_text(source, entities)

assert result.masked_text == (
    "Synthetic contact [PERSON_1]; email [EMAIL_1]."
)
assert reassemble_text(result.masked_text, result.mapping) == source
print(result.masked_text)
```

このマッピングは**元に戻せる仮名化**を行います。不可逆な削除、あるいは匿名化の証明とは呼ばないでください。実際のワークフローでは、元データ、マッピング、未加工の予測、学習済みアダプターに適切なアクセス制御と保持期限を設定する必要があります。往復テストで確認できるのは可逆性です。何も置き換えない場合でも、そのテストには合格することがあります。

現在の `parse_tsv()` は意図的に寛容で、不正な行を破棄して有効な行を保持する場合があります。`train.py` はエンティティが0件のドキュメントを有効な入力として扱えるため、空の completion も解析成功として数えることがあります。したがって、「解析成功」だけでは抽出の正しさを示しません。PII 評価ワークショップでは、厳密な形式の妥当性、エンティティ再現率、残存 PII を分けて評価します。

### 問題に合ったベースラインを選ぶ

| 方法 | 最初に有効な実験 | 自動では解決しないこと |
|---|---|---|
| 正規表現と決定的ルール | 安定した電話/メール形式、厳密な置換ルール | 文脈依存の名前、関係性、OCR のばらつき、曖昧な数値 |
| トークン分類/NER モデル | 安定したエンティティ分類体系によるスパンラベル | 新しいドメインへの対応、アノテーション品質、後段の置換ポリシー |
| プロンプトのみの生成 | ベースモデルの抽出能力と TSV の動作を確認 | 安定した形式、完全な再現率、ドキュメント内の指示への耐性 |
| LoRA | 学習可能な低ランク更新で事前学習モデルを適応 | 量子化されていないベースモデルの保存容量削減 |
| QLoRA | メモリーに制約がある場合、凍結した量子化ベースを通してアダプターを学習 | 活性化、オプティマイザー状態、すべてのモデル tensor が4-bitになること |

まず決定的ベースラインとプロンプトのみのベースラインを用意します。制約されたタスクでプロンプトのみのモデルが既に十分なら、学習を追加しても複雑さに見合う効果がない可能性があります。ドメイン固有エンティティを見落とす、または出力契約に繰り返し違反する場合は、教師ありアダプター実験の目的が明確になります。

## 2. LoRA が変更するものを理解する

入力幅が `d_in`、出力幅が `d_out` の線形層を考えます。

- `W` の形状は `(d_out, d_in)`
- `A` の形状は `(r, d_in)`
- `B` の形状は `(d_out, r)`

標準的な LoRA は次の式を使います。

```text
W_effective = W + (alpha / r) * B @ A
y = W @ x + (alpha / r) * B @ A @ x
```

ベース行列 `W` は凍結されます。オプティマイザーが更新するのは `A` と `B` で、パラメーター数は `d_in × d_out` ではなく `r × (d_in + d_out)` です。ベースモデルを使う計算を通じて勾配は引き続き伝播します。「凍結」は、順伝播や逆伝播にベースモデルが存在しないという意味ではありません。[LoRA 論文](https://arxiv.org/abs/2106.09685)を参照してください。

`2048 → 768` の射影に rank 16 を使うと、次のようになります。

```python
d_in, d_out, rank, alpha = 2048, 768, 16, 32
base_parameters = d_in * d_out
adapter_parameters = rank * (d_in + d_out)

assert base_parameters == 1_572_864
assert adapter_parameters == 45_056
assert alpha / rank == 2
print(base_parameters, adapter_parameters, alpha / rank)
```

rank が制御するのは更新の表現能力であり、学習 epoch 数ではありません。`lora_alpha` はスケーリングを制御します。この設定では `alpha/r` は2です。alpha を考慮せずに rank を増やすと、そのスケールも変わります。PEFT のオプションである rank-stabilized LoRA では別のスケーリング規則を使いますが、コミット済みの構成では有効になっていません。

[PEFT 0.17.1 のデフォルト初期化](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md)では、`B` の初期値が0のため、アダプターは最初は何もしない状態です。最初の backward pass ですべてのアダプター tensor に非ゼロの勾配が必要だとは考えないでください。MoE モデルでは、特定のバッチで選択されない expert もあります。有用な診断では、存在する勾配が有限であることと、optimizer step 後に想定したアダプターパラメーターが変化したことを確認します。

## 3. 4-bit ウェイト以外の QLoRA メモリーも見積もる

[QLoRA 論文](https://arxiv.org/abs/2305.14314)は、凍結した量子化ベースと学習可能なアダプターを組み合わせます。コミット済み trainer の以下の設定は、それぞれ異なる決定です。

| 設定またはメモリー分類 | この例での意味 |
|---|---|
| `load_in_4bit=True` | 対応するベース線形ウェイトを4-bit 量子化でロード |
| `bnb_4bit_quant_type="nf4"` | 正規分布するウェイトを想定して設計された NormalFloat4 を使用 |
| `bnb_4bit_use_double_quant=True` | 量子化定数も量子化して追加の格納量を減らす |
| `bnb_4bit_compute_dtype=torch.bfloat16` | 量子化線形経路の演算に BF16 を使用。すべてを4-bit 演算するわけではない |
| LoRA パラメーターと勾配 | 独自の dtype とメモリー要件を持つ学習可能 tensor |
| オプティマイザー状態 | 学習可能パラメーターに必要な追加状態。NF4 が自動的にこれを8-bitにするわけではない |
| 活性化と一時 tensor | シーケンス長、マイクロバッチ、attention の実装、checkpointing に依存 |
| 非量子化モジュール | embedding、正規化などは高精度のままの場合がある |

Double quantization は「モデルを2-bitに量子化する」という意味ではありません。BF16 にしても、すべての tensor が2バイトを使うとは限りません。k-bit 用の準備やアダプター処理で、選択した tensor が FP32 のままになったり、FP32 に昇格したりすることがあります。1つの構成フィールドから全体のメモリー使用量を推定せず、実際の dtype と学習対象パラメーターを確認してください。[バージョンを固定した bitsandbytes ガイド](https://github.com/huggingface/transformers/blob/v4.57.6/docs/source/en/quantization/bitsandbytes.md)では、NF4、compute dtype、nested quantization をそれぞれ説明しています。

Gradient checkpointing は選択した活性化を保存せず、backward 中に再計算してメモリーを節約します。計算量とメモリーを交換します。Gradient accumulation は optimizer 更新まで複数のマイクロバッチをまとめますが、それらすべての活性化グラフを同時に保持する必要はありません。どちらの機能もオプティマイザー状態をなくすものではありません。

### 総パラメーター数と MoE のアクティブパラメーター数は別の予算

[Qwen のモデルカード](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)では、**全体で30.5B、アクティブ化されるパラメーターは3.3B**、48層、128 expert、token ごとに選択される expert は8つと説明されています。アクティブパラメーター数は、token ごとの疎な計算を表します。ロードする必要があるパラメーターが3.3Bだけという意味ではありません。

理想化した `30.5 billion × 4 bits` の計算は **15.25 decimal GB** です。これはウェイト格納量の下限を示す例であり、GPU メモリー使用量の予測ではありません。量子化メタデータ、非量子化 tensor、アダプター、勾配、オプティマイザー状態、活性化、割り当てオーバーヘッドは含まれません。特定の単一 GPU インスタンスに収まる証明にもなりません。

## 4. このモデルのアダプター対象を調べる

過去のパッケージでは、以下の関連バージョンを固定しています。

| パッケージ | 固定バージョン |
|---|---|
| PyTorch | `2.8.0` |
| Transformers | `4.57.6` |
| PEFT | `0.17.1` |
| TRL | `0.24.0` |
| bitsandbytes | `0.48.2` |
| Accelerate | `1.10.1` |
| datasets | `3.6.0` |

[固定バージョンの Qwen3 MoE 実装](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)では、expert は `gate_proj`、`up_proj`、`down_proj` の線形層を持つ `ModuleList` です。Attention は `q_proj`、`k_proj`、`v_proj`、`o_proj` を使います。routing gate の名前はこれらと別の `gate` です。

コミット済み `LoraConfig` は、この7種類の射影 suffix を対象にします。`gate_proj` に “gate” が含まれるという理由だけで router を対象にするわけではありません。逆に、一覧を `"all-linear"` に置き換えると router を含む追加の線形モジュールが対象になることがあります。それは別の実験です。

```python
# Inspection hook after an authorized model load, before adapter insertion.
from collections import Counter

targets = {
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
}
matched = [
    name for name, module in model.named_modules()
    if name.rsplit(".", 1)[-1] in targets
]
counts = Counter(name.rsplit(".", 1)[-1] for name in matched)
assert set(counts) == targets
assert not any(name.endswith(".gate") for name in matched)
print(dict(sorted(counts.items())))  # Module names/counts, not training data.
```

公開されたモデル構成と rank 16 に基づく計算では、attention の4つの射影に約 **13.37 million**、すべての expert 内の3つの射影に約 **830.47 million** のアダプターパラメーターがあり、合計は **843,841,536** です。これはモデル次元に基づく計算であり、GPU 上で計測した結果ではありません。アダプター挿入後に `trainer.model.print_trainable_parameters()` を実行して実数を確認します。

モデルをロードしなくても、この数を再現できます。[モデル構成](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json)には hidden size 2,048、head dimension 128、query head 32、key/value head 4、expert intermediate size 768 とあります。そのため Q は `2048 → 4096`、K/V はそれぞれ `2048 → 512`、O は `4096 → 2048` に射影されます。各 expert は `2048 → 768` の射影を2つ、`768 → 2048` の射影を1つ持ちます。

```python
# CPU arithmetic from this model/version's configuration; not a GPU benchmark.
layers, experts, rank = 48, 128, 16
hidden, head_dim, q_heads, kv_heads = 2048, 128, 32, 4
expert_hidden = 768
q_width, kv_width = q_heads * head_dim, kv_heads * head_dim

attention = layers * rank * (
    (hidden + q_width)
    + 2 * (hidden + kv_width)
    + (q_width + hidden)
)
expert_adapters = layers * experts * 3 * rank * (hidden + expert_hidden)
total = attention + expert_adapters

assert attention == 13_369_344
assert expert_adapters == 830_472_192
assert total == 843_841_536
assert layers * (4 + 3 * experts) == 18_624  # Targeted linear modules.
print(attention, expert_adapters, total)
```

この数は、公開された48層モデルの expert 構造と上記7種類の対象 suffix を前提とし、追加の学習可能モジュールや bias を含みません。実際のアダプター一覧と比較するための想定値であり、その一覧の代わりにはなりません。

これが、大規模 MoE の対象リストに対して「LoRA は少数のパラメーターを使う」だけでは説明として不十分な理由です。attention のみを対象にする場合と、attention と expert の両方を対象にする場合の比較は、有用な統制実験になります。ただし対象の変更には教材の変更が必要です。現在の trainer では対象リストがハードコードされています。

新しい MoE 実装の中には、`nn.Linear` expert の代わりに、2次元または3次元の `nn.Parameter` を直接使うものもあります。そのケースについては [PEFT 0.17.1 の `target_parameters` の説明](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md)で、expert 軸や複数アダプターに関する制約も説明されています。選んだモデルとバージョンの実装を調べ、このモジュール方式の実装に parameter-targeting の手順をそのまま適用しないでください。

## 5. 1つのレコードをチャット形式と loss mask に沿って追う

実際の [dataset loader](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/dataset.py) は、会話形式の**prompt/completion** データを返します。

```python
from src.dataset import SYSTEM_INSTRUCTION

record = {
    "source_text": "Synthetic contact Alex Example.",
    "target_tsv": "PERSON\tAlex Example",
}
row = {
    "prompt": [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": record["source_text"]},
    ],
    "completion": [
        {"role": "assistant", "content": record["target_tsv"]},
    ],
}
assert row["completion"][0]["role"] == "assistant"
```

`train.py` 内の未使用関数 `format_training_text()` は `### Instruction` 形式のテキストを生成します。これは**現在のデータセット経路ではありません**。`SFTTrainer` が実際に受け取る形式として教えないでください。

[TRL 0.24.0](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)では、trainer が tokenizer の chat template を prompt と prompt-plus-completion に適用します。その境界から completion mask を作ります。`completion_only_loss=True` の場合、prompt の位置に label `-100` を割り当て、completion の位置を causal language model の loss 計算に使います。padding も無視されます。

### 抽出対象が空でも学習信号は空ではない

対象エンティティがないドキュメントでは、assistant の内容を空文字列にします。それでも応答を assistant turn の終了 token で終わらせる必要があります。このモデルの [tokenizer 設定](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/tokenizer_config.json)では、EOS が `<|im_end|>`、padding が `<|endoftext|>` です。

```python
# CPU-only illustration of a mask, not actual tokenizer output.
input_ids = [101, 102, 103, 104, 151645]
completion_mask = [0, 0, 0, 0, 1]
labels = [
    token if keep else -100
    for token, keep in zip(input_ids, completion_mask)
]
assert labels == [-100, -100, -100, -100, 151645]
assert sum(label != -100 for label in labels) == 1
```

この例は、対象なしのレコードで EOS を教師信号にする様子を示します。実際の template には改行などの追加 completion token が含まれることがあります。実際に token 化した行を検証し、例示の prompt ID や固定長の completion を前提にしないでください。

Instruct-2507 のモデルカードでは、このモデルは **non-thinking** であり `enable_thinking=False` は不要としています。現在の予測コードはその引数を渡しますが、それによってこの checkpoint が推論モデルになるわけではありません。`assistant_only_loss=True` は別のオプションで、template に適切な assistant mask のサポートが必要です。この単一応答の prompt/completion 契約には必要ありません。

### 最初の学習ステップ前に準備済みデータを調べる

次の hook は、認可され互換性のある環境で trainer を構築した後に使います。入力本文や decode した label を出力せず、件数と mask を確認します。

```python
# Instructional inspection hook; not currently present in src/train.py.
prepared = trainer.train_dataset
for example in prepared:
    mask = example["completion_mask"]
    assert len(mask) == len(example["input_ids"])
    assert any(mask), "No supervised completion survived preprocessing"

examples = [prepared[i] for i in range(min(4, len(prepared)))]
batch = trainer.data_collator(examples)
supervised = (batch["labels"] != -100).sum(dim=1)
assert bool((supervised > 0).all())
if "attention_mask" in batch:
    padding = batch["attention_mask"] == 0
    assert bool((batch["labels"][padding] == -100).all())
print({"examples": len(examples), "target_tokens": supervised.tolist()})
```

切り詰め前の prompt-plus-completion の長さも確認し、応答末尾の EOS が残ることを検証します。`max_length=1024` は文書だけではなく、学習シーケンス全体に適用されます。長い prompt だけで予算を使い切り、回答が削られる可能性があります。推論時の切り詰めでも PII が隠れる一方、評価では文書全体から抽出すべきエンティティが期待されることがあります。

明文化された方針を選びます。長さ超過を拒否する、重要でない prompt 指示だけを短くする、またはアノテーション契約を更新しながらソースを分割する、のいずれかです。分割チャンクと拡張データの派生物は、同じドキュメント family/split 内に保ちます。活性化メモリー、マイクロバッチ、推論出力の長さを再検討せずに、単にシーケンス長を増やすことはしないでください。

## 6. 固定された学習構成を実行順に読む

以下は**コードを読むための抜粋**であり、ブロックされた GPU ランタイムを起動する指示ではありません。PEFT 0.17.1、Transformers 4.57.6、TRL 0.24.0 の名前と引数に一致します。

まず `run_training()` 内の次の段階を確認します。

| 順番 | コミット済みエントリーポイントの処理 |
|---|---|
| 1 | 学習スタックを import する前にサポート条件の guard を実行 |
| 2 | 構成と seed を解決し、MLflow を準備してデータセットファイルを読み込む |
| 3 | 量子化モデル/tokenizer をロードし、test でベースラインを評価 |
| 4 | k-bit 学習を準備し、アダプターと会話データセットを作成 |
| 5 | 学習を実行し、validation で途中評価 |
| 6 | モデルの出力を保存し、最終アダプターファイルを記録 |
| 7 | チューニング済みモデルを test で評価し、集計結果を出力 |

3段階目と7段階目で test を使うのは現在の動作であり、セクション8が推奨する候補選択ワークフローではありません。

```python
import torch
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import BitsAndBytesConfig

quantization = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

# `model` has already been loaded by the reviewed loading path.
model.config.use_cache = False
model = prepare_model_for_kbit_training(
    model, use_gradient_checkpointing=True
)
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)
```

コミット済み loader は `AutoModelForCausalLM.from_pretrained(..., quantization_config=..., device_map="auto", torch_dtype=torch.bfloat16)` を使います。自動配置の結果を調べてください。CPU/disk offload を、学習に有効な配置の実証の代わりにしてはいけません。単一 GPU 実験を提案する場合は、メモリーに収まることを確認した後、明示的な配置を使えます。この章では loader を変更しません。

現在のコードでは `output_router_logits=True` も設定しています。固定された MoE 実装では、router の補助 loss が報告される loss に加算される場合があります。これによって router が LoRA の対象になるわけではありません。比較実験では、この選択を記録します。

```python
from trl import SFTConfig, SFTTrainer

sft_args = SFTConfig(
    output_dir=str(output_dir / "checkpoints"),
    max_steps=80,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=0.0002,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=1,
    eval_strategy="steps",
    eval_steps=20,
    save_strategy="steps",
    save_steps=80,
    save_total_limit=1,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    max_length=1024,
    packing=False,
    completion_only_loss=True,
    report_to="none",
    seed=42,
    data_seed=42,
)
trainer = SFTTrainer(
    model=model,
    args=sft_args,
    train_dataset=train_dataset,
    eval_dataset=validation_dataset,
    processing_class=tokenizer,
    peft_config=lora_config,
)
```

この抜粋は、構成済みの**フル実行**値を示し、既存のモデル、tokenizer、データセット、出力ディレクトリがあることを前提としています。`max_length` と `processing_class` を意図的に使っています。バージョンを確認せず、古い `max_seq_length`/`tokenizer` の例に置き換えないでください。固定バージョンの `SFTConfig` に構成レベルの `chat_template_kwargs` フィールドはありません。バージョン0.24.0では、各例に対する template kwargs をサポートします。

実際の tokenizer には適切な EOS が既に設定されています。この SFTConfig で `eos_token="<|im_end|>"` を明示すれば、教材上その契約を見やすくできますが、この指定を省略しても現在の tokenizer の EOS が誤っているわけではありません。

`config/experiment.yaml` には `quantization`、`double_quant`、`compute_dtype` がありますが、loader は現在 NF4/double quantization/BF16 をハードコードしています。YAML 値だけ変えてもアブレーションにはなりません。設定を固定したままその事実を説明するか、選択を実際に loader に接続する、別途レビューされた教材修正を行ってください。

### 最適化から抽出結果の生成まで

前提条件と検査用 hook が検証済み GPU 環境で通った後、コミット済みの手順は `trainer.train()` を呼び出し、モデル出力を保存して、調整済みモデルを評価します。次の抜粋はその境界を示すものであり、CPU 演習ではありません。

```python
# Code-reading excerpt: assumes an approved, constructed GPU trainer.
train_result = trainer.train()
trainer.save_model(str(output_dir))
trainer.model.config.use_cache = True
```

生成時は prompt を assistant の生成プレフィックスで止め、正解 completion を含めないでください。生成された ID から prompt token を取り除いてから回答を解析します。上の合成 `row` と `record` を使う、単一レコードの診断案を以下に示します。

```python
# Instructional inference hook; not a replacement for the committed CLI.
trainer.model.eval()
prompt = tokenizer.apply_chat_template(
    row["prompt"], tokenize=False, add_generation_prompt=True
)
inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
prompt_length = inputs["input_ids"].shape[1]
if prompt_length > 1024:
    raise ValueError("Apply the reviewed long-document policy first")
inputs = inputs.to(trainer.model.device)

with torch.inference_mode():
    generated = trainer.model.generate(
        **inputs,
        do_sample=False,
        max_new_tokens=512,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
completion = tokenizer.decode(
    generated[0, prompt_length:], skip_special_tokens=True
)
entities = parse_tsv(completion, record["source_text"])
# Evaluate aggregate metrics; do not log raw completions from real documents.
```

現在の `_predict_records()` は、左 padding と truncation を使って例をバッチ処理します。一方、上記 hook は教材上の境界を明確にするため、単一 prompt が長すぎる場合に拒否します。出力の512 token 上限は別個の制約です。長い TSV 回答はそれでも途中で切れることがあります。prompt 長だけでなく、応答の終了と形式も確認してください。

## 7. 例、optimizer 更新、epoch を数える

通常のデータ並列学習では、次のように計算します。

```text
effective batch ≈ microbatch per device × accumulation × data-parallel workers
```

コミット済みの単一インスタンス、単一 GPU の例では `1 × 8 × 1 = 8` です。勾配蓄積を8回にすると、8マイクロバッチ後に1回 optimizer 更新します。各マイクロバッチに8例ずつ含まれるという意味ではありません。

```python
from math import ceil

records = 1600
microbatch, accumulation, workers = 1, 8, 1
effective_batch = microbatch * accumulation * workers
updates_per_epoch = ceil(records / effective_batch)

assert effective_batch == 8
assert updates_per_epoch == 200
assert 10 * effective_batch == 80
assert 80 * effective_batch == 640
assert 80 / updates_per_epoch == 0.4
```

このように、構成済みスモーク実行は optimizer を10回更新し、約80回の例提示を行います。「フル」実行は80回更新し、例が割り切れて pack されていない前提では約640回提示、1,600レコードの epoch の0.4回分です。「Full」は実行モード名であり、収束や完全な1 epoch を意味しません。

`max_steps` は更新回数の予算を決めます。シーケンス長が変わると、step 数が等しくても教師信号の token 数や計算量は同じとは限りません。より長い context や拡張データを比べる場合は、経過時間と loss だけでなく、観測した例と対象 token 数を記録してください。分散実行の端数 batch と packing には追加の計算が必要ですが、上記の計算には含めません。

## 8. 少数例への過学習診断とモデル選択を分ける

フル学習予算を使う前に、**学習用**レコード8～16件の診断案を定義します。単純な positive 例、繰り返しのあるエンティティ、形式のばらつき、PII なしの例を含めます。この小規模データを validation と固定済み test から分離します。

ランタイム移行後、次の順で確認します。モデルがロードされる、prompt/completion mask が正しい、1回の forward/backward で有限値が得られる、想定したアダプターパラメーターが変わる、小規模データに適合しやすくなる、保存したアダプターを同じベースモデルで再ロードし決定的な decode を再現する。

例として、実効 batch が8のデータ8件を使い、optimizer を20回更新すると、その小規模データを約20回ずつ見ることになります。これは意図的な診断予算であり、全データセットに対する推奨値ではありません。その8件の完全一致の抽出と、PII なしの例が終了 token で終わることを確認します。loss が下がることだけを合格条件にはしません。

これは意図的な過学習チェックです。成功からわかるのは、学習経路がこれらの例を学習できることです。汎化、本番での再現率、すべての PII の除去を示すものではありません。失敗した場合は有益な情報です。モデルやデータセットを大きくする前に、mask、target、データの対応関係、最適化を修正します。

### 現在の trainer が安全な HPO ループではない理由

コミット済み trainer はスモークを含むすべての実行の前後に test ファイルを読み、評価します。学習中の途中評価には validation を使いますが、最終的なベースライン/調整済みモデルのメトリクスは毎回 test から計算します。ハイパーパラメーターを選ぶ間、test の結果を何度も調べてはいけません。

教材用のチューニング手順を作る場合は、実行診断にはスモーク用サブセット、候補の比較には validation を使うよう明示的に修正します。通常のチューニング実行では test を使えないようにし、候補の構成を固定してから、最後に一度だけベースラインと候補を test で比較します。この分離については[PII 評価/リリースワークショップ](07-pii-evaluation-release.md)でも説明します。

| 実験 | 固定するもの | 意図的に変更するもの | validation で選ぶ項目 |
|---|---|---|---|
| アダプターの容量 | データ、対象、学習率、token 予算 | スケーリング方針を明記した上で rank (例: 8 と16) | 再現率、残存 PII、過剰マスキング、学習の安定性 |
| 対象範囲 | データ、rank、decode、予算 | attention のみ、または現在の attention + expert 対象 | 学習可能パラメーターと実測メモリーに対する品質向上 |
| 最適化 | データ、対象、rank、シーケンスポリシー | 一度に1つの学習率を選択 | loss の推移と抽出指標。loss だけではない |
| シーケンスポリシー | 評価レコードと label 契約 | 拒否/分割ポリシー、または根拠を示した token 予算の拡大 | 長文カバレッジと切り詰め率 |
| 拡張 | 元の document family と評価セット | 学習用に限った変換 family を1つ | 稀な type、形式、negative 例に対する挙動 |

これらは実験計画であり、実装済み CLI オプションでも、勝つことが推奨される設定値でもありません。拡張データの派生物は元の family と同じ場所に保ちます。family の分離だけでは、完全一致テキスト、エンティティ、template、ドメインの分離までは保証されません。[データ拡張ワークショップ](06-data-augmentation-workshop.md)ではそれらの監査を明示しています。

データ拡張ワークショップの CPU 演習では別のデータセットを使います。ここで示した1,600件の計算は過去の学習構成についてのもので、新しいラボ出力に暗黙に流用しないでください。

## 9. 実験を SageMaker AI に対応付ける

[実際の launcher](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py)を使って、ローカルの概念とジョブの入力/出力を結び付けます。

| 手順 | 現在の対応関係 | 確認する証拠 |
|---|---|---|
| ローカル構成 | `config/experiment.yaml` と `requirements.lock` | 構成、ソース、依存関係のバージョン |
| ソースバンドル | `generated/source.tar.gz` にソース/構成/requirements が入る | バンドル内容と SHA-256。認証情報/データを再帰的に含めていないこと |
| S3 入力 | 実験用に `source/` と `dataset/` prefix を分離 | アップロードしたオブジェクトの hash、想定するアカウント/bucket/prefix |
| ジョブ内のソース | `/opt/ml/code/config/experiment.yaml`; `SAGEMAKER_PROGRAM=src/train.py` | Toolkit の呼び出し、構成ファイルの存在 |
| データセット channel | `dataset` という名前の File モード channel を1つ | `/opt/ml/input/data/dataset/{train,validation,test}.jsonl` と manifest |
| Trainer の評価 | 学習中は validation データセット。現在の最終比較では test を使用 | 実際の split ID/hash と上記の使い分け |
| MLflow | 構成/バージョン/manifest ファイル、集計メトリクス、最終アダプターファイル | Run ID、artifact の可用性、client/App の互換性 |
| SageMaker モデル出力 | 現在の `output-dir=/opt/ml/model` | 最終ディレクトリの内容、S3 model-artifact URI |

Channel 名によって入力パスが決まります。`dataset` という名前の channel があっても、中身すべてが「学習データ」とは限りません。この channel には3つの異なる split が含まれます。それらから学習する前に、実際のファイル hash を再計算して比較してください。manifest がログに記録されていただけでは、読み込んだファイルが一致した証拠になりません。

### 何が保存されるかを把握する

現在の SFT 出力ディレクトリは `/opt/ml/model/checkpoints` です。checkpoint は `output_dir` 配下に置かれるためです。SageMaker はモデルディレクトリ全体をアップロード用にパッケージ化するため、生成されるモデル artifact には最終アダプターや JSON ファイルに加え、checkpoint も含まれる場合があります。MLflow で明示したアダプターファイルの allowlist によって、SageMaker のディレクトリパッケージ化が変わるわけではありません。

より整理された構成案では、最終アダプターファイルを `/opt/ml/model`、集計出力を `/opt/ml/output/data`、復元可能な checkpoint を `/opt/ml/checkpoints` に分けます。S3 への checkpoint 同期には適切なジョブ設定が必要です。ローカルディレクトリを作成しただけではバックアップになりません。[AWS のストレージパス一覧](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html)と[学習出力の契約](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)を参照してください。

アダプターはベースモデルの置き換えだけで動作するものではありません。再読み込みには正しいベースモデル/revision、tokenizer、アダプター構成、互換性のあるランタイムが必要です。現在のコードではモデル revision を固定していません。再現性を改善する場合は、別途レビューした改善として記録します。

## 10. ハイパーパラメーターを変える前にジョブの段階を診断する

SageMaker の状態とモデル段階の診断では、異なる質問に答えます。`SecondaryStatus` からダウンロード、学習、アップロード中かどうかがわかります。アプリケーションがウェイトを読み込み、ベースラインを評価し、アダプターを保存している間も、ジョブが `Training` のままの場合があります。

次の読み取り専用診断コマンドは、**既存の認可済みジョブ**を対象とするもので、このワークショップでは実行しません。

```bash
: "${TRAINING_JOB_NAME:?Set the existing reviewed job name}"
: "${AWS_REGION:?Set its Region}"
aws sagemaker describe-training-job \
  --region "$AWS_REGION" \
  --training-job-name "$TRAINING_JOB_NAME" \
  --query '{
    status:TrainingJobStatus,
    phase:SecondaryStatus,
    stages:SecondaryStatusTransitions,
    failure:FailureReason,
    model:ModelArtifacts.S3ModelArtifacts,
    trainingSeconds:TrainingTimeInSeconds,
    billableSeconds:BillableTimeInSeconds
  }'
```

レビュー前の失敗情報は非公開に保ちます。`/aws/sagemaker/TrainingJobs` にある対象ジョブのログストリームと、範囲を限定したログ区間を使います。無関係なジョブや学習例をまとめて出力しないでください。AWS の[secondary status の遷移](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_SecondaryStatusTransition.html)と[CloudWatch ロギング](https://docs.aws.amazon.com/sagemaker/latest/dg/logging-cloudwatch.html)を参照してください。

今後の教材用 trainer には、集計情報のみの段階マーカーを加えます。データ検証済み、モデルロード完了、ベースライン完了、アダプター挿入済み、最初の backward pass 完了、最適化完了、artifact 保存済み、評価完了などです。元ドキュメントをログに出さずに、停止箇所を診断しやすくなります。

| 症状 | 最初に区別すること | 次に行う有用な対応 |
|---|---|---|
| モデルロード前に失敗 | ランタイム guard、パッケージ/toolkit の失敗、パス不足 | 段階、設定と channel の対応を読む。rank を調整しない |
| ロード中に OOM | ベースウェイト/配置か、optimizer メモリーか | モデル全体のサイズ、量子化、非量子化 tensor、実際の配置を確認 |
| backward 中に OOM | 活性化か、アダプター/optimizer 状態か | マイクロバッチ/シーケンス予算を減らし、checkpointing と対象範囲を確認 |
| loss が NaN | target の不備か、数値/最適化上の問題か | 教師 label が0件でないこと、値の有限性、BF16 対応、学習率を確認 |
| loss は下がるが再現率が低い | 形式の学習か、エンティティの網羅性か | type、言語、長さ、negative/positive レコード別に validation を調べる |
| 出力が散文または不正な TSV | chat template/EOS/mask か、タスクの曖昧さか | 学習ステップを増やす前に、準備後の実例と decode 契約を検証 |
| 解析/往復スコアは高いが PII が残る | parser の許容性と元に戻せる置換 | 残存 PII と entity 再現率を調べる。解析成功をプライバシー成功とみなさない |
| ジョブ完了後に結果を再ロードできない | artifact ディレクトリの誤り、またはベース/revision の不一致 | artifact 内容を調べ、アダプターを別途再ロードして確認 |

現在の `peak_gpu_memory_bytes` は、モデルロード後に reset し、デフォルト CUDA device 上で計測した PyTorch 割り当てメモリーのピークです。GPU メモリー総量でもロード時のピークでもなく、複数デバイス間の合計でもありません。今後の計測では意味を正確に表示してください。

## 11. ランタイム移行を検証済みの組み合わせとして扱う

[AWS DLC のサポートポリシー](https://aws.github.io/deep-learning-containers/reference/support_policy/)と[イメージカタログ](https://aws.github.io/deep-learning-containers/reference/available_images/)は2026年9月15日に確認しました。旧 `pytorch-training` イメージ系列と新しい `pytorch` 系列を混同しないでください。

| カタログ項目 | SageMaker tag (レジストリホスト名を除く) | Python / OS | パッチ提供終了 |
|---|---|---|---|
| 現在の過去事例 | `pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` | 3.12 / Ubuntu 22.04 | 2026-08-06 |
| 新系列 2.11 | `pytorch:2.11.0-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-04-30 |
| 新系列 2.12 | `pytorch:2.12.1-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-02 |
| 新系列 2.13 | `pytorch:2.13.0-cu133-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-20 |

これらは確認済みのカタログ項目であり、過去の `src/train.py`/マネージド MLflow 経路の置き換えが検証済みという意味ではありません。別の `src/train_execution.py` 経路の2.11 GPU スモークについては[実行記録](README.md#sagemaker-execution-readiness)にあります。2.12 と2.13は未実行のカタログ参照です。また AWS は Ubuntu ベースの PyTorch 2.8～2.10 は完全なパッチ適用ができず、AL2023 ベースの PyTorch 2.11 以降を推奨すると警告しています。過去の launcher は古いリポジトリ名と tag の両方を固定しています。バージョン番号だけの置き換えでは不十分です。

移行では、イメージのリポジトリ/tag/digest、リージョンでの可用性、Python、CUDA/driver/アーキテクチャ、PyTorch、HF/PEFT/TRL/bitsandbytes の依存関係、training toolkit、MLflow client/service を整合させる必要があります。新しい DLC に現在の `torch==2.8.0` lock をインストールすると、意図したフレームワーク移行が元に戻る可能性があります。

それらの選択をレビューした後に限り、認可済み GPU の事前検証で、実際の CUDA/BF16 対応、量子化ロード、想定した対象/dtype、forward/backward、有限 loss、アダプター更新、保存/再読み込みをテストします。**テスト手順を記述しただけでは、実行成功を立証できません。** 上記の別記録にある2.11の実際の証拠を使用し、過去経路の guard も維持してください。

## 12. 理解度を確認する

1. 1 worker でマイクロバッチ1、蓄積8の場合、80回の更新で何回の例提示になるか。**約640回**。ここでの割り切れていて unpacked である前提によります。
2. 「3.3B が active」は、3.3B パラメーターだけメモリーが必要という意味か。**いいえ。** 疎な計算量の説明であり、全ウェイトと学習状態も関係します。
3. PII のないドキュメントから何を学習させるか。**assistant turn の終了で終わる、有効な空の抽出応答**です。すべてが無視される label 列ではありません。
4. 毎回 test スコアを見て rank を選んでよいか。**いいえ。** validation で候補を選び、構成を固定してから、最後に一度だけ test で比較します。
5. 往復成功は PII が削除された証明になるか。**いいえ。** 置換経路が可逆であることを示します。見逃した PII はそのまま残る可能性があります。
6. 対応 DLC tag があれば現在の launcher を実行できるか。**いいえ。** リポジトリ、依存関係、toolkit、ハードウェア、統合契約が検証済みの組み合わせになっている必要があります。

## 主な参考資料

以下はすべて **2026-09-15** に確認しました。コードを読む例ではバージョンを指定した情報源を優先します。

- [LoRA 論文](https://arxiv.org/abs/2106.09685)と[QLoRA 論文](https://arxiv.org/abs/2305.14314)
- [PEFT 0.17.1 LoRA ガイド](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md)と[k-bit 準備のソース](https://github.com/huggingface/peft/blob/v0.17.1/src/peft/utils/other.py)
- [Transformers 4.57.6 bitsandbytes 量子化](https://github.com/huggingface/transformers/blob/v4.57.6/docs/source/en/quantization/bitsandbytes.md)
- [bitsandbytes 0.48.2 の4-bit モジュール](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/0.48.2/docs/source/reference/nn/linear4bit.mdx)
- [TRL 0.24.0 SFT ガイド](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)、[SFTConfig](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_config.py)、[SFTTrainer](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_trainer.py)
- [Qwen モデルカード](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)、[モデル構成](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json)、[固定版 Transformers 実装](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)
- [AWS DLC サポート](https://aws.github.io/deep-learning-containers/reference/support_policy/)と[利用可能なイメージ](https://aws.github.io/deep-learning-containers/reference/available_images/)
- [SageMaker ストレージ/環境変数](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html)と[学習出力](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)

次: [データ拡張ワークショップ](06-data-augmentation-workshop.md)

## クイズ

[QLoRA ファインチューニングワークショップのクイズ](../../quizzes/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop-quiz.md)で概念と計算を確認してください。
