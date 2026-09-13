# EKS 升级：Auto Mode、回滚和蓝绿部署

> **最后更新**：2026 年 9 月 12 日。命令使用 AWS CLI 2.36.44、Pluto 5.24.3 和 Velero 1.18.2 检查。
> 示例转换为 1.35 → 1.36；请查询实际区域可用性。

将控制平面、节点、插件、应用和数据一并规划。仅 Auto Mode 和 PDB 不保证服务不中断。根据可用性目标验证备用容量、就绪状态、重连行为、会话、状态和恢复。

## 1. 版本和管理职责

上游 Kubernetes 维护最近三个次版本，不是当前版本加之前三个版本。EKS 有独立生命周期：通常标准支持 14 个月、扩展支持 12 个月。检查确切日期、策略和区域可用性。

普通 EKS 基础控制平面费用在标准支持下为 $0.10/小时，扩展支持下总计 $0.60/小时（$0.10 + $0.50）。额外费用不是 $0.60。Auto Mode、计算、存储、网络及单独预置的控制平面容量另行收费。

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

`describe-addon-versions` 检查插件兼容性，不检查集群支持日期。EKS 控制平面每次仅前进一个次版本，不跳过中间版本。对于当前受支持版本，kubelet 不能比 API 服务器新，上游策略在其条件下允许最多落后三个次版本。这不是建议让节点落后。应计划在下一次升级前让节点与当前控制平面对齐，并分别检查 EKS 托管节点、Fargate、自主管理和 Hybrid 要求。kubectl 与控制平面相差应不超过一个次版本。

| 部署 | 更新职责 |
|---|---|
| 纯 Auto Mode | 服务管理的节点、网络、块存储和负载均衡能力 |
| 普通/自主管理/Hybrid 节点 | 规划节点、CNI、DNS、代理、驱动和控制器更新 |
| 混合集群 | 保留非 Auto 节点需要的插件 |
| 应用、自主管理控制器和 EKS 插件 | 验证已安装版本、配置和 CRD |

纯 Auto Mode 将 CoreDNS 作为节点系统服务。仅缺少 CoreDNS Deployment 不代表故障；混合集群必须保留其他节点需要的 DNS Deployment。不要在 Auto Mode 中无条件安装或寻找普通节点的 aws-node/kube-proxy/Pod Identity agent Pod。兼容性可能要求控制平面升级前先做工作，因此“控制平面 → 所有插件 → 节点”不是通用顺序。

| API 稳定性 | 弃用策略 |
|---|---|
| GA | 可弃用，但不能在同一 Kubernetes 主版本内移除 |
| Beta | 弃用后至少九个月或三个次版本（取较长者）才停止提供服务 |
| Alpha | 可不经提前弃用通知直接移除 |

CLI 标志和指标的策略不同。应比较迁移指南及实际已安装版本、架构、平台版本和计算类型，不要复制旧兼容性表。

## 2. 升级前审查

升级洞察存在时间和覆盖限制。官方升级指南仍注明：对某些升级洞察问题，暂时停止要求 `--force`。应与下文回滚就绪 ERROR/UNKNOWN 阻断区分。API 接受请求不代表已完成就绪审查。

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.3 区分退出码 0（无问题）、2（已弃用）和 3（已移除）。不要将所有非零结果变为“未安装”，也不要用 `|| true` 隐藏。其 JSON 是对象：统计 `.items // []`；无问题响应可能省略 items。`detect-all-in-cluster` 也有效。检查官方发布架构和校验和。

在线发现可能漏掉原始 API 版本，因为 API 服务器会转换对象。审核 Git、渲染后的 Helm/Kustomize、发布元数据、API 警告/审计及实际客户端。还要将 Pluto 的其他组件目标与已部署 Istio/cert-manager 版本对齐。

此只读工具比较 EKS 和 kubecontext 端点，再检查 Node/Pod 就绪状态、Deployment generation/滚动发布、PDB 及实际安装的插件。代理 kubeconfig 可能不同于直接 EKS 端点，需要单独审核。

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

