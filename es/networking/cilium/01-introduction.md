# Parte 1: Introducción

> **Base revisada**: Cilium 1.20.3 / Cilium CLI 0.20.1 / Hubble CLI 1.20.2. **Última actualización**: 16 de octubre de 2026

## Preparación del entorno de laboratorio

Utiliza un entorno de Kubernetes aislado y preparado. Cilium 1.20 indica que Kubernetes **1.33–1.36** está probado. Los nodos requieren Linux AMD64/AArch64 con kernel **5.10+**, o un equivalente documentado, como el kernel 4.18 con backports de RHEL 8.10. Una VM o contenedor de kind/minikube usa el kernel de su nodo/VM; el nombre del sistema operativo de la estación de trabajo, por sí solo, no demuestra compatibilidad. También se aplican los requisitos específicos de cada función.

Usa kubectl con una versión que no se aparte más de una versión menor de la del servidor de API. Instala los binarios de Cilium CLI y Hubble CLI correspondientes al sistema operativo y la arquitectura, y verifica sus sumas de comprobación como se describe en [la guía principal](README.md). Helm puede renderizar y revisar la configuración; en esta auditoría se usó Helm 3.21.3. No repitas descargas AMD64 de `latest` sin verificar ni reinstales la misma versión en cada capítulo.

### Instala una sola vez con el perfil elegido

EKS ENI, el encadenamiento de VPC CNI y las configuraciones normales de cluster-pool tienen requisitos previos distintos; consulta [la guía principal](README.md). Los valores de laboratorio que siguen corresponden a la **alternativa normal de cluster-pool IPv4**, con kube-proxy y DNS ya operativos y un único CNI ya preparado y designado como responsable de la red. No son una receta de migración para EKS. Comprueba que el CIDR de Pods no se solape con los rangos de Service, nodos o redes conectadas.

Guárdalo como `cilium-lab-values.yaml`:

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

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
kubectl --context "$CILIUM_LAB_CONTEXT" get nodes -o wide
cilium version --client

# Fresh installation only, after preparing the cluster/CNI ownership and values.
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.3 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

Si Cilium ya está instalado, inspecciona su versión y configuración y sigue el proceso de actualización del responsable de esa instalación. Los comandos de instalación/estado y las pruebas de conectividad posteriores no demuestran compatibilidad con producción; para esta auditoría no se aprovisionó ningún clúster.

## ¿Qué es Cilium?

Cilium proporciona redes, seguridad y observabilidad mediante un plano de datos eBPF de Linux y su integración con Kubernetes. Ofrece políticas de endpoint, IPAM/enrutamiento según el modo, gestión de Services y visibilidad de flujos con Hubble. La integración con Docker libnetwork se eliminó en la versión 1.20; Kubernetes, Docker y Mesos no deben presentarse como destinos de instalación actuales e intercambiables.

### Componentes y capacidades principales

| Componente / función | Función y salvedades |
| --- | --- |
| Agente de Cilium | Gestiona endpoints y el plano de datos en cada nodo; no es responsable de todas las funciones de red y del host |
| Operador de Cilium | Gestiona asignaciones, identidades y control a nivel de clúster; admite varias réplicas, con elección de líder cuando corresponde. El chart revisado usa dos réplicas de forma predeterminada |
| eBPF | Programas y mapas en puntos de conexión del kernel, sujetos al verificador y a los requisitos de cada función; el rendimiento debe medirse |
| Políticas L3/L4 y L7 | L7 necesita la ruta compatible del proxy Envoy/DNS; las políticas L7 con conocimiento de Kafka se eliminaron en 1.20, aunque las reglas L4 aún pueden regir las conexiones de Kafka |
| Reemplazo de kube-proxy | Gestión opcional de Services; DSR, Maglev y XDP tienen sus propias restricciones de configuración y topología |
| Cifrado | `encryption.type` selecciona `ipsec`, `wireguard` o `ztunnel` beta; el mTLS de cargas de trabajo con ztunnel tiene sus propios requisitos previos de incorporación, bootstrap, tráfico y políticas |
| Hubble | Observaciones de flujos de red/proxy y mapas de servicios; no ofrece automáticamente rastreo de aplicaciones de extremo a extremo |
| ClusterMesh / BGP | ClusterMesh requiere identidad, confianza y conectividad de red; BGP anuncia rutas, pero no programa el enrutamiento interno del clúster |

La relación entre componentes es la siguiente: kubelet solicita operaciones de sandbox de Pods mediante **CRI**; el entorno de ejecución de contenedores invoca el **plugin CNI** configurado; Cilium coordina la configuración de endpoints y el agente programa el plano de datos. CNI no es un salto de reenvío para cada paquete. Envoy gestiona el tráfico de proxy L7 configurado, y Hubble expone eventos de flujo por separado del scraping de métricas de Prometheus.

### Identidad de seguridad

Una identidad de seguridad es un identificador numérico asignado al **conjunto de etiquetas relevantes para la seguridad** de un endpoint, dentro del ámbito de asignación correspondiente. Estas etiquetas se filtran/configuran y pueden incluir etiquetas derivadas del namespace. Las mismas etiquetas `app`, por sí solas, no garantizan la misma identidad en distintos namespaces o clústeres. El ID numérico no es un hash permanente con significado global ni una IP de Pod. Otros tipos de endpoint también usan identidades.

## Fundamentos de redes de contenedores

