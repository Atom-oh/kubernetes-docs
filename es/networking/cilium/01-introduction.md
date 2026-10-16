# Parte 1: Introducción

> **Versión de referencia revisada**: Cilium 1.20.2 / Cilium CLI 0.20.1 / Hubble CLI 1.20.2. **Última actualización**: October 15, 2026

## Configuración del entorno de laboratorio

Use un entorno de Kubernetes aislado y preparado. Cilium 1.20 enumera Kubernetes **1.33–1.36** como versiones probadas. Los nodes requieren Linux AMD64/AArch64 con kernel **5.10+**, o el equivalente documentado, como el kernel 4.18 con backport de RHEL 8.10. Una VM o contenedor de kind/minikube utiliza el kernel de su node/VM; el nombre del OS de la estación de trabajo por sí solo no establece la compatibilidad. Aún se aplican los requisitos específicos de cada característica.

Use kubectl dentro de una versión minor del servidor de API. Instale los recursos de Cilium CLI y Hubble CLI correctos para el OS/la arquitectura con verificación de checksum, como se describe en [la guía principal](README.md). Helm puede renderizar/revisar la configuración; la auditoría utilizó Helm 3.21.3. No repita descargas AMD64 de `latest` sin verificar ni reinstale la versión en cada capítulo.

### Instalar una vez con el perfil seleccionado

EKS ENI, el encadenamiento de VPC CNI y las configuraciones habituales de cluster-pool tienen requisitos previos distintos; consulte [la guía principal](README.md). Los siguientes valores de laboratorio son la **alternativa habitual de IPv4 cluster-pool**, con kube-proxy y DNS ya en funcionamiento y un propietario de CNI preparado. No son una receta de migración para EKS. Verifique que el CIDR de Pod no se superponga con los rangos de Service, node o redes conectadas.

Guarde como `cilium-lab-values.yaml`:

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
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.2 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

Si Cilium ya está instalado, inspeccione su versión/configuración y siga el proceso de actualización de su propietario. Los comandos de instalación/estado y las pruebas de conectividad posteriores no demuestran la compatibilidad con producción; no se aprovisionó ningún cluster para esta auditoría.

## ¿Qué es Cilium?

Cilium proporciona networking, seguridad y observabilidad mediante un dataplane Linux eBPF y la integración con Kubernetes. Ofrece políticas de endpoint, IPAM/routing dependientes del modo, manejo de Service y visibilidad de flujos mediante Hubble. La integración de Docker libnetwork se eliminó en 1.20; Kubernetes, Docker y Mesos no deben presentarse como objetivos de instalación actuales intercambiables.

### Componentes y capacidades principales

| Componente / característica | Función y consideraciones |
| --- | --- |
| Cilium Agent | Gestión de endpoint y dataplane por node; no controla todas las funciones de host/networking |
| Cilium Operator | Trabajo de asignación/identidad/controlador a nivel de cluster; se admiten varias réplicas, con elección de líder cuando corresponde. El chart revisado usa dos réplicas de forma predeterminada |
| eBPF | Programas/maps en hooks del kernel, sujetos a requisitos de verificación y características; el rendimiento debe medirse |
| Política L3/L4 y L7 | L7 necesita la ruta de proxy Envoy/DNS compatible; la política L7 compatible con Kafka se eliminó en 1.20, mientras que las reglas L4 aún pueden controlar conexiones Kafka |
| Reemplazo de kube-proxy | Manejo de Service opcional; DSR, Maglev y XDP tienen sus propias restricciones de configuración/topología |
| Cifrado | `encryption.type` selecciona `ipsec`, `wireguard` o `ztunnel` beta; mTLS de workload de ztunnel tiene sus propios requisitos previos de inscripción, bootstrap, tráfico y política |
| Hubble | Observaciones de flujo de red/proxy y mapas de Service, no tracing automático integral de aplicaciones |
| ClusterMesh / BGP | ClusterMesh necesita identidad, confianza y alcance de red; BGP anuncia rutas, pero no programa el routing interno del cluster |

La relación entre componentes es: kubelet solicita operaciones de sandbox de Pod mediante **CRI**; el runtime de contenedor invoca el **CNI plugin** configurado; Cilium coordina la configuración del endpoint y el agent programa el dataplane. CNI no es un salto de forwarding por paquete. Envoy gestiona el tráfico de proxy L7 configurado, y Hubble expone eventos de flujo de forma separada del scraping de métricas de Prometheus.

### Identidad de seguridad

Una identidad de seguridad es un identificador numérico asignado para el **conjunto de labels relevante para la seguridad** de un endpoint, dentro del ámbito de asignación pertinente. Estos labels se filtran/configuran y pueden incluir labels derivados de namespace. Los mismos labels de `app` por sí solos no garantizan la misma identidad entre namespaces o clusters. El ID numérico no es un hash permanente con significado global ni una IP de Pod. Otros tipos de endpoint también usan identidades.

## Fundamentos de networking de contenedores

