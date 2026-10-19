# Actualizaciones de Amazon EKS

> **Última actualización**: 12 de octubre de 2026

Mantener actualizado el clúster de Amazon EKS es importante para la seguridad, la estabilidad y el aprovechamiento de nuevas funciones. Este documento presenta estrategias, prácticas recomendadas y guías paso a paso para actualizar clústeres de EKS de forma segura.

Estos son procedimientos revisados por los responsables; en esta auditoría no se ejecutó ninguna actualización. Use una cuenta, una región y un contexto de Kubernetes explícitos, registre las versiones de origen y destino aprobadas y los ID de actualización, y valide el comportamiento de las aplicaciones. No ejecute todos los ejemplos alternativos de forma consecutiva sobre los mismos recursos. El análisis sintáctico local y las simulaciones no demuestran que algo esté listo para producción.

## Tabla de contenido

1. [Descripción general de las actualizaciones de EKS](#eks-upgrade-overview)
2. [Planificación y preparación de la actualización](#upgrade-planning-and-preparation)
3. [Actualización del plano de control de EKS](#eks-control-plane-upgrade)
4. [Actualización del grupo de nodos](#node-group-upgrade)
5. [Actualización de complementos](#add-on-upgrade)
6. [Validación y solución de problemas de la actualización](#upgrade-validation-and-troubleshooting)
7. [Automatización de actualizaciones](#upgrade-automation)
8. [Prácticas recomendadas para las actualizaciones](#upgrade-best-practices)

## Descripción general de las actualizaciones de EKS {#eks-upgrade-overview}

![Diagrama de árbol de los cuatro pilares de una actualización de EKS: política de administración de versiones, los componentes que se actualizan (plano de control, grupos de nodos, complementos y componentes autoadministrados), la ruta de actualización de una versión secundaria a la vez frente al salto de versión no admitido y el orden de actualización en cinco pasos.](../.gitbook/assets/en-eks-08-eks-upgrades-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-0.html)

### Administración de versiones de EKS

EKS usa la numeración de versiones de Kubernetes y cuenta con su propio calendario de lanzamientos y soporte. Cada versión secundaria recibe **14 meses de soporte estándar**, seguidos de **12 meses de soporte extendido** con un cargo adicional. AWS anuncia el fin del soporte estándar con al menos 60 días de anticipación. Consulte el [catálogo de versiones y el calendario de soporte de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html); una versión publicada por el proyecto de Kubernetes no está disponible automáticamente en EKS. Evite suponer que existe un “mínimo de cuatro versiones” fijo o considerar que 14 meses representan todo el ciclo de soporte.

### Anuncios recientes sobre actualizaciones de EKS (2026)

- **Kubernetes 1.37 disponible (1 de octubre de 2026)**: EKS 1.37 ya es un destino admitido. En Auto Mode, los NodePools personalizados recién creados que omiten una política de consolidación tienen `Balanced` como valor predeterminado; los grupos integrados `general-purpose` y `system` también usan `Balanced`. Los montajes de volúmenes SELinux son estables y están habilitados de forma predeterminada para las configuraciones compatibles de CSI y de los Pods. Antes de actualizar, revise el comportamiento previsto de los NodePool y los requisitos de SELinux/CSI para las cargas de trabajo que comparten volúmenes con distintas etiquetas. Consulte la sección de Kubernetes 1.37 en las [notas de la versión de soporte estándar de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html) y el [calendario de soporte](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html).
- **Compatibilidad con la reversión de versiones de Kubernetes (1 de julio de 2026)**: Si una actualización causa problemas, ahora puede revertir el plano de control a la versión secundaria anterior en un plazo de 7 días. Antes, EKS ejecuta una comprobación automatizada de preparación para la reversión, que abarca la compatibilidad de API, la diferencia de versiones, la compatibilidad de complementos y el estado del clúster. En una reversión iniciada por el usuario, Auto Mode reemplaza los nodos de trabajo aptos antes de revertir el plano de control; no se trata de una reacción automática ante fallas de aplicaciones. Siguen aplicándose los requisitos de elegibilidad y los controles de interrupción. La función no tiene cargos adicionales en las regiones donde se ofrece EKS; siguen aplicándose los cargos por nodos/almacenamiento y los cargos correspondientes al nivel de soporte de versiones. Consulte el [Procedimiento de reversión](#rollback-procedure) más abajo para obtener más detalles. (Fuente: [Amazon EKS anuncia la reversión de versiones de Kubernetes](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-version-rollback))
- **SLA del 99,99 % y nivel 8XL del plano de control (20 de marzo de 2026)**: El SLA para los clústeres de Provisioned Control Plane aumentó del 99,95 % al 99,99 % y se mide con una granularidad de un minuto. Un nuevo nivel de escalado 8XL duplica la capacidad de procesamiento de solicitudes de API del nivel 4XL anterior y está orientado a clústeres muy grandes y cargas de trabajo de IA/ML/HPC. (Fuente: [Amazon EKS anuncia el SLA y el nivel de escalado 8XL](https://aws.amazon.com/about-aws/whats-new/2026/03/amazon-eks-announces-sla-8xl-scaling-tier/))

### Componentes de la actualización

Las actualizaciones de clústeres de EKS incluyen los siguientes componentes:

1. **Plano de control de EKS**: servidor de API de Kubernetes, etcd, administrador del controlador, etc.
2. **Grupos de nodos**: nodos de trabajo y AMI de nodos
3. **Complementos**: complementos administrados por AWS (p. ej., CoreDNS, kube-proxy, VPC CNI)
4. **Componentes autoadministrados**: gráficos de Helm, recursos personalizados, etc.

### Ruta de actualización

Los clústeres de EKS deben actualizarse de una versión secundaria a la siguiente:

- Ilustración histórica: 1.24 → 1.25 → 1.26 → 1.27 muestra el patrón de una versión secundaria a la vez; no son destinos de implementación actuales.
- Un salto directo de 1.24 → 1.26 ilustra una versión secundaria omitida que no está admitida.
- Para un cambio real, elija la siguiente versión secundaria que EKS ofrezca en su región y según su política de soporte.

### Orden de actualización

1. Inventaríe, pruebe y haga copias de seguridad; resuelva las actualizaciones activas y alinee los nodos con la versión secundaria **actual** del plano de control como flujo de preparación conservador.
2. Aplique cualquier versión puente necesaria de complementos/controladores compatible con las versiones actuales y de destino de Kubernetes; verifique los requisitos previos específicos de cada componente.
3. Actualice el plano de control en una versión secundaria admitida y espere a que la actualización correspondiente a ese ID finalice correctamente.
4. Actualice los nodos, los clientes/controladores y los complementos restantes según el orden de dependencias verificado, comprobando cada paso. Auto Mode administra sus capacidades integradas e inicia las actualizaciones de nodos después de la actualización del plano de control.
5. Valide las versiones reales de los nodos, la disponibilidad de las cargas de trabajo, el tráfico, el almacenamiento y los SLO.

En Kubernetes, kubelet 1.25 y las versiones posteriores pueden estar hasta tres versiones secundarias por detrás del servidor de API, pero nunca por delante; si el servidor de API tiene varias versiones, el intervalo permitido se reduce. La documentación de EKS indica tanto las pautas de alineación de nodos previas a la actualización como la diferencia de versiones admitida. Este procedimiento elige la alineación como política de preparación; no afirma que la API de EKS rechace universalmente todas las diferencias de versiones admitidas. No hay una regla universal que indique que los complementos deban actualizarse todos “antes” o todos “después” del plano de control. La reversión tiene otra secuencia, que se describe más abajo.

## Planificación y preparación de la actualización {#upgrade-planning-and-preparation}

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Tree diagram showing upgrade planning and preparation split into an upgrade assessment branch (version compatibility check, resource requirements, upgrade schedule planning) and a pre-upgrade preparation branch (check cluster state, create backup, test upgrade, upgrade documentation).](../.gitbook/assets/en-eks-08-eks-upgrades-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-1.html)
-->

### Evaluación de la actualización

Antes de iniciar una actualización, evalúe lo siguiente:

#### Comprobación de compatibilidad de versiones

Compruebe la compatibilidad con la versión de destino de Kubernetes:

- **Eliminación de API**: identifique las cargas de trabajo que usan API obsoletas
- **Cambios de funciones**: revise los cambios de funciones de la nueva versión
- **Compatibilidad de complementos**: verifique que los complementos sean compatibles con la versión de destino

Una lista de imágenes o `kubectl get … .apiVersion` no constituye una auditoría de API/cliente obsoletas: el servidor de API devuelve representaciones negociadas/actuales. Una API beta no está obsoleta automáticamente. Revise los manifiestos de origen/Helm, los clientes, los CRD, los webhooks y los datos de análisis de actualizaciones de EKS para la versión de destino. Una única recopilación de métricas del servidor de API solo aporta evidencia observada; la ausencia de datos o un error no demuestra que no haya uso obsoleto.

Guarde el siguiente recopilador de solo lectura como `eks-upgrade-preflight.py`. Exporte `CLUSTER_NAME`, `AWS_REGION`, `EXPECTED_ACCOUNT_ID`, `KUBE_CONTEXT` y `TARGET_VERSION`; guarde su JSON con permisos locales restringidos. Si termina correctamente, significa que la recopilación se completó, no que la actualización esté aprobada ni que todas las cargas de trabajo sean compatibles.

```python
import json
import os
import re
import subprocess


def run_json(args):
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


def run_text(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def inspect_upgrade(cluster_name, region, expected_account, context, target, query=run_json, text=run_text):
    if not re.fullmatch(r"[0-9]{12}", expected_account):
        raise ValueError("Set the reviewed 12-digit AWS account ID")
    if not re.fullmatch(r"[0-9]+\.[0-9]+", target):
        raise ValueError("Target must be an EKS major.minor version")
    aws = [os.environ.get("AWS_CLI", "aws")]
    suffix = ["--region", region, "--output", "json", "--no-cli-pager"]
    identity = query(aws + ["sts", "get-caller-identity"] + suffix)
    if identity["Account"] != expected_account:
        raise RuntimeError("AWS account mismatch")
    cluster = query(aws + ["eks", "describe-cluster", "--name", cluster_name] + suffix)["cluster"]
    if cluster["status"] != "ACTIVE":
        raise RuntimeError("Cluster must be ACTIVE; inspect any in-progress updates")
    if cluster["arn"].split(":")[4] != expected_account:
        raise RuntimeError("Cluster/account mismatch")
    current = cluster["version"]
    current_parts = tuple(map(int, current.split(".")))
    target_parts = tuple(map(int, target.split(".")))
    if target_parts != (current_parts[0], current_parts[1] + 1):
        raise ValueError("This upgrade example requires exactly the next minor version")
    server = text(["kubectl", "--context", context, "config", "view", "--minify",
                   "--output", "jsonpath={.clusters[0].cluster.server}"])
    if server != cluster["endpoint"]:
        raise RuntimeError("Kubernetes context does not match the EKS API endpoint")
    catalog = query(aws + ["eks", "describe-cluster-versions", "--cluster-versions", target,
                         "--include-all", "--no-default-only"] + suffix)["clusterVersions"]
    if not any(item["clusterVersion"] == target and item.get("versionStatus") in
               ["STANDARD_SUPPORT", "EXTENDED_SUPPORT"] for item in catalog):
        raise ValueError("Target is not offered as a supported EKS version in this Region")
    insights = query(aws + [
        "eks", "list-insights", "--cluster-name", cluster_name,
        "--filter", json.dumps({"categories": ["UPGRADE_READINESS"], "kubernetesVersions": [target]}),
    ] + suffix)["insights"]
    nodes = query(["kubectl", "--context", context, "get", "nodes", "--output", "json"])["items"]
    update_ids = query(aws + ["eks", "list-updates", "--name", cluster_name] + suffix)["updateIds"]
    addon_names = query(aws + ["eks", "list-addons", "--cluster-name", cluster_name] + suffix)["addons"]
    addons = []
    for name in addon_names:
        addon = query(aws + ["eks", "describe-addon", "--cluster-name", cluster_name,
                             "--addon-name", name] + suffix)["addon"]
        addons.append({"name": name, "version": addon["addonVersion"], "status": addon["status"]})
    return {
        "cluster": cluster_name, "region": region, "account": expected_account,
        "currentVersion": current, "targetVersion": target, "targetCatalog": catalog,
        "insights": insights,
        "clusterUpdateIds": update_ids,
        "nodes": [{"name": node["metadata"]["name"],
                   "kubeletVersion": node["status"]["nodeInfo"]["kubeletVersion"],
                   "ready": next((condition.get("status") for condition in node["status"].get("conditions", [])
                                  if condition.get("type") == "Ready"), None),
                   "computeType": node["metadata"].get("labels", {}).get("eks.amazonaws.com/compute-type"),
                   "nodegroup": node["metadata"].get("labels", {}).get("eks.amazonaws.com/nodegroup")}
                  for node in nodes],
        "managedAddons": addons,
        "decision": "Inventory collected only; active-update review, owner approval, node alignment, API/client scans, "
                    "backups/restore tests, add-on bridge versions, capacity, and workload tests remain required.",
    }


if __name__ == "__main__":
    report = inspect_upgrade(
        os.environ["CLUSTER_NAME"], os.environ["AWS_REGION"],
        os.environ["EXPECTED_ACCOUNT_ID"], os.environ["KUBE_CONTEXT"],
        os.environ["TARGET_VERSION"],
    )
    print(json.dumps(report, indent=2))
```

#### Evaluación de requisitos de recursos

Evalúe los recursos necesarios para la actualización:

- **Capacidad del clúster**: capacidad suficiente para admitir nodos adicionales durante la actualización
- **Tolerancia al tiempo de inactividad**: si las cargas de trabajo pueden tolerar tiempo de inactividad
- **Plan de reversión**: plan de reversión en caso de problemas

#### Planificación del calendario de actualización

Planifique el calendario de actualización:

- **Ventana de mantenimiento**: programe la actualización durante períodos de poco tráfico
- **Enfoque por fases**: comience con entornos que no sean de producción y avance hacia producción
- **Ventana de reversión**: planifique el tiempo necesario para revertir en caso de problemas

### Preparación previa a la actualización

#### Comprobar el estado del clúster

Compruebe el estado del clúster antes de la actualización:

```bash
# Check node status
kubectl --context "$KUBE_CONTEXT" get nodes

# Check pod status
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces

# Check component status
kubectl --context "$KUBE_CONTEXT" get --raw /readyz

# Check events
kubectl --context "$KUBE_CONTEXT" get events --all-namespaces
```

#### Crear una copia de seguridad

Haga copias de seguridad de los datos importantes antes de la actualización:

AWS administra etcd del plano de control administrado; un comando `etcd-pod`/`etcdctl snapshot` en su espacio de nombres no puede hacer una copia de seguridad de ese servicio. `kubectl get all` también omite recursos importantes y datos de volúmenes, por lo que no constituye una copia de seguridad completa.

[AWS Backup for EKS](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html) puede proteger el estado del clúster y los recursos EBS/EFS/S3 respaldados por PVC mediante puntos de recuperación compuestos, con los requisitos previos documentados de IAM, modo de acceso API/API_AND_CONFIG_MAP, almacenamiento y restauración. Como alternativa, use una configuración propia de copias de seguridad con Velero/aplicaciones, con cobertura de volúmenes y credenciales verificadas. Revise la cobertura de recursos de ámbito de clúster/espacio de nombres, la coherencia de las bases de datos, la retención y las pruebas de restauración. Que una solicitud de copia de seguridad devuelva un ID no demuestra que haya terminado ni que sea posible recuperar los datos.

#### Probar la actualización

Pruebe la actualización en un entorno que no sea de producción:

1. Cree un clúster de prueba similar al entorno de producción
2. Realice la actualización en el clúster de prueba
3. Pruebe las cargas de trabajo y las funciones
4. Identifique y resuelva los problemas

#### Crear la documentación de la actualización

Documente el proceso de actualización:

- Pasos de actualización
- Responsables y contactos
- Procedimientos de reversión
- Guía para solucionar problemas

## Actualización del plano de control de EKS {#eks-control-plane-upgrade}

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagram of an EKS control plane upgrade split into four stages, preparation, execution, monitoring, and troubleshooting, each grouping its steps: version checks and planning, Console/CLI/eksctl, status, cluster state and CloudWatch monitoring, and common issues with troubleshooting steps.](../.gitbook/assets/en-eks-08-eks-upgrades-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-2.html)
-->

### Preparación de la actualización del plano de control

#### Comprobar la versión actual

Compruebe la versión actual del clúster de EKS:

```bash
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --query "cluster.version"
```

#### Comprobar las versiones disponibles

Compruebe las versiones de Kubernetes disponibles:

```bash
aws eks describe-cluster-versions --region "$AWS_REGION" \
  --no-default-only --output json --no-cli-pager
```

#### Crear un plan de actualización

Antes de enviar una actualización normal, revise las [pautas actuales de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html): el requisito de usar `--force` para los hallazgos del análisis de actualizaciones se ha retirado temporalmente. Esto difiere de las reglas bloqueantes de `ROLLBACK_READINESS` para la reversión de versiones. Resuelva los hallazgos o evalúelos explícitamente; la evidencia de API obsoletas de los últimos 30 días puede persistir después de corregir el problema. Asegúrese de que existan las subredes del clúster, que tengan las direcciones libres necesarias (EKS puede requerir hasta cinco) y que permitan la comunicación del plano de control. Una vez iniciada, una actualización del plano de control no se puede pausar ni detener; los clientes deben gestionar las reconexiones.

Cree un plan de actualización del plano de control:

- Hora de actualización: elija períodos de poco tráfico
- Configuración de supervisión: supervise el estado del clúster durante la actualización
- Plan de reversión: procedimiento de reversión en caso de problemas

### Ejecución de la actualización del plano de control

#### Actualización mediante la consola de administración de AWS

1. Inicie sesión en la consola de administración de AWS
2. Vaya al servicio Amazon EKS
3. Seleccione en la lista el clúster que desea actualizar
4. Seleccione la pestaña "Cluster configuration"
5. Haga clic en "Update Kubernetes version"
6. Seleccione la versión de destino y haga clic en "Update"

#### Actualización mediante AWS CLI

Ejecútela solo después de que se hayan aprobado el plan registrado y los requisitos previos. Guarde el asistente de sondeo de la sección siguiente como `eks-wait-update.py`. Esto solicita únicamente la actualización del plano de control; no actualiza nodos/complementos ni demuestra que las cargas de trabajo estén listas.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${AWS_REGION:?Set the reviewed Region}"
: "${TARGET_VERSION:?Set the next supported EKS minor version}"
umask 077
aws eks update-cluster-version \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --output json --no-cli-pager \
  > control-plane-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' control-plane-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

#### Actualización mediante eksctl

```bash
eksctl upgrade cluster \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --version "$TARGET_VERSION" \
  --approve
```

### Supervisión de la actualización del plano de control

#### Comprobar el estado de la actualización

Compruebe el estado de la actualización:

Supervise `DescribeUpdate` para el ID de actualización exacto. `cluster-active`/`nodegroup-active` no demuestra que esta solicitud haya terminado correctamente, y AWS CLI 2.36.44 no dispone de un waiter `eks wait update-successful`. Guarde este archivo como `eks-wait-update.py`; para una solicitud de grupo de nodos/complemento, establezca exactamente una de estas variables: `NODEGROUP_NAME` o `ADDON_NAME`; de lo contrario, deje ambas sin definir. Falla ante errores de API, errores/cancelaciones, estados desconocidos o al llegar al plazo del cliente. El tiempo de espera del cliente no cancela la operación de AWS. El tiempo de espera predeterminado de dos horas del cliente debe ajustarse a la operación aprobada, especialmente en las reversiones prolongadas de Auto Mode.

```python
import json
import os
import subprocess
import time
from pathlib import Path


def wait_update(lookup, timeout_seconds, interval_seconds=15, clock=time.monotonic, sleep=time.sleep):
    if timeout_seconds <= 0 or interval_seconds < 0:
        raise ValueError("Use a positive timeout and nonnegative polling interval")
    deadline = clock() + timeout_seconds
    while True:
        update = lookup()["update"]
        status = update["status"]
        print(json.dumps({"id": update["id"], "status": status, "errors": update.get("errors", [])}), flush=True)
        if status == "Successful":
            return update
        if status in ["Failed", "Cancelled"]:
            raise RuntimeError(f"EKS update ended with {status}; inspect its error details")
        if status not in ["InProgress", "Cancelling"]:
            raise RuntimeError(f"Unexpected update status: {status}")
        if clock() >= deadline:
            raise TimeoutError("Client wait expired; the AWS operation may still be running. Preserve its update ID.")
        sleep(interval_seconds)


if __name__ == "__main__":
    cluster = os.environ["CLUSTER_NAME"]
    region = os.environ["AWS_REGION"]
    update_id = os.environ["UPDATE_ID"]
    nodegroup = os.environ.get("NODEGROUP_NAME")
    addon = os.environ.get("ADDON_NAME")
    if nodegroup and addon:
        raise ValueError("Set only NODEGROUP_NAME or ADDON_NAME for a scoped update")
    command = [
        os.environ.get("AWS_CLI", "aws"), "eks", "describe-update",
        "--name", cluster, "--region", region, "--update-id", update_id,
        "--output", "json", "--no-cli-pager",
    ]
    if nodegroup:
        command += ["--nodegroup-name", nodegroup]
    if addon:
        command += ["--addon-name", addon]
    status_file = Path(os.environ.get("UPDATE_STATUS_FILE", "eks-update-status.json"))

    def lookup():
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        response = json.loads(completed.stdout)
        status_file.write_text(json.dumps(response, indent=2) + "\n")
        return response

    wait_update(lookup, int(os.environ.get("WAIT_TIMEOUT_SECONDS", "7200")))
```

#### Supervisar el estado del clúster

Supervise el estado del clúster durante la actualización:

```bash
# Check node status
kubectl --context "$KUBE_CONTEXT" get nodes

# Check pod status
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces

# Check events
kubectl --context "$KUBE_CONTEXT" get events --all-namespaces --sort-by='.lastTimestamp'
```

#### Supervisar las métricas de CloudWatch

Supervise las métricas del plano de control que realmente se publican para su versión/nivel de EKS y la telemetría que haya configurado: tasa/latencia/errores de solicitudes de API, preparación de la API y reconexiones de clientes, programación, estado de nodos/cargas de trabajo y SLO de aplicaciones. No suponga que se exponen directamente los puntos de conexión de etcd/administrador del controlador ni todas las métricas de componentes. `/readyz` comprueba la preparación de la API, no todas las condiciones de las aplicaciones ni las condiciones históricas de disponibilidad.

### Solución de problemas de la actualización del plano de control

#### Problemas comunes

Problemas comunes que pueden presentarse durante la actualización del plano de control:

- **Falla de la actualización**: el proceso de actualización falla o se interrumpe
- **Disponibilidad del servidor de API**: problemas de disponibilidad del servidor de API durante la actualización
- **Problemas de compatibilidad**: problemas de compatibilidad entre las cargas de trabajo y la nueva versión

#### Pasos para solucionar problemas

1. Compruebe el estado de la actualización
2. Revise los registros de CloudTrail
3. Revise los registros del plano de control de EKS
4. Póngase en contacto con AWS Support

## Actualización del grupo de nodos {#node-group-upgrade}

Después de actualizar el plano de control, debe actualizar los grupos de nodos. Hay varias estrategias para actualizar grupos de nodos, cada una con ventajas y desventajas.

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagram showing node group upgrades split into five branches, strategies, managed, self-managed, Fargate, and monitoring and validation, with the strategies branch broken down into managed, self-managed, and Fargate approaches.](../.gitbook/assets/en-eks-08-eks-upgrades-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-3.html)
-->

### Estrategias de actualización de grupos de nodos

#### Actualización de grupos de nodos administrados

Los grupos de nodos administrados son una función de administración de grupos de nodos que ofrece AWS y automatiza las actualizaciones de nodos:

- **Estrategia de reemplazo**: `maxUnavailable`/porcentaje permite reemplazar varios nodos en paralelo. La API `updateStrategy=DEFAULT` lanza nueva capacidad antes de retirar la antigua; `MINIMAL` retira primero la capacidad antigua y tiene distintas ventajas y desventajas en cuanto a disponibilidad/capacidad.
- **Drenaje**: las actualizaciones normales recurren a la expulsión de Pods y a las comprobaciones de PDB; los controladores vuelven a crear los Pods en lugar de migrarlos en caliente. La opción de forzado del grupo de nodos puede omitir las fallas de drenaje relacionadas con PDB y no es lo mismo que la marca de forzado de reversión del clúster.
- **Selección de versión/AMI**: elija la versión de Kubernetes y la versión de AMI revisadas, o una nueva versión de la plantilla de lanzamiento original si usa AMI personalizadas. Una actualización fallida no demuestra que la flota se haya revertido automáticamente; inspeccione el estado mixto de nodos/AMI y los errores de actualización.

#### Actualización de grupos de nodos autoadministrados

En los grupos de nodos autoadministrados, debe actualizar los nodos manualmente:

- **Implementación Blue/Green**: cree un grupo de nodos nuevo y migre las cargas de trabajo
- **Actualización gradual**: drene y termine los nodos uno por uno y reemplácelos por nodos nuevos
- **Actualización in situ**: actualice kubelet y el tiempo de ejecución de contenedores en los nodos existentes

#### Actualización de nodos de Fargate

AWS administra la infraestructura de los nodos de Fargate, pero quien opera la carga de trabajo debe coordinar el reemplazo de los Pods. Los Pods de Fargate recién lanzados usan una versión de kubelet que coincide con la del plano de control; la actualización del plano de control no actualiza los Pods existentes. Planifique la implementación gradual de los controladores, la disponibilidad y la validación; no dé por hecho que Fargate no requiere tareas de actualización. Auto Mode funciona de otra manera: inicia su propio reemplazo gradual de nodos después de actualizar el plano de control, sujeto a sus controles de interrupción.

### Actualización de grupos de nodos administrados

#### Comprobar la versión del grupo de nodos administrado

Compruebe la versión actual del grupo de nodos administrado:

```bash
aws eks describe-nodegroup \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query "nodegroup.version"
```

#### Actualización mediante la consola de administración de AWS

1. Inicie sesión en la consola de administración de AWS
2. Vaya al servicio Amazon EKS
3. Seleccione en la lista el clúster que desea actualizar
4. Seleccione la pestaña "Compute"
5. Seleccione el grupo de nodos que desea actualizar
6. Haga clic en "Update node group"
7. Seleccione la versión de destino y haga clic en "Update"

#### Actualización mediante AWS CLI

Para una AMI optimizada para EKS, use la versión de lanzamiento revisada y la versión de destino. Esta operación tiene su propio ID de actualización; conserve el ámbito del grupo de nodos al sondear el estado. Revise la compatibilidad de la plataforma/familia de AMI; cambiar la versión de Kubernetes no migra un grupo de nodos AL2 a AL2023.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${TARGET_VERSION:?Set the reviewed target, no newer than the control plane}"
: "${TARGET_AMI_RELEASE:?Set the reviewed EKS-optimized AMI release}"
umask 077
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" --output json > nodegroup-before.json
if jq -e '.nodegroup.amiType == "CUSTOM"' nodegroup-before.json >/dev/null; then
  echo "Use the custom launch-template path for this node group" >&2
  exit 1
fi
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --release-version "$TARGET_AMI_RELEASE" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

Para una **AMI personalizada**, actualice la plantilla de lanzamiento original a una nueva versión revisada. No pase `version` ni `releaseVersion` de Kubernetes en esa solicitud con AMI personalizada; verifique el kubelet, el tiempo de ejecución y la AMI reales en los nodos de reemplazo.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${LAUNCH_TEMPLATE_ID:?Set the same launch template originally used by the group}"
: "${LAUNCH_TEMPLATE_VERSION:?Set the reviewed version containing the updated custom AMI}"
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --launch-template "id=$LAUNCH_TEMPLATE_ID,version=$LAUNCH_TEMPLATE_VERSION" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

#### Actualización mediante eksctl

```bash
eksctl upgrade nodegroup \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name "$NODEGROUP_NAME" \
  --kubernetes-version "$TARGET_VERSION"
```

#### Configuración de la actualización de grupos de nodos administrados

Puede configurar el comportamiento de actualización de los grupos de nodos administrados:

- **Máximo no disponible**: número máximo de nodos no disponibles durante la actualización
- **PDB**: limita las expulsiones voluntarias aptas, pero no todas las fallas ni todos los resultados de las aplicaciones. Una actualización forzada del grupo de nodos puede ignorar un problema de PDB. Cambiar la configuración de escalado deseado/mínimo/máximo de un grupo de nodos administrado es una operación de escalado de ASG y **no** ofrece las garantías de drenaje/PDB de la actualización; no use un cambio de tamaño a cero como migración segura.

```bash
aws eks update-nodegroup-config \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --update-config maxUnavailable=1
```

### Actualización de grupos de nodos autoadministrados

#### Implementación Blue/Green

Prepare un grupo de nodos nuevo, con un nombre distinto, a partir de la configuración propietaria, conservando los requisitos revisados de subred/zona, IAM, AMI/inicialización, etiquetas, taints, almacenamiento y red. Consulte la [guía de creación de clústeres](02-eks-cluster-creation.md). `eksctl create nodegroup` crea un grupo administrado de forma predeterminada; una configuración autoadministrada debe seleccionar explícitamente `--managed=false` o la sección de configuración `nodeGroups` correspondiente. La creación usa `--version`, mientras que `eksctl upgrade nodegroup` usa `--kubernetes-version`.

1. Cree capacidad en el nuevo grupo de nodos según la configuración revisada y compruebe el número de nodos, las versiones de kubelet y AMI de destino, el estado Ready, CNI/DNS y la programación de las aplicaciones. El simple hecho de enumerar los nodos no constituye esa validación.
2. Migre las cargas de trabajo en fases controladas por el responsable. La afinidad preferida no garantiza la ubicación en el grupo nuevo; compruebe en qué nodos se ejecutan realmente los Pods y revise la topología del almacenamiento.
3. Drene un nodo antiguo identificado a la vez con un tiempo de espera finito; deténgase si falla una expulsión o una comprobación de estado. Vuelva a validar las cargas de trabajo/la capacidad de reemplazo antes de continuar.
4. Retire el grupo antiguo solo después de registrar la aceptación de la migración, el estado, la retención de datos y la recuperación. No lo elimine automáticamente después de un bucle sin comprobaciones o una espera de duración fija.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

Este drenaje predeterminado se detiene ante casos de datos locales o Pods no administrados que requieren una decisión aparte. `--delete-emptydir-data` permite explícitamente perder los datos de emptyDir; no lo agregue sin evaluar el caso. `kubectl drain --force` permite desalojar Pods no administrados y no equivale a omitir las comprobaciones de expulsión/PDB. Coordine con sus responsables los DaemonSets, los Pods estáticos, los controladores y los datos persistentes.

#### Actualización gradual

En un ASG autoadministrado, primero actualice la configuración/plantilla de lanzamiento administrada al AMI validado; de lo contrario, los reemplazos pueden volver a iniciar con la imagen antigua. Use la compuerta de drenaje de un solo nodo anterior y verifique el ID de proveedor del nodo, la instancia EC2 y la propiedad del ASG antes de terminar cualquier instancia. No asigne un nodo de Kubernetes al primer resultado de búsqueda por nombre DNS privado de EC2. El responsable del ASG debe reemplazar la instancia drenada y esperar a que haya un nodo nuevo, correctamente configurado y Ready, y a que se recuperen las cargas de trabajo, antes de continuar. Una espera de 60 segundos no demuestra que el reemplazo esté listo. El escalado directo de ASG/la actualización de instancias requiere la integración correspondiente de drenaje de Kubernetes; no aplica automáticamente un PDB.

#### Actualización in situ

Use un procedimiento específico del sistema operativo/de la imagen, probado por separado, solo para hosts autoadministrados que lo admitan. En flotas administradas optimizadas para EKS, prefiera una ruta de reemplazo con AMI inmutable y validada; la infraestructura de Auto Mode/Fargate es propiedad del servicio. Un `yum update kubelet kubectl` genérico no selecciona una versión revisada de Kubernetes/tiempo de ejecución ni constituye una actualización de nodo de EKS. Una solicitud de SSM es asíncrona: no quite el cordón hasta que la invocación, los reinicios de servicios necesarios, las versiones reales, el estado Ready del nodo y las pruebas de cargas de trabajo hayan finalizado correctamente. Conserve la evidencia de las fallas en vez de quitar el cordón o terminar nodos automáticamente tras un error.

### Supervisión y validación de la actualización de nodos

#### Comprobar la versión del nodo

Compruebe la versión de Kubernetes del nodo:

```bash
kubectl --context "$KUBE_CONTEXT" get nodes -o custom-columns=NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion
```

#### Comprobar el estado del nodo

Compruebe el estado del nodo:

```bash
kubectl --context "$KUBE_CONTEXT" get nodes
kubectl --context "$KUBE_CONTEXT" describe nodes
```

#### Comprobar la implementación de Pods

Verifique que los Pods se implementen con normalidad:

```bash
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces -o wide
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,PHASE:.status.phase,READY:'.status.conditions[?(@.type=="Ready")].status'
```

## Actualización de complementos {#add-on-upgrade}

Inventaríe los propietarios reales de los componentes y sus rutas de actualización. Las versiones de complementos administrados por EKS no se actualizan automáticamente al actualizar el plano de control; el responsable selecciona e inicia una actualización compatible. Las versiones puente necesarias pueden instalarse antes del cambio del plano de control. AWS administra por separado las capacidades integradas de Auto Mode; no instale ni actualice componentes duplicados de redes/almacenamiento/DNS de nodos como si todos los clústeres usaran los mismos DaemonSets/Deployments.

![Diagrama que muestra cómo se dividen las actualizaciones de complementos en complementos administrados por AWS (comprobar versiones y luego actualizar con update-addon o eksctl), complementos autoadministrados (Helm o kubectl), guías de complementos clave (CoreDNS, kube-proxy, VPC CNI) y solución de problemas (problemas comunes y pasos para solucionarlos).](../.gitbook/assets/en-eks-08-eks-upgrades-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-4.html)

### Complementos administrados por AWS

#### Comprobar la lista de complementos administrados

Compruebe los complementos administrados instalados en el clúster:

```bash
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
```

#### Comprobar la versión del complemento administrado

Compruebe la versión actual de los complementos administrados:

```bash
aws eks describe-addon \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name vpc-cni \
  --query "addon.addonVersion"
```

#### Comprobar las versiones disponibles de los complementos

Compruebe las versiones de complementos disponibles:

El primer elemento de una matriz no garantiza que sea “la versión más reciente” ni la versión correcta. Revise `compatibilities`, los indicadores de versión predeterminada, la compatibilidad de plataforma/tipo de computación/arquitectura, las notas de la versión, los cambios de IAM y los requisitos de versiones intermedias. Capture la configuración y las asociaciones de identidad antes de cambiar el complemento. Guarde los archivos con permisos restringidos; la configuración puede contener valores sensibles.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"
: "${TARGET_VERSION:?Set the Kubernetes version for this stage}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json > addon-before.json
aws eks describe-addon-versions --addon-name "$ADDON_NAME" \
  --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json > addon-candidates.json
# Select ADDON_VERSION after reviewing compatibility, architecture, compute type, and upgrade path.
: "${ADDON_VERSION:?Set the reviewed add-on version}"
aws eks describe-addon-configuration --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --output json > addon-schema.json
jq -r '.addon.configurationValues // "{}"' addon-before.json > addon-config-candidate.json
```

#### Actualizar complementos administrados

Puede actualizar complementos administrados mediante la consola de administración de AWS, AWS CLI o eksctl:

Valide el JSON candidato con el esquema de destino y conserve la configuración y la semántica de identidad previstas. `PRESERVE` gestiona los conflictos en campos administrados; no valida todos los valores personalizados, no garantiza el comportamiento de la aplicación ni combina una configuración parcial explícita con el JSON anterior. Pasar `{}` puede restablecer la configuración. Actualice un complemento administrado a la vez y compruebe su ID de actualización, estado, versión y comportamiento de las cargas de trabajo.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"; : "${ADDON_VERSION:?}"
: "${REVIEWED_ADDON_CONFIG_FILE:?Provide the complete reviewed target configuration JSON}"
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG_FILE" \
  --resolve-conflicts PRESERVE --output json > addon-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' addon-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID ADDON_NAME
unset NODEGROUP_NAME
python3 eks-wait-update.py
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json
```

En eksctl 0.229, `update addon` admite `--wait` y `--config-file`, pero no tiene una marca `--preserve`. Incluya la política de resolución de conflictos prevista en una configuración de eksctl revisada o use el procedimiento explícito de AWS CLI anterior. `eksctl --force` migra la propiedad desde un complemento autoadministrado y no es una opción genérica para conservar configuraciones ante conflictos.

### Complementos autoadministrados

#### Actualizar complementos autoadministrados

Actualice los complementos autoadministrados mediante Helm o kubectl:

Use el propietario actual de Helm/manifiestos. El ejemplo supone que se ha revisado la referencia al repositorio/OCI del gráfico y que existe una versión instalada; deliberadamente no usa `--install` para crear un segundo administrador si falta la versión. Revise los requisitos de migración de CRD e IAM del nuevo gráfico; `helm upgrade` por sí solo no actualiza los CRD de un directorio `crds/` del gráfico. Helm y la implementación de manifiestos sin procesar son alternativas, no pasos de actualización consecutivos. El ejemplo anterior de Metrics Server 0.6.1/3.8.2 no selecciona una versión de destino compatible.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${RELEASE:?}"; : "${ADDON_NAMESPACE:?}"
: "${CHART_REF:?Set the verified repository/chart or OCI reference}"
: "${CHART_VERSION:?Set a reviewed compatible chart version}"
: "${REVIEWED_VALUES_FILE:?Set the complete reviewed target values file}"
umask 077
helm get values "$RELEASE" --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > addon-values-before.yaml
helm show values "$CHART_REF" --version "$CHART_VERSION" > addon-values-defaults.yaml
# Merge/migrate values and handle CRDs/IAM through the owner before this step.
helm upgrade "$RELEASE" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  -f "$REVIEWED_VALUES_FILE" --wait --timeout 15m
```

### Guías de actualización de complementos clave

#### Actualización de CoreDNS

Para los nodos estándar, determine si EKS u otra herramienta administra el Deployment de CoreDNS, conserve la configuración de Corefile/PDB y los ajustes personalizados, y siga las notas de migración de la versión seleccionada. Los nodos de Auto Mode ejecutan CoreDNS como un servicio del sistema del nodo: un clúster exclusivamente de Auto Mode no requiere el complemento Deployment, mientras que un clúster mixto debe conservar DNS para los nodos que no sean de Auto Mode. No interprete la ausencia de un Deployment en un clúster exclusivamente de Auto Mode como una actualización fallida.

#### Actualización de kube-proxy

Mantenga kube-proxy compatible con el servidor de API y los nodos en los que se ejecuta; no debe ser más reciente que el servidor de API. Use la compilación del complemento admitida para el destino y el orden verificado. Auto Mode administra las redes de sus servicios; no suponga que allí existe un DaemonSet autoadministrado de kube-proxy.

#### Actualización de VPC CNI

Para los nodos EC2 estándar, verifique la ruta de versión de CNI, el modo IP/prefijo, IAM, la configuración de políticas de red y la conectividad de las cargas de trabajo. No suponga que un único ConfigMap `aws-node` contiene todos los ajustes: incluya `configurationValues` de EKS, la configuración del DaemonSet/contenedor, la identidad de la cuenta de servicio y la configuración propietaria de Helm/GitOps cuando corresponda. Las redes integradas de Auto Mode siguen su propia ruta de administración.

Use el proceso genérico de captura/selección/actualización/espera anterior para cada complemento administrado por EKS. Inspeccione los agentes de nodos estándar solo si están realmente instalados:

```bash
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset kube-proxy aws-node -o wide
```

### Solución de problemas de actualización de complementos

#### Problemas comunes

Problemas comunes que pueden presentarse durante la actualización de complementos:

- **Conflictos de configuración**: conflictos entre la configuración personalizada y la nueva versión
- **Problemas de compatibilidad**: problemas de compatibilidad entre el complemento y la versión de Kubernetes
- **Restricciones de recursos**: recursos insuficientes para la actualización

#### Pasos para solucionar problemas

1. Compruebe el estado del complemento:

```bash
aws eks describe-addon \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name vpc-cni
```

2. Compruebe los registros del complemento:

```bash
kubectl --context "$KUBE_CONTEXT" logs -n kube-system -l k8s-app=kube-dns
kubectl --context "$KUBE_CONTEXT" logs -n kube-system -l k8s-app=kube-proxy
kubectl --context "$KUBE_CONTEXT" logs -n kube-system -l k8s-app=aws-node
```

3. Compruebe los eventos del complemento:

```bash
kubectl --context "$KUBE_CONTEXT" get events -n kube-system --sort-by='.lastTimestamp'
```

## Validación y solución de problemas de la actualización {#upgrade-validation-and-troubleshooting}

Cuando termine la actualización, debe validar que el clúster funcione con normalidad y resolver cualquier problema que pueda surgir.

![Diagrama de árbol que divide el trabajo posterior a la actualización en Validación de la actualización (versión del clúster, estado del clúster, validación de cargas de trabajo y pruebas funcionales) y Solución de problemas de la actualización (problemas comunes, pasos para solucionarlos y procedimiento de reversión).](../.gitbook/assets/en-eks-08-eks-upgrades-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-5.html)

### Validación de la actualización

#### Comprobar la versión del clúster

Compruebe las versiones del clúster y los nodos:

```bash
# Check cluster version
kubectl --context "$KUBE_CONTEXT" version --output=yaml

# Check node version
kubectl --context "$KUBE_CONTEXT" get nodes -o custom-columns=NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion
```

#### Comprobar el estado del clúster

Compruebe el estado de los componentes del clúster:

```bash
# Check node status
kubectl --context "$KUBE_CONTEXT" get nodes

# Check pod status
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces

# Check namespace status
kubectl --context "$KUBE_CONTEXT" get namespaces

# Check service status
kubectl --context "$KUBE_CONTEXT" get services --all-namespaces
```

#### Validación de cargas de trabajo

Verifique que las cargas de trabajo de las aplicaciones funcionen con normalidad:

```bash
# Check deployment status
kubectl --context "$KUBE_CONTEXT" get deployments --all-namespaces

# Check statefulset status
kubectl --context "$KUBE_CONTEXT" get statefulsets --all-namespaces

# Check daemonset status
kubectl --context "$KUBE_CONTEXT" get daemonsets --all-namespaces

# Check service endpoints
kubectl --context "$KUBE_CONTEXT" get endpointslices.discovery.k8s.io --all-namespaces
```

#### Pruebas funcionales

Use recursos de prueba aislados y propios, y criterios de aceptación explícitos. La siguiente **prueba rápida de nodos EC2 Linux** cubre la implementación/escalado de Deployment, las solicitudes de Service/DNS y los datos de PVC entre Jobs separados. No es una prueba de carga, no prueba todos los nodos/zonas de disponibilidad ni demuestra la corrección de las aplicaciones/alta disponibilidad/seguridad. Añada pruebas específicas de las cargas de trabajo, entrada/salida, controladores/webhooks y recuperación. Fargate, híbrido y otras plataformas requieren sus propios planes de prueba compatibles.

Guarde el archivo como `eks-upgrade-smoke.py`. Usa el manifiesto de imagen oficial de BusyBox fijado y verificado para esta auditoría; aquí no se ejecutó ninguna prueba de imagen ni del clúster. Antes de ejecutarlo, verifique la política de imágenes, las reglas de admisión/red, la capacidad disponible y una StorageClass de sistema de archivos compatible en los nodos seleccionados. Establezca `KUBE_CONTEXT`, `TEST_STORAGE_CLASS`, `RUN_SMOKE_TEST=yes` y, si va a probar nodos de reemplazo específicos, un mapa JSON `SMOKE_NODE_SELECTOR` revisado. El script crea un espacio de nombres único, nunca adopta uno existente, se detiene ante errores y registra la ubicación real y los detalles de reclamación del PV. Los volúmenes `WaitForFirstConsumer` reciben un consumidor escritor antes de esperar a que finalicen.

Los recursos se conservan de forma predeterminada para su revisión. `CLEANUP_ON_SUCCESS=yes` elimina únicamente el UID del espacio de nombres creado por esa ejecución después de verificaciones satisfactorias. La eliminación del espacio de nombres puede dejar PV/almacenamiento facturable si la clase usa Retain; inspeccione el PV registrado y limpie solo el almacenamiento de prueba propio. Los errores se conservan para el diagnóstico y no se notifican como éxito. Las métricas actuales de corto plazo y 20 solicitudes HTTP secuenciales no demuestran equivalencia de rendimiento.

```python
import json
import os
import subprocess
import uuid
from pathlib import Path

IMAGE = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"


def manifests(namespace, storage_class, marker, node_selector):
    if node_selector.get("kubernetes.io/os", "linux") != "linux":
        raise ValueError("This BusyBox example requires Linux nodes")
    node_selector = {"kubernetes.io/os": "linux", **node_selector}
    security = {"runAsNonRoot": True, "runAsUser": 65532, "fsGroup": 65532,
                "seccompProfile": {"type": "RuntimeDefault"}}
    container_security = {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                          "capabilities": {"drop": ["ALL"]}}
    resources = {"requests": {"cpu": "50m", "memory": "32Mi"},
                 "limits": {"cpu": "200m", "memory": "128Mi"}}

    def job(name, command, with_volume=False):
        container = {"name": "check", "image": IMAGE, "command": ["sh", "-ec", command],
                     "resources": resources, "securityContext": container_security}
        pod = {"restartPolicy": "Never", "automountServiceAccountToken": False,
               "securityContext": security, "nodeSelector": node_selector, "containers": [container]}
        if with_volume:
            container["volumeMounts"] = [{"name": "data", "mountPath": "/data"}]
            pod["volumes"] = [{"name": "data", "persistentVolumeClaim": {"claimName": "smoke-data"}}]
        return {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": name, "namespace": namespace},
                "spec": {"backoffLimit": 0, "activeDeadlineSeconds": 120,
                         "template": {"spec": pod}}}

    config = {"apiVersion": "v1", "kind": "ConfigMap",
              "metadata": {"name": "smoke-content", "namespace": namespace},
              "data": {"index.html": marker + "\n"}}
    deployment = {
        "apiVersion": "apps/v1", "kind": "Deployment",
        "metadata": {"name": "smoke-http", "namespace": namespace},
        "spec": {"replicas": 2, "selector": {"matchLabels": {"app": "smoke-http"}},
                 "template": {"metadata": {"labels": {"app": "smoke-http"}}, "spec": {
                     "automountServiceAccountToken": False, "securityContext": security,
                     "nodeSelector": node_selector,
                     "containers": [{"name": "http", "image": IMAGE,
                                     "command": ["httpd", "-f", "-p", "8080", "-h", "/www"],
                                     "securityContext": container_security, "resources": resources,
                                     "ports": [{"name": "http", "containerPort": 8080}],
                                     "readinessProbe": {"httpGet": {"path": "/", "port": "http"}},
                                     "volumeMounts": [{"name": "content", "mountPath": "/www", "readOnly": True}]}],
                     "volumes": [{"name": "content", "configMap": {"name": "smoke-content"}}],
                 }}},
    }
    service = {"apiVersion": "v1", "kind": "Service",
               "metadata": {"name": "smoke-http", "namespace": namespace},
               "spec": {"selector": {"app": "smoke-http"}, "ports": [{"port": 80, "targetPort": "http"}]}}
    pvc = {"apiVersion": "v1", "kind": "PersistentVolumeClaim",
           "metadata": {"name": "smoke-data", "namespace": namespace},
           "spec": {"storageClassName": storage_class, "accessModes": ["ReadWriteOnce"],
                    "resources": {"requests": {"storage": "1Gi"}}}}
    writer = job("smoke-write", f"printf '%s\\n' '{marker}' > /data/marker; sync", True)
    reader = job("smoke-read", f"test \"$(cat /data/marker)\" = '{marker}'", True)
    http = job("smoke-request", f"i=0; while [ \"$i\" -lt 20 ]; do "
               f"test \"$(wget -T 5 -q -O - http://smoke-http)\" = '{marker}'; "
               "i=$((i + 1)); sleep 1; done")
    return [config, deployment, service, pvc, writer], reader, http


def run_smoke(context, storage_class, node_selector, call=subprocess.run):
    if not context or not storage_class or not isinstance(node_selector, dict):
        raise ValueError("Set the reviewed context, StorageClass, and node selector map")
    namespace = "eks-upgrade-smoke-" + uuid.uuid4().hex[:12]
    marker = uuid.uuid4().hex
    evidence = Path(namespace)
    evidence.mkdir()
    prefix = ["kubectl", "--context", context]

    def kubectl(*args, payload=None):
        completed = call(prefix + list(args), input=json.dumps(payload) if payload else None,
                         check=True, capture_output=True, text=True, timeout=240)
        return completed.stdout

    # Create, never apply/adopt, the namespace. A failed creation must not lead to deletion.
    created = json.loads(kubectl("create", "namespace", namespace, "--output", "json"))
    namespace_uid = created["metadata"]["uid"]
    (evidence / "namespace.json").write_text(json.dumps(created, indent=2) + "\n")
    print(f"Owned smoke namespace: {namespace}; preserve evidence and inspect PV reclamation before cleanup.", flush=True)
    try:
        initial, reader, http = manifests(namespace, storage_class, marker, node_selector)
        kubectl("create", "-f", "-", payload={"apiVersion": "v1", "kind": "List", "items": initial})
        # The writer is a PVC consumer, so WaitForFirstConsumer provisioning can proceed.
        kubectl("-n", namespace, "wait", "--for=condition=Complete", "job/smoke-write", "--timeout=180s")
        kubectl("-n", namespace, "delete", "job", "smoke-write", "--cascade=foreground",
                "--wait=true", "--timeout=60s")
        kubectl("create", "-f", "-", payload=reader)
        kubectl("-n", namespace, "wait", "--for=condition=Complete", "job/smoke-read", "--timeout=180s")
        kubectl("-n", namespace, "rollout", "status", "deployment/smoke-http", "--timeout=180s")
        kubectl("-n", namespace, "scale", "deployment/smoke-http", "--replicas=3")
        kubectl("-n", namespace, "rollout", "status", "deployment/smoke-http", "--timeout=180s")
        kubectl("create", "-f", "-", payload=http)
        kubectl("-n", namespace, "wait", "--for=condition=Complete", "job/smoke-request", "--timeout=180s")
        pods = json.loads(kubectl("-n", namespace, "get", "pods", "--output", "json"))
        claim = json.loads(kubectl("-n", namespace, "get", "pvc", "smoke-data", "--output", "json"))
        volume = json.loads(kubectl("get", "pv", claim["spec"]["volumeName"], "--output", "json"))
        result = {"namespace": namespace, "namespaceUID": namespace_uid, "nodeSelector": node_selector,
                  "checks": ["PVC write/read across Jobs", "Deployment rollout/scale", "20 HTTP/DNS requests"],
                  "pods": pods, "pvc": claim, "pv": volume,
                  "limits": "A bounded smoke test, not a load benchmark, HA proof, or full application validation."}
        (evidence / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    except Exception:
        print(f"Smoke test failed; namespace {namespace} retained for diagnosis.", flush=True)
        raise
    print(f"Smoke checks completed. Evidence: {evidence}/result.json", flush=True)
    if os.environ.get("CLEANUP_ON_SUCCESS") == "yes":
        current = json.loads(kubectl("get", "namespace", namespace, "--output", "json"))
        if current["metadata"]["uid"] != namespace_uid:
            raise RuntimeError("Namespace identity changed; refusing cleanup")
        kubectl("delete", "namespace", namespace, "--wait=true", "--timeout=180s")
        print("Namespace deleted; inspect the recorded PV reclaim policy for retained billable storage.", flush=True)
    return namespace


if __name__ == "__main__":
    if os.environ.get("RUN_SMOKE_TEST") != "yes":
        raise SystemExit("Set RUN_SMOKE_TEST=yes only for the approved test scope")
    os.umask(0o077)
    run_smoke(os.environ["KUBE_CONTEXT"], os.environ["TEST_STORAGE_CLASS"],
              json.loads(os.environ.get("SMOKE_NODE_SELECTOR", "{}")))
```

### Solución de problemas de la actualización

#### Problemas comunes durante la actualización

Problemas comunes que pueden presentarse durante la actualización:

1. **Falla de la actualización del plano de control**:
   - Problemas de disponibilidad del servidor de API
   - Problemas con la base de datos etcd
   - Problemas de permisos de IAM

2. **Problemas con la actualización de nodos**:
   - Falla del drenaje del nodo
   - Falla al iniciar el nodo nuevo
   - Diferencia de versión de kubelet

3. **Problemas con la actualización de complementos**:
   - Conflictos de configuración
   - Problemas de compatibilidad
   - Restricciones de recursos

4. **Problemas con las cargas de trabajo**:
   - Falla de la carga de trabajo debido a la eliminación de API
   - Fallo de programación de Pods debido a restricciones de recursos
   - Problemas de red

#### Pasos para solucionar problemas

1. **Comprobar los registros**:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${START_TIME_MS:?Set the reviewed start timestamp in epoch milliseconds}"
: "${END_TIME_MS:?Set the reviewed analysis-window end timestamp}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.logging' --output json --no-cli-pager
# Read existing logs; enabling logging is a separate change and does not backfill history.
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
# Standard EC2-node agents only, where installed; these are Pod logs, not all host journals.
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-proxy \
  --all-containers=true --prefix=true --since=15m --tail=100
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=aws-node \
  --all-containers=true --prefix=true --since=15m --tail=100
```

2. **Comprobar los eventos**:

```bash
kubectl --context "$KUBE_CONTEXT" get events --all-namespaces --sort-by='.lastTimestamp'
```

3. **Comprobar el estado de los recursos**:

```bash
kubectl --context "$KUBE_CONTEXT" describe nodes
kubectl --context "$KUBE_CONTEXT" -n "$WORKLOAD_NAMESPACE" get deployments,statefulsets,daemonsets,pods -o wide
```

4. **Comprobar la versión de API**:

```bash
kubectl --context "$KUBE_CONTEXT" api-versions
```

#### Procedimiento de reversión {#rollback-procedure}

La reversión de versión de EKS es una operación real iniciada por el usuario que se introdujo en julio de 2026. Use la [guía actual de reversión](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), no una afirmación general y antigua de que “no es posible bajar de versión”. Esto cambia la versión secundaria de Kubernetes; **no** restaura una instantánea anterior de etcd/datos de aplicaciones/PV ni revierte automáticamente los complementos. La versión de la plataforma pasa a ser la última versión de la plataforma para la versión secundaria anterior.

**Elegibilidad y preparación**

- Inicie la operación dentro de los **7 días posteriores a la finalización de la actualización in situ**. Un clúster creado en su versión actual no es apto. Solo se permite volver a la versión secundaria inmediatamente anterior; no se pueden encadenar reversiones a versiones secundarias más antiguas.
- El destino debe estar admitido. Para un destino con soporte extendido, adopte primero la política de soporte `EXTENDED` y tenga en cuenta los cargos. Las actualizaciones automáticas por fin del soporte extendido no se pueden revertir; las actualizaciones automáticas durante el soporte estándar tienen la condición documentada de política extendida.
- El clúster debe estar ACTIVE y no debe tener actualizaciones incompatibles en curso. Una función de EKS incompatible con versiones anteriores que esté habilitada en la nueva versión puede impedir la reversión. `--force` no puede omitir estos requisitos previos.
- Revise los datos de análisis de reversión, la compatibilidad de aplicaciones/clientes/CRD/webhooks, la diferencia de versiones de nodos y la compatibilidad de complementos. Las comprobaciones son puntuales y se realizan con el mejor esfuerzo; evite introducir cambios incompatibles mientras se lleva a cabo la reversión.

Los hallazgos ERROR/UNKNOWN de `ROLLBACK_READINESS` bloquean la reversión; WARNING solo es informativo. Esto contrasta con la retirada temporal del requisito que, ante hallazgos del análisis, obligaba a añadir la opción de forzado a las actualizaciones normales. La marca de reversión `--force` omite las comprobaciones de esos hallazgos (ERROR/WARNING/UNKNOWN), pero no vuelve seguro un plan inseguro ni elude los requisitos de elegibilidad o los controles de interrupción de Auto Mode. Resuelva los hallazgos siempre que sea posible y trate cualquier excepción como una decisión de riesgo explícita; no se incluye en los ejemplos habituales.

```bash
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
# Set INSIGHT_ID from the response to inspect one finding.
aws eks describe-insight --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --id "$INSIGHT_ID" --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

**Prepare los nodos y complementos antes del plano de control**

Los grupos de nodos administrados pueden revertirse con `UpdateNodegroupVersion`, según se describe en la guía actual de [grupos de nodos administrados](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html). Hágalo antes de bajar la versión del plano de control y verifique las versiones resultantes de nodos/AMI. El texto antiguo de la descripción general de la API aún indica que no hay reversión; la guía actual de reversión describe explícitamente este flujo de reversión de versión. No es una promesa general de que se pueda bajar a cualquier AMI histórica. Un grupo con AMI personalizada requiere la ruta revisada de su plantilla de lanzamiento original.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${ROLLBACK_VERSION:?Set the reviewed previous minor for the eligible rollback}"
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > node-rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' node-rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

La actualización de los nodos autoadministrados e híbridos es responsabilidad de quien opera el clúster. Auto Mode administra sus propios nodos antes de revertir el plano de control. No es posible revertir in situ los kubelets de Fargate: coordine la disponibilidad y los controladores (incluidos HPA, GitOps y Jobs) para evitar que se vuelvan a crear de inmediato Pods de Fargate incompatibles con la versión más reciente. Siga un plan de migración o mantenimiento probado y vuelva a crear los Pods después de revertir el plano de control. Un bucle sencillo que elimine Pods no basta. Omitir por la fuerza el análisis de diferencias de versiones de Fargate no hace que los kubelets más recientes sean compatibles con el servidor de API anterior.

EKS no revierte las versiones de complementos. Seleccione versiones puente/anteriores compatibles y una configuración revisada; use sus propios ID de actualización y comprobaciones funcionales. Los controladores/CRD autoadministrados requieren una evaluación independiente. No use OVERWRITE para todo ni suponga que un grupo de nodos AL2 antiguo es un plan de reversión.

**Solicitar y supervisar la reversión del plano de control**

Use `update-cluster-version` con la versión secundaria anterior aprobada; no hay un comando independiente `rollback-cluster`. Esta es una alternativa a solicitar una actualización, no un paso que deba ejecutarse automáticamente tras cada actualización. Establezca un tiempo de espera explícito y adecuado para el cliente y conserve el ID de actualización devuelto:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ROLLBACK_VERSION:?}"
: "${WAIT_TIMEOUT_SECONDS:?Set an explicit client wait for the approved rollback}"
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID WAIT_TIMEOUT_SECONDS
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

**Plazos y cancelación de Auto Mode**

Durante la reversión de nodos de Auto Mode, el clúster puede seguir en estado **ACTIVE** y luego pasar a UPDATING durante la fase del plano de control. Siga el ID de actualización durante todo el proceso. Los presupuestos de desviación de NodePool y las anotaciones do-not-disrupt de los nodos pueden bloquear su reemplazo; los PDB y las anotaciones do-not-disrupt de los Pods pueden retrasarlo, dentro de lo que permite `terminationGracePeriod`. Estos controles no garantizan por sí solos la disponibilidad de las aplicaciones. `--force` no los anula.

El valor predeterminado de `rollbackConfig.timeoutMinutes` de Auto Mode es **720** y acepta valores de **120–10080**. Es un tiempo de espera con un mínimo definido, no una fecha límite exacta. Cuando se agota, la actualización falla, el plano de control permanece en la versión actual y los nodos vuelven a converger hacia esa versión. La ventana original de siete días sigue siendo relevante al volver a intentarlo. La sintaxis de la opción siguiente se validó localmente con AWS CLI 2.36.44:

```bash
# Alternative Auto Mode request: do not run this as a second request after the preceding one.
# Select a reviewed timeout from 120 to 10080 minutes; default is 720 when omitted.
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --rollback-config timeoutMinutes=720 \
  --output json --no-cli-pager > rollback-update.json
```

Después de una solicitud de Auto Mode, use el ID devuelto y el mismo waiter; el plazo predeterminado de dos horas del script auxiliar es más corto que el tiempo de espera predeterminado de doce horas del servicio, así que elija deliberadamente el plazo del cliente. Los tiempos de espera de CI/IaC/credenciales no cancelan la operación de AWS. CancelUpdate está disponible solo durante la fase de nodos de Auto Mode, antes de la reversión del plano de control; es una operación de mejor esfuerzo y los nodos que ya estén sufriendo interrupciones completan su operación. Observe la transición Cancelling → Cancelled y la convergencia posterior de los nodos. Una actualización normal del plano de control o una reversión ya iniciada del plano de control no se pueden cancelar de esta manera.

```bash
# Only during the cancellable Auto Mode node phase, before control-plane rollback starts.
aws eks cancel-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" --output json --no-cli-pager
```

Una reversión de una pila de CloudFormation o una reversión de Git no inicia automáticamente una reversión de versión de EKS. Tras una recuperación explícita, reconcilie el estado/los planes de IaC con la versión observada. Si la reversión no es posible, evalúe una corrección progresiva o un clúster nuevo en una versión admitida, con migración/restauración probadas. Ninguno de estos mecanismos deshace automáticamente las migraciones de bases de datos ni los cambios en los datos de las aplicaciones.

## Automatización de actualizaciones {#upgrade-automation}

En entornos a gran escala, es importante automatizar el proceso de actualización. Puede automatizar las actualizaciones de EKS con las siguientes herramientas y métodos.

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagram of EKS upgrade automation branching into three paths -- eksctl, AWS CLI scripts, and GitOps -- each with its ordered cluster, add-on, and node group upgrade steps, plus the automation best practices that apply across all of them.](../.gitbook/assets/en-eks-08-eks-upgrades-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-6.html)
-->

### Automatización mediante eksctl

Use una configuración de eksctl revisada y las marcas correctas para cada operación. `upgrade cluster --approve` solicita el cambio del plano de control; sin `--approve`, el comando muestra una vista previa. La creación de grupos de nodos usa `--version`, mientras que `upgrade nodegroup` usa `--kubernetes-version`. Elija una sola herramienta/propietario para cada operación y luego verifique la actualización real de EKS y el estado de las cargas de trabajo. No ejecute una actualización de AWS CLI y otra de eksctl como solicitudes duplicadas consecutivas.

### Automatización mediante AWS CLI y scripts

El análisis previo de solo lectura, el sondeo de una actualización específica y los ejemplos de solicitud por componente anteriores son bloques de construcción. Un orquestador debe conservar sus resultados y detenerse ante fallas, tiempos de espera o validaciones incompletas. Debe usar versiones aprobadas de complementos/AMI/configuración en vez de basarse en el orden de una matriz, gestionar las diferencias de AMI personalizada y Auto/Fargate, y reanudar mediante el ID de actualización tras una falla del cliente. No debe afirmar que toda la actualización se completó porque un recurso pasó a estar ACTIVE. Este punto de entrada de inspección no inicia una actualización:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

### Automatización mediante GitOps

Git puede contener las versiones deseadas, evidencia de compatibilidad y runbooks revisados. Argo CD/Flux no convierte de forma nativa un archivo `ClusterConfig` de eksctl en un cambio del plano de control de EKS; se necesita un controlador o ejecutor compatible con AWS y con la autorización adecuada. Una reversión de Git/CloudFormation no revierte automáticamente una actualización de versión de EKS.

El siguiente flujo de trabajo se limita deliberadamente a la **recopilación en modo de solo lectura de datos para evaluar la preparación**. Antes de usarlo, incorpore a Git el archivo completo `eks-upgrade-preflight.py` mostrado anteriormente en `runbooks/eks-upgrade-preflight.py`. Provisione por separado el ejecutor de red privada de confianza y la cadena de herramientas revisada de AWS CLI/kubectl/Python. Las acciones fijadas usan Node.js 24; el ejecutor autohospedado debe admitir ese tiempo de ejecución. Configure las variables del repositorio y el entorno protegido `eks-upgrade-review`, y limite la confianza de OIDC a este repositorio/entorno y `sts.amazonaws.com`. El nombre de un entorno no crea por sí solo protecciones de revisión. Use un rol de inspección que tenga solo los permisos de lectura de EKS/STS necesarios y acceso para enumerar los nodos de Kubernetes; el ejemplo no necesita permisos para modificar la versión del clúster.

Revise el artefacto junto con las pruebas de aplicaciones/API/copias de seguridad/capacidad y, luego, use una fase de cambio separada y aprobada con los procedimientos por componente anteriores. Este flujo de trabajo no afirma que recopilar información correctamente equivalga a estar listo ni que se haya probado una actualización de producción. El acceso al artefacto debe corresponder a la sensibilidad de los metadatos de infraestructura/análisis; el kubeconfig aislado no se carga.

```yaml
name: Inspect EKS upgrade readiness
'on':
  workflow_dispatch:
    inputs:
      target_version:
        description: Reviewed next EKS minor version; inspection only
        required: true
        type: string
permissions:
  contents: read
  id-token: write
concurrency:
  group: eks-readiness-${{ vars.AWS_REGION }}-${{ vars.EKS_CLUSTER_NAME }}
  cancel-in-progress: false
jobs:
  inspect:
    runs-on:
    - self-hosted
    - linux
    - eks-upgrade
    environment: eks-upgrade-review
    timeout-minutes: 20
    env:
      CLUSTER_NAME: ${{ vars.EKS_CLUSTER_NAME }}
      AWS_REGION: ${{ vars.AWS_REGION }}
      EXPECTED_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}
      KUBE_CONTEXT: eks-upgrade-review
      TARGET_VERSION: ${{ inputs.target_version }}
    steps:
    - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
      with:
        persist-credentials: false
    - name: Assume the scoped review role
      uses: aws-actions/configure-aws-credentials@cbe3b392738ccf3f987d68400dafcf4b0624a56c
      with:
        role-to-assume: ${{ vars.EKS_REVIEW_ROLE_ARN }}
        aws-region: ${{ env.AWS_REGION }}
        allowed-account-ids: ${{ env.EXPECTED_ACCOUNT_ID }}
        unset-current-credentials: true
    - name: Prepare isolated context
      shell: bash
      run: "set -euo pipefail\numask 077\nEVIDENCE_DIR=\"$RUNNER_TEMP/eks-readiness-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT\"\
        \nKUBECONFIG=\"$EVIDENCE_DIR/kubeconfig\"\nexport EVIDENCE_DIR KUBECONFIG\n\
        mkdir -m 700 -p \"$EVIDENCE_DIR\"\nprintf 'EVIDENCE_DIR=%s\\nKUBECONFIG=%s\\\
        n' \"$EVIDENCE_DIR\" \"$KUBECONFIG\" >> \"$GITHUB_ENV\"\naws eks update-kubeconfig\
        \ --name \"$CLUSTER_NAME\" --region \"$AWS_REGION\" \\\n  --kubeconfig \"\
        $KUBECONFIG\" --alias \"$KUBE_CONTEXT\"\naws --version\nkubectl version --client\
        \ --output=json\npython3 --version"
      id: prepare
    - name: Collect review evidence
      shell: bash
      run: 'set -euo pipefail

        umask 077

        python3 runbooks/eks-upgrade-preflight.py > "$EVIDENCE_DIR/preflight.json"'
    - name: Preserve the review artifact
      if: ${{ always() && steps.prepare.outcome == 'success' }}
      uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
      with:
        name: eks-readiness-${{ github.run_id }}-${{ github.run_attempt }}
        path: ${{ env.EVIDENCE_DIR }}/preflight.json
        if-no-files-found: warn
        retention-days: 14
```

### Prácticas recomendadas para la automatización

Prácticas recomendadas para automatizar actualizaciones de EKS:

1. **Enfoque gradual**: comience con entornos que no sean de producción y avance hacia producción
2. **Plan de recuperación**: use un procedimiento de recuperación probado que tenga en cuenta la elegibilidad; no revierta versiones ni cambios de datos a ciegas
3. **Pasos de validación**: incluya pasos de validación automatizados después de la actualización
4. **Notificaciones**: configure notificaciones de éxito o falla de la actualización
5. **Documentación**: documente el proceso y los pasos de automatización

## Prácticas recomendadas para las actualizaciones {#upgrade-best-practices}

Veamos las prácticas recomendadas para actualizar clústeres de EKS.

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Tree diagram showing general EKS upgrade best practices across planning, preparation, execution, and post-upgrade, plus additional practices for large clusters and for financial-services compliance.](../.gitbook/assets/en-eks-08-eks-upgrades-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-7.html)
-->

### Prácticas recomendadas generales

#### Planificación de la actualización

1. **Selección de versión**: seleccione una versión estable y revise las notas de la versión
2. **Calendario de actualización**: programe la actualización durante períodos de poco tráfico
3. **Enfoque por fases**: comience con entornos que no sean de producción y avance hacia producción
4. **Planificación de la reversión**: cree un plan de reversión en caso de problemas

#### Preparación de la actualización

1. **Copia de seguridad**: haga copias de seguridad de los datos importantes
2. **Asignación de recursos**: asegure recursos suficientes para la actualización
3. **Comprobación de compatibilidad**: verifique la compatibilidad de las cargas de trabajo y los complementos
4. **Identificación de API obsoletas**: identifique y actualice las cargas de trabajo que usan API obsoletas

#### Ejecución de la actualización

1. **Preparación**: alinee las versiones actuales de los nodos y cualquier complemento/controlador puente necesario antes del cambio de destino
2. **Destino del plano de control**: solicite la siguiente versión secundaria admitida y verifique el ID de actualización
3. **Componentes dependientes**: actualice los nodos, los complementos/controladores restantes y los clientes según el orden de compatibilidad revisado
4. **Actualización gradual de nodos**: actualice los nodos gradualmente para minimizar las interrupciones de las cargas de trabajo

#### Después de la actualización

1. **Validación**: valide el estado del clúster y las cargas de trabajo
2. **Supervisión**: supervise el clúster después de la actualización
3. **Documentación**: documente el proceso y los resultados de la actualización
4. **Aprendizaje**: aprenda de los problemas encontrados durante la actualización y de sus soluciones

### Prácticas recomendadas para clústeres grandes

Prácticas recomendadas adicionales para actualizar clústeres grandes de EKS:

1. **Implementación canary**: comience con algunos nodos o cargas de trabajo y amplíe gradualmente
2. **Automatización**: automatice el proceso de actualización
3. **Supervisión mejorada**: supervise continuamente el estado del clúster durante la actualización
4. **Plan de comunicación**: comunique periódicamente el estado de la actualización a las partes interesadas
5. **Recuperación controlada**: automatice las comprobaciones de evidencia/elegibilidad y aplique la ruta de recuperación revisada; la reversión es condicional

### Prácticas recomendadas para servicios financieros

Prácticas recomendadas adicionales para actualizar clústeres de EKS en el sector de servicios financieros:

1. **Cumplimiento normativo**: asegúrese de que la actualización cumpla los requisitos normativos
2. **Evaluación de riesgos**: realice una evaluación de riesgos antes de la actualización
3. **Gestión de cambios**: siga procesos estrictos de gestión de cambios
4. **Pruebas exhaustivas**: realice pruebas exhaustivas antes de la actualización
5. **Documentación detallada**: documente detalladamente el proceso y los resultados de la actualización

## Conclusión

Actualizar correctamente un clúster de Amazon EKS requiere una planificación, preparación y validación exhaustivas. En este documento se describen estrategias, pasos y prácticas recomendadas para actualizar de forma segura el plano de control, los grupos de nodos y los complementos de un clúster de EKS.

Puntos clave:

1. **Descripción general de las actualizaciones de EKS**: administración de versiones de EKS, componentes y ruta de actualización
2. **Planificación y preparación de la actualización**: evaluación, preparación y pruebas de la actualización
3. **Actualización del plano de control de EKS**: métodos de actualización y supervisión del plano de control
4. **Actualización del grupo de nodos**: estrategias para actualizar grupos de nodos administrados y autoadministrados
5. **Actualización de complementos**: actualizaciones de complementos administrados por AWS y autoadministrados
6. **Validación y solución de problemas de la actualización**: validación de la actualización y resolución de problemas comunes
7. **Automatización de actualizaciones**: automatización mediante eksctl, AWS CLI y GitOps
8. **Prácticas recomendadas para las actualizaciones**: prácticas generales y específicas del sector

Mantener actualizado el clúster de EKS permite obtener parches de seguridad, correcciones de errores y nuevas funciones, y contribuye a mejorar su seguridad, estabilidad y rendimiento.

## Referencias

- [Documentación de actualización de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Versiones de Kubernetes y diferencia de versiones](https://kubernetes.io/docs/setup/release/version-skew-policy/)
- [Actualización de grupos de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Actualización de complementos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managing-add-ons.html)
- [Documentación de eksctl](https://eksctl.io/usage/cluster-upgrade/)
- [Prácticas recomendadas para actualizar Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/cluster-upgrade/)

## Cuestionario

Para poner a prueba lo que aprendió en este capítulo, pruebe el [cuestionario del tema](../quizzes/eks/08-eks-upgrades-quiz.md).
