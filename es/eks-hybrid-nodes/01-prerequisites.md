# Requisitos previos

> **Versiones compatibles**: Ejemplos revisados para EKS 1.36 / nodeadm híbrido 1.0.20; consulte los requisitos específicos del SO que se indican a continuación
> **Última actualización**: 13 de septiembre de 2026

Prepare el host, la red, las credenciales y el acceso al clúster antes de unir un nodo híbrido. Las comprobaciones locales de esquema, criptografía y entradas no validan la red física, el runtime de GPU ni el clúster de producción. Durante esta auditoría no se ejecutaron cambios en la nube, la red del host, los controladores de GPU ni la creación de imágenes.

![Requisitos previos de los nodos híbridos y enrutamiento bidireccional entre VPC y las instalaciones locales. Declarar CIDR remotos no crea todas las rutas ni reglas de firewall.](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

## Sistemas operativos y runtime

| Integración híbrida validada por AWS | Versiones / alcance |
|---------------------------------|------------------|
| Ubuntu | 20.04, 22.04, 24.04; revise por separado el mantenimiento de seguridad de la distribución |
| RHEL | 8, 9; revise el kernel/CNI y la suscripción/asistencia de Red Hat |
| AL2023 | Entornos **virtualizados** locales; no bare metal genérico ni derechos de soporte del SO de AWS fuera de EC2 |
| Bottlerocket | Variantes de VMware v1.37.0+, disponibles para Kubernetes 1.28+, **solo x86_64**; procedimiento de arranque distinto |

Estos mínimos no hacen que las versiones antiguas de Kubernetes tengan compatibilidad vigente con EKS. Elija una versión activa de EKS y la cohorte correspondiente de SO/runtime/CNI. AWS admite la integración híbrida con Ubuntu/RHEL, no el mantenimiento del SO por parte del proveedor.

Las instalaciones nuevas y las actualizaciones de SSM requieren **nodeadm 1.0.19+** porque los binarios anteriores contienen una clave de firma de SSM obsoleta. La versión revisada es **v1.0.20**. Use nodeadm híbrido, no la herramienta de AMI de EKS para EC2 de nombre parecido.

kube-proxy de EKS 1.31+ en ARM requiere ARMv8.2+crypto. El hardware anterior a Pi 5/Cortex-A72 no cumple ese requisito; una CPU de Pi 5 por sí sola no valida la pila completa. La solución temporal anterior para kube-proxy 1.30 dejó de tener compatibilidad extendida con EKS en julio de 2026.

Se requiere containerd; Docker Engine no. Una comprobación de “containerd 1.6+” o de la versión de Docker no determina la compatibilidad actual con CRI.

| SO / opción | Fuente de containerd de nodeadm |
|-------------|--------------------------|
| Ubuntu / AL2023 | `distro` es el valor predeterminado admitido |
| RHEL | `docker`, o `none` con un runtime compatible preinstalado; `distro` no es válido |
| AL2023 | `docker` no es compatible |
| Instalación manual del runtime | `none` omite la instalación; no proporciona un runtime |

La corrección histórica de Ubuntu 24.04 para la terminación de Pod/AppArmor requería containerd 1.7.19+ o la actualización de AppArmor adecuada. Esto no es una recomendación para instalar versiones antiguas. Revise los requisitos del kernel del CNI elegido; ni “kernel 5.4+” ni reemplazar el kernel a ciegas es suficiente.

### Dimensionamiento e inspección del host

AWS recomienda un mínimo de **1 vCPU y 1 GiB de memoria** para un host. La capacidad real necesaria depende de las cargas de trabajo y de la configuración operativa.

Dimensione la CPU y la memoria según el uso combinado del runtime de contenedores, el CNI, los agentes de administración y las cargas de trabajo. Asigne espacio en disco para el SO, las imágenes de contenedor y los registros, con margen operativo.

```bash
# Run these read-only checks on the intended hybrid host.
cat /etc/os-release
uname -m
uname -r
free -h
df -h /
swapon --show
ip -j link show
# When already installed, inspect the actual CRI runtime:
containerd --version
```

La versión de un binario no demuestra que kubelet use ese socket de runtime. Revise el intercambio, los cgroups, el reenvío, los módulos de CNI y los firewalls con el propietario del host. Los cambios indiscriminados a swapoff/fstab/sysctl/MTU no son portables a todos los hosts compatibles.

### Instalar, validar y luego inicializar

En los hosts Ubuntu/AL2023 preparados, la secuencia siguiente instala las dependencias antes de unir el host. RHEL necesita la fuente de runtime descrita anteriormente; Bottlerocket sigue otro procedimiento.

```bash
set -euo pipefail
# Installation/bootstrap sequence for prepared Ubuntu/AL2023 hosts.
# RHEL requires --containerd-source docker, or none with a preinstalled compatible runtime.
# These commands mutate the host; review OS/runtime/network/identity first.
sudo nodeadm install 1.36 --credential-provider ssm --containerd-source distro \
  --region ap-northeast-2 --timeout 20m
sudo nodeadm config check -c file:///etc/eks/nodeConfig.yaml
sudo nodeadm init -c file:///etc/eks/nodeConfig.yaml
```

La configuración del nodo ya debe contener las entradas previstas para el clúster y el proveedor. Proteja los archivos de configuración que contengan credenciales con el modo 0600 y no incluya los códigos de activación en imágenes maestras ni registros. Estos comandos modifican el host. No omita fases de validación para ocultar fallos. `nodeadm upgrade` es disruptivo y requiere evacuar las cargas de trabajo.

## Preparación de imágenes con Packer

Los ejemplos de AWS abarcan Ubuntu 22.04/24.04 y RHEL 8/9 con destinos vSphere OVA y QEMU qcow2/raw. La **plantilla v1.0.20** revisada no es una canalización de imágenes lista para EKS 1.36:

- La validación de `K8S_VERSION` todavía solo permite 1.26–1.31. Mantenga una bifurcación actual revisada; no baje de versión para ajustarse al ejemplo.
- `NODEADM_ARCH` espera **`amd` o `arm`** y después añade `64`; el antiguo `amd64` se convierte en `amd6464`.
- `CREDENTIAL_PROVIDER=iam` de Packer se asigna a **`iam-ra`** de nodeadm.
- El archivo real es `hybrid-nodes-template.pkr.hcl`; no existe el origen `general-build.qemu.al2023`.
- Revise las descargas mutables de `releases/latest`, `insecure_connection=true` de vSphere, las contraseñas predeterminadas del generador y los requisitos globales de variables. Los aprovisionadores de RHEL codifican repositorios x86; cambiar únicamente la arquitectura del binario no produce una compilación ARM.

| Grupo de entradas | Revisión |
|-------------|--------|
| Herramientas | Packer ≥1.11, complemento vSphere ≥1.4 o QEMU 1.x; fije una combinación probada |
| Comunes | `ISO_URL`, `ISO_CHECKSUM` verificada, `PKR_SSH_PASSWORD`, `K8S_VERSION`, `NODEADM_ARCH`, `CREDENTIAL_PROVIDER` |
| RHEL | `RH_USERNAME`, `RH_PASSWORD`, `RHEL_VERSION`; excluya los secretos de las imágenes finales y los registros |
| vSphere | Servidor/usuario/contraseña, centro de datos, clúster, almacén de datos, red, **VSPHERE_OUTPUT_FOLDER** |
| QEMU | **PACKER_OUTPUT_FORMAT** (`qcow2`/`raw`), compatibilidad de CPU/virtualización |

El origen también incluye generadores de AMI de AWS con coste; eso no autoriza ejecutar máquinas en la nube como nodos híbridos. Valide una plantilla mantenida y la imagen resultante. Aquí no se realizó ninguna compilación de Packer/VM.

## Compatibilidad con GPU

Compruebe en conjunto la variante de GPU, la arquitectura de CPU, el SO/kernel, el controlador NVIDIA compatible, el kit de herramientas/runtime de contenedores, la imagen de CUDA/framework y la memoria. Los valores anteriores de controlador 525/535/545/550 y CUDA 11.8/12.x mezclaban mínimos históricos y recomendaciones; no son requisitos universales actuales para Nodos híbridos.

H100 80GB, H200 141GB, A100 40/80GB y L40S 48GB son ejemplos de variantes, no una lista completa de variantes certificadas. Cuatro GB no es un mínimo significativo para todos los modelos. No se requiere un compilador de CUDA en el host solo para ejecutar un contenedor GPU empaquetado correctamente; las versiones del controlador y del compilador significan cosas distintas.

```bash
# On a host where the driver is already installed:
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
# Optional: nvcc reports the locally installed compiler, if present.
if command -v nvcc >/dev/null 2>&1; then nvcc --version; fi
```

Siga las instrucciones vigentes de NVIDIA sobre compatibilidad y plataformas para la cohorte elegida. Pruebe los cambios de controlador/kernel en un host de prueba sin cargas de trabajo. Instalar una rama antigua del controlador o reiniciar containerd en un nodo de trabajo activo no es una comprobación de requisitos previos inocua.

## Red, CIDR y MTU

Los Nodos híbridos requieren **conectividad privada bidireccional** fiable, incluido el acceso del plano de control a kubelet y a los webhooks alojados en los hosts híbridos. El acceso público a la API cambia el tráfico del nodo a la API, no la ruta privada inversa necesaria.

AWS recomienda **un ancho de banda de 100 Mbps y un RTT de 200 ms o menos** como orientación general de conectividad. Establezca objetivos de ancho de banda, latencia y pérdida de paquetes según las necesidades de las cargas de trabajo y mídalos a lo largo de la ruta de conexión real. Configure la MTU después de tener en cuenta la sobrecarga de encapsulación de túneles y los tamaños compatibles con los dispositivos de la ruta.

Los CIDR remotos de nodo/Pod usan IPv4 RFC1918 o CGNAT, sin solaparse entre sí, con las redes de VPC o con las redes de servicio. Hasta 15 CIDR de cada tipo remoto caben en **un** bloque de configuración de red de nodos remotos y **uno** de red de Pods remotos. El enrutamiento de Pods entre clústeres también requiere una separación deliberada.

Guarde un `network-plan.json` revisado:

```json
{
  "vpcCidrs": [
    "10.0.0.0/16"
  ],
  "serviceCidrs": [
    "10.100.0.0/16"
  ],
  "remoteNodeCidrs": [
    "10.80.0.0/16"
  ],
  "remotePodCidrs": [
    "10.85.0.0/16"
  ]
}
```
```bash
: "${NETWORK_PLAN_JSON:?Set the reviewed local network plan JSON}"
export NETWORK_PLAN_JSON
python3 - <<'PY'
import ipaddress, itertools, json, os
from pathlib import Path
plan = json.loads(Path(os.environ["NETWORK_PLAN_JSON"]).read_text())
allowed = [ipaddress.ip_network(c) for c in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")]
groups = {}
for key in ("vpcCidrs", "serviceCidrs", "remoteNodeCidrs", "remotePodCidrs"):
    values = plan[key]
    if not isinstance(values, list) or not values:
        raise SystemExit(f"{key} must be a nonempty list for this example")
    groups[key] = [ipaddress.ip_network(v, strict=True) for v in values]
    if any(n.version != 4 for n in groups[key]):
        raise SystemExit("This Hybrid Nodes plan requires IPv4")
for key in ("remoteNodeCidrs", "remotePodCidrs"):
    if len(groups[key]) > 15 or any(not any(n.subnet_of(a) for a in allowed) for n in groups[key]):
        raise SystemExit("Remote CIDRs must use RFC1918/CGNAT ranges, at most 15 per kind")
flat = [(key, n) for key, networks in groups.items() for n in networks]
for (ka, a), (kb, other) in itertools.combinations(flat, 2):
    if a.overlaps(other):
        raise SystemExit(f"Overlapping CIDRs: {ka} {a}, {kb} {other}")
print("CIDR syntax/range/non-overlap checks passed; routing and reachability remain unverified")
PY
```

Esto comprueba la sintaxis, los rangos y los solapamientos, pero no la conectividad. Configure las rutas de retorno de VPC a través del TGW/VGW real, además de las rutas de retorno locales y las rutas de Pods por nodo en las instalaciones.

| Flujo | Revisión |
|------|--------|
| Nodo/Pod remoto → API TCP443 | Ingreso adicional en el grupo de seguridad del clúster para los CIDR previstos |
| ENI del plano de control → nodo TCP10250 | Egreso restringido del clúster, ruta privada e ingreso en el host/firewall local |
| Plano de control → webhook | IP real del Pod, puerto, rutas y firewall |
| Host/Pod → credenciales/imágenes/DNS/hora | Endpoints del proveedor, registro, DNS y sincronización del reloj |

TCP10250 no es tráfico entrante de kubelet al grupo de seguridad del servidor de API. EKS por sí solo no crea todas las reglas personalizadas; eksctl puede automatizar los recursos del lado de VPC que administra. Compruebe las cuotas reales de reglas en lugar de considerar 60 un máximo inmutable.

AWS recomienda usar solo endpoints públicos o solo privados. Si se habilitan ambos, los nodos fuera de la VPC resuelven direcciones públicas y **pueden** no unirse si las rutas/reglas de acceso son distintas. No se trata de un rechazo categórico de la API. El acceso solo privado también necesita DNS privado y acceso administrativo.

## Credenciales específicas del proveedor

Prepare las entradas de AWS con la identidad de administrador prevista. Guarde el material de activación en un directorio privado:

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended account}"
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the intended cluster}"
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/hybrid-preflight.XXXXXXXX")
export EXPECTED_ACCOUNT_ID AWS_REGION CLUSTER_NAME
printf 'Private preparation directory: %s\n' "$WORK_DIR"
```

Tanto SSM como Roles Anywhere requieren conectividad con AWS. Una CA local o credenciales almacenadas en caché durante más tiempo no crean un plano de control sin conexión.

### Rol y activación de SSM

El rol necesita permisos `eks:DescribeCluster`, extracción de ECR y permisos de núcleo/limpieza de SSM. **AmazonEKSWorkerNodeMinimalPolicy por sí sola no proporciona DescribeCluster.** El permiso `eks-auth:AssumeRoleForPodIdentity` de Pod Identity es independiente.

Reemplace de forma coherente los valores de ejemplo de cuenta/Región/clúster. La operación de lista siguiente no permite limitar el recurso por instancia, por lo que su comodín se restringe a la Región prevista:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:ssm:ap-northeast-2:123456789012:*"
        }
      }
    }
  ]
}
```
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "eks:DescribeCluster",
      "Resource": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DescribeInstanceInformation",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DeregisterManagedInstance",
      "Resource": "arn:aws:ssm:ap-northeast-2:123456789012:managed-instance/*",
      "Condition": {
        "StringEquals": {
          "ssm:resourceTag/EKSClusterARN": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
        }
      }
    }
  ]
}
```

Adjunte los permisos revisados `AmazonEC2ContainerRegistryPullOnly` y `AmazonSSMManagedInstanceCore`, o permisos equivalentes. La etiqueta `EKSClusterARN` de la activación debe coincidir con la política de cancelación de registro.

Prepare un límite de registro deliberado y una caducidad de **registro** de 24 horas:

```bash
: "${HYBRID_ROLE_NAME:?Use the reviewed SSM-trusting role name}"
: "${REGISTRATION_LIMIT:?Set a deliberate node registration limit}"
export HYBRID_ROLE_NAME REGISTRATION_LIMIT
python3 - <<'PY'
import json, os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
account, region, cluster = (os.environ[k] for k in ("EXPECTED_ACCOUNT_ID", "AWS_REGION", "CLUSTER_NAME"))
if not re.fullmatch(r"\d{12}", account) or not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid account/Region")
if region.startswith(("cn-", "us-gov-")):
    raise SystemExit("Hybrid Nodes is not available in this Region family")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", cluster):
    raise SystemExit("Invalid cluster name")
