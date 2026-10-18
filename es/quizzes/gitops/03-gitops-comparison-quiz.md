# Cuestionario de comparación de herramientas GitOps

Este cuestionario evalúa tus conocimientos sobre las herramientas GitOps y cómo elegir entre ellas.

1. ¿Qué herramienta GitOps incluye una interfaz web de forma predeterminada?
   - A) FluxCD
   - B) ArgoCD
   - C) Ambas
   - D) Ninguna

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ArgoCD**

**Explicación:**
ArgoCD incluye una interfaz web integrada y completa para administrar aplicaciones. FluxCD prioriza el uso de la CLI y no incluye una interfaz integrada, aunque se pueden añadir interfaces de terceros como Weave GitOps.

</details>

2. ¿Qué afirmación describe la compatibilidad actual con fuentes de despliegue basadas en OCI?
   - A) Solo ArgoCD admite OCI
   - B) Solo FluxCD admite OCI
   - C) Ambos admiten OCI, con distintas configuraciones de fuente, capa y verificación
   - D) Ninguno admite OCI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ambos admiten OCI, con distintas configuraciones de fuente, capa y verificación**

**Explicación:**
FluxCD admite artefactos OCI de forma nativa mediante su tipo de fuente `OCIRepository`, que permite almacenar y desplegar desde registros compatibles con OCI. La versión actual de Argo CD también admite fuentes de aplicación OCI generales. Compare los requisitos de versión, tipo de medio, autenticación y verificación.

</details>

3. ¿Qué herramienta incluye automatización de imágenes (actualizaciones automáticas de Git para imágenes nuevas)?
   - A) ArgoCD (de forma nativa)
   - B) FluxCD (de forma nativa)
   - C) Ambas la incluyen de forma nativa
   - D) Ninguna la incluye de forma nativa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FluxCD (de forma nativa)**

**Explicación:**
FluxCD ofrece los controladores opcionales Image Reflector e Image Automation. No siempre se instalan con el proceso de arranque predeterminado. Para una funcionalidad similar, ArgoCD requiere el proyecto independiente Argo Image Updater.

</details>

4. ¿En qué caso de uso sería ArgoCD la mejor opción?
   - A) Flujos de trabajo basados en la CLI que no requieren una interfaz
   - B) Equipos que necesitan gestión visual de los despliegues e integración con SSO
   - C) Requisitos de uso mínimo de recursos
   - D) Despliegues basados en artefactos OCI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Equipos que necesitan gestión visual de los despliegues e integración con SSO**

**Explicación:**
ArgoCD destaca en entornos donde los equipos necesitan información visual mediante su interfaz web, RBAC integral e integración de SSO con proveedores de identidad empresariales.

</details>

5. ¿Se pueden usar ArgoCD y FluxCD juntos en el mismo clúster?
   - A) No, son mutuamente excluyentes
   - B) Sí, pueden complementarse
   - C) Solo en entornos de desarrollo
   - D) Solo con una configuración especial

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sí, pueden complementarse**

**Explicación:**
ArgoCD y FluxCD pueden coexistir si cada uno administra recursos distintos; no permita que ambos reconcilien o eliminen los mismos objetos. Un patrón habitual es usar FluxCD para administrar la infraestructura y automatizar imágenes, y ArgoCD para desplegar aplicaciones con su interfaz de usuario.

</details>
