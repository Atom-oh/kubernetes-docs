# Actualizaciones de EKS: Auto Mode, reversión y blue/green

> **Última actualización**: 12 de octubre de 2026. Comandos comprobados el 12 de septiembre de 2026 con AWS CLI 2.36.44, Pluto 5.24.3 y Velero 1.18.2.
> La transición de ejemplo es 1.35 → 1.36; descubra la disponibilidad regional real.

Planifique juntos el plano de control, los nodos, los complementos, las aplicaciones y los datos.
Auto Mode y los PDB por sí solos no garantizan un servicio ininterrumpido. Valide la capacidad de reserva,
la preparación, el comportamiento de reconexión, las sesiones, el estado y la recuperación frente a los objetivos de disponibilidad.

## 1. Versiones y responsabilidades de gestión

Kubernetes upstream mantiene ramas de lanzamiento para las tres versiones menores más recientes
(1.35–1.37 al 12 de octubre de 2026), no la versión actual más las tres versiones anteriores.
Cada versión menor recibe aproximadamente 14 meses de parches, los dos últimos meses en modo de mantenimiento; la 1.34 está en
modo de mantenimiento hasta el fin de su vida útil el 27 de octubre de 2026.
EKS tiene un ciclo de vida independiente: por lo general, 14 meses de
soporte estándar y 12 meses de soporte extendido. Compruebe las fechas exactas, la política y la disponibilidad regional.

La tarifa básica ordinaria del plano de control de EKS es de $0.10/hora con soporte estándar y un total de
$0.60/hora con soporte extendido ($0.10 + $0.50). La tarifa adicional no es de $0.60.
Auto Mode, cómputo, almacenamiento, redes y capacidad del plano de control aprovisionada por separado tienen coste adicional.

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

`describe-addon-versions` comprueba la compatibilidad de complementos, no las fechas de soporte del clúster.
Avance un plano de control de EKS una versión menor a la vez, sin omitir las intermedias.
Para las versiones actuales compatibles, kubelet no puede ser más reciente que el servidor de API y la política upstream
permite hasta tres versiones menores anteriores bajo sus condiciones. Eso no es una recomendación para mantener
los nodos atrasados. Planifique alinear los nodos con el plano de control actual antes de la siguiente actualización,
y compruebe por separado los requisitos de nodos gestionados por EKS, Fargate, autogestionados e Hybrid.
Use kubectl a no más de una versión menor del plano de control.

| Despliegue | Responsabilidad de actualización |
|---|---|
| Auto Mode puro | Nodos, redes, almacenamiento en bloques y capacidades de LB gestionados por el servicio |
| Nodos ordinarios/autogestionados/Hybrid | Planificar actualizaciones de nodos, CNI, DNS, proxy, drivers y controladores |
| Clúster mixto | Conservar los complementos necesarios para nodos que no son Auto |
| Aplicaciones, controladores autogestionados y complementos de EKS | Validar las versiones instaladas, la configuración y los CRD |

Auto Mode puro usa CoreDNS como servicio de sistema de nodos. La ausencia de un Deployment de CoreDNS por sí sola no es
un fallo; los clústeres mixtos deben conservar los Deployment de DNS requeridos por otros nodos.
No instale ni busque incondicionalmente pods aws-node/kube-proxy/Pod Identity agent de nodos ordinarios
en Auto Mode. La compatibilidad puede requerir trabajo antes de la actualización del plano de control, por lo que
«plano de control → cada complemento → nodos» no es universal.

| Estabilidad de API | Política de obsolescencia |
|---|---|
| GA | Puede quedar obsoleta, pero no eliminarse dentro de la misma versión mayor de Kubernetes |
| Beta | Eliminación del servicio después de al menos nueve meses o tres versiones menores tras la obsolescencia, lo que sea más largo |
| Alpha | Se puede eliminar sin aviso previo de obsolescencia |

