# Parte 1: Introducción a Calico

> **Base de revisión**: Calico Open Source 3.32.2, kind 0.33.0, Kubernetes 1.36.4
> **Última actualización**: 12 de septiembre de 2026. Calico 3.32 se prueba con Kubernetes 1.34–1.36.

## Entorno de laboratorio

Este laboratorio local desechable selecciona explícitamente iptables, VXLAN y Calico IPAM. No sustituye un CNI existente ni configura EKS. La auditoría comprobó artefactos publicados y configuración sin crear el clúster ni probar tráfico real.

| Herramienta/entorno | Requisito |
|---|---|
| kind | 0.33.0; fije la imagen 1.36.4 siguiente en vez de aceptar un valor predeterminado sin fijar |
| Docker | Runtime compatible y funcional con capacidad para tres nodos kind |
| SO de nodos | Kernel/módulos Linux que cumplan los [requisitos de Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements); en macOS es el kernel de la VM de contenedores |
| kubectl | Como máximo una versión menor de diferencia respecto al servidor API 1.36; resulta práctico un cliente 1.36 |
| calicoctl | Cliente opcional 3.32.2 compatible con el SO/arquitectura reales del host CLI |
| curl / Python 3 | Descarga opcional del cliente y verificación SHA-256 descritas abajo |
| Helm | Alternativa opcional en la [descripción general](README.md); no se necesita en este laboratorio |

