# Administración del ciclo de vida de los nodos

< [Anterior: Estrategias de ubicación de cargas de trabajo](./06-workload-placement.md) | [Tabla de contenido](./README.md) | [Siguiente: Operaciones y mantenimiento](./08-operations.md) >

> **Versiones compatibles**: nodos Hybrid de EKS con una versión de Kubernetes compatible con AWS; referencia de nodeadm 1.0.20 (la instalación y actualización con SSM requieren 1.0.19 o posterior).
> **Última actualización**: 13 de septiembre de 2026

Este documento abarca la configuración avanzada de nodeadm, la automatización de la instalación en una flota, las estrategias de actualización, el ciclo de vida de las credenciales y la supervisión del estado de los nodos Hybrid de EKS.

## 1. Configuración avanzada de NodeConfig

### Ajuste de kubelet

En entornos de producción, es necesario ajustar las reservas de recursos de kubelet, los umbrales de desalojo, la recolección de basura de imágenes y el comportamiento durante el apagado.

#### Reserva de recursos (system-reserved / kube-reserved)

Estos ajustes restan las reservas al calcular Node Allocatable. No constituyen un límite estricto universal para todos los procesos del host. La configuración predeterminada `enforceNodeAllocatable` abarca los Pods; para aplicar además las reservas de sistema y kube se requieren cgroups dedicados válidos y una jerarquía de cgroups revisada. Mida la sobrecarga del sistema operativo, kubelet, el runtime de contenedores y CNI/controladores antes de elegir valores.

```yaml
kubelet:
  config:
    systemReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "10Gi"
    kubeReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "5Gi"
```

| Parámetro | Descripción | Ejemplo inicial de planificación; mida antes de usar |
|-----------|-------------|-------------------|
| `systemReserved.cpu` | CPU para el sistema operativo y los servicios del sistema | 500m – 1000m |
| `systemReserved.memory` | Memoria para el sistema operativo y los servicios del sistema | 1Gi – 2Gi |
| `kubeReserved.cpu` | CPU para kubelet y containerd | 500m – 1000m |
| `kubeReserved.memory` | Memoria para kubelet y containerd | 1Gi – 2Gi |

#### Umbrales de desalojo

Kubelet intenta recuperar recursos a nivel del nodo y, cuando es necesario, desaloja Pods ante presión de recursos. Esto no garantiza estabilidad, y el desalojo por presión del nodo no respeta los PodDisruptionBudgets como sí lo hace una solicitud de desalojo a través de la API.

```yaml
kubelet:
  config:
    evictionHard:
      memory.available: 200Mi
      nodefs.available: 10%
      imagefs.available: 15%
      nodefs.inodesFree: 5%
      imagefs.inodesFree: 5%
    evictionSoft:
      memory.available: 500Mi
      nodefs.available: 15%
    evictionSoftGracePeriod:
      memory.available: 1m30s
      nodefs.available: 2m
    evictionMaxPodGracePeriod: 60
```

> **Nota**: los umbrales estrictos no tienen un período de observación gradual configurado y provocan la terminación inmediata. Un umbral gradual debe mantenerse durante `evictionSoftGracePeriod`; `evictionMaxPodGracePeriod` limita por separado el período de gracia de terminación de los Pods. Los umbrales graduales no impiden un desalojo estricto posterior ni una terminación por falta de memoria (OOM). Al personalizar `evictionHard`, especifique el mapa completo de umbrales previsto, incluidos los umbrales de inodos: de lo contrario, los valores predeterminados omitidos pasan a ser cero, salvo que se habilite explícitamente un comportamiento compatible de combinación con valores predeterminados.

#### Cálculo de maxPods

Dimensione `maxPods` según la CPU, la memoria, la sobrecarga de los DaemonSet y el pool por nodo de Cilium. El pool de clúster de Cilium reserva dos direcciones IPv4 por CIDR, de modo que `/25`, `/24` y `/26` proporcionan 126, 254 y 62 direcciones utilizables, respectivamente. Los siguientes valores son ejemplos de planificación, no recomendaciones validadas para una flota ni un límite derivado de ENI. No es posible cambiar sin más `clusterPoolIPv4MaskSize` para ampliar los bloques ya asignados.

```yaml
kubelet:
  config:
    maxPods: 110  # /25 has 126 usable IPv4 addresses; leave capacity for overhead
```

| Tamaño de máscara | Direcciones IPv4 totales | Ejemplo de maxPods |
|-----------|----------|-------------------|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### Recolección de basura de imágenes

Limpie automáticamente las imágenes que no se usan para administrar el espacio en disco.

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### Período de gracia de apagado

En los hosts Linux compatibles, el apagado ordenado del nodo depende de los bloqueos inhibidores de systemd y de la configuración de kubelet. No puede garantizar una terminación ordenada si se pierde la alimentación o se fuerza el apagado.

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **Nota**: en esta configuración de dos grupos, el presupuesto total de 60 segundos incluye 20 segundos para los Pods críticos y deja una ventana de 40 segundos para los demás. Esto no garantiza que cada Pod reciba siempre 40 segundos; también se aplican `terminationGracePeriodSeconds` y las condiciones reales del apagado.

### Configuración avanzada de containerd

#### Configuración de un mirror de registro privado

