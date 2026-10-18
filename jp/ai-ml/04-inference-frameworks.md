# LLM サービング向け推論フレームワーク

> **検証基準**: 公式リリース、API、chart、ローカルチェックを2026年9月12日に確認。GPU／Neuron モデル実行は未実施。
> **最終更新**: 2026年10月12日

推論エンジン、分散実行レイヤー、Kubernetes controller、プロバイダー gateway は分けて選定してください。「OpenAI 互換」でも、endpoint、field、streaming、tool call、認証が同じとは限りません。

## 推論フレームワークの全体像

![推論エンジン、分散サービング、Kubernetes 運用、プロバイダー gateway の役割の違い。](../.gitbook/assets/en-ai-ml-04-inference-frameworks-0.png)

[インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-0.html)

| コンポーネント | 確認した基準バージョン | 選定時の確認事項 |
| --- | --- | --- |
| NIM LLM/VLM | 2.0.12 のドキュメント、別個の 3.0 提供 | モデル、profile、hardware、support agreement、backend |
| Dynamo | 1.4.2 | 集約／分離サービング、KV transfer、planner、controller |
| AIBrix | 0.7.0 | Envoy Gateway、adapter/controller、autoscaling |
| SGLang | 0.5.19 | モデル、grammar backend、device、実測した workload |
| vLLM / Ray Serve | vLLM 0.29.0 / Ray 2.58.0 / KubeRay 1.7.0 | 個別に検証した image／model／controller の組み合わせ |
| TGI | 3.3.7、maintenance mode | 既存システムの保守と移行計画 |
| Ollama | 0.34.0 | ローカル API アクセス、モデルストレージ、準備方法 |
| LiteLLM | 1.100.1 | プロバイダー適合、認証、fallback、コスト計測 |
| Neuron | SDK 2.32.0、Helm 1.10.0 | インスタンス固有の plugin／compiler／driver 互換性 |

vLLM 0.31.0 は、表にある 0.29.0 のローカル検証後である2026年10月5日にリリースされました。表のバージョンは確認した組み合わせを示し、最新リリースや相互互換性のある一式を示すものではありません。リクエスト単位のマルチモーダル引数を既定で制限する 0.31.0 の変更については、[デプロイ章の更新](02-vllm-deployment.md)を参照してください。

すべてに当てはまる yes／no の機能表は避けてください。Dynamo の planner、vLLM／SGLang の分離実行、CPU と GGUF のサポートは、リリース、backend、hardware によって異なります。adapter の読み込みやモデル alias は、テナント認証の境界ではありません。

## NVIDIA NIM

container、モデル profile、GPU 互換性、support agreement を一緒に確認してください。NIM Operator 3.1.2 は LLM／VLM 2.0.12 container とは別のものです。確認した 2.0.12 リリースのドキュメントでは vLLM 0.27.1 を説明しています。NIM が常に TensorRT-LLM を使うとは限りません。Dynamo ベースの 3.0 提供と 2.0 のデプロイ方法を同一視しないでください。

![承認された経路で NIM リクエストを処理し、準備済みモデルの cache と独立した metrics 収集を行う構成。](../.gitbook/assets/en-ai-ml-04-inference-frameworks-1.png)

[インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-1.html)

### デプロイの準備と profile

AMI、driver／toolkit、device-plugin の要件は [GPU ガイド](01-ai-ml-workloads.md)を参照してください。driver installation を常時有効にすると、プロバイダー AMI と競合する場合があります。Karpenter NodePool／EC2NodeClass、実際にスケジュール可能な CPU／RAM／GPU リソース、device 数を確認してください。GPU 8基を要求する Pod は GPU 1基／4基の node には配置できません。Custom AMI では EKS bootstrap 設定も明示する必要があります。

container の profile 一覧にあるサポート対象 profile ID／name を NIM_MODEL_PROFILE で指定します。古い NIM_MANIFEST_PROFILE や、実在が確認されていない vllm-bf16-tp8 文字列が使えるとは考えないでください。image digest、モデル revision、profile、driver、実際に検証した内容をまとめて記録してください。

NGC の image pull 認証情報と、実行時のモデル download 認証情報は用途が異なります。ドキュメントにある NGC_API_KEY 環境変数の方法は、file-only credential policy を満たしません。承認済みの prepared-model 経路か、検証済み credential adapter を使ってください。実際の key を shell 引数や source に含めてはいけません。内部 Service だけでは推論リクエストを認証できません。

