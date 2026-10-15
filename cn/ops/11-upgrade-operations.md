# EKS 升级：Auto Mode、回滚和蓝绿部署

> **最后更新**：2026 年 10 月 12 日。命令于 2026 年 9 月 12 日使用 AWS CLI 2.36.44、Pluto 5.24.3 和 Velero 1.18.2 验证。
> 示例迁移为 1.35 → 1.36；请发现实际的区域可用性。

统筹规划控制平面、节点、附加组件、应用程序和数据。
仅有 Auto Mode 和 PDB 并不能保证服务不中断。请根据可用性目标验证备用容量、
就绪状态、重连行为、会话、状态和恢复。

## 1. 版本和管理职责

上游 Kubernetes 为最近三个次要版本维护发布分支
（截至 2026 年 10 月 12 日为 1.35–1.37），而不是当前版本加前三个旧版本。
每个次要版本大约获得 14 个月的补丁，最后两个月处于维护模式；1.34 将在
2026 年 10 月 27 日生命周期结束前处于维护模式。
EKS 有独立的生命周期：通常为 14 个月标准支持和
12 个月扩展支持。请检查准确日期、策略和区域可用性。

普通 EKS 基础控制平面费用在标准支持期内为 $0.10/小时，在扩展支持期内总计为
$0.60/小时（$0.10 + $0.50）。附加费用不是 $0.60。
Auto Mode、计算、存储、网络和单独预置的控制平面容量需额外付费。

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

`describe-addon-versions` 检查附加组件兼容性，而非集群支持日期。
每次将 EKS 控制平面升级一个次要版本，不要跳过中间版本。对于当前支持的版本，
kubelet 不能比 API server 更新，上游策略在其条件下允许最多相差三个较旧的次要版本。
这并不是建议让节点落后。请在下一次升级前规划使节点与当前控制平面对齐，
并分别检查 EKS 托管节点、Fargate、自管和 Hybrid 的要求。
在控制平面的一个次要版本范围内使用 kubectl。

| 部署 | 更新职责 |
|---|---|
| 纯 Auto Mode | 由服务管理节点、网络、块存储和 LB 功能 |
| 普通/自管/Hybrid 节点 | 规划节点、CNI、DNS、代理、驱动程序和控制器更新 |
| 混合集群 | 保留非 Auto 节点所需的附加组件 |
| 应用程序、自管控制器和 EKS 附加组件 | 验证已安装的版本、配置和 CRD |

纯 Auto Mode 将 CoreDNS 用作节点系统服务。仅仅缺少 CoreDNS Deployment
并不表示失败；混合集群必须保留其他节点所需的 DNS Deployment。
不要在 Auto Mode 中无条件安装或查找普通节点的 aws-node/kube-proxy/Pod Identity agent
Pod。兼容性可能要求在控制平面升级前完成工作，因此
“控制平面 → 每个附加组件 → 节点”并不通用。

| API 稳定性 | 弃用策略 |
|---|---|
| GA | 可以弃用，但不会在同一个 Kubernetes 主版本中移除 |
| Beta | 弃用后至少九个月或三个次要版本（以较长者为准）才会停止提供 |
| Alpha | 可以在不事先发出弃用通知的情况下移除 |

CLI 标志和指标策略有所不同。请比较迁移指南和实际安装的版本、
架构、平台版本和计算类型，而不要复制旧的兼容性表。

## 2. 升级前审查

升级洞察存在时效性和覆盖范围限制。官方升级指南仍指出，
针对某些升级洞察问题暂时暂停要求使用 `--force`。
请将此与下面阻止回滚就绪性的 ERROR/UNKNOWN 区分开来。
API 接受并不代表就绪审查已经完成。

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.3 区分退出码 0（干净）、2（已弃用）和 3（已移除）。
不要将每个非零结果都视为“未安装”，也不要用 `|| true` 隐藏它。
其 JSON 是一个对象：计数 `.items // []`；干净的响应可能省略 items。
`detect-all-in-cluster` 同样有效。请检查官方发布架构和校验和。

实时发现可能遗漏原始 API 版本，因为 API server 会转换对象。
请审查 Git、渲染后的 Helm/Kustomize、发布元数据、API 警告/审计和实际客户端。
也请使 Pluto 的其他组件目标与已部署的 Istio/cert-manager 版本对齐。

此只读工具会比较 EKS 和 kubecontext 端点，然后检查 Node/Pod 就绪状态、
Deployment generation/rollout、PDB 以及实际安装的附加组件。
代理 kubeconfig 可能与直接 EKS 端点不同，需要单独审查。

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

