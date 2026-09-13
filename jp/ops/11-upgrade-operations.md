# EKSアップグレード: Auto Mode、ロールバック、ブルー/グリーン

> **最終更新**: September 12, 2026。コマンドはAWS CLI 2.36.44、Pluto 5.24.3、Velero 1.18.2で確認しました。
> 移行例は1.35 → 1.36です。実際のリージョンでの提供状況を確認してください。

コントロールプレーン、ノード、アドオン、アプリケーション、データを一緒に計画します。
Auto ModeとPDBだけでは無停止サービスは保証されません。可用性目標に対して予備容量、
準備状態、再接続動作、セッション、状態、復旧を検証してください。

## 1. バージョンと管理責任

上流Kubernetesが保守するのは最新3マイナーリリースであり、現行に過去3バージョンを加えたものではありません。
EKSは別のライフサイクルを持ち、一般に標準サポート14か月と延長サポート12か月です。
正確な日付、方針、リージョンでの提供状況を確認します。

通常のEKS基本コントロールプレーン料金は標準サポートで$0.10/時間、延長サポートで合計
$0.60/時間（$0.10 + $0.50）です。追加料金が$0.60ではありません。
Auto Mode、コンピュート、ストレージ、ネットワーク、別途プロビジョニングするコントロールプレーン容量は追加です。

```bash
DOCS_CLUSTER="my-cluster"
DOCS_REGION="ap-northeast-2"
DOCS_CONTEXT="my-cluster-context"
DOCS_TARGET="1.36"
aws eks describe-cluster --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --query 'cluster.{version:version,status:status,platform:platformVersion,policy:upgradePolicy}'
aws eks describe-cluster-versions --region "$DOCS_REGION" \
  --cluster-versions "$DOCS_TARGET" --output json
kubectl --context "$DOCS_CONTEXT" get nodes -o wide
```

`describe-addon-versions`はアドオン互換性を確認し、クラスターのサポート日付は確認しません。
EKSコントロールプレーンは中間を飛ばさず1マイナーずつ進めます。
現在の対応バージョンではkubeletはAPIサーバーより新しくできず、上流ポリシーは条件付きで最大3マイナー古い版を許します。
ノードを古いままにする推奨ではありません。次のアップグレード前に現コントロールプレーンと揃える計画を立て、
EKSマネージドノード、Fargate、自己管理、Hybridの要件を別々に確認します。
kubectlはコントロールプレーンから1マイナー以内を使います。

| デプロイ | 更新責任 |
|---|---|
| Auto Modeのみ | サービス管理のノード、ネットワーク、ブロックストレージ、LB機能 |
| 通常/自己管理/Hybridノード | ノード、CNI、DNS、プロキシ、ドライバー、コントローラー更新を計画 |
| 混在クラスター | 非Autoノードに必要なアドオンを保持 |
| アプリ、自己管理コントローラー、EKSアドオン | インストール済みバージョン、設定、CRDを検証 |

Auto ModeのみではCoreDNSをノードシステムサービスとして使います。CoreDNS Deploymentがないだけでは
障害ではありません。混在クラスターは他ノードに必要なDNS Deploymentを保持します。
Auto Modeで通常ノード用aws-node/kube-proxy/Pod Identity agent Podを無条件にインストールしたり探したりしないでください。
互換性のためコントロールプレーン更新前に作業が必要な場合があり、
「コントロールプレーン → 全アドオン → ノード」は普遍的な順序ではありません。

| APIの安定性 | 非推奨化ポリシー |
|---|---|
| GA | 非推奨化可能だが同じKubernetesメジャー内では削除されない |
| Beta | 非推奨化から最低9か月または3マイナーの長い方を経て提供を削除 |
| Alpha | 事前の非推奨通知なしに削除可能 |

CLIフラグとメトリクスのポリシーは異なります。古い互換表をコピーせず、移行ガイドと実際の
インストール済みバージョン、アーキテクチャ、プラットフォームバージョン、コンピュートタイプを比較します。

## 2. アップグレード前のレビュー

アップグレードインサイトにはタイミングと範囲の制限があります。公式ガイドには、一部のインサイト問題で
`--force`を要求することを一時停止中との記載がまだあります。
後述のロールバック準備状態ERROR/UNKNOWNによるブロックと区別してください。
APIが受け入れたことは準備状況レビューの完了ではありません。

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.3は終了0（問題なし）、2（非推奨）、3（削除済み）を区別します。
すべての非ゼロを「未インストール」に変えたり、`|| true`で隠したりしないでください。
JSONはオブジェクトです。`.items // []`を数えます。問題のない応答ではitemsが省略される場合があります。
`detect-all-in-cluster`も有効です。公式リリースのアーキテクチャとチェックサムを確認します。