El siguiente fragmento usa containerd 1.x (versión 2 del formato de configuración). Para containerd 2.x, use la versión 3 y la ruta del complemento de registro `io.containerd.cri.v1.images.registry`. Compruebe la versión instalada y la configuración combinada efectiva antes de reiniciar el runtime. Verifique la confianza del registro y la compatibilidad de la ruta del mirror; no desactive la verificación TLS.

Use registros privados de confianza como mirrors. La entrada del servidor que aparece abajo conserva el endpoint de origen como alternativa; no configura un entorno aislado de Internet. Verifique la autenticación, la ruta del proyecto proxy y la confianza de la CA antes de depender del mirror.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

Configure mirrors por registro mediante archivos `hosts.toml`:

```bash
# /etc/containerd/certs.d/docker.io/hosts.toml
sudo mkdir -p /etc/containerd/certs.d/docker.io
cat <<EOF | sudo tee /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"

[host."https://harbor.internal.company.io/v2/dockerhub-proxy"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
  override_path = true
EOF
```

#### Clase de runtime de NVIDIA para nodos con GPU

Este fragmento de containerd 1.x presupone que el binario/runtime de NVIDIA y el controlador compatible ya están instalados en un nodo dedicado a GPU. Registra un controlador de runtime; no instala la pila de GPU. Cuando sea necesario, selecciónelo mediante una configuración real de RuntimeClass/carga de trabajo. Para containerd 2.x, use la versión 3 y las rutas del complemento `io.containerd.cri.v1.runtime`; no mezcle los dos formatos. Consulte el capítulo de GPU para conocer los requisitos previos del complemento de dispositivos/DRA y del toolkit seleccionado.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".containerd]

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
      privileged_without_host_devices = false
      runtime_type = "io.containerd.runc.v2"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
      BinaryName = "/usr/bin/nvidia-container-runtime"
      SystemdCgroup = true
```

### Estrategias de etiquetas y taints

#### Etiquetas automáticas de nodeadm

nodeadm asigna automáticamente la siguiente etiqueta al inicializar nodos Hybrid:

```
eks.amazonaws.com/compute-type=hybrid
```

No es necesario agregar esta etiqueta manualmente a `--node-labels`.

#### Estrategias de etiquetas personalizadas

Agregue etiquetas según el propósito o el entorno para controlar con mayor precisión la ubicación de las cargas de trabajo.

```yaml
kubelet:
  flags:
    # Purpose-based labels
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training

    # Environment-based labels (production)
    # - --node-labels=environment=production,tier=compute

    # Datacenter location labels
    # - --node-labels=datacenter=dc-seoul-01,rack=rack-a3
```

#### Estrategias de taints

| Estrategia | Descripción | Caso de uso |
|----------|-------------|----------|
| Taints automáticos (NodeConfig) | Se aplican durante el registro inicial del nodo; reconcilie explícitamente los taints de los nodos existentes | Taints comunes para todos los nodos Hybrid |
| Taints manuales (kubectl) | Se aplican dinámicamente durante las operaciones | Aislamiento de nodos GPU, modo de mantenimiento |

```yaml
# Automatic taints in NodeConfig
kubelet:
  flags:
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

```bash
# Manual taint addition during operations
kubectl taint nodes hybrid-gpu-001 gpu=true:NoSchedule
kubectl taint nodes hybrid-node-005 maintenance=true:NoSchedule
```

<a id="full-production-nodeconfig-example"></a>

### Plantilla completa para revisar NodeConfig

Esta es una plantilla de configuración no ejecutada, no una afirmación de que esté lista para producción. Los fragmentos anteriores de kubelet/containerd van bajo `spec`. El nombre del clúster y la región deben identificar el clúster previsto; nodeadm obtiene los metadatos del clúster mediante la ruta de descubrimiento autorizada. Proporcione valores de activación reales solo mediante un archivo NodeConfig privado y aprobado. Seleccione la sintaxis de containerd y todos los valores de recursos según el host real.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: prod-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 60s
      shutdownGracePeriodCriticalPods: 20s
      systemReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 10Gi
      kubeReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 5Gi
      evictionHard:
        memory.available: 200Mi
        nodefs.available: 10%
        imagefs.available: 15%
        nodefs.inodesFree: 5%
        imagefs.inodesFree: 5%
      evictionSoft:
        memory.available: 500Mi
        nodefs.available: 15%
      evictionSoftGracePeriod:
        memory.available: 1m30s
        nodefs.available: 2m
      imageGCHighThresholdPercent: 85
      imageGCLowThresholdPercent: 80
      evictionMaxPodGracePeriod: 60
    flags:
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
  containerd:
    config: "version = 2\n[plugins.\"io.containerd.grpc.v1.cri\".registry]\n  config_path\
      \ = \"/etc/containerd/certs.d\"\n"
