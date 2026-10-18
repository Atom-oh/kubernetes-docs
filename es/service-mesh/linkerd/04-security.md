# Seguridad de Linkerd

> **Última actualización**: 16 de octubre de 2026 · Linkerd edge-26.10.1 · Ejemplos de cert-manager comprobados con 1.21.2

Linkerd autentica las cargas de trabajo, cifra el transporte y controla el acceso entrante al tráfico que gestionan sus proxies. La incorporación a la malla, las políticas, el ciclo de vida de los certificados y la seguridad de la aplicación requieren un diseño explícito. Utilice la combinación compatible de Kubernetes y Gateway API indicada en la [guía de instalación](01-installation.md); estos ejemplos presuponen esa instalación y cargas de trabajo de aplicaciones ya existentes.

## Arquitectura de seguridad

![Cadena lógica de firma y funciones del plano de control. La raíz firma un emisor; el servicio Identity utiliza ese emisor para firmar certificados de cargas de trabajo. El dibujo no implica que la clave privada de la raíz deba almacenarse en el clúster.](../../.gitbook/assets/en-service-mesh-linkerd-04-security-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-04-security-0.html)

## mTLS automático

Linkerd utiliza mTLS automáticamente para el tráfico TCP entre Pods de la malla que cumplen sus requisitos. Ambos proxies deben participar, confiar en la cadena de certificados y recibir el tráfico. Los puertos excluidos evitan el proxy; UDP queda fuera de este mecanismo TCP. El tráfico hacia o desde endpoints ajenos a la malla no obtiene mTLS de Linkerd por el mero hecho de que uno de los extremos tenga un proxy.

Si una aplicación utiliza HTTP sin cifrar, el proxy saliente autentica al proxy de destino y cifra el salto de red. El proxy receptor autentica al cliente y reenvía HTTP a su aplicación local. Cuando la propia aplicación utiliza TLS, el tráfico puede permanecer cifrado al atravesar la malla: Linkerd no descifra automáticamente todos los flujos TLS externos u opacos.

| Propiedad | Alcance y límites |
|---|---|
| Cifrado transparente | El salto entre proxies que cumple los requisitos de mTLS no requiere que la aplicación implemente TLS |
| Autenticación mutua | Los proxies autentican las identidades de las cargas de trabajo, no las de los usuarios finales |
| TLS 1.3 | Protocolo TLS de la malla en la versión seleccionada |
| Renovación automática de certificados de las cargas de trabajo | Los proxies suelen renovar sus certificados de corta duración |
| Ciclo de vida de la raíz y del emisor | Credenciales independientes que también requieren rotación y monitorización |

De forma predeterminada, Linkerd acepta tráfico sin cifrar procedente de orígenes ajenos a la malla. Las políticas de autorización pueden rechazarlo. Por tanto, habilitar mTLS no implica que todo acceso entrante requiera una identidad autenticada de la malla. Las políticas de red y los controles de admisión también deben cubrir las rutas que evitan el proxy o no lo utilizan.

### Observar el cifrado y la identidad

```bash
linkerd check --proxy
linkerd viz edges deploy -n production
linkerd viz tap deploy/api -n production --method GET
linkerd identity -n production -l app=api
kubectl -n production get pods -l app=api \
  -o custom-columns=NAME:.metadata.name,SERVICEACCOUNT:.spec.serviceAccountName
```

`viz edges` muestra las conexiones observadas entre recursos y su estado de seguridad; no enumera todas las conexiones posibles o inactivas. `tap` muestra el tráfico observado que admite la herramienta, pero no constituye una auditoría completa de paquetes o de seguridad. Su visualización tampoco equivale a los valores de las etiquetas TLS de Prometheus. Compruebe tanto el tráfico aceptado como el denegado deliberadamente desde las identidades de cliente previstas.

`linkerd identity` obtiene certificados públicos de los Pods seleccionados mediante reenvío de puertos. Inspeccione sus SAN, el emisor y el periodo de validez. Así evita dar por hecho que el certificado emitido para la carga de trabajo está disponible en una ruta fija dentro de la imagen del proxy.

## Identidad de cargas de trabajo

En el mecanismo estándar de identidad de Kubernetes, Linkerd utiliza una identidad con este formato DNS:

