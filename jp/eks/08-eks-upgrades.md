# Amazon EKS のアップグレード

> **最終更新日**: 2026年10月12日

Amazon EKS クラスターを最新の状態に保つことは、セキュリティと安定性を確保し、新機能を活用するうえで重要です。このドキュメントでは、EKS クラスターを安全にアップグレードするための戦略、ベストプラクティス、手順を説明します。

ここに記載するのはオーナーがレビューした手順であり、この監査でアップグレードを実行したわけではありません。明示したアカウント、リージョン、Kubernetes コンテキストを使用し、承認済みのアップグレード元とアップグレード先のバージョンおよび更新 ID を記録して、アプリケーションの動作を検証してください。同じリソースに対して、複数の代替例を続けてすべて実行しないでください。ローカルでの解析やモックでは、本番環境での準備が整っていることは確認できません。

## 目次

1. [EKS のアップグレード概要](#eks-upgrade-overview)
2. [アップグレードの計画と準備](#upgrade-planning-and-preparation)
3. [EKS コントロールプレーンのアップグレード](#eks-control-plane-upgrade)
4. [ノードグループのアップグレード](#node-group-upgrade)
5. [アドオンのアップグレード](#add-on-upgrade)
6. [アップグレードの検証とトラブルシューティング](#upgrade-validation-and-troubleshooting)
7. [アップグレードの自動化](#upgrade-automation)
8. [アップグレードのベストプラクティス](#upgrade-best-practices)

## EKS のアップグレード概要 {#eks-upgrade-overview}

![EKS のアップグレードを構成する4つの柱を示すツリー図。バージョン管理ポリシー、アップグレード対象のコンポーネント（コントロールプレーン、ノードグループ、アドオン、セルフマネージドコンポーネント）、マイナーバージョンを1つずつ進めるアップグレードパスとサポートされないバージョンのスキップ、5つの手順からなるアップグレード順序を示す。](../.gitbook/assets/en-eks-08-eks-upgrades-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-0.html)

### EKS のバージョン管理

EKS は Kubernetes のバージョン番号を使用し、独自のリリースおよびサポートカレンダーを設けています。各マイナーバージョンには、**標準サポート期間が14か月**あり、その後、追加料金が発生する**延長サポート期間が12か月**あります。AWS は標準サポート終了の少なくとも60日前に告知します。[現在の EKS カタログ／カレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)を確認してください。上流の Kubernetes リリースが、EKS ですぐに利用可能になるとは限りません。「最低4バージョン」という固定の想定や、14か月がサポートライフサイクルのすべてだとする扱いは避けてください。

### 最近の EKS アップグレードに関する発表（2026年）

- **Kubernetes 1.37 が利用可能に（2026年10月1日）**: EKS 1.37 がサポート対象のアップグレード先になりました。Auto Mode では、統合ポリシーを指定せずに新規作成したカスタム NodePool の統合ポリシーは、デフォルトで `Balanced` になります。組み込みの `general-purpose` プールと `system` プールも `Balanced` を使用します。SELinux ボリュームマウントは安定版となり、対応する CSI および Pod の構成ではデフォルトで有効です。アップグレード前に、想定する NodePool の動作と、異なるラベルを使用するワークロードがボリュームを共有する場合の SELinux／CSI 要件を確認してください。[EKS 標準サポートのリリースノート](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)と[サポートカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)の Kubernetes 1.37 の項を参照してください。
- **Kubernetes バージョンのロールバックをサポート（2026年7月1日）**: アップグレードで問題が発生した場合、7日以内であればコントロールプレーンを直前のマイナーバージョンに戻せるようになりました。EKS は事前に自動のロールバック準備チェックを実行し、API 互換性、バージョンスキュー、アドオン互換性、クラスターの健全性を確認します。ユーザーが開始するロールバックでは、コントロールプレーンを戻す前に、Auto Mode が対象となるワーカーノードを置き換えます。これはアプリケーションの障害に自動的に反応する機能ではありません。対象要件と中断制御は引き続き適用されます。EKS を提供するリージョンでは追加料金はありませんが、ノード／ストレージ料金や該当するバージョンサポート料金は引き続き適用されます。詳細は以下の[ロールバック手順](#rollback-procedure)を参照してください。（出典: [Amazon EKS が Kubernetes バージョンのロールバックを発表](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-version-rollback)）
- **99.99% SLA と 8XL コントロールプレーンティア（2026年3月20日）**: Provisioned Control Plane クラスターの SLA が99.95%から99.99%に引き上げられ、1分単位で測定されます。新しい8XLスケーリングティアは、従来の4XLティアのAPIリクエスト処理能力を2倍にし、非常に大規模なクラスターや AI／ML／HPC ワークロードを対象としています。（出典: [Amazon EKS が SLA と 8XL スケーリングティアを発表](https://aws.amazon.com/about-aws/whats-new/2026/03/amazon-eks-announces-sla-8xl-scaling-tier/)）

### アップグレード対象のコンポーネント

EKS クラスターのアップグレードには、次のコンポーネントが含まれます。

1. **EKS コントロールプレーン**: Kubernetes API server、etcd、controller manager など
2. **ノードグループ**: ワーカーノードとノード AMI
3. **アドオン**: AWS マネージドアドオン（CoreDNS、kube-proxy、VPC CNI など）
4. **セルフマネージドコンポーネント**: Helm Chart、カスタムリソースなど

### アップグレードパス

EKS クラスターは、マイナーバージョンを1つずつアップグレードする必要があります。

- 過去の例として、1.24 → 1.25 → 1.26 → 1.27 は、マイナーバージョンを1つずつ進めるパターンを示しています。これらは現在のデプロイ先ではありません。
- 1.24 → 1.26 の直接アップグレードは、マイナーバージョンを飛ばすサポート対象外の例です。
- 実際に変更する場合は、対象リージョンおよびサポートポリシーで EKS が提供している次のマイナーバージョンを選んでください。

### アップグレードの順序

1. インベントリの作成、テスト、バックアップ、進行中の更新の解決を行い、保守的な準備手順としてノードを**現在の**コントロールプレーンのマイナーバージョンにそろえます。
2. 現在とアップグレード先の Kubernetes バージョンの両方に対応する、必要なアドオン／コントローラーの橋渡しバージョンを適用し、コンポーネントごとの前提条件を確認します。
3. コントロールプレーンを、サポート対象のマイナーバージョン1つ分だけアップグレードし、その更新 ID が成功するまで待ちます。
4. 検証済みの依存関係順序に従って、ノード、クライアント／コントローラー、残りのアドオンをアップグレードし、各手順を確認します。Auto Mode は組み込み機能を管理し、コントロールプレーンのアップグレード後にノード更新を開始します。
5. 実際のノードバージョン、ワークロードの準備状況、トラフィック、ストレージ、SLO を検証します。

kubelet 1.25 以降では、上流の仕様により kubelet のバージョンは API server より最大3マイナーバージョン古くてもかまいませんが、新しくなることはできません。API server のバージョンが混在していると、許容範囲は狭まります。EKS のドキュメントには、アップグレード前にノードをそろえる指針と、サポートされるスキューの許容範囲の両方が記載されています。この手順書では準備方針としてバージョンをそろえますが、サポート対象となるスキューがすべて EKS API によって一律に拒否されるとは述べていません。アドオンは、必ずコントロールプレーンの「前」または「後」にすべてアップグレードするものではありません。ロールバックでは別の、ノードを先に処理する順序が使われます。詳細は以下を参照してください。

## アップグレードの計画と準備 {#upgrade-planning-and-preparation}

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Tree diagram showing upgrade planning and preparation split into an upgrade assessment branch (version compatibility check, resource requirements, upgrade schedule planning) and a pre-upgrade preparation branch (check cluster state, create backup, test upgrade, upgrade documentation).](../.gitbook/assets/en-eks-08-eks-upgrades-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-1.html)
-->

### アップグレードの評価

アップグレードを始める前に、次の項目を評価してください。

#### バージョン互換性の確認

アップグレード先の Kubernetes バージョンとの互換性を確認します。

- **API の非推奨化**: 非推奨 API を使用するワークロードを特定する
- **機能の変更**: 新バージョンでの機能変更を確認する
- **アドオンの互換性**: アドオンがアップグレード先のバージョンに対応していることを確認する

イメージ一覧や `kubectl get … .apiVersion` は、クライアント／API の非推奨化を監査する方法ではありません。API server が返すのは、ネゴシエートされた、または現在の表現です。ベータ API が必ずしも非推奨とは限りません。ソース／Helm マニフェスト、クライアント、CRD、webhook、EKS アップグレードインサイトをアップグレード先のリリースに照らして確認してください。API server のメトリクスを一度取得した結果は、観測できた証拠にすぎません。使用が検出されなかったことやエラーが発生したことは、非推奨 API が使用されていない証拠にはなりません。

次の読み取り専用コレクターを `eks-upgrade-preflight.py` として保存してください。`CLUSTER_NAME`、`AWS_REGION`、`EXPECTED_ACCOUNT_ID`、`KUBE_CONTEXT`、`TARGET_VERSION` を設定し、JSON をローカルのアクセス制限された場所に保存します。正常終了は収集が成功したことを意味するだけであり、アップグレードが承認されたことや、すべてのワークロードに互換性があることを意味しません。

```python
import json
import os
import re
import subprocess


def run_json(args):
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


def run_text(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def inspect_upgrade(cluster_name, region, expected_account, context, target, query=run_json, text=run_text):
    if not re.fullmatch(r"[0-9]{12}", expected_account):
        raise ValueError("Set the reviewed 12-digit AWS account ID")
    if not re.fullmatch(r"[0-9]+\.[0-9]+", target):
        raise ValueError("Target must be an EKS major.minor version")
    aws = [os.environ.get("AWS_CLI", "aws")]
    suffix = ["--region", region, "--output", "json", "--no-cli-pager"]
    identity = query(aws + ["sts", "get-caller-identity"] + suffix)
    if identity["Account"] != expected_account:
        raise RuntimeError("AWS account mismatch")
    cluster = query(aws + ["eks", "describe-cluster", "--name", cluster_name] + suffix)["cluster"]
    if cluster["status"] != "ACTIVE":
        raise RuntimeError("Cluster must be ACTIVE; inspect any in-progress updates")
    if cluster["arn"].split(":")[4] != expected_account:
        raise RuntimeError("Cluster/account mismatch")
    current = cluster["version"]
    current_parts = tuple(map(int, current.split(".")))
    target_parts = tuple(map(int, target.split(".")))
    if target_parts != (current_parts[0], current_parts[1] + 1):
        raise ValueError("This upgrade example requires exactly the next minor version")
    server = text(["kubectl", "--context", context, "config", "view", "--minify",
                   "--output", "jsonpath={.clusters[0].cluster.server}"])
    if server != cluster["endpoint"]:
        raise RuntimeError("Kubernetes context does not match the EKS API endpoint")
    catalog = query(aws + ["eks", "describe-cluster-versions", "--cluster-versions", target,
                         "--include-all", "--no-default-only"] + suffix)["clusterVersions"]
    if not any(item["clusterVersion"] == target and item.get("versionStatus") in
               ["STANDARD_SUPPORT", "EXTENDED_SUPPORT"] for item in catalog):
        raise ValueError("Target is not offered as a supported EKS version in this Region")
    insights = query(aws + [
        "eks", "list-insights", "--cluster-name", cluster_name,
        "--filter", json.dumps({"categories": ["UPGRADE_READINESS"], "kubernetesVersions": [target]}),
    ] + suffix)["insights"]
    nodes = query(["kubectl", "--context", context, "get", "nodes", "--output", "json"])["items"]
    update_ids = query(aws + ["eks", "list-updates", "--name", cluster_name] + suffix)["updateIds"]
    addon_names = query(aws + ["eks", "list-addons", "--cluster-name", cluster_name] + suffix)["addons"]
    addons = []
    for name in addon_names:
        addon = query(aws + ["eks", "describe-addon", "--cluster-name", cluster_name,
                             "--addon-name", name] + suffix)["addon"]
        addons.append({"name": name, "version": addon["addonVersion"], "status": addon["status"]})
    return {
        "cluster": cluster_name, "region": region, "account": expected_account,
        "currentVersion": current, "targetVersion": target, "targetCatalog": catalog,
        "insights": insights,
        "clusterUpdateIds": update_ids,
        "nodes": [{"name": node["metadata"]["name"],
                   "kubeletVersion": node["status"]["nodeInfo"]["kubeletVersion"],
                   "ready": next((condition.get("status") for condition in node["status"].get("conditions", [])
                                  if condition.get("type") == "Ready"), None),
                   "computeType": node["metadata"].get("labels", {}).get("eks.amazonaws.com/compute-type"),
                   "nodegroup": node["metadata"].get("labels", {}).get("eks.amazonaws.com/nodegroup")}
                  for node in nodes],
        "managedAddons": addons,
        "decision": "Inventory collected only; active-update review, owner approval, node alignment, API/client scans, "
                    "backups/restore tests, add-on bridge versions, capacity, and workload tests remain required.",
    }


if __name__ == "__main__":
    report = inspect_upgrade(
        os.environ["CLUSTER_NAME"], os.environ["AWS_REGION"],
        os.environ["EXPECTED_ACCOUNT_ID"], os.environ["KUBE_CONTEXT"],
        os.environ["TARGET_VERSION"],
    )
    print(json.dumps(report, indent=2))
```

#### リソース要件の評価

アップグレードに必要なリソースを評価します。

- **クラスター容量**: アップグレード中に追加ノードを収容できる十分な容量
- **ダウンタイム許容度**: ワークロードがダウンタイムに耐えられるかどうか
- **ロールバック計画**: 問題が発生した場合のロールバック計画

#### アップグレードスケジュールの計画

アップグレードのスケジュールを計画します。

- **メンテナンスウィンドウ**: トラフィックが少ない時間帯にアップグレードをスケジュールする
- **段階的なアプローチ**: 非本番環境から始め、本番環境へ進める
- **ロールバック時間枠**: 問題が発生した場合にロールバックに必要な時間を見積もる

### アップグレード前の準備

#### クラスターの状態を確認する

アップグレード前にクラスターの状態を確認します。

```bash
# Check node status
kubectl --context "$KUBE_CONTEXT" get nodes

# Check pod status
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces

# Check component status
kubectl --context "$KUBE_CONTEXT" get --raw /readyz

# Check events
kubectl --context "$KUBE_CONTEXT" get events --all-namespaces
```

#### バックアップを作成する

アップグレード前に重要なデータをバックアップします。

EKS が管理するコントロールプレーンの etcd は AWS が所有します。自分の namespace 内で `etcd-pod`／`etcdctl snapshot` コマンドを実行しても、バックアップはできません。また、`kubectl get all` では重要なリソースやボリュームデータが含まれないため、完全なバックアップにはなりません。

[AWS Backup for EKS](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html) は、複合リカバリポイントを使用して、クラスターの状態と PVC が使用する EBS／EFS／S3 リソースを保護できます。その際、ドキュメントに記載された IAM、API／API_AND_CONFIG_MAP アクセスモード、ストレージ、復元の前提条件を満たす必要があります。別の方法として、ボリュームの対象範囲と認証情報を検証済みの、自分たちが所有する Velero／アプリケーションのバックアップ環境を使用できます。namespace／クラスター範囲の対象、データベースの整合性、保持期間、復元テストを確認してください。バックアップ要求から ID が返ってきても、完了や復元可能性が証明されたわけではありません。

#### アップグレードをテストする

本番以外の環境でアップグレードをテストします。

1. 本番環境に似たテストクラスターを作成する
2. テストクラスターをアップグレードする
3. ワークロードと機能をテストする
4. 問題を特定して解決する

#### アップグレード手順書を作成する

アップグレード手順を文書化します。

- アップグレード手順
- 担当者と連絡先
- ロールバック手順
- トラブルシューティングガイド

## EKS コントロールプレーンのアップグレード {#eks-control-plane-upgrade}

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagram of an EKS control plane upgrade split into four stages, preparation, execution, monitoring, and troubleshooting, each grouping its steps: version checks and planning, Console/CLI/eksctl, status, cluster state and CloudWatch monitoring, and common issues with troubleshooting steps.](../.gitbook/assets/en-eks-08-eks-upgrades-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-2.html)
-->

### コントロールプレーンのアップグレード準備

#### 現在のバージョンを確認する

EKS クラスターの現在のバージョンを確認します。

```bash
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --query "cluster.version"
```

#### 利用可能なバージョンを確認する

利用可能な Kubernetes バージョンを確認します。

```bash
aws eks describe-cluster-versions --region "$AWS_REGION" \
  --no-default-only --output json --no-cli-pager
```

#### アップグレード計画を作成する

通常のアップグレードを要求する前に、[現在の EKS ガイダンス](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)を確認してください。アップグレードインサイトの検出結果に対して `--force` を必須とする制約は、一時的に取り下げられています。これは、バージョンのロールバックにおける `ROLLBACK_READINESS` のブロック条件とは異なります。検出結果を解決するか、明示的に評価してください。過去30日間の非推奨 API の証拠は、問題を修正した後も残る場合があります。クラスターのサブネットが存在し、必要な予備 IP アドレス（EKS は最大5個を必要とする場合があります）があり、コントロールプレーンとの通信が許可されていることを確認してください。コントロールプレーンのアップグレードが始まると、一時停止や停止はできません。クライアント側で再接続に対応する必要があります。

コントロールプレーンのアップグレード計画を作成します。

- アップグレード時刻: トラフィックが少ない時間帯を選ぶ
- 監視の設定: アップグレード中にクラスターの状態を監視する
- ロールバック計画: 問題が発生した場合のロールバック手順を用意する

### コントロールプレーンのアップグレード実行

#### AWS Management Console を使用してアップグレードする

1. AWS Management Console にログインします
2. Amazon EKS サービスに移動します
3. クラスター一覧からアップグレードするクラスターを選択します
4. 「Cluster configuration」タブを選択します
5. 「Update Kubernetes version」をクリックします
6. アップグレード先のバージョンを選択し、「Update」をクリックします

#### AWS CLI を使用してアップグレードする

記録した計画と前提条件が承認されてから実行してください。次のセクションのポーリングヘルパーを `eks-wait-update.py` として保存します。これはコントロールプレーンの更新のみを要求します。ノード／アドオンのアップグレードや、ワークロードの準備状況の確認は行いません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${AWS_REGION:?Set the reviewed Region}"
: "${TARGET_VERSION:?Set the next supported EKS minor version}"
umask 077
aws eks update-cluster-version \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --output json --no-cli-pager \
  > control-plane-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' control-plane-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

#### eksctl を使用してアップグレードする

```bash
eksctl upgrade cluster \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --version "$TARGET_VERSION" \
  --approve
```

### コントロールプレーンのアップグレード監視

#### アップグレードの状態を確認する

アップグレードの状態を確認します。

正確な更新 ID に対して `DescribeUpdate` を追跡してください。`cluster-active`／`nodegroup-active` は、この要求が成功したことを示すものではありません。また、AWS CLI 2.36.44 には `eks wait update-successful` waiter がありません。次のコードを `eks-wait-update.py` として保存してください。ノードグループ／アドオンの要求の場合は `NODEGROUP_NAME` または `ADDON_NAME` のいずれか一方だけを設定し、それ以外の場合はどちらも設定しません。API エラー、失敗／キャンセル、不明な状態、クライアントの待機期限に達した場合、このスクリプトは失敗します。クライアント側のタイムアウトでは AWS の操作はキャンセルされません。デフォルトのクライアント待機時間は2時間です。特に時間のかかる Auto Mode のロールバックでは、承認済みの操作に合わせて調整してください。

```python
import json
import os
import subprocess
import time
from pathlib import Path


def wait_update(lookup, timeout_seconds, interval_seconds=15, clock=time.monotonic, sleep=time.sleep):
    if timeout_seconds <= 0 or interval_seconds < 0:
        raise ValueError("Use a positive timeout and nonnegative polling interval")
    deadline = clock() + timeout_seconds
    while True:
        update = lookup()["update"]
        status = update["status"]
        print(json.dumps({"id": update["id"], "status": status, "errors": update.get("errors", [])}), flush=True)
        if status == "Successful":
            return update
        if status in ["Failed", "Cancelled"]:
            raise RuntimeError(f"EKS update ended with {status}; inspect its error details")
        if status not in ["InProgress", "Cancelling"]:
            raise RuntimeError(f"Unexpected update status: {status}")
        if clock() >= deadline:
            raise TimeoutError("Client wait expired; the AWS operation may still be running. Preserve its update ID.")
        sleep(interval_seconds)


if __name__ == "__main__":
    cluster = os.environ["CLUSTER_NAME"]
    region = os.environ["AWS_REGION"]
    update_id = os.environ["UPDATE_ID"]
    nodegroup = os.environ.get("NODEGROUP_NAME")
    addon = os.environ.get("ADDON_NAME")
    if nodegroup and addon:
        raise ValueError("Set only NODEGROUP_NAME or ADDON_NAME for a scoped update")
    command = [
        os.environ.get("AWS_CLI", "aws"), "eks", "describe-update",
        "--name", cluster, "--region", region, "--update-id", update_id,
        "--output", "json", "--no-cli-pager",
    ]
    if nodegroup:
        command += ["--nodegroup-name", nodegroup]
    if addon:
        command += ["--addon-name", addon]
    status_file = Path(os.environ.get("UPDATE_STATUS_FILE", "eks-update-status.json"))

    def lookup():
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        response = json.loads(completed.stdout)
        status_file.write_text(json.dumps(response, indent=2) + "\n")
        return response

    wait_update(lookup, int(os.environ.get("WAIT_TIMEOUT_SECONDS", "7200")))
```

#### クラスターの状態を監視する

アップグレード中にクラスターの状態を監視します。

```bash
# Check node status
kubectl --context "$KUBE_CONTEXT" get nodes

# Check pod status
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces

# Check events
kubectl --context "$KUBE_CONTEXT" get events --all-namespaces --sort-by='.lastTimestamp'
```

#### CloudWatch メトリクスを監視する

使用している EKS のバージョン／ティアで実際に公開されるコントロールプレーンメトリクスと、設定済みのテレメトリを監視します。対象は、API リクエストレート／レイテンシ／エラー、API の準備状況とクライアントの再接続、スケジューリング、ノード／ワークロードの健全性、アプリケーションの SLO です。etcd／controller manager のエンドポイントや、すべてのコンポーネントメトリクスが公開されていると想定しないでください。`/readyz` が確認するのは API の準備状況であり、すべてのアプリケーション状態や過去の可用性条件ではありません。

### コントロールプレーンのアップグレードのトラブルシューティング

#### よくある問題

コントロールプレーンのアップグレード中に、次のような問題が発生することがあります。

- **アップグレードの失敗**: アップグレード処理が失敗または中断される
- **API server の可用性**: アップグレード中に API server の可用性に問題が発生する
- **互換性の問題**: ワークロードと新バージョンの間で互換性の問題が発生する

#### トラブルシューティングの手順

1. アップグレードの状態を確認する
2. CloudTrail ログを確認する
3. EKS コントロールプレーンログを確認する
4. AWS Support に問い合わせる

## ノードグループのアップグレード {#node-group-upgrade}

コントロールプレーンのアップグレード後、ノードグループもアップグレードする必要があります。ノードグループのアップグレードには複数の戦略があり、それぞれに利点と欠点があります。

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagram showing node group upgrades split into five branches, strategies, managed, self-managed, Fargate, and monitoring and validation, with the strategies branch broken down into managed, self-managed, and Fargate approaches.](../.gitbook/assets/en-eks-08-eks-upgrades-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-3.html)
-->

### ノードグループのアップグレード戦略

#### マネージドノードグループのアップグレード

マネージドノードグループは、ノードのアップグレードを自動化する AWS のノードグループ管理機能です。

- **置き換え戦略**: `maxUnavailable`／割合を指定すると、並行して置き換えられます。API の `updateStrategy=DEFAULT` は古い容量を削除する前に新しい容量を起動します。`MINIMAL` は先に古い容量を削除し、可用性と容量に異なるトレードオフをもたらします。
- **Drain**: 通常の更新では Pod の退避／PDB チェックが行われ、コントローラーは Pod をライブマイグレーションするのではなく再作成します。ノードグループの force オプションは PDB に関する Drain の失敗を回避できますが、クラスターのロールバックに使う force フラグとは別のものです。
- **バージョン／AMI の選択**: レビュー済みの Kubernetes および AMI リリースを選ぶか、カスタム AMI の場合は元の起動テンプレートの新しいバージョンを選びます。更新が失敗しても、フリートが自動的にロールバックされたとは限りません。ノード／AMI の混在状態と更新エラーを確認してください。

#### セルフマネージドノードグループのアップグレード

セルフマネージドノードグループの場合、ノードを手動でアップグレードする必要があります。

- **Blue/Green Deployment**: 新しいノードグループを作成し、ワークロードを移行する
- **ローリングアップグレード**: ノードを1台ずつ drain して終了し、新しいノードに置き換える
- **インプレースアップグレード**: 既存ノード上の kubelet とコンテナランタイムをアップグレードする

#### Fargate ノードのアップグレード

Fargate ノードのインフラストラクチャは AWS が所有しますが、ワークロードのオーナーは Pod の置き換えを調整する必要があります。新しく起動した Fargate Pod はコントロールプレーンに一致する kubelet バージョンを使用します。既存の Pod はコントロールプレーンの操作ではアップグレードされません。Fargate ではアップグレード作業が不要だとみなすのではなく、コントローラーのロールアウト、可用性、検証を計画してください。Auto Mode は異なり、独自の中断制御に従って、コントロールプレーンのアップグレード後に段階的なノード置き換えを開始します。

### マネージドノードグループのアップグレード

#### マネージドノードグループのバージョンを確認する

マネージドノードグループの現在のバージョンを確認します。

```bash
aws eks describe-nodegroup \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query "nodegroup.version"
```

#### AWS Management Console を使用してアップグレードする

1. AWS Management Console にログインします
2. Amazon EKS サービスに移動します
3. クラスター一覧からアップグレードするクラスターを選択します
4. 「Compute」タブを選択します
5. アップグレードするノードグループを選択します
6. 「Update node group」をクリックします
7. アップグレード先のバージョンを選択し、「Update」をクリックします

#### AWS CLI を使用してアップグレードする

EKS 最適化 AMI の場合は、レビュー済みのリリースとアップグレード先のバージョンを使用します。この操作には専用の更新 ID があります。ポーリング時はノードグループのスコープを指定してください。プラットフォーム／AMI ファミリーのサポート状況を確認してください。Kubernetes のバージョンを変更するだけでは、AL2 ノードグループは AL2023 に移行しません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${TARGET_VERSION:?Set the reviewed target, no newer than the control plane}"
: "${TARGET_AMI_RELEASE:?Set the reviewed EKS-optimized AMI release}"
umask 077
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" --output json > nodegroup-before.json
if jq -e '.nodegroup.amiType == "CUSTOM"' nodegroup-before.json >/dev/null; then
  echo "Use the custom launch-template path for this node group" >&2
  exit 1
fi
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --release-version "$TARGET_AMI_RELEASE" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

**カスタム AMI** の場合は、元の起動テンプレートをレビュー済みの新しいバージョンに更新してください。カスタム AMI の要求に Kubernetes の `version` や `releaseVersion` を渡さないでください。置き換え後のノードで、実際の kubelet／ランタイム／AMI を確認してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${LAUNCH_TEMPLATE_ID:?Set the same launch template originally used by the group}"
: "${LAUNCH_TEMPLATE_VERSION:?Set the reviewed version containing the updated custom AMI}"
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --launch-template "id=$LAUNCH_TEMPLATE_ID,version=$LAUNCH_TEMPLATE_VERSION" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

#### eksctl を使用してアップグレードする

```bash
eksctl upgrade nodegroup \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name "$NODEGROUP_NAME" \
  --kubernetes-version "$TARGET_VERSION"
```

#### マネージドノードグループのアップグレードを設定する

マネージドノードグループのアップグレード動作を設定できます。

- **最大の使用不可ノード数**: アップグレード中に使用できなくなるノードの最大数
- **PDB**: 対象となる自発的な退避を制限しますが、あらゆる障害やアプリケーションの結果を防ぐものではありません。ノードグループの強制更新では PDB の問題を無視できます。マネージドノードグループの desired／min／max スケーリング設定の変更は ASG のスケーリング操作であり、アップグレード時の Drain／PDB の保証を提供するものではありません。安全な移行方法として、サイズをゼロにする切り替えを使用しないでください。

```bash
aws eks update-nodegroup-config \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --update-config maxUnavailable=1
```

### セルフマネージドノードグループのアップグレード

#### Blue/Green Deployment

所有元の設定から、名前の異なる新しいノードグループを準備します。レビュー済みのサブネット／ゾーン、IAM、AMI アーキテクチャ／ブートストラップ、ラベル、taint、ストレージ、ネットワーク要件を維持してください。[クラスター作成ガイド](02-eks-cluster-creation.md)を参照してください。`eksctl create nodegroup` はデフォルトでマネージドグループを作成します。セルフマネージドの設定では、`--managed=false` または適切な `nodeGroups` 設定セクションを明示する必要があります。作成には `--version` を使用し、`eksctl upgrade nodegroup` には `--kubernetes-version` を使用します。

1. レビュー済みの設定から green の容量を作成し、ノード数、アップグレード先の kubelet／AMI、Ready 状態、CNI／DNS、アプリケーションのスケジューリングを確認します。ノードを一覧表示するだけでは検証になりません。
2. オーナーが管理する段階的な手順でワークロードを移行します。preferred affinity は green への配置を保証しません。実際の Pod のノード割り当てとストレージトポロジーを確認してください。
3. 特定した古いノードを一度に1台ずつ、有限のタイムアウトを設定して drain します。退避またはヘルスチェックに失敗した場合は中止してください。続行する前に、ワークロードと置き換え容量を再検証します。
4. 記録済みの移行、健全性、データ保持、復旧の受け入れ確認が完了してから、古いグループを廃止します。未確認のループや固定時間の待機後に、自動で削除しないでください。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

このデフォルトの drain は、別途判断が必要な未管理 Pod／ローカルデータがある場合、処理を拒否します。`--delete-emptydir-data` は emptyDir データの喪失を明示的に許可するため、むやみに追加しないでください。`kubectl drain --force` は未管理 Pod を許可するものであり、退避／PDB チェックを回避するのとは異なります。DaemonSet、static Pod、コントローラー、永続データは、それぞれのオーナーを通じて調整してください。

#### ローリングアップグレード

セルフマネージド ASG の場合、まず所有する起動設定／テンプレートを検証済み AMI に更新してください。更新しないと、置き換えノードが古いイメージで再び起動する可能性があります。前述の単一ノード drain のゲートを使用し、インスタンスを終了する前にノードの provider ID、EC2 インスタンス、ASG の所有関係を確認してください。Kubernetes ノードと EC2 インスタンスの対応付けに、最初に見つかった EC2 のプライベート DNS 名を使用しないでください。ASG のオーナーに drain 済みインスタンスを置き換えてもらい、正しく設定された**新しい** Ready ノードとワークロードの復旧を確認してから、次に進んでください。60秒待っても、置き換え準備が整ったことは証明されません。ASG の直接スケーリング／インスタンス更新には、対応する Kubernetes drain 連携が必要です。PDB が自動的に適用されるわけではありません。

#### インプレースアップグレード

インプレースアップグレードをサポートするセルフマネージドホストに限り、個別にテストした OS／イメージ固有の手順を使用してください。EKS 最適化マネージドフリートでは、不変で検証済みの AMI 置き換え方式を優先します。Auto Mode／Fargate のインフラストラクチャはサービスが所有します。汎用的な `yum update kubelet kubectl` では、レビュー済みの Kubernetes／ランタイムバージョンを選べず、EKS ノードのアップグレードにもなりません。SSM の要求は非同期です。呼び出し、必要なサービスの再起動、実際のバージョン、ノードの準備状況、ワークロードテストが成功するまで、ノードの cordon を解除しないでください。エラー後に自動で cordon を解除したりノードを終了したりせず、失敗の証拠を保持してください。

### ノードのアップグレード監視と検証

#### ノードバージョンを確認する

ノードの Kubernetes バージョンを確認します。

```bash
kubectl --context "$KUBE_CONTEXT" get nodes -o custom-columns=NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion
```

#### ノードの状態を確認する

ノードの状態を確認します。

```bash
kubectl --context "$KUBE_CONTEXT" get nodes
kubectl --context "$KUBE_CONTEXT" describe nodes
```

#### Pod のデプロイを確認する

Pod が通常どおりデプロイされていることを確認します。

```bash
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces -o wide
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,PHASE:.status.phase,READY:'.status.conditions[?(@.type=="Ready")].status'
```

## アドオンのアップグレード {#add-on-upgrade}

実際のコンポーネントのオーナーとアップグレードパスを一覧にしてください。EKS マネージドアドオンは、コントロールプレーンのアップグレードによって自動的にアップグレードされるわけではありません。オーナーが互換性のある更新を選んで開始します。必要な橋渡しリリースは、コントロールプレーンの変更より先に適用できます。Auto Mode の組み込み機能は AWS が別途管理します。すべてのクラスターで同じ DaemonSet／Deployment が使われているかのように、重複するノードネットワーク／ストレージ／DNS コンポーネントをインストールまたは更新しないでください。

![アドオンのアップグレードを、AWS マネージドアドオン（バージョン確認後、update-addon または eksctl でアップグレード）、セルフマネージドアドオン（Helm または kubectl）、主要アドオンのガイド（CoreDNS、kube-proxy、VPC CNI）、トラブルシューティング（よくある問題と手順）に分けて示す図。](../.gitbook/assets/en-eks-08-eks-upgrades-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-4.html)

### AWS マネージドアドオン

#### マネージドアドオンの一覧を確認する

クラスターにインストールされているマネージドアドオンを確認します。

```bash
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
```

#### マネージドアドオンのバージョンを確認する

マネージドアドオンの現在のバージョンを確認します。

```bash
aws eks describe-addon \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name vpc-cni \
  --query "addon.addonVersion"
```

#### 利用可能なアドオンバージョンを確認する

利用可能なアドオンバージョンを確認します。

配列の最初の要素が「最新」または正しいバージョンである保証はありません。`compatibilities`、デフォルトバージョンのマーカー、プラットフォーム／コンピューティング方式／アーキテクチャのサポート状況、リリースノート、IAM の変更、中間バージョンの要件を確認してください。アドオンを変更する前に、設定と ID の関連付けを記録します。設定に機密値が含まれる場合があるため、アクセス制限された場所にファイルを保存してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"
: "${TARGET_VERSION:?Set the Kubernetes version for this stage}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json > addon-before.json
aws eks describe-addon-versions --addon-name "$ADDON_NAME" \
  --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json > addon-candidates.json
# Select ADDON_VERSION after reviewing compatibility, architecture, compute type, and upgrade path.
: "${ADDON_VERSION:?Set the reviewed add-on version}"
aws eks describe-addon-configuration --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --output json > addon-schema.json
jq -r '.addon.configurationValues // "{}"' addon-before.json > addon-config-candidate.json
```

#### マネージドアドオンをアップグレードする

AWS Management Console、AWS CLI、または eksctl を使用して、マネージドアドオンをアップグレードできます。

候補の JSON をアップグレード先のスキーマに照らして検証し、意図した設定／ID の意味を維持してください。`PRESERVE` はマネージドフィールドの競合に対処するものであり、すべてのカスタム値を検証することや、アプリケーションの動作を保証すること、明示的に指定した部分設定を以前の JSON にマージすることを意味しません。`{}` を渡すと、設定がリセットされる場合があります。オーナーが管理するアドオンを一度に1つだけ更新し、更新 ID、健全性、バージョン、ワークロードの動作を確認してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"; : "${ADDON_VERSION:?}"
: "${REVIEWED_ADDON_CONFIG_FILE:?Provide the complete reviewed target configuration JSON}"
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG_FILE" \
  --resolve-conflicts PRESERVE --output json > addon-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' addon-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID ADDON_NAME
unset NODEGROUP_NAME
python3 eks-wait-update.py
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json
```

eksctl 0.229 の `update addon` には `--wait` と `--config-file` がありますが、`--preserve` フラグはありません。競合ポリシーは、レビュー済みの eksctl 設定に記載するか、上記の明示的な AWS CLI 手順を使用してください。`eksctl --force` はセルフマネージドアドオンから所有権を移行するものであり、汎用的な競合保持オプションではありません。

### セルフマネージドアドオン

#### セルフマネージドアドオンをアップグレードする

Helm または kubectl を使用して、セルフマネージドアドオンをアップグレードします。

既存の Helm／マニフェストのオーナーが管理する方法を使用してください。この例では、レビュー済みの Chart リポジトリ／OCI 参照と既存のリリースを前提とします。リリースがない場合に別の管理者を作らないよう、意図的に `--install` を使用していません。新しい Chart の CRD および IAM の移行要件を確認してください。`helm upgrade` だけでは、Chart の `crds/` ディレクトリ内にある CRD はアップグレードされません。Helm と raw マニフェストのデプロイは代替手段であり、連続して行う更新手順ではありません。以前の Metrics Server 0.6.1／3.8.2 の例は、アップグレード先のバージョン互換性を選択するものではありません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${RELEASE:?}"; : "${ADDON_NAMESPACE:?}"
: "${CHART_REF:?Set the verified repository/chart or OCI reference}"
: "${CHART_VERSION:?Set a reviewed compatible chart version}"
: "${REVIEWED_VALUES_FILE:?Set the complete reviewed target values file}"
umask 077
helm get values "$RELEASE" --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > addon-values-before.yaml
helm show values "$CHART_REF" --version "$CHART_VERSION" > addon-values-defaults.yaml
# Merge/migrate values and handle CRDs/IAM through the owner before this step.
helm upgrade "$RELEASE" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  -f "$REVIEWED_VALUES_FILE" --wait --timeout 15m
```

### 主要アドオンのアップグレードガイド

#### CoreDNS のアップグレード

標準ノードでは、CoreDNS の Deployment を EKS または別のツールのどちらが所有しているかを確認し、Corefile／PDB／カスタム設定を維持したうえで、選択したバージョンの移行ノートに従ってください。Auto Mode ノードでは CoreDNS はノードのシステムサービスとして動作します。Auto Mode のみで構成されたクラスターでは Deployment アドオンは不要ですが、混在クラスターでは Auto Mode 以外のノード用に DNS を維持する必要があります。Auto Mode のみの環境で Deployment が見つからなくても、アップグレード失敗と判断しないでください。

#### kube-proxy のアップグレード

kube-proxy は API server および稼働先ノードとの互換性を維持する必要があります。API server より新しいバージョンにしてはいけません。アップグレード先でサポートされるアドオンビルドを使用し、検証済みの順序に従ってください。Auto Mode はサービスネットワークを管理します。そこにセルフマネージドの kube-proxy DaemonSet があると想定しないでください。

#### VPC CNI のアップグレード

標準 EC2 ノードでは、CNI のバージョンパス、IP／prefix モード、IAM、ネットワークポリシー設定、ワークロードの接続性を確認してください。`aws-node` ConfigMap 1つにすべての設定が含まれていると想定しないでください。該当する場合は、EKS の `configurationValues`、DaemonSet／コンテナ設定、service account の ID、所有する Helm／GitOps 設定も確認してください。Auto Mode の組み込みネットワークは独自の管理パスに従います。

上記の汎用的な取得／選択／更新／待機の手順を、EKS が所有する各アドオンに適用します。標準ノードエージェントは、実際にインストールされている場合にのみ確認してください。

```bash
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset kube-proxy aws-node -o wide
```

### アドオンアップグレードのトラブルシューティング

#### よくある問題

アドオンのアップグレード中に、次のような問題が発生することがあります。

- **設定の競合**: カスタム設定と新バージョンの間で競合が発生する
- **互換性の問題**: アドオンと Kubernetes バージョンの間で互換性の問題が発生する
- **リソース制約**: アップグレードに必要なリソースが不足する

#### トラブルシューティングの手順

1. アドオンの状態を確認します。

```bash
aws eks describe-addon \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name vpc-cni
```

2. アドオンのログを確認します。

```bash
kubectl --context "$KUBE_CONTEXT" logs -n kube-system -l k8s-app=kube-dns
kubectl --context "$KUBE_CONTEXT" logs -n kube-system -l k8s-app=kube-proxy
kubectl --context "$KUBE_CONTEXT" logs -n kube-system -l k8s-app=aws-node
```

3. アドオンのイベントを確認します。

```bash
kubectl --context "$KUBE_CONTEXT" get events -n kube-system --sort-by='.lastTimestamp'
```

## アップグレードの検証とトラブルシューティング {#upgrade-validation-and-troubleshooting}

アップグレード完了後は、クラスターが正常に動作していることを検証し、発生した問題を解決する必要があります。

![アップグレード後の作業を、アップグレードの検証（クラスターのバージョン、クラスターの状態、ワークロードの検証、機能テスト）とアップグレードのトラブルシューティング（よくあるアップグレードの問題、トラブルシューティングの手順、ロールバック手順）に分けたツリー図。](../.gitbook/assets/en-eks-08-eks-upgrades-5.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-5.html)

### アップグレードの検証

#### クラスターのバージョンを確認する

クラスターとノードのバージョンを確認します。

```bash
# Check cluster version
kubectl --context "$KUBE_CONTEXT" version --output=yaml

# Check node version
kubectl --context "$KUBE_CONTEXT" get nodes -o custom-columns=NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion
```

#### クラスターの状態を確認する

クラスターコンポーネントの状態を確認します。

```bash
# Check node status
kubectl --context "$KUBE_CONTEXT" get nodes

# Check pod status
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces

# Check namespace status
kubectl --context "$KUBE_CONTEXT" get namespaces

# Check service status
kubectl --context "$KUBE_CONTEXT" get services --all-namespaces
```

#### ワークロードの検証

アプリケーションのワークロードが正常に動作していることを確認します。

```bash
# Check deployment status
kubectl --context "$KUBE_CONTEXT" get deployments --all-namespaces

# Check statefulset status
kubectl --context "$KUBE_CONTEXT" get statefulsets --all-namespaces

# Check daemonset status
kubectl --context "$KUBE_CONTEXT" get daemonsets --all-namespaces

# Check service endpoints
kubectl --context "$KUBE_CONTEXT" get endpointslices.discovery.k8s.io --all-namespaces
```

#### 機能テスト

分離された、自分たちが所有するテストリソースと、明示的な受け入れ基準を使用してください。以下の**Linux EC2 ノード向けスモークテスト**では、Deployment のロールアウト／スケーリング、Service／DNS リクエスト、および別々の Job を使った PVC データの確認を行います。負荷テストではなく、すべてのノード／AZ のテストでも、アプリケーション／HA／セキュリティの正しさの証明でもありません。ワークロード固有のテスト、ingress／egress、コントローラー／webhook、復旧テストを追加してください。Fargate／ハイブリッド／その他のプラットフォームには、それぞれに対応したテスト計画が必要です。

`eks-upgrade-smoke.py` として保存します。このスクリプトでは、この監査用に確認した公式 BusyBox イメージの固定マニフェストを使用しています。ここではイメージ取得もクラスターのテストも実行していません。実行前に、イメージポリシー、Admission／ネットワークルール、利用可能な容量、選択したノードで使用可能な互換性のあるファイルシステムの StorageClass を確認してください。`KUBE_CONTEXT`、`TEST_STORAGE_CLASS`、`RUN_SMOKE_TEST=yes` を設定し、特定の置き換えノードをテストする場合はレビュー済みの `SMOKE_NODE_SELECTOR` JSON マップも設定します。このスクリプトは一意の namespace を作成し、既存 namespace を流用せず、失敗時に停止し、実際の配置先と PV の回収に関する詳細を記録します。`WaitForFirstConsumer` ボリュームでは、完了を待つ前に書き込みを行う Pod を使用します。

リソースはレビュー用にデフォルトで保持されます。`CLEANUP_ON_SUCCESS=yes` を設定すると、チェック成功後に、その実行で作成された namespace UID のリソースだけを削除します。namespace を削除しても、クラスが Retain を使用している場合、課金対象の PV／ストレージが残る可能性があります。記録された PV を確認し、テスト用として所有するストレージだけをクリーンアップしてください。失敗は診断用に保持され、成功として報告されません。短期間の現在のメトリクスと20件の逐次 HTTP リクエストでは、性能が同等であることは確認できません。

```python
import json
import os
import subprocess
import uuid
from pathlib import Path

IMAGE = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"


def manifests(namespace, storage_class, marker, node_selector):
    if node_selector.get("kubernetes.io/os", "linux") != "linux":
        raise ValueError("This BusyBox example requires Linux nodes")
    node_selector = {"kubernetes.io/os": "linux", **node_selector}
    security = {"runAsNonRoot": True, "runAsUser": 65532, "fsGroup": 65532,
                "seccompProfile": {"type": "RuntimeDefault"}}
    container_security = {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                          "capabilities": {"drop": ["ALL"]}}
    resources = {"requests": {"cpu": "50m", "memory": "32Mi"},
                 "limits": {"cpu": "200m", "memory": "128Mi"}}

    def job(name, command, with_volume=False):
        container = {"name": "check", "image": IMAGE, "command": ["sh", "-ec", command],
                     "resources": resources, "securityContext": container_security}
        pod = {"restartPolicy": "Never", "automountServiceAccountToken": False,
               "securityContext": security, "nodeSelector": node_selector, "containers": [container]}
        if with_volume:
            container["volumeMounts"] = [{"name": "data", "mountPath": "/data"}]
            pod["volumes"] = [{"name": "data", "persistentVolumeClaim": {"claimName": "smoke-data"}}]
        return {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": name, "namespace": namespace},
                "spec": {"backoffLimit": 0, "activeDeadlineSeconds": 120,
                         "template": {"spec": pod}}}

    config = {"apiVersion": "v1", "kind": "ConfigMap",
              "metadata": {"name": "smoke-content", "namespace": namespace},
              "data": {"index.html": marker + "\n"}}
    deployment = {
        "apiVersion": "apps/v1", "kind": "Deployment",
        "metadata": {"name": "smoke-http", "namespace": namespace},
        "spec": {"replicas": 2, "selector": {"matchLabels": {"app": "smoke-http"}},
                 "template": {"metadata": {"labels": {"app": "smoke-http"}}, "spec": {
                     "automountServiceAccountToken": False, "securityContext": security,
                     "nodeSelector": node_selector,
                     "containers": [{"name": "http", "image": IMAGE,
                                     "command": ["httpd", "-f", "-p", "8080", "-h", "/www"],
                                     "securityContext": container_security, "resources": resources,
                                     "ports": [{"name": "http", "containerPort": 8080}],
                                     "readinessProbe": {"httpGet": {"path": "/", "port": "http"}},
                                     "volumeMounts": [{"name": "content", "mountPath": "/www", "readOnly": True}]}],
                     "volumes": [{"name": "content", "configMap": {"name": "smoke-content"}}],
                 }}},
    }
    service = {"apiVersion": "v1", "kind": "Service",
               "metadata": {"name": "smoke-http", "namespace": namespace},
               "spec": {"selector": {"app": "smoke-http"}, "ports": [{"port": 80, "targetPort": "http"}]}}
    pvc = {"apiVersion": "v1", "kind": "PersistentVolumeClaim",
           "metadata": {"name": "smoke-data", "namespace": namespace},
           "spec": {"storageClassName": storage_class, "accessModes": ["ReadWriteOnce"],
                    "resources": {"requests": {"storage": "1Gi"}}}}
    writer = job("smoke-write", f"printf '%s\\n' '{marker}' > /data/marker; sync", True)
    reader = job("smoke-read", f"test \"$(cat /data/marker)\" = '{marker}'", True)
    http = job("smoke-request", f"i=0; while [ \"$i\" -lt 20 ]; do "
               f"test \"$(wget -T 5 -q -O - http://smoke-http)\" = '{marker}'; "
               "i=$((i + 1)); sleep 1; done")
    return [config, deployment, service, pvc, writer], reader, http


def run_smoke(context, storage_class, node_selector, call=subprocess.run):
    if not context or not storage_class or not isinstance(node_selector, dict):
        raise ValueError("Set the reviewed context, StorageClass, and node selector map")
    namespace = "eks-upgrade-smoke-" + uuid.uuid4().hex[:12]
    marker = uuid.uuid4().hex
    evidence = Path(namespace)
    evidence.mkdir()
    prefix = ["kubectl", "--context", context]

    def kubectl(*args, payload=None):
        completed = call(prefix + list(args), input=json.dumps(payload) if payload else None,
                         check=True, capture_output=True, text=True, timeout=240)
        return completed.stdout

    # Create, never apply/adopt, the namespace. A failed creation must not lead to deletion.
    created = json.loads(kubectl("create", "namespace", namespace, "--output", "json"))
    namespace_uid = created["metadata"]["uid"]
    (evidence / "namespace.json").write_text(json.dumps(created, indent=2) + "\n")
    print(f"Owned smoke namespace: {namespace}; preserve evidence and inspect PV reclamation before cleanup.", flush=True)
    try:
        initial, reader, http = manifests(namespace, storage_class, marker, node_selector)
        kubectl("create", "-f", "-", payload={"apiVersion": "v1", "kind": "List", "items": initial})
        # The writer is a PVC consumer, so WaitForFirstConsumer provisioning can proceed.
        kubectl("-n", namespace, "wait", "--for=condition=Complete", "job/smoke-write", "--timeout=180s")
        kubectl("-n", namespace, "delete", "job", "smoke-write", "--cascade=foreground",
                "--wait=true", "--timeout=60s")
        kubectl("create", "-f", "-", payload=reader)
        kubectl("-n", namespace, "wait", "--for=condition=Complete", "job/smoke-read", "--timeout=180s")
        kubectl("-n", namespace, "rollout", "status", "deployment/smoke-http", "--timeout=180s")
        kubectl("-n", namespace, "scale", "deployment/smoke-http", "--replicas=3")
        kubectl("-n", namespace, "rollout", "status", "deployment/smoke-http", "--timeout=180s")
        kubectl("create", "-f", "-", payload=http)
        kubectl("-n", namespace, "wait", "--for=condition=Complete", "job/smoke-request", "--timeout=180s")
        pods = json.loads(kubectl("-n", namespace, "get", "pods", "--output", "json"))
        claim = json.loads(kubectl("-n", namespace, "get", "pvc", "smoke-data", "--output", "json"))
        volume = json.loads(kubectl("get", "pv", claim["spec"]["volumeName"], "--output", "json"))
        result = {"namespace": namespace, "namespaceUID": namespace_uid, "nodeSelector": node_selector,
                  "checks": ["PVC write/read across Jobs", "Deployment rollout/scale", "20 HTTP/DNS requests"],
                  "pods": pods, "pvc": claim, "pv": volume,
                  "limits": "A bounded smoke test, not a load benchmark, HA proof, or full application validation."}
        (evidence / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    except Exception:
        print(f"Smoke test failed; namespace {namespace} retained for diagnosis.", flush=True)
        raise
    print(f"Smoke checks completed. Evidence: {evidence}/result.json", flush=True)
    if os.environ.get("CLEANUP_ON_SUCCESS") == "yes":
        current = json.loads(kubectl("get", "namespace", namespace, "--output", "json"))
        if current["metadata"]["uid"] != namespace_uid:
            raise RuntimeError("Namespace identity changed; refusing cleanup")
        kubectl("delete", "namespace", namespace, "--wait=true", "--timeout=180s")
        print("Namespace deleted; inspect the recorded PV reclaim policy for retained billable storage.", flush=True)
    return namespace


if __name__ == "__main__":
    if os.environ.get("RUN_SMOKE_TEST") != "yes":
        raise SystemExit("Set RUN_SMOKE_TEST=yes only for the approved test scope")
    os.umask(0o077)
    run_smoke(os.environ["KUBE_CONTEXT"], os.environ["TEST_STORAGE_CLASS"],
              json.loads(os.environ.get("SMOKE_NODE_SELECTOR", "{}")))
```

### アップグレードのトラブルシューティング

#### よくあるアップグレードの問題

アップグレード中に、次のような問題が発生することがあります。

1. **コントロールプレーンのアップグレード失敗**:
   - API server の可用性に関する問題
   - etcd データベースに関する問題
   - IAM 権限に関する問題

2. **ノードのアップグレードに関する問題**:
   - ノードの Drain 失敗
   - 新しいノードの起動失敗
   - kubelet バージョンの不一致

3. **アドオンのアップグレードに関する問題**:
   - 設定の競合
   - 互換性の問題
   - リソース制約

4. **ワークロードの問題**:
   - API の非推奨化によるワークロードの失敗
   - リソース制約による Pod のスケジューリング失敗
   - ネットワークの問題

#### トラブルシューティングの手順

1. **ログを確認する**:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${START_TIME_MS:?Set the reviewed start timestamp in epoch milliseconds}"
: "${END_TIME_MS:?Set the reviewed analysis-window end timestamp}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.logging' --output json --no-cli-pager
# Read existing logs; enabling logging is a separate change and does not backfill history.
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
# Standard EC2-node agents only, where installed; these are Pod logs, not all host journals.
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-proxy \
  --all-containers=true --prefix=true --since=15m --tail=100
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=aws-node \
  --all-containers=true --prefix=true --since=15m --tail=100
```

2. **イベントを確認する**:

```bash
kubectl --context "$KUBE_CONTEXT" get events --all-namespaces --sort-by='.lastTimestamp'
```

3. **リソースの状態を確認する**:

```bash
kubectl --context "$KUBE_CONTEXT" describe nodes
kubectl --context "$KUBE_CONTEXT" -n "$WORKLOAD_NAMESPACE" get deployments,statefulsets,daemonsets,pods -o wide
```

4. **API バージョンを確認する**:

```bash
kubectl --context "$KUBE_CONTEXT" api-versions
```

#### ロールバック手順 {#rollback-procedure}

EKS のバージョンロールバックは、2026年7月に導入された、ユーザーが開始する実際の操作です。「ダウングレード不可」とする過去の包括的な記述ではなく、[現在のロールバックガイド](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)を使用してください。これは Kubernetes のマイナーバージョンを変更するものであり、以前の etcd／アプリケーション／PV データのスナップショットを復元するものでも、アドオンを自動的に戻すものでもありません。プラットフォームバージョンは、直前のマイナーバージョンにおける最新のプラットフォームバージョンになります。

**対象要件と準備**

- インプレースアップグレードの完了後、**7日以内**に開始してください。現在のバージョンで作成したクラスターは対象外です。戻せるのは直前のマイナーバージョンのみであり、さらに古いマイナーバージョンに連続してロールバックすることはできません。
- ロールバック先はサポート対象でなければなりません。延長サポート対象のバージョンに戻す場合は、まず `EXTENDED` サポートポリシーを採用し、料金を考慮してください。延長サポート終了時の自動アップグレードは元に戻せません。標準サポート中の自動アップグレードには、文書に記載された延長サポートポリシーの条件があります。
- クラスターが ACTIVE で、競合する更新がない必要があります。新しいバージョンで有効になった後方互換性のない EKS 機能により、ロールバックできないことがあります。`--force` でこれらの前提条件を回避することはできません。
- ロールバックインサイト、アプリケーション／クライアント／CRD／webhook の互換性、ノードスキュー、アドオンの互換性を確認してください。チェックはその時点でのベストエフォートです。ロールバック中に互換性のない変更を導入しないでください。

`ROLLBACK_READINESS` の ERROR／UNKNOWN 検出結果はロールバックをブロックします。WARNING は参考情報です。これは、通常のアップグレードインサイトに対する一時的に撤回された適用制約とは異なります。ロールバックの `--force` フラグは、インサイトチェック（ERROR／WARNING／UNKNOWN）を回避しますが、安全でない計画を安全にするものではなく、対象要件や Auto Mode の中断制御を回避することもありません。可能な限り検出結果を解決してください。上書きする場合は、明示的なリスク判断として扱います。通常の例ではこのフラグを省略しています。

```bash
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
# Set INSIGHT_ID from the response to inspect one finding.
aws eks describe-insight --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --id "$INSIGHT_ID" --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

**コントロールプレーンより前にノードとアドオンを準備する**

マネージドノードグループは、現在の[マネージドノードグループガイド](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)に記載されているとおり、`UpdateNodegroupVersion` を使ってロールバックできます。コントロールプレーンのバージョンを下げる前に実施し、その後のノード／AMI バージョンを確認してください。古い API 概要の記述には「ロールバック不可」と残っているものがありますが、現在のロールバックガイドでは、このバージョンロールバック手順が明示されています。過去の任意の AMI バージョンへのダウングレードが一般的に保証されているわけではありません。カスタム AMI のグループでは、レビュー済みの元の起動テンプレートを使用する手順が必要です。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${ROLLBACK_VERSION:?Set the reviewed previous minor for the eligible rollback}"
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > node-rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' node-rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

セルフマネージド／ハイブリッドノードはオーナーの責任で管理します。Auto Mode はコントロールプレーンより前に、自身のノードを自動的に処理します。Fargate の kubelet はインプレースでロールバックできません。互換性のない Fargate Pod が新しいバージョンで直ちに再作成されないよう、可用性とコントローラー（HPA／GitOps／Job を含む）を調整してください。テスト済みの移行／メンテナンス計画を使用し、コントロールプレーンを戻した後に Pod を再作成します。単純な Pod 削除ループでは不十分です。Fargate のスキューに関するインサイトを force で回避しても、新しい kubelet が古い API server に対してサポートされることにはなりません。

EKS はアドオンのバージョンを元に戻しません。互換性のある橋渡し／以前のアドオンバージョンとレビュー済みの設定を選択し、それぞれの更新 ID と機能チェックを使用してください。セルフマネージドのコントローラー／CRD は個別に評価する必要があります。一律の OVERWRITE や、推測で選んだ古い AL2 ノードグループをロールバック計画として使わないでください。

**コントロールプレーンのロールバックを要求して監視する**

承認済みの以前のマイナーバージョンを指定して `update-cluster-version` を使用します。別個の `rollback-cluster` コマンドはありません。これはアップグレード要求の代替手段であり、すべての更新後に自動的に実行する手順ではありません。適切なクライアント待機時間を明示し、返された更新 ID を保持してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ROLLBACK_VERSION:?}"
: "${WAIT_TIMEOUT_SECONDS:?Set an explicit client wait for the approved rollback}"
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID WAIT_TIMEOUT_SECONDS
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

**Auto Mode の所要時間とキャンセル**

Auto Mode のノードロールバック中、クラスターは **ACTIVE** のままになる場合があり、その後、コントロールプレーンのフェーズで UPDATING になります。更新 ID を通じて進行状況を追跡してください。NodePool のドリフト予算とノードの do-not-disrupt アノテーションにより、ノード置き換えがブロックされる場合があります。PDB と Pod の do-not-disrupt アノテーションは、`terminationGracePeriod` の範囲で置き換えを遅らせます。これらはアプリケーションの可用性を絶対に保証するものではありません。`--force` でこれらの制御を上書きすることはできません。

Auto Mode の `rollbackConfig.timeoutMinutes` はデフォルトで **720** で、**120～10080** を指定できます。これは最低限のタイムアウト時間であり、正確な期限ではありません。タイムアウトすると更新は失敗し、コントロールプレーンは現在のバージョンのままとなり、ノードはそのバージョンに向けてドリフトし直します。再試行時も、最初の7日間の開始期限が重要です。以下のオプションは、CLI 2.36.44 でローカルのパーサーチェックを実施しています。

```bash
# Alternative Auto Mode request: do not run this as a second request after the preceding one.
# Select a reviewed timeout from 120 to 10080 minutes; default is 720 when omitted.
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --rollback-config timeoutMinutes=720 \
  --output json --no-cli-pager > rollback-update.json
```

Auto Mode の要求後も、返された ID を使って同じ waiter を実行してください。このヘルパーのデフォルトの待機時間は2時間で、サービスのデフォルトの12時間より短いため、クライアント側の期限を慎重に設定してください。CI／IaC／認証情報のタイムアウトでは、AWS の操作はキャンセルされません。CancelUpdate を使用できるのは、コントロールプレーンのロールバック前における Auto Mode のノードフェーズのみです。ベストエフォートの操作であり、中断処理がすでに進行中のノードでは、処理が完了します。Cancelling → Cancelled の状態遷移と、その後のノードの収束を監視してください。通常のコントロールプレーンアップグレードや、開始済みのコントロールプレーンロールバックは、この方法ではキャンセルできません。

```bash
# Only during the cancellable Auto Mode node phase, before control-plane rollback starts.
aws eks cancel-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" --output json --no-cli-pager
```

CloudFormation スタックのロールバックや Git の revert によって、EKS のバージョンロールバックが自動的に開始されることはありません。明示的な復旧後は、観測されたバージョンに IaC の状態／計画を合わせてください。ロールバックの対象外であれば、前進修正、またはサポートされるバージョンで新しいクラスターを作成して、テスト済みの移行／復元を行う方法を検討してください。これらの方法では、データベースのマイグレーションやアプリケーションデータの変更が自動的に取り消されることはありません。

## アップグレードの自動化 {#upgrade-automation}

大規模な環境では、アップグレードプロセスを自動化することが重要です。次のツールや方法を使用して、EKS のアップグレードを自動化できます。

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagram of EKS upgrade automation branching into three paths -- eksctl, AWS CLI scripts, and GitOps -- each with its ordered cluster, add-on, and node group upgrade steps, plus the automation best practices that apply across all of them.](../.gitbook/assets/en-eks-08-eks-upgrades-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-6.html)
-->

### eksctl を使用した自動化

レビュー済みの eksctl 設定と、操作に合ったフラグを使用してください。`upgrade cluster --approve` はコントロールプレーンの変更を要求します。`--approve` を指定しない場合、コマンドはプレビューを表示します。ノードグループの作成には `--version` を使い、`upgrade nodegroup` には `--kubernetes-version` を使います。操作ごとにオーナー／ツールを1つ選び、実際の EKS 更新とワークロードの状態を確認してください。AWS CLI と eksctl の更新を重複して続けて要求しないでください。

### AWS CLI とスクリプトを使用した自動化

上記の読み取り専用の事前チェック、特定の更新をポーリングするヘルパー、コンポーネントごとの要求例は、自動化の構成要素です。オーケストレーターは結果を保持し、失敗、タイムアウト、不完全な検証があれば停止する必要があります。配列の順序ではなく、承認済みのアドオン／AMI／設定バージョンを使用し、カスタム AMI や Auto Mode／Fargate の違いを処理し、クライアント側の失敗後は更新 ID を使って再開する必要があります。リソースが ACTIVE になっただけで、アップグレード全体が成功したと判断してはなりません。この確認用エントリーポイントはアップグレードを開始しません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

### GitOps を使用した自動化

Git には、希望するバージョン、互換性の証拠、レビュー済みの手順書を保存できます。Argo CD／Flux は、eksctl の `ClusterConfig` ファイルを EKS コントロールプレーンの変更にネイティブ変換しません。そのため、適切な権限を持つ AWS 対応のコントローラーまたはランナーが必要です。Git／CloudFormation のロールバックによって、EKS のバージョンアップグレードが自動的に元に戻ることはありません。

次のワークフローは、意図的に**読み取り専用の準備状況収集**を行います。使用前に、上記の `eks-upgrade-preflight.py` を完全な形で `runbooks/eks-upgrade-preflight.py` にコミットしてください。信頼できるプライベートネットワーク上のランナーと、レビュー済みの AWS CLI／kubectl／Python ツールチェーンを別途用意します。固定された Actions は Node.js 24 を使用するため、セルフホストランナーがこのランタイムをサポートしている必要があります。リポジトリ変数と保護された `eks-upgrade-review` 環境を設定し、OIDC の信頼をこのリポジトリ／環境と `sts.amazonaws.com` に結び付けてください。環境名を指定するだけでは、レビュアーによる保護は設定されません。必要な EKS／STS の読み取り権限と Kubernetes のノード一覧取得権限だけを持つ確認用ロールを使用します。この例ではクラスターのバージョンを変更する権限は必要ありません。

アーティファクトをアプリケーション／API／バックアップ／容量のテストとともにレビューした後、上記のコンポーネントごとの手順を使う、別途承認された変更ステージに進んでください。このワークフローは、収集成功がアップグレード準備完了を意味するとも、本番アップグレードがテスト済みであるとも主張しません。アーティファクトへのアクセス権は、インフラストラクチャ／インサイトのメタデータの機密性に合わせてください。分離された kubeconfig はアップロードされません。

```yaml
name: Inspect EKS upgrade readiness
'on':
  workflow_dispatch:
    inputs:
      target_version:
        description: Reviewed next EKS minor version; inspection only
        required: true
        type: string
permissions:
  contents: read
  id-token: write
concurrency:
  group: eks-readiness-${{ vars.AWS_REGION }}-${{ vars.EKS_CLUSTER_NAME }}
  cancel-in-progress: false
jobs:
  inspect:
    runs-on:
    - self-hosted
    - linux
    - eks-upgrade
    environment: eks-upgrade-review
    timeout-minutes: 20
    env:
      CLUSTER_NAME: ${{ vars.EKS_CLUSTER_NAME }}
      AWS_REGION: ${{ vars.AWS_REGION }}
      EXPECTED_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}
      KUBE_CONTEXT: eks-upgrade-review
      TARGET_VERSION: ${{ inputs.target_version }}
    steps:
    - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
      with:
        persist-credentials: false
    - name: Assume the scoped review role
      uses: aws-actions/configure-aws-credentials@cbe3b392738ccf3f987d68400dafcf4b0624a56c
      with:
        role-to-assume: ${{ vars.EKS_REVIEW_ROLE_ARN }}
        aws-region: ${{ env.AWS_REGION }}
        allowed-account-ids: ${{ env.EXPECTED_ACCOUNT_ID }}
        unset-current-credentials: true
    - name: Prepare isolated context
      shell: bash
      run: "set -euo pipefail\numask 077\nEVIDENCE_DIR=\"$RUNNER_TEMP/eks-readiness-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT\"\
        \nKUBECONFIG=\"$EVIDENCE_DIR/kubeconfig\"\nexport EVIDENCE_DIR KUBECONFIG\n\
        mkdir -m 700 -p \"$EVIDENCE_DIR\"\nprintf 'EVIDENCE_DIR=%s\\nKUBECONFIG=%s\\\
        n' \"$EVIDENCE_DIR\" \"$KUBECONFIG\" >> \"$GITHUB_ENV\"\naws eks update-kubeconfig\
        \ --name \"$CLUSTER_NAME\" --region \"$AWS_REGION\" \\\n  --kubeconfig \"\
        $KUBECONFIG\" --alias \"$KUBE_CONTEXT\"\naws --version\nkubectl version --client\
        \ --output=json\npython3 --version"
      id: prepare
    - name: Collect review evidence
      shell: bash
      run: 'set -euo pipefail

        umask 077

        python3 runbooks/eks-upgrade-preflight.py > "$EVIDENCE_DIR/preflight.json"'
    - name: Preserve the review artifact
      if: ${{ always() && steps.prepare.outcome == 'success' }}
      uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
      with:
        name: eks-readiness-${{ github.run_id }}-${{ github.run_attempt }}
        path: ${{ env.EVIDENCE_DIR }}/preflight.json
        if-no-files-found: warn
        retention-days: 14
```

### 自動化のベストプラクティス

EKS のアップグレードを自動化する際のベストプラクティスは次のとおりです。

1. **段階的に進める**: 非本番環境から始め、本番環境へ進める
2. **復旧計画**: テスト済みで対象要件を考慮した復旧手順を使用し、バージョンやデータの変更をむやみに元に戻さない
3. **検証手順**: アップグレード後の自動検証手順を含める
4. **通知**: アップグレードの成功または失敗に関する通知を設定する
5. **ドキュメント**: 自動化のプロセスと手順を文書化する

## アップグレードのベストプラクティス {#upgrade-best-practices}

EKS クラスターのアップグレードに関するベストプラクティスを見ていきましょう。

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Tree diagram showing general EKS upgrade best practices across planning, preparation, execution, and post-upgrade, plus additional practices for large clusters and for financial-services compliance.](../.gitbook/assets/en-eks-08-eks-upgrades-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-7.html)
-->

### 一般的なベストプラクティス

#### アップグレードの計画

1. **バージョンの選択**: 安定したバージョンを選び、リリースノートを確認する
2. **アップグレードスケジュール**: トラフィックが少ない時間帯にアップグレードをスケジュールする
3. **段階的なアプローチ**: 非本番環境から始め、本番環境へ進める
4. **ロールバック計画**: 問題が発生した場合に備えてロールバック計画を作成する

#### アップグレードの準備

1. **バックアップ**: 重要なデータをバックアップする
2. **リソースの割り当て**: アップグレードに十分なリソースを確保する
3. **互換性の確認**: ワークロードとアドオンの互換性を確認する
4. **非推奨 API の特定**: 非推奨 API を使用するワークロードを特定して更新する

#### アップグレードの実行

1. **準備**: アップグレード先への変更前に、現在のノードバージョンと、必要な橋渡しアドオン／コントローラーをそろえる
2. **コントロールプレーンのアップグレード先**: 次のサポート対象マイナーバージョンを要求し、更新 ID を確認する
3. **依存コンポーネント**: レビュー済みの互換性順序に従って、ノード、残りのアドオン／コントローラー、クライアントをアップグレードする
4. **段階的なノードアップグレード**: ワークロードへの影響を最小限に抑えるため、ノードを段階的にアップグレードする

#### アップグレード後

1. **検証**: クラスターとワークロードの状態を検証する
2. **監視**: アップグレード後にクラスターを監視する
3. **文書化**: アップグレードのプロセスと結果を文書化する
4. **学習**: アップグレード中に発生した問題と解決策から学ぶ

### 大規模クラスター向けのベストプラクティス

大規模な EKS クラスターのアップグレードでは、次の追加のベストプラクティスが役立ちます。

1. **カナリアデプロイ**: 一部のノードまたはワークロードから始め、徐々に範囲を広げる
2. **自動化**: アップグレードプロセスを自動化する
3. **強化された監視**: アップグレード中にクラスターの状態を継続的に監視する
4. **コミュニケーション計画**: アップグレードの状況を関係者に定期的に伝える
5. **制御された復旧**: 証拠／対象要件の確認を自動化し、レビュー済みの復旧経路を適用する。ロールバックは条件付きである

### 金融サービス向けのベストプラクティス

金融サービス業界の EKS クラスターのアップグレードでは、次の追加のベストプラクティスが役立ちます。

1. **規制への準拠**: アップグレードが規制要件を満たすことを確認する
2. **リスク評価**: アップグレード前にリスクを評価する
3. **変更管理**: 厳格な変更管理プロセスに従う
4. **強化されたテスト**: アップグレード前に徹底的なテストを行う
5. **強化されたドキュメント**: アップグレードのプロセスと結果を詳しく文書化する

## まとめ

Amazon EKS クラスターを正常にアップグレードするには、十分な計画、準備、検証が必要です。このドキュメントでは、EKS クラスターのコントロールプレーン、ノードグループ、アドオンを安全にアップグレードするための戦略、手順、ベストプラクティスを説明しました。

要点:

1. **EKS のアップグレード概要**: EKS のバージョン管理、アップグレード対象のコンポーネントとパス
2. **アップグレードの計画と準備**: アップグレードの評価、準備、テスト
3. **EKS コントロールプレーンのアップグレード**: コントロールプレーンのアップグレード方法と監視
4. **ノードグループのアップグレード**: マネージド／セルフマネージドノードグループのアップグレード戦略
5. **アドオンのアップグレード**: AWS マネージド／セルフマネージドアドオンのアップグレード
6. **アップグレードの検証とトラブルシューティング**: アップグレードの検証とよくある問題の解決
7. **アップグレードの自動化**: eksctl、AWS CLI、GitOps を使用したアップグレードの自動化
8. **アップグレードのベストプラクティス**: 一般的なベストプラクティスと業界固有のベストプラクティス

EKS クラスターを最新の状態に保つことで、セキュリティパッチ、バグ修正、新機能を活用し、クラスター全体のセキュリティ、安定性、パフォーマンスを向上できます。

## 参考資料

- [Amazon EKS アップグレードのドキュメント](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Kubernetes のバージョンとバージョンスキュー](https://kubernetes.io/docs/setup/release/version-skew-policy/)
- [EKS マネージドノードグループのアップグレード](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [EKS アドオンのアップグレード](https://docs.aws.amazon.com/eks/latest/userguide/managing-add-ons.html)
- [eksctl のドキュメント](https://eksctl.io/usage/cluster-upgrade/)
- [Kubernetes アップグレードのベストプラクティス](https://kubernetes.io/docs/tasks/administer-cluster/cluster-upgrade/)

## クイズ

この章で学んだことを確認するには、[トピッククイズ](../quizzes/eks/08-eks-upgrades-quiz.md)に挑戦してください。
