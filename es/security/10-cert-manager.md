# Gestión de certificados con cert-manager

> **Última actualización**: 16 de octubre de 2026
> **Base de validación**: cert-manager 1.21.2, cmctl 2.6.1, trust-manager 0.25.0, istio-csr 0.18.0, aws-privateca-issuer 1.9.2, ACK ACM 1.8.1. El intervalo de versiones de Kubernetes que cert-manager 1.21 publica como compatibles o probadas es 1.33–1.36. Kubernetes 1.37 queda fuera de ese intervalo, por lo que esta guía no afirma que sea compatible.

cert-manager gestiona la emisión y la renovación de certificados mediante recursos de Kubernetes. **La distribución de la confianza en las CA, la recarga de las aplicaciones, la revocación y las operaciones de CRL y OCSP siguen siendo responsabilidades independientes.** Los ejemplos se comprobaron con esquemas, configuración y bibliotecas locales; no demuestran una emisión mediante una CA externa ni un despliegue en AWS o Kubernetes. Una prueba independiente con una instancia local efímera de Vault 2.1.0 utilizó una CA sintética para dieciséis casos de aceptación y rechazo de emisión de certificados y firma de CSR.

<span id="what-cert-manager-solves"></span>
<span id="project-status"></span>
<span id="why-certificate-lifecycle-automation-matters"></span>
<span id="overview-1"></span>

## Descripción general

cert-manager se incorporó a CNCF el 10 de noviembre de 2020, pasó a la fase Incubating el 19 de septiembre de 2022 y **alcanzó la fase Graduated el 29 de septiembre de 2024**. Esta graduación no garantiza la seguridad ni la disponibilidad de un despliegue concreto.

| Aspecto del ciclo de vida | Responsabilidad |
|---|---|
| Emisión | Autenticar el Issuer, aprobar al solicitante y definir las políticas de SAN, usos y validez |
| Renovación | Considerar la validez realmente emitida, ARI y renewBefore, los reintentos y las alertas |
| Rotación de claves | Controlar el acceso al Secret, la recarga del consumidor y el orden de sustitución de las CA |
| Confianza | Definir en qué raíces y certificados intermedios confía cada espacio de nombres o proceso |
| Revocación | Establecer el procedimiento de revocación de la CA y la publicación y el consumo de CRL y OCSP |

No utilice la antigua instalación 1.16.2 ni su tabla de compatibilidad como referencia de soporte actual. La versión 1.16 llegó al fin de su soporte en junio de 2025. Planifique las actualizaciones teniendo en cuenta las notas de las versiones intermedias y los cambios de CRD.

<span id="component-overview"></span>
<span id="component-responsibilities"></span>
<span id="certificate-issuance-flow"></span>

## Arquitectura

![Componentes de cert-manager y relaciones entre Issuer y Secret](../.gitbook/assets/en-security-10-cert-manager-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-0.html)

El controlador reconcilia los Certificates y crea CertificateRequests; los controladores de Issuer gestionan la emisión. El webhook valida los recursos personalizados, les asigna valores predeterminados y los convierte. cainjector gestiona los paquetes de CA en las configuraciones de API y webhook compatibles. Los Issuers CA y SelfSigned no son necesariamente servicios externos.

<span id="prerequisites"></span>
<span id="installation-with-helm-recommended"></span>
<span id="production-helm-values"></span>
<span id="installation-with-kubectl"></span>
<span id="verify-installation"></span>

## Instalación

Compruebe las versiones de Kubernetes admitidas, los permisos de Helm y del clúster, los CRD de Gateway API y la presencia de un controlador de Gateway operativo, además de los CRD opcionales de Prometheus Operator. Si instala los CRD de Gateway API después de arrancar el controlador, compruebe los requisitos de reinicio y descubrimiento.

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update jetstack
helm upgrade --install cert-manager jetstack/cert-manager \
  --version v1.21.2 --namespace cert-manager --create-namespace \
  --values cert-manager-values.yaml
