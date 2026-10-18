# Cuestionario de Linkerd multiclúster

Basado en la [guía multiclúster](../../../service-mesh/linkerd/06-multi-cluster.md), revisada el 11 de septiembre de 2026.

### 1. ¿Cuál es un mecanismo esencial de Linkerd multiclúster?

- A. Fusionar clústeres de Kubernetes
- B. Reflejar Services
- C. Replicar automáticamente todas las escrituras de las aplicaciones
- D. Usar obligatoriamente un balanceador de carga global

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Un controlador de origen observa información seleccionada de Services mediante la API de Kubernetes de destino y crea recursos locales para su descubrimiento. Esto no es duplicación de solicitudes ni replicación de datos. Los modos jerárquico, plano y federado tienen distintos requisitos de red.

</details>

### 2. ¿Qué deben autenticar los clústeres para usar mTLS de la malla?

- A. La misma clave privada de la entidad emisora
- B. El conjunto pertinente de anclas de confianza públicas y cadenas de entidades emisoras
- C. Una clave privada compartida de carga de trabajo
- D. Objetos Secret de Kubernetes idénticos en todos los clústeres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Una raíz común es la configuración más sencilla; un paquete de confianza compartido puede contener varias raíces adecuadas. Las entidades emisoras de cada clúster pueden tener claves distintas. Los proxies existentes necesitan una transición coordinada del paquete de confianza, y hay que distinguir las raíces públicas de las claves de firma.

</details>

### 3. ¿Cuál es la etiqueta de exportación predeterminada para la réplica jerárquica mediante gateway?