La [política de diferencia de versiones de Kubernetes](https://kubernetes.io/releases/version-skew-policy/) no admite cualquier `kubectl 1.28+` con todos los servidores posteriores. Compruebe los CIDR de Pods/Services frente a la red de contenedores, LAN del host y VPN antes de crear el laboratorio.

### Opcional: un calicoctl compatible

Elija una plataforma, verifique el digest publicado del artefacto exacto y conserve el binario en el directorio del laboratorio. Estos comandos no requieren instalación global ni configuración en el directorio personal.

```bash
set -euo pipefail
CALICO_VERSION=v3.32.2
case "$(uname -s)" in
  Linux) CALICO_OS=linux ;;
  Darwin) CALICO_OS=darwin ;;
  *) echo "Select a supported calicoctl OS" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) CALICO_ARCH=amd64 ;;
  aarch64|arm64) CALICO_ARCH=arm64 ;;
  *) echo "Select a supported calicoctl architecture" >&2; exit 1 ;;
esac
CALICO_ASSET="calicoctl-$CALICO_OS-$CALICO_ARCH"
curl --fail --location --retry 3 \
  "https://api.github.com/repos/projectcalico/calico/releases/tags/$CALICO_VERSION" \
  --output calico-release.json
curl --fail --location --retry 3 \
  "https://github.com/projectcalico/calico/releases/download/$CALICO_VERSION/$CALICO_ASSET" \
  --output calicoctl
python3 - "$CALICO_ASSET" <<'PY'
import hashlib
import json
import pathlib
import sys

release = json.loads(pathlib.Path("calico-release.json").read_text())
if release["tag_name"] != "v3.32.2":
    raise SystemExit("Unexpected release")
asset = next(a for a in release["assets"] if a["name"] == sys.argv[1])
expected = asset.get("digest") or ""
actual = "sha256:" + hashlib.sha256(pathlib.Path("calicoctl").read_bytes()).hexdigest()
if not expected.startswith("sha256:") or actual != expected:
    raise SystemExit("Digest mismatch or missing published digest")
print("Verified", asset["name"], actual)
PY
chmod +x calicoctl
./calicoctl --help
```

Ejecute `./calicoctl version` después de configurar el datastore del laboratorio para ver información del cliente y clúster. El comando documentado `version` no tiene opción `--client`. Cuando el servidor API agregado esté listo, `kubectl` también puede gestionar recursos Calico; calicoctl no es obligatorio para todas las operaciones.

### Crear un clúster kind separado

Use un nombre de clúster libre y un kubeconfig local nuevo. La [versión kind 0.33.0](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0) publica esta imagen 1.36.4 dentro del intervalo menor probado por Calico. Se comprobaron el digest del registro y el manifiesto amd64/arm64; no se descargaron capas de la imagen de nodo durante la auditoría.

```bash
set -euo pipefail
CALICO_LAB_KUBECONFIG="$PWD/calico-lab.kubeconfig"
test ! -e "$CALICO_LAB_KUBECONFIG"
cat > kind-calico.yaml <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  disableDefaultCNI: true
  kubeProxyMode: iptables
  podSubnet: 10.244.0.0/16
nodes:
  - role: control-plane
  - role: worker
  - role: worker
YAML
kind create cluster --name calico-lab --config kind-calico.yaml \
  --kubeconfig "$CALICO_LAB_KUBECONFIG" \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed
export KUBECONFIG="$CALICO_LAB_KUBECONFIG"
export DATASTORE_TYPE=kubernetes
kubectl config current-context
kubectl cluster-info
```

Los nodos y Pods ordinarios pueden permanecer no preparados hasta instalar el CNI. No instale un segundo CNI para eliminar esa condición. Si el CIDR de Pods entra en conflicto, cámbielo tanto en kind como en Installation antes de crear el clúster.

```bash
CALICO_VERSION=v3.32.2
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/v1_crd_projectcalico_org.yaml"
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml"
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=300s
kubectl apply -f - <<'YAML'
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: Kind
  cni:
    type: Calico
  calicoNetwork:
    linuxDataplane: Iptables
    bgp: Disabled
    ipPools:
      - cidr: 10.244.0.0/16
        blockSize: 26
        encapsulation: VXLAN
        natOutgoing: Enabled
        nodeSelector: all()
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
```

Espere a que aparezcan las cargas creadas por el operador y compruebe sus rollouts y condiciones. Una selección de etiquetas vacía o la disponibilidad de un controlador no demuestran que funcione toda la red de nodos.

```bash
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl -n calico-system rollout status deployment/calico-kube-controllers --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl wait --for=condition=Ready nodes --all --timeout=300s
kubectl get ippools.projectcalico.org -o wide
kubectl get installations.operator.tigera.io default -o yaml
# Optional, if the matching local client was downloaded:
./calicoctl version
./calicoctl get nodes
```

Aquí BGP está desactivado, por lo que las sesiones BIRD y `calicoctl node status` no son criterios de readiness. Ese comando también necesita el entorno de nodo apropiado, no solo un kubeconfig de portátil. Observe los números reales de componentes; las réplicas CSI/Typha no son fijas. Use cargas desechables para comprobar conectividad de Pods, Services y DNS, así como flujos permitidos y rechazados por las políticas.

## Qué proporciona Calico

Calico combina redes Kubernetes, IPAM y aplicación de políticas. En integraciones de solo políticas, otro CNI conserva redes e IPAM. Las funciones varían por sistema operativo, plano de datos y edición; que una plataforma figure en una lista no promete comportamiento idéntico.

## Historia y gobernanza del proyecto

Project Calico comenzó en Metaswitch en 2014; Tigera se fundó en 2016 y es su principal mantenedor. Los registros siguientes corrigen las fechas anteriores de 3.0/3.29 y distinguen la vista previa eBPF original de la disponibilidad posterior de funciones.

| Fecha | Registro primario de la versión |
|---|---|
| 21 de diciembre de 2017 | [Calico 3.0.0](https://github.com/projectcalico/calico/releases/tag/v3.0.0), versión histórica, no recomendación de instalación |
| 25 de febrero de 2020 | [Introducción de eBPF](https://www.tigera.io/blog/introducing-the-calico-ebpf-dataplane/): anunciada como **vista previa técnica de 3.13**, no GA |
| 29 de octubre de 2024 | [Calico 3.29.0](https://github.com/projectcalico/calico/releases/tag/v3.29.0) |
| 30 de agosto de 2026 | [Calico 3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2), base de esta revisión |

Las afirmaciones anteriores de «paridad eBPF completa» y «eBPF en Windows» eran incorrectas. Las [limitaciones actuales de Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations) siguen excluyendo eBPF de Linux, IPIP, IPv6/doble pila y WireGuard.

Calico usa licencia Apache-2.0 y es mantenido por Tigera y la comunidad. Figurar en CNCF Landscape no implica propiedad de CNCF, incubación ni graduación. Enterprise es un producto comercial autogestionado; Cloud es una oferta SaaS. Open Source no está limitado a clústeres pequeños o no productivos.

![Relaciones entre el ecosistema Calico y los productos comerciales.](../../.gitbook/assets/en-networking-calico-01-introduction-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-01-introduction-4.html)

El recuadro CNCF solo representa participación en Landscape/ecosistema. Tigera mantiene tanto el proyecto abierto como sus productos; la agrupación de la figura no concede autoridad de gobernanza a CNCF.

## Capacidades principales

### 1. Redes y planos de datos

Encapsulación e implementación son elecciones separadas. Calico puede usar IPIP, VXLAN o una red subyacente enrutada. CrossSubnet es un ajuste condicional IPIP/VXLAN, no un servicio WAN. Los planos Linux incluyen iptables, nftables y eBPF. eBPF se ejecuta **dentro del kernel** y puede evitar partes de su ruta convencional de procesamiento de paquetes; no evita el kernel. El enrutamiento sin encapsulación omite cabeceras de túnel solo cuando la red subyacente dispone de las rutas Pod necesarias, sin garantizar la latencia mínima para toda carga.

### 2. Políticas Kubernetes y Calico

Kubernetes NetworkPolicy tiene ámbito de namespace y es aditiva. Calico añade acciones explícitas, políticas ordenadas y niveles, también en Open Source. GlobalNetworkPolicy tiene ámbito de recurso de clúster, pero puede seleccionar un namespace. HostEndpoint describe un endpoint de host que se protege; no es un tercer tipo de política debajo de NetworkPolicy en una jerarquía fija.

Estos son **ejemplos independientes** en un namespace dedicado. Considere los niveles existentes y las políticas prioritarias; ninguno es una base de seguridad completa.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: calico-demo
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress: []
```

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-trusted-ingress
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'backend'
  order: 100
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
        selector: trusted == 'true'
      destination:
        ports: [8080]
    - action: Deny
```

El ejemplo Calico permite TCP 8080 hacia backends seleccionados desde endpoints coincidentes del namespace de demostración, y luego rechaza el resto de entrada. Proteja los permisos de escritura de etiquetas: `trusted` no es una identidad criptográfica. Los ejemplos no configuran salida ni DNS. Se admiten reglas CIDR/puerto, pero un CIDR privado amplio no es un límite de identidad. Las políticas DNS/FQDN y de aplicación requieren funciones Enterprise/Cloud adecuadas; consulte la [matriz de ediciones](https://docs.tigera.io/calico/latest/about/calico-product-editions).

### 3. Gestión de direcciones IP

Cuando Calico gestiona IPAM, los pools y bloques controlan la asignación. Un bloque IPv4 /26 contiene 64 direcciones, no 64 direcciones Pod utilizables garantizadas en toda plataforma; Windows reserva direcciones e IPv6 tiene otros valores predeterminados. En modo VPC CNI de solo políticas, AWS gestiona IPAM.

Esto ilustra la [API IPPool](https://docs.tigera.io/calico/latest/reference/resources/ippool). **No lo cree junto a un pool gestionado por el operador que se solape.** El laboratorio kind ya tiene su pool; cambiar encapsulación/IPAM es un ejercicio independiente que debe planificarse.

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: example-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
```

Varios pools no solapados y selectores de nodos pueden separar asignaciones. `natOutgoing` normalmente se aplica al tráfico que sale de los pools Calico; no es un ajuste de firewall ni cifrado. Ni el enrutamiento directo ni CrossSubnet conectan sedes distintas sin un diseño de red subyacente.

### 4. Enrutamiento BGP

BGP distribuye rutas; los paquetes de aplicación no atraviesan el proceso BIRD y BGP no los cifra. Puede soportar enrutamiento directo o coexistir con IPIP. La malla completa, los reflectores de rutas y los peers externos son elecciones de topología.

Lo siguiente pertenece a un **laboratorio enrutado separado**, no al ejemplo kind con BGP desactivado. Sustituya la dirección de documentación, los ASN y las etiquetas por una topología diseñada y configuración de router compatible. No desactive la malla de nodos antes de que funcione la distribución de rutas sustituta.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: example-rack-tor
spec:
  peerIP: 192.0.2.1
  asNumber: 64513
  nodeSelector: rack == 'rack-1'
```

BGPPeer admite `password.secretKeyRef` para autenticar sesiones. El Secret pertenece al namespace del componente de nodo Calico y el router debe usar credenciales coincidentes; esto no cifra el tráfico de la carga. El anuncio de CIDR de Service y la eliminación de la malla requieren más pruebas; consulte [BGP en profundidad](04-bgp-deep-dive.md).

### 5. Límites de plataforma y escala

| Entorno | Límite |
|---|---|
| EKS | VPC CNI + políticas Calico es una integración; Calico CNI completo es otro diseño de clúster nuevo |
| AKS | Revise la combinación CNI/políticas admitida por el proveedor y el procedimiento actual |
| GKE | Dataplane V2 usa **Cilium**; Calico se aplica a la configuración heredada pertinente, no se instala sobre V2 |
| Kubernetes autogestionado | Revise distribución, kernel, propiedad del CNI, rutas y privilegios |
| Windows | Configuraciones IPv4 concretas; sin paridad de eBPF Linux, IPIP, IPv6/doble pila o WireGuard |
| Hosts / VM | Requisitos de instalación y funciones separados; el estado KubeVirt/Enterprise difiere de la protección básica de hosts |

La [documentación de GKE](https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2) distingue explícitamente Cilium en V2 de la ruta Calico heredada.

Typha almacena y distribuye actualizaciones mediante un conjunto separado de Pods, reduciendo las observaciones directas del datastore por Felix. Tres réplicas son un ejemplo, no un mínimo universal. La capacidad depende de políticas, endpoints, cambios de Service, hardware, datastore y plano de datos. Esta introducción no aporta evidencia reproducible de un límite fijo de «5,000 nodos / 100,000 Pods / millones de reglas».

## Calico, kube-proxy y rendimiento

kube-proxy implementa reenvío de Service, no redes CNI ni NetworkPolicy. Los planos estándar de Calico pueden coexistir con él, como en este laboratorio; el plano eBPF puede sustituir la gestión de Service cuando se configura.

| Aspecto | Comparación |
|---|---|
| Redes Pod/IPAM | Implementaciones CNI/IPAM con la misma topología |
| Reenvío de Service | Backend kube-proxy elegido o sustituto eBPF |
| Políticas | Reglas y cobertura de aplicación equivalentes |
| Escala | Services/endpoints, selectores, cambios y reutilización de conexiones |
| CPU/memoria/latencia | Hardware, kernel, versiones, carga, calentamiento, repeticiones y errores |

kube-proxy no se limita a iptables: Kubernetes actual también ofrece nftables y backends heredados según versión. Una consulta IP-set no convierte toda la ruta de paquetes Calico en O(1). La selección NAT inicial de Service en iptables también difiere de la ruta rápida conntrack de paquetes posteriores. El antiguo ejemplo sin fuente de reglas, latencia y memoria para 1,000 nodos/50,000 Pods no era un benchmark reproducible y no debe usarse para dimensionar.

Las redes tradicionales de VM también pueden automatizarse y distribuirse. La política declarativa de Calico no implica capacidad IP ilimitada ni convergencia garantizada en segundos.

## Escenarios de despliegue

- **Local:** Coordine rutas Pod, peers/filtros BGP, rutas de retorno y protección de hosts. Desactivar encapsulación no crea rutas subyacentes.
- **EKS:** Para conservar redes AWS, seleccione `cni.type: AmazonVPC` y siga la [descripción general revisada](README.md), incluida la propiedad del motor de políticas y las anotaciones IP de Pod. No aplique una Installation EKS a este laboratorio Kind ni ejecute dos motores de políticas.
- **Híbrido/multiclúster:** Conectividad, descubrimiento y administración de políticas son funciones separadas. Un IPPool CrossSubnet no establece VPN, identidad compartida ni descubrimiento entre clústeres. Evalúe por separado las funciones adecuadas de cluster mesh/multiclúster y la red subyacente; «Calico Federation» no es un enlace integrado universal.
- **Cargas reguladas:** Enterprise/Cloud pueden añadir informes, registros y seguridad; instalarlos no establece cumplimiento. Los registros de auditoría API registran cambios API y los de flujo observaciones de red, no automáticamente toda decisión de política. WireGuard también está disponible en configuraciones Linux Open Source compatibles.

## Comunidad y desarrollo del código fuente

Use la [página de comunidad](https://www.tigera.io/project-calico/community/) para enlaces actuales de Slack/reuniones, el [seguimiento de incidencias](https://github.com/projectcalico/calico/issues) para informes reproducibles y la [guía de contribución](https://github.com/projectcalico/calico/blob/v3.32.2/CONTRIBUTING.md). No asuma que un calendario quincenal sin fecha o una URL antigua de foro siguen vigentes.

Para estudiar el código, la [guía de desarrollo](https://github.com/projectcalico/calico/blob/v3.32.2/DEVELOPER_GUIDE.md) describe un entorno Linux/Docker/git/make y pruebas por componente. No existe un objetivo raíz `make dev-environment`. Este flujo opcional es independiente del laboratorio de redes y no se ejecutó durante la auditoría:

```bash
git clone --depth 1 --branch v3.32.2 https://github.com/projectcalico/calico.git calico-source-study
cd calico-source-study
# Read prerequisites and the selected component's Makefile before running tests.
cat DEVELOPER_GUIDE.md
make -C calicoctl test
```

Open Source ofrece redes y políticas con soporte comunitario tanto para producción como para laboratorios. Enterprise añade capacidades/soporte comerciales; Cloud ofrece gestión SaaS. Elija según la [matriz de funciones](https://docs.tigera.io/calico/latest/about/calico-product-editions), no según una regla general de «clúster pequeño frente a grande».

## Limpiar el laboratorio desechable

Después de guardar los resultados, elimine únicamente el clúster `calico-lab` creado para el ejercicio con `kind delete cluster --name calico-lab`. Conserve clústeres y kubeconfigs no relacionados. Esta limpieza local no es un procedimiento de eliminación de EKS.

[Siguiente: Arquitectura de Calico](02-architecture.md) · [Descripción general de Calico](README.md) · [Cuestionario introductorio](../../quizzes/networking/calico/01-introduction-quiz.md)