kubectl get pods -n cert-manager
cmctl check api
```

```yaml
crds:
  enabled: true
  keep: true
replicaCount: 2
podDisruptionBudget:
  enabled: true
  minAvailable: 1
config:
  apiVersion: controller.config.cert-manager.io/v1alpha1
  kind: ControllerConfiguration
  gatewayAPI:
    enabled: true
prometheus:
  enabled: true
  servicemonitor:
    enabled: true
webhook:
  replicaCount: 2
  timeoutSeconds: 10
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
cainjector:
  replicaCount: 2
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
```

Este perfil habilita ServiceMonitor y Gateway API, por lo que sus CRD y controladores deben existir previamente. Deshabilite esas opciones si necesita una instalación mínima sin esas dependencias. Las réplicas y los PDB no sustituyen la distribución entre nodos y zonas de disponibilidad ni la conectividad con la API. La configuración actual utiliza config.gatewayAPI.enabled; el decodificador de 1.21.2 todavía acepta el antiguo campo enableGatewayAPI, pero está obsoleto.

Compruebe la retención de los CRD y qué herramienta o responsable gestiona la desinstalación. Eliminar un CRD puede borrar sus recursos personalizados; no es un paso habitual para resolver problemas de actualización.

<span id="custom-resource-definitions-crds"></span>
<span id="certificate-resource"></span>
<span id="issuer-vs-clusterissuer"></span>
<span id="certificaterequest-resource"></span>

## Conceptos básicos

![Recursos Certificate y solicitudes creadas por el controlador](../.gitbook/assets/en-security-10-cert-manager-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-1.html)

| Recurso | Ámbito y finalidad |
|---|---|
| Certificate | Certificado deseado y Secret de salida dentro de un espacio de nombres |
| Issuer | Configuración de emisión a la que se hace referencia dentro de su espacio de nombres |
| ClusterIssuer | Configuración de emisión a la que se puede hacer referencia desde distintos espacios de nombres |
| CertificateRequest | CSR, issuerRef y estado de aprobación o denegación |
| Order/Challenge | Recursos de solicitud y validación utilizados en el flujo ACME |

Los Secrets de credenciales y de CA de un ClusterIssuer se almacenan en el espacio de nombres de recursos de clúster del controlador, que es cert-manager de forma predeterminada. Los Secrets de un Issuer se almacenan en el espacio de nombres de ese Issuer. El permiso para crear un Certificate no restringe, por sí solo, los SAN ni issuerRef.

### Certificate y renovación

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: demo-app
spec:
  secretName: app-tls
  dnsNames: [app.example.com]
  duration: 2160h
  renewBeforePercentage: 33
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Always
  usages: [server auth]
  issuerRef:
    name: lab-ca
    kind: ClusterIssuer
    group: cert-manager.io
```

La validez solicitada puede diferir de la que emite la CA. De forma predeterminada, la renovación se produce **cuando han transcurrido dos tercios de la validez real del certificado X.509**, no un número fijo de 15 o 30 días antes de la caducidad. renewBeforePercentage calcula el margen a partir de esa validez real. Elija renewBefore o el porcentaje, no ambos: duration debe ser de al menos una hora, y el margen efectivo de renovación debe ser de al menos cinco minutos y menor que duration.

La política y las ventanas de renovación de 1.21.2, junto con los flujos ARI admitidos, pueden afectar al momento de la renovación. renewal.policy:Disabled deshabilita la renovación automática. Inspeccione status.renewalTime, los valores reales de notBefore y notAfter, y las alertas de fallo. Desde 1.18, privateKey.rotationPolicy tiene Always como valor predeterminado. Actualizar un Secret de clave y certificado no garantiza que la aplicación los recargue.

### CertificateRequest y claves privadas

