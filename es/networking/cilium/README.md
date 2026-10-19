# Cilium en profundidad: el futuro de las redes cloud native

## Descripción general y versiones de referencia

Esta sección trata las redes, las políticas y la observabilidad de Cilium. Los ejemplos se revisaron con **Cilium y su chart de Helm 1.20.3**, Cilium CLI **0.20.1** y Hubble CLI **1.20.2**. La página de compatibilidad de Cilium 1.20 con Kubernetes incluye **1.33–1.36** entre las versiones probadas; la publicación de Kubernetes 1.37 no amplía automáticamente esa matriz. Los hosts compatibles son Linux AMD64/AArch64 con kernel **5.10+**, o el equivalente documentado de la distribución, como el kernel 4.18 con correcciones retroportadas de RHEL 8.10. Algunas funciones tienen requisitos adicionales.

> **Última actualización**: 16 de octubre de 2026

### Historial de versiones

Las fechas siguientes corresponden a la publicación en GitHub, en UTC. Describen esas versiones y no las versiones fijadas para la instalación actual. Las funciones retroportadas varían entre las distintas ramas.

| Fecha | Versión | Cambios verificados |
| --- | --- | --- |
| 14 de julio de 2026 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | Primer candidato de la versión 1.20 |
| 16 de julio de 2026 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | La configuración de registros de acceso del Gateway figura en 1.19.6/1.18.12; las correcciones de la política de reinicio y la afinidad de ClusterMesh citadas aquí figuran en 1.19.6, no en las tres versiones |
| 21 de julio de 2026 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | Segundo candidato de la versión 1.20 |
| 29 de julio de 2026 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | Versión estable; algunos cambios se describen más abajo |
| 3 de agosto de 2026 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | Versión preliminar del siguiente ciclo, fuera de las versiones de referencia de esta guía |
| 18 de agosto de 2026 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | Documentación de ClusterMesh y correcciones, incluido el tratamiento de reinicios y políticas CIDR |
| 18 de agosto de 2026 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | Correcciones de tiempos de interfaces ENI, Services/balanceadores y otros componentes |
| 18 de agosto de 2026 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | Soporte de VRRP/IGMP en el firewall del host y correcciones relacionadas |
| 9 de septiembre de 2026 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | Versión preliminar; su registro de cambios abarca de pre.0 a pre.2 porque **1.21.0-pre.1 nunca se publicó** |
| 16 de septiembre de 2026 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | Correcciones de asignación/liberación con delegación de prefijos en ENI IPAM y CIDR secundarios de VPC, ClusterMesh, revisión de políticas para Pods creados inmediatamente después de un cambio, una regresión de LocalRedirectPolicy y actualización de clusters creados con v1.15 o anterior (versión de CRD `CiliumNodeConfig v2alpha1`) |
| 16 de septiembre de 2026 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | Versiones de corrección de las ramas anteriores compatibles |
| 2 de octubre de 2026 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | Última versión preliminar de 1.21; **1.21 sigue siendo preliminar, sin versión estable**, y las funciones indicadas como 1.21 en esta guía pueden cambiar |
| 15 de octubre de 2026 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Dependencia de Gateway API v1.6.3, recolección de entradas de conntrack y tratamiento de CNP con `nodeSelector`, entre otras correcciones; versión de referencia actual de esta guía |

El 14 de septiembre de 2026, el blog de CNCF publicó un [resumen de las funciones de Cilium 1.20](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/) —Gateway API ExternalAuth, TCPRoute/UDPRoute, ENI IPAM para IPv6 y otras— que cubre las mismas funciones que el resumen del anuncio de 1.20.0 que aparece a continuación.

El anuncio de 1.20.0 menciona **más de 2.660 commits nuevos**, con el respaldo de una **comunidad de más de 1.100 colaboradores**. Esta segunda cifra describe el tamaño de la comunidad, no el número de autores de esa versión. Entre las novedades se incluyen:

