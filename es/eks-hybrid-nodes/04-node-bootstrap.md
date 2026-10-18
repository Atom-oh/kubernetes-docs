# Inicio de nodos

< [Anterior: Configuración con acceso restringido a Internet](./03-airgap-setup.md) | [Tabla de contenido](./README.md) | [Siguiente: Integración de GPU](./05-gpu-integration.md) >

> **Versiones compatibles**: EKS Hybrid Nodes; se revisó el código fuente de nodeadm v1.0.20. Seleccione un conjunto compatible de SO, Kubernetes y CNI para el clúster de destino.
> **Última actualización**: 12 de septiembre de 2026

Este capítulo conecta un host local preparado con EKS. Separa la instalación de software, la identidad de AWS, la inicialización y la preparación verificada para ejecutar cargas de trabajo. Los ejemplos requieren un clúster y un host identificados, así como la aprobación del operador para los cambios descritos. La validación local no demuestra que se hayan probado una red de producción, una imagen de SO, una PKI o una carga de trabajo.

## Flujo de inicio

1. Prepare el SO/runtime compatible, una identidad de host única, la sincronización horaria, las rutas, el DNS y las reglas del firewall según [Requisitos previos](./01-prerequisites.md) y [Configuración de red](./02-network-configuration.md).
2. Prepare un **rol de IAM para Hybrid Nodes**, el proveedor SSM o IAM Roles Anywhere y una entrada de acceso al clúster de tipo `HYBRID_LINUX`. Un rol genérico de administración de SSM no es suficiente.
3. Verifique la versión de nodeadm para Hybrid y, después, instale las dependencias en el host o en una compilación controlada de la imagen del SO.
4. Entregue una NodeConfig protegida y específica para cada nodo, con exactamente un proveedor de credenciales. Configure el proxy y la confianza del registro si es necesario.
5. Ejecute `nodeadm config check` y, después, `nodeadm init` en el host identificado.
6. Configure el CNI compatible con Hybrid y los complementos necesarios. Un nodo registrado todavía puede estar en estado `NotReady`.
7. Verifique la identidad exacta del nodo, la condición Ready, el CNI/DNS, la actualización de credenciales y una prueba acotada de carga de trabajo antes de aceptarlo para el servicio.

## Instalación de nodeadm y dependencias

nodeadm para Hybrid procede de **`aws/eks-hybrid`**, no del instalador EC2 `amazon-eks-ami`. Las instalaciones o actualizaciones nuevas de SSM requieren **nodeadm 1.0.19 o posterior**, porque las versiones anteriores contienen una clave de firma de SSM obsoleta. Esta revisión utilizó el código fuente publicado de la versión **v1.0.20**.

Descargue la versión aprobada con la verificación HTTPS habilitada y compare su digest con un registro aprobado de forma independiente antes de ejecutarla como root. No sustituya a ciegas `/usr/local/bin/nodeadm` por una descarga mutable de `latest`. El capítulo de [configuración con acceso restringido a Internet](./03-airgap-setup.md) cubre la preparación de imágenes y las opciones de manifiesto privado de la versión revisada. En esta auditoría no se obtuvo ni ejecutó un binario de nodeadm porque el host oficial de artefactos no superó la verificación del nombre de host TLS en este entorno.

```bash
# Target host/image builder: installs software. Choose exactly one provider.
set -euo pipefail
: "${KUBERNETES_VERSION:?Approved cluster-compatible version}"
: "${CREDENTIAL_PROVIDER:?ssm or iam-ra}" "${REGION:?}"
: "${CONTAINERD_SOURCE:?distro, docker or none for this OS}"
case "$CREDENTIAL_PROVIDER" in ssm|iam-ra) ;; *) exit 1 ;; esac
case "$CONTAINERD_SOURCE" in distro|docker|none) ;; *) exit 1 ;; esac
sudo nodeadm install "$KUBERNETES_VERSION" \
  --credential-provider "$CREDENTIAL_PROVIDER" \
  --containerd-source "$CONTAINERD_SOURCE" --region "$REGION" --timeout 20m
```

Para un nodo nuevo, prefiera la versión menor actual del plano de control. La compatibilidad de versiones de kubelet permite cierta diferencia, pero no justifica instalar una versión antigua de EKS que ya no tenga soporte. kubelet no puede ser más reciente que el servidor de API; compruebe también la compatibilidad de EKS y del CNI, además de la política de diferencias de versión de Kubernetes.