APIサーバーがオブジェクトを変換するため、ライブ検出では元のAPIバージョンを見逃すことがあります。
Git、Helm/Kustomizeのレンダリング結果、リリースメタデータ、API警告/監査、実際のクライアントを確認します。
Plutoの他コンポーネント対象も、デプロイ済みIstio/cert-managerバージョンに合わせてください。

この読み取り専用ツールはEKSとkubecontextのエンドポイントを比較してから、Node/Pod準備状態、
Deploymentのgeneration/ロールアウト、PDB、実際にインストールされたアドオンを確認します。
プロキシkubeconfigは直接EKSエンドポイントと異なる場合があり、別レビューが必要です。

```python
# preflight.py
"""Read-only upgrade review report. A clean report is not upgrade authorization."""
import argparse
import json
import re
import subprocess
import sys


class CheckError(RuntimeError):
    pass


def command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise CheckError(f"{argv[0]} query failed (exit {result.returncode}); inspect permissions and connectivity")
    return result.stdout.strip()


def decode(text):
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise CheckError("A command returned invalid JSON") from error
    if not isinstance(value, dict):
        raise CheckError("Expected a JSON object from the command")
    return value


def assess(cluster, target, nodes, pods, deployments, pdbs, addons):
    findings = []
    if cluster.get("status") != "ACTIVE":
        findings.append("Cluster is not ACTIVE")
    current = cluster.get("version", "")
    if not re.fullmatch(r"1\.\d+", current) or int(target.split(".")[1]) != int(current.split(".")[1]) + 1:
        findings.append("Target must be exactly the next minor version")
    for node in nodes:
        ready = next((c.get("status") for c in node.get("status", {}).get("conditions", []) if c.get("type") == "Ready"), None)
        if ready != "True":
            findings.append(f"Node {node['metadata']['name']}: Ready={ready or 'missing'}")
        version = node.get("status", {}).get("nodeInfo", {}).get("kubeletVersion", "")
        minor = re.match(r"^v?(1\.\d+)\.", version)
        if not minor or minor.group(1) != current:
            findings.append(f"Node {node['metadata']['name']}: kubelet={version or 'unknown'}; review version alignment and supported skew")
    for pod in pods:
        metadata, status = pod["metadata"], pod.get("status", {})
        name = f"{metadata.get('namespace', 'default')}/{metadata['name']}"
        if metadata.get("deletionTimestamp"):
            findings.append(f"Pod {name}: terminating")
            continue
        if status.get("phase") == "Succeeded":
            continue
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in status.get("conditions", []))
        if status.get("phase") != "Running" or not ready:
            findings.append(f"Pod {name}: phase={status.get('phase', 'unknown')}, Ready={ready}")
    for deployment in deployments:
        metadata = deployment["metadata"]
        spec, status = deployment.get("spec", {}), deployment.get("status", {})
        desired = spec.get("replicas", 1)
        current_generation = status.get("observedGeneration", 0) >= metadata.get("generation", 1)
        rolled_out = all(status.get(key, 0) >= desired for key in ("updatedReplicas", "readyReplicas", "availableReplicas"))
        if not current_generation or not rolled_out:
            findings.append(f"Deployment {metadata.get('namespace', 'default')}/{metadata['name']}: rollout incomplete")
    for pdb in pdbs:
        metadata, status = pdb["metadata"], pdb.get("status", {})
        name = f"{metadata.get('namespace', 'default')}/{metadata['name']}"
        if status.get("observedGeneration", 0) < metadata.get("generation", 1):
            findings.append(f"PDB {name}: status is stale or missing")
        elif status.get("expectedPods", 0) > 0 and status.get("disruptionsAllowed", 0) == 0:
            findings.append(f"PDB {name}: no disruptions currently allowed; assess affected nodes and workloads")
    for addon in addons:
        if addon["status"] != "ACTIVE":
            findings.append(f"Add-on {addon['name']}: status={addon['status']}")
        if not addon["currentVersionAdvertisedForTarget"]:
            findings.append(f"Add-on {addon['name']}: current version not advertised for target")
    return findings


def collect(args, execute=command):
    def aws(operation, *params):
        return decode(execute(["aws", "eks", operation, "--region", args.region,
                               "--output", "json", "--no-cli-pager", *params]))

    def kube(resource):
        result = decode(execute(["kubectl", "--context", args.context, "get", resource, "-A", "-o", "json"]))
        if not isinstance(result.get("items"), list):
            raise CheckError(f"Missing items list for {resource}")
        return result["items"]

    cluster = aws("describe-cluster", "--name", args.cluster,
                  "--query", "cluster.{name:name,status:status,version:version,endpoint:endpoint,platformVersion:platformVersion,computeConfig:computeConfig}")
    server = execute(["kubectl", "--context", args.context, "config", "view", "--minify",
                      "-o", "jsonpath={.clusters[0].cluster.server}"])
    if not cluster.get("endpoint") or server.rstrip("/") != cluster["endpoint"].rstrip("/"):
        raise CheckError("Kubernetes context does not point at the selected EKS endpoint")
    versions = aws("describe-cluster-versions", "--cluster-versions", args.target)
    advertised = versions.get("clusterVersions", [])
    if not any(v.get("clusterVersion") == args.target for v in advertised):
        raise CheckError("Target version is not advertised by EKS in this region")
    insights = aws("list-insights", "--cluster-name", args.cluster,
                   "--filter", json.dumps({"categories":["UPGRADE_READINESS"], "kubernetesVersions":[args.target]}))
    addon_names = aws("list-addons", "--cluster-name", args.cluster).get("addons")
    if not isinstance(addon_names, list):
        raise CheckError("Missing add-on list")
    addons = []
    for name in addon_names:
        installed = aws("describe-addon", "--cluster-name", args.cluster, "--addon-name", name,
                        "--query", "addon.{name:addonName,version:addonVersion,status:status}")
        available = aws("describe-addon-versions", "--addon-name", name, "--kubernetes-version", args.target)
        matches = [version for entry in available.get("addons", [])
                   if entry.get("addonName") == name
                   for version in entry.get("addonVersions", [])
                   if version.get("addonVersion") == installed["version"]
                   and any(c.get("clusterVersion") == args.target for c in version.get("compatibilities", []))]
        addons.append({**installed, "currentVersionAdvertisedForTarget": bool(matches),
                       "matchingVersionMetadata": matches})
    nodes, pods, deployments, pdbs = (kube(name) for name in ("nodes", "pods", "deployments", "pdb"))
    findings = assess(cluster, args.target, nodes, pods, deployments, pdbs, addons)
    if not nodes:
        findings.append("No nodes returned; verify intended compute capacity separately")
    if not isinstance(insights.get("insights"), list):
        raise CheckError("Missing upgrade insight list")
    if not insights["insights"]:
        findings.append("No target-version upgrade insights returned; review coverage and freshness")
    for insight in insights.get("insights", []):
        status = insight.get("insightStatus", {}).get("status", "UNKNOWN")
        if status != "PASSING":
            findings.append(f"Upgrade insight {insight.get('id', 'unknown')}: {status}")
    return {
        "cluster": args.cluster, "region": args.region, "context": args.context,
        "currentVersion": cluster["version"], "targetVersion": args.target,
        "platformVersion": cluster.get("platformVersion"),
        "computeConfig": cluster.get("computeConfig"),
        "nodeVersions": {n["metadata"]["name"]:n.get("status", {}).get("nodeInfo", {}).get("kubeletVersion") for n in nodes},
        "observedCounts": {"nodes":len(nodes), "pods":len(pods), "deployments":len(deployments), "pdbs":len(pdbs)},
        "reportStatus": "review-required" if findings else "checks-collected",
        "findings": findings, "targetVersionMetadata": advertised,
        "addons": addons, "upgradeInsights": insights.get("insights", []),
        "limits": [
            "No mutation was performed. checks-collected is not permission to upgrade.",
            "Version advertisement does not validate all architecture/platform/compute-type combinations or configuration migrations.",
            "Readiness snapshots do not prove application, storage, DNS, capacity, backup or recovery behavior.",
            "No control-plane version change or IaC plan should run automatically from this report."
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"1\.\d+", args.target):
        parser.error("--target must be an EKS minor version such as 1.36")
    try:
        report = collect(args)
    except (CheckError, KeyError, TypeError, subprocess.TimeoutExpired, OSError) as error:
        print(json.dumps({"reportStatus":"unknown", "error":str(error)}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 2 if report["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
```

