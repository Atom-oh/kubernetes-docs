# Cuestionario de seguridad de ArgoCD

Este cuestionario evalúa tus conocimientos sobre las funciones de seguridad de ArgoCD y las prácticas recomendadas.

1. ¿Cómo gestiona ArgoCD de forma predeterminada los secretos en los repositorios Git?
   - A) Los cifra automáticamente
   - B) No cifra automáticamente los secretos de Git
   - C) Usa la API de Kubernetes Secrets
   - D) Requiere un administrador de secretos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No cifra automáticamente los secretos de Git**

**Explicación:**
ArgoCD no proporciona cifrado de secretos por sí mismo. Sealed Secrets y SOPS almacenan texto cifrado en Git. En cambio, las integraciones con ESO/Vault pueden almacenar referencias externas y recuperar los valores; no cifran automáticamente los archivos de Git. Base64 no es cifrado.

</details>

2. ¿Qué herramienta sella Kubernetes Secrets mediante una clave pública del controlador?
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sealed Secrets**

**Explicación:**
Sealed Secrets usa pares de claves del controlador. El alcance estricto predeterminado también vincula el nombre y el espacio de nombres, mientras que el límite de confianza para descifrar depende de quién posee las claves. El SealedSecret cifrado se puede almacenar de forma segura en Git; el controlador de Sealed Secrets lo descifra en el clúster.

</details>

3. ¿Cuál es la función del componente Dex de ArgoCD?
   - A) Analizar imágenes de contenedor
   - B) Proporcionar autenticación OpenID Connect y SSO
   - C) Aplicar políticas de red
   - D) Rotar secretos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporcionar autenticación OpenID Connect y SSO**

**Explicación:**
Dex es un servicio de identidad que proporciona autenticación OpenID Connect (OIDC). Intermedia identidades de LDAP, SAML, GitHub y otros proveedores mediante OIDC. El uso de OIDC directo en Argo CD no siempre requiere Dex.

</details>

4. ¿Cómo se puede restringir qué tipos de recursos con ámbito de espacio de nombres puede administrar una Application?
   - A) Mediante Kubernetes ResourceQuotas
   - B) Mediante `namespaceResourceBlacklist` o `namespaceResourceWhitelist` de AppProject
   - C) Cambiando únicamente las solicitudes y los límites de los Pods
   - D) No es posible en ArgoCD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante `namespaceResourceBlacklist` o `namespaceResourceWhitelist` de AppProject**

**Explicación:**
AppProjects pueden definir `namespaceResourceBlacklist` (denegar recursos específicos) o `namespaceResourceWhitelist` (permitir solo recursos específicos) para controlar los tipos de recursos con ámbito de espacio de nombres. Los recursos con ámbito de clúster usan listas distintas; esto no inspecciona ajustes de Pods privilegiados como lo haría una política de admisión.

</details>

5. ¿Cuál es la práctica recomendada para exponer el servidor API de ArgoCD?
   - A) Exponerlo públicamente con autenticación básica
   - B) Usar vías de acceso protegidas con TLS y autenticación
   - C) Ejecutarlo sin autenticación
   - D) Acceder a él únicamente mediante port-forwarding

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar vías de acceso protegidas con TLS y autenticación**

**Explicación:**
Use TLS con autenticación a través de un Ingress/Gateway o una ruta interna protegida. Terminar TLS en el frontend no valida por sí solo el TLS del backend. En entornos sensibles, se recomiendan medidas adicionales como el acceso por VPN o una lista de IP permitidas.

</details>
