# Guía de comparación

> **Última revisión**: 11 de septiembre de 2026
> **Público objetivo**: Arquitectos, ingenieros de DevOps e ingenieros de plataforma

Antes de elegir una malla, compare los contratos necesarios de tráfico, identidad, plataforma y operación. El tamaño de la organización, las estrellas de funcionalidades o un porcentaje fijo de sobrecarga de recursos no determinan si una solución es adecuada. Compruebe por separado la compatibilidad de versiones y las opciones de canal de publicación; no se deducen de la comparación arquitectónica.

## Contenido

### 1. [Comparación de soluciones de Service Mesh](01-service-mesh-comparison.md)

La comparación detallada incluye Istio, Linkerd, Kong Mesh/Kuma y Consul Service Mesh. Al evaluar conjuntamente las funciones de red y de malla, considere también la [guía mantenida de Cilium Service Mesh](../../cilium-service-mesh/README.md).

Compare los planos de datos y de control, las políticas de tráfico admitidas, la identidad y el cifrado, la observabilidad, la compatibilidad con Kubernetes y VM, la topología multiclúster, el ciclo de vida y las condiciones de distribución comercial. Mida el uso de recursos con políticas y tráfico equivalentes, en lugar de asignar de antemano una clasificación intrínseca alta/media/baja.

### 2. [Istio frente a VPC Lattice](02-istio-vs-lattice.md)

Istio es una malla que se puede desplegar, con integración documentada para Kubernetes y VM. VPC Lattice es un servicio de redes de aplicaciones administrado por AWS para servicios y recursos, incluidos destinos compatibles de EC2, contenedores y Lambda. No exige que todas las aplicaciones sean sin servidor.

Compare el comportamiento de protocolos y enrutamiento, la identidad en cada límite TLS, la conectividad regional, las responsabilidades de cada propietario y las dimensiones reales de facturación. Una red administrada no elimina las tareas operativas de la aplicación, DNS, IAM, estado de los destinos ni costos.

### 3. [Sidecar frente a Ambient](03-sidecar-vs-ambient.md)

Esta guía incluye experimentos registrados en EKS sobre mTLS, NetworkPolicy, latencia y fallos durante despliegues. Mantenga vinculados a cada conclusión las versiones, la carga de trabajo, la ventana de medición y los resultados brutos de 503 de cada experimento. Los resultados visibles para el cliente después de los reintentos son otra medición; los reintentos pueden ocultar fallos y duplicar operaciones no idempotentes.

Use esas observaciones para diseñar una prueba para la carga de trabajo prevista. No demuestran una clasificación universal de la fiabilidad de sidecars frente a waypoints ni establecen una regla obligatoria para ubicar cargas de trabajo en niveles centrales, semicentrales o periféricos.

## Criterios de selección

| Requisito | Funciones candidatas que evaluar | Evidencia necesaria |
|---|---|---|
| Tráfico y políticas L7 detallados | Istio; además, las funciones concretas requeridas de Linkerd/Kong/Consul/Cilium | API admitidas, comportamiento de protocolos, configuración generada y pruebas de actualización |
| Una malla Kubernetes enfocada | Linkerd o un despliegue de Istio con alcance adecuado | Esfuerzo operativo real, ciclo de vida de identidad, cobertura funcional y mediciones con carga equivalente |
| Redes Cilium existentes | Plano de datos eBPF de Cilium y funciones L7 basadas en proxy | Compatibilidad del kernel/CNI, funciones L7 habilitadas y requisitos separados de autenticación/cifrado |
| Conectividad de servicios y recursos de AWS | VPC Lattice | Ruta de red/endpoints regionales, compatibilidad de destinos, contratos IAM/TLS y responsabilidades de propietarios de servicios/recursos |
| Cargas de trabajo de VM o híbridas | Integración de VM de Istio, expansión de malla de Linkerd, modo Universal de Kong o entornos de ejecución admitidos por Consul | Identidad de carga de trabajo, DNS, accesibilidad de IP/API y limitaciones específicas del entorno de ejecución |
| Multiclúster o multinube | Topología admitida por la malla elegida y la red externa necesaria | Límites de confianza, distribución de configuración, recuperación de datos, latencia y costos de transferencia |
| Observabilidad profunda | La malla elegida y los backends adecuados de métricas/logs/trazas | Etiquetas reales de telemetría, propagación de trazas de la aplicación, muestreo, retención y controles de acceso |

Estas son opciones candidatas, no recomendaciones automáticas de productos. Un backend de trazado o un dashboard es una dependencia adicional que debe configurarse; ninguna malla genera una traza completa de la aplicación sin la propagación de contexto y la instrumentación necesarias.

## Comparación rápida de arquitecturas