Las políticas de indicadores de CLI y métricas difieren. Compare las guías de migración y las versiones realmente instaladas,
arquitecturas, versiones de plataforma y tipos de cómputo en vez de copiar tablas de compatibilidad antiguas.

## 2. Revisión previa a la actualización

Los insights de actualización tienen límites de tiempo y cobertura. La guía oficial de actualización sigue indicando una
suspensión temporal de exigir `--force` para determinados problemas de insights de actualización.
Distinga esto del bloqueo ERROR/UNKNOWN de preparación para reversión que se indica más abajo.
La aceptación de la API no es una revisión de preparación completada.

```bash
aws eks list-insights --cluster-name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --filter "{\"categories\":[\"UPGRADE_READINESS\"],\"kubernetesVersions\":[\"$DOCS_TARGET\"]}"
pluto detect-files -d manifests/ --target-versions "k8s=v${DOCS_TARGET}.0" -o json > pluto-report.json
pluto detect-helm --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
pluto detect-api-resources --target-versions "k8s=v${DOCS_TARGET}.0" -o wide
```

Pluto 5.24.3 distingue salida 0 (limpio), 2 (obsoleto) y 3 (eliminado).
No convierta todo resultado distinto de cero en «no instalado» ni lo oculte con `|| true`.
Su JSON es un objeto: cuente `.items // []`; una respuesta limpia puede omitir items.
`detect-all-in-cluster` también es válido. Compruebe la arquitectura y la suma de comprobación de la versión oficial.

El descubrimiento en vivo puede omitir las versiones originales de API porque el servidor de API convierte objetos.
Revise Git, Helm/Kustomize renderizado, metadatos de lanzamiento, advertencias/auditoría de API y clientes reales.
Alinee también los otros objetivos de componentes de Pluto con las versiones de Istio/cert-manager desplegadas.

Esta herramienta de solo lectura compara los endpoints de EKS y kubecontext, y después comprueba la preparación de Node/Pod,
la generación/despliegue de Deployment, los PDB y los complementos realmente instalados.
Un kubeconfig proxy puede diferir del endpoint directo de EKS y requiere una revisión independiente.

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

La salida 0 significa que se recopilaron las comprobaciones enumeradas, 2 significa hallazgos y 1 significa un resultado desconocido
debido a un error. Cero no es una aprobación automática de actualización ni prueba de la salud completa de la aplicación.
Las versiones de complementos anunciadas todavía necesitan revisión de arquitectura/plataforma/tipo de cómputo y configuración.

Un PDB con maxUnavailable 1 aún puede permitir cero interrupciones debido a pods no saludables o
PDB superpuestos. AlwaysAllow cambia el comportamiento de expulsión de pods no saludables; no garantiza la disponibilidad.

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

No infiera la salud solo de la fase Node o Pod Running. Distinga los Deployment con cero réplicas,
los Job completados y los selectores PDB vacíos. Inspeccione las condiciones ready/serving/terminating de EndpointSlice
y los selectores de Service; los Service sin selector/ExternalName no requieren endpoints Pod ordinarios.

## 3. Validación de copia de seguridad y restauración

Las copias de seguridad administradas de EKS no implican restauración controlada por el cliente desde snapshots de etcd arbitrarios.
Separe Git/IaC, objetos Kubernetes, datos PV, bases de datos externas, permisos, claves de cifrado
y procedimientos de recuperación. Prepare primero BackupStorageLocation de Velero, la configuración de plugin/snapshot de CSI
e IAM. Este Schedule selecciona explícitamente production.
La CLI Backup predeterminada incluye espacios de nombres `*`; no excluye automáticamente todo velero.

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

Completed no demuestra la consistencia de la aplicación ni la recuperación de cada volumen.
Revise errores/advertencias, resultados de snapshot/data-mover, volúmenes excluidos y la pausa/replicación de la base de datos.
Los objetos PVC/PV por sí solos no son una copia de seguridad completa de aplicación/Secret/Service/datos.
La copia de seguridad de filesystem requiere una configuración independiente de node-agent y volumen.

