# Linkerd

> **Última actualización**: 21 de noviembre de 2026 · Ejemplos públicos de CLI verificados con edge-26.10.1

El proyecto upstream publica artefactos edge; las distribuciones estables y su ciclo de soporte provienen de los proveedores. Linkerd 2.20 es un hito de funcionalidades, no una cadena de versión universal para la CLI descargada. Elige una distribución/versión exacta y comprueba su compatibilidad con Kubernetes y Gateway API. El ejemplo público actual es edge-26.10.1 (proxy v2.370.0), publicado el 5 de octubre de 2026. En edge-26.9.1 se corrigió la aceptación de remote-credential exec-auth-provider en multicluster y el manejo de conflictos de IP de destino que se pueden reintentar. Consulta la [versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.1) y el [modelo de versiones](https://linkerd.io/releases/).

Las siguientes entradas conservan el contexto histórico de las versiones. La versión máxima de Kubernetes probada con edge-26.8.2 no amplía automáticamente la matriz de compatibilidad de una distribución estable de un proveedor.

### Actualización de octubre de 2026: edge-26.10.2

La versión edge-26.10.2, publicada el 29 de octubre de 2026, aumenta la ventana de conexión gRPC HTTP/2 del controlador de políticas para evitar los mensajes GOAWAY, garantiza que los clientes que se conectan al servidor de la API tap proporcionen TLS, incluye proxy v2.372.0, actualiza la compilación a Go 1.26.9 y actualiza proxy-init a v2.4.11 y el complemento CNI a v1.7.1. Consulta las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.2) para obtener más detalles.

### Actualización de agosto de 2026: edge-26.8.4

La versión edge-26.8.4, publicada el 25 de agosto de 2026, protege contra un ExternalWorkload nulo al manejar protocolos opacos, hace que el controlador de políticas negocie con el clúster la versión de la API TLSRoute y actualiza Go a 1.26.7. Consulta las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4) para obtener más detalles.

### Actualización de agosto de 2026: edge-26.8.2 (compatibilidad con Gateway API 1.5.1)

La versión edge-26.8.2, publicada el 14 de agosto de 2026, añade compatibilidad con Gateway API 1.5.1 (mediante linkerd-kubert 0.27.0) y eleva a 1.36 la versión máxima de Kubernetes probada. También incluye correcciones de estabilidad: elimina un informador Job duplicado del controlador de destino y hace que el controlador de políticas salga si se interrumpe su tarea de observación de la concesión. Consulta las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2) para obtener más detalles.

### Actualización de julio de 2026: edge-26.7.1 (se rechazan las solicitudes a puertos de Service no definidos)

La versión de GitHub de edge-26.7.1 se publicó el 21 de julio de 2026. Incluye una corrección que cambia el comportamiento: rechaza las solicitudes a puertos que no declara el Service de destino, incluso cuando existe un ServiceProfile. Antes de actualizar, comprueba las declaraciones reales de puertos del Service. La versión también añade una comprobación de instalación de Gateway API. Consulta las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1).

## Descripción general

Linkerd es una malla de servicios de nivel graduado de CNCF con un proxy del plano de datos escrito en Rust. CNCF registra el primer commit en 2016 y la graduación en 2021. Evalúa su modelo operativo, compatibilidad con protocolos y uso de recursos según la carga de trabajo real; no des por hecho que «simple» o «ligero» sean garantías.

### Propuestas de valor principales

| Capacidad | Qué verificar |
|---|---|
| mTLS predeterminado para las cargas de trabajo | Que ambos pares estén en la malla y que el tráfico no evite el proxy; el tráfico sin cifrar de pares que no están en la malla requiere una política de autorización explícita |
| Proxy Rust | Solicitudes, límites y uso de memoria/CPU con los niveles previstos de conexiones y tráfico |
| Enrutamiento HTTP/gRPC | Tipos de Gateway API compatibles, asociación y detección de protocolos |
| Operaciones | Ciclo de vida de los certificados, HA, compatibilidad de actualización y responsabilidad por las extensiones |
| Rendimiento | Mediciones de latencia, errores y carga específicas de la carga de trabajo; no hay una promesa universal de 10 MB o de menos de un milisegundo |

## Descripción general de la arquitectura de Linkerd

| Componente | Función |
|---|---|
| Controladores de destino y de políticas | Descubren endpoints y distribuyen políticas de enrutamiento/autorización a los proxies |
| Identity | Valida las solicitudes de identidad y emite certificados de corta duración para las cargas de trabajo mediante las credenciales de confianza configuradas |
| Proxy Injector | Modifica los Pods nuevos que cumplan los requisitos para añadirles el proxy |
| linkerd-proxy | Intercepta el tráfico TCP configurado, autentica/cifra las rutas elegibles de la malla y proporciona el comportamiento L7 compatible |
| Extensiones/backends opcionales | Métricas/dashboard de Viz, integración multicluster y recopilación/almacenamiento de trazas configurados por separado |

