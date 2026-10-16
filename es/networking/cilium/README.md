# Análisis detallado de Cilium: el futuro de las redes Cloud Native

## Descripción general y línea base revisada

Esta sección cubre las redes, las políticas y la observabilidad de Cilium. Los ejemplos se revisaron con **Cilium/Helm chart 1.20.2**, Cilium CLI **0.20.1** y Hubble CLI **1.20.2**. La página de compatibilidad de Kubernetes de Cilium 1.20 enumera **1.33–1.36** como versiones probadas; una versión upstream 1.37 no extiende esa matriz automáticamente. Los hosts compatibles son Linux AMD64/AArch64 con kernel **5.10+**, o el equivalente documentado de la distribución, como el kernel 4.18 con backports de RHEL 8.10. Las características individuales tienen requisitos adicionales.

> **Última actualización**: October 15, 2026

### Notas históricas de versiones

Las fechas siguientes son fechas de publicación de GitHub en UTC y describen esas versiones, no las versiones de instalación actuales fijadas. Los backports de características difieren entre líneas de versiones.

| Fecha | Versión | Aspectos destacados verificados |
| --- | --- | --- |
| July 14, 2026 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | Primera versión candidata de 1.20 |
| July 16, 2026 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | La configuración de registros de acceso de Gateway aparece para 1.19.6/1.18.12; las correcciones de afinidad de política de reinicio y ClusterMesh citadas aquí aparecen en 1.19.6, no en las tres versiones |
| July 21, 2026 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | Segunda versión candidata de 1.20 |
| July 29, 2026 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | Versión GA; cambios seleccionados a continuación |
| August 3, 2026 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | Prelanzamiento del siguiente ciclo, no la línea base de despliegue de esta guía |
| August 18, 2026 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | Documentación y correcciones de errores de ClusterMesh, incluidos el manejo de reinicio/política CIDR |
| August 18, 2026 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | Incluye correcciones de tiempos de interfaz ENI, Service/LB y otras |
| August 18, 2026 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | Compatibilidad de firewall de host VRRP/IGMP y correcciones relacionadas |
| September 9, 2026 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | Prelanzamiento; su registro de cambios cubre de pre.0 a pre.2 porque **1.21.0-pre.1 nunca se publicó** |
| September 16, 2026 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | Línea base estable actual de esta guía; correcciones de delegación de prefijos ENI y CIDR de VPC secundaria, correcciones de ClusterMesh y la corrección para actualizar clústeres creados en v1.15 o anterior (versión de CRD `CiliumNodeConfig v2alpha1`) |
| September 16, 2026 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | Versiones de parche de las líneas antiguas compatibles |
| October 2, 2026 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | Último prelanzamiento 1.21; **1.21 solo está en prelanzamiento (aún sin GA)** y los elementos marcados como 1.21 en esta guía pueden cambiar |

El anuncio de 1.20.0 informa **2,660+ nuevos commits**, respaldados por una **comunidad de 1,100+ colaboradores**. Lo último es el tamaño de la comunidad, no un recuento de autores de esta versión. Los aspectos destacados incluyen:

- Gateway API **1.6.1**, TCPRoute/UDPRoute, BackendTLSPolicy, ListenerSets, ExternalAuth y compatibilidad con CORS, sujetos a la configuración y madurez de API de cada característica.
- Plugins de datapath y `bpf.datapathMode=auto` opcional; el valor predeterminado anunciado sigue siendo veth. Los clústeres dual-stack pueden configurar una dirección de gateway de salida IPv6.
- **Beta** de IPv6 ENI IPAM y migración de cluster-pool a multi-pool sin reconstruir el clúster. La migración in situ no garantiza que no haya interrupción.
- Sugerencias de distribución de tráfico, backends Maglev ponderados e integración MCS estable; compatibilidad con Kubernetes ClusterNetworkPolicy e identidad de workload basada en ztunnel en **beta**.
- Una reducción informada del binario `cilium-cni` de aproximadamente **77 MB a 16 MB**. Las mejoras de ADS/Delta xDS están en el anuncio de 1.20; no las atribuya a las notas de parche de 1.18.13. Estas son afirmaciones de versiones upstream, no mediciones repetidas en esta auditoría.