- Gateway API **1.6.1**, TCPRoute/UDPRoute, BackendTLSPolicy, ListenerSets, ExternalAuth y CORS, sujetos a la configuración y madurez de cada función y API.
- Plugins del datapath y selección opcional mediante `bpf.datapathMode=auto`; el valor predeterminado anunciado sigue siendo veth. Los clusters de doble pila pueden configurar una dirección IPv6 para la puerta de enlace de salida.
- ENI IPAM para IPv6 en **beta** y migración de cluster-pool a multi-pool sin reconstruir el cluster. La migración in situ no garantiza la ausencia de interrupciones.
- Indicaciones de distribución del tráfico, backends Maglev ponderados e integración estable con MCS; soporte de Kubernetes ClusterNetworkPolicy e identidad de cargas de trabajo basada en ztunnel en **beta**.
- Una reducción anunciada del binario `cilium-cni` de aproximadamente **77 MB a 16 MB**. Las mejoras de ADS/Delta xDS pertenecen al anuncio de 1.20, por lo que no deben atribuirse a las notas de 1.18.13. Son resultados publicados por el proyecto, no mediciones repetidas durante esta revisión.

Consulte las [notas de actualización de 1.20](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes) para Mutual Authentication (**obsoleta en 1.20** y eliminada en la versión preliminar 1.21), las extensiones Go de Envoy eliminadas o reemplazadas, las políticas para Kafka, la antigua API CiliumNodeConfig, la integración libnetwork y los cambios en configuraciones CNI personalizadas.

### Aviso de seguridad de NetworkPolicy

El aviso del proyecto [GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) se publicó el **6 de julio de 2026**. La API del proyecto y la API global de avisos de GitHub muestran fechas distintas: esta última registra el 3 de septiembre. Para este historial, use la fecha de divulgación del proyecto; la fecha del registro global no corresponde a una corrección posterior. Afecta a **1.19.0–1.19.4** bajo las condiciones de nombre de cluster personalizado descritas en el aviso: un peer de una NetworkPolicy estándar de Kubernetes que contiene únicamente `ipBlock` puede permitir involuntariamente tráfico entrante de cargas del mismo namespace que el Pod seleccionado. **1.19.5** corrige este problema; para el despliegue, use una versión actual con las correcciones apropiadas. Según el aviso, este error concreto no afecta a CiliumNetworkPolicy/ClusterwideNetworkPolicy ni a versiones anteriores a 1.19.0.

## Introducción

Cilium ofrece redes, seguridad y observabilidad para los entornos Linux de Kubernetes compatibles. El enrutamiento, IPAM, el cifrado y el tratamiento de Services son decisiones independientes; elegir eBPF no habilita todas las funciones ni garantiza un rendimiento determinado. La antigua integración libnetwork de Docker se eliminó en 1.20, por lo que Docker y Mesos no deben presentarse como destinos de instalación actuales intercambiables.

### eBPF y funciones principales

El kernel verifica los programas eBPF antes de cargarlos y puede compilarlos mediante JIT para ejecutarlos en los puntos de conexión compatibles. Esto permite procesar paquetes y obtener observabilidad sin un módulo de kernel personalizado; el verificador no demuestra que la aplicación o las políticas sean correctas. El throughput, la latencia y la memoria reales dependen de los programas, la plataforma y la carga.

Cilium ofrece políticas L3/L4, políticas L7 mediante integración con Envoy y el proxy DNS, WireGuard/IPsec opcional, balanceo de Services, visibilidad de flujos con Hubble, ClusterMesh y anuncios BGP. La aceleración XDP es opcional y depende de los dispositivos y la configuración. Las funciones L7 pueden utilizar Envoy por nodo; la identidad de cargas mediante ztunnel requiere una configuración beta independiente. Instalar el agente no habilita por sí solo todas las funciones de malla de servicios, cifrado o comunicación entre clusters.

### Comparación con otros proyectos de redes

| Proyecto | Conectividad / IPAM | Políticas y funciones relacionadas |
| --- | --- | --- |
| Cilium | Enrutamiento nativo u overlay; modos IPAM que incluyen ENI de la nube | Dataplane eBPF, políticas de Cilium/Kubernetes, integración L7, Hubble y cifrado opcional |
| Calico | Perfiles nativos/IPIP/VXLAN con IPAM de Calico o externo | Iptables/Nftables/BPF en Linux y HNS en Windows compatible; WireGuard de código abierto, políticas por etapas e integración L7 independiente |
| Flannel | Conectividad de Pods mediante backends como VXLAN/host-gw/WireGuard | El demonio de enrutamiento no aplica NetworkPolicy; su chart puede desplegar el controlador de políticas de SIGs con `netpol.enabled`, o combinarse con otra implementación de políticas |
| AWS VPC CNI | Asignación de direcciones y redes con ENI de VPC | Políticas de red nativas en nodos EC2 Linux compatibles y función independiente de grupos de seguridad para Pods; EKS Auto Mode utiliza una implementación administrada distinta |