Esta arquitectura no implica una huella de memoria ni una sobrecarga de latencia fijas. Mide esas propiedades para la carga de trabajo y la configuración seleccionadas.

## Comparación de mallas de servicios

| Aspecto | Linkerd | Istio | Cilium |
|---|---|---|---|
| Plano de datos | Sidecars Rust | Sidecars Envoy o ztunnel más waypoints | Redes eBPF con Envoy para las funciones L7 compatibles |
| Enrutamiento HTTP | Rutas de Gateway API; ServiceProfiles siguen siendo compatibles con flujos de trabajo anteriores | API de Istio o asociación de Gateway API compatible | Gateway API y funciones de políticas/controladores de Cilium |
| Seguridad | mTLS automático entre pares TCP elegibles de la malla; los controles de autorización regulan otras fuentes | El mTLS automático, la aplicación de reglas de entrada y la autorización son controles distintos | La autenticación de pares y el cifrado del contenido deben evaluarse por separado |
| Observabilidad | Métricas del proxy más Viz/backends configurados | Telemetría específica del modo más backends configurados | Hubble y backends L7/métricas configurados |
| Multicluster | Replicación/federación y configuración explícita de confianza/red | Configuraciones de malla compatibles con cada topología | ClusterMesh y sus requisitos de plataforma/red |
| Selección | Prueba las funciones y operaciones necesarias | Prueba las funciones y operaciones necesarias | Prueba las funciones y operaciones necesarias |

SMI TrafficSplit es un flujo de trabajo heredado, no una descripción completa del enrutamiento actual de Linkerd. Linkerd puede enrutar HTTP/gRPC según las propiedades de las solicitudes mediante Gateway API. No se pueden comparar las clasificaciones de memoria fija, p99 ni personal/necesidad de complejidad sin una carga de trabajo reproducible y mediciones con versiones identificadas.

## Cuándo elegir Linkerd

Linkerd es una opción cuando su integración predeterminada con Kubernetes, la identidad de las cargas de trabajo y el comportamiento HTTP/gRPC/TCP compatible se ajustan a las necesidades de la aplicación. Evalúa el uso eficiente de recursos y la latencia con una carga realista, y planifica la rotación de la CA, las políticas de acceso y las actualizaciones. El cifrado automático del transporte, por sí solo, no constituye un programa completo de confianza cero ni de cumplimiento.

Valida las funciones exactas de enrutamiento/filtros/extensibilidad que necesitas antes de elegir una malla. Los protocolos que no son HTTP se pueden transportar por proxy como TCP; esto no les proporciona enrutamiento ni métricas de nivel HTTP. Las conexiones iniciadas primero por el servidor o inactivas pueden requerir la configuración de puertos opacos o appProtocol, y el TLS iniciado por la aplicación sigue siendo opaco para la inspección HTTP. El tráfico opaco sigue pasando por el proxy; los puertos omitidos lo evitan.

La integración con máquinas virtuales y físicas está disponible mediante [mesh expansion](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/), que incluye el registro de ExternalWorkload y una ruta externa de identidad/inicialización. No es algo que carezca categóricamente de compatibilidad. La accesibilidad de red, DNS, la instalación del proxy y el diseño de confianza imponen requisitos adicionales a los de la inyección normal en Pods; los atajos de inicialización del tutorial upstream no constituyen un diseño para producción.

## Estructura de la documentación

| Documento | Descripción |
|---|---|
| [Instalación y configuración](01-installation.md) | Versión/compatibilidad exacta, CLI/Helm, credenciales de confianza, HA y extensiones |
| [Arquitectura](02-architecture.md) | Controladores, proxies y jerarquía de certificados |
| [Gestión del tráfico](03-traffic-management.md) | Gateway API, ServiceProfiles heredados, reintentos/tiempos de espera y división del tráfico |
| [Seguridad](04-security.md) | Límites de mTLS, autorización y rotación de la CA |
| [Observabilidad](05-observability.md) | Métricas, Viz, backends externos y trazas |
| [Multicluster](06-multi-cluster.md) | Replicación/federación, rutas de red, confianza y credenciales |
| [Prácticas recomendadas](07-best-practices.md) | Validación operativa, rendimiento y solución de problemas |

## Inicio rápido

### 1. Selecciona la CLI y los requisitos previos

Sigue la [guía de instalación](01-installation.md) para el sistema operativo/arquitectura y la versión exactos que hayas elegido. Verifica que la salida de la CLI coincida con la distribución prevista; no supongas que un instalador sin versión fijada instalará una versión estable anterior. Los CRD de Gateway API son un requisito previo, y el paquete instalado debe ser compatible con todos los controladores que lo utilicen.

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. Genera los manifiestos, revísalos e instala