- A. `linkerd.io/exported: "true"`
- B. `mirror.linkerd.io/exported: "true"`
- C. `multicluster.linkerd.io/export: "enabled"`
- D. `linkerd.io/multicluster: "export"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El selector jerárquico predeterminado coincide con `mirror.linkerd.io/exported=true`. El modo plano usa `remote-discovery` y la federación usa `mirror.linkerd.io/federated=member` para los miembros. Las etiquetas afectan el descubrimiento según los Links y RBAC coincidentes; no constituyen un límite de control de acceso.

</details>

### 4. ¿Cuál suele ser el nombre de un Service replicado?

- A. `<service>.<cluster>`
- B. `<service>-<nombre del clúster de Link>`
- C. `<cluster>-<service>`
- D. `<service>@<cluster>`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Normalmente, el Service `web` importado desde un Link llamado `west` pasa a llamarse `web-west` en el espacio de nombres correspondiente. El nombre de clúster del Link es un alias y no tiene que coincidir con el nombre físico del clúster de EKS. La creación de espacios de nombres no está habilitada de forma predeterminada.

</details>

### 5. ¿Qué genera el comando actual `link-gen`?

- A. Rutas de VPC y balanceadores de carga de gateway
- B. Un Link y dos Secrets de credenciales para el clúster de origen
- C. Una base de datos de aplicación replicada
- D. Certificados nuevos para cada Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Generar los recursos con el contexto `west` y aplicarlos a `east` permite que East descubra West. La lista de controladores del chart proporciona el controlador de réplica de origen. El comando antiguo `link` está obsoleto. Los datos de kubeconfig generados son confidenciales y deben incluir un endpoint de API accesible y datos de CA utilizables.

</details>

### 6. ¿Qué comando muestra las estadísticas de sondeo del gateway de destino?

- A. `linkerd multicluster status`
- B. `linkerd multicluster gateways`
- C. `kubectl get gateway`
- D. `linkerd gateway inspect`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** `gateways` muestra el resultado del sondeo configurado del gateway de destino, no el estado de cada aplicación. El sondeo lo ejecuta el controlador de réplica del clúster de origen. Los Links que solo usan el modo plano no requieren un gateway; usa los diagnósticos de Link, endpoint y conectividad de Pods para esos casos.

</details>

### 7. ¿Qué configuración de balanceador se usa en el ejemplo de AWS Load Balancer Controller de la guía?

- A. Un ALB público que termina el TLS de la malla
- B. Un ClusterIP arbitrario al que se puede acceder automáticamente entre regiones
- C. Un NLB TCP interno seleccionado con `service.k8s.aws/nlb`
- D. La anotación heredada de NLB demuestra automáticamente que el propietario usa destinos IP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El ejemplo presupone ese controlador, las anotaciones admitidas y la conectividad privada ya preparada. EKS Auto Mode tiene una clase y un propietario diferentes. Hay que comprobar por separado la accesibilidad de los datos del gateway, las rutas de sondeo y los endpoints de la API remota de Kubernetes.

</details>

### 8. ¿Qué backends puede usar el ejemplo actual de HTTPRoute para distribuir solicitudes entre servicios locales y remotos?

- A. Un Service local y una IP de Pod arbitraria de otro servidor de API
- B. Un Service backend local y un Service réplica importado localmente
- C. Solo el Service local
- D. Un conjunto de réplicas de base de datos automático

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El ejemplo conecta `web-local` y `web-west` mediante un Service raíz. Los pesos relativos no crean una política automática de respaldo; un reparto 100/0 no cambia por sí solo al backend de peso cero si hay un fallo. Las extensiones SMI/Failover están obsoletas; la federación plana tiene requisitos y comportamiento propios.

</details>

### 9. ¿Cuál no es una función del controlador de réplica?

- A. Observar Services remotos seleccionados
- B. Crear o actualizar réplicas locales
- C. Emitir certificados de cargas de trabajo
- D. Mantener la información de descubrimiento y endpoints adecuada para cada modo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Identity emite certificados para las cargas de trabajo. El controlador de réplica seleccionado sigue manteniendo Endpoints heredados para los servicios jerárquicos; en el modo `remote-discovery` puede quitar los Endpoints locales y depender del descubrimiento remoto del lado de destino.

</details>

### 10. ¿Qué puede proporcionar conectividad privada enrutada entre VPC cuando se configura adecuadamente?

- A. Route 53 por sí solo
- B. VPC Peering o rutas adecuadas de Transit Gateway
- C. CloudFront por sí solo
- D. Un endpoint de interfaz de administración de EKS que proporcione automáticamente enrutamiento de Pods en modo plano

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** También se necesitan rutas, direcciones únicas y accesibles, DNS y controles de seguridad. PrivateLink ofrece acceso a servicios o recursos seleccionados; no equivale a VPC Peering. Un endpoint de interfaz de EKS no es el endpoint de la API de Kubernetes del clúster.

</details>

### 11. ¿Cómo puede autorizar un servidor final una identidad remota de carga de trabajo que se haya conservado?

- A. Tratar el nombre de la cuenta de AWS como una identidad implícita de la malla
- B. Usar la autorización de Linkerd con la identidad real en formato DNS en modo plano o federado
- C. Usar en cualquier gateway el ejemplo obsoleto de URI SPIFFE
- D. Suponer que una etiqueta pública de exportación autentica a los clientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Los gateways jerárquicos pierden la identidad del cliente original cuando llega al servidor final. Las rutas planas o federadas la conservan. El mismo nombre de ServiceAccount, espacio de nombres y dominio de confianza puede identificar cargas de trabajo en más de un clúster; la política no demuestra automáticamente que el origen sea East.

</details>

### 12. ¿Qué no demuestra una comprobación de la infraestructura multiclúster?

- A. Si la configuración Link tiene errores detectables
- B. Si el acceso remoto o los sondeos configurados tienen fallos detectables
- C. La corrección de la aplicación o una recuperación regional garantizada
- D. Si los componentes de réplica tienen problemas de configuración detectables

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Las comprobaciones ayudan a diagnosticar la configuración, las credenciales y la infraestructura. No demuestran la coherencia de datos, que los reintentos de escritura sean seguros, que haya capacidad suficiente ni que el comportamiento de negocio sea correcto tras una conmutación por error. Verifica por separado los resultados reales de las cargas de trabajo.

</details>
