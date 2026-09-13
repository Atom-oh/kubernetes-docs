# Linkerd

> **Última actualización**: September 11, 2026 · Ejemplos de CLI pública comprobados con edge-26.9.1

El proyecto upstream publica artefactos edge; las distribuciones estables y su ciclo de soporte proceden de proveedores. Linkerd 2.20 es un hito de funciones, no una cadena de versión universal para la CLI descargada. Elija una distribución/versión exacta y compruebe su compatibilidad con Kubernetes y Gateway API. El ejemplo público actual aquí es edge-26.9.1, publicado el September 4, 2026; corrige la aceptación de exec-auth-provider en credenciales remotas multiclúster y el tratamiento de conflictos de IP de destino reintentables. Consulte la [versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1) y el [modelo de versiones](https://linkerd.io/releases/).

Las entradas siguientes conservan el contexto histórico de versiones. La versión máxima de Kubernetes probada con edge-26.8.2 no amplía automáticamente la matriz de soporte de una distribución estable de un proveedor.

### Actualización de agosto de 2026: edge-26.8.4

La versión edge-26.8.4, publicada el August 25, 2026, protege frente a un ExternalWorkload nulo en el tratamiento de protocolos opacos, hace que el controlador de políticas negocie la versión de API TLSRoute con el clúster y actualiza Go a 1.26.7. Consulte las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4) para más detalles.

### Actualización de agosto de 2026: edge-26.8.2 — Compatibilidad con Gateway API 1.5.1

La versión edge-26.8.2, publicada el August 14, 2026, añade compatibilidad con Gateway API 1.5.1 (mediante linkerd-kubert 0.27.0) y eleva a 1.36 la versión máxima de Kubernetes probada. También incluye correcciones de estabilidad: elimina un informador Job duplicado en el controlador destination y hace que el controlador de políticas termine si muere su tarea de observación del arrendamiento. Consulte las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2) para más detalles.

### Actualización de julio de 2026: edge-26.7.1 — Solicitudes a puertos de Service no definidos prohibidas

La versión de GitHub para edge-26.7.1 se publicó el July 21, 2026. Incluye una corrección que cambia el comportamiento y rechaza solicitudes a puertos no declarados por el Service de destino incluso cuando existe un ServiceProfile. Compruebe las declaraciones reales de puertos de Service antes de actualizar. La versión también añade una comprobación de instalación de Gateway API. Consulte las [notas de la versión](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1).

## Descripción general

Linkerd es una malla de servicios graduada de CNCF con un proxy del plano de datos en Rust. CNCF registra su primer commit en 2016 y su graduación en 2021. Evalúe su modelo operativo, la compatibilidad de protocolos y el consumo de recursos respecto a la carga de trabajo real en vez de tratar «sencillo» o «ligero» como garantías.

### Principales propuestas de valor

| Capacidad | Qué verificar |
|---|---|
| mTLS predeterminado de cargas de trabajo | Ambos pares están en la malla y el tráfico no elude el proxy; el texto sin cifrar ajeno a la malla necesita políticas de autorización explícitas |
| Proxy Rust | Solicitudes, límites y uso de memoria/CPU con las conexiones y el tráfico esperados |
| Enrutamiento HTTP/gRPC | Tipos de Gateway API compatibles, asociación y detección de protocolos |
| Operaciones | Ciclo de vida de certificados, alta disponibilidad, compatibilidad de actualizaciones y gestión de extensiones |
| Rendimiento | Mediciones de latencia/errores/carga específicas de la carga de trabajo; sin promesa universal de 10MB ni de menos de un milisegundo |

## Descripción general de la arquitectura de Linkerd

| Componente | Función |
|---|---|
| Controladores Destination y de políticas | Descubrir endpoints y distribuir políticas de enrutamiento/autorización a los proxies |
| Identity | Validar solicitudes de identidad y emitir certificados de cargas de trabajo de corta duración usando credenciales de confianza configuradas |
| Inyector de proxies | Modificar Pods recién creados aptos para añadir el proxy |
| linkerd-proxy | Interceptar tráfico TCP configurado, autenticar/cifrar rutas de malla aptas y proporcionar comportamiento L7 compatible |
| Extensiones/backends opcionales | Métricas/panel de Viz, integración multiclúster y recopilación/almacenamiento de trazas configurados por separado |

Esta arquitectura no implica un consumo fijo de memoria ni una sobrecarga fija de latencia. Mida esas propiedades para la carga de trabajo y configuración seleccionadas.

