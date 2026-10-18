# Argo Rollouts Experiment の詳細

> **対応バージョン**: Argo Rollouts 1.10.0（過去の1.8.3／Kubernetes 1.33 の報告は別途区別）
> **最終更新**: 2026年9月11日

## 目次

- [Experiment とは](#what-is-an-experiment)
- [リソース階層と生成の流れ](#resource-hierarchy-and-creation-chain)
- [名前の生成規則](#name-generation-rules)
- [トラフィックルーティングの動作](#traffic-routing-behavior)
- [測定と判定: AnalysisRun](#measurement-and-verdict-analysisrun)
- [結果の伝播と Rollout の状態遷移](#result-propagation-and-rollout-state-transitions)
- [動作例](#working-example)
- [kubectl plugin で観測する](#observing-with-the-kubectl-plugin)
- [検証結果](#verification-results)
- [次のステップ](#next-steps)
- [参考資料](#references)
- [クイズ](#quiz)

## Experiment とは {#what-is-an-experiment}

Experiment は Argo Rollouts の CRD で、一時的な ReplicaSet を作成して分析を実行します。Baseline と canary の比較、デプロイ前の確認、実トラフィックを使った実験に利用できます。**ReplicaSet を分けるだけでは、本番トラフィックは隔離されません。** Service の selector、ルーター、テストトラフィックを明示的に設計してください。

| 観点 | Canary step | Experiment step |
|---|---|---|
| Pod | Rollout の canary ReplicaSet | 一時的な Experiment ReplicaSet |
| トラフィック | 基本的な canary では Pod 数の比率で近似。設定時は重み付けルーティング | Service／ルーターの設定に応じた隔離トラフィックまたは実トラフィック |
| 完了 | 新しい stable version になる可能性がある | cleanup delay policy に従って replica 数をゼロに縮小 |
| 分析 | バージョン固有の品質指標 | Baseline／canary 別の指標とテストトラフィック |

単独の Experiment と Rollout の Experiment step の両方を使用できます。`specRef` と `weight` は **Rollout step template** のフィールドです。単独の Experiment では selector と Pod template を直接定義します。

## リソース階層と生成の流れ {#resource-hierarchy-and-creation-chain}

Rollout が Experiment step に到達すると、次の順序でリソースが作成されます。

![Rollout が Experiment を作成し、Experiment が spec.templates から baseline／canary ReplicaSet を起動し、spec.analyses から AnalysisRun を作成する。templateName が参照する AnalysisTemplate は AnalysisRun のメトリクス定義を提供する。](../../.gitbook/assets/en-gitops-argocd-10-rollouts-experiment-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-10-rollouts-experiment-0.html)

1. Experiment step に到達する更新で Experiment が作成されます。初回作成時に stable が確立され、通常の canary step は省略されます。**その後に Pod template を変更したとき**の Experiment の動作を確認してください。
2. Controller は template ごとに ReplicaSet を作成し、要求された replica 数が利用可能になるまで待ちます。Readiness と `minReadySeconds` が影響します。Progress deadline を超えると Experiment は失敗します。
3. すべての replica が利用可能になると `status.availableAt` を記録し、分析を開始します。設定した `duration` はこの時点から測定されます。
4. 完了結果が伝播します。Successful は次へ進み、Failed／Error は中断し、**Inconclusive は一時停止**します。ReplicaSet／Service の削除は別の reconciliation 処理で行われます。

## 名前の生成規則 {#name-generation-rules}

Experiment 関連リソースには規則に沿った名前が付き、名前だけで親の Rollout、revision、step を追跡できます。

| リソース | 規則 | 実測例 |
|---|---|---|
| Experiment | `<rollout-name>-<new-version PodTemplateHash>-<revision>-<step-index>` | `demo-app-74d8d8b4fb-2-0` |
| ReplicaSet | `<experiment-name>-<template-name>` | `demo-app-74d8d8b4fb-2-0-baseline`、`demo-app-74d8d8b4fb-2-0-canary` |
| AnalysisRun | `<experiment-name>-<analysis-name>` | `demo-app-74d8d8b4fb-2-0-success-rate` |

上記は `demo-app` Rollout の revision 2 の更新で、step index 0 に作成された Experiment の例です。[検証結果](#verification-results)のツリー出力で実際の階層を確認できます。

これらは基本名です。Experiment／AnalysisRun の名前が衝突すると、数字の suffix が付くことがあります。実際のリソースは ownerReferences と status で特定してください。

## トラフィックルーティングの動作 {#traffic-routing-behavior}

`app: demo-app` のみを選択する本番 Service は、Experiment の Pod も選択する可能性があります。ハッシュ固有の selector も確認してください。ハッシュが異なるだけで十分に分離されると仮定しないでください。この例では本番 Service に `traffic-class: production`、Experiment template に `traffic-class: experiment` を設定します。ほかの Service とメッシュルートも確認してください。

以下は Rollout `spec.strategy.canary.steps` のエントリに使う**2つの代替案**です。Service を作成しても、外部トラフィックが自動的に接続されるわけではありません。

```yaml
- experiment:
    duration: 1m
    templates:
    - name: baseline
      specRef: stable
      service: {}
    - name: canary
      specRef: canary
      service: {}
```

```yaml
- experiment:
    duration: 1m
    templates:
    - name: baseline
      specRef: stable
      weight: 5
    - name: canary
      specRef: canary
      weight: 5
```

- `service: {}` は template 用の Service を作成します。既定名は ReplicaSet 名と同じで、`service.name` で上書きできます。宣言するコンテナーポートはアプリケーションが実際に listen するポートと一致させてください。
- `weight` は template ごとに設定します。合計 weight の既定値が100なら、5は5%です。独自の `maxTrafficWeight` を使う場合は単位を確認してください。`weight` を設定すると Service も作成されます。
- 重み付けを使う Experiment には、対応するルーターが必要です。Version 1.10 のドキュメントでは ALB／Istio／SMI が挙げられています。通常の canary の重み付けに対応していても、NGINX やすべての plugin が Experiment のトラフィック分割に対応するとは限りません。

## 測定と判定: AnalysisRun {#measurement-and-verdict-analysisrun}

AnalysisRun は条件に基づいて provider の結果を評価します。以下は **AnalysisTemplate spec の一部**で、provider 全体は後の例にあります。成功率が欠損または許容範囲外の場合、両条件が false となり Inconclusive になります。不正な型、HTTP リクエスト/collection の失敗、式の評価エラーは Error 経路をたどります。

```yaml
metrics:
- name: success-rate
  interval: 15s
  count: 3
  successCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil &&
    asFloat(payload.success_rate) >= 0.95 && asFloat(payload.success_rate) <= 1
  failureCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil &&
    asFloat(payload.success_rate) >= 0 && asFloat(payload.success_rate) < 0.95
  failureLimit: 1
  inconclusiveLimit: 1
  consecutiveErrorLimit: 2
```

| 条件 | 測定結果 |
|---|---|
| `failureCondition=true` | Failed。Success より優先 |
| `successCondition=true`、`failureCondition=false` | Successful |
| 両方 false | Inconclusive |
| Provider または expression error | Error |

成功条件だけの場合、false は Failed です。失敗条件だけの場合、false は Successful です。どちらの条件もなければ、collection error のない測定は Successful になります。

| フィールド | 意味 | 上限超過時の結果 |
|---|---|---|
| `failureLimit` | 許容する Failed の測定回数 | Failed |
| `inconclusiveLimit` | 許容する Inconclusive の測定回数 | Inconclusive |
| `consecutiveErrorLimit` | 連続 Error の許容回数。既定値は4 | Error |

`failureLimit: 1` は、2回目の失敗測定で上限を超えます。`count` が数えるのは HTTP リクエストではなく測定回数です。`count` なしで `interval` を設定すると無期限に繰り返します。`count` と `interval` の両方を省略すると、1回だけ測定します。重複する3つのメトリクスウィンドウは、独立した3つのサンプルではありません。

## 結果の伝播と Rollout の状態遷移 {#result-propagation-and-rollout-state-transitions}

![Experiment が Successful なら次へ進み、Failed／Error なら中断し、Inconclusive なら一時停止する。cleanup は delay policy に従って行われる。](../../.gitbook/assets/en-gitops-argocd-10-rollouts-experiment-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-10-rollouts-experiment-1.html)

| Experiment の結果 | Rollout の動作 |
|---|---|
| Successful | 次の step に進む |
| Failed／Error | Abort／Degraded。設定済みのルーティング/replica policy に従って stable に戻す |
| Inconclusive | `InconclusiveExperiment` で一時停止。調査してオペレーターが判断する |

Version 1.10 では、duration **と**分析の両方が終わるまで常に待つわけではありません。必須分析がすべて成功すると、duration 経過前に Experiment が完了する場合があります。未完了の必須分析があると、duration 経過後も実行が続く場合があります。必須でない分析は duration 終了時に停止されることがあります。duration も必須分析もなければ、明示的に終了するまで実行されます。この例では duration を省略し、回数を指定した必須分析で完了させます。

`scaleDownDelaySeconds` の既定値は30秒です。終端 status、Pod 数がゼロになること、Service の削除が同時に起きる保証はありません。Controller は delay 後に scale down し、利用可能な replica 数がゼロになると生成した Service を削除します。ReplicaSet／AnalysisRun オブジェクトは履歴/GC policy に応じて残ることがあります。Abort してもデータベースへの変更や外部への副作用は取り消されません。

## 動作例 {#working-example}

これは**制御フローを学ぶための例**です。Rollouts 1.10.0/CRD と plugin をインストールし、namespace `demo` に以下の JSON を返す `metrics-mock` という HTTP Service を別途用意してください。サーバーの実装は含まれないため、これらのマニフェストだけを適用しても成功は保証されません。固定の mock 値では、baseline／canary の品質や実トラフィック比率は測定できません。

```json
{"status":"ok","success_rate":0.99}
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: demo
---
apiVersion: v1
kind: Service
metadata:
  name: demo-production
  namespace: demo
spec:
  selector:
    app: demo-app
    traffic-class: production
  ports:
  - name: http
    port: 9898
    targetPort: http
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate-check
  namespace: demo
spec:
  metrics:
  - name: success-rate
    interval: 15s
    count: 3
    successCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil
      && asFloat(payload.success_rate) >= 0.95 && asFloat(payload.success_rate) <= 1
    failureCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil
      && asFloat(payload.success_rate) >= 0 && asFloat(payload.success_rate) < 0.95
    failureLimit: 1
    inconclusiveLimit: 1
    consecutiveErrorLimit: 2
    provider:
      web:
        url: http://metrics-mock.demo.svc.cluster.local/metrics.json
        jsonPath: '{$}'
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-app
  namespace: demo
spec:
  replicas: 3
  revisionHistoryLimit: 3
  progressDeadlineSeconds: 180
  selector:
    matchLabels:
      app: demo-app
  strategy:
    canary:
      steps:
      - experiment:
          scaleDownDelaySeconds: 30
          templates:
          - name: baseline
            specRef: stable
            replicas: 1
            metadata:
              labels:
                traffic-class: experiment
                experiment-role: baseline
            service: {}
          - name: canary
            specRef: canary
            replicas: 1
            metadata:
              labels:
                traffic-class: experiment
                experiment-role: canary
            service: {}
          analyses:
          - name: success-rate
            templateName: success-rate-check
            requiredForCompletion: true
      - setWeight: 20
      - pause:
          duration: 10s
  template:
    metadata:
      labels:
        app: demo-app
        traffic-class: production
      annotations:
        demo-revision: v1
    spec:
      containers:
      - name: app
        image: ghcr.io/stefanprodan/podinfo:6.15.0
        ports:
        - name: http
          containerPort: 9898
        readinessProbe:
          httpGet:
            path: /readyz
            port: http
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
```

専用の lab cluster でファイルを適用し、最初の stable revision を確立してから Pod template の annotation を変更して Experiment step を実行します。これは controller の流れを示すもので、新しい image の品質確認ではありません。Argo CD 管理下のリソースは live patch せず、Git で変更してください。mock rate が0.99なら成功、0.50なら `failureLimit` を超えて中断し、rate が欠けていれば Inconclusive で一時停止する動作を確認できます。最後に lab リソースの削除範囲を確認してください。

```bash
kubectl argo rollouts status demo-app -n demo --timeout=180s
# A second Pod-template revision exercises the steps; the image stays unchanged in this demo.
kubectl patch rollout demo-app -n demo --type merge \
  -p '{"spec":{"template":{"metadata":{"annotations":{"demo-revision":"v2"}}}}}'
kubectl argo rollouts get rollout demo-app -n demo --watch
```

`setWeight: 20` は `trafficRouting` がない場合の Pod 数の比率による近似です。replica が3つでは、ユーザーリクエストを正確に20%へ振り分けられません。実際に比較するには、テストトラフィック、計測/スクレイピング、十分なサンプル、以下の **Experiment ReplicaSet** のハッシュ引数が必要です。これらは `podTemplateHashValue: Baseline/Canary` フィールドではありません。

```yaml
args:
- name: baseline-hash
  value: '{{templates.baseline.podTemplateHash}}'
- name: canary-hash
  value: '{{templates.canary.podTemplateHash}}'
```

[Metric 比較の例](05-traffic-management.md#experiments)を参照してください。

## kubectl plugin で観測する {#observing-with-the-kubectl-plugin}

`kubectl argo rollouts get rollout <name> --watch` は Experiment の階層全体（Experiment → ReplicaSet → Pod、および AnalysisRun）をリアルタイムで表示します。以下の出力は元文書に記録された過去の1.8.3のもので、現行例を新たに実行した結果ではありません。名前、時刻、cleanup のタイミングを1.10.0での新しい結果として解釈しないでください。

```
$ kubectl argo rollouts get rollout demo-app -n demo
Name:            demo-app
Namespace:       demo
Status:          ◌ Progressing
Strategy:        Canary
  Step:          0/3
  SetWeight:     0
  ActualWeight:  0

NAME                                                  KIND         STATUS         AGE  INFO
⟳ demo-app                                            Rollout      ◌ Progressing  51s
├──# revision:2
│  ├──⧉ demo-app-74d8d8b4fb                           ReplicaSet   • ScaledDown   29s  canary
│  └──Σ demo-app-74d8d8b4fb-2-0                       Experiment   ◌ Running      29s
│     ├──⧉ demo-app-74d8d8b4fb-2-0-baseline           ReplicaSet   ✔ Healthy      29s
│     │  └──□ demo-app-74d8d8b4fb-2-0-baseline-gvgnq  Pod          ✔ Running      29s  ready:1/1
│     ├──⧉ demo-app-74d8d8b4fb-2-0-canary             ReplicaSet   ✔ Healthy      29s
│     │  └──□ demo-app-74d8d8b4fb-2-0-canary-jq6lb    Pod          ✔ Running      29s  ready:1/1
│     └──α demo-app-74d8d8b4fb-2-0-success-rate       AnalysisRun  ◌ Running      29s  ✔ 2
└──# revision:1
   └──⧉ demo-app-779c8779bf                           ReplicaSet   ✔ Healthy      51s  stable
```

過去のトレースでは revision 2 の main ReplicaSet が scale down しています。ただし、step の順序や Service／ルーターの設定が異なる場合にも、本番トラフィックに露出しないことを証明するものではありません。AnalysisRun は事後分析に使えるよう、測定履歴を status に保持します。

```
$ kubectl get analysisrun demo-app-74d8d8b4fb-2-0-success-rate -n demo \
    -o jsonpath='{.status.metricResults[0]}' | python3 -m json.tool
{
    "consecutiveSuccess": 2,
    "count": 2,
    "measurements": [
        {
            "finishedAt": "2026-07-17T01:24:09Z",
            "phase": "Successful",
            "value": "{\"error_rate\":0.004,\"status\":\"ok\",\"success_rate\":0.99}"
        },
        ...
    ],
    "name": "success-rate",
    "phase": "Running",
    "successful": 2
}
```

## 検証結果 {#verification-results}

元文書では、1.8.3 のソースをビルドし、Kubernetes 1.33/kwok（実際の control plane バイナリを使用し、Pod/ノードのライフサイクルをシミュレーション）で得た結果を報告しています。実行したマニフェスト一式、生の API dump、ログが添付されていないため、このレビューでは報告を再現できません。以下は過去の観測結果であり、現行の1.10.0で新たに得た結果でも、実トラフィック、Pod の Ready 状態、アプリケーション品質の証拠でもありません。

| 過去の項目 | 元文書の報告 |
|---|---|
| Experiment step で Experiment を自動作成。名前 = `<rollout>-<PodHash>-<revision>-<step>` | 報告値: `demo-app-74d8d8b4fb-2-0`（revision 2、step 0） |
| template から ReplicaSet を作成。名前 = `<experiment>-<template>` | 報告値: `...-2-0-baseline`、`...-2-0-canary`、各1 replica |
| `service: {}` を指定した template 用の Experiment 専用 Service を作成して削除 | 報告値: `...-2-0-canary` Service を作成し、Experiment 後の削除を確認 |
| すべての template が正常になった後に AnalysisRun を作成。`interval: 15s`/`count: 3` で繰り返し測定 | 報告値: 15秒間隔で3回測定し、`successCondition` は Successful と判定 |
| 成功経路: 60秒の duration 経過 → Experiment Successful → Experiment の ReplicaSet を0に縮小 → 次の step（`setWeight 20`）→ Rollout Healthy | 報告値: 動作を確認 |
| 失敗経路: メトリクス悪化 → `failed (2) > failureLimit (1)` で AnalysisRun Failed → Experiment Failed → Rollout を中断（Degraded）、stable は維持 | 報告値: 動作を確認（中断メッセージに該当するメトリクス名がそのまま表示） |

## 次のステップ {#next-steps}

1. **[トラフィック管理](05-traffic-management.md)**: Experiment step を canary／blue-green 戦略や Ingress 連携と組み合わせます。
2. **[ベストプラクティス](09-best-practices.md)**: 段階的デリバリーの運用上のベストプラクティスを学びます。

## 参考資料 {#references}

- [Experiment の公式ドキュメント](https://argoproj.github.io/argo-rollouts/features/experiment/)
- [Analysis の公式ドキュメント](https://argoproj.github.io/argo-rollouts/features/analysis/)
- [Experiment CRD 仕様](https://argoproj.github.io/argo-rollouts/features/specification/)

- [1.10.0 Experiment の状態遷移](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/experiments/experiment.go)
- [1.10.0 Rollout の一時停止/中断処理](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/rollout/experiment.go)
- [1.10.0 ReplicaSet の削除](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/experiments/replicaset.go)

## クイズ {#quiz}

この章の理解を確認するには、[Rollouts Experiment のクイズ](../../quizzes/gitops/argocd/10-rollouts-experiment-quiz.md)を解いてください。