```bash
python3 preflight.py --cluster "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --context "$DOCS_CONTEXT" --target "$DOCS_TARGET" > preflight-report.json
```

終了0は列挙された確認を収集済み、2は指摘あり、1はエラーによる不明な結果です。
0は自動アップグレード承認やアプリケーション全体の健全性の証明ではありません。
提示されたアドオンバージョンにも、アーキテクチャ/プラットフォーム/コンピュートタイプと設定の確認が必要です。

maxUnavailable 1のPDBでも、異常Podや重複PDBにより許可中断数が0になる場合があります。
AlwaysAllowは異常Podの退避動作を変えますが、可用性は保証しません。

```yaml
# pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api
  namespace: production
spec:
  maxUnavailable: 1
  unhealthyPodEvictionPolicy: AlwaysAllow
  selector:
    matchLabels:
      app: api
```

NodeフェーズやPod Runningだけから健全性を推測しないでください。0レプリカDeployment、完了Job、
空のPDBセレクターを区別します。EndpointSliceのready/serving/terminating条件とServiceセレクターを調べます。
セレクターなし/ExternalName Serviceには通常のPodエンドポイントは不要です。

## 3. バックアップと復元の検証

マネージドEKSのバックアップは、顧客が任意のetcdスナップショットから復元を制御できる意味ではありません。
Git/IaC、Kubernetesオブジェクト、PVデータ、外部DB、権限、暗号化キー、復旧手順を分けて扱います。
先にVelero BackupStorageLocation、プラグイン/CSIスナップショット設定、IAMを準備します。
このScheduleはproductionを明示的に選びます。
デフォルトBackup CLIは`*`名前空間を含み、velero全体を自動除外しません。