退出码 0 表示已收集所列检查，2 表示有发现，1 表示因错误导致结果未知。零不自动批准升级，也不能证明完整应用健康。公布的插件版本仍需审核架构/平台/计算类型和配置。

maxUnavailable 为 1 的 PDB 仍可能因不健康 Pod 或重叠 PDB 而允许零次中断。AlwaysAllow 改变不健康 Pod 驱逐行为；不保证可用性。

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

不要仅凭 Node 阶段或 Pod Running 推断健康。区分零副本 Deployment、已完成 Job 和空 PDB 选择器。检查 EndpointSlice 的 ready/serving/terminating 条件及 Service 选择器；无选择器/ExternalName Service 不需要普通 Pod 端点。

## 3. 备份和恢复验证

托管 EKS 备份不意味着客户可控制从任意 etcd 快照恢复。分开处理 Git/IaC、Kubernetes 对象、PV 数据、外部数据库、权限、加密密钥和恢复流程。先准备 Velero BackupStorageLocation、插件/CSI 快照配置和 IAM。此 Schedule 显式选择 production。默认 Backup CLI 包含 `*` 命名空间；不会自动排除整个 velero。

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

Completed 不能证明应用一致性或每个卷都可恢复。审核错误/警告、快照/数据移动器结果、排除卷和数据库静默/复制。仅 PVC/PV 对象不是完整的应用/Secret/Service/数据备份。文件系统备份需要独立节点代理和卷配置。

Velero 1.18.2 restore create 没有 `--dry-run`。`-o yaml/json` 打印 Restore 而不创建它，但会执行发现/Backup 读取。它既不完全离线，也不是恢复测试。

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

在隔离测试环境执行实际恢复。仅命名空间映射不会隔离 CronJob、消费者、外部数据库或 DNS/负载均衡器更改。审核测试集群的备份存储写入所有权、快照区域/可用区和 KMS/IAM。适当时使用只读 BackupStorageLocation 进行同步。分别测试恢复创建、Pod 启动、卷附加、完整性和应用行为。测试清理时不要删除原始备份。

## 4. 控制平面和节点更新

此处使用[基础设施章节](./01-infrastructure-setup.md)中的现有集群层。不要在新状态中创建重复集群或重建 VPC/IAM。将模块/提供程序主版本更改与 Kubernetes 次版本更改分开审核。不要将旧 EKS 模块 v20 输入混入当前模块。将 tfvars 替换为真实绝对文件路径。

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

若选择 CLI 更改，避免并发 IaC 更改同一设置。下一条命令在就绪审查后执行真实更改。记录更新 ID。

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

退出码 0 表示 Successful，1 表示失败/取消/查询错误，2 表示客户端超时。超时不会取消 AWS 操作；继续观察同一 ID。控制平面升级开始后，不能任意暂停/停止。仅 cluster-active 不能证明节点替换完成。之后重新检查实际版本、节点和应用。

Auto Mode 在控制平面更新后逐步替换节点。客户不通过 EC2NodeClass al2023@latest 选择 Auto Mode AMI。普通托管/自主管理/Hybrid 节点及现有 Fargate Pod 需要单独处理。并非所有 EKS 插件都会自动更新。审核 describe-addon-configuration 提供的版本和配置模式；不要无差别应用 OVERWRITE。

### 中断约束

适用的 NodePool 预算按最严格约束组合。10% 和 1 不意味着“至少一个”。考虑取整、正在删除/NotReady 节点和 UTC 时间计划。仅计划预算不会禁止其活动窗口外的中断。

要暂停自愿漂移，保留/审核现有预算，添加 `nodes: "0", reasons: [Drifted]` 等策略，再恢复原策略。NodePool 元数据上的 do-not-disrupt 注解不是该暂停机制。Node/Pod 注解和预算不能防止每次中断、到期或终止宽限路径。

| 手动排空选项 | 含义 |
|---|---|
| `--ignore-daemonsets` | 排除 DaemonSet Pod，不删除它们 |
| `--delete-emptydir-data` | 允许丢失 emptyDir 数据 |
| `--disable-eviction` | 直接删除而不使用 Eviction，绕过 PDB 保护 |