La red del host comparte el namespace de red del host. Un puente conecta interfaces dentro de un host; una superposición encapsula tráfico a través de una red subyacente. El enrutamiento nativo depende de que la red subyacente pueda alcanzar las direcciones de Pod. Estos conceptos pueden coexistir y no deben confundirse con la elección de una implementación eBPF o Netfilter.

Entre las cuestiones operativas están la capacidad de direcciones, el enrutamiento/MTU, el comportamiento de los Services, las políticas de los tenants, la observabilidad y la recuperación ante fallos. El modelo de red por sí solo no determina el rendimiento ni la seguridad.

## Comprender CNI

CNI es el ecosistema de especificaciones, bibliotecas y plugins de la CNCF para configurar redes de contenedores. Los plugins intercambian configuración y resultados en JSON, y pueden delegar la asignación de direcciones a un plugin de IPAM. El contrato de configuración/eliminación de CNI es distinto de CRI, que kubelet usa para comunicarse con el entorno de ejecución de contenedores. Desde Kubernetes 1.24, kubelet ya no es responsable de las opciones de configuración eliminadas `--network-plugin`/`--cni-bin-dir`.

| Proyecto | Distinción pertinente |
| --- | --- |
| Cilium | Plano de datos eBPF para Linux, varios modos de enrutamiento/IPAM, políticas L7 asistidas por proxy y Hubble |
| Calico | Iptables/Nftables/BPF para Linux y compatibilidad con Windows HNS; WireGuard en OSS, políticas por etapas e integración L7 configurada por separado |
| Flannel | Backends de conectividad como VXLAN/host-gw/WireGuard; un controlador opcional del chart u otra implementación pueden aportar políticas |
| AWS VPC CNI | Asignación de direcciones y redes de VPC; políticas nativas en nodos Linux de EC2 compatibles y controles SG for Pods configurados por separado |
| Weave Net | El repositorio original `weaveworks/weave` está archivado; considéralo una opción histórica y comprueba por separado cualquier distribución mantenida que se proponga |

Consulta [la comparación actual](README.md) para conocer los límites de compatibilidad. No uses compatibilidad con Kubernetes sin límites definidos ni clasificaciones de rendimiento como «muy alto/alto/medio» como evidencia para un despliegue. Las mallas de servicios son integraciones opcionales, no un requisito para la conectividad normal de Pods.

## Laboratorio: una política L4 con alcance definido

Usa el contexto elegido y un namespace dedicado. Este ejemplo define una política; **no** despliega un servidor de aplicaciones ni imágenes de cliente. Prepara cargas de prueba gestionadas por un controlador con imágenes/herramientas aprobadas:

- Un Pod backend con la etiqueta `app=backend`, a la escucha en TCP 8080.
- Un Pod frontend con la etiqueta `app=frontend` y otro cliente con una etiqueta distinta; ambos deben tener un cliente de prueba adecuado.
- Interfaces de Pod normales y gestionadas, tratamiento predeterminado de etiquetas, configuración conocida de DNS/Service y ninguna otra política de autorización coincidente que invalide el aislamiento previsto.

Guarda la definición del namespace como `cilium-intro-namespace.yaml`, aplícala y, después, prepara las cargas de prueba:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cilium-intro-demo
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-namespace.yaml
```

Guarda la política siguiente como `cilium-intro-policy.yaml`:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n cilium-intro-demo --show-labels
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-policy.yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n cilium-intro-demo
```

Con esos requisitos previos y sin ninguna regla de autorización coincidente adicional, se esperan estos resultados de **ingreso normal de Pod a Pod**:

| Origen / destino | Resultado esperado |
| --- | --- |
| Frontend del mismo namespace → backend por TCP 8080 | Permitido |
| Cliente con otra etiqueta → backend por TCP 8080 | Denegado |
| Frontend → backend por otro puerto/protocolo | Esta política no lo permite |
| Misma etiqueta de aplicación desde otro namespace | Esta política no lo permite |

Verifica las conexiones permitidas y denegadas después de que se aplique la política. Otras políticas de autorización/denegación, el tráfico del host y las sondas pueden cambiar el resultado efectivo. Esta regla de ingreso no restringe la salida del frontend ni filtra métodos/rutas HTTP. Inspecciona el tráfico real y el estado de los endpoints en vez de suponer que la aceptación de la API implica que la política se aplica.

`cilium connectivity test` es un ejecutor de pruebas adicional que crea cargas de trabajo y políticas. Ejecútalo solo en un entorno de prueba revisado y con los permisos necesarios; no es un comando de solo lectura para consultar el estado. Usa `cilium connectivity perf` como ejecutor independiente de pruebas de rendimiento y conserva la versión, la topología y los resultados reales al hacer benchmarks.

## Referencias y siguientes pasos

- [Requisitos y configuración de Cilium](README.md)
- [Proyecto CNI](https://github.com/containernetworking/cni)
- [Plugins de red de Kubernetes y responsabilidad del entorno de ejecución](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Compatibilidad entre versiones del cliente de Kubernetes](https://kubernetes.io/releases/version-skew-policy/)
- [Identidades y terminología de Cilium](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/gettingstarted/terminology.rst)
- [Metadatos del repositorio original de Weave](https://api.github.com/repos/weaveworks/weave)

Continúa con [eBPF](02-ebpf.md) o comprueba lo aprendido con el [Cuestionario de introducción](../../quizzes/networking/cilium/01-introduction-quiz.md).
