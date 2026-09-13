# Calico en profundidad: redes y políticas de Kubernetes

> **Base de revisión**: Calico Open Source 3.32.2 · **Última actualización**: 12 de septiembre de 2026
> Calico 3.32 se prueba con Kubernetes 1.34–1.36. No es una garantía de compatibilidad indefinida `3.29+ / Kubernetes 1.28+`.

## Descripción general

Calico proporciona redes y políticas de red para Kubernetes, además de capacidades para hosts y VM que dependen del despliegue y la edición. Esta serie cubre arquitectura, encapsulación/enrutamiento, BGP, políticas, eBPF, integración EKS y operaciones. Elija una configuración según los [requisitos actuales](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements), no una clasificación sin fecha de madurez o consumo.

### Julio de 2026: Calico para VM en Kubernetes

El [anuncio oficial de Tigera](https://www.tigera.io/news/tigera-launches-ebpf-powered-calico-for-vms-on-kubernetes-vm-migration-that-doesnt-require-rebuilding-the-network/) está fechado el **23 de julio de 2026**. Describe redes VM/contenedores, continuidad IP, extensión de puente L2, políticas y observabilidad para migraciones VMware. Es un anuncio de producto, no una promesa de que toda función anunciada esté en Calico Open Source. Revise edición, topología y estado exactos: las [notas Enterprise 3.23](https://docs.tigera.io/calico-enterprise/latest/release-notes/) aún marcan la migración en vivo KubeVirt como vista previa técnica. La disponibilidad comercial no elimina esa limitación específica.

## Compatibilidad y límites de funciones

- Calico 3.32.2 se publicó el 30 de agosto de 2026. Sus versiones menores Kubernetes probadas son 1.34, 1.35 y 1.36; que Kubernetes 1.37 esté disponible no demuestra compatibilidad.
- El requisito Linux general es kernel 5.10 o posterior con los módulos necesarios. Consulte la guía eBPF para arquitecturas, backports de proveedores y requisitos superiores de funciones concretas.
- Los planos Linux incluyen iptables, nftables y eBPF. Los valores predeterminados dependen del instalador/plataforma; las instalaciones actuales con operador kubeadm autogestionado pueden usar eBPF por defecto. No hay garantía general de paridad.
- [Calico para Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations) admite configuraciones IPv4 VXLAN y BGP específicas, pero no eBPF Linux, IPIP, IPv6/doble pila, WireGuard ni todas las políticas Linux.
- Open Source incluye políticas por niveles, agregación de flujos Goldmane y la interfaz Whisker. DNS/FQDN, políticas de aplicación y otras capacidades avanzadas tienen límites de edición en la [comparación de productos](https://docs.tigera.io/calico/latest/about/calico-product-editions).

## Calico y Cilium

| Requisito | Calico | Cilium |
|---|---|---|
| Plano de datos Linux | iptables / nftables / eBPF según configuración | eBPF, con Envoy para las funciones L7 pertinentes |
| Kubernetes NetworkPolicy | Compatible, más políticas y niveles Calico | Compatible, más políticas Cilium |
| Políticas L7 / DNS | Revise licencia Enterprise/Cloud y estado funcional | Políticas HTTP y DNS disponibles, con límites por protocolo |
| BGP | Enrutamiento BIRD en el modo correspondiente | Anuncios del plano de control BGP; evalúe rutas y topología requeridas |
| Observabilidad | Goldmane/Whisker y métricas Open Source; funciones de pago añaden capacidades | Hubble y métricas |
| Windows | Configuraciones admitidas con limitaciones importantes | Los agentes Cilium 1.20 requieren Linux; no es un plano Windows beta |
| Sustitución de kube-proxy | Disponible con eBPF | Disponible si se configura |
| Multiclúster / malla | Funciones e integraciones separadas, según edición | Cluster Mesh y funciones opcionales de malla; no todas se activan al instalar |

Ambos pueden ser opciones de producción. Consumo y complejidad dependen de reglas, tráfico, plataforma y ajustes. Valide las funciones necesarias en el entorno objetivo. No instale dos CNI primarios en un clúster solo porque funcionan por separado. Los [requisitos versionados de Cilium](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst) y la [guía de malla Cilium](../../service-mesh/cilium-service-mesh/README.md) describen sus límites de plataforma y malla.

## Arquitectura

![Despliegue esquemático BGP de Calico con datastore Kubernetes, Typha opcional, Felix, confd y BIRD.](../../.gitbook/assets/en-networking-calico-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-readme-0.html)

La figura esquematiza BGP, no una disposición obligatoria. El ejemplo EKS de solo políticas usa datastore Kubernetes y omite BIRD/confd. «Plano de control» describe un rol lógico, no ubicación en máquinas gestionadas del plano EKS. Typha es un Deployment separado, no un proceso por nodo.

| Componente | Rol y alcance |
|---|---|
| Felix | Programa políticas y rutas pertinentes en nodos de cargas |
| BIRD / confd | BGP y su configuración cuando se habilita ese backend; ausentes en modo solo políticas |
| Typha | Caché/distribución opcional de actualizaciones; el operador escala réplicas con la instalación, no necesariamente tres |
| kube-controllers | Reconciliación, sincronización y limpieza de recursos Kubernetes |
| Calico CNI / IPAM | Interfaces y direcciones Pod cuando Calico gestiona la red; Amazon VPC CNI/IPAM conserva esos roles en el ejemplo EKS |
| Servidor API Calico | API agregada `projectcalico.org/v3` sobre CRD internos en el modelo predeterminado; CRD nativos v3 son otra vista previa técnica |

Use la [referencia de arquitectura](https://docs.tigera.io/calico/latest/reference/architecture/overview) y las cargas renderizadas reales para identificar componentes habilitados. La guía usa datastore Kubernetes API; un diseño basado en etcd tiene otras restricciones de instalación y funciones.

## Modos de red y MTU

| Modo | Encapsulación y enrutamiento | MTU Pod de ejemplo con red IPv4 subyacente de 1500 bytes |
|---|---|---|
| IPIP | IPv4 dentro de IPv4, normalmente con distribución BGP | 1480 |
| VXLAN | UDP 4789 por defecto; el enrutamiento Pod VXLAN no requiere BGP | 1450 |
| Sin encapsular | La red subyacente debe enrutar direcciones Pod; BGP es una forma de distribuir rutas | 1500 |
| CrossSubnet | Ajuste IPIP o VXLAN que encapsula solo entre subredes de nodos | Reserve igualmente la sobrecarga de túnel de las rutas que lo necesitan |

Las MTU son ejemplos, no constantes universales. Sobrecarga VXLAN IPv6, redes jumbo, WireGuard y límites de nube cambian el cálculo. IPIP solo admite IPv4, y VXLAN IPv4 también es utilizable donde IPIP no conviene. Revise [configuración MTU](https://docs.tigera.io/calico/latest/networking/configuring/mtu) y [requisitos overlay](https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip). BGP disponible no demuestra que cada salto subyacente enrute CIDR Pod; la adyacencia en la misma L2 no es un requisito universal de una red enrutada sin encapsular. Planifique red subyacente, puertos, familia de direcciones y plataforma antes de elegir.

## EKS: conservar Amazon VPC CNI y añadir políticas Calico

Este ejemplo es para nodos Linux EC2 con Amazon VPC CNI existente y compatible. No sustituye la red Pod. No es una receta Auto Mode o Fargate. La [guía oficial EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks) exige:

1. Desactivar la aplicación nativa de políticas VPC CNI antes de elegir Calico; ejecutar ambos causa conflictos. En un clúster protegido existente, planifique y valide el relevo de políticas sin crear una transición desprotegida.
2. Establecer `ANNOTATE_POD_IP=true` en VPC CNI y conceder a su ServiceAccount `aws-node` acceso `patch` sobre Pods. Gestione los ajustes mediante el propietario del complemento/configuración para evitar que la reconciliación los revierta. Verifique el nombre real antes de aplicar el RBAC aditivo siguiente.
3. No afirmar cobertura para Pods IPv6 con `ENABLE_V4_EGRESS=true`: la guía Calico EKS excluye explícitamente esa combinación.
4. Elegir **un** método de instalación siguiente. Son ejemplos nuevos, no comandos para apropiarse de un operador existente ni migrar un CNI activo.

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

### Método A: manifiestos del operador fijados

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

### Método B: instalación Helm fijada

Complete los mismos requisitos VPC CNI. Calico 3.32 separa la instalación CRD del chart del operador; instalar solo el pequeño chart no basta en un clúster nuevo. Guarde estos valores como `calico-eks-values.yaml`:

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

El chart fijado también habilita Goldmane y Whisker por defecto. Revise esos componentes y sus accesos en los manifiestos renderizados. Los CRD nativos `projectcalico.org/v3` son una vista previa técnica aparte; aquí se usan CRD internos convencionales y servidor API agregado.

### Verificar y después probar las políticas

```bash
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl get felixconfigurations.projectcalico.org
```

Inspeccione estados degraded/progressing y pruebe flujos permitidos y denegados con cargas desechables antes de confiar en la aplicación de políticas. Un DaemonSet Ready no lo demuestra. En AmazonVPC de solo políticas, IPPools vacíos o ausencia de sesiones BIRD no son necesariamente fallos: AWS sigue proporcionando IPAM y redes Pod.

### Red Calico completa y otros métodos de instalación

La red Calico completa en EKS es otro diseño de clúster nuevo. El procedimiento oficial empieza sin nodos de carga y cambia el CNI antes de añadirlos; no aplique `cni.type: Calico` sobre un clúster VPC CNI en ejecución. Consulte [integración EKS](08-eks-integration.md) y el procedimiento oficial. Para clústeres autogestionados sin CNI, use la [guía local](https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises). Los manifiestos directos son otra alternativa, pero namespace, Typha y ciclo de vida difieren del operador. Elija un propietario, sin superponer Helm, operador y `calico.yaml`.

## Ejemplos de políticas con alcance explícito

Use el namespace dedicado `calico-demo`. Los ejemplos de entrada/salida solo lo seleccionan a él; no son un despliegue zero trust de todo el clúster. Los niveles y políticas Calico anteriores aún pueden cambiar el resultado.

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

El `podSelector` del peer significa Pods frontend del **mismo namespace**. No autentica usuarios, no permite todo el tráfico del namespace ni establece política de salida. El siguiente ejemplo independiente limita salida del namespace demo a Pods CoreDNS seleccionados por UDP/TCP 53 y rechaza el resto:

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

Confirme primero endpoints DNS y etiquetas reales. El ejemplo basado en selectores se dirige a Pods CoreDNS ordinarios; no es una política NodeLocal DNSCache ni del resolvedor del sistema Auto Mode. El puerto 53 no identifica por sí solo un DNS autorizado. Si necesita salida de aplicación, diseñe y pruebe permisos explícitos antes del rechazo final. Un permiso posterior separado no puede anular un Calico Deny anterior coincidente.

### Las políticas FQDN dependen de la edición

El campo `destination.domains` de las políticas DNS Enterprise/Cloud **no está en el esquema NetworkPolicy de Open Source 3.32.2**. No lo aplique a esta instalación Open Source. Con una edición autorizada, use la [guía de políticas por dominio](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy), configure DNS de confianza y permita su ruta. Restrinja dominios deliberadamente: `*.amazonaws.com` sería amplio, no autorización para una cuenta o servicio AWS. La autorización DNS a IP no equivale a validar HTTP Host o identidad TLS.

## Monitorización y estado

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
```

Felix desactiva métricas por defecto. Habilitar el listener no crea un job Prometheus ni lo hace seguro públicamente; configure descubrimiento privado y controles según la [guía de métricas](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics). `flowLogsFileEnabled` no es un campo FelixConfiguration Open Source. Use la [ruta de logs de flujo Goldmane/Whisker](https://docs.tigera.io/calico/latest/observability/view-flow-logs) admitida, sin copiar ajustes Enterprise de archivos.

| Métrica | Significado |
|---|---|
| `felix_active_local_endpoints` | Endpoints locales activos de cargas y hosts |
| `felix_active_local_policies` | Políticas activas para endpoints de este nodo |
| `felix_iptables_rules` | Reglas iptables activas; específicas del plano de datos |
| `felix_int_dataplane_failures` | Actualizaciones fallidas del plano de datos que se reintentarán |
| `felix_cluster_num_hosts` | Número de hosts del clúster visto por Felix; no lo sume entre todas las instancias |
| `typha_connections_accepted` | Conexiones aceptadas acumuladas, no conexiones actuales |
| `typha_connections_active` | Conexiones de clientes abiertas actualmente |

Consulte las referencias de [Felix](https://docs.tigera.io/calico/latest/reference/felix/prometheus) y [Typha](https://docs.tigera.io/calico/latest/reference/typha/prometheus). Son métricas de salud/configuración de componentes, no un contador universal de paquetes rechazados. Felix usa por defecto localhost:9099 para salud; Typha suele usar 9098 si está habilitado. Lea los probes desplegados: ejecutar `curl localhost` en su portátil no inspecciona el servidor de salud de un nodo.

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

Las instalaciones del operador suelen usar `calico-system`; los manifiestos directos pueden usar `kube-system`. Use nombres API completos para distinguir NetworkPolicies Kubernetes y Calico. `kubectl get nodes ...status.conditions` no es un comando de estado de rutas Calico. Los comandos BIRD solo aplican con BGP habilitado, y `calicoctl node status` necesita el entorno de nodo Calico adecuado, no cualquier portátil administrativo.

| Síntoma | Investigar antes de cambiar configuración |
|---|---|
| Pod sin IP | Identifique primero el propietario IPAM: logs/capacidad VPC CNI en EKS de solo políticas, Calico IPAM en los demás casos |
| Fallo entre nodos | Rutas, permisos subyacentes/firewall, MTU y encapsulación; habilitar un túnel a ciegas puede empeorar el incidente |
| Política no coincide | Etiquetas de endpoints, namespaces, dirección, niveles/orden, políticas existentes y plano real |
| CPU elevada | Escala de tráfico/reglas y evidencia de métricas/perfilado; migrar eBPF es un cambio planificado, no una solución genérica inmediata |

Use [calicoctl](https://docs.tigera.io/calico/latest/reference/calicoctl/) de versión compatible solo si hace falta, eligiendo SO/CPU reales y verificando el artefacto. Nunca deduzca un fallo de solo políticas únicamente por ausencia de BGP o estado IPAM Calico.

## Contenido en profundidad

| Parte | Tema |
|---|---|
| [1](01-introduction.md) | Introducción, historia y laboratorio |
| [2](02-architecture.md) | Componentes, datastore y flujo de paquetes |
| [3](03-networking-modes.md) | Encapsulación, rutas directas y MTU |
| [4](04-bgp-deep-dive.md) | BGP, reflectores e integración externa |
| [5](05-network-policy.md) | NetworkPolicy, niveles y diseño de políticas |
| [6](06-ebpf-dataplane.md) | Configuración eBPF, límites y diagnóstico |
| [7](07-advanced-topics.md) | Temas avanzados de redes/seguridad |
| [8](08-eks-integration.md) | Integración EKS y VPC CNI |
| [9](09-operations.md) | Operaciones y diagnóstico |
| [Glosario](glossary.md) | Terminología |

[Cuestionario introductorio de Calico](../../quizzes/networking/calico/01-introduction-quiz.md) · [Documentación oficial](https://docs.tigera.io/calico/latest/about/) · [Versión 3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2)
