# EKS upgrades: Auto Mode, rollback and blue/green

> Reviewed 2026-09-12. Commands checked with AWS CLI 2.36.44, Pluto 5.24.3 and Velero 1.18.2.
> The example transition is 1.35 → 1.36; discover actual regional availability.

Plan the control plane, nodes, add-ons, applications and data together.
Auto Mode and PDBs alone do not guarantee uninterrupted service. Validate spare capacity,
readiness, reconnect behavior, sessions, state and recovery against availability goals.

## 1. Versions and management responsibilities

Upstream Kubernetes maintains the most recent three minor releases, not the current release
plus three previous versions. EKS has a separate lifecycle: generally 14 months of standard
support and 12 months of extended support. Check exact dates, policy and regional availability.

The ordinary EKS base control-plane fee is $0.10/hour under standard support and a total of
$0.60/hour under extended support ($0.10 + $0.50). The additional fee is not $0.60.
Auto Mode, compute, storage, networking and separately provisioned control-plane capacity are additional.

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

`describe-addon-versions` checks add-on compatibility, not cluster support dates.
Advance an EKS control plane by one minor at a time without skipping intermediates.
For current supported versions, kubelet cannot be newer than the API server and upstream policy
allows up to three older minors under its conditions. That is not a recommendation to keep
nodes behind. Plan to align nodes with the current control plane before the next upgrade,
and check EKS managed-node, Fargate, self-managed and Hybrid requirements separately.
Use kubectl within one minor of the control plane.

| Deployment | Update responsibility |
|---|---|
| Pure Auto Mode | Service-managed nodes, networking, block storage and LB capabilities |
| Ordinary/self-managed/Hybrid nodes | Plan node, CNI, DNS, proxy, driver and controller updates |
| Mixed cluster | Preserve add-ons needed by non-Auto nodes |
| Apps, self-managed controllers and EKS add-ons | Validate installed versions, configuration and CRDs |

Pure Auto Mode uses CoreDNS as a node system service. An absent CoreDNS Deployment alone is
not a failure; mixed clusters must retain DNS Deployments required by other nodes.
Do not unconditionally install or look for ordinary-node aws-node/kube-proxy/Pod Identity agent
pods in Auto Mode. Compatibility may require work before the control-plane upgrade, so
“control plane → every add-on → nodes” is not universal.

| API stability | Deprecation policy |
|---|---|
| GA | May be deprecated, but not removed within the same Kubernetes major version |
| Beta | Serving removal after at least nine months or three minors following deprecation, whichever is longer |
| Alpha | Can be removed without prior deprecation notice |

CLI flag and metric policies differ. Compare migration guides and actual installed versions,
architectures, platform versions and compute types rather than copying old compatibility tables.

## 2. Pre-upgrade review

Upgrade insights have timing and coverage limits. The official upgrade guide still notes a
temporary suspension of requiring `--force` for certain upgrade-insight issues.
Distinguish this from rollback readiness ERROR/UNKNOWN blocking below.
API acceptance is not a completed readiness review.

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.3 distinguishes exit 0 (clean), 2 (deprecated) and 3 (removed).
Do not turn every nonzero result into “not installed” or hide it with `|| true`.
Its JSON is an object: count `.items // []`; a clean response may omit items.
`detect-all-in-cluster` is also valid. Check the official release architecture and checksum.

Live discovery can miss original API versions because the API server converts objects.
Review Git, rendered Helm/Kustomize, release metadata, API warnings/audit and actual clients.
Align Pluto's other component targets with deployed Istio/cert-manager versions too.

This read-only tool compares EKS and kubecontext endpoints, then checks Node/Pod readiness,
Deployment generation/rollout, PDBs and actually installed add-ons.
A proxy kubeconfig can differ from the direct EKS endpoint and requires separate review.

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

Exit 0 means the listed checks were collected, 2 means findings, and 1 means an unknown result
due to error. Zero is not automatic upgrade approval or proof of full application health.
Advertised add-on versions still need architecture/platform/compute-type and configuration review.