```text
<service-account>.<namespace>.serviceaccount.identity.<control-plane-namespace>.<trust-domain>

web.production.serviceaccount.identity.linkerd.cluster.local
api.production.serviceaccount.identity.linkerd.cluster.local
```

Los ejemplos utilizan el espacio de nombres del plano de control `linkerd` y el dominio de confianza `cluster.local`. El nombre común del certificado raíz no determina por sí solo el dominio de confianza de las cargas de trabajo. La identidad DNS de Linkerd difiere de la URI de Istio `spiffe://.../ns/.../sa/...` que figuraba anteriormente en esta sección. Varios Pods con el mismo ServiceAccount comparten una identidad de autorización, aunque cada uno tiene sus propias claves privadas y certificados.

El proxy genera su clave y CSR, y envía el CSR con su token proyectado de ServiceAccount a Identity. Identity valida el token mediante TokenReview de Kubernetes, comprueba la identidad solicitada y firma con la clave **del emisor**. La raíz firma el emisor; no firma cada solicitud del proxy. La clave privada no se deriva del token de ServiceAccount.

Los certificados predeterminados de las cargas de trabajo duran unas 24 horas y se renuevan antes de caducar. Solicitar un certificado no crea un nuevo ServiceAccount de Kubernetes, y la renovación no demuestra que todas las claves roten en cada actualización. Consulte el ciclo de vida en la [guía de arquitectura](02-architecture.md).

## Políticas de autorización

Estos recursos pertenecen a la API `policy.linkerd.io` de Linkerd. `AuthorizationPolicy` no es un recurso de Gateway API; se introdujo en Linkerd 2.12. Puede dirigirse a rutas que utilizan definiciones de Gateway API.

| Recurso | Función |
|---|---|
| Server | Selecciona un puerto entrante declarado en Pods coincidentes de su espacio de nombres |
| HTTPRoute/GRPCRoute asociado a Server | Selecciona un subconjunto de solicitudes entrantes |
| MeshTLSAuthentication | Describe las identidades de malla permitidas |
| NetworkAuthentication | Describe las redes IP de clientes permitidas; no proporciona mTLS |
| AuthorizationPolicy | Concede acceso a un destino cuando coinciden sus requisitos de autenticación |
| ServerAuthorization | Concesión anterior solo para Server; compatible como `v1beta1` en los CRD seleccionados |

`ServerAuthorization` y `AuthorizationPolicy` son mecanismos alternativos para conceder acceso, no etapas de una secuencia. Varias concesiones pueden ampliar el acceso; en cambio, deben cumplirse **todos** los requisitos de varias `requiredAuthenticationRefs` dentro de una misma AuthorizationPolicy. Una AuthorizationPolicy cuyo destino es un espacio de nombres abarca los destinos de políticas definidos en él, pero no aplica automáticamente una política a cada puerto no declarado.

Los Servers no deben seleccionar combinaciones de Pod y puerto que se solapen. Declare el puerto de la aplicación en la especificación del Pod. Un Server deniega de forma predeterminada el tráfico que no coincide con una autorización, incluso si la política predeterminada del espacio de nombres es permisiva. `accessPolicy: audit` permite observar ese tráfico durante la preparación, pero lo deja pasar y no impone una restricción.

### Política predeterminada

Esta anotación configura proxies recién creados en un espacio de nombres incorporado:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  annotations:
    linkerd.io/inject: enabled
    config.linkerd.io/default-inbound-policy: deny
```

Cambiar la anotación del espacio de nombres no modifica el valor predeterminado con el que ya se inicializaron los proxies existentes. Coordine la actualización de cada carga de trabajo y compruebe que esté preparada para recibir tráfico. Los CRD de políticas dinámicas funcionan por separado y pueden actualizar las políticas sin sustituir todos los Pods.

El valor de Helm para todo el clúster es `proxy.defaultInboundPolicy`, no `policyController.defaultPolicy`. Incorpórelo a los valores completos de instalación, conservando la configuración de la CA y la gestión de la release:

```yaml
proxy:
  defaultInboundPolicy: deny
