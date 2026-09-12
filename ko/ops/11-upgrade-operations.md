# EKS 업그레이드: Auto Mode, 롤백과 Blue/Green

> 검토: 2026-09-12. 명령 검증: AWS CLI 2.36.44, Pluto 5.24.3, Velero 1.18.2.
> 예시 전환은 1.35 → 1.36이며 실제 대상은 리전에서 조회합니다.

컨트롤 플레인·노드·애드온·앱·데이터를 함께 계획합니다.
Auto Mode와 PDB만으로 무중단을 보장하지 않습니다. 여유 용량, readiness,
재연결, 세션, 저장 상태와 복구를 검증해 가용성 목표를 충족합니다.

## 1. 버전과 관리 주체

상류 Kubernetes는 최근 **세 minor release**를 유지합니다.
“현재 버전 + 세 개 이전 버전”이라는 설명과 다릅니다.
EKS 수명은 별도이며 일반적으로 EKS 출시 후 표준 지원 14개월, 연장 지원 12개월입니다.
정확한 날짜·지원 정책·리전 가용성은 조회 시점의 API와 공식 수명주기를 확인합니다.

일반 EKS 기본 제어 플레인 요금은 표준 지원 $0.10/시간,
연장 지원 **총 $0.60/시간($0.10 + $0.50)**입니다. $0.60이 추가분은 아닙니다.
Auto Mode·컴퓨팅·스토리지·네트워크와 별도 control plane capacity 요금은 포함되지 않습니다.

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

`describe-addon-versions`는 애드온 호환성용이며 클러스터 지원 종료일 조회가 아닙니다.
EKS 컨트롤 플레인은 다음 minor로 한 단계씩 진행하며 중간 minor를 건너뛰지 않습니다.
현재 지원 버전의 kubelet은 API server보다 새로울 수 없고 상류 정책상 최대 세 minor 이전을
허용하는 조건이 있습니다. 이것을 노드를 계속 오래된 버전으로 유지하라는 권장으로 해석하지 않습니다.
노드를 현재 CP 버전에 정렬한 뒤 다음 업그레이드를 진행하도록 계획하고,
EKS 관리 노드·Fargate·자가 관리·Hybrid의 개별 조건을 확인합니다. kubectl은 CP와 ±1 minor를 사용합니다.

| 구성 | 업데이트 책임 |
|---|---|
| 순수 Auto Mode | 서비스가 노드·네트워크·블록 스토리지·LB 기능 등을 관리 |
| 일반/자가 관리/Hybrid 노드 | 노드·CNI·DNS·proxy·드라이버·컨트롤러를 별도 계획 |
| 혼합 클러스터 | 일반 노드가 사용하는 애드온을 유지하며 Auto Mode 경로와 구별 |
| 앱·자가 관리 컨트롤러·EKS 애드온 | 사용자가 설치한 버전·설정·CRD 호환성을 확인 |

순수 Auto Mode는 노드 system service의 CoreDNS를 사용합니다.
CoreDNS Deployment가 없다는 이유만으로 장애로 판정하지 않습니다. 일반 노드가 섞이면 필요한
DNS Deployment를 유지합니다. Auto Mode에 일반 노드용 aws-node/kube-proxy/Pod Identity agent
Pod를 무조건 설치하거나 고정 label로 존재를 검사하지 않습니다.
호환성 때문에 CP보다 먼저 필요한 준비 작업도 있어 “CP → 모든 애드온 → 노드”는 보편적 순서가 아닙니다.

| API 안정성 | 사용 중단 정책 |
|---|---|
| GA | deprecated로 표시할 수 있지만 같은 Kubernetes major 안에서 제거하지 않는 정책 |
| Beta | deprecation 후 최소 9개월 또는 3 minor 중 긴 기간을 거쳐 serving 제거 |
| Alpha | 사전 deprecation 없이 릴리스에서 제거될 수 있음 |

CLI flag·metric 정책은 API version 정책과 다릅니다.
과거 애드온/기능 표 대신 대상 migration guide와 실제 설치 버전·architecture·platformVersion·
compute type을 대조합니다.

## 2. 사전 점검

Upgrade insights는 시점·수집 범위에 한계가 있습니다.
공식 업그레이드 문서는 일부 insight 문제에 `--force`를 강제하던 기능이 일시 철회된 상태임을
안내합니다. 이를 뒤의 **rollback readiness ERROR/UNKNOWN 차단**과 혼동하지 않습니다.
API가 요청을 받아주는 것만으로 검증이 끝나지는 않습니다.

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.3은 문제 없음 0, deprecated 발견 2, removed 발견 3을 구별합니다.
이를 모두 “미설치”로 처리하거나 `|| true`로 성공 처리하지 않습니다.
JSON은 객체이며 항목은 `.items // []`에서 셉니다. 문제 없는 응답에는 items가 없을 수 있습니다.
`detect-all-in-cluster`도 유효합니다. 공식 release의 OS/architecture와 checksum을 확인합니다.

