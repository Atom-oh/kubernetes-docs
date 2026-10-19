# Análisis profundo de Cilium: el futuro de las redes nativas de la nube

## Descripción general y línea base revisada

Esta sección abarca las redes, las políticas y la observabilidad de Cilium. Los ejemplos se revisaron con **Cilium/Helm chart 1.20.3**, Cilium CLI **0.20.1** y Hubble CLI **1.20.2**. La página de compatibilidad de Cilium 1.20 con Kubernetes indica que **1.33–1.36** son versiones probadas; una versión upstream 1.37 no amplía automáticamente esa matriz. Los hosts compatibles son Linux AMD64/AArch64 con kernel **5.10+**, o el equivalente de distribución documentado, como el kernel 4.18 con backports de RHEL 8.10. Cada función puede tener requisitos adicionales.

> **Última actualización**: 19 de octubre de 2026

### Notas históricas de las versiones

Las fechas siguientes son las fechas de publicación en GitHub, en UTC, y describen esas versiones, no las versiones fijadas para la instalación actual. Los backports de funciones varían entre las distintas líneas de versiones.

| Fecha | Versión | Aspectos destacados verificados |
| --- | --- | --- |
| 14 de julio de 2026 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | Primera versión candidata de 1.20 |
| 16 de julio de 2026 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | La configuración de los registros de acceso de Gateway figura en 1.19.6/1.18.12; las correcciones de la política de reinicio y la afinidad de ClusterMesh citadas aquí aparecen en 1.19.6, no en las tres versiones |
| 21 de julio de 2026 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | Segunda versión candidata de 1.20 |
| 29 de julio de 2026 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | Versión GA; cambios seleccionados a continuación |
| 3 de agosto de 2026 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | Versión preliminar del siguiente ciclo, no es la línea base de despliegue de esta guía |
| 18 de agosto de 2026 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | Documentación de ClusterMesh y correcciones de errores, incluida la gestión de reinicios y políticas CIDR |
| 18 de agosto de 2026 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | Incluye correcciones de temporización de interfaces ENI, Service/LB y otras |
| 18 de agosto de 2026 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | Compatibilidad con el firewall del host para VRRP/IGMP y correcciones relacionadas |
| 9 de septiembre de 2026 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | Versión preliminar; su registro de cambios abarca de pre.0 a pre.2 porque **1.21.0-pre.1 nunca se publicó** |
| 16 de septiembre de 2026 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | Correcciones de errores, incluida la asignación/liberación de delegación de prefijos de ENI IPAM y la gestión de CIDR secundarios de VPC, correcciones de ClusterMesh, revisión de políticas para Pods creados justo después de un cambio de política, una regresión de LocalRedirectPolicy y la actualización de clústeres creados con v1.15 o anterior (versión CRD `CiliumNodeConfig v2alpha1`) |
| 16 de septiembre de 2026 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | Versiones de parche de las líneas anteriores aún compatibles |
| 2 de octubre de 2026 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | Última versión preliminar de 1.21; **1.21 solo está disponible como versión preliminar (todavía no hay versión GA)** y los elementos de esta guía marcados como 1.21 pueden cambiar |
| 15 de octubre de 2026 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Dependencia de Gateway API v1.6.3, GC de conntrack y gestión de CNP con `nodeSelector`, entre otras correcciones; la línea base revisada actual de esta guía |
| 15 de octubre de 2026 | [1.19.9](https://github.com/cilium/cilium/releases/tag/v1.19.9), [1.18.15](https://github.com/cilium/cilium/releases/tag/v1.18.15) | Versiones de parche de las líneas anteriores aún compatibles |

El 14 de septiembre de 2026, el blog de CNCF publicó un [resumen de las funciones de Cilium 1.20](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/) (Gateway API ExternalAuth, TCPRoute/UDPRoute, IPv6 ENI IPAM y más), que abarca el mismo alcance que el resumen del anuncio de 1.20.0 a continuación.

El anuncio de 1.20.0 informa de **más de 2660 commits nuevos**, respaldados por una **comunidad de más de 1100 colaboradores**. Esta última cifra indica el tamaño de la comunidad, no la cantidad de autores de esta versión. Entre los aspectos destacados se incluyen:

- Gateway API **1.6.1**, TCPRoute/UDPRoute, BackendTLSPolicy, ListenerSets, ExternalAuth y compatibilidad con CORS, sujetos a la configuración y el grado de madurez de la API de cada función.
- Plugins de datapath y `bpf.datapathMode=auto` opcional; el valor predeterminado anunciado sigue siendo veth. Los clústeres de doble pila pueden configurar una dirección de gateway de salida IPv6.
- IPv6 ENI IPAM en **beta** y migración de cluster-pool a multi-pool sin reconstruir el clúster. La migración en el mismo lugar no garantiza que no haya interrupciones.
- Sugerencias de distribución de tráfico, backends Maglev ponderados e integración estable de MCS; compatibilidad con Kubernetes ClusterNetworkPolicy e identidad de cargas de trabajo basada en ztunnel en **beta**.
- Reducción informada del binario `cilium-cni` de aproximadamente **77 MB a 16 MB**. Las mejoras de ADS/Delta xDS aparecen en el anuncio de 1.20; no se deben atribuir a las notas de parche de 1.18.13. Estas son afirmaciones de la versión upstream, no mediciones repetidas en esta auditoría.

Consulta las [notas de actualización a 1.20](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes) para obtener información sobre Mutual Authentication (**obsoleta en 1.20**, eliminada en la versión preliminar 1.21), las extensiones Envoy Go eliminadas/sustituidas, las políticas con reconocimiento de Kafka, la API antigua de CiliumNodeConfig, la integración con libnetwork y los cambios en la configuración personalizada de CNI.

### Aviso de seguridad de NetworkPolicy

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) tiene como fecha de publicación del aviso del proyecto el **6 de julio de 2026**. La API del proyecto y la API global de avisos de GitHub muestran fechas distintas: esta última registra el 3 de septiembre. Para esta cronología de versiones, utiliza la fecha de divulgación del proyecto; la fecha del registro global no corresponde a una versión de corrección posterior. Afecta a las versiones **1.19.0–1.19.4** bajo las condiciones de nombre de clúster personalizado del aviso: un peer de una NetworkPolicy estándar de Kubernetes que contenga únicamente `ipBlock` puede permitir involuntariamente el ingreso de cargas de trabajo del espacio de nombres del Pod seleccionado. **1.19.5** corrige este problema; para el despliegue, utiliza una versión parcheada actual apropiada. El aviso indica que CiliumNetworkPolicy/ClusterwideNetworkPolicy y las versiones anteriores a 1.19.0 no se ven afectadas por este error concreto.