`distro` no es compatible con RHEL; use el origen de paquetes de Docker documentado o un runtime compatible preinstalado junto con `none`. `docker` no es compatible con AL2023. `none` omite la instalación de containerd. El modo privado también omite los paquetes del SO: no proporciona las dependencias de runtime que falten.

| Componente | Ubicación instalada documentada |
|---|---|
| kubelet | `/usr/bin/kubelet` |
| kubectl | `/usr/local/bin/kubectl` |
| Proveedor de credenciales de ECR | `/etc/eks/image-credential-provider/ecr-credential-provider` |
| Autenticador de AWS IAM / helper de firma | `/usr/local/bin/aws-iam-authenticator` / `/usr/local/bin/aws_signing_helper` |
| CLI de configuración de SSM | `/opt/ssm/ssm-setup-cli` |
| Agente SSM | Ubuntu snap: `/snap/amazon-ssm-agent/current/amazon-ssm-agent`; AL2023/RHEL: `/usr/bin/amazon-ssm-agent` |
| containerd | Ubuntu/AL2023: `/usr/bin/containerd`; la documentación de RHEL usa `/bin/containerd` |
| Rastreador de nodeadm | `/opt/nodeadm/tracker` |

`nodeadm install` instala y configura el agente SSM mediante su CLI de configuración firmada; **el registro de SSM se realiza durante `init`**. No es una secuencia escrita a mano de `dpkg` seguida de un instalador de nodeadm incompatible.

## NodeConfig y credenciales

### SSM

Proporcione el nombre y la Región del clúster, además de un código/ID de activación válido para el rol Hybrid preparado:

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: REPLACE_WITH_ACTIVATION_CODE
      activationId: REPLACE_WITH_ACTIVATION_ID
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=workload.example.com/location=onprem
```

La configuración protegida es una plantilla de entrada, no un secreto que deba confirmarse en el repositorio. Use propietario root y modo `0600`; entregue los valores sin publicarlos en registros ni en el historial del shell. El descubrimiento del clúster obtiene el endpoint de API y la CA mediante los permisos de EKS del rol Hybrid. Un bloque PEM sin procesar en un campo de CA codificado en base64 no es intercambiable con la representación de la API.

Los periodos `maxPods` y de apagado son ejemplos de planificación, no garantías de capacidad. Compruebe la asignación del CNI, las IP reservadas, los recursos y los requisitos de terminación de las cargas de trabajo. Las taints opcionales `NoSchedule` requieren tolerations correspondientes en las cargas de trabajo/el CNI; no añada una taint predeterminada que impida silenciosamente programar agentes o aplicaciones necesarios.

Cree activaciones solo a través del responsable de credenciales, usando el rol Hybrid preparado, la Región correcta, un vencimiento explícito y un límite acotado de registros. Guarde la respuesta en un archivo privado en vez de imprimir el código de activación:

```bash
# AWS write: owner-approved activation for one new host.
set -euo pipefail
umask 077
: "${REGION:?}" "${HYBRID_ROLE_NAME:?Prepared Hybrid Nodes IAM role name}"
: "${ACTIVATION_EXPIRY:?Future UTC timestamp within SSM service limits}"
test ! -e activation.json
aws ssm create-activation --region "$REGION" \
  --iam-role "$HYBRID_ROLE_NAME" --registration-limit 1 \
  --expiration-date "$ACTIVATION_EXPIRY" \
  --default-instance-name eks-hybrid-node > activation.json
