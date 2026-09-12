# EKS 上の AI/ML ベストプラクティス

> **最終更新**: September12,2026
> **ベースライン**: inference-perf0.6.1 / SOCI0.15.0 / Karpenter1.14.1 / External Secrets2.10.0

改善は、同一のワークロードに対するレイテンシ、成功率、スループット、コスト、リカバリで評価します。GPU、snapshotter、共有機能が、固定された高速化率やコスト削減率を保証することはありません。

![Benchmarking, startup optimization, devices, networking/storage, observability, cost and security evaluated with measurements and recovery checks.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-0.png)

[インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-0.html)

## LLM 推論のベンチマーク

![Distinct measurement windows for first output, token intervals, end-to-end latency and aggregate throughput/goodput.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-1.png)

[インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-1.html)

| メトリクス | 定義と注意点 |
| --- | --- |
| TTFT | 送信から最初の**空でない出力**を受信するまで。最初の HTTP/SSE フレームにトークンが含まれているとは限らない |
| ITL | トークン/チャンクの間隔。1つのネットワークチャンクに複数のトークンが含まれることがある |
| TPOT | 最初のトークン以降のツール定義による平均値。出力トークンが1個以下の場合は未定義 |
| E2E | リクエストから完了までの時間。キュー、ネットワーク、後処理の境界を記録する |
| リクエストスループット | 成功して完了したリクエスト数 / 指定した測定ウィンドウ |
| トークンスループット | ウィンドウ内の出力トークン数の合計 / 時間。リクエスト単位 TPS の非加重平均ではない |
| Goodput | 成功条件とレイテンシ SLO の基準を満たしたリクエストのレート |

実際のトークンのタイムスタンプがある場合、ITL の平均は(最後のトークン時刻 - 最初のトークン時刻)/(トークン数 - 1)です。非ストリーミング応答では実際の TTFT/ITL を測定できません。tokenizer、空/単一トークンの出力、失敗、ウォームアップの除外を明記してください。500ms/50ms は普遍的な SLO ではありません。

### inference-perf と GenAI-Perf

inference-perf は Kubernetes SIGs/wg-serving のベンチマークツールです。調査対象の PyPI パッケージは0.6.1ですが、その Git タグの pyproject には依然として0.5.0と記載されています。このメタデータの不一致を記録しておきます。実際の CLI は、以前の benchmark --endpoint --prompt-length というインターフェースではなく、--config_file または --server.type のような構造化オプションを使用します。

この**内部モック**設定はモデルサーバーを呼び出しません。実際の0.6.1CLI は、1worker で3件のリクエストを完了しました。モックのトークン数はゼロで、TTFT/TPOT は null になるため、これらはモデル性能の結果ではありません。

```yaml
api:
  type: chat
  streaming: false
data:
  type: mock
load:
  type: concurrent
  stages:
    - concurrency_level: 1
      num_requests: 3
  num_workers: 1
  worker_max_concurrency: 1
  base_seed: 17
server:
  type: mock
  base_url: http://127.0.0.1:8000
report:
  request_lifecycle:
    summary: true
    per_stage: true
    per_request: true
storage:
  local_storage:
    path: ./benchmark-fixture-results
```

```bash
inference-perf --config_file benchmark-fixture.yaml
```

実際のエンドポイントに切り替える前に、サーバー/API のタイプ、モデルのエイリアス、ストリーミング、tokenizer、認証を検証してください。設定にシークレットヘッダーが含まれることがあり、マージ後の設定はログに記録されるため、認証情報の受け渡しとマスキングを検証してください。出力ファイル、生のリクエスト/レスポンス、失敗を保存し、データセットのプライバシーと利用許諾を尊重してください。

一定レート/Poisson レートは1秒あたりの到着数を測定し、concurrent 負荷は同時実行数を制御します。数値が同じ設定でも等価ではありません。単一リクエストのベースライン、上限付きの負荷ランプ、バースト、現実的な分布をテストしてください。飽和曲線だけでは CPU/GPU/メモリのボトルネックを証明できません。プロファイリング、キュー、ネットワーク、クライアント側の能力を確認してください。

GenAI-Perf0.0.16では、でっち上げた --backend vllm の組み合わせではなく、監査済みの [profile/endpoint/service/token オプション](04-inference-frameworks.md)を使用してください。GPU メトリクスは別途収集が必要です。負荷生成側の CPU/ネットワーク上限も確認してください。ベンチマーク Job には、検証済みのイメージ、設定キー、PVC、デッドライン、そして重複した負荷を考慮したリトライのセマンティクスが必要です。

