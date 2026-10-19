# Actualizaciones de EKS: Auto Mode, reversión y blue/green

> **Última actualización**: 16 de octubre de 2026. Comandos comprobados el 12 de septiembre de 2026, salvo Pluto y Velero, comprobados el 16 de octubre de 2026, con AWS CLI 2.36.44, Pluto 5.24.4 y Velero 1.18.4.
> La transición del ejemplo es 1.35 → 1.36; compruebe qué versiones están realmente disponibles en su región.

Planifique conjuntamente el plano de control, los nodos, los complementos, las aplicaciones y los datos. Auto Mode y los PDB no garantizan por sí solos un servicio sin interrupciones. Compruebe la capacidad disponible, el estado Ready, la reconexión, las sesiones, el estado de los datos y la recuperación frente a sus objetivos de disponibilidad.

## 1. Versiones y responsabilidades de gestión

El proyecto Kubernetes mantiene las ramas de las tres versiones menores más recientes: 1.35–1.37 a fecha de 12 de octubre de 2026. No mantiene la versión actual y tres anteriores. Cada versión menor recibe aproximadamente 14 meses de parches, con los dos últimos meses en modo de mantenimiento. La versión 1.34 permanece en mantenimiento hasta el fin de su vida útil, el 27 de octubre de 2026. EKS tiene un ciclo independiente: normalmente 14 meses de soporte estándar y 12 meses de soporte extendido. Compruebe las fechas exactas, la política y la disponibilidad regional.

La tarifa básica habitual del plano de control de EKS es de $0.10 por hora con soporte estándar y de **$0.60 por hora en total** con soporte extendido ($0.10 + $0.50). El incremento no es de $0.60. Se cobran por separado Auto Mode, los recursos de cómputo, el almacenamiento, la red y la capacidad del plano de control aprovisionada de forma independiente.

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

`describe-addon-versions` comprueba la compatibilidad de los complementos, no las fechas de soporte del clúster. Actualice el plano de control de EKS una versión menor cada vez, sin saltarse versiones intermedias. En las versiones actualmente admitidas, kubelet no puede ser más reciente que el servidor de API. La política de Kubernetes permite hasta tres versiones menores anteriores bajo sus condiciones; esto no recomienda mantener los nodos desactualizados. Antes de la siguiente actualización, planifique alinear los nodos con el plano de control actual. Revise por separado los requisitos de los nodos administrados de EKS, Fargate, los autogestionados y los híbridos. Utilice kubectl con una diferencia máxima de una versión menor respecto al plano de control.

| Despliegue | Responsabilidad de actualización |
|---|---|
| Solo Auto Mode | El servicio administra los nodos, la red, el almacenamiento en bloques y las funciones de balanceo de carga |
| Nodos convencionales, autogestionados o híbridos | Planificar las actualizaciones de nodos, CNI, DNS, proxy, drivers y controladores |
| Clúster mixto | Conservar los complementos que necesitan los nodos ajenos a Auto Mode |
| Aplicaciones, controladores autogestionados y complementos de EKS | Validar las versiones instaladas, la configuración y los CRD |

En un clúster que utiliza solo Auto Mode, CoreDNS funciona como servicio del sistema de los nodos. Que no exista un Deployment de CoreDNS no indica por sí solo un fallo. Los clústeres mixtos deben conservar los Deployments de DNS que necesitan los otros nodos. En Auto Mode, no instale ni busque sistemáticamente los Pods aws-node, kube-proxy o del agente de Pod Identity propios de los nodos convencionales. Algunos trabajos de compatibilidad deben realizarse antes de actualizar el plano de control; por tanto, la secuencia «plano de control → todos los complementos → nodos» no se aplica a todos los casos.

| Estabilidad de la API | Política de retirada |
|---|---|
| GA | Puede declararse obsoleta, pero no eliminarse dentro de la misma versión mayor de Kubernetes |
| Beta | Se deja de servir como mínimo nueve meses o tres versiones menores después de declararse obsoleta, lo que suponga más tiempo |
| Alpha | Puede eliminarse sin un aviso previo de obsolescencia |