```

| Valor predeterminado | Significado |
|---|---|
| all-unauthenticated | Permite tráfico sin exigir autenticación de malla; valor predeterminado de instalación |
| all-authenticated | Requiere clientes autenticados de la malla, incluidos clientes multiclúster con confianza apropiada |
| cluster-authenticated | Requiere clientes autenticados del mismo clúster |
| cluster-unauthenticated | Permite clientes del ámbito de red del clúster configurado sin exigir autenticación de malla |
| deny | Deniega tráfico no coincidente, sujeto a políticas explícitas y al tratamiento documentado de sondas |
| audit | Permite tráfico no coincidente mientras registra evidencia de auditoría |

El ámbito de clúster no es una identidad de usuario final ni un límite de autorización de la aplicación. Verifique las redes configuradas y las direcciones de origen visibles en el proxy.

### Ejemplo de microservicios

Para estos recursos de ejemplo independientes, prepare cargas de trabajo frontend, API y PostgreSQL incorporadas a la malla en `production`, con `app: frontend/api/postgres`, los puertos declarados a continuación y sus ServiceAccounts correspondientes. Prepare también la carga de trabajo de entrada de la malla con el ServiceAccount `edge-gateway` en el espacio de nombres `ingress`; utilizar ese nombre no instala ni autentica un gateway.

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: frontend-http
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: frontend-from-gateway
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: frontend-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: edge-gateway
    namespace: ingress
---
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: api-http
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: api-from-frontend
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: api-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: frontend
    namespace: production
---
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: database-tcp
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres
  port: 5432
  proxyProtocol: opaque
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: database-tcp
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: api
    namespace: production
```

La cadena de llamadas prevista es gateway → frontend → API → base de datos. Escribir el nombre de un ServiceAccount en YAML no basta: el cliente debe presentar la identidad autenticada de esa cuenta. Compruebe que ninguna otra concesión más amplia, aplicada al espacio de nombres o al Server, permita el acceso de clientes no deseados.

Linkerd suele añadir autorizaciones para las sondas HTTP de estado y disponibilidad declaradas cuando el Server no tiene una ruta explícita asociada. Si se asocian recursos HTTPRoute o GRPCRoute, esas autorizaciones predeterminadas no se crean. Defina expresamente las rutas necesarias para las sondas y limite su acceso. No permita acceso sin autenticar a todo un puerto de la aplicación para que una sola sonda funcione.

Como referencia, esta **concesión heredada alternativa** permite al frontend acceder a la aplicación API, igual que la autorización anterior. No es necesario combinarla con la AuthorizationPolicy precedente:

```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: ServerAuthorization
metadata:
  name: api-from-frontend-legacy
  namespace: production
spec:
  server:
    name: api-http
  client:
    meshTLS:
      serviceAccounts:
      - name: frontend
        namespace: production
```

La versión seleccionada no expone `ServerAuthorization/v1beta2`; no deduzca la versión de API de un recurso a partir de la versión de Server. `client.unauthenticated:true` permite clientes sin autenticación de malla, mientras que `meshTLS.identities:["*"]` sigue exigiendo una identidad de malla y concede acceso de forma muy amplia.

### Puertos de métricas y verificación

Para un **puerto de métricas de aplicación 9091** declarado explícitamente en el Pod de API, una concesión de ejemplo es:

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: api-app-metrics
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  port: 9091
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: metrics-from-prometheus
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: api-app-metrics
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: prometheus
    namespace: monitoring
