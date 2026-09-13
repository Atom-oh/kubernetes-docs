# Descripción general de Cilium Service Mesh

> **Última actualización**: 11 de septiembre de 2026 · Cilium/chart 1.20.1 · CLI 0.20.0 · Hubble CLI 1.19.4

Cilium combina redes Kubernetes, políticas/balanceo eBPF y funciones opcionales de proxy de aplicación. Su integración Envoy procesa tráfico L7 seleccionado; eliminar sidecars por aplicación no elimina el proxy, requisitos del kernel ni componentes operativos.

## Arquitectura y límites de seguridad

![Comparación lógica con Istio sidecar: Cilium usa la ruta eBPF y redirige tráfico L7 seleccionado a Envoy compartido. No garantiza cifrado/rendimiento ni representa Istio ambient.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-readme-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-readme-0.html)

Envoy puede ejecutarse como proceso con el agente Cilium o como DaemonSet `cilium-envoy` gestionado por separado. La configuración renderizada habitual del chart elegido usa el DaemonSet dedicado. Ubicación y número de saltos L7 dependen de funciones/políticas; no todo paquete atraviesa Envoy.

| Componente | Rol |
|---|---|
| Agente Cilium | Ruta de datos del nodo, identidades de endpoints y aplicación de políticas |
| Operador Cilium | IPAM y otras responsabilidades de clúster/controlador según modo |
| Envoy | Políticas L7 coincidentes, ingress y Gateway API |
| Hubble | Observaciones de flujos; L7 requiere visibilidad del proxy correspondiente |
| Hubble Relay / UI | Componentes adicionales de agregación y visualización |
| SPIRE, si se configura | Infraestructura de identidad para autenticación mutua beta |

### Autenticación mutua no es cifrado automático de tráfico

Cilium 1.20.1 documenta **la autenticación mutua fuera de banda como beta e incompleta**. Su handshake de identidad basado en mTLS ocurre fuera de banda entre agentes para identidades de seguridad Cilium. No envuelve cada conexión de aplicación en el mismo modelo TLS de un proxy Istio o Linkerd.

WireGuard/IPsec son mecanismos independientes con sus modos y alcances. WireGuard no es TLS y habilitar solo SPIRE no cifra datos ni activa reglas de autenticación para todos los endpoints. La versión también documenta incompatibilidad de autenticación mutua con ClusterMesh o una solución mTLS de malla externa.

Cilium 1.20.1 ofrece además una [beta separada de cifrado transparente ztunnel](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), seleccionada con `encryption.type: ztunnel`. Proporciona mTLS TCP de cargas por inscripción de namespace; ambos extremos deben estar inscritos. Excluye ClusterMesh y Pods host-network; la guía advierte que las políticas L4 ordinarias no funcionan en esa ruta salvo sobre HBONE 15008. Es otro despliegue con requisitos CA/bootstrap propios.

Revise la [guía de seguridad](03-security.md) y el modelo/límites publicados antes de adoptarlo. Trate routing, autenticación, autorización y cifrado como requisitos distintos.

Cilium también puede proporcionar el CNI de una instalación Istio. Esa integración no hace intercambiables sus autenticaciones; revise balanceo en sockets según modo, coexistencia CNI y propiedad de políticas L7.

## Comparar capacidades y costes medidos

| Tema | Cilium | Istio | Linkerd |
|---|---|---|---|
| Plano de datos | eBPF y Envoy compartido para L7 seleccionado | Sidecar o roles ztunnel/waypoint ambient | Proxy por Pod, incluida ubicación sidecar nativa |
| Redes Pod | Proporciona CNI o se encadena con otro según modo | Necesita red Pod subyacente; su CNI redirige tráfico de malla | Necesita red Pod; CNI opcional redirige tráfico de malla |
| Política | NetworkPolicy Kubernetes/Cilium y L7 | Autorización/rutas de malla con capa de red separada | Autorización Server/ruta y routing saliente, no solo L4 |
| Gateway API | Controlador opt-in y conformidad/funciones documentadas | Roles gateway y routing de malla | Roles de rutas con padres Service/Server admitidos |
| Seguridad | Autenticación fuera de banda y cifrado separado; ztunnel mTLS beta distinto con límites | mTLS de carga más políticas | mTLS de carga más políticas |