Las opciones de la CLI y las métricas siguen políticas distintas. Compare las guías de migración con las versiones realmente instaladas, las arquitecturas, las versiones de plataforma y los tipos de cómputo, en lugar de copiar tablas de compatibilidad antiguas.

## 2. Revisión previa a la actualización

Los insights de actualización tienen límites de cobertura y de tiempo. La guía oficial aún indica que se ha suspendido temporalmente la exigencia de `--force` para determinados problemas detectados por esos insights. Distinga esa situación del bloqueo de la reversión por ERROR o UNKNOWN, explicado más adelante. Que la API acepte una solicitud no significa que se haya completado la revisión de preparación.

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.4 distingue los códigos de salida 0 (sin problemas), 2 (API obsoleta), 3 (API eliminada) y 4 (API de sustitución no disponible en la versión de destino). No interprete todos los códigos distintos de cero como «no instalado» ni los oculte con `|| true`. Su JSON es un objeto: cuente `.items // []`, porque una respuesta sin problemas puede omitir items. `detect-all-in-cluster` también es válido. Compruebe la arquitectura y la suma de comprobación de la versión oficial.

La inspección del clúster en funcionamiento puede omitir las versiones originales de las API porque el servidor convierte los objetos. Revise Git, los manifiestos generados por Helm o Kustomize, los metadatos de las versiones, las advertencias y la auditoría de la API y los clientes reales. Ajuste también los destinos de los otros componentes de Pluto a las versiones desplegadas de Istio y cert-manager.

Esta herramienta de solo lectura compara los endpoints de EKS y del contexto de Kubernetes. Después comprueba el estado Ready de Nodes y Pods, la generación y el despliegue de los Deployments, los PDB y los complementos realmente instalados. Un kubeconfig que utilice un proxy puede tener un endpoint distinto al de EKS y requiere una revisión independiente.

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

El código de salida 0 indica que se recopilaron las comprobaciones enumeradas; 2 indica hallazgos y 1, un resultado desconocido debido a un error. El código 0 no autoriza automáticamente la actualización ni demuestra el buen funcionamiento de toda la aplicación. Aunque se anuncie una versión de un complemento, aún debe revisar su arquitectura, plataforma, tipo de cómputo y configuración.

Un PDB con maxUnavailable 1 puede no permitir ninguna interrupción si hay Pods que no están sanos o PDB que se solapan. AlwaysAllow cambia cómo se expulsan los Pods que no están sanos; no garantiza la disponibilidad.

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

No deduzca el buen funcionamiento solo a partir de la fase de un Node o del estado Running de un Pod. Distinga los Deployments con cero réplicas, los Jobs completados y los selectores vacíos de PDB. Inspeccione las condiciones ready, serving y terminating de EndpointSlice y los selectores de Service. Los Services sin selector o de tipo ExternalName no necesitan los endpoints habituales de Pods.

## 3. Validación de copia de seguridad y restauración

Las copias de seguridad administradas de EKS no permiten asumir que el cliente puede restaurar cualquier instantánea de etcd. Trate por separado Git e IaC, los objetos de Kubernetes, los datos de PV, las bases de datos externas, los permisos, las claves de cifrado y los procedimientos de recuperación. Prepare primero BackupStorageLocation de Velero, la configuración del plugin y las instantáneas CSI y los permisos de IAM. Este Schedule selecciona explícitamente production. La CLI de Backup incluye de forma predeterminada los namespaces `*`; no excluye automáticamente todo el namespace velero.

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

El estado Completed no demuestra la coherencia de la aplicación ni la recuperación de todos los volúmenes. Revise los errores y advertencias, los resultados de las instantáneas y del data mover, los volúmenes excluidos y la pausa de escrituras o replicación de la base de datos. Copiar únicamente los objetos PVC y PV no respalda toda la aplicación, sus Secrets, Services y datos. La copia del sistema de archivos requiere configurar por separado el node-agent y los volúmenes.

