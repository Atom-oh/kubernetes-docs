# Actualizaciones de Amazon EKS

> **Última actualización**: 12 de octubre de 2026

Mantener actualizado el clúster de Amazon EKS es importante para la seguridad y la estabilidad, y permite aprovechar las nuevas funciones. Este documento presenta estrategias, prácticas recomendadas y guías paso a paso para actualizar clústeres de EKS de forma segura.

Estos procedimientos fueron revisados por sus responsables; no se ejecutó ninguna actualización durante esta auditoría. Use un contexto explícito de cuenta, Región y Kubernetes, registre las versiones de origen y destino aprobadas y los ID de actualización, y valide el comportamiento de las aplicaciones. No ejecute consecutivamente todos los ejemplos alternativos sobre los mismos recursos. El análisis local y las simulaciones no demuestran que la solución esté lista para producción.

## Tabla de contenido

1. [Descripción general de las actualizaciones de EKS](#eks-upgrade-overview)
2. [Planificación y preparación de la actualización](#upgrade-planning-and-preparation)
3. [Actualización del plano de control de EKS](#eks-control-plane-upgrade)
4. [Actualización de grupos de nodos](#node-group-upgrade)
5. [Actualización de complementos](#add-on-upgrade)
6. [Validación y solución de problemas de la actualización](#upgrade-validation-and-troubleshooting)
7. [Automatización de las actualizaciones](#upgrade-automation)
8. [Prácticas recomendadas para las actualizaciones](#upgrade-best-practices)

## Descripción general de las actualizaciones de EKS {#eks-upgrade-overview}

![Diagrama en árbol de los cuatro pilares de una actualización de EKS: política de administración de versiones, componentes que se actualizan (plano de control, grupos de nodos, complementos y componentes autoadministrados), ruta de actualización de una versión menor a la vez frente a un salto de versión no admitido y orden de actualización de cinco pasos.](../.gitbook/assets/en-eks-08-eks-upgrades-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-0.html)

### Administración de versiones de EKS

EKS usa la numeración de versiones de Kubernetes y cuenta con su propio calendario de lanzamientos y soporte. Cada versión menor recibe **14 meses de soporte estándar**, seguidos de **12 meses de soporte extendido** con un cargo adicional. AWS anuncia el fin del soporte estándar con al menos 60 días de antelación. Consulte el [catálogo y calendario actuales de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html); una versión del proyecto upstream de Kubernetes no está disponible automáticamente en EKS. Evite dar por sentado que hay un «mínimo de cuatro versiones» o considerar que los 14 meses corresponden a todo el ciclo de soporte.

### Anuncios recientes sobre actualizaciones de EKS (2026)

- **Kubernetes 1.37 disponible (1 de octubre de 2026)**: EKS 1.37 ya es un destino admitido. En Auto Mode, los NodePools personalizados recién creados que omiten una política de consolidación tienen `Balanced` como valor predeterminado; los grupos integrados `general-purpose` y `system` también usan `Balanced`. Los montajes de volúmenes SELinux son estables y están habilitados de forma predeterminada para las configuraciones compatibles de CSI y Pod. Antes de actualizar, revise el comportamiento previsto de NodePool y los requisitos de SELinux/CSI para las cargas de trabajo que comparten volúmenes con etiquetas distintas. Consulte la sección sobre Kubernetes 1.37 de las [notas de lanzamiento de soporte estándar de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html) y el [calendario de soporte](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html).
- **Compatibilidad con la reversión de versiones de Kubernetes (1 de julio de 2026)**: Si una actualización causa problemas, ahora puede revertir el plano de control a la versión menor anterior en un plazo de 7 días. Antes, EKS ejecuta una comprobación automatizada de preparación para la reversión que abarca la compatibilidad de la API, la diferencia de versiones, la compatibilidad de los complementos y el estado del clúster. En una reversión iniciada por el usuario, Auto Mode reemplaza los nodos de trabajo que cumplen los requisitos antes de revertir el plano de control; no se trata de una reacción automática ante fallos de las aplicaciones. Siguen aplicándose los requisitos de elegibilidad y los controles de interrupciones. La función no tiene ningún cargo adicional en las Regiones donde se ofrece EKS; siguen aplicándose los cargos por nodos/almacenamiento y los cargos pertinentes de soporte de versiones. Consulte más abajo el [Procedimiento de reversión](#rollback-procedure) para obtener más información. (Fuente: [Amazon EKS anuncia la reversión de versiones de Kubernetes](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-version-rollback))
- **SLA del 99,99 % y nivel 8XL del plano de control (20 de marzo de 2026)**: El SLA de los clústeres Provisioned Control Plane aumentó del 99,95 % al 99,99 % y se mide con una granularidad de un minuto. Un nuevo nivel de escalado 8XL duplica la capacidad de gestión de solicitudes de API del nivel 4XL anterior, con el objetivo de atender clústeres muy grandes y cargas de trabajo de IA/ML/HPC. (Fuente: [Amazon EKS anuncia el SLA y el nivel de escalado 8XL](https://aws.amazon.com/about-aws/whats-new/2026/03/amazon-eks-announces-sla-8xl-scaling-tier/))

### Componentes que se actualizan

Las actualizaciones de clústeres de EKS incluyen los siguientes componentes:

1. **Plano de control de EKS**: servidor de API de Kubernetes, etcd, administrador de controladores, etc.
2. **Grupos de nodos**: nodos de trabajo y AMI de nodos
3. **Complementos**: complementos administrados por AWS (por ejemplo, CoreDNS, kube-proxy y VPC CNI)
4. **Componentes autoadministrados**: Helm Charts, recursos personalizados, etc.

### Ruta de actualización

Los clústeres de EKS deben actualizarse de una versión menor a la siguiente:

- Ejemplo histórico: 1.24 → 1.25 → 1.26 → 1.27 muestra el patrón de avanzar una versión menor a la vez; estas no son versiones de destino actuales para implementaciones.
- El salto directo de 1.24 → 1.26 ilustra que no se admite omitir una versión menor.
- Para un cambio real, elija la siguiente versión menor que EKS ofrezca en su Región conforme a la política de soporte.

### Orden de actualización

1. Inventariar, probar y hacer copias de seguridad; resolver las actualizaciones activas y alinear los nodos con la versión menor **actual** del plano de control, como flujo de preparación conservador.
2. Aplicar las versiones puente necesarias de complementos/controladores que sean compatibles tanto con la versión actual como con la versión de destino de Kubernetes; verificar los requisitos previos específicos de cada componente.
3. Actualizar el plano de control una versión menor admitida y esperar a que la actualización con ese ID finalice correctamente.
4. Actualizar los nodos, los clientes/controladores y los complementos restantes según el orden de dependencias verificado, y comprobar cada paso. Auto Mode administra sus funciones integradas e inicia las actualizaciones de nodos después de la actualización del plano de control.
5. Validar las versiones reales de los nodos, la preparación de las cargas de trabajo, el tráfico, el almacenamiento y los SLO.

Para kubelet 1.25 y versiones posteriores, el proyecto upstream de Kubernetes permite que las versiones de kubelet estén hasta tres versiones menores por detrás del servidor de API, pero nunca por delante; si hay varias versiones del servidor de API, el rango permitido se reduce. La documentación de EKS incluye tanto la recomendación de alinear los nodos antes de actualizar como el margen de diferencia de versiones admitido. Este procedimiento elige la alineación como política de preparación; no afirma que la API de EKS rechace universalmente todas las diferencias de versiones admitidas. No todos los complementos deben actualizarse necesariamente «antes» o «después» del plano de control. La reversión tiene una secuencia distinta, con los nodos primero, descrita más abajo.

## Planificación y preparación de la actualización {#upgrade-planning-and-preparation}

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagrama en árbol que muestra la planificación y preparación de la actualización divididas en una rama de evaluación de la actualización (comprobación de compatibilidad de versiones, requisitos de recursos y planificación del calendario) y una rama de preparación previa a la actualización (comprobación del estado del clúster, creación de una copia de seguridad, prueba de la actualización y documentación de la actualización).](../.gitbook/assets/en-eks-08-eks-upgrades-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-1.html)
-->

### Evaluación de la actualización

Antes de iniciar una actualización, evalúe lo siguiente:

#### Comprobación de compatibilidad de versiones

Compruebe la compatibilidad con la versión de destino de Kubernetes:

- **API en desuso**: identifique las cargas de trabajo que usan API obsoletas
- **Cambios en las funciones**: revise los cambios de funciones de la nueva versión
- **Compatibilidad de complementos**: verifique que los complementos sean compatibles con la versión de destino

Una lista de imágenes o `kubectl get … .apiVersion` no constituye una auditoría de API obsoletas para clientes/API: el servidor de API devuelve las representaciones negociadas/actuales. Una API beta no está obsoleta automáticamente. Revise los manifiestos de origen/Helm, los clientes, las CRD, los webhooks y la información de actualización de EKS teniendo en cuenta la versión de destino. Una sola captura de métricas del servidor de API es únicamente evidencia observada; la ausencia de datos o un error no demuestra que no haya uso de API obsoletas.

Guarde el siguiente recopilador de solo lectura como `eks-upgrade-preflight.py`. Exporte `CLUSTER_NAME`, `AWS_REGION`, `EXPECTED_ACCOUNT_ID`, `KUBE_CONTEXT` y `TARGET_VERSION`; guarde el JSON con permisos locales restringidos. Si finaliza correctamente, significa que la recopilación tuvo éxito, no que la actualización esté aprobada ni que todas las cargas de trabajo sean compatibles.

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

#### Evaluación de los requisitos de recursos

Evalúe los recursos necesarios para la actualización:

- **Capacidad del clúster**: capacidad suficiente para admitir nodos adicionales durante la actualización
- **Tolerancia al tiempo de inactividad**: determine si las cargas de trabajo pueden tolerar tiempos de inactividad
- **Plan de reversión**: plan de reversión en caso de problemas

#### Planificación del calendario de actualización

Planifique el calendario de actualización:

- **Ventana de mantenimiento**: programe la actualización durante períodos de poco tráfico
- **Enfoque por fases**: empiece por los entornos que no son de producción y avance hacia producción
- **Ventana de reversión**: planifique el tiempo necesario para revertir en caso de problemas

### Preparación previa a la actualización

#### Comprobar el estado del clúster

Compruebe el estado del clúster antes de actualizar:

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

Haga una copia de seguridad de los datos importantes antes de actualizar:

EKS administra el etcd del plano de control administrado; un comando `etcd-pod`/`etcdctl snapshot` en su espacio de nombres no puede crear una copia de seguridad. Además, `kubectl get all` omite recursos importantes y datos de volúmenes, por lo que no constituye una copia de seguridad completa.

[AWS Backup for EKS](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html) puede proteger el estado del clúster y los recursos de EBS/EFS/S3 respaldados por PVC mediante puntos de recuperación compuestos, con los requisitos previos documentados de IAM, acceso API/API_AND_CONFIG_MAP, almacenamiento y restauración. Como alternativa, use una configuración propia de Velero/copia de seguridad de aplicaciones con cobertura de volúmenes y credenciales verificadas. Revise la cobertura de recursos con alcance de espacio de nombres/clúster, la coherencia de las bases de datos, la retención y las pruebas de restauración. Que una solicitud de copia de seguridad devuelva un ID no demuestra que se haya completado ni que permita recuperar los datos.

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
![Diagrama de una actualización del plano de control de EKS dividida en cuatro etapas —preparación, ejecución, supervisión y solución de problemas—, cada una con sus pasos agrupados: comprobaciones de versiones y planificación, Console/CLI/eksctl, estado, supervisión del estado del clúster y de CloudWatch, y problemas comunes con sus pasos para solucionarlos.](../.gitbook/assets/en-eks-08-eks-upgrades-2.png)

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

Antes de enviar una actualización normal, revise las [directrices actuales de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html): se ha retirado temporalmente la aplicación del requisito de usar `--force` para las observaciones de información de actualización. Esto difiere de las reglas bloqueantes `ROLLBACK_READINESS` para la reversión de versiones. Resuelva las observaciones o evalúelas explícitamente; la evidencia móvil de los últimos 30 días sobre API obsoletas puede permanecer después de corregir el problema. Asegúrese de que las subredes del clúster existan, tengan las direcciones de reserva necesarias (EKS puede requerir hasta cinco) y permitan la comunicación del plano de control. Una actualización del plano de control que ya se inició no se puede pausar ni detener; los clientes deben gestionar las reconexiones.

Cree un plan de actualización del plano de control:

- Hora de la actualización: seleccione períodos de poco tráfico
- Configuración de la supervisión: supervise el estado del clúster durante la actualización
- Plan de reversión: procedimiento de reversión en caso de problemas

### Ejecución de la actualización del plano de control

#### Actualizar mediante AWS Management Console

1. Inicie sesión en AWS Management Console
2. Vaya al servicio Amazon EKS
3. Seleccione en la lista el clúster que desea actualizar
4. Seleccione la pestaña «Cluster configuration»
5. Haga clic en «Update Kubernetes version»
6. Seleccione la versión de destino y haga clic en «Update»

#### Actualizar mediante AWS CLI

Ejecute el comando solo después de aprobar el plan registrado y sus condiciones previas. Guarde el asistente de sondeo de la sección siguiente como `eks-wait-update.py`. Esto solo solicita la actualización del plano de control; no actualiza nodos ni complementos ni demuestra que las cargas de trabajo estén listas.

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

#### Actualizar mediante eksctl

```bash
eksctl upgrade cluster \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --version "$TARGET_VERSION" \
  --approve
```

### Supervisión de la actualización del plano de control

#### Comprobar el estado de la actualización

Compruebe el estado de la actualización:

Haga un seguimiento de `DescribeUpdate` usando el ID exacto de la actualización. Que el clúster o el grupo de nodos estén `active` no demuestra que esta solicitud haya tenido éxito, y AWS CLI 2.36.44 no cuenta con un waiter `eks wait update-successful`. Guarde este código como `eks-wait-update.py`; para una solicitud de grupo de nodos o complemento, establezca exactamente una de `NODEGROUP_NAME` o `ADDON_NAME`; en caso contrario, deje ambas sin definir. El código falla ante errores de la API, fallos/cancelaciones, estados desconocidos o al vencer el plazo del cliente. Un timeout del cliente no cancela la operación de AWS. El tiempo de espera predeterminado de dos horas del cliente debe ajustarse a la operación aprobada, especialmente en el caso de reversiones prolongadas de Auto Mode.

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

Supervise las métricas del plano de control que se publiquen realmente para su versión/nivel de EKS y la telemetría que haya configurado: tasa/latencia/errores de las solicitudes de API, preparación de la API para atender solicitudes y reconexiones de clientes, programación, estado de nodos/cargas de trabajo y SLO de las aplicaciones. No dé por sentado que se exponen directamente los puntos de conexión de etcd/administrador de controladores ni todas las métricas de los componentes. `/readyz` comprueba si la API está lista para atender solicitudes, no todas las condiciones de las aplicaciones ni la disponibilidad histórica.

### Solución de problemas de la actualización del plano de control

#### Problemas comunes

Problemas comunes que pueden producirse durante la actualización del plano de control:

- **Fallo de la actualización**: el proceso de actualización falla o se interrumpe
- **Disponibilidad del servidor de API**: problemas de disponibilidad del servidor de API durante la actualización
- **Problemas de compatibilidad**: problemas de compatibilidad entre las cargas de trabajo y la nueva versión

#### Pasos para solucionar problemas

1. Compruebe el estado de la actualización
2. Revise los registros de CloudTrail
3. Revise los registros del plano de control de EKS
4. Póngase en contacto con AWS Support

## Actualización de grupos de nodos {#node-group-upgrade}

Después de actualizar el plano de control, debe actualizar los grupos de nodos. Hay varias estrategias para actualizar grupos de nodos, cada una con sus ventajas e inconvenientes.

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagrama que muestra la actualización de grupos de nodos dividida en cinco ramas —estrategias, administrados, autoadministrados, Fargate, y supervisión y validación—, con la rama de estrategias desglosada en enfoques administrados, autoadministrados y de Fargate.](../.gitbook/assets/en-eks-08-eks-upgrades-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-3.html)
-->

### Estrategias para actualizar grupos de nodos

#### Actualización de grupos de nodos administrados

Los grupos de nodos administrados son una función de administración de grupos de nodos proporcionada por AWS que automatiza las actualizaciones de nodos:

- **Estrategia de reemplazo**: `maxUnavailable`/porcentaje permite el reemplazo en paralelo. La API `updateStrategy=DEFAULT` lanza nueva capacidad antes de retirar la anterior; `MINIMAL` retira primero la capacidad anterior y ofrece distintas ventajas y desventajas en términos de disponibilidad/capacidad.
- **Drenaje**: las actualizaciones normales usan la expulsión de Pod y comprueban los PDB; los controladores vuelven a crear los Pod en vez de migrarlos en vivo. La opción de forzado del grupo de nodos puede omitir los fallos de drenaje relacionados con PDB; no equivale a la marca de forzado de la reversión del clúster.
- **Selección de versión/AMI**: elija la versión de Kubernetes y la versión de AMI revisadas, o una versión nueva de la plantilla de lanzamiento original para AMI personalizadas. Que falle una actualización no demuestra que se haya revertido automáticamente toda la flota; inspeccione los estados mixtos de nodos/AMI y los errores de actualización.

#### Actualización de grupos de nodos autoadministrados

En los grupos de nodos autoadministrados, debe actualizar manualmente los nodos:

- **Implementación Blue/Green**: cree un grupo de nodos nuevo y migre las cargas de trabajo
- **Actualización gradual**: drene y termine los nodos de uno en uno y reemplácelos por nodos nuevos
- **Actualización local**: actualice kubelet y el tiempo de ejecución de contenedores en los nodos existentes

#### Actualización de nodos de Fargate

AWS es responsable de la infraestructura de nodos de Fargate, pero el responsable de la carga de trabajo debe coordinar el reemplazo de Pod. Los Pod de Fargate que se lancen después usarán una versión de kubelet que coincida con el plano de control; la operación de actualización del plano de control no actualiza los Pod existentes. Planifique las implementaciones graduales de controladores, la disponibilidad y la validación; no dé por hecho que Fargate no requiere ningún trabajo de actualización. Auto Mode es diferente: inicia su propio reemplazo incremental de nodos tras una actualización del plano de control, sujeto a sus controles de interrupción.

### Actualización de grupos de nodos administrados

#### Comprobar la versión del grupo de nodos administrado

Compruebe la versión actual del grupo de nodos administrado:

```bash
aws eks describe-nodegroup \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query "nodegroup.version"
```

#### Actualizar mediante AWS Management Console

1. Inicie sesión en AWS Management Console
2. Vaya al servicio Amazon EKS
3. Seleccione en la lista el clúster que desea actualizar
4. Seleccione la pestaña «Compute»
5. Seleccione el grupo de nodos que desea actualizar
6. Haga clic en «Update node group»
7. Seleccione la versión de destino y haga clic en «Update»

#### Actualizar mediante AWS CLI

Para una AMI optimizada para EKS, use la versión de lanzamiento y la versión de destino revisadas. Esta operación tiene su propio ID de actualización; mantenga el ámbito del grupo de nodos al sondear el estado. Revise la compatibilidad con la plataforma/familia de AMI; cambiar la versión de Kubernetes no migra un grupo de nodos AL2 a AL2023.

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

Para una **AMI personalizada**, actualice la plantilla de lanzamiento original a una versión nueva revisada. No incluya `version` ni `releaseVersion` de Kubernetes en esa solicitud de AMI personalizada; verifique el kubelet/tiempo de ejecución/AMI reales en los nodos de reemplazo.

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

#### Actualizar mediante eksctl

```bash
eksctl upgrade nodegroup \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name "$NODEGROUP_NAME" \
  --kubernetes-version "$TARGET_VERSION"
```

#### Configuración de la actualización de grupos de nodos administrados

Puede configurar el comportamiento de actualización de los grupos de nodos administrados:

- **Máximo de nodos no disponibles**: cantidad máxima de nodos no disponibles durante la actualización
- **PDB**: limita las expulsiones voluntarias que cumplen los requisitos, pero no todos los fallos ni los resultados de las aplicaciones. Una actualización forzada del grupo de nodos puede ignorar un problema de PDB. Cambiar la configuración de escalado deseada/máxima/mínima de un grupo de nodos administrado es una operación de escalado de ASG y **no** ofrece las garantías de drenaje/PDB de una actualización; no use un cambio de tamaño a cero como si fuera una migración segura.

```bash
aws eks update-nodegroup-config \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --update-config maxUnavailable=1
```

### Actualización de grupos de nodos autoadministrados

#### Implementación Blue/Green

Prepare un grupo de nodos nuevo con un nombre distinto a partir de la configuración propietaria, y conserve los requisitos revisados de subred/zona, IAM, arquitectura/inicialización de AMI, etiquetas, taints, almacenamiento y red. Consulte la [guía de creación de clústeres](02-eks-cluster-creation.md). De forma predeterminada, `eksctl create nodegroup` crea un grupo administrado; para crear un grupo autoadministrado, la configuración debe seleccionar explícitamente `--managed=false` o la sección apropiada `nodeGroups`. La creación usa `--version`, mientras que `eksctl upgrade nodegroup` usa `--kubernetes-version`.

1. Cree capacidad green a partir de la configuración revisada y, luego, compruebe la cantidad de nodos, el kubelet/AMI de destino, el estado Ready, CNI/DNS y la programación de las aplicaciones. Limitarse a enumerar los nodos no basta para esta validación.
2. Mueva las cargas de trabajo por fases bajo el control de sus responsables. Una afinidad preferida no garantiza que se coloquen en green; inspeccione las asignaciones reales de Pod a nodos y la topología del almacenamiento.
3. Drene un nodo antiguo identificado a la vez, con un tiempo de espera limitado; deténgase si falla una expulsión o una comprobación de estado. Vuelva a validar las cargas de trabajo/la capacidad de reemplazo antes de continuar.
4. Retire el grupo antiguo solo después de registrar la aceptación de la migración, el estado, la retención de datos y la recuperación. No lo elimine automáticamente después de un bucle sin comprobaciones o de una espera fija.

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

De forma predeterminada, este drenaje se niega a proceder en casos de Pod no administrados/datos locales que requieren una decisión aparte. `--delete-emptydir-data` permite explícitamente perder los datos de emptyDir; no lo añada sin evaluar la situación. `kubectl drain --force` permite Pod no administrados y no equivale a omitir las comprobaciones de expulsión/PDB. Coordine los DaemonSets, los Pod estáticos, los controladores y los datos persistentes con sus responsables.

#### Actualización gradual

Para un ASG autoadministrado, primero actualice la configuración/plantilla de lanzamiento que administra al AMI validado; de lo contrario, los reemplazos podrían iniciar de nuevo con la imagen antigua. Use la compuerta de drenaje de un solo nodo anterior y verifique el ID del proveedor del nodo, la instancia de EC2 y la propiedad del ASG antes de terminar cualquier instancia. No asigne un nodo de Kubernetes al primer resultado de búsqueda por nombre DNS privado de EC2. Pida al responsable del ASG que reemplace la instancia drenada y espere a que aparezca un nodo **nuevo**, correctamente configurado y Ready, y a que se recuperen las cargas de trabajo, antes de continuar. Esperar 60 segundos no demuestra que el reemplazo esté listo. El escalado directo del ASG/la actualización de instancias requiere la integración de drenaje de Kubernetes correspondiente; no aplica automáticamente un PDB.

#### Actualización local

Use un procedimiento específico del sistema operativo/imagen que se haya probado por separado, y solo en hosts autoadministrados que lo admitan. Para las flotas administradas optimizadas para EKS, prefiera una ruta de reemplazo con AMI inmutable y validada; Auto Mode/Fargate administra la infraestructura del servicio. Un comando genérico `yum update kubelet kubectl` no selecciona una versión revisada de Kubernetes/tiempo de ejecución ni constituye una actualización de nodo de EKS. Una solicitud de SSM es asíncrona: no quite la marca de no programable del nodo hasta que se hayan completado correctamente su invocación, los reinicios necesarios de servicios, las versiones reales, la preparación del nodo y las pruebas de cargas de trabajo. Conserve las pruebas del fallo en lugar de quitar automáticamente esa marca o terminar el nodo tras un error.

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

#### Comprobar la implementación de los Pod

Verifique que los Pod se hayan implementado con normalidad:

```bash
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces -o wide
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,PHASE:.status.phase,READY:'.status.conditions[?(@.type=="Ready")].status'
```

## Actualización de complementos {#add-on-upgrade}

Haga un inventario de los responsables reales de los componentes y de sus rutas de actualización. La actualización del plano de control no actualiza automáticamente las versiones de los complementos administrados por EKS; el responsable selecciona e inicia una actualización compatible. Las versiones puente necesarias pueden instalarse antes del cambio del plano de control. AWS administra por separado las funciones integradas de Auto Mode; no instale ni actualice componentes de red/almacenamiento/DNS duplicados para nodos como si todos los clústeres usaran los mismos DaemonSets/Deployments.

![Diagrama que muestra la división de las actualizaciones de complementos en complementos administrados por AWS (comprobar las versiones y, después, actualizar con update-addon o eksctl), complementos autoadministrados (Helm o kubectl), guías para complementos clave (CoreDNS, kube-proxy, VPC CNI) y solución de problemas (problemas comunes y pasos para solucionarlos).](../.gitbook/assets/en-eks-08-eks-upgrades-4.png)

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

Compruebe las versiones disponibles de los complementos:

El primer elemento de una matriz no garantiza que sea la versión «más reciente» ni la correcta. Revise `compatibilities`, los indicadores de versión predeterminada, la compatibilidad con la plataforma/tipo de cómputo/arquitectura, las notas de lanzamiento, los cambios de IAM y los requisitos de versiones intermedias. Antes de cambiar el complemento, capture su configuración y las asociaciones de identidad. Guarde los archivos con permisos restringidos; la configuración puede contener valores confidenciales.

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

Puede actualizar los complementos administrados mediante AWS Management Console, AWS CLI o eksctl:

Valide el JSON candidato con el esquema de destino y conserve la semántica prevista de configuración/identidad. `PRESERVE` se aplica a conflictos en campos administrados; no valida todos los valores personalizados, no garantiza el comportamiento de las aplicaciones ni fusiona una configuración parcial explícita con el JSON anterior. Pasar `{}` puede restablecer la configuración. Actualice un solo complemento a la vez bajo la responsabilidad de su propietario y compruebe su ID de actualización, estado, versión y comportamiento de las cargas de trabajo.

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

En eksctl 0.229, `update addon` admite `--wait` y `--config-file`, pero no la opción `--preserve`. Incluya la política de resolución de conflictos prevista en una configuración de eksctl revisada, o use el procedimiento explícito de AWS CLI anterior. `eksctl --force` migra la propiedad de un complemento autoadministrado y no es una opción genérica para preservar conflictos.

### Complementos autoadministrados

#### Actualizar complementos autoadministrados

Actualice los complementos autoadministrados mediante Helm o kubectl:

Use el responsable existente de Helm/manifiestos. El ejemplo presupone un repositorio/referencia OCI del chart revisados y un lanzamiento existente; intencionalmente no usa `--install` para crear un segundo administrador si falta el lanzamiento. Revise los requisitos de migración de CRD e IAM del nuevo chart; `helm upgrade` por sí solo no actualiza las CRD que estén en el directorio `crds/` de un chart. Helm y la implementación de manifiestos sin procesar son alternativas, no pasos consecutivos de actualización. El ejemplo anterior de Metrics Server 0.6.1/3.8.2 no representa una selección de versiones compatibles de destino.

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

### Guías para actualizar complementos clave

#### Actualización de CoreDNS

En los nodos estándar, determine si EKS u otra herramienta administra el Deployment de CoreDNS; conserve la configuración de Corefile/PDB/personalizada y siga las notas de migración de la versión elegida. En los nodos de Auto Mode, CoreDNS se ejecuta como servicio del sistema del nodo: un clúster exclusivamente de Auto Mode no requiere el complemento Deployment, mientras que un clúster mixto debe conservar DNS para los nodos que no sean de Auto Mode. No interprete la falta de un Deployment en un clúster exclusivamente de Auto Mode como una actualización fallida.

#### Actualización de kube-proxy

Mantenga kube-proxy compatible con el servidor de API y los nodos donde se ejecuta; su versión no debe ser posterior a la del servidor de API. Use la versión admitida del complemento para el destino y el orden verificado. Auto Mode administra las redes de servicio; no dé por hecho que allí exista un DaemonSet de kube-proxy autoadministrado.

#### Actualización de VPC CNI

En los nodos EC2 estándar, verifique la ruta de versiones de CNI, el modo IP/prefijo, IAM, la configuración de políticas de red y la conectividad de las cargas de trabajo. No dé por sentado que un solo ConfigMap `aws-node` contiene todos los ajustes: incluya `configurationValues` de EKS, la configuración del DaemonSet/contenedor, la identidad de la cuenta de servicio y la configuración propietaria de Helm/GitOps cuando corresponda. La red integrada de Auto Mode sigue su propia ruta de administración.

Use el proceso genérico de captura/selección/actualización/espera anterior para cada complemento administrado por EKS. Inspeccione los agentes de nodos estándar únicamente donde estén instalados:

```bash
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset kube-proxy aws-node -o wide
```

### Solución de problemas de la actualización de complementos

#### Problemas comunes

Problemas comunes que pueden producirse durante la actualización de complementos:

- **Conflictos de configuración**: conflictos entre la configuración personalizada y la nueva versión
- **Problemas de compatibilidad**: problemas de compatibilidad entre el complemento y la versión de Kubernetes
- **Limitaciones de recursos**: recursos insuficientes para la actualización

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

Cuando finalice la actualización, debe validar que el clúster funcione con normalidad y resolver los problemas que puedan surgir.

![Diagrama en árbol que divide el trabajo posterior a la actualización en Validación de la actualización (versión del clúster, estado del clúster, validación de las cargas de trabajo y pruebas funcionales) y Solución de problemas de la actualización (problemas comunes de actualización, pasos para solucionar problemas y procedimiento de reversión).](../.gitbook/assets/en-eks-08-eks-upgrades-5.png)

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

#### Validación de las cargas de trabajo

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

Use recursos de prueba aislados y propios, y criterios de aceptación explícitos. La siguiente **prueba básica de nodos EC2 Linux** abarca el despliegue/escalado de Deployment, solicitudes de Service/DNS y datos de PVC entre Jobs separados. No es una prueba de carga, no prueba todos los nodos/AZ ni demuestra que la aplicación, la alta disponibilidad o la seguridad sean correctas. Añada pruebas específicas de las cargas de trabajo, de entrada/salida, de controladores/webhooks y de recuperación. Las rutas de Fargate/híbridas/otras plataformas necesitan su propio plan de pruebas compatible.

Guarde el código como `eks-upgrade-smoke.py`. Usa el manifiesto de la imagen oficial BusyBox fijada que se verificó para esta auditoría; aquí no se ejecutó ninguna imagen ni prueba de clúster. Antes de ejecutarlo, verifique las políticas de imágenes, las reglas de admisión/red, la capacidad disponible y una StorageClass con sistema de archivos compatible en los nodos seleccionados. Establezca `KUBE_CONTEXT`, `TEST_STORAGE_CLASS`, `RUN_SMOKE_TEST=yes` y un mapa JSON revisado `SMOKE_NODE_SELECTOR` si va a probar nodos de reemplazo específicos. El script crea un espacio de nombres único, nunca adopta uno existente, se detiene ante fallos y registra los detalles de colocación real y recuperación del PV. Los volúmenes `WaitForFirstConsumer` reciben un Pod consumidor que escribe en ellos antes de esperar a que finalice la operación.

Los recursos se conservan de forma predeterminada para su revisión. `CLEANUP_ON_SUCCESS=yes` elimina solo el UID del espacio de nombres creado por esa ejecución y únicamente después de que las comprobaciones finalicen correctamente. La eliminación del espacio de nombres puede dejar PV/almacenamiento facturable si la clase usa Retain; inspeccione el PV registrado y limpie solo el almacenamiento de prueba propio. Los fallos se conservan para su diagnóstico; no se notifican como éxitos. Las métricas actuales de corto plazo y 20 solicitudes HTTP secuenciales no demuestran equivalencia de rendimiento.

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

#### Problemas comunes de actualización

Problemas comunes que pueden producirse durante la actualización:

1. **Fallo de la actualización del plano de control**:
   - Problemas de disponibilidad del servidor de API
   - Problemas con la base de datos etcd
   - Problemas con los permisos de IAM

2. **Problemas en la actualización de nodos**:
   - Fallo al drenar nodos
   - Fallo al iniciar nodos nuevos
   - Diferencia de versiones de kubelet

3. **Problemas en la actualización de complementos**:
   - Conflictos de configuración
   - Problemas de compatibilidad
   - Limitaciones de recursos

4. **Problemas de cargas de trabajo**:
   - Fallo de una carga de trabajo debido al uso de una API en desuso
   - Fallo de programación de Pod debido a limitaciones de recursos
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

4. **Comprobar las versiones de API**:

```bash
kubectl --context "$KUBE_CONTEXT" api-versions
```

#### Procedimiento de reversión {#rollback-procedure}

La reversión de versiones de EKS es una operación real iniciada por el usuario que se introdujo en julio de 2026. Use la [guía actual de reversión](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), no la afirmación general y anticuada de que «no se puede bajar de versión». Esto cambia la versión menor de Kubernetes; **no** restaura una instantánea anterior de etcd/datos de aplicaciones/PV ni revierte automáticamente los complementos. La versión de plataforma pasa a ser la versión de plataforma más reciente de la versión menor anterior.

**Requisitos de elegibilidad y preparación**

- Inicie el procedimiento en un plazo de **7 días desde la finalización de la actualización local**. Los clústeres creados con su versión actual no cumplen los requisitos. Solo se permite la versión menor inmediatamente anterior; no se pueden encadenar reversiones a versiones menores más antiguas.
- El destino debe contar con soporte. Si el destino tiene soporte extendido, primero adopte la política de soporte `EXTENDED` y tenga en cuenta sus cargos. Las actualizaciones automáticas al final del soporte extendido no se pueden revertir; las actualizaciones automáticas durante el soporte estándar están sujetas a la condición documentada de la política extendida.
- El clúster debe estar ACTIVE y no debe tener ninguna actualización incompatible en curso. Una función de EKS activada en la nueva versión que no sea compatible con versiones anteriores puede impedir la reversión. `--force` no omite estos requisitos previos.
- Revise la información de reversión, la compatibilidad de las aplicaciones/clientes/CRD/webhooks, la diferencia de versiones de los nodos y la compatibilidad de los complementos. Las comprobaciones son puntuales y se realizan según el mejor esfuerzo; evite introducir cambios incompatibles mientras se lleva a cabo la reversión.

Las observaciones `ROLLBACK_READINESS` con ERROR/UNKNOWN bloquean la reversión; las de WARNING son informativas. Esto difiere de la aplicación, retirada temporalmente, de los requisitos normales de información de actualización. La opción `--force` de reversión omite las comprobaciones de información (ERROR/WARNING/UNKNOWN), pero no convierte un plan inseguro en uno seguro ni omite los requisitos de elegibilidad y los controles de interrupción de Auto Mode. Resuelva las observaciones cuando sea posible y trate cualquier excepción como una decisión de riesgo explícita; se omite de los ejemplos normales.

```bash
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
# Set INSIGHT_ID from the response to inspect one finding.
aws eks describe-insight --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --id "$INSIGHT_ID" --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

**Prepare los nodos y complementos antes del plano de control**

Los grupos de nodos administrados se pueden revertir con `UpdateNodegroupVersion`, tal como se documenta en la [guía actual de grupos de nodos administrados](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html). Hágalo antes de bajar la versión del plano de control y verifique las versiones resultantes de nodos/AMI. El texto de descripciones generales de API más antiguas aún indica que no se puede revertir; la guía actual de reversión describe explícitamente este flujo de reversión de versiones. No constituye una promesa general de que se pueda bajar a cualquier versión histórica de AMI. Los grupos con AMI personalizada necesitan la ruta revisada de la plantilla de lanzamiento original.

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

Los nodos autoadministrados/híbridos son responsabilidad de su propietario. Auto Mode se encarga automáticamente de sus propios nodos antes que del plano de control. Los kubelet de Fargate no se pueden revertir en el mismo Pod: coordine la disponibilidad y los controladores (incluidos HPA/GitOps/Jobs) para que los Pod de Fargate que resultarían incompatibles tras la reversión no se vuelvan a crear inmediatamente con la versión más reciente. Use un plan de mantenimiento/migración probado y, luego, vuelva a crearlos una vez revertido el plano de control. Un simple bucle para eliminar Pod no basta. Omitir con `--force` la observación sobre la diferencia de versiones de Fargate no hace que kubelet más recientes sean compatibles con el servidor de API anterior.

EKS no revierte las versiones de los complementos. Seleccione versiones puente/anteriores compatibles y una configuración revisada, usando los ID de actualización y las comprobaciones funcionales propios de cada una. Los controladores/CRD autoadministrados requieren una evaluación independiente. No use OVERWRITE indiscriminadamente ni suponga que un grupo de nodos AL2 antiguo es un plan de reversión.

**Solicite y supervise la reversión del plano de control**

Use `update-cluster-version` con la versión menor anterior aprobada; no existe un comando `rollback-cluster` separado. Esta es una alternativa a una solicitud de actualización, no un paso que se deba ejecutar automáticamente después de cada actualización. Establezca un tiempo de espera explícito y adecuado para el cliente y conserve el ID de actualización devuelto:

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

**Duración y cancelación de Auto Mode**

Durante la reversión de nodos de Auto Mode, el clúster puede permanecer **ACTIVE** y, luego, pasar a UPDATING durante la fase del plano de control. Haga un seguimiento del ID de actualización en todo momento. Los presupuestos de desviación de NodePool y las anotaciones de los nodos que impiden interrupciones pueden bloquear el reemplazo de nodos; los PDB y las anotaciones de Pod que impiden interrupciones lo retrasan, sujeto a `terminationGracePeriod`. No son garantías absolutas de disponibilidad de las aplicaciones. `--force` no omite estos controles.

En Auto Mode, `rollbackConfig.timeoutMinutes` tiene un valor predeterminado de **720** y admite valores de **120 a 10080**. Es un tiempo de espera mínimo, no un plazo exacto. Si vence, la actualización falla, el plano de control permanece en su versión actual y los nodos vuelven a desviarse hacia esa versión. El plazo original de siete días para iniciar la reversión sigue siendo importante si se vuelve a intentar. Se comprobó localmente el análisis sintáctico de la CLI 2.36.44 para la siguiente opción:

```bash
# Alternative Auto Mode request: do not run this as a second request after the preceding one.
# Select a reviewed timeout from 120 to 10080 minutes; default is 720 when omitted.
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --rollback-config timeoutMinutes=720 \
  --output json --no-cli-pager > rollback-update.json
```

Use el ID devuelto y el mismo asistente de espera después de una solicitud de Auto Mode; el tiempo de espera predeterminado de dos horas del asistente es inferior al tiempo de espera predeterminado de doce horas del servicio, así que elija el plazo del cliente con cuidado. Los tiempos de espera de CI/IaC/credenciales no cancelan la operación de AWS. CancelUpdate solo está disponible durante la fase de nodos de Auto Mode, antes de que comience la reversión del plano de control; la cancelación se realiza con el mejor esfuerzo, sin garantía de detener todas las operaciones, y las operaciones que ya estén causando interrupciones en los nodos se completan. Supervise la transición Cancelling → Cancelled y la convergencia posterior de los nodos. No se puede cancelar de esta forma una actualización normal del plano de control ni una reversión del plano de control ya iniciada.

```bash
# Only during the cancellable Auto Mode node phase, before control-plane rollback starts.
aws eks cancel-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" --output json --no-cli-pager
```

Una reversión de una pila de CloudFormation o un Git revert no inicia automáticamente una reversión de versión de EKS. Después de una recuperación explícita, concilie el estado/los planes de IaC con la versión observada. Si no se cumplen los requisitos para revertir, evalúe una corrección progresiva o un clúster nuevo en una versión admitida, con migración/restauración probadas. Ninguno de estos mecanismos deshace automáticamente las migraciones de bases de datos ni los cambios en los datos de las aplicaciones.

## Automatización de las actualizaciones {#upgrade-automation}

En entornos a gran escala, es importante automatizar el proceso de actualización. Puede automatizar las actualizaciones de EKS con las siguientes herramientas y métodos.

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagrama de la automatización de actualizaciones de EKS con tres rutas: eksctl, scripts de AWS CLI y GitOps. Cada ruta incluye los pasos ordenados para actualizar el clúster, los complementos y los grupos de nodos, además de las prácticas recomendadas de automatización aplicables a todas ellas.](../.gitbook/assets/en-eks-08-eks-upgrades-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-6.html)
-->

### Automatización mediante eksctl

Use una configuración de eksctl revisada y las opciones correctas para la operación. `upgrade cluster --approve` solicita el cambio del plano de control; sin `--approve`, el comando muestra una vista previa. La creación de grupos de nodos usa `--version`, mientras que `upgrade nodegroup` usa `--kubernetes-version`. Elija un único responsable/herramienta para cada operación y verifique el estado real de la actualización de EKS y de las cargas de trabajo. No ejecute una actualización de AWS CLI y otra de eksctl consecutivamente como solicitudes duplicadas.

### Automatización mediante AWS CLI y scripts

Los ejemplos anteriores del preanálisis de solo lectura, el sondeo de una actualización específica y las solicitudes por componente son bloques de construcción. Un orquestador debe conservar los resultados y detenerse ante fallos, tiempos de espera o validaciones incompletas. Debe usar las versiones aprobadas de complementos/AMI/configuración en vez del orden de una matriz, gestionar las diferencias de AMI personalizada y Auto/Fargate, y reanudar por ID de actualización tras un fallo del cliente. No debe afirmar que toda la actualización tuvo éxito porque un recurso esté ACTIVE. Este punto de entrada de inspección no inicia una actualización:

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

Git puede contener las versiones deseadas, la evidencia de compatibilidad y los procedimientos revisados. Argo CD/Flux no convierte de forma nativa un archivo `ClusterConfig` de eksctl en un cambio del plano de control de EKS; se necesita un controlador o ejecutor compatible con AWS que tenga la autorización adecuada. Una reversión de Git/CloudFormation no revierte automáticamente una actualización de versión de EKS.

El siguiente flujo de trabajo es, deliberadamente, una **recopilación de preparación de solo lectura**. Antes de usarlo, confirme en el repositorio el archivo completo `eks-upgrade-preflight.py` anterior en `runbooks/eks-upgrade-preflight.py`. Aprovisione por separado el ejecutor confiable en una red privada y la cadena de herramientas revisada de AWS CLI/kubectl/Python. Las acciones fijadas usan Node.js 24; el ejecutor autohospedado debe admitir ese entorno de ejecución. Configure las variables del repositorio y el entorno protegido `eks-upgrade-review`, y restrinja la confianza de OIDC a este repositorio/entorno y a `sts.amazonaws.com`. El hecho de asignar un nombre a un entorno no activa protecciones de revisión. Use un rol de inspección con solo las lecturas necesarias de EKS/STS y acceso para listar nodos de Kubernetes; el ejemplo no necesita permisos para modificar la versión del clúster.

Revise el artefacto con pruebas de aplicaciones/API/copias de seguridad/capacidad y, después, use una fase de cambio independiente y aprobada con los procedimientos por componente anteriores. Este flujo no afirma que una recopilación correcta equivalga a estar listos ni que se haya probado una actualización de producción. El acceso a los artefactos debe corresponderse con la sensibilidad de los metadatos de infraestructura/información; no se carga el kubeconfig aislado.

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

Prácticas recomendadas para automatizar las actualizaciones de EKS:

1. **Enfoque gradual**: empiece por los entornos que no son de producción y avance hacia producción
2. **Plan de recuperación**: use un procedimiento de recuperación probado que tenga en cuenta los requisitos de elegibilidad; no revierta versiones ni cambios de datos a ciegas
3. **Pasos de validación**: incluya pasos automatizados de validación después de la actualización
4. **Notificaciones**: configure notificaciones para informar del éxito o el fallo de la actualización
5. **Documentación**: documente el proceso y los pasos de automatización

## Prácticas recomendadas para las actualizaciones {#upgrade-best-practices}

Veamos las prácticas recomendadas para actualizar clústeres de EKS.

<!-- Pending parent diagram repair: see core-audit/eks-upgrades/diagram-review.json
![Diagrama en árbol de las prácticas recomendadas generales para actualizar EKS durante la planificación, preparación, ejecución y etapa posterior a la actualización, además de prácticas adicionales para clústeres grandes y para el cumplimiento normativo de servicios financieros.](../.gitbook/assets/en-eks-08-eks-upgrades-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-08-eks-upgrades-7.html)
-->

### Prácticas recomendadas generales

#### Planificación de la actualización

1. **Selección de versión**: seleccione una versión estable y revise las notas de lanzamiento
2. **Calendario de actualización**: programe la actualización durante períodos de poco tráfico
3. **Enfoque por fases**: empiece por los entornos que no son de producción y avance hacia producción
4. **Planificación de la reversión**: cree un plan de reversión para usar en caso de problemas

#### Preparación de la actualización

1. **Copia de seguridad**: haga copias de seguridad de los datos importantes
2. **Asignación de recursos**: asegure recursos suficientes para la actualización
3. **Comprobación de compatibilidad**: verifique la compatibilidad de las cargas de trabajo y los complementos
4. **Identificación de API obsoletas**: identifique y actualice las cargas de trabajo que usan API obsoletas

#### Ejecución de la actualización

1. **Preparación**: alinee las versiones actuales de los nodos y los complementos/controladores puente necesarios antes del cambio al destino
2. **Destino del plano de control**: solicite la siguiente versión menor admitida y verifique el ID de actualización
3. **Componentes dependientes**: actualice los nodos, los complementos/controladores restantes y los clientes según el orden de compatibilidad revisado
4. **Actualización gradual de nodos**: actualice los nodos gradualmente para reducir al mínimo las interrupciones de las cargas de trabajo

#### Después de la actualización

1. **Validación**: valide el estado del clúster y las cargas de trabajo
2. **Supervisión**: supervise el clúster después de la actualización
3. **Documentación**: documente el proceso y los resultados de la actualización
4. **Aprendizaje**: aprenda de los problemas que surgieron durante la actualización y de sus soluciones

### Prácticas recomendadas para clústeres grandes

Prácticas recomendadas adicionales para actualizar clústeres grandes de EKS:

1. **Implementación canary**: empiece con algunos nodos o cargas de trabajo y amplíe gradualmente
2. **Automatización**: automatice el proceso de actualización
3. **Supervisión mejorada**: supervise continuamente el estado del clúster durante la actualización
4. **Plan de comunicación**: comunique periódicamente el estado de la actualización a las partes interesadas
5. **Recuperación controlada**: automatice las comprobaciones de evidencia/elegibilidad y aplique la ruta de recuperación revisada; la reversión está sujeta a condiciones

### Prácticas recomendadas para servicios financieros

Prácticas recomendadas adicionales para actualizar clústeres de EKS en el sector de los servicios financieros:

1. **Cumplimiento normativo**: asegúrese de que la actualización cumpla los requisitos normativos
2. **Evaluación de riesgos**: evalúe los riesgos antes de la actualización
3. **Administración de cambios**: siga procesos estrictos de administración de cambios
4. **Pruebas mejoradas**: realice pruebas exhaustivas antes de la actualización
5. **Documentación detallada**: documente en detalle el proceso y los resultados de la actualización

## Conclusión

Para actualizar correctamente un clúster de Amazon EKS se necesitan planificación, preparación y validación exhaustivas. Este documento presentó estrategias, pasos y prácticas recomendadas para actualizar de forma segura los planos de control, los grupos de nodos y los complementos de clústeres de EKS.

Puntos clave:

1. **Descripción general de las actualizaciones de EKS**: administración de versiones, componentes y ruta de actualización de EKS
2. **Planificación y preparación de la actualización**: evaluación, preparación y pruebas de la actualización
3. **Actualización del plano de control de EKS**: métodos de actualización y supervisión del plano de control
4. **Actualización de grupos de nodos**: estrategias para actualizar grupos de nodos administrados y autoadministrados
5. **Actualización de complementos**: actualización de complementos administrados por AWS y autoadministrados
6. **Validación y solución de problemas de la actualización**: validación de la actualización y resolución de problemas comunes
7. **Automatización de las actualizaciones**: automatización mediante eksctl, AWS CLI y GitOps
8. **Prácticas recomendadas para las actualizaciones**: prácticas generales y específicas de cada sector

Mantener actualizado el clúster de EKS permite aprovechar los parches de seguridad, las correcciones de errores y las nuevas funciones, lo que mejora la seguridad, la estabilidad y el rendimiento generales del clúster.

## Referencias

- [Documentación de actualización de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Versiones de Kubernetes y diferencia de versiones](https://kubernetes.io/docs/setup/release/version-skew-policy/)
- [Actualización de grupos de nodos administrados de EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Actualización de complementos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/managing-add-ons.html)
- [Documentación de eksctl](https://eksctl.io/usage/cluster-upgrade/)
- [Prácticas recomendadas para actualizar Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/cluster-upgrade/)

## Cuestionario

Para poner a prueba lo que aprendió en este capítulo, pruebe el [cuestionario sobre el tema](../quizzes/eks/08-eks-upgrades-quiz.md).