Un modo de enrutamiento y una implementación de procesamiento de paquetes pertenecen a categorías diferentes. Calico no se limita a iptables/IPVS, Flannel puede usar un backend cifrado y las políticas de AWS no equivalen a grupos de seguridad. Las mallas de servicios son capas opcionales, y la conectividad entre VPC de distintos clusters no se limita a Transit Gateway. Compare una carga medida y una matriz explícita de compatibilidad, en lugar de establecer clasificaciones universales de rendimiento.

## Arquitectura

El **servidor API de Kubernetes** almacena los recursos de Kubernetes y Cilium. Los agentes de Cilium observan el estado pertinente y programan el dataplane de cada nodo; Cilium Operator gestiona responsabilidades del cluster, como la asignación según el modo IPAM y el trabajo de identidades y controladores. Esta arquitectura básica no requiere un despliegue independiente de un «Cilium API Server» para todo el cluster. Los agentes tienen API locales, y el servidor API opcional de ClusterMesh cumple otra función.

| Componente | Función |
| --- | --- |
| Cilium Agent | Gestión local de endpoints, políticas, estado de enrutamiento/Services y eBPF |
| Cilium Operator | Reconciliación del cluster y asignación/controladores según el modo elegido |
| Envoy | Proxy en espacio de usuario para políticas L7, ingress/Gateway y funciones relacionadas habilitadas |
| Servidor Hubble | API local de flujos integrada en el agente |
| Hubble Relay / UI | Agregación de flujos / visualización de mapas de servicios y flujos |
| Endpoints de métricas Prometheus | Recopilación de estadísticas independiente; Relay/UI no forman el pipeline de extracción de métricas |
| cilium / cilium-dbg / hubble | CLI de administración del cluster / diagnóstico del agente / cliente de flujos, respectivamente |

### Redes y rutas de los paquetes

El enrutamiento nativo requiere una red subyacente con conectividad; los túneles utilizan VXLAN o Geneve. AWS ENI y Azure IPAM son opciones de asignación e integración con sus propios requisitos de plataforma. El plano de control BGP de Cilium anuncia rutas a los routers y **no programa el datapath ni proporciona el enrutamiento interno del cluster**.

No existe una secuencia universal XDP→TC→Pod. El balanceo en sockets puede actuar antes de que existan paquetes; los hooks TC/netkit dependen del datapath; XDP acelera determinados tráficos de forma opcional; y el tráfico L7 puede pasar por Envoy. La ruta de retorno también depende de NAT, conntrack y DSR. Consulte los capítulos de redes y eBPF para el perfil elegido.

## Integración con Amazon EKS

Antes de instalar, elija el perfil real de redes y cómputo. El nombre y la versión de complemento `cilium` / `v1.17.0-eksbuild.1` del ejemplo anterior no eran una distribución verificada de AWS y aquí no se incluyen como comando de instalación. Si considera un complemento de un proveedor, examine el catálogo real de la región, su editor, licencia y tipos de cómputo compatibles.

| Perfil EKS | Comprobaciones necesarias |
| --- | --- |
| Nodos EC2 convencionales con Cilium ENI en sustitución de VPC CNI | CNI administrado por el proyecto o un socio; el CNI que AWS admite para EC2 es VPC CNI. Planifique el responsable del CNI, IAM, direcciones, rutas, arranque y migración de nodos |
| Nodos EC2 convencionales con encadenamiento de AWS VPC CNI | VPC CNI gestiona las interfaces/IPAM y Cilium conecta después su dataplane. Es necesario recrear los Pods existentes; L7/IPsec tienen limitaciones documentadas |
| Hybrid Nodes | Siga la guía CNI especializada de AWS y la matriz de builds de Cilium mantenidos por AWS; la versión 1.20.3 del proyecto no es automáticamente un build compatible de AWS |
| Auto Mode | No admite plugins alternativos de CNI/políticas; use las funciones administradas de NodeClass y redes |
| Fargate | No admite instalar un CNI alternativo ni un DaemonSet |
| Windows | El agente de Cilium requiere Linux; no aplique este procedimiento a nodos Windows |