```

Este puerto es distinto del puerto de administración del propio proxy, normalmente **4191**. La configuración de proxy-init excluye los puertos de administración y control de la interceptación entrante habitual. Por tanto, definir un Server en 4191 no convierte ese endpoint en un puerto de aplicación protegido con mTLS. Proteja los endpoints de gestión mediante los controles efectivos del clúster y de la red, y con rutas de acceso restringidas.

```bash
kubectl -n production get servers,authorizationpolicies,serverauthorizations
kubectl -n production get server api-http -o yaml
# Set this to an actual selected API Pod.
api_pod=api-example-pod
linkerd diagnostics policy -n production "pod/$api_pod" 8080 -o json
linkerd viz authz deploy/api -n production
```

Un rechazo HTTP identificado como una denegación de política suele devolver HTTP 403; el tráfico opaco o TCP puede rechazarse al establecer la conexión. Cambiar una política puede interrumpir las conexiones existentes. Los eventos `Forbidden` de Kubernetes no registran automáticamente cada solicitud denegada por la autorización del proxy. Utilice los diagnósticos de políticas y las métricas de autorización HTTP y TCP correspondientes.


## Gestión de certificados

| Credencial | Finalidad | Gestión predeterminada y consideraciones para la gestión manual |
|---|---|---|
| Paquete de certificados de las anclas de confianza | Raíces públicas que acepta la malla | Normalmente, ConfigMap `linkerd-identity-trust-roots`, clave `ca-bundle.crt` |
| Certificado y clave del emisor de identidad | CA intermedia que utiliza Identity para firmar los certificados de las cargas de trabajo | Secret `linkerd-identity-issuer`; los nombres de las claves dependen del esquema del emisor |
| Certificado y clave de la carga de trabajo | Credencial TLS de cada proxy | Certificado de corta duración que el proxy renueva automáticamente |

La raíz y el emisor generados con la configuración predeterminada de la CLI caducan al cabo de un año; los certificados de las cargas de trabajo suelen durar 24 horas. Se puede elegir manualmente una raíz válida durante diez años, pero no es una recomendación universal ni la configuración predeterminada de instalación. Defina los periodos de validez y la antelación de la renovación según la política de la CA y el proceso de recuperación, y supervise todos los certificados de la cadena.

Las credenciales de la raíz y del emisor que se proporcionan a Linkerd requieren **ECDSA P-256**. La [guía de instalación](01-installation.md) especifica los parámetros de generación y el manejo local de las claves privadas. Mantenga la clave de firma de la raíz separada del paquete público de confianza; un ConfigMap público nunca debe contener esa clave.

### Consultar las credenciales públicas en uso

```bash
set -euo pipefail
umask 077
# Public trust bundle: ConfigMap data is not base64-encoded.
kubectl -n linkerd get configmap linkerd-identity-trust-roots -o json \
  | jq -er '.data["ca-bundle.crt"] | select(length > 0)' > current-trust.pem
# Select only public certificate data from the issuer Secret, never its key.
kubectl -n linkerd get secret linkerd-identity-issuer -o json \
  | jq -er '(.data["tls.crt"] // .data["crt.pem"]) | select(length > 0)' \
  | base64 -d > current-issuer.pem

# Show every certificate in a multi-root bundle, not only its first entry.
openssl crl2pkcs7 -nocrl -certfile current-trust.pem \
  | openssl pkcs7 -print_certs -text -noout
