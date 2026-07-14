# Cuestionario de ApplicationSets de ArgoCD

Este cuestionario evalúa tu comprensión de los ApplicationSets de ArgoCD para la generación de aplicaciones con plantillas.

1. ¿Cuál es el propósito principal de un ApplicationSet?
   - A) Agrupar Applications existentes
   - B) Generar automáticamente múltiples Applications a partir de plantillas
   - C) Crear copias de seguridad de aplicaciones
   - D) Gestionar secretos de aplicaciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Generar automáticamente múltiples Applications a partir de plantillas**

**Explicación:**
Los ApplicationSets usan generators y plantillas para crear y gestionar automáticamente múltiples Applications de ArgoCD. Son ideales para desplegar aplicaciones en múltiples clusters o entornos.

</details>

2. ¿Qué generator usarías para crear Applications para cada cluster registrado en ArgoCD?
   - A) Git generator
   - B) List generator
   - C) Cluster generator
   - D) Matrix generator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Cluster generator**

**Explicación:**
El Cluster generator genera automáticamente Applications para cada cluster registrado en ArgoCD. Puede usar selectores de etiquetas para dirigirse a clusters específicos.

</details>

3. ¿Qué hace el Git directory generator?
   - A) Crea Applications basadas en ramas de Git
   - B) Crea Applications para cada directorio en una ruta especificada
   - C) Sincroniza las credenciales de Git
   - D) Gestiona webhooks de Git

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crea Applications para cada directorio en una ruta especificada**

**Explicación:**
El Git directory generator analiza un directorio especificado en un repositorio de Git y crea una Application para cada subdirectorio encontrado. Esto es útil para configuraciones de monorepo.

</details>

4. ¿Cómo combinas múltiples generators en un ApplicationSet?
   - A) Usando el Merge generator
   - B) Usando el Matrix generator
   - C) Usando el Combine generator
   - D) Tanto A como B

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Tanto A como B**

**Explicación:**
El Matrix generator crea combinaciones (producto cartesiano) de parámetros de múltiples generators. El Merge generator combina parámetros de múltiples generators, fusionando las entradas coincidentes. Ambos pueden usarse para combinar generators.

</details>

5. ¿Cuál es el propósito del campo `goTemplate` en las plantillas de ApplicationSet?
   - A) Habilitar la programación en Go
   - B) Usar la sintaxis de plantillas de Go para una creación de plantillas más compleja
   - C) Compilar aplicaciones de Go
   - D) Habilitar la depuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar la sintaxis de plantillas de Go para una creación de plantillas más compleja**

**Explicación:**
Configurar `goTemplate: true` habilita la sintaxis de plantillas de Go, que proporciona capacidades de creación de plantillas más potentes, como condicionales, bucles y funciones, en comparación con la sustitución de variables simple predeterminada.

</details>

6. ¿Qué generator usarías para crear Applications basadas en pull requests?
   - A) Git generator
   - B) Pull Request generator
   - C) SCM Provider generator
   - D) Webhook generator

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pull Request generator**

**Explicación:**
El Pull Request generator crea Applications para cada pull request abierto en un repositorio, lo que habilita entornos de vista previa para la revisión de código. Es compatible con GitHub, GitLab, Bitbucket y Gitea.

</details>

7. ¿Qué sucede de forma predeterminada cuando eliminas un ApplicationSet?
   - A) Nada, las Applications generadas permanecen
   - B) Se eliminan todas las Applications generadas
   - C) Las Applications quedan huérfanas
   - D) Se crea una copia de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Se eliminan todas las Applications generadas**

**Explicación:**
De forma predeterminada, los ApplicationSets tienen una política de eliminación en cascada, lo que significa que, al eliminar un ApplicationSet, también se eliminarán todas las Applications que generó. Esto se puede cambiar usando la política `preserveResourcesOnDeletion`.

</details>

8. ¿Cómo puedes evitar que un ApplicationSet elimine las Applications generadas cuando se elimina el ApplicationSet?
   - A) Configurar `syncPolicy.preserveResourcesOnDeletion: true`
   - B) Usar el finalizer `orphan`
   - C) Configurar la anotación de la política de eliminación
   - D) Eliminar manualmente la referencia de propietario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Configurar `syncPolicy.preserveResourcesOnDeletion: true`**

**Explicación:**
Configurar `preserveResourcesOnDeletion: true` en el syncPolicy del ApplicationSet garantiza que las Applications generadas (y sus recursos desplegados) se conserven cuando se elimina el ApplicationSet.

</details>