Velero 1.18.4 restore create no dispone de `--dry-run`. `-o yaml/json` muestra el Restore sin crearlo, pero consulta el clúster y lee el Backup. No es una operación completamente sin conexión ni una prueba de recuperación.

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

Realice restauraciones reales en un entorno de prueba aislado. Cambiar la asignación de namespaces no aísla por sí solo CronJobs, consumidores, bases de datos externas ni cambios de DNS y balanceadores. Revise quién puede escribir en el almacenamiento de copias, la región y la AZ de las instantáneas y los permisos KMS e IAM del clúster de prueba. Cuando corresponda, utilice un BackupStorageLocation de solo lectura para sincronizar. Pruebe por separado la creación del Restore, el arranque de Pods, la conexión de volúmenes, la integridad y el comportamiento de la aplicación. No elimine la copia original al limpiar la prueba.

## 4. Actualizaciones del plano de control y nodos

El ejemplo utiliza la capa existente del clúster descrita en el [capítulo de infraestructura](./01-infrastructure-setup.md). No cree un clúster duplicado en un estado nuevo ni reconstruya VPC e IAM. Revise los cambios de versión mayor del módulo y del proveedor por separado de los cambios de versión menor de Kubernetes. No mezcle los parámetros antiguos del módulo EKS v20 con los del módulo actual. Sustituya tfvars por una ruta absoluta real.

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

Si decide realizar el cambio mediante la CLI, evite modificar simultáneamente el mismo ajuste mediante IaC. El comando siguiente realiza un cambio real después de la revisión de preparación; registre el ID de la actualización.

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

El código 0 indica Successful; 1, un fallo, una cancelación o un error de consulta; y 2, que se agotó el tiempo de espera del cliente. Este último no cancela la operación de AWS: siga observando el mismo ID. Una actualización del plano de control no puede pausarse o detenerse libremente una vez iniciada. cluster-active no demuestra por sí solo que haya terminado la sustitución de nodos. Compruebe después la versión real, los nodos y las aplicaciones.

Auto Mode sustituye los nodos gradualmente después de actualizar el plano de control. El cliente no selecciona una AMI de Auto Mode mediante EC2NodeClass al2023@latest. Los nodos convencionales administrados, autogestionados e híbridos y los Pods de Fargate existentes requieren un tratamiento independiente. No todos los complementos de EKS se actualizan automáticamente: revise sus versiones y los esquemas que devuelve describe-addon-configuration. No aplique OVERWRITE de forma indiscriminada.

### Restricciones de interrupción

Los presupuestos aplicables de NodePool se combinan utilizando la restricción más estricta. 10% y 1 no significan «al menos uno». Tenga en cuenta el redondeo, los nodos en proceso de eliminación o NotReady y las programaciones en UTC. Un presupuesto programado no impide por sí solo las interrupciones fuera de su período activo.

Para pausar la sustitución voluntaria por drift, conserve y revise los presupuestos existentes, añada una política como `nodes: "0", reasons: [Drifted]` y después restaure la política original. Una anotación do-not-disrupt en los metadatos de NodePool no proporciona esa pausa. Las anotaciones de Nodes y Pods y los presupuestos no bloquean todas las interrupciones, vencimientos ni vías que utilizan el período de gracia de terminación.

| Opción de drenaje manual | Significado |
|---|---|
| `--ignore-daemonsets` | Excluye los pods DaemonSet sin eliminarlos |
| `--delete-emptydir-data` | Permite pérdida de datos emptyDir |
| `--disable-eviction` | Elimina en lugar de usar Eviction, omitiendo la protección PDB |

Los DaemonSets se ejecutan en los nodos que cumplen sus requisitos. No automatice la eliminación forzada ni la omisión de los PDB como solución general.

## 5. Reversión nativa de versión de Kubernetes