Velero 1.18.2 restore create no tiene `--dry-run`.
`-o yaml/json` imprime el Restore sin crearlo, pero realiza descubrimiento/lecturas de Backup.
No está completamente desconectado ni es una prueba de recuperación.

```bash
velero --kubecontext "$DOCS_CONTEXT" restore create review-restore \
  --from-backup "$DOCS_BACKUP" --include-namespaces production \
  --namespace-mappings production:restore-test -o yaml > restore-plan.yaml
```

Realice restauraciones reales en un entorno de prueba aislado. El mapeo de espacio de nombres por sí solo no
aísla CronJobs, consumidores, bases de datos externas ni cambios DNS/LB.
Revise la propiedad de escritura del almacenamiento de copias de seguridad, la región/AZ de snapshot y KMS/IAM para el clúster de prueba.
Use un BackupStorageLocation de solo lectura para la sincronización cuando corresponda.
Pruebe por separado la creación de restauración, inicio de Pod, conexión de volumen, integridad y comportamiento de la aplicación.
No elimine la copia de seguridad original durante la limpieza de prueba.

## 4. Actualizaciones del plano de control y nodos

Esto usa la capa de clúster existente del [capítulo de infraestructura](./01-infrastructure-setup.md).
No cree un clúster duplicado en un estado nuevo ni reconstruya VPC/IAM.
Revise por separado los cambios mayores de módulo/proveedor de los cambios menores de Kubernetes.
No mezcle entradas antiguas del módulo EKS v20 con el módulo actual.
Reemplace tfvars con una ruta de archivo absoluta real.

```bash
DOCS_TFVARS="/absolute/path/to/production.cluster.tfvars.json"
terraform -chdir=terraform/02-cluster plan \
  -var-file="$DOCS_TFVARS" -var="cluster_version=$DOCS_TARGET" -out=upgrade.tfplan
terraform -chdir=terraform/02-cluster show upgrade.tfplan
# Apply the reviewed saved plan:
terraform -chdir=terraform/02-cluster apply upgrade.tfplan
```

Si elige cambios de CLI, evite cambios simultáneos de IaC en la misma configuración.
El siguiente comando realiza un cambio real después de la revisión de preparación. Registre su ID de actualización.

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

La salida 0 significa Successful, 1 significa fallo/cancelación/error de consulta y 2 significa un tiempo de espera del cliente.
El tiempo de espera no cancela AWS; reanude la observación del mismo ID.
No se puede pausar/detener arbitrariamente una actualización del plano de control después de que comienza.
cluster-active por sí solo no establece la finalización del reemplazo de nodos.
Vuelva a comprobar la versión real, los nodos y las aplicaciones después.

Auto Mode reemplaza nodos de forma incremental después de la actualización del plano de control.
Los clientes no seleccionan una AMI de Auto Mode a través de EC2NodeClass al2023@latest.
Los nodos ordinarios gestionados/autogestionados/Hybrid y los pods Fargate existentes necesitan tratamiento independiente.
No todos los complementos de EKS se actualizan automáticamente. Revise versiones y esquemas de configuración
desde describe-addon-configuration; no aplique indiscriminadamente OVERWRITE.

### Restricciones de interrupción

Los presupuestos NodePool aplicables se combinan mediante la restricción más estricta.
10% y 1 no significan «al menos uno». Considere el redondeo, los nodos eliminados/NotReady y las programaciones UTC.
Un presupuesto programado por sí solo no prohíbe la interrupción fuera de su ventana activa.

Para pausar la desviación voluntaria, conserve/revise los presupuestos existentes, agregue una política como
`nodes: "0", reasons: [Drifted]`, y luego restaure la política original.
Una anotación do-not-disrupt en los metadatos de NodePool no es ese mecanismo de pausa.
Las anotaciones Node/Pod y los presupuestos no impiden todas las rutas de interrupción, caducidad o periodo de gracia de terminación.

