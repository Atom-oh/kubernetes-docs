# EKS 升级：Auto Mode、回滚与蓝绿部署

> **最后更新**：October 16, 2026。命令于 September 12, 2026 检查（Pluto 和 Velero 于 October 16, 2026 检查），使用 AWS CLI 2.36.44、Pluto 5.24.4 和 Velero 1.18.4。
> 示例升级路径为 1.35 → 1.36；请确认实际区域可用性。

请一并规划控制平面、节点、附加组件、应用和数据。
仅靠 Auto Mode 和 PDB 无法保证服务不中断。请根据可用性目标，验证备用容量、就绪状态、重新连接行为、会话、状态和恢复能力。

## 1. 版本与管理职责

截至 October 12, 2026，上游 Kubernetes 为最近三个次要版本（1.35–1.37）维护发布分支，
而不是当前版本加上之前的三个版本。每个次要版本大约有 14 个月的补丁支持，其中最后两个月处于维护模式；1.34 将处于
维护模式，直至其生命周期于 October 27, 2026 结束。
EKS 有单独的生命周期：通常提供 14 个月标准
支持和 12 个月延长支持。请确认确切日期、策略和区域可用性。

标准支持期间，EKS 普通基础控制平面费用为 $0.10/小时；延长支持期间的总费用为
$0.60/小时（$0.10 + $0.50）。额外费用不是 $0.60。
Auto Mode、计算、存储、网络以及单独预置的控制平面容量需额外付费。

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

`describe-addon-versions` 检查附加组件兼容性，不检查集群支持日期。
EKS 控制平面每次只能升级一个次要版本，不能跳过中间版本。
对于当前受支持的版本，kubelet 不能比 API server 新；根据上游策略及其条件，最多可比 API server 旧三个次要版本。这并不意味着建议让
节点落后。请规划在下次升级前使节点版本与当前控制平面对齐，
并分别检查 EKS 托管节点、Fargate、自管理节点和 Hybrid 的要求。
使用与控制平面相差不超过一个次要版本的 kubectl。

| Deployment | 更新职责 |
|---|---|
| 纯 Auto Mode | 由服务管理节点、网络、块存储和 LB 功能 |
| 普通/自管理/Hybrid 节点 | 规划节点、CNI、DNS、代理、驱动和控制器更新 |
| 混合集群 | 保留非 Auto 节点所需的附加组件 |
| 应用、自管理控制器和 EKS 附加组件 | 验证已安装的版本、配置和 CRD |

纯 Auto Mode 将 CoreDNS 用作节点系统服务。没有 CoreDNS Deployment 本身
并不代表故障；混合集群必须保留其他节点所需的 DNS Deployment。
不要在 Auto Mode 中无条件安装或查找普通节点的 aws-node/kube-proxy/Pod Identity agent
Pod。兼容性可能要求在控制平面升级前先进行处理，因此
“控制平面 → 每个附加组件 → 节点”并不适用于所有情况。

| API 稳定性 | 弃用策略 |
|---|---|
| GA | 可以弃用，但不能在同一个 Kubernetes 主版本中移除 |
| Beta | 弃用后至少九个月或三个次要版本（以较长者为准）才会停止提供服务 |
| Alpha | 可以在不事先发出弃用通知的情况下移除 |

CLI 标志和指标采用不同的策略。请对照迁移指南以及实际安装的版本、
架构、平台版本和计算类型，而不要照搬旧的兼容性表。

## 2. 升级前审查

升级洞察有时间和覆盖范围方面的限制。官方升级指南仍指出，
某些升级洞察问题暂时不再要求使用 `--force`。
请将此情况与下文阻止操作的回滚就绪状态 ERROR/UNKNOWN 区分开来。
API 接受请求并不代表已完成就绪状态审查。

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.4 区分退出码 0（无问题）、2（已弃用）、3（已移除）和 4（目标版本中没有可用的替代 API）。
不要将所有非零结果都解释为“未安装”，也不要用 `|| true` 隐藏结果。
其 JSON 是一个对象：统计 `.items // []`；干净的响应可能不包含 items。
`detect-all-in-cluster` 也有效。请检查官方发布版本的架构和校验和。

实时发现可能无法识别原始 API 版本，因为 API server 会转换对象。
请检查 Git、渲染后的 Helm/Kustomize、发布元数据、API 警告/审计记录和实际客户端。
也要让 Pluto 的其他组件目标版本与已部署的 Istio/cert-manager 版本匹配。

此只读工具会比较 EKS 和 kubecontext 端点，然后检查 Node/Pod 就绪状态、
Deployment generation/rollout、PDB 和实际安装的附加组件。
代理 kubeconfig 可能与 EKS 直接端点不同，需要单独审查。

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