```yaml
# backup-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: production-daily
  namespace: velero
spec:
  schedule: "CRON_TZ=UTC 0 2 * * *"
  template:
    includedNamespaces:
      - production
    storageLocation: default
    snapshotVolumes: true
    defaultVolumesToFsBackup: false
    ttl: 720h
```

```bash
DOCS_BACKUP="pre-upgrade-$(date -u +%Y%m%dT%H%M%SZ)"
velero --kubecontext "$DOCS_CONTEXT" backup create "$DOCS_BACKUP" \
  --include-namespaces production --snapshot-volumes --ttl 720h --wait
velero --kubecontext "$DOCS_CONTEXT" backup describe "$DOCS_BACKUP" --details
velero --kubecontext "$DOCS_CONTEXT" backup logs "$DOCS_BACKUP"
```

Completedはアプリケーション整合性や全ボリュームの復旧を証明しません。
エラー/警告、スナップショット/データムーバー結果、除外ボリューム、DB静止化/レプリケーションを確認します。
PVC/PVオブジェクトだけでは完全なアプリケーション/Secret/Service/データのバックアップではありません。
ファイルシステムバックアップには別途node-agentとボリューム設定が必要です。

Velero 1.18.2のrestore createには`--dry-run`がありません。
`-o yaml/json`はRestoreを作らず表示しますが、検出/Backup読み取りを実行します。
完全なオフライン動作でも復旧テストでもありません。

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

隔離テスト環境で実際に復元します。名前空間マッピングだけではCronJob、コンシューマー、外部DB、
DNS/LB変更は分離されません。
テストクラスター用のバックアップストレージ書き込み所有権、スナップショットのリージョン/AZ、KMS/IAMを確認します。
適切なら同期に読み取り専用BackupStorageLocationを使用します。
復元作成、Pod起動、ボリューム接続、整合性、アプリケーション動作を別々にテストします。
テストのクリーンアップで元のバックアップを削除しないでください。

## 4. コントロールプレーンとノードの更新

[インフラの章](./01-infrastructure-setup.md)の既存クラスター層を使います。
新しいstateに重複クラスターを作ったり、VPC/IAMを再構築したりしないでください。
モジュール/プロバイダーのメジャー変更とKubernetesマイナー変更を分けて確認します。
古いEKSモジュールv20の入力を現モジュールに混ぜないでください。
tfvarsは実際の絶対ファイルパスに置き換えます。

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

CLI変更を選ぶ場合、同じ設定へのIaC変更を同時に行わないでください。
次のコマンドは準備状況レビュー後に実際の変更を行います。更新IDを記録します。

```bash
DOCS_UPDATE_ID=$(aws eks update-cluster-version \
  --name "$DOCS_CLUSTER" --region "$DOCS_REGION" --kubernetes-version "$DOCS_TARGET" \
  --query 'update.id' --output text)
printf '%s\n' "$DOCS_UPDATE_ID"
```

