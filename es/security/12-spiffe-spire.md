# Identidad de carga de trabajo con SPIFFE/SPIRE

> **Última actualización**: September 13, 2026
> **Referencia de validación**: SPIRE 1.15.3, hardened chart 0.30.2 / CRD chart 0.6.1, Controller Manager 0.7.0, imagen CSI del chart 0.2.7 (también verificada frente a la documentación actual de CSI 0.2.13), go-spiffe 2.8.1. Inspeccione por separado las versiones de imágenes renderizadas por el chart.

SPIFFE define la identidad, las credenciales, la entrega y los formatos de confianza de las cargas de trabajo; SPIRE los implementa. **Emitir una identidad no cifra automáticamente el tráfico ni autoriza el acceso al Service.** Esta guía valida la configuración local, los esquemas, las bibliotecas, los charts y los diagramas. No se realizó ningún clúster en vivo, CA de AWS, atestación de SPIRE ni instalación de mesh.

## Descripción general

SPIFFE y SPIRE son proyectos Graduated de CNCF. Sus páginas de proyectos de CNCF registran el 23 y el 22 de agosto de 2022, respectivamente. La madurez del proyecto es independiente de la validación de un Deployment individual.

Las identidades estables son útiles frente a cambios de IPs/Pods, pero las aplicaciones aún necesitan un cliente, SDK, proxy o adaptador explícito de archivos para la Workload API. “Cero cambios en la aplicación para cada carga de trabajo” no es una garantía universal. Este capítulo se centra en las rutas X.509/JWT de SPIRE; no se asume que la **especificación WIT-SVID Incubating**, publicada por separado, sea compatible con todos los Deployments.

<span id="svid-spiffe-verifiable-identity-document"></span>
<span id="x-509-svid-vs-jwt-svid-comparison"></span>
<span id="trust-bundle"></span>
<span id="trust-domain"></span>

## Conceptos fundamentales

### ID de SPIFFE

```text
spiffe://example.org/ns/payments/sa/payment-processor
```

Un ID contiene un esquema, un dominio de confianza y una ruta opcional. Los componentes de consulta, fragmento, puerto, segmento de punto y ruta codificada en porcentaje están prohibidos. Los nombres estables de dominios de confianza similares a DNS son útiles, pero no tienen que poder resolverse mediante DNS. Los nombres con forma de IPv4 o numéricos no son categóricamente inválidos; distinga la sintaxis de las recomendaciones de nomenclatura.

### SVIDs y validación

| Aspecto | X.509-SVID | JWT-SVID |
|---|---|---|
| Identidad | URI SAN de SPIFFE en el certificado leaf | sub |
| Validación | Cadena, vigencia, reglas de SVID, dominio de confianza | Firma, sujeto, audiencia, vencimiento |
| Uso | Autenticación TLS de cliente/servidor | APIs que aceptan bearer tokens |
| Clave | Ruta de clave privada de la carga de trabajo/agente | El emisor conserva la clave privada de firma |
| Vigencia | Política y emisión real | Política y exp real del token |

CN no es la identidad de SPIFFE. Las pruebas locales de go-spiffe rechazaron solo CN, múltiples URIs de SPIFFE, vencimiento y dominios de confianza incorrectos. La validación de audiencia limita los destinatarios, pero no detecta replay: el mismo bearer token válido superó la verificación nuevamente. Aplique políticas apropiadas de uso de TLS/token y defensas contra replay donde sea necesario.

Los trust bundles incluyen autoridades X.509, claves de verificación JWT y metadatos. PEM, JSON de bundle de SPIFFE y YAML arbitrario no son intercambiables. Los bundles públicos no deben contener claves privadas de carga de trabajo ni de CA.

<span id="spire-server"></span>
<span id="spire-agent"></span>
<span id="svid-issuance-flow"></span>

## Arquitectura de SPIRE