DaemonSet 在符合条件的节点运行。不要将自动强制删除/绕过 PDB 作为通用补救。

## 5. 原生 Kubernetes 版本回滚

EKS 支持在升级完成后七天内发起回滚到前一个次版本。“控制平面永远不能回滚”已不正确。限制包括：集群创建时即为当前版本、窗口过期、扩展支持结束时自动升级，以及 EKS 功能与目标不兼容。连续升级后仅紧邻的前一个次版本符合条件。扩展支持目标需要相应策略和成本条件。

| 组件 | 处理方式 |
|---|---|
| API 服务器/控制平面 | 前一个 Kubernetes 次版本及其最新平台版本 |
| Auto Mode 节点 | 服务先调整节点，再回滚控制平面 |
| 普通托管节点组 | 用户先通过 UpdateNodegroupVersion 调整 |
| 自主管理/Hybrid 节点 | 用户先用兼容节点替换 |
| Fargate | 不直接降级现有 Pod kubelet；规划独立替换/兼容性 |
| 插件、应用、etcd 对象和 PV 数据 | 不从历史快照恢复 |

这不是数据恢复或即时流量切回。验证新 API/字段、控制器和数据库模式与前一版本的兼容性。

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

已测试 CLI 2.36.44 支持 rollback-config；环境中较旧的 2.35.11 不支持。不要将旧 CLI 的未知选项与 EKS 缺少此能力混淆。使用官方更新版 CLI 或受支持 API/SDK。不存在独立 aws eks rollback-cluster 命令。

回滚就绪 ERROR/UNKNOWN 阻止操作；WARNING 仅提供建议。Force 可绕过洞察检查，但不能绕过资格或 Auto Mode 中断控制。基线不使用 force。

### Auto Mode 观察和取消

节点回滚期间，控制平面继续提供较新版本服务，集群状态保持 ACTIVE。节点满足目标版本偏差要求后，EKS 重新检查洞察，再回滚控制平面。观察更新 ID。节点超时默认 720 分钟，范围为 120–10,080 分钟。它是最小界限，不是精确定时器。区分七天发起窗口与已开始节点阶段的超时。超时后，控制平面保持当前版本，节点向该版本漂移回去，更新变为 Failed。

零 Drift 预算或节点 do-not-disrupt 可阻止进展。PDB/Pod 注解可将中断延迟到 TerminationGracePeriod，但不能永久阻止。节点阶段可尽力取消，但已进行中的单个中断可能完成。控制平面回滚开始后不能取消。

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

取消后，节点向当前控制平面版本漂移。IaC 超时不会停止 AWS 操作，CloudFormation 堆栈回滚也不是自动 Kubernetes 版本回滚。CLI/API 更改后，协调实际与预期 IaC 版本。

## 6. 蓝绿部署

为 Green 使用独立状态/身份，并将共享 DNS/NLB/数据库所有权置于 Blue 删除范围之外。按照[多集群 GitOps](./04-gitops-multi-cluster.md)流程注册真实端点/CA、工作负载身份、IAM 角色代入、EKS 访问条目和 Kubernetes RBAC。将集群 Secret 应用到 Hub 上下文，而非 Green。

此 ApplicationSet 仅选择 Green，不启用自动同步。准备生产 AppProject/命名空间、仓库和获准修订。替换 URL/SHA 占位符，并控制工作进程、消费者和 CronJob 的并发激活。若选择器更改移除生成的 Application，preserveResourcesOnDeletion 保护工作负载。保留不是管理权移交；更改颜色/选择器前规划稳态 GitOps 所有权。

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

回滚 Git 修订时，恢复获准 Git 状态并同步。argocd app rollback 接受部署历史 ID，不是 SHA。否则自动同步/ApplicationSet 期望状态可能再次改变它。

### 直接测试 Green

Pod 运行和 TCP 连通不能证明数据库/消息/就绪行为。使用直接 Green 路径，并保留服务主机名的 SNI/Host 及证书验证。NLB 的 AWS 主机名不是应用 TLS 主机名。对于实际在 443 提供 HTTPS 的 Service，使用独立终端：

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