退出码 0 表示已收集所列检查项，2 表示发现问题，1 表示因错误而结果未知。
零不代表自动获准升级，也不能证明应用完全健康。
已公布的附加组件版本仍需进行架构/平台/计算类型和配置审查。

即使 maxUnavailable 为 1，PDB 仍可能因为 Pod 不健康或 PDB 重叠而允许零次驱逐。
AlwaysAllow 会改变对不健康 Pod 的驱逐行为；但不能保证可用性。

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

不要仅凭 Node phase 或 Pod Running 状态判断健康。请区分零副本 Deployment、
已完成的 Job 和空 PDB selector。检查 EndpointSlice 的 ready/serving/terminating 条件
和 Service selector；无 selector/ExternalName Service 不需要普通 Pod 端点。

## 3. 备份和恢复验证

EKS 托管备份并不意味着客户可以从任意 etcd 快照自行恢复。
请分别处理 Git/IaC、Kubernetes 对象、PV 数据、外部数据库、权限、加密密钥
和恢复流程。先准备 Velero BackupStorageLocation、插件/CSI 快照配置
和 IAM。此 Schedule 明确选择了 production。
默认 Backup CLI 包含 `*` namespace；它不会自动排除所有 velero。

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

显示 Completed 并不能证明应用一致性或每个卷都能恢复。
请检查错误/警告、快照/数据移动器结果、排除的卷以及数据库静默/复制情况。
PVC/PV 对象本身并不是完整的应用/Secret/Service/数据备份。
文件系统备份需要单独配置 node-agent 和卷。

Velero 1.18.4 的 restore create 没有 `--dry-run`。
`-o yaml/json` 会打印 Restore 而不创建它，但仍会执行发现和 Backup 读取操作。
因此它既不是完全离线操作，也不是恢复测试。

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

请在隔离的测试环境中实际执行恢复。仅靠 namespace 映射无法隔离 CronJobs、消费者、
外部数据库或 DNS/LB 变更。
请检查测试集群的备份存储写入所有权、快照区域/AZ 以及 KMS/IAM。
在适当情况下，使用只读 BackupStorageLocation 进行同步。
分别测试恢复创建、Pod 启动、卷挂载、完整性和应用行为。
测试清理时不要删除原始备份。

## 4. 控制平面和节点更新

本节使用[基础设施章节](./01-infrastructure-setup.md)中已有的集群层。
不要在新的 state 中创建重复集群，也不要重建 VPC/IAM。
请单独审查模块/提供程序主版本变更和 Kubernetes 次要版本变更。
不要将旧 EKS module v20 输入混入当前模块。
请将 tfvars 替换为真实的绝对文件路径。

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

如果选择 CLI 变更，请避免对同一设置同时进行 IaC 变更。
下一个命令会在就绪状态审查后实际执行变更。请记录其 update ID。

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
超时不会取消 AWS 操作；请使用同一个 ID 恢复观察。
控制平面升级开始后，不能随意暂停/停止。
仅 cluster-active 并不能证明节点替换已完成。
之后请重新检查实际版本、节点和应用。

控制平面更新后，Auto Mode 会逐步替换节点。
客户不能通过 EC2NodeClass al2023@latest 选择 Auto Mode AMI。
普通托管/自管理/Hybrid 节点和现有 Fargate Pod 需要单独处理。
EKS 附加组件不会全部自动更新。请从 describe-addon-configuration 审查版本和配置 schema；
不要不加区分地应用 OVERWRITE。

### 中断约束

适用的 NodePool budget 会按照限制最严格的约束合并。
10% 和 1 并不意味着“至少一个”。请考虑取整、删除中/NotReady 节点以及 UTC 时间表。
仅设置计划 budget 并不能禁止其生效时间窗口以外的中断。

要暂停自愿 drift，请保留/审查现有 budget，添加类似
`nodes: "0", reasons: [Drifted]` 的策略，然后恢复原策略。
NodePool metadata 上的 do-not-disrupt annotation 不是这种暂停机制。
Node/Pod annotation 和 budget 并不能阻止所有中断、到期或 termination-grace 路径。

| 手动 drain 选项 | 含义 |
|---|---|
| `--ignore-daemonsets` | 排除 DaemonSet Pod，但不删除它们 |
| `--delete-emptydir-data` | 允许丢失 emptyDir 数据 |
| `--disable-eviction` | 不使用 Eviction 而直接删除，从而绕过 PDB 保护 |