別々の node にある replica 間で、単一の EBS RWO PVC を共有しないでください。replica ごとの storage／local cache、または適切な共有 filesystem を選び、download 失敗、storage 性能、startup probe、rollout をテストします。モデルが常に image に含まれるわけではなく、cache が FSx／S3 と自動同期するわけでもありません。

### Metrics と GenAI-Perf

確認した NIM 2.0.12 のドキュメントでは、native vLLM backend metrics をそのまま返す `/v1/metrics` が公開されています。架空の nim_* 名や `/metrics` を流用せず、実際の名前、単位、label を確認してください。Grafana ConfigMap には対応する datasource／sidecar と Prometheus の scrape 設定が必要です。秒単位の値を変換せずにミリ秒 panel に表示しないでください。

TTFT、ITL、end-to-end latency、成功時の throughput、queueing について workload 固有の SLO を定めます。token 間隔が均一なら、概算は `TTFT + (output tokens - 1) × ITL` に、別途ネットワーク／postprocessing の overhead を加えたものです。500ms や GPU 使用率80%といった値は、普遍的な健全性基準ではありません。

GenAI-Perf 0.0.16 では profile subcommand と synthetic-input-tokens-mean／output-tokens-mean option を使います。以下は準備済みの内部 endpoint に負荷をかける command ですが、この監査では実行していません。先に perf_analyzer、tokenizer、その他の配布依存関係を用意してください。

```bash
genai-perf profile   --endpoint-type chat   --service-kind openai   --url http://127.0.0.1:8000   --model approved-model-alias   --concurrency 2   --synthetic-input-tokens-mean 128   --output-tokens-mean 64   --num-prompts 20   --profile-export-file profile_export.json
```

analyze が JSON の後処理だけを行うとは限りません。sweep 設定によって追加 profiling が実行される場合があります。raw request、失敗、tokenizer、warmup、concurrency、model／backend revision を保存してください。GPU utilization の評価には実際の metrics 収集が必要です。

## NVIDIA Dynamo

公式の Kubernetes 1.4.2 経路では、Dynamo platform、DynamoGraphDeployment (DGD)、DynamoGraphDeploymentRequest (DGDR) を使用します。旧版で使われていた、実在しない dynamo-router／dynamo-worker image、KV_CACHE_HOST、任意の router YAML で実装する構成ではありません。DGDR は profiling と DGD 作成を要求するもので、読み取り専用の確認ではありません。

![Dynamo frontend、設定済み worker、KV 転送。controller／planner がデプロイと capacity を管理する。](../.gitbook/assets/en-ai-ml-04-inference-frameworks-2.png)

[インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-2.html)

### 実際の DGD 構造

この**schema 検証済みの設定**は、公開モデルと上限を定めた実行設定を使う、公式 1.4.2 v1beta1 の集約型サンプルを適合させたものです。platform／controller、namespace、GPU、モデルへのアクセス、networking が必要です。デプロイ前に model／image digest を固定し、実 hardware で確認してください。この監査ではモデルを実行していません。

```yaml
apiVersion: nvidia.com/v1beta1
kind: DynamoGraphDeployment
metadata:
  name: vllm-agg
  namespace: dynamo-system
spec:
  components:
  - name: Frontend
    podTemplate:
      spec:
        containers:
        - image: nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.4.2
          name: main
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: '1'
              memory: 2Gi
    replicas: 1
    type: frontend
  - name: VllmDecodeWorker
    podTemplate:
      spec:
        containers:
        - args:
          - --model
          - Qwen/Qwen3-0.6B
          - --max-model-len
          - '2048'
          - --max-num-seqs
          - '8'
          command:
          - python3
          - -m
          - dynamo.vllm
          image: nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.4.2
          name: main
          resources:
            limits:
              nvidia.com/gpu: '1'
              cpu: '4'
              memory: 12Gi
            requests:
              ephemeral-storage: 2Gi
              cpu: '2'
              memory: 4Gi
          workingDir: /workspace/examples/backends/vllm
    replicas: 1
    type: worker
```

prefill／decode の分離には、両 role、KV connector／format、モデル revision、networking の互換性が必要です。backend や GPU を任意に組み合わせても自動的に相互運用できるわけではありません。KV-aware routing は locality と load のバランスを取りますが、0.7／0.3 の固定式が一般的な実装とは限りません。すべての Dynamo deployment で Redis が KV tensor の必須 store というわけでもありません。