## コンテナ起動の最適化

![Measure Pod placement, image fetch/unpack, container startup, model loading and readiness separately.](../.gitbook/assets/en-ai-ml-07-ai-ml-best-practices-2.png)

[インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-07-ai-ml-best-practices-2.html)

イメージの転送、展開、モデルのダウンロード/ロード、readiness はそれぞれ個別に測定してください。出典のない「常に5〜15分」や「80〜95%削減」といった表は削除しました。45GB/1Gbps≈360秒は理想化された転送の算術にすぎず、圧縮後のサイズ、プロトコル、ディスク、並行性のオーバーヘッドを除外しています。測定された pull 時間ではありません。

モデル成果物を外部に置くとイメージの変更/pull を減らせる可能性がありますが、ダウンロードとキャッシュ管理のコストが加わります。環境によっては、あらかじめ用意したイメージが適切な場合もあります。初期化処理は失敗を伝播させ、リビジョン、チェックサム、完了を検証しなければなりません。以前の S3 sync の後に成功する echo を実行する構成は、ダウンロード失敗を隠す可能性があったため削除しました。

マルチステージビルドでは、実行可能ファイルや共有ライブラリを含め、Python インタープリタ/ABI と CUDA/ランタイムライブラリを揃える必要があります。Ubuntu22.04の python3.11と pip3が同じインタープリタを使うと仮定したり、site-packages だけをコピーしたりしないでください。サポートされているディストリビューションのパッケージ/wheel を使用し、イメージ内で import とエントリポイントをテストしてください。root ファイルシステムは読み取り専用にし、書き込み可能な cache/tmp/model のマウントを明示するのが望ましいです。

### SOCI0.15

SOCI は遅延イメージロードをサポートしますが、起動直後にすべての重み/ライブラリを読み込む場合は効果が小さくなることがあります。インデックスが存在するだけでは、CRI が SOCI snapshotter を使うようには設定されません。containerd/CRI の統合、イメージ/インデックスのダイジェスト、レジストリの互換性を検証してください。ホストの containerd ソケットを公開する未検証の privileged DaemonSet は削除しました。

バージョン0.15の create/push は、--ref ではなく位置引数としてイメージ参照を取ります。現行の getting-started では、SOCI 対応イメージの作成に convert を使用します。standalone モードでは、containerd や sudo なしでローカルの OCI レイアウトを処理します。

```bash
soci convert --standalone --format oci-dir input-oci-layout output-soci-layout
```

入力は通常の docker-save の tarball ではなく、OCI レイアウトでなければなりません。すべてのレイヤーが min-layer-size より小さい場合、変換は失敗することがあります。この監査では min-layer-size=0を明示して合成レイヤー1つを変換し、8個の blob ダイジェストを検証しました。コンテナ起動のベンチマークは実施していません。公開時には、変換後のイメージとインデックスをまとめて保存してください。

### Bottlerocket ブートストラップ

1.64では、`bootstrap-containers.<name>.user-data` は**base64 データ**であり、bootstrap コンテナがファイルとして読み取ります。設定に平文のシェルテキストを書いても自動的に実行されるわけではありません。ソースイメージは実在し、ホストのイメージストア/名前空間を正しく使う必要があります。静的な images-prefetched=true ラベルは成功の証拠にはなりません。

mode=once は実行後に off になります。essential=true の失敗は起動を停止させ、false は失敗を許容するため、readiness の要件に合わせて設定してください。allowed-unsafe-sysctls は privileged コンテナのスイッチではありません。プリフェッチがノード準備時間に与える影響も測定に含めてください。

## GPU、Neuron、ストレージの選択

パラメータ数×バイト数は重みの下限にすぎません。アーキテクチャに応じた KV cache、アクティベーション、ワークスペース、通信バッファ、フラグメンテーション、シャーディングの制約を含めてください。13B FP16の重み≈26GB は24GB には収まりません。70B FP16≈140GB は24GB GPU4基の合計を超えます。ホストの CPU を増やしても、GPU の VRAM は変わりません。