실행 중 리소스 조회는 API server 변환으로 원래 API version을 놓칠 수 있습니다.
Git·렌더링한 Helm/Kustomize·Helm release·API warning/audit·실제 client 호출을 함께 봅니다.
Pluto의 다른 component target도 실제 Istio/cert-manager 버전과 맞춥니다.

다음 읽기 전용 도구는 EKS와 kubecontext endpoint를 비교하고 Node/Pod Ready,
Deployment generation/rollout, PDB와 실제 설치된 애드온을 검사합니다.
프록시 kubeconfig는 직접 EKS endpoint와 다를 수 있어 별도 확인합니다.

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

exit 0은 나열한 점검 수집, 2는 검토 항목, 1은 결과를 알 수 없는 오류입니다.
0이 자동 업그레이드 승인이나 전체 앱 정상 판정은 아닙니다.
광고된 애드온 버전도 architecture/platform/compute type과 설정 migration을 별도로 확인합니다.

PDB maxUnavailable이 1이어도 이미 unhealthy한 Pod나 중첩 PDB 때문에 allowance가 0일 수 있습니다.
AlwaysAllow는 unhealthy Pod 퇴거 동작을 바꾸며 서비스 가용성을 보장하지 않습니다.

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

Node phase나 Pod Running만으로 정상 판정하지 않습니다. 0 replica Deployment, 종료된 Job,
빈 selector의 PDB도 구별합니다. EndpointSlice의 ready/serving/terminating 조건과 Service selector를
확인하며 selector 없는 Service/ExternalName에 일반 Pod endpoint를 요구하지 않습니다.

## 3. 백업과 복원 검증

EKS의 관리형 백업은 고객이 임의 etcd snapshot으로 복원할 수 있다는 뜻이 아닙니다.
Git/IaC·Kubernetes 객체·PV 데이터·외부 DB·권한·암호화 키와 복구 절차를 구분합니다.
Velero의 BackupStorageLocation, plugin/CSI snapshot 구성과 IAM이 먼저 준비되어야 합니다.
아래는 production을 명시적으로 선택한 Schedule입니다.
기본 Backup CLI는 `*` 네임스페이스를 포함하며 velero 전체를 자동 제외한다고 가정하지 않습니다.

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

Completed가 앱 정합성과 모든 볼륨 복구를 보장하지 않습니다. errors/warnings,
snapshot/data-mover 결과, 제외된 볼륨과 DB quiesce/replication을 확인합니다.
PVC/PV 객체만 백업하는 것은 앱·Secret·Service·데이터를 포함한 전체 백업과 다릅니다.
파일 시스템 백업에는 별도 node-agent와 볼륨 설정이 필요합니다.

Velero 1.18.2의 `restore create`에는 `--dry-run`이 없습니다.
`-o yaml/json`은 Restore를 출력하고 생성하지 않지만 discovery와 Backup 읽기는 수행합니다.
완전한 오프라인 검사나 복원 성공 시험으로 부르지 않습니다.

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

실제 복원 시험은 격리된 테스트 환경에서 수행합니다. 네임스페이스 mapping만으로
CronJob·consumer·외부 DB·DNS/LB 변경이 격리되지 않습니다.
테스트 클러스터의 backup storage 쓰기 소유권, snapshot region/AZ, KMS/IAM을 확인합니다.
필요하면 읽기 전용 BackupStorageLocation으로 동기화합니다.
복원 생성·Pod 실행·볼륨 attach·무결성·앱 동작을 각각 시험하며 정리 때 원래 백업을 삭제하지 않습니다.

## 4. 컨트롤 플레인과 노드 업데이트

아래는 [인프라 설정 장](./01-infrastructure-setup.md)의 기존 cluster layer 예제입니다.
새 state로 동일 클러스터를 중복 생성하거나 VPC/IAM을 다시 만들지 않습니다.
module/provider major 전환과 Kubernetes minor 전환은 변경 범위를 각각 검토합니다.
과거 EKS module v20의 입력 이름을 현행 module과 섞지 않습니다.
tfvars는 실제 파일의 절대 경로로 바꿉니다.

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="kubernetes_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