Revise las [notas de actualización de 1.20](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes) para Mutual Authentication (**obsoleta en 1.20**, eliminada en el prelanzamiento 1.21), las extensiones Envoy Go eliminadas/reemplazadas, las políticas con reconocimiento de Kafka, la antigua API CiliumNodeConfig, la integración de libnetwork y los cambios de configuración CNI personalizada.

### Aviso de seguridad de NetworkPolicy

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) tiene una fecha de publicación del aviso del proyecto de **July 6, 2026**. La API del proyecto y la API global de avisos de GitHub exponen fechas diferentes: la última registra September 3. Use la fecha de divulgación del proyecto para esta cronología de versiones; la fecha del registro global no es una versión de corrección posterior. Afecta a **1.19.0–1.19.4** bajo las condiciones de nombre de clúster personalizado del aviso: un peer estándar de Kubernetes NetworkPolicy que contiene solo `ipBlock` puede permitir involuntariamente ingress desde workloads en el namespace del Pod seleccionado. **1.19.5** corrige este problema; use una versión actual con parches apropiada para el despliegue. El aviso indica que CiliumNetworkPolicy/ClusterwideNetworkPolicy y las versiones anteriores a 1.19.0 no se ven afectadas por este error en particular.

## Introducción

Cilium proporciona redes, seguridad y observabilidad para entornos Kubernetes Linux compatibles. El enrutamiento, IPAM, el cifrado y el manejo de Service son opciones independientes; seleccionar eBPF por sí solo no establece cada característica ni una garantía de rendimiento. La antigua integración Docker libnetwork se eliminó en 1.20, por lo que Docker/Mesos no debe aparecer aquí como objetivos de instalación actuales intercambiables.

### eBPF y capacidades principales

El kernel verifica los programas eBPF antes de cargarlos y puede compilarlos con JIT para ejecutarlos en hooks compatibles. Esto permite el procesamiento de paquetes y la observabilidad sin un módulo personalizado del kernel; el verificador no prueba la corrección de la aplicación ni de las políticas. El rendimiento real, la latencia y la memoria dependen de los programas, la plataforma y el workload.

Cilium ofrece política L3/L4, política L7 mediante integración con proxy Envoy/DNS, WireGuard/IPsec opcionales, balanceo de carga de Service, visibilidad de flujos Hubble, ClusterMesh y anuncio BGP. La aceleración XDP es opcional y depende del dispositivo/configuración. Las características L7 pueden usar Envoy por nodo; la identidad de workload mediante ztunnel tiene configuración beta independiente. Instalar solo el agente no habilita todo el comportamiento de mesh, cifrado o múltiples clústeres.

### Comparación con otros proyectos de redes

| Proyecto | Conectividad / IPAM | Política y capacidades relacionadas |
| --- | --- | --- |
| Cilium | Enrutamiento nativo o overlay; modos IPAM que incluyen ENI de cloud | Plano de datos eBPF, políticas Cilium/Kubernetes, integración L7, Hubble y cifrado opcional |
| Calico | Perfiles nativos/IPIP/VXLAN con IPAM de Calico o externo | Linux Iptables/Nftables/BPF, Windows HNS compatible; OSS WireGuard, política por etapas e integración L7 independiente |
| Flannel | Conectividad Pod mediante backends seleccionados como VXLAN/host-gw/WireGuard | El daemon de enrutamiento no aplica NetworkPolicy; su chart puede desplegar el controlador de network-policy de SIGs con `netpol.enabled`, o puede combinarse con otra implementación de políticas |
| AWS VPC CNI | Asignación de direcciones/redes VPC ENI | Política de red nativa en nodos EC2 Linux compatibles y funcionalidad SG-for-Pods independiente; EKS Auto Mode es una implementación administrada diferente |

Un modo de enrutamiento no pertenece a la misma categoría que una implementación de procesamiento de paquetes. Calico no se limita a iptables/IPVS, Flannel puede usar un backend cifrado y la política de AWS no es sinónimo de grupos de seguridad. Los service meshes son capas opcionales y la conectividad VPC entre clústeres no está restringida a Transit Gateway. Use un workload medido y una matriz de compatibilidad explícita en lugar de clasificaciones universales de rendimiento.

