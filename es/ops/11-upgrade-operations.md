# Actualizaciones de EKS: Auto Mode, rollback y blue/green

> **Última actualización**: 12 de septiembre de 2026. Comandos comprobados con AWS CLI 2.36.44, Pluto 5.24.3 y Velero 1.18.2.
> La transición de ejemplo es 1.35 → 1.36; compruebe la disponibilidad regional real.

Planifique conjuntamente control plane, nodos, complementos, aplicaciones y datos. Auto Mode
y PDB no garantizan servicio ininterrumpido. Valide reserva, readiness, reconexión, sesiones,
estado y recuperación frente a los objetivos de disponibilidad.

## 1. Versiones y responsabilidades

Kubernetes upstream mantiene las tres versiones menores más recientes, no la actual más tres
anteriores. EKS tiene su propio ciclo: generalmente 14 meses estándar y 12 ampliados.
Compruebe fechas exactas, política y disponibilidad regional.

La tarifa base ordinaria de control plane EKS es $0.10/hora con soporte estándar y un total de
$0.60/hora con soporte ampliado ($0.10 + $0.50). El suplemento no es $0.60.
Auto Mode, cómputo, almacenamiento, red y capacidad de control aprovisionada aparte son adicionales.

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

`describe-addon-versions` comprueba compatibilidad de complementos, no fechas de soporte.
Avance el control plane una versión menor cada vez. kubelet no puede ser más nuevo que el API
server y la política upstream admite hasta tres menores anteriores bajo sus condiciones. No
recomienda mantener nodos atrasados. Alinéelos antes de la siguiente actualización y revise
por separado nodos administrados, Fargate, autogestionados e Hybrid. Use kubectl dentro de una versión menor.

| Despliegue | Responsabilidad de actualización |
|---|---|
| Solo Auto Mode | Nodos, red, bloques y LB administrados por el servicio |
| Nodos ordinarios/autogestionados/Hybrid | Planificar nodos, CNI, DNS, proxy, drivers y controladores |
| Clúster mixto | Conservar complementos de nodos no Auto |
| Apps, controladores propios y add-ons EKS | Validar versiones, configuración y CRD |

Auto Mode puro usa CoreDNS como servicio del nodo. No encontrar su Deployment no es por sí solo
un fallo; los clústeres mixtos conservan DNS para otros nodos. No instale ni busque incondicionalmente
Pods aws-node/kube-proxy/Pod Identity agent ordinarios en Auto Mode. La compatibilidad puede exigir
trabajo previo al control plane: «control plane → todos los add-ons → nodos» no es universal.

| Estabilidad API | Política de obsolescencia |
|---|---|
| GA | Puede declararse obsoleta, pero no eliminarse dentro del mismo major Kubernetes |
| Beta | Retirada tras al menos nueve meses o tres menores desde la obsolescencia, el plazo mayor |
| Alpha | Puede retirarse sin aviso previo de obsolescencia |

Las políticas de flags CLI y métricas difieren. Compare guías y versiones reales, arquitecturas,
versiones de plataforma y cómputo en lugar de copiar tablas antiguas.

## 2. Revisión previa

Upgrade insights tienen límites de tiempo y cobertura. La guía oficial todavía indica una suspensión
temporal de exigir `--force` para ciertos problemas. Distíngalo del bloqueo ERROR/UNKNOWN de
preparación para rollback descrito después. Que una API acepte no completa la revisión.

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.3 distingue salida 0 limpia, 2 obsoleta y 3 eliminada. No convierta todo error en «no instalado»
ni lo oculte con `|| true`. Su JSON es un objeto: cuente `.items // []`; una respuesta limpia puede
omitir items. `detect-all-in-cluster` también es válido. Verifique arquitectura y checksum oficiales.

El descubrimiento en vivo puede perder versiones API originales porque el servidor convierte objetos.
Revise Git, Helm/Kustomize renderizado, metadatos, advertencias/auditoría y clientes reales.
Ajuste también los targets de Pluto a Istio/cert-manager desplegados.

Esta herramienta de lectura compara endpoints EKS/kubecontext y comprueba Node/Pod readiness,
generación/rollout de Deployment, PDB y complementos instalados. Un kubeconfig con proxy puede
usar un endpoint distinto del directo EKS y requiere revisión aparte.

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

