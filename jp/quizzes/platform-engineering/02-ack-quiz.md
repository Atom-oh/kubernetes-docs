# AWS Controllers for Kubernetes (ACK) クイズ

[ACK](../../platform-engineering/02-ack.md)

これらの問題は、レビュー済みの controller の動作に基づき、元の 15 個のトピックを維持しています。

## 1. ACK の主な目的は何ですか？

<details>
<summary>回答を表示</summary>

Kubernetes API と custom resource を通じて AWS resource を宣言的に管理することです。自動的なコスト削減や即時の準備完了を保証するものではありません。

</details>

## 2. 各 service にはどの component がインストールされますか？

<details>
<summary>回答を表示</summary>

CRD を含む service controller です。必要な service を選択し、バージョン管理された CRD でサポートされる resource と field を確認します。

</details>

## 3. controller はどのように AWS credential を受け取るべきですか？

<details>
<summary>回答を表示</summary>

IRSA またはサポートされる EKS Pod Identity などの workload identity を設定します。OIDC trust/association、ServiceAccount、SDK/agent の互換性、および最小限の IAM permission を検証してください。access key を ConfigMap に保存したり、root credential を使用したりしないでください。

</details>

## 4. CR の削除後も AWS resource を保持する値はどれですか？

<details>
<summary>回答を表示</summary>

`services.k8s.aws/deletion-policy: retain` です。現在の runtime は orphan を受け付けません。優先順位は、CR、namespace の service 固有 annotation、controller の default の順です。保持された AWS resource でも、引き続き ownership と運用が必要です。

</details>

## 5. 既存の resource はどのように adopt しますか？

<details>
<summary>回答を表示</summary>

ResourceAdoption の `adoption-policy: adopt` と service 固有の adoption-fields を使用し、gate、identifier、region、account を検証します。resource-imported:true はこの設定ではありません。adopt-or-create は存在しない resource を作成できます。その後の reconciliation では resource が変更される可能性があるため、adoption と read-only の動作を区別してください。

</details>

## 6. GA status は何を示しますか？

<details>
<summary>回答を表示</summary>

これは controller の公式な成熟段階を示すものであり、すべての AWS API や運用要件のサポートを示すものではありません。成熟度と CRD の v1alpha1 string を区別し、field、release、運用上の適合性を検証してください。

</details>

## 7. synchronization を示す condition はどれですか？また、その制限は何ですか？

<details>
<summary>回答を表示</summary>

ACK.ResourceSynced=True は controller の synchronization を示します。app の readiness、database connectivity、message delivery の証明ではありません。ほかの condition と AWS service state を確認してください。

</details>

## 8. team ごとに namespace を分ければ、isolation は完了しますか？

<details>
<summary>回答を表示</summary>

いいえ。default の installScope=cluster は namespace をまたいで CR を監視します。watchNamespace/installScope、ServiceAccount/IAM/RBAC、および cross-namespace/CARM の動作をまとめて制限してください。namespace mode でも、namespace cache のために cluster read permission を持つ場合があります。

</details>

## 9. 望ましい AWS state と観測された AWS state を一致させる pattern は何ですか？

<details>
<summary>回答を表示</summary>

reconciliation loop は、サポートされる field と controller logic を繰り返し処理します。一時的な error と AWS quota はこれに影響します。考えられるすべての drift を即座に修復するわけではありません。

</details>

## 10. resource input を定義する Kubernetes extension はどれですか？

<details>
<summary>回答を表示</summary>

CRD です。S3 の例では Bucket.spec.policy を使用します。レビュー済みの version には、独立した BucketPolicy または IAM RolePolicyAttachment CRD はありません。実際の kind と schema を検証してください。

</details>

## 11. ARN はどこで確認できますか？

<details>
<summary>回答を表示</summary>

resource に提供されている場合は、NLB と TargetGroup を含め、status.ackResourceMetadata.arn を使用します。追加の status field は resource ごとに異なります。

</details>

## 12. CARM は cross-cluster reference とどのように異なりますか？

<details>
<summary>回答を表示</summary>

CARM は、target-role assumption を通じて別の AWS account を管理するよう controller を設定するもので、trust、AssumeRole permission、mapping、controller setting が必要です。複数の cluster による競合する mutation を安全にするものではありません。mutation の ownership と read-only reference を分離してください。

</details>

## 13. Development tag を付けた S3 Bucket の例には何を含めるべきですか？

<details>
<summary>回答を表示</summary>

グローバルに一意な名前、実際の region、tagging.tagSet、4 つすべての Block Public Access 設定、および encryption を使用します。bucket policy を適用する前に、principal/IAM Role が存在している必要があります。例示用の名前と account ID は置き換えてください。

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: replace-with-globally-unique-bucket-name
  createBucketConfiguration:
    locationConstraint: us-west-2
  publicAccessBlock:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  encryption:
    rules:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  tagging:
    tagSet:
    - key: Environment
      value: Development
  policy: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"\
    Effect\": \"Allow\",\n      \"Principal\": {\n        \"AWS\": \"arn:aws:iam::123456789012:role/MyApplicationRole\"\
    \n      },\n      \"Action\": \"s3:GetObject\",\n      \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

</details>

## 14. ACK S3 chart はどのように確認し、インストール前には何が必要ですか？

<details>
<summary>回答を表示</summary>

この command は、固定された OCI chart を offline で render します。実際の install/upgrade の前に、infra、その ServiceAccount、IRSA/Pod Identity、および IAM permission を準備してください。rendering は AWS deployment の検証ではありません。

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.12.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

</details>

## 15. どの status と log を確認すべきですか？

<details>
<summary>回答を表示</summary>

namespace と fully qualified kind を指定し、condition/event、controller image/log、実際の account/region/permission、および reference を確認します。chart label は app.kubernetes.io/instance=ack-s3 です。finalizer の削除は通常の修正方法ではありません。

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

</details>