role = os.environ["HYBRID_ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Use the actual IAM role name, not a role ARN")
limit = int(os.environ["REGISTRATION_LIMIT"])
if not 1 <= limit <= 1000:
    raise SystemExit("RegistrationLimit must be 1..1000 per activation; review service quotas separately")
body = {"DefaultInstanceName": "eks-hybrid-node", "IamRole": role, "RegistrationLimit": limit,
        "Description": "Reviewed EKS hybrid activation",
        "Tags": [{"Key": "EKSClusterARN", "Value": f"arn:aws:eks:{region}:{account}:cluster/{cluster}"}],
        "ExpirationDate": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
(Path(os.environ["WORK_DIR"]) / "activation-request.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```
```bash
set -euo pipefail
# Run only after the role/trust/tag policy and registration scope are prepared.
check_account
aws ssm create-activation --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/activation-request.json" --output json \
  > "$WORK_DIR/activation-response.json"
chmod 600 "$WORK_DIR/activation-response.json"
# The response contains the secret ActivationCode. Do not print or commit it.
```

ActivationCode se devuelve una sola vez; distribuya de forma segura ActivationId junto con él. La caducidad/eliminación de la activación no cancela el registro de instancias administradas existentes. [CreateActivation RegistrationLimit](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html) sigue teniendo un límite de 1–1.000 por activación. No es un umbral de nivel gratuito para toda la flota; los precios actuales se explican en la [comparación de proveedores de credenciales](README.md#credential-providers).

SSM usa un nombre de nodo `mi-...` y credenciales fijas de una hora. El retroceso de los reintentos de actualización puede retrasar la reconexión después de una interrupción de red. No registre credenciales en los logs.

### Confianza y duración de Roles Anywhere

Use un rol, un ancla de confianza y un perfil adecuados al proveedor. Vincule el nombre de sesión a la identidad del certificado/nodeName; la comparación anterior de PrincipalTag/RequestTag no lo hacía.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": [
        "sts:TagSession",
        "sts:SetSourceIdentity"
      ],
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        },
        "StringEquals": {
          "sts:RoleSessionName": "${aws:PrincipalTag/x509Subject/CN}"
        }
      }
    }
  ]
}
```
```json
{
  "name": "hybrid-node-profile",
  "roleArns": [
    "arn:aws:iam::123456789012:role/EKSHybridNodeRole"
  ],
  "enabled": true,
  "acceptRoleSessionName": true,
  "durationSeconds": 3600
}
```

Reemplace el ARN del ancla, conceda permisos limitados de DescribeCluster/ECR y establezca **acceptRoleSessionName=true**.

```text
effectiveDuration = min(profileDuration, requestedDuration)
                    or profileDuration when the request omits duration