確認した platform chart では、cluster-wide operator が crd-apply init container を使って CRD を管理します。upgradeCRD=false は外部管理を選ぶ設定で、CRD が不要になるわけではありません。planner、discovery、NATS／etcd、Grove／KAI、その他のリリース固有設定を確認してください。chart を render しても、CRD の適用、authorization、稼働中の discovery は検証されません。

## AIBrix

0.7.0 では Envoy Gateway、gateway plugin、controller-manager、metadata service を使用します。Ray ベースの機能では KubeRay を任意で利用できます。以前の単独 aibrix-registry server や /v1/lora/register API は、確認した 0.7.0 のインストール経路ではありません。

### ModelAdapter と PodAutoscaler

実際の ModelAdapter field には baseModel、podSelector、artifactURL があります。replicas を省略すると一致するすべての Pod に adapter が読み込まれ、1 を指定すると1 Pod、その他の値は拒否されます。サンプルの bucket／revision と base model を承認済みの値に置き換えてください。controller の download 権限、runtime 互換性、adapter の容量と lifecycle、テナント認可はそれぞれ別に検証します。

```yaml
apiVersion: model.aibrix.ai/v1alpha1
kind: ModelAdapter
metadata:
  name: support-lora
  namespace: ai-inference
spec:
  baseModel: approved-base-model
  podSelector:
    matchLabels:
      model.aibrix.ai/name: approved-base-model
  artifactURL: s3://REPLACE_WITH_APPROVED_BUCKET/adapters/support/REVISION/
  replicas: 1
```

PodAutoscaler 0.7.0 は metricsSources と HPA／KPA／APA strategy を使います。任意の autoscaler ConfigMap ではありません。この CPU の例には metrics-server、workload の CPU request、controller が必要です。GPU queue に基づく scaling を検証するものではありません。同一 target を複数 scaler が制御しないようにしてください。

```yaml
apiVersion: autoscaling.aibrix.ai/v1alpha1
kind: PodAutoscaler
metadata:
  name: model-cpu
  namespace: ai-inference
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: prepared-model-server
  minReplicas: 1
  maxReplicas: 3
  scalingStrategy: HPA
  metricsSources:
  - metricSourceType: resource
    targetMetric: cpu
    targetValue: '70'
```

## Ray Serve との連携

監査済みの [Ray Serve](ray/04-ray-serve.md) と [KubeRay](ray/02-kuberay-operator.md) の API を使用します。KubeRay reconciliation、Ray worker autoscaling、Serve replica autoscaling は別の役割です。通常の Deployment HPA target として RayCluster を使ったり、自動生成される cluster／Serve Service の名前や selector を推測したりしないでください。

code と依存関係は head だけでなく実行 worker にも届く必要があります。user_config を設定しても constructor の引数は自動的に変わりません。適切な再構成処理を実装してください。互換 API には実際の chat template、streaming、cancel、finish reason、usage、error の対応が必要です。role 文字列を単純に連結し、stream=true を無視するだけでは不十分です。古い Ray 2.9／operator 1.1 の例と、無条件の trust_remote_code=True は削除しました。

## SGLang

0.5.19 の RadixAttention は共通 prefix の KV を再利用します。任意に重なり合う中間部分文字列を、同じように cache できる prefix として扱うことはできません。モデル、KV format、アクセス policy を一致させてください。現在の grammar backend には既定の XGrammar と、Outlines／Llguidance の選択肢があります。「圧縮 FSM のおかげで常に10倍高速」という結論は一般化できません。

![SGLang API／runtime、共通 prefix の KV cache、選択した grammar backend。](../.gitbook/assets/en-ai-ml-04-inference-frameworks-3.png)

[インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-04-inference-frameworks-3.html)

### 構造化リクエストの例

この client は SGLang の json_schema request 形式に対応する承認済み gateway を前提とします。正常終了と出力形式を確認します。検証には合成 response と失敗ケースを返すローカル HTTP fixture を使い、モデルの正確性は測定しません。JSON が妥当でも、事実の正確さや tool 使用権限が保証されるわけではありません。

```python
from pathlib import Path
import json
from urllib.request import Request, urlopen

# Existing private gateway and a scoped credential mounted as a file.
base_url = "https://inference.example.internal/v1"
credential = Path("/run/secrets/inference/token").read_text().strip()
payload = {
    "model": "approved-model-alias",
    "messages": [{"role": "user", "content": "Return the city Seoul and country Korea."}],
    "temperature": 0,
    "max_tokens": 128,
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "location",
            "schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "country": {"type": "string"}},
                "required": ["city", "country"],
                "additionalProperties": False,
            },
        },
    },
}
request = Request(
    base_url + "/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + credential},
    method="POST",
)
with urlopen(request, timeout=30) as response:
    result = json.load(response)
choice = result["choices"][0]
if choice["finish_reason"] != "stop":
    raise RuntimeError("Generation did not complete normally")
location = json.loads(choice["message"]["content"])
if set(location) != {"city", "country"} or not all(isinstance(v, str) for v in location.values()):
    raise ValueError("Unexpected output shape")
print(location)
```