```python
# wait_update.py
"""Observe a known EKS update ID; a client timeout never cancels the AWS operation."""
import argparse
import json
import subprocess
import sys
import time


def wait_for_update(fetch, timeout, interval=15, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    while True:
        update = fetch()
        status = update.get("status")
        if status in ("Successful", "Failed", "Cancelled"):
            return {"status": status, "errors": update.get("errors", [])}
        if status not in ("InProgress", "Cancelling"):
            raise RuntimeError(f"Unexpected update status: {status!r}")
        remaining = deadline-clock()
        if remaining <= 0:
            return {"status":"ClientTimeout", "lastServerStatus":status,
                    "note":"AWS update may still be running; resume observation with the same update ID."}
        sleep(min(interval, remaining))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--update-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=5400)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("timeout must be positive")

    def fetch():
        process = subprocess.run([
            "aws","eks","describe-update","--name",args.cluster,"--region",args.region,
            "--update-id",args.update_id,"--output","json","--no-cli-pager",
        ],capture_output=True,text=True,timeout=60)
        if process.returncode:
            raise RuntimeError(f"describe-update failed (exit {process.returncode}); state is unknown")
        update = json.loads(process.stdout)["update"]
        if update.get("id") != args.update_id:
            raise RuntimeError("Response update ID did not match")
        return update

    try:
        result = wait_for_update(fetch, args.timeout_seconds)
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"updateId":args.update_id,"status":"Unknown","error":str(error)}))
        return 1
    print(json.dumps({"updateId":args.update_id, **result},indent=2))
    return 0 if result["status"] == "Successful" else (2 if result["status"] == "ClientTimeout" else 1)


if __name__ == "__main__":
    sys.exit(main())
```

```bash
python3 wait_update.py --cluster "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_UPDATE_ID" --timeout-seconds 5400
```

終了0はSuccessful、1は失敗/キャンセル/照会エラー、2はクライアントタイムアウトです。
タイムアウトはAWS操作をキャンセルしません。同じIDの観察を再開してください。
開始後のコントロールプレーン更新を任意に一時停止/停止することはできません。
cluster-activeだけではノード置換の完了は示されません。
その後に実バージョン、ノード、アプリケーションを再確認します。

Auto Modeはコントロールプレーン更新後にノードを段階的に置き換えます。
顧客はEC2NodeClass al2023@latestでAuto Mode AMIを選びません。
通常のマネージド/自己管理/Hybridノードと既存Fargate Podは別対応が必要です。
EKSアドオンがすべて自動更新されるわけではありません。describe-addon-configurationでバージョンと
設定スキーマを確認し、OVERWRITEを無差別に適用しないでください。

### 中断制約

適用されるNodePool予算は最も厳しい制約として組み合わされます。
10%と1は「最低1つ」を意味しません。丸め、削除中/NotReadyノード、UTCスケジュールを考慮します。
スケジュール付き予算だけでは有効時間外の中断を禁止しません。

自発的ドリフトを一時停止するには既存予算を保持・確認し、
`nodes: "0", reasons: [Drifted]`のようなポリシーを追加してから元に戻します。
NodePoolメタデータのdo-not-disruptアノテーションはこの停止手段ではありません。
Node/Podアノテーションと予算は、全中断、有効期限、終了猶予経路を防ぎません。

| 手動drainオプション | 意味 |
|---|---|
| `--ignore-daemonsets` | DaemonSet Podを削除せず除外 |
| `--delete-emptydir-data` | emptyDirのデータ損失を許可 |
| `--disable-eviction` | Evictionを使わず削除し、PDB保護を迂回 |

DaemonSetは適格ノード上で動作します。汎用対処として強制削除/PDB迂回を自動化しないでください。

## 5. ネイティブのKubernetesバージョンロールバック

EKSはアップグレード完了から7日以内に、直前のマイナーへのロールバック開始をサポートします。
「コントロールプレーンは決してロールバックできない」はもはや正しくありません。
制約には現バージョンで作成したクラスター、期限切れ、延長サポート終了時の自動更新、
対象と互換性のないEKS機能があります。連続更新後は直前のマイナーだけが対象です。
延長サポートの対象版には対応する方針と費用条件が必要です。

| コンポーネント | 対応 |
|---|---|
| APIサーバー/コントロールプレーン | 直前のKubernetesマイナーとその最新プラットフォーム版 |
| Auto Modeノード | サービスが先にノードを調整し、その後コントロールプレーンを戻す |
| 通常のマネージドノードグループ | 利用者が先にUpdateNodegroupVersionで調整 |
| 自己管理/Hybridノード | 利用者が先に互換ノードへ置換 |
| Fargate | 既存Pod kubeletの直接ダウングレードなし。別途置換/互換性を計画 |
| アドオン、アプリ、etcdオブジェクト、PVデータ | 過去スナップショットから復元されない |