effectiveDuration <= role.MaxSessionDuration
```

Las duraciones solicitadas y del perfil van de 900 a 43.200 segundos. **CreateSession permite la igualdad**: un perfil de 3.600, sin anulación, y un máximo de rol de 3.600 son válidos. La formulación anterior, estricta (“mayor que”), era inexacta. La validez/revocación del certificado y la conectividad con AWS siguen siendo necesarias.

### Claves y certificados por nodo

Use un directorio privado en el nodo nuevo previsto. Genere una clave/CSR única; este ejemplo acepta una etiqueta DNS en minúsculas sencilla. Envíe la CSR al emisor aprobado; no coloque una clave de firma de CA en los nodos.

```bash
set -euo pipefail
umask 077
: "${WORK_DIR:?Set a private preparation directory on this node}"
: "${NODE_NAME:?Use a unique certificate CN / node name}"
export NODE_NAME
python3 - <<'PY'
import os, re
name = os.environ["NODE_NAME"]
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", name):
    raise SystemExit("This example requires a lowercase DNS label of 2..63 characters")
PY
test ! -e "$WORK_DIR/node.key"
test ! -e "$WORK_DIR/node.csr"
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$WORK_DIR/node.key"
chmod 600 "$WORK_DIR/node.key"
openssl req -new -key "$WORK_DIR/node.key" -out "$WORK_DIR/node.csr" -subj "/CN=$NODE_NAME"
# Send the CSR to the approved PKI issuer; do not copy its CA private key to nodes.
```

Verifique la cadena emitida, la CA aprobada, la validez/revocación, la correspondencia de la clave y el CN. Mantenga los relojes sincronizados. Solo para un nodo nuevo:

```bash
set -euo pipefail
: "${ISSUED_NODE_CERT:?Set the verified certificate/chain issued for this node}"
: "${WORK_DIR:?Set the private directory containing the node key}"
# New-node installation only; do not overwrite an existing identity.
sudo test ! -e /etc/iam/pki/server.key
sudo test ! -e /etc/iam/pki/server.pem
sudo install -d -m 0700 /etc/iam/pki
sudo install -m 0644 "$ISSUED_NODE_CERT" /etc/iam/pki/server.pem
sudo install -m 0600 "$WORK_DIR/node.key" /etc/iam/pki/server.key
```

Estos no son los archivos de CA de la API de Kubernetes de EKS. No clone identidades de nodo en imágenes ni sobrescriba silenciosamente una clave existente.

## Preparación de CloudFormation

Las plantillas v1.0.20 fijadas son puntos de partida para el aprovisionamiento. La plantilla de SSM crea el rol, **no la activación**. Revise el amplio alcance de DescribeCluster y los nombres de exportación fijos antes de usarlos con varios clústeres.

El valor `CertAttributeTrustPolicy` de IRA es la cadena literal **`${aws:PrincipalTag/x509Subject/CN}`**, no `"CN"`. Este script auxiliar de Python, que usa `cryptography`, serializa correctamente PEM y comprueba la forma básica y la validez actual de la CA, pero no la autoridad del emisor ni la revocación:

```bash
: "${CA_PEM_FILE:?Set the approved CA certificate file, not a private key}"
: "${ROLE_NAME:?Set the new role name selected by the IaC owner}"
export CA_PEM_FILE ROLE_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
from cryptography import x509
from datetime import datetime, timezone
raw = Path(os.environ["CA_PEM_FILE"]).read_bytes()
if b"PRIVATE KEY" in raw or raw.count(b"-----BEGIN CERTIFICATE-----") != 1:
    raise SystemExit("Provide one reviewed CA certificate")