CLI를 변경 수단으로 선택하면 IaC와 동시에 같은 값을 변경하지 않습니다.
다음은 실제 변경 명령이며 사전 검토 후 실행합니다. 반환된 update ID를 기록합니다.

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

exit 0은 update Successful, 1은 실패/취소/조회 오류, 2는 클라이언트 timeout입니다.
timeout은 AWS 작업 취소가 아닙니다. 같은 ID로 관찰을 재개합니다.
컨트롤 플레인 업그레이드는 시작 후 임의 pause/stop할 수 없습니다.
`aws eks wait cluster-active`만으로 노드 교체 완료까지 판정하지 않습니다.
마지막에 실제 cluster version과 노드·앱을 다시 확인합니다.

Auto Mode는 CP 업데이트 후 새 버전 노드로 점진적으로 교체합니다.
Auto Mode AMI를 고객 EC2NodeClass의 `al2023@latest`로 선택하는 구조가 아닙니다.
일반 관리 노드·자가 관리·Hybrid·기존 Fargate Pod는 별도 교체가 필요합니다.
EKS 애드온도 모두 자동 업데이트되지 않습니다. 검토한 버전과
`describe-addon-configuration` 스키마로 설정 보존/변경을 계획하며 OVERWRITE를 일괄 적용하지 않습니다.

### Disruption 제약

적용되는 NodePool budget 중 더 엄격한 제약을 따릅니다.
10%와 1은 “적어도 1개”라는 OR 조건이 아닙니다.
반올림, 삭제/NotReady 노드와 UTC schedule을 고려합니다.
scheduled budget 하나만 추가하면 그 밖의 시간에 자동 금지되는 것도 아닙니다.

voluntary drift를 막을 때는 기존 budget 목록을 보존·검토한 뒤
`nodes: "0", reasons: [Drifted]` 정책을 추가하고 원래 정책으로 복구합니다.
NodePool metadata의 do-not-disrupt annotation은 이 pause 기능이 아닙니다.
노드/Pod annotation과 budget도 interruption·만료·종료 grace period의 모든 경로를 막지 않습니다.

| 수동 drain 옵션 | 의미 |
|---|---|
| `--ignore-daemonsets` | DaemonSet Pod를 삭제하지 않고 제외 |
| `--delete-emptydir-data` | emptyDir 데이터 손실 허용 |
| `--disable-eviction` | Eviction API 대신 삭제하여 PDB 보호 우회 |

DaemonSet은 eligible node에 실행됩니다. 강제 삭제/PDB 우회를 자동 복구로 사용하지 않습니다.

## 5. 네이티브 Kubernetes 버전 롤백

EKS는 **업그레이드 완료 후 7일 안에 시작하는 이전 minor 롤백**을 지원합니다.
“컨트롤 플레인은 항상 롤백 불가”라는 설명은 현재 기준으로 잘못되었습니다.
현재 버전으로 생성한 클러스터, 만료된 자격 창, end-of-extended-support 자동 업그레이드,
대상 버전이 지원하지 않는 EKS 기능 등은 제한됩니다.
연속 업그레이드 후에는 현재의 바로 이전 minor만 대상으로 합니다.
연장 지원 버전으로 돌아가려면 upgrade policy와 비용 조건도 맞춰야 합니다.

| 항목 | 처리 |
|---|---|
| API server/제어 플레인 | 이전 Kubernetes minor와 그 버전의 최신 platform version |
| Auto Mode 노드 | 서비스가 **노드부터** 조정한 뒤 CP 롤백 |
| 일반 관리 노드 그룹 | 사용자가 UpdateNodegroupVersion으로 먼저 조정 |
| 자가 관리/Hybrid | 사용자가 먼저 호환 노드로 교체 |
| Fargate | 기존 Pod kubelet 직접 downgrade 미지원. 별도 교체/호환성 계획 필요 |
| 애드온·앱·etcd 객체·PV 데이터 | 과거 snapshot으로 복원되지 않음 |

이는 데이터 복원이나 즉각적인 traffic failback이 아닙니다.
새 API/필드·컨트롤러·DB schema와 이전 버전의 호환성을 검증합니다.

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

이 rollback-config 옵션은 검증한 CLI 2.36.44에서 지원합니다.
작업 환경의 이전 CLI 2.35.11은 인식하지 못했습니다. 옵션 오류를 기능 부재로 오해하지 않고
공식 CLI를 업데이트하거나 지원되는 API/SDK를 사용합니다. 별도 `aws eks rollback-cluster` 명령은 없습니다.