![Responsabilidades de SPIRE Server, Agent, claves de firma y registro](../.gitbook/assets/en-security-12-spiffe-spire-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-0.html)


El Server administra la atestación de Agent, el registro y la firma X.509/JWT. DataStore y KeyManager tienen responsabilidades de persistencia distintas. Una UpstreamAuthority como AWS Private CA firma CAs intermedias de SPIRE; no reemplaza cada operación de firma leaf de la carga de trabajo.

El Agent atestigua el proceso que llama a su API y utiliza entradas sincronizadas/caché de SVID. Una caché válida no requiere una nueva emisión del Server en cada solicitud de API. Los consumidores deben adoptar las credenciales actualizadas mediante streams, SDKs o proxies.

![Caché local de X.509-SVID y ruta de renovación condicional](../.gitbook/assets/en-security-12-spiffe-spire-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-1.html)


<span id="prerequisites"></span>
<span id="helm-installation-recommended"></span>
<span id="namespace-layout"></span>
<span id="high-availability-configuration"></span>
<span id="verify-installation"></span>

## Instalación

Descargue el [directorio de ejemplo](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/spiffe) y trabaje desde `examples/security/spiffe`. Verifique los requisitos de hostPath/CSI/kernel/kubelet. No se puede asumir que los mismos DaemonSets se ejecuten en hosts como Fargate, donde el acceso requerido no está disponible.

```bash
helm repo add spiffe https://spiffe.github.io/helm-charts-hardened
helm repo update spiffe
helm upgrade --install spire-crds spiffe/spire-crds \
  --version 0.6.1 --namespace spire-system --create-namespace
helm upgrade --install spire spiffe/spire \
  --version 0.30.2 --namespace spire-system --values lab-values.yaml
```

### Laboratorio con un solo Server

```yaml
global:
  spire:
    trustDomain: example.org
    clusterName: documentation
    caSubject:
      organization: Documentation Lab
      country: KR
    namespaces:
      server:
        name: spire-system
      system:
        name: spire-system
  installAndUpgradeHooks:
    enabled: false
  deleteHooks:
    enabled: false
spire-server:
  replicaCount: 1
  controllerManager:
    enabled: true
    identities:
      clusterSPIFFEIDs:
        default:
          enabled: false
        oidc-discovery-provider:
          enabled: false
        test-keys:
          enabled: false
  externalControllerManagers:
    enabled: false
  persistence:
    enabled: true
    size: 1Gi
spire-agent:
  workloadAttestors:
    k8s:
      verification:
        type: apiServerCA
    unix:
      enabled: true
spiffe-oidc-discovery-provider:
  enabled: false
spiffe-csi-driver:
  enabled: true
```


Este es un laboratorio SQLite con un solo Server. Las identidades amplias predeterminadas, de prueba y OIDC no utilizadas están deshabilitadas; un ClusterSPIFFEID independiente selecciona las cargas de trabajo. El chart omite de forma predeterminada la verificación de kubelet, por lo que apiServerCA se establece explícitamente. Esto presupone que el certificado de servicio real de kubelet se valida con esa CA; utilice el método de CA/certificado de host adecuado para otras PKI en lugar de deshabilitar la verificación.

Los hooks de instalación/eliminación están deshabilitados en este perfil; realice por separado cualquier migración/limpieza necesaria. El render incluye un StatefulSet de Server con sidecar de Controller Manager, además de DaemonSets de Agent y CSI. Confirme los nombres de recursos, etiquetas y rutas de sockets específicos de la versión del release.

### Alta disponibilidad

[ha-values.yaml](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/spiffe/ha-values.yaml) utiliza tres réplicas, PostgreSQL compartido, un Secret de contraseña existente, TLS verify-full con una CA montada y anti-affinity que coincide con las etiquetas reales del Pod. Tres réplicas SQLite independientes no constituyen un datastore HA compartido.

