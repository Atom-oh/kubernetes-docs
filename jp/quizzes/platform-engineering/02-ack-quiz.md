# AWS Controllers for Kubernetes (ACK) Quiz

このクイズでは、AWS Controllers for Kubernetes (ACK) の概念、アーキテクチャ、インストール、セキュリティ、運用に関する理解を確認します。

## Multiple Choice Questions

1. ACK (AWS Controllers for Kubernetes) の主な目的は何ですか？
   - A) AWS console のみを通じて AWS リソースを管理する
   - B) Kubernetes API を通じて AWS リソースを宣言的に管理する
   - C) Kubernetes クラスターを AWS 上でのみ実行する
   - D) AWS コストを自動的に削減する

<details>

<summary>答えを表示</summary>

**答え: B) Kubernetes API を通じて AWS リソースを宣言的に管理する**

**解説:**
ACK は、Kubernetes ユーザーが使い慣れた Kubernetes API やツール (kubectl、Helm など) を直接使用して、AWS サービスとリソースを管理できるようにするプロジェクトです。これにより、GitOps ワークフローとの統合や、宣言的な設定を通じた AWS infrastructure as code の管理が可能になります。
</details>

2. ACK アーキテクチャでは、各 AWS サービスごとに個別にインストールされるコンポーネントはどれですか？
   - A) Kubernetes API Server
   - B) Service controller
   - C) etcd database
   - D) kubelet

<details>

<summary>答えを表示</summary>

**答え: B) Service controller**

**解説:**
ACK は、各 AWS サービス (S3、RDS、DynamoDB など) に対して個別の service controller を提供します。たとえば、S3 bucket を管理するには S3 controller をインストールし、RDS database を管理するには RDS controller をインストールします。このモジュール式のアプローチにより、必要なサービスの controller だけをインストールできます。
</details>

3. ACK controller が AWS リソースを管理するための IAM 権限を設定する推奨方法は何ですか？
   - A) EC2 instance profile のみを使用する
   - B) AWS access key を ConfigMap に保存する
   - C) IRSA (IAM Roles for Service Accounts) を使用する
   - D) すべての AWS 権限を持つ root account を使用する

<details>

<summary>答えを表示</summary>

**答え: C) IRSA (IAM Roles for Service Accounts) を使用する**

**解説:**
IRSA (IAM Roles for Service Accounts) は、IAM role を Kubernetes service account に関連付けることで、ACK controller に AWS リソース管理権限を付与するための推奨方法です。このアプローチは最小権限の原則に従い、安全な認証情報管理を可能にし、各 controller に必要な権限のみを付与できます。
</details>

4. Kubernetes リソースを削除するときに AWS リソースを保持するため、ACK で使用すべき annotation はどれですか？
   - A) services.k8s.aws/keep-resource: "true"
   - B) services.k8s.aws/deletion-policy: "orphan"
   - C) services.k8s.aws/preserve: "true"
   - D) services.k8s.aws/no-delete: "true"

<details>

<summary>答えを表示</summary>

**答え: B) services.k8s.aws/deletion-policy: "orphan"**

**解説:**
デフォルトでは、Kubernetes リソースが削除されると、ACK は対応する AWS リソースも削除します。ただし、`services.k8s.aws/deletion-policy: "orphan"` annotation を設定すると、Kubernetes リソースが削除されても AWS リソースは保持されます。これは、本番環境で重要なリソースが誤って削除されるのを防ぐのに役立ちます。
</details>

5. ACK を使用して既存の AWS リソースを Kubernetes にインポートするにはどうしますか？
   - A) kubectl import コマンドを使用する
   - B) AWS console から export 機能を使用する
   - C) リソース manifest に services.k8s.aws/resource-imported: "true" annotation を追加する
   - D) ACK CLI import コマンドを使用する

<details>

<summary>答えを表示</summary>

**答え: C) リソース manifest に services.k8s.aws/resource-imported: "true" annotation を追加する**

