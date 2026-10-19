# EKS アップグレード: Auto Mode、ロールバック、ブルー/グリーン

> **最終更新**: 2026年10月16日。コマンドは2026年9月12日に確認し、Pluto と Velero は2026年10月16日に再確認しました（AWS CLI 2.36.44、Pluto 5.24.4、Velero 1.18.4）。
> 例の移行は 1.35 → 1.36 です。実際のリージョンでの提供状況を確認してください。

コントロールプレーン、ノード、アドオン、アプリケーション、データをまとめて計画します。
Auto Mode と PDB だけでは中断のないサービスを保証できません。可用性目標に照らして、予備容量、
readiness、再接続動作、セッション、状態、復旧を検証してください。

## 1. バージョンと管理責任

Upstream Kubernetes は、現在のリリースに加えて過去 3 バージョンではなく、直近 3 つのマイナーリリースの
リリースブランチを維持します（2026年10月12日時点で 1.35–1.37）。各マイナーリリースにはおよそ 14 か月の
パッチが提供され、その最後の 2 か月はメンテナンスモードです。1.34 は 2026年10月27日の EOL まで
メンテナンスモードです。EKS には別のライフサイクルがあり、通常は 14 か月の標準サポートと
12 か月の延長サポートです。正確な日付、ポリシー、リージョンでの提供状況を確認してください。

通常の EKS ベースコントロールプレーン料金は、標準サポートでは $0.10/hour、延長サポートでは合計
$0.60/hour（$0.10 + $0.50）です。追加料金は $0.60 ではありません。
Auto Mode、コンピュート、ストレージ、ネットワーキング、別途プロビジョニングされたコントロールプレーン容量には追加料金がかかります。

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

`describe-addon-versions` はアドオンの互換性を確認するものであり、クラスターのサポート日付を確認するものではありません。
EKS コントロールプレーンは、中間バージョンをスキップせずに一度に 1 マイナーバージョン進めます。
現在サポートされているバージョンでは、kubelet は API サーバーより新しくできず、Upstream ポリシーはその条件下で
最大 3 マイナー古いバージョンを許容します。これはノードを遅れたままにする推奨ではありません。次のアップグレード前に
ノードを現在のコントロールプレーンに合わせるよう計画し、EKS managed-node、Fargate、self-managed、Hybrid の要件をそれぞれ確認してください。
kubectl はコントロールプレーンから 1 マイナー以内のバージョンを使用してください。

| デプロイメント | 更新責任 |
|---|---|
| Pure Auto Mode | サービス管理のノード、ネットワーキング、ブロックストレージ、LB 機能 |
| 通常/self-managed/Hybrid ノード | ノード、CNI、DNS、proxy、driver、controller の更新を計画 |
| 混在クラスター | 非 Auto ノードに必要なアドオンを維持 |
| アプリ、self-managed controller、EKS アドオン | インストール済みバージョン、設定、CRD を検証 |

Pure Auto Mode は CoreDNS をノードシステムサービスとして使用します。CoreDNS Deployment が存在しないことだけで
障害とはいえません。混在クラスターでは、他のノードに必要な DNS Deployment を保持する必要があります。
Auto Mode で通常ノード用の aws-node/kube-proxy/Pod Identity agent
Pod を無条件にインストールまたは検索しないでください。コントロールプレーンのアップグレード前に互換性対応が必要になることがあるため、
「コントロールプレーン → すべてのアドオン → ノード」は普遍的ではありません。

| API 安定性 | 非推奨化ポリシー |
|---|---|
| GA | 非推奨にすることはできますが、同一 Kubernetes メジャーバージョン内では削除されません |
| Beta | 非推奨化後、少なくとも 9 か月または 3 マイナーのうち長い方を経過してから Serving を削除 |
| Alpha | 事前の非推奨通知なしで削除される可能性があります |

CLI フラグとメトリクスのポリシーは異なります。古い互換性表をコピーするのではなく、
移行ガイド、実際にインストールされているバージョン、アーキテクチャ、platform version、コンピュートタイプを比較してください。

## 2. アップグレード前レビュー