openssl x509 -in current-issuer.pem -noout -subject -issuer -dates
# Nonzero exit means expiration is within this window or parsing failed.
openssl x509 -in current-issuer.pem -noout -checkend 86400
```

Con el esquema predeterminado `linkerd.io/tls`, el Secret del emisor utiliza `crt.pem`/`key.pem`; `kubernetes.io/tls` utiliza `tls.crt`/`tls.key`. El comando selecciona únicamente datos de certificados públicos. Compruebe el esquema configurado y el responsable del recurso antes de cambiar nada.

Inspeccione todas las raíces del paquete. `openssl x509` por sí solo examina únicamente el primer certificado y no permite auditar la caducidad de un paquete con varias raíces. Además de comprobar las fechas, valide la cadena del emisor frente a las anclas de confianza previstas e incluya los certificados intermedios que requiera la cadena. Un fallo de análisis o de lectura de la API debe registrarse como tal, no como una confirmación de que el certificado está en buen estado.

### Renovación del emisor sin cambiar el ancla de confianza

Actualice el emisor mediante la herramienta o el controlador que lo gestiona: proporcione los valores completos de certificados de Helm o de la CLI para un Secret gestionado por Linkerd, o utilice el controlador de certificados si este gestiona el Secret. Identity vigila los archivos del emisor que tiene montados, valida el reemplazo y recarga el emisor si es válido. No es necesario reiniciar el Deployment de Identity en cada renovación.

```bash
kubectl -n linkerd get events --field-selector reason=IssuerUpdated
kubectl -n linkerd get events --field-selector reason=IssuerUpdateSkipped
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
linkerd check --proxy
linkerd identity -n production -l app=api
```

`IssuerUpdated` confirma que Identity aceptó una actualización. Investigue `IssuerUpdateSkipped` y los errores de validación. Los certificados de los proxies existentes pueden seguir firmados por el emisor anterior hasta su renovación habitual; es normal mientras ambas cadenas sigan siendo válidas. Sustituir de inmediato todos esos certificados requiere una operación coordinada independiente sobre las cargas de trabajo.

### Rotación del ancla de confianza

Sustituir una raíz requiere una transición por etapas. El procedimiento previsto para una raíz válida no garantiza la recuperación cuando la raíz ya ha caducado.

1. Inventaríe el paquete de raíces activo, la cadena del emisor, los recursos gestionados y todos los consumidores: proxies del plano de control, cargas de trabajo internas y externas, y clústeres vinculados. Compruebe la capacidad y la disponibilidad necesarias para la actualización prevista.
2. Genere la nueva raíz y conserve el **paquete público con la raíz anterior y la nueva**. Actualice el paquete mediante la herramienta o el controlador que lo gestiona.
3. Distribuya ese paquete con ambas raíces a todos los consumidores antes de cambiar el emisor. Los proxies reciben la configuración de confianza durante la instalación o la inyección; escribir un ConfigMap no demuestra que los procesos existentes la hayan recargado.
4. Verifique la distribución con `linkerd check --proxy` y con comprobaciones de las cargas de trabajo y de las conexiones entre clústeres. Después, emita y cargue un emisor firmado por la nueva raíz.
5. Permita o coordine expresamente la renovación de los certificados de las cargas de trabajo. Compruebe que todos los clientes y servidores pertinentes utilicen la nueva cadena. Una espera fija o una actualización correcta del controlador, por sí solas, no bastan.
6. Elimine la raíz anterior mediante el responsable del paquete, distribuya el paquete definitivo a todos los consumidores y vuelva a comprobar las conexiones y la confianza.

Conserve los elementos necesarios para revertir el cambio y supervise cada etapa. Reinicie únicamente los controladores de cargas de trabajo de la malla que haya revisado, con las comprobaciones de disponibilidad y el manejo de interrupciones adecuados para cada carga. Un bucle que reinicia los Deployments de todos los espacios de nombres omite otros tipos de cargas de trabajo y puede interrumpir aplicaciones ajenas al cambio. La ausencia de interrupciones no está garantizada en una rotación que no se haya probado.

## Gestión externa de certificados

### Renovación del emisor con cert-manager

Este ejemplo presupone que el Secret `linkerd-trust-anchor`, en el espacio de nombres `linkerd`, ya contiene un certificado de CA validado y una clave de firma ECDSA P-256. Un CA Issuer de cert-manager conserva esa clave de firma en el clúster; elija otra integración de CA si esto no encaja con su modelo de confianza. La versión seleccionada de cert-manager debe admitir la versión de Kubernetes del clúster.

```yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: linkerd-trust-anchor
  namespace: linkerd
spec:
  ca:
    secretName: linkerd-trust-anchor
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
spec:
  secretName: linkerd-identity-issuer
  duration: 8760h
  renewBefore: 720h
  issuerRef:
    name: linkerd-trust-anchor
    kind: Issuer
    group: cert-manager.io
  commonName: identity.linkerd.cluster.local
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
    rotationPolicy: Always
  usages:
  - cert sign
  - crl sign
  - server auth
  - client auth
```

El emisor es una CA porque firma los certificados de las cargas de trabajo. `rotationPolicy: Always` establece explícitamente la rotación de claves. En este ejemplo, 8760h equivalen a 365 días y `renewBefore:720h` indica una renovación **30 días antes de la caducidad**, no cada 30 días. Compruebe que la CA superior siga siendo válida durante el tiempo necesario: el CA Issuer no impone automáticamente todas las restricciones de validez de la cadena o de longitud de ruta. Actualizar su Secret de CA tampoco vuelve a emitir automáticamente todos los certificados que dependen de ella.

```bash
kubectl -n linkerd get issuer linkerd-trust-anchor
kubectl -n linkerd get certificate linkerd-identity-issuer
kubectl -n linkerd describe certificate linkerd-identity-issuer
# Inspect public certificate contents and effective issuer loading as above.
```

La integración solo estará operativa cuando el Certificate esté Ready, su Secret contenga las claves y la cadena esperadas, e Identity lo haya aceptado.

### Elegir explícitamente quién gestiona el paquete de confianza

**Opción A: cert-manager gestiona el emisor; Helm gestiona el paquete público de confianza.** Guarde esto como `managed-issuer-values.yaml` y proporcione el paquete raíz mediante los valores completos y revisados del chart:

```yaml
identity:
  externalCA: false
  issuer:
    scheme: kubernetes.io/tls