データ復元や即時のトラフィック切り戻しではありません。
新API/フィールド、コントローラー、DBスキーマと前バージョンの互換性を検証します。

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}'
DOCS_PREVIOUS="1.35"
DOCS_ROLLBACK_ID=$(aws eks update-cluster-version \
  --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --kubernetes-version "$DOCS_PREVIOUS" --rollback-config timeoutMinutes=1440 \
  --query 'update.id' --output text)
python3 wait_update.py --cluster "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID" --timeout-seconds 5400
```

テストしたCLI 2.36.44はrollback-configをサポートし、環境の旧2.35.11は非対応でした。
古いCLIの不明オプションをEKS機能の不在と混同しないでください。
公式更新済みCLIまたは対応API/SDKを使います。別のaws eks rollback-clusterコマンドはありません。

ロールバック準備状態ERROR/UNKNOWNは操作をブロックし、WARNINGは助言です。
Forceはインサイト確認を迂回できますが、適格条件やAuto Mode中断制御は迂回できません。
基準設定はforceを使いません。

### Auto Modeの観察とキャンセル

ノードのロールバック中、コントロールプレーンは新バージョンを提供し続け、クラスター状態はACTIVEです。
ノードが対象スキュー要件を満たすとEKSはインサイトを再確認し、その後CPをロールバックします。
更新IDを観察します。ノードタイムアウトはデフォルト720分、範囲120–10,080分です。
正確なタイマーではなく最小境界です。7日間の開始期限と、開始済みノード段階のタイムアウトを区別します。
タイムアウト時はCPが現バージョンに留まり、ノードはそれに向けて戻り、更新はFailedになります。

Drift予算0やノードのdo-not-disruptは進行をブロックし得ます。PDB/Podアノテーションは
TerminationGracePeriodまで中断を遅らせられますが、永久に防ぎません。
ノード段階ではベストエフォートのキャンセルが可能ですが、開始済みの個別中断は完了する場合があります。
CPロールバック開始後はキャンセルできません。

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

キャンセル後、ノードは現在のCPバージョンに向けて戻ります。
IaCタイムアウトはAWS操作を止めず、CloudFormationスタックのロールバックは自動的なKubernetesバージョン
ロールバックではありません。CLI/API変更後はIaCの実際と期待のバージョンを整合させます。

## 6. ブルー/グリーン

Greenには別のstate/IDを使い、共有DNS/NLB/DB所有権をBlueの削除範囲外に置きます。
実エンドポイント/CA、ワークロードID、assume-role、EKSアクセスエントリ、Kubernetes RBACは
[マルチクラスターGitOps](./04-gitops-multi-cluster.md)の手順で登録します。
クラスターSecretはGreenでなくHubコンテキストに適用します。

このApplicationSetは自動同期なしでGreenだけを選びます。
本番AppProject/名前空間、リポジトリ、承認済みリビジョンを準備します。
URL/SHAプレースホルダーを置き換え、ワーカー、コンシューマー、CronJobの同時有効化を制御します。
preserveResourcesOnDeletionは、セレクター変更で生成Applicationが削除された場合にワークロードを保護します。
保持は管理の引き継ぎではありません。色/セレクター変更前に定常状態のGitOps所有権を計画してください。

```yaml
# applicationset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: upgrade-validation
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  syncPolicy:
    preserveResourcesOnDeletion: true
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  environment: production
                  cluster-color: green
          - list:
              elements:
                - app: api
                  namespace: production
  template:
    metadata:
      name: '{{.app}}-{{.nameNormalized}}'
      labels:
        migration: upgrade-validation
        cluster-color: '{{index .metadata.labels "cluster-color"}}'
    spec:
      project: production
      source:
        repoURL: https://github.com/your-org/platform-manifests.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT_SHA
        path: 'apps/{{.app}}'
      destination:
        server: '{{.server}}'
        namespace: '{{.namespace}}'