```

---

## 2. Automatización de la instalación en la flota

### Playbook de Ansible

Use un inventario controlado y grupos pequeños para orquestar el [flujo de arranque](./04-node-bootstrap.md). Fije y verifique el artefacto de nodeadm de Hybrid Nodes para la arquitectura de cada host; no envíe un binario amd64 a todos los hosts ni vuelva a descargar un binario `latest` sin revisar durante una tanda. Para las instalaciones/actualizaciones con SSM, AWS requiere nodeadm **1.0.19 o posterior**, porque las versiones anteriores incluyen una clave de firma del instalador obsoleta. Este capítulo toma como referencia la versión 1.0.20; antes de ejecutarla, compruebe la combinación aprobada de sistema operativo, Kubernetes, CNI, CSI y runtime.

#### Configuración del inventario

Las direcciones de abajo son marcadores de posición de la documentación. Registre por separado el destino de conexión del host real, su nombre de Node en Kubernetes y su UID. En particular, el nombre de un Node respaldado por SSM no tiene por qué ser un nombre de host resoluble mediante SSH.

```ini
[hybrid_nodes:children]
gpu_nodes
cpu_nodes

[gpu_nodes]
gpu-host-a ansible_host=192.0.2.10 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[cpu_nodes]
cpu-host-a ansible_host=192.0.2.20 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[hybrid_nodes:vars]
ansible_user=REPLACE_WITH_APPROVED_OPERATOR
```

#### Playbook de automatización

Este playbook es una **comprobación previa para hosts con el software ya instalado**, no un instalador completo. Primero, proporcione un archivo NodeConfig privado, propiedad de root, mediante el proceso aprobado para archivos secretos; los códigos de activación y las claves privadas no deben almacenarse como variables ordinarias de inventario/grupo ni aparecer en la salida registrada de una plantilla. Reemplace ambos marcadores de posición de digest por artefactos verificados de forma independiente para la versión elegida. El playbook no ejecuta install/init ni inicia servicios detenidos, y no se debe interpretar como una verificación de su estado.

```yaml
- name: Review preinstalled Hybrid Nodes before an approved bootstrap
  hosts: hybrid_nodes
  gather_facts: true
  become: true
  serial: 1
  any_errors_fatal: true
  vars:
    architecture_map:
      x86_64: amd64
      aarch64: arm64
    approved_nodeadm_sha256:
      amd64: REPLACE_WITH_REVIEWED_AMD64_SHA256
      arm64: REPLACE_WITH_REVIEWED_ARM64_SHA256
    nodeconfig_path: /etc/eks/nodeconfig.yaml
  tasks:
  - name: Require a reviewed architecture and binary digest
    ansible.builtin.assert:
      that:
      - ansible_facts.architecture in architecture_map
      - approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]] is match('^[a-f0-9]{64}$')
  - name: Inspect the existing nodeadm artifact
    ansible.builtin.stat:
      path: /usr/local/bin/nodeadm
      checksum_algorithm: sha256
      get_checksum: true
    register: nodeadm_artifact
  - name: Match the approved artifact
    ansible.builtin.assert:
      that:
      - nodeadm_artifact.stat.exists
      - nodeadm_artifact.stat.executable
      - nodeadm_artifact.stat.checksum == approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]]
  - name: Validate the privately delivered NodeConfig
    ansible.builtin.command:
      argv:
      - /usr/local/bin/nodeadm
      - config
      - check
      - -c
      - file://{{ nodeconfig_path }}
    changed_when: false
    no_log: true
```

Un archivo de kubelet por sí solo no demuestra que la instalación haya terminado. Después de las comprobaciones previas, ejecute el procedimiento completo de instalación/inicialización del capítulo de arranque, con su registro de operaciones e identidad por host. Detenga la tanda si hay un fallo; conserve el estado como desconocido/parcial para recuperarlo en vez de volver a ejecutar init a ciegas. `changed_when: false` controla los informes de Ansible, no el comportamiento del comando que se ejecuta.

#### Variables basadas en roles (nodos GPU frente a nodos CPU)

| Grupo de hosts | Configuración explícita por host que se debe revisar |
| --- | --- |
| CPU | Sistema operativo/arquitectura elegidos, formato de runtime, reservas medidas, etiquetas de carga de trabajo y taints |
| GPU | Requisitos de CPU más el controlador/toolkit real, la ruta elegida del complemento de dispositivos o DRA, el controlador de runtime/RuntimeClass y la validación de GPU |

Seleccione explícitamente la plantilla de cada host; `group_names[0]` no es un selector de rol fiable. Declarar `nvidia.com/gpu.present=true` no instala un controlador ni demuestra que haya una GPU asignable. Consulte [Integración de GPU](./05-gpu-integration.md).

### Script de verificación de la flota

Guarde un `expected-nodes.json` aprobado por separado que incluya **todos los nodos Hybrid previstos** en el clúster. No derive el conjunto esperado de la misma respuesta de la API que se está probando: eso ocultaría los nodos faltantes. Un reemplazo cambia el registro de identidad y exige una conciliación deliberada.

```json
[
  {"name": "REPLACE_WITH_REGISTERED_NODE_NAME", "uid": "REPLACE_WITH_APPROVED_NODE_UID"}
]
```

Guarde lo siguiente como `check-fleet.sh`. Requiere Bash, kubectl y jq. Establezca `KUBE_CONTEXT` en una estación de trabajo del operador; el observador dentro del clúster usa su ServiceAccount. Una llamada a la API denegada/fallida, un grupo vacío, un UID incorrecto o una condición faltante devuelve un estado distinto de cero.

```bash
#!/usr/bin/env bash
# Read-only Node inventory/condition snapshot; no workload or host mutations.
set -euo pipefail
EXPECTED_FILE="${1:?Usage: check-fleet.sh expected-nodes.json}"
umask 077
WORK_DIR=$(mktemp -d)
trap 'rm -rf -- "$WORK_DIR"' EXIT
KUBECTL=(kubectl --cache-dir "$WORK_DIR/kube-cache")
if [ -n "${KUBE_CONTEXT:-}" ]; then KUBECTL+=(--context "$KUBE_CONTEXT"); fi
"${KUBECTL[@]}" get nodes -l eks.amazonaws.com/compute-type=hybrid -o json > "$WORK_DIR/nodes.json"
jq -e --slurpfile expected "$EXPECTED_FILE" '
  def required($kind; $status):
    [.status.conditions[]? | select(.type == $kind)] as $c |
    ($c | length) == 1 and $c[0].status == $status;
  $expected[0] as $want |
  ($expected | length) == 1 and ($want | type) == "array" and
  ($want | length) > 0 and
  ($want | length) == ($want | map(.name) | unique | length) and
  all($want[]; (.name | type) == "string" and (.name | length) > 0 and
               (.uid | type) == "string" and (.uid | length) > 0) and
  (.items | type) == "array" and
  (.items | map(.metadata.name) | sort) == ($want | map(.name) | sort) and
  all(.items[];
    . as $node |
    any($want[]; .name == $node.metadata.name and .uid == $node.metadata.uid) and
    .metadata.deletionTimestamp == null and
    .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
    required("Ready"; "True") and
    required("MemoryPressure"; "False") and
    required("DiskPressure"; "False") and
    required("PIDPressure"; "False"))