このリリースには SGLang の function／system／user／assistant／gen DSL API が引き続きあります。function を宣言するだけでは推論は実行されません。準備済み RuntimeEndpoint／backend に接続し、実行してください。導入時に Torch、FlashInfer、hardware の互換性を確認します。この監査では完全な GPU SDK をインストールせず、DSL をモデルにも接続していません。

## Hugging Face TGI

公式 repository は**保守モード**を宣言しています。確認した最新 release は 3.3.7（2025年12月19日）です。軽微な修正、documentation、maintenance を受け付け、新規 engine 採用では vLLM／SGLang などを案内しています。新しい project の汎用的な既定候補ではありません。既存 deployment を移行する場合は、model、template、streaming、metrics、SLO の互換性を検証してください。

--quantize=awq を追加しても、通常のモデルから AWQ weight が自動生成されるわけではありません。その形式で準備されたサポート対象モデルを使ってください。floating tag、gated model の認証情報不足、短すぎる liveness deadline は再現性と起動成功を損ないます。

## Ollama

0.34.0 では、モデルの pull と serving は別の操作です。sleep 10 を行う postStart hook だけでは readiness を保証できません。承認済みモデルを事前に配置するか、health check、上限付き retry、失敗時の処理を備えた別の準備手順を使用します。変更され得る model tag と storage permission を記録してください。

ローカル Ollama API にはユーザー認証がありません。公開する前に authorization と path control を前段に置いてください。Pod の localhost のみに bind した server には Service 経由で接続できません。OLLAMA_HOST は listen 範囲を変えますが、認証を追加しません。model-management endpoint と inference endpoint は別々に制限してください。

Modelfile は base model、system prompt、generation setting を定義します。モデルを学習したり Kubernetes image を build したりするものではありません。大規模な multitenancy が可能だと仮定せず、model size、device、backend ごとに CPU／GPU 対応を確認してください。

## LiteLLM

[Agentic AI ガイド](03-agentic-ai-platform.md)にある、監査済み 1.100.1 Router 設定を使用してください。provider gateway は推論 engine とは異なる層です。alias を gpt-4-equivalent と名付けても品質が同等とは限りません。fallback 先は、許可済み provider と data-egress policy を満たす必要があります。

実際の設定 file を proxy command に接続し、必要に応じて client credential、DB／Redis、callback を設定してください。dummy key や ClusterIP は認証ではありません。drop_params=true は意味のある request 条件を取り除く可能性があります。request、成功、失敗、retry、cache cost を区別してください。

## AWS Neuron と Inferentia2

chip、NeuronCore、host RAM／HBM を区別してください。Inferentia2 chip 1基には NeuronCore-v2 が2 core、HBM が32GiBあります。

| Instance | Chip 数 | NeuronCore-v2 | Device HBM (GiB) | Host RAM (GiB) | vCPU |
| --- | --- | --- | --- | --- | --- |
| inf2.xlarge | 1 | 2 | 32 | 16 | 4 |
| inf2.8xlarge | 1 | 2 | 32 | 128 | 32 |
| inf2.24xlarge | 6 | 12 | 192 | 384 | 96 |
| inf2.48xlarge | 12 | 24 | 384 | 768 | 192 |

### Device 割り当てと plugin の経路

aws.amazon.com/neuron は**device 全体**を割り当て、aws.amazon.com/neuroncore は**core**を割り当てます。以前の inf2.xlarge の例は、device 1基、vCPU 4個、RAM 16GiB の node に neuron:2、CPU 8個、RAM 24GiB を要求しており、配置できません。NEURON_RT_VISIBLE_CORES は runtime の範囲を選ぶだけで、未割り当ての device を作りません。選択した release の NUM_CORES と logical-core policy の優先関係を確認してください。

確認した公式 Helm 1.10.0 には device-plugin、scheduler、node-problem-detector の option があります。導入前に render された DaemonSet、hostPath、RBAC、障害復旧の動作を確認してください。この command はローカルに出力を生成するだけです。