Primero prepare PostgreSQL/DNS, el ConfigMap de CA, la clave `password` del Secret `spire-database`, StorageClass y la conectividad. El ejemplo suministra la contraseña sin procesar mediante `PGPASSWORD` usando `extraEnv.valueFrom.secretKeyRef`. Deshabilita la interpolación `dataStore.sql.externalSecret` del chart y deja `password` vacío, por lo que la cadena de conexión generada no contiene contraseña. El driver PostgreSQL de SPIRE lee `PGPASSWORD` por separado: las comillas, barras invertidas, espacios en blanco y signos de dólar no entran en el parser JSON/DSN. No aplique escape previo ni codificación URI a la contraseña real.

Las comprobaciones de configuración nativa de SPIRE 1.15.3 y del parser lib/pq 1.12.3 cubrieron seis casos sintéticos de contraseña mientras mantenían `sslmode=verify-full` y la ruta de CA. Estas comprobaciones no se conectaron a PostgreSQL ni probaron failover. Los cambios de Secret entregados como variables de entorno requieren reiniciar los Pods de Server; coordine la rotación de contraseña de la base de datos con el reinicio y verifique la disponibilidad. HA también requiere persistencia de claves, copias de seguridad, rollover de bundles y pruebas de recuperación.

<span id="attestation-flow"></span>
<span id="kubernetes-psat-projected-service-account-token"></span>
<span id="aws-instance-identity-document-iid"></span>
<span id="join-token-bootstrap"></span>
<span id="node-attestor-comparison"></span>

## Atestación de nodos

![Atestación independiente de Agent y carga de trabajo](../.gitbook/assets/en-security-12-spiffe-spire-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-2.html)


k8s_psat valida el token proyectado de ServiceAccount del Agent mediante **Kubernetes TokenReview**, y luego comprueba datos de namespace/SA/Pod/nodo. Esto no es el flujo de proveedor OIDC de IAM utilizado por IRSA. Haga coincidir los nombres lógicos de clúster, la audiencia del token, la allowlist de SA y los permisos de TokenReview.

Los IDs de Agent predeterminados siguen `spiffe://TRUST_DOMAIN/spire/agent/k8s_psat/CLUSTER/NODE_UID`; la versión actual también ofrece un modo de UID de Pod. Descubra los IDs de Agent/alias registrados en lugar de inventar parentIDs. token generate, entry create y bundle set modifican el estado real.

aws_iid es una alternativa que utiliza la identidad de instancia EC2. No es universalmente más fuerte que PSAT ni está restringida a entornos no EKS. Revise las suposiciones de skip_block_device, validación local, cuentas permitidas y selectores adicionales. No coloque credenciales estáticas de AWS en ConfigMaps.

<span id="kubernetes-workload-attestor"></span>
<span id="registration-entry-examples"></span>
<span id="unix-workload-attestor"></span>

## Atestación de carga de trabajo

El Agent utiliza el PID/cgroups del llamador e información de kubelet. No establezca por defecto el puerto inseguro 10255 de kubelet ni skip_kubelet_verification=true. La autenticación segura, la CA de servicio correcta y el acceso de red son requisitos previos.

Los selectores comunes incluyen k8s:ns, k8s:sa, k8s:pod-label, k8s:pod-uid y k8s:container-name/image. container-image refleja tags/digests informados por Kubernetes; nginx:* no es un selector glob. Una cadena de tag no es verificación de la cadena de suministro. Utilice por separado la atestación adecuada de digest/firma donde sea necesario.

Las entidades principales que pueden cambiar las etiquetas de namespace/Pod o crear Pods con un ServiceAccount pueden afectar la elegibilidad de identidad. Controle conjuntamente la creación de namespace/SA/Pod y la propiedad de la política de identidad. Los selectores Unix UID/GID/path/hash también dependen de la configuración del plugin y del modelo de amenazas.

<span id="spiffe-csi-driver"></span>
<span id="spire-controller-manager"></span>
<span id="envoy-sds-integration"></span>