' "$WORK_DIR/nodes.json" > /dev/null
printf 'Expected Node identities and conditions match this snapshot.\n'
# CNI readiness, DNS, network paths, storage, applications and freshness need
# separate checks; Node Ready is not an end-to-end health guarantee.
```

Esta es una instantánea del inventario y las condiciones de los nodos. `Ready=True` no demuestra el estado actual de CNI, DNS, almacenamiento ni aplicaciones. Compruebe por separado el DaemonSet/Pods reales del CNI elegido, la conectividad entre los sitios pertinentes, la resolución DNS, las operaciones de almacenamiento y los endpoints de las cargas de trabajo; no cuente `NotReady` como Ready mediante una coincidencia parcial de texto.

## 3. Estrategias de actualización de nodos

### Política de desfase de versiones

La tabla de 1.31 que aparece abajo ilustra la aritmética de desfase entre versiones; no recomienda desplegar hoy esos nodos históricos. Seleccione un destino compatible con EKS y un sistema operativo, CNI, CSI y runtime compatibles según la documentación actual de AWS.

Kubernetes mantiene una política estricta de compatibilidad de versiones entre kubelet y el servidor de la API.

| Versión de kubelet | Versión del servidor de la API | Compatible |
|----------------|-------------------|------------|
| 1.31 | 1.31 | Sí (misma versión) |
| 1.30 | 1.31 | Sí (n-1) |
| 1.29 | 1.31 | Sí (n-2) |
| 1.28 | 1.31 | Sí (n-3) |
| 1.27 | 1.31 | No (n-4, no compatible) |
| 1.32 | 1.31 | No (kubelet más reciente que el servidor de la API, no compatible) |

> **Orden de actualización**: primero actualice los nodos rezagados a la versión minor actual del plano de control. Antes de pasar los nodos a la siguiente versión minor, actualice el plano de control. kubelet no debe tener una versión más reciente que el servidor de la API; el desfase compatible no recomienda mantener nodos antiguos indefinidamente.

### Lista de comprobación previa a la actualización

Antes de cada tanda, apruebe la versión major.minor de destino, las versiones completas y sumas de comprobación de los artefactos, compruebe el desfase con el plano de control y la compatibilidad del sistema operativo/CNI/CSI/runtime, y confirme que haya capacidad de reserva suficiente para las cargas de trabajo desalojadas. Inspeccione las solicitudes/ubicación de los Pods, las interrupciones permitidas por PDB, los PV locales/propiedad de `emptyDir`, las copias de seguridad/la recuperación y la observabilidad. `kubectl top` es una medición de uso opcional, no una prueba de que todos los Pods puedan reprogramarse.

Inventaríe el nombre/UID del Node, la conexión real con el host, el proveedor de credenciales y el estado original de `.spec.unschedulable`. `nodeadm upgrade` conserva el nombre del Node y no puede cambiar el proveedor de credenciales. Normalmente selecciona los artefactos más recientes de la versión minor solicitada; fijar solo una versión minor no constituye un plan de artefactos inmutable. Cuando se requiera reproducibilidad, use el manifiesto aprobado y el procedimiento para artefactos privados.

### Actualización gradual

Procese **un solo nodo seleccionado explícitamente a la vez** y deténgase ante el primer fallo. Los ejemplos siguientes son un flujo operativo no ejecutado, no un controlador de flota con una garantía de disponibilidad probada. Ejecute los primeros y últimos bloques desde la estación de trabajo aprobada con permisos de administrador del clúster, en el mismo shell o restaurando el directorio/los datos registrados. El operador necesita permisos para observar Nodes, Leases, Pods/PDB y para acordonar/desagendar.

Guarde la ruta del registro privado; estos comandos acordonan y desagendan el Node seleccionado. Un PDB que impida la operación o un `emptyDir` local requieren una decisión explícita sobre la carga de trabajo/los datos. No agregue `force`, desactive la protección contra desalojo ni use delete-emptydir-data solo para que se complete un desagendamiento fallido.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the actual Kubernetes Node name}"
: "${EXPECTED_UID:?Set the approved Node UID}"
UPGRADE_RECORD_DIR=$(mktemp -d "$PWD/hybrid-upgrade.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/node-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null
' "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/lease-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | type) == "string"
' "$UPGRADE_RECORD_DIR/lease-before.private.json" > /dev/null
printf 'Private upgrade record: %s\n' "$UPGRADE_RECORD_DIR"
kubectl --context "$KUBE_CONTEXT" cordon "$NODE"
kubectl --context "$KUBE_CONTEXT" drain "$NODE" --ignore-daemonsets --timeout=10m
```