Las solicitudes directas requieren una CSR real en formato PEM; no aplique ejemplos con base64 truncado. cmctl create certificaterequest **crea una solicitud en el clúster** y no es un comando de validación sin conexión. Restrinja por separado los permisos de cmctl approve y deny. Esta auditoría utilizó la biblioteca PKI de cert-manager únicamente para generar y verificar una clave y una CSR sintéticas locales.

<span id="selfsigned-issuer-development-testing"></span>
<span id="ca-issuer-internal-pki"></span>
<span id="acme-let-s-encrypt"></span>
<span id="acme-challenge-types"></span>
<span id="http-01-solver"></span>
<span id="dns-01-solver-with-route53-and-irsa"></span>
<span id="aws-private-ca-issuer"></span>
<span id="hashicorp-vault-pki"></span>

## Tipos de Issuer

### Inicialización con SelfSigned y CA

El [ejemplo completo de inicialización](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/bootstrap.yaml) crea una raíz dedicada de laboratorio y un certificado para una carga de trabajo. La raíz utiliza explícitamente la renovación Disabled y la rotación de clave Never para evitar la **sustitución no planificada del ancla de confianza**. La custodia de la raíz de producción, las CA sin conexión, la separación de certificados intermedios, la auditoría y la revocación requieren un diseño independiente.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cert-manager
  labels:
    trust-bundle: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: demo-app
  labels:
    trust-bundle: enabled
    cert-manager-http01: enabled
---
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: bootstrap
  namespace: cert-manager
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: lab-root
  namespace: cert-manager
spec:
  secretName: lab-root
  isCA: true
  commonName: Documentation Lab Root
  subject:
    organizations: [Documentation Lab]
  duration: 8760h
  renewal:
    policy: Disabled
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Never
  usages: [cert sign, crl sign]
  issuerRef:
    name: bootstrap
    kind: Issuer
    group: cert-manager.io
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: lab-ca
spec:
  ca:
    secretName: lab-root
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: demo-app
spec:
  secretName: app-tls
  dnsNames: [app.example.com]
  duration: 2160h
  renewBeforePercentage: 33
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Always
  usages: [server auth]
  issuerRef:
    name: lab-ca
    kind: ClusterIssuer
    group: cert-manager.io
```

El Issuer CA utiliza un Secret que contiene un certificado de CA y su clave privada. Sustituir ese Secret no vuelve a emitir inmediatamente todos los certificados de las cargas de trabajo ni actualiza los almacenes de confianza de todos los clientes. Los Issuers CA pueden incluir URL de CRL y OCSP, pero no generan ni mantienen las CRL o las respuestas OCSP. Imponga una política que evite que los certificados emitidos caduquen después de su CA.

### ACME: HTTP-01 y DNS-01

![Validación y emisión ACME HTTP/DNS](../.gitbook/assets/en-security-10-cert-manager-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-2.html)

HTTP-01 requiere que el nombre de host sea accesible en el puerto 80 y no admite comodines. DNS-01 utiliza permisos sobre registros DNS TXT para validar comodines. La reutilización de autorizaciones y el flujo de prevalidación de ACM hacen que no sea necesario crear un nuevo Challenge para cada solicitud.

No recomiende el ingress-nginx de la comunidad como opción predeterminada para una instalación nueva, ya que su mantenimiento terminó en marzo de 2026. El [ejemplo HTTP-01 con Gateway](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/public-staging.yaml) presupone un Envoy Gateway instalado y su GatewayClass envoy-gateway. Compruebe la clase en uso y haga que la etiqueta cert-manager-http01:enabled del espacio de nombres del solver coincida con allowedRoutes. La integración automática de certificados de Gateway no instala un controlador de Gateway ni implementa su recarga de TLS.

El [Issuer de Route53](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-issuer.yaml) y la [política IAM](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-policy.json) especifican un hostedZoneID y limitan los cambios a los nombres TXT utilizados por los desafíos. Especificar la zona evita necesitar acceso global a ListHostedZonesByName. Compruebe las credenciales del controlador mediante IRSA o una configuración compatible de Pod Identity, así como cualquier cadena de roles entre cuentas. Seleccionar un espacio de nombres o dnsZones no sustituye la autorización de IAM.

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: public-dns01
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: pki-admin@example.com
    privateKeySecretRef:
      name: public-dns01-account
    solvers:
      - selector:
          dnsZones: [example.com]
        dns01:
          route53:
            region: ap-northeast-2
            hostedZoneID: Z1234567890ABC
```

