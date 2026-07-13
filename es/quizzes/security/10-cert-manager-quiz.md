# Cuestionario de cert-manager

Pon a prueba tu comprensión de cert-manager y la gestión de certificados en Kubernetes con las siguientes preguntas.

---

## Preguntas

### 1. ¿Cuál es el estado del proyecto cert-manager en la CNCF?

- A) Proyecto Sandbox
- B) Proyecto Incubating
- C) Proyecto Graduated
- D) Proyecto archivado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Proyecto Graduated**

**Explicación:**
cert-manager alcanzó el estado CNCF Graduated en noviembre de 2022, lo que lo convierte en una de las soluciones de gestión de certificados para Kubernetes más maduras y ampliamente adoptadas. Este estado indica que el proyecto ha cumplido requisitos rigurosos de gobernanza, seguridad y adopción por parte de la comunidad.

</details>

---

### 2. ¿Qué componente de cert-manager observa los recursos Certificate y desencadena la emisión de certificados?

- A) cainjector
- B) webhook
- C) controller
- D) acmesolver

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) controller**

**Explicación:**
cert-manager consta de tres componentes principales:
- **controller**: Observa los recursos Certificate, gestiona el ciclo de vida del certificado y desencadena la emisión/renovación
- **webhook**: Valida y modifica los recursos de cert-manager mediante admission webhooks
- **cainjector**: Inyecta CA bundles en ValidatingWebhookConfiguration, MutatingWebhookConfiguration y webhooks de conversión de CRD

</details>

---

### 3. ¿Cuál es la diferencia clave entre los recursos Issuer y ClusterIssuer?

- A) Issuer admite más tipos de certificados
- B) ClusterIssuer está limitado a un namespace, mientras que Issuer tiene alcance de cluster
- C) Issuer está limitado a un namespace, mientras que ClusterIssuer tiene alcance de cluster
- D) ClusterIssuer solo funciona con ACME

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Issuer está limitado a un namespace, mientras que ClusterIssuer tiene alcance de cluster**

**Explicación:**
```yaml
# Issuer - only issues certificates in its namespace
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-prod
  namespace: my-app  # Only works in this namespace

# ClusterIssuer - issues certificates across all namespaces
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod  # No namespace - cluster-wide
```

Usa ClusterIssuer para políticas de certificados de toda la organización e Issuer para configuraciones específicas de namespace.

</details>

---

### 4. ¿Qué tipo de desafío ACME admite la emisión de certificados wildcard?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) Tanto HTTP-01 como DNS-01

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) DNS-01**

**Explicación:**
Tipos de desafíos ACME y sus capacidades:
- **HTTP-01**: Demuestra el control del dominio mediante un endpoint HTTP (puerto 80). NO admite wildcards.
- **DNS-01**: Demuestra el control del dominio mediante registros DNS TXT. Admite certificados wildcard (*.example.com).
- **TLS-ALPN-01**: Demuestra el control del dominio mediante TLS (puerto 443). NO admite wildcards.

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
spec:
  acme:
    solvers:
    - dns01:
        route53:
          region: us-east-1
      selector:
        dnsNames:
        - "*.example.com"  # Wildcard requires DNS-01
```

</details>

---

### 5. En un recurso Certificate, ¿qué especifica el campo secretName?

- A) El nombre del Secret del Issuer
- B) El Kubernetes Secret donde se almacenará el certificado emitido
- C) El Secret del certificado de CA
- D) El Secret de la cuenta ACME

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El Kubernetes Secret donde se almacenará el certificado emitido**

**Explicación:**
El campo secretName especifica dónde almacena cert-manager el certificado emitido:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-app-tls
  namespace: my-app
spec:
  secretName: my-app-tls-cert  # Certificate stored here
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - my-app.example.com
```

El Secret resultante contiene:
- `tls.crt`: La cadena de certificados
- `tls.key`: La clave privada
- `ca.crt`: El certificado de CA (si está disponible)

</details>

---

### 6. ¿Cuál es el caso de uso principal de AWS Private CA Issuer?

- A) Certificados públicos gratuitos
- B) PKI interna para certificados privados/empresariales
- C) Automatización de desafíos DNS-01
- D) Revocación de certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) PKI interna para certificados privados/empresariales**

**Explicación:**
AWS Private CA (PCA) Issuer integra cert-manager con AWS Certificate Manager Private Certificate Authority:

```yaml
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAClusterIssuer
metadata:
  name: aws-pca-issuer
spec:
  arn: arn:aws:acm-pca:us-east-1:123456789:certificate-authority/abc-123
  region: us-east-1
```