A PDB with maxUnavailable 1 can still allow zero disruptions because of unhealthy pods or
overlapping PDBs. AlwaysAllow changes unhealthy-pod eviction behavior; it does not guarantee availability.

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

Do not infer health from Node phase or Pod Running alone. Distinguish zero-replica Deployments,
completed Jobs and empty PDB selectors. Inspect EndpointSlice ready/serving/terminating conditions
and Service selectors; selectorless/ExternalName Services do not require ordinary Pod endpoints.

## 3. Backup and restore validation

Managed EKS backups do not imply customer-controlled restoration from arbitrary etcd snapshots.
Separate Git/IaC, Kubernetes objects, PV data, external databases, permissions, encryption keys
and recovery procedures. Prepare Velero BackupStorageLocation, plugin/CSI snapshot configuration
and IAM first. This Schedule explicitly selects production.
The default Backup CLI includes `*` namespaces; it does not automatically exclude all of velero.

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

Completed does not prove application consistency or recovery of every volume.
Review errors/warnings, snapshot/data-mover results, excluded volumes and DB quiescing/replication.
PVC/PV objects alone are not a complete application/Secret/Service/data backup.
Filesystem backup requires separate node-agent and volume configuration.

Velero 1.18.2 restore create has no `--dry-run`.
`-o yaml/json` prints the Restore without creating it, but performs discovery/Backup reads.
It is neither completely offline nor a recovery test.

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

Perform actual restores in an isolated test environment. Namespace mapping alone does not
isolate CronJobs, consumers, external DBs or DNS/LB changes.
Review backup-storage write ownership, snapshot region/AZ and KMS/IAM for the test cluster.
Use a read-only BackupStorageLocation for synchronization where appropriate.
Test restore creation, Pod startup, volume attachment, integrity and application behavior separately.
Do not delete the original backup during test cleanup.

## 4. Control-plane and node updates

This uses the existing cluster layer from the [infrastructure chapter](./01-infrastructure-setup.md).
Do not create a duplicate cluster in new state or rebuild VPC/IAM.
Review module/provider major changes separately from Kubernetes minor changes.
Do not mix old EKS module v20 inputs into the current module.
Replace tfvars with a real absolute file path.

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="kubernetes_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

If choosing CLI changes, avoid concurrent IaC changes to the same setting.
The next command performs a real change after readiness review. Record its update ID.

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

Exit 0 means Successful, 1 means failure/cancellation/query error, and 2 means a client timeout.
Timeout does not cancel AWS; resume observing the same ID.
A control-plane upgrade cannot be arbitrarily paused/stopped after it starts.
cluster-active alone does not establish completion of node replacement.
Recheck actual version, nodes and applications afterward.

Auto Mode incrementally replaces nodes after the control-plane update.
Customers do not select an Auto Mode AMI through EC2NodeClass al2023@latest.
Ordinary managed/self-managed/Hybrid nodes and existing Fargate pods need separate handling.
EKS add-ons are not all automatically updated. Review versions and configuration schemas
from describe-addon-configuration; do not indiscriminately apply OVERWRITE.

### Disruption constraints

Applicable NodePool budgets combine through the most restrictive constraint.
10% and 1 do not mean “at least one.” Consider rounding, deleting/NotReady nodes and UTC schedules.
A scheduled budget alone does not prohibit disruption outside its active window.

To pause voluntary drift, preserve/review existing budgets, add a policy such as
`nodes: "0", reasons: [Drifted]`, then restore the original policy.
A do-not-disrupt annotation on NodePool metadata is not that pause mechanism.
Node/Pod annotations and budgets do not prevent every interruption, expiry or termination-grace path.

| Manual drain option | Meaning |
|---|---|
| `--ignore-daemonsets` | Excludes DaemonSet pods without deleting them |
| `--delete-emptydir-data` | Permits emptyDir data loss |
| `--disable-eviction` | Deletes instead of using Eviction, bypassing PDB protection |