Rollback readiness의 ERROR/UNKNOWN은 차단하고 WARNING은 advisory입니다.
force는 insight 검사를 우회할 수 있지만 자격 조건과 Auto Mode disruption 제약을 해제하지 않습니다.
기본 예제는 force를 사용하지 않습니다.

### Auto Mode 관찰과 취소

노드 롤백 중에는 CP가 새 버전으로 계속 동작하고 cluster status도 ACTIVE입니다.
노드가 대상 skew를 충족하면 insights를 다시 검사한 뒤 CP를 롤백하므로 update ID로 관찰합니다.
노드 단계 timeout은 기본 720분(12시간), 범위 120–10,080분이며 정확한 순간의 timer가 아니라
지정 시간보다 일찍 발생하지 않는 하한 성격입니다.
7일 **시작 자격 창**과 시작된 작업의 node timeout을 구별합니다.
timeout이면 CP는 현재 버전에 남고 노드는 다시 현재 버전으로 drift하며 update는 Failed가 됩니다.

Drift budget 0과 노드 do-not-disrupt는 진행을 막을 수 있습니다.
PDB/Pod do-not-disrupt는 TerminationGracePeriod까지 지연시킬 수 있으며 영구적인 보호가 아닙니다.
노드 단계에서는 best-effort cancel이 가능하지만 진행 중인 개별 disruption은 마무리될 수 있습니다.
CP 롤백이 시작되면 취소할 수 없습니다.

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

취소 완료 후 노드는 현재 CP 버전으로 다시 drift합니다.
IaC timeout이 AWS 작업을 멈추는 것은 아니며 CloudFormation stack rollback도 자동 Kubernetes
버전 롤백이 아닙니다. CLI/API로 바꿨다면 실제 버전과 IaC의 의도를 맞춘 뒤 다음 plan을 만듭니다.

## 6. Blue/Green

Green은 별도 상태·이름으로 만들고 DNS·공유 NLB·DB 소유권을 Blue 삭제 범위와 분리합니다.
[멀티 클러스터 GitOps](./04-gitops-multi-cluster.md)의 실제 endpoint/CA, workload identity,
assume-role, EKS access entry와 Kubernetes RBAC 절차로 등록합니다.
cluster Secret은 Green이 아니라 **Hub context**에 적용합니다.

다음 ApplicationSet은 Green만 선택하고 자동 sync를 켜지 않습니다.
production AppProject/namespace, 실제 저장소와 승인된 revision이 필요합니다.
URL/SHA placeholder를 교체하고 worker/consumer/CronJob의 양쪽 동시 활성화를 방지합니다.
cluster label 변경으로 생성된 Application이 제거될 수 있어 preserveResourcesOnDeletion을 설정했습니다.
리소스 보존은 관리 인계가 아닙니다. 색상/selector 변경 전 최종 GitOps 소유권을 계획합니다.

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

Git revision으로 되돌리려면 승인된 Git 상태로 복원해 sync합니다.
`argocd app rollback`의 인자는 SHA가 아니라 deployment history ID입니다.
자동 sync/ApplicationSet desired state와 충돌하면 다시 변경될 수 있습니다.

### Green 직접 시험

Running Pod와 정상 TCP 연결만으로 DB·메시지·readiness 동작을 입증하지 않습니다.
Green에 직접 도달하는 경로를 사용하며 HTTPS는 실제 hostname의 SNI/Host와 인증서 검증을 유지합니다.
NLB의 AWS hostname을 서비스 TLS hostname처럼 쓰지 않습니다.
예를 들어 실제 HTTPS 443 Service라면 별도 터미널에서:

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

다른 터미널에서 실제 hostname·경로·응답 계약으로 확인합니다.

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### NLB 가중치

NLB weighted target groups는 지원됩니다. 값은 0–999의 **상대 가중치**이며 합계가 100일 필요는 없습니다.
새 연결의 기대 비중이지 요청/바이트/기존 세션의 정확한 비율이 아닙니다.
각 클러스터의 별도 TG에 healthy target이 실제 등록되어야 합니다.
TGB·target type·네트워크/보안 그룹은 [인프라 고급](./02-infrastructure-advanced.md)을 참조합니다.

일반 가중치 변경은 새 연결에 적용되지만 **0으로 바꾸면 짧은 시간 후 기존 연결도 닫힐 수 있습니다.**
무중단 draining과 같지 않으며 연결 수명·재시도·세션을 시험합니다.
TCP/UDP/TCP_UDP는 target-group stickiness를 지원하지만 TLS listener는 지원하지 않습니다.
TCP forward stickiness를 ALB 전용 기능으로 제거하지 않습니다.
API의 DurationSeconds는 ALB용으로 설명되어 있으므로 NLB에 같은 시간 보장을 복사하지 않습니다.