El entorno de pruebas de Let’s Encrypt tiene límites de solicitudes y raíces en las que los navegadores de producción no confían. Cada entorno tiene sus propias cuentas ACME. Los avisos de caducidad por correo electrónico dejaron de enviarse en 2025; el campo email no sustituye la monitorización de la caducidad. Ante respuestas 429, respete Retry-After y la política correspondiente de reposición de cuota, en lugar de reintentar siempre al cabo de una hora. Las renovaciones ARI y las nuevas emisiones reciben un tratamiento diferente en los límites de solicitudes.

### AWS Private CA

El controlador externo aws-privateca-issuer necesita permisos de emisión y lectura limitados al ARN de la CA, además de una identidad de carga de trabajo de EKS. Las acciones documentadas son acm-pca:DescribeCertificateAuthority, acm-pca:GetCertificate y acm-pca:IssueCertificate; restrinja su Resource al ARN de la CA prevista. Sustituya el ARN de la CA en el [ejemplo](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/pca-issuer.yaml) y valide el modo de CA, la plantilla, el algoritmo, los usos y la validez solicitada. Compruebe por separado los límites y los precios de las CA de corta duración. No omita las comprobaciones de aprobación mediante disableApprovedCheck.

```bash
helm repo add awspca https://cert-manager.github.io/aws-privateca-issuer
helm upgrade --install aws-pca-issuer awspca/aws-privateca-issuer \
  --version v1.9.2 --namespace cert-manager
```

### Vault PKI

El [ejemplo de Issuer y RBAC para tokens](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-issuer.yaml) limita la creación de tokens a demo-app/vault-issuer. Proporcione por separado el Secret de la CA TLS del servidor Vault. El [script de rol y política PKI](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-setup.sh) presupone montajes de PKI y autenticación Kubernetes ya existentes, una identidad de Vault aprobada y acceso a TokenReview configurado.

Limite los SAN en el rol de Vault y vincule la audiencia vault://demo-app/vault-pki a este Issuer. Los JWT del revisor, las audiencias de la API de Kubernetes y el acceso OIDC dependen de dónde se ejecute Vault. No intente sortear problemas de conectividad mediante tls-skip-verify ni mediante una política predeterminada de Vault con permisos amplios.

<span id="tls-termination-comparison"></span>
<span id="alb-ingress-with-acm-vs-cert-manager"></span>
<span id="nlb-with-tls-termination-at-ingress-controller"></span>
<span id="gateway-api-integration"></span>

El rol DNS establece explícitamente allow_ip_sans=false y allow_localhost=false. allowed_domains no restringe los SAN de direcciones IP, y localhost tiene su propio valor predeterminado permisivo. Un POST realizado con vault write restablece los campos del rol que se omitan a sus valores predeterminados. Tras aplicarlo, consulte el rol completo y pruebe tanto las solicitudes DNS permitidas como el rechazo de las solicitudes de IP y localhost.

## Patrones de integración de EKS

| Ruta | Terminación de TLS y ubicación de la clave |
|---|---|
| Listener TLS de ALB o NLB con ACM | El balanceador de carga de AWS utiliza un ARN de ACM |
| NLB TCP con Gateway o Pod | El backend termina TLS mediante un Secret de Kubernetes |
| Listener HTTPS de Gateway | El controlador de Gateway hace referencia a un Secret TLS del mismo espacio de nombres |
| Certificado público exportable de ACM | La clave y el certificado se exportan explícitamente para utilizarlos en cargas de trabajo gestionadas por el cliente |