| Opción de drenaje manual | Significado |
|---|---|
| `--ignore-daemonsets` | Excluye los pods DaemonSet sin eliminarlos |
| `--delete-emptydir-data` | Permite pérdida de datos emptyDir |
| `--disable-eviction` | Elimina en lugar de usar Eviction, omitiendo la protección PDB |

DaemonSets se ejecutan en nodos aptos. No automatice la eliminación forzada/omisión de PDB como solución genérica.

## 5. Reversión nativa de versión de Kubernetes

EKS permite iniciar una reversión a la versión menor anterior dentro de los siete días posteriores a la finalización de la actualización.
«Los planos de control nunca pueden revertirse» ya no es correcto.
Las restricciones incluyen clústeres creados en su versión actual, una ventana vencida, actualizaciones automáticas
al final del soporte extendido y características de EKS incompatibles con el objetivo.
Después de actualizaciones consecutivas, solo la versión menor inmediatamente anterior es elegible.
Los objetivos de soporte extendido requieren las condiciones de política y coste correspondientes.

| Componente | Tratamiento |
|---|---|
| Servidor de API/plano de control | Versión menor anterior de Kubernetes y su última versión de plataforma |
| Nodos Auto Mode | El servicio ajusta primero los nodos y luego revierte el plano de control |
| Grupos de nodos gestionados ordinarios | El usuario los ajusta primero con UpdateNodegroupVersion |
| Nodos autogestionados/Hybrid | El usuario primero los reemplaza por nodos compatibles |
| Fargate | Sin degradación directa de los kubelet de Pod existentes; planifique reemplazo/compatibilidad por separado |
| Complementos, aplicaciones, objetos etcd y datos PV | No se restauran desde un snapshot histórico |

Esto no es restauración de datos ni una reversión instantánea del tráfico.
Valide la compatibilidad de nuevas API/campos, controladores y esquemas de base de datos con la versión anterior.

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

La CLI 2.36.44 probada admite rollback-config; la 2.35.11 anterior del entorno no lo admitía.
No confunda una opción desconocida de una CLI antigua con la ausencia de la capacidad de EKS.
Use la CLI oficial actualizada o una API/SDK compatible. No existe un comando independiente aws eks rollback-cluster.

La preparación para reversión ERROR/UNKNOWN bloquea la operación; WARNING es informativo.
Force puede omitir comprobaciones de insights, pero no los controles de elegibilidad ni de interrupción de Auto Mode.
La línea de base no usa force.

### Observación y cancelación de Auto Mode

Durante la reversión de nodos, el plano de control continúa sirviendo la versión más nueva y el estado del clúster permanece
ACTIVE. EKS vuelve a comprobar los insights después de que los nodos cumplen los requisitos de desfase del objetivo y luego revierte el CP.
Observe el ID de actualización. El tiempo de espera de nodos predeterminado es de 720 minutos, con un rango de 120–10,080 minutos.
Es un límite mínimo, no un temporizador exacto. Distinga la ventana de inicio de siete días del tiempo de espera
de una fase de nodos ya iniciada. Al agotarse el tiempo, el CP permanece en la versión actual, los nodos regresan gradualmente
hacia ella y la actualización pasa a Failed.

Un presupuesto Drift de cero o node do-not-disrupt puede bloquear el progreso. Los PDB/anotaciones Pod pueden retrasar
la interrupción hasta TerminationGracePeriod, pero no impedirla permanentemente.
La cancelación de mejor esfuerzo está disponible durante la fase de nodos, aunque las interrupciones individuales
que ya están en curso pueden finalizar. La cancelación no está disponible tras iniciar la reversión del CP.

```bash
aws eks cancel-update --name "$DOCS_CLUSTER" --region "$DOCS_REGION" \
  --update-id "$DOCS_ROLLBACK_ID"
```