```

```bash
# Merge into the complete reviewed values from the installation guide.
# In this option, Helm owns the public trust bundle; cert-manager owns the issuer.
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.10.1 -n linkerd \
  -f reviewed-values.yaml -f managed-issuer-values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt > reviewed-control-plane.yaml
```

Con `kubernetes.io/tls`, el chart espera que el Secret del emisor ya exista, en lugar de crear uno en formato Linkerd. Con `externalCA:false`, Helm sigue creando el ConfigMap público de confianza. Revise los objetos renderizados y quién los gestiona antes de desplegarlos mediante el flujo de instalación.

**Opción B: un controlador externo también gestiona el ConfigMap de confianza.** En ese modelo distinto de gestión:

```yaml
identity:
  externalCA: true
  issuer:
    scheme: kubernetes.io/tls
```

`identity.externalCA:true` significa que el chart **no** crea `linkerd-identity-trust-roots`. Un controlador externo como trust-manager debe proporcionar ese ConfigMap en el espacio de nombres del plano de control con `ca-bundle.crt`. Pasar únicamente `identityTrustAnchorsPEM` y omitir el ConfigMap externo no completa esta configuración.

Al rotar raíces gestionadas, conserve el **certificado público** anterior en el paquete que contiene ambas raíces. Coordine la renovación del emisor y la actualización de los consumidores antes de retirar la raíz anterior. No copie un Secret de CA completo solo para conservar su certificado público. cert-manager y trust-manager no automatizan todos los reinicios de cargas de trabajo ni todas las transiciones de confianza.

### Límite de la integración con Vault

Vault puede formar parte del diseño de la CA, pero un procedimiento habitual de firma de certificados de cargas de trabajo mediante PKI `sign/<role>` no constituye un flujo completo para el emisor de Linkerd. Linkerd requiere un certificado real de CA intermedia; establecer `isCA:true` en un recurso Certificate no demuestra por sí solo que el endpoint de Vault permita emitirlo.

Verifique el endpoint de firma y cómo la integración seleccionada traduce las solicitudes y las respuestas. Vault documenta el endpoint privilegiado `root/sign-intermediate` y otros endpoints de firma intermedia específicos del emisor. Autorizar su uso permite emitir certificados de CA y requiere un rol y una política deliberadamente restringidos. Valide también ECDSA P-256, la cadena devuelta, la validez del emisor, la confianza en el servidor de Vault y el comportamiento de la renovación.

Para autenticar cert-manager, utilice preferentemente el flujo documentado de tokens de ServiceAccount de corta duración cuando corresponda. Configure el RBAC de TokenRequest necesario, la autenticación Kubernetes o JWT de Vault y las audiencias. Crear un Secret llamado `vault-token` no basta. El YAML anterior omitía estos requisitos y no demostraba una vía funcional para emitir una CA intermedia; por ello, no se ofrece como un procedimiento de despliegue probado.

## Seguridad de la aplicación y monitorización

| Responsabilidad | Aportación de Linkerd | Controles adicionales |
|---|---|---|
| Salto de red | mTLS entre proxies aptos | TLS para otros saltos, restricciones de red y exposición de endpoints |
| Autenticación de cargas de trabajo | Identidad de malla derivada de ServiceAccount | Autenticación de usuarios finales/clientes de API y validación de tokens |
| Acceso a servicios | Políticas de autorización entrante | Roles de aplicación, autorización de inquilinos y objetos |
| Tratamiento de datos | No valida entradas de negocio | Validación de entradas, tratamiento de salidas y protección de datos |

Una identidad frontend permitida no demuestra que su cliente sea administrador. Las aplicaciones deben validar las credenciales de usuario y los permisos de negocio, además de las entradas.

### Alertas de seguridad significativas

Las reglas siguientes requieren Prometheus Operator y una instancia de Prometheus que seleccione este PrometheusRule. La recopilación de métricas debe conservar las etiquetas mostradas de espacio de nombres, Deployment e identidad TLS del proxy. En backends compartidos, revise qué destinos y clústeres abarca cada regla.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: linkerd-security-alerts
  namespace: monitoring
spec:
  groups:
  - name: linkerd-security
    rules:
    - alert: LinkerdWorkloadCertificateExpiring
      expr: identity_cert_expiration_timestamp_seconds{namespace="production"} - time() < 3600
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Proxy workload certificate has less than one hour remaining
    - alert: LinkerdIssuerCertificateExpiring
      expr: issuer_cert_ttl_seconds{job="linkerd-controller",component="identity"} < 86400
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Identity issuer has less than one day remaining
    - alert: LinkerdInboundHTTPWithoutMeshIdentity
      expr: |-
        ((sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) - (sum(rate(response_total{namespace="production",deployment="api",direction="inbound",tls="true",client_id!=""}[5m])) or vector(0))) / sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) > 0.10)
        and on() (sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: More than 10% of observed API HTTP responses lack authenticated mesh client identity
    - alert: LinkerdInboundHTTPAuthorizationDenied
      expr: sum(rate(inbound_http_authz_deny_total{namespace="production",deployment="api"}[5m])) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: API inbound HTTP authorization denials observed
```