ALB no utiliza directamente un Secret de Kubernetes de cert-manager como certificado de su listener. La importación o exportación y la asociación con un ARN de ACM son pasos independientes. El [ejemplo de ALB](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/alb-acm-ingress.yaml) requiere un ARN de ACM real y un Service backend. El [ejemplo de NLB TCP](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/nlb-tcp-service.yaml) transmite TLS al puerto 8443 del backend, que debe atender conexiones TLS.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: app-gateway
  namespace: demo-app
  annotations:
    cert-manager.io/cluster-issuer: lab-ca
spec:
  gatewayClassName: envoy-gateway
  listeners:
    - name: https
      hostname: app.example.com
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - group: ""
            kind: Secret
            name: app-gateway-tls
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app
  namespace: demo-app
spec:
  parentRefs:
    - name: app-gateway
  hostnames: [app.example.com]
  rules:
    - backendRefs:
        - name: app
          port: 8080
```

Este Gateway utiliza lab-ca, en la que los navegadores habituales no confían. Para una emisión pública real se necesitan un Issuer aprobado, un proceso de validación de dominio y un controlador. Compruebe los nombres de GatewayClass y el ámbito y tipo de certificateRefs; evite que dos controladores gestionen el mismo Secret.

<span id="july-2026-update-acm-now-supports-the-acme-protocol"></span>
<span id="supported-certificate-types"></span>
<span id="applicable-scenarios"></span>
<span id="example-defining-a-certificate-via-ack"></span>
<span id="comparison-with-cert-manager"></span>

<span id="aws-native-alternative-acm--ack"></span>

## Alternativa nativa de AWS: ACM + ACK

### ACM RequestCertificate y exportación ACK

ACK ACM es un controlador de código abierto que también debe instalarse y operarse. El [ejemplo](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/ack-acm.yaml) de 1.8.1 configura expresamente options.export:ENABLED, exportTo y el Secret de salida. Definir solo una solicitud de emisión no crea un Secret TLS. En el CRD de 1.8.1, sin cambios en v1.10.0, validationMethod aparece únicamente en los campos de solo lectura domainValidations de status, no en spec. No copie ese campo en una solicitud a partir de ejemplos antiguos.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: exported-public-tls
  namespace: demo-app
type: kubernetes.io/tls
data:
  tls.crt: ""
  tls.key: ""
---
apiVersion: acm.services.k8s.aws/v1alpha1
kind: Certificate
metadata:
  name: exportable-public-tls
  namespace: demo-app
spec:
  domainName: app.example.com
  keyAlgorithm: RSA_2048
  options:
    export: ENABLED
  exportTo:
    namespace: demo-app
    name: exported-public-tls
    key: tls.crt
```

La validación del dominio es un proceso independiente. Route53 ACK puede gestionar el CNAME que proporciona ACM, pero instalar el controlador de ACM no valida automáticamente todos los proveedores DNS. Evalúe los precios de los certificados exportables, los límites de IAM, RBAC y espacios de nombres del controlador, y el acceso al Secret de la clave privada. La identidad mTLS mediante Private CA o SPIFFE requiere su propio diseño de emisor y confianza.

### ACM ACME: EAB y dominios prevalidados

ACM ACME, anunciado el 6 de julio de 2026, emite certificados públicos de 45 días. Un administrador de PKI prepara un endpoint, la validación de dominio y las credenciales EAB asociadas a un rol de IAM; después registra a los clientes. **Cambiar únicamente la URL del servidor no basta.** Almacene la clave HMAC de forma segura y proporcione la entrada hmac del Secret acm-eab en el espacio de nombres de recursos de clúster de cert-manager.

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: acm-acme
spec:
  acme:
    server: https://acm-acme-enroll.ap-northeast-2.api.aws/REPLACE_ENDPOINT_ID/directory
    email: pki-admin@example.com
    privateKeySecretRef:
      name: acm-acme-account
    externalAccountBinding:
      keyID: REPLACE_EAB_KEY_ID
      keySecretRef:
        name: acm-eab
        key: hmac