アップグレードインサイトにはタイミングとカバレッジの制限があります。公式アップグレードガイドでは、
特定のアップグレードインサイト問題で `--force` を必須とする要件が一時的に停止されていることが引き続き記されています。
これを、後述のロールバック準備状況で ERROR/UNKNOWN がブロックすることと混同しないでください。
API が受け付けたことは readiness レビューの完了ではありません。

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.4 は、終了コード 0（検出事項なし）、2（非推奨）、3（削除済み）、4（対象バージョンで代替 API を利用できない）を区別します。
ゼロ以外のすべての結果を「未インストール」に変換したり、`|| true` で隠したりしないでください。
JSON はオブジェクトです。`.items // []` を数えてください。正常なレスポンスでは items が省略されることがあります。
`detect-all-in-cluster` も有効です。公式リリースのアーキテクチャとチェックサムを確認してください。

API サーバーがオブジェクトを変換するため、ライブ検出では元の API バージョンを見逃す可能性があります。
Git、レンダリング済み Helm/Kustomize、リリースメタデータ、API 警告/audit、実際のクライアントをレビューしてください。
Pluto の他のコンポーネントターゲットも、デプロイ済みの Istio/cert-manager バージョンに合わせてください。

この読み取り専用ツールは、EKS と kubecontext のエンドポイントを比較してから、Node/Pod の readiness、
Deployment generation/rollout、PDB、実際にインストールされているアドオンを確認します。
proxy kubeconfig は直接の EKS エンドポイントと異なる場合があり、別途レビューが必要です。

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

終了コード 0 は列挙したチェックが収集されたこと、2 は検出事項、1 はエラーによる不明な結果を意味します。
ゼロは自動的なアップグレード承認や完全なアプリケーション健全性の証明ではありません。
提供されているアドオンバージョンにも、アーキテクチャ/platform/コンピュートタイプと設定のレビューが必要です。

maxUnavailable 1 の PDB でも、不健全な Pod や重複する PDB により、許容される中断がゼロになる場合があります。
AlwaysAllow は不健全な Pod の eviction 動作を変更しますが、可用性を保証するものではありません。

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

Node の phase や Pod の Running だけから健全性を推測しないでください。レプリカ数ゼロの Deployment、
完了した Job、空の PDB selector を区別してください。EndpointSlice の ready/serving/terminating 条件と
Service selector を検査してください。selector のない Service/ExternalName Service には通常の Pod endpoint は不要です。

## 3. バックアップとリストアの検証

Managed EKS バックアップは、任意の etcd snapshot から顧客が制御してリストアできることを意味しません。
Git/IaC、Kubernetes オブジェクト、PV データ、外部データベース、権限、暗号化キー、復旧手順を分離してください。
まず Velero BackupStorageLocation、plugin/CSI snapshot 設定、IAM を準備します。この Schedule は production を明示的に選択します。
デフォルトの Backup CLI は `*` namespace を含みます。velero のすべてを自動的に除外するわけではありません。

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

Completed は、アプリケーションの整合性やすべてのボリュームの復旧を証明しません。
エラー/警告、snapshot/data-mover の結果、除外されたボリューム、DB の quiescing/replication をレビューしてください。
PVC/PV オブジェクトだけでは、完全なアプリケーション/Secret/Service/データのバックアップにはなりません。
Filesystem backup には別途 node-agent とボリューム設定が必要です。

Velero 1.18.4 の restore create には `--dry-run` がありません。
`-o yaml/json` は Restore を作成せずに出力しますが、discovery/Backup の読み取りは実行します。
これは完全なオフラインでも、復旧テストでもありません。

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

実際のリストアは隔離されたテスト環境で実行してください。namespace mapping だけでは
CronJob、consumer、外部 DB、DNS/LB の変更は隔離されません。
テストクラスターの backup-storage 書き込み所有権、snapshot の region/AZ、KMS/IAM をレビューしてください。
適切な場合は同期に読み取り専用の BackupStorageLocation を使用してください。
リストア作成、Pod の起動、volume attachment、整合性、アプリケーション動作をそれぞれテストしてください。
テストのクリーンアップ中に元のバックアップを削除しないでください。

## 4. コントロールプレーンとノードの更新