cert = x509.load_pem_x509_certificate(raw)
if not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
    raise SystemExit("Certificate is not a CA")
now = datetime.now(timezone.utc)
if not cert.not_valid_before.replace(tzinfo=timezone.utc) <= now <= cert.not_valid_after.replace(tzinfo=timezone.utc):
    raise SystemExit("CA certificate is not currently valid")
role = os.environ["ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Invalid IAM role name")
body = [
    {"ParameterKey": "RoleName", "ParameterValue": role},
    {"ParameterKey": "CertAttributeTrustPolicy", "ParameterValue": "${aws:PrincipalTag/x509Subject/CN}"},
    {"ParameterKey": "CABundleCert", "ParameterValue": raw.decode("ascii")}
]
(Path(os.environ["WORK_DIR"]) / "cfn-iamra-parameters.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

Compare las claves de parámetros y los valores AllowedValues con la plantilla fijada, limite el alcance de las políticas y las exportaciones de espacios de nombres con el responsable de IaC, y luego revise el conjunto de cambios. No despliegue abreviaturas PEM con formato incorrecto ni una plantilla mutable de main sin revisar.

## Planes de acceso y creación del clúster

Prefiera una entrada de acceso **HYBRID_LINUX** para el rol IAM del nodo:

```json
{
  "clusterName": "my-hybrid-cluster",
  "principalArn": "arn:aws:iam::123456789012:role/EKSHybridNodeRole",
  "type": "HYBRID_LINUX"
}
```

La asignación usa `system:node:{{SessionName}}` y grupos de arranque de nodo. Confirme la autenticación API/API_AND_CONFIG_MAP y quién es responsable de ella. No aplique un ConfigMap `aws-auth` de reemplazo con un solo rol que borre las asignaciones existentes; los cambios de asignaciones heredadas requieren una migración controlada.

Reemplace todos los identificadores de abajo por recursos existentes revisados. Los endpoints solo privados, IPv4 y la versión 1.36 son explícitos. El permiso de administrador para quien crea el clúster sirve para un laboratorio controlado; decida deliberadamente el acceso de los operadores de producción.

Para eksctl 0.229.0, use los valores documentados de proveedor **SSM/IRA**. Si se proporciona un roleARN, prepare los recursos del proveedor por separado:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-hybrid-cluster
  region: ap-northeast-2
  version: '1.36'
iam:
  serviceRoleARN: arn:aws:iam::123456789012:role/EKSClusterRole
accessConfig:
  authenticationMode: API_AND_CONFIG_MAP
  bootstrapClusterCreatorAdminPermissions: true
kubernetesNetworkConfig:
  ipFamily: IPv4
  serviceIPv4CIDR: 10.100.0.0/16
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      ap-northeast-2a:
        id: subnet-0123456789abcdef0
      ap-northeast-2c:
        id: subnet-0123456789abcdef1
  controlPlaneSecurityGroupIDs:
  - sg-0123456789abcdef0
  clusterEndpoints:
    privateAccess: true
    publicAccess: false
remoteNetworkConfig:
  iam:
    provider: SSM
    roleARN: arn:aws:iam::123456789012:role/EKSHybridNodeRole
  vpcGatewayID: tgw-0123456789abcdef0
  remoteNodeNetworks:
  - cidrs:
    - 10.80.0.0/16
  remotePodNetworks:
  - cidrs:
    - 10.85.0.0/16
```

Al aprovisionar con eksctl, use `--without-nodegroup` y una ruta explícita a un kubeconfig privado. La validez del esquema no demuestra los permisos IAM, las rutas ni la conectividad con la gateway. La documentación anterior de eksctl que solo contemplaba el lanzamiento está desactualizada: EKS admite actualmente la configuración de redes remotas híbridas en clústeres existentes mediante el flujo de trabajo API adecuado.

Solicitud equivalente de EKS CreateCluster:

```json
{
  "name": "my-hybrid-cluster",
  "version": "1.36",
  "roleArn": "arn:aws:iam::123456789012:role/EKSClusterRole",
  "resourcesVpcConfig": {
    "subnetIds": [
      "subnet-0123456789abcdef0",
      "subnet-0123456789abcdef1"
    ],
    "securityGroupIds": [
      "sg-0123456789abcdef0"
    ],
    "endpointPrivateAccess": true,
    "endpointPublicAccess": false
  },
  "kubernetesNetworkConfig": {
    "ipFamily": "ipv4",
    "serviceIpv4Cidr": "10.100.0.0/16"
  },
  "accessConfig": {
    "authenticationMode": "API_AND_CONFIG_MAP",
    "bootstrapClusterCreatorAdminPermissions": true
  },
  "remoteNetworkConfig": {
    "remoteNodeNetworks": [
      {
        "cidrs": [
          "10.80.0.0/16"
        ]
      }
    ],
    "remotePodNetworks": [
      {
        "cidrs": [
          "10.85.0.0/16"
        ]
      }
    ]
  }
}
```

Elija un único propietario de la infraestructura; no ejecute ambas vías. Valide la identidad real del clúster/endpoint, los permisos de los operadores y el acceso de los nodos antes de unir hosts. Estos identificadores de ejemplo de AWS no son recursos verificados.

## Complementos

Estos mínimos de compatibilidad documentados para nodos híbridos **no son objetivos de instalación** para todas las versiones de Kubernetes:

| Complemento | Mínimo de compatibilidad híbrida |
|--------|-----------------------------|
| kube-proxy / CoreDNS | 1.25.14-eksbuild.2 / 1.9.3-eksbuild.7 |
| ADOT / CloudWatch Observability | 0.102.1-eksbuild.2 / 2.2.1-eksbuild.1 |
| Pod Identity Agent | 1.3.3-eksbuild.1 en general; **1.3.7-eksbuild.2 en Bottlerocket**, que también requiere **Bottlerocket OS 1.39.0+** |
| Node monitoring / snapshot controller | 1.2.0-eksbuild.1 / 8.1.0-eksbuild.2 |
| Private CA Connector / FSx CSI / Secrets Store provider | 1.6.0-eksbuild.1 / 1.7.0-eksbuild.1 / 2.1.1-eksbuild.1 |
| Metrics Server / cert-manager | 0.7.2-eksbuild.1 / 1.17.2-eksbuild.1 |
| Node Exporter / kube-state-metrics / External DNS | 1.9.1-eksbuild.2 / 2.15.0-eksbuild.4 / 0.19.0-eksbuild.1 |

```bash
check_account
: "${ADDON_NAME:?Select one add-on to review}"
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version 1.36 --output json > "$WORK_DIR/addon-catalog.json"
jq '[.addons[].addonVersions[] |
     {addonVersion,architecture,computeTypes,compatibilities}]' "$WORK_DIR/addon-catalog.json"
```

Revise la configuración híbrida/SO/kernel de la versión elegida. VPC CNI no administra los nodos híbridos; configure un CNI compatible y la ubicación de los agentes exclusivos de la nube. La presencia en el catálogo no demuestra que se haya instalado ni que esté listo.

## Referencias

- [Requisitos previos para nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [Sistemas operativos y mínimo de nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [Referencia de nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Redes de nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Credenciales y rol IAM de Nodos híbridos](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Credenciales del host durante desconexiones](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [CreateSession de IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [Complementos híbridos compatibles](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [Configuración híbrida de eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/hybrid-nodes.html)
- [nodeadm v1.0.20 publicado](https://github.com/aws/eks-hybrid/releases/tag/v1.0.20)
- [Origen de Packer fijado](https://github.com/aws/eks-hybrid/tree/v1.0.20/example/packer)
- [Plantilla de CloudFormation de SSM fijada](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ssm-cfn.yaml)
- [Plantilla de CloudFormation de Roles Anywhere fijada](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ira-cfn.yaml)
- [Compatibilidad de NVIDIA CUDA](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [Instalación de NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)


< [Tabla de contenidos](./README.md) | [Siguiente: Configuración de red](02-network-configuration.md) >