DaemonSet 会在符合条件的节点上运行。不要将强制删除/绕过 PDB 自动化用作通用补救措施。

## 5. 原生 Kubernetes 版本回滚

EKS 支持在升级完成后的七天内发起回滚至上一个次要版本。
“控制平面永远不能回滚”这一说法已不再正确。
限制包括：集群是在其当前版本创建的、窗口已过期、延长支持结束时发生自动升级，以及 EKS 功能与目标版本不兼容。
连续升级后，只有紧邻的上一个次要版本符合条件。
回滚到延长支持版本需要满足相应的策略和费用条件。

| 组件 | 处理方式 |
|---|---|
| API server/控制平面 | 上一个 Kubernetes 次要版本及其最新 platform version |
| Auto Mode 节点 | 服务先调整节点，然后回滚控制平面 |
| 普通托管节点组 | 用户先使用 UpdateNodegroupVersion 调整节点组 |
| 自管理/Hybrid 节点 | 用户先替换为兼容节点 |
| Fargate | 不能直接降级现有 Pod 的 kubelet；请单独规划替换/兼容性 |
| 附加组件、应用、etcd 对象和 PV 数据 | 不会从历史快照恢复 |

这不是数据恢复，也不是即时流量切回。
请验证新 API/字段、控制器和数据库 schema 与旧版本的兼容性。

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

经测试的 CLI 2.36.44 支持 rollback-config；环境中的旧版 2.35.11 不支持。
不要将旧 CLI 的未知选项误认为 EKS 不具备该功能。
请使用官方更新后的 CLI 或受支持的 API/SDK。没有单独的 aws eks rollback-cluster 命令。

回滚就绪状态为 ERROR/UNKNOWN 时会阻止操作；WARNING 仅作提示。
Force 可以绕过洞察检查，但不能绕过资格条件或 Auto Mode 中断控制。
基准流程不使用 force。

### Auto Mode 观察与取消

节点回滚期间，控制平面会继续提供较新版本的服务，集群状态保持
ACTIVE。节点满足目标版本偏差要求后，EKS 会重新检查洞察，然后回滚 CP。
请观察 update ID。节点超时默认值为 720 分钟，范围为 120–10,080 分钟。
它是最短界限，不是精确计时器。请区分七天的发起窗口和
已开始的节点阶段超时。超时后，CP 保持当前版本，节点会逐渐回到该版本，更新状态变为 Failed。

零 Drift budget 或节点 do-not-disrupt 可能阻止进度。PDB/Pod annotation 可能延迟中断，
最长可达 TerminationGracePeriod，但无法永久阻止中断。
节点阶段可以尽力取消，不过已开始的单次中断可能仍会完成。
CP 回滚开始后则不能取消。

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

取消后，节点会逐渐回到当前 CP 版本。
IaC 超时不会停止 AWS 操作，CloudFormation stack rollback 也不会自动执行
Kubernetes 版本回滚。CLI/API 变更后，请协调实际版本和 IaC 目标版本。

## 6. 蓝绿部署

为 Green 使用独立的 state/identity，并确保共享 DNS/NLB/数据库的所有权不在 Blue 的
删除范围内。按照[多集群 GitOps](./04-gitops-multi-cluster.md) 流程，为真实端点/CA、
workload identity、assume-role、EKS access entries 和 Kubernetes RBAC 注册。
将集群 Secret 应用到 Hub context，而不是 Green。

此 ApplicationSet 仅选择 Green，且不启用自动同步。
准备 production AppProject/namespace、仓库和已批准的 revision。
替换 URL/SHA 占位符，并控制 workers、消费者和 CronJobs 的并发激活。
如果 selector 变更导致生成的 Application 被移除，preserveResourcesOnDeletion 可保护工作负载。
保留资源并不代表管理权已交接；更改颜色/selector 前，请规划好稳态下的 GitOps 所有权。

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

要回滚 Git revision，请恢复已批准的 Git 状态并进行同步。
argocd app rollback 使用 deployment history ID，而不是 SHA。
否则，自动同步/ApplicationSet 的期望状态可能会再次更改它。

### 直接测试 Green

Pod 正在运行且 TCP 可连通，并不能证明 DB/消息/readiness 行为正常。
请使用直接通往 Green 的路径，并保留服务主机名的 SNI/Host 和证书验证。
NLB 的 AWS 主机名不是应用的 TLS 主机名。
对于确实在 443 上提供 HTTPS 服务的 Service，请在单独的终端中运行：

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

在另一个终端中使用实际的主机名、路径和响应约定。

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### NLB 权重