これは [インフラストラクチャの章](./01-infrastructure-setup.md) の既存クラスター層を使用します。
新しい state に重複クラスターを作成したり、VPC/IAM を再構築したりしないでください。
Kubernetes のマイナー変更とは別に、module/provider のメジャー変更をレビューしてください。
古い EKS module v20 の input を現在の module に混在させないでください。
tfvars は実際の絶対ファイルパスに置き換えてください。

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

CLI による変更を選ぶ場合、同じ設定に対する IaC の変更を同時に行わないでください。
次のコマンドは readiness レビュー後に実際の変更を実行します。update ID を記録してください。

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

終了コード 0 は Successful、1 は失敗/キャンセル/クエリエラー、2 はクライアントのタイムアウトを意味します。
タイムアウトで AWS はキャンセルされません。同じ ID の監視を再開してください。
コントロールプレーンのアップグレードは、開始後に任意で pause/stop できません。
cluster-active だけではノード置換の完了を確認できません。
その後、実際のバージョン、ノード、アプリケーションを再確認してください。

Auto Mode はコントロールプレーン更新後にノードを段階的に置き換えます。
顧客は EC2NodeClass al2023@latest を通じて Auto Mode AMI を選択しません。
通常の managed/self-managed/Hybrid ノードと既存の Fargate Pod には別個の対応が必要です。
すべての EKS アドオンが自動更新されるわけではありません。describe-addon-configuration の
バージョンと設定 schema をレビューし、無差別に OVERWRITE を適用しないでください。

### 中断制約

適用可能な NodePool budget は、最も厳しい制約によって組み合わされます。
10% と 1 は「少なくとも 1」を意味しません。丸め、削除中/NotReady ノード、UTC schedule を考慮してください。
schedule 済みの budget だけでは、その有効ウィンドウ外の中断は禁止されません。

任意の drift を pause するには、既存の budget を保持/レビューし、
`nodes: "0", reasons: [Drifted]` などのポリシーを追加してから、元のポリシーに戻します。
NodePool metadata の do-not-disrupt annotation は、その pause メカニズムではありません。
Node/Pod annotation と budget は、すべての interruption、expiry、termination-grace 経路を防止するものではありません。

| 手動 drain オプション | 意味 |
|---|---|
| `--ignore-daemonsets` | DaemonSet Pod を削除せずに除外 |
| `--delete-emptydir-data` | emptyDir データの損失を許可 |
| `--disable-eviction` | Eviction を使わずに削除し、PDB 保護をバイパス |

DaemonSet は適格なノードで実行されます。一般的な対処として force-deletion/PDB バイパスを自動化しないでください。

## 5. Native Kubernetes バージョンロールバック

EKS は、アップグレード完了から 7 日以内であれば、直前のマイナーバージョンへのロールバック開始をサポートします。
「コントロールプレーンは決してロールバックできない」はもはや正しくありません。
制約には、現在のバージョンで作成されたクラスター、期限切れのウィンドウ、延長サポート終了時の自動アップグレード、
ターゲットと互換性のない EKS 機能が含まれます。連続アップグレード後に対象となるのは直前のマイナーだけです。
延長サポートのターゲットには、対応するポリシーとコスト条件が必要です。

| コンポーネント | 処理 |
|---|---|
| API サーバー／コントロールプレーン | 前の Kubernetes マイナーとその最新 platform version |
| Auto Mode ノード | サービスが最初にノードを調整し、その後コントロールプレーンをロールバック |
| 通常の managed node group | 利用者が最初に UpdateNodegroupVersion で調整 |
| Self-managed/Hybrid ノード | 利用者が最初に互換性のあるノードで置換 |
| Fargate | 既存 Pod kubelet の直接ダウングレードはなし。別個の置換/互換性を計画 |
| アドオン、アプリ、etcd オブジェクト、PV データ | 履歴 snapshot からはリストアされない |

これはデータリストアや即時のトラフィックフェイルバックではありません。
新しい API/field、controller、DB schema と前のバージョンとの互換性を検証してください。

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

テストした CLI 2.36.44 は rollback-config をサポートしていますが、環境の古い 2.35.11 はサポートしていませんでした。
古い CLI の不明なオプションと EKS 機能の不在を混同しないでください。
公式の更新済み CLI またはサポート対象の API/SDK を使用してください。個別の aws eks rollback-cluster コマンドはありません。