EKS permite iniciar la reversión a la versión menor anterior durante los siete días posteriores a la finalización de la actualización. Ya no es correcto afirmar que «el plano de control nunca puede volver a una versión anterior». Existen restricciones para clústeres creados en su versión actual, ventanas vencidas, actualizaciones automáticas al finalizar el soporte extendido y funciones de EKS incompatibles con el destino. Después de varias actualizaciones consecutivas, solo puede volver a la versión menor inmediatamente anterior. Si el destino está en soporte extendido, se aplican sus condiciones de política y coste.

| Componente | Tratamiento |
|---|---|
| Servidor de API y plano de control | Vuelven a la versión menor anterior de Kubernetes y a su versión de plataforma más reciente |
| Nodos de Auto Mode | El servicio ajusta primero los nodos y después revierte el plano de control |
| Grupos convencionales de nodos administrados | El usuario los ajusta primero mediante UpdateNodegroupVersion |
| Nodos autogestionados o híbridos | El usuario los sustituye primero por nodos compatibles |
| Fargate | No permite cambiar directamente a una versión anterior el kubelet de los Pods existentes; planifique por separado su sustitución y compatibilidad |
| Complementos, aplicaciones, objetos de etcd y datos de PV | No se restauran desde una instantánea histórica |

La reversión no restaura los datos ni devuelve instantáneamente el tráfico al entorno anterior. Valide la compatibilidad de las nuevas API y sus campos, los controladores y los esquemas de base de datos con la versión anterior.

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

La AWS CLI 2.36.44 utilizada en la revisión documentada admite rollback-config; la versión 2.35.11 que tenía el entorno no lo admitía. Que una CLI antigua no reconozca una opción no significa que EKS carezca de esa función. Utilice la CLI oficial actualizada o una API o SDK compatible. No existe un comando independiente aws eks rollback-cluster.

Un resultado ERROR o UNKNOWN en la preparación de la reversión bloquea la operación; WARNING es una advertencia. Force puede omitir las comprobaciones de insights, pero no los requisitos para realizar la reversión ni los controles de interrupción de Auto Mode. La configuración de referencia no utiliza force.

### Observación y cancelación de Auto Mode

Durante la reversión de los nodos, el plano de control sigue sirviendo la versión más reciente y el clúster permanece ACTIVE. Cuando los nodos cumplen los requisitos de diferencia de versiones, EKS vuelve a revisar los insights y después revierte el plano de control. Observe el ID de actualización. El tiempo de espera de los nodos es de 720 minutos de forma predeterminada y admite valores de 120–10,080 minutos. Es un límite mínimo, no un temporizador exacto. Distinga la ventana de siete días para iniciar la reversión del tiempo de espera de una fase de nodos ya iniciada. Si se agota ese tiempo, el plano de control conserva la versión actual, los nodos vuelven gradualmente hacia ella y la actualización pasa a Failed.

Un presupuesto Drift de cero o una anotación do-not-disrupt en el nodo pueden bloquear el avance. Los PDB y las anotaciones de Pod pueden retrasar la interrupción hasta TerminationGracePeriod, pero no impedirla permanentemente. Durante la fase de nodos puede solicitarse la cancelación sin garantía de detener todas las operaciones: las interrupciones ya iniciadas pueden completarse. La cancelación deja de estar disponible cuando comienza la reversión del plano de control.

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

Después de la cancelación, los nodos vuelven gradualmente hacia la versión actual del plano de control. Que una herramienta IaC agote su tiempo de espera no detiene la operación de AWS. Revertir una pila de CloudFormation tampoco revierte automáticamente la versión de Kubernetes. Tras los cambios mediante CLI o API, reconcilie la versión real con la prevista en IaC.

## 6. Blue/green

Utilice un estado y una identidad distintos para Green. Mantenga la administración compartida de DNS, NLB y la base de datos fuera del alcance de eliminación de Blue. Registre el clúster mediante los procedimientos de [GitOps multiclúster](./04-gitops-multi-cluster.md), utilizando el endpoint y la CA reales, la identidad de la carga, assume-role, las entradas de acceso de EKS y RBAC de Kubernetes. Aplique el Secret del clúster al contexto Hub, no a Green.