NLB 支持加权目标组。相对权重范围为 0–999，无需总和为 100。
它们表示新连接的预期占比，而不是精确的请求数、字节数或现有会话数。
请在每个集群使用单独的 TG 注册健康目标。
有关 TGB、目标类型和网络/安全组，请参阅[高级基础设施](./02-infrastructure-advanced.md)。

普通权重变更会影响新连接，但将权重设为零可能会在短时间后关闭现有连接。
这不等同于不中断排空；请测试连接生命周期、重试和会话。
TCP/UDP/TCP_UDP 支持目标组粘性；TLS listener 不支持。
TCP forward 粘性并非 ALB 独有功能。
API 为 ALB 记录了 DurationSeconds；不要将该时长保证照搬到 NLB。

此工具仅生成 JSON。请先确认实际 listener protocol 和目标组 VPC、
协议/IP family、健康状态及现有粘性设置。

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

请先设置三个 ARN 变量。不要仅凭计时器推进百分比。
每个阶段都要观察 SLO、新/现有连接、错误和会话。
请测试权重为零、目标不健康和跨区行为，不要想当然地认为流量会故障转移到另一个 TG。
通过共享 NLB 验证 Green 时，请使用单独的直接 Service 路径。

### 数据与清理

外部 RDS/ElastiCache 或共享 EFS 并不能免除 schema、权限、缓存格式或
并发 writer/consumer 迁移工作。共享文件系统或单次 SQL 计数不能证明一致性。
请检查快照区域/AZ、存储类、KMS，以及距上次写入以来的 RPO。

在约定的观察/恢复期和数据兼容性验证完成之前，保留 Blue。
权重为零的 TG 仍可能被 listener 引用。
Auto Mode TGB/集群删除会影响相关 TG 的生命周期。请从共享 listener 中移除 Blue TG 引用，
然后在清理前检查所有权、IaC 和删除顺序。
请将此情况与自管理 LB Controller 对外部 TG 的所有权区分开来。
流量切换后不要立即自动运行 terraform destroy。

如果 workers 已在按 AZ 分离的集群中运行，可以选择一次升级一个集群。
但这并不意味着每个 EKS 控制平面都是单 AZ。
请验证其他集群的备用容量/状态兼容性，以及原生回滚的资格条件/时长。
七天窗口并不保证能立即切回 Blue。

## 7. 升级后验证

更新状态为 Successful 后，请验证实际版本、Node/Pod Ready、控制器 generation、
DNS/网络路径、存储、权限、应用行为和计划任务。
count 也会统计值为零的 condition/phase 样本。请按以下方式聚合数值，不要
将缺失的观测数据当作健康的零值。多个集群需要在采集数据时使用实际的集群标签。

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

Pod 重启计数不等于重新调度计数。不要假设 Auto Mode 控制器指标
是从自管理的 Karpenter Pod 抓取的。
以下查询要求有真实的 service=api 标签/指标约定。
零流量并不代表错误率健康为零；只有在总流量 series 存在且其 rate 大于零时，才将缺失的错误 series 补为零。

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

比较历史数据时，分子、分母和 buckets 应使用相同的 offset。
`[30m] offset 1h` 覆盖的是现在之前 90–60 分钟，而不是 60–30 分钟。
请比较相同的样本群体：blue/green 的流量、路由、样本数量和负载可能不同。
七十二小时无法覆盖完整的每周模式。请根据工作负载周期和回滚资格窗口选择观察时长。

使用[技术栈章节](./09-observability-stack.md)中明确的 UID 和完整的仪表板配置。
不要将不完整的面板 YAML/JSON 作为可完整导入的仪表板呈现。
记录升级前/后的版本、update ID、计划/实际时间、故障和恢复结果。

本次审查检查了合成 preflight/wait/routing 用例、官方 CLI 解析器、Velero 仅 GET 输出行为
以及 manifests/queries。未执行真实的 EKS 升级/回滚、NLB 变更、
快照/恢复或应用负载测试。

## 官方参考资料

- [EKS 更新](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Auto Mode 回滚](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Auto Mode 升级](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [EKS 定价](https://aws.amazon.com/eks/pricing/)
- [Kubernetes 版本偏差](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes 发布历史](https://kubernetes.io/releases/)
- [Kubernetes 补丁版本和支持周期](https://kubernetes.io/releases/patch-releases/)
- [Kubernetes 弃用策略](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.4](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.4)
- [Velero 1.18.4](https://github.com/velero-io/velero/releases/tag/v1.18.4)
- [NLB listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [上一章：资源优化](./10-resource-optimization.md) | [目录](./README.md) | [下一章：活动容量规划](./12-event-capacity-planning.md) >