```

El valor del Secret al que hace referencia externalAccountBinding debe contener la clave HMAC codificada en base64url. La codificación de los datos de un Secret de Kubernetes es una capa distinta. Conserve el valor ya codificado por el proveedor en lugar de codificarlo dos veces. Consulte la [configuración de ACME EAB](https://cert-manager.io/docs/configuration/acme/).

El ID del endpoint y el keyID de EAB son marcadores de posición. Los dominios deben estar prevalidados en el endpoint. El cliente ACME genera y conserva la clave privada, y gestiona la renovación. Que un ARN aparezca en el inventario de ACM no permite utilizar directamente ese certificado con las integraciones gestionadas de ALB, CloudFront o API Gateway. ExportCertificate, RenewCertificate y RevokeCertificate no se aplican a esta vía de emisión: el cliente ACME gestiona el ciclo de vida. Distinga este flujo de RequestCertificate para los servicios integrados con AWS.

<span id="istio-with-istio-csr"></span>
<span id="installing-istio-csr"></span>
<span id="configuring-istio-to-use-istio-csr"></span>
<span id="linkerd-trust-anchor-management"></span>

## Integración con mallas de servicios

![istio-agent, istio-csr, SDS y mTLS entre pares](../.gitbook/assets/en-security-10-cert-manager-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-3.html)

### Istio e istio-csr

En el flujo con sidecar, istio-agent crea la CSR e istio-csr envía una CertificateRequest. El agente entrega la clave y el certificado a Envoy mediante SDS; los proxies de las cargas de trabajo establecen mTLS. El salto hasta la aplicación dentro del mismo Pod no queda protegido automáticamente con mTLS.

Los [valores de istio-csr](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/istio-csr-values.yaml) configuran un volumen de ConfigMap y su montaje para rootCAFile. Cree el paquete application-trust en cert-manager y espere a que el Issuer esté preparado antes de continuar. Definir solo una ruta de archivo o un PEM vacío en meshConfig no basta. Utilice la configuración actual de CA externa de Helm o istioctl de Istio; no mezcle el flujo istio-csr con el modo RA de CSR de Kubernetes. Evalúe por separado la compatibilidad con Ambient.

```bash
helm upgrade --install cert-manager-istio-csr jetstack/cert-manager-istio-csr \
  --version v0.18.0 --namespace cert-manager --values istio-csr-values.yaml
```

### Linkerd y trust-manager {#linkerd-and-trust-manager}

El [ejemplo de identidad de Linkerd](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/linkerd-identity.yaml) prepara el Secret del emisor y el ConfigMap del paquete de raíces. El chart del plano de control, fijado a la versión 2026.9.1, hace referencia a linkerd-identity-issuer y linkerd-identity-trust-roots.

```yaml
identity:
  externalCA: true
  issuer:
    scheme: kubernetes.io/tls
```

Esta configuración conecta el plano de control a un Secret del emisor que se renueva externamente, en lugar de copiar una clave una sola vez durante la instalación. Sustituir la raíz requiere mantener las raíces anterior y nueva durante la transición, renovar las credenciales de las cargas de trabajo y recargar la confianza. La raíz de laboratorio del ejemplo se gestiona manualmente y tiene la renovación automática deshabilitada.

<span id="installing-trust-manager"></span>
<span id="bundle-resource"></span>
<span id="using-trust-bundles-in-applications"></span>

## trust-manager

El chart predeterminado de trust-manager 0.25.0 renderiza un Bundle de trust.cert-manager.io/v1alpha1. La presencia de otro CRD en el repositorio no cambia, por sí sola, la API instalada de forma predeterminada. Los Secrets y ConfigMaps de origen se leen del espacio de nombres de confianza configurado.

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: application-trust
spec:
  sources:
    - secret:
        name: lab-root
        key: tls.crt
  target:
    configMap:
      key: ca-bundle.pem
    namespaceSelector:
      matchLabels:
        trust-bundle: enabled
```