Solo después de que termine correctamente el desagendamiento, conéctese al **host físico/virtual asignado**, verifique la identidad registrada y el binario nodeadm revisado, y ejecute allí la actualización disruptiva. NodeConfig debe conservar el proveedor de credenciales existente. No omita como procedimiento rutinario la validación del nodo/los Pods/la inicialización.

```bash
set -euo pipefail
: "${TARGET_MINOR:?Set the approved EKS-supported major.minor target}"
sudo /usr/local/bin/nodeadm upgrade "$TARGET_MINOR" \
  -c file:///etc/eks/nodeconfig.yaml --timeout 20m
```

Un error del comando de actualización o la pérdida de la sesión significa que la operación es desconocida/fallida, aunque Kubernetes siga mostrando una condición Ready antigua. Mantenga el Node acordonado e investigue. Tras confirmar que la operación en el host terminó correctamente, obsérvelo desde la estación de trabajo; use la versión completa esperada de kubelet del plan de artefactos, incluido cualquier sufijo de compilación.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the recorded Node name}"
: "${EXPECTED_UID:?Set the recorded Node UID}"
: "${EXPECTED_KUBELET_VERSION:?Set the full version from the approved artifact plan}"
: "${UPGRADE_RECORD_DIR:?Use the private record directory from the pre-upgrade step}"
jq -e --arg uid "$EXPECTED_UID" --arg node "$NODE" \
  '.metadata.uid == $uid and .metadata.name == $node' \
  "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