```

Una solicitud fallida o de resultado desconocido no justifica volver a crearla a ciegas; resuélvala con el responsable de credenciales. SSM usa como nombre del nodo el ID de instancia administrada resultante `mi-*`. Los reinicios normales reutilizan el registro de SSM y las credenciales temporales renovadas. Para volver a registrar el nodo se necesita una activación todavía válida y con capacidad de registro restante; su vencimiento importa tanto como el límite.

### IAM Roles Anywhere

Use el ancla de confianza, el perfil habilitado, el rol Hybrid y el certificado/clave específicos del nodo preparados en [Requisitos previos](./01-prerequisites.md). No cree otra ancla de confianza/perfil cada vez que ejecute este capítulo.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_ID
      roleArn: arn:aws:iam::111122223333:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

Las rutas son ejemplos, no una instrucción para reutilizar un certificado en varios equipos. Vincule `nodeName` al atributo del certificado que utiliza la política de confianza del rol; la condición habitual sobre CN requiere que coincidan. El nombre debe cumplir las reglas de nomenclatura de nodos y tener como máximo 64 caracteres. Habilite **`acceptRoleSessionName: true`** en el perfil.

La duración de la sesión no aumenta por el mero hecho de establecer en 12 horas el máximo del rol. La duración efectiva solicitada/en el perfil debe estar dentro de `MaxSessionDuration` del rol; se permite que sea igual. Elija la duración según los requisitos de seguridad y disponibilidad, y compruebe la renovación de credenciales. Las claves de acceso estáticas de un usuario de IAM no son un tercer proveedor de credenciales compatible con nodeadm para Hybrid.

## Confianza en registros privados

Para un registro interno, verifique la huella de la CA y el nombre de host del certificado con el responsable del registro. Cuando corresponda, prefiera la confianza limitada al registro. No instale globalmente un certificado presentado sin verificar ni deshabilite la verificación del nombre de host.

Ejemplo de `hosts.toml` para el registro aprobado:

```toml
# /etc/containerd/certs.d/registry.internal.example.com/hosts.toml
server = "https://registry.internal.example.com"

