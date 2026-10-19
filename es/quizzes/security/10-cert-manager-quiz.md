# Cuestionario de cert-manager

> **Última actualización**: 13 de septiembre de 2026

Diez preguntas sobre emisión, renovación, distribución de confianza y límites de integración con AWS.

## Preguntas

### 1. ¿Cuál es el estado del proyecto cert-manager en la CNCF?

- A) Sandbox
- B) Incubating
- C) Graduated
- D) Archivado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Graduated**

cert-manager se graduó el 29 de septiembre de 2024. Su fecha de entrada en Incubating fue el 19 de septiembre de 2022. La madurez del proyecto no demuestra la seguridad ni la disponibilidad de una instalación concreta.

</details>

<span id="_2-which-component-in-cert-manager-watches-certificate-resources-and-triggers-certificate-issuance"></span>

### 2. ¿Qué componente observa los recursos Certificate y reconcilia la emisión y la renovación?

- A) cainjector
- B) webhook
- C) controller
- D) scheduler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) controller**

El controller reconcilia el ciclo de vida de los certificados. El webhook valida, asigna valores predeterminados y convierte recursos personalizados; cainjector inyecta paquetes de CA en las configuraciones de API y webhook admitidas.

</details>

<span id="_3-what-is-the-key-difference-between-issuer-and-clusterissuer-resources"></span>

### 3. ¿Cuál es la diferencia principal entre los recursos Issuer y ClusterIssuer?

- A) Solo Issuer admite ACME
- B) Issuer tiene alcance de namespace; ClusterIssuer tiene alcance de clúster
- C) Solo ClusterIssuer renueva automáticamente
- D) Crear un ClusterIssuer impone automáticamente una política de SAN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Issuer tiene alcance de namespace; ClusterIssuer tiene alcance de clúster**

Issuer se referencia dentro de su namespace. Los Secrets de credenciales y de CA de ClusterIssuer se guardan en el namespace de recursos de clúster del controlador, normalmente `cert-manager`. El alcance del recurso, por sí solo, no autoriza los SAN ni `issuerRef`; se necesita una política de aprobación/admisión independiente.

</details>

<span id="_4-which-acme-challenge-type-supports-wildcard-certificate-issuance"></span>

### 4. ¿Qué método de validación admite la emisión normal de certificados wildcard con ACME de Let’s Encrypt?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) Solo comprobar la conectividad del puerto 443

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) DNS-01**

DNS-01 demuestra el control del dominio mediante registros TXT. HTTP-01 requiere el puerto 80 y no admite wildcard. Limita los permisos de la API DNS a la zona y los nombres TXT previstos. Las autorizaciones reutilizadas o la prevalidación de ACM pueden evitar que se cree un desafío nuevo en cada solicitud.

</details>

<span id="_5-in-a-certificate-resource-what-does-the-secretname-field-specify"></span>

### 5. ¿Qué especifica el campo `Certificate.spec.secretName`?

- A) El Secret de la clave de cuenta ACME
- B) El Secret de salida con el certificado y la clave privada, en el mismo namespace
- C) El ConfigMap que siempre distribuye la CA raíz
- D) El Secret de autenticación de Issuer

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El Secret de salida con el certificado y la clave privada, en el mismo namespace**

El Secret de salida contiene `tls.crt` y `tls.key`. `ca.crt` puede no estar presente y no sustituye la distribución de confianza a los clientes. `privateKey.rotationPolicy` tiene `Always` como valor predeterminado desde la versión 1.18. Hay que verificar por separado que la aplicación se recargue después de actualizar el Secret.

</details>

<span id="_6-what-is-the-primary-use-case-for-the-aws-private-ca-issuer"></span>

### 6. ¿Qué extensión integra AWS Private CA como issuer externo de cert-manager?

- A) aws-pca-controller
- B) aws-privateca-issuer
- C) acmesolver
- D) trust-manager

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) aws-privateca-issuer**

`aws-privateca-issuer` gestiona `AWSPCAIssuer` y `AWSPCAClusterIssuer`. Necesita permisos de IAM limitados a la CA, identidad de workload, aprobación de solicitudes y un modo de CA, plantillas y períodos de validez compatibles. Que una CA sea privada no implica confianza de los navegadores públicos ni emisión gratuita.

</details>

<span id="_7-what-does-trust-manager-do-in-the-cert-manager-ecosystem"></span>