## Introducción

Cilium proporciona redes, seguridad y observabilidad para entornos Kubernetes compatibles con Linux. El enrutamiento, IPAM, cifrado y la gestión de Service son opciones independientes; elegir eBPF por sí solo no habilita todas las funciones ni garantiza el rendimiento. La antigua integración de Docker libnetwork se eliminó en 1.20, por lo que Docker/Mesos no deberían incluirse aquí como destinos de instalación actuales intercambiables.

### eBPF y capacidades principales

El kernel verifica los programas eBPF antes de cargarlos y puede compilarlos con JIT para ejecutarlos en hooks compatibles. Esto permite el procesamiento de paquetes y la observabilidad sin un módulo de kernel personalizado; el verificador no demuestra que la aplicación o la política sean correctas. El rendimiento real, la latencia y el consumo de memoria dependen de los programas, la plataforma y la carga de trabajo.

Cilium ofrece políticas L3/L4, políticas L7 mediante la integración con Envoy/proxy DNS, WireGuard/IPsec opcionales, balanceo de carga de Service, visibilidad de flujos con Hubble, ClusterMesh y anuncios BGP. La aceleración XDP es opcional y depende del dispositivo y la configuración. Las funciones L7 pueden utilizar Envoy por nodo; la identidad de cargas de trabajo mediante ztunnel requiere una configuración beta independiente. Instalar solo el agente no habilita todo el comportamiento de malla, cifrado o multiclúster.