```

```bash
kubectl --context argocd-hub apply -f applicationset.yaml
argocd app list --selector migration=upgrade-validation
# Use the actual generated Application name:
argocd app diff api-my-cluster-green
argocd app sync api-my-cluster-green
argocd app wait api-my-cluster-green --sync --health --timeout 300
```

Gitリビジョンを戻すには、承認済みGit状態を復元して同期します。
argocd app rollbackはSHAでなくデプロイ履歴IDを取ります。
そうしないと自動同期/ApplicationSetの期待状態により再び変更される場合があります。

### Greenを直接テスト

PodのRunningやTCP接続はDB/メッセージ/準備状態の動作を証明しません。
Greenへの直接経路を使い、サービスホスト名のSNI/Hostと証明書検証を維持します。
NLBのAWSホスト名はアプリケーションTLSホスト名ではありません。
443で実際にHTTPSを提供するServiceには、別ターミナルで次を使います。

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

別のターミナルでは、実ホスト名、パス、応答契約を使います。

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### NLBの重み

NLBの重み付きターゲットグループはサポートされています。相対重みは0–999で、合計100でなくても構いません。
新規接続の期待比率を表し、正確なリクエスト、バイト、既存セッションの比率ではありません。
クラスターごとに別TGへ正常ターゲットを登録します。
TGB、ターゲットタイプ、ネットワーク/セキュリティグループは[高度なインフラ](./02-infrastructure-advanced.md)を参照してください。

通常の重み変更は新規接続に影響しますが、0にすると短時間後に既存接続が閉じられる場合があります。
無中断のドレインではありません。接続寿命、再試行、セッションをテストします。
TCP/UDP/TCP_UDPはターゲットグループのスティッキネスをサポートし、TLSリスナーはしません。
TCP転送のスティッキネスはALB専用機能ではありません。
APIはALBのDurationSecondsを文書化しています。その期間保証をNLBにコピーしないでください。

このツールはJSONを生成するだけです。先に実リスナープロトコルとターゲットグループのVPC、
プロトコル/IPファミリー、健全性、既存スティッキネスを確認します。

```python
# traffic_action.py
"""Generate one NLB action for review. This program does not call AWS."""
import argparse
import json
import re