En un laboratorio nuevo y controlado, con la CLI y los requisitos previos seleccionados, la CLI genera los manifiestos:

```bash
set -euo pipefail
linkerd install --crds > linkerd-crds.yaml
# Review CRD ownership/version before applying.
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
# Review trust credentials and deployment settings before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

La configuración predeterminada de la CLI genera credenciales de confianza con una duración limitada. No es una configuración multicluster lista para usar con confianza compartida. Para instalaciones repetibles y de larga duración, sigue el proceso documentado de ciclo de vida de Helm/CA. En esta revisión se comprobaron la generación de manifiestos sin conexión y la sintaxis de la CLI, no una instalación activa.

### 3. Añade la aplicación prevista

Para un namespace y un Deployment existentes y seleccionados, sustituye ambos nombres my-app por los destinos reales:

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

Si hay una anotación existente que entra en conflicto, revísala en lugar de sobrescribirla automáticamente. Solo se inyectan los Pods nuevos, y un reinicio gradual necesita las salvaguardas de disponibilidad y capacidad del workload. Como alternativa, la inyección manual puede aplicarse al manifiesto de la aplicación revisado; no vuelvas a procesar todos los Deployment activos mediante inject/apply como solución general.

### 4. Añade Viz si hace falta

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz es opcional y tiene su propio ciclo de vida. Su configuración predeterminada de métricas no es un diseño universal de retención/HA para producción.

## Comprobación del estado de los componentes de Linkerd

```bash
# Core installation/control-plane checks.
linkerd check
# Data-plane proxy checks in the selected namespace.
linkerd check --proxy -n my-app
# Requires the configured Viz extension.
linkerd viz stat deploy -n my-app
linkerd viz tap deploy/my-app -n my-app
```

Tap observa eventos de solicitudes HTTP compatibles; no demuestra que se hayan cubierto todas las rutas TCP, todos los paquetes ni todos los límites de cifrado.

## Conceptos básicos

### Proxy del plano de datos

linkerd-proxy, escrito en Rust, se ejecuta junto a las cargas de trabajo incorporadas. Procesa las rutas TCP configuradas; los puertos omitidos, los endpoints que no están en la malla y las restricciones de la plataforma deben comprobarse por separado. El comportamiento de nivel HTTP requiere que HTTP sea visible o detectable. Mide el uso de recursos y la latencia en lugar de dar por sentada una huella constante por Pod.

### Descubrimiento de servicios

Los componentes de destino y de políticas observan el estado de Service/endpoints y proporcionan información de enrutamiento. ServiceProfiles y Gateway API son rutas de configuración distintas, con precedencia y compatibilidad de funciones que dependen de la versión. Asegúrate de declarar todos los puertos de Service previstos; consulta arriba la nota histórica sobre el cambio incompatible.

### mTLS automático

La duración predeterminada documentada para los certificados de las cargas de trabajo es de 24 horas, con renovación automática. La identidad está vinculada al ServiceAccount del Pod, no es una identidad única para cada Pod. Los anclajes de confianza y las credenciales del emisor tienen ciclos de vida distintos; las credenciales generadas por la CLI de forma predeterminada caducan al cabo de un año y requieren una rotación planificada.

Los pares TCP de la malla usan mTLS, pero el tráfico hacia/desde pares que no están en la malla y los puertos omitidos quedan fuera de esa garantía automática. La política de entrada predeterminada acepta tráfico sin cifrar procedente de pares que no están en la malla; usa una política de autorización si debe rechazarse. Para la comunicación multicluster se requieren confianza compartida y conectividad explícita.

## Próximos pasos

1. [Instalación y configuración](01-installation.md)
2. [Arquitectura](02-architecture.md)
3. [Cuestionario sobre instalación](../../quizzes/service-mesh/linkerd/installation.md), [Cuestionario sobre arquitectura](../../quizzes/service-mesh/linkerd/architecture.md), [Cuestionario sobre tráfico](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [Cuestionario sobre seguridad](../../quizzes/service-mesh/linkerd/security.md), [Cuestionario sobre observabilidad](../../quizzes/service-mesh/linkerd/observability.md), [Cuestionario sobre multicluster](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## Referencias

- [Documentación de Linkerd](https://linkerd.io/docs/overview/)
- [Canales de versiones](https://linkerd.io/releases/) e [instalación](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/) y [enrutamiento de solicitudes](https://linkerd.io/docs/features/request-routing/)
- [mTLS automático y salvedades](https://linkerd.io/docs/features/automatic-mtls/) y [manejo de TCP/protocolos](https://linkerd.io/docs/features/protocol-detection/)
- [Registro del proyecto CNCF](https://www.cncf.io/projects/linkerd/)
- [GitHub de Linkerd](https://github.com/linkerd/linkerd2), [comunidad](https://slack.linkerd.io/), [blog de Buoyant](https://buoyant.io/blog)
