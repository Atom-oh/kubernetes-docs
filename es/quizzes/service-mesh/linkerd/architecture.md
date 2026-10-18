# Cuestionario sobre la arquitectura de Linkerd

Revisado el 16 de octubre de 2026 para edge-26.10.1. Consulta la [guía de arquitectura](../../../service-mesh/linkerd/02-architecture.md) para ver el modelo y las limitaciones respaldados por la fuente.

### 1. ¿Cuál de estos elementos no es un componente del plano de control de Linkerd?

A. Controlador Destination

B. Controlador Identity

C. Proxy Injector

D. Proxy Envoy

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: D**

Linkerd utiliza un proxy del plano de datos escrito en Rust. La versión fijada del plano de control tiene tres implementaciones principales (Deployments), además de controladores lógicos, como el de políticas, que se ejecutan dentro de ellas. Envoy se usa en los sidecars y waypoints de Istio, no como controlador de Linkerd.

</details>

### 2. ¿En qué lenguaje está escrito linkerd2-proxy?

A. Go

B. C++

C. Rust

D. Java

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

Está escrito en Rust. El lenguaje elegido no demuestra que el consumo de memoria sea siempre de 10 MB, que la latencia p99 sea inferior a un milisegundo ni que el proxy sea siempre superior a otro. Compara las compilaciones, las cargas de trabajo y las configuraciones reales.

</details>

### 3. ¿Cuál no es una responsabilidad principal de Destination?

A. Descubrimiento de servicios

B. Emisión de certificados para las cargas de trabajo

C. Información compatible con ServiceProfile

D. Actualizaciones de endpoints

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Identity emite certificados para las cargas de trabajo mediante la credencial de la entidad emisora que tenga configurada. Destination proporciona información de descubrimiento y perfiles. El enrutamiento actual de Gateway API y la autorización también involucran al controlador de políticas. La extensión heredada TrafficSplit no representa todo el modelo actual de políticas.

</details>

### 4. ¿Qué constituye la base de confianza en la parte superior de la jerarquía de certificados predeterminada?

A. El certificado de la carga de trabajo

B. La entidad emisora de Identity

C. El ancla de confianza

D. Un nombre de Pod único

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

El ancla de confianza pública es la raíz de la validación de la cadena de certificados. Normalmente, firma el certificado de la entidad emisora intermedia, cuya clave firma los certificados de las cargas de trabajo. Linkerd no necesita la clave privada de la raíz para procesar cada solicitud de firma de certificado (CSR) de una carga de trabajo.

</details>

### 5. ¿Cuál es la duración nominal predeterminada de un certificado de carga de trabajo?

A. 1 hora

B. 24 horas

C. 7 días

D. 30 días

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

La duración predeterminada configurada para la emisión es de 24 horas y el certificado se renueva antes de caducar. La validez real y el momento de renovación dependen de la configuración y del estado del certificado. Renovarlo no implica generar automáticamente una clave privada nueva ni rotar la entidad emisora o la raíz.

</details>

### 6. ¿Qué mecanismo de Kubernetes realiza la inyección automática del proxy?

A. DaemonSet

B. CronJob

C. Webhook de admisión mutante

D. Application Load Balancer

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

El webhook modifica los Pods nuevos que cumplen los criterios. En la versión seleccionada, el proxy normalmente se agrega como sidecar nativo; si se configura Linkerd CNI, se omite linkerd-init. Los Pods existentes y los excluidos o sobrescritos deben evaluarse por separado.

</details>

### 7. ¿Qué hace linkerd-init cuando no se usa Linkerd CNI?

A. Descarga todas las políticas de enrutamiento

B. Configura la captura del tráfico de red del Pod

C. Actúa como la entidad certificadora raíz

D. Almacena series temporales de Prometheus

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Configura las reglas de captura dentro del espacio de nombres de red del Pod. Antes de redirigir el tráfico TCP interceptado, hay que tener en cuenta el UID del proxy y las reglas de omisión configuradas. Esto no significa que el proxy gestione todos los protocolos ni los puertos excluidos de la captura.

</details>

### 8. ¿Cuál es el puerto de entrada predeterminado del proxy?

A. 4140

B. 4143

C. 4191

D. 8080

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Los valores predeterminados son 4143 para la entrada, 4140 para la salida y 4191 para administración y métricas. Los puertos de entrada y salida gestionan el TCP interceptado, que puede transportar HTTP, gRPC o datos opacos. Los puertos se pueden configurar.

</details>

### 9. Si el ServiceAccount es web-service en my-app, ¿cuál es la identidad de Kubernetes predeterminada cuando el espacio de nombres del plano de control es linkerd y el dominio de confianza es cluster.local?

A. spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service

B. web-service.my-app.serviceaccount.identity.linkerd.cluster.local

C. `https://linkerd.io/identity/my-pod`

D. urn:linkerd:my-pod

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

La revisión del token de Kubernetes (TokenReview) produce la identidad del ServiceAccount, con formato de nombre DNS. Varios Pods que usan ese ServiceAccount comparten la identidad. Las identidades de cargas de trabajo externas de SPIFFE/SPIRE siguen un proceso de arranque distinto; no usan este formato URI predeterminado de Kubernetes.

</details>

### 10. ¿Qué comparación está justificada sin un benchmark equivalente?

A. Linkerd siempre consume exactamente 10 MB

B. Compara la arquitectura y las API admitidas; mide las diferencias de recursos y latencia con la carga de trabajo real

C. Istio siempre agrega entre 2 y 5 ms a la latencia p99

D. Una solicitud de memoria configurada más pequeña demuestra un consumo en ejecución menor

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

Las reservas configuradas, el tamaño del binario, la memoria realmente consumida y la latencia son propiedades distintas. Compara la misma versión y compilación, arquitectura, patrón de tráfico y conjunto de políticas. También verifica la extensibilidad para el modo y la API seleccionados; no la deduzcas de una clasificación genérica de productos.

</details>

### 11. ¿Qué comprueba el validador predeterminado de identidad de Kubernetes?

A. Solo la dirección IP del Pod

B. El token de ServiceAccount enviado, mediante TokenReview de Kubernetes

C. Solo una etiqueta del espacio de nombres

D. Solo el nombre de un ConfigMap

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

El validador publicado autentica el token y obtiene de la información de usuario de Kubernetes la identidad en formato DNS. La solicitud de certificación también incluye la identidad y los datos de la CSR. Esto no significa que se acepte cualquier URI SPIFFE que proporcione quien llama solo porque parezca válida.

</details>

### 12. ¿Cómo se entregan normalmente al proxy las actualizaciones dinámicas de enrutamiento y políticas?

A. Escribiendo en el endpoint de métricas de Prometheus

B. Cambiando el sujeto del certificado raíz

C. Mediante las API del plano de control, incluido gRPC en streaming

D. Aplicando reglas REDIRECT arbitrarias en el espacio de nombres de red del nodo

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

El puerto de administración proporciona interfaces de comprobación de estado y métricas; no sustituye a las API de políticas del plano de control. La configuración de inicio y de inyección, por un lado, y las políticas que se entregan dinámicamente, por otro, son entradas distintas. Al diagnosticar el comportamiento, revisa ambas.

</details>