## Comparación de mallas de servicios

| Aspecto | Linkerd | Istio | Cilium |
|---|---|---|---|
| Plano de datos | Sidecars Rust | Sidecars Envoy o ztunnel más waypoints | Redes eBPF con Envoy para funciones L7 compatibles |
| Enrutamiento HTTP | Rutas de Gateway API; ServiceProfiles siguen siendo compatibles para flujos anteriores | API de Istio o asociaciones compatibles de Gateway API | Gateway API y funciones de políticas/controladores de Cilium |
| Seguridad | mTLS automático entre pares TCP aptos de la malla; la autorización controla otros orígenes | mTLS automático, aplicación entrante y autorización son controles distintos | La autenticación de pares y el cifrado del contenido deben evaluarse por separado |
| Observabilidad | Métricas del proxy más Viz/otros backends configurados | Telemetría específica del modo más backends configurados | Hubble y backends L7/de métricas configurados |
| Multiclúster | Reflejo/federación y configuración explícita de confianza/red | Configuraciones compatibles de malla específicas de la topología | ClusterMesh y sus requisitos de plataforma/red |
| Selección | Probar las funciones y operaciones necesarias | Probar las funciones y operaciones necesarias | Probar las funciones y operaciones necesarias |

SMI TrafficSplit es un flujo heredado, no la descripción completa del enrutamiento actual de Linkerd. Linkerd puede enrutar HTTP/gRPC según propiedades de solicitudes mediante Gateway API. Las clasificaciones fijas de memoria, p99 y personal/complejidad no son comparables sin una carga de trabajo reproducible y mediciones con versiones identificadas.

## Cuándo elegir Linkerd

Linkerd es un candidato cuando su integración predeterminada con Kubernetes, identidad de cargas de trabajo y comportamiento HTTP/gRPC/TCP compatible encajan con las necesidades de la aplicación. Compare la eficiencia de recursos y la latencia bajo una carga realista y planifique la rotación de CA, las políticas de acceso y las actualizaciones. El cifrado automático de transporte por sí solo no es un programa completo de confianza cero ni de cumplimiento.

Valide las funciones exactas requeridas de enrutamiento/filtros/extensibilidad antes de elegir una malla. Los protocolos no HTTP pueden pasar por el proxy como TCP; esto no les proporciona enrutamiento ni métricas a nivel HTTP. Las conexiones donde el servidor habla primero/inactivas pueden necesitar configuración de puertos opacos o appProtocol, y el TLS originado en la aplicación sigue siendo opaco a la inspección HTTP. El tráfico opaco sigue atravesando el proxy; los puertos omitidos lo eluden.

La integración de VM y máquinas físicas está disponible mediante [expansión de la malla](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/), incluido el registro ExternalWorkload y una ruta externa de identidad/arranque. No es categóricamente incompatible. La accesibilidad de red, DNS, la instalación del proxy y el diseño de confianza añaden requisitos más allá de la inyección ordinaria de Pods; los atajos de arranque del tutorial upstream no son un diseño de producción.

## Estructura de la documentación

| Documento | Descripción |
|---|---|
| [Instalación y configuración](01-installation.md) | Versión/compatibilidad exactas, CLI/Helm, credenciales de confianza, alta disponibilidad y extensiones |
| [Arquitectura](02-architecture.md) | Controladores, proxies y jerarquía de certificados |
| [Gestión del tráfico](03-traffic-management.md) | Gateway API, ServiceProfiles heredados, reintentos/tiempos de espera y división del tráfico |
| [Seguridad](04-security.md) | Límites de mTLS, autorización y rotación de CA |
| [Observabilidad](05-observability.md) | Métricas, Viz, backends externos y trazado |
| [Multiclúster](06-multi-cluster.md) | Reflejo/federación, rutas de red, confianza y credenciales |
| [Buenas prácticas](07-best-practices.md) | Validación operativa, rendimiento y solución de problemas |

## Inicio rápido

### 1. Seleccionar la CLI y los requisitos previos

Siga la [guía de instalación](01-installation.md) para el sistema operativo/arquitectura y la versión exacta elegidos. Verifique que la salida de la CLI coincida con la distribución prevista; no suponga que un instalador sin versión fijada produce una versión estable anterior. Los CRD de Gateway API son un requisito previo y el paquete instalado debe ser compatible con todos los controladores que lo utilizan.

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. Renderizar, revisar e instalar

Para un laboratorio nuevo y controlado con la CLI y los requisitos seleccionados, la CLI renderiza manifiestos:

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