## Arquitectura

El **Kubernetes API server** almacena recursos de Kubernetes/Cilium. Los agentes Cilium observan el estado pertinente y programan el dataplane de cada nodo; el Cilium Operator maneja responsabilidades a nivel de clúster, como el IPAM seleccionado y el trabajo de identidad/controlador. No hay un despliegue obligatorio independiente de “Cilium API Server” para todo el clúster en esta arquitectura básica. Los agentes tienen API locales, y el API server opcional de ClusterMesh tiene un propósito distinto.

| Componente | Función |
| --- | --- |
| Cilium Agent | Gestión local al nodo de endpoint, política, estado de enrutamiento/Service y eBPF |
| Cilium Operator | Conciliación a nivel de clúster y trabajo de asignación/controlador dependiente del modo |
| Envoy | Proxy de espacio de usuario para política L7 habilitada, ingress/Gateway y características relacionadas |
| Hubble server | API de flujos local al nodo integrada con el agente |
| Hubble Relay / UI | Agrega flujos de datos / muestra mapas de Service y flujos |
| Prometheus metrics endpoints | Recopilación de estadísticas independiente; Relay/UI no es la canalización de scraping de métricas |
| cilium / cilium-dbg / hubble | CLI de gestión del clúster / diagnósticos del agente / cliente de flujos respectivamente |

### Redes y rutas de paquetes

El enrutamiento nativo necesita un underlay accesible; el tunneling usa VXLAN o Geneve. AWS ENI y Azure IPAM son opciones de asignación/integración con sus propios requisitos de plataforma. El BGP Control Plane de Cilium anuncia accesibilidad a los routers y **no programa el datapath ni proporciona enrutamiento interno del clúster**.

No existe una secuencia universal XDP→TC→Pod. El balanceo de carga de socket puede actuar antes de que existan paquetes, los hooks TC/netkit dependen del datapath, XDP opcional acelera el tráfico seleccionado y el tráfico L7 puede pasar por Envoy. El tráfico de retorno también depende de las opciones NAT, conntrack y DSR. Consulte los capítulos de redes y eBPF para el perfil elegido.

## Integración con Amazon EKS

Elija el perfil de red y computación real antes de instalar nada. El nombre/versión de addon de ejemplo `cilium` / `v1.17.0-eksbuild.1` no era una distribución de AWS verificada y no es un comando de instalación aquí. Inspeccione el catálogo de add-ons, publisher, licencia y tipos de computación compatibles reales de la Region si considera un add-on de proveedor empaquetado.

| Perfil EKS | Qué verificar |
| --- | --- |
| Nodos EC2 ordinarios, Cilium ENI reemplaza VPC CNI | CNI administrado upstream/por partner; el CNI EC2 compatible de AWS es VPC CNI. Planifique propiedad de CNI, IAM, direccionamiento, rutas, bootstrap y migración de nodos |
| Nodos EC2 ordinarios, chaining AWS VPC CNI | VPC CNI posee las interfaces/IPAM; Cilium adjunta su dataplane después. Los Pods existentes necesitan recrearse y L7/IPsec tienen limitaciones documentadas |
| Hybrid Nodes | Siga la guía CNI especializada de AWS y la matriz de compilaciones de Cilium mantenida por AWS; upstream 1.20.2 no es automáticamente la compilación de AWS compatible |
| Auto Mode | Los plugins CNI/política alternativos no son compatibles; use las características administradas NodeClass/redes |
| Fargate | La instalación de CNI/DaemonSet alternativo no es compatible |
| Windows | Los requisitos del agente Cilium son Linux; no aplique esta receta a workers Windows |

La página general de CNI alternativo de AWS y la guía especializada Hybrid difieren en su redacción de la compatibilidad de Calico; que un ejemplo cambie de repositorio no establece la finalización del soporte. Para Hybrid Nodes, confirme la distribución exacta, el conjunto de capacidades y el propietario del soporte. Para Auto Mode, las redes CoreDNS/sistema locales al nodo también son diferentes de la configuración EC2 ordinaria de esta guía; los nodos mixtos que no son Auto aún necesitan el Deployment DNS tradicional.