### Comparación con otros proyectos de redes

| Proyecto | Conectividad / IPAM | Políticas y capacidades relacionadas |
| --- | --- | --- |
| Cilium | Enrutamiento nativo o superpuesto; modos de IPAM, incluido cloud ENI | Dataplane eBPF, políticas de Cilium/Kubernetes, integración L7, Hubble y cifrado opcional |
| Calico | Perfiles nativos/IPIP/VXLAN con IPAM de Calico o externo | Iptables/Nftables/BPF de Linux, HNS de Windows compatible; WireGuard en OSS, políticas por etapas e integración L7 independiente |
| Flannel | Conectividad de Pods mediante backends seleccionados, como VXLAN/host-gw/WireGuard | El demonio de enrutamiento no aplica NetworkPolicy; su chart puede desplegar el controlador de políticas de red de SIGs con `netpol.enabled`, o se puede combinar con otra implementación de políticas |
| AWS VPC CNI | Asignación de direcciones ENI de VPC/redes | Política de red nativa en nodos Linux de EC2 compatibles y funcionalidad SG-for-Pods independiente; EKS Auto Mode es una implementación gestionada distinta |

Un modo de enrutamiento no pertenece a la misma categoría que una implementación de procesamiento de paquetes. Calico no se limita a iptables/IPVS, Flannel puede utilizar un backend cifrado y las políticas de AWS no son sinónimo de grupos de seguridad. Las mallas de servicios son capas opcionales, y la conectividad de VPC entre clústeres no se limita a Transit Gateway. En lugar de clasificaciones universales de rendimiento, utiliza una carga de trabajo medida y una matriz de compatibilidad explícita.

## Arquitectura

El **servidor de API de Kubernetes** almacena recursos de Kubernetes/Cilium. Los agentes de Cilium observan el estado pertinente y programan el dataplane de cada nodo; el Cilium Operator se encarga de responsabilidades a nivel de clúster, como la gestión del IPAM seleccionado y el trabajo de identidades/controladores. En esta arquitectura básica no hay un despliegue independiente y obligatorio de un «Cilium API Server» para todo el clúster. Los agentes tienen API locales, y el servidor de API opcional de ClusterMesh cumple otra función.

| Componente | Función |
| --- | --- |
| Cilium Agent | Gestión local del nodo de los endpoints, las políticas, el estado del enrutamiento/Service y eBPF |
| Cilium Operator | Conciliación a nivel de clúster y trabajo de asignación/controlador según el modo |
| Envoy | Proxy de espacio de usuario para políticas L7 habilitadas, ingress/Gateway y funciones relacionadas |
| Hubble server | API de flujos local al nodo e integrada con el agente |
| Hubble Relay / UI | Agrega flujos / muestra mapas de servicios y flujos |
| Endpoints de métricas de Prometheus | Recopilación independiente de estadísticas; Relay/UI no es la canalización de recopilación de métricas |
| cilium / cilium-dbg / hubble | CLI de gestión del clúster / diagnóstico del agente / cliente de flujos, respectivamente |

### Redes y rutas de paquetes

El enrutamiento nativo necesita una red subyacente accesible; el encapsulamiento utiliza VXLAN o Geneve. AWS ENI y Azure IPAM son opciones de asignación/integración con requisitos propios de cada plataforma. BGP Control Plane de Cilium anuncia la accesibilidad a los routers y **no programa el datapath ni proporciona enrutamiento interno del clúster**.