La configuración predeterminada de la CLI genera credenciales de confianza con duración finita. No es una configuración multiclúster de confianza compartida lista para usar. Para instalaciones repetibles de larga duración, siga el proceso documentado del ciclo de vida de Helm/CA. Esta revisión comprobó el renderizado sin conexión y la sintaxis de la CLI, no una instalación real.

### 3. Añadir la aplicación prevista

Para un espacio de nombres y Deployment existentes seleccionados, sustituya ambos nombres my-app por los destinos reales:

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

Revise una anotación existente en conflicto en vez de sobrescribirla automáticamente. Solo los Pods nuevos reciben inyección y un reinicio gradual necesita las protecciones de disponibilidad/capacidad de la carga de trabajo. La inyección manual puede operar en su lugar sobre el manifiesto de aplicación revisado; no pase todos los Deployments activos por inject/apply como solución general.

### 4. Añadir Viz si es necesario

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz es opcional y necesita su propio ciclo de vida. Su configuración predeterminada de métricas no es un diseño universal de retención/alta disponibilidad de producción.

## Comprobar el estado de los componentes de Linkerd

```bash
# Core installation/control-plane checks.
linkerd check
# Data-plane proxy checks in the selected namespace.
linkerd check --proxy -n my-app
# Requires the configured Viz extension.
linkerd viz stat deploy -n my-app
linkerd viz tap deploy/my-app -n my-app
```

Tap observa eventos de solicitudes HTTP compatibles; no demuestra todas las rutas TCP, paquetes ni límites de cifrado.

## Conceptos básicos

### Proxy del plano de datos

El linkerd-proxy de Rust se ejecuta junto a las cargas de trabajo incorporadas. Procesa rutas TCP configuradas; los puertos omitidos, los endpoints ajenos a la malla y las restricciones de plataforma deben comprobarse por separado. El comportamiento a nivel HTTP requiere HTTP visible/detectado. Mida el consumo de recursos y la latencia en vez de suponer un consumo constante por Pod.

### Descubrimiento de servicios

Los componentes Destination y de políticas observan el estado de Services/endpoints y proporcionan información de enrutamiento. ServiceProfiles y Gateway API son rutas de configuración distintas con prioridad y compatibilidad de funciones específicas de la versión. Asegúrese de que todos los puertos previstos de Service estén declarados; consulte la nota histórica anterior sobre el cambio incompatible.

### mTLS automático

La duración predeterminada documentada de los certificados de cargas de trabajo es de 24 horas con renovación automática. La identidad está ligada al ServiceAccount del Pod, no es una identidad única para cada Pod. Las anclas de confianza y las credenciales de emisores tienen ciclos de vida separados; las credenciales predeterminadas generadas por la CLI caducan al cabo de un año y necesitan rotación planificada.

Los pares TCP de la malla utilizan mTLS, pero el tráfico hacia/desde pares ajenos a la malla y los puertos omitidos quedan fuera de esa garantía automática. La política entrante predeterminada acepta texto sin cifrar ajeno a la malla; utilice políticas de autorización cuando deba rechazarse. La comunicación multiclúster requiere confianza compartida y conectividad explícita.

## Siguientes pasos

1. [Instalación y configuración](01-installation.md)
2. [Arquitectura](02-architecture.md)
3. [Cuestionario de instalación](../../quizzes/service-mesh/linkerd/installation.md), [cuestionario de arquitectura](../../quizzes/service-mesh/linkerd/architecture.md), [cuestionario de tráfico](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [Cuestionario de seguridad](../../quizzes/service-mesh/linkerd/security.md), [cuestionario de observabilidad](../../quizzes/service-mesh/linkerd/observability.md), [cuestionario multiclúster](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## Referencias

- [Documentación de Linkerd](https://linkerd.io/docs/overview/)
- [Canales de versiones](https://linkerd.io/releases/) e [instalación](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/) y [enrutamiento de solicitudes](https://linkerd.io/docs/features/request-routing/)
- [mTLS automático y limitaciones](https://linkerd.io/docs/features/automatic-mtls/) y [tratamiento de TCP/protocolos](https://linkerd.io/docs/features/protocol-detection/)
- [Registro del proyecto en CNCF](https://www.cncf.io/projects/linkerd/)
- [GitHub de Linkerd](https://github.com/linkerd/linkerd2), [comunidad](https://slack.linkerd.io/), [blog de Buoyant](https://buoyant.io/blog)