Después de la cancelación, los nodos regresan gradualmente hacia la versión actual del CP.
Un tiempo de espera de IaC no detiene la operación de AWS, y la reversión de una pila CloudFormation no es una reversión automática
de versión de Kubernetes. Reconcilie las versiones reales y previstas de IaC después de los cambios de CLI/API.

## 6. Blue/green

Use estado/identidad distintos para Green y mantenga la propiedad compartida de DNS/NLB/base de datos fuera del alcance
de eliminación de Blue. Registre mediante los procedimientos de [GitOps multiclúster](./04-gitops-multi-cluster.md)
para endpoint/CA reales, identidad de carga de trabajo, assume-role, entradas de acceso EKS y RBAC de Kubernetes.
Aplique el Secret del clúster al contexto Hub, no a Green.

Este ApplicationSet selecciona solo Green sin sincronización automatizada.
Prepare el AppProject/espacio de nombres de producción, el repositorio y la revisión aprobada.
Reemplace los marcadores URL/SHA y controle la activación simultánea de workers, consumidores y CronJobs.
preserveResourcesOnDeletion protege las cargas de trabajo si un cambio de selector elimina una Application generada.
La preservación no es una transferencia de gestión; planifique la propiedad de GitOps en estado estable antes de cambiar colores/selectores.

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

Para revertir una revisión Git, restaure el estado Git aprobado y sincronice.
argocd app rollback toma un ID de historial de despliegue, no un SHA.
De lo contrario, el estado deseado de sincronización automatizada/ApplicationSet puede cambiarlo de nuevo.

### Probar Green directamente

Los pods en ejecución y la conectividad TCP no demuestran el comportamiento de base de datos/mensajes/preparación.
Use una ruta Green directa y conserve el SNI/Host y la validación de certificado del nombre de host del servicio.
El nombre de host AWS del NLB no es el nombre de host TLS de la aplicación.
Para un Service que realmente sirve HTTPS en 443, use una terminal independiente:

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

Los grupos de destino ponderados de NLB son compatibles. Los pesos relativos van de 0 a 999 y no necesitan sumar 100.
Expresan proporciones esperadas de conexiones nuevas, no solicitudes, bytes ni sesiones existentes exactas.
Registre destinos saludables en TG independientes para cada clúster.
Consulte [infraestructura avanzada](./02-infrastructure-advanced.md) para TGB, tipo de destino y grupos de red/seguridad.

Los cambios de peso ordinarios afectan conexiones nuevas, pero establecer el peso en cero puede cerrar conexiones existentes
después de un breve periodo. Esto no es drenaje ininterrumpido; pruebe duración, reintentos y sesiones.
TCP/UDP/TCP_UDP admiten afinidad de grupo de destino; los listeners TLS no.
La afinidad de reenvío TCP no es una característica exclusiva de ALB.
La API documenta DurationSeconds para ALB; no copie esa garantía de duración a NLB.

Esta herramienta solo genera JSON. Verifique primero el protocolo real del listener y la VPC de grupo de destino,
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

Establezca primero las tres variables ARN. No avance porcentajes basándose solo en temporizadores.
Observe SLO, conexiones nuevas/existentes, errores y sesiones en cada etapa.
Pruebe peso cero, destinos no saludables y comportamiento entre zonas en lugar de asumir failover a otro TG.
Use una ruta Service directa independiente al validar Green detrás de un NLB compartido.

### Datos y limpieza

RDS/ElastiCache externos o EFS compartido no eliminan el trabajo de migración de esquemas, permisos, formato de caché o
de escritores/consumidores simultáneos. Un filesystem compartido o un conteo SQL no establece
consistencia. Compruebe región/AZ de snapshot, clase de almacenamiento, KMS y RPO desde las últimas escrituras.