ロールバック readiness の ERROR/UNKNOWN は操作をブロックします。WARNING は助言です。
force は insight チェックをバイパスできますが、適格性や Auto Mode の中断制御はバイパスできません。
ベースラインでは force を使用しません。

### Auto Mode の監視とキャンセル

ノードロールバック中、コントロールプレーンは新しいバージョンを引き続き提供し、クラスター status は
ACTIVE のままです。ノードがターゲットの skew 要件を満たすと EKS が insight を再確認し、その後 CP をロールバックします。
update ID を監視してください。Node の timeout はデフォルトで 720 分で、範囲は 120–10,080 分です。
これは最小境界であり、正確なタイマーではありません。7 日間の開始ウィンドウと、すでに開始済みのノードフェーズの
タイムアウトを区別してください。timeout 時、CP は現在のバージョンのまま、ノードはその方向へ drift し戻り、
update は Failed になります。

ゼロの Drift budget や node do-not-disrupt は進行をブロックする場合があります。PDB/Pod annotation は
TerminationGracePeriod まで中断を遅延させることができますが、恒久的に防止することはできません。
個々の中断がすでに進行中の場合は完了することがありますが、ノードフェーズ中はベストエフォートの
キャンセルが可能です。CP のロールバック開始後はキャンセルできません。

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

キャンセル後、ノードは現在の CP バージョンへ drift します。
IaC timeout は AWS 操作を停止せず、CloudFormation stack rollback は自動的な
Kubernetes バージョンロールバックではありません。CLI/API 変更後に実際と意図した IaC バージョンを照合してください。

## 6. ブルー/グリーン

Green には別個の state/identity を使用し、共有 DNS/NLB/database の所有権は Blue の
削除スコープ外に保ちます。実際の endpoint/CA、workload identity、assume-role、EKS access entry、
Kubernetes RBAC について、[マルチクラスター GitOps](./04-gitops-multi-cluster.md) の手順を通じて登録してください。
cluster Secret は Green ではなく Hub context に適用してください。

この ApplicationSet は自動 sync なしで Green のみを選択します。
production の AppProject/namespace、repository、承認済み revision を準備してください。
URL/SHA の placeholder を置き換え、worker、consumer、CronJob の同時アクティブ化を制御してください。
preserveResourcesOnDeletion は、selector の変更により生成された Application が削除される場合に workload を保護します。
Preservation は管理の引き渡しではありません。color/selector を変更する前に、定常状態の GitOps 所有権を計画してください。

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

Git revision をロールバックするには、承認済みの Git state を復元して sync します。
argocd app rollback は SHA ではなく deployment history ID を受け取ります。
そうしないと、自動 sync/ApplicationSet の desired state によって再び変更されることがあります。

### Green を直接テストする

実行中の Pod と TCP 接続は、DB/message/readiness の動作を証明しません。
Green への直接パスを使用し、Service hostname の SNI/Host と certificate validation を保持してください。
NLB の AWS hostname はアプリケーションの TLS hostname ではありません。
実際に 443 で HTTPS を提供する Service の場合は、別の terminal を使用してください。

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

別の terminal で、実際の hostname、path、response contract を使用します。

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### NLB weight

NLB の weighted target group はサポートされています。相対 weight は 0–999 の範囲で、合計を 100 にする必要はありません。
これは新規接続の予想シェアを表すものであり、正確なリクエスト、bytes、既存 session を表すものではありません。
クラスターごとに別々の TG に正常な target を登録してください。
TGB、target type、network/security group については [高度なインフラストラクチャ](./02-infrastructure-advanced.md) を参照してください。

通常の weight 変更は新規接続に影響しますが、weight をゼロにすると短時間後に既存の
接続を閉じる場合があります。これは中断のない drain ではありません。lifetime、retry、session をテストしてください。
TCP/UDP/TCP_UDP は target-group stickiness をサポートしますが、TLS listener はサポートしません。
TCP forward stickiness は ALB 専用機能ではありません。
API は ALB の DurationSeconds を文書化しています。NLB にこの期間保証をコピーしないでください。

このツールは JSON のみを生成します。実際の listener protocol と target-group VPC、
protocol/IP family、health、既存の stickiness を最初に検証してください。

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