Salida 0 indica comprobaciones recogidas; 2, hallazgos; 1, resultado desconocido por error.
Cero no aprueba automáticamente una actualización ni prueba salud completa. Las versiones
anunciadas aún requieren revisar arquitectura/plataforma/cómputo y configuración.

Un PDB maxUnavailable 1 puede permitir cero interrupciones por Pods no saludables o PDB solapados.
AlwaysAllow cambia el desalojo de Pods no saludables, no garantiza disponibilidad.

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

No deduzca salud de fase Node o Pod Running. Distinga Deployments con cero réplicas, Jobs
completados y selectores PDB vacíos. Compruebe EndpointSlice ready/serving/terminating y selectores;
Services sin selector o ExternalName no necesitan endpoints Pod ordinarios.

## 3. Copias de seguridad y validación de restauración

Las copias administradas EKS no implican restauración controlada por el cliente desde cualquier
snapshot etcd. Separe Git/IaC, objetos Kubernetes, datos PV, bases externas, permisos, claves y
recuperación. Prepare BackupStorageLocation, plugins/CSI e IAM de Velero. Este Schedule selecciona
production explícitamente. Backup CLI incluye namespaces `*`; no excluye automáticamente todo velero.

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

Completed no demuestra consistencia ni recuperación de todos los volúmenes. Revise errores,
avisos, snapshots/data-mover, exclusiones y pausa/replicación de DB. PVC/PV solos no son copia
completa de aplicación/Secret/Service/datos. El backup de archivos requiere node-agent y volúmenes aparte.

Velero 1.18.2 restore create no tiene `--dry-run`. `-o yaml/json` imprime Restore sin crearlo,
pero consulta descubrimiento/Backup. No es completamente offline ni una prueba de recuperación.

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

Restaure realmente en pruebas aisladas. Mapear namespaces no aísla CronJobs, consumidores,
DB externas ni cambios DNS/LB. Revise propiedad de escritura del backup, región/AZ del snapshot
 y KMS/IAM del clúster de prueba. Use BackupStorageLocation de lectura para sincronizar cuando
proceda. Pruebe creación, arranque, adjunto de volumen, integridad y aplicación por separado.
No elimine el backup original durante la limpieza.

## 4. Actualización de control plane y nodos

Use la capa existente del [capítulo de infraestructura](./01-infrastructure-setup.md).
No duplique el clúster en otro state ni reconstruya VPC/IAM. Revise majors de módulo/proveedor
separados de minors Kubernetes. No mezcle entradas EKS módulo v20 con el actual.
Sustituya tfvars por una ruta absoluta real.

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

Si elige CLI, evite cambios IaC concurrentes sobre el mismo ajuste. El siguiente comando realiza
un cambio real tras la revisión. Registre el ID de actualización.

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

Salida 0 significa Successful; 1, fallo/cancelación/error de consulta; 2, timeout cliente.
El timeout no cancela AWS: continúe observando el mismo ID. Una actualización del control plane
no puede detenerse arbitrariamente después de empezar. cluster-active no prueba que finalizara
el reemplazo de nodos. Recompruebe versión, nodos y aplicaciones.

Auto Mode sustituye nodos incrementalmente después del control plane. El cliente no selecciona
su AMI con EC2NodeClass al2023@latest. Los nodos ordinarios/propios/Hybrid y Pods Fargate existentes
requieren tratamiento separado. No todos los add-ons se actualizan automáticamente. Revise versiones
y esquemas con describe-addon-configuration; no aplique OVERWRITE indiscriminadamente.

### Restricciones de interrupción

Los presupuestos NodePool se combinan con la restricción más estricta. 10% y 1 no significan
«al menos uno». Considere redondeo, nodos borrándose/NotReady y horarios UTC.
Un presupuesto programado no prohíbe interrupciones fuera de su ventana.

Para pausar drift voluntario, conserve/revise presupuestos, añada por ejemplo
`nodes: "0", reasons: [Drifted]` y restaure después la política original. Una anotación
do-not-disrupt en metadatos NodePool no es ese mecanismo. Anotaciones y presupuestos no impiden
toda interrupción, expiración o vía de terminación con gracia.

| Opción de drain manual | Significado |
|---|---|
| `--ignore-daemonsets` | Excluye Pods DaemonSet sin eliminarlos |
| `--delete-emptydir-data` | Permite perder datos emptyDir |
| `--disable-eviction` | Borra en vez de Eviction, omitiendo PDB |

DaemonSets se ejecutan en nodos elegibles. No automatice borrado forzado/omisión PDB como remedio genérico.