在另一终端使用实际主机名、路径和响应约定。

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### NLB 权重

NLB 支持加权目标组。相对权重范围为 0–999，不必总和为 100。它们表示新连接的预期份额，不是精确请求数、字节数或现有会话份额。为每个集群在独立目标组中注册健康目标。TGB、目标类型及网络/安全组参阅[高级基础设施](./02-infrastructure-advanced.md)。

普通权重更改影响新连接，但权重设零可能在短时间后关闭现有连接。这不是不中断的排空；应测试连接寿命、重试和会话。TCP/UDP/TCP_UDP 支持目标组粘性；TLS 监听器不支持。TCP 转发粘性不是 ALB 专属功能。API 对 ALB 记录了 DurationSeconds；不要将该持续时间保证复制到 NLB。

此工具仅生成 JSON。先验证实际监听器协议及目标组 VPC、协议/IP 地址族、健康状况和现有粘性。

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

先设置三个 ARN 变量。不要仅按定时器推进百分比。每阶段观察 SLO、新/现有连接、错误和会话。测试零权重、不健康目标和跨可用区行为，不要假定会故障转移到其他目标组。验证共享 NLB 后的 Green 时，使用独立直接 Service 路径。

### 数据和清理

外部 RDS/ElastiCache 或共享 EFS 不会免除模式、权限、缓存格式或并发写入方/消费者迁移工作。共享文件系统或一次 SQL count 不能证明一致性。检查快照区域/可用区、存储类、KMS 和自最后写入以来的 RPO。

在约定观察/恢复期及数据兼容性验证期间保留 Blue。零权重目标组仍可被监听器引用。Auto Mode TGB/集群删除影响关联目标组生命周期。先从共享监听器移除 Blue 目标组引用，再审核所有权、IaC 和删除顺序后清理。应与自主管理 LB Controller 的外部目标组所有权区分。切换流量后不要立即自动 terraform destroy。

若工作进程已在按可用区分离的集群中运行，可选择逐个集群升级。这不会使每个 EKS 控制平面变为单可用区。验证其他集群备用容量/状态兼容性及原生回滚资格/时长。七天窗口不保证可即时切回 Blue。

## 7. 升级后验证

更新 Successful 后，验证实际版本、Node/Pod Ready、控制器 generation、DNS/网络路径、存储、权限、应用行为和计划任务。count 也统计值为零的条件/阶段样本。按下方聚合值，不要将缺失观测变为健康的零值。多集群需要采集中的实际集群标签。

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

Pod 重启次数不是重新调度次数。不要假定 Auto Mode 控制器指标从自主管理 Karpenter Pod 抓取。以下需要真实 service=api 标签/指标约定。零流量不是健康的零错误率；仅当总流量序列存在且速率为正时，才将缺失错误序列填零。

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

比较历史时，对分子、分母和桶使用相同 offset。[30m] offset 1h 覆盖距今 90–60 分钟，不是 60–30 分钟。比较等效群体：Blue/Green 的流量、路由、样本数和负载可能不同。七十二小时不覆盖完整每周模式。根据工作负载周期及回滚资格窗口选择观察时长。

使用[技术栈章节](./09-observability-stack.md)的显式 UID 和完整仪表板预置。不要将部分面板 YAML/JSON 作为完整可导入仪表板。记录前后版本、更新 ID、计划/实际时间、失败和恢复结果。

本次审查检查了合成预检/等待/路由用例、官方 CLI 解析器、Velero 仅 GET 输出行为及清单/查询。未执行真实 EKS 升级/回滚、NLB 更改、快照/恢复或应用负载测试。

## 官方参考资料

- [EKS 更新](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Auto Mode 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Auto Mode 升级](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [EKS 定价](https://aws.amazon.com/eks/pricing/)
- [Kubernetes 版本偏差](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes 弃用策略](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.3](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.3)
- [Velero 1.18.2](https://github.com/velero-io/velero/releases/tag/v1.18.2)
- [NLB 监听器](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [上一篇：资源优化](./10-resource-optimization.md) | [目录](./README.md) | [下一篇：活动容量规划](./12-event-capacity-planning.md) >