No existe una secuencia universal XDP→TC→Pod. El balanceo de carga a nivel de socket puede actuar antes de que existan paquetes, los hooks TC/netkit dependen del datapath, XDP opcional acelera el tráfico seleccionado y el tráfico L7 puede pasar por Envoy. El tráfico de retorno también depende de las opciones de NAT, conntrack y DSR. Consulta los capítulos sobre redes y eBPF para ver el perfil seleccionado.

## Integración con Amazon EKS

Elige el perfil real de redes y cómputo antes de instalar nada. El nombre/versión de addon de ejemplo `cilium` / `v1.17.0-eksbuild.1` no correspondía a una distribución de AWS verificada y aquí no se presenta como comando de instalación. Si estás considerando un addon de proveedor empaquetado, consulta el catálogo de addons real de la Región, su editor, licencia y tipos de cómputo compatibles.

| Perfil de EKS | Qué verificar |
| --- | --- |
| Nodos EC2 ordinarios, Cilium ENI sustituye a VPC CNI | CNI gestionado por upstream/socio; el CNI de EC2 compatible con AWS es VPC CNI. Planifica la responsabilidad del CNI, IAM, direccionamiento, rutas, bootstrap y migración de nodos |
| Nodos EC2 ordinarios, encadenamiento de AWS VPC CNI | VPC CNI se encarga de las interfaces/IPAM; Cilium conecta después su dataplane. Es necesario recrear los Pods existentes y existen limitaciones documentadas para L7/IPsec |
| Hybrid Nodes | Sigue la guía especializada de CNI de AWS y la matriz de compilaciones de Cilium mantenida por AWS; upstream 1.20.3 no es automáticamente la compilación compatible de AWS |
| Auto Mode | No se admiten plugins de CNI/políticas alternativos; utiliza las funciones gestionadas de NodeClass/redes |
| Fargate | No se admite la instalación de CNI/DaemonSet alternativos |
| Windows | Los requisitos del agente de Cilium son Linux; no apliques esta receta a los nodos de trabajo Windows |

La página general de AWS sobre CNI alternativos y la guía especializada para Hybrid difieren en cómo expresan la compatibilidad con Calico; un ejemplo de traslado de repositorios no demuestra que se haya dejado de ofrecer compatibilidad. Para Hybrid Nodes, confirma la distribución exacta, el conjunto de capacidades y quién se encarga de la compatibilidad. En Auto Mode, CoreDNS local al nodo y las redes del sistema también difieren de la configuración habitual de EC2 descrita en esta guía; los nodos mixtos que no sean Auto siguen necesitando el Deployment de DNS tradicional.

### Clúster EC2 preparado con Cilium ENI

Estos son **valores de Cilium Helm para un clúster EC2 IPv4 preparado**, no una receta completa para crear un clúster ni para migrarlo en el mismo lugar. Antes de utilizarlos:

1. Elige una versión de EKS/Kubernetes y una AMI de Linux compatibles, y establece quién será el único responsable del CNI. No elimines `aws-node` de un clúster existente con cargas de trabajo como atajo.
2. Prepara las taints/planificación de los nodos para que las cargas de trabajo esperen hasta que Cilium gestione el nodo. La guía upstream de EKS utiliza `node.cilium.io/agent-not-ready=true:NoExecute`; evalúa los efectos sobre la expulsión y el bootstrap en el ciclo de vida real del nodo.
3. Prepara la capacidad de las subredes, las cuotas de ENI/grupos de seguridad, el acceso a los metadatos de los nodos y los permisos de EC2 que necesita el operador. El ARN de rol que aparece a continuación es un marcador de posición para un rol **cilium-operator ServiceAccount** con una relación de confianza correctamente configurada; no es un rol creado por el archivo de valores.
4. Mantén kube-proxy y DNS en funcionamiento para este ejemplo con `kubeProxyReplacement: false`. Para el modo de sustitución, sigue los requisitos independientes para el acceso directo a la API/bootstrap-DNS. Elige el valor de max-Pods según la capacidad real de la instancia/IPAM, no un valor universal de 110.