DaemonSets run on eligible nodes. Do not automate force-deletion/PDB bypass as a generic remedy.

## 5. Native Kubernetes version rollback

EKS supports initiating rollback to the previous minor within seven days of upgrade completion.
“Control planes can never roll back” is no longer correct.
Restrictions include clusters created at their current version, an expired window, automatic upgrades
at the end of extended support and EKS features incompatible with the target.
After consecutive upgrades only the immediately previous minor is eligible.
Extended-support targets require the corresponding policy and cost conditions.

| Component | Handling |
|---|---|
| API server/control plane | Previous Kubernetes minor and its latest platform version |
| Auto Mode nodes | Service adjusts nodes first, then rolls back the control plane |
| Ordinary managed node groups | User adjusts them first with UpdateNodegroupVersion |
| Self-managed/Hybrid nodes | User first replaces them with compatible nodes |
| Fargate | No direct downgrade of existing Pod kubelets; plan separate replacement/compatibility |
| Add-ons, apps, etcd objects and PV data | Not restored from a historical snapshot |

This is not data restoration or instant traffic failback.
Validate compatibility of new APIs/fields, controllers and DB schemas with the previous version.

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

The tested CLI 2.36.44 supports rollback-config; the environment's older 2.35.11 did not.
Do not confuse an old CLI's unknown option with absence of the EKS capability.
Use the official updated CLI or a supported API/SDK. There is no separate aws eks rollback-cluster command.

Rollback readiness ERROR/UNKNOWN blocks the operation; WARNING is advisory.
Force can bypass insight checks, but not eligibility or Auto Mode disruption controls.
The baseline does not use force.

### Auto Mode observation and cancellation

During node rollback the control plane keeps serving the newer version and cluster status stays
ACTIVE. EKS rechecks insights after nodes meet target skew requirements, then rolls back the CP.
Observe the update ID. Node timeout defaults to 720 minutes, with a range of 120–10,080 minutes.
It is a minimum bound, not an exact timer. Distinguish the seven-day initiation window from an
already-started node phase's timeout. On timeout, the CP stays at the current version, nodes drift
back toward it, and the update becomes Failed.

A zero Drift budget or node do-not-disrupt can block progress. PDBs/Pod annotations can delay
disruption up to TerminationGracePeriod, not permanently prevent it.
Best-effort cancellation is available during the node phase, although individual disruptions
already underway may finish. Cancellation is unavailable after CP rollback starts.

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

After cancellation nodes drift toward the current CP version.
An IaC timeout does not stop the AWS operation, and CloudFormation stack rollback is not automatic
Kubernetes version rollback. Reconcile actual and intended IaC versions after CLI/API changes.

## 6. Blue/green

Use distinct state/identity for Green and keep shared DNS/NLB/database ownership outside Blue's
deletion scope. Register through the [multi-cluster GitOps](./04-gitops-multi-cluster.md) procedures
for real endpoint/CA, workload identity, assume-role, EKS access entries and Kubernetes RBAC.
Apply the cluster Secret to the Hub context, not Green.

This ApplicationSet selects Green only without automated sync.
Prepare the production AppProject/namespace, repository and approved revision.
Replace URL/SHA placeholders and control concurrent activation of workers, consumers and CronJobs.
preserveResourcesOnDeletion protects workloads if a selector change removes a generated Application.
Preservation is not a management handoff; plan steady-state GitOps ownership before changing colors/selectors.

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

To roll back a Git revision, restore approved Git state and sync.
argocd app rollback takes a deployment history ID, not a SHA.
Automated sync/ApplicationSet desired state can otherwise change it again.

### Test Green directly

Running pods and TCP connectivity do not prove DB/message/readiness behavior.
Use a direct Green path and preserve the service hostname's SNI/Host and certificate validation.
The NLB's AWS hostname is not the application TLS hostname.
For a Service that actually serves HTTPS on 443, use a separate terminal:

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

In another terminal, use the actual hostname, path and response contract.

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### NLB weights