El campo para PEM en línea se llama inLine, no inlineString. Reduzca al mínimo las raíces de confianza públicas y privadas, y seleccione expresamente los espacios de nombres de destino. Los destinos de tipo Secret requieren habilitación y RBAC independientes; el ejemplo utiliza ConfigMaps. Un paquete de confianza distribuye anclas de confianza, no claves privadas.

El [Deployment consumidor](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/trust-consumer.yaml) monta un directorio. Los cambios de ConfigMap no se propagan mediante un archivo montado con subPath. Incluso al proyectar un directorio, el proceso no recarga automáticamente el contexto TLS que tiene en caché. Compruebe si la aplicación utiliza realmente SSL_CERT_FILE o el almacén de confianza que tiene configurado.

<span id="prometheus-metrics"></span>
<span id="key-metrics"></span>
<span id="prometheusrule-for-alerting"></span>
<span id="certificate-readiness-check"></span>
<span id="common-errors-and-solutions"></span>
<span id="cmctl-cli-tool"></span>

## Monitorización y solución de problemas

Inspeccione los selectores y los valores de port y targetPort del ServiceMonitor en el chart instalado. El perfil de 1.21.2 utiliza http-metrics para el controlador, cainjector y el webhook. No invente un nombre de puerto tcp-prometheus-servicemonitor.

```yaml
groups:
  - name: cert-manager
    rules:
      - alert: CertificateNotReady
        expr: certmanager_certificate_ready_status{condition="True"} == 0
        for: 10m
        labels:
          severity: critical
      - alert: CertificateExpiringSoon
        expr: (certmanager_certificate_expiration_timestamp_seconds - time() < 604800) and (certmanager_certificate_expiration_timestamp_seconds - time() > 86400)
        for: 30m
        labels:
          severity: warning
      - alert: CertificateExpiryCritical
        expr: (certmanager_certificate_expiration_timestamp_seconds - time() <= 86400) and (certmanager_certificate_expiration_timestamp_seconds - time() > 0)
        for: 10m
        labels:
          severity: critical
      - alert: CertificateExpired
        expr: (certmanager_certificate_expiration_timestamp_seconds > 0) and (certmanager_certificate_expiration_timestamp_seconds <= time())
        for: 5m
        labels:
          severity: critical
```

Las métricas de disponibilidad incluyen series True, False y Unknown; una comparación ==0 sin filtrar puede activar una alerta para certificados válidos y preparados. Estas reglas superaron cinco casos con veinte aserciones que cubren certificados en buen estado, NotReady, caducidad con nivel de advertencia, caducidad crítica y certificados caducados. La ausencia de recopilación o de métricas requiere alertas independientes.

```bash
kubectl get certificates,certificaterequests -A
kubectl get orders,challenges -A
kubectl describe certificate app-tls -n demo-app
cmctl status certificate app-tls -n demo-app
# These change resources; check permissions and impact first.
cmctl renew app-tls -n demo-app
```

Seleccionar resolvedores DNS recursivos no aumenta el tiempo de espera para la propagación. Inspeccione el DNS de horizonte dividido, CAA, la autorización de registros TXT, los CNAME, las rutas HTTP y los motivos de Challenge. Investigue la conectividad, autenticación y rutas del webhook antes de ajustar timeoutSeconds del chart, cuyo intervalo es de 1 a 30 segundos. No existe una opción genérica webhook-timeout que deba aplicarse a ciegas.

<span id="renewal-buffer-configuration"></span>
<span id="backup-ca-strategy"></span>
<span id="multi-tenant-issuer-strategy"></span>
<span id="rbac-configuration"></span>
<span id="private-key-rotation"></span>