## Integración con Kubernetes

### CSI monta el socket de API

Las implementaciones de SPIFFE CSI 0.2.7 del chart y la actual 0.2.13 montan un **directorio que contiene el socket Unix de la Workload API**. No crean automáticamente archivos svid.pem, svid.key ni bundle.pem. Las aplicaciones basadas en archivos necesitan un adaptador independiente y manejo de renovación/recarga.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: payments
  labels:
    spiffe-enabled: 'true'
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: payment-processor
  namespace: payments
---
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: payments-workload
spec:
  spiffeIDTemplate: spiffe://{{ .TrustDomain }}/ns/{{ .PodMeta.Namespace }}/sa/{{
    .PodSpec.ServiceAccountName }}
  namespaceSelector:
    matchLabels:
      spiffe-enabled: 'true'
  podSelector:
    matchLabels:
      spiffe-managed: 'true'
  workloadSelectorTemplates:
  - k8s:ns:{{ .PodMeta.Namespace }}
  - k8s:sa:{{ .PodSpec.ServiceAccountName }}
  - k8s:container-name:app
  ttl: 1h
  jwtTtl: 5m
---
apiVersion: v1
kind: Pod
metadata:
  name: payment-processor
  namespace: payments
  labels:
    spiffe-managed: 'true'
spec:
  serviceAccountName: payment-processor
  containers:
  - name: app
    image: registry.example.com/team/payment-app:REPLACE_WITH_APPROVED_VERSION
    env:
    - name: SPIFFE_ENDPOINT_SOCKET
      value: unix:///spiffe-workload-api/spire-agent.sock
    volumeMounts:
    - name: spiffe-workload-api
      mountPath: /spiffe-workload-api
      readOnly: true
  volumes:
  - name: spiffe-workload-api
    csi:
      driver: csi.spiffe.io
      readOnly: true
```


Reemplace la imagen de la aplicación por un consumidor real de Workload API. Distinga jwtTTL de identidad del chart de jwtTtl de CRD. El selector explícito se dirige al contenedor app; un contenedor Envoy independiente necesita una política de registro de proxy coincidente.

### Envoy SDS

El [ejemplo completo de bootstrap](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/spiffe/envoy.yaml) incluye filtros HTTP, el clúster SDS, require_client_certificate:true y un matcher exacto de URI de peer permitido. El proceso Envoy debe poder ser atestado y deben registrarse ambas identidades de servidor/cliente con nombre.

SDS comparte el socket público de Agent con la Workload API. Los nombres de recursos de certificado usan un ID de SPIFFE de carga de trabajo o default; los contextos de validación usan un ID de dominio de confianza o ROOTCA/ALL. Compruebe la compatibilidad con el certificate-validator de SPIFFE, especialmente para ALL. Se verificaron los esquemas de protocolo y la implementación de URI-matcher; no se ejecutó ningún handshake real de Envoy/SDS/mTLS.

<span id="istio-spire-integration"></span>
<span id="cilium-spire-mutual-authentication"></span>
<span id="linkerd-identity-trust-anchors"></span>

## Integración con Service Mesh

### Istio

No apunte la dirección de CA de Istio al puerto 8081 de SPIRE Server ni use variables inventadas ENABLE_SPIFFE_IDENTITY/PILOT_ENABLE_SPIRE_INTEGRATION. La [integración oficial](https://istio.io/latest/docs/ops/integrations/spire/) actual configura montajes de socket CSI, registro de SPIRE y plantillas de sidecar/gateway.

Con sidecars nativos, istio-proxy es un initContainer y debe modificarse allí. El modo de sidecar nativo explícitamente deshabilitado utiliza containers en su lugar. Valide las versiones, plantillas, sockets y readiness instalados; no reemplace un ConfigMap completo de injector por un snippet parcial.

### Cilium

La autenticación mutua de Cilium 1.20.1 es **beta y fuera de banda de las conexiones ordinarias**. El cifrado del tráfico requiere una configuración independiente de WireGuard/IPsec. Una etiqueta arbitraria que contiene un ID de SPIFFE no es una política de identidad autenticada.

La configuración oficial utiliza authentication.mutual.spire.enabled y, para su instalación incluida, authentication.mutual.spire.install.enabled. Mantenga distintas las configuraciones de SPIRE incluida y externa, y consulte la [fuente de instalación fijada](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/installation.rst). Los selectores de endpoint/modos de autenticación, la emisión de identidad y el cifrado tienen responsabilidades independientes.

### Linkerd

No pase JSON de bundle de SPIRE donde Linkerd espera raíces PEM ni copie claves privadas de CA de SPIRE como claves de emisor. Linkerd necesita un certificado/clave de emisor adecuado y raíces de confianza, con renovación y rollover de raíz. Consulte la [ruta revisada de cert-manager/Linkerd](./10-cert-manager.md#linkerd-and-trust-manager). Compartir solamente la confianza de raíz no integra la Workload API ni SDS de SPIFFE.

<span id="federation-trust-establishment"></span>
<span id="configuring-federation"></span>
<span id="federated-registration-entries"></span>
<span id="multi-cloud-federation-example"></span>

## Federación

![Federación con confianza explícita de bundle y autorización de carga de trabajo](../.gitbook/assets/en-security-12-spiffe-spire-3.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-3.html)


Configure explícitamente cada dirección de confianza; la federación no establece automáticamente confianza mutua ni autorización. Opere la conectividad del endpoint de bundle, la verificación TLS, los fallos de actualización, el vencimiento y el rollover.

```yaml
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterFederatedTrustDomain
metadata:
  name: partner-domain