| Solución | Plano de datos | Consideraciones de plataforma y operación |
|---|---|---|
| Istio | Sidecars Envoy; Ambient usa ztunnel por nodo y waypoints Envoy opcionales | Kubernetes e integración documentada con VM; compatibilidad de funciones/topología según el modo; distribución autogestionada o de proveedor |
| Linkerd | Proxy linkerd2-proxy escrito en Rust | Kubernetes y expansión de malla documentada a entornos no Kubernetes mediante ExternalWorkload e identidad/red compatibles; no equivale a «sin compatibilidad con VM» |
| Kong Mesh | Proxies Envoy en el plano de datos | Modos Universal para Kubernetes y VM/bare metal; opciones autogestionadas o con plano de control global administrado, con funciones según la edición |
| Consul Service Mesh | Sidecars Envoy con descubrimiento/plano de control de Consul | Integraciones documentadas con Kubernetes, VM y otros entornos; verifique la edición/versión y la compatibilidad del proxy elegidos |
| Cilium | Plano de datos de red eBPF y proxies como Envoy para L7 | Verifique los componentes habilitados y la compatibilidad de la plataforma; la implementación L7 no está totalmente libre de proxies |

Cilium 1.20.1 documenta la autenticación mutua fuera de banda como **Beta**, mediante un protocolo de enlace fuera de banda. El cifrado del tráfico requiere una configuración independiente de WireGuard/IPsec; esa función de autenticación no equivale a envolver automáticamente cada conexión de aplicación en una sesión TLS al estilo de Istio. También importan las limitaciones documentadas para Cluster Mesh y mTLS externo.

Cilium 1.20.1 también proporciona una [versión beta de cifrado transparente con ztunnel](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), que se selecciona con `encryption.type: ztunnel`. Proporciona mTLS TCP para cargas de trabajo inscritas por namespace; ambos extremos deben estar inscritos. Excluye ClusterMesh y los Pods que usan la red del host, y la guía publicada advierte que las políticas L4 ordinarias no funcionan en esta ruta, salvo al dirigirse al puerto HBONE 15008. Es una opción de despliegue distinta, con requisitos propios de CA y bootstrap.

La versión de hito del proyecto Linkerd y el artefacto instalado son decisiones distintas. La página oficial de publicaciones enumera Linkerd 2.20 y su versión edge correspondiente; el proyecto de código abierto publica artefactos edge, mientras que los artefactos estables provienen de proveedores. Revise las directrices de publicación, la compatibilidad con Kubernetes, las condiciones de actualización/soporte y cualquier costo de suscripción. No deduzca el artefacto o canal a partir de un enlace de documentación antiguo.

### Istio y VPC Lattice

| Dimensión | Istio | VPC Lattice |
|---|---|---|
| Despliegue | Planos de control/datos operados por el usuario o distribución de proveedor elegida | AWS opera el servicio de red; los usuarios configuran servicios/recursos, acceso y destinos |
| Plataforma | Integración con Kubernetes y VM, con requisitos explícitos de red/confianza | Redes de AWS con destinos de servicio y configuraciones de recursos admitidos, además de rutas de cliente documentadas |
| Modelo de tráfico/seguridad | Enrutamiento de malla, identidad de cargas de trabajo y políticas según el modo | Contratos de listeners/reglas/destinos y políticas de autenticación del servicio; las configuraciones de recursos tienen controles distintos |
| Operación | Ciclo de vida de proxies/plano de control, capacidad, certificados, políticas y telemetría | IAM/compartición, DNS/endpoints, estado de destinos, integración con controladores, cuotas y telemetría siguen siendo tareas del usuario |
| Costo | Cómputo, balanceadores de carga, transferencia, almacenamiento/telemetría y soporte opcional | Dimensiones de facturación aplicables por capacidad aprovisionada/uso, además de infraestructura y operación circundantes |
| Integración híbrida | Diseño explícito de gateway/confianza/identidad | Ruta explícita de endpoint/red regional y límite TLS/autenticación; no es federación automática de mallas entre nubes |

Se omiten las puntuaciones de funciones y las celdas de «soporte empresarial» de un proveedor: disponibilidad, licencias y soporte dependen de la distribución y el contrato reales; las integraciones mencionadas no certifican una configuración.

## Guía de migración

### De Linkerd a Istio

Antes de traducir la configuración, inventaríe las API de tráfico, el comportamiento de reintentos/timeouts, la autorización, las identidades, los certificados y la telemetría. Linkerd usa CRD además de anotaciones; la migración no consiste en convertir mecánicamente anotaciones en CRD de Istio. Pruebe la coexistencia y migre por etapas un grupo de servicios o namespaces; evite solapar la captura de tráfico o inyectar dos sidecars de malla en el mismo Pod.