**解説:**
既存の AWS リソースを ACK にインポートするには、リソース manifest を作成し、`services.k8s.aws/resource-imported: "true"` annotation を追加します。これにより、ACK controller は新しいリソースを作成する代わりに、既存の AWS リソースへ接続します。これにより、既存の infrastructure を GitOps ワークフローへ段階的に移行できます。
</details>

6. ACK service controller のどの成熟度レベルが本番利用に適していますか？
   - A) Alpha
   - B) Beta
   - C) GA (Generally Available)
   - D) Preview

<details>

<summary>答えを表示</summary>

**答え: C) GA (Generally Available)**

**解説:**
ACK service controller は、Alpha、Beta、GA の 3 つの成熟度レベルを経ます。Alpha は API 変更が発生する可能性のある初期開発段階で、Beta は機能が完了しているものの API 変更の可能性がまだあることを意味します。GA (Generally Available) は本番利用の準備ができた段階であり、安定した API と完全な機能を提供します。
</details>

7. ACK リソースが正常に同期されたことを示す Condition type はどれですか？
   - A) ACK.Ready
   - B) ACK.ResourceSynced
   - C) ACK.Healthy
   - D) ACK.Available

<details>

<summary>答えを表示</summary>

**答え: B) ACK.ResourceSynced**

**解説:**
ACK リソースの status は `status.conditions` フィールドで確認できます。`ACK.ResourceSynced` Condition が True の場合、Kubernetes リソースの望ましい状態 (spec) が、実際の AWS リソース状態と正常に同期されたことを意味します。これにより、リソースが正しく作成または更新されたかを確認できます。
</details>

8. ACK で複数の team や環境の権限を分離するための推奨方法は何ですか？
   - A) すべての環境を単一の controller で管理する
   - B) 個別の namespace と IAM role を使用して分離する
   - C) AWS Organizations のみを使用する
   - D) VPC isolation のみを使用する

<details>

<summary>答えを表示</summary>

**答え: B) 個別の namespace と IAM role を使用して分離する**

**解説:**
ACK で複数の team や環境 (development、staging、production) の権限を分離するには、それぞれに個別の Kubernetes namespace と IAM role を使用することが推奨されます。各 namespace に個別の controller をインストールし、その環境に適した IAM policy を持つ role を関連付けます。さらに、Kubernetes RBAC を使用して、ACK リソースへのユーザーアクセスを制御できます。
</details>

## Short Answer Questions

9. ACK controller が、望ましい状態と実際の状態の差分を検出して解消しながら、AWS API を呼び出してリソースの作成、更新、削除を行うパターンは何と呼ばれますか？

<details>

<summary>答えを表示</summary>

**答え: Reconciliation Loop または Reconciliation Pattern**

**解説:**
Reconciliation loop は Kubernetes controller の中核となるパターンであり、ACK もこのパターンに基づいています。ACK controller は、Kubernetes リソースの望ましい状態 (spec) と AWS リソースの実際の状態を継続的に比較します。差分が検出されると、controller は AWS API を呼び出して実際の状態を望ましい状態に一致させます。このプロセスは自動的に繰り返され、drift を検出して修正します。
</details>

10. ACK は、Kubernetes API を通じて AWS リソースを定義するために、どの Kubernetes extension mechanism を使用しますか？

<details>

<summary>答えを表示</summary>

**答え: CRD (Custom Resource Definition)**

**解説:**
ACK は、Kubernetes API を通じて AWS リソースを定義するために CRD (Custom Resource Definition) を使用します。たとえば、S3 controller をインストールすると、`Bucket` や `BucketPolicy` のような CRD が作成され、Kubernetes リソースのように S3 bucket を管理できます。各 service controller は、対応する AWS サービスのリソース用 CRD を提供します。
</details>

11. ACK リソースの status を確認するとき、AWS リソースの ARN (Amazon Resource Name) はどのフィールドで確認できますか？

<details>

<summary>答えを表示</summary>

**答え: status.ackResourceMetadata.arn**

**解説:**
ACK リソースが正常に作成されると、対応する AWS リソースの ARN が `status.ackResourceMetadata.arn` フィールドに保存されます。`kubectl describe` コマンドでリソース status を確認すると、この情報を確認できます。また、リソースを所有する AWS account ID は `status.ackResourceMetadata.ownerAccountID` フィールドで確認できます。
</details>