다음 도구는 JSON 생성만 수행합니다. 실제 listener protocol,
두 TG의 VPC/프로토콜/IP family·health·기존 stickiness를 먼저 확인합니다.

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

세 ARN 변수는 실제 값으로 먼저 설정합니다. 타이머만으로 다음 비중으로 자동 진행하지 않습니다.
단계별 SLO·신규/기존 연결·오류·세션을 관찰합니다. weight 0, target 비정상,
cross-zone 설정도 시험하며 다른 TG로 자동 failover될 것이라 가정하지 않습니다.
shared NLB의 Green을 직접 검증할 때는 별도 Service 검증 경로를 사용합니다.

### 데이터와 정리

외부 RDS/ElastiCache·공유 EFS를 써도 schema·권한·캐시 형식·동시 writer/consumer 전환은 남습니다.
같은 파일시스템을 연결하거나 SQL count 한 번을 실행하는 것만으로 정합성을 보장하지 않습니다.
snapshot region/AZ·스토리지 클래스·KMS와 마지막 쓰기 이후 RPO도 확인합니다.

Blue는 합의한 관찰/복구 기간과 데이터 호환성 확인 전까지 유지합니다.
weight 0인 TG도 listener에서 아직 참조될 수 있습니다.
Auto Mode의 TGB/클러스터 삭제는 연관 TG 삭제 수명주기에 영향을 주므로,
공유 listener의 Blue TG 참조를 제거하고 소유권·IaC·삭제 순서를 확인한 뒤 정리합니다.
일반 자가 관리 LB Controller의 외부 TG 수명주기와 혼동하지 않습니다.
traffic shift 직후 terraform destroy를 자동 실행하지 않습니다.

이미 worker 배치를 AZ별 클러스터로 나눴다면 한 클러스터씩 in-place 업데이트할 수도 있습니다.
각 EKS 제어 플레인이 단일 AZ라는 뜻은 아닙니다.
다른 클러스터의 여유 용량·상태 호환성과 native rollback 자격/소요 시간을 확인합니다.
7일 롤백 창은 즉시 Blue failback을 보장하는 기능이 아닙니다.

## 7. 사후 검증

update Successful 뒤에도 실제 버전, Node/Pod Ready, controller generation, DNS·입출력 네트워크,
스토리지·권한·앱 기능과 배치 작업을 확인합니다.
`count`는 0인 condition/phase gauge도 셉니다. 아래처럼 값을 집계하며 수집 데이터가 없다는 것을
정상 0으로 바꾸지 않습니다. 다중 클러스터에서는 실제 cluster label을 수집 경로에 설정합니다.

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

Pod restart 수는 reschedule 수가 아닙니다. Auto Mode의 컨트롤러 메트릭이
자가 관리 Karpenter Pod에서 scrape된다고 가정하지 않습니다.
아래 앱 쿼리는 실제 `service="api"` label과 metric 계약이 있어야 합니다.
분모가 0이면 오류율을 정상 0으로 만들지 않고, error series가 없지만 트래픽은 있는 경우만 0을 채웁니다.

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

과거와 비교할 때 분자/분모/bucket에 같은 offset을 사용합니다.
`[30m] offset 1h`는 현재 기준 **90–60분 전** 구간이며 60–30분 전이 아닙니다.
Blue/Green은 요청량·route·샘플 수·부하 조건이 달라질 수 있어 동일한 cohort로 비교합니다.
72시간이 주간 패턴 전체를 포함한다고 말하지 않습니다. 배치/주말/업무 주기와 rollback 자격 창을
함께 고려해 관찰 기간을 정합니다.

Grafana는 [스택 장](./09-observability-stack.md)의 명시적 UID와 완전한 dashboard provisioning을
사용합니다. 부분 panel YAML/JSON을 import 가능한 전체 dashboard라고 제시하지 않습니다.
변경 전/후 버전, update ID, 계획·실제 소요 시간, 실패/복구 결과와 다음 점검을 기록합니다.

이 장의 검토는 합성 입력으로 점검/대기/라우팅 도구, 공식 CLI parser, Velero의 GET-only 출력
동작과 manifest/query를 확인했습니다. 실제 EKS 업그레이드·롤백, NLB 변경, snapshot/복원이나
애플리케이션 부하 시험을 실행한 것은 아닙니다.

## 공식 자료

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

< [이전: 리소스 최적화](./10-resource-optimization.md) | [목차](./README.md) | [다음: 이벤트 용량 계획](./12-event-capacity-planning.md) >