## Prácticas recomendadas

- El [Role del espacio de nombres](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/certificate-requester-rbac.yaml) permite gestionar Certificates sin conceder a los desarrolladores acceso de lectura a Secrets de todo el clúster. Las restricciones de SAN, issuerRef y secretName requieren políticas independientes de admisión o aprobación.
- Separe la aprobación de CertificateRequest del acceso a las credenciales de la CA. Compruebe el comportamiento predeterminado del controlador de aprobación y configure una política de emisión, como approver-policy, cuando sea necesario.
- Las copias de seguridad de las claves de CA requieren cifrado, control de acceso y pruebas de restauración. No guarde YAML de Secrets sin cifrar en directorios comunes. Base64 no es cifrado.
- Una CA privada no sustituye automáticamente a una pública: valide la confianza del cliente, los nombres, los usos, el acceso a las claves y el tiempo de recuperación.
- Las anotaciones y etiquetas de secretTemplate son metadatos; no activan por sí solas la sincronización con sistemas externos de secretos.
- Pruebe por separado la renovación, la sustitución de CA, la recarga del consumidor y la revocación. Una validación correcta del esquema o de Helm no demuestra que la emisión funcione.

<span id="table-of-contents"></span>
<span id="key-concepts-summary"></span>
<span id="issuer-selection-guide"></span>
<span id="official-references"></span>
<span id="version-compatibility-matrix"></span>

## Resumen y referencias

Las comprobaciones locales incluyen esquemas de Helm y CRD con versiones fijadas, la decodificación de la configuración del controlador, seis casos de renovación, la generación de CSR reales y la comprobación de sus firmas, cinco casos de Prometheus con veinte aserciones, veinticuatro casos de diagramas en el navegador y dieciséis casos sintéticos de emisión de certificados y firma de CSR en una instancia local efímera de Vault. No se realizaron emisiones externas mediante CA o ACME, creación de recursos de AWS, inicio de sesión en un Vault desplegado, instalación de la malla ni comprobaciones de mTLS en ejecución.

- [versiones de cert-manager](https://cert-manager.io/docs/releases/)
- [versión 1.21.2 de cert-manager](https://github.com/cert-manager/cert-manager/releases/tag/v1.21.2)
- [historia del proyecto CNCF](https://www.cncf.io/projects/cert-manager/)
- [Renovación y rotación de certificados](https://cert-manager.io/docs/usage/certificate/)
- [Limitaciones de Issuer CA](https://cert-manager.io/docs/configuration/ca/)
- [Issuer Vault](https://cert-manager.io/docs/configuration/vault/)
- [Integración de Issuer de Gateway API](https://cert-manager.io/docs/usage/gateway/)
- [trust-manager](https://cert-manager.io/docs/trust/trust-manager/)
- [istio-csr](https://cert-manager.io/docs/usage/istio-csr/)
- [Rotación automática de certificados de Linkerd](https://linkerd.io/2-edge/tasks/automatically-rotating-control-plane-tls-credentials/)
- [Exportación de ACM Kubernetes](https://docs.aws.amazon.com/acm/latest/userguide/exportable-certificates-kubernetes.html)
- [ACM ACME](https://docs.aws.amazon.com/acm/latest/userguide/acm-acme.html)
- [Lanzamiento de ACM ACME](https://aws.amazon.com/about-aws/whats-new/2026/07/aws-certificate-manager-acme/)
- [Issuer AWS Private CA](https://github.com/cert-manager/aws-privateca-issuer/tree/v1.9.2)
- [Límites de tasa de Let’s Encrypt](https://letsencrypt.org/docs/rate-limits/)
- [Entorno de staging](https://letsencrypt.org/docs/staging-environment/)
- [Correos de expiración retirados](https://letsencrypt.org/2025/01/22/ending-expiration-emails/)
- [Retiro de Ingress NGINX](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