La página general de AWS sobre CNI alternativos y la guía especializada de Hybrid Nodes describen de forma distinta el soporte de Calico; que un ejemplo cambie de repositorio no demuestra que haya terminado ese soporte. Para Hybrid Nodes, confirme la distribución exacta, las funciones disponibles y el responsable del soporte. En Auto Mode, CoreDNS local al nodo y las redes del sistema también difieren de la configuración EC2 convencional de esta guía; los nodos ajenos a Auto Mode de un cluster mixto siguen necesitando el Deployment tradicional de DNS.

### Cluster EC2 preparado para Cilium ENI

Los siguientes son **valores de Helm de Cilium para un cluster EC2 IPv4 preparado**, no un procedimiento completo para crear un cluster o migrarlo in situ. Antes de utilizarlos:

1. Elija una versión de EKS/Kubernetes y una AMI Linux compatibles, y establezca un único responsable del CNI. No elimine `aws-node` de un cluster con cargas existentes como atajo.
2. Prepare los taints y la planificación de nodos para que las cargas esperen hasta que Cilium gestione el nodo. La guía EKS del proyecto utiliza `node.cilium.io/agent-not-ready=true:NoExecute`; evalúe los efectos sobre la expulsión de Pods y el arranque en el ciclo de vida real del nodo.
3. Prepare la capacidad de las subredes, las cuotas y grupos de seguridad de ENI, el acceso a los metadatos del nodo y los permisos EC2 que necesita el Operator. El ARN de rol siguiente es un marcador para un rol con la relación de confianza correcta para el **ServiceAccount cilium-operator**, no un rol creado por este archivo de valores.
4. Mantenga kube-proxy y DNS operativos en este ejemplo con `kubeProxyReplacement: false`. Para el modo de reemplazo, siga los requisitos independientes de acceso directo a la API y DNS durante el arranque. Determine el máximo de Pods según la capacidad real de la instancia/IPAM, sin asumir un valor universal de 110.

Guarde el archivo como `cilium-eni-values.yaml` y sustituya las opciones de rol e interfaz por los valores revisados:

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
# egressMasqueradeInterfaces is intentionally omitted: it only affects iptables masquerade,
# and ENI mode leaves IPv4 masquerade off by default since 1.18.
serviceAccounts:
  operator:
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/CiliumOperatorENI
```

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# After preparing the cluster and reviewing the rendered configuration:
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-eni-values.yaml
```

Gestione estos parámetros mediante el responsable de la instalación. Sustituir `cilium-config` por una configuración de pocas claves puede eliminar otros parámetros necesarios; el antiguo `tunnel=disabled` se reemplaza por `routingMode: native`. La asignación y los permisos de ENI y el comportamiento de SNAT aún requieren validación en ejecución; renderizar correctamente no demuestra que la red EC2 funcione.

**Consideraciones sobre IPv6:** la referencia de ENI IPAM 1.20.3 describe IPv6 como beta, mientras que su página de requisitos EKS sigue indicando una integración ENI exclusiva de IPv4. Esta guía conserva un ejemplo IPv4 y documenta esa discrepancia, sin tratar ninguna de las dos afirmaciones como prueba de compatibilidad de IPv6 con EKS en producción. Antes de diseñar IPv6 por separado, revise los requisitos actuales de ENI y subredes de doble pila.

### Alternativa: encadenamiento de VPC CNI

La guía de encadenamiento del proyecto requiere VPC CNI 1.11.2+ y documenta este perfil:

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

Úselo como una **configuración distinta**, sin superponerlo a los valores que reemplazan el CNI con ENI. VPC CNI sigue asignando las direcciones. Actualice el complemento administrado real mediante su responsable, en lugar de aplicar un DaemonSet histórico del proyecto. Evite motores de políticas que compitan por los mismos endpoints. Al cambiar la cadena CNI, los Pods existentes no se conectan retroactivamente a Cilium: recréelos durante un despliegue planificado y compruebe que sus endpoints estén gestionados. El encadenamiento tiene limitaciones documentadas de políticas L7/IPsec; no dé por hecho que todos los ejemplos posteriores funcionen con ese perfil.

### ClusterMesh

ClusterMesh necesita identidades de cluster únicas, versiones compatibles, redes de Pods accesibles y sin solapamientos, conectividad API autenticada y un modelo de exposición adecuado. Un Service LoadBalancer puede crear recursos en la nube y requiere un diseño deliberado de redes y seguridad. Crear dos endpoints públicos no basta para conectar clusters con seguridad. Siga la [guía mantenida de ClusterMesh](13-clustermesh-install-upgrade.md) y el capítulo avanzado para la topología elegida.

