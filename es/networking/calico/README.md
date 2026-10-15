# Análisis profundo de Calico: redes y políticas de Kubernetes

> **Referencia de ejemplo**: Calico Open Source 3.32.2
>
> **Última revisión**: October 12, 2026
>
> **Última versión**: Calico 3.33.0, publicada el 1 de octubre, es la versión más reciente de Open Source y se prueba con Kubernetes 1.35–1.37.
>
> Los comandos de esta serie permanecen fijados en 3.32.2, cuyo rango probado es 1.34–1.36. Estos ejemplos no se han validado con 3.33.0. Revise las [notas de la versión 3.33.0](https://github.com/projectcalico/calico/releases/tag/v3.33.0) y los [requisitos actuales](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements) antes de elegir una versión. Esta no es una garantía de compatibilidad abierta de `3.29+ / Kubernetes 1.28+`.

## Descripción general

Calico proporciona redes y políticas de red para Kubernetes, con capacidades adicionales para hosts y VM que dependen de la implementación y de la edición del producto. Esta serie cubre arquitectura, encapsulación y enrutamiento, BGP, políticas, eBPF, integración con EKS y operaciones. Elija una configuración mediante los [requisitos actuales](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements), no mediante una clasificación sin fecha de madurez o uso de recursos.

### Julio de 2026: Calico para VM en Kubernetes

El [anuncio oficial](https://www.tigera.io/news/tigera-launches-ebpf-powered-calico-for-vms-on-kubernetes-vm-migration-that-doesnt-require-rebuilding-the-network/) de Tigera tiene fecha de **23 de julio de 2026**. Describe redes de VM/contenedores, continuidad de IP, extensión de puente L2, políticas y observabilidad para migraciones de VMware. Este es un anuncio de producto, no una promesa de que cada capacidad anunciada esté incluida en Calico Open Source. Verifique la edición, topología y estado de la característica exactos: las [notas de la versión Enterprise 3.23](https://docs.tigera.io/calico-enterprise/latest/release-notes/) aún marcan la migración en vivo de KubeVirt como vista previa técnica. La disponibilidad comercial no elimina esa limitación específica de la característica.

## Compatibilidad y límites de características

- Calico 3.32.2 se publicó el 30 de agosto de 2026 y se prueba con Kubernetes 1.34–1.36. La versión más reciente 3.33.0 se prueba con Kubernetes 1.35–1.37; la disponibilidad de Kubernetes 1.37 por sí sola no establece compatibilidad para los ejemplos fijados en 3.32.2.
- El requisito general de Linux es kernel 5.10 o posterior con los módulos requeridos. Consulte la guía de eBPF para conocer arquitecturas compatibles, backports de proveedores y requisitos superiores para características individuales.
- Los planos de datos de Linux incluyen iptables, nftables y eBPF. Los valores predeterminados dependen del instalador/plataforma; las instalaciones actuales del operador kubeadm autogestionado pueden usar eBPF de forma predeterminada. No existe una garantía general de paridad de características.
- [Calico para Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations) admite configuraciones específicas de IPv4 VXLAN y BGP, pero no eBPF de Linux, IPIP, IPv6/dual stack, WireGuard ni todas las características de políticas de Linux.
- Open Source incluye políticas por niveles, agregación de flujos Goldmane y la interfaz de usuario Whisker. Las políticas DNS/FQDN, las políticas de capa de aplicación y otras capacidades avanzadas tienen límites de edición en la [comparación de productos](https://docs.tigera.io/calico/latest/about/calico-product-editions).

## Calico y Cilium

| Requisito | Calico | Cilium |
|---|---|---|
| Plano de datos de Linux | iptables / nftables / eBPF, según la configuración | eBPF, con Envoy para funciones L7 aplicables |
| Kubernetes NetworkPolicy | Compatible, además de políticas y niveles de Calico | Compatible, además de políticas de Cilium |
| Política L7 / DNS | Compruebe las licencias Enterprise/Cloud y el estado de las características | Política HTTP y DNS disponible; se aplican límites específicos del protocolo |
| BGP | Enrutamiento basado en BIRD en el modo de red aplicable | Anuncio del plano de control BGP; evalúe las rutas y la topología requeridas |
| Observabilidad | Goldmane/Whisker y métricas de Open Source; las características de pago añaden capacidades | Hubble y métricas |
| Windows | Configuraciones compatibles con limitaciones significativas | Los agentes Cilium 1.20 requieren Linux; no es un plano de datos beta para Windows |
| Reemplazo de kube-proxy | Disponible con el plano de datos eBPF | Disponible cuando se configura |
| Multiclúster / mesh | Características e integraciones separadas; dependiente de la edición | Cluster Mesh y características opcionales de service mesh; no todas se habilitan mediante la instalación |

Ambos pueden ser opciones de producción. El uso de recursos y la complejidad operativa dependen de las reglas, el tráfico, la plataforma y el ajuste. Valide las características requeridas en el entorno objetivo. No instale dos CNI principales en un clúster simplemente porque funcionan en entornos separados. Los [requisitos versionados](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst) de Cilium y la [guía de service mesh de Cilium](../../service-mesh/cilium-service-mesh/README.md) de este sitio describen sus límites de plataforma y mesh.

## Arquitectura

![Implementación esquemática de Calico BGP con datastore de Kubernetes, Typha opcional, Felix, confd y BIRD.](../../.gitbook/assets/en-networking-calico-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-readme-0.html)

La figura es una implementación esquemática de BGP, no una disposición obligatoria de componentes. El ejemplo de solo políticas de EKS siguiente usa el datastore de Kubernetes y omite BIRD/confd. “Plano de control” describe un rol lógico, no la ubicación en máquinas de plano de control administrado de EKS. Typha es un Deployment independiente en lugar de un proceso por nodo.

| Componente | Rol y alcance |
|---|---|
| Felix | Programa políticas y rutas aplicables en nodos de cargas de trabajo |
| BIRD / confd | BGP y su configuración cuando ese backend está habilitado; ausente en modo de solo políticas |
| Typha | Caché/distribución opcional de actualizaciones del datastore; el operador escala las réplicas con la instalación, no necesariamente a tres |
| kube-controllers | Conciliación, sincronización y limpieza de recursos de Kubernetes |
| Calico CNI / IPAM | Gestión de interfaces y direcciones de Pod cuando Calico posee las redes; Amazon VPC CNI/IPAM conserva estos roles en el ejemplo de EKS |
| Calico API server | API agregada `projectcalico.org/v3` sobre CRD internos en el modelo predeterminado; los CRD v3 nativos son una vista previa técnica independiente |

Use la [referencia de arquitectura](https://docs.tigera.io/calico/latest/reference/architecture/overview) y las cargas de trabajo renderizadas reales para identificar los componentes habilitados. Esta guía usa el datastore de la API de Kubernetes; un diseño respaldado por etcd tiene restricciones de instalación y características independientes.

## Modos de red y MTU

| Modo | Encapsulación y enrutamiento | MTU de Pod de ejemplo con un underlay IPv4 de 1500 bytes |
|---|---|---|
| IPIP | IPv4 en IPv4, normalmente con distribución de rutas BGP | 1480 |
| VXLAN | UDP 4789 de forma predeterminada; el enrutamiento de Pod VXLAN no requiere BGP | 1450 |
| Sin encapsular | El underlay debe enrutar direcciones de Pod; BGP es una forma de distribuir rutas | 1500 |
| CrossSubnet | Una configuración de IPIP o VXLAN que encapsula solo entre subredes de nodos | Aún reserve la sobrecarga de túnel requerida para las rutas que la necesiten |

Estos MTU son ejemplos, no constantes universales. La sobrecarga de IPv6 VXLAN, los underlay jumbo, WireGuard y los límites de rutas de nube cambian el cálculo. IPIP solo admite IPv4, y IPv4 VXLAN también se puede usar cuando IPIP no es adecuado. Compruebe la [configuración de MTU](https://docs.tigera.io/calico/latest/networking/configuring/mtu) y los [requisitos de overlay](https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip). La disponibilidad de BGP por sí sola no demuestra que cada salto del underlay pueda enrutar CIDR de Pod; la adyacencia en la misma L2 no es un requisito previo universal para una estructura enrutada sin encapsular. Planifique el underlay, los puertos, la familia de direcciones y la plataforma antes de seleccionar un modo.

## EKS: conservar Amazon VPC CNI y añadir la política de Calico

Este ejemplo es para nodos EC2 de Linux con una instalación existente y compatible de Amazon VPC CNI. No reemplaza las redes de Pod. No es una receta de instalación para Auto Mode ni Fargate. La [guía oficial de EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks) requiere:

1. Deshabilite la aplicación nativa de políticas de red de Amazon VPC CNI antes de seleccionar Calico como motor de políticas; ejecutar ambos provoca conflictos. Para un clúster protegido existente, planifique y valide la transferencia de políticas en lugar de crear una transición sin protección.
2. Configure VPC CNI `ANNOTATE_POD_IP=true` y conceda a su ServiceAccount `aws-node` acceso `patch` a Pods. Administre estos ajustes mediante el propietario de la configuración/complemento instalado para que la conciliación no los revierta. Compruebe el nombre real de ServiceAccount antes de aplicar el ejemplo de RBAC aditivo siguiente.
3. No afirme cobertura para Pods IPv6 con `ENABLE_V4_EGRESS=true`: la guía de Calico para EKS excluye explícitamente la aplicación para esa combinación.
4. Elija **un** método de instalación a continuación. Estos son ejemplos de instalación nueva, no comandos para asumir un operador existente ni migrar un CNI activo.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-ip-patch
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-ip-patch
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-ip-patch
subjects:
  - kind: ServiceAccount
    name: aws-node
    namespace: kube-system
```

### Método A: manifiestos de operador fijados

```bash
set -euo pipefail
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
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
```

### Método B: instalación de Helm fijada

Complete los mismos requisitos previos de VPC CNI. Calico 3.32 separa la instalación de CRD del chart de operador; instalar solo el pequeño chart de operador es insuficiente para un clúster nuevo. Guarde estos valores como `calico-eks-values.yaml`:

```yaml
installation:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
apiServer:
  enabled: true
```

```bash
set -euo pipefail
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico-crds projectcalico/crd.projectcalico.org.v1 --version v3.32.2   | kubectl apply --server-side -f -
helm install calico projectcalico/tigera-operator --version v3.32.2   --namespace tigera-operator --create-namespace -f calico-eks-values.yaml
```

El chart fijado también habilita Goldmane y Whisker de forma predeterminada. Revise esos componentes y los controles de acceso en los manifiestos renderizados. Los CRD `projectcalico.org/v3` nativos son una vista previa técnica independiente; los ejemplos aquí usan los CRD internos convencionales más el API server agregado.

### Verificar y luego probar el comportamiento de políticas

```bash
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl get felixconfigurations.projectcalico.org
```

Inspeccione el estado degradado/en progreso y pruebe los flujos permitidos y denegados mediante cargas de trabajo desechables antes de confiar en la aplicación. Un DaemonSet Ready no es una prueba de políticas. En el modo AmazonVPC de solo políticas, IPPools de Calico vacíos o sesiones BIRD ausentes no son necesariamente fallos: AWS aún proporciona IPAM y redes de Pod.

### Redes completas de Calico y otros métodos de instalación

Las redes completas de Calico en EKS son un diseño independiente para un clúster nuevo. El procedimiento oficial comienza sin nodos de cargas de trabajo y cambia el CNI antes de añadirlos; no aplique un fragmento `cni.type: Calico` sobre un clúster VPC CNI en ejecución. Consulte la [integración de EKS](08-eks-integration.md) y el procedimiento oficial de EKS. Para clústeres autogestionados sin un CNI existente, use la [guía on-premises](https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises). Los manifiestos directos siguen siendo una alternativa, pero su espacio de nombres, configuración de Typha y ciclo de vida difieren de las instalaciones mediante operador. Elija un propietario en vez de superponer instalaciones de Helm, operador y `calico.yaml`.

## Ejemplos de políticas con alcance explícito

Use un espacio de nombres dedicado `calico-demo`. Los siguientes ejemplos de ingreso y salida seleccionan solo ese espacio de nombres; no son una implementación de confianza cero para todo el clúster. Los niveles de Calico y las políticas anteriores existentes aún pueden cambiar el resultado.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: calico-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

El `podSelector` de pares significa Pods frontend en el **mismo espacio de nombres**. No autentica usuarios, permite todo el tráfico del mismo espacio de nombres ni establece una política de salida. El siguiente ejemplo independiente restringe la salida del espacio de nombres de demostración a Pods CoreDNS seleccionados en UDP/TCP 53 y deniega cualquier otra salida:

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-dns-only
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: all()
  order: 100
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Deny
```

Confirme primero los endpoints y las etiquetas DNS reales. Este ejemplo basado en selectores se dirige a Pods CoreDNS normales; no es una política para un resolvedor de sistema NodeLocal DNSCache o Auto Mode. El puerto 53 por sí solo no identifica un servidor DNS autorizado. Si también necesita salida de aplicaciones, diseñe y pruebe esas asignaciones explícitas antes de habilitar la denegación final. Una asignación posterior independiente no puede anular un Deny de Calico anterior coincidente.

### La política FQDN es específica de la edición

El campo `destination.domains` usado en las políticas DNS de Calico Enterprise/Cloud **no está en el esquema NetworkPolicy de Open Source 3.32.2**. No lo aplique a esta instalación de Open Source. Para una implementación con derecho a uso, use la [guía de políticas basadas en dominios](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy), configure servidores DNS confiables y permita la ruta DNS. Restrinja los dominios deliberadamente: `*.amazonaws.com` sería una asignación amplia, no autorización para una cuenta o servicio de AWS. La autorización de DNS a IP no equivale a validar la identidad HTTP Host o TLS.

## Monitorización y estado de salud

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
```

Las métricas están deshabilitadas de forma predeterminada en Felix. Habilitar este listener no crea un trabajo de scraping de Prometheus ni lo hace seguro públicamente; configure el descubrimiento privado y los controles de acceso mediante la [guía de métricas](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics). `flowLogsFileEnabled` no es un campo FelixConfiguration de Open Source. Use la [ruta de logs de flujo Goldmane/Whisker](https://docs.tigera.io/calico/latest/observability/view-flow-logs) compatible en lugar de copiar ajustes de logs de archivos de Enterprise.

| Métrica | Significado |
|---|---|
| `felix_active_local_endpoints` | Endpoints activos de cargas de trabajo y hosts locales |
| `felix_active_local_policies` | Políticas activas para endpoints en este nodo |
| `felix_iptables_rules` | Reglas iptables activas; específicas del plano de datos |
| `felix_int_dataplane_failures` | Actualizaciones fallidas del plano de datos que se reintentarán |
| `felix_cluster_num_hosts` | Recuento de hosts de todo el clúster de Felix; no lo sume en cada instancia de Felix |
| `typha_connections_accepted` | Conexiones aceptadas acumuladas, no el recuento de conexiones actual |
| `typha_connections_active` | Conexiones de clientes abiertas actualmente |

Consulte las referencias de métricas de [Felix](https://docs.tigera.io/calico/latest/reference/felix/prometheus) y [Typha](https://docs.tigera.io/calico/latest/reference/typha/prometheus). Son métricas de estado/configuración de componentes, no un contador universal de paquetes denegados. El estado de salud de Felix usa localhost:9099 de forma predeterminada; el estado de salud de Typha suele usar 9098 cuando está habilitado. Lea los probes implementados antes de verificarlos: `curl localhost` en su portátil no inspecciona el servidor de estado de salud de un nodo.

## Resolución de problemas

```bash
kubectl -n calico-system get pods -o wide
kubectl -n calico-system logs -l k8s-app=calico-node -c calico-node --tail=100
kubectl get installations.operator.tigera.io default -o yaml
kubectl get networkpolicies.networking.k8s.io -A
kubectl get networkpolicies.projectcalico.org -A
kubectl get globalnetworkpolicies.projectcalico.org
kubectl get ippools.projectcalico.org -o wide
```

Las instalaciones mediante operador usan normalmente `calico-system`; los manifiestos directos pueden usar `kube-system`. Use nombres de recursos de API totalmente calificados para distinguir las NetworkPolicies de Kubernetes y Calico. `kubectl get nodes ...status.conditions` no es un comando de estado de enrutamiento de Calico. Los comandos de estado de BIRD solo se aplican cuando BGP está habilitado, y `calicoctl node status` necesita el entorno de nodo de Calico adecuado en lugar del portátil de un administrador arbitrario.

| Síntoma | Investigue antes de cambiar la configuración |
|---|---|
| Pod no tiene IP | Identifique primero el propietario de IPAM: logs/capacidad de VPC CNI en EKS de solo políticas, IPAM de Calico en caso contrario |
| Fallo entre nodos | Rutas, permisos de underlay/firewall, MTU y la encapsulación elegida; habilitar un túnel a ciegas puede empeorar la interrupción |
| Discordancia de políticas | Etiquetas de endpoint, espacios de nombres, dirección, niveles/orden, políticas existentes y plano de datos real |
| CPU alta | Escala de tráfico/reglas y evidencia de métricas/perfil; una migración a eBPF es un cambio planificado, no una solución genérica inmediata |

Use un [calicoctl](https://docs.tigera.io/calico/latest/reference/calicoctl/) de versión coincidente solo cuando sea necesario, seleccionando el sistema operativo/arquitectura de CPU real y verificando el artefacto de la versión. Nunca infiera un fallo de solo políticas únicamente a partir de BGP ausente o el estado de IPAM de Calico.

## Contenido del análisis profundo

| Parte | Tema |
|---|---|
| [1](01-introduction.md) | Introducción, historia del proyecto y configuración del laboratorio |
| [2](02-architecture.md) | Componentes, datastore y flujo de paquetes |
| [3](03-networking-modes.md) | Encapsulación, enrutamiento directo y MTU |
| [4](04-bgp-deep-dive.md) | BGP, route reflectors e integración externa |
| [5](05-network-policy.md) | NetworkPolicy, niveles y diseño de políticas |
| [6](06-ebpf-dataplane.md) | Configuración de eBPF, limitaciones y resolución de problemas |
| [7](07-advanced-topics.md) | Temas avanzados de redes/seguridad |
| [8](08-eks-integration.md) | Integración de EKS y VPC CNI |
| [9](09-operations.md) | Operaciones y diagnósticos |
| [Glosario](glossary.md) | Terminología |

[Cuestionario de introducción a Calico](../../quizzes/networking/calico/01-introduction-quiz.md) · [Documentación oficial](https://docs.tigera.io/calico/latest/about/) · [Última versión 3.33.0](https://github.com/projectcalico/calico/releases/tag/v3.33.0) · [Referencia de ejemplo 3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2)