```bash
helm template neuron-audit oci://public.ecr.aws/neuron/neuron-helm-chart   --version 1.10.0 --namespace kube-system --include-crds > neuron-rendered.yaml
```

SDK 2.32.0 のドキュメントでは、2つの別々の経路を扱っています。**Inf2／Trn1／Trn2 向けの NxD Inference plugin 0.5.x と vLLM 0.16**、および**Trn2／Trn3 のみを対象とする新しい vLLM Neuron beta 0.24.0.1.1.0**です。詳細な NxD guide にはまだ 0.5.0／SDK 2.29 があり、overview の 0.5.3 と異なります。選ぶ plugin tag、DLC、正確な依存関係を検証してください。Inf2 に最新 beta を入れたり、古い 2.18 DLC に pip install を追加したりしても互換性の検証にはなりません。

Neuron compile では、サポートされる model implementation、shape／batch／sequence bucket、TP、compiler／SDK、hardware、cache artifact が必要です。未使用の tp_degree dictionary を一般的な Transformers model と一緒に torch_neuronx.trace に渡しても、分散 causal-LM serving にはなりません。compiler output file と tokenizer directory は別の artifact です。この監査では compiler も Neuron instance も実行していません。

## 性能、コスト、運用

出典のない A100 順位表と、一律40～70%のコスト削減という記述は削除しました。同じ model／revision／precision、input／output token 分布、concurrency、成功率、SLO、warmup、日付を明記した価格を比べてください。1日100万 request を30日実行すれば3,000万 request です。仮定上の月額48,000ドルは、1,000 request 当たり1.60ドルです。以前の0.80ドルという値は算術的に誤っていました。この例は現在の AWS 価格ではありません。

engine を変更する際は、実際の payload、template、streaming、usage、失敗時の動作を回帰テストしてください。shard された model group と独立 replica を区別し、StatefulSet の順序付き readiness が互いの起動を待つ worker を block しないか確認します。StatefulSet だけでは TP／PP、rendezvous、NCCL は設定されません。

model size、restart／download concurrency、authorization、cost を踏まえ、local cache、EBS、EFS、FSx を比較してください。EFS が常に FSx より遅いわけではなく、過去の gp3 limit も現在の保証ではありません。[GPU／storage の例](01-ai-ml-workloads.md)を参照してください。

運用開始前に、実環境で authentication、TLS、管理用 path、probe、placement、quota、scaler の単独所有、metrics の単位、固定した model revision、cache lifecycle、rollout／rollback、中断からの復旧をテストしてください。

## 検証範囲

検証したのは、公式 chart／CRD、実際の SDK／CLI source、ローカル HTTP request／failure fixture、Markdown、image です。GPU／Neuron でのモデル実行、throughput／cost の測定、cloud deployment、モデル download は実施していません。schema／chart の検証に成功しても、admission、authorization、モデル互換性、本番利用の準備が整ったとは限りません。

## 参考資料

- [NIM 2.0 release note](https://docs.nvidia.com/nim/large-language-models/2.0.12/about-nim-llm/release-notes.html)
- [NIM の設定](https://docs.nvidia.com/nim/large-language-models/2.0.12/reference/environment-variables.html)
- [NIM の observability](https://docs.nvidia.com/nim/large-language-models/2.0.12/reference/logging-and-observability.html)
- [Dynamo 1.4.2](https://github.com/ai-dynamo/dynamo/tree/v1.4.2)
- [AIBrix 0.7.0](https://github.com/aibrix/aibrix/tree/v0.7.0)
- [SGLang 0.5.19 の structured output](https://github.com/sgl-project/sglang/blob/v0.5.19/docs/docs/advanced_features/structured_outputs.mdx)
- [TGI の保守モード告知](https://github.com/huggingface/text-generation-inference)
- [Ollama 0.34.0](https://github.com/ollama/ollama/tree/v0.34.0)
- [GenAI-Perf 0.0.16](https://pypi.org/project/genai-perf/0.0.16/)
- [Neuron SDK 2.32.0 の推論経路](https://github.com/aws-neuron/aws-neuron-sdk/blob/v2.32.0/libraries/vllm-neuron/neuron-inference-overview.rst)
- [Inf2 のアーキテクチャ](https://awsdocs-neuron.readthedocs-hosted.com/en/latest/about-neuron/arch/neuron-hardware/inf2-arch.html)
- [Neuron の Kubernetes component](https://github.com/aws-neuron/neuron-helm-charts)

## クイズ

[推論フレームワークのクイズ](../quizzes/ai-ml/04-inference-frameworks-quiz.md)
