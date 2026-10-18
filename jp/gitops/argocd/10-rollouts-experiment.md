# Argo Rollouts Experiment の詳細

> **対応 version**: Argo Rollouts 1.10.0（過去の1.8.3／Kubernetes 1.33の報告は別途識別）
> **最終更新**: 2026年9月11日

## 目次

- [Experiment とは](#what-is-an-experiment)
- [Resource の階層と生成の連鎖](#resource-hierarchy-and-creation-chain)
- [Name 生成規則](#name-generation-rules)
- [Traffic routing の挙動](#traffic-routing-behavior)
- [Measurement と判定: AnalysisRun](#measurement-and-verdict-analysisrun)
- [結果の伝播と Rollout の状態遷移](#result-propagation-and-rollout-state-transitions)
- [動作例](#working-example)
- [kubectl plugin での観測](#observing-with-the-kubectl-plugin)
- [検証結果](#verification-results)
- [次のステップ](#next-steps)
- [参考資料](#references)
- [クイズ](#quiz)

## Experiment とは {#what-is-an-experiment}

Experiment は Argo Rollouts の CRD で、一時的な ReplicaSet を作成して analysis を実行します。Baseline／canary の比較、deploy 前の確認、実 traffic を使った実験に対応します。**ReplicaSet を分けても、本番 traffic が自動的に隔離されるわけではありません。** Service selector、router、test traffic を明示的に設計してください。

| 観点 | Canary step | Experiment step |
|---|---|---|
| Pod | Rollout の canary ReplicaSet | 一時的な Experiment ReplicaSet |
| Traffic | 基本 canary では Pod 数の比率で近似。設定時は weight routing | Service／router 設定に応じて隔離 traffic または実 traffic |
| 完了 | 新しい stable version になり得る | Cleanup delay policy に従って replica がゼロに scale down |
| Analysis | Version 固有の品質 metric | Baseline／canary 別 metric と test traffic |

単独の Experiment と Rollout の Experiment step の両方に対応しています。`specRef` と `weight` は **Rollout step template** の field です。単独 Experiment では selector と Pod template を直接定義します。

## Resource の階層と生成の連鎖 {#resource-hierarchy-and-creation-chain}

Rollout が Experiment step に到達すると、次の順に resource が作成されます。

![Rollout が Experiment を作成し、Experiment が spec.templates から baseline／canary ReplicaSet を起動し、spec.analyses から AnalysisRun を作成する。templateName が参照する AnalysisTemplate は AnalysisRun 用の metric 定義を提供する。](../../.gitbook/assets/en-gitops-argocd-10-rollouts-experiment-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-10-rollouts-experiment-0.html)

1. Experiment step に到達する更新で Experiment が作られます。初回作成では stable が確立され、通常の canary step は実行されません。**後続する Pod-template の変更**で Experiment が動くことを確認してください。
2. Controller は template ごとに ReplicaSet を作成し、要求された replica が利用可能になるのを待ちます。Readiness／`minReadySeconds` が影響します。Progress deadline を超えると Experiment は失敗します。
3. すべてが利用可能になると `status.availableAt` が記録され、analysis が開始します。設定した `duration` はその時点から測定します。
4. 完了結果が伝播します。Successful は次へ進み、Failed／Error は abort、**Inconclusive は pause** します。ReplicaSet／Service の cleanup は別の reconciliation 処理です。

## Name 生成規則 {#name-generation-rules}

Experiment 系 resource には規則的な名前が付き、名前だけで owner Rollout、revision、step を追跡できます。

| Resource | 規則 | 測定例 |
|---|---|---|
| Experiment | `<rollout-name>-<new-version PodTemplateHash>-<revision>-<step-index>` | `demo-app-74d8d8b4fb-2-0` |
| ReplicaSet | `<experiment-name>-<template-name>` | `demo-app-74d8d8b4fb-2-0-baseline`、`demo-app-74d8d8b4fb-2-0-canary` |
| AnalysisRun | `<experiment-name>-<analysis-name>` | `demo-app-74d8d8b4fb-2-0-success-rate` |

上記は `demo-app` Rollout の revision 2 update における step index 0 の Experiment での例です。[検証結果](#verification-results)の tree 出力で実際の階層を確認できます。

これらは基本名です。Experiment／AnalysisRun の名前が衝突すると数字の suffix が付くことがあります。実際の resource は ownerReferences と status で特定してください。

## Traffic routing の挙動 {#traffic-routing-behavior}

`app: demo-app` のみを選択する production Service は Experiment Pod も選択する可能性があります。Hash 固有の selector も確認してください。Hash が別であるだけで十分に隔離されると仮定しないでください。この例では production Service に `traffic-class: production`、Experiment template に `traffic-class: experiment` を設定します。ほかの Service と mesh route も確認してください。

以下は Rollout `spec.strategy.canary.steps` の entry に使う**2つの代替案**です。Service を作成しても、外部 traffic が自動的に接続されるわけではありません。

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

- `service: {}` は template 用 Service を作ります。既定名は ReplicaSet 名と一致し、`service.name` で上書きできます。宣言する container port は application が実際に listen する port と一致させてください。
- `weight` は template ごとに設定します。既定の合計 weight が100なら5は5%です。独自 `maxTrafficWeight` を使う場合は単位を確認してください。Weight を設定すると Service も作成されます。
- Weighted Experiment には対応 router が必要です。Version 1.10 のドキュメントでは ALB／Istio／SMI が挙げられています。通常の canary weight に対応していても、NGINX やすべての plugin が Experiment の traffic split に対応するとは限りません。

## Measurement と判定: AnalysisRun {#measurement-and-verdict-analysisrun}

AnalysisRun は条件に従って provider の結果を評価します。これは **AnalysisTemplate spec の fragment** です。Provider 全体は以下の例にあります。Success rate が欠損または範囲外なら両条件が false となり、Inconclusive になります。型が不正、HTTP／collection failure、expression error の場合は Error 経路をたどります。

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

| 条件 | Measurement の結果 |
|---|---|
| `failureCondition=true` | Failed。Success より優先 |
| `successCondition=true`、`failureCondition=false` | Successful |
| 両方 false | Inconclusive |
| Provider または expression error | Error |

Success condition だけなら false は Failed です。Failure condition だけなら false は Successful です。どちらの condition もなければ、collection error のない measurement は Successful になります。

| Field | 意味 | 上限超過時の結果 |
|---|---|---|
| `failureLimit` | 許容する Failed measurement 数 | Failed |
| `inconclusiveLimit` | 許容する Inconclusive measurement 数 | Inconclusive |
| `consecutiveErrorLimit` | 連続 Error の許容数。既定4 | Error |

`failureLimit: 1` は2回目の Failed measurement で超過します。`count` が数えるのは HTTP request ではなく measurement です。`count` なしで `interval` を設定すると無期限に繰り返します。どちらも省略すると1回だけ測定します。重複する3つの metric window は、独立した3 sample ではありません。

## 結果の伝播と Rollout の状態遷移 {#result-propagation-and-rollout-state-transitions}

![Experiment の Successful は次へ進み、Failed／Error は abort、Inconclusive は pause となる。Cleanup は delay policy の後に行われる。](../../.gitbook/assets/en-gitops-argocd-10-rollouts-experiment-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-10-rollouts-experiment-1.html)

| Experiment の結果 | Rollout の挙動 |
|---|---|
| Successful | 次の step に進む |
| Failed／Error | Abort／Degraded。設定済み routing／replica policy に従い stable に戻す |
| Inconclusive | `InconclusiveExperiment` で pause。調査して Operator が判断する |

Version 1.10 は duration **かつ** analysis が終わるまで常に待つわけではありません。必須の analysis がすべて成功すると、duration より前に Experiment が完了する場合があります。未完了の必須 analysis があると duration 経過後も実行が続く場合があります。必須でない analysis は duration 終了時に停止されることがあります。Duration も必須 analysis もなければ、明示的に終了するまで実行されます。この例では duration を省き、有限回の必須 analysis で完了させます。

`scaleDownDelaySeconds` の既定値は30秒です。Terminal status、Pod 数ゼロ、Service 削除は同時に保証されません。Controller は delay 後に scale down し、利用可能な replica 数がゼロになると生成 Service を削除します。ReplicaSet／AnalysisRun object は history／GC policy に応じて残ることがあります。Abort しても database 変更や外部副作用は取り消されません。

## 動作例 {#working-example}

これは**制御フローを学ぶための例**です。Rollouts 1.10.0／CRD と plugin を install し、namespace `demo` に以下の JSON を返す `metrics-mock` という HTTP Service を別途用意してください。Server 実装は含まれないため、これらの manifest だけを apply しても成功は保証されません。固定 mock value は baseline／canary の品質や実 traffic 比率を測定しません。

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

専用 lab cluster で file を apply し、最初の stable revision を確立してから Pod-template annotation を変更し、Experiment step を動かします。これは controller の流れを示すもので、新しい image の品質確認ではありません。Argo CD 管理 resource の変更は live patch せず Git で行ってください。Mock rate が0.99なら成功、0.50なら `failureLimit` 超過で abort、rate が欠けていれば Inconclusive pause を確認できます。最後に lab resource の cleanup 範囲を確認してください。

```bash
kubectl argo rollouts status demo-app -n demo --timeout=180s
# A second Pod-template revision exercises the steps; the image stays unchanged in this demo.
kubectl patch rollout demo-app -n demo --type merge \
  -p '{"spec":{"template":{"metadata":{"annotations":{"demo-revision":"v2"}}}}}'
kubectl argo rollouts get rollout demo-app -n demo --watch
```

`setWeight: 20` は `trafficRouting` がない場合の Pod 比率による近似です。Replica が3つでは user request を正確に20%へ振り分けられません。実際の比較には test traffic、instrumentation／scraping、十分な sample、以下の **Experiment ReplicaSet** hash argument が必要です。これらは `podTemplateHashValue: Baseline/Canary` field ではありません。

```yaml
args:
- name: baseline-hash
  value: '{{templates.baseline.podTemplateHash}}'
- name: canary-hash
  value: '{{templates.canary.podTemplateHash}}'
```

[Metric 比較の例](05-traffic-management.md#experiments)を参照してください。

## kubectl Plugin で観測する {#observing-with-the-kubectl-plugin}

`kubectl argo rollouts get rollout <name> --watch` は Experiment の階層全体（Experiment → ReplicaSet → Pod と AnalysisRun）をリアルタイムに表示します。以下の出力は元文書にある過去の1.8.3記録であり、現行例を新たに実行した結果ではありません。名前、時刻、cleanup timing を1.10.0の新しい結果として解釈しないでください。

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

過去の trace では revision 2 の main ReplicaSet が scale down しています。ただし、別の step 順序や Service／router 設定でも本番への露出がないことを証明するものではありません。AnalysisRun は事後分析用に、measurement 履歴を status に保持します。

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

元文書では、1.8.3 の source build と Kubernetes 1.33／kwok（実際の control-plane binary、Pod／node lifecycle は simulation）での結果が報告されています。実行した manifest 一式、生 API dump、log は添付されていないため、このレビューでは報告を再現できません。以下は過去の観測結果であり、現行1.10.0での新しい結果でも、実 traffic、Pod readiness、application 品質の証拠でもありません。

| 過去の項目 | 元文書の報告 |
|---|---|
| Experiment step で Experiment を自動作成。Name = `<rollout>-<PodHash>-<revision>-<step>` | 報告値: `demo-app-74d8d8b4fb-2-0`（revision 2、step 0） |
| Template から ReplicaSet を作成。Name = `<experiment>-<template>` | 報告値: `...-2-0-baseline`、`...-2-0-canary`、各1 replica |
| `service: {}` の template 用 Experiment scope Service を作成して cleanup | 報告値: `...-2-0-canary` Service を作成し、Experiment 後の削除を確認 |
| すべての template が healthy になった後 AnalysisRun を作成。`interval: 15s`／`count: 3` で繰り返し測定 | 報告値: 15秒おきの測定を3回記録し、`successCondition` は Successful と評価 |
| 成功経路: 60秒の duration 経過 → Experiment Successful → Experiment RS を0に scale → 次の step（`setWeight 20`）→ Rollout Healthy | 報告値: 動作 |
| 失敗経路: Metric 劣化 → `failed (2) > failureLimit (1)` で AnalysisRun Failed → Experiment Failed → Rollout abort（Degraded）、stable は維持 | 報告値: 動作（abort message に該当 metric 名がそのまま表示） |

## 次のステップ {#next-steps}

1. **[Traffic Management](05-traffic-management.md)**: Experiment step を canary／blue-green strategy、Ingress integration と組み合わせます。
2. **[Best Practices](09-best-practices.md)**: Progressive delivery の運用上の best practice を学びます。

## 参考資料 {#references}

- [Experiment の公式ドキュメント](https://argoproj.github.io/argo-rollouts/features/experiment/)
- [Analysis の公式ドキュメント](https://argoproj.github.io/argo-rollouts/features/analysis/)
- [Experiment CRD 仕様](https://argoproj.github.io/argo-rollouts/features/specification/)

- [1.10.0 Experiment state machine](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/experiments/experiment.go)
- [1.10.0 Rollout pause／abort 処理](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/rollout/experiment.go)
- [1.10.0 ReplicaSet cleanup](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/experiments/replicaset.go)

## クイズ {#quiz}

この章の理解を確認するには、[Rollouts Experiments のクイズ](../../quizzes/gitops/argocd/10-rollouts-experiment-quiz.md)を解いてください。