POSTCHECK_DIR=$(mktemp -d "$UPGRADE_RECORD_DIR/check.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$POSTCHECK_DIR/node-after.private.json"
jq -e --arg uid "$EXPECTED_UID" --arg version "$EXPECTED_KUBELET_VERSION" '
  [.status.conditions[]? | select(.type == "Ready")] as $ready |
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null and
  .status.nodeInfo.kubeletVersion == $version and
  ($ready | length) == 1 and $ready[0].status == "True"
' "$POSTCHECK_DIR/node-after.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$POSTCHECK_DIR/lease-after.private.json"
jq -e --arg uid "$EXPECTED_UID" \
  --slurpfile before "$UPGRADE_RECORD_DIR/lease-before.private.json" '
  def epoch: sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601;
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | epoch) > ($before[0].spec.renewTime | epoch)
' "$POSTCHECK_DIR/lease-after.private.json" > /dev/null
printf 'Node identity, target kubelet version, Ready and a newer Lease observed.\n'
# Workload/CNI/DNS/storage checks and the prior scheduling intent remain separate.
# This check never uncordons the node.
```

Esto requiere que un Lease se renueve después de la instantánea guardada, además de que coincidan la versión de destino y la identidad del Node. Aun así, no es una prueba de aceptación de la aplicación. Verifique el CNI, DNS, los volúmenes, el controlador/runtime y la recuperación de las cargas de trabajo. Solo entonces quite explícitamente el cordón de un Node que podía programarse antes del mantenimiento. No quite el cordón automáticamente mediante una trampa EXIT ni restablezca la programación de un Node que ya estaba acordonado intencionalmente. Conserve las pruebas y repita el proceso con el siguiente Node aprobado.

### Actualización canary

Elija un canary representativo según el sistema operativo/la arquitectura, el runtime, el proveedor de credenciales y la carga de trabajo; no seleccione el primer nombre que devuelva la API. Aplique el mismo flujo de un nodo y, durante el período acordado para el servicio, observe los errores/la latencia de la aplicación, el estado del almacenamiento/la red y las versiones reales. Una espera fija o que el Node figure como Ready no bastan para aprobarlo. Amplíe a otras tandas pequeñas solo después de estas comprobaciones; durante la transición, conserve los hosts antiguos hasta que se complete la aceptación.

<a id="rollback-procedure"></a>

### Límites de recuperación y reversión

AWS recomienda reemplazar los hosts y realizar una transición controlada cuando haya capacidad de reserva. Mantenga disponibles los hosts antiguos hasta que se aprueben las comprobaciones de la aplicación, el almacenamiento, la red y la versión de destino. `nodeadm upgrade` en el mismo host es disruptivo y no constituye un mecanismo general de degradación transaccional.

Si se produce un fallo, mantenga acordonado el nodo afectado, detenga la tanda restante, conserve los diagnósticos e inspeccione los artefactos/credenciales instalados. Recupérelo con una imagen/versión aprobada y compatible con el plano de control actual. No quite el cordón automáticamente solo porque siga visible una condición antigua `Ready=True`; verifique la identidad prevista del nodo y la versión real de kubelet, además de que las cargas de trabajo estén listas.

No elimine recursivamente `/var/lib/kubelet` ni `/etc/kubernetes` como paso genérico de reversión. Los montajes de volúmenes y subrutas de Pods pueden exponer datos montados del host o de la aplicación. Desde nodeadm 1.0.9, incluso la desinstalación forzada conserva deliberadamente `/var/lib/kubelet`; toda limpieza excepcional requiere revisar explícitamente los montajes y la retención de datos. La desinstalación no desagenda ni elimina el objeto Node de Kubernetes, ni quita por completo el CNI. En el caso de SSM, también cancela el registro de la instancia administrada. Por lo tanto, la reconstrucción requiere el proceso completo de instalación/arranque y conciliación de identidades, no un ciclo ciego de desinstalación y reinstalación.

---

## 4. Ciclo de vida de las credenciales

<a id="ssm-hybrid-activation-renewal"></a>

### Vencimiento de la activación Hybrid de SSM

El vencimiento de una activación limita los **registros nuevos**. Los nodos que ya se registraron siguen siendo nodos administrados por Systems Manager hasta que se los dé de baja explícitamente. No desinstale ni vuelva a registrar nodos en buen estado solo porque haya vencido su activación original. El registro, las credenciales rotativas del agente, los permisos de IAM y la conectividad tienen ciclos de vida independientes.

Cree una activación nueva solo cuando haya que registrar hosts adicionales o una recuperación aprobada exija volver a registrarlos. Use el rol IAM real de Hybrid Nodes configurado para SSM; no lo sustituya por un rol genérico de Run Command. Revise la relación de confianza/los permisos del rol, la cuenta, la región y el número exacto de nodos nuevos antes de ejecutar este comando que crea un recurso de AWS. El código de activación es un secreto similar a una contraseña, así que guarde la respuesta en un archivo privado y entréguelo mediante el proceso aprobado de archivo secreto para NodeConfig.

```bash
set -euo pipefail
umask 077
: "${HYBRID_NODE_ROLE_NAME:?Set the reviewed Hybrid Nodes IAM role name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${NEW_NODE_COUNT:?Set the approved registration count}"
set -C  # Refuse to overwrite an existing private response file.
aws ssm create-activation   --iam-role "$HYBRID_NODE_ROLE_NAME"   --registration-limit "$NEW_NODE_COUNT"   --region "$AWS_REGION"   --output json > activation.private.json
```

Si falla AWS CLI, el archivo de respuesta queda sin confianza o posiblemente parcial; deténgase e inspecciónelo de forma privada antes de reintentar. No muestre el código de activación ni confirme este archivo en el repositorio. Establezca un vencimiento explícito aprobado cuando la ventana de registro predeterminada de la API no sea adecuada; el máximo es de 30 días. El recuento limita los registros, pero no determina qué hosts están autorizados a usar una activación filtrada.

`nodeadm uninstall` da de baja un host respaldado por SSM y elimina los componentes instalados. Ejecutar después solo `init` no reemplaza `install`. Para una recuperación intencional, primero revise el desagendamiento/la retención de datos y los cambios de identidad; después, use el [flujo de arranque](./04-node-bootstrap.md) completo. Hay que conciliar con el inventario los nombres/UID de los nodos existentes y los ID de las instancias administradas por SSM; no reutilice en silencio un registro anterior de una operación satisfactoria.

### Renovación de certificados de IAM Roles Anywhere

Renueve el **certificado de autenticación del host** del nodo mediante su PKI actual antes de que venza. Es independiente de los certificados de cliente/servidor de kubelet y de la CA del plano de control de EKS. El asunto del certificado, `nodeName` configurado, las condiciones de la sesión del rol, el perfil, el rol y el ancla de confianza deben seguir siendo compatibles; cambiar el CN no es una rotación de archivo inocua.

#### Supervisión del vencimiento del certificado

Ejecute esta comprobación contra el `certificatePath` configurado, no contra una ruta supuesta. Si el certificado no existe, no se puede leer, es inválido o vence en 30 días o menos, la comprobación falla. El aviso de 30 días es un umbral operativo de ejemplo.

```bash
#!/usr/bin/env bash
set -euo pipefail
CERT_PATH="${1:?Usage: check-cert-expiry.sh certificate.pem}"
test -r "$CERT_PATH" || { echo 'Certificate missing or unreadable' >&2; exit 1; }
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
# This is an expiration check only, not chain/key/CN/trust/IAM validation.
```

<a id="automatic-renewal-script"></a>

#### Flujo de renovación del certificado

Use el cliente de CA y la política de inscripción autenticada aprobados por la organización; no existe un endpoint genérico `/sign` sin autenticación. Proteja la clave existente si la reutiliza o siga el proceso aprobado de rotación de claves. Envíe una CSR con la identidad prevista y guarde el certificado emitido como candidato separado del certificado activo.

Las siguientes **comprobaciones locales solamente** verifican el tiempo de validez restante, la cadena frente a raíces aprobadas por separado y la correspondencia de la clave pública. Proporcione los certificados intermedios mediante `INTERMEDIATE_CHAIN` cuando sea necesario. No comprueban todas las políticas de PKI/IAM, la revocación, `nodeName`/CN ni las condiciones de autenticación en vivo.

```bash
set -euo pipefail
umask 077
: "${CANDIDATE_CERT:?Path to the issued candidate leaf certificate}"
: "${PRIVATE_KEY:?Path to its existing protected private key}"
: "${APPROVED_CA_PEM:?Path to the separately approved trust roots}"
CERT_CHECK_DIR=$(mktemp -d)
trap 'rm -rf -- "$CERT_CHECK_DIR"' EXIT
openssl x509 -in "$CANDIDATE_CERT" -checkend 2592000 -noout
VERIFY=(openssl verify -CAfile "$APPROVED_CA_PEM")
if [ -n "${INTERMEDIATE_CHAIN:-}" ]; then VERIFY+=(-untrusted "$INTERMEDIATE_CHAIN"); fi
"${VERIFY[@]}" "$CANDIDATE_CERT"
openssl x509 -in "$CANDIDATE_CERT" -pubkey -noout > "$CERT_CHECK_DIR/cert.pub"
openssl pkey -in "$PRIVATE_KEY" -pubout > "$CERT_CHECK_DIR/key.pub"
cmp "$CERT_CHECK_DIR/cert.pub" "$CERT_CHECK_DIR/key.pub"
```

Antes de aprobar el certificado, revise el asunto/SAN, los usos, la política de la CA, la revocación y las condiciones exactas de `nodeName`/rol. Haga una copia privada del certificado actual; luego, solicite al administrador de certificados aprobado que reemplace atómicamente el certificado validado en el mismo sistema de archivos y conserve el propietario y el modo. Si rota tanto la clave como el certificado, coordine el par para que ningún consumidor pueda leer archivos que no coincidan.

Inspeccione el modo real del asistente de credenciales configurado por nodeadm (proceso de credenciales o actualizador de archivos de credenciales) y valide la próxima actualización de credenciales mediante la ruta de diagnóstico privado aprobada. Reiniciar kubelet no renueva el certificado X.509 ni demuestra que el asistente lo haya aceptado. Programe la renovación automática solo después de probar para ese entorno el emisor, el rechazo de candidatos, el reemplazo atómico, la actualización y el comportamiento de reversión; para este capítulo no se ejecutó ninguna renovación en producción de este tipo.

#### Actualización del ancla de confianza

Por lo general, un certificado final renovado bajo la misma CA de confianza no exige reemplazar el ancla de confianza. Una rotación de CA afecta a todos los hosts/perfiles/roles dependientes. Planifique la superposición/migración con los responsables de PKI e IAM, inspeccione el tipo de origen y los nodos dependientes, y conserve una ruta de recuperación antes de cambiar la confianza.

Para un origen **CERTIFICATE_BUNDLE**, use una entrada JSON desde archivo para conservar intactos los saltos de línea PEM. En este caso, la unión `sourceData` solo contiene `x509CertificateData`. Un ancla `AWS_ACM_PCA` usa `acmPcaArn` y requiere otra revisión. Este ejemplo crea un archivo de solicitud privado y después actualiza AWS; no lo ejecute como parte de la supervisión ordinaria del vencimiento de certificados.

```bash
set -euo pipefail
umask 077
: "${APPROVED_CA_PEM:?Path to the reviewed CA certificate bundle}"
: "${TRUST_ANCHOR_ID:?Set the reviewed existing trust anchor ID}"
: "${AWS_REGION:?Set the trust anchor Region}"
set -C
jq -n --rawfile bundle "$APPROVED_CA_PEM" \
  '{sourceType:"CERTIFICATE_BUNDLE", sourceData:{x509CertificateData:$bundle}}' \
  > trust-anchor-source.private.json