退出码 0 表示已收集列出的检查项，2 表示有发现，1 表示因错误而得出未知结果。
零并不自动批准升级，也不证明完整的应用程序运行状况。
公布的附加组件版本仍需进行架构/平台/计算类型和配置审查。

maxUnavailable 为 1 的 PDB 仍可能由于不健康 Pod 或重叠 PDB 而允许零次中断。
AlwaysAllow 会改变不健康 Pod 的驱逐行为；它不保证可用性。

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

不要仅从 Node phase 或 Pod Running 推断健康状态。请区分零副本 Deployment、
已完成的 Job 和空的 PDB selector。检查 EndpointSlice ready/serving/terminating 条件
以及 Service selector；无 selector/ExternalName Service 不需要普通 Pod endpoint。

## 3. 备份和恢复验证

托管 EKS 备份并不意味着客户可从任意 etcd 快照控制恢复。
请区分 Git/IaC、Kubernetes 对象、PV 数据、外部数据库、权限、加密密钥
和恢复过程。首先准备 Velero BackupStorageLocation、plugin/CSI 快照配置
和 IAM。此 Schedule 明确选择 production。
默认 Backup CLI 包括 `*` namespace；它不会自动排除所有 velero 内容。

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

Completed 并不证明应用程序一致性或每个卷都可以恢复。
审查错误/警告、snapshot/data-mover 结果、排除的卷和 DB 静默/复制。
仅有 PVC/PV 对象不是完整的应用程序/Secret/Service/数据备份。
文件系统备份需要单独的 node-agent 和卷配置。

Velero 1.18.2 restore create 没有 `--dry-run`。
`-o yaml/json` 会打印 Restore 而不创建它，但会执行发现/Backup 读取。
它既非完全离线，也不是恢复测试。

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

在隔离的测试环境中执行实际恢复。仅 namespace 映射并不能
隔离 CronJob、消费者、外部 DB 或 DNS/LB 更改。
审查测试集群的备份存储写入所有权、快照区域/AZ 和 KMS/IAM。
在适当时使用只读 BackupStorageLocation 进行同步。
分别测试恢复创建、Pod 启动、卷挂载、完整性和应用程序行为。
测试清理期间不要删除原始备份。

## 4. 控制平面和节点更新

这里使用[基础设施章节](./01-infrastructure-setup.md)中的现有集群层。
不要在新 state 中创建重复集群或重建 VPC/IAM。
将模块/provider 主版本变更与 Kubernetes 次要版本变更分开审查。
不要将旧的 EKS module v20 输入混入当前模块。
将 tfvars 替换为真实的绝对文件路径。

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

如果选择 CLI 更改，请避免同时对相同设置进行 IaC 更改。
下一条命令会在就绪审查后执行真实更改。请记录其更新 ID。

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

退出码 0 表示 Successful，1 表示失败/取消/查询错误，2 表示客户端超时。
超时不会取消 AWS；请继续观察相同的 ID。
控制平面升级一旦开始就不能随意暂停/停止。
仅 cluster-active 并不能确定节点替换已经完成。
随后重新检查实际版本、节点和应用程序。

Auto Mode 会在控制平面更新后增量替换节点。
客户不会通过 EC2NodeClass al2023@latest 选择 Auto Mode AMI。
普通托管/自管/Hybrid 节点和现有 Fargate Pod 需要单独处理。
并非所有 EKS 附加组件都会自动更新。请从 describe-addon-configuration 审查版本和配置 schema；
不要不加区分地应用 OVERWRITE。

### 中断约束

适用的 NodePool budget 会通过最严格的约束组合。
10% 和 1 并不表示“至少一个”。请考虑取整、正在删除/NotReady 的节点和 UTC schedule。
单独的计划 budget 不会禁止其活动窗口以外的中断。

要暂停自愿 drift，请保留/审查现有 budget，添加类似
`nodes: "0", reasons: [Drifted]` 的策略，然后恢复原始策略。
NodePool metadata 上的 do-not-disrupt annotation 不是该暂停机制。
Node/Pod annotation 和 budget 不能防止每一种中断、到期或 termination-grace 路径。

| 手动 drain 选项 | 含义 |
|---|---|
| `--ignore-daemonsets` | 排除 DaemonSet Pod 而不删除它们 |
| `--delete-emptydir-data` | 允许 emptyDir 数据丢失 |
| `--disable-eviction` | 删除而非使用 Eviction，从而绕过 PDB 保护 |