Casos de uso:
- mTLS interno de microservicios
- Requisitos de cumplimiento de PKI empresarial
- Certificados privados no expuestos a Internet público
- Integración con la infraestructura AWS PCA existente

</details>

---

### 7. ¿Qué hace trust-manager en el ecosistema de cert-manager?

- A) Valida firmas de certificados
- B) Distribuye CA bundles entre namespaces como ConfigMaps o Secrets
- C) Gestiona el registro de cuentas ACME
- D) Gestiona la revocación de certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Distribuye CA bundles entre namespaces como ConfigMaps o Secrets**

**Explicación:**
trust-manager es un subproyecto de cert-manager que distribuye certificados de CA de confianza:

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: my-ca-bundle
spec:
  sources:
  - useDefaultCAs: true           # Include system CAs
  - secret:
      name: "internal-ca"
      key: "ca.crt"
  target:
    configMap:
      key: "ca-certificates.crt"
    namespaceSelector:
      matchLabels:
        trust-bundle: enabled     # Distribute to labeled namespaces
```

Esto garantiza una confianza de CA coherente en todos los namespaces de aplicaciones.

</details>

---

### 8. ¿Qué controla el campo renewBefore en un recurso Certificate?

- A) El período mínimo de validez
- B) Con cuánta antelación antes del vencimiento cert-manager inicia la renovación
- C) El número máximo de intentos de renovación
- D) El intervalo de comprobación de renovación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Con cuánta antelación antes del vencimiento cert-manager inicia la renovación**

**Explicación:**
El campo renewBefore especifica cuándo cert-manager inicia el proceso de renovación:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
spec:
  secretName: my-cert
  duration: 2160h    # 90 days validity
  renewBefore: 360h  # Renew 15 days before expiry
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - example.com
```

Con esta configuración:
- Certificado válido durante 90 días
- La renovación comienza el día 75 (90 - 15 = 75)
- Proporciona un margen ante fallos de renovación

</details>

---

### 9. ¿Cuál es el rol de istio-csr en la integración de cert-manager con Istio?

- A) Valida configuraciones de Istio
- B) Emite certificados de workload para Istio service mesh usando cert-manager
- C) Gestiona únicamente certificados de Istio gateway
- D) Sincroniza certificados entre clusters

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Emite certificados de workload para Istio service mesh usando cert-manager**

**Explicación:**
istio-csr reemplaza la CA integrada de Istio (istiod) por cert-manager para la identidad de workloads:

```yaml
# istio-csr issues certificates for:
# - Workload mTLS (pod-to-pod)
# - Service mesh identity (SPIFFE)

# Configuration example
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: istiod
  namespace: istio-system
spec:
  secretName: istiod-tls
  issuerRef:
    name: istio-ca
    kind: ClusterIssuer
  isCA: true
```

Beneficios:
- Gestión centralizada de PKI
- Políticas de certificados coherentes en mesh e ingress
- Integración con CA externas (Vault, AWS PCA)

</details>

---

### 10. ¿Cuál es una diferencia clave entre cert-manager y AWS Certificate Manager (ACM)?

- A) ACM admite más issuers
- B) cert-manager solo puede ejecutarse en EKS
- C) cert-manager proporciona certificados como Kubernetes Secrets; ACM los almacena en AWS
- D) ACM admite más tipos de certificados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) cert-manager proporciona certificados como Kubernetes Secrets; ACM los almacena en AWS**

**Explicación:**
Comparación entre cert-manager y AWS ACM:

| Característica | cert-manager | AWS ACM |
|---------|--------------|---------|
| Almacenamiento | Kubernetes Secrets | Gestionado por AWS |
| Acceso a la clave privada | Sí (en Secret) | No (solo AWS) |
| Uso con Pods | Montaje directo | No es posible |
| Integración con Ingress | Cualquier ingress controller | Solo ALB/NLB |
| Multi-cloud | Sí | Solo AWS |
| Issuers | ACME, Vault, PCA, self-signed | Amazon, PCA |

Usa cert-manager cuando necesites:
- Certificados dentro de pods
- Portabilidad multi-cloud
- Issuers personalizados
- Control detallado sobre claves privadas

</details>

---

## Cálculo de puntuación

- **9-10 correctas**: Excelente: tienes un conocimiento profundo de cert-manager.
- **7-8 correctas**: Bien: tienes una comprensión sólida de los conceptos clave.
- **5-6 correctas**: Aceptable: hay áreas que necesitan estudio adicional.
- **4 o menos**: Revisa la documentación nuevamente.

## Documentación relacionada

- [Gestión de certificados con cert-manager](../../security/10-cert-manager.md)