NLB weighted target groups are supported. Relative weights range from 0–999 and need not sum to 100.
They express expected shares of new connections, not exact requests, bytes or existing sessions.
Register healthy targets in separate TGs for each cluster.
See [advanced infrastructure](./02-infrastructure-advanced.md) for TGB, target type and network/security groups.

Ordinary weight changes affect new connections, but setting weight zero can close existing
connections after a short period. This is not uninterrupted draining; test lifetime, retries and sessions.
TCP/UDP/TCP_UDP support target-group stickiness; TLS listeners do not.
TCP forward stickiness is not an ALB-only feature.
The API documents DurationSeconds for ALB; do not copy that duration guarantee to NLB.

This tool only generates JSON. Verify the actual listener protocol and target-group VPC,
protocol/IP family, health and existing stickiness first.

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

Set the three ARN variables first. Do not advance percentages on timers alone.
Observe SLOs, new/existing connections, errors and sessions at each stage.
Test zero weight, unhealthy targets and cross-zone behavior instead of assuming failover to another TG.
Use a separate direct Service path when validating Green behind a shared NLB.

### Data and cleanup

External RDS/ElastiCache or shared EFS does not remove schema, permissions, cache-format or
concurrent writer/consumer migration work. A shared filesystem or one SQL count does not establish
consistency. Check snapshot region/AZ, storage class, KMS and RPO since the last writes.

Retain Blue through the agreed observation/recovery period and data-compatibility verification.
A zero-weight TG can still be referenced by a listener.
Auto Mode TGB/cluster deletion affects the associated TG lifecycle. Remove Blue TG references
from shared listeners, then review ownership, IaC and deletion order before cleanup.
Distinguish this from self-managed LB Controller external-TG ownership.
Do not automatically terraform destroy immediately after shifting traffic.

If workers already run in AZ-separated clusters, upgrading one cluster at a time is an option.
That does not make each EKS control plane single-AZ.
Validate other clusters' spare capacity/state compatibility and native rollback eligibility/duration.
The seven-day window does not guarantee instant Blue failback.

## 7. Post-upgrade validation

After update Successful, verify actual versions, Node/Pod Ready, controller generations,
DNS/network paths, storage, permissions, application behavior and scheduled work.
count also counts zero-valued condition/phase samples. Aggregate values as below and do not
turn missing observations into healthy zero. Multiple clusters need actual cluster labels in collection.

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

Pod restart counts are not rescheduling counts. Do not assume Auto Mode controller metrics
are scraped from a self-managed Karpenter pod.
The following requires a real service=api label/metric contract.
Zero traffic is not healthy zero error rate; fill missing error series with zero only when
the total-traffic series exists and its rate is positive.

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

Use the same offset for numerators, denominators and buckets when comparing history.
[30m] offset 1h covers 90–60 minutes before now, not 60–30 minutes.
Compare equivalent cohorts: blue/green can differ in traffic, routes, sample counts and load.
Seventy-two hours does not cover a full weekly pattern. Choose observation duration from workload
cycles and the rollback eligibility window.

Use the [stack chapter's](./09-observability-stack.md) explicit UIDs and complete dashboard provisioning.
Do not present partial panel YAML/JSON as a complete importable dashboard.
Record before/after versions, update IDs, planned/actual timing, failures and recovery outcomes.

This review checked synthetic preflight/wait/routing cases, official CLI parsers, Velero GET-only
output behavior and manifests/queries. It did not execute real EKS upgrades/rollbacks, NLB changes,
snapshots/restores or application load tests.

## Official references

- [EKS update](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Auto Mode rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Auto Mode upgrades](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [Kubernetes version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Kubernetes deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.3](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.3)
- [Velero 1.18.2](https://github.com/velero-io/velero/releases/tag/v1.18.2)
- [NLB listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [Previous: Resource optimization](./10-resource-optimization.md) | [Contents](./README.md) | [Next: Event capacity planning](./12-event-capacity-planning.md) >