Este ApplicationSet selecciona únicamente Green y no activa la sincronización automática. Prepare el AppProject y el namespace de producción, el repositorio y la revisión aprobada. Sustituya los marcadores de URL y SHA y controle la activación simultánea de workers, consumidores y CronJobs. preserveResourcesOnDeletion protege las cargas de trabajo si un cambio de selector elimina una Application generada. Conservar los recursos no transfiere su gestión: planifique quién los administrará mediante GitOps antes de cambiar los colores o los selectores.

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

Para volver a una revisión de Git, restaure el estado aprobado en Git y sincronice. argocd app rollback recibe un ID del historial de despliegue, no un SHA. La sincronización automática o el estado deseado del ApplicationSet podrían volver a cambiarlo.

### Probar Green directamente

Que los Pods estén en ejecución y exista conectividad TCP no demuestra el correcto funcionamiento de la base de datos, la mensajería ni la preparación de la aplicación. Acceda directamente a Green y conserve el SNI, el encabezado Host y la validación del certificado del nombre del servicio. El nombre de AWS del NLB no es el nombre TLS de la aplicación. Para un Service que realmente sirva HTTPS en el puerto 443, utilice otra terminal:

```bash
kubectl --context green -n production port-forward --address 127.0.0.1 svc/api 18443:443
```

En otra terminal, use el nombre de host, la ruta y el contrato de respuesta reales.

```bash
DOCS_SERVICE_HOST="api.example.com"
DOCS_HTTP_CODE=$(curl --silent --show-error --fail --connect-timeout 5 --max-time 15 \
  --connect-to "$DOCS_SERVICE_HOST:443:127.0.0.1:18443" \
  --output /tmp/green-health-response --write-out '%{http_code}' \
  "https://$DOCS_SERVICE_HOST/health/ready") || exit 1
test "$DOCS_HTTP_CODE" = "200" || exit 1
```

### Pesos de NLB

NLB admite grupos de destino con pesos. Los pesos relativos van de 0 a 999 y no tienen que sumar 100. Indican la proporción esperada de **conexiones nuevas**, no un reparto exacto de solicitudes, bytes ni sesiones existentes. Registre destinos sanos en grupos independientes para cada clúster. Consulte [infraestructura avanzada](./02-infrastructure-advanced.md) para TargetGroupBinding (TGB), el tipo de destino, la red y los grupos de seguridad.

Los cambios normales de peso afectan a las conexiones nuevas. Sin embargo, fijar el peso en cero puede cerrar conexiones existentes después de un breve período; no garantiza un drenaje sin interrupciones. Pruebe la duración de las conexiones, los reintentos y las sesiones. TCP, UDP y TCP_UDP admiten afinidad de grupo de destino; los listeners TLS no. La afinidad de reenvío TCP no es exclusiva de ALB. La API documenta DurationSeconds para ALB: no atribuya esa misma garantía de duración a NLB.

Esta herramienta solo genera JSON. Antes, compruebe el protocolo real del listener, la VPC de los grupos de destino, el protocolo y la familia IP, el estado de los destinos y la afinidad existente.

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

Defina primero las tres variables de ARN. No avance entre porcentajes de tráfico solo porque transcurra un tiempo. Observe en cada etapa los SLO, las conexiones nuevas y existentes, los errores y las sesiones. Pruebe el peso cero, los destinos que no están sanos y el comportamiento entre zonas, sin dar por hecho que el tráfico pasará a otro grupo de destino. Para validar Green detrás de un NLB compartido, utilice una ruta directa e independiente al Service.

### Datos y limpieza

Utilizar RDS o ElastiCache externos o EFS compartido no elimina la necesidad de migrar esquemas, permisos y formatos de caché ni de coordinar escritores y consumidores simultáneos. Un sistema de archivos compartido o un único recuento SQL no demuestran la coherencia de los datos. Compruebe la región y AZ de las instantáneas, la clase de almacenamiento, KMS y el RPO respecto a las últimas escrituras.