[host."https://registry.internal.example.com"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/registry.internal.example.com/ca.crt"
```

El archivo de CA correspondiente y verificado debe estar presente en cada nodo. En containerd 1.x, `config_path` del registro va en `plugins."io.containerd.grpc.v1.cri".registry`; en containerd 2.x/configuración versión 3, va en `plugins."io.containerd.cri.v1.images".registry`. Revise el `/etc/containerd/config.toml` generado por nodeadm y use la sección correspondiente al runtime instalado. No combine `configs/auth` de registro en línea obsoleto con una receta `config_path` ni incluya contraseñas del registro en NodeConfig.

Si la organización necesita confianza de CA para todo el sistema, Ubuntu usa `/usr/local/share/ca-certificates/` junto con `update-ca-certificates`; RHEL/AL2023 usan `/etc/pki/ca-trust/source/anchors/` junto con `update-ca-trust extract`. No indique la ruta de Ubuntu en un ejemplo de RHEL. Los certificados ECR normales usan confianza pública; el SO sigue necesitando un paquete de CA funcional. La confianza en el registro y la autenticación del registro son aspectos distintos.

## Inicialización y verificación

```bash
# Identified target host; init changes local configuration and joins EKS.
set -euo pipefail
sudo nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml
sudo nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
```

En una instalación con manifiesto privado, pase `--manifest-override` y `--private-mode` aprobados a `init`, como se describe en [Configuración con acceso restringido a Internet](./03-airgap-setup.md). Los ajustes del proxy deben llegar a los procesos reales de nodeadm/daemon. `config check` valida la configuración local; no es una prueba integral de unión al clúster.

Desde la estación de trabajo del **administrador del clúster**, compruebe el contexto kubeconfig previsto y el nombre de nodo exacto esperado (SSM `mi-*` o el nombre aprobado para IAM Roles Anywhere):

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${EXPECTED_NODE_NAME:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o json > node-registration.json
jq -e '.metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid"
  and (.metadata.uid | type == "string" and length > 0)' node-registration.json
expected_uid=$(jq -er '.metadata.uid' node-registration.json)
# After CNI and required add-ons are ready:
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" wait \
  --for=condition=Ready "node/$EXPECTED_NODE_NAME" --timeout=5m
observed_uid=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o jsonpath='{.metadata.uid}')
test "$observed_uid" = "$expected_uid"
```

Registre el UID del nodo y compare el proveedor/las direcciones con el host físico o virtual identificado. La condición Ready es necesaria, pero también hay que verificar DNS, extracción de imágenes, conectividad, renovación de credenciales y la carga de trabajo necesaria. La salida anterior con `v1.31.0` era un ejemplo histórico ilustrativo, no una medición reciente del registro.

## Automatización de systemd para un host preinstalado

Prepare el software con `nodeadm install` durante la fase controlada de compilación/instalación. La siguiente automatización solo ejecuta la **inicialización** y almacena un registro vinculado al ID de máquina, el binario de nodeadm aprobado, NodeConfig y, opcionalmente, el manifiesto privado. Rechaza estados modificados o parcialmente inicializados en lugar de repetir silenciosamente el registro. No clone el estado de registro, los ID de máquina, las claves ni este directorio de estado en otros nodos.

Ejemplo de `/etc/eks/bootstrap.env` propiedad de root (modo `0600`):

```text
NODECONFIG_PATH=/etc/eks/nodeconfig.yaml
APPROVED_NODEADM_SHA256=REPLACE_WITH_APPROVED_64_HEX_DIGEST
# Only for the reviewed private-manifest path:
# LOCAL_MANIFEST=/etc/eks/manifest.json
```

Guarde el siguiente script, propiedad de root, en `/usr/local/bin/eks-hybrid-bootstrap.sh`. El propietario del host debe administrar los directorios y archivos protegidos que lo contienen; esto no protege frente a un root malicioso.

```bash
#!/usr/bin/env bash
# Initialize one preinstalled, uniquely identified host. Run as root.
set -euo pipefail
umask 077
[[ "$EUID" -eq 0 ]]
: "${NODECONFIG_PATH:?Absolute per-node config path}"
: "${APPROVED_NODEADM_SHA256:?Hash from the approved binary record}"
[[ "$NODECONFIG_PATH" = /* ]]
[[ "$APPROVED_NODEADM_SHA256" =~ ^[0-9a-f]{64}$ ]]
NODEADM=/usr/local/bin/nodeadm
STATE=/var/lib/eks-hybrid-bootstrap

private_file() {
  local path=$1 owner mode
  [[ -f "$path" && ! -L "$path" ]]
  owner=$(stat -c '%u' "$path")
  mode=$(stat -c '%a' "$path")
  [[ "$owner" == 0 && "$mode" == 600 ]]
}

private_file "$NODECONFIG_PATH"
test -s /etc/machine-id
test -s /opt/nodeadm/tracker
test -x "$NODEADM"
actual=$(sha256sum "$NODEADM")
[[ "${actual%% *}" == "$APPROVED_NODEADM_SHA256" ]]
if [[ -e /var/lib/eks/.nodeadm-installed || -e /var/lib/eks/.nodeadm-initialized ]]; then
  echo 'Legacy markers found: review existing installation and migrate state manually.' >&2
  exit 1
fi
[[ ! -L "$STATE" ]]
mkdir -p -m 700 "$STATE"
[[ "$(stat -c '%u:%a' "$STATE")" == 0:700 ]]
exec 9>"$STATE/lock"
flock -n 9

args=(--config-source "file://$NODECONFIG_PATH")
fingerprint_inputs=(/etc/machine-id "$NODEADM" "$NODECONFIG_PATH")
if [[ -n "${LOCAL_MANIFEST:-}" ]]; then
  [[ "$LOCAL_MANIFEST" = /* ]]
  private_file "$LOCAL_MANIFEST"
  fingerprint_inputs+=("$LOCAL_MANIFEST")
  args+=(--manifest-override "file://$LOCAL_MANIFEST" --private-mode)
fi
fingerprint=$(sha256sum "${fingerprint_inputs[@]}" | sha256sum)
fingerprint=${fingerprint%% *}
if [[ -e "$STATE/state" ]]; then
  private_file "$STATE/state"
  if [[ "$(cat "$STATE/state")" == "$fingerprint init-command-completed" ]]; then
    echo 'Matching initialization record; verify current Node readiness separately.'
    exit 0
  fi
  echo 'Changed identity/config or incomplete initialization: manual recovery required.' >&2
  exit 1
fi

"$NODEADM" config check --config-source "file://$NODECONFIG_PATH"
printf '%s started\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
# Failure/interruption retains started state and prevents an automatic retry.
"$NODEADM" init "${args[@]}"
systemctl is-active --quiet containerd
systemctl is-active --quiet kubelet
printf '%s init-command-completed\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
echo 'Init command completed; cluster registration/CNI/readiness still require verification.'
```

El registro de estado indica que el comando de inicialización terminó y que los dos servicios locales estaban activos en ese momento. **No significa que el nodo de Kubernetes esté Ready.** Si se produce un error, permanece un registro `started`; inspeccione el estado real del host/SSM/clúster antes de que un operador lo reconcilie. Un timeout del servicio o un comando interrumpido no demuestra que no se haya producido el registro.

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=Initialize one prepared EKS Hybrid Node
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
TimeoutStartSec=10min
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Instale y habilite la unidad mediante el responsable de configuración del host. `network-online.target` establece el orden de arranque según el servicio de espera del administrador de red; no garantiza que se pueda acceder al DNS, la VPN, EKS o los servicios de credenciales. `RemainAfterExit` registra el estado del servicio, no la salud del nodo. Systemd analiza un `EnvironmentFile`; el script no lo ejecuta con `source` de shell.

Las instalaciones existentes que solo usan archivos de marca requieren una migración explícita. Eliminar `.nodeadm-installed` / `.nodeadm-initialized` y reiniciar no es un procedimiento de restablecimiento. Para un cambio de configuración aprobado, como habilitar el archivo de credenciales, siga el procedimiento documentado de mantenimiento/inicialización y reconcilie después el registro de automatización.

En un reinicio normal, se reanudan kubelet y los servicios de credenciales configurados. Eliminar un objeto Node de Kubernetes no anula el registro de SSM ni detiene kubelet; un kubelet en ejecución y autorizado puede volver a crear el nodo. No use `delete node` para dar de baja un host ni dé por hecho que todos los hosts que fallan volverán a unirse.

## CNI de Cilium

Actualmente AWS admite sus compilaciones de **Cilium 1.17.x y 1.18.x** mantenidas para Hybrid Nodes. Los ejemplos publicados incluyen `1.17.9-0` y `1.18.3-0` en `oci://public.ecr.aws/eks/cilium/cilium`. Esto no recomienda seleccionar cualquier chart upstream más reciente.

La página actual de CNI de AWS excluye explícitamente **Ubuntu 20.04 y RHEL 8 para Cilium v1.18.3** debido al requisito de kernel. No afirme que cambiar solo el kernel establezca la compatibilidad con AWS; seleccione una combinación de SO/CNI que esté dentro de la matriz documentada.

Los ejemplos de Calico se trasladaron a `aws-samples/eks-hybrid-examples`. Esto no significa que el proyecto Calico esté obsoleto ni garantiza que todas las implementaciones existentes de Calico sigan funcionando. La página específica y actual de compatibilidad de CNI de AWS identifica las compilaciones de Cilium mantenidas por AWS y las capacidades compatibles.

### Valores de instalación

Este ejemplo de cluster-pool IPv4 supone que la red remota de Pod revisada es `10.85.0.0/16`, sin solapamiento con las redes de nodos/VPC/Service. Sustitúyala por los valores aprobados para el clúster **antes de la primera instalación**:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: eks.amazonaws.com/compute-type
              operator: In
              values: [hybrid]
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList: [10.85.0.0/16]
loadBalancer:
  serviceTopology: true
operator:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: In
                values: [hybrid]
  unmanagedPodWatcher:
    restart: false
envoy:
  enabled: false
kubeProxyReplacement: "false"
preflight:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
```

El selector de preflight es independiente de la affinity del agente. Un `/25` contiene 128 direcciones; Cilium cluster-pool reserva dos, por lo que no se garantiza que haya 128 direcciones de Pod utilizables. Coordine `maxPods` de kubelet, los Pods hostNetwork y las demás restricciones.

No modifique las entradas existentes del pool ni `clusterPoolIPv4MaskSize`. Cilium documenta la ampliación **añadiendo** una nueva entrada del pool; coordine primero las redes remotas de EKS, el enrutamiento/BGP, el solapamiento y la revisión de capacidad. Es demasiado tajante afirmar que «la lista completa nunca se puede ampliar».

```bash
# Cluster write; requires approved context, values and supported chart.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${CILIUM_VERSION:?Approved AWS chart version}"
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version "$CILIUM_VERSION" --namespace kube-system \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values cilium-values.yaml --wait --timeout 10m
```

Verifique el agente de Cilium en cada nodo Hybrid previsto, su operador, la preparación del nodo y el tráfico entre nodos. La affinity limita esta instalación a los nodos Hybrid; el controlador existente sigue administrando la red de los nodos de la nube. Un diseño que sustituya kube-proxy requiere su propio plan de accesibilidad de API y migración; no deje en los mismos nodos el comportamiento de kube-proxy en conflicto.

### Límites de actualización y eliminación

Antes de actualizar Cilium, guarde los valores/manifiestos actuales y una revisión explícita de Helm, revise las notas de actualización específicas de la versión y renderice el chart propuesto con los valores aprobados. Ejecute una **versión de preflight independiente**, limitada a los nodos Hybrid, con `preflight.enabled=true`, `agent=false`, `operator.enabled=false`. Espere a que estén listas **tanto** la cobertura del DaemonSet de preflight **como** la implementación de validación; crear la versión de preflight no equivale al resultado de la comprobación.

Elimine solo esa versión de preflight cuando se complete correctamente. Actualice con los valores guardados y revisados y el ajuste `upgradeCompatibility` apropiado. No arrastre a ciegas ajustes obsoletos entre versiones menores mediante `--reuse-values`. Para volver a una versión anterior se requiere una revisión explícita y verificada y comprobar el estado del CNI y la compatibilidad de los CRD; no se garantiza la recuperación automática del plano de datos.

Eliminar el CNI es una tarea disruptiva de migración o baja del servicio. Desaloje las cargas de trabajo y verifique qué nodos, políticas y CR todavía dependen de Cilium. No ejecute `kubectl get crds | grep cilium | xargs kubectl delete` en un clúster compartido. La desinstalación de Helm no garantiza que se eliminen las rutas, interfaces o el estado BPF del host. Siga el procedimiento de limpieza de CNI específico de la versión en los hosts identificados y desalojados; compruebe los montajes activos y los datos conservados antes de eliminar rutas.

## Bottlerocket usa un contrato de inicio diferente

AWS admite variantes de VMware Bottlerocket a partir de la versión **1.37.0**, con la variante x86_64 de Kubernetes compatible y sus requisitos previos. **No** ejecuta nodeadm. La guía de AWS configura los ajustes de Kubernetes/AWS y un **contenedor de inicio `eks-hybrid-setup`**. Los antiguos ejemplos `[settings.hybrid.ssm]` y `[settings.hybrid.iam-roles-anywhere]` no corresponden al contrato de configuración documentado.

Use la configuración completa del proveedor elegido que aparece en [Conectar nodos Hybrid con Bottlerocket](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html). Entre los campos comunes se incluyen:

```toml
# Common fragment only: combine with the provider-specific settings from AWS.
[settings.kubernetes]
cluster-name = "my-hybrid-cluster"
api-server = "https://REPLACE_WITH_CLUSTER_ENDPOINT"
cluster-certificate = "REPLACE_WITH_BASE64_CLUSTER_CA"
hostname-override = "hybrid-node-001"
provider-id = "eks-hybrid:///ap-northeast-2/my-hybrid-cluster/hybrid-node-001"
authentication-mode = "aws"
cloud-provider = ""
server-tls-bootstrap = true

[settings.network]
hostname = "hybrid-node-001"

[settings.aws]
region = "ap-northeast-2"

[settings.kubernetes.node-labels]
"eks.amazonaws.com/compute-type" = "hybrid"

[settings.bootstrap-containers.eks-hybrid-setup]
mode = "always"
user-data = "REPLACE_WITH_BASE64_PROVIDER_BOOTSTRAP_INPUT"
```

Este fragmento no es una configuración completa con la que se pueda arrancar. El proveedor SSM suministra la entrada de activación/Región `eks-hybrid-ssm-setup`; después del registro, el nombre del nodo cambia a `mi-*`. IAM Roles Anywhere suministra la entrada de certificado/clave `eks-hybrid-iam-ra-setup` y la configuración del proceso de credenciales de AWS, con el nombre de sesión del rol vinculado a la política del certificado. Incluya el proveedor ECR documentado y las etiquetas/ajustes específicos del proveedor para el nodo.

Base64 es codificación, no cifrado. Los datos de inicio del proveedor pueden contener secretos de activación o claves privadas: proteja la configuración de la VM, guestinfo, los permisos de administración y las exportaciones de diagnóstico; nunca los incluya en un repositorio público ni en registros. El acceso SSH mediante el contenedor de administración es opcional y debe autorizarse por separado. No clone como plantilla limpia una VM que ya se haya registrado.

Configure la **VM nueva, aprovisionada y apagada** que se haya aprobado antes del primer encendido. La guía de AWS usa `settings.toml` codificado en base64 con `guestinfo.userdata.encoding=base64`; no etiquete base64 simple como `gzip+base64`. Confirme las versiones implementadas de govc/VMware, el almacén de datos, la red, la propiedad de la plantilla y el método de entrega de secretos antes de aprovisionar. En esta auditoría no se ejecutó ninguna implementación de VMware.

## Ubicación de complementos e identidad de Pods

Dirija el tráfico del servidor de API al listener real del webhook/API agregada. Si no se puede acceder a los CIDR de Pod Hybrid, coloque el **servidor/operador del webhook** en nodos de la nube accesibles o valide un diseño apropiado de hostNetwork cuando sea compatible. Esto no significa que todos los agentes de CloudWatch/ADOT o los Pods de aplicaciones deban ejecutarse en la nube.

Para ubicar Pods en nodos de la nube, use una etiqueta/affinity explícita y revisada y compruebe la capacidad y las taints. `NotIn [hybrid]` también puede coincidir con nodos sin etiqueta; no demuestra que el destino sea una instancia EC2 aprobada.

En un clúster mixto de nube e Hybrid, AWS recomienda al menos una réplica de CoreDNS en cada lado. Cuatro réplicas con distribución blanda no garantizan exactamente dos por lado. Aplique y verifique el procedimiento de ubicación y Service Traffic Distribution de [Configuración de red](./02-network-configuration.md).

| SO del nodo | Preparación de Pod Identity |
|---|---|
| Ubuntu/RHEL/AL2023 | `spec.hybrid.enableCredentialsFile: true`, seguido del `nodeadm init` documentado; la configuración del agente habilita `daemonsets.hybrid.create` |
| Bottlerocket | SO **1.39.0+**; el comando de inicio del proveedor usa `--enable-credentials-file=true`; habilite `daemonsets.hybrid-bottlerocket.create` |

Los mínimos de compatibilidad son el agente **v1.3.3-eksbuild.1** para sistemas que no son Bottlerocket y **v1.3.7-eksbuild.2** para Bottlerocket; no son versiones objetivo para instalar actualmente. Seleccione una versión/configuración del complemento actualmente compatible con el clúster. Las ubicaciones de montaje de las credenciales temporales son distintas: `/eks-hybrid/.aws/credentials` frente a `/var/eks-hybrid/.aws/credentials` en Bottlerocket.

Las implementaciones privadas necesitan la ruta del servicio `eks-auth`, el permiso `eks-auth:AssumeRoleForPodIdentity` del rol de nodo y la asociación/confianza/permisos de Pod Identity para cada carga de trabajo. No basta con instalar el agente. Combine la configuración necesaria del DaemonSet mediante el responsable del complemento; no sobrescriba un complemento existente con un `create-addon` a ciegas.

## Actualización, recuperación y eliminación

Es preferible añadir y **inicializar/verificar por completo** la capacidad de reemplazo antes de desalojar los nodos antiguos. Instalar binarios en hosts nuevos no añade capacidad al clúster. Mantenga la disponibilidad de DNS necesaria; no reduzca a ciegas una implementación existente de cuatro réplicas de CoreDNS a dos como medida de «resiliencia».

Para un nodo antiguo identificado, verifique el contexto, el UID del nodo, la correspondencia con el host y la propiedad de cargas de trabajo/datos. Márquelo como no programable, desaloje las cargas con un timeout y deténgase ante cualquier error de PDB/desalojo. `--delete-emptydir-data` permite explícitamente perder datos locales de emptyDir; no es una opción de seguridad predeterminada. Los Pods no administrados, los datos persistentes locales y los DaemonSet requieren tratamiento propio. No use `--force` ni deshabilite el desalojo para aparentar que se completó correctamente uno bloqueado.

Para una actualización in situ, ejecute el `nodeadm upgrade` documentado en el host desalojado y, después, verifique la identidad, las versiones del software, Ready/CNI/DNS y el comportamiento de las cargas de trabajo antes de volver a permitir la programación. Es una operación disruptiva; «no hay capacidad de reserva» no la hace segura.

Para dar de baja un nodo, detenga cualquier ruta automática de inicio/reunión, complete la eliminación documentada de nodeadm y la baja del proveedor; después, elimine el objeto Node exacto y reconcilie los recursos restantes del CNI mediante su responsable. Conserve en privado las pruebas de recuperación necesarias.

`nodeadm uninstall` no equivale a `kubectl drain` ni a `kubectl delete node`. Normalmente se niega a continuar si quedan Pods de cargas de trabajo. No elimina todos los artefactos de CNI/complementos. **Desde v1.0.9, ni siquiera la ruta documentada de desinstalación forzada o sin confirmación borra `/var/lib/kubelet`**, porque las rutas montadas pueden exponer el sistema de archivos del host. `--force` elimina rutas adicionales predeterminadas de CNI/Kubernetes; no es una opción genérica de «omitir confirmación y borrar todo». Inspeccione los montajes y los datos antes de cualquier eliminación manual.

Si se aprueba una reinstalación real tras la eliminación, vuelva a ejecutar **install → config check → init** con credenciales válidas y reconcilie el registro de automatización. Nunca considere que un error de autenticación, un perfil existente o una inicialización parcial son motivos suficientes para desinstalar un nodo activo.

## Solución de problemas

| Observación | Qué investigar antes de cambiar el estado |
|---|---|
| Error de firma del instalador SSM en una versión antigua de nodeadm | Verifique que nodeadm aprobado sea al menos 1.0.19; no omita las comprobaciones de firma |
| Error del administrador de paquetes/descarga | Acceso al repositorio real, proxy, confianza de CA, bloqueos de paquetes, SO/runtime compatibles y errores; `dnf update` es una actualización del sistema, no un diagnóstico |
| Timeout | Determine qué fase falló y su accesibilidad; aumentar solo el timeout no lo corrige |
| IP del nodo fuera de las redes remotas | Tipo de IP real del nodo y CIDR de nodo remoto de EKS |
| API inaccesible / Unauthorized | DNS/rutas/443 y ruta de retorno, rol Hybrid previsto, confianza/validez de credenciales, entrada de acceso `HYBRID_LINUX` |
| NotReady | Registros del CNI/agente y puertos del dataplane elegido, runtime, condiciones de disco/recursos; no todos los casos se deben a la falta de CNI |
| Error de extracción de imagen o x509 | Imagen/ruta de autenticación exactas, ECR API/DKR/S3, CA del registro privado y nombre de host; mantenga habilitada la verificación TLS |
| Activación/token caducados | Vencimiento/capacidad/Región de la activación frente a la renovación de credenciales del agente en ejecución, sincronización horaria y accesibilidad de AWS; reiniciar no garantiza que se solucione |
| Perfil Hybrid existente / inicialización parcial | Inspeccione el estado actual de nodeadm/proveedor y el clúster previsto; conserve las pruebas, no desinstale automáticamente |

```bash
# Private diagnostic output on the identified node; no nonexistent nodeadm status.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet --since '-15 min' --lines 200 --no-pager
sudo nodeadm debug --config-source file:///etc/eks/nodeconfig.yaml
```

`nodeadm debug` realiza lecturas de AWS/clúster y comprobaciones de credenciales. Mantenga su salida en privado y elimine los datos sensibles antes de compartirla. `sudo aws sts get-caller-identity` puede usar una cadena de credenciales de root/administrador distinta y no demuestra qué credenciales usa kubelet. No use `curl -k` para validar TLS. La confianza de CA del servidor y la aprobación/emisión de certificados de cliente kubelet son mecanismos independientes.

## Referencias principales

- [Comandos de nodeadm para Hybrid, ubicaciones de archivos y comportamiento de eliminación](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Credenciales de Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Duración de CreateSession de IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [CreateActivation de SSM](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html)
- [Compatibilidad y ciclo de vida del CNI Hybrid de AWS](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Ampliación de Cilium cluster-pool](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/concepts/ipam/cluster-pool.rst)
- [Inicio de Hybrid en Bottlerocket](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html)
- [Complementos e identidad de Pods para Hybrid](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [Configuración de hosts de registro de containerd](https://github.com/containerd/containerd/blob/v2.2.0/docs/hosts.md)
- [Semántica de systemd network-online](https://systemd.io/NETWORK_ONLINE/)
- [Diferencias de versión de Kubernetes](https://kubernetes.io/releases/version-skew-policy/)

< [Anterior: Configuración con acceso restringido a Internet](./03-airgap-setup.md) | [Tabla de contenido](./README.md) | [Siguiente: Integración de GPU](./05-gpu-integration.md) >