### 7. ¿Cuál es la función principal de trust-manager?

- A) Emitir certificados y claves privadas
- B) Distribuir paquetes de CA a los namespaces seleccionados
- C) Copiar claves privadas de CA en todos los pods
- D) Revocar certificados automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Distribuir paquetes de CA a los namespaces seleccionados**

El chart predeterminado de la versión 0.25.0 usa Bundle v1alpha1. Las fuentes se leen del namespace de confianza configurado y `namespaceSelector` limita los destinos. Se admiten destinos ConfigMap; los destinos Secret requieren habilitarse por separado y contar con RBAC. Un montaje con `subPath` no recibe actualizaciones, y la proyección de un directorio no garantiza que el proceso se recargue.

</details>

<span id="_8-what-does-the-renewbefore-field-control-in-a-certificate-resource"></span>

### 8. Una solicitud pide 90 días, pero el certificado emitido dura 45. Sin ajustes de renovación explícitos ni ARI, ¿cuándo se programa la renovación predeterminada?

- A) Aproximadamente cuando haya transcurrido un tercio de la vigencia real
- B) El día 60, según los 90 días solicitados
- C) Siempre 30 días antes del vencimiento
- D) Siempre 75 días después de la emisión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Aproximadamente cuando haya transcurrido un tercio de la vigencia real**

El valor predeterminado es dos tercios de la vigencia X.509 real. Para un certificado de 45 días, eso ocurre aproximadamente el día 30. El día 75 solo corresponde a un certificado que efectivamente dura 90 días y tiene `renewBefore: 360h`. No configures a la vez `renewBefore` y `renewBeforePercentage`. Las políticas o ventanas de renovación de la versión 1.21, o las rutas ARI admitidas, pueden cambiar el calendario; comprueba `status.renewalTime`.

</details>

<span id="_9-what-is-the-role-of-istio-csr-in-cert-manager-s-istio-integration"></span>

### 9. ¿Qué afirmación describe correctamente la ruta de emisión para el sidecar de Istio?

- A) Envoy firma con la clave privada de la CA
- B) istio-agent → istio-csr → CertificateRequest/Issuer; SDS entrega el material a Envoy
- C) Todas las conexiones dentro del mismo pod usan mTLS automáticamente
- D) Una ruta `rootCAFile` elimina la necesidad de montar un archivo de CA real

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) istio-agent → istio-csr → CertificateRequest/Issuer; SDS entrega el material a Envoy**

`istio-agent` crea el CSR e `istio-csr` lo conecta con la emisión de cert-manager. El mTLS de peer-proxy es distinto del salto local a la aplicación. Configura un montaje real de la raíz de confianza, un issuer listo y los ajustes de CA externa de Istio; no mezcles esta ruta con el modo RA de Kubernetes CSR, que es independiente.

</details>

<span id="_10-what-is-a-key-difference-between-cert-manager-and-aws-certificate-manager-acm"></span>

### 10. ¿Qué afirmación sobre el comportamiento actual de ACM y cert-manager es correcta?

- A) Los certificados de ACM nunca se pueden usar en pods ni en instalaciones locales
- B) ALB lee directamente los Secrets TLS de Kubernetes
- C) Los certificados exportables de ACM admiten una exportación explícita; ACM ACME tiene un ciclo de vida y limitaciones propios
- D) Cambiar solo la URL del servidor completa la inscripción en ACM ACME

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Los certificados exportables de ACM admiten una exportación explícita; ACM ACME tiene un ciclo de vida y limitaciones propios**

La exportación de ACM mediante ACK requiere `options.export:ENABLED`, `exportTo`, un Secret de salida y una validación de dominio independiente. ACM ACME requiere dominios prevalidados/EAB y que el cliente administre las claves y la renovación; sus certificados de 45 días no se pueden adjuntar directamente a integraciones administradas de ALB, CloudFront o API Gateway. cert-manager reconcilia Secrets de Kubernetes y varios issuers; los operadores siguen siendo responsables de los controladores, la confianza y los costos de las CA.

</details>

## Cálculo de puntuación

- 9–10: comprensión sólida.
- 7–8: repasa las rutas de emisión y confianza que te faltaron.
- 6 o menos: repasa la guía y los ejemplos.

## Documentación relacionada

- [Gestión de certificados con cert-manager](../../security/10-cert-manager.md)