## Instalación y configuración

### Herramientas cliente

Utilice los archivos oficiales de Cilium CLI 0.20.1 y Hubble CLI 1.20.2 adecuados para el sistema operativo y la arquitectura del equipo, y verifique las sumas de comprobación suministradas antes de extraerlos. Linux ARM64 y AMD64 usan archivos distintos; macOS usa los correspondientes a Darwin. Las versiones de las CLI son independientes de la versión del agente/chart de Cilium. Consulte las [instrucciones verificadas de instalación de las CLI](../../service-mesh/cilium-service-mesh/README.md).

```bash
cilium version --client
hubble version
```

### Ejemplo cluster-pool para un cluster fuera de la nube

La siguiente **alternativa** corresponde a un cluster Linux convencional preparado, con kube-proxy y DNS ya operativos. Compruebe que el rango de Pods del ejemplo, `10.244.0.0/16`, sea compatible con el cluster y no se solape con rangos de Services, nodos, VPC ni redes conectadas. No utilice esta configuración de pool para el modo ENI.

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - icmp
    - httpV2
```

Guarde el archivo como `cilium-values.yaml`, renderice el chart con la versión fijada e instálelo únicamente en el cluster preparado:

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

Para una instalación existente, siga su proceso de actualización/GitOps, conserve los valores gestionados por su responsable y aplique el procedimiento de actualización de esa versión. Repetir ejemplos de `cilium install` no es un método general para cambiar parámetros individuales.

| Opción | Configuración actual y requisito |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` junto con `tunnelProtocol`; permita la encapsulación elegida y ajuste el MTU a la ruta |
| Enrutamiento nativo | `routingMode: native`; la red subyacente debe enrutar las direcciones de Pods. `autoDirectNodeRoutes` requiere conectividad directa adecuada, no cualquier combinación de subredes |
| Reemplazo de kube-proxy | `kubeProxyReplacement: true` o `false`, en lugar del antiguo `strict`; el reemplazo necesita `k8sServiceHost`/`k8sServicePort` accesibles y el plan de arranque documentado |
| WireGuard | Habilite el modo de cifrado compatible después de comprobar el kernel, la plataforma y las rutas entre peers; no cifra automáticamente todas las rutas posibles del tráfico |
| IPsec | Requiere el Secret de claves documentado, distribución/rotación de claves y un modo compatible; el flag de Helm por sí solo no completa la configuración |
| XDP/DSR/BBR | Opciones independientes que dependen del dispositivo, kernel y topología, no una configuración universal de instalación |

## Políticas de red

NetworkPolicy de Kubernetes, con API `networking.k8s.io/v1`, y las políticas `cilium.io/v2` de Cilium son API distintas. Varias políticas de permiso pueden combinarse. Estos ejemplos usan **namespaces de prueba preparados por separado** para que el permiso L4 no anule inadvertidamente la restricción L7. Antes de sacar conclusiones, examine todas las políticas que seleccionan los endpoints reales.

### Ejemplo L4

En `cilium-l4-demo`, esta política selecciona los Pods backend y permite tráfico entrante de Pods frontend del mismo namespace en TCP 8080:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-l4-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - port: 8080
      protocol: TCP
```

### Ejemplo HTTP

En el namespace independiente `cilium-l7-demo`, esta política selecciona los Pods backend y restringe HTTP sin cifrar en TCP 8080 al método y la ruta indicados, desde Pods frontend de ese namespace. El modo CNI elegido debe admitir el proxy L7; HTTP cifrado no se inspecciona automáticamente sin una configuración de terminación compatible.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-product-read
  namespace: cilium-l7-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-l7-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/api/v1/products$
```

No añada un permiso L4 sin restricciones para los mismos peers y puerto: Cilium documenta que ese permiso elimina el efecto de las restricciones L7 más específicas. Una denegación L7 puede devolver HTTP 403 en lugar de descartar un paquete. Pruebe solicitudes GET permitidas y métodos/rutas denegados con identidades reales de endpoints.

### Ejemplo DNS/FQDN

En `cilium-dns-demo`, esta política permite consultas DNS a los Pods convencionales de CoreDNS y TCP 443 a las direcciones aprendidas para `api.example.com`. El dominio es un ejemplo; sustitúyalo por un destino aprobado. El comodín amplio `*.amazonaws.com` no define un límite de cuenta ni de recurso y se omite.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-api-domain
  namespace: cilium-dns-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:k8s-app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