12. ACK で、複数のクラスターから同じ AWS リソースを参照したり、異なる AWS account のリソースを管理したりできる機能は何と呼ばれますか？

<details>

<summary>答えを表示</summary>

**答え: Cross-Account Resource Management または Multi-Cluster Support**

**解説:**
ACK は、複数の Kubernetes クラスターから同じ AWS リソースを参照したり、異なる AWS account のリソースを管理したりする機能を提供します。これを行うには、ACK controller が他の account のリソースにアクセスできるように、IAM role chaining または cross-account IAM policy を設定します。この機能により、multi-cluster または multi-account 環境で一元的なリソース管理が可能になります。
</details>

## Hands-on Questions

13. ACK を使用して S3 bucket を作成する Kubernetes manifest を書いてください。bucket 名は "my-ack-demo-bucket-2025" で、Environment: Development tag を追加します。

<details>

<summary>答えを表示</summary>

**答え:**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-ack-demo-bucket
  namespace: default
spec:
  name: my-ack-demo-bucket-2025
  tagging:
    tagSet:
      - key: Environment
        value: Development
  createBucketConfiguration:
    locationConstraint: us-west-2
```

**解説:**
これは、ACK S3 controller を使用して S3 bucket を作成するための manifest です。`metadata.name` は Kubernetes リソース名で、`spec.name` は実際の AWS S3 bucket 名です。bucket 名はグローバルに一意である必要があるため、実際の使用時には一意の名前を使用してください。AWS resource tag は `tagging.tagSet` を通じて設定でき、`createBucketConfiguration.locationConstraint` は bucket が作成される region を指定します。
</details>

14. Helm を使用して ACK S3 controller をインストールし、IRSA を設定するコマンドを書いてください。cluster 名 "my-eks-cluster"、namespace "ack-system" を使用します。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# 1. Add Helm chart repository
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts
helm repo update

# 2. Create IAM service account for IRSA
eksctl create iamserviceaccount \
  --cluster=my-eks-cluster \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve \
  --override-existing-serviceaccounts

# 3. Install S3 controller
helm install ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --namespace ack-system \
  --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set aws.region=us-west-2
```

**解説:**
まず、ACK Helm chart repository を追加します。次に、eksctl を使用して IRSA 設定用の IAM service account を作成します。S3 管理に必要な IAM policy がこの service account にアタッチされます。最後に、Helm を使用して S3 controller をインストールし、すでに作成済みの service account を使用するように設定します。本番環境では、AmazonS3FullAccess の代わりに最小権限の custom policy を使用することをお勧めします。
</details>

15. ACK で作成されたリソースのトラブルシューティングのために、controller logs を確認し、リソース status を調査するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# 1. Check ACK controller logs
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller

# 2. Check specific resource status and events
kubectl describe bucket my-ack-demo-bucket

# 3. Check detailed resource status (JSON format)
kubectl get bucket my-ack-demo-bucket -o json | jq '.status'

# 4. Check resource-related events
kubectl get events --field-selector involvedObject.name=my-ack-demo-bucket

# 5. Check CRD installation status
kubectl get crd | grep services.k8s.aws

# 6. Check controller deployment status
kubectl get deployment -n ack-system
```

**解説:**
ACK リソース作成の問題をトラブルシューティングする際は、複数の観点を確認します。まず、controller logs を確認して AWS API call errors や permission issues を特定します。`kubectl describe` を使用してリソース status と Conditions を確認し、events を通じて最近の変更を追跡します。また、CRD が正しくインストールされていること、controller pods が正常に実行されていることも確認します。よくある問題には、IAM 権限不足、region 設定の誤り、リソース名の競合があります。
</details>

---

**採点:**
- 13-15 問正解: 優秀 (ACK expert level)
- 10-12 問正解: 良好 (実践的に適用できる)
- 7-9 問正解: 平均 (追加学習を推奨)
- 0-6 問正解: 不十分 (基本概念の復習が必要)

[学習資料に戻る](../../platform-engineering/02-ack.md)
