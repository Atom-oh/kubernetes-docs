# Kube Resource Orchestrator (kro) クイズ

[kro](../../platform-engineering/03-kro.md)

これらの問題は、kro 0.9.4 を使用した元の 20 のトピックを保持しています。

## 1. kro のコアコンセプトは何ですか？

<details>
<summary>回答を表示</summary>

RGD で API schema と resource graph を定義し、CEL 参照から依存関係を推論して、インスタンスを reconcile します。kro は命令型スクリプトランナーではありません。

</details>

## 2. 管理対象 resource の定義はどこで宣言しますか？

<details>
<summary>回答を表示</summary>

spec.resources 配下で、各エントリの id と template または externalRef を使用して宣言します。以前の childResources は現在の RGD field ではありません。

</details>

## 3. kro は Helm と併用して何を提供しますか？

<details>
<summary>回答を表示</summary>

resource-reference graph と継続的なインスタンス reconciliation を提供します。Helm は chart rendering と release management を提供します。両者は併用できます。どちらもすべての workload に対して常に優れているわけではありません。

</details>

## 4. インスタンス入力は CEL でどのように参照しますか？

<details>
<summary>回答を表示</summary>

`${schema.spec.replicas}` のように schema.spec または schema.metadata を使用します。.parent や Go-template 構文は使用しません。

</details>

## 5. 条件付き resource inclusion はどのように設定しますか？

<details>
<summary>回答を表示</summary>

includeWhen に Boolean CEL expression を使用します。条件を変更すると resource が追加または prune される可能性があるため、stateful resource の lifecycle への影響を確認してください。

</details>

## 6. 管理対象 resource の status 値はどこに projection しますか？

<details>
<summary>回答を表示</summary>

spec.schema.status 配下に CEL expression を定義します。たとえば `${deployment.status.availableReplicas}` です。statusMappings は現在の field ではありません。

</details>

## 7. 依存関係と readiness はどのように順序付けられますか？

<details>
<summary>回答を表示</summary>

他の resource ID への CEL 参照から DAG が推論されます。dependents は、存在する場合、readyWhen 条件も待機します。cycle は拒否され、YAML の記述順は依存関係の代わりにはなりません。

</details>

## 8. インスタンスが削除されると何が起こりますか？

<details>
<summary>回答を表示</summary>

現在の kro は ApplySet inventory と deletion wave を使用して、dependents を先に削除し、finalizer を保持します。child finalizer は進行を妨げる可能性があります。external-reference target は削除されません。

</details>

## 9. インスタンスの変更を監視するのは何ですか？

<details>
<summary>回答を表示</summary>

kro の dynamic instance controller が変更を監視し、graph を reconcile します。RGD/GraphRevision の validation と compilation はインスタンスの進行に影響します。

</details>

## 10. kubectl apply は何を行いますか？

<details>
<summary>回答を表示</summary>

CR の desired state を作成または更新し、その後 controller が reconcile します。apply の成功は graph compilation やアプリケーションの readiness を意味するものではなく、transactional な外部への影響を保証するものでもありません。

</details>

## 11. RGD とは何ですか？

<details>
<summary>回答を表示</summary>

ResourceGraphDefinition は、生成される API schema、管理対象 resource、status relationship を定義します。これはアプリケーションインスタンスの CR とは異なります。

</details>

## 12. Helm values に相当する入力を提供するのは何ですか？

<details>
<summary>回答を表示</summary>

生成された API インスタンスの spec です。その SimpleSchema の type、default、bound は、template が実際に使用する field と一致している必要があります。

</details>

## 13. 別の resource はどのように参照しますか？

<details>
<summary>回答を表示</summary>

`${deployment.spec.selector.matchLabels}` や `${service.metadata.name}` のように、resource ID を直接参照します。.children は使用しません。

</details>

## 14. 管理対象 resource を追跡し、削除の診断を支援するものは何ですか？

<details>
<summary>回答を表示</summary>

現在の ApplySet inventory、owner metadata、internal.kro.run/apply-order deletion wave を確認します。作り出した kro.run/owner annotation を追跡契約全体として扱わないでください。

</details>

## 15. 入力 schema はどのように validation されますか？

<details>
<summary>回答を表示</summary>

SimpleSchema は生成される CRD の OpenAPI schema になり、Kubernetes はそれを使用してインスタンスを validation します。RGD の構造、graph-compiler の CEL type checking、runtime readiness は別個の確認です。

</details>

## 16. 例の NginxApp インスタンスを記述してください。

<details>
<summary>回答を表示</summary>

最初に、RGD が Active であり、生成された CRD が Established であることを確認します。このインスタンスでは ingress を無効にします。

```yaml
apiVersion: platform.example.com/v1alpha1
kind: NginxApp
metadata:
  name: reviewed-web
  namespace: example
spec:
  replicas: 2
  image: nginxinc/nginx-unprivileged:1.30.4-alpine
  ingress:
    enabled: false
    className: internal
    host: app.example.com
    tlsSecret: app-tls
```

</details>

## 17. Deployment を作成する resource entry を記述してください。

<details>
<summary>回答を表示</summary>

これはガイドと同じ template です。readyWhen は Deployment 自体のみを参照します。実際の環境で image、namespace、policy を確認してください。

```yaml
resources:
- id: deployment
  readyWhen:
  - ${deployment.status.availableReplicas >= deployment.spec.replicas}
  - ${deployment.status.observedGeneration >= deployment.metadata.generation}
  template:
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: ${schema.metadata.name}
      namespace: ${schema.metadata.namespace}
      labels:
        app.kubernetes.io/name: ${schema.metadata.name}
    spec:
      replicas: ${schema.spec.replicas}
      selector:
        matchLabels:
          app.kubernetes.io/name: ${schema.metadata.name}
      template:
        metadata:
          labels:
            app.kubernetes.io/name: ${schema.metadata.name}
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 101
            runAsGroup: 101
            fsGroup: 101
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: web
            image: ${schema.spec.image}
            ports:
            - name: http
              containerPort: 8080
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            readinessProbe:
              httpGet:
                path: /
                port: http
            volumeMounts:
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: tmp
            emptyDir:
              sizeLimit: 64Mi
```

</details>

## 18. status で availableReplicas を公開してください。

<details>
<summary>回答を表示</summary>

これは RGD spec.schema 配下の status section です。値がない場合、解決は待機する可能性があります。これは包括的なアプリケーション health ではありません。

```yaml
status:
  availableReplicas: ${deployment.status.availableReplicas}
  serviceIP: ${service.spec.clusterIP}
```

</details>

## 19. dev/staging/prod 戦略を設計してください。

<details>
<summary>回答を表示</summary>

検証済みの API contract と image digest を共有しつつ、namespace、replica、ingress、policy をインスタンスごとに分離します。各 cluster で kro/RGD/permission を準備し、synchronization には fleet tooling を使用します。未使用の autoscaling field で HPA は作成されません。

</details>

## 20. stateful application に対する Helm と kro の限界は何ですか？

<details>
<summary>回答を表示</summary>

database backup、restore、failover、schema migration を自動的に実装するものはどちらにもありません。専用 operator/managed-service の動作と data retention を検証してください。Git spec を restore しても database rollback にはなりません。失敗した最新の GraphRevision が自動的に fallback されることはありません。

</details>