Conserve Blue durante el período acordado de observación y recuperación y mientras verifica la compatibilidad de los datos. Un listener puede seguir referenciando un grupo de destino con peso cero. Eliminar un TGB o el clúster de Auto Mode afecta al ciclo de vida del grupo asociado. Retire primero las referencias a los grupos de Blue de los listeners compartidos y revise después la administración de los recursos, IaC y el orden de eliminación. Distinga este caso de los grupos externos administrados con AWS Load Balancer Controller autogestionado. No ejecute terraform destroy automáticamente justo después de mover el tráfico.

Si los workers ya se ejecutan en clústeres separados por AZ, puede actualizar un clúster cada vez. Esto no convierte el plano de control de cada clúster de EKS en un plano de una sola AZ. Valide la capacidad disponible y la compatibilidad del estado en los demás clústeres, además de los requisitos y la duración de la reversión nativa. La ventana de siete días no garantiza un retorno inmediato a Blue.

## 7. Validación posterior a la actualización

Después de que la actualización alcance Successful, compruebe las versiones reales, el estado Ready de Nodes y Pods, las generaciones de los controladores, DNS y los recorridos de red, el almacenamiento, los permisos, el funcionamiento de la aplicación y las tareas programadas. count también cuenta muestras con valor cero de condiciones y fases. Agregue los valores como se muestra abajo y no interprete la ausencia de observaciones como un cero que indique buen funcionamiento. Para varios clústeres, la recopilación debe incluir etiquetas reales de clúster.

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

El número de reinicios de Pods no indica cuántas veces se han programado en otro nodo. No dé por hecho que puede obtener las métricas del controlador de Auto Mode de un Pod autogestionado de Karpenter. La consulta siguiente necesita métricas y etiquetas que realmente incluyan service=api. Sin tráfico, una tasa de errores cero no demuestra buen funcionamiento. Complete con cero una serie de errores ausente solo si existe la serie de tráfico total y su tasa es positiva.

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

Al comparar con el historial, utilice el mismo offset en numeradores, denominadores y buckets. [30m] offset 1h cubre entre 90 y 60 minutos antes del momento actual, no entre 60 y 30. Compare grupos equivalentes: Blue y Green pueden recibir distinto tráfico, rutas, cantidades de muestras y carga. Setenta y dos horas no cubren un ciclo semanal completo. Elija el período de observación según los ciclos de la carga y la ventana en la que sea posible iniciar la reversión.

Utilice los UID explícitos y el aprovisionamiento completo de dashboards del [capítulo de la plataforma de observabilidad](./09-observability-stack.md). Un fragmento YAML o JSON de un panel no es un dashboard completo que pueda importarse. Registre las versiones anteriores y posteriores, los ID de actualización, los tiempos previstos y reales, los fallos y los resultados de recuperación.

La revisión documentada comprobó casos sintéticos de preparación, espera y enrutamiento, los analizadores oficiales de la CLI, la salida de Velero mediante consultas GET y los manifiestos y consultas. No realizó actualizaciones ni reversiones reales de EKS, cambios de NLB, instantáneas, restauraciones ni pruebas de carga de aplicaciones.

## Referencias oficiales

- [Actualización de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Reversión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Reversión de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Actualizaciones de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [Precios de EKS](https://aws.amazon.com/eks/pricing/)
- [Diferencias de versiones admitidas por Kubernetes](https://kubernetes.io/releases/version-skew-policy/)
- [Historial de versiones de Kubernetes](https://kubernetes.io/releases/)
- [Parches y período de soporte de Kubernetes](https://kubernetes.io/releases/patch-releases/)
- [Política de retirada de API de Kubernetes](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.4](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.4)
- [Velero 1.18.4](https://github.com/velero-io/velero/releases/tag/v1.18.4)
- [Listeners de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [Anterior: Optimización de recursos](./10-resource-optimization.md) | [Contenido](./README.md) | [Siguiente: Planificación de capacidad para eventos](./12-event-capacity-planning.md) >
