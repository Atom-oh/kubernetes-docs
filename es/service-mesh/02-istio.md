# Istio

> **Última actualización**: 11 de septiembre de 2026 · Guía de Istio 1.31

Esta introducción conserva la URL del capítulo anterior. El [índice mantenido de Istio](istio/README.md) y la [guía de instalación](istio/01-installation.md) contienen procedimientos detallados y matriz de compatibilidad; úselos para configurar actualmente.

## Contenido

- [Introducción](#introduction)
- [Funciones principales](#key-features)
- [Arquitectura](#architecture-overview)
- [Documentación detallada](#detailed-documentation)
- [Inicio rápido](#quick-start)
- [Recursos de aprendizaje](#learning-resources)

## Introducción {#introduction}

Istio es una plataforma de malla de servicios de código abierto para aplicaciones de microservicios. Una malla de servicios es una capa de infraestructura que gestiona la comunicación entre servicios y permite controlar y observar esa comunicación a nivel de infraestructura. La propagación del contexto de trazas de la aplicación, el apagado ordenado y la idempotencia de negocio siguen requiriendo participación de la aplicación.

### ¿Qué es un service mesh?

Sus capacidades principales son:

1. **Gestión de tráfico**: Controlar flujos entre servicios
2. **Seguridad**: Cifrar y autenticar comunicaciones
3. **Observabilidad**: Hacer visibles esas comunicaciones

### Ventajas principales

- **Independencia de plataforma**: Kubernetes, VM y otros entornos
- **Integración transparente**: Muchos controles no requieren cambiar lógica de negocio
- **mTLS de cargas**: Identidad y protección de transporte en rutas inscritas; verificar aplicación y excepciones
- **Tráfico avanzado**: Rutas, balanceo e inyección de fallos
- **Métricas detalladas**: Comunicación entre servicios
- **Aplicación de políticas**: Acceso y limitación local/global explícitamente configurada

## Funciones principales {#key-features}

### 1. Gestión de tráfico

Istio proporciona capacidades potentes:

- **Gateways**: Enrutamiento externo; diferenciar Istio Gateway de Kubernetes Gateway API
- **VirtualService / HTTPRoute**: Usar la API soportada por dataplane/controlador elegidos
- **DestinationRule**: Balanceo y pools de conexión
- **División de tráfico**: Canary y pruebas A/B
- **Argo Rollouts**: Entrega progresiva con análisis y fallos configurados aparte

### 2. Seguridad

Funciones integrales:

- **mTLS**: Identidad y cifrado del transporte de cargas inscritas
- **Política de autorización**: Acceso detallado
- **Autenticación de solicitudes**: Validar JWT; AuthorizationPolicy para exigir su presencia
- **Autenticación de peers**: Política mTLS entrante

### 3. Observabilidad

Telemetría e integraciones según el modo:

- **Métricas**: Prometheus
- **Tracing distribuido**: Proveedor/backend, por ejemplo OpenTelemetry con Jaeger; la app propaga contexto
- **Logs**: Acceso y registros estructurados
- **Visualización**: Dashboard Kiali

### 4. Resiliencia

Patrones de resiliencia:

- **Circuit breaker**: Límites de pools de conexiones/solicitudes, no garantía contra sobrecarga
- **Reintentos**: Presupuestos explícitos para operaciones que se pueden reintentar de forma segura; desactivar los reintentos de escrituras cuyo resultado es incierto
- **Timeout**: Plazos de solicitudes
- **Detección de outliers**: Excluir instancias no saludables
- **Limitación de tasa**: Buckets locales o servicio global configurados

## Arquitectura {#architecture-overview}

Istio consta de un **plano de control** y un **plano de datos**. La figura representa sidecar, no ambient.

![Istiod, en el plano de control, envía configuración a los proxies sidecar Envoy que se ejecutan junto a los contenedores de aplicaciones en tres pods del plano de datos, y esos proxies establecen conexiones TLS mutuas directamente entre sí.](../.gitbook/assets/en-service-mesh-02-istio-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-02-istio-0.html)

### Plano de control (istiod)

istiod es el control central y proporciona:

- **Descubrimiento**: Mantiene el registro de servicios
- **Configuración**: Observa, traduce y distribuye ajustes; Kubernetes persiste recursos API
- **Certificados**: Gestiona solicitudes y rotación con la CA configurada

### Plano de datos: sidecar y ambient

En sidecar, Envoy acompaña cada Pod inscrito:

- **Enrutamiento**: Control del tráfico entre servicios
- **Balanceo**: Distribución entre instancias
- **Seguridad**: Cifrado y autenticación mTLS
- **Observabilidad**: Métricas, logs y trazas

Ambient utiliza ztunnel a nivel de nodo para el transporte L4 y waypoints Envoy opcionales para funciones L7 compatibles. No inyecta un Envoy en cada Pod de aplicación. La compatibilidad de funciones, la asociación de políticas y el consumo de recursos difieren según el modo; de esta topología no se deriva un porcentaje fijo de ahorro de recursos ni una superioridad universal de rendimiento. Consulte [Modo Ambient](istio/advanced/01-ambient-mode.md).

## Documentación detallada {#detailed-documentation}

Los enlaces orientan hacia el subárbol mantenido. Su índice incluye otros temas y novedades.

### 📚 Documentación básica

| Documento | Descripción |
|----------|-------------|
| [Instalación](istio/01-installation.md) | Instalación y configuración inicial |
| [Conceptos fundamentales](istio/02-basic-concepts.md) | Conceptos y terminología |
| [Componentes](istio/03-architecture.md) | Arquitectura y componentes |

### 🚦 Gestión de tráfico

| Documento | Descripción |
|----------|-------------|
| [Gateway y VirtualService](istio/traffic-management/01-gateway-virtualservice.md) | Gateways de entrada/salida |
| [Rutas](istio/traffic-management/02-routing.md) | Reglas VirtualService |
| [DestinationRule](istio/traffic-management/03-destination-rule.md) | Políticas de tráfico |
| [División de tráfico](istio/traffic-management/04-traffic-splitting.md) | Canary y A/B |
| [Timeout y reintentos](istio/traffic-management/05-retry-timeout.md) | Políticas de plazos/reintentos |
| [Balanceo](istio/traffic-management/06-load-balancing.md) | Estrategias de balanceo |
| [Circuit breaker](istio/traffic-management/07-circuit-breaker.md) | Implementación del patrón |
| [Inyección de fallos](istio/traffic-management/08-fault-injection.md) | Ingeniería del caos |
| [Espejo de tráfico](istio/traffic-management/09-traffic-mirror.md) | Duplicación y pruebas sombra |
| [Afinidad de sesión](istio/traffic-management/10-session-affinity.md) | Configuración de afinidad |

### 🔐 Seguridad

| Documento | Descripción |
|----------|-------------|
| [mTLS](istio/security/01-mtls.md) | mTLS entre servicios |
| [Autorización](istio/security/03-authorization.md) | Políticas de acceso |
| [Autenticación de solicitudes](istio/security/02-authentication.md) | Autenticación JWT |
| [Autenticación de peers](istio/security/01-mtls.md) | Autenticación entre servicios |

### 📊 Observabilidad

| Documento | Descripción |
|----------|-------------|
| [Métricas](istio/observability/01-metrics.md) | Recopilación Prometheus |
| [Tracing distribuido](istio/observability/02-tracing.md) | Jaeger/Zipkin |
| [Logs](istio/observability/03-logging.md) | Acceso y registros estructurados |
| [Visualización](istio/observability/04-dashboards.md) | Dashboards Kiali/Grafana |

### 💪 Resiliencia

| Documento | Descripción |
|----------|-------------|
| [Outliers](istio/resilience/01-outlier-detection.md) | Detección de instancias no saludables |
| [Limitación de tasa](istio/resilience/02-rate-limiting.md) | Límites locales/globales |
| [Rutas por zona](istio/resilience/03-zone-aware-routing.md) | Enrutamiento según localidad |

### 🚀 Temas avanzados

| Documento | Descripción |
|----------|-------------|
| [Ambient](istio/advanced/01-ambient-mode.md) | Malla sin sidecars |
| [Multiclúster](istio/advanced/02-multi-cluster.md) | Configuración de malla multiclúster |
| [EnvoyFilter](istio/advanced/03-envoy-filter.md) | Personalización Envoy |
| [Captura y caché DNS](istio/advanced/04-dns-cache.md) | Captura, resolución y comportamiento medido |
| [gRPC](istio/advanced/05-grpc.md) | Soporte gRPC |
| [WebSocket](istio/advanced/06-websocket.md) | Soporte de conexiones WebSocket |
| [Inyección sidecar](istio/advanced/07-sidecar-injection.md) | Mecanismo de inyección |
| [Argo Rollouts](istio/advanced/08-argo-rollouts.md) | Integración de entrega progresiva |

### ✅ Buenas prácticas

| Documento | Descripción |
|----------|-------------|
| [Buenas prácticas](istio/best-practices.md) | Lista y recomendaciones de producción |

## Inicio rápido {#quick-start}

1. Compruebe la intersección exacta de compatibilidad de Istio/Kubernetes/EKS en la [guía de instalación](istio/01-installation.md). Un requisito previo genérico de «Kubernetes 1.28+» no basta para una versión actual de Istio.
2. Elija sidecar/ambient y siga CLI/chart fijados, namespace aislado y requisitos de plataforma. No descargue una CLI última sin especificar para luego entrar en un directorio antiguo.
3. Use Bookinfo de versión coincidente y las instrucciones gateway mantenidas. El perfil predeterminado no crea automáticamente un Deployment ingress gateway; un objeto Gateway no crea todos los componentes/LoadBalancer necesarios.
4. Verifique dirección real, puerto Service, estado de ruta y respuesta HTTP. El LB puede publicar IP o hostname; no suponga un campo exclusivo AWS ni nombre de puerto específico.
5. Instale/configure [backends de observabilidad](istio/observability/README.md) antes de comandos de dashboard. Prometheus, Grafana, Kiali y almacenamiento de trazas no se instalan automáticamente.

Comprobación básica después del procedimiento:

```bash
istioctl version
istioctl analyze -A
istioctl proxy-status
```

El estado del proxy es solo una entrada diagnóstica. Inscripción ambient y ztunnel necesitan comprobaciones propias; un analyzer limpio no prueba tráfico extremo a extremo.

## Recursos de aprendizaje {#learning-resources}

### Documentación oficial

- [Documentación Istio](https://istio.io/latest/docs/)
- [Repositorio Istio](https://github.com/istio/istio)
- [Documentación Envoy](https://www.envoyproxy.io/docs/envoy/latest/)

### AWS y comunidad

- [Istio en Amazon EKS](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Guía AWS mantenida](istio/04-aws-integration.md)
- [Ciclo de vida AWS App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html): AWS indica fin de soporte el 30 de septiembre de 2026. Evalúe migración; no es recomendación de nuevo despliegue.
- [Comunidad, canales y grupos Istio](https://istio.io/latest/get-involved/)

### Recursos adicionales

- [Service Mesh Patterns (O'Reilly)](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
- [Istio in Action (Manning)](https://www.manning.com/books/istio-in-action)
- [Optimización de rendimiento Istio](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)

## Cuestionario

Compruebe su comprensión con el [cuestionario Istio](../quizzes/service-mesh/02-istio-quiz.md).

Incluye:

- Conceptos de service mesh
- Arquitectura Istio
- Gestión de tráfico y canary
- Seguridad mTLS
- Gateway e Ingress
- Herramientas de observabilidad
- Modos sidecar/ambient
- Limitación de tasa
- Enrutamiento local
- Integración EKS

---

**Próximos pasos**: Siga la [instalación](istio/01-installation.md) y aprenda los [conceptos fundamentales](istio/02-basic-concepts.md).