El comodín DNS permite consultas al resolver seleccionado, no conexiones a todas las direcciones devueltas. Aun así, puede transportar nombres DNS arbitrarios; cuando sea necesario, restrinja los nombres consultados teniendo en cuenta los sufijos de búsqueda DNS. NodeLocal DNS u otro resolver requieren seleccionar el destino correcto. La política FQDN autoriza IP derivadas de DNS, sin verificar el nombre de host TLS ni autorizar URL HTTP; las IP compartidas y el TLS y la autenticación de la aplicación siguen siendo relevantes.

## Observabilidad con Hubble

Los valores cluster-pool anteriores habilitan Relay/UI y métricas de componentes. En una instalación existente, aplique los valores de Hubble mediante el responsable de la configuración; `cilium hubble enable --ui` es un comando auxiliar compatible, pero `cilium hubble enable --metrics=...` no es un flag admitido por la CLI 0.20.1. Configure en su lugar `hubble.metrics.enabled` en los valores de Helm. No habilite juntos los handlers antiguos `http` y `httpV2`.

Mantenga el reenvío de puertos de Relay activo en una terminal:

```bash
cilium hubble port-forward --port-forward 4245
```

En otra terminal, con Hubble CLI instalado:

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

Este ejemplo local presupone la configuración predeterminada del servidor Relay; si Relay usa TLS, el cliente necesita la configuración correspondiente de confianza y autenticación. Los eventos HTTP requieren que el tráfico atraviese el proxy L7 configurado. `DROPPED` es un veredicto del datapath, no representa todas las solicitudes fallidas de la aplicación. Use `cilium hubble ui` para reenviar el puerto de la UI y configure por separado el descubrimiento de targets de Prometheus para las métricas. El streaming de flujos de Hubble no constituye por sí solo tracing distribuido de aplicaciones.

## Pruebas y operaciones

Los comandos de conectividad y rendimiento crean cargas de prueba y pueden cambiar políticas o generar tráfico considerable. Use un namespace/entorno de prueba y permisos revisados; esta revisión no los ejecutó contra un cluster.

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

El subcomando de rendimiento es `cilium connectivity perf`; `connectivity test --test=performance` solo proporciona un filtro de nombres de pruebas, no ejecuta el runner de rendimiento. Registre las versiones de software, la topología, el tráfico y los resultados sin procesar antes de comparar throughput o latencia.

Para la inspección, distinga la CLI de administración de **`cilium-dbg`, ejecutado dentro del agente**:

```bash
cilium status --verbose
kubectl get cnp,ccnp -A
kubectl get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent Pod on the affected node.
CILIUM_POD=replace-with-actual-cilium-pod
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg metrics list
kubectl logs -n kube-system "$CILIUM_POD" -c cilium-agent --since=15m --tail=200 --timestamps
```

`cilium endpoint list`, `cilium bpf maps list` y `cilium metrics list` no son comandos equivalentes de la CLI de administración. `cilium sysdump` puede recopilar material de diagnóstico; proteja los datos resultantes de infraestructura y registros. Un agente Ready o una extracción de métricas correcta no sustituyen las pruebas de aplicaciones y las pruebas de denegación de políticas.

### Prioridades operativas

- Mida antes de habilitar la preasignación de maps, XDP, DSR, BBR o un patrón fijo de dispositivos. Estas opciones consumen recursos o cambian rutas de paquetes y requieren comprobaciones específicas.
- Introduzca la denegación predeterminada en un ámbito seleccionado, con permisos explícitos para DNS, API, identidad y dependencias de aplicaciones. Compruebe tanto los Pods nuevos y las transiciones de actualización como las conexiones establecidas.
- Verifique por separado el cifrado, la rotación de certificados/claves, la aplicación de políticas y la observabilidad. Mantenga una vía operativa de administración y recuperación.
- Revise la matriz actual de plataformas y la ruta de actualización compatible. Los anuncios históricos de versiones no establecen la compatibilidad actual del despliegue.

## Índice de contenidos

**[Introducción a Cilium y conceptos básicos](01-introduction.md)**
- Descripción general e historia de Cilium
- Fundamentos de redes de contenedores
- Comprensión de CNI (Container Network Interface)
- Funciones que distinguen a Cilium

**[La tecnología eBPF en profundidad](02-ebpf.md)**
- Introducción e historia de eBPF
- Funcionamiento de eBPF dentro del kernel
- Tipos de programas y maps eBPF
- Uso de eBPF en Cilium