El networking de host comparte el namespace de red del host. Un bridge conecta interfaces en un host; un overlay encapsula el tráfico a través de un underlay. El routing nativo se basa en que el underlay alcance direcciones de Pod. Estos conceptos pueden coexistir y no deben confundirse con elegir una implementación eBPF frente a Netfilter.

Las preguntas operativas incluyen capacidad de direcciones, routing/MTU, comportamiento de Service, política de tenant, observabilidad y recuperación ante fallos. Un modelo de red por sí solo no determina el rendimiento ni la seguridad.

## Comprender CNI

CNI es el ecosistema de especificación/biblioteca/plugins de CNCF para la configuración de red de contenedores. Los plugins intercambian configuración/resultados en JSON y pueden delegar la asignación de direcciones a un plugin IPAM. El contrato de configuración/eliminación de CNI es distinto de CRI, que kubelet utiliza para comunicarse con el runtime de contenedor. Desde Kubernetes 1.24, kubelet ya no controla los flags de configuración `--network-plugin`/`--cni-bin-dir` eliminados.

| Proyecto | Distinción relevante |
| --- | --- |
| Cilium | Dataplane Linux eBPF, varios modos de routing/IPAM, política L7 asistida por proxy y Hubble |
| Calico | Linux Iptables/Nftables/BPF y Windows HNS compatible; OSS WireGuard, política por etapas e integración L7 configurada por separado |
| Flannel | Backends de conectividad como VXLAN/host-gw/WireGuard; la política puede proporcionarse mediante su controlador de chart opcional u otra implementación |
| AWS VPC CNI | Asignación de direcciones/networking de VPC; política nativa en nodes EC2 Linux compatibles y controles de SG-for-Pods independientes |
| Weave Net | El repositorio original `weaveworks/weave` está archivado; trátelo como una opción histórica y compruebe por separado cualquier distribución mantenida propuesta |

Consulte [la comparación actual](README.md) para conocer los límites de soporte. No use una compatibilidad de Kubernetes sin límites ni clasificaciones de rendimiento «muy alto/alto/medio» como evidencia de despliegue. Los service meshes son integraciones opcionales, no un requisito previo para el networking habitual de Pod.

## Laboratorio: una política L4 acotada

Use el contexto elegido y un namespace dedicado. Este ejemplo define una política; **no** despliega un servidor de aplicación ni imágenes de cliente. Prepare workloads de prueba gestionados por controlador con imágenes/herramientas aprobadas:

- Un Pod backend con el label `app=backend`, que escucha en TCP 8080.
- Un Pod frontend con el label `app=frontend` y otro cliente con un label diferente, ambos con un cliente de prueba adecuado.
- Interfaces de Pod gestionadas habituales, manejo de labels predeterminado, configuración conocida de DNS/Service y ninguna otra política allow coincidente que invalide el aislamiento previsto.

Guarde la definición de namespace como `cilium-intro-namespace.yaml`, aplíquela y, después, prepare los workloads de prueba:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cilium-intro-demo
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-namespace.yaml
```

Guarde la política siguiente como `cilium-intro-policy.yaml`:

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

Con esos requisitos previos y sin allow adicionales coincidentes, los resultados esperados de **ingress habitual de Pod a Pod** son:

| Origen / destino | Resultado esperado |
| --- | --- |
| Frontend del mismo namespace → backend TCP 8080 | Permitido |
| Otro label de cliente → backend TCP 8080 | Denegado |
| Frontend → backend en otro puerto/protocolo | No permitido por esta política |
| El mismo label de app desde otro namespace | No permitido por esta política |

Verifique las conexiones positivas y negativas después de que la política se materialice. Otras políticas allow/deny, tráfico de host y probes pueden cambiar el resultado efectivo. Esta regla de ingress no restringe el egress de frontend ni proporciona filtrado por método/ruta HTTP. Inspeccione el tráfico real y el estado del endpoint en lugar de asumir que la aceptación de la API equivale a la aplicación de la política.

`cilium connectivity test` es un ejecutor de pruebas adicional que crea workloads y políticas. Ejecútelo solo en un entorno de prueba revisado con los permisos necesarios; no es un comando de estado de solo lectura. Use `cilium connectivity perf` para el ejecutor de rendimiento independiente y conserve la versión/topología/resultados reales al realizar benchmarks.

## Referencias y próximos pasos

- [Requisitos y configuración de Cilium](README.md)
- [Proyecto CNI](https://github.com/containernetworking/cni)
- [Plugins de red y propiedad del runtime de Kubernetes](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Desfase de versiones de cliente de Kubernetes](https://kubernetes.io/releases/version-skew-policy/)
- [Identidades y terminología de Cilium](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/gettingstarted/terminology.rst)
- [Metadatos del repositorio original de Weave](https://api.github.com/repos/weaveworks/weave)

Continúe con [eBPF](02-ebpf.md) o pruebe sus conocimientos con el [Cuestionario de introducción](../../quizzes/networking/cilium/01-introduction-quiz.md).