Conserve Blue durante el periodo acordado de observación/recuperación y la verificación de compatibilidad de datos.
Un TG con peso cero aún puede ser referenciado por un listener.
La eliminación de TGB/clúster de Auto Mode afecta el ciclo de vida del TG asociado. Elimine las referencias de TG Blue
de listeners compartidos y luego revise la propiedad, IaC y el orden de eliminación antes de la limpieza.
Distinga esto de la propiedad de TG externo de LB Controller autogestionado.
No ejecute automáticamente terraform destroy inmediatamente después de cambiar el tráfico.

Si los workers ya se ejecutan en clústeres separados por AZ, actualizar un clúster a la vez es una opción.
Eso no convierte cada plano de control de EKS en una sola AZ.
Valide la capacidad de reserva/compatibilidad de estado de otros clústeres y la elegibilidad/duración de reversión nativa.
La ventana de siete días no garantiza una reversión instantánea a Blue.

## 7. Validación posterior a la actualización

Después de que la actualización sea Successful, verifique las versiones reales, Node/Pod Ready, generaciones de controladores,
rutas DNS/red, almacenamiento, permisos, comportamiento de aplicación y trabajo programado.
count también cuenta muestras de condición/fase con valor cero. Agregue los valores como se indica a continuación y no
convierta observaciones ausentes en cero saludable. Varios clústeres necesitan etiquetas de clúster reales en la recopilación.

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

Los conteos de reinicios de Pod no son conteos de reprogramación. No asuma que las métricas de controladores de Auto Mode
se recopilan desde un pod Karpenter autogestionado.
Lo siguiente requiere un contrato real de etiqueta/métrica service=api.
El tráfico cero no es una tasa de error cero saludable; complete las series de errores ausentes con cero solo cuando
la serie de tráfico total exista y su tasa sea positiva.

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

Use el mismo offset para numeradores, denominadores y buckets al comparar el historial.
[30m] offset 1h cubre de 90 a 60 minutos antes de ahora, no de 60 a 30 minutos.
Compare cohortes equivalentes: blue/green puede diferir en tráfico, rutas, conteos de muestras y carga.
Setenta y dos horas no cubren un patrón semanal completo. Elija la duración de observación a partir de los ciclos de carga de trabajo
y de la ventana de elegibilidad de reversión.

Use los UID explícitos y el aprovisionamiento completo de dashboard del [capítulo de stack](./09-observability-stack.md).
No presente YAML/JSON parcial de panel como un dashboard completo importable.
Registre las versiones antes/después, los ID de actualización, la planificación/tiempo real, los fallos y los resultados de recuperación.

Esta revisión comprobó casos sintéticos de preflight/espera/enrutamiento, analizadores de CLI oficiales, comportamiento
de salida solo GET de Velero y manifiestos/consultas. No ejecutó actualizaciones/reversiones reales de EKS, cambios de NLB,
snapshots/restauraciones ni pruebas de carga de aplicaciones.

## Referencias oficiales

- [Actualización de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Reversión de EKS](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Reversión de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html)
- [Actualizaciones de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-upgrade.html)
- [Precios de EKS](https://aws.amazon.com/eks/pricing/)
- [Desfase de versiones de Kubernetes](https://kubernetes.io/releases/version-skew-policy/)
- [Historial de versiones de Kubernetes](https://kubernetes.io/releases/)
- [Lanzamientos de parches y periodo de soporte de Kubernetes](https://kubernetes.io/releases/patch-releases/)
- [Política de obsolescencia de Kubernetes](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Pluto 5.24.3](https://github.com/FairwindsOps/pluto/releases/tag/v5.24.3)
- [Velero 1.18.2](https://github.com/velero-io/velero/releases/tag/v1.18.2)
- [Listeners de NLB](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)

---

< [Anterior: Optimización de recursos](./10-resource-optimization.md) | [Contenido](./README.md) | [Siguiente: Planificación de capacidad para eventos](./12-event-capacity-planning.md) >