### Clúster EC2 preparado con Cilium ENI

Estos son **valores Helm de Cilium para un clúster EC2 IPv4 preparado**, no una receta completa de creación de clúster o migración in situ. Antes de usarlos:

1. Elija una versión de EKS/Kubernetes y AMI Linux compatibles, y establezca un propietario de CNI. No elimine `aws-node` de un clúster de workload existente como atajo.
2. Prepare los taints/la programación de nodos para que los workloads esperen hasta que Cilium gestione el nodo. La guía upstream de EKS usa `node.cilium.io/agent-not-ready=true:NoExecute`; evalúe los efectos de expulsión y bootstrap en el ciclo de vida real del nodo.
3. Prepare capacidad de subred, cuotas ENI/grupos de seguridad, acceso a metadatos de nodo y los permisos EC2 requeridos por el operador. El ARN de rol siguiente es un marcador de posición para un rol de **cilium-operator ServiceAccount** con confianza configurada correctamente, no un rol creado por el archivo de valores.
4. Conserve kube-proxy y DNS operativos para este ejemplo `kubeProxyReplacement: false`. Para el modo de reemplazo, siga los requisitos independientes de API directa/bootstrap-DNS. Seleccione max-Pods según la capacidad real de instancia/IPAM, no un 110 universal.

Guarde como `cilium-eni-values.yaml` y reemplace las opciones de rol/interfaz con valores revisados:

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
helm template cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# After preparing the cluster and reviewing the rendered configuration:
helm install cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-eni-values.yaml
```

Gestione estos ajustes mediante el propietario de la instalación. Un `cilium-config` de reemplazo que contenga solo unas pocas claves puede eliminar otros ajustes requeridos; el antiguo valor `tunnel=disabled` se reemplaza por `routingMode: native`. La asignación/permisos ENI y el comportamiento SNAT aún requieren validación en tiempo de ejecución; un renderizado correcto no prueba que las redes EC2 se puedan usar.

**Calificación de IPv6:** la referencia IPAM ENI 1.20.2 describe IPv6 como beta, mientras que su página de requisitos previos de EKS aún indica integración ENI solo para IPv4. Esta guía mantiene un ejemplo IPv4 y registra esa inconsistencia de documentación en lugar de considerar cualquiera de las declaraciones como prueba de compatibilidad de EKS IPv6 en producción. Revise los requisitos actuales de subred ENI/dual-stack antes de un diseño IPv6 independiente.

### Alternativa de chaining VPC CNI

La guía upstream de chaining requiere VPC CNI 1.11.2+ y documenta este perfil:

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

Úselo como una **configuración diferente**, no como una superposición sobre los valores de reemplazo ENI. VPC CNI sigue siendo el asignador. Actualice el add-on administrado real mediante su propietario en vez de aplicar un DaemonSet upstream histórico. Evite motores de política que compitan en los mismos endpoints. Los Pods existentes no se adjuntan retroactivamente a Cilium cuando cambia la cadena CNI; recréelos bajo un rollout planificado y verifique la gestión de endpoints. El chaining tiene limitaciones documentadas de política L7/IPsec, por lo que no asuma que todos los ejemplos posteriores de esta página funcionan en ese perfil.

### ClusterMesh

ClusterMesh necesita identidades de clúster únicas, versiones compatibles, redes Pod accesibles/sin solapamiento, conectividad de API autenticada y un modelo de exposición apropiado. Un Service LoadBalancer puede crear recursos de cloud y necesita un diseño deliberado de red/seguridad. Crear dos endpoints públicos no es suficiente para conectar clústeres de forma segura. Siga la [guía de ClusterMesh](13-clustermesh-install-upgrade.md) mantenida y el capítulo avanzado para la topología elegida.

## Instalación y configuración

### Herramientas de cliente

Use los recursos oficiales adecuados de Cilium CLI 0.20.1 y Hubble CLI 1.20.2 para el SO/arquitectura de la estación de trabajo, y verifique las sumas de comprobación proporcionadas antes de extraerlos. Linux ARM64 y AMD64 difieren; macOS usa los recursos Darwin correspondientes. Las versiones CLI son independientes de la versión del agente/chart Cilium. Consulte la [guía de instalación de CLI verificada](../../service-mesh/cilium-service-mesh/README.md).

```bash
cilium version --client
hubble version
```

### Ejemplo no cloud de Cluster-Pool

La siguiente **alternativa** es para un clúster Linux ordinario preparado con kube-proxy y DNS ya operativos. Asegúrese de que el rango Pod de ejemplo `10.244.0.0/16` sea compatible con el clúster y no se solape con los rangos de Service, nodo, VPC o red conectada. No use esta configuración de pool para el modo ENI.

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

Guarde como `cilium-values.yaml`, renderice el chart fijado y luego instale solo en el clúster preparado:

```bash
helm template cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