DaemonSet 在符合条件的节点上运行。不要将强制删除/绕过 PDB 自动化为通用补救措施。

## 5. 原生 Kubernetes 版本回滚

EKS 支持在升级完成后七天内启动回滚到前一个次要版本。
“控制平面永远不能回滚”已不再正确。
限制包括在当前版本创建的集群、过期窗口、扩展支持结束时的自动升级
以及与目标不兼容的 EKS 功能。
连续升级后，只有紧邻的前一个次要版本符合条件。
扩展支持目标需要相应的策略和费用条件。

| 组件 | 处理方式 |
|---|---|
| API server/control plane | 前一个 Kubernetes 次要版本及其最新平台版本 |
| Auto Mode 节点 | 服务先调整节点，然后回滚控制平面 |
| 普通托管节点组 | 用户先使用 UpdateNodegroupVersion 调整它们 |
| 自管/Hybrid 节点 | 用户先以兼容节点替换它们 |
| Fargate | 现有 Pod kubelet 无法直接降级；请规划单独的替换/兼容性 |
| 附加组件、应用程序、etcd 对象和 PV 数据 | 不从历史快照恢复 |

这不是数据恢复或即时流量故障回退。
请验证新 API/字段、控制器和 DB schema 与前一版本的兼容性。

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

已测试的 CLI 2.36.44 支持 rollback-config；环境中较旧的 2.35.11 不支持。
不要将旧 CLI 的未知选项误认为 EKS 功能不存在。
请使用官方更新的 CLI 或受支持的 API/SDK。不存在单独的 aws eks rollback-cluster 命令。

回滚就绪性 ERROR/UNKNOWN 会阻止该操作；WARNING 仅作提示。
Force 可以绕过洞察检查，但不能绕过资格或 Auto Mode 中断控制。
基线不使用 force。

### Auto Mode 观察和取消

在节点回滚期间，控制平面继续提供较新版本，集群状态保持
ACTIVE。EKS 在节点满足目标版本偏差要求后重新检查洞察，然后回滚 CP。
观察更新 ID。节点超时默认值为 720 分钟，范围为 120–10,080 分钟。
这是最小界限，不是精确计时器。请区分七天启动窗口与
已开始节点阶段的超时。超时时，CP 保持当前版本，节点向它 drift
回去，更新变为 Failed。

零 Drift budget 或节点 do-not-disrupt 可以阻止进度。PDB/Pod annotation 可以将
中断延迟至 TerminationGracePeriod，但无法永久阻止它。
节点阶段中可进行尽力取消，尽管已经开始的个别中断
可能会完成。CP 回滚开始后无法取消。

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

取消后，节点会向当前 CP 版本 drift。
IaC 超时不会停止 AWS 操作，CloudFormation stack rollback 也不是自动
Kubernetes 版本回滚。CLI/API 更改后请协调实际和预期的 IaC 版本。

## 6. 蓝绿部署

为 Green 使用不同的 state/identity，并将共享 DNS/NLB/database 所有权置于 Blue 的
删除范围之外。请通过[多集群 GitOps](./04-gitops-multi-cluster.md)流程注册
真实 endpoint/CA、workload identity、assume-role、EKS access entry 和 Kubernetes RBAC。
将集群 Secret 应用到 Hub context，而不是 Green。

此 ApplicationSet 仅选择 Green，且不使用自动 sync。
准备 production AppProject/namespace、repository 和已批准的 revision。
替换 URL/SHA 占位符，并控制 worker、consumer 和 CronJob 的并发激活。
preserveResourcesOnDeletion 会在 selector 更改移除生成的 Application 时保护工作负载。
保留不等于管理移交；请在更改颜色/selector 前规划稳定状态 GitOps 所有权。

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

要回滚 Git revision，请恢复已批准的 Git state 并同步。
argocd app rollback 接受 deployment history ID，而不是 SHA。
否则自动 sync/ApplicationSet desired state 可能再次更改它。

### 直接测试 Green

运行中的 Pod 和 TCP 连通性并不能证明 DB/message/readiness 行为。
使用直接 Green 路径，并保留服务 hostname 的 SNI/Host 和证书验证。
NLB 的 AWS hostname 不是应用程序 TLS hostname。
对于实际在 443 上提供 HTTPS 的 Service，请使用单独的终端：

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

在另一终端中使用实际 hostname、path 和响应契约。

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### NLB 权重