最初に 3 つの ARN 変数を設定してください。タイマーだけに基づいて比率を進めないでください。
各段階で SLO、新規/既存接続、エラー、session を監視してください。
別の TG への failover を想定するのではなく、ゼロ weight、不健全な target、cross-zone 動作をテストしてください。
共有 NLB の背後で Green を検証する際は、別個の直接 Service パスを使用してください。

### データとクリーンアップ

外部 RDS/ElastiCache または共有 EFS があっても、schema、権限、cache-format、
concurrent writer/consumer の移行作業は不要になりません。共有 filesystem や単一の SQL count では
整合性を確立できません。最後の書き込み以降の snapshot region/AZ、storage class、KMS、RPO を確認してください。

合意した監視/復旧期間とデータ互換性の検証が終わるまで Blue を保持してください。
ゼロ weight の TG も listener に参照されている場合があります。
Auto Mode の TGB/cluster 削除は、関連 TG のライフサイクルに影響します。共有 listener から Blue TG の参照を
削除してから、クリーンアップ前に所有権、IaC、削除順序をレビューしてください。
これを self-managed LB Controller の external-TG 所有権と区別してください。
トラフィック移行直後に自動で terraform destroy しないでください。

worker がすでに AZ 分離されたクラスターで実行されている場合、クラスターを一度に 1 つずつアップグレードする選択肢があります。
それでも各 EKS コントロールプレーンが single-AZ になるわけではありません。
他のクラスターの予備容量/状態互換性と native rollback の適格性/期間を検証してください。
7 日間のウィンドウは即時の Blue failback を保証しません。

## 7. アップグレード後の検証

update が Successful になった後、実際のバージョン、Node/Pod Ready、controller generation、
DNS/network path、storage、権限、アプリケーション動作、schedule 済みの作業を検証してください。
count はゼロ値の condition/phase sample も数えます。以下のように値を集約し、
欠落した観測を健全なゼロに変換しないでください。複数クラスターでは、収集に実際の cluster label が必要です。

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

Pod restart count は rescheduling count ではありません。Auto Mode controller metric が
self-managed Karpenter Pod から scrape されていると想定しないでください。
以下には実際の service=api label/metric contract が必要です。
トラフィックゼロは健全なゼロ error rate ではありません。total-traffic series が存在し、その rate が正の場合にのみ、
欠落した error series をゼロで補完してください。

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

履歴を比較する際は、numerator、denominator、bucket に同じ offset を使用してください。
[30m] offset 1h は現在の 60–30 分前ではなく、90–60 分前を対象とします。
等価な cohort を比較してください。blue/green は traffic、route、sample count、load が異なる場合があります。
72 時間では完全な週次パターンをカバーしません。workload cycle とロールバック適格性ウィンドウから監視期間を選んでください。

[オブザーバビリティスタックの章](./09-observability-stack.md) 明示的な UID と完全な dashboard provisioning を使用してください。
部分的な panel YAML/JSON を完全にインポート可能な dashboard として提示しないでください。
前後のバージョン、update ID、計画/実際の時刻、障害、復旧結果を記録してください。

このレビューでは、synthetic preflight/wait/routing ケース、公式 CLI parser、Velero の GET-only
出力動作、manifest/query を確認しました。実際の EKS アップグレード/ロールバック、NLB の変更、
snapshot/restore、アプリケーション load test は実行していません。

## 公式リファレンス

- [EKS の更新](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS のロールバック](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Auto Mode のロールバック](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Auto Mode のアップグレード](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [EKS の料金](https://aws.amazon.com/eks/pricing/)
- [Kubernetes のバージョンスキュー](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes のリリース履歴](https://kubernetes.io/releases/)
- [Kubernetes のパッチリリースとサポート期間](https://kubernetes.io/releases/patch-releases/)
- [Kubernetes の非推奨ポリシー](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.4](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.4)
- [Velero 1.18.4](https://github.com/velero-io/velero/releases/tag/v1.18.4)
- [NLB リスナー](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [前へ: リソース最適化](./10-resource-optimization.md) | [目次](./README.md) | [次へ: イベント容量計画](./12-event-capacity-planning.md) >