# AWS mutation: run only after the CA rollover and dependent-node review.
aws rolesanywhere update-trust-anchor --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --region "$AWS_REGION" --source file://trust-anchor-source.private.json \
  --output json > trust-anchor-update.private.json
```

Vuelva a leer y verificar el ancla prevista, y pruebe la emisión de credenciales nuevas con un canary antes de terminar la rotación. Un error de la API indica que la operación es desconocida/fallida; no demuestra que la confianza anterior siga activa. Nunca registre las credenciales emitidas ni suponga que reemplazar un ancla conserva automáticamente el acceso de todos los certificados anteriores.

## 5. Automatización de la supervisión de estado

### CronJob para la comprobación automática de estado

Este observador ejecuta la comprobación de instantáneas de Nodes de la sección 2. **No** ejecuta nodeadm en los hosts ni valida sus credenciales de AWS. Use una imagen revisada que contenga Bash, kubectl y jq, sea compatible con el clúster y pueda ejecutarse con UID 10001. Antes del despliegue, reemplace la imagen de marcador de posición; aquí no se validó ninguna imagen ni ejecución en un clúster. El espacio de nombres de supervisión debe existir previamente.

Cree el manifiesto ConfigMap a partir del archivo guardado `check-fleet.sh` y del `expected-nodes.json` aprobado. Después, revíselo y aplíquelo junto con el ServiceAccount/RBAC/CronJob de abajo. ClusterRole puede listar todos los Nodes; el selector de etiquetas filtra la consulta, pero no delimita la autorización. Revise quiénes son los responsables del espacio de nombres que pueden modificar el ConfigMap o ejecutar Pods con este ServiceAccount.

```bash
: "${KUBE_CONTEXT:?Set the approved cluster context}"
kubectl --context "$KUBE_CONTEXT" -n monitoring create configmap hybrid-node-check \
  --from-file=check-fleet.sh --from-file=expected-nodes.json \
  --dry-run=client -o yaml > hybrid-node-check.yaml