Para una versión existente, use su proceso de actualización/GitOps, conserve los valores administrados y siga el procedimiento de actualización específico de la versión. Los ejemplos repetidos de `cilium install` no son una forma general de cambiar ajustes individuales.

| Elección | Configuración y requisito previo actuales |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` más `tunnelProtocol`; permita la encapsulación elegida y establezca MTU para la ruta |
| Enrutamiento nativo | `routingMode: native`; el underlay debe enrutar las direcciones Pod. `autoDirectNodeRoutes` necesita conectividad directa adecuada, no enrutamiento arbitrario entre múltiples subredes |
| Reemplazo de kube-proxy | `kubeProxyReplacement: true` o `false`, no el antiguo `strict`; el reemplazo requiere `k8sServiceHost`/`k8sServicePort` accesibles y el plan de bootstrap documentado |
| WireGuard | Habilite el modo de cifrado compatible tras comprobar el kernel/plataforma y las rutas de peers; no cifra automáticamente todas las rutas de tráfico posibles |
| IPsec | Requiere el Secret de clave documentado, distribución/rotación de claves y modo compatible; el flag Helm de habilitación por sí solo es incompleto |
| XDP/DSR/BBR | Opciones independientes que dependen del dispositivo/kernel/topología, no un preset de instalación universal |

## Políticas de red

Kubernetes `networking.k8s.io/v1` NetworkPolicy y las políticas Cilium `cilium.io/v2` son API distintas. Múltiples políticas allow pueden combinarse. Estos ejemplos usan **namespaces de prueba preparados independientes** para que el allow L4 no omita silenciosamente la restricción L7. Inspeccione todas las políticas que seleccionan los endpoints reales antes de sacar conclusiones.

### Ejemplo L4

En `cilium-l4-demo`, esto selecciona Pods backend y permite ingress desde Pods frontend del mismo namespace en TCP 8080:

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

En un `cilium-l7-demo` independiente, esto selecciona Pods backend y restringe HTTP de texto sin cifrar en TCP 8080 al método/ruta indicados desde Pods frontend de ese namespace. La compatibilidad con proxy L7 debe estar disponible en el modo CNI elegido; HTTP cifrado no se inspecciona automáticamente sin una configuración de terminación compatible.

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

No agregue un allow L4 sin restricciones coincidente para los mismos peers/puerto: Cilium documenta que tal allow elimina el efecto de las restricciones L7 más limitadas. La denegación L7 puede devolver HTTP 403 en vez de una caída de paquete. Pruebe solicitudes GET permitidas y métodos/rutas denegados con identidades de endpoint reales.

### Ejemplo DNS/FQDN

En `cilium-dns-demo`, esto permite consultas DNS a Pods CoreDNS ordinarios y TCP 443 a direcciones aprendidas para `api.example.com`. El dominio es un ejemplo; reemplácelo por un destino aprobado. Se omite el comodín amplio `*.amazonaws.com` porque no es un límite de cuenta/recurso.

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

El comodín DNS permite consultas al resolver seleccionado, no conexiones a cada dirección devuelta. Aun así puede transportar nombres DNS arbitrarios; restrinja los nombres de consulta cuando se requiera, teniendo en cuenta los sufijos de búsqueda DNS. NodeLocal DNS o un resolver diferente necesita la selección de destino correcta. La política FQDN es autorización de IP derivada de DNS, no verificación de hostname TLS ni autorización de URL HTTP; las IP compartidas y TLS/autenticación de aplicaciones siguen siendo importantes.

## Observabilidad con Hubble

Los valores de cluster-pool anteriores habilitan Relay/UI y métricas de componentes. Para una instalación existente, aplique los valores Hubble previstos mediante su propietario de configuración; `cilium hubble enable --ui` es un comando de conveniencia compatible, pero `cilium hubble enable --metrics=...` no es un flag CLI compatible de 0.20.1. Configure `hubble.metrics.enabled` en valores Helm en su lugar. No habilite los handlers heredados `http` y `httpV2` juntos.

Mantenga el port-forward de Relay en ejecución en una terminal:

```bash
cilium hubble port-forward --port-forward 4245
```

En otra terminal con Hubble CLI instalado:

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

Este ejemplo local asume la configuración predeterminada del servidor Relay; un Relay con TLS habilitado necesita la confianza/autenticación de cliente correspondiente. Los eventos HTTP requieren que el tráfico atraviese el proxy L7 configurado. `DROPPED` es un veredicto del datapath, no toda solicitud de aplicación fallida. Use `cilium hubble ui` para el port-forward de UI y configure por separado el descubrimiento de objetivos de Prometheus para las métricas. El streaming de flujos Hubble no es por sí mismo trazado de aplicaciones distribuido.

## Pruebas y operaciones

Los comandos de conectividad/rendimiento crean workloads de prueba y pueden cambiar políticas o generar tráfico considerable. Use un namespace/entorno de prueba y permisos revisados; esta auditoría no los ejecutó contra un clúster.

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

El subcomando de rendimiento es `cilium connectivity perf`; `connectivity test --test=performance` solo proporciona un filtro de nombre de prueba y no es el ejecutor de rendimiento. Registre versiones de software, topología, tráfico y resultados sin procesar antes de comparar rendimiento/latencia.

Para la inspección, distinga la CLI de gestión de **`cilium-dbg` del lado del agente**:

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

`cilium endpoint list`, `cilium bpf maps list` y `cilium metrics list` no son comandos equivalentes en la CLI de gestión. `cilium sysdump` puede recopilar material de diagnóstico; proteja los datos de infraestructura/registros resultantes. Un agente Ready o un scraping exitoso no sustituye a las pruebas de aplicación y de política negativa.

### Prioridades operativas

- Mida antes de habilitar la preasignación de mapas, XDP, DSR, BBR o un patrón de dispositivo fijo. Estos consumen recursos o cambian las rutas de paquetes y requieren comprobaciones específicas de cada característica.
- Introduzca default-deny en un ámbito seleccionado con dependencias DNS, API, identidad y aplicación explícitamente permitidas. Compruebe Pods nuevos y transiciones de actualización, además de conexiones establecidas.
- Mantenga el cifrado, la rotación de certificados/claves, la aplicación de políticas y la observabilidad como comprobaciones de aceptación independientes. Conserve una ruta de gestión/recuperación utilizable.
- Revise la matriz de plataforma actual y la ruta de actualización compatible. Los anuncios históricos de versiones no establecen la compatibilidad de despliegue actual.

## Índice del análisis detallado

**[Introducción a Cilium y conceptos básicos](01-introduction.md)**
- Descripción general e historia de Cilium
- Fundamentos de redes de contenedores
- Comprensión de CNI (Container Network Interface)
- Características diferenciadoras de Cilium

**[Análisis detallado de la tecnología eBPF](02-ebpf.md)**
- Introducción a la tecnología eBPF e historia
- Cómo funciona eBPF dentro del kernel
- Tipos de programas y mapas eBPF
- Uso de eBPF en Cilium

**[Modelos de redes y VXLAN](03-networking.md)**
- Comparación de modelos de redes de contenedores
- Análisis detallado de la tecnología VXLAN
- Redes overlay de Cilium
- Técnicas de optimización de rendimiento
- Mecanismos de enrutamiento (encapsulación frente a enrutamiento nativo)
- Redes de proveedores cloud (AWS ENI, Google Cloud)

**[IPAM y políticas de red](04-ipam-policy.md)**
- Estrategias de gestión de direcciones IP (IPAM)
- Integración IPAM de Kubernetes y Cilium
- Diseño e implementación de políticas de red
- Escenarios de múltiples clústeres
- Análisis detallado de modos IPAM (ámbito de clúster, ámbito de host Kubernetes, Multi-Pool)
- IPAM de proveedor cloud (Azure IPAM, AWS ENI, GKE)
- IPAM basado en CRD

**[Redes L2-L7 y balanceo de carga](05-l2-l7-networking.md)**
- Comprensión de las capas del modelo OSI (L2, L3, L4, L7)
- Características específicas por capa de Cilium
- Integración de Service Mesh
- Arquitectura de balanceo de carga
- Configuración de masquerading y modos de implementación
- Manejo de fragmentos IPv4

**[Seguridad y visibilidad](06-security-visibility.md)**
- Características de seguridad de Cilium
- Visibilidad y monitorización de red
- Arquitectura y uso de Hubble
- Detección de amenazas en tiempo real

**[Temas avanzados y casos reales](07-advanced-topics.md)**
- Ajuste de rendimiento y solución de problemas
- Estrategias de despliegue a gran escala
- Estudios de casos de uso reales
- Hoja de ruta futura y dirección del desarrollo

**[Aspectos internos del datapath eBPF](08-ebpf-datapath-internals.md)**
- Conjunto de programas, puntos de adjunción y tail calls
- Catálogo de mapas BPF, dimensionamiento y flujo de compilación/carga
- Ruta de aplicación de políticas y canalización de eventos Hubble

**[Enrutamiento overlay y nativo](09-overlay-native-routing.md)**
- VXLAN/Geneve, identidad en VNI, MTU y recorridos de paquetes
- Enrutamiento nativo, masquerading, enrutamiento de host, DSR y netkit
- Tabla de decisiones EKS: overlay frente a ENI frente a chaining VPC CNI

**[Análisis detallado de IPAM](10-ipam-deep-dive.md)**
- Todos los modos IPAM, cálculos de dimensionamiento y matriz de decisiones
- Multi-pool, `CiliumPodIPPool`, ENI, LB IPAM, Node IPAM
- Solución de problemas de agotamiento y cambios de API 1.21

**[BGP, IP de Load Balancer y salida](11-bgp-lb-egress-edge.md)**
- CRD BGP Control Plane v2, anuncio e inspección
- Anuncios L2, Egress Gateway, Local Redirect Policy
- Requisitos de Gateway API y exposición de EKS solo interna

**[mTLS, cifrado e identidad](12-mtls-encryption-identity.md)**
- Modelo de identidad, semántica de políticas y modo de auditoría
- Cronología de Mutual Authentication, mTLS de workload ztunnel
- WireGuard, IPsec, Hubble y gestión de certificados

**[Versiones, instalación/actualización y Cluster Mesh](13-clustermesh-install-upgrade.md)**
- Matriz de características 1.17-1.21, reglas de actualización y rollback
- Especificidades de instalación EKS, Cluster Mesh y MCS-API

## Recursos adicionales

- [Análisis detallado de conceptos de redes](networking-concepts.md)
- [Glosario y abreviaturas](glossary.md)

## Referencias

- [Compatibilidad de Kubernetes con Cilium 1.20](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/compatibility.rst)
- [Requisitos del sistema de Cilium](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [Requisitos previos de EKS](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [Compatibilidad de CNI alternativo de AWS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [CNI de AWS Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Semántica de políticas L7 de Cilium](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer7.rst)
- [Proyecto Hubble](https://github.com/cilium/hubble)
- [Integración de redes y políticas de Flannel](https://github.com/flannel-io/flannel)
- [Terminología de comparación de Calico](../calico/glossary.md)

## Cuestionario

Para poner a prueba lo aprendido en esta sección, pruebe el [Cuestionario de análisis detallado de Cilium](../../quizzes/networking/cilium/01-introduction-quiz.md).