Ningún producto tiene un ranking universal CPU/memoria/latencia independiente de carga y configuración. Las cifras fijas antiguas por nodo/Pod y el diagrama de memoria de 100 Pods no eran un benchmark atribuido y omitían componentes, nodos y carga. Compare coste incremental medido con la misma base, incluyendo agentes/proxies, controladores, telemetría e identidad.

Cilium puede ser útil si su modelo de red y L7 necesario encajan, especialmente si ya se opera allí. Evalúe migración CNI, soporte kernel/plataforma, fallo de nodo compartido, seguridad y dependencias de políticas. Ni «sin sidecars» ni «eBPF» demuestran un objetivo de latencia/coste para cargas financieras o en tiempo real.

Consulte la [comparación mantenida de mallas](../istio/comparison/01-service-mesh-comparison.md) para límites más amplios.

## Requisitos de versión y plataforma

Para la versión elegida:

- La compatibilidad Kubernetes e2e general es **1.33–1.36**. El archivo EKS CI publicado lista **1.33–1.35**, con 1.35 por defecto. Son conjuntos de evidencia distintos; combinaciones nuevas/no listadas del proveedor necesitan validación separada.
- El permisivo `kubeVersion >=1.21.0-0` del chart no es la matriz probada; versiones Kubernetes más recientes no quedan cubiertas automáticamente.
- Hosts requieren Linux AMD64/AArch64 compatible, normalmente kernel 5.10 o posterior o backport equivalente documentado. Redirección L7 y funciones avanzadas añaden requisitos kernel/módulos.
- La referencia Gateway API es **v1.6.1**. Revise CRD requeridos/opcionales y notas de actualización TLSRoute 1.20 antes de cambiarlos; no sustituya por latest sin revisión.

```bash
cilium version --client
cilium version
cilium status --wait --wait-duration 5m
kubectl -n kube-system get daemonset cilium
# For the dedicated Envoy mode selected below:
kubectl -n kube-system get daemonset cilium-envoy
```

La versión CLI y la imagen Cilium activa son datos distintos. Conserve estado completo y errores; grep de «Envoy» o «Hubble» no certifica readiness. En modo integrado puede ser normal que no exista DaemonSet Envoy dedicado.

### Opciones de instalación EKS

| Modo/plataforma | Distinción requerida |
|---|---|
| Modo AWS ENI Cilium | Cilium gestiona ENI IPAM/routing nativo; necesita plan IAM, rutas e inscripción nodo/Pod. La referencia ENI 1.20.1 documenta IPv6 Beta, pero la página EKS aún dice solo IPv4; use aquí IPv4 y verifique aparte IPv6 específico |
| AWS VPC CNI chaining | AWS mantiene interfaces/IPAM; Cilium adjunta después su ruta; evalúe limitaciones L7/IPsec avanzadas |
| EKS Fargate | No admite CNI alternativos; requiere AWS VPC CNI |
| EKS Auto Mode | No admite CNI ni plugins de políticas de red alternativos |
| EKS Hybrid Nodes | Siga la guía independiente de versiones/configuración/capacidades Cilium soportadas por AWS, no argumentos ENI EC2 |

AWS solo soporta Amazon VPC CNI para nodos EC2; otros CNI compatibles necesitan soporte operativo/del proveedor propio. No infiera el límite de soporte Hybrid Nodes de una tabla genérica Cilium.

Una línea Helm install no es un plan de migración de un clúster VPC CNI existente. Aborde acceso bootstrap API, reemplazo kube-proxy, propiedad CNI, IAM, taints de readiness y recreación de Pods previamente no gestionados mediante un procedimiento probado. La auditoría no creó clústeres ni sustituyó su CNI.

## Habilitar funciones seleccionadas

Para un Cilium ya instalado correctamente, guarde el overlay como `cilium-mesh-features.yaml`:

```yaml
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

El flag L7 admitido es `l7Proxy`; `proxy.enabled` no lo sustituye. La comprobación nativa confirmó que `proxy.enabled:false` deja L7 activo y `l7Proxy:false` lo desactiva.

```bash
set -euo pipefail
umask 077
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
# Preview only: reviewed-cni-values.yaml must describe the existing intended CNI mode.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system --kube-version 1.35.0 \
  -f reviewed-cni-values.yaml -f cilium-mesh-features.yaml \
  > cilium-mesh-rendered.yaml
```

Esto previsualiza una versión Kubernetes compatible de ejemplo y combina values CNI revisados. Inspeccione el resultado y siga la actualización admitida bajo el propietario existente. No es instalación CNI completa ni permiso para cambiar modo de red.

| Capacidad opcional | Requisitos adicionales |
|---|---|
| Gateway API | Sustitución kube-proxy, proxy L7, CRD v1.6.1 necesarios y diseño adecuado LB/host-network |
| Controlador ingress | Configuración y exposición admitidas; no todo el tráfico de malla automáticamente |
| Métricas Hubble | Familias elegidas y collector configurado; Relay/UI no crean Prometheus |
| Autenticación mutua | Revisión beta, habilitación explícita, SPIRE/almacenamiento/conectividad, política aplicable y cifrado evaluado aparte |

Para una **evaluación aislada de autenticación beta**, debe incluirse el flag raíz ausente antes:

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
```

El chart rechaza SPIRE sin `authentication.enabled:true`. El servidor SPIRE incluido usa persistencia por defecto, por lo que necesita PVC adecuado. El fragmento no establece seguridad productiva, autenticación entre clústeres ni cifrado de aplicación.

## Ejemplo de política L7 y observación

Prepare una aplicación HTTP gestionada por Cilium con `app:productpage` en `bookinfo`, y un cliente Cilium `app:frontend` en el mismo namespace. Si usa Bookinfo, despliegue todas sus dependencias; solo productpage no es la aplicación completa. Use imágenes verificadas y readiness apropiada.

La política selecciona ese endpoint y permite combinaciones cliente/método/ruta mostradas. No crea ninguna carga:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: productpage-l7
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: productpage
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: bookinfo
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/productpage$
        - method: GET
          path: ^/health$
```

Evalúe otras políticas y el default-deny esperado antes de aplicarla por su propietario. Permite dos rutas, no todos los assets o dependencias de un flujo completo de navegador. Autenticación/cifrado son independientes de este permiso L7.

```bash
# Keep this terminal running; configure the intended kube context first.
cilium hubble port-forward --port-forward 4245

# In another terminal, use the selected Hubble CLI:
hubble status --server localhost:4245
hubble observe --server localhost:4245 --namespace bookinfo --protocol http --follow
# Service-name filters are an alternative to --namespace in this CLI.
hubble observe --server localhost:4245 --to-service bookinfo/productpage
```

La CLI Hubble elegida rechaza combinar `--namespace` y `--to-service`. Use observación de namespace o prefijo de servicio con namespace. L7 necesita tráfico real coincidente y visibilidad de proxy; descartes anteriores al proxy pueden requerir inspección más amplia de flujos/drops. No observar flujos no demuestra ruta permitida, denegada ni saludable.

## Estructura documental y referencias

| Guía | Alcance |
|---|---|
| [Arquitectura](01-architecture.md) | Ruta de datos, Envoy y modelo API |
| [Gestión del tráfico](02-traffic-management.md) | Enrutamiento y balanceo |
| [Seguridad](03-security.md) | Límites de políticas, autenticación y cifrado |
| [Observabilidad](04-observability.md) | Hubble y métricas |
| [Ingress/Gateway](05-ingress-gateway.md) | Tráfico externo y Gateway API |
| [Buenas prácticas](06-best-practices.md) | Operaciones, migración y validación |

- [Compatibilidad Kubernetes publicada](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/compatibility.rst)
- [Requisitos del sistema](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)
- [Red Cilium con Istio](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/istio.rst)
- [Modos Envoy](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/proxy/envoy.rst)
- [Límites de autenticación mutua](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Requisitos Gateway API](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/gateway-api/installation.rst)
- [Requisitos ENI EKS](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/requirements-eks.rst) y [AWS VPC CNI chaining](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst)
- [CNI alternativos EKS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html) y [CNI Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium 1.20.1 ENI IPAM / IPv6 Beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst)