spec:
  trustDomain: partner.example.org
  bundleEndpointURL: https://bundle.partner.example.org
  bundleEndpointProfile:
    type: https_web
```


Este ejemplo https_web presupone un endpoint real con un certificado Web PKI válido. https_spiffe también necesita endpointSPIFFEID y un **bundle confiable inicial adquirido mediante una ruta de bootstrap autenticada**; establecer solo una URL no es suficiente. Utilice nombres de dominio de confianza sin prefijo, como partner.example.org, en las listas federatesWith de cargas de trabajo aplicables. Obtener un trust bundle y autorizar una carga de trabajo peer son acciones distintas.

<span id="irsa-vs-spiffe-comparison"></span>
<span id="pod-identity-vs-spire"></span>
<span id="hybrid-use-cases"></span>
<span id="eks-specific-node-attestation"></span>

## Integración con EKS

IRSA/Pod Identity proporcionan rutas de credenciales de API de AWS; SPIFFE/SPIRE proporcionan rutas de identidad de carga de trabajo. Ninguno reemplaza al otro, y no todos los entornos necesitan ambos. IRSA admite diseños entre cuentas y actualiza las credenciales mediante el comportamiento compatible de SDK/token proyectado; reiniciar el Pod no es inherentemente necesario. No suponga una vigencia fija de doce horas.

Configure IRSA en el ServiceAccount y valide la confianza aud/sub y los permisos de AWS. Una anotación de Pod o una variable de entorno AWS_ROLE_ARN por sí sola no es suficiente. Para mTLS de carga de trabajo, las aplicaciones/proxies deben consumir SVIDs y autorizar por separado las identidades peer.

### AWS Private CA

Utilice los [campos de plugin fijados](https://github.com/spiffe/spire/blob/v1.15.3/doc/plugin_server_upstreamauthority_aws_pca.md) dentro de una sección completa de plugins de Server. Esto es un fragmento de plugin, no una configuración de Server ejecutable de forma independiente.

```hcl
# Merge this plugin into an otherwise complete server configuration.
UpstreamAuthority "aws_pca" {
  plugin_data {
    region = "ap-northeast-2"
    certificate_authority_arn = "arn:aws:acm-pca:ap-northeast-2:111122223333:certificate-authority/REPLACE_CA_ID"
    ca_signing_template_arn = "arn:aws:acm-pca:::template/SubordinateCACertificate_PathLen0/V1"
  }
}
```


SPIRE posee la CA intermedia y firma certificados leaf. Limite DescribeCertificateAuthority/IssueCertificate/GetCertificate al ARN de CA previsto utilizando el [ejemplo de política](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/spiffe/aws-pca-policy.json). Seleccione algoritmos/plantillas de firma para la CA real. supplemental_bundle_path contiene autoridades PEM adicionales, no una región de respaldo. Distinga KeyManager aws_kms de los plugins UpstreamAuthority.

## Mejores prácticas y solución de problemas

Ajuste las vigencias frente a fallos de renovación, clock skew, carga de emisión y períodos offline. Los TTL cortos no resuelven todos los problemas de revocación o replay de JWT. Los cambios de bundle set modifican los bundles confiables; no rotan una clave privada de CA.

La política de red debe contemplar DNS, Kubernetes TokenReview/API, datastore, CA/KMS ascendente, federación y telemetría, además del tráfico Server↔Agent. Un selector de Pod en un namespace no selecciona Agents en otro. Valide la conectividad real antes de afirmar que la política permite todos los flujos necesarios.

Ejecutar api fetch dentro del Pod de Agent atestigua el proceso que realiza la llamada, no el contexto de la aplicación. Diagnostique desde el contexto de la carga de trabajo prevista mediante un procedimiento aprobado. Limite los selectores, tokens y claves sensibles en los logs.

<span id="table-of-contents"></span>
<span id="the-zero-trust-identity-problem"></span>
<span id="spiffe-specification-overview"></span>
<span id="cncf-graduation-status"></span>
<span id="best-practices"></span>
<span id="trust-domain-naming"></span>
<span id="svid-ttl-tuning"></span>
<span id="high-availability-deployment"></span>
<span id="key-rotation"></span>
<span id="security-hardening"></span>
<span id="troubleshooting"></span>
<span id="common-issues"></span>
<span id="health-checks"></span>
<span id="key-takeaways"></span>
<span id="architecture-decision-guide"></span>
<span id="references"></span>

## Resumen y referencias

La validación local cubrió la configuración de Server/Agent, nueve casos de ID, cinco casos X.509, seis casos JWT, Helm de laboratorio/HA, esquemas CRD/Pod, esquemas protobuf de Envoy y veinticuatro casos de navegador para ocho diagramas. No se ejecutaron atestación real, instalación de clúster, conexión a DB, emisión de AWS, intercambio de federación ni tráfico mTLS.

- [Especificación de ID de SPIFFE](https://spiffe.io/docs/latest/spiffe-specs/spiffe-id/)
- [X.509-SVID](https://spiffe.io/docs/latest/spiffe-specs/x509-svid/)
- [JWT-SVID](https://spiffe.io/docs/latest/spiffe-specs/jwt-svid/)
- [WIT-SVID Incubating](https://spiffe.io/docs/latest/spiffe-specs/wit-svid/)
- [Dominio de confianza y bundle](https://spiffe.io/docs/latest/spiffe-specs/spiffe_trust_domain_and_bundle/)
- [Especificación de federación](https://spiffe.io/docs/latest/spiffe-specs/spiffe_federation/)
- [Historial de SPIFFE en CNCF](https://www.cncf.io/projects/spiffe/)
- [Historial de SPIRE en CNCF](https://www.cncf.io/projects/spire/)
- [SPIRE 1.15.3](https://github.com/spiffe/spire/releases/tag/v1.15.3)
- [SPIFFE CSI 0.2.13](https://github.com/spiffe/spiffe-csi/blob/v0.2.13/README.md)
- [Charts Helm hardened](https://github.com/spiffe/helm-charts-hardened)
- [Autenticación mutua de Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