def action(listener, blue, green, blue_weight, green_weight, protocol="TCP", sticky=False):
    if not re.fullmatch(r"arn:[a-z0-9-]+:elasticloadbalancing:[a-z0-9-]+:\d{12}:listener/net/[^/]+/[^/]+/[^/]+", listener):
        raise ValueError("Expected a Network Load Balancer listener ARN")
    for target in (blue, green):
        if not re.fullmatch(r"arn:[a-z0-9-]+:elasticloadbalancing:[a-z0-9-]+:\d{12}:targetgroup/[^/]+/[^/]+", target):
            raise ValueError("Invalid target group ARN")
    if blue == green:
        raise ValueError("Blue and green must be separate target groups")
    if any(type(weight) is not int or not 0 <= weight <= 999 for weight in (blue_weight, green_weight)):
        raise ValueError("Weights must be integers from 0 to 999")
    if blue_weight + green_weight == 0:
        raise ValueError("At least one target group must have a positive weight")
    if protocol not in ("TCP","TLS","UDP","TCP_UDP"):
        raise ValueError("Select the actual listener protocol")
    if type(sticky) is not bool:
        raise ValueError("sticky must be a boolean")
    if protocol == "TLS" and sticky:
        raise ValueError("TLS listeners do not support target group stickiness")
    forward = {
        "TargetGroups":[{"TargetGroupArn":blue,"Weight":blue_weight},
                        {"TargetGroupArn":green,"Weight":green_weight}],
        "TargetGroupStickinessConfig":{"Enabled":sticky},
    }
    return {"ListenerArn":listener,"DefaultActions":[{"Type":"forward","ForwardConfig":forward}]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--listener-arn",required=True)
    parser.add_argument("--blue-arn",required=True)
    parser.add_argument("--green-arn",required=True)
    parser.add_argument("--blue-weight",type=int,required=True)
    parser.add_argument("--green-weight",type=int,required=True)
    parser.add_argument("--protocol",choices=["TCP","TLS","UDP","TCP_UDP"],default="TCP")
    parser.add_argument("--sticky",action="store_true")
    args=parser.parse_args()
    try:
        result=action(args.listener_arn,args.blue_arn,args.green_arn,args.blue_weight,args.green_weight,
                      args.protocol,args.sticky)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
```

```bash
python3 traffic_action.py --listener-arn "$DOCS_LISTENER_ARN" \
  --blue-arn "$DOCS_BLUE_TG_ARN" --green-arn "$DOCS_GREEN_TG_ARN" \
  --blue-weight 90 --green-weight 10 --protocol TCP > traffic-action.json
# After reviewing this one stage and target health:
aws elbv2 modify-listener --region "$DOCS_REGION" --cli-input-json file://traffic-action.json
aws elbv2 describe-listeners --region "$DOCS_REGION" \
  --listener-arns "$DOCS_LISTENER_ARN" --output json
```

先に3つのARN変数を設定します。タイマーだけで割合を進めないでください。
各段階でSLO、新規/既存接続、エラー、セッションを観察します。
別TGへのフェイルオーバーを想定せず、重み0、異常ターゲット、クロスゾーン動作をテストします。
共有NLB背後のGreen検証には別の直接Service経路を使います。

### データとクリーンアップ

外部RDS/ElastiCacheや共有EFSでも、スキーマ、権限、キャッシュ形式、同時書き込み/コンシューマー移行作業はなくなりません。
共有ファイルシステムや1つのSQL件数確認だけでは整合性は成立しません。
スナップショットのリージョン/AZ、ストレージクラス、KMS、最後の書き込みからのRPOを確認します。

合意した観察/復旧期間とデータ互換性検証が終わるまでBlueを保持します。
重み0のTGもリスナーから参照されている場合があります。
Auto ModeのTGB/クラスター削除は関連TGのライフサイクルに影響します。共有リスナーからBlue TG参照を
削除し、所有権、IaC、削除順序を確認してからクリーンアップします。
自己管理LB Controllerの外部TG所有権とは区別してください。
トラフィック移行直後にterraform destroyを自動実行しないでください。

ワーカーがすでにAZごとに分離したクラスターで動く場合、1クラスターずつ更新する選択肢があります。
各EKSコントロールプレーンが単一AZになるわけではありません。
他クラスターの予備容量/状態互換性と、ネイティブロールバック適格条件/期間を検証します。
7日間の期限はBlueへの即時切り戻しを保証しません。

## 7. アップグレード後の検証

更新Successful後、実バージョン、Node/Pod Ready、コントローラーgeneration、DNS/ネットワーク経路、
ストレージ、権限、アプリケーション動作、スケジュール済み処理を検証します。
countはゼロ値の条件/フェーズサンプルも数えます。以下のように値を集約し、観測欠損を正常なゼロに変えないでください。
複数クラスターでは収集に実際のclusterラベルが必要です。

```promql
count by (cluster, kubelet_version) (
  max by (cluster, node, kubelet_version) (kube_node_info)
)
```

```promql
sum by (cluster) (
  max by (cluster, node) (
    kube_node_status_condition{condition="Ready",status=~"false|unknown"}
  )
)
```

```promql
sum by (cluster) (
  max by (cluster, namespace, pod) (kube_pod_status_phase{phase="Pending"})
)
```

Pod再起動数は再スケジュール数ではありません。Auto Modeコントローラーメトリクスが
自己管理Karpenter Podからスクレイプされると想定しないでください。
以下には実際のservice=apiラベル/メトリクス契約が必要です。
トラフィック0は正常なエラー率0ではありません。総トラフィック系列が存在してrateが正の場合だけ、
欠けたエラー系列を0で埋めます。

```promql
(
  sum by (cluster, service) (rate(http_requests_total{service="api",status=~"5.."}[5m]))
  or
  0 * sum by (cluster, service) (rate(http_requests_total{service="api"}[5m]))
)
/
(
  sum by (cluster, service) (rate(http_requests_total{service="api"}[5m])) > 0
)
```

```promql
histogram_quantile(0.99,
  sum by (cluster, service, le) (
    rate(http_request_duration_seconds_bucket{service="api"}[5m])
  )
)
```

過去との比較では分子、分母、バケットに同じoffsetを使います。
[30m] offset 1hは現在の90–60分前を対象とし、60–30分前ではありません。
同等の集団を比較します。blue/greenは通信、経路、サンプル数、負荷が異なる場合があります。
72時間では1週間の全パターンをカバーしません。ワークロード周期とロールバック適格期間から観察期間を選びます。

[スタックの章](./09-observability-stack.md)の明示的UIDと完全なダッシュボードプロビジョニングを使います。
部分パネルYAML/JSONを完全なインポート可能ダッシュボードとして提示しないでください。
前後のバージョン、更新ID、計画/実際の時間、失敗、復旧結果を記録します。

このレビューは合成の事前確認/待機/ルーティングケース、公式CLIパーサー、VeleroのGET専用出力動作、
マニフェスト/クエリを確認しました。実際のEKS更新/ロールバック、NLB変更、
スナップショット/復元、アプリケーション負荷テストは実行していません。

## 公式参考資料

- [EKS更新](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKSロールバック](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Auto Modeロールバック](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Auto Modeアップグレード](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [EKS料金](https://aws.amazon.com/eks/pricing/)
- [Kubernetesバージョンスキュー](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes非推奨化ポリシー](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.3](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.3)
- [Velero 1.18.2](https://github.com/velero-io/velero/releases/tag/v1.18.2)
- [NLBリスナー](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [前: リソース最適化](./10-resource-optimization.md) | [目次](./README.md) | [次: イベント容量計画](./12-event-capacity-planning.md) >