## 5. Rollback nativo de versión Kubernetes

EKS permite iniciar rollback a la menor anterior dentro de siete días tras finalizar la actualización.
«El control plane nunca puede retroceder» ya no es correcto. Hay restricciones para clústeres creados
en su versión actual, ventana vencida, actualizaciones automáticas al terminar soporte ampliado y
funciones EKS incompatibles. Tras varias actualizaciones solo se admite la menor inmediatamente
anterior. Volver a soporte ampliado exige sus condiciones de política y coste.

| Componente | Tratamiento |
|---|---|
| API server/control plane | Menor anterior y su última versión de plataforma |
| Nodos Auto Mode | El servicio ajusta primero nodos y luego control plane |
| Grupos administrados ordinarios | El usuario ajusta primero con UpdateNodegroupVersion |
| Autogestionados/Hybrid | El usuario sustituye primero por nodos compatibles |
| Fargate | No degrada directamente kubelets de Pods existentes; planificar reemplazo/compatibilidad |
| Add-ons, apps, objetos etcd y datos PV | No se restauran desde snapshot histórico |

No restaura datos ni devuelve tráfico instantáneamente. Valide compatibilidad de API/campos nuevos,
controladores y esquemas DB con la versión anterior.

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

CLI 2.36.44 soporta rollback-config; la antigua 2.35.11 del entorno no. Una opción desconocida en
CLI vieja no implica ausencia de capacidad EKS. Use CLI actual oficial o API/SDK compatible.
No hay un comando separado aws eks rollback-cluster.

ERROR/UNKNOWN en preparación bloquea; WARNING es informativo. Force puede omitir insights,
no elegibilidad ni controles de interrupción Auto Mode. La base no usa force.

### Observación y cancelación Auto Mode

Durante rollback de nodos, el control plane sigue en la versión nueva y el estado ACTIVE.
EKS revisa insights al cumplir el skew y luego revierte CP. Observe el ID. El timeout de nodos es
720 minutos por defecto, rango 120–10,080: límite mínimo, no temporizador exacto. Distinga la
ventana de inicio de siete días del timeout de una fase ya iniciada. Si vence, CP conserva la versión,
los nodos vuelven hacia ella y la actualización queda Failed.

Presupuesto Drift cero o do-not-disrupt del nodo pueden bloquear. PDB/anotaciones Pod retrasan
hasta TerminationGracePeriod, no indefinidamente. La cancelación es de mejor esfuerzo durante
la fase de nodos; interrupciones iniciadas pueden terminar. No puede cancelarse tras comenzar rollback de CP.

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

Tras cancelar, los nodos convergen a la versión actual del CP. Un timeout IaC no detiene AWS,
y rollback de CloudFormation no equivale a rollback automático Kubernetes. Reconcilie versiones
reales/deseadas de IaC después de cambios CLI/API.

## 6. Blue/green

Use state/identidad distintos para Green y deje DNS/NLB/DB compartidos fuera del borrado de Blue.
Registre mediante [GitOps multiclúster](./04-gitops-multi-cluster.md) con endpoint/CA reales,
identidad de carga, assume-role, entradas EKS y RBAC. Aplique el Secret de clúster al contexto Hub, no Green.

Este ApplicationSet selecciona solo Green sin sync automático. Prepare AppProject/namespace,
repositorio y revisión aprobada. Sustituya URL/SHA y controle activación simultánea de workers,
consumidores y CronJobs. preserveResourcesOnDeletion protege cargas si un selector elimina una
Application generada. Conservar no transfiere gestión; planifique propiedad GitOps estable antes del cambio.

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

Para volver a una revisión, restaure Git aprobado y sincronice. argocd app rollback usa ID del
historial, no SHA. Sync automático o estado ApplicationSet podrían volver a cambiarlo.

### Probar Green directamente

Running y TCP no demuestran DB, mensajes o readiness. Use ruta directa Green conservando
SNI/Host del servicio y validación del certificado. El hostname AWS del NLB no es el TLS de la app.
Para un Service que realmente sirve HTTPS en 443, use otro terminal:

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

En otro terminal use hostname, ruta y contrato de respuesta reales.

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### Pesos NLB

Los grupos ponderados NLB están soportados. Pesos relativos 0–999 no necesitan sumar 100.
Son proporciones esperadas de conexiones nuevas, no solicitudes, bytes o sesiones exactos.
Registre destinos sanos en TG distintos por clúster. Véase [infraestructura avanzada](./02-infrastructure-advanced.md)
para TGB, tipos y grupos/red.