NLB 支持加权 target group。相对权重范围为 0–999，无需总和为 100。
它们表示新连接的预期份额，而非精确的请求、字节或现有会话。
为每个集群在单独的 TG 中注册健康 target。
有关 TGB、target type 和 network/security group，请参阅[高级基础设施](./02-infrastructure-advanced.md)。

普通权重变更会影响新连接，但将权重设为零可能在短时间后关闭现有
连接。这并不是不中断的排空；请测试生命周期、重试和会话。
TCP/UDP/TCP_UDP 支持 target-group stickiness；TLS listener 不支持。
TCP forward stickiness 并非 ALB 独有功能。
API 为 ALB 记录了 DurationSeconds；不要将该时长保证复制到 NLB。

此工具只生成 JSON。首先验证实际 listener protocol 和 target-group VPC、
protocol/IP family、健康状态和现有 stickiness。

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

首先设置三个 ARN 变量。不要仅按计时器推进百分比。
在每个阶段观察 SLO、新/现有连接、错误和会话。
测试零权重、不健康 target 和 cross-zone 行为，而不要假定故障转移至另一个 TG。
在共享 NLB 后验证 Green 时使用单独的直接 Service 路径。

### 数据和清理

外部 RDS/ElastiCache 或共享 EFS 并不能消除 schema、权限、cache-format 或
并发 writer/consumer 迁移工作。共享文件系统或一个 SQL count 都不能证明
一致性。检查快照区域/AZ、storage class、KMS 以及自最近写入以来的 RPO。

在约定的观察/恢复期和数据兼容性验证期内保留 Blue。
零权重 TG 仍可能被 listener 引用。
Auto Mode TGB/cluster 删除会影响关联 TG 生命周期。先从共享 listener 中移除
Blue TG 引用，然后在清理前审查所有权、IaC 和删除顺序。
请将其与自管 LB Controller 的 external-TG 所有权区分开来。
流量切换后不要立即自动 terraform destroy。

如果 worker 已在按 AZ 分隔的集群中运行，可以选择一次升级一个集群。
这并不使每个 EKS 控制平面成为单 AZ。
验证其他集群的备用容量/状态兼容性以及原生回滚资格/持续时间。
七天窗口不保证即时 Blue 故障回退。

## 7. 升级后验证

更新 Successful 后，验证实际版本、Node/Pod Ready、controller generation、
DNS/network 路径、存储、权限、应用程序行为和计划任务。
count 也会计数零值的 condition/phase 样本。如下聚合值，且不要将
缺失的观测转换为健康的零。多个集群需要在收集中具有实际 cluster label。

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

Pod restart count 并不是重新调度计数。不要假定 Auto Mode controller metric
由自管 Karpenter Pod 抓取。
以下内容需要真实的 service=api label/metric 契约。
零流量不是健康的零错误率；仅在 total-traffic series 存在且其 rate 为正时，
才以零填充缺失的 error series。

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

比较历史记录时，对分子、分母和 bucket 使用相同 offset。
[30m] offset 1h 覆盖的是现在前 90–60 分钟，而非 60–30 分钟。
比较等价 cohort：蓝绿环境可能在流量、路由、样本计数和负载方面不同。
七十二小时无法覆盖完整的每周模式。请依据工作负载周期和回滚资格窗口选择观察持续时间。

使用[stack 章节](./09-observability-stack.md)中的明确 UID 和完整 dashboard provisioning。
不要将部分 panel YAML/JSON 作为完整的可导入 dashboard。
记录前/后版本、更新 ID、计划/实际时间、失败和恢复结果。

本审查检查了合成 preflight/wait/routing 用例、官方 CLI parser、Velero 仅 GET 的
输出行为以及 manifest/query。它未执行真实 EKS 升级/回滚、NLB 更改、
快照/恢复或应用程序负载测试。

## 官方参考资料

- [EKS 更新](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Auto Mode 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Auto Mode 升级](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [EKS 定价](https://aws.amazon.com/eks/pricing/)
- [Kubernetes 版本偏差](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes 发布历史](https://kubernetes.io/releases/)
- [Kubernetes 补丁版本和支持期](https://kubernetes.io/releases/patch-releases/)
- [Kubernetes 弃用策略](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.3](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.3)
- [Velero 1.18.2](https://github.com/velero-io/velero/releases/tag/v1.18.2)
- [NLB listener](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [上一节：资源优化](./10-resource-optimization.md) | [目录](./README.md) | [下一节：事件容量规划](./12-event-capacity-planning.md) >
