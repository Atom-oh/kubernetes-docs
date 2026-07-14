# Cuestionario de comparación de herramientas GitOps

Este cuestionario evalúa tu comprensión de las herramientas GitOps y cómo elegir entre ellas.

1. ¿Qué herramienta GitOps proporciona una Web UI integrada lista para usar?
   - A) FluxCD
   - B) ArgoCD
   - C) Ambas
   - D) Ninguna

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ArgoCD**

**Explicación:**
ArgoCD incluye una Web UI integrada y completa para administrar aplicaciones. FluxCD prioriza la CLI y no incluye una UI integrada, aunque se pueden añadir UI de terceros como Weave GitOps.

</details>

2. ¿Qué herramienta tiene mejor compatibilidad nativa con artefactos OCI como fuentes de Deployment?
   - A) ArgoCD
   - B) FluxCD
   - C) Ambas tienen compatibilidad equivalente
   - D) Ninguna admite OCI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FluxCD**

**Explicación:**
FluxCD tiene compatibilidad de primera clase con artefactos OCI mediante su tipo de fuente OCIRepository, lo que te permite almacenar y realizar Deployment desde registros compatibles con OCI. La compatibilidad de ArgoCD con OCI se limita a los charts de Helm.

</details>

3. ¿Qué herramienta proporciona automatización de imágenes integrada (actualizaciones automáticas de Git para imágenes nuevas)?
   - A) ArgoCD (nativa)
   - B) FluxCD (nativa)
   - C) Ambas tienen compatibilidad nativa
   - D) Ninguna tiene compatibilidad nativa

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FluxCD (nativa)**

**Explicación:**
FluxCD tiene Image Automation integrada mediante sus controladores Image Reflector e Image Automation. ArgoCD requiere el proyecto independiente Argo Image Updater para una funcionalidad similar.

</details>

4. ¿Para qué caso de uso sería ArgoCD la mejor elección?
   - A) Flujos de trabajo basados en CLI sin requisitos de UI
   - B) Equipos que necesitan gestión visual de Deployment e integración con SSO
   - C) Requisitos de uso mínimo de recursos
   - D) Deployments basados en artefactos OCI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Equipos que necesitan gestión visual de Deployment e integración con SSO**

**Explicación:**
ArgoCD destaca en entornos donde los equipos necesitan retroalimentación visual mediante su Web UI, RBAC integral e integración con SSO y proveedores de identidad empresariales.

</details>

5. ¿Se pueden usar ArgoCD y FluxCD juntos en el mismo cluster?
   - A) No, son mutuamente excluyentes
   - B) Sí, pueden complementarse
   - C) Solo en entornos de desarrollo
   - D) Solo con configuración especial

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sí, pueden complementarse**

**Explicación:**
ArgoCD y FluxCD se pueden usar juntos. Un patrón común es usar FluxCD para la gestión de infraestructura y la automatización de imágenes, mientras se usa ArgoCD para los Deployments de aplicaciones con su UI.

</details>