p4d.24xlarge の8×40GB と、p4de の8×80GB A100を区別してください。G5g は Arm/T4G を使用するため、イメージ/カーネルのアーキテクチャを検証してください。inf2.48xlarge の192vCPU/768GiB ホスト RAM、12chip/24NeuronCore/384GiB HBM については[監査済みの Inf2 表](04-inference-frameworks.md)を参照してください。P5のようなファミリー名は、すべてのサイズで GPU 数を固定するものではありません。選定時には、利用可能な世代、リージョン、クォータ、価格を再確認してください。

LoRA は学習対象のアダプタの状態を削減しますが、ベースの重み/アクティベーションは保持され、QLoRA とは異なります。ほとんどの LoRA モデルが24GB に収まると仮定する関数は使用しないでください。ピークメモリ、レイテンシ、スループット、再起動回数を測定してください。

10TB というデータセットのしきい値だけでストレージを選定しないでください。アクセスパターン、並行性、メタデータ、レイテンシ、セマンティクス、耐久性、コストを比較してください。現行の汎用 gp3のドキュメントには、ベースライン3000IOPS/125MiB/s、最大80000IOPS/2000MiB/s が記載されており、サイズ/IOPS/インスタンスの制約を受けます。Outposts は異なります。過去の16000IOPS/1GB/s という上限は、一般に現行の値ではありません。

EFS の Elastic スループット、FSx/CSI/S3 の関連付け、Mountpoint の POSIX 制限については[インフラストラクチャガイド](06-ai-infrastructure.md)を参照してください。S3のスループットは無限ではなく、レイテンシも固定ではありません。EFS が FSx より常に遅いわけでもありません。インスタンスストア/tmpfs は一時的なものです。GPU の KV cache は通常 GPU メモリ上に存在し、自動的に SSD/tmpfs に置かれることはありません。

### モデルキャッシュの検証

config.json ファイルの存在は、重みのダウンロードが完了した証拠にはなりません。イミュータブルな読み取り専用ストレージとして公開する前に、信頼できるリリースマニフェスト/リビジョンに対して**すべてのファイル**を検証してください。ダウンローダーの競合や部分的に書き込まれたファイルを防いでください。

このローカル検証ツールはダウンロードや削除を一切行いません。テストでは、完全なファイル、誤ったリビジョン、部分的/欠落した重み、パストラバーサル、外部シンボリックリンクを扱っています。マニフェストの信頼性と検証後のイミュータブル性は、別途満たすべき要件です。

```python
from pathlib import Path
import hashlib
import re


def verify_model_cache(root, manifest, expected_revision):
    """Verify files against a separately trusted release manifest; no downloads/deletion."""
    root = Path(root).resolve(strict=True)
    if manifest.get("revision") != expected_revision:
        raise ValueError("Model revision mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Empty or invalid release manifest")
    for relative, expected_hash in files.items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError("Unsafe manifest path")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("Invalid SHA256")
        target = (root / name).resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("File escapes the cache or is not a regular file")
        digest = hashlib.sha256()
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_hash:
            raise ValueError("Incomplete or corrupt model file: " + relative)
    return root
```

チェックポイントには、[学習/リカバリの例](05-model-training.md)にあるように、optimizer/RNG/データカーソルとシャードの状態が必要です。転送、チェックサム、完了マニフェストが成功する前に、以前の有効なコピーを削除しないでください。以前の ls/xargs rm -rf のループは、ディレクトリの内容とチェックポイントのパスを混同し、読み取り専用マウント越しの削除を試みていたため削除しました。最初の同期を30分遅らせたり、終了時のフラッシュを省略したりすると、作業消失のリスクが高まります。

## ネットワークとスケジューリング

EFA は適したワークロードの通信を改善しますが、すべての DDP 実行に必須ではありません。インターフェース、同一 AZ への配置、ドライバ/libfabric/aws-ofi-nccl、Pod のリソース、セキュリティグループ、実際のトランスポートを検証してください。RAID0やサブネットのタグで有効になるものではありません。未検証の NCCL_TIMEOUT や、そのままコピーした Ring/Simple/IB_DISABLE の設定は避けてください。torchrun --nnodes はノード数を数えるもので、全プロセス数である WORLD_SIZE ではありません。