# Review this manifest and the observer/RBAC manifest before applying either.
```
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: hybrid-node-observer
rules:
- apiGroups:
  - ''
  resources:
  - nodes
  verbs:
  - get
  - list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: hybrid-node-observer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: hybrid-node-observer
subjects:
- kind: ServiceAccount
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hybrid-node-observer
  namespace: monitoring
spec:
  schedule: '*/30 * * * *'
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 120
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      ttlSecondsAfterFinished: 1800
      template:
        spec:
          serviceAccountName: hybrid-node-observer
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            fsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: observer
            image: example.invalid/hybrid-observer:replace-with-reviewed-build
            command:
            - /bin/bash
            - /config/check-fleet.sh
            - /config/expected-nodes.json
            env:
            - name: TMPDIR
              value: /work
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            volumeMounts:
            - name: config
              mountPath: /config
              readOnly: true
            - name: work
              mountPath: /work
          volumes:
          - name: config
            configMap:
              name: hybrid-node-check
              defaultMode: 292
          - name: work
            emptyDir:
              sizeLimit: 64Mi
```

Genere una alerta tanto si falla un Job **como si se omiten ejecuciones o no hay éxitos recientes**. Un intervalo de sondeo de 30 minutos no permite detectar fallos de inmediato. Envíe notificaciones mediante la integración protegida del sistema de supervisión; no incluya URLs portadoras de tokens de webhooks de Slack en el entorno del Pod ni considere que una notificación fallida equivale a una comprobación de estado satisfactoria.

### Supervisión del estado de kubelet/containerd (nivel de nodo)

El siguiente script, propiedad de root, observa el estado local de los servicios y el sistema de archivos raíz sin reiniciar servicios. Los sistemas de archivos montados aparte para kubelet/containerd/imágenes requieren comprobaciones adicionales; el porcentaje de uso del disco raíz por sí solo no basta. No se debe informar como saludable si un comando no está disponible o una medición está mal formada.

```bash
#!/usr/bin/env bash
# Observe local services/filesystem; do not restart anything automatically.
set -euo pipefail
failed=0
for service in kubelet containerd; do
  if ! systemctl is-active --quiet "$service"; then
    printf '%s is not active\n' "$service" >&2
    failed=1
  fi
done
usage=$(df --output=pcent / | tail -n 1 | tr -d ' %')
case "$usage" in ''|*[!0-9]*) echo 'Unknown filesystem usage' >&2; exit 1;; esac
if [ "$usage" -ge 90 ]; then
  printf 'Root filesystem usage: %s%%\n' "$usage" >&2
  failed=1
fi
exit "$failed"
```

Instale el script mediante el proceso revisado de administración de hosts como `/usr/local/bin/node-health-check.sh`; debe ser ejecutable y no modificable por usuarios que no sean de confianza. El timer/unit son ejemplos de configuración; la supervisión del journal y de las unidades fallidas se debe conectar por separado. `PrivateTmp` no hace que sea seguro registrar credenciales.

```ini
[Unit]
Description=Periodic Hybrid Node local observation

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```
```ini
[Unit]
Description=Observe Hybrid Node local services and root filesystem

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/node-health-check.sh
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
```

Ante un problema específico de red/credenciales, un operador puede ejecutar por separado `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` con privilegios de root. Se comunica con AWS y el clúster y puede exponer contexto de diagnóstico; conserve la salida en privado. No lo ejecute silenciosamente con cada activación del timer, descarte sus errores ni reinicie kubelet/containerd automáticamente sin una decisión específica para el incidente.

## Verificación y fuentes

La validación local abarca el análisis de los ejemplos, casos simulados de fallo de Node/API y comprobaciones sintéticas de certificados. No demuestra que se haya completado la instalación de la flota, la actualización de hosts, la rotación de credenciales, la admisión de Kubernetes, las pruebas de CNI/DNS/almacenamiento ni un SLO de producción.

- [nodeadm de Hybrid Nodes de AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Actualizaciones de Hybrid Nodes de AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [Registro y duración de activación de SSM](https://docs.aws.amazon.com/systems-manager/latest/userguide/hybrid-activation-managed-nodes.html)
- [Configuración de credenciales de IAM Roles Anywhere](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Entrada de UpdateTrustAnchor](https://docs.aws.amazon.com/botocore/latest/reference/services/rolesanywhere/client/update_trust_anchor.html)
- [Desfase de versiones de Kubernetes](https://kubernetes.io/releases/version-skew-policy/)
- [Desalojo por presión del nodo](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Allocatable](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Apagado ordenado del nodo](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/)
- [Configuración de containerd](https://github.com/containerd/containerd/blob/main/docs/cri/config.md)
- [Asignador de pool de clúster de Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool.rst)

---

< [Anterior: Estrategias de ubicación de cargas de trabajo](./06-workload-placement.md) | [Tabla de contenido](./README.md) | [Siguiente: Operaciones y mantenimiento](./08-operations.md) >