**[Modelos de redes y VXLAN](03-networking.md)**
- Comparación de modelos de redes de contenedores
- VXLAN en profundidad
- Redes overlay de Cilium
- Técnicas de optimización del rendimiento
- Mecanismos de enrutamiento: encapsulación y enrutamiento nativo
- Redes de proveedores de nube: AWS ENI y Google Cloud

**[IPAM y políticas de red](04-ipam-policy.md)**
- Estrategias de gestión de direcciones IP (IPAM)
- Integración de IPAM de Kubernetes y Cilium
- Diseño e implementación de políticas de red
- Escenarios con varios clusters
- Modos IPAM en profundidad: ámbito de cluster, ámbito de host Kubernetes y multi-pool
- IPAM de proveedores de nube: Azure IPAM, AWS ENI y GKE
- IPAM basado en CRD

**[Redes L2-L7 y balanceo de carga](05-l2-l7-networking.md)**
- Capas del modelo OSI: L2, L3, L4 y L7
- Funciones de Cilium por capa
- Integración con mallas de servicios
- Arquitectura del balanceo de carga
- Configuración y modos de implementación de masquerading
- Tratamiento de fragmentos IPv4

**[Seguridad y visibilidad](06-security-visibility.md)**
- Funciones de seguridad de Cilium
- Visibilidad y supervisión de redes
- Arquitectura y uso de Hubble
- Detección de amenazas en tiempo real

**[Temas avanzados y casos reales](07-advanced-topics.md)**
- Ajuste del rendimiento y resolución de problemas
- Estrategias de despliegue a gran escala
- Estudios de casos de uso reales
- Hoja de ruta y dirección futura del desarrollo

**[Funcionamiento interno del datapath eBPF](08-ebpf-datapath-internals.md)**
- Conjunto de programas, puntos de conexión y llamadas de cola
- Catálogo de maps BPF, dimensionamiento y flujo de compilación/carga
- Ruta de aplicación de políticas y pipeline de eventos de Hubble

**[Overlay y enrutamiento nativo](09-overlay-native-routing.md)**
- VXLAN/Geneve, identidad en el VNI, MTU y recorrido de paquetes
- Enrutamiento nativo, masquerading, enrutamiento del host, DSR y netkit
- Tabla de decisión para EKS: overlay, ENI o encadenamiento de VPC CNI

**[IPAM en profundidad](10-ipam-deep-dive.md)**
- Todos los modos IPAM, cálculos de dimensionamiento y matriz de decisión
- Multi-pool, `CiliumPodIPPool`, ENI, LB IPAM y Node IPAM
- Diagnóstico del agotamiento de direcciones y cambios de API en 1.21

**[BGP, IP de balanceadores y salida de tráfico](11-bgp-lb-egress-edge.md)**
- CRD del plano de control BGP v2, anuncios e inspección
- Anuncios L2, Egress Gateway y Local Redirect Policy
- Requisitos de Gateway API y exposición interna exclusiva en EKS

**[mTLS, cifrado e identidad](12-mtls-encryption-identity.md)**
- Modelo de identidad, semántica de políticas y modo de auditoría
- Evolución de Mutual Authentication y mTLS de cargas con ztunnel
- WireGuard, IPsec, Hubble y gestión de certificados

**[Versiones, instalación/actualización y ClusterMesh](13-clustermesh-install-upgrade.md)**
- Matriz de funciones 1.17-1.21 y reglas de actualización y reversión
- Particularidades de instalación en EKS, ClusterMesh y MCS-API

## Recursos adicionales

- [Conceptos de redes en profundidad](networking-concepts.md)
- [Glosario y abreviaturas](glossary.md)

## Referencias

- [Compatibilidad de Cilium 1.20 con Kubernetes](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Requisitos del sistema de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [Requisitos para EKS](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [ENI IPAM de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [Soporte de CNI alternativos en AWS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [CNI para AWS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Semántica de políticas L7 de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Proyecto Hubble](https://github.com/cilium/hubble)
- [Redes e integración de políticas de Flannel](https://github.com/flannel-io/flannel)
- [Terminología de comparación de Calico](../calico/glossary.md)

## Cuestionario

Para comprobar lo aprendido en esta sección, complete el [cuestionario de Cilium en profundidad](../../quizzes/networking/cilium/01-introduction-quiz.md).