Los cambios ordinarios afectan conexiones nuevas; peso cero puede cerrar las existentes pronto.
No es drenaje sin interrupciones: pruebe duración, reintentos y sesiones. TCP/UDP/TCP_UDP
admiten afinidad de TG; TLS no. La afinidad forward TCP no es exclusiva de ALB.
DurationSeconds está documentado para ALB; no traslade esa garantía a NLB.

La herramienta solo genera JSON. Verifique primero protocolo del listener, VPC del TG,
protocolo/familia IP, salud y afinidad existente.

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

Fije primero las tres variables ARN. No avance porcentajes solo por tiempo. Observe SLO,
conexiones nuevas/existentes, errores y sesiones en cada etapa. Pruebe peso cero, destinos enfermos
y cross-zone sin asumir failover a otro TG. Use una ruta Service directa separada para validar Green.

### Datos y limpieza

RDS/ElastiCache externos o EFS compartido no eliminan migración de esquemas, permisos, formatos
ni escritores/consumidores concurrentes. Un filesystem compartido o un conteo SQL no demuestra
consistencia. Revise región/AZ de snapshots, StorageClass, KMS y RPO desde últimas escrituras.

Conserve Blue durante observación/recuperación acordadas y validación de datos. Un TG de peso cero
puede seguir referenciado. Borrar TGB/clúster Auto Mode afecta al ciclo TG: retire sus referencias
de listeners compartidos y revise propiedad, IaC y orden antes de limpiar. Distíngalo de grupos
externos del LB Controller autogestionado. No ejecute terraform destroy automáticamente tras mover tráfico.

Si workers ya están en clústeres separados por AZ, actualizar uno cada vez es una opción; no
convierte sus control planes EKS en una sola AZ. Valide reserva/estado de los otros y elegibilidad/
duración de rollback. La ventana de siete días no garantiza retorno instantáneo a Blue.

## 7. Validación posterior

Después de Successful, compruebe versiones, Node/Pod Ready, generaciones, DNS/red, storage,
permisos, aplicación y trabajos programados. count incluye muestras de condición/fase de valor cero.
Agregue como abajo y no transforme ausencias en cero saludable. Multiclúster necesita etiquetas reales.

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

Los recuentos de reinicios de Pods no son recuentos de reprogramación. No suponga que las métricas
del controlador Auto Mode se recopilen desde un pod Karpenter autogestionado.
Lo siguiente requiere un contrato real de etiqueta/métrica service=api.
Cero tráfico no es una tasa de errores cero saludable; rellene las series de errores ausentes con cero solo
cuando exista la serie de tráfico total y su tasa sea positiva.

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

Utilice el mismo desplazamiento para numeradores, denominadores y intervalos de histogramas al comparar el historial.
[30m] offset 1h cubre de 90 a 60 minutos antes del momento actual, no de 60 a 30 minutos.
Compare grupos equivalentes: azul/verde pueden diferir en tráfico, rutas, número de muestras y carga.
Setenta y dos horas no cubren un patrón semanal completo. Elija la duración de observación según los ciclos
de las cargas de trabajo y la ventana en la que sigue siendo posible revertir.

Use UID explícitos y provisioning completo del [capítulo de la plataforma](./09-observability-stack.md).
No presente paneles parciales como dashboard importable. Registre versiones, ID, tiempos previstos/
reales, fallos y resultados de recuperación.

La revisión comprobó casos sintéticos de preflight/espera/rutas, parsers CLI, salida GET-only Velero
y manifiestos/consultas. No ejecutó upgrades/rollback EKS, cambios NLB, snapshots/restores ni carga real.

## Referencias oficiales

- [Actualización EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Rollback EKS](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Rollback Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Actualizaciones Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [Precios EKS](https://aws.amazon.com/eks/pricing/)
- [Diferencias de versiones Kubernetes](https://kubernetes.io/releases/version-skew-policy/)
- [Obsolescencia Kubernetes](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.3](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.3)
- [Velero 1.18.2](https://github.com/velero-io/velero/releases/tag/v1.18.2)
- [Listeners NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [Anterior: Optimización de recursos](./10-resource-optimization.md) | [Contenido](./README.md) | [Siguiente: Capacidad para eventos](./12-event-capacity-planning.md) >