Karpenter1.14.1の実際の placementGroupSelector を使用してください。aws:ec2:placement-group タグは placement API ではなく、aws: はユーザータグの名前空間ではありません。この**スキーマ例**には、承認済みの AMI/subnet/SG/role の識別子と、既存の placement group が必要です。この例では amiFamily に AL2023を指定しているため、置き換えるものは他 OS 用の AMI ではなく、検証済みの EKS AL2023 AMI でなければなりません。この例は EFA の networkInterfaces 設定を完結させるものではありません。

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: prepared-gpu-class
spec:
  role: REPLACE_WITH_APPROVED_NODE_ROLE
  amiSelectorTerms:
  - id: ami-0123456789abcdef0
  subnetSelectorTerms:
  - id: subnet-0123456789abcdef0
  securityGroupSelectorTerms:
  - id: sg-0123456789abcdef0
  placementGroupSelector:
    name: prepared-training-placement-group
  amiFamily: AL2023
```

### Disruption Budget と Spot

この budget は月曜〜金曜の**09:00〜17:00UTC** に適用されます。以前の0 9-17 * * 1-5は17:00まで毎時8時間のウィンドウを開始しており、保護が翌日の01:00まで延長されていました。同時に有効な budget はより厳しい制限が適用され、ローカルのタイムゾーンに自動的に追従することはありません。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-gpu-pool
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: prepared-gpu-class
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: '0'
      schedule: 0 9 * * 1-5
      duration: 8h
    - nodes: 30%
```

budgets.nodes=0が制限するのは自発的な中断だけで、Spot の中断、ノード障害、強制的な expiration は制限しません。spot のみの requirements は必須指定であり、on-demand へのフォールバックを伴う優先指定ではありません。ScheduleAnyway の topology spread はソフトな制約です。実際のレプリカ数、キャパシティ、AZ 分散を検証してください。

terminationGracePeriodSeconds=120は、EC2が120秒を与えることを保証しません。実際の終了処理を通して、ゲートウェイの readiness/ドレイン、エンドポイントの伝播、SIGTERM、アクティブなストリーム、リトライ、重複をテストしてください。存在しない vLLM の /drain API をでっち上げないでください。推論のキャッシュ、セッション、TP グループは状態と再起動コストを伴います。

## オブザーバビリティとコスト

[現行の vLLM メトリクス](02-vllm-deployment.md)と [DCGM ルール](06-ai-infrastructure.md)を使用してください。KV の占有率は、以前の gpu_cache_usage_perc ではなく vllm:kv_cache_usage_perc です。キャッシュが満杯になれば即座にリクエストが拒否されると仮定するのではなく、キュー/プリエンプションとバックエンドの挙動を観測してください。prefix ヒット率は、現行の hit/query カウンタから、分母ゼロを扱いつつ導出してください。

DCGM の FB_USED/FREE は MiB 単位の gauge、XID_ERRORS は最後のコードです。存在しない FB_TOTAL や、gauge に対する increase() は避けてください。温度だけではサーマルスロットリングを証明できません。クロック、電力、スロットリング理由、ワークロードを比較してください。Prometheus のラベル/ヒストグラムの集約を揃え、式に対する avg_over_time では有効なサブクエリ構文を使用してください。

VPA の Off モードは CPU/メモリの推奨値を提供するもので、GPU インスタンスを自動選択するものではありません。以前のライトサイジングスクリプトは最初の系列だけを参照し、0〜1の比率を50/90と比較していたため削除しました。ワークロード横断でピーク、キュー、SLO、そして削減後のリカバリを確認してください。

コスト削減は、実際のリージョン/OS/購入条件、稼働率、アイドル/障害時間、ストレージ、転送、運用を用いて記録してください。Spot/Savings Plans/RI は割引率とキャパシティ保証が異なります。60〜90%といった固定の表や、最適化による削減率の単純な足し合わせは避けてください。コミットメント購入の判断は、測定したベースラインと変動性に基づいて別途行ってください。

## モデルアクセスとシークレット管理

S3の ListBucket と GetObject は、それぞれバケット ARN とオブジェクト ARN、そしてサポートされる条件キーを使用します。汎用バケットでは、ABAC を明示的に有効化した後、aws:ResourceTag/Environment のようなバケットタグ条件を使用できます。ABAC はデフォルトで無効です。タグ条件だけをコピーするのではなく、バケットの状態、信頼できるタグ管理権限、アイデンティティ/バケットのポリシー、アクションとリソースの対応を検証してください。有効化しても、必要な Allow が作られたり、他の Deny ポリシーが上書きされたりすることはありません。信頼ポリシーに紐づく ServiceAccount の namespace/name、SDK の認証情報チェーン、実際のリクエストの ID を検証してください。vLLM はすべての S3モデル URI を自動的にダウンロードするわけではありません。