`identity_cert_expiration_timestamp_seconds` indica el **momento absoluto en que caduca el certificado de la carga de trabajo del proxy**. Un aviso con siete días de antelación se activaría siempre para un certificado predeterminado válido de 24 horas. La métrica del controlador `issuer_cert_ttl_seconds` ya expresa el tiempo restante; no le reste `time()`. Su selector utiliza las etiquetas predeterminadas de job y componente del controlador Viz; esa recopilación no añade una etiqueta de espacio de nombres. Adapte el selector si un recopilador personalizado cambia esas etiquetas. Ajuste los umbrales a la validez configurada de las credenciales y al intervalo de renovación previsto. Supervise por separado las raíces públicas y la disponibilidad de la recopilación.

En el proxy seleccionado, las etiquetas TLS incluyen `true`, `no_identity`, `disabled` y `opaque`; la consulta original `tls="false"` no seleccionaba las series previstas. `tls="true"` por sí sola tampoco garantiza la presencia de una identidad de cliente. El ejemplo compara las respuestas HTTP entrantes completadas por la aplicación API con las que incluyen tanto TLS como un `client_id` autenticado no vacío. Utiliza tasas y una condición que exige tráfico positivo.

Esta proporción **no expresa el porcentaje de todos los bytes de red ni de todo el tráfico sin cifrar**. No incluye las rutas que evitan el proxy ni TCP opaco, y depende de que se conserven las etiquetas de identidad. Las sondas previstas y las rutas deliberadamente sin autenticación necesitan un ámbito y una referencia propios. Si todo el tráfico está autenticado y no existe una serie de tráfico sin autenticar, la proporción subyacente es cero y la alerta no se activa. La ausencia de tráfico o de datos no demuestra que el sistema sea seguro.

Los contadores de denegación de autorización HTTP son distintos de los fallos de inicio de sesión de la aplicación. Utilice los contadores de autorización TCP para las conexiones opacas; si falta una recopilación de métricas, no deduzca que no hubo denegaciones. Los registros y las métricas del modo de auditoría reflejan tráfico que no coincide con una autorización pero se permite, no rechazos efectivos.

## Siguientes pasos y referencias

- [Observabilidad](05-observability.md), [multiclúster](06-multi-cluster.md), [buenas prácticas](07-best-practices.md), [cuestionario de seguridad](../../quizzes/service-mesh/linkerd/security.md)
- [mTLS automático](https://linkerd.io/docs/features/automatic-mtls/)
- [Comportamiento de autorización](https://linkerd.io/docs/features/server-policy/) y [referencia de API](https://linkerd.io/docs/reference/authorization-policy/)
- [CLI de identidad](https://linkerd.io/docs/reference/cli/identity/)
- [Rotación manual de credenciales](https://linkerd.io/docs/tasks/manually-rotating-control-plane-tls-credentials/)
- [Rotación gestionada de credenciales](https://linkerd.io/docs/tasks/automatically-rotating-control-plane-tls-credentials/)
- [Métricas del proxy](https://linkerd.io/docs/reference/proxy-metrics/)
- [Implementación publicada de recarga de Identity/métricas del emisor](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/pkg/identity/service.go)
- [Gestión de credenciales del chart publicado](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/charts/linkerd-control-plane/templates/identity.yaml)
- [CA Issuer de cert-manager](https://cert-manager.io/docs/configuration/ca/) y [autenticación de Vault](https://cert-manager.io/docs/configuration/vault/)
- [Firma intermedia de Vault](https://developer.hashicorp.com/vault/api-docs/secret/pki#sign-intermediate)