### De Kubernetes a una malla

Parta de un requisito no satisfecho: identidad de cargas de trabajo, políticas, resiliencia u observabilidad. El número de servicios por sí solo no determina la necesidad de una malla. Es posible que Services existentes, una implementación mantenida de Ingress/Gateway API, NetworkPolicy e instrumentación de la aplicación ya satisfagan el requisito. Pruebe la inyección o inscripción en Ambient, el inicio/drenaje, la aplicación de políticas y la reversión en una carga de trabajo acotada.

### Istio y VPC Lattice

Una solución híbrida puede usar Istio dentro de un clúster y Lattice a través de una ruta de servicio configurada explícitamente. Trace cada terminación TLS y la identidad del cliente. Una solicitud autenticada mediante IAM en Lattice requiere la ruta documentada de firma/autorización; mTLS de la malla por sí solo no crea identidad SigV4 ni propagación SPIFFE de extremo a extremo. No ejecute controladores que compitan por la misma ruta, destino o recurso DNS.

## Preguntas frecuentes

<details>
<summary>¿Siempre se necesita una malla de servicios?</summary>

No. Determine qué requisito de red, identidad, políticas u observabilidad aún no se satisface. Un servicio pequeño puede necesitar controles de identidad estrictos, mientras que un sistema mayor quizá ya implemente los controles necesarios en otros componentes. Evalúe el beneficio frente al costo operativo y de recursos real.

</details>

<details>
<summary>¿Debo elegir Istio o Linkerd?</summary>

Compare las funciones exactas de enrutamiento/seguridad/observabilidad, la compatibilidad de plataforma y el flujo operativo. Linkerd no se limita a funciones «básicas» ni a cargas de trabajo exclusivamente Kubernetes, e Istio tiene perfiles distintos de recursos y funciones en los modos sidecar y Ambient. Ejecute la misma carga de trabajo representativa y revise las opciones de publicación y soporte antes de decidir.

</details>

<details>
<summary>¿Cuándo es VPC Lattice una opción candidata?</summary>

Cuando el modelo de servicios/recursos admitido y los contratos de red/autenticación de AWS se ajusten a la aplicación. Pueden ser relevantes los destinos mixtos de contenedores, EC2 y Lambda; que la solución esté «centrada en AWS» o sea «sin servidor» no basta por sí solo. Confirme la región, la ruta del cliente, el tipo de destino, el protocolo, la identidad y las hipótesis de costo.

</details>

<details>
<summary>¿Cuánta sobrecarga debo esperar?</summary>

No existe una cifra universal de latencia, porcentaje de CPU o memoria por Pod que se aplique a todos estos productos. Mida políticas, TLS, tráfico, concurrencia, cantidad de nodos/proxies/waypoints y comportamiento ante fallos equivalentes. Conserve las versiones originales y los datos brutos de un benchmark reproducible. Las redes administradas también añaden una ruta de procesamiento, trabajo de observabilidad y uso facturable; no tienen impacto nulo en la infraestructura.

</details>

<details>
<summary>¿Pueden coexistir varias mallas?</summary>

Pueden coexistir en clústeres/grupos de cargas de trabajo separados o a través de un límite de migración/híbrido explícito. Varios interceptores en el mismo Pod o ruta de red pueden entrar en conflicto. Defina la propiedad del tráfico, la traducción de confianza/identidad, la telemetría y la reversión; no dé por hecho que separar namespaces hace interoperables los sistemas.

</details>

## Recursos relacionados

- [Arquitectura de Istio](../03-architecture.md)
- [Gestión del tráfico](../traffic-management/README.md)
- [Seguridad](../security/README.md)
- [Observabilidad](../observability/README.md)
- [VPC Lattice](../../../networking/02-vpc-lattice.md)
- [Linkerd](../../linkerd/README.md)
- [Service Mesh de Cilium](../../cilium-service-mesh/README.md)

## Referencias oficiales

- [Documentación de Istio](https://istio.io/latest/docs/) e [integración con VM](https://istio.io/latest/docs/setup/install/virtual-machine/)
- [Descripción general de Linkerd](https://linkerd.io/docs/overview/), [expansión de malla](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/) y [canales de publicación](https://linkerd.io/releases/)
- [Kong Mesh](https://developer.konghq.com/mesh/) y su [arquitectura](https://developer.konghq.com/mesh/architecture/)
- [Service Mesh de Consul](https://developer.hashicorp.com/consul/docs/connect)
- [Fuente sobre la arquitectura de malla de Cilium 1.20.1](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/index.rst) y [estado de la autenticación mutua](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Componentes y responsabilidades de VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