調査対象の ESO2.10.0の CRD は **v1を serve** しており、v1beta1は served=false です。この例は、すでに承認済みの同一 namespace の SecretStore を参照しています。リモートのキー、権限、ローテーション、target のライフサイクルは別途準備してください。

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: model-download-token
  namespace: ai-ml
spec:
  refreshPolicy: Periodic
  refreshInterval: 1h
  secretStoreRef:
    name: approved-secrets-manager
    kind: SecretStore
  target:
    name: model-download-credential
    creationPolicy: Owner
  data:
  - secretKey: token
    remoteRef:
      key: approved/model-download
      property: token
```

Kubernetes Secret はボリュームとしてマウントし、必要に応じてアプリケーションがファイルを再読み込みするようにしてください。subPath マウントは自動更新を受け取りません。環境変数や起動時にのみ読み込まれる値も、自動的にはリロードされません。ESO の refresh は、上流での認証情報の発行/ローテーションそのものではありません。プロバイダ側のローテーション、Secret へのアクセス、アプリケーションのリロードをそれぞれ検証してください。

CloudTrail の Secrets Manager API の記録は、ローカルの Secret ファイルに対するアプリケーションのすべての読み取りを捕捉しません。kubectl describe が一般に SecretKeyRef の値を出力すると主張しないでください。ただし環境変数での受け渡しは、プロセスやデバッグの経路を露出させる点で、ファイルによる認証情報のポリシーとは異なります。例やログに実際のシークレットを出力してはいけません。

NetworkPolicy には CNI による enforcement が必要です。セレクタの AND/OR セマンティクス、デフォルトの namespace 名ラベル、TCP と UDP 両方の DNS を検証してください。10.0.0.0/8のヘルスチェック向け開放と、「インターネットの443は S3のみを意味する」というルールは削除しました。準備済みモデルを使う場合は、実行時の egress を必要な経路に限定し、ゲートウェイで推論 API と管理 API を区別してください。

監査ログには、ユーザー/ワークロードの ID、モデルのリビジョン、アクション、結果、リクエスト ID を記録し、必要に応じてプロンプトやシークレットをマスクしてください。containerd の CRI ログを Docker 形式として解析したり、request を含む行だけを保持したりすると、監査イベントを失う可能性があります。ConfigMap だけでなく、実際のコレクタ、パーサー、IAM、バッファ、保持期間、配信失敗を検証してください。

## 検証の範囲

元のガイドとクイズの本文すべて、および87個のユニークなコードブロックをレビューしました。検証には、ネイティブな inference-perf のモックリクエスト3件、SOCI のローカル OCI 変換、キャッシュの6ケース、Karpenter/ESO の3つのスキーマ、cron の計算が含まれます。GPU/実モデルのベンチマーク、コンテナ起動時間の測定、ホストへの SOCI インストール、クラウドリソース、シークレットプロバイダの実行は行っていません。

## 参考資料

- [inference-perf0.6.1](https://github.com/kubernetes-sigs/inference-perf/tree/v0.6.1)
- [SOCI0.15 CLI](https://github.com/awslabs/soci-snapshotter/blob/v0.15.0/docs/cli-usage.md)
- [Bottlerocket1.64 bootstrap settings](https://bottlerocket.dev/en/os/1.64.x/api/settings/bootstrap-containers/)
- [Karpenter1.14.1 CRDs](https://github.com/aws/karpenter-provider-aws/tree/v1.14.1/pkg/apis/crds)
- [Karpenter disruption](https://karpenter.sh/docs/concepts/disruption/)
- [ESO2.10 ExternalSecret CRD](https://github.com/external-secrets/external-secrets/blob/helm-chart-2.10.0/config/crds/bases/external-secrets.io_externalsecrets.yaml)
- [Kubernetes Secret updates](https://kubernetes.io/docs/concepts/configuration/secret/)
- [S3 general-purpose bucket ABAC enablement](https://docs.aws.amazon.com/AmazonS3/latest/userguide/buckets-tagging-enable-abac.html)
- [EBS gp3 performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)

## クイズ

[AI/ML ベストプラクティスクイズ](../quizzes/ai-ml/07-ai-ml-best-practices-quiz.md)