Guárdalo como `cilium-eni-values.yaml` y sustituye el rol y las opciones de interfaz por valores revisados:

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

Gestiona estos ajustes a través del responsable de la instalación. Un `cilium-config` sustituto que contenga solo unas pocas claves puede eliminar otros ajustes necesarios; el valor antiguo `tunnel=disabled` se sustituye por `routingMode: native`. La asignación ENI, los permisos y el comportamiento de SNAT aún requieren validación en tiempo de ejecución; que la renderización termine correctamente no demuestra que las redes de EC2 sean utilizables.

**Aclaración sobre IPv6:** la referencia de ENI IPAM de 1.20.3 describe IPv6 como beta, mientras que la página de requisitos previos de EKS sigue indicando que la integración ENI solo admite IPv4. Esta guía mantiene un ejemplo IPv4 y señala esa inconsistencia en la documentación, en lugar de tratar cualquiera de las dos afirmaciones como prueba de compatibilidad de producción entre EKS e IPv6. Antes de diseñar una solución IPv6 independiente, revisa los requisitos actuales de ENI/subredes de doble pila.

### Alternativa de encadenamiento de VPC CNI

La guía upstream de encadenamiento requiere VPC CNI 1.11.2+ y documenta este perfil:

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

Utilízalo como **una configuración distinta**, no como una superposición sobre los valores para sustituir ENI. VPC CNI sigue siendo el asignador. Actualiza el addon gestionado real a través de quien lo gestione, en lugar de aplicar un DaemonSet upstream histórico. Evita tener motores de políticas en conflicto en los mismos endpoints. Cuando cambia la cadena de CNI, los Pods existentes no se conectan retroactivamente a Cilium; recréalos como parte de una implementación planificada y verifica la gestión de los endpoints. El encadenamiento tiene limitaciones documentadas para políticas L7/IPsec, así que no des por sentado que todos los ejemplos posteriores de esta página funcionen con ese perfil.

### ClusterMesh

ClusterMesh necesita identidades de clúster únicas, versiones compatibles, redes de Pods accesibles y no superpuestas, conectividad de API autenticada y un modelo de exposición adecuado. Un Service de tipo LoadBalancer puede crear recursos en la nube y requiere un diseño de redes/seguridad deliberado. Crear dos endpoints públicos no basta para conectar clústeres de forma segura. Sigue la [guía de ClusterMesh](13-clustermesh-install-upgrade.md) mantenida y el capítulo avanzado correspondiente a la topología elegida.

## Instalación y configuración

### Herramientas cliente

Utiliza los artefactos oficiales adecuados de Cilium CLI 0.20.1 y Hubble CLI 1.20.2 para el sistema operativo/la arquitectura de la estación de trabajo y verifica las sumas de comprobación proporcionadas antes de extraerlos. Linux ARM64 y AMD64 utilizan artefactos distintos; macOS utiliza los artefactos Darwin correspondientes. Las versiones de CLI son independientes de la versión del agente/chart de Cilium. Consulta la [guía de instalación verificada de CLI](../../service-mesh/cilium-service-mesh/README.md).

```bash
cilium version --client
hubble version
```

### Ejemplo de cluster-pool para un clúster no basado en la nube

La siguiente **alternativa** es para un clúster Linux ordinario preparado, con kube-proxy y DNS ya en funcionamiento. Asegúrate de que el rango de Pods de ejemplo `10.244.0.0/16` sea compatible con el clúster y no se superponga con los rangos de Service, nodos, VPC o redes conectadas. No utilices esta configuración de pool para el modo ENI.

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

Guárdalo como `cilium-values.yaml`, renderiza el chart con la versión fijada y luego instálalo solo en el clúster preparado:

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

Para una versión existente, utiliza su proceso de actualización/GitOps, conserva los valores bajo su gestión y sigue el procedimiento de actualización específico de la versión. Repetir ejemplos de `cilium install` no es una forma general de cambiar ajustes individuales.

