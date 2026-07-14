# Cuestionario de seguridad de ArgoCD

Este cuestionario evalúa tu comprensión de las características de seguridad y las mejores prácticas de ArgoCD.

1. ¿Cómo maneja ArgoCD los secrets en los repositorios de Git de forma predeterminada?
   - A) Los cifra automáticamente
   - B) No maneja los secrets de manera especial: se almacenan como texto sin formato
   - C) Usa la API de Kubernetes Secrets
   - D) Requiere un administrador de secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No maneja los secrets de manera especial: se almacenan como texto sin formato**

**Explicación:**
ArgoCD no proporciona por sí mismo cifrado de secrets. Los secrets en Git deben cifrarse mediante herramientas como Sealed Secrets, SOPS, External Secrets Operator o Vault antes de confirmarlos en Git.

</details>

2. ¿Qué herramienta cifra Kubernetes Secrets mediante una clave específica del cluster?
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sealed Secrets**

**Explicación:**
Sealed Secrets utiliza un par de claves específico del cluster para cifrar secrets. El SealedSecret cifrado puede almacenarse de forma segura en Git y el controller de Sealed Secrets lo descifra en el cluster.

</details>

3. ¿Cuál es el propósito del componente Dex de ArgoCD?
   - A) Escaneo de imágenes de contenedor
   - B) Autenticación OpenID Connect y SSO
   - C) Aplicación de políticas de red
   - D) Rotación de secrets

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Autenticación OpenID Connect y SSO**

**Explicación:**
Dex es un servicio de identidad que proporciona autenticación OpenID Connect (OIDC). Permite que ArgoCD se integre con diversos proveedores de identidad (LDAP, SAML, GitHub, etc.) para el inicio de sesión único.

</details>

4. ¿Cómo puedes restringir qué recursos de Kubernetes puede crear una Application?
   - A) Mediante Kubernetes ResourceQuotas
   - B) Mediante namespaceResourceBlacklist o namespaceResourceWhitelist de AppProject
   - C) Mediante Pod Security Policies
   - D) No es posible en ArgoCD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante namespaceResourceBlacklist o namespaceResourceWhitelist de AppProject**

**Explicación:**
Los AppProjects pueden definir `namespaceResourceBlacklist` (denegar recursos específicos) o `namespaceResourceWhitelist` (permitir solo recursos específicos) para controlar qué tipos de recursos de Kubernetes pueden administrar las Applications.

</details>

5. ¿Cuál es la práctica recomendada para exponer el API server de ArgoCD?
   - A) Exponerlo públicamente con autenticación básica
   - B) Mantenerlo interno y usar un ingress con TLS y autenticación
   - C) Ejecutarlo sin ninguna autenticación
   - D) Acceder a él únicamente mediante port-forwarding

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mantenerlo interno y usar un ingress con TLS y autenticación**

**Explicación:**
El API server de ArgoCD debe exponerse mediante un ingress con terminación TLS y una autenticación adecuada (SSO/OIDC). Para entornos sensibles, se recomiendan medidas adicionales como el acceso por VPN o la inclusión de IP en listas de permitidos.

</details>
