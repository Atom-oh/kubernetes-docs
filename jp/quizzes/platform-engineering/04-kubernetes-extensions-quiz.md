# Kubernetes 拡張メカニズム クイズ

[Kubernetes extensions](../../platform-engineering/04-kubernetes-extensions.md)

元の 20 の問題トピックは、現在の API と挙動に照らしてレビュー済みです。

## 1. CRD は何のためのものですか？

<details>
<summary>回答を表示</summary>

Kubernetes API にカスタム resource 型と入力 schema を登録するためのものです。CRD それ自体が workload の挙動を実装するわけではありません。

</details>

## 2. reconciliation loop は何を行いますか？

<details>
<summary>回答を表示</summary>

繰り返し発生する event、再起動、競合を処理しながら、観測された状態と望ましい状態を一致させます。状態が既に一致している場合は不要な更新を避けます。

</details>

## 3. Operator を定義するものは何で、その限界は何ですか？

<details>
<summary>回答を表示</summary>

Operator はカスタム API と controller を使ってドメイン知識を実装します。それらを作成しただけでは、backup、failover、upgrade が安全になるわけではありません。

</details>

## 4. mutating webhook は何を返せますか？

<details>
<summary>回答を表示</summary>

リクエストを許可/拒否し、必要に応じて JSONPatch を伴う AdmissionReview response を返します。リクエストの UID/version は保持し、patch のバイト列は Base64 でエンコードします。

</details>

## 5. Filter plugin は何を行いますか？

<details>
<summary>回答を表示</summary>

Pod の要件を満たせない node を除外します。filter を通過しても binding や実行が完了するわけではありません。

</details>

## 6. aggregation と CRD はどう違いますか？

<details>
<summary>回答を表示</summary>

CRD は既存の API server のカスタム resource ストレージ/バリデーションを利用します。aggregation は別の server に委譲するため、TLS、認証、認可、discovery、ストレージの運用が必要になります。

</details>

## 7. finalizer は何を提供しますか？

<details>
<summary>回答を表示</summary>

削除が完了する前に、controller がクリーンアップを終える機会を与えます。文字列自体が何らかのクリーンアップを実行するわけではなく、調査せずに削除すると外部 resource が残る可能性があります。

</details>

## 8. PostBind はいつ実行されますか？

<details>
<summary>回答を表示</summary>

binding が成功した後の情報提供用のステージであり、あらゆるエラーからの復旧手段ではありません。失敗/キャンセルされた予約に対しては Unreserve などの経路を実装します。

</details>

## 9. 現在の Istio における Pod 単位の injection はどのように制御しますか？

<details>
<summary>回答を表示</summary>

Pod または workload の Pod template の label に sidecar.istio.io/inject を設定します。古い annotation を既定として使うのではなく、namespace の injection/revision label と優先順位を確認します。

</details>

## 10. Score の結果はどのように使われますか？

<details>
<summary>回答を表示</summary>

正規化と plugin の重みを組み合わせて、実行可能な node を順位付けします。同点時の選択や失敗時の処理も scheduler の挙動に含まれます。

</details>

## 11. CRD の schema と必須 field はどこに置きますか？

<details>
<summary>回答を表示</summary>

spec.versions[].schema.openAPIV3Schema 配下に置きます。トップレベルの required: [spec] と spec 内の required: [image] は、それぞれ異なる条件を強制します。

</details>

## 12. ownerReferences について何を確認しなければなりませんか？

<details>
<summary>回答を表示</summary>

owner の UID、namespace/スコープ、既存の controller 所有権を確認します。GC は propagation/finalizer に依存し、名前が一致するだけでは他の workload を引き取る権限にはなりません。

</details>

## 13. VAP と validating webhook はどう違いますか？

<details>
<summary>回答を表示</summary>

ValidatingAdmissionPolicy は 1.30 以降 stable であり、CEL をプロセス内で評価します。webhook はリモート呼び出し、TLS、可用性の管理が必要です。VAP でもスコープと validationActions を指定する binding が必要です。

</details>

## 14. controller-runtime は何を提供しますか？

<details>
<summary>回答を表示</summary>

manager、client/cache、reconciliation のセットアップ、leader election を提供します。カスタム API 型、scheme、RBAC、ドメインロジックは提供しないため、ライブラリと Kubernetes Go モジュールのバージョンを揃えてください。

</details>

## 15. conversion webhook は何のためのものですか？

<details>
<summary>回答を表示</summary>

CRD の API version 間で表現を変換するためのものです。served/storage version、storedVersions、意味の保持を確認します。すべての CRD に conversion webhook が必要なわけではありません。

</details>

## 16. image を必須とし、replicas を 1 から 5 の範囲に制限する WebApp CRD を書いてください。

<details>
<summary>回答を表示</summary>

これには spec 自体も必須とし、status/scale の経路を分離することが必要です。実際の status.replicas と selector は controller が設定しなければなりません。

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames: [wa]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [image]
              properties:
                replicas:
                  type: integer
                  default: 1
                  minimum: 1
                  maximum: 5
                image:
                  type: string
                  minLength: 1
                port:
                  type: integer
                  default: 8080
                  minimum: 1
                  maximum: 65535
            status:
              type: object
              properties:
                replicas:
                  type: integer
                availableReplicas:
                  type: integer
                selector:
                  type: string
                observedGeneration:
                  type: integer
                  format: int64
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
          labelSelectorPath: .status.selector
```

</details>

## 17. Deployment を検証する webhook を production に限定するにはどうしますか？

<details>
<summary>回答を表示</summary>

apps/v1 の deployments の CREATE/UPDATE にマッチさせ、kubernetes.io/metadata.name: production を選択します。実際の検証用 server/Service/path、CA bundle、failurePolicy、timeoutSeconds、sideEffects、admissionReviewVersions を設定します。ガイドの /mutate handler は Deployment の validator ではありません。replica の上限だけを制限する場合は、その VAP/binding の例を使い、`deployments` と `deployments/scale` の両方にマッチさせて、HPA や `kubectl scale` による更新が制限を回避できないようにします。

</details>

## 18. 堅牢な reconciliation の流れを説明してください。

<details>
<summary>回答を表示</summary>

NotFound は正常完了として扱います。削除中は冪等なクリーンアップを完了させてから、自身の finalizer のみを削除します。外部 resource を作成する前に finalizer を永続化し、子 resource の所有権を確認して、所有する field を reconcile します。競合はリトライし、変化した観測状態を patch します。擬似コードを実行可能な controller と称してはいけません。

</details>

## 19. 分散データベースの Operator を設計する際に必要なものは何ですか？

<details>
<summary>回答を表示</summary>

schema と workload の作成に加えて、primary の fencing、quorum、replica 同期、backup/WAL リカバリのテスト、ストレージのライフサイクル、移行の互換性、障害を設計します。Service、StatefulSet、CronJob を作成するだけではデータの安全性は確立されません。

</details>

## 20. カスタム scheduler はどのように実装し検証すべきですか？

<details>
<summary>回答を表示</summary>

対象となる Kubernetes マイナーバージョンの framework インターフェースに対して plugin をコンパイル/登録します。profile 名と Pod の schedulerName を揃え、Filter/Score と予約、permit、binding の失敗をテストします。YAML だけでは plugin をインストールできません。単純な zone 要件であれば、まず node affinity を検討してください。

</details>