| Opción | Configuración actual y requisito previo |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` más `tunnelProtocol`; permite la encapsulación elegida y establece el MTU para la ruta |
| Enrutamiento nativo | `routingMode: native`; la red subyacente debe enrutar las direcciones de los Pods. `autoDirectNodeRoutes` requiere conectividad directa adecuada, no enrutamiento arbitrario entre varias subredes |
| Sustitución de kube-proxy | `kubeProxyReplacement: true` o `false`, no `strict` heredado; la sustitución requiere que `k8sServiceHost`/`k8sServicePort` sean accesibles y que se siga el plan de bootstrap documentado |
| WireGuard | Habilita el modo de cifrado compatible tras comprobar el kernel/la plataforma y las rutas entre peers; no cifra automáticamente todas las rutas de tráfico posibles |
| IPsec | Requiere el Secret de claves documentado, distribución/rotación de claves y un modo compatible; la opción de habilitación de Helm por sí sola no es suficiente |
| XDP/DSR/BBR | Opciones independientes que dependen del dispositivo/kernel/topología; no son un ajuste preestablecido de instalación universal |

## Políticas de red

NetworkPolicy de Kubernetes `networking.k8s.io/v1` y las políticas de Cilium `cilium.io/v2` son API distintas. Varias políticas de permiso pueden combinarse. Estos ejemplos utilizan **espacios de nombres de prueba preparados por separado** para que la regla de permiso L4 no eluda silenciosamente la restricción L7. Antes de sacar conclusiones, inspecciona todas las políticas que seleccionen los endpoints reales.

### Ejemplo L4

En `cilium-l4-demo`, esto selecciona los Pods backend y permite el ingreso desde los Pods frontend del mismo espacio de nombres en TCP 8080:

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

En un espacio de nombres independiente, `cilium-l7-demo`, esto selecciona los Pods backend y restringe el tráfico HTTP sin cifrar en TCP 8080 al método/ruta especificados desde los Pods frontend de ese espacio de nombres. La compatibilidad con el proxy L7 debe estar disponible en el modo de CNI elegido; el tráfico HTTP cifrado no se inspecciona automáticamente sin una configuración de terminación compatible.

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

No añadas una regla de permiso L4 sin restricciones que coincida con los mismos peers/puerto: Cilium documenta que ese permiso elimina el efecto de las restricciones L7 más específicas. Una denegación L7 puede devolver un HTTP 403 en lugar de descartar un paquete. Prueba solicitudes GET permitidas y métodos/rutas denegados con identidades de endpoint reales.

### Ejemplo de DNS/FQDN

En `cilium-dns-demo`, esto permite consultas DNS a Pods ordinarios de CoreDNS y TCP 443 a las direcciones conocidas para `api.example.com`. El dominio es un ejemplo; sustitúyelo por un destino aprobado. Se omite el comodín amplio `*.amazonaws.com`, ya que no es un límite de cuenta/recurso.

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

El comodín DNS permite consultas al resolver seleccionado, no conexiones a todas las direcciones devueltas. Aun así, puede transportar nombres DNS arbitrarios; restringe los nombres consultados cuando sea necesario y ten en cuenta los sufijos de búsqueda DNS. NodeLocal DNS u otro resolver requieren seleccionar el destino correcto. La política FQDN es una autorización de direcciones IP derivada de DNS, no una verificación del nombre de host TLS ni una autorización de URL HTTP; siguen siendo importantes las IP compartidas y la autenticación/TLS de la aplicación.

## Observabilidad con Hubble

Los valores de cluster-pool anteriores habilitan Relay/UI y las métricas de los componentes. Para una instalación existente, aplica los valores de Hubble previstos a través de quien gestione su configuración; `cilium hubble enable --ui` es un comando de conveniencia compatible, pero `cilium hubble enable --metrics=...` no es una opción compatible de CLI 0.20.1. En su lugar, configura `hubble.metrics.enabled` en los valores de Helm. No habilites simultáneamente el controlador heredado `http` y el controlador `httpV2`.

Mantén el port-forward de Relay en ejecución en una terminal:

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

Este ejemplo local presupone la configuración predeterminada del servidor Relay; un Relay con TLS habilitado requiere la confianza/autenticación correspondiente del cliente. Los eventos HTTP requieren que el tráfico pase por el proxy L7 configurado. `DROPPED` es un veredicto del datapath, no equivale a toda solicitud de aplicación fallida. Utiliza `cilium hubble ui` para el port-forward de la UI y configura por separado la detección de destinos de Prometheus para las métricas. La transmisión de flujos de Hubble no constituye por sí sola un sistema de trazas distribuidas de aplicaciones.

## Pruebas y operaciones

Los comandos de conectividad/rendimiento crean cargas de trabajo de prueba y pueden cambiar las políticas o generar mucho tráfico. Utiliza un entorno/espacio de nombres de prueba y permisos revisados; esta auditoría no los ejecutó en un clúster.

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

El subcomando de rendimiento es `cilium connectivity perf`; `connectivity test --test=performance` solo proporciona un filtro por nombre de prueba y no ejecuta las pruebas de rendimiento. Registra las versiones del software, la topología, el tráfico y los resultados sin procesar antes de comparar el rendimiento/la latencia.

Para la inspección, distingue la CLI de gestión de **`cilium-dbg` del lado del agente**:

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

`cilium endpoint list`, `cilium bpf maps list` y `cilium metrics list` no son comandos equivalentes de la CLI de gestión. `cilium sysdump` puede recopilar material de diagnóstico; protege los datos de infraestructura/registros resultantes. Que un agente esté Ready o que una recopilación de métricas se complete correctamente no sustituye las pruebas de aplicación ni las pruebas negativas de políticas.

### Prioridades operativas

- Mide antes de habilitar la preasignación de mapas, XDP, DSR, BBR o un patrón de dispositivo fijo. Estas opciones consumen recursos o cambian las rutas de los paquetes y requieren comprobaciones específicas de cada función.
- Introduce la denegación predeterminada en un ámbito seleccionado, permitiendo explícitamente las dependencias de DNS, API, identidad y aplicaciones. Comprueba los Pods nuevos y las transiciones de actualización, además de las conexiones establecidas.
- Mantén como verificaciones de aceptación independientes el cifrado, la rotación de certificados/claves, la aplicación de políticas y la observabilidad. Conserva una ruta de gestión/recuperación utilizable.
- Revisa la matriz actual de plataformas y la ruta de actualización compatible. Los anuncios históricos de versiones no demuestran la compatibilidad con los despliegues actuales.

## Índice del análisis en profundidad

**[Introducción a Cilium y conceptos básicos](01-introduction.md)**
- Descripción general e historia de Cilium
- Fundamentos de las redes de contenedores
- Introducción a CNI (Container Network Interface)
- Funciones diferenciadoras de Cilium

**[Análisis profundo de la tecnología eBPF](02-ebpf.md)**
- Introducción e historia de la tecnología eBPF
- Funcionamiento de eBPF dentro del kernel
- Tipos de programas y mapas de eBPF
- Uso de eBPF en Cilium

**[Modelos de redes y VXLAN](03-networking.md)**
- Comparación de modelos de redes para contenedores
- Análisis profundo de la tecnología VXLAN
- Redes superpuestas de Cilium
- Técnicas de optimización del rendimiento
- Mecanismos de enrutamiento (encapsulamiento frente a enrutamiento nativo)
- Redes de proveedores de nube (AWS ENI, Google Cloud)

**[IPAM y políticas de red](04-ipam-policy.md)**
- Estrategias de gestión de direcciones IP (IPAM)
- Integración de Kubernetes y Cilium IPAM
- Diseño e implementación de políticas de red
- Escenarios multiclúster
- Análisis profundo de los modos de IPAM (ámbito de clúster, ámbito de host de Kubernetes, Multi-Pool)
- IPAM de proveedores de nube (Azure IPAM, AWS ENI, GKE)
- IPAM basado en CRD

**[Redes L2-L7 y balanceo de carga](05-l2-l7-networking.md)**
- Introducción a las capas del modelo OSI (L2, L3, L4, L7)
- Funciones de Cilium específicas de cada capa
- Integración con mallas de servicios
- Arquitectura de balanceo de carga
- Configuración de la mascarada y modos de implementación
- Gestión de fragmentos IPv4

**[Seguridad y visibilidad](06-security-visibility.md)**
- Funciones de seguridad de Cilium
- Visibilidad y monitorización de la red
- Arquitectura y uso de Hubble
- Detección de amenazas en tiempo real

**[Temas avanzados y casos reales](07-advanced-topics.md)**
- Ajuste del rendimiento y solución de problemas
- Estrategias de despliegue a gran escala
- Estudios de casos de uso reales
- Hoja de ruta futura y dirección del desarrollo

**[Aspectos internos del datapath de eBPF](08-ebpf-datapath-internals.md)**
- Conjunto de programas, puntos de conexión y llamadas de cola
- Catálogo, dimensionamiento y flujo de compilación/carga de mapas BPF
- Ruta de aplicación de políticas y canalización de eventos de Hubble

**[Enrutamiento superpuesto y nativo](09-overlay-native-routing.md)**
- VXLAN/Geneve, identidad en el VNI, MTU y recorrido de paquetes
- Enrutamiento nativo, mascarada, enrutamiento del host, DSR y netkit
- Tabla de decisiones de EKS: superposición frente a ENI frente a encadenamiento de VPC CNI

**[Análisis profundo de IPAM](10-ipam-deep-dive.md)**
- Todos los modos de IPAM, cálculos de dimensionamiento y matriz de decisiones
- Multi-pool, `CiliumPodIPPool`, ENI, LB IPAM, Node IPAM
- Solución de problemas de agotamiento y cambios de API de 1.21

**[BGP, IP de balanceadores de carga y tráfico de salida](11-bgp-lb-egress-edge.md)**
- CRD de BGP Control Plane v2, anuncios e inspección
- Anuncios L2, Egress Gateway, Local Redirect Policy
- Requisitos de Gateway API y exposición de solo uso interno en EKS

**[mTLS, cifrado e identidad](12-mtls-encryption-identity.md)**
- Modelo de identidad, semántica de políticas y modo de auditoría
- Cronología de Mutual Authentication, mTLS de cargas de trabajo con ztunnel
- WireGuard, IPsec, Hubble y gestión de certificados

**[Versiones, instalación/actualización y Cluster Mesh](13-clustermesh-install-upgrade.md)**
- Matriz de funciones de 1.17 a 1.21, reglas de actualización y reversión
- Particularidades de instalación en EKS, Cluster Mesh y MCS-API

## Recursos adicionales

- [Análisis profundo de conceptos de redes](networking-concepts.md)
- [Glosario y abreviaturas](glossary.md)

## Referencias

- [Compatibilidad de Cilium 1.20 con Kubernetes](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Requisitos del sistema de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [Requisitos previos de EKS](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [Compatibilidad de AWS con CNI alternativos](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [CNI de AWS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Semántica de políticas L7 de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Proyecto Hubble](https://github.com/cilium/hubble)
- [Integración de redes y políticas de Flannel](https://github.com/flannel-io/flannel)
- [Terminología de la comparación con Calico](../calico/glossary.md)

## Cuestionario

Para poner a prueba lo que has aprendido en esta sección, prueba el [cuestionario de análisis profundo de Cilium](../../quizzes/networking/cilium/01-introduction-quiz.md